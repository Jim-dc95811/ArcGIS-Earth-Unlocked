import json, sys, threading, types, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
fake = types.ModuleType("tkinter"); fake.Tk = type("Tk", (), {})
for sub in ("filedialog", "messagebox", "ttk"):
    m = types.ModuleType("tkinter." + sub); setattr(fake, sub, m); sys.modules["tkinter." + sub] = m
sys.modules["tkinter"] = fake
p = types.ModuleType("p15"); exec(compile(open(__import__("sys").argv[1]).read(), "Parcel100.py", "exec"), p.__dict__)
p.time = types.SimpleNamespace(sleep=lambda s: None)
calls = []
LAYERS = {0: ("Parcels", "esriGeometryPolygon"), 1: ("Hydrants", "esriGeometryPoint"),
          2: ("Parcels 2024 (slow server)", "esriGeometryPolygon"), 3: ("Zoning", "esriGeometryPolygon")}
FAIL = {2}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        path = self.path.rstrip("/"); calls.append(path)
        tail = path.rsplit("/", 1)[-1]
        if tail in ("FeatureServer", "MapServer"):
            body = {"layers": [{"id": i, "name": n} for i, (n, _) in LAYERS.items()]}
        elif tail.isdigit() and int(tail) in FAIL:
            self.send_response(504); self.end_headers(); return
        elif tail.isdigit():
            n, g = LAYERS[int(tail)]
            body = {"type": "Feature Layer", "name": n, "geometryType": g, "fields": [{"name": "OBJECTID"}]}
        else:
            self.send_response(404); self.end_headers(); return
        b = json.dumps(body).encode(); self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
srv = ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}/arcgis/rest/services/County/FeatureServer"
def show(label, url):
    calls.clear()
    try:
        prog=[]; c, un = p.discover_polygon_layers(url, progress_callback=prog.append); res = ([m["name"] for _, m in c], "unchecked:", un, f"{len(prog)} progress msgs")
    except Exception as e:
        res = f"ERROR: {e}"
    print(f"{label:46} -> {res}   ({len(calls)} requests)")
show("service root (layer 2 times out)", base)
show("explicit layer /0", base + "/0")
show("explicit point layer /1", base + "/1")
show("MapServer root", base.replace("FeatureServer", "MapServer"))
show("layer URL with trailing /query", base + "/0/query")
show("layer URL with /query?where=1=1", base + "/0/query?where=1%3D1&f=json")
FAIL.update({0, 3})
show("root, every polygon layer times out", base)
