#!/usr/bin/env python3
"""Copy original PNG/JPEG MBTiles directly into Esri Compact Cache V2 TPKX.

Usage: python mb2tpkx.py input.mbtiles [output.tpkx]
Requirement: Pillow (python -m pip install pillow).

Based on the exact TPKX structure tested successfully in ArcGIS Earth and ArcGIS Pro.
The imagery tiles themselves are never modified, resized, or recompressed.
Standard Web Mercator MBTiles use TMS tile-row indexing; output uses Esri XYZ rows.

v1.1 hardening (no change to tile copying or bundle structure):
- output is written to "<name>.tpkx.partial" and renamed only after full success;
  a failed or cancelled run removes the partial file
- the source path is escaped so names containing #, % or ? open correctly, read-only
- common problems are reported as one plain ERROR line instead of a traceback
- the database connection is closed explicitly

2.1 re-hardening (tile bytes and bundle structure unchanged from 2.0 / 1.1):
- disk space is checked before any work; a full drive stops at once with a plain message
- progress shows "bundle N of M (P%)"
- an existing TPKX: asks "Replace it? [y/N]" (a TPKX open in ArcGIS Earth is caught before building)
- an empty tile record says the MBTiles is damaged instead of showing a programmer error
"""
import contextlib
import copy
import datetime
import io
import json
import math
import pathlib
import shutil
import sqlite3
import struct
import sys
import tempfile
import urllib.parse
import uuid
import zipfile

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    sys.exit("ERROR: Pillow is not installed. Install it with: py -3 -m pip install Pillow")

VERSION = "2.1"   # 2.1 (2026-11-08) re-hardening: disk-space check, bundle progress, Replace question, damaged-tile message

# Metadata and bundle-header bytes extracted from the Bryce TPKX accepted by
# both ArcGIS Earth and ArcGIS Pro. Only content-dependent values change.
REFERENCE_ROOT = json.loads(r'''{"version":1.0,"tileBundlesPath":"./tile","spatialReference":{"wkid":102100,"latestWkid":3857},"tileInfo":{"spatialReference":{"wkid":102100,"latestWkid":3857},"origin":{"x":-20037508.342787,"y":20037508.342787},"rows":256,"cols":256,"dpi":96,"lods":[{"level":0,"resolution":156543.033928,"scale":591657527.591555},{"level":1,"resolution":78271.5169639999,"scale":295828763.795777},{"level":2,"resolution":39135.7584820001,"scale":147914381.897889},{"level":3,"resolution":19567.8792409999,"scale":73957190.948944},{"level":4,"resolution":9783.93962049996,"scale":36978595.474472},{"level":5,"resolution":4891.96981024998,"scale":18489297.737236},{"level":6,"resolution":2445.98490512499,"scale":9244648.868618},{"level":7,"resolution":1222.99245256249,"scale":4622324.434309},{"level":8,"resolution":611.49622628138,"scale":2311162.217155},{"level":9,"resolution":305.748113140558,"scale":1155581.108577},{"level":10,"resolution":152.874056570411,"scale":577790.554289},{"level":11,"resolution":76.4370282850732,"scale":288895.277144},{"level":12,"resolution":38.2185141425366,"scale":144447.638572},{"level":13,"resolution":19.1092570712683,"scale":72223.819286},{"level":14,"resolution":9.55462853563415,"scale":36111.909643},{"level":15,"resolution":4.77731426794937,"scale":18055.954822},{"level":16,"resolution":2.38865713397468,"scale":9027.977411},{"level":17,"resolution":1.19432856685505,"scale":4513.988705},{"level":18,"resolution":0.597164283559817,"scale":2256.994353},{"level":19,"resolution":0.298582141647617,"scale":1128.497176},{"level":20,"resolution":0.14929107082380833,"scale":564.248588},{"level":21,"resolution":0.07464553541190416,"scale":282.124294},{"level":22,"resolution":0.03732276770595208,"scale":141.062147},{"level":23,"resolution":0.01866138385297604,"scale":70.5310735}]},"storageInfo":{"packetSize":128,"storageFormat":"esriMapCacheStorageModeCompactV2"},"tileImageInfo":{"format":"MIXED","compressionQuality":75,"bandCount":1,"lercError":0},"name":"Bryceville","minScale":144447.638572,"maxScale":564.248588,"minLOD":12,"maxLOD":20,"units":"esriMeters","serviceDescription":"","resampling":true,"exportTilesAllowed":false,"initialExtent":{"xmin":-9121230.588607743,"ymin":3553977.85367441,"xmax":-9120886.621980567,"ymax":3554168.946245065,"spatialReference":{"wkid":102100,"latestWkid":3857}},"fullExtent":{"xmin":-9121230.588607743,"ymin":3553977.85367441,"xmax":-9120886.621980567,"ymax":3554168.946245065,"spatialReference":{"wkid":102100,"latestWkid":3857}}}''')
REFERENCE_ITEM = json.loads(r'''{"creator":"DiagnosticPackageBuild","name":"Bryceville","guid":"C17123FC-DFFA-4ED4-8B42-F1C991494F70","version":1.0,"created":0,"snippet":"","description":"","summary":"","title":"Bryceville","tags":"","type":"Compact Tile Package","typeKeywords":["Compact Tile Package","Tile Package","tpkx"],"thumbnail":"./thumbnail.png","extent":{"xmin":-81.93740847724834,"ymin":30.391534221363404,"xmax":-81.93431857246415,"ymax":30.3930149413159,"spatialReference":{"wkid":4326,"latestWkid":4326}}}''')
REFERENCE_HEADER = bytes.fromhex("0300000000000000a3000200050000000000000000000000e7000400000000002800000000000000140002000300000000000000004000000500000000000200")


def zip_entry(name, now, ntfs_extra):
    entry = zipfile.ZipInfo(name, now.timetuple()[:6])
    entry.compress_type = zipfile.ZIP_STORED
    entry.create_system = 0
    entry.create_version = 63
    entry.extract_version = 10
    entry.external_attr = 32
    entry.internal_attr = 0
    entry.extra = ntfs_extra
    return entry


def _gb(n):
    return f"{n / 1e9:.1f} GB" if n >= 1e9 else f"{n / 1e6:.0f} MB"


def convert(source, destination, replace=False):
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output paths cannot be the same.")
    if not source.is_file():
        raise FileNotFoundError(f"MBTiles file not found: {source}")
    if destination.exists():
        if not replace:
            raise FileExistsError(f"Output already exists: {destination} - delete or rename it and run again.")
        # Find out now (not after a long build) if ArcGIS Earth or another program holds the old file.
        try:
            with open(destination, "ab"):
                pass
        except OSError:
            raise PermissionError(f"Could not replace {destination.name} - it may be open in ArcGIS Earth "
                                  "or another program. Close it and run again.") from None

    # Build under a temporary name so a failed or cancelled run never leaves a
    # complete-looking but incomplete .tpkx behind.
    partial = destination.with_name(destination.name + ".partial")
    try:
        written, bundles = _build(source, partial)
        if destination.exists() and not replace:
            raise FileExistsError(f"Output appeared during conversion: {destination} - nothing was overwritten.")
        try:
            partial.replace(destination)
        except PermissionError:
            raise PermissionError(f"Could not replace {destination.name} - it may be open in ArcGIS Earth "
                                  "or another program. Close it and run again.") from None
    except BaseException:
        with contextlib.suppress(OSError):
            partial.unlink()
        raise
    print(f"SUCCESS: {written} original tiles, {bundles} bundles -> {destination}")


def _build(source, destination):
    # Escape the path so characters such as # % ? cannot truncate it or drop mode=ro.
    uri = "file:" + urllib.parse.quote(source.resolve().as_posix(), safe="/:") + "?mode=ro"
    with contextlib.closing(sqlite3.connect(uri, uri=True)) as db:
        details = dict(db.execute("SELECT name, value FROM metadata"))
        min_z, max_z, tile_count = db.execute(
            "SELECT MIN(zoom_level), MAX(zoom_level), COUNT(*) FROM tiles"
        ).fetchone()
        if not tile_count:
            raise ValueError("MBTiles has no imagery tiles.")
        levels = {entry["level"]: entry for entry in REFERENCE_ROOT["tileInfo"]["lods"]}
        if min_z not in levels or max_z not in levels:
            raise ValueError("Input zoom levels exceed the verified 0–23 Esri tiling scheme.")

        # A bundle corresponds to a 128 x 128 tile block in Esri XYZ coordinates.
        groups = db.execute("""
            SELECT zoom_level, ((1 << zoom_level) - 1 - tile_row) / 128 AS br,
                   tile_column / 128 AS bc
            FROM tiles
            GROUP BY zoom_level, br, bc
            ORDER BY zoom_level, br, bc
        """).fetchall()

        # 2.1: stop before any work when the output drive is too full. The TPKX holds every tile
        # unchanged plus a 4-byte length each and a 128 KB index per bundle.
        tile_bytes = db.execute("SELECT SUM(LENGTH(tile_data)) FROM tiles").fetchone()[0] or 0
        need = tile_bytes + 4 * tile_count + len(groups) * (64 + 131072) + 50_000_000
        folder = destination.resolve().parent
        free = shutil.disk_usage(folder).free
        if free < need:
            raise ValueError(f"Not enough disk space: the TPKX needs about {_gb(need)} in\n  {folder}\n"
                             f"and that drive has {_gb(free)} free. Free some space, or move the MBTiles "
                             "to a drive with more room and run again.")
        origin = REFERENCE_ROOT["tileInfo"]["origin"]
        resolution = {z: entry["resolution"] for z, entry in levels.items()}
        left = bottom = float("inf")
        right = top = float("-inf")
        # The display extent follows the finest-level source tiles, as in the
        # successfully tested Bryce and Color 2B packages.
        for z, row_group, col_group in groups:
            if z != max_z:
                continue
            row0, col0 = row_group * 128, col_group * 128
            tms_low = (1 << z) - 1 - (row0 + 127)
            tms_high = (1 << z) - 1 - row0
            minc, maxc, minr, maxr = db.execute("""
                SELECT MIN(tile_column), MAX(tile_column), MIN(tile_row), MAX(tile_row)
                FROM tiles WHERE zoom_level=? AND tile_column BETWEEN ? AND ?
                  AND tile_row BETWEEN ? AND ?
            """, (z, col0, col0 + 127, tms_low, tms_high)).fetchone()
            if minc is None:
                continue
            side = resolution[z] * 256
            left = min(left, origin["x"] + minc * side)
            right = max(right, origin["x"] + (maxc + 1) * side)
            bottom = min(bottom, origin["y"] - ((1 << z) - minr) * side)
            top = max(top, origin["y"] - ((1 << z) - 1 - maxr) * side)

        root = copy.deepcopy(REFERENCE_ROOT)
        item = copy.deepcopy(REFERENCE_ITEM)
        name = details.get("name") or source.stem
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

        # A real thumbnail uses the source image; source tiles stay byte-for-byte intact.
        first_tile = db.execute("SELECT tile_data FROM tiles ORDER BY zoom_level LIMIT 1").fetchone()[0]
        if not first_tile:
            raise ValueError("The first tile is empty - the MBTiles is damaged. Make it again in QGIS.")
        with Image.open(io.BytesIO(first_tile)) as picture:
            if picture.size != (256, 256) or picture.format not in ("PNG", "JPEG"):
                raise ValueError("Only 256 x 256 PNG/JPEG MBTiles are supported without changing imagery.")
            thumbnail = io.BytesIO()
            picture.convert("RGBA").resize((300, 200)).save(thumbnail, format="PNG")

        now = datetime.datetime.now(datetime.timezone.utc)
        file_time = int((now.timestamp() + 11644473600) * 10000000)
        ntfs_extra = struct.pack("<HHIHHQQQ", 0x000A, 32, 0, 1, 24,
                                 file_time, file_time, file_time)
        written = 0
        with zipfile.ZipFile(destination, "w", allowZip64=True) as package:
            package.writestr(zip_entry("iteminfo.json", now, ntfs_extra),
                             json.dumps(item, separators=(",", ":")).encode())
            package.writestr(zip_entry("root.json", now, ntfs_extra),
                             json.dumps(root, separators=(",", ":")).encode())
            package.writestr(zip_entry("thumbnail.png", now, ntfs_extra), thumbnail.getvalue())

            for number, (z, row_group, col_group) in enumerate(groups, 1):
                row0, col0 = row_group * 128, col_group * 128
                tms_low = (1 << z) - 1 - (row0 + 127)
                tms_high = (1 << z) - 1 - row0
                index = [4] * 16384  # Verified Esri missing-tile sentinel.
                largest_image = 0
                with tempfile.TemporaryFile(mode="w+b") as bundle:
                    bundle.write(b"\x00" * (64 + 131072))
                    rows = db.execute("""
                        SELECT tile_column, tile_row, tile_data FROM tiles
                        WHERE zoom_level=? AND tile_column BETWEEN ? AND ?
                          AND tile_row BETWEEN ? AND ?
                        ORDER BY tile_column, tile_row DESC
                    """, (z, col0, col0 + 127, tms_low, tms_high))
                    for column, tms_row, image in rows:
                        row = (1 << z) - 1 - tms_row
                        if not image:
                            raise ValueError(f"Tile z{z} ({column}, {tms_row}) is empty - the MBTiles is damaged. "
                                             "Make it again in QGIS.")
                        if not (0 <= column < (1 << z) and 0 <= row < (1 << z)):
                            raise ValueError(f"Invalid tile coordinate at z{z}: ({column}, {tms_row})")
                        if not (image.startswith(b"\x89PNG\r\n\x1a\n") or
                                image.startswith(b"\xff\xd8\xff")):
                            raise ValueError(f"Unsupported image format at z{z} ({column}, {tms_row})")
                        with Image.open(io.BytesIO(image)) as tile_image:
                            if tile_image.size != (256, 256) or tile_image.format not in ("PNG", "JPEG"):
                                raise ValueError(f"Unsupported tile dimensions or format at z{z} ({column}, {tms_row})")
                        # Esri's indexed image length occupies 24 bits.
                        if len(image) >= 1 << 24:
                            raise ValueError("An input tile exceeds the Compact V2 index capacity.")
                        slot = (row - row0) * 128 + column - col0
                        if index[slot] != 4:
                            raise ValueError(f"Duplicate tile: z{z}, x{column}, y{row}")
                        bundle.write(struct.pack("<I", len(image)))
                        offset = bundle.tell()
                        bundle.write(image)
                        index[slot] = len(image) << 40 | offset
                        largest_image = max(largest_image, len(image))
                        written += 1
                    bundle_length = bundle.tell()
                    header = bytearray(REFERENCE_HEADER)
                    struct.pack_into("<I", header, 8, max(131092, largest_image))
                    struct.pack_into("<Q", header, 24, bundle_length)
                    bundle.seek(0)
                    bundle.write(header)
                    bundle.write(struct.pack("<16384Q", *index))
                    bundle.seek(0)
                    filename = f"tile/L{z:02d}/R{row0:04x}C{col0:04x}.bundle"
                    entry = zip_entry(filename, now, ntfs_extra)
                    entry.file_size = bundle_length
                    with package.open(entry, "w") as member:
                        shutil.copyfileobj(bundle, member, length=1024 * 1024)
                print(f"bundle {number:,} of {len(groups):,} ({number * 100 // len(groups)}%) - z{z} {filename}", flush=True)
        if written != tile_count:
            raise ValueError(f"Tile count mismatch: source={tile_count}, written={written}")
    return written, len(groups)


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit("Usage: python mb2tpkx.py input.mbtiles [output.tpkx]")
    source = pathlib.Path(sys.argv[1])
    output = pathlib.Path(sys.argv[2]) if len(sys.argv) == 3 else source.with_suffix(".tpkx")
    print(f"mb2tpkx {VERSION}", flush=True)
    replace = False
    if output.exists() and source.is_file() and source.resolve() != output.resolve():
        try:
            answer = input(f"{output.name} already exists in\n  {output.resolve().parent}\nReplace it? [y/N]: ")
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            sys.exit("Not converted - the existing TPKX was kept.")
        replace = True
    try:
        convert(source, output, replace)
    except KeyboardInterrupt:
        sys.exit("CANCELLED: no output file was kept.")
    except (FileNotFoundError, FileExistsError, PermissionError, ValueError) as error:
        sys.exit(f"ERROR: {error}")
    except UnidentifiedImageError:
        sys.exit("ERROR: A tile is not a readable PNG/JPEG image. No output file was kept.")
    except sqlite3.Error as error:
        sys.exit(f"ERROR: Could not read {source.name} as an MBTiles database ({error}).")
    except OSError as error:
        sys.exit(f"ERROR: File problem - {error}. No output file was kept.")


if __name__ == "__main__":
    main()
