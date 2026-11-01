"""Object Factory v1.1 vs v1.0: output regression and hardening checks (no Tk available here;
PNG normalization is replaced by a plain copy in BOTH versions so everything else can be compared)."""
import os, shutil, sys, zipfile, pathlib
sys.path.insert(0, os.path.dirname(__file__))
from load_of import load

HERE = pathlib.Path(__file__).parent
V10 = load(str(HERE / "Object_Factory_v1.0.py"))
V11 = load("/home/claude/dev/object_factory_v1.1/Object_Factory_v1.1/Object_Factory_v1.1.py")
ICONS = HERE / "icons"
W = HERE / "t11"; shutil.rmtree(W, ignore_errors=True); W.mkdir()
results = []


def check(name, ok, detail=""):
    results.append((ok, name, detail))


def copy_norm(source, dest, master=None, max_dim=256):
    source, dest = pathlib.Path(source), pathlib.Path(dest)
    if source.suffix.lower() != ".png": raise ValueError(f"PNG required: {source.name}")
    if not source.is_file(): raise FileNotFoundError(source)
    dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, dest)
    return {"factor": 1}


for m in (V10, V11):
    m.icon_dir = lambda: ICONS
    m.normalize_png = copy_norm


def zip_contents(p):
    with zipfile.ZipFile(p) as z:
        return {n: z.read(n) for n in z.namelist()}


# 1. Output regression: identical files for the same inputs.
d10, d11 = W / "v10", W / "v11"; d10.mkdir(); d11.mkdir()
samples = HERE / "zipped/Object_Factory_v0.2.2_TEST"
lists = {"sample_objects.txt": samples / "sample_objects.txt", "simple_objects.txt": samples / "simple_objects.txt"}
stress = W / "stress.txt"
stress.write_text("\n".join(["type|name|lat|lon|alt_m|icon|description|url|link_text|scale|altitude_mode|tether|popup|label"] +
                            [f"fuel|Fuel {i}|30.{100000+i}|-81.{200000+i}|150||Object {i} <b>&</b>|https://x.example/?a=1&b={i}|GO|1.4|"
                             f"{['relativeToGround','absolute','clampToGround'][i%3]}|{'yes' if i%2 else 'no'}|{'None' if i%5==0 else 'Info'}|{'yes' if i%7==0 else 'no'}"
                             for i in range(100)]), encoding="utf-8")
lists["stress_100.txt"] = stress
for name, lp in lists.items():
    rows10, rows11 = V10.parse_batch_rows(lp), V11.parse_batch_rows(lp)
    check(f"batch rows identical: {name}", rows10 == rows11, f"{len(rows11)} rows")
    a, _ = V10.create_batch_kmz(lp, d10 / f"{name}.kmz"); b, _ = V11.create_batch_kmz(lp, d11 / f"{name}.kmz")
    check(f"batch KMZ identical: {name}", zip_contents(a) == zip_contents(b))
for mode in ("relativeToGround", "absolute", "clampToGround"):
    for popup in ("Info", "None"):
        args = (ICONS / "firetruck.png", "Engine 7 & <crew>", 30.40098, -81.93471, 150.0, 1.5, mode,
                "Line one\nLine <two>", "https://example.com/?a=1&b=2", "OPEN", True, popup == "Info", popup)
        a = V10.create_single_object_kmz(d10 / f"one_{mode}_{popup}.kmz", *args)
        b = V11.create_single_object_kmz(d11 / f"one_{mode}_{popup}.kmz", *args)
        check(f"single object identical: {mode}/{popup}", zip_contents(a) == zip_contents(b))
a = V10.create_sky_compass_kmz(d10 / "compass.kmz", 30.3855, -81.9308, 100, 20000, 6)
b = V11.create_sky_compass_kmz(d11 / "compass.kmz", 30.3855, -81.9308, 100, 20000, 6)
check("Sky Compass identical", zip_contents(a) == zip_contents(b))
for color in V10.COLORS:
    a = V10.create_beacon_kml(d10 / f"b_{color}.kml", "Beacon & Co", 30.2, -81.2, 100, 6, color)
    b = V11.create_beacon_kml(d11 / f"b_{color}.kml", "Beacon & Co", 30.2, -81.2, 100, 6, color)
    if a.read_bytes() != b.read_bytes(): check(f"Beacon identical: {color}", False); break
else:
    check("Beacon identical: all 7 colors", True)
check("no .partial files left after successful builds", not list(d11.glob("*.partial")))

# 2. Failed builds keep the previous file.
os.rename(ICONS / "W.png", ICONS / "W.hold")
out = W / "Sky_Compass.kmz"; out.write_bytes(b"previous compass")
try:
    V11.create_sky_compass_kmz(out, 30.38, -81.93, 100, 20000, 6); err = None
except FileNotFoundError as e:
    err = str(e)
os.rename(ICONS / "W.hold", ICONS / "W.png")
check("Sky Compass, W icon missing: clear error, previous file kept, no partial",
      bool(err) and "W.png" in err and out.read_bytes() == b"previous compass" and not list(W.glob("*.partial")), err)
out = W / "Object_Set.kmz"; out.write_bytes(b"previous set")
bad = W / "bad_icon.txt"; bad.write_text("type|name|lat|lon|icon\nfuel|A|30.4|-81.9|\nfuel|B|30.5|-81.8|missing.png\n")
try:
    V11.create_batch_kmz(bad, out); err = None
except FileNotFoundError as e:
    err = str(e)
check("batch with a missing icon: previous file kept", out.read_bytes() == b"previous set" and bool(err), err)
real_zip = V11.zipfile.ZipFile
class Boom(real_zip):
    def write(self, *a, **k): raise OSError("disk full (simulated)")
V11.zipfile.ZipFile = Boom
out = W / "Engine.kmz"; out.write_bytes(b"previous object")
try:
    V11.create_single_object_kmz(out, ICONS / "firetruck.png", "E", 30.4, -81.9, 150, 1.5, "relativeToGround", "", "", "", False, False, "Info"); err = None
except OSError as e:
    err = str(e)
V11.zipfile.ZipFile = real_zip
check("disk full while writing a KMZ: previous file kept, no partial",
      out.read_bytes() == b"previous object" and not list(W.glob("*.partial")), err)

# 3. Batch reading.
p = W / "list.txt"
p.write_text("staging,30.10,-81.60,150,Palatka Colony Staging\nfuel,30.41,-81.92\nwater,30.40,-81.91\n")
try:
    n = len(V11.parse_batch_rows(p)); ok = n == 3; det = f"{n} objects"
except Exception as e:
    ok, det = False, str(e)
check("shorthand list starting 'Palatka Colony Staging' reads as shorthand", ok, det)
cases = {
    "# comment\nfuel,30.41,-81.92\n\nwater,30.4O,-81.91\n": "Line 4",
    "type|name|lat|lon\nfuel|A|30.41|-81.92\nwater|B|30.40|-8l.91\n": "Line 3 (B)",
    "fuel,30.41,-81.92\nwater,95.0,-81.91,100,Tank\n": "Line 2 (Tank)",
    "type|name|lat|lon|altitude_mode\nfuel|A|30.41|-81.92|onGround\n": "Line 2 (A)",
    "fuel,30.41\n": "Line 1",
}
for body, expect in cases.items():
    p.write_text(body)
    try:
        V11.parse_batch_rows(p); msg = "accepted"
    except ValueError as e:
        msg = str(e)
    check(f"error names the line: expects {expect!r}", msg.startswith(expect), msg)

# 4. Removed code is really gone.
src = open("/home/claude/dev/object_factory_v1.1/Object_Factory_v1.1/Object_Factory_v1.1.py", encoding="utf-8").read()
check("ArcGIS Earth camera-coordinate code removed", "get_arcgis_camera_coordinates" not in src and "urllib" not in src and "localhost" not in src)

fails = 0
for ok, name, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    fails += not ok
print(f"\n{len(results) - fails}/{len(results)} passed")
