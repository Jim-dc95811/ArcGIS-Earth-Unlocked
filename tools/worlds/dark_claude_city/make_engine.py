"""Assembles darkcity.py from the proven firefighter drawing code + the night-city parts below."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _parts  # the proven firefighter drawing code, extracted (HEAD = drawing pieces, EXTRA = billboard etc., REND = render)

head = _parts.HEAD
i = head.index("import hashlib")
head = '''"""Dark Claude City - picture maker
Draws an original night city - art-deco towers, rain-wet streets, an elevated railway, a clock tower,
blocks that seem to shift, and a city that ends at black water - as one giant JPEG for Picture World Maker.
Everything is drawn by this program: no outside pictures, no outside characters or places.

py darkcity.py [--seed N] [--out file.jpg] [--crop x0 y0 x1 y1] [--scale k]

PLUG-INS: darkcity_*.py files beside this one are loaded at start. Each has register(E), where E is
this module; it may add block builders to E.BUILDERS, street/edge hooks, per-chunk overlays, specials.
"""
''' + head[i:]

def rep(s, a, b):
    assert a in s, a[:70]
    return s.replace(a, b, 1)

head = rep(head, 'VERSION = "0.2 TEST"\nHOME_TOWN = "New Claude City"      # Enter at the name question = this town (town number 1)', 'VERSION = "0.1 TEST"\nCITY = "Dark Claude City"')
head = rep(head, "TOP = 520", "TOP = 1100                   # room above the island for the tallest towers")
head = rep(head, "N = 340                      # island grid is N x N tiles", "N = int(os.environ.get(\"DCC_N\", \"340\"))   # island grid is N x N tiles (bigger cities: set DCC_N before loading)")
# night palette
a = head.index("COL = {SEA:")
b = head.index("WATER = (SEA")
head = head[:a] + '''COL = {SEA: (8, 13, 24), SHALLOW: (12, 20, 34), SAND: (64, 60, 58), GRASS: (28, 42, 32),
       ROAD: (30, 32, 38), WALK: (56, 56, 60), PLAZA: (58, 52, 48), RIVER: (12, 20, 32), PATH: (58, 50, 40),
       DIRT: (44, 36, 28), FIELD: (30, 44, 32), LOT: (34, 34, 38), PIER: (56, 42, 32), BRIDGE: (44, 42, 44),
       POND: (14, 22, 36), YARD: (34, 46, 36), MARKET: (60, 46, 38), CONCRETE: (56, 56, 58)}
QUAY = SAND                  # the stone edge where the city stops
LAMP = (255, 206, 120)       # warm lamplight
LIT = (255, 210, 130)        # lit window
DARKWIN = (26, 32, 44)       # dark window
NEON = [(255, 60, 90), (60, 220, 255), (255, 170, 40), (190, 90, 255), (80, 255, 140)]
'''+ head[b:]
head = rep(head, "OUT = (40, 36, 40)", "OUT = (12, 12, 16)")
head = rep(head, "SHADOW = (0, 0, 20, 70)", "SHADOW = (0, 0, 8, 90)")
# fedora + trench coat options for people
head = rep(head, '''    elif hat == "helmet":''', '''    elif hat == "fedora":
        ctx.ell(x, hy - 2.0 * s, 5.2 * s, 1.5 * s, L["hcol"], OUT)
        ctx.poly([(x - 3.1 * s, hy - 2.0 * s), (x + 3.1 * s, hy - 2.0 * s), (x + 2.6 * s, hy - 5.4 * s), (x - 2.6 * s, hy - 5.4 * s)], L["hcol"], OUT)
        ctx.line([(x - 3.0 * s, hy - 2.8 * s), (x + 3.0 * s, hy - 2.8 * s)], shade(L["hcol"], 0.5), 0.8 * s)
    elif hat == "helmet":''')
head = rep(head, '''    if ff:
        for yy in (sh + 3.2 * s, hip - 0.8 * s):''', '''    if L.get("coat"):   # long coat down to the knees
        ctx.poly([(x - 3.5 * s, hip), (x + 3.5 * s, hip), (x + 4.2 * s, y - 4 * s), (x - 4.2 * s, y - 4 * s)], shirt, shade(shirt, 0.6))
        ctx.line([(x, sh + 1 * s), (x, y - 4.5 * s)], shade(shirt, 0.7), 0.6 * s)
    if ff:
        for yy in (sh + 3.2 * s, hip - 0.8 * s):''')

ENGINE = r'''

# ---------------------------------------------------------------- night helpers (for plug-ins too)

def glow(ctx, x, y, rx, ry, col, alpha=60, rings=7):
    """soft light: many faint concentric see-through ellipses, brightest in the middle"""
    for i in range(rings, 0, -1):
        f = (i / rings) ** 0.8
        ctx.ell(x, y, rx * f, ry * f, (col[0], col[1], col[2], max(2, int(alpha / rings * 1.25))))


def light_pool(ctx, c, r, radius, col=LAMP, alpha=70):
    x, y = iso(c, r)
    glow(ctx, x, y, radius * 1.414 * HW, radius * 1.414 * HH, col, alpha)


def noir_windows(ctx, c0, r0, c1, r1, z0, h, seed, lit_frac=0.33, floor_h=42, gap=0.45, wfrac=0.55, lit=LIT, dark=DARKWIN):
    rnd = random.Random(seed)
    for face, length in (("L", c1 - c0), ("R", r1 - r0)):
        n = max(1, int(length / gap))
        step = 1.0 / n
        floors = int((h - 8) / floor_h)
        for f in range(floors):
            za = z0 + f * floor_h + floor_h * 0.32
            zb = za + floor_h * 0.48
            for i in range(n):
                ua = (i + (1 - wfrac) / 2) * step
                ub = ua + step * wfrac
                on = rnd.random() < lit_frac
                col = lit if on else dark
                pts = [face_pt(face, c0, r0, c1, r1, ua, za), face_pt(face, c0, r0, c1, r1, ub, za),
                       face_pt(face, c0, r0, c1, r1, ub, zb), face_pt(face, c0, r0, c1, r1, ua, zb)]
                ctx.poly(pts, shade(col, 1.0 if face == "L" else 0.85) if on else shade(col, 0.95 if face == "L" else 0.8), None)
                if on and rnd.random() < 0.25:
                    mx = sum(p[0] for p in pts) / 4
                    my = sum(p[1] for p in pts) / 4
                    ctx.ell(mx, my, 9, 9, (255, 200, 110, 26))


def font(px):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=max(6, int(px)))
    except Exception:
        return ImageFont.load_default()


def neon_text(ctx, x, y, text, col, size=22, glow_px=10):
    """glowing sign text centred on (x, y) in picture pixels"""
    k = ctx.k
    f = font(size * k)
    tw = ctx.d.textlength(text, font=f)
    X, Y = (x - ctx.ox) * k - tw / 2, (y - ctx.oy) * k - size * k * 0.6
    cxp, cyp = X + tw / 2, Y + size * k * 0.62
    for g in range(5, 0, -1):
        ctx.d.ellipse([cxp - tw * 0.5 - g * glow_px * k * 0.6, cyp - size * k * 0.6 - g * glow_px * k * 0.45,
                       cxp + tw * 0.5 + g * glow_px * k * 0.6, cyp + size * k * 0.6 + g * glow_px * k * 0.45], fill=(col[0], col[1], col[2], 10))
    ctx.d.text((X, Y), text, font=f, fill=shade(col, 0.6))
    ctx.d.text((X - 0.6 * k, Y - 0.6 * k), text, font=f, fill=tuple(min(255, v + 90) for v in col[:3]))


def noir_look(R, **kw):
    """people of the night city: coats, hats, umbrellas"""
    coat = R.choice([(38, 38, 44), (52, 46, 40), (140, 116, 82), (44, 50, 66), (70, 30, 36), (90, 90, 96), (30, 30, 30)])
    L = dict(s=1.0 if R.random() > 0.06 else 0.75, f=R.choice((-1, 1)), pose=R.choice(("walk", "walk", "walk", "stand")),
             skin=R.choice(SKIN), hair=R.choice(HAIR[:6]), shirt=coat, pants=R.choice([(30, 30, 34), (46, 44, 48), (60, 56, 50)]),
             coat=R.random() < 0.7)
    q = R.random()
    if q < 0.55:
        L.update(hat="fedora", hcol=R.choice([(30, 28, 30), (60, 50, 40), (90, 84, 78), (40, 42, 52)]))
    if R.random() < 0.18:
        L.update(extra="umbrella", ecol=R.choice([(20, 20, 24), (20, 20, 24), (110, 20, 30), (40, 40, 60)]))
    L.update(kw)
    return L


# ---------------------------------------------------------------- plug-in registry

BUILDERS = {}        # kind -> fn(town, bx, by)      fills one 14 x 14 block (tiles bx..bx+14, by..by+14)
STREET_HOOKS = []    # fn(town)                       dress the streets (replaces the default dressing if any)
EDGE_HOOKS = []      # fn(town)                       the edge of the world (quay, water, lone sign ...)
FINAL_HOOKS = []     # fn(town)                       anything last (searchlights, landmarks ...)
OVERLAYS = []        # fn(ctx, cx, cy, cw, ch)        drawn over each finished chunk (rain, fog)
SPECIALS = {}        # (di, dj) offset from the centre block -> kind
WEIGHTS = {          # ring -> [(kind, weight)]   (ring: 'core' < 3 blocks from centre < 'mid' < 6.5 < 'outer')
    "core": [("deco_towers", 6), ("hotel", 1), ("theater", 1), ("plaza", 1), ("shifting", 1.5)],
    "mid": [("tenements", 4), ("deco_towers", 2.5), ("diner", 1), ("hotel", 1), ("plaza", 0.8), ("shifting", 1), ("theater", 0.6)],
    "outer": [("tenements", 5), ("warehouses", 2), ("park", 1.2), ("diner", 0.8), ("shifting", 0.6)],
}


class Town:
    def __init__(self, seed=1, force=None):
        self.seed = seed
        self.rnd = random.Random(seed)
        self.g = bytearray([SEA]) * (E * E)
        self.objs = []
        self.blocks = []          # (bx, by, kind)
        self.force = force
        self.build()

    # ---- grid
    def gt(self, c, r):
        if -OFF <= c < N + OFF and -OFF <= r < N + OFF:
            return self.g[(c + OFF) * E + r + OFF]
        return SEA

    def st(self, c, r, t):
        if -OFF <= c < N + OFF and -OFF <= r < N + OFF:
            self.g[(c + OFF) * E + r + OFF] = t

    def fill(self, bx, by, t, w=14, h=14):
        for c in range(int(bx), int(bx + w)):
            for r in range(int(by), int(by + h)):
                self.st(c, r, t)

    # ---- adding things to draw (key = painter order: bigger c + r = nearer = drawn later)
    def add(self, key, bbox, fn, *args):
        self.objs.append((key, len(self.objs), bbox, fn, args))

    def add_box_obj(self, c0, r0, c1, r1, h, fn, *args, key=None):
        x0 = iso(c0, r1)[0] - 6
        x1 = iso(c1, r0)[0] + 6
        y0 = iso(c0, r0, h)[1] - 6
        y1 = iso(c1, r1)[1] + 10
        self.add(key if key is not None else (c0 + c1 + r0 + r1) / 2, (x0, y0, x1, y1), fn, *args)

    def add_person(self, c, r, z=0.0, keyplus=0.0, **kw):
        x, y = iso(c, r, z)
        L = noir_look(self.rnd, **kw)
        self.add(c + r + keyplus, (x - 14, y - 70, x + 14, y + 4), person, x, y, L)
        return L

    def add_light(self, c, r, radius=1.6, col=LAMP, alpha=70):
        x, y = iso(c, r)
        rx, ry = radius * 1.414 * HW, radius * 1.414 * HH
        self.add(c + r - 1.5, (x - rx, y - ry, x + rx, y + ry), light_pool, c, r, radius, col, alpha)

    def add_lamp(self, c, r):
        x, y = iso(c, r)
        self.add_light(c, r)
        self.add(c + r + 0.01, (x - 30, y - 80, x + 30, y + 4), noir_lamp, x, y)

    def add_tree(self, c, r, s=1.4):
        x, y = iso(c, r)
        col = self.rnd.choice([(30, 52, 38), (26, 44, 34), (40, 58, 40)])
        self.add(c + r, (x - 30 * s, y - 50 * s, x + 30 * s, y + 8), tree, x, y, 0, s, col)

    def add_car(self, c, r, along, col=None):
        col = col or self.rnd.choice([(20, 20, 22), (60, 20, 24), (30, 40, 60), (70, 70, 74), (90, 80, 60), (24, 50, 40)])
        self.add_box_obj(c, r, c + 1, r + 1, 40, car, c, r, along, col)

    def crowd(self, bx, by, w, h, n, ok=(PLAZA, MARKET, CONCRETE, LOT, YARD, GRASS, WALK, DIRT, PATH, QUAY)):
        R = self.rnd
        for _ in range(n):
            for _ in range(5):
                c, r = bx + R.random() * w, by + R.random() * h
                if self.gt(int(c), int(r)) in ok:
                    self.add_person(c, r)
                    break

    # ---- the city
    def build(self):
        R = self.rnd
        S = random.Random(self.seed * 7919 + 13)
        ph = [S.uniform(0, 6.283) for _ in range(7)] if self.seed != 1 else [0.0] * 7
        noise = lambda c, r: (2.5 * math.sin(c * 0.071 + 1.3 + ph[0]) + 2 * math.sin(r * 0.09 + 0.4 + ph[1]) + 1.5 * math.sin((c + r) * 0.05 + ph[2])
                              + 1.2 * math.sin((c - r) * 0.13 + ph[3]))
        canal = lambda c: N * 0.42 + 6 * math.sin(c / 47.0 + ph[5])
        for c in range(N):
            cv = canal(c)
            for r in range(N):
                d = min(c, r, N - 1 - c, N - 1 - r) + noise(c, r)
                t = SEA if d < 10 else SHALLOW if d < 13 else QUAY if d < 16 else GRASS
                if abs(r - cv) < 2.0 and d >= 13:
                    t = RIVER
                self.st(c, r, t)
        for c in range(N):
            for r in range(N):
                t = self.gt(c, r)
                if t not in (GRASS, RIVER):
                    continue
                rc, rr = c % P, r % P
                road_r, road_c = rr in (1, 2), rc in (1, 2)
                walk = rr in (0, 3) or rc in (0, 3)
                if road_r or road_c:
                    if t == RIVER:
                        if road_r and road_c:
                            continue
                        dc, dr = (1, 0) if road_r else (0, 1)
                        ends = [any(self.gt(c + s * k * dc, r + s * k * dr) not in (RIVER, SEA, SHALLOW, QUAY) for k in range(1, 8)) for s in (1, -1)]
                        if all(ends):
                            self.st(c, r, BRIDGE)
                    else:
                        self.st(c, r, ROAD)
                elif walk and t == GRASS:
                    self.st(c, r, WALK)
        nb = N // P
        cb = nb / 2.0
        for bi in range(nb):
            for bj in range(nb):
                bx, by = bi * P + 4, bj * P + 4
                if bx + 14 > N or by + 14 > N:
                    continue
                tiles = [self.gt(c, r) for c in range(bx, bx + 14) for r in range(by, by + 14)]
                if any(t == RIVER for t in tiles):
                    kind = "canalside"
                elif not all(t == GRASS for t in tiles):
                    kind = "edge" if sum(t == GRASS for t in tiles) > 40 else None
                else:
                    dc = math.hypot(bi + 0.5 - cb, bj + 0.5 - cb)
                    kind = SPECIALS.get((bi - int(cb), bj - int(cb)))
                    if kind is None:
                        ring = "core" if dc < 3 * nb / 18 else "mid" if dc < 6.5 * nb / 18 else "outer"
                        kinds, w = zip(*WEIGHTS[ring])
                        kind = R.choices(kinds, w)[0]
                    if self.force:
                        kind = self.force
                if kind is None:
                    continue
                self.blocks.append((bx, by, kind))
                fn = BUILDERS.get(kind) or BUILDERS.get("tenements") or b_tenements
                fn(self, bx, by)
        if STREET_HOOKS:
            for f in STREET_HOOKS:
                f(self)
        else:
            street_dressing(self)
        for f in EDGE_HOOKS:
            f(self)
        for f in FINAL_HOOKS:
            f(self)


# ---------------------------------------------------------------- default pieces (plug-ins may replace)

def noir_lamp(ctx, x, y):
    ctx.line([(x, y), (x, y - 50)], (20, 20, 24), 1.8)
    ctx.line([(x, y - 50), (x + 8, y - 54)], (20, 20, 24), 1.4)
    ctx.ell(x + 9, y - 52, 3.6, 2.6, (255, 230, 170), OUT)
    glow(ctx, x + 9, y - 52, 22, 18, LAMP, 70)


def plain_block(ctx, c0, r0, c1, r1, h, wall, seed):
    box(ctx, c0, r0, c1, r1, 0, h, shade(wall, 0.8), shade(wall, 0.95), shade(wall, 0.72))
    noir_windows(ctx, c0, r0, c1, r1, 0, h, seed)


def b_tenements(town, bx, by):
    R = town.rnd
    town.fill(bx, by, CONCRETE)
    for i in range(3):
        for j in range(3):
            c0, r0 = bx + 0.4 + i * 4.6, by + 0.4 + j * 4.6
            c1, r1 = c0 + 3.4 + R.random() * 0.6, r0 + 3.4 + R.random() * 0.6
            h = 42 * R.randint(3, 6) + 8
            wall = R.choice([(92, 52, 44), (80, 70, 62), (70, 60, 56), (100, 84, 66)])
            town.add_box_obj(c0, r0, c1, r1, h + 20, plain_block, c0, r0, c1, r1, h, wall, R.random() * 1e9)
    town.crowd(bx, by, 14, 14, 25)


def b_plaza(town, bx, by):
    town.fill(bx, by, PLAZA)
    for k in range(8):
        a = k * math.pi / 4
        town.add_lamp(bx + 7 + math.cos(a) * 5, by + 7 + math.sin(a) * 5)
    town.crowd(bx, by, 14, 14, 140)


def b_park(town, bx, by):
    R = town.rnd
    town.fill(bx, by, GRASS)
    for _ in range(22):
        town.add_tree(bx + R.random() * 14, by + R.random() * 14)
    for k in range(4):
        town.add_lamp(bx + 2 + k * 3.3, by + 7)
    town.crowd(bx, by, 14, 14, 20)


def b_canalside(town, bx, by):
    R = town.rnd
    for c in range(bx, bx + 14):
        for r in range(by, by + 14):
            if town.gt(c, r) == GRASS:
                town.st(c, r, PLAZA)
    for _ in range(6):
        c, r = bx + R.random() * 14, by + R.random() * 14
        if town.gt(int(c), int(r)) == PLAZA:
            town.add_lamp(c, r)
    town.crowd(bx, by, 14, 14, 30)


def b_edge(town, bx, by):
    R = town.rnd
    for _ in range(6):
        c, r = bx + R.random() * 14, by + R.random() * 14
        if town.gt(int(c), int(r)) == QUAY:
            town.add_lamp(c, r)


for _k, _f in (("tenements", b_tenements), ("plaza", b_plaza), ("park", b_park), ("canalside", b_canalside), ("edge", b_edge)):
    BUILDERS[_k] = _f


def street_dressing(town):
    R = town.rnd
    for c in range(N):
        for r in range(N):
            t = town.gt(c, r)
            if t in (ROAD, BRIDGE):
                rc, rr = c % P, r % P
                along = "c" if rr in (1, 2) and rc not in (0, 1, 2, 3) else "r" if rc in (1, 2) and rr not in (0, 1, 2, 3) else None
                if along and R.random() < 0.06:
                    town.add_car(c, r, along)
            elif t == WALK:
                if R.random() < 0.35:
                    town.add_person(c + R.random(), r + R.random())
                if (c + r) % 6 == 0 and R.random() < 0.5:
                    town.add_lamp(c + 0.5, r + 0.5)


# ---------------------------------------------------------------- ground at night

def draw_tile(ctx, town, c, r, t):
    h = hsh(c, r)
    base = COL[t]
    j = ((h & 0xFF) - 128) / 128.0
    col = shade(base, 1 + 0.05 * j)
    pts = [iso(c, r), iso(c + 1, r), iso(c + 1, r + 1), iso(c, r + 1)]
    ctx.poly(pts, col, col)
    if t in (PLAZA, MARKET, QUAY):          # cobbles / stone setts
        for k in (0.25, 0.5, 0.75):
            ctx.line([iso(c + k, r), iso(c + k, r + 1)], shade(col, 0.8), 0.5)
            ctx.line([iso(c, r + k), iso(c + 1, r + k)], shade(col, 0.8), 0.5)
    elif t in (ROAD, BRIDGE, LOT):          # wet asphalt: thin light streaks
        if h % 3 == 0:
            x, y = iso(c + ((h >> 4) % 10) / 10, r + ((h >> 9) % 10) / 10)
            ctx.line([(x - 10, y), (x + 10, y)], (120, 110, 100, 70), 0.8)
        if h % 7 == 0:
            x, y = iso(c + 0.5, r + 0.5)
            ctx.ell(x, y, 26, 9, (70, 80, 100, 60))          # puddle
            ctx.ell(x - 4, y - 1, 10, 3, (255, 210, 140, 40))  # lamplight in the puddle
        if t != LOT:
            rc, rr = c % P, r % P
            if rr == 1 and rc not in (0, 1, 2, 3):
                ctx.line([iso(c + 0.2, r + 1), iso(c + 0.6, r + 1)], (150, 130, 70), 1.0)
            if rc == 1 and rr not in (0, 1, 2, 3):
                ctx.line([iso(c + 1, r + 0.2), iso(c + 1, r + 0.6)], (150, 130, 70), 1.0)
            if rr in (1, 2) and rc in (0, 3):
                for k in range(5):
                    ctx.line([iso(c + 0.1 + k * 0.2, r + 0.1), iso(c + 0.1 + k * 0.2, r + 0.9)], (150, 150, 150), 2.2)
            if rc in (1, 2) and rr in (0, 3):
                for k in range(5):
                    ctx.line([iso(c + 0.1, r + 0.1 + k * 0.2), iso(c + 0.9, r + 0.1 + k * 0.2)], (150, 150, 150), 2.2)
        if t == BRIDGE:
            for (dc, dr) in ((-1, 0), (0, -1), (1, 0), (0, 1)):
                if town.gt(c + dc, r + dr) == RIVER:
                    a = {(-1, 0): (iso(c, r), iso(c, r + 1)), (0, -1): (iso(c, r), iso(c + 1, r)),
                         (1, 0): (iso(c + 1, r), iso(c + 1, r + 1)), (0, 1): (iso(c, r + 1), iso(c + 1, r + 1))}[(dc, dr)]
                    ctx.line(list(a), (90, 86, 84), 3.0)
    elif t == WALK:
        ctx.line([iso(c + 0.5, r), iso(c + 0.5, r + 1)], shade(col, 0.82), 0.6)
        ctx.line([iso(c, r + 0.5), iso(c + 1, r + 0.5)], shade(col, 0.82), 0.6)
    elif t in (SEA, SHALLOW, RIVER, POND):
        if h % 5 == 0:
            x, y = iso(c + ((h >> 4) % 10) / 10, r + ((h >> 9) % 10) / 10)
            ctx.line([(x - 8, y), (x - 3, y - 2), (x + 3, y), (x + 8, y - 2)], (60, 80, 110, 90), 1.0)
        if t in (SHALLOW, RIVER):
            for (dc, dr) in ((-1, 0), (0, -1), (1, 0), (0, 1)):
                if town.gt(c + dc, r + dr) in (QUAY, PLAZA, WALK, ROAD, GRASS, CONCRETE):
                    a = {(-1, 0): (iso(c, r), iso(c, r + 1)), (0, -1): (iso(c, r), iso(c + 1, r)),
                         (1, 0): (iso(c + 1, r), iso(c + 1, r + 1)), (0, 1): (iso(c, r + 1), iso(c + 1, r + 1))}[(dc, dr)]
                    ctx.line(list(a), (90, 84, 78), 2.6)
    elif t in (GRASS, YARD):
        if h % 9 == 0:
            x, y = iso(c + 0.5, r + 0.5)
            ctx.line([(x - 6, y), (x - 4, y - 4)], shade(col, 0.7), 0.8)
'''

rend = _parts.REND
rend = rep(rend, "            for o in buckets[j * nx + i]:\n                o[3](ctx, *o[4])",
           "            for o in buckets[j * nx + i]:\n                o[3](ctx, *o[4])\n            for f in OVERLAYS:\n                f(ctx, cx, cy, cw, ch)")

TAIL = r'''


# ---------------------------------------------------------------- previews (for building plug-ins)

def preview(kind, out, size=(2400, 1500), seed=1):
    """every block in the city becomes `kind`; renders a crop at the centre at full detail"""
    t = Town(seed, force=kind)
    x, y = W // 2, H // 2 + 600
    render(t, None, (x - size[0] // 2, y - size[1] // 2, x + size[0] // 2, y + size[1] // 2), log=lambda *a: None).save(out)
    return t


def preview_at(town, c, r, out, size=(2400, 1500)):
    x, y = iso(c, r)
    render(town, None, (int(x - size[0] / 2), int(y - size[1] / 2), int(x + size[0] / 2), int(y + size[1] / 2)), log=lambda *a: None).save(out)


def overview(out, scale=0.06, seed=1):
    t = Town(seed)
    render(t, None, None, scale, log=lambda *a: None).save(out)
    return t


def load_plugins():
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    me = sys.modules[__name__]
    for name in ("darkcity_architect", "darkcity_street", "darkcity_uncanny"):
        path = os.path.join(here, name + ".py")
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.register(me)


load_plugins()


def main(argv):
    seed, out, crop, scale = 1, None, None, 1.0
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--seed":
            seed = int(argv[i + 1]); i += 2
        elif a == "--out":
            out = argv[i + 1]; i += 2
        elif a == "--crop":
            crop = tuple(int(v) for v in argv[i + 1:i + 5]); i += 5
        elif a == "--scale":
            scale = float(argv[i + 1]); i += 2
        else:
            i += 1
    here = os.path.dirname(os.path.abspath(__file__))
    out = out or os.path.join(os.path.dirname(here), "Dark_Claude_City.jpg" if seed == 1 else f"Dark_Claude_City_{seed}.jpg")
    print(f"DARK CLAUDE CITY picture maker v{VERSION}")
    print(f"Picture {W:,} x {H:,} pixels")
    t0 = time.time()
    town = Town(seed)
    print(f"City planned: {len(town.objs):,} things to draw ({time.time() - t0:.0f} s)")
    img = render(town, out, crop, scale)
    print("Saving the picture ...")
    img.save(out, quality=90)
    print(f"Done in {time.time() - t0:.0f} s: {out}  ({os.path.getsize(out) / 1e6:.0f} MB)")
    print()
    print("Next: open Picture World Maker, choose this picture, pick a World spot and build the TPKX.")


if __name__ == "__main__":
    main(sys.argv[1:])
'''

src = head + "\n" + _parts.EXTRA + "\n" + ENGINE + "\n\n" + rend + TAIL
open(os.path.join(HERE, "darkcity.py"), "w").write(src)
print("written", len(src.splitlines()), "lines")
