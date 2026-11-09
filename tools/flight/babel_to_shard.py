"""Babel to the Shard - a recordable flight for a YouTube Short (Claude, 2026-11-08).

Opens close on the treadwheel crane in Bruegel's Tower of Babel (1563, World spot 1), pulls up to the whole
painting, crosses 60 miles east over the ocean and dives onto the Shard and its red tower cranes in the London
panorama (World spot 2). Clock-timed (the plan's seconds are the flown seconds), eased, 20 updates a second.
Touch the mouse or the stick and Claude lets go at once.

  py babel_to_shard.py            fly it (96 s)
  py babel_to_shard.py home       park on the opening view (both worlds)
  py babel_to_shard.py read       print the camera only
"""
import builtins, json, math, sys, time, urllib.request
from pathlib import Path

_LOG = open(Path(__file__).resolve().parent.parent / "flight_log.txt", "a", encoding="utf-8")
_print = builtins.print
def print(*a, **k):
    _print(*a, **k); k.pop("file", None); _print(*a, file=_LOG, **k); _LOG.flush()

CAMERA_URL = "http://localhost:8000/arcgisearth/camera"
_OPEN = urllib.request.build_opener(urllib.request.ProxyHandler({}))
R = 6378137.0


def call(method, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(CAMERA_URL, data=data, method=method,
                                 headers={"Accept": "application/json", "Content-Type": "application/json"})
    with _OPEN.open(req, timeout=2) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def picture_point(spot_lon, width_px, height_px, px, py):
    """Picture World Maker placement: 1 px = 1 Web Mercator metre, picture centred on (30 N, spot_lon)."""
    cx = math.radians(spot_lon) * R
    cy = R * math.log(math.tan(math.pi / 4 + math.radians(30.0) / 2))
    x = cx - width_px / 2 + px
    y = cy + height_px / 2 - py
    return math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2), math.degrees(x / R)


# What we look at (picture pixels -> lat, lon)
CRANE = picture_point(-80.0, 30000, 21952, 21000, 10750)    # Bruegel's treadwheel crane, men inside the wheel
BABEL = picture_point(-80.0, 30000, 21952, 15000, 10976)    # the whole painting
SHARD = picture_point(-79.0, 50000, 12006, 45050, 2000)     # the whole Shard (spire at px y 250, foot at 3700)
CRANES = picture_point(-79.0, 50000, 12006, 44300, 2500)    # its red tower cranes, left of the Shard


def camera_for(lat, lon, z, heading, tilt):
    """Camera that looks at (lat, lon) on the picture from height z, at this heading and tilt."""
    back = z * math.tan(math.radians(tilt))                    # stand back so the target is mid-screen
    b = math.radians(heading + 180)
    dlat = back * math.cos(b) / 6371008.8
    dlon = back * math.sin(b) / (6371008.8 * math.cos(math.radians(lat)))
    return {"position": {"x": lon + math.degrees(dlon), "y": lat + math.degrees(dlat), "z": z,
                         "spatialReference": {"wkid": 4326}}, "heading": heading % 360, "tilt": tilt, "roll": 0.0}


def ease(f):
    return (1 - math.cos(math.pi * max(0.0, min(1.0, f)))) / 2


# (seconds, look-at lat, lon, height m, heading, tilt, how to get there)
OVERVIEW = (30.0, -79.5)                                     # both worlds on the ocean

PLAN = [   # take 3: twice as long as take 2 (Jim)
    (0.0,  *OVERVIEW, 140000, 0,  0, "start"),     # both pictures floating on the ocean
    (12.0,  *BABEL,     26000, 0,  0, "log"),       # zoom into Babel
    (26.0, *CRANE,       550, 0, 20, "log"),       # down onto Bruegel's crane (men walking inside the wheel)
    (34.0, *CRANE,       470, 0, 20, "ease"),      # hold, slow push in
    (64.0, *SHARD,      4500, 0, 10, "hop"),       # climb out, 60 miles east over the ocean, dive: the whole Shard
    (74.0, *SHARD,      3300, 0, 15, "log"),       # settle on the Shard
    (88.0, *CRANES,     1100, 0, 22, "log"),       # down to its red tower cranes
    (96.0, *CRANES,      950, 0, 22, "ease"),      # hold
]


def at(t):
    for (t0, la0, lo0, z0, h0, ti0, _), (t1, la1, lo1, z1, h1, ti1, how) in zip(PLAN, PLAN[1:]):
        if t <= t1:
            f = ease((t - t0) / (t1 - t0))
            la, lo = la0 + (la1 - la0) * f, lo0 + (lo1 - lo0) * f
            if how == "ease":
                z = z0 + (z1 - z0) * f
            elif how == "log":
                z = math.exp(math.log(z0) + (math.log(z1) - math.log(z0)) * f)
            else:                                   # hop: up and over, then down
                bump = math.log(85000 / math.sqrt(z0 * z1))
                z = math.exp(math.log(z0) + (math.log(z1) - math.log(z0)) * f + bump * math.sin(math.pi * f))
            return camera_for(la, lo, z, h0 + (h1 - h0) * f, ti0 + (ti1 - ti0) * f)
    last = PLAN[-1]
    return camera_for(last[1], last[2], last[3], last[4], last[5])


def touched(now, sent):
    dz = abs(now["position"]["z"] - sent["position"]["z"])
    dpos = max(abs(now["position"]["x"] - sent["position"]["x"]), abs(now["position"]["y"] - sent["position"]["y"]))
    dh = abs(((now.get("heading", 0) - sent.get("heading", 0) + 540) % 360) - 180)
    z = sent["position"]["z"]
    return dh > 2.0 or dz > max(15.0, 0.03 * z) or dpos > max(2e-4, 0.02 * z / 111000)


def fly(hz=20.0):
    total = PLAN[-1][0]
    print(f"Babel to the Shard - {total:.0f} s. Crane {CRANE[0]:.6f},{CRANE[1]:.6f}  Shard {SHARD[0]:.6f},{SHARD[1]:.6f}")
    sent = at(0.0); call("PUT", sent); time.sleep(0.3)          # already parked there by 'home' (no jump)
    t0 = time.monotonic()
    while True:
        t = time.monotonic() - t0
        now = call("GET")
        if touched(now, sent):
            print(f"Someone else moved the camera at {t:.1f} s - Claude lets go. Your plane."); return
        if t >= total:
            break
        sent = at(t); call("PUT", sent)
        time.sleep(max(0.0, (t0 + (int(t * hz) + 1) / hz) - time.monotonic()))
    sent = at(total); call("PUT", sent)
    p = call("GET")["position"]
    print(f"Landed after {time.monotonic() - t0:.1f} s at {p['y']:.6f},{p['x']:.6f}, {p['z'] * 3.28084:,.0f} ft (planned {total:.0f} s)")


if __name__ == "__main__":
    if sys.argv[1:] == ["home"]:                                # park on the first frame before recording starts
        call("PUT", at(0.0)); time.sleep(1.0); call("PUT", at(0.0)); print("Parked on the opening view.")
    elif sys.argv[1:] == ["read"]:
        c = call("GET"); p = c["position"]
        print(f"Camera: {p['y']:.6f},{p['x']:.6f} {p['z'] * 3.28084:,.0f} ft heading {c.get('heading', 0):.1f} tilt {c.get('tilt', 0):.1f}")
    else:
        fly()
