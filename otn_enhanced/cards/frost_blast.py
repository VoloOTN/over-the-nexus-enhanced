"""Frost Blast of the Monarchs (Normal Spell) on Double Snare 0x14C3.  Single-card / combined TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "If you control a monster with 2400 or more ATK and 1000 DEF: Target 1 Set card on the field; destroy it.  You can banish this card and 1 "Monarch"
     Spell/Trap Card from your Graveyard, then target 1 Set card on the field; destroy it."

Clauses  C1 condition: a monster you control with 2400+ ATK and 1000 DEF.  C2 target 1 Set card on the field; destroy it.
         C3 (Graveyard): banish this card and 1 other "Monarch" Spell/Trap from the GY (cost), then target 1 Set card; destroy it.
Design   * cls0 {0x14C3, 0x02204899 (native destroy target 0), 0x021DFD1D (Granmarg the Rock Monarch's "Set card" filter), COND, 0, 0x02234DA5 (single-target selector)}
           rewritten in place over Double Snare's record (stock {.., 0x02204899, 0x021DE2B1, 0, 0, 0x02234DA5}: the same resolver / selector, a different filter).
         * COND uses the PRINTED ATK / DEF (cid getters 0x0202AC49 / 0x0202AC29) of your face-up monsters: a KNOWN GAP versus current ATK (not a silent deviation).
         * C3 = a cls2 record over a cls2 phantom + the 18th virtual GY-action row (gy_vrow_hook layout GYV2, MONARCH_ARMS) + the native banish cost 0x021E5319 over a virtual GY
           row 0xFFB0 {0x14C3, set 0x6D, 0x0223CA2D (GY handler with the set-code predicate), word 0x2C = Spell|Trap, not self}, then the native self-banish 0x021E5709.
         * "Monarch" = set code 0x6D (tenacity.py hosts the list; its 8-entry slot is full with this card).

    uv run python _build_frost_blast.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.cards import tenacity as TN
from otn_enhanced.dsl import CLS0, CLS2, Compiled, Edit, Row
from otn_enhanced.effects import gy_vrow_hook as gyv, ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

FB = 0x14C3
CHAIN = "data/over_the_nexus/working/rom_chain_17400.nds"
OUT = "data/over_the_nexus/working/rom_frost_blast.nds"
C_DIR = Path(__file__).resolve().parent / "c"

NATIVE = (FB, 0x02204899, 0x021DE2B1, 0, 0, 0x02234DA5)            # Double Snare's cls0 record, stock (read 2026-11-11 from the chain ROM)
DESTROY_TARGET, SET_FILTER, SINGLE_SELECT = 0x02204899, 0x021DFD1D, 0x02234DA5
GY_SETCODE_HANDLER = 0x0223CA2D                                    # GY handler with the set-code predicate (flags 0x10000), aux = the set code
IDX = 0xFFB0
WORD_ST_NOT_SELF = 0x0000002C                                      # Spell (0x4) | Trap (0x8) | except self (0x20)
CLS2_PHANTOM = 0x0EBE
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
for _v in (DESTROY_TARGET, SET_FILTER, SINGLE_SELECT, GY_SETCODE_HANDLER, H3_RESUME):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

S = {n: getattr(O5, f"CAVE_FB_{n}") for n in ("COND", "COND2", "COST2", "ROWS", "H2", "H3")}
RESERVE = {"COND": 0x70, "COND2": 0x70, "COST2": 0x20, "ROWS": 0x10, "H2": 0x30, "H3": 0x30}
_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_FB_H2], _DN[O5.CAVE_FB_H3]
ROWS_BLOB = struct.pack("<HHII", FB, TN.MONARCH_SET, GY_SETCODE_HANDLER, WORD_ST_NOT_SELF) + bytes(4)
assert struct.unpack_from("<I", ROWS_BLOB, 4)[0] == GY_SETCODE_HANDLER and len(ROWS_BLOB) == 0x10, "the GY row's handler is missing (a zero handler = blx 0 = freeze)"
CLS0_REC = (FB, DESTROY_TARGET, SET_FILTER, S["COND"] | 1, 0, SINGLE_SELECT)
CLS2_REC = (FB, 0, DESTROY_TARGET, SET_FILTER, S["COND2"] | 1, S["COST2"] | 1, SINGLE_SELECT)


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "frostblast.c", S[slot], {"STUB": stub}), slot)


def h2_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, FB)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, IDX)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _fit(b.assemble(S["H2"], pad="nop"), "H2")


def h3_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, IDX)
    b.insn("SUB", "R0, R6, R0")
    b.insn("CMP", "R0, #0x1")
    b.insn("BCS", "prev")
    b.insn("LSL", "R0, R0, #0x4")
    b.ldr_const(3, S["ROWS"])
    b.insn("ADD", "R0, R0, R3")
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, H3_PREV | 1)
    b.insn("BX", "R0")
    return _fit(b.assemble(S["H3"], pad="nop"), "H3")


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _reaches(view, site: int, slot: str) -> bool:
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


class frost_blast_of_the_monarchs:
    cid: int = FB

    def blobs(self):
        return {"COND": (S["COND"], _c("FB_COND", "COND"), "cls0 +0C cond (C)"),
                "COND2": (S["COND2"], _c("FB_COND2", "COND2"), "cls2 +0C cond (C)"),
                "COST2": (S["COST2"], _c("FB_COST2", "COST2"), "cls2 +10 cost (C)"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria row 0xFFB0 (GY)"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"),
                "MON": (O5.CAVE_TN_MON, TN.MON_BLOB, "'Monarch' set code 0x6D list (shared with Tenacity)")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            if key not in ("ROWS", "MON"):
                assert_thumb1_only(blob, addr)
        group = TN.GROUPS[0]
        assert group.setcode == TN.MONARCH_SET

        def install(rom, v):
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            group.install(rom, v)
            gyv.install(rom, v.buf, arms=gyv.ARMS + gyv.MONARCH_ARMS, layout=gyv.GYV2)

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Frost Blast {slot} front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            c.eq(struct.unpack_from("<I", O5.read_cave(rom, S["ROWS"], 0x10), 4)[0], GY_SETCODE_HANDLER, "GY row 0xFFB0 handler")
            group.check(c, rom, v)

        return Compiled(tuple(blobs.values()), edits=(Edit(CLS0, FB, NATIVE, CLS0_REC),), rows=(Row(CLS2, CLS2_REC, CLS2_PHANTOM),), installs=(install,), checks=(check,))


SPEC = frost_blast_of_the_monarchs()
_dsl_main, _dsl_verify = dsl.make(SPEC, None, out=OUT)


def _ai_row(ov_data: bytes, base: int):
    for off in range(0x02390000 - base, min(len(ov_data), 0x02397200 - base) - 8, 4):
        w, h = struct.unpack_from("<II", ov_data, off)
        if (w & 0x3FFF) == FB and h & 1 and (w >> 16) and (w >> 16) & 0xFFF0 == 0:
            return off
    return None


def _patch_ai_row(out):
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov = O5._load_ov5_decompressed(rom)
    data = bytearray(ov.data)
    off = _ai_row(bytes(data), ov.ramAddress)
    if off is None:
        print("[WARN] no ov5 CPU row for 0x14C3")
        return
    struct.pack_into("<I", data, off + 4, 0x023107C1)
    O5._save_ov5(rom, ov, bytes(data))
    rom.saveToFile(out)


def main(write_text=False, src=dsl.SRC, out=OUT):
    _dsl_main(write_text=write_text, src=src, out=out)
    _patch_ai_row(out)


def verify(out=OUT):
    import ndspy.rom
    ok = _dsl_verify(out)
    ov = O5._load_ov5_decompressed(ndspy.rom.NintendoDSRom.fromFile(out))
    off = _ai_row(bytes(ov.data), ov.ramAddress)
    good = off is None or struct.unpack_from("<I", bytes(ov.data), off + 4)[0] == 0x023107C1
    print(f"[{'PASS' if good else 'FAIL'}] ov5 CPU row for 0x14C3 -> always-true evaluator")
    return bool(ok) and good


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
