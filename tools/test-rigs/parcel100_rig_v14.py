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


def build(batch_size=2000, stop_after_cells=None, crash_on_write_of=None):
    """Replays Parcel100App._build_worker (minus the window)."""
    w0, e0, s0, n0, label = p.parse_master4("82w,81w,30n,31n")
    stats = dict(written=0, existing=0, empty=0, records=0)
    for idx, (cell, w, e, s, n) in enumerate(p.cell_bounds(w0, e0, s0, n0), start=1):
        path = OUT / p.output_name(label, cell)
        if path.exists():
            stats["existing"] += 1; continue
        ids, _ = p.query_object_ids_with_fallback(URL, (w, e, s, n))
        if not ids:
            stats["empty"] += 1; continue
        feats = p.query_features_json(URL, ids, FIELDS, 7, batch_size)
        if crash_on_write_of == cell:
            # Simulate the window being closed (daemon thread killed) part-way through json.dump.
            real_dump = p.json.dump
            def half_dump(obj, f, **kw):
                text = json.dumps(obj, **kw); f.write(text[: len(text) // 2]); raise SystemExit("window closed")
            p.json.dump = half_dump
            try:
                p.write_feature_collection(path, feats, label, cell, (w, e, s, n), URL)
            except SystemExit:
                p.json.dump = real_dump
                return stats, "interrupted while writing cell %03d" % cell
        p.write_feature_collection(path, feats, label, cell, (w, e, s, n), URL)
        stats["written"] += 1; stats["records"] += len(feats)
        stats.setdefault("ids", 0); stats["ids"] += len(ids)
    return stats, "complete"


r = {"scenario": SCENARIO}
try:
    if SCENARIO == "normal":
        st, how = build(); r.update(st, result=how)
    elif SCENARIO == "interrupted_write_then_resume":
        st, how = build(crash_on_write_of=37); r["first_run"] = how
        st2, how2 = build(); r["resume"] = {k: st2[k] for k in ("written", "existing")}
        bad = []
        for f in sorted(OUT.glob("*.geojson")):
            try: json.load(open(f))
            except Exception: bad.append(f.name)
        r["broken_files_left_after_resume"] = bad
    elif SCENARIO == "server_drops_features":
        Svc.drop = 2
        st, how = build(batch_size=10); r.update(ids=st.get("ids"), records=st["records"], result=how, warning="none")
    elif SCENARIO == "big_batch_504":
        Svc.fail_big_batches = 20
        st, how = build(batch_size=2000); r.update(st, result=how)
except Exception as e:
    r["error"] = f"{type(e).__name__}: {str(e)[:120]}"
sys.__stdout__.write(json.dumps(r) + "\n")
