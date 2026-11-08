"""PRAVE/ME Tracker 2.1 vs 2.0. A scripted radio feed (Gold sentence formats) goes down a virtual serial
cable (pty) into the real tracker; a stand-in ArcGIS Earth (local HTTP) records every API request and can be
switched off and on.

python3 prave_tracker_test_v21.py <2.0 PRAVE_ME_Tracker.py> <2.1 PRAVE_ME_Tracker.py> <pyserial source dir>
(one scenario per child process: ... --child <tracker.py> <scenario>)
"""
import contextlib, importlib.util, io, json, os, pathlib, pty, subprocess, sys, threading, time, tty
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve()

# ------------------------------------------------------------------ driver
if "--child" not in sys.argv:
    OLD, NEW, PYSERIAL = sys.argv[1:4]
    def child(tracker, scenario):
        r = subprocess.run([sys.executable, str(HERE), "--child", tracker, scenario, PYSERIAL],
                           capture_output=True, text=True, timeout=120)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return {"crash": (r.stdout + r.stderr)[-800:]}
    results = []
    def check(name, ok, detail=""): results.append((bool(ok), name, detail))

    a, b = child(OLD, "normal"), child(NEW, "normal")
    check(f"normal run: the same {len(a.get('requests', []))} ArcGIS Earth requests, in order, byte for byte (2.0 = 2.1)",
          a.get("requests") and a.get("requests") == b.get("requests"), (a.get("crash"), b.get("crash")))
    check("2.1 self-test PASS", b.get("self_test") == 0)

    a, b = child(OLD, "earth_restart"), child(NEW, "earth_restart")
    check(f"2.0 ArcGIS Earth gone 4 s: {a.get('down_lines')} 'not reachable' log lines; map empty after restart until units report "
          f"({a.get('units_after_restart')})", a.get("down_lines", 0) >= 3 and a.get("units_after_restart") == [], a)
    check(f"2.1 ArcGIS Earth gone 4 s: 'lost' logged once ({b.get('lost_lines')}), 'back' once ({b.get('back_lines')})",
          b.get("lost_lines") == 1 and b.get("back_lines") == 1 and b.get("down_lines") == 1, b)
    check(f"2.1 after the restart all {len(b.get('units_after_restart', []))} units + ME are back with no new reports",
          len(b.get("units_after_restart", [])) == 6 and b.get("me_after_restart"), b)
    check("2.1 radio data kept being logged while ArcGIS Earth was gone", b.get("prave_rows_while_down", 0) > 0, b)

    b = child(NEW, "earth_closed_at_start")
    check(f"2.1 ArcGIS Earth closed at start: one ERROR line over 4 s ({b.get('error_lines')}), then it connects when it opens",
          b.get("error_lines") == 1 and b.get("connected"), b)

    for sc, want in (("port_missing", "was not found. Serial ports on this PC:"), ("port_missing_windows", "COM12 was not found"),
                     ("port_busy_windows", "COM12 is in use by another program")):
        a, b = child(OLD, sc), child(NEW, sc)
        check(f"{sc}: 2.0 says it {a.get('error_lines')} times in 4 s (raw pyserial text)", a.get("error_lines", 0) >= 3, a.get("first_error"))
        check(f"{sc}: 2.1 says it once, in plain words", b.get("error_lines") == 1 and want in (b.get("first_error") or ""), b.get("first_error"))
    b = child(NEW, "port_appears")
    check("2.1 port plugged in later: connects and draws units", b.get("connected") and len(b.get("units", [])) == 6, b)

    a, b = child(OLD, "daily_logs"), child(NEW, "daily_logs")
    check("2.0 log names have no date", a.get("files") == ["AE_PRAVE_Live_Activity.log", "AE_PRAVE_Packet_History.csv", "AE_RMC_Position_History.csv"], a)
    check(f"2.1 one file per day: {b.get('files')}", b.get("files") == [f"AE_PRAVE_Live_Activity_{b.get('today')}.log",
          f"AE_PRAVE_Packet_History_{b.get('today')}.csv", f"AE_RMC_Position_History_{b.get('today')}.csv"], b)

    a, b = child(OLD, "stale"), child(NEW, "stale")
    check("2.0: a unit quiet for 12 min still shows only '7-101'", a.get("titles", {}).get("AE_PRAVE_7101") == "7-101", a.get("titles"))
    check("2.1: quiet 12 min -> '7-101 · 12 min'; a fresh report -> '7-102'",
          b.get("titles", {}).get("AE_PRAVE_7101") == "7-101 · 12 min" and b.get("fresh_title") == "7-102", (b.get("titles"), b.get("fresh_title")))
    check("2.1: 2 h 05 min shows '7-101 · 2 h 05 min'", b.get("two_hours") == "7-101 · 2 h 05 min", b.get("two_hours"))

    for ok, name, detail in results:
        print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    print("ALL PASS" if all(r[0] for r in results) else f"{sum(not r[0] for r in results)} FAILED")
    sys.exit(0 if all(r[0] for r in results) else 1)

# ------------------------------------------------------------------ child
TRACKER, SCENARIO, PYSERIAL = sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, PYSERIAL)
import serial  # noqa: E402

WORK = pathlib.Path(os.environ.get("WORK", "/tmp/pt21")) / f"{pathlib.Path(TRACKER).parent.name}_{SCENARIO}"
import shutil; shutil.rmtree(WORK, ignore_errors=True); WORK.mkdir(parents=True)


class Earth:
    drawings, requests, camera = {}, [], {"position": {"x": -81.0, "y": 30.0, "z": 4321.0, "spatialReference": {"wkid": 4326}},
                                          "heading": 17.0, "tilt": 5.0, "roll": 0.0}
    lock = threading.Lock()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, obj=None):
        body = b"" if obj is None else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def _body(self):
        n = int(self.headers.get("Content-Length") or 0); return self.rfile.read(n)
    def do_GET(self):
        with Earth.lock: Earth.requests.append(("GET", self.path, ""))
        self._send(200, Earth.camera) if self.path == "/arcgisearth/camera" else self._send(404, {"error": "not found"})
    def do_PUT(self):
        raw = self._body()
        with Earth.lock: Earth.requests.append(("PUT", self.path, raw.decode())); Earth.camera = json.loads(raw)
        self._send(200, {})
    def do_POST(self):
        raw = self._body(); d = json.loads(raw)
        with Earth.lock: Earth.requests.append(("POST", self.path, raw.decode())); Earth.drawings[d["id"]] = d
        self._send(200, {"id": d["id"]})
    def do_DELETE(self):
        did = self.path.rsplit("/", 1)[-1]
        with Earth.lock:
            Earth.requests.append(("DELETE", self.path, ""))
            if did in Earth.drawings: del Earth.drawings[did]; self._send(200, {})
            else: self._send(404, {"error": "Drawing not found"})


srv = [None]; PORT = [0]
def earth_on():
    s = ThreadingHTTPServer(("127.0.0.1", PORT[0]), H); s.daemon_threads = True
    PORT[0] = s.server_address[1]; srv[0] = s; threading.Thread(target=s.serve_forever, daemon=True).start()
def earth_off():
    srv[0].shutdown(); srv[0].server_close()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m; spec.loader.exec_module(m); return m


t = load(TRACKER, "tracker")
t.serial = serial
master, slave = pty.openpty(); tty.setraw(slave)
t.INPUT_PORT = os.ttyname(slave)
t.RECONNECT_DELAY_SECONDS = 1.0
t.SHOW_VALID_PRAVE = False; t.SHOW_STATUS_SUMMARY = False
icons = WORK / "Icons"; icons.mkdir()
for n in t.RSSI_ICON_FILENAMES.values(): (icons / n).write_bytes(b"\x89PNG fake")
t.ICON_FOLDER = str(icons)
t.script_dir = lambda: WORK
if hasattr(t, "EARTH_RETRY_SECONDS"): t.EARTH_RETRY_SECONDS = 1.0

# clock that the scenario can move forward (stale labels)
OFFSET = [0.0]
real_mono = time.monotonic
t.time = type("T", (), {"monotonic": staticmethod(lambda: real_mono() + OFFSET[0]), "sleep": staticmethod(time.sleep)})

# scripted feed in the Gold formats (units 7-101..7-106, RSSI blank,-115..-75)
RSSI = {"101": "", "102": "-115", "103": "-105", "104": "-95", "105": "-85", "106": "-75"}
def rmc(i):
    return t.make_nmea_sentence(f"GPRMC,2122{i % 60:02d}.00,A,3025.14642,N,08155.58994,W,0.0,0.0,240726,,,A")
def prave(ind, i):
    return t.make_nmea_sentence(f"PRAVE,01{ind[-2:]},1234,3025.{32642 + i * 7:05d},-08155.{58994 + i * 3:05d},2122{i % 60:02d},"
                                f"2,12,7,0,12.80,0,{RSSI[ind]},{ind},0,,")
feed_on = [True]
def send(line):
    with contextlib.suppress(OSError): os.write(master, (line + "\r\n").encode())
def feed(rounds, units=tuple(RSSI), gap=0.05):
    for i in range(rounds):
        send(rmc(i)); time.sleep(gap)
        for u in units:
            send(prave(u, i)); time.sleep(gap)

out = io.StringIO(); result = {}
def run():
    with contextlib.redirect_stdout(out):
        sys.argv = ["tracker"]
        try: result["exit"] = t.main()
        except SystemExit as e: result["exit"] = e.code
def start(): threading.Thread(target=run, daemon=True).start()
def log_lines():
    files = sorted((WORK / "Logs").glob("AE_PRAVE_Live_Activity*.log"))
    return [l for f in files for l in f.read_text().splitlines()]
def units():
    with Earth.lock: return sorted(k for k in Earth.drawings if k.startswith("AE_PRAVE_"))
def finish():
    result["log_tail"] = [l[22:200] for l in log_lines()][-5:]
    sys.__stdout__.write(json.dumps(result) + "\n"); sys.__stdout__.flush(); os._exit(0)


if SCENARIO == "normal":
    earth_on(); t.ARCGIS_EARTH_API_BASE = f"http://127.0.0.1:{PORT[0]}"
    start(); time.sleep(1.0); feed(5); time.sleep(1.0)
    with Earth.lock: result["requests"] = [(m, u, b.replace(str(WORK), "<WORK>")) for m, u, b in Earth.requests]   # icon path = rig folder
    with contextlib.redirect_stdout(io.StringIO()): result["self_test"] = t.run_self_test()
    finish()

if SCENARIO == "earth_restart":
    earth_on(); t.ARCGIS_EARTH_API_BASE = f"http://127.0.0.1:{PORT[0]}"
    start(); time.sleep(1.0); feed(2); time.sleep(0.5)
    earth_off()
    rows0 = sum(1 for f in (WORK / "Logs").glob("AE_PRAVE_Packet_History*.csv") for _ in open(f))
    end = time.time() + 4
    i = 2
    while time.time() < end: feed(1); i += 1
    result["prave_rows_while_down"] = sum(1 for f in (WORK / "Logs").glob("AE_PRAVE_Packet_History*.csv") for _ in open(f)) - rows0
    with Earth.lock: Earth.drawings.clear()          # ArcGIS Earth restarted: empty map
    earth_on()
    for k in range(6): send(rmc(100 + k)); time.sleep(0.4)  # GPS only - no unit reports after the restart
    time.sleep(1.5)
    result["units_after_restart"] = units()
    with Earth.lock: result["me_after_restart"] = "AE_ME" in Earth.drawings
    L = log_lines()
    result["down_lines"] = sum("not reachable" in l for l in L)
    result["lost_lines"] = sum("ARCGIS_EARTH_LOST" in l for l in L)
    result["back_lines"] = sum("ARCGIS_EARTH_BACK" in l for l in L)
    finish()

if SCENARIO == "earth_closed_at_start":
    earth_on(); t.ARCGIS_EARTH_API_BASE = f"http://127.0.0.1:{PORT[0]}"; earth_off()
    start(); time.sleep(4); earth_on(); time.sleep(2.0)
    L = log_lines()
    result["error_lines"] = sum(" ERROR " in l for l in L)
    result["connected"] = any("SERIAL_CONNECTED" in l for l in L)
    finish()

if SCENARIO.startswith("port_"):
    earth_on(); t.ARCGIS_EARTH_API_BASE = f"http://127.0.0.1:{PORT[0]}"
    if SCENARIO == "port_missing":
        t.INPUT_PORT = "/dev/ttyNOPE12"
    elif SCENARIO in ("port_missing_windows", "port_busy_windows"):
        t.INPUT_PORT = "COM12"
        text = ("could not open port 'COM12': FileNotFoundError(2, 'The system cannot find the file specified.', None, 2)"
                if SCENARIO == "port_missing_windows" else "could not open port 'COM12': PermissionError(13, 'Access is denied.', None, 5)")
        def fail(*a, **k): raise serial.SerialException(text)
        t.serial = type("S", (), {"Serial": staticmethod(fail), "SerialException": serial.SerialException,
                                  "EIGHTBITS": 8, "PARITY_NONE": "N", "STOPBITS_ONE": 1})
    elif SCENARIO == "port_appears":
        real = t.INPUT_PORT; t.INPUT_PORT = "/dev/ttyNOPE12"
    start(); time.sleep(4)
    if SCENARIO == "port_appears":
        t.INPUT_PORT = real; time.sleep(1.5); feed(2); time.sleep(0.5)
        result["connected"] = any("SERIAL_CONNECTED" in l for l in log_lines()); result["units"] = units()
    L = [l for l in log_lines() if " ERROR " in l]
    result["error_lines"] = len(L); result["first_error"] = L[0][22:] if L else None
    finish()

if SCENARIO == "daily_logs":
    earth_on(); t.ARCGIS_EARTH_API_BASE = f"http://127.0.0.1:{PORT[0]}"
    start(); time.sleep(1.0); feed(2); time.sleep(0.5)
    result["files"] = sorted(p.name for p in (WORK / "Logs").iterdir()); result["today"] = datetime.now().strftime("%Y-%m-%d")
    finish()

if SCENARIO == "stale":
    earth_on(); t.ARCGIS_EARTH_API_BASE = f"http://127.0.0.1:{PORT[0]}"
    if hasattr(t, "STALE_AFTER_MINUTES"): t.STALE_AFTER_MINUTES = 5
    start(); time.sleep(1.0); feed(2); time.sleep(0.5)
    OFFSET[0] = 12 * 60 + 5; time.sleep(11)          # the 10-second tick sees 12 quiet minutes
    with Earth.lock: result["titles"] = {k: v["title"] for k, v in Earth.drawings.items() if k.startswith("AE_PRAVE_")}
    send(prave("102", 9)); time.sleep(0.8)
    with Earth.lock: result["fresh_title"] = Earth.drawings.get("AE_PRAVE_7102", {}).get("title")
    if hasattr(t, "unit_label"):
        u = next(iter([v for k, v in []]), None)
        p = t.parse_prave_sentence(prave("101", 1)); p.received_monotonic = t.time.monotonic() - (2 * 3600 + 5 * 60 + 3)
        result["two_hours"] = t.unit_label(p)
    finish()

print(json.dumps({"error": "unknown scenario"})); os._exit(1)
