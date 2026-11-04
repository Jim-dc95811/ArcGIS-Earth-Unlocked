# CLAUDE.md - Continuity for Claude

**Written by Claude, for Claude.** Read this first after any session reset. It is the fastest way to get fully caught up on Jim's ArcGIS Earth Unlocked project family and how to work with him.

**Last updated:** 2026-11-03 (evening)

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
- **Names decided (Jim, 2026-11-03):** family name **ArcGIS Earth Flight** (Jim's choice; he is giving the work away and wants people to find ArcGIS Earth, so "ArcGIS Earth" up front is intended - do not keep re-raising trademark concerns). Gate feature name **World Gates** (airport gates fit the ATL "connect here" hub; "portal" collides with Esri's Portal for ArcGIS and the Portal game; "portal" is fine as a word in videos). Tool names stay: EarthStick (not "Flight Stick" - generic, unsearchable), Object Factory, PointLayer, Parcel100, MBTiles converter, Master 4. **Renaming the pages/repos from "ArcGIS Earth Unlocked" to "ArcGIS Earth Flight" is NOT done yet** - separate job when Jim says go.
- **IN TEST - EarthStick 1.3.1 + World Gates (status 2026-11-03 19:20; branch EarthStick `earthstick-v1.3.1-test`, folder `test-builds/`):**
  - **EarthStick 1.3.1** = 1.3 with a larger crosshair (RETICLE_SIZE 80, RETICLE_WIDTH 5, gap 8, dot 3); dev copy `/home/claude/dev/earthstick_v1.3.1/` (sandbox only - rebuild from 1.3 if lost). **Accepted live by Jim 2026-11-03 19:23: 'the crosshair mod is great'.**
  - **Current gate pack: World Gates v14** (`World_Gates_JAX_ATL_v14.kmz`, inside `EarthStick_v1.3.1_TEST_WorldGates_v14.zip`); built by `tools/build_world_gates.py` (`GATES_VERSION`) + `tools/make_gate_kmz.py`. Older v5-v13 KMZs sit on the branch.
  - **Network:** JAX ring over JIA (1,500 ft MSL) -> ATL hub (8 rings on a 3 km circle at 2,530 ft MSL: NYC 315, London 0, Paris 45, Rome 90, JAX 135, Rio 180, Sydney 225, Tokyo 270; arrive facing 22.5) -> seven cities. **Round-the-world tour** (Jim): each city has an ATL return ring 2 km from the landmark toward ATL and a next-city ring 2 km beyond it (NYC->London->Paris->Rome->Tokyo->Sydney->Rio; Rio's onward = ATL). Arrival 1.7 km short of the landmark, facing it.
  - **City layout (v8-v14, tuned live from Jim's screenshots):** KML text is a FIXED SIZE on screen, so welcome signs, site menus and (v14) ring names sit in Region LOD folders shown within ~20,000 ft (`lod_folder`, Object Factory 1.2 calibration). Welcome sign at arrival height 1.2 km straight ahead; site menu = one row of five stars 900 m out, 100 m below (hub: 200 m), spaced by name length (~0.72 deg/char at label scale 0.9, GAP_DEG 5; sign ~1.15 deg/char at 1.4); sign + row turn sideways until clear of every ring at that city (NYC +55, London -25, Paris -35, Tokyo +20 ...). Sites: 5 per city incl. ATL and JAX (v14).
  - **SHOW ME stars (v13+):** clicking a star opens a short popup whose script immediately POSTs a coloured beacon line (3 km) + coloured ground name to `http://localhost:8000/arcgisearth/drawings`; colours red, blue, green, magenta, orange in menu order, menu name drawn in the same colour; clear by unticking under My Drawings (Jim prefers that - no buttons). Re-click does not duplicate (proven 18:44). The blue pin under the ground name stays (Jim 19:18: 'not worth the grief').
  - **ArcGIS Earth facts learned tonight:** labels draw ~80 px ABOVE their icon (vertical lists mis-pair); labels wrap onto two lines by text WIDTH (sign at 1.4: 18 chars OK, 'Welcome to New York' wraps; site at 0.9: 'Empire State Building' fits, 'Royal Botanic Garden' wraps; hyphens break: 'World of Coca-' / 'Cola'); build check enforces sign <=18 / site <=19 (`SEEN_ON_ONE_LINE` exceptions); a `no-cors` DELETE from a popup is never sent; KML `<LookAt>` and `<Camera>` are both IGNORED on double-click (zooms straight overhead).
  - **City Beacons** (`World_Gates_City_Beacons_v1.zip` / `_v2.zip`, `tools/build_city_beacons.py`): nine red beacon KMZs ('Go to Paris' ...) - double-click in the Data list to jump straight to a city, bypassing the gates; lands overhead (Jim: fine, nudge the view). v1 LookAt / v2 Camera behave the same.
  - **Queued v15 (build on Jim's go):** (1) ATL hub welcome sign lifted ~12 deg above the rings (hub rings circle you at sign height; v14 sign sat on the London ring name); (2) rename 'World of Coca-Cola' -> 'Coca-Cola Museum'; (3) remove the v14 invisible-marker attempt + fallback (back to the plain v13 label POST).
  - **NEXT SESSION (Jim, 2026-11-03 19:35):** Jim converts MBTiles and keeps exploring/testing tonight; tomorrow = final edit (v15 list + anything from his testing), then post (release).
  - **Release plan (proposed, not yet approved):** after acceptance, release EarthStick 1.3.1 with the latest gate pack in `Gates/` + City Beacons, user-manual section on touring, then Jim's World Gates tour video.
  - **City Z18 imagery (Jim, for the video):** Jim built Google Hybrid TPKX islands for the seven cities from Master 4 cells (NYC W075W074 61,62,71,72 + W074W073 70,80; London W001E000 41,42,51,52 + E000E001 41,51; Paris 83,84,93,94; Rome 85,86,95,96; Tokyo 58,67,68,69,78; Sydney 82,83,92,93; Rio S023S022 92,93 + S024S023 02,03), batched in QGIS, not following the naming protocol; ATL and JAX already heavily mapped. Idea: fly the tour with the basemap OFF so each city is a floating island (toggle on/off in the video). Local tiles = almost no render time on arrival.
  - **ArcGIS Earth Flight launcher v1.0 TEST (Jim's idea 19:25):** `ArcGIS_Earth_Flight_Launcher_v1.0_TEST.zip` on the branch (source in `tools/launcher/`): `Fly_ArcGIS_Earth.bat` (goes in the EarthStick folder; finds ArcGISEarth.exe - known paths, then `where /r`, remembered in `ArcGIS_Earth_path.txt` - starts it unless running, then calls EarthStick.bat, which waits for the API) + `Make_Taskbar_Shortcut.bat` (PowerShell makes desktop 'ArcGIS Earth Flight.lnk' = cmd /c Fly..., ArcGIS Earth icon; user pins it). **Accepted live by Jim 2026-11-03 19:32 ('worked the first time').** Measured: ArcGIS Earth installs at `C:\Program Files\ArcGIS\ArcGIS Earth\bin\ArcGISEarth.exe` (found by the `where /r` search; add it to the known-paths list in the next launcher version). Order works: EarthStick waited through 'urlopen timed out' / 'Unexpected camera response' until ArcGIS Earth connected.
  - **Ideas not built:** live webcam object per city (Jim to supply webcam links); Object Factory Gate tab; trap-door gates; TAKE ME THERE camera PUT from a popup (untested).
- **Tagline (Jim, 2026-11-01):** "Google owns the ground, but we own the space above it." Candidate for videos and pages.
- **Mission:** "Create new map makers." "Do not make the user learn GIS before they can use geography."
- **Audience and goal (Jim, 2026-11-01):** open-source sharing of this knowledge with everyone. Jim works for a state government fire department, the primary consumers of this information; the project has expanded to a general-public appeal and to the GIS community. He has met pushback from parts of the GIS community. Pages are written for YouTube visitors with no GitHub experience. A video focused on objects (Object Factory) is planned.
- **Primary environment:** Windows 11, Python 3.14.x, ArcGIS Earth desktop (Automation API at `http://localhost:8000`), ArcGIS Earth Mobile on Android, QGIS. All tools are Windows/Python with `.bat` launchers.

**Minimal Build Rule (non-negotiable):**
- Implement only what was asked. No unrequested cleanup, refactors or "improvements".
- One functional change at a time, discussed first.
- Every code change gets a new version number.
- **This includes data packs and test files (Jim, 2026-11-03):** gate packs, beacon packs and test zips carry their version in the file name and layer name (`World_Gates_JAX_ATL_v10.kmz`, `EarthStick_v1.3.1_TEST_WorldGates_v10.zip`, `World_Gates_City_Beacons_v1.zip`). Never overwrite a pushed file under the same name.
- Preserve filenames, paths, constants and known-good behavior unless the change specifically requires otherwise.
- Nothing is "accepted" until Jim live-tests it in ArcGIS Earth.
- Keep **verified**, **owner-observed**, **inferred** and **conceptual** clearly separate. "Unknown" beats pretending.
- No new dependencies unless they solve a demonstrated need.

Documentation fixes (broken links, stale versions, typos) are fine when Jim asks for an errors pass. Code and release zips are not touched without explicit direction. Manual PDFs are now generated from their Markdown (see section 2a), except Jim's own tester PDF, which stays unmodified.

**Code-hardening workflow (agreed 2026-10-31):** go page by page in the order of the umbrella README. For each script: review and test here, report findings ranked by importance, change nothing until Jim approves. Jim chose to bundle approved fixes for one script into a single release (e.g. mb2tpkx v1.1) rather than one version per fix. Build in a dev folder, test here (including a byte-for-byte regression against the current version where output files exist), then hand off for Jim's live Windows/ArcGIS Earth test. Post to main only after he accepts.

**Auto-install launchers (Jim, 2026-11-02):** any tool needing a non-standard Python library installs it from its `.bat`, never from the `.py`: find Python (`set "PYEXE=py -3"`, `where py || set PYEXE=python`, `--version` check), `%PYEXE% -c "import <mod>"`, if missing `%PYEXE% -m pip install <lib>`, re-check, else print the manual command and 'ask IT' and stop. Released as launcher-only versions: mb2tpkx v1.1.1 and Master 4 v3.1.1 (Pillow), PRAVE/ME Tracker v1.2.1 and the Gold tester's launcher (pyserial); all live-tested by Jim. EarthStick, Object Factory, PointLayer and Parcel100 need no extra libraries.

**Packaging standard (Jim, 2026-11-01):** every Python script is delivered as a zip containing the `.py` and a `.bat` launcher (CRLF; `py -3`, falling back to `python`; `pause` at the end), inside a folder named after the tool.

**Delivering test builds:** the chat app's file cards do not work for Jim with `.bat` or `.zip` files. Push the test zip to a separate branch (`<tool>-v<ver>-test`, under `test-builds/`) and give him the GitHub raw link plus the file-page link. This sandbox cannot reach raw.githubusercontent.com, so verify by comparing the branch blob with `git show`, not by downloading. The session's git proxy also refuses branch deletion, so ask Jim to delete finished test branches on GitHub (Branches page). If the stop hook demands a push before Jim's input is in, park work on a side branch, never on main.

Note on terms: MBTiles cannot be opened in ArcGIS Earth; only the converted TPKX can.

### 2a. Page and documentation standard (approved by Jim 2026-11-01)

- **"Link, link, pic":** for every tool on every page: a bold "⬇️ DOWNLOAD <TOOL> vX" heading link to the zip, then a bold "📖 User manual" link on the next line, then one plain line, then a screenshot that opens the YouTube video (caption ends "▶️ Watch the video (YouTube).") Where there is no video, the picture stands alone. Same layout on a repo's GitHub Pages site if it has one (only Chartplotting has `index.html`).
- **"Get everything you need" block (Jim, 2026-11-02):** at the top of every repo page, before the tool's download heading: numbered bold links to each outside program the tool needs (ArcGIS Earth https://www.esri.com/en-us/arcgis/products/arcgis-earth/downloads, Python 3 https://www.python.org/downloads/windows/, QGIS https://qgis.org/download/, ArcGIS Pro trial https://esri.com/en-us/arcgis/products/arcgis-pro/trial, .NET 10 SDK https://dotnet.microsoft.com/en-us/download/dotnet/10.0, Thrustmaster TCA Sidestick product page), one-line pip commands for Pillow/pyserial, then the tool heading numbered next (e.g. "### ⬇️ 4. DOWNLOAD EARTHSTICK v1.2"). Unlocked front page has one "Before you start" line (ArcGIS Earth + Python); Chartplotting `index.html` has a "What you need" line above its downloads table.
- **"First time? Three quick tips" box (Jim, 2026-11-02):** on every repo page just above the first download heading (and on the Unlocked front page under "Before you start"; Chartplotting `index.html` has it as a note above the downloads table): Extract All before running; Windows security warning (More info > Run anyway / Run, or Properties > Unblock on the zip); tick "Add python.exe to PATH".
- **"Try it in 2 minutes - no Python needed" (Jim, 2026-11-02):** Unlocked front page (above "Download the tools") and Object Factory page link four KMZ samples in Object Factory `samples/` (raw links): `SAMPLE_Live_Traffic_Camera.kmz` (the proven FL511 camera 1362 object, renamed), `SAMPLE_Beacon.kmz` (the v1.2 zip's beacon KML packed as KMZ, because raw `.kml` opens as text in browsers), `SAMPLE_Sky_Compass.kmz`, `SAMPLE_Object_Set.kmz`. Open by dragging onto the ArcGIS Earth map or the + Add data button. **Proven by Jim 2026-11-02 19:07:** GitHub page link -> download -> drag onto ArcGIS Earth -> live camera popup.
- **Screenshots** come from Jim (3840x2160 PNGs; his displayed coordinates are x1.92). Crop to the app/map, save as ~1400 px JPG (PNG for UI windows) in that repo's `images/` or `assets/`, and preview with Playwright when a site is involved (1280 and 390 px). Never use a screenshot that is already on another page without asking.
- **Videos:** MBTiles converter `C71n8TAByuE`, Master 4 `zNt-I4KgAy8`, Batch Factory `KGckjaOu0hY`, EarthStick / PointLayer / Object Factory `5Wn14qlC7n4`, Parcel100 `_hMB_TOODOQ`, PRAVE/ME Tracker `JKWJmEIBP_I`.
- **Unlocked front page** order: title, one plain sentence, quote, "The project pages" (6 numbered links), "Download the tools" (8 tools; zips via `github.com/.../raw/main/...`; pictures open the tool's page; local copies in `images/` at 1000 px), "Start with what you want to do" table (Jim: keep), "How the pieces fit", Independence, mission. PRAVE/RMC tester stays off the front page (Jim).
- **Manual PDFs** are generated from the Markdown manual with `tools/md2pdf.py` (python-markdown + Playwright Chromium; run with `GH_BASE=https://github.com/Jim-dc95811/<repo>/blob/main/ REPO_ROOT=.` from the repo root so relative links become GitHub links). Regenerate the PDF whenever its manual changes. Each manual opens with a "printable copy" link to its PDF.
- **Corruption check:** several uploads in these repos were truncated at about 15 KB. Before trusting any binary, open it (PIL / `pdfinfo` / `unzip -t`).

### 2a-1. Project timeline from Jim's YouTube channel (@dc95811, read 2026-11-01)

- **~1 year+ ago:** two-way radio / communications engineering (P25, BK, Telex, Viavi, antennas). Early mapping seeds: Google Earth Pro pre-trip cache building, vehicle tracking with Google Earth + MS Teams, Raveon GPS telemetry testing (the PRAVE ancestor).
- **Origin (Jim):** it all started with OpenCPN being able to read MBTiles made in QGIS. Jim's twist was Google imagery over land instead of nautical charts over water; the OpenCPN community was not happy about it. The MBTiles habit later became mb2tpkx (MBTiles -> TPKX for ArcGIS Earth). That work (plus NMEA decoding to get past closed chartplotters, and a compact 22-character radio position packet, "F22") led Jim to notice that the commercial tracking system his department used displayed only zoom-17 imagery; learning how multiresolution tile pyramids and zoom levels work is what drove the Z20 TPKX focus.
- **~6-5 months ago (May-June 2026):** tracking and land navigation: OpenCPN as a land chart plotter with QGIS/Google Maps/Google Earth Pro, U-blox GPS, Arduino NMEA conversion, Kenwood NX-700 GPS backhaul, multi-AVL on one plotter.
- **~4 months ago (July 2026):** location pushing (Google Maps dispatch texting tool built with AI, address push via AIS/OpenCPN). Google announced the end of Google Earth Pro downloads on July 8, 2026 (downloads stop June 25, 2027).
- **~2 months ago (Sept 2026):** the ArcGIS Earth pivot: pre-loaded satellite maps for first responders, ArcGIS Pro TPKX creation.
- **~1 month ago (Oct 2026):** TPKX production and QGIS (offline TPKX, chart plotting, QGIS + ArcGIS Pro, export DPI/zoom guide, "How to Make an Offline Map with QGIS and ArcGIS Earth", "Google Maps OFFLINE").
- **Last 3 weeks:** scale and data: large regions with QGIS (Master 4), ArcGIS Earth Mobile at Z20, Parcel100, EarthStick/flight video.
- Channel: 889 subscribers, 202 videos. Most-viewed videos are radio/tech (lightbar 1.9K, RS232 981, VHF duplexer 605); mapping videos run 27-226 views, best ones being practical how-tos with a clear result. The subscriber base came for radio; the mapping work needs a new audience (Shorts, Esri Community, fire-service outlets). Network Earth (Google Earth Pro "Earth Server in a Box", v0.2.2 test) was the Google Earth Pro-era predecessor.

### 2b. Working with Jim (observed)

- He answers tersely: "engage" = go ahead; "approve all" / "1.4 yes 1-6" = approve the listed findings; "works good" or a screenshot = live acceptance. Do not press for self-tests after that.
- Best format for decisions: findings ranked by importance, each with a plain one-line consequence, then a single recommendation. He usually picks the recommendation.
- He wants to be told when something is broken even if he did not ask (corrupt files, stale PDFs, wrong versions), then decides what to do.
- Plain words: he is not a programmer. Name buttons and files exactly; skip code detail unless asked.
- "Confirm X" means check it with a tool (e.g. `git ls-remote`, link check), not from memory.
- He edits on GitHub himself between turns: always `git pull` before editing, and re-check what you claim is there.
- Read every line of his report before acting. If he says something is not working, deal with that first (2026-11-01: "the joystick itself is not working" was missed while chasing the trigger; the cause was an old EarthStick 0.10 copy).
- No hedging or reflexive caveats (he calls it "kicking balls"). Give a clear answer; keep caution only where it actually protects him or his users.
- A screenshot with a one-line label ("screen shot showing object and crosshairs") usually means: put it on the page/manual for the thing just released.

### 2c. Sandbox facts (this cloud workspace)

- No `python3-tk`: stub Tkinter (see `tools/test-rigs/README.md`). Pillow, python-markdown, pandoc, poppler (`pdfinfo`, `pdftotext`, `pdftoppm`) and Playwright Chromium are available.
- Blocked: PyPI for some packages (pyserial: clone from GitHub instead), YouTube (thumbnails and pages), raw.githubusercontent.com. `gh run list` works; `gh api .../pages` is refused.
- GitHub Actions in Parcel100 commits a rebuilt zip after pushes to main; pull before the next edit.
- Repos must be attached with `add_repo(access: push)` before pushing; branch deletion is refused (Jim deletes branches).
- **Claude Toolbox (`tools/`, Jim's idea 2026-11-01): check `tools/README.md` before writing a helper from scratch.** It holds `linkcheck.py`, `check_binaries.py`, `md2pdf.py`, `crop_screenshot.py`, `test-rigs/`, `samples/` (the live-camera test KMZ) and `ARCGIS_EARTH_API.md` (Automation API reference: proven vs documented vs untested; read it before any API work). Add new reusable helpers there and list them in its README.

---

## 3. The seven repos

| Repo | Role | Current version | Continuity file |
|---|---|---|---|
| `ArcGIS-Earth-Unlocked` | Umbrella front door / system map | - | this file |
| `QGIS-Mbtile-to-ArcGIS-Earth-TPKX` | Foundation maps: MBTiles -> TPKX converter + Master 4 Grid Maker | mb2tpkx v1.1.1 (py = protected v1.1 baseline), Master 4 v3.1.1 (py = v3.1) | `CONTINUITY.md` (snapshot 2026-10-10, dated notes since) |
| `ArcGIS-Earth-Offline-Maps-Chartplotting` | ArcGIS Pro TPKX route (Batch Factory), mobile offline, chartplotting, PRAVE/ME tracker; GitHub Pages site `index.html` | Batch Factory v1 (Extent Tool v2 retired 2026-11-01), PRAVE/ME Tracker v1.2.1, PRAVE/RMC Tester v1.0 Gold (launcher updated 2026-11-02) | none (README + `docs/`; this file) |
| `EarthStick` | Joystick flight of the ArcGIS Earth camera | 1.3 (World Gates) | `CONTINUITY.md` |
| `ArcGIS-Earth-Object-Factory` | Geographic object authoring: Objects, Batch, Sky Compass, Beacon | 1.2 (released 2026-11-02) | `internal/CONTINUITY.md` + `internal/MAPWORLD.md` |
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
- **Seven-layer FFS-style recipe (2026-11-01):** the Esri "Boundaries & Places" raster layer started returning 403 Forbidden in QGIS (service itself is scheduled to retire Dec 2029; cause unconfirmed). Jim: the Esri vector reference layer works as its replacement, and Google Hybrid is a backup. Recipe is a continuous evolution; note layer changes with the recipe.
- **Operation Map Florida:** statewide enhanced Z17 overview packages (seven-layer FFS-style recipe). Rule: "Measure three times, form once" - do not build the statewide numbered index until all Z17 extents are locked.
- Android: ~2 GB Z17 TPKX is the practical ceiling; copy from SD card to internal storage before opening.
- Manuals: `MB2TPKX_USER_MANUAL.md` (new 2026-11-01) and `MASTER4_GRID_MAKER.md`, each with a generated PDF of the same base name as before (`mb2tpkx_User_Manual.pdf`, `Master4_Grid_Maker_User_Manual.pdf`).

**EarthStick 1.3**
- Thrustmaster TCA Sidestick Airbus Edition (Windows name `T.A320 Pilot`), WinMM/ctypes, standard library only.
- Neutral controls = hover. Button 4 (red) zoom in/descend, Button 3 (black) zoom out/climb, Button 1 (trigger) trigger-click (1.2), all other buttons unassigned.
- **1.3 released 2026-11-02 - WORLD GATES** (Jim's idea; flown live all evening): gate KMZs in a `Gates` folder beside EarthStick.py, read at startup; forward pass through a ring (gold side, within radius, while the stick moves the camera) jumps the camera to the partner (300 m past it, facing away) or a fixed spot; 2 s cooldown; partners resolved in the same file first. Ships with `Gates/World_Gates_JAX_ATL.kmz` (also `gates/` in the repo, linked from the Unlocked 'Try it in 2 minutes' list). No gates = byte-identical to 1.2. `releases/EarthStick_v1.3.zip` `0e8c394748f428eef42fed5aa1da5e5d317557082505ad4ca52e4d271ce0731f`, `EarthStick.py` `df0e48dda1da08a7439b118bb5f44d731f6c215e4e86d4f7f223fae9dbde26fe`, change doc `docs/EARTHSTICK_V1.3_CHANGES.md`, guide section 'World Gates: flying through wormholes' (PDF rebuilt), page pictures `images/world_gates_atl_hub_arcgis_earth.jpg` + `world_gates_paris_ring_arcgis_earth.jpg`.
- **1.2 released 2026-11-01** (trigger-click; flying byte-identical to 1.1): click-through red crosshair centred on the ArcGIS Earth window; trigger glides the Windows pointer there and clicks (opens a popup; on open map, closes it); 0.8 s lockout; fails safe if Tk is missing. Button 2 = Esc close (TEST2) did not work for Jim and was dropped. `releases/EarthStick_v1.2.zip` (folder `EarthStick_v1.2/`) SHA-256 `ad114b6197037f8851db459b244f98befee70066b458369ea993b0dcd6f224a5`; `EarthStick.py` `63dd9b55af8aa8273dee212ed2da41ea73395752da898b8a09877d6f9bbefe5a`. v1.0 and v1.1 zips kept. Change doc `docs/EARTHSTICK_V1.2_CHANGES.md`.
- **1.1 released 2026-10-31** (hardening; flying identical to 1.0): waits for the joystick at startup, proxy-free localhost API opener, startup wait prints reason, single post-error prompt. `releases/EarthStick_v1.1.zip` SHA-256 `505295a68e041bec7ae921f2c71b5240816946a8d5bb5f48459f3b237819c52e`; `EarthStick.py` `84894c2f2d6c857ba71b2153126cb274254e3dbf23099ca1b821dbc2ca7400c7`. `releases/EarthStick_v1.0.zip` (`8b399d70...`) kept for existing links. Change doc `docs/EARTHSTICK_V1.1_CHANGES.md`. Constants and recovery behavior are locked; see its `CONTINUITY.md`.
- Test rig: `es_rig.py` pattern - load EarthStick.py via exec into a module, replace `WinJoystick` with a scripted class, `time` with a sleep-driven fake clock, `os.name` with 'nt', and point `CAMERA_URL` at a local mock camera API; compare the PUT stream between versions.

**Object Factory 1.2**
- v1.0 = accepted v0.2.2 TEST build, promoted with only three text changes (version string, one error message, startup status). v1.0 source SHA-256 `e77e1866e7a87b9824ed6bb1cd0f830f52adb1a2872efe48ede13a581018aa00`, which exists only in commit `b65a54c`; Jim removed the loose file from the repo root on 10/30.
- **v1.1 released 2026-10-31** (hardening; outputs identical to v1.0): `releases/ArcGIS_Earth_Object_Factory_v1.1.zip` (folder `Object_Factory_v1.1/`, SHA-256 `927ed4bf...`), source `source/Object_Factory_v1.1.py` (`f94a2034a9e3348d81a2a2061619201fd795d36930c2b64797ebb2611f5b6b70`), change doc `docs/OBJECT_FACTORY_V1.1_CHANGES.md`. v0.2.2 TEST zip removed from current files. Jim accepted on live proof (POF screenshot); he considers working output sufficient and did not run `--selftest` - don't keep pressing for it. Clipboard from Google Maps right-click is THE coordinate method; never reintroduce ArcGIS Earth camera pickup.
- **v1.2 released 2026-11-02** (Jim's request; accepted live on TEST3, "target acquired"): **Hide above (ft)** on the Objects tab + optional batch column `hide_above_ft`. Each object (+ tether) goes in a `<Folder>` with a KML Region: a 300 m CUBE (LatLonAltBox with minAltitude/maxAltitude, centred on the object) and `minLodPixels = LOD_FT_PX / feet`, `LOD_FT_PX = 1,790,000`. Calibrated on Jim's screen: altitude x minLodPixels was constant (1.44-2.38 million ft*px for the 0.003-degree test box); 40,000 ft check passed. A FLAT box vanishes edge-on at low altitude; the cube stays visible sideways (to ~1.35x the setting). Objects tab altitude now in feet (presets rounded to 10 ft); batch `alt_m` stays metres. Popup Info with empty text and URL now shows the name (v1.1 wrote nothing, so a click only selected the object). Header/rows tightened so CREATE OBJECT KMZ fits on Jim's maximised window. `releases/ArcGIS_Earth_Object_Factory_v1.2.zip` `531d4e0e54e38a0608052ba4140c51534101e40a16d75af6842532701c2fe1c4`, `source/Object_Factory_v1.2.py` `1310743e2f129d70dd85291efe1922c2f275bedbb9a91f45759d5925b4640ff9`, change doc `docs/OBJECT_FACTORY_V1.2_CHANGES.md`, manual PDF `docs/ArcGIS_Earth_Object_Factory_v1.2_User_Manual.pdf` (v1.1 PDF removed; v1.1 zip + source kept). Rig: `tools/test-rigs/object_factory_test_v12.py` (32 checks). ArcGIS Earth status bar shows **eye alt in feet**.
- 11 presets: object, helicopter, fuel, bird, hazard, home, staging, water, firetruck, camera, medical. PNGs normalized to 256 px or less on a working copy; originals never modified. Labels off by default; popup Info or None. Batch aliases: pin, heli, gas, gas_pump, warning, base, truck, viewpoint, hospital; unknown type -> object. Default outputs on the Desktop.
- Batch format: `type|name|lat|lon|alt_m|icon|description|url|link_text|scale|altitude_mode|tether|popup|label|hide_above_ft` (last column optional, v1.2), with comma shorthand `type,lat,lon[,alt][,name]`.
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
- **Jim's position (2026-11-01):** he cannot control what others do with these ideas; the imagery and overlay sources users choose are between them and those providers. His work is public, non-commercial and for public safety. Keep the existing practice (tools not data, link to sources rather than re-host, credit them, the repos' 'users are responsible for source terms' wording) and do not keep re-raising terms of use; mention a specific term only if it is concrete and directly relevant.
- Generated artwork in the repos is illustrative, not authoritative geometry.

---

## 5. Pending ideas (not approved for building)

From the older continuity files. None of these is approved just by appearing here:
- Clipboard -> QR -> email pin-drop utility (verify ArcGIS Earth app-link syntax first).
- Object Factory: live camera objects (popup picture + refresh script, proven; see section 6), a separate always-on-top viewer, 3D models, scenario/progressive reveal logic.
- Outreach: YouTube Shorts recorded from ArcGIS Earth at its 1200x2000 minimum window (close to 9:16); recreation direction to grow popularity (Jim leaning that way).
- Parcel100: source profiles, field-profile save/load, GPS-driven cell loading. (Resume validation and batch splitting shipped in 1.5.)
- Batch Factory: accept Master 4 TXT rows as they are and use their file names (needs Jim's OK and an ArcGIS Pro 3.7 build/test on his PC).
- PointLayer: non-hydrant tests, more symbols, better LOD suggestions.
- Master 4 "55-44" radio shorthand concept (untested).
- Classroom multi-joystick selector.

---

## 6. Open items

- **PRAVE (Jim: "addressed later"):** radio field test of tracker v1.1/v1.2 (only startup confirmed); then a PDF of `docs/PRAVE_ME_TRACKER.md`; a screenshot for the PRAVE/RMC tester on the Chartplotting page.
- **NEXT WHEN JIM RETURNS - live camera objects:** Jim to choose between (a) a camera field in the Object Factory (paste the FL511 picture link; popup gets the live, refreshing picture) and (b) a camera-pack maker (camera numbers + coordinates -> one KMZ). Either is a new feature and a new version. The proven test KMZ is saved at `tools/samples/TEST_Camera_SR200_W_of_I95.kmz` (its branch is deleted). Open question for camera objects: altitude and tether (Claude suggested no tether, about 60-80 m; Jim undecided). Trigger-click (EarthStick 1.2) now opens these popups from the joystick.
- **Camera picture-in-picture idea (Jim, 2026-11-01, not approved to build):** a separate always-on-top Windows viewer opened by clicking a camera object. PROVEN by Jim: the ArcGIS Earth popup is a built-in browser - an fl511.com link opened the live site inside the popup (back/forward, pin). `earthpip:` link with no handler registered: "couldn't be opened" (inconclusive). PROVEN: a camera object whose popup has `<img src=https://fl511.com/map/Cctv/1362>` + a 10-second refresh script shows the live camera and updates by itself (popup runs JavaScript). Test KMZ saved at `tools/samples/TEST_Camera_SR200_W_of_I95.kmz`. Building it into a tool (e.g. Object Factory camera field or a camera-pack maker) is a new feature: needs Jim's approval and a new version. See `tools/ARCGIS_EARTH_API.md`.
- **EarthStick 1.2 RELEASED 2026-11-01** (trigger-click; see section 3). Page and manual carry Jim's crosshair + camera-object screenshot (`images/earthstick_trigger_click_crosshair.jpg`). Optional next picture: the same view with the info box open (before/after). The simulated-click recipe is in `tools/ARCGIS_EARTH_API.md`.
- **WORMHOLES / WORLD GATES - RELEASED as EarthStick 1.3, 2026-11-02 (history below). FIRST LIVE JUMP 2026-11-02 19:41 (Jim: "GIS history").** Next ideas: names (Jim wants real thought, avoid movie trademarks), Object Factory Gate tab (simple gate maker), one-way trap doors for games, more hubs. Jim's idea: golden rings; fly through the NYC ring over downtown Jacksonville (30.3227,-81.6557, centre 457 m absolute, radius 150 m, facing 28.7) and arrive 300 m past the JAX ring over the Statue of Liberty (40.6892,-74.0445, facing 213.2), heading away from it. Gates are KMZ files in a `Gates` folder beside EarthStick.py (ExtendedData `gate=1, lat, lon, alt_m, radius_m, facing, to` or one-way `dest_lat/lon/alt_m/heading`); forward crossings only, 2 s cooldown, only while the stick moves the camera; no Gates folder = byte-identical to 1.2 (335-PUT replay). Maker: `tools/make_gate_kmz.py`; rig: `tools/test-rigs/earthstick_rig_wormhole.py`. ArcGIS Earth API cannot report layer visibility, so the Gates folder is the on/off switch. **Next build (Jim):** back side of each ring red (second ring a few metres behind the gold one); then one-way "trap door" gates for games; later an Object Factory Gate tab. Also asked Jim: is 300 m past the return ring the right arrival spot? Prior-art search (twice): no public fly-through portal in any real GIS globe found. **World Gates (Jim, 2026-11-02 evening):** JAX (ring over JIA) -> ATL hub over Hartsfield-Jackson ("connect in Atlanta, like real life") -> NYC/London/Paris/Rome/Tokyo/Sydney/Rio landmarks, each with an ATL return ring; built by `tools/build_world_gates.py`, all gates one-way with explicit landing spots. Flown live: JAX->ATL, ATL->London (via a mislabelled ring: labels sat one floor up - fixed in v2), London->ATL, ATL->Rio. **Measured:** ArcGIS Earth "eye alt" is height above SEA LEVEL (Jim crossed the London ring at eye alt ~3,570 ft = ring centre 3,726 ft MSL, not 2,700 AGL; arrived at 1,499 ft). EarthStick 1.3 TEST2 (`EarthStick_v1.3_TEST2.zip`, py `df0e48dd...`): partners looked up in their own file first (two gate files can reuse NYC/JAX); console lists plain names. World Gates v2: 450 m rings, floors 2,000 ft apart, hub radius 1,200 m, label beside its own ring at centre height + smaller white "eye alt N ft" line, red back rings. **Naming:** Jim wants to put real thought into the names (avoid movie trademarks like Stargate); DECIDED 2026-11-03: World Gates (see section 2). **v3/v4 (Jim):** ATL hub = eight equal-height gates evenly around the airport (v4: 3 km circle, all eye alt 2,530 ft), stand in the middle, turn and pick; slots NYC 315, London 0, Paris 45, Rome 90, JAX 135, Rio 180, Sydney 225, Tokyo 270 (a world map wrapped around you; true bearings for NYC/London/Paris/Rome are all ~45-51 so true placement is impossible); arrival heading 22.5 (between gates). Labels: name beside its own ring at centre height + white altitude line "2,530 ft" 130 m below (the "eye alt ..." text wrapped in ArcGIS Earth). Flown live on v4: ATL->Paris, ATL->Tokyo (v3) - Jim: "magnifique". Current gate file: `World_Gates_JAX_ATL_v4.kmz` on branch `earthstick-v1.3-test`.
- **Objects video** coming from Jim; when it exists, it may replace `5Wn14qlC7n4` on the Object Factory picture (ask).
- **Parked (Jim's call, 2026-10-31):** Batch Factory findings (code read only) - Cancel ignores the 2-minute settle, duplicate labels caught late, closing the window mid-batch. Raise again only if Jim asks. (Extent Tool findings are moot: tool retired.)
- `legacy/Earth_Beacon_v1.0/README_original.md` in Object Factory has three relative links that broke when it moved into `legacy/`. Left alone as a preserved original.
- **Branches to delete (Jim):** EarthStick `earthstick-v1.3-test`, Object Factory `wormhole-test` (both finished); later `earthstick-v1.3.1-test` once 1.3.1 is released.

---

## 7. Session log

- **2026-10-31 (first Claude session):** cloned the seven repos, read every continuity file, created this file. Documentation errors pass on five repos. Code hardening began, one release per tool after Jim's live test: **mb2tpkx v1.1**, **Master 4 v3.1**, **PRAVE/ME Tracker v1.1 + v1.2** (PRAVE/RMC Tester v1.0 Gold published unmodified), **EarthStick 1.1**, **Object Factory v1.1** (Beacon Maker retired as a separate download). Extent Tool and Batch Factory findings parked.
- **2026-11-01:**
  - **PointLayer 1.4** and **Parcel100 1.5** released after Jim's live tests (Parcel100 1.5 = Jim's discovery/chooser + discovery fixes A-C + build fixes 1-4; workflow switched to the v1.5 zip). Hardening pass complete on all seven repos except parked items.
  - **Page standardization** ("link, link, pic", section 2a) on all seven pages, plus the Chartplotting site. **TPKX Extent Tool v2 retired** (Jim: conflicts with Master 4). Corrupt files found and removed with Jim's OK: MBTiles (Cell 55 JPG + 4 WebP), Point-Maps (3 assets), Parcel100 (1 SVG). Unlocked front page rebuilt (download gallery, 6 project-page links, trimmed explanation).
  - **User manual audit:** every manual checked against current code and corrected; PDFs regenerated from Markdown for Parcel100, PointLayer (was corrupt), Object Factory (v1.1 PDF replaces corrupt v1.0), EarthStick, mb2tpkx (new `MB2TPKX_USER_MANUAL.md`), Master 4, and the Batch Factory (new PDF; install section confirmed by Jim). Chartplotting site manual links now open GitHub blob pages. `tools/md2pdf.py` and `tools/linkcheck.py` added to this repo.
  - Jim deleted all leftover test branches.
  - Unlocked front page gained "The project pages" (6 links). Claude Toolbox created in `tools/` (Jim's idea). ArcGIS Earth Automation API researched into `tools/ARCGIS_EARTH_API.md`.
  - **Big finding (Jim's tests):** the ArcGIS Earth popup is a built-in web browser that runs JavaScript. A camera object over SR-200 W of I-95 (Nassau) showing FL511 camera 1362 auto-refreshed live inside ArcGIS Earth. Test KMZ now in `tools/samples/`. Jim's direction: objects in 3D space online and offline (live cameras, kids' scavenger games with beacon guides, object packs); an objects video is planned. Session paused for a few hours at Jim's request.
  - **EarthStick 1.2 released** (trigger-click, Jim's idea): test builds v0.1-v0.3 found the glide-and-rest click recipe; TEST accepted live ("works great"); TEST2's Button 2 = Esc did not work, and Jim found a trigger-click on open map closes the popup, so 1.2 = TEST. Front-page link updated; Jim's crosshair screenshot added to the page and manual (PDF rebuilt). Jim deleted all test branches; all repos are `main` only. Night break.
- **2026-11-02:** **Object Factory 1.2 released** (Hide above via KML Region cube, calibrated live from Jim's eye-alt screenshots; altitude in feet; name popup; layout). Jim also put the live FL511 camera HTML into a 1.2 object - works inside the Hide above folder. 'Get everything you need' blocks on all pages. Launcher auto-install releases (mb2tpkx v1.1.1, Master 4 v3.1.1, Tracker v1.2.1, Gold tester launcher). Jim's 5Wn14qlC7n4 video hit 125 views in 2 days (big for him); next: live-camera Short.
  - **Evening: WORLD GATES.** Jim asked about wormholes; one evening later EarthStick 1.3 shipped with the World Gates pack: first live jump JAX->NYC 19:41, then the Atlanta hub ('connect in ATL, just like real life') and flights to London, Rio, Tokyo and Paris, refined live (red backs, labels beside their own rings, eye-alt numbers, 8 gates around the airport, 3 km circle). Measured: ArcGIS Earth eye alt is from sea level. Jim: 'a $100K night for us'.
- **2026-11-03:** Names decided: family **ArcGIS Earth Flight**, feature **World Gates** (page renaming not done yet). EarthStick 1.3.1 TEST (bigger crosshair). World Gates v5-v14 in one day: round-the-world tour rings, welcome signs, live-proven popup -> Automation API beacons (SHOW ME), then a full evening of layout tuning from Jim's screenshots in every city (near-only text, menu row, name-length spacing, per-site colours, one-click beacons, short names). City Beacons for direct jumps. Jim built Z18 city imagery islands from Master 4 cells and flew the whole tour (Jim: 'it is creepy weird how real it feels ... it is fun'). New rule: data packs and test zips carry version numbers too. v15 queued.
