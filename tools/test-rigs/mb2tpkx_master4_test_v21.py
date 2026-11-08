"""mb2tpkx 2.1 + Master 4 2.1 vs 2.0: same TPKX bundles / grid files; the 2.1 disk check, progress,
Replace question, damaged-tile message and Master 4 typing example.

python3 mb2tpkx_master4_test_v21.py <2.0 System Files dir> <2.1 dir holding mb2tpkx.py + Master4_Grid_Maker.py>
"""
import importlib.util, io, os, shutil, sqlite3, subprocess, sys, types, zipfile, json, pathlib
from PIL import Image

OLD, NEW = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
W = pathlib.Path(os.environ.get("WORK", "/tmp/mb21")).resolve(); shutil.rmtree(W, ignore_errors=True); W.mkdir(parents=True)
results = []
def check(name, ok, detail=""): results.append((bool(ok), name, detail))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def run(script, *args, stdin=""):
    r = subprocess.run([sys.executable, str(script), *map(str, args)], input=stdin, capture_output=True, text=True, cwd=W)
    return r.returncode, r.stdout + r.stderr


# --- a realistic MBTiles: z8-z15 over ~40 x 30 km near Jacksonville, JPEG inside + PNG edges, several bundles at z15
def blob(i, fmt):
    b = io.BytesIO(); Image.new("RGB", (256, 256), (i * 37 % 255, i * 91 % 255, i * 53 % 255)).save(b, fmt); return b.getvalue()
JP = [blob(i, "JPEG") for i in range(40)]; PN = [blob(i, "PNG") for i in range(40, 50)]
src = W / "jax_test.mbtiles"
con = sqlite3.connect(src)
con.execute("CREATE TABLE metadata (name text, value text)"); con.execute("INSERT INTO metadata VALUES ('name','JAX test')")
con.execute("CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)")
con.execute("CREATE UNIQUE INDEX tile_index on tiles (zoom_level, tile_column, tile_row)")
import math
def tile(lon, lat, z):
    n = 1 << z; x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n); return x, y
k = 0
for z in range(8, 16):
    x0, y0 = tile(-81.9, 30.45, z); x1, y1 = tile(-81.5, 30.18, z)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            edge = x in (x0, x1) or y in (y0, y1)
            con.execute("INSERT INTO tiles VALUES (?,?,?,?)", (z, x, (1 << z) - 1 - y, PN[k % 10] if edge else JP[k % 40])); k += 1
con.commit(); n_tiles = con.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]; con.close()


def members(p):
    with zipfile.ZipFile(p) as z:
        return {i.filename: z.read(i) for i in z.infolist()}


(W / "o").mkdir(); (W / "n").mkdir()
rc_o, out_o = run(OLD / "mb2tpkx.py", src, W / "o" / "jax_test.tpkx")
rc_n, out_n = run(NEW / "mb2tpkx.py", src, W / "n" / "jax_test.tpkx")
mo, mn = members(W / "o" / "jax_test.tpkx"), members(W / "n" / "jax_test.tpkx")
bundles = [k for k in mo if k.endswith(".bundle")]
check(f"both convert ({n_tiles:,} tiles, {len(bundles)} bundles)", rc_o == 0 and rc_n == 0, out_n[-300:])
check("same files in the same order", list(mo) == list(mn))
check(f"all {len(bundles)} bundles byte-identical 2.0 / 2.1", all(mo[k] == mn[k] for k in bundles))
check("root.json + thumbnail identical", mo["root.json"] == mn["root.json"] and mo["thumbnail.png"] == mn["thumbnail.png"])
io_, in_ = json.loads(mo["iteminfo.json"]), json.loads(mn["iteminfo.json"]); io_.pop("guid"); in_.pop("guid")
check("iteminfo identical apart from the random package ID", io_ == in_)
prog = [l for l in out_n.splitlines() if l.startswith("bundle ")]
check(f"progress: 'bundle N of {len(bundles)} (P%)' on every bundle, ends at 100%",
      len(prog) == len(bundles) and prog[0].startswith(f"bundle 1 of {len(bundles)} (") and f"bundle {len(bundles)} of {len(bundles)} (100%)" in prog[-1], prog[:2] + prog[-1:])

# Replace question
target = W / "n" / "jax_test.tpkx"; before = target.read_bytes()
rc, out = run(NEW / "mb2tpkx.py", src, target, stdin="n\n")
check("existing TPKX + No -> kept, plain line", rc != 0 and "Replace it? [y/N]" in out and "existing TPKX was kept" in out and target.read_bytes() == before, out)
rc, out = run(NEW / "mb2tpkx.py", src, target, stdin="")
check("existing TPKX + no answer (Enter / closed input) -> kept", rc != 0 and target.read_bytes() == before, out)
rc, out = run(NEW / "mb2tpkx.py", src, target, stdin="y\n")
check("existing TPKX + Yes -> replaced with a good TPKX, no .partial left",
      rc == 0 and "SUCCESS" in out and members(target).keys() == mn.keys() and not target.with_name(target.name + ".partial").exists(), out[-200:])
rc, out = run(OLD / "mb2tpkx.py", src, target)
check("2.0: existing TPKX -> stops, delete it yourself", rc != 0 and "delete or rename it" in out, out)

# a replace target that cannot be opened (stand-in for a TPKX held by ArcGIS Earth) -> stops before building
M = load(NEW / "mb2tpkx.py", "mb21")
locked = W / "locked.tpkx"; locked.mkdir()
try:
    M.convert(src, locked, replace=True); e = None
except PermissionError as x:
    e = str(x)
check("TPKX that cannot be replaced -> plain message before any work", e and "may be open in ArcGIS Earth" in e and not (W / "locked.tpkx.partial").exists(), e)

# disk space
real = shutil.disk_usage
M.shutil.disk_usage = lambda p: types.SimpleNamespace(total=1, used=1, free=10_000_000)
try:
    M.convert(src, W / "full.tpkx"); e = None
except ValueError as x:
    e = str(x)
M.shutil.disk_usage = real
check("too little disk -> stops at once, plain message, nothing written", e and "Not enough disk space" in e and not (W / "full.tpkx").exists() and not (W / "full.tpkx.partial").exists(), e)

# empty tile record
bad = W / "damaged.mbtiles"; shutil.copy(src, bad)
c = sqlite3.connect(bad); c.execute("UPDATE tiles SET tile_data=NULL WHERE rowid=(SELECT MAX(rowid) FROM tiles)"); c.commit(); c.close()
rc, out = run(OLD / "mb2tpkx.py", bad, W / "o" / "damaged.tpkx")
check("2.0 damaged MBTiles -> programmer error", "AttributeError" in out or "TypeError" in out, out[-200:])
rc, out = run(NEW / "mb2tpkx.py", bad, W / "n" / "damaged.tpkx")
check("2.1 damaged MBTiles -> 'is empty - the MBTiles is damaged', nothing left behind",
      rc != 0 and "the MBTiles is damaged" in out and "Traceback" not in out and not list((W / "n").glob("damaged.tpkx*")), out[-200:])

# --- Master 4
O4, N4 = load(OLD / "Master4_Grid_Maker.py", "m4o"), load(NEW / "Master4_Grid_Maker.py", "m4n")
for box in ("82w, 81w, 30n, 31n", "10e, 11e, 30n, 31n", "82w, 81w, 31s, 30s", "1w, 0e, 0n, 1n"):
    (W / "4o").mkdir(exist_ok=True); (W / "4n").mkdir(exist_ok=True)
    to, fo = O4.build_outputs(box, W / "4o"); tn, fn = N4.build_outputs(box, W / "4n")
    check(f"Master 4 {box}: TXT + TIF byte-identical", to.read_bytes() == tn.read_bytes() and fo.read_bytes() == fn.read_bytes())
w_, e_, s_, n_, lab = N4.parse_master4("82w, 81w, 30n, 31n"); rec = N4.cell_records(w_, e_, s_, n_)
O4.make_cell55_zoom_demo_tpkx(W / "4o" / "demo.tpkx", rec, lab); N4.make_cell55_zoom_demo_tpkx(W / "4n" / "demo.tpkx", rec, lab)
do, dn = members(W / "4o" / "demo.tpkx"), members(W / "4n" / "demo.tpkx")
check("Master 4 Cell 55 demo: bundles + root identical", all(do[k] == dn[k] for k in do if k != "iteminfo.json") and list(do) == list(dn))
for typed in ("-82,-81,30,31", "82w 81w 30n 31n"):
    try:
        N4.parse_master4(typed); e = None
    except ValueError as x:
        e = str(x)
    check(f"Master 4 '{typed}' -> message shows 82w, 81w, 30n, 31n", e and "82w, 81w, 30n, 31n" in e, e)

for ok, name, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
print("ALL PASS" if all(r[0] for r in results) else f"{sum(not r[0] for r in results)} FAILED")
sys.exit(0 if all(r[0] for r in results) else 1)
