"""Verdict for the ov5 cave canary (_build_ov5_canary.py).

For each savestate: says which overlay occupies 0x022C5900 (ov5 / ov41 / other),
then lists every byte run in the cave region that is no longer 0xA5.

⚠️ If ov41 (puzzle) is resident and ov5 was never loaded this boot, the region
never received the canary at all -- a "reclaimed" result there means "never
written", not "engine wrote here".

    python -m otn_enhanced.tools.ov5_cave_check [state.ml1 ...]
"""
from __future__ import annotations

import glob
import os
import sys

import ndspy.rom

from otn_enhanced.effects import ov5_cave as oc
from otn_enhanced.tools.ov3_cave_check import RAM0, find_ram_offset

ROM = "data/over_the_nexus/working/rom_ov5_canary.nds"
DEFAULT_GLOB = "data/over_the_nexus/working/rom_ov5_canary.ml*"
CANARY = 0xA5
LO, HI = oc.OV5_NATIVE_END, oc.OV5_NATIVE_END + oc.RESERVE
PROBE = 0x400   # compare the first 1 KB at the shared load address


def runs(seg: bytes, base: int) -> list[tuple[int, int]]:
    """Coalesce non-canary bytes into [lo, hi) address runs."""
    out, start = [], None
    for i, b in enumerate(seg):
        if b != CANARY and start is None:
            start = i
        elif b == CANARY and start is not None:
            out.append((base + start, base + i)); start = None
    if start is not None:
        out.append((base + start, base + len(seg)))
    return out


def main(argv: list[str] | None = None) -> int:
    paths = (sys.argv[1:] if argv is None else argv) or sorted(glob.glob(DEFAULT_GLOB))
    if not paths:
        print(f"no savestates matched {DEFAULT_GLOB}")
        return 2
    ovs = ndspy.rom.NintendoDSRom.fromFile(ROM).loadArm9Overlays([5, 41])
    heads = {n: bytes(ovs[n].data[:PROBE]) for n in (5, 41)}

    union: list[tuple[int, int]] = []
    for p in paths:
        buf = open(p, "rb").read()
        off = find_ram_offset(buf)
        print(os.path.basename(p) + ":")
        if off is None:
            print("  SKIP (ov3 anchor not found -- not in a duel / unknown layout)\n")
            continue
        ram = lambda a, n: buf[off + a - RAM0:off + a - RAM0 + n]
        head = ram(oc.OV5_RAM_BASE, PROBE)
        who = next((f"ov{n}" for n, h in heads.items() if h == head), "UNKNOWN")
        bad = runs(ram(LO, HI - LO), LO)
        print(f"  resident @0x{oc.OV5_RAM_BASE:08X}: {who}")
        if not bad:
            print(f"  [PASS] 0x{LO:08X}-0x{HI:08X} fully intact\n")
            continue
        n = sum(h - l for l, h in bad)
        print(f"  [FAIL] {n} byte(s) in {len(bad)} run(s) are not 0x{CANARY:02X}:")
        for l, h in bad[:40]:
            print(f"    0x{l:08X}-0x{h:08X}  ({h - l:#x} B)")
        if len(bad) > 40:
            print(f"    ... {len(bad) - 40} more")
        if who == "ov5":
            union += bad
        print()

    if union:
        first = min(l for l, _ in union)
        print(f"VERDICT (ov5-resident states): reclaimed bytes exist; lowest at 0x{first:08X}. "
              f"Safe contiguous prefix = 0x{LO:08X}-0x{first:08X} ({(first - LO) / 1024:.1f} KB).")
        return 1
    print("VERDICT: no ov5-resident state showed a reclaimed byte.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
