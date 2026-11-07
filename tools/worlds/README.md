# Picture worlds made by code - the homework already done

Written for the next person + AI team that wants to build their own world for ArcGIS Earth. Everything below was measured and flown live on Jim's PC (Windows 11, i3-13100, 16 GB, ArcGIS Earth 3.0.1) between 2026-11-06 and 2026-11-07. Skip the dead ends; start from what works.

## What is here

| Folder | Makes | Inputs | Proven result | Route |
|---|---|---|---|---|
| `wheres_the_firefighter/` | **New Claude City** + name-your-own-town hunt (tilted isometric island, ~32k people, a hidden firefighter and dalmatian) | none (a town name -> seed) | 32,640 x 16,840 JPEG, 25 s, 56 MB -> Picture World Maker spot 3: 31,990 tiles, 162 MB | one JPEG |
| `dark_claude_city/` | **Dark Claude City** (noir night city: deco towers, elevated railway, clock tower, shifting blocks, rain, a lone SUNNY COVE sign) | none | 32,640 x 17,420 JPEG, 31 s, 46 MB -> spot 4: 33,180 tiles, 126 MB | one JPEG |
| `dark_claude_city/world_tiles.py` | **Dark Claude City XL** - any size, straight into a TPKX | none (`--size`, `--spot`) | x10 = 105 x 54 km, 323,976 tiles, 1.56 GB, under 8 min on 7 cores | straight to tiles |
| `real_sim_city/realsim.py` | **Dark Jacksonville** - a fictional night city on a real town's own lot lines, at its real location, with see-through windows to the real imagery | a Parcel100 GeoJSON cell + an OpenStreetMap-style street map MBTiles of the same area | 8 x 7.4 km, 31,897 lots, 18,468 tiles, 133 MB, 11 min on 1 core | real location, overlay |

Each folder's `.bat` is the kit launcher (one obvious file; the `.py` files go in `System Files`). `world_tiles.py` and `realsim.py` also need `MBTiles_to_TPKX_v0_3_0.py` (Picture-World-Maker `System Files`) beside them; `realsim.py` needs `darkcity.py` for people and drawing helpers.

## Pick your route

1. **One picture** (fastest to try): draw a JPEG, then Picture World Maker places it on a World spot (30 N 80 W = spot 1, +1 degree east per spot, spots 11-20 one degree north). Limit: JPEG max 65,535 px a side, and RAM ~2x the picture at build + ~5 bytes per pixel in Picture World Maker -> about 1.5-2 gigapixels on 16 GB.
2. **Straight to tiles** (any size): draw 8 x 8-tile blocks of the top zoom on every core, shrink 4 tiles into 1 for lower zooms, pack the TPKX. Memory stays flat; only time grows. 50 GB is ~13 million tiles; a whole town object list per worker is the next limit (~17M objects) - build such worlds region by region.
3. **Real location overlay** (Real Sim City): draw at real coordinates in a true top-down projection (not isometric), leave transparent holes, load it ABOVE real imagery. No licensed imagery is ever copied into the file - each viewer sees their own imagery through the holes.

## Numbers and rules that work

**Placement (match Picture World Maker exactly):** picture centred on the spot, 1 picture pixel = 1 Web Mercator metre, bounds `cx +- W/2, cy +- H/2`; tile (tx, ty) at zoom z covers `res = 156543.03392804097 / 2^z` metres per tile pixel, origin `(-20037508.34 + tx*256*res, 20037508.34 - ty*256*res)`; MBTiles rows are TMS: `row = 2^z - 1 - ty`. Ground metres = Mercator metres x cos(latitude).

**Isometric (tilted) worlds:** tile (c, r) at height z -> `x = X0 + (c - r) * 48`, `y = Y0 + (c + r) * 24 - z` (tiles 96 x 48 px); inverse `c = (a + b)/2, r = (b - a)/2` with `a = (x - X0)/48, b = (y - Y0)/24`. Visible box faces: the r = r1 face (front-left) and the c = c1 face (front-right). A circle of R tiles is an ellipse `R*sqrt2*48` x `R*sqrt2*24`. Painter order: key = footprint centre c + r (people and trees: their foot point).

**Top-down real-location worlds:** buildings extruded with a lean of (0.30 right, 0.62 up) screen units per metre of height; a face is visible when its outward normal . lean < 0; paint by the footprint's southernmost y. Toy-city look: people and cars ~2.5x real (a real person is 3 px at zoom 19), low buildings 2x real height. **A drawn tall feature sits NORTH of its base on the flat map** (the clock faces of a 230 m tower are ~930 m north of its foot) - mark drawn features at the map point under them, not at the base.

**Smooth and correct drawing (Pillow):** draw each chunk at 2x and `reduce(2)`; `ImageDraw.Draw(img, "RGBA")` blends see-through fills ONLY on an RGB image - on an RGBA image the glows come out as solid discs, so draw on RGB and add the alpha channel afterwards. Ground polygons need `outline = fill` (no hairline gaps). Give every random choice one seeded `random.Random` -> the same seed draws the same world byte for byte.

**Big-data pitfalls:** classify colour pictures in strips (128 rows) - doing a whole map at once ran out of memory; multiprocessing must use `spawn` (Windows) and each worker rebuilds the world from the seed; SQLite readers in workers open `Path(...).as_uri() + "?mode=ro"` (Windows paths with spaces) while the main process writes in WAL mode; the first progress estimate includes every worker's start-up - it starts absurdly high, ignore it.

**Tiles and TPKX:** solid tiles JPEG, partly see-through tiles PNG, fully transparent tiles left out (no tile = the layer below shows); the TPKX is written as MIXED by `MBTiles_to_TPKX_v0_3_0` (mb2tpkx structure). ArcGIS Earth composites layers by order - the top layer wins every pixel it draws, transparent pixels pass through.

**Land use from a street map (Real Sim City):** OpenStreetMap standard-style colours - water (171,210,225), residential (223,223,223), industrial (235,218,234), commercial (242,218,217)/(255,214,209), parks (174,208,158) and friends, school (255,255,229), roads white/yellow/orange/pink. Majority vote in a 5 x 5 patch at the lot centre, ignoring roads, buildings and background. Lot rule (Jim): small residential = houses, bigger = apartments, industrial = warehouses, commercial = shops, downtown commercial = towers thinning with distance, huge lots split into several buildings, parks = trees.

**Distance switch in ArcGIS Earth (porch-light beacon):** a KML Region box around the place with `minLodPixels = sqrt(box ground area) * 1818 / distance` lights it only within `distance` (1818 = effective focal length in px, from Object Factory's calibration 1,790,000 ft*px for a 300 m cube). For a 2:1 island box at one island width the number is 1285 whatever the size. Proven live: Mega Dark Claude City beacon v4.

## Rules of the road (Jim's)

- Original work only: no borrowed characters, logos, brand or film names. A film's MOOD is fine; its characters, places and names are not. Invented signs, never repeated.
- Real data -> **real structure, invented life**: from parcel data use only lot shapes and acreage, never owner names or addresses. Street layouts are not copyrightable; take them from OpenStreetMap (credit "(c) OpenStreetMap contributors"), never traced from Google or Esri imagery.
- One obvious `.bat` per package, everything else in `System Files`; every test is a full kit; every file and version carries its version number.

## Make your own world in five steps

1. Pick the route above and copy the matching folder.
2. Change the look: palettes, building builders (`BUILDERS` in `darkcity.py` take a 14 x 14-tile block), people (`noir_look`), overlays (rain, fog).
3. For a real place: export a Parcel100 cell and the same area's street map from QGIS; set `DOWNTOWN` and `WINDOWS` in `realsim.py`.
4. Build small first (one block preview, then size 1), look at full detail, then go big.
5. Fly it, find what feels wrong from the pilot's seat, change one thing, version it, fly again.
