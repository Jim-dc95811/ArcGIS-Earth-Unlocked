#!/usr/bin/env python3
"""Picture World Maker pipeline rig (v0.2.3+: photo mode only, no QGIS anywhere).

Runs PWM_PIPELINE.build() end to end and reports time, tiles, stages, output
files and leftover temp folders (must be 0):
  TPKX, Both, MBTiles, the zoom-24 TPKX refusal, cancel mid-build, and a
  GeoTIFF (map coordinates) - built flat like any picture since v0.2.3.

Usage:
  python3 picture_world_maker_rig.py "<repo>/Picture World Maker/System Files" \
      --photo Kings_reach_panorama_1.jpg [--zmax 18] [--work DIR]

Use a big photo (Jim's 50,000 px Kings Reach panorama) so the cancel run is
still building after 3 s. Compare TPKX files with ../tpkx_compare.py.
History: v0.1.6-v0.2.2 versions of this rig also drove the QGIS route with a
stand-in QGIS folder (shell scripts named like the real tools); the QGIS route
was removed in v0.2.3 (Jim: ArcGIS Earth opens GeoTIFFs directly).
"""
import argparse
import glob
import pathlib
import sys
import tempfile
import threading
import time

ap = argparse.ArgumentParser()
ap.add_argument("system_files")
ap.add_argument("--photo", required=True)
ap.add_argument("--zmax", type=int, default=18)
ap.add_argument("--work", default=tempfile.mkdtemp(prefix="pwm_rig_"))
a = ap.parse_args()

SF = pathlib.Path(a.system_files).resolve()
R = pathlib.Path(a.work).resolve()
R.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SF))
import PWM_PIPELINE as P  # noqa: E402
from PIL import Image, TiffImagePlugin  # noqa: E402

cfg = P.load_config(SF)
photo = pathlib.Path(a.photo).resolve()

# a small GeoTIFF with a ModelTiepoint tag (= "has map coordinates")
geo = R / "geo_probe.tif"
ifd = TiffImagePlugin.ImageFileDirectory_v2()
ifd[33922] = (0.0, 0.0, 0.0, 500000.0, 3300000.0, 0.0)
ifd.tagtype[33922] = 12
Image.new("RGB", (3000, 2000), (90, 140, 60)).save(geo, tiffinfo=ifd)


def run(name, src, mode, zmax=a.zmax, cancel_after=None):
    out = R / "out" / name
    ev, msgs = threading.Event(), []
    if cancel_after:
        threading.Timer(cancel_after, ev.set).start()
    before = set(glob.glob(tempfile.gettempdir() + "/Picture_World_*"))
    t0 = time.monotonic()
    files = {}
    try:
        r = P.build(cfg, src, "auto", mode, out, "rig", 0, zmax, 1.0, lambda *m: msgs.append(m), ev)
        res = f"OK tiles={r.tile_count:,} bundles={r.bundle_count}"
        files = {p.name: p.stat().st_size for p in out.iterdir()}
    except Exception as e:  # report, keep going
        res = f"{type(e).__name__}: {str(e)[:110]}"
    left = set(glob.glob(tempfile.gettempdir() + "/Picture_World_*")) - before
    print(f"{name:18s} {time.monotonic()-t0:6.1f}s  {res} | stages={sorted({m[0] for m in msgs})} | temp left={len(left)}")
    for k, v in files.items():
        print(f"{'':21s}{k}: {v/1e6:,.1f} MB")


info = P.inspect_raster(cfg, photo)
print(f"photo: {info.width} x {info.height} {info.driver} -> {info.mode_suggested}")
gi = P.inspect_raster(cfg, geo)
print(f"GeoTIFF: {gi.width} x {gi.height} -> {gi.mode_suggested}, has map coordinates = {gi.has_crs}")
run("tpkx", photo, "tpkx")
run("both", photo, "both")
run("mbtiles", photo, "mbtiles")
run("zoom24_tpkx", photo, "tpkx", zmax=24)        # must refuse before any work
run("cancel_3s", photo, "tpkx", cancel_after=3)  # must stop, clean up, no output
run("geotiff_tpkx", geo, "tpkx")
print("work folder:", R)
