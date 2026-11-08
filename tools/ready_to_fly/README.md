# Ready to Fly - the shared "get this PC ready" launcher step

`Ready_To_Fly.ps1` v1.0.1 (Windows PowerShell 5.1 compatible, ASCII, ship it CRLF inside `System Files`) is called by a package's one obvious `.bat`. It checks and fixes, in plain words:

0. **Internet** (heads-up only): `Get-NetConnectionProfile`, then the NCSI probe `http://www.msftconnecttest.com/connecttest.txt` = `Microsoft Connect Test` (anything else = Wi-Fi sign-in page), fallback HTTPS HEAD to python.org. Offline = "online basemaps won't load, your TPKX still work".
1. **Python 3.9+**: remembered `python_path.txt`, `py -3`, `python` on PATH (ignores the `WindowsApps` Store stub), `%LOCALAPPDATA%\Programs\Python\Python3*`, Program Files. Missing -> asks, then per-user install: `winget install -e --id Python.Python.3.14 --scope user --silent ...` (then 3.13), else the python.org installer after `Get-AuthenticodeSignature` = Valid + Python Software Foundation, `/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1 Include_tcltk=1`. Found by folder scan afterwards (PATH is not refreshed in the running window).
2. **Libraries** `-Packages "pillow,pyserial" -Imports "PIL,serial"`: `import` test, `pip install --user` only if missing (needs internet).
3. **ArcGIS Earth** (`-NeedEarth`): `ArcGIS_Earth_path.txt`, known paths (incl. `C:\Program Files\ArcGIS\ArcGIS Earth\bin\ArcGISEarth.exe`), Uninstall registry keys, folder search. Missing -> offers Esri's download page. Never installs it. Starts it if not running.
4. **Automation API** (`-NeedApi`): waits up to `-ApiWaitS` (90) for `http://localhost:8000/arcgisearth/camera` (no proxy). Process up but no answer -> "Settings > Advanced application settings > tick Enable Automation API" and Enter to re-check.

Other switches: `-NeedTk` (warn if no Tkinter), `-EarthOnly` (find + save the ArcGIS Earth path only; the taskbar shortcut maker uses it via `Fly_ArcGIS_Earth.bat /find`), `-Unattended` (no questions; tests). Exit 0 = ready, 1 = stopped. Log: `Ready_To_Fly_log.txt` beside it.

Tested here with PowerShell 7.4.6 on Linux (stand-in ArcGIS Earth + mock API): no Python, Python found, library missing offline, Earth missing, Earth found + API up, Earth running + API off, Earth not running, /find. **Not testable here:** winget, the signature check, NCSI cmdlet, registry, Windows PowerShell 5.1 itself - Jim's Windows run is the test.

First used in **EarthStick 1.3.8 TEST** (branch `earthstick-v1.3.8-test`, `test-builds/EarthStick_v1.3.8_TEST.zip`, program = 1.3.6 byte-identical). After Jim accepts, roll it into the other packages (each a launcher-only x.y.z bump).

## v1.0.1 (EarthStick 1.3.9 TEST, 2026-11-08) - after Jim's worst-case run

Jim's old Windows 10 laptop (Python uninstalled, offline for weeks): blank window for several minutes (PowerShell cold start + Defender scanning), then Python installed by itself and EarthStick flew. Changes: the .bat prints a 'please wait - Defender may slow the PC - do not close this window' line before PowerShell; 'several minutes' wording; '...still installing (N min)' every minute; winget gets 20 min (`-WingetMinutes`) then the python.org installer; internet probe 4 s limits; download time limits; winget output saved in the log; **only one Ready to Fly at a time** (named mutex `Local\ReadyToFly_single_instance`; a second copy says so and exits 1).
