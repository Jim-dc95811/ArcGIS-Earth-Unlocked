"""City beacons for World Gates (Jim, 2026-11-03): one red beacon KMZ per World Gates city. Double-click it in
ArcGIS Earth's Data list to go straight there, skipping the gates. The beacon (red line, 3 km tall, same
form as the Object Factory beacon) stands on the landmark; its LookAt puts you at the gate arrival spot,
at arrival height, facing the landmark.

python3 build_city_beacons.py <output folder>
"""
import math, runpy, sys, tempfile, zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_argv = sys.argv
sys.argv = ["build_world_gates.py", str(Path(tempfile.mkdtemp()) / "gates.kmz")]
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    W = runpy.run_path(str(HERE / "build_world_gates.py"))
sys.argv = _argv
dest = W["dest"]

TILT, RANGE = 80.0, 1000.0


def beacon_kmz(path, title, lat, lon, eye):
    elat, elon, ealt, head = eye
    tlat, tlon = dest(elat, elon, head, RANGE * math.sin(math.radians(TILT)))
    talt = ealt - RANGE * math.cos(math.radians(TILT))
    n = escape(title)
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{n}</name>
    <Style id="beaconStyle">
      <LineStyle><color>ff0000ff</color><width>6</width></LineStyle>
      <IconStyle><scale>1.1</scale></IconStyle>
    </Style>
    <Placemark>
      <name>{n}</name>
      <LookAt><longitude>{tlon:.8f}</longitude><latitude>{tlat:.8f}</latitude><altitude>{talt:.1f}</altitude><heading>{head:.1f}</heading><tilt>{TILT:g}</tilt><range>{RANGE:g}</range><altitudeMode>absolute</altitudeMode></LookAt>
      <styleUrl>#beaconStyle</styleUrl>
      <MultiGeometry>
        <Point><altitudeMode>relativeToGround</altitudeMode><coordinates>{lon:.8f},{lat:.8f},0</coordinates></Point>
        <LineString><tessellate>0</tessellate><altitudeMode>relativeToGround</altitudeMode><coordinates>
          {lon:.8f},{lat:.8f},0
          {lon:.8f},{lat:.8f},3000.000
        </coordinates></LineString>
      </MultiGeometry>
    </Placemark>
  </Document>
</kml>
'''
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)


out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
items = [("Jacksonville (JAX)", *W["JIA"], (W["alat"], W["alon"], W["JAX_LEVEL"], W["back_jax"])),
         ("Atlanta (ATL)", *W["ATL"], (*W["ATL"], W["LEVEL"], W["HUB_ARRIVAL_HEADING"]))]
items += [(W["CITY"][c], W["DEST"][c][0], W["DEST"][c][1], W["arrival"][c]) for c in W["TOUR"]]
for i, (title, lat, lon, eye) in enumerate(items, 1):
    f = out / f"{i:02d}_Beacon_{title.split(' (')[0].replace(' ', '_')}.kmz"
    beacon_kmz(f, f"Go to {title}", lat, lon, eye)
    print(f.name, f"eye {eye[0]:.4f},{eye[1]:.4f} {round(eye[2] / 0.3048):,} ft heading {eye[3]:.0f}")
