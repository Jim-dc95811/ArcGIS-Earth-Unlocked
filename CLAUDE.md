# CLAUDE.md - Continuity for Claude

**Written by Claude, for Claude.** Read this first after any session reset. It is the fastest way to get fully caught up on Jim's ArcGIS Earth Unlocked project family and how to work with him.

**Last updated:** 2026-10-31

Update this file whenever something durable changes: a release, an accepted test, a new rule, a decision, an open item opened or closed. Keep it current rather than long. History belongs in the session log at the bottom, kept short.

---

## 1. Resume procedure

1. Clone all seven public repos (list in section 3) into one working folder.
2. To push, each repo must be attached to the session with write access first (`add_repo` with `access: push`). Without that, the git proxy returns 403 even though `list_repos` shows `can_push: true`.
3. Read this file, then the repo-specific continuity file for whatever repo the task touches (section 3 says where each one lives).
4. Before editing, `git fetch` and check that nothing new landed upstream. Jim edits on GitHub directly and often.
5. Check section 6 (open items) before proposing new work.

The older continuity files in each repo were written by ChatGPT for ChatGPT. They are still valuable and mostly accurate, but some are dated snapshots. Where they conflict with this file, this file is newer; where they conflict with the live repo, the live repo wins.

---

## 2. Owner and working rules

- **Owner:** Jim Gaddy, GitHub `Jim-dc95811`. Public-safety / fire-service background, decades of hands-on computer and electronics work. Not a traditional programmer; a relentless tester who trusts measured behavior over theory.
- **Mission:** "Create new map makers." "Do not make the user learn GIS before they can use geography."
- **Primary environment:** Windows 11, Python 3.14.x, ArcGIS Earth desktop (Automation API at `http://localhost:8000`), ArcGIS Earth Mobile on Android, QGIS. All tools are Windows/Python with `.bat` launchers.

**Minimal Build Rule (non-negotiable):**
- Implement only what was asked. No unrequested cleanup, refactors or "improvements".
- One functional change at a time, discussed first.
- Every code change gets a new version number.
- Preserve filenames, paths, constants and known-good behavior unless the change specifically requires otherwise.
- Nothing is "accepted" until Jim live-tests it in ArcGIS Earth.
- Keep **verified**, **owner-observed**, **inferred** and **conceptual** clearly separate. "Unknown" beats pretending.
- No new dependencies unless they solve a demonstrated need.

Documentation fixes (broken links, stale versions, typos) are fine when Jim asks for an errors pass. Code, release zips and PDFs are not touched without explicit direction.

**Code-hardening workflow (agreed 2026-10-31):** go page by page in the order of the umbrella README. For each script: review and test here, report findings ranked by importance, change nothing until Jim approves. Jim chose to bundle approved fixes for one script into a single release (e.g. mb2tpkx v1.1) rather than one version per fix. Build in a dev folder, test here (including a byte-for-byte regression against the current version where output files exist), then hand off for Jim's live Windows/ArcGIS Earth test. Post to main only after he accepts.

**Delivering test builds:** the chat app's file cards do not work for Jim with `.bat` or `.zip` files. Push the test zip to a separate branch (`<tool>-v<ver>-test`, under `test-builds/`) and give him the GitHub raw link plus the file-page link. This sandbox cannot reach raw.githubusercontent.com, so verify by comparing the branch blob with `git show`, not by downloading. The session's git proxy also refuses branch deletion, so ask Jim to delete finished test branches on GitHub (Branches page).

Note on terms: MBTiles cannot be opened in ArcGIS Earth; only the converted TPKX can.

---

## 3. The seven repos

| Repo | Role | Current version | Continuity file |
|---|---|---|---|
| `ArcGIS-Earth-Unlocked` | Umbrella front door / system map | - | this file |
| `QGIS-Mbtile-to-ArcGIS-Earth-TPKX` | Foundation maps: MBTiles -> TPKX converter + Master 4 Grid Maker | mb2tpkx v1.1 (protected baseline), Master 4 v3.1 | `CONTINUITY.md` (snapshot 2026-10-10) |
| `ArcGIS-Earth-Offline-Maps-Chartplotting` | Earlier ArcGIS Pro TPKX route, mobile offline, chartplotting, PRAVE/ME tracker | Batch Factory v1 (Extent Tool v2 retired 2026-11-01), PRAVE/ME Tracker v1.2, PRAVE/RMC Tester v1.0 Gold | none (README + `docs/`) |
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

**EarthStick 1.0**
- Thrustmaster TCA Sidestick Airbus Edition (Windows name `T.A320 Pilot`), WinMM/ctypes, standard library only.
- Neutral controls = hover. Button 4 (red) zoom in/descend, Button 3 (black) zoom out/climb, all other buttons unassigned.
- **1.1 released 2026-10-31** (hardening; flying identical to 1.0): waits for the joystick at startup, proxy-free localhost API opener, startup wait prints reason, single post-error prompt. `releases/EarthStick_v1.1.zip` SHA-256 `505295a68e041bec7ae921f2c71b5240816946a8d5bb5f48459f3b237819c52e`; `EarthStick.py` `84894c2f2d6c857ba71b2153126cb274254e3dbf23099ca1b821dbc2ca7400c7`. `releases/EarthStick_v1.0.zip` (`8b399d70...`) kept for existing links; README presents only 1.1. Change doc `docs/EARTHSTICK_V1.1_CHANGES.md`. Constants and recovery behavior are locked; see its `CONTINUITY.md`.
- Test rig: `es_rig.py` pattern - load EarthStick.py via exec into a module, replace `WinJoystick` with a scripted class, `time` with a sleep-driven fake clock, `os.name` with 'nt', and point `CAMERA_URL` at a local mock camera API; compare the PUT stream between versions.

**Object Factory 1.0**
- v1.0 = accepted v0.2.2 TEST build, promoted with only three text changes (version string, one error message, startup status). v1.0 source SHA-256 `e77e1866e7a87b9824ed6bb1cd0f830f52adb1a2872efe48ede13a581018aa00`, which exists only in commit `b65a54c`; Jim removed the loose file from the repo root on 10/30.
- **v1.1 released 2026-10-31** (hardening; outputs identical to v1.0): `releases/ArcGIS_Earth_Object_Factory_v1.1.zip` (folder `Object_Factory_v1.1/`, SHA-256 `927ed4bf...`), source `source/Object_Factory_v1.1.py` (`f94a2034a9e3348d81a2a2061619201fd795d36930c2b64797ebb2611f5b6b70`), change doc `docs/OBJECT_FACTORY_V1.1_CHANGES.md`. v0.2.2 TEST zip removed from current files. Jim accepted on live proof (POF screenshot); he considers working output sufficient and did not run `--selftest` - don't keep pressing for it. Clipboard from Google Maps right-click is THE coordinate method; never reintroduce ArcGIS Earth camera pickup.
- 11 presets: object, helicopter, fuel, bird, hazard, home, staging, water, firetruck, camera, medical. PNGs normalized to 256 px or less on a working copy; originals never modified. Labels off by default; Info or No Popup.
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
- Test rig used here: Gold tester -> pty -> tracker -> mock Automation API (GET/PUT camera, POST/DELETE drawings). pyserial is not pip-installable in this sandbox; clone github.com/pyserial/pyserial tag v3.5 and use PYTHONPATH.

**Parcel100 1.5**
- Standard library only. Florida source: `services5.arcgis.com/GcvM6vDlR2gM4x31/.../FL_Parcels/FeatureServer/0`. Recommended fields: OWN_NAME, PHY_ADDR1, PHY_CITY, PHY_ZIPCD, PARCEL_ID, Acres.
- Output `W082W081N031N030-004-Parcels.geojson`. Since 1.5: `.partial` writes; resume skips an existing cell only if it loads as a FeatureCollection, otherwise rebuilds it. Per-parcel completeness check (OID field requested, not written; missing re-asked once; write and warn). Timed-out batches split in half. Accepts service roots with a polygon-layer chooser.
- A GitHub Actions workflow rebuilds `downloads/Parcel100_v1.5.zip` (changed from v1.4 at the 1.5 release) whenever `Parcel100.py`, `Parcel100.bat` or `PACKAGE_README.txt` change on main. README/doc edits do not trigger it. The bot zip's own SHA changes every rebuild (timestamps); check the `.py` inside instead. Bump the workflow's file name at every version change.
- The root `Parcel100_User_Manual.pdf` is an older release; `USER_MANUAL.md` is current.

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
- Parcel100: source profiles, field-profile save/load, resume validation, adaptive batch size, GPS-driven cell loading.
- PointLayer: non-hydrant tests, more symbols, better LOD suggestions.
- Master 4 "55-44" radio shorthand concept (untested).
- Classroom multi-joystick selector.

---

## 6. Open items

- **Test branch `master4-v3.1-test`** in QGIS-Mbtile-to-ArcGIS-Earth-TPKX is obsolete; Jim to delete it on GitHub.
- **Test branch `earthstick-v1.1-test`** in EarthStick is obsolete; Jim to delete it (also old `earthstick-v0.6..0.9-test` branches predate this work).
- **PRAVE/ME Tracker: radio field test still pending** for v1.1/v1.2 behavior (Jim confirmed startup only). v1.2 released 2026-10-31 (proxy bypass only); change doc `docs/PRAVE_ME_TRACKER_V1.1_CHANGES.md` now covers v1.1 + v1.2.
- **Parked (Jim's call, 2026-10-31):** ~~Extent Tool v2 findings~~ (moot: Extent Tool retired 2026-11-01) - stale SAVE/COPY after HOME edit, silent save failure under pythonw, launcher needs python.exe on PATH, clipboard timeout dumps script, window too big for small screens. Batch Factory findings (code read only; needs ArcGIS Pro 3.7 SDK to build) - Cancel ignores 2-min settle, duplicate labels caught late, closing window mid-batch. Raise again only if Jim asks.
- **Test branch `object-factory-v1.1-test`** (also holds the dropped Beacon Maker 1.1 zip) is obsolete; Jim to delete it, plus the older Object Factory branches (`github-finalize`, `ignore-me`, `release-object-factory-v1*`).
- **Beacon Maker retired as a separate download (2026-10-31, Jim's decision).** Download button, README links and `releases/Beacon_Maker_v1.0.zip` removed (zip stays in git history); `legacy/Earth_Beacon_v1.0/` kept as the historical record; README: 'Earth Beacon started this project; its beacon is now the Beacon tab.' The factory beacon matches Beacon Maker's apart from whitespace inside <coordinates>. Beacon Maker 1.1 dropped (never published; its test zip sits on the `object-factory-v1.1-test` branch only).
- **Test branches `parcel100-v1.5-test` and `parcel100-v1.5-hardened-test`** in Parcel100 are obsolete after the 1.5 release; Jim to delete them.

- ~~Object Factory v1.0 package~~ resolved by v1.1 (2026-10-31). Old note: the v1.0 download is the v0.2.2 TEST zip, which shows "0.2.2 TEST" in the app and contains two `__pycache__` files, while the v1.0 manual/PDF describe `Object_Factory_v1.0.py`. Offered to build `ArcGIS_Earth_Object_Factory_v1.0.zip` from the exact `b65a54c` source (no cache files) and repoint docs. Jim said we'll come back to this page. Needs his live test before it's called accepted.
- `legacy/Earth_Beacon_v1.0/README_original.md` in Object Factory has three relative links that broke when it moved into `legacy/`. Left alone as a preserved original.

---

## 7. Session log

- **2026-10-31:** First Claude session. Cloned all seven repos and read every continuity file. Documentation errors pass, pushed to five repos (docs only, no code or packages):
  - Unlocked: removed stray `</tr></table>`.
  - Object Factory: fixed truncated intro sentence, broken v1.0 source link (now pinned to `b65a54c`), CONTINUITY/MAPWORLD links (now `internal/`), guide download link, self-test script name; added a superseded-items note to `internal/CONTINUITY.md`; updated repo name in `MAPWORLD.md`.
  - Parcel100: fixed misplaced value in field-results table, "above"/"below" reference, listed `docs/` PDF, SECURITY.md version 1.1 -> 1.4.
  - Point-Maps: updated project-family section of `CONTINUITY.md`.
  - MBTiles: `ARCGIS_EARTH_UNLOCKED.md` links moved off the old Earth-Beacon repo.
  - EarthStick and Chartplotting needed no changes. Created this file.
  - Started code hardening. **mb2tpkx v1.1 released** after Jim's live ArcGIS Earth acceptance (Bryceville 7-layer TPKX opened correctly). 27/27 synthetic tests; Bryceville real-data output byte-identical to v1.0 apart from the random GUID. Added `MB2TPKX_V1.1_CHANGES.md`; updated checksums. The `#`/`%` name fix is verified here only, not yet live on Windows.
  - **2026-11-01:** Page standardization started (Jim: YouTube visitors with no GitHub experience; classic web presentation). Chartplotting first: user-manual link under each download (tester PDF copied to `docs/`). **TPKX Extent Tool v2 retired** (Jim: conflicts with Master 4): zip + guide removed (Git history), README/index.html/WORKFLOW/BATCH_FACTORY point to Master 4 Grid Maker. FINDING (code read only): Batch Factory's ExtentRegex rejects Master 4 TXT rows because of the trailing `.tpkx` name; docs tell users to delete it; a Factory fix needs Jim's OK + Pro SDK build. Jim approved the pattern ("Link, link, pic"): **PAGE STANDARD for every repo = download link, then 📖 User manual link, then one line, then screenshot (clickable to the YouTube video where one exists)**, same on README and on the GitHub Pages site if the repo has one. Screenshots: crop to the app/window (Jim's PNGs are 3840x2160; display coords x1.92), save to `images/`, ~1400 px wide; preview the site with Playwright at 1280 and 390 px. Chartplotting done for Batch Factory and Tracker; tester screenshot pending from Jim. Site manual links point at `docs/*.md` - check they work on github.io.
  - **2026-11-01:** **Parcel100 1.5 released** after Jim's live test ("confirmed working well"): his discovery/chooser + discovery fixes A-C + build fixes 1-4. `.py` `ba0627bc...`; 100 cells byte-identical to 1.4; change doc `docs/PARCEL100_V1.5_CHANGES.md`. Workflow switched to v1.5 zip (bot commit `4afb643`); v1.4 zip kept. All seven repos' hardening passes done except parked items.
  - **2026-11-01:** **PointLayer 1.4 released** after Jim's live test (all works good); Jim deleted the test branch.
  - **Object Factory v1.1 released** (clipboard N/S/E/W + DMS readback, overwrite prompt, safe writes, batch fixes, clean package); **Beacon Maker retired** as a separate download.
  - **EarthStick 1.1 released** after Jim's live flight test (startup joystick wait, proxy bypass, wait reason, single prompt; 335 scripted camera writes identical to 1.0). **Tracker v1.2 released** (proxy bypass only).
  - **PRAVE/ME Tracker v1.1 released** (launchers fixed, units kept through reconnect, pyserial/icon/no-fix/API logging fixes) and **PRAVE/RMC Tester v1.0 Gold added** with a bench-testing guide section. Extent Tool and Batch Factory findings parked by Jim.
  - **Master 4 Grid Maker v3.1 released** after Jim's live acceptance (grid TIF, Cell 55 demo and TXT checked in ArcGIS Earth/Notepad). 42/42 tests; TXT+TIF byte-identical to v3. Locked-TIF message and re-prompt verified here only. Added `MASTER4_V3.1_CHANGES.md`; updated checksums in README, MASTER4_GRID_MAKER.md, TECHNICAL.md, CONTINUITY.md, 00_USER_MANUALS.md.
