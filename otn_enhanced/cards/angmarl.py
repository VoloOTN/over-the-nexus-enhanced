"""Angmarl the Fiendish Monarch (0x14D8, donor The Dragon Dwelling in the Cave): blobs for cards/mega_monarch.py (the Monarch set module installs them).

    "When this card is Tribute Summoned: You can banish 1 Spell Card from your Graveyard; add 1 card with the same name as the banished Spell Card from
     your Deck to your hand."   DARK / Fiend / Level 6 / 2400 / 1000.

Clauses  C1 trigger on its own Tribute Summon (the Monarch-list front answers 1 for 0x14D8).  C2 optional ("You can"): banish 1 Spell Card from your GY as a cost.
         C3 add 1 card with the same name from the Deck.
Design   (notes/angmarl-findings.md; UNPROVEN until traced)
  * cls1 {0x14D8, 0, RES, 0, COND, 0x021E51E5 (the native "You can" prompt), COST} over a cls1 phantom (Return's record shape).
  * COST = the native banish cost 0x021E5319 (Survival Instinct's: GY picker driven by the criteria row, banishes exactly 1 for an unlisted cid).
  * TWO virtual criteria rows under the one cid (Tenacity's recipe): 0xFF90 = GY handler 0x0223CA11 with word 0x4 (Spell Card), used while the cost machine runs
    ([0x0229AAFC+0x7C] != 0); 0xFF91 = a Deck handler with a custom predicate (same name as DATA+0), used at resolution.
  * RES remembers the cid just banished (the last entry of the banished list) at phase 0x80, then runs the native Deck -> hand resolver 0x02207EF5.
"""
from __future__ import annotations

import struct
from pathlib import Path

from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.effects import ov5_cave as O5

ANGMARL = 0x14D8
C_DIR = Path(__file__).resolve().parent / "c"
IDX_GY, IDX_DECK = 0xFF90, 0xFF91
GY_HANDLER, WORD_SPELL, WORD_ANY_CARD = 0x0223CA11, 0x00000004, 0x0000000E
TAG_YOU_CAN = 0x021E51E5
STATE = 0x0229AAFC
SAME_NAME, ENUM_DECK = 0x02022E99, 0x0223BC3D
H3_RESUME = 0x02243F71
S = {n: getattr(O5, f"CAVE_AG_{n}") for n in ("COND", "COST", "RES", "PRED", "HAND", "ROWS", "DATA", "H2", "H3")}
RESERVE = {"COND": 0x50, "COST": 0x10, "RES": 0x60, "PRED": 0x30, "HAND": 0x30, "ROWS": 0x20, "DATA": 0x10, "H2": 0x30, "H3": 0x30}


def _c(stub: str, slot: str) -> bytes:
    return compile_c(C_DIR / "angmarl.c", S[slot], {"STUB": stub, "DATA": f"0x{S['DATA']:08X}"})


def pred_stub() -> bytes:
    """Deck-search predicate (the enumerator's stack args at [sp] -> card word pointer): the card has the banished card's name (DATA+0; 0 = nothing banished -> no)."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("PUSH", "{R4, LR}")
    b.ldr_const(1, S["DATA"])
    b.insn("LDR", "R1, [R1, #0x0]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BEQ", "no")
    b.ldr_const(3, SAME_NAME | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "no")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, PC}")
    return b.assemble(S["PRED"], pad="nop")


def hand_stub() -> bytes:
    """Row handler (row r0, side r1): 0x0223CAF4's body with the custom predicate (Return's recipe)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, LR}")
    b.insn("ADD", "R3, R0, #0x0")
    b.insn("MOV", "R0, #0x2")
    b.insn("MOV", "R2, #0x0")
    b.insn("STR", "R2, [SP, #0x8]")
    b.insn("LDR", "R2, [R3, #0x8]")
    b.insn("STR", "R2, [SP, #0x0]")
    b.insn("STR", "R0, [SP, #0x4]")
    b.insn("ADD", "R0, R1, #0x0")
    b.insn("LDRH", "R1, [R3, #0x0]")
    b.ldr_const(2, S["PRED"] | 1)
    b.insn("ADD", "R3, SP, #0x8")
    b.ldr_const(4, ENUM_DECK | 1)
    b.insn("BLX", "R4")
    b.insn("POP", "{R1, R2, R3, R4, PC}")
    return b.assemble(S["HAND"], pad="nop")


def rows_blob() -> bytes:
    return (struct.pack("<HHII", ANGMARL, 0xFFFF, GY_HANDLER, WORD_SPELL) + bytes(4)
            + struct.pack("<HHII", ANGMARL, 0xFFFF, S["HAND"] | 1, WORD_ANY_CARD) + bytes(4))


def h2_front(prev: int) -> bytes:
    """criteria miss tail (r5 = cid): 0x14D8 -> the GY row while the cost machine runs, else the Deck row; pop the caller's frame.  Others: BL onward."""
    b = EffectBuilder()
    b.ldr_const(0, ANGMARL)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, STATE)
    b.insn("LDR", "R0, [R0, #0x7C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "gy")
    b.ldr_const(0, IDX_DECK)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("gy")
    b.ldr_const(0, IDX_GY)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(prev)
    return b.assemble(S["H2"], pad="nop")


def h3_front(prev: int) -> bytes:
    """invoker row compute (r6 = index): 0xFF90..0xFF91 -> r0 = ROWS + 0x10 * (index - 0xFF90), r3 = [r0+4], resume 0x02243F70; else tail to the previous H3."""
    b = EffectBuilder()
    b.ldr_const(0, IDX_GY)
    b.insn("SUB", "R0, R6, R0")
    b.insn("CMP", "R0, #0x2")
    b.insn("BCS", "prev")
    b.insn("LSL", "R0, R0, #0x4")
    b.ldr_const(3, S["ROWS"])
    b.insn("ADD", "R0, R0, R3")
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, prev | 1)
    b.insn("BX", "R0")
    return b.assemble(S["H3"], pad="nop")


def blobs(h2_prev: int, h3_prev: int) -> dict:
    """slot name -> (address, bytes, label) for the Monarch set module."""
    return {"AG_COND": (S["COND"], _c("AG_COND", "COND"), "Angmarl cls1 +0C cond (C)"),
            "AG_COST": (S["COST"], _c("AG_COST", "COST"), "Angmarl cls1 +14 cost (C)"),
            "AG_RES": (S["RES"], _c("AG_RES", "RES"), "Angmarl cls1 +04 resolver (C)"),
            "AG_PRED": (S["PRED"], pred_stub(), "Angmarl Deck predicate"),
            "AG_HAND": (S["HAND"], hand_stub(), "Angmarl Deck row handler"),
            "AG_ROWS": (S["ROWS"], rows_blob(), "Angmarl virtual criteria rows 0xFF90 / 0xFF91"),
            "AG_DATA": (S["DATA"], bytes(0x10), "Angmarl DATA: banished cid (ships clear)"),
            "AG_H2": (S["H2"], h2_front(h2_prev), "Angmarl criteria miss-tail front"),
            "AG_H3": (S["H3"], h3_front(h3_prev), "Angmarl criteria row-compute front")}


def reserves() -> dict:
    return {f"AG_{k}": v for k, v in RESERVE.items()}


def cls1_record() -> tuple:
    return (ANGMARL, 0, S["RES"] | 1, 0, S["COND"] | 1, TAG_YOU_CAN, S["COST"] | 1)
