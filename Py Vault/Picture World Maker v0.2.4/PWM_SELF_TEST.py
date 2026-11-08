from pathlib import Path
import hashlib
from PWM_PIPELINE import check_zoom_range, synthetic_bounds, estimate_synthetic_tiles, recommended_max_zoom, web_mercator_from_lonlat, load_config, synthetic_bounds_for_config

HERE = Path(__file__).resolve().parent
errors=[]
b=synthetic_bounds(20634,10317,1.0)
if b != (-10317.0,10317.0,-5158.5,5158.5): errors.append(f"bounds mismatch: {b}")
count=estimate_synthetic_tiles(b,0,18)
if count != 12489: errors.append(f"manual-proof tile count mismatch: {count}")
if recommended_max_zoom(1.0) != 18: errors.append("recommended max zoom mismatch")

# v0.1.3 regression: flat images park at a deterministic synthetic anchor
# east of Florida instead of at lon/lat 0,0 off Africa.
cfg = load_config(HERE)
cx, cy = web_mercator_from_lonlat(cfg.synthetic_anchor_lon, cfg.synthetic_anchor_lat)
if abs(cfg.synthetic_anchor_lon - (-80.0)) > 1e-9 or abs(cfg.synthetic_anchor_lat - 30.0) > 1e-9:
    errors.append(f"synthetic parking anchor mismatch: {cfg.synthetic_anchor_lon}, {cfg.synthetic_anchor_lat}")
fb = synthetic_bounds_for_config(cfg, 29684, 7620, 1.0)
if abs(((fb[0]+fb[1])/2)-cx) > 0.01 or abs(((fb[2]+fb[3])/2)-cy) > 0.01:
    errors.append(f"Florida parking center mismatch: {fb}")

# v0.2.4: 20 World spots, spot 1 = the old anchor (earlier pictures keep their place),
# 1 degree apart, all in the open-ocean box 30-31 N, 80-71 W, and each spot's picture centred on it.
from PWM_PIPELINE import world_spots, config_for_spot
spots = world_spots(cfg)
if len(spots) != 20: errors.append(f"world spot count {len(spots)}")
if spots[0][1:] != (cfg.synthetic_anchor_lat, cfg.synthetic_anchor_lon): errors.append("world spot 1 is not the anchor")
if len({(la, lo) for _, la, lo in spots}) != 20: errors.append("world spots overlap")
for n, la, lo in spots:
    if not (30.0 <= la <= 31.0 and -80.0 <= lo <= -71.0): errors.append(f"world spot {n} off the ocean grid: {la}, {lo}")
    sb = synthetic_bounds_for_config(config_for_spot(cfg, n), 30000, 21952, 1.0)
    sx, sy = web_mercator_from_lonlat(lo, la)
    if abs((sb[0]+sb[1])/2 - sx) > 0.01 or abs((sb[2]+sb[3])/2 - sy) > 0.01: errors.append(f"world spot {n} centre mismatch")
if synthetic_bounds_for_config(config_for_spot(cfg, 1), 29684, 7620, 1.0) != fb: errors.append("world spot 1 moved the old parking")
try:
    config_for_spot(cfg, 21); errors.append("world spot 21 accepted")
except ValueError:
    pass

# v0.1.6: TPKX stops at zoom 23 (Esri scheme) - refuse 24-25 before any long work starts.
for zmin, zmax, mode, ok in ((0, 18, 'tpkx', True), (0, 23, 'both', True), (0, 24, 'tpkx', False),
                             (0, 25, 'both', False), (0, 25, 'mbtiles', True), (5, 4, 'mbtiles', False)):
    try:
        check_zoom_range(zmin, zmax, mode); got = True
    except ValueError:
        got = False
    if got != ok: errors.append(f"zoom check {zmin}-{zmax} {mode}: expected {'accept' if ok else 'refuse'}")

conv=HERE/'MBTiles_to_TPKX_v0_3_0.py'
sha=hashlib.sha256(conv.read_bytes()).hexdigest()
expected='9fbdd81d4114cddcc99616f465d182b767cc00d26601bba142fad620d3df9dce'
if sha != expected: errors.append(f"converter hash mismatch: {sha}")

# v0.1.5: the converter must write the mb2tpkx 1.1 / ArcGIS-proven TPKX structure.
# Build a tiny 2-zoom PNG MBTiles, convert it, and check the parts v0.1.0 got wrong.
import json, sqlite3, struct, subprocess, sys, tempfile, zipfile, zlib, binascii
def _png256():
    def ch(k, b): return struct.pack('>I', len(b)) + k + b + struct.pack('>I', binascii.crc32(k + b) & 0xffffffff)
    raw = (b'\x00' + b'\x20\x60\xa0' * 256) * 256
    return b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', 256, 256, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b'')
with tempfile.TemporaryDirectory() as td:
    mbt = Path(td) / 'probe.mbtiles'; out = Path(td) / 'probe.tpkx'
    con = sqlite3.connect(mbt)
    con.execute('CREATE TABLE metadata (name text, value text)')
    con.execute('CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)')
    con.executemany('INSERT INTO metadata VALUES (?,?)', [('name', 'probe'), ('format', 'png')])
    t = _png256()
    con.executemany('INSERT INTO tiles VALUES (?,?,?,?)', [(1, 0, 1, t), (1, 1, 1, t), (2, 1, 2, t)])
    con.commit(); con.close()
    r = subprocess.run([sys.executable, str(conv), str(mbt), str(out)], capture_output=True, text=True)
    if r.returncode != 0 or not out.is_file():
        errors.append('converter failed on probe: ' + (r.stdout + r.stderr)[-300:])
    else:
        with zipfile.ZipFile(out) as z:
            names = [i.filename for i in z.infolist()]
            if names[:3] != ['iteminfo.json', 'root.json', 'thumbnail.png']: errors.append(f'member order: {names[:3]}')
            if any(i.compress_type != zipfile.ZIP_STORED or i.create_system != 0 for i in z.infolist()): errors.append('zip entries not stored/Windows-style')
            root = json.loads(z.read('root.json')); item = json.loads(z.read('iteminfo.json'))
            if root['tileImageInfo'] != {'format': 'MIXED', 'compressionQuality': 75, 'bandCount': 1, 'lercError': 0}: errors.append(f"tileImageInfo: {root['tileImageInfo']}")
            if root['tileInfo']['lods'][0] != {'level': 0, 'resolution': 156543.033928, 'scale': 591657527.591555}: errors.append('LOD 0 is not the Esri published value')
            if (root['minLOD'], root['maxLOD'], root['storageInfo']['packetSize']) != (1, 2, 128): errors.append('LOD range / packet size wrong')
            if item['tags'] != '' or item['creator'] != 'MBTilesDirectConverter': errors.append('iteminfo tags/creator wrong')
            bun = z.read('tile/L01/R0000C0000.bundle')
            hdr = struct.unpack_from('<4I3Q6I', bun, 0)
            if hdr[:2] != (3, 0) or hdr[2] != 131092 or hdr[3] != 5 or hdr[5] != len(bun) or hdr[6:] != (40, 131092, 3, 0, 16384, 5, 131072):
                errors.append(f'bundle header differs from the ArcGIS-proven reference: {hdr}')
            idx = struct.unpack_from('<16384Q', bun, 64)
            if sum(1 for v in idx if v != 4) != 2 or idx[2] != 4: errors.append('missing-tile index value must be 4 (Esri)')
            if bun[(idx[0] & ((1 << 40) - 1)):][:8] != t[:8]: errors.append('tile bytes not copied unchanged')
# v0.2.0: photo mode - a small picture must give exactly Picture World Maker's tile set, the
# picture's edge must land where the synthetic placement says, and the TPKX converter must accept it.
try:
    from PIL import Image
    from PWM_PIPELINE import inspect_raster_pillow, synthetic_bounds
    from PWM_PHOTO_TILER import build_photo_mbtiles, count_tiles
    import io as _io
    with tempfile.TemporaryDirectory() as td:
        pic = Path(td) / 'photo_probe.jpg'
        Image.new('RGB', (3000, 1200), (40, 90, 160)).save(pic, quality=90)
        info = inspect_raster_pillow(pic)
        if (info.width, info.height, info.mode_suggested) != (3000, 1200, 'flat'): errors.append(f'Pillow inspection: {info}')
        geo_tif = Path(td) / 'geo_probe.tif'
        im = Image.new('RGB', (64, 64)); from PIL import TiffImagePlugin
        ifd = TiffImagePlugin.ImageFileDirectory_v2(); ifd[33922] = (0.0, 0.0, 0.0, 500000.0, 3300000.0, 0.0); ifd.tagtype[33922] = 12
        im.save(geo_tif, tiffinfo=ifd)
        gi = inspect_raster_pillow(geo_tif)
        if (gi.mode_suggested, gi.has_crs) != ('flat', True): errors.append(f'v0.2.3: a GeoTIFF is built flat and flagged as having coordinates: {gi}')
        bb = synthetic_bounds(3000, 1200, 1.0, *__import__('PWM_PIPELINE').web_mercator_from_lonlat(-80.0, 30.0))
        mbt = Path(td) / 'photo_probe.mbtiles'
        n = build_photo_mbtiles(pic, mbt, bb, 0, 18)
        if n != estimate_synthetic_tiles(bb, 0, 18) or n != count_tiles(bb, 0, 18): errors.append(f'photo tile count {n} != estimate')
        con = sqlite3.connect(mbt); kinds = {r[0][:3] == b'\xff\xd8\xff' for r in con.execute('SELECT tile_data FROM tiles')}; con.close()
        if kinds != {True, False}: errors.append('photo mode should mix JPEG (inside) and PNG (edges)')
        out2 = Path(td) / 'photo_probe.tpkx'
        r2 = subprocess.run([sys.executable, str(conv), str(mbt), str(out2)], capture_output=True, text=True)
        if r2.returncode != 0: errors.append('converter rejected photo-mode MBTiles: ' + (r2.stdout + r2.stderr)[-200:])
except ImportError:
    print('NOTE: Pillow not installed - photo mode checks skipped (the launchers install it).')

if errors:
    print('PICTURE WORLD MAKER SELF TEST: FAIL')
    for e in errors: print(' -',e)
    raise SystemExit(1)
print('PICTURE WORLD MAKER SELF TEST: PASS')
print('Manual proof synthetic bounds:', b)
print('Manual proof Z0-Z18 tile addresses:', f'{count:,}')
print('1 m/pixel recommended max zoom:', recommended_max_zoom(1.0))
print('Synthetic parking anchor:', f'{cfg.synthetic_anchor_lat:.1f}N {abs(cfg.synthetic_anchor_lon):.1f}W')
print('TPKX converter MBTiles_to_TPKX_v0_3_0.py (mb2tpkx 1.1 structure) SHA-256:', sha)
