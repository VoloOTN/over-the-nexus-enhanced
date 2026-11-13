"""March of the Monarchs (Continuous Spell) on Kishido Spirit 0x15EC.  WHOLE CARD built (the Extra Deck lock is added: see the end of this docstring).  SINGLE-CARD TEST ROM, NOT SHIPPED.

    "Tribute Summoned monsters you control cannot be targeted by, or destroyed by, card effects. You cannot Special Summon monsters from the Extra Deck."

BUILT: the activation (a Continuous Spell record: cls0 {RES, 0, COND, COST, 0} over a cls0 phantom, like Fire Formation - Tenki; Kishido Spirit has NO cls0 record; its ONE code reference is the
battle-protection query literal @0x02198460 (`ldr r1,=0x15EC ; bl 0x021AC0C8` @0x02198314), repointed to a never-used phantom cid so a face-up March does not trigger it) and the protection:
  * "cannot be destroyed by card effects": a front on the survive check's default exit (the bl @0x021CC264 Block Dragon's C2 already fronts; ours sits AHEAD of
    CAVE_BD_C2W and tail-jumps to it).  Contract (Block Dragon c2_front): r4 = zone, r5 = side, [sp+8] = the destroyed card's cid; survive = `pop {r1-r7,pc}` with r0 = 1.
  * "cannot be targeted by card effects": a front on the targeting link bl @0x021B05CC (Safe Zone's CAVE3_SZ_TARGET stub is the chain head); contract (Safe Zone's
    _target3): r6 = the monster's side, r5 = its slot, r2 = 0x150A; a hit jumps to the predicate's "NOT affectable" exit 0x021B0296.
  * the shared leaf CAVE_MA_TEST(side, zone) (C, march.c): face-up monster, zone flag bit 3 = Tribute Summoned, a face-up March in the controller's S/T zones.
EXTRA DECK LOCK (researched 2026-11-10 with scratch/edlock_probe.py, CPU duels): three fronts, all asking CAVE_MA_LOCK(side) = a face-up March:
  * `bl is_synchro` @0x0224954E (can_synchro_summon, side in r4) and `bl is_fusion` @0x0223299A (can_fusion_summon, side in r7): inside the legality functions, so the human
    menu (hand-menu builder 0x0225E5xx), the Extra enumerator and the CPU's ov5 callers (LR 0x02341B1F / 0x0235E123) are all covered by ONE site each;
  * `bl 0x021AD8C4` @0x02269266 in the SS engine: Special Summons whose source zone is the Extra Deck (locator code 0xC; every Extra Deck summon reached the engine
    with code 12 in the probe, Synchro included) look like "no free zone", the engine's own bail-out; a backstop for effect summons that never ask the two predicates.
GAP kept: a procedure whose materials are paid BEFORE the engine runs would lose them to the backstop, but the legality fronts stop it being offered.
OLD NOTE (kept for the record): the gap was "You cannot Special Summon monsters from the Extra Deck".  There is no template: the summon gate 0x021B9708 is cid-blind and does not
know the source zone, and blocking the Special-Summon engine after the materials are paid would lose them.  It needs a measured hook on the Extra Deck offer path; it is shared
with Stormforth and Return (notes/monarch-megas-findings.md).

    uv run python _build_march.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS0, Compiled, Row
from otn_enhanced.effects import cave3, ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_march.nds"
MARCH = 0x15EC
CLS0_PHANTOM = 0x0E1E
KISHIDO_LIT = 0x02198460               # ov3 pool literal = 0x15EC: Kishido Spirit's native battle-protection query (needs a face-up Kishido Spirit; March has the same cid)
KISHIDO_PHANTOM = 0x2619               # a cid that is no card and appears nowhere in ov3 (asserted)
C_DIR = Path(__file__).resolve().parent / "c"

C2_SITE = 0x021CC264                  # the survive check's default-exit bl (Block Dragon's CAVE_BD_C2W is the chain head)
TGT_SITE = 0x021B05CC                 # the targeting link (Safe Zone's CAVE3_SZ_TARGET is the chain head)
TARGET_REJECT = 0x021B0296            # the predicate's "NOT affectable" exit
C2_PREV = O5.CAVE_BD_C2W
TGT_PREV = cave3.CAVE3_SZ_TARGET
IS_SYNCHRO, IS_FUSION, FREE_ZONE, LOCATOR = 0x02023050, 0x0202303C, 0x021AD8C4, 0x021A220C
HS_SITE, HF_SITE, HE_SITE = 0x0224954E, 0x0223299A, 0x02269266     # `bl is_synchro` / `bl is_fusion` / `bl free-zone check`
RESERVES = {"TINY": 0x10, "TEST": 0xA0, "C2W": 0x30, "TGT": 0x50, "LOCK": 0x140, "HS": 0x30, "HF": 0x30, "HE": 0x50}
for _a in (IS_SYNCHRO, IS_FUSION, FREE_ZONE, LOCATOR):
    assert _a % 2 == 0



def tiny_stubs(base: int) -> bytes:
    """+0 cond (movs r0,#1 ; bx lr), +4 cost (same), +8 res (movs r0,#0 ; bx lr), +0xC pad."""
    b = EffectBuilder()
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.insn("MOV", "R0, #0x0")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def c2_front(base: int, test: int) -> bytes:
    """Entered by the `bl` at the survive check's default exit (r4 zone, r5 side, [sp+8] = the destroyed card's cid; sp = the check's frame)."""
    b = EffectBuilder()
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("ADD", "R1, R4, #0x0")
    b.ldr_const(3, test | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "prev")
    b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")      # r0 = 1: the card survives
    b.label("prev")
    b.ldr_const(3, C2_PREV | 1)
    b.insn("BX", "R3")
    return b.assemble(base, pad="nop")


def tgt_front(base: int, test: int) -> bytes:
    """Entered by the `bl` at the targeting link (r6 = the monster's side, r5 = its slot, r2 = 0x150A, r0/r1 = the query's arguments).
    March-protected -> jump to the predicate's 'NOT affectable' exit (dropping our frame); else on to the previous head with every argument intact."""
    b = EffectBuilder()
    b.insn("PUSH", "{R0, R1, R2, R4, LR}")
    b.insn("ADD", "R0, R6, #0x0")
    b.insn("ADD", "R1, R5, #0x0")
    b.ldr_const(3, test | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "prev")
    b.insn("POP", "{R0, R1, R2, R4}")
    b.insn("POP", "{R3}")                                   # the dropped LR
    b.ldr_const(0, TARGET_REJECT | 1)
    b.insn("BX", "R0")
    b.label("prev")
    b.insn("POP", "{R0, R1, R2, R4}")
    b.insn("POP", "{R3}")
    b.insn("MOV", "LR, R3")
    b.ldr_const(3, TGT_PREV | 1)
    b.insn("BX", "R3")
    return b.assemble(base, pad="nop")


def hs_stub(base: int, lock: int, side_reg: int, native: int) -> bytes:
    """`bl <native test>` front inside can_synchro_summon (side in r4) / can_fusion_summon (side in r7): the native test runs; a hit under the lock becomes 'no'."""
    b = EffectBuilder()
    b.insn("PUSH", "{LR}")
    b.ldr_const(3, native | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "out")
    b.insn("PUSH", "{R0}")
    b.insn("ADD", f"R0, R{side_reg}, #0x0")
    b.ldr_const(3, lock | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("POP", "{R0}")                        # the native verdict (pop does not touch the flags)
    b.insn("BEQ", "out")
    b.insn("MOV", "R0, #0x0")
    b.label("out")
    b.insn("POP", "{PC}")
    return b.assemble(base, pad="nop")


def he_stub(base: int, lock: int) -> bytes:
    """SS engine `bl 0x021AD8C4(side)` front (r0 = side, r6 = &card word): -1 ('no free zone', the engine's own bail-out) when the side is locked and the card is
    coming from the Extra Deck (the locator's zone code 0xC, the same lookup the engine does a few instructions later)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.ldr_const(3, FREE_ZONE | 1)
    b.insn("BLX", "R3")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("CMP", "R5, #0x0")
    b.insn("BLT", "done")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, lock | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "done")
    b.insn("LDR", "R0, [R6, #0x0]")              # the card word -> ref -> where it lives
    b.insn("LSL", "R1, R0, #1")
    b.insn("LSR", "R1, R1, #0x18")
    b.insn("LSL", "R1, R1, #1")
    b.insn("LSL", "R2, R0, #0x11")
    b.insn("LSR", "R2, R2, #0x1F")
    b.insn("ADD", "R0, R1, R2")
    b.ldr_const(3, LOCATOR | 1)
    b.insn("BLX", "R3")
    b.insn("LSL", "R0, R0, #0x10")
    b.insn("LSR", "R0, R0, #0x18")               # zone code
    b.insn("CMP", "R0, #0xC")
    b.insn("BNE", "done")
    b.insn("MOV", "R5, #0x0")
    b.insn("MVN", "R5, R5")                      # -1
    b.label("done")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("POP", "{R4, R5, PC}")
    return b.assemble(base, pad="nop")


@dataclass(frozen=True)
class march:
    cid: int = MARCH

    def blobs(self):
        test = compile_c(C_DIR / "march.c", O5.CAVE_MA_TEST)
        return {"TINY": (O5.CAVE_MA_TINY, tiny_stubs(O5.CAVE_MA_TINY), "March cond / cost / res"),
                "TEST": (O5.CAVE_MA_TEST, test, "March protects (side, zone)? (C)"),
                "C2W": (O5.CAVE_MA_C2W, c2_front(O5.CAVE_MA_C2W, O5.CAVE_MA_TEST), "survive-check front"),
                "TGT": (O5.CAVE_MA_TGT, tgt_front(O5.CAVE_MA_TGT, O5.CAVE_MA_TEST), "targeting-link front"),
                "LOCK": (O5.CAVE_MA_LOCK, compile_c(C_DIR / "edlock.c", O5.CAVE_MA_LOCK), "ED_LOCK(side) (C)"),
                "HS": (O5.CAVE_MA_HS, hs_stub(O5.CAVE_MA_HS, O5.CAVE_MA_LOCK, 4, IS_SYNCHRO), "Synchro legality front"),
                "HF": (O5.CAVE_MA_HF, hs_stub(O5.CAVE_MA_HF, O5.CAVE_MA_LOCK, 7, IS_FUSION), "Fusion legality front"),
                "HE": (O5.CAVE_MA_HE, he_stub(O5.CAVE_MA_HE, O5.CAVE_MA_LOCK), "SS engine Extra Deck backstop")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            assert len(blob) <= RESERVES[key], f"{key}: {len(blob):#x} B > {RESERVES[key]:#x}"
            assert_thumb1_only(blob, addr)
        rec = (MARCH, O5.CAVE_MA_TINY + 8 | 1, 0, O5.CAVE_MA_TINY | 1, O5.CAVE_MA_TINY + 4 | 1, 0)
        sites = ((C2_SITE, C2_PREV, O5.CAVE_MA_C2W, "survive-check exit"), (TGT_SITE, TGT_PREV, O5.CAVE_MA_TGT, "targeting link"),
                 (HS_SITE, IS_SYNCHRO, O5.CAVE_MA_HS, "can_synchro_summon is_synchro test"), (HF_SITE, IS_FUSION, O5.CAVE_MA_HF, "can_fusion_summon is_fusion test"),
                 (HE_SITE, FREE_ZONE, O5.CAVE_MA_HE, "SS engine free-zone check"))

        def install(rom, v):
            assert v.u32(KISHIDO_LIT) in (MARCH, KISHIDO_PHANTOM), f"Kishido literal @{KISHIDO_LIT:#x} = {v.u32(KISHIDO_LIT):#x}"
            v.pack(KISHIDO_LIT, "<I", KISHIDO_PHANTOM)
            for site, prev, mine, what in sites:
                cur = ov3_bl_target(v.buf, site)
                assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (the chain head) or ours"
                v.write(site, common_bl(site, mine))

        def check(c, rom, v):
            c.eq(v.u32(KISHIDO_LIT), KISHIDO_PHANTOM, "Kishido Spirit's native battle-protection literal -> phantom (March does not trigger it)")
            for site, prev, mine, what in sites:
                c.ok(code_reaches(rom, site, mine), f"{what} @{site:#x} reaches March's front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")

        return Compiled(tuple(blobs.values()), (Row(CLS0, rec, CLS0_PHANTOM),), installs=(install,), checks=(check,))


SPEC = march()
main, verify = dsl.make(SPEC, None, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
