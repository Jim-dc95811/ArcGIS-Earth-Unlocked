#!/usr/bin/env python3
"""Traveler Manager - set up a Traveler box and name your units, from the PC.

The Lookout Traveler's own setup app - a fully independent product, zero files
shared with Lookout Manager (a Traveler box carries only Traveler files).

Two tabs:
  * Set up a router - point it at a brand-new GL-MT3000 (IP + its admin password)
    and it installs everything over SSH: Python + libusb, the Traveler programs, the
    split-screen map, the two boot services and the hotplug handler, then starts them.
    The same thing you would otherwise type by hand, in one button.

    The Traveler program files ship bundled beside this app (the "Traveler Files"
    folder). Manager streams each to the box over SSH with `cat > file`, which works
    on the box's dropbear SSH (it has no SFTP). No GitHub needed - the install never
    depends on anything but the box's own GL/OpenWrt package feed (for python3 +
    libusb, the one internet moment).

  * Name units - load the current unit-ID -> name table from a running box, edit it,
    save it back. Names appear on the map within a few seconds.

Deltas from the fixed Lookout (per the Lookout-vs-Traveler comparison):
  - GPS is the Garmin over libusb (gps_source auto-detects it) - same as the Lookout.
  - NO audio: no sound-card package, no audio streamer, no audio boot service.
  - The map is the locked split-screen (hybrid top / street bottom) - its own map.html.
  - Two services on the box (radio bridge + map server), not three.

Standard library + paramiko (for SSH). The .bat installs paramiko if it is missing.

Run:  double-click  Start Traveler Manager.bat
"""
import json, http.client, threading, queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog

VERSION       = "1.1"
PORT          = 8080
DEFAULT_IP    = "192.168.8.1"
DEFAULT_TOKEN = "lookout"


# --- the provisioning sequence -------------------------------------------------
# Two kinds of step:
#   sh(label, cmd)                         - a plain shell command
#   fetch(label, files, pre=.., post=..)   - stream files from the bundled
#        "Traveler Files" folder onto the box (cat > remote):
#        files = [(bundle_path, remote_path), ...]
#        pre/post are optional shell commands run before/after (mkdir, chmod).
#
# This is the proven Lookout provisioning engine with the audio steps removed and
# the map set to the split-screen page. The boot service it installs (bk-bridge)
# brings usb0 up and frees the Garmin for libusb - the radio AND "you are here".
def sh(label, cmd):                            return ("sh", label, cmd)
def fetch(label, files, pre=None, post=None):  return ("fetch", label, files, pre, post)

SETUP_STEPS = [
    sh("Updating the package list",            "opkg update"),
    sh("Installing Python (takes a minute)",   "which python3 >/dev/null 2>&1 && echo 'already installed' || opkg install python3"),
    sh("Installing GPS support (libusb)",      "opkg list-installed | grep -q '^libusb-1.0-0 ' && echo 'already installed' || opkg install libusb-1.0-0"),
    fetch("Delivering the radio bridge",       [("bk_bridge.py",    "/root/bk_bridge.py"),
                                                ("gps_source.py",   "/root/gps_source.py"),
                                                ("garmin_linux.py", "/root/garmin_linux.py")]),
    fetch("Delivering the map server",         [("units_kml.py",    "/root/units_kml.py")]),
    fetch("Delivering the split-screen map",   [("map.html",        "/root/map.html"),
                                                ("leaflet.js",      "/root/leaflet.js"),
                                                ("leaflet.css",     "/root/leaflet.css")]),
    fetch("Installing the hotplug handler",    [("openwrt/hotplug-usb0", "/etc/hotplug.d/net/30-traveler-usb0")],
                                               pre="mkdir -p /etc/hotplug.d/net"),
    fetch("Installing the boot services",      [("openwrt/bk-bridge", "/etc/init.d/bk-bridge"),
                                                ("openwrt/units-kml", "/etc/init.d/units-kml")],
                                               post="chmod +x /etc/init.d/bk-bridge /etc/init.d/units-kml"),
    sh("Enabling them on boot",                "/etc/init.d/bk-bridge enable && /etc/init.d/units-kml enable"),
    sh("Starting the services",                "/etc/init.d/bk-bridge start && /etc/init.d/units-kml start"),
    sh("Checking they are running",            "sleep 1; ps | grep -c '[p]ython3 /root'"),
    sh("Saving everything to flash",           "sync"),   # REQUIRED - or a power-pull reverts the whole setup
]

SERVICES_EXPECTED = 2   # radio bridge + map server (the Traveler has no audio)


def all_fetch_files():
    """Every (bundle_path, remote_path) the setup delivers - used to validate the bundle."""
    out = []
    for step in SETUP_STEPS:
        if step[0] == "fetch":
            out.extend(step[2])
    return out


def default_files_dir():
    """The bundled Traveler Files folder - a sibling of this script, inside System Files."""
    return Path(__file__).resolve().parent / "Traveler Files"


# ======================= Name units tab =======================
class NamesTab(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        top = tk.Frame(self, padx=10, pady=10); top.pack(fill="x")
        tk.Label(top, text="Box IP").grid(row=0, column=0, sticky="w")
        self.ip = tk.Entry(top, width=16); self.ip.insert(0, DEFAULT_IP); self.ip.grid(row=0, column=1, padx=6)
        tk.Label(top, text="Token").grid(row=0, column=2, sticky="w")
        self.token = tk.Entry(top, width=12); self.token.insert(0, DEFAULT_TOKEN); self.token.grid(row=0, column=3, padx=6)
        tk.Button(top, text="Load from box", command=self.load).grid(row=0, column=4, padx=4)

        hdr = tk.Frame(self, padx=12); hdr.pack(fill="x")
        tk.Label(hdr, text="Unit ID", width=20, anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=0)
        tk.Label(hdr, text="Name",    width=28, anchor="w", font=("Segoe UI", 9, "bold")).grid(row=0, column=1)

        mid = tk.Frame(self); mid.pack(fill="both", expand=True, padx=12)
        self.canvas = tk.Canvas(mid, highlightthickness=0)
        sb = tk.Scrollbar(mid, orient="vertical", command=self.canvas.yview)
        self.rows_frame = tk.Frame(self.canvas)
        self.rows_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        self.rows = []

        bot = tk.Frame(self, padx=10, pady=8); bot.pack(fill="x")
        tk.Button(bot, text="+ Add unit", command=lambda: self.add_row("", "")).pack(side="left")
        tk.Button(bot, text="Save to box", command=self.save, bg="#228B55", fg="white",
                  font=("Segoe UI", 9, "bold")).pack(side="right")
        self.status = tk.Label(self, text="Enter the box IP and click \"Load from box\".",
                               anchor="w", fg="#555", padx=12, pady=4)
        self.status.pack(fill="x")
        self.add_row("", "")

    def add_row(self, uid, name):
        fr = tk.Frame(self.rows_frame)
        e1 = tk.Entry(fr, width=20); e1.insert(0, uid); e1.grid(row=0, column=0, padx=2, pady=2)
        e2 = tk.Entry(fr, width=28); e2.insert(0, name); e2.grid(row=0, column=1, padx=2, pady=2)
        tk.Button(fr, text="-", width=2, command=lambda: self.del_row(fr)).grid(row=0, column=2, padx=4)
        fr.pack(anchor="w")
        self.rows.append((fr, e1, e2))

    def del_row(self, fr):
        self.rows = [r for r in self.rows if r[0] is not fr]
        fr.destroy()

    def clear(self):
        for fr, _, _ in self.rows:
            fr.destroy()
        self.rows = []

    def _conn(self):
        return http.client.HTTPConnection(self.ip.get().strip(), PORT, timeout=6)

    def load(self):
        try:
            c = self._conn()
            c.request("GET", "/admin/aliases?token=" + self.token.get().strip())
            r = c.getresponse(); data = json.loads(r.read() or b"{}")
            if r.status != 200 or not data.get("ok"):
                return self.set_status("Load failed: " + str(data.get("error", r.status)), True)
            al = data.get("aliases", {})
            self.clear()
            for uid, name in sorted(al.items()):
                self.add_row(uid, name)
            if not al:
                self.add_row("", "")
            self.set_status("Loaded %d name(s) from %s." % (len(al), self.ip.get().strip()))
        except Exception as e:
            self.set_status("Could not reach the box: %s" % e, True)

    def save(self):
        out = {}
        for _, e1, e2 in self.rows:
            uid = e1.get().strip()
            if uid:
                out[uid] = e2.get().strip()
        try:
            c = self._conn()
            body = json.dumps(out).encode()
            c.request("POST", "/admin/aliases?token=" + self.token.get().strip(),
                      body=body, headers={"Content-Type": "application/json"})
            r = c.getresponse(); data = json.loads(r.read() or b"{}")
            if r.status != 200 or not data.get("ok"):
                return self.set_status("Save failed: " + str(data.get("error", r.status)), True)
            self.set_status("Saved %s name(s). The map updates within a few seconds." % data.get("count"))
        except Exception as e:
            self.set_status("Could not reach the box: %s" % e, True)

    def set_status(self, msg, err=False):
        self.status.config(text=msg, fg="#c00" if err else "#282")


# ======================= Set up a router tab =======================
class SetupTab(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.q = queue.Queue()
        self.running = False
        self.files_dir = tk.StringVar(value=str(default_files_dir()))

        top = tk.Frame(self, padx=10, pady=10); top.pack(fill="x")
        tk.Label(top, text="New box IP").grid(row=0, column=0, sticky="w")
        self.ip = tk.Entry(top, width=16); self.ip.insert(0, DEFAULT_IP); self.ip.grid(row=0, column=1, padx=6)
        tk.Label(top, text="Admin password").grid(row=0, column=2, sticky="w")
        self.pw = tk.Entry(top, width=16, show="*"); self.pw.grid(row=0, column=3, padx=6)
        self.btn = tk.Button(top, text="Set up this box", command=self.start,
                             bg="#1f6feb", fg="white", font=("Segoe UI", 9, "bold"))
        self.btn.grid(row=0, column=4, padx=6)

        # --- Traveler Files folder (bundled beside this app; change only if you moved it) ---
        src = tk.LabelFrame(self, text=" Traveler program files ", padx=10, pady=6)
        src.pack(fill="x", padx=12, pady=(2, 4))
        self.folder_entry = tk.Entry(src, textvariable=self.files_dir, width=52)
        self.folder_entry.grid(row=0, column=0, sticky="w", padx=(2, 4))
        tk.Button(src, text="Change...", command=self._browse).grid(row=0, column=1, sticky="w")

        tk.Label(self, anchor="w", padx=12, fg="#555", justify="left",
                 text="The box needs internet once for the system packages (python3 + libusb, from "
                      "GL/OpenWrt's feed). Everything else is streamed from the Traveler Files folder "
                      "above. Uses the box's own admin password over SSH; it is not saved.").pack(fill="x")

        box = tk.Frame(self, padx=12, pady=6); box.pack(fill="both", expand=True)
        self.log = tk.Text(box, wrap="word", height=16, font=("Consolas", 9),
                           bg="#101418", fg="#d6e2ee", insertbackground="#d6e2ee")
        lsb = tk.Scrollbar(box, command=self.log.yview); self.log.configure(yscrollcommand=lsb.set)
        self.log.pack(side="left", fill="both", expand=True); lsb.pack(side="right", fill="y")
        self.log.configure(state="disabled")
        self.log.tag_config("ok", foreground="#49d17a")
        self.log.tag_config("err", foreground="#ff6b6b")
        self.log.tag_config("step", foreground="#8ab4ff")

        self.after(120, self._drain)

    def _browse(self):
        d = filedialog.askdirectory(title="Pick the Traveler Files folder",
                                    initialdir=self.files_dir.get() or ".")
        if d:
            self.files_dir.set(d)

    def write(self, msg, tag=None):
        self.q.put((msg, tag))

    def _drain(self):
        try:
            while True:
                msg, tag = self.q.get_nowait()
                self.log.configure(state="normal")
                self.log.insert("end", msg + "\n", tag or ())
                self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(120, self._drain)

    def start(self):
        if self.running:
            return
        ip = self.ip.get().strip(); pw = self.pw.get()
        if not ip or not pw:
            return self.write("Enter the box IP and its admin password first.", "err")
        files_dir = self.files_dir.get().strip()
        missing = self._missing_local_files(files_dir)
        if missing is None:
            return self.write("Traveler Files folder not found: %s\nClick \"Change...\" and pick the "
                              "\"Traveler Files\" folder bundled with this app." % files_dir, "err")
        if missing:
            return self.write("These files are missing from %s:\n   %s\nPick the right folder."
                              % (files_dir, "\n   ".join(missing)), "err")
        self.running = True
        self.btn.config(state="disabled", text="Setting up...")
        self.log.configure(state="normal"); self.log.delete("1.0", "end"); self.log.configure(state="disabled")
        threading.Thread(target=self._run, args=(ip, pw, files_dir), daemon=True).start()

    def _missing_local_files(self, files_dir):
        """None if the folder is absent; else a list of bundle_paths not found inside it."""
        base = Path(files_dir)
        if not base.is_dir():
            return None
        missing = []
        for bundle_path, _remote in all_fetch_files():
            if not (base / Path(bundle_path)).is_file():
                missing.append(bundle_path)
        return missing

    def _exec(self, c, cmd):
        """Run one shell command on the box, stream its output to the log, return exit code."""
        _in, out, err = c.exec_command(cmd, timeout=240)
        for line in iter(out.readline, ""):
            if line.strip():
                self.write("   " + line.rstrip())
        rc = out.channel.recv_exit_status()
        etxt = err.read().decode("utf-8", "replace").strip()
        if etxt:
            for line in etxt.splitlines():
                self.write("   " + line)
        return rc

    def _put_file(self, c, local, remote):
        """Stream a local file to the box over SSH with `cat > remote`.
        Uses a plain exec channel, so it works on the box's dropbear SSH
        (which has no SFTP subsystem). Returns the remote exit code."""
        with open(local, "rb") as fh:
            data = fh.read()
        stdin, stdout, stderr = c.exec_command("cat > '%s'" % remote, timeout=120)
        stdin.write(data)
        stdin.flush()
        stdin.channel.shutdown_write()
        rc = stdout.channel.recv_exit_status()
        etxt = stderr.read().decode("utf-8", "replace").strip()
        if etxt:
            for line in etxt.splitlines():
                self.write("   " + line)
        return rc

    def _run(self, ip, pw, files_dir):
        try:
            import paramiko
        except ImportError:
            self.write("The SSH library (paramiko) is not installed. Close this and run the .bat "
                       "again - it installs it automatically. Or: pip install paramiko", "err")
            return self._done()
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.write("Connecting to %s ..." % ip, "step")
            c.connect(ip, username="root", password=pw, timeout=12,
                      look_for_keys=False, allow_agent=False)
            self.write("Connected.", "ok")
            self.write("Files: %s\n" % files_dir, "ok")
        except Exception as e:
            self.write("Could not log in: %s" % e, "err")
            self.write("Check the IP, that it is a fresh GL-MT3000, and the admin password.", "err")
            return self._done()

        try:
            for step in SETUP_STEPS:
                kind, label = step[0], step[1]
                self.write("== %s ==" % label, "step")
                if kind == "sh":
                    self._exec(c, step[2])
                else:
                    _, _, files, pre, post = step
                    if pre:
                        self._exec(c, pre)
                    for bundle_path, remote in files:
                        local = str(Path(files_dir) / Path(bundle_path))
                        rc = self._put_file(c, local, remote)
                        if rc != 0:
                            self.write("   FAILED writing %s (exit %s)" % (remote, rc), "err")
                        else:
                            self.write("   sent %s" % remote)
                    if post:
                        self._exec(c, post)
            # one clean verification read
            _in, out, _e = c.exec_command("ps | grep -c '[p]ython3 /root'", timeout=20)
            count = (out.read().decode().strip() or "0")
            if count.isdigit() and int(count) >= SERVICES_EXPECTED:
                self.write("\nDONE - this box is now a Lookout Traveler. Two services are running "
                           "(radio bridge + map server).", "ok")
                self.write("Plug the radio relay and the Garmin into the hub, then open the "
                           "split-screen map at  http://%s:%d/" % (ip, PORT), "ok")
            else:
                self.write("\nSetup ran, but I only see %s running service(s) (expected %d)."
                           % (count, SERVICES_EXPECTED), "err")
                self.write("Re-run, or check the log above for a download or install error.", "err")
        except Exception as e:
            self.write("Setup stopped: %s" % e, "err")
        finally:
            try: c.close()
            except Exception: pass
            self._done()

    def _done(self):
        self.running = False
        self.after(0, lambda: self.btn.config(state="normal", text="Set up this box"))


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Traveler Manager v" + VERSION)
    root.geometry("600x600")
    nb = ttk.Notebook(root)
    nb.add(SetupTab(nb), text="  Set up a router  ")
    nb.add(NamesTab(nb),  text="  Name units  ")
    nb.pack(fill="both", expand=True)
    root.mainloop()
