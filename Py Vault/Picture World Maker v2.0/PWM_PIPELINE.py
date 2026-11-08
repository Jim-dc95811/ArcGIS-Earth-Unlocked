#!/usr/bin/env python3
from __future__ import annotations

import configparser
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import queue
import threading
import time
import zipfile
from dataclasses import dataclass, replace
from typing import Callable, Optional

WEB_MERCATOR_HALF = 20037508.342789244
WEB_MERCATOR_RES_Z0 = 156543.03392804097
TPKX_MAX_ZOOM = 23      # Esri's published Web Mercator tiling scheme (and the TPKX converter) stops at level 23
ProgressCallback = Callable[[str, str, Optional[float]], None]

class PictureWorldError(RuntimeError):
    pass

class BuildCancelled(PictureWorldError):
    pass

@dataclass(frozen=True)
class Config:
    base_dir: Path
    default_min_zoom: int
    default_max_zoom: int
    synthetic_meters_per_pixel: float
    synthetic_anchor_lon: float
    synthetic_anchor_lat: float
    warning_tile_count: int
    photo_tiles: str = "mixed"
    photo_jpeg_quality: int = 85

@dataclass(frozen=True)
class RasterInfo:
    path: Path
    width: int
    height: int
    driver: str
    has_crs: bool
    has_geotransform: bool
    mode_suggested: str

@dataclass(frozen=True)
class BuildResult:
    input_file: Path
    mode: str
    output_mode: str
    mbtiles_file: Optional[Path]
    tpkx_file: Optional[Path]
    tile_count: int
    min_zoom: int
    max_zoom: int
    bundle_count: int
    elapsed_seconds: float


def load_config(base_dir: Path) -> Config:
    path = base_dir / "Picture_World_Maker_Config.ini"
    cp = configparser.ConfigParser()
    if not path.is_file():
        raise PictureWorldError(f"Configuration file is missing: {path}")
    cp.read(path, encoding="utf-8")
    p = cp["PYRAMID"]
    ph = cp["PHOTO"] if cp.has_section("PHOTO") else {}
    return Config(
        base_dir=base_dir,
        default_min_zoom=p.getint("default_min_zoom", 0),
        default_max_zoom=p.getint("default_max_zoom", 18),
        synthetic_meters_per_pixel=p.getfloat("synthetic_meters_per_pixel", 1.0),
        synthetic_anchor_lon=p.getfloat("synthetic_anchor_lon", -80.0),
        synthetic_anchor_lat=p.getfloat("synthetic_anchor_lat", 30.0),
        warning_tile_count=p.getint("warning_tile_count", 100000),
        photo_tiles=str(ph.get("tiles", "mixed")).strip().lower(),
        photo_jpeg_quality=int(ph.get("jpeg_quality", 85)),
    )


def explorer_size(size: int) -> str:
    return f"{(max(0, int(size)) + 1023) // 1024:,} KB"


def _hidden_flags(new_group: bool = False):
    if os.name != "nt":
        return 0, None
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if new_group:
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    return flags, si


def terminate_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=10,
            )
            return
        except Exception:
            pass
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


GEOTIFF_TAGS = (33550, 33922, 34264, 34735)   # ModelPixelScale, ModelTiepoint, ModelTransformation, GeoKeyDirectory


def photo_mode_available() -> bool:
    """Picture World Maker needs Pillow (the launcher installs it)."""
    try:
        import PIL  # noqa: F401
        return True
    except Exception:
        return False


def inspect_raster_pillow(path: Path) -> RasterInfo:
    """Read a picture's size with Pillow. v0.2.3: every picture is built flat (parked on the ocean).
    A TIFF carrying GeoTIFF tags is flagged (has_crs) so the window can say ArcGIS Earth opens it directly."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    try:
        with Image.open(path) as im:
            width, height = im.size
            driver = im.format or "Raster"
            tags = getattr(im, "tag_v2", None)
            geo = bool(tags) and any(t in tags for t in GEOTIFF_TAGS)
    except Exception as exc:
        raise PictureWorldError(f"Could not read this picture: {exc}") from exc
    return RasterInfo(path, int(width), int(height), driver, geo, geo, "flat")


def inspect_raster(config: Config, path: Path) -> RasterInfo:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if not photo_mode_available():
        raise PictureWorldError("The Pillow helper is not installed. Start Picture World Maker with its .bat file - it installs Pillow.")
    return inspect_raster_pillow(path)


def web_mercator_from_lonlat(lon: float, lat: float) -> tuple[float, float]:
    """Convert WGS84 lon/lat to EPSG:3857 meters for synthetic parking."""
    lat = max(-85.05112878, min(85.05112878, float(lat)))
    x = WEB_MERCATOR_HALF * float(lon) / 180.0
    y = WEB_MERCATOR_HALF * math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / math.pi
    return x, y


def synthetic_bounds(
    width: int,
    height: int,
    meters_per_pixel: float = 1.0,
    center_x: float = 0.0,
    center_y: float = 0.0,
) -> tuple[float, float, float, float]:
    if width <= 0 or height <= 0 or meters_per_pixel <= 0:
        raise ValueError("Raster dimensions and synthetic scale must be positive.")
    half_w = width * meters_per_pixel / 2.0
    half_h = height * meters_per_pixel / 2.0
    return center_x - half_w, center_x + half_w, center_y - half_h, center_y + half_h


def synthetic_bounds_for_config(
    config: Config, width: int, height: int, meters_per_pixel: float | None = None
) -> tuple[float, float, float, float]:
    mpp = config.synthetic_meters_per_pixel if meters_per_pixel is None else float(meters_per_pixel)
    cx, cy = web_mercator_from_lonlat(config.synthetic_anchor_lon, config.synthetic_anchor_lat)
    return synthetic_bounds(width, height, mpp, cx, cy)


# v0.2.4 (Jim, 2026-11-06: 'multiple places on the ocean ... each could have its own grid box'):
# 20 numbered World spots, each the centre of its own 1-degree box of open Atlantic east of Florida.
# Spot 1 = the configured anchor (default 30 N 80 W, where every earlier picture landed, so old
# files keep their place). Spots 2-10 step 1 degree east along the same latitude; spots 11-20 are
# the row 1 degree north. Default grid: 30-31 N, 80-71 W - all open ocean, well clear of the coast,
# the Bahamas (south of 27.3 N) and Bermuda (32.3 N 64.8 W).
WORLD_SPOT_COUNT = 20
WORLD_SPOTS_PER_ROW = 10


def world_spots(config: Config) -> list[tuple[int, float, float]]:
    """[(spot number, lat, lon)] - spot 1 is the configured anchor."""
    spots = []
    for n in range(1, WORLD_SPOT_COUNT + 1):
        row, col = divmod(n - 1, WORLD_SPOTS_PER_ROW)
        spots.append((n, config.synthetic_anchor_lat + row, config.synthetic_anchor_lon + col))
    return spots


def world_spot_label(lat: float, lon: float) -> str:
    return f"{abs(lat):.1f}{'N' if lat >= 0 else 'S'} {abs(lon):.1f}{'W' if lon < 0 else 'E'}"


def config_for_spot(config: Config, spot: int) -> Config:
    """The same settings with the picture parked at World spot <spot> (1-20)."""
    for n, lat, lon in world_spots(config):
        if n == int(spot):
            return replace(config, synthetic_anchor_lat=lat, synthetic_anchor_lon=lon)
    raise ValueError(f"World spot must be 1 to {WORLD_SPOT_COUNT}.")


def world_spot_box_m(config: Config, spot: int) -> tuple[float, float]:
    """Size of a spot's own 1-degree box (centred on the spot) in the same Web Mercator metres the
    picture is placed in (picture width x metres-per-pixel), east-west and north-south."""
    lat, lon = {n: (la, lo) for n, la, lo in world_spots(config)}[int(spot)]
    x0, y0 = web_mercator_from_lonlat(lon - 0.5, lat - 0.5)
    x1, y1 = web_mercator_from_lonlat(lon + 0.5, lat + 0.5)
    return x1 - x0, y1 - y0


def recommended_max_zoom(meters_per_pixel: float) -> int:
    if meters_per_pixel <= 0:
        return 18
    return max(0, min(25, int(math.ceil(math.log2(WEB_MERCATOR_RES_Z0 / meters_per_pixel)))))


def _tile_xy_from_meters(x: float, y: float, z: int) -> tuple[int, int]:
    n = 1 << z
    world = WEB_MERCATOR_HALF * 2.0
    tx = int(math.floor(((x + WEB_MERCATOR_HALF) / world) * n))
    ty = int(math.floor(((WEB_MERCATOR_HALF - y) / world) * n))
    return max(0, min(n - 1, tx)), max(0, min(n - 1, ty))


def estimate_synthetic_tiles(bounds: tuple[float, float, float, float], zmin: int, zmax: int) -> int:
    xmin, xmax, ymin, ymax = bounds
    total = 0
    eps = 1e-9
    for z in range(zmin, zmax + 1):
        x0, y0 = _tile_xy_from_meters(xmin, ymax, z)
        x1, y1 = _tile_xy_from_meters(xmax - eps, ymin + eps, z)
        total += (x1 - x0 + 1) * (y1 - y0 + 1)
    return total


def check_zoom_range(zoom_min: int, zoom_max: int, output_mode: str) -> None:
    """v0.1.6: reject impossible zoom choices before any long work starts."""
    if not (0 <= zoom_min <= zoom_max <= 25):
        raise ValueError("Zooms must satisfy 0 <= minimum <= maximum <= 25.")
    if output_mode.lower() in {"tpkx", "both"} and zoom_max > TPKX_MAX_ZOOM:
        raise ValueError(
            f"TPKX supports zoom levels up to {TPKX_MAX_ZOOM} (Esri's tiling scheme). "
            f"Set Max zoom to {TPKX_MAX_ZOOM} or less, or choose MBTiles only.")


def _line_pump(stream) -> "queue.Queue[str | None]":
    """v0.1.6: read a child's output on a helper thread so Cancel is noticed within 0.2 s
    even while the child prints nothing for a long time."""
    q: "queue.Queue[str | None]" = queue.Queue()
    def pump():
        try:
            for line in iter(stream.readline, ""):
                q.put(line)
        except Exception:
            pass
        finally:
            try:
                stream.close()   # the reader owns the pipe; the caller never blocks on closing it
            except Exception:
                pass
            q.put(None)
    threading.Thread(target=pump, daemon=True).start()
    return q


def _lines_until_done(proc: subprocess.Popen, cancel_event):
    """Yield the child's output lines; stop it at once if the operator cancels."""
    assert proc.stdout is not None
    q = _line_pump(proc.stdout)
    while True:
        if cancel_event is not None and cancel_event.is_set():
            terminate_tree(proc)
            raise BuildCancelled("Build cancelled by operator.")
        try:
            line = q.get(timeout=0.2)
        except queue.Empty:
            continue
        if line is None:
            return
        yield line


def inspect_mbtiles(path: Path) -> dict:
    uri = path.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        cols = {row[1] for row in con.execute("PRAGMA table_info(tiles)")}
        if not {"zoom_level", "tile_column", "tile_row", "tile_data"}.issubset(cols):
            raise PictureWorldError("MBTiles does not expose the standard raster tiles table.")
        row = con.execute("SELECT MIN(zoom_level), MAX(zoom_level), COUNT(*) FROM tiles").fetchone()
        if not row or row[0] is None or int(row[2]) <= 0:
            raise PictureWorldError("MBTiles contains no tiles.")
        md = dict(con.execute("SELECT name,value FROM metadata"))
        fmt = (md.get("format") or "").lower()
        if fmt not in {"png", "jpg", "jpeg"}:
            raise PictureWorldError(f"Unexpected raster tile format: {fmt!r}")
        return {"min_zoom": int(row[0]), "max_zoom": int(row[1]), "tile_count": int(row[2]), "metadata": md}
    finally:
        con.close()


def inspect_tpkx(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size <= 0:
        raise PictureWorldError("TPKX output is missing or empty.")
    with zipfile.ZipFile(path, "r") as zf:
        bad = zf.testzip()
        if bad:
            raise PictureWorldError(f"TPKX ZIP verification failed at {bad}")
        names = set(zf.namelist())
        for required in {"root.json", "iteminfo.json", "thumbnail.png"}:
            if required not in names:
                raise PictureWorldError(f"TPKX is missing {required}")
        bundles = [n for n in names if n.lower().endswith(".bundle")]
        if not bundles:
            raise PictureWorldError("TPKX contains no Compact Cache V2 bundles.")
        root = json.loads(zf.read("root.json").decode("utf-8"))
    if (root.get("storageInfo") or {}).get("storageFormat") != "esriMapCacheStorageModeCompactV2":
        raise PictureWorldError("TPKX does not identify Compact Cache V2 storage.")
    return {"bundle_count": len(bundles), "min_zoom": int(root.get("minLOD", -1)), "max_zoom": int(root.get("maxLOD", -1))}


def _console_python() -> str:
    exe = Path(sys.executable)
    if exe.name.lower() in {"pythonw.exe", "pythonw"}:
        c = exe.with_name("python.exe" if exe.suffix.lower() == ".exe" else "python")
        if c.is_file():
            return str(c)
    return str(exe)


def _run_converter(converter: Path, mbtiles: Path, tpkx: Path, emit, cancel_event):
    flags, si = _hidden_flags(new_group=True)
    proc = subprocess.Popen(
        [_console_python(), "-u", str(converter), str(mbtiles), str(tpkx)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", bufsize=1,
        creationflags=flags, startupinfo=si, cwd=str(converter.parent),
    )
    tail = []
    try:
        for raw in _lines_until_done(proc, cancel_event):
            line = raw.rstrip()
            if line:
                tail.append(line); tail = tail[-30:]
                if line.startswith("Tiles "):
                    emit("convert", "TPKX conversion — " + line, None)
                elif line.startswith("Packaging "):
                    emit("package", line, None)
        rc = proc.wait()
    finally:
        if proc.poll() is None:
            terminate_tree(proc)
    if rc != 0:
        raise PictureWorldError("TPKX converter failed.\n\n" + "\n".join(tail[-15:]))


def _publish(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise FileExistsError(f"Output already exists: {dst}")
    partial = dst.with_name("." + dst.name + ".__publishing")
    if partial.exists():
        partial.unlink()
    shutil.copy2(src, partial)
    partial.replace(dst)


def build(
    config: Config,
    input_file: Path,
    raster_mode: str,
    output_mode: str,
    output_dir: Path,
    output_stem: str,
    zoom_min: int,
    zoom_max: int,
    meters_per_pixel: float = 1.0,
    progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
) -> BuildResult:
    input_file = Path(input_file).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    if not input_file.is_file():
        raise FileNotFoundError(input_file)
    check_zoom_range(zoom_min, zoom_max, output_mode)
    output_mode = output_mode.lower()
    if output_mode not in {"mbtiles", "tpkx", "both"}:
        raise ValueError("Output mode must be MBTiles, TPKX, or Both.")
    output_stem = re.sub(r'[<>:"/\\|?*]+', "_", output_stem.strip()).strip(" .") or input_file.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    final_mb = output_dir / f"{output_stem}.mbtiles"
    final_tpkx = output_dir / f"{output_stem}.tpkx"
    if output_mode in {"mbtiles", "both"} and final_mb.exists():
        raise FileExistsError(final_mb)
    if output_mode in {"tpkx", "both"} and final_tpkx.exists():
        raise FileExistsError(final_tpkx)

    def emit(stage, msg, frac=None):
        if progress: progress(stage, msg, frac)

    info = inspect_raster(config, input_file)
    if raster_mode.lower() not in {"auto", "flat"}:
        raise ValueError("Picture World Maker builds pictures only (Auto / Flat).")
    mode = "flat"

    work = Path(tempfile.mkdtemp(prefix="Picture_World_"))
    started = time.monotonic()
    temp_mb = work / "raster_pyramid.mbtiles"
    temp_tpkx = work / "raster_pyramid.tpkx"
    converter = config.base_dir / "MBTiles_to_TPKX_v0_3_0.py"
    try:
        from PWM_PHOTO_TILER import build_photo_mbtiles, Cancelled as PhotoCancelled, PhotoTilerError
        bounds = synthetic_bounds_for_config(config, info.width, info.height, meters_per_pixel)
        try:
            build_photo_mbtiles(input_file, temp_mb, bounds, zoom_min, zoom_max, name=output_stem,
                                jpeg=config.photo_tiles != "png", quality=config.photo_jpeg_quality,
                                emit=emit, cancel_event=cancel_event)
        except PhotoCancelled as exc:
            raise BuildCancelled(str(exc)) from exc
        except PhotoTilerError as exc:
            raise PictureWorldError(str(exc)) from exc
        except MemoryError as exc:
            raise PictureWorldError("Not enough memory to open this picture. Close other programs and try again, "
                                    "or use a smaller picture.") from exc
        if not temp_mb.is_file():
            raise PictureWorldError("The pyramid stage did not create the MBTiles output.")
        emit("verify_mb", "Verifying MBTiles pyramid...", 0.90)
        mb_info = inspect_mbtiles(temp_mb)

        published_mb = None
        published_tpkx = None
        bundle_count = 0
        if output_mode in {"mbtiles", "both"}:
            emit("publish_mb", "Publishing verified MBTiles...", 0.93)
            _publish(temp_mb, final_mb)
            inspect_mbtiles(final_mb)
            published_mb = final_mb

        if output_mode in {"tpkx", "both"}:
            if not converter.is_file():
                raise PictureWorldError(f"Frozen TPKX converter is missing: {converter}")
            emit("convert", "Converting raster pyramid to native TPKX...", 0.94)
            _run_converter(converter, temp_mb, temp_tpkx, emit, cancel_event)
            emit("verify_tpkx", "Verifying Compact Cache V2 TPKX...", 0.98)
            tinfo = inspect_tpkx(temp_tpkx)
            bundle_count = int(tinfo["bundle_count"])
            _publish(temp_tpkx, final_tpkx)
            inspect_tpkx(final_tpkx)
            published_tpkx = final_tpkx

        elapsed = time.monotonic() - started
        emit("complete", "COMPLETE — pyramid products verified and published.", 1.0)
        return BuildResult(
            input_file=input_file, mode=mode, output_mode=output_mode,
            mbtiles_file=published_mb, tpkx_file=published_tpkx,
            tile_count=int(mb_info["tile_count"]), min_zoom=int(mb_info["min_zoom"]),
            max_zoom=int(mb_info["max_zoom"]), bundle_count=bundle_count,
            elapsed_seconds=elapsed,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)
