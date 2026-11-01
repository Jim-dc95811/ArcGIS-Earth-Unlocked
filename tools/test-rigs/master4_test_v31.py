"""Regression + hardening tests for Master 4 Grid Maker v3.1 against v3."""
import hashlib, importlib.util, json, os, shutil, subprocess, sys, zipfile, pathlib
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
V3 = "/home/claude/repos/QGIS-Mbtile-to-ArcGIS-Earth-TPKX/Master4_Grid_Maker.py"
V31 = "/home/claude/dev/master4_v3.1/Master4_Grid_Maker.py"
W = HERE / "t31"
shutil.rmtree(W, ignore_errors=True); W.mkdir()
results = []


def check(name, ok, detail=""):
    results.append((ok, name, detail))


def load(path, alias):
    spec = importlib.util.spec_from_file_location(alias, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


v3, v31 = load(V3, "m4v3"), load(V31, "m4v31")
read = lambda p: pathlib.Path(p).read_bytes()

# 1. Byte-for-byte regression: TXT and TIF for many boxes.
boxes = ["82w, 81w, 30n, 31n", "10e, 11e, 30n, 31n", "82w, 81w, 31s, 30s", "1w, 0e, 0n, 1n",
         "1w, 0w, 1s, 0s", "0e, 1e, 0n, 1n", "179e, 180e, 84n, 85n", "180w, 179w, 85s, 84s",
         "82W,81W,30N,31N", " 82 w ,  81 w , 30 n , 31 n "]
for i, box in enumerate(boxes):
    a = v3.build_outputs(box, output_dir=W / f"r3_{i}")
    b = v31.build_outputs(box, output_dir=W / f"r31_{i}")
    same_names = [p.name for p in a] == [p.name for p in b]
    same_bytes = all(read(x) == read(y) for x, y in zip(a, b))
    check(f"regression {box.strip()!r}: same file names and identical TXT+TIF bytes", same_names and same_bytes,
          ", ".join(p.name for p in b))
    left = sorted(os.listdir(W / f"r31_{i}"))
    check(f"regression {box.strip()!r}: no .partial files left", not any(f.endswith(".partial") for f in left))

# 2. Against Jim's sample TIF: georeferencing identical, all non-label pixels identical.
s = Image.open(HERE / "sample.tif"); g = Image.open(W / "r31_0" / "Master4_82W_81W_30N_31N_Grid.tif")
tags_same = all(s.tag_v2.get(t) == g.tag_v2.get(t) for t in (33550, 33922, 34735, 42113)) and s.size == g.size
a, b = np.array(s), np.array(g)
cols = [x for x in range(a.shape[1]) if (a[:, x] == 255).mean() > 0.9]
rows = [y for y in range(a.shape[0]) if (a[y, :] == 255).mean() > 0.9]
check("sample TIF: same size and GeoTIFF tags (scale, tiepoint, EPSG keys, NoData)", tags_same)
check("sample TIF: every grid-line pixel identical", bool((a[:, cols] == b[:, cols]).all() and (a[rows, :] == b[rows, :]).all()))

# 3. Decimal / leading-zero whole degrees now work and match the normal output exactly.
for i, box in enumerate(["82.0w, 81w, 30n, 31n", "082w, 081w, 030n, 031n", "82.00W, 081.0w, 30.0n, 031N"]):
    try:
        out = v31.build_outputs(box, output_dir=W / f"d_{i}")
        ok = [p.name for p in out] == ["Master4_82W_81W_30N_31N_Extents.txt", "Master4_82W_81W_30N_31N_Grid.tif"] \
             and all(read(x) == read(W / "r31_0" / x.name) for x in out)
        det = ", ".join(p.name for p in out)
    except Exception as e:
        ok, det = False, f"{type(e).__name__}: {e}"
    check(f"input {box!r}: named 82W_81W_30N_31N, identical to normal entry", ok, det)
for box in ["82.5w, 81.5w, 30n, 31n", "81w, 82w, 30n, 31n", "82w, 81w, 30n", "82w, 81w, 30n, 32n"]:
    try:
        v31.build_outputs(box, output_dir=W / "rej"); ok, det = False, "accepted"
    except ValueError as e:
        ok, det = True, str(e)
    check(f"input {box!r}: still rejected with a message", ok and not (W / "rej").exists() or ok and not os.listdir(W / "rej"), det)

# 4. TXT/TIF pair: a TIF failure leaves the previous pair untouched and no partial files.
d = W / "pair"; first = v31.build_outputs("82w, 81w, 30n, 31n", output_dir=d)
before = {p.name: read(p) for p in first}
real = v31.make_grid_tif
def bad_tif(*a, **k): raise OSError("disk full (simulated)")
v31.make_grid_tif = bad_tif
try:
    v31.build_outputs("82w, 81w, 30n, 31n", output_dir=d); err = None
except OSError as e:
    err = str(e)
v31.make_grid_tif = real
check("TIF failure: error raised, previous TXT+TIF untouched, no partial files",
      err and sorted(os.listdir(d)) == sorted(before) and all(read(d / n) == b for n, b in before.items()), err)

# Locked TIF on replace -> plain message.
real_replace = v31.os.replace
def locked(src, dst):
    if str(dst).endswith(".tif"): raise PermissionError(13, "Permission denied")
    return real_replace(src, dst)
v31.os.replace = locked
try:
    v31.build_outputs("82w, 81w, 30n, 31n", output_dir=d); err = None
except PermissionError as e:
    err = str(e)
v31.os.replace = real_replace
check("locked TIF: plain 'may be open in ArcGIS Earth' message, old pair untouched, no partials",
      bool(err) and "open in ArcGIS Earth" in err and sorted(os.listdir(d)) == sorted(before)
      and all(read(d / n) == b for n, b in before.items()), err)

# 5. Demo TPKX: identical content to v3 (GUID excepted).
w, e, s_, n, lab = v31.parse_master4("82w, 81w, 30n, 31n")
recs = v31.cell_records(w, e, s_, n)
(W / "d3").mkdir(); (W / "d31").mkdir()
p3 = v3.make_cell55_zoom_demo_tpkx(W / "d3" / v3.zoom_demo_filename(lab), recs, lab)
p31 = v31.make_cell55_zoom_demo_tpkx(W / "d31" / v31.zoom_demo_filename(lab), recs, lab)
za, zb = zipfile.ZipFile(p3), zipfile.ZipFile(p31)
diff = [x for x in za.namelist() if za.read(x) != zb.read(x)]
ia, ib = json.loads(za.read("iteminfo.json")), json.loads(zb.read("iteminfo.json"))
check("demo TPKX: same name and entries; only iteminfo GUID differs",
      p3.name == p31.name and za.namelist() == zb.namelist() and diff == ["iteminfo.json"]
      and [k for k in ia if ia[k] != ib[k]] == ["guid"], f"{len(za.namelist())} entries, differ: {diff}")
check("demo TPKX: no .partial left after success", sorted(os.listdir(W / "d31")) == [p31.name])

# Interrupted demo: nothing left, rerun works.
(W / "di").mkdir(); target = W / "di" / v31.zoom_demo_filename(lab)
real_copy = v31.shutil.copyfileobj; c = [0]
def boom(*a, **k):
    c[0] += 1
    if c[0] == 6: raise KeyboardInterrupt
    return real_copy(*a, **k)
v31.shutil.copyfileobj = boom
try:
    v31.make_cell55_zoom_demo_tpkx(target, recs, lab)
except KeyboardInterrupt:
    pass
v31.shutil.copyfileobj = real_copy
check("interrupted demo: no .tpkx and no .partial left", os.listdir(W / "di") == [], str(os.listdir(W / "di")))
try:
    v31.make_cell55_zoom_demo_tpkx(target, recs, lab); ok = True
except Exception as e:
    ok = False
check("interrupted demo: rerun succeeds", ok and os.listdir(W / "di") == [target.name])
try:
    v31.make_cell55_zoom_demo_tpkx(target, recs, lab); err = None
except FileExistsError as e:
    err = str(e)
check("existing demo: clear message, not overwritten", bool(err) and "delete or rename" in err, err)

# 6. Interactive flow through the real program (stdin), as the .bat runs it.
def session(stdin, harness=None):
    cwd = W / f"s{len(results)}"; cwd.mkdir()
    cmd = [sys.executable, V31] if harness is None else [sys.executable, "-c", harness]
    p = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True)
    files = sorted(os.listdir(cwd / "C:\\downloads")) if (cwd / "C:\\downloads").exists() else []
    return p.returncode, p.stdout + p.stderr, files

code, out, files = session("82.5w, 81w, 30n, 31n\n81w,82w,30n,31n\n82w, 81w, 30n, 31n\nn\n")
check("typo then valid entry: asks again, then creates TXT+TIF, exit 0",
      code == 0 and out.count("ERROR:") == 2 and out.count("Try again") == 2 and files == ["Master4_82W_81W_30N_31N_Extents.txt", "Master4_82W_81W_30N_31N_Grid.tif"],
      f"exit={code} files={files}")
check("banner shows version", "Master 4 Grid Maker v3.1" in out)
code, out, files = session("\n")
check("blank entry: quits cleanly, nothing created, exit 0", code == 0 and "nothing created" in out and files == [], f"exit={code}")
code, out, files = session("bad\n")  # input ends (EOF) after one bad entry
check("input closed mid-session: 'Cancelled.', no traceback, exit 1", code == 1 and "Cancelled." in out and "Traceback" not in out, f"exit={code}")
code, out, files = session("82w, 81w, 30n, 31n\ny\n")
check("full run with demo: TXT+TIF+demo created, no partials", code == 0 and len(files) == 3 and not any(f.endswith(".partial") for f in files), str(files))
h = f"""
import builtins, sys; sys.argv=['x']
seq = iter(['82w, 81w, 30n, 31n'])
def fake(prompt=''):
    try: return next(seq)
    except StopIteration: raise KeyboardInterrupt
builtins.input = fake
exec(open({V31!r}).read())
"""
code, out, files = session("", harness=h)
check("Ctrl+C at the demo question: 'Cancelled.', standard files kept, exit 1",
      code == 1 and "Cancelled." in out and "Traceback" not in out and len(files) == 2, f"exit={code} files={files}")

fails = 0
for ok, name, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
    fails += not ok
print(f"\n{len(results) - fails}/{len(results)} passed")
