#!/usr/bin/env python3
r"""
ArcGIS Earth PRAVE / ME Tracker - 3.0 (adds the P25 GPS relay source; 2.1 path unchanged)

3.0 - one map, one owner of the ArcGIS Earth API (Gold RMC/PRAVE path unchanged):
    * NEW P25 source: the BK P25 base radio, connected as the USB Ethernet/RNDIS
      Gadget at 10.250.46.6, relays received field-radio GPS on TCP port 65535.
      3.0 subscribes (one 5-byte request), reads the $GNGGA + $PP25 pair per fix,
      and draws each sending radio's P25 unit ID as its own marker - on the SAME
      map as ME and the Raveon ($PRAVE) fleet.
    * The P25 feed runs in its own reader thread that only parses and queues; every
      ArcGIS Earth write still goes through the one existing main-thread gate
      (earth_action), so there is a single API owner and no write ever collides.
    * ME ($GPRMC/$GNRMC) remains the camera authority; P25 never moves the camera.
    * P25 units: own AE_P25_ drawing IDs, own orange/amber markers (beside this
      file), friendly aliases from p25_aliases.json (9076801 -> "Jax 24",
      hot-reloaded and editable with the included alias editor), age labels, a
      daily CSV, and automatic drop after P25_EXPIRE_SECONDS of silence.
    * Set P25_ENABLED = False to run exactly like 2.1 (no P25 thread started).
    * It only READS the radio (sends the one subscribe) and draws to ArcGIS Earth.
      It never reprograms the radio and never touches the Raveon serial side.

2.1 re-hardening (Gold RMC/PRAVE parsing unchanged):
    * ArcGIS Earth closed or restarted while tracking: "lost" and "back" are
      logged once each (no line every second), and when it comes back every
      known unit and ME are drawn again at once at their last positions
    * a missing or busy COM port is explained in plain words (with the ports
      this PC has), said once, then the tracker keeps waiting quietly
    * the logs start a new file every day (..._2026-11-08.csv)
    * a unit not heard from for STALE_AFTER_MINUTES shows its age in the map
      label, for example "7-101 · 12 min" (refreshed once a minute)

v1.2: the local ArcGIS Earth Automation API connection never goes through a
      system or agency proxy (Windows proxy settings could otherwise block
      every update to localhost).

v1.1 hardening (Gold RMC/PRAVE parsing, drawings and camera tracking unchanged):
    * a serial reconnect no longer clears all units from the map; old
      drawings are cleaned only when the tracker starts
    * missing pyserial is reported once and the tracker exits instead of
      retrying forever
    * startup warning when the RSSI icon folder or icon files are missing
    * ArcGIS Earth API failures are logged as API problems, not as bad sentences
    * GPS "no fix" (RMC status V) is logged once when it starts and once when
      the fix returns, instead of a log line every second

Modern successor to the proven PRAVE / ME Version 1.0 Gold display path.

Preserved from the Gold decoder:
    * One mixed Raveon serial input
    * Checksum-validated $GPRMC / $GNRMC
    * Checksum-validated $PRAVE
    * Proven PRAVE field positions
    * District + 3-digit individual display ID
    * RSSI 0-5 icon selection
    * CSV and activity logging
    * Auto reconnect
    * No Windows clock access
    * No Internet dependency

Modernized display path:
    $PRAVE -> ArcGIS Earth local REST Automation API -> point Drawing
    Each unit drawing uses:
        * stable drawing ID
        * local RSSI fire-truck PNG
        * native ArcGIS Earth label
        * direct position replacement on each report

ME / own-position:
    $GPRMC / $GNRMC -> ArcGIS Earth ME point Drawing + camera tracking
    Each valid RMC update recenters the ArcGIS Earth camera on ME while
    preserving the operator's current camera height, heading, tilt, and roll.

Project rule:
    Friends don't let friends edit Python.
    Change settings above HERE BE DRAGONS. Leave the dragons alone.
"""

from __future__ import annotations

# ============================================================
#                    USER CONFIGURATION
# ============================================================

# Same mixed Raveon serial input model as PRAVE / ME Gold.
INPUT_PORT = "COM12"
INPUT_BAUD = 19200

# ArcGIS Earth Automation API.
ARCGIS_EARTH_API_BASE = "http://localhost:8000"
API_TIMEOUT_SECONDS = 3.0

# Existing proven PRAVE icon folder.
ICON_FOLDER = r"C:\MyData\PRAVE_ME\Icons"

RSSI_ICON_FILENAMES = {
    0: "firetruck_rssi_unknown.png",
    1: "firetruck_rssi_1.png",
    2: "firetruck_rssi_2.png",
    3: "firetruck_rssi_3.png",
    4: "firetruck_rssi_4.png",
    5: "firetruck_rssi_5.png",
}

# Initial Gold RSSI thresholds.
RSSI_2_BAR_MIN_DBM = -110
RSSI_3_BAR_MIN_DBM = -100
RSSI_4_BAR_MIN_DBM = -90
RSSI_5_BAR_MIN_DBM = -80

# ArcGIS Earth display.
FIRETRUCK_SIZE_PX = 52
LABEL_SIZE = 13
LABEL_COLOR = [255, 255, 255, 255]
DRAWING_ID_PREFIX = "AE_PRAVE_"
ME_DRAWING_ID = "AE_ME"

# Logs live beside this program, not in the old KML operational folder.
ENABLE_TEXT_LOG = True
ENABLE_CSV_LOG = True
LOG_FOLDER_NAME = "Logs"
ACTIVITY_LOG_FILENAME = "AE_PRAVE_Live_Activity.log"
PRAVE_CSV_FILENAME = "AE_PRAVE_Packet_History.csv"
RMC_CSV_FILENAME = "AE_RMC_Position_History.csv"
SESSION_STATE_FILENAME = "AE_PRAVE_previous_units.json"

# Serial recovery.
AUTO_RECONNECT = True
RECONNECT_DELAY_SECONDS = 5.0

# A unit not heard from for this many minutes shows its age in its map label,
# for example "7-101 · 12 min". 0 = never.
STALE_AFTER_MINUTES = 5

# Console.
SHOW_VALID_RMC = False
SHOW_VALID_PRAVE = True
SHOW_IGNORED_SENTENCES = False
SHOW_STATUS_SUMMARY = True
ME_TRACKING_ENABLED_AT_START = True

# ---- P25 GPS relay source (BK base radio over USB RNDIS) --------------------
# The base radio appears as the "USB Ethernet/RNDIS Gadget" network adapter and
# relays received field-radio GPS on a TCP service. Set P25_ENABLED = False to
# run exactly like 2.1 (the P25 thread is never started).
P25_ENABLED = True
P25_RADIO_IP = "10.250.46.6"
P25_RADIO_PORT = 65535
P25_SUBSCRIBE_HEX = "80 04 18 e4 81"       # the one request that starts the GPS stream

# A P25 unit not heard from for this many seconds is dropped from the map.
# 0 = never drop (match the PRAVE side, which keeps units until restart).
P25_EXPIRE_SECONDS = 2 * 60 * 60           # 2 hours

# P25 markers and alias table live beside this file (System Files).
P25_MARKER_FILENAME = "marker.png"         # fresh fix
P25_MARKER_STALE_FILENAME = "marker_stale.png"   # aging (amber)
P25_MARKER_SIZE_PX = 40
P25_ALIAS_FILENAME = "p25_aliases.json"    # {"9076801": "Jax 24"} - hot-reloaded
P25_DRAWING_ID_PREFIX = "AE_P25_"
P25_CSV_FILENAME = "AE_P25_Track_History.csv"
P25_STATE_FILENAME = "AE_P25_previous_units.json"

# P25 link keep-alive / recovery (independent of the Raveon serial recovery).
P25_KEEPALIVE_SECONDS = 20                 # re-send the subscribe this often (0 = off)
P25_WATCHDOG_SECONDS = 90                  # no bytes at all this long -> reconnect
P25_RECONNECT_SECONDS = 4

# ============================================================
#                    HERE BE DRAGONS
# ============================================================

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import re
import socket
import threading
import time
from urllib import request, error

try:
    import serial  # pyserial
except ImportError:
    serial = None

try:
    import msvcrt  # Windows console key input
except ImportError:
    msvcrt = None


VERSION = "3.0"   # 3.0 (2026-11-11) adds the P25 GPS relay source on one shared ArcGIS Earth API owner; Gold RMC/PRAVE path unchanged

me_tracking_enabled = ME_TRACKING_ENABLED_AT_START


class RMCNoFix(ValueError):
    """RMC sentence is valid but the GPS reports no fix (status V)."""


class EarthUnreachable(RuntimeError):
    """ArcGIS Earth is not answering on this PC (closed, restarting or busy)."""


class PortProblem(RuntimeError):
    """The serial port is missing or held by another program (plain message)."""


EARTH_RETRY_SECONDS = 5.0


@dataclass
class RMCPosition:
    lat: float
    lon: float
    gps_utc: datetime
    received_at_local: datetime
    received_monotonic: float
    speed_knots: float | None
    course_degrees: float | None
    raw_sentence: str


@dataclass
class PRAVEUnit:
    raw_id: str
    display_id: str
    lat: float
    lon: float
    rssi_dbm: int | None
    rssi_level: int
    gps_status: str
    satellites: str
    voltage: str
    prave_utc_text: str
    last_seen_local: datetime
    packet_count: int
    raw_sentence: str
    received_monotonic: float = 0.0


@dataclass
class P25Unit:
    """A field radio heard over the P25 GPS relay. Kept separate from PRAVEUnit so
    the Gold PRAVE path is never touched; drawn on the same map via the same gate."""
    unit_id: str
    lat: float
    lon: float
    alt: str
    sats: str
    gps_utc: str
    last_seen_local: datetime
    received_monotonic: float
    packet_count: int


@dataclass
class Counters:
    rx_lines: int = 0
    valid_rmc: int = 0
    bad_rmc: int = 0
    valid_prave: int = 0
    bad_prave: int = 0
    valid_p25: int = 0
    ignored: int = 0
    api_ok: int = 0
    api_bad: int = 0
    no_fix_rmc: int = 0


@dataclass
class TrackerState:
    """Kept across serial reconnects so units stay on the map and in the state file."""
    units: dict
    counters: Counters
    me: RMCPosition | None = None
    startup_clean_done: bool = False
    gps_no_fix: bool = False
    earth_down: bool = False
    earth_next_try: float = 0.0
    last_problem: str = ""
    drawn: dict = None
    # --- P25 source (added in 3.0; all optional so 2.1 behaviour is intact) ---
    p25: dict = None               # unit_id -> P25Unit
    p25_drawn: dict = None         # unit_id -> last drawn label (stale-label cache)
    p25_aliases: dict = None       # unit_id -> friendly name (from p25_aliases.json)
    p25_alias_mtime: float = 0.0
    p25_queue: object = None       # fixes/logs from the P25 reader thread
    p25_stop: object = None        # threading.Event to stop that thread
    p25_thread: object = None

    def __post_init__(self):
        if self.drawn is None:
            self.drawn = {}
        if self.p25 is None:
            self.p25 = {}
        if self.p25_drawn is None:
            self.p25_drawn = {}
        if self.p25_aliases is None:
            self.p25_aliases = {}


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def log_dir() -> Path:
    return script_dir() / LOG_FOLDER_NAME


def daily(filename: str) -> str:
    """One file per day: AE_RMC_Position_History.csv -> AE_RMC_Position_History_2026-11-08.csv"""
    path = Path(filename)
    return f"{path.stem}_{datetime.now().strftime('%Y-%m-%d')}{path.suffix}"


def activity_log_path() -> Path:
    return log_dir() / daily(ACTIVITY_LOG_FILENAME)


def prave_csv_path() -> Path:
    return log_dir() / daily(PRAVE_CSV_FILENAME)


def rmc_csv_path() -> Path:
    return log_dir() / daily(RMC_CSV_FILENAME)


def session_state_path() -> Path:
    return script_dir() / SESSION_STATE_FILENAME


def ensure_directories() -> None:
    log_dir().mkdir(parents=True, exist_ok=True)


def log_message(message: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line)
    if not ENABLE_TEXT_LOG:
        return
    try:
        ensure_directories()
        with activity_log_path().open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


def append_csv(path: Path, header: list[str], row: list[object]) -> None:
    if not ENABLE_CSV_LOG:
        return
    try:
        ensure_directories()
        exists = path.exists()
        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if not exists:
                writer.writerow(header)
            writer.writerow(row)
    except Exception as exc:
        log_message(f"CSV_LOG_WARNING path={path} error={exc}")


# ------------------------------------------------------------
# Gold checksum and coordinate logic
# ------------------------------------------------------------

def nmea_checksum(body: str) -> str:
    value = 0
    for char in body:
        value ^= ord(char)
    return f"{value:02X}"


def make_nmea_sentence(body: str) -> str:
    return f"${body}*{nmea_checksum(body)}"


def verify_nmea_checksum(sentence: str) -> bool:
    text = sentence.strip()
    if not text.startswith("$") or "*" not in text:
        return False
    try:
        body, supplied = text[1:].split("*", 1)
    except ValueError:
        return False
    if len(supplied) < 2:
        return False
    return nmea_checksum(body) == supplied[:2].upper()


def nmea_coord_to_decimal(value: str, hemisphere: str) -> float:
    value = value.strip()
    hemisphere = hemisphere.strip().upper()
    if not value or "." not in value:
        raise ValueError("missing coordinate")
    left = value.split(".", 1)[0]
    degree_digits = len(left) - 2
    if degree_digits not in (2, 3):
        raise ValueError("bad NMEA coordinate width")
    degrees = int(value[:degree_digits])
    minutes = float(value[degree_digits:])
    if not 0.0 <= minutes < 60.0:
        raise ValueError("bad NMEA minutes")
    result = degrees + minutes / 60.0
    if hemisphere in ("S", "W"):
        result = -result
    elif hemisphere not in ("N", "E"):
        raise ValueError("bad hemisphere")
    return result


def parse_signed_prave_coord(value: str) -> float:
    value = value.strip()
    if not value:
        raise ValueError("empty PRAVE coordinate")
    sign = -1.0 if value.startswith("-") else 1.0
    if value[0] in "+-":
        value = value[1:]
    if "." not in value:
        raise ValueError("PRAVE coordinate missing decimal point")
    left = value.split(".", 1)[0]
    degree_digits = len(left) - 2
    if degree_digits < 1 or degree_digits > 3:
        raise ValueError("bad PRAVE coordinate width")
    degrees = int(value[:degree_digits])
    minutes = float(value[degree_digits:])
    if not 0.0 <= minutes < 60.0:
        raise ValueError("bad PRAVE minutes")
    return sign * (degrees + minutes / 60.0)


def parse_optional_float(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    return float(text)


def parse_rmc_sentence(sentence: str) -> RMCPosition | None:
    text = sentence.strip()
    if not (text.startswith("$GPRMC") or text.startswith("$GNRMC")):
        return None
    if not verify_nmea_checksum(text):
        raise ValueError("bad RMC checksum")

    fields = text.split("*", 1)[0].split(",")
    if len(fields) < 10:
        raise ValueError("not enough RMC fields")

    utc_text = fields[1].strip()
    status = fields[2].strip().upper()
    if status != "A":
        raise RMCNoFix(f"RMC status is not valid: {status or 'blank'}")

    date_text = fields[9].strip()
    if len(utc_text) < 6 or len(date_text) != 6:
        raise ValueError("RMC missing UTC time or date")

    hour = int(utc_text[0:2])
    minute = int(utc_text[2:4])
    second_float = float(utc_text[4:])
    second = int(second_float)
    microsecond = int(round((second_float - second) * 1_000_000))
    if microsecond >= 1_000_000:
        second += 1
        microsecond -= 1_000_000

    day = int(date_text[0:2])
    month = int(date_text[2:4])
    two_digit_year = int(date_text[4:6])
    year = 1900 + two_digit_year if two_digit_year >= 80 else 2000 + two_digit_year

    gps_utc = datetime(
        year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc
    )
    lat = nmea_coord_to_decimal(fields[3], fields[4])
    lon = nmea_coord_to_decimal(fields[5], fields[6])

    if not (20.0 <= lat <= 69.99999):
        raise ValueError(f"RMC latitude outside expected operating range: {lat:.6f}")
    if not (-180.0 <= lon < 0.0):
        raise ValueError(f"RMC longitude is not valid West longitude: {lon:.6f}")

    return RMCPosition(
        lat=lat,
        lon=lon,
        gps_utc=gps_utc,
        received_at_local=datetime.now(),
        received_monotonic=time.monotonic(),
        speed_knots=parse_optional_float(fields[7]),
        course_degrees=parse_optional_float(fields[8]),
        raw_sentence=text,
    )


def rssi_level_from_dbm(rssi_dbm: int | None) -> int:
    if rssi_dbm is None:
        return 0
    if rssi_dbm >= RSSI_5_BAR_MIN_DBM:
        return 5
    if rssi_dbm >= RSSI_4_BAR_MIN_DBM:
        return 4
    if rssi_dbm >= RSSI_3_BAR_MIN_DBM:
        return 3
    if rssi_dbm >= RSSI_2_BAR_MIN_DBM:
        return 2
    return 1


def parse_prave_rssi(text: str) -> int | None:
    value = text.strip()
    if not value:
        return None
    parsed = int(value)
    if not -140 <= parsed <= 0:
        raise ValueError(f"RSSI outside accepted range: {parsed}")
    return parsed


def build_prave_ids(fields: list[str]) -> tuple[str, str]:
    district = fields[8].strip().upper()
    individual = fields[13].strip().upper()

    if len(district) != 1:
        raise ValueError(f"district must be one character, got '{district}'")
    if district not in "0123456789ABCDEF":
        raise ValueError(f"district is not hex-safe: '{district}'")
    if not individual.isdigit():
        raise ValueError(f"individual ID is not numeric: '{individual}'")
    individual_value = int(individual)
    if not 0 <= individual_value <= 999:
        raise ValueError(f"individual ID outside 000-999: '{individual}'")

    raw_id = f"{district}{individual_value:03d}"
    display_id = f"{raw_id[0]}-{raw_id[1:]}"
    return raw_id, display_id


def parse_prave_sentence(sentence: str) -> PRAVEUnit | None:
    text = sentence.strip()
    if not text.startswith("$PRAVE"):
        return None
    if not verify_nmea_checksum(text):
        raise ValueError("bad PRAVE checksum")

    fields = text.split("*", 1)[0].split(",")
    if len(fields) < 15:
        raise ValueError(f"not enough PRAVE fields: {len(fields)}")

    lat = parse_signed_prave_coord(fields[3])
    lon = parse_signed_prave_coord(fields[4])
    if not (20.0 <= lat <= 69.99999):
        raise ValueError(f"PRAVE latitude outside expected range: {lat:.6f}")
    if not (-180.0 <= lon < 0.0):
        raise ValueError(f"PRAVE longitude is not valid West longitude: {lon:.6f}")

    raw_id, display_id = build_prave_ids(fields)
    rssi_dbm = parse_prave_rssi(fields[12])

    return PRAVEUnit(
        raw_id=raw_id,
        display_id=display_id,
        lat=lat,
        lon=lon,
        rssi_dbm=rssi_dbm,
        rssi_level=rssi_level_from_dbm(rssi_dbm),
        gps_status=fields[6].strip(),
        satellites=fields[7].strip(),
        voltage=fields[10].strip(),
        prave_utc_text=fields[5].strip(),
        last_seen_local=datetime.now(),
        packet_count=1,
        raw_sentence=text,
        received_monotonic=time.monotonic(),
    )


def merge_prave_unit(db: dict[str, PRAVEUnit], incoming: PRAVEUnit) -> PRAVEUnit:
    existing = db.get(incoming.raw_id)
    if existing is not None:
        incoming.packet_count = existing.packet_count + 1
    db[incoming.raw_id] = incoming
    return incoming


def format_rssi(rssi_dbm: int | None) -> str:
    return "Unknown" if rssi_dbm is None else f"{rssi_dbm} dBm"


def gps_freshness_text(position: RMCPosition | None) -> str:
    if position is None:
        return "WAITING"
    age = max(0.0, time.monotonic() - position.received_monotonic)
    return "FRESH" if age <= 5.0 else f"STALE ({age:.1f} s old)"


# ------------------------------------------------------------
# ArcGIS Earth Automation API
# ------------------------------------------------------------

def api_url(path: str) -> str:
    return ARCGIS_EARTH_API_BASE.rstrip("/") + path


# ArcGIS Earth runs on this computer, so its API must never be sent through a
# system or agency proxy (urllib would otherwise use the Windows proxy setting).
_LOCAL_OPENER = request.build_opener(request.ProxyHandler({}))


def http_json(method: str, path: str, payload: dict | None = None) -> object:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(api_url(path), data=data, headers=headers, method=method)
    try:
        with _LOCAL_OPENER.open(req, timeout=API_TIMEOUT_SECONDS) as response:
            raw = response.read()
            if not raw:
                return {}
            text = raw.decode("utf-8", errors="replace").strip()
            if not text:
                return {}
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ArcGIS Earth API HTTP {exc.code}: {body or exc.reason}") from exc
    except (error.URLError, TimeoutError, ConnectionError) as exc:
        raise EarthUnreachable(
            "ArcGIS Earth Automation API is not reachable at "
            f"{ARCGIS_EARTH_API_BASE}. "
            "In ArcGIS Earth open Settings > Advanced application settings "
            "and enable Automation API."
        ) from exc


def check_arcgis_earth_api() -> None:
    http_json("GET", "/arcgisearth/camera")


def drawing_id(raw_id: str) -> str:
    return f"{DRAWING_ID_PREFIX}{raw_id}"


_icon_warnings_given: set[str] = set()


def icon_path_for_level(level: int) -> Path | None:
    folder = Path(ICON_FOLDER)
    exact = folder / RSSI_ICON_FILENAMES[level]
    if exact.is_file():
        return exact

    unknown = folder / RSSI_ICON_FILENAMES[0]
    if unknown.is_file():
        if level != 0 and exact.name not in _icon_warnings_given:
            _icon_warnings_given.add(exact.name)
            log_message(f"ICON_WARNING missing {exact.name}; using {unknown.name}")
        return unknown

    return None


def check_icon_folder() -> None:
    folder = Path(ICON_FOLDER)
    if not folder.is_dir():
        log_message(
            f"ICON_WARNING icon folder not found: {folder} - units will show "
            "ArcGIS Earth's default marker. Set ICON_FOLDER above HERE BE DRAGONS."
        )
        return
    missing = [name for name in RSSI_ICON_FILENAMES.values() if not (folder / name).is_file()]
    if missing:
        log_message(f"ICON_WARNING missing in {folder}: {', '.join(missing)}")


def unit_label(unit: PRAVEUnit) -> str:
    """'7-101', or '7-101 · 12 min' once the unit has been quiet for STALE_AFTER_MINUTES."""
    if not STALE_AFTER_MINUTES or not unit.received_monotonic:
        return unit.display_id
    minutes = int((time.monotonic() - unit.received_monotonic) // 60)
    if minutes < STALE_AFTER_MINUTES:
        return unit.display_id
    if minutes < 60:
        return f"{unit.display_id} · {minutes} min"
    return f"{unit.display_id} · {minutes // 60} h {minutes % 60:02d} min"


def build_unit_drawing(unit: PRAVEUnit) -> dict:
    payload = {
        "id": drawing_id(unit.raw_id),
        "visible": True,
        "title": unit_label(unit),
        "geometry": {
            "x": unit.lon,
            "y": unit.lat,
            "spatialReference": {"wkid": 4326},
        },
        "labelSymbol": {
            "type": "text",
            "color": LABEL_COLOR,
            "size": LABEL_SIZE,
        },
    }

    icon = icon_path_for_level(unit.rssi_level)
    if icon is not None:
        payload["symbol"] = {
            "type": "picture-marker",
            "url": str(icon),
            "size": f"{FIRETRUCK_SIZE_PX}px",
        }

    return payload


def build_me_drawing(position: RMCPosition) -> dict:
    return {
        "id": ME_DRAWING_ID,
        "visible": True,
        "title": "ME",
        "geometry": {
            "x": position.lon,
            "y": position.lat,
            "spatialReference": {"wkid": 4326},
        },
        "labelSymbol": {
            "type": "text",
            "color": LABEL_COLOR,
            "size": LABEL_SIZE,
        },
    }


def build_me_tracking_camera(camera: object, position: RMCPosition) -> dict:
    if not isinstance(camera, dict):
        raise RuntimeError("ArcGIS Earth camera response is not a JSON object")
    current_position = camera.get("position")
    if not isinstance(current_position, dict) or "z" not in current_position:
        raise RuntimeError("ArcGIS Earth camera response is missing position.z")

    return {
        "position": {
            "x": position.lon,
            "y": position.lat,
            "z": current_position["z"],
            "spatialReference": {"wkid": 4326},
        },
        "heading": camera.get("heading", 0.0),
        "tilt": camera.get("tilt", 0.0),
        "roll": camera.get("roll", 0.0),
    }


def center_camera_on_me(position: RMCPosition) -> None:
    camera = http_json("GET", "/arcgisearth/camera")
    http_json("PUT", "/arcgisearth/camera", build_me_tracking_camera(camera, position))


def delete_drawing(raw_id: str, ignore_missing: bool = True) -> None:
    path = f"/arcgisearth/drawings/{drawing_id(raw_id)}"
    try:
        http_json("DELETE", path)
    except RuntimeError as exc:
        text = str(exc)
        if ignore_missing and ("HTTP 404" in text or "not found" in text.lower()):
            return
        raise


def post_unit_drawing(unit: PRAVEUnit) -> None:
    http_json("POST", "/arcgisearth/drawings", build_unit_drawing(unit))


def replace_unit_drawing(unit: PRAVEUnit) -> None:
    # Drawing API gives us native labelSymbol + local picture-marker in one object.
    # PRAVE cadence is slow enough that delete/re-add is appropriate and simple.
    delete_drawing(unit.raw_id, ignore_missing=True)
    post_unit_drawing(unit)


def replace_me_drawing(position: RMCPosition) -> None:
    try:
        http_json("DELETE", f"/arcgisearth/drawings/{ME_DRAWING_ID}")
    except RuntimeError as exc:
        text = str(exc)
        if "HTTP 404" not in text and "not found" not in text.lower():
            raise
    http_json("POST", "/arcgisearth/drawings", build_me_drawing(position))


def load_previous_unit_ids() -> list[str]:
    path = session_state_path()
    try:
        if not path.is_file():
            return []
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            return []
        return [str(x) for x in value]
    except Exception:
        return []


def save_current_unit_ids(units: dict[str, PRAVEUnit]) -> None:
    try:
        session_state_path().write_text(
            json.dumps(sorted(units), indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        log_message(f"STATE_WARNING could not save unit state: {exc}")


def clean_previous_session() -> None:
    previous = load_previous_unit_ids()
    removed = 0
    for raw_id in previous:
        try:
            delete_drawing(raw_id, ignore_missing=True)
            removed += 1
        except Exception as exc:
            log_message(f"STALE_DRAWING_WARNING id={raw_id} error={exc}")
    try:
        http_json("DELETE", f"/arcgisearth/drawings/{ME_DRAWING_ID}")
    except RuntimeError as exc:
        text = str(exc)
        if "HTTP 404" not in text and "not found" not in text.lower():
            log_message(f"STALE_ME_WARNING error={exc}")
    try:
        session_state_path().unlink(missing_ok=True)
    except Exception:
        pass
    # P25 markers from a previous run (added in 3.0).
    previous_p25 = load_previous_p25_ids()
    removed_p25 = 0
    for uid in previous_p25:
        try:
            delete_p25_drawing(uid, ignore_missing=True)
            removed_p25 += 1
        except Exception as exc:
            log_message(f"STALE_P25_WARNING id={uid} error={exc}")
    try:
        session_p25_state_path().unlink(missing_ok=True)
    except Exception:
        pass
    if previous or previous_p25:
        log_message(f"STARTUP_CLEAN previous drawings checked - PRAVE={removed} P25={removed_p25}")


# ------------------------------------------------------------
# Recording
# ------------------------------------------------------------

def record_rmc(position: RMCPosition) -> None:
    append_csv(
        rmc_csv_path(),
        [
            "received_local",
            "gps_utc",
            "latitude",
            "longitude",
            "speed_knots",
            "course_degrees",
            "raw_rmc",
        ],
        [
            position.received_at_local.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            position.gps_utc.isoformat(),
            f"{position.lat:.7f}",
            f"{position.lon:.7f}",
            "" if position.speed_knots is None else position.speed_knots,
            "" if position.course_degrees is None else position.course_degrees,
            position.raw_sentence,
        ],
    )


def record_prave(unit: PRAVEUnit) -> None:
    append_csv(
        prave_csv_path(),
        [
            "received_local",
            "display_id",
            "raw_id",
            "latitude",
            "longitude",
            "rssi_dbm",
            "rssi_icon_level",
            "gps_status",
            "satellites",
            "voltage",
            "packet_count_session",
            "raw_prave",
        ],
        [
            unit.last_seen_local.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            unit.display_id,
            unit.raw_id,
            f"{unit.lat:.7f}",
            f"{unit.lon:.7f}",
            "" if unit.rssi_dbm is None else unit.rssi_dbm,
            unit.rssi_level,
            unit.gps_status,
            unit.satellites,
            unit.voltage,
            unit.packet_count,
            unit.raw_sentence,
        ],
    )


# ------------------------------------------------------------
# P25 GPS relay source (added in 3.0)
#
# The BK base radio, connected as the USB Ethernet/RNDIS Gadget, relays received
# field-radio GPS on TCP P25_RADIO_PORT. We subscribe once, then read framed
# messages whose payload, per fix, is a standard $GNGGA position followed by a
# proprietary $PP25,<unit_id> sentence. A reader thread only parses and queues;
# the main thread draws every fix through the one shared earth_action() gate, so
# ME, the Raveon fleet and P25 all share a single ArcGIS Earth API owner.
# ------------------------------------------------------------

_P25_SENTENCE = re.compile(r"\$[^*$\r\n]{2,88}\*[0-9A-Fa-f]{2}")


class P25StreamParser:
    """Feed raw socket bytes; yield (unit_id, lat, lon, alt, sats, utc) per fix.

    Frame-agnostic: it finds checksum-valid NMEA sentences anywhere in the byte
    stream and pairs each $GNGGA position with the $PP25 unit id that follows it,
    reusing the Gold checksum and coordinate routines above."""

    def __init__(self):
        self._buf = bytearray()
        self._pending = None

    def feed(self, data: bytes):
        out = []
        self._buf.extend(data)
        text = self._buf.decode("latin-1")
        last_end = 0
        for match in _P25_SENTENCE.finditer(text):
            sentence = match.group(0)
            last_end = match.end()
            if not verify_nmea_checksum(sentence):
                continue
            fields = sentence.split("*", 1)[0].split(",")
            tag = fields[0][1:]
            if tag.endswith("GGA") and len(fields) >= 10:
                if fields[6] in ("", "0"):      # GGA fix-quality 0 = no fix
                    self._pending = None
                    continue
                try:
                    lat = nmea_coord_to_decimal(fields[2], fields[3])
                    lon = nmea_coord_to_decimal(fields[4], fields[5])
                except ValueError:
                    self._pending = None
                    continue
                if abs(lat) < 1e-6 and abs(lon) < 1e-6:   # null island = no real fix
                    self._pending = None
                    continue
                self._pending = (lat, lon, fields[9], fields[7], fields[1])
            elif tag == "PP25" and len(fields) >= 2 and fields[1].strip():
                if self._pending is not None:
                    lat, lon, alt, sats, utc = self._pending
                    out.append((fields[1].strip(), lat, lon, alt, sats, utc))
                    self._pending = None
        if last_end:
            del self._buf[:last_end]
        if len(self._buf) > 8192:
            del self._buf[:-2048]
        return out


def _p25_subscribe_bytes() -> bytes:
    return bytes.fromhex(P25_SUBSCRIBE_HEX.replace(" ", ""))


def p25_reader_loop(stop_event, out_q) -> None:
    """Producer thread: connect to the relay, parse fixes, push them on out_q.

    Pushes ('fix', unit_id, lat, lon, alt, sats, utc) and ('log', message).
    Never touches ArcGIS Earth - the main thread owns every draw. Reconnects on
    its own and keeps quiet while the radio is simply not there."""
    subscribe = _p25_subscribe_bytes()
    said_unreachable = False
    while not stop_event.is_set():
        sock = None
        try:
            sock = socket.create_connection((P25_RADIO_IP, P25_RADIO_PORT), timeout=6)
            sock.sendall(subscribe)
            sock.settimeout(0.5)
            said_unreachable = False
            out_q.put(("log", f"P25_CONNECTED {P25_RADIO_IP}:{P25_RADIO_PORT} - listening for GPS"))
            parser = P25StreamParser()
            last_keep = last_data = time.monotonic()
            while not stop_event.is_set():
                try:
                    data = sock.recv(65535)
                except socket.timeout:
                    data = b""
                except OSError:
                    break
                now = time.monotonic()
                if data:
                    last_data = now
                    for fix in parser.feed(data):
                        out_q.put(("fix",) + fix)
                if P25_KEEPALIVE_SECONDS and now - last_keep > P25_KEEPALIVE_SECONDS:
                    try:
                        sock.sendall(subscribe)
                    except OSError:
                        break
                    last_keep = now
                if now - last_data > P25_WATCHDOG_SECONDS:
                    out_q.put(("log", f"P25 link quiet > {P25_WATCHDOG_SECONDS}s - reconnecting"))
                    break
        except OSError as exc:
            if not said_unreachable:
                out_q.put(("log",
                           f"P25 radio not reachable at {P25_RADIO_IP}:{P25_RADIO_PORT} "
                           f"({exc.__class__.__name__}) - will keep trying quietly"))
                said_unreachable = True
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        if stop_event.is_set():
            break
        stop_event.wait(P25_RECONNECT_SECONDS)


# ---- P25 aliases, markers, drawings (main thread only) ----

def p25_marker_path(stale: bool) -> Path | None:
    name = P25_MARKER_STALE_FILENAME if stale else P25_MARKER_FILENAME
    candidate = script_dir() / name
    return candidate if candidate.is_file() else None


def p25_alias_path() -> Path:
    return script_dir() / P25_ALIAS_FILENAME


def load_p25_aliases() -> dict:
    path = p25_alias_path()
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def p25_alias(state: TrackerState, unit_id: str):
    return (state.p25_aliases or {}).get(unit_id)


def p25_label(state: TrackerState, unit: P25Unit) -> str:
    """'Jax 24' (or the raw ID), plus age once quiet for STALE_AFTER_MINUTES."""
    name = p25_alias(state, unit.unit_id) or unit.unit_id
    if not STALE_AFTER_MINUTES or not unit.received_monotonic:
        return name
    minutes = int((time.monotonic() - unit.received_monotonic) // 60)
    if minutes < STALE_AFTER_MINUTES:
        return name
    if minutes < 60:
        return f"{name} · {minutes} min"
    return f"{name} · {minutes // 60} h {minutes % 60:02d} min"


def p25_is_stale(unit: P25Unit) -> bool:
    if not STALE_AFTER_MINUTES or not unit.received_monotonic:
        return False
    return (time.monotonic() - unit.received_monotonic) >= STALE_AFTER_MINUTES * 60


def p25_drawing_id(unit_id: str) -> str:
    return f"{P25_DRAWING_ID_PREFIX}{unit_id}"


def build_p25_drawing(state: TrackerState, unit: P25Unit) -> dict:
    payload = {
        "id": p25_drawing_id(unit.unit_id),
        "visible": True,
        "title": p25_label(state, unit),
        "geometry": {"x": unit.lon, "y": unit.lat, "spatialReference": {"wkid": 4326}},
        "labelSymbol": {"type": "text", "color": LABEL_COLOR, "size": LABEL_SIZE},
    }
    icon = p25_marker_path(p25_is_stale(unit))
    if icon is not None:
        payload["symbol"] = {
            "type": "picture-marker",
            "url": str(icon),
            "size": f"{P25_MARKER_SIZE_PX}px",
        }
    return payload


def delete_p25_drawing(unit_id: str, ignore_missing: bool = True) -> None:
    path = f"/arcgisearth/drawings/{p25_drawing_id(unit_id)}"
    try:
        http_json("DELETE", path)
    except RuntimeError as exc:
        text = str(exc)
        if ignore_missing and ("HTTP 404" in text or "not found" in text.lower()):
            return
        raise


def post_p25_drawing(state: TrackerState, unit: P25Unit) -> None:
    http_json("POST", "/arcgisearth/drawings", build_p25_drawing(state, unit))


def replace_p25_drawing(state: TrackerState, unit: P25Unit) -> None:
    delete_p25_drawing(unit.unit_id, ignore_missing=True)
    post_p25_drawing(state, unit)


def merge_p25_unit(db: dict, unit_id: str, lat: float, lon: float,
                   alt: str, sats: str, utc: str) -> P25Unit:
    existing = db.get(unit_id)
    count = (existing.packet_count + 1) if existing else 1
    unit = P25Unit(
        unit_id=unit_id, lat=lat, lon=lon, alt=alt, sats=sats, gps_utc=utc,
        last_seen_local=datetime.now(), received_monotonic=time.monotonic(),
        packet_count=count,
    )
    db[unit_id] = unit
    return unit


def p25_csv_path() -> Path:
    return log_dir() / daily(P25_CSV_FILENAME)


def record_p25(unit: P25Unit) -> None:
    append_csv(
        p25_csv_path(),
        ["received_local", "gps_utc", "unit_id", "latitude", "longitude",
         "altitude_m", "satellites", "packet_count_session"],
        [unit.last_seen_local.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], unit.gps_utc,
         unit.unit_id, f"{unit.lat:.7f}", f"{unit.lon:.7f}", unit.alt, unit.sats,
         unit.packet_count],
    )


def session_p25_state_path() -> Path:
    return script_dir() / P25_STATE_FILENAME


def load_previous_p25_ids() -> list:
    path = session_p25_state_path()
    try:
        if path.is_file():
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, list):
                return [str(x) for x in value]
    except Exception:
        pass
    return []


def save_current_p25_ids(db: dict) -> None:
    try:
        session_p25_state_path().write_text(json.dumps(sorted(db), indent=2), encoding="utf-8")
    except Exception as exc:
        log_message(f"P25_STATE_WARNING could not save unit state: {exc}")


def reload_p25_aliases_if_changed(state: TrackerState) -> None:
    """Pick up edits to p25_aliases.json (made by hand or the alias editor) and
    relabel the affected markers right away."""
    path = p25_alias_path()
    try:
        mtime = path.stat().st_mtime if path.is_file() else 0.0
    except OSError:
        return
    if mtime == state.p25_alias_mtime:
        return
    state.p25_aliases = load_p25_aliases()
    state.p25_alias_mtime = mtime
    if state.earth_down:
        state.p25_drawn.clear()     # redraw_everything relabels when Earth returns
        return
    for unit in list(state.p25.values()):
        try:
            if earth_action(state, lambda u=unit: replace_p25_drawing(state, u)):
                state.p25_drawn[unit.unit_id] = p25_label(state, unit)
        except Exception:
            pass


def refresh_p25_stale_labels(state: TrackerState) -> None:
    """Once a minute a quiet P25 unit's label shows its age ('Jax 24 · 12 min')."""
    if not STALE_AFTER_MINUTES or state.earth_down:
        return
    for unit in list(state.p25.values()):
        label = p25_label(state, unit)
        if state.p25_drawn.get(unit.unit_id) == label:
            continue
        try:
            if earth_action(state, lambda u=unit: replace_p25_drawing(state, u)):
                state.p25_drawn[unit.unit_id] = label
        except Exception as exc:
            state.counters.api_bad += 1
            log_message(f"API_BAD p25={unit.unit_id} reason={exc}")
        if state.earth_down:
            return


def sweep_p25(state: TrackerState) -> None:
    """Drop a P25 unit whose last fix is older than P25_EXPIRE_SECONDS."""
    if not P25_EXPIRE_SECONDS or state.earth_down:
        return
    now = time.monotonic()
    expired = [uid for uid, unit in state.p25.items()
               if unit.received_monotonic and now - unit.received_monotonic > P25_EXPIRE_SECONDS]
    for uid in expired:
        try:
            earth_action(state, lambda i=uid: delete_p25_drawing(i))
        except Exception:
            pass
        state.p25.pop(uid, None)
        state.p25_drawn.pop(uid, None)
        save_current_p25_ids(state.p25)
        log_message(f"P25_EXPIRE {uid} - silent > {P25_EXPIRE_SECONDS // 60} min, marker removed")


def drain_p25(state: TrackerState) -> None:
    """Main-thread consumer: pull fixes/logs the reader thread queued and draw them
    through the shared earth_action() gate. Called every main-loop tick."""
    if state.p25_queue is None:
        return
    reload_p25_aliases_if_changed(state)
    for _ in range(500):            # bounded so one tick can't run away
        try:
            item = state.p25_queue.get_nowait()
        except queue.Empty:
            break
        if item[0] == "log":
            log_message(item[1])
            continue
        _, unit_id, lat, lon, alt, sats, utc = item
        unit = merge_p25_unit(state.p25, unit_id, lat, lon, alt, sats, utc)
        state.counters.valid_p25 += 1
        record_p25(unit)
        save_current_p25_ids(state.p25)
        try:
            if earth_action(state, lambda u=unit: replace_p25_drawing(state, u)):
                state.p25_drawn[unit.unit_id] = p25_label(state, unit)
        except Exception as exc:
            state.counters.api_bad += 1
            log_message(f"API_BAD p25={unit_id} reason={exc}")
        if SHOW_VALID_PRAVE:
            print(f"P25 -> EARTH {p25_label(state, unit)} "
                  f"POS={unit.lat:.7f},{unit.lon:.7f} COUNT={unit.packet_count}")
    sweep_p25(state)


def start_p25_source(state: TrackerState) -> None:
    """Start the P25 reader thread once (if enabled). Safe to call repeatedly."""
    if not P25_ENABLED or state.p25_thread is not None:
        return
    state.p25_aliases = load_p25_aliases()
    try:
        path = p25_alias_path()
        state.p25_alias_mtime = path.stat().st_mtime if path.is_file() else 0.0
    except OSError:
        state.p25_alias_mtime = 0.0
    state.p25_queue = queue.Queue()
    state.p25_stop = threading.Event()
    state.p25_thread = threading.Thread(
        target=p25_reader_loop, args=(state.p25_stop, state.p25_queue), daemon=True)
    state.p25_thread.start()
    log_message(f"P25_SOURCE enabled - reader thread listening to {P25_RADIO_IP}:{P25_RADIO_PORT}")


def stop_p25_source(state: TrackerState) -> None:
    if state.p25_stop is not None:
        state.p25_stop.set()


# ------------------------------------------------------------
# Serial engine
# ------------------------------------------------------------

def ports_on_this_pc() -> list[str]:
    try:
        from serial.tools import list_ports
        return sorted(p.device for p in list_ports.comports())
    except Exception:
        return []


def open_input_port():
    if serial is None:
        raise RuntimeError("pyserial is not installed; run: py -m pip install pyserial")
    try:
        return _open_serial()
    except serial.SerialException as exc:
        text = str(exc)
        ports = ports_on_this_pc()
        if "PermissionError" in text or "Access is denied" in text or "Errno 13" in text or "Errno 16" in text:
            raise PortProblem(
                f"{INPUT_PORT} is in use by another program (the PRAVE tester, another tracker or a "
                "terminal program). Close that program - the tracker keeps trying."
            ) from None
        if INPUT_PORT not in ports and ("FileNotFoundError" in text or "Errno 2" in text or "cannot find" in text):
            raise PortProblem(
                f"{INPUT_PORT} was not found. Serial ports on this PC: {', '.join(ports) or 'none'}. "
                "Plug in the radio cable, or set INPUT_PORT at the top of System Files\\PRAVE_ME_Tracker.py "
                "to one of those ports. The tracker keeps trying."
            ) from None
        raise


def _open_serial():
    return serial.Serial(
        port=INPUT_PORT,
        baudrate=INPUT_BAUD,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=0.25,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    )


def poll_me_tracking_toggle() -> None:
    global me_tracking_enabled
    if msvcrt is None or not msvcrt.kbhit():
        return
    key = msvcrt.getwch().lower()
    if key != "t":
        return
    me_tracking_enabled = not me_tracking_enabled
    state = "ON" if me_tracking_enabled else "OFF"
    print(f"\nME TRACKING {state}")
    log_message(f"ME_TRACKING {state}")


def update_me_when_tracking(position: RMCPosition) -> None:
    if not me_tracking_enabled:
        return
    replace_me_drawing(position)
    center_camera_on_me(position)


def print_banner() -> None:
    print()
    print("============================================================")
    print(f"   ARCGIS EARTH PRAVE / ME TRACKER - v{VERSION}")
    print("============================================================")
    print(f"Mixed serial input : {INPUT_PORT} @ {INPUT_BAUD} 8-N-1")
    print(f"ArcGIS Earth API   : {ARCGIS_EARTH_API_BASE}")
    print(f"RSSI icon folder   : {ICON_FOLDER}")
    if P25_ENABLED:
        print(f"P25 GPS relay      : {P25_RADIO_IP}:{P25_RADIO_PORT}  (BK base radio, USB RNDIS)")
    else:
        print("P25 GPS relay      : OFF (P25_ENABLED = False)")
    print()
    print("$PRAVE -> native ArcGIS Earth point drawing + label")
    print("$GPRMC -> ME point + camera center tracking at current zoom")
    if P25_ENABLED:
        print("$PP25  -> P25 field-radio point drawing + alias label (same map, same API)")
    print("Press T in this window to toggle ME tracking ON/OFF")
    print("Other NMEA -> ignored")
    print()
    print("No KML writer. No NetworkLink refresh loop. No Internet.")
    print("============================================================")
    print()


def print_summary(counters: Counters, units: dict[str, PRAVEUnit], me: RMCPosition | None) -> None:
    if not SHOW_STATUS_SUMMARY:
        return
    print(
        f"STATUS RMC={counters.valid_rmc} PRAVE={counters.valid_prave} "
        f"P25={counters.valid_p25} "
        f"UNITS={len(units)} API_OK={counters.api_ok} API_BAD={counters.api_bad} "
        f"BAD_RMC={counters.bad_rmc} BAD_PRAVE={counters.bad_prave} "
        f"NO_FIX_RMC={counters.no_fix_rmc} "
        f"RMC={gps_freshness_text(me)}"
    )


def redraw_everything(state: TrackerState) -> None:
    """ArcGIS Earth came back (or was restarted): put every known unit and ME back at once."""
    for unit in list(state.units.values()):
        replace_unit_drawing(unit)
        state.drawn[unit.raw_id] = unit_label(unit)
    for unit in list(state.p25.values()):
        replace_p25_drawing(state, unit)
        state.p25_drawn[unit.unit_id] = p25_label(state, unit)
    if state.me is not None and me_tracking_enabled:
        replace_me_drawing(state.me)


def earth_action(state: TrackerState, action, count: bool = True) -> bool:
    """Run one ArcGIS Earth update. While ArcGIS Earth is gone, say so once and retry every
    EARTH_RETRY_SECONDS; when it answers again, say so once and redraw everything."""
    now = time.monotonic()
    if state.earth_down:
        if now < state.earth_next_try:
            return False
        try:
            redraw_everything(state)
        except EarthUnreachable:
            state.earth_next_try = now + EARTH_RETRY_SECONDS
            return False
        state.earth_down = False
        log_message(f"ARCGIS_EARTH_BACK - redrew {len(state.units)} PRAVE + {len(state.p25)} P25 unit(s)"
                    + (" and ME" if state.me is not None and me_tracking_enabled else ""))
    try:
        action()
    except EarthUnreachable as exc:
        state.counters.api_bad += 1
        state.earth_down = True
        state.earth_next_try = now + EARTH_RETRY_SECONDS
        log_message(f"ARCGIS_EARTH_LOST {exc} Units keep being logged; they come back on the map "
                    "as soon as ArcGIS Earth answers again.")
        return False
    if count:
        state.counters.api_ok += 1
    return True


def refresh_stale_labels(state: TrackerState) -> None:
    """Once a minute a quiet unit's label shows its age ('7-101 · 12 min')."""
    if not STALE_AFTER_MINUTES or state.earth_down:
        return
    for unit in list(state.units.values()):
        label = unit_label(unit)
        if state.drawn.get(unit.raw_id) == label:
            continue
        try:
            if earth_action(state, lambda u=unit: replace_unit_drawing(u)):
                state.drawn[unit.raw_id] = label
        except Exception as api_exc:
            state.counters.api_bad += 1
            log_message(f"API_BAD unit={unit.display_id} reason={api_exc}")
        if state.earth_down:
            return
    refresh_p25_stale_labels(state)


def run_gateway_once(state: TrackerState) -> None:
    ensure_directories()
    check_arcgis_earth_api()
    # Old drawings are removed only once, when the tracker starts. A serial
    # reconnect keeps every unit on the map at its last reported position.
    if not state.startup_clean_done:
        clean_previous_session()
        state.startup_clean_done = True

    units = state.units
    counters = state.counters
    me = state.me
    last_summary = time.monotonic()
    if state.earth_down:          # ArcGIS Earth answered the startup check again
        state.earth_down = False
        state.earth_next_try = 0.0
        redraw_everything(state)
        log_message(f"ARCGIS_EARTH_BACK - redrew {len(units)} PRAVE + {len(state.p25)} P25 unit(s)")

    with open_input_port() as ser_in:
        ser_in.reset_input_buffer()
        log_message(
            f"START input={INPUT_PORT}@{INPUT_BAUD} api={ARCGIS_EARTH_API_BASE} "
            f"icons={ICON_FOLDER}"
        )
        log_message("ARCGIS_EARTH_API_CONNECTED")
        log_message(f"SERIAL_CONNECTED {INPUT_PORT}@{INPUT_BAUD} 8-N-1 flow=none")
        state.last_problem = ""

        while True:
            poll_me_tracking_toggle()
            raw = ser_in.readline()
            now_mono = time.monotonic()

            # P25 source shares this loop and the one ArcGIS Earth gate. Drained
            # every tick (readline's 0.25 s timeout) so it keeps flowing even when
            # the Raveon serial side is streaming or silent.
            drain_p25(state)

            if raw:
                line = raw.decode("ascii", errors="ignore").strip()
                counters.rx_lines += 1
                if not line:
                    continue

                if line.startswith("$GPRMC") or line.startswith("$GNRMC"):
                    try:
                        parsed_rmc = parse_rmc_sentence(line)
                    except RMCNoFix:
                        # Valid sentence, no GPS fix: log the change once, not every second.
                        counters.no_fix_rmc += 1
                        if not state.gps_no_fix:
                            state.gps_no_fix = True
                            log_message("GPS_NO_FIX RMC status V - waiting for a GPS fix")
                        continue
                    except Exception as exc:
                        counters.bad_rmc += 1
                        log_message(f"RMC_BAD reason={exc} raw={line}")
                        continue
                    if parsed_rmc is None:
                        continue
                    if state.gps_no_fix:
                        state.gps_no_fix = False
                        log_message("GPS_FIX_RESTORED")
                    me = state.me = parsed_rmc
                    counters.valid_rmc += 1
                    record_rmc(me)

                    try:
                        earth_action(state, lambda: update_me_when_tracking(me), count=me_tracking_enabled)
                    except Exception as api_exc:
                        # An ArcGIS Earth problem, not a bad sentence.
                        counters.api_bad += 1
                        log_message(f"API_BAD ME reason={api_exc}")
                        continue

                    if SHOW_VALID_RMC:
                        print(
                            f"RMC -> ME {'CENTER' if me_tracking_enabled else 'TRACKING OFF'} "
                            f"{me.lat:.7f},{me.lon:.7f} UTC={me.gps_utc.isoformat()}"
                        )
                    continue

                if line.startswith("$PRAVE"):
                    try:
                        parsed_prave = parse_prave_sentence(line)
                    except Exception as exc:
                        counters.bad_prave += 1
                        log_message(f"PRAVE_BAD reason={exc} raw={line}")
                        continue
                    if parsed_prave is None:
                        continue
                    unit = merge_prave_unit(units, parsed_prave)
                    counters.valid_prave += 1
                    record_prave(unit)

                    save_current_unit_ids(units)
                    try:
                        if earth_action(state, lambda: replace_unit_drawing(unit)):
                            state.drawn[unit.raw_id] = unit_label(unit)
                    except Exception as api_exc:
                        # An ArcGIS Earth problem, not a bad sentence.
                        counters.api_bad += 1
                        log_message(
                            f"API_BAD unit={unit.display_id} reason={api_exc}"
                        )
                        continue

                    if SHOW_VALID_PRAVE:
                        print(
                            f"PRAVE -> EARTH {unit.display_id} "
                            f"RSSI={format_rssi(unit.rssi_dbm)} "
                            f"ICON={unit.rssi_level} "
                            f"POS={unit.lat:.7f},{unit.lon:.7f} "
                            f"COUNT={unit.packet_count}"
                        )
                    continue

                counters.ignored += 1
                if SHOW_IGNORED_SENTENCES:
                    print(f"IGNORED {line}")

            if now_mono - last_summary >= 10.0:
                print_summary(counters, units, state.me)
                last_summary = now_mono
                if state.earth_down:
                    earth_action(state, lambda: None, count=False)   # quiet retry + redraw when back
                refresh_stale_labels(state)


# ------------------------------------------------------------
# Self-test: parser + ArcGIS drawing payload construction
# ------------------------------------------------------------

def run_self_test() -> int:
    failures: list[str] = []

    rmc = make_nmea_sentence(
        "GPRMC,212246.00,A,3025.14642,N,08155.58994,W,0.0,0.0,240726,,,A"
    )
    try:
        parsed_rmc = parse_rmc_sentence(rmc)
        assert parsed_rmc is not None
        assert parsed_rmc.gps_utc == datetime(
            2026, 7, 24, 21, 22, 46, tzinfo=timezone.utc
        )
        assert abs(parsed_rmc.lat - 30.419107) < 0.000001
        assert abs(parsed_rmc.lon - (-81.926499)) < 0.000001
    except Exception as exc:
        failures.append(f"RMC parser: {exc}")

    try:
        assert parsed_rmc is not None
        me_payload = build_me_drawing(parsed_rmc)
        assert me_payload["id"] == ME_DRAWING_ID
        assert me_payload["title"] == "ME"
        assert me_payload["geometry"]["x"] == parsed_rmc.lon
        assert me_payload["geometry"]["y"] == parsed_rmc.lat

        current_camera = {
            "position": {
                "x": -81.0,
                "y": 30.0,
                "z": 4321.0,
                "spatialReference": {"wkid": 4326},
            },
            "heading": 17.0,
            "tilt": 0.0,
            "roll": 0.0,
        }
        tracked_camera = build_me_tracking_camera(current_camera, parsed_rmc)
        assert tracked_camera["position"]["x"] == parsed_rmc.lon
        assert tracked_camera["position"]["y"] == parsed_rmc.lat
        assert tracked_camera["position"]["z"] == 4321.0
        assert tracked_camera["heading"] == 17.0
        assert tracked_camera["tilt"] == 0.0
        assert tracked_camera["roll"] == 0.0
    except Exception as exc:
        failures.append(f"ME drawing/camera tracking: {exc}")

    expected = [
        ("101", "", 0),
        ("102", "-115", 1),
        ("103", "-105", 2),
        ("104", "-95", 3),
        ("105", "-85", 4),
        ("106", "-75", 5),
    ]

    for individual, rssi_text, level in expected:
        body = (
            f"PRAVE,01{individual[-2:]},1234,3025.32642,-08155.58994,212248,"
            f"2,12,7,0,12.80,0,{rssi_text},{individual},0,,"
        )
        sentence = make_nmea_sentence(body)
        try:
            parsed = parse_prave_sentence(sentence)
            assert parsed is not None
            assert parsed.display_id == f"7-{individual}"
            assert parsed.rssi_level == level
            payload = build_unit_drawing(parsed)
            assert payload["id"] == f"{DRAWING_ID_PREFIX}7{individual}"
            assert payload["title"] == f"7-{individual}"
            assert payload["geometry"]["spatialReference"]["wkid"] == 4326
            assert payload["labelSymbol"]["type"] == "text"
        except Exception as exc:
            failures.append(f"PRAVE {individual}: {exc}")

    # P25 relay parser + drawing (added in 3.0).
    try:
        gga = make_nmea_sentence(
            "GNGGA,145623.00,3025.14642,N,08155.58994,W,1,09,0.9,5.2,M,-30.0,M,,")
        pp25 = make_nmea_sentence("PP25,9076801,")
        fixes = P25StreamParser().feed((gga + "\r\n" + pp25 + "\r\n").encode("ascii"))
        assert len(fixes) == 1, f"expected 1 P25 fix, got {len(fixes)}"
        uid, lat, lon, alt, sats, _utc = fixes[0]
        assert uid == "9076801", f"unit id {uid}"
        assert abs(lat - 30.419107) < 1e-6, f"lat {lat}"
        assert abs(lon - (-81.926499)) < 1e-6, f"lon {lon}"
        assert sats == "09", f"sats {sats}"

        # A no-fix GGA (quality 0) must not produce a position.
        gga0 = make_nmea_sentence("GNGGA,145624.00,,,,,0,00,,,M,,M,,")
        assert P25StreamParser().feed((gga0 + "\r\n" + pp25 + "\r\n").encode("ascii")) == []

        unit = merge_p25_unit({}, uid, lat, lon, alt, sats, _utc)
        state = TrackerState(units={}, counters=Counters())
        payload = build_p25_drawing(state, unit)
        assert payload["id"] == "AE_P25_9076801"
        assert payload["title"] == "9076801"
        assert payload["geometry"]["x"] == lon and payload["geometry"]["y"] == lat
        assert payload["geometry"]["spatialReference"]["wkid"] == 4326
        assert payload["labelSymbol"]["type"] == "text"
        state.p25_aliases = {"9076801": "Jax 24"}
        assert p25_label(state, unit) == "Jax 24", "alias relabel"
    except Exception as exc:
        failures.append(f"P25 parser/drawing: {exc}")

    if failures:
        print("SELF TEST: FAIL")
        for failure in failures:
            print(" -", failure)
        return 1

    print("SELF TEST: PASS")
    print(" - Gold RMC parser preserved")
    print(" - ME point drawing + camera tracking payload constructed")
    print(" - Current camera height/orientation preserved while X/Y follow ME")
    print(" - ME tracking toggle control present (T key)")
    print(" - Gold PRAVE parser preserved")
    print(" - IDs 7-101 through 7-106 preserved")
    print(" - RSSI levels unknown + 1-5 preserved")
    print(" - ArcGIS Earth drawing payloads constructed")
    print(" - Native point labels configured")
    print(" - P25 relay parser: GGA+PP25 pair -> unit 9076801 at the right position")
    print(" - P25 no-fix GGA rejected; AE_P25_ drawing + alias label constructed")
    return 0


def sleep_or_pump_p25(state: TrackerState, seconds: float) -> None:
    """Wait `seconds`, but keep draining the P25 feed if it is enabled, so a
    Raveon serial outage never freezes the P25 side of the map."""
    if not P25_ENABLED or state.p25_queue is None:
        time.sleep(seconds)
        return
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            drain_p25(state)
        except Exception:
            pass
        time.sleep(0.25)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"ArcGIS Earth PRAVE / ME Tracker v{VERSION}"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Verify parsers and ArcGIS drawing payloads without serial or ArcGIS Earth.",
    )
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    print_banner()

    # pyserial cannot appear while the tracker is running, so report it once and stop.
    if serial is None:
        log_message("ERROR pyserial is not installed; run: py -m pip install pyserial")
        return 1

    check_icon_folder()

    # Units, counters and the startup-clean flag survive serial reconnects.
    state = TrackerState(units={}, counters=Counters())

    # Start the P25 reader thread once. It only parses and queues; the main loop
    # (and the reconnect wait below) draws its fixes through the one Earth gate.
    start_p25_source(state)

    while True:
        try:
            run_gateway_once(state)
            stop_p25_source(state)
            return 0
        except KeyboardInterrupt:
            print("\nStopped by user.")
            log_message("STOP user keyboard interrupt")
            stop_p25_source(state)
            return 0
        except Exception as exc:
            # Say each problem once; while it lasts, keep trying quietly.
            if isinstance(exc, EarthUnreachable):
                state.earth_down = True
            if str(exc) != state.last_problem:
                state.last_problem = str(exc)
                log_message(f"ERROR {exc}")
                if not AUTO_RECONNECT:
                    stop_p25_source(state)
                    return 1
                log_message(f"RECONNECT trying every {RECONNECT_DELAY_SECONDS:.0f} seconds (quietly until something changes)")
            elif not AUTO_RECONNECT:
                stop_p25_source(state)
                return 1
            try:
                # Keep the P25 feed alive while the Raveon serial side is down.
                sleep_or_pump_p25(state, RECONNECT_DELAY_SECONDS)
            except KeyboardInterrupt:
                print("\nStopped by user.")
                log_message("STOP user keyboard interrupt")
                stop_p25_source(state)
                return 0


if __name__ == "__main__":
    raise SystemExit(main())
