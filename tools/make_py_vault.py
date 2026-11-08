"""Rebuild 'Py Vault' - a copy of every Python script in the ArcGIS Earth Unlocked family,
taken straight from the released zips people download (so the vault always matches the downloads).

Run from the Unlocked repo root after any release:  python3 tools/make_py_vault.py
It empties 'Py Vault', copies every .py / .pyw from each zip in RELEASES into
'Py Vault/<Tool> <version>/', and writes 'Py Vault/README.md' (table + SHA-256 + source zip).
Update RELEASES when a download link changes. Repos are expected beside this one (../<Repo>)."""
import hashlib, shutil, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOS = ROOT.parent
VAULT = ROOT / "Py Vault"
GH = "https://github.com/Jim-dc95811"

# tool name, repo, zip path inside the repo (same zips the front page links to)
RELEASES = [
    ("MBTiles to TPKX converter (mb2tpkx)", "QGIS-Mbtile-to-ArcGIS-Earth-TPKX", "mb2tpkx.zip"),
    ("Master 4 Grid Maker", "QGIS-Mbtile-to-ArcGIS-Earth-TPKX", "Master4_Grid_Maker.zip"),
    ("PRAVE ME Tracker", "ArcGIS-Earth-Offline-Maps-Chartplotting", "downloads/PRAVE_ME_Tracker_v1.zip"),
    ("PRAVE RMC Field Decoder Tester Gold", "ArcGIS-Earth-Offline-Maps-Chartplotting", "downloads/PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.zip"),
    ("TPKX Batch Factory", "ArcGIS-Earth-Offline-Maps-Chartplotting", "downloads/TPKX_Batch_Factory_v1.zip"),
    ("EarthStick", "EarthStick", "releases/EarthStick_v2.0.zip"),
    ("World Gate Maker", "EarthStick", "releases/World_Gate_Maker_v2.0.zip"),
    ("Object Factory", "ArcGIS-Earth-Object-Factory", "releases/ArcGIS_Earth_Object_Factory_v2.1.zip"),
    ("PointLayer", "Point-Maps", "releases/PointLayer_v2.1.zip"),
    ("Parcel100", "Parcel100", "downloads/Parcel100_v2.0.zip"),
    ("Picture World Maker", "Picture-World-Maker", "releases/Picture_World_Maker_v2.0.zip"),
]


def main():
    if VAULT.exists():
        shutil.rmtree(VAULT)
    VAULT.mkdir()
    rows, count = [], 0
    for tool, repo, rel in RELEASES:
        zpath = REPOS / repo / rel
        with zipfile.ZipFile(zpath) as z:
            top = z.namelist()[0].split("/")[0]                       # e.g. EarthStick_v1.3.6
            version = top.split("_v")[-1] if "_v" in top else "-"
            pys = [n for n in z.namelist() if n.lower().endswith((".py", ".pyw"))]
            if not pys:
                rows.append(f"| {tool} | {version} | *(no Python - C# / PowerShell add-in)* | | [{rel.split('/')[-1]}]({GH}/{repo}/raw/main/{rel}) |")
                continue
            folder = VAULT / f"{tool.split(' (')[0]} v{version}"
            folder.mkdir()
            for n in sorted(pys):
                data = z.read(n)
                name = n.split("/")[-1]
                (folder / name).write_bytes(data)
                sha = hashlib.sha256(data).hexdigest()
                link = f"{folder.name}/{name}".replace(" ", "%20")
                rows.append(f"| {tool} | {version} | [{name}]({link}) | `{sha[:16]}...` | [{rel.split('/')[-1]}]({GH}/{repo}/raw/main/{rel}) |")
                count += 1
    (VAULT / "README.md").write_text(
        "# Py Vault\n\n"
        "Every Python script in the ArcGIS Earth Unlocked family, in one place - copied byte for byte from the "
        "release zips you download, so you can read or compare the code without unzipping anything. "
        "When a tool gets a new release, the vault is rebuilt from the new zip (old versions stay in each repo's history).\n\n"
        "To run a tool, download its zip from its project page - the zip has the one-click .bat launcher and everything else it needs.\n\n"
        "| Tool | Version | Script | SHA-256 (first 16) | From release zip |\n|---|---|---|---|---|\n"
        + "\n".join(rows) + f"\n\n{count} scripts. Rebuilt by `tools/make_py_vault.py`.\n", encoding="utf-8")
    print(f"Py Vault: {count} scripts from {len(RELEASES)} releases")


if __name__ == "__main__":
    main()
