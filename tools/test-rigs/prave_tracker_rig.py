"""Test rig: Jim's Gold field tester -> virtual serial port -> tracker -> mock ArcGIS Earth API.

Usage: python3 rig.py <v1.0|v1.1> <scenario>
Prints one JSON line of results and exits.
"""
import importlib.util, io, json, os, pty, sys, threading, time, tty, contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pyserial-src"))
import serial  # noqa: E402

VERSION, SCENARIO = sys.argv[1], sys.argv[2]
TRACKER = {"v1.0": os.path.join(HERE, "PRAVE_ME_Tracker_v1/PRAVE_ME_Tracker/PRAVE_ME_Tracker.py"),
           "v1.1": "/home/claude/dev/prave_v1.1/PRAVE_ME_Tracker.py",
           "v1.2": "/home/claude/dev/prave_v1.2/PRAVE_ME_Tracker.py"}[VERSION]
GOLD = "/mnt/user-data/attachments/0538666f-0b95-5128-958e-e4b3b04f84fa/cb86a0c3-PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.py"
WORK = os.path.join(HERE, "rigwork", f"{VERSION}_{SCENARIO}")
os.makedirs(WORK, exist_ok=True)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


# ---------------- mock ArcGIS Earth Automation API ----------------
class Earth:
    def __init__(self):
        self.drawings = {}
        self.camera = {"position": {"x": -81.0, "y": 30.0, "z": 4321.0, "spatialReference": {"wkid": 4326}},
                       "heading": 17.0, "tilt": 5.0, "roll": 0.0}
        self.mode = "up"          # up | error500
        self.calls = 0
        self.lock = threading.Lock()


earth = Earth()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj=None):
        body = b"" if obj is None else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _gate(self):
        earth.calls += 1
        if earth.mode == "error500":
            self._send(500, {"error": "simulated ArcGIS Earth failure"}); return False
        return True

    def do_GET(self):
        if not self._gate(): return
        if self.path == "/arcgisearth/camera":
            with earth.lock: self._send(200, earth.camera)
        else: self._send(404, {"error": "not found"})

    def do_PUT(self):
        if not self._gate(): return
        if self.path == "/arcgisearth/camera":
            with earth.lock: earth.camera = self._body()
            self._send(200, {})
        else: self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._gate(): return
        if self.path == "/arcgisearth/drawings":
            d = self._body()
            with earth.lock: earth.drawings[d["id"]] = d
            self._send(200, {"id": d["id"]})
        else: self._send(404, {"error": "not found"})

    def do_DELETE(self):
        if not self._gate(): return
        did = self.path.rsplit("/", 1)[-1]
        with earth.lock:
            if did in earth.drawings:
                del earth.drawings[did]; self._send(200, {})
            else:
                self._send(404, {"error": "Drawing not found"})


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
API = f"http://127.0.0.1:{server.server_address[1]}"


# ---------------- virtual serial line fed by Jim's Gold tester ----------------
class Line:
    """One 'cable': a pty pair. The Gold tester writes to the master end."""
    def __init__(self):
        self.master, self.slave = pty.openpty()
        tty.setraw(self.slave)
        self.port_name = os.ttyname(self.slave)

    def unplug(self):
        with contextlib.suppress(OSError): os.close(self.master)


class GoldPort:
    """Stands in for serial.Serial(OUTPUT_PORT) inside the Gold tester."""
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def write(self, data):
        line = current_line[0]
        if gold_status["no_fix"]:
            data = data.replace(b",A,", b",V,", 1)  # RMC status A -> V (fix lost)
            if data.startswith(b"$GPRMC"):
                body = data.decode().strip()[1:].split("*")[0]
                data = (gold.wrap_nmea_body(body) + "\r\n").encode()
        if line is not None:
            with contextlib.suppress(OSError): os.write(line.master, data)
        return len(data)


gold_status = {"no_fix": False}
current_line = [Line()]
gold = load(GOLD, "gold")
gold.serial = type("S", (), {"Serial": GoldPort})
gold.ENABLE_TEXT_LOG = False; gold.SHOW_RMC_SENTENCES = False; gold.SHOW_PRAVE_SENTENCES = False
gold.PRAVE_MIN_INTERVAL_SECONDS, gold.PRAVE_MAX_INTERVAL_SECONDS = 0.4, 0.8   # faster cycle for testing
gold.RANDOM_SEED = 22
threading.Thread(target=lambda: gold.run_connected_session(), daemon=True).start()

# ---------------- tracker ----------------
t = load(TRACKER, "tracker")
t.serial = serial
t.INPUT_PORT = current_line[0].port_name
t.ARCGIS_EARTH_API_BASE = API
t.RECONNECT_DELAY_SECONDS = 1.0
t.SHOW_VALID_PRAVE = False; t.SHOW_STATUS_SUMMARY = False
icons = os.path.join(WORK, "Icons"); os.makedirs(icons, exist_ok=True)
for name in t.RSSI_ICON_FILENAMES.values():
    open(os.path.join(icons, name), "wb").write(b"\x89PNG fake")
t.ICON_FOLDER = icons
t.script_dir = lambda: __import__("pathlib").Path(WORK)
for f in ("AE_PRAVE_previous_units.json",):
    with contextlib.suppress(FileNotFoundError): os.remove(os.path.join(WORK, f))
with contextlib.suppress(FileNotFoundError): os.remove(os.path.join(WORK, "Logs", "AE_PRAVE_Live_Activity.log"))

out = io.StringIO()
result = {"version": VERSION, "scenario": SCENARIO}


def units_on_map():
    with earth.lock: return sorted(k for k in earth.drawings if k.startswith("AE_PRAVE_"))


def run_tracker():
    with contextlib.redirect_stdout(out):
        try:
            result["exit_code"] = t.main()
        except SystemExit as e:
            result["exit_code"] = e.code


def log_lines():
    p = os.path.join(WORK, "Logs", "AE_PRAVE_Live_Activity.log")
    return open(p).read().splitlines() if os.path.exists(p) else []


def finish():
    result["log_tail"] = [l[22:] for l in log_lines()][-6:]
    sys.__stdout__.write(json.dumps(result) + "\n"); sys.__stdout__.flush(); os._exit(0)


# ---------------- scenarios ----------------
if SCENARIO == "normal":
    sys.argv = ["tracker"]; threading.Thread(target=run_tracker, daemon=True).start()
    time.sleep(8)
    with earth.lock:
        d = {k: {"title": v["title"], "xy": [round(v["geometry"]["x"], 6), round(v["geometry"]["y"], 6)],
                 "icon": os.path.basename(v.get("symbol", {}).get("url", "")), "label": v["labelSymbol"]}
             for k, v in earth.drawings.items()}
        cam = earth.camera
    result["drawings"] = d
    result["camera"] = {"xy": [round(cam["position"]["x"], 6), round(cam["position"]["y"], 6)],
                        "z": cam["position"]["z"], "heading": cam["heading"], "tilt": cam["tilt"]}
    finish()

if SCENARIO == "reconnect":
    sys.argv = ["tracker"]; threading.Thread(target=run_tracker, daemon=True).start()
    time.sleep(6)
    result["units_before_unplug"] = units_on_map()
    old = current_line[0]; current_line[0] = None; old.unplug()     # cable pulled
    time.sleep(0.5)
    new = Line(); t.INPUT_PORT = new.port_name                      # cable plugged back in
    time.sleep(0.6)
    result["units_right_after_reconnect"] = units_on_map()
    current_line[0] = new                                            # data flows again
    sp = os.path.join(WORK, "AE_PRAVE_previous_units.json")
    state = json.load(open(sp)) if os.path.exists(sp) else "(state file deleted)"
    result["state_file_after_reconnect"] = state
    time.sleep(0.2)
    result["reconnect_logged"] = any("RECONNECT" in l for l in log_lines())
    finish()

if SCENARIO == "startup_clean":
    # A previous session left drawings on the map and in the state file.
    with earth.lock:
        for i in ("7101", "7102", "9999"):
            earth.drawings[f"AE_PRAVE_{i}"] = {"id": f"AE_PRAVE_{i}"}
        earth.drawings["AE_ME"] = {"id": "AE_ME"}
    json.dump(["7101", "7102", "9999"], open(os.path.join(WORK, "AE_PRAVE_previous_units.json"), "w"))
    current_line[0] = None   # no data yet, so only startup cleaning acts
    sys.argv = ["tracker"]; threading.Thread(target=run_tracker, daemon=True).start()
    time.sleep(1.5)
    with earth.lock: result["drawings_after_start"] = sorted(earth.drawings)
    finish()

if SCENARIO == "api_down":
    sys.argv = ["tracker"]; threading.Thread(target=run_tracker, daemon=True).start()
    time.sleep(4)
    earth.mode = "error500"; time.sleep(4); earth.mode = "up"; time.sleep(4)
    c = t_state = None
    lines = log_lines()
    result["api_bad_lines"] = sum("API_BAD" in l for l in lines)
    result["rmc_bad_lines"] = sum("RMC_BAD" in l for l in lines)
    result["prave_bad_lines"] = sum("PRAVE_BAD" in l for l in lines)
    result["units_after_recovery"] = units_on_map()
    with earth.lock: result["me_after_recovery"] = "AE_ME" in earth.drawings
    finish()

if SCENARIO == "no_fix":
    sys.argv = ["tracker"]; threading.Thread(target=run_tracker, daemon=True).start()
    time.sleep(2); gold_status["no_fix"] = True; time.sleep(6); gold_status["no_fix"] = False; time.sleep(2.5)
    lines = log_lines()
    result["rmc_bad_lines"] = sum("RMC_BAD" in l for l in lines)
    result["no_fix_lines"] = sum("GPS_NO_FIX" in l for l in lines)
    result["fix_restored_lines"] = sum("GPS_FIX_RESTORED" in l for l in lines)
    finish()

if SCENARIO == "no_pyserial":
    t.serial = None
    sys.argv = ["tracker"]; th = threading.Thread(target=run_tracker, daemon=True); th.start()
    th.join(4)
    result["still_running_after_4s"] = th.is_alive()
    result["error_lines"] = sum("pyserial is not installed" in l for l in log_lines())
    finish()

if SCENARIO == "no_icons":
    t.ICON_FOLDER = os.path.join(WORK, "missing_icon_folder")
    sys.argv = ["tracker"]; threading.Thread(target=run_tracker, daemon=True).start()
    time.sleep(5)
    lines = log_lines()
    result["icon_warning_lines"] = sum("ICON_WARNING" in l for l in lines)
    result["first_icon_warning"] = next((l[22:] for l in lines if "ICON_WARNING" in l), None)
    result["units_still_drawn"] = len(units_on_map())
    finish()

if SCENARIO == "missing_some_icons":
    os.remove(os.path.join(icons, "firetruck_rssi_3.png"))
    sys.argv = ["tracker"]; threading.Thread(target=run_tracker, daemon=True).start()
    time.sleep(8)
    lines = log_lines()
    result["icon_warning_lines"] = sum("ICON_WARNING" in l for l in lines)
    result["warnings"] = [l[22:] for l in lines if "ICON_WARNING" in l][:3]
    finish()

print(json.dumps({"error": "unknown scenario"})); os._exit(1)
