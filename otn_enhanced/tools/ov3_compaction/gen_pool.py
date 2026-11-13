"""Generate pool_blocks.py: the frozen input of step 0 (ov3_compact).

    uv run python -m otn_enhanced.tools.ov3_compaction.gen_pool

Run against stock rom.nds and a chain ROM built WITHOUT step 0 (the build takes ~3 min, a
scan ~1 min per ROM, so the result is frozen as data). It refuses a chain that already has
step 0 applied: there the freed bytes are zeros and the scan would see a different world.

Three kinds of edit, all at STOCK addresses (step 0 runs first, on stock ov3):
  FREE_RUNS  -- bytes freed: code + private literals reachable only from phantom cls records,
                dead in BOTH stock and chain (census.phantom_dead), plus exact-duplicate copies.
                Ranges already in check_allocations.OV3_DEAD_BLOCKS are excluded.
  NULL_SLOTS -- phantom cls-record slot words pointing into a freed run, nulled where a live
                record of the same table+slot is already null (engine provably tolerates it).
  REDIRECTS  -- every reference to a freed duplicate copy, repointed at the canonical copy.
"""
from __future__ import annotations

import collections
import struct
import sys
import zlib
from pathlib import Path

from otn_enhanced.tools.ov3_compaction import census as C
from otn_enhanced.tools.ov3_compaction.census import OV3, _bl_at, runs_of

OUT = Path(__file__).resolve().parents[2] / "effects" / "pool_blocks.py"

_TERMINAL = lambda h: (h & 0xFF00) == 0xBD00 or (h & 0xFF87) == 0x4700 or (h & 0xF800) == 0xE000


def _body_ok(ov3: bytes, a: int, n: int) -> bool:
    """Thumb body is position-independent apart from BL: every PC-relative load and every
    short branch stays inside [a, a+n); no ADD rX,PC / hi-reg write to PC (jump tables)."""
    i = 0
    while i < n - 1:
        pc = a + i
        if i + 4 <= n and _bl_at(ov3, pc - OV3):
            i += 4
            continue
        h = struct.unpack_from("<H", ov3, pc - OV3)[0]
        if (h & 0xF800) == 0x4800:
            t = ((pc + 4) & ~3) + (h & 0xFF) * 4
            if not a <= t < a + n:
                return False
        elif (h & 0xF800) == 0xA000:
            return False
        elif (h & 0xFF00) in (0x4400, 0x4600) and (h & 0x87) == 0x87:  # add/mov pc, rX
            return False
        elif (h & 0xF800) == 0xE000:
            o = (h & 0x7FF) << 1
            o -= 0x1000 if o & 0x800 else 0
            if not a <= pc + 4 + o < a + n:
                return False
        elif (h & 0xF000) == 0xD000 and (h >> 8) & 0xF < 0xE:
            o = (h & 0xFF) << 1
            o -= 0x200 if o & 0x100 else 0
            if not a <= pc + 4 + o < a + n:
                return False
        i += 2
    return True


def _record_slots(ctx) -> dict[int, tuple]:
    """cls slot-word address -> (table, slot index 1..5, cid)."""
    return {r[4] + 4 * k: (r[0], k, r[2]) for r in ctx.recs for k in range(1, 6)}


def _dup_redirects(ctx_s, ctx_c, groups, csv_rows):
    """Accept a duplicate copy only if every reference to it is redirectable (stock) and no
    shipped patch added a reference the redirect would miss (chain)."""
    boundary = {int(r["memory_offset"], 16) for r in csv_rows if r["boundary"]}
    slots_s, slots_c = _record_slots(ctx_s), _record_slots(ctx_c)
    in_ov3 = lambda s: OV3 <= s < ctx_s.END
    freed, redirects, rejected = [], [], collections.Counter()
    for g in groups:
        (ca, n) = g[0]
        if ca in boundary or not _body_ok(ctx_s.ov3, ca, n):
            rejected["canonical body"] += len(g) - 1
            continue
        for a, _ in g[1:]:
            why = None
            if a in boundary or not _body_ok(ctx_s.ov3, a, n):
                why = "body"
            prev = struct.unpack_from("<H", ctx_s.ov3, a - 2 - OV3)[0]
            if not why and not (_TERMINAL(prev) or prev == 0 or (a - 4) in ctx_s.lit_all_users
                                or (a - 2) in ctx_s.lit_all_users):
                why = "fall-through"
            mine = []
            for ctx, slots in ((ctx_s, slots_s), (ctx_c, slots_c)):
                for t in range(a, a + n):
                    for kind, src in ctx.refs.get(t, []):
                        if kind in ("b", "bcc") and a <= src < a + n:
                            continue
                        ok = t == a and (
                            (kind == "bl" and in_ov3(src) and _bl_at(ctx.ov3, src - OV3)
                             and src + 4 + _bl_at(ctx.ov3, src - OV3)[0] == a
                             and not _bl_at(ctx.ov3, src - OV3)[1])
                            or (kind == "word" and (src in slots or src in ctx.lit_all_users)))
                        if not ok:
                            why = why or f"ref {kind} from 0x{src:08X}"
                        elif ctx is ctx_s:
                            mine.append((kind, src))
            # every chain BL into the copy must also be a stock BL (ov3 code does not move)
            stock_bl = {s for k, s in mine if k == "bl"}
            for kind, src in ctx_c.refs.get(a, []):
                if kind == "bl" and src not in stock_bl:
                    why = why or f"chain-only bl from 0x{src:08X}"
            if why:
                rejected[why.split(" from")[0]] += 1
                continue
            freed.append((a, a + n))
            for kind, src in mine:
                if kind == "bl":
                    redirects.append((src, "bl", a, ca))
                else:
                    old = struct.unpack_from("<I", ctx_s.ov3, src - OV3)[0]
                    redirects.append((src, "word", old, ca | (old & 1)))
    return freed, redirects, rejected


def main() -> int:
    import csv
    from otn_enhanced.knowledge.check_allocations import OV3_DEAD_BLOCKS, PHANTOM_CLAIMS

    print("scanning stock + chain (~2 min)...")
    ctx_s, ctx_c = C.load_ctx(C.STOCK), C.load_ctx(C.CHAIN)
    ps, pc = C.phantom_dead(C.STOCK, ctx_s), C.phantom_dead(C.CHAIN, ctx_c)
    reserved = {x for a, n, _ in OV3_DEAD_BLOCKS for x in range(a, a + n)}
    dead = (ps["free"] & pc["free"]) - reserved
    if not dead:
        raise SystemExit("no phantom-dead bytes in the chain -- is step 0 already applied?")
    for a in dead:  # step 0 must not be in the chain yet
        if ctx_c.ov3[a - OV3] != ctx_s.ov3[a - OV3]:
            raise SystemExit(f"chain differs from stock at 0x{a:08X}: rebuild the chain WITHOUT step 0")

    rows = [r for r in csv.DictReader(open(C.CSV, encoding="utf-8")) if r["kind"] == "func"]
    taken = dead | reserved
    groups = [g for g in C.duplicate_groups(ctx_s.ov3, ctx_c.ov3)
              if not any(x in taken for a, n in g for x in range(a, a + n))]
    dup_freed, redirects, rejected = _dup_redirects(ctx_s, ctx_c, groups, rows)

    free_runs = runs_of(dead | {x for s, e in dup_freed for x in range(s, e)})
    # a reference sitting inside freed code is zeroed with it -- don't redirect it
    redirects = [r for r in redirects if not any(s <= r[0] < e for s, e in free_runs)]
    # null phantom record slots that point into a freed run, where null is proven tolerated
    claimed = {cid for _, cid, _ in PHANTOM_CLAIMS}
    null_ok = {(r[0], k) for r in ctx_s.recs if r[2] in ctx_s.live
               for k in range(1, 6) if r[3][k - 1] == 0}
    chain_ph = {(r[0], r[2]) for r in ctx_c.ph}
    in_free = lambda p: any(s <= (p & ~1) < e for s, e in free_runs)
    nulls, kept = [], 0
    for r in ctx_s.ph:
        for k in range(1, 6):
            p = r[3][k - 1]
            if p and in_free(p):
                if (r[0], k) in null_ok and r[2] not in claimed and (r[0], r[2]) in chain_ph:
                    nulls.append((r[4] + 4 * k, p))
                else:
                    kept += 1

    crc = lambda s, e: zlib.crc32(ctx_s.ov3[s - OV3:e - OV3])
    L = ['"""GENERATED by gen_pool.py -- do not edit. Stock-EU addresses; input of ov3_compact."""',
         "", f"# phantom-dead {len(dead)} B + duplicate copies {sum(e - s for s, e in dup_freed)} B",
         "FREE_RUNS: list[tuple[int, int, int]] = [  # (start, end, crc32 of stock bytes)"]
    L += [f"    (0x{s:08X}, 0x{e:08X}, 0x{crc(s, e):08X})," for s, e in free_runs]
    L += ["]", "", f"# {kept} phantom slot words into freed runs left in place (no live-null precedent / claimed)",
          "NULL_SLOTS: list[tuple[int, int]] = [  # (slot word addr, stock value)"]
    L += [f"    (0x{a:08X}, 0x{v:08X})," for a, v in nulls]
    L += ["]", "", "REDIRECTS: list[tuple[int, str, int, int]] = [  # (site, kind, old target/word, new)"]
    L += [f"    (0x{s:08X}, {k!r}, 0x{o:08X}, 0x{nw:08X})," for s, k, o, nw in redirects]
    L += ["]", ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"phantom-dead {len(dead)} B, dup copies freed {len(dup_freed)} "
          f"({sum(e - s for s, e in dup_freed)} B), rejected {dict(rejected)}")
    print(f"FREE_RUNS {len(free_runs)} ({sum(e - s for s, e in free_runs)} B), "
          f"NULL_SLOTS {len(nulls)} (kept {kept}), REDIRECTS {len(redirects)}")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
