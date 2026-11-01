"""crop_screenshot.py <in.png> <out.jpg|png> [left top right bottom] [--width 1400] [--display-width 2000]
Crop one of Jim's screenshots and resize it for a README.
Box coordinates are in the DISPLAYED image size (the chat shows his 3840x2160 shots at 2000 px wide,
so they are scaled by real_width / display_width). Omit the box to keep the whole frame.
JPG for maps/photos (quality 86), PNG for UI windows."""
import sys
from PIL import Image
args, opts, it = [], {}, iter(sys.argv[1:])
for a in it:
    if a.startswith("--"):
        opts[a] = next(it)
    else:
        args.append(a)
width = int(opts.get("--width", 1400)); disp = float(opts.get("--display-width", 2000))
src, out = args[0], args[1]
im = Image.open(src).convert("RGB")
if len(args) >= 6:
    f = im.width / disp
    im = im.crop(tuple(round(float(v) * f) for v in args[2:6]))
if im.width > width:
    im = im.resize((width, round(width * im.height / im.width)), Image.LANCZOS)
kw = {"quality": 86, "optimize": True} if out.lower().endswith((".jpg", ".jpeg")) else {"optimize": True}
im.save(out, **kw); print(out, im.size)
