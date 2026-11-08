"""Put a PDF manual beside the .bat inside a release zip (same zip name; programs untouched). Idempotent.
Usage: python3 tools/add_manual_to_zip.py <release.zip> <manual.pdf>   (Jim 2026-11-08: manual next to the .bat in every package)"""
import sys, zipfile, os, hashlib
zpath, pdf = sys.argv[1], sys.argv[2]
name = os.path.basename(pdf)
with zipfile.ZipFile(zpath) as z:
    items = [(i, z.read(i)) for i in z.infolist()]
top = items[0][0].filename.split("/")[0]
items = [(i, d) for i, d in items if i.filename != f"{top}/{name}"]
tmp = zpath + ".partial"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
    for i, d in items:
        out.writestr(i, d)
    info = zipfile.ZipInfo(f"{top}/{name}", (2026, 11, 8, 14, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    out.writestr(info, open(pdf, "rb").read())
os.replace(tmp, zpath)
with zipfile.ZipFile(zpath) as z:
    tops = sorted({n.split("/")[1] for n in z.namelist() if n.count("/") >= 1 and n.split("/")[1]})
print(f"{os.path.basename(zpath)}: {top}/ -> {', '.join(tops)}")
