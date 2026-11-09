import json, pathlib, re, subprocess, sys
from playwright.sync_api import sync_playwright
D = pathlib.Path(sys.argv[1]); IMG = pathlib.Path("/home/claude/repos/ArcGIS-Earth-Unlocked/images")
BLOB = {"978f6c8cc2980e2e78975672b8db750b": "ten_tools_montage.jpg", "eef9733d04ea8e69482b30204b4810a0": "babel_to_shard_short_thumb.jpg",
        "8a28e8169f0b2691fc27053b71971854": "seven_projects_montage.jpg", "c9cfb6bb6d626d00e5f3dde1ed38c858": "mbtiles_converter.jpg",
        "7d398a46dfbf40966f8dc07523e802c2": "earthstick.jpg", "63e799420d3af4cc8ccd23cab5c5c299": "world_gates_v19.jpg",
        "7c9ffa989b9b01ccccef5054c99cf224": "object_factory.jpg", "7327f9f9c1ffdab823d36dc03f2d966d": "pointlayer.jpg",
        "f8865d78cfbbf0fde437c2694bb6cf8d": "parcel100.jpg", "17597f6d3f00ef68ab21b1771c557f14": "prave_me_tracker.jpg",
        "c872e381809a9dc5bba8f8b204012083": "picture_world_sea_street_stone.jpg"}
order = json.loads((D / "project/deck.json").read_text())["order"]
css = """*{margin:0;padding:0;box-sizing:border-box} html,body{width:1920px;height:1080px;overflow:hidden}
section{position:relative;width:1920px;height:1080px;overflow:hidden} aside{display:none}
table{border-collapse:collapse;width:100%} th,td{text-align:left;padding:16px 24px;vertical-align:top} th{border-bottom:3px solid #14213D}
a{color:inherit} @page{size:1920px 1080px;margin:0}"""
pages = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
    for i, sid in enumerate(order):
        html = (D / f"project/slides/{sid}.html").read_text()
        missing = [m for m in re.findall(r"/_blob/([0-9a-f]{32})", html) if m not in BLOB]
        assert not missing, (sid, missing)
        html = re.sub(r"/_blob/([0-9a-f]{32})", lambda m: (IMG / BLOB[m.group(1)]).as_uri(), html)
        f = pathlib.Path(f"s{i:02d}.html").resolve()
        f.write_text(f"<!doctype html><html><head><meta charset=utf-8><style>{css}</style></head><body>{html}</body></html>")
        pg.goto(f.as_uri(), wait_until="networkidle")
        out = f"p{i:02d}.pdf"; pg.pdf(path=out, width="1920px", height="1080px", print_background=True); pages.append(out)
        if sid in ("cover", "family", "proof", "pictures"): pg.screenshot(path=f"{sid}.png")
    b.close()
subprocess.run(["pdfunite", *pages, "ArcGIS_Earth_Unlocked_Briefing_for_Esri.pdf"], check=True)
print(len(pages), "pages")
