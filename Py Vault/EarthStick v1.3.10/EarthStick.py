#!/usr/bin/env python3
"""EarthStick 1.3.10

1.3.10: buttons swapped (Jim, 2026-11-07, two-handed flying: the mouse does the clicking, so the trigger drops
  gates) - Button 1 (trigger) = Gate Dropper (press at two places; hold 2 s = undo), Button 2 = click the object
  under the crosshair. Nothing else changed from 1.3.9.

1.3.9: hardening (Jim approved 1, 2, 3, 5, 6 on 2026-11-08) - flying, gates and Gate Dropper unchanged:
  1. only one EarthStick at a time: a second copy (an extra double-click on a slow PC) says so and closes,
     instead of two programs fighting over the camera
  2. the tractor beam no longer pulls you back while you move the map with the mouse near a gate: when
     the stick is let go it re-reads the camera before each nudge and only changes the height
  3. the status line fits the window, so it updates in place instead of scrolling on a normal-size window
  5. hold-Button-2 undo removes the highest-numbered dropped gate (Dropped_Gate_100 after 99, not 99)
  6. the 'waiting for ArcGIS Earth' message names the exact setting: Settings > Advanced application
     settings > Enable Automation API

1.3.6: the Gate Dropper (Jim, 2026-11-06: 'manually entering that info is a huge pain ... I would love
  to automate that procedure') - fly to a place and hover, press Button 2: mark 1 saved. Fly to a second
  place (at least 750 m away), press Button 2 again: EarthStick writes a pair of World Gates there into
  the Gates folder (Dropped_Gate_01.kmz, 02, ...), each at exactly the height you were hovering, arms
  them at once (no restart) and asks ArcGIS Earth to show the file on the map. Same look as World Gate
  Maker gates (Medium size, square with legs).
  TEST2 (Jim: 'I can not orient myself to face the gate in the babel pic ... at 90 degrees'): each gate
  now faces the way you were LOOKING when you pressed Button 2 (TEST faced the other mark, like World Gate
  Maker), and going through it lands you 300 m past the other gate looking the way you looked when you
  marked it - the gate behind you, so no bounce back.
  TEST3 (Jim: TEST2 'is impossible' - the way in was behind you, over the water): each gate now appears
  500 m IN FRONT of you at your height, facing the way you look - press Button 2, then just push forward.
  TEST4 (Jim: 'the manual delete thing sucks'): HOLD Button 2 for 2 seconds = undo. With a mark 1 waiting,
  it clears the mark; otherwise it deletes the newest Dropped_Gate file, disarms its gates at once and
  removes it from the ArcGIS Earth map (if EarthStick put it there in this session). The number is reused.
  A short press now acts when you let go of the button.
  TEST5 (Jim: the picture islands are huge, so you approach far above or below; gold is an eyesore on a
  painting): a gate may carry its own grab zone (lock_capture_m / lock_range_m in its data) - dropped gates
  grab you from 3 km out and +-2,000 ft; World Gates and World Gate Maker gates keep the 1.5 km / 1 radius
  zone. Dropped gates are drawn thin and black (red back), with a bigger opening (about 425 m across) and
  white names. While locked on, the light counts down the distance: LOCKED ON · 1,380 ft. Press Button 2 again near mark 1 (closer than 750 m) to clear
  the mark. The drawing code is in gate_dropper.py beside this file. Flying is unchanged.

1.3.5: one obvious file (Jim, 2026-11-06) - the package now shows only Fly_ArcGIS_Earth.bat, Gates,
  City_Beacons and System Files. This file lives in System Files, so the Gates folder is read from the
  folder above it. Flying is unchanged.

1.3.4: the ring-height light (Jim, 2026-11-05) - a green light above the readout comes on when you are at
  the height of the World Gate ring you are flying toward (EarthStick flies level, so height is the part
  the crosshair cannot show). The ring that counts is the nearest one ahead of you (within 15 degrees of
  your heading), whose gold side faces you, within 10 km - so a nearby ring off to the side never lights
  it. Green = within half the ring's radius of its centre height. Flying, gates, trigger-click and the
  readout are otherwise unchanged.
  TEST5: the tractor beam (Jim) - flying forward at the ring ahead, within 1,500 m and within one ring
  radius of its height, EarthStick glides you onto the ring's centre height (half the gap each second)
  and the light says LOCKED ON. Stop pushing forward, turn away, or press climb/descend (buttons 3/4)
  and it lets go at once.
  TEST6: proximity, not motion - it also pulls while you hover near the ring (Jim: 'proximity snap'),
  and when you are moving it lays a straight glide path to the ring's centre height so it is done by the
  mouth even at full throttle (TEST5 pulled only while pushing forward, half the gap per second: too slow
  at 668 m/s). Climb/descend buttons still release it at once.
  TEST7: program as TEST6 (Jim: 'it works perfect'); ships with World Gates v21 - square gates with legs.

1.3.3: a small readout at the bottom right of ArcGIS Earth (Jim, 2026-11-04) - height, compass heading and
  an equivalent map zoom level ("1,970 ft · NE 45° · ≈ Z19"), visible in full-screen mode too; flying,
  gates and trigger-click are unchanged
  TEST2: moved up above the globe button (Jim: the bottom corner is ArcGIS Earth's), room for the whole text
  TEST3: altitude on its own line above heading and zoom (Jim)

1.3.2: release with the World Gates v19 pack; the program is unchanged apart from this version text

1.3.1: larger, thicker crosshair (80 px, 5 px lines) for aiming at World Gates;
  nothing else changed

1.3 adds wormholes (flying, trigger-click, constants and recovery unchanged from 1.2):
  - gate files (KML/KMZ golden rings with gate data) in a "Gates" folder beside
    this program are read at startup
  - fly through a gate ring in its facing direction and the camera jumps:
    to just past the partner gate named in "to" (facing away from it), or to a
    fixed destination (one-way gate)
  - gates only fire when crossed forwards, and not again for GATE_COOLDOWN_S
  - a gate's "to" partner is looked up in its own file first, so two gate files
    may reuse names (TEST2); a name that is ambiguous across files is skipped
    with a message
  - no Gates folder or no gate files = flies exactly as 1.2

1.2 adds trigger-click (flying, constants and recovery unchanged from 1.1):
  - a red crosshair sits at the centre of the ArcGIS Earth window (click-through)
  - put an object under the crosshair, let go (hover) and pull the trigger
    (button 1): EarthStick clicks it for you, so its popup opens without the mouse
  - the click glides the pointer onto the target and rests before and after, which
    ArcGIS Earth needs to select an object (an instant click zooms instead)
  - if the crosshair cannot be shown, EarthStick still flies normally

1.1 hardening (controls, constants, movement, zoom and recovery unchanged):
  - if the joystick is not connected at startup, EarthStick waits for it
    instead of stopping
  - the local ArcGIS Earth API connection never goes through a system proxy
  - while waiting for ArcGIS Earth, the reason is shown when it first appears
    or changes
  - one "press Enter" prompt after an error instead of two

Thrustmaster T.A320 Pilot -> ArcGIS Earth camera bridge.

Controls:
  X axis       : strafe left/right
  Y axis       : move forward/back
  RZ axis      : heading left/right
  Slider0      : movement speed
  POV up/down  : camera tilt

Button 4 (red top button) zooms in / descends.
Button 3 (black thumb button) zooms out / climbs.
Button 1 (trigger) drops gates: press once at each of two places; hold 2 s = undo (1.3.10; was Button 2).
Button 2 clicks the object under the crosshair (1.3.10; was Button 1).
Neutral controls stop and hover in place.

Standard-library only. Windows desktop ArcGIS Earth Automation API is expected
at http://localhost:8000.
"""

from __future__ import annotations

import ctypes
import json
import math
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from ctypes import wintypes
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

VERSION = "1.3.10"
BASE_URL = "http://localhost:8000"
CAMERA_URL = BASE_URL + "/arcgisearth/camera"
TARGET_NAME = "T.A320 Pilot"

POLL_HZ = 30.0
DEADZONE = 0.08
YAW_RATE_DPS = 55.0
TILT_RATE_DPS = 45.0
EARTH_RADIUS_M = 6378137.0
IDLE_RESYNC_SECONDS = 0.50
HTTP_TIMEOUT = 0.75

# Thrustmaster manual: RZ decreases toward right twist, so invert for
# intuitive right-twist = increasing/right heading.
INVERT_TWIST = False
# Thrustmaster manual: Slider0 is 0 at the forward/+ end, so invert so
# forward throttle = faster movement.
INVERT_THROTTLE = True

# Trigger-click (1.2)
TRIGGER_BUTTON = 2            # 1.3.10: joystick button that clicks (joy.cpl numbering); was 1 (Jim: the trigger drops gates, the mouse does two-handed work)
EARTH_EXE = "arcgisearth"     # matched against the window's program file name
CENTER_OFFSET_X = 0           # nudge the crosshair (screen pixels) if needed
CENTER_OFFSET_Y = 0
RETICLE_SIZE = 80              # crosshair size in pixels (1.3.1; was 48)
RETICLE_WIDTH = 5             # line thickness (1.3.1; was 3)
RETICLE_COLOR = "#ff2020"
SHOW_READOUT = True            # 1.3.3: height / heading / zoom readout, bottom right of ArcGIS Earth
READOUT_FONT = ("Segoe UI", 16, "bold")
READOUT_COLOR = "#ffffff"
READOUT_RIGHT_PX = 60          # gap from the right edge of the ArcGIS Earth window (lines up over the globe button)
READOUT_BOTTOM_PX = 480        # text bottom above the window bottom, full screen: clear above the globe button (TEST2)
READOUT_BOTTOM_WINDOWED_PX = 695   # same, when ArcGIS Earth is a normal window (status bar below) (TEST2)
VIEW_WIDTH_DEG = 78.0          # ArcGIS Earth's horizontal field of view (measured on Jim's screenshots)
CLICK_LOCKOUT_S = 0.8         # one click per pull, never two within a double-click time
ACTIVATE_PAUSE_S = 0.7        # pause between an activating click and the real click
HOVER_BEFORE_S = 0.25         # pointer rests on the object before the click
PRESS_S = 0.08                # how long the button is held down
HOVER_AFTER_S = 0.4           # pointer stays on the object after the click


# Wormholes (1.3)
# Ring-height light (1.3.4)
RING_LIGHT = True             # green light above the readout when you are at the height of the ring ahead
RING_LIGHT_RANGE_M = 10000.0  # only rings closer than this count
RING_LIGHT_CONE_DEG = 15.0    # ...that are within this many degrees of your heading
RING_LIGHT_FACING_DEG = 60.0  # ...whose gold side faces you (ring direction within this of your heading)
RING_LIGHT_TOLERANCE = 0.5    # green within this fraction of the ring's radius above or below its centre
RING_LIGHT_COLOR = "#39ff4a"
RING_LIGHT_TEXT = "\u25cf RING HEIGHT"
# Tractor beam (1.3.4 TEST5)
TRACTOR_BEAM = True           # glide onto the ring's height on the final approach
TRACTOR_RANGE_M = 1500.0      # starts pulling within this distance of the ring ahead
TRACTOR_CAPTURE = 1.0         # ...when within this many ring radii above or below its centre
TRACTOR_HALF_LIFE_S = 1.0     # half the remaining height gap is closed every this many seconds
TRACTOR_TEXT = "\u25cf LOCKED ON"

DROP_BUTTON = 1               # 1.3.10: Gate Dropper on the trigger (was Button 2 in 1.3.6-1.3.9)
DROP_ADD_TO_MAP = True        # 1.3.6: ask ArcGIS Earth to show a dropped gate file on the map
DROP_UNDO_HOLD_S = 2.0        # 1.3.6 TEST4: hold Button 2 this long = undo
NOTICE_S = 5.0                # 1.3.6: how long a Gate Dropper message stays above the readout
NOTICE_COLOR = "#ffd700"      # gold, like the gates
GATES_FOLDER = "Gates"        # 1.3.5: in the EarthStick folder (one level above System Files)
GATE_EXIT_M = 300.0           # arrive this far past the partner gate
GATE_COOLDOWN_S = 2.0         # no second jump within this time
GATE_MAX_RANGE_M = 50000.0    # gates farther away than this are not checked


class EarthAPIError(RuntimeError):
    pass


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def deadzone(v: float, dz: float = DEADZONE) -> float:
    if abs(v) <= dz:
        return 0.0
    sign = 1.0 if v > 0 else -1.0
    return sign * (abs(v) - dz) / (1.0 - dz)


def norm_centered(raw: int, lo: int, hi: int) -> float:
    if hi <= lo:
        return 0.0
    unit = (float(raw) - float(lo)) / float(hi - lo)
    return clamp(unit * 2.0 - 1.0, -1.0, 1.0)


def norm_unit(raw: int, lo: int, hi: int) -> float:
    if hi <= lo:
        return 0.0
    return clamp((float(raw) - float(lo)) / float(hi - lo), 0.0, 1.0)


def speed_from_throttle(throttle: float, altitude_m: float) -> float:
    """Altitude-aware max speed with fine low-speed control."""
    throttle = clamp(throttle, 0.0, 1.0)
    max_speed = clamp(max(8.0, altitude_m * 0.020), 8.0, 12000.0) * 60.0
    min_speed = 0.50
    return min_speed + (max_speed - min_speed) * (throttle ** 2.0)


def move_lonlat(lon: float, lat: float, heading_deg: float,
                forward_m: float, right_m: float) -> tuple[float, float]:
    """Small-step heading-relative movement on WGS84-like sphere."""
    h = math.radians(heading_deg)
    north_m = forward_m * math.cos(h) - right_m * math.sin(h)
    east_m = forward_m * math.sin(h) + right_m * math.cos(h)

    lat_rad = math.radians(lat)
    dlat = north_m / EARTH_RADIUS_M
    coslat = max(0.001, abs(math.cos(lat_rad)))
    dlon = east_m / (EARTH_RADIUS_M * coslat)

    lat2 = clamp(lat + math.degrees(dlat), -89.9, 89.9)
    lon2 = lon + math.degrees(dlon)
    lon2 = ((lon2 + 180.0) % 360.0) - 180.0
    return lon2, lat2


# ArcGIS Earth runs on this computer, so its API must never be sent through a
# system or agency proxy (urllib would otherwise use the Windows proxy setting).
_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http_json(method: str, url: str, body=None):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _LOCAL_OPENER.open(req, timeout=HTTP_TIMEOUT) as resp:
            raw = resp.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise EarthAPIError(str(exc)) from exc


def get_camera():
    cam = http_json("GET", CAMERA_URL)
    if not isinstance(cam, dict) or not isinstance(cam.get("position"), dict):
        raise EarthAPIError("Unexpected camera response")

    pos = cam["position"]
    sr = pos.get("spatialReference") or {}
    if not isinstance(sr, dict):
        raise EarthAPIError("Unexpected camera spatial reference")
    wkid = sr.get("wkid")
    if wkid not in (4326, "4326", None):
        raise EarthAPIError(f"Camera spatial reference is {wkid}; EarthStick requires WKID 4326")

    try:
        x = float(pos["x"])
        y = float(pos["y"])
        z = float(pos["z"])
        heading = float(cam.get("heading", 0.0))
        tilt = float(cam.get("tilt", 0.0))
        roll = float(cam.get("roll", 0.0))
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise EarthAPIError(f"Invalid camera response: {exc}") from exc

    if not all(math.isfinite(v) for v in (x, y, z, heading, tilt, roll)):
        raise EarthAPIError("Camera response contains non-finite numeric values")

    # Preserve all documented camera properties.
    return {
        "position": {
            "x": x,
            "y": y,
            "z": z,
            "spatialReference": {"wkid": 4326},
        },
        "heading": heading,
        "tilt": tilt,
        "roll": roll,
    }


def put_camera(cam):
    http_json("PUT", CAMERA_URL, cam)


# --- Windows Multimedia Joystick API ---------------------------------------

MAXPNAMELEN = 32
MAX_JOYSTICKOEMVXDNAME = 260
JOY_RETURNX = 0x00000001
JOY_RETURNY = 0x00000002
JOY_RETURNZ = 0x00000004
JOY_RETURNR = 0x00000008
JOY_RETURNU = 0x00000010
JOY_RETURNV = 0x00000020
JOY_RETURNPOV = 0x00000040
JOY_RETURNBUTTONS = 0x00000080
JOY_RETURNALL = 0x000000FF
JOYERR_NOERROR = 0
JOY_POVCENTERED = 0xFFFF


class JOYCAPS(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("szPname", wintypes.WCHAR * MAXPNAMELEN),
        ("wXmin", wintypes.UINT), ("wXmax", wintypes.UINT),
        ("wYmin", wintypes.UINT), ("wYmax", wintypes.UINT),
        ("wZmin", wintypes.UINT), ("wZmax", wintypes.UINT),
        ("wNumButtons", wintypes.UINT),
        ("wPeriodMin", wintypes.UINT), ("wPeriodMax", wintypes.UINT),
        ("wRmin", wintypes.UINT), ("wRmax", wintypes.UINT),
        ("wUmin", wintypes.UINT), ("wUmax", wintypes.UINT),
        ("wVmin", wintypes.UINT), ("wVmax", wintypes.UINT),
        ("wCaps", wintypes.UINT),
        ("wMaxAxes", wintypes.UINT), ("wNumAxes", wintypes.UINT),
        ("wMaxButtons", wintypes.UINT),
        ("szRegKey", wintypes.WCHAR * MAXPNAMELEN),
        ("szOEMVxD", wintypes.WCHAR * MAX_JOYSTICKOEMVXDNAME),
    ]


class JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("dwXpos", wintypes.DWORD), ("dwYpos", wintypes.DWORD),
        ("dwZpos", wintypes.DWORD), ("dwRpos", wintypes.DWORD),
        ("dwUpos", wintypes.DWORD), ("dwVpos", wintypes.DWORD),
        ("dwButtons", wintypes.DWORD), ("dwButtonNumber", wintypes.DWORD),
        ("dwPOV", wintypes.DWORD),
        ("dwReserved1", wintypes.DWORD), ("dwReserved2", wintypes.DWORD),
    ]


class WinJoystick:
    def __init__(self, preferred_name: str = TARGET_NAME):
        if os.name != "nt":
            raise RuntimeError("EarthStick requires Windows")
        self.winmm = ctypes.WinDLL("winmm")
        self.winmm.joyGetNumDevs.restype = wintypes.UINT
        self.winmm.joyGetDevCapsW.argtypes = [wintypes.UINT, ctypes.POINTER(JOYCAPS), wintypes.UINT]
        self.winmm.joyGetDevCapsW.restype = wintypes.UINT
        self.winmm.joyGetPosEx.argtypes = [wintypes.UINT, ctypes.POINTER(JOYINFOEX)]
        self.winmm.joyGetPosEx.restype = wintypes.UINT
        self.id, self.caps = self._find(preferred_name)
        self.slider_name, self.slider_field, self.slider_min, self.slider_max = self._detect_slider_axis()

    def _detect_slider_axis(self):
        # T.A320 exposes X, Y, RZ plus one Slider0 axis. WinMM can place
        # that slider on Z, U, or V depending on the driver mapping.
        # Use the axis capability flags instead of assuming U.
        JOYCAPS_HASZ = 0x0001
        JOYCAPS_HASU = 0x0004
        JOYCAPS_HASV = 0x0008
        candidates = [
            ("Z", "dwZpos", self.caps.wZmin, self.caps.wZmax, JOYCAPS_HASZ),
            ("U", "dwUpos", self.caps.wUmin, self.caps.wUmax, JOYCAPS_HASU),
            ("V", "dwVpos", self.caps.wVmin, self.caps.wVmax, JOYCAPS_HASV),
        ]
        present = [
            (name, field, lo, hi)
            for name, field, lo, hi, flag in candidates
            if (self.caps.wCaps & flag) and hi > lo
        ]
        if len(present) != 1:
            names = ", ".join(name for name, _, _, _ in present) or "none"
            raise RuntimeError(f"Could not identify Slider0 axis uniquely (Z/U/V present: {names})")
        return present[0]

    def _connected(self, joy_id: int) -> bool:
        ji = JOYINFOEX()
        ji.dwSize = ctypes.sizeof(JOYINFOEX)
        ji.dwFlags = JOY_RETURNALL
        return self.winmm.joyGetPosEx(joy_id, ctypes.byref(ji)) == JOYERR_NOERROR

    def _find(self, preferred_name: str):
        connected = []
        for joy_id in range(int(self.winmm.joyGetNumDevs())):
            caps = JOYCAPS()
            rc = self.winmm.joyGetDevCapsW(joy_id, ctypes.byref(caps), ctypes.sizeof(caps))
            if rc == JOYERR_NOERROR and self._connected(joy_id):
                connected.append((joy_id, caps))
        if not connected:
            raise RuntimeError("No Windows joystick is connected")
        preferred = preferred_name.casefold()
        for joy_id, caps in connected:
            if preferred in caps.szPname.casefold():
                return joy_id, caps

        # Some Windows/Thrustmaster installations expose only the generic
        # WinMM driver name ("Microsoft PC-joystick driver") even though
        # joy.cpl correctly shows "T.A320 Pilot". Fall back to the known
        # T.A320 control capabilities: 4 axes, 17 buttons, and a POV hat.
        JOYCAPS_HASPOV = 0x0010
        matches = [
            (joy_id, caps) for joy_id, caps in connected
            if caps.wNumAxes >= 4
            and caps.wNumButtons == 17
            and (caps.wCaps & JOYCAPS_HASPOV)
        ]
        if len(matches) == 1:
            return matches[0]

        names = ", ".join(c.szPname for _, c in connected)
        raise RuntimeError(f"{preferred_name!r} not found uniquely. Connected: {names}")

    def read(self):
        ji = JOYINFOEX()
        ji.dwSize = ctypes.sizeof(JOYINFOEX)
        ji.dwFlags = JOY_RETURNALL
        rc = self.winmm.joyGetPosEx(self.id, ctypes.byref(ji))
        if rc != JOYERR_NOERROR:
            raise RuntimeError(f"Joystick read failed ({rc})")

        x = deadzone(norm_centered(ji.dwXpos, self.caps.wXmin, self.caps.wXmax))
        y = deadzone(norm_centered(ji.dwYpos, self.caps.wYmin, self.caps.wYmax))
        rz = deadzone(norm_centered(ji.dwRpos, self.caps.wRmin, self.caps.wRmax))
        if INVERT_TWIST:
            rz = -rz

        throttle_raw = getattr(ji, self.slider_field)
        throttle = norm_unit(throttle_raw, self.slider_min, self.slider_max)
        if INVERT_THROTTLE:
            throttle = 1.0 - throttle

        pov = int(ji.dwPOV)
        tilt_axis = 0.0
        if pov != JOY_POVCENTERED:
            # hundredths of a degree: 0=up, 9000=right, 18000=down, 27000=left
            angle = pov % 36000
            if angle <= 4500 or angle >= 31500:
                tilt_axis = 1.0
            elif 13500 <= angle <= 22500:
                tilt_axis = -1.0

        return {
            "strafe": x,
            "forward": -y,
            "yaw": rz,
            "throttle": throttle,
            "tilt": tilt_axis,
            "buttons": int(ji.dwButtons),
        }


def wait_for_joystick_reconnect(factory=None, sleep_fn=None):
    """Wait for the configured joystick to become available again."""
    if factory is None:
        factory = WinJoystick
    if sleep_fn is None:
        sleep_fn = time.sleep

    while True:
        try:
            return factory()
        except RuntimeError:
            sleep_fn(1.0)


def print_status(name: str, state, cam, speed: float, active: bool):
    status = "FLY" if active else "IDLE"
    line = (
        f"{status:<4}  X {state['strafe']:+.2f}  Y {state['forward']:+.2f}  "
        f"RZ {state['yaw']:+.2f}  THR {state['throttle']:.2f}  "
        f"SPD {speed:7.1f} m/s  HDG {cam['heading']:6.1f}  TILT {cam['tilt']:5.1f}"
    )
    width = min(150, max(40, shutil.get_terminal_size((151, 20)).columns - 1))   # 1.3.9: fit the window (no wrap)
    sys.stdout.write("\r" + line[:width].ljust(width))
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Trigger-click (1.2). Everything here is optional: if any part fails, EarthStick
# flies exactly as before. The crosshair window and the clicking run in their own
# thread so the flying loop never waits for them.

def window_center(rect, off_x=0, off_y=0):
    left, top, right, bottom = rect
    return (left + right) // 2 + off_x, (top + bottom) // 2 + off_y


COMPASS_POINTS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def compass_point(heading_deg: float) -> str:
    return COMPASS_POINTS[int(((heading_deg % 360.0) + 22.5) // 45.0) % 8]


def zoom_equivalent(height_m: float, lat_deg: float, view_px: int) -> int:
    """Web-map zoom level whose tiles match ArcGIS Earth's sharpness straight below this height.
    One screen pixel covers height / focal_length metres; zoom z covers 156543.03 * cos(lat) / 2**z."""
    f = (view_px / 2.0) / math.tan(math.radians(VIEW_WIDTH_DEG / 2.0))
    m_per_px = max(float(height_m), 1.0) / f
    z = math.log2(156543.03392 * max(math.cos(math.radians(lat_deg)), 0.01) / m_per_px)
    return int(clamp(round(z), 0, 23))


def _angle_off(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def ring_ahead(cam, gates):
    """The ring you are flying toward: nearest one within RING_LIGHT_CONE_DEG of your heading, gold side
    facing you, within RING_LIGHT_RANGE_M. None if there is no such ring."""
    return ring_ahead_with_distance(cam, gates)[0]


def ring_ahead_with_distance(cam, gates):
    """(ring, horizontal metres) for ring_ahead(); (None, None) if there is none."""
    pos = cam["position"]
    lat, lon, hd = float(pos["y"]), float(pos["x"]), float(cam["heading"])
    best, best_d = None, None
    for g in gates or ():
        n = math.radians(g["lat"] - lat) * EARTH_RADIUS_M
        e = math.radians(g["lon"] - lon) * EARTH_RADIUS_M * math.cos(math.radians(lat))
        d = math.hypot(e, n)
        if d < 1.0 or d > RING_LIGHT_RANGE_M:
            continue
        if _angle_off(math.degrees(math.atan2(e, n)), hd) > RING_LIGHT_CONE_DEG:
            continue
        if _angle_off(g["facing"], hd) > RING_LIGHT_FACING_DEG:
            continue
        if best_d is None or d < best_d:
            best, best_d = g, d
    return best, best_d


TRACTOR_SETTLE_M = 0.3        # closer than this to the ring's height = holding, nothing to send


def tractor_pull(next_cam, gates, dt, travel_m, zoom_dir):
    """Tractor beam: the ring ahead (same separation rule as the light), within TRACTOR_RANGE_M and within
    TRACTOR_CAPTURE ring radii of its height, pulls next_cam's height toward the ring's centre height -
    hovering or flying. Each step closes at least half the gap per TRACTOR_HALF_LIFE_S, and when moving at
    least travel/distance of it (a straight glide path that ends at the mouth). Climb/descend = no pull.
    Returns (locked, moved): locked = the beam has you; moved = the height was changed."""
    if not (TRACTOR_BEAM and gates) or zoom_dir != 0 or dt <= 0.0:
        return False, False
    g, d = ring_ahead_with_distance(next_cam, gates)
    if g is None or d > g.get("lock_range_m", TRACTOR_RANGE_M):        # TEST5: a gate may carry its own zone
        return False, False
    pos = next_cam["position"]
    gap = g["alt_m"] - float(pos["z"])
    if abs(gap) > g.get("lock_capture_m", TRACTOR_CAPTURE * g["radius_m"]):
        return False, False
    if abs(gap) <= TRACTOR_SETTLE_M:
        return True, False
    frac = max(1.0 - 0.5 ** (dt / TRACTOR_HALF_LIFE_S), min(1.0, max(float(travel_m), 0.0) / max(d, 1.0)))
    pos["z"] = float(pos["z"]) + gap * frac
    return True, True


def ring_light_on(cam, gates):
    g = ring_ahead(cam, gates)
    return g is not None and abs(float(cam["position"]["z"]) - g["alt_m"]) <= RING_LIGHT_TOLERANCE * g["radius_m"]


def readout_text(cam, view_px: int) -> str:
    pos = cam["position"]
    ft = float(pos["z"]) / 0.3048
    hdg = float(cam["heading"]) % 360.0
    return (f"{ft:,.0f} ft\n{compass_point(hdg)} {hdg:.0f}\u00b0 \u00b7 "
            f"\u2248 Z{zoom_equivalent(pos['z'], pos['y'], view_px)}")


def is_earth_exe(path, needle=EARTH_EXE):
    name = os.path.basename(path or "").lower()
    return name.endswith(".exe") and needle in name


class TriggerGate:
    """Fires once per trigger pull, and never twice within CLICK_LOCKOUT_S."""
    def __init__(self, lockout=CLICK_LOCKOUT_S):
        self.lockout = lockout
        self.was_down = False
        self.last = None

    def update(self, down, now):
        fire = down and not self.was_down
        self.was_down = down
        if not fire:
            return False
        if self.last is not None and now - self.last < self.lockout:
            return False
        self.last = now
        return True


class TriggerClick:
    """Crosshair overlay + simulated mouse click, run in a background thread."""

    def __init__(self):
        import queue
        import threading
        self.requests = queue.Queue()
        self.ready = threading.Event()
        self.error = None
        self.gate = TriggerGate()
        self.thread = threading.Thread(target=self._thread_main, name="TriggerClick", daemon=True)

    @classmethod
    def start(cls):
        """Start the crosshair; returns the TriggerClick, or None (with the reason printed)."""
        try:
            tc = cls()
            tc.thread.start()
            tc.ready.wait(5.0)
            if tc.error or not tc.ready.is_set():
                raise RuntimeError(tc.error or "crosshair did not start")
            print(f"Trigger-click: ready (button {TRIGGER_BUTTON} clicks the object under the red crosshair)")
            return tc
        except Exception as exc:
            print(f"Trigger-click: unavailable ({exc}); flying is not affected.")
            return None

    def on_buttons(self, buttons):
        """Called from the flying loop with the button mask; never blocks."""
        down = bool(buttons & (1 << (TRIGGER_BUTTON - 1)))
        if self.gate.update(down, time.perf_counter()):
            self.requests.put("click")

    # -- everything below runs in the TriggerClick thread ------------------
    def _thread_main(self):
        try:
            self._setup_windows()
            import tkinter as tk
            self.root = tk.Tk()
            self.root.withdraw()
            ov = tk.Toplevel(self.root)
            ov.overrideredirect(True)
            ov.attributes("-topmost", True)
            key = "#010203"
            ov.configure(bg=key)
            ov.attributes("-transparentcolor", key)
            s = RETICLE_SIZE
            c = tk.Canvas(ov, width=s, height=s, bg=key, highlightthickness=0)
            c.pack()
            m, gap = s // 2, 8
            for x0, y0, x1, y1 in ((0, m, m - gap, m), (m + gap, m, s, m), (m, 0, m, m - gap), (m, m + gap, m, s)):
                c.create_line(x0, y0, x1, y1, fill=RETICLE_COLOR, width=RETICLE_WIDTH)
            c.create_oval(m - 3, m - 3, m + 3, m + 3, outline=RETICLE_COLOR, fill=RETICLE_COLOR)
            ov.update_idletasks()
            self._click_through(ov)
            ov.withdraw()
            self.overlay = ov
            self.center = None
            self.readout = None                     # 1.3.3: text set by the flying loop
            self.view_px = 1920
            self.ro = None
            if SHOW_READOUT:
                try:
                    ro = tk.Toplevel(self.root)
                    ro.overrideredirect(True)
                    ro.attributes("-topmost", True)
                    ro.configure(bg=key)
                    ro.attributes("-transparentcolor", key)
                    self.ro_w, self.ro_h = 1000, 320   # room for the full text at any screen scaling (1.3.4: plus the ring light line)
                    rc = tk.Canvas(ro, width=self.ro_w, height=self.ro_h, bg=key, highlightthickness=0)
                    rc.pack()
                    self.ro_items = [rc.create_text(self.ro_w - 4 + dx, self.ro_h - 4 + dy, text="", anchor="se", justify="right",
                                                    font=READOUT_FONT, fill="#000000")
                                     for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2))]
                    self.ro_items.append(rc.create_text(self.ro_w - 4, self.ro_h - 4, text="", anchor="se", justify="right",
                                                        font=READOUT_FONT, fill=READOUT_COLOR))
                    # 1.3.4: the ring-height light, one line above the readout
                    self.light_items = [rc.create_text(self.ro_w - 4 + dx, 0 + dy, text="", anchor="se", font=READOUT_FONT, fill="#000000")
                                        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2))]
                    self.light_items.append(rc.create_text(self.ro_w - 4, 0, text="", anchor="se", font=READOUT_FONT,
                                                           fill=RING_LIGHT_COLOR))
                    self.ring_light, self.light_shown = False, None
                    ro.update_idletasks()
                    self._click_through(ro)
                    ro.withdraw()
                    self.ro, self.ro_canvas, self.ro_shown = ro, rc, ""
                    self.root.after(250, self._refresh_readout)
                except Exception:
                    self.ro = None
            self.ready.set()
            self.root.after(100, self._track)
            self.root.after(50, self._serve)
            self.root.mainloop()
        except Exception as exc:
            self.error = str(exc) or type(exc).__name__
            self.ready.set()

    def _setup_windows(self):
        self.user32 = ctypes.WinDLL("user32")
        self.kernel32 = ctypes.WinDLL("kernel32")
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        try:
            self.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))   # real screen pixels
        except Exception:
            try:
                ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
            except Exception:
                pass
        self.earth_hwnd = None

    def _click_through(self, tk_window):
        hwnd = self.user32.GetParent(tk_window.winfo_id()) or tk_window.winfo_id()
        style = self.user32.GetWindowLongW(hwnd, -20)                       # GWL_EXSTYLE
        style |= 0x00080000 | 0x00000020 | 0x00000080 | 0x08000000           # layered, transparent, toolwindow, noactivate
        self.user32.SetWindowLongW(hwnd, -20, style)

    def _exe_of(self, hwnd):
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = self.kernel32.OpenProcess(0x1000, False, pid.value)              # query limited information
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(len(buf))
            return buf.value if self.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)) else ""
        finally:
            self.kernel32.CloseHandle(h)

    def _earth_rect(self):
        found = []
        EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd, _):
            if self.user32.IsWindowVisible(hwnd) and not self.user32.IsIconic(hwnd) and is_earth_exe(self._exe_of(hwnd)):
                r = wintypes.RECT()
                if self.user32.GetWindowRect(hwnd, ctypes.byref(r)):
                    w, h = r.right - r.left, r.bottom - r.top
                    if w > 200 and h > 200:
                        found.append((w * h, (r.left, r.top, r.right, r.bottom), hwnd))
            return True

        self.user32.EnumWindows(EnumProc(callback), 0)
        if not found:
            self.earth_hwnd = None
            return None
        best = max(found, key=lambda f: f[0])
        self.earth_hwnd = best[2]
        return best[1]

    def _track(self):
        try:
            rect = self._earth_rect()
            if rect is None:
                self.center = None
                self.overlay.withdraw()
            else:
                self.center = window_center(rect, CENTER_OFFSET_X, CENTER_OFFSET_Y)
                x, y = self.center
                half = RETICLE_SIZE // 2
                self.overlay.geometry(f"{RETICLE_SIZE}x{RETICLE_SIZE}+{x - half}+{y - half}")
                self.overlay.deiconify()
                self.overlay.attributes("-topmost", True)
                self._place_readout(rect)
        except Exception:
            pass
        if self.center is None:
            try:
                if self.ro is not None:
                    self.ro.withdraw()
            except Exception:
                pass
        self.root.after(400, self._track)

    def _place_readout(self, rect):
        if self.ro is None:
            return
        try:
            left, top, right, bottom = rect
            self.view_px = max(200, right - left)
            screen_h = self.user32.GetSystemMetrics(1)
            full = (bottom - top) >= screen_h - 2
            gap = READOUT_BOTTOM_PX if full else READOUT_BOTTOM_WINDOWED_PX
            x = right - READOUT_RIGHT_PX - self.ro_w
            y = bottom - gap - self.ro_h
            self.ro.geometry(f"{self.ro_w}x{self.ro_h}+{x}+{y}")
            if self.readout:
                self.ro.deiconify()
                self.ro.attributes("-topmost", True)
        except Exception:
            pass

    def _refresh_readout(self):
        try:
            text = self.readout or ""
            changed = text != self.ro_shown
            if changed:
                for item in self.ro_items:
                    self.ro_canvas.itemconfigure(item, text=text)
                self.ro_shown = text
            light = "" if not text else (getattr(self, "tractor_text", TRACTOR_TEXT) if getattr(self, "tractor", False) else
                                         RING_LIGHT_TEXT if getattr(self, "ring_light", False) else "")
            color = RING_LIGHT_COLOR
            note = getattr(self, "notice", None)          # 1.3.6: Gate Dropper message, shown for NOTICE_S
            if text and note and time.perf_counter() < note[1]:
                light, color = note[0], NOTICE_COLOR
            if changed or light != self.light_shown:
                self.ro_canvas.itemconfigure(self.light_items[-1], fill=color)
                bb = self.ro_canvas.bbox(self.ro_items[-1])
                top = (bb[1] if bb else self.ro_h) - 2
                offsets = ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2), (0, 0))
                for item, (dx, dy) in zip(self.light_items, offsets):
                    self.ro_canvas.coords(item, self.ro_w - 4 + dx, top + dy)
                    self.ro_canvas.itemconfigure(item, text=light)
                self.light_shown = light
        except Exception:
            pass
        self.root.after(250, self._refresh_readout)

    def _serve(self):
        try:
            while True:
                self.requests.get_nowait()
                if self.center is not None:
                    self._fire(*self.center)
        except Exception:
            pass
        self.root.after(30, self._serve)

    def _earth_active(self):
        fg = self.user32.GetForegroundWindow()
        return bool(self.earth_hwnd) and bool(fg) and self._exe_of(fg) == self._exe_of(self.earth_hwnd)

    def _click(self, x, y):
        old = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(old))
        steps = 12
        for i in range(1, steps + 1):          # glide onto the target like a real mouse
            self.user32.SetCursorPos(int(old.x + (x - old.x) * i / steps), int(old.y + (y - old.y) * i / steps))
            time.sleep(0.01)
        time.sleep(HOVER_BEFORE_S)
        self.user32.mouse_event(0x0002, 0, 0, 0, 0)    # left down
        time.sleep(PRESS_S)
        self.user32.mouse_event(0x0004, 0, 0, 0, 0)    # left up
        time.sleep(HOVER_AFTER_S)
        self.user32.SetCursorPos(old.x, old.y)

    def _fire(self, x, y):
        self.overlay.withdraw()                         # crosshair out of the way
        self.root.update()
        try:
            if not self._earth_active():
                self._click(x, y)                       # first click makes ArcGIS Earth active
                time.sleep(ACTIVATE_PAUSE_S)            # longer than a double-click
            self._click(x, y)
        finally:
            self.overlay.deiconify()
            self.overlay.attributes("-topmost", True)


_GATE_DROPPER = None


def gate_dropper_module():
    """1.3.6: load gate_dropper.py from beside this file (once)."""
    global _GATE_DROPPER
    if _GATE_DROPPER is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gate_dropper", Path(__file__).resolve().with_name("gate_dropper.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _GATE_DROPPER = mod
    return _GATE_DROPPER


def _drop_number(f):
    """1.3.9: Dropped_Gate_NN.kmz -> NN, so undo picks the real newest (100 after 99); other names sort first."""
    import re
    m = re.fullmatch(r"Dropped_Gate_(\d+)\.kmz", f.name)
    return (1, int(m.group(1)), f.name) if m else (0, 0, f.name)


class GateDropper:
    """1.3.6: the drop button (Button 1 since 1.3.10) marks a place; the second mark writes a gate pair (gate_dropper.py)."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.mark = None
        self.layers = {}          # TEST4: dropped file name -> ArcGIS Earth layer id (this session)
        self.down_at = None
        self.undo_fired = False
        self.last_press = -1e9

    def update(self, down, now):
        """TEST4: 'press' when a short press is let go, 'undo' once when held DROP_UNDO_HOLD_S, else None."""
        if down:
            if self.down_at is None:
                self.down_at, self.undo_fired = now, False
            elif not self.undo_fired and now - self.down_at >= DROP_UNDO_HOLD_S:
                self.undo_fired = True
                return "undo"
            return None
        if self.down_at is None:
            return None
        held_undo, self.down_at = self.undo_fired, None
        if held_undo or now - self.last_press < CLICK_LOCKOUT_S:
            return None
        self.last_press = now
        return "press"

    def undo(self):
        """TEST4: clear mark 1, or delete the newest dropped gate file. Returns (message, deleted_name_or_None)."""
        if self.mark is not None:
            self.mark = None
            return "MARK 1 CLEARED", None
        gd = gate_dropper_module()
        files = sorted(self.folder.glob(gd.DROP_FILE_PREFIX + "*.kmz"), key=_drop_number)   # 1.3.9: by number
        files = [f for f in files if _drop_number(f)[0]]                  # 1.3.9: only Dropped_Gate_NN.kmz files
        if not files:
            return "NOTHING TO UNDO", None
        last = files[-1]
        last.unlink()
        layer = self.layers.pop(last.name, None)
        if layer is not None:
            try:
                http_json("DELETE", BASE_URL + f"/arcgisearth/layer/{layer}")
            except EarthAPIError:
                pass
        return f"UNDONE · {last.stem}", last.name

    def press(self, cam):
        """Handle one drop-button press at camera cam. Returns (message, written_path_or_None)."""
        gd = gate_dropper_module()
        here = (float(cam["position"]["y"]), float(cam["position"]["x"]), float(cam["position"]["z"]),
                float(cam.get("heading", 0.0)))           # TEST2: the gate faces the way you are looking
        ft = round(here[2] / gd.FT / 10) * 10
        if self.mark is None:
            self.mark = here
            return f"MARK 1 SAVED · {ft:,} ft", None
        apart = gd.distance_m(self.mark[0], self.mark[1], here[0], here[1])
        if apart < gd.min_apart_m():
            self.mark = None
            return "MARK 1 CLEARED", None
        path = gd.drop_pair(self.folder, self.mark, here)
        self.mark = None
        return f"GATES DROPPED · {path.stem}", path


def add_layer_to_map(path):
    """1.3.6: ask ArcGIS Earth to show a KMZ (Automation API add layer). Returns the layer id
    ArcGIS Earth gives back ("" if it gave none), or None if it refused."""
    try:
        reply = http_json("POST", BASE_URL + "/arcgisearth/layer",
                          {"URI": str(Path(path).resolve()), "target": "operationalLayers", "type": "KML"})
        return str(reply.get("id", "")) if isinstance(reply, dict) else ""
    except EarthAPIError:
        return None


# ---------------------------------------------------------------------------
# Wormholes (1.3). A gate is a vertical ring: centre (lat, lon, alt_m absolute),
# radius_m, and facing = compass direction a pilot flies to go through it.

_KML_NS = "{http://www.opengis.net/kml/2.2}"


def _gate_from_placemark(pm):
    data = {}
    for d in pm.iter(_KML_NS + "Data"):
        v = d.find(_KML_NS + "value")
        data[(d.get("name") or "").strip().lower()] = (v.text or "").strip() if v is not None else ""
    if data.get("gate", "").lower() not in ("1", "yes", "true"):
        return None
    name_el = pm.find(_KML_NS + "name")
    gate = {"name": (name_el.text or "").strip() if name_el is not None else ""}
    for k in ("lat", "lon", "alt_m", "radius_m", "facing"):
        gate[k] = float(data[k])
    gate["to"] = data.get("to", "")
    for k in ("lock_capture_m", "lock_range_m"):      # 1.3.6 TEST5: a gate's own grab zone (optional)
        if data.get(k, "") != "":
            gate[k] = float(data[k])
    if not gate["to"]:
        for k in ("dest_lat", "dest_lon", "dest_alt_m", "dest_heading"):
            gate[k] = float(data[k])
    for k, v in gate.items():
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError(f"gate {gate['name']!r}: {k} is not a number")
    if not (-90 <= gate["lat"] <= 90 and -180 <= gate["lon"] <= 180 and gate["radius_m"] > 0):
        raise ValueError(f"gate {gate['name']!r}: bad position or radius")
    return gate


def load_gates(folder):
    """Read every gate in *.kmz / *.kml in folder. Returns (gates, problems)."""
    gates, problems = [], []
    folder = Path(folder)
    if not folder.is_dir():
        return gates, problems
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in (".kmz", ".kml"):
            continue
        try:
            if f.suffix.lower() == ".kmz":
                with zipfile.ZipFile(f) as z:
                    name = next((n for n in z.namelist() if n.lower().endswith(".kml")), None)
                    if name is None:
                        raise ValueError("no KML inside")
                    root = ET.fromstring(z.read(name))
            else:
                root = ET.parse(f).getroot()
            for pm in root.iter(_KML_NS + "Placemark"):
                try:
                    g = _gate_from_placemark(pm)
                except (KeyError, ValueError) as exc:
                    problems.append(f"{f.name}: {exc}")
                    continue
                if g is not None:
                    g["file"] = f.name
                    gates.append(g)
        except Exception as exc:
            problems.append(f"{f.name}: {exc}")
    kept = []
    for g in gates:
        if g["to"]:
            same = [p for p in gates if p is not g and p["file"] == g["file"] and p["name"] == g["to"]]
            other = [p for p in gates if p["file"] != g["file"] and p["name"] == g["to"]]
            if len(same) == 1:
                g["partner"] = same[0]
            elif not same and len(other) == 1:
                g["partner"] = other[0]
            else:
                where = "is not in the Gates folder" if not (same or other) else "matches more than one gate"
                problems.append(f"{g['file']}: gate {g['name']!r} leads to {g['to']!r}, which {where}")
                continue
        kept.append(g)
    return kept, problems


def _local_xyz(lat0, lon0, lat, lon, alt):
    k = math.pi / 180.0 * EARTH_RADIUS_M
    return ((lon - lon0) * k * math.cos(math.radians(lat0)), (lat - lat0) * k, alt)


def gate_crossed(gate, p0, p1):
    """True if the move p0 -> p1 ((lon, lat, alt) each) passes forwards through the ring."""
    a = _local_xyz(gate["lat"], gate["lon"], p0[1], p0[0], p0[2] - gate["alt_m"])
    b = _local_xyz(gate["lat"], gate["lon"], p1[1], p1[0], p1[2] - gate["alt_m"])
    if math.hypot(a[0], a[1]) > GATE_MAX_RANGE_M:
        return False
    f = math.radians(gate["facing"])
    n = (math.sin(f), math.cos(f), 0.0)
    d0 = a[0] * n[0] + a[1] * n[1]
    d1 = b[0] * n[0] + b[1] * n[1]
    if not (d0 < 0.0 <= d1):          # forwards only
        return False
    s = d0 / (d0 - d1)
    q = [a[i] + s * (b[i] - a[i]) for i in range(3)]
    return math.sqrt(q[0] ** 2 + q[1] ** 2 + q[2] ** 2) <= gate["radius_m"]


def gate_arrival(gate, gates):
    """(lon, lat, alt_m, heading) where a jump through gate lands."""
    if gate["to"]:
        p = gate.get("partner") or next(g for g in gates if g["name"] == gate["to"])
        heading = (p["facing"] + 180.0) % 360.0      # away from the partner ring
        lon, lat = move_lonlat(p["lon"], p["lat"], heading, GATE_EXIT_M, 0.0)
        return lon, lat, p["alt_m"], heading
    return gate["dest_lon"], gate["dest_lat"], gate["dest_alt_m"], gate["dest_heading"] % 360.0


def gate_label(gate):
    return gate["name"]


_INSTANCE = None


def single_instance(name="Local\\EarthStick_single_instance"):
    """1.3.9: True if this is the only EarthStick running (holds a Windows named mutex for the program's
    life). Anything unexpected = True, so EarthStick never refuses to fly because of this check."""
    global _INSTANCE
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateMutexW.restype = wintypes.HANDLE
        k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        h = k32.CreateMutexW(None, False, name)
        if not h:
            return True
        if ctypes.get_last_error() == 183:          # ERROR_ALREADY_EXISTS
            return False
        _INSTANCE = h
        return True
    except Exception:
        return True


def run():
    print(f"EarthStick {VERSION}")
    print("Minimal T.A320 Pilot -> ArcGIS Earth bridge")
    print("Button 4 = descend/zoom in; Button 3 = climb/zoom out; neutral = hover.")
    print(f"Button {TRIGGER_BUTTON} = click the object under the crosshair.")
    print(f"Button {DROP_BUTTON} (trigger) = Gate Dropper (hold 2 s = undo): press at one place, then at another - a gate pair appears there.")
    print()

    if os.name != "nt":
        raise RuntimeError("EarthStick requires Windows")
    if not single_instance():
        print("EarthStick is already running in another window - use that one.")
        print("(Only one EarthStick can fly the camera at a time. You can close this window.)")
        return

    # Same retry used after a mid-flight unplug, so EarthStick can be started
    # before the joystick is plugged in.
    try:
        joy = WinJoystick()
    except RuntimeError as exc:
        print(f"Joystick not ready: {exc}")
        print("Waiting for the joystick - plug it in or check joy.cpl. Ctrl+C to stop.")
        joy = wait_for_joystick_reconnect()
    print(f"Joystick: {joy.caps.szPname}  (Windows ID {joy.id})")
    print(f"Slider0 source: WinMM {joy.slider_name} axis")
    print(f"Waiting for ArcGIS Earth Automation API at {BASE_URL} ...")

    cam = None
    last_reason = None
    while cam is None:
        try:
            cam = get_camera()
        except EarthAPIError as exc:
            reason = str(exc)
            if reason != last_reason:
                print(f"  Still waiting: {reason}")
                print("  Check that ArcGIS Earth is open with its Automation API switched on: "
                      "Settings > Advanced application settings > tick 'Enable Automation API'.")
                last_reason = reason
            time.sleep(1.0)
    print("ArcGIS Earth: connected")
    clicker = TriggerClick.start()
    here = Path(__file__).resolve().parent
    top = here.parent if here.name == "System Files" else here   # 1.3.5
    gates, gate_problems = load_gates(top / GATES_FOLDER)
    for msg in gate_problems:
        print(f"Wormholes: skipped - {msg}")
    if gates:
        print(f"Wormholes: {len(gates)} gate(s) armed: " + ", ".join(gate_label(g) for g in gates))
    else:
        print(f"Wormholes: none (put gate files in the {GATES_FOLDER} folder in the EarthStick folder)")
    last_jump = -1e9
    dropper = GateDropper(top / GATES_FOLDER)
    print("Close this window or press Ctrl+C to stop EarthStick.\n")

    dt_target = 1.0 / POLL_HZ
    last_t = time.perf_counter()
    last_idle_sync = time.perf_counter()
    was_active = False
    last_status = 0.0
    api_fault = False

    while True:
        loop_start = time.perf_counter()

        # After any API fault, do not send another camera write until a fresh
        # camera has been read from ArcGIS Earth. This prevents stale local
        # movement from accumulating while Earth/API communication is down.
        if api_fault:
            try:
                cam = get_camera()
            except EarthAPIError:
                time.sleep(0.25)
                continue

            api_fault = False
            last_t = time.perf_counter()
            last_idle_sync = last_t
            was_active = False
            sys.stdout.write("\nArcGIS Earth: reconnected; camera re-synchronized.\n")
            sys.stdout.flush()
            continue

        dt = clamp(loop_start - last_t, 0.001, 0.10)
        last_t = loop_start

        try:
            state = joy.read()
        except RuntimeError as exc:
            sys.stdout.write(f"\nJoystick connection lost: {exc}\nWaiting for joystick to reconnect...\n")
            sys.stdout.flush()

            joy = wait_for_joystick_reconnect()
            sys.stdout.write(
                f"Joystick: reconnected as {joy.caps.szPname}  "
                f"(Windows ID {joy.id}); Slider0 source: WinMM {joy.slider_name} axis\n"
            )
            sys.stdout.flush()

            # Re-read the live ArcGIS Earth camera before accepting any new
            # joystick movement. If the API is also unavailable, the
            # API recovery path takes ownership of the wait.
            try:
                cam = get_camera()
            except EarthAPIError:
                api_fault = True
                sys.stdout.write(
                    "ArcGIS Earth connection unavailable after joystick reconnect. "
                    "Waiting to re-synchronize...\n"
                )
                sys.stdout.flush()

            last_t = time.perf_counter()
            last_idle_sync = last_t
            was_active = False
            continue

        if clicker is not None:
            clicker.on_buttons(state["buttons"])

        # 1.3.6: Gate Dropper (DROP_BUTTON: Button 1 since 1.3.10)
        drop_action = dropper.update(bool(state["buttons"] & (1 << (DROP_BUTTON - 1))), loop_start)
        if drop_action == "undo":                          # TEST4: hold the drop button = undo
            try:
                msg, removed = dropper.undo()
                if removed is not None:
                    gates, gate_problems = load_gates(top / GATES_FOLDER)
                    sys.stdout.write(f"\nGate Dropper: {removed} deleted and disarmed ({len(gates)} gates armed).\n")
                else:
                    sys.stdout.write(f"\nGate Dropper: {msg}\n")
            except Exception as exc:
                msg = "UNDO FAILED"
                sys.stdout.write(f"\nGate Dropper: could not undo ({exc}).\n")
            sys.stdout.flush()
            if clicker is not None:
                clicker.notice = (msg, time.perf_counter() + NOTICE_S)
        if drop_action == "press":
            try:
                try:
                    here_cam = get_camera()
                except EarthAPIError:
                    here_cam = cam
                msg, written = dropper.press(here_cam)
                if written is not None:
                    gates, gate_problems = load_gates(top / GATES_FOLDER)
                    for p_msg in gate_problems:
                        sys.stdout.write(f"\nWormholes: skipped - {p_msg}")
                    last_jump = loop_start                 # never jump through the gate you are sitting in
                    layer = add_layer_to_map(written) if DROP_ADD_TO_MAP else None
                    if layer:
                        dropper.layers[written.name] = layer
                    shown = layer is not None
                    msg_more = (" - shown on the map" if shown else
                                f" - drag {written.name} from the Gates folder onto ArcGIS Earth to see it")
                    sys.stdout.write(f"\nGate Dropper: {written.name} written and armed ({len(gates)} gates armed){msg_more}.\n")
                else:
                    sys.stdout.write(f"\nGate Dropper: {msg}\n")
            except Exception as exc:
                msg = "GATE DROP FAILED"
                sys.stdout.write(f"\nGate Dropper: could not write the gates ({exc}).\n")
            sys.stdout.flush()
            if clicker is not None:
                clicker.notice = (msg, time.perf_counter() + NOTICE_S)

        # Button 4 (red trigger) = zoom in.
        # Button 3 (black thumb) = zoom out.
        zoom_in = bool(state["buttons"] & (1 << (4 - 1)))
        zoom_out = bool(state["buttons"] & (1 << (3 - 1)))
        zoom_dir = (1 if zoom_out else 0) - (1 if zoom_in else 0)

        active = (
            any(abs(state[k]) > 0.0 for k in ("strafe", "forward", "yaw", "tilt"))
            or zoom_dir != 0
        )

        # Re-sync from Earth when the user first moves the stick, so mouse navigation
        # performed while idle is respected.
        if active and not was_active:
            try:
                cam = get_camera()
            except EarthAPIError:
                api_fault = True
                sys.stdout.write("\nArcGIS Earth connection lost. Holding position; waiting to re-synchronize...\n")
                sys.stdout.flush()
                time.sleep(0.25)
                continue

        if active:
            # Work on a temporary camera. The confirmed local camera is updated
            # only after ArcGIS Earth accepts the PUT.
            next_cam = {
                "position": dict(cam["position"]),
                "heading": cam["heading"],
                "tilt": cam["tilt"],
                "roll": cam["roll"],
            }
            pos = next_cam["position"]

            # Continuous altitude-only zoom.
            # Zoom rate scales with current altitude: roughly 75% of current
            # altitude per second while held, with a 2 m/s floor near ground.
            if zoom_dir != 0:
                zoom_rate_mps = max(2.0, float(pos["z"]) * 0.75)
                pos["z"] = max(1.0, float(pos["z"]) + zoom_dir * zoom_rate_mps * dt)

            speed = speed_from_throttle(state["throttle"], pos["z"])

            # Translation uses current heading.
            travel = speed * dt
            lon, lat = move_lonlat(
                pos["x"], pos["y"], next_cam["heading"],
                state["forward"] * travel,
                state["strafe"] * travel,
            )
            pos["x"] = lon
            pos["y"] = lat

            next_cam["heading"] = (next_cam["heading"] + state["yaw"] * YAW_RATE_DPS * dt) % 360.0
            next_cam["tilt"] = clamp(next_cam["tilt"] + state["tilt"] * TILT_RATE_DPS * dt, 0.0, 180.0)

            tractor_on, _ = tractor_pull(next_cam, gates, dt, max(state["forward"], 0.0) * travel, zoom_dir)

            jumped = None
            if gates and loop_start - last_jump >= GATE_COOLDOWN_S:
                p0 = (float(cam["position"]["x"]), float(cam["position"]["y"]), float(cam["position"]["z"]))
                p1 = (float(pos["x"]), float(pos["y"]), float(pos["z"]))
                for g in gates:
                    if gate_crossed(g, p0, p1):
                        lon, lat, alt, heading = gate_arrival(g, gates)
                        pos["x"], pos["y"], pos["z"] = lon, lat, alt
                        next_cam["heading"] = heading
                        jumped = g
                        break

            try:
                put_camera(next_cam)
            except EarthAPIError:
                api_fault = True
                sys.stdout.write("\nArcGIS Earth connection lost. Holding position; waiting to re-synchronize...\n")
                sys.stdout.flush()
                time.sleep(0.25)
                continue

            cam = next_cam
            if jumped is not None:
                last_jump = loop_start
                sys.stdout.write(f"\nWormhole: through the {jumped['name']} gate.\n")
                sys.stdout.flush()
        else:
            speed = speed_from_throttle(state["throttle"], cam["position"]["z"])
            # TEST6: the tractor beam also works while hovering near a ring
            tractor_on = False
            if TRACTOR_BEAM and gates:
                probe = {"position": dict(cam["position"]), "heading": cam["heading"], "tilt": cam["tilt"], "roll": cam["roll"]}
                tractor_on, moved = tractor_pull(probe, gates, dt, 0.0, zoom_dir)
                if moved:
                    try:
                        # 1.3.9: start from where ArcGIS Earth is NOW (the mouse may have moved the map),
                        # change only the height, so two-handed mouse moves are never pulled back
                        held = get_camera()
                        tractor_on, moved = tractor_pull(held, gates, dt, 0.0, zoom_dir)
                        if moved:
                            put_camera(held)
                        cam = held
                        last_idle_sync = loop_start
                    except EarthAPIError:
                        api_fault = True
                        sys.stdout.write("\nArcGIS Earth connection lost. Holding position; waiting to re-synchronize...\n")
                        sys.stdout.flush()
                        time.sleep(0.25)
                        continue
            if loop_start - last_idle_sync >= IDLE_RESYNC_SECONDS:
                try:
                    cam = get_camera()
                except EarthAPIError:
                    api_fault = True
                    sys.stdout.write("\nArcGIS Earth connection lost. Holding position; waiting to re-synchronize...\n")
                    sys.stdout.flush()
                    time.sleep(0.25)
                    continue
                last_idle_sync = loop_start

        if loop_start - last_status >= 0.10:
            print_status(joy.caps.szPname, state, cam, speed, active)
            last_status = loop_start
            if clicker is not None and SHOW_READOUT:
                try:
                    clicker.readout = readout_text(cam, getattr(clicker, "view_px", 1920))
                    clicker.ring_light = RING_LIGHT and ring_light_on(cam, gates)
                    clicker.tractor = bool(tractor_on)
                    if tractor_on:                      # TEST5: count down the distance to the gate
                        _g, _d = ring_ahead_with_distance(cam, gates)
                        clicker.tractor_text = TRACTOR_TEXT + (f" \u00b7 {round(_d / 0.3048 / 10) * 10:,.0f} ft" if _d is not None else "")
                except Exception:
                    pass

        was_active = active
        elapsed = time.perf_counter() - loop_start
        if elapsed < dt_target:
            time.sleep(dt_target - elapsed)


def selftest():
    # Deadzone
    assert deadzone(0.0) == 0.0
    assert deadzone(0.05) == 0.0
    assert deadzone(1.0) == 1.0
    assert deadzone(-1.0) == -1.0

    # Normalization
    assert abs(norm_centered(0, 0, 100) + 1.0) < 1e-9
    assert abs(norm_centered(50, 0, 100)) < 1e-9
    assert abs(norm_centered(100, 0, 100) - 1.0) < 1e-9

    # Heading-relative movement sanity checks.
    lon, lat = move_lonlat(-81.65, 30.33, 0.0, 1000.0, 0.0)
    assert lat > 30.33 and abs(lon + 81.65) < 1e-6
    lon, lat = move_lonlat(-81.65, 30.33, 90.0, 1000.0, 0.0)
    assert lon > -81.65 and abs(lat - 30.33) < 1e-6
    lon, lat = move_lonlat(-81.65, 30.33, 0.0, 0.0, 1000.0)
    assert lon > -81.65 and abs(lat - 30.33) < 1e-6

    assert 0.5 <= speed_from_throttle(0.0, 3000.0) < speed_from_throttle(1.0, 3000.0)

    # Camera response validation for API fault isolation.
    original_http_json = globals()["http_json"]
    try:
        globals()["http_json"] = lambda method, url, body=None: {
            "position": {
                "x": -81.65,
                "y": 30.33,
                "z": 1000.0,
                "spatialReference": {"wkid": 4326},
            },
            "heading": 90.0,
            "tilt": 45.0,
            "roll": 0.0,
        }
        cam = get_camera()
        assert cam["position"]["x"] == -81.65

        globals()["http_json"] = lambda method, url, body=None: {
            "position": {"x": "bad", "y": 30.33, "z": 1000.0}
        }
        try:
            get_camera()
            raise AssertionError("Malformed camera response was not rejected")
        except EarthAPIError:
            pass
    finally:
        globals()["http_json"] = original_http_json

    # Simulate two failed joystick detection attempts followed by a
    # successful reconnect without sleeping.
    attempts = {"count": 0}
    marker = object()

    def fake_factory():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("simulated joystick missing")
        return marker

    slept = []
    reconnected = wait_for_joystick_reconnect(fake_factory, slept.append)
    assert reconnected is marker
    assert attempts["count"] == 3
    assert slept == [1.0, 1.0]

    # Trigger-click (1.2)
    assert window_center((0, 0, 1200, 2000)) == (600, 1000)
    assert window_center((100, 50, 1300, 2050), 5, -10) == (705, 1040)
    assert is_earth_exe(r"C:\Program Files\ArcGIS\Earth\ArcGISEarth.exe")
    assert not is_earth_exe(r"C:\Windows\explorer.exe") and not is_earth_exe("")
    g = TriggerGate(0.8)
    # press, hold, release, press too soon, release, press later
    assert [g.update(d, t) for d, t in ((True, 0.0), (True, 0.1), (False, 0.2), (True, 0.5),
                                         (False, 0.6), (True, 1.0))] == [True, False, False, False, False, True]
    assert TRIGGER_BUTTON not in (3, 4) and DROP_BUTTON not in (3, 4) and TRIGGER_BUTTON != DROP_BUTTON
    assert ACTIVATE_PAUSE_S > 0.5 and CLICK_LOCKOUT_S > ACTIVATE_PAUSE_S

    # Wormholes (1.3): a ring facing north over (30.0, -81.0) at 500 m, radius 150 m.
    g = {"name": "A", "lat": 30.0, "lon": -81.0, "alt_m": 500.0, "radius_m": 150.0, "facing": 0.0, "to": "B"}
    b = {"name": "B", "lat": 40.0, "lon": -74.0, "alt_m": 400.0, "radius_m": 150.0, "facing": 210.0, "to": "A"}
    south, north = move_lonlat(-81.0, 30.0, 180.0, 50.0, 0.0), move_lonlat(-81.0, 30.0, 0.0, 50.0, 0.0)
    assert gate_crossed(g, (*south, 520.0), (*north, 520.0))                 # through the ring, forwards
    assert not gate_crossed(g, (*north, 520.0), (*south, 520.0))             # backwards: no jump
    assert not gate_crossed(g, (*south, 900.0), (*north, 900.0))             # above the ring
    east = move_lonlat(-81.0, 30.0, 90.0, 400.0, 0.0)
    assert not gate_crossed(g, (east[0], south[1], 500.0), (east[0], north[1], 500.0))  # beside it
    lon, lat, alt, hd = gate_arrival(g, [g, b])
    assert abs(hd - 30.0) < 1e-9 and alt == 400.0 and lat > 40.0              # past B, facing away
    assert not gate_crossed(b, (-74.0, 40.0, 400.0), (lon, lat, 400.0))      # leaving B does not trigger B
    one = dict(g, to="", dest_lat=1.0, dest_lon=2.0, dest_alt_m=3.0, dest_heading=370.0)
    assert gate_arrival(one, [one]) == (2.0, 1.0, 3.0, 10.0)

    # Ring-height light (1.3.4): the ATL hub - 8 rings on a 3 km circle facing outward, 771 m, radius 225
    hub = []
    for i, brg in enumerate((315, 0, 45, 90, 135, 180, 225, 270)):
        la, lo = 33.6407 + 3000 * math.cos(math.radians(brg)) / 111195.0, \
                 -84.4277 + 3000 * math.sin(math.radians(brg)) / (111195.0 * math.cos(math.radians(33.6407)))
        hub.append({"name": f"g{brg}", "lat": la, "lon": lo, "alt_m": 771.0, "radius_m": 225.0, "facing": float(brg)})
    def at(h, z=771.0, lat=33.6407, lon=-84.4277):
        return {"position": {"x": lon, "y": lat, "z": z}, "heading": h, "tilt": 85.0, "roll": 0.0}
    assert ring_ahead(at(0.0), hub)["name"] == "g0"                  # facing London
    assert ring_ahead(at(44.0), hub)["name"] == "g45"                # turned to Paris
    assert ring_ahead(at(22.5), hub) is None                          # arrival heading: between two rings
    assert ring_light_on(at(0.0, 771.0 + 100), hub)                   # 100 m high: still green (half radius = 112 m)
    assert not ring_light_on(at(0.0, 771.0 + 130), hub)               # 130 m high: off
    assert ring_ahead(at(180.0, 771.0, lat=33.6407 + 3200 / 111195.0), hub)["name"] == "g180"   # past London looking back: its red side is ignored, Rio's gold side ahead counts
    assert ring_ahead(at(180.0, 771.0, lat=33.6407 + 9500 / 111195.0), hub) is None   # 6.5 km north: London's red side ahead, Rio beyond 10 km
    assert not ring_light_on(at(0.0), [])                             # no gates: never on
    # Tractor beam (TEST6): 1,000 m short of London, 150 m low
    near = 33.6407 + 2000 / 111195.0
    c = at(0.0, 771.0 - 150.0, lat=near)
    assert tractor_pull(c, hub, 1.0, 0.0, 0) == (True, True) and abs(c["position"]["z"] - (771.0 - 75.0)) < 0.5   # hovering: half the gap in 1 s
    c = at(0.0, 771.0 - 150.0, lat=near)
    assert tractor_pull(c, hub, 0.1, 500.0, 0)[1] and abs(c["position"]["z"] - (771.0 - 75.0)) < 0.5            # 500 m of 1,000 m flown: half the gap (glide path)
    c = at(0.0, 771.0 - 150.0, lat=near)
    assert tractor_pull(c, hub, 1.0, 0.0, -1) == (False, False) and c["position"]["z"] == 771.0 - 150.0         # descend button: lets go
    assert tractor_pull(at(0.0, 771.0 - 300.0, lat=near), hub, 1.0, 0.0, 0) == (False, False)                   # 300 m low: outside capture
    assert tractor_pull(at(0.0, 771.0 - 150.0), hub, 1.0, 0.0, 0) == (False, False)                             # 3 km out: too far
    assert tractor_pull(at(30.0, 771.0 - 150.0, lat=near), hub, 1.0, 0.0, 0) == (False, False)                  # turned away
    assert tractor_pull(at(0.0, 771.1, lat=near), hub, 1.0, 0.0, 0) == (True, False)                            # on height: holding, nothing sent
    c = at(0.0, 771.0 - 150.0, lat=near)
    for _ in range(60):
        tractor_pull(c, hub, 0.1, 0.0, 0)
    assert abs(c["position"]["z"] - 771.0) < 3.0                                                         # 6 s hovering: within 3 m

    # 1.3.6: Gate Dropper - mark, clear, drop, armed, flyable
    import tempfile
    folder = Path(tempfile.mkdtemp(prefix="es_drop_"))
    d = GateDropper(folder)
    def cam_at(lat, lon, z):
        return {"position": {"x": lon, "y": lat, "z": z}, "heading": 0.0, "tilt": 80.0, "roll": 0.0}
    assert d.press(cam_at(30.0, -80.0, 152.4))[1] is None and d.mark is not None            # mark 1
    assert d.press(cam_at(30.001, -80.0, 160.0)) == ("MARK 1 CLEARED", None) and d.mark is None   # close by: clears
    d.press(cam_at(30.0, -80.0, 152.4))
    msg, path = d.press(cam_at(30.0, -79.0, 300.0))                                          # 1 degree east
    assert path is not None and path.name == "Dropped_Gate_01.kmz" and msg.startswith("GATES DROPPED")
    dropped, problems = load_gates(folder)
    assert not problems and len(dropped) == 2
    ga = next(g for g in dropped if g["name"] == "Drop 01 B")                                 # the gate at mark 1 leads to B
    gd = gate_dropper_module()
    alat, alon = gd.dest(30.0, -80.0, 0.0, gd.DROP_AHEAD_M)                                   # TEST3: 500 m in front of mark 1
    assert abs(ga["lat"] - alat) < 1e-6 and abs(ga["lon"] - alon) < 1e-6 and abs(ga["alt_m"] - 152.4) < 0.01
    assert abs(ga["facing"] - 0.0) < 1e-6                                                     # TEST2: faces the way you looked (north)
    assert not gate_crossed(ga, (-80.0, 29.999, 152.4), (-80.0, 30.001, 152.4))               # not where you pressed...
    assert gate_crossed(ga, (-80.0, 30.001, 152.4), (-80.0, 30.010, 152.4))                   # ...but 500 m ahead: push forward
    lon, lat, alt, hd = gate_arrival(ga, dropped)
    blat, blon = gd.dest(30.0, -79.0, 0.0, gd.DROP_AHEAD_M + 300.0)
    assert abs(lon - blon) < 1e-5 and abs(lat - blat) < 1e-5 and abs(alt - 300.0) < 0.01 and hd == 0.0   # 300 m past gate B, looking north
    d.press(cam_at(30.0, -79.0, 300.0)); assert d.press(cam_at(30.0, -78.0, 300.0))[1].name == "Dropped_Gate_02.kmz"
    # TEST5: dropped gates carry their own wide grab zone (3 km, +-2,000 ft); other gates keep 1.5 km / 1 radius
    assert abs(ga["lock_capture_m"] - 609.6) < 0.01 and ga["lock_range_m"] == 3000.0 and ga["radius_m"] == 300.0
    def behind(g, dist_m, dz):
        lon, lat = move_lonlat(g["lon"], g["lat"], g["facing"], -dist_m, 0.0)
        return {"position": {"x": lon, "y": lat, "z": g["alt_m"] + dz}, "heading": g["facing"], "tilt": 80.0, "roll": 0.0}
    assert tractor_pull(behind(ga, 2800.0, 580.0), [ga], 0.1, 0.0, 0)[0]                    # 2.8 km out, 1,900 ft high: grabbed
    assert not tractor_pull(behind(ga, 3200.0, 0.0), [ga], 0.1, 0.0, 0)[0]                 # 3.2 km out: not yet
    assert not tractor_pull(behind(ga, 1000.0, 640.0), [ga], 0.1, 0.0, 0)[0]                # 2,100 ft high: not grabbed
    plain = {k: v for k, v in ga.items() if k not in ("lock_capture_m", "lock_range_m")}
    assert not tractor_pull(behind(plain, 2800.0, 0.0), [plain], 0.1, 0.0, 0)[0]            # a normal gate: 1.5 km as before
    assert not tractor_pull(behind(plain, 1000.0, 310.0), [plain], 0.1, 0.0, 0)[0]          # ...and 1 radius (300 m) as before

    # TEST4: hold = undo (newest file first, number reused), short press acts on release
    assert d.undo() == ("UNDONE · Dropped_Gate_02", "Dropped_Gate_02.kmz") and not (folder / "Dropped_Gate_02.kmz").exists()
    d.press(cam_at(30.0, -79.0, 300.0)); assert d.undo() == ("MARK 1 CLEARED", None) and (folder / "Dropped_Gate_01.kmz").exists()
    assert d.undo()[1] == "Dropped_Gate_01.kmz" and d.undo() == ("NOTHING TO UNDO", None)
    d.press(cam_at(30.0, -80.0, 152.4)); assert d.press(cam_at(30.0, -79.0, 300.0))[1].name == "Dropped_Gate_01.kmz"
    b = GateDropper(folder)
    assert [b.update(x, t) for x, t in ((True, 0.0), (True, 0.5), (False, 0.6))] == [None, None, "press"]       # short press
    assert [b.update(x, t) for x, t in ((True, 1.0), (True, 2.9), (True, 3.1), (True, 5.0), (False, 5.1))] == [None, None, "undo", None, None]  # hold
    assert [b.update(x, t) for x, t in ((True, 6.0), (False, 6.1), (True, 6.2), (False, 6.3))] == [None, "press", None, None]   # bounce ignored

    # 1.3.9: undo goes by number; other files in the folder are never chosen over a numbered gate
    order = sorted((Path(n) for n in ("Dropped_Gate_99.kmz", "Dropped_Gate_100.kmz", "Dropped_Gate_02 (1).kmz")), key=_drop_number)
    assert order[-1].name == "Dropped_Gate_100.kmz"
    if os.name != "nt":
        assert single_instance()                      # not Windows: the check stays out of the way

    print("EarthStick self-test PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit(0)
    try:
        run()
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as exc:
        # EarthStick.bat pauses after this, so no second prompt here.
        print(f"\nEarthStick stopped: {exc}")
