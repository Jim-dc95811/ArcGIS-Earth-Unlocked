"""World Tiles - draws a picture world straight into map tiles, then a TPKX for ArcGIS Earth.

No giant picture in between: every block of 8 x 8 tiles at the top zoom is drawn on its own (on every
CPU core at once), the lower zooms are made by shrinking 4 tiles into 1, and the result is packed with
Picture World Maker's TPKX converter. Memory stays small however big the world is; only time grows.

The world is placed exactly like Picture World Maker places a flat picture: centred on a World spot
(spot 1 = 30 N 80 W, spots 2-10 one degree east each, 11-20 the row one degree north),
1 picture pixel = 1 Web Mercator metre.

py world_tiles.py [--size 10] [--spot 6] [--zmax 18] [--workers N] [--seed 1] [--out file.tpkx]
"""
import io
import math
import multiprocessing as mp
import os
import sqlite3
import sys
import time
import importlib.util

HALF = 20037508.342789244
RES0 = 156543.03392804097
TILE = 256
GROUP = 8                     # tiles per side drawn together at the top zoom
SS = 2                        # drawn at 2x then shrunk (smooth edges)
BUCKET = 2048                 # object lookup grid, picture pixels
BASE_N = 340                  # the normal city's grid
HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "darkcity.py")
G = {}


def lonlat_to_m(lon, lat):
    lat = max(-85.05112878, min(85.05112878, lat))
    return HALF * lon / 180.0, HALF * math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / math.pi


def m_to_lonlat(x, y):
    return x / HALF * 180.0, math.degrees(2 * math.atan(math.exp(y / HALF * math.pi)) - math.pi / 2)


def spot_center(spot):
    row, col = divmod(int(spot) - 1, 10)
    return 30.0 + row, -80.0 + col


def tile_range(bounds, z):
    """same tile addressing as Picture World Maker"""
    xmin, xmax, ymin, ymax = bounds
    n = 1 << z
    world = HALF * 2.0
    eps = 1e-9

    def txy(x, y):
        tx = int(math.floor(((x + HALF) / world) * n))
        ty = int(math.floor(((HALF - y) / world) * n))
        return max(0, min(n - 1, tx)), max(0, min(n - 1, ty))

    x0, y0 = txy(xmin, ymax)
    x1, y1 = txy(xmax - eps, ymin + eps)
    return x0, x1, y0, y1


def load_engine(n):
    os.environ["DCC_N"] = str(n)
    spec = importlib.util.spec_from_file_location("darkcity", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["darkcity"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- workers: top zoom

def init_draw(n, seed, bounds, zmax, quality):
    E = load_engine(n)
    town = E.Town(seed)
    objs = sorted(town.objs, key=lambda o: (o[0], o[1]))
    buckets = {}
    for idx, o in enumerate(objs):
        bx0, by0, bx1, by1 = o[2]
        for i in range(int(bx0 // BUCKET), int(bx1 // BUCKET) + 1):
            for j in range(int(by0 // BUCKET), int(by1 // BUCKET) + 1):
                buckets.setdefault((i, j), []).append(idx)
    G.update(E=E, town=town, objs=objs, buckets=buckets, bounds=bounds, zmax=zmax, quality=quality)


def draw_region(ox, oy, pw, ph, px_w, px_h):
    """picture region [ox, ox+pw) x [oy, oy+ph) drawn into an image px_w x px_h (already 2x)"""
    E, town, objs, buckets = G["E"], G["town"], G["objs"], G["buckets"]
    from PIL import Image
    k = px_w / pw
    img = Image.new("RGB", (px_w, px_h), E.COL[E.SEA])
    ctx = E.Ctx(img, ox, oy, k)
    corners = [E.inv(ox, oy), E.inv(ox + pw, oy), E.inv(ox, oy + ph), E.inv(ox + pw, oy + ph)]
    cmin, cmax = int(min(p[0] for p in corners)) - 2, int(max(p[0] for p in corners)) + 2
    rmin, rmax = int(min(p[1] for p in corners)) - 2, int(max(p[1] for p in corners)) + 2
    for c in range(cmin, cmax + 1):
        for r in range(rmin, rmax + 1):
            tx = E.X0 + (c - r) * E.HW
            ty = E.Y0 + (c + r) * E.HH
            if tx + E.HW < ox or tx - E.HW > ox + pw or ty > oy + ph or ty + E.TH < oy:
                continue
            E.draw_tile(ctx, town, c, r, town.gt(c, r))
    found = set()
    for i in range(int(ox // BUCKET), int((ox + pw) // BUCKET) + 1):
        for j in range(int(oy // BUCKET), int((oy + ph) // BUCKET) + 1):
            found.update(buckets.get((i, j), ()))
    for idx in sorted(found):
        o = objs[idx]
        bx0, by0, bx1, by1 = o[2]
        if bx1 < ox or bx0 > ox + pw or by1 < oy or by0 > oy + ph:
            continue
        o[3](ctx, *o[4])
    for f in E.OVERLAYS:
        f(ctx, ox, oy, pw, ph)
    return img


def draw_group(task):
    tx0, ty0 = task
    xmin, xmax, ymin, ymax = G["bounds"]
    z = G["zmax"]
    n = 1 << z
    res = RES0 / n                          # metres per tile pixel = picture pixels per tile pixel (1 m/px)
    x0, x1, y0, y1 = tile_range(G["bounds"], z)
    gx0 = -HALF + tx0 * TILE * res
    gy0 = HALF - ty0 * TILE * res
    ox, oy = gx0 - xmin, ymax - gy0
    side = GROUP * TILE * res
    img = draw_region(ox, oy, side, side, GROUP * TILE * SS, GROUP * TILE * SS).reduce(SS)
    out = []
    for i in range(GROUP):
        for j in range(GROUP):
            tx, ty = tx0 + i, ty0 + j
            if x0 <= tx <= x1 and y0 <= ty <= y1:
                buf = io.BytesIO()
                img.crop((i * TILE, j * TILE, (i + 1) * TILE, (j + 1) * TILE)).save(buf, "JPEG", quality=G["quality"])
                out.append((z, tx, n - 1 - ty, buf.getvalue()))
    return out


# ---------------------------------------------------------------- workers: lower zooms

def init_shrink(path, sea, quality):
    G.update(path=path, sea=sea, quality=quality, db=None)


def shrink_row(task):
    """one row of tiles at zoom z, each made from its 4 children at z + 1"""
    from PIL import Image
    z, ty, tx0, tx1 = task
    if G["db"] is None:
        from pathlib import Path
        G["db"] = sqlite3.connect(Path(G["path"]).resolve().as_uri() + "?mode=ro", uri=True, timeout=60)
    db = G["db"]
    n, n2 = 1 << z, 1 << (z + 1)
    rows = {}
    for (c, r, data) in db.execute("SELECT tile_column, tile_row, tile_data FROM tiles WHERE zoom_level=? AND tile_column BETWEEN ? AND ? AND tile_row IN (?, ?)",
                                   (z + 1, 2 * tx0, 2 * tx1 + 1, n2 - 1 - 2 * ty, n2 - 1 - (2 * ty + 1))):
        rows[(c, n2 - 1 - r)] = data
    out = []
    for tx in range(tx0, tx1 + 1):
        big = Image.new("RGB", (2 * TILE, 2 * TILE), G["sea"])
        for dx in (0, 1):
            for dy in (0, 1):
                data = rows.get((2 * tx + dx, 2 * ty + dy))
                if data:
                    big.paste(Image.open(io.BytesIO(data)).convert("RGB"), (dx * TILE, dy * TILE))
        buf = io.BytesIO()
        big.reduce(2).save(buf, "JPEG", quality=G["quality"])
        out.append((z, tx, n - 1 - ty, buf.getvalue()))
    return out


# ---------------------------------------------------------------- main

def build(size=10.0, spot=6, zmax=18, zmin=0, seed=1, workers=None, out=None, quality=85, log=print):
    n = max(60, int(round(BASE_N * math.sqrt(size) / 18)) * 18 + 16)   # keep the street grid whole
    if abs(size - 1.0) < 1e-9:
        n = BASE_N
    E = load_engine(n)
    W, H = E.W, E.H
    lat, lon = spot_center(spot)
    cx, cy = lonlat_to_m(lon, lat)
    bounds = (cx - W / 2.0, cx + W / 2.0, cy - H / 2.0, cy + H / 2.0)
    workers = workers or max(1, min(8, (os.cpu_count() or 2) - 1))
    name = "Dark_Claude_City" + ("" if size == 1 else f"_x{size:g}") + f"_spot{int(spot):02d}"
    out = out or os.path.join(os.path.dirname(HERE), name + ".tpkx")
    mb = os.path.splitext(out)[0] + ".mbtiles"
    total = sum((tile_range(bounds, z)[1] - tile_range(bounds, z)[0] + 1) * (tile_range(bounds, z)[3] - tile_range(bounds, z)[2] + 1) for z in range(zmin, zmax + 1))
    log(f"Dark Claude City x{size:g}: {n} x {n} city tiles, world {W / 1000:.1f} x {H / 1000:.1f} km at World spot {spot} ({lat:.0f}N {abs(lon):.0f}W)")
    log(f"{total:,} map tiles, zoom {zmin}-{zmax}, drawing on {workers} cores")
    if W > 111000:
        log("Note: this world is wider than one World spot box - it spills into the next spots east and west.")
    if os.path.exists(mb):
        os.remove(mb)
    db = sqlite3.connect(mb)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=OFF")
    db.execute("CREATE TABLE metadata (name text, value text)")
    db.execute("CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)")
    lon0, lat0 = m_to_lonlat(bounds[0], bounds[2])
    lon1, lat1 = m_to_lonlat(bounds[1], bounds[3])
    db.executemany("INSERT INTO metadata VALUES (?, ?)", [
        ("name", name), ("format", "jpg"), ("type", "overlay"), ("version", "1.1"), ("description", "Dark Claude City - World Tiles"),
        ("minzoom", str(zmin)), ("maxzoom", str(zmax)), ("bounds", f"{lon0:.8f},{lat0:.8f},{lon1:.8f},{lat1:.8f}"),
        ("center", f"{(lon0 + lon1) / 2:.8f},{(lat0 + lat1) / 2:.8f},{zmax}")])
    db.commit()
    t0 = time.time()
    written = 0
    x0, x1, y0, y1 = tile_range(bounds, zmax)
    tasks = [(tx, ty) for ty in range(y0, y1 + 1, GROUP) for tx in range(x0, x1 + 1, GROUP)]
    log(f"Planning the city on each core ...")
    ctx = mp.get_context("spawn")
    with ctx.Pool(workers, initializer=init_draw, initargs=(n, seed, bounds, zmax, quality)) as pool:
        done = 0
        last = 0
        for res in pool.imap_unordered(draw_group, tasks):
            db.executemany("INSERT INTO tiles VALUES (?, ?, ?, ?)", res)
            written += len(res)
            done += 1
            if time.time() - last > 5 or done == len(tasks):
                last = time.time()
                el = last - t0
                log(f"  zoom {zmax}: {done:,}/{len(tasks):,} blocks drawn ({el:.0f} s, about {el / done * (len(tasks) - done):.0f} s to go)")
                db.commit()
    db.commit()
    db.execute("CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row)")
    db.commit()
    sea = tuple(E.COL[E.SEA])
    with ctx.Pool(workers, initializer=init_shrink, initargs=(mb, sea, quality)) as pool:
        for z in range(zmax - 1, zmin - 1, -1):
            a0, a1, b0, b1 = tile_range(bounds, z)
            step = 64
            rtasks = [(z, ty, tx, min(a1, tx + step - 1)) for ty in range(b0, b1 + 1) for tx in range(a0, a1 + 1, step)]
            for res in pool.imap_unordered(shrink_row, rtasks):
                db.executemany("INSERT INTO tiles VALUES (?, ?, ?, ?)", res)
                written += len(res)
            db.commit()
            log(f"  zoom {z}: done ({time.time() - t0:.0f} s)")
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db.execute("PRAGMA journal_mode=DELETE")
    db.close()
    if written != total:
        raise RuntimeError(f"tile count mismatch: expected {total}, wrote {written}")
    log(f"{written:,} tiles drawn in {time.time() - t0:.0f} s. Packing the TPKX ...")
    spec = importlib.util.spec_from_file_location("mb2tpkx_conv", os.path.join(HERE, "MBTiles_to_TPKX_v0_3_0.py"))
    conv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conv)
    from pathlib import Path
    if os.path.exists(out):
        os.remove(out)
    conv.convert_mbtiles_to_tpkx(Path(mb), Path(out))
    os.remove(mb)
    log(f"Done in {time.time() - t0:.0f} s: {out} ({os.path.getsize(out) / 1e6:,.0f} MB)")
    return out


def main(argv):
    kw = {}
    i = 0
    conv = {"--size": ("size", float), "--spot": ("spot", int), "--zmax": ("zmax", int), "--workers": ("workers", int),
            "--seed": ("seed", int), "--out": ("out", str), "--quality": ("quality", int)}
    while i < len(argv):
        if argv[i] in conv:
            k, f = conv[argv[i]]
            kw[k] = f(argv[i + 1])
            i += 2
        else:
            i += 1
    build(**kw)


if __name__ == "__main__":
    main(sys.argv[1:])
