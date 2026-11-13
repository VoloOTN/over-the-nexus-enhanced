"""Block Dragon (0x0FDD, donor Giant Flea): Lv8 EARTH Rock 2500/3000. NOT SHIPPED: the user pulled the ship approval 2026-11-09 ("I said ship too soon") until the GY-origin summon is built.

  C1  "Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand or GY) by banishing 3 EARTH monsters from your hand and/or GY."
        BUILT: NS/Set block (nomi class 4, phantom 0x0E22) + the HAND Special Summon (virtual cls2 record, 3-pick banish cost over hand + GY) + CPU legality/payment.
        NOT BUILT: the GY-ORIGIN Special Summon. The printed text allows it; this card cannot do it. That is a known gap, not a deviation.
  C2  Rock monsters you control cannot be destroyed except by battle: chained front on the survive check 0x021CC028's default exit.
  C3  Sent field -> GY: add up to 3 Rocks from the Deck, total Level 8, once per turn (leave-mask trigger, stepwise Level-sum picker).
In-game: user 2026-11-09 "I have tested C2 and the hand summon, they work for me"; C3 "i have tested it and can confirm it works"; 2026-11-09 "Tested banishing
from hand or GY and it works. Ship". Itemised checks were not listed. Design, proofs, ruled-out routes: notes/block-dragon-findings.md.

    uv run python _build_block_dragon.py      # single-card test ROM on the chain
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R3, R4, R5, R6, R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import Compiled, LEAVE_MASK, Row, archetype_member, card, card_props
from otn_enhanced.cards.windrose import NOMI_CLASS_4_TABLE
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import ov3_bl_target, bl as common_bl, RAM_BASE as _RB

BD = 0x0FDD
C_DIR = Path(__file__).resolve().parent / "c"
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_block_dragon.nds"
IDX = 0xFF40                                    # virtual criteria index (Disguise 0xFF00|j, Medraut 0xFF10, Gearfried 0xFF20, Predaplant 0xFF30..32)
PICKS = 3

# --- natives (Thumb, odd) ----------------------------------------------------------------------------------------
IS_MONSTER, GET_ATTR = 0x02029E61, 0x0202ABC9
SHORT, MESSAGE, PICKER, READBACK = 0x021D2BC9, 0x0219A819, 0x0219C431, 0x0219C511
CPUSH, CPOP = 0x021D28A5, 0x021D2965
HINDEX, HBANISH, R2W, GBANISH = 0x021A25A1, 0x021C6E99, 0x021A25E9, 0x021C7105
HAND_BUILDER, GY_BUILDER = 0x0223C16D, 0x0223C4E9
HANDSS_RES = 0x02206ABD
H3_RESUME = 0x02243F71
ACTING, STATE = 0x0229A9FC, 0x0229AAFC
BANISH_FLAGS, PROMPT, EARTH = 0x10000, 0x56, 5
for _v in (IS_MONSTER, GET_ATTR, SHORT, MESSAGE, PICKER, READBACK, CPUSH, CPOP, HINDEX, HBANISH, R2W, GBANISH, HAND_BUILDER, GY_BUILDER,
           HANDSS_RES, H3_RESUME):
    assert _v & 1, f"{_v:#x}: blx/bx to an even literal switches to ARM state -> freeze"

# --- shared sites and the owner each must hold BEFORE us (chain ROM 2026-11-06, read this session) ------------------------
H1_SITE, H1_PREV = 0x0224A86A, O5.CAVE_GF_H1                 # find_event_handler miss tail -> Gearfried's H1 (-> Dragon Rulers' H1)
H2_SITE, H2_PREV = 0x02243F24, O5.CAVE_PD_H2                 # Predaplant's front (-> Gearfried's -> Medraut's)
H3_SITE, H3_PREV = 0x02243F62, O5.CAVE_PD_H3
H4_SITE, H4_PREV = 0x02023566, O5.CAVE_GF_H4                 # ARM9, Gearfried's front (-> Disguise's)

S = {n: getattr(O5, f"CAVE_BD_{n}") for n in ("ROWS", "VREC", "C1_COND", "C1_COST", "C1_H", "C1_FILT", "C1_S5", "H1", "H2", "H3", "H4", "AI", "C2W", "C2", "C3REC", "C3COND", "C3COST", "C3PRED", "C3RES", "C3H", "C3MISS", "GYREC", "GYRES")}
RESERVE = {"ROWS": 0x20, "VREC": 0x30, "C1_COND": 0xB0, "C1_COST": 0x100, "C1_H": 0x50, "C1_FILT": 0x80, "C1_S5": 0x10, "H1": 0x70,
           "H2": 0x20, "H3": 0x30, "H4": 0x20, "AI": 0x20, "C2W": 0x30, "C2": 0x80, "C3REC": 0x30, "C3COND": 0x1A0, "C3COST": 0x40, "C3PRED": 0x1A0, "C3RES": 0x120, "C3H": 0x80, "C3MISS": 0x20, "GYREC": 0x30, "GYRES": 0x30}

C1_REC = (BD, 0, HANDSS_RES, 0, S["C1_COND"] | 1, S["C1_COST"] | 1, S["C1_S5"] | 1)         # virtual cls2 hand record (24 B, "<HHIIIII")
ROW = (BD, 0xFFFF, S["C3H"] | 1, 0x00000002)                                              # virtual criteria row {cid, aux, handler, word}
ROWS_BLOB = struct.pack("<HHII", *ROW) + bytes(0x14)
VREC_BLOB = struct.pack("<HHIIIII", *C1_REC) + bytes(0x18)


def _asm(b: EffectBuilder, slot: str) -> bytes:
    blob = b.assemble(S[slot], pad="nop")
    assert_thumb1_only(blob, S[slot])
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    return blob


def c1_cond() -> bytes:
    blob = compile_c(C_DIR / "block_dragon.c", S["C1_COND"], {"STUB": "C1COND"})
    assert len(blob) <= RESERVE["C1_COND"], f"C1_COND: {len(blob):#x} B > {RESERVE['C1_COND']:#x}"
    return blob


def c1_filt() -> bytes:
    """per-candidate callback ([sp] = &candidate word at entry): an EARTH monster, not this card's own ref, not already picked."""
    b = EffectBuilder()
    b.insn("PUSH", "{R3, R4, R5, LR}")
    b.insn("LDR", "R4, [SP, #0x10]")
    b.insn("LDR", "R4, [R4, #0x0]")                # r4 = the candidate's card word
    b.insn("LSL", "R5, R4, #0x12")
    b.insn("LSR", "R5, R5, #0x12")                 # r5 = cid
    b.insn("ADD", "R0, R5, #0x0")
    b.ldr_const(3, IS_MONSTER)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "no")
    b.insn("ADD", "R0, R5, #0x0")
    b.ldr_const(3, GET_ATTR)
    b.insn("BLX", "R3")
    b.insn("CMP", f"R0, #{EARTH}")
    b.insn("BNE", "no")
    b.ldr_const(0, ACTING)
    b.insn("LDR", "R0, [R0, #0x50]")               # the acting descriptor (set by the cost before the picker opens)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "yes")
    b.insn("LDRH", "R1, [R0, #0x0]")
    b.ldr_const(2, BD)
    b.insn("CMP", "R1, R2")
    b.insn("BNE", "yes")                           # not our descriptor: no exclusions
    b.insn("LSL", "R2, R4, #0x1")
    b.insn("LSR", "R2, R2, #0x18")
    b.insn("LSL", "R2, R2, #0x1")
    b.insn("LSL", "R3, R4, #0x11")
    b.insn("LSR", "R3, R3, #0x1F")
    b.insn("ADD", "R2, R2, R3")                    # r2 = the candidate's ref
    b.insn("LDRH", "R1, [R0, #0xC]")               # this card's own ref (desc[+0xC])
    b.insn("CMP", "R2, R1")
    b.insn("BEQ", "no")
    b.insn("LDRH", "R3, [R0, #0x12]")              # picks so far
    b.insn("CMP", f"R3, #{PICKS}")
    b.insn("BGE", "yes")
    b.insn("ADD", "R1, R0, #0x0")
    b.insn("ADD", "R1, #0x14")                     # r1 = &desc[+0x14]
    b.label("lp")
    b.insn("CMP", "R3, #0x0")
    b.insn("BEQ", "yes")
    b.insn("SUB", "R3, #0x1")
    b.insn("LSL", "R0, R3, #0x1")
    b.insn("ADD", "R0, R1, R0")
    b.insn("LDRH", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, R2")
    b.insn("BEQ", "no")
    b.insn("B", "lp")
    b.label("yes")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R3, R4, R5, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R3, R4, R5, PC}")
    return _asm(b, "C1_FILT")


def c1_handler() -> bytes:
    """virtual criteria handler (r0 = &row, r1 = side, r2 = param): the hand builder then the GY builder, banish flags, EARTH filter."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("SUB", "SP, #0xC")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("ADD", "R4, R1, #0x0")
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [SP, #0x8]")
    b.ldr_const(6, S["C1_FILT"] | 1)
    for builder in (HAND_BUILDER, GY_BUILDER):
        b.insn("MOV", "R0, #0x2")
        b.insn("STR", "R0, [SP, #0x0]")
        b.ldr_const(0, BANISH_FLAGS)
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.insn("ADD", "R2, R6, #0x0")
        b.insn("ADD", "R3, SP, #0x8")
        b.call_addr(builder, via=R7)
    b.insn("ADD", "SP, #0xC")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return _asm(b, "C1_H")


def c1_cost() -> bytes:
    """cls2 +10: Double Evolution Pill's two-pick protocol, three picks. desc[+0x12] = picks so far, desc[+0x14 + 2i] = pick i's ref."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.call_addr(SHORT, via=R3)
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "done")
    b.insn("LDRB", "R5, [R4, #0x2]")
    b.ldr_const(6, STATE)
    b.insn("LDR", "R0, [R6, #0x7C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "ph0")
    b.insn("CMP", "R0, #0x1")
    b.insn("BEQ", "ph1")
    b.insn("CMP", "R0, #0x2")
    b.insn("BEQ", "ph2")
    b.insn("CMP", "R0, #0x3")
    b.insn("BEQ", "ph3")
    # commit: every pick, hand first (index by ref), else the GY
    b.call_addr(CPUSH, via=R3)
    b.insn("MOV", "R7, #0x0")
    b.label("lp")
    b.insn("LSL", "R0, R7, #0x1")
    b.insn("ADD", "R0, R4, R0")
    b.insn("LDRH", "R6, [R0, #0x14]")
    b.call_addr(HINDEX, R5, R6, via=R3)
    b.insn("CMP", "R0, #0x0")
    b.insn("BLT", "gy")
    b.insn("ADD", "R1, R0, #0x0")
    b.call_addr(HBANISH, R5, via=R3)
    b.insn("B", "nx")
    b.label("gy")
    b.call_addr(R2W, R6, via=R3)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "nx")
    b.insn("ADD", "R1, R0, #0x0")
    b.call_addr(GBANISH, R5, R1, 0, via=R3)
    b.label("nx")
    b.insn("ADD", "R7, #0x1")
    b.insn("CMP", f"R7, #{PICKS}")
    b.insn("BLT", "lp")
    b.call_addr(CPOP, via=R3)
    b.label("done")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    b.label("ph0")
    b.insn("MOV", "R0, #0x0")
    b.insn("STRH", "R0, [R4, #0x12]")
    b.insn("B", "next")
    b.label("ph1")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", f"R1, #0x{PROMPT:X}")
    b.call_addr(MESSAGE, via=R3)
    b.insn("B", "next")
    b.label("ph2")
    b.ldr_const(0, ACTING)
    b.insn("STR", "R4, [R0, #0x50]")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", "R1, #0x6")
    b.insn("LDRH", "R2, [R4, #0x0]")
    b.call_addr(PICKER, R0, R1, R2, 0, via=R7)
    b.insn("B", "next")
    b.label("ph3")
    b.call_addr(READBACK, via=R3)
    b.insn("LDR", "R1, [R0, #0x0]")
    b.insn("LSL", "R0, R1, #0x11")
    b.insn("LSR", "R0, R0, #0x1F")
    b.insn("LSL", "R1, R1, #0x1")
    b.insn("LSR", "R1, R1, #0x18")
    b.insn("LSL", "R1, R1, #0x1")
    b.insn("ADD", "R1, R1, R0")
    b.insn("LDRH", "R0, [R4, #0x12]")
    b.insn("LSL", "R2, R0, #0x1")
    b.insn("ADD", "R2, R4, R2")
    b.insn("STRH", "R1, [R2, #0x14]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STRH", "R0, [R4, #0x12]")
    b.insn("MOV", "R1, #0x4")
    b.insn("CMP", f"R0, #{PICKS}")
    b.insn("BGE", "setp")
    b.insn("MOV", "R1, #0x1")
    b.label("setp")
    b.insn("STR", "R1, [R6, #0x7C]")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    b.label("next")
    b.insn("LDR", "R0, [R6, #0x7C]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R6, #0x7C]")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return _asm(b, "C1_COST")


def c1_s5() -> bytes:
    b = EffectBuilder()
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    return _asm(b, "C1_S5")


# --- fronts (Gearfried's, re-keyed) --------------------------------------------------------------------------------------
def h1_front() -> bytes:
    """find_event_handler miss tail (r4 = desc, [sp] = key cid, frame = push {r1-r7,lr}): Block Dragon's HAND cls2 lookup
    (desc[+5] == 2, [+3] == 0xB, [+4] == 0) -> r0 = &virtual record and pop the frame; everything else tails to Gearfried's H1."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.ldr_const(1, BD)
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "prev")
    b.insn("LDRB", "R1, [R4, #0x5]")
    b.insn("CMP", "R1, #0x2")
    b.insn("BNE", "prev")
    b.insn("LDRB", "R1, [R4, #0x3]")
    b.insn("CMP", "R1, #0xB")
    b.insn("BNE", "notHand")
    b.insn("LDRB", "R1, [R4, #0x4]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BNE", "c3")
    b.ldr_const(0, S["VREC"])
    b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
    b.label("notHand")
    b.insn("CMP", "R1, #0xE")
    b.insn("BNE", "c3")
    b.insn("LDRB", "R1, [R4, #0x4]")
    b.insn("CMP", "R1, #0x6")
    b.insn("BGT", "c3")
    b.ldr_const(0, S["GYREC"])
    b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
    b.label("c3")
    b.ldr_const(0, S["C3REC"])
    b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
    b.label("prev")
    b.ldr_const(3, H1_PREV | 1)
    b.insn("BX", "R3")
    return _asm(b, "H1")


def h2_front() -> bytes:
    """criteria resolver miss tail (r5 = cid): Block Dragon -> index 0xFF40 and pop the caller's frame, else onward to Predaplant's front."""
    b = EffectBuilder()
    b.ldr_const(0, BD)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, IDX)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _asm(b, "H2")


def h3_front() -> bytes:
    """invoker row compute (r6 = index): 0xFF40 -> r0 = CAVE_BD_ROWS, r3 = [r0+4], resume 0x02243F70; else tail to Predaplant's H3."""
    b = EffectBuilder()
    b.ldr_const(0, IDX)
    b.insn("CMP", "R6, R0")
    b.insn("BNE", "prev")
    b.ldr_const(0, S["ROWS"])
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, H3_PREV | 1)
    b.insn("BX", "R0")
    return _asm(b, "H3")


def h4_front() -> bytes:
    """ARM9 0x02023566 BL (r0 = cid): Block Dragon -> 1 (hand effect offered), else Gearfried's front."""
    b = EffectBuilder()
    b.ldr_const(3, BD)
    b.insn("CMP", "R0, R3")
    b.insn("BNE", "prev")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.label("prev")
    b.ldr_const(3, H4_PREV | 1)
    b.insn("BX", "R3")
    return _asm(b, "H4")


# --- Normal Summon/Set block: nomi class 4 (phantom 0x0E22) + the CPU planner's class view --------------------------------
AI_SITE, AI_PREV = 0x0236A1BA, O5.CAVE_WR_AICLASS            # ov5: `bl 0x020231C8` in the CPU hand-SS planner, re-pointed by Windrose
AI_NATIVE = bytes.fromhex("b9f405f8")
NOMI_PHANTOM = 0x0E22


def ai_front() -> bytes:
    """Windrose's class-view stub, one link ahead: Block Dragon -> class 2 (the CPU planner skips class 3/4/5 but not 2), else Windrose's."""
    b = EffectBuilder()
    b.ldr_const(1, BD)
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "prev")
    b.insn("MOV", "R0, #0x2")
    b.insn("BX", "LR")
    b.label("prev")
    b.ldr_const(3, AI_PREV | 1)
    b.insn("BX", "R3")
    return _asm(b, "AI")


@dataclass(frozen=True)
class cpu_planner_reads_class_2_ahead_of_windrose:
    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.summon_trigger_hook import _bl
        blob = ai_front()
        want = _bl(AI_SITE, S["AI"])
        was = _bl(AI_SITE, AI_PREV)

        def install(rom, view):
            ov5 = O5._load_ov5_decompressed(rom)
            data = bytearray(ov5.data)
            o = AI_SITE - O5.OV5_RAM_BASE
            cur = bytes(data[o:o + 4])
            assert cur in (was, want), f"ov5 {AI_SITE:#x} is {cur.hex()} -- not Windrose's re-point (needs Windrose in the chain)"
            if cur == want:
                return
            data[o:o + 4] = want
            O5._save_ov5(rom, ov5, bytes(data))

        def check(c, rom, view):
            o5 = O5._load_ov5_decompressed(rom).data
            o = AI_SITE - O5.OV5_RAM_BASE
            c.eq(bytes(o5[o:o + 4]), want, f"CPU planner {AI_SITE:#x} -> Block Dragon's class-view front")

        return Compiled(((S["AI"], blob, "CPU class view front"),), installs=(install,), checks=(check,))


# --- C2: Rock monsters you control cannot be destroyed, except by battle ------------------------------------------------------
C2_SITE, SEAL_STUB = 0x021CC264, 0x021B2B10          # survive check 0x021CC028's default exit: `bl` into Seal of Orichalcos' ov3 stub (chain ROM)


def c2_front() -> bytes:
    """Entered by the `bl` at the survive check's default exit (r4 zone, r5 side, [sp+8] the destroyed card's cid, sp = the check's frame).
    C2(side, zone, cid) -> 1: survives (`pop {r1-r7,pc}` straight out, r0 = 1); else fall through to Seal's stub, which is entered exactly as before."""
    b = EffectBuilder()
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("ADD", "R1, R4, #0x0")
    b.insn("LDR", "R2, [SP, #0x8]")
    b.ldr_const(3, S["C2"] | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "seal")
    b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
    b.label("seal")
    b.ldr_const(3, SEAL_STUB | 1)
    b.insn("BX", "R3")
    return _asm(b, "C2W")


@dataclass(frozen=True)
class rocks_survive_effect_destruction:
    def compile(self, view, cid) -> Compiled:
        blob = c2_front()
        c2 = compile_c(C_DIR / "block_dragon.c", S["C2"], {"STUB": "C2"})
        assert len(c2) <= RESERVE["C2"], f"C2: {len(c2):#x} B > {RESERVE['C2']:#x}"

        def install(rom, view):
            cur = ov3_bl_target(view.buf, C2_SITE)
            assert cur in (SEAL_STUB, S["C2W"]), f"survive-check exit @{C2_SITE:#x} calls {cur:#x}, expected Seal's stub {SEAL_STUB:#x} (needs seal_of_orichalcos in the chain)"
            view.write(C2_SITE, common_bl(C2_SITE, S["C2W"]))

        def check(c, rom, view):
            c.ok(code_reaches(rom, C2_SITE, S["C2W"]), f"survive-check exit @{C2_SITE:#x} reaches Block Dragon C2 front")

        return Compiled(((S["C2W"], blob, "C2 survive-check front"), (S["C2"], c2, "C2 Rock-survives test")), (), installs=(install,), checks=(check,))


# --- C3: "If this card is sent from the field to the GY: You can add up to 3 Rock monsters from your Deck to your hand, whose total Levels equal 8" ------
# Blueprint = Eva (in-game confirmed): virtual cls2 record {RES, 0, COND, native "You can", COST}, leave-mask row, never-miss front, picker loop in RES with the
# native add-to-hand mover 0x021C72CC.  Block Dragon's cls2 slot is taken by the VIRTUAL hand record, so the trigger record is virtual too: the H1 front
# serves the hand record for the hand lookup and this one for every other cls2 lookup of the cid (descriptor shape to be MEASURED -- notes).
YOU_CAN = 0x021E51E5
C3_REC = (BD, 0, S["C3RES"] | 1, 0, S["C3COND"] | 1, YOU_CAN, S["C3COST"] | 1)
C3REC_BLOB = struct.pack("<HHIIIII", *C3_REC) + bytes(0x18)
MISS_PREV = 0x023ADC10                                       # the chain's head at the node (read 2026-11-09: an ov5 front of an earlier card)
MISS_SITE = 0x021EE10C                                       # never-miss test's node: BL -> the chain of fronts (r3 = cid, Z = accept)
C3_MASK_ROW, C3_MASK_PHANTOM = (BD, 0x0800), 0x0E12          # leave-mask row {cid, to-GY}; phantom dropped from 0x0226EC1C (count 0x98)
P_DECK, ROCK_WORD, DECK_FLAGS = 0x20000, 0x30000002, 0xA
COUNT_C, DECK_B, ADD_HAND, SHUFFLE, CID_LEVEL = 0x02243FA9, 0x0223BC3D, 0x021C72CD, 0x021D269D, 0x0202ABD9
for _v in (COUNT_C, DECK_B, ADD_HAND, SHUFFLE, CID_LEVEL, YOU_CAN):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"


def c3_res() -> bytes:
    """+04 (desc, ev), phase [STATE+0x70] (Eva's loop): 0x80 open | 0x7F total left and picks left and a candidate -> prompt | 0x7E picker (1 Rock)
    | 0x7D read it back, total -= its Level, remember its ref, mover | 0x64 shuffle, close, clear the state magic.  desc: +0x12 total left, +0x14/+0x16 refs,
    +0x18 magic, +0x1A picks made (set by the cost)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("SUB", "SP, #0x8")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("STR", "R1, [SP, #0x0]")
    b.insn("LDRB", "R5, [R4, #0x2]")
    b.insn("LDRB", "R0, [R4, #0x6]")
    b.insn("EOR", "R5, R0")
    b.ldr_const(6, STATE)
    b.insn("LDR", "R0, [R6, #0x70]")
    b.insn("CMP", "R0, #0x80")
    b.insn("BEQ", "p80")
    b.insn("CMP", "R0, #0x7F")
    b.insn("BEQ", "p7f")
    b.insn("CMP", "R0, #0x7E")
    b.insn("BEQ", "p7e")
    b.insn("CMP", "R0, #0x7D")
    b.insn("BEQ", "p7d")
    b.insn("CMP", "R0, #0x64")
    b.insn("BEQ", "p64j")
    b.insn("MOV", "R0, #0x0")
    b.insn("B", "ret")
    b.label("p64j")
    b.insn("B", "p64")
    b.label("p80")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("LDR", "R1, [SP, #0x0]")
    b.call_addr(CPUSH, via=R3)
    b.insn("MOV", "R0, #0x7F")
    b.insn("B", "ret")
    b.label("p7f")
    b.insn("LDRH", "R0, [R4, #0x12]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BLE", "to64")
    b.insn("LDRH", "R0, [R4, #0x1A]")
    b.insn("CMP", "R0, #0x3")
    b.insn("BGE", "to64")
    b.ldr_const(7, P_DECK)
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("LDRH", "R1, [R4, #0x0]")
    b.call_addr(COUNT_C, R0, R1, R7, via=R3)
    b.insn("CMP", "R0, #0x0")
    b.insn("BLE", "to64")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", "R1, #0x33")
    b.call_addr(MESSAGE, via=R3)
    b.insn("MOV", "R0, #0x7E")
    b.insn("B", "ret")
    b.label("to64")
    b.insn("MOV", "R0, #0x64")
    b.insn("B", "ret")
    b.label("p7e")
    b.ldr_const(7, P_DECK)
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", "R1, #0x6")
    b.insn("LDRH", "R2, [R4, #0x0]")
    b.call_addr(PICKER, R0, R1, R2, R7, via=R6)
    b.insn("MOV", "R0, #0x7D")
    b.insn("B", "ret")
    b.label("p7d")
    b.call_addr(READBACK, via=R3)
    b.insn("ADD", "R7, R0, #0x0")
    b.insn("LDR", "R0, [R7, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.call_addr(CID_LEVEL, via=R3)
    b.insn("LDRH", "R1, [R4, #0x12]")
    b.insn("SUB", "R1, R1, R0")
    b.insn("STRH", "R1, [R4, #0x12]")
    b.insn("LDR", "R0, [R7, #0x0]")
    b.insn("LSL", "R1, R0, #0x11")
    b.insn("LSR", "R1, R1, #0x1F")
    b.insn("LSL", "R0, R0, #0x1")
    b.insn("LSR", "R0, R0, #0x18")
    b.insn("LSL", "R0, R0, #0x1")
    b.insn("ADD", "R0, R0, R1")
    b.insn("LDRH", "R1, [R4, #0x1A]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BNE", "sec")
    b.insn("STRH", "R0, [R4, #0x14]")
    b.insn("B", "cnt")
    b.label("sec")
    b.insn("STRH", "R0, [R4, #0x16]")
    b.label("cnt")
    b.insn("ADD", "R1, #0x1")
    b.insn("STRH", "R1, [R4, #0x1A]")
    b.call_addr(ADD_HAND, R5, R7, via=R3)
    b.insn("MOV", "R0, #0x7F")
    b.insn("B", "ret")
    b.label("p64")
    b.call_addr(SHUFFLE, R5, via=R3)
    b.call_addr(CPOP, via=R3)
    b.insn("MOV", "R0, #0x0")
    b.insn("STRH", "R0, [R4, #0x18]")
    b.label("ret")
    b.insn("ADD", "SP, #0x8")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return _asm(b, "C3RES")


def c3_handler() -> bytes:
    """Criteria row handler (r0 row, r1 side, r2 param): param >> 16 == 2 -> the Deck walker over Rocks with C3PRED as the filter; else C1's handler."""
    b = EffectBuilder()
    b.insn("LSR", "R3, R2, #0x10")
    b.insn("CMP", "R3, #0x2")
    b.insn("BEQ", "m2")
    b.ldr_const(3, S["C1_H"] | 1)
    b.insn("BX", "R3")
    b.label("m2")
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("SUB", "SP, #0x10")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("ADD", "R4, R1, #0x0")
    b.insn("ADD", "R6, R2, #0x0")
    b.ldr_const(0, ROCK_WORD)
    b.insn("STR", "R0, [SP, #0x0]")
    b.insn("MOV", f"R0, #0x{DECK_FLAGS:X}")
    b.insn("STR", "R0, [SP, #0x4]")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("LDRH", "R1, [R5, #0x0]")
    b.ldr_const(2, S["C3PRED"] | 1)
    b.insn("LSL", "R3, R6, #0x12")
    b.insn("LSR", "R3, R3, #0x12")
    b.call_addr(DECK_B, via=R7)
    b.insn("ADD", "SP, #0x10")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return _asm(b, "C3H")


def c3_miss(prev: int) -> bytes:
    """BL'd from the never-miss test's node 0x021EE10C (r3 = cid, Z = accept): Block Dragon -> Z (never miss), else on to the head that was there."""
    b = EffectBuilder()
    b.ldr_const(1, BD)
    b.insn("CMP", "R3, R1")
    b.insn("BEQ", "ret")
    b.ldr_const(1, prev | 1)
    b.insn("BX", "R1")
    b.label("ret")
    b.insn("BX", "LR")
    return _asm(b, "C3MISS")


@dataclass(frozen=True)
class sent_to_gy_add_rocks_totalling_level_8:
    def compile(self, view, cid) -> Compiled:
        cur = ov3_bl_target(view.buf, MISS_SITE)
        prev = MISS_PREV
        assert cur in (MISS_PREV, *O5.dc_ahead_of(S["C3MISS"])), f"miss-timing node {MISS_SITE:#x} calls {cur:#x}, expected the chain head {MISS_PREV:#x} (or ours)"
        blobs = {}
        for slot, stub in (("C3COND", "C3COND"), ("C3COST", "C3COST"), ("C3PRED", "C3PRED")):
            blob = compile_c(C_DIR / "block_dragon.c", S[slot], {"STUB": stub})
            assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
            blobs[slot] = blob
        stubs = ((S["C3REC"], C3REC_BLOB, "C3 virtual cls2 record"),
                 (S["C3COND"], blobs["C3COND"], "C3 +0C cond"),
                 (S["C3COST"], blobs["C3COST"], "C3 +14 cost"),
                 (S["C3PRED"], blobs["C3PRED"], "C3 Deck candidate filter"),
                 (S["C3RES"], c3_res(), "C3 +04 picker loop"),
                 (S["C3H"], c3_handler(), "C3 criteria handler front"),
                 (S["C3MISS"], c3_miss(prev), "C3 never-miss front"))

        def install(rom, view):
            view.write(MISS_SITE, common_bl(MISS_SITE, S["C3MISS"]))

        def check(c, rom, view):
            c.ok(ov3_bl_target(view.buf, MISS_SITE) in O5.dc_ahead_of(S["C3MISS"]), f"miss-timing node @{MISS_SITE:#x} -> Block Dragon's never-miss front (or a registered front ahead of it)")
            for label, addr, blob, _ in ((l, ad, bl, 0) for ad, bl, l in stubs):
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{label} installed @{addr:#x}")

        return Compiled(stubs, (Row(LEAVE_MASK, C3_MASK_ROW, C3_MASK_PHANTOM),), installs=(install,), checks=(check,))


# --- C1, GY half: "Special Summoned (from your hand or GY) by banishing 3 EARTH monsters from your hand and/or GY" -------------------------------------------
# A second virtual cls2 record for the GY lookup ([+3] == 0xE, [+4] <= 6 -- the shape Dragon Rulers' H1 serves; the leave TRIGGER is [+4] == 0x1D, measured
# 2026-11-09), the shared GY self-SS resolver as RES, the SAME COND / COST / handler as the hand record (COND accepts zone 0xE; the cost excludes the card's
# own ref desc[+0xC]), and the last free row of the shared virtual GY-action table so the GY menu lists it.
GY_SS_RES = 0x0220731D
GYSS_REC = (BD, 0, S["GYRES"] | 1, 0, S["C1_COND"] | 1, S["C1_COST"] | 1, S["C1_S5"] | 1)
GYREC_BLOB = struct.pack("<HHIIIII", *GYSS_REC) + bytes(0x18)
GYV_ARM = ()                                                 # the row lives in gy_vrow_hook.ARMS since shipping (2026-11-09)


def gy_res() -> bytes:
    """GY record +04 (r0 desc, r1 ev): a card with a summon restriction (Block Dragon: nomi class 4) may leave the GY by a Special Summon only when bit 15 of its card
    word is set (0x021A2618, read from the 2026-11-09 savestate: a Block Dragon discarded to the GY has it clear, so the native resolver returned 0 right after the
    cost was paid).  Paying Block Dragon's own cost IS the proper procedure, so mark the word (found by desc[+0xC], the card's ref) and run the shared resolver."""
    b = EffectBuilder()
    b.insn("PUSH", "{R0, R1, LR}")
    b.insn("LDRH", "R0, [R0, #0xC]")
    b.call_addr(R2W, via=R3)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "skip")
    b.insn("LDR", "R1, [R0, #0x0]")
    b.insn("MOV", "R2, #0x80")
    b.insn("LSL", "R2, R2, #0x8")
    b.insn("ORR", "R1, R2")
    b.insn("STR", "R1, [R0, #0x0]")
    b.label("skip")
    b.insn("POP", "{R0, R1, R3}")
    b.insn("MOV", "LR, R3")
    b.ldr_const(3, GY_SS_RES | 1)
    b.insn("BX", "R3")
    return _asm(b, "GYRES")


@dataclass(frozen=True)
class special_summon_from_gy_by_banishing_three_earth:
    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import gy_vrow_hook as gyv
        arms = gyv.ARMS + GYV_ARM

        def install(rom, view):
            gyv.install(rom, view.buf, arms=arms)

        def check(c, rom, view):
            gyv.verify(rom, view.buf, lambda ok, msg: c.ok(ok, msg), arms=arms)
            c.ok(O5.read_cave(rom, S["GYREC"], len(GYREC_BLOB)) == GYREC_BLOB, f"GY virtual cls2 record installed @{S['GYREC']:#x}")

        return Compiled(((S["GYREC"], GYREC_BLOB, "virtual cls2 GY record"), (S["GYRES"], gy_res(), "GY +04 proper-summon flag wrapper")), (), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class block_dragon_c1_hand:
    def compile(self, view, cid) -> Compiled:
        assert cid == BD

        stubs = (
            (S["ROWS"], ROWS_BLOB, "virtual criteria row 0xFF40"),
            (S["VREC"], VREC_BLOB, "virtual cls2 hand record"),
            (S["C1_COND"], c1_cond(), "C1 +0C hand cond"),
            (S["C1_COST"], c1_cost(), "C1 +10 three-pick banish cost"),
            (S["C1_H"], c1_handler(), "C1 criteria handler"),
            (S["C1_FILT"], c1_filt(), "C1 EARTH candidate filter"),
            (S["C1_S5"], c1_s5(), "C1 +14"),
            (S["H1"], h1_front(), "find_event_handler front"),
            (S["H2"], h2_front(), "H2 front"),
            (S["H3"], h3_front(), "H3 front"),
            (S["H4"], h4_front(), "ARM9 H4 front"))

        def _front(view, site, prev, mine, what):
            cur = ov3_bl_target(view.buf, site)
            assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
            view.write(site, common_bl(site, mine))

        def install(rom, view):
            _front(view, H1_SITE, H1_PREV, S["H1"], "find_event_handler miss tail")
            _front(view, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front(view, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            mc, sec = O5._arm9_main(rom)
            d = bytearray(sec.data)
            a = H4_SITE - 0x02000000
            assert bytes(d[a:a + 4]) in (common_bl(H4_SITE, H4_PREV), common_bl(H4_SITE, S["H4"])), \
                f"ARM9 H4 site {H4_SITE:#x} is not Gearfried's front"
            d[a:a + 4] = common_bl(H4_SITE, S["H4"])
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def check(c, rom, view):
            for site, slot in ((H1_SITE, "H1"), (H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(code_reaches(rom, site, S[slot]), f"bl @{site:#x} reaches {slot}")
            mc, sec = O5._arm9_main(rom)
            a = H4_SITE - 0x02000000
            c.ok(code_reaches(rom, H4_SITE, S["H4"]), "ARM9 bl @0x02023566 reaches H4 front")
            for label, addr, blob, _ in ((l, ad, bl, 0) for ad, bl, l in stubs):
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{label} installed @{addr:#x}")

        return Compiled(stubs, (), installs=(install,), checks=(check,))


SPEC = card(BD, block_dragon_c1_hand(), archetype_member(NOMI_CLASS_4_TABLE, NOMI_PHANTOM), cpu_planner_reads_class_2_ahead_of_windrose(), rocks_survive_effect_destruction(), sent_to_gy_add_rocks_totalling_level_8(), special_summon_from_gy_by_banishing_three_earth())
PROPS = card_props("EARTH", "Rock", level=8, atk=2500, defense=3000, card_type="Effect Monster")

_main, _verify = dsl.make(SPEC, PROPS, out=OUT)


def main(write_text: bool = True, src: str = CHAIN, out: str = OUT) -> None:
    _main(write_text=write_text, src=src, out=out)


def verify(out: str = OUT) -> bool:
    return _verify(out) is not False
