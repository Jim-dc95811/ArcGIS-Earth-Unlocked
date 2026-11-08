"""PointLayer test server - a tiny stand-in ArcGIS FeatureServer on this PC (standard library only).

Used by the PointLayer 2.1 TEST kit (Jim double-clicks the server .bat, then pastes a URL into
PointLayer) and by tools/test-rigs/pointlayer_test_v21.py.

    python PointLayer_Test_Server.py [port]          (default 8765)

URLs (all on http://127.0.0.1:<port>):
  /arcgis/rest/services/Bryceville_Test/FeatureServer      service root: 2 point layers
      /0  "Test hydrants - odd records": 6 hydrants near Bryceville FL - one with location
          "NaN", one with a blank location, a date field (INSTALLED) and a code-list field (OWNER)
      /1  "Test hydrants - clean": 4 hydrants, text fields only (2.0 and 2.1 write the same KMZ)
  /login                                                   an HTML login page, not map data
The hydrants are made up (invented IDs and owners); the points sit along US-301 in Bryceville.
"""
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = "/arcgis/rest/services/Bryceville_Test/FeatureServer"

OWNER_DOMAIN = {"type": "codedValue", "name": "OwnerCodes",
                "codedValues": [{"name": "Nassau County", "code": 1}, {"name": "Town of Hilliard", "code": 2},
                                {"name": "Private", "code": 3}]}

LAYERS = {
    0: {"name": "Test hydrants - odd records",
        "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "OBJECTID"},
                   {"name": "HYDRANT_ID", "type": "esriFieldTypeString", "alias": "Hydrant ID"},
                   {"name": "OWNER", "type": "esriFieldTypeSmallInteger", "alias": "Owner", "domain": OWNER_DOMAIN},
                   {"name": "INSTALLED", "type": "esriFieldTypeDate", "alias": "Installed"},
                   {"name": "FLOW_GPM", "type": "esriFieldTypeString", "alias": "Flow (gpm)"}],
        "features": [
            (1, "TEST-H1", 1, 1625112000000, "1000", (-81.9392, 30.3961)),   # 2021-07-01 (local midnight)
            (2, "TEST-H2", 2, 1488326400000, "750", (-81.9371, 30.3990)),    # 2017-03-01 (UTC midnight)
            (3, "TEST-H3 (no location - NaN)", 1, 1625112000000, "500", ("NaN", "NaN")),
            (4, "TEST-H4 (blank location)", 3, None, "500", (None, None)),
            (5, "TEST-H5", 3, 1704114000000, "1250", (-81.9418, 30.3932)),   # 2024-01-01 13:00 UTC -> keeps the time
            (6, "TEST-H6", 2, None, "1000", (-81.9350, 30.4012)),
        ]},
    1: {"name": "Test hydrants - clean",
        "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "OBJECTID"},
                   {"name": "HYDRANT_ID", "type": "esriFieldTypeString", "alias": "Hydrant ID"},
                   {"name": "OWNER_NAME", "type": "esriFieldTypeString", "alias": "Owner"},
                   {"name": "FLOW_GPM", "type": "esriFieldTypeString", "alias": "Flow (gpm)"}],
        "features": [
            (1, "TEST-C1", "Nassau County", "1000", (-81.9392, 30.3961)),
            (2, "TEST-C2", "Town of Hilliard", "750", (-81.9371, 30.3990)),
            (3, "TEST-C3", "Private", "1250", (-81.9418, 30.3932)),
            (4, "TEST-C4", "Nassau County", "1000", (-81.9350, 30.4012)),
        ]},
}


def layer_meta(lid):
    L = LAYERS[lid]
    return {"id": lid, "name": L["name"], "type": "Feature Layer", "geometryType": "esriGeometryPoint",
            "objectIdField": "OBJECTID", "maxRecordCount": 1000, "capabilities": "Query",
            "fields": L["fields"]}


def feature(lid, row, out_fields):
    names = [f["name"] for f in LAYERS[lid]["fields"]]
    attrs = dict(zip(names, row[:-1]))
    x, y = row[-1]
    want = names if out_fields in ("", "*") else [n for n in out_fields.split(",") if n in names]
    return {"attributes": {n: attrs[n] for n in want}, "geometry": {"x": x, "y": y}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _params(self):
        parsed = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(parsed.query))
        if self.command == "POST":
            n = int(self.headers.get("Content-Length") or 0)
            q.update(urllib.parse.parse_qsl(self.rfile.read(n).decode("utf-8")))
        return parsed.path.rstrip("/"), q

    def _handle(self):
        path, q = self._params()
        if path == "/login" or path.startswith("/login/"):
            return self._send("<html><body><h1>Sign in</h1><form>User <input></form></body></html>",
                              "text/html; charset=utf-8")
        if path == ROOT:
            return self._send(json.dumps({"layers": [{"id": i, "name": L["name"]} for i, L in LAYERS.items()]}))
        if path.startswith(ROOT + "/"):
            rest = path[len(ROOT) + 1:].split("/")
            try:
                lid = int(rest[0])
            except ValueError:
                lid = -1
            if lid in LAYERS:
                rows = LAYERS[lid]["features"]
                if len(rest) == 1:
                    return self._send(json.dumps(layer_meta(lid)))
                if rest[1] == "query":
                    if q.get("returnCountOnly") == "true":
                        return self._send(json.dumps({"count": len(rows)}))
                    if q.get("returnIdsOnly") == "true":
                        return self._send(json.dumps({"objectIdFieldName": "OBJECTID", "objectIds": [r[0] for r in rows]}))
                    ids = {int(x) for x in (q.get("objectIds") or "").split(",") if x.strip()}
                    feats = [feature(lid, r, q.get("outFields", "*")) for r in rows if not ids or r[0] in ids]
                    return self._send(json.dumps({"objectIdFieldName": "OBJECTID", "features": feats}))
        self._send(json.dumps({"error": {"code": 400, "message": "Invalid URL", "details": []}}))

    do_GET = _handle
    do_POST = _handle


def start(port=8765):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return srv


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    srv = start(port)
    base = f"http://127.0.0.1:{port}"
    print("PointLayer TEST server is running on this PC - leave this window open while you test.\n")
    print("Paste one of these into PointLayer and click Read Service:\n")
    print(f"  Odd records (NaN + blank location, date, code list):\n    {base}{ROOT}/0?f=pjson\n")
    print(f"  Both layers (shows the layer chooser):\n    {base}{ROOT}\n")
    print(f"  Clean layer:\n    {base}{ROOT}/1/query\n")
    print(f"  Not map data (login page):\n    {base}/login/arcgis/rest/services/X/FeatureServer/0\n")
    print("Close this window when you are done.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
