"""P25 GPS Tracker - on-screen overlay (Claude + Jim, 2026-11-12, v0.8).

A small click-through badge pinned to the bottom-right of the ArcGIS Earth window
(above the Esri logo). It is on screen the whole time the tracker is running, so if
it disappears the operator knows the program stopped. While tracking, if the radio
drops, a red "RADIO DISCONNECTED" alarm blinks just above the badge.

It finds the ArcGIS Earth window by its visible TITLE only (GetWindowText). It does
not open or inspect any other process - v0.7 read each window's program file, which a
virus scanner's machine-learning flagged as "process discovery" (a false positive);
reading only the caption text is the ordinary way a taskbar or alt-tab tool works.

A borderless, always-on-top, click-through Tk window (the same technique as
EarthStick's readout). Windows only; needs ctypes and marker.png. ANY failure
disables just the badge - the tracker itself is never affected.
"""
import ctypes
from ctypes import wintypes
from pathlib import Path

import tkinter as tk

EARTH_TITLE = "arcgis earth"    # matched (lower-cased) against each window's caption text
KEY        = "#010203"          # transparent-colour key (nothing else uses this exact colour)
RIGHT_GAP  = 28                 # px in from the right edge of the ArcGIS Earth window
BOTTOM_GAP = 90                 # px up from the bottom (clear of the scale bar / Esri logo)
BADGE_W, BADGE_H = 360, 120


class StatusOverlay:
    """Lives on the app's own Tk root. start() once; then set_radio(ok) and
    set_tracking(on) as state changes. The badge shows whenever ArcGIS Earth is
    on screen; the alarm shows only while tracking AND the radio is down."""

    def __init__(self, root, icon_path):
        self.root = root
        self.icon_path = Path(icon_path)
        self.win = self.canvas = self.img = None
        self.ok = False
        self.radio_ok = True
        self.tracking = False
        self._blink = False
        try:
            self.user32 = ctypes.WinDLL("user32")
        except Exception:
            self.user32 = None

    # ---- lifecycle ----
    def start(self):
        if self.user32 is None:
            return False
        try:
            self._build()
            self.ok = True
            self.root.after(100, self._track)
            self.root.after(600, self._blinker)
            return True
        except Exception:
            self.ok = False
            return False

    def destroy(self):
        try:
            if self.win is not None:
                self.win.destroy()
        except Exception:
            pass

    # ---- state the app feeds in ----
    def set_radio(self, ok):
        self.radio_ok = bool(ok)

    def set_tracking(self, on):
        self.tracking = bool(on)

    # ---- build the click-through badge ----
    def _build(self):
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=KEY)
        try:
            w.attributes("-transparentcolor", KEY)
        except Exception:
            pass
        c = tk.Canvas(w, width=BADGE_W, height=BADGE_H, bg=KEY, highlightthickness=0)
        c.pack()

        try:
            img = tk.PhotoImage(file=str(self.icon_path))
            k = max(1, img.width() // 36)
            self.img = img.subsample(k, k)
        except Exception:
            self.img = None

        # presence pill (bottom): firetruck + "P25 TRACKER - running"
        bx0, by0, bx1, by1 = 8, BADGE_H - 46, BADGE_W - 8, BADGE_H - 6
        cy = (by0 + by1) // 2
        c.create_rectangle(bx0, by0, bx1, by1, fill="#10233a", outline="#3f6ea5", width=2)
        if self.img is not None:
            c.create_image(bx0 + 24, cy, image=self.img)
        c.create_text(bx0 + 48, cy, anchor="w", text="P25 TRACKER  ·  running",
                      font=("Segoe UI", 13, "bold"), fill="#e8f0f8")

        # alarm line (above the pill), hidden until an alarm
        ax0, ay0, ax1, ay1 = 8, 6, BADGE_W - 8, by0 - 8
        self.alarm_bg = c.create_rectangle(ax0, ay0, ax1, ay1, fill="#5a0000",
                                           outline="#ff3b3b", width=2, state="hidden")
        self.alarm_txt = c.create_text((ax0 + ax1) // 2, (ay0 + ay1) // 2,
                                       text="⚠  RADIO DISCONNECTED",
                                       font=("Segoe UI", 14, "bold"), fill="#ffffff", state="hidden")
        w.update_idletasks()
        self._click_through(w)
        w.withdraw()
        self.win, self.canvas = w, c

    def _click_through(self, win):
        hwnd = self.user32.GetParent(win.winfo_id()) or win.winfo_id()
        style = self.user32.GetWindowLongW(hwnd, -20)                       # GWL_EXSTYLE
        style |= 0x00080000 | 0x00000020 | 0x00000080 | 0x08000000          # layered, transparent, toolwindow, noactivate
        self.user32.SetWindowLongW(hwnd, -20, style)

    # ---- find the ArcGIS Earth window by its visible title (no process access) ----
    def _title_of(self, hwnd):
        n = self.user32.GetWindowTextLengthW(hwnd)
        if not n:
            return ""
        buf = ctypes.create_unicode_buffer(n + 1)
        self.user32.GetWindowTextW(hwnd, buf, n + 1)
        return buf.value

    def _earth_rect(self):
        found = []
        EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def cb(hwnd, _):
            try:
                if self.user32.IsWindowVisible(hwnd) and not self.user32.IsIconic(hwnd) \
                        and EARTH_TITLE in self._title_of(hwnd).lower():
                    r = wintypes.RECT()
                    if self.user32.GetWindowRect(hwnd, ctypes.byref(r)):
                        w, h = r.right - r.left, r.bottom - r.top
                        if w > 200 and h > 200:
                            found.append((w * h, (r.left, r.top, r.right, r.bottom)))
            except Exception:
                pass
            return True

        self.user32.EnumWindows(EnumProc(cb), 0)
        return max(found, key=lambda f: f[0])[1] if found else None

    def _track(self):
        if self.win is not None:
            try:
                rect = self._earth_rect()
                if rect is None:
                    self.win.withdraw()                 # no ArcGIS Earth window -> nothing to pin to
                else:
                    _, _, right, bottom = rect
                    x = right - RIGHT_GAP - BADGE_W
                    y = bottom - BOTTOM_GAP - BADGE_H
                    self.win.geometry(f"{BADGE_W}x{BADGE_H}+{x}+{y}")
                    self.win.deiconify()
                    self.win.attributes("-topmost", True)
            except Exception:
                pass
        self.root.after(500, self._track)

    def _blinker(self):
        show = self.tracking and not self.radio_ok
        self._blink = (not self._blink) if show else False
        try:
            st = "normal" if (show and self._blink) else "hidden"
            self.canvas.itemconfigure(self.alarm_bg, state=st)
            self.canvas.itemconfigure(self.alarm_txt, state=st)
        except Exception:
            pass
        self.root.after(600, self._blinker)
