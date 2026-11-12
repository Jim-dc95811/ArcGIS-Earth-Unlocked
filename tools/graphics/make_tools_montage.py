"""The 10 tools in action - front page montage (Jim 2026-11-08 17:34: 'That link for 10, and a photo montage
representing those 10, should be at the top. 7 reference has to go').

The 10 = the folders in downloads/ArcGIS_Earth_Unlocked_All_Tools.zip (tools/make_all_tools_zip.py), in that order.
Pictures are the front-page tool pictures in images/. (2026-11-11: the PRAVE/RMC tester left the 10; the P25 GPS
Tracker took slot 4, with the live two-unit map shot `p25_gps_tracker.jpg`. The tester-console tile code is kept
below only in case a future tile has no screenshot.)

    python3 tools/graphics/make_tools_montage.py      (run from the Unlocked repo root)
writes images/ten_tools_montage.jpg (2000 px wide) and site/images/ten_tools_montage.jpg.
"""
import contextlib, datetime as dt, importlib.util, io, math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
IMG = ROOT / "images"
NAVY, NAVY2, GOLD, WHITE, GREY = (11, 25, 54), (18, 38, 78), (245, 185, 30), (255, 255, 255), (200, 210, 228)
F = "/usr/share/fonts/truetype/google-fonts/Poppins-{}.ttf"
font = lambda w, s: ImageFont.truetype(F.format(w), s)

TOOLS = [  # (name, one line, picture, focus (x, y) 0-1 for the crop)
    ("MBTILES CONVERTER", "QGIS maps, offline in ArcGIS Earth", "mbtiles_converter.jpg", (0.5, 0.5)),
    ("MASTER 4 GRID MAKER", "100 numbered map cells", "master4_grid.jpg", (0.5, 0.5)),
    ("PRAVE / ME TRACKER", "radio units live on the map", "prave_me_tracker.jpg", (0.5, 0.5)),
    ("P25 GPS TRACKER", "radio GPS live on the map", "p25_gps_tracker.jpg", (0.5, 0.5)),
    ("EARTHSTICK", "fly the world with a joystick", "earthstick.jpg", (0.5, 0.5)),
    ("WORLD GATE MAKER", "your own gates, city to city", "world_gate_maker_v1.1_seattle.jpg", (0.5, 0.5)),
    ("OBJECT FACTORY", "beacons and objects in the sky", "object_factory.jpg", (0.5, 0.5)),
    ("POINTLAYER", "hydrants and public points offline", "pointlayer.jpg", (0.5, 0.5)),
    ("PARCEL100", "click a parcel: owner and address", "parcel100.jpg", (0.5, 0.5)),
    ("PICTURE WORLD MAKER", "fly into giant pictures", "picture_world_maker.jpg", (0.5, 0.5)),
    ("GARMIN USB GPS TRACKER", "your own GPS live on the map", "garmin_gps_tracker.jpg", (0.5, 0.42)),
]

W, COLS, PAD, GAP = 2000, 4, 24, 16
TW = (W - 2 * PAD - (COLS - 1) * GAP) // COLS          # tile width
PH = round(TW * 9 / 16)                                 # picture height
CH = 92                                                 # caption height
ROWS = math.ceil(len(TOOLS) / COLS)
H = 2 * PAD + ROWS * (PH + CH) + (ROWS - 1) * GAP


def tester_console(tester_py):
    """The tester's own startup banner + the sentences it sends, printed the way it prints them."""
    spec = importlib.util.spec_from_file_location("tester", tester_py)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m.print_startup_banner()
    lines = [l for l in buf.getvalue().splitlines()][1:20]
    t = dt.datetime(2026, 11, 8, 22, 30, 0, tzinfo=dt.timezone.utc)
    for i, unit in enumerate(m.TEST_UNITS[1:4], start=1):
        lines.append(f"RMC   {i:05d}: {m.make_gprmc_sentence(t + dt.timedelta(seconds=i))}")
        rssi = "blank" if unit["rssi"] is None else f"{unit['rssi']} dBm"
        lines.append(f"PRAVE {i:05d}: {m.unit_display_id(unit)}  RSSI {rssi:<9}  expected {unit['expected']}")
        lines.append(f"             {m.make_prave_sentence(unit, t + dt.timedelta(seconds=i))}")
    return lines


def console_tile(lines, w, h):
    s = 3
    im = Image.new("RGB", (w * s, h * s), (12, 12, 12))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w * s, 15 * s], fill=(32, 32, 32))
    d.text((8 * s, 2 * s), "PRAVE / RMC Field Decoder Tester - Version 1.0 Gold",
           font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 8 * s), fill=(220, 220, 220))
    mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 6 * s)
    y = 20 * s
    for line in lines:
        col = (110, 230, 120) if line.lstrip().startswith(("$", "RMC", "PRAVE 0")) else (205, 205, 205)
        d.text((6 * s, y), line, font=mono, fill=col)
        y += 7 * s
    return im.resize((w, h), Image.LANCZOS)


def crop(img, w, h, focus):
    r = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x = round((img.width - w) * focus[0]); y = round((img.height - h) * focus[1])
    return img.crop((x, y, x + w, y + h))


def main():
    # The tester tile was retired 2026-11-11 (P25 GPS Tracker took slot 4); tester_console
    # only runs if a tile still has no screenshot (pic is None) and a tester .py was passed.
    tester_lines = tester_console(sys.argv[1]) if (any(t[2] is None for t in TOOLS) and len(sys.argv) > 1) else []
    out = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(out)
    for i, (name, line, pic, focus) in enumerate(TOOLS):
        r, c = divmod(i, COLS)
        x, y = PAD + c * (TW + GAP), PAD + r * (PH + CH + GAP)
        tile = console_tile(tester_lines, TW, PH) if pic is None else crop(Image.open(IMG / pic).convert("RGB"), TW, PH, focus)
        out.paste(tile, (x, y))
        d.rectangle([x, y + PH, x + TW - 1, y + PH + 5], fill=GOLD)
        d.rectangle([x, y + PH + 6, x + TW - 1, y + PH + CH - 1], fill=NAVY2)
        cx, cy, rad = x + 30, y + PH + 6 + (CH - 6) // 2, 20
        d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=GOLD)
        num = str(i + 1)
        d.text((cx, cy + 1), num, font=font("Bold", 24 if len(num) == 1 else 20), fill=NAVY, anchor="mm")
        nf = font("Bold", 21)
        while d.textlength(name, font=nf) > TW - 70 and nf.size > 14:
            nf = font("Bold", nf.size - 1)
        d.text((x + 60, cy - 6), name, font=nf, fill=GOLD, anchor="ls")
        lf = font("Medium", 15)
        while d.textlength(line, font=lf) > TW - 70 and lf.size > 11:
            lf = font("Medium", lf.size - 1)
        d.text((x + 60, cy + 20), line, font=lf, fill=WHITE, anchor="ls")
        d.rectangle([x, y, x + TW - 1, y + PH + CH - 1], outline=(40, 70, 130), width=2)
    for p in (IMG / "ten_tools_montage.jpg", ROOT / "site" / "images" / "ten_tools_montage.jpg"):
        out.save(p, quality=88, optimize=True)
    print("made", out.size)


if __name__ == "__main__":
    main()
