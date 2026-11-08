"""Picture World Maker 2.1 vs 2.0: ordinary 8-bit pictures give byte-identical tiles; the 2.1 picture
fixes (upright phone photos, 16-bit stretch, see-through -> white), the Replace path and the disk-space check.

python3 picture_world_maker_test_v21.py <2.0 System Files dir> <2.1 System Files dir>
"""
import importlib, os, shutil, sqlite3, sys, pathlib, types
from PIL import Image
import numpy as np

OLD_DIR, NEW_DIR = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
W = pathlib.Path(os.environ.get("WORK", "/tmp/pwm21")); shutil.rmtree(W, ignore_errors=True); W.mkdir(parents=True)
results = []
def check(name, ok, detail=""): results.append((bool(ok), name, detail))
def err(f):
    try: f(); return None
    except Exception as e: return f"{type(e).__name__}: {e}"


def load(d):
    for m in ("PWM_PIPELINE", "PWM_PHOTO_TILER"):
        sys.modules.pop(m, None)
    sys.path.insert(0, str(d))
    P = importlib.import_module("PWM_PIPELINE"); T = importlib.import_module("PWM_PHOTO_TILER")
    sys.path.pop(0)
    return P, T


def tiles(mb):
    con = sqlite3.connect(mb)
    try:
        return {(z, x, y): d for z, x, y, d in con.execute("SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles")}
    finally:
        con.close()


def make(P, T, pic, out, z0=0, z1=13):
    cfg = P.load_config(pathlib.Path(P.__file__).parent)
    info = P.inspect_raster(cfg, pic)
    b = P.synthetic_bounds_for_config(cfg, info.width, info.height, 1.0)
    T.build_photo_mbtiles(pic, out, b, z0, z1, name="t")
    return info, tiles(out)


# test pictures
rng = np.random.default_rng(7)
photo = (rng.random((1500, 2600, 3)) * 255).astype("uint8"); photo[:, :300] = (20, 90, 200)
Image.fromarray(photo).save(W / "plain.jpg", quality=90)
Image.fromarray(photo[:900, :900]).save(W / "plain.png")
side = Image.new("RGB", (1600, 900), (200, 40, 40)); side.paste((30, 60, 220), (0, 0, 200, 900))   # blue band = top of the scene
ex = side.getexif(); ex[0x0112] = 6; side.save(W / "phone.jpg", exif=ex, quality=92)
g = (np.linspace(0, 1023, 1200 * 800).reshape(800, 1200)).astype("uint16"); Image.fromarray(g).save(W / "grey16.png")
a = Image.new("RGBA", (1200, 800), (0, 0, 0, 0)); a.paste((250, 200, 0, 255), (300, 200, 900, 600)); a.save(W / "logo.png")

OP, OT = load(OLD_DIR)
o_plain = make(OP, OT, W / "plain.jpg", W / "o_plain.mbtiles")[1]
o_png = make(OP, OT, W / "plain.png", W / "o_png.mbtiles")[1]
o_phone_info, _ = make(OP, OT, W / "phone.jpg", W / "o_phone.mbtiles")
o16 = Image.open(W / "grey16.png").convert("RGB")
NP, NT = load(NEW_DIR)
n_plain = make(NP, NT, W / "plain.jpg", W / "n_plain.mbtiles")[1]
n_png = make(NP, NT, W / "plain.png", W / "n_png.mbtiles")[1]
check(f"8-bit JPEG: all {len(n_plain):,} tiles byte-identical to 2.0", n_plain == o_plain)
check(f"8-bit PNG: all {len(n_png):,} tiles byte-identical to 2.0", n_png == o_png)

# phone photo
n_phone_info, _ = make(NP, NT, W / "phone.jpg", W / "n_phone.mbtiles")
check("2.0 reads the phone photo sideways (1600 x 900)", (o_phone_info.width, o_phone_info.height) == (1600, 900))
check("2.1 reads it upright (900 x 1600)", (n_phone_info.width, n_phone_info.height) == (900, 1600))
up = NT.prepare_picture(Image.open(W / "phone.jpg"), Image)
top_mid = up.getpixel((450, 50)); bottom_mid = up.getpixel((450, 1500))
check("2.1 upright photo: the blue band is at the top", top_mid[2] > 150 and bottom_mid[0] > 150, (top_mid, bottom_mid))

# 16-bit
mean = lambda im: float(np.asarray(im.convert("L")).mean())
n16 = NT.prepare_picture(Image.open(W / "grey16.png"), Image)
check(f"2.0 16-bit grey comes out washed out (mean {mean(o16):.0f} of 255)", mean(o16) > 200)
check(f"2.1 16-bit grey stretched (mean {mean(n16):.0f}, darkest {min(np.asarray(n16.convert('L')).ravel())}, brightest {max(np.asarray(n16.convert('L')).ravel())})",
      100 < mean(n16) < 155 and min(np.asarray(n16.convert('L')).ravel()) <= 2 and max(np.asarray(n16.convert('L')).ravel()) >= 253)
check("2.1 16-bit picture builds", err(lambda: make(NP, NT, W / "grey16.png", W / "n16.mbtiles")) is None)

# transparency
n_logo = NT.prepare_picture(Image.open(W / "logo.png"), Image)
check("2.0 see-through corner turns black", Image.open(W / "logo.png").convert("RGB").getpixel((10, 10)) == (0, 0, 0))
check("2.1 see-through corner is white, art unchanged", n_logo.getpixel((10, 10)) == (255, 255, 255) and n_logo.getpixel((600, 400)) == (250, 200, 0))

# existing output: plain message, and replace_existing
cfg = NP.load_config(NEW_DIR)
outd = W / "out"; outd.mkdir()
(outd / "plain_spot01.mbtiles").write_text("old")
e = err(lambda: NP.build(cfg, W / "plain.jpg", "auto", "mbtiles", outd, "plain_spot01", 0, 10))
check("2.1 existing file -> plain message", e and "is already in" in e and "Choose another name" in e, e)
r = NP.build(cfg, W / "plain.jpg", "auto", "mbtiles", outd, "plain_spot01", 0, 10, replace_existing=True)
check("2.1 Replace: the old file is replaced by a real MBTiles", (outd / "plain_spot01.mbtiles").stat().st_size > 1000 and r.tile_count > 0)
oe = err(lambda: OP.build(OP.load_config(OLD_DIR), W / "plain.jpg", "auto", "mbtiles", outd, "plain_spot01", 0, 10))
check("2.0 existing file -> only the path", oe and "already" not in oe.split(":", 1)[1].lower(), oe)

# disk space
need_t, need_o = NP.space_needed(35216, "tpkx")
check(f"Kings Reach estimate: {need_t/1e9:.1f} GB working + {need_o/1e9:.1f} GB output (measured 0.47 + 0.44)", 0.9e9 < need_t < 2e9 and 0.5e9 < need_o < 1.2e9)
real = shutil.disk_usage
NP.shutil.disk_usage = lambda p: types.SimpleNamespace(total=1, used=1, free=50_000_000)
e = err(lambda: NP.build(cfg, W / "plain.jpg", "auto", "tpkx", W / "out2", "x", 0, 18))
NP.shutil.disk_usage = real
check("2.1 too little disk -> stops before building, plain message", e and "Not enough disk space" in e and not (W / "out2" / "x.tpkx").exists(), e)
check("2.1 enough disk -> no complaint", err(lambda: NP.check_disk_space(1000, "both", W)) is None)

for ok, name, detail in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
print("ALL PASS" if all(r[0] for r in results) else f"{sum(not r[0] for r in results)} FAILED")
sys.exit(0 if all(r[0] for r in results) else 1)
