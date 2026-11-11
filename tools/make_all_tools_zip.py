"""Build 'ArcGIS Earth Unlocked - all tools in one zip' (Jim, 2026-11-08: 'Download the Whole Unblocked Series
of Tools' under every page's own download link).

Run from the Unlocked repo root after ANY release (same moment as tools/make_py_vault.py):
    python3 tools/make_all_tools_zip.py
It takes the CURRENT release zip of every Python tool (the RELEASES list in make_py_vault.py - so the two never
disagree; Batch Factory is left out: it is an ArcGIS Pro add-in, not a click-and-run tool) and copies each one's
folder, exactly as released, into one folder:

    ArcGIS_Earth_Unlocked_All_Tools/
        EarthStick_v2.0/              (Fly_ArcGIS_Earth.bat + ...)
        World_Gate_Maker_v2.0/        (World_Gate_Maker.bat + System Files)
        ...                           one folder per tool, one .bat in each

-> downloads/ArcGIS_Earth_Unlocked_All_Tools.zip (the file every page links to; same name every time).
Refuses to build if a release zip holds anything a PC writes on first run (logs, saved paths).
"""
import zipfile
from pathlib import Path

from make_py_vault import RELEASES, REPOS, ROOT

OUT = ROOT / "downloads" / "ArcGIS_Earth_Unlocked_All_Tools.zip"
TOP = "ArcGIS_Earth_Unlocked_All_Tools"
SKIP_TOOLS = {
    "TPKX Batch Factory",                      # ArcGIS Pro add-in, not click-and-run
    "PRAVE RMC Field Decoder Tester Gold",     # 2026-11-11: left the 10; P25 GPS Tracker took its slot
    "PRAVE ME P25 Tracker (trifecta)",         # trifecta held out until field-tested (lives under PRAVE/ME)
}
NEVER = ("python_path.txt", "arcgis_earth_path.txt", "ready_to_fly_log.txt", ".log", "__pycache__", ".pyc")


def main():
    OUT.parent.mkdir(exist_ok=True)
    tmp = OUT.with_name(OUT.name + ".partial")
    names = []
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for tool, repo, rel in RELEASES:
            if tool in SKIP_TOOLS:
                continue
            with zipfile.ZipFile(REPOS / repo / rel) as z:
                for info in z.infolist():
                    low = info.filename.lower()
                    if any(n in low for n in NEVER):
                        raise SystemExit(f"{rel} holds a first-run file ({info.filename}) - fix the release zip first")
                    new = zipfile.ZipInfo(f"{TOP}/{info.filename}", info.date_time)
                    new.external_attr, new.compress_type = info.external_attr, zipfile.ZIP_DEFLATED
                    out.writestr(new, b"" if info.is_dir() else z.read(info))
                names.append(z.namelist()[0].split("/")[0])
    tmp.replace(OUT)
    print(f"{OUT.relative_to(ROOT)}: {len(names)} tools - " + ", ".join(names))


if __name__ == "__main__":
    main()
