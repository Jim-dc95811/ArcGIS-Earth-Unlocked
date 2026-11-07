"""Where's the Firefighter? - picture maker
Draws an original isometric island town - houses, towers, shops, parks, a plaza, a market, a fire
station, a harbour, beaches, boats and thousands of people - as one giant JPEG for Picture World Maker.
One firefighter in a gold helmet is hidden somewhere in it (and one lost dalmatian).
Everything is drawn by this program: no outside pictures, no outside characters.

py wheres_the_firefighter.py [--seed N] [--out file.jpg] [--crop x0 y0 x1 y1] [--scale k]
"""
import hashlib, math, os, random, re, sys, time
from PIL import Image, ImageDraw

VERSION = "0.2 TEST"
HOME_TOWN = "New Claude City"      # Enter at the name question = this town (town number 1)

N = 340                      # island grid is N x N tiles
TW, TH = 96, 48              # tile size in picture pixels
HW, HH = TW / 2, TH / 2
TOP = 520
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
COL = {SEA: (38, 112, 178), SHALLOW: (64, 170, 200), SAND: (236, 214, 160), GRASS: (104, 168, 74),
       ROAD: (86, 88, 96), WALK: (196, 196, 190), PLAZA: (222, 210, 186), RIVER: (54, 136, 196),
       PATH: (214, 190, 140), DIRT: (160, 122, 82), FIELD: (90, 170, 80), LOT: (92, 94, 100),
       PIER: (150, 108, 70), BRIDGE: (110, 104, 100), POND: (60, 150, 200), YARD: (122, 182, 86),
       MARKET: (206, 150, 112), CONCRETE: (178, 178, 172)}
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
OUT = (40, 36, 40)
SHADOW = (0, 0, 20, 70)


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


# ---------------------------------------------------------------- the town

class Town:
    def __init__(self, seed, name=HOME_TOWN):
        self.seed, self.name = seed, name
        self.rnd = random.Random(seed)
        self.g = bytearray([SEA]) * (E * E)
        self.objs = []
        self.answer = {}
        self.crowd_spots = []
        self.park_spots = []
        self.build()

    def gt(self, c, r):
        if -OFF <= c < N + OFF and -OFF <= r < N + OFF:
            return self.g[(c + OFF) * E + r + OFF]
        return SEA

    def st(self, c, r, t):
        if -OFF <= c < N + OFF and -OFF <= r < N + OFF:
            self.g[(c + OFF) * E + r + OFF] = t

    def add(self, key, bbox, fn, *args):
        self.objs.append((key, len(self.objs), bbox, fn, args))

    def add_box_obj(self, c0, r0, c1, r1, h, fn, *args, key=None):
        x0 = iso(c0, r1)[0] - 4
        x1 = iso(c1, r0)[0] + 4
        y0 = iso(c0, r0, h)[1] - 4
        y1 = iso(c1, r1)[1] + 8
        self.add(key if key is not None else (c0 + c1 + r0 + r1) / 2, (x0, y0, x1, y1), fn, *args)

    def look(self, **kw):
        R = self.rnd
        L = dict(s=1.0 if R.random() > 0.15 else 0.72, f=R.choice((-1, 1)), pose=R.choice(("walk", "walk", "stand")),
                 skin=R.choice(SKIN), hair=R.choice(HAIR), shirt=R.choice(SHIRT), pants=R.choice(PANTS))
        q = R.random()
        if q < 0.12:
            L.update(hat="cap", hcol=R.choice(SHIRT))
        elif q < 0.18:
            L.update(hat="sun", hcol=R.choice([(240, 220, 160), (250, 250, 250), (200, 60, 60), (240, 200, 60)]))
        q = R.random()
        if q < 0.03:
            L.update(extra="balloon", ecol=R.choice(SHIRT))
        elif q < 0.06:
            L.update(extra="umbrella", ecol=R.choice(SHIRT))
        elif q < 0.14:
            L.update(extra="bag", ecol=R.choice(SHIRT))
        L.update(kw)
        return L

    def add_person(self, c, r, z=0.0, keyplus=0.0, **kw):
        x, y = iso(c, r, z)
        L = self.look(**kw)
        self.add(c + r + keyplus, (x - 12, y - 60, x + 12, y + 4), person, x, y, L)
        return L

    def add_tree(self, c, r, kind=None, s=None):
        x, y = iso(c, r)
        R = self.rnd
        kind = R.choice((0, 0, 0, 1)) if kind is None else kind
        s = 1.7 * (s or (0.8 + R.random() * 0.5))
        col = R.choice([(70, 150, 60), (86, 166, 70), (60, 130, 56), (110, 170, 60), (80, 140, 80)])
        if kind == 1:
            col = (50, 120, 70)
        self.add(c + r, (x - 26 * s, y - 50 * s, x + 26 * s, y + 8), tree, x, y, kind, s, col)

    def build(self):
        R = self.rnd
        # every town has its own coast and river; town 1 (New Claude City) keeps the original shape
        S = random.Random(self.seed * 7919 + 13)
        ph = [0.0] * 7 if self.seed == 1 else [S.uniform(0, 6.283) for _ in range(7)]
        rvp = (0.6, 14, 7) if self.seed == 1 else (S.uniform(0.35, 0.65), S.uniform(8, 18), S.uniform(4, 9))
        noise = lambda c, r: (3 * math.sin(c * 0.071 + 1.3 + ph[0]) + 2.5 * math.sin(r * 0.09 + 0.4 + ph[1]) + 2 * math.sin((c + r) * 0.05 + ph[2])
                              + 1.5 * math.sin((c - r) * 0.13 + ph[3]) + 1.2 * math.sin(c * 0.21 + r * 0.17 + ph[4]))
        river = lambda c: N * rvp[0] + rvp[1] * math.sin(c / 31.0 + ph[5]) + rvp[2] * math.sin(c / 13.0 + 2 + ph[6])
        self.dist = {}
        for c in range(N):
            rv = river(c)
            for r in range(N):
                d = min(c, r, N - 1 - c, N - 1 - r) + noise(c, r)
                if d < 9:
                    t = SEA
                elif d < 14:
                    t = SHALLOW
                elif d < 22:
                    t = SAND
                else:
                    t = GRASS
                if abs(r - rv) < 2.6 and d >= 12:
                    t = RIVER
                self.st(c, r, t)
        # streets
        for c in range(N):
            for r in range(N):
                t = self.gt(c, r)
                if t != GRASS and t != RIVER:
                    continue
                rc, rr = c % P, r % P
                road_r, road_c = rr in (1, 2), rc in (1, 2)
                walk = rr in (0, 3) or rc in (0, 3)
                if road_r or road_c:
                    if t == RIVER:
                        if road_r and road_c:
                            continue
                        dc, dr = (1, 0) if road_r else (0, 1)
                        ends = [any(self.gt(c + s * k * dc, r + s * k * dr) not in (RIVER, SEA, SHALLOW, SAND) for k in range(1, 8)) for s in (1, -1)]
                        if all(ends):
                            self.st(c, r, BRIDGE)
                    else:
                        self.st(c, r, ROAD)
                elif walk and t == GRASS:
                    self.st(c, r, WALK)
        # blocks
        nb = N // P
        cb = nb / 2.0
        specials = {(int(cb), int(cb)): "hall", (int(cb) + 2, int(cb) - 1): "fire", (int(cb) - 1, int(cb) + 1): "plaza",
                    (int(cb) + 1, int(cb) + 3): "market", (int(cb) - 3, int(cb) - 2): "market", (int(cb) + 3, int(cb) + 2): "plaza"}
        for bi in range(nb):
            for bj in range(nb):
                bx, by = bi * P + 4, bj * P + 4
                if bx + 14 > N or by + 14 > N:
                    continue
                tiles = [self.gt(c, r) for c in range(bx, bx + 14) for r in range(by, by + 14)]
                if any(t == RIVER for t in tiles):
                    self.riverpark(bx, by)
                    continue
                if not all(t == GRASS for t in tiles):
                    if sum(t == GRASS for t in tiles) > 60:
                        self.countryside(bx, by)
                    continue
                dc = math.hypot(bi + 0.5 - cb, bj + 0.5 - cb)
                kind = specials.get((bi, bj))
                if kind is None:
                    q = R.random()
                    if dc < 3.5:
                        kind = "towers" if q < 0.25 else "apart" if q < 0.45 else "shops" if q < 0.7 else "construction" if q < 0.78 else "market" if q < 0.88 else "plaza"
                    elif dc < 6.5:
                        kind = ("apart" if q < 0.3 else "shops" if q < 0.5 else "houses" if q < 0.68 else "park" if q < 0.78
                                else "parking" if q < 0.85 else "market" if q < 0.89 else "sports" if q < 0.94 else "construction")
                    else:
                        kind = "houses" if q < 0.68 else "park" if q < 0.8 else "sports" if q < 0.87 else "docks" if (q < 0.95 and bi >= nb - 3) else "houses"
                getattr(self, "b_" + kind)(bx, by)
        self.streetlife()
        self.coast()
        self.hide()
        self.welcome_sign()

    # ---- blocks
    def fill(self, bx, by, t, w=14, h=14):
        for c in range(bx, bx + w):
            for r in range(by, by + h):
                self.st(c, r, t)

    def b_houses(self, bx, by):
        R = self.rnd
        self.fill(bx, by, YARD)
        for i in range(4):
            for j in range(4):
                lc, lr = bx + i * 3.5, by + j * 3.5
                w, d = 1.9 + R.random() * 0.9, 1.6 + R.random() * 0.9
                c0, r0 = lc + 0.4 + R.random() * (3.1 - w - 0.4), lr + 0.35
                c1, r1 = c0 + w, r0 + d
                h = 42 if R.random() < 0.6 else 84
                rh = 24 + R.random() * 12
                self.add_box_obj(c0, r0, c1, r1, h + rh + 30, house, c0, r0, c1, r1, h, rh, R.choice(WALLS), R.choice(ROOFS),
                                 R.random() < 0.5, R.choice([(120, 70, 40), (40, 70, 120), (180, 40, 40), (60, 100, 60)]), R.random() * 1e9)
                if R.random() < 0.25 and r1 < lr + 2.6:   # pool
                    pc, pr = c0, r1 + 0.25
                    self.add(pc + pr - 0.5, (iso(pc, pr + 0.7)[0] - 4, iso(pc, pr)[1] - 4, iso(pc + 1.1, pr)[0] + 4, iso(pc + 1.1, pr + 0.7)[1] + 4),
                             flat, [iso(pc, pr), iso(pc + 1.1, pr), iso(pc + 1.1, pr + 0.7), iso(pc, pr + 0.7)], (90, 200, 230), (230, 230, 230))
                elif R.random() < 0.5:
                    self.add_tree(lc + 3.0, lr + 3.1)
                for _ in range(R.randint(0, 3)):
                    self.add_person(c1 - R.random() * w, r1 + 0.3 + R.random() * 0.6)
                if R.random() < 0.12:
                    x, y = iso(c1 + 0.6, r1 + 0.2)
                    self.add(c1 + r1 + 0.8, (x - 12, y - 16, x + 12, y + 4), dog, x, y, R.choice((-1, 1)), R.choice([(150, 100, 50), (40, 30, 26), (220, 180, 110)]), False)

    def b_apart(self, bx, by):
        R = self.rnd
        self.fill(bx, by, PLAZA)
        for i in range(2):
            for j in range(2):
                c0, r0 = bx + 0.8 + i * 7, by + 0.8 + j * 7
                c1, r1 = c0 + 4.6 + R.random(), r0 + 4.6 + R.random()
                h = 42 * R.randint(4, 7) + 8
                self.add_box_obj(c0, r0, c1, r1, h + 50, tower, c0, r0, c1, r1, h, R.choice(WALLS), (120, 170, 210), (150, 150, 150), R.random() * 1e9)
                if R.random() < 0.4:
                    self.add_person(c0 + 1.5, r0 + 1.5, z=h + 6, keyplus=(c1 - c0 + r1 - r0) + 1)
        for _ in range(12):
            self.add_tree(bx + R.random() * 14, by + 6.3 + R.random() * 0.6)
        self.crowd(bx, by, 14, 14, 70)

    def b_towers(self, bx, by):
        R = self.rnd
        self.fill(bx, by, PLAZA)
        n = R.choice((1, 2, 4))
        spots = {1: [(2, 2, 10)], 2: [(1, 1, 6), (7.5, 7, 6)], 4: [(0.8, 0.8, 5), (7.6, 0.8, 5), (0.8, 7.6, 5), (7.6, 7.6, 5)]}[n]
        for (a, b, s) in spots:
            c0, r0 = bx + a, by + b
            c1, r1 = c0 + s, r0 + s * (0.7 + R.random() * 0.3)
            h = 42 * R.randint(8, 12) + 8
            glass = R.choice([(110, 160, 200), (90, 140, 170), (140, 190, 210), (100, 130, 150)])
            self.add_box_obj(c0, r0, c1, r1, h + 60, tower, c0, r0, c1, r1, h, R.choice([(200, 206, 214), (170, 180, 190), (220, 214, 200)]),
                             glass, (130, 134, 140), R.random() * 1e9)
        self.crowd(bx, by, 14, 14, 80)

    def b_shops(self, bx, by):
        R = self.rnd
        self.fill(bx, by, LOT)
        for i in range(4):   # along the front-left street (r = by+14)
            c0, r0 = bx + i * 3.5 + 0.1, by + 11.6
            self.add_box_obj(c0, r0, c0 + 3.3, r0 + 2.2, 120, shop, c0, r0, c0 + 3.3, r0 + 2.2, R.choice((42, 84)), R.choice(WALLS),
                             R.choice(SHIRT[:6]), R.choice(SHIRT), R.random() * 1e9)
        for j in range(3):   # along the front-right street (c = bx+14)
            c0, r0 = bx + 11.6, by + j * 3.8 + 0.1
            self.add_box_obj(c0, r0, c0 + 2.2, r0 + 3.4, 120, house, c0, r0, c0 + 2.2, r0 + 3.4, 84, 20, R.choice(WALLS), R.choice(ROOFS),
                             False, (120, 70, 40), R.random() * 1e9)
        for c in range(bx, bx + 11):
            for r in range(by, by + 11):
                if (c - bx) % 2 == 0 and R.random() < 0.55:
                    self.add_car(c, r, "r")
        self.crowd(bx, by + 10.8, 14, 0.7, 40)
        self.crowd(bx, by, 11, 11, 25)

    def b_park(self, bx, by, dalmatian_ok=True):
        R = self.rnd
        self.fill(bx, by, GRASS)
        for c in range(bx, bx + 14):
            for r in range(by, by + 14):
                a, b = c - bx, r - by
                if abs(a - b) < 1 or abs(a + b - 13) < 1:
                    self.st(c, r, PATH)
                if (a - 10) ** 2 + (b - 4) ** 2 < 7:
                    self.st(c, r, POND)
        for _ in range(26):
            c, r = bx + R.random() * 14, by + R.random() * 14
            if self.gt(int(c), int(r)) == GRASS:
                self.add_tree(c, r)
        for _ in range(4):
            x, y = iso(bx + 10 + R.random() * 1.6 - 0.8, by + 4 + R.random() * 1.6 - 0.8)
            self.add(0, (x - 6, y - 6, x + 6, y + 4), lambda ctx, x, y: (ctx.ell(x, y, 4, 2, (250, 250, 250), OUT), ctx.ell(x + 3, y - 3, 1.8, 1.8, (60, 120, 60))), x, y)
        for k in range(70):
            t = R.random() * 13
            if k % 2:
                self.add_person(bx + t + 0.5, by + t + 0.5)
            else:
                self.add_person(bx + t + 0.5, by + 13 - t + 0.5)
        for _ in range(4):  # picnic
            c, r = bx + 1 + R.random() * 5, by + 8 + R.random() * 4
            if self.gt(int(c), int(r)) != GRASS:
                continue
            pts = [iso(c, r), iso(c + 0.8, r), iso(c + 0.8, r + 0.6), iso(c, r + 0.6)]
            self.add(c + r - 0.5, (pts[3][0] - 4, pts[0][1] - 4, pts[1][0] + 4, pts[2][1] + 4), flat, pts, R.choice([(220, 60, 60), (60, 110, 200), (240, 200, 60)]), (250, 250, 250))
            self.add_person(c + 0.2, r + 0.3, pose="sit")
            self.add_person(c + 0.6, r + 0.4, pose="sit", f=-1)
        for i in range(4):
            self.add(bx + 3 + i * 2 + by + 3 + i * 2 - 0.2, (iso(bx + 3 + i * 2, by + 4 + i * 2)[0] - 30, iso(bx + 3 + i * 2, by + 3 + i * 2)[1] - 40,
                     iso(bx + 4 + i * 2, by + 3 + i * 2)[0] + 30, iso(bx + 4 + i * 2, by + 4 + i * 2)[1] + 10), bench, bx + 3.2 + i * 2, by + 2.2 + i * 2, "c")
        if dalmatian_ok:
            self.park_spots.append((bx + 3 + R.random() * 3, by + 10 + R.random() * 2))

    def riverpark(self, bx, by):
        R = self.rnd
        for c in range(bx, bx + 14):
            for r in range(by, by + 14):
                if self.gt(c, r) == GRASS:
                    self.st(c, r, GRASS)
        for _ in range(16):
            c, r = bx + R.random() * 14, by + R.random() * 14
            if self.gt(int(c), int(r)) == GRASS:
                self.add_tree(c, r)
        for _ in range(8):
            c, r = bx + R.random() * 14, by + R.random() * 14
            if self.gt(int(c), int(r)) == GRASS:
                self.add_person(c, r)
        for _ in range(2):
            c, r = bx + R.random() * 14, by + R.random() * 14
            if self.gt(int(c), int(r)) == RIVER:
                x, y = iso(c, r)
                self.add(c + r, (x - 20, y - 10, x + 20, y + 8), boat, x, y, "row", R.choice(CARS), R.choice((-1, 1)))
                self.add_person(c, r - 0.05, pose="sit")

    def countryside(self, bx, by):
        R = self.rnd
        for _ in range(10):
            c, r = bx + R.random() * 14, by + R.random() * 14
            t = self.gt(int(c), int(r))
            if t == GRASS:
                self.add_tree(c, r, kind=R.choice((0, 1, 1)))
            elif t == SAND and R.random() < 0.4:
                self.add_tree(c, r, kind=2)

    def b_plaza(self, bx, by):
        R = self.rnd
        self.fill(bx, by, PLAZA)
        fx, fy = bx + 7, by + 7
        self.add(fx + fy, (iso(fx, fy)[0] - 140, iso(fx, fy)[1] - 120, iso(fx, fy)[0] + 140, iso(fx, fy)[1] + 80), fountain, fx, fy)
        for k in range(12):
            a = k * math.pi / 6
            self.add_tree(fx + math.cos(a) * 5.5, fy + math.sin(a) * 5.5, kind=0, s=0.9)
        self.crowd(bx, by, 14, 14, 650, avoid=(fx, fy, 2.6))
        for _ in range(30):
            c, r = bx + R.random() * 14, by + R.random() * 14
            x, y = iso(c, r)
            self.add(c + r, (x - 4, y - 5, x + 4, y + 2), lambda ctx, x, y: (ctx.ell(x, y - 2, 2.4, 1.6, (130, 130, 140)), ctx.ell(x + 1.8, y - 3.6, 1.2, 1.2, (110, 110, 120))), x, y)
        self.crowd_spots.append((bx, by, 14, 14))

    def b_market(self, bx, by):
        R = self.rnd
        self.fill(bx, by, MARKET)
        for i in range(5):
            for j in range(4):
                c, r = bx + 0.8 + i * 2.6, by + 0.8 + j * 3.4
                self.add_box_obj(c - 0.1, r - 0.1, c + 1.4, r + 1.0, 50, stall, c, r, R.choice([(220, 50, 50), (50, 120, 200), (40, 160, 80), (240, 160, 30)]))
        for j in range(4):
            self.crowd(bx, by + 2.1 + j * 3.4, 14, 1.4, 120)
        self.crowd_spots.append((bx, by + 2, 14, 11))

    def b_parking(self, bx, by):
        R = self.rnd
        self.fill(bx, by, LOT)
        for c in range(bx, bx + 14):
            for r in range(by, by + 14):
                if (r - by) % 3 != 2 and R.random() < 0.7:
                    self.add_car(c, r, "r")
        self.crowd(bx, by, 14, 14, 6)

    def b_sports(self, bx, by):
        R = self.rnd
        self.fill(bx, by, FIELD)
        w = (250, 250, 250)
        lines = [[(1, 1), (13, 1), (13, 13), (1, 13), (1, 1)], [(7, 1), (7, 13)], [(1, 5), (3.5, 5), (3.5, 9), (1, 9)], [(13, 5), (10.5, 5), (10.5, 9), (13, 9)]]
        for ln in lines:
            pts = [iso(bx + a, by + b) for a, b in ln]
            self.add(-1e9, (min(p[0] for p in pts) - 4, min(p[1] for p in pts) - 4, max(p[0] for p in pts) + 4, max(p[1] for p in pts) + 4),
                     lambda ctx, pts: ctx.line(pts, w, 1.6), pts)
        circ = [iso(bx + 7 + 1.8 * math.cos(a / 20 * 2 * math.pi), by + 7 + 1.8 * math.sin(a / 20 * 2 * math.pi)) for a in range(21)]
        self.add(-1e9, (min(p[0] for p in circ) - 4, min(p[1] for p in circ) - 4, max(p[0] for p in circ) + 4, max(p[1] for p in circ) + 4),
                 lambda ctx, pts: ctx.line(pts, w, 1.6), circ)
        ta, tb = R.sample(SHIRT, 2)
        for k in range(22):
            c, r = bx + 1.5 + R.random() * 11, by + 1.5 + R.random() * 11
            self.add_person(c, r, shirt=ta if k < 11 else tb, pants=(250, 250, 250), extra=None, hat=None, s=1.0)
        self.add_person(bx + 7.2, by + 7.6, shirt=(20, 20, 20), pants=(20, 20, 20), hat=None, extra=None, s=1.0)
        x, y = iso(bx + 6 + R.random() * 2, by + 6 + R.random() * 2)
        self.add(0, (x - 4, y - 4, x + 4, y + 4), lambda ctx, x, y: ctx.ell(x, y - 2, 2.2, 2.2, (250, 250, 250), OUT), x, y)
        for k in range(30):
            self.add_person(bx + 13.4, by + 0.5 + k * 0.45, pose="stand", f=-1)

    def b_construction(self, bx, by):
        R = self.rnd
        self.fill(bx, by, DIRT)
        c0, r0, c1, r1 = bx + 2, by + 2, bx + 9, by + 9
        floors = R.randint(3, 6)

        def frame(ctx):
            for f in range(floors):
                z = f * 42
                box(ctx, c0, r0, c1, r1, z + 38, 4, (180, 180, 176))
                for a in (c0, c1):
                    for b in (r0, r1, (r0 + r1) / 2):
                        ctx.line([iso(a, b, z), iso(a, b, z + 38)], (120, 120, 120), 2.0)
        self.add_box_obj(c0, r0, c1, r1, floors * 42 + 10, frame)
        self.add_box_obj(bx + 11, by + 2, bx + 11.35, by + 2.35, 420, crane, bx + 11, by + 2, 360, (-1, 0.35))
        for _ in range(6):
            a, b = bx + 1 + R.random() * 12, by + 10 + R.random() * 3
            self.add_box_obj(a, b, a + 0.7, b + 0.5, 20, box, a, b, a + 0.7, b + 0.5, 0, 6 + R.random() * 10, R.choice([(160, 120, 80), (150, 150, 150), (200, 160, 100)]))
        for _ in range(16):
            self.add_person(bx + 0.5 + R.random() * 13, by + 0.5 + R.random() * 13, hat="helmet", hcol=(250, 250, 250),
                            shirt=(250, 120, 20), vest=True, extra=None)

    def b_fire(self, bx, by):
        R = self.rnd
        self.fill(bx, by, CONCRETE)
        c0, r0, c1, r1 = bx + 1, by + 2, bx + 10, by + 8
        red = (180, 40, 36)

        def station(ctx):
            box(ctx, c0, r0, c1, r1, 0, 92, (150, 140, 130), shade(red, 1.05), shade(red, 0.8))
            windows(ctx, c0, r0, c1, r1, 46, 50, 40, (130, 180, 214), gap=0.6)
            sx, sy = face_pt("L", c0, r0, c1, r1, 0.5, 66)
            ctx.sign(sx, sy, "FIRE STATION 1", (250, 250, 250), (200, 20, 20))
            for k in range(3):
                u0 = 0.06 + k * 0.32
                pts = [face_pt("L", c0, r0, c1, r1, u0, 0), face_pt("L", c0, r0, c1, r1, u0 + 0.26, 0),
                       face_pt("L", c0, r0, c1, r1, u0 + 0.26, 40), face_pt("L", c0, r0, c1, r1, u0, 40)]
                ctx.poly(pts, (40, 30, 30) if k == 1 else (236, 236, 236))
                if k != 1:
                    for z in range(6, 40, 6):
                        ctx.line([face_pt("L", c0, r0, c1, r1, u0, z), face_pt("L", c0, r0, c1, r1, u0 + 0.26, z)], (170, 170, 170), 0.6)
            box(ctx, c1 - 1.6, r0, c1, r0 + 1.6, 92, 120, shade(red, 0.95), shade(red, 1.0), shade(red, 0.78))
            ctx.line([iso(c0 + 0.6, r1 - 0.6, 92), iso(c0 + 0.6, r1 - 0.6, 160)], (200, 200, 200), 1.2)
            x, y = iso(c0 + 0.6, r1 - 0.6, 160)
            ctx.poly([(x, y), (x + 26, y + 4), (x + 26, y + 20), (x, y + 16)], (220, 30, 30))
        self.add_box_obj(c0, r0, c1, r1, 260, station)
        for k, cc in enumerate((bx + 1.6, bx + 4.6)):
            self.add_box_obj(cc, r1 + 0.5, cc + 2, r1 + 1.5, 40, car, cc - 0.1 + (0 if k == 0 else 0), r1 + 0.6, "r", (210, 30, 30), 1.9, 20, 0, "truck")
        for k in range(7):
            self.add_person(bx + 1 + R.random() * 10, by + 9.5 + R.random() * 4, hat="helmet", hcol=(30, 30, 30),
                            shirt=(60, 52, 40), pants=(60, 52, 40), extra=None)

    def b_hall(self, bx, by):
        R = self.rnd
        self.fill(bx, by, PLAZA)
        self.add_box_obj(bx + 3, by + 3, bx + 11, by + 8, 160, house, bx + 3, by + 3, bx + 11, by + 8, 126, 40, (230, 214, 180), (110, 60, 50), True, (90, 50, 30), 77)
        self.add_box_obj(bx + 6, by + 8, bx + 8, by + 10, 400, clocktower, bx + 6, by + 8, bx + 8, by + 10, 300)
        for k in range(8):
            self.add_tree(bx + 1 + k * 1.7, by + 12.6, kind=0, s=0.8)
        self.crowd(bx, by + 10.2, 14, 3.6, 320)
        self.crowd(bx, by, 14, 2.6, 120)
        self.crowd_spots.append((bx, by + 10.2, 14, 3.6))

    def b_docks(self, bx, by):
        R = self.rnd
        self.fill(bx, by, CONCRETE)
        cols = [(200, 60, 40), (40, 100, 170), (60, 150, 80), (230, 170, 40), (120, 120, 130), (170, 70, 120)]
        for i in range(6):
            for j in range(3):
                c0, r0 = bx + 0.6 + i * 2.2, by + 0.6 + j * 4.4
                stack = R.randint(1, 4)

                def cont(ctx, c0=c0, r0=r0, stack=stack, seed=R.random()):
                    rr = random.Random(seed)
                    for z in range(stack):
                        col = rr.choice(cols)
                        box(ctx, c0, r0, c0 + 1.8, r0 + 3.6, z * 22, 22, col)
                        for u in range(1, 12):
                            ctx.line([face_pt("L", c0, r0, c0 + 1.8, r0 + 3.6, u / 12, z * 22 + 2), face_pt("L", c0, r0, c0 + 1.8, r0 + 3.6, u / 12, z * 22 + 20)], shade(col, 0.7), 0.5)
                self.add_box_obj(c0, r0, c0 + 1.8, r0 + 3.6, stack * 22 + 10, cont)
        self.crowd(bx, by, 14, 14, 10)

    # ---- people and traffic
    def crowd(self, bx, by, w, h, n, avoid=None):
        R = self.rnd
        for _ in range(n):
            for _ in range(5):
                c, r = bx + R.random() * w, by + R.random() * h
                if avoid and (c - avoid[0]) ** 2 + (r - avoid[1]) ** 2 < avoid[2] ** 2:
                    continue
                t = self.gt(int(c), int(r))
                if t in (PLAZA, MARKET, CONCRETE, LOT, YARD, GRASS, WALK, DIRT, PATH, SAND):
                    self.add_person(c, r)
                    break

    def add_car(self, c, r, along, col=None, kind="car"):
        col = col or self.rnd.choice(CARS)
        if kind == "bus":
            self.add_box_obj(c - 0.7, r - 0.7, c + 1.7, r + 1.7, 60, car, c, r, along, col, 2.0, 22, 0, "bus")
        else:
            self.add_box_obj(c, r, c + 1, r + 1, 40, car, c, r, along, col)

    def streetlife(self):
        R = self.rnd
        for c in range(N):
            for r in range(N):
                t = self.gt(c, r)
                if t in (ROAD, BRIDGE):
                    rc, rr = c % P, r % P
                    along = None
                    if rr in (1, 2) and rc not in (0, 1, 2, 3):
                        along = "c"
                    elif rc in (1, 2) and rr not in (0, 1, 2, 3):
                        along = "r"
                    if along and R.random() < 0.13:
                        if R.random() < 0.06:
                            self.add_car(c, r, along, R.choice([(240, 190, 30), (40, 110, 200)]), "bus")
                        else:
                            self.add_car(c, r, along)
                elif t == WALK:
                    for _ in range(2):
                        if R.random() < 0.45:
                            self.add_person(c + R.random(), r + R.random())
                    if (c + r) % 5 == 0 and R.random() < 0.5:
                        x, y = iso(c + 0.5, r + 0.5)
                        self.add(c + r + 1, (x - 6, y - 52, x + 6, y + 2), lamp, x, y)
                    if R.random() < 0.02:
                        self.add_tree(c + 0.5, r + 0.5, kind=0, s=0.7)

    def coast(self):
        R = self.rnd
        # beach
        lg = 0
        for c in range(N):
            for r in range(N):
                t = self.gt(c, r)
                if t == SAND:
                    q = R.random()
                    if q < 0.03:
                        x, y = iso(c + 0.5, r + 0.5)
                        self.add(c + r + 1, (x - 26, y - 44, x + 26, y + 10), umbrella, x, y, R.choice(SHIRT))
                        self.add_person(c + 0.7, r + 0.9, pose="sit", hat=None)
                    elif q < 0.07:
                        pts = [iso(c + 0.2, r + 0.3), iso(c + 0.7, r + 0.3), iso(c + 0.7, r + 0.9), iso(c + 0.2, r + 0.9)]
                        self.add(c + r, (pts[3][0] - 4, pts[0][1] - 4, pts[1][0] + 4, pts[2][1] + 4), flat, pts, R.choice(SHIRT), (250, 250, 250))
                        self.add_person(c + 0.5, r + 0.6, pose="sit")
                    elif q < 0.42:
                        self.add_person(c + R.random(), r + R.random(), hat=R.choice((None, "sun", "cap")), hcol=R.choice(SHIRT))
                    elif q < 0.205:
                        self.add_tree(c + 0.5, r + 0.5, kind=2)
                    elif q < 0.207:
                        x, y = iso(c + 0.5, r + 0.5)
                        self.add(c + r, (x - 10, y - 12, x + 10, y + 4), lambda ctx, x, y: (cyl(ctx, x, y, 7, 3.5, 6, (220, 190, 130), (236, 210, 150)), cyl(ctx, x, y - 6, 3, 1.5, 6, (220, 190, 130), (236, 210, 150))), x, y)
                    lg += 1
                    if lg % 900 == 0:
                        self.add_box_obj(c, r, c + 0.9, r + 0.9, 70, lifeguard, c, r)
                elif t == SHALLOW and R.random() < 0.025:
                    x, y = iso(c + R.random(), r + R.random())
                    self.add(c + r, (x - 8, y - 8, x + 8, y + 4), swimmer, x, y, R.choice(SKIN), R.choice(HAIR), R.choice(SHIRT) if R.random() < 0.3 else None)
        # harbour piers on the right-hand coast
        for r0 in range(int(N * 0.18), int(N * 0.42), 10):
            for c in range(N - 30, N + 2):
                for r in (r0, r0 + 1):
                    if self.gt(c, r) in (SEA, SHALLOW, SAND):
                        self.st(c, r, PIER)
            for k in range(4):
                c = N - 14 + k * 6 + R.random() * 2
                for side in (-1.2, 2.6):
                    x, y = iso(c, r0 + side)
                    self.add(c + r0 + side, (x - 60, y - 70, x + 60, y + 20), boat, x, y, R.choice(("sail", "motor", "motor")), R.choice(CARS), 1)
            for _ in range(5):
                self.add_person(N - 26 + R.random() * 36, r0 + 0.5 + R.random(), pose=R.choice(("stand", "walk")))
        # boats at sea (inside and outside the island grid)
        n = 0
        while n < 420:
            c, r = R.uniform(-OFF + 2, N + OFF - 2), R.uniform(-OFF + 2, N + OFF - 2)
            x, y = iso(c, r)
            if not (80 < x < W - 80 and 80 < y < H - 40):
                continue
            if self.gt(int(c), int(r)) != SEA:
                continue
            ok = all(self.gt(int(c) + dc, int(r) + dr) == SEA for dc in (-3, 0, 3) for dr in (-3, 0, 3))
            if not ok:
                continue
            kind = R.choice(("sail", "sail", "motor", "motor", "row")) if R.random() > 0.02 else "ferry"
            self.add(c + r, (x - 90, y - 70, x + 90, y + 20), boat, x, y, kind, R.choice(CARS), R.choice((-1, 1)))
            n += 1
        # lighthouse on the top tip
        for k in range(10, 40):
            if self.gt(k, k) == SAND:
                self.add(k + k + 1, (iso(k, k)[0] - 160, iso(k, k)[1] - 320, iso(k, k)[0] + 60, iso(k, k)[1] + 30), lighthouse, k + 0.5, k + 0.5)
                break

    def welcome_sign(self):
        people = sum(1 for o in self.objs if o[3] is person)
        line2 = "County Seat of Claude County" if self.name == HOME_TOWN else f"Population {people:,}"
        for k in range(N - 12, N // 2, -1):          # the bottom tip of the island, on the first dry land
            if self.gt(k, k) in (SAND, GRASS, YARD, WALK, PLAZA):
                x, y = iso(k + 0.5, k + 0.5)
                self.add(2 * k + 2, (x - 700, y - 420, x + 700, y + 40), billboard, x, y, self.name.upper(), line2)
                break

    def hide(self):
        R = self.rnd
        bx, by, w, h = R.choice(self.crowd_spots)
        for _ in range(100):
            c, r = bx + 1 + R.random() * (w - 2), by + 0.3 + R.random() * max(0.1, h - 0.6)
            if self.gt(int(c), int(r)) in (PLAZA, MARKET):
                break
        L = self.add_person(c, r, s=1.0, pose="walk", hat="helmet", hcol=(255, 200, 20), shirt=(200, 24, 24),
                            pants=(40, 34, 30), ff=True, extra="hose")
        self.answer["firefighter"] = iso(c, r)
        c, r = R.choice(self.park_spots)
        x, y = iso(c, r)
        self.add(c + r, (x - 12, y - 16, x + 12, y + 4), dog, x, y, 1, (250, 250, 250), True)
        self.answer["dalmatian"] = (x, y)


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


# ---------------------------------------------------------------- ground

def draw_tile(ctx, town, c, r, t):
    h = hsh(c, r)
    base = COL[t]
    j = ((h & 0xFF) - 128) / 128.0
    if t in (GRASS, YARD, FIELD):
        col = shade(base, 1 + 0.04 * j)
        if t == FIELD:
            col = shade(base, 1.06 if (c // 1) % 2 else 0.95)
    elif t in (SEA, SHALLOW, RIVER, POND):
        col = shade(base, 1 + 0.03 * j)
    elif t == PLAZA:
        col = base
    elif t == MARKET:
        col = base
    else:
        col = shade(base, 1 + 0.02 * j)
    pts = [iso(c, r), iso(c + 1, r), iso(c + 1, r + 1), iso(c, r + 1)]
    ctx.poly(pts, col, col)
    if t in (PLAZA, MARKET):
        alt = shade(col, 0.94)
        for a, b in ((0, 0), (0.5, 0.5)):
            ctx.poly([iso(c + a, r + b), iso(c + a + 0.5, r + b), iso(c + a + 0.5, r + b + 0.5), iso(c + a, r + b + 0.5)], alt, alt)
    if t in (GRASS, YARD):
        if h % 13 == 0:
            fc = [(250, 250, 250), (250, 210, 40), (230, 80, 120), (170, 120, 230)][(h >> 8) % 4]
            for k in range(4):
                x, y = iso(c + ((h >> (k * 3)) % 8) / 8, r + ((h >> (k * 3 + 9)) % 8) / 8)
                ctx.ell(x, y, 1.4, 1.0, fc)
        elif h % 5 == 0:
            x, y = iso(c + 0.5, r + 0.5)
            ctx.line([(x - 6, y), (x - 4, y - 4)], shade(col, 0.8), 0.8)
            ctx.line([(x + 3, y + 2), (x + 5, y - 2)], shade(col, 0.8), 0.8)
    elif t in (SEA, SHALLOW, RIVER):
        if h % 4 == 0:
            x, y = iso(c + ((h >> 4) % 10) / 10, r + ((h >> 9) % 10) / 10)
            ctx.line([(x - 9, y), (x - 3, y - 2), (x + 3, y), (x + 9, y - 2)], shade(col, 1.25), 1.0)
        if t == SHALLOW:
            for (dc, dr) in ((-1, 0), (0, -1), (1, 0), (0, 1)):
                if town.gt(c + dc, r + dr) == SAND:
                    a = {(-1, 0): (iso(c, r), iso(c, r + 1)), (0, -1): (iso(c, r), iso(c + 1, r)),
                         (1, 0): (iso(c + 1, r), iso(c + 1, r + 1)), (0, 1): (iso(c, r + 1), iso(c + 1, r + 1))}[(dc, dr)]
                    ctx.line(list(a), (240, 250, 255), 2.2)
    elif t == SAND:
        for k in range(3):
            x, y = iso(c + ((h >> (k * 4)) % 9) / 9, r + ((h >> (k * 4 + 7)) % 9) / 9)
            ctx.ell(x, y, 1.0, 0.7, shade(base, 0.85))
    elif t in (ROAD, BRIDGE):
        rc, rr = c % P, r % P
        if t == BRIDGE:
            for (dc, dr) in ((-1, 0), (0, -1), (1, 0), (0, 1)):
                if town.gt(c + dc, r + dr) == RIVER:
                    a = {(-1, 0): (iso(c, r), iso(c, r + 1)), (0, -1): (iso(c, r), iso(c + 1, r)),
                         (1, 0): (iso(c + 1, r), iso(c + 1, r + 1)), (0, 1): (iso(c, r + 1), iso(c + 1, r + 1))}[(dc, dr)]
                    ctx.line(list(a), (200, 196, 190), 3.0)
        if rr == 1 and rc not in (0, 1, 2, 3):
            ctx.line([iso(c + 0.2, r + 1), iso(c + 0.6, r + 1)], (250, 220, 90), 1.2)
        if rc == 1 and rr not in (0, 1, 2, 3):
            ctx.line([iso(c + 1, r + 0.2), iso(c + 1, r + 0.6)], (250, 220, 90), 1.2)
        if rr in (1, 2) and rc in (0, 3):
            for k in range(5):
                ctx.line([iso(c + 0.1 + k * 0.2, r + 0.1), iso(c + 0.1 + k * 0.2, r + 0.9)], (240, 240, 240), 2.6)
        if rc in (1, 2) and rr in (0, 3):
            for k in range(5):
                ctx.line([iso(c + 0.1, r + 0.1 + k * 0.2), iso(c + 0.9, r + 0.1 + k * 0.2)], (240, 240, 240), 2.6)
    elif t == WALK:
        ctx.line([iso(c + 0.5, r), iso(c + 0.5, r + 1)], shade(col, 0.88), 0.6)
        ctx.line([iso(c, r + 0.5), iso(c + 1, r + 0.5)], shade(col, 0.88), 0.6)
    elif t == LOT:
        ctx.line([iso(c, r), iso(c, r + 0.8)], (230, 230, 230), 1.0)
    elif t == PIER:
        for k in (0.25, 0.5, 0.75):
            ctx.line([iso(c + k, r), iso(c + k, r + 1)], shade(base, 0.75), 0.7)
    elif t == DIRT:
        for k in range(3):
            x, y = iso(c + ((h >> (k * 4)) % 9) / 9, r + ((h >> (k * 4 + 7)) % 9) / 9)
            ctx.ell(x, y, 1.6, 1.0, shade(base, 0.8))


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
            small = chunk.reduce(k)
            if scale != 1.0:
                small = small.resize((max(1, int(cw * scale)), max(1, int(ch * scale))), Image.LANCZOS)
            img.paste(small, (int((cx - x0) * scale), int((cy - y0) * scale)))
            done += 1
            if done % 8 == 0 or done == nx * ny:
                el = time.time() - t0
                log(f"  drawn {done}/{nx * ny} pieces  ({el:.0f} s, about {el / done * (nx * ny - done):.0f} s to go)")
    return img


def main(argv):
    seed, out, crop, scale, name = None, None, None, 1.0, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--seed":
            seed = int(argv[i + 1]); i += 2
        elif a == "--name":
            name = argv[i + 1].strip(); i += 2
        elif a == "--out":
            out = argv[i + 1]; i += 2
        elif a == "--crop":
            crop = tuple(int(v) for v in argv[i + 1:i + 5]); i += 5
        elif a == "--scale":
            scale = float(argv[i + 1]); i += 2
        else:
            i += 1
    name = " ".join((name or "").split())[:28] or HOME_TOWN
    if seed is None:   # the name picks the town: same name = same town, for anyone
        seed = 1 if name.lower() == HOME_TOWN.lower() else int(hashlib.sha256(name.lower().encode()).hexdigest()[:8], 16)
    tag = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "Town"
    here = os.path.dirname(os.path.abspath(__file__))
    top = os.path.dirname(here)
    out = out or os.path.join(top, f"Wheres_the_Firefighter_{tag}.jpg")
    print(f"WHERE'S THE FIREFIGHTER? picture maker v{VERSION}")
    print(f"Building the town of {name} (town number {seed}), picture {W:,} x {H:,} pixels")
    t0 = time.time()
    town = Town(seed, name)
    print(f"Town planned: {len(town.objs):,} things to draw ({time.time() - t0:.0f} s)")
    img = render(town, out, crop, scale)
    print("Saving the picture ...")
    img.save(out, quality=90, optimize=False)
    fx, fy = town.answer["firefighter"]
    dx, dy = town.answer["dalmatian"]
    print(f"Done in {time.time() - t0:.0f} s: {out}  ({os.path.getsize(out) / 1e6:.0f} MB)")
    print()
    print("Next: open Picture World Maker, choose this picture, pick a World spot and build the TPKX.")
    print(f"Stuck? The answers are in System Files\\ANSWER_{tag}.txt (no peeking).")
    with open(os.path.join(here, f"ANSWER_{tag}.txt"), "w") as f:
        f.write(f"Where's the Firefighter? {name} (town number {seed}) - answers (picture pixels from the top-left corner)\n")
        f.write(f"Firefighter (gold helmet): x {fx:.0f}, y {fy:.0f}\n")
        f.write(f"Lost dalmatian: x {dx:.0f}, y {dy:.0f}\n")
    return town, img


if __name__ == "__main__":
    main(sys.argv[1:])
