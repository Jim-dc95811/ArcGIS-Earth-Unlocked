"""Dark Claude City - the uncanny: the clock tower, blocks that shift, the canal, the edge of the world,
searchlights, rain and fog. Original designs only. Loaded by darkcity.py (register(E))."""
import math
import random

E = None

FOG = (120, 130, 150)
WIRE = (180, 220, 255)
STONE = (78, 74, 72)


def register(engine):
    global E
    E = engine
    E.BUILDERS["clocktower"] = b_clocktower
    E.BUILDERS["shifting"] = b_shifting
    E.BUILDERS["canalside"] = b_canalside
    E.SPECIALS[(0, 0)] = "clocktower"
    E.SPECIALS[(2, -3)] = "shifting"
    E.SPECIALS[(-3, 2)] = "shifting"
    E.EDGE_HOOKS.append(edge_of_the_world)
    E.FINAL_HOOKS.append(searchlights)
    E.OVERLAYS.append(rain_and_fog)


# ---------------------------------------------------------------- small helpers

def h01(*v):
    """deterministic 0..1 from numbers"""
    x = 0
    for i, a in enumerate(v):
        x ^= (int(a * 1000) + 7919 * (i + 1)) * 2654435761
        x = (x ^ (x >> 15)) * 2246822519 & 0xFFFFFFFF
    return (x & 0xFFFFFF) / 0xFFFFFF


def face_poly(face, c0, r0, c1, r1, u0, u1, z0, z1):
    fp = E.face_pt
    return [fp(face, c0, r0, c1, r1, u0, z0), fp(face, c0, r0, c1, r1, u1, z0),
            fp(face, c0, r0, c1, r1, u1, z1), fp(face, c0, r0, c1, r1, u0, z1)]


def face_circle(face, c0, r0, c1, r1, uc, zc, ru, rz, n=28):
    """a circle lying on a building face: u along the face (0..1), z up"""
    return [E.face_pt(face, c0, r0, c1, r1, uc + ru * math.cos(a), zc + rz * math.sin(a))
            for a in [k * 2 * math.pi / n for k in range(n)]]


# ---------------------------------------------------------------- the clock tower

def clock_face(ctx, face, c0, r0, c1, r1, zc, rz, seed):
    # face length in screen px for scaling a round dial
    a = E.face_pt(face, c0, r0, c1, r1, 0, zc)
    b = E.face_pt(face, c0, r0, c1, r1, 1, zc)
    flen = math.hypot(b[0] - a[0], b[1] - a[1])
    ru = rz / flen * 1.0
    mx, my = E.face_pt(face, c0, r0, c1, r1, 0.5, zc)
    E.glow(ctx, mx, my, rz * 1.8, rz * 1.6, (255, 236, 180), 60, 5)
    ctx.poly(face_circle(face, c0, r0, c1, r1, 0.5, zc, ru * 1.12, rz * 1.12), (60, 52, 40))
    ctx.poly(face_circle(face, c0, r0, c1, r1, 0.5, zc, ru, rz), (250, 236, 196), (40, 34, 26))
    for k in range(12):
        ang = k * math.pi / 6
        p0 = E.face_pt(face, c0, r0, c1, r1, 0.5 + math.cos(ang) * ru * 0.78, zc + math.sin(ang) * rz * 0.78)
        p1 = E.face_pt(face, c0, r0, c1, r1, 0.5 + math.cos(ang) * ru * 0.92, zc + math.sin(ang) * rz * 0.92)
        ctx.line([p0, p1], (40, 30, 24), 2.4 if k % 3 == 0 else 1.2)
    # the hands never agree between faces (the city keeps its own time)
    rnd = random.Random(seed)
    for length, width_px in ((0.55, 3.2), (0.8, 1.8)):
        ang = rnd.uniform(0, 2 * math.pi)
        p = E.face_pt(face, c0, r0, c1, r1, 0.5 + math.cos(ang) * ru * length, zc + math.sin(ang) * rz * length)
        ctx.line([(mx, my), p], (24, 18, 14), width_px)
    ctx.ell(mx, my, 3, 3, (24, 18, 14))


def draw_clocktower(ctx, cm, rm, seed):
    stone = (86, 80, 76)
    dark = (54, 50, 50)
    # stepped base
    for (s, z0, h) in ((3.0, 0, 120), (2.4, 120, 140), (1.9, 260, 330)):
        c0, r0, c1, r1 = cm - s / 2, rm - s / 2, cm + s / 2, rm + s / 2
        E.box(ctx, c0, r0, c1, r1, z0, h, E.shade(stone, 0.8), E.shade(stone, 1.0), E.shade(stone, 0.72))
        E.noir_windows(ctx, c0, r0, c1, r1, z0, h, seed + z0, lit_frac=0.22, floor_h=48, gap=0.4, wfrac=0.35)
        # ribs at the corners
        for (cc, rr) in ((c0, r1), (c1, r1), (c1, r0)):
            ctx.line([E.iso(cc, rr, z0), E.iso(cc, rr, z0 + h)], E.shade(stone, 1.25), 2.0)
    # door with light
    ctx.poly(face_poly("L", cm - 1.5, rm - 1.5, cm + 1.5, rm + 1.5, 0.42, 0.58, 0, 70), (255, 200, 120))
    # clock stage
    c0, r0, c1, r1 = cm - 1.45, rm - 1.45, cm + 1.45, rm + 1.45
    E.box(ctx, c0, r0, c1, r1, 590, 230, E.shade(dark, 0.9), E.shade(stone, 0.95), E.shade(stone, 0.7))
    for face in ("L", "R"):
        clock_face(ctx, face, c0, r0, c1, r1, 700, 54, seed + (1 if face == "L" else 2))
    # cornice
    E.box(ctx, c0 - 0.15, r0 - 0.15, c1 + 0.15, r1 + 0.15, 820, 18, E.shade(stone, 1.1), E.shade(stone, 1.0), E.shade(stone, 0.75))
    # belfry with arches lit from inside
    b0, q0, b1, q1 = cm - 0.9, rm - 0.9, cm + 0.9, rm + 0.9
    E.box(ctx, b0, q0, b1, q1, 838, 90, dark, E.shade(stone, 0.9), E.shade(stone, 0.65))
    for face in ("L", "R"):
        for u in (0.2, 0.55):
            ctx.poly(face_poly(face, b0, q0, b1, q1, u, u + 0.25, 850, 910), (255, 190, 100))
    # spire
    apex = E.iso(cm, rm, 1060)
    for face_pts, col in (([E.iso(b0, q1, 928), E.iso(b1, q1, 928)], E.shade(stone, 0.75)),
                          ([E.iso(b1, q1, 928), E.iso(b1, q0, 928)], E.shade(stone, 0.55))):
        ctx.poly(face_pts + [apex], col)
    ctx.line([apex, (apex[0], apex[1] - 26)], (40, 40, 40), 1.6)
    E.glow(ctx, apex[0], apex[1] - 28, 30, 30, (255, 60, 60), 90, 4)
    ctx.ell(apex[0], apex[1] - 28, 3.5, 3.5, (255, 90, 80))


def b_clocktower(town, bx, by):
    R = town.rnd
    town.fill(bx, by, E.PLAZA)
    cm, rm = bx + 7, by + 7
    top_y = E.iso(cm, rm, 1100)[1]
    x0 = E.iso(cm - 2, rm + 2)[0] - 80
    x1 = E.iso(cm + 2, rm - 2)[0] + 80
    town.add(cm + rm + 1.5, (x0, top_y - 40, x1, E.iso(cm + 1.5, rm + 1.5)[1] + 20), draw_clocktower, cm, rm, int(R.random() * 1e6))
    # ring of lamps and benches of people waiting for the hour
    for k in range(12):
        a = k * math.pi / 6
        town.add_lamp(cm + math.cos(a) * 5.4, rm + math.sin(a) * 5.4)
    for _ in range(46):
        a = R.uniform(0, 2 * math.pi)
        d = R.uniform(3.0, 6.6)
        town.add_person(cm + math.cos(a) * d, rm + math.sin(a) * d, pose="stand" if R.random() < 0.7 else "walk")
    # paving rings
    pts = [E.iso(cm + 2.6 * math.cos(a), rm + 2.6 * math.sin(a)) for a in [k * math.pi / 18 for k in range(37)]]
    town.add(cm + rm - 2.5, (min(p[0] for p in pts) - 4, min(p[1] for p in pts) - 4, max(p[0] for p in pts) + 4, max(p[1] for p in pts) + 4),
             lambda ctx, pts: ctx.line(pts, (96, 88, 80), 2.0), pts)


# ---------------------------------------------------------------- blocks that shift

def sheared_box(ctx, c0, r0, c1, r1, h, wall, dx, dy, seed):
    A, B, C = E.iso(c0, r1), E.iso(c1, r1), E.iso(c1, r0)
    def up(c, r):
        x, y = E.iso(c, r, h)
        return (x + dx, y + dy)
    A2, B2, C2, D2 = up(c0, r1), up(c1, r1), up(c1, r0), up(c0, r0)
    ctx.poly([A, B, B2, A2], E.shade(wall, 0.95))
    ctx.poly([B, C, C2, B2], E.shade(wall, 0.72))
    ctx.poly([D2, C2, B2, A2], E.shade(wall, 0.8))
    rnd = random.Random(seed)
    floors = int(h / 42)
    for f in range(floors):
        t0, t1 = (f * 42 + 14) / h, (f * 42 + 32) / h
        for face, P0, P1, Q0, Q1 in (("L", A, B, A2, B2), ("R", B, C, B2, C2)):
            n = 5
            for i in range(n):
                ua, ub = (i + 0.25) / n, (i + 0.7) / n
                def at(u, t):
                    bx_ = P0[0] + (P1[0] - P0[0]) * u
                    by_ = P0[1] + (P1[1] - P0[1]) * u
                    tx = Q0[0] + (Q1[0] - Q0[0]) * u
                    ty = Q0[1] + (Q1[1] - Q0[1]) * u
                    return (bx_ + (tx - bx_) * t, by_ + (ty - by_) * t)
                on = rnd.random() < 0.3
                col = E.LIT if on else E.DARKWIN
                ctx.poly([at(ua, t0), at(ub, t0), at(ub, t1), at(ua, t1)], E.shade(col, 1.0 if face == "L" else 0.82), None)


def risen(ctx, c0, r0, c1, r1, h, sunk, wall, seed):
    """a building pushing up out of the ground: drawn from below ground, then the broken ground in front"""
    E.box(ctx, c0, r0, c1, r1, -sunk, h + sunk, E.shade(wall, 0.8), E.shade(wall, 0.95), E.shade(wall, 0.72))
    E.noir_windows(ctx, c0, r0, c1, r1, -sunk, h + sunk, seed, lit_frac=0.2)
    rnd = random.Random(seed)
    # torn ground lip along the two front faces, covering the sunk part
    for face, n in (("L", 9), ("R", 9)):
        pts_top = []
        for i in range(n + 1):
            u = i / n
            pts_top.append(E.face_pt(face, c0, r0, c1, r1, u, rnd.uniform(-6, 26)))
        lip = []
        for i in range(n + 1):
            u = i / n
            if face == "L":
                lip.append(E.iso(c0 + (c1 - c0) * u, r1 + 0.35 + rnd.uniform(0, 0.25), 0))
            else:
                lip.append(E.iso(c1 + 0.35 + rnd.uniform(0, 0.25), r1 - (r1 - r0) * u, 0))
        ctx.poly(pts_top + lip[::-1], (72, 70, 72), (18, 18, 20))
        for i in range(0, n + 1, 2):
            ctx.line([pts_top[i], lip[i]], (22, 22, 24), 0.8)
    # cracks running out across the ground
    for _ in range(7):
        c = rnd.uniform(c0, c1 + 1.5)
        r = r1 + rnd.uniform(0.3, 0.6)
        pts = [E.iso(c, r)]
        for _ in range(5):
            c += rnd.uniform(-0.3, 0.6)
            r += rnd.uniform(0.1, 0.5)
            pts.append(E.iso(c, r))
        ctx.line(pts, (14, 14, 16), 1.4)


def forming(ctx, c0, r0, c1, r1, h_solid, h_wire, wall, seed):
    """lower floors real, upper floors still being imagined: glowing wire edges"""
    E.box(ctx, c0, r0, c1, r1, 0, h_solid, E.shade(wall, 0.8), E.shade(wall, 0.95), E.shade(wall, 0.72))
    E.noir_windows(ctx, c0, r0, c1, r1, 0, h_solid, seed, lit_frac=0.25)
    top = h_solid + h_wire
    corners = [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]
    wire = (WIRE[0], WIRE[1], WIRE[2], 150)
    for z in range(int(h_solid), int(top) + 1, 42):
        fade = 1 - (z - h_solid) / max(1, h_wire)
        col = (WIRE[0], WIRE[1], WIRE[2], int(60 + 120 * fade))
        pts = [E.iso(c, r, z) for c, r in corners] + [E.iso(c0, r0, z)]
        ctx.line(pts, col, 1.2)
    for c, r in corners:
        ctx.line([E.iso(c, r, h_solid), E.iso(c, r, top)], wire, 1.4)
    x, y = E.iso((c0 + c1) / 2, (r0 + r1) / 2, h_solid + h_wire / 2)
    E.glow(ctx, x, y, (c1 - c0) * 60, h_wire * 0.6, WIRE, 40, 4)
    # sparks where the wires meet
    rnd = random.Random(seed)
    for _ in range(14):
        c, r = rnd.choice(corners)
        z = rnd.uniform(h_solid, top)
        x, y = E.iso(c, r, z)
        ctx.ell(x, y, 2.2, 2.2, (230, 245, 255))


def broken_road(ctx, c0, r, length, rise, along_c=True):
    """a stretch of street that lifts off the ground and stops in mid-air"""
    n = 10
    for i in range(n):
        u0, u1 = i / n, (i + 1) / n
        z0, z1 = rise * u0 ** 1.6, rise * u1 ** 1.6
        a0, a1 = c0 + length * u0, c0 + length * u1
        if along_c:
            top = [E.iso(a0, r, z0), E.iso(a1, r, z1), E.iso(a1, r + 2, z1), E.iso(a0, r + 2, z0)]
            side = [E.iso(a0, r + 2, z0), E.iso(a1, r + 2, z1), E.iso(a1, r + 2, z1 - 14), E.iso(a0, r + 2, max(0, z0 - 14))]
        else:
            top = [E.iso(r, a0, z0), E.iso(r + 2, a0, z0), E.iso(r + 2, a1, z1), E.iso(r, a1, z1)]
            side = [E.iso(r + 2, a0, z0), E.iso(r + 2, a1, z1), E.iso(r + 2, a1, z1 - 14), E.iso(r + 2, a0, max(0, z0 - 14))]
        ctx.poly(side, (34, 34, 38))
        ctx.poly(top, (58, 60, 66))
        if i % 2 == 0:
            m0 = [(top[0][0] + top[3][0]) / 2, (top[0][1] + top[3][1]) / 2]
            m1 = [(top[1][0] + top[2][0]) / 2, (top[1][1] + top[2][1]) / 2]
            ctx.line([m0, m1], (150, 130, 70), 1.0)
    # the jagged end and falling bits
    end = top[1:3]
    ctx.line(end, (90, 90, 96), 2.0)
    for k in range(5):
        x = end[0][0] + (end[1][0] - end[0][0]) * (k + 0.5) / 5
        y = end[0][1] + (end[1][1] - end[0][1]) * (k + 0.5) / 5
        ctx.poly([(x - 3, y + 8 + k * 9), (x + 3, y + 10 + k * 9), (x + 1, y + 15 + k * 9)], (60, 60, 64), None)
    # a street lamp still standing at the very edge
    lx, ly = top[1][0] - 6, top[1][1] + 4
    ctx.line([(lx, ly), (lx, ly - 46)], (20, 20, 24), 1.6)
    E.glow(ctx, lx + 6, ly - 48, 22, 18, E.LAMP, 70)
    ctx.ell(lx + 6, ly - 48, 3, 2.2, (255, 230, 170))


def rubble(ctx, c, r, seed):
    rnd = random.Random(seed)
    for _ in range(9):
        a, b = c + rnd.uniform(-0.6, 0.6), r + rnd.uniform(-0.6, 0.6)
        s = rnd.uniform(0.12, 0.3)
        E.box(ctx, a, b, a + s, b + s * rnd.uniform(0.6, 1.4), 0, rnd.uniform(4, 14), rnd.choice([(70, 66, 64), (88, 60, 50), (60, 60, 64)]))


def crack_field(ctx, pts):
    ctx.line(pts, (14, 14, 16), 1.2)


def b_shifting(town, bx, by):
    R = town.rnd
    town.fill(bx, by, E.CONCRETE)
    walls = [(88, 54, 46), (76, 70, 64), (66, 62, 70), (96, 84, 70)]
    slots = [(0.8, 0.8), (7.4, 0.8), (0.8, 7.6)]
    R.shuffle(slots)
    # 1 a building rising out of the ground
    c0, r0 = bx + slots[0][0], by + slots[0][1]
    h = 42 * R.randint(4, 7)
    town.add_box_obj(c0, r0, c0 + 4, r0 + 3.6, h + 40, risen, c0, r0, c0 + 4, r0 + 3.6, h, 90, R.choice(walls), int(R.random() * 1e6))
    # 2 a tilted building (leans as if mid-move)
    c0, r0 = bx + slots[1][0], by + slots[1][1]
    h = 42 * R.randint(5, 8)
    lean = R.choice((-1, 1)) * R.uniform(40, 90)
    town.add_box_obj(c0, r0, c0 + 3.8, r0 + 3.8, h + 30, sheared_box, c0, r0, c0 + 3.8, r0 + 3.8, h, R.choice(walls), lean, R.uniform(-10, 10), int(R.random() * 1e6),
                     key=c0 + r0 + 3.8)
    # widen its bbox for the lean
    k, n, bb, fn, args = town.objs[-1]
    town.objs[-1] = (k, n, (bb[0] - 100, bb[1], bb[2] + 100, bb[3]), fn, args)
    # 3 a building whose top is still forming
    c0, r0 = bx + slots[2][0], by + slots[2][1]
    hs = 42 * R.randint(3, 5)
    hw = 42 * R.randint(4, 7)
    town.add_box_obj(c0, r0, c0 + 4, r0 + 4, hs + hw + 40, forming, c0, r0, c0 + 4, r0 + 4, hs, hw, R.choice(walls), int(R.random() * 1e6))
    # 4 a street that lifts off and ends in the air
    bc, br = bx + 6.5, by + 11.0
    rise = R.uniform(140, 240)
    x0 = E.iso(bc, br + 2)[0] - 20
    x1 = E.iso(bc + 7, br)[0] + 20
    town.add(bc + br + 6, (x0, E.iso(bc + 7, br, rise)[1] - 80, x1, E.iso(bc + 7, br + 2)[1] + 70), broken_road, bc, br, 7.0, rise, True)
    # 5 rubble and cracks
    for _ in range(5):
        c, r = bx + R.uniform(1, 13), by + R.uniform(1, 13)
        x, y = E.iso(c, r)
        town.add(c + r - 0.2, (x - 70, y - 40, x + 70, y + 40), rubble, c, r, int(R.random() * 1e6))
    for _ in range(10):
        c, r = bx + R.uniform(0, 14), by + R.uniform(0, 14)
        pts = [E.iso(c, r)]
        for _ in range(6):
            c += R.uniform(-0.5, 0.5)
            r += R.uniform(-0.5, 0.5)
            pts.append(E.iso(c, r))
        town.add(-1e8, (min(p[0] for p in pts) - 4, min(p[1] for p in pts) - 4, max(p[0] for p in pts) + 4, max(p[1] for p in pts) + 4), crack_field, pts)
    # 6 people standing very still, looking up
    for _ in range(14):
        c, r = bx + R.uniform(5.5, 13.5), by + R.uniform(5.5, 10.5)
        town.add_person(c, r, pose="stand", extra=None)
    for _ in range(4):
        town.add_lamp(bx + R.uniform(5, 13), by + R.uniform(5, 10))


# ---------------------------------------------------------------- the canal

def canal_wall(ctx, a, b, depth):
    ctx.poly([a, b, (b[0], b[1] + depth), (a[0], a[1] + depth)], STONE, (30, 28, 28))
    ctx.line([(a[0], a[1] + depth * 0.5), (b[0], b[1] + depth * 0.5)], E.shade(STONE, 0.75), 0.6)
    ctx.line([a, b], E.shade(STONE, 1.4), 1.6)


def railing(ctx, a, b):
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 12))
    for i in range(n + 1):
        x = a[0] + (b[0] - a[0]) * i / n
        y = a[1] + (b[1] - a[1]) * i / n
        ctx.line([(x, y), (x, y - 12)], (20, 20, 24), 1.2)
    ctx.line([(a[0], a[1] - 12), (b[0], b[1] - 12)], (24, 24, 28), 1.6)
    ctx.line([(a[0], a[1] - 6), (b[0], b[1] - 6)], (24, 24, 28), 0.8)


def shimmer(ctx, x, y, seed, col=(255, 206, 120)):
    rnd = random.Random(seed)
    for i in range(9):
        dx = rnd.uniform(-10, 10)
        yy = y + 6 + i * 7
        w = rnd.uniform(4, 12) * (1 - i / 11)
        ctx.line([(x + dx - w, yy), (x + dx + w, yy)], (col[0], col[1], col[2], int(120 * (1 - i / 10))), 1.4)


def barge(ctx, c, r, along, length, col, seed):
    if along == "c":
        c0, c1, r0, r1 = c, c + length, r + 0.22, r + 0.78
    else:
        c0, c1, r0, r1 = c + 0.22, c + 0.78, r, r + length
    E.box(ctx, c0, r0, c1, r1, -4, 12, E.shade(col, 0.6), E.shade(col, 0.9), E.shade(col, 0.7))
    rnd = random.Random(seed)
    if along == "c":
        a, b = c0 + length * 0.6, c1 - 0.1
        E.box(ctx, a, r0 + 0.08, b, r1 - 0.08, 8, 16, (60, 50, 44), (80, 64, 50), (60, 48, 40))
        ctx.poly(face_poly("L", a, r0 + 0.08, b, r1 - 0.08, 0.2, 0.45, 13, 20), (255, 200, 120))
        for i in range(3):
            x, y = E.iso(c0 + 0.3 + i * 0.5, (r0 + r1) / 2, 8)
            ctx.ell(x, y - 3, 8, 4, rnd.choice([(70, 60, 50), (60, 64, 70), (80, 70, 50)]), (20, 20, 20))
    else:
        a, b = r0 + length * 0.6, r1 - 0.1
        E.box(ctx, c0 + 0.08, a, c1 - 0.08, b, 8, 16, (60, 50, 44), (80, 64, 50), (60, 48, 40))
        ctx.poly(face_poly("R", c0 + 0.08, a, c1 - 0.08, b, 0.3, 0.55, 13, 20), (255, 200, 120))
    x, y = E.iso((c0 + c1) / 2, (r0 + r1) / 2)
    ctx.line([(x - 40, y + 10), (x + 40, y + 10)], (60, 80, 110, 90), 1.0)


def water_fog(ctx, x, y, rx, ry):
    soft(ctx, x, y, rx, ry, FOG, 4, 6)


def b_canalside(town, bx, by):
    R = town.rnd
    RIVER, PLAZA = E.RIVER, E.PLAZA
    for c in range(bx, bx + 14):
        for r in range(by, by + 14):
            if town.gt(c, r) == E.GRASS:
                town.st(c, r, PLAZA)
    land = (PLAZA, E.WALK, E.ROAD, E.CONCRETE, E.GRASS, E.QUAY)
    for c in range(bx - 4, bx + 18):
        for r in range(by - 4, by + 18):
            if town.gt(c, r) != RIVER:
                continue
            # far walls of the canal: visible faces drop into the water
            if town.gt(c, r - 1) in land:
                a, b = E.iso(c, r), E.iso(c + 1, r)
                town.add(c + r - 0.6, (a[0] - 4, a[1] - 4, b[0] + 4, b[1] + 40), canal_wall, a, b, 34)
            if town.gt(c - 1, r) in land:
                a, b = E.iso(c, r), E.iso(c, r + 1)
                town.add(c + r - 0.6, (b[0] - 4, a[1] - 4, a[0] + 4, b[1] + 40), canal_wall, a, b, 34)
            # near edge: railing on the bank
            if town.gt(c, r + 1) in land and h01(c, r) < 0.9:
                a, b = E.iso(c, r + 1), E.iso(c + 1, r + 1)
                town.add(c + r + 1.05, (a[0] - 4, a[1] - 20, b[0] + 4, b[1] + 4), railing, a, b)
            if town.gt(c + 1, r) in land and h01(c, r, 2) < 0.9:
                a, b = E.iso(c + 1, r), E.iso(c + 1, r + 1)
                town.add(c + r + 1.05, (b[0] - 4, a[1] - 20, a[0] + 4, b[1] + 4), railing, a, b)
    # bridges: iron railings along both sides
    for c in range(bx - 4, bx + 18):
        for r in range(by - 4, by + 18):
            if town.gt(c, r) != E.BRIDGE:
                continue
            if town.gt(c, r - 1) == RIVER or town.gt(c, r + 1) == RIVER:
                for cc in (c, c + 1):
                    a, b = E.iso(cc, r), E.iso(cc, r + 1)
                    town.add(c + r + 0.9, (b[0] - 4, a[1] - 20, a[0] + 4, b[1] + 4), railing, a, b)
            elif town.gt(c - 1, r) == RIVER or town.gt(c + 1, r) == RIVER:
                for rr in (r, r + 1):
                    a, b = E.iso(c, rr), E.iso(c + 1, rr)
                    town.add(c + r + 0.9, (a[0] - 4, a[1] - 20, b[0] + 4, b[1] + 4), railing, a, b)
    # lamps on the banks with light shimmering in the water
    water = [(c, r) for c in range(bx, bx + 14) for r in range(by, by + 14) if town.gt(c, r) == RIVER]
    for k in range(0, len(water), 5):
        c, r = water[k]
        if town.gt(c, r - 1) in land:
            town.add_lamp(c + 0.5, r - 0.4)
            x, y = E.iso(c + 0.5, r + 0.2)
            town.add(c + r - 0.4, (x - 20, y - 4, x + 20, y + 80), shimmer, x, y, c * 31 + r)
    # moored barges and rowboats
    for _ in range(3):
        if not water:
            break
        c, r = R.choice(water)
        along = "c" if town.gt(c + 1, r) == RIVER and town.gt(c + 2, r) == RIVER else "r"
        ln = R.uniform(1.6, 2.6)
        x0, y0 = E.iso(c, r + 1)
        town.add(c + r + 0.5, (x0 - 140, y0 - 140, x0 + 260, y0 + 80), barge, c, r, along, ln, R.choice([(60, 40, 34), (40, 44, 50), (50, 50, 40)]), int(R.random() * 1e6))
    for k in range(0, len(water), 9):
        c, r = water[k]
        x, y = E.iso(c + 0.5, r + 0.5)
        town.add(c + r, (x - 130, y - 40, x + 130, y + 40), water_fog, x, y, 120, 18)
    town.crowd(bx, by, 14, 14, 26)


# ---------------------------------------------------------------- the edge of the world

def sea_wall(ctx, a, b, depth):
    ctx.poly([a, b, (b[0], b[1] + depth), (a[0], a[1] + depth)], (58, 56, 58), (20, 20, 24))
    for k in (0.33, 0.66):
        ctx.line([(a[0], a[1] + depth * k), (b[0], b[1] + depth * k)], (40, 40, 44), 0.7)
    ctx.line([(a[0], a[1] + depth), (b[0], b[1] + depth)], (90, 110, 140, 90), 1.4)   # foam line
    ctx.line([a, b], (110, 106, 100), 2.0)


def lone_sign(ctx, x, y, name, sub):
    # stilts into the water and their reflections
    w, top, bot = 640, y - 470, y - 250
    for px in (x - w * 0.36, x - w * 0.12, x + w * 0.12, x + w * 0.36):
        ctx.line([(px, y), (px, bot)], (36, 32, 30), 6)
        ctx.line([(px, y), (px, y + 70)], (36, 32, 30, 90), 6)
    ctx.line([(x - w * 0.36, y - 120), (x + w * 0.36, y - 160)], (36, 32, 30), 3)
    ctx.line([(x - w * 0.36, y - 160), (x + w * 0.36, y - 120)], (36, 32, 30), 3)
    soft(ctx, x, (top + bot) / 2, w * 0.75, 200, (255, 200, 130), 6, 7)
    ctx.poly([(x - w / 2 - 12, top - 12), (x + w / 2 + 12, top - 12), (x + w / 2 + 12, bot + 12), (x - w / 2 - 12, bot + 12)], (40, 36, 34))
    # a sunny painted scene: sky, sun, sea, sand - the only daylight in the city
    sky = [(x - w / 2, top), (x + w / 2, top), (x + w / 2, top + 120), (x - w / 2, top + 120)]
    ctx.poly(sky, (120, 200, 240), None)
    ctx.pie(x + w * 0.28, top + 120, 60, 60, 180, 360, (255, 210, 70), None)
    ctx.poly([(x - w / 2, top + 120), (x + w / 2, top + 120), (x + w / 2, top + 168), (x - w / 2, top + 168)], (40, 130, 190), None)
    ctx.poly([(x - w / 2, top + 168), (x + w / 2, top + 168), (x + w / 2, bot), (x - w / 2, bot)], (238, 214, 150), None)
    for k in range(4):
        ctx.line([(x - w * 0.4 + k * 60, top + 140), (x - w * 0.4 + k * 60 + 22, top + 136)], (230, 245, 255), 1.6)
    plain_text(ctx, x - 90, top + 58, name, (196, 64, 30), 58)
    plain_text(ctx, x, bot - 26, sub, (90, 60, 30), 26)
    # lamps along the top of the board
    for k in range(7):
        lx = x - w / 2 + 40 + k * (w - 80) / 6
        ctx.line([(lx, top - 12), (lx, top - 34)], (30, 30, 30), 1.2)
        ctx.ell(lx, top - 36, 5, 4, (255, 240, 200))
    # reflection in the black water
    for i in range(16):
        yy = y + 20 + i * 14
        ww = (w * 0.45) * (1 - i / 18) * (0.6 + 0.4 * h01(i, x))
        ctx.line([(x - ww, yy), (x + ww, yy)], (255, 200, 120, int(120 * (1 - i / 16))), 2.4)


def soft(ctx, x, y, rx, ry, col, alpha_each=5, rings=7):
    """very soft glow: many faint rings so no hard edges show"""
    for i in range(rings, 0, -1):
        f = i / rings
        ctx.ell(x, y, rx * f, ry * f, (col[0], col[1], col[2], alpha_each))


def plain_text(ctx, x, y, text, col, size):
    k = ctx.k
    f = E.font(size * k)
    tw = ctx.d.textlength(text, font=f)
    ctx.d.text(((x - ctx.ox) * k - tw / 2, (y - ctx.oy) * k - size * k * 0.6), text, font=f, fill=col)


def dark_boat(ctx, x, y, kind, f, seed):
    rnd = random.Random(seed)
    if kind == "ferry":
        ctx.poly([(x - 80, y - 12), (x + 80, y - 12), (x + 64, y + 10), (x - 70, y + 10)], (36, 36, 40))
        ctx.poly([(x - 66, y - 12), (x + 58, y - 12), (x + 52, y - 34), (x - 58, y - 34)], (48, 46, 50))
        for i in range(11):
            wx = x - 52 + i * 10
            ctx.poly([(wx, y - 29), (wx + 6, y - 29), (wx + 6, y - 20), (wx, y - 20)], (255, 206, 120) if rnd.random() < 0.6 else (30, 34, 44), None)
        ctx.poly([(x - 10, y - 34), (x + 8, y - 34), (x + 6, y - 54), (x - 8, y - 54)], (30, 30, 34))
        E.glow(ctx, x + 70 * f, y - 20, 18, 12, (255, 240, 200), 70)
        for i in range(10):
            ctx.line([(x - 40 + i * 9, y + 16 + i % 3 * 6), (x - 34 + i * 9, y + 16 + i % 3 * 6)], (255, 206, 120, 60), 1.6)
    else:
        ctx.poly([(x - 30, y - 6), (x + 30, y - 6), (x + 22, y + 6), (x - 24, y + 6)], (34, 34, 38))
        ctx.poly([(x - 8, y - 6), (x + 12, y - 6), (x + 10, y - 18), (x - 6, y - 18)], (44, 44, 48))
        ctx.ell(x + 2, y - 13, 3, 2, (255, 210, 130))
        ctx.line([(x + 2, y - 18), (x + 2, y - 40)], (30, 30, 30), 1.0)
        ctx.ell(x + 2, y - 41, 2, 2, (255, 70, 60))
    ctx.line([(x - 30 * f, y + 4), (x - 90 * f, y + 12)], (70, 90, 120, 90), 1.2)


def edge_of_the_world(town):
    R = town.rnd
    QUAY, SEA, SHALLOW = E.QUAY, E.SEA, E.SHALLOW
    water = (SEA, SHALLOW)
    lamp_n = 0
    for c in range(E.N):
        for r in range(E.N):
            if town.gt(c, r) != QUAY:
                continue
            # the wall face toward the viewer drops into the water
            if town.gt(c, r + 1) in water:
                a, b = E.iso(c, r + 1), E.iso(c + 1, r + 1)
                town.add(c + r + 1.4, (a[0] - 4, a[1] - 4, b[0] + 4, b[1] + 70), sea_wall, a, b, 60)
            if town.gt(c + 1, r) in water:
                a, b = E.iso(c + 1, r), E.iso(c + 1, r + 1)
                town.add(c + r + 1.4, (b[0] - 4, a[1] - 4, a[0] + 4, b[1] + 70), sea_wall, a, b, 60)
            # the far side's top edge (wall facing away) gets a railing
            if town.gt(c, r - 1) in water:
                a, b = E.iso(c, r), E.iso(c + 1, r)
                town.add(c + r + 0.2, (a[0] - 4, a[1] - 20, b[0] + 4, b[1] + 4), railing, a, b)
            if town.gt(c - 1, r) in water:
                a, b = E.iso(c, r), E.iso(c, r + 1)
                town.add(c + r + 0.2, (b[0] - 4, a[1] - 20, a[0] + 4, b[1] + 4), railing, a, b)
            near_water = any(town.gt(c + dc, r + dr) in water for dc, dr in ((1, 0), (0, 1), (-1, 0), (0, -1)))
            if near_water:
                if h01(c, r, 7) < 0.045:
                    town.add_lamp(c + 0.5, r + 0.5)
                    lamp_n += 1
                elif h01(c, r, 9) < 0.02:
                    # someone at the rail, looking out at nothing
                    town.add_person(c + 0.5, r + 0.5, pose="stand", extra=None)
    # the one lit sign out in the dark water, off the south-east shore
    sc, sr = E.N + 8, int(E.N * 0.56)
    x, y = E.iso(sc, sr)
    town.add(sc + sr + 5, (x - 420, y - 520, x + 420, y + 260), lone_sign, x, y, "SUNNY COVE", "ALWAYS DAYTIME  ->  NEXT EXIT")
    # a few dark boats and a ferry with lit windows
    n = 0
    tries = 0
    while n < 26 and tries < 4000:
        tries += 1
        c, r = R.uniform(-E.OFF + 4, E.N + E.OFF - 4), R.uniform(-E.OFF + 4, E.N + E.OFF - 4)
        x, y = E.iso(c, r)
        if not (200 < x < E.W - 200 and E.TOP + 200 < y < E.H - 60):
            continue
        if any(town.gt(int(c) + dc, int(r) + dr) not in water for dc in (-4, 0, 4) for dr in (-4, 0, 4)):
            continue
        if abs(x - E.iso(sc, sr)[0]) < 500 and abs(y - E.iso(sc, sr)[1]) < 500:
            continue
        kind = "ferry" if n % 6 == 0 else "boat"
        town.add(c + r, (x - 120, y - 70, x + 120, y + 40), dark_boat, x, y, kind, R.choice((-1, 1)), int(R.random() * 1e6))
        n += 1


# ---------------------------------------------------------------- searchlights

def beam(ctx, x, y, ang, length, spread):
    ex, ey = x + math.cos(ang) * length, y + math.sin(ang) * length
    nx, ny = -math.sin(ang), math.cos(ang)
    for k, a in ((1.0, 10), (0.55, 12), (0.25, 16)):
        w = spread * k
        ctx.poly([(x - nx * 4, y - ny * 4), (x + nx * 4, y + ny * 4), (ex + nx * w, ey + ny * w), (ex - nx * w, ey - ny * w)],
                 (220, 230, 255, a), None)
    E.glow(ctx, x, y, 14, 10, (240, 245, 255), 120)
    ctx.ell(x, y, 3, 3, (255, 255, 255))


def searchlights(town):
    R = town.rnd
    spots = []
    cb = (E.N // E.P) // 2
    cbx = cb * E.P + 4
    spots.append((cbx + 7, cbx + 7, 935))       # from the clock tower's belfry
    towers = [(bx, by) for bx, by, kind in town.blocks if kind == "deco_towers"]
    R.shuffle(towers)
    for bx, by in towers[:6]:
        spots.append((bx + R.uniform(3, 10), by + R.uniform(3, 10), R.uniform(420, 620)))
    for c, r, z in spots:
        x, y = E.iso(c, r, z)
        ang = -math.pi / 2 + R.uniform(-0.75, 0.75)
        length = R.uniform(1400, 2400)
        ex, ey = x + math.cos(ang) * length, y + math.sin(ang) * length
        spread = R.uniform(70, 130)
        x0, x1 = min(x, ex) - spread - 20, max(x, ex) + spread + 20
        y0, y1 = max(0, min(y, ey) - spread - 20), max(y, ey) + 20
        town.add(1e8, (x0, y0, x1, y1), beam, x, y, ang, length, spread)


# ---------------------------------------------------------------- rain and fog over every chunk

def rain_and_fog(ctx, cx, cy, cw, ch):
    rnd = random.Random(int(cx) * 7919 + int(cy) * 104729 + 17)
    n = int(cw * ch / 9000)
    for _ in range(n):
        x = cx + rnd.random() * cw
        y = cy + rnd.random() * ch
        ln = rnd.uniform(14, 30)
        ctx.line([(x, y), (x - ln * 0.28, y + ln)], (190, 200, 220, rnd.randint(22, 46)), 0.6)
    for _ in range(2):
        if rnd.random() < 0.6:
            x = cx + rnd.random() * cw
            y = cy + rnd.random() * ch
            rx = rnd.uniform(260, 620)
            for i in range(6, 0, -1):
                f = i / 6
                ctx.ell(x, y, rx * f, rx * 0.3 * f, (FOG[0], FOG[1], FOG[2], 3))
