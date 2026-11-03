"""EarthStick 1.3 wormhole flight test: copies EarthStick.py into a temp folder with a Gates
folder (gate A 1 km ahead of the rig's start, facing the rig's heading; partner B over NYC),
runs the standard replay script through earthstick_rig.py, and checks the camera stream.

python3 earthstick_rig_wormhole.py <EarthStick.py>
"""
import json, math, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from make_gate_kmz import gate, write_kmz, dest

src = sys.argv[1]
tmp = tempfile.mkdtemp()
shutil.copy(src, os.path.join(tmp, "EarthStick.py"))
os.mkdir(os.path.join(tmp, "Gates"))
start = (30.4191, -81.9265); alt = 1500.0
alat, alon = dest(*start, 30.0, 1000.0)
write_kmz(os.path.join(tmp, "Gates", "test.kmz"), "test", [
    gate("A", alat, alon, alt, facing=30.0, to="B"),
    gate("B", 40.6892, -74.0445, 457.0, facing=213.2, to="A")])
out = subprocess.run([sys.executable, os.path.join(HERE, "earthstick_rig.py"), os.path.join(tmp, "EarthStick.py"), "replay"],
                     capture_output=True, text=True).stdout
res = json.loads(out)
puts = json.load(open(os.path.join(HERE, f"es_puts_{res['version']}.json")))
os.remove(os.path.join(HERE, f"es_puts_{res['version']}.json"))
jumps = [i for i in range(1, len(puts)) if abs(puts[i]["position"]["y"] - puts[i - 1]["position"]["y"]) > 1.0]
ok = True
def check(name, cond, detail=""):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
check("script ran", res.get("stopped") == "script done", res)
check("exactly one jump", len(jumps) == 1, jumps)
if jumps:
    j = puts[jumps[0]]
    check("arrived near the Statue of Liberty at 457 m", abs(j["position"]["y"] - 40.69) < 0.01 and abs(j["position"]["x"] + 74.04) < 0.01 and j["position"]["z"] == 457.0, j["position"])
    check("arrival heading faces away from Jacksonville (~33)", abs(j["heading"] - 33.2) < 0.01, j["heading"])
    check("tilt kept", j["tilt"] == puts[jumps[0] - 1]["tilt"])
    check("stays in NYC afterwards (no bounce back)", all(abs(p["position"]["y"] - 40.69) < 0.2 for p in puts[jumps[0]:]))
print("ALL PASS" if ok else "FAILURES")
shutil.rmtree(tmp)
