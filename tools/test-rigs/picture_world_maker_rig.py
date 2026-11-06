#!/usr/bin/env python3
"""Picture World Maker pipeline rig (Linux sandbox, no QGIS, no Tk).

Runs PWM_PIPELINE.build() end to end and reports time, tiles, stages, output
files and leftover temp folders. Two routes:

* QGIS route  - a stand-in QGIS folder is created here: qgis_process.bat /
  python-qgis.bat / gdalinfo / gdal_translate / gdaladdo are shell scripts
  (executable, .bat names are fine on Linux because command_for() only wraps
  .bat in cmd.exe on Windows). python-qgis.bat copies SAMPLE_MBTILES in as
  "QGIS's output", so the TPKX stage runs on real tiles.
  RIG_MODE=silent makes the stand-in QGIS print nothing for 60 s (cancel test).
* Photo route - a real picture through PWM_PHOTO_TILER (Pillow), with the
  QGIS folder pointing nowhere (proves "no QGIS needed").

Usage:
  python3 picture_world_maker_rig.py "<repo>/Picture World Maker/System Files" \
      --mbtiles demo_lon_41.mbtiles [--photo Kings_reach_panorama_1.jpg] [--work DIR]

Compare a TPKX against a reference with ../tpkx_compare.py.
History: built 2026-11-05/06 for Rasta v0.1.6 / v0.2.0 (then RASTA_PIPELINE,
RPF_* worker lines); renamed for Picture World Maker v0.2.1.
"""
import argparse
import dataclasses
import glob
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time

ap = argparse.ArgumentParser()
ap.add_argument("system_files")
ap.add_argument("--mbtiles", required=True, help="any 256 px raster MBTiles; stands in for QGIS output")
ap.add_argument("--photo", help="a real JPG/PNG for the photo-mode runs (big = slow)")
ap.add_argument("--zmax", type=int, default=18)
ap.add_argument("--work", default=tempfile.mkdtemp(prefix="pwm_rig_"))
a = ap.parse_args()

SF = pathlib.Path(a.system_files).resolve()
R = pathlib.Path(a.work).resolve()
R.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SF))
import PWM_PIPELINE as P  # noqa: E402

PIDFILE = R / "stand_in_qgis.pid"
STAND_INS = {
    "qgis_process.bat": 'echo "QGIS version: 3.44.9-Solothurn"\n',
    "python-qgis.bat": f'''OUT=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['output_mbtiles'])" "$2")
if [ "$RIG_MODE" = "silent" ]; then echo "$$" > "{PIDFILE}"; sleep 60; fi
echo "PWM_INFO Raster extent: test"; echo "PWM_PROGRESS 50.000"; echo "PWM_PROGRESS 100.000"
cp "{pathlib.Path(a.mbtiles).resolve()}" "$OUT"
echo "PWM_RESULT_JSON {{\\"output\\": \\"$OUT\\"}}"
''',
    # a flat 29,684 x 7,620 JPEG with no coordinate system
    "gdalinfo": '''echo '{"size":[29684,7620],"driverShortName":"JPEG","coordinateSystem":{"wkt":""}}'
echo "Warning 1: harmless diagnostic" >&2
''',
    "gdal_translate": 'for last; do :; done; echo staged > "$last"\n',
    "gdaladdo": "exit 0\n",
}
qgis = R / "QGIS"
(qgis / "bin").mkdir(parents=True, exist_ok=True)
for name, body in STAND_INS.items():
    f = qgis / "bin" / name
    f.write_text("#!/bin/sh\n" + body)
    f.chmod(f.stat().st_mode | stat.S_IEXEC)
fake = R / "skyline.jpg"           # a fake file; the stand-in gdalinfo describes it
fake.write_bytes(b"\xff\xd8\xff fake")

base = P.load_config(SF)
def cfg(**kw):
    return dataclasses.replace(base, **kw)

def run(name, c, src, mode, zmax=a.zmax, cancel_after=None, rig="normal"):
    os.environ["RIG_MODE"] = rig
    out = R / "out" / name
    shutil.rmtree(out, ignore_errors=True)
    ev, msgs = threading.Event(), []
    if cancel_after:
        threading.Timer(cancel_after, ev.set).start()
    before = set(glob.glob(tempfile.gettempdir() + "/Picture_World_*"))
    t0 = time.monotonic()
    files = {}
    try:
        r = P.build(c, src, "auto", mode, out, "rig", 0, zmax, 1.0, lambda *m: msgs.append(m), ev)
        res = f"OK tiles={r.tile_count:,} bundles={r.bundle_count}"
        files = {p.name: p.stat().st_size for p in out.iterdir()}
    except Exception as e:  # report, keep going
        res = f"{type(e).__name__}: {str(e)[:110]}"
    left = set(glob.glob(tempfile.gettempdir() + "/Picture_World_*")) - before
    print(f"{name:24s} {time.monotonic()-t0:6.1f}s  {res} | stages={sorted({m[0] for m in msgs})} | temp left={len(left)}")
    for k, v in files.items():
        print(f"{'':27s}{k}: {v/1e6:,.1f} MB")

qgis_cfg = cfg(qgis_install_dir=qgis, photo_engine="qgis")
print("== QGIS route (stand-in QGIS)")
run("qgis_tpkx", qgis_cfg, fake, "tpkx")
run("qgis_both", qgis_cfg, fake, "both")
run("qgis_mbtiles", qgis_cfg, fake, "mbtiles")
run("qgis_zoom24_tpkx", qgis_cfg, fake, "tpkx", zmax=24)       # must refuse before any work
run("qgis_cancel_silent", qgis_cfg, fake, "tpkx", cancel_after=1.0, rig="silent")
if PIDFILE.exists():
    alive = subprocess.run(["ps", "-p", PIDFILE.read_text().strip()], capture_output=True).returncode == 0
    print(f"{'':27s}stand-in QGIS still running after cancel: {alive}")

if a.photo:
    photo = pathlib.Path(a.photo).resolve()
    noqgis = cfg(qgis_install_dir=pathlib.Path("/nonexistent/QGIS 3.44.9"))
    info = P.inspect_raster(noqgis, photo)
    print(f"== Photo route (no QGIS)  inspect: {info.width} x {info.height} {info.driver} -> {info.mode_suggested}")
    run("photo_tpkx", noqgis, photo, "tpkx")
    run("photo_cancel", noqgis, photo, "tpkx", cancel_after=5)
print("work folder:", R)
