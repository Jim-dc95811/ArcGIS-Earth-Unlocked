"""Parcel100 test server - a tiny stand-in ArcGIS parcel FeatureServer on this PC (standard library only).

Used by the Parcel100 2.1 TEST kit and by tools/test-rigs/parcel100_test_v21.py.

    python Parcel100_Test_Server.py [port]          (default 8766)

URLs (all on http://127.0.0.1:<port>):
  /arcgis/rest/services/Bryceville_Parcels_Test/FeatureServer      service root: 3 polygon layers
      /0  "Test parcels - odd records": 6 made-up lots in Bryceville FL (Master 4 box 82w,81w,30n,31n,
          cells 040 and 039), one sent with an empty shape {}
      /1  "Test parcels - clean": the same lots without the empty one (2.0 and 2.1 write the same files)
      /2  "Other county parcels": the same lots with different field names (for the Replace / Keep question)
  /login                                                           an HTML login page, not map data
Owners and addresses are invented. Envelope queries (inSR 4326) are honoured, so the other 98 cells are empty.
"""
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = "/arcgis/rest/services/Bryceville_Parcels_Test/FeatureServer"


def lot(x, y, w=0.0012, h=0.0009):
    return [[x, y], [x, y + h], [x + w, y + h], [x + w, y], [x, y]]


LOTS = [  # (oid, owner, address, parcel id, acres, ring or None for the empty shape)
    (1, "TEST OWNER ONE", "100 TEST LOT RD", "TEST-0001", 0.9, lot(-81.9400, 30.3955)),
    (2, "TEST OWNER TWO", "102 TEST LOT RD", "TEST-0002", 0.9, lot(-81.9386, 30.3955)),
    (3, "TEST OWNER THREE", "104 TEST LOT RD", "TEST-0003", 1.2, lot(-81.9372, 30.3966)),
    (4, "TEST OWNER FOUR (empty shape)", "106 TEST LOT RD", "TEST-0004", 0.5, None),
    (5, "TEST OWNER FIVE", "200 TEST FARM RD", "TEST-0005", 5.0, lot(-81.8950, 30.3920, 0.004, 0.003)),
    (6, "TEST OWNER SIX", "202 TEST FARM RD", "TEST-0006", 4.0, lot(-81.8890, 30.3930, 0.003, 0.003)),
]
FL_FIELDS = [("OBJECTID", "esriFieldTypeOID"), ("OWN_NAME", "esriFieldTypeString"), ("PHY_ADDR1", "esriFieldTypeString"),
             ("PARCEL_ID", "esriFieldTypeString"), ("ACRES", "esriFieldTypeDouble")]
OTHER_FIELDS = [("FID", "esriFieldTypeOID"), ("OWNER", "esriFieldTypeString"), ("SITUS", "esriFieldTypeString"),
                ("APN", "esriFieldTypeString"), ("AREA_AC", "esriFieldTypeDouble")]
LAYERS = {
    0: ("Test parcels - odd records", FL_FIELDS, [r for r in LOTS]),
    1: ("Test parcels - clean", FL_FIELDS, [r for r in LOTS if r[5] is not None]),
    2: ("Other county parcels", OTHER_FIELDS, [r for r in LOTS if r[5] is not None]),
}


def meta(lid):
    name, fields, _ = LAYERS[lid]
    return {"id": lid, "name": name, "type": "Feature Layer", "geometryType": "esriGeometryPolygon",
            "objectIdField": fields[0][0], "maxRecordCount": 2000, "capabilities": "Query",
            "fields": [{"name": n, "type": t, "alias": n} for n, t in fields]}


def bbox(ring):
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def hits(rows, geometry):
    if not geometry:
        return rows
    w, s, e, n = (float(v) for v in geometry.split(","))
    out = []
    for r in rows:
        if r[5] is None:      # the empty shape sits with lot 1 (cell 040)
            ring = LOTS[0][5]
        else:
            ring = r[5]
        x0, y0, x1, y1 = bbox(ring)
        if x0 <= e and x1 >= w and y0 <= n and y1 >= s:
            out.append(r)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle(self):
        parsed = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(parsed.query))
        if self.command == "POST":
            q.update(urllib.parse.parse_qsl(self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()))
        path = parsed.path.rstrip("/")
        if path.startswith("/login"):
            return self._send("<html><body><h1>Sign in</h1><form>User <input></form></body></html>", "text/html; charset=utf-8")
        if path == ROOT:
            return self._send(json.dumps({"layers": [{"id": i, "name": L[0]} for i, L in LAYERS.items()]}))
        if path.startswith(ROOT + "/"):
            rest = path[len(ROOT) + 1:].split("/")
            lid = int(rest[0]) if rest[0].isdigit() else -1
            if lid in LAYERS:
                name, fields, rows = LAYERS[lid]
                oid = fields[0][0]
                if len(rest) == 1:
                    return self._send(json.dumps(meta(lid)))
                if rest[1] == "query":
                    if q.get("returnIdsOnly") == "true":
                        return self._send(json.dumps({"objectIdFieldName": oid,
                                                      "objectIds": [r[0] for r in hits(rows, q.get("geometry"))]}))
                    ids = {int(x) for x in (q.get("objectIds") or "").split(",") if x.strip()}
                    want = [f for f in (q.get("outFields") or "*").split(",") if f]
                    feats = []
                    for r in rows:
                        if ids and r[0] not in ids:
                            continue
                        attrs = dict(zip([f for f, _ in fields], r[:5]))
                        attrs = {k: v for k, v in attrs.items() if want == ["*"] or k in want}
                        feats.append({"attributes": attrs, "geometry": {} if r[5] is None else {"rings": [r[5]]}})
                    return self._send(json.dumps({"objectIdFieldName": oid, "features": feats}))
        self._send(json.dumps({"error": {"code": 400, "message": "Invalid URL", "details": []}}))

    do_GET = _handle
    do_POST = _handle


def start(port=8766):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    srv = start(port)
    base = f"http://127.0.0.1:{port}"
    print("Parcel100 TEST server is running on this PC - leave this window open while you test.\n")
    print("Master 4 box to use: 82w,81w,30n,31n  (the test lots are in cells 039 and 040)\n")
    print(f"  A. Odd records (one parcel with an empty shape):\n     {base}{ROOT}/0?f=pjson\n")
    print(f"  B. Clean parcels:\n     {base}{ROOT}/1\n")
    print(f"  C. Other county (different fields):\n     {base}{ROOT}/2\n")
    print(f"  D. Not map data (login page):\n     {base}/login/arcgis/rest/services/X/FeatureServer/0\n")
    print("Close this window when you are done.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
