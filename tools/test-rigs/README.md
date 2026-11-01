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
| `earthstick_proxy_check.py` | EarthStick localhost API with a system proxy set | edit the path, run with a label argument |
| `prave_tracker_rig.py` + `prave_serial_sim.py` | PRAVE/ME tracker: simulated serial stream through a pty, mock Automation API (camera + drawings) | needs pyserial (clone github.com/pyserial/pyserial tag v3.5, use `PYTHONPATH`); edit the version paths |
| `master4_test_v31.py` | Master 4 v3 vs v3.1 (TXT + TIF byte compare, input handling) | edit `V3`/`V31` |
| `object_factory_test_v11.py`, `object_factory_load.py` | Object Factory v1.1 clipboard parsing, batch errors, safe writes, outputs vs v1.0 | edit the paths |

Not saved: the mb2tpkx v1.1 synthetic tests (run inline at the time). For a real-data check, ask Jim for an MBTiles file (he supplied `bryceville_7_layer_mbtile.mbtiles`, 97 MB, which converts to 6,461 tiles in 14 bundles).
