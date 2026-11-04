"""World Gate Maker 1.0 - make your own pair of World Gates for EarthStick (1.3 or later).

Jim's idea (2026-11-04): two places (GPS coordinates + name), one height above ground,
and you get a pair of golden rings: the ring at place 1 takes you to place 2 and the
ring at place 2 brings you back. Each ring is named for where it takes you and faces
the other place. Same look as the World Gates pack: gold front, red back, name beside
the ring with the eye alt to fly at underneath (names only show when you are near).

The KMZ is saved into EarthStick's Gates folder. Drag the same file onto ArcGIS Earth to
see the rings, then restart EarthStick (it reads the Gates folder when it starts).

Standard library only. Self-test: py -3 World_Gate_Maker.py --selftest
"""
import json
import math
import os
import re
import struct
import sys
import zipfile
import zlib
from pathlib import Path
from xml.sax.saxutils import escape

APP = "World Gate Maker"
VERSION = "1.0"
FT = 0.3048
R = 6371008.8
GOLD = "ff00d7ff"          # KML aabbggrr for #FFD700
RED = "ff0000ff"
BACK_OFFSET_M = 10.0       # red back ring sits this far behind the gold one
LABEL_GAP_M = 40.0         # name starts this far outside the ring's edge
ALT_LINE_DROP_M = 130.0    # "N ft" line sits this far below the name
SHOW_NAMES_WITHIN_FT = 20000.0
LOD_FT_PX = 1_790_000.0    # Object Factory 1.2 calibration (300 m cube)
GATE_EXIT_M = 300.0        # EarthStick lands you this far past the partner ring
SIZES = {"Small (100 m)": 50.0, "Medium (250 m)": 125.0, "Large (450 m)": 225.0}   # ring radius in metres
DEFAULT_SIZE = "Medium (250 m)"
DEFAULT_AGL_FT = 500
MIN_CLEARANCE_M = 15.0     # lowest point of the ring must stay this far above the ground
MAX_NAME_CHARS = 18        # longer names wrap onto two lines in ArcGIS Earth
SETTINGS = Path(__file__).resolve().with_name("World_Gate_Maker_settings.json")


# ---------------------------------------------------------------- geometry
def dest(lat, lon, brg, d):
    la, lo, b = map(math.radians, (lat, lon, brg))
    dd = d / R
    la2 = math.asin(math.sin(la) * math.cos(dd) + math.cos(la) * math.sin(dd) * math.cos(b))
    lo2 = lo + math.atan2(math.sin(b) * math.sin(dd) * math.cos(la), math.cos(dd) - math.sin(la) * math.sin(la2))
    return math.degrees(la2), (math.degrees(lo2) + 540) % 360 - 180


def bearing(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(math.radians, (lat1, lon1, lat2, lon2))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def distance_m(lat1, lon1, lat2, lon2):
    la1, la2 = math.radians(lat1), math.radians(lat2)
    dla, dlo = la2 - la1, math.radians(lon2 - lon1)
    a = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


# ---------------------------------------------------------------- coordinates (from Object Factory 1.2)
def validate_lat_lon(lat, lon):
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValueError("Coordinates must be finite numbers.")
    if not -90 <= lat <= 90:
        raise ValueError("Latitude must be between -90 and 90.")
    if not -180 <= lon <= 180:
        raise ValueError("Longitude must be between -180 and 180.")
    return lat, lon


COORD_RE = re.compile(r"""
    (?<![A-Za-z])(?P<pre>[NSEWnsew])?\s*
    (?P<sign>[-+])?\s*
    (?P<deg>\d+(?:\.\d+)?|\.\d+)\s*[°º˚]?\s*
    (?:(?P<min>\d+(?:\.\d+)?)\s*['′’]\s*)?
    (?:(?P<sec>\d+(?:\.\d+)?)\s*(?:["″”]|'')\s*)?
    (?(pre)|(?P<post>[NSEWnsew])(?![A-Za-z]))?
    """, re.X)


def _coord_value(m):
    deg = float(m.group("deg"))
    minutes = float(m.group("min")) if m.group("min") else 0.0
    seconds = float(m.group("sec")) if m.group("sec") else 0.0
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"Minutes and seconds must be below 60: {m.group(0).strip()}")
    value = deg + minutes / 60.0 + seconds / 3600.0
    hemi = (m.group("pre") or m.group("post") or "").upper() or None
    sign = m.group("sign")
    if hemi:
        if (hemi in "SW" and sign == "+") or (hemi in "NE" and sign == "-"):
            raise ValueError(f"Sign and hemisphere letter disagree: {m.group(0).strip()}")
        value = -value if hemi in "SW" else value
    elif sign == "-":
        value = -value
    return value, hemi


def _readback(lat, lon):
    return (f"Read as Latitude {abs(lat):.6f} {'N' if lat >= 0 else 'S'}, "
            f"Longitude {abs(lon):.6f} {'E' if lon >= 0 else 'W'}")


def parse_coordinates(text):
    """Latitude, longitude from text such as a Google Maps right-click copy ("30.40098, -81.93471")."""
    if not text or not text.strip():
        raise ValueError("Nothing to read - the clipboard is empty.")
    source = text.strip()
    lat_match = re.search(r"\b(?:lat|latitude)\b\s*[:=]?\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))", source, re.I)
    lon_match = re.search(r"\b(?:lon|lng|long|longitude)\b\s*[:=]?\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))", source, re.I)
    if lat_match and lon_match:
        lat, lon = float(lat_match.group(1)), float(lon_match.group(1))
        validate_lat_lon(lat, lon)
        return lat, lon
    values = [_coord_value(m) for m in COORD_RE.finditer(source) if m.group("deg")]
    lettered = [(v, h) for v, h in values if h]
    if len(lettered) == 2:
        values = lettered
    elif len(values) != 2:
        raise ValueError("Could not find one latitude, longitude pair. "
                         "Copy it from Google Maps: right-click the spot and click the numbers at the top.")
    (a, ha), (b, hb) = values
    if ha or hb:
        roles = {}
        for value, hemi in ((a, ha), (b, hb)):
            if hemi:
                role = "lat" if hemi in "NS" else "lon"
                if role in roles:
                    raise ValueError("Two latitudes or two longitudes - copy one pair.")
                roles[role] = value
        if "lat" not in roles:
            roles["lat"] = a if roles["lon"] is b else b
        if "lon" not in roles:
            roles["lon"] = a if roles["lat"] is b else b
        lat, lon = roles["lat"], roles["lon"]
    else:
        lat, lon = a, b                    # Google Maps order: latitude first
        if not -90 <= a <= 90 and -90 <= b <= 90:
            lat, lon = b, a
    validate_lat_lon(lat, lon)
    return lat, lon


def parse_number(text, what):
    t = (text or "").strip().replace(",", "")
    t = re.sub(r"\s*(ft|feet|')\s*$", "", t, flags=re.I)
    if not t:
        raise ValueError(f"{what} is empty.")
    try:
        v = float(t)
    except ValueError:
        raise ValueError(f"{what} must be a number (got {text!r}).")
    if not math.isfinite(v):
        raise ValueError(f"{what} must be a number.")
    return v


# ---------------------------------------------------------------- gates
def make_pair(name1, lat1, lon1, elev1_ft, name2, lat2, lon2, elev2_ft, agl_ft, radius_m):
    """Two gates: the ring at place 1 is named name2 and leads to the ring at place 2 (named name1),
    and the other way round. Returns (gates, notes)."""
    name1, name2 = (name1 or "").strip(), (name2 or "").strip()
    if not name1 or not name2:
        raise ValueError("Give both places a name.")
    if name1.lower() == name2.lower():
        raise ValueError("The two places need different names (each ring is named for where it takes you).")
    validate_lat_lon(lat1, lon1)
    validate_lat_lon(lat2, lon2)
    if not radius_m > 0:
        raise ValueError("Choose a ring size.")
    if not -1500 <= elev1_ft <= 30000 or not -1500 <= elev2_ft <= 30000:
        raise ValueError("Ground elev looks wrong - use the 'elev' number (feet) from ArcGIS Earth's status bar.")
    min_agl_ft = math.ceil((radius_m + MIN_CLEARANCE_M) / FT / 10) * 10
    if agl_ft < min_agl_ft:
        raise ValueError(f"Height above ground must be at least {min_agl_ft:,} ft for this ring size, "
                         f"or the bottom of the ring would touch the ground.")
    d = distance_m(lat1, lon1, lat2, lon2)
    min_d = 2 * radius_m + GATE_EXIT_M + 200
    if d < min_d:
        raise ValueError(f"The places are only {d:,.0f} m apart - they must be at least {min_d:,.0f} m apart "
                         f"for this ring size.")
    alt1 = (elev1_ft + agl_ft) * FT
    alt2 = (elev2_ft + agl_ft) * FT
    face1 = bearing(lat1, lon1, lat2, lon2)          # ring at place 1 faces place 2
    face2 = bearing(lat2, lon2, lat1, lon1)
    ft1 = round(alt1 / FT / 10) * 10
    ft2 = round(alt2 / FT / 10) * 10
    g1 = dict(name=name2, lat=lat1, lon=lon1, alt_m=alt1, facing=face1, radius_m=radius_m, to=name1,
              description=f"<b>Gate to {escape(name2)}</b><br/>Fly through the gold side at eye alt {ft1:,} ft.")
    g2 = dict(name=name1, lat=lat2, lon=lon2, alt_m=alt2, facing=face2, radius_m=radius_m, to=name2,
              description=f"<b>Gate to {escape(name1)}</b><br/>Fly through the gold side at eye alt {ft2:,} ft.")
    notes = [f"{d / 1000:,.1f} km apart"]
    for n in (name1, name2):
        if len(n) > MAX_NAME_CHARS:
            notes.append(f"'{n}' is long - ArcGIS Earth may split it onto two lines (keep names to {MAX_NAME_CHARS} characters)")
    return [g1, g2], notes


def _ring_coords(g, step=5, behind_m=0.0):
    side = (g["facing"] + 90) % 360
    lat, lon = g["lat"], g["lon"]
    if behind_m:
        lat, lon = dest(lat, lon, g["facing"], behind_m)
    pts = []
    for k in range(0, 360 + step, step):
        t = math.radians(k)
        h = g["radius_m"] * math.cos(t)
        la, lo = dest(lat, lon, side if h >= 0 else (side + 180) % 360, abs(h))
        pts.append(f"{lo:.7f},{la:.7f},{g['alt_m'] + g['radius_m'] * math.sin(t):.1f}")
    return " ".join(pts)


def _gate_placemark(g):
    keys = ["lat", "lon", "alt_m", "radius_m", "facing", "to"]
    ext = "".join(f'<Data name="{k}"><value>{escape(str(round(g[k], 7) if isinstance(g[k], float) else g[k]))}</value></Data>'
                  for k in keys)
    return f'''  <Placemark>
    <name>{escape(g["name"])}</name>
    <description><![CDATA[{g["description"]}]]></description>
    <styleUrl>#gate</styleUrl>
    <ExtendedData><Data name="gate"><value>1</value></Data>{ext}</ExtendedData>
    <MultiGeometry>
      <LineString><tessellate>0</tessellate><altitudeMode>absolute</altitudeMode><coordinates>{_ring_coords(g)}</coordinates></LineString>
    </MultiGeometry>
  </Placemark>'''


def _back_placemark(g):
    return f'''  <Placemark>
    <name>{escape(g["name"])} (back)</name>
    <styleUrl>#gateBack</styleUrl>
    <LineString><tessellate>0</tessellate><altitudeMode>absolute</altitudeMode><coordinates>{_ring_coords(g, behind_m=BACK_OFFSET_M)}</coordinates></LineString>
  </Placemark>'''


def _label_folder(g):
    lat, lon = dest(g["lat"], g["lon"], (g["facing"] + 90) % 360, g["radius_m"] + LABEL_GAP_M)
    ft = round(g["alt_m"] / FT / 10) * 10
    desc = f"<![CDATA[{g['description']}]]>"
    half = 150.0
    dlat = math.degrees(half / R)
    dlon = math.degrees(half / (R * max(math.cos(math.radians(g["lat"])), 0.01)))
    lod = max(1, int(round(LOD_FT_PX / SHOW_NAMES_WITHIN_FT)))
    return f'''  <Folder>
    <name>{escape(g["name"])} name</name>
    <Region><LatLonAltBox><north>{g["lat"] + dlat:.8f}</north><south>{g["lat"] - dlat:.8f}</south><east>{g["lon"] + dlon:.8f}</east><west>{g["lon"] - dlon:.8f}</west><minAltitude>{g["alt_m"] - half:.1f}</minAltitude><maxAltitude>{g["alt_m"] + half:.1f}</maxAltitude><altitudeMode>absolute</altitudeMode></LatLonAltBox>
      <Lod><minLodPixels>{lod}</minLodPixels><maxLodPixels>-1</maxLodPixels></Lod></Region>
  <Placemark>
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
  </Placemark>
  </Folder>'''


def _blank_png():
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) + ch(b"IEND", b""))


def build_kml(title, gates):
    width = 10
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>{escape(title)}</name>
  <Style id="gate"><LineStyle><color>{GOLD}</color><width>{width}</width></LineStyle></Style>
  <Style id="gateName"><IconStyle><scale>1.0</scale><Icon><href>icons/blank.png</href></Icon></IconStyle><LabelStyle><color>{GOLD}</color><scale>1.4</scale></LabelStyle></Style>
  <Style id="gateAlt"><IconStyle><scale>1.0</scale><Icon><href>icons/blank.png</href></Icon></IconStyle><LabelStyle><color>ffffffff</color><scale>1.0</scale></LabelStyle></Style>
  <Style id="gateBack"><LineStyle><color>{RED}</color><width>{width}</width></LineStyle><BalloonStyle><displayMode>hide</displayMode></BalloonStyle></Style>
{chr(10).join(_gate_placemark(g) for g in gates)}
{chr(10).join(_label_folder(g) for g in gates)}
{chr(10).join(_back_placemark(g) for g in gates)}
</Document>
</kml>
'''


def safe_file_part(name):
    s = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return s[:40] or "Place"


def gate_file_name(name1, name2):
    return f"Gate_{safe_file_part(name1)}_{safe_file_part(name2)}.kmz"


def write_pair_kmz(path, name1, name2, gates):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    try:
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("doc.kml", build_kml(f"World Gate - {name1} <-> {name2}", gates))
            z.writestr("icons/blank.png", _blank_png())
        os.replace(partial, path)
    finally:
        if partial.exists():
            try:
                partial.unlink()
            except OSError:
                pass
    return path


# ---------------------------------------------------------------- settings
def load_settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def guess_gates_folder():
    """EarthStick's Gates folder if this tool sits in or next to the EarthStick folder."""
    here = Path(__file__).resolve().parent
    for cand in [here / "Gates", here.parent / "Gates"] + sorted(here.parent.glob("EarthStick*/Gates")):
        if cand.is_dir():
            return cand
    return None


# ---------------------------------------------------------------- window
def run_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog

    root = tk.Tk()
    root.title(f"{APP} {VERSION}")
    root.minsize(860, 560)
    settings = load_settings()
    gates_dir = tk.StringVar(value=settings.get("gates_folder") or str(guess_gates_folder() or ""))
    status = tk.StringVar(value="Fill in both places, then press MAKE GATES.")

    outer = ttk.Frame(root, padding=12)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="World Gate Maker", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w")
    ttk.Label(outer, text=f"v{VERSION}  -  two places, two golden rings: fly through one, come out at the other",
              font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w", padx=8)

    places = []
    for col, title in ((0, "Place 1"), (1, "Place 2")):
        f = ttk.LabelFrame(outer, text=title, padding=10)
        f.grid(row=1, column=col, sticky="nsew", padx=(0 if col == 0 else 6, 0), pady=10)
        v = dict(name=tk.StringVar(), lat=tk.StringVar(), lon=tk.StringVar(), elev=tk.StringVar(), readback=tk.StringVar())
        ttk.Label(f, text="Name").grid(row=0, column=0, sticky="w")
        ttk.Entry(f, textvariable=v["name"], width=28).grid(row=0, column=1, sticky="we", pady=2)
        ttk.Label(f, text="Latitude").grid(row=1, column=0, sticky="w")
        ttk.Entry(f, textvariable=v["lat"], width=28).grid(row=1, column=1, sticky="we", pady=2)
        ttk.Label(f, text="Longitude").grid(row=2, column=0, sticky="w")
        ttk.Entry(f, textvariable=v["lon"], width=28).grid(row=2, column=1, sticky="we", pady=2)

        def from_clip(v=v):
            try:
                lat, lon = parse_coordinates(root.clipboard_get())
            except tk.TclError:
                messagebox.showerror(APP, "The clipboard is empty."); return
            except ValueError as e:
                messagebox.showerror(APP, str(e)); return
            v["lat"].set(f"{lat:.6f}"); v["lon"].set(f"{lon:.6f}")
            v["readback"].set(_readback(lat, lon))

        ttk.Button(f, text="From Clipboard", command=from_clip).grid(row=3, column=1, sticky="w", pady=(2, 0))
        ttk.Label(f, textvariable=v["readback"], foreground="#555", wraplength=330).grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Label(f, text="Ground elev (ft)").grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(f, textvariable=v["elev"], width=12).grid(row=5, column=1, sticky="w", pady=(8, 0))
        ttk.Label(f, text="In ArcGIS Earth, put the mouse pointer on the spot and read 'elev' in the status bar.",
                  foreground="#555", wraplength=330).grid(row=6, column=0, columnspan=2, sticky="w")
        f.columnconfigure(1, weight=1)
        places.append(v)
    outer.columnconfigure(0, weight=1)
    outer.columnconfigure(1, weight=1)

    opts = ttk.Frame(outer)
    opts.grid(row=2, column=0, columnspan=2, sticky="we")
    agl = tk.StringVar(value=str(DEFAULT_AGL_FT))
    size = tk.StringVar(value=DEFAULT_SIZE)
    ttk.Label(opts, text="Height above ground (ft)").grid(row=0, column=0, sticky="w")
    ttk.Entry(opts, textvariable=agl, width=10).grid(row=0, column=1, sticky="w", padx=6)
    ttk.Label(opts, text="Ring size").grid(row=0, column=2, sticky="w", padx=(20, 4))
    for i, s in enumerate(SIZES):
        ttk.Radiobutton(opts, text=s, value=s, variable=size).grid(row=0, column=3 + i, sticky="w", padx=4)

    ttk.Label(opts, text="Save into (EarthStick Gates folder)").grid(row=1, column=0, sticky="w", pady=(10, 0))
    ttk.Label(opts, textvariable=gates_dir, foreground="#1a4fa0", wraplength=480).grid(row=1, column=1, columnspan=4, sticky="w", pady=(10, 0), padx=6)

    def choose_folder():
        d = filedialog.askdirectory(title="Choose the Gates folder inside your EarthStick folder",
                                    initialdir=gates_dir.get() or str(Path.home()))
        if d:
            gates_dir.set(d)
            settings["gates_folder"] = d
            save_settings(settings)

    ttk.Button(opts, text="Choose...", command=choose_folder).grid(row=1, column=5, sticky="w", pady=(10, 0))

    def make():
        try:
            vals = []
            for i, v in enumerate(places, 1):
                lat = parse_number(v["lat"].get(), f"Place {i} latitude")
                lon = parse_number(v["lon"].get(), f"Place {i} longitude")
                elev = parse_number(v["elev"].get(), f"Place {i} ground elev")
                vals.append((v["name"].get(), lat, lon, elev))
            h = parse_number(agl.get(), "Height above ground")
            gates, notes = make_pair(*vals[0], *vals[1], h, SIZES[size.get()])
        except ValueError as e:
            messagebox.showerror(APP, str(e)); return
        if not gates_dir.get():
            choose_folder()
            if not gates_dir.get():
                return
        folder = Path(gates_dir.get())
        if folder.name.lower() != "gates" and not messagebox.askyesno(
                APP, f"{folder}\nis not named 'Gates'. EarthStick only reads the Gates folder beside EarthStick.py.\n\nSave here anyway?"):
            return
        n1, n2 = vals[0][0].strip(), vals[1][0].strip()
        out = folder / gate_file_name(n1, n2)
        if out.exists() and not messagebox.askyesno(APP, f"{out.name} already exists in\n{folder}\n\nReplace it?",
                                                     icon="warning", default="no"):
            return
        try:
            write_pair_kmz(out, n1, n2, gates)
        except OSError as e:
            messagebox.showerror(APP, f"Could not save:\n{e}"); return
        settings["gates_folder"] = str(folder)
        save_settings(settings)
        g1, g2 = gates
        status.set(f"Saved {out.name} ({'; '.join(notes)}).")
        messagebox.showinfo(APP, f"Saved {out.name} in\n{folder}\n\n"
                            f"At {n1}: ring '{g1['name']}' - fly through at eye alt {round(g1['alt_m'] / FT / 10) * 10:,} ft.\n"
                            f"At {n2}: ring '{g2['name']}' - fly through at eye alt {round(g2['alt_m'] / FT / 10) * 10:,} ft.\n\n"
                            "1. Drag the file onto ArcGIS Earth to see the rings.\n"
                            "2. Restart EarthStick (it reads the Gates folder when it starts).\n"
                            "3. Fly through the gold side.\n\n" + "\n".join(notes))

    ttk.Button(outer, text="MAKE GATES", command=make).grid(row=3, column=0, columnspan=2, sticky="we", pady=(14, 4), ipady=6)
    ttk.Label(outer, textvariable=status, foreground="#333").grid(row=4, column=0, columnspan=2, sticky="w")
    root.mainloop()


# ---------------------------------------------------------------- self-test
def selftest():
    import tempfile
    import xml.dom.minidom
    import xml.etree.ElementTree as ET
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    lat, lon = parse_coordinates("30.40098, -81.93471")
    check("Google Maps clipboard text", (lat, lon) == (30.40098, -81.93471))
    check("N/W letters", parse_coordinates("30.4N 81.9W") == (30.4, -81.9))
    gates, notes = make_pair("Station 7", 30.3322, -81.6557, 20, "Hospital", 30.2867, -81.7259, 30, 500, 125.0)
    g1, g2 = gates
    check("ring at place 1 named for place 2", g1["name"] == "Hospital" and g1["to"] == "Station 7")
    check("ring at place 2 named for place 1", g2["name"] == "Station 7" and g2["to"] == "Hospital")
    check("rings face each other", abs((g1["facing"] - g2["facing"]) % 360 - 180) < 1)
    check("height = ground + above ground", abs(g1["alt_m"] - 520 * FT) < 0.01 and abs(g2["alt_m"] - 530 * FT) < 0.01)
    for bad, args in (("same names", ("A", 30, -81, 0, "a", 30.1, -81, 0, 500, 125.0)),
                      ("too low for ring", ("A", 30, -81, 0, "B", 30.1, -81, 0, 300, 225.0)),
                      ("too close", ("A", 30, -81, 0, "B", 30.001, -81, 0, 500, 125.0))):
        try:
            make_pair(*args); check(f"refuses {bad}", False)
        except ValueError:
            check(f"refuses {bad}", True)
    with tempfile.TemporaryDirectory() as d:
        p = write_pair_kmz(Path(d) / gate_file_name("Station 7", "Hospital"), "Station 7", "Hospital", gates)
        check("file name", p.name == "Gate_Station_7_Hospital.kmz")
        with zipfile.ZipFile(p) as z:
            kml = z.read("doc.kml").decode()
            check("KMZ has the blank icon", "icons/blank.png" in z.namelist())
        xml.dom.minidom.parseString(kml)
        ns = {"k": "http://www.opengis.net/kml/2.2"}
        pms = [pm for pm in ET.fromstring(kml).iter("{http://www.opengis.net/kml/2.2}Placemark")
               if pm.find("k:ExtendedData", ns) is not None]
        check("two gate placemarks with gate data", len(pms) == 2)
        check("two red backs and two near-only name folders", kml.count("(back)</name>") == 2 and kml.count("<Region>") == 2)
    print("\nAll checks passed." if ok else "\nSOME CHECKS FAILED.")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    run_gui()
