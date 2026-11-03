"""Build the World Gate network (Jim, 2026-11-02): JAX (over JIA) -> ATL hub (over Hartsfield-Jackson)
-> seven landmark destinations, each with an "ATL" return ring. All gates are one-way with explicit
landing spots, so ring names can repeat (every return ring is called ATL).

python3 build_world_gates.py <output.kmz>
"""
import sys
from make_gate_kmz import gate, write_kmz, dest, bearing, welcome_sign, site_placemark, lod_folder
from pathlib import Path

GATES_VERSION = "v12"           # Jim: every change gets a new version number
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
            ("One World Trade Center", "Tallest building in the Western Hemisphere.", 40.7127, -74.0134),
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
               ("Royal Botanic Garden", "Beside the Opera House.", -33.8642, 151.2166),
               ("Taronga Zoo", "Across the harbour.", -33.8436, 151.2411),
               ("Bondi Beach", "Sydney's famous surf beach.", -33.8915, 151.2767)],
    "Rio": [("Christ the Redeemer", "On Corcovado, 1931.", -22.9519, -43.2105),
            ("Sugarloaf Mountain", "Cable car to the top.", -22.9486, -43.1566),
            ("Copacabana Beach", "4 km of beach.", -22.9711, -43.1822),
            ("Ipanema Beach", "Made famous by the song.", -22.9868, -43.2050),
            ("Maracana Stadium", "Home of Brazilian football.", -22.9122, -43.2302)],
}

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
SHOW_WITHIN_FT = 20000.0     # signs + menus disappear beyond about 4 miles
SIGN_AHEAD_M, SIGN_ABOVE_M = 1200.0, 0.0
MENU_AHEAD_M, MENU_STEP_DEG, MENU_BELOW_M = 900.0, 9.0, 100.0


DEG_PER_CHAR_SITE = 0.72      # label scale 0.9 (site names)
DEG_PER_CHAR_SIGN = 1.15      # label scale 1.4 (welcome sign)
GAP_DEG, RING_CLEAR_DEG = 3.0, 12.0


def _ang(a):
    return (a + 180) % 360 - 180


def city_extras(key, sign_text, alat_, alon_, aalt, ahead, sites):
    # star offsets (deg, relative to the board's left end); a label is drawn to the right of its star
    offs, x = [], 0.0
    for sname, *_ in sites:
        offs.append(x); x += DEG_PER_CHAR_SITE * len(sname) + GAP_DEG
    sign_w = DEG_PER_CHAR_SIGN * len(sign_text)
    row_w = (offs[-1] + DEG_PER_CHAR_SITE * len(sites[-1][0])) if sites else 0.0
    width = max(row_w, sign_w)
    near = [bearing(alat_, alon_, g["lat"], g["lon"]) for g in gates
            if abs(g["lat"] - alat_) < 0.06 and abs(g["lon"] - alon_) < 0.08]
    def clear(c):
        return all(abs(_ang(b - (ahead + c))) > width / 2 + RING_CLEAR_DEG for b in near)
    centre = next((c for k in range(0, 91, 5) for c in ((k, -k) if k else (0,)) if clear(c)), 0)
    board = (ahead + centre) % 360
    parts = [welcome_sign(sign_text, alat_, alon_, aalt, (board - sign_w / 2) % 360, ahead_m=SIGN_AHEAD_M, above_m=SIGN_ABOVE_M)]
    for i, (sname, blurb, slat, slon) in enumerate(sites):
        off = offs[i] - row_w / 2
        mlat, mlon = dest(alat_, alon_, (board + off) % 360, MENU_AHEAD_M)
        parts.append(site_placemark(f"site-{key.lower()}-{i + 1}", sname, blurb, slat, slon, mlat, mlon,
                                    aalt - MENU_BELOW_M))
    print(f"{key:7s} board turned {centre:+4d} deg, {width:4.1f} deg wide")
    return lod_folder(f"{sign_text} (near view)", "\n".join(parts), alat_, alon_, aalt, SHOW_WITHIN_FT)


extras = [city_extras(n, f"Welcome to {CITY[n]}", *arrival[n], SITES[n]) for n in TOUR]
extras.append(city_extras("ATL", "Welcome to Atlanta (ATL)", ATL[0], ATL[1], LEVEL, HUB_ARRIVAL_HEADING, []))
extras.append(city_extras("JAX", "Welcome home to Jacksonville", alat, alon, JAX_LEVEL, back_jax, []))
SITE_ICON = Path(__file__).resolve().parent / "samples" / "site_icon.png"
write_kmz(sys.argv[1], f"World Gates {GATES_VERSION} - JAX ATL hub", gates, red_backs=True, side_labels=True, name_scale=1.4, alt_scale=1.0,
          extra_kml="\n".join(extras), extra_files={"icons/site.png": SITE_ICON.read_bytes()})
for g in gates:
    print(f"{g['name']:7s} at {g['lat']:.4f},{g['lon']:.4f} {round(g['alt_m'] / FT):>6,} ft facing {g['facing']:5.1f}")
