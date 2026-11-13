"""C-migration Phase 0 step 2: the "before" bytes of every live code slot, read from a ROM.

    uv run python -m otn_enhanced.tools.c_corpus [ROM] [--out scratch/c_corpus.json]

Slots come from the same parsers the allocation guard uses (ov5 CAVE_*, ov3 pool CAVE3_*, ov3 dead-block
claims), so the corpus can't drift from the ledger. A slot without a declared size is bounded by the next
slot's address and marked ``size_inferred``. Retired / legacy / diagnostic ov5 slots are skipped.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ndspy.rom

from otn_enhanced.knowledge import check_allocations as ca

DEFAULT_ROM = "data/over_the_nexus/working/rom_baseline.nds"
INFER_CAP = 0x100   # ponytail: an unsized slot at the end of a region is capped here, not measured


def _slots() -> list[dict]:
    out = []
    for region, slots in (("ov5", ca.parse_ov5_slots()), ("ov3_pool", ca.parse_cave3_slots())):
        addrs = sorted(s["addr"] for s in slots)
        for s in slots:
            if region == "ov5" and not ca._live(s):
                continue
            size, inferred = s["size"], False
            if not size:
                nxt = next((a for a in addrs if a > s["addr"]), s["addr"] + INFER_CAP)
                size, inferred = min(nxt - s["addr"], INFER_CAP), True
            out.append({"name": s["name"], "region": region, "addr": s["addr"], "size": size,
                        "size_inferred": inferred,
                        "owner": s.get("owner") or (re.findall(r"bytes\)\s+(\w+)", s.get("note", "")) or [None])[0]})
    for addr, size, owner in ca.OV3_CLAIMS:
        out.append({"name": f"OV3_DEAD_{addr:08X}", "region": "ov3_dead", "addr": addr, "size": size,
                    "size_inferred": False, "owner": owner})
    return sorted(out, key=lambda s: s["addr"])


def slot_symbols() -> dict[str, int]:
    """Every live ledger slot -> its address: C calls another of our stubs as slot_<NAME> (asm/cc.py)."""
    return {s["name"]: s["addr"] for s in _slots()}


def build(rom_path: str) -> list[dict]:
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    ovs = rom.loadArm9Overlays([3, 5])
    images = [(ov.ramAddress, bytes(ov.data) + b"\0" * (ov.ramSize - len(ov.data))) for ov in ovs.values()]
    corpus = []
    for s in _slots():
        base, img = next(((b, i) for b, i in images if b <= s["addr"] and s["addr"] + s["size"] <= b + len(i)),
                         (None, b""))
        if base is None:
            raise SystemExit(f"{s['name']} @0x{s['addr']:08X}+0x{s['size']:X} is outside overlays 3/5 in {rom_path}")
        raw = img[s["addr"] - base:s["addr"] - base + s["size"]]
        corpus.append({**s, "addr": f"0x{s['addr']:08X}", "empty": not any(raw), "bytes": raw.hex()})
    return corpus


if __name__ == "__main__":
    args = sys.argv[1:]
    out = Path(args.pop(args.index("--out") + 1)) if "--out" in args else Path("scratch/c_corpus.json")
    args = [a for a in args if a != "--out"]
    rom_path = args[0] if args else DEFAULT_ROM
    corpus = build(rom_path)
    out.write_text(json.dumps({"rom": rom_path, "slots": corpus}, indent=1), encoding="utf-8")
    by = {}
    for s in corpus:
        r = by.setdefault(s["region"], [0, 0, 0, 0])
        r[0] += 1; r[1] += s["size"]; r[2] += s["empty"]; r[3] += s["size_inferred"]
    for region, (n, b, e, i) in by.items():
        print(f"{region:9} {n:4} slots {b:6} B  ({e} empty, {i} size inferred)")
    print(f"-> {out}")
