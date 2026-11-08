"""Obstacle Course v1 - square hoops over Dark Jacksonville, a KMZ to see them, and a scorer.
Shared by Claude's runner (claude_flight.py course) and by people (Flight Recorder CSV -> score_csv)."""
import math, zipfile

R = 6371008.8
HALF = 75.0   # half the square's side (m): hoops are 150 m (~490 ft) across
# name, lat, lon, alt_m (sea level), facing (direction you fly through it)
HOOPS = [
    ("1 START",   30.3040, -81.6720, 150.0,  45.0),
    ("2",         30.3120, -81.6640, 120.0,  45.0),
    ("3 CLIMB",   30.3200, -81.6640, 200.0,   0.0),
    ("4 HIGH",    30.3280, -81.6620, 300.0,  20.0),
    ("5 DIVE",    30.3330, -81.6540,  80.0,  90.0),
    ("6 TURN",    30.3290, -81.6450, 100.0, 160.0),
    ("7 FINISH",  30.3220, -81.6400, 150.0, 200.0),
]


def dest(lat, lon, brg, d):
    la, lo, b = map(math.radians, (lat, lon, brg)); dd = d / R
    la2 = math.asin(math.sin(la) * math.cos(dd) + math.cos(la) * math.sin(dd) * math.cos(b))
    lo2 = lo + math.atan2(math.sin(b) * math.sin(dd) * math.cos(la), math.cos(dd) - math.sin(la) * math.sin(la2))
    return math.degrees(la2), math.degrees(lo2)


def enu(lat0, lon0, lat, lon):
    return (math.radians(lon - lon0) * R * math.cos(math.radians(lat0)), math.radians(lat - lat0) * R)


def kml():
    pm = []
    for i, (name, lat, lon, alt, fac) in enumerate(HOOPS):
        col = "ff00ff00" if i == 0 else "ffffffff" if i == len(HOOPS) - 1 else "ff00a5ff"
        l1, o1 = dest(lat, lon, fac - 90, HALF); l2, o2 = dest(lat, lon, fac + 90, HALF)
        ring = [(o1, l1, alt - HALF), (o2, l2, alt - HALF), (o2, l2, alt + HALF), (o1, l1, alt + HALF), (o1, l1, alt - HALF)]
        coords = " ".join(f"{x:.7f},{y:.7f},{z:.1f}" for x, y, z in ring)
        pm.append(f"""<Placemark><name>{name}</name><Style><LineStyle><color>{col}</color><width>6</width></LineStyle></Style>
<LineString><altitudeMode>absolute</altitudeMode><coordinates>{coords}</coordinates></LineString></Placemark>
<Placemark><name>{name}</name><Style><IconStyle><scale>0</scale></IconStyle><LabelStyle><color>{col}</color><scale>1.3</scale></LabelStyle></Style>
<Point><altitudeMode>absolute</altitudeMode><coordinates>{lon:.7f},{lat:.7f},{alt + HALF + 25:.1f}</coordinates></Point></Placemark>""")
    return ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Obstacle Course v1</name>'
            + "\n".join(pm) + "</Document></kml>")


def write_kmz(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml())


def score(points):
    """points = [(t, lon, lat, alt_m), ...] in flight order. Returns lines of text + hoops passed."""
    out, passed, nxt = [], 0, 0
    t_start = t_end = None
    for k in range(1, len(points)):
        if nxt >= len(HOOPS):
            break
        name, lat0, lon0, alt0, fac = HOOPS[nxt]
        n = (math.sin(math.radians(fac)), math.cos(math.radians(fac)))     # flight direction (east, north)
        s = (n[1], -n[0])                                                  # to the right
        (t0, x0, y0, z0), (t1, x1, y1, z1) = points[k - 1], points[k]
        e0, e1 = enu(lat0, lon0, y0, x0), enu(lat0, lon0, y1, x1)
        d0, d1 = e0[0] * n[0] + e0[1] * n[1], e1[0] * n[0] + e1[1] * n[1]
        if d0 < 0 <= d1:
            f = -d0 / (d1 - d0) if d1 != d0 else 0.0
            side = (e0[0] + (e1[0] - e0[0]) * f) * s[0] + (e0[1] + (e1[1] - e0[1]) * f) * s[1]
            up = z0 + (z1 - z0) * f - alt0
            tc = t0 + (t1 - t0) * f
            ok = abs(side) <= HALF and abs(up) <= HALF
            verdict = "THROUGH" if ok else "MISSED"
            out.append(f"Hoop {name:9s} {verdict:7s} {abs(side):5.0f} m {'right' if side > 0 else 'left '} {abs(up):5.0f} m {'high' if up > 0 else 'low '}  at {tc:6.1f} s")
            passed += ok
            if nxt == 0: t_start = tc
            if nxt == len(HOOPS) - 1: t_end = tc
            nxt += 1
    for name, *_ in HOOPS[nxt:]:
        out.append(f"Hoop {name:9s} NOT REACHED")
    if t_start is not None and t_end is not None:
        out.append(f"Course time START -> FINISH: {t_end - t_start:.1f} s")
    out.append(f"SCORE: {passed} / {len(HOOPS)} hoops")
    return out, passed


def score_csv(path):
    """Score a Flight Recorder CSV (columns t_s, lon, lat, alt_m)."""
    import csv
    with open(path, newline="", encoding="utf-8") as fh:
        pts = [(float(r["t_s"]), float(r["lon"]), float(r["lat"]), float(r["alt_m"])) for r in csv.DictReader(fh)]
    return score(pts)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1].endswith(".csv"):
        print("\n".join(score_csv(sys.argv[1])[0]))
    else:
        write_kmz("Obstacle_Course_v1.kmz"); print("wrote Obstacle_Course_v1.kmz")
