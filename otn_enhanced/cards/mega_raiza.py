"""Raiza the Mega Monarch's resolver + candidate handler stubs (imported by mega_monarch).

"If this card is Tribute Summoned: Target 1 card on the field and 1 card in either player's Graveyard, also if this card was Tribute Summoned by Tributing a WIND
monster, you can target an additional card on the field; place the first target(s) on the top of the Deck in any order, also, after that, return the additional
target (if any) to the hand."

Built like Zaborg's picker (Block Dragon C3's protocol): a VIRTUAL criteria row 0xFF51 + handler RH fill the candidate buffer, and RESR is a phase machine on
[0x0229AAFC+0x70] that opens the stock picker once per card.  The cls1 record is Thestalos-the-Firestorm-Monarch-shaped ({cid, 0, RESR, 0, 0, 0, 0}: a trigger with
NO targeting step), so everything happens at RESOLUTION.

KNOWN GAPS (not deviations; they are what "Target" / "in any order" / "you can" print):
  (1) the cards are CHOSEN AT RESOLUTION, not targeted when the effect is activated (no response window with the targets known, no fizzle if one is gone);
  (2) the order of the cards placed on the Deck is fixed, not the player's choice;
  (3) the WIND additional card is not optional: it is chosen whenever a field card remains.
Phases: 0x80 plan (steps 2, or 3 after a WIND Tribute; refs := 0xFFFF; open the pick session 0x021D28A4) | 0x7F next step: count candidates for it via the criteria
row, skip the step when there are none, else prompt 0x4E | 0x7E picker 0x0219C430(controller, 6, cid, param) | 0x7D read the pick back, remember its ref |
0x7C apply: field card 1 -> Deck top (0x021CF590), the GY card -> Deck top (0x021C6A0C), the additional field card -> hand (0x021CF524) | 0x64 close, consume the latch.
Handler modes (param >> 16): 0 = every card on the field (both players, zones 0..10) except the ref remembered in RST+4, 1 = both Graveyards.
"""
from __future__ import annotations

import struct

from otn_enhanced.asm.effect_builder import EffectBuilder

COUNT_C = 0x02243FA8
MESSAGE = 0x0219A818
PICKER = 0x0219C430
READBACK = 0x0219C510
CPUSH, CPOP = 0x021D28A4, 0x021D2964
RECORDER = 0x02243B2C             # (side, zone code, index): append a candidate (word + locator)
SLOT_PTR = 0x0219CA28             # (side, zone code, index) -> &card word
LOCATOR = 0x021A220C              # (ref) -> (zone << 8) | side on the field; (index << 16) | (code << 8) | side in a list; 0x1000 = not found
FIELD_TO_DECK = 0x021CF590        # (desc, side, zone) queued move to the Deck (top)
FIELD_TO_HAND = 0x021CF524        # (desc, side, zone) queued move to the hand
GY_TO_DECK = 0x021C6A0C           # (desc, side, ref, 1) immediate move; dest index 0 = top
STATE = 0x0229AAFC
GY_COUNT0 = 0x0229ACA8            # player 0 Graveyard count (player + 0x14); + side * 0xB3C
SIDE_STRIDE = 0x0B3C
MSG_DECK_TOP = 0x4E               # Raiza the Storm Monarch's own prompt ("place on top of the Deck")
H3_RESUME = 0x02243F70
IDX = 0xFF51
WIND = 6
NONE = 0xFFFF
for _a in (COUNT_C, MESSAGE, PICKER, READBACK, CPUSH, CPOP, RECORDER, SLOT_PTR, LOCATOR, FIELD_TO_DECK, FIELD_TO_HAND, GY_TO_DECK, H3_RESUME):
    assert _a % 2 == 0


def row_blob(cid: int, handler: int) -> bytes:
    return struct.pack("<HHII", cid, 0xFFFF, handler | 1, 2) + bytes(0x14)


def rh_stub(base: int, rst: int) -> bytes:
    """Criteria handler (r0 = &row, r1 = side (ignored: both players), r2 = param).  mode = param >> 16: 0 field, 1 Graveyards."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("SUB", "SP, #0x8")
    b.insn("LSR", "R0, R2, #0x10")
    b.insn("STR", "R0, [SP, #0x0]")              # mode
    b.insn("MOV", "R4, #0x0")                    # side
    b.label("sloop")
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "gy")
    # ---- field: zones 0..10 ----
    b.insn("MOV", "R5, #0x0")
    b.label("zloop")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("ADD", "R1, R5, #0x0")
    b.insn("MOV", "R2, #0x0")
    b.ldr_const(3, SLOT_PTR | 1)
    b.insn("BLX", "R3")
    b.insn("LDR", "R6, [R0, #0x0]")              # the card word
    b.insn("LSL", "R0, R6, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("BEQ", "znext")                       # empty zone
    b.insn("LSL", "R0, R6, #1")                  # ref = ((w << 1) >> 24) * 2 + ((w >> 14) & 1)
    b.insn("LSR", "R0, R0, #0x18")
    b.insn("LSL", "R0, R0, #1")
    b.insn("LSL", "R1, R6, #0x11")
    b.insn("LSR", "R1, R1, #0x1F")
    b.insn("ADD", "R0, R0, R1")
    b.ldr_const(1, rst)
    b.insn("LDR", "R1, [R1, #0x4]")              # the card already chosen (excluded)
    b.insn("CMP", "R0, R1")
    b.insn("BEQ", "znext")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("ADD", "R1, R5, #0x0")
    b.insn("MOV", "R2, #0x0")
    b.ldr_const(3, RECORDER | 1)
    b.insn("BLX", "R3")
    b.label("znext")
    b.insn("ADD", "R5, R5, #0x1")
    b.insn("CMP", "R5, #0xB")
    b.insn("BLT", "zloop")
    b.insn("B", "snext")
    # ---- Graveyards ----
    b.label("gy")
    b.ldr_const(0, GY_COUNT0)
    b.ldr_const(1, SIDE_STRIDE)
    b.insn("MUL", "R1, R4")
    b.insn("LDR", "R7, [R0, R1]")                # this side's Graveyard count
    b.insn("MOV", "R5, #0x0")
    b.label("gloop")
    b.insn("CMP", "R5, R7")
    b.insn("BGE", "snext")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("MOV", "R1, #0xE")
    b.insn("ADD", "R2, R5, #0x0")
    b.ldr_const(3, RECORDER | 1)
    b.insn("BLX", "R3")
    b.insn("ADD", "R5, R5, #0x1")
    b.insn("B", "gloop")
    b.label("snext")
    b.insn("ADD", "R4, R4, #0x1")
    b.insn("CMP", "R4, #0x2")
    b.insn("BLT", "sloop")
    b.insn("ADD", "SP, #0x8")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return b.assemble(base, pad="nop")


def h2_front(base: int, cid: int, prev: int, idx: int = IDX) -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, cid)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, idx)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(prev)
    return b.assemble(base, pad="nop")


def h3_front(base: int, rows: int, prev: int, idx: int = IDX) -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, idx)
    b.insn("CMP", "R6, R0")
    b.insn("BNE", "prev")
    b.ldr_const(0, rows)
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME | 1)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, prev | 1)
    b.insn("BX", "R0")
    return b.assemble(base, pad="nop")


def _param(b: EffectBuilder, tag: str) -> None:
    """r7 = RST -> r3 = (step == 1 ? 1 : 0) << 16."""
    b.insn("LDR", "R0, [R7, #0x0]")
    b.insn("MOV", "R3, #0x0")
    b.insn("CMP", "R0, #0x1")
    b.insn("BNE", "pm" + tag)
    b.insn("MOV", "R3, #0x1")
    b.label("pm" + tag)
    b.insn("LSL", "R3, R3, #0x10")


def resr_stub(base: int, rst: int, flag: int) -> bytes:
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("SUB", "SP, #0x10")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("STR", "R1, [SP, #0x0]")
    b.insn("LDRB", "R5, [R4, #0x2]")
    b.insn("LDRB", "R0, [R4, #0x6]")
    b.insn("EOR", "R5, R0")
    b.insn("MOV", "R0, #0x1")
    b.insn("AND", "R5, R0")                      # the controller
    b.ldr_const(6, STATE)
    b.ldr_const(7, rst)
    b.insn("LDR", "R0, [R6, #0x70]")
    for k, ph in enumerate((0x80, 0x7F, 0x7E, 0x7D, 0x7C, 0x64)):
        b.insn("CMP", f"R0, #0x{ph:X}")
        b.insn("BNE", f"n{k}")
        b.insn("B", f"p{ph:x}")
        b.label(f"n{k}")
    b.insn("MOV", "R0, #0x0")
    b.insn("B", "ret")

    b.label("p80")
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [R7, #0x0]")
    b.ldr_const(0, NONE)
    b.insn("STR", "R0, [R7, #0x4]")
    b.insn("STR", "R0, [R7, #0x8]")
    b.insn("STR", "R0, [R7, #0xC]")
    b.ldr_const(1, flag)
    b.insn("LDR", "R1, [R1, #0x0]")
    b.insn("LSR", "R1, R1, #" + str(WIND))
    b.insn("MOV", "R2, #0x1")
    b.insn("AND", "R1, R2")
    b.insn("ADD", "R1, #0x2")                    # 2 steps, 3 after a WIND Tribute
    b.insn("STR", "R1, [R7, #0x10]")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("LDR", "R1, [SP, #0x0]")
    b.ldr_const(3, CPUSH | 1)
    b.insn("BLX", "R3")
    b.insn("MOV", "R0, #0x7F")
    b.insn("B", "ret")

    b.label("p7f")
    b.label("l7f")
    b.insn("LDR", "R0, [R7, #0x0]")
    b.insn("LDR", "R1, [R7, #0x10]")
    b.insn("CMP", "R0, R1")
    b.insn("BGE", "toapply")
    _param(b, "a")
    b.insn("ADD", "R2, R3, #0x0")
    b.insn("LDRH", "R1, [R4, #0x0]")
    b.insn("ADD", "R0, R5, #0x0")
    b.ldr_const(3, COUNT_C | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BGT", "ask")
    b.insn("LDR", "R0, [R7, #0x0]")              # nothing to pick for this step
    b.insn("ADD", "R0, R0, #0x1")
    b.insn("STR", "R0, [R7, #0x0]")
    b.insn("B", "l7f")
    b.label("ask")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", "R1, #" + hex(MSG_DECK_TOP))
    b.ldr_const(3, MESSAGE | 1)
    b.insn("BLX", "R3")
    b.insn("MOV", "R0, #0x7E")
    b.insn("B", "ret")
    b.label("toapply")
    b.insn("MOV", "R0, #0x7C")
    b.insn("B", "ret")

    b.label("p7e")
    _param(b, "b")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", "R1, #0x6")
    b.insn("LDRH", "R2, [R4, #0x0]")
    b.ldr_const(6, PICKER | 1)
    b.insn("BLX", "R6")
    b.insn("MOV", "R0, #0x7D")
    b.insn("B", "ret")

    b.label("p7d")
    b.ldr_const(3, READBACK | 1)
    b.insn("BLX", "R3")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R1, R0, #1")
    b.insn("LSR", "R1, R1, #0x18")
    b.insn("LSL", "R1, R1, #1")
    b.insn("LSL", "R2, R0, #0x11")
    b.insn("LSR", "R2, R2, #0x1F")
    b.insn("ADD", "R2, R1, R2")                  # ref
    b.insn("LDR", "R1, [R7, #0x0]")
    b.insn("LSL", "R3, R1, #0x2")
    b.insn("ADD", "R3, R3, R7")
    b.insn("STR", "R2, [R3, #0x4]")
    b.insn("ADD", "R1, R1, #0x1")
    b.insn("STR", "R1, [R7, #0x0]")
    b.insn("MOV", "R0, #0x7F")
    b.insn("B", "ret")

    # ---- 0x7C: apply the three moves -------------------------------------------------------------------------------------------
    b.label("p7c")
    for slot, mover in ((0x4, FIELD_TO_DECK), (0xC, FIELD_TO_HAND)):
        lab = f"f{slot:x}"
        b.insn("LDR", "R0, [R7, #" + hex(slot) + "]")
        b.ldr_const(1, NONE)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", lab)
        b.ldr_const(3, LOCATOR | 1)
        b.insn("BLX", "R3")                      # (zone << 8) | side
        b.insn("LSL", "R1, R0, #0x18")
        b.insn("LSR", "R1, R1, #0x18")           # side
        b.insn("LSL", "R2, R0, #0x10")
        b.insn("LSR", "R2, R2, #0x18")           # zone
        b.insn("ADD", "R0, R4, #0x0")
        b.ldr_const(3, mover | 1)
        b.insn("BLX", "R3")
        b.label(lab)
    b.insn("LDR", "R2, [R7, #0x8]")              # the Graveyard card
    b.ldr_const(1, NONE)
    b.insn("CMP", "R2, R1")
    b.insn("BEQ", "applied")
    b.insn("MOV", "R1, #0x1")
    b.insn("AND", "R1, R2")                      # its side
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("MOV", "R3, #0x1")
    b.ldr_const(6, GY_TO_DECK | 1)
    b.insn("BLX", "R6")
    b.label("applied")
    b.insn("MOV", "R0, #0x64")
    b.insn("B", "ret")

    b.label("p64")
    b.ldr_const(3, CPOP | 1)
    b.insn("BLX", "R3")
    b.ldr_const(1, flag)
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [R1, #0x0]")
    b.label("ret")
    b.insn("ADD", "SP, #0x10")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return b.assemble(base, pad="nop")


def trig_stub(base: int, megas, list_search: int) -> bytes:
    b = EffectBuilder()
    for cid in megas:
        b.ldr_const(3, cid)
        b.insn("CMP", "R0, R3")
        b.insn("BEQ", "hit")
    b.ldr_const(3, list_search | 1)
    b.insn("BX", "R3")
    b.label("hit")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")
