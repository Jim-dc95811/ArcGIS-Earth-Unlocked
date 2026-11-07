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


if __name__ == "__main__":
    try:
        mode = sys.argv[1] if len(sys.argv) > 1 else "read"
        print(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} {mode}")
        if mode == "turn":
            turn(float(sys.argv[2]) if len(sys.argv) > 2 else 30.0)
        else:
            print("ArcGIS Earth camera right now:"); show(call("GET"))
    except Exception as exc:
        print(f"Could not reach ArcGIS Earth at {CAMERA_URL}: {exc}")
        print("Is ArcGIS Earth open, with its Automation API on?")
