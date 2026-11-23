#!/usr/bin/env python3
"""
RNDIS NMEA Logger  -  the "answer key" recorder for P25-GPS-Decode.

Connects to the BK base relay over its USB-RNDIS TCP link, subscribes, and
writes every GPS sentence it hands us to a timestamped log file -- so the
decoded-from-the-air result can be diffed against known-good ground truth.

Radio facts + NMEA extractor are lifted VERBATIM from the proven bk_bridge.py
(The-Lookout).  Stdlib only.  Read-only: it never transmits to or alters a radio.

Run this NEXT TO Audacity while you record the DEO audio.  Each burst you hear
lands here as a timestamped $GNGGA/$PP25 -- that pairing is the whole experiment.
"""
import socket, re, time, os, sys
from datetime import datetime

VERSION = "1.0"

# ---- config (verbatim from bk_bridge.py) ----
RADIO_IP    = "10.250.46.6"
RADIO_PORT  = 65535
SUBSCRIBE   = bytes.fromhex("800418e481")   # 5-byte subscribe: 80 04 18 e4 81
KEEPALIVE_S = 20                            # re-send subscribe this often
RECONNECT_S = 3                             # wait this long before a reconnect

# ---- NMEA extraction (verbatim from p25_core.py / bk_bridge.py) ----
_SENTENCE = re.compile(r"\$[^*$\r\n]{2,88}\*[0-9A-Fa-f]{2}")

def _nmea_ok(s):
    body, _, chk = s[1:].partition("*")
    try:
        want = int(chk[:2], 16)
    except ValueError:
        return False
    g = 0
    for c in body:
        g ^= ord(c)
    return g == want

def _gga_latlon(s):
    """Best-effort lat/lon out of a $..GGA for the on-screen echo (never fatal)."""
    try:
        f = s.split(",")
        if "GGA" not in f[0]:
            return None
        lat = float(f[2][:2]) + float(f[2][2:]) / 60.0
        if f[3] == "S": lat = -lat
        lon = float(f[4][:3]) + float(f[4][3:]) / 60.0
        if f[5] == "W": lon = -lon
        return lat, lon
    except Exception:
        return None

def _stamp():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now().microsecond//1000:03d}"

def main():
    here   = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.dirname(here) if os.path.basename(here).lower() == "system files" else here
    start  = datetime.now().strftime("%Y%m%d_%H%M%S")
    logpath = os.path.join(outdir, f"rndis_nmea_{start}.log")
    rawpath = os.path.join(outdir, f"rndis_raw_{start}.bin")
    log = open(logpath, "a", encoding="ascii", errors="replace")
    raw = open(rawpath, "ab")

    print("=" * 62)
    print(f"  RNDIS NMEA Logger v{VERSION}  -  P25-GPS-Decode answer-key recorder")
    print(f"  radio {RADIO_IP}:{RADIO_PORT}   (read-only)")
    print(f"  log : {logpath}")
    print(f"  raw : {rawpath}")
    print("  Start your Audacity recording now.  Ctrl+C to stop.")
    print("=" * 62, flush=True)
    log.write(f"# RNDIS NMEA log  started {_stamp()}  radio {RADIO_IP}:{RADIO_PORT}\n"); log.flush()

    nfix = 0
    while True:
        try:
            s = socket.create_connection((RADIO_IP, RADIO_PORT), timeout=10)
            s.settimeout(1.0)
            s.sendall(SUBSCRIBE)
            print(f"[{_stamp()}] connected + subscribed - waiting for reports", flush=True)
            buf = ""
            last_ka = time.time()
            while True:
                now = time.time()
                if now - last_ka >= KEEPALIVE_S:
                    try: s.sendall(SUBSCRIBE)
                    except OSError: break
                    last_ka = now
                try:
                    data = s.recv(65535)
                except socket.timeout:
                    continue
                if not data:
                    break
                raw.write(data); raw.flush()
                buf += data.decode("ascii", "replace")
                if len(buf) > 8192:
                    buf = buf[-4096:]
                for m in _SENTENCE.finditer(buf):
                    sent = m.group(0)
                    if not _nmea_ok(sent):
                        continue
                    ts = _stamp()
                    log.write(f"{ts}  {sent}\n"); log.flush()
                    ll = _gga_latlon(sent)
                    if ll:
                        nfix += 1
                        print(f"[{ts}] FIX #{nfix}  {ll[0]:.6f}, {ll[1]:.6f}   {sent}", flush=True)
                    else:
                        print(f"[{ts}]           {sent}", flush=True)
                # keep only the tail past the last complete sentence
                last = 0
                for m in _SENTENCE.finditer(buf):
                    last = m.end()
                buf = buf[last:]
            s.close()
        except KeyboardInterrupt:
            break
        except OSError as e:
            print(f"[{_stamp()}] link down ({e}); reconnecting in {RECONNECT_S}s", flush=True)
            time.sleep(RECONNECT_S)
        except KeyboardInterrupt:
            break
    print(f"\nStopped.  {nfix} fixes logged to:\n  {logpath}")
    log.close(); raw.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
