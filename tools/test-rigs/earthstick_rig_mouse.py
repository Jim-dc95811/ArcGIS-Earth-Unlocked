"""EarthStick 1.3.9 check: the tractor beam must not pull back mouse moves while the stick is let go.

python3 earthstick_rig_mouse.py <EarthStick.py>
Hover 2 km before a dropped gate, 300 m below it (inside its grab zone), stick neutral, while the 'mouse'
pans the map 15 m east every time EarthStick reads the camera. Counts camera PUTs that put the map back.
"""
import json, os, shutil, sys, tempfile, threading, types
import tempfile as _tf; os.environ["LOCALAPPDATA"] = _tf.mkdtemp(prefix="es_lad_")   # 1.3.11: last-flown note goes here
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SRC = os.path.abspath(sys.argv[1])
tmp = tempfile.mkdtemp(prefix="es_mouse_rig_")
prog = os.path.join(tmp, "System Files"); os.makedirs(prog)
shutil.copy(SRC, os.path.join(prog, "EarthStick.py"))
shutil.copy(os.path.join(os.path.dirname(SRC), "gate_dropper.py"), os.path.join(prog, "gate_dropper.py"))
gates_dir = os.path.join(tmp, "Gates"); os.makedirs(gates_dir)
PATH = os.path.join(prog, "EarthStick.py")


class StopTest(BaseException):
    pass


class Earth:
    camera = None
    puts, pulled_back, mouse_m, last_t = [], 0, 0.0, 1000.0


def mouse():
    """the hand on the mouse pans the map 60 m/s east, whatever EarthStick is doing (fake clock time)"""
    dt = Clock.t - Earth.last_t
    Earth.last_t = Clock.t
    if dt > 0:
        lon, lat = es.move_lonlat(Earth.camera["position"]["x"], Earth.camera["position"]["y"], 90.0, 60.0 * dt, 0.0)
        Earth.camera["position"]["x"], Earth.camera["position"]["y"] = lon, lat
        Earth.mouse_m += 60.0 * dt


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, obj=None):
        b = b"" if obj is None else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        mouse()
        self._send(200, Earth.camera)

    def do_PUT(self):
        n = int(self.headers.get("Content-Length") or 0)
        new = json.loads(self.rfile.read(n))
        mouse()
        if new["position"]["x"] < Earth.camera["position"]["x"] - 1e-9:
            Earth.pulled_back += 1
        Earth.camera = new; Earth.puts.append(new); self._send(200)

    def do_POST(self):
        self._send(200, {"id": "x"})


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
es.print = lambda *a, **k: None
es.sys = types.SimpleNamespace(stdout=types.SimpleNamespace(write=lambda *a: None, flush=lambda: None), argv=sys.argv)
es.TriggerClick = types.SimpleNamespace(start=lambda: None)

gd = es.gate_dropper_module()
gd.drop_pair(gates_dir, (30.0, -80.0, 500.0, 0.0), (31.0, -80.0, 500.0, 0.0))   # gate B 500 m north of (30,-80), facing north (partner due north, so true for both the old rule and the 2.0 kernel)
glat, glon = gd.dest(30.0, -80.0, 0.0, 500.0)
slat, slon = gd.dest(glat, glon, 180.0, 2000.0)                                  # 2 km before it
Earth.camera = {"position": {"x": slon, "y": slat, "z": 200.0, "spatialReference": {"wkid": 4326}},
                "heading": 0.0, "tilt": 80.0, "roll": 0.0}


class FakeJoy:
    def __init__(self, *a, **k):
        self.caps = types.SimpleNamespace(szPname="T.A320 Pilot"); self.id = 0; self.slider_name = "Z"; self.n = 0

    def read(self):
        self.n += 1
        if self.n > 150:                                  # 5 s of hovering
            raise StopTest()
        return dict(strafe=0.0, forward=0.0, yaw=0.0, throttle=0.0, tilt=0.0, buttons=0)


es.WinJoystick = FakeJoy
try:
    es.run()
except StopTest:
    pass
z = Earth.camera["position"]["z"]
mouse()
moved = es.math.hypot((Earth.camera["position"]["x"] - slon) * 96486.0, Earth.camera["position"]["y"] - slat)
print(f"{es.VERSION}: {len(Earth.puts)} PUTs, {Earth.pulled_back} pulled the map back; mouse panned {Earth.mouse_m:.0f} m, map actually moved {moved:.0f} m east; height 200 -> {z:.1f} m (gate 500)")
