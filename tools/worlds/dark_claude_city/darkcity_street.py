"""Dark Claude City - STREET plug-in.
People, lamps, 1940s cars with headlight beams, taxis, a trolley line, an elevated railway with lit
trains, steam vents, newsstands, phone booths, hydrants, mailboxes, cops on the beat, couples under
umbrellas, dog walkers, newspaper readers; the plaza and park builders. All original designs.
"""
import math

E = None          # the engine module (set by register)

WIRE = (70, 70, 76)
STEEL = (46, 48, 54)
STEEL_LIT = (70, 72, 80)
TAXI = (176, 148, 60)
CAR_COLS = [(22, 22, 24), (62, 22, 26), (30, 40, 62), (72, 72, 76), (92, 82, 60), (26, 52, 42), (44, 36, 30), (110, 104, 96)]
STEAM = (220, 224, 232)


def register(engine):
    global E
    E = engine
    E.STREET_HOOKS.append(dress_streets)
    E.BUILDERS.update({"plaza": b_plaza, "park": b_park})


# ---------------------------------------------------------------- small helpers

def _roadlike(town, c, r):
    return town.gt(c, r) in (E.ROAD, E.BRIDGE)


def _bbox(pts, pad=6):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


# ---------------------------------------------------------------- 1940s cars

def car40(ctx, c, r, along, col, front, lights, taxi=False):
    """rounded 1940s sedan: long hood, fat fenders, rounded cabin; front = +1/-1 along the axis"""
    iso, box, shade, OUT = E.iso, E.box, E.shade, E.OUT
    L, Wd = 0.86, 0.44
    if along == "c":
        c0, c1, r0, r1 = c + (1 - L) / 2, c + (1 + L) / 2, r + (1 - Wd) / 2, r + (1 + Wd) / 2
    else:
        c0, c1, r0, r1 = c + (1 - Wd) / 2, c + (1 + Wd) / 2, r + (1 - L) / 2, r + (1 + L) / 2
    x, y = iso((c0 + c1) / 2, (r0 + r1) / 2)
    ctx.ell(x, y + 2, 34, 13, E.SHADOW)
    # body (low) with a slightly lighter belt line
    box(ctx, c0, r0, c1, r1, 3, 9, shade(col, 1.1), shade(col, 0.95), shade(col, 0.7))
    # cabin set back from the front (long hood)
    if along == "c":
        if front > 0:
            a0, a1 = c0 + 0.12, c1 - 0.34
        else:
            a0, a1 = c0 + 0.34, c1 - 0.12
        cab = (a0, r0 + 0.05, a1, r1 - 0.05)
    else:
        if front > 0:
            b0, b1 = r0 + 0.12, r1 - 0.34
        else:
            b0, b1 = r0 + 0.34, r1 - 0.12
        cab = (c0 + 0.05, b0, c1 - 0.05, b1)
    box(ctx, cab[0], cab[1], cab[2], cab[3], 12, 8, shade(col, 1.15), (70, 84, 100), (52, 62, 78))
    # rounded roof cap
    rx, ry = iso((cab[0] + cab[2]) / 2, (cab[1] + cab[3]) / 2, 20)
    ctx.ell(rx, ry, 12, 5, shade(col, 1.2), None)
    if taxi:
        box(ctx, (cab[0] + cab[2]) / 2 - 0.06, (cab[1] + cab[3]) / 2 - 0.05, (cab[0] + cab[2]) / 2 + 0.06, (cab[1] + cab[3]) / 2 + 0.05,
            20, 4, (250, 220, 120), (230, 190, 90), (190, 150, 70), None)
        E.glow(ctx, rx, ry - 4, 10, 6, (255, 220, 120), 50, 2)
    # fat fenders over the wheels on the visible long side
    face = "L" if along == "c" else "R"
    for u in (0.2, 0.8):
        wx, wy = E.face_pt(face, c0, r0, c1, r1, u, 3)
        ctx.ell(wx, wy, 4.4, 4.4, (16, 16, 18))
        ctx.pie(wx, wy - 1, 6.2, 5.6, 180, 360, shade(col, 0.85), OUT)
    # chrome line
    ctx.line([E.face_pt(face, c0, r0, c1, r1, 0.05, 8), E.face_pt(face, c0, r0, c1, r1, 0.95, 8)], (150, 150, 150), 0.6)
    # lights
    if along == "c":
        fx = c1 if front > 0 else c0
        bx_ = c0 if front > 0 else c1
        fpts = [iso(fx, r0 + 0.08, 8), iso(fx, r1 - 0.08, 8)]
        bpts = [iso(bx_, r0 + 0.08, 8), iso(bx_, r1 - 0.08, 8)]
    else:
        fy = r1 if front > 0 else r0
        by_ = r0 if front > 0 else r1
        fpts = [iso(c0 + 0.08, fy, 8), iso(c1 - 0.08, fy, 8)]
        bpts = [iso(c0 + 0.08, by_, 8), iso(c1 - 0.08, by_, 8)]
    if lights:
        for p in fpts:
            ctx.ell(p[0], p[1], 2.2, 1.8, (255, 246, 210))
            E.glow(ctx, p[0], p[1], 9, 7, (255, 236, 180), 70, 2)
        for p in bpts:
            ctx.ell(p[0], p[1], 1.8, 1.5, (255, 40, 40))
            E.glow(ctx, p[0], p[1], 7, 5, (255, 40, 40), 60, 2)
    else:
        for p in fpts:
            ctx.ell(p[0], p[1], 1.8, 1.5, (120, 120, 110))


def beam(ctx, c, r, along, front, length=2.8):
    """headlight cone on the wet road ahead of a car"""
    iso = E.iso
    m = 0.5
    for k, (ln, al) in enumerate(((length, 18), (length * 0.7, 20), (length * 0.42, 26))):
        if along == "c":
            fx = c + 0.93 if front > 0 else c + 0.07
            ex = fx + front * ln
            pts = [iso(fx, r + m - 0.17), iso(fx, r + m + 0.17), iso(ex, r + m + 0.62), iso(ex, r + m - 0.62)]
        else:
            fy = r + 0.93 if front > 0 else r + 0.07
            ey = fy + front * ln
            pts = [iso(c + m - 0.17, fy), iso(c + m + 0.17, fy), iso(c + m + 0.62, ey), iso(c + m - 0.62, ey)]
        ctx.poly(pts, (255, 232, 170, al), None)


def add_car40(town, c, r, along, front, moving=True, taxi=False):
    R = town.rnd
    col = TAXI if taxi else R.choice(CAR_COLS)
    if moving:
        if along == "c":
            ex = c + 0.5 + front * 3.4
            pts = [E.iso(c, r), E.iso(c + 1, r + 1), E.iso(ex, r - 0.4), E.iso(ex, r + 1.4)]
        else:
            ey = r + 0.5 + front * 3.4
            pts = [E.iso(c, r), E.iso(c + 1, r + 1), E.iso(c - 0.4, ey), E.iso(c + 1.4, ey)]
        town.add(c + r - 1.2, _bbox(pts, 30), beam, c, r, along, front)
    town.add_box_obj(c, r, c + 1, r + 1, 40, car40, c, r, along, col, front, moving, taxi)


# ---------------------------------------------------------------- the elevated railway

EL_Z = 72


def el_piece(ctx, c, r, along, column, rails_only=False):
    """one tile of elevated track along `along`, centred on the lane boundary line"""
    iso, box, shade = E.iso, E.box, E.shade
    if along == "c":
        c0, c1, r0, r1 = c, c + 1, r - 0.46, r + 0.46
    else:
        c0, c1, r0, r1 = c - 0.46, c + 0.46, r, r + 1
    if column:
        for (a, b) in ((c0 + 0.45, r0 + 0.02), (c0 + 0.45, r1 - 0.14)) if along == "c" else ((c0 + 0.02, r0 + 0.45), (c1 - 0.14, r0 + 0.45)):
            box(ctx, a, b, a + 0.12, b + 0.12, 0, EL_Z, STEEL, STEEL_LIT, shade(STEEL, 0.75))
        # cross brace
        if along == "c":
            ctx.line([iso(c0 + 0.5, r0 + 0.08, EL_Z - 6), iso(c0 + 0.5, r1 - 0.08, EL_Z - 30)], STEEL_LIT, 1.4)
            ctx.line([iso(c0 + 0.5, r1 - 0.08, EL_Z - 6), iso(c0 + 0.5, r0 + 0.08, EL_Z - 30)], STEEL_LIT, 1.4)
        else:
            ctx.line([iso(c0 + 0.08, r0 + 0.5, EL_Z - 6), iso(c1 - 0.08, r0 + 0.5, EL_Z - 30)], STEEL_LIT, 1.4)
            ctx.line([iso(c1 - 0.08, r0 + 0.5, EL_Z - 6), iso(c0 + 0.08, r0 + 0.5, EL_Z - 30)], STEEL_LIT, 1.4)
    # girder deck with lattice on the visible side
    box(ctx, c0, r0, c1, r1, EL_Z, 10, (40, 40, 44), STEEL_LIT, shade(STEEL, 0.7))
    face = "L" if along == "c" else "R"
    for k in range(4):
        u0, u1 = k / 4, (k + 1) / 4
        ctx.line([E.face_pt(face, c0, r0, c1, r1, u0, EL_Z + 1), E.face_pt(face, c0, r0, c1, r1, u1, EL_Z + 9)], (30, 30, 34), 0.8)
        ctx.line([E.face_pt(face, c0, r0, c1, r1, u0, EL_Z + 9), E.face_pt(face, c0, r0, c1, r1, u1, EL_Z + 1)], (30, 30, 34), 0.8)
    # ties + rails on top
    for k in range(5):
        u = (k + 0.5) / 5
        if along == "c":
            ctx.line([iso(c0 + u, r0 + 0.08, EL_Z + 10), iso(c0 + u, r1 - 0.08, EL_Z + 10)], (60, 46, 36), 1.6)
        else:
            ctx.line([iso(c0 + 0.08, r0 + u, EL_Z + 10), iso(c1 - 0.08, r0 + u, EL_Z + 10)], (60, 46, 36), 1.6)
    for off in (-0.2, 0.2):
        if along == "c":
            ctx.line([iso(c0, r + off, EL_Z + 11), iso(c1, r + off, EL_Z + 11)], (150, 150, 156), 0.9)
        else:
            ctx.line([iso(c + off, r0, EL_Z + 11), iso(c + off, r1, EL_Z + 11)], (150, 150, 156), 0.9)


def train_car(ctx, c0, r0, c1, r1, along, head, seed):
    """one lit train car sitting on the el deck"""
    box, shade = E.box, E.shade
    z = EL_Z + 11
    body = (64, 34, 30)
    box(ctx, c0, r0, c1, r1, z, 26, (52, 52, 56), shade(body, 1.0), shade(body, 0.75))
    face = "L" if along == "c" else "R"
    n = 7
    for i in range(n):
        ua, ub = (i + 0.18) / n, (i + 0.82) / n
        pts = [E.face_pt(face, c0, r0, c1, r1, ua, z + 9), E.face_pt(face, c0, r0, c1, r1, ub, z + 9),
               E.face_pt(face, c0, r0, c1, r1, ub, z + 20), E.face_pt(face, c0, r0, c1, r1, ua, z + 20)]
        ctx.poly(pts, (255, 214, 130), None)
    mx, my = E.face_pt(face, c0, r0, c1, r1, 0.5, z + 14)
    E.glow(ctx, mx, my + 10, 60, 24, (255, 210, 130), 40, 3)
    if head:
        px, py = E.face_pt(face, c0, r0, c1, r1, 1.0, z + 12)
        ctx.ell(px, py, 3, 2.6, (255, 250, 220))
        E.glow(ctx, px, py, 30, 16, (255, 240, 190), 70, 3)


def build_el(town, along, line, cars_on=True):
    """el above the road band whose lane boundary is at `line` (r for along c, c for along r)"""
    R = town.rnd
    run = []
    pieces = []
    for k in range(-4, E.N + 4):
        if along == "c":
            ok = _roadlike(town, k, line - 1) and _roadlike(town, k, line)
        else:
            ok = _roadlike(town, line - 1, k) and _roadlike(town, line, k)
        if ok:
            run.append(k)
        elif run:
            if len(run) >= 10:
                pieces.append(run)
            run = []
    if len(run) >= 10:
        pieces.append(run)
    for run in pieces:
        for k in run:
            col = (k % 2 == 0) or k in (run[0], run[-1])
            if along == "c":
                c, r = k, line
                pts = [E.iso(c, r - 0.5, EL_Z + 14), E.iso(c + 1, r + 0.5, 0), E.iso(c, r + 0.5, 0), E.iso(c + 1, r - 0.5, EL_Z + 14)]
            else:
                c, r = line, k
                pts = [E.iso(c - 0.5, r, EL_Z + 14), E.iso(c + 0.5, r + 1, 0), E.iso(c + 0.5, r, 0), E.iso(c - 0.5, r + 1, EL_Z + 14)]
            town.add(c + r + 0.5 + 0.3, _bbox(pts, 12), el_piece, c, r, along, col)
        # trains
        if cars_on and len(run) > 40:
            for _ in range(R.randint(1, 2)):
                start = R.randint(0, len(run) - 8)
                ncar = R.randint(3, 5)
                head_at_front = R.random() < 0.5
                for i in range(ncar):
                    a = run[start] + i * 1.35
                    b = a + 1.25
                    if along == "c":
                        box_ = (a, line - 0.34, b, line + 0.34)
                    else:
                        box_ = (line - 0.34, a, line + 0.34, b)
                    head = (i == ncar - 1) if head_at_front else False
                    town.add_box_obj(box_[0], box_[1], box_[2], box_[3], EL_Z + 50, train_car, *box_, along, head, R.random() * 1e9,
                                     key=(box_[0] + box_[2] + box_[1] + box_[3]) / 2 + 0.35)


# ---------------------------------------------------------------- trolley line

def wire_piece(ctx, c, r, along, pole):
    iso = E.iso
    z = 64
    if along == "c":
        for off in (-0.12, 0.12):
            ctx.line([iso(c, r + off, z), iso(c + 1, r + off, z)], WIRE, 0.7)
        if pole:
            for rr, s in ((r - 2.3, 1), (r + 2.3, -1)):
                ctx.line([iso(c + 0.5, rr), iso(c + 0.5, rr, z + 8)], (36, 36, 40), 1.6)
            ctx.line([iso(c + 0.5, r - 2.3, z + 4), iso(c + 0.5, r + 2.3, z + 4)], WIRE, 0.7)
    else:
        for off in (-0.12, 0.12):
            ctx.line([iso(c + off, r, z), iso(c + off, r + 1, z)], WIRE, 0.7)
        if pole:
            for cc in (c - 2.3, c + 2.3):
                ctx.line([iso(cc, r + 0.5), iso(cc, r + 0.5, z + 8)], (36, 36, 40), 1.6)
            ctx.line([iso(c - 2.3, r + 0.5, z + 4), iso(c + 2.3, r + 0.5, z + 4)], WIRE, 0.7)


def trolley(ctx, c0, r0, c1, r1, along, seed):
    box, shade = E.box, E.shade
    green, cream = (36, 70, 52), (190, 180, 150)
    box(ctx, c0, r0, c1, r1, 3, 12, shade(green, 1.0), shade(green, 0.95), shade(green, 0.72))
    box(ctx, c0, r0, c1, r1, 15, 16, (60, 60, 60), shade(cream, 0.9), shade(cream, 0.7))
    face = "L" if along == "c" else "R"
    for i in range(8):
        ua, ub = (i + 0.15) / 8, (i + 0.85) / 8
        ctx.poly([E.face_pt(face, c0, r0, c1, r1, ua, 18), E.face_pt(face, c0, r0, c1, r1, ub, 18),
                  E.face_pt(face, c0, r0, c1, r1, ub, 28), E.face_pt(face, c0, r0, c1, r1, ua, 28)], (255, 212, 130), None)
    mx, my = E.face_pt(face, c0, r0, c1, r1, 0.5, 20)
    E.glow(ctx, mx, my + 14, 70, 26, (255, 210, 130), 36, 3)
    # trolley pole up to the wire
    cx, cr = (c0 + c1) / 2, (r0 + r1) / 2
    ctx.line([E.iso(cx, cr, 31), E.iso(cx - (0.5 if along == "c" else 0), cr - (0.5 if along == "r" else 0), 64)], (30, 30, 30), 1.0)
    px, py = E.iso(cx - (0.5 if along == "c" else 0), cr - (0.5 if along == "r" else 0), 64)
    E.glow(ctx, px, py, 8, 8, (160, 200, 255), 90, 2)


def build_trolley(town, along, line):
    R = town.rnd
    ks = []
    for k in range(-2, E.N + 2):
        ok = (_roadlike(town, k, line - 1) and _roadlike(town, k, line)) if along == "c" else (_roadlike(town, line - 1, k) and _roadlike(town, line, k))
        if ok:
            ks.append(k)
    for k in ks:
        c, r = (k, line) if along == "c" else (line, k)
        pts = [E.iso(c - 2.5, r - 2.5, 80), E.iso(c + 3, r + 3)]
        town.add(c + r + 0.6, _bbox([E.iso(c, r - 2.4, 80), E.iso(c + 1, r + 2.4), E.iso(c - 2.4, r, 80), E.iso(c + 2.4, r + 1)], 10),
                 wire_piece, c, r, along, k % 4 == 0)
    for _ in range(3):
        if len(ks) < 20:
            break
        k = R.choice(ks[5:-5])
        if along == "c":
            b = (k, line - 0.42 - 0.5, k + 2.0, line - 0.5 + 0.42) if R.random() < 0.5 else (k, line + 0.5 - 0.42, k + 2.0, line + 0.5 + 0.42)
        else:
            b = (line - 0.92, k, line - 0.08, k + 2.0) if R.random() < 0.5 else (line + 0.08, k, line + 0.92, k + 2.0)
        town.add_box_obj(b[0], b[1], b[2], b[3], 80, trolley, *b, along, R.random())


# ---------------------------------------------------------------- street props

def hydrant(ctx, x, y):
    ctx.ell(x + 2, y, 5, 2, E.SHADOW)
    ctx.poly([(x - 2.4, y), (x + 2.4, y), (x + 2.0, y - 9), (x - 2.0, y - 9)], (130, 30, 28), E.OUT)
    ctx.pie(x, y - 9, 2.4, 2.2, 180, 360, (150, 36, 32), E.OUT)
    ctx.line([(x - 3.6, y - 6), (x + 3.6, y - 6)], (110, 26, 24), 1.4)


def mailbox(ctx, c, r):
    E.box(ctx, c, r, c + 0.18, r + 0.14, 0, 16, (40, 52, 80))
    x, y = E.iso(c + 0.09, r + 0.07, 16)
    ctx.pie(x, y + 3, 5.4, 3.6, 180, 360, (46, 60, 92), E.OUT)


def phone_booth(ctx, c, r):
    box, shade = E.box, E.shade
    col = (96, 40, 32)
    box(ctx, c, r, c + 0.3, r + 0.3, 0, 46, shade(col, 1.1), col, shade(col, 0.75))
    for face in ("L", "R"):
        ctx.poly([E.face_pt(face, c, r, c + 0.3, r + 0.3, 0.2, 12), E.face_pt(face, c, r, c + 0.3, r + 0.3, 0.8, 12),
                  E.face_pt(face, c, r, c + 0.3, r + 0.3, 0.8, 38), E.face_pt(face, c, r, c + 0.3, r + 0.3, 0.2, 38)],
                 (240, 214, 150) if face == "L" else (200, 176, 120), None)
    x, y = E.iso(c + 0.15, r + 0.15, 24)
    E.glow(ctx, x, y, 22, 22, (255, 220, 150), 50, 3)


def newsstand(ctx, c, r):
    box, shade = E.box, E.shade
    wood = (70, 52, 36)
    box(ctx, c, r, c + 0.9, r + 0.5, 0, 22, shade(wood, 1.1), wood, shade(wood, 0.75))
    # stacks of papers on the counter
    for i in range(5):
        x, y = E.face_pt("L", c, r, c + 0.9, r + 0.5, 0.1 + i * 0.18, 16)
        ctx.poly([(x, y), (x + 6, y + 3), (x + 6, y - 2), (x, y - 5)], (210, 206, 190), None)
    # awning
    ctx.poly([E.iso(c - 0.05, r - 0.05, 34), E.iso(c + 0.95, r - 0.05, 34), E.iso(c + 0.95, r + 0.75, 26), E.iso(c - 0.05, r + 0.75, 26)],
             (90, 30, 30), E.OUT)
    for i in range(0, 5, 2):
        u0, u1 = i / 5, (i + 1) / 5
        ctx.poly([E.iso(c - 0.05 + u0, r - 0.05, 34), E.iso(c - 0.05 + u1, r - 0.05, 34), E.iso(c - 0.05 + u1, r + 0.75, 26), E.iso(c - 0.05 + u0, r + 0.75, 26)],
                 (170, 160, 130), None)
    x, y = E.iso(c + 0.45, r + 0.5, 30)
    E.glow(ctx, x, y + 6, 28, 12, (255, 220, 150), 40, 2)


def trash_can(ctx, x, y):
    E.cyl(ctx, x, y, 3.6, 1.8, 10, (60, 62, 64), (80, 82, 84))


def steam(ctx, x, y, seed):
    rnd = E.random.Random(seed)
    ctx.ell(x, y, 9, 3.6, (20, 20, 22), (60, 60, 64))
    for i in range(10):
        t = i / 9
        px = x + rnd.uniform(-5, 5) + t * rnd.uniform(4, 14)
        py = y - 6 - t * 90
        rr = 7 + t * 20
        ctx.ell(px, py, rr, rr * 0.75, (STEAM[0], STEAM[1], STEAM[2], int(46 * (1 - t) + 8)))


def newspaper(ctx, x, y, f):
    """paper held open in front of a standing person (drawn after the person)"""
    px, py = x + 3.6 * f, y - 15
    ctx.poly([(px - 4, py - 4), (px + 4, py - 5), (px + 4, py + 4), (px - 4, py + 5)], (214, 208, 190), (90, 90, 90))
    ctx.line([(px - 3, py - 1), (px + 3, py - 2)], (110, 110, 110), 0.5)
    ctx.line([(px - 3, py + 1.5), (px + 3, py + 0.5)], (110, 110, 110), 0.5)


def add_hydrant(town, c, r):
    x, y = E.iso(c, r)
    town.add(c + r, (x - 6, y - 14, x + 6, y + 3), hydrant, x, y)


def add_cop(town, c, r):
    L = town.add_person(c, r, shirt=(28, 34, 58), pants=(24, 28, 46), hat="cap", hcol=(24, 28, 50), coat=True, extra=None, s=1.0)
    return L


# ---------------------------------------------------------------- the hook

def dress_streets(town):
    R = town.rnd
    N, P = E.N, E.P
    nb = N // P
    # elevated railway: two lines along c, one along r (lane boundary = band start + 2)
    el_lines_c = [int(nb * 0.33) * P + 2, int(nb * 0.67) * P + 2]
    el_lines_r = [int(nb * 0.5) * P + 2 + P]
    for ln in el_lines_c:
        build_el(town, "c", ln)
    for ln in el_lines_r:
        build_el(town, "r", ln)
    # trolley avenues (not under the el)
    tr_r = [int(nb * 0.2) * P + 2]
    tr_c = [int(nb * 0.5) * P + 2]
    for ln in tr_r:
        build_trolley(town, "r", ln)
    for ln in tr_c:
        if ln not in el_lines_c:
            build_trolley(town, "c", ln)
    el_set = set(el_lines_c)
    for c in range(N):
        for r in range(N):
            t = town.gt(c, r)
            if t in (E.ROAD, E.BRIDGE):
                rc, rr = c % P, r % P
                along = "c" if rr in (1, 2) and rc not in (0, 1, 2, 3) else "r" if rc in (1, 2) and rr not in (0, 1, 2, 3) else None
                if along:
                    lane = rr if along == "c" else rc
                    front = 1 if lane == 2 else -1
                    q = R.random()
                    if q < 0.075:
                        add_car40(town, c, r, along, front, moving=True, taxi=R.random() < 0.18)
                    elif q < 0.095:
                        add_car40(town, c, r, along, front, moving=False)
                if R.random() < 0.008 and t == E.ROAD:
                    x, y = E.iso(c + 0.5, r + 0.5)
                    town.add(c + r + 0.9, (x - 40, y - 140, x + 50, y + 6), steam, x, y, R.random() * 1e9)
            elif t == E.WALK:
                n = 1 if R.random() < 0.7 else 0
                n += 1 if R.random() < 0.28 else 0
                for _ in range(n):
                    town.add_person(c + R.random(), r + R.random())
                if (c + r) % 6 == 0 and R.random() < 0.6:
                    town.add_lamp(c + 0.5, r + 0.5)
                q = R.random()
                if q < 0.012:
                    add_hydrant(town, c + 0.3, r + 0.3)
                elif q < 0.02:
                    town.add_box_obj(c + 0.4, r + 0.4, c + 0.6, r + 0.6, 30, mailbox, c + 0.4, r + 0.4)
                elif q < 0.026:
                    town.add_box_obj(c + 0.3, r + 0.3, c + 0.6, r + 0.6, 60, phone_booth, c + 0.3, r + 0.3)
                    if R.random() < 0.4:
                        town.add_person(c + 0.75, r + 0.7, pose="stand")
                elif q < 0.03:
                    town.add_box_obj(c + 0.05, r + 0.25, c + 0.95, r + 0.75, 50, newsstand, c + 0.05, r + 0.25)
                    town.add_person(c + 0.5, r + 0.9, pose="stand", hat="cap", hcol=(60, 54, 44), extra=None)
                elif q < 0.04:
                    x, y = E.iso(c + 0.5, r + 0.5)
                    town.add(c + r + 1, (x - 6, y - 14, x + 6, y + 3), trash_can, x, y)
                elif q < 0.046:
                    add_cop(town, c + 0.5, r + 0.5)
                elif q < 0.054:     # couple under one umbrella
                    f = R.choice((-1, 1))
                    town.add_person(c + 0.4, r + 0.5, f=f, extra="umbrella", ecol=(20, 20, 24), pose="walk")
                    town.add_person(c + 0.55, r + 0.62, f=f, pose="walk", extra=None, hat=None, shirt=R.choice([(110, 30, 40), (60, 50, 70), (140, 120, 90)]))
                elif q < 0.06:      # dog walker
                    f = R.choice((-1, 1))
                    town.add_person(c + 0.4, r + 0.4, f=f, extra=None)
                    x, y = E.iso(c + 0.4 + 0.45 * f, r + 0.6)
                    town.add(c + r + 1.0, (x - 12, y - 16, x + 12, y + 4), E.dog, x, y, f, R.choice([(40, 30, 26), (120, 90, 50), (180, 170, 150)]), False)
                elif q < 0.065 and (c + r) % 6 == 0:   # reading the paper under the lamp
                    f = R.choice((-1, 1))
                    L = town.add_person(c + 0.62, r + 0.6, pose="stand", f=f, extra=None)
                    x, y = E.iso(c + 0.62, r + 0.6)
                    town.add(c + r + 1.25, (x - 12, y - 26, x + 12, y - 6), newspaper, x, y, f)


# ---------------------------------------------------------------- plaza

def statue(ctx, c, r):
    """original figure: a robed lamplighter holding a lantern high"""
    box, shade = E.box, E.shade
    stone = (92, 88, 84)
    box(ctx, c - 1.0, r - 1.0, c + 1.0, r + 1.0, 0, 14, shade(stone, 1.05))
    box(ctx, c - 0.7, r - 0.7, c + 0.7, r + 0.7, 14, 46, shade(stone, 1.0), shade(stone, 0.95), shade(stone, 0.75))
    x, y = E.iso(c, r, 60)
    bronze = (58, 74, 64)
    hi = (88, 110, 92)
    ctx.ell(x, y, 16, 6, shade(bronze, 0.8), E.OUT)
    ctx.poly([(x - 13, y), (x + 13, y), (x + 7, y - 52), (x - 7, y - 52)], bronze, E.OUT)
    ctx.poly([(x - 2, y - 2), (x + 11, y - 2), (x + 6, y - 50), (x + 1, y - 50)], hi, None)
    ctx.poly([(x - 8, y - 50), (x + 8, y - 50), (x + 6, y - 58), (x - 6, y - 58)], shade(bronze, 0.9), E.OUT)
    ctx.ell(x, y - 64, 6, 7, hi, E.OUT)
    ctx.pie(x, y - 64, 7.5, 8, 180, 360, shade(bronze, 0.8), E.OUT)   # hood
    # raised arm + lantern
    ctx.line([(x + 6, y - 54), (x + 16, y - 76), (x + 18, y - 92)], bronze, 4.0)
    ctx.poly([(x + 13, y - 92), (x + 23, y - 92), (x + 22, y - 104), (x + 14, y - 104)], (255, 214, 140), E.OUT)
    ctx.line([(x + 18, y - 104), (x + 18, y - 109)], bronze, 1.4)
    E.glow(ctx, x + 18, y - 98, 46, 40, (255, 210, 130), 80, 4)
    # the other arm holding the long lighting pole
    ctx.line([(x - 6, y - 50), (x - 15, y - 34)], bronze, 3.4)
    ctx.line([(x - 24, y + 4), (x - 10, y - 74)], (50, 60, 52), 1.6)


def pigeon(ctx, x, y):
    ctx.ell(x, y - 2, 2.6, 1.6, (96, 98, 108))
    ctx.ell(x + 2, y - 3.6, 1.2, 1.2, (80, 84, 96))


def b_plaza(town, bx, by):
    R = town.rnd
    town.fill(bx, by, E.PLAZA)
    cx, cy = bx + 7, by + 7
    x, y = E.iso(cx, cy)
    town.add(cx + cy, (x - 140, y - 160, x + 140, y + 60), statue, cx, cy)
    town.add_light(cx, cy, 3.2, E.LAMP, 60)
    for k in range(8):
        a = k * math.pi / 4
        town.add_lamp(cx + math.cos(a) * 5.4, cy + math.sin(a) * 5.4)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        bc, br = cx + math.cos(a) * 3.2, cy + math.sin(a) * 3.2
        along = "c" if abs(math.sin(a)) > abs(math.cos(a)) else "r"
        bxx, byy = E.iso(bc, br)
        town.add(bc + br + 0.3, (bxx - 40, byy - 30, bxx + 40, byy + 14), E.bench, bc, br, along)
        if R.random() < 0.6:
            town.add_person(bc + 0.3, br + 0.4, pose="sit")
    for (tc, tr) in ((bx + 1, by + 1), (bx + 13, by + 1), (bx + 1, by + 13), (bx + 13, by + 13)):
        town.add_tree(tc, tr, 1.5)
    for _ in range(50):
        c, r = bx + R.random() * 14, by + R.random() * 14
        if (c - cx) ** 2 + (r - cy) ** 2 < 2.2 ** 2:
            continue
        px, py = E.iso(c, r)
        town.add(c + r, (px - 4, py - 6, px + 5, py + 2), pigeon, px, py)
    # a newsstand and a flower cart
    town.add_box_obj(bx + 0.8, by + 10.5, bx + 1.7, by + 11.0, 50, newsstand, bx + 0.8, by + 10.5)
    town.crowd(bx, by, 14, 14, 170)


# ---------------------------------------------------------------- park

def fence_piece(ctx, c, r, along):
    iso = E.iso
    col = (22, 22, 26)
    if along == "c":
        a, b = iso(c, r), iso(c + 1, r)
    else:
        a, b = iso(c, r), iso(c, r + 1)
    for z in (6, 16):
        ctx.line([(a[0], a[1] - z), (b[0], b[1] - z)], col, 1.0)
    for k in range(5):
        t = k / 4
        px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        ctx.line([(px, py), (px, py - 20)], col, 0.9)
        ctx.ell(px, py - 21, 1.0, 1.4, col)


def bandstand(ctx, c, r):
    """octagonal bandstand: stone base, white posts, lit inside, pointed roof with a ring of bulbs"""
    x, y = E.iso(c, r)
    R = 1.25
    rx, ry = R * 1.414 * E.HW, R * 1.414 * E.HH
    E.cyl(ctx, x, y, rx, ry, 10, (80, 76, 72), (98, 92, 86))
    E.glow(ctx, x, y - 30, rx * 0.95, ry * 1.8, (255, 210, 140), 80, 4)
    posts = [(x + math.cos(k * math.pi / 4) * rx * 0.88, y - 10 + math.sin(k * math.pi / 4) * ry * 0.88, math.sin(k * math.pi / 4)) for k in range(8)]
    for px, py, sn in posts:
        if sn < 0:
            ctx.line([(px, py), (px, py - 50)], (200, 196, 186), 2.0)
    for px, py, sn in posts:
        if sn >= 0:
            ctx.line([(px, py), (px, py - 50)], (220, 216, 206), 2.2)
    # roof: eave ring + two visible cone faces
    ey = y - 60
    ctx.ell(x, ey, rx * 1.08, ry * 1.08, (54, 36, 32), E.OUT)
    ctx.poly([(x - rx * 1.08, ey), (x, ey + ry * 1.08), (x, ey - 70)], (86, 56, 46), E.OUT)
    ctx.poly([(x, ey + ry * 1.08), (x + rx * 1.08, ey), (x, ey - 70)], (64, 42, 36), E.OUT)
    ctx.line([(x, ey - 70), (x, ey - 84)], (180, 170, 140), 1.4)
    ctx.ell(x, ey - 86, 2.4, 2.4, (230, 200, 120))
    for k in range(12):
        a = k * math.pi / 6
        if math.sin(a) > -0.3:
            ctx.ell(x + math.cos(a) * rx * 1.06, ey + math.sin(a) * ry * 1.06, 2.2, 2.2, (255, 232, 160))


def b_park(town, bx, by):
    R = town.rnd
    town.fill(bx, by, E.GRASS)
    for c in range(bx, bx + 14):
        for r in range(by, by + 14):
            a, b = c - bx, r - by
            if abs(a - b) < 1 or abs(a + b - 13) < 1 or (a in (0, 13) or b in (0, 13)):
                town.st(c, r, E.PATH)
    # iron fence along all four sides (inside the path ring)
    for k in range(14):
        for (c, r, along) in ((bx + k, by, "c"), (bx + k, by + 14, "c"), (bx, by + k, "r"), (bx + 14, by + k, "r")):
            if (k in (6, 7)):
                continue            # gates
            pts = [E.iso(c, r, 24), E.iso(c + (1 if along == "c" else 0), r + (1 if along == "r" else 0), 0)]
            town.add(c + r + 0.5 + (0.3 if (r == by + 14 or c == bx + 14) else -0.3), _bbox(pts + [E.iso(c, r), E.iso(c + 1, r + 1, 24)], 6), fence_piece, c, r, along)
    cx, cy = bx + 7, by + 7
    x, y = E.iso(cx, cy)
    town.add(cx + cy + 0.02, (x - 110, y - 160, x + 110, y + 60), bandstand, cx, cy)
    for k in range(4):
        town.add_person(cx + 0.45 * math.cos(k * 1.57), cy + 0.45 * math.sin(k * 1.57), z=10, pose="stand", extra=None, hat=None,
                        shirt=(30, 30, 34), keyplus=-0.01)
    for _ in range(26):
        c, r = bx + 1 + R.random() * 12, by + 1 + R.random() * 12
        if town.gt(int(c), int(r)) == E.GRASS and (c - cx) ** 2 + (r - cy) ** 2 > 9:
            town.add_tree(c, r, 1.3 + R.random() * 0.5)
    for k in (1, 4, 9.5, 12):          # along both diagonal paths, clear of the bandstand
        town.add_lamp(bx + k + 0.5, by + k + 0.5)
        town.add_lamp(bx + k + 0.5, by + 13 - k + 0.5)
    for k in range(6):
        a = k * math.pi / 3
        bc, br = cx + math.cos(a) * 3.4, cy + math.sin(a) * 3.4
        bxx, byy = E.iso(bc, br)
        town.add(bc + br + 0.3, (bxx - 40, byy - 30, bxx + 40, byy + 14), E.bench, bc, br, "c")
        if R.random() < 0.7:
            town.add_person(bc + 0.3, br + 0.4, pose="sit")
    for _ in range(40):           # audience around the bandstand
        a = R.random() * 6.283
        d = 2.6 + R.random() * 1.6
        town.add_person(cx + math.cos(a) * d, cy + math.sin(a) * d, pose="stand", f=1 if math.cos(a) < 0 else -1)
    town.crowd(bx, by, 14, 14, 30, ok=(E.PATH,))
