"""The Monarchs Stormforth (Quick-Play Spell) on Tailor of the Fickle 0x1328.  SINGLE-CARD TEST ROM, NOT SHIPPED.

    "Once during this turn, if you would Tribute a monster for a Tribute Summon, you can Tribute 1 monster your opponent controls even though you do not control it.
     You can only activate 1 "The Monarchs Stormforth" per turn.  During the turn you activate this card, you cannot Special Summon monsters from the Extra Deck."

Mechanism (disassembled 2026-11-10; see notes/monarch-megas-findings.md, Stormforth section):
  * activation   the donor's one cls0 record rewritten in place (dsl.Edit) to the Continuous-Spell shape {cid, RES|1, 0, COND|1, COST|1, 0} (Tenki / March):
                 COND = kind-1 turn-log node for (side, 0x1328) not posted (the "only 1 per turn" clause); COST = post that node (skipped in a replay); RES = no-op.
                 The node is also the latch for everything else: "activated this turn".
  * ED lock      edlock.c's TLQ(side, 0xB, 0x1328, 1): shared with March, same three fronts and the same cave slots (CAVE_MA_LOCK/HS/HF/HE), so a combined ROM carries one lock stack.
  * permission   the Tribute-release core 0x021AD8F4 (player, controller, slot, mode) refuses a monster the player does not control unless a rider-node family (keys 0xDDE / 0x13EB,
                 queried with `bl 0x021A14B4` @0x021AD94A / 0x021AD95A) is attached to it.  Front over the first query: native answer first; else, while the SUMMON-RELEASE flag
                 is up, 1 if side `player` has the activation node and has NOT used the opponent-Tribute (node under key USED).
  * flag         `bl 0x021AD8F4` @0x021AE102 is the tail of 0x021ADC90 (the Tribute Summon's release query: callers 0x0225DC3A, 0x02260078, 0x021AE354).  A wrapper raises the flag
                 around the core, so cost payments that reach the core through the wrappers 0x021AE124 / 0x021AE130 / 0x021AE13C never get the permission.
  * used         the four `bl 0x021CF68C(player, slot mask)` Tribute payments: a mask bit on the OTHER side (mask = 1 << (side * 16 + slot)) posts USED.
KNOWN GAPS / UNPROVEN (nothing here is in-game confirmed):
  * the permission has never been exercised: the CPU never Tributes the opponent's monsters, so only the user's duel can show it.  Pre-build evidence is static (this docstring).
  * the wrapper at 0x021AE102 covers ONLY the ADC90 path; the other summon-picker route (0x02260058 -> wrapper 0x021AE130 mode 0, taken when [0x02298A28 + 0x16] != 0) is NOT covered.
  * "used" is posted at payment, so a Tribute Summon that is cancelled after the opponent's monster was chosen but before payment does not consume it (correct) ... and one
    cancelled AFTER payment cannot happen (payment is the commit).
  * USED is a turn-log key 0x261A that is not a card (kind-1 nodes are only ever queried by exact key).
Composition: the PAY sites are also fronted by mega_monarch's CAP stub; this module installs over the NATIVE bl and refuses to run on top of CAP (combined build needs a chain: see the findings).

    uv run python _build_stormforth.py
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
from otn_enhanced.cards import march as M
from otn_enhanced.dsl import CLS0, Compiled, Edit, _COPY_EXEMPT_BX, _TURNLOG_POST_ODD, _TURNLOG_QUERY_ODD
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

CHAIN = M.CHAIN
import os
TEST_ALWAYS = bool(os.environ.get("SF_ALWAYS"))        # TEST-ONLY variant: the permission front ignores the activation node (isolates the CPU's Tribute choice)
TEST_OWNTURN = bool(os.environ.get("SF_OWNTURN"))      # TEST-ONLY variant: the cond only allows activation in its owner's own Main Phase 1 (forces the CPU to use it before summoning)
OUT = ("data/over_the_nexus/working/rom_stormforth_always.nds" if TEST_ALWAYS else
       "data/over_the_nexus/working/rom_stormforth_own.nds" if TEST_OWNTURN else "data/over_the_nexus/working/rom_stormforth.nds")
STORM = 0x1328
USED = 0x261A                                  # turn-log key for "the opponent-Tribute was used this turn" (not a card)
NATIVE = (STORM, 0x0220E22D, 0x021DB2D1, 0, 0, 0x02236539)           # the donor's cls0 record, stock AND chain (read 2026-11-10)
C_DIR = Path(__file__).resolve().parent / "c"

QUERY14B4 = 0x021A14B4
PERM_SITE, WRAP_SITE = 0x021AD94A, 0x021AE102
CORE = 0x021AD8F4
TRIB_PAY = 0x021CF68C
PAY_SITES = (0x02262574, 0x02266F7E, 0x02267BF6, 0x02268DA4)
RES = {"COND": 0x30, "COST": 0x30, "RES": 0x10, "PERM": 0x60, "WRAP": 0x30, "PAY": 0x50, "FLAG": 0x10}


def _side(b: EffectBuilder, dst: int, desc: int) -> None:
    b.insn("LDRB", f"R{dst}, [R{desc}, #0x2]")
    b.insn("LDRB", f"R0, [R{desc}, #0x6]")
    b.insn("EOR", f"R{dst}, R0")


def cond_stub(base: int) -> bytes:
    """cls0 cond (r0 = desc): menu check (desc[+7] == 0) -> 0 if the activation node is already posted this turn, else 1."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    _side(b, 5, 4)
    b.insn("LDRB", "R0, [R4, #0x7]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "yes")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", "R1, #0xB")
    b.ldr_const(2, STORM)
    b.insn("MOV", "R3, #0x1")
    b.ldr_const(6, _TURNLOG_QUERY_ODD)
    b.insn("BLX", "R6")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "no")
    b.label("yes")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, R6, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, PC}")
    return b.assemble(base, pad="nop")


OWN_GATE = 0x023AFDC0                                   # TEST-ONLY: the unused 0x50 B hole left by the relocated LOCK slot


def own_gate_stub(base: int, cond: int) -> bytes:
    """Test variant: in its owner's own Main Phase 1 (turn player [0x0229DD14+0x34] == side, phase [+0x48] == 2) the real cond runs and, if it says 'activatable'
    (node not posted), the activation node is POSTED right here (the CPU never plays the card in its own Main Phase, so the activation is simulated); else 0."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("LDRB", "R5, [R4, #0x2]")
    b.insn("LDRB", "R2, [R4, #0x6]")
    b.insn("EOR", "R5, R2")
    b.ldr_const(0, 0x0229DD14)
    b.insn("LDR", "R2, [R0, #0x34]")
    b.insn("CMP", "R2, R5")
    b.insn("BNE", "no")
    b.insn("LDR", "R2, [R0, #0x48]")
    b.insn("CMP", "R2, #0x2")
    b.insn("BNE", "no")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, cond | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "no")
    b.insn("ADD", "R0, R5, #0x0")
    b.ldr_const(1, STORM)
    b.insn("MOV", "R2, #0x1")
    b.insn("MOV", "R3, #0x0")
    b.ldr_const(4, _TURNLOG_POST_ODD)
    b.insn("BLX", "R4")
    b.insn("MOV", "R0, #0x0")                           # the post is done; hide the card from the CPU's menu
    b.insn("POP", "{R4, R5, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, PC}")
    return b.assemble(base, pad="nop")


def cost_stub(base: int) -> bytes:
    """cls0 cost: post the kind-1 node (side, 0x1328) (skipped in a replay, 0x021D2B89)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.ldr_const(3, _COPY_EXEMPT_BX)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "done")
    _side(b, 5, 4)
    b.insn("ADD", "R0, R5, #0x0")
    b.ldr_const(1, STORM)
    b.insn("MOV", "R2, #0x1")
    b.insn("MOV", "R3, #0x0")
    b.ldr_const(4, _TURNLOG_POST_ODD)
    b.insn("BLX", "R4")
    b.label("done")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, PC}")
    return b.assemble(base, pad="nop")


def res_stub(base: int) -> bytes:
    b = EffectBuilder()
    b.insn("MOV", "R0, #0x0")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def perm_stub(base: int, flag: int) -> bytes:
    """Entered by `bl 0x021A14B4(controller r0, slot r1, key 0xDDE r2, player r3)` inside the release core: native answer; else, in a Tribute Summon release query,
    1 when `player` activated Stormforth this turn and has not used the opponent-Tribute."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, LR}")
    b.ldr_const(4, QUERY14B4 | 1)
    b.insn("BLX", "R4")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "out")
    b.ldr_const(1, flag)
    b.insn("LDR", "R1, [R1, #0x0]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BEQ", "out")
    if TEST_ALWAYS:
        b.insn("MOV", "R0, #0x1")
        b.insn("B", "out")
    b.insn("LDR", "R0, [SP, #0x8]")                     # player
    b.insn("MOV", "R1, #0xB")
    b.ldr_const(2, STORM)
    b.insn("MOV", "R3, #0x1")
    b.ldr_const(4, _TURNLOG_QUERY_ODD)
    b.insn("BLX", "R4")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "no")                                 # not activated this turn
    b.insn("LDR", "R0, [SP, #0x8]")
    b.insn("MOV", "R1, #0xB")
    b.ldr_const(2, USED)
    b.insn("MOV", "R3, #0x1")
    b.ldr_const(4, _TURNLOG_QUERY_ODD)
    b.insn("BLX", "R4")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "no")                                 # already used
    b.insn("MOV", "R0, #0x1")
    b.insn("B", "out")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.label("out")
    b.insn("POP", "{R1, R2, R3, R4, PC}")
    return b.assemble(base, pad="nop")


def wrap_stub(base: int, flag: int) -> bytes:
    """Entered by `bl 0x021AD8F4(player, controller, slot, mode)` @0x021AE102: raise the flag around the core (arguments and result untouched)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.ldr_const(4, flag)
    b.insn("MOV", "R5, #0x1")
    b.insn("STR", "R5, [R4, #0x0]")
    b.ldr_const(5, CORE | 1)
    b.insn("BLX", "R5")
    b.insn("MOV", "R5, #0x0")
    b.insn("STR", "R5, [R4, #0x0]")
    b.insn("POP", "{R4, R5, PC}")
    return b.assemble(base, pad="nop")


def pay_stub(base: int) -> bytes:
    """Entered by `bl 0x021CF68C(player r0, slot mask r1)`: a mask bit on the other side (bit side*16+slot) posts the USED node, then the native payment."""
    b = EffectBuilder()
    b.insn("PUSH", "{R0, R1, R4, LR}")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "p1")
    b.insn("LSR", "R2, R1, #0x10")                      # player 0: the opponent is bits 16..31
    b.insn("B", "chk")
    b.label("p1")
    b.insn("LSL", "R2, R1, #0x10")                      # player 1: the opponent is bits 0..15
    b.label("chk")
    b.insn("CMP", "R2, #0x0")
    b.insn("BEQ", "tail")
    b.ldr_const(1, USED)
    b.insn("MOV", "R2, #0x1")
    b.insn("MOV", "R3, #0x0")
    b.ldr_const(4, _TURNLOG_POST_ODD)
    b.insn("BLX", "R4")
    b.label("tail")
    b.insn("POP", "{R0, R1, R4}")
    b.insn("POP", "{R2}")                               # the saved LR
    b.insn("MOV", "LR, R2")
    b.ldr_const(2, TRIB_PAY | 1)
    b.insn("BX", "R2")
    return b.assemble(base, pad="nop")


@dataclass(frozen=True)
class stormforth:
    cid: int = STORM

    def blobs(self):
        return {"COND": (O5.CAVE_SF_COND, cond_stub(O5.CAVE_SF_COND), "cond: HOPT query"),
                **({"GATE": (OWN_GATE, own_gate_stub(OWN_GATE, O5.CAVE_SF_COND), "TEST-ONLY own-turn gate")} if TEST_OWNTURN else {}),
                "COST": (O5.CAVE_SF_COST, cost_stub(O5.CAVE_SF_COST), "cost: post the activation node"),
                "RES": (O5.CAVE_SF_RES, res_stub(O5.CAVE_SF_RES), "res: no-op"),
                "PERM": (O5.CAVE_SF_PERM, perm_stub(O5.CAVE_SF_PERM, O5.CAVE_SF_FLAG), "release-core permission front"),
                "WRAP": (O5.CAVE_SF_WRAP, wrap_stub(O5.CAVE_SF_WRAP, O5.CAVE_SF_FLAG), "summon-release flag wrapper"),
                "PAY": (O5.CAVE_SF_PAY, pay_stub(O5.CAVE_SF_PAY), "Tribute-payment 'used' front"),
                "FLAG": (O5.CAVE_SF_FLAG, bytes(4), "summon-release flag word"),
                # the shared Extra Deck lock stack (identical bytes to march.py's: a combined ROM writes them twice)
                "LOCK": (O5.CAVE_MA_LOCK, compile_c(C_DIR / "edlock.c", O5.CAVE_MA_LOCK), "ED_LOCK(side) (C)"),
                "HS": (O5.CAVE_MA_HS, M.hs_stub(O5.CAVE_MA_HS, O5.CAVE_MA_LOCK, 4, M.IS_SYNCHRO), "Synchro legality front"),
                "HF": (O5.CAVE_MA_HF, M.hs_stub(O5.CAVE_MA_HF, O5.CAVE_MA_LOCK, 7, M.IS_FUSION), "Fusion legality front"),
                "HE": (O5.CAVE_MA_HE, M.he_stub(O5.CAVE_MA_HE, O5.CAVE_MA_LOCK), "SS engine Extra Deck backstop")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        res = dict(RES, GATE=0x50, **{k: M.RESERVES[k] for k in ("LOCK", "HS", "HF", "HE")})
        for key, (addr, blob, _) in blobs.items():
            assert len(blob) <= res[key], f"{key}: {len(blob):#x} B > {res[key]:#x}"
            if key != "FLAG":
                assert_thumb1_only(blob, addr)
        patched = (STORM, O5.CAVE_SF_RES | 1, 0, (OWN_GATE if TEST_OWNTURN else O5.CAVE_SF_COND) | 1, O5.CAVE_SF_COST | 1, 0)
        sites = [(PERM_SITE, QUERY14B4, O5.CAVE_SF_PERM, "release-core node query"), (WRAP_SITE, CORE, O5.CAVE_SF_WRAP, "summon-release core call"),
                 (M.HS_SITE, M.IS_SYNCHRO, O5.CAVE_MA_HS, "can_synchro_summon is_synchro test"), (M.HF_SITE, M.IS_FUSION, O5.CAVE_MA_HF, "can_fusion_summon is_fusion test"),
                 (M.HE_SITE, M.FREE_ZONE, O5.CAVE_MA_HE, "SS engine free-zone check")]
        sites += [(s, TRIB_PAY, O5.CAVE_SF_PAY, f"Tribute payment {s:#x}") for s in PAY_SITES]

        def install(rom, v):
            for site, prev, mine, what in sites:
                cur = ov3_bl_target(v.buf, site)
                if O5.combo() and cur == O5.CAVE_MM_CAP and site in PAY_SITES:
                    continue                    # MONARCH_COMBO: mega_monarch's CAP front owns the site and tails to our PAY stub
                assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (native) or ours"
                v.write(site, common_bl(site, mine))

        def check(c, rom, v):
            for site, prev, mine, what in sites:
                c.ok(code_reaches(rom, site, mine), f"{what} @{site:#x} reaches Stormforth's front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")

        return Compiled(tuple(blobs.values()), edits=(Edit(CLS0, STORM, NATIVE, patched),), installs=(install,), checks=(check,))


SPEC = stormforth()
main, verify = dsl.make(SPEC, None, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
