# Maintainer self-test (no .bat on purpose). Encodes several addresses, renders
# each card, and decodes it back with OpenCV to confirm it is scannable.
# v1.2: normalize() encodes EXACTLY what is typed (adds only http://, no forced
# :8080 and no forced trailing slash); also exercises the bare "Just the QR" mode.
import sys, cv2, numpy as np
import lookout_qr as L

def decode(img):
    arr = np.array(img)[:, :, ::-1].copy()   # RGB->BGR
    data, pts, _ = cv2.QRCodeDetector().detectAndDecode(arr)
    return data

# (typed address, expected encoded URL) — encode exactly what you type
cases = [
    ("a.lan",                            "http://a.lan"),                  # v1 (the clean one)
    ("a.lan:8080",                       "http://a.lan:8080"),
    ("north.lan:8080",                   "http://north.lan:8080"),
    ("192.168.8.1:8080",                 "http://192.168.8.1:8080"),
    ("192.168.8.1",                      "http://192.168.8.1"),            # no port imposed
    ("http://192.168.8.1:8080/",         "http://192.168.8.1:8080/"),      # scheme/slash preserved
    ("192.168.8.1:8080/m/a_mega_4_grid", "http://192.168.8.1:8080/m/a_mega_4_grid"),            # -> v3
    ("192.168.8.1:8080/m/c-master-grid-1s-ghy-z20-a/", "http://192.168.8.1:8080/m/c-master-grid-1s-ghy-z20-a/"),  # long deep link
]
ok = True
for raw, expect in cases:
    url = L.normalize(raw)
    assert url == expect, "normalize(%r)=%r expected %r" % (raw, url, expect)
    img, ver = L.make_card(url, "Jax 24")
    got = decode(img)
    good = (got == url)
    ok = ok and good
    print(("PASS" if good else "FAIL"), "v%d" % ver, "%-44s" % url, "-> decoded %r" % got)

# bare "Just the QR" mode still produces a scannable code
bimg, bver = L.make_card(L.normalize("a.lan"), minimal=True)
bgot = decode(bimg)
bgood = (bgot == "http://a.lan")
ok = ok and bgood
print(("PASS" if bgood else "FAIL"), "bare v%d" % bver, "%-44s" % "http://a.lan", "-> decoded %r" % bgot)

# pretty() = what you'd type, scheme + bare trailing slash dropped
assert L.pretty("http://a.lan") == "a.lan"
assert L.pretty("http://a.lan:8080/") == "a.lan:8080"
print("PASS pretty() strips scheme + bare trailing slash")

# length guard
try:
    L.encode_matrix("x" * 90); print("FAIL overlong not rejected"); ok = False
except ValueError:
    print("PASS overlong rejected")

print("\nLOOKOUT QR SELF TEST:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
