#!/usr/bin/env python3
"""Picture World Maker photo tiler (v0.2.0) - flat pictures to MBTiles without QGIS.

A flat picture (no coordinates) is parked by Picture World Maker at an exact spot: centred on the configured anchor
(default 30 N, 80 W), 1 picture pixel = synthetic_meters_per_pixel Web Mercator metres, axis-aligned with
the map grid. So making its tiles needs no reprojection: every 256 x 256 tile at every zoom is a patch of
the picture, scaled. This module does exactly that with Pillow, producing the same tile set (same
z/x/y addresses, same placement) that the QGIS route renders, without QGIS.

Tiles fully inside the picture are JPEG (photos compress far better); tiles on the picture's edge are PNG
with transparency so the ocean shows through around it. Esri's TPKX allows mixed tiles (format MIXED).

Command line (for testing):
  python PWM_PHOTO_TILER.py picture.jpg out.mbtiles [zmin] [zmax] [--png] [--quality 85]
"""
from __future__ import annotations

import io
import math
import sqlite3
import sys
import time
from pathlib import Path

WEB_MERCATOR_HALF = 20037508.342789244
WEB_MERCATOR_RES_Z0 = 156543.03392804097
TILE = 256


class PhotoTilerError(RuntimeError):
    pass


class Cancelled(RuntimeError):
    pass


def _tile_range(bounds, z):
    """Same tile addressing as PWM_PIPELINE.estimate_synthetic_tiles."""
    xmin, xmax, ymin, ymax = bounds
    n = 1 << z
    world = WEB_MERCATOR_HALF * 2.0
    eps = 1e-9

    def txy(x, y):
        tx = int(math.floor(((x + WEB_MERCATOR_HALF) / world) * n))
        ty = int(math.floor(((WEB_MERCATOR_HALF - y) / world) * n))
        return max(0, min(n - 1, tx)), max(0, min(n - 1, ty))

    x0, y0 = txy(xmin, ymax)
    x1, y1 = txy(xmax - eps, ymin + eps)
    return x0, x1, y0, y1


def count_tiles(bounds, zmin, zmax) -> int:
    total = 0
    for z in range(zmin, zmax + 1):
        x0, x1, y0, y1 = _tile_range(bounds, z)
        total += (x1 - x0 + 1) * (y1 - y0 + 1)
    return total


def _lonlat(x, y):
    lon = x / WEB_MERCATOR_HALF * 180.0
    lat = math.degrees(2 * math.atan(math.exp(y / WEB_MERCATOR_HALF * math.pi)) - math.pi / 2)
    return lon, lat


def build_photo_mbtiles(source: Path, out_mbtiles: Path, bounds, zmin: int, zmax: int,
                        name: str = "", jpeg: bool = True, quality: int = 85,
                        emit=None, cancel_event=None) -> int:
    """Write an MBTiles (TMS rows) for a flat picture placed at `bounds` (xmin, xmax, ymin, ymax in EPSG:3857 m).
    Returns the number of tiles written. Emits ('render', message, fraction) progress like the QGIS stage."""
    try:
        from PIL import Image
    except Exception as exc:
        raise PhotoTilerError("Pillow is not installed (needed for photo mode).") from exc
    Image.MAX_IMAGE_PIXELS = None
    emit = emit or (lambda *a: None)
    xmin, xmax, ymin, ymax = bounds

    emit("render", "Photo mode — reading the picture once...", 0.06)
    try:
        picture = Image.open(source)
        picture.load()                                 # one full decode, no second copy
    except MemoryError:
        raise
    except Exception as exc:
        raise PhotoTilerError(f"Could not open this picture: {exc}") from exc
    if picture.mode != "RGB":
        picture = picture.convert("RGB")
    width, height = picture.size
    mpp = (xmax - xmin) / width                       # metres per picture pixel
    if abs((ymax - ymin) / height - mpp) > 1e-9 * max(1.0, mpp):
        raise PhotoTilerError("Picture placement is not square-pixel; photo mode needs Picture World Maker's synthetic placement.")

    total = count_tiles(bounds, zmin, zmax)
    out_mbtiles.parent.mkdir(parents=True, exist_ok=True)
    if out_mbtiles.exists():
        out_mbtiles.unlink()
    db = sqlite3.connect(out_mbtiles)
    db.execute("PRAGMA journal_mode=OFF")
    db.execute("PRAGMA synchronous=OFF")
    db.execute("CREATE TABLE metadata (name text, value text)")
    db.execute("CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)")
    lon0, lat0 = _lonlat(xmin, ymin)
    lon1, lat1 = _lonlat(xmax, ymax)
    db.executemany("INSERT INTO metadata VALUES (?, ?)", [
        ("name", name or Path(source).stem), ("format", "jpg" if jpeg else "png"), ("type", "overlay"),
        ("version", "1.1"), ("description", "Picture World Maker photo mode"),
        ("minzoom", str(zmin)), ("maxzoom", str(zmax)),
        ("bounds", f"{lon0:.8f},{lat0:.8f},{lon1:.8f},{lat1:.8f}"),
        ("center", f"{(lon0 + lon1) / 2:.8f},{(lat0 + lat1) / 2:.8f},{zmax}"),
    ])

    levels = {1: picture}                              # reduced copies: factor -> image
    written = 0
    started = time.monotonic()
    last_emit = 0.0
    batch = []
    try:
        for z in range(zmax, zmin - 1, -1):
            res = WEB_MERCATOR_RES_Z0 / (1 << z)       # metres per tile pixel at this zoom
            scale = res / mpp                          # picture pixels per tile pixel
            factor = 1
            while factor * 2 <= scale and width // (factor * 2) >= 1 and height // (factor * 2) >= 1:
                factor *= 2
            if factor not in levels:
                base = max(f for f in levels if f < factor)
                img = levels[base]
                f = base
                while f < factor:
                    img = img.reduce(2)
                    f *= 2
                    levels[f] = img
            work = levels[factor]
            wmpp_x = (xmax - xmin) / work.width
            wmpp_y = (ymax - ymin) / work.height
            x0, x1, y0, y1 = _tile_range(bounds, z)
            n = 1 << z
            for ty in range(y0, y1 + 1):
                for tx in range(x0, x1 + 1):
                    if cancel_event is not None and cancel_event.is_set():
                        raise Cancelled("Build cancelled by operator.")
                    gx0 = -WEB_MERCATOR_HALF + tx * TILE * res
                    gy0 = WEB_MERCATOR_HALF - ty * TILE * res
                    left = (gx0 - xmin) / wmpp_x
                    top = (ymax - gy0) / wmpp_y
                    right = left + TILE * res / wmpp_x
                    bottom = top + TILE * res / wmpp_y
                    inside = left >= 0 and top >= 0 and right <= work.width and bottom <= work.height
                    if inside:
                        tile = work.resize((TILE, TILE), Image.LANCZOS, box=(left, top, right, bottom))
                        buf = io.BytesIO()
                        if jpeg:
                            tile.save(buf, "JPEG", quality=quality, optimize=True)
                        else:
                            tile.save(buf, "PNG", optimize=False)
                    else:
                        cl, ct = max(0.0, left), max(0.0, top)
                        cr, cb = min(float(work.width), right), min(float(work.height), bottom)
                        tile = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
                        if cr > cl and cb > ct:
                            px = TILE / (right - left)
                            dl, dt = round((cl - left) * px), round((ct - top) * px)
                            dr, db_ = round((cr - left) * px), round((cb - top) * px)
                            if dr > dl and db_ > dt:
                                part = work.resize((dr - dl, db_ - dt), Image.LANCZOS, box=(cl, ct, cr, cb))
                                tile.paste(part.convert("RGBA"), (dl, dt))
                        buf = io.BytesIO()
                        tile.save(buf, "PNG", optimize=False)
                    batch.append((z, tx, n - 1 - ty, buf.getvalue()))
                    written += 1
                    if len(batch) >= 500:
                        db.executemany("INSERT INTO tiles VALUES (?, ?, ?, ?)", batch)
                        batch.clear()
                    now = time.monotonic()
                    if now - last_emit >= 0.5 or written == total:
                        last_emit = now
                        emit("render", f"Photo mode — tiles {written:,} / {total:,} (zoom {z})",
                             0.08 + 0.80 * written / max(1, total))
            # lower zooms only use smaller copies - release the bigger ones as soon as they are done
            for f in [f for f in levels if f < factor]:
                del levels[f]
        if batch:
            db.executemany("INSERT INTO tiles VALUES (?, ?, ?, ?)", batch)
        db.execute("CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row)")
        db.commit()
    finally:
        db.close()
        levels.clear()
    if written != total:
        raise PhotoTilerError(f"Tile count mismatch: expected {total}, wrote {written}")
    return written


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        sys.exit(__doc__)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import PWM_PIPELINE as P
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    src, out = Path(args[0]), Path(args[1])
    zmin = int(args[2]) if len(args) > 2 else 0
    zmax = int(args[3]) if len(args) > 3 else 18
    q = int(sys.argv[sys.argv.index("--quality") + 1]) if "--quality" in sys.argv else 85
    with Image.open(src) as im:
        w, h = im.size
    cfg = P.load_config(Path(__file__).resolve().parent)
    b = P.synthetic_bounds_for_config(cfg, w, h)
    t0 = time.monotonic()
    n = build_photo_mbtiles(src, out, b, zmin, zmax, jpeg="--png" not in sys.argv, quality=q,
                            emit=lambda s, m, f: print(m, flush=True) if f and int(f * 100) % 10 == 0 else None)
    print(f"done: {n:,} tiles in {time.monotonic() - t0:.0f} s; Picture World Maker estimate {P.estimate_synthetic_tiles(b, zmin, zmax):,}")
