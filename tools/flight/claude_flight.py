"""Claude Flight Test v0.1 - Claude's first hands on the ArcGIS Earth camera.

  py claude_flight.py read        read the camera once and print it (moves nothing)
  py claude_flight.py turn [deg]  slow turn in place (default 30 degrees over ~10 s), same API as EarthStick
Touch the mouse or EarthStick during a turn and Claude lets go at once.
"""
import builtins, json, math, sys, time, urllib.request
from pathlib import Path

_LOG = open(Path(__file__).resolve().parent.parent / "flight_test_log.txt", "a", encoding="utf-8")
_print = builtins.print
def print(*a, **k):
    _print(*a, **k)
    k.pop("file", None); _print(*a, file=_LOG, **k); _LOG.flush()


CAMERA_URL = "http://localhost:8000/arcgisearth/camera"
_OPEN = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # localhost: never via a proxy


def call(method, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(CAMERA_URL, data=data, method=method,
                                 headers={"Accept": "application/json", "Content-Type": "application/json"})
    with _OPEN.open(req, timeout=2) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def show(cam):
    p = cam["position"]
    print(f"  lat {p['y']:.6f}  lon {p['x']:.6f}  height {p['z'] * 3.28084:,.0f} ft  "
          f"heading {cam.get('heading', 0):.1f}  tilt {cam.get('tilt', 0):.1f}  roll {cam.get('roll', 0):.1f}")


def turn(deg=30.0, seconds=10.0, hz=20.0):
    cam = call("GET")
    print("Starting point:"); show(cam)
    start_h = cam.get("heading", 0.0)
    n = int(seconds * hz)
    sent = cam
    for i in range(1, n + 1):
        now = call("GET")
        if (abs(((now.get("heading", 0) - sent.get("heading", 0) + 540) % 360) - 180) > 2.0
                or abs(now["position"]["z"] - sent["position"]["z"]) > 5.0
                or abs(now["position"]["x"] - sent["position"]["x"]) > 1e-4
                or abs(now["position"]["y"] - sent["position"]["y"]) > 1e-4):
            print("\nSomeone else moved the camera - Claude lets go. Your plane.")
            return
        ease = (1 - math.cos(math.pi * i / n)) / 2          # gentle start, gentle stop
        nxt = dict(cam)
        nxt["position"] = dict(cam["position"])
        nxt["heading"] = (start_h + deg * ease) % 360
        call("PUT", nxt)
        sent = nxt
        time.sleep(1.0 / hz)
    print("Finished:"); show(call("GET"))


def dest(lat, lon, brg, d):
    R = 6371008.8
    la, lo, b = map(math.radians, (lat, lon, brg)); dd = d / R
    la2 = math.asin(math.sin(la) * math.cos(dd) + math.cos(la) * math.sin(dd) * math.cos(b))
    lo2 = lo + math.atan2(math.sin(b) * math.sin(dd) * math.cos(la), math.cos(dd) - math.sin(la) * math.sin(la2))
    return math.degrees(la2), math.degrees(lo2)


def orbit(degrees=360.0, seconds=60.0, hz=20.0):
    """Circle the spot in the middle of the screen, always looking at it (eased start and stop)."""
    cam = call("GET")
    print("Starting point:"); show(cam)
    p = cam["position"]; h0 = cam.get("heading", 0.0); tilt = cam.get("tilt", 0.0)
    height_m = max(p["z"] - 2.0, 20.0)
    radius = min(height_m * math.tan(math.radians(min(tilt, 80.0))), 3000.0)
    tlat, tlon = dest(p["y"], p["x"], h0, radius)            # the spot under the screen centre
    print(f"Orbiting the spot {radius:,.0f} m ahead ({tlat:.6f}, {tlon:.6f}), {degrees:.0f} degrees in {seconds:.0f} s")
    n = int(seconds * hz); sent = cam
    for i in range(1, n + 1):
        now = call("GET")
        if (abs(((now.get("heading", 0) - sent.get("heading", 0) + 540) % 360) - 180) > 2.0
                or abs(now["position"]["z"] - sent["position"]["z"]) > 5.0
                or abs(now["position"]["x"] - sent["position"]["x"]) > 2e-4
                or abs(now["position"]["y"] - sent["position"]["y"]) > 2e-4):
            print("\nSomeone else moved the camera - Claude lets go. Your plane.")
            return
        ease = (1 - math.cos(math.pi * i / n)) / 2
        hd = (h0 + degrees * ease) % 360
        clat, clon = dest(tlat, tlon, (hd + 180) % 360, radius)   # stand behind the spot, facing it
        nxt = dict(cam); nxt["position"] = dict(p, x=clon, y=clat); nxt["heading"] = hd
        call("PUT", nxt); sent = nxt
        time.sleep(1.0 / hz)
    print("Finished:"); show(call("GET"))


def glide(dist_m=600.0, climb_ft=0.0, seconds=25.0, hz=20.0):
    """Lesson 3: straight and level (or a gentle climb/descent) along the heading, eased, then hover."""
    cam = call("GET")
    print("Starting point:"); show(cam)
    p = cam["position"]; hd = cam.get("heading", 0.0)
    print(f"Gliding {dist_m:,.0f} m on heading {hd:.1f}, height change {climb_ft:+,.0f} ft, in {seconds:.0f} s")
    n = int(seconds * hz); sent = cam
    for i in range(1, n + 1):
        now = call("GET")
        if (abs(((now.get("heading", 0) - sent.get("heading", 0) + 540) % 360) - 180) > 2.0
                or abs(now["position"]["z"] - sent["position"]["z"]) > 5.0
                or abs(now["position"]["x"] - sent["position"]["x"]) > 2e-4
                or abs(now["position"]["y"] - sent["position"]["y"]) > 2e-4):
            print("\nSomeone else moved the camera - Claude lets go. Your plane.")
            return
        ease = (1 - math.cos(math.pi * i / n)) / 2
        lat, lon = dest(p["y"], p["x"], hd, dist_m * ease)
        nxt = dict(cam); nxt["position"] = dict(p, x=lon, y=lat, z=p["z"] + climb_ft * 0.3048 * ease)
        call("PUT", nxt); sent = nxt
        time.sleep(1.0 / hz)
    print("Hovering. Finished:"); show(call("GET"))


def driveby(dist_m=1200.0, low_ft=150.0, seconds=40.0, hz=20.0):
    """Lesson 5: low pass - dip to low_ft and look ahead (tilt up), cruise, climb back; distance along the heading."""
    cam = call("GET")
    print("Starting point:"); show(cam)
    p = cam["position"]; hd = cam.get("heading", 0.0); t0 = cam.get("tilt", 0.0)
    z0 = p["z"]; zl = low_ft * 0.3048; tl = max(t0, 80.0)
    print(f"Low pass: {dist_m:,.0f} m on heading {hd:.1f}, down to {low_ft:,.0f} ft, tilt {t0:.0f} -> {tl:.0f}, in {seconds:.0f} s")
    sm = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else (1 - math.cos(math.pi * x)) / 2
    n = int(seconds * hz); sent = cam
    for i in range(1, n + 1):
        now = call("GET")
        if (abs(((now.get("heading", 0) - sent.get("heading", 0) + 540) % 360) - 180) > 2.0
                or abs(now["position"]["z"] - sent["position"]["z"]) > 5.0
                or abs(now["position"]["x"] - sent["position"]["x"]) > 2e-4
                or abs(now["position"]["y"] - sent["position"]["y"]) > 2e-4):
            print("\nSomeone else moved the camera - Claude lets go. Your plane.")
            return
        f = i / n
        low = sm(f / 0.3) - sm((f - 0.7) / 0.3)            # 0 -> 1 over the first 30 %, back to 0 over the last 30 %
        lat, lon = dest(p["y"], p["x"], hd, dist_m * sm(f))
        nxt = dict(cam); nxt["position"] = dict(p, x=lon, y=lat, z=z0 + (zl - z0) * low)
        nxt["tilt"] = t0 + (tl - t0) * low
        call("PUT", nxt); sent = nxt
        time.sleep(1.0 / hz)
    print("Hovering. Finished:"); show(call("GET"))


def bearing(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(math.radians, (lat1, lon1, lat2, lon2))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def distance_m(lat1, lon1, lat2, lon2):
    la1, la2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(a)))


def goto(tlat, tlon, stop_short_m=700.0, cruise_ft=1500.0, arrive_ft=600.0, seconds=45.0, hz=20.0):
    """Lesson 6: point to point - turn toward the target, climb to cruise, fly, descend, arrive stop_short_m
    before the target, looking at it."""
    cam = call("GET")
    print("Starting point:"); show(cam)
    p = cam["position"]; h0 = cam.get("heading", 0.0); z0 = p["z"]
    brg = bearing(p["y"], p["x"], tlat, tlon)
    total = distance_m(p["y"], p["x"], tlat, tlon)
    leg = max(total - stop_short_m, 0.0)
    zc, za = cruise_ft * 0.3048, arrive_ft * 0.3048
    dh = ((brg - h0 + 540) % 360) - 180
    print(f"Target {tlat:.5f}, {tlon:.5f}: {total:,.0f} m on bearing {brg:.0f}; fly {leg:,.0f} m, cruise {cruise_ft:,.0f} ft, arrive {arrive_ft:,.0f} ft, {seconds:.0f} s")
    sm = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else (1 - math.cos(math.pi * x)) / 2
    n = int(seconds * hz); sent = cam
    for i in range(1, n + 1):
        now = call("GET")
        if (abs(((now.get("heading", 0) - sent.get("heading", 0) + 540) % 360) - 180) > 2.0
                or abs(now["position"]["z"] - sent["position"]["z"]) > 5.0
                or abs(now["position"]["x"] - sent["position"]["x"]) > 3e-4
                or abs(now["position"]["y"] - sent["position"]["y"]) > 3e-4):
            print("\nSomeone else moved the camera - Claude lets go. Your plane.")
            return
        f = i / n
        hd = (h0 + dh * sm(f / 0.25)) % 360                         # turn onto the bearing in the first quarter
        lat, lon = dest(p["y"], p["x"], brg, leg * sm((f - 0.1) / 0.9))   # roll forward after the turn starts
        up, down = sm(f / 0.4), sm((f - 0.6) / 0.4)
        z = z0 + (zc - z0) * up + (za - zc) * down                  # climb out, cruise, descend in
        nxt = dict(cam); nxt["position"] = dict(p, x=lon, y=lat, z=z); nxt["heading"] = hd
        call("PUT", nxt); sent = nxt
        time.sleep(1.0 / hz)
    print("Arrived. Hovering:"); show(call("GET"))


if __name__ == "__main__":
    try:
        mode = sys.argv[1] if len(sys.argv) > 1 else "read"
        print(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} {mode}")
        if mode == "downtown":
            goto(30.3297, -81.6589)                     # Dark Jacksonville's downtown (realsim DOWNTOWN)
        elif mode == "driveby":
            driveby(float(sys.argv[2]) if len(sys.argv) > 2 else 1200.0, float(sys.argv[3]) if len(sys.argv) > 3 else 150.0)
        elif mode == "return":
            # Lesson 4: about-face, then glide back down to where lesson 3 started
            dist = float(sys.argv[2]) if len(sys.argv) > 2 else 600.0
            drop = float(sys.argv[3]) if len(sys.argv) > 3 else 200.0
            turn(180.0, seconds=8.0)
            glide(dist, -drop)
        elif mode == "glide":
            glide(float(sys.argv[2]) if len(sys.argv) > 2 else 600.0, float(sys.argv[3]) if len(sys.argv) > 3 else 0.0)
        elif mode == "orbit":
            orbit(float(sys.argv[2]) if len(sys.argv) > 2 else 360.0)
        elif mode == "turn":
            turn(float(sys.argv[2]) if len(sys.argv) > 2 else 30.0)
        else:
            print("ArcGIS Earth camera right now:"); show(call("GET"))
    except Exception as exc:
        print(f"Could not reach ArcGIS Earth at {CAMERA_URL}: {exc}")
        print("Is ArcGIS Earth open, with its Automation API on?")
