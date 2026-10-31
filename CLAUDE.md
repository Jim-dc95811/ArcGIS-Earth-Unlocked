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

---

## 3. The seven repos

| Repo | Role | Current version | Continuity file |
|---|---|---|---|
| `ArcGIS-Earth-Unlocked` | Umbrella front door / system map | - | this file |
| `QGIS-Mbtile-to-ArcGIS-Earth-TPKX` | Foundation maps: MBTiles -> TPKX converter + Master 4 Grid Maker | mb2tpkx (protected baseline), Master 4 v3 | `CONTINUITY.md` (snapshot 2026-10-10) |
| `ArcGIS-Earth-Offline-Maps-Chartplotting` | Earlier ArcGIS Pro TPKX route, mobile offline, chartplotting, PRAVE/ME tracker | Extent Tool v2, Batch Factory v1, PRAVE/ME Tracker v1 | none (README + `docs/`) |
| `EarthStick` | Joystick flight of the ArcGIS Earth camera | 1.0 (protected baseline) | `CONTINUITY.md` |
| `ArcGIS-Earth-Object-Factory` | Geographic object authoring: Objects, Batch, Sky Compass, Beacon | 1.0 (commissioned 2026-10-29) | `internal/CONTINUITY.md` + `internal/MAPWORLD.md` |
| `Point-Maps` | PointLayer: public ArcGIS point service -> offline KMZ/GeoJSON | 1.3 | `CONTINUITY.md` |
| `Parcel100` | Master 4 box -> up to 100 parcel GeoJSON cells | 1.4 | `CONTINUITY.md` |

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
- `mb2tpkx.py`: 256x256 PNG/JPEG Web Mercator raster MBTiles -> Esri Compact Cache V2 TPKX, bytes copied unchanged, TMS rows flipped to XYZ. Needs Pillow. Does not download imagery or build missing zooms. Baseline SHA-256 values are in its `CONTINUITY.md`; do not change without explicit authorization.
- Field-proven in ArcGIS Earth at 4 GB, 20+ GB and 40 GB-class packages.
- **Master 4:** one whole-degree box entered as `west, east, south, north` (e.g. `82w, 81w, 30n, 31n`), split into 100 cells of 0.1 degrees. Cell number = (first decimal of |lat|) x 10 + (first decimal of |lon|) + 1, so `30.56N 81.34W` is cell 54. Outputs: `Master4_<box>_Extents.txt` (100 rows + `MASTER` row, EPSG:3857) and `Master4_<box>_Grid.tif`. Optional Cell 55 Z10-Z20 synthetic demo TPKX, default No.
- Filename pattern: `W082W081N031N030-055-GHY-Z20.tpkx`. This numbering and naming is shared infrastructure (Parcel100 uses it). Do not change it casually.
- **Operation Map Florida:** statewide enhanced Z17 overview packages (seven-layer FFS-style recipe). Rule: "Measure three times, form once" - do not build the statewide numbered index until all Z17 extents are locked.
- Android: ~2 GB Z17 TPKX is the practical ceiling; copy from SD card to internal storage before opening.

**EarthStick 1.0**
- Thrustmaster TCA Sidestick Airbus Edition (Windows name `T.A320 Pilot`), WinMM/ctypes, standard library only.
- Neutral controls = hover. Button 4 (red) zoom in/descend, Button 3 (black) zoom out/climb, all other buttons unassigned.
- Release zip SHA-256 `8b399d70df582c448ed2bfdf532d5dcc17f579187f99a4d165bd06ef1cb0c292` (verified 2026-10-31). Constants and recovery behavior are locked; see its `CONTINUITY.md`.

**Object Factory 1.0**
- v1.0 = accepted v0.2.2 TEST build, promoted with only three text changes (version string, one error message, startup status). v1.0 source SHA-256 `e77e1866e7a87b9824ed6bb1cd0f830f52adb1a2872efe48ede13a581018aa00`, which exists only in commit `b65a54c`; Jim removed the loose file from the repo root on 10/30.
- The published download is still `releases/ArcGIS_Earth_Object_Factory_v0.2.2_TEST.zip` (see open items).
- 11 presets: object, helicopter, fuel, bird, hazard, home, staging, water, firetruck, camera, medical. PNGs normalized to 256 px or less on a working copy; originals never modified. Labels off by default; Info or No Popup.
- Batch format: `type|name|lat|lon|alt_m|icon|description|url|link_text|scale|altitude_mode|tether|popup|label`, with comma shorthand `type,lat,lon[,alt][,name]`.
- This repo was formerly `Earth-Beacon`. Standalone Beacon Maker v1.0 is preserved in `legacy/` and `releases/`.
- Known cosmetic issue: ArcGIS Earth's native KML popup box is larger than wanted. That is viewer behavior, not a bug in the factory.
- ChatGPT was given broad design authority over the Object Factory build. Do not assume Claude has the same authority; ask.

**PointLayer 1.3**
- Accepts a service root or layer URL, discovers point layers (Nassau hydrants are layer 458, not 0). Downloads the whole layer via `returnIdsOnly` + batches. Geometry from `outSR=4326`, never from attribute fields named Lat/Lon/X/Y.
- Accepted LODs: Nassau 3,250 features -> 12,000; Duval 30,688 -> 30,000. Starting points, not laws.
- Say "3,250 features were published and downloaded", never "the county has 3,250 hydrants".
- Multi-tier duplicate-symbol LOD was tested and rejected. Do not reintroduce without discussion.

**Parcel100 1.4**
- Standard library only. Florida source: `services5.arcgis.com/GcvM6vDlR2gM4x31/.../FL_Parcels/FeatureServer/0`. Recommended fields: OWN_NAME, PHY_ADDR1, PHY_CITY, PHY_ZIPCD, PARCEL_ID, Acres.
- Output `W082W081N031N030-004-Parcels.geojson`. Resume skips any existing expected filename without validating it.
- A GitHub Actions workflow rebuilds `downloads/Parcel100_v1.4.zip` whenever `Parcel100.py`, `Parcel100.bat` or `PACKAGE_README.txt` change on main. README/doc edits do not trigger it.
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

- **Object Factory v1.0 package (raised 2026-10-31, Jim deferred):** the v1.0 download is the v0.2.2 TEST zip, which shows "0.2.2 TEST" in the app and contains two `__pycache__` files, while the v1.0 manual/PDF describe `Object_Factory_v1.0.py`. Offered to build `ArcGIS_Earth_Object_Factory_v1.0.zip` from the exact `b65a54c` source (no cache files) and repoint docs. Jim said we'll come back to this page. Needs his live test before it's called accepted.
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
