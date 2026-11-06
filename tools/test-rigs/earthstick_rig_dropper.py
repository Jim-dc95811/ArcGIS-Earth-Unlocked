"""EarthStick 1.3.6 Gate Dropper flight test (no Windows, no joystick, no ArcGIS Earth).

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
es.os = types.SimpleNamespace(name="nt")
printed = []
es.print = lambda *a, **k: printed.append(" ".join(str(x) for x in a))
es.sys = types.SimpleNamespace(stdout=types.SimpleNamespace(write=printed.append, flush=lambda: None), argv=sys.argv)
es.TriggerClick = types.SimpleNamespace(start=lambda: None)      # no overlay window here


def at(lat, lon, z, heading):
    return {"position": {"x": lon, "y": lat, "z": z, "spatialReference": {"wkid": 4326}},
            "heading": heading, "tilt": 80.0, "roll": 0.0}


lon2, lat2 = es.move_lonlat(-80.0, 30.0, 90.0, 3000.0, 0.0)          # mark 2: 3 km east
lon0, lat0 = es.move_lonlat(-80.0, 30.0, 90.0, -500.0, 0.0)          # 500 m before mark 1
B2 = 1 << 1
SNAP = os.path.join(tmp, "snapshot")


def snapshot():
    os.makedirs(SNAP, exist_ok=True)
    src = os.path.join(tmp, "Gates", "Dropped_Gate_01.kmz")
    if os.path.exists(src):
        shutil.copy(src, SNAP)


def script():
    S = lambda fwd=0.0, thr=0.0, btn=0, act=None: (dict(strafe=0.0, forward=fwd, yaw=0.0, throttle=thr, tilt=0.0, buttons=btn), act)
    segs = [(20, S()), (5, S(btn=B2)), (40, S()),
            (1, S(act=lambda: setattr(Earth, "camera", at(lat2, lon2, 300.0, 270.0)))), (30, S()),
            (5, S(btn=B2)), (40, S()),
            (1, S(act=snapshot)),                                             # keep a copy (TEST4 undo deletes it later)
            (1, S(act=lambda: setattr(Earth, "camera", at(lat0, lon0, 152.4, 90.0)))), (30, S()),
            (90, S(fwd=1.0, thr=1.0)), (30, S()),
            (75, S(btn=B2)), (30, S())]                                       # TEST4: hold Button 2 2.5 s = undo
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

text = "".join(printed)
kmz = os.path.join(tmp, "Gates", "Dropped_Gate_01.kmz")
check("mark 1 message", "MARK 1 SAVED" in text)
check("gate file written into Gates", os.path.isfile(os.path.join(SNAP, "Dropped_Gate_01.kmz")))
check("written and armed message", "Dropped_Gate_01.kmz written and armed (2 gates armed)" in text, [l for l in printed if "Gate Dropper" in l])
check("one layer request, KML, path of the file", len(Earth.layers) == 1 and Earth.layers[0]["type"] == "KML"
      and Earth.layers[0]["URI"].endswith("Dropped_Gate_01.kmz"), Earth.layers)
gates, problems = es.load_gates(SNAP)
ga = next((g for g in gates if g["name"] == "Drop 01 B"), None)
glon, glat = es.move_lonlat(-80.0, 30.0, 90.0, 500.0, 0.0)                        # TEST3: 500 m in front of mark 1
check("gate at mark 1 = 500 m ahead, at hover height", ga and abs(ga["lat"] - glat) < 1e-6 and abs(ga["lon"] - glon) < 1e-5 and abs(ga["alt_m"] - 152.4) < 0.01, ga)
jumps = [i for i in range(1, len(Earth.puts)) if abs(Earth.puts[i]["position"]["x"] - Earth.puts[i - 1]["position"]["x"]) > 0.005]
check("exactly one jump while flying through", len(jumps) == 1, jumps)
if jumps:
    j = Earth.puts[jumps[0]]["position"]
    land_lon, land_lat = es.move_lonlat(lon2, lat2, 270.0, 800.0, 0.0)          # TEST3: gate 500 m ahead of mark 2 + 300 m past it
    check("landed 300 m past the gate ahead of mark 2 (the way you looked there), at its height", abs(j["x"] - land_lon) < 1e-4 and abs(j["y"] - land_lat) < 1e-4 and abs(j["z"] - 300.0) < 0.01, j)
    check("looking the way you looked when you marked it (270)", abs(Earth.puts[jumps[0]]["heading"] - 270.0) < 1e-6, Earth.puts[jumps[0]]["heading"])
check("gate at mark 1 faces the way you looked there (90)", ga and abs(ga["facing"] - 90.0) < 1e-6, ga and ga["facing"])
check("hold Button 2: file deleted", not os.path.exists(kmz))
check("hold Button 2: map layer removed (DELETE /arcgisearth/layer/x)", Earth.deletes == ["/arcgisearth/layer/x"], Earth.deletes)
check("hold Button 2: gates disarmed", "Dropped_Gate_01.kmz deleted and disarmed (0 gates armed)" in text, [l for l in printed if "deleted" in l])
print("ALL PASS" if ok else "FAILURES")
shutil.rmtree(tmp)
