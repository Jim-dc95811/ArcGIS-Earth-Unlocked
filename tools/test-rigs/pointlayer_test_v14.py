"""PointLayer 1.4 vs 1.3: regression and hardening tests against a mock ArcGIS FeatureServer."""
import json, os, re, subprocess, sys, threading, types, zipfile, urllib.parse, pathlib, xml.dom.minidom
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).parent
V13, V14 = "/home/claude/repos/Point-Maps/PointLayer.py", "/home/claude/dev/pointlayer_v1.4/PointLayer.py"
W = HERE / "t14"
import shutil; shutil.rmtree(W, ignore_errors=True); W.mkdir()

fake = types.ModuleType("tkinter"); fake.Tk = type("Tk", (), {})
for sub in ("filedialog", "messagebox", "ttk"):
    m = types.ModuleType("tkinter." + sub); setattr(fake, sub, m); sys.modules["tkinter." + sub] = m
sys.modules["tkinter"] = fake


def load(path, name):
    mod = types.ModuleType(name); mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    mod.time = types.SimpleNamespace(sleep=lambda s: None)
    return mod


p13, p14 = load(V13, "pl13"), load(V14, "pl14")
results = []


def check(name, ok, detail=""):
    results.append((ok, name, detail))


class Svc:
    n, max_record, drop_per_batch, drop_once, null_every, same_lat, ctrl, no_oid_field = 3250, 1000, 0, set(), 0, False, False, False
    unicode_names = False


def feature(oid, out_fields):
    lat = 30.60 if Svc.same_lat else 30.40 + (oid % 97) * 0.003
    lon = -81.75 + (oid % 89) * 0.004
    note = f"Hydrant {oid}" + (" — Ñandú & <Co> \"quoted\"" if Svc.unicode_names and oid % 3 == 0 else "")
    if Svc.ctrl and oid == 7:
        note = "Flushed 3/2024\x0bvalve stiff\x1a"
    attrs = {"OBJECTID": oid, "FACILITYID": f"H-{oid:05d}", "NOTES": note, "OWNER": "Nassau County",
             "FLOW": None if oid % 11 == 0 else 1000 + oid, "ACTIVE": oid % 2 == 0}
    f = {"attributes": {k: v for k, v in attrs.items() if k in out_fields}}
    if not (Svc.null_every and oid % Svc.null_every == 0):
        f["geometry"] = {"x": lon, "y": lat}
    return f


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        q = dict(urllib.parse.parse_qsl(self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()))
        path = self.path.rstrip("/")
        if path.endswith("/458/query"):
            if q.get("returnIdsOnly") == "true":
                body = {"objectIds": list(range(1, Svc.n + 1))}
                if not Svc.no_oid_field: body["objectIdFieldName"] = "OBJECTID"
                return self._send(body)
            ids = [int(x) for x in q["objectIds"].split(",")]
            if Svc.drop_per_batch: ids = ids[:-Svc.drop_per_batch]
            if Svc.drop_once:
                keep = [i for i in ids if i not in Svc.drop_once]; Svc.drop_once -= set(ids); ids = keep
            return self._send({"features": [feature(i, q["outFields"].split(",")) for i in ids]})
        if path.endswith("/458"):
            meta = {"name": "Water Hydrant", "geometryType": "esriGeometryPoint", "capabilities": "Query",
                    "maxRecordCount": Svc.max_record,
                    "fields": [{"name": n, "alias": n, "type": t} for n, t in
                               (("OBJECTID", "esriFieldTypeOID"), ("FACILITYID", "esriFieldTypeString"),
                                ("NOTES", "esriFieldTypeString"), ("OWNER", "esriFieldTypeString"),
                                ("FLOW", "esriFieldTypeInteger"), ("ACTIVE", "esriFieldTypeSmallInteger"))]}
            if not Svc.no_oid_field: meta["objectIdField"] = "OBJECTID"
            return self._send(meta)
        self.send_response(404); self.end_headers()


srv = ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
LAYER = f"http://127.0.0.1:{srv.server_address[1]}/arcgis/rest/services/Water_Hydrant/FeatureServer/458"
FIELDS = ["FACILITYID", "NOTES", "OWNER", "FLOW", "ACTIVE"]


def reset(**kw):
    for k, v in dict(n=3250, max_record=1000, drop_per_batch=0, drop_once=set(), null_every=0, same_lat=False,
                     ctrl=False, no_oid_field=False, unicode_names=False).items():
        setattr(Svc, k, kw.get(k, v))


def dl13(fields=FIELDS):
    ids, _ = p13.query_object_ids(LAYER); meta = p13.read_service(LAYER)
    b = max(1, min(int(meta.get("maxRecordCount") or 1000), p13.MAX_BATCH)); feats = []
    for s in range(0, len(ids), b):
        feats.extend(p13.query_feature_batch_resilient(LAYER, ids[s:s + b], fields, p13.DEFAULT_PRECISION))
    return ids, feats


def dl14(fields=FIELDS):
    ids, oid = p14.query_object_ids(LAYER); meta = p14.read_service(LAYER)
    oid = oid or meta.get("objectIdField")
    b = max(1, min(int(meta.get("maxRecordCount") or 1000), p14.MAX_BATCH))
    feats, missing = p14.download_all_features(LAYER, ids, oid, fields, b)
    return ids, feats, missing


def outputs(mod, feats, tag, fields=FIELDS, icon="Red H (hydrant)", hide=True, lod=12000, scale=0.5):
    d = W / tag; d.mkdir(exist_ok=True)
    kmz, geo = d / "Water_Hydrant.kmz", d / "Water_Hydrant.geojson"
    mod.write_kmz(kmz, feats, fields, {f: f"{f} alias" for f in fields}, LAYER, "Water Hydrant", lod, scale,
                  mod.built_in_icon_bytes(icon), hide)
    mod.write_geojson(geo, feats, fields, LAYER, "Water Hydrant")
    z = zipfile.ZipFile(kmz)
    return {n: z.read(n) for n in z.namelist()}, geo.read_bytes()


# 1. Regression: identical KMZ entries and GeoJSON bytes for normal services.
for label, kw, fields, icon, hide in [
        ("Nassau-like 3,250 / maxRecord 1000", {}, FIELDS, "Red H (hydrant)", True),
        ("Duval-like 30,688 / maxRecord 2000", {"n": 30688, "max_record": 2000}, FIELDS, "Red dot", True),
        ("unicode, quotes, & and < in values", {"unicode_names": True}, FIELDS, "Blue dot", False),
        ("single selected field", {}, ["FACILITYID"], "Yellow dot", True)]:
    reset(**kw)
    _, f13 = dl13(fields); _, f14, miss = dl14(fields)
    k13, g13 = outputs(p13, f13, "a13", fields, icon, hide); k14, g14 = outputs(p14, f14, "a14", fields, icon, hide)
    check(f"regression {label}: KMZ entries and GeoJSON identical to 1.3", k13 == k14 and g13 == g14 and not miss,
          f"{len(f14):,} features, missing={len(miss)}")
check("GeoJSON contains only the chosen fields (OBJECTID requested but not written)",
      "OBJECTID" not in json.loads(g14)["features"][0]["properties"])
check("no .partial files left after successful writes", not list(W.rglob("*.partial")))

# 2. Completeness.
reset(drop_once={5, 1234, 3001})
ids, feats, miss = dl14()
check("features dropped once are fetched on the second request", len(feats) == 3250 and miss == [], f"{len(feats)} written, missing {miss}")
reset(drop_per_batch=3)
ids, feats, miss = dl14()
# The mock also drops the last 3 IDs of every retry batch: 12 missing -> 9 recovered -> 3 reported.
check("features never returned are reported (after the retry recovers what it can)",
      miss == [3248, 3249, 3250] and len(feats) == 3247, f"{len(feats)} returned, missing {miss}")
reset(drop_per_batch=3, no_oid_field=True)
ids, feats, miss = dl14()
check("service without an object-ID field: shortfall still reported by count", len(miss) == len(ids) - len(feats) > 0, f"{len(miss)} missing")

# 3. Bad characters.
reset(ctrl=True)
_, f14, _ = dl14(); k14, _ = outputs(p14, f14, "ctrl14")
try:
    xml.dom.minidom.parseString(k14["doc.kml"]); ok = True
except Exception as e:
    ok = False
check("control characters in a notes field: KML is valid XML", ok)
check("the rest of that note survives", b"Flushed 3/2024valve stiff" in k14["doc.kml"])

# 4. Zero-area region.
for label, kw in [("one point", {"n": 1}), ("40 points on one latitude", {"n": 40, "same_lat": True})]:
    reset(**kw); _, f14, _ = dl14(); k14, _ = outputs(p14, f14, "zero")
    k = k14["doc.kml"].decode()
    n, s, e, w = (float(re.search(f"<{t}>([-0-9.]+)</{t}>", k).group(1)) for t in ("north", "south", "east", "west"))
    pts = [p14.extract_point(f) for f in f14]
    inside = all(w <= x <= e and s <= y <= n for x, y in pts)
    check(f"{label}: Region has area and contains every point", n > s and e > w and inside, f"N{n} S{s} E{e} W{w}")

# 5. Missing locations counted.
reset(null_every=50)
_, f14, miss = dl14()
nolo = len(f14) - sum(1 for f in f14 if p14.extract_point(f) is not None)
check("points without a location counted (reported in the completion message)", nolo == 65 and not miss, f"{nolo} skipped")

# 6. Failed write keeps the previous file.
reset(); _, f14, _ = dl14()
prev = W / "Hydrants.kmz"; prev.write_bytes(b"yesterday's layer")
real = p14.zipfile.ZipFile
class Boom(real):
    def writestr(self, *a, **k): raise OSError("disk full (simulated)")
p14.zipfile.ZipFile = Boom
try:
    p14.write_kmz(prev, f14, FIELDS, {}, LAYER, "x", 12000, 0.5, p14.built_in_icon_bytes("Red dot"), True); err = None
except OSError as e:
    err = str(e)
p14.zipfile.ZipFile = real
check("disk full while writing: previous KMZ kept, no partial", prev.read_bytes() == b"yesterday's layer" and not list(W.glob("*.partial")), err)

# 7. PNG check.
png = W / "icon.png"; png.write_bytes(p14.built_in_icon_bytes("Red dot"))
jpg = W / "renamed.png"; jpg.write_bytes(b"\xff\xd8\xff\xe0 not really a png")
check("custom icon PNG check: real PNG accepted, renamed JPEG rejected", p14.is_png(png) and not p14.is_png(jpg))

# 8. Built-in self-test (runs without a display).
r = subprocess.run([sys.executable, "-c", f"""
import sys, types
fake = types.ModuleType("tkinter"); fake.Tk = type("Tk", (), {{}})
for sub in ("filedialog", "messagebox", "ttk"):
    m = types.ModuleType("tkinter." + sub); setattr(fake, sub, m); sys.modules["tkinter." + sub] = m
sys.modules["tkinter"] = fake
sys.argv = ["PointLayer.py", "--self-test", {str(W / 'selftest')!r}]
exec(open({V14!r}).read())
"""], capture_output=True, text=True)
check("built-in --self-test passes", "SELF TEST PASS" in r.stdout, (r.stdout + r.stderr).strip().splitlines()[0] if (r.stdout + r.stderr).strip() else "")

fails = 0
for ok, name, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    fails += not ok
print(f"\n{len(results) - fails}/{len(results)} passed")
