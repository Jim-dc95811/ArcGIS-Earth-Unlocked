"""World Gate Maker 2.0 - make your own pair of World Gates for EarthStick (1.3 or later).

2.0 Reference (Jim, 2026-11-08): the whole family moved to 2.0. World Gate Maker 2.0 = 1.2.2 TEST2 (live-tested
15:51: "running now" line, gates armed by EarthStick 2.0 with no restart) - gate files identical to 1.2.1.

1.2.2 TEST2 (Jim, 2026-11-08: 'if i have multiple versions of earthstick saved all over how do you know which
one I launched from?' + 'what if I have earthstick running now. dont I have to quit?') - gate files unchanged:
  a. saves into the EarthStick you actually fly: EarthStick 1.3.11+ leaves a note at startup
     (%LOCALAPPDATA%\\ArcGIS Earth Unlocked\\last_earthstick.txt) and World Gate Maker uses that Gates folder
     first; then the one used last time, then the newest EarthStick folder it can find nearby
  b. the line under 'Save into' says which EarthStick that is - running now, flown last, or found nearby -
     and turns RED with what to do when no EarthStick Gates folder is found
  c. Choose... only takes an EarthStick Gates folder: picking the EarthStick folder or its System Files folder
     is corrected to its Gates folder; any other folder is refused (no more 'save here anyway')
  d. with EarthStick 1.3.11+ running, the gates are armed and shown on the map within seconds - no restart;
     the 'Saved' message says so (older EarthStick: start or restart it, as before)

1.2.2 hardening (Jim approved 1-4, 2026-11-08) - the gate files it writes are unchanged:
  1. with several EarthStick folders side by side (EarthStick_v1.3.9 and EarthStick_v1.3.10 in Downloads) it now
     picks the NEWEST version for its Gates folder (1.2.1 sorted the names alphabetically and picked 1.3.9)
  2. a remembered Gates folder that no longer exists is not used (1.2.1 kept saving there and quietly re-created
     the deleted folder); it looks again and says so
  3. the Ground elev box also takes the status bar text as pasted, e.g. "elev 85 ft"
  4. sharp text on high-resolution / scaled screens (the window tells Windows it handles scaling)

Jim's idea (2026-11-04): two places (GPS coordinates + name), one height above ground,
and you get a pair of golden rings: the ring at place 1 takes you to place 2 and the
ring at place 2 brings you back. Each ring is named for where it takes you and faces
the other place. Same look as the World Gates pack: gold front, red back, name beside
the ring with the eye alt to fly at underneath (names only show when you are near).

1.1 (Jim, 2026-11-05): gates are drawn as SQUARES with four legs running back from the corners
(World Gates v21 look, 'a glass-top side table turned sideways') so the mouth of the gate and
which way it points show at a glance. The square fits inside the trigger circle (half-side =
radius / sqrt 2); legs are 1.42 x the radius (320 m on Large, like v21). Gate data unchanged.

The KMZ is saved into EarthStick's Gates folder. EarthStick 1.3.11+ picks it up while it runs (armed and shown
on the map); older EarthSticks read the Gates folder when they start, so restart them.

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
VERSION = "2.0"
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
SIZES = {"Small (70 m)": 50.0, "Medium (180 m)": 125.0, "Large (320 m)": 225.0}   # 1.1: label = square width; value = trigger radius in metres
DEFAULT_SIZE = "Medium (180 m)"
DEFAULT_AGL_FT = 500
MIN_CLEARANCE_M = 15.0     # lowest point of the ring must stay this far above the ground
LEG_PER_RADIUS = 320.0 / 225.0   # 1.1: legs scale with the gate (Large 225 m radius -> 320 m, as World Gates v21)
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
    t = re.sub(r"^\s*elev(?:ation)?\s*[:=]?\s*", "", t, flags=re.I)          # 1.2.2: "elev 85 ft" as pasted
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
        raise ValueError("The two places need different names (each gate is named for where it takes you).")
    validate_lat_lon(lat1, lon1)
    validate_lat_lon(lat2, lon2)
    if not radius_m > 0:
        raise ValueError("Choose a gate size.")
    if not -1500 <= elev1_ft <= 30000 or not -1500 <= elev2_ft <= 30000:
        raise ValueError("Ground elev looks wrong - use the 'elev' number (feet) from ArcGIS Earth's status bar.")
    min_agl_ft = math.ceil((radius_m + MIN_CLEARANCE_M) / FT / 10) * 10
    if agl_ft < min_agl_ft:
        raise ValueError(f"Height above ground must be at least {min_agl_ft:,} ft for this gate size, "
                         f"or the bottom of the gate would touch the ground.")
    d = distance_m(lat1, lon1, lat2, lon2)
    min_d = 2 * radius_m + GATE_EXIT_M + 200
    if d < min_d:
        raise ValueError(f"The places are only {d:,.0f} m apart - they must be at least {min_d:,.0f} m apart "
                         f"for this gate size.")
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


def _gate_pt(g, along_m, side_m, up_m):
    """Point relative to the gate centre: along = flight direction (+ = exit side), side = right as seen
    from the gold side, up = above the centre."""
    la, lo = g["lat"], g["lon"]
    if along_m:
        la, lo = dest(la, lo, g["facing"] if along_m > 0 else (g["facing"] + 180) % 360, abs(along_m))
    if side_m:
        la, lo = dest(la, lo, (g["facing"] + 90) % 360 if side_m > 0 else (g["facing"] + 270) % 360, abs(side_m))
    return f"{lo:.7f},{la:.7f},{g['alt_m'] + up_m:.1f}"


def _ls(coords):
    return f"<LineString><tessellate>0</tessellate><altitudeMode>absolute</altitudeMode><coordinates>{' '.join(coords)}</coordinates></LineString>"


def _square_corners(g):
    a = g["radius_m"] / math.sqrt(2.0)     # the square fits inside the trigger circle
    return [(-a, a), (a, a), (a, -a), (-a, -a)]


def _square_geoms(g, behind_m=0.0, legs=True):
    """Gold square frame facing the approach + four legs straight back from the corners: lined up,
    the legs make an even X; high, low or to one side, they lean and show which way to move."""
    c = _square_corners(g)
    out = _ls([_gate_pt(g, behind_m, s, u) for s, u in c + c[:1]])
    if legs:
        leg_m = g["radius_m"] * LEG_PER_RADIUS
        out += "".join(_ls([_gate_pt(g, 0, s, u), _gate_pt(g, leg_m, s, u)]) for s, u in c)
    return out


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
      {_square_geoms(g)}
    </MultiGeometry>
  </Placemark>'''


def _back_placemark(g):
    return f'''  <Placemark>
    <name>{escape(g["name"])} (back)</name>
    <styleUrl>#gateBack</styleUrl>
    {_square_geoms(g, behind_m=BACK_OFFSET_M, legs=False)}
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


def _es_version_key(gates):
    """1.2.2: EarthStick_v1.3.10/Gates sorts after EarthStick_v1.3.9/Gates (numbers, not letters); folder date breaks ties."""
    m = re.search(r"(\d+(?:\.\d+)*)", gates.parent.name)
    nums = tuple(int(x) for x in m.group(1).split(".")) if m else ()
    try:
        when = gates.parent.stat().st_mtime
    except OSError:
        when = 0.0
    return (nums, when)


def remembered_or_guess(settings):
    """1.2.2: the remembered Gates folder only if it still exists, else a fresh guess. Returns (folder_text, note)."""
    remembered = settings.get("gates_folder") or ""
    if remembered and Path(remembered).is_dir():
        return remembered, ""
    guess = guess_gates_folder()
    note = (f"The Gates folder used last time is gone ({remembered}). " if remembered else "")
    return (str(guess) if guess else ""), note


LAST_FLOWN_NOTE = ("ArcGIS Earth Unlocked", "last_earthstick.txt")   # TEST2: written by EarthStick 1.3.11+


def read_last_flown():
    """TEST2: EarthStick's note (dict: gates, version, started, picks_up_new_gates) or {} if none / unreadable."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    try:
        text = Path(base).joinpath(*LAST_FLOWN_NOTE).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    note = {}
    for line in text.splitlines():
        k, sep, v = line.partition("=")
        if sep:
            note[k.strip()] = v.strip()
    return note if note.get("gates") else {}


def earthstick_running():
    """TEST2: True/False on Windows (EarthStick 1.3.9+ holds a named mutex while it runs), None elsewhere."""
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
    except Exception:
        return None
    try:
        h = k32.OpenMutexW(0x00100000, False, "Local\\EarthStick_single_instance")   # SYNCHRONIZE
        if h:
            k32.CloseHandle(h)
            return True
        return False
    except Exception:
        return None


def is_gates_folder(p):
    return p.name.lower() == "gates" and p.is_dir()


def gates_folder_from_pick(picked):
    """TEST2 (Choose...): the EarthStick Gates folder for what was picked, or None. Picking the Gates folder,
    the EarthStick folder (has Gates inside) or its System Files folder (Gates beside it) all count."""
    p = Path(picked)
    if is_gates_folder(p):
        return p
    if (p / "Gates").is_dir():
        return p / "Gates"
    if p.name.lower() == "system files" and (p.parent / "Gates").is_dir():
        return p.parent / "Gates"
    return None


def start_folder(settings, note=None, running=None):
    """TEST2: where to save, and the line that says why. Returns (folder_text, line, ok)."""
    note = read_last_flown() if note is None else note
    flown = Path(note["gates"]) if note.get("gates") else None
    if flown is not None and is_gates_folder(flown):
        if running is None:
            running = earthstick_running()
        when = "running now" if running else f"flown last ({note.get('started', '').split(' ')[0] or 'earlier'})"
        return str(flown), f"EarthStick {note.get('version', '')} {when} - its Gates folder.".replace("  ", " "), True
    remembered = settings.get("gates_folder") or ""
    if remembered and is_gates_folder(Path(remembered)):
        return remembered, "The Gates folder you used last time.", True
    guess = guess_gates_folder()
    if guess is not None:
        return str(guess), f"Newest EarthStick found nearby ({guess.parent.name}). Start EarthStick once and this line names the one you fly.", True
    return "", ("EarthStick not found. Start EarthStick (Fly_ArcGIS_Earth.bat) once, then reopen World Gate Maker - "
                "or press Choose... and pick the Gates folder inside your EarthStick folder."), False


def make_dpi_aware():
    """1.2.2: sharp text on scaled (high-resolution) Windows screens. Harmless anywhere else."""
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def guess_gates_folder():
    """EarthStick's Gates folder if this tool sits in or next to the EarthStick folder."""
    here = Path(__file__).resolve().parent
    # 1.2: this file lives in "System Files" inside the World Gate Maker folder, so also look one level higher
    # (Downloads\EarthStick_v1.3.5\Gates next to Downloads\World_Gate_Maker_v1.2).
    top = here.parent if here.name == "System Files" else here
    cands = [here / "Gates", top / "Gates", top.parent / "Gates"]
    # newest EarthStick folder first (Downloads often holds several versions) - 1.2.2: by version NUMBER, then date
    cands += sorted(top.parent.glob("EarthStick*/Gates"), key=_es_version_key, reverse=True)
    cands += sorted(top.parent.parent.glob("EarthStick*/Gates"), key=_es_version_key, reverse=True)
    for cand in cands:
        if cand.is_dir():
            return cand
    return None


# ---------------------------------------------------------------- window
def run_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog

    make_dpi_aware()
    root = tk.Tk()
    root.title(f"{APP} {VERSION}")
    k = max(1.0, root.winfo_fpixels("1i") / 96.0)          # 1.2.2: screen scaling (2.0 at 200 %)
    root.minsize(int(860 * k), int(560 * k))
    settings = load_settings()
    start_dir, where_text, where_ok = start_folder(settings)
    gates_dir = tk.StringVar(value=start_dir)
    where = tk.StringVar(value=where_text)
    status = tk.StringVar(value="Fill in both places, then press MAKE GATES.")

    outer = ttk.Frame(root, padding=12)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="World Gate Maker", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w")
    ttk.Label(outer, text=f"v{VERSION}  -  two places, two golden gates: fly through one, come out at the other",
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
        ttk.Label(f, textvariable=v["readback"], foreground="#555", wraplength=int(330 * k)).grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Label(f, text="Ground elev (ft)").grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(f, textvariable=v["elev"], width=12).grid(row=5, column=1, sticky="w", pady=(8, 0))
        ttk.Label(f, text="In ArcGIS Earth, put the mouse pointer on the spot and read 'elev' in the status bar.",
                  foreground="#555", wraplength=int(330 * k)).grid(row=6, column=0, columnspan=2, sticky="w")
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
    ttk.Label(opts, text="Gate size").grid(row=0, column=2, sticky="w", padx=(20, 4))
    for i, s in enumerate(SIZES):
        ttk.Radiobutton(opts, text=s, value=s, variable=size).grid(row=0, column=3 + i, sticky="w", padx=4)

    ttk.Label(opts, text="Save into (EarthStick Gates folder)").grid(row=1, column=0, sticky="w", pady=(10, 0))
    ttk.Label(opts, textvariable=gates_dir, foreground="#1a4fa0", wraplength=int(480 * k)).grid(row=1, column=1, columnspan=4, sticky="w", pady=(10, 0), padx=6)
    where_label = ttk.Label(opts, textvariable=where, foreground="#2a6b2a" if where_ok else "#c00000",
                            wraplength=int(640 * k), font=("Segoe UI", 9, "normal" if where_ok else "bold"))
    where_label.grid(row=2, column=1, columnspan=5, sticky="w", padx=6)

    def set_where(text, ok):
        where.set(text)
        where_label.configure(foreground="#2a6b2a" if ok else "#c00000", font=("Segoe UI", 9, "normal" if ok else "bold"))

    def choose_folder():
        d = filedialog.askdirectory(title="Choose the Gates folder inside your EarthStick folder",
                                    initialdir=gates_dir.get() or str(Path.home()))
        if not d:
            return
        g = gates_folder_from_pick(d)
        if g is None:
            messagebox.showerror(APP, f"{d}\nis not an EarthStick Gates folder.\n\nOpen your EarthStick folder (the one with "
                                      "Fly_ArcGIS_Earth.bat) and pick the Gates folder inside it.")
            return
        gates_dir.set(str(g))
        set_where("The Gates folder you chose.", True)
        settings["gates_folder"] = str(g)
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
        if not folder.is_dir():                                     # 1.2.2: never re-create a deleted folder
            messagebox.showerror(APP, f"This Gates folder no longer exists:\n{folder}\n\nChoose the Gates folder inside your EarthStick folder.")
            gates_dir.set("")
            set_where("EarthStick not found - press Choose... and pick the Gates folder inside your EarthStick folder.", False)
            choose_folder()
            if not gates_dir.get():
                return
            folder = Path(gates_dir.get())
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
        note = read_last_flown()
        live = (earthstick_running() and note.get("picks_up_new_gates") == "yes"
                and Path(note.get("gates", "")).resolve() == folder.resolve())
        steps = ("EarthStick is running: within a few seconds it arms these gates and puts them on the map\n"
                 "(no restart, no dragging). Fly through the gold side.\n\n" if live else
                 "1. Start EarthStick (if it is already open, close its window and start it again).\n"
                 "   EarthStick 1.3.11 or later picks new gates up by itself and shows them on the map.\n"
                 "2. Fly through the gold side.\n\n")
        messagebox.showinfo(APP, f"Saved {out.name} in\n{folder}\n\n"
                            f"At {n1}: gate '{g1['name']}' - fly through at eye alt {round(g1['alt_m'] / FT / 10) * 10:,} ft.\n"
                            f"At {n2}: gate '{g2['name']}' - fly through at eye alt {round(g2['alt_m'] / FT / 10) * 10:,} ft.\n\n"
                            + steps + "\n".join(notes))

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
        lines = [pm.findall(".//k:LineString", ns) for pm in pms]
        check("each gate = square + 4 legs", all(len(ls) == 5 for ls in lines))
        sq = [c.split(",") for c in lines[0][0].find("k:coordinates", ns).text.split()]
        half = max(distance_m(g1["lat"], g1["lon"], float(p[1]), float(p[0])) for p in sq)
        check("square corners inside the trigger circle", half <= g1["radius_m"] + 0.5)
        leg = [c.split(",") for c in lines[0][1].find("k:coordinates", ns).text.split()]
        d_leg = distance_m(float(leg[0][1]), float(leg[0][0]), float(leg[1][1]), float(leg[1][0]))
        check("legs 1.42 x radius, on the exit side", abs(d_leg - 125.0 * LEG_PER_RADIUS) < 1.0
              and distance_m(float(leg[1][1]), float(leg[1][0]), g2["lat"], g2["lon"])
              < distance_m(float(leg[0][1]), float(leg[0][0]), g2["lat"], g2["lon"]))
    # 1.2.2 checks
    check("elev as pasted from the status bar", parse_number("elev 85 ft", "x") == 85.0 and parse_number("Elevation: 1,234'", "x") == 1234.0)
    with tempfile.TemporaryDirectory() as d:
        dl = Path(d) / "Downloads"
        sf = dl / "World_Gate_Maker_v1.2.2" / "System Files"; sf.mkdir(parents=True)
        for name in ("EarthStick_v1.3.6", "EarthStick_v1.3.9", "EarthStick_v1.3.10", "EarthStick_v1.3.8_TEST (1)"):
            (dl / name / "Gates").mkdir(parents=True)
        newest = max((dl.glob("EarthStick*/Gates")), key=_es_version_key)
        check("newest EarthStick by number (1.3.10, not 1.3.9)", newest.parent.name == "EarthStick_v1.3.10")
        gone = str(dl / "EarthStick_v1.3.4" / "Gates")
        folder, note = remembered_or_guess({"gates_folder": gone})
        check("a deleted remembered folder is not used", folder != gone and "gone" in note and not Path(gone).exists())
        here = str(dl / "EarthStick_v1.3.9" / "Gates")
        check("an existing remembered folder is kept", remembered_or_guess({"gates_folder": here}) == (here, ""))
    # TEST2 checks
    with tempfile.TemporaryDirectory() as d:
        dl = Path(d) / "Downloads"
        for name in ("EarthStick_v1.3.10", "EarthStick_v1.3.11_TEST"):
            (dl / name / "Gates").mkdir(parents=True); (dl / name / "System Files").mkdir()
        flown = dl / "EarthStick_v1.3.10" / "Gates"
        note = {"gates": str(flown), "version": "1.3.11 TEST", "started": "2026-11-08 15:00:00", "picks_up_new_gates": "yes"}
        folder, line, good = start_folder({}, note, running=True)
        check("the EarthStick you fly wins over the newest one", folder == str(flown) and good and "running now" in line)
        folder, line, good = start_folder({}, note, running=False)
        check("flown last (not running) says so", "flown last (2026-11-08)" in line)
        gone = dict(note, gates=str(dl / "EarthStick_v1.3.4" / "Gates"))
        folder, line, good = start_folder({"gates_folder": str(dl / "EarthStick_v1.3.11_TEST" / "Gates")}, gone, running=False)
        check("a note pointing at a deleted EarthStick is skipped", folder.endswith(str(Path("EarthStick_v1.3.11_TEST") / "Gates")))
        check("Choose: the Gates folder itself", gates_folder_from_pick(flown) == flown)
        check("Choose: the EarthStick folder -> its Gates", gates_folder_from_pick(flown.parent) == flown)
        check("Choose: System Files -> the Gates beside it", gates_folder_from_pick(flown.parent / "System Files") == flown)
        check("Choose: any other folder is refused", gates_folder_from_pick(dl) is None)
        saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = d
        try:
            p = Path(d) / "ArcGIS Earth Unlocked" / "last_earthstick.txt"
            check("no note = empty", read_last_flown() == {})
            p.parent.mkdir()
            p.write_text("program=EarthStick\nversion=1.3.11 TEST\ngates=" + str(flown) + "\npicks_up_new_gates=yes\nstarted=2026-11-08 15:00:00\n", encoding="utf-8")
            check("reads EarthStick's note", read_last_flown().get("gates") == str(flown))
        finally:
            if saved is None:
                os.environ.pop("LOCALAPPDATA", None)
            else:
                os.environ["LOCALAPPDATA"] = saved
    print("\nAll checks passed." if ok else "\nSOME CHECKS FAILED.")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    run_gui()
