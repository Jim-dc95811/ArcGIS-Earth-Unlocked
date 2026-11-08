"""(roundtrip rig - based on the dropper rig) EarthStick 1.3.6 Gate Dropper flight test (no Windows, no joystick, no ArcGIS Earth).

python3 earthstick_rig_dropper.py <EarthStick.py>

Copies EarthStick.py and gate_dropper.py into a temp "System Files" folder with an empty Gates folder
beside it, then runs EarthStick's real flying loop with a scripted joystick, a deterministic clock and a
mock ArcGIS Earth API (camera GET/PUT + POST /arcgisearth/layer):
  1. hover at the start, press Button 2           -> mark 1
  2. the camera is moved 3 km along the heading (as if flown with the mouse), Button 2 again
                                                  -> Dropped_Gate_01.kmz written, armed, layer request sent
  4. Button 2 held 2.5 s (TEST4)          -> file deleted, gates disarmed, map layer removed
  3. the camera is put 500 m before mark 1, flying the way it looked at mark 1
                                                  -> exactly one jump, landing 300 m past mark 2 looking the way
                                                     it looked at mark 2 (TEST2: gates face the pilot's heading)
"""
import json, math, os, shutil, sys, tempfile, threading, types
import tempfile as _tf; os.environ["LOCALAPPDATA"] = _tf.mkdtemp(prefix="es_lad_")   # 1.3.11: last-flown note goes here
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SRC = os.path.abspath(sys.argv[1])
tmp = tempfile.mkdtemp(prefix="es_drop_rig_")
prog = os.path.join(tmp, "System Files"); os.makedirs(prog)
shutil.copy(SRC, os.path.join(prog, "EarthStick.py"))
shutil.copy(os.path.join(os.path.dirname(SRC), "gate_dropper.py"), os.path.join(prog, "gate_dropper.py"))
os.makedirs(os.path.join(tmp, "Gates"))
PATH = os.path.join(prog, "EarthStick.py")


class StopTest(BaseException):
    pass


class Earth:
    camera = {"position": {"x": -80.0, "y": 30.0, "z": 152.4, "spatialReference": {"wkid": 4326}},
              "heading": 90.0, "tilt": 80.0, "roll": 0.0}
    puts, layers, deletes = [], [], []


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, obj=None):
        b = b"" if obj is None else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._send(200, Earth.camera)

    def do_PUT(self):
        n = int(self.headers.get("Content-Length") or 0)
        Earth.camera = json.loads(self.rfile.read(n)); Earth.puts.append(Earth.camera); self._send(200)

    def do_DELETE(self):
        Earth.deletes.append(self.path); self._send(200, {})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        Earth.layers.append(json.loads(self.rfile.read(n))); self._send(200, {"id": "x", "loadStatus": "loaded"})


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

es = types.ModuleType("earthstick"); es.__file__ = PATH
exec(compile(open(PATH).read(), PATH, "exec"), es.__dict__)
es.BASE_URL = f"http://localhost:{srv.server_address[1]}"; es.CAMERA_URL = es.BASE_URL + "/arcgisearth/camera"


class Clock:
    t = 1000.0

    @classmethod
    def perf_counter(cls): return cls.t

    @classmethod
    def sleep(cls, s): cls.t += s


es.time = types.SimpleNamespace(perf_counter=Clock.perf_counter, sleep=Clock.sleep, monotonic=Clock.perf_counter)
es.os = types.SimpleNamespace(**{**{k: getattr(os, k) for k in dir(os) if not k.startswith("__")}, "name": "nt"})  # 1.3.11: real os, Windows name
printed = []
es.print = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
es.sys = types.SimpleNamespace(stdout=types.SimpleNamespace(write=printed.append, flush=lambda: None), argv=sys.argv)
es.TriggerClick = types.SimpleNamespace(start=lambda: None)      # no overlay window here


def at(lat, lon, z, heading):
    return {"position": {"x": lon, "y": lat, "z": z, "spatialReference": {"wkid": 4326}},
            "heading": heading, "tilt": 80.0, "roll": 0.0}



# Jim's 2026-11-08 15:22 case: both marks taken looking EAST (heading 90), 3 km apart, then the round trip
lon2, lat2 = es.move_lonlat(-80.0, 30.0, 90.0, 3000.0, 0.0)          # mark 2: 3 km east, still looking east
lon0, lat0 = es.move_lonlat(-80.0, 30.0, 90.0, -500.0, 0.0)          # 500 m before mark 1
DROP = 1 << (es.DROP_BUTTON - 1)
marks = {}


def mark(n):
    marks[n] = len(Earth.puts)


def turn_round(height_off=0.0):
    c = Earth.camera
    Earth.camera = at(c["position"]["y"], c["position"]["x"], c["position"]["z"] + height_off, (c["heading"] + 180.0) % 360)


def script():
    S = lambda fwd=0.0, thr=0.0, btn=0, act=None: (dict(strafe=0.0, forward=fwd, yaw=0.0, throttle=thr, tilt=0.0, buttons=btn), act)
    segs = [(20, S()), (5, S(btn=DROP)), (40, S()),
            (1, S(act=lambda: setattr(Earth, "camera", at(lat2, lon2, 300.0, 90.0)))), (30, S()),
            (5, S(btn=DROP)), (40, S()),
            (1, S(act=lambda: setattr(Earth, "camera", at(lat0, lon0, 152.4, 90.0)))), (30, S(act=lambda: mark("out"))),
            (90, S(fwd=1.0, thr=1.0)), (30, S(act=lambda: mark("arrived2"))),          # eastbound through gate 1
            (1, S(act=lambda: turn_round(100.0))), (60, S(act=lambda: mark("home"))),  # turn round, 100 m high
            (90, S(fwd=1.0, thr=1.0)), (30, S(act=lambda: mark("arrived1"))),          # westbound: the way home
            (1, S(act=lambda: turn_round(0.0))), (60, S(act=lambda: mark("again"))),
            (90, S(fwd=1.0, thr=1.0)), (30, S(act=lambda: mark("end")))]
    for n, (st, act) in segs:
        for i in range(n):
            if act and i == 0:
                act()
            yield dict(st)


class FakeJoy:
    def __init__(self, *a, **k):
        self.caps = types.SimpleNamespace(szPname="T.A320 Pilot"); self.id = 0; self.slider_name = "Z"
        self.frames = script()

    def read(self):
        try:
            return next(self.frames)
        except StopIteration:
            raise StopTest("script done")


es.WinJoystick = FakeJoy
try:
    es.run()
except StopTest:
    pass

ok = True
def check(name, cond, detail=""):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

def jumps(a, b):
    p = Earth.puts[marks[a]:marks[b]]
    return [p[i] for i in range(1, len(p)) if abs(p[i]["position"]["x"] - p[i - 1]["position"]["x"]) > 0.005]

g1lon, g1lat = es.move_lonlat(-80.0, 30.0, 90.0, 500.0, 0.0)          # gate at mark 1
g2lon, g2lat = es.move_lonlat(lon2, lat2, 90.0, 500.0, 0.0)           # gate at mark 2
j = jumps("out", "arrived2")
want = es.move_lonlat(g2lon, g2lat, 90.0, 300.0, 0.0)
check("1 eastbound through the first gate: one jump, out 300 m past the second gate heading east",
      len(j) == 1 and abs(j[0]["position"]["x"] - want[0]) < 1e-4 and abs(j[0]["heading"] - 90.0) < 1e-6, j and (j[0]["position"], j[0]["heading"]))
j = jumps("home", "arrived1")
want = es.move_lonlat(g1lon, g1lat, 270.0, 300.0, 0.0)
check("2 turn round once, fly home west: one jump through the second gate (from 100 m high: tractor beam)",
      len(j) == 1, len(j))
if j:
    check("  ...out 300 m in front of the first gate, heading west (the way home), at its height",
          abs(j[0]["position"]["x"] - want[0]) < 1e-4 and abs(j[0]["position"]["y"] - want[1]) < 1e-4
          and abs(j[0]["heading"] - 270.0) < 1e-6 and abs(j[0]["position"]["z"] - 152.4) < 0.01, (j[0]["position"], j[0]["heading"]))
    pre = Earth.puts[marks["home"]:marks["arrived1"]]
    k = pre.index(j[0])
    check("  ...tractor beam pulled the height to the gate before the jump", abs(pre[k - 1]["position"]["z"] - 300.0) < 5.0, pre[k - 1]["position"]["z"])
j = jumps("again", "end")
check("3 turn round once more, fly east: through the first gate again", len(j) == 1, len(j))
gates, _ = es.load_gates(os.path.join(tmp, "Gates"))
g2 = next(g for g in gates if g["name"].endswith("A"))
check("the second gate faces back the way you came (270)", abs(g2["facing"] - 270.0) < 1e-6, g2["facing"])
print("ALL PASS" if ok else "FAILURES")
shutil.rmtree(tmp)
