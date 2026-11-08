"""Object Factory 2.1 vs 2.0: every output from good input must have identical contents; the
2.1 hardening (Excel encodings, quote marks, blank rows, number checks) checked one by one.
No Tk here, so PNG normalization is a plain copy in both (same as object_factory_test_v12.py).

python3 object_factory_test_v21.py <2.0 .py> <2.1 .py> <icons dir> <samples dir>
"""
import os, shutil, sys, zipfile, pathlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from object_factory_load import load

OLD, NEW = load(sys.argv[1]), load(sys.argv[2])
ICONS, SAMPLES = pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
W = pathlib.Path(os.environ.get("WORK", "/tmp/of21")); shutil.rmtree(W, ignore_errors=True); W.mkdir(parents=True)
results = []
def check(name, ok, detail=""): results.append((bool(ok), name, detail))

def copy_norm(source, dest, master=None, max_dim=256):
    source, dest = pathlib.Path(source), pathlib.Path(dest)
    if source.suffix.lower() != ".png": raise ValueError(f"PNG required: {source.name}")
    if not source.is_file(): raise FileNotFoundError(source)
    dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, dest); return {"factor": 1}
for m in (OLD, NEW):
    m.icon_dir = lambda: ICONS; m.normalize_png = copy_norm
def zc(p):
    with zipfile.ZipFile(p) as z: return {n: z.read(n) for n in z.namelist()}
def err(f):
    try: f(); return None
    except Exception as e: return str(e)

a, b = W / "old", W / "new"; a.mkdir(); b.mkdir()
# 1. single objects, every mode / popup / tether / label / hide combination
n = 0; same = 0
for mode in ("relativeToGround", "absolute", "clampToGround"):
    for popup in ("Info", "None"):
        for tether in (False, True):
            for hide in (None, 3000):
                for desc, url in (("", ""), ("Line 1\nLine <2> & co", "https://fl511.com/map/Cctv/1362?a=1&b=2")):
                    n += 1
                    args = (ICONS / "camera.png", "Cam & <Co>", 30.62, -81.65, 54.864, 1.5, mode, desc, url, "GO",
                            tether, n % 2 == 0, popup)
                    OLD.create_single_object_kmz(a / f"o{n}.kmz", *args, hide_above_ft=hide)
                    NEW.create_single_object_kmz(b / f"o{n}.kmz", *args, hide_above_ft=hide)
                    same += zc(a / f"o{n}.kmz") == zc(b / f"o{n}.kmz")
check(f"single objects identical ({n} combinations)", same == n, f"{same}/{n}")
# 2. batch lists: the shipped samples, a 100-row stress list with every column, hide_above_ft
stress = W / "stress.txt"
stress.write_text("\n".join(["type|name|lat|lon|alt_m|icon|description|url|link_text|scale|altitude_mode|tether|popup|label|hide_above_ft"] +
    [f"fuel|Fuel {i}|30.{100000+i}|-81.{200000+i}|150||Obj {i} <b>&</b>|https://x.example/?a=1&b={i}|GO|1.4|"
     f"{['relativeToGround','absolute','clampToGround'][i%3]}|{'yes' if i%2 else 'no'}|{'None' if i%5==0 else 'Info'}|"
     f"{'yes' if i%7==0 else 'no'}|{'' if i%4 else 2000}" for i in range(100)]), encoding="utf-8")
csvlist = W / "excel_utf8.csv"
csvlist.write_text('type,name,lat,lon,alt_m,description\nwater,"Hydrant, north",30.4,-81.9,60,"Main, 12 in"\nfuel,Pump,30.41,-81.91,,\n', encoding="utf-8-sig")
for name, path in (("sample_objects.txt", SAMPLES / "sample_objects.txt"), ("simple_objects.txt", SAMPLES / "simple_objects.txt"),
                   ("stress", stress), ("comma CSV with quotes (UTF-8)", csvlist)):
    ra, rb = OLD.parse_batch_rows(path), NEW.parse_batch_rows(path)
    OLD.create_batch_kmz(path, a / "batch.kmz"); NEW.create_batch_kmz(path, b / "batch.kmz")
    check(f"batch identical: {name} ({len(rb)} objects)", ra == rb and zc(a / "batch.kmz") == zc(b / "batch.kmz"))
# 3. sky compass + beacon
OLD.create_sky_compass_kmz(a / "c.kmz", 30.3855, -81.9308, 100, 20000, 6); NEW.create_sky_compass_kmz(b / "c.kmz", 30.3855, -81.9308, 100, 20000, 6)
check("sky compass identical", zc(a / "c.kmz") == zc(b / "c.kmz"))
OLD.create_beacon_kml(a / "b.kml", "Beacon", 30.2, -81.2, 100, 6, "Red"); NEW.create_beacon_kml(b / "b.kml", "Beacon", 30.2, -81.2, 100, 6, "Red")
check("beacon identical", (a / "b.kml").read_bytes() == (b / "b.kml").read_bytes())

# --- the 2.1 fixes ---------------------------------------------------------------------------
# F1 Excel "CSV" (Windows-1252) and "Unicode Text" (UTF-16 tab... we test UTF-16 comma)
ansi = W / "excel_ansi.csv"; ansi.write_bytes("type,name,lat,lon\nwater,Café Hydrant,30.4,-81.9\nfuel,Señor Pump,30.41,-81.91\n".encode("cp1252"))
check("2.0 fails on Excel Windows-1252 CSV", err(lambda: OLD.parse_batch_rows(ansi)) is not None)
rows = NEW.parse_batch_rows(ansi)
check("2.1 reads Excel Windows-1252 CSV with accents", [r["name"] for r in rows] == ["Café Hydrant", "Señor Pump"])
NEW.create_batch_kmz(ansi, b / "ansi.kmz")
check("2.1 accented names written into the KMZ as UTF-8", "Café Hydrant" in zc(b / "ansi.kmz")["doc.kml"].decode("utf-8"))
u16 = W / "excel_u16.csv"; u16.write_bytes("type,name,lat,lon\nwater,Café,30.4,-81.9\n".encode("utf-16"))
check("2.1 reads a UTF-16 list", [r["name"] for r in NEW.parse_batch_rows(u16)] == ["Café"])
# F2 quote marks in | lists
q = W / "quote.txt"; q.write_text('type|name|lat|lon|description\nwater|A|30.4|-81.9|"12 in" main, north side\nwater|B|30.5|-81.9|ok\nwater|C|30.6|-81.9|ok\n', encoding="utf-8")
check("2.0 drops the rows after a leading quote (3 rows -> fewer)", len(OLD.parse_batch_rows(q)) < 3 or
      OLD.parse_batch_rows(q)[0]["description"] != '"12 in" main, north side')
rows = NEW.parse_batch_rows(q)
check("2.1 keeps all 3 rows and the quote marks", [r["name"] for r in rows] == ["A", "B", "C"] and rows[0]["description"] == '"12 in" main, north side')
q.write_text('type|name|lat|lon|description\nwater|A|30.4|-81.9|"unclosed\nwater|B|30.5|-81.9|ok\n', encoding="utf-8")
check("2.1 | list unclosed quote: both rows kept", [r["name"] for r in NEW.parse_batch_rows(q)] == ["A", "B"])
qc = W / "quote.csv"; qc.write_text('type,name,lat,lon,description\nwater,A,30.4,-81.9,"unclosed\nwater,B,30.5,-81.9,ok\nwater,C,30.6,-81.9,ok\n', encoding="utf-8")
e = err(lambda: NEW.parse_batch_rows(qc))
check("2.1 comma list unclosed quote: stops and names line 2", e is not None and e.startswith("Line 2"), e)
# F3 Excel blank rows
blank = W / "blank.csv"; blank.write_text("type,name,lat,lon,,,\nwater,A,30.4,-81.9,,,\n,,,,,,\n\n,,,,,,\nfuel,B,30.41,-81.91,,,\n", encoding="utf-8")
check("2.0 stops on Excel blank rows", err(lambda: OLD.parse_batch_rows(blank)) is not None)
check("2.1 skips Excel blank rows", [r["name"] for r in NEW.parse_batch_rows(blank)] == ["A", "B"])
bad = W / "bad_after_blank.csv"; bad.write_text("type,name,lat,lon\n,,,\nwater,A,thirty,-81.9\n", encoding="utf-8")
e = err(lambda: NEW.parse_batch_rows(bad))
check("2.1 errors still name the real file line", e is not None and e.startswith("Line 3"), e)
# F4 numbers
check("gui_number plain message", NEW.gui_number.__name__ and err(lambda: NEW.gui_number("thirty", "Altitude (ft)")) == "Altitude (ft): 'thirty' is not a number.")
check("gui_number empty box", err(lambda: NEW.gui_number("  ", "Icon scale")) == "Icon scale is empty - type a number.")
check("gui_number thousands comma", NEW.gui_number("1,500", "Altitude (ft)") == 1500)
check("gui_number latitude comma refused", err(lambda: NEW.gui_number("30,4", "Latitude", commas=False)) is not None)
check("gui_number nan refused", err(lambda: NEW.gui_number("nan", "Altitude (ft)")) is not None)
check("gui_number zero scale refused", err(lambda: NEW.gui_number("0", "Icon scale", positive=True)) == "Icon scale must be greater than zero.")
check("object: nan altitude refused", err(lambda: NEW.create_single_object_kmz(b / "x.kmz", ICONS / "object.png", "X", 30, -81, float("nan"), 1.4,
      "relativeToGround", "", "", "", False, False, "Info")) is not None and not (b / "x.kmz").exists())
check("object: scale 0 refused", err(lambda: NEW.create_single_object_kmz(b / "x.kmz", ICONS / "object.png", "X", 30, -81, 50, 0,
      "relativeToGround", "", "", "", False, False, "Info")) is not None)
sc = W / "scale0.txt"; sc.write_text("type|name|lat|lon|scale\nwater|A|30.4|-81.9|0\n", encoding="utf-8")
e = err(lambda: NEW.parse_batch_rows(sc))
check("batch: scale 0 refused with its line", e is not None and e.startswith("Line 2"), e)
check("compass: radius 0 refused", err(lambda: NEW.create_sky_compass_kmz(b / "c0.kmz", 30, -81, 0, 20000, 6)) == "Radius (km) must be greater than zero.")
check("compass: negative scale refused", err(lambda: NEW.create_sky_compass_kmz(b / "c0.kmz", 30, -81, 10, 20000, -6)) is not None)
# F5 desktop (Linux here: the fallback)
check("desktop_dir fallback off Windows", NEW.desktop_dir() == pathlib.Path.home() / "Desktop")
# 2.0's own self-test checks that do not need Tk
check("clipboard reader unchanged", all(NEW.parse_clipboard_coordinates(t) == OLD.parse_clipboard_coordinates(t) for t in
      ("30.4009768, -81.9347098", "30.4009768°N 81.9347098°W", "N30.4009768 W81.9347098", "81.9347098°W 30.4009768°N", "30°24'03.5\"N 81°56'05.0\"W")))

for ok, name, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
print("ALL PASS" if all(r[0] for r in results) else f"{sum(not r[0] for r in results)} FAILED")
sys.exit(0 if all(r[0] for r in results) else 1)
