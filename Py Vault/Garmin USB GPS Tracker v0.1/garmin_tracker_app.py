"""Garmin USB GPS Tracker - control panel (Claude + Jim, 2026-11-12, v0.1).

A small window that reads your Garmin USB GPS and plots your live position on the
offline ArcGIS Earth map, one marker, updated about once a second. Standard Python 3
with Tk only; no COM port, no NMEA, no driver change.
"""
import queue, threading, datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk

import garmin_core as core

FIX_TEXT = core.FIX_TEXT


def now_hhmmss():
    return datetime.datetime.now().strftime("%H:%M:%S")


class State:
    center = False          # "Keep me centered" checkbox


class App:
    def __init__(self, root):
        self.root = root
        root.title("Garmin USB GPS Tracker")
        root.geometry("520x380"); root.minsize(460, 340)
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.idle_stop = threading.Event()
        self.idle_thread = None
        self.state = State()
        self.earth = core.EarthClient()

        self._build_ui()
        self.root.after(150, self._poll)
        self._start_idle()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI ----
    def _light(self, parent, text, padx=(6, 26)):
        bg = self.root.cget("bg")
        c = tk.Canvas(parent, width=26, height=26, highlightthickness=0, bd=0, bg=bg)
        oval = c.create_oval(4, 4, 23, 23, fill="#c62828", outline="#7a1414", width=1)
        c.pack(side="left")
        tk.Label(parent, text=text, font=("Segoe UI", 12, "bold"), bg=bg).pack(side="left", padx=padx)
        return (c, oval)

    def _set_light(self, light, ok):
        c, oval = light
        c.itemconfigure(oval, fill="#1a7f37" if ok else "#c62828",
                        outline="#145c28" if ok else "#7a1414")

    def _build_ui(self):
        ind = ttk.Frame(self.root, padding=(12, 10, 12, 4)); ind.pack(fill="x")
        self.gps_dot = self._light(ind, "GPS connected")
        self.earth_dot = self._light(ind, "ArcGIS Earth API ready", padx=(6, 0))

        top = ttk.Frame(self.root, padding=(12, 6)); top.pack(fill="x")
        self.start_btn = ttk.Button(top, text="Start tracking", command=self._start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(top, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(6, 0))
        self.center_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Keep me centered", variable=self.center_var,
                        command=self._on_center).pack(side="right")

        self.status = ttk.Label(self.root, text="Stopped", foreground="#555", padding=(14, 0))
        self.status.pack(anchor="w")

        box = ttk.LabelFrame(self.root, text="Position", padding=12)
        box.pack(fill="x", padx=12, pady=8)
        self.v = {}
        for i, (key, lbl) in enumerate((("fix", "Fix"), ("pos", "Latitude, Longitude"),
                                        ("acc", "Accuracy"), ("spd", "Speed"), ("upd", "Last update"))):
            ttk.Label(box, text=lbl + ":").grid(row=i, column=0, sticky="w", pady=2)
            val = ttk.Label(box, text="-", font=("Consolas", 11))
            val.grid(row=i, column=1, sticky="w", padx=(12, 0), pady=2)
            self.v[key] = val

        lf = ttk.Frame(self.root, padding=(12, 4)); lf.pack(fill="both", expand=True)
        ttk.Label(lf, text="Activity").pack(anchor="w")
        self.logbox = tk.Text(lf, height=5, wrap="word", state="disabled",
                              font=("Consolas", 9), background="#111", foreground="#ddd")
        self.logbox.pack(fill="both", expand=True)

    def _on_center(self):
        self.state.center = bool(self.center_var.get())

    # ---- idle 'start ready' probe ----
    def _idle_probe(self):
        while not self.idle_stop.is_set():
            self._emit("gps", core.device_present())
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

    # ---- start/stop ----
    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        self._stop_idle()
        self.stop_event.clear()
        self.worker = threading.Thread(target=core.run_bridge,
                                       args=(self.state, self.stop_event, self._emit), daemon=True)
        self.worker.start()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

    def _stop(self):
        self.stop_event.set()
        self.stop_btn.configure(state="disabled")

    # ---- events ----
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

    def _handle(self, kind, args):
        if kind == "status":
            self.status.configure(text=args[0]); self._log(args[0])
            if args[0] == "stopped":
                self.start_btn.configure(state="normal")
                self.stop_btn.configure(state="disabled")
                self._start_idle()
        elif kind == "gps":
            self._set_light(self.gps_dot, bool(args[0]))
        elif kind == "earth":
            self._set_light(self.earth_dot, bool(args[0]))
        elif kind == "fix":
            f = args[0]
            fixn = f["fix"]
            self.v["fix"].configure(text=FIX_TEXT.get(fixn, str(fixn)),
                                    foreground="#1a7f37" if fixn >= 2 else "#b7791f")
            if fixn >= 2:
                self.v["pos"].configure(text=f"{f['lat']:.6f}, {f['lon']:.6f}")
                self.v["acc"].configure(text=f"±{f['epe_m']:.0f} m")
                self.v["spd"].configure(text=f"{f['speed_mph']:.0f} mph")
            else:
                self.v["pos"].configure(text="(waiting for fix)")
            self.v["upd"].configure(text=now_hhmmss())
        elif kind == "log":
            self._log(args[0])

    def _log(self, text):
        line = f"[{now_hhmmss()}] {text}"
        self.logbox.configure(state="normal")
        self.logbox.insert("end", line + "\n"); self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def _on_close(self):
        self.stop_event.set()
        self._stop_idle()
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
