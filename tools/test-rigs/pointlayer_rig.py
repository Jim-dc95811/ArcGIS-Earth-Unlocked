"""PointLayer test rig: a mock ArcGIS FeatureServer + PointLayer's own download/write functions.

python3 pl_rig.py <path to PointLayer.py> <scenario>   -> prints one JSON line
"""
import json, os, sys, threading, types, zipfile, urllib.parse, pathlib, xml.dom.minidom
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PATH, SCENARIO = sys.argv[1], sys.argv[2]
OUT = pathlib.Path(__file__).parent / "out" / f"{os.path.basename(os.path.dirname(PATH)) or 'x'}_{SCENARIO}"
OUT.mkdir(parents=True, exist_ok=True)

# ---- fake tkinter so the module loads without a display ----
fake = types.ModuleType("tkinter"); fake.Tk = type("Tk", (), {})
for sub in ("filedialog", "messagebox", "ttk"):
    m = types.ModuleType("tkinter." + sub); setattr(fake, sub, m); sys.modules["tkinter." + sub] = m
sys.modules["tkinter"] = fake
pl = types.ModuleType("pointlayer"); pl.__file__ = PATH
exec(compile(open(PATH).read(), PATH, "exec"), pl.__dict__)
pl.time = types.SimpleNamespace(sleep=lambda s: None)   # no real waiting between retries


# ---- mock hydrant service ----
class Svc:
    n = 3250
    max_record = 1000
    drop_per_batch = 0        # server silently returns this many fewer features per batch
    null_geom_every = 0       # every Nth feature has no geometry
    json_error_once = None    # body-level ArcGIS error returned once on first feature query
    same_lat = False
    control_chars = False
    calls = 0


def feature(oid):
    lat = 30.60 if Svc.same_lat else 30.40 + (oid % 97) * 0.003
    lon = -81.75 + (oid % 89) * 0.004
    note = f"Hydrant {oid}"
    if Svc.control_chars and oid == 7:
        note = "Flushed 3/2024\x0bvalve stiff\x1a"          # vertical tab + SUB, common in old agency data
    geom = None if (Svc.null_geom_every and oid % Svc.null_geom_every == 0) else {"x": lon, "y": lat}
    f = {"attributes": {"OBJECTID": oid, "FACILITYID": f"H-{oid:05d}", "NOTES": note, "OWNER": "Nassau County"}}
    if geom: f["geometry"] = geom
    return f


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        q = dict(urllib.parse.parse_qsl(self.rfile.read(n).decode()))
        path = self.path.rstrip("/")
        Svc.calls += 1
        if path.endswith("/FeatureServer/458"):
            return self._send({"name": "Water Hydrant", "geometryType": "esriGeometryPoint", "capabilities": "Query",
                               "maxRecordCount": Svc.max_record, "objectIdField": "OBJECTID",
                               "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "OBJECTID"},
                                          {"name": "FACILITYID", "type": "esriFieldTypeString", "alias": "Facility ID"},
                                          {"name": "NOTES", "type": "esriFieldTypeString", "alias": "Notes"},
                                          {"name": "OWNER", "type": "esriFieldTypeString", "alias": "Owner"}]})
        if path.endswith("/458/query"):
            if q.get("returnCountOnly") == "true":
                return self._send({"count": Svc.n})
            if q.get("returnIdsOnly") == "true":
                return self._send({"objectIdFieldName": "OBJECTID", "objectIds": list(range(1, Svc.n + 1))})
            if Svc.json_error_once:
                err, Svc.json_error_once = Svc.json_error_once, None
                return self._send({"error": err})
            ids = [int(x) for x in q["objectIds"].split(",")]
            if Svc.drop_per_batch:
                ids = ids[:-Svc.drop_per_batch]
            return self._send({"features": [feature(i) for i in ids]})
        self.send_response(404); self.end_headers()


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
LAYER = f"http://127.0.0.1:{srv.server_address[1]}/arcgis/rest/services/Water_Hydrant/FeatureServer/458"


def download(fields=("FACILITYID", "NOTES", "OWNER")):
    """Same sequence as PointLayerApp._build_worker, minus the window."""
    ids, _ = pl.query_object_ids(LAYER)
    meta = pl.read_service(LAYER)
    batch = max(1, min(int(meta.get("maxRecordCount") or 1000), pl.MAX_BATCH))
    feats = []
    for s in range(0, len(ids), batch):
        feats.extend(pl.query_feature_batch_resilient(LAYER, ids[s:s + batch], list(fields), pl.DEFAULT_PRECISION))
    return ids, feats


def write(feats, fields=("FACILITYID", "NOTES", "OWNER"), name="Hydrants"):
    kmz = OUT / f"{name}.kmz"
    pl.write_kmz(kmz, feats, list(fields), {f: f for f in fields}, LAYER, "Water Hydrant", 12000, 0.5,
                 pl.built_in_icon_bytes("Red H (hydrant)"), True)
    return kmz


def kml_ok(kmz):
    try:
        xml.dom.minidom.parseString(zipfile.ZipFile(kmz).read("doc.kml")); return True, ""
    except Exception as e:
        return False, str(e)[:90]


r = {"scenario": SCENARIO}
try:
    if SCENARIO == "normal":
        ids, feats = download(); kmz = write(feats)
        k = zipfile.ZipFile(kmz).read("doc.kml").decode()
        r.update(ids=len(ids), features=len(feats), placemarks=k.count("<Placemark>"), valid_xml=kml_ok(kmz)[0])
    elif SCENARIO == "server_drops":
        Svc.drop_per_batch = 3
        ids, feats = download(); kmz = write(feats)
        r.update(ids=len(ids), features=len(feats), placemarks=zipfile.ZipFile(kmz).read("doc.kml").decode().count("<Placemark>"),
                 warning_given="no (tool reports only what it wrote)")
    elif SCENARIO == "null_geometry":
        Svc.null_geom_every = 50
        ids, feats = download(); kmz = write(feats)
        valid = sum(1 for f in feats if pl.extract_point(f) is not None)
        r.update(ids=len(ids), features=len(feats), with_location=valid, skipped_silently=len(feats) - valid)
    elif SCENARIO == "control_chars":
        Svc.control_chars = True
        ids, feats = download(); kmz = write(feats)
        ok, err = kml_ok(kmz)
        r.update(features=len(feats), kml_is_valid_xml=ok, parser_error=err)
    elif SCENARIO == "one_point":
        Svc.n = 1
        ids, feats = download(); kmz = write(feats)
        k = zipfile.ZipFile(kmz).read("doc.kml").decode()
        import re
        box = {t: float(re.search(f"<{t}>([-0-9.]+)</{t}>", k).group(1)) for t in ("north", "south", "east", "west")}
        r.update(features=len(feats), region_box=box, region_has_area=box["north"] > box["south"] and box["east"] > box["west"])
    elif SCENARIO == "same_latitude":
        Svc.n = 40; Svc.same_lat = True
        ids, feats = download(); kmz = write(feats)
        k = zipfile.ZipFile(kmz).read("doc.kml").decode()
        import re
        n, s = (float(re.search(f"<{t}>([-0-9.]+)</{t}>", k).group(1)) for t in ("north", "south"))
        r.update(features=len(feats), north=n, south=s, region_has_area=n > s)
    elif SCENARIO == "json_504":
        Svc.json_error_once = {"code": 504, "message": "Unable to complete operation.", "details": []}
        ids, feats = download()
        r.update(ids=len(ids), features=len(feats), service_calls=Svc.calls)
    elif SCENARIO == "permanent_error":
        Svc.json_error_once = {"code": 400, "message": "Invalid or missing input parameters.", "details": []}
        Svc.max_record = 5000; Svc.n = 10
        before = Svc.calls
        try:
            download(); r["result"] = "succeeded"
        except Exception as e:
            r["result"] = f"error: {e}"
        r["service_calls"] = Svc.calls - before
    elif SCENARIO == "overwrite":
        ids, feats = download()
        (OUT / "Hydrants.kmz").write_bytes(b"yesterday's hand-tuned layer")
        write(feats)
        r["previous_file_replaced_without_asking"] = (OUT / "Hydrants.kmz").read_bytes() != b"yesterday's hand-tuned layer"
except Exception as e:
    r["error"] = f"{type(e).__name__}: {e}"
sys.stdout.write(json.dumps(r) + "\n")
