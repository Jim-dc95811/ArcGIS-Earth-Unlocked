# The Realm - design journal

**Started:** 2026-11-04, by Jim and Claude.
**Purpose:** the ongoing log of the Realm - games, gates and adventures built on top of the real map in ArcGIS Earth with EarthStick. Every idea, decision and release gets a dated entry here. Newest entries go at the bottom of the log.

> Google owns the ground, but we own the space above it.

## What the Realm is

The real Earth (ArcGIS Earth imagery and terrain) with a layer of adventure floating above it: gates, traps, clues, beacons and signs. You move through it with EarthStick.

The adventures will be **released together as packages**: one download, many realms. Each one is a set of KMZ files for EarthStick's `Gates` folder plus anything shown on the map.

**The overarching theme (Jim, 2026-11-05):** *"3D space. Placing objects in it, and doing things while in it. Different objects, different behaviors, different possibilities revealed."* Every idea in this journal is judged against that: what can be placed in the space above the real map, how it behaves, and what it lets the pilot discover or do.

## Building blocks (what exists today)

| Block | What it does | Status |
|---|---|---|
| World Gates | Fly through a gold gate and jump to its partner or a fixed spot | Released (EarthStick 1.3, 2026-11-02; current pack v21 in 1.3.4) |
| Square gates with legs | Gate drawn as a square with four legs running back: the mouth and the way it points show at a glance from any angle | Released (World Gates v21, EarthStick 1.3.4; World Gate Maker 1.1, 2026-11-05) |
| Ring-height light + tractor beam | Green RING HEIGHT light when level with the gate ahead; within 1.5 km the beam pulls you onto its height (LOCKED ON) | Released (EarthStick 1.3.4) |
| Hidden gates | A gate file in the Gates folder but not loaded on the map: invisible but armed | Works now (no new code) |
| Welcome signs | Floating text far out in the sky ahead of an arrival point, shown only when near | Released (World Gates v14; sky layout v19) |
| Site stars + beacons | Click a star: a coloured beacon goes up over a site (popup script -> Automation API) | Released (World Gates v14) |
| City Beacons | Double-click to jump straight to a place | Released (EarthStick 1.3.1) |
| World Gate Maker | Make a two-way gate pair between any two places | Released (v1.0, 2026-11-04; v1.1 square gates 2026-11-05) |
| Live camera objects | Popup shows a live, refreshing traffic camera | Proven (Object Factory) |
| Viewer model | Predicts exactly where anything appears on Jim's screen (78 deg view, label offsets) and flags overlaps before flying | `tools/preview_view.py` (2026-11-04) |

## Building blocks still to build

- **Clue gates** - fly through to collect a clue (counts, shows a riddle, no jump). Needs EarthStick 1.4.
- **Locked gates** - stay dead until the needed clues are found. Needs EarthStick 1.4.
- **Appearing gates** - EarthStick draws the ring in the sky (through the Automation API) when it unlocks. Needs EarthStick 1.4.
- **Trap Maker** - a maker for players' own realms, like World Gate Maker.
- **3D model test (ready to build on Jim's word)** - one small arch model (KML `<Model>` + COLLADA `.dae` inside a KMZ) floating over Jacksonville; drag into ArcGIS Earth. Shows up = Realm doorways are possible; if not, doorways are drawn as outlines with lines, like the rings.

## Realms

### 1. The Void (named by Jim, 2026-11-04)

Inspired by the Void in Star Trek: The Next Generation. A giant hidden gate snatches unsuspecting pilots and drops them somewhere far away. There is a gate home, but it is locked: find the clues to open it.

- **The trap:** hidden, giant, one-way. No warning.
- **The clues:** hidden clue rings at landmarks around the drop zone. Each one counts ("Clue 1 of 3 found") and shows the riddle to the next.
- **The way home:** invisible and dead until the last clue is found; then EarthStick draws the gold ring and arms it. Through it, you are back where you were snatched.
- **Open:** clues in order (each riddle leads to the next) or any order; where the trap is and where it drops you; how many clues.

## The instruction book (Jim, 2026-11-04)

Jim's real goal for the Realm: people take the tools, sit down with their own Claude and **branch their own universe**. In Jim's words: *"my Claude left your Claude an instruction book."* So the Realm ships with a public page written to be handed straight to an AI: the gate file format with a working example, what is proven in ArcGIS Earth (eye alt from sea level, fixed-size text hidden when far, names wrap past ~18 characters, popups can draw beacons through the Automation API), the tools (World Gate Maker, `make_gate_kmz.py`, the beacon script), and the rules of the road (tools, not data; imagery people are allowed to use). The Void is the example realm. Not written yet.

## Realm doorways (Jim, 2026-11-04)

Gates don't have to be rings: the ring is only decoration, the gate itself is invisible data. Jim: **each door takes the look of a door native to its destination.** Our own designs, inspired by each place (not copies of protected designs): Tokyo - a torii gate; Rome - a stone triumphal arch; Paris - an Art Nouveau metro-style arch; London - a black Georgian door with a fanlight; New York - a brownstone doorway; Rio - a colonial doorway in bright colours; Sydney - a harbour-sail frame; Atlanta - an airport gate frame; The Void - a cracked stone arch. Needs a first test: does ArcGIS Earth show 3D models (KML `<Model>` / COLLADA) inside a KMZ? Not tested yet.

## Mystery Gate (Jim, 2026-11-04)

One gate, a different destination every time: "a mystery gate that would pop you at the bottom of the great pyramid ... inside a zoo ... crazy places, and they all have a GPS coordinate." The gate holds a list of places (lat, lon, height, heading); each pass picks one at random. Needs EarthStick 1.4 (a gate with several destinations). Each place needs its ground height (arrival heights are sea level) and a facing direction toward the thing worth seeing. First list ideas: base of the Great Pyramid (Giza), a zoo enclosure, the floor of the Grand Canyon, Niagara Falls from the river, Everest summit, Stonehenge, Uluru, Machu Picchu, the Taj Mahal, the South Pole, the middle of the Pacific. Variants: a "Mystery" ring at the Atlanta hub; mystery gates hidden around Jacksonville; a daily-mystery gate. Could ship as a "Mystery Places" pack people add to.

**Classroom mode (Jim is a teacher, 2026-11-04):** the teacher holds the answer key (place, details, what to look for); students fly in **full-screen mode** (no status bar, so no coordinates) and must work out where they are from **visual clues** before time runs out and they are sent on. Needs, besides the random pick: a **stay timer** (EarthStick sends you back or onward after N seconds), **no giveaways** (no welcome sign, gate named "?", no landmark names; the basemap's own labels are clues too - imagery without labels for a harder level), and a **teacher's sheet** printed from the same place list (answers, facts, discussion questions). Ideas: difficulty levels (famous landmark -> ordinary street in a far country), a round of ten jumps, students write their guess before the timer ends.

**Flash round (Jim, 2026-11-04):** as soon as they come out of a gate they fly straight into the next one, so they only get the first look. **Works with today's EarthStick (no new code):** a chain of one-way gates, each arrival facing a hidden exit ring straight ahead that leads to the next place. Watch the 2-second rest after a jump: the exit ring must be far enough ahead that the pilot reaches it after the rest (or it lets them through without jumping). Glimpse length = distance to the next ring, set per level. Hidden rings (in the Gates folder, not on the map) mean nothing gives the game away.

## Idea backlog
- **Joystick Explorer + universal EarthStick (Jim/Claude, 2026-11-04):** a standalone tool that lists every connected controller, shows live axis bars and button lights, walks the user through 'push forward / twist / throttle / press your trigger...', and saves a joystick settings file; a future EarthStick reads that file (no file = exactly today's behaviour with the T.A320). Opens EarthStick to any stick people already own. Explorer = straightforward; the real work is testing on hardware we don't have (Jim has only the Airbus stick - needs viewer volunteers). Gamepads (XInput) and two-piece HOTAS are a later step.

- **HOME button (Jim, 2026-11-05):** one joystick button takes you straight back to Jacksonville from wherever you are - lost over Tokyo, one press and you're home. Notes: **Button 2 is free** (the trigger stayed trigger-click); the jump itself is already proven - it is the same camera move a World Gate makes, just with no gate. Ideas to settle when it's built: where exactly 'home' is (suggestion: just short of the JAX gate at 1,500 ft, facing it, so one push forward sends you back out to Atlanta - or Jim's own home), whether it fires on one press or a short hold (so a bump can't send you home mid-flight), and a home spot people can set for their own town. Needs an EarthStick release (1.3.5 or part of 1.4); in The Void it could be switched off, so the only way out is to solve the clues.
- **City info panel (Jim, 2026-11-05):** instead of only the famous-landmark board at each city's gates, a live **info panel**: live webcam, current weather, current radar, news headlines, and more. Why it should work: the ArcGIS Earth popup is a full web browser that runs JavaScript and is already proven showing a live, self-refreshing FL511 camera, so one click on a panel object (or a trigger-click from EarthStick) can open a live city page. Candidate free sources to test: weather - **Open-Meteo** (worldwide, no key) or the **National Weather Service** API (US only); radar - **RainViewer** (worldwide radar tiles) or NWS radar images; webcams - see *Live webcams* below; news - each city's public news RSS feeds. Open questions for the first test: whether the popup browser is allowed to fetch these services directly (some sites block requests from other pages), and what the panel shows with no internet (it must fail politely - offline first). Layout follows the sky rules: far out, in the sky, clear of the gates. Suggested first test: one panel for Jacksonville with weather + radar + one webcam.
- **Sky traffic: the zeppelin (Jim, 2026-11-05):** other flying objects sharing the sky with you - starting with a slow zeppelin drifting over a city. What we know: a still zeppelin works today (Object Factory floats any picture at any height). Moving it with ArcGIS Earth's live drawing tools does not work well - measured on 11/5: drawings keep their height but flash the cyan 'just added' highlight on every move; graphics move smoothly but are glued to the ground. Two routes:
  1. **EarthStick's see-through layer (most promising):** EarthStick already draws the crosshair and readout over ArcGIS Earth and knows the camera ten times a second; with the viewer model (`tools/preview_view.py`, about 5 px accurate) it can draw the zeppelin picture where it would appear in the sky - growing as you close in, sliding as you turn, drifting along its own slow route. Smooth, no flash. Limits: only while EarthStick runs; always drawn on top (cannot pass behind hills or buildings). Size of job: about the readout plus the ring light.
  2. **A self-refreshing map file (needs a 10-minute test):** if ArcGIS Earth re-reads a KML file every few seconds (a KML NetworkLink with a refresh interval), EarthStick could rewrite the zeppelin's position into it and it becomes a real map object - hides behind terrain, visible to anyone. Untested: whether ArcGIS Earth refreshes it at all, and whether it flashes.
  Later: more traffic (helicopters, birds, other 'pilots'), objects with routes and schedules, objects you can chase or follow, a zeppelin that is itself a moving gate.
- Famous traps: Bermuda Triangle -> over the South Pole; Area 51 (Groom Lake) -> somewhere unexpected.
- Kids' scavenger hunt around Jacksonville: hidden gates send you to clue spots, beacons guide you on.
- Traps that catch from any direction: several hidden rings at one spot facing different ways.
- World Gate Maker 1.2 ideas (Jim, 2026-11-04; 1.1 became the square gates - not approved to build yet): one-way gates (Place 2 = drop point, no return ring); a PNG picture with each ring (a 'door look' without 3D models); hidden option; ring colour; more than one pair per file.
- **Live webcams (2026-11-04, sources found):** a live camera at each World Gates city / Realm place. The ArcGIS Earth popup is a full browser (live FL511 camera already proven), so a popup can embed a live player.
  - **Windy Webcams** (windy.com/webcams; API api.windy.com/webcams) - largest worldwide collection; free API tier (key required) filters by country, category and location; free-tier still-image links expire after ~10-15 min, so embed their live/timelapse player (free at any size), not a fixed picture link. Pro tier 9,990 EUR/yr - not needed.
  - **EarthCam** - curated famous places (Times Square, Abbey Road, Las Vegas, Niagara...).
  - **SkylineWebcams** - European landmarks (Rome, Venice, Paris, Greek islands, volcanoes) - matches the tour cities.
  - **Explore.org** - nature and animal cams (bears, eagles, aquariums, zoos) - fits the Mystery Gate 'inside a zoo' and classrooms.
  - **YouTube live streams** - many cities and attractions run 24-hour cams.
  - Rule: only official, intentionally public cameras - never sites that list unsecured private cameras.
  - **First test:** one camera object near a tour arrival whose popup embeds a Windy or YouTube live player - does it play inside ArcGIS Earth?
- More hubs beyond Atlanta.
- Sky menu boards for public safety: hydrants, stations, hospitals, staging - pick one and a beacon guides you.

## Log

- **2026-11-02** - First wormhole jump, JAX -> NYC, 19:41 (Jim: "GIS history"). World Gates released in EarthStick 1.3 that night.
- **2026-11-03** - Round-the-world tour, welcome signs, one-click site beacons (World Gates v14); EarthStick 1.3.1 released; video "ArcGIS Earth Flight: City to City Using Wormholes" (`2N8-4cWMoPw`) posted.
- **2026-11-04** - World Gate Maker 1.0 released (Jim flew Home <-> Central Park: "truly a marvel"). Jim: hidden giant trap gates "like the Void in STTNG"; the way home needs clues. **The Realm** named as the bigger plan, released as packages; this journal started. First realm: **The Void**.
- **2026-11-04** - Jim: rather than us building every game, people should "get with your twin brother Claude and branch their own universe" - the instruction book for their Claude (see above).
- **2026-11-04** - Placement rule from Jim: put signs and menus far away (several km). Close objects shift and pile up as you move; distant ones stay put like scenery, and the trigger reaches them anyway. World Gates v16 built on it.
- **2026-11-04** - Jim asked Claude to work out the 3D geometry for future objects. Result: a viewer model of ArcGIS Earth (78 deg view, label offsets, text widths) fitted to Jim's Rio screenshot within 5 pixels, and a preview tool (`tools/preview_view.py`) that draws any arrival view and flags overlapping labels before anyone flies it. Rules in `tools/ARCGIS_EARTH_API.md`. Every future Realm sign, menu and clue gets checked with it.
- **2026-11-04** - EarthStick 1.3.2 released with World Gates v19 (signs and site stars in the sky, far out, two rows, clear of the gates). Jim: "these are more ornaments on our beta". The sky layout rules (CLAUDE.md section 3a, `tools/ARCGIS_EARTH_API.md`) now apply to every Realm object.
- **2026-11-04** - Jim: "each door would take the appearance of a door native to the destination" - Realm doorways (see above). Needs a 3D-model test in ArcGIS Earth first.
- **2026-11-04** - Jim on how the Realm gets built: he knows many things can be coded into existence but took the analog path long ago; with an AI partner "the possibilities branch in wild lightning type patterns." Working mode: Jim plays with ideas and tests; Claude builds, measures and keeps this journal.
- **2026-11-04** - Jim: Mystery Gate - one gate, a random crazy destination each time (bottom of the Great Pyramid, inside a zoo...). Logged above.
- **2026-11-04** - Jim (a teacher): Mystery Gate classroom mode - full screen, visual clues only, a timer before they must leave; teacher knows the details. Logged under Mystery Gate.
- **2026-11-04** - Jim: flash round - straight from one gate into the next, one look per place. Possible with EarthStick as it is.
- **2026-11-04** - Webcam sources found for the city/Realm webcam idea (Windy API, EarthCam, SkylineWebcams, Explore.org, YouTube live); first test = an embedded live player in a popup.
- **2026-11-05** - Gate alignment solved, in Jim's words 'great fundamental research'. Laser beam and approach arrows tried and dropped; square gates with legs ('That is the effect. Brilliant.'), a green RING HEIGHT light and a tractor beam ('like a giant space ship locks on') shipped in EarthStick 1.3.4 with World Gates v21 (Jim: 'to london and back, working great'). For the Realm: any gate in a game can be flown through reliably, even small ones, and the tractor beam is a ready-made 'the gate grabs you' moment for The Void. World Gate Maker 1.1 (square gates) in test.
- **2026-11-05** - Jim: a HOME button on the joystick that takes you back to Jacksonville from anywhere. Logged in the backlog (Button 2 is free; the jump is the same proven camera move a gate makes).
- **2026-11-05** - Jim: replace the landmark board at each city with a live info panel - webcam, weather, radar, news headlines. Logged in the backlog with candidate free sources and the first test to run.
- **2026-11-05** - Jim named the overarching theme: *3D space - placing objects in it, doing things while in it; different objects, different behaviors, different possibilities revealed.* First moving object idea logged: **sky traffic, starting with a slow zeppelin** (two routes in the backlog: EarthStick's see-through layer, or a self-refreshing map file to test).
