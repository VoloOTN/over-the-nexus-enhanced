"""The Monarchs Erupt (Continuous Trap) on Respect Play 0x135E.  E1 + E2 + E3 built.  SINGLE-CARD TEST ROM, NOT SHIPPED,
nothing here is in-game confirmed.

    "Activate this card only if you have no cards in your Extra Deck and control a Tribute Summoned monster. Negate the effects of all face-up monsters on
     the field, while those monsters are face-up on the field, except Tribute Summoned monsters'. During your End Phase, if you control no Tribute Summoned
     monsters, send this card to the Graveyard."

Design (notes/erupt-findings.md):
  * Activation = cls0 {RES, 0, COND, COST, 0} over cls0 phantom 0x0E3B (March's Continuous Spell shape; Battle-Scarred proves Traps use cls0 too).
    Respect Play has no record and no ov3/ov5 reference (halfword scan 2026-11-11).
  * E1 COND (erupt.c ER_COND): own Extra Deck count (player + 0x18) == 0 and an own face-up monster with zone flag bit 3 (Tribute Summoned).
  * E2: 0x021EE3DC(side, zone) is the native per-card "effects negated" gate; its only two BL callers are the resolution negate 0x021D3AA0 (@0x021D3AE6)
    and the continuous monster-negate check 0x021EE4E4 (@0x021EE4F6).  Both get one shared front: native first, then ER_TEST(side, zone).
  * E3: End-Phase registry row 277 {0x02255959 generic maintenance walker, cid 0} gets ER_EP as its fn: on the turn player's first pass, a face-up
    own Erupt with no own face-up Tribute Summoned monster is queued to the GY (0x021CF6B8, NAST's send) and the row asks to be re-called (0);
    otherwise the native walker runs unchanged.

    uv run python _build_erupt.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS0, Compiled, Row
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

CHAIN = "data/over_the_nexus/working/rom_chain_19C00.nds"
OUT = "data/over_the_nexus/working/rom_erupt.nds"
ERUPT = 0x135E
CLS0_PHANTOM = 0x0E3B
NEG_GATE = 0x021EE3DC                   # push {r3-r7,lr}: (side, zone) -> 1 if negated
NEG_SITES = (0x021D3AE6, 0x021EE4F6)    # resolution negate 0x021D3AA0 / continuous monster negate 0x021EE4E4
EP_ROW, EP_WALKER = 0x0228EA88, 0x02255959   # End-Phase registry row 277 {generic maintenance walker, cid 0}
C_DIR = Path(__file__).resolve().parent / "c"
RESERVES = {"TINY": 0x10, "COND": 0x80, "TEST": 0xC0, "NEG": 0x30, "EP": 0x100}
S = {k: getattr(O5, f"CAVE_ER_{k}") for k in RESERVES}


def tiny_stubs(base: int) -> bytes:
    """+0 cost (movs r0,#1 ; bx lr), +4 res (movs r0,#0 ; bx lr)."""
    b = EffectBuilder()
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.insn("MOV", "R0, #0x0")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def neg_front(base: int) -> bytes:
    """Replaces `bl 0x021EE3DC` (r0 = side, r1 = zone): the native gate first, then Erupt's test."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.ldr_const(3, NEG_GATE | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "out")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("ADD", "R1, R5, #0x0")
    b.ldr_const(3, S["TEST"] | 1)
    b.insn("BLX", "R3")
    b.label("out")
    b.insn("POP", "{R4, R5, PC}")
    return b.assemble(base, pad="nop")


class the_monarchs_erupt:
    cid: int = ERUPT

    def blobs(self):
        return {"TINY": (S["TINY"], tiny_stubs(S["TINY"]), "Erupt cost / res"),
                "COND": (S["COND"], compile_c(C_DIR / "erupt.c", S["COND"], {"STUB": "ER_COND"}), "E1 activation cond (C)"),
                "TEST": (S["TEST"], compile_c(C_DIR / "erupt.c", S["TEST"], {"STUB": "ER_TEST"}), "E2 negate test (C)"),
                "NEG": (S["NEG"], neg_front(S["NEG"]), "negate-gate front"),
                "EP": (S["EP"], compile_c(C_DIR / "erupt.c", S["EP"], {"STUB": "ER_EP"}), "E3 End-Phase walker front (C)")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            assert len(blob) <= RESERVES[key], f"{key}: {len(blob):#x} B > {RESERVES[key]:#x}"
            assert_thumb1_only(blob, addr)
        rec = (ERUPT, S["TINY"] + 4 | 1, 0, S["COND"] | 1, S["TINY"] | 1, 0)

        def install(rom, v):
            for site in NEG_SITES:
                cur = ov3_bl_target(v.buf, site)
                assert cur in (NEG_GATE, S["NEG"]), f"bl @{site:#x} calls {cur:#x}, expected {NEG_GATE:#x} (or ours)"
                v.write(site, common_bl(site, S["NEG"]))
            row = tuple(v.unpack(EP_ROW, "<IH"))
            assert row in ((EP_WALKER, 0), (S["EP"] | 1, 0)), f"End-Phase registry row 277 = {row}"
            v.pack(EP_ROW, "<I", S["EP"] | 1)

        def check(c, rom, v):
            for site in NEG_SITES:
                c.eq(ov3_bl_target(v.buf, site), S["NEG"], f"negate gate bl @{site:#x} -> Erupt's front")
            c.eq(tuple(v.unpack(EP_ROW, "<IH")), (S["EP"] | 1, 0), "End-Phase registry row 277 -> Erupt's E3 front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")

        return Compiled(tuple(blobs.values()), (Row(CLS0, rec, CLS0_PHANTOM),), installs=(install,), checks=(check,))


SPEC = the_monarchs_erupt()
main, verify = dsl.make(SPEC, None, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
