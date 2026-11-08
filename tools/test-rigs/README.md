# Test rigs (for Claude sessions)

These are the regression and hardening rigs used during the 2026-10-31 / 11-01 hardening releases. They run on Linux without ArcGIS Earth, a joystick or a radio: each one loads the real program, replaces Tkinter / hardware / time with stand-ins, and talks to a small mock server. They are working tools, not polished tests. Read a rig before running it.

Common tricks inside them:
- **Tkinter stub:** a fake `tkinter` module with `Tk = type("Tk", (), {})` (a plain `object` causes an MRO error), registered in `sys.modules` before `exec` of the program.
- **No sleeping:** the program's `time` is replaced with `SimpleNamespace(sleep=lambda s: None)` or a fake clock.
- **Mock ArcGIS services:** `ThreadingHTTPServer` on port 0 serving FeatureServer / Automation API JSON. The random port ends up in outputs (Parcel100 `source` field), so normalize it before byte comparisons.
- **Old vs new:** most rigs take the program path as an argument so the same scenario can be run against the released and the dev version and the outputs compared byte for byte.

Paths: some rigs still contain the original session's absolute paths (`/home/claude/repos/...`, `/home/claude/dev/<tool>_v<ver>/...`). Edit those lines to point at the versions being compared.

| Rig | Tool | How to run |
|---|---|---|
| `parcel100_rig_v14.py` | Parcel100 1.4-style build loop | `python3 parcel100_rig_v14.py <Parcel100.py> normal\|interrupted_write_then_resume\|server_drops_features\|big_batch_504` |
| `parcel100_rig_v15.py` | Parcel100 1.5 real `_build_worker` | same scenarios plus `url_changed` |
| `parcel100_discovery.py` | Parcel100 1.5 service-root discovery | `python3 parcel100_discovery.py <Parcel100.py>` |
| `pointlayer_rig.py`, `pointlayer_test_v14.py` | PointLayer 1.3 vs 1.4 (mock layer 458) | edit `V13`/`V14`, then `python3 pointlayer_test_v14.py` |
| `earthstick_rig.py` | EarthStick: scripted joystick + fake clock + mock camera API; compares PUT streams | `python3 earthstick_rig.py <EarthStick.py> <scenario>` |
| `earthstick_rig_trigger.py` | EarthStick 1.2 trigger-click: scripted trigger presses (incl. a bounce) with a fake clicker; checks clicks and that camera PUTs match 1.1 | `python3 earthstick_rig_trigger.py <EarthStick.py> trigger` |
| `earthstick_rig_wormhole.py` | EarthStick 1.3 wormholes: gate 1 km ahead of the scripted flight, partner over NYC; checks one jump, arrival point/heading, no bounce back | `python3 earthstick_rig_wormhole.py <EarthStick.py>` |
| `earthstick_rig_dropper.py` | EarthStick 1.3.6 Gate Dropper: copies EarthStick.py + gate_dropper.py into a temp System Files folder, presses Button 2 at two places (camera moved like mouse navigation), checks the KMZ in Gates, gates armed at the hover height, the add-layer request, then flies through the new gate: one jump, lands 300 m past the partner | `python3 earthstick_rig_dropper.py <EarthStick.py>` |
| `earthstick_rig_pickup.py` | EarthStick 1.3.11 Gates-folder pickup + ADD GATES: a gate file appears mid-flight (half-written first), is armed and shown once within 4 s, flown through (one jump), removed (layer deleted, no jump), ADD GATES copy / duplicate / no-gates file, Gate Dropper pair shown once, last-flown note. Also: the other EarthStick rigs now give the program the real `os` (named 'nt') and a temp `LOCALAPPDATA`, and the dropper rig presses `DROP_BUTTON` | `python3 earthstick_rig_pickup.py <EarthStick.py>` |
| `earthstick_proxy_check.py` | EarthStick localhost API with a system proxy set | edit the path, run with a label argument |
| `prave_tracker_rig.py` + `prave_serial_sim.py` | PRAVE/ME tracker: simulated serial stream through a pty, mock Automation API (camera + drawings) | needs pyserial (clone github.com/pyserial/pyserial tag v3.5, use `PYTHONPATH`); edit the version paths |
| `master4_test_v31.py` | Master 4 v3 vs v3.1 (TXT + TIF byte compare, input handling) | edit `V3`/`V31` |
| `object_factory_test_v12.py` | Object Factory v1.2 vs v1.1: regression (identical except name popups on empty Info), Hide above cube Region, batch `hide_above_ft` | `python3 object_factory_test_v12.py <v1.1.py> <v1.2.py> <icons dir> <samples dir>` (set `WORK` for the output folder) |
| `picture_world_maker_rig.py` | Picture World Maker pipeline end to end without Windows or QGIS: stand-in QGIS folder (shell scripts named like the real tools) for the QGIS route - TPKX, Both, MBTiles, zoom-24 refusal, cancel while QGIS is silent - plus photo mode with QGIS pointing nowhere; reports stages, files and leftover temp folders (must be 0) | `python3 picture_world_maker_rig.py "<repo>/Picture World Maker/System Files" --mbtiles demo_lon_41.mbtiles [--photo picture.jpg] [--zmax 15]` (Jim's `demo_lon_41.mbtiles` and `Kings_reach_panorama_1.jpg` were the 2026-11 test files; a small photo makes the photo cancel run finish before 5 s - use the big one to test cancel) |
| `object_factory_test_v11.py`, `object_factory_load.py` | Object Factory v1.1 clipboard parsing, batch errors, safe writes, outputs vs v1.0 | edit the paths |

Not saved: the mb2tpkx v1.1 synthetic tests (run inline at the time). For a real-data check, ask Jim for an MBTiles file (he supplied `bryceville_7_layer_mbtile.mbtiles`, 97 MB, which converts to 6,461 tiles in 14 bundles).
