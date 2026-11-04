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
| World Gates | Fly through a gold ring and jump to its partner or a fixed spot | Released (EarthStick 1.3, 2026-11-02) |
| Hidden gates | A gate file in the Gates folder but not loaded on the map: invisible but armed | Works now (no new code) |
| Welcome signs | Floating text near an arrival point, shown only when near | Released (World Gates v14) |
| Site stars + beacons | Click a star: a coloured beacon goes up over a site (popup script -> Automation API) | Released (World Gates v14) |
| City Beacons | Double-click to jump straight to a place | Released (EarthStick 1.3.1) |
| World Gate Maker | Make a two-way gate pair between any two places | Released (v1.0, 2026-11-04) |
| Live camera objects | Popup shows a live, refreshing traffic camera | Proven (Object Factory) |

## Building blocks still to build

- **Clue gates** - fly through to collect a clue (counts, shows a riddle, no jump). Needs EarthStick 1.4.
- **Locked gates** - stay dead until the needed clues are found. Needs EarthStick 1.4.
- **Appearing gates** - EarthStick draws the ring in the sky (through the Automation API) when it unlocks. Needs EarthStick 1.4.
- **Trap Maker** - a maker for players' own realms, like World Gate Maker.

## Realms

### 1. The Void (named by Jim, 2026-11-04)

Inspired by the Void in Star Trek: The Next Generation. A giant hidden gate snatches unsuspecting pilots and drops them somewhere far away. There is a gate home, but it is locked: find the clues to open it.

- **The trap:** hidden, giant, one-way. No warning.
- **The clues:** hidden clue rings at landmarks around the drop zone. Each one counts ("Clue 1 of 3 found") and shows the riddle to the next.
- **The way home:** invisible and dead until the last clue is found; then EarthStick draws the gold ring and arms it. Through it, you are back where you were snatched.
- **Open:** clues in order (each riddle leads to the next) or any order; where the trap is and where it drops you; how many clues.

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
