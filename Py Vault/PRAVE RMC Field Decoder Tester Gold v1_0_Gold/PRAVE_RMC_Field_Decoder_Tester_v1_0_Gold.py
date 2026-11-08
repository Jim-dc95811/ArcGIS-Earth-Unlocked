"""
PRAVE / RMC Field Decoder Tester - Version 1.0 Gold

Purpose:
    Generate one mixed serial stream that resembles the Raveon field input expected
    by the PRAVE / ME / Time Keeper decoder:

        - One valid $GPRMC sentence every second for ME position and UTC date/time.
        - Valid $PRAVE sentences at randomized intervals for six remote units.
        - Six RSSI test states: unknown plus one through five bars.

The six remote units remain at fixed positions around the local ME position so all
RSSI icon variants can be inspected simultaneously in Google Earth.

Project philosophy:
    Friends don't let friends edit Python.
    Change the settings below. Leave the dragons alone.

Version:
    1.0 Gold
"""

# ============================================================
#
#                    USER CONFIGURATION
#
#        This is the only section most users should edit.
#
# ============================================================

# Serial output connected to the decoder's mixed-input COM port.
OUTPUT_PORT = "COM12"
OUTPUT_BAUD = 19200

# Normal field behavior: RMC once per second; PRAVE arrives asynchronously.
RMC_INTERVAL_SECONDS = 1.0
PRAVE_MIN_INTERVAL_SECONDS = 1.5
PRAVE_MAX_INTERVAL_SECONDS = 3.5

# Reconnect if the USB/serial path is unplugged.
AUTO_RECONNECT = True
RECONNECT_DELAY_SECONDS = 5.0

# Console and text-log behavior.
SHOW_RMC_SENTENCES = True
SHOW_PRAVE_SENTENCES = True
ENABLE_TEXT_LOG = True
LOG_FILE = "logs/prave_rmc_field_decoder_tester_activity_log.txt"

# Local ME position used by every generated $GPRMC sentence.
LOCAL_ME_LAT = 30.419107
LOCAL_ME_LON = -81.926499

# Optional deterministic shuffle for repeated bench demonstrations.
# Set to an integer such as 22 for repeatable order, or None for fresh randomness.
RANDOM_SEED = None

# Six remote units.  RSSI None creates a valid PRAVE sentence with a blank RSSI
# field so the decoder should select firetruck_rssi_unknown.png.
#
# The numeric test values are centered inside the initial Version 1 icon bands:
#   1 bar: -120 through -111 dBm
#   2 bars: -110 through -101 dBm
#   3 bars: -100 through  -91 dBm
#   4 bars:  -90 through  -81 dBm
#   5 bars:  -80 dBm or stronger
TEST_UNITS = [
    {"district": "7", "individual": "101", "lat": 30.422107, "lon": -81.929999, "rssi": None, "expected": "unknown"},
    {"district": "7", "individual": "102", "lat": 30.422107, "lon": -81.926499, "rssi": -115, "expected": "1 bar"},
    {"district": "7", "individual": "103", "lat": 30.422107, "lon": -81.922999, "rssi": -105, "expected": "2 bars"},
    {"district": "7", "individual": "104", "lat": 30.416107, "lon": -81.929999, "rssi": -95,  "expected": "3 bars"},
    {"district": "7", "individual": "105", "lat": 30.416107, "lon": -81.926499, "rssi": -85,  "expected": "4 bars"},
    {"district": "7", "individual": "106", "lat": 30.416107, "lon": -81.922999, "rssi": -75,  "expected": "5 bars"},
]

# PRAVE fields that are not central to this test but are kept realistic.
PRAVE_SEND_TO = "1234"
PRAVE_GPS_STATUS = "2"
PRAVE_SATELLITES = "12"
PRAVE_ATAI = "0"
PRAVE_VOLTAGE = "12.80"
PRAVE_IO = "0"
PRAVE_STATE_ID = "0"


# ============================================================
#
#                    HERE BE DRAGONS
#
#        Program code below this line should not need editing.
#
# ============================================================

import argparse
import datetime as dt
from pathlib import Path
import random
import sys
import time
from typing import Any

try:
    import serial  # pyserial
except ImportError:
    serial = None


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def resolve_near_script(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else script_dir() / path


def write_log(message: str) -> None:
    if not ENABLE_TEXT_LOG:
        return
    try:
        log_path = resolve_near_script(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}] {message}\n")
    except Exception:
        # Logging must never stop the tester.
        pass


def nmea_checksum(body: str) -> str:
    value = 0
    for character in body:
        value ^= ord(character)
    return f"{value:02X}"


def verify_nmea_checksum(sentence: str) -> bool:
    sentence = sentence.strip()
    if not sentence.startswith("$") or "*" not in sentence:
        return False
    body, given = sentence[1:].split("*", 1)
    return len(given) >= 2 and nmea_checksum(body) == given[:2].upper()


def wrap_nmea_body(body: str) -> str:
    return f"${body}*{nmea_checksum(body)}"


def decimal_to_nmea(value: float, is_latitude: bool) -> tuple[str, str]:
    absolute = abs(value)
    degrees = int(absolute)
    minutes = (absolute - degrees) * 60.0
    degree_width = 2 if is_latitude else 3
    field = f"{degrees:0{degree_width}d}{minutes:08.5f}"

    if is_latitude:
        hemisphere = "N" if value >= 0 else "S"
    else:
        hemisphere = "E" if value >= 0 else "W"

    return field, hemisphere


def decimal_to_signed_prave(value: float, is_latitude: bool) -> str:
    field, hemisphere = decimal_to_nmea(value, is_latitude)
    negative = hemisphere in ("S", "W")
    return f"-{field}" if negative else field


def make_gprmc_sentence(now_utc: dt.datetime) -> str:
    lat_field, lat_hemi = decimal_to_nmea(LOCAL_ME_LAT, True)
    lon_field, lon_hemi = decimal_to_nmea(LOCAL_ME_LON, False)

    utc_text = now_utc.strftime("%H%M%S") + ".00"
    date_text = now_utc.strftime("%d%m%y")

    body = ",".join([
        "GPRMC",
        utc_text,
        "A",
        lat_field,
        lat_hemi,
        lon_field,
        lon_hemi,
        "0.0",
        "0.0",
        date_text,
        "",
        "",
        "A",
    ])
    return wrap_nmea_body(body)


def make_prave_sentence(unit: dict[str, Any], now_utc: dt.datetime) -> str:
    individual = str(unit["individual"]).zfill(3)
    time_slot = individual[-4:].zfill(4)
    rssi_text = "" if unit["rssi"] is None else str(int(unit["rssi"]))

    fields = [
        "$PRAVE",                                                   # index 0: header
        time_slot,                                                   # index 1: time slot
        PRAVE_SEND_TO,                                               # index 2: send to
        decimal_to_signed_prave(float(unit["lat"]), True),          # index 3: latitude
        decimal_to_signed_prave(float(unit["lon"]), False),         # index 4: longitude
        now_utc.strftime("%H%M%S"),                                 # index 5: UTC
        PRAVE_GPS_STATUS,                                            # index 6: GPS status
        PRAVE_SATELLITES,                                            # index 7: satellites
        str(unit["district"]),                                      # index 8: district ID
        PRAVE_ATAI,                                                  # index 9: ATAI
        PRAVE_VOLTAGE,                                               # index 10: voltage
        PRAVE_IO,                                                    # index 11: I/O
        rssi_text,                                                   # index 12: RSSI
        individual,                                                  # index 13: individual ID
        PRAVE_STATE_ID,                                              # index 14: state ID
        "",                                                          # index 15: optional
        "",                                                          # index 16: optional
    ]

    body = ",".join(fields)[1:]  # Remove the leading dollar sign for checksum.
    return wrap_nmea_body(body)


def send_sentence(port: Any, sentence: str) -> None:
    port.write((sentence + "\r\n").encode("ascii", errors="strict"))


def unit_display_id(unit: dict[str, Any]) -> str:
    return f"{unit['district']}-{str(unit['individual']).zfill(3)}"


def print_startup_banner() -> None:
    print()
    print("============================================================")
    print("      PRAVE / RMC Field Decoder Tester - Version 1.0 Gold")
    print("============================================================")
    print()
    print(f"Mixed output : {OUTPUT_PORT} @ {OUTPUT_BAUD}")
    print(f"RMC cadence  : every {RMC_INTERVAL_SECONDS:.1f} second")
    print(f"PRAVE cadence: randomized {PRAVE_MIN_INTERVAL_SECONDS:.1f} to {PRAVE_MAX_INTERVAL_SECONDS:.1f} seconds")
    print(f"ME position  : {LOCAL_ME_LAT:.6f}, {LOCAL_ME_LON:.6f}")
    print()
    print("Remote RSSI icon test fleet:")
    for unit in TEST_UNITS:
        rssi = "blank" if unit["rssi"] is None else f"{unit['rssi']} dBm"
        print(f"  {unit_display_id(unit):<6}  RSSI {rssi:<9}  expected {unit['expected']}")
    print()
    print("One valid $GPRMC is generated every second.")
    print("One valid $PRAVE is generated at each randomized PRAVE interval.")
    print("All six PRAVE units are sent once per shuffled cycle.")
    print()
    print("Friends don't let friends edit Python below the dragons.")
    print("============================================================")
    print()


def self_test() -> int:
    now_utc = dt.datetime.now(dt.timezone.utc)
    sentences = [make_gprmc_sentence(now_utc)]
    sentences.extend(make_prave_sentence(unit, now_utc) for unit in TEST_UNITS)

    print("PRAVE / RMC Field Decoder Tester self-test")
    print("-------------------------------------------")
    for sentence in sentences:
        status = "PASS" if verify_nmea_checksum(sentence) else "FAIL"
        print(f"{status}: {sentence}")

    failures = [sentence for sentence in sentences if not verify_nmea_checksum(sentence)]
    if failures:
        print(f"\nSELF-TEST FAILED: {len(failures)} bad checksum(s).")
        return 1

    print(f"\nSELF-TEST PASSED: {len(sentences)} valid NMEA sentences generated.")
    return 0


def run_connected_session() -> None:
    if PRAVE_MIN_INTERVAL_SECONDS <= 0 or PRAVE_MAX_INTERVAL_SECONDS < PRAVE_MIN_INTERVAL_SECONDS:
        raise ValueError("Invalid PRAVE interval configuration")
    if RMC_INTERVAL_SECONDS <= 0:
        raise ValueError("RMC_INTERVAL_SECONDS must be greater than zero")

    rng = random.Random(RANDOM_SEED)
    unit_cycle: list[dict[str, Any]] = []
    rmc_count = 0
    prave_count = 0

    print(f"Opening mixed test output {OUTPUT_PORT} @ {OUTPUT_BAUD}...")
    with serial.Serial(OUTPUT_PORT, OUTPUT_BAUD, timeout=1, write_timeout=2) as port:
        print("Output connected. Press Ctrl+C to stop.")
        print()
        write_log(f"START output={OUTPUT_PORT}@{OUTPUT_BAUD}")

        now_mono = time.monotonic()
        next_rmc = now_mono
        next_prave = now_mono + rng.uniform(PRAVE_MIN_INTERVAL_SECONDS, PRAVE_MAX_INTERVAL_SECONDS)

        while True:
            now_mono = time.monotonic()

            if now_mono >= next_rmc:
                now_utc = dt.datetime.now(dt.timezone.utc)
                sentence = make_gprmc_sentence(now_utc)
                send_sentence(port, sentence)
                rmc_count += 1
                if SHOW_RMC_SENTENCES:
                    print(f"RMC   {rmc_count:05d}: {sentence}")
                write_log(f"RMC_TX {sentence}")

                # Keep a stable one-second cadence without building a backlog.
                next_rmc += RMC_INTERVAL_SECONDS
                if next_rmc <= now_mono:
                    next_rmc = now_mono + RMC_INTERVAL_SECONDS

            if now_mono >= next_prave:
                if not unit_cycle:
                    unit_cycle = list(TEST_UNITS)
                    rng.shuffle(unit_cycle)

                unit = unit_cycle.pop(0)
                now_utc = dt.datetime.now(dt.timezone.utc)
                sentence = make_prave_sentence(unit, now_utc)
                send_sentence(port, sentence)
                prave_count += 1

                rssi = "blank" if unit["rssi"] is None else f"{unit['rssi']} dBm"
                if SHOW_PRAVE_SENTENCES:
                    print(
                        f"PRAVE {prave_count:05d}: {unit_display_id(unit)}  "
                        f"RSSI {rssi:<9}  expected {unit['expected']}\n"
                        f"             {sentence}"
                    )
                write_log(
                    f"PRAVE_TX id={unit_display_id(unit)} rssi={rssi} "
                    f"expected={unit['expected']} sentence={sentence}"
                )

                next_prave = now_mono + rng.uniform(
                    PRAVE_MIN_INTERVAL_SECONDS,
                    PRAVE_MAX_INTERVAL_SECONDS,
                )

            time.sleep(0.02)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate mixed GPRMC and PRAVE test sentences.")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Generate and checksum-test one RMC plus all six PRAVE sentences without opening a COM port.",
    )
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if serial is None:
        print("ERROR: pyserial is not installed.")
        print("Install it with: python -m pip install pyserial")
        return 1

    print_startup_banner()

    while True:
        try:
            run_connected_session()
            return 0
        except KeyboardInterrupt:
            print("\nTester stopped by user.")
            write_log("STOP user keyboard interrupt")
            return 0
        except Exception as exc:
            print()
            print(f"ERROR: {exc}")
            write_log(f"ERROR {exc}")

            if not AUTO_RECONNECT:
                return 1

            print(f"Waiting {RECONNECT_DELAY_SECONDS:.0f} seconds before reconnect...")
            print()
            time.sleep(RECONNECT_DELAY_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
