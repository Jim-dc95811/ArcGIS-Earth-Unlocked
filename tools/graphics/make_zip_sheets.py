"""'What's in the zip' sheets for every tool (Jim, 2026-11-04: "a matching file explanation sheet alongside every zip").

Same look as earthstick_whats_in_the_folder.html (the EarthStick sheet stays hand-made there).
Each sheet: one card per thing in the extracted zip, dashed cards for files the tool MAKES, three tips.
Facts come from the zips themselves (checked 2026-11-04) - update a sheet whenever its zip changes.

Run:  python3 make_zip_sheets.py OUTDIR   -> OUTDIR/<key>.html, <key>.png (1600 wide), <key>_full.png (2x)
"""
import html
import pathlib
import sys

FILE = '<path d="M22 8 h58 l26 26 v86 h-84 z" fill="#f4f7fb" stroke="#9fb8d4" stroke-width="3"/><path d="M80 8 v26 h26" fill="#cfd9e6" stroke="#9fb8d4" stroke-width="3"/>'
FOLDER = ('<path d="M8 30 a6 6 0 0 1 6 -6 h30 l10 10 h60 a6 6 0 0 1 6 6 v70 a6 6 0 0 1 -6 6 h-100 a6 6 0 0 1 -6 -6 z" fill="#f2c94c" stroke="#a37a12" stroke-width="3"/>'
          '<path d="M8 46 h112" stroke="#d9a92e" stroke-width="3"/>')
GLOBE = ('<circle cx="{x}" cy="{y}" r="{r}" fill="#2a7fd4" stroke="#0b1d33" stroke-width="3"/>'
         '<path d="M{a} {b} q{c} -{d} {e} 2 q{f} {d} {e} 0" fill="none" stroke="#7fd36b" stroke-width="5" stroke-linecap="round"/>')


def globe(x, y, r):
    return GLOBE.format(x=x, y=y, r=r, a=x - r * 0.75, b=y - r * 0.15, c=r * 0.35, d=r * 0.25, e=r * 0.75, f=r * 0.4)


ICONS = {
    # START HERE launcher: page with a gold play button
    "go": FILE + '<circle cx="64" cy="76" r="30" fill="#ffd400" stroke="#0b1d33" stroke-width="3"/><path d="M55 60 L80 76 L55 92 Z" fill="#0b1d33"/>',
    # the program: page with lines and a "hands off" sign
    "py": FILE + '<g stroke="#9fb8d4" stroke-width="4" stroke-linecap="round"><path d="M36 50 h48"/><path d="M36 64 h56"/><path d="M36 78 h40"/><path d="M36 92 h52"/></g>'
          '<circle cx="94" cy="98" r="22" fill="#12325a" stroke="#ffd400" stroke-width="4"/><rect x="80" y="94" width="28" height="8" rx="3" fill="#ffd400" transform="rotate(45 94 98)"/>',
    # program with settings at the top: page with a highlighted first line + slider knobs
    "pyset": FILE + '<rect x="30" y="40" width="64" height="16" rx="4" fill="#ffd400"/><text x="34" y="52" font-family="Consolas,monospace" font-weight="700" font-size="11" fill="#0b1d33">COM12</text>'
             '<g stroke="#9fb8d4" stroke-width="4" stroke-linecap="round"><path d="M36 72 h48"/><path d="M36 86 h56"/><path d="M36 100 h40"/></g>',
    # text notes to read: page with lines + "TXT"
    "txt": FILE + '<g stroke="#9fb8d4" stroke-width="4" stroke-linecap="round"><path d="M34 52 h56"/><path d="M34 66 h60"/><path d="M34 80 h48"/></g>'
           '<rect x="34" y="92" width="46" height="20" rx="4" fill="#2d5f94"/><text x="40" y="107" font-family="Poppins" font-size="14" fill="#fff">TXT</text>',
    # example list: page with rows of small icons and commas
    "list": FILE + '<g font-family="Consolas,monospace" font-size="11" fill="#2d5f94" font-weight="700"><text x="32" y="54">fuel,30.41,</text><text x="32" y="72">heli,30.39,</text><text x="32" y="90">home,30.38,</text><text x="32" y="108">water,30.40</text></g>',
    # a PDF
    "pdf": FILE + '<rect x="30" y="70" width="62" height="26" rx="5" fill="#e8322b"/><text x="42" y="89" font-family="Poppins" font-size="18" fill="#fff">PDF</text>'
           '<g stroke="#9fb8d4" stroke-width="4" stroke-linecap="round"><path d="M34 46 h52"/><path d="M34 58 h40"/></g>',
    # a map file to drag onto ArcGIS Earth: page with a globe and a pin
    "kmz": FILE + globe(62, 78, 28) + '<path d="M88 52 a10 10 0 1 1 0.1 0 z" fill="#e8322b" stroke="#fff" stroke-width="2"/><path d="M88 62 l0 14" stroke="#e8322b" stroke-width="4"/>',
    # a square gate with legs (World Gates v21 / World Gate Maker 1.1)
    "gates": FILE + '<path d="M50 66 l-10 -10 M74 66 l10 -10 M50 90 l-10 10 M74 90 l10 10" stroke="#e0a800" stroke-width="5" stroke-linecap="round"/><rect x="50" y="66" width="24" height="24" fill="none" stroke="#ffd400" stroke-width="7"/><rect x="50" y="66" width="24" height="24" fill="none" stroke="#7a5600" stroke-width="1.5"/>'
             '<path d="M28 78 h14 M82 78 h14" stroke="#12325a" stroke-width="4" stroke-linecap="round"/><path d="M90 72 l7 6 l-7 6" fill="none" stroke="#12325a" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
    # pictures folder
    "folder_pics": FOLDER + '<g stroke="#0b1d33" stroke-width="2"><rect x="22" y="58" width="24" height="24" rx="4" fill="#e8322b"/><rect x="52" y="58" width="24" height="24" rx="4" fill="#2a7fd4"/><rect x="82" y="58" width="24" height="24" rx="4" fill="#3cc76a"/>'
                   '<rect x="22" y="88" width="24" height="24" rx="4" fill="#fff"/><rect x="52" y="88" width="24" height="24" rx="4" fill="#ff9a3c"/><rect x="82" y="88" width="24" height="24" rx="4" fill="#fff"/></g>'
                   '<text x="28" y="107" font-family="Poppins" font-size="15" fill="#0b1d33">N</text><text x="89" y="107" font-family="Poppins" font-size="15" fill="#0b1d33">E</text>',
    # folder of add-in parts (gears)
    "folder_parts": FOLDER + '<g transform="translate(64 82)"><circle r="20" fill="#5d7fa3" stroke="#0b1d33" stroke-width="2"/><circle r="8" fill="#f2c94c"/>'
                    '<g fill="#5d7fa3" stroke="#0b1d33" stroke-width="2"><rect x="-5" y="-28" width="10" height="10" rx="2"/><rect x="-5" y="18" width="10" height="10" rx="2"/><rect x="-28" y="-5" width="10" height="10" rx="2"/><rect x="18" y="-5" width="10" height="10" rx="2"/></g></g>',
    # console with a green check (self test)
    "check": '<rect x="8" y="16" width="112" height="84" rx="10" fill="#05101e" stroke="#9fb8d4" stroke-width="3"/><rect x="8" y="16" width="112" height="16" rx="8" fill="#2d5f94"/>'
             '<text x="18" y="58" font-family="Consolas,monospace" font-weight="700" font-size="14" fill="#7fd36b">SELF TEST</text>'
             '<circle cx="92" cy="104" r="20" fill="#3cc76a" stroke="#0b1d33" stroke-width="3"/><path d="M82 104 l7 7 l13 -14" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>',
    # radio + map (tracker)
    "radio": '<rect x="14" y="40" width="40" height="76" rx="8" fill="#2b2f36" stroke="#9fb8d4" stroke-width="3"/><path d="M24 40 v-28" stroke="#9fb8d4" stroke-width="5" stroke-linecap="round"/>'
             '<rect x="22" y="52" width="24" height="18" rx="3" fill="#7fd36b"/><g fill="#9fb8d4"><circle cx="28" cy="84" r="3"/><circle cx="40" cy="84" r="3"/><circle cx="28" cy="96" r="3"/><circle cx="40" cy="96" r="3"/></g>'
             '<path d="M60 52 q8 8 0 16 M68 46 q14 14 0 28" fill="none" stroke="#ffd400" stroke-width="4" stroke-linecap="round"/>' + globe(96, 86, 24),
    # signal generator (tester)
    "signal": '<rect x="10" y="34" width="70" height="60" rx="8" fill="#2b2f36" stroke="#9fb8d4" stroke-width="3"/><path d="M20 64 h10 l6 -16 l8 32 l8 -24 l6 8 h12" fill="none" stroke="#7fd36b" stroke-width="4" stroke-linejoin="round"/>'
              '<path d="M80 64 h18" stroke="#9fb8d4" stroke-width="5"/><rect x="96" y="52" width="22" height="24" rx="4" fill="#5d7fa3" stroke="#9fb8d4" stroke-width="2"/><g fill="#0b1d33"><circle cx="102" cy="60" r="2"/><circle cx="112" cy="60" r="2"/><circle cx="107" cy="68" r="2"/></g>'
              '<text x="18" y="114" font-family="Poppins" font-size="15" fill="#ffd400">1 per second</text>',
    # ArcGIS Pro button (where the add-in shows up)
    "button": '<rect x="6" y="26" width="116" height="76" rx="8" fill="#e9eef5" stroke="#9fb8d4" stroke-width="3"/><rect x="6" y="26" width="116" height="18" rx="8" fill="#2d5f94"/>'
              '<text x="14" y="40" font-family="Inter,Arial" font-weight="700" font-size="11" fill="#fff">Add-In</text>'
              '<rect x="22" y="52" width="84" height="42" rx="6" fill="#ffd400" stroke="#0b1d33" stroke-width="2"/><g transform="translate(64 67)"><circle r="8" fill="#5d7fa3"/><circle r="3" fill="#ffd400"/></g>'
              '<text x="30" y="90" font-family="Inter,Arial" font-weight="700" font-size="11" fill="#0b1d33">Open Factory</text>',
    # log file after a failure
    "log": FILE + '<g stroke="#9fb8d4" stroke-width="4" stroke-linecap="round"><path d="M34 50 h52"/><path d="M34 64 h40"/></g>'
           '<path d="M64 74 l24 42 h-48 z" fill="#ffd400" stroke="#0b1d33" stroke-width="3"/><path d="M64 88 v14" stroke="#0b1d33" stroke-width="4" stroke-linecap="round"/><circle cx="64" cy="108" r="2.5" fill="#0b1d33"/>',
    # map tile pyramid -> tpkx
    "tpkx": FILE + '<g stroke="#0b1d33" stroke-width="2"><rect x="34" y="88" width="56" height="20" fill="#3cc76a"/><rect x="42" y="68" width="40" height="20" fill="#2a7fd4"/><rect x="50" y="48" width="24" height="20" fill="#ffd400"/></g>',
    # a grid of numbered cells (master 4 extents / parcels)
    "grid": FILE + '<g stroke="#2d5f94" stroke-width="2" fill="none"><rect x="30" y="44" width="64" height="64"/><path d="M46 44 v64 M62 44 v64 M78 44 v64 M30 60 h64 M30 76 h64 M30 92 h64"/></g>'
            '<rect x="62" y="76" width="16" height="16" fill="#ffd400"/><text x="64" y="88" font-family="Poppins" font-size="9" fill="#0b1d33">55</text>',
    "parcels": FILE + '<g stroke="#e8322b" stroke-width="2.5" fill="#fde8e6"><path d="M30 46 h30 v26 h-30 z"/><path d="M60 46 h32 v18 h-32 z"/><path d="M60 64 h32 v26 h-32 z"/><path d="M30 72 h30 v36 h-30 z"/><path d="M60 90 h32 v18 h-32 z"/></g>',
    "settings": FILE + '<g stroke="#9fb8d4" stroke-width="3"><path d="M32 54 h60"/><path d="M32 74 h60"/><path d="M32 94 h60"/></g><g fill="#ffd400" stroke="#0b1d33" stroke-width="2"><circle cx="72" cy="54" r="7"/><circle cx="46" cy="74" r="7"/><circle cx="82" cy="94" r="7"/></g>',
}

BADGES = {  # class, colour
    "go": ("#ffd400", "#0b1d33"), "once": ("#3cc76a", "#06260f"), "alt": ("#6fb2ff", "#0b1d33"),
    "leave": ("#9aa9bb", "#0b1d33"), "drag": ("#ff9a3c", "#2a1200"), "read": ("#c9a7ff", "#1d0b33"),
    "out": ("#7fd36b", "#06260f"),
}

TIP_ICONS = {
    "folder": '<rect x="4" y="10" width="38" height="28" rx="4" fill="#f2c94c" stroke="#a37a12" stroke-width="2"/><path d="M14 24 l6 6 l12 -12" fill="none" stroke="#0b1d33" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
    "new": '<path d="M10 4 h18 l8 8 v30 h-26 z" fill="#f4f7fb" stroke="#9fb8d4" stroke-width="2"/><text x="14" y="34" font-family="Poppins" font-size="18" fill="#3cc76a">+</text>',
    "warn": '<path d="M23 4 l19 34 h-38 z" fill="#ffd400" stroke="#0b1d33" stroke-width="2"/><path d="M23 16 v12" stroke="#0b1d33" stroke-width="4" stroke-linecap="round"/><circle cx="23" cy="33" r="2.5" fill="#0b1d33"/>',
    "net": '<circle cx="23" cy="23" r="18" fill="#2a7fd4" stroke="#bfe0ff" stroke-width="2"/><ellipse cx="23" cy="23" rx="7" ry="18" fill="none" stroke="#bfe0ff" stroke-width="2"/><path d="M5 23 h36" stroke="#bfe0ff" stroke-width="2"/>',
    "clock": '<circle cx="23" cy="23" r="18" fill="#12325a" stroke="#ffd400" stroke-width="3"/><path d="M23 12 v12 l8 5" fill="none" stroke="#ffd400" stroke-width="3" stroke-linecap="round"/>',
    "plug": '<rect x="12" y="6" width="22" height="22" rx="4" fill="#5d7fa3" stroke="#bfe0ff" stroke-width="2"/><path d="M18 28 v10 M28 28 v10" stroke="#bfe0ff" stroke-width="3"/><path d="M17 14 h12" stroke="#ffd400" stroke-width="3"/>',
    "earth": '<circle cx="23" cy="23" r="18" fill="#2a7fd4" stroke="#0b1d33" stroke-width="2"/><path d="M10 20 q6 -4 11 1 q5 4 10 0 M9 30 q7 3 12 -1 q6 -4 12 1" fill="none" stroke="#7fd36b" stroke-width="3" stroke-linecap="round"/>',
}

WARN = ("warn", "<b>Blue Windows warning?</b> Click <b>More info</b>, then <b>Run anyway</b>. It only asks the first time.")

SHEETS = {
    "world_gate_maker": dict(
        repo="EarthStick", title="What's in the World Gate Maker folder?",
        sub="After you <y>Extract All</y> the zip, you get two files. Here is what each one does - and what it makes for you.",
        cards=[
            ("go", "START HERE · DOUBLE-CLICK", ["World_Gate_Maker.bat"], "Opens the gate maker",
             "Double-click it. A window opens: type two places, how high the gates float and how big they are, then press <b>MAKE GATES</b>."),
            ("py", "LEAVE IT ALONE", ["World_Gate_Maker.py"], "The program itself",
             "The .bat runs it for you, so you <b>never open it</b>. On some PCs it looks like a blank page - that's normal. Keep it next to the .bat."),
            ("gates", "MADE FOR YOU", ["Gate_Home_Central_Park.kmz"], "Your new pair of gates",
             "Saved into EarthStick's <b>Gates</b> folder (it asks you to pick that folder the first time). <b>Drag it onto the map</b> to see the square gates, then <b>restart EarthStick</b> to fly them.", "out"),
        ],
        tips=[("new", "<b>A new file may appear:</b> <m>World_Gate_Maker_settings.json</m>. It just remembers your Gates folder. Leave it."),
              ("earth", "<b>Needs EarthStick 1.3 or later</b> to fly through the gates. The gates can be seen in ArcGIS Earth by anyone."),
              WARN]),

    "object_factory": dict(
        repo="ArcGIS-Earth-Object-Factory", title="What's in the Object Factory folder?",
        sub="After you <y>Extract All</y> the zip, you get these. Here is what each one is for.",
        cards=[
            ("go", "START HERE · DOUBLE-CLICK", ["Run_Object_Factory.bat"], "Opens the Object Factory",
             "A window opens with four tabs: <b>Objects</b> (one marker), <b>Batch</b> (a whole list), <b>Sky Compass</b> and <b>Beacon</b>. Paste coordinates from Google Maps with <b>From Clipboard</b>."),
            ("py", "LEAVE IT ALONE", ["Object_Factory_v1.2.py"], "The program itself",
             "The .bat runs it for you, so you <b>never open it</b>. It may look like a blank page - that's normal. Keep it in this folder."),
            ("folder_pics", "KEEP IT HERE", ["icons"], "The built-in pictures",
             "The 11 ready-made markers (fire truck, helicopter, fuel, water, camera, medical...) and the <b>N E S W</b> letters for the Sky Compass. The program needs this folder beside it."),
            ("txt", "READ IN NOTEPAD", ["README.txt"], "The short instructions",
             "Double-click to open it in Notepad: the quick version of the manual, with the Batch list format."),
            ("list", "EXAMPLE LISTS", ["simple_objects.txt", "sample_objects.txt"], "Lists for the Batch tab",
             "One object per line. Copy one, change the names and coordinates, and give it to the <b>Batch</b> tab. <b>simple</b> = short form, <b>sample</b> = every option."),
            ("kmz", "DRAG ONTO THE MAP", ["SAMPLE_Object_Set.kmz", "SAMPLE_Sky_Compass.kmz", "SAMPLE_Beacon.kml", "SAMPLE_Linked_Camera.kmz"], "Finished examples",
             "Drag any of these onto ArcGIS Earth to see what the factory makes. Nothing to run.", "drag"),
        ],
        tips=[("new", "<b>Your objects are saved to your Desktop</b> unless you pick another place. Drag them onto ArcGIS Earth."),
              ("folder", "<b>Keep the .bat, the .py and the icons folder together.</b> The samples can go anywhere."),
              WARN]),

    "pointlayer": dict(
        repo="Point-Maps", title="What's in the PointLayer folder?",
        sub="After you <y>Extract All</y> the zip, you get four files. Here is what each one does - and what it makes for you.",
        cards=[
            ("go", "START HERE · DOUBLE-CLICK", ["PointLayer.bat"], "Opens PointLayer",
             "Paste the web address of a public map layer (fire hydrants, for example), click <b>Read Service</b>, tick the fields you want, press <b>BUILD</b>."),
            ("py", "LEAVE IT ALONE", ["PointLayer.py"], "The program itself",
             "The .bat runs it for you, so you <b>never open it</b>. It may look like a blank page - that's normal. Keep it next to the .bat."),
            ("txt", "READ IN NOTEPAD", ["README_PointLayer.txt"], "The short instructions",
             "Double-click to open it in Notepad: the steps, what it accepts, and what the completeness check means."),
            ("txt", "TRY THESE FIRST", ["TEST_SOURCES.txt"], "Two layers to practise on",
             "The Nassau and Duval County hydrant addresses PointLayer was built and tested with. Copy one into PointLayer to see it work.", "read"),
            ("kmz", "MADE FOR YOU", ["Hydrants.kmz", "Hydrants.geojson"], "Your offline map layer",
             "Saved in the folder and name you choose. <b>Drag it onto ArcGIS Earth</b> - it works with no internet from then on.", "out"),
        ],
        tips=[("net", "<b>Internet is needed only while it builds</b> - it downloads the points. The file it makes works offline."),
              ("folder", "<b>Keep the .bat and the .py together.</b> The two text files are just for reading."),
              WARN]),

    "parcel100": dict(
        repo="Parcel100", title="What's in the Parcel100 folder?",
        sub="After you <y>Extract All</y> the zip, you get three files. Here is what each one does - and what it makes for you.",
        cards=[
            ("go", "START HERE · DOUBLE-CLICK", ["Parcel100.bat"], "Opens Parcel100",
             "Type your Master 4 box (like <b>82w,81w,30n,31n</b>), keep the Florida parcel address or paste your own, tick the fields, press <b>BUILD 100 GEOJSON FILES</b>."),
            ("py", "LEAVE IT ALONE", ["Parcel100.py"], "The program itself",
             "The .bat runs it for you, so you <b>never open it</b>. It may look like a blank page - that's normal. Keep it next to the .bat."),
            ("txt", "READ IN NOTEPAD", ["README.txt"], "The short instructions",
             "Double-click to open it in Notepad: quick start, the Florida preset, file names and how resume works."),
            ("parcels", "MADE FOR YOU", ["W082W081N031N030-001-Parcels.geojson", "...-100-Parcels.geojson"], "Up to 100 parcel files",
             "One file per Master 4 cell, in the folder you choose. <b>Drag the cells you need onto ArcGIS Earth</b> and click a parcel to see its owner and address.", "out"),
        ],
        tips=[("clock", "<b>Stopped part way?</b> Run it again with the same box and folder - finished cells are skipped, it carries on."),
              ("net", "<b>Internet is needed only while it builds.</b> The parcel files work offline."),
              WARN]),

    "picture_world_maker": dict(
        repo="Picture-World-Maker", title="What's in the Picture World Maker folder?",
        sub="After you <y>Extract All</y> the zip, you get just two things. Here is what each one does - and what it makes for you.",
        cards=[
            ("go", "START HERE · DOUBLE-CLICK", ["Start Picture World Maker.bat"], "Opens Picture World Maker",
             "Choose a giant picture, pick TPKX or MBTiles, press <b>BUILD RASTER PYRAMID</b>. The first time, it installs the Pillow helper by itself."),
            ("folder_parts", "LEAVE IT ALONE", ["System Files"], "The engine room",
             "The program, the photo tiler, the TPKX converter and <m>Picture_World_Maker_Config.ini</m>. Keep it next to the .bat."),
            ("tpkx", "MADE FOR YOU", ["your_picture.tpkx", "your_picture.mbtiles"], "Your picture as a map",
             "Saved in the folder you choose. <b>Drag the .tpkx onto ArcGIS Earth</b> - a photo lands on the ocean off Jacksonville, ready to fly over.", "out"),
        ],
        tips=[("clock", "<b>Fast:</b> about 1 minute for a 50,000 px wide photo. Real map files (GeoTIFFs) open straight in ArcGIS Earth - no need to build them."),
              ("plug", "<b>Memory:</b> about 5 bytes per picture pixel - 3 GB for a 600-million-pixel photo. Close other programs for giant ones."),
              WARN]),

    "mb2tpkx": dict(
        repo="QGIS-Mbtile-to-ArcGIS-Earth-TPKX", title="What's in the MBTiles -> TPKX folder?",
        sub="After you <y>Extract All</y> the zip, you get two files. Here is what each one does - and what it makes for you.",
        cards=[
            ("go", "START HERE · DRAG OR DOUBLE-CLICK", ["mb2tpkx.bat"], "Converts one map",
             "<b>Drag your .mbtiles file onto it</b>, or double-click it and paste the file's full path. The first time, it installs the Pillow helper by itself."),
            ("py", "LEAVE IT ALONE", ["mb2tpkx.py"], "The program itself",
             "The .bat runs it for you, so you <b>never open it</b>. It may look like a blank page - that's normal. Keep it next to the .bat."),
            ("tpkx", "MADE FOR YOU", ["your_map.tpkx"], "Your map for ArcGIS Earth",
             "Saved <b>next to your .mbtiles</b>, same name. Drag it onto ArcGIS Earth - desktop or phone - and it works with no internet.", "out"),
        ],
        tips=[("new", "<b>Pasting a path:</b> right-click the .mbtiles file, <b>Copy as path</b>, then paste it into the black window."),
              ("clock", "<b>Big maps take a while.</b> Leave the window open until it says <b>Conversion complete</b>."),
              WARN]),

    "master4": dict(
        repo="QGIS-Mbtile-to-ArcGIS-Earth-TPKX", title="What's in the Master 4 Grid Maker folder?",
        sub="After you <y>Extract All</y> the zip, you get two files. Here is what each one does - and what it makes for you.",
        cards=[
            ("go", "START HERE · DOUBLE-CLICK", ["Master4_Grid_Maker.bat"], "Makes your grid",
             "Type a one-degree box like <b>82w, 81w, 30n, 31n</b>. It cuts it into <b>100 numbered cells</b>. The first time, it installs the Pillow helper by itself."),
            ("py", "LEAVE IT ALONE", ["Master4_Grid_Maker.py"], "The program itself",
             "The .bat runs it for you, so you <b>never open it</b>. It may look like a blank page - that's normal. Keep it next to the .bat."),
            ("grid", "MADE FOR YOU", ["Master4_82W_81W_30N_31N_Grid.tif"], "The grid picture",
             "Add it to QGIS on top of your map to see which cell is which.", "out"),
            ("txt", "MADE FOR YOU", ["Master4_82W_81W_30N_31N_Extents.txt"], "The exact cell edges",
             "One line per cell. Copy a cell's line into QGIS when you export that cell as a map.", "out"),
        ],
        tips=[("folder", "<b>Look in C:\\downloads</b> - that's where the grid files are saved."),
              ("new", "<b>It asks about a Cell 55 demo map.</b> Just press Enter for No; Yes makes a big colourful practice map."),
              WARN]),

    "batch_factory": dict(
        repo="ArcGIS-Earth-Offline-Maps-Chartplotting", title="What's in the TPKX Batch Factory folder?",
        sub="After you <y>Extract All</y> the zip, you get one file to run and a folder of parts. You install it once - then it lives inside ArcGIS Pro.",
        cards=[
            ("go", "START HERE · OPEN ARCGIS PRO FIRST", ["BUILD_INSTALL.bat"], "Builds and installs it",
             "Open ArcGIS Pro, then double-click this. When it says <b>Build complete</b>, click OK, then <b>Install Add-In</b>. Restart ArcGIS Pro once."),
            ("folder_parts", "LEAVE IT ALONE", ["Factory"], "The parts of the add-in",
             "Code, window layout and toolbar pictures that the builder turns into the add-in on your PC. You never open these - just keep the folder next to BUILD_INSTALL.bat."),
            ("txt", "OPTIONAL READING", ["Factory\\QUIET_BUILD_NOTE.txt", "Factory\\README_GUI_TEST.txt"], "Builder's notes",
             "Notes from testing the builder and the window. Not needed to use the Factory.", "read"),
            ("button", "WHERE YOU'LL FIND IT", ["Add-In tab > Open Factory"], "Your new button in ArcGIS Pro",
             "After the restart, open any project, go to the <b>Add-In</b> tab and click <b>Open Factory</b>. That's where you use it from now on.", "out"),
            ("log", "ONLY IF A BUILD FAILS", ["BUILD_LOG.txt"], "What went wrong",
             "Appears beside BUILD_INSTALL.bat. The message on screen names the problem, for example <b>.NET build tools were not found</b>.", "out"),
        ],
        tips=[("plug", "<b>Needs ArcGIS Pro 3.7 and the free .NET 10 SDK</b> (links at the top of the page)."),
              ("clock", "<b>One time only.</b> Once installed, you never run BUILD_INSTALL.bat again."),
              WARN]),

    "prave_tracker": dict(
        repo="ArcGIS-Earth-Offline-Maps-Chartplotting", title="What's in the PRAVE / ME Tracker folder?",
        sub="After you <y>Extract All</y> the zip, you get three files. Here is what each one does.",
        cards=[
            ("radio", "START HERE · DOUBLE-CLICK", ["START_TRACKER.bat"], "Starts the tracker",
             "Reads radio GPS positions from the COM port and moves each unit's marker in ArcGIS Earth. The first time, it installs the pyserial helper by itself."),
            ("check", "CHECK IT WORKS", ["SELF_TEST.bat"], "A quick check - no radio needed",
             "Runs the tracker's built-in tests and tells you if it passed. A good first step on a new PC.", "alt"),
            ("pyset", "SETTINGS AT THE TOP", ["PRAVE_ME_Tracker.py"], "The program (settings on top)",
             "Don't run it directly. If your radio isn't on <b>COM12</b>, open it in Notepad and change <b>INPUT_PORT</b> near the top. Stop at <b>HERE BE DRAGONS</b>.", "read"),
        ],
        tips=[("earth", "<b>Open ArcGIS Earth first</b> with the <b>Automation API</b> turned on (Settings > Advanced)."),
              ("folder", "<b>Keep all three together</b> in one folder."),
              WARN]),

    "prave_tester": dict(
        repo="ArcGIS-Earth-Offline-Maps-Chartplotting", title="What's in the PRAVE / RMC Tester folder?",
        sub="After you <y>Extract All</y> the zip, you get three files. This is a bench tool: it pretends to be a radio so you can test without one.",
        cards=[
            ("signal", "START HERE · DOUBLE-CLICK", ["Run_PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.bat"], "Starts the tester",
             "Sends practice GPS and radio messages out a COM port, once a second, so you can test a tracker or chartplotter on the bench. <b>Ctrl+C</b> stops it."),
            ("pyset", "SETTINGS AT THE TOP", ["PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.py"], "The program (settings on top)",
             "Don't run it directly. The <b>COM port</b> and speed are at the top - open it in Notepad to change them. It starts on <b>COM12</b>.", "read"),
            ("pdf", "READ THIS", ["PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold_Instructions.pdf"], "The original instructions",
             "Jim's instructions for the tester. Some details are from before the ArcGIS Earth tracker (it mentions COM3 and Google Earth) - the page has the current notes.", "read"),
        ],
        tips=[("plug", "<b>Tester and tracker need opposite ends</b> of a COM port pair - they can't both use COM12."),
              ("folder", "<b>Keep all three together</b> in one folder."),
              WARN]),
}

CSS = """
@font-face { font-family: "Poppins"; font-weight: 700; src: url("file:///usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"); }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { width: 1600px; background: #0b1d33; font-family: "Inter", "Segoe UI", Arial, sans-serif; color: #f4f7fb; }
.wrap { width: 1600px; padding: 40px 56px 30px; background: radial-gradient(ellipse at 50% 0%, #1d4a7a 0%, #0b1d33 62%); }
h1 { font-family: "Poppins"; font-size: 44px; letter-spacing: 0.5px; color: #ffd400; text-shadow: 0 3px 0 #000; }
.sub { font-size: 21px; color: #cfe0f2; margin-top: 4px; }
y { color: #ffd400; font-weight: 700; }
m { font-family: Consolas, "Courier New", monospace; color: #fff; }
.grid { display: grid; gap: 34px 28px; margin-top: 34px; }
.card { position: relative; background: #12325a; border: 2px solid #2d5f94; border-radius: 22px; min-height: 384px;
        padding: 22px 22px 18px; display: flex; flex-direction: column; align-items: center; text-align: center; }
.card.go { background: linear-gradient(180deg, #3a2a00, #1a1400); border-color: #ffd400; box-shadow: 0 0 28px rgba(255,212,0,0.25); }
.card.leave { background: #0f2745; border-color: #24496f; }
.card.out { background: #0f2a2a; border: 2px dashed #7fd36b; }
.badge { position: absolute; top: -15px; left: 50%; transform: translateX(-50%); white-space: nowrap;
         font-family: "Poppins"; font-size: 16px; letter-spacing: 1px; padding: 5px 16px; border-radius: 16px; box-shadow: 0 3px 0 #000; }
.icon { width: 128px; height: 128px; margin-top: 10px; flex: 0 0 auto; }
.fnames { margin-top: 8px; display: flex; flex-direction: column; align-items: center; gap: 5px; max-width: 100%; }
.fname { font-family: Consolas, "Courier New", monospace; font-weight: 700; color: #fff; background: #0b1d33; border: 2px solid #2d5f94;
         border-radius: 10px; padding: 3px 11px; max-width: 100%; }
.out .fname { border-style: dashed; border-color: #7fd36b; }
.t { font-family: "Poppins"; font-size: 24px; margin-top: 10px; line-height: 1.15; color: #ffd400; }
.out .t { color: #9be88a; }
.d { font-size: 18px; color: #dbe7f4; margin-top: 7px; line-height: 1.38; }
.d b { color: #fff; }
.foot { margin-top: 30px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 28px; }
.tip { background: #0f2745; border: 2px dashed #2d5f94; border-radius: 16px; padding: 12px 16px; font-size: 17px; color: #cfe0f2; line-height: 1.35; display: flex; gap: 12px; align-items: center; }
.tip b { color: #ffd400; }
.tip svg { flex: 0 0 46px; height: 46px; }
.key { margin-top: 18px; font-size: 16px; color: #9fb8d4; }
.key span { display: inline-block; width: 26px; height: 14px; border: 2px dashed #7fd36b; border-radius: 4px; vertical-align: -2px; margin-right: 6px; }
/* LIGHT THEME (Jim, 2026-11-04: "brighter, not black and blue") */
body { background: #ffffff; color: #1d2b3a; }
.wrap { background: linear-gradient(180deg, #d9ecff 0%, #f4f9ff 38%, #ffffff 100%); }
h1 { color: #0b3d75; text-shadow: none; }
.sub { color: #2c3e52; }
.sub b, y { color: #c26a00 !important; }
.card { background: #ffffff; border-color: #9cc3ea; box-shadow: 0 4px 14px rgba(20,60,110,0.10); }
.card.go { background: linear-gradient(180deg, #fff3b8, #fffbe6); border: 3px solid #f2b800; box-shadow: 0 4px 18px rgba(242,184,0,0.30); }
.card.quiet, .card.leave { background: #f3f6fa; border-color: #c3cfdc; }
.card.out { background: #f0fbec; border: 2px dashed #3aa94a; }
.badge { box-shadow: 0 2px 0 rgba(0,0,0,0.25); }
.fname { color: #0b2a4a; background: #eaf3fc; border-color: #9cc3ea; }
.out .fname { border-color: #3aa94a; background: #e2f6dc; }
.t { color: #0b3d75; }
.card.go .t { color: #9a5200; }
.out .t { color: #23802f; }
.d { color: #2c3e52; }
.d b { color: #0b1d33; }
.tip { background: #fffdf2; border-color: #e8c96a; color: #2c3e52; }
.tip b { color: #9a5200; }
m { color: #0b2a4a; }
.key { color: #4a6280; }
.key span { border-color: #3aa94a; }
svg path[fill="#f4f7fb"] { fill: #ffffff; stroke: #6f8db0; }
svg path[fill="#cfd9e6"] { stroke: #6f8db0; }
"""


def fname_size(names, cols):
    longest = max(len(n) for n in names)
    width = {2: 640, 3: 405, 4: 280}[cols]
    return max(18, min(23, int(width / (longest * 0.62))))


def sheet_html(s):
    cards = s["cards"]
    n = len(cards)
    cols = {2: 2, 3: 3, 4: 4, 5: 3, 6: 3}[n]
    out = []
    has_out = False
    for c in cards:
        icon, badge, names, title, desc = c[:5]
        kind = c[5] if len(c) > 5 else ("go" if "START HERE" in badge else "leave" if badge == "LEAVE IT ALONE" else "")
        has_out |= kind == "out"
        bcol = BADGES.get(kind) or BADGES["drag" if ("KEEP" in badge or "DRAG" in badge) else "once"]
        size = fname_size(names, cols)
        chips = "".join(f'<div class="fname" style="font-size:{size}px">' + html.escape(x).replace("_", "_<wbr>").replace("\\", "\\<wbr>") + '</div>' for x in names)
        out.append(f'<div class="card {kind}"><div class="badge" style="background:{bcol[0]};color:{bcol[1]}">{badge}</div>'
                   f'<svg class="icon" viewBox="0 0 128 128">{ICONS[icon]}</svg><div class="fnames">{chips}</div>'
                   f'<div class="t">{title}</div><div class="d">{desc}</div></div>')
    tips = "".join(f'<div class="tip"><svg viewBox="0 0 46 46">{TIP_ICONS[i]}</svg><div>{t}</div></div>' for i, t in s["tips"])
    key = '<div class="key"><span></span>Dashed green cards are not in the zip: they are what the tool makes for you, or where to find it.</div>' if has_out else ""
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="wrap">'
            f'<h1>{s["title"]}</h1><div class="sub">{s["sub"]}</div>'
            f'<div class="grid" style="grid-template-columns:repeat({cols},1fr)">{"".join(out)}</div>'
            f'<div class="foot">{tips}</div>{key}</div></body></html>')


def main(outdir):
    from playwright.sync_api import sync_playwright
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    only = sys.argv[2:] or list(SHEETS)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for key in only:
            page_html = sheet_html(SHEETS[key])
            f = outdir / f"{key}.html"
            f.write_text(page_html, encoding="utf-8")
            for scale, suffix in ((1, ""), (2, "_full")):
                pg = b.new_page(viewport={"width": 1600, "height": 300}, device_scale_factor=scale)
                pg.goto(f.resolve().as_uri())
                pg.wait_for_timeout(300)
                pg.screenshot(path=str(outdir / f"{key}{suffix}.png"), full_page=True)
                pg.close()
            print("made", key)
        b.close()


if __name__ == "__main__":
    main(sys.argv[1])
