#!/usr/bin/env python3
"""gps_source.py - the Lookout's OWN position, from a local USB GPS  (Claude + Jim, 2026-11-16)

A small, self-contained reader that finds a GPS plugged into the box and turns its fixes
into NMEA sentences tagged as one reserved "unit" - the box itself ("you are here"). It is
read by bk_bridge.py, which broadcasts those sentences into the same :10110 feed as the
radio units, so the box shows up on the map alongside the fleet with no change to the map.

It tries three ways to reach a GPS, in order of how battle-tested each one is, and uses the
first that actually produces a fix:

  1. gpsd        - the standard Linux GPS daemon on 127.0.0.1:2947. This is the clean way to
                   read a Garmin GPS 18 USB (091E:0003), whose own protocol is NOT NMEA:
                   gpsd's mature garmin driver speaks it and re-serves plain NMEA. Install on
                   OpenWrt with:  opkg update && opkg install gpsd gpsd-clients
                   then point gpsd at the device and start it (see docs/GPS_SOURCE.md).
  2. serial NMEA - any plain USB-serial GPS puck (BU-353N5, u-blox, a Garmin in NMEA mode) on
                   /dev/ttyUSB* or /dev/ttyACM*. Needs pyserial + the matching USB-serial kmod
                   (cp210x / pl2303 / ftdi / cdc-acm). Dead simple, plug-and-play.
  3. Garmin USB  - the Garmin GPS 18 USB (091E:0003) read DIRECTLY over libusb, no gpsd. This
                   re-uses the exact D800 PVT protocol proven on Jim's unit (garmin_core.py).
                   The proven path is garmin_linux.GarminLibusb (ctypes + libusb-1.0, endpoints
                   discovered from the device) - LIVE-PROVEN on the GL-MT6000 router 2026-11-16,
                   no pyusb needed (opkg install libusb-1.0-0). A pyusb variant is kept as a
                   last-ditch fallback for boxes that happen to have pyusb but not libusb bound.

This box's own GPS is tried Garmin-first: garmin_linux fails instantly when no Garmin is
plugged in, so it costs nothing on a serial/gpsd setup and leads on the proven hardware.

Output of every source is identical: a stream of NMEA sentences, and after each position
(GGA) one '$PP25,<SELF_ID>' tag so units_kml keys the box as the unit <SELF_ID>.

Pure standard library except: gpsd needs nothing, serial needs pyserial, Garmin-USB needs
pyusb + libusb-1.0. Each is imported lazily, so a missing library only disables that one
path; the others still work, and if none works bk_bridge just runs the radio as before.
"""
import socket, time, glob, datetime
from math import pi

GPSD_HOST = "127.0.0.1"
GPSD_PORT = 2947
SERIAL_GLOBS = ("/dev/ttyUSB*", "/dev/ttyACM*")
SERIAL_BAUDS = (4800, 9600, 38400)      # 4800 = classic NMEA, 9600 = most modern pucks
GARMIN_VID, GARMIN_PID = 0x091E, 0x0003
PROBE_SECONDS = 5.0                     # how long to wait for a first real fix before moving on


# ---------------- NMEA helpers ----------------
def _cs(body):
    g = 0
    for c in body:
        g ^= ord(c)
    return f"${body}*{g:02X}"

def _ddm(value, deg_digits):
    """decimal degrees -> ddmm.mmmm (lat: deg_digits=2, lon: deg_digits=3)."""
    d = int(abs(value))
    m = (abs(value) - d) * 60.0
    return f"{d:0{deg_digits}d}{m:07.4f}"

def build_gga(lat, lon, alt_m, sats, utc):
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    try:
        nn = f"{int(sats):02d}"
    except (TypeError, ValueError):
        nn = "08"
    body = (f"GPGGA,{utc},{_ddm(lat,2)},{ns},{_ddm(lon,3)},{ew},1,{nn},1.0,"
            f"{alt_m:.1f},M,0.0,M,,")
    return _cs(body)

def build_rmc(lat, lon, utc, date, speed_kn=0.0, course=0.0):
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    body = (f"GPRMC,{utc},A,{_ddm(lat,2)},{ns},{_ddm(lon,3)},{ew},"
            f"{speed_kn:.1f},{course:.1f},{date},,,A")
    return _cs(body)

def tag(self_id):
    # real radio shape is "$PP25,<id>,*cs" - the trailing comma keeps the checksum out of
    # the id field, so units_kml reads f[1] clean.
    return _cs(f"PP25,{self_id},")


# ---------------- coordinate sanity (don't broadcast a glitchy self-fix) ----------------
def _coords_ok(lat, lon):
    """Reject NaN, out-of-range, and the (0,0) 'null island' a cold-start can emit."""
    try:
        if lat != lat or lon != lon:          # NaN
            return False
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            return False
        if abs(lat) < 1e-6 and abs(lon) < 1e-6:
            return False
    except TypeError:
        return False
    return True

def _ddm_to_deg(tok, hemi):
    """ddmm.mmmm / dddmm.mmmm + hemisphere -> signed decimal degrees, or None."""
    try:
        v = float(tok)
    except (TypeError, ValueError):
        return None
    deg = int(v // 100); dd = deg + (v - deg * 100) / 60.0
    return -dd if hemi in ("S", "W") else dd

def _nmea_coords_ok(line):
    """Validate the lat/lon carried by a GGA or RMC sentence (field layout differs)."""
    f = line.split(",")
    t = f[0][1:] if f and f[0] else ""
    if t.endswith("GGA") and len(f) > 5:
        lat = _ddm_to_deg(f[2], f[3]); lon = _ddm_to_deg(f[4], f[5])
    elif t.endswith("RMC") and len(f) > 6:
        lat = _ddm_to_deg(f[3], f[4]); lon = _ddm_to_deg(f[5], f[6])
    else:
        return False
    if lat is None or lon is None:
        return False
    return _coords_ok(lat, lon)

_SENTENCE_START = "$"

def _looks_valid(line):
    """A quick 'is this a usable GGA/RMC with a real fix' check for probing a source."""
    if not line.startswith(_SENTENCE_START) or "*" not in line:
        return False
    f = line.split(",")
    t = f[0][1:]
    if t.endswith("GGA") and len(f) >= 7:
        return f[6] not in ("", "0") and bool(f[2]) and bool(f[4])
    if t.endswith("RMC") and len(f) >= 7:
        return (len(f) > 2 and f[2] == "A") and bool(f[3]) and bool(f[5])
    return False


# ---------------- source: gpsd ----------------
class GpsdSource:
    name = "gpsd (127.0.0.1:2947)"

    def __init__(self):
        self.sock = None

    def open(self):
        self.sock = socket.create_connection((GPSD_HOST, GPSD_PORT), timeout=3)
        self.sock.sendall(b'?WATCH={"enable":true,"nmea":true}\n')
        self.sock.settimeout(1.0)
        return self

    def _lines(self):
        buf = b""
        while True:
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                yield None            # let the caller tick (timeouts, status)
                continue
            if not chunk:
                return
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                yield raw.decode("latin-1", "replace").strip()

    def sentences(self, self_id):
        """gpsd already emits NMEA; pass GGA/RMC through and inject the self tag after a GGA."""
        for line in self._lines():
            if line is None:
                continue
            if not line.startswith(_SENTENCE_START) or "*" not in line:
                continue
            t = line.split(",")[0][1:]
            if t.endswith("GGA"):
                if _nmea_coords_ok(line):
                    yield line
                    yield tag(self_id)
            elif t.endswith("RMC"):
                if _nmea_coords_ok(line):
                    yield line

    def close(self):
        try:
            if self.sock:
                self.sock.close()
        except OSError:
            pass


# ---------------- source: plain serial NMEA puck ----------------
class SerialSource:
    def __init__(self, port, baud, serial_mod):
        self.port, self.baud, self._serial, self.ser = port, baud, serial_mod, None
        self.name = f"serial NMEA {port} @ {baud}"

    def open(self):
        self.ser = self._serial.Serial(self.port, self.baud, timeout=1)
        return self

    def sentences(self, self_id):
        pend = b""
        while True:
            try:
                chunk = self.ser.read(256)
            except Exception:
                return
            if not chunk:
                continue
            pend += chunk
            while b"\n" in pend:
                raw, pend = pend.split(b"\n", 1)
                line = raw.decode("latin-1", "replace").strip()
                if not line.startswith(_SENTENCE_START) or "*" not in line:
                    continue
                t = line.split(",")[0][1:]
                if t.endswith("GGA"):
                    if _nmea_coords_ok(line):
                        yield line
                        yield tag(self_id)
                elif t.endswith("RMC"):
                    if _nmea_coords_ok(line):
                        yield line

    def close(self):
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass


# ---------------- source: Garmin GPS 18 USB over libusb (proven D800 protocol) ----------------
# packet layer ids (from garmin_core.py, proven on Jim's unit 2026-11-12)
_LAYER_TRANSPORT, _LAYER_APPL = 0, 20
_PID_START_SESSION, _PID_SESSION_STARTED = 5, 6
_PID_COMMAND_DATA, _PID_PVT_DATA = 10, 51
_CMND_START_PVT, _CMND_STOP_PVT = 49, 50
_PID_DATA_AVAILABLE = 2
_GPS_EPOCH = datetime.datetime(1980, 1, 6, tzinfo=datetime.timezone.utc)

import struct

def _pkt(ptype, pid, data=b""):
    return struct.pack("<B3xH2xI", ptype, pid, len(data)) + data

def _parse(b):
    if len(b) < 12:
        return None
    ptype = b[0]
    pid = struct.unpack("<H", b[4:6])[0]
    dsize = struct.unpack("<I", b[8:12])[0]
    return ptype, pid, dsize, b[12:12 + dsize]

def decode_d800(data):
    """Return (lat_deg, lon_deg, alt_msl_m, fix, utc_hhmmss, date_ddmmyy, speed_kn) or None.
    Byte layout verbatim from garmin_core.py's proven decode."""
    if len(data) < 64:
        return None
    (alt, epe, eph, epv, fix, tow, lat, lon,
     east, north, up, msl, leap, wn) = struct.unpack("<ffffhdddffffhi", data[:64])
    lat_deg = lat * 180 / pi
    lon_deg = lon * 180 / pi
    speed_kn = (east * east + north * north) ** 0.5 * 1.943844      # m/s -> knots
    try:
        secs = wn * 604800 + tow - leap
        t = _GPS_EPOCH + datetime.timedelta(seconds=secs)
        utc = t.strftime("%H%M%S"); date = t.strftime("%d%m%y")
    except (ValueError, OverflowError):
        utc = time.strftime("%H%M%S"); date = time.strftime("%d%m%y")
    return lat_deg, lon_deg, (alt - msl), int(fix), utc, date, speed_kn


class GarminUsbSource:
    name = "Garmin GPS 18 USB (091E:0003, libusb)"

    def __init__(self, usb_mod):
        self._usb = usb_mod
        self.dev = self.ep_out = self.ep_in = None

    def open(self):
        usb = self._usb
        dev = usb.core.find(idVendor=GARMIN_VID, idProduct=GARMIN_PID)
        if dev is None:
            raise RuntimeError("no Garmin USB device (091E:0003)")
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)        # take it from the garmin_gps kmod if loaded
        except Exception:
            pass
        dev.set_configuration()
        intf = dev.get_active_configuration()[(0, 0)]
        self.ep_out = usb.util.find_descriptor(intf, custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT and
            usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK)
        self.ep_in = usb.util.find_descriptor(intf, custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN and
            usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_INTR)
        self.ep_bulk_in = usb.util.find_descriptor(intf, custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN and
            usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK)
        if not (self.ep_out and self.ep_in):
            raise RuntimeError("Garmin USB endpoints not found")
        self.dev = dev
        self.dev.write(self.ep_out.bEndpointAddress, _pkt(_LAYER_TRANSPORT, _PID_START_SESSION))
        self.dev.write(self.ep_out.bEndpointAddress,
                       _pkt(_LAYER_APPL, _PID_COMMAND_DATA, struct.pack("<H", _CMND_START_PVT)))
        return self

    def _read_packet(self):
        """Read one framed packet. Small packets arrive on the interrupt pipe; a transport
        'data available' tells us to pull the body from the bulk-in pipe (Garmin USB protocol)."""
        out = b""
        for _ in range(80):
            try:
                chunk = bytes(self.dev.read(self.ep_in.bEndpointAddress, 64, timeout=2000))
            except Exception:
                return b""
            out += chunk
            if len(chunk) < 64:
                break
        hd = _parse(out)
        if hd and hd[0] == _LAYER_TRANSPORT and hd[1] == _PID_DATA_AVAILABLE and self.ep_bulk_in:
            body = b""
            for _ in range(80):
                try:
                    chunk = bytes(self.dev.read(self.ep_bulk_in.bEndpointAddress, 64, timeout=2000))
                except Exception:
                    break
                body += chunk
                if len(chunk) < 64:
                    break
            return body
        return out

    def sentences(self, self_id):
        while True:
            hd = _parse(self._read_packet())
            if not hd:
                continue
            if hd[0] == _LAYER_APPL and hd[1] == _PID_PVT_DATA:
                d = decode_d800(hd[3])
                if not d:
                    continue
                lat, lon, alt, fix, utc, date, spd = d
                if fix < 2 or not _coords_ok(lat, lon):   # 0/1 = no fix; reject NaN/(0,0)/range
                    continue
                yield build_gga(lat, lon, alt, 8, utc)
                yield tag(self_id)
                yield build_rmc(lat, lon, utc, date, spd)

    def close(self):
        try:
            if self.dev:
                self.dev.write(self.ep_out.bEndpointAddress,
                               _pkt(_LAYER_APPL, _PID_COMMAND_DATA, struct.pack("<H", _CMND_STOP_PVT)))
        except Exception:
            pass


# ---------------- auto-detect ----------------
def _candidates():
    """Yield (source, needs_probe) in priority order, importing libs lazily."""
    # 1. Garmin GPS 18 USB direct over libusb (ctypes) - proven on the router 2026-11-16.
    #    Fails instantly if no Garmin is plugged in, so it's free on serial/gpsd setups.
    try:
        import garmin_linux
        yield garmin_linux.GarminLibusb(), True
    except Exception:
        pass
    # 2. gpsd
    try:
        yield GpsdSource(), True
    except Exception:
        pass
    # 3. serial pucks
    try:
        import serial
        for pattern in SERIAL_GLOBS:
            for port in sorted(glob.glob(pattern)):
                for baud in SERIAL_BAUDS:
                    yield SerialSource(port, baud, serial), True
    except ImportError:
        pass
    # 4. Garmin over pyusb (last-ditch fallback; skipped when pyusb isn't installed)
    try:
        import usb.core, usb.util
        yield GarminUsbSource(usb), True
    except ImportError:
        pass


def open_source(self_id, log=print):
    """Try each GPS backend; return the first that OPENS and yields a real fix within the
    probe window, as (source, primed_generator). Returns (None, None) if no GPS is present."""
    for src, _ in _candidates():
        try:
            src.open()
        except Exception as e:
            continue
        gen = src.sentences(self_id)
        deadline = time.monotonic() + PROBE_SECONDS
        primed = []
        ok = False
        try:
            while time.monotonic() < deadline:
                sen = next(gen)
                primed.append(sen)
                if _looks_valid(sen):
                    ok = True
                    break
        except StopIteration:
            pass
        except Exception:
            pass
        if ok:
            log(f"[gps] using {src.name}")
            def chained():
                for s in primed:
                    yield s
                for s in gen:
                    yield s
            return src, chained()
        src.close()
    return None, None
