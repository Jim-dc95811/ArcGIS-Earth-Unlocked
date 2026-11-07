"""Dark Claude City - ARCHITECT plug-in: art-deco towers, hotel, theater, diner, warehouses, tenements.
All names and designs are original (invented for this city)."""
import math
import random

E = None

STONE = [(74, 72, 76), (62, 60, 66), (84, 76, 66), (58, 54, 50), (46, 58, 52), (70, 64, 58), (52, 56, 64), (88, 84, 80)]
BRICK = [(92, 50, 42), (78, 44, 38), (100, 70, 56), (70, 56, 50), (86, 62, 48), (64, 46, 44)]
ACCENT = [(196, 160, 90), (170, 150, 120), (150, 170, 160), (190, 120, 80), (210, 190, 140)]
HOTELS = ["HOTEL MERIDIAN", "HOTEL ARCADIA", "THE ROYALE", "HOTEL NOCTURNE", "THE BELMONT", "HOTEL CRESCENT"]
THEATERS = ["THE MOONLIGHT", "THE STARLIGHT", "THE ALHAMBRA", "THE GLOAMING", "THE RIALTO", "THE LYRIC"]
MOVIES = ["LAST CAR TO NOWHERE", "NO MORNING TOMORROW", "FOOTSTEPS IN THE RAIN", "CITY OF NO SUNRISE",
          "THE VANISHING HOUR", "SHADOWS ON 9TH STREET", "THE LAST TROLLEY", "WHISPER OF STEEL"]
DINERS = ["ALL NITE AUTOMAT", "EAT", "NIGHT OWL DINER", "THE BLUE PLATE", "CHROME CAFE", "EAT 24 HRS"]


def register(engine):
    global E
    E = engine
    E.BUILDERS.update({
        "deco_towers": b_deco_towers,
        "hotel": b_hotel,
        "theater": b_theater,
        "diner": b_diner,
        "warehouses": b_warehouses,
        "tenements": b_tenements,
    })


# ---------------------------------------------------------------- small helpers

def out_pt(face, c0, r0, c1, r1, u, z, out):
    """point on a visible face pushed `out` tiles toward the viewer"""
    if face == "L":
        return E.iso(c0 + (c1 - c0) * u, r1 + out, z)
    return E.iso(c1 + out, r1 - (r1 - r0) * u, z)


def pilasters(ctx, c0, r0, c1, r1, z0, h, col, every=0.9):
    for face, length in (("L", c1 - c0), ("R", r1 - r0)):
        n = max(2, int(length / every))
        for i in range(n + 1):
            u = i / n
            a = E.face_pt(face, c0, r0, c1, r1, u, z0 + 2)
            b = E.face_pt(face, c0, r0, c1, r1, u, z0 + h - 2)
            ctx.line([a, b], E.shade(col, 0.95 if face == "L" else 0.75), 1.6)


def band(ctx, c0, r0, c1, r1, z, col, w=2.2):
    ctx.line([E.face_pt("L", c0, r0, c1, r1, 0, z), E.face_pt("L", c0, r0, c1, r1, 1, z)], col, w)
    ctx.line([E.face_pt("R", c0, r0, c1, r1, 0, z), E.face_pt("R", c0, r0, c1, r1, 1, z)], E.shade(col, 0.8), w)


def pyramid(ctx, c0, r0, c1, r1, z, h, col, outline=None):
    cm, rm = (c0 + c1) / 2, (r0 + r1) / 2
    apex = E.iso(cm, rm, z + h)
    ctx.poly([E.iso(c0, r1, z), E.iso(c1, r1, z), apex], E.shade(col, 0.95), outline or E.OUT)
    ctx.poly([E.iso(c1, r1, z), E.iso(c1, r0, z), apex], E.shade(col, 0.72), outline or E.OUT)
    return apex


def water_tank(ctx, c, r, z):
    x, y = E.iso(c, r, z)
    for dx in (-8, 8):
        ctx.line([(x + dx, y), (x + dx, y - 14)], (30, 26, 24), 1.2)
    E.cyl(ctx, x, y - 14, 12, 6, 24, (82, 64, 50), (96, 74, 58))
    ctx.poly([(x - 12, y - 38), (x + 12, y - 38), (x, y - 50)], (60, 48, 40), E.OUT)


def slant_text(ctx, a, b, text, size, col):
    """letters set along the line a->b (a building face), centred, each letter upright"""
    f = E.font(size * ctx.k)
    widths = [ctx.d.textlength(ch, font=f) / ctx.k for ch in text]
    total = sum(widths) + len(text) * 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    ux, uy = 1.0, dy / dx if dx else 0.0
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    x, y = mx - ux * total / 2, my - uy * total / 2
    for ch, w in zip(text, widths):
        ctx.d.text(((x - ctx.ox) * ctx.k, (y - ctx.oy) * ctx.k - size * ctx.k * 0.55), ch, font=f, fill=col)
        x += ux * (w + 1.0)
        y += uy * (w + 1.0)


def bulbs_line(ctx, a, b, n, col=(255, 236, 170)):
    for i in range(n + 1):
        t = i / n
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        ctx.ell(x, y, 1.6, 1.6, col)


# ---------------------------------------------------------------- deco tower

def deco_tower(ctx, c0, r0, c1, r1, tiers, wall, accent, crown, seed):
    rnd = random.Random(seed)
    z = 0
    lit = 0.2 + rnd.random() * 0.25
    top_fp = None
    for k, (inset, h) in enumerate(tiers):
        a0, b0, a1, b1 = c0 + inset, r0 + inset, c1 - inset, r1 - inset
        if k > 0:   # setback roof terrace edge
            E.box(ctx, a0 - 0.12, b0 - 0.12, a1 + 0.12, b1 + 0.12, z, 5, E.shade(wall, 0.85), E.shade(wall, 0.9), E.shade(wall, 0.7))
            z += 5
        E.box(ctx, a0, b0, a1, b1, z, h, E.shade(wall, 0.78), E.shade(wall, 0.92), E.shade(wall, 0.7))
        E.noir_windows(ctx, a0, b0, a1, b1, z, h, rnd.random() * 1e9, lit_frac=lit, gap=0.42, wfrac=0.5)
        pilasters(ctx, a0, b0, a1, b1, z, h, E.shade(wall, 1.25), every=0.84 if k == 0 else 0.7)
        band(ctx, a0, b0, a1, b1, z + h - 3, accent, 2.4)
        if k == 0:   # entrance with lit door
            u = 0.42
            d = [E.face_pt("L", a0, b0, a1, b1, u, 0), E.face_pt("L", a0, b0, a1, b1, u + 0.16, 0),
                 E.face_pt("L", a0, b0, a1, b1, u + 0.16, 34), E.face_pt("L", a0, b0, a1, b1, u, 34)]
            ctx.poly(d, (255, 214, 140), E.OUT)
            band(ctx, a0, b0, a1, b1, 48, accent, 3)
        z += h
        top_fp = (a0, b0, a1, b1)
    a0, b0, a1, b1 = top_fp
    cm, rm = (a0 + a1) / 2, (b0 + b1) / 2
    if crown == "spire":
        s = min(a1 - a0, b1 - b0)
        for i in range(3):
            q = s * (0.18 + i * 0.1)
            E.box(ctx, a0 + q, b0 + q, a1 - q, b1 - q, z, 22, E.shade(wall, 0.85), E.shade(accent, 0.75), E.shade(accent, 0.55))
            z += 22
        top = E.iso(cm, rm, z)
        tip = E.iso(cm, rm, z + 110)
        ctx.line([top, tip], E.shade(accent, 0.9), 2.4)
        ctx.line([(top[0] - 6, top[1]), tip], E.shade(accent, 0.6), 1.0)
        E.glow(ctx, tip[0], tip[1], 30, 30, (255, 40, 40), 110)
        ctx.ell(tip[0], tip[1], 3.4, 3.4, (255, 90, 80))
    elif crown == "lit":
        apex = pyramid(ctx, a0, b0, a1, b1, z, 70 + (a1 - a0) * 18, E.shade(accent, 0.7))
        for (p, q) in ((E.iso(a0, b1, z), apex), (E.iso(a1, b1, z), apex), (E.iso(a1, b0, z), apex)):
            ctx.line([p, q], (255, 226, 150), 1.6)
        E.glow(ctx, apex[0], apex[1] + 40, 90, 70, (255, 200, 120), 70)
        ctx.line([apex, (apex[0], apex[1] - 60)], E.shade(accent, 0.9), 2.0)
        E.glow(ctx, apex[0], apex[1] - 60, 20, 20, (255, 230, 170), 120)
    else:   # flat roof with tanks and a beacon
        E.box(ctx, a0, b0, a1, b1, z, 6, E.shade(wall, 0.7), E.shade(wall, 0.85), E.shade(wall, 0.65))
        water_tank(ctx, a0 + (a1 - a0) * 0.3, b0 + (b1 - b0) * 0.35, z + 6)
        if a1 - a0 > 2:
            water_tank(ctx, a0 + (a1 - a0) * 0.7, b0 + (b1 - b0) * 0.6, z + 6)
        x, y = E.iso(a1 - 0.2, b1 - 0.2, z + 6)
        ctx.line([(x, y), (x, y - 40)], (40, 40, 44), 1.2)
        E.glow(ctx, x, y - 40, 14, 14, (255, 50, 50), 100)


def b_deco_towers(town, bx, by):
    R = town.rnd
    town.fill(bx, by, E.PLAZA)
    n = R.choice((1, 2, 2, 3, 4))
    spots = {1: [(1.5, 1.5, 10.5)], 2: [(0.8, 0.8, 6.4), (7.4, 6.8, 6.0)], 3: [(0.6, 0.6, 6.2), (7.6, 0.8, 5.4), (3.5, 7.8, 5.6)],
             4: [(0.6, 0.6, 5.6), (7.6, 0.6, 5.6), (0.6, 7.6, 5.6), (7.6, 7.6, 5.6)]}[n]
    for (a, b, s) in spots:
        c0, r0 = bx + a, by + b
        c1, r1 = c0 + s, r0 + s * (0.78 + R.random() * 0.22)
        wall = R.choice(STONE)
        accent = R.choice(ACCENT)
        ntiers = R.choice((2, 3, 3, 4))
        budget = R.randint(14, 23) if n <= 2 else R.randint(9, 17)   # storeys
        tiers, inset = [], 0.0
        for k in range(ntiers):
            st = max(2, int(budget * (0.45 if k == 0 else 0.55 / (ntiers - 1)) + R.randint(-1, 1)))
            tiers.append((inset, st * 42))
            inset += 0.45 + R.random() * 0.45 * (s / 6)
            if (c1 - c0) - 2 * inset < 1.2:
                break
        crown = R.choice(("spire", "lit", "flat", "spire", "lit"))
        hh = sum(h for _, h in tiers) + 220
        town.add_box_obj(c0, r0, c1, r1, hh, deco_tower, c0, r0, c1, r1, tiers, wall, accent, crown, R.random() * 1e9)
        town.add_light(c0 + (c1 - c0) * 0.5, r1 + 0.6, 1.2, (255, 214, 140), 60)
    for k in range(4):
        town.add_lamp(bx + 0.3 + k * 4.4, by + 13.6)
    town.crowd(bx, by, 14, 14, 45)


# ---------------------------------------------------------------- hotel

def hotel(ctx, c0, r0, c1, r1, h, wall, accent, name, ncol, seed):
    rnd = random.Random(seed)
    E.box(ctx, c0, r0, c1, r1, 0, h, E.shade(wall, 0.78), E.shade(wall, 0.92), E.shade(wall, 0.7))
    E.noir_windows(ctx, c0, r0, c1, r1, 60, h - 60, rnd.random() * 1e9, lit_frac=0.42, gap=0.5, wfrac=0.45)
    pilasters(ctx, c0, r0, c1, r1, 0, h, E.shade(wall, 1.2), every=1.2)
    band(ctx, c0, r0, c1, r1, 58, accent, 3)
    band(ctx, c0, r0, c1, r1, h - 4, accent, 3)
    # lobby glow along the ground floor
    for face in ("L", "R"):
        ctx.poly([E.face_pt(face, c0, r0, c1, r1, 0.08, 6), E.face_pt(face, c0, r0, c1, r1, 0.92, 6),
                  E.face_pt(face, c0, r0, c1, r1, 0.92, 40), E.face_pt(face, c0, r0, c1, r1, 0.08, 40)],
                 (240, 196, 120) if face == "L" else (190, 150, 90), None)
    # roof: lit name band
    E.box(ctx, c0 + 0.3, r0 + 0.3, c1 - 0.3, r1 - 0.3, h, 30, E.shade(wall, 0.7), E.shade(wall, 0.8), E.shade(wall, 0.6))
    x, y = E.face_pt("L", c0, r0, c1, r1, 0.5, h + 60)
    ctx.line([E.face_pt("L", c0 + 0.3, r0, c1 - 0.3, r1 - 0.3, 0.1, h + 30), (x - 80, y)], (40, 40, 40), 1.0)
    E.neon_text(ctx, x, y, name, ncol, size=30)
    # canopy over the entrance
    ua, ub = 0.35, 0.65
    a, b = E.face_pt("L", c0, r0, c1, r1, ua, 46), E.face_pt("L", c0, r0, c1, r1, ub, 46)
    c, d = out_pt("L", c0, r0, c1, r1, ub, 42, 1.0), out_pt("L", c0, r0, c1, r1, ua, 42, 1.0)
    for u in (ua + 0.01, ub - 0.01):
        ctx.line([out_pt("L", c0, r0, c1, r1, u, 0, 0.95), out_pt("L", c0, r0, c1, r1, u, 42, 0.95)], (180, 160, 110), 1.6)
    ctx.poly([a, b, c, d], (120, 20, 30), E.OUT)
    bulbs_line(ctx, d, c, 14)
    # vertical blade sign at the front corner (c0, r1)
    letters = name.replace("HOTEL ", "").replace("THE ", "")
    top = h - 40
    sx, sy = out_pt("L", c0, r0, c1, r1, 0.0, top, 0.55)
    lh = 34
    ln = len(letters)
    ctx.poly([(sx - 17, sy - 10), (sx + 17, sy - 10), (sx + 17, sy + ln * lh + 6), (sx - 17, sy + ln * lh + 6)], (24, 20, 26), (60, 50, 50))
    for i, ch in enumerate(letters):
        if ch == " ":
            continue
        E.neon_text(ctx, sx, sy + 14 + i * lh, ch, ncol, size=26, glow_px=8)


def b_hotel(town, bx, by):
    R = town.rnd
    town.fill(bx, by, E.CONCRETE)
    c0, r0, c1, r1 = bx + 1.0, by + 1.0, bx + 12.6, by + 9.0
    h = 42 * R.randint(12, 18) + 60
    name = R.choice(HOTELS)
    ncol = R.choice(E.NEON)
    town.add_box_obj(c0, r0, c1, r1, h + 160, hotel, c0, r0, c1, r1, h, R.choice(STONE), R.choice(ACCENT), name, ncol, R.random() * 1e9,
                     key=(c0 + c1 + r0 + r1) / 2)
    # taxis waiting on the forecourt + doorman + guests
    for k in range(R.randint(2, 4)):
        town.add_car(bx + 1.5 + k * 1.9, by + 11.6, "c", (214, 170, 40))
    town.add_person(c0 + (c1 - c0) * 0.5, r1 + 0.6, shirt=(120, 20, 30), hat="cap", hcol=(120, 20, 30), coat=True, extra=None, pose="stand")
    town.add_light(c0 + (c1 - c0) * 0.5, r1 + 1.2, 2.2, (255, 214, 140), 85)
    town.crowd(bx, by + 9.6, 14, 4, 30)
    for k in range(3):
        town.add_lamp(bx + 0.5 + k * 6.5, by + 13.6)


# ---------------------------------------------------------------- theater

def theater(ctx, c0, r0, c1, r1, h, wall, name, movie, ncol, seed):
    rnd = random.Random(seed)
    E.box(ctx, c0, r0, c1, r1, 0, h, E.shade(wall, 0.75), E.shade(wall, 0.92), E.shade(wall, 0.7))
    pilasters(ctx, c0, r0, c1, r1, 0, h, E.shade(wall, 1.25), every=0.8)
    band(ctx, c0, r0, c1, r1, h - 4, (200, 170, 110), 3)
    # lobby doors, bright
    ctx.poly([E.face_pt("L", c0, r0, c1, r1, 0.25, 4), E.face_pt("L", c0, r0, c1, r1, 0.75, 4),
              E.face_pt("L", c0, r0, c1, r1, 0.75, 44), E.face_pt("L", c0, r0, c1, r1, 0.25, 44)], (255, 220, 150), E.OUT)
    for u in (0.35, 0.45, 0.55, 0.65):
        ctx.line([E.face_pt("L", c0, r0, c1, r1, u, 4), E.face_pt("L", c0, r0, c1, r1, u, 44)], (120, 80, 40), 1.0)
    # poster frames on the right face
    for u in (0.2, 0.45, 0.7):
        ctx.poly([E.face_pt("R", c0, r0, c1, r1, u, 10), E.face_pt("R", c0, r0, c1, r1, u + 0.12, 10),
                  E.face_pt("R", c0, r0, c1, r1, u + 0.12, 46), E.face_pt("R", c0, r0, c1, r1, u, 46)],
                 rnd.choice([(150, 40, 40), (40, 70, 120), (150, 120, 40)]), (200, 180, 120))
    # marquee: a deep box out over the pavement, rows of bulbs, title text
    ua, ub = 0.1, 0.9
    zb, zt = 56, 96
    mc0, mc1 = c0 + (c1 - c0) * ua, c0 + (c1 - c0) * ub
    E.box(ctx, mc0, r1, mc1, r1 + 1.1, zb, zt - zb, (40, 30, 30), (236, 226, 200), (170, 160, 140))
    for z in (zb + 4, zt - 4):
        bulbs_line(ctx, E.iso(mc0, r1 + 1.1, z), E.iso(mc1, r1 + 1.1, z), 34)
        bulbs_line(ctx, E.iso(mc1, r1 + 1.1, z), E.iso(mc1, r1, z), 8)
    for z in range(zb + 4, zt - 3, 9):
        ctx.ell(*E.iso(mc0, r1 + 1.1, z), 1.6, 1.6, (255, 236, 170))
    mx, my = E.iso((mc0 + mc1) / 2, r1 + 1.1, (zb + zt) / 2)
    E.glow(ctx, mx, my + 40, 160, 60, (255, 220, 150), 50)
    slant_text(ctx, E.iso(mc0, r1 + 1.1, (zb + zt) / 2), E.iso(mc1, r1 + 1.1, (zb + zt) / 2), movie, 15, (20, 16, 16))
    # neon name over the marquee
    nx, ny = E.face_pt("L", c0, r0, c1, r1, 0.5, zt + 40)
    E.neon_text(ctx, nx, ny, name, ncol, size=32)
    # vertical blade sign at the corner
    sx, sy = out_pt("L", c0, r0, c1, r1, 0.06, h - 10, 0.5)
    word = name.replace("THE ", "")
    lh = 30
    ctx.poly([(sx - 16, sy - 8), (sx + 16, sy - 8), (sx + 16, sy + len(word) * lh + 4), (sx - 16, sy + len(word) * lh + 4)], (30, 24, 26), (200, 170, 110))
    for i in range(len(word) * 2 + 1):
        ctx.ell(sx - 16, sy - 8 + i * lh / 2, 1.4, 1.4, (255, 236, 170))
        ctx.ell(sx + 16, sy - 8 + i * lh / 2, 1.4, 1.4, (255, 236, 170))
    for i, ch in enumerate(word):
        E.neon_text(ctx, sx, sy + 12 + i * lh, ch, ncol, size=22, glow_px=7)


def b_theater(town, bx, by):
    R = town.rnd
    town.fill(bx, by, E.PLAZA)
    c0, r0, c1, r1 = bx + 1.2, by + 1.0, bx + 12.8, by + 8.6
    h = R.randint(4, 6) * 42 + 20
    name, movie = R.choice(THEATERS), R.choice(MOVIES)
    town.add_box_obj(c0, r0, c1, r1, h + 120, theater, c0, r0, c1, r1, h, R.choice(STONE + BRICK[:2]), name, movie, R.choice(E.NEON), R.random() * 1e9)
    town.add_light((c0 + c1) / 2, r1 + 1.6, 3.0, (255, 220, 150), 95)
    # the queue: a line of people along the pavement
    for k in range(26):
        town.add_person(c0 + 0.4 + k * 0.42, r1 + 1.6 + (k % 2) * 0.12, pose="stand", f=-1)
    town.crowd(bx, by + 10.6, 14, 3, 40)
    for k in range(3):
        town.add_lamp(bx + 0.5 + k * 6.5, by + 13.6)


# ---------------------------------------------------------------- diner

def diner(ctx, c0, r0, c1, r1, name, ncol, seed):
    rnd = random.Random(seed)
    h = 46
    chrome, chrome2 = (176, 180, 188), (120, 124, 134)
    rm = (r0 + r1) / 2
    # rounded end on the right (drawn first, the body covers its inner half)
    ry = (r1 - r0) / 2
    x, y = E.iso(c1 - 0.05, rm)
    E.cyl(ctx, x, y, ry * 1.414 * E.HW * 0.62, ry * 1.414 * E.HH * 0.62, h, chrome2, (90, 94, 102))
    E.box(ctx, c0, r0, c1, r1, 0, h, (90, 94, 102), chrome, chrome2)
    # bright window band with diners inside
    za, zb = 14, 36
    ctx.poly([E.face_pt("L", c0, r0, c1, r1, 0.04, za), E.face_pt("L", c0, r0, c1, r1, 0.96, za),
              E.face_pt("L", c0, r0, c1, r1, 0.96, zb), E.face_pt("L", c0, r0, c1, r1, 0.04, zb)], (255, 236, 190), E.OUT)
    for i in range(int((c1 - c0) * 4)):
        u = 0.07 + i / ((c1 - c0) * 4) * 0.86
        if rnd.random() < 0.7:
            px, py = E.face_pt("L", c0, r0, c1, r1, u, za + 9)
            ctx.ell(px, py - 6, 2.6, 2.8, rnd.choice(E.SKIN))
            ctx.poly([(px - 3.2, py - 3), (px + 3.2, py - 3), (px + 3.6, py + 4), (px - 3.6, py + 4)], rnd.choice([(40, 40, 46), (110, 30, 40), (60, 60, 80), (140, 116, 82)]), None)
    for u in range(1, 10):
        ctx.line([E.face_pt("L", c0, r0, c1, r1, u / 10, za), E.face_pt("L", c0, r0, c1, r1, u / 10, zb)], (150, 150, 156), 0.9)
    for z in (8, 42):
        band(ctx, c0, r0, c1, r1, z, (230, 232, 240), 1.6)
    band(ctx, c0, r0, c1, r1, 11, (200, 40, 50), 2.2)
    # roof sign on a frame
    sx, sy = E.iso((c0 + c1) / 2, rm, h)
    ctx.line([(sx - 50, sy), (sx - 50, sy - 30)], (40, 40, 44), 1.4)
    ctx.line([(sx + 50, sy), (sx + 50, sy - 30)], (40, 40, 44), 1.4)
    E.neon_text(ctx, sx, sy - 44, name, ncol, size=28)
    E.glow(ctx, *E.face_pt("L", c0, r0, c1, r1, 0.5, 20), 150, 60, (255, 236, 190), 50)


def b_diner(town, bx, by):
    R = town.rnd
    town.fill(bx, by, E.LOT)
    name, ncol = R.choice(DINERS), R.choice(E.NEON)
    c0, r0, c1, r1 = bx + 3.0, by + 8.0, bx + 9.5, by + 10.4
    town.add_box_obj(c0, r0, c1 + 1, r1, 160, diner, c0, r0, c1, r1, name, ncol, R.random() * 1e9)
    town.add_light((c0 + c1) / 2, r1 + 1.0, 2.8, (255, 236, 190), 90)
    for k in range(R.randint(3, 6)):   # parked cars
        town.add_car(bx + 0.5 + k * 2.2, by + 12.4, "r")
    # walk-ups behind
    for i in range(3):
        a, b = bx + 0.4 + i * 4.6, by + 0.4
        cc1, rr1 = a + 3.8, b + 5.6
        hh = 42 * R.randint(3, 5) + 8
        town.add_box_obj(a, b, cc1, rr1, hh + 90, tenement, a, b, cc1, rr1, hh, R.choice(BRICK), R.random() * 1e9)
    town.crowd(bx, by + 10.6, 14, 3.2, 22)
    town.add_lamp(bx + 1, by + 7)
    town.add_lamp(bx + 12.5, by + 7)


# ---------------------------------------------------------------- warehouses

def warehouse(ctx, c0, r0, c1, r1, h, wall, seed):
    rnd = random.Random(seed)
    E.box(ctx, c0, r0, c1, r1, 0, h, E.shade(wall, 0.7), E.shade(wall, 0.88), E.shade(wall, 0.66))
    # sawtooth roof along c
    n = max(2, int((c1 - c0) / 1.2))
    for i in range(n):
        a = c0 + (c1 - c0) * i / n
        b = c0 + (c1 - c0) * (i + 1) / n
        p1, p2 = E.iso(a, r1, h), E.iso(a, r0, h)
        q1, q2 = E.iso(b, r1, h + 26), E.iso(b, r0, h + 26)
        ctx.poly([p1, p2, q2, q1], (46, 44, 46), E.OUT)
        ctx.poly([E.iso(b, r1, h), E.iso(b, r1, h + 26), E.iso(b, r0, h + 26), E.iso(b, r0, h)], (90, 110, 120) if rnd.random() < 0.3 else (40, 46, 54), E.OUT)
    # loading doors on the front face, a few dim lights over them
    nd = max(2, int((c1 - c0) / 1.5))
    for i in range(nd):
        u = (i + 0.2) / nd
        w = 0.6 / nd
        open_ = rnd.random() < 0.25
        ctx.poly([E.face_pt("L", c0, r0, c1, r1, u, 0), E.face_pt("L", c0, r0, c1, r1, u + w, 0),
                  E.face_pt("L", c0, r0, c1, r1, u + w, 38), E.face_pt("L", c0, r0, c1, r1, u, 38)],
                 (200, 160, 90) if open_ else (54, 52, 50), E.OUT)
        if not open_:
            for z in range(6, 38, 6):
                ctx.line([E.face_pt("L", c0, r0, c1, r1, u, z), E.face_pt("L", c0, r0, c1, r1, u + w, z)], (70, 68, 66), 0.6)
        if rnd.random() < 0.4:
            lx, ly = E.face_pt("L", c0, r0, c1, r1, u + w / 2, 48)
            ctx.ell(lx, ly, 2.4, 1.8, (255, 220, 150))
            E.glow(ctx, lx, ly + 14, 30, 22, (255, 200, 120), 50)
    # stencilled number
    x, y = E.face_pt("R", c0, r0, c1, r1, 0.5, h * 0.6)
    f = E.font(18 * ctx.k)
    t = f"No. {rnd.randint(2, 99)}"
    ctx.d.text(((x - ctx.ox) * ctx.k - ctx.d.textlength(t, font=f) / 2, (y - ctx.oy) * ctx.k), t, font=f, fill=(150, 140, 120))


def crate(ctx, c, r, z, s, col):
    E.box(ctx, c, r, c + s, r + s, z, s * 26, col)
    ctx.line([E.iso(c, r + s, z), E.iso(c + s, r + s, z + s * 26)], E.shade(col, 0.6), 0.6)


def truck(ctx, c, r, col):
    E.box(ctx, c, r + 0.15, c + 1.5, r + 0.85, 4, 30, (120, 116, 108), (140, 136, 126), (100, 96, 90))
    E.box(ctx, c + 1.5, r + 0.2, c + 2.1, r + 0.8, 4, 20, col)
    E.box(ctx, c + 1.55, r + 0.25, c + 1.95, r + 0.75, 24, 8, E.shade(col, 1.05), (60, 70, 86), (50, 60, 76))
    for u in (0.2, 0.8):
        x, y = E.face_pt("L", c, r + 0.15, c + 2.1, r + 0.85, u, 2)
        ctx.ell(x, y, 4.6, 4.6, (16, 16, 18))
    x, y = E.iso(c + 2.1, r + 0.5, 12)
    E.glow(ctx, x + 30, y + 14, 50, 18, (255, 236, 180), 60)


def b_warehouses(town, bx, by):
    R = town.rnd
    town.fill(bx, by, E.CONCRETE)
    for j in range(2):
        c0, r0 = bx + 0.6, by + 0.6 + j * 7
        c1, r1 = c0 + 12.6 - R.random() * 3, r0 + 4.4
        h = R.randint(60, 110)
        town.add_box_obj(c0, r0, c1, r1, h + 40, warehouse, c0, r0, c1, r1, h, R.choice(BRICK), R.random() * 1e9)
        # crates in the yard in front
        for _ in range(R.randint(3, 7)):
            a, b = c0 + R.random() * (c1 - c0 - 1), r1 + 0.4 + R.random() * 1.2
            s = 0.3 + R.random() * 0.25
            col = R.choice([(110, 84, 54), (90, 70, 46), (70, 80, 70)])
            town.add_box_obj(a, b, a + s, b + s, s * 60, crate, a, b, 0, s, col)
            if R.random() < 0.4:
                town.add_box_obj(a, b, a + s, b + s, s * 60, crate, a + 0.04, b + 0.04, s * 26, s * 0.9, col, key=a + b + s + 0.01)
    a, b = bx + 2 + R.random() * 6, by + 5.4
    town.add_box_obj(a, b, a + 2.1, b + 1, 50, truck, a, b, R.choice([(60, 70, 60), (90, 40, 30), (40, 50, 70)]))
    town.crowd(bx, by, 14, 14, 6)
    town.add_lamp(bx + 7, by + 6)


# ---------------------------------------------------------------- tenements

def tenement(ctx, c0, r0, c1, r1, h, wall, seed):
    rnd = random.Random(seed)
    E.box(ctx, c0, r0, c1, r1, 0, h, E.shade(wall, 0.7), E.shade(wall, 0.92), E.shade(wall, 0.7))
    E.noir_windows(ctx, c0, r0, c1, r1, 0, h, rnd.random() * 1e9, lit_frac=0.18 + rnd.random() * 0.15, gap=0.55, wfrac=0.45)
    # brick courses
    for z in range(14, int(h), 14):
        ctx.line([E.face_pt("L", c0, r0, c1, r1, 0, z), E.face_pt("L", c0, r0, c1, r1, 1, z)], E.shade(wall, 0.8), 0.5)
    # cornice
    E.box(ctx, c0 - 0.06, r0 - 0.06, c1 + 0.06, r1 + 0.06, h, 6, E.shade(wall, 0.6), E.shade(wall, 1.1), E.shade(wall, 0.85))
    # fire escapes on both visible faces
    floors = int((h - 8) / 42)
    iron = (22, 22, 24)
    for face in ("L", "R"):
        if rnd.random() < 0.25:
            continue
        ua = 0.18 + rnd.random() * 0.3
        ub = ua + 0.32
        for f in range(1, floors):
            z = f * 42 + 6
            p = [E.face_pt(face, c0, r0, c1, r1, ua, z), E.face_pt(face, c0, r0, c1, r1, ub, z),
                 out_pt(face, c0, r0, c1, r1, ub, z, 0.3), out_pt(face, c0, r0, c1, r1, ua, z, 0.3)]
            ctx.poly(p, (34, 34, 36), iron)
            for zz in (z + 10,):
                ctx.line([out_pt(face, c0, r0, c1, r1, ua, zz, 0.3), out_pt(face, c0, r0, c1, r1, ub, zz, 0.3)], iron, 1.0)
            for u in (ua, ub):
                ctx.line([out_pt(face, c0, r0, c1, r1, u, z, 0.3), out_pt(face, c0, r0, c1, r1, u, z + 10, 0.3)], iron, 0.8)
            if f < floors - 1:   # zig-zag stair to the next landing
                a = out_pt(face, c0, r0, c1, r1, ua if f % 2 else ub, z, 0.2)
                b = out_pt(face, c0, r0, c1, r1, ub if f % 2 else ua, z + 42, 0.2)
                ctx.line([a, b], iron, 1.6)
                for t in range(1, 7):
                    q = (a[0] + (b[0] - a[0]) * t / 7, a[1] + (b[1] - a[1]) * t / 7)
                    ctx.line([(q[0] - 2, q[1]), (q[0] + 2, q[1])], iron, 0.7)
    # laundry line across the front
    if rnd.random() < 0.55 and floors > 2:
        z = rnd.randint(1, floors - 1) * 42 + 30
        a = out_pt("L", c0, r0, c1, r1, 0.05, z, 0.05)
        b = out_pt("L", c0, r0, c1, r1, 0.95, z - 6, 0.9)
        ctx.line([a, b], (150, 150, 150), 0.6)
        for i in range(1, 9):
            t = i / 9
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t + 1
            ctx.poly([(x - 3, y), (x + 3, y), (x + 3, y + 7 + (i % 3)), (x - 3, y + 7 + (i % 3))],
                     rnd.choice([(200, 196, 186), (150, 40, 40), (60, 80, 130), (190, 170, 120)]), None)
    # rooftop: chimneys, a tank sometimes
    for _ in range(rnd.randint(1, 3)):
        a = c0 + 0.2 + rnd.random() * (c1 - c0 - 0.6)
        b = r0 + 0.2 + rnd.random() * (r1 - r0 - 0.6)
        E.box(ctx, a, b, a + 0.28, b + 0.28, h + 6, 22, (70, 50, 44))
        x, y = E.iso(a + 0.14, b + 0.14, h + 30)
        ctx.ell(x + 4, y - 6, 6, 4, (80, 80, 90, 70))
    if rnd.random() < 0.3:
        water_tank(ctx, c0 + (c1 - c0) * 0.55, r0 + (r1 - r0) * 0.45, h + 6)


def b_tenements(town, bx, by):
    R = town.rnd
    town.fill(bx, by, E.CONCRETE)
    # a court of walk-ups: 3 x 2 rows with an alley between
    for j in range(2):
        for i in range(3):
            c0, r0 = bx + 0.4 + i * 4.6, by + 0.5 + j * 7.0
            c1, r1 = c0 + 3.7 + R.random() * 0.4, r0 + 4.6 + R.random() * 0.6
            h = 42 * R.randint(3, 6) + 8
            town.add_box_obj(c0, r0, c1, r1, h + 90, tenement, c0, r0, c1, r1, h, R.choice(BRICK + STONE[2:4]), R.random() * 1e9)
            if R.random() < 0.4:
                town.add_person(c0 + 1 + R.random() * 2, r1 + 0.5, pose="stand")
    for _ in range(4):   # trash cans / crates in the alleys
        a, b = bx + R.random() * 13, by + 6.1 + R.random() * 0.6
        town.add_box_obj(a, b, a + 0.3, b + 0.3, 20, crate, a, b, 0, 0.3, (60, 62, 60))
    town.add_lamp(bx + 7, by + 6.4)
    town.crowd(bx, by, 14, 14, 18)
