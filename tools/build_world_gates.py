"""Build the World Gate network (Jim, 2026-11-02): JAX (over JIA) -> ATL hub (over Hartsfield-Jackson)
-> seven landmark destinations, each with an "ATL" return ring. All gates are one-way with explicit
landing spots, so ring names can repeat (every return ring is called ATL).

python3 build_world_gates.py <output.kmz>
"""
import sys
from make_gate_kmz import gate, write_kmz, dest, bearing, welcome_sign, site_placemark
from pathlib import Path

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
APPROACH_M = 900.0               # return ring sits this far from the landmark, toward ATL

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
    # far end: return ring between landmark and home, arrival 600 m short of the landmark, facing it
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

# next-city rings: beyond the landmark (900 m out toward the next city), so you arrive,
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
signs = [welcome_sign(f"Welcome to {CITY[n]}", *arrival[n]) for n in TOUR]
signs.append(welcome_sign("Welcome to Atlanta (ATL)", ATL[0], ATL[1], LEVEL, HUB_ARRIVAL_HEADING))
signs.append(welcome_sign("Welcome home to Jacksonville", alat, alon, JAX_LEVEL, back_jax))
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
MENU_AHEAD_M = 180.0     # the menu row floats this far ahead of the arrival point
MENU_SPACING_M = 70.0    # side-by-side spacing of the menu icons
MENU_BELOW_M = 30.0      # a little below eye level (the welcome sign is above)
menus = []
for city, sites in SITES.items():
    alat_, alon_, aalt, ahead = arrival[city]
    clat, clon = dest(alat_, alon_, ahead, MENU_AHEAD_M)
    n = len(sites)
    for i, (sname, blurb, slat, slon) in enumerate(sites):
        off = (i - (n - 1) / 2) * MENU_SPACING_M
        plat, plon = dest(clat, clon, (ahead + 90) % 360 if off >= 0 else (ahead + 270) % 360, abs(off))
        menus.append(site_placemark(f"site-{city.lower()}-{i + 1}", sname, blurb, slat, slon, plat, plon, aalt - MENU_BELOW_M))
SITE_ICON = Path(__file__).resolve().parent / "samples" / "site_icon.png"
write_kmz(sys.argv[1], "World Gates - JAX ATL hub", gates, red_backs=True, side_labels=True, name_scale=1.4, alt_scale=1.0,
          extra_kml="\n".join(signs + menus), extra_files={"icons/site.png": SITE_ICON.read_bytes()})
for g in gates:
    print(f"{g['name']:7s} at {g['lat']:.4f},{g['lon']:.4f} {round(g['alt_m'] / FT):>6,} ft facing {g['facing']:5.1f}")
