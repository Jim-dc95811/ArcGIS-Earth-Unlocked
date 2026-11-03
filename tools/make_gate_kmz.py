"""Make a wormhole gate KMZ for EarthStick 1.3+ (golden vertical rings + gate data).

Each gate is a vertical ring (thick gold LineString circle, altitudeMode absolute so it
matches the camera altitude EarthStick reads) plus a label point, with ExtendedData
that EarthStick reads from its Gates folder:
  gate=1, lat, lon, alt_m (absolute), radius_m, facing (compass direction you fly to go
  through), and either to=<partner gate name> or dest_lat/dest_lon/dest_alt_m/dest_heading.

Use from Python:
    from make_gate_kmz import gate, write_kmz
    write_kmz("Gates.kmz", "My gates", [gate("NYC", 30.32, -81.65, 457, facing=28.7, to="JAX"), ...])
"""
import math
import struct
import zipfile
import zlib
from xml.sax.saxutils import escape

R = 6371008.8
GOLD = "ff00d7ff"   # KML aabbggrr for #FFD700


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


def _ring_coords(g, step=5):
    side = (g["facing"] + 90) % 360
    pts = []
    for k in range(0, 360 + step, step):
        t = math.radians(k)
        h = g["radius_m"] * math.cos(t)
        la, lo = dest(g["lat"], g["lon"], side if h >= 0 else (side + 180) % 360, abs(h))
        pts.append(f"{lo:.7f},{la:.7f},{g['alt_m'] + g['radius_m'] * math.sin(t):.1f}")
    return " ".join(pts)


def _placemark(g):
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
      <Point><altitudeMode>absolute</altitudeMode><coordinates>{g["lon"]:.7f},{g["lat"]:.7f},{g["alt_m"] + g["radius_m"] + 40:.1f}</coordinates></Point>
      <LineString><tessellate>0</tessellate><altitudeMode>absolute</altitudeMode><coordinates>{_ring_coords(g)}</coordinates></LineString>
    </MultiGeometry>
  </Placemark>'''


def _blank_png():
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) + ch(b"IEND", b""))


def write_kmz(path, title, gates, width=10):
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>{escape(title)}</name>
  <Style id="gate">
    <LineStyle><color>{GOLD}</color><width>{width}</width></LineStyle>
    <IconStyle><scale>1.0</scale><Icon><href>icons/blank.png</href></Icon></IconStyle>
    <LabelStyle><color>{GOLD}</color><scale>2.0</scale></LabelStyle>
  </Style>
{chr(10).join(_placemark(g) for g in gates)}
</Document>
</kml>'''
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)
        z.writestr("icons/blank.png", _blank_png())
    return path
