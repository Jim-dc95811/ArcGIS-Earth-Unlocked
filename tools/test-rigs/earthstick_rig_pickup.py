"""EarthStick 1.3.11 Gates-folder pickup + ADD GATES test (no Windows, no joystick, no ArcGIS Earth).

python3 earthstick_rig_pickup.py <EarthStick.py>

Copies EarthStick.py and gate_dropper.py into a temp "System Files" folder with a Gates folder beside it that
already holds one gate file (armed at startup, not put on the map), then runs EarthStick's real flying loop with
a scripted joystick, a fake clock and a mock ArcGIS Earth API (camera GET/PUT, POST/DELETE layer):
  1. while hovering, a new gate file appears in Gates - first half-written, then complete a moment later
     -> never read half-written; armed and put on the map once, within 4 s, no restart
  2. fly through the new gate -> exactly one jump, landing 300 m past its partner
  3. the file is deleted -> disarmed, its map layer removed; flying the same line again -> no jump
  4. ADD GATES (add_gate_files, the button's copy step) with a file from elsewhere -> copied, armed, shown;
     the same file again -> not copied twice; a file with no gates -> skipped, not copied
  5. a Gate Dropper pair is still put on the map exactly once (the pickup does not add it a second time)
  6. the last-flown note names this Gates folder
"""
import json, os, shutil, sys, tempfile, threading, types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SRC = os.path.abspath(sys.argv[1])
tmp = tempfile.mkdtemp(prefix="es_pickup_rig_")
os.environ["LOCALAPPDATA"] = os.path.join(tmp, "LocalAppData")
prog = os.path.join(tmp, "System Files"); os.makedirs(prog)
shutil.copy(SRC, os.path.join(prog, "EarthStick.py"))
shutil.copy(os.path.join(os.path.dirname(SRC), "gate_dropper.py"), os.path.join(prog, "gate_dropper.py"))
GATES = os.path.join(tmp, "Gates"); os.makedirs(GATES)
ELSEWHERE = os.path.join(tmp, "Downloads"); os.makedirs(ELSEWHERE)
PATH = os.path.join(prog, "EarthStick.py")


class StopTest(BaseException):
    pass


class Earth:
    camera = {"position": {"x": -80.0, "y": 30.0, "z": 152.4, "spatialReference": {"wkid": 4326}},
              "heading": 90.0, "tilt": 80.0, "roll": 0.0}
    puts, layers, deletes, n = [], [], [], 0


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
        Earth.deletes.append(self.path.rsplit("/", 1)[-1]); self._send(200, {})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        Earth.n += 1
        Earth.layers.append((f"L{Earth.n}", json.loads(self.rfile.read(n))))
        self._send(200, {"id": f"L{Earth.n}", "loadStatus": "loaded"})


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


es.time = types.SimpleNamespace(perf_counter=Clock.perf_counter, sleep=Clock.sleep, monotonic=Clock.perf_counter,
                                strftime=__import__("time").strftime)
es.os = types.SimpleNamespace(**{**{k: getattr(os, k) for k in dir(os) if not k.startswith("__")}, "name": "nt"})
printed, stamped = [], []
def _out(t):
    printed.append(t); stamped.append((Clock.t, t))
es.print = lambda *a, **k: _out(" ".join(str(x) for x in a))
es.sys = types.SimpleNamespace(stdout=types.SimpleNamespace(write=_out, flush=lambda: None), argv=sys.argv)
es.TriggerClick = types.SimpleNamespace(start=lambda: None)
gd = es.gate_dropper_module()

# gate files made outside the Gates folder (the same writer the Gate Dropper uses)
lon2, lat2 = es.move_lonlat(-80.0, 30.0, 90.0, 3000.0, 0.0)
lon0, lat0 = es.move_lonlat(-80.0, 30.0, 90.0, -500.0, 0.0)
mk = lambda d, a, b: str(gd.drop_pair(d, a, b))
os.makedirs(os.path.join(tmp, "w1")); os.makedirs(os.path.join(tmp, "w2")); os.makedirs(os.path.join(tmp, "w3"))
start_file = mk(os.path.join(tmp, "w1"), (45.0, -100.0, 300.0, 0.0), (45.1, -100.0, 300.0, 180.0))       # far away
shutil.copy(start_file, os.path.join(GATES, "Start_pair.kmz"))
new_file = mk(os.path.join(tmp, "w2"), (30.0, -80.0, 152.4, 90.0), (lat2, lon2, 300.0, 270.0))           # on our line
add_file = shutil.copy(mk(os.path.join(tmp, "w3"), (35.0, -90.0, 300.0, 0.0), (35.1, -90.0, 300.0, 180.0)),
                       os.path.join(ELSEWHERE, "Gate_from_email.kmz"))
junk = os.path.join(ELSEWHERE, "Just_a_map.kmz")
import zipfile
with zipfile.ZipFile(junk, "w") as z:
    z.writestr("doc.kml", '<kml xmlns="http://www.opengis.net/kml/2.2"><Placemark><name>x</name></Placemark></kml>')

NEW = os.path.join(GATES, "Gate_new.kmz")
marks, add_results = {}, []


def at(lat, lon, z, heading):
    return {"position": {"x": lon, "y": lat, "z": z, "spatialReference": {"wkid": 4326}},
            "heading": heading, "tilt": 80.0, "roll": 0.0}


def mark(name):
    marks[name] = (len(Earth.puts), len(Earth.layers), len(Earth.deletes), len(printed), Clock.t)


def half_write():
    with open(NEW, "wb") as f:
        f.write(open(new_file, "rb").read()[:200])          # a zip cut short


def full_write():
    shutil.copy(new_file, NEW)
    marks["complete_t"] = Clock.t


DROP = 1 << (es.DROP_BUTTON - 1)


def script():
    S = lambda fwd=0.0, thr=0.0, btn=0, act=None: (dict(strafe=0.0, forward=fwd, yaw=0.0, throttle=thr, tilt=0.0, buttons=btn), act)
    segs = [(30, S(act=lambda: mark("start"))),
            (15, S(act=half_write)), (150, S(act=full_write)),                       # 0.5 s half-written, then 5 s
            (1, S(act=lambda: (mark("armed"), setattr(Earth, "camera", at(lat0, lon0, 152.4, 90.0))))), (30, S()),
            (90, S(fwd=1.0, thr=1.0)), (30, S(act=lambda: mark("flown"))),
            (150, S(act=lambda: os.remove(NEW))),                                    # 5 s
            (1, S(act=lambda: (mark("removed"), setattr(Earth, "camera", at(lat0, lon0, 152.4, 90.0))))), (30, S()),
            (90, S(fwd=1.0, thr=1.0)), (30, S(act=lambda: mark("flown2"))),
            (150, S(act=lambda: add_results.append(es.add_gate_files([add_file, junk], GATES)))),
            (150, S(act=lambda: (mark("added"), add_results.append(es.add_gate_files([add_file], GATES))))),
            (1, S(act=lambda: (mark("added2"), setattr(Earth, "camera", at(30.0, -80.0, 152.4, 90.0))))), (20, S()),
            (5, S(btn=DROP)), (40, S()),
            (1, S(act=lambda: setattr(Earth, "camera", at(lat2, lon2, 300.0, 270.0)))), (30, S()),
            (5, S(btn=DROP)), (180, S(act=lambda: mark("dropped")))]
    for n, (st, act) in segs:
        for i in range(n):
            if act and i == 0:
                act()
            yield dict(st)
    mark("end")


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
def between(a, b, i): return slice(marks[a][i], marks[b][i])
def jumps(a, b):
    p = Earth.puts[between(a, b, 0)]
    return [i for i in range(1, len(p)) if abs(p[i]["position"]["x"] - p[i - 1]["position"]["x"]) > 0.005]

check("startup gates armed, not put on the map", "2 gate(s) armed" in text and not Earth.layers[:0] and
      all("Start_pair" not in l[1]["URI"] for l in Earth.layers), [l[1]["URI"] for l in Earth.layers])
lay = Earth.layers[between("start", "armed", 1)]
check("new file put on the map once", len(lay) == 1 and lay[0][1]["URI"].endswith("Gate_new.kmz"), lay)
when = [l for l in printed[marks["start"][3]:marks["armed"][3]] if "Gates folder:" in l]
check("armed message", any("armed Gate_new.kmz (4 gates armed)" in l for l in when), when)
check("half-written file never read", "no gates in" not in "".join(when) and "skipped" not in "".join(printed[marks["start"][3]:marks["armed"][3]]))
t_arm = next((t for t, l in stamped if "armed Gate_new.kmz" in l), None)
check("no restart needed: armed within 4 s of the file being complete", t_arm is not None and 0 < t_arm - marks["complete_t"] <= 4.0,
      t_arm and round(t_arm - marks["complete_t"], 2))
j = jumps("armed", "flown")
check("fly through the new gate: exactly one jump", len(j) == 1, j)
if j:
    land_lon, land_lat = es.move_lonlat(lon2, lat2, 270.0, 800.0, 0.0)
    jp = Earth.puts[marks["armed"][0] + j[0]]["position"]
    check("landed 300 m past the partner", abs(jp["x"] - land_lon) < 1e-4 and abs(jp["y"] - land_lat) < 1e-4, jp)
dels = Earth.deletes[between("flown", "removed", 2)]
check("removed file: its map layer deleted", dels == [lay[0][0]] if lay else False, dels)
check("removed file: disarmed message", "disarmed Gate_new.kmz (2 gates armed)" in "".join(printed[marks["flown"][3]:marks["removed"][3]]))
check("same line again: no jump", jumps("removed", "flown2") == [], jumps("removed", "flown2"))
r1 = add_results[0] if add_results else []
check("ADD GATES copies a gate file from elsewhere", r1 and r1[0] == ("Gate_from_email.kmz", "added", "Gate_from_email.kmz"), r1)
check("ADD GATES skips a file with no gates, does not copy it", r1 and r1[1][2] is None and not os.path.exists(os.path.join(GATES, "Just_a_map.kmz")), r1)
lay2 = Earth.layers[between("flown2", "added", 1)]
check("added file armed and shown", len(lay2) == 1 and lay2[0][1]["URI"].endswith("Gate_from_email.kmz")
      and "armed Gate_from_email.kmz (4 gates armed)" in "".join(printed[marks["flown2"][3]:marks["added"][3]]), lay2)
r2 = add_results[1] if len(add_results) > 1 else []
check("same file again: not copied twice, not shown twice", r2 and r2[0][1] == "already there"
      and len(Earth.layers[between("added", "added2", 1)]) == 0
      and sorted(f for f in os.listdir(GATES) if "from_email" in f) == ["Gate_from_email.kmz"], (r2, os.listdir(GATES)))
lay3 = Earth.layers[between("added2", "end", 1)]
check("Gate Dropper pair shown exactly once (pickup does not add it again)", len(lay3) == 1 and lay3[0][1]["URI"].endswith("Dropped_Gate_01.kmz"), lay3)
note = os.path.join(os.environ["LOCALAPPDATA"], "ArcGIS Earth Unlocked", "last_earthstick.txt")
check("last-flown note names this Gates folder", os.path.isfile(note) and f"gates={os.path.realpath(GATES)}" in open(note).read())
check("no half-copied leftovers", not [f for f in os.listdir(GATES) if f.endswith(".copying")])
print("ALL PASS" if ok else "FAILURES")
shutil.rmtree(tmp)
