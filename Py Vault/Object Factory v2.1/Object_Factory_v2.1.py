#!/usr/bin/env python3
"""ArcGIS Earth Object Factory 2.1

v2.1 (2026-11-08) re-hardening - objects made from good input are byte-identical to 2.0:
  - batch lists saved by Excel as plain "CSV" (Windows-1252) or "Unicode Text" (UTF-16)
    are read; accented names no longer stop the list
  - in | lists a quote mark is just a character (a description starting with " used to
    swallow the rows after it without a word); comma lists keep normal CSV quoting
  - empty rows (only commas or | from Excel) are skipped
  - every number box says in plain words which box is wrong; nan, a scale of 0 or less
    and a Sky Compass radius of 0 or less are refused
  - default output folder = the Desktop Windows really shows (OneDrive-moved Desktops)
  - the window fits small laptop screens; a tab that does not fit gets a scroll bar
  - From Clipboard with no text on the clipboard says so in plain words

2.0 (= v1.3; 2.0 Reference (2026-11-08): the whole ArcGIS Earth Unlocked family moved to 2.0 as one reference point)

v1.3 (2026-11-06): one obvious file - the package shows Run_Object_Factory.bat and System Files
  (this program, its icons and the samples). Nothing else changed.

v1.2 adds "Hide above" (KML Region / LOD), Objects tab and Batch lists:
  - type the eye altitude in feet (as ArcGIS Earth shows it, "eye alt") above
    which the object disappears; blank = always visible (v1.1 behaviour)
  - the object (and its tether) is wrapped in a Folder with a 300 m Region CUBE
    (300 m tall, centred on the object's altitude) so it hides by distance in any
    direction: a flat box vanished edge-on at low altitude (Jim, 2026-11-02);
    minLodPixels = LOD_FT_PX / hide_above_ft (calibrated on Jim's screen 2026-11-02)
  - Popup Info with no Info text and no URL now shows the object name, so a click
    always opens something (v1.1 wrote no popup at all); Popup None is unchanged
  - outputs with no Hide above value are byte-identical to v1.1
  - Objects tab: Altitude is entered in feet (converted to metres in the KML;
    presets shown rounded to 10 ft); Batch lists keep alt_m
  - Objects tab and header squeezed so CREATE OBJECT KMZ fits on a maximised
    window

v1.1 hardening (object/KML generation, PNG normalization, presets, Sky Compass and
Beacon geometry unchanged from v1.0):
  - From Clipboard honors N/S/E/W letters and degrees-minutes-seconds, and reports
    exactly how it read the coordinate
  - asks before replacing an existing output file
  - outputs are built under a temporary name; a failed build keeps the old file
  - batch lists: header detected by real column names; errors name the line
  - unused ArcGIS Earth camera-coordinate code removed (clipboard is the method)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from xml.sax.saxutils import escape as xml_escape

APP = "ArcGIS Earth Object Factory"
VERSION = "2.1"
EARTH_R = 6371008.8
MAX_ICON_DIM = 256

# Hide above (v1.2). ArcGIS Earth shows a Region when its box covers at least
# minLodPixels on screen, so the cutoff altitude is inversely proportional to
# minLodPixels. Calibrated 2026-11-02 on Jim's PC (looking straight down): a
# 0.003 x 0.003 degree box at 30.62 N (309.6 m equivalent) disappears at
# altitude x minLodPixels between 1.44 and 2.38 million ft*px; geometric mean
# 1.85 million, scaled to the 300 m box used here.
LOD_BOX_M = 300.0
LOD_FT_PX = 1_790_000.0
FT_PER_M = 1 / 0.3048


def m_to_ft_display(m: float) -> str:
    """Preset altitude in feet, rounded to 10 ft, for the Objects tab."""
    return f"{round(m * FT_PER_M / 10) * 10:g}"

COLORS = {
    "Red": "ff0000ff",
    "Yellow": "ff00ffff",
    "Cyan": "ffffff00",
    "Green": "ff00ff00",
    "Magenta": "ffff00ff",
    "White": "ffffffff",
    "Orange": "ff0088ff",
}

PRESET_ALIASES = {
    "heli": "helicopter",
    "helicopter": "helicopter",
    "fuel": "fuel",
    "gas": "fuel",
    "gas_pump": "fuel",
    "bird": "bird",
    "hazard": "hazard",
    "warning": "hazard",
    "home": "home",
    "base": "home",
    "staging": "staging",
    "water": "water",
    "firetruck": "firetruck",
    "truck": "firetruck",
    "camera": "camera",
    "viewpoint": "camera",
    "medical": "medical",
    "hospital": "medical",
    "object": "object",
    "pin": "object",
}

PRESET_DEFAULTS = {
    "object":      {"alt": 150.0, "scale": 1.4},
    "helicopter":  {"alt": 300.0, "scale": 1.5},
    "fuel":        {"alt": 150.0, "scale": 1.4},
    "bird":        {"alt": 120.0, "scale": 1.4},
    "hazard":      {"alt": 200.0, "scale": 1.5},
    "home":        {"alt": 200.0, "scale": 1.5},
    "staging":     {"alt": 150.0, "scale": 1.5},
    "water":       {"alt": 150.0, "scale": 1.5},
    "firetruck":   {"alt": 150.0, "scale": 1.5},
    "camera":      {"alt": 180.0, "scale": 1.5},
    "medical":     {"alt": 180.0, "scale": 1.5},
}

FLOAT_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)")


def app_dir() -> Path:
    return Path(__file__).resolve().parent


def icon_dir() -> Path:
    return app_dir() / "icons"


def desktop_dir() -> Path:
    """The Desktop folder Windows really shows (it may have been moved into OneDrive).
    Falls back to <home>/Desktop."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class _GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]
            # FOLDERID_Desktop {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
            fid = _GUID(0xB4BFCC3A, 0xDB2C, 0x424C,
                        (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
            buf = ctypes.c_wchar_p()
            shell32 = ctypes.windll.shell32
            if shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(buf)) == 0:
                path = buf.value
                ctypes.windll.ole32.CoTaskMemFree(buf)
                if path and Path(path).is_dir():
                    return Path(path)
        except Exception:
            pass
    return Path.home() / "Desktop"


def read_list_text(path: Path) -> str:
    """Text of a batch list: UTF-8 (with or without BOM), UTF-16 (Excel 'Unicode Text'),
    else Windows-1252 (Excel's plain 'CSV' save), which can decode any byte."""
    data = Path(path).read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def gui_number(text: str, box: str, positive: bool = False, commas: bool = True) -> float:
    """A number typed in a window box, with a plain message naming the box.
    commas=True lets thousands separators through (1,500 ft); latitude/longitude use False."""
    s = str(text).strip()
    if commas:
        s = s.replace(",", "")
    try:
        n = float(s)
    except ValueError:
        shown = str(text).strip()
        raise ValueError(f"{box}: {shown!r} is not a number." if shown else f"{box} is empty - type a number.") from None
    if not math.isfinite(n):
        raise ValueError(f"{box}: {str(text).strip()!r} is not a usable number.")
    if positive and n <= 0:
        raise ValueError(f"{box} must be greater than zero.")
    return n


def _check_positive(value: float, what: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{what} must be greater than zero.")


def _check_finite(value: float, what: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{what} must be a usable number.")


def boolish(value, default=False) -> bool:
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def validate_lat_lon(lat: float, lon: float) -> tuple[float, float]:
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValueError("Coordinates must be finite numbers.")
    if not -90 <= lat <= 90:
        raise ValueError("Latitude must be between -90 and 90.")
    if not -180 <= lon <= 180:
        raise ValueError("Longitude must be between -180 and 180.")
    return lat, lon


# One coordinate value: optional hemisphere letter in front OR behind, optional sign,
# decimal degrees or degrees-minutes-seconds (30°24'03.5"N, 30 24.06' N, N30.4009, -81.93).
COORD_RE = re.compile(r"""
    (?<![A-Za-z])(?P<pre>[NSEWnsew])?\s*
    (?P<sign>[-+])?\s*
    (?P<deg>\d+(?:\.\d+)?|\.\d+)\s*[°º˚]?\s*
    (?:(?P<min>\d+(?:\.\d+)?)\s*['′’]\s*)?
    (?:(?P<sec>\d+(?:\.\d+)?)\s*(?:["″”]|'')\s*)?
    (?(pre)|(?P<post>[NSEWnsew])(?![A-Za-z]))?
    """, re.X)


def _coord_value(m) -> tuple[float, str | None]:
    """Signed decimal degrees and hemisphere letter (if any) for one COORD_RE match."""
    deg = float(m.group("deg"))
    minutes = float(m.group("min")) if m.group("min") else 0.0
    seconds = float(m.group("sec")) if m.group("sec") else 0.0
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"Minutes and seconds must be below 60: {m.group(0).strip()}")
    value = deg + minutes / 60.0 + seconds / 3600.0
    hemi = (m.group("pre") or m.group("post") or "").upper() or None
    sign = m.group("sign")
    if hemi:
        if (hemi in "SW" and sign == "+") or (hemi in "NE" and sign == "-"):
            raise ValueError(f"Sign and hemisphere letter disagree: {m.group(0).strip()}")
        value = -value if hemi in "SW" else value
    elif sign == "-":
        value = -value
    return value, hemi


def _readback(lat: float, lon: float, basis: str) -> str:
    return (f"Read as Latitude {abs(lat):.6f} {'N' if lat >= 0 else 'S'}, "
            f"Longitude {abs(lon):.6f} {'E' if lon >= 0 else 'W'} ({basis}). Check before creating.")


def parse_clipboard_coordinates(text: str, order: str = "Auto") -> tuple[float, float, str]:
    if not text or not text.strip():
        raise ValueError("The clipboard is empty.")
    source = text.strip()
    lat_match = re.search(r"\b(?:lat|latitude)\b\s*[:=]?\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))", source, re.I)
    lon_match = re.search(r"\b(?:lon|lng|long|longitude)\b\s*[:=]?\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))", source, re.I)
    if lat_match and lon_match:
        lat, lon = float(lat_match.group(1)), float(lon_match.group(1))
        validate_lat_lon(lat, lon)
        return lat, lon, _readback(lat, lon, "labelled lat/lon")

    found = [m for m in COORD_RE.finditer(source) if m.group("deg")]
    values = [_coord_value(m) for m in found]
    lettered = [(v, h) for v, h in values if h]
    if len(lettered) == 2:
        values = lettered          # extra numbers around a lettered pair are ignored
    elif len(values) != 2:
        if len(values) < 2:
            raise ValueError("Could not find a coordinate pair in the clipboard. "
                             "Copy one latitude, longitude pair (e.g. 30.40098, -81.93471).")
        raise ValueError(f"The clipboard holds {len(values)} numbers, not one coordinate pair. "
                         "Copy just the latitude, longitude pair (e.g. 30.40098, -81.93471).")

    (a, ha), (b, hb) = values
    if ha or hb:
        # Hemisphere letters decide which value is which, in either order.
        roles = {}
        for value, hemi, other in ((a, ha, b), (b, hb, a)):
            if hemi:
                role = "lat" if hemi in "NS" else "lon"
                if role in roles:
                    raise ValueError("The clipboard has two " + ("latitudes (N/S)." if role == "lat" else "longitudes (E/W)."))
                roles[role] = value
        if "lat" not in roles:
            roles["lat"] = a if roles["lon"] is b else b
        if "lon" not in roles:
            roles["lon"] = a if roles["lat"] is b else b
        lat, lon = roles["lat"], roles["lon"]
        validate_lat_lon(lat, lon)
        return lat, lon, _readback(lat, lon, "N/S/E/W letters")

    if order == "Lat, Lon":
        validate_lat_lon(a, b); return a, b, _readback(a, b, "latitude first")
    if order == "Lon, Lat":
        validate_lat_lon(b, a); return b, a, _readback(b, a, "longitude first")
    if not (-180 <= a <= 180 and -180 <= b <= 180):
        raise ValueError("Clipboard coordinates are outside the valid longitude range.")
    if not -90 <= a <= 90 and -90 <= b <= 90:
        validate_lat_lon(b, a); return b, a, _readback(b, a, "longitude first - the first value is beyond 90")
    validate_lat_lon(a, b)
    return a, b, _readback(a, b, "latitude first, the Google Maps order")


def preset_key(value: str) -> str:
    raw = (value or "object").strip().lower().replace(" ", "_")
    return PRESET_ALIASES.get(raw, raw if raw in PRESET_DEFAULTS else "object")


def preset_icon(value: str) -> Path:
    key = preset_key(value)
    p = icon_dir() / f"{key}.png"
    if p.exists():
        return p
    return icon_dir() / "object.png"


def png_info(path: Path, master=None) -> tuple[int, int, int, bool]:
    p = Path(path)
    if p.suffix.lower() != ".png":
        raise ValueError("Object Factory accepts PNG icons only.")
    if not p.is_file():
        raise FileNotFoundError(p)
    im = tk.PhotoImage(master=master, file=str(p))
    return im.width(), im.height(), p.stat().st_size, True


def normalize_png(source: Path, dest: Path, master=None, max_dim: int = MAX_ICON_DIM) -> dict:
    """Standard-library/Tk normalization. Original file is never modified.

    Tk PhotoImage preserves PNG transparency. If a source is over max_dim, use integer
    subsampling so the packaged working copy is <= max_dim while preserving aspect ratio.
    Smaller sources are copied unchanged and are never upscaled.
    """
    source, dest = Path(source), Path(dest)
    if source.suffix.lower() != ".png":
        raise ValueError(f"PNG required: {source.name}")
    if not source.is_file():
        raise FileNotFoundError(source)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im = tk.PhotoImage(master=master, file=str(source))
    w, h = im.width(), im.height()
    if w <= 0 or h <= 0:
        raise ValueError(f"Invalid PNG dimensions: {source}")
    factor = max(1, math.ceil(max(w, h) / max_dim))
    if factor == 1:
        shutil.copy2(source, dest)
        out_w, out_h = w, h
    else:
        small = im.subsample(factor, factor)
        small.write(str(dest), format="png")
        out_w, out_h = small.width(), small.height()
    return {"source_w": w, "source_h": h, "out_w": out_w, "out_h": out_h, "factor": factor}


class _SafeOutput:
    """Write to "<name>.partial" and replace the real file only when writing succeeded,
    so a failed build never destroys the previous output or leaves a broken one."""
    def __init__(self, path: Path):
        self.path = Path(path)
        self.partial = self.path.with_name(self.path.name + ".partial")

    def __enter__(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return self.partial

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            os.replace(self.partial, self.path)
        else:
            try:
                self.partial.unlink()
            except OSError:
                pass
        return False


def output_path_for(path, suffix: str) -> Path:
    """The exact file a create_* function will write (suffix normalized)."""
    path = Path(path)
    return path if path.suffix.lower() == suffix else path.with_suffix(suffix)


def description_html(description: str, url: str = "", link_text: str = "OPEN LINK") -> str:
    parts = []
    if description and description.strip():
        for line in description.strip().splitlines():
            parts.append(html.escape(line))
        body = "<br/>".join(parts)
    else:
        body = ""
    if url and url.strip():
        link = f'<a href="{html.escape(url.strip(), quote=True)}">{html.escape((link_text or "OPEN LINK").strip())}</a>'
        body = f"{body}<br/><br/>{link}" if body else link
    return body


def object_style(style_id: str, icon_href: str, scale: float, show_label: bool, popup_mode: str) -> str:
    label_scale = "1.0" if show_label else "0.0"
    balloon = "<BalloonStyle><displayMode>hide</displayMode></BalloonStyle>" if popup_mode.lower() == "none" else ""
    return f'''  <Style id="{style_id}">
    <IconStyle><scale>{scale:g}</scale><Icon><href>{xml_escape(icon_href)}</href></Icon></IconStyle>
    <LabelStyle><scale>{label_scale}</scale></LabelStyle>
    {balloon}
  </Style>'''


def parse_hide_above(value, where: str = "Hide above") -> float | None:
    """Blank/0 = always visible (None); otherwise a positive number of feet."""
    s = str(value if value is not None else "").strip().replace(",", "")
    if s == "" or s == "0":
        return None
    try:
        ft = float(s)
    except ValueError:
        raise ValueError(f"{where}: {str(value).strip()!r} is not a number of feet (leave blank for always visible).") from None
    if not math.isfinite(ft) or ft <= 0:
        raise ValueError(f"{where}: must be a positive number of feet (leave blank for always visible).")
    return ft


def lod_pixels_for(hide_above_ft: float) -> int:
    return max(1, int(round(LOD_FT_PX / hide_above_ft)))


def lod_region(lat: float, lon: float, hide_above_ft: float, altitude_m: float = 0.0,
               altitude_mode: str = "relativeToGround") -> str:
    half = LOD_BOX_M / 2.0
    if altitude_mode == "absolute":
        bottom, box_mode = altitude_m - half, "absolute"
    else:
        bottom = 0.0 if altitude_mode == "clampToGround" else max(0.0, altitude_m - half)
        box_mode = "relativeToGround"
    dlat = math.degrees(half / EARTH_R)
    dlon = math.degrees(half / (EARTH_R * max(math.cos(math.radians(lat)), 0.01)))
    north, south = min(lat + dlat, 90.0), max(lat - dlat, -90.0)
    return (f"    <Region><LatLonAltBox><north>{north:.8f}</north><south>{south:.8f}</south>"
            f"<east>{lon + dlon:.8f}</east><west>{lon - dlon:.8f}</west>"
            f"<minAltitude>{bottom:.1f}</minAltitude><maxAltitude>{bottom + LOD_BOX_M:.1f}</maxAltitude>"
            f"<altitudeMode>{box_mode}</altitudeMode></LatLonAltBox>\n"
            f"      <Lod><minLodPixels>{lod_pixels_for(hide_above_ft)}</minLodPixels><maxLodPixels>-1</maxLodPixels></Lod></Region>")


def object_placemark(name: str, lat: float, lon: float, altitude_m: float, style_id: str,
                     altitude_mode: str = "relativeToGround", description: str = "", url: str = "",
                     link_text: str = "OPEN LINK", tether: bool = False, popup_mode: str = "Info",
                     hide_above_ft: float | None = None) -> str:
    validate_lat_lon(lat, lon)
    if altitude_mode not in {"relativeToGround", "absolute", "clampToGround"}:
        raise ValueError(f"Unsupported altitude mode: {altitude_mode}")
    safe_name = xml_escape(name.strip() or "Object")
    desc = ""
    if popup_mode.lower() != "none":
        body = description_html(description, url, link_text) or html.escape(name.strip() or "Object")
        if body:
            desc = f"\n    <description><![CDATA[{body}]]></description>"
    if altitude_mode == "clampToGround":
        coord_alt = 0
    else:
        coord_alt = altitude_m
    tether_kml = ""
    if tether and altitude_mode != "clampToGround":
        tether_kml = f'''
  <Placemark>
    <name>{safe_name} tether</name>
    <Style><LineStyle><color>ff4040ff</color><width>2</width></LineStyle><LabelStyle><scale>0</scale></LabelStyle><BalloonStyle><displayMode>hide</displayMode></BalloonStyle></Style>
    <LineString><altitudeMode>{altitude_mode}</altitudeMode><coordinates>{lon},{lat},0 {lon},{lat},{altitude_m}</coordinates></LineString>
  </Placemark>'''
    pm = f'''  <Placemark>
    <name>{safe_name}</name>
    <styleUrl>#{style_id}</styleUrl>{desc}
    <Point><altitudeMode>{altitude_mode}</altitudeMode><coordinates>{lon},{lat},{coord_alt}</coordinates></Point>
  </Placemark>'''
    if hide_above_ft:
        return (f"  <Folder>\n    <name>{safe_name}</name>\n{lod_region(lat, lon, hide_above_ft, altitude_m, altitude_mode)}\n"
                f"{pm}{tether_kml}\n  </Folder>")
    return pm + tether_kml


def create_single_object_kmz(output_path: Path, icon_path: Path, name: str, lat: float, lon: float,
                             altitude_m: float, scale: float, altitude_mode: str, description: str,
                             url: str, link_text: str, tether: bool, show_label: bool, popup_mode: str,
                             master=None, hide_above_ft: float | None = None) -> Path:
    _check_finite(altitude_m, "Altitude")
    _check_positive(scale, "Icon scale")
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".kmz":
        output_path = output_path.with_suffix(".kmz")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        norm = td / "icon.png"
        normalize_png(icon_path, norm, master=master)
        style = object_style("objectStyle", "icons/icon.png", scale, show_label, popup_mode)
        pm = object_placemark(name, lat, lon, altitude_m, "objectStyle", altitude_mode,
                              description, url, link_text, tether, popup_mode, hide_above_ft)
        kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>{xml_escape(name.strip() or "Object")}</name>
{style}
{pm}
</Document>
</kml>'''
        with _SafeOutput(output_path) as tmp, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("doc.kml", kml)
            z.write(norm, "icons/icon.png")
    return output_path


ALTITUDE_MODES = {"relativeToGround", "absolute", "clampToGround"}


def _number(value, what: str, where: str) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{where}: {what} {str(value).strip()!r} is not a number.") from None
    if not math.isfinite(n):
        raise ValueError(f"{where}: {what} {str(value).strip()!r} is not a usable number.")
    return n


def _check_row(r: dict, where: str) -> None:
    try:
        validate_lat_lon(r["lat"], r["lon"])
    except ValueError as e:
        raise ValueError(f"{where}: {e}") from None
    if r["scale"] <= 0:
        raise ValueError(f"{where}: scale must be greater than zero (found {r['scale']:g}).")
    if r["altitude_mode"] not in ALTITUDE_MODES:
        raise ValueError(f"{where}: altitude_mode must be relativeToGround, absolute or clampToGround "
                         f"(found {r['altitude_mode']!r}).")


def _is_header(line: str) -> bool:
    """A header line names its columns; it must contain 'lat' and 'lon' as whole fields."""
    delim = "|" if "|" in line else ","
    fields = {f.strip().lower() for f in line.split(delim)}
    return "lat" in fields and "lon" in fields


def parse_batch_rows(path: Path) -> list[dict]:
    path = Path(path)
    # v2.1: Excel encodings; rows of only commas/| (Excel's emptied rows) are blank.
    numbered = [(n, ln) for n, ln in enumerate(read_list_text(path).splitlines(), start=1)
                if ln.strip(" \t,|;") and not ln.lstrip().startswith("#")]
    if not numbered:
        return []
    lines = [ln for _, ln in numbered]
    has_header = _is_header(lines[0])
    rows = []
    if has_header:
        delim = "|" if "|" in lines[0] else ","
        # v2.1: in | lists a quote mark is just a character (a leading " used to swallow the
        # following rows); comma lists keep CSV quoting, which Excel uses for commas in a cell.
        quoting = csv.QUOTE_NONE if delim == "|" else csv.QUOTE_MINIMAL
        reader = csv.DictReader(lines, delimiter=delim, quoting=quoting)
        prev_num = 1
        for row in reader:
            # reader.line_num counts list items read, so it maps back to the real file line.
            if reader.line_num - prev_num > 1:
                first = numbered[prev_num][0]
                raise ValueError(f"Line {first}: a quote mark (\") opens a cell that does not close on "
                                 "that line, so the lines after it would be lost. Remove the quote mark "
                                 "or close it on the same line.")
            prev_num = reader.line_num
            line_no = numbered[min(reader.line_num, len(numbered)) - 1][0]
            clean = {str(k).strip().lower(): (v.strip() if v else "") for k, v in row.items() if k}
            typ = clean.get("type", "object") or "object"
            key = preset_key(typ)
            defaults = PRESET_DEFAULTS.get(key, PRESET_DEFAULTS["object"])
            name = clean.get("name") or key.replace("_", " ").title()
            where = f"Line {line_no} ({name})"
            if not clean.get("lat") or not clean.get("lon"):
                raise ValueError(f"{where}: latitude and longitude are required.")
            r = {
                "type": key,
                "name": name,
                "lat": _number(clean["lat"], "latitude", where),
                "lon": _number(clean["lon"], "longitude", where),
                "alt_m": _number(clean.get("alt_m") or clean.get("alt") or defaults["alt"], "alt_m", where),
                "icon": clean.get("icon", ""),
                "description": clean.get("description", ""),
                "url": clean.get("url", ""),
                "link_text": clean.get("link_text", "OPEN LINK") or "OPEN LINK",
                "scale": _number(clean.get("scale") or defaults["scale"], "scale", where),
                "altitude_mode": clean.get("altitude_mode", "relativeToGround") or "relativeToGround",
                "tether": boolish(clean.get("tether"), False),
                "popup": clean.get("popup", "Info") or "Info",
                "label": boolish(clean.get("label"), False),
                "hide_above_ft": parse_hide_above(clean.get("hide_above_ft", ""), f"{where}: hide_above_ft"),
            }
            _check_row(r, where)
            rows.append(r)
    else:
        # Simple shorthand: type,lat,lon[,alt_m][,name]
        for line_no, ln in numbered:
            where = f"Line {line_no}"
            delim = "|" if "|" in ln else ","
            parts = [p.strip() for p in ln.split(delim)]
            if len(parts) < 3:
                raise ValueError(f"{where}: shorthand requires type,lat,lon[,alt_m][,name].")
            typ = parts[0]
            key = preset_key(typ)
            defaults = PRESET_DEFAULTS.get(key, PRESET_DEFAULTS["object"])
            lat = _number(parts[1], "latitude", where)
            lon = _number(parts[2], "longitude", where)
            alt = _number(parts[3], "alt_m", where) if len(parts) >= 4 and parts[3] else defaults["alt"]
            name = parts[4] if len(parts) >= 5 and parts[4] else key.replace("_", " ").title()
            r = {
                "type": key, "name": name, "lat": lat, "lon": lon, "alt_m": alt,
                "icon": "", "description": "", "url": "", "link_text": "OPEN LINK",
                "scale": defaults["scale"], "altitude_mode": "relativeToGround",
                "tether": False, "popup": "Info", "label": False, "hide_above_ft": None,
            }
            _check_row(r, f"{where} ({name})")
            rows.append(r)
    return rows


def resolve_row_icon(row: dict, list_path: Path) -> Path:
    if row.get("icon"):
        p = Path(row["icon"])
        if not p.is_absolute():
            p = Path(list_path).parent / p
        return p
    return preset_icon(row.get("type", "object"))


def create_batch_kmz(list_path: Path, output_path: Path, master=None) -> tuple[Path, int]:
    rows = parse_batch_rows(list_path)
    if not rows:
        raise ValueError("Object list is empty.")
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".kmz":
        output_path = output_path.with_suffix(".kmz")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        asset_by_key = {}
        asset_files = {}
        styles = []
        placemarks = []
        for i, row in enumerate(rows, start=1):
            src = resolve_row_icon(row, list_path)
            if src.suffix.lower() != ".png":
                raise ValueError(f"{row['name']}: icon must be PNG ({src})")
            if not src.exists():
                raise FileNotFoundError(f"{row['name']}: icon not found: {src}")
            key = str(src.resolve()).lower()
            if key not in asset_by_key:
                digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]
                arc = f"icons/{len(asset_by_key)+1:03d}_{src.stem}_{digest}.png"
                norm = td / Path(arc).name
                normalize_png(src, norm, master=master)
                asset_by_key[key] = arc
                asset_files[arc] = norm
            arc = asset_by_key[key]
            sid = f"s{i}"
            styles.append(object_style(sid, arc, row["scale"], row["label"], row["popup"]))
            placemarks.append(object_placemark(row["name"], row["lat"], row["lon"], row["alt_m"], sid,
                                               row["altitude_mode"], row["description"], row["url"],
                                               row["link_text"], row["tether"], row["popup"],
                                               row.get("hide_above_ft")))
        docname = xml_escape(Path(list_path).stem)
        kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>{docname}</name>
{chr(10).join(styles)}
{chr(10).join(placemarks)}
</Document>
</kml>'''
        with _SafeOutput(output_path) as tmp, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("doc.kml", kml)
            for arc, norm in asset_files.items():
                z.write(norm, arc)
    return output_path, len(rows)


def destination(lat_deg: float, lon_deg: float, bearing_deg: float, distance_m: float) -> tuple[float, float]:
    lat, lon, br = math.radians(lat_deg), math.radians(lon_deg), math.radians(bearing_deg)
    a = distance_m / EARTH_R
    lat2 = math.asin(math.sin(lat)*math.cos(a) + math.cos(lat)*math.sin(a)*math.cos(br))
    lon2 = lon + math.atan2(math.sin(br)*math.sin(a)*math.cos(lat), math.cos(a)-math.sin(lat)*math.sin(lat2))
    lon2 = (lon2 + 3*math.pi) % (2*math.pi) - math.pi
    return math.degrees(lat2), math.degrees(lon2)


def create_sky_compass_kmz(output_path: Path, center_lat: float, center_lon: float, radius_km: float,
                           altitude_m: float, icon_scale: float) -> Path:
    validate_lat_lon(center_lat, center_lon)
    _check_positive(radius_km, "Radius (km)")
    _check_finite(altitude_m, "Altitude AGL (m)")
    _check_positive(icon_scale, "Icon scale")
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".kmz":
        output_path = output_path.with_suffix(".kmz")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    defs = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
    missing = [f"{letter}.png" for letter, _ in defs if not (icon_dir() / f"{letter}.png").exists()]
    if missing:
        raise FileNotFoundError(f"Sky Compass icon(s) missing from {icon_dir()}: {', '.join(missing)}")
    styles, pms = [], []
    for i, (letter, bearing) in enumerate(defs, start=1):
        lat, lon = destination(center_lat, center_lon, bearing, radius_km*1000)
        arc = f"icons/{letter}.png"
        sid = f"s{i}"
        styles.append(object_style(sid, arc, icon_scale, False, "Info"))
        pms.append(object_placemark(letter, lat, lon, altitude_m, sid, "relativeToGround",
                                    f"{letter} sky compass marker; {radius_km:g} km from center.", "", "", False, "Info"))
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document><name>Sky Compass</name>
{chr(10).join(styles)}
{chr(10).join(pms)}
</Document></kml>'''
    with _SafeOutput(output_path) as tmp, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)
        for letter, _ in defs:
            src = icon_dir() / f"{letter}.png"
            if not src.exists():
                raise FileNotFoundError(src)
            z.write(src, f"icons/{letter}.png")
    return output_path


def build_beacon_kml(name: str, lat: float, lon: float, height_m: float, width: float, color_kml: str) -> str:
    validate_lat_lon(lat, lon)
    if not math.isfinite(height_m) or height_m <= 0:
        raise ValueError("Beacon height must be greater than zero.")
    if not math.isfinite(width) or width <= 0:
        raise ValueError("Line width must be greater than zero.")
    safe_name = xml_escape(name.strip() or "EarthStick Beacon")
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{safe_name}</name>
    <Style id="beaconStyle">
      <LineStyle><color>{color_kml}</color><width>{width:g}</width></LineStyle>
      <IconStyle><scale>1.1</scale></IconStyle>
    </Style>
    <Placemark>
      <name>{safe_name}</name>
      <styleUrl>#beaconStyle</styleUrl>
      <MultiGeometry>
        <Point><altitudeMode>relativeToGround</altitudeMode><coordinates>{lon:.8f},{lat:.8f},0</coordinates></Point>
        <LineString><tessellate>0</tessellate><altitudeMode>relativeToGround</altitudeMode><coordinates>
          {lon:.8f},{lat:.8f},0
          {lon:.8f},{lat:.8f},{height_m:.3f}
        </coordinates></LineString>
      </MultiGeometry>
    </Placemark>
  </Document>
</kml>
'''


def create_beacon_kml(output_path: Path, name: str, lat: float, lon: float, height_km: float, width: float, color_name: str) -> Path:
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".kml":
        output_path = output_path.with_suffix(".kml")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    kml = build_beacon_kml(name, lat, lon, height_km*1000.0, width, COLORS[color_name])
    with _SafeOutput(output_path) as tmp:
        tmp.write_text(kml, encoding="utf-8")
    return output_path


def open_path(path: Path):
    try:
        if os.name == "nt":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}" >/dev/null 2>&1 &')
    except Exception:
        pass


class CoordinateMixin:
    def clipboard_coords(self, lat_var, lon_var, status_var, order="Auto"):
        try:
            try:
                text = self.clipboard_get()
            except tk.TclError:
                raise ValueError("The clipboard has no text. Copy a latitude, longitude pair first "
                                 "(Google Maps: right-click the spot and click the numbers).") from None
            lat, lon, msg = parse_clipboard_coordinates(text, order)
            lat_var.set(f"{lat:.12f}".rstrip("0").rstrip("."))
            lon_var.set(f"{lon:.12f}".rstrip("0").rstrip("."))
            status_var.set(msg)
        except Exception as e:
            messagebox.showerror(APP, str(e))


class ObjectFactory(tk.Tk, CoordinateMixin):
    def _ok_to_write(self, path, suffix: str) -> bool:
        target = output_path_for(path, suffix)
        if not target.exists():
            return True
        return messagebox.askyesno(APP, f"{target.name} already exists in\n{target.parent}\n\nReplace it?",
                                   icon="warning", default="no")

    def __init__(self, smoke_test=False):
        super().__init__()
        self.title(f"{APP} {VERSION}")
        # v2.1: fit small laptop screens (taskbar + title bar ~110 px); tabs scroll if needed.
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(980, sw - 40), min(790, sh - 110)
        if h < 790:
            self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+0")
        else:
            self.geometry(f"{w}x{h}")
        self.minsize(min(900, w), min(480, h))
        self.status = tk.StringVar(value=f"Factory ready. Object Factory v{VERSION} for ArcGIS Earth.")
        self.preview_image = None
        self._build_ui()
        if smoke_test:
            self.after(1000, self.destroy)

    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text="ArcGIS Earth Object Factory", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(header, text=f"v{VERSION}", font=("Segoe UI", 10)).pack(side="left", padx=(8,0), pady=(6,0))
        ttk.Label(header, text="Create geographic objects without hand-writing KML. Original PNG files are never modified.").pack(side="left", padx=(18,0), pady=(6,0))
        ttk.Frame(root, height=4).pack(fill="x")
        style = ttk.Style(self)
        style.configure("Factory.TNotebook.Tab", font=("Segoe UI", 12, "bold"), foreground="#005EA8", padding=(16, 5))
        style.map("Factory.TNotebook.Tab", foreground=[("selected", "#003B73"), ("active", "#004F8C")])
        self.nb = ttk.Notebook(root, style="Factory.TNotebook")
        self.nb.pack(fill="both", expand=True)
        self.object_tab = self._scroll_tab("Objects", (10, 6))
        self.batch_tab = self._scroll_tab("Batch", 10)
        self.compass_tab = self._scroll_tab("Sky Compass", 10)
        self.beacon_tab = self._scroll_tab("Beacon", 10)
        self._build_object_tab()
        self._build_batch_tab()
        self._build_compass_tab()
        self._build_beacon_tab()
        ttk.Separator(root).pack(fill="x", pady=(4,3))
        ttk.Label(root, textvariable=self.status, wraplength=930).pack(anchor="w")

    def _scroll_tab(self, title, padding):
        """v2.1: a notebook tab whose content scrolls when the window is too short for it.
        On a screen tall enough the tab looks exactly as before (no scroll bar)."""
        outer = ttk.Frame(self.nb)
        self.nb.add(outer, text=title)
        bg = ttk.Style(self).lookup("TFrame", "background") or self.cget("background")
        canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0, background=bg)
        bar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas, padding=padding)
        win = canvas.create_window(0, 0, window=inner, anchor="nw")
        state = {"bar": False}

        def refit(_evt=None):
            need = inner.winfo_reqheight()
            have = canvas.winfo_height()
            canvas.itemconfigure(win, width=canvas.winfo_width(), height=max(need, have))
            canvas.configure(scrollregion=(0, 0, canvas.winfo_width(), max(need, have)))
            show = need > have > 1
            if show != state["bar"]:
                state["bar"] = show
                if show:
                    bar.pack(side="right", fill="y", before=canvas)
                else:
                    bar.pack_forget()
                    canvas.yview_moveto(0)

        def wheel(evt):
            if state["bar"]:
                canvas.yview_scroll(int(-evt.delta / 120) or (-1 if evt.delta > 0 else 1), "units")

        canvas.bind("<Configure>", refit)
        inner.bind("<Configure>", refit)
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        return inner

    def _coord_buttons(self, parent, row, latv, lonv, statusv):
        f = ttk.Frame(parent)
        f.grid(row=row, column=1, columnspan=3, sticky="w", pady=(2,6))
        ttk.Button(f, text="From Clipboard", command=lambda:self.clipboard_coords(latv, lonv, statusv)).pack(side="left")

    def _build_object_tab(self):
        t = self.object_tab
        t.columnconfigure(1, weight=1); t.columnconfigure(3, weight=1)
        self.ov = {
            "preset": tk.StringVar(value="object"), "name": tk.StringVar(value="Airborne Object"),
            "lat": tk.StringVar(value="30.385524823620624"), "lon": tk.StringVar(value="-81.93080672778036"),
            "alt": tk.StringVar(value=m_to_ft_display(150)), "scale": tk.StringVar(value="1.4"),
            "mode": tk.StringVar(value="relativeToGround"), "icon": tk.StringVar(value=str(preset_icon("object"))),
            "popup": tk.StringVar(value="Info"), "link_text": tk.StringVar(value="OPEN LINK"), "url": tk.StringVar(),
            "tether": tk.BooleanVar(value=False), "label": tk.BooleanVar(value=False), "hide": tk.StringVar(value=""),
            "out": tk.StringVar(value=str(desktop_dir()/"ArcGIS_Earth_Object.kmz")),
            "png_info": tk.StringVar(value="Select a PNG. Packaged copy will be <=256 px; original remains untouched."),
            "coord_status": tk.StringVar(value="Enter coordinates manually or use From Clipboard."),
        }
        r=0
        ttk.Label(t,text="Single Object",font=("Segoe UI",13,"bold")).grid(row=r,column=0,columnspan=4,sticky="w",pady=(0,2));r+=1
        ttk.Label(t,text="Preset").grid(row=r,column=0,sticky="w",padx=(0,8),pady=3)
        presets=["object","helicopter","fuel","bird","hazard","home","staging","water","firetruck","camera","medical"]
        cb=ttk.Combobox(t,textvariable=self.ov["preset"],values=presets,state="readonly");cb.grid(row=r,column=1,sticky="ew",pady=3);cb.bind("<<ComboboxSelected>>",self.on_preset)
        ttk.Label(t,text="Object name").grid(row=r,column=2,sticky="w",padx=(16,8),pady=3);ttk.Entry(t,textvariable=self.ov["name"]).grid(row=r,column=3,sticky="ew",pady=3);r+=1
        ttk.Label(t,text="Latitude").grid(row=r,column=0,sticky="w",padx=(0,8),pady=3);ttk.Entry(t,textvariable=self.ov["lat"]).grid(row=r,column=1,sticky="ew",pady=3)
        ttk.Label(t,text="Longitude").grid(row=r,column=2,sticky="w",padx=(16,8),pady=3);ttk.Entry(t,textvariable=self.ov["lon"]).grid(row=r,column=3,sticky="ew",pady=3);r+=1
        self._coord_buttons(t,r,self.ov["lat"],self.ov["lon"],self.ov["coord_status"]);r+=1
        ttk.Label(t,textvariable=self.ov["coord_status"],foreground="#555").grid(row=r,column=1,columnspan=3,sticky="w",pady=(0,2));r+=1
        ttk.Label(t,text="PNG icon").grid(row=r,column=0,sticky="w",padx=(0,8),pady=3);ttk.Entry(t,textvariable=self.ov["icon"]).grid(row=r,column=1,columnspan=2,sticky="ew",pady=3);ttk.Button(t,text="Browse",command=self.pick_icon).grid(row=r,column=3,sticky="e",pady=3);r+=1
        infof=ttk.Frame(t); infof.grid(row=r,column=1,columnspan=3,sticky="ew",pady=(0,3)); infof.columnconfigure(1,weight=1)
        self.preview_label=ttk.Label(infof);self.preview_label.grid(row=0,column=0,rowspan=2,padx=(0,10))
        ttk.Label(infof,text="PNG inspection",font=("Segoe UI",10,"bold")).grid(row=0,column=1,sticky="w")
        ttk.Label(infof,textvariable=self.ov["png_info"],wraplength=650).grid(row=1,column=1,sticky="w")
        self.after(100,self.refresh_png_info);r+=1
        ttk.Label(t,text="Altitude (ft)").grid(row=r,column=0,sticky="w",padx=(0,8),pady=3);ttk.Entry(t,textvariable=self.ov["alt"]).grid(row=r,column=1,sticky="ew",pady=3)
        ttk.Label(t,text="Altitude mode").grid(row=r,column=2,sticky="w",padx=(16,8),pady=3);ttk.Combobox(t,textvariable=self.ov["mode"],values=("relativeToGround","absolute","clampToGround"),state="readonly").grid(row=r,column=3,sticky="ew",pady=3);r+=1
        ttk.Label(t,text="Icon scale").grid(row=r,column=0,sticky="w",padx=(0,8),pady=3);ttk.Entry(t,textvariable=self.ov["scale"]).grid(row=r,column=1,sticky="ew",pady=3)
        ttk.Label(t,text="Popup").grid(row=r,column=2,sticky="w",padx=(16,8),pady=3);ttk.Combobox(t,textvariable=self.ov["popup"],values=("Info","None"),state="readonly").grid(row=r,column=3,sticky="ew",pady=3);r+=1
        ttk.Label(t,text="Hide above (ft)").grid(row=r,column=0,sticky="w",padx=(0,8),pady=3);ttk.Entry(t,textvariable=self.ov["hide"]).grid(row=r,column=1,sticky="ew",pady=3)
        ttk.Label(t,text="Eye alt in feet, as ArcGIS Earth shows it. Blank = always visible.",foreground="#555").grid(row=r,column=2,columnspan=2,sticky="w",padx=(16,0),pady=3);r+=1
        flags=ttk.Frame(t);flags.grid(row=r,column=1,columnspan=3,sticky="w",pady=3);ttk.Checkbutton(flags,text="Show tether",variable=self.ov["tether"]).pack(side="left",padx=(0,18));ttk.Checkbutton(flags,text="Show label",variable=self.ov["label"]).pack(side="left");r+=1
        ttk.Label(t,text="Info text").grid(row=r,column=0,sticky="nw",padx=(0,8),pady=3);self.object_desc=tk.Text(t,height=2,wrap="word");self.object_desc.grid(row=r,column=1,columnspan=3,sticky="ew",pady=3);r+=1
        ttk.Label(t,text="Link text").grid(row=r,column=0,sticky="w",padx=(0,8),pady=3);ttk.Entry(t,textvariable=self.ov["link_text"]).grid(row=r,column=1,sticky="ew",pady=3)
        ttk.Label(t,text="URL").grid(row=r,column=2,sticky="w",padx=(16,8),pady=3);ttk.Entry(t,textvariable=self.ov["url"]).grid(row=r,column=3,sticky="ew",pady=3);r+=1
        ttk.Label(t,text="Output KMZ").grid(row=r,column=0,sticky="w",padx=(0,8),pady=3);ttk.Entry(t,textvariable=self.ov["out"]).grid(row=r,column=1,columnspan=2,sticky="ew",pady=3);ttk.Button(t,text="Browse",command=self.pick_object_out).grid(row=r,column=3,sticky="e",pady=3);r+=1
        outf=ttk.Frame(t);outf.grid(row=r,column=0,columnspan=4,sticky="ew",pady=(6,2));outf.columnconfigure(0,weight=1);ttk.Button(outf,text="CREATE OBJECT KMZ",command=self.create_object).grid(row=0,column=0,sticky="e",ipadx=20,ipady=5)

    def on_preset(self,_evt=None):
        key=preset_key(self.ov["preset"].get());d=PRESET_DEFAULTS.get(key,PRESET_DEFAULTS["object"]);self.ov["icon"].set(str(preset_icon(key)));self.ov["alt"].set(m_to_ft_display(d['alt']));self.ov["scale"].set(f"{d['scale']:g}");self.refresh_png_info()

    def pick_icon(self):
        p=filedialog.askopenfilename(filetypes=[("PNG image","*.png")]);
        if p:self.ov["icon"].set(p);self.refresh_png_info()

    def refresh_png_info(self):
        try:
            p=Path(self.ov["icon"].get());im=tk.PhotoImage(master=self,file=str(p));w,h=im.width(),im.height();size=p.stat().st_size
            factor=max(1,math.ceil(max(w,h)/MAX_ICON_DIM));ow=math.ceil(w/factor);oh=math.ceil(h/factor)
            status="Excellent" if max(w,h)<=256 else "Will normalize for KMZ"
            self.ov["png_info"].set(f"{p.name} — {w}×{h}px — {size/1024:.1f} KB — transparency preserved — {status}. Packaged copy ≈ {ow}×{oh}px; source untouched.")
            prev=im
            pf=max(1,math.ceil(max(w,h)/72));
            if pf>1:prev=im.subsample(pf,pf)
            self.preview_image=prev;self.preview_label.configure(image=prev)
        except Exception as e:
            self.ov["png_info"].set(f"PNG not ready: {e}");self.preview_label.configure(image="");self.preview_image=None

    def pick_object_out(self):
        p=filedialog.asksaveasfilename(defaultextension=".kmz",filetypes=[("KMZ","*.kmz")]);
        if p:self.ov["out"].set(p)

    def create_object(self):
        try:
            if not self._ok_to_write(self.ov["out"].get(), ".kmz"):
                self.status.set("Not created - existing file kept."); return
            p=create_single_object_kmz(Path(self.ov["out"].get()),Path(self.ov["icon"].get()),self.ov["name"].get(),gui_number(self.ov["lat"].get(),"Latitude",commas=False),gui_number(self.ov["lon"].get(),"Longitude",commas=False),gui_number(self.ov["alt"].get(),"Altitude (ft)")*0.3048,gui_number(self.ov["scale"].get(),"Icon scale",positive=True),self.ov["mode"].get(),self.object_desc.get("1.0","end").strip(),self.ov["url"].get(),self.ov["link_text"].get(),self.ov["tether"].get(),self.ov["label"].get(),self.ov["popup"].get(),master=self,hide_above_ft=parse_hide_above(self.ov["hide"].get()))
            self.status.set(f"Created object: {p}")
            messagebox.showinfo(APP,f"Created:\n{p}\n\nOriginal PNG was not modified.")
        except Exception as e:messagebox.showerror(APP,str(e))

    def _build_batch_tab(self):
        t=self.batch_tab;t.columnconfigure(1,weight=1)
        here=app_dir();self.bv={"list":tk.StringVar(value=str(here/"sample_objects.txt")),"out":tk.StringVar(value=str(desktop_dir()/"Object_Set.kmz")),"summary":tk.StringVar(value="Load a header-based list or simple shorthand list.")}
        ttk.Label(t,text="Batch Object Set",font=("Segoe UI",15,"bold")).grid(row=0,column=0,columnspan=3,sticky="w",pady=(0,8))
        ttk.Label(t,text="Simple shorthand: type,lat,lon[,alt_m][,name]   —   Full list supports icon, description, hyperlink, scale, tether, popup, and labels.",wraplength=850).grid(row=1,column=0,columnspan=3,sticky="w",pady=(0,12))
        ttk.Label(t,text="Object list").grid(row=2,column=0,sticky="w",padx=(0,8),pady=5);ttk.Entry(t,textvariable=self.bv["list"]).grid(row=2,column=1,sticky="ew",pady=5);ttk.Button(t,text="Browse",command=self.pick_batch_list).grid(row=2,column=2,padx=(8,0),pady=5)
        ttk.Button(t,text="VALIDATE LIST",command=self.validate_batch).grid(row=3,column=1,sticky="w",pady=(2,8));ttk.Label(t,textvariable=self.bv["summary"],wraplength=700).grid(row=4,column=1,columnspan=2,sticky="w",pady=(0,12))
        ttk.Label(t,text="Output KMZ").grid(row=5,column=0,sticky="w",padx=(0,8),pady=5);ttk.Entry(t,textvariable=self.bv["out"]).grid(row=5,column=1,sticky="ew",pady=5);ttk.Button(t,text="Browse",command=self.pick_batch_out).grid(row=5,column=2,padx=(8,0),pady=5)
        fmt=ttk.LabelFrame(t,text="Full header format",padding=10);fmt.grid(row=6,column=0,columnspan=3,sticky="nsew",pady=12);t.rowconfigure(6,weight=1);fmt.columnconfigure(0,weight=1)
        header="type|name|lat|lon|alt_m|icon|description|url|link_text|scale|altitude_mode|tether|popup|label|hide_above_ft"
        ttk.Label(fmt,text=header,font=("Consolas",9),wraplength=820).grid(row=0,column=0,sticky="w")
        ttk.Label(fmt,text="Blank icon = preset icon. Relative icon paths are resolved beside the list file. hide_above_ft = eye alt (ft) above which the object disappears; blank = always visible (optional column). PNGs are normalized to <=256 px inside the KMZ; originals remain untouched.",wraplength=820).grid(row=1,column=0,sticky="w",pady=(8,0))
        f=ttk.Frame(t);f.grid(row=7,column=0,columnspan=3,sticky="ew",pady=(8,0));f.columnconfigure(0,weight=1);ttk.Button(f,text="CREATE OBJECT SET",command=self.create_batch).grid(row=0,column=0,sticky="e",ipadx=20,ipady=5)

    def pick_batch_list(self):
        p=filedialog.askopenfilename(filetypes=[("Object lists","*.txt *.csv"),("All files","*.*")]);
        if p:self.bv["list"].set(p);self.validate_batch()
    def pick_batch_out(self):
        p=filedialog.asksaveasfilename(defaultextension=".kmz",filetypes=[("KMZ","*.kmz")]);
        if p:self.bv["out"].set(p)
    def validate_batch(self):
        try:
            rows=parse_batch_rows(Path(self.bv["list"].get()));types={r['type'] for r in rows};self.bv["summary"].set(f"Valid: {len(rows)} objects. Presets/types: {', '.join(sorted(types)) or 'object'}.")
        except Exception as e:self.bv["summary"].set(f"Problem: {e}")
    def create_batch(self):
        try:
            if not self._ok_to_write(self.bv["out"].get(), ".kmz"):
                self.status.set("Not created - existing file kept."); return
            p,n=create_batch_kmz(Path(self.bv["list"].get()),Path(self.bv["out"].get()),master=self);self.status.set(f"Created batch object set: {p} ({n} objects)")
            messagebox.showinfo(APP,f"Created {n} objects:\n{p}")
        except Exception as e:messagebox.showerror(APP,str(e))

    def _build_compass_tab(self):
        t=self.compass_tab;t.columnconfigure(1,weight=1)
        self.cv={"lat":tk.StringVar(value="30.385524823620624"),"lon":tk.StringVar(value="-81.93080672778036"),"radius":tk.StringVar(value="100"),"alt":tk.StringVar(value="20000"),"scale":tk.StringVar(value="6"),"out":tk.StringVar(value=str(desktop_dir()/"Sky_Compass.kmz")),"coord_status":tk.StringVar(value="Center coordinates for N/E/S/W generation.")}
        ttk.Label(t,text="Sky Compass",font=("Segoe UI",15,"bold")).grid(row=0,column=0,columnspan=3,sticky="w",pady=(0,8));ttk.Label(t,text="Creates giant N/E/S/W PNG markers around a center point using the live-proven POF3 geometry.",wraplength=800).grid(row=1,column=0,columnspan=3,sticky="w",pady=(0,12))
        r=2
        for k,l in [("lat","Center latitude"),("lon","Center longitude")]:ttk.Label(t,text=l).grid(row=r,column=0,sticky="w",pady=5);ttk.Entry(t,textvariable=self.cv[k]).grid(row=r,column=1,columnspan=2,sticky="ew",pady=5);r+=1
        self._coord_buttons(t,r,self.cv["lat"],self.cv["lon"],self.cv["coord_status"]);r+=1;ttk.Label(t,textvariable=self.cv["coord_status"],foreground="#555").grid(row=r,column=1,columnspan=2,sticky="w",pady=(0,8));r+=1
        for k,l in [("radius","Radius (km)"),("alt","Altitude AGL (m)"),("scale","Icon scale")]:ttk.Label(t,text=l).grid(row=r,column=0,sticky="w",pady=5);ttk.Entry(t,textvariable=self.cv[k]).grid(row=r,column=1,columnspan=2,sticky="ew",pady=5);r+=1
        ttk.Label(t,text="Output KMZ").grid(row=r,column=0,sticky="w",pady=5);ttk.Entry(t,textvariable=self.cv["out"]).grid(row=r,column=1,sticky="ew",pady=5);ttk.Button(t,text="Browse",command=self.pick_compass_out).grid(row=r,column=2,padx=(8,0),pady=5);r+=1
        f=ttk.Frame(t);f.grid(row=r,column=0,columnspan=3,sticky="ew",pady=(12,0));f.columnconfigure(0,weight=1);ttk.Button(f,text="CREATE SKY COMPASS",command=self.create_compass).grid(row=0,column=0,sticky="e",ipadx=20,ipady=5)
    def pick_compass_out(self):
        p=filedialog.asksaveasfilename(defaultextension=".kmz",filetypes=[("KMZ","*.kmz")]);
        if p:self.cv["out"].set(p)
    def create_compass(self):
        try:
            if not self._ok_to_write(self.cv["out"].get(), ".kmz"):
                self.status.set("Not created - existing file kept."); return
            p=create_sky_compass_kmz(Path(self.cv["out"].get()),gui_number(self.cv["lat"].get(),"Center latitude",commas=False),gui_number(self.cv["lon"].get(),"Center longitude",commas=False),gui_number(self.cv["radius"].get(),"Radius (km)",positive=True),gui_number(self.cv["alt"].get(),"Altitude AGL (m)"),gui_number(self.cv["scale"].get(),"Icon scale",positive=True));self.status.set(f"Created Sky Compass: {p}")
            messagebox.showinfo(APP,f"Created:\n{p}")
        except Exception as e:messagebox.showerror(APP,str(e))

    def _build_beacon_tab(self):
        t=self.beacon_tab;t.columnconfigure(1,weight=1)
        self.ev={"name":tk.StringVar(value="EarthStick Beacon"),"lat":tk.StringVar(value="30.385524823620624"),"lon":tk.StringVar(value="-81.93080672778036"),"height":tk.StringVar(value="100"),"width":tk.StringVar(value="6"),"color":tk.StringVar(value="Red"),"out":tk.StringVar(value=str(desktop_dir()/"EarthStick_Beacon.kml")),"coord_status":tk.StringVar(value="Accepted Beacon Maker behavior integrated here.")}
        ttk.Label(t,text="Earth Beacon",font=("Segoe UI",15,"bold")).grid(row=0,column=0,columnspan=3,sticky="w",pady=(0,8));ttk.Label(t,text="Accepted Earth Beacon geometry preserved: a long-range vertical KML destination marker.").grid(row=1,column=0,columnspan=3,sticky="w",pady=(0,12))
        r=2
        ttk.Label(t,text="Beacon name").grid(row=r,column=0,sticky="w",pady=5);ttk.Entry(t,textvariable=self.ev["name"]).grid(row=r,column=1,columnspan=2,sticky="ew",pady=5);r+=1
        for k,l in [("lat","Latitude"),("lon","Longitude")]:ttk.Label(t,text=l).grid(row=r,column=0,sticky="w",pady=5);ttk.Entry(t,textvariable=self.ev[k]).grid(row=r,column=1,columnspan=2,sticky="ew",pady=5);r+=1
        self._coord_buttons(t,r,self.ev["lat"],self.ev["lon"],self.ev["coord_status"]);r+=1;ttk.Label(t,textvariable=self.ev["coord_status"],foreground="#555").grid(row=r,column=1,columnspan=2,sticky="w",pady=(0,8));r+=1
        ttk.Label(t,text="Height (km)").grid(row=r,column=0,sticky="w",pady=5);ttk.Entry(t,textvariable=self.ev["height"]).grid(row=r,column=1,columnspan=2,sticky="ew",pady=5);r+=1
        ttk.Label(t,text="Line width").grid(row=r,column=0,sticky="w",pady=5);ttk.Entry(t,textvariable=self.ev["width"]).grid(row=r,column=1,columnspan=2,sticky="ew",pady=5);r+=1
        ttk.Label(t,text="Color").grid(row=r,column=0,sticky="w",pady=5);ttk.Combobox(t,textvariable=self.ev["color"],values=tuple(COLORS.keys()),state="readonly").grid(row=r,column=1,columnspan=2,sticky="ew",pady=5);r+=1
        ttk.Label(t,text="Output KML").grid(row=r,column=0,sticky="w",pady=5);ttk.Entry(t,textvariable=self.ev["out"]).grid(row=r,column=1,sticky="ew",pady=5);ttk.Button(t,text="Browse",command=self.pick_beacon_out).grid(row=r,column=2,padx=(8,0),pady=5);r+=1
        f=ttk.Frame(t);f.grid(row=r,column=0,columnspan=3,sticky="ew",pady=(12,0));f.columnconfigure(0,weight=1);ttk.Button(f,text="CREATE BEACON KML",command=self.create_beacon).grid(row=0,column=0,sticky="e",ipadx=20,ipady=5)
    def pick_beacon_out(self):
        p=filedialog.asksaveasfilename(defaultextension=".kml",filetypes=[("KML","*.kml")]);
        if p:self.ev["out"].set(p)
    def create_beacon(self):
        try:
            if not self._ok_to_write(self.ev["out"].get(), ".kml"):
                self.status.set("Not created - existing file kept."); return
            p=create_beacon_kml(Path(self.ev["out"].get()),self.ev["name"].get(),gui_number(self.ev["lat"].get(),"Latitude",commas=False),gui_number(self.ev["lon"].get(),"Longitude",commas=False),gui_number(self.ev["height"].get(),"Height (km)",positive=True),gui_number(self.ev["width"].get(),"Line width",positive=True),self.ev["color"].get());self.status.set(f"Created Beacon: {p}")
            messagebox.showinfo(APP,f"Created:\n{p}")
        except Exception as e:messagebox.showerror(APP,str(e))


def selftest():
    root = tk.Tk(); root.withdraw()
    here = app_dir()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        # 1. Normalization: large and wide PNG; original untouched.
        large=tk.PhotoImage(master=root,width=900,height=300);large.put("#ff0000",to=(0,0,900,300));src=td/"wide.png";large.write(str(src),format="png");before=hashlib.sha256(src.read_bytes()).hexdigest();norm=td/"norm.png";ni=normalize_png(src,norm,master=root);after=hashlib.sha256(src.read_bytes()).hexdigest();assert before==after and max(ni["out_w"],ni["out_h"])<=256 and ni["out_w"]>ni["out_h"]
        # 2. Single object + hyperlink + hidden label.
        out1=td/"one.kmz";create_single_object_kmz(out1,preset_icon("helicopter"),"Test",30.1,-81.1,300,1.5,"relativeToGround","Desc","https://example.com","OPEN",False,False,"Info",master=root)
        with zipfile.ZipFile(out1) as z:
            k=z.read("doc.kml").decode();assert "https://example.com" in k and "<scale>0.0</scale>" in k and "icons/icon.png" in z.namelist()
        # 3. No-popup style emitted.
        outnp=td/"none.kmz";create_single_object_kmz(outnp,preset_icon("object"),"NoPopup",30.1,-81.1,100,1.4,"relativeToGround","","","",False,False,"None",master=root)
        with zipfile.ZipFile(outnp) as z: assert "<displayMode>hide</displayMode>" in z.read("doc.kml").decode()
        # 4. 100-object stress pack with duplicate icon reuse.
        lst=td/"stress.txt";lines=["type|name|lat|lon|alt_m|icon|description|url|link_text|scale|altitude_mode|tether|popup|label"]
        for i in range(100):lines.append(f"fuel|Fuel {i}|30.{100000+i}|-81.{200000+i}|150||Object {i}|||1.4|relativeToGround|no|Info|no")
        lst.write_text("\n".join(lines),encoding="utf-8");out2=td/"stress.kmz";_,n=create_batch_kmz(lst,out2,master=root);assert n==100
        with zipfile.ZipFile(out2) as z:
            names=z.namelist();assert names.count("doc.kml")==1 and len([x for x in names if x.startswith("icons/")])==1
        # 5. Shorthand parser.
        sh=td/"short.txt";sh.write_text("fuel,30.410104,-81.922396\nheli,30.39821,-81.93144,300,Helicopter 1\n",encoding="utf-8");assert len(parse_batch_rows(sh))==2
        # 5b. v1.1: a place name containing "lat" and "lon" is not mistaken for a header; errors name the line.
        sh.write_text("staging,30.1,-81.6,150,Palatka Colony Staging\nfuel,30.41,-81.92\n",encoding="utf-8");assert len(parse_batch_rows(sh))==2
        sh.write_text("fuel,30.41,-81.92\nwater,30.4O,-81.91\n",encoding="utf-8")
        try: parse_batch_rows(sh); raise AssertionError("bad number accepted")
        except ValueError as e: assert str(e).startswith("Line 2")
        # 5c. v1.1 clipboard: Google Maps pair, N/S/E/W letters and DMS all read as the same place.
        for text in ("30.4009768, -81.9347098","30.4009768°N 81.9347098°W","N30.4009768 W81.9347098","81.9347098°W 30.4009768°N","30°24'03.5\"N 81°56'05.0\"W"):
            la,lo,_=parse_clipboard_coordinates(text);assert abs(la-30.40098)<1e-4 and abs(lo+81.93471)<1e-4, text
        # 5d. v1.1: a failed build keeps the previous file.
        keep=td/"keep.kml";keep.write_text("previous",encoding="utf-8")
        try: create_beacon_kml(keep,"Bad",95.0,-81.2,100,6,"Red")
        except ValueError: pass
        assert keep.read_text(encoding="utf-8")=="previous" and not (td/"keep.kml.partial").exists()
        # 5e. v1.2 Hide above: Region/LOD only when set; blank output unchanged.
        assert lod_pixels_for(3000)==597 and parse_hide_above("")is None and parse_hide_above(" 5,000 ")==5000
        for bad in ("-5","abc"):
            try: parse_hide_above(bad); raise AssertionError("bad hide accepted")
            except ValueError: pass
        outh=td/"hide.kmz";create_single_object_kmz(outh,preset_icon("camera"),"Cam",30.62,-81.65,180,1.5,"relativeToGround","","","",True,False,"Info",master=root,hide_above_ft=3000)
        with zipfile.ZipFile(outh) as z:
            k=z.read("doc.kml").decode();assert "<minLodPixels>597</minLodPixels>" in k and k.count("<Folder>")==1 and "tether" in k and k.index("<Region>")<k.index("<Placemark>") and "<minAltitude>30.0</minAltitude><maxAltitude>330.0</maxAltitude><altitudeMode>relativeToGround</altitudeMode>" in k and "<description><![CDATA[Cam]]></description>" in k
        with zipfile.ZipFile(out1) as z: assert "<Region>" not in z.read("doc.kml").decode()
        lst.write_text("type|name|lat|lon|hide_above_ft\ncamera|A|30.6|-81.6|2000\ncamera|B|30.6|-81.5|\n",encoding="utf-8");rows=parse_batch_rows(lst);assert rows[0]["hide_above_ft"]==2000 and rows[1]["hide_above_ft"] is None
        out3=td/"hb.kmz";create_batch_kmz(lst,out3,master=root)
        with zipfile.ZipFile(out3) as z:
            k=z.read("doc.kml").decode();assert k.count("<Region>")==1 and "<minLodPixels>895</minLodPixels>" in k
        lst.write_text("type|name|lat|lon|hide_above_ft\ncamera|A|30.6|-81.6|high\n",encoding="utf-8")
        try: parse_batch_rows(lst); raise AssertionError("bad hide_above_ft accepted")
        except ValueError as e: assert str(e).startswith("Line 2")
        # 5f. v2.1: Excel Windows-1252 list with accents + blank rows; quote marks in | lists; number boxes.
        ex=td/"excel.csv";ex.write_bytes("type,name,lat,lon\r\nwater,Café,30.4,-81.9\r\n,,,\r\nfuel,\"Pump, north\",30.41,-81.91\r\n".encode("cp1252"))
        assert [r["name"] for r in parse_batch_rows(ex)]==["Café","Pump, north"]
        qt=td/"quote.txt";qt.write_text('type|name|lat|lon|description\nwater|A|30.4|-81.9|"12 in" main\nwater|B|30.5|-81.9|ok\n',encoding="utf-8")
        assert [r["description"] for r in parse_batch_rows(qt)]==['"12 in" main',"ok"]
        try: gui_number("thirty","Altitude (ft)"); raise AssertionError("word accepted as a number")
        except ValueError as e: assert str(e)=="Altitude (ft): 'thirty' is not a number."
        # 6. Sky compass.
        comp=td/"comp.kmz";create_sky_compass_kmz(comp,30.3855,-81.9308,100,20000,6)
        with zipfile.ZipFile(comp) as z:
            k=z.read("doc.kml").decode();assert all(f"<name>{x}</name>" in k for x in "NESW")
        # 7. Beacon accepted geometry.
        b=td/"b.kml";create_beacon_kml(b,"Beacon",30.2,-81.2,100,6,"Red");text=b.read_text();assert "100000.000" in text and "relativeToGround" in text
    root.destroy()
    print("OBJECT FACTORY SELFTEST PASS")


def main():
    ap=argparse.ArgumentParser(add_help=False);ap.add_argument("--selftest",action="store_true");ap.add_argument("--smoke-test",action="store_true");ns,_=ap.parse_known_args()
    if ns.selftest:selftest();return
    ObjectFactory(smoke_test=ns.smoke_test).mainloop()

if __name__=="__main__":
    main()
