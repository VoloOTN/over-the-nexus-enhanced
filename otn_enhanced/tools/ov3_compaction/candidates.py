"""Phase D picker: which card's ov5 stubs can move to the ov3 pool next, and where they fit.

    uv run python -m otn_enhanced.tools.ov3_compaction.candidates [N]

A card qualifies only if its WHOLE live ov5 footprint is movable (else "works in a puzzle" cannot
pass): every live slot method == "asm" (thumb_asm, re-basable) and owned by that module alone.
Shared slots (trampolines, hooks) are listed separately -- they need their own session.
Demand comes from scratch/ov3_compaction_census.json (re-run `census` if ov5_cave.py grew);
supply = FREE_RUNS minus the CAVE3_* claims. Placement is best-fit per stub, whole-stub only.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

from otn_enhanced.knowledge.check_allocations import parse_cave3_slots, parse_ov5_slots, _live
from otn_enhanced.effects.pool_blocks import FREE_RUNS

CENSUS = "scratch/ov3_compaction_census.json"


def free_fragments() -> list[tuple[int, int]]:
    """(start, end) of every unclaimed piece of every freed run."""
    claims = sorted((s["addr"], s["addr"] + s["size"]) for s in parse_cave3_slots())
    out = []
    for s, e, _ in FREE_RUNS:
        cur = s
        for a, b in claims:
            if s <= a < e:
                if a > cur:
                    out.append((cur, a))
                cur = max(cur, b)
        if cur < e:
            out.append((cur, e))
    return out


def main(argv: list[str]) -> None:
    top = int(argv[0]) if argv else 15
    live = {s["name"] for s in parse_ov5_slots() if _live(s)}
    allslots = [d for d in json.load(open(CENSUS))["demand"] if d["name"] in live]
    demand = [d for d in allslots if d["used"] > 0]
    latches = defaultdict(list)   # all-zero ov5 slots = runtime RAM latches: in a puzzle that RAM is ov41
    for d in allslots:
        if d["used"] == 0:
            for u in d["users"]:
                latches[u].append(d["name"])
    frags = free_fragments()
    print(f"ov3 pool: {sum(b - a for a, b in frags)} B free in {len(frags)} fragments "
          f"(largest {max((b - a for a, b in frags), default=0)} B); "
          f"{sum(d['used'] for d in demand)} B of live ov5 code remains")
    by = defaultdict(list)
    for d in demand:
        for u in d["users"]:
            by[u].append(d)
    ok, blocked = [], []
    for mod, slots in by.items():
        if not mod.startswith("patch_"):
            continue
        bad = [d["name"] for d in slots if d["method"] != "asm" or len(d["users"]) != 1]
        (blocked if bad else ok).append((sum(d["used"] for d in slots), mod, slots, bad))
    sizes = sorted(b - a for a, b in frags)
    print(f"\nWHOLE-CARD movable ({len(ok)} modules), smallest first:")
    for total, mod, slots, _ in sorted(ok)[:top]:
        pool, fits = list(sizes), True
        for d in sorted(slots, key=lambda d: -d["used"]):   # best-fit, biggest stub first
            fit = next((x for x in pool if x >= d["used"]), None)
            fits &= fit is not None
            if fit is not None:
                pool.remove(fit)
        print(f"  {total:5d} B  {mod:42s} {'fits' if fits else 'NEEDS SPLIT'}  "
              + ", ".join(f"{d['name']}({d['used']})" for d in slots)
              + (f"  !! ov5 LATCH {latches[mod]}" if latches[mod] else ""))
    print(f"\nblocked by a shared or hand-encoded slot: {len(blocked)} modules "
          f"(e.g. {', '.join(m for _, m, _, _ in sorted(blocked)[:5])})")


if __name__ == "__main__":
    main(sys.argv[1:])
