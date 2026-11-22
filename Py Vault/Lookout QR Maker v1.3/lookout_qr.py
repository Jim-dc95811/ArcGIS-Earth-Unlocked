# Lookout QR Maker - makes a print-ready QR card for a router address.
# Pure-Python QR encoder (byte mode, versions 1-3, error-correction level M,
# single data block) + Pillow for the card. No external QR library, no internet.
# The GUI needs only tkinter (ships with Python) and Pillow.
#
# Why this exists: phones force https when you TYPE an address, so a crew that
# types 192.168.8.1:8080 lands on nothing. A QR encodes http:// explicitly, so a
# camera scan opens the Lookout map directly. Print the card, tape it to the box.

VERSION = "1.3"   # 1.3: card shows the full http:// address (the typeable form that works). 1.2: encode exactly what you type (no forced :8080); "Just the QR" bare-code option

# ---------- QR parameters (single data block only) ----------
# Each entry: (version, modules/side, EC codewords, DATA codewords,
#              alignment center or None, EC-level format bits).
# Format bits: M=0, L=1. These are all SINGLE-block configs (no interleaving),
# ordered by capacity. Level M (stronger correction) is used where it fits;
# longer URLs step down to level L to gain room while staying single-block.
CONFIGS = [
    (1, 21, 10, 16, None, 0),   # v1-M  ~14 chars
    (2, 25, 16, 28, 18,   0),   # v2-M  ~26
    (3, 29, 26, 44, 22,   0),   # v3-M  ~42
    (3, 29, 15, 55, 22,   1),   # v3-L  ~53
    (4, 33, 20, 80, 26,   1),   # v4-L  ~78
]
MAX_BYTES = 78  # version-4-L byte capacity

# ---------- GF(256) for Reed-Solomon ----------
_exp = [0]*512; _log = [0]*256
_x = 1
for _i in range(255):
    _exp[_i] = _x; _log[_x] = _i
    _x <<= 1
    if _x & 0x100: _x ^= 0x11d
for _i in range(255, 512): _exp[_i] = _exp[_i-255]
def _gmul(a, b):
    if a == 0 or b == 0: return 0
    return _exp[_log[a] + _log[b]]
def _gen_poly(n):
    g = [1]
    for i in range(n):
        g2 = [0]*(len(g)+1)
        for j in range(len(g)):
            g2[j]   ^= _gmul(g[j], _exp[i])
            g2[j+1] ^= g[j]
        g = g2
    return list(reversed(g))            # highest degree first, g[0]=1
def _rs_encode(data, n):
    gen = _gen_poly(n); msg = list(data) + [0]*n
    for i in range(len(data)):
        c = msg[i]
        if c:
            for j in range(len(gen)): msg[i+j] ^= _gmul(gen[j], c)
    return msg[len(data):]

def _getbit(v, i): return (v >> i) & 1

def pick_config(nbytes):
    bits = 4 + 8 + nbytes*8                 # mode + 8-bit count + data
    for cfg in CONFIGS:
        if bits <= cfg[3]*8:
            return cfg
    raise ValueError("Address too long for this encoder (max %d characters)." % MAX_BYTES)

def encode_matrix(text):
    """Return a list-of-lists of booleans (True = dark) for `text` (<= MAX_BYTES ascii)."""
    raw = text.encode("ascii")
    if len(raw) > MAX_BYTES:
        raise ValueError("Address too long for this encoder (max %d characters)." % MAX_BYTES)
    v, SIZE, ECC, DATACW, ALIGN, ECFMT = pick_config(len(raw))

    # data codewords
    bits = [0,1,0,0] + [int(b) for b in format(len(raw), "08b")]
    for ch in raw:
        bits += [int(b) for b in format(ch, "08b")]
    bits += [0]*min(4, DATACW*8 - len(bits))        # terminator
    while len(bits) % 8: bits.append(0)
    data = [int("".join(map(str, bits[i:i+8])), 2) for i in range(0, len(bits), 8)]
    pad = [0xEC, 0x11]; k = 0
    while len(data) < DATACW: data.append(pad[k % 2]); k += 1
    allcw = data + _rs_encode(data, ECC)

    mod = [[False]*SIZE for _ in range(SIZE)]
    fn  = [[False]*SIZE for _ in range(SIZE)]
    def setf(x, y, val):
        if 0 <= x < SIZE and 0 <= y < SIZE: mod[y][x] = bool(val); fn[y][x] = True
    def finder(cx, cy):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                setf(cx+dx, cy+dy, max(abs(dx), abs(dy)) not in (2, 4))
    def align(cx, cy):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                setf(cx+dx, cy+dy, max(abs(dx), abs(dy)) != 1)
    for i in range(SIZE):
        setf(6, i, i % 2 == 0); setf(i, 6, i % 2 == 0)      # timing
    finder(3, 3); finder(SIZE-4, 3); finder(3, SIZE-4)
    if ALIGN is not None: align(ALIGN, ALIGN)
    setf(8, SIZE-8, True)                                   # dark module

    def draw_format(mask):
        d = (ECFMT << 3) | mask                            # EC level (M=0, L=1) + mask
        rem = d
        for _ in range(10): rem = (rem << 1) ^ (((rem >> 9) & 1) * 0x537)
        b = ((d << 10) | rem) ^ 0x5412
        for i in range(6):  setf(8, i, _getbit(b, i))
        setf(8, 7, _getbit(b, 6)); setf(8, 8, _getbit(b, 7)); setf(7, 8, _getbit(b, 8))
        for i in range(9, 15): setf(14-i, 8, _getbit(b, i))
        for i in range(8):  setf(SIZE-1-i, 8, _getbit(b, i))
        for i in range(8, 15): setf(8, SIZE-15+i, _getbit(b, i))
        setf(8, SIZE-8, True)
    draw_format(0)                                         # reserve format area

    i = 0; col = SIZE-1
    while col > 0:
        if col == 6: col -= 1
        for vrt in range(SIZE):
            for j in range(2):
                x = col - j
                up = ((col+1) & 2) == 0
                y = (SIZE-1-vrt) if up else vrt
                if not fn[y][x]:
                    bit = _getbit(allcw[i >> 3], 7-(i & 7)) if i < len(allcw)*8 else 0
                    mod[y][x] = bool(bit); i += 1
        col -= 2

    def cond(m, x, y):
        return [ (x+y) % 2 == 0, y % 2 == 0, x % 3 == 0, (x+y) % 3 == 0,
                 (x//3 + y//2) % 2 == 0, (x*y) % 2 + (x*y) % 3 == 0,
                 ((x*y) % 2 + (x*y) % 3) % 2 == 0, ((x+y) % 2 + (x*y) % 3) % 2 == 0 ][m]
    def apply_mask(m):
        for y in range(SIZE):
            for x in range(SIZE):
                if not fn[y][x] and cond(m, x, y): mod[y][x] = not mod[y][x]
    def penalty():
        r = 0
        for y in range(SIZE):
            rc = None; run = 0
            for x in range(SIZE):
                if mod[y][x] == rc: run += 1; r += 3 if run == 5 else (1 if run > 5 else 0)
                else: rc = mod[y][x]; run = 1
        for x in range(SIZE):
            rc = None; run = 0
            for y in range(SIZE):
                if mod[y][x] == rc: run += 1; r += 3 if run == 5 else (1 if run > 5 else 0)
                else: rc = mod[y][x]; run = 1
        for y in range(SIZE-1):
            for x in range(SIZE-1):
                if mod[y][x] == mod[y][x+1] == mod[y+1][x] == mod[y+1][x+1]: r += 3
        for y in range(SIZE):
            b = 0
            for x in range(SIZE):
                b = ((b << 1) & 0x7FF) | (1 if mod[y][x] else 0)
                if x >= 10 and b in (0x05D, 0x5D0): r += 40
        for x in range(SIZE):
            b = 0
            for y in range(SIZE):
                b = ((b << 1) & 0x7FF) | (1 if mod[y][x] else 0)
                if y >= 10 and b in (0x05D, 0x5D0): r += 40
        dark = sum(c for row in mod for c in row); total = SIZE*SIZE
        r += ((abs(dark*20 - total*10) + total - 1)//total - 1) * 10
        return r
    best = None; bestm = 0
    for m in range(8):
        apply_mask(m); draw_format(m); p = penalty(); apply_mask(m)
        if best is None or p < best: best = p; bestm = m
    apply_mask(bestm); draw_format(bestm)
    return mod, v

# ---------- address normalizing ----------
def normalize(addr):
    # Encode EXACTLY what the user types, adding only the invisible http:// scheme.
    # No forced :8080 and no forced trailing slash - the shortest address you type is
    # the shortest URL the QR carries. (The map's port is the user's to include:
    # needed only while the map is on :8080, and gone after the port-flip to :80.)
    # The http:// is what makes a *scan* deterministic - the camera opens it directly
    # with no "search-vs-URL / force-https" guessing - so it stays, invisibly.
    s = (addr or "").strip()
    if not s:
        raise ValueError("Enter the router address, for example  a.lan:8080  or  192.168.8.1:8080")
    if "://" not in s:
        s = "http://" + s
    scheme, rest = s.split("://", 1)
    return scheme.lower() + "://" + rest

def pretty(url):
    # The human-readable form - what you'd type and hit enter (scheme + a bare
    # trailing slash dropped). Shown on the card; never what the QR encodes.
    import re
    return re.sub(r"^https?://", "", url).rstrip("/") or url

# ---------- card rendering ----------
def _font(sz, bold=False):
    from PIL import ImageFont
    names = (["DejaVuSans-Bold.ttf", "arialbd.ttf"] if bold else ["DejaVuSans.ttf", "arial.ttf"])
    for n in names:
        try: return ImageFont.truetype(n, sz)
        except Exception: pass
    for p in (["/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else "")]):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

def make_card(url, box_name="", minimal=False):
    from PIL import Image, ImageDraw
    mod, ver = encode_matrix(url)
    S = len(mod); QZ = 4; SC = 16
    dim = (S + 2*QZ) * SC
    qr = Image.new("RGB", (dim, dim), "white"); dq = ImageDraw.Draw(qr)
    for y in range(S):
        for x in range(S):
            if mod[y][x]:
                px = (x+QZ)*SC; py = (y+QZ)*SC
                dq.rectangle([px, py, px+SC-1, py+SC-1], fill="black")

    # Show the FULL address incl. http:// - this line is a typing instruction, and
    # the only form that works when typed is http://a.lan (bare a.lan gets
    # https-upgraded / search-boxed). So the http:// belongs on the card.
    show = url

    # ----- bare mode: just the code (keeps its quiet zone) + the clean address -----
    if minimal:
        uf = _font(36, True)
        meas = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        uw = meas.textbbox((0, 0), show, font=uf)[2]
        W = max(dim, uw + 40); H = dim + 64
        img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
        img.paste(qr, ((W-dim)//2, 0))
        w = d.textbbox((0, 0), show, font=uf)[2]
        d.text(((W-w)//2, dim + 14), show, font=uf, fill=(0, 0, 0))
        return img, ver

    # ----- full card -----
    title_f = _font(64, True); sub_f = _font(28); box_f = _font(30, True)
    title = "THE LOOKOUT"; sub = "Scan with your phone camera to open the live map"
    # Address line shrinks to fit, and the card widens to hold it, so even a long
    # link is never clipped by the card edge.
    meas = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    usz = 32; url_f = _font(usz, True)
    while usz > 15 and meas.textbbox((0, 0), show, font=url_f)[2] > max(dim, 540):
        usz -= 1; url_f = _font(usz, True)
    uw = meas.textbbox((0, 0), show, font=url_f)[2]
    W = max(dim + 140, uw + 96, 760)
    pad = 58; th = 86; gap = 26; uh = 50; sh = 44; bh = 70
    H = pad + th + gap + dim + gap + uh + 8 + sh + gap + bh + pad
    img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
    d.rectangle([6, 6, W-7, H-7], outline=(11, 61, 110), width=3)   # cut border
    def ctr(t, f, y, fill):
        w = d.textbbox((0,0), t, font=f)[2]; d.text(((W-w)//2, y), t, font=f, fill=fill)
    y = pad
    ctr(title, title_f, y, (11, 61, 110)); y += th + gap
    img.paste(qr, ((W-dim)//2, y)); y += dim + gap
    ctr(show, url_f, y, (0, 0, 0)); y += uh + 8
    ctr(sub, sub_f, y, (90, 90, 90)); y += sh + gap
    label = ("Box:  " + box_name) if box_name.strip() else "Box:  ____________________"
    ctr(label, box_f, y, (60, 60, 60))
    return img, ver

def desktop_dir():
    import os, ctypes
    from ctypes import wintypes
    try:
        buf = ctypes.c_wchar_p()
        FOLDERID_Desktop = ctypes.create_string_buffer(16)
        # {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
        import uuid
        g = uuid.UUID("B4BFCC3A-DB2C-424C-B029-7FE99A87C641").bytes_le
        ctypes.memmove(FOLDERID_Desktop, g, 16)
        res = ctypes.windll.shell32.SHGetKnownFolderPath(FOLDERID_Desktop, 0, 0, ctypes.byref(buf))
        if res == 0 and buf.value: return buf.value
    except Exception: pass
    home = os.path.expanduser("~")
    dsk = os.path.join(home, "Desktop")
    return dsk if os.path.isdir(dsk) else home

def safe_slug(url):
    import re
    s = re.sub(r"^https?://", "", url)
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s or "lookout"

# ---------- GUI ----------
def main():
    import os, tkinter as tk
    from tkinter import messagebox
    root = tk.Tk(); root.title("Lookout QR Maker  v" + VERSION)
    root.configure(bg="white")
    try: root.geometry("460x360")
    except Exception: pass
    pad = {"padx": 16, "pady": 6}
    tk.Label(root, text="Lookout QR Maker", font=("Segoe UI", 18, "bold"),
             fg="#0b3d6e", bg="white").pack(**pad)
    tk.Label(root, text="Makes a printable QR card that opens the map on a phone.",
             font=("Segoe UI", 10), fg="#444", bg="white").pack(padx=16)

    frm = tk.Frame(root, bg="white"); frm.pack(pady=10)
    tk.Label(frm, text="Router address:", font=("Segoe UI", 11), bg="white").grid(row=0, column=0, sticky="e")
    addr = tk.Entry(frm, font=("Segoe UI", 12), width=24); addr.grid(row=0, column=1, padx=8, pady=4)
    addr.insert(0, "192.168.8.1:8080")
    tk.Label(frm, text="Box name (optional):", font=("Segoe UI", 11), bg="white").grid(row=1, column=0, sticky="e")
    name = tk.Entry(frm, font=("Segoe UI", 12), width=24); name.grid(row=1, column=1, padx=8, pady=4)

    minimal_var = tk.IntVar(value=0)
    tk.Checkbutton(root, text="Just the QR code (no card)", variable=minimal_var,
                   bg="white", font=("Segoe UI", 10)).pack(pady=2)

    status = tk.Label(root, text="", font=("Segoe UI", 10), fg="#0b3d6e", bg="white", wraplength=420, justify="center")
    status.pack(pady=4)

    def go():
        try:
            url = normalize(addr.get())
            img, ver = make_card(url, name.get(), minimal=bool(minimal_var.get()))
            tag = "_bare" if minimal_var.get() else ""
            out = os.path.join(desktop_dir(), "Lookout_QR_%s%s.png" % (safe_slug(url), tag))
            img.save(out, "PNG")
            status.config(text="Saved to your Desktop:\n%s\n(QR version %d)" % (os.path.basename(out), ver))
            try: os.startfile(out)
            except Exception: pass
        except Exception as e:
            messagebox.showerror("Lookout QR Maker", str(e))

    tk.Button(root, text="Make QR card", font=("Segoe UI", 12, "bold"),
              bg="#0b3d6e", fg="white", activebackground="#12568f",
              command=go, padx=18, pady=6).pack(pady=8)
    root.mainloop()

if __name__ == "__main__":
    main()
