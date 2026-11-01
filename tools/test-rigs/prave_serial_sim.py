"""Simulate a Raveon RMC/PRAVE feed at 19200 baud on a pseudo-terminal and read it
the way PRAVE_ME_Tracker.py v1.0 does (pyserial readline with timeout=0.25),
counting how many sentences arrive whole versus split."""
import os, pty, random, sys, threading, time, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pyserial-src"))
import serial

spec = importlib.util.spec_from_file_location(
    "tracker", os.path.join(os.path.dirname(__file__), "PRAVE_ME_Tracker_v1/PRAVE_ME_Tracker/PRAVE_ME_Tracker.py"))
tracker = importlib.util.module_from_spec(spec); sys.modules["tracker"] = tracker; spec.loader.exec_module(tracker)

DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
BYTE_TIME = 10 / 19200  # 8-N-1: 10 bits per byte

master, slave = pty.openpty()
os.set_blocking(master, True)
import termios, tty
tty.setraw(slave)
slave_name = os.ttyname(slave)

sent = {"RMC": 0, "PRAVE": 0}
stop = threading.Event()


def writer():
    rng = random.Random(7)
    t_next_rmc = time.monotonic() + 0.3
    t_next_prave = time.monotonic() + 0.9
    unit = 0
    while not stop.is_set():
        now = time.monotonic()
        if now >= t_next_rmc:
            body = "GPRMC,212246.00,A,3025.14642,N,08155.58994,W,0.0,0.0,240726,,,A"
            kind, t_next_rmc = "RMC", t_next_rmc + 1.0
        elif now >= t_next_prave:
            unit = unit % 6 + 1
            body = f"PRAVE,0101,1234,3025.32642,-08155.58994,212248,2,12,7,0,12.80,0,-95,10{unit},0,,"
            kind, t_next_prave = "PRAVE", t_next_prave + rng.uniform(1.5, 3.0)
        else:
            time.sleep(0.001)
            continue
        data = (tracker.make_nmea_sentence(body) + "\r\n").encode()
        # pace at the real line rate, 8 bytes at a time
        for i in range(0, len(data), 8):
            os.write(master, data[i:i + 8])
            time.sleep(BYTE_TIME * 8)
        sent[kind] += 1


def read_like_v1(ser, deadline):
    got = {"RMC": 0, "PRAVE": 0, "bad": 0, "fragments": 0}
    while time.monotonic() < deadline:
        raw = ser.readline()                      # exactly as v1.0 does
        if not raw:
            continue
        line = raw.decode("ascii", errors="ignore").strip()
        if not line:
            continue
        if line.startswith(("$GPRMC", "$GNRMC", "$PRAVE")):
            kind = "PRAVE" if line.startswith("$PRAVE") else "RMC"
            try:
                parsed = tracker.parse_rmc_sentence(line) if kind == "RMC" else tracker.parse_prave_sentence(line)
                got[kind] += parsed is not None
            except Exception:
                got["bad"] += 1
        else:
            got["fragments"] += 1                 # tail half of a split sentence
    return got


def read_buffered(ser, deadline):
    """Proposed fix: keep partial bytes until the newline arrives."""
    got = {"RMC": 0, "PRAVE": 0, "bad": 0, "fragments": 0}
    pending = b""
    while time.monotonic() < deadline:
        chunk = ser.readline()
        if not chunk:
            continue
        pending += chunk
        if not pending.endswith(b"\n"):
            continue                              # wait for the rest of the sentence
        raw, pending = pending, b""
        line = raw.decode("ascii", errors="ignore").strip()
        if not line:
            continue
        if line.startswith(("$GPRMC", "$GNRMC", "$PRAVE")):
            kind = "PRAVE" if line.startswith("$PRAVE") else "RMC"
            try:
                parsed = tracker.parse_rmc_sentence(line) if kind == "RMC" else tracker.parse_prave_sentence(line)
                got[kind] += parsed is not None
            except Exception:
                got["bad"] += 1
        else:
            got["fragments"] += 1
    return got


mode = sys.argv[2] if len(sys.argv) > 2 else "v1"
ser = serial.Serial(slave_name, 19200, timeout=0.25)
threading.Thread(target=writer, daemon=True).start()
deadline = time.monotonic() + DURATION
got = (read_like_v1 if mode == "v1" else read_buffered)(ser, deadline)
stop.set()
time.sleep(0.2)
total_sent = sent["RMC"] + sent["PRAVE"]
total_ok = got["RMC"] + got["PRAVE"]
print(f"[{mode}] {DURATION:.0f}s  sent RMC={sent['RMC']} PRAVE={sent['PRAVE']}  "
      f"decoded RMC={got['RMC']} PRAVE={got['PRAVE']}  bad={got['bad']} fragments={got['fragments']}  "
      f"lost={total_sent - total_ok} of {total_sent} ({100 * (total_sent - total_ok) / max(1, total_sent):.0f}%)")
