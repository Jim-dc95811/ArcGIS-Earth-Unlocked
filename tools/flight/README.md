# Claude's flight manual - flying ArcGIS Earth through its API

Written by Claude for the next Claude (and any person + AI team). Everything here was flown live on Jim's PC on 2026-11-07 (ArcGIS Earth 3.0.1, Dark Jacksonville loaded), with Claude in the cloud and the session linked to his computer. Eight lessons, eight clean landings, one look off the edge of the world.

## How it works

- ArcGIS Earth's Automation API on the user's PC: `GET` / `PUT http://localhost:8000/arcgisearth/camera`. Camera = `{"position": {"x": lon, "y": lat, "z": metres above SEA LEVEL, "spatialReference": {"wkid": 4326}}, "heading", "tilt", "roll"}`. Same calls as EarthStick. Open localhost without any proxy (`ProxyHandler({})`).
- Flying = sending a new camera 20 times a second. Every move is eased (`(1 - cos(pi*f))/2`): slow start, slow stop. A finished move ends in a HOVER (nothing more is sent).
- **Hands-off safety:** before each step the script GETs the camera; if it differs from what Claude last sent (heading > 2 deg, height > 5 m (15 m on fast legs), position > 2e-4 deg (1.5e-3 on fast legs)), someone touched the mouse or stick - Claude prints "Your plane" and stops.
- Every run appends to `flight_test_log.txt` beside the .bat, because Claude cannot see the command window (masked in its screenshots). Claude reads the log with `device_stage_files` after each flight.
- `add_gates()` shows a KMZ on the map with `POST /arcgisearth/layer {"URI": path, "target": "operationalLayers", "type": "KML"}` (proven).

## Running it on Jim's PC (linked session - CLAUDE.md 2c)

1. Write the new version under a NEW file name in `/mnt/user-data/outputs/cftN/` (a re-sent or edited staged file delivers the OLD content), commit it to `Downloads\Claude_Flight_Test_v0.1\Claude_Flight_Test.bat` + `System Files\claude_flight.py`, and check the sizes with `device_list_dir`.
2. Test it first against a stand-in ArcGIS Earth here (a tiny HTTP server answering GET/PUT/POST on :8000 that keeps whatever camera it was sent).
3. Jim double-clicks the .bat (Windows will not let Claude start a .bat). The .bat reads the camera, brings ArcGIS Earth to the front (PowerShell `AppActivate('ArcGIS Earth')`), waits 10 s, then flies.
4. Jim says "done"; Claude reads the log and compares the finish with the prediction.

## The moves (`py claude_flight.py <mode> ...`)

| Mode | Lesson | What it does | Proven |
|---|---|---|---|
| `read` | - | print the camera | yes |
| `turn [deg]` | 1 | turn in place (10 s) | 342.3 -> 12.3 -> 42.3, position unchanged |
| `orbit [deg]` | 2 | circle the spot under the screen centre (radius = height x tan(tilt), max 3 km), always facing it, 60 s | closed the circle to 6 decimals |
| `glide [m] [climb ft]` | 3 | straight along the heading, optional climb/descent, 25 s | finish within 0.1 m of prediction |
| `return [m] [drop ft]` | 4 | about-face (8 s) then glide back descending | landed exactly on the start |
| `driveby [m] [low ft]` | 5 | dip to low_ft while tilting up to 80, cruise, climb back; 40 s | flew as planned - but off the map edge (see rules) |
| `downtown` / `goto()` | 6 | point to point: turn onto the bearing in the first quarter, climb to cruise, fly, descend, arrive `stop_short_m` before the target looking at it | arrived exactly on the planned point |
| `gaterun` | 7 | add World Gates v21, goto the line-up point 1.5 km before a gate at the gate's height, turn onto the gate's facing, straight run (ease in, full speed), PUT the gate's destination (the jump), glide out (ease out) | JAX 'ATL' gate -> Atlanta |
| `jaxtour` | - | the recordable Dark Jacksonville tour: downtown, orbit, neighbourhood, drive-by, climb-out (~3 min planned, ~4.3 min flown) | recorded + reviewed 18:55 |
| `tour` | 8 | chain: JAX gate home from Atlanta, downtown, orbit 360, the neighbourhood, turn, drive-by, climb-out; ~4 min | all six stops clean |

Gate data comes from EarthStick's own loader (`load_gates`): `lat, lon, alt_m, facing, dest_lat, dest_lon, dest_alt_m, dest_heading`. Line-up point = gate moved 1.5 km along facing + 180.

## Rules learned the hard way

- **Know the map's bounds and keep every move AND every view inside them.** Lesson 5 ran south-west off Dark Jacksonville and hovered looking into the white void (no basemap when not signed in). Gate exits can also land outside a map - warn the viewer or start the leg sooner.
- With no basemap, map edges and Real Sim City's see-through windows show white; with real imagery underneath they show the real world (proven 18:09).
- Chain legs at full speed with ease-in on the leg before a jump and ease-out on the leg after, so the jump feels like flying through, not stopping.
- Fast legs (18 km in 50 s) need the looser hands-off thresholds, or ArcGIS Earth's own smoothing looks like someone else moving the camera.
- A drawn tall feature sits north of its base on a flat map (the clock faces are ~930 m north of the tower's foot) - aim views at what is drawn, not at the base.

## Reviewing a flight from video (2026-11-07)

Jim screen-records the flight and saves it to Downloads (stay under 400 MB: 720p or 1080p at a low bitrate). Claude pulls frames with ffmpeg (`fps=1/5` contact sheets with timestamps, plus full frames at key moments), reads ArcGIS Earth's status-bar eye alt in the frames, and matches them to the log. First review found: **moves run ~1.45x longer than planned** (fixed sleep after slow GET + PUT calls) - next version must time moves by the clock; low drive-by at tilt 80 shows too much sky; routes should stay over the city, not the river; the climb-out toward the stadium window is the money shot. `jaxtour` = the recordable tour (no gate).

## Next on the syllabus

Autopilot / screen saver (loops forever, never leaves the bounds), chopper cam (slow banked orbits, maybe a searchlight), the house-hunting tour guide (stops + captions + Windows' built-in speech), 'The Test' examiner runs, agent flight school, and tuning everything from Jim's Flight Recorder laps.
