#!/usr/bin/env python3
"""garmin_linux.py - read a Garmin GPS 18 USB (091e:0003) on Linux via ctypes + libusb-1.0.

Why this exists (2026-11-16): gpsd on this OpenWrt build detects the Garmin ("Garmin USB
binary") but cannot read it (missing HAVE_LIBUSB/NON_NMEA0183 build), and neither pyusb nor
gpsbabel is packaged. But libusb-1.0 IS installable (opkg install libusb-1.0-0). So this
talks the Garmin USB protocol directly over libusb - the SAME protocol reverse-engineered on
Jim's own GPS 18 for the Windows P25 tool: Start_Session, then Start_Pvt, then read D800 PVT
records off the interrupt pipe in 64-byte chunks reassembled until one is < 64. Packet
framing + the D800 decode are reused verbatim from gps_source.py (bench-proven).

The USB endpoints are DISCOVERED from the device's own config descriptor (not hardcoded),
so it matches whatever addresses this puck actually uses.

Standalone test (prints every step):
    opkg install libusb-1.0-0        # provides libusb-1.0.so.0
    rmmod garmin_gps 2>/dev/null     # free the device from the kernel serial driver
    python3 garmin_linux.py
"""
import ctypes, ctypes.util, struct, sys, time
import gps_source as G

VID, PID = 0x091E, 0x0003
LIBUSB_ERROR_TIMEOUT = -7


def _load_libusb():
    last = None
    for name in ("libusb-1.0.so.0", "/usr/lib/libusb-1.0.so.0",
                 ctypes.util.find_library("usb-1.0"), "libusb-1.0.so", "usb-1.0"):
        if not name:
            continue
        try:
            return ctypes.CDLL(name, use_errno=True)
        except OSError as e:
            last = e
    raise OSError("libusb-1.0 not found (opkg install libusb-1.0-0): %s" % last)


class GarminLibusb:
    name = "Garmin GPS 18 USB (091e:0003, ctypes/libusb)"

    def __init__(self, verbose=False):
        self.lib = self.ctx = self.h = None
        self.claimed = False
        self.v = verbose
        # sensible defaults; replaced by discovery from the device descriptor
        self.ep_out, self.out_bulk = 0x02, True
        self.ep_in, self.in_bulk = 0x81, False

    def _log(self, m):
        if self.v:
            print("[garmin] " + m, flush=True)

    def _bind(self, lib):
        v = ctypes.c_void_p; i = ctypes.c_int
        lib.libusb_init.argtypes = [ctypes.POINTER(v)]
        lib.libusb_open_device_with_vid_pid.restype = v
        lib.libusb_open_device_with_vid_pid.argtypes = [v, ctypes.c_uint16, ctypes.c_uint16]
        lib.libusb_kernel_driver_active.argtypes = [v, i]
        lib.libusb_detach_kernel_driver.argtypes = [v, i]
        lib.libusb_claim_interface.argtypes = [v, i]
        lib.libusb_release_interface.argtypes = [v, i]
        lib.libusb_close.argtypes = [v]
        lib.libusb_exit.argtypes = [v]
        lib.libusb_control_transfer.restype = i
        lib.libusb_control_transfer.argtypes = [v, ctypes.c_ubyte, ctypes.c_ubyte,
                                                ctypes.c_uint16, ctypes.c_uint16, v,
                                                ctypes.c_uint16, ctypes.c_uint]
        lib.libusb_bulk_transfer.argtypes = [v, ctypes.c_ubyte, v, i, ctypes.POINTER(i), ctypes.c_uint]
        lib.libusb_interrupt_transfer.argtypes = [v, ctypes.c_ubyte, v, i, ctypes.POINTER(i), ctypes.c_uint]

    def _discover_endpoints(self):
        """Read the config descriptor off the device and find the real OUT + IN endpoints."""
        buf = (ctypes.c_char * 255)()
        n = self.lib.libusb_control_transfer(self.h, 0x80, 0x06, 0x0200, 0, buf, 255, 2000)
        if n < 4:
            self._log("couldn't read config descriptor (n=%d) - keeping defaults 0x%02x/0x%02x"
                      % (n, self.ep_out, self.ep_in))
            return
        blob = bytes(buf[:n])
        out_ep = out_bulk = int_in = bulk_in = None
        i = 0
        while i + 3 < len(blob):
            blen = blob[i]
            if blen == 0:
                break
            if blob[i + 1] == 0x05:                 # ENDPOINT descriptor
                addr = blob[i + 2]; ttype = blob[i + 3] & 0x03   # 2=bulk 3=interrupt
                if addr & 0x80:                     # IN
                    if ttype == 3 and int_in is None:
                        int_in = addr
                    elif ttype == 2 and bulk_in is None:
                        bulk_in = addr
                else:                               # OUT
                    if out_ep is None:
                        out_ep, out_bulk = addr, (ttype == 2)
            i += blen
        if out_ep is not None:
            self.ep_out, self.out_bulk = out_ep, out_bulk
        if int_in is not None:
            self.ep_in, self.in_bulk = int_in, False
        elif bulk_in is not None:
            self.ep_in, self.in_bulk = bulk_in, True
        self._log("endpoints found: OUT=0x%02x(%s)  IN=0x%02x(%s)%s" % (
            self.ep_out, "bulk" if self.out_bulk else "int",
            self.ep_in, "bulk" if self.in_bulk else "int",
            "  bulk_in=0x%02x" % bulk_in if bulk_in else ""))

    def open(self):
        lib = self.lib = _load_libusb()
        self._bind(lib)
        ctx = ctypes.c_void_p()
        if lib.libusb_init(ctypes.byref(ctx)) != 0:
            raise OSError("libusb_init failed")
        self.ctx = ctx
        self._log("libusb initialised")
        h = lib.libusb_open_device_with_vid_pid(ctx, VID, PID)
        if not h:
            raise OSError("Garmin 091e:0003 not found or cannot open")
        self.h = ctypes.c_void_p(h)
        self._log("opened 091e:0003")
        try:
            if lib.libusb_kernel_driver_active(self.h, 0) == 1:
                lib.libusb_detach_kernel_driver(self.h, 0)
                self._log("detached kernel driver (garmin_gps)")
        except OSError:
            pass
        rc = lib.libusb_claim_interface(self.h, 0)
        if rc != 0:
            raise OSError("claim_interface rc=%d (garmin_gps still bound? rmmod garmin_gps)" % rc)
        self.claimed = True
        self._log("claimed interface 0")
        self._discover_endpoints()
        self._write(G._pkt(G._LAYER_TRANSPORT, G._PID_START_SESSION))
        self._log("sent Start_Session")
        self._write(G._pkt(G._LAYER_APPL, G._PID_COMMAND_DATA, struct.pack("<H", G._CMND_START_PVT)))
        self._log("sent Start_Pvt - device should now stream PVT ~1/s")
        return self

    def _write(self, data):
        n = ctypes.c_int(0)
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        fn = self.lib.libusb_bulk_transfer if self.out_bulk else self.lib.libusb_interrupt_transfer
        rc = fn(self.h, self.ep_out, buf, len(data), ctypes.byref(n), 3000)
        if rc != 0:
            raise OSError("write to EP 0x%02x (%s) rc=%d" %
                          (self.ep_out, "bulk" if self.out_bulk else "int", rc))

    def _read_chunk(self, timeout_ms=2000):
        buf = (ctypes.c_char * 64)()
        n = ctypes.c_int(0)
        fn = self.lib.libusb_bulk_transfer if self.in_bulk else self.lib.libusb_interrupt_transfer
        rc = fn(self.h, self.ep_in, buf, 64, ctypes.byref(n), timeout_ms)
        if rc == LIBUSB_ERROR_TIMEOUT:
            return None
        if rc != 0:
            raise OSError("read from EP 0x%02x rc=%d" % (self.ep_in, rc))
        return bytes(buf[:n.value])

    def _read_packet(self):
        out = b""
        for _ in range(64):
            c = self._read_chunk()
            if c is None:
                return out or None
            out += c
            if len(c) < 64:
                break
        return out

    def sentences(self, self_id):
        seen = False
        while True:
            pkt = self._read_packet()
            if pkt is None:
                continue
            hd = G._parse(pkt)
            if not hd:
                continue
            ptype, pid, dsize, data = hd
            if not seen:
                self._log("first packet type=%d id=%d size=%d" % (ptype, pid, dsize))
                seen = True
            if ptype == G._LAYER_APPL and pid == G._PID_PVT_DATA:
                d = G.decode_d800(data)
                if not d:
                    continue
                lat, lon, alt, fix, utc, date, spd = d
                self._log("PVT fix=%d lat=%.5f lon=%.5f" % (fix, lat, lon))
                if fix < 2 or not G._coords_ok(lat, lon):   # no fix, or NaN/(0,0)/out-of-range
                    continue
                yield G.build_gga(lat, lon, alt, 8, utc)
                yield G.tag(self_id)
                yield G.build_rmc(lat, lon, utc, date, spd)

    def close(self):
        try:
            if self.h:
                try:
                    self._write(G._pkt(G._LAYER_APPL, G._PID_COMMAND_DATA, struct.pack("<H", G._CMND_STOP_PVT)))
                except OSError:
                    pass
                if self.claimed:
                    self.lib.libusb_release_interface(self.h, 0)
                self.lib.libusb_close(self.h)
            if self.ctx:
                self.lib.libusb_exit(self.ctx)
        except OSError:
            pass


if __name__ == "__main__":
    print("=== Garmin GPS 18 USB test  (ctypes/libusb, proven D800 protocol) ===", flush=True)
    src = GarminLibusb(verbose=True)
    try:
        src.open()
    except OSError as e:
        print("OPEN FAILED:", e, flush=True)
        print("checklist: opkg install libusb-1.0-0 | rmmod garmin_gps | Garmin in the hub", flush=True)
        sys.exit(1)
    print("--- reading up to 8 fixes / ~40 s (puck needs sky view) ---", flush=True)
    fixes = 0
    deadline = time.time() + 40
    try:
        for s in src.sentences("LOOKOUT"):
            print("  NMEA:", s, flush=True)
            if s.startswith("$GPRMC"):
                fixes += 1
            if fixes >= 8 or time.time() > deadline:
                break
    except Exception as e:
        print("READ ERROR:", e, flush=True)
    finally:
        src.close()
    print("=== done: %d position fix(es) ===" % fixes, flush=True)
