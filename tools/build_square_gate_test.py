"""Square gate test (Jim, 2026-11-05): 'the very shape of the ring is the problem ... a square gate with
90-degree legs, like a glass-top side table turned sideways - the shape gives the visual clue.'

One gate only (Jim: 'concentrate on 1 ring until we get it right'): the London gate at the ATL hub, with
exactly the v19 London-hub gate data, so the wormhole is unchanged. Drawn as:
  * a gold SQUARE frame facing the approach, sized to fit inside the gate's trigger circle
    (half-side = radius / sqrt 2, so every point inside the square really fires the gate);
  * four gold LEGS from the corners straight back along the flight direction (the table legs).
    Lined up, you look straight down the legs and they close in evenly on the centre; high, low or off to
    one side, the legs tilt and show which way to move;
  * a red square just behind (the wrong side), as the rings have;
  * the name and eye-alt line beside it (shown within ~4 miles), as v19.

Run:  python3 build_square_gate_test.py OUT.kmz [leg_length_m]
"""
import math
import sys
import zipfile
from xml.sax.saxutils import escape

from make_gate_kmz import dest, gate, GOLD, RED, _label_placemarks, _blank_png, lod_folder

VERSION = "v1"
LONDON_HUB = gate("London", 33.66767961091173, -84.4277, 769.9248, facing=0.0, radius_m=225.0,
                  dest_lat=51.51040264379737, dest_lon=-0.09866623619256377, dest_alt_m=457.0,
                  dest_heading=108.71672052752865)
SHOW_WITHIN_FT = 20000.0


def _pt(g, along_m, side_m, up_m):
    """Point relative to the gate centre: along = in the flight direction (+ = exit side), side = to the
    right seen from the gold side, up = above the centre."""
    la, lo = g["lat"], g["lon"]
    if along_m:
        la, lo = dest(la, lo, g["facing"] if along_m > 0 else (g["facing"] + 180) % 360, abs(along_m))
    if side_m:
        la, lo = dest(la, lo, (g["facing"] + 90) % 360 if side_m > 0 else (g["facing"] + 270) % 360, abs(side_m))
    return f"{lo:.7f},{la:.7f},{g['alt_m'] + up_m:.1f}"


def _line(coords):
    return f"<LineString><tessellate>0</tessellate><altitudeMode>absolute</altitudeMode><coordinates>{' '.join(coords)}</coordinates></LineString>"


def square_gate_kml(g, leg_m):
    a = g["radius_m"] / math.sqrt(2.0)                      # half-side: the square fits inside the trigger circle
    corners = [(-a, a), (a, a), (a, -a), (-a, -a)]
    frame = _line([_pt(g, 0, s, u) for s, u in corners + corners[:1]])
    legs = "".join(_line([_pt(g, 0, s, u), _pt(g, leg_m, s, u)]) for s, u in corners)
    back = _line([_pt(g, 10.0, s, u) for s, u in corners + corners[:1]])
    keys = ["lat", "lon", "alt_m", "radius_m", "facing", "to", "dest_lat", "dest_lon", "dest_alt_m", "dest_heading"]
    ext = "".join(f'<Data name="{k}"><value>{escape(str(g[k]))}</value></Data>' for k in keys)
    return f'''  <Placemark>
    <name>{escape(g["name"])}</name>
    <styleUrl>#gate</styleUrl>
    <ExtendedData><Data name="gate"><value>1</value></Data>{ext}</ExtendedData>
    <MultiGeometry>{frame}{legs}</MultiGeometry>
  </Placemark>
  <Placemark>
    <name>{escape(g["name"])} (back)</name>
    <styleUrl>#gateBack</styleUrl>
    {back}
  </Placemark>'''


def write(path, leg_m=640.0):
    g = LONDON_HUB
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>Square Gate Test {VERSION} - London at ATL</name>
  <Style id="gate"><LineStyle><color>{GOLD}</color><width>10</width></LineStyle></Style>
  <Style id="gateName"><IconStyle><scale>1.0</scale><Icon><href>icons/blank.png</href></Icon></IconStyle><LabelStyle><color>{GOLD}</color><scale>1.4</scale></LabelStyle></Style>
  <Style id="gateAlt"><IconStyle><scale>1.0</scale><Icon><href>icons/blank.png</href></Icon></IconStyle><LabelStyle><color>ffffffff</color><scale>1.0</scale></LabelStyle></Style>
  <Style id="gateBack"><LineStyle><color>{RED}</color><width>10</width></LineStyle><BalloonStyle><displayMode>hide</displayMode></BalloonStyle></Style>
{square_gate_kml(g, leg_m)}
{lod_folder(g["name"] + " name", _label_placemarks(g), g["lat"], g["lon"], g["alt_m"], SHOW_WITHIN_FT)}
</Document>
</kml>'''
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)
        z.writestr("icons/blank.png", _blank_png())
    return path


if __name__ == "__main__":
    write(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 640.0)
