"""Dark Claude City - picture maker
Draws an original night city - art-deco towers, rain-wet streets, an elevated railway, a clock tower,
blocks that seem to shift, and a city that ends at black water - as one giant JPEG for Picture World Maker.
Everything is drawn by this program: no outside pictures, no outside characters or places.

py darkcity.py [--seed N] [--out file.jpg] [--crop x0 y0 x1 y1] [--scale k]

PLUG-INS: darkcity_*.py files beside this one are loaded at start. Each has register(E), where E is
this module; it may add block builders to E.BUILDERS, street/edge hooks, per-chunk overlays, specials.
"""
import hashlib, math, os, random, re, sys, time
from PIL import Image, ImageDraw

VERSION = "0.1 TEST"
CITY = "Dark Claude City"

N = int(os.environ.get("DCC_N", "340"))   # island grid is N x N tiles (bigger cities: set DCC_N before loading)
TW, TH = 96, 48              # tile size in picture pixels
HW, HH = TW / 2, TH / 2
TOP = 1100                   # room above the island for the tallest towers
W = N * TW
H = TOP + N * TH
X0 = N * HW
Y0 = TOP
SS = 2                       # draw at 2x, then shrink (smooth edges)
CS = 2048                    # chunk size in picture pixels
P = 18                       # street period: sidewalk, 2 lanes, sidewalk, 14-tile block
OFF = N // 2 + 30            # ground array margin (sea beyond the island grid)
E = N + 2 * OFF

SEA, SHALLOW, SAND, GRASS, ROAD, WALK, PLAZA, RIVER, PATH, DIRT, FIELD, LOT, PIER, BRIDGE, POND, YARD, MARKET, CONCRETE = range(18)
COL = {SEA: (8, 13, 24), SHALLOW: (12, 20, 34), SAND: (64, 60, 58), GRASS: (28, 42, 32),
       ROAD: (30, 32, 38), WALK: (56, 56, 60), PLAZA: (58, 52, 48), RIVER: (12, 20, 32), PATH: (58, 50, 40),
       DIRT: (44, 36, 28), FIELD: (30, 44, 32), LOT: (34, 34, 38), PIER: (56, 42, 32), BRIDGE: (44, 42, 44),
       POND: (14, 22, 36), YARD: (34, 46, 36), MARKET: (60, 46, 38), CONCRETE: (56, 56, 58)}
QUAY = SAND                  # the stone edge where the city stops
LAMP = (255, 206, 120)       # warm lamplight
LIT = (255, 210, 130)        # lit window
DARKWIN = (26, 32, 44)       # dark window
NEON = [(255, 60, 90), (60, 220, 255), (255, 170, 40), (190, 90, 255), (80, 255, 140)]
WATER = (SEA, SHALLOW, RIVER, POND)

SKIN = [(255, 224, 196), (241, 194, 150), (224, 172, 120), (198, 134, 90), (160, 102, 64), (110, 70, 44), (86, 54, 36)]
HAIR = [(30, 24, 20), (60, 40, 24), (110, 70, 36), (176, 120, 60), (224, 190, 120), (150, 150, 150), (200, 80, 40), (40, 40, 60)]
SHIRT = [(220, 60, 60), (60, 110, 200), (60, 170, 90), (240, 200, 60), (240, 140, 50), (150, 80, 180), (240, 240, 240),
         (40, 40, 50), (90, 200, 210), (240, 120, 170), (120, 90, 60), (180, 30, 60), (30, 90, 70), (250, 220, 140)]
PANTS = [(40, 50, 90), (60, 60, 70), (30, 30, 34), (120, 100, 70), (200, 190, 160), (70, 90, 140), (90, 60, 40)]
WALLS = [(244, 226, 196), (232, 196, 170), (210, 226, 236), (236, 236, 228), (250, 214, 150), (196, 220, 180),
         (238, 190, 190), (214, 200, 230), (226, 170, 120), (180, 120, 90)]
ROOFS = [(178, 70, 50), (120, 60, 46), (90, 96, 110), (60, 90, 70), (200, 110, 60), (70, 70, 80), (150, 50, 50)]
CARS = [(210, 40, 40), (40, 80, 180), (240, 240, 240), (30, 30, 34), (160, 164, 170), (240, 200, 40), (40, 140, 80),
        (250, 120, 30), (110, 40, 120), (90, 180, 220)]
OUT = (12, 12, 16)
SHADOW = (0, 0, 8, 90)


def iso(c, r, z=0.0):
    return (X0 + (c - r) * HW, Y0 + (c + r) * HH - z)


def shade(col, f):
    return tuple(max(0, min(255, int(v * f))) for v in col[:3])


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hsh(c, r, k=0):
    v = (c * 73856093) ^ (r * 19349663) ^ (k * 83492791)
    v = (v ^ (v >> 13)) * 1274126177
    return (v ^ (v >> 16)) & 0xFFFFFF


class Ctx:
    def __init__(self, img, ox, oy, k):
        self.d = ImageDraw.Draw(img, "RGBA")
        self.ox, self.oy, self.k = ox, oy, k

    def P(self, pts):
        ox, oy, k = self.ox, self.oy, self.k
        return [((x - ox) * k, (y - oy) * k) for x, y in pts]

    def poly(self, pts, fill, outline=OUT):
        self.d.polygon(self.P(pts), fill=fill, outline=outline)

    def ell(self, x, y, rx, ry, fill, outline=None):
        k = self.k
        self.d.ellipse([(x - rx - self.ox) * k, (y - ry - self.oy) * k, (x + rx - self.ox) * k, (y + ry - self.oy) * k],
                       fill=fill, outline=outline)

    def pie(self, x, y, rx, ry, a0, a1, fill, outline=None):
        k = self.k
        self.d.pieslice([(x - rx - self.ox) * k, (y - ry - self.oy) * k, (x + rx - self.ox) * k, (y + ry - self.oy) * k],
                        a0, a1, fill=fill, outline=outline)

    def sign(self, x, y, text, bg, fg):
        from PIL import ImageFont
        try:
            font = ImageFont.load_default(size=int(13 * self.k))
        except Exception:
            font = ImageFont.load_default()
        X, Y = (x - self.ox) * self.k, (y - self.oy) * self.k
        l, t, r_, b = self.d.textbbox((0, 0), text, font=font)
        w, h = r_ - l, b - t
        self.d.rectangle([X - w / 2 - 8, Y - h / 2 - 6, X + w / 2 + 8, Y + h / 2 + 8], fill=bg, outline=OUT)
        self.d.text((X - w / 2 - l, Y - h / 2 - t), text, font=font, fill=fg)

    def line(self, pts, fill, width=1.0):
        self.d.line(self.P(pts), fill=fill, width=max(1, int(round(width * self.k))))


# ---------------------------------------------------------------- drawing pieces

def face_pt(face, c0, r0, c1, r1, u, z):
    """point u (0..1) along a visible face: 'L' = r=r1 face (c0->c1), 'R' = c=c1 face (r1->r0)"""
    if face == "L":
        return iso(c0 + (c1 - c0) * u, r1, z)
    return iso(c1, r1 - (r1 - r0) * u, z)


def box(ctx, c0, r0, c1, r1, z0, h, top, left=None, right=None, outline=OUT):
    left = left or shade(top, 0.9)
    right = right or shade(top, 0.72)
    A, B, C = iso(c0, r1, z0), iso(c1, r1, z0), iso(c1, r0, z0)
    A2, B2, C2, D2 = iso(c0, r1, z0 + h), iso(c1, r1, z0 + h), iso(c1, r0, z0 + h), iso(c0, r0, z0 + h)
    ctx.poly([A, B, B2, A2], left, outline)
    ctx.poly([B, C, C2, B2], right, outline)
    ctx.poly([D2, C2, B2, A2], top, outline)


def windows(ctx, c0, r0, c1, r1, z0, h, floor_h, color, lit=None, rnd=None, gap=0.5, wfrac=0.5):
    for face, length in (("L", c1 - c0), ("R", r1 - r0)):
        n = max(1, int(length / gap))
        step = 1.0 / n
        floors = int((h - 8) / floor_h)
        for f in range(floors):
            za = z0 + f * floor_h + floor_h * 0.35
            zb = za + floor_h * 0.45
            for i in range(n):
                ua = (i + (1 - wfrac) / 2) * step
                ub = ua + step * wfrac
                col = color
                if lit and rnd and rnd.random() < 0.12:
                    col = lit
                ctx.poly([face_pt(face, c0, r0, c1, r1, ua, za), face_pt(face, c0, r0, c1, r1, ub, za),
                          face_pt(face, c0, r0, c1, r1, ub, zb), face_pt(face, c0, r0, c1, r1, ua, zb)],
                         shade(col, 0.95 if face == "L" else 0.8), None)


def house(ctx, c0, r0, c1, r1, h, rh, wall, roof, ridge_c, door, seed):
    rnd = random.Random(seed)
    box(ctx, c0, r0, c1, r1, 0, h, shade(wall, 1.0), shade(wall, 0.95), shade(wall, 0.78))
    windows(ctx, c0, r0, c1, r1, 0, h, 42, (120, 170, 210), (255, 226, 140), rnd, gap=0.7, wfrac=0.45)
    # door on the front-left face
    u = 0.15 + rnd.random() * 0.55
    ctx.poly([face_pt("L", c0, r0, c1, r1, u, 0), face_pt("L", c0, r0, c1, r1, u + 0.12, 0),
              face_pt("L", c0, r0, c1, r1, u + 0.12, 26), face_pt("L", c0, r0, c1, r1, u, 26)], door)
    if ridge_c:
        rm = (r0 + r1) / 2
        ctx.poly([iso(c0, r0, h), iso(c1, r0, h), iso(c1, rm, h + rh), iso(c0, rm, h + rh)], shade(roof, 0.8))
        ctx.poly([iso(c1, r1, h), iso(c1, r0, h), iso(c1, rm, h + rh)], shade(wall, 0.72))
        ctx.poly([iso(c0, r1, h), iso(c1, r1, h), iso(c1, rm, h + rh), iso(c0, rm, h + rh)], roof)
        chim = (c0 + (c1 - c0) * 0.7, rm - 0.15)
    else:
        cm = (c0 + c1) / 2
        ctx.poly([iso(c0, r0, h), iso(c0, r1, h), iso(cm, r1, h + rh), iso(cm, r0, h + rh)], shade(roof, 1.08))
        ctx.poly([iso(c1, r0, h), iso(c1, r1, h), iso(cm, r1, h + rh), iso(cm, r0, h + rh)], shade(roof, 0.78))
        ctx.poly([iso(c0, r1, h), iso(c1, r1, h), iso(cm, r1, h + rh)], shade(wall, 0.92))
        chim = (cm + 0.12, r0 + (r1 - r0) * 0.3)
    if rnd.random() < 0.5:
        box(ctx, chim[0], chim[1], chim[0] + 0.22, chim[1] + 0.22, h + rh * 0.4, rh * 0.75, (150, 80, 60))


def tower(ctx, c0, r0, c1, r1, h, wall, glass, top, seed):
    rnd = random.Random(seed)
    box(ctx, c0, r0, c1, r1, 0, h, top, shade(wall, 0.95), shade(wall, 0.75))
    windows(ctx, c0, r0, c1, r1, 0, h, 42, glass, (255, 230, 150), rnd, gap=0.42, wfrac=0.62)
    # roof edge + roof boxes
    box(ctx, c0, r0, c1, r1, h, 6, shade(top, 1.05), shade(wall, 0.85), shade(wall, 0.65))
    for _ in range(rnd.randint(1, 4)):
        a = c0 + rnd.random() * (c1 - c0 - 0.8) + 0.2
        b = r0 + rnd.random() * (r1 - r0 - 0.8) + 0.2
        box(ctx, a, b, a + 0.5, b + 0.4, h + 6, 14 + rnd.random() * 14, (170, 172, 176))
    if rnd.random() < 0.3:  # water tank
        a, b = c0 + 0.5, r0 + 0.5
        x, y = iso(a + 0.3, b + 0.3, h + 6)
        cyl(ctx, x, y, 14, 7, 26, (120, 90, 70), (150, 110, 80))


def cyl(ctx, x, y, rx, ry, h, side, top):
    ctx.ell(x, y, rx, ry, shade(side, 0.75), OUT)
    ctx.poly([(x - rx, y), (x + rx, y), (x + rx, y - h), (x - rx, y - h)], side, None)
    ctx.line([(x - rx, y), (x - rx, y - h)], OUT, 0.5)
    ctx.line([(x + rx, y), (x + rx, y - h)], OUT, 0.5)
    ctx.ell(x, y - h, rx, ry, top, OUT)


def shop(ctx, c0, r0, c1, r1, h, wall, awning, sign, seed):
    rnd = random.Random(seed)
    box(ctx, c0, r0, c1, r1, 0, h, (190, 186, 180), shade(wall, 0.95), shade(wall, 0.78))
    # big shop windows on the front-left face
    ctx.poly([face_pt("L", c0, r0, c1, r1, 0.08, 4), face_pt("L", c0, r0, c1, r1, 0.92, 4),
              face_pt("L", c0, r0, c1, r1, 0.92, 26), face_pt("L", c0, r0, c1, r1, 0.08, 26)], (150, 200, 226))
    windows(ctx, c0, r0, c1, r1, 42, h - 42, 42, (120, 170, 210), (255, 226, 140), rnd, gap=0.6)
    # striped awning
    n = 8
    for i in range(n):
        u0, u1 = i / n, (i + 1) / n
        col = awning if i % 2 == 0 else (250, 250, 250)
        a = face_pt("L", c0, r0, c1, r1, u0, 34)
        b = face_pt("L", c0, r0, c1, r1, u1, 34)
        cc = iso(c0 + (c1 - c0) * u1, r1 + 0.32, 24)
        dd = iso(c0 + (c1 - c0) * u0, r1 + 0.32, 24)
        ctx.poly([a, b, cc, dd], col, None)
    # sign board on the right face
    ctx.poly([face_pt("R", c0, r0, c1, r1, 0.2, 30), face_pt("R", c0, r0, c1, r1, 0.8, 30),
              face_pt("R", c0, r0, c1, r1, 0.8, 40), face_pt("R", c0, r0, c1, r1, 0.2, 40)], sign)


def tree(ctx, x, y, kind, s, col):
    ctx.ell(x + 4 * s, y, 13 * s, 5 * s, SHADOW)
    ctx.poly([(x - 1.6 * s, y), (x + 1.6 * s, y), (x + 1.3 * s, y - 16 * s), (x - 1.3 * s, y - 16 * s)], (110, 76, 46), None)
    if kind == 0:
        ctx.ell(x, y - 26 * s, 13 * s, 12 * s, shade(col, 0.8), OUT)
        ctx.ell(x - 5 * s, y - 30 * s, 9 * s, 8.5 * s, col, None)
        ctx.ell(x + 5 * s, y - 31 * s, 8 * s, 8 * s, shade(col, 0.92), None)
        ctx.ell(x - 2 * s, y - 35 * s, 6 * s, 5 * s, shade(col, 1.15), None)
    elif kind == 1:   # pine
        for i, (yy, w) in enumerate(((-12, 11), (-22, 9), (-31, 6.5))):
            ctx.poly([(x - w * s, y + (yy + 4) * s), (x + w * s, y + (yy + 4) * s), (x, y + (yy - 12) * s)],
                     shade(col, 0.7 + 0.12 * i), OUT)
    else:             # palm
        ctx.line([(x, y), (x + 3 * s, y - 30 * s)], (130, 96, 60), 2.4 * s)
        tx, ty = x + 3 * s, y - 30 * s
        for a in range(0, 360, 60):
            ex = tx + math.cos(math.radians(a)) * 13 * s
            ey = ty + math.sin(math.radians(a)) * 6 * s + 4 * s
            ctx.line([(tx, ty), ((tx + ex) / 2, ty - 3 * s), (ex, ey)], (50, 140, 60), 2.0 * s)


def person(ctx, x, y, L):
    s, f, pose = L["s"], L["f"], L["pose"]
    skin, shirt, pants = L["skin"], L["shirt"], L["pants"]
    ff = L.get("ff")
    ctx.ell(x, y, 5.5 * s, 2 * s, SHADOW)
    if pose == "sit":
        hip, sh = y - 6 * s, y - 14 * s
        ctx.line([(x - 0.8 * s, hip), (x + 4 * f * s, hip + 0.5 * s), (x + 4.4 * f * s, y)], pants, 2.3 * s)
        ctx.line([(x + 0.8 * s, hip), (x + 3.4 * f * s, hip + 1.2 * s), (x + 3.0 * f * s, y)], shade(pants, 0.85), 2.3 * s)
    else:
        hip, sh = y - 9 * s, y - 17 * s
        boot = (20, 20, 20) if ff else (50, 40, 34)
        if pose == "walk":
            a, b = (x + 2.6 * f * s, y), (x - 2.4 * f * s, y)
        else:
            a, b = (x - 1.5 * s, y), (x + 1.5 * s, y)
        ctx.line([(x + 0.9 * s, hip), b], shade(pants, 0.85), 2.3 * s)
        ctx.line([(x - 0.9 * s, hip), a], pants, 2.3 * s)
        for p in (a, b):
            ctx.ell(p[0] + 0.6 * f * s, p[1], (1.9 if ff else 1.5) * s, 1.0 * s, boot)
        if ff:
            ctx.line([(x - 2.6 * s, y - 4 * s), (x + 2.6 * s, y - 4 * s)], (250, 220, 40), 0.9 * s)
    # arm behind
    sw = 2.2 * f * s if pose == "walk" else 0.6 * s
    ctx.line([(x + 3 * s, sh + 1 * s), (x + 3.6 * s - sw, sh + 7.5 * s)], shade(shirt, 0.8), 1.9 * s)
    ctx.poly([(x - 3.7 * s, sh), (x + 3.7 * s, sh), (x + 2.9 * s, hip + 0.6 * s), (x - 2.9 * s, hip + 0.6 * s)], shirt, shade(shirt, 0.6))
    if L.get("coat"):   # long coat down to the knees
        ctx.poly([(x - 3.5 * s, hip), (x + 3.5 * s, hip), (x + 4.2 * s, y - 4 * s), (x - 4.2 * s, y - 4 * s)], shirt, shade(shirt, 0.6))
        ctx.line([(x, sh + 1 * s), (x, y - 4.5 * s)], shade(shirt, 0.7), 0.6 * s)
    if ff:
        for yy in (sh + 3.2 * s, hip - 0.8 * s):
            ctx.line([(x - 3.3 * s, yy), (x + 3.3 * s, yy)], (250, 220, 40), 1.0 * s)
    if L.get("vest"):
        ctx.line([(x - 2.4 * s, sh + 0.5 * s), (x - 2.2 * s, hip)], (230, 230, 230), 0.7 * s)
        ctx.line([(x + 2.4 * s, sh + 0.5 * s), (x + 2.2 * s, hip)], (230, 230, 230), 0.7 * s)
    hx, hy = x - 3.4 * s + sw, sh + 7.5 * s
    ctx.line([(x - 3 * s, sh + 1 * s), (hx, hy)], shirt, 1.9 * s)
    ctx.ell(hx, hy + 0.6 * s, 1.0 * s, 1.0 * s, skin)
    extra = L.get("extra")
    if extra == "balloon":
        bx, by = hx + 4 * s, hy - 26 * s
        ctx.line([(hx, hy), (bx, by + 3 * s)], (90, 90, 90), 0.4)
        ctx.ell(bx, by, 3.2 * s, 3.8 * s, L["ecol"], OUT)
    elif extra == "umbrella":
        ctx.line([(hx, hy), (hx, hy - 24 * s)], (60, 60, 60), 0.6 * s)
        ctx.pie(hx, hy - 20 * s, 9 * s, 5 * s, 180, 360, L["ecol"], OUT)
    elif extra == "bag":
        ctx.poly([(hx - 1.6 * s, hy), (hx + 1.6 * s, hy), (hx + 1.8 * s, hy + 4 * s), (hx - 1.8 * s, hy + 4 * s)], L["ecol"])
    elif extra == "hose":
        ctx.poly([(hx - 1.3 * s, hy - 1 * s), (hx + 1.3 * s, hy - 1 * s), (hx + 1.3 * s, hy + 4.5 * s), (hx - 1.3 * s, hy + 4.5 * s)], (200, 20, 20))
    # head
    hy = sh - 3.6 * s
    ctx.ell(x, hy - 0.5 * s, 3.5 * s, 3.5 * s, L["hair"])
    ctx.ell(x + 0.5 * f * s, hy + 0.4 * s, 3.0 * s, 3.1 * s, skin)
    ctx.ell(x + 1.7 * f * s, hy, 0.4 * s, 0.45 * s, (30, 20, 20))
    hat = L.get("hat")
    if hat == "cap":
        ctx.pie(x, hy - 1.0 * s, 3.5 * s, 3.0 * s, 180, 360, L["hcol"])
        ctx.line([(x, hy - 1.0 * s), (x + 4.6 * f * s, hy - 0.8 * s)], shade(L["hcol"], 0.7), 1.0 * s)
    elif hat == "sun":
        ctx.ell(x, hy - 2.4 * s, 6.0 * s, 1.6 * s, L["hcol"], OUT)
        ctx.pie(x, hy - 2.0 * s, 3.2 * s, 2.8 * s, 180, 360, L["hcol"])
    elif hat == "fedora":
        ctx.ell(x, hy - 2.0 * s, 5.2 * s, 1.5 * s, L["hcol"], OUT)
        ctx.poly([(x - 3.1 * s, hy - 2.0 * s), (x + 3.1 * s, hy - 2.0 * s), (x + 2.6 * s, hy - 5.4 * s), (x - 2.6 * s, hy - 5.4 * s)], L["hcol"], OUT)
        ctx.line([(x - 3.0 * s, hy - 2.8 * s), (x + 3.0 * s, hy - 2.8 * s)], shade(L["hcol"], 0.5), 0.8 * s)
    elif hat == "helmet":
        ctx.ell(x, hy - 1.3 * s, 5.0 * s, 1.4 * s, shade(L["hcol"], 0.8), OUT)
        ctx.pie(x, hy - 1.2 * s, 3.9 * s, 3.6 * s, 180, 360, L["hcol"], OUT)
        if ff:
            ctx.ell(x + 2.0 * f * s, hy - 2.6 * s, 1.0 * s, 1.1 * s, (240, 240, 240))


def dog(ctx, x, y, f, col, spots):
    ctx.ell(x, y, 6, 2, SHADOW)
    for dx in (-3.4, -1.8, 2.2, 3.6):
        ctx.line([(x + dx * f, y - 5), (x + dx * f, y)], shade(col, 0.85), 1.3)
    ctx.ell(x, y - 6, 5.2, 2.6, col, OUT)
    ctx.line([(x - 5 * f, y - 7), (x - 8 * f, y - 10)], col, 1.2)
    ctx.ell(x + 5.6 * f, y - 9, 2.4, 2.1, col, OUT)
    ctx.ell(x + 5.0 * f, y - 10.4, 0.9, 1.3, shade(col, 0.5) if not spots else (20, 20, 20))
    if spots:
        for dx, dy in ((-2.5, -6.5), (0.5, -5.4), (2.4, -7.0), (-0.6, -7.6), (6.4, -8.4)):
            ctx.ell(x + dx * f, y + dy, 0.8, 0.7, (20, 20, 20))


def car(ctx, c, r, along, col, length=0.78, height=11, cab=8, kind="car"):
    if along == "c":
        c0, c1, r0, r1 = c + (1 - length) / 2, c + (1 + length) / 2, r + 0.28, r + 0.72
    else:
        c0, c1, r0, r1 = c + 0.28, c + 0.72, r + (1 - length) / 2, r + (1 + length) / 2
    x, y = iso((c0 + c1) / 2, (r0 + r1) / 2)
    ctx.ell(x, y + 2, (c1 - c0 + r1 - r0) * HW * 0.72, (c1 - c0 + r1 - r0) * HH * 0.55, SHADOW)
    box(ctx, c0, r0, c1, r1, 2, height, col)
    if kind == "car":
        if along == "c":
            a0, a1, b0, b1 = c0 + 0.18, c1 - 0.22, r0 + 0.04, r1 - 0.04
        else:
            a0, a1, b0, b1 = c0 + 0.04, c1 - 0.04, r0 + 0.18, r1 - 0.22
        box(ctx, a0, b0, a1, b1, 2 + height, cab, shade(col, 1.05), (150, 190, 214), (110, 150, 180))
    elif kind == "bus":
        windows(ctx, c0, r0, c1, r1, 2, height, height * 0.95, (150, 190, 214), gap=0.3, wfrac=0.7)
    elif kind == "truck":   # fire truck: cab at the front, ladder on top, light bar
        if along == "c":
            box(ctx, c1 - 0.45, r0 + 0.02, c1, r1 - 0.02, 2 + height, 9, shade(col, 1.05), (150, 190, 214), (110, 150, 180))
            l0, l1 = iso(c0 + 0.1, r0 + 0.2, 2 + height + 4), iso(c1 - 0.5, r0 + 0.2, 2 + height + 4)
            m0, m1 = iso(c0 + 0.1, r1 - 0.2, 2 + height + 4), iso(c1 - 0.5, r1 - 0.2, 2 + height + 4)
            lx, ly = iso(c1 - 0.2, (r0 + r1) / 2, 2 + height + 9)
        else:
            box(ctx, c0 + 0.02, r1 - 0.45, c1 - 0.02, r1, 2 + height, 9, shade(col, 1.05), (110, 150, 180), (150, 190, 214))
            l0, l1 = iso(c0 + 0.2, r0 + 0.1, 2 + height + 4), iso(c0 + 0.2, r1 - 0.5, 2 + height + 4)
            m0, m1 = iso(c1 - 0.2, r0 + 0.1, 2 + height + 4), iso(c1 - 0.2, r1 - 0.5, 2 + height + 4)
            lx, ly = iso((c0 + c1) / 2, r1 - 0.2, 2 + height + 9)
        ctx.line([l0, l1], (220, 220, 220), 1.6)
        ctx.line([m0, m1], (220, 220, 220), 1.6)
        for i in range(10):
            t = i / 9
            ctx.line([(l0[0] + (l1[0] - l0[0]) * t, l0[1] + (l1[1] - l0[1]) * t), (m0[0] + (m1[0] - m0[0]) * t, m0[1] + (m1[1] - m0[1]) * t)], (220, 220, 220), 0.8)
        ctx.ell(lx - 3, ly, 2.6, 1.6, (60, 120, 255))
        ctx.ell(lx + 3, ly, 2.6, 1.6, (255, 50, 50))
        ctx.line([face_pt("L", c0, r0, c1, r1, 0, 7), face_pt("L", c0, r0, c1, r1, 1, 7)], (250, 230, 120), 1.4)
    for u in (0.2, 0.8):
        if along == "c":
            wx, wy = face_pt("L", c0, r0, c1, r1, u, 2)
        else:
            wx, wy = face_pt("R", c0, r0, c1, r1, u, 2)
        ctx.ell(wx, wy, 4.2, 4.2, (24, 24, 26))


def boat(ctx, x, y, kind, col, f):
    ctx.line([(x - 22 * f, y + 4), (x - 50 * f, y + 9)], (230, 245, 255), 1.4)
    ctx.line([(x - 22 * f, y + 6), (x - 46 * f, y + 14)], (230, 245, 255), 1.0)
    if kind == "sail":
        ctx.poly([(x - 20, y - 6), (x + 22, y - 6), (x + 14, y + 4), (x - 14, y + 4)], col)
        ctx.line([(x, y - 6), (x, y - 62)], (90, 70, 50), 1.4)
        ctx.poly([(x + 1, y - 60), (x + 1, y - 9), (x + 26 * f, y - 10)], (250, 250, 246))
        ctx.poly([(x - 1, y - 52), (x - 1, y - 10), (x - 16 * f, y - 10)], (236, 236, 230))
    elif kind == "motor":
        ctx.poly([(x - 26, y - 6), (x + 26, y - 6), (x + 18, y + 5), (x - 22, y + 5)], (250, 250, 250))
        ctx.poly([(x - 10, y - 6), (x + 12, y - 6), (x + 8, y - 16), (x - 8, y - 16)], col)
        ctx.poly([(x - 6, y - 8), (x + 8, y - 8), (x + 6, y - 14), (x - 4, y - 14)], (150, 190, 214), None)
    elif kind == "row":
        ctx.poly([(x - 12, y - 3), (x + 12, y - 3), (x + 8, y + 3), (x - 8, y + 3)], col)
        ctx.line([(x - 15, y + 4), (x + 15, y - 4)], (120, 90, 60), 1.0)
    else:  # ferry
        ctx.poly([(x - 70, y - 12), (x + 70, y - 12), (x + 56, y + 10), (x - 60, y + 10)], (240, 240, 240))
        ctx.poly([(x - 60, y - 12), (x + 52, y - 12), (x + 46, y - 30), (x - 52, y - 30)], col)
        for i in range(10):
            wx = x - 46 + i * 10
            ctx.poly([(wx, y - 26), (wx + 6, y - 26), (wx + 6, y - 18), (wx, y - 18)], (150, 190, 214), None)
        ctx.poly([(x - 14, y - 30), (x + 6, y - 30), (x + 4, y - 48), (x - 12, y - 48)], (220, 50, 40))


def stall(ctx, c, r, col):
    box(ctx, c, r, c + 1.3, r + 0.8, 0, 14, (180, 140, 90))
    for i in range(6):
        ctx.ell(*iso(c + 0.15 + i * 0.2, r + 0.35, 15), 3.0, 2.0, random.Random(int(c * 100 + r * 7 + i)).choice(
            [(230, 50, 40), (250, 180, 30), (100, 190, 60), (240, 120, 40), (150, 60, 160)]))
    for i in range(5):
        u0, u1 = i / 5, (i + 1) / 5
        cc = col if i % 2 == 0 else (250, 250, 250)
        ctx.poly([iso(c - 0.1 + 1.5 * u0, r - 0.1, 40), iso(c - 0.1 + 1.5 * u1, r - 0.1, 40),
                  iso(c - 0.1 + 1.5 * u1, r + 1.0, 30), iso(c - 0.1 + 1.5 * u0, r + 1.0, 30)], cc)
    ctx.line([iso(c, r + 0.8, 0), iso(c, r + 0.8, 31)], (90, 70, 50), 1.0)
    ctx.line([iso(c + 1.3, r + 0.8, 0), iso(c + 1.3, r + 0.8, 31)], (90, 70, 50), 1.0)


def fountain(ctx, c, r):
    x, y = iso(c, r)
    R = 2.0
    rx, ry = R * 1.414 * HW, R * 1.414 * HH
    cyl(ctx, x, y, rx, ry, 16, (200, 196, 186), (220, 216, 206))
    ctx.ell(x, y - 16, rx * 0.86, ry * 0.86, (90, 170, 220), None)
    for k in range(18):
        a = k * math.pi / 9
        ctx.ell(x + math.cos(a) * rx * 0.5, y - 16 + math.sin(a) * ry * 0.5, 3, 1.2, (200, 235, 255))
    cyl(ctx, x, y - 16, 12, 6, 30, (200, 196, 186), (220, 216, 206))
    for k in range(8):
        a = k * math.pi / 4
        ex, ey = x + math.cos(a) * 46, y - 20 + math.sin(a) * 20
        ctx.line([(x, y - 46), (x + math.cos(a) * 22, y - 66), (ex, ey)], (190, 230, 255), 1.6)
    ctx.ell(x, y - 52, 6, 8, (220, 245, 255))


def bench(ctx, c, r, along):
    if along == "c":
        box(ctx, c, r, c + 0.6, r + 0.18, 6, 3, (150, 100, 60))
        box(ctx, c, r - 0.02, c + 0.6, r + 0.02, 9, 7, (140, 92, 56))
    else:
        box(ctx, c, r, c + 0.18, r + 0.6, 6, 3, (150, 100, 60))
        box(ctx, c - 0.02, r, c + 0.02, r + 0.6, 9, 7, (140, 92, 56))


def lamp(ctx, x, y):
    ctx.line([(x, y), (x, y - 44)], (60, 64, 70), 1.4)
    ctx.ell(x, y - 46, 3.2, 2.4, (255, 240, 180), OUT)


def umbrella(ctx, x, y, col):
    ctx.ell(x + 6, y, 18, 7, SHADOW)
    ctx.line([(x, y), (x, y - 34)], (230, 230, 230), 1.2)
    ctx.pie(x, y - 28, 22, 10, 180, 360, col, OUT)
    ctx.pie(x, y - 28, 22, 10, 225, 270, (250, 250, 250), None)
    ctx.pie(x, y - 28, 22, 10, 300, 330, (250, 250, 250), None)


def flat(ctx, pts, col, outline=None):
    ctx.poly(pts, col, outline)


def crane(ctx, c, r, h, jib_dir):
    box(ctx, c, r, c + 0.35, r + 0.35, 0, h, (240, 190, 30))
    for z in range(10, int(h), 20):
        ctx.line([iso(c, r + 0.35, z), iso(c + 0.35, r + 0.35, z + 20)], (120, 90, 20), 0.6)
    top = h
    a, b = iso(c + 0.17, r + 0.17, top + 6), iso(c + 0.17 + 7 * jib_dir[0], r + 0.17 + 7 * jib_dir[1], top + 6)
    bb = iso(c + 0.17 - 2.2 * jib_dir[0], r + 0.17 - 2.2 * jib_dir[1], top + 6)
    ctx.line([bb, b], (240, 190, 30), 3.0)
    ctx.line([iso(c + 0.17, r + 0.17, top + 40), b], (120, 90, 20), 0.8)
    ctx.line([iso(c + 0.17, r + 0.17, top + 40), bb], (120, 90, 20), 0.8)
    ctx.line([iso(c + 0.17, r + 0.17, top), iso(c + 0.17, r + 0.17, top + 40)], (240, 190, 30), 2.0)
    box(ctx, c + 0.17 - 2.2 * jib_dir[0] - 0.2, r + 0.17 - 2.2 * jib_dir[1] - 0.2,
        c + 0.17 - 2.2 * jib_dir[0] + 0.2, r + 0.17 - 2.2 * jib_dir[1] + 0.2, top - 6, 14, (130, 130, 130))
    hk = (c + 0.17 + 5 * jib_dir[0], r + 0.17 + 5 * jib_dir[1])
    ctx.line([iso(hk[0], hk[1], top + 6), iso(hk[0], hk[1], top * 0.45)], (60, 60, 60), 0.6)
    box(ctx, hk[0] - 0.35, hk[1] - 0.15, hk[0] + 0.35, hk[1] + 0.15, top * 0.45 - 10, 10, (200, 80, 40))


def lighthouse(ctx, c, r):
    x, y = iso(c, r)
    cyl(ctx, x, y, 34, 17, 20, (170, 170, 170), (190, 190, 190))
    for i in range(6):
        col = (220, 40, 40) if i % 2 == 0 else (250, 250, 250)
        w = 22 - i * 1.6
        ctx.poly([(x - w, y - 20 - i * 40), (x + w, y - 20 - i * 40), (x + w - 1.6, y - 60 - i * 40), (x - w + 1.6, y - 60 - i * 40)], col, OUT)
    ctx.ell(x, y - 260, 16, 6, (60, 60, 60), OUT)
    ctx.poly([(x - 11, y - 260), (x + 11, y - 260), (x + 11, y - 284), (x - 11, y - 284)], (255, 240, 150), OUT)
    ctx.pie(x, y - 284, 13, 12, 180, 360, (200, 40, 40), OUT)
    ctx.poly([(x, y - 272), (x - 140, y - 300), (x - 140, y - 250)], (255, 250, 200, 70), None)


def clocktower(ctx, c0, r0, c1, r1, h):
    box(ctx, c0, r0, c1, r1, 0, h, (200, 180, 150), (226, 206, 172), (190, 170, 140))
    windows(ctx, c0, r0, c1, r1, 0, h - 40, 42, (110, 150, 190), gap=0.5)
    cm, rm = (c0 + c1) / 2, (r0 + r1) / 2
    ctx.poly([iso(c0, r1, h), iso(c1, r1, h), iso(cm, rm, h + 70)], (110, 60, 50))
    ctx.poly([iso(c1, r1, h), iso(c1, r0, h), iso(cm, rm, h + 70)], (90, 48, 40))
    x, y = face_pt("L", c0, r0, c1, r1, 0.5, h - 30)
    ctx.ell(x, y, 14, 16, (250, 250, 240), OUT)
    ctx.line([(x, y), (x, y - 11)], (20, 20, 20), 1.4)
    ctx.line([(x, y), (x + 8, y + 3)], (20, 20, 20), 1.4)


def billboard(ctx, x, y, name, line2):
    from PIL import ImageFont
    k = ctx.k
    try:
        f1 = ImageFont.load_default(size=int(58 * k))
        f2 = ImageFont.load_default(size=int(30 * k))
        f0 = ImageFont.load_default(size=int(26 * k))
    except Exception:
        f1 = f2 = f0 = ImageFont.load_default()
    w1 = ctx.d.textlength(name, font=f1) / k
    w = max(520, w1 + 80)
    top, bot = y - 360, y - 150
    ctx.ell(x + 20, y, w * 0.45, 26, SHADOW)
    for px in (x - w * 0.32, x + w * 0.32):
        ctx.poly([(px - 6, y), (px + 6, y), (px + 6, bot), (px - 6, bot)], (110, 80, 50))
    ctx.poly([(x - w / 2 - 10, top - 10), (x + w / 2 + 10, top - 10), (x + w / 2 + 10, bot + 10), (x - w / 2 - 10, bot + 10)], (120, 80, 40))
    ctx.poly([(x - w / 2, top), (x + w / 2, top), (x + w / 2, bot), (x - w / 2, bot)], (250, 244, 220))
    X, Y = (x - ctx.ox) * k, (y - ctx.oy) * k
    for text, font, dy, col in (("WELCOME TO", f0, -330, (90, 90, 90)), (name, f1, -285, (200, 30, 30)), (line2, f2, -205, (40, 90, 60))):
        tw = ctx.d.textlength(text, font=font)
        ctx.d.text((X - tw / 2, Y + dy * k), text, font=font, fill=col)


def lifeguard(ctx, c, r):
    for a, b in ((c, r), (c + 0.8, r), (c, r + 0.8), (c + 0.8, r + 0.8)):
        ctx.line([iso(a, b), iso(a, b, 40)], (240, 240, 240), 1.6)
    box(ctx, c - 0.05, r - 0.05, c + 0.9, r + 0.9, 40, 22, (240, 240, 240), (220, 50, 40), (190, 40, 30))
    x, y = iso(c + 0.45, r + 0.45, 70)
    ctx.line([(x, y), (x, y - 26)], (90, 90, 90), 1.0)
    ctx.poly([(x, y - 26), (x + 16, y - 22), (x, y - 18)], (240, 60, 40))


def swimmer(ctx, x, y, skin, hair, ring):
    if ring:
        ctx.ell(x, y, 7, 3.2, ring, OUT)
        ctx.ell(x, y, 3.6, 1.6, (64, 170, 200))
    else:
        ctx.ell(x, y + 1, 6, 2, (200, 235, 245))
    ctx.ell(x, y - 3, 3.0, 3.0, hair)
    ctx.ell(x + 0.6, y - 2.6, 2.6, 2.6, skin)




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


def inv(x, y):
    a, b = (x - X0) / HW, (y - Y0) / HH
    return (a + b) / 2, (b - a) / 2


# ---------------------------------------------------------------- render

def render(town, out, crop=None, scale=1.0, log=print):
    x0, y0, x1, y1 = crop or (0, 0, W, H)
    ow, oh = int((x1 - x0) * scale), int((y1 - y0) * scale)
    img = Image.new("RGB", (ow, oh), COL[SEA])
    objs = sorted(town.objs, key=lambda o: (o[0], o[1]))
    nx, ny = math.ceil((x1 - x0) / CS), math.ceil((y1 - y0) / CS)
    buckets = [[] for _ in range(nx * ny)]
    for o in objs:
        bx0, by0, bx1, by1 = o[2]
        i0, i1 = max(0, int((bx0 - x0) // CS)), min(nx - 1, int((bx1 - x0) // CS))
        j0, j1 = max(0, int((by0 - y0) // CS)), min(ny - 1, int((by1 - y0) // CS))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                buckets[j * nx + i].append(o)
    t0 = time.time()
    k = SS
    done = 0
    for j in range(ny):
        for i in range(nx):
            cx, cy = x0 + i * CS, y0 + j * CS
            cw, ch = min(CS, x1 - cx), min(CS, y1 - cy)
            if cw <= 0 or ch <= 0:
                continue
            chunk = Image.new("RGB", (int(cw * k), int(ch * k)), COL[SEA])
            ctx = Ctx(chunk, cx, cy, k)
            corners = [inv(cx, cy), inv(cx + cw, cy), inv(cx, cy + ch), inv(cx + cw, cy + ch)]
            cmin, cmax = int(min(p[0] for p in corners)) - 2, int(max(p[0] for p in corners)) + 2
            rmin, rmax = int(min(p[1] for p in corners)) - 2, int(max(p[1] for p in corners)) + 2
            for c in range(cmin, cmax + 1):
                for r in range(rmin, rmax + 1):
                    tx = X0 + (c - r) * HW
                    ty = Y0 + (c + r) * HH
                    if tx + HW < cx or tx - HW > cx + cw or ty > cy + ch or ty + TH < cy:
                        continue
                    draw_tile(ctx, town, c, r, town.gt(c, r))
            for o in buckets[j * nx + i]:
                o[3](ctx, *o[4])
            for f in OVERLAYS:
                f(ctx, cx, cy, cw, ch)
            small = chunk.reduce(k)
            if scale != 1.0:
                small = small.resize((max(1, int(cw * scale)), max(1, int(ch * scale))), Image.LANCZOS)
            img.paste(small, (int((cx - x0) * scale), int((cy - y0) * scale)))
            done += 1
            if done % 8 == 0 or done == nx * ny:
                el = time.time() - t0
                log(f"  drawn {done}/{nx * ny} pieces  ({el:.0f} s, about {el / done * (nx * ny - done):.0f} s to go)")
    return img




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
