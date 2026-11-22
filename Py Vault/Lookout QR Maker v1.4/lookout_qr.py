# Lookout QR Maker - makes a print-ready QR card for a router address.
# Pure-Python QR encoder (byte mode, versions 1-4, error-correction level M,
# single data block) + Pillow for the card. No external QR library, no internet.
# The GUI needs only tkinter (ships with Python) and Pillow.
#
# Why this exists: phones force https when you TYPE an address, so a crew that
# types 192.168.8.1:8080 lands on nothing. A QR encodes http:// explicitly, so a
# camera scan opens the Lookout map directly. Print the card, tape it to the box.

VERSION = "1.4"   # 1.4: Wi-Fi-join QR (standard WIFI: payload) + a "Join + open" two-code card. 1.3: card shows the full http:// address. 1.2: encode exactly what you type; "Just the QR" bare-code option

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
    s = (addr or "").strip()
    if not s:
        raise ValueError("Enter the router address, for example  192.168.8.1:8080")
    if "://" not in s:
        s = "http://" + s
    scheme, rest = s.split("://", 1)
    return scheme.lower() + "://" + rest

def pretty(url):
    import re
    return re.sub(r"^https?://", "", url).rstrip("/") or url

# ---------- Wi-Fi join payload (standard WIFI: QR) ----------
def wifi_payload(ssid, password, open_net=False, hidden=False):
    """Build the standard WIFI:T:...;S:...;P:...;; string a phone camera reads to join."""
    def esc(s):
        out = ""
        for ch in s:
            if ch in '\\;,:"':
                out += "\\" + ch
            else:
                out += ch
        return out
    ssid = (ssid or "").strip()
    if not ssid:
        raise ValueError("Enter the Wi-Fi network name (SSID).")
    # Match Android's own "Share Wi-Fi" field order exactly (S first, then T, P, H) —
    # some phone parsers (e.g. Moto G) only join when the order matches theirs, even
    # though the spec says order shouldn't matter. H is always present (true/false).
    body = "S:%s;" % esc(ssid)
    if open_net:
        body += "T:nopass;"
    else:
        if not password:
            raise ValueError("Enter the Wi-Fi password (or tick 'Open network').")
        body += "T:WPA;P:%s;" % esc(password)
    body += "H:true;" if hidden else "H:false;"
    s = "WIFI:" + body + ";"
    if len(s) > MAX_BYTES:
        raise ValueError("Network name + password are too long for this encoder (%d of max %d characters)." % (len(s), MAX_BYTES))
    return s

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

def _qr_img(text, SC=16, QZ=4):
    """Render just the QR (with quiet zone) as a PIL image. Returns (img, version, dim)."""
    from PIL import Image, ImageDraw
    mod, ver = encode_matrix(text)
    S = len(mod)
    dim = (S + 2*QZ) * SC
    im = Image.new("RGB", (dim, dim), "white"); d = ImageDraw.Draw(im)
    for y in range(S):
        for x in range(S):
            if mod[y][x]:
                px = (x+QZ)*SC; py = (y+QZ)*SC
                d.rectangle([px, py, px+SC-1, py+SC-1], fill="black")
    return im, ver, dim

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
    show = url
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
    title_f = _font(64, True); sub_f = _font(28); box_f = _font(30, True)
    title = "THE LOOKOUT"; sub = "Scan with your phone camera to open the live map"
    meas = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    usz = 32; url_f = _font(usz, True)
    while usz > 15 and meas.textbbox((0, 0), show, font=url_f)[2] > max(dim, 540):
        usz -= 1; url_f = _font(usz, True)
    uw = meas.textbbox((0, 0), show, font=url_f)[2]
    W = max(dim + 140, uw + 96, 760)
    pad = 58; th = 86; gap = 26; uh = 50; sh = 44; bh = 70
    H = pad + th + gap + dim + gap + uh + 8 + sh + gap + bh + pad
    img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
    d.rectangle([6, 6, W-7, H-7], outline=(11, 61, 110), width=3)
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

def make_wifi_card(wifi_s, ssid, minimal=False):
    """A single card whose QR joins the Wi-Fi."""
    from PIL import Image, ImageDraw
    qr, ver, dim = _qr_img(wifi_s, SC=16)
    show = "Wi-Fi:  " + ssid
    if minimal:
        uf = _font(34, True)
        meas = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        uw = meas.textbbox((0, 0), show, font=uf)[2]
        W = max(dim, uw + 40); H = dim + 60
        img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
        img.paste(qr, ((W-dim)//2, 0))
        w = d.textbbox((0, 0), show, font=uf)[2]
        d.text(((W-w)//2, dim + 12), show, font=uf, fill=(0, 0, 0))
        return img, ver
    title_f = _font(58, True); sub_f = _font(26); ssid_f = _font(30, True)
    title = "JOIN THE WI-FI"; sub = "Scan with your phone camera to join"
    meas = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    W = max(dim + 140, meas.textbbox((0, 0), title, font=title_f)[2] + 96, 760)
    pad = 58; th = 80; gap = 26; uh = 48; sh = 42
    H = pad + th + gap + dim + gap + uh + 8 + sh + pad
    img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
    d.rectangle([6, 6, W-7, H-7], outline=(46, 157, 107), width=3)
    def ctr(t, f, y, fill):
        w = d.textbbox((0,0), t, font=f)[2]; d.text(((W-w)//2, y), t, font=f, fill=fill)
    y = pad
    ctr(title, title_f, y, (46, 157, 107)); y += th + gap
    img.paste(qr, ((W-dim)//2, y)); y += dim + gap
    ctr(show, ssid_f, y, (0, 0, 0)); y += uh + 8
    ctr(sub, sub_f, y, (90, 90, 90))
    return img, ver

def make_combo_card(wifi_s, map_url, ssid):
    """One card, two codes: (1) join the Wi-Fi, (2) open the map."""
    from PIL import Image, ImageDraw
    q1, v1, d1 = _qr_img(wifi_s, SC=12)
    q2, v2, d2 = _qr_img(map_url, SC=12)
    qh = max(d1, d2)
    title_f = _font(54, True); sub_f = _font(24); lab_f = _font(26, True); small_f = _font(20); badge_f = _font(26, True)
    pad = 54; gap = 72
    colw = max(d1, d2, 300)
    W = pad + colw + gap + colw + pad
    th = 68; sh = 38; labh = 96
    H = pad + th + 8 + sh + 30 + qh + 18 + labh + pad
    img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
    d.rectangle([6, 6, W-7, H-7], outline=(11, 61, 110), width=3)
    def ctr(t, f, y, fill, cx):
        w = d.textbbox((0,0), t, font=f)[2]; d.text((cx - w//2, y), t, font=f, fill=fill)
    y = pad
    ctr("THE LOOKOUT", title_f, y, (11, 61, 110), W//2); y += th + 8
    ctr("Scan both:  join the Wi-Fi, then open the map", sub_f, y, (90, 90, 90), W//2); y += sh + 30
    c1x = pad + colw//2
    c2x = pad + colw + gap + colw//2
    qy = y
    img.paste(q1, (c1x - d1//2, qy)); img.paste(q2, (c2x - d2//2, qy))
    y = qy + qh + 18
    def step(cx, n, label, sub, col):
        r = 18
        lw = d.textbbox((0,0), label, font=lab_f)[2]
        total = r*2 + 10 + lw
        x0 = cx - total//2
        d.ellipse([x0, y, x0+2*r, y+2*r], fill=col)
        nw = d.textbbox((0,0), str(n), font=badge_f)[2]
        d.text((x0 + r - nw//2, y + r - 18), str(n), font=badge_f, fill=(255,255,255))
        d.text((x0 + 2*r + 10, y + r - 16), label, font=lab_f, fill=col)
        sw = d.textbbox((0,0), sub, font=small_f)[2]
        d.text((cx - sw//2, y + 2*r + 8), sub, font=small_f, fill=(90,90,90))
    step(c1x, 1, "JOIN WI-FI", ssid, (46, 157, 107))
    step(c2x, 2, "OPEN THE MAP", pretty(map_url), (11, 61, 110))
    return img, max(v1, v2)

def desktop_dir():
    import os, ctypes
    from ctypes import wintypes
    try:
        buf = ctypes.c_wchar_p()
        FOLDERID_Desktop = ctypes.create_string_buffer(16)
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
    try: root.geometry("480x500")
    except Exception: pass
    tk.Label(root, text="Lookout QR Maker", font=("Segoe UI", 18, "bold"),
             fg="#0b3d6e", bg="white").pack(pady=(14, 2))
    tk.Label(root, text="Makes a printable QR card.", font=("Segoe UI", 10),
             fg="#444", bg="white").pack()

    mode = tk.StringVar(value="Open the map")
    tk.Label(root, text="What should the card do?", font=("Segoe UI", 11, "bold"),
             bg="white", fg="#0b3d6e").pack(pady=(12, 2))
    tk.OptionMenu(root, mode, "Open the map", "Join the Wi-Fi", "Join + open (one card)").pack()

    body = tk.Frame(root, bg="white"); body.pack(pady=8, fill="x", padx=20)
    openv = tk.IntVar(value=0); hidev = tk.IntVar(value=0); minv = tk.IntVar(value=0)

    def make_row(label):
        f = tk.Frame(body, bg="white")
        tk.Label(f, text=label, font=("Segoe UI", 11), bg="white", width=16, anchor="e").pack(side="left", padx=(0, 8))
        e = tk.Entry(f, font=("Segoe UI", 12))
        e.pack(side="left", fill="x", expand=True)
        return f, e

    r_addr, addr = make_row("Map address:"); addr.insert(0, "192.168.8.1:8080")
    r_ssid, ssid = make_row("Wi-Fi name:")
    r_pw,   pw   = make_row("Wi-Fi password:")
    r_name, name = make_row("Box name (optional):")
    r_open = tk.Checkbutton(body, text="Open network (no password)", variable=openv, bg="white", font=("Segoe UI", 10), anchor="w")
    r_hide = tk.Checkbutton(body, text="Hidden network", variable=hidev, bg="white", font=("Segoe UI", 10), anchor="w")
    r_min  = tk.Checkbutton(body, text="Just the QR code (no card)", variable=minv, bg="white", font=("Segoe UI", 10), anchor="w")
    allrows = [r_addr, r_ssid, r_pw, r_open, r_hide, r_name, r_min]

    def show(*which):
        for w in allrows: w.pack_forget()
        for w in which: w.pack(fill="x", pady=3)
    def on_mode(*_):
        m = mode.get()
        if m == "Open the map": show(r_addr, r_name, r_min)
        elif m == "Join the Wi-Fi": show(r_ssid, r_pw, r_open, r_hide, r_min)
        else: show(r_ssid, r_pw, r_open, r_hide, r_addr)
    mode.trace_add("write", on_mode); on_mode()

    status = tk.Label(root, text="", font=("Segoe UI", 10), fg="#0b3d6e", bg="white", wraplength=440, justify="center")
    status.pack(pady=4)

    def go():
        try:
            m = mode.get()
            if m == "Open the map":
                url = normalize(addr.get())
                img, ver = make_card(url, name.get(), minimal=bool(minv.get()))
                out = os.path.join(desktop_dir(), "Lookout_QR_%s%s.png" % (safe_slug(url), "_bare" if minv.get() else ""))
            elif m == "Join the Wi-Fi":
                w = wifi_payload(ssid.get(), pw.get(), open_net=bool(openv.get()), hidden=bool(hidev.get()))
                img, ver = make_wifi_card(w, ssid.get().strip(), minimal=bool(minv.get()))
                out = os.path.join(desktop_dir(), "Lookout_WiFi_%s%s.png" % (safe_slug(ssid.get() or "wifi"), "_bare" if minv.get() else ""))
            else:
                w = wifi_payload(ssid.get(), pw.get(), open_net=bool(openv.get()), hidden=bool(hidev.get()))
                url = normalize(addr.get())
                img, ver = make_combo_card(w, url, ssid.get().strip())
                out = os.path.join(desktop_dir(), "Lookout_Join_and_Open_%s.png" % safe_slug(ssid.get() or "lookout"))
            img.save(out, "PNG")
            status.config(text="Saved to your Desktop:\n%s\n(QR version %s)" % (os.path.basename(out), ver))
            try: os.startfile(out)
            except Exception: pass
        except Exception as e:
            messagebox.showerror("Lookout QR Maker", str(e))

    tk.Button(root, text="Make QR card", font=("Segoe UI", 12, "bold"),
              bg="#0b3d6e", fg="white", activebackground="#12568f",
              command=go, padx=18, pady=6).pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    main()
