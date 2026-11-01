"""check_binaries.py [root=/home/claude/repos]
Open every image, PDF, SVG and zip in the repos and report the ones that are damaged.
Several uploads in Jim's repos were found truncated at about 15 KB; run this after any upload."""
import os, sys, zipfile, subprocess, xml.dom.minidom
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
root = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/repos"
bad = 0
for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d != ".git"]
    for name in files:
        p = os.path.join(dirpath, name); ext = name.lower().rsplit(".", 1)[-1]
        try:
            if ext in ("png", "jpg", "jpeg", "webp", "gif", "tif", "tiff"):
                Image.open(p).load()
            elif ext == "pdf":
                r = subprocess.run(["pdfinfo", p], capture_output=True, text=True)
                if r.returncode: raise ValueError(r.stderr.strip()[:80])
            elif ext == "svg":
                xml.dom.minidom.parse(p)
            elif ext in ("zip", "tpkx", "kmz", "docx", "xlsx"):
                with zipfile.ZipFile(p) as z:
                    b = z.testzip()
                    if b: raise ValueError(f"bad member {b}")
            else:
                continue
        except Exception as e:
            bad += 1; print(f"DAMAGED {os.path.relpath(p, root)}  ({type(e).__name__}: {str(e)[:80]})")
print(f"{bad} damaged file(s)")
