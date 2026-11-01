# Claude Toolbox

Working tools Claude built while maintaining the ArcGIS Earth Unlocked project family. They are kept here so a new Claude session can reuse them instead of rebuilding them. They are maintenance aids, not part of any tool Jim distributes.

All of them assume the seven repositories are cloned side by side under `/home/claude/repos/` (change the path argument if not).

| Tool | What it does | Run |
|---|---|---|
| `linkcheck.py` | Checks every link in all seven repos: relative files, cross-repo GitHub links (including pinned commits and branches) and `#anchors`. | `python3 tools/linkcheck.py` - only known failures are three links in the preserved `legacy/Earth_Beacon_v1.0/README_original.md` |
| `check_binaries.py` | Opens every image, PDF, SVG and zip and reports damaged ones. Several uploads were found truncated at about 15 KB. | `python3 tools/check_binaries.py` |
| `md2pdf.py` | Turns a Markdown user manual into the matching printable PDF (page numbers, links rewritten to GitHub). | From the repo root: `GH_BASE=https://github.com/Jim-dc95811/<repo>/blob/main/ REPO_ROOT=. python3 <path>/md2pdf.py <manual.md> <manual.pdf> "<footer title>"` |
| `crop_screenshot.py` | Crops and resizes one of Jim's screenshots for a page (box in the displayed 2000-px coordinates). | `python3 tools/crop_screenshot.py in.png out.jpg [left top right bottom] [--width 1400]` |
| `ARCGIS_EARTH_API.md` | Working reference for the ArcGIS Earth Automation API: every endpoint, what Jim's tools already prove, what the API cannot do (no click events), and untested ideas such as the camera picture-in-picture. | Read before any API work |
| `test-rigs/` | Regression and hardening rigs for Parcel100, PointLayer, EarthStick, the PRAVE/ME tracker, Master 4 and the Object Factory. | See [`test-rigs/README.md`](test-rigs/README.md) |

Which PDF comes from which manual, the page layout standard, and the video for each tool are listed in [`../CLAUDE.md`](../CLAUDE.md) (section 2a).
