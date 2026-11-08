"""PointLayer 2.1 vs 2.0 against the PointLayer test server (pointlayer_test_server.py).

python3 pointlayer_test_v21.py <2.0 PointLayer.py> <2.1 PointLayer.py>
"""
import os, re, shutil, sys, threading, types, zipfile, pathlib, xml.dom.minidom
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import pointlayer_test_server as server

fake = types.ModuleType("tkinter"); fake.Tk = type("Tk", (), {})
for sub in ("filedialog", "messagebox", "ttk"):
    m = types.ModuleType("tkinter." + sub); setattr(fake, sub, m); sys.modules["tkinter." + sub] = m
sys.modules["tkinter"] = fake


def load(path, name):
    mod = types.ModuleType(name); mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    mod.time = types.SimpleNamespace(sleep=lambda s: None)
    return mod


OLD, NEW = load(sys.argv[1], "pl20"), load(sys.argv[2], "pl21")
srv = server.start(0); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
BASE = f"http://127.0.0.1:{port}{server.ROOT}"
W = pathlib.Path(os.environ.get("WORK", "/tmp/pl21")); shutil.rmtree(W, ignore_errors=True); W.mkdir(parents=True)
results = []
def check(name, ok, detail=""): results.append((bool(ok), name, detail))
def err(f):
    try: f(); return None
    except Exception as e: return f"{type(e).__name__}: {e}"


def build(mod, layer_url, out, field_meta=True):
    (lu, meta), = mod.discover_point_layers(layer_url)
    ids, oidf = mod.query_object_ids(lu)
    fields = [f["name"] for f in meta["fields"] if f["type"] != "esriFieldTypeOID"]
    feats, missing = mod.download_all_features(lu, ids, oidf, fields, 1000)
    kw = {"field_meta": {f["name"]: f for f in meta["fields"]}} if field_meta else {}
    aliases = {f["name"]: f.get("alias") for f in meta["fields"]}
    mod.write_kmz(out, feats, fields, aliases, lu, meta["name"], 12000, 0.5, mod.built_in_icon_bytes("Red H (hydrant)"), True, **kw)
    mod.write_geojson(out.with_suffix(".geojson"), feats, fields, lu, meta["name"])
    return zipfile.ZipFile(out).read("doc.kml").decode("utf-8"), feats


# 1. clean layer: same KMZ + GeoJSON from 2.0 and 2.1
(W / "v20").mkdir(); (W / "v21").mkdir()
k20, _ = build(OLD, BASE + "/1", W / "v20" / "clean.kmz", field_meta=False)
k21, _ = build(NEW, BASE + "/1", W / "v21" / "clean.kmz")
check("clean layer: KMZ doc.kml identical 2.0 / 2.1", k20 == k21)
check("clean layer: GeoJSON identical", (W / "v20" / "clean.geojson").read_bytes() == (W / "v21" / "clean.geojson").read_bytes())
check("clean layer: 4 placemarks", k21.count("<Placemark>") == 4)

# 2. odd layer with 2.0: the NaN point breaks the Region (or the blank one stops the build)
e = err(lambda: build(OLD, BASE + "/0", W / "odd20.kmz", field_meta=False))
k_old = None if e else zipfile.ZipFile(W / "odd20.kmz").read("doc.kml").decode()
check("2.0 on odd layer: build stops or writes a 'nan' Region",
      e is not None or "<north>nan</north>" in (k_old or ""), e or "region nan")

# 3. odd layer with 2.1
k, feats = build(NEW, BASE + "/0", W / "odd21.kmz")
xml.dom.minidom.parseString(k.encode())
region = dict(re.findall(r"<(north|south|east|west)>([^<]*)<", k))
check("2.1: 4 placemarks (NaN and blank skipped)", k.count("<Placemark>") == 4, k.count("<Placemark>"))
check("2.1: no 'nan' anywhere in the KML", "nan" not in k.lower())
check("2.1: Region is a real box round the 4 hydrants",
      30.39 < float(region["south"]) < float(region["north"]) < 30.41 and -81.95 < float(region["west"]) < float(region["east"]) < -81.93, region)
check("2.1: 2 records counted as no location", sum(1 for f in feats if NEW.extract_point(f) is None) == 2)
check("2.1: code list shows the meaning", "<value>Nassau County</value>" in k and "<value>Town of Hilliard</value>" in k and "<value>Private</value>" in k)
check("2.1: local-midnight date -> 2021-07-01", "<value>2021-07-01</value>" in k)
check("2.1: UTC-midnight date -> 2017-03-01", "<value>2017-03-01</value>" in k)
check("2.1: date with a time keeps it", "<value>2024-01-01 13:00 UTC</value>" in k)
check("2.1: empty date stays empty", k.count("<displayName>Installed</displayName>\n<value></value>") == 1)
check("2.1: GeoJSON keeps raw values", '"OWNER":1' in (W / "odd21.geojson").read_text() and '"INSTALLED":1625112000000' in (W / "odd21.geojson").read_text())

# 4. URLs copied from the browser
for u in (BASE + "/0?f=pjson", BASE + "/0/query", BASE + "/0/query?where=1%3D1&outFields=*", BASE + "/0/#hash", BASE + "?f=json"):
    check(f"2.1 accepts {u.split(server.ROOT)[1] or '(root)'}", err(lambda: NEW.discover_point_layers(u)) is None, err(lambda: NEW.discover_point_layers(u)))
check("2.0 refused ?f=pjson", err(lambda: OLD.discover_point_layers(BASE + "/0?f=pjson")) is not None)
check("2.1 root lists both layers", len(NEW.discover_point_layers(BASE)) == 2)

# 5. not map data
login = f"http://127.0.0.1:{port}/login/arcgis/rest/services/X/FeatureServer/0"
e_old, e_new = err(lambda: OLD.discover_point_layers(login)), err(lambda: NEW.discover_point_layers(login))
check("2.0 login page -> programmer message", e_old and "Expecting value" in e_old, e_old)
check("2.1 login page -> plain message", e_new and "did not send map data" in e_new, e_new)

# 6. desktop fallback and the self-test
check("desktop_dir fallback off Windows", NEW.desktop_dir() == pathlib.Path.home() / "Desktop")
check("2.1 self-test", err(lambda: NEW.run_self_test(W / "selftest")) is None, err(lambda: NEW.run_self_test(W / "selftest2")))

srv.shutdown()
for ok, name, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
print("ALL PASS" if all(r[0] for r in results) else f"{sum(not r[0] for r in results)} FAILED")
sys.exit(0 if all(r[0] for r in results) else 1)
