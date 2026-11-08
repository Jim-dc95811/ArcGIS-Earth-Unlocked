"""Parcel100 2.1

2.1 re-hardening (2026-11-08) - a normal build writes exactly the same files as 2.0:
  - BUILD checks the cell files already in the folder: if they came from a different layer
    or hold different fields, it asks Replace / Keep / Cancel (a true resume still skips
    quietly)
  - URLs copied from the browser with ?f=pjson or #... on the end are accepted
  - a login page or other non-map answer gets a plain message
  - a parcel the server sends with an empty shape {} is written without a shape and
    counted, instead of stopping the whole build
  - plain messages for the Coordinate precision box and a Master 4 box typed as numbers
  - the end message shows the 100 cells as written / already there / empty, with the parcel
    count on its own line (Jim: '64 written, 36 skipped')

2.0 = 1.5 (2.0 Reference, 2026-11-08).

Parcel100 1.5

1.5 adds service-root discovery: paste a FeatureServer/MapServer service or a layer URL;
if the service has several polygon layers, a chooser lists them.

1.5 hardening (Master 4 cells, file names, ID-query fallback, polygon conversion and
normal output unchanged from 1.4):
  - each cell is written as .partial and renamed when complete; on resume, an existing
    cell that is not complete GeoJSON is rebuilt instead of skipped
  - every parcel ID is checked; missing parcels are asked for once more and any still
    missing are reported per cell (the cell is still written)
  - a download batch that keeps timing out is split in half and retried
  - the build uses the layer that was read; editing the URL afterwards asks for a re-read
  - discovery reports layers that could not be checked and shows its progress
"""
import json
import math
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Parcel100"
VERSION = "2.1"
FLORIDA_URL = "https://services5.arcgis.com/GcvM6vDlR2gM4x31/arcgis/rest/services/FL_Parcels/FeatureServer/0"
DEFAULT_MASTER4 = "82w,81w,30n,31n"
DEFAULT_PRECISION = 7
TIMEOUT = 90
RETRIES = 3

# These are only preferences for the known Florida layer. Other services are
# discovered from their own metadata and the user chooses the fields.
FLORIDA_PREFERRED_FIELDS = [
    "OWN_NAME",
    "PHY_ADDR1",
    "PHY_CITY",
    "PHY_ZIPCD",
    "PARCEL_ID",
    "ACRES",
]


def parse_coord(token, longitude):
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([NSEWnsew])\s*", token)
    if not match:
        raise ValueError(f"Invalid coordinate: {token.strip()}\n\nWrite each edge as whole degrees with a "
                         f"letter, west,east,south,north - for example {DEFAULT_MASTER4}")
    value = float(match.group(1))
    direction = match.group(2).upper()
    if longitude and direction not in ("E", "W"):
        raise ValueError(f"Longitude must end in E or W: {token.strip()}")
    if not longitude and direction not in ("N", "S"):
        raise ValueError(f"Latitude must end in N or S: {token.strip()}")
    if longitude and value > 180:
        raise ValueError("Longitude must be 180 degrees or less.")
    if not longitude and value > 90:
        raise ValueError("Latitude must be 90 degrees or less.")
    if direction in ("W", "S"):
        value = -value
    return value


def parse_master4(text):
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError("Enter four coordinates: west,east,south,north")
    west = parse_coord(parts[0], True)
    east = parse_coord(parts[1], True)
    south = parse_coord(parts[2], False)
    north = parse_coord(parts[3], False)
    if west >= east:
        raise ValueError("The first longitude must be the west edge.")
    if south >= north:
        raise ValueError("The third latitude must be the south edge.")
    if not math.isclose(east - west, 1.0, abs_tol=1e-9):
        raise ValueError("Master 4 longitude edges must be exactly 1 degree apart.")
    if not math.isclose(north - south, 1.0, abs_tol=1e-9):
        raise ValueError("Master 4 latitude edges must be exactly 1 degree apart.")
    for value, name in ((west, "west"), (east, "east"), (south, "south"), (north, "north")):
        if not math.isclose(value, round(value), abs_tol=1e-9):
            raise ValueError(f"Master 4 {name} edge must be a whole degree.")
    label = "_".join(p.upper().replace(" ", "") for p in parts)
    return west, east, south, north, label


def cell_bounds(west, east, south, north):
    """Match the established Master4 Grid Maker 01-100 cell numbering."""
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

        records.append((cell_id, lon_w, lon_e, lat_s, lat_n))
    return records


def padded_master_label(master_label):
    parts = master_label.split("_")
    if len(parts) != 4:
        return master_label.replace(",", "_")

    def padded(token):
        value = int(float(token[:-1]))
        direction = token[-1].upper()
        return f"{direction}{value:03d}"

    west, east, south, north = (padded(p) for p in parts)
    return f"{west}{east}{north}{south}"


def output_name(master_label, cell_id):
    return f"{padded_master_label(master_label)}-{cell_id:03d}-Parcels.geojson"


NOT_MAP_DATA = ("The server did not send map data. It may need a login, or this is not an ArcGIS REST "
                "service URL (it should end in /FeatureServer or /MapServer, maybe with a layer number).")


def _request(url, params, expect_json=True, retry_callback=None):
    data = urllib.parse.urlencode(params).encode("utf-8")
    last_error = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "User-Agent": f"{APP_NAME}/{VERSION}",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json, application/geo+json, */*",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                raw = response.read()
            if not expect_json:
                return raw
            try:
                result = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise RuntimeError(NOT_MAP_DATA) from None
            if isinstance(result, dict) and "error" in result:
                err = result["error"]
                msg = err.get("message", "ArcGIS service error") if isinstance(err, dict) else str(err)
                details = err.get("details", []) if isinstance(err, dict) else []
                if details:
                    msg += " — " + "; ".join(str(x) for x in details)
                raise RuntimeError(msg)
            return result
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < RETRIES:
                if retry_callback is not None:
                    retry_callback(attempt + 2, RETRIES, exc)
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(str(last_error))


def _service_url_parts(url):
    # 2.1: a URL copied from the browser may end in ?f=pjson or #...; drop that first.
    clean = re.split(r"[?#]", url.strip(), maxsplit=1)[0].rstrip("/")
    # A URL copied from a browser query page ends in /query; the layer is the part before it.
    clean = re.sub(r"/query(?:\?.*)?$", "", clean, flags=re.IGNORECASE).rstrip("/")
    match = re.fullmatch(r"(.+/(?:FeatureServer|MapServer))(?:/(\d+))?", clean, re.IGNORECASE)
    if not match:
        raise ValueError("Paste an ArcGIS FeatureServer or MapServer service or layer URL.")
    service_url = match.group(1)
    layer_id = int(match.group(2)) if match.group(2) is not None else None
    return service_url, layer_id


def _read_polygon_layer(layer_url):
    layer_url = layer_url.rstrip("/")
    meta = _request(layer_url, {"f": "json"})
    if meta.get("type") not in ("Feature Layer", None):
        raise ValueError("URL does not appear to be an ArcGIS feature layer.")
    if meta.get("geometryType") != "esriGeometryPolygon":
        raise ValueError(f"Parcel100 requires a polygon layer. Service reports: {meta.get('geometryType')}")
    fields = meta.get("fields") or []
    if not fields:
        raise ValueError("No fields were reported by the service.")
    return meta


def discover_polygon_layers(url, progress_callback=None):
    """Return (candidates, unchecked).

    candidates: [(layer_url, meta)] for the polygon layers found.
    unchecked:  ["name (reason)"] for advertised layers that could not be read, so a
                layer the server failed to describe is reported rather than silently missing.
    """
    service_url, layer_id = _service_url_parts(url)
    if layer_id is not None:
        layer_url = f"{service_url}/{layer_id}"
        return [(layer_url, _read_polygon_layer(layer_url))], []

    service_meta = _request(service_url, {"f": "json"})
    layers = [layer for layer in (service_meta.get("layers") or []) if layer.get("id") is not None]
    candidates = []
    unchecked = []
    for number, layer in enumerate(layers, start=1):
        candidate_id = layer.get("id")
        label = layer.get("name") or f"layer {candidate_id}"
        if progress_callback is not None:
            progress_callback(f"Checking layer {number} of {len(layers)}: {label}...")
        layer_url = f"{service_url}/{candidate_id}"
        try:
            meta = _request(layer_url, {"f": "json"})
        except Exception as exc:
            unchecked.append(f"{candidate_id}: {label} ({exc})")
            continue
        if meta.get("geometryType") != "esriGeometryPolygon":
            continue
        if not (meta.get("fields") or []):
            continue
        candidates.append((layer_url, meta))

    if not candidates:
        if unchecked:
            raise ValueError(
                "No polygon layer could be confirmed. These layers did not respond and may "
                "include the parcels:\n\n" + "\n".join(unchecked[:8]) +
                "\n\nTry again later, or paste the parcel layer's own URL (ending in /<layer number>).")
        raise ValueError("No polygon layers were found in this ArcGIS service.")
    return candidates, unchecked


def _query_endpoint(layer_url):
    return layer_url.rstrip("/") + "/query"


def query_object_ids(layer_url, bbox, retry_callback=None):
    w, e, s, n = bbox
    params = {
        "f": "json",
        "where": "1=1",
        "geometry": f"{w:.10f},{s:.10f},{e:.10f},{n:.10f}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "returnIdsOnly": "true",
        "returnGeometry": "false",
    }
    data = _request(_query_endpoint(layer_url), params, retry_callback=retry_callback)
    return data.get("objectIds") or [], data.get("objectIdFieldName")


def _is_transient_query_error(exc):
    text = str(exc).lower()
    markers = (
        "504",
        "502",
        "503",
        "gateway timeout",
        "timed out",
        "timeout",
        "remote end closed connection",
        "connection reset",
        "temporarily unavailable",
    )
    return any(marker in text for marker in markers)


def split_bbox_quarters(bbox):
    w, e, s, n = bbox
    mid_x = (w + e) / 2.0
    mid_y = (s + n) / 2.0
    return [
        (w, mid_x, s, mid_y),
        (mid_x, e, s, mid_y),
        (w, mid_x, mid_y, n),
        (mid_x, e, mid_y, n),
    ]


def query_object_ids_with_fallback(layer_url, bbox, status_callback=None):
    def retry_status(prefix):
        if status_callback is None:
            return None

        def callback(next_attempt, total_attempts, exc):
            status_callback(
                f"{prefix}: request failed ({exc}) - retry {next_attempt} of {total_attempts}..."
            )

        return callback

    try:
        return query_object_ids(layer_url, bbox, retry_callback=retry_status("ID query"))
    except RuntimeError as exc:
        if not _is_transient_query_error(exc):
            raise
        if status_callback is not None:
            status_callback(f"ID query failed ({exc}) - using 4-part fallback...")

    all_ids = set()
    object_id_field = None
    quarters = split_bbox_quarters(bbox)
    for quarter_number, quarter_bbox in enumerate(quarters, start=1):
        if status_callback is not None:
            status_callback(f"4-part fallback: querying quarter {quarter_number} of 4...")
        ids, oid_field = query_object_ids(
            layer_url,
            quarter_bbox,
            retry_callback=retry_status(f"Fallback quarter {quarter_number}/4"),
        )
        all_ids.update(ids)
        if object_id_field is None and oid_field:
            object_id_field = oid_field

    return sorted(all_ids), object_id_field


def _signed_area(ring):
    total = 0.0
    if len(ring) < 3:
        return 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][1]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _close_ring(ring):
    pts = [[float(p[0]), float(p[1])] for p in ring if p is not None and len(p) >= 2]
    if pts and pts[0] != pts[-1]:
        pts.append(pts[0][:])
    return pts


def _point_in_ring(point, ring):
    x, y = point
    inside = False
    if len(ring) < 4:
        return False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) if (yj - yi) != 0 else 1e-300) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _representative_point(ring):
    # A ring vertex is adequate for the containment test in ordinary parcel data.
    # If it sits on another ring boundary, try subsequent vertices.
    if not ring:
        return (0.0, 0.0)
    for p in ring[:-1] if len(ring) > 1 else ring:
        return (p[0], p[1])
    return (ring[0][0], ring[0][1])


def esri_rings_to_geojson(rings):
    clean = [_close_ring(r) for r in (rings or [])]
    clean = [r for r in clean if len(r) >= 4 and abs(_signed_area(r)) > 0]
    if not clean:
        return None

    # Build a containment tree independent of ring winding direction. This
    # handles services that do not consistently preserve Esri winding rules.
    info = []
    for idx, ring in enumerate(clean):
        info.append({"idx": idx, "ring": ring, "area": abs(_signed_area(ring)), "parent": None, "depth": 0})

    by_area = sorted(info, key=lambda x: x["area"])
    for item in by_area:
        point = _representative_point(item["ring"])
        candidates = [x for x in info if x["area"] > item["area"] and _point_in_ring(point, x["ring"])]
        if candidates:
            item["parent"] = min(candidates, key=lambda x: x["area"])["idx"]

    index_map = {x["idx"]: x for x in info}
    for item in info:
        depth = 0
        parent = item["parent"]
        seen = set()
        while parent is not None and parent not in seen:
            seen.add(parent)
            depth += 1
            parent = index_map[parent]["parent"]
        item["depth"] = depth

    polygons = []
    for outer in [x for x in info if x["depth"] % 2 == 0]:
        coords = [outer["ring"]]
        holes = [
            x for x in info
            if x["parent"] == outer["idx"] and x["depth"] == outer["depth"] + 1
        ]
        coords.extend(h["ring"] for h in holes)
        polygons.append(coords)

    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def esri_feature_to_geojson(feature, selected_fields):
    attrs = feature.get("attributes") or {}
    props = {name: attrs.get(name) for name in selected_fields}
    geom = feature.get("geometry")
    if geom is None:
        geometry = None
    elif "rings" in geom:
        geometry = esri_rings_to_geojson(geom.get("rings"))
    elif not any(k in geom for k in ("x", "points", "paths")):
        geometry = None   # 2.1: an empty shape {} - written without a shape, counted by the caller
    else:
        raise ValueError("Service returned a non-polygon geometry.")
    return {"type": "Feature", "properties": props, "geometry": geometry}


def _query_esri_batch(endpoint, batch, request_fields, precision, retry_callback=None, status_callback=None):
    """One feature request. A batch that keeps failing with a timeout-type error is split in
    half and each half is requested separately (down to single parcels)."""
    params = {
        "f": "json",
        "objectIds": ",".join(str(x) for x in batch),
        "outFields": ",".join(request_fields),
        "returnGeometry": "true",
        "outSR": "4326",
        "returnZ": "false",
        "returnM": "false",
        "geometryPrecision": str(precision),
    }
    try:
        data = _request(endpoint, params, retry_callback=retry_callback)
        return data.get("features") or []
    except RuntimeError as exc:
        if len(batch) <= 1 or not _is_transient_query_error(exc):
            raise
        mid = len(batch) // 2
        if status_callback is not None:
            status_callback(f"batch of {len(batch):,} parcels timed out - splitting into {mid:,} + {len(batch) - mid:,}...")
        return (_query_esri_batch(endpoint, batch[:mid], request_fields, precision, retry_callback, status_callback) +
                _query_esri_batch(endpoint, batch[mid:], request_fields, precision, retry_callback, status_callback))


def query_features_json(layer_url, ids, fields, precision, batch_size, retry_callback=None,
                        oid_field=None, status_callback=None):
    """Download the parcels for one cell. Returns (geojson_features, missing_ids).

    The object-ID field is requested as well (only the chosen fields are written) so every
    returned parcel can be matched to its ID; parcels not returned are requested once more."""
    if not ids:
        return [], []
    endpoint = _query_endpoint(layer_url)
    request_fields = list(fields)
    if oid_field and oid_field not in request_fields:
        request_fields.append(oid_field)

    def fetch(id_list):
        got = []
        for start in range(0, len(id_list), batch_size):
            got.extend(_query_esri_batch(endpoint, id_list[start:start + batch_size], request_fields,
                                         precision, retry_callback, status_callback))
        return got

    esri = fetch(ids)
    missing = []
    if oid_field:
        def seen_ids(feats):
            return {str((f.get("attributes") or {}).get(oid_field)) for f in feats}
        seen = seen_ids(esri)
        missing = [i for i in ids if str(i) not in seen]
        if missing:
            if status_callback is not None:
                status_callback(f"{len(missing):,} parcels were not returned - asking for them once more...")
            try:
                esri.extend(fetch(missing))
            except RuntimeError:
                pass  # reported below as still missing
            seen = seen_ids(esri)
            missing = [i for i in ids if str(i) not in seen]
        # A parcel returned twice (once per request) is written once.
        unique, kept = [], set()
        for f in esri:
            key = str((f.get("attributes") or {}).get(oid_field))
            if key in kept:
                continue
            kept.add(key)
            unique.append(f)
        esri = unique
    elif len(esri) < len(ids):
        missing = [None] * (len(ids) - len(esri))
    return [esri_feature_to_geojson(f, fields) for f in esri], missing


def write_feature_collection(path, features, master_label, cell_id, bbox, source_url):
    w, e, s, n = bbox
    collection = {
        "type": "FeatureCollection",
        "name": path.stem,
        "bbox": [w, s, e, n],
        "master4": master_label,
        "cell": cell_id,
        "source": source_url,
        "features": features,
    }
    # Write beside the real file and rename only when complete, so an interrupted build
    # can never leave a half-written cell that resume would treat as finished.
    partial = path.with_name(path.name + ".partial")
    try:
        with partial.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(collection, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(partial, path)
    except BaseException:
        try:
            partial.unlink()
        except OSError:
            pass
        raise


def is_complete_cell(path):
    """True if an existing cell file is complete GeoJSON (written by any version)."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("type") == "FeatureCollection" and isinstance(data.get("features"), list)
    except (OSError, ValueError, AttributeError):
        return False


def read_cell_header(path, limit=262144):
    """2.1: (source URL, field names) of an existing cell file, read from its first bytes only
    (cell files can be large). Field names come from the first parcel; None if not found."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            head = f.read(limit)
    except OSError:
        return None, None
    dec = json.JSONDecoder()

    def value_after(key):
        m = re.search(r'"%s"\s*:\s*' % key, head)
        if not m:
            return None
        try:
            return dec.raw_decode(head, m.end())[0]
        except ValueError:
            return None

    source = value_after("source")
    props = value_after("properties")
    fields = list(props) if isinstance(props, dict) else None
    return source, fields


def mismatched_cells(out_dir, label, layer_url, fields):
    """2.1: cell files of this Master 4 box already in out_dir that were made from another layer
    or with other fields: [(cell_id, reason)]."""
    out = []
    want_url = layer_url.rstrip("/").lower()
    for cell_id in range(1, 101):
        path = Path(out_dir) / output_name(label, cell_id)
        if not path.exists():
            continue
        source, have = read_cell_header(path)
        if source is not None and str(source).rstrip("/").lower() != want_url:
            out.append((cell_id, "another layer"))
        elif have is not None and have != list(fields):
            out.append((cell_id, "other fields"))
    return out


def recommended_indices(fields):
    names = [f.get("name", "") for f in fields]
    upper = [n.upper() for n in names]
    chosen = []

    # Exact known Florida fields first.
    for preferred in FLORIDA_PREFERRED_FIELDS:
        if preferred in upper:
            chosen.append(upper.index(preferred))

    if chosen:
        return sorted(set(chosen))

    # Portable fallback for other states/counties.
    keywords = (
        "OWNER", "OWN_NAME", "OWNNAME", "ONAME",
        "ADDRESS", "ADDR", "SITE", "PHYS", "PHY_",
        "PARCEL", "PARCELID", "PARCEL_ID", "APN", "PIN",
        "CITY", "ZIP",
    )
    for i, name in enumerate(upper):
        if any(k in name for k in keywords):
            chosen.append(i)
    return sorted(set(chosen))[:12]


class Parcel100App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("860x690")
        self.minsize(760, 620)
        self.meta = None
        self.fields = []
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Master 4", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.master_var = tk.StringVar(value=DEFAULT_MASTER4)
        ttk.Entry(outer, textvariable=self.master_var).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(2, 8))
        ttk.Label(outer, text="Example: 82w,81w,30n,31n   (west,east,south,north)").grid(row=2, column=0, columnspan=3, sticky="w")

        ttk.Label(outer, text="ArcGIS FeatureServer / MapServer polygon service or layer URL", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.url_var = tk.StringVar(value=FLORIDA_URL)
        ttk.Entry(outer, textvariable=self.url_var).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(2, 4))
        self.read_btn = ttk.Button(outer, text="Read Service", command=self.read_service_clicked)
        self.read_btn.grid(row=4, column=2, sticky="ew", padx=(8, 0))

        ttk.Label(outer, text="Fields to keep in each GeoJSON", font=("Segoe UI", 10, "bold")).grid(row=5, column=0, sticky="w", pady=(12, 2))

        field_frame = ttk.Frame(outer)
        field_frame.grid(row=6, column=0, columnspan=3, sticky="nsew")
        self.field_list = tk.Listbox(field_frame, selectmode=tk.EXTENDED, exportselection=False, height=16)
        field_scroll = ttk.Scrollbar(field_frame, orient="vertical", command=self.field_list.yview)
        self.field_list.configure(yscrollcommand=field_scroll.set)
        self.field_list.pack(side="left", fill="both", expand=True)
        field_scroll.pack(side="right", fill="y")

        btns = ttk.Frame(outer)
        btns.grid(row=7, column=0, columnspan=3, sticky="w", pady=(6, 8))
        ttk.Button(btns, text="Recommended", command=self.select_recommended).pack(side="left")
        ttk.Button(btns, text="Select All", command=lambda: self.field_list.select_set(0, tk.END)).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text="Clear", command=lambda: self.field_list.selection_clear(0, tk.END)).pack(side="left", padx=(6, 0))

        ttk.Label(outer, text="Output folder", font=("Segoe UI", 10, "bold")).grid(row=8, column=0, sticky="w", pady=(4, 0))
        default_dir = Path.home() / "Downloads" / "Parcel100"
        self.output_var = tk.StringVar(value=str(default_dir))
        ttk.Entry(outer, textvariable=self.output_var).grid(row=9, column=0, columnspan=2, sticky="ew", pady=(2, 4))
        ttk.Button(outer, text="Browse", command=self.browse_output).grid(row=9, column=2, sticky="ew", padx=(8, 0))

        opts = ttk.Frame(outer)
        opts.grid(row=10, column=0, columnspan=3, sticky="w", pady=(8, 8))
        ttk.Label(opts, text="Coordinate precision:").pack(side="left")
        self.precision_var = tk.IntVar(value=DEFAULT_PRECISION)
        ttk.Spinbox(opts, from_=5, to=12, width=5, textvariable=self.precision_var).pack(side="left", padx=(6, 18))
        ttk.Label(opts, text="Up to 100 files; existing files and empty cells are skipped (01-100)").pack(side="left")

        self.build_btn = ttk.Button(outer, text="BUILD 100 GEOJSON FILES", command=self.build_clicked)
        self.build_btn.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(6, 8), ipady=5)

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress.grid(row=12, column=0, columnspan=3, sticky="ew")
        self.status_var = tk.StringVar(value="Ready. Read the service first.")
        ttk.Label(outer, textvariable=self.status_var).grid(row=13, column=0, columnspan=3, sticky="w", pady=(6, 0))

        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)
        outer.columnconfigure(2, weight=0)
        outer.rowconfigure(6, weight=1)

    def set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.read_btn.configure(state=state)
        self.build_btn.configure(state=state)

    def browse_output(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get() or str(Path.home()))
        if folder:
            self.output_var.set(folder)

    def read_service_clicked(self):
        if self.worker and self.worker.is_alive():
            return
        self.set_busy(True)
        self.status_var.set("Reading service metadata...")
        self.worker = threading.Thread(target=self._read_service_worker, daemon=True)
        self.worker.start()

    def _read_service_worker(self):
        try:
            candidates, unchecked = discover_polygon_layers(
                self.url_var.get().strip(),
                progress_callback=lambda text: self.after(0, self.status_var.set, text),
            )
            self.after(0, self._handle_polygon_layers, candidates, unchecked)
        except Exception as exc:
            self.after(0, self._error, f"Could not read service:\n\n{exc}")

    def _handle_polygon_layers(self, candidates, unchecked=()):
        unchecked = list(unchecked)
        if len(candidates) == 1 and not unchecked:
            layer_url, meta = candidates[0]
            self._accept_polygon_layer(layer_url, meta)
            return

        chooser = tk.Toplevel(self)
        chooser.title("Choose polygon layer")
        chooser.transient(self)

        ttk.Label(
            chooser,
            text=("This service contains multiple polygon layers. Choose one:" if len(candidates) > 1
                  else "Polygon layer found. Use it, or Cancel and try again later:"),
            padding=(12, 12, 12, 6),
        ).pack(anchor="w")
        if unchecked:
            ttk.Label(
                chooser,
                text=("These layers did not respond and could not be checked:\n" +
                      "\n".join(unchecked[:6]) + ("\n..." if len(unchecked) > 6 else "")),
                foreground="#9a4b00", wraplength=520, justify="left", padding=(12, 0, 12, 6),
            ).pack(anchor="w")

        frame = ttk.Frame(chooser, padding=(12, 0, 12, 8))
        frame.pack(fill="both", expand=True)
        layer_list = tk.Listbox(frame, exportselection=False, height=min(12, len(candidates)), width=70)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=layer_list.yview)
        layer_list.configure(yscrollcommand=scroll.set)
        layer_list.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for layer_url, meta in candidates:
            layer_id = layer_url.rsplit("/", 1)[-1]
            layer_list.insert(tk.END, f"{layer_id}: {meta.get('name', 'Layer')}")
        layer_list.selection_set(0)
        layer_list.see(0)

        buttons = ttk.Frame(chooser, padding=(12, 0, 12, 12))
        buttons.pack(fill="x")

        def use_selected(event=None):
            selected = layer_list.curselection()
            if not selected:
                return
            layer_url, meta = candidates[selected[0]]
            try:
                chooser.grab_release()
            except tk.TclError:
                pass
            chooser.destroy()
            self._accept_polygon_layer(layer_url, meta)

        def cancel():
            try:
                chooser.grab_release()
            except tk.TclError:
                pass
            chooser.destroy()
            self.set_busy(False)
            self.status_var.set("Layer selection cancelled.")

        ttk.Button(buttons, text="Use Selected Layer", command=use_selected).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=cancel).pack(side="right")
        layer_list.bind("<Double-Button-1>", use_selected)
        chooser.protocol("WM_DELETE_WINDOW", cancel)
        chooser.wait_visibility()
        chooser.grab_set()
        layer_list.focus_set()

    def _accept_polygon_layer(self, layer_url, meta):
        self.layer_url = layer_url
        self.url_var.set(layer_url)
        fields = [f for f in meta.get("fields", []) if f.get("type") != "esriFieldTypeGeometry"]
        self._load_fields(meta, fields)

    def _load_fields(self, meta, fields):
        self.meta = meta
        self.fields = fields
        self.field_list.delete(0, tk.END)
        for f in fields:
            name = f.get("name", "")
            alias = f.get("alias", "")
            line = name if not alias or alias == name else f"{name}    [{alias}]"
            self.field_list.insert(tk.END, line)
        self.select_recommended()
        max_count = meta.get("maxRecordCount", 2000)
        layer_name = meta.get("name", "Feature layer")
        self.status_var.set(f"Loaded {len(fields)} fields from {layer_name}. Max record count: {max_count}.")
        self.set_busy(False)

    def select_recommended(self):
        self.field_list.selection_clear(0, tk.END)
        if not self.fields:
            return
        for idx in recommended_indices(self.fields):
            self.field_list.selection_set(idx)
        if self.field_list.curselection():
            self.field_list.see(self.field_list.curselection()[0])

    def _selected_field_names(self):
        return [self.fields[i].get("name") for i in self.field_list.curselection()]

    def build_clicked(self):
        if self.worker and self.worker.is_alive():
            return
        if self.meta is None:
            messagebox.showerror(APP_NAME, "Read the FeatureServer first.")
            return
        if self.url_var.get().strip().rstrip("/") != (getattr(self, "layer_url", "") or "").rstrip("/"):
            messagebox.showerror(
                APP_NAME,
                "The service URL was changed after Read Service.\n\n"
                "Click Read Service again so the field list matches the layer that will be downloaded.")
            return
        try:
            master = parse_master4(self.master_var.get())
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Master 4: {exc}")
            return
        try:
            precision = int(str(self.precision_var.get()).strip())
            if precision < 5 or precision > 12:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror(APP_NAME, "Coordinate precision: type a whole number from 5 to 12 (7 is the usual).")
            return
        fields = self._selected_field_names()
        if not fields:
            messagebox.showerror(APP_NAME, "Select at least one field to keep.")
            return
        out_dir = Path(self.output_var.get().strip())
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Cannot create output folder:\n{exc}")
            return

        # 2.1: cell files left from another layer or field list are not skipped without a word.
        replace = set()
        clash = mismatched_cells(out_dir, master[4], self.layer_url, fields)
        if clash:
            listed = ", ".join(f"{c:03d}" for c, _ in clash[:20]) + (" ..." if len(clash) > 20 else "")
            reasons = sorted({r for _, r in clash})
            answer = messagebox.askyesnocancel(
                APP_NAME,
                f"{len(clash)} cell file(s) already in this folder were made from {' / '.join(reasons)}:\n{listed}\n\n"
                "Yes = replace them with this layer and these fields\n"
                "No = keep the old files (they are skipped)\n"
                "Cancel = stop", icon="warning")
            if answer is None:
                self.status_var.set("Not built.")
                return
            if answer:
                replace = {c for c, _ in clash}

        self.progress["value"] = 0
        self.set_busy(True)
        self.status_var.set("Starting...")
        self.worker = threading.Thread(
            target=self._build_worker,
            args=(master, fields, precision, out_dir, replace),
            daemon=True,
        )
        self.worker.start()

    def _build_worker(self, master, fields, precision, out_dir, replace=frozenset()):
        west, east, south, north, label = master
        cells = cell_bounds(west, east, south, north)
        max_count = int(self.meta.get("maxRecordCount") or 2000)
        batch_size = max(1, min(max_count, 2000))
        url = self.layer_url.rstrip("/")
        meta_oid = self.meta.get("objectIdField") or self.meta.get("objectIdFieldName")
        total_features = 0
        files_written = 0
        existing_files = 0
        empty_cells = 0
        rebuilt = []
        shortfalls = []
        no_shape = 0
        replaced = []
        try:
            for index, (cell_id, w, e, s, n) in enumerate(cells, start=1):
                path = out_dir / output_name(label, cell_id)
                if path.exists():
                    if cell_id in replace:
                        replaced.append(cell_id)
                        self.after(0, self.status_var.set, f"Cell {cell_id:03d}: replacing the old file")
                    elif is_complete_cell(path):
                        existing_files += 1
                        self.after(0, self.status_var.set, f"Cell {cell_id:03d}: existing file - skipped")
                        self.after(0, self.progress.configure, {"value": index})
                        continue
                    else:
                        rebuilt.append(cell_id)
                        self.after(0, self.status_var.set, f"Cell {cell_id:03d}: existing file is incomplete - rebuilding")

                def set_cell_status(text):
                    self.after(0, self.status_var.set, f"Cell {cell_id:03d}: {text}")

                set_cell_status("finding parcels...")
                ids, oid_field = query_object_ids_with_fallback(
                    url,
                    (w, e, s, n),
                    status_callback=set_cell_status,
                )
                if not ids:
                    if cell_id in replace:
                        # 2.1: the new layer has nothing here - remove the old layer's file too.
                        try:
                            path.unlink()
                        except OSError:
                            pass
                    empty_cells += 1
                    self.after(0, self.status_var.set, f"Cell {cell_id:03d}: EMPTY - skipped")
                    self.after(0, self.progress.configure, {"value": index})
                    continue

                set_cell_status(f"downloading {len(ids):,} parcels...")

                def feature_retry_status(next_attempt, total_attempts, exc):
                    set_cell_status(
                        f"download request failed ({exc}) - retry {next_attempt} of {total_attempts}..."
                    )

                features, missing = query_features_json(
                    url, ids, fields, precision, batch_size, retry_callback=feature_retry_status,
                    oid_field=oid_field or meta_oid, status_callback=set_cell_status,
                )
                if missing:
                    shortfalls.append((cell_id, len(missing), len(ids)))
                no_shape += sum(1 for f in features if f.get("geometry") is None)
                total_features += len(features)
                write_feature_collection(path, features, label, cell_id, (w, e, s, n), url)
                files_written += 1
                self.after(0, self.progress.configure, {"value": index})
            self.after(0, self._build_done, out_dir, total_features, files_written, existing_files, empty_cells,
                       rebuilt, shortfalls, no_shape, replaced)
        except Exception as exc:
            self.after(0, self._error, f"Build stopped:\n\n{exc}")

    def _build_done(self, out_dir, total_features, files_written, existing_files, empty_cells,
                    rebuilt=(), shortfalls=(), no_shape=0, replaced=()):
        self.set_busy(False)
        missing_total = sum(n for _, n, _ in shortfalls)
        # 2.1: the three cell counts are shown together so they visibly add up to 100; the parcel
        # count (which can run to many thousands) is a separate line.
        cells = files_written + existing_files + empty_cells
        self.status_var.set(
            f"Complete{' with warning' if shortfalls else ''}: {cells} cells - {files_written} written, "
            f"{existing_files} already there, {empty_cells} empty. {total_features:,} parcels written."
            + (f" {missing_total:,} parcels not returned by the service." if shortfalls else "")
        )
        text = (
            f"Complete.\n\n{cells} cells:\n"
            f"   {files_written} written\n"
            f"   {existing_files} already there (skipped)\n"
            f"   {empty_cells} empty - no parcels (skipped)\n\n"
            f"{total_features:,} parcels written into the {files_written} new file{'s' if files_written != 1 else ''}.\n\n"
            f"Folder:\n{out_dir}"
        )
        if replaced:
            text += ("\n\nReplaced old cell files from another layer or field list: " +
                     ", ".join(f"{c:03d}" for c in replaced) + ".")
        if no_shape:
            text += (f"\n\n{no_shape:,} parcel record(s) came from the service with no shape; they are in the "
                     "files with their fields but draw nothing.")
        if rebuilt:
            text += ("\n\nRebuilt incomplete cell files left by an interrupted build: " +
                     ", ".join(f"{c:03d}" for c in rebuilt) + ".")
        if shortfalls:
            lines = [f"  Cell {c:03d}: {n:,} of {total:,} parcels" for c, n, total in shortfalls[:12]]
            if len(shortfalls) > 12:
                lines.append(f"  ... and {len(shortfalls) - 12} more cells")
            text += ("\n\nWARNING: the service did not return some parcels, even after asking again. "
                     "These cells were written without them:\n" + "\n".join(lines) +
                     "\n\nTo try those cells again later, delete their files and build again.")
            messagebox.showwarning(APP_NAME, text)
        else:
            messagebox.showinfo(APP_NAME, text)

    def _error(self, message):
        self.set_busy(False)
        self.status_var.set("Stopped.")
        messagebox.showerror(APP_NAME, message)


def main():
    app = Parcel100App()
    app.mainloop()


if __name__ == "__main__":
    main()
