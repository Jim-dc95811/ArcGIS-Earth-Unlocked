"""Mock ArcGIS Earth camera API on localhost; call it through EarthStick's own http code
with and without a system proxy configured."""
import importlib.util, json, os, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        b = json.dumps({"position": {"x": -81.9, "y": 30.4, "z": 900.0, "spatialReference": {"wkid": 4326}}, "heading": 10, "tilt": 0, "roll": 0}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
srv = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
spec = importlib.util.spec_from_file_location("es", "/home/claude/repos/EarthStick/EarthStick.py")
es = importlib.util.module_from_spec(spec); sys.modules["es"] = es; spec.loader.exec_module(es)
es.CAMERA_URL = f"http://localhost:{srv.server_address[1]}/arcgisearth/camera"
try:
    cam = es.get_camera(); print(f"[{sys.argv[1]}] camera read OK: z={cam['position']['z']}")
except es.EarthAPIError as e:
    print(f"[{sys.argv[1]}] camera read FAILED: {e}")
