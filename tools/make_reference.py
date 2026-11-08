"""Write REFERENCE_2.0.md - the 2.0 Reference list (Jim, 2026-11-08: 'I want all of the programs to go to 2.0,
and to establish today's product as a reference').

Run from the Unlocked repo root with all repos side by side (same as make_py_vault.py):
    python3 tools/make_reference.py
For every release zip in RELEASES (make_py_vault.py) plus the TPKX Batch Factory it lists the zip's SHA-256 and the
SHA-256 of every file inside it, so anyone can check that a copy is exactly the reference version.
Re-run after the Parcel100 GitHub workflow has rebuilt its zip (its zip SHA changes each rebuild; the files inside do not).
"""
import hashlib
import subprocess
import zipfile
from pathlib import Path

from make_py_vault import RELEASES, REPOS, ROOT, GH

EXTRA = [("TPKX Batch Factory (ArcGIS Pro add-in)", "ArcGIS-Earth-Offline-Maps-Chartplotting", "downloads/TPKX_Batch_Factory_v1.zip")]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    seen, rows = set(), []
    for tool, repo, rel in RELEASES + EXTRA:
        if (repo, rel) in seen:
            continue
        seen.add((repo, rel))
        data = (REPOS / repo / rel).read_bytes()
        with zipfile.ZipFile(REPOS / repo / rel) as z:
            top = z.namelist()[0].split("/")[0]
            files = [(i.filename, sha(z.read(i))) for i in z.infolist() if not i.is_dir()]
        rows.append((tool, repo, rel, top, sha(data), files))
    out = ["# ArcGIS Earth Unlocked - 2.0 Reference (8 November 2026)", "",
           "> 🤖 **Using AI assistance?** Have the agent read the [CLAUDE.md](CLAUDE.md) file first.", "",
           "On 8 November 2026 Jim Gaddy moved every tool in the family to **2.0** at once, so that this day's working "
           "set is one known-good reference point. Every tool below was run by Jim on Windows with ArcGIS Earth before "
           "it was published. The table **Reference commits** below names the exact commit of each repository that holds "
           "this state - later commits may follow, and that commit stays the reference.", "",
           "**What changed for 2.0:** EarthStick 2.0 and World Gate Maker 2.0 bring new features (gates picked up while "
           "you fly, the + ADD GATES button, dropped gates that face each other - see the "
           f"[EarthStick 2.0 change document]({GH}/EarthStick/blob/main/docs/EARTHSTICK_V2.0_CHANGES.md)). "
           "Every other tool is the same program as before with only its version text changed (checked line by line). "
           "The PRAVE / RMC Field Decoder Tester stays *Version 1.0 Gold* - Jim's own program, published unchanged. "
           "Older zips are kept in each repository's `archive/` folder.", "",
           "**How to check a copy:** on Windows, open PowerShell in the folder with the zip and type "
           "`Get-FileHash <zip name>` - the SHA-256 must match the zip line below. For a file you already extracted, "
           "`Get-FileHash \"System Files\\<file>\"` must match its line.", "",
           "| Tool | Download | Folder inside |", "|---|---|---|"]
    for tool, repo, rel, top, zsha, files in rows:
        out.append(f"| {tool} | [{rel.split('/')[-1]}]({GH}/{repo}/raw/main/{rel}) | `{top}` |")
    out += ["", "## Reference commits", "", "| Repository | Commit |", "|---|---|"]
    for repo in sorted({r[1] for r in rows} | {"ArcGIS-Earth-Unlocked"}):
        c = subprocess.run(["git", "-C", str(REPOS / repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        out.append(f"| [{repo}]({GH}/{repo}) | [`{c[:7]}`]({GH}/{repo}/tree/{c}) |")
    for tool, repo, rel, top, zsha, files in rows:
        out += ["", f"## {tool}", "", f"Zip [`{rel}`]({GH}/{repo}/raw/main/{rel}) (repository [{repo}]({GH}/{repo})):", "",
                f"`{zsha}`" + ("  *(rebuilt by the repository's GitHub workflow - check the files inside)*" if repo == "Parcel100" else ""),
                "", "| File | SHA-256 |", "|---|---|"]
        out += [f"| `{n}` | `{h}` |" for n, h in files]
    out += ["", "Written by `tools/make_reference.py`.", ""]
    (ROOT / "REFERENCE_2.0.md").write_text("\n".join(out), encoding="utf-8")
    print("REFERENCE_2.0.md:", len(rows), "zips,", sum(len(r[5]) for r in rows), "files")


if __name__ == "__main__":
    main()
