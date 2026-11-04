"""Preview what a KMZ looks like in ArcGIS Earth from a camera pose, before Jim flies it.

Calibrated on Jim's screenshots (2000 x 1125 px as shown in chat = his 3840 x 2160 screen / 1.92):
  * pinhole camera, focal length F_PX = 1231 px  ->  ~78 deg wide, ~49 deg tall
  * KML text is a fixed size on screen; a label starts LABEL_DX px right of its point and its
    middle sits LABEL_DY px above it (~1.9 deg); label scale 0.9 ~ 14.5 px per character,
    scale 1.4 ~ 23.5 px per character (bold sans with an outline)
  * eye alt = camera height above SEA LEVEL; KML 'absolute' altitudes are sea level too
See ARCGIS_EARTH_API.md "Viewer geometry" for the measurements.

Use:
  from preview_view import load_kmz, render, project
  items = load_kmz("World_Gates_JAX_ATL_v17.kmz")
  render(items, cam=dict(lat=..., lon=..., alt=..., heading=..., pitch=10), out="preview.png")
pitch = degrees the view is tilted UP from level (Jim's arrivals usually look ~0-10 deg up).
"""
import math
import re
import zipfile
import xml.etree.ElementTree as ET

W, H, F_PX = 2000, 1125, 1231.0
LABEL_DX, LABEL_DY = 22, -39          # label beside a site star (scale 0.9 icon), measured Rio v17
BLANK_DX, BLANK_DY = 36, -21          # label of a blank-icon point (welcome sign, ring names), measured Rio v17
PX_PER_CHAR = {0.9: 14.5, 1.0: 16.0, 1.4: 23.5}
R = 6371008.8
K = "{http://www.opengis.net/kml/2.2}"


def _px_per_char(scale):
    return PX_PER_CHAR.get(scale, 16.0 * scale)


def _kml_color(aabbggrr, default=(255, 215, 0)):
    if not aabbggrr or len(aabbggrr) != 8:
        return default
    return (int(aabbggrr[6:8], 16), int(aabbggrr[4:6], 16), int(aabbggrr[2:4], 16))


def load_kmz(path):
    """Items: rings (polylines), labels (points with text), stars (site icons). Region LOD is ignored."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("doc.kml"))
    styles = {}
    for st in root.iter(K + "Style"):
        sid = st.get("id")
        if sid:
            styles["#" + sid] = st
    items = []
    for pm in root.iter(K + "Placemark"):
        name = (pm.findtext(K + "name") or "").strip()
        st = pm.find(K + "Style")
        if st is None:
            st = styles.get((pm.findtext(K + "styleUrl") or "").strip())
        icon = st.find(f".//{K}IconStyle/{K}Icon/{K}href") if st is not None else None
        lab = st.find(f".//{K}LabelStyle") if st is not None else None
        line = st.find(f".//{K}LineStyle/{K}color") if st is not None else None
        scale = float(lab.findtext(K + "scale") or 1.0) if lab is not None else 1.0
        lcol = _kml_color(lab.findtext(K + "color")) if lab is not None else (255, 255, 255)
        for ls in pm.iter(K + "LineString"):
            pts = [tuple(map(float, c.split(","))) for c in (ls.findtext(K + "coordinates") or "").split()]
            items.append(dict(kind="line", name=name, pts=pts, color=_kml_color(line.text if line is not None else None)))
        for p in pm.iter(K + "Point"):
            lon, lat, alt = map(float, (p.findtext(K + "coordinates") or "0,0,0").strip().split(","))
            href = icon.text if icon is not None else ""
            items.append(dict(kind="point", name=name, lon=lon, lat=lat, alt=alt, scale=scale, color=lcol,
                              star="site" in (href or ""), blank="blank" in (href or "")))
    return items


def _enu(cam, lon, lat, alt):
    """Camera-relative east/north/up metres (earth curvature included)."""
    la0 = math.radians(cam["lat"])
    e = math.radians(lon - cam["lon"]) * R * math.cos(la0)
    n = math.radians(lat - cam["lat"]) * R
    d2 = e * e + n * n
    return e, n, alt - cam["alt"] - d2 / (2 * R)


def project(cam, lon, lat, alt):
    """Screen x, y (None if behind the camera)."""
    h, p = math.radians(cam["heading"]), math.radians(cam.get("pitch", 0.0))
    fwd = (math.sin(h) * math.cos(p), math.cos(h) * math.cos(p), math.sin(p))
    right = (math.cos(h), -math.sin(h), 0.0)
    up = (fwd[1] * right[2] - fwd[2] * right[1], fwd[2] * right[0] - fwd[0] * right[2], fwd[0] * right[1] - fwd[1] * right[0])
    up = tuple(-u for u in up) if up[2] < 0 else up
    v = _enu(cam, lon, lat, alt)
    z = sum(a * b for a, b in zip(v, fwd))
    if z <= 1.0:
        return None
    x = W / 2 + F_PX * sum(a * b for a, b in zip(v, right)) / z
    y = H / 2 - F_PX * sum(a * b for a, b in zip(v, up)) / z
    return x, y


def label_box(x, y, text, scale, blank=False):
    w = _px_per_char(scale) * len(text)
    hgt = _px_per_char(scale) * 1.9
    dx, dy = (BLANK_DX, BLANK_DY) if blank else (LABEL_DX, LABEL_DY)
    cx, cy = x + dx, y + dy
    return (cx, cy - hgt / 2, cx + w, cy + hgt / 2)


MAX_DIST_M = 15000.0   # things farther than this are hidden by the KML Region rules (signs/stars 40,000 ft, ring names 20,000 ft) or the horizon


def _dist(cam, lon, lat):
    e, n, _ = _enu(cam, lon, lat, cam["alt"])
    return math.hypot(e, n)


def screen_items(items, cam, max_dist=MAX_DIST_M):
    """Projected items within max_dist: lines as point lists, labels with boxes. Used by render() and overlap checks."""
    out = []
    for it in items:
        ref = it["pts"][0] if it["kind"] == "line" else (it["lon"], it["lat"])
        if _dist(cam, ref[0], ref[1]) > max_dist:
            continue
        if it["kind"] == "line":
            pts = [project(cam, *p) for p in it["pts"]]
            pts = [q for q in pts if q]
            if pts:
                out.append(dict(it, screen=pts))
        else:
            q = project(cam, it["lon"], it["lat"], it["alt"])
            if q:
                out.append(dict(it, screen=q, box=label_box(q[0], q[1], it["name"], it["scale"], it["blank"])))
    return out


def overlaps(items, cam, margin=4):
    """Pairs of on-screen labels whose boxes overlap (the thing Jim keeps catching)."""
    labs = [s for s in screen_items(items, cam) if s["kind"] == "point" and s["name"]
            and -200 < s["screen"][0] < W + 200 and -200 < s["screen"][1] < H + 200]
    bad = []
    for i, a in enumerate(labs):
        for b in labs[i + 1:]:
            A, B = a["box"], b["box"]
            if A[0] < B[2] + margin and B[0] < A[2] + margin and A[1] < B[3] + margin and B[1] < A[3] + margin:
                bad.append((a["name"], b["name"]))
    return bad


def render(items, cam, out, title=""):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (W, H), (150, 200, 245))
    d = ImageDraw.Draw(im)
    # horizon: the sea-level point 50 km straight ahead
    far = 50000.0
    la, lo = _dest(cam["lat"], cam["lon"], cam["heading"], far)
    hz = project(cam, lo, la, 0.0)
    if hz:
        d.rectangle((0, hz[1], W, H), fill=(95, 120, 90))
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    lines = [s for s in screen_items(items, cam) if s["kind"] == "line" and len(s["screen"]) > 1]
    lines.sort(key=lambda s: -_dist(cam, s["pts"][0][0], s["pts"][0][1]))   # far first, so near rings paint on top
    for s in lines:
        d.line(s["screen"], fill=s["color"], width=8)
    for s in screen_items(items, cam):
        if s["kind"] != "point":
            continue
        x, y = s["screen"]
        if s["star"]:
            d.regular_polygon((x, y, 11), 5, fill=(255, 215, 0), outline=(120, 90, 0))
        if s["name"]:
            size = int(_px_per_char(s["scale"]) * 1.65)
            f = ImageFont.truetype(font_path, size)
            b = s["box"]
            d.text((b[0], (b[1] + b[3]) / 2), s["name"], font=f, fill=s["color"], anchor="lm",
                   stroke_width=max(2, size // 10), stroke_fill=(0, 0, 0))
    d.line((W / 2 - 20, H / 2, W / 2 + 20, H / 2), fill=(230, 30, 30), width=3)
    d.line((W / 2, H / 2 - 20, W / 2, H / 2 + 20), fill=(230, 30, 30), width=3)
    if title:
        d.text((20, 20), title, font=ImageFont.truetype(font_path, 26), fill=(0, 0, 0))
    im.save(out)
    return out


def _dest(lat, lon, brg, dist):
    la, lo, b = map(math.radians, (lat, lon, brg))
    dd = dist / R
    la2 = math.asin(math.sin(la) * math.cos(dd) + math.cos(la) * math.sin(dd) * math.cos(b))
    lo2 = lo + math.atan2(math.sin(b) * math.sin(dd) * math.cos(la), math.cos(dd) - math.sin(la) * math.sin(la2))
    return math.degrees(la2), math.degrees(lo2)
