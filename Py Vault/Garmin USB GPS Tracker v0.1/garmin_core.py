"""Garmin USB GPS Tracker - core engine (Claude + Jim, 2026-11-12, v0.1).

Reads live position from a Garmin USB GPS (GPS 18 USB and kin, USB id 091E:0003)
through Garmin's OWN kernel driver - pure ctypes, no driver change, no COM port, no
NMEA - and plots it as a single moving marker on ArcGIS Earth's offline map through
the local Automation API.

How it talks to the GPS (proven on Jim's unit 2026-11-12):
  - find the device by Garmin's USB interface GUID, open it with CreateFile,
  - Start_Session (transport packet type 0, id 5) -> unit id,
  - Start_Pvt_Data (command 49) -> the unit streams a D800 PVT record ~1/sec,
  - PVT arrives on the INTERRUPT pipe as a 64-byte chunk + a short chunk; reassemble,
  - decode D800 (lat/lon in radians -> degrees), draw the marker.
It is read-only to the GPS apart from the standard start/stop-PVT commands.

Standard library only.
"""
import os, csv, json, time, struct, datetime, threading, ctypes
from ctypes import wintypes
from urllib import request, error
from pathlib import Path
from math import pi

ARCGIS_EARTH_API = "http://localhost:8000"
API_TIMEOUT_SECONDS = 4
MARKER_ICON = Path(__file__).resolve().parent / "marker.png"
MARKER_SIZE_PX = 36
DRAW_ID = "garmin-me"
LABEL = "My position"
LABEL_COLOR = [255, 255, 255, 255]
LABEL_SIZE = 12
LOG_DIR = Path(__file__).resolve().parent.parent / "Logs"

FIX_TEXT = {0: "no fix", 1: "no fix", 2: "2D", 3: "3D", 4: "2D diff", 5: "3D diff"}

# ---- Garmin USB constants ----
DIGCF_PRESENT = 0x02
DIGCF_DEVICEINTERFACE = 0x10
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def _ctl(dev, func, meth, acc):
    return (dev << 16) | (acc << 14) | (func << 2) | meth

IOCTL_GARMIN_USB_BULK_OUT_PACKET_SIZE = _ctl(0x22, 0x851, 0, 0)   # 0x222144
IOCTL_GARMIN_USB_INTERRUPT_IN         = _ctl(0x22, 0x850, 0, 0)   # 0x222140

LAYER_TRANSPORT = 0
LAYER_APPL = 20
PID_START_SESSION = 5
PID_SESSION_STARTED = 6
PID_COMMAND_DATA = 10
PID_PVT_DATA = 51
CMND_START_PVT = 49
CMND_STOP_PVT = 50


class GarminError(Exception):
    pass


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


class _SP_DID(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("InterfaceClassGuid", _GUID),
                ("Flags", wintypes.DWORD), ("Reserved", ctypes.POINTER(ctypes.c_ulong))]


_setup = ctypes.WinDLL("setupapi", use_last_error=True)
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_P = ctypes.c_void_p
_DW = wintypes.DWORD
_setup.SetupDiGetClassDevsW.restype = wintypes.HANDLE
_setup.SetupDiGetClassDevsW.argtypes = [_P, wintypes.LPCWSTR, wintypes.HWND, _DW]
_setup.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
_setup.SetupDiEnumDeviceInterfaces.argtypes = [wintypes.HANDLE, _P, _P, _DW, _P]
_setup.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
_setup.SetupDiGetDeviceInterfaceDetailW.argtypes = [wintypes.HANDLE, _P, _P, _DW, _P, _P]
_setup.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL
_setup.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
_k32.CreateFileW.restype = wintypes.HANDLE
_k32.CreateFileW.argtypes = [wintypes.LPCWSTR, _DW, _DW, _P, _DW, _DW, wintypes.HANDLE]
_k32.DeviceIoControl.restype = wintypes.BOOL
_k32.DeviceIoControl.argtypes = [wintypes.HANDLE, _DW, _P, _DW, _P, _DW, _P, _P]
_k32.ReadFile.restype = wintypes.BOOL
_k32.ReadFile.argtypes = [wintypes.HANDLE, _P, _DW, _P, _P]
_k32.WriteFile.restype = wintypes.BOOL
_k32.WriteFile.argtypes = [wintypes.HANDLE, _P, _DW, _P, _P]
_k32.CloseHandle.restype = wintypes.BOOL
_k32.CloseHandle.argtypes = [wintypes.HANDLE]


def device_present():
    """True if a Garmin USB GPS interface is present - a read-only 'start ready' check
    that does NOT open the device (so it never clashes with tracking)."""
    g = _garmin_guid()
    hdev = _setup.SetupDiGetClassDevsW(ctypes.byref(g), None, None,
                                       DIGCF_PRESENT | DIGCF_DEVICEINTERFACE)
    if not hdev or hdev == INVALID_HANDLE_VALUE:
        return False
    try:
        did = _SP_DID()
        did.cbSize = ctypes.sizeof(_SP_DID)
        return bool(_setup.SetupDiEnumDeviceInterfaces(hdev, None, ctypes.byref(g), 0, ctypes.byref(did)))
    finally:
        _setup.SetupDiDestroyDeviceInfoList(hdev)


def earth_reachable(client=None):
    try:
        (client or EarthClient()).ping()
        return True
    except Exception:
        return False


def _garmin_guid():
    g = _GUID()
    g.Data1, g.Data2, g.Data3 = 0x2C9C45C2, 0x8E7D, 0x4C08
    for i, b in enumerate((0xA1, 0x2D, 0x81, 0x6B, 0xBA, 0xE7, 0x22, 0xC0)):
        g.Data4[i] = b
    return g


class GarminUSB:
    """Open a Garmin USB GPS and stream decoded PVT fixes."""

    def __init__(self):
        self.h = None
        self.unit_id = None

    def open(self):
        g = _garmin_guid()
        hdev = _setup.SetupDiGetClassDevsW(ctypes.byref(g), None, None,
                                           DIGCF_PRESENT | DIGCF_DEVICEINTERFACE)
        if not hdev or hdev == INVALID_HANDLE_VALUE:
            raise GarminError("No Garmin USB device found. Is it plugged in and is the "
                              "Garmin USB driver installed (Device Manager > GARMIN Devices)?")
        try:
            did = _SP_DID()
            did.cbSize = ctypes.sizeof(_SP_DID)
            if not _setup.SetupDiEnumDeviceInterfaces(hdev, None, ctypes.byref(g), 0, ctypes.byref(did)):
                raise GarminError("No Garmin USB device present.")
            req = wintypes.DWORD(0)
            _setup.SetupDiGetDeviceInterfaceDetailW(hdev, ctypes.byref(did), None, 0, ctypes.byref(req), None)
            buf = ctypes.create_string_buffer(req.value)
            ctypes.memmove(buf, struct.pack("<I", 8), 4)   # cbSize = 8 (64-bit)
            if not _setup.SetupDiGetDeviceInterfaceDetailW(hdev, ctypes.byref(did), buf,
                                                           req.value, ctypes.byref(req), None):
                raise GarminError("Could not read the Garmin device path.")
            path = ctypes.wstring_at(ctypes.addressof(buf) + 4)
        finally:
            _setup.SetupDiDestroyDeviceInfoList(hdev)

        h = _k32.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
        if not h or h == INVALID_HANDLE_VALUE:
            raise GarminError("Found the Garmin but could not open it - another program "
                              "(Garmin Express, BaseCamp, an old GPS app) may be holding it.")
        self.h = h
        # start session
        self._write(self._pkt(LAYER_TRANSPORT, PID_START_SESSION))
        for _ in range(12):
            hd = self._parse(self._read_packet())
            if hd and hd[0] == LAYER_TRANSPORT and hd[1] == PID_SESSION_STARTED and len(hd[3]) >= 4:
                self.unit_id = struct.unpack("<I", hd[3][:4])[0]
                break
        return self.unit_id

    def start_pvt(self):
        self._write(self._pkt(LAYER_APPL, PID_COMMAND_DATA, struct.pack("<H", CMND_START_PVT)))

    def stop_pvt(self):
        try:
            self._write(self._pkt(LAYER_APPL, PID_COMMAND_DATA, struct.pack("<H", CMND_STOP_PVT)))
        except Exception:
            pass

    def read_fix(self):
        """Return a decoded PVT dict, or None if the next packet was not a PVT record."""
        hd = self._parse(self._read_packet())
        if hd and hd[0] == LAYER_APPL and hd[1] == PID_PVT_DATA:
            return self._decode(hd[3])
        return None

    def close(self):
        if self.h:
            _k32.CloseHandle(self.h)
            self.h = None

    # -- low level --
    def _pkt(self, ptype, pid, data=b""):
        return struct.pack("<B3xH2xI", ptype, pid, len(data)) + data

    def _write(self, data):
        n = wintypes.DWORD(0)
        if not _k32.WriteFile(self.h, data, len(data), ctypes.byref(n), None):
            raise GarminError("write to Garmin failed (device unplugged?)")

    def _read_chunk(self):
        buf = ctypes.create_string_buffer(64)
        ret = wintypes.DWORD(0)
        ok = _k32.DeviceIoControl(self.h, IOCTL_GARMIN_USB_INTERRUPT_IN, None, 0,
                                  buf, 64, ctypes.byref(ret), None)
        if not ok:
            raise GarminError("read from Garmin failed (device unplugged?)")
        return buf.raw[:ret.value]

    def _read_packet(self):
        out = b""
        for _ in range(80):
            c = self._read_chunk()
            out += c
            if len(c) < 64:
                break
        return out

    def _parse(self, b):
        if len(b) < 12:
            return None
        ptype = b[0]
        pid = struct.unpack("<H", b[4:6])[0]
        dsize = struct.unpack("<I", b[8:12])[0]
        return ptype, pid, dsize, b[12:12 + dsize]

    def _decode(self, data):
        if len(data) < 64:
            return None
        (alt, epe, eph, epv, fix, tow, lat, lon,
         east, north, up, msl, leap, wn) = struct.unpack("<ffffhdddffffhi", data[:64])
        # ground speed from east/north velocities (m/s -> mph)
        speed_mph = (east * east + north * north) ** 0.5 * 2.236936
        return dict(lat=lat * 180 / pi, lon=lon * 180 / pi, fix=int(fix),
                    alt_msl_m=alt - msl, epe_m=epe, eph_m=eph, speed_mph=speed_mph)


# ---- ArcGIS Earth Automation API ----
class EarthUnreachable(Exception):
    pass


class EarthClient:
    def __init__(self, base=ARCGIS_EARTH_API):
        self.base = base.rstrip("/")
        self._opener = request.build_opener(request.ProxyHandler({}))

    def _http(self, method, path, payload=None):
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=API_TIMEOUT_SECONDS) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code}") from exc
        except Exception as exc:
            raise EarthUnreachable(
                "ArcGIS Earth Automation API not reachable at " + self.base +
                ". In ArcGIS Earth: Settings > Advanced application settings > enable the Automation API.") from exc

    def ping(self):
        self._http("GET", "/arcgisearth/camera")

    def get_camera(self):
        return self._http("GET", "/arcgisearth/camera")

    def put_camera(self, payload):
        self._http("PUT", "/arcgisearth/camera", payload)

    def post_drawing(self, payload):
        self._http("POST", "/arcgisearth/drawings", payload)

    def delete_drawing(self, draw_id):
        try:
            self._http("DELETE", f"/arcgisearth/drawings/{draw_id}")
        except Exception:
            pass


def draw_marker(earth, lat, lon, label=LABEL):
    earth.delete_drawing(DRAW_ID)
    p = {
        "id": DRAW_ID, "visible": True, "title": label,
        "geometry": {"x": lon, "y": lat, "spatialReference": {"wkid": 4326}},
        "labelSymbol": {"type": "text", "color": LABEL_COLOR, "size": LABEL_SIZE},
    }
    if MARKER_ICON.is_file():
        p["symbol"] = {"type": "picture-marker", "url": str(MARKER_ICON), "size": f"{MARKER_SIZE_PX}px"}
    earth.post_drawing(p)


def recenter(earth, lat, lon):
    try:
        cam = earth.get_camera()
        z = cam.get("position", {}).get("z", 2000) if isinstance(cam, dict) else 2000
    except Exception:
        z = 2000
    earth.put_camera({"position": {"x": lon, "y": lat, "z": z, "spatialReference": {"wkid": 4326}},
                      "heading": 0, "tilt": 0})


def csv_log(fix):
    try:
        LOG_DIR.mkdir(exist_ok=True)
        f = LOG_DIR / f"garmin_track_{datetime.date.today():%Y%m%d}.csv"
        new = not f.exists()
        with open(f, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["time", "lat", "lon", "fix", "alt_msl_m", "epe_m", "speed_mph"])
            w.writerow([datetime.datetime.now().isoformat(timespec="seconds"),
                        f"{fix['lat']:.6f}", f"{fix['lon']:.6f}", fix["fix"],
                        f"{fix['alt_msl_m']:.1f}", f"{fix['epe_m']:.1f}", f"{fix['speed_mph']:.1f}"])
    except Exception:
        pass


def run_bridge(state, stop_event, emit):
    """state: object with .center (bool). emit(kind, *args) for the GUI."""
    earth = EarthClient()
    earth_ok = {"v": None}

    def set_earth(ok):
        if ok != earth_ok["v"]:
            earth_ok["v"] = ok
            emit("earth", ok)

    while not stop_event.is_set():
        gps = GarminUSB()
        try:
            emit("status", "opening Garmin GPS ...")
            emit("gps", False)
            uid = gps.open()
            emit("gps", True)
            emit("status", f"connected - unit {uid}, waiting for fix ...")
            gps.start_pvt()
        except GarminError as exc:
            emit("gps", False)
            emit("status", str(exc))
            emit("log", str(exc))
            for _ in range(40):
                if stop_event.is_set():
                    break
                time.sleep(0.1)
            continue

        try:
            while not stop_event.is_set():
                fix = gps.read_fix()
                if not fix:
                    continue
                emit("fix", fix)
                csv_log(fix)
                if fix["fix"] >= 2:                 # have a usable position
                    try:
                        draw_marker(earth, fix["lat"], fix["lon"])
                        set_earth(True)
                        if getattr(state, "center", False):
                            recenter(earth, fix["lat"], fix["lon"])
                    except EarthUnreachable:
                        set_earth(False)
                    except Exception:
                        pass
        except GarminError as exc:
            emit("gps", False)
            emit("status", "lost the GPS - reconnecting ...")
            emit("log", f"{exc} (reconnecting)")
        finally:
            gps.stop_pvt()
            gps.close()
        for _ in range(30):
            if stop_event.is_set():
                break
            time.sleep(0.1)

    try:
        EarthClient().delete_drawing(DRAW_ID)
    except Exception:
        pass
    emit("status", "stopped")
