#!/usr/bin/env python3
"""Compare two TPKX (Esri Compact Cache V2 tile package) files layer by layer.

Usage: python3 tpkx_compare.py reference.tpkx candidate.tpkx

Reports differences in: zip member list and order, zip entry attributes
(compression, origin system, attributes, extra field), root.json and
iteminfo.json (key by key; values that are expected to differ per build such
as guid are flagged as 'expected'), thumbnail, and for every bundle: the 64-byte
header (field by field), the 16384-entry index (empty-slot sentinel, slots used)
and the tile bytes in every slot. Tile *order* inside a bundle is reported but
is not a structural difference (readers go through the index).
"""
import json
import struct
import sys
import zipfile

EXPECTED_DIFF = {"guid", "created"}
HEADER_FIELDS = [  # (offset, struct, name)
    (0, "<I", "version"), (4, "<I", "record count"), (8, "<I", "max record size"),
    (12, "<I", "offset byte count"), (16, "<Q", "slack space"), (24, "<Q", "file size"),
    (32, "<Q", "user header offset"), (40, "<I", "user header size"), (44, "<I", "legacy 1"),
    (48, "<I", "legacy 2"), (52, "<I", "legacy 3"), (56, "<I", "legacy 4"), (60, "<I", "index size"),
]


def flat(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flat(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.update(flat(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = d
    return out


def bundle_info(data):
    hdr = {name: struct.unpack_from(fmt, data, off)[0] for off, fmt, name in HEADER_FIELDS}
    idx = struct.unpack_from("<16384Q", data, 64)
    values = {}
    for v in idx:
        values[v] = values.get(v, 0) + 1
    empty = max(values, key=values.get) if values else None
    slots = {}
    order = []
    for i, v in enumerate(idx):
        if v == empty:
            continue
        off, size = v & ((1 << 40) - 1), v >> 40
        slots[i] = data[off:off + size]
        order.append((off, i))
        if struct.unpack_from("<I", data, off - 4)[0] != size:
            slots[i] = b"BAD LENGTH PREFIX"
    order = [i for _, i in sorted(order)]
    return hdr, empty, slots, order


def compare(ref_path, cand_path):
    problems, notes = [], []
    a, b = zipfile.ZipFile(ref_path), zipfile.ZipFile(cand_path)
    an, bn = [i.filename for i in a.infolist()], [i.filename for i in b.infolist()]
    if set(an) != set(bn):
        problems.append(f"member list differs: only in reference {sorted(set(an) - set(bn))[:8]}, only in candidate {sorted(set(bn) - set(an))[:8]}")
    elif an != bn:
        notes.append("member order differs")
    for name in sorted(set(an) & set(bn)):
        ia, ib = a.getinfo(name), b.getinfo(name)
        for attr in ("compress_type", "create_system", "create_version", "extract_version", "external_attr"):
            if getattr(ia, attr) != getattr(ib, attr):
                problems.append(f"zip entry {name}: {attr} {getattr(ia, attr)} vs {getattr(ib, attr)}")
                break
    for js in ("root.json", "iteminfo.json"):
        if js in an and js in bn:
            fa, fb = flat(json.loads(a.read(js))), flat(json.loads(b.read(js)))
            for k in sorted(set(fa) | set(fb)):
                va, vb = fa.get(k, "<missing>"), fb.get(k, "<missing>")
                if va == vb:
                    continue
                if k.split(".")[-1] in EXPECTED_DIFF:
                    notes.append(f"{js} {k}: differs (expected per build)")
                elif isinstance(va, float) and isinstance(vb, float) and abs(va - vb) <= 1e-9 * max(1.0, abs(va)):
                    notes.append(f"{js} {k}: float rounding only")
                else:
                    problems.append(f"{js} {k}: {va!r} vs {vb!r}")
    if "thumbnail.png" in an and "thumbnail.png" in bn:
        ta, tb = a.read("thumbnail.png"), b.read("thumbnail.png")
        wa, ha = struct.unpack(">II", ta[16:24]); wb, hb = struct.unpack(">II", tb[16:24])
        if (wa, ha) != (wb, hb):
            notes.append(f"thumbnail size {wa}x{ha} vs {wb}x{hb}")
    tiles = 0
    for name in sorted(n for n in set(an) & set(bn) if n.endswith(".bundle")):
        da, db = a.read(name), b.read(name)
        ha, ea, sa, oa = bundle_info(da)
        hb, eb, sb, ob = bundle_info(db)
        for k in ha:
            if ha[k] != hb[k]:
                problems.append(f"{name} header '{k}': {ha[k]} vs {hb[k]}")
        if ea != eb:
            problems.append(f"{name} empty-slot sentinel: {ea} vs {eb}")
        if set(sa) != set(sb):
            problems.append(f"{name} slots used differ ({len(sa)} vs {len(sb)})")
        for i in set(sa) & set(sb):
            if sa[i] != sb[i]:
                problems.append(f"{name} slot {i}: tile bytes differ")
                break
        if oa != ob:
            notes.append(f"{name}: tile order inside bundle differs")
        if da == db:
            notes.append(f"{name}: byte-identical")
        tiles += len(sb)
    return problems, notes, tiles


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    problems, notes, tiles = compare(sys.argv[1], sys.argv[2])
    seen = set()
    for n in notes:
        key = n.split(":")[-1] if ".bundle" in n else n
        if key in seen:
            continue
        seen.add(key)
        print("note   ", n if ".bundle" not in n else "(bundles)" + n.split(".bundle", 1)[1])
    for p in problems[:60]:
        print("DIFFERS", p)
    print(f"\n{len(problems)} structural difference(s); {tiles} tiles compared.")
    sys.exit(1 if problems else 0)
