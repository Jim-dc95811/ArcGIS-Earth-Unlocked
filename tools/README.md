# Claude Toolbox

Working tools Claude built while maintaining the ArcGIS Earth Unlocked project family. They are kept here so a new Claude session can reuse them instead of rebuilding them. They are maintenance aids, not part of any tool Jim distributes.

All of them assume the seven repositories are cloned side by side under `/home/claude/repos/` (change the path argument if not).

| Tool | What it does | Run |
|---|---|---|
| `linkcheck.py` | Checks every link in all seven repos: relative files, cross-repo GitHub links (including pinned commits and branches) and `#anchors`. | `python3 tools/linkcheck.py` - only known failures are three links in the preserved `legacy/Earth_Beacon_v1.0/README_original.md` |
| `check_binaries.py` | Opens every image, PDF, SVG and zip and reports damaged ones. Several uploads were found truncated at about 15 KB. | `python3 tools/check_binaries.py` |
| `md2pdf.py` | Turns a Markdown user manual into the matching printable PDF (page numbers, links rewritten to GitHub). | From the repo root: `GH_BASE=https://github.com/Jim-dc95811/<repo>/blob/main/ REPO_ROOT=. python3 <path>/md2pdf.py <manual.md> <manual.pdf> "<footer title>"` |
| `crop_screenshot.py` | Crops and resizes one of Jim's screenshots for a page (box in the displayed 2000-px coordinates). | `python3 tools/crop_screenshot.py in.png out.jpg [left top right bottom] [--width 1400]` |
| `make_gate_kmz.py` | Builds wormhole gate KMZs for EarthStick 1.3+: golden vertical rings (absolute altitude) with the gate data EarthStick reads (`gate, lat, lon, alt_m, radius_m, facing, to` or `dest_*`). | `from make_gate_kmz import gate, write_kmz` (see its docstring) |
| `build_world_gates.py` | Builds Jim's World Gates file: JAX (over JIA) -> ATL hub (Hartsfield, rings stacked by direction, 1,500 ft above the field) -> NYC, London, Paris, Rome, Tokyo, Sydney, Rio landmarks, each with an ATL return ring; red back sides. | `python3 tools/build_world_gates.py out.kmz` |
| `ARCGIS_EARTH_API.md` | Working reference for the ArcGIS Earth Automation API: every endpoint, what Jim's tools already prove, what the API cannot do (no click events), and untested ideas such as the camera picture-in-picture. | Read before any API work |
| `samples/` | `TEST_Camera_SR200_W_of_I95.kmz`: the proven live-camera object (FL511 camera 1362 in the popup, refreshes every 10 s). Unzip to read `doc.kml`. | Open in ArcGIS Earth |
| `test-rigs/` | Regression and hardening rigs for Parcel100, PointLayer, EarthStick, the PRAVE/ME tracker, Master 4 and the Object Factory. | See [`test-rigs/README.md`](test-rigs/README.md) |
| `preview_view.py` | Draws what a KMZ looks like in ArcGIS Earth from a camera pose (pinhole model fitted to Jim's screenshots, 5 px rms) and lists overlapping labels - check gate packs and sky objects before Jim flies them. | `from preview_view import load_kmz, render, overlaps` |

Which PDF comes from which manual, the page layout standard, and the video for each tool are listed in [`../CLAUDE.md`](../CLAUDE.md) (section 2a).
