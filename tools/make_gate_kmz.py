"""Make a wormhole gate KMZ for EarthStick 1.3+ (golden vertical rings + gate data).

Each gate is a vertical ring (thick gold LineString circle, altitudeMode absolute so it
matches the camera altitude EarthStick reads) plus a label point, with ExtendedData
that EarthStick reads from its Gates folder:
  gate=1, lat, lon, alt_m (absolute), radius_m, facing (compass direction you fly to go
  through), and either to=<partner gate name> or dest_lat/dest_lon/dest_alt_m/dest_heading.

Use from Python:
    from make_gate_kmz import gate, write_kmz
    write_kmz("Gates.kmz", "My gates", [gate("NYC", 30.32, -81.65, 457, facing=28.7, to="JAX"), ...], red_backs=True)

side_labels=True puts each name beside its own ring at centre height with an "eye alt N ft" line below
(name_scale / alt_scale set the text sizes). red_backs=True adds a red ring BACK_OFFSET_M behind each gold ring (the wrong side), drawn only, not a gate.
"""
import math
import struct
import zipfile
import zlib
from xml.sax.saxutils import escape

R = 6371008.8
GOLD = "ff00d7ff"   # KML aabbggrr for #FFD700
RED = "ff0000ff"
BACK_OFFSET_M = 10.0  # red back ring sits this far behind the gold one


def dest(lat, lon, brg, d):
    la, lo, b = map(math.radians, (lat, lon, brg))
    dd = d / R
    la2 = math.asin(math.sin(la) * math.cos(dd) + math.cos(la) * math.sin(dd) * math.cos(b))
    lo2 = lo + math.atan2(math.sin(b) * math.sin(dd) * math.cos(la), math.cos(dd) - math.sin(la) * math.sin(la2))
    return math.degrees(la2), math.degrees(lo2)


def bearing(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(math.radians, (lat1, lon1, lat2, lon2))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def gate(name, lat, lon, alt_m, facing, radius_m=150.0, to="", dest_lat=None, dest_lon=None,
         dest_alt_m=None, dest_heading=None, description=""):
    g = dict(name=name, lat=lat, lon=lon, alt_m=alt_m, facing=facing % 360, radius_m=radius_m, to=to,
             description=description)
    if not to:
        g.update(dest_lat=dest_lat, dest_lon=dest_lon, dest_alt_m=dest_alt_m, dest_heading=dest_heading)
    return g


def _ring_coords(g, step=5, behind_m=0.0):
    side = (g["facing"] + 90) % 360
    if behind_m:
        clat, clon = dest(g["lat"], g["lon"], g["facing"], behind_m)
        g = dict(g, lat=clat, lon=clon)
    pts = []
    for k in range(0, 360 + step, step):
        t = math.radians(k)
        h = g["radius_m"] * math.cos(t)
        la, lo = dest(g["lat"], g["lon"], side if h >= 0 else (side + 180) % 360, abs(h))
        pts.append(f"{lo:.7f},{la:.7f},{g['alt_m'] + g['radius_m'] * math.sin(t):.1f}")
    return " ".join(pts)


def _placemark(g, side_labels=False):
    data = ["gate=1"]
    keys = ["lat", "lon", "alt_m", "radius_m", "facing", "to"]
    if not g["to"]:
        keys += ["dest_lat", "dest_lon", "dest_alt_m", "dest_heading"]
    ext = "".join(f'<Data name="{k}"><value>{escape(str(g[k]))}</value></Data>' for k in keys)
    return f'''  <Placemark>
    <name>{escape(g["name"])}</name>
    <description><![CDATA[{g["description"]}]]></description>
    <styleUrl>#gate</styleUrl>
    <ExtendedData><Data name="gate"><value>1</value></Data>{ext}</ExtendedData>
    <MultiGeometry>
      {"" if side_labels else f'<Point><altitudeMode>absolute</altitudeMode><coordinates>{g["lon"]:.7f},{g["lat"]:.7f},{g["alt_m"] + g["radius_m"] + 40:.1f}</coordinates></Point>'}
      <LineString><tessellate>0</tessellate><altitudeMode>absolute</altitudeMode><coordinates>{_ring_coords(g)}</coordinates></LineString>
    </MultiGeometry>
  </Placemark>'''


LABEL_GAP_M = 40.0      # name starts this far outside the ring's right edge (seen from the gold side)
ALT_LINE_DROP_M = 130.0 # altitude line sits this far below the name


def _label_placemarks(g):
    """Name beside its own ring at centre height, eye-alt line underneath (MSL feet, as ArcGIS Earth shows)."""
    lat, lon = dest(g["lat"], g["lon"], (g["facing"] + 90) % 360, g["radius_m"] + LABEL_GAP_M)
    ft = round(g["alt_m"] / 0.3048 / 10) * 10
    desc = f"<![CDATA[{g['description']}]]>"
    return f'''  <Placemark>
    <name>{escape(g["name"])}</name>
    <description>{desc}</description>
    <styleUrl>#gateName</styleUrl>
    <Point><altitudeMode>absolute</altitudeMode><coordinates>{lon:.7f},{lat:.7f},{g["alt_m"]:.1f}</coordinates></Point>
  </Placemark>
  <Placemark>
    <name>{ft:,} ft</name>
    <description>{desc}</description>
    <styleUrl>#gateAlt</styleUrl>
    <Point><altitudeMode>absolute</altitudeMode><coordinates>{lon:.7f},{lat:.7f},{g["alt_m"] - ALT_LINE_DROP_M:.1f}</coordinates></Point>
  </Placemark>'''


def _back_placemark(g):
    return f'''  <Placemark>
    <name>{escape(g["name"])} (back)</name>
    <styleUrl>#gateBack</styleUrl>
    <LineString><tessellate>0</tessellate><altitudeMode>absolute</altitudeMode><coordinates>{_ring_coords(g, behind_m=BACK_OFFSET_M)}</coordinates></LineString>
  </Placemark>'''


def _blank_png():
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) + ch(b"IEND", b""))


LOD_FT_PX = 1_790_000.0   # Object Factory 1.2 calibration (300 m cube, Jim's screen)


def lod_folder(name, inner_kml, lat, lon, alt_m, hide_above_ft, box_m=300.0):
    """Wrap KML in a Folder that only shows within about hide_above_ft (Region cube, proven in Object Factory 1.2)."""
    half = box_m / 2.0
    dlat = math.degrees(half / R)
    dlon = math.degrees(half / (R * max(math.cos(math.radians(lat)), 0.01)))
    lod = max(1, int(round(LOD_FT_PX / hide_above_ft)))
    return f'''  <Folder>
    <name>{escape(name)}</name>
    <Region><LatLonAltBox><north>{lat + dlat:.8f}</north><south>{lat - dlat:.8f}</south><east>{lon + dlon:.8f}</east><west>{lon - dlon:.8f}</west><minAltitude>{alt_m - half:.1f}</minAltitude><maxAltitude>{alt_m + half:.1f}</maxAltitude><altitudeMode>absolute</altitudeMode></LatLonAltBox>
      <Lod><minLodPixels>{lod}</minLodPixels><maxLodPixels>-1</maxLodPixels></Lod></Region>
{inner_kml}
  </Folder>'''


def welcome_sign(text, lat, lon, alt_m, heading, ahead_m=250.0, above_m=40.0):
    """Floating text placed ahead of an arrival point (seen right after a jump)."""
    slat, slon = dest(lat, lon, heading, ahead_m)
    return f'''  <Placemark>
    <name>{escape(text)}</name>
    <styleUrl>#welcome</styleUrl>
    <Point><altitudeMode>absolute</altitudeMode><coordinates>{slon:.7f},{slat:.7f},{alt_m + above_m:.1f}</coordinates></Point>
  </Placemark>'''


SHOW_ME_JS = r"""<script>
function showMe(id, name, lat, lon, rgb) {
  rgb = rgb || [255, 0, 0];
  var api = "http://localhost:8000/arcgisearth/drawings";
  var out = document.getElementById("st-" + id);
  var items = [
    {id: id + "-label", visible: true, title: name,
     geometry: {x: lon, y: lat, spatialReference: {wkid: 4326}},
     labelSymbol: {type: "text", color: rgb.concat([255]), size: 16}},
    {id: id + "-beacon", visible: true, title: name + " beacon",
     geometry: {paths: [[[lon, lat, 0], [lon, lat, 3000]]], hasZ: true, spatialReference: {wkid: 4326}},
     symbol: {type: "simple-line", color: rgb.concat([255]), width: 6}}];
  items.forEach(function (b) {
    fetch(api + "/" + b.id, {method: "DELETE"}).catch(function () {}).then(function () {
      return fetch(api, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(b)})
        .catch(function () {
          return fetch(api, {method: "POST", mode: "no-cors", headers: {"Content-Type": "text/plain"}, body: JSON.stringify(b)});
        });
    }).then(function () { if (out && !out.textContent) out.textContent = "Beacon on. To clear it, untick it under My Drawings (left)."; })
      .catch(function (e) { out.textContent = "Could not reach ArcGIS Earth (Automation API on?) " + e; });
  });
}
function clearMe(id) {
  var api = "http://localhost:8000/arcgisearth/drawings/";
  ["-label", "-beacon"].forEach(function (k) { fetch(api + id + k, {method: "DELETE", mode: "no-cors"}).catch(function () {}); });
  document.getElementById("st-" + id).textContent = "Beacon removed.";
}
</script>"""


def site_placemark(site_id, name, blurb, lat, lon, pos_lat, pos_lon, pos_alt_m, icon_href="icons/site.png",
                   rgb=None, auto=False):
    """Floating menu icon at pos_*; its popup draws a beacon at (lat, lon) through the Automation API.
    auto=True (Jim, 2026-11-03): the beacon goes up as soon as the popup opens - no buttons; clear it by
    unticking it under My Drawings. rgb = beacon/label colour; the menu name is drawn in the same colour."""
    js_name = escape(name).replace("\\", "\\\\").replace("'", "\\'")
    if auto:
        c = list(rgb or (255, 0, 0))
        html = (f'<div style="font-family:Segoe UI,Arial,sans-serif;min-width:260px">'
                f'<small>{escape(blurb)}</small>'
                f'<div id="st-{site_id}" style="margin-top:6px;color:#555"></div>{SHOW_ME_JS}'
                f'<script>showMe(\'{site_id}\', \'{js_name}\', {lat}, {lon}, {c});</script></div>')
        kml_col = f"ff{c[2]:02x}{c[1]:02x}{c[0]:02x}"
        return f'''  <Placemark>
    <name>{escape(name)}</name>
    <description><![CDATA[{html}]]></description>
    <Style><IconStyle><scale>0.9</scale><Icon><href>{icon_href}</href></Icon></IconStyle><LabelStyle><color>{kml_col}</color><scale>0.9</scale></LabelStyle></Style>
    <Point><altitudeMode>absolute</altitudeMode><coordinates>{pos_lon:.7f},{pos_lat:.7f},{pos_alt_m:.1f}</coordinates></Point>
  </Placemark>'''
    html = (f'<div style="font-family:Segoe UI,Arial,sans-serif;min-width:300px"><b>{escape(name)}</b><br/>'
            f'<small>{escape(blurb)}</small><br/><br/>'
            f'<button onclick="showMe(\'{site_id}\', \'{js_name}\', {lat}, {lon})">SHOW ME</button> '
            f'<button onclick="clearMe(\'{site_id}\')">CLEAR BEACON</button>'
            f'<div id="st-{site_id}" style="margin-top:6px;color:#555"></div>{SHOW_ME_JS}</div>')
    return f'''  <Placemark>
    <name>{escape(name)}</name>
    <description><![CDATA[{html}]]></description>
    <styleUrl>#site</styleUrl>
    <Point><altitudeMode>absolute</altitudeMode><coordinates>{pos_lon:.7f},{pos_lat:.7f},{pos_alt_m:.1f}</coordinates></Point>
  </Placemark>'''


def write_kmz(path, title, gates, width=10, red_backs=False, side_labels=False, name_scale=2.0, alt_scale=1.0, extra_kml="", extra_files=None,
              label_within_ft=None):
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>{escape(title)}</name>
  <Style id="gate">
    <LineStyle><color>{GOLD}</color><width>{width}</width></LineStyle>
    <IconStyle><scale>1.0</scale><Icon><href>icons/blank.png</href></Icon></IconStyle>
    <LabelStyle><color>{GOLD}</color><scale>{name_scale}</scale></LabelStyle>
  </Style>
  <Style id="gateName"><IconStyle><scale>1.0</scale><Icon><href>icons/blank.png</href></Icon></IconStyle><LabelStyle><color>{GOLD}</color><scale>{name_scale}</scale></LabelStyle></Style>
  <Style id="gateAlt"><IconStyle><scale>1.0</scale><Icon><href>icons/blank.png</href></Icon></IconStyle><LabelStyle><color>ffffffff</color><scale>{alt_scale}</scale></LabelStyle></Style>
  <Style id="site"><IconStyle><scale>0.9</scale><Icon><href>icons/site.png</href></Icon></IconStyle><LabelStyle><color>ffffffff</color><scale>0.9</scale></LabelStyle></Style>
  <Style id="welcome"><IconStyle><scale>1.0</scale><Icon><href>icons/blank.png</href></Icon></IconStyle><LabelStyle><color>{GOLD}</color><scale>1.4</scale></LabelStyle><BalloonStyle><displayMode>hide</displayMode></BalloonStyle></Style>
  <Style id="gateBack"><LineStyle><color>{RED}</color><width>{width}</width></LineStyle><BalloonStyle><displayMode>hide</displayMode></BalloonStyle></Style>
{chr(10).join(_placemark(g, side_labels) for g in gates)}
{chr(10).join((lod_folder(g["name"] + " name", _label_placemarks(g), g["lat"], g["lon"], g["alt_m"], label_within_ft) if label_within_ft else _label_placemarks(g)) for g in gates) if side_labels else ""}
{extra_kml}
{chr(10).join(_back_placemark(g) for g in gates) if red_backs else ""}
</Document>
</kml>'''
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)
        z.writestr("icons/blank.png", _blank_png())
        for arc, data in (extra_files or {}).items():
            z.writestr(arc, data)
    return path
