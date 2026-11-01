# CLAUDE.md - Continuity for Claude

**Written by Claude, for Claude.** Read this first after any session reset. It is the fastest way to get fully caught up on Jim's ArcGIS Earth Unlocked project family and how to work with him.

**Last updated:** 2026-11-01

Update this file whenever something durable changes: a release, an accepted test, a new rule, a decision, an open item opened or closed. Keep it current rather than long. History belongs in the session log at the bottom, kept short.

---

## 1. Resume procedure

1. Clone all seven public repos (list in section 3) into one working folder (this session used `/home/claude/repos/<Repo>`; `tools/linkcheck.py` expects that root).
2. To push, each repo must be attached to the session with write access first (`add_repo` with `access: push`). Without that, the git proxy returns 403 even though `list_repos` shows `can_push: true`.
3. Read this file, then the repo-specific continuity file for whatever repo the task touches (section 3 says where each one lives).
4. Before editing, `git fetch` and check that nothing new landed upstream. Jim edits on GitHub directly and often.
5. Check section 6 (open items) before proposing new work.
6. Re-run `python3 tools/linkcheck.py` after any doc change (only known failures: three links inside the preserved `legacy/Earth_Beacon_v1.0/README_original.md`).

The older continuity files in each repo were written by ChatGPT for ChatGPT. They are still valuable and mostly accurate, but some are dated snapshots. Where they conflict with this file, this file is newer; where they conflict with the live repo, the live repo wins.

---

## 2. Owner and working rules

- **Owner:** Jim Gaddy, GitHub `Jim-dc95811`. Public-safety / fire-service background, decades of hands-on computer and electronics work. Not a traditional programmer; a relentless tester who trusts measured behavior over theory.
- **Mission:** "Create new map makers." "Do not make the user learn GIS before they can use geography."
- **Audience and goal (Jim, 2026-11-01):** open-source sharing of this knowledge with everyone. Jim works for a state government fire department, the primary consumers of this information; the project has expanded to a general-public appeal and to the GIS community. He has met pushback from parts of the GIS community. Pages are written for YouTube visitors with no GitHub experience. A video focused on objects (Object Factory) is planned.
- **Primary environment:** Windows 11, Python 3.14.x, ArcGIS Earth desktop (Automation API at `http://localhost:8000`), ArcGIS Earth Mobile on Android, QGIS. All tools are Windows/Python with `.bat` launchers.

**Minimal Build Rule (non-negotiable):**
- Implement only what was asked. No unrequested cleanup, refactors or "improvements".
- One functional change at a time, discussed first.
- Every code change gets a new version number.
- Preserve filenames, paths, constants and known-good behavior unless the change specifically requires otherwise.
- Nothing is "accepted" until Jim live-tests it in ArcGIS Earth.
- Keep **verified**, **owner-observed**, **inferred** and **conceptual** clearly separate. "Unknown" beats pretending.
- No new dependencies unless they solve a demonstrated need.

Documentation fixes (broken links, stale versions, typos) are fine when Jim asks for an errors pass. Code and release zips are not touched without explicit direction. Manual PDFs are now generated from their Markdown (see section 2a), except Jim's own tester PDF, which stays unmodified.

**Code-hardening workflow (agreed 2026-10-31):** go page by page in the order of the umbrella README. For each script: review and test here, report findings ranked by importance, change nothing until Jim approves. Jim chose to bundle approved fixes for one script into a single release (e.g. mb2tpkx v1.1) rather than one version per fix. Build in a dev folder, test here (including a byte-for-byte regression against the current version where output files exist), then hand off for Jim's live Windows/ArcGIS Earth test. Post to main only after he accepts.

**Delivering test builds:** the chat app's file cards do not work for Jim with `.bat` or `.zip` files. Push the test zip to a separate branch (`<tool>-v<ver>-test`, under `test-builds/`) and give him the GitHub raw link plus the file-page link. This sandbox cannot reach raw.githubusercontent.com, so verify by comparing the branch blob with `git show`, not by downloading. The session's git proxy also refuses branch deletion, so ask Jim to delete finished test branches on GitHub (Branches page). If the stop hook demands a push before Jim's input is in, park work on a side branch, never on main.

Note on terms: MBTiles cannot be opened in ArcGIS Earth; only the converted TPKX can.

### 2a. Page and documentation standard (approved by Jim 2026-11-01)

- **"Link, link, pic":** for every tool on every page: a bold "⬇️ DOWNLOAD <TOOL> vX" heading link to the zip, then a bold "📖 User manual" link on the next line, then one plain line, then a screenshot that opens the YouTube video (caption ends "▶️ Watch the video (YouTube).") Where there is no video, the picture stands alone. Same layout on a repo's GitHub Pages site if it has one (only Chartplotting has `index.html`).
- **Screenshots** come from Jim (3840x2160 PNGs; his displayed coordinates are x1.92). Crop to the app/map, save as ~1400 px JPG (PNG for UI windows) in that repo's `images/` or `assets/`, and preview with Playwright when a site is involved (1280 and 390 px). Never use a screenshot that is already on another page without asking.
- **Videos:** MBTiles converter `C71n8TAByuE`, Master 4 `zNt-I4KgAy8`, Batch Factory `KGckjaOu0hY`, EarthStick / PointLayer / Object Factory `5Wn14qlC7n4`, Parcel100 `_hMB_TOODOQ`, PRAVE/ME Tracker `JKWJmEIBP_I`.
- **Unlocked front page** order: title, one plain sentence, quote, "The project pages" (6 numbered links), "Download the tools" (8 tools; zips via `github.com/.../raw/main/...`; pictures open the tool's page; local copies in `images/` at 1000 px), "Start with what you want to do" table (Jim: keep), "How the pieces fit", Independence, mission. PRAVE/RMC tester stays off the front page (Jim).
- **Manual PDFs** are generated from the Markdown manual with `tools/md2pdf.py` (python-markdown + Playwright Chromium; run with `GH_BASE=https://github.com/Jim-dc95811/<repo>/blob/main/ REPO_ROOT=.` from the repo root so relative links become GitHub links). Regenerate the PDF whenever its manual changes. Each manual opens with a "printable copy" link to its PDF.
- **Corruption check:** several uploads in these repos were truncated at about 15 KB. Before trusting any binary, open it (PIL / `pdfinfo` / `unzip -t`).

### 2b. Working with Jim (observed)

- He answers tersely: "engage" = go ahead; "approve all" / "1.4 yes 1-6" = approve the listed findings; "works good" or a screenshot = live acceptance. Do not press for self-tests after that.
- Best format for decisions: findings ranked by importance, each with a plain one-line consequence, then a single recommendation. He usually picks the recommendation.
- He wants to be told when something is broken even if he did not ask (corrupt files, stale PDFs, wrong versions), then decides what to do.
- Plain words: he is not a programmer. Name buttons and files exactly; skip code detail unless asked.
- "Confirm X" means check it with a tool (e.g. `git ls-remote`, link check), not from memory.
- He edits on GitHub himself between turns: always `git pull` before editing, and re-check what you claim is there.

### 2c. Sandbox facts (this cloud workspace)

- No `python3-tk`: stub Tkinter (see `tools/test-rigs/README.md`). Pillow, python-markdown, pandoc, poppler (`pdfinfo`, `pdftotext`, `pdftoppm`) and Playwright Chromium are available.
- Blocked: PyPI for some packages (pyserial: clone from GitHub instead), YouTube (thumbnails and pages), raw.githubusercontent.com. `gh run list` works; `gh api .../pages` is refused.
- GitHub Actions in Parcel100 commits a rebuilt zip after pushes to main; pull before the next edit.
- Repos must be attached with `add_repo(access: push)` before pushing; branch deletion is refused (Jim deletes branches).
- **Claude Toolbox (`tools/`, Jim's idea 2026-11-01): check `tools/README.md` before writing a helper from scratch.** It holds `linkcheck.py`, `check_binaries.py`, `md2pdf.py`, `crop_screenshot.py`, `test-rigs/` and `ARCGIS_EARTH_API.md` (Automation API reference: proven vs documented vs untested; read it before any API work). Add new reusable helpers there and list them in its README.

---

## 3. The seven repos

| Repo | Role | Current version | Continuity file |
|---|---|---|---|
| `ArcGIS-Earth-Unlocked` | Umbrella front door / system map | - | this file |
| `QGIS-Mbtile-to-ArcGIS-Earth-TPKX` | Foundation maps: MBTiles -> TPKX converter + Master 4 Grid Maker | mb2tpkx v1.1 (protected baseline), Master 4 v3.1 | `CONTINUITY.md` (snapshot 2026-10-10, dated notes since) |
| `ArcGIS-Earth-Offline-Maps-Chartplotting` | ArcGIS Pro TPKX route (Batch Factory), mobile offline, chartplotting, PRAVE/ME tracker; GitHub Pages site `index.html` | Batch Factory v1 (Extent Tool v2 retired 2026-11-01), PRAVE/ME Tracker v1.2, PRAVE/RMC Tester v1.0 Gold | none (README + `docs/`; this file) |
| `EarthStick` | Joystick flight of the ArcGIS Earth camera | 1.1 (protected baseline) | `CONTINUITY.md` |
| `ArcGIS-Earth-Object-Factory` | Geographic object authoring: Objects, Batch, Sky Compass, Beacon | 1.1 (released 2026-10-31) | `internal/CONTINUITY.md` + `internal/MAPWORLD.md` |
| `Point-Maps` | PointLayer: public ArcGIS point service -> offline KMZ/GeoJSON | 1.4 | `CONTINUITY.md` |
| `Parcel100` | Master 4 box -> up to 100 parcel GeoJSON cells | 1.5 | `CONTINUITY.md` |

Jim also has private repos outside this family. They are not covered here.

### Architecture in one picture

```text
Foundation maps  -> what the world looks like          (TPKX)
Operational data -> what databases know about it        (Parcel100, PointLayer)
EarthStick       -> how the user moves through it
Object Factory   -> intentional objects and meaning placed in it
ArcGIS Earth     -> the common renderer
```

**Foundation = stable geography. Layers = changing information.** Never rebuild a big foundation map because one object changed. **Offline first**: online links are optional extensions.

### Key facts per repo

**QGIS MBTiles -> TPKX**
- `mb2tpkx.py`: 256x256 PNG/JPEG Web Mercator raster MBTiles -> Esri Compact Cache V2 TPKX, bytes copied unchanged, TMS rows flipped to XYZ. Needs Pillow. Does not download imagery or build missing zooms. **v1.1 released 2026-10-31** (hardening only; see `MB2TPKX_V1.1_CHANGES.md` in that repo). v1.1 `mb2tpkx.py` SHA-256 `b2efa752a6f386b6bada84532efe8ee56fed3c9863fa3c6dd76f51129e85f785`; `.bat` unchanged. Baselines are also in its `CONTINUITY.md` and `TECHNICAL.md`; do not change without explicit authorization.
- Field-proven in ArcGIS Earth at 4 GB, 20+ GB and 40 GB-class packages.
- **Master 4:** one whole-degree box entered as `west, east, south, north` (e.g. `82w, 81w, 30n, 31n`), split into 100 cells of 0.1 degrees. Cell number = (first decimal of |lat|) x 10 + (first decimal of |lon|) + 1, so `30.56N 81.34W` is cell 54. Outputs: `Master4_<box>_Extents.txt` (100 rows + `MASTER` row, EPSG:3857) and `Master4_<box>_Grid.tif`. Optional Cell 55 Z10-Z20 synthetic demo TPKX, default No. **v3.1 released 2026-10-31** (hardening only; `MASTER4_V3.1_CHANGES.md`); `.py` SHA-256 `5ca38785a5b5e9537dc1b3d2d79c829414efe86816f7bc0f7407fdc3cbe632e7`. Output folder is hard-coded `C:\downloads`.
- Filename pattern: `W082W081N031N030-055-GHY-Z20.tpkx`. This numbering and naming is shared infrastructure (Parcel100 uses it). Do not change it casually.
- **Operation Map Florida:** statewide enhanced Z17 overview packages (seven-layer FFS-style recipe). Rule: "Measure three times, form once" - do not build the statewide numbered index until all Z17 extents are locked.
- Android: ~2 GB Z17 TPKX is the practical ceiling; copy from SD card to internal storage before opening.
- Manuals: `MB2TPKX_USER_MANUAL.md` (new 2026-11-01) and `MASTER4_GRID_MAKER.md`, each with a generated PDF of the same base name as before (`mb2tpkx_User_Manual.pdf`, `Master4_Grid_Maker_User_Manual.pdf`).

**EarthStick 1.1**
- Thrustmaster TCA Sidestick Airbus Edition (Windows name `T.A320 Pilot`), WinMM/ctypes, standard library only.
- Neutral controls = hover. Button 4 (red) zoom in/descend, Button 3 (black) zoom out/climb, all other buttons unassigned.
- **1.1 released 2026-10-31** (hardening; flying identical to 1.0): waits for the joystick at startup, proxy-free localhost API opener, startup wait prints reason, single post-error prompt. `releases/EarthStick_v1.1.zip` SHA-256 `505295a68e041bec7ae921f2c71b5240816946a8d5bb5f48459f3b237819c52e`; `EarthStick.py` `84894c2f2d6c857ba71b2153126cb274254e3dbf23099ca1b821dbc2ca7400c7`. `releases/EarthStick_v1.0.zip` (`8b399d70...`) kept for existing links; README presents only 1.1. Change doc `docs/EARTHSTICK_V1.1_CHANGES.md`. Constants and recovery behavior are locked; see its `CONTINUITY.md`.
- Test rig: `es_rig.py` pattern - load EarthStick.py via exec into a module, replace `WinJoystick` with a scripted class, `time` with a sleep-driven fake clock, `os.name` with 'nt', and point `CAMERA_URL` at a local mock camera API; compare the PUT stream between versions.

**Object Factory 1.1**
- v1.0 = accepted v0.2.2 TEST build, promoted with only three text changes (version string, one error message, startup status). v1.0 source SHA-256 `e77e1866e7a87b9824ed6bb1cd0f830f52adb1a2872efe48ede13a581018aa00`, which exists only in commit `b65a54c`; Jim removed the loose file from the repo root on 10/30.
- **v1.1 released 2026-10-31** (hardening; outputs identical to v1.0): `releases/ArcGIS_Earth_Object_Factory_v1.1.zip` (folder `Object_Factory_v1.1/`, SHA-256 `927ed4bf...`), source `source/Object_Factory_v1.1.py` (`f94a2034a9e3348d81a2a2061619201fd795d36930c2b64797ebb2611f5b6b70`), change doc `docs/OBJECT_FACTORY_V1.1_CHANGES.md`. v0.2.2 TEST zip removed from current files. Jim accepted on live proof (POF screenshot); he considers working output sufficient and did not run `--selftest` - don't keep pressing for it. Clipboard from Google Maps right-click is THE coordinate method; never reintroduce ArcGIS Earth camera pickup.
- 11 presets: object, helicopter, fuel, bird, hazard, home, staging, water, firetruck, camera, medical. PNGs normalized to 256 px or less on a working copy; originals never modified. Labels off by default; popup Info or None. Batch aliases: pin, heli, gas, gas_pump, warning, base, truck, viewpoint, hospital; unknown type -> object. Default outputs on the Desktop.
- Batch format: `type|name|lat|lon|alt_m|icon|description|url|link_text|scale|altitude_mode|tether|popup|label`, with comma shorthand `type,lat,lon[,alt][,name]`.
- This repo was formerly `Earth-Beacon`. Standalone Beacon Maker v1.0 source/docs are preserved in `legacy/Earth_Beacon_v1.0/`; it is no longer a separate download (retired 2026-10-31).
- Known cosmetic issue: ArcGIS Earth's native KML popup box is larger than wanted. That is viewer behavior, not a bug in the factory.
- ChatGPT was given broad design authority over the Object Factory build. Do not assume Claude has the same authority; ask.

**PointLayer 1.4** (released 2026-11-01; hardening, normal output identical to 1.3)
- `releases/PointLayer_v1.4.zip` (`1987c1ef...`), `PointLayer.py` SHA-256 `d09a4fae215a2fdd2e8a19faaac99140966e782a6ea93e69c8679e3b57ed3c67`; 1.3 zip kept for links. Change doc `docs/POINTLAYER_V1.4_CHANGES.md`. 1.4: completeness check (OID always requested, missing re-requested once, write-and-warn), XML control-char stripping, zero-area Region widening, no-location count, overwrite prompt + .partial, PNG check. Internet requests keep the system proxy on purpose.
- Test rig: `pl_rig.py`/`test_pl14.py` pattern - stub tkinter, mock FeatureServer (layer 458) with knobs for dropped features, null geometry, control chars, single point/same latitude, no OID field.
- Accepts a service root or layer URL, discovers point layers (Nassau hydrants are layer 458, not 0). Downloads the whole layer via `returnIdsOnly` + batches. Geometry from `outSR=4326`, never from attribute fields named Lat/Lon/X/Y.
- Accepted LODs: Nassau 3,250 features -> 12,000; Duval 30,688 -> 30,000. Starting points, not laws.
- Say "3,250 features were published and downloaded", never "the county has 3,250 hydrants".
- Multi-tier duplicate-symbol LOD was tested and rejected. Do not reintroduce without discussion.

**PRAVE/ME Tracker 1.2** (Chartplotting repo; still in active field use)
- Download stays `downloads/PRAVE_ME_Tracker_v1.zip` (README and `index.html` link to it); folder `PRAVE_ME_Tracker/` with `.py`, `START_TRACKER.bat`, `SELF_TEST.bat`. v1.2 `.py` SHA-256 `f1f0d8685675a59cc55de59d17a5aadd089a474fbcc3a9fc4f82dbd24bf98b56` (v1.1 was `c1f2416c...`). Change doc `docs/PRAVE_ME_TRACKER_V1.1_CHANGES.md`.
- Gold field layout: PRAVE lat 3, lon 4, district 8, RSSI 12, individual 13; display `district-NNN`. Sanity filters: lat 20-70N, west longitudes only. Never touches the Windows clock.
- Settings above HERE BE DRAGONS: `INPUT_PORT` (COM12), `INPUT_BAUD` 19200, `ICON_FOLDER` `C:\MyData\PRAVE_ME\Icons` (six firetruck_rssi_*.png, not distributed).
- **Bench tester:** Jim's `PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold` (.py/.bat/PDF) published unmodified as `downloads/PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.zip` (dev log omitted). RMC 1 Hz at 30.419107,-81.926499; units 7-101..7-106 = RSSI blank,-115,-105,-95,-85,-75. Also defaults to COM12, so tester and tracker need opposite ports of a pair. Its PDF predates the ArcGIS Earth tracker (says COM3, TimeKeeper icon path, Google Earth placemarks, clock sync) - differences documented in `docs/PRAVE_ME_TRACKER.md` instead of editing his PDF.
- **Batch Factory** (same repo): ArcGIS Pro 3.7 add-in, .NET 10 (`net10.0-windows`), built on the user's PC by `BUILD_INSTALL.bat` -> `Factory/BUILD_QUIET.ps1` -> Add-In Installation Utility; appears on the Add-In tab as **Open Factory**. Jim confirmed the install steps (open ArcGIS Pro FIRST, then run the BAT; restart Pro after installing). Its extent regex rejects Master 4 TXT rows that still carry the trailing `.tpkx` name - docs tell users to delete it.
- Test rig used here: Gold tester -> pty -> tracker -> mock Automation API (GET/PUT camera, POST/DELETE drawings). pyserial is not pip-installable in this sandbox; clone github.com/pyserial/pyserial tag v3.5 and use PYTHONPATH.

**Parcel100 1.5**
- Standard library only. Florida source: `services5.arcgis.com/GcvM6vDlR2gM4x31/.../FL_Parcels/FeatureServer/0`. Recommended fields: OWN_NAME, PHY_ADDR1, PHY_CITY, PHY_ZIPCD, PARCEL_ID, Acres.
- Output `W082W081N031N030-004-Parcels.geojson`. Since 1.5: `.partial` writes; resume skips an existing cell only if it loads as a FeatureCollection, otherwise rebuilds it. Per-parcel completeness check (OID field requested, not written; missing re-asked once; write and warn). Timed-out batches split in half. Accepts service roots with a polygon-layer chooser.
- A GitHub Actions workflow rebuilds `downloads/Parcel100_v1.5.zip` (changed from v1.4 at the 1.5 release) whenever `Parcel100.py`, `Parcel100.bat` or `PACKAGE_README.txt` change on main. README/doc edits do not trigger it. The bot zip's own SHA changes every rebuild (timestamps); check the `.py` inside instead. Bump the workflow's file name at every version change.
- The root `Parcel100_User_Manual.pdf` is the 1.5 manual generated from `USER_MANUAL.md` (2026-11-01; the old v1.1 PDF is in Git history).

---

## 4. Evidence and rights discipline

- Do not claim the converter downloads imagery, or that file-format openness grants imagery rights.
- Do not claim large real TPKX packages were validated in ArcGIS Pro unless separately tested there.
- Public GIS availability does not mean unrestricted redistribution. Repos distribute tools, not agency datasets.
- No life-safety or certification claims.
- Generated artwork in the repos is illustrative, not authoritative geometry.

---

## 5. Pending ideas (not approved for building)

From the older continuity files. None of these is approved just by appearing here:
- Clipboard -> QR -> email pin-drop utility (verify ArcGIS Earth app-link syntax first).
- Object Factory: Camera/Viewpoint objects with a separate always-on-top viewer, 3D models, scenario/progressive reveal logic.
- Parcel100: source profiles, field-profile save/load, GPS-driven cell loading. (Resume validation and batch splitting shipped in 1.5.)
- Batch Factory: accept Master 4 TXT rows as they are and use their file names (needs Jim's OK and an ArcGIS Pro 3.7 build/test on his PC).
- PointLayer: non-hydrant tests, more symbols, better LOD suggestions.
- Master 4 "55-44" radio shorthand concept (untested).
- Classroom multi-joystick selector.

---

## 6. Open items

- **PRAVE (Jim: "addressed later"):** radio field test of tracker v1.1/v1.2 (only startup confirmed); then a PDF of `docs/PRAVE_ME_TRACKER.md`; a screenshot for the PRAVE/RMC tester on the Chartplotting page.
- **Camera picture-in-picture idea (Jim, 2026-11-01, not approved to build):** a separate always-on-top Windows viewer opened by clicking a camera object. First tests: does an `earthpip:` custom-scheme link in a KML popup reach Windows; are the chosen cameras refreshing JPEGs or live video. See `tools/ARCGIS_EARTH_API.md`.
- **Objects video** coming from Jim; when it exists, it may replace `5Wn14qlC7n4` on the Object Factory picture (ask).
- **Parked (Jim's call, 2026-10-31):** Batch Factory findings (code read only) - Cancel ignores the 2-minute settle, duplicate labels caught late, closing the window mid-batch. Raise again only if Jim asks. (Extent Tool findings are moot: tool retired.)
- `legacy/Earth_Beacon_v1.0/README_original.md` in Object Factory has three relative links that broke when it moved into `legacy/`. Left alone as a preserved original.
- **Branches:** all seven repos have only `main` (checked 2026-11-01).

---

## 7. Session log

- **2026-10-31 (first Claude session):** cloned the seven repos, read every continuity file, created this file. Documentation errors pass on five repos. Code hardening began, one release per tool after Jim's live test: **mb2tpkx v1.1**, **Master 4 v3.1**, **PRAVE/ME Tracker v1.1 + v1.2** (PRAVE/RMC Tester v1.0 Gold published unmodified), **EarthStick 1.1**, **Object Factory v1.1** (Beacon Maker retired as a separate download). Extent Tool and Batch Factory findings parked.
- **2026-11-01:**
  - **PointLayer 1.4** and **Parcel100 1.5** released after Jim's live tests (Parcel100 1.5 = Jim's discovery/chooser + discovery fixes A-C + build fixes 1-4; workflow switched to the v1.5 zip). Hardening pass complete on all seven repos except parked items.
  - **Page standardization** ("link, link, pic", section 2a) on all seven pages, plus the Chartplotting site. **TPKX Extent Tool v2 retired** (Jim: conflicts with Master 4). Corrupt files found and removed with Jim's OK: MBTiles (Cell 55 JPG + 4 WebP), Point-Maps (3 assets), Parcel100 (1 SVG). Unlocked front page rebuilt (download gallery, 6 project-page links, trimmed explanation).
  - **User manual audit:** every manual checked against current code and corrected; PDFs regenerated from Markdown for Parcel100, PointLayer (was corrupt), Object Factory (v1.1 PDF replaces corrupt v1.0), EarthStick, mb2tpkx (new `MB2TPKX_USER_MANUAL.md`), Master 4, and the Batch Factory (new PDF; install section confirmed by Jim). Chartplotting site manual links now open GitHub blob pages. `tools/md2pdf.py` and `tools/linkcheck.py` added to this repo.
  - Jim deleted all leftover test branches.
