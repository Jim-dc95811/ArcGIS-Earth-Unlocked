# The Realm - design journal

**Started:** 2026-11-04, by Jim and Claude.
**Purpose:** the ongoing log of the Realm - games, gates and adventures built on top of the real map in ArcGIS Earth with EarthStick. Every idea, decision and release gets a dated entry here. Newest entries go at the bottom of the log.

> Google owns the ground, but we own the space above it.

## What the Realm is

The real Earth (ArcGIS Earth imagery and terrain) with a layer of adventure floating above it: gates, traps, clues, beacons and signs. You move through it with EarthStick.

The adventures will be **released together as packages**: one download, many realms. Each one is a set of KMZ files for EarthStick's `Gates` folder plus anything shown on the map.

## Building blocks (what exists today)

| Block | What it does | Status |
|---|---|---|
| World Gates | Fly through a gold ring and jump to its partner or a fixed spot | Released (EarthStick 1.3, 2026-11-02; current pack v19 in 1.3.2) |
| Hidden gates | A gate file in the Gates folder but not loaded on the map: invisible but armed | Works now (no new code) |
| Welcome signs | Floating text far out in the sky ahead of an arrival point, shown only when near | Released (World Gates v14; sky layout v19) |
| Site stars + beacons | Click a star: a coloured beacon goes up over a site (popup script -> Automation API) | Released (World Gates v14) |
| City Beacons | Double-click to jump straight to a place | Released (EarthStick 1.3.1) |
| World Gate Maker | Make a two-way gate pair between any two places | Released (v1.0, 2026-11-04) |
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

## Idea backlog

- Famous traps: Bermuda Triangle -> over the South Pole; Area 51 (Groom Lake) -> somewhere unexpected.
- Kids' scavenger hunt around Jacksonville: hidden gates send you to clue spots, beacons guide you on.
- Traps that catch from any direction: several hidden rings at one spot facing different ways.
- World Gate Maker 1.1: a "hidden, one-way" option.
- Live webcam object at each World Gates city (Jim to pick the webcams).
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
