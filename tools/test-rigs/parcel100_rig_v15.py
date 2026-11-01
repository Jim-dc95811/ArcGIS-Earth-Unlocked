"""Parcel100 rig: mock polygon FeatureServer + Parcel100's own functions, replaying _build_worker's loop."""
import json, os, sys, threading, types, urllib.parse, pathlib, shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PATH, SCENARIO = sys.argv[1], sys.argv[2]
OUT = pathlib.Path(__file__).parent / "out" / SCENARIO
shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir(parents=True)

fake = types.ModuleType("tkinter"); fake.Tk = type("Tk", (), {})
for sub in ("filedialog", "messagebox", "ttk"):
    m = types.ModuleType("tkinter." + sub); setattr(fake, sub, m); sys.modules["tkinter." + sub] = m
sys.modules["tkinter"] = fake
p = types.ModuleType("p100"); p.__file__ = PATH
exec(compile(open(PATH).read(), PATH, "exec"), p.__dict__)
p.time = types.SimpleNamespace(sleep=lambda s: None)

GRID = 6          # parcels per cell side -> 36 per cell
class Svc:
    drop = 0              # features silently not returned per feature batch
    fail_big_batches = 0  # feature batches larger than this get HTTP 504 (0 = never)


def parcel(oid):
    cell, k = divmod(oid - 1, GRID * GRID)
    row, col = divmod(cell, 10)
    r, c = divmod(k, GRID)
    w = -81.0 - (col + 1) / 10 + c * (0.1 / GRID) + 0.001
    s = 30.0 + row / 10 + r * (0.1 / GRID) + 0.001
    d = 0.1 / GRID - 0.002
    ring = [[w, s], [w, s + d], [w + d, s + d], [w + d, s], [w, s]]
    return {"attributes": {"OBJECTID": oid, "OWN_NAME": f"OWNER {oid}", "PARCEL_ID": f"P{oid:06d}", "Acres": 1.5},
            "geometry": {"rings": [ring]}}


ALL = {oid: parcel(oid) for oid in range(1, 100 * GRID * GRID + 1)}


def bbox_of(f):
    xs = [x for x, _ in f["geometry"]["rings"][0]]; ys = [y for _, y in f["geometry"]["rings"][0]]
    return min(xs), max(xs), min(ys), max(ys)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        q = dict(urllib.parse.parse_qsl(self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()))
        if self.path.rstrip("/").endswith("/0/query"):
            if q.get("returnIdsOnly") == "true":
                w, s, e, n = (float(v) for v in q["geometry"].split(","))
                ids = [o for o, f in ALL.items() if (lambda b: b[0] < e and b[1] > w and b[2] < n and b[3] > s)(bbox_of(f))]
                return self._send({"objectIdFieldName": "OBJECTID", "objectIds": ids})
            ids = [int(x) for x in q["objectIds"].split(",")]
            if Svc.fail_big_batches and len(ids) > Svc.fail_big_batches:
                self.send_response(504); self.end_headers(); return
            if Svc.drop: ids = ids[:-Svc.drop]
            out = q["outFields"].split(",")
            return self._send({"features": [{"attributes": {k: v for k, v in ALL[i]["attributes"].items() if k in out},
                                             "geometry": ALL[i]["geometry"]} for i in ids]})
        if self.path.rstrip("/").endswith("/0"):
            return self._send({"type": "Feature Layer", "name": "Parcels", "geometryType": "esriGeometryPolygon",
                               "maxRecordCount": 2000, "objectIdField": "OBJECTID",
                               "fields": [{"name": n, "type": "esriFieldTypeString"} for n in ("OBJECTID", "OWN_NAME", "PARCEL_ID", "Acres")]})
        self.send_response(404); self.end_headers()


srv = ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/arcgis/rest/services/Parcels/FeatureServer/0"
FIELDS = ["OWN_NAME", "PARCEL_ID", "Acres"]

class Svc2: drop_once = set()
_orig_post = H.do_POST
def do_POST(self):
    # drop_once: those IDs are missing from the first feature request only
    if Svc2.drop_once and "objectIds=" in (self.headers.get("X-peek") or ""):
        pass
    return _orig_post(self)
H.do_POST = do_POST

class Var:
    def __init__(self, v=""): self.v = v
    def get(self): return self.v
    def set(self, v): self.v = v
class Fake:
    def __init__(self):
        self.status_var = Var(); self.url_var = Var(URL); self.layer_url = URL
        self.progress = types.SimpleNamespace(configure=lambda *a, **k: None)
        self.meta = {"maxRecordCount": 2000, "objectIdField": "OBJECTID"}
        self.done = None; self.err = None; self.statuses = []
    def after(self, ms, fn, *a): fn(*a)
    def _build_done(self, *a): self.done = a
    def _error(self, msg): self.err = msg
_set = Var.set
def run(meta_max=2000):
    f = Fake(); f.meta["maxRecordCount"] = meta_max
    f.status_var.set = lambda v: (f.statuses.append(v), _set(f.status_var, v))
    master = p.parse_master4("82w,81w,30n,31n")
    p.Parcel100App._build_worker(f, master, FIELDS, 7, OUT)
    return f

def summary(f):
    if f.err: return {"error": f.err[:200]}
    out_dir, total, written, existing, empty, rebuilt, short = f.done
    return dict(records=total, written=written, existing=existing, empty=empty, rebuilt=list(rebuilt),
                shortfall_cells=len(short), missing=sum(n for _, n, _ in short))

def broken():
    bad = []
    for g in sorted(OUT.glob("*.geojson")):
        try: json.load(open(g))
        except Exception: bad.append(g.name)
    return bad

r = {"scenario": SCENARIO}
if SCENARIO == "normal":
    r.update(summary(run()))
elif SCENARIO == "interrupted_write_then_resume":
    real = p.json.dump; n = {"c": 0}
    def half(obj, fh, **kw):
        n["c"] += 1
        if n["c"] == 37:
            t = json.dumps(obj, **kw); fh.write(t[:len(t)//2]); raise SystemExit("window closed")
        return real(obj, fh, **kw)
    p.json.dump = half
    try: run()
    except SystemExit: r["first_run"] = "interrupted at cell write 37"
    p.json.dump = real
    r["files_after_crash"] = len(list(OUT.glob("*.geojson"))); r["partials_after_crash"] = len(list(OUT.glob("*.partial")))
    # Also plant a truncated file the way 1.4 would have left one.
    victim = sorted(OUT.glob("*.geojson"))[5]; t = victim.read_text(); victim.write_text(t[:len(t)//3])
    r["planted_truncated"] = victim.name
    r["resume"] = summary(run()); r["broken_files_left_after_resume"] = broken()
elif SCENARIO == "server_drops_features":
    Svc.drop = 2
    r.update(summary(run(meta_max=10)))
elif SCENARIO == "big_batch_504":
    Svc.fail_big_batches = 20
    r.update(summary(run())); r["broken"] = broken()
elif SCENARIO == "url_changed":
    f = Fake(); f.url_var.set(URL.replace("/0", "/3"))
    r["check"] = f.url_var.get().strip().rstrip("/") != (f.layer_url or "").rstrip("/")
r["partials_left"] = len(list(OUT.glob("*.partial")))
sys.__stdout__.write(json.dumps(r) + "\n")
