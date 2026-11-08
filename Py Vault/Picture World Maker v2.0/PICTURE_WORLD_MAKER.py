#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PWM_PIPELINE import (
    BuildCancelled, PictureWorldError, build, check_zoom_range, estimate_synthetic_tiles, explorer_size,
    inspect_raster, load_config, photo_mode_available, recommended_max_zoom, synthetic_bounds_for_config,
    config_for_spot, world_spot_box_m, world_spot_label, world_spots,
)

APP = "PICTURE WORLD MAKER"
VERSION = "2.0"   # 2.0 Reference (2026-11-08): the whole ArcGIS Earth Unlocked family moved to 2.0 as one reference point - program = v0.2.4, only this text changed
HERE = Path(__file__).resolve().parent
BG = "#f3f5f7"
TEXT = "#17233a"
MUTED = "#5f6b7a"
ACCENT = "#d6a300"
GOOD = "#176b3a"
BLUE = "#1756A9"
_GUI_MUTEX_HANDLE = None


def acquire_single_instance() -> bool:
    global _GUI_MUTEX_HANDLE
    if os.name != "nt": return True
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.CreateMutexW.restype = ctypes.c_void_p
        h = k.CreateMutexW(None, False, "Local\\PictureWorldMakerGUI")
        if h and k.GetLastError() == 183:
            k.CloseHandle(h); return False
        _GUI_MUTEX_HANDLE = h
    except Exception:
        pass
    return True


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP} {VERSION}")
        self.geometry("1000x690")
        self.minsize(920, 630)
        self.configure(bg=BG)
        self.cfg = load_config(HERE)
        self.input_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="auto")
        self.output_mode_var = tk.StringVar(value="tpkx")
        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Desktop"))
        self.output_name_var = tk.StringVar(value="")
        self.zoom_min_var = tk.IntVar(value=self.cfg.default_min_zoom)
        self.zoom_max_var = tk.IntVar(value=self.cfg.default_max_zoom)
        self.scale_var = tk.DoubleVar(value=self.cfg.synthetic_meters_per_pixel)
        # v0.2.4: which World spot (1-20) on the ocean the picture is parked at
        self.spot_choices = [f"{n} · {world_spot_label(lat, lon)}" for n, lat, lon in world_spots(self.cfg)]
        self.spot_var = tk.StringVar(value=self.spot_choices[0])
        self.info_var = tk.StringVar(value="Choose a raster image. Picture World Maker will inspect it automatically.")
        self.status_var = tk.StringVar(value="Ready.")
        self.progress_var = tk.DoubleVar(value=0)
        self.cancel_event = threading.Event()
        self.thread = None
        self.raster_info = None
        self._build_started = None
        self._current_stage = "ready"
        self._current_message = "Ready."
        self._heartbeat_tick_index = 0
        self._closing = False
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._close)
        # v0.1.6: keep the tile estimate current when the zooms change
        for var in (self.zoom_min_var, self.zoom_max_var, self.spot_var):
            var.trace_add("write", lambda *_: self.refresh_info())

    def _build_ui(self):
        header = tk.Frame(self, bg=BG); header.pack(fill="x", padx=24, pady=(18,8))
        tk.Label(header, text="PICTURE WORLD MAKER", font=("Segoe UI", 24, "bold"), fg=TEXT, bg=BG).pack(side="left")
        tk.Label(header, text="SLICE • DICE • PRESENT", font=("Segoe UI", 11, "bold"), fg=MUTED, bg=BG).pack(side="right", pady=8)

        body = tk.Frame(self, bg=BG); body.pack(fill="both", expand=True, padx=24, pady=4)

        f1 = ttk.LabelFrame(body, text="1. Choose giant raster")
        f1.pack(fill="x", pady=7)
        row = tk.Frame(f1, bg=BG); row.pack(fill="x", padx=14, pady=12)
        ttk.Entry(row, textvariable=self.input_var).pack(side="left", fill="x", expand=True, padx=(0,10))
        ttk.Button(row, text="CHOOSE IMAGE", command=self.choose_input).pack(side="right")
        tk.Label(f1, textvariable=self.info_var, anchor="w", justify="left", bg=BG, fg=BLUE, font=("Segoe UI", 10, "bold")).pack(fill="x", padx=14, pady=(0,10))

        f3 = ttk.LabelFrame(body, text="2. Pyramid recipe")
        f3.pack(fill="x", pady=7)
        recipe = tk.Frame(f3, bg=BG); recipe.pack(fill="x", padx=14, pady=10)
        tk.Label(recipe, text="Min zoom", bg=BG, fg=TEXT).pack(side="left")
        ttk.Spinbox(recipe, from_=0, to=25, textvariable=self.zoom_min_var, width=6).pack(side="left", padx=(7,28))
        tk.Label(recipe, text="Max zoom", bg=BG, fg=TEXT).pack(side="left")
        ttk.Spinbox(recipe, from_=0, to=25, textvariable=self.zoom_max_var, width=6).pack(side="left", padx=(7,28))
        tk.Label(recipe, text="World spot", bg=BG, fg=TEXT).pack(side="left")
        ttk.Combobox(recipe, textvariable=self.spot_var, values=self.spot_choices, state="readonly", width=16).pack(side="left", padx=(7,28))
        self.recipe_var = tk.StringVar(value=self._recipe_text("flat"))
        tk.Label(recipe, textvariable=self.recipe_var, bg=BG, fg=GOOD, font=("Segoe UI", 10, "bold")).pack(side="left")

        f4 = ttk.LabelFrame(body, text="3. Finished product")
        f4.pack(fill="x", pady=7)
        out = tk.Frame(f4, bg=BG); out.pack(fill="x", padx=14, pady=(10,6))
        ttk.Radiobutton(out, text="MBTiles", value="mbtiles", variable=self.output_mode_var).pack(side="left", padx=(0,22))
        ttk.Radiobutton(out, text="TPKX", value="tpkx", variable=self.output_mode_var).pack(side="left", padx=(0,22))
        ttk.Radiobutton(out, text="Both", value="both", variable=self.output_mode_var).pack(side="left")
        out2 = tk.Frame(f4, bg=BG); out2.pack(fill="x", padx=14, pady=(2,10))
        tk.Label(out2, text="Name", bg=BG).pack(side="left")
        ttk.Entry(out2, textvariable=self.output_name_var, width=28).pack(side="left", padx=(6,14))
        tk.Label(out2, text="Folder", bg=BG).pack(side="left")
        ttk.Entry(out2, textvariable=self.output_dir_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(out2, text="BROWSE", command=self.choose_output_dir).pack(side="right")

        status = tk.Frame(body, bg=BG); status.pack(fill="x", pady=(12,4))
        self.bar = ttk.Progressbar(status, variable=self.progress_var, maximum=100); self.bar.pack(fill="x")
        tk.Label(status, textvariable=self.status_var, bg=BG, fg=TEXT, anchor="w", font=("Segoe UI",10,"bold")).pack(fill="x", pady=(6,0))

        buttons = tk.Frame(body, bg=BG); buttons.pack(fill="x", pady=(10,0))
        self.build_btn = tk.Button(buttons, text="BUILD RASTER PYRAMID", command=self.start_build, bg=ACCENT, fg=TEXT,
                                   font=("Segoe UI", 13, "bold"), padx=22, pady=12, relief="flat")
        self.build_btn.pack(side="left")
        self.cancel_btn = ttk.Button(buttons, text="CANCEL", command=self.cancel, state="disabled"); self.cancel_btn.pack(side="left", padx=14)
        tk.Label(buttons, text="Any picture → MBTiles → native TPKX for ArcGIS Earth", bg=BG, fg=MUTED).pack(side="right")

    def choose_input(self):
        p = filedialog.askopenfilename(title="Choose giant raster image", filetypes=[
            ("Raster images", "*.tif *.tiff *.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")])
        if not p: return
        self.input_var.set(p)
        self._inspect(p)

    def _inspect(self, p):
        """Inspect the picture (Pillow); True when accepted."""
        self.status_var.set("Inspecting raster...")
        self.update_idletasks()
        try:
            self.raster_info = inspect_raster(self.cfg, Path(p))
            if not self.output_name_var.get().strip(): self.output_name_var.set(Path(p).stem[:60])
            if self.raster_info.mode_suggested == "flat":
                self.mode_var.set("auto")
                self.zoom_max_var.set(recommended_max_zoom(float(self.scale_var.get())))
            self.refresh_info()
            self.status_var.set("Raster accepted. Ready to build.")
            return True
        except Exception as exc:
            self.raster_info = None
            self.info_var.set("Raster inspection failed.")
            self.status_var.set("Ready.")
            messagebox.showerror(APP, str(exc))
            return False

    def _spot(self):
        """v0.2.4: the chosen World spot number (1-20)."""
        try:
            return int(self.spot_var.get().split("·")[0].strip())
        except Exception:
            return 1

    def _spot_cfg(self):
        return config_for_spot(self.cfg, self._spot())

    def _spot_too_small(self, mpp):
        """True when the picture is bigger than its spot's own 1-degree box (it would reach the next spot)."""
        i = self.raster_info
        bw, bh = world_spot_box_m(self.cfg, self._spot())
        return i.width * mpp > bw or i.height * mpp > bh

    def _recipe_text(self, mode):
        """v0.2.0: show which engine will build this picture."""
        tiles = "PNG tiles" if self.cfg.photo_tiles == "png" else f"JPEG tiles (quality {self.cfg.photo_jpeg_quality}) + PNG edges"
        return f"PHOTO MODE • {tiles}"

    def refresh_info(self):
        if not self.raster_info or not hasattr(self, "info_var"): return
        i = self.raster_info
        selected = self.mode_var.get()
        mode = i.mode_suggested if selected == "auto" else selected
        if hasattr(self, "recipe_var"): self.recipe_var.set(self._recipe_text(mode))
        text = f"{i.width:,} × {i.height:,} pixels • {i.driver}"
        if i.has_crs:
            text += " • has map coordinates: ArcGIS Earth can open this file directly - here it is built as a picture"
        if mode == "flat":
            try:
                mpp = float(self.scale_var.get())
                c = self._spot_cfg()
                b = synthetic_bounds_for_config(c, i.width, i.height, mpp)
                z0, z1 = int(self.zoom_min_var.get()), int(self.zoom_max_var.get())
                tiles = estimate_synthetic_tiles(b, z0, z1)
                text += (f"\nParked at World spot {self._spot()} ({world_spot_label(c.synthetic_anchor_lat, c.synthetic_anchor_lon)}), "
                         f"Atlantic east of Florida • estimated tile addresses Z{z0}–Z{z1}: {tiles:,}")
                if self._spot_too_small(mpp):
                    text += "\nThis picture is bigger than one World spot's box - it will reach into the next spot."
            except Exception:
                pass
        self.info_var.set(text)

    def choose_output_dir(self):
        p = filedialog.askdirectory(title="Choose output folder", initialdir=self.output_dir_var.get() or str(Path.home()))
        if p: self.output_dir_var.set(p)

    def start_build(self):
        if self.thread and self.thread.is_alive(): return
        typed = self.input_var.get().strip().strip('"')
        # v0.1.6: a path typed or pasted into the box (or changed after CHOOSE IMAGE) is inspected too.
        if typed and (not self.raster_info or Path(typed).expanduser().resolve() != self.raster_info.path):
            if not self._inspect(typed): return
        if not self.raster_info:
            messagebox.showwarning(APP, "Choose a raster image first."); return
        try:
            zmin, zmax = int(self.zoom_min_var.get()), int(self.zoom_max_var.get())
            mpp = float(self.scale_var.get())
            if mpp <= 0: raise ValueError
        except Exception:
            messagebox.showerror(APP, "Zoom values must be whole numbers 0–25 and flat-image scale must be positive."); return
        try:
            check_zoom_range(zmin, zmax, self.output_mode_var.get())
        except ValueError as exc:
            messagebox.showerror(APP, str(exc)); return
        actual_mode = self.raster_info.mode_suggested if self.mode_var.get() == "auto" else self.mode_var.get()
        if actual_mode == "flat":
            try:
                tiles = estimate_synthetic_tiles(synthetic_bounds_for_config(self._spot_cfg(), self.raster_info.width, self.raster_info.height, mpp), zmin, zmax)
                if tiles >= self.cfg.warning_tile_count:
                    if not messagebox.askyesno(APP, f"This pyramid is estimated at about {tiles:,} tile addresses.\n\nContinue?"):
                        return
            except Exception: pass
            if self._spot_too_small(mpp):
                if not messagebox.askyesno(APP, f"This picture is bigger than World spot {self._spot()}'s box, so it will reach into "
                                                 "the next spot and may cover a picture parked there.\n\nBuild anyway?"):
                    return
        # v0.2.4: the file name carries its World spot, e.g. Tower_of_Babel_spot02.tpkx
        spot = self._spot()
        stem = self.output_name_var.get().strip() or self.raster_info.path.stem[:60]
        if not stem.lower().endswith(f"_spot{spot:02d}"):
            stem = f"{stem}_spot{spot:02d}"
        self.cancel_event.clear(); self.progress_var.set(0)
        self.build_btn.config(state="disabled"); self.cancel_btn.config(state="normal")
        self._build_started = time.monotonic()
        self._current_stage = "starting"
        self._current_message = "Starting..."
        self.status_var.set("WORKING 00:00:00 • STARTING")
        self.after(250, self._heartbeat)
        args = dict(
            config=self._spot_cfg(), input_file=self.raster_info.path, raster_mode=self.mode_var.get(),
            output_mode=self.output_mode_var.get(), output_dir=Path(self.output_dir_var.get()),
            output_stem=stem, zoom_min=zmin, zoom_max=zmax,
            meters_per_pixel=mpp, progress=self._progress_from_worker, cancel_event=self.cancel_event,
        )
        self.thread = threading.Thread(target=self._run_build, kwargs=args, daemon=True); self.thread.start()

    def _progress_from_worker(self, stage, msg, frac):
        self.after(0, self._apply_progress, stage, msg, frac)

    @staticmethod
    def _stage_label(stage):
        labels = {
            "render": "PHOTO MODE PYRAMID",
            "verify_mb": "VERIFYING MBTILES",
            "publish_mb": "PUBLISHING MBTILES",
            "convert": "TPKX CONVERTER",
            "package": "PACKAGING TPKX",
            "verify_tpkx": "VERIFYING TPKX",
            "complete": "COMPLETE",
            "starting": "STARTING",
        }
        return labels.get(str(stage), str(stage).replace("_", " ").upper())

    def _apply_progress(self, stage, msg, frac):
        self._current_stage = stage
        self._current_message = msg
        if frac is not None:
            self.progress_var.set(max(0, min(100, frac*100)))
        self._render_working_status()

    def _render_working_status(self):
        if not (self.thread and self.thread.is_alive()) or self._build_started is None:
            return
        elapsed = max(0, int(time.monotonic() - self._build_started))
        hh, rem = divmod(elapsed, 3600)
        mm, ss = divmod(rem, 60)
        pulse = ("●", "◐", "○", "◑")[self._heartbeat_tick_index % 4]
        label = self._stage_label(self._current_stage)
        detail = self._current_message.strip()
        text = f"{pulse} WORKING {hh:02d}:{mm:02d}:{ss:02d} • {label}"
        if detail and detail.upper() not in text.upper():
            text += f" • {detail}"
        self.status_var.set(text)

    def _heartbeat(self):
        if not (self.thread and self.thread.is_alive()):
            return
        self._heartbeat_tick_index += 1
        self._render_working_status()
        self.after(1000, self._heartbeat)

    def _run_build(self, **kwargs):
        try:
            result = build(**kwargs)
        except BuildCancelled as exc:
            # v0.1.6: bind the message now - Python deletes 'exc' when this block ends,
            # so v0.1.5's lambda raised NameError and the Cancelled box never appeared.
            if not self._closing:
                self.after(0, lambda m=str(exc): messagebox.showinfo(APP, m))
                self.after(0, self._finish_ui, "Cancelled.", False)
        except Exception as exc:
            if not self._closing:
                self.after(0, lambda e=str(exc): messagebox.showerror(APP, e))
                self.after(0, self._finish_ui, "Build failed.", False)
        else:
            parts = [f"Tiles: {result.tile_count:,}", f"Zooms: {result.min_zoom}–{result.max_zoom}", f"Elapsed: {time.strftime('%H:%M:%S', time.gmtime(result.elapsed_seconds))}"]
            if result.mbtiles_file: parts.append(f"MBTiles: {result.mbtiles_file}")
            if result.tpkx_file: parts.append(f"TPKX: {result.tpkx_file}")
            if result.bundle_count: parts.append(f"Bundles: {result.bundle_count:,}")
            text = "RASTER PYRAMID COMPLETE\n\n" + "\n".join(parts)
            self.after(0, lambda: messagebox.showinfo(APP, text))
            self.after(0, self._finish_ui, "COMPLETE — verified pyramid product(s) published.", True)

    def _finish_ui(self, msg, complete):
        self._build_started = None
        self._current_stage = "complete" if complete else "ready"
        self._current_message = msg
        self.status_var.set(msg); self.progress_var.set(100 if complete else 0)
        self.build_btn.config(state="normal"); self.cancel_btn.config(state="disabled")

    def cancel(self):
        if self.thread and self.thread.is_alive():
            self.cancel_event.set(); self.status_var.set("Cancellation requested — stopping active process tree...")

    def _close(self):
        if self._closing: return
        if self.thread and self.thread.is_alive():
            if not messagebox.askyesno(APP, "A pyramid build is running. Cancel it and close?"): return
            # v0.1.6: stop the build and clean the working folder BEFORE closing. v0.1.5 closed at
            # once, which ended the build thread before it could stop the background programs, so
            # QGIS kept running hidden and the temporary working folder was never removed.
            self._closing = True
            self.cancel_event.set()
            self.build_btn.config(state="disabled"); self.cancel_btn.config(state="disabled")
            self.status_var.set("Stopping the build and cleaning up before closing...")
            self._close_deadline = time.monotonic() + 60
            self.after(200, self._close_when_stopped)
            return
        self.destroy()

    def _close_when_stopped(self):
        if self.thread and self.thread.is_alive() and time.monotonic() < self._close_deadline:
            self.after(200, self._close_when_stopped); return
        self.destroy()


def main():
    if not acquire_single_instance():
        messagebox.showwarning(APP, "Picture World Maker is already running.")
        return 2
    app = App(); app.mainloop(); return 0

if __name__ == "__main__":
    raise SystemExit(main())
