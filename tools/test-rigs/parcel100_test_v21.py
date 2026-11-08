"""Parcel100 2.1 vs 2.0 against the parcel test server (parcel_test_server.py). Runs each version's own
_build_worker headless (stand-in Tk: after() runs at once, message boxes are recorded).

python3 parcel100_test_v21.py <2.0 Parcel100.py> <2.1 Parcel100.py>
"""
import os, shutil, sys, threading, types, pathlib, json
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import parcel_test_server as server

BOXES = []
fake = types.ModuleType("tkinter"); fake.Tk = type("Tk", (), {}); fake.TclError = type("TclError", (Exception,), {})
for sub in ("filedialog", "messagebox", "ttk"):
    m = types.ModuleType("tkinter." + sub); setattr(fake, sub, m); sys.modules["tkinter." + sub] = m
mb = sys.modules["tkinter.messagebox"]
mb.showinfo = lambda t, m, **k: BOXES.append(("info", m))
mb.showwarning = lambda t, m, **k: BOXES.append(("warning", m))
mb.showerror = lambda t, m, **k: BOXES.append(("error", m))
mb.ANSWER = True
mb.askyesnocancel = lambda t, m, **k: (BOXES.append(("ask", m)), mb.ANSWER)[1]
sys.modules["tkinter"] = fake


def load(path, name):
    mod = types.ModuleType(name); mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    mod.time = types.SimpleNamespace(sleep=lambda s: None)
    return mod


OLD, NEW = load(sys.argv[1], "p20"), load(sys.argv[2], "p21")
srv = server.start(0); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
BASE = f"http://127.0.0.1:{port}{server.ROOT}"
W = pathlib.Path(os.environ.get("WORK", "/tmp/p21")); shutil.rmtree(W, ignore_errors=True); W.mkdir(parents=True)
results = []
def check(name, ok, detail=""): results.append((bool(ok), name, detail))
def err(f):
    try: f(); return None
    except Exception as e: return f"{type(e).__name__}: {e}"


class Var:
    def __init__(self, v=""): self.v = v
    def get(self): return self.v
    def set(self, v): self.v = v


def app(mod, layer_url, fields, folder, master="82w,81w,30n,31n", precision=7):
    a = mod.Parcel100App.__new__(mod.Parcel100App)
    (lu, meta), = mod.discover_polygon_layers(layer_url)[0]
    a.meta, a.layer_url, a.worker = meta, lu, None
    a.after = lambda ms, f, *args: f(*args)
    a.status_var, a.url_var, a.master_var, a.precision_var, a.output_var = Var(), Var(lu), Var(master), Var(precision), Var(str(folder))
    a.progress = {}
    a.progress_configure = None
    a.progress = types.SimpleNamespace(configure=lambda *x, **k: None, __setitem__=None)
    a.set_busy = lambda b: None
    a._selected_field_names = lambda: list(fields)
    a.fields = [{"name": f} for f in fields]
    return a


def run(mod, layer_url, fields, folder):
    """build_clicked's checks + the build worker, synchronously."""
    a = app(mod, layer_url, fields, folder)
    started = []
    class T:
        def __init__(self, target, args, daemon): self.t, self.a = target, args
        def start(self): started.append(1); self.t(*self.a)
        def is_alive(self): return False
    mod.threading = types.SimpleNamespace(Thread=T)
    class P(dict):
        def configure(self, *x, **k): pass
    a.progress = P()
    BOXES.clear()
    a.build_clicked()
    return a, list(BOXES), bool(started)


def files(folder):
    return {p.name: p.read_bytes() for p in sorted(pathlib.Path(folder).glob("*.geojson"))}


FL = ["OWN_NAME", "PHY_ADDR1", "PARCEL_ID", "ACRES"]
# 1. clean layer: same files from 2.0 and 2.1
_, b20, _ = run(OLD, BASE + "/1", FL, W / "c20")
_, b21, _ = run(NEW, BASE + "/1", FL, W / "c21")
f20, f21 = files(W / "c20"), files(W / "c21")
check("clean layer: same file names (cells 039 + 040)", list(f20) == list(f21) and len(f21) == 2, list(f21))
check("clean layer: files byte-identical 2.0 / 2.1", f20 == f21)
check("2.1 message: 100 cells = 2 written + 0 already there + 98 empty; 5 parcels", b21 and "100 cells:\n   2 written\n   0 already there (skipped)\n   98 empty" in b21[-1][1] and "5 parcels written into the 2 new files" in b21[-1][1], b21)
check("clean layer: no extra notes in 2.1's message", b21 and "no shape" not in b21[-1][1] and "Replaced" not in b21[-1][1])
# 1b. true resume: same layer + fields -> no question, all skipped
_, b, _ = run(NEW, BASE + "/1", FL, W / "c21")
check("resume (same layer, same fields): no question, 2 skipped", not any(k == "ask" for k, _ in b) and "0 written" in b[-1][1] and "2 already there" in b[-1][1] and "98 empty" in b[-1][1], b)

# 2. empty shape {}: 2.0 stops, 2.1 writes it without a shape and counts it
_, b, _ = run(OLD, BASE + "/0", FL, W / "o20")
check("2.0 odd layer: build stops on the empty shape", any(k == "error" and "non-polygon" in m for k, m in b), b)
_, b, _ = run(NEW, BASE + "/0", FL, W / "o21")
c40 = json.loads((W / "o21" / NEW.output_name("82W_81W_30N_31N", 40)).read_text())
check("2.1 odd layer: cell 040 has 4 parcels, one with no shape", len(c40["features"]) == 4 and sum(f["geometry"] is None for f in c40["features"]) == 1)
check("2.1 odd layer: message counts 1 parcel with no shape", b and "1 parcel record(s) came from the service with no shape" in b[-1][1], b)

# 3. another layer into the same folder -> question; Keep / Replace / Cancel
OTHER = ["OWNER", "SITUS", "APN", "AREA_AC"]
before = files(W / "c21")
_, b, _ = run(OLD, BASE + "/2", OTHER, W / "c21")
check("2.0: another layer into the same folder - no question, old files kept", not any(k == "ask" for k, _ in b) and files(W / "c21") == before)
mb.ANSWER = None
_, b, started = run(NEW, BASE + "/2", OTHER, W / "c21")
check("2.1: asks, naming the cells and 'another layer'", any(k == "ask" and "039, 040" in m and "another layer" in m for k, m in b), b)
check("2.1 Cancel: nothing built, files untouched", not started and files(W / "c21") == before)
mb.ANSWER = False
_, b, _ = run(NEW, BASE + "/2", OTHER, W / "c21")
check("2.1 No (keep): old files kept", files(W / "c21") == before)
mb.ANSWER = True
_, b, _ = run(NEW, BASE + "/2", OTHER, W / "c21")
c39 = json.loads((W / "c21" / NEW.output_name("82W_81W_30N_31N", 39)).read_text())
check("2.1 Yes (replace): files now from the other layer with its fields",
      c39["source"].endswith("/2") and list(c39["features"][0]["properties"]) == OTHER, (c39["source"], list(c39["features"][0]["properties"])))
check("2.1 Yes: message lists the replaced cells", "Replaced old cell files" in b[-1][1] and "039, 040" in b[-1][1], b[-1])
# same layer, other fields
mb.ANSWER = None
_, b, _ = run(NEW, BASE + "/2", ["OWNER", "APN"], W / "c21")
check("2.1: same layer, fewer fields -> asks 'other fields'", any(k == "ask" and "other fields" in m for k, m in b), b)
# replace where the new layer has nothing: the old file is removed
mb.ANSWER = True
(W / "e").mkdir()
for n, data in files(W / "c20").items():
    (W / "e" / n).write_bytes(data)
fake_name = NEW.output_name("82W_81W_30N_31N", 55)
(W / "e" / fake_name).write_text(json.dumps({"type": "FeatureCollection", "source": "https://other/FeatureServer/9",
                                              "features": [{"type": "Feature", "properties": {"X": 1}, "geometry": None}]}))
run(NEW, BASE + "/1", FL, W / "e")
check("2.1 Yes: an old-layer cell the new layer leaves empty is removed", not (W / "e" / fake_name).exists())

# 4. URLs and messages
for u in (BASE + "/1?f=pjson", BASE + "/1/#x", BASE + "?f=json", BASE + "/1/query?where=1%3D1"):
    check(f"2.1 accepts {u.split(server.ROOT)[1] or '(root)'}", err(lambda: NEW.discover_polygon_layers(u)) is None, err(lambda: NEW.discover_polygon_layers(u)))
check("2.0 refused ?f=pjson", err(lambda: OLD.discover_polygon_layers(BASE + "/1?f=pjson")) is not None)
login = f"http://127.0.0.1:{port}/login/arcgis/rest/services/X/FeatureServer/0"
e_old, e_new = err(lambda: OLD.discover_polygon_layers(login)), err(lambda: NEW.discover_polygon_layers(login))
check("2.0 login page -> programmer message", e_old and "Expecting value" in e_old, e_old)
check("2.1 login page -> plain message", e_new and "did not send map data" in e_new, e_new)
e = err(lambda: NEW.parse_master4("-82,-81,30,31"))
check("2.1 Master 4 typed as numbers -> example in the message", e and "82w,81w,30n,31n" in e, e)
a = app(NEW, BASE + "/1", FL, W / "x")
a.precision_var = Var("abc"); BOXES.clear(); a.build_clicked()
check("2.1 precision 'abc' -> plain message", BOXES and BOXES[-1][0] == "error" and "whole number from 5 to 12" in BOXES[-1][1], BOXES)
check("header reader: source + fields of a cell file",
      NEW.read_cell_header(W / "c20" / NEW.output_name("82W_81W_30N_31N", 39)) == (BASE + "/1", FL))

srv.shutdown()
for ok, name, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
print("ALL PASS" if all(r[0] for r in results) else f"{sum(not r[0] for r in results)} FAILED")
sys.exit(0 if all(r[0] for r in results) else 1)
