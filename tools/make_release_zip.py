"""make_release_zip.py <out.zip> <folder name in zip> <src1>[=<dest path inside folder>] ...
Builds a release zip: one top folder, files copied byte-for-byte, fixed timestamps,
no __pycache__, every .bat checked for CRLF line endings (it refuses LF-only .bat files).
Example: make_release_zip.py releases/Tool_v1.2.zip Tool_v1.2 Tool.bat "System Files"
         (src=dest renames: "build/System Files=System Files")
Written 2026-11-06 for Jim's one-obvious-file packaging (one .bat + System Files)."""
import sys, zipfile, pathlib, time
out, top, items = sys.argv[1], sys.argv[2], sys.argv[3:]
T = (2026, 11, 6, 15, 30, 0)
files = []
for it in items:
    src, _, dest = it.partition("=")
    src = pathlib.Path(src)
    if src.is_dir():
        for f in sorted(src.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                files.append((f, f"{dest or src.name}/{f.relative_to(src).as_posix()}"))
    else:
        files.append((src, dest or src.name))
dirs = sorted({str(pathlib.PurePosixPath(d).parent) for _, d in files} - {"."})
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr(zipfile.ZipInfo(top + "/", T), "")
    for d in dirs:
        for i in range(1, len(d.split("/")) + 1):
            name = top + "/" + "/".join(d.split("/")[:i]) + "/"
            if name not in z.namelist():
                z.writestr(zipfile.ZipInfo(name, T), "")
    for f, d in files:
        data = f.read_bytes()
        if d.lower().endswith(".bat"):
            assert b"\r\n" in data and data.count(b"\n") == data.count(b"\r\n"), f"{d} is not CRLF"
        zi = zipfile.ZipInfo(f"{top}/{d}", T); zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, data)
print(out)
for n in zipfile.ZipFile(out).namelist():
    print("  ", n)
