"""P25 GPS Tracker - core engine (Claude + Jim, 2026-11-12, v0.14).

v0.9: no engine change - the overlay badge anchors to the screen corner (v0.8's title match
never matched: ArcGIS Earth titles its window after the open workspace, e.g. 'Legacy Workspace').
v0.8: no engine change - overlay found ArcGIS Earth by window title (v0.7's per-process scan
tripped a Defender machine-learning false positive).
v0.7: no engine change - the package gains an on-screen overlay badge (overlay.py, GUI only).
v0.6: the two status lights (radio / ArcGIS Earth) are larger and run even before Start
tracking - radio_reachable() and earth_reachable() are read-only 'start ready' probes.
v0.13: optional own-position source - reads a Garmin USB GPS (garmin_usb.py, if attached) in
v0.14: hardens the Garmin side - rejects bad coordinates (#1), flips the GPS light red +
       alarms when a good fix is lost for 12s (#2), and stays alarm-free during cold-start lock.
its own thread and draws a blue "My position" marker; independent of the radio (either can fail
and the other keeps going). A "Keep me centered" option re-centres the map on your own fixes.
v0.5: markers are firetrucks (red live / amber aging); the view no longer snaps to the first
unit; and the trucks shrink as you zoom out and hide above 200000 ft so wide views stay clean.
v0.4: the retirement time (how long an idle unit stays on the map) is chosen in
the control panel instead of fixed at 2 hours; "Never" keeps units until Stop.
Engine note: Tracker.expire_s may be set live by the GUI; 0 means never retire.

Reverse-engineered on the bench:
  BK radio over USB RNDIS = a networked device at 10.250.46.6. Its GPS relay is a
  TCP service on port 65535. Connect, send the 5-byte subscribe 80 04 18 e4 81, and
  it streams framed messages  80 0d 02 8a 82 00 41 <ASCII NMEA> <checksum> 81  where
  the NMEA is, per received fix:
        $GNGGA,<time>,<lat>,N,<lon>,W,<qual>,<sats>,...   (standard position)
        $PP25,<unit_id>,*cs                               (the sending radio's P25 ID)

v0.3 hardening: keepalive, connection watchdog, visible staleness (amber marker +
age label that ticks), coordinate sanity bounds, and a daily CSV track log.
This module is the engine; the GUI drives run_bridge() in a worker thread.
"""
import re, csv, json, time, math, socket, datetime
from pathlib import Path
from urllib import request, error
try:
    import garmin_usb                      # own-position source (optional; Windows only)
except Exception:
    garmin_usb = None

# ============================ CONFIG ============================
RADIO_IP            = "10.250.46.6"
RADIO_PORT          = 65535
SUBSCRIBE           = bytes.fromhex("80 04 18 e4 81".replace(" ", ""))

ARCGIS_EARTH_API    = "http://localhost:8000"
API_TIMEOUT_SECONDS = 3.0

EXPIRE_SECONDS      = 2 * 60 * 60     # drop a unit's marker after 2 h of silence
STALE_AFTER_MINUTES = 5              # mark a unit "aging" (amber + age label) after this
CENTER_ON_FIRST     = False   # v0.5: never move the operator's view; markers still plot at true location
RECONNECT_SECONDS   = 4
KEEPALIVE_SECONDS   = 20            # re-send SUBSCRIBE this often (0 = off)
WATCHDOG_SECONDS    = 90            # no bytes at all for this long -> force reconnect
REFRESH_SECONDS     = 30            # re-draw aging units so the age/colour stays current

DRAWING_ID_PREFIX   = "AE_P25_"
LABEL_SIZE          = 13
LABEL_COLOR         = [255, 255, 255, 255]
MARKER_SIZE_PX      = 40            # base / max on-screen size (zoomed in)
# ---- LOD: the tracker shrinks the trucks as you zoom out and hides them when too high ----
HIDE_ABOVE_FT       = 200000       # trucks disappear above this eye-altitude (0 = never hide)
ICON_MIN_PX         = 16           # smallest size before they hide
FULL_BELOW_FT       = 6000         # full size at / below this eye-altitude
LOD_POLL_SECONDS    = 0.5          # how often to check your zoom (localhost GET; 0 = LOD off)
# ===============================================================
_HERE        = Path(__file__).resolve().parent
MARKER_ICON  = _HERE / "marker.png"          # fresh (orange)
MARKER_STALE = _HERE / "marker_stale.png"    # aging (amber)
LOG_DIR      = _HERE.parent / "Logs"

# ---- own position from a Garmin USB GPS (optional second source) ----
GARMIN_DRAW_ID   = "AE_P25_ME_GARMIN"
GARMIN_MARKER    = _HERE / "marker_me.png"   # blue "you are here"
GARMIN_LABEL     = "My position"
GARMIN_MARKER_PX = 36
GPS_STALE_SECONDS = 12          # v0.14: after a good fix is lost for this long, the GPS light
                                # goes red + the GPS alarm fires (a frozen position is the danger)


def _coords_ok(lat, lon):
    """v0.14 (#1): reject a corrupt Garmin fix before it moves the marker or the camera."""
    try:
        if lat != lat or lon != lon:        # NaN
            return False
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            return False
        if abs(lat) < 1e-6 and abs(lon) < 1e-6:   # null island (0,0) = no real fix
            return False
        return True
    except Exception:
        return False


# ---------------- NMEA / frame parsing (frame-agnostic) ----------------
_SENTENCE = re.compile(r"\$[^*$\r\n]{2,88}\*[0-9A-Fa-f]{2}")


def _nmea_ok(s):
    body, _, chk = s[1:].partition("*")
    try:
        want = int(chk[:2], 16)
    except ValueError:
        return False
    g = 0
    for c in body:
        g ^= ord(c)
    return g == want


def _to_deg(value, hemi, deg_digits):
    if not value:
        return None
    try:
        d = int(value[:deg_digits]); m = float(value[deg_digits:])
    except ValueError:
        return None
    dd = d + m / 60.0
    return -dd if hemi in ("S", "W") else dd


def _valid_coord(lat, lon):
    if lat is None or lon is None:
        return False
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return False
    if abs(lat) < 1e-6 and abs(lon) < 1e-6:     # null island = no real fix
        return False
    return True


class Report:
    __slots__ = ("unit", "lat", "lon", "alt", "sats", "utc")
    def __init__(self, unit, lat, lon, alt, sats, utc):
        self.unit, self.lat, self.lon, self.alt, self.sats, self.utc = unit, lat, lon, alt, sats, utc


class StreamParser:
    """Feed raw bytes; yields paired (GGA position + PP25 unit id) Reports."""
    def __init__(self):
        self._buf = bytearray()
        self._pending = None

    def feed(self, data: bytes):
        out = []
        self._buf.extend(data)
        text = self._buf.decode("latin-1")
        last_end = 0
        for m in _SENTENCE.finditer(text):
            s = m.group(0); last_end = m.end()
            if not _nmea_ok(s):
                continue
            f = s.split(",")
            tag = f[0][1:]
            if tag.endswith("GGA") and len(f) >= 10:
                lat = _to_deg(f[2], f[3], 2); lon = _to_deg(f[4], f[5], 3)
                if f[6] in ("", "0") or not _valid_coord(lat, lon):
                    self._pending = None
                    continue
                self._pending = {"lat": lat, "lon": lon, "alt": f[9], "sats": f[7], "utc": f[1]}
            elif tag == "PP25" and len(f) >= 2 and f[1]:
                if self._pending is not None:
                    p = self._pending
                    out.append(Report(f[1], p["lat"], p["lon"], p["alt"], p["sats"], p["utc"]))
                    self._pending = None
        if last_end:
            del self._buf[:last_end]
        if len(self._buf) > 8192:
            del self._buf[:-2048]
        return out


# ---------------- ArcGIS Earth Automation API (PRAVE-proven) ----------------
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
            raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')}") from exc
        except (error.URLError, TimeoutError, ConnectionError) as exc:
            raise EarthUnreachable(
                f"ArcGIS Earth Automation API not reachable at {self.base}. In ArcGIS "
                "Earth open Settings > Advanced application settings and enable the "
                "Automation API.") from exc

    def ping(self):
        self._http("GET", "/arcgisearth/camera")

    def get_camera(self):
        return self._http("GET", "/arcgisearth/camera")

    def put_camera(self, payload):
        self._http("PUT", "/arcgisearth/camera", payload)

    def post_drawing(self, payload):
        self._http("POST", "/arcgisearth/drawings", payload)

    def delete_drawing(self, draw_id, ignore_missing=True):
        try:
            self._http("DELETE", f"/arcgisearth/drawings/{draw_id}")
        except RuntimeError as exc:
            t = str(exc)
            if ignore_missing and ("HTTP 404" in t or "not found" in t.lower()):
                return
            raise


# ---------------- Marker manager ----------------
class Unit:
    __slots__ = ("unit", "lat", "lon", "alt", "sats", "seen", "stale")
    def __init__(self, unit, lat, lon, alt, sats, seen):
        self.unit, self.lat, self.lon, self.alt, self.sats = unit, lat, lon, alt, sats
        self.seen, self.stale = seen, False


class Tracker:
    def __init__(self, earth, alias_fn=None, now_fn=time.monotonic, expire_s=EXPIRE_SECONDS,
                 stale_min=STALE_AFTER_MINUTES, center_on_first=CENTER_ON_FIRST):
        self.earth = earth
        self.alias_fn = alias_fn or (lambda uid: None)
        self.now = now_fn
        self.expire_s = expire_s
        self.stale_min = stale_min
        self.center_on_first = center_on_first
        self.units = {}
        self._centered = False
        self.icon_px = MARKER_SIZE_PX   # current on-screen size (LOD)
        self.hidden  = False            # True = zoomed out past the cutoff

    def _draw_id(self, unit):
        return f"{DRAWING_ID_PREFIX}{unit}"

    def _is_stale(self, u):
        return bool(self.stale_min) and (self.now() - u.seen) >= self.stale_min * 60

    def _label(self, u):
        name = self.alias_fn(u.unit) or u.unit
        mins = int((self.now() - u.seen) // 60)
        if not self.stale_min or mins < self.stale_min:
            return name
        if mins < 60:
            return f"{name} · {mins} min"
        return f"{name} · {mins // 60} h {mins % 60:02d} min"

    def _payload(self, u):
        icon = MARKER_STALE if (self._is_stale(u) and MARKER_STALE.is_file()) else MARKER_ICON
        p = {
            "id": self._draw_id(u.unit),
            "visible": True,
            "title": self._label(u),
            "geometry": {"x": u.lon, "y": u.lat, "spatialReference": {"wkid": 4326}},
            "labelSymbol": {"type": "text", "color": LABEL_COLOR, "size": LABEL_SIZE},
        }
        if icon.is_file():
            p["symbol"] = {"type": "picture-marker", "url": str(icon), "size": f"{self.icon_px}px"}
        return p

    def _draw(self, u):
        self.earth.delete_drawing(self._draw_id(u.unit), ignore_missing=True)
        if self.hidden:                       # zoomed out past the cutoff: leave the map clean
            return
        self.earth.post_drawing(self._payload(u))

    def report(self, r: Report):
        new = r.unit not in self.units
        u = self.units.get(r.unit) or Unit(r.unit, r.lat, r.lon, r.alt, r.sats, self.now())
        u.lat, u.lon, u.alt, u.sats, u.seen, u.stale = r.lat, r.lon, r.alt, r.sats, self.now(), False
        self.units[r.unit] = u
        self._draw(u)
        if self.center_on_first and not self._centered:
            self._center(u)
        return ("new" if new else "fix"), u

    def redraw(self, unit):
        u = self.units.get(unit)
        if u is not None:
            self._draw(u)

    def refresh(self):
        """Re-draw aging units so their age label and amber colour stay current.
        Returns the list of units that have just crossed into 'stale'."""
        newly = []
        for u in self.units.values():
            st = self._is_stale(u)
            if st or st != u.stale:
                self._draw(u)
            if st and not u.stale:
                newly.append(u.unit)
            u.stale = st
        return newly

    def _center(self, u):
        try:
            cam = self.earth.get_camera()
            z = cam.get("position", {}).get("z", 1500.0) if isinstance(cam, dict) else 1500.0
            self.earth.put_camera({
                "position": {"x": u.lon, "y": u.lat, "z": z, "spatialReference": {"wkid": 4326}},
                "heading": 0.0, "tilt": 0.0, "roll": 0.0})
            self._centered = True
        except Exception:
            pass

    def _size_for(self, alt_ft):
        if alt_ft <= FULL_BELOW_FT:
            return MARKER_SIZE_PX
        hi = HIDE_ABOVE_FT or (FULL_BELOW_FT * 40)
        f  = (math.log(alt_ft) - math.log(FULL_BELOW_FT)) / (math.log(hi) - math.log(FULL_BELOW_FT))
        f  = max(0.0, min(1.0, f))
        px = round(MARKER_SIZE_PX - f * (MARKER_SIZE_PX - ICON_MIN_PX))
        return (px // 2) * 2                   # even px -> fewer redraws while zooming

    def apply_lod(self, alt_ft):
        """Resize / hide the trucks for the current eye-altitude. Redraws only on a real change."""
        hide = bool(HIDE_ABOVE_FT) and alt_ft > HIDE_ABOVE_FT
        px   = self._size_for(alt_ft)
        if hide == self.hidden and px == self.icon_px:
            return False                       # nothing changed -> no API traffic
        self.hidden, self.icon_px = hide, px
        for u in self.units.values():
            self._draw(u)                      # redraw all at new size, or clear if now hidden
        return True

    def sweep(self):
        if not self.expire_s:          # 0 / None = never retire (user chose "Never")
            return []
        now = self.now()
        expired = [k for k, u in self.units.items() if now - u.seen > self.expire_s]
        for unit in expired:
            self.earth.delete_drawing(self._draw_id(unit), ignore_missing=True)
            del self.units[unit]
        return expired


def csv_log(r: Report):
    try:
        LOG_DIR.mkdir(exist_ok=True)
        path = LOG_DIR / f"p25_track_{datetime.date.today():%Y%m%d}.csv"
        new = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["pc_time", "gps_utc", "unit_id", "lat", "lon", "alt_m", "sats"])
            w.writerow([datetime.datetime.now().isoformat(timespec="seconds"),
                        r.utc, r.unit, f"{r.lat:.6f}", f"{r.lon:.6f}", r.alt, r.sats])
    except Exception:
        pass


def _socket_closed(sock):
    try:
        sock.setblocking(False)
        chunk = sock.recv(1, socket.MSG_PEEK)
        sock.setblocking(True); sock.settimeout(0.5)
        return chunk == b""
    except BlockingIOError:
        sock.setblocking(True); sock.settimeout(0.5)
        return False
    except OSError:
        return True


def radio_reachable(timeout=1.5):
    """Read-only 'start ready' check: can we open the base radio's TCP port?
    Opens and immediately closes - never subscribes or reads. Used by the GUI's
    Radio light while idle so you can see the link is up before Start tracking."""
    try:
        socket.create_connection((RADIO_IP, RADIO_PORT), timeout=timeout).close()
        return True
    except OSError:
        return False


def earth_reachable(client=None, timeout=1.5):
    """Read-only 'start ready' check for the ArcGIS Earth Automation API."""
    try:
        (client or EarthClient()).ping()
        return True
    except Exception:
        return False


def run_bridge(tracker, stop_event, emit, redraw_q=None):
    """Connect/subscribe/parse/draw loop for a worker thread.
    emit(kind, *args): status | fix | stale | expire | log."""
    earth = tracker.earth
    earth_state = {"ok": None}
    def set_earth(ok):                     # drive the 'ArcGIS Earth API ready' light on change
        if ok != earth_state["ok"]:
            earth_state["ok"] = ok; emit("earth", ok)
    emit("radio", False)
    try:
        earth.ping(); emit("status", f"ArcGIS Earth reachable at {earth.base}"); set_earth(True)
    except EarthUnreachable:
        emit("status", "ArcGIS Earth not reachable yet - will keep trying"); set_earth(False)

    while not stop_event.is_set():
        sock = None
        try:
            emit("status", f"connecting to radio {RADIO_IP}:{RADIO_PORT} ..."); emit("radio", False)
            sock = socket.create_connection((RADIO_IP, RADIO_PORT), timeout=6)
            sock.sendall(SUBSCRIBE); sock.settimeout(0.5)
            emit("status", "connected - listening for GPS"); emit("radio", True)
            parser = StreamParser()
            t0 = time.monotonic()
            last_sweep = last_keep = last_refresh = last_data = last_lod = t0
            while not stop_event.is_set():
                try:
                    data = sock.recv(65535)
                except socket.timeout:
                    data = b""
                now = time.monotonic()
                if data:
                    last_data = now
                    if data == b"" and _socket_closed(sock):
                        emit("log", "radio closed the connection"); break
                    for rpt in parser.feed(data):
                        try:
                            kind, _ = tracker.report(rpt)
                            csv_log(rpt)
                            emit("fix", rpt.unit, rpt.lat, rpt.lon, rpt.utc, kind)
                        except EarthUnreachable:
                            emit("status", "ArcGIS Earth not reachable"); set_earth(False)
                        except Exception as exc:
                            emit("log", f"draw error for {rpt.unit}: {exc}")
                elif _socket_closed(sock):
                    emit("log", "radio closed the connection"); break
                if redraw_q is not None:
                    while True:
                        try:
                            tracker.redraw(redraw_q.get_nowait())
                        except Exception:
                            break
                if LOD_POLL_SECONDS and now - last_lod > LOD_POLL_SECONDS:
                    try:
                        cam = earth.get_camera()
                        z = cam.get("position", {}).get("z") if isinstance(cam, dict) else None
                        if z is not None:
                            tracker.apply_lod(z * 3.28084)   # metres -> feet
                        set_earth(True)
                    except EarthUnreachable:
                        set_earth(False)
                    except Exception:
                        pass
                    last_lod = now
                if now - last_refresh > REFRESH_SECONDS:
                    try:
                        for u in tracker.refresh():
                            emit("stale", u)
                    except Exception:
                        pass
                    last_refresh = now
                if now - last_sweep > 30:
                    try:
                        for u in tracker.sweep():
                            emit("expire", u)
                    except Exception:
                        pass
                    last_sweep = now
                if KEEPALIVE_SECONDS and now - last_keep > KEEPALIVE_SECONDS:
                    try: sock.sendall(SUBSCRIBE)
                    except Exception: pass
                    last_keep = now
                if now - last_data > WATCHDOG_SECONDS:
                    emit("log", f"no data for {WATCHDOG_SECONDS}s - reconnecting"); break
        except OSError as exc:
            emit("status", f"connection problem: {exc}")
        finally:
            if sock is not None:
                try: sock.close()
                except Exception: pass
        if stop_event.is_set():
            break
        emit("status", f"reconnecting in {RECONNECT_SECONDS}s (markers stay) ...")
        stop_event.wait(RECONNECT_SECONDS)
    emit("status", "stopped")


# ---------- own-position source: Garmin USB GPS (independent of the radio) ----------
def _draw_me(earth, lat, lon):
    earth.delete_drawing(GARMIN_DRAW_ID, ignore_missing=True)
    p = {"id": GARMIN_DRAW_ID, "visible": True, "title": GARMIN_LABEL,
         "geometry": {"x": lon, "y": lat, "spatialReference": {"wkid": 4326}},
         "labelSymbol": {"type": "text", "color": LABEL_COLOR, "size": LABEL_SIZE}}
    if GARMIN_MARKER.is_file():
        p["symbol"] = {"type": "picture-marker", "url": str(GARMIN_MARKER), "size": f"{GARMIN_MARKER_PX}px"}
    earth.post_drawing(p)


def _recenter_me(earth, lat, lon):
    try:
        cam = earth.get_camera()
        z = cam.get("position", {}).get("z", 2000) if isinstance(cam, dict) else 2000
    except Exception:
        z = 2000
    earth.put_camera({"position": {"x": lon, "y": lat, "z": z, "spatialReference": {"wkid": 4326}},
                      "heading": 0, "tilt": 0})


def run_garmin(state, stop_event, emit):
    """Read the Garmin USB GPS (if one is attached) and draw 'My position'. Runs in its
    own thread: a Garmin failure never stops the P25 radio side, and vice versa. If no
    Garmin module/device is present it simply reports the GPS light off and idles."""
    if garmin_usb is None:
        emit("gps", False)
        return
    earth = EarthClient()
    while not stop_event.is_set():
        gps = garmin_usb.GarminUSB()
        try:
            emit("gps", False)
            gps.open()
            emit("gps", True)          # device open; "acquiring" until the first good fix
            gps.start_pvt()
        except garmin_usb.GarminError as exc:
            emit("gps", False)
            emit("log", f"GPS: {exc}")
            stop_event.wait(4.0)
            continue
        # v0.14 (#2): a plugged-but-not-fixing unit must not look live. Once we've HAD a good
        # fix, losing it for GPS_STALE_SECONDS flips the light red + fires the GPS alarm; a good
        # fix clears it. Before the first fix we stay "acquiring" (green, no alarm, no marker),
        # so a normal cold-start lock doesn't false-alarm. (#3 cheap half: the unit streams PVT
        # ~1/sec even with no lock, so this loop keeps ticking; the thread is a daemon, so a
        # truly silent-but-open unit can't block app close.)
        had_fix = False
        stale = False
        last_good = time.monotonic()
        try:
            while not stop_event.is_set():
                fix = gps.read_fix()
                now = time.monotonic()
                good = bool(fix) and fix["fix"] >= 2 and _coords_ok(fix["lat"], fix["lon"])  # (#1)
                if good:
                    last_good = now
                    had_fix = True
                    if stale:
                        stale = False
                        emit("gps", True)
                        emit("log", "GPS: fix restored")
                    try:
                        _draw_me(earth, fix["lat"], fix["lon"])
                        if getattr(state, "center", False):
                            _recenter_me(earth, fix["lat"], fix["lon"])
                    except EarthUnreachable:
                        pass
                    except Exception:
                        pass
                elif had_fix and not stale and now - last_good > GPS_STALE_SECONDS:
                    stale = True
                    emit("gps", False)
                    emit("log", f"GPS: no fix for {GPS_STALE_SECONDS}s - position is stale")
        except garmin_usb.GarminError:
            emit("gps", False)
            emit("log", "GPS: lost - reconnecting")
        finally:
            gps.stop_pvt()
            gps.close()
        stop_event.wait(3.0)
    try:
        EarthClient().delete_drawing(GARMIN_DRAW_ID, ignore_missing=True)
    except Exception:
        pass
