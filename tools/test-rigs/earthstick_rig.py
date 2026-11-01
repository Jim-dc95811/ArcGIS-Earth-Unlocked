"""EarthStick test rig: scripted joystick + deterministic clock + mock ArcGIS Earth camera API.

python3 es_rig.py <path to EarthStick.py> <scenario>   -> prints one JSON line
"""
import json, os, sys, threading, types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PATH, SCENARIO = sys.argv[1], sys.argv[2]


class StopTest(BaseException):
    pass


# ---------- mock ArcGIS Earth camera API ----------
class Earth:
    camera = {"position": {"x": -81.9265, "y": 30.4191, "z": 1500.0, "spatialReference": {"wkid": 4326}},
              "heading": 30.0, "tilt": 60.0, "roll": 0.0}
    puts, gets, mode = [], 0, "ok"   # mode: ok | notfound


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, obj=None):
        b = b"" if obj is None else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if Earth.mode == "notfound": return self._send(404, {"error": "not ArcGIS Earth"})
        Earth.gets += 1; self._send(200, Earth.camera)

    def do_PUT(self):
        n = int(self.headers.get("Content-Length") or 0)
        cam = json.loads(self.rfile.read(n)); Earth.camera = cam; Earth.puts.append(cam); self._send(200)


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

# ---------- load EarthStick as a module ----------
es = types.ModuleType("earthstick"); es.__file__ = PATH
exec(compile(open(PATH).read(), PATH, "exec"), es.__dict__)
port = srv.server_address[1]
es.BASE_URL = f"http://localhost:{port}"; es.CAMERA_URL = es.BASE_URL + "/arcgisearth/camera"


# ---------- deterministic clock (advances only when EarthStick sleeps) ----------
class Clock:
    t = 1000.0
    limit = None

    @classmethod
    def perf_counter(cls): return cls.t

    @classmethod
    def sleep(cls, s):
        cls.t += s
        if cls.limit is not None and cls.t > cls.limit: raise StopTest("time limit")


es.time = types.SimpleNamespace(perf_counter=Clock.perf_counter, sleep=Clock.sleep, monotonic=Clock.perf_counter)
es.os = types.SimpleNamespace(name="nt")            # pretend to be Windows
printed = []
real_stdout = sys.stdout
es.print = lambda *a, **k: printed.append(" ".join(str(x) for x in a))


class Out:
    def write(self, s): printed.append(s)
    def flush(self): pass


es.sys = types.SimpleNamespace(stdout=Out(), argv=sys.argv)


# ---------- scripted joystick ----------
def script():
    """(frames, state) segments covering every control and idle periods."""
    S = lambda strafe=0.0, fwd=0.0, yaw=0.0, thr=0.5, tilt=0.0, btn=0: dict(strafe=strafe, forward=fwd, yaw=yaw, throttle=thr, tilt=tilt, buttons=btn)
    segs = [(20, S()), (60, S(fwd=1.0, thr=0.8)), (30, S()), (45, S(strafe=-0.6, thr=0.3)), (40, S(yaw=0.7)),
            (25, S(tilt=1.0)), (25, S(tilt=-1.0)), (40, S(btn=1 << 3)), (40, S(btn=1 << 2)), (30, S()),
            (60, S(fwd=-0.5, strafe=0.4, yaw=-0.3, thr=1.0)), (20, S())]
    for n, st in segs:
        for _ in range(n):
            yield dict(st)


class FakeJoy:
    attempts = 0
    fail_first = 0

    def __init__(self, *a, **k):
        FakeJoy.attempts += 1
        if FakeJoy.attempts <= FakeJoy.fail_first:
            raise RuntimeError("No Windows joystick is connected")
        self.caps = types.SimpleNamespace(szPname="T.A320 Pilot"); self.id = 0; self.slider_name = "Z"
        self.frames = script()

    def read(self):
        try:
            return next(self.frames)
        except StopIteration:
            raise StopTest("script done")


es.WinJoystick = FakeJoy
result = {"version": es.VERSION, "scenario": SCENARIO}


def go():
    try:
        es.run()
    except StopTest as e:
        result["stopped"] = str(e)
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"


if SCENARIO == "replay":
    go()
    result["puts"] = len(Earth.puts)
    result["final"] = Earth.puts[-1] if Earth.puts else None
    json.dump(Earth.puts, open(os.path.join(os.path.dirname(__file__), f"es_puts_{es.VERSION}.json"), "w"))

elif SCENARIO == "unplugged_at_start":
    FakeJoy.fail_first = 3
    go()
    result["joystick_attempts"] = FakeJoy.attempts
    result["flew_after_plug_in"] = len(Earth.puts) > 0
    result["messages"] = [p.strip() for p in printed if "oystick" in p][:3]

elif SCENARIO == "proxy":
    Clock.limit = Clock.t + 5          # give it 5 (simulated) seconds to connect
    go()
    result["connected"] = any("ArcGIS Earth: connected" in p for p in printed)
    result["puts"] = len(Earth.puts)
    result["wait_messages"] = [p.strip() for p in printed if "Still waiting" in p][:1]

elif SCENARIO == "port_conflict":
    Earth.mode = "notfound"; Clock.limit = Clock.t + 10
    go()
    waits = [p.strip() for p in printed if "Still waiting" in p]
    result["reason_lines_in_10s"] = len(waits)
    result["reason"] = waits[:1]

sys.__stdout__.write(json.dumps(result) + "\n")
