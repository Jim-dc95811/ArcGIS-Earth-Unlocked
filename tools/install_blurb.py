"""Insert / refresh the standard "Installing <tool> - read this first" box under the H1 of every manual (idempotent;
between <!-- install-blurb:start/end --> markers). Run from the repos root (all repos side by side), then rebuild the PDFs
with md2pdf.py and put them in the zips with add_manual_to_zip.py. Jim 2026-11-08: installation blurb at the top of every manual."""
import re, sys
MARK_START = "<!-- install-blurb:start -->"
MARK_END = "<!-- install-blurb:end -->"
COMMON = """> 1. **Extract All first:** right-click the downloaded zip > **Extract All**, then open the new folder. (Double-clicking files while they are still inside the zip does not work.)
> 2. **Double-click `{bat}`** - the only .bat in the folder. This manual sits right next to it. The **System Files** folder holds the program - leave it alone.
> 3. **Blue "Windows protected your PC" box?** Click **More info**, then **Run anyway**. It only asks the first time. (Or, before extracting: right-click the zip > **Properties** > tick **Unblock** > **OK**.)
> 4. **Python - nothing to install by hand.** If Python is missing, the window asks **Install Python now? [Y/N]**: type **Y** and press Enter. It installs just for you (no admin needed){libs}. On an older PC this can take several minutes and Windows Defender may make the PC look frozen - **do not close the window**.
{extra}>
> Something stops it? The window says what to do in plain words, and keeps a log in `System Files\\Ready_To_Fly_log.txt`. On a work computer that blocks installs, ask IT to install Python 3 from python.org."""
EARTH = "**ArcGIS Earth** (free from Esri: https://www.esri.com/en-us/arcgis/products/arcgis-earth/downloads)"
API = "Settings > Advanced application settings > tick **Enable Automation API**"
TOOLS = {
 "EarthStick/docs/USER_GUIDE.md": ("EarthStick", "Fly_ArcGIS_Earth.bat", "",
   [f"Install {EARTH}. The .bat starts it for you and checks its Automation API is on ({API}).", "Plug the joystick in by USB - no driver needed.", "Gate files work only from the **Gates** folder: add them with the **+ ADD GATES** button (or World Gate Maker). ArcGIS Earth's own Add Data only draws them."]),
 "EarthStick/docs/WORLD_GATE_MAKER.md": ("World Gate Maker", "World_Gate_Maker.bat", "",
   ["**Needs EarthStick:** start EarthStick 2.0 at least once first - it tells World Gate Maker where its **Gates** folder is. With EarthStick running, new gates appear in it within seconds (no restart).", f"To see the gates you need {EARTH}."]),
 "ArcGIS-Earth-Object-Factory/docs/OBJECT_FACTORY_USER_MANUAL.md": ("Object Factory", "Run_Object_Factory.bat", "",
   [f"To see your objects you need {EARTH}: drag the KMZ it makes onto the map."]),
 "Point-Maps/docs/USER_GUIDE.md": ("PointLayer", "PointLayer.bat", "",
   ["An internet connection (it downloads public map layers).", f"To see the result you need {EARTH}."]),
 "Parcel100/USER_MANUAL.md": ("Parcel100", "Parcel100.bat", "",
   ["An internet connection (it downloads public parcel data) and a Master 4 box (for example `82w, 81w, 30n, 31n`).", f"To see the parcels you need {EARTH}."]),
 "Picture-World-Maker/docs/USER_MANUAL.md": ("Picture World Maker", "Start Picture World Maker.bat", " - and the Pillow picture library too",
   [f"To fly over your picture you need {EARTH}.", "Giant pictures need room: free disk space of a few times the picture's size, and plenty of memory."]),
 "QGIS-Mbtile-to-ArcGIS-Earth-TPKX/MB2TPKX_USER_MANUAL.md": ("the MBTiles to TPKX Converter", "mb2tpkx.bat", " - and the Pillow picture library too",
   ["An MBTiles map file to convert (for example one made in QGIS).", f"To open the TPKX it makes you need {EARTH}."]),
 "QGIS-Mbtile-to-ArcGIS-Earth-TPKX/MASTER4_GRID_MAKER.md": ("Master 4 Grid Maker", "Master4_Grid_Maker.bat", " - and the Pillow picture library too",
   ["Its files are saved in `C:\\downloads`."]),
 "ArcGIS-Earth-Offline-Maps-Chartplotting/docs/PRAVE_ME_TRACKER.md": ("the PRAVE / ME Tracker", "START_TRACKER.bat", " - and the pyserial library too",
   [f"Install {EARTH}. The .bat starts it for you and checks its Automation API is on ({API}).", "The serial port settings (`INPUT_PORT`, default COM12, and `INPUT_BAUD`) are at the top of `System Files\\PRAVE_ME_Tracker.py`."]),
}
def block(tool, bat, libs, extras):
    ex = "".join(f"> {5+i}. {e}\n" for i, e in enumerate(extras))
    return f"{MARK_START}\n> ### Installing {tool} - read this first\n>\n" + COMMON.format(bat=bat, libs=libs, extra=ex) + f"\n{MARK_END}\n"
for path, (tool, bat, libs, extras) in TOOLS.items():
    s = open(path, encoding="utf-8").read()
    if MARK_START in s:                       # 2.0: replace in place (idempotent - earlier runs added a blank line each time)
        s = re.sub(re.escape(MARK_START) + r".*?" + re.escape(MARK_END) + r"\n", lambda m: block(tool, bat, libs, extras), s, count=1, flags=re.S)
    else:
        lines = s.split("\n")
        h = next(i for i, l in enumerate(lines) if l.startswith("# "))
        lines[h+1:h+1] = ["", block(tool, bat, libs, extras)]
        s = "\n".join(lines)
    open(path, "w", encoding="utf-8").write(s)
    print("ok", path)
