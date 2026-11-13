# The Realm — Instruction Book

### Branch your own universe on top of the real Earth

🤖 **Using AI assistance?** This whole page is written to be handed straight to your AI helper (Claude, ChatGPT, or any other). Paste it in, or point your agent at it, and say: *"help me build a realm using this."* Everything your AI needs to start is here. (For the wider project it belongs to, see the [ArcGIS Earth Unlocked](../README.md) front page and its `CLAUDE.md`.)

---

## What this is

**ArcGIS Earth** is a free globe viewer from Esri. It shows satellite imagery and your own offline maps. On its own it has no games, no gates, no adventures.

This project adds a layer of adventure *floating above the real map*: gold **gates** you fly through to teleport across the world, **signs** and **menus** hanging in the sky, **beacons** that shoot up from the ground, **clues**, **traps**, and whole **picture worlds** of your own making. You move through all of it with a joystick, using a free tool called **EarthStick**.

The point of this page is simple. Jim built the first realms with his AI. His wish was that *you* would sit down with your own AI and build your own — **"my Claude left your Claude an instruction book."** This is that book. It is the gate file format, the handful of facts about ArcGIS Earth that were learned the hard way (by measuring, not guessing), the free tools that make gates for you, and the rules of the road. The example realm is **The Void**.

> *Google owns the ground, but we own the space above it.*

Nothing here requires coding. It requires a free globe viewer, a few free tools, and a willingness to test. Everything below has been proven in **ArcGIS Earth Desktop 3.0.1** unless it is clearly marked *coming* or *untested*.

---

## The one idea

A **gate** is a spot in the sky with a position, a height, a size, and a direction it faces. When you fly a joystick forward through the front of a gate, ArcGIS Earth's camera instantly jumps to the gate's **destination** — a partner gate on the far side of the world, or any fixed point you choose. That is the whole trick. Everything else — signs, clues, traps, picture worlds — is decoration and rules layered on top of it.

A gate lives in a **KMZ file** (a small zipped map file). The look of the gate — a gold ring or square drawn in the air — is just decoration. The gate itself is a few lines of plain data inside that file that EarthStick reads.

---

## What you need

1. **ArcGIS Earth** (free) — the globe viewer everything runs in: <https://www.esri.com/en-us/arcgis/products/arcgis-earth/downloads>. After installing, turn on its remote control: **Settings → Advanced application settings → enable Automation API** (this lets EarthStick fly the camera; it listens at `http://localhost:8000`).
2. **Python 3** (free) — <https://www.python.org/downloads/windows/> (tick *Add python.exe to PATH*). The tools install anything else they need by themselves.
3. **EarthStick** (free, in this family) — flies the ArcGIS Earth camera with a joystick and reads your gates. A joystick helps but the flight tools also run hands-free.
4. **World Gate Maker** and **Picture World Maker** (free, in this family) — make gates and picture worlds for you, so you never hand-write a file unless you want to.

All of these are linked from the [ArcGIS Earth Unlocked front page](../README.md). They are offline-first: once installed, they work with no internet (your own offline maps keep working; only ArcGIS Earth's *online* basemaps need a connection).

---

## The gate file (with a working example)

Gates are KMZ files you drop into a folder named **`Gates`** next to EarthStick. EarthStick reads them when it starts (newer versions also re-read the folder while you fly, so a gate added mid-flight arms within a couple of seconds). **The folder is the on/off switch**: a gate file sitting in `Gates` but *not* loaded onto the ArcGIS Earth map is **invisible but still armed** — that is how hidden traps work.

Inside the KMZ, each gate is a `<Placemark>` whose `<ExtendedData>` carries the gate's data. Here is a **real, working two-way gate pair** — fly through the gold gate hovering over Bryceville, Florida and you come out over Central Park in New York, and vice versa:

```
Gate "Central Park"  (hovering over Bryceville, FL)
    gate   = 1
    lat    = 30.3961        ← where this gate is
    lon    = -81.9392
    alt_m  = 178.308        ← its height, in metres above SEA LEVEL
    radius_m = 125.0        ← how big the opening is
    facing = 29.72          ← compass heading you fly to go THROUGH it
    to     = Bryceville     ← the partner gate's name (in the same file)

Gate "Bryceville"  (hovering over Central Park, NYC)
    gate   = 1
    lat    = 40.7812
    lon    = -73.9665
    alt_m  = 188.976
    radius_m = 125.0
    facing = 214.39
    to     = Central Park
```

Each gate is **named for where it takes you**, so the label you read in the sky is your destination. The two gates point at each other with `to=`, so the pair is a round trip.

**The fields, in plain words:**

| Field | Meaning |
|---|---|
| `gate` | Always `1` — marks this placemark as a gate. |
| `lat`, `lon` | Where the gate hangs. |
| `alt_m` | Its height in **metres above sea level**. (ArcGIS Earth's "eye alt" is also from sea level — see below.) |
| `radius_m` | How big the opening is. Bigger = easier to fly through. |
| `facing` | The compass heading (0 = north, 90 = east…) you must be flying to pass through the **front** (gold) side. |
| `to` | The name of the partner gate **in the same file** — makes a two-way pair. |
| `dest_lat`, `dest_lon`, `dest_alt_m`, `dest_heading` | Use these **instead of** `to` for a **one-way** gate to any fixed spot. You arrive at that exact point, facing that heading. |

**How a gate behaves (all proven live):**

- It fires only on a **forward pass through the gold (front) side**, within `radius_m`, while the joystick is actually moving the camera. Flying backwards through it, or drifting past the red back, does nothing.
- After a jump there is a short **cool-down** (about 2 seconds) so you don't instantly re-trigger.
- With `to=`, you arrive a short distance *past* the partner gate, facing away from it, so you never bounce straight back.
- You don't hand-place these numbers. **World Gate Maker** and the **Gate Dropper** (below) write correct gate files for you.

---

## What is true about ArcGIS Earth (learn these, don't guess)

Every one of these was learned by measuring on a real screen. An AI that assumes otherwise will build things that don't line up.

- **Heights are from sea level.** The camera's "eye alt" and a gate's `alt_m` are both above sea level, not above the ground. A gate 500 ft over a 100 ft hill has `alt_m` ≈ 600 ft worth of metres.
- **Text and icons are a fixed size on screen** — they do **not** shrink as you fly away. So distant things don't get crowded, but **nearby signs shift and pile up as you move**. Put signs and menus **several kilometres out**; EarthStick's aim reaches any distance.
- **Labels wrap by width.** Keep a sign's text short (roughly **18 characters or fewer** on one line) or it wraps and breaks at hyphens.
- **You can hide a thing until you're close.** A KML `<Region>` with `<minLodPixels>` on a `<Folder>` makes its contents appear only within about a set distance. Build it as a small **cube** (give the box a min/max altitude), not a flat square, or it vanishes when seen edge-on. Rule of thumb from calibration: `minLodPixels ≈ 1,790,000 ÷ (feet you want it to appear within)` for a 300 m cube.
- **A popup is a real web browser.** An object's popup can show a live, self-refreshing web page (a traffic camera was proven), **and its JavaScript can call the Automation API** at `http://localhost:8000/arcgisearth/...`. That is how a "SHOW ME" button in a popup can shoot a beacon up from the ground with no helper program.
- **The remote-control (Automation) API can move the camera** (`GET`/`PUT /arcgisearth/camera`), **draw** in the air (`POST /arcgisearth/drawings` — these keep their height), and **add or remove map layers** (`POST`/`DELETE /arcgisearth/layer`). It **cannot** tell you what the user clicked — there are no click events. Anything that reacts to a click must go through that object's own popup.
- **Drawings keep their height; graphics stick to the ground.** If you draw something in the sky through the API, use a *drawing*, not a *graphic*.
- ArcGIS Earth **ignores** a KML's built-in camera/LookAt, so "jump straight to a place" lands you overhead rather than at a set angle. That's fine; plan for it.

---

## Tools that make gates for you

You almost never edit a gate file by hand. Three free tools in this family do it:

- **World Gate Maker** — type (or paste from Google Maps) two places, pick a size, and it writes a correct two-way gate pair straight into EarthStick's `Gates` folder. The "OG" way to build a realm's map of gates.
- **Gate Dropper** (built into EarthStick) — the fastest way. Fly to a spot, press the trigger to mark it, fly somewhere else, press again, and a gate pair appears at your exact heights, ready to fly. Building a tour becomes *fly-and-press*.
- **Picture World Maker** — turns any big picture (a painting, a panorama, a map, your own artwork) into a **place on the globe** you can fly into. Flat pictures park out over the open Atlantic at a fixed spot, one metre per pixel; there are 20 numbered "world spots" so you can lay out a gallery of them. Reach each one with a World Gate Maker pair (use ground elevation 0 over the ocean).

---

## Sky-layout rules (for every sign, menu, and clue)

These were learned by flying and fixing, over many versions. Follow them and your realm reads cleanly from the cockpit:

1. **Put signs and menus several kilometres out.** Near things slide and pile up as you move; far things sit still like scenery.
2. **Put them in the sky**, above about one degree up. From flying height the horizon is at eye level, so anything lower lands on top of busy imagery.
3. **A board must fit the view** (about 78° wide). Split a long list into rows about 4° apart; never one tall column (each name lands beside the icon above it).
4. **Keep clear of gates and their names.** A gate's label sits beside it. If there's no room, lift the whole board above the gates.
5. **Version everything.** Put the version in every file name and layer name (`World_Gates_Tour_v3.kmz`). Never overwrite a file people already have under the same name.

---

## Building a realm: *The Void*, the worked example

A **realm** is a package of gates (and whatever you hang in the sky) that tells a little story or runs a little game over the real Earth. *The Void* is the example — named after the trap in *Star Trek: The Next Generation*.

**The shape of it:**

- **The trap** — a giant, hidden, **one-way** gate. The pilot is flying along and, with no warning, is snatched and dropped somewhere far away. (A one-way gate uses `dest_*`; "hidden" means the file is in the `Gates` folder but never loaded onto the map — *invisible but armed*. **Both work today.**)
- **The clues** — hidden gates at landmarks around the drop zone. Each one you find counts ("Clue 1 of 3") and shows the riddle leading to the next.
- **The way home** — dead and invisible until the last clue is found; then it appears in the sky and arms itself. Fly through and you're back where you started.

Two honest notes for your AI:

- The **trap** and the **hidden one-way gates** work with EarthStick as it is today.
- **Clue gates, locked gates, and gates that appear when unlocked** are a planned EarthStick feature (**"1.4"**) and are **not built yet**. Until then, build the counting/locking in whatever way your tools allow, or keep the puzzle simple.

**A full game you *can* build today — the "flash round":** a chain of one-way gates where each arrival faces a hidden exit gate straight ahead. You come out of one gate, get only a glimpse of where you are, and fly straight into the next. Great as a classroom "where in the world am I?" game: fly in full-screen (no coordinates showing), guess from what you see, then you're whisked onward. No new features needed — just hidden one-way gates and the sky-layout rules above.

Keep spoilers (where a trap is, what the answers are) out of anything you publish, so the surprise survives.

---

## Rules of the road

This project gives away **tools, not data**. Please keep it that way:

- **Use imagery and pictures you're allowed to use.** ArcGIS Earth's own basemaps, maps you build yourself, or openly licensed / public-domain pictures. Don't redistribute someone else's imagery, and check a picture's terms before you turn it into a world.
- **Make your own designs and names.** If a gate's look or a world's signs are *inspired by* a film, a book, or a place, that's fine — but invent your own names and art; don't copy protected characters, logos, titles, or designs.
- **Offline first.** Build so your realm works with no internet. Online links are a bonus, never a requirement.
- **Credit your sources** when you lean on one (OpenStreetMap, a museum's public-domain scan, and so on).
- **No safety or certification claims.** This is for exploration, teaching, and fun.

---

## How to work with your AI

- **Hand it this page.** It contains the file format, the proven facts, the tools, and the rules — enough to start.
- **Measure, don't guess.** The facts above exist because screens were measured. When something looks off, take a screenshot and work from what's actually there.
- **Test in ArcGIS Earth.** Nothing is "done" until you've flown it. Build small, fly it, fix it, fly it again.
- **Then build your own.** New gates, new signs, new worlds, new games — a realm nobody has flown before.

Welcome to the space above the map. Go make something in it.

---

*Part of [ArcGIS Earth Unlocked](../README.md) — free, open, offline-first tools for making and moving through maps in ArcGIS Earth.*
