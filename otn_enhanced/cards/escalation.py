"""Escalation of the Monarchs (Continuous Trap) on Enervating Mist 0x1800 (a records-free Continuous Trap).  TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "Once per turn, during your opponent's Main Phase or your opponent's Battle Phase, you can: Immediately after this effect resolves, Tribute Summon 1 monster."

Design (notes/escalation-findings.md)
  * Activation = cls0 {RES, 0, ALWAYS, COST, 0} over cls0 phantom 0x0E71 (Erupt's shape: a Continuous Trap with no activation effect).
  * Effect = cls3 {+04 0x0220D80D, +0C ES_COND, +10 ES_COST} over cls3 phantom 0x152C.  0x0220D80D is Cry Havoc!'s resolver: the engine's native "Normal Summon from the hand as an
    effect" machine (candidate count -> prompt 0x27 -> hand picker 0x0224B9C8 -> the standard summon state machine, which runs the Tribute selection).  It asks the per-cid
    predicate lookup 0x0220D7B4(acting cid); for this cid a front on that function's BL call at 0x0220D81C answers ES_PRED: hand monsters of
    Level 5 or higher only (mask 0x10 = Summon).
  * "Monarch" Spell/Trap set code: 0x1800 joins tenacity.MONARCH.
UNPROVEN: that the summon legality (0x0225D6D4) accepts a Summon on the OPPONENT's turn; that the effect offers in the opponent's Main/Battle Phase (the cls3 offer path for a
Continuous Trap); the phase numbering (2 Main 1, 3 Battle, 4 Main 2 read from CPU traces: End Phase = 5, Main = 2).

    uv run python -m otn_enhanced.cards.escalation
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS0, CLS3, Compiled, Row
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

ESC = 0x1800
CHAIN = "data/over_the_nexus/working/rom_chain_19C00.nds"
OUT = "data/over_the_nexus/working/rom_escalation.nds"
C_DIR = Path(__file__).resolve().parent / "c"
CLS0_PHANTOM, CLS3_PHANTOM = 0x0E71, 0x152C
NS_RESOLVER = 0x0220D80D                      # Cry Havoc!'s cls3 +04
PRED_LOOKUP = 0x0220D7B4                      # (acting cid) -> hand predicate or 0
PRED_SITES = (0x0220D81C,)                    # the resolver's own call; the other two callers (0x02200BF2 / 0x02222488) serve other cards' paths
PRED_TAIL = 0x021F0FD8                        # what that site calls in the chain: a cave3 front (Sakitama's) that tails to the native lookup
ALWAYS = 0x0224A115                           # movs r0,#2 ; bx lr
for _v in (NS_RESOLVER, ALWAYS):
    assert _v & 1

RESERVES = {"TINY": 0x10, "COND": 0x100, "COST": 0x30, "PRED": 0x50, "FRONT": 0x40, "PREH": 0x40}
S = {k: getattr(O5, f"CAVE_EC_{k}") for k in RESERVES}


def tiny_stubs(base: int) -> bytes:
    """+0 cost (movs r0,#1 ; bx lr), +4 res (movs r0,#0 ; bx lr)."""
    b = EffectBuilder()
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.insn("MOV", "R0, #0x0")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def front_stub(base: int) -> bytes:
    """Replaces `bl 0x0220D7B4` (r0 = the acting cid): Escalation gets its predicate, everyone else the native lookup (LR untouched)."""
    b = EffectBuilder()
    b.ldr_const(3, ESC)
    b.insn("CMP", "R0, R3")
    b.insn("BEQ", "hit")
    b.ldr_const(3, 0x1312)                         # Ehther's E2 (cards/erebus.py) shares this resolver
    b.insn("CMP", "R0, R3")
    b.insn("BEQ", "hit2")
    b.ldr_const(3, 0x0D6A)                         # The Monarchs Masterplan C2 (cards/masterplan.py): only the six named Monarchs
    b.insn("CMP", "R0, R3")
    b.insn("BEQ", "hit3")
    b.ldr_const(3, PRED_TAIL | 1)
    b.insn("BX", "R3")
    b.label("hit")
    b.ldr_const(0, S["PRED"] | 1)
    b.insn("BX", "LR")
    b.label("hit2")
    b.ldr_const(0, S["PREH"] | 1)
    b.insn("BX", "LR")
    b.label("hit3")
    b.ldr_const(0, O5.CAVE_MP_NSPRED | 1)
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def _c(stub: str, slot: str) -> bytes:
    return compile_c(C_DIR / "escalation.c", S[slot], {"STUB": stub})


class escalation_of_the_monarchs:
    cid: int = ESC

    def blobs(self):
        return {"TINY": (S["TINY"], tiny_stubs(S["TINY"]), "cls0 cost / res"),
                "COND": (S["COND"], _c("ES_COND", "COND"), "cls3 +0C cond (C)"),
                "COST": (S["COST"], _c("ES_COST", "COST"), "cls3 +10 once-per-turn stamp (C)"),
                "PRED": (S["PRED"], _c("ES_PRED", "PRED"), "hand predicate: Level 5+ (C)"),
                "PREH": (S["PREH"], _c("ES_PRED_EH", "PREH"), "hand predicate: Ehther (C)"),
                "FRONT": (S["FRONT"], front_stub(S["FRONT"]), "predicate-lookup front")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            assert len(blob) <= RESERVES[key], f"{key}: {len(blob):#x} B > {RESERVES[key]:#x}"
            assert_thumb1_only(blob, addr)
        rec0 = (ESC, S["TINY"] + 4 | 1, 0, ALWAYS, S["TINY"] | 1, 0)
        rec3 = (ESC, NS_RESOLVER, 0, S["COND"] | 1, S["COST"] | 1, 0)

        def install(rom, v):
            for site in PRED_SITES:
                cur = ov3_bl_target(v.buf, site)
                assert cur in (PRED_TAIL, S["FRONT"]), f"bl @{site:#x} calls {cur:#x}, expected {PRED_TAIL:#x} (or ours)"
                v.write(site, common_bl(site, S["FRONT"]))

        def check(c, rom, v):
            for site in PRED_SITES:
                c.eq(ov3_bl_target(v.buf, site), S["FRONT"], f"predicate lookup bl @{site:#x} -> Escalation's front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")

        return Compiled(tuple(blobs.values()), rows=(Row(CLS0, rec0, CLS0_PHANTOM), Row(CLS3, rec3, CLS3_PHANTOM)), installs=(install,), checks=(check,))


SPEC = escalation_of_the_monarchs()
main, verify = dsl.make(SPEC, None, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
