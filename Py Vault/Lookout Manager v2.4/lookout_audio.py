#!/usr/bin/env python3
"""The Lookout - radio audio streamer (OPTIONAL, fully isolated).

Reads the radio's received audio from a USB sound card via ALSA `arecord` and
streams it as raw PCM over a WebSocket to any browser. The in-browser live map
(served by units_kml.py on :8080) grows a "Listen" button that plays this feed,
so a crew watching the units can also hear the net - no app, no install.

ISOLATION (by design): this is its OWN process on its OWN port (:8081). It never
touches bk_bridge.py or units_kml.py and shares no state with them. If the sound
card is absent, this program dies, or no one is listening, the map and the radio
position feed are completely unaffected - audio is purely additive.

Pure Python standard library only (no PyPI, no codec). Voice is narrowband, so it
ships 16 kHz / 16-bit / mono PCM (~256 kbps) straight to the browser, which plays
it with the Web Audio API. On a LAN that bandwidth is nothing, and the router does
no encoding - just a byte copy to each listener.

Run:
    python3 lookout_audio.py            # live: capture from the sound card
    python3 lookout_audio.py --test     # no card: emit a 440 Hz test tone
"""
import base64, hashlib, math, os, socket, struct, subprocess, sys, threading, time

HOST      = "0.0.0.0"
PORT      = int(os.environ.get("LOOKOUT_AUDIO_PORT", "8081"))
RATE      = int(os.environ.get("LOOKOUT_AUDIO_RATE", "16000"))   # Hz, mono, S16_LE
ALSA_DEV  = os.environ.get("LOOKOUT_AUDIO_DEV", "plughw:0,0")    # the USB sound card
CHUNK     = RATE * 2 // 10          # bytes per frame = ~100 ms of 16-bit mono audio
SEND_TMO  = 2.0                     # drop a listener whose socket blocks this long
WS_GUID   = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

_clients = []                       # live listener sockets
_lock    = threading.Lock()


# ---------------- minimal WebSocket (server -> client, binary, unmasked) --------
def _ws_handshake(conn):
    data = b""
    while b"\r\n\r\n" not in data:
        part = conn.recv(1024)
        if not part:
            return False
        data += part
        if len(data) > 8192:
            return False
    key = None
    for line in data.split(b"\r\n"):
        if line[:18].lower() == b"sec-websocket-key:":
            key = line.split(b":", 1)[1].strip()
    if not key:
        return False
    accept = base64.b64encode(hashlib.sha1(key + WS_GUID).digest())
    conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\n"
                 b"Upgrade: websocket\r\nConnection: Upgrade\r\n"
                 b"Sec-WebSocket-Accept: " + accept + b"\r\n\r\n")
    return True


def _frame(payload):                 # one binary frame (opcode 0x2), no mask
    n = len(payload)
    if n < 126:
        head = struct.pack("!BB", 0x82, n)
    elif n < 65536:
        head = struct.pack("!BBH", 0x82, 126, n)
    else:
        head = struct.pack("!BBQ", 0x82, 127, n)
    return head + payload


def _register(conn, addr):
    conn.settimeout(10)
    try:
        if not _ws_handshake(conn):
            conn.close(); return
    except Exception:
        conn.close(); return
    conn.settimeout(SEND_TMO)         # a stuck listener is dropped, never stalls others
    with _lock:
        _clients.append(conn)
    print("[audio] listener on %s:%d - %d now" % (addr[0], addr[1], len(_clients)), flush=True)


def _drop(conns):
    if not conns:
        return
    with _lock:
        for c in conns:
            if c in _clients:
                _clients.remove(c)
    for c in conns:
        try: c.close()
        except Exception: pass
    print("[audio] listener gone - %d now" % len(_clients), flush=True)


def _broadcast(pcm):
    frame = _frame(pcm)
    with _lock:
        snapshot = list(_clients)     # copy, then send OUTSIDE the lock (lock-free fan-out)
    dead = []
    for c in snapshot:
        try:
            c.sendall(frame)
        except Exception:
            dead.append(c)
    _drop(dead)


# ---------------- audio source: the sound card, or a test tone -------------------
def _capture_from_card():
    cmd = ["arecord", "-D", ALSA_DEV, "-f", "S16_LE", "-c", "1",
           "-r", str(RATE), "-t", "raw", "-q"]
    while True:
        print("[audio] opening %s @ %d Hz" % (ALSA_DEV, RATE), flush=True)
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        except FileNotFoundError:
            print("[audio] arecord not found - install alsa-utils. retrying in 5s", flush=True)
            time.sleep(5); continue
        try:
            while True:
                buf = p.stdout.read(CHUNK)
                if not buf:
                    break
                _broadcast(buf)
        finally:
            try: p.kill()
            except Exception: pass
        print("[audio] capture ended (card unplugged?) - retrying in 2s", flush=True)
        time.sleep(2)


def _test_tone():
    print("[audio] TEST MODE - emitting a 440 Hz tone (no sound card used)", flush=True)
    samples = CHUNK // 2
    phase = 0.0
    step = 2 * math.pi * 440 / RATE
    period = samples / RATE           # real-time pacing
    while True:
        out = bytearray()
        for _ in range(samples):
            out += struct.pack("<h", int(8000 * math.sin(phase)))
            phase += step
            if phase > 2 * math.pi:
                phase -= 2 * math.pi
        _broadcast(bytes(out))
        time.sleep(period)


# ---------------- server ---------------------------------------------------------
def main():
    source = _test_tone if "--test" in sys.argv else _capture_from_card
    threading.Thread(target=source, daemon=True).start()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(16)
    print("[audio] WebSocket PCM server on %s:%d  (%d Hz, 16-bit, mono)"
          % (HOST, PORT, RATE), flush=True)
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=_register, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
