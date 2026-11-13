"""ov3 compaction census (read-only): ov3 supply vs ov5-cave demand.

Supply  = ov3 bytes reachable only from phantom cls records (dead in BOTH the stock
          and the chained ROM) + exact-duplicate functions + unclaimed OV3_DEAD_BLOCKS.
Demand  = every ov5 cave slot's used bytes in the chained ROM.
Fit     = first-fit-decreasing of whole stubs into the supply runs (no splitting).

    uv run python -m otn_enhanced.tools.ov3_compaction.census

Writes notes/ov3-compaction-census.md + scratch/ov3_compaction_census.json.
The phantom scan is scratch/phantom_ov3_scan.py promoted verbatim (it reproduces
9804 B / 147 runs on stock rom.nds, 2026-09-27 and 2026-10-06).
"""
from __future__ import annotations

import collections
import csv
import json
import logging
import re
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

import ndspy.code
import ndspy.rom

logging.disable(logging.CRITICAL)

REPO = Path(__file__).resolve().parents[3]
WORK = REPO / "data/over_the_nexus/working"
STOCK = WORK / "rom.nds"
CHAIN = WORK / "rom_all_patches.nds"
CSV = REPO / "docs/ov3_catalogue/ov3_index.csv"
OUT_MD = REPO / "notes/ov3-compaction-census.md"
OUT_JSON = REPO / "scratch/ov3_compaction_census.json"
OV3 = 0x02141700
OV5_BASE = 0x022C5900


def _bl_at(buf, off):
    h1, h2 = struct.unpack_from("<HH", buf, off)
    if (h1 & 0xF800) == 0xF000 and (h2 & 0xE800) == 0xE800:
        o = ((h1 & 0x7FF) << 12) | ((h2 & 0x7FF) << 1)
        if o & 0x400000:
            o -= 0x800000
        return o, (h2 & 0xF800) == 0xE800  # blx
    return None


def runs_of(addrs):
    out, s, p = [], None, None
    for a in sorted(addrs):
        if s is None:
            s = p = a
        elif a == p + 1:
            p = a
        else:
            out.append((s, p + 1))
            s = p = a
    if s is not None:
        out.append((s, p + 1))
    return out


# ---------------------------------------------------------------------------
# Phantom dead code (fixpoint).  See the module docstring for provenance.
# ---------------------------------------------------------------------------
def load_ctx(rom_path: Path) -> SimpleNamespace:
    """Every inbound reference into ov3 (ARM9 + all overlays), the cls records, live cids."""
    from otn_enhanced.tools.donor_scan import cards

    rom = ndspy.rom.NintendoDSRom.fromFile(str(rom_path))
    ovs = rom.loadArm9Overlays()
    ov3 = bytes(ovs[3].data)
    END = OV3 + len(ov3)
    u32 = lambda a: struct.unpack_from("<I", ov3, a - OV3)[0]

    # the literal words the cls selector reads (dispatch.cls_table_selector)
    tables = {"cls2": (u32(0x0224A398), u32(0x0224A39C)), "cls0": (u32(0x0224A3A0), u32(0x0224A3A4)),
              "cls1": (u32(0x0224A3A8), u32(0x0224A3AC)), "cls3": (0x02279D74, 0x308)}
    live = set(cards())
    recs = []  # (table, idx, cid, [5 ptrs], rec_addr)
    for t, (b, n) in tables.items():
        for i in range(n):
            a = b + i * 24
            recs.append((t, i, u32(a), [u32(a + k) for k in (4, 8, 12, 16, 20)], a))
    ph = [r for r in recs if r[2] not in live]

    arm9 = ndspy.code.MainCodeFile(rom.arm9, 0x02000000)
    images = [("arm9", 0x02000000, bytes(arm9.sections[0].data))]
    for s in arm9.sections[1:]:
        images.append(("arm9s", s.ramAddress, bytes(s.data)))
    for k, o in ovs.items():
        images.append((f"ov{k}", o.ramAddress, bytes(o.data)))

    refs = collections.defaultdict(list)  # target(even) -> [(kind, src)]
    for name, base, buf in images:
        n = len(buf)
        for off in range(0, n - 3, 4):
            v = struct.unpack_from("<I", buf, off)[0]
            if OV3 <= (v & ~1) < END:
                refs[v & ~1].append(("word", base + off))
        for off in range(0, n - 3, 2):
            r = _bl_at(buf, off)
            if r:
                o, blx = r
                t = base + off + 4 + o
                if blx:
                    t &= ~3
                if OV3 <= t < END:
                    refs[t].append(("bl", base + off))
        for off in range(0, n - 3, 4):  # ARM bl / blx imm
            w = struct.unpack_from("<I", buf, off)[0]
            if (w >> 24) & 0xF in (0xA, 0xB):
                o = w & 0xFFFFFF
                if o & 0x800000:
                    o -= 0x1000000
                t = base + off + 8 + o * 4 + ((2 * ((w >> 24) & 1)) if (w >> 28) == 0xF else 0)
                if OV3 <= t < END and ((w >> 28) == 0xF or (w >> 24) & 0xF == 0xB):
                    refs[t].append(("bl", base + off))
        if name == "ov3":  # short branches only matter intra-overlay
            for off in range(0, n - 1, 2):
                h = struct.unpack_from("<H", buf, off)[0]
                if (h & 0xF800) == 0xE000:
                    o = (h & 0x7FF) << 1
                    if o & 0x800:
                        o -= 0x1000
                    refs[base + off + 4 + o].append(("b", base + off))
                elif (h & 0xF000) == 0xD000 and (h >> 8) & 0xF < 0xE:
                    o = (h & 0xFF) << 1
                    if o & 0x100:
                        o -= 0x200
                    refs[base + off + 4 + o].append(("bcc", base + off))

    lit_all_users = collections.defaultdict(set)  # literal addr -> ldr [pc] sites in ov3
    for off in range(0, len(ov3) - 1, 2):
        h = struct.unpack_from("<H", ov3, off)[0]
        if (h & 0xF800) == 0x4800:
            pc = OV3 + off
            lit_all_users[((pc + 4) & ~3) + (h & 0xFF) * 4].add(pc)
    return SimpleNamespace(ov3=ov3, END=END, refs=refs, recs=recs, ph=ph, live=live,
                           tables=tables, lit_all_users=lit_all_users)


def phantom_dead(rom_path: Path, c: SimpleNamespace | None = None) -> dict:
    c = c or load_ctx(rom_path)
    ov3, END, refs, recs, ph, live = c.ov3, c.END, c.refs, c.recs, c.ph, c.live
    lit_all_users = c.lit_all_users
    from otn_enhanced.rom import stock as _stock
    stock = _stock.ov3()
    u16 = lambda a: struct.unpack_from("<H", ov3, a - OV3)[0]

    starts = set()
    for r in recs:
        starts |= {p & ~1 for p in r[3] if p}
    for t, lst in refs.items():
        if any(k in ("bl", "word") for k, _ in lst):
            starts.add(t)
    starts = sorted(s for s in starts if OV3 <= s < END)

    def extent(entry):
        """Walk the CFG; return (code addrs, literal addrs, bl targets, flow-resolved)."""
        seen, lits, calls, todo, ok = set(), set(), set(), [entry], True
        while todo:
            pc = todo.pop()
            while OV3 <= pc < END and pc not in seen:
                h = u16(pc)
                seen.add(pc)
                r = _bl_at(ov3, pc - OV3)
                if r:
                    seen.add(pc + 2)
                    t = pc + 4 + r[0]
                    calls.add(t & ~3 if r[1] else t)
                    pc += 4
                    continue
                if (h & 0xF800) == 0x4800:
                    lits.add(((pc + 4) & ~3) + (h & 0xFF) * 4)
                elif (h & 0xF800) == 0xA000:
                    ok = False
                if (h & 0xFF00) == 0xBD00 or (h & 0xFF87) == 0x4700:
                    break
                if (h & 0xFF87) == 0x4487 or (h & 0xFF78) == 0x4478 and (h & 0x87) == 0x87:
                    ok = False
                    break
                if (h & 0xF800) == 0xE000:
                    o = (h & 0x7FF) << 1
                    if o & 0x800:
                        o -= 0x1000
                    pc = pc + 4 + o
                    continue
                if (h & 0xF000) == 0xD000 and (h >> 8) & 0xF < 0xE:
                    o = (h & 0xFF) << 1
                    if o & 0x100:
                        o -= 0x200
                    todo.append(pc + 4 + o)
                if (h & 0xFF00) in (0xDF00, 0xDE00):
                    ok = False
                pc += 2
        return seen, lits, calls, ok

    ph_ptrs = {p & ~1 for r in ph for p in r[3] if p}
    live_ptrs = {p & ~1 for r in recs if r[2] in live for p in r[3] if p}
    ph_rec_addrs = {r[4] + k for r in ph for k in (4, 8, 12, 16, 20)}
    cand = ph_ptrs - live_ptrs
    dead, rejected, changed = {}, set(), True
    while changed:
        changed = False
        for f in sorted(cand):
            if f not in dead:
                dead[f] = extent(f)
        owned = set()
        for seen, *_ in dead.values():
            owned |= seen | {p + 1 for p in seen}
        bad = set()
        for f, (seen, lits, calls, ok) in dead.items():
            for a in seen:
                for kind, src in refs.get(a, []):
                    if src in ph_rec_addrs:
                        continue
                    if src in owned and kind != "word":
                        continue
                    if kind in ("b", "bcc") and src in seen:
                        continue
                    bad.add(f)
                    break
                if f in bad:
                    break
        if bad:
            for f in bad:
                dead.pop(f)
            cand -= bad
            rejected |= bad
            changed = True
            continue
        for f, (seen, lits, calls, ok) in list(dead.items()):
            for c in calls:
                if OV3 <= c < END and c not in cand and c not in live_ptrs and c not in rejected:
                    cand.add(c)
                    changed = True

    code_owned = set()
    for seen, *_ in dead.values():
        for a in seen:
            code_owned |= {a, a + 1}
    lit_users = collections.defaultdict(set)
    for f, (seen, lits, calls, ok) in dead.items():
        for lit in lits:
            lit_users[lit].add(f)
    lit_owned = set()
    for lit in lit_users:
        if all(u in code_owned for u in lit_all_users[lit]):
            lit_owned |= {lit + i for i in range(4)}
    for st in starts:  # bytes a live entry can flow into are not free
        if st in dead or st not in code_owned:
            continue
        sn, ln, _, _ = extent(st)
        for a in sn:
            code_owned -= {a, a + 1}
        for lit in ln:
            lit_owned -= {lit + i for i in range(4)}
    owned = code_owned | lit_owned
    mod = {OV3 + i for i in range(min(len(ov3), len(stock))) if ov3[i] != stock[i]}
    free = owned - mod
    return {
        "free": free,
        "dead_fns": {f: (min(v[0]), max(v[0]) + 2, v[3]) for f, v in dead.items()},
        "phantom_records": [(r[0], r[1], r[2], r[4]) for r in ph],
        "already_patched": len(owned & mod),
    }


# ---------------------------------------------------------------------------
# Exact duplicate functions (stock catalogue; BL/BLX normalised to absolute target)
# ---------------------------------------------------------------------------
def duplicate_groups(stock_ov3: bytes, chain_ov3: bytes) -> list[list[tuple[int, int]]]:
    rows = [r for r in csv.DictReader(open(CSV, encoding="utf-8")) if r["kind"] == "func"]

    def norm(a, n, mode):
        d = bytearray(stock_ov3[a - OV3:a - OV3 + n])
        if mode == "thumb":
            i = 0
            while i + 4 <= n:
                r = _bl_at(d, i)
                if r:
                    struct.pack_into("<I", d, i, (a + i + 4 + r[0]) & 0xFFFFFFFF)
                    i += 4
                else:
                    i += 2
        else:
            for i in range(0, n - 3, 4):
                w = struct.unpack_from("<I", d, i)[0]
                if (w >> 25) & 7 == 5:
                    o = w & 0xFFFFFF
                    if o & 0x800000:
                        o -= 0x1000000
                    struct.pack_into("<I", d, i, (w & 0xFF000000) | ((a + i + 8 + o * 4) & 0xFFFFFF))
        return bytes(d) + bytes([a & 2, mode == "arm"])

    g = collections.defaultdict(list)
    for r in rows:
        a, n = int(r["memory_offset"], 16), int(r["size"], 16)
        if stock_ov3[a - OV3:a - OV3 + n] != chain_ov3[a - OV3:a - OV3 + n]:
            continue  # a shipped patch rewrote it: not a clean duplicate any more
        g[norm(a, n, r["mode"])].append((a, n))
    return sorted((v for v in g.values() if len(v) > 1), key=lambda v: -v[0][1] * (len(v) - 1))


# ---------------------------------------------------------------------------
# Demand: ov5 cave slots in the chained ROM
# ---------------------------------------------------------------------------
_PATCH_DIRS = tuple(REPO / "otn_enhanced" / d for d in ("cards", "system", "data", "effects"))
_ASM = re.compile(r"thumb_asm|EffectBuilder|ThumbAssembler")


def cave_demand(chain_ov5: bytes) -> list[dict]:
    from otn_enhanced.effects import ov5_cave as C
    from otn_enhanced.knowledge.check_allocations import parse_ov5_slots

    texts = {p: p.read_text(encoding="utf-8", errors="replace")
             for d in _PATCH_DIRS for p in d.glob("*.py") if p.name != "ov5_cave.py"}
    slots = [s for s in parse_ov5_slots() if C.OV5_NATIVE_END <= s["addr"] < C.CAVE_FREE]
    addrs = sorted({s["addr"] for s in slots}) + [C.CAVE_FREE]
    nxt = dict(zip(addrs, addrs[1:]))
    seen, out = set(), []
    for s in slots:
        if s["addr"] in seen:
            continue  # aliases share one slot
        seen.add(s["addr"])
        blk = chain_ov5[s["addr"] - OV5_BASE:nxt[s["addr"]] - OV5_BASE]
        used = (len(blk.rstrip(b"\0")) + 3) & ~3
        word = re.compile(rf"\b{s['name']}\b")
        users = [p.stem for p, t in texts.items() if word.search(t)]
        method = ("asm" if users and all(_ASM.search(texts[p]) for p in texts if p.stem in users)
                  else "hand" if users else "-")
        flags = list(s["flags"])
        if used == 0:
            flags.append("zero")  # runtime latch / scratch, or unused
        if re.search(r"DIAG|_OLD\b|RETIRED", s["name"]):
            flags.append("debug/retired-name")
        out.append({"name": s["name"], "addr": s["addr"], "reserved": nxt[s["addr"]] - s["addr"],
                    "used": used, "users": users, "method": method, "flags": flags})
    return out


# ---------------------------------------------------------------------------
def ov3_ledger_free() -> list[tuple[int, int]]:
    from otn_enhanced.knowledge.check_allocations import OV3_CLAIMS, OV3_DEAD_BLOCKS
    free = set()
    for a, n, _ in OV3_DEAD_BLOCKS:
        free |= set(range(a, a + n))
    for a, n, _ in OV3_CLAIMS:
        free -= set(range(a, a + n))
    return runs_of(free)


def ffd(runs: list[tuple[int, int]], sizes: list[int]) -> tuple[int, int]:
    """First-fit-decreasing; stubs start 4-aligned (they carry literal pools)."""
    holes = [[(s + 3) & ~3, e] for s, e in runs]
    placed = placed_b = 0
    for n in sorted(sizes, reverse=True):
        for h in holes:
            if h[1] - h[0] >= n:
                h[0] = (h[0] + n + 3) & ~3
                placed += 1
                placed_b += n
                break
    return placed, placed_b


def main() -> int:
    stock_rom = ndspy.rom.NintendoDSRom.fromFile(str(STOCK))
    chain_rom = ndspy.rom.NintendoDSRom.fromFile(str(CHAIN))
    s_ov3 = bytes(stock_rom.loadArm9Overlays([3])[3].data)
    c_ovs = chain_rom.loadArm9Overlays([3, 5])
    c_ov3, c_ov5 = bytes(c_ovs[3].data), bytes(c_ovs[5].data)

    ps, pc = phantom_dead(STOCK), phantom_dead(CHAIN)
    both = ps["free"] & pc["free"]
    dead_runs = runs_of(both)
    dups = duplicate_groups(s_ov3, c_ov3)
    dup_runs = [(a, a + n) for g in dups for a, n in g[1:] if not any(a <= x < a + n for x in both)]
    ledger_runs = ov3_ledger_free()
    demand = cave_demand(c_ov5)

    code = [d for d in demand if d["used"]]
    sizes = [d["used"] for d in code]
    supply = dead_runs + dup_runs + ledger_runs
    fit = ffd(supply, sizes)
    tot = lambda rs: sum(e - s for s, e in rs)
    by_method = collections.Counter()
    for d in code:
        by_method[d["method"]] += d["used"]

    S = {
        "phantom_dead_stock": len(ps["free"]), "phantom_dead_chain": len(pc["free"]),
        "phantom_dead_both": len(both), "phantom_dead_runs": len(dead_runs),
        "dup_groups": len(dups), "dup_bytes": tot(dup_runs),
        "ledger_free": tot(ledger_runs), "supply_total": tot(supply),
        "demand_slots": len(demand), "demand_code_slots": len(code), "demand_used": sum(sizes),
        "demand_zero_reserved": sum(d["reserved"] for d in demand if not d["used"]),
        "demand_by_method": dict(by_method),
        "fit_placed": fit[0], "fit_bytes": fit[1],
    }
    OUT_JSON.parent.mkdir(exist_ok=True)
    json.dump({"summary": S, "dead_runs": dead_runs, "dup_groups": dups,
               "ledger_runs": ledger_runs, "demand": demand}, open(OUT_JSON, "w"), indent=1)

    L = ["# ov3 compaction census (generated -- do not edit)", "",
         f"`python -m otn_enhanced.tools.ov3_compaction.census` -- stock `{STOCK.name}`, chain `{CHAIN.name}`.",
         "Supply is code-structure evidence (scans), NOT in-game proof.", "",
         "## Summary", "", "| item | value |", "|---|---:|"]
    L += [f"| {k} | {v} |" for k, v in S.items()]
    L += ["", "## Largest dead runs (phantom-only, dead in stock AND chain)", "",
          "| addr | bytes |", "|---|---:|"]
    L += [f"| 0x{s:08X} | {e - s} |" for s, e in sorted(dead_runs, key=lambda r: r[0] - r[1])[:25]]
    L += ["", "## Duplicate function groups (first = canonical)", "", "| bytes | copies |", "|---:|---|"]
    L += [f"| {g[0][1]} | {', '.join(f'0x{a:08X}' for a, _ in g)} |" for g in dups]
    L += ["", "## Demand: largest cave slots", "", "| slot | used | method | users | flags |",
          "|---|---:|---|---|---|"]
    L += [f"| {d['name']} | {d['used']} | {d['method']} | {', '.join(d['users'][:3])} | {', '.join(d['flags'])} |"
          for d in sorted(code, key=lambda d: -d["used"])[:40]]
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    for k, v in S.items():
        print(f"{k:24} {v}")
    print("wrote", OUT_MD.relative_to(REPO), "and", OUT_JSON.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
