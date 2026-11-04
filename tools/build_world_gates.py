"""Build the World Gate network (Jim, 2026-11-02): JAX (over JIA) -> ATL hub (over Hartsfield-Jackson)
-> seven landmark destinations, each with an "ATL" return ring. All gates are one-way with explicit
landing spots, so ring names can repeat (every return ring is called ATL).

python3 build_world_gates.py <output.kmz>
"""
import math
import sys
from make_gate_kmz import gate, write_kmz, dest, bearing, welcome_sign, site_placemark, lod_folder
from pathlib import Path

GATES_VERSION = "v19"           # Jim: every change gets a new version number
FT = 0.3048
JIA = (30.4941, -81.6879)        # Jacksonville International
ATL = (33.6407, -84.4277)        # Hartsfield-Jackson Atlanta
HUB_R = 3000.0                   # ATL departure rings: a circle this far out, around the airport (Jim: 1.5x)
ATL_GROUND = 1026 * FT           # Hartsfield-Jackson field elevation (ring heights are above sea level)
JAX_LEVEL = 1500 * FT            # JIA is ~30 ft above sea level
LEVEL = ATL_GROUND + 1500 * FT   # ATL terminal level: 1,500 ft above the airport
# Jim (2026-11-02): eight equal-height rings evenly around the airport; stand in the middle, turn and pick.
# NYC/London/Paris/Rome all lie ~45-51 deg from ATL, so the ring is laid out like a world map wrapped
# around you (Atlantic cities west to east), with home (JAX) in its true south-east direction.
SLOT = {"NYC": 315, "London": 0, "Paris": 45, "Rome": 90, "JAX": 135, "Rio": 180, "Sydney": 225, "Tokyo": 270}
HUB_ARRIVAL_HEADING = 22.5       # arrive facing between two gates, never straight into one
RING_R = 225.0                   # 450 m rings
EXIT_M = 300.0
APPROACH_M = 2000.0              # v9 (Jim: spread it out): return ring this far from the landmark, toward ATL; next-city ring as far beyond

# name: (landmark lat, lon, ring altitude m absolute, level in its direction tower)
DEST = {
    "NYC":    (40.6892, -74.0445, 457.0, 0),     # Statue of Liberty
    "London": (51.5055, -0.0754, 457.0, 1),      # Tower Bridge
    "Paris":  (48.8584, 2.2945, 600.0, 2),       # Eiffel Tower (330 m tall)
    "Rome":   (41.8902, 12.4922, 457.0, 3),      # Colosseum
    "Tokyo":  (35.6586, 139.7454, 600.0, 0),     # Tokyo Tower (333 m tall)
    "Sydney": (-33.8568, 151.2153, 457.0, 0),    # Opera House
    "Rio":    (-22.9519, -43.2105, 1000.0, 1),   # Christ the Redeemer (on a 700 m peak)
}

gates = []
hub_arrival = dict(dest_lat=ATL[0], dest_lon=ATL[1], dest_alt_m=LEVEL, dest_heading=HUB_ARRIVAL_HEADING)

# JAX -> ATL
b_atl = bearing(*JIA, *ATL)
gates.append(gate("ATL", *JIA, JAX_LEVEL, facing=b_atl, radius_m=RING_R, **hub_arrival,
                  description="<b>Gate to Atlanta (ATL)</b><br/>Fly through to connect to your international gates."))

# ATL hub: return to JAX (level 0 in its direction)
b_jax = SLOT["JAX"]
jlat, jlon = dest(*ATL, b_jax, HUB_R)
back_jax = (b_atl + 180) % 360
alat, alon = dest(*JIA, back_jax, EXIT_M)
gates.append(gate("JAX", jlat, jlon, LEVEL, facing=b_jax, radius_m=RING_R, dest_lat=alat, dest_lon=alon, dest_alt_m=JAX_LEVEL,
                  dest_heading=back_jax, description="<b>Gate home to Jacksonville (JAX)</b>"))
# Round-the-world tour (Jim, 2026-11-03): each city also gets a ring to the next city, eastward;
# Rio's onward gate is its ATL ring, which closes the circle.
TOUR = ["NYC", "London", "Paris", "Rome", "Tokyo", "Sydney", "Rio"]
arrival = {}       # city -> (lat, lon, alt, heading) where its gates land you
levels_used = {}
for name, (lat, lon, alt, level) in DEST.items():
    b_out = SLOT[name]
    b_home = bearing(lat, lon, *ATL)
    # far end: return ring between landmark and home, arrival 1,700 m short of the landmark, facing it
    rlat, rlon = dest(lat, lon, b_home, APPROACH_M)
    land_head = (b_home + 180) % 360
    arr_lat, arr_lon = dest(rlat, rlon, land_head, EXIT_M)
    arrival[name] = (arr_lat, arr_lon, alt, land_head)
    # departure ring in the ATL hub, stacked by level
    dlat, dlon = dest(*ATL, b_out, HUB_R)
    dalt = LEVEL
    gates.append(gate(name, dlat, dlon, dalt, facing=b_out, radius_m=RING_R, dest_lat=arr_lat, dest_lon=arr_lon, dest_alt_m=alt,
                      dest_heading=land_head,
                      description=f"<b>Gate to {name}</b><br/>Departure level {round((dalt - ATL_GROUND) / FT):,} ft above the airport."))
    gates.append(gate("ATL", rlat, rlon, alt, facing=b_home, radius_m=RING_R, **hub_arrival,
                      description="<b>Gate back to Atlanta (ATL)</b><br/>Connect there for home (JAX) or another city."))

# next-city rings: beyond the landmark (2 km out toward the next city), so you arrive,
# fly over the landmark and on through the next gate
for i, name in enumerate(TOUR[:-1]):
    lat, lon, alt, _ = DEST[name]
    nxt = TOUR[i + 1]
    b_next = bearing(lat, lon, DEST[nxt][0], DEST[nxt][1])
    b_home = bearing(lat, lon, *ATL)
    sep = abs((b_next - b_home + 180) % 360 - 180)
    assert sep > 40, (name, nxt, sep)      # keep the two rings at a city apart
    nlat, nlon = dest(lat, lon, b_next, APPROACH_M)
    a = arrival[nxt]
    gates.append(gate(nxt, nlat, nlon, alt, facing=b_next, radius_m=RING_R, dest_lat=a[0], dest_lon=a[1],
                      dest_alt_m=a[2], dest_heading=a[3],
                      description=f"<b>Round-the-world tour: next stop {nxt}</b><br/>Or take the ATL gate back to Atlanta."))

# Welcome signs (Jim, 2026-11-03): floating text just ahead of every arrival point
CITY = {"NYC": "New York", "London": "London", "Paris": "Paris", "Rome": "Rome", "Tokyo": "Tokyo",
        "Sydney": "Sydney", "Rio": "Rio de Janeiro"}
# Popular sites (Jim, 2026-11-03): a row of floating icons ahead of each arrival; each popup's SHOW ME
# button draws a red beacon + gold label on the site through the Automation API (proven from a popup).
SITES = {
    "NYC": [("Statue of Liberty", "Liberty Island, 1886.", 40.6892, -74.0445),
            ("1 World Trade Ctr", "One World Trade Center, tallest building in the Western Hemisphere.", 40.7127, -74.0134),
            ("Brooklyn Bridge", "Opened 1883.", 40.7061, -73.9969),
            ("Empire State Building", "Midtown Manhattan, 1931.", 40.7484, -73.9857),
            ("Central Park", "843 acres in the middle of Manhattan.", 40.7829, -73.9654)],
    "London": [("Tower Bridge", "Opened 1894.", 51.5055, -0.0754),
               ("Tower of London", "Home of the Crown Jewels.", 51.5081, -0.0759),
               ("St Paul's Cathedral", "Christopher Wren's dome, 1710.", 51.5138, -0.0984),
               ("London Eye", "Giant wheel on the South Bank.", 51.5033, -0.1196),
               ("Big Ben", "The Elizabeth Tower at Westminster.", 51.5007, -0.1246)],
    "Paris": [("Eiffel Tower", "1889, 330 m tall.", 48.8584, 2.2945),
              ("Arc de Triomphe", "At the centre of the Etoile.", 48.8738, 2.2950),
              ("Louvre", "Home of the Mona Lisa.", 48.8606, 2.3376),
              ("Notre-Dame", "Ile de la Cite.", 48.8530, 2.3499),
              ("Sacre-Coeur", "On the hill of Montmartre.", 48.8867, 2.3431)],
    "Rome": [("Colosseum", "Completed AD 80.", 41.8902, 12.4922),
             ("Roman Forum", "Heart of ancient Rome.", 41.8925, 12.4853),
             ("Trevi Fountain", "Throw in a coin.", 41.9009, 12.4833),
             ("Pantheon", "Nearly 2,000 years old.", 41.8986, 12.4769),
             ("St Peter's Basilica", "Vatican City.", 41.9022, 12.4539)],
    "Tokyo": [("Tokyo Tower", "333 m, 1958.", 35.6586, 139.7454),
              ("Imperial Palace", "Home of the Emperor of Japan.", 35.6852, 139.7528),
              ("Shibuya Crossing", "The world's busiest crossing.", 35.6595, 139.7005),
              ("Senso-ji", "Tokyo's oldest temple, Asakusa.", 35.7148, 139.7967),
              ("Tokyo Skytree", "634 m tall.", 35.7101, 139.8107)],
    "Sydney": [("Sydney Opera House", "Opened 1973.", -33.8568, 151.2153),
               ("Harbour Bridge", "The Coathanger, 1932.", -33.8523, 151.2108),
               ("Botanic Garden", "Royal Botanic Garden, beside the Opera House.", -33.8642, 151.2166),
               ("Taronga Zoo", "Across the harbour.", -33.8436, 151.2411),
               ("Bondi Beach", "Sydney's famous surf beach.", -33.8915, 151.2767)],
    "Rio": [("Christ the Redeemer", "On Corcovado, 1931.", -22.9519, -43.2105),
            ("Sugarloaf Mountain", "Cable car to the top.", -22.9486, -43.1566),
            ("Copacabana Beach", "4 km of beach.", -22.9711, -43.1822),
            ("Ipanema Beach", "Made famous by the song.", -22.9868, -43.2050),
            ("Maracana Stadium", "Home of Brazilian football.", -22.9122, -43.2302)],
    "ATL": [("Georgia Aquarium", "One of the largest aquariums in the world.", 33.7634, -84.3951),
            ("Centennial Park", "Centennial Olympic Park, built for the 1996 Games.", 33.7603, -84.3933),
            ("Coca-Cola Museum", "World of Coca-Cola, the Coca-Cola museum.", 33.7626, -84.3927),
            ("Mercedes-Benz", "Mercedes-Benz Stadium, home of the Falcons.", 33.7554, -84.4008),
            ("Stone Mountain", "Granite dome with the Confederate memorial carving.", 33.8053, -84.1455)],
    "JAX": [("EverBank Stadium", "Home of the Jacksonville Jaguars.", 30.3239, -81.6373),
            ("Jax Beach Pier", "Jacksonville Beach fishing pier.", 30.2917, -81.3900),
            ("St Johns Town Ctr", "St. Johns Town Center shopping district.", 30.2567, -81.5264),
            ("Riverside Arts Mkt", "Riverside Arts Market, under the Fuller Warren Bridge.", 30.3166, -81.6760),
            ("Fort Caroline", "Fort Caroline National Memorial, 1564.", 30.3866, -81.4985)],
}

# v16 (Jim, 2026-11-04 17:49 "put them away ... if they were distant you wouldn't have this effect"):
# the board was 0.9-1.2 km out, so moving a few hundred metres squashed the star row against the rings.
# Now the welcome sign is 6 km out and the star row 5 km out (angles unchanged), so the board stays put
# like scenery on the horizon. Hub: the 8 rings surround you at eye level, so sign AND star row sit above
# them (row +9 deg, sign +14 deg; ring tops are +4.3 deg).
# v15 (Jim, 2026-11-04 17:28 'world gate v15, engage'): ATL hub welcome sign lifted ~12 deg above the
# rings (they circle you at sign height, so v14's sign sat on the London ring name); 'World of Coca-Cola'
# -> 'Coca-Cola Museum' (it wrapped at the hyphen); the v14 pin-hiding attempt removed (Jim: leave the pin).
# v14 (Jim, 2026-11-03 18:51, after his round-the-world tour): no pin under a SHOW ME beacon's name;
# names shortened so ArcGIS Earth does not wrap them (it wraps by text width: a sign over ~18 characters at
# scale 1.4 or a site name over ~19 at 0.9 splits), with a build check; wider gaps between names; no doubled
# name in the star popup; site rows for Atlanta and Jacksonville too; ring names only within SHOW_WITHIN_FT.
# v13 (Jim, 18:02): clicking a star puts its beacon up straight away (no SHOW ME button; clear it by
# unticking it under My Drawings), and each of a city's five sites has its own beacon colour, with the
# menu name in that colour. (v12's CLEAR button sent a no-cors DELETE, which the browser never sends.)
SITE_COLOURS = [(255, 0, 0), (0, 110, 255), (0, 200, 0), (255, 0, 255), (255, 140, 0)]  # red blue green magenta orange
# v12 (Jim, 17:51 screenshot coming out of the ATL gate in Paris): names still ran together and the
# next-city ring (Rome) sat right behind the welcome sign. Each star is now spaced by the length of the
# name before it (measured on Jim's screen: ~0.72 deg per character at label scale 0.9, 1.15 at the sign's 1.4, 9 deg = 175 px),
# and the whole board (sign + row) turns sideways until no ring at that city is behind it.
# v11 (Jim, 17:45 "names and stars don't align"): ArcGIS Earth draws each label a fixed ~80 px ABOVE its
# icon, so in a vertical column every name sat beside the star above it. The menu is now one row, below
# the welcome sign, items 9 deg apart on an arc 900 m out, so each name sits just above its own star.
# v10: same as v9 plus the version in the layer name (Jim: every change gets a new version number).
# Layout v9 (Jim, 2026-11-03 17:25): spread out; welcome sign at the height you come out at, straight ahead.
# Layout v8 (Jim, 2026-11-03): KML text is a fixed size on screen, so signs and menus only show near
# each arrival (Region LOD, as Object Factory "Hide above"); welcome sign further ahead and higher;
# sites as a vertical menu board off to the left so labels do not collide.
SHOW_WITHIN_FT = 20000.0     # ring names disappear beyond about 4 miles
# v17 (Jim, 2026-11-04 17:58 'Rio is problematic, the objects will disappear before you can see all in one
# shot'): ArcGIS Earth's view is ~78 deg wide (measured on Jim's v16 hub screenshot: London/Paris rings at
# +-22.5 deg sat where a 78 deg view puts them), and a one-row board reached 79 deg (Rio, NYC). Boards are
# now TWO rows (first 3 sites, then 2), about half as wide; rows 4 km out (room for the second row above the
# ground); welcome sign just above the rows; boards show from twice as far so backing off does not hide them.
# v18 (2026-11-04, from tools/preview_view.py - the viewer model fitted to Jim's Rio v17 screenshot to 5 px):
# the board now keeps clear of each ring AND its name (names sit beside the ring), and prefers a turn that
# keeps the whole board inside the ~78 deg view when you look straight ahead (NYC's v17 board ran off-screen).
VIEW_HALF_DEG = 39.0
BOARD_WITHIN_FT = 40000.0    # v17: signs + star rows (was 20,000)
SIGN_AHEAD_M = 6000.0        # v16
MENU_AHEAD_M = 4000.0        # v17 (v16: 5,000)
# v19 (Jim, 2026-11-04 18:15, London at 1,500 ft: 'the bottom 2 are lost in imagery when we got all that blue
# sky to work with'): seen from arrival height the horizon is at eye level, so anything below eye level sits on
# busy imagery. The whole board now sits in the sky. (Model fit to Jim's London shot: 2.3 px rms.)
CITY_SIGN_DEG, CITY_ROW_DEG = 10.5, (6.0, 2.0)        # v19 (v17: 3.5, (-0.5, -4.5)): degrees above eye level
HUB_SIGN_DEG, HUB_ROW_DEG = 17.5, (13.0, 9.0)         # v17: hub board above the 8 rings (ring tops ~4.3 deg)
ROWS = ((0, 1, 2), (3, 4))   # v17: which sites go on each row


DEG_PER_CHAR_SITE = 0.72      # label scale 0.9 (site names)
DEG_PER_CHAR_SIGN = 1.15      # label scale 1.4 (welcome sign)
GAP_DEG, RING_CLEAR_DEG = 5.0, 12.0   # v14: gap 3 -> 5 (Copacabana Beach ran into Ipanema Beach)


def distance_m(lat1, lon1, lat2, lon2):
    la1, la2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(h)))


def _ang(a):
    return (a + 180) % 360 - 180


def _up(dist_m, deg):
    return dist_m * math.tan(math.radians(deg))


def city_extras(key, sign_text, alat_, alon_, aalt, ahead, sites, hub=False):
    sign_deg, row_deg = (HUB_SIGN_DEG, HUB_ROW_DEG) if hub else (CITY_SIGN_DEG, CITY_ROW_DEG)
    rows = []                                   # per row: [(site index, offset deg from row's left end)], width
    for idx in ROWS:
        idx = [k for k in idx if k < len(sites)]
        offs, x = [], 0.0
        for k in idx:
            offs.append((k, x)); x += DEG_PER_CHAR_SITE * len(sites[k][0]) + GAP_DEG
        w = (offs[-1][1] + DEG_PER_CHAR_SITE * len(sites[idx[-1]][0])) if idx else 0.0
        rows.append((offs, w))
    sign_w = DEG_PER_CHAR_SIGN * len(sign_text)
    width = max([sign_w] + [w for _, w in rows])
    # each nearby ring blocks the bearings from its left edge to the end of its name (names sit beside the ring)
    blocked = []
    for g in gates:
        if abs(g["lat"] - alat_) > 0.06 or abs(g["lon"] - alon_) > 0.08:
            continue
        b = bearing(alat_, alon_, g["lat"], g["lon"])
        dist = max(1.0, distance_m(alat_, alon_, g["lat"], g["lon"]))
        rad = math.degrees(math.atan(g["radius_m"] / dist))
        llat, llon = dest(g["lat"], g["lon"], (g["facing"] + 90) % 360, g["radius_m"] + 40)
        lb = bearing(alat_, alon_, llat, llon)
        name_w = DEG_PER_CHAR_SIGN * max(len(g["name"]), 8)        # ring name (scale 1.4) / "2,530 ft" line
        rel = _ang(b - ahead)
        if abs(rel) > 100:                       # behind you (e.g. the ATL ring you just came out of)
            continue
        lrel = rel + _ang(lb - b)
        lo_ = min(rel - rad, lrel)
        hi_ = max(rel + rad, lrel + name_w)
        blocked.append((lo_ - 4.0, hi_ + 4.0))
    def clear(c):
        return all(c + width / 2 < lo_ or c - width / 2 > hi_ for lo_, hi_ in blocked)
    cands = sorted(range(-90, 91), key=abs)
    centre = 0 if hub else next((c for c in cands if clear(c) and abs(c) + width / 2 <= VIEW_HALF_DEG), None)
    if centre is None:                           # v18: no side gap fits in the view -> lift the board over the rings
        centre, sign_deg, row_deg = 0, HUB_SIGN_DEG, HUB_ROW_DEG
    board = (ahead + centre) % 360
    parts = [welcome_sign(sign_text, alat_, alon_, aalt, (board - sign_w / 2) % 360, ahead_m=SIGN_AHEAD_M,
                          above_m=_up(SIGN_AHEAD_M, sign_deg))]
    for (offs, w), deg in zip(rows, row_deg):
        for k, off in offs:
            sname, blurb, slat, slon = sites[k]
            mlat, mlon = dest(alat_, alon_, (board + off - w / 2) % 360, MENU_AHEAD_M)
            parts.append(site_placemark(f"site-{key.lower()}-{k + 1}", sname, blurb, slat, slon, mlat, mlon,
                                        aalt + _up(MENU_AHEAD_M, deg), rgb=SITE_COLOURS[k % len(SITE_COLOURS)], auto=True))
    lowest = aalt + _up(MENU_AHEAD_M, min(row_deg))
    print(f"{key:7s} board turned {centre:+4d} deg, {width:4.1f} deg wide, lowest star {lowest:5.0f} m above sea level")
    return lod_folder(f"{sign_text} (near view)", "\n".join(parts), alat_, alon_, aalt, BOARD_WITHIN_FT)

SIGN = {"NYC": "Welcome to NYC", "London": "Welcome to London", "Paris": "Welcome to Paris", "Rome": "Welcome to Rome",
        "Tokyo": "Welcome to Tokyo", "Sydney": "Welcome to Sydney", "Rio": "Welcome to Rio",
        "ATL": "Welcome to Atlanta", "JAX": "Welcome to JAX"}
MAX_SIGN_CHARS, MAX_SITE_CHARS = 18, 19      # longer text wraps onto two lines in ArcGIS Earth
SEEN_ON_ONE_LINE = {"Empire State Building"}   # longer, but narrow letters: Jim saw it on one line (v13)
too_long = [s for s in SIGN.values() if len(s) > MAX_SIGN_CHARS] + \
           [s[0] for v in SITES.values() for s in v if len(s[0]) > MAX_SITE_CHARS and s[0] not in SEEN_ON_ONE_LINE]
if too_long:
    sys.exit(f"Labels too long (would wrap in ArcGIS Earth): {too_long}")
extras = [city_extras(n, SIGN[n], *arrival[n], SITES[n]) for n in TOUR]
# hub: sign and rows sit above the 8 rings (v16/v17)
extras.append(city_extras("ATL", SIGN["ATL"], ATL[0], ATL[1], LEVEL, HUB_ARRIVAL_HEADING, SITES["ATL"], hub=True))
extras.append(city_extras("JAX", SIGN["JAX"], alat, alon, JAX_LEVEL, back_jax, SITES["JAX"]))
SITE_ICON = Path(__file__).resolve().parent / "samples" / "site_icon.png"
write_kmz(sys.argv[1], f"World Gates {GATES_VERSION} - JAX ATL hub", gates, red_backs=True, side_labels=True, name_scale=1.4, alt_scale=1.0,
          extra_kml="\n".join(extras), extra_files={"icons/site.png": SITE_ICON.read_bytes()}, label_within_ft=SHOW_WITHIN_FT)
for g in gates:
    print(f"{g['name']:7s} at {g['lat']:.4f},{g['lon']:.4f} {round(g['alt_m'] / FT):>6,} ft facing {g['facing']:5.1f}")
