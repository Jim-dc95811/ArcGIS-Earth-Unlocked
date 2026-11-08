#!/usr/bin/env python3
"""MBTiles -> ArcGIS TPKX converter v0.3.0 for Picture World Maker (2026-11-05).

Writes the SAME package structure as mb2tpkx 1.1 (Jim-dc95811/QGIS-Mbtile-to-ArcGIS-Earth-TPKX),
whose output is proven in ArcGIS Earth and ArcGIS Pro: the root.json / iteminfo.json templates,
the Compact Cache V2 bundle header and missing-tile sentinel (4) were taken from a TPKX accepted by
both, and only content-dependent values change. Bundle bytes are identical to mb2tpkx output for the
same MBTiles (checked with tools/tpkx_compare.py on Jim's London demo: 11,821 tiles, 24 bundles).

What v0.1.0 did differently (all fixed here, see releases/v0.1.5_TEST_RELEASE_NOTES.md):
  bundle header record count 16384 / legacy field 16 / max record size (reference: 0 / 0 / 131092+),
  empty index slots 0 (reference: 4), root.json tileImageInfo PNG/JPEG without bandCount/lercError
  (reference: MIXED, 75, 1, 0), LODs recalculated (reference: Esri's published values),
  extent from metadata 'bounds' (reference: the finest-level tiles), iteminfo tags as a list,
  zip entries without the Windows/NTFS attributes, 200x133 grey thumbnail.

Standard library only. If Pillow happens to be installed, the thumbnail is made from the imagery
exactly as mb2tpkx does; otherwise a plain 300x200 thumbnail is used (cosmetic only).
Tile images are never modified, resized or recompressed. MBTiles TMS rows are flipped to Esri rows.

Usage: python MBTiles_to_TPKX_v0_3_0.py input.mbtiles [output.tpkx] [--keep-work]
       (no arguments = file pickers)
Picture World Maker's pipeline reads the 'Tiles ...' and 'Packaging ...' progress lines and the exit code.
"""
from __future__ import annotations

import argparse
import binascii
import contextlib
import copy
import datetime
import io
import json
import math
import shutil
import sqlite3
import struct
import sys
import tempfile
import time
import urllib.parse
import uuid
import zipfile
import zlib
from pathlib import Path

VERSION = "0.3.0"

# --- Reference values: copied verbatim from mb2tpkx 1.1 (proven in ArcGIS Earth and ArcGIS Pro) ---
REFERENCE_ROOT = json.loads(r'''{"version":1.0,"tileBundlesPath":"./tile","spatialReference":{"wkid":102100,"latestWkid":3857},"tileInfo":{"spatialReference":{"wkid":102100,"latestWkid":3857},"origin":{"x":-20037508.342787,"y":20037508.342787},"rows":256,"cols":256,"dpi":96,"lods":[{"level":0,"resolution":156543.033928,"scale":591657527.591555},{"level":1,"resolution":78271.5169639999,"scale":295828763.795777},{"level":2,"resolution":39135.7584820001,"scale":147914381.897889},{"level":3,"resolution":19567.8792409999,"scale":73957190.948944},{"level":4,"resolution":9783.93962049996,"scale":36978595.474472},{"level":5,"resolution":4891.96981024998,"scale":18489297.737236},{"level":6,"resolution":2445.98490512499,"scale":9244648.868618},{"level":7,"resolution":1222.99245256249,"scale":4622324.434309},{"level":8,"resolution":611.49622628138,"scale":2311162.217155},{"level":9,"resolution":305.748113140558,"scale":1155581.108577},{"level":10,"resolution":152.874056570411,"scale":577790.554289},{"level":11,"resolution":76.4370282850732,"scale":288895.277144},{"level":12,"resolution":38.2185141425366,"scale":144447.638572},{"level":13,"resolution":19.1092570712683,"scale":72223.819286},{"level":14,"resolution":9.55462853563415,"scale":36111.909643},{"level":15,"resolution":4.77731426794937,"scale":18055.954822},{"level":16,"resolution":2.38865713397468,"scale":9027.977411},{"level":17,"resolution":1.19432856685505,"scale":4513.988705},{"level":18,"resolution":0.597164283559817,"scale":2256.994353},{"level":19,"resolution":0.298582141647617,"scale":1128.497176},{"level":20,"resolution":0.14929107082380833,"scale":564.248588},{"level":21,"resolution":0.07464553541190416,"scale":282.124294},{"level":22,"resolution":0.03732276770595208,"scale":141.062147},{"level":23,"resolution":0.01866138385297604,"scale":70.5310735}]},"storageInfo":{"packetSize":128,"storageFormat":"esriMapCacheStorageModeCompactV2"},"tileImageInfo":{"format":"MIXED","compressionQuality":75,"bandCount":1,"lercError":0},"name":"Bryceville","minScale":144447.638572,"maxScale":564.248588,"minLOD":12,"maxLOD":20,"units":"esriMeters","serviceDescription":"","resampling":true,"exportTilesAllowed":false,"initialExtent":{"xmin":-9121230.588607743,"ymin":3553977.85367441,"xmax":-9120886.621980567,"ymax":3554168.946245065,"spatialReference":{"wkid":102100,"latestWkid":3857}},"fullExtent":{"xmin":-9121230.588607743,"ymin":3553977.85367441,"xmax":-9120886.621980567,"ymax":3554168.946245065,"spatialReference":{"wkid":102100,"latestWkid":3857}}}''')
REFERENCE_ITEM = json.loads(r'''{"creator":"DiagnosticPackageBuild","name":"Bryceville","guid":"C17123FC-DFFA-4ED4-8B42-F1C991494F70","version":1.0,"created":0,"snippet":"","description":"","summary":"","title":"Bryceville","tags":"","type":"Compact Tile Package","typeKeywords":["Compact Tile Package","Tile Package","tpkx"],"thumbnail":"./thumbnail.png","extent":{"xmin":-81.93740847724834,"ymin":30.391534221363404,"xmax":-81.93431857246415,"ymax":30.3930149413159,"spatialReference":{"wkid":4326,"latestWkid":4326}}}''')
REFERENCE_HEADER = bytes.fromhex("0300000000000000a3000200050000000000000000000000e7000400000000002800000000000000140002000300000000000000004000000500000000000200")
MISSING_TILE = 4          # Esri missing-tile index value (offset 4, length 0)
PACKET = 128              # tiles per bundle side


class ConversionError(RuntimeError):
    pass


def fmt_int(n: int) -> str:
    return f"{n:,}"


def format_elapsed(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def image_size(data: bytes):
    """(format, width, height) of a PNG or JPEG tile using only the standard library."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return "PNG", w, h
    if data.startswith(b"\xff\xd8\xff"):
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7 or marker == 0xFF:
                i += 1 if marker == 0xFF else 2
                continue
            length = struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return "JPEG", w, h
            i += 2 + length
        return "JPEG", None, None
    return None, None, None


def check_tile(data: bytes, where: str) -> None:
    fmt, w, h = image_size(data)
    if fmt is None:
        raise ConversionError(f"Unsupported image format at {where} - only PNG and JPEG tiles are supported.")
    if (w, h) != (256, 256):
        raise ConversionError(f"Tile at {where} is {w}x{h}; only 256 x 256 tiles are supported without changing imagery.")


def _png(width: int, height: int, rgb=(0x34, 0x34, 0x34)) -> bytes:
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", binascii.crc32(kind + body) & 0xFFFFFFFF)
    raw = (b"\x00" + bytes(rgb) * width) * height
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def make_thumbnail(first_tile: bytes) -> bytes:
    """Same 300x200 thumbnail as mb2tpkx when Pillow is available; a plain one otherwise."""
    try:
        from PIL import Image
    except Exception:
        return _png(300, 200)
    try:
        with Image.open(io.BytesIO(first_tile)) as picture:
            out = io.BytesIO()
            picture.convert("RGBA").resize((300, 200)).save(out, format="PNG")
            return out.getvalue()
    except Exception:
        return _png(300, 200)


def zip_entry(name: str, now, ntfs_extra: bytes) -> zipfile.ZipInfo:
    entry = zipfile.ZipInfo(name, now.timetuple()[:6])
    entry.compress_type = zipfile.ZIP_STORED
    entry.create_system = 0
    entry.create_version = 63
    entry.extract_version = 10
    entry.external_attr = 32
    entry.internal_attr = 0
    entry.extra = ntfs_extra
    return entry


def _build(source: Path, destination: Path) -> tuple[int, int]:
    uri = "file:" + urllib.parse.quote(source.resolve().as_posix(), safe="/:") + "?mode=ro"
    with contextlib.closing(sqlite3.connect(uri, uri=True)) as db:
        try:
            details = dict(db.execute("SELECT name, value FROM metadata"))
        except sqlite3.Error:
            details = {}
        declared = str(details.get("format", "")).strip().lower()
        if declared in {"pbf", "mvt", "webp", "image/webp"}:
            raise ConversionError(f"Unsupported MBTiles tile format '{declared}'. Only raster PNG/JPEG tiles are supported.")
        min_z, max_z, tile_count = db.execute(
            "SELECT MIN(zoom_level), MAX(zoom_level), COUNT(*) FROM tiles").fetchone()
        if not tile_count:
            raise ConversionError("MBTiles has no imagery tiles.")
        levels = {entry["level"]: entry for entry in REFERENCE_ROOT["tileInfo"]["lods"]}
        if min_z not in levels or max_z not in levels:
            raise ConversionError("Input zoom levels exceed the verified 0-23 Esri tiling scheme.")

        name = str(details.get("name") or "").strip() or source.stem
        print(f"Name  : {name}")
        print(f"Zooms : {min_z}-{max_z}")
        print(f"Tiles : {fmt_int(tile_count)}")
        print(flush=True)

        groups = db.execute("""
            SELECT zoom_level, ((1 << zoom_level) - 1 - tile_row) / 128 AS br,
                   tile_column / 128 AS bc
            FROM tiles GROUP BY zoom_level, br, bc ORDER BY zoom_level, br, bc
        """).fetchall()
        origin = REFERENCE_ROOT["tileInfo"]["origin"]
        resolution = {z: entry["resolution"] for z, entry in levels.items()}
        left = bottom = float("inf")
        right = top = float("-inf")
        # Display extent follows the finest-level source tiles (as in the proven packages).
        for z, row_group, col_group in groups:
            if z != max_z:
                continue
            row0, col0 = row_group * PACKET, col_group * PACKET
            tms_low = (1 << z) - 1 - (row0 + PACKET - 1)
            tms_high = (1 << z) - 1 - row0
            minc, maxc, minr, maxr = db.execute("""
                SELECT MIN(tile_column), MAX(tile_column), MIN(tile_row), MAX(tile_row)
                FROM tiles WHERE zoom_level=? AND tile_column BETWEEN ? AND ? AND tile_row BETWEEN ? AND ?
            """, (z, col0, col0 + PACKET - 1, tms_low, tms_high)).fetchone()
            if minc is None:
                continue
            side = resolution[z] * 256
            left = min(left, origin["x"] + minc * side)
            right = max(right, origin["x"] + (maxc + 1) * side)
            bottom = min(bottom, origin["y"] - ((1 << z) - minr) * side)
            top = max(top, origin["y"] - ((1 << z) - 1 - maxr) * side)

        root = copy.deepcopy(REFERENCE_ROOT)
        item = copy.deepcopy(REFERENCE_ITEM)
        root["name"] = item["name"] = item["title"] = name
        root["minLOD"], root["maxLOD"] = min_z, max_z
        root["minScale"], root["maxScale"] = levels[min_z]["scale"], levels[max_z]["scale"]
        extent = {"xmin": left, "ymin": bottom, "xmax": right, "ymax": top,
                  "spatialReference": copy.deepcopy(root["spatialReference"])}
        root["initialExtent"] = copy.deepcopy(extent)
        root["fullExtent"] = extent
        item["guid"] = str(uuid.uuid4()).upper()
        item["creator"] = "MBTilesDirectConverter"
        radius = 6378137
        item["extent"] = {
            "xmin": left * 180 / (math.pi * radius),
            "ymin": (2 * math.atan(math.exp(bottom / radius)) - math.pi / 2) * 180 / math.pi,
            "xmax": right * 180 / (math.pi * radius),
            "ymax": (2 * math.atan(math.exp(top / radius)) - math.pi / 2) * 180 / math.pi,
            "spatialReference": copy.deepcopy(item["extent"]["spatialReference"]),
        }

        first_tile = bytes(db.execute("SELECT tile_data FROM tiles ORDER BY zoom_level LIMIT 1").fetchone()[0])
        check_tile(first_tile, "the first tile")
        thumbnail = make_thumbnail(first_tile)

        now = datetime.datetime.now(datetime.timezone.utc)
        file_time = int((now.timestamp() + 11644473600) * 10000000)
        ntfs_extra = struct.pack("<HHIHHQQQ", 0x000A, 32, 0, 1, 24, file_time, file_time, file_time)
        written = 0
        started = time.monotonic()
        print(f"Packaging {fmt_int(len(groups) + 3)} files into {destination.name.replace('.partial', '')} ...", flush=True)
        with zipfile.ZipFile(destination, "w", allowZip64=True) as package:
            package.writestr(zip_entry("iteminfo.json", now, ntfs_extra), json.dumps(item, separators=(",", ":")).encode())
            package.writestr(zip_entry("root.json", now, ntfs_extra), json.dumps(root, separators=(",", ":")).encode())
            package.writestr(zip_entry("thumbnail.png", now, ntfs_extra), thumbnail)
            for number, (z, row_group, col_group) in enumerate(groups, 1):
                row0, col0 = row_group * PACKET, col_group * PACKET
                tms_low = (1 << z) - 1 - (row0 + PACKET - 1)
                tms_high = (1 << z) - 1 - row0
                index = [MISSING_TILE] * (PACKET * PACKET)
                largest_image = 0
                with tempfile.TemporaryFile(mode="w+b") as bundle:
                    bundle.write(b"\x00" * (64 + 131072))
                    rows = db.execute("""
                        SELECT tile_column, tile_row, tile_data FROM tiles
                        WHERE zoom_level=? AND tile_column BETWEEN ? AND ? AND tile_row BETWEEN ? AND ?
                        ORDER BY tile_column, tile_row DESC
                    """, (z, col0, col0 + PACKET - 1, tms_low, tms_high))
                    for column, tms_row, image in rows:
                        image = bytes(image)
                        row = (1 << z) - 1 - tms_row
                        where = f"z{z} x{column} y{row}"
                        if not (0 <= column < (1 << z) and 0 <= row < (1 << z)):
                            raise ConversionError(f"Invalid tile coordinate at {where}")
                        check_tile(image, where)
                        if len(image) >= 1 << 24:
                            raise ConversionError(f"Tile at {where} exceeds the Compact V2 index capacity.")
                        slot = (row - row0) * PACKET + column - col0
                        if index[slot] != MISSING_TILE:
                            raise ConversionError(f"Duplicate tile: {where}")
                        bundle.write(struct.pack("<I", len(image)))
                        offset = bundle.tell()
                        bundle.write(image)
                        index[slot] = len(image) << 40 | offset
                        largest_image = max(largest_image, len(image))
                        written += 1
                        if written == 1 or written % 5000 == 0 or written == tile_count:
                            pct = written / tile_count * 100.0
                            print(f"Tiles {fmt_int(written)} / {fmt_int(tile_count)} ({pct:6.2f}%)  "
                                  f"Bundles {fmt_int(number)}  Elapsed {format_elapsed(time.monotonic() - started)}",
                                  flush=True)
                    bundle_length = bundle.tell()
                    header = bytearray(REFERENCE_HEADER)
                    struct.pack_into("<I", header, 8, max(131092, largest_image))
                    struct.pack_into("<Q", header, 24, bundle_length)
                    bundle.seek(0)
                    bundle.write(header)
                    bundle.write(struct.pack(f"<{PACKET * PACKET}Q", *index))
                    bundle.seek(0)
                    entry = zip_entry(f"tile/L{z:02d}/R{row0:04x}C{col0:04x}.bundle", now, ntfs_extra)
                    entry.file_size = bundle_length
                    with package.open(entry, "w") as member:
                        shutil.copyfileobj(bundle, member, length=1024 * 1024)
        if written != tile_count:
            raise ConversionError(f"Tile count mismatch: source={tile_count}, written={written}")
    with zipfile.ZipFile(destination) as check:
        bad = check.testzip()
        if bad is not None:
            raise ConversionError(f"TPKX ZIP verification failed at entry: {bad}")
    return written, len(groups)


def convert_mbtiles_to_tpkx(input_path: Path, output_path: Path, keep_work: bool = False) -> None:
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    if not input_path.is_file():
        raise ConversionError(f"Input file not found: {input_path}")
    if output_path.suffix.lower() != ".tpkx":
        output_path = output_path.with_suffix(".tpkx")
    if input_path == output_path:
        raise ConversionError("Input and output paths must be different.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"MBTiles_to_TPKX {VERSION} (mb2tpkx 1.1 structure)")
    print(f"Input : {input_path}")
    print(f"Output: {output_path}")
    if keep_work:
        print("Note  : --keep-work has nothing to keep (bundles are built in temporary files).")
    started = time.monotonic()
    partial = output_path.with_name(output_path.name + ".partial")
    try:
        written, bundles = _build(input_path, partial)
        partial.replace(output_path)
    except BaseException:
        with contextlib.suppress(OSError):
            partial.unlink()
        raise
    print()
    print("CONVERSION COMPLETE")
    print(f"Tiles   : {fmt_int(written)}")
    print(f"Bundles : {fmt_int(bundles)}")
    print(f"Output  : {output_path}")
    print(f"Bytes   : {fmt_int(output_path.stat().st_size)}")
    print(f"Elapsed : {format_elapsed(time.monotonic() - started)}")


def choose_paths_gui():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None, None
    root = tk.Tk()
    root.withdraw()
    try:
        name = filedialog.askopenfilename(title="Select MBTiles file",
                                          filetypes=[("MBTiles", "*.mbtiles"), ("All files", "*.*")])
        if not name:
            return None, None
        out = filedialog.asksaveasfilename(title="Save ArcGIS Tile Package", defaultextension=".tpkx",
                                           initialfile=Path(name).stem + ".tpkx",
                                           filetypes=[("ArcGIS Compact Tile Package", "*.tpkx")])
        return (Path(name), Path(out)) if out else (None, None)
    finally:
        root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert raster Web Mercator MBTiles to ArcGIS TPKX (Compact Cache V2).")
    parser.add_argument("input", nargs="?", help="Input .mbtiles file")
    parser.add_argument("output", nargs="?", help="Output .tpkx file")
    parser.add_argument("--keep-work", action="store_true", help="Accepted for compatibility; nothing to keep.")
    args = parser.parse_args()
    if args.input:
        source = Path(args.input)
        output = Path(args.output) if args.output else source.with_suffix(".tpkx")
    else:
        source, output = choose_paths_gui()
        if source is None:
            print("Cancelled.")
            return 1
    try:
        convert_mbtiles_to_tpkx(source, output, keep_work=args.keep_work)
    except ConversionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Cancelled by user. No output file was kept.", file=sys.stderr)
        return 130
    except sqlite3.Error as exc:
        print(f"ERROR: Could not read the input as an MBTiles database ({exc}).", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"UNEXPECTED ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
