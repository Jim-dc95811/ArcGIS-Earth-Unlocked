# Maintainer self-test (no .bat on purpose). Encodes several addresses, renders
# each card, and decodes it back with OpenCV to confirm it is scannable.
import sys, cv2, numpy as np
import lookout_qr as L

def decode(img):
    arr = np.array(img)[:, :, ::-1].copy()   # RGB->BGR
    data, pts, _ = cv2.QRCodeDetector().detectAndDecode(arr)
    return data

cases = [
    ("192.168.8.1",                      "http://192.168.8.1:8080/"),      # v1/v2
    ("192.168.8.1:8080",                 "http://192.168.8.1:8080/"),
    ("http://192.168.8.1:8080/",         "http://192.168.8.1:8080/"),
    ("10.250.46.100",                    "http://10.250.46.100:8080/"),
    ("192.168.8.1:8080/m/a_mega_4_grid", "http://192.168.8.1:8080/m/a_mega_4_grid"),  # longer -> v3
    ("192.168.8.1:8080/m/b-mega-4-grid-z-16-bing/", "http://192.168.8.1:8080/m/b-mega-4-grid-z-16-bing/"),  # Jim's 50-char deep link
    ("192.168.8.1:8080/m/c-master-grid-1s-ghy-z20-a/", "http://192.168.8.1:8080/m/c-master-grid-1s-ghy-z20-a/"),
]
ok = True
for raw, expect in cases:
    url = L.normalize(raw)
    assert url == expect, "normalize(%r)=%r expected %r" % (raw, url, expect)
    img, ver = L.make_card(url, "Jax 24")
    got = decode(img)
    good = (got == url)
    ok = ok and good
    print(("PASS" if good else "FAIL"), "v%d" % ver, "%-40s" % url, "-> decoded %r" % got)

# length guard
try:
    L.encode_matrix("x" * 90); print("FAIL overlong not rejected"); ok = False
except ValueError:
    print("PASS overlong rejected")

print("\nLOOKOUT QR SELF TEST:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
