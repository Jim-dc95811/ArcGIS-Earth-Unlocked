"""Master 4 Grid Maker 2.0 (= v3.1; 2.0 Reference (2026-11-08): the whole ArcGIS Earth Unlocked family moved to 2.0 as one reference point)

v3.1 hardening (grid geometry, cell numbering, georeferencing, filenames and
demo tiles unchanged from v3):
- the Cell 55 demo TPKX is built as "<name>.tpkx.partial" and renamed only on
  success; a failed or cancelled build removes the partial file
- whole degrees typed as decimals or with leading zeros (82.0w, 082w) are named
  the same as 82w instead of crashing or producing a second naming
- an input mistake shows the error and asks again; a blank entry quits;
  Ctrl+C prints "Cancelled." instead of a traceback
- the TXT and TIF are written under temporary names and swapped in together,
  with a plain message if a file is locked by another program
"""
import contextlib
import copy
import datetime
import io
import json
import math
import os
import re
import shutil
import struct
import tempfile
import uuid
import zipfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, TiffImagePlugin
except ImportError:
    raise SystemExit(
        "Pillow is required. Install it with: py -3 -m pip install Pillow"
    )

VERSION = "2.0"   # program = v3.1, only this text changed
EPSG = 3857
EARTH_RADIUS = 6378137.0
OUTPUT_DIR = Path(r"C:\downloads")
IMAGE_SIZE = 5000
WEB_MERCATOR_MAX_LAT = 85.05112878

DEMO_CELL = 55
DEMO_MIN_ZOOM = 10
DEMO_MAX_ZOOM = 20
DEMO_COLORS = {
    10: (120, 55, 170),
    11: (70, 80, 190),
    12: (45, 145, 200),
    13: (45, 165, 120),
    14: (220, 55, 55),
    15: (240, 130, 40),
    16: (235, 210, 45),
    17: (70, 170, 75),
    18: (50, 160, 210),
    19: (70, 90, 210),
    20: (150, 70, 190),
}

# Compact Cache V2 metadata/header values are the same verified structure used
# by this project's MBTiles -> TPKX converter. Only demo-specific values change.
REFERENCE_ROOT = json.loads(r'''{"version":1.0,"tileBundlesPath":"./tile","spatialReference":{"wkid":102100,"latestWkid":3857},"tileInfo":{"spatialReference":{"wkid":102100,"latestWkid":3857},"origin":{"x":-20037508.342787,"y":20037508.342787},"rows":256,"cols":256,"dpi":96,"lods":[{"level":0,"resolution":156543.033928,"scale":591657527.591555},{"level":1,"resolution":78271.5169639999,"scale":295828763.795777},{"level":2,"resolution":39135.7584820001,"scale":147914381.897889},{"level":3,"resolution":19567.8792409999,"scale":73957190.948944},{"level":4,"resolution":9783.93962049996,"scale":36978595.474472},{"level":5,"resolution":4891.96981024998,"scale":18489297.737236},{"level":6,"resolution":2445.98490512499,"scale":9244648.868618},{"level":7,"resolution":1222.99245256249,"scale":4622324.434309},{"level":8,"resolution":611.49622628138,"scale":2311162.217155},{"level":9,"resolution":305.748113140558,"scale":1155581.108577},{"level":10,"resolution":152.874056570411,"scale":577790.554289},{"level":11,"resolution":76.4370282850732,"scale":288895.277144},{"level":12,"resolution":38.2185141425366,"scale":144447.638572},{"level":13,"resolution":19.1092570712683,"scale":72223.819286},{"level":14,"resolution":9.55462853563415,"scale":36111.909643},{"level":15,"resolution":4.77731426794937,"scale":18055.954822},{"level":16,"resolution":2.38865713397468,"scale":9027.977411},{"level":17,"resolution":1.19432856685505,"scale":4513.988705},{"level":18,"resolution":0.597164283559817,"scale":2256.994353},{"level":19,"resolution":0.298582141647617,"scale":1128.497176},{"level":20,"resolution":0.14929107082380833,"scale":564.248588},{"level":21,"resolution":0.07464553541190416,"scale":282.124294},{"level":22,"resolution":0.03732276770595208,"scale":141.062147},{"level":23,"resolution":0.01866138385297604,"scale":70.5310735}]},"storageInfo":{"packetSize":128,"storageFormat":"esriMapCacheStorageModeCompactV2"},"tileImageInfo":{"format":"MIXED","compressionQuality":75,"bandCount":1,"lercError":0},"name":"Zoom Demo","minScale":36111.909643,"maxScale":564.248588,"minLOD":14,"maxLOD":20,"units":"esriMeters","serviceDescription":"","resampling":true,"exportTilesAllowed":false,"initialExtent":{"xmin":0,"ymin":0,"xmax":0,"ymax":0,"spatialReference":{"wkid":102100,"latestWkid":3857}},"fullExtent":{"xmin":0,"ymin":0,"xmax":0,"ymax":0,"spatialReference":{"wkid":102100,"latestWkid":3857}}}''')
REFERENCE_ITEM = json.loads(r'''{"creator":"Master4GridMaker","name":"Cell 55 Zoom Demo","guid":"00000000-0000-0000-0000-000000000000","version":1.0,"created":0,"snippet":"","description":"Synthetic colored zoom-level demonstration for Master 4 cell 55.","summary":"","title":"Cell 55 Zoom Demo","tags":"","type":"Compact Tile Package","typeKeywords":["Compact Tile Package","Tile Package","tpkx"],"thumbnail":"./thumbnail.png","extent":{"xmin":0,"ymin":0,"xmax":0,"ymax":0,"spatialReference":{"wkid":4326,"latestWkid":4326}}}''')
REFERENCE_HEADER = bytes.fromhex("0300000000000000a3000200050000000000000000000000e7000400000000002800000000000000140002000300000000000000004000000500000000000200")


def parse_coord(token, longitude):
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([NSEWnsew])\s*", token)
    if not match:
        raise ValueError(f"Invalid coordinate: {token.strip()}")

    value = float(match.group(1))
    direction = match.group(2).upper()

    if longitude and direction not in ("E", "W"):
        raise ValueError(f"Longitude must end in E or W: {token.strip()}")
    if not longitude and direction not in ("N", "S"):
        raise ValueError(f"Latitude must end in N or S: {token.strip()}")

    if longitude and value > 180:
        raise ValueError(f"Longitude must be 180 degrees or less: {token.strip()}")
    if not longitude and value > 90:
        raise ValueError(f"Latitude must be 90 degrees or less: {token.strip()}")

    if direction in ("W", "S"):
        value = -value
    return value, direction


def parse_master4(text):
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError("Enter exactly four coordinates separated by commas.")

    west, west_dir = parse_coord(parts[0], True)
    east, east_dir = parse_coord(parts[1], True)
    south, south_dir = parse_coord(parts[2], False)
    north, north_dir = parse_coord(parts[3], False)

    if west >= east:
        raise ValueError("The first longitude must be the west edge and the second the east edge.")
    if south >= north:
        raise ValueError("The third latitude must be the south edge and the fourth the north edge.")
    if not math.isclose(east - west, 1.0, abs_tol=1e-9):
        raise ValueError("The longitude edges must be exactly 1 degree apart.")
    if not math.isclose(north - south, 1.0, abs_tol=1e-9):
        raise ValueError("The latitude edges must be exactly 1 degree apart.")

    for value, name in (
        (west, "west longitude"),
        (east, "east longitude"),
        (south, "south latitude"),
        (north, "north latitude"),
    ):
        if not math.isclose(value, round(value), abs_tol=1e-9):
            raise ValueError(f"Master 4 edges must be whole degrees. Invalid {name}: {value}")

    if south <= -WEB_MERCATOR_MAX_LAT or north >= WEB_MERCATOR_MAX_LAT:
        raise ValueError("Latitude is outside the usable EPSG:3857 Web Mercator range.")

    # Name files from the parsed whole-degree values so 82w, 82.0w and 082w
    # all produce the same "82W" label used by every output filename.
    label = "_".join(
        f"{int(round(abs(value)))}{direction}"
        for value, direction in (
            (west, west_dir), (east, east_dir), (south, south_dir), (north, north_dir)
        )
    )
    return west, east, south, north, label


def mercator_x(lon_deg):
    return EARTH_RADIUS * math.radians(lon_deg)


def mercator_y(lat_deg):
    lat = math.radians(lat_deg)
    return EARTH_RADIUS * math.log(math.tan(math.pi / 4.0 + lat / 2.0))


def cell_records(west, east, south, north):
    """
    Cell numbering follows the first decimal digit of absolute latitude/longitude.

    Examples:
      30.56N, 81.34W -> cell 54
      30.56N, 10.34E -> cell 54
      30.56S, 81.34W -> cell 54
      30.56S, 10.34E -> cell 54

    This makes the 01-100 address pattern work in all four hemispheres.
    """
    records = []

    west_side = east <= 0.0
    south_side = north <= 0.0

    lon_base = abs(east) if west_side else abs(west)
    lat_base = abs(north) if south_side else abs(south)

    for cell_id in range(1, 101):
        row_digit = (cell_id - 1) // 10
        col_digit = (cell_id - 1) % 10

        if west_side:
            lon_w = -(lon_base + (col_digit + 1) / 10.0)
            lon_e = -(lon_base + col_digit / 10.0)
        else:
            lon_w = lon_base + col_digit / 10.0
            lon_e = lon_base + (col_digit + 1) / 10.0

        if south_side:
            lat_s = -(lat_base + (row_digit + 1) / 10.0)
            lat_n = -(lat_base + row_digit / 10.0)
        else:
            lat_s = lat_base + row_digit / 10.0
            lat_n = lat_base + (row_digit + 1) / 10.0

        xmin = mercator_x(lon_w)
        xmax = mercator_x(lon_e)
        ymin = mercator_y(lat_s)
        ymax = mercator_y(lat_n)
        records.append((cell_id, xmin, xmax, ymin, ymax))

    return records


def find_font(size):
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\Arialbd.ttf"),
        Path(r"C:\Windows\Fonts\calibrib.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def make_grid_tif(path, west, east, south, north, records):
    width = IMAGE_SIZE
    height = IMAGE_SIZE

    master_xmin = mercator_x(west)
    master_xmax = mercator_x(east)
    master_ymin = mercator_y(south)
    master_ymax = mercator_y(north)

    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    font = find_font(92)

    def x_to_px(x):
        return (x - master_xmin) / (master_xmax - master_xmin) * (width - 1)

    def y_to_px(y):
        return (master_ymax - y) / (master_ymax - master_ymin) * (height - 1)

    for i in range(11):
        lon = west + i / 10.0
        x = round(x_to_px(mercator_x(lon)))
        draw.line([(x, 0), (x, height - 1)], fill=255, width=12 if i in (0, 10) else 8)

        lat = south + i / 10.0
        y = round(y_to_px(mercator_y(lat)))
        draw.line([(0, y), (width - 1, y)], fill=255, width=12 if i in (0, 10) else 8)

    for cell_id, xmin, xmax, ymin, ymax in records:
        x_center = x_to_px((xmin + xmax) / 2.0)
        y_center = y_to_px((ymin + ymax) / 2.0)
        label = f"{cell_id:02d}" if cell_id < 100 else "100"
        bbox = draw.textbbox((0, 0), label, font=font, stroke_width=8)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text(
            (x_center - text_w / 2.0, y_center - text_h / 2.0),
            label,
            font=font,
            fill=255,
            stroke_width=8,
            stroke_fill=64,
        )

    pixel_x = (master_xmax - master_xmin) / width
    pixel_y = (master_ymax - master_ymin) / height

    tiffinfo = TiffImagePlugin.ImageFileDirectory_v2()
    tiffinfo[33550] = (pixel_x, pixel_y, 0.0)  # ModelPixelScaleTag
    tiffinfo[33922] = (0.0, 0.0, 0.0, master_xmin, master_ymax, 0.0)  # ModelTiepointTag
    tiffinfo[34735] = (
        1, 1, 0, 3,
        1024, 0, 1, 1,      # GTModelTypeGeoKey = Projected
        1025, 0, 1, 1,      # GTRasterTypeGeoKey = PixelIsArea
        3072, 0, 1, EPSG,   # ProjectedCSTypeGeoKey = EPSG:3857
    )
    tiffinfo[42113] = "0"  # GDAL_NODATA: background is transparent/NoData

    image.save(path, format="TIFF", compression="tiff_deflate", tiffinfo=tiffinfo)


def map_filename(master_label, cell_id):
    parts = master_label.split("_")

    def padded(token):
        value = int(token[:-1])
        direction = token[-1]
        return f"{direction}{value:03d}"

    west, east, south, north = (padded(part) for part in parts)
    return f"{west}{east}{north}{south}-{cell_id:03d}-GHY-Z20.tpkx"


def write_extent_txt(path, records, master_label, west, east, south, north):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for cell_id, xmin, xmax, ymin, ymax in records:
            label = f"{cell_id:02d}" if cell_id < 100 else "100"
            filename = map_filename(master_label, cell_id)
            f.write(
                f"{label} {xmin:.4f},{xmax:.4f},{ymin:.4f},{ymax:.4f} [EPSG:{EPSG}] {filename}\n"
            )

        f.write(
            f"MASTER {mercator_x(west):.4f},{mercator_x(east):.4f},"
            f"{mercator_y(south):.4f},{mercator_y(north):.4f} [EPSG:{EPSG}]\n"
        )


def build_outputs(master4_text, output_dir=OUTPUT_DIR):
    west, east, south, north, master_label = parse_master4(master4_text)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    txt_path = output_dir / f"Master4_{master_label}_Extents.txt"
    tif_path = output_dir / f"Master4_{master_label}_Grid.tif"

    records = cell_records(west, east, south, north)

    # Write both files under temporary names first so a failure never leaves a
    # new TXT beside an old or missing TIF.
    txt_partial = txt_path.with_name(txt_path.name + ".partial")
    tif_partial = tif_path.with_name(tif_path.name + ".partial")
    try:
        write_extent_txt(txt_partial, records, master_label, west, east, south, north)
        make_grid_tif(tif_partial, west, east, south, north, records)
        # TIF first: it is the file most likely to be held open by ArcGIS Earth.
        for partial, final in ((tif_partial, tif_path), (txt_partial, txt_path)):
            try:
                os.replace(partial, final)
            except PermissionError:
                raise PermissionError(
                    f"Could not replace {final.name} - it may be open in ArcGIS Earth "
                    "or another program. Close it and try again."
                ) from None
    finally:
        for partial in (txt_partial, tif_partial):
            with contextlib.suppress(OSError):
                partial.unlink()
    return txt_path, tif_path



def inverse_mercator_x(x):
    return math.degrees(x / EARTH_RADIUS)


def inverse_mercator_y(y):
    return math.degrees(2.0 * math.atan(math.exp(y / EARTH_RADIUS)) - math.pi / 2.0)


def zoom_demo_filename(master_label):
    parts = master_label.split("_")

    def padded(token):
        value = int(token[:-1])
        direction = token[-1]
        return f"{direction}{value:03d}"

    west, east, south, north = (padded(part) for part in parts)
    return f"{west}{east}{north}{south}-055-ZOOM-DEMO.tpkx"


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


def make_zoom_tile_png(zoom):
    image = Image.new("RGB", (256, 256), DEMO_COLORS[zoom])
    draw = ImageDraw.Draw(image)
    large_font = find_font(68)
    small_font = find_font(24)

    draw.rectangle((5, 5, 250, 250), outline=(255, 255, 255), width=6)
    label = f"Z{zoom}"
    bbox = draw.textbbox((0, 0), label, font=large_font, stroke_width=3)
    x = (256 - (bbox[2] - bbox[0])) / 2.0
    y = 82 - (bbox[3] - bbox[1]) / 2.0
    draw.text((x, y), label, font=large_font, fill=(255, 255, 255),
              stroke_width=3, stroke_fill=(0, 0, 0))

    sub = "CELL 55"
    bbox = draw.textbbox((0, 0), sub, font=small_font, stroke_width=2)
    x = (256 - (bbox[2] - bbox[0])) / 2.0
    draw.text((x, 174), sub, font=small_font, fill=(255, 255, 255),
              stroke_width=2, stroke_fill=(0, 0, 0))

    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def demo_tile_range(xmin, xmax, ymin, ymax, zoom, resolution, origin):
    tile_side = resolution * 256.0
    limit = (1 << zoom) - 1
    col_min = math.floor((xmin - origin["x"]) / tile_side)
    col_max = math.ceil((xmax - origin["x"]) / tile_side) - 1
    row_min = math.floor((origin["y"] - ymax) / tile_side)
    row_max = math.ceil((origin["y"] - ymin) / tile_side) - 1
    return (
        max(0, min(limit, col_min)),
        max(0, min(limit, col_max)),
        max(0, min(limit, row_min)),
        max(0, min(limit, row_max)),
    )


def make_cell55_zoom_demo_tpkx(path, records, master_label):
    path = Path(path)
    if path.exists():
        raise FileExistsError(
            f"Output already exists: {path} - delete or rename it to create a new demo."
        )

    # Build under a temporary name so an interrupted build never leaves a
    # complete-looking but incomplete demo TPKX behind.
    partial = path.with_name(path.name + ".partial")
    try:
        written, bundle_count = _build_cell55_zoom_demo(partial, records, master_label)
        if path.exists():
            raise FileExistsError(f"Output appeared during the build: {path} - nothing was overwritten.")
        partial.replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            partial.unlink()
        raise
    print(
        f"Cell 55 zoom demo complete: {written} tiles, {bundle_count} bundles -> {path}"
    )
    return path


def _build_cell55_zoom_demo(path, records, master_label):
    cell = next(record for record in records if record[0] == DEMO_CELL)
    _, xmin, xmax, ymin, ymax = cell

    levels = {entry["level"]: entry for entry in REFERENCE_ROOT["tileInfo"]["lods"]}
    origin = REFERENCE_ROOT["tileInfo"]["origin"]

    root = copy.deepcopy(REFERENCE_ROOT)
    item = copy.deepcopy(REFERENCE_ITEM)
    name = f"Master 4 Cell 55 Zoom Demo ({master_label})"
    root["name"] = item["name"] = item["title"] = name
    root["minLOD"], root["maxLOD"] = DEMO_MIN_ZOOM, DEMO_MAX_ZOOM
    root["minScale"] = levels[DEMO_MIN_ZOOM]["scale"]
    root["maxScale"] = levels[DEMO_MAX_ZOOM]["scale"]
    extent = {
        "xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax,
        "spatialReference": copy.deepcopy(root["spatialReference"]),
    }
    root["initialExtent"] = copy.deepcopy(extent)
    root["fullExtent"] = extent

    item["guid"] = str(uuid.uuid4()).upper()
    item["extent"] = {
        "xmin": inverse_mercator_x(xmin),
        "ymin": inverse_mercator_y(ymin),
        "xmax": inverse_mercator_x(xmax),
        "ymax": inverse_mercator_y(ymax),
        "spatialReference": copy.deepcopy(item["extent"]["spatialReference"]),
    }

    tiles = {z: make_zoom_tile_png(z) for z in range(DEMO_MIN_ZOOM, DEMO_MAX_ZOOM + 1)}
    with Image.open(io.BytesIO(tiles[DEMO_MAX_ZOOM])) as picture:
        thumbnail = io.BytesIO()
        picture.resize((300, 200)).save(thumbnail, format="PNG")

    now = datetime.datetime.now(datetime.timezone.utc)
    file_time = int((now.timestamp() + 11644473600) * 10000000)
    ntfs_extra = struct.pack(
        "<HHIHHQQQ", 0x000A, 32, 0, 1, 24, file_time, file_time, file_time
    )

    written = 0
    bundle_count = 0
    with zipfile.ZipFile(path, "w", allowZip64=True) as package:
        package.writestr(
            zip_entry("iteminfo.json", now, ntfs_extra),
            json.dumps(item, separators=(",", ":")).encode(),
        )
        package.writestr(
            zip_entry("root.json", now, ntfs_extra),
            json.dumps(root, separators=(",", ":")).encode(),
        )
        package.writestr(
            zip_entry("thumbnail.png", now, ntfs_extra), thumbnail.getvalue()
        )

        for zoom in range(DEMO_MIN_ZOOM, DEMO_MAX_ZOOM + 1):
            resolution = levels[zoom]["resolution"]
            col_min, col_max, row_min, row_max = demo_tile_range(
                xmin, xmax, ymin, ymax, zoom, resolution, origin
            )
            image = tiles[zoom]
            largest_image = len(image)
            zoom_written = 0

            first_bundle_row = (row_min // 128) * 128
            last_bundle_row = (row_max // 128) * 128
            first_bundle_col = (col_min // 128) * 128
            last_bundle_col = (col_max // 128) * 128

            for row0 in range(first_bundle_row, last_bundle_row + 1, 128):
                for col0 in range(first_bundle_col, last_bundle_col + 1, 128):
                    r_start = max(row_min, row0)
                    r_end = min(row_max, row0 + 127)
                    c_start = max(col_min, col0)
                    c_end = min(col_max, col0 + 127)
                    if r_start > r_end or c_start > c_end:
                        continue

                    index = [4] * 16384
                    with tempfile.TemporaryFile(mode="w+b") as bundle:
                        bundle.write(b"\x00" * (64 + 131072))
                        for row in range(r_start, r_end + 1):
                            for column in range(c_start, c_end + 1):
                                slot = (row - row0) * 128 + column - col0
                                bundle.write(struct.pack("<I", len(image)))
                                offset = bundle.tell()
                                bundle.write(image)
                                index[slot] = len(image) << 40 | offset
                                written += 1
                                zoom_written += 1

                        bundle_length = bundle.tell()
                        header = bytearray(REFERENCE_HEADER)
                        struct.pack_into("<I", header, 8, max(131092, largest_image))
                        struct.pack_into("<Q", header, 24, bundle_length)
                        bundle.seek(0)
                        bundle.write(header)
                        bundle.write(struct.pack("<16384Q", *index))
                        bundle.seek(0)

                        filename = f"tile/L{zoom:02d}/R{row0:04x}C{col0:04x}.bundle"
                        entry = zip_entry(filename, now, ntfs_extra)
                        entry.file_size = bundle_length
                        with package.open(entry, "w") as member:
                            shutil.copyfileobj(bundle, member, length=1024 * 1024)
                        bundle_count += 1

            print(f"Z{zoom}: {zoom_written} colored tiles complete", flush=True)

    return written, bundle_count


def main():
    try:
        run()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        raise SystemExit(1)


def run():
    print(f"Master 4 Grid Maker v{VERSION}")
    print("Example: 82w, 81w, 30n, 31n")
    print("East example: 10e, 11e, 30n, 31n")
    print("South example: 82w, 81w, 31s, 30s")
    print()

    # A mistake asks again instead of closing the program; a blank entry quits.
    while True:
        master4_text = input("Enter Master 4 (blank to quit): ").strip()
        if not master4_text:
            print("No Master 4 entered - nothing created.")
            return
        try:
            txt_path, tif_path = build_outputs(master4_text)
            break
        except Exception as exc:
            print(f"\nERROR: {exc}")
            print("Try again, or press Enter on a blank line to quit.\n")

    print("\nCreated:")
    print(txt_path)
    print(tif_path)

    choice = input("\nCreate Cell 55 colored zoom-demo TPKX (Z10-Z20)? [y/N]: ").strip().lower()
    if choice in ("y", "yes"):
        try:
            west, east, south, north, master_label = parse_master4(master4_text)
            records = cell_records(west, east, south, north)
            demo_path = Path(txt_path).parent / zoom_demo_filename(master_label)
            make_cell55_zoom_demo_tpkx(demo_path, records, master_label)
        except Exception as exc:
            print(f"\nERROR creating Cell 55 zoom demo: {exc}")
            raise SystemExit(1)
        print("\nCreated:")
        print(demo_path)


if __name__ == "__main__":
    main()
