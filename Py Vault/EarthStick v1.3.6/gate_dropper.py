"""Gate Dropper for EarthStick 1.3.6 (TEST2: gates face the way you were looking; TEST3: 500 m in front of you;
TEST5: thin black, bigger opening, wide grab zone) (Jim, 2026-11-06: 'manually entering that info is a huge pain ...
I would love to automate that procedure').

Fly to a place, hover, press Button 2 = mark 1. Fly to a second place, press Button 2 = mark 2:
EarthStick writes a pair of World Gates there (the gate at mark 1 leads to mark 2 and back) into the
Gates folder, at exactly the height you were hovering, and arms them at once.

The drawing code below is copied unchanged from World Gate Maker 1.2 (gate_maker/System Files/
World_Gate_Maker.py), so a dropped gate looks exactly like a World Gate Maker gate: gold square with
legs, red back, name beside it with the eye alt to fly at underneath. Standard library only.
"""
import math
import os
import re
import struct
import zipfile
import zlib
from pathlib import Path
from xml.sax.saxutils import escape

FT = 0.3048
R = 6371008.8
GOLD = "ff00d7ff"
RED = "ff0000ff"
BACK_OFFSET_M = 10.0
LABEL_GAP_M = 40.0
ALT_LINE_DROP_M = 130.0
SHOW_NAMES_WITHIN_FT = 20000.0
LOD_FT_PX = 1_790_000.0
GATE_EXIT_M = 300.0
LEG_PER_RADIUS = 320.0 / 225.0

DROP_RADIUS_M = 300.0          # TEST5: bigger opening (square about 425 m across); TEST-TEST4 used Medium 125
DROP_LOCK_CAPTURE_M = 2000 * 0.3048   # TEST5: lock on from up to 2,000 ft above or below the gate
DROP_LOCK_RANGE_M = 3000.0     # TEST5: ...and from 3 km out
DROP_LINE = "ff000000"         # TEST5: black lines (KML aabbggrr) instead of gold
DROP_LINE_WIDTH = 4            # TEST5: thinner (World Gate Maker draws 10)
DROP_NAME = "ffffffff"         # TEST5: white names instead of gold
DROP_FILE_PREFIX = "Dropped_Gate_"
DROP_AHEAD_M = 500.0           # TEST3: the gate appears this far in front of you, so you just push forward


# ---------------------------------------------------------------- copied from World Gate Maker 1.2
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


# ---------------------------------------------------------------- Gate Dropper
def min_apart_m(radius_m=DROP_RADIUS_M):
    """Same rule as World Gate Maker: room for both gates plus the 300 m arrival."""
    return 2 * radius_m + GATE_EXIT_M + 200


def next_number(folder):
    nums = [int(m.group(1)) for f in Path(folder).glob(DROP_FILE_PREFIX + "*.kmz")
            if (m := re.fullmatch(re.escape(DROP_FILE_PREFIX) + r"(\d+)\.kmz", f.name))]
    return max(nums, default=0) + 1


def _dropped_placemark(g):
    """TEST2: like World Gate Maker's gate placemark, but a one-way gate with its own landing spot."""
    keys = ["lat", "lon", "alt_m", "radius_m", "facing", "dest_lat", "dest_lon", "dest_alt_m", "dest_heading",
            "lock_capture_m", "lock_range_m"]
    ext = "".join(f'<Data name="{k}"><value>{round(g[k], 7)}</value></Data>' for k in keys)
    return f'''  <Placemark>
    <name>{escape(g["name"])}</name>
    <description><![CDATA[{g["description"]}]]></description>
    <styleUrl>#gate</styleUrl>
    <ExtendedData><Data name="gate"><value>1</value></Data>{ext}</ExtendedData>
    <MultiGeometry>
      {_square_geoms(g)}
    </MultiGeometry>
  </Placemark>'''


def drop_pair(folder, mark1, mark2, radius_m=DROP_RADIUS_M):
    """mark = (lat, lon, alt_m sea level, heading). Writes Dropped_Gate_NN.kmz into folder; returns its path.
    TEST2 (Jim: the gate in Babel faced 90 degrees away): each gate faces the way you were LOOKING when you
    marked it, and going through it lands you 300 m past the other gate, looking the way you looked when
    you marked that one (gate behind you, so no bounce back). Places are named 'Drop NN A' (mark 1) and
    'Drop NN B' (mark 2); each gate is named for where it takes you."""
    (lat1, lon1, alt1, hd1), (lat2, lon2, alt2, hd2) = mark1, mark2
    # TEST3 (Jim: TEST2 'is impossible' - the way in was behind you): each gate stands DROP_AHEAD_M in front
    # of where you pressed, at your height, facing the way you looked - so you just push forward into it.
    lat1, lon1 = dest(lat1, lon1, hd1 % 360, DROP_AHEAD_M)
    lat2, lon2 = dest(lat2, lon2, hd2 % 360, DROP_AHEAD_M)
    if distance_m(lat1, lon1, lat2, lon2) < min_apart_m(radius_m):
        raise ValueError(f"the two marks must be at least {min_apart_m(radius_m):,.0f} m apart")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    n = next_number(folder)
    a, b = f"Drop {n:02d} A", f"Drop {n:02d} B"

    def gate(name, lat, lon, alt, facing, to_lat, to_lon, to_alt, to_heading):
        ft = round(alt / FT / 10) * 10
        dlat, dlon = dest(to_lat, to_lon, to_heading % 360, GATE_EXIT_M)
        return dict(name=name, to="", lat=lat, lon=lon, alt_m=alt, facing=facing % 360, radius_m=radius_m,
                    lock_capture_m=DROP_LOCK_CAPTURE_M, lock_range_m=DROP_LOCK_RANGE_M,
                    dest_lat=dlat, dest_lon=dlon, dest_alt_m=to_alt, dest_heading=to_heading % 360,
                    description=f"<b>Gate to {escape(name)}</b><br/>Fly through the gold side at eye alt {ft:,} ft.")
    gates = [gate(b, lat1, lon1, alt1, hd1, lat2, lon2, alt2, hd2),
             gate(a, lat2, lon2, alt2, hd2, lat1, lon1, alt1, hd1)]
    path = folder / f"{DROP_FILE_PREFIX}{n:02d}.kmz"
    partial = path.with_name(path.name + ".partial")
    kml = build_kml(f"Dropped Gate {n:02d} - {a} <-> {b}", gates)
    # TEST5: thin black lines (red back kept, thinner) and white names - quieter over a painting
    kml = kml.replace(f'<Style id="gate"><LineStyle><color>{GOLD}</color><width>10</width>',
                      f'<Style id="gate"><LineStyle><color>{DROP_LINE}</color><width>{DROP_LINE_WIDTH}</width>')
    kml = kml.replace(f'<Style id="gateBack"><LineStyle><color>{RED}</color><width>10</width>',
                      f'<Style id="gateBack"><LineStyle><color>{RED}</color><width>{DROP_LINE_WIDTH}</width>')
    kml = kml.replace(f'<LabelStyle><color>{GOLD}</color><scale>1.4</scale>', f'<LabelStyle><color>{DROP_NAME}</color><scale>1.4</scale>')
    for g in gates:                                   # one-way gates with their own landing spot
        old = _gate_placemark(g)
        assert old in kml
        kml = kml.replace(old, _dropped_placemark(g))
    try:
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("doc.kml", kml)
            z.writestr("icons/blank.png", _blank_png())
        os.replace(partial, path)
    finally:
        if partial.exists():
            try:
                partial.unlink()
            except OSError:
                pass
    return path

