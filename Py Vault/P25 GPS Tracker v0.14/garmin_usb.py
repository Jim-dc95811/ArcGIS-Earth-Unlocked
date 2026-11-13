"""Garmin USB GPS reader (Claude + Jim, 2026-11-12) - shared by the P25 tracker.

Reads live position from a Garmin USB GPS (GPS 18 USB and kin, USB id 091E:0003)
through Garmin's OWN kernel driver - pure ctypes, no driver change, no COM port, no
NMEA. Reader only: no GUI, no ArcGIS Earth; the caller draws the fixes.

Protocol (proven on Jim's unit 2026-11-12): find the device by Garmin's USB interface
GUID, CreateFile it; Start_Session (transport id 5) -> unit id; Start_Pvt_Data (49) ->
the unit streams a D800 PVT record ~1/sec on the INTERRUPT pipe as a 64-byte chunk + a
short chunk (reassemble); decode D800 (lat/lon radians -> degrees).
"""
import struct, ctypes
from ctypes import wintypes
from math import pi

FIX_TEXT = {0: "no fix", 1: "no fix", 2: "2D", 3: "3D", 4: "2D diff", 5: "3D diff"}

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
_k32.WriteFile.restype = wintypes.BOOL
_k32.WriteFile.argtypes = [wintypes.HANDLE, _P, _DW, _P, _P]
_k32.CloseHandle.restype = wintypes.BOOL
_k32.CloseHandle.argtypes = [wintypes.HANDLE]


def _garmin_guid():
    g = _GUID()
    g.Data1, g.Data2, g.Data3 = 0x2C9C45C2, 0x8E7D, 0x4C08
    for i, b in enumerate((0xA1, 0x2D, 0x81, 0x6B, 0xBA, 0xE7, 0x22, 0xC0)):
        g.Data4[i] = b
    return g


def device_present():
    """True if a Garmin USB GPS interface is present - a read-only check that does NOT
    open the device (so it never clashes with tracking)."""
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


class GarminUSB:
    def __init__(self):
        self.h = None
        self.unit_id = None

    def open(self):
        g = _garmin_guid()
        hdev = _setup.SetupDiGetClassDevsW(ctypes.byref(g), None, None,
                                           DIGCF_PRESENT | DIGCF_DEVICEINTERFACE)
        if not hdev or hdev == INVALID_HANDLE_VALUE:
            raise GarminError("No Garmin USB GPS found (plug it in; driver under Device Manager > GARMIN Devices).")
        try:
            did = _SP_DID()
            did.cbSize = ctypes.sizeof(_SP_DID)
            if not _setup.SetupDiEnumDeviceInterfaces(hdev, None, ctypes.byref(g), 0, ctypes.byref(did)):
                raise GarminError("No Garmin USB GPS present.")
            req = wintypes.DWORD(0)
            _setup.SetupDiGetDeviceInterfaceDetailW(hdev, ctypes.byref(did), None, 0, ctypes.byref(req), None)
            buf = ctypes.create_string_buffer(req.value)
            ctypes.memmove(buf, struct.pack("<I", 8), 4)
            if not _setup.SetupDiGetDeviceInterfaceDetailW(hdev, ctypes.byref(did), buf,
                                                           req.value, ctypes.byref(req), None):
                raise GarminError("Could not read the Garmin device path.")
            path = ctypes.wstring_at(ctypes.addressof(buf) + 4)
        finally:
            _setup.SetupDiDestroyDeviceInfoList(hdev)
        h = _k32.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
        if not h or h == INVALID_HANDLE_VALUE:
            raise GarminError("Found the Garmin but could not open it - another Garmin program may be holding it.")
        self.h = h
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
        hd = self._parse(self._read_packet())
        if hd and hd[0] == LAYER_APPL and hd[1] == PID_PVT_DATA:
            return self._decode(hd[3])
        return None

    def close(self):
        if self.h:
            _k32.CloseHandle(self.h)
            self.h = None

    def _pkt(self, ptype, pid, data=b""):
        return struct.pack("<B3xH2xI", ptype, pid, len(data)) + data

    def _write(self, data):
        n = wintypes.DWORD(0)
        if not _k32.WriteFile(self.h, data, len(data), ctypes.byref(n), None):
            raise GarminError("write to Garmin failed (unplugged?)")

    def _read_chunk(self):
        buf = ctypes.create_string_buffer(64)
        ret = wintypes.DWORD(0)
        if not _k32.DeviceIoControl(self.h, IOCTL_GARMIN_USB_INTERRUPT_IN, None, 0,
                                    buf, 64, ctypes.byref(ret), None):
            raise GarminError("read from Garmin failed (unplugged?)")
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
        return b[0], struct.unpack("<H", b[4:6])[0], struct.unpack("<I", b[8:12])[0], b[12:12 + struct.unpack("<I", b[8:12])[0]]

    def _decode(self, data):
        if len(data) < 64:
            return None
        (alt, epe, eph, epv, fix, tow, lat, lon,
         east, north, up, msl, leap, wn) = struct.unpack("<ffffhdddffffhi", data[:64])
        speed_mph = (east * east + north * north) ** 0.5 * 2.236936
        return dict(lat=lat * 180 / pi, lon=lon * 180 / pi, fix=int(fix),
                    alt_msl_m=alt - msl, epe_m=epe, speed_mph=speed_mph)
