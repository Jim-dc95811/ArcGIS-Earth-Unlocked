"""Build the World Gate network (Jim, 2026-11-02): JAX (over JIA) -> ATL hub (over Hartsfield-Jackson)
-> seven landmark destinations, each with an "ATL" return ring. All gates are one-way with explicit
landing spots, so ring names can repeat (every return ring is called ATL).

python3 build_world_gates.py <output.kmz>
"""
import sys
from make_gate_kmz import gate, write_kmz, dest, bearing

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
levels_used = {}
for name, (lat, lon, alt, level) in DEST.items():
    b_out = SLOT[name]
    b_home = bearing(lat, lon, *ATL)
    # far end: return ring between landmark and home, arrival 600 m short of the landmark, facing it
    rlat, rlon = dest(lat, lon, b_home, APPROACH_M)
    land_head = (b_home + 180) % 360
    arr_lat, arr_lon = dest(rlat, rlon, land_head, EXIT_M)
    # departure ring in the ATL hub, stacked by level
    dlat, dlon = dest(*ATL, b_out, HUB_R)
    dalt = LEVEL
    gates.append(gate(name, dlat, dlon, dalt, facing=b_out, radius_m=RING_R, dest_lat=arr_lat, dest_lon=arr_lon, dest_alt_m=alt,
                      dest_heading=land_head,
                      description=f"<b>Gate to {name}</b><br/>Departure level {round((dalt - ATL_GROUND) / FT):,} ft above the airport."))
    gates.append(gate("ATL", rlat, rlon, alt, facing=b_home, radius_m=RING_R, **hub_arrival,
                      description="<b>Gate back to Atlanta (ATL)</b><br/>Connect there for home (JAX) or another city."))

write_kmz(sys.argv[1], "World Gates - JAX ATL hub", gates, red_backs=True, side_labels=True, name_scale=1.4, alt_scale=1.0)
for g in gates:
    print(f"{g['name']:7s} at {g['lat']:.4f},{g['lon']:.4f} {round(g['alt_m'] / FT):>6,} ft facing {g['facing']:5.1f}")
