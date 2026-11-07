"""Real Sim City - Dark Jacksonville (pilot)
Builds a fictional night city on a real town's own lot lines, at its real location, straight into a TPKX
that lies on top of the real map in ArcGIS Earth.

Inputs (beside this file or given on the command line):
  * a Parcel100 GeoJSON cell  - ONLY lot shapes and acreage are used (owner names / addresses are never read)
  * an OpenStreetMap-style street map MBTiles of the same area (raster) - its colours give water, parks,
    roads and the land-use zone (residential, commercial, industrial) of every lot

Each lot is built up by its zone and size (Jim's rule): small residential = houses, bigger = apartments,
industrial = warehouses, commercial = shops, downtown commercial = towers, parks = trees.
Ground is a true top-down map; buildings rise and lean a little up-right so they read as 3D.
WINDOWS are see-through circles where the real world underneath shows through.

py realsim.py [--parcels file.geojson] [--streetmap file.mbtiles] [--zmax 19] [--workers N] [--out file.tpkx]
"""
import io
import math
import multiprocessing as mp
import os
import random
import sqlite3
import sys
import time
import importlib.util
import json

HERE = os.path.dirname(os.path.abspath(__file__))
HALF = 20037508.342789244
RES0 = 156543.03392804097
TILE = 256
GROUP = 8
SS = 2
BUCKET = 400.0                     # object lookup grid, metres

NAME = "Dark Jacksonville"
DOWNTOWN = (-81.6589, 30.3297)     # the clock tower (James Weldon Johnson Park area)
WINDOWS = [                        # (lon, lat, search m): the real world shows through around the BIGGEST lot
    (-81.6791, 30.3093, 500.0),    # within 'search' metres of the point - Memorial Park, Riverside
    (-81.6373, 30.3239, 500.0),    # the stadium
]
LEAN = (0.30, 0.62)                # screen shift per metre of height: right, up
PEOPLE_SCALE = 0.20                # person drawn ~4.4 m tall (2.5x real: toy-city look)
HEIGHT_X = 2.0                     # buildings drawn twice their real height (toy-city look)
G = {}


# ---------------------------------------------------------------- geometry helpers

def lonlat_to_m(lon, lat):
    return HALF * lon / 180.0, HALF * math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / math.pi


def m_to_lonlat(x, y):
    return x / HALF * 180.0, math.degrees(2 * math.atan(math.exp(y / HALF * math.pi)) - math.pi / 2)


def area(poly):
    s = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def centroid(poly):
    a = area(poly)
    if abs(a) < 1e-9:
        return sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
    cx = cy = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        f = x1 * y2 - x2 * y1
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    return cx / (6 * a), cy / (6 * a)


def simplify(pts, tol):
    if len(pts) < 4:
        return pts
    def rdp(a, b):
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1e-9
        best, bi = -1, -1
        for i in range(a + 1, b):
            d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / L
            if d > best:
                best, bi = d, i
        if best > tol:
            return rdp(a, bi)[:-1] + rdp(bi, b)
        return [pts[a], pts[b]]
    out = rdp(0, len(pts) - 1)
    return out if len(out) >= 3 else pts


def inside(pt, poly):
    x, y = pt
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            c = not c
        j = i
    return c


def oriented_rect(poly):
    """centre, unit axis of the longest edge, half-lengths along/across"""
    best, ang = 0, 0.0
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        L = math.hypot(x2 - x1, y2 - y1)
        if L > best:
            best, ang = L, math.atan2(y2 - y1, x2 - x1)
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    us = [p[0] * ux + p[1] * uy for p in poly]
    vs = [p[0] * vx + p[1] * vy for p in poly]
    cu, cv = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
    cx, cy = cu * ux + cv * vx, cu * uy + cv * vy
    return (cx, cy), (ux, uy), (max(us) - min(us)) / 2, (max(vs) - min(vs)) / 2


def rect(c, u, a, b):
    (cx, cy), (ux, uy) = c, u
    vx, vy = -uy, ux
    return [(cx + ux * a + vx * b, cy + uy * a + vy * b), (cx - ux * a + vx * b, cy - uy * a + vy * b),
            (cx - ux * a - vx * b, cy - uy * a - vy * b), (cx + ux * a - vx * b, cy + uy * a - vy * b)]


# ---------------------------------------------------------------- land use from the street map colours

PAL = [  # (rgb, class)
    ((171, 210, 225), "water"), ((170, 211, 223), "water"),
    ((223, 223, 223), "res"), ((224, 223, 221), "res"),
    ((235, 218, 234), "ind"), ((235, 219, 232), "ind"),
    ((242, 218, 217), "com"), ((255, 214, 209), "com"),
    ((174, 208, 158), "park"), ((200, 250, 204), "park"), ((205, 235, 176), "park"), ((173, 209, 158), "park"), ((170, 203, 175), "park"),
    ((255, 255, 229), "school"),
    ((255, 255, 255), "road"), ((255, 254, 253), "road"), ((247, 250, 191), "road"), ((252, 214, 164), "road"),
    ((232, 146, 162), "road"), ((249, 178, 156), "road"), ((228, 109, 113), "road"),
    ((217, 208, 203), "bldg"), ((217, 208, 201), "bldg"),
    ((242, 239, 232), "bg"), ((242, 239, 233), "bg"), ((238, 238, 238), "bg"),
]
CLASSES = ["water", "res", "ind", "com", "park", "school", "road", "bldg", "bg", "other"]


def classify(arr):
    """arr: HxWx3 uint8 -> HxW class index (CLASSES), 'other' when no palette colour is near"""
    import numpy as np
    cols = np.array([p[0] for p in PAL], dtype=np.int32)
    idx = np.array([CLASSES.index(p[1]) for p in PAL])
    out = np.empty(arr.shape[:2], dtype=np.int8)
    for y0 in range(0, arr.shape[0], 128):            # in strips: memory stays small
        a = arr[y0:y0 + 128].astype(np.int32)
        d = ((a[:, :, None, :] - cols[None, None, :, :]) ** 2).sum(-1)
        o = idx[d.argmin(-1)]
        o[d.min(-1) > 18 * 18] = CLASSES.index("other")
        out[y0:y0 + 128] = o
    return out


class StreetMap:
    def __init__(self, path):
        self.path = path
        self.db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
        self.cache = {}

    def tile(self, z, tx, ty):
        key = (z, tx, ty)
        if key not in self.cache:
            from PIL import Image
            row = self.db.execute("SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                                  (z, tx, (1 << z) - 1 - ty)).fetchone()
            self.cache[key] = Image.open(io.BytesIO(row[0])).convert("RGB") if row else None
            if len(self.cache) > 600:
                self.cache.pop(next(iter(self.cache)))
        return self.cache[key]


from pathlib import Path


# ---------------------------------------------------------------- the city

class City:
    def __init__(self, parcels_path, streetmap_path, seed=7):
        import numpy as np
        self.rnd = random.Random(seed)
        self.sm = StreetMap(streetmap_path)
        b = [float(v) for v in dict(self.sm.db.execute("SELECT name, value FROM metadata").fetchall())["bounds"].split(",")]
        with open(parcels_path, encoding="utf-8") as f:
            data = json.load(f)
        lons, lats = [], []
        for ft in data["features"][:2000]:
            if ft["geometry"]["type"] != "Polygon":
                continue
            for pt in ft["geometry"]["coordinates"][0]:
                lons.append(pt[0]); lats.append(pt[1])
        # the area = parcel cell box (rounded to 0.1 degree) inside the street map's bounds
        lons.sort(); lats.sort()
        px0, py0 = math.floor(lons[len(lons) // 2] * 10) / 10, math.floor(lats[len(lats) // 2] * 10) / 10   # the 0.1-degree Master 4 cell
        self.area = (max(px0, b[0]), max(py0, b[1]), min(px0 + 0.1, b[2]), min(py0 + 0.1, b[3]))
        lo0, la0, lo1, la1 = self.area
        self.XMIN, self.YMIN = lonlat_to_m(lo0, la0)
        self.XMAX, self.YMAX = lonlat_to_m(lo1, la1)
        self.W, self.H = self.XMAX - self.XMIN, self.YMAX - self.YMIN
        self.MS = 1.0 / math.cos(math.radians((la0 + la1) / 2))   # ground metre -> Mercator metre
        # land-use grid from the z16 street map (2.4 m per cell)
        self.z16 = 16
        self.res16 = RES0 / (1 << 16)
        tx0, ty0 = self.txy(self.XMIN, self.YMAX, 16)
        tx1, ty1 = self.txy(self.XMAX, self.YMIN, 16)
        from PIL import Image
        mos = Image.new("RGB", ((tx1 - tx0 + 1) * TILE, (ty1 - ty0 + 1) * TILE), (242, 239, 232))
        for tx in range(tx0, tx1 + 1):
            for ty in range(ty0, ty1 + 1):
                im = self.sm.tile(16, tx, ty)
                if im:
                    mos.paste(im, ((tx - tx0) * TILE, (ty - ty0) * TILE))
        self.grid = classify(np.asarray(mos))
        self.gx0 = -HALF + tx0 * TILE * self.res16
        self.gy0 = HALF - ty0 * TILE * self.res16
        self.objs = []
        self.lots = []
        self.names = list(SIGN_NAMES)
        self.rnd.shuffle(self.names)
        self.build(data)

    # picture coordinates (metres from the area's top-left, y down)
    def P(self, lon, lat):
        x, y = lonlat_to_m(lon, lat)
        return x - self.XMIN, self.YMAX - y

    def txy(self, mx, my, z):
        n = 1 << z
        return int((mx + HALF) / (2 * HALF) * n), int((HALF - my) / (2 * HALF) * n)

    def cls_at(self, px, py, r=0):
        """land-use class at a picture point (majority over a (2r+1)^2 patch, ignoring road/bldg/bg/other)"""
        gx = int((self.XMIN + px - self.gx0) / self.res16)
        gy = int((self.gy0 - (self.YMAX - py)) / self.res16)
        H, W = self.grid.shape
        if r == 0:
            if 0 <= gx < W and 0 <= gy < H:
                return CLASSES[self.grid[gy, gx]]
            return "other"
        votes = {}
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = gx + dx, gy + dy
                if 0 <= x < W and 0 <= y < H:
                    c = CLASSES[self.grid[y, x]]
                    votes[c] = votes.get(c, 0) + 1
        for skip in ("road", "bldg", "bg", "other"):
            votes.pop(skip, None)
        return max(votes, key=votes.get) if votes else None

    def windows(self):
        """each window = the biggest lot within the search distance of its point, as a circle around it"""
        out = []
        for lon, lat, search in WINDOWS:
            x, y = self.P(lon, lat)
            best = None
            for ring, cls in self.lots:
                cx, cy = centroid(ring)
                if math.hypot(cx - x, cy - y) <= search * self.MS:
                    a = abs(area(ring))
                    if best is None or a > best[0]:
                        best = (a, cx, cy, ring)
            if best:
                a, cx, cy, ring = best
                rad = max(math.hypot(px - cx, py - cy) for px, py in ring) * 1.05
                out.append((cx, cy, rad))
        return out

    def add(self, key, bbox, fn, *args):
        self.objs.append((key, len(self.objs), bbox, fn, args))

    def add_poly_obj(self, poly, h, fn, *args, key=None):
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        hx, hy = h * LEAN[0], h * LEAN[1]
        self.add(key if key is not None else max(ys), (min(xs) - 4, min(ys) - hy - 6, max(xs) + hx + 6, max(ys) + 6), fn, *args)

    def build(self, data):
        R = self.rnd
        dcx, dcy = self.P(*DOWNTOWN)
        for ft in data["features"]:
            g = ft["geometry"]
            if g["type"] != "Polygon":
                continue
            acres = ft["properties"].get("Acres") or 0.0          # only shape + acreage are used
            ring = [self.P(pt[0], pt[1]) for pt in g["coordinates"][0]]
            if ring and ring[0] == ring[-1]:
                ring = ring[:-1]
            if len(ring) < 3:
                continue
            ring = simplify(ring, 0.8)
            a = area(ring)
            if a > 0:
                ring = ring[::-1]                                 # screen y is down: keep one winding
            cx, cy = centroid(ring)
            if not (0 <= cx <= self.W and 0 <= cy <= self.H):
                continue
            cls = self.cls_at(cx, cy, 2)
            if cls == "water":
                continue
            dist = math.hypot(cx - dcx, cy - dcy) / self.MS          # ground metres from downtown
            if cls is None:                                          # no land-use colour on the map
                cls = "com" if dist < 2000 else "res"
            elif cls == "res" and dist < 700:
                cls = "com"
            self.lots.append((ring, cls))
            self.add(cy - 1e6, (min(p[0] for p in ring) - 2, min(p[1] for p in ring) - 2, max(p[0] for p in ring) + 2, max(p[1] for p in ring) + 2),
                     draw_lot, ring, cls, R.random())
            self.build_lot(ring, cls, acres, dist, (cx, cy))
        self.street_life()
        # the clock tower
        self.add_poly_obj(rect((dcx, dcy), (1, 0), 9 * self.MS, 9 * self.MS), 290 * self.MS, draw_clocktower, (dcx, dcy), self.MS)

    def build_lot(self, ring, cls, acres, dist, c):
        R = self.rnd
        MS = self.MS
        (rc, ru, ra, rb) = oriented_rect(ring)
        if cls == "park":
            n = min(40, int(abs(area(ring)) / (400 * MS * MS)) + 1)
            for _ in range(n):
                p = (rc[0] + ru[0] * R.uniform(-ra, ra) - ru[1] * R.uniform(-rb, rb), rc[1] + ru[1] * R.uniform(-ra, ra) + ru[0] * R.uniform(-rb, rb))
                if inside(p, ring):
                    self.add(p[1], (p[0] - 12, p[1] - 30, p[0] + 16, p[1] + 6), draw_tree, p, R.uniform(3.5, 6.5) * MS, R.random())
            return
        big = acres > 6
        if cls == "res":
            if acres < 0.6:
                kind, cov, floors = "house", 0.58, R.choice((1, 1, 2))
            else:
                kind, cov, floors = "apart", 0.62, R.randint(3, 5)
        elif cls == "ind":
            kind, cov, floors = "warehouse", 0.78, 2
        elif cls == "school":
            kind, cov, floors = "school", 0.5, R.randint(2, 3)
        else:  # commercial / unknown
            if dist < 900 and R.random() < 0.55 * (1 - dist / 900) + 0.08:
                kind, cov, floors = "tower", 0.66, max(8, int(R.uniform(10, 34) * (1 - dist / 1200) + R.uniform(0, 6)))
            elif dist < 2200:
                kind, cov, floors = "block", 0.7, R.randint(2, 7)
            else:
                kind, cov, floors = "shop", 0.62, R.randint(1, 2)
        if big and kind in ("warehouse", "block", "shop", "school", "apart"):
            # several buildings on a big lot
            nx = max(1, min(6, int(ra / (35 * MS))))
            ny = max(1, min(4, int(rb / (30 * MS))))
            for i in range(nx):
                for j in range(ny):
                    u = (i + 0.5) / nx * 2 - 1
                    v = (j + 0.5) / ny * 2 - 1
                    cc = (rc[0] + ru[0] * u * ra - ru[1] * v * rb, rc[1] + ru[1] * u * ra + ru[0] * v * rb)
                    if inside(cc, ring) and R.random() < 0.8:
                        poly = rect(cc, ru, ra / nx * 0.75, rb / ny * 0.7)
                        self.add_building(poly, kind, floors)
            return
        f = math.sqrt(cov)
        poly = rect(rc, ru, ra * f, rb * f)
        if kind == "house":
            poly = rect(rc, ru, min(ra * 0.62, 11 * MS), min(rb * 0.55, 8 * MS))
            if R.random() < 0.5:
                p = (rc[0] - ru[1] * rb * 0.7, rc[1] + ru[0] * rb * 0.7)
                if inside(p, ring):
                    self.add(p[1], (p[0] - 12, p[1] - 30, p[0] + 16, p[1] + 6), draw_tree, p, R.uniform(3, 5) * MS, R.random())
        self.add_building(poly, kind, floors)

    def add_building(self, poly, kind, floors):
        R = self.rnd
        MS = self.MS
        hx = HEIGHT_X if floors <= 3 else max(1.0, HEIGHT_X - (floors - 3) * 0.15)   # low buildings exaggerated, towers true
        fh = (3.6 if kind != "warehouse" else 4.5) * MS * hx
        h = floors * fh
        wall = {"house": R.choice([(96, 70, 58), (84, 80, 76), (110, 96, 80), (74, 70, 72), (100, 76, 66)]),
                "apart": R.choice([(96, 56, 46), (86, 76, 66), (72, 66, 64)]),
                "warehouse": R.choice([(70, 64, 58), (58, 60, 62), (82, 66, 54)]),
                "school": (92, 72, 60),
                "tower": R.choice([(70, 72, 80), (82, 78, 72), (60, 66, 70), (92, 86, 76), (52, 58, 66)]),
                "block": R.choice([(92, 70, 60), (78, 74, 70), (66, 64, 68), (100, 84, 68)]),
                "shop": R.choice([(90, 78, 66), (70, 70, 74), (96, 66, 58)])}[kind]
        lit = {"house": 0.45, "apart": 0.35, "warehouse": 0.08, "school": 0.1, "tower": 0.3, "block": 0.3, "shop": 0.5}[kind]
        sign = None
        if kind in ("shop", "block", "tower") and self.names and R.random() < (0.35 if kind == "shop" else 0.15):
            sign = (self.names.pop(), R.choice(NEON))
        crown = R.choice((None, "spire", "lit", "tank")) if kind == "tower" and floors > 12 else ("tank" if kind == "apart" and R.random() < 0.3 else None)
        self.add_poly_obj(poly, h + (40 * MS if crown == "spire" else 8 * MS), draw_building, poly, h, fh, wall, lit, kind, sign, crown, R.random())

    def street_life(self):
        """people, parked cars and lamps along lot fronts (the edges that face a street)"""
        R = self.rnd
        MS = self.MS
        dcx, dcy = self.P(*DOWNTOWN)
        for ring, cls in self.lots:
            for i in range(len(ring)):
                (x1, y1), (x2, y2) = ring[i], ring[(i + 1) % len(ring)]
                L = math.hypot(x2 - x1, y2 - y1)
                if L < 8 * MS:
                    continue
                nx, ny = (y2 - y1) / L, -(x2 - x1) / L               # outward normal (ring winding fixed above)
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                if self.cls_at(mx + nx * 7 * MS, my + ny * 7 * MS) not in ("road", "bg", "other"):
                    nx, ny = -nx, -ny
                    if self.cls_at(mx + nx * 7 * MS, my + ny * 7 * MS) not in ("road", "bg", "other"):
                        continue
                dist = math.hypot(mx - dcx, my - dcy) / MS
                dens = 0.06 if dist < 900 else 0.03 if dist < 2500 else 0.012
                if cls in ("com",):
                    dens *= 1.8
                for _ in range(int(L / MS * dens + R.random())):
                    t = R.random()
                    off = R.uniform(1.5, 3.5) * MS
                    p = (x1 + (x2 - x1) * t + nx * off, y1 + (y2 - y1) * t + ny * off)
                    self.add_person(p)
                if R.random() < L / MS / 45:
                    t = R.random()
                    p = (x1 + (x2 - x1) * t + nx * 4.5 * MS, y1 + (y2 - y1) * t + ny * 4.5 * MS)
                    self.add(p[1], (p[0] - 14 * MS, p[1] - 14 * MS, p[0] + 14 * MS, p[1] + 8 * MS), draw_car, p, ((x2 - x1) / L, (y2 - y1) / L), MS, R.random())
                if R.random() < L / MS / 40:
                    t = R.random()
                    p = (x1 + (x2 - x1) * t + nx * 2.5 * MS, y1 + (y2 - y1) * t + ny * 2.5 * MS)
                    r = 14 * MS
                    self.add(p[1] - 0.5, (p[0] - r, p[1] - r * 0.8, p[0] + r, p[1] + r * 0.8), draw_pool, p, r)
                    self.add(p[1] + 0.01, (p[0] - 4, p[1] - 12 * MS - 6, p[0] + 10 * MS, p[1] + 4), draw_lamp, p, MS)

    def add_person(self, p):
        L = G["E"].noir_look(self.rnd, s=PEOPLE_SCALE * self.MS)
        self.add(p[1], (p[0] - 2, p[1] - 6 * self.MS, p[0] + 2, p[1] + 1), G["E"].person, p[0], p[1], L)


SIGN_NAMES = ["THE LANTERN", "BLUE MOTH", "OWL & ANCHOR", "RIVER ROOM", "THE PALMETTO", "NIGHTJAR", "CLOVE & SMOKE",
              "THE CORMORANT", "SILVER SPOON", "LAST CALL", "THE BRIDGEWAY", "HARBOR LIGHTS", "MOONGATE", "THE TIDEWATER",
              "COPPER KETTLE", "STARLINE", "THE GULL", "BLACK HERON", "ST. JOHNS GRILL", "THE RAINCOAT", "MIDNIGHT OIL",
              "THE MAGNOLIA", "TWIN LAMPS", "THE FERRYMAN", "ORANGE GROVE", "THE KINGFISHER", "VELVET ROPE", "THE OSPREY",
              "RAINY DAY", "PELICAN BAR", "THE NIGHT DESK", "OLD SAWMILL", "HALF MOON", "THE PIER", "GASLIGHT", "THE SKIFF",
              "IRON BRIDGE", "THE MANATEE", "CYPRESS", "THE SALT HOUSE", "WHITE HERON", "THE ANCHOR", "FOGHORN", "THE DOCKHAND",
              "LAMPLIGHTER", "THE RIVERBOAT", "SPANISH MOSS", "THE WHARF", "TURPENTINE", "STEAMBOAT", "THE OYSTER", "NIGHT TRAIN"]
NEON = [(255, 60, 90), (60, 220, 255), (255, 170, 40), (190, 90, 255), (80, 255, 140)]


# ---------------------------------------------------------------- drawing (picture units = Mercator metres)

def lean(p, h):
    return p[0] + h * LEAN[0], p[1] - h * LEAN[1]


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


def draw_lot(ctx, ring, cls, r):
    col = {"res": (30, 40, 32), "ind": (40, 40, 40), "com": (50, 50, 54), "school": (36, 46, 38),
           "park": (24, 38, 28), "other": (44, 44, 48)}.get(cls, (44, 44, 48))
    ctx.poly(ring, col, (66, 66, 70))


def draw_building(ctx, poly, h, fh, wall, lit, kind, sign, crown, seed):
    rnd = random.Random(seed)
    OUT = (12, 12, 16)
    n = len(poly)
    L = (LEAN[0], -LEAN[1])
    faces = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        el = math.hypot(ex, ey) or 1
        nx, ny = ey / el, -ex / el
        if nx * L[0] + ny * L[1] > 0:     # make sure the normal points outward for this winding
            pass
        faces.append((a, b, nx, ny, el))
    # outward normals: polygon is clockwise in screen (y down) when area > 0 after the flip above
    sgn = 1 if area(poly) < 0 else -1
    for a, b, nx, ny, el in faces:
        nx, ny = nx * sgn, ny * sgn
        if nx * L[0] + ny * L[1] >= 0:    # faces turned away from the viewer are hidden
            continue
        light = 0.72 + 0.28 * max(0.0, -nx * 0.7 + ny * 0.7)
        col = shade(wall, light)
        ctx.poly([a, b, lean(b, h), lean(a, h)], col, OUT)
        # windows
        floors = int(h / fh)
        nwin = max(1, int(el / (fh * 0.95)))
        for f in range(floors):
            z0 = f * fh + fh * 0.32
            z1 = z0 + fh * 0.42
            for w in range(nwin):
                u0 = (w + 0.25) / nwin
                u1 = (w + 0.75) / nwin
                on = rnd.random() < lit
                wc = (255, 210, 130) if on else (26, 32, 44)
                p0 = (a[0] + (b[0] - a[0]) * u0, a[1] + (b[1] - a[1]) * u0)
                p1 = (a[0] + (b[0] - a[0]) * u1, a[1] + (b[1] - a[1]) * u1)
                ctx.poly([lean(p0, z0), lean(p1, z0), lean(p1, z1), lean(p0, z1)], wc if on else shade(wc, light), None)
        if kind == "shop":
            ctx.poly([a, b, lean(b, fh * 0.75), lean(a, fh * 0.75)], (255, 206, 120, 70), None)
    roof = [lean(p, h) for p in poly]
    rc = shade(wall, 0.62)
    ctx.poly(roof, rc, OUT)
    cx = sum(p[0] for p in roof) / n
    cy = sum(p[1] for p in roof) / n
    if kind == "house":
        # ridge along the long axis
        (c0, u, ra, rb) = oriented_rect(poly)
        r0, r1 = lean((c0[0] + u[0] * ra * 0.8, c0[1] + u[1] * ra * 0.8), h), lean((c0[0] - u[0] * ra * 0.8, c0[1] - u[1] * ra * 0.8), h)
        ctx.line([r0, r1], shade(wall, 0.4), 0.6)
    if crown == "spire":
        ctx.poly([(cx - 3, cy), (cx + 3, cy), (cx + 0.5 * 40 * LEAN[0], cy - 40 * LEAN[1])], (150, 140, 120), OUT)
        ctx.ell(cx + 40 * LEAN[0] * 0.5, cy - 40 * LEAN[1], 1.5, 1.5, (255, 40, 40))
    elif crown == "lit":
        ctx.poly([(cx + (p[0] - cx) * 0.35, cy + (p[1] - cy) * 0.35) for p in roof], (190, 150, 90), OUT)
        for i in range(4, 0, -1):
            ctx.ell(cx, cy, 6.0 * i, 5.0 * i, (255, 210, 140, 10))
    elif crown == "tank":
        ctx.ell(cx, cy - 2, 2.5, 1.6, (110, 84, 64), OUT)
    if sign:
        txt, col = sign
        bx = min(p[0] for p in roof)
        by = max(p[1] for p in roof)
        neon(ctx, (bx + cx) / 2, (by + cy) / 2, txt, col, 3.2)


def neon(ctx, x, y, text, col, size_m):
    from PIL import ImageFont
    k = ctx.k
    try:
        f = ImageFont.load_default(size=max(6, int(size_m * k)))
    except Exception:
        f = ImageFont.load_default()
    tw = ctx.d.textlength(text, font=f)
    X, Y = (x - ctx.ox) * k - tw / 2, (y - ctx.oy) * k - size_m * k * 0.6
    ctx.d.ellipse([X - size_m * k, Y - size_m * k * 0.8, X + tw + size_m * k, Y + size_m * k * 2], fill=(col[0], col[1], col[2], 30))
    ctx.d.text((X, Y), text, font=f, fill=tuple(min(255, v + 80) for v in col))


def draw_tree(ctx, p, r, seed):
    x, y = p
    ctx.ell(x + r * 0.5, y + r * 0.2, r * 1.1, r * 0.6, (0, 0, 8, 80))
    ctx.ell(x, y - r * 0.6, r, r * 0.9, (26, 46, 32), (12, 20, 14))
    ctx.ell(x - r * 0.3, y - r * 0.9, r * 0.55, r * 0.5, (36, 60, 40))


def draw_pool(ctx, p, r):
    for i in range(7, 0, -1):
        f = (i / 7) ** 0.8
        ctx.ell(p[0], p[1], r * f, r * f * 0.8, (255, 206, 120, 9))


def draw_lamp(ctx, p, MS):
    x, y = p
    top = lean(p, 9 * MS)
    ctx.line([p, top], (18, 18, 22), 0.5)
    ctx.ell(top[0], top[1], 1.0 * MS, 0.8 * MS, (255, 232, 170))
    for i in range(4, 0, -1):
        ctx.ell(top[0], top[1], 3.5 * MS * i / 4, 3 * MS * i / 4, (255, 206, 120, 22))


def draw_car(ctx, p, d, MS, seed):
    rnd = random.Random(seed)
    col = rnd.choice([(20, 20, 22), (70, 20, 24), (30, 40, 64), (80, 80, 84), (100, 90, 60), (24, 54, 44), (150, 130, 40)])
    ux, uy = d
    vx, vy = -uy, ux
    a, b = 4.8 * MS, 2.1 * MS
    base = [(p[0] + ux * a + vx * b, p[1] + uy * a + vy * b), (p[0] - ux * a + vx * b, p[1] - uy * a + vy * b),
            (p[0] - ux * a - vx * b, p[1] - uy * a - vy * b), (p[0] + ux * a - vx * b, p[1] + uy * a - vy * b)]
    h = 3.0 * MS
    ctx.poly([(q[0] + 1.5, q[1] + 1.0) for q in base], (0, 0, 8, 90), None)
    top = [lean(q, h) for q in base]
    for i in range(4):
        q0, q1 = base[i], base[(i + 1) % 4]
        ctx.poly([q0, q1, lean(q1, h), lean(q0, h)], shade(col, 0.75), (10, 10, 12))
    ctx.poly(top, col, (10, 10, 12))
    cab = [lean((p[0] + ux * a * f1 + vx * b * f2, p[1] + uy * a * f1 + vy * b * f2), h + 1.6 * MS)
           for f1, f2 in ((0.35, 0.8), (-0.45, 0.8), (-0.45, -0.8), (0.35, -0.8))]
    ctx.poly(cab, (120, 150, 170), (10, 10, 12))
    hl = lean((p[0] + ux * a, p[1] + uy * a), 1.2 * MS)
    ctx.ell(hl[0], hl[1], 0.9 * MS, 0.9 * MS, (255, 240, 190))


def draw_clocktower(ctx, c, MS):
    s = 9 * MS
    base = rect(c, (1, 0), s, s)
    h = 230 * MS
    stone = (96, 90, 84)
    draw_building(ctx, base, h, 4 * MS, stone, 0.25, "tower", None, None, 3)
    # clock faces on the two visible sides, near the top
    for (fx, fy) in ((0, 1), (-1, 0)):
        cpt = (c[0] + fx * s, c[1] + fy * s)
        q = lean(cpt, h - 18 * MS)
        ctx.ell(q[0], q[1], 6 * MS, 6 * MS, (240, 232, 210), (12, 12, 16))
        ctx.line([q, (q[0], q[1] - 4.5 * MS)], (20, 20, 20), 0.7)
        ctx.line([q, (q[0] + 3.5 * MS * (1 if fx == 0 else -1), q[1] + 1.5 * MS)], (20, 20, 20), 0.7)
        for i in range(4, 0, -1):
            ctx.ell(q[0], q[1], 6 * MS + i * 2.5 * MS, 6 * MS + i * 2.5 * MS, (255, 230, 170, 10))
    top = [lean(p, h) for p in base]
    tcx = sum(p[0] for p in top) / 4
    tcy = sum(p[1] for p in top) / 4
    tip = lean((c[0], c[1]), h + 45 * MS)
    ctx.poly([top[0], top[1], tip], (60, 40, 36), (12, 12, 16))
    ctx.poly([top[1], top[2], tip], (80, 52, 44), (12, 12, 16))
    ctx.ell(tip[0], tip[1], 1.6 * MS, 1.6 * MS, (255, 40, 40))


# ---------------------------------------------------------------- tiles

def tile_range(bounds, z):
    xmin, xmax, ymin, ymax = bounds
    n = 1 << z
    w = HALF * 2.0
    eps = 1e-9
    def txy(x, y):
        return max(0, min(n - 1, int(math.floor(((x + HALF) / w) * n)))), max(0, min(n - 1, int(math.floor(((HALF - y) / w) * n))))
    x0, y0 = txy(xmin, ymax)
    x1, y1 = txy(xmax - eps, ymin + eps)
    return x0, x1, y0, y1


def load_engine():
    os.environ.setdefault("DCC_N", "60")
    spec = importlib.util.spec_from_file_location("darkcity", os.path.join(HERE, "darkcity.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["darkcity"] = mod
    spec.loader.exec_module(mod)
    return mod


def init_draw(parcels, streetmap, zmax, quality, seed):
    E = load_engine()
    G["E"] = E
    city = City(parcels, streetmap, seed)
    objs = sorted(city.objs, key=lambda o: (o[0], o[1]))
    buckets = {}
    for idx, o in enumerate(objs):
        bx0, by0, bx1, by1 = o[2]
        for i in range(int(bx0 // BUCKET), int(bx1 // BUCKET) + 1):
            for j in range(int(by0 // BUCKET), int(by1 // BUCKET) + 1):
                buckets.setdefault((i, j), []).append(idx)
    G.update(city=city, objs=objs, buckets=buckets, zmax=zmax, quality=quality, wins=city.windows())


GROUND = {"water": (11, 19, 32), "park": (24, 38, 28), "road": (42, 44, 52)}
BASE = (30, 32, 38)


def ground_image(z, tx0, ty0, ntx, nty):
    """the street map's tiles for this block, recoloured to night ground (water, parks, roads)"""
    import numpy as np
    from PIL import Image
    city = G["city"]
    out = np.zeros((nty * TILE, ntx * TILE, 3), dtype=np.uint8)
    out[:] = BASE
    sz = min(z, 18)
    f = 1 << (z - sz)
    for i in range(ntx):
        for j in range(nty):
            tx, ty = tx0 + i, ty0 + j
            im = city.sm.tile(sz, tx // f, ty // f)
            if im is None:
                continue
            if f > 1:
                s = TILE // f
                im = im.crop(((tx % f) * s, (ty % f) * s, (tx % f + 1) * s, (ty % f + 1) * s)).resize((TILE, TILE), Image.NEAREST)
            cl = classify(np.asarray(im))
            blk = out[j * TILE:(j + 1) * TILE, i * TILE:(i + 1) * TILE]
            for name, col in GROUND.items():
                blk[cl == CLASSES.index(name)] = col
    return Image.fromarray(out)


def rain(ctx, ox, oy, pw, ph):
    rnd = random.Random(int(ox * 7 + oy * 13))
    n = int(pw * ph / 900)
    for _ in range(n):
        x, y = ox + rnd.random() * pw, oy + rnd.random() * ph
        ctx.line([(x, y), (x - 1.2, y + 5)], (170, 180, 200, 45), 0.3)


def draw_group(task):
    import numpy as np
    from PIL import Image
    tx0, ty0 = task
    city, E = G["city"], G["E"]
    z = G["zmax"]
    n = 1 << z
    res = RES0 / n
    bounds = (city.XMIN, city.XMAX, city.YMIN, city.YMAX)
    x0, x1, y0, y1 = tile_range(bounds, z)
    gx0 = -HALF + tx0 * TILE * res
    gy0 = HALF - ty0 * TILE * res
    ox, oy = gx0 - city.XMIN, city.YMAX - gy0
    side = GROUP * TILE * res
    px = GROUP * TILE * SS
    k = px / side
    img = ground_image(z, tx0, ty0, GROUP, GROUP).resize((px, px), Image.NEAREST)   # solid RGB: see-through light blends
    ctx = E.Ctx(img, ox, oy, k)
    found = set()
    for i in range(int(ox // BUCKET), int((ox + side) // BUCKET) + 1):
        for j in range(int(oy // BUCKET), int((oy + side) // BUCKET) + 1):
            found.update(G["buckets"].get((i, j), ()))
    for idx in sorted(found):
        o = G["objs"][idx]
        b = o[2]
        if b[2] < ox or b[0] > ox + side or b[3] < oy or b[1] > oy + side:
            continue
        o[3](ctx, *o[4])
    rain(ctx, ox, oy, side, side)
    img = img.reduce(SS)
    # see-through: outside the area and inside the windows
    W = GROUP * TILE
    yy, xx = np.mgrid[0:W, 0:W]
    mx = ox + (xx + 0.5) * res
    my = oy + (yy + 0.5) * res
    alpha = np.full((W, W), 255.0)
    alpha[(mx < 0) | (mx > city.W) | (my < 0) | (my > city.H)] = 0
    for wx, wy, wr in G["wins"]:
        d = np.hypot(mx - wx, my - wy)
        alpha = np.minimum(alpha, np.clip((d - wr) / (wr * 0.12) * 255, 0, 255))
    arr = np.dstack([np.asarray(img), alpha.astype(np.uint8)])
    out = []
    for i in range(GROUP):
        for j in range(GROUP):
            tx, ty = tx0 + i, ty0 + j
            if not (x0 <= tx <= x1 and y0 <= ty <= y1):
                continue
            t = arr[j * TILE:(j + 1) * TILE, i * TILE:(i + 1) * TILE]
            a = t[:, :, 3]
            if a.max() == 0:
                continue
            buf = io.BytesIO()
            if a.min() == 255:
                Image.fromarray(t[:, :, :3]).save(buf, "JPEG", quality=G["quality"])
            else:
                Image.fromarray(t).save(buf, "PNG")
            out.append((z, tx, n - 1 - ty, buf.getvalue()))
    return out


def init_shrink(path, quality):
    G.update(path=path, quality=quality, db=None)


def shrink_row(task):
    from PIL import Image
    z, ty, tx0, tx1 = task
    if G["db"] is None:
        G["db"] = sqlite3.connect(Path(G["path"]).resolve().as_uri() + "?mode=ro", uri=True, timeout=60)
    n, n2 = 1 << z, 1 << (z + 1)
    rows = {}
    for (c, r, d) in G["db"].execute("SELECT tile_column, tile_row, tile_data FROM tiles WHERE zoom_level=? AND tile_column BETWEEN ? AND ? AND tile_row IN (?, ?)",
                                     (z + 1, 2 * tx0, 2 * tx1 + 1, n2 - 1 - 2 * ty, n2 - 1 - (2 * ty + 1))):
        rows[(c, n2 - 1 - r)] = d
    out = []
    for tx in range(tx0, tx1 + 1):
        big = Image.new("RGBA", (2 * TILE, 2 * TILE), (0, 0, 0, 0))
        any_ = False
        for dx in (0, 1):
            for dy in (0, 1):
                d = rows.get((2 * tx + dx, 2 * ty + dy))
                if d:
                    big.paste(Image.open(io.BytesIO(d)).convert("RGBA"), (dx * TILE, dy * TILE))
                    any_ = True
        if not any_:
            continue
        small = big.reduce(2)
        buf = io.BytesIO()
        if small.getchannel("A").getextrema()[0] == 255:
            small.convert("RGB").save(buf, "JPEG", quality=G["quality"])
        else:
            small.save(buf, "PNG")
        out.append((z, tx, n - 1 - ty, buf.getvalue()))
    return out


def find(pattern):
    for root in (HERE, os.path.dirname(HERE)):
        for f in sorted(os.listdir(root)):
            if f.lower().endswith(pattern) and not f.startswith(NAME.replace(" ", "_")):
                return os.path.join(root, f)
    return None


def build(parcels=None, streetmap=None, zmax=19, zmin=10, workers=None, out=None, quality=85, seed=7, log=print):
    parcels = parcels or find("parcels.geojson")
    streetmap = streetmap or find(".mbtiles")
    if not parcels or not streetmap:
        raise SystemExit("Put the Parcel100 .geojson and the street map .mbtiles beside the .bat (or in System Files).")
    workers = workers or max(1, min(8, (os.cpu_count() or 2) - 1))
    t0 = time.time()
    G["E"] = load_engine()
    city = City(parcels, streetmap, seed)
    bounds = (city.XMIN, city.XMAX, city.YMIN, city.YMAX)
    log(f"{NAME}: {len(city.lots):,} lots, {len(city.objs):,} things to draw, area {city.W / city.MS / 1000:.1f} x {city.H / city.MS / 1000:.1f} km ({time.time() - t0:.0f} s)")
    out = out or os.path.join(os.path.dirname(HERE), NAME.replace(" ", "_") + ".tpkx")
    mb = os.path.splitext(out)[0] + ".mbtiles"
    if os.path.exists(mb):
        os.remove(mb)
    db = sqlite3.connect(mb)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=OFF")
    db.execute("CREATE TABLE metadata (name text, value text)")
    db.execute("CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)")
    lo0, la0, lo1, la1 = city.area
    db.executemany("INSERT INTO metadata VALUES (?, ?)", [("name", NAME), ("format", "png"), ("type", "overlay"), ("version", "1.1"),
                   ("description", "Real Sim City"), ("minzoom", str(zmin)), ("maxzoom", str(zmax)),
                   ("bounds", f"{lo0},{la0},{lo1},{la1}"), ("center", f"{(lo0 + lo1) / 2},{(la0 + la1) / 2},{zmax}")])
    db.commit()
    x0, x1, y0, y1 = tile_range(bounds, zmax)
    tasks = [(tx, ty) for ty in range(y0, y1 + 1, GROUP) for tx in range(x0, x1 + 1, GROUP)]
    log(f"Drawing zoom {zmax} on {workers} cores ({len(tasks):,} blocks) ...")
    ctx = mp.get_context("spawn")
    written = 0
    with ctx.Pool(workers, initializer=init_draw, initargs=(parcels, streetmap, zmax, quality, seed)) as pool:
        done, last = 0, 0
        for res in pool.imap_unordered(draw_group, tasks):
            db.executemany("INSERT INTO tiles VALUES (?, ?, ?, ?)", res)
            written += len(res)
            done += 1
            if time.time() - last > 5 or done == len(tasks):
                last = time.time()
                log(f"  zoom {zmax}: {done:,}/{len(tasks):,} blocks ({last - t0:.0f} s)")
                db.commit()
    db.commit()
    db.execute("CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row)")
    db.commit()
    with ctx.Pool(workers, initializer=init_shrink, initargs=(mb, quality)) as pool:
        for z in range(zmax - 1, zmin - 1, -1):
            a0, a1, b0, b1 = tile_range(bounds, z)
            rt = [(z, ty, tx, min(a1, tx + 63)) for ty in range(b0, b1 + 1) for tx in range(a0, a1 + 1, 64)]
            for res in pool.imap_unordered(shrink_row, rt):
                db.executemany("INSERT INTO tiles VALUES (?, ?, ?, ?)", res)
                written += len(res)
            db.commit()
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db.execute("PRAGMA journal_mode=DELETE")
    db.close()
    log(f"{written:,} tiles in {time.time() - t0:.0f} s. Packing the TPKX ...")
    spec = importlib.util.spec_from_file_location("mb2tpkx_conv", os.path.join(HERE, "MBTiles_to_TPKX_v0_3_0.py"))
    conv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conv)
    if os.path.exists(out):
        os.remove(out)
    conv.convert_mbtiles_to_tpkx(Path(mb), Path(out))
    os.remove(mb)
    log(f"Done in {time.time() - t0:.0f} s: {out} ({os.path.getsize(out) / 1e6:,.0f} MB)")
    return out


if __name__ == "__main__":
    kw = {}
    a = sys.argv[1:]
    conv = {"--parcels": ("parcels", str), "--streetmap": ("streetmap", str), "--zmax": ("zmax", int), "--zmin": ("zmin", int),
            "--workers": ("workers", int), "--out": ("out", str), "--seed": ("seed", int)}
    i = 0
    while i < len(a):
        if a[i] in conv:
            k, f = conv[a[i]]
            kw[k] = f(a[i + 1])
            i += 2
        else:
            i += 1
    build(**kw)
