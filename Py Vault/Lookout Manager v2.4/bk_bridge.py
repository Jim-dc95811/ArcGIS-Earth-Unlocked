#!/usr/bin/env python3
"""bk_bridge.py - BK radio GPS -> network NMEA bridge  (Claude + Jim, 2026-11-14)

Turns a Raspberry Pi or OpenWrt router into a field bridge box: it reads the BK base
relay's framed GPS stream over the USB-RNDIS link (10.250.46.6:65535), pulls out the
standard NMEA sentences, and RE-SERVES them as a plain NMEA-over-TCP feed on port 10110
to any number of devices at once - PCs, phones, tablets. Plug the radio in, run this,
and the whole scene can read the same live feed over the network.

The sentence-finder + checksum are lifted verbatim from the proven P25 GPS Tracker
(p25_core.py), which is frame-agnostic: it never needs to decode the 80..81 wrapper,
it just scans the raw bytes for valid $....*cs sentences and verifies each one.

v1.1 (2026-11-15): one stuck/frozen viewer can no longer stall the feed for the others -
each client socket has a send timeout and a viewer that can't keep up is dropped, and
the fan-out no longer holds the lock while sending.

v1.2 (2026-11-15): the bridge now ANNOUNCES its radio link state into the feed, so the
map can raise an immediate alarm when the radio is unplugged instead of letting units
quietly go stale. It emits a $PLKT,LINK,UP / $PLKT,LINK,DOWN heartbeat every few seconds
(and instantly on any change). This is a proprietary NMEA sentence; other NMEA apps
ignore it. All sends still come from this one thread, so nothing interleaves on a socket.

v1.3 (2026-11-16): the box can now report its OWN position. A local USB GPS plugged into
the hub (a Garmin GPS 18 USB via gpsd or libusb, or any plain serial NMEA puck) is read by
gps_source.py in a separate daemon thread, and the box's fix is broadcast into the SAME
:10110 feed tagged as one reserved unit (SELF_ID) - so "you are here" shows on the map next
to the radio fleet, with NO change to the map. The radio reader is byte-for-byte unchanged;
if there is no GPS (or gps_source can't load), the bridge behaves exactly as v1.2.

v1.4 (2026-11-16): field hardening. (1) A quiet fleet no longer raises a false RADIO LINK
DOWN alarm - the link is held UP as long as the 20 s keepalive keeps succeeding (and usb0 is
up), so an idle fleet (no units transmitting for 90 s - normal) no longer triggers a
reconnect/alarm flap. SO_KEEPALIVE is set so the OS still catches a truly dead peer. (2) The
box's own GPS fix is coordinate-validated (in gps_source) before it's broadcast, so a glitchy
Garmin fix can't put the box at (0,0) or fling it.

Run:   python3 bk_bridge.py
Stop:  Ctrl+C
"""
import re, socket, threading, time, sys

try:
    import gps_source                            # the box's own-position reader (optional)
except Exception:
    gps_source = None

VERSION = "1.4"

# ---- upstream: the BK base relay ----
RADIO_IP    = "10.250.46.6"
RADIO_PORT  = 65535
RADIO_IFACE = "usb0"                          # the radio's USB interface (instant unplug detection)
SUBSCRIBE   = bytes.fromhex("800418e481")     # the 5-byte subscribe: 80 04 18 e4 81
KEEPALIVE_S = 20                              # re-send subscribe this often
WATCHDOG_S  = 90                              # no bytes at all this long -> reconnect
RECONNECT_S = 4

# ---- downstream: who we serve the NMEA to ----
SERVE_HOST     = "0.0.0.0"                    # all of the box's networks (LAN, etc.)
SERVE_PORT     = 10110                        # the standard NMEA-0183-over-TCP port
HEARTBEAT_S    = 15                           # print an "alive, no fixes yet" line this often
SEND_TIMEOUT_S = 5                            # drop a viewer that can't accept data within this
STATUS_EVERY_S = 5                            # broadcast the LINK UP/DOWN heartbeat this often

# ---- the box's own position (a local USB GPS plugged into the hub) ----
GPS_ENABLE   = True                           # read a local GPS and show the box as a unit
SELF_ID      = "LOOKOUT"                       # the box appears as this unit (alias it in the
                                              # Alias Manager, e.g. 9076801 -> "Jax 24" style)
GPS_RESCAN_S = 20                             # no GPS yet, or GPS dropped -> look again this often

# ---- NMEA extraction (verbatim from p25_core.py) ----
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

def _mk(body):
    g = 0
    for c in body:
        g ^= ord(c)
    return f"${body}*{g:02X}"

# ---- client fan-out ----
_clients = set()
_lock = threading.Lock()

def _broadcast(sentence):
    data = (sentence + "\r\n").encode("ascii", "replace")
    with _lock:
        clients = list(_clients)             # take a copy, then send WITHOUT holding the lock
    dead = []
    for c in clients:
        try:
            c.sendall(data)                  # socket has a send timeout; a stuck reader raises here
        except OSError:
            dead.append(c)
    if dead:
        with _lock:
            for c in dead:
                _clients.discard(c)
            n = len(_clients)
        for c in dead:
            try: c.close()
            except OSError: pass
        print(f"[bridge] dropped {len(dead)} slow/closed client(s)  (now {n} connected)",
              flush=True)

def _serve_clients():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((SERVE_HOST, SERVE_PORT))
    srv.listen(16)
    print(f"[bridge] serving NMEA on tcp {SERVE_HOST}:{SERVE_PORT} - connect any device here",
          flush=True)
    while True:
        try:
            conn, addr = srv.accept()
        except OSError as e:
            print(f"[bridge] accept error: {e} - continuing", flush=True)
            time.sleep(0.5)
            continue
        conn.settimeout(SEND_TIMEOUT_S)       # a viewer that can't keep up is dropped, not blocked
        with _lock:
            _clients.add(conn)
            n = len(_clients)
        print(f"[bridge] client connected: {addr[0]}:{addr[1]}  (now {n} connected)",
              flush=True)

# ---- radio link status (announced into the feed so the map can alarm) ----
_link_state     = "down"       # "up" once subscribed and reading; "down" while the radio is lost
_last_status_at = 0.0
_printed_state  = None

def _emit_status(now, force=False):
    global _last_status_at, _printed_state
    if force or (now - _last_status_at) >= STATUS_EVERY_S:
        _broadcast(_mk("PLKT,LINK,UP" if _link_state == "up" else "PLKT,LINK,DOWN"))
        _last_status_at = now
    if _printed_state != _link_state:
        print(f"[radio] LINK {_link_state.upper()}", flush=True)
        _printed_state = _link_state

def _set_link(state, now):
    global _link_state
    if _link_state != state:
        _link_state = state
        _emit_status(now, force=True)         # announce the change immediately

def _wait(seconds):
    """Sleep in small steps so the LINK heartbeat keeps going while we are disconnected."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        _emit_status(time.monotonic())
        time.sleep(0.5)

_iface_seen = False
def _iface_lost():
    """True once the radio's USB interface vanishes or goes down - instant unplug detection.
    Stays inert (False) on systems where the interface never appears, so a non-usb0 setup
    falls back to the keepalive probe and the watchdog."""
    global _iface_seen
    try:
        with open(f"/sys/class/net/{RADIO_IFACE}/operstate") as fh:
            _iface_seen = True
            return fh.read().strip() == "down"
    except OSError:
        return _iface_seen

# ---- radio reader ----
def _radio_loop():
    buf = bytearray()
    while True:
        s = None
        try:
            print(f"[radio] connecting to {RADIO_IP}:{RADIO_PORT} ...", flush=True)
            s = socket.create_connection((RADIO_IP, RADIO_PORT), timeout=6)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)   # OS detects a dead peer
            s.sendall(SUBSCRIBE)
            s.settimeout(0.5)
            print("[radio] connected + subscribed - listening for GPS", flush=True)
            _set_link("up", time.monotonic())
            last_keep = last_data = last_beat = last_alive = time.monotonic()
            got_any = False
            while True:
                try:
                    data = s.recv(65535)
                except socket.timeout:
                    data = b""
                now = time.monotonic()
                if data:
                    last_data = last_alive = now
                    buf.extend(data)
                    text = buf.decode("latin-1")
                    last_end = 0
                    for m in _SENTENCE.finditer(text):
                        sen = m.group(0); last_end = m.end()
                        if _nmea_ok(sen):
                            got_any = True
                            with _lock:
                                n = len(_clients)
                            print(f"[nmea -> {n} client(s)] {sen}", flush=True)
                            _broadcast(sen)
                    if last_end:
                        del buf[:last_end]
                    if len(buf) > 8192:
                        del buf[:-2048]
                if _iface_lost():
                    print(f"[radio] {RADIO_IFACE} is gone - radio unplugged", flush=True)
                    break
                if KEEPALIVE_S and now - last_keep > KEEPALIVE_S:
                    try:
                        s.sendall(SUBSCRIBE)            # re-subscribe + probe the link
                    except OSError:
                        print("[radio] keepalive failed - radio lost", flush=True)
                        break
                    last_keep = last_alive = now        # a successful keepalive = link alive
                _emit_status(now)                       # LINK UP heartbeat
                if not got_any and now - last_beat > HEARTBEAT_S:
                    print("[radio] alive - subscribed and waiting (no units transmitting yet)",
                          flush=True)
                    last_beat = now
                if now - last_alive > WATCHDOG_S:
                    # a quiet fleet (no units transmitting) is NOT a lost link - the keepalive
                    # above refreshes last_alive every 20 s, so this only fires on a real stall.
                    print("[radio] link stalled (no data AND no keepalive) - reconnecting", flush=True)
                    break
        except OSError as e:
            print(f"[radio] connection problem: {e} - retrying", flush=True)
        finally:
            if s is not None:
                try: s.close()
                except OSError: pass
        _set_link("down", time.monotonic())             # radio is gone -> raise the alarm
        _wait(RECONNECT_S)

# ---- local GPS reader (the box's own position) ----
def _gps_loop():
    """Read a local USB GPS and broadcast the box's own fix as unit SELF_ID. Runs in its own
    daemon thread and swallows every error, so it can never disturb the radio feed."""
    if not (GPS_ENABLE and gps_source):
        return
    announced_absent = False
    while True:
        try:
            src, stream = gps_source.open_source(SELF_ID, log=lambda m: print(m, flush=True))
        except Exception as e:
            src, stream = None, None
            print(f"[gps] reader error: {e} - will look again", flush=True)
        if not src:
            if not announced_absent:
                print("[gps] no local GPS found yet - the box won't show its own position "
                      "(radio feed is unaffected). Still looking.", flush=True)
                announced_absent = True
            time.sleep(GPS_RESCAN_S)
            continue
        announced_absent = False
        print(f"[gps] local GPS live on {src.name} - adding this box as unit '{SELF_ID}'",
              flush=True)
        try:
            for sen in stream:
                _broadcast(sen)
        except Exception as e:
            print(f"[gps] {getattr(src, 'name', 'GPS')} stopped: {e} - will look again", flush=True)
        finally:
            try: src.close()
            except Exception: pass
        time.sleep(GPS_RESCAN_S)

if __name__ == "__main__":
    print(f"=== BK radio -> NMEA network bridge  v{VERSION} ===", flush=True)
    threading.Thread(target=_serve_clients, daemon=True).start()
    if GPS_ENABLE and gps_source:
        threading.Thread(target=_gps_loop, daemon=True).start()
    try:
        _radio_loop()
    except KeyboardInterrupt:
        print("\n[bridge] stopped.", flush=True)
        sys.exit(0)
