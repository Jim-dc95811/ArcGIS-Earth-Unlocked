"""P25 GPS Tracker - control panel (Claude + Jim, 2026-11-12, v0.8).

A single window that runs the live bridge (radio -> ArcGIS Earth), shows every unit
the radio reports with a Live / Stale / Expired status, and lets you give each P25
unit ID a friendly alias (9076801 -> "Jax 24") that labels its marker on the map.

Aliases are saved in aliases.json next to this file. Standard Python 3 with Tk only.
"""
import json, queue, threading, datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

import p25_core as core
try:
    from overlay import StatusOverlay          # on-screen badge over ArcGIS Earth (Windows)
except Exception:
    StatusOverlay = None

ALIAS_FILE = Path(__file__).resolve().parent / "aliases.json"
MARKER_FILE = Path(__file__).resolve().parent / "marker.png"
SETTINGS_FILE = Path(__file__).resolve().parent / "settings.json"
LOG_DIR = Path(__file__).resolve().parent.parent / "Logs"

# How long an idle unit stays on the map before it is dropped. Plain choices so
# there is no typing and no unit confusion; "Never remove" keeps it until Stop.
RETIRE_PRESETS = [
    ("30 minutes", 30 * 60),
    ("1 hour", 60 * 60),
    ("2 hours", 2 * 60 * 60),
    ("4 hours", 4 * 60 * 60),
    ("8 hours", 8 * 60 * 60),
    ("Never remove", 0),
]
DEFAULT_RETIRE_LABEL = "2 hours"


def now_hhmmss():
    return datetime.datetime.now().strftime("%H:%M:%S")


class AliasDialog(tk.Toplevel):
    def __init__(self, parent, title, unit="", alias="", lock_unit=False):
        super().__init__(parent)
        self.title(title); self.resizable(False, False); self.result = None
        self.transient(parent); self.grab_set()
        frm = ttk.Frame(self, padding=14); frm.grid()
        ttk.Label(frm, text="Unit ID (P25):").grid(row=0, column=0, sticky="w", pady=4)
        self.u = ttk.Entry(frm, width=22); self.u.grid(row=0, column=1, pady=4)
        self.u.insert(0, unit)
        if lock_unit:
            self.u.configure(state="disabled")
        ttk.Label(frm, text="Alias (shown on map):").grid(row=1, column=0, sticky="w", pady=4)
        self.a = ttk.Entry(frm, width=22); self.a.grid(row=1, column=1, pady=4)
        self.a.insert(0, alias)
        btns = ttk.Frame(frm); btns.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btns, text="Save", command=self._ok).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="Cancel", command=self.destroy).grid(row=0, column=1, padx=5)
        (self.a if lock_unit else self.u).focus_set()
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _ok(self):
        unit = self.u.get().strip()
        if not unit:
            messagebox.showwarning("Missing", "Enter a Unit ID.", parent=self); return
        self.result = (unit, self.a.get().strip())
        self.destroy()


class App:
    def __init__(self, root):
        self.root = root
        root.title("P25 GPS Tracker")
        root.geometry("820x580"); root.minsize(680, 480)

        self._alias_lock = threading.Lock()
        self.aliases = self._load_aliases()
        self.events = queue.Queue()
        self.redraw_q = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.idle_stop = threading.Event()      # the 'start ready' probe (runs while not tracking)
        self.idle_thread = None
        self.rows = {}

        self.earth = core.EarthClient()
        self.tracker = core.Tracker(self.earth, alias_fn=self._alias_for)

        self._build_ui()
        self._apply_retire_setting()
        for unit, alias in sorted(self.aliases.items()):
            self._ensure_row(unit); self._set_cell(unit, "alias", alias)
        self.root.after(150, self._poll)
        self._start_idle()                      # light the lamps now, before Start tracking
        self.badge = None                       # on-screen overlay pinned over ArcGIS Earth
        if StatusOverlay is not None:
            try:
                b = StatusOverlay(self.root, MARKER_FILE)
                if b.start():
                    self.badge = b
            except Exception:
                self.badge = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- 'start ready' probe: while NOT tracking, check radio + ArcGIS Earth every 2 s ----
    def _idle_probe(self):
        while not self.idle_stop.is_set():
            self._emit("radio", core.radio_reachable())
            self._emit("earth", core.earth_reachable(self.earth))
            self.idle_stop.wait(2.0)

    def _start_idle(self):
        if self.idle_thread and self.idle_thread.is_alive():
            return
        self.idle_stop.clear()
        self.idle_thread = threading.Thread(target=self._idle_probe, daemon=True)
        self.idle_thread.start()

    def _stop_idle(self):
        self.idle_stop.set()

    def _load_aliases(self):
        try:
            if ALIAS_FILE.is_file():
                d = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
                if isinstance(d, dict):
                    return {str(k): str(v) for k, v in d.items()}
        except Exception:
            pass
        return {}

    def _save_aliases(self):
        try:
            with self._alias_lock:
                data = dict(self.aliases)
            ALIAS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            self._log(f"could not save aliases.json: {exc}")

    def _alias_for(self, unit):
        with self._alias_lock:
            return self.aliases.get(unit)

    # ---- retirement time (how long an idle unit stays on the map) ----
    def _load_settings(self):
        try:
            if SETTINGS_FILE.is_file():
                d = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                if isinstance(d, dict):
                    return d
        except Exception:
            pass
        return {}

    def _save_settings(self):
        try:
            SETTINGS_FILE.write_text(
                json.dumps({"retire_seconds": self.tracker.expire_s}, indent=2),
                encoding="utf-8")
        except Exception as exc:
            self._log(f"could not save settings.json: {exc}")

    def _apply_retire_setting(self):
        """Load the saved retirement time and show it in the picker."""
        secs = self._load_settings().get("retire_seconds", core.EXPIRE_SECONDS)
        label = next((l for l, s in RETIRE_PRESETS if s == secs), None)
        if label is None:                       # unknown saved value -> safe default
            label = DEFAULT_RETIRE_LABEL
            secs = dict(RETIRE_PRESETS)[label]
        self.tracker.expire_s = secs
        self.retire_var.set(label)

    def _on_retire_change(self, event=None):
        label = self.retire_var.get()
        secs = dict(RETIRE_PRESETS).get(label, core.EXPIRE_SECONDS)
        self.tracker.expire_s = secs            # read live by the sweep; takes effect at once
        self._save_settings()
        self._log(f"retirement time set to: {label}")

    def _light(self, parent, text, padx=(6, 28)):
        """A big round status light (red/green) with a bold label beside it."""
        bg = self.root.cget("bg")
        c = tk.Canvas(parent, width=26, height=26, highlightthickness=0, bd=0, bg=bg)
        oval = c.create_oval(4, 4, 23, 23, fill="#c62828", outline="#7a1414", width=1)
        c.pack(side="left")
        tk.Label(parent, text=text, font=("Segoe UI", 12, "bold"), bg=bg).pack(side="left", padx=padx)
        return (c, oval)

    def _build_ui(self):
        # Status lights (top strip, above the controls/status). Red = not ready,
        # green = ready. These run even before Start tracking so you can see at a
        # glance whether the radio and ArcGIS Earth are both ready to go.
        ind = ttk.Frame(self.root, padding=(12, 10, 12, 4)); ind.pack(fill="x")
        self.radio_dot = self._light(ind, "Radio connected")
        self.earth_dot = self._light(ind, "ArcGIS Earth API ready", padx=(6, 0))

        top = ttk.Frame(self.root, padding=(10, 8)); top.pack(fill="x")
        self.start_btn = ttk.Button(top, text="Start tracking", command=self._start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(top, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(6, 0))
        self.status = ttk.Label(top, text="Stopped", foreground="#555")
        self.status.pack(side="left", padx=14)

        # Retirement-time picker (right side of the top bar).
        self.retire_var = tk.StringVar(value=DEFAULT_RETIRE_LABEL)
        self.retire_cb = ttk.Combobox(top, textvariable=self.retire_var, width=13,
                                      state="readonly",
                                      values=[label for label, _ in RETIRE_PRESETS])
        self.retire_cb.pack(side="right")
        self.retire_cb.bind("<<ComboboxSelected>>", self._on_retire_change)
        ttk.Label(top, text="Drop idle units after:").pack(side="right", padx=(0, 5))

        mid = ttk.Frame(self.root, padding=(10, 4)); mid.pack(fill="both", expand=True)
        ttk.Label(mid, text="Units  (double-click a row to name it)").pack(anchor="w")
        cols = ("unit", "alias", "status", "last", "pos")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=10)
        for c, t, w in (("unit", "Unit ID", 100), ("alias", "Alias", 140),
                        ("status", "Status", 80), ("last", "Last fix", 80),
                        ("pos", "Last position", 190)):
            self.tree.heading(c, text=t); self.tree.column(c, width=w, anchor="w")
        self.tree.tag_configure("live", foreground="#1a7f37")
        self.tree.tag_configure("stale", foreground="#b7791f")
        self.tree.tag_configure("expired", foreground="#999999")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y"); self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", lambda e: self._edit_alias())

        btns = ttk.Frame(self.root, padding=(10, 4)); btns.pack(fill="x")
        ttk.Button(btns, text="Add / name a unit", command=self._add_alias).pack(side="left")
        ttk.Button(btns, text="Edit alias", command=self._edit_alias).pack(side="left", padx=6)
        ttk.Button(btns, text="Remove alias", command=self._remove_alias).pack(side="left")

        lf = ttk.Frame(self.root, padding=(10, 6)); lf.pack(fill="both")
        ttk.Label(lf, text="Activity").pack(anchor="w")
        self.logbox = tk.Text(lf, height=8, wrap="word", state="disabled",
                              font=("Consolas", 9), background="#111", foreground="#ddd")
        self.logbox.pack(fill="both", expand=True)

    def _ensure_row(self, unit):
        if unit not in self.rows:
            self.rows[unit] = self.tree.insert("", "end", values=(unit, "", "", "", ""))
        return self.rows[unit]

    def _set_cell(self, unit, col, value):
        iid = self._ensure_row(unit)
        idx = {"unit": 0, "alias": 1, "status": 2, "last": 3, "pos": 4}[col]
        vals = list(self.tree.item(iid, "values"))
        vals[idx] = value
        self.tree.item(iid, values=vals)

    def _set_status(self, unit, text, tag):
        self._set_cell(unit, "status", text)
        self.tree.item(self._ensure_row(unit), tags=(tag,))

    def _selected_unit(self):
        sel = self.tree.selection()
        return self.tree.item(sel[0], "values")[0] if sel else None

    def _apply_alias(self, unit, alias):
        with self._alias_lock:
            if alias:
                self.aliases[unit] = alias
            else:
                self.aliases.pop(unit, None)
        self._save_aliases()
        self._set_cell(unit, "alias", alias)
        self.redraw_q.put(unit)
        self._log(f"alias: {unit} -> {alias or '(none)'}")

    def _add_alias(self):
        dlg = AliasDialog(self.root, "Add / name a unit")
        self.root.wait_window(dlg)
        if dlg.result:
            self._apply_alias(*dlg.result)

    def _edit_alias(self):
        unit = self._selected_unit()
        if not unit:
            messagebox.showinfo("Pick a unit", "Select a row first.", parent=self.root); return
        cur = self._alias_for(unit) or ""
        dlg = AliasDialog(self.root, "Edit alias", unit=unit, alias=cur, lock_unit=True)
        self.root.wait_window(dlg)
        if dlg.result:
            self._apply_alias(unit, dlg.result[1])

    def _remove_alias(self):
        unit = self._selected_unit()
        if unit:
            self._apply_alias(unit, "")

    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        self._stop_idle()                       # the bridge drives the lights while tracking
        if self.badge:
            self.badge.set_tracking(True)       # arm the RADIO DISCONNECTED alarm
        self.stop_event.clear()
        self.worker = threading.Thread(
            target=core.run_bridge,
            args=(self.tracker, self.stop_event, self._emit, self.redraw_q),
            daemon=True)
        self.worker.start()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

    def _stop(self):
        self.stop_event.set()
        self.stop_btn.configure(state="disabled")

    def _emit(self, kind, *args):
        self.events.put((kind, args))

    def _poll(self):
        try:
            while True:
                kind, args = self.events.get_nowait()
                self._handle(kind, args)
        except queue.Empty:
            pass
        self.root.after(150, self._poll)

    def _set_light(self, light, ok):
        c, oval = light
        c.itemconfigure(oval, fill="#1a7f37" if ok else "#c62828",      # green / red
                        outline="#145c28" if ok else "#7a1414")

    def _handle(self, kind, args):
        if kind == "status":
            self.status.configure(text=args[0]); self._log(args[0])
            if args[0] == "stopped":
                self.start_btn.configure(state="normal")
                self.stop_btn.configure(state="disabled")
                if self.badge:
                    self.badge.set_tracking(False)   # disarm the alarm when not tracking
                self._start_idle()              # resume the 'start ready' probe
        elif kind == "fix":
            unit, lat, lon, utc, how = args
            self._ensure_row(unit)
            self._set_cell(unit, "last", now_hhmmss())
            self._set_cell(unit, "pos", f"{lat:.5f}, {lon:.5f}")
            self._set_status(unit, "Live", "live")
            if how == "new":
                self._log(f"NEW unit {unit}  {lat:.5f},{lon:.5f}")
        elif kind == "stale":
            self._set_status(args[0], "Stale", "stale")
            self._log(f"unit {args[0]} aging (no new fix)")
        elif kind == "expire":
            self._set_status(args[0], "Expired", "expired")
            self._log(f"EXPIRE unit {args[0]} - idle past {self.retire_var.get()}, marker removed")
        elif kind == "radio":
            self._set_light(self.radio_dot, bool(args[0]))
            if self.badge:
                self.badge.set_radio(bool(args[0]))
        elif kind == "earth":
            self._set_light(self.earth_dot, bool(args[0]))
        elif kind == "log":
            self._log(args[0])

    def _log(self, text):
        line = f"[{now_hhmmss()}] {text}"
        self.logbox.configure(state="normal")
        self.logbox.insert("end", line + "\n"); self.logbox.see("end")
        self.logbox.configure(state="disabled")
        try:
            LOG_DIR.mkdir(exist_ok=True)
            with open(LOG_DIR / f"p25_tracker_{datetime.date.today():%Y%m%d}.log",
                      "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def _on_close(self):
        self.stop_event.set()
        self._stop_idle()
        if self.badge:
            self.badge.destroy()
        self._save_aliases()
        self.root.after(250, self.root.destroy)


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
