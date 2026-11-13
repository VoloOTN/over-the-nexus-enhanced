"""Shared X-Saber set-code (archetype) membership-table helper for OTN (EU rom.nds).

The engine recognises X-Saber membership via a SORTED 20-entry u16 cid table in
ARM9 main RAM @0x0209CB6E, queried by binary-search wrappers. It is consulted
from exactly two call sites (verified exhaustively):

    consumer A: pool word @0x02023BA0 (table ptr) + `movs r2,#0x14` @0x02023B84
    consumer B: pool word @0x02023DE4 (table ptr) + `movs r2,#0x14` @0x02023DE0

The table is PACKED against the next archetype table (0-byte gap) and ARM9 has
NO truly-dead 44-byte cave (every zero run is a BSS buffer, a sparse jump table,
or structure padding -- relocating there corrupts a live dispatch path, which is
exactly what silently broke Deep Diver's End-Phase trigger). So the table MUST be
edited IN PLACE at 20 entries.

`add_xsaber_member` keeps the count at 20 and SORTED by dropping the first
available *droppable* cid (by default the two engine-internal phantom cids
0x2347 and 0x2346, which have no obtainable card) to make room for the new
member. Stacking the Boggart patch (adds 0x15D4, drops 0x2347) then the Darksoul
patch (adds Gigobyte 0x1783, drops 0x2346) yields a roster of 18 real X-Sabers + both
donors -- no real card sacrificed, no relocation.
"""
from __future__ import annotations

import struct

import ndspy.code
import ndspy.rom

from otn_enhanced.effects.common import ARM9_BASE
XSABER_TBL = 0x0209CB6E         # RAM address of the sorted 20-entry X-/XX-Saber cid table (EU rom.nds)
XSABER_COUNT = 0x14             # 20 entries (the two membership wrappers hardcode this count)

# Engine-internal phantom cids (no obtainable card) -- the only entries safe to
# drop. 0x2347 = native Darksoul, 0x2346 = native Boggart Knight. Default drop
# priority drops the Darksoul phantom first so a standalone Boggart build keeps
# 0x2346 (its synchro predicate routes Orchis 0x15D4 -> 0x2346 by remap).
DEFAULT_DROP_CIDS = (0x2347, 0x2346)

# The two consumer call sites (used only to sanity-check the table addr + count).
POOL_PTRS = (0x02023BA0, 0x02023DE4)    # 4-aligned words that hold the table address
COUNT_IMMS = (0x02023B84, 0x02023DE0)   # `movs r2,#0x14` halfwords feeding the bsearch count


def _open(out_path: str):
    """Open the ROM and return (rom, mc, sec, bytearray(sec.data)) for ARM9 main."""
    rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
    return rom, mc, sec, bytearray(sec.data)


def add_xsaber_member(out_path: str, insert_cid: int,
                      drop_cids: tuple = DEFAULT_DROP_CIDS) -> None:
    """Add *insert_cid* to the X-Saber table IN PLACE, keeping it 20-entry & sorted.

    Idempotent: if *insert_cid* is already present, nothing changes. Otherwise the
    first cid from *drop_cids* that is currently present is removed to make room,
    then the table is re-sorted and written back at its original address. The two
    consumers keep reading 0x0209CB6E with count 20, so no caller assumption moves.
    """
    rom, mc, sec, d = _open(out_path)

    def off(addr: int) -> int:                                  # RAM address -> section-buffer offset
        return addr - ARM9_BASE

    # Sanity: both consumers still point at the table with the hardcoded count 20.
    for p in POOL_PTRS:
        ptr = struct.unpack_from("<I", d, off(p))[0]
        assert ptr == XSABER_TBL, (
            f"X-Saber consumer pool @0x{p:08X} = 0x{ptr:08X} (expected 0x{XSABER_TBL:08X}); "
            f"refusing to patch a moved table"
        )
    for c in COUNT_IMMS:
        imm = struct.unpack_from("<H", d, off(c))[0]
        assert imm == (0x2200 | XSABER_COUNT), (
            f"X-Saber count immediate @0x{c:08X} = 0x{imm:04X} (expected movs r2,#0x14)"
        )

    cur = list(struct.unpack_from("<20H", d, off(XSABER_TBL)))   # current 20-entry table

    if insert_cid in cur:                                        # idempotent
        print(f"X-Saber set-code: 0x{insert_cid:04X} already present -> no change")
        return

    # Pick the first droppable cid that is actually present.
    drop = next((c for c in drop_cids if c in cur), None)
    if drop is None:
        raise SystemExit(
            f"X-Saber set-code: no droppable slot {[hex(c) for c in drop_cids]} present "
            f"to make room for 0x{insert_cid:04X}; table is full of real cards"
        )

    new_tbl = tuple(sorted((set(cur) - {drop}) | {insert_cid}))  # drop one, add one, re-sort
    assert len(new_tbl) == XSABER_COUNT and all(                # still exactly 20, strictly ascending
        new_tbl[i] < new_tbl[i + 1] for i in range(len(new_tbl) - 1)
    ), f"resulting table is not a sorted 20-entry set: {[hex(x) for x in new_tbl]}"

    struct.pack_into("<20H", d, off(XSABER_TBL), *new_tbl)       # write back in place (same addr/size)
    sec.data = bytes(d)
    rom.arm9 = mc.save()
    rom.saveToFile(out_path)

    print(f"X-Saber set-code: in-place table @0x{XSABER_TBL:08X} (count {XSABER_COUNT}); "
          f"dropped 0x{drop:04X}, inserted 0x{insert_cid:04X}")
    print(f"  entries: {', '.join(f'0x{v:04X}' for v in new_tbl)}")
