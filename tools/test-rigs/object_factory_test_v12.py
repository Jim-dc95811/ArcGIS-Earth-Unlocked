"""Object Factory v1.2 vs v1.1: outputs without Hide above must be byte-identical; Hide above
adds one Folder + Region per object. No Tk here, so PNG normalization is a plain copy in both.

python3 object_factory_test_v12.py <v1.1 .py> <v1.2 .py> <icons dir> <samples dir>
"""
import os, re, shutil, sys, zipfile, pathlib, xml.dom.minidom
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from object_factory_load import load

V11, V12 = load(sys.argv[1]), load(sys.argv[2])
ICONS, SAMPLES = pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
W = pathlib.Path(os.environ.get("WORK", "/tmp/of12")); shutil.rmtree(W, ignore_errors=True); W.mkdir(parents=True)
results = []
def check(name, ok, detail=""): results.append((ok, name, detail))

def copy_norm(source, dest, master=None, max_dim=256):
    source, dest = pathlib.Path(source), pathlib.Path(dest)
    if source.suffix.lower() != ".png": raise ValueError(f"PNG required: {source.name}")
    if not source.is_file(): raise FileNotFoundError(source)
    dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, dest); return {"factor": 1}
for m in (V11, V12):
    m.icon_dir = lambda: ICONS; m.normalize_png = copy_norm
NAME_POPUP = re.compile(rb"\n    <description><!\[CDATA\[[^<\]]*\]\]></description>")
def zc(p, strip_name_popup=False):
    with zipfile.ZipFile(p) as z: d = {n: z.read(n) for n in z.namelist()}
    if strip_name_popup: d["doc.kml"] = NAME_POPUP.sub(b"", d["doc.kml"])
    return d
def name_popups(p):
    with zipfile.ZipFile(p) as z: return len(NAME_POPUP.findall(z.read("doc.kml")))
def kml(p):
    with zipfile.ZipFile(p) as z: return z.read("doc.kml").decode()

a_dir, b_dir = W / "v11", W / "v12"; a_dir.mkdir(); b_dir.mkdir()
# 1. regression without Hide above
stress = W / "stress.txt"
stress.write_text("\n".join(["type|name|lat|lon|alt_m|icon|description|url|link_text|scale|altitude_mode|tether|popup|label"] +
    [f"fuel|Fuel {i}|30.{100000+i}|-81.{200000+i}|150||Obj {i} <b>&</b>|https://x.example/?a=1&b={i}|GO|1.4|"
     f"{['relativeToGround','absolute','clampToGround'][i%3]}|{'yes' if i%2 else 'no'}|{'None' if i%5==0 else 'Info'}|{'yes' if i%7==0 else 'no'}"
     for i in range(100)]), encoding="utf-8")
lists = {"sample_objects.txt": SAMPLES / "sample_objects.txt", "simple_objects.txt": SAMPLES / "simple_objects.txt", "stress": stress}
for name, lp in lists.items():
    r11, r12 = V11.parse_batch_rows(lp), V12.parse_batch_rows(lp)
    check(f"batch rows same (plus hide_above_ft=None): {name}", [dict(r, hide_above_ft=None) for r in r11] == r12, f"{len(r12)} rows")
    a, _ = V11.create_batch_kmz(lp, a_dir / f"{name}.kmz"); b, _ = V12.create_batch_kmz(lp, b_dir / f"{name}.kmz")
    empty_info = sum(1 for r in r12 if r["popup"].lower() != "none" and not r["description"].strip() and not r["url"].strip())
    check(f"batch KMZ identical except a name popup on each empty-Info object: {name}",
          zc(a, True) == zc(b, True) and name_popups(b) - name_popups(a) == empty_info, f"{empty_info} name popups added")
for mode in ("relativeToGround", "absolute", "clampToGround"):
    for popup in ("Info", "None"):
        args = (ICONS / "firetruck.png", "Engine 7 & <crew>", 30.40098, -81.93471, 150.0, 1.5, mode,
                "Line one\nLine <two>", "https://example.com/?a=1&b=2", "OPEN", True, popup == "Info", popup)
        a = V11.create_single_object_kmz(a_dir / f"one_{mode}_{popup}.kmz", *args)
        b = V12.create_single_object_kmz(b_dir / f"one_{mode}_{popup}.kmz", *args)
        check(f"single object identical: {mode}/{popup}", zc(a) == zc(b))
    a = V11.create_single_object_kmz(a_dir / f"empty_{mode}.kmz", ICONS / "camera.png", "Cam <7>", 30.4, -81.9, 150.0, 1.5, mode, "", "", "OPEN", False, False, "Info")
    b = V12.create_single_object_kmz(b_dir / f"empty_{mode}.kmz", ICONS / "camera.png", "Cam <7>", 30.4, -81.9, 150.0, 1.5, mode, "", "", "OPEN", False, False, "Info")
    check(f"empty Info -> popup shows the name only: {mode}", "<description>" not in kml(a) and "<description><![CDATA[Cam &lt;7&gt;]]></description>" in kml(b) and zc(a) == zc(b, True))
a = V11.create_sky_compass_kmz(a_dir / "c.kmz", 30.3855, -81.9308, 100, 20000, 6); b = V12.create_sky_compass_kmz(b_dir / "c.kmz", 30.3855, -81.9308, 100, 20000, 6)
check("sky compass identical", zc(a) == zc(b))
a = V11.create_beacon_kml(a_dir / "b.kml", "B", 30.2, -81.2, 100, 6, "Red"); b = V12.create_beacon_kml(b_dir / "b.kml", "B", 30.2, -81.2, 100, 6, "Red")
check("beacon identical", a.read_bytes() == b.read_bytes())

# 2. Hide above
args = (ICONS / "camera.png", "Cam & <1>", 30.620303, -81.649687, 180.0, 1.5, "relativeToGround", "x", "", "OPEN", True, False, "Info")
p = V12.create_single_object_kmz(W / "hide.kmz", *args, hide_above_ft=3000)
k = kml(p); xml.dom.minidom.parseString(k)
lod = int(re.search(r"<minLodPixels>(\d+)</minLodPixels>", k).group(1))
check("hide 3000 ft -> one Folder/Region, minLodPixels 597", k.count("<Folder>") == 1 and k.count("<Region>") == 1 and lod == 597, str(lod))
check("tether inside the Folder", k.index("tether") < k.index("</Folder>"))
n = float(re.search(r"<north>([\d.]+)", k).group(1)); s = float(re.search(r"<south>([\d.]+)", k).group(1))
e = float(re.search(r"<east>(-?[\d.]+)", k).group(1)); w_ = float(re.search(r"<west>(-?[\d.]+)", k).group(1))
import math
ns_m = (n - s) * math.pi / 180 * V12.EARTH_R; ew_m = (e - w_) * math.pi / 180 * V12.EARTH_R * math.cos(math.radians(30.620303))
check("Region box is 300 m x 300 m", abs(ns_m - 300) < 0.5 and abs(ew_m - 300) < 0.5, f"{ns_m:.1f} x {ew_m:.1f}")
check("Hide above folder name escaped", "<name>Cam &amp; &lt;1&gt;</name>" in k)
check("Region is a cube: 30-330 m relativeToGround around a 180 m object",
      "<minAltitude>30.0</minAltitude><maxAltitude>330.0</maxAltitude><altitudeMode>relativeToGround</altitudeMode>" in k)
for mode, alt, want in (("clampToGround", 180.0, "<minAltitude>0.0</minAltitude><maxAltitude>300.0</maxAltitude><altitudeMode>relativeToGround"),
                        ("absolute", 500.0, "<minAltitude>350.0</minAltitude><maxAltitude>650.0</maxAltitude><altitudeMode>absolute"),
                        ("relativeToGround", 60.0, "<minAltitude>0.0</minAltitude><maxAltitude>300.0</maxAltitude><altitudeMode>relativeToGround")):
    q = V12.create_single_object_kmz(W / f"cube_{mode}_{alt:g}.kmz", ICONS / "camera.png", "C", 30.6, -81.6, alt, 1.5, mode, "", "", "", False, False, "Info", hide_above_ft=20000)
    check(f"cube box for {mode} {alt:g} m", want in kml(q))
# Predicted cutoff for the calibration test boxes reproduces Jim's observations
cal_side = math.sqrt((0.003 * math.pi / 180 * V12.EARTH_R) * (0.003 * math.pi / 180 * V12.EARTH_R * math.cos(math.radians(30.620303))))
C = V12.LOD_FT_PX * cal_side / V12.LOD_BOX_M
obs = {256: (5618, 10019), 128: (10019, 18610), 64: (18610, 37210), 32: (37210, 74433), 16: (74433, 148895)}
check("calibration constant inside every observed bracket",
      all(lo < C / L < hi for L, (lo, hi) in obs.items()), f"C={C:,.0f} ft*px for the test box")
# batch
lp = W / "hide.txt"
lp.write_text("type|name|lat|lon|alt_m|icon|description|url|link_text|scale|altitude_mode|tether|popup|label|hide_above_ft\n"
              "camera|A|30.62|-81.65|180||||||relativeToGround|yes|Info|no|2000\n"
              "camera|B|30.62|-81.64|180||||||relativeToGround|no|Info|no|\n"
              "camera|C|30.62|-81.63|180||||||relativeToGround|no|Info|no|5,000\n", encoding="utf-8")
p, cnt = V12.create_batch_kmz(lp, W / "hide_batch.kmz"); k = kml(p); xml.dom.minidom.parseString(k)
check("batch: 2 Regions (2000 ft, 5000 ft), 1 always visible", cnt == 3 and k.count("<Region>") == 2 and "<minLodPixels>895</minLodPixels>" in k and "<minLodPixels>358</minLodPixels>" in k)
for bad in ("high", "-10"):
    lp.write_text(f"type|name|lat|lon|hide_above_ft\ncamera|A|30.6|-81.6|1000\ncamera|B|30.6|-81.6|{bad}\n", encoding="utf-8")
    try: V12.parse_batch_rows(lp); check(f"bad hide_above_ft {bad!r} rejected", False)
    except ValueError as ex: check(f"bad hide_above_ft {bad!r} rejected with line", str(ex).startswith("Line 3"), str(ex))
for v, want in (("", None), ("0", None), (" 2500 ", 2500.0)):
    check(f"parse_hide_above({v!r})", V12.parse_hide_above(v) == want)

bad = [r for r in results if not r[0]]
for ok, name, d in results: print(("PASS " if ok else "FAIL ") + name + (f"  [{d}]" if d else ""))
print(f"\n{len(results)-len(bad)}/{len(results)} passed")
sys.exit(1 if bad else 0)
