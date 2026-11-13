"""Zaborg the Mega Monarch's resolver + Extra Deck picker stubs (imported by mega_monarch; no card logic of its own).

"If this card is Tribute Summoned: Target 1 monster on the field; destroy it, then, if it was a LIGHT monster, both players send as many cards as possible from
their Extra Deck to the GY, but not more than the original Level/Rank of that destroyed monster. If this card was Tribute Summoned by Tributing a LIGHT monster,
add this additional effect. * You choose the cards your opponent sends to the GY."

Shape = Block Dragon C3's confirmed stepwise picker, over the EXTRA DECK:
  * a VIRTUAL criteria row 0xFF50 for the donor cid (H2 front: cid -> index; H3 front: index -> row; both chain AHEAD of Block Dragon's) whose handler
    ZH(row, side, param) runs the engine's Extra Deck candidate enumerator 0x0223BE40(side, cid, 0 = no per-card callback, r3 = param & 0x3FFF,
    [sp] = criteria word 2, [sp+4] = flags) with flags bit 0 = param bit 16 ("the OTHER player's Extra Deck", the builder flips the side).
    Because the zone mover is IMMEDIATE, a card that was sent is already out of the array on the next pick, so no exclusion callback is needed.
  * RESZ = cls1 +04 as a phase machine on [0x0229AAFC+0x70], exactly c3_res's protocol: 0x80 read the target (cid -> LIGHT? Level), native destroy-1,
    compute the steps and open the pick session (0x021D28A5) | 0x7F next step / count candidates / prompt 0x3A ("send it to the Graveyard") |
    0x7E picker 0x0219C430(picker, 6 = exactly 1, cid, param) | 0x7D read back the pick, send it to the GY with 0x021C69D0(side, 0xC, ref, side, 0xE, 1, 0)
    + event 0x022391CC(0x26, 0) | 0x64 close the session, consume the LIGHT-Tribute latch.
  * steps (u32 {picker | target << 8 | n << 16} in the ZST data block): not LIGHT-Tributed = [(c, c, nc), (o, o, no)] (each player picks their own);
    LIGHT-Tributed = [(c, c, nc), (c, o, no)] (the controller picks both).  n = min(Level, Extra Deck count).
UNPROVEN (CPU harness + the user must settle each): the criteria row is served for this cid; the Extra builder accepts word 2 / callback 0; the picker shows
the OPPONENT's Extra Deck cards for the 'you choose' variant; 0x021C69D0 moves an Extra Deck card to the GY; the CPU seat picks for itself.
"""
from __future__ import annotations

import struct

from otn_enhanced.asm.effect_builder import EffectBuilder

# natives (Thumb entry | 1 added where called through a register)
TARGET_AT = 0x022349B0
ZONE_CID = 0x021A36EC
GET_ATTR = 0x0202ABC8
CID_LEVEL = 0x0202ABD8
DESTROY_ONE = 0x02204674
ZONE_MOVE = 0x021C69D0
POST_SENT = 0x022391CC
EXTRA_B = 0x0223BE40
COUNT_C = 0x02243FA8              # (side, cid, param) -> candidate count (criteria lookup + walk)
MESSAGE = 0x0219A818              # (side, message id)
PICKER = 0x0219C430               # (side, count code, cid, param)
READBACK = 0x0219C510             # () -> &candidate word of the pick
CPUSH, CPOP = 0x021D28A4, 0x021D2964
STATE = 0x0229AAFC
EXTRA_COUNT0 = 0x0229ACAC
SIDE_STRIDE = 0x0B3C
MSG_SEND_GY = 0x3A
H3_RESUME = 0x02243F70
IDX = 0xFF50
LIGHT = 1
for _a in (TARGET_AT, ZONE_CID, GET_ATTR, CID_LEVEL, DESTROY_ONE, ZONE_MOVE, POST_SENT, EXTRA_B, COUNT_C, MESSAGE, PICKER, READBACK, CPUSH, CPOP, H3_RESUME):
    assert _a % 2 == 0


def row_blob(cid: int, handler: int) -> bytes:
    """Virtual criteria row {cid, aux 0xFFFF, handler | 1, word 2} (Block Dragon's ROW shape), padded to 0x20."""
    return struct.pack("<HHII", cid, 0xFFFF, handler | 1, 2) + bytes(0x14)


def zh_stub(base: int) -> bytes:
    """Criteria handler (r0 = &row, r1 = side, r2 = param): the Extra Deck enumerator over side's Extra Deck, or the OTHER player's when param bit 16 is set."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("SUB", "SP, #0x10")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("ADD", "R4, R1, #0x0")
    b.insn("ADD", "R6, R2, #0x0")
    b.insn("MOV", "R0, #0x2")
    b.insn("STR", "R0, [SP, #0x0]")              # criteria word: a monster
    b.insn("LSR", "R0, R6, #0x10")
    b.insn("MOV", "R1, #0x1")
    b.insn("AND", "R0, R1")
    b.insn("STR", "R0, [SP, #0x4]")              # flags bit 0 = flip to the other player's Extra Deck
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("LDRH", "R1, [R5, #0x0]")
    b.insn("MOV", "R2, #0x0")
    b.insn("LSL", "R3, R6, #0x12")
    b.insn("LSR", "R3, R3, #0x12")
    b.ldr_const(7, EXTRA_B | 1)
    b.insn("BLX", "R7")
    b.insn("ADD", "SP, #0x10")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return b.assemble(base, pad="nop")


def h2_front(base: int, cid: int, prev: int) -> bytes:
    """Criteria resolver miss tail (r5 = cid): the donor -> virtual index, popping the caller's frame; else onward to the previous head."""
    b = EffectBuilder()
    b.ldr_const(0, cid)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, IDX)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(prev)
    return b.assemble(base, pad="nop")


def h3_front(base: int, rows: int, prev: int) -> bytes:
    """Invoker row compute (r6 = index): IDX -> r0 = our row, r3 = [r0 + 4], resume 0x02243F70; else tail to the previous head."""
    b = EffectBuilder()
    b.ldr_const(0, IDX)
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


def _step_regs(b: EffectBuilder) -> None:
    """r7 = ZST.  -> r0 = the current step's picker, r1 = its target, r2 = the packed step, r3 = param (bit 16 = picker != target)."""
    b.insn("LDR", "R0, [R7, #0x0]")
    b.insn("LSL", "R0, R0, #0x2")
    b.insn("ADD", "R0, R0, R7")
    b.insn("LDR", "R2, [R0, #0xC]")
    b.insn("LSL", "R0, R2, #0x18")
    b.insn("LSR", "R0, R0, #0x18")
    b.insn("LSL", "R1, R2, #0x10")
    b.insn("LSR", "R1, R1, #0x18")
    b.insn("ADD", "R3, R0, #0x0")
    b.insn("EOR", "R3, R1")
    b.insn("LSL", "R3, R3, #0x10")


def resz_stub(base: int, zst: int, flag: int) -> bytes:
    """Zaborg cls1 +04 (r0 desc, r1 ev) on the [STATE+0x70] phase protocol (see the module docstring)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("SUB", "SP, #0x10")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("STR", "R1, [SP, #0x0]")
    b.ldr_const(6, STATE)
    b.ldr_const(7, zst)
    b.insn("LDR", "R0, [R6, #0x70]")
    for k, ph in enumerate((0x80, 0x7F, 0x7E, 0x7D, 0x64)):    # conditional branches reach only +-256 B: skip over an unconditional B
        b.insn("CMP", f"R0, #0x{ph:X}")
        b.insn("BNE", f"n{k}")
        b.insn("B", f"p{ph:x}")
        b.label(f"n{k}")
    b.insn("MOV", "R0, #0x0")
    b.insn("B", "ret")

    # ---- 0x80: read the target, destroy it, plan the sends ---------------------------------------------------------------
    b.label("p80")
    b.insn("MOV", "R1, #0x0")
    b.insn("STR", "R1, [SP, #0x4]")              # LIGHT?
    b.insn("STR", "R1, [SP, #0x8]")              # original Level
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("ADD", "R2, SP, #0xC")
    b.ldr_const(3, TARGET_AT | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "destroy")
    b.insn("LDR", "R1, [SP, #0xC]")
    b.insn("LSL", "R2, R1, #0x18")
    b.insn("LSR", "R0, R2, #0x18")               # side
    b.insn("LSL", "R1, R1, #0x10")
    b.insn("LSR", "R1, R1, #0x18")               # zone
    b.ldr_const(3, ZONE_CID | 1)
    b.insn("BLX", "R3")
    b.insn("ADD", "R5, R0, #0x0")                # cid
    b.ldr_const(3, GET_ATTR | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #" + hex(LIGHT))
    b.insn("BNE", "destroy")
    b.insn("MOV", "R1, #0x1")
    b.insn("STR", "R1, [SP, #0x4]")
    b.insn("ADD", "R0, R5, #0x0")
    b.ldr_const(3, CID_LEVEL | 1)
    b.insn("BLX", "R3")
    b.insn("STR", "R0, [SP, #0x8]")
    b.label("destroy")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, DESTROY_ONE | 1)
    b.insn("BLX", "R3")
    b.insn("LDR", "R0, [SP, #0x4]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "plan")
    b.insn("MOV", "R0, #0x0")
    b.insn("B", "ret")                           # not LIGHT: nothing is sent
    b.label("plan")
    # controller c -> r5, other o -> r6 (STATE ptr is reloaded where needed)
    b.insn("LDRB", "R5, [R4, #0x2]")
    b.insn("LDRB", "R0, [R4, #0x6]")
    b.insn("EOR", "R5, R0")
    b.insn("MOV", "R0, #0x1")
    b.insn("AND", "R5, R0")
    # n_c = min(L, count_c)
    b.ldr_const(0, EXTRA_COUNT0)
    b.ldr_const(1, SIDE_STRIDE)
    b.insn("MUL", "R1, R5")
    b.insn("LDR", "R0, [R0, R1]")
    b.insn("LDR", "R1, [SP, #0x8]")
    b.insn("CMP", "R0, R1")
    b.insn("BLE", "ncok")
    b.insn("ADD", "R0, R1, #0x0")
    b.label("ncok")
    b.insn("LSL", "R0, R0, #0x10")
    b.insn("ORR", "R0, R5")
    b.insn("LSL", "R1, R5, #0x8")
    b.insn("ORR", "R0, R1")
    b.insn("STR", "R0, [R7, #0xC]")              # step 0 = (c, c, n_c)
    # n_o = min(L, count_o), o = c ^ 1 -> r6
    b.insn("MOV", "R6, #0x1")
    b.insn("EOR", "R6, R5")
    b.ldr_const(0, EXTRA_COUNT0)
    b.ldr_const(1, SIDE_STRIDE)
    b.insn("MUL", "R1, R6")
    b.insn("LDR", "R0, [R0, R1]")
    b.insn("LDR", "R1, [SP, #0x8]")
    b.insn("CMP", "R0, R1")
    b.insn("BLE", "nook")
    b.insn("ADD", "R0, R1, #0x0")
    b.label("nook")
    b.insn("LSL", "R0, R0, #0x10")               # n_o << 16
    b.insn("LSL", "R1, R6, #0x8")
    b.insn("ORR", "R0, R1")                      # | target (o) << 8
    b.ldr_const(1, flag)
    b.insn("LDR", "R1, [R1, #0x0]")
    b.insn("LSR", "R1, R1, #" + str(LIGHT))
    b.insn("MOV", "R2, #0x1")
    b.insn("AND", "R1, R2")                      # 1 = Tributed by a LIGHT monster: the controller picks the opponent's cards too
    b.insn("BEQ", "ownpick")
    b.insn("ORR", "R0, R5")                      # picker = c
    b.insn("B", "stepo")
    b.label("ownpick")
    b.insn("ORR", "R0, R6")                      # picker = o
    b.label("stepo")
    b.insn("STR", "R0, [R7, #0x10]")             # step 1
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [R7, #0x0]")              # step index
    b.insn("STR", "R0, [R7, #0x4]")              # picks done in this step
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("LDR", "R1, [SP, #0x0]")
    b.ldr_const(3, CPUSH | 1)
    b.insn("BLX", "R3")
    b.insn("MOV", "R0, #0x7F")
    b.insn("B", "ret")

    # ---- 0x7F: next pick (or next step) ---------------------------------------------------------------------------------------
    b.label("p7f")
    b.label("l7f")
    b.insn("LDR", "R0, [R7, #0x0]")
    b.insn("CMP", "R0, #0x2")
    b.insn("BGE", "to64")
    b.insn("LSL", "R1, R0, #0x2")
    b.insn("ADD", "R1, R1, R7")
    b.insn("LDR", "R2, [R1, #0xC]")
    b.insn("LSR", "R3, R2, #0x10")
    b.insn("MOV", "R1, #0xFF")
    b.insn("AND", "R3, R1")                      # n of this step
    b.insn("LDR", "R1, [R7, #0x4]")              # picks done
    b.insn("CMP", "R1, R3")
    b.insn("BLT", "need")
    b.label("adv")
    b.insn("ADD", "R0, R0, #0x1")
    b.insn("STR", "R0, [R7, #0x0]")
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [R7, #0x4]")
    b.insn("B", "l7f")
    b.label("need")
    _step_regs(b)                                # r0 picker, r3 param
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("LDRH", "R1, [R4, #0x0]")             # the donor's cid
    b.insn("ADD", "R2, R3, #0x0")
    b.ldr_const(3, COUNT_C | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BGT", "ask")
    b.insn("LDR", "R0, [R7, #0x0]")              # nothing left to pick in this step
    b.insn("B", "adv")
    b.label("ask")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", "R1, #" + hex(MSG_SEND_GY))
    b.ldr_const(3, MESSAGE | 1)
    b.insn("BLX", "R3")
    b.insn("MOV", "R0, #0x7E")
    b.insn("B", "ret")
    b.label("to64")
    b.insn("MOV", "R0, #0x64")
    b.insn("B", "ret")

    # ---- 0x7E: open the picker (exactly 1) -----------------------------------------------------------------------------------
    b.label("p7e")
    _step_regs(b)                                # r0 picker, r3 param
    b.insn("MOV", "R1, #0x6")
    b.insn("LDRH", "R2, [R4, #0x0]")
    b.ldr_const(5, PICKER | 1)
    b.insn("BLX", "R5")
    b.insn("MOV", "R0, #0x7D")
    b.insn("B", "ret")

    # ---- 0x7D: read the pick back, send it to the GY --------------------------------------------------------------------------
    b.label("p7d")
    b.ldr_const(3, READBACK | 1)
    b.insn("BLX", "R3")
    b.insn("LDR", "R0, [R0, #0x0]")              # the candidate's packed word
    b.insn("LSL", "R1, R0, #1")
    b.insn("LSR", "R1, R1, #0x18")
    b.insn("LSL", "R1, R1, #1")                  # instance index << 1
    b.insn("LSL", "R2, R0, #0x11")
    b.insn("LSR", "R2, R2, #0x1F")               # side bit
    b.insn("ADD", "R2, R1, R2")                  # ref
    b.insn("MOV", "R1, #0x1")
    b.insn("AND", "R1, R2")                      # the card's side
    b.insn("ADD", "R5, R1, #0")
    b.insn("SUB", "SP, #0xC")
    b.insn("MOV", "R6, #0xE")
    b.insn("STR", "R6, [SP, #0x0]")
    b.insn("MOV", "R6, #0x1")
    b.insn("STR", "R6, [SP, #0x4]")
    b.insn("MOV", "R6, #0x0")
    b.insn("STR", "R6, [SP, #0x8]")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", "R1, #0xC")
    b.insn("ADD", "R3, R5, #0x0")
    b.ldr_const(6, ZONE_MOVE | 1)
    b.insn("BLX", "R6")
    b.insn("ADD", "SP, #0xC")
    b.insn("MOV", "R0, #0x26")
    b.insn("MOV", "R1, #0x0")
    b.ldr_const(6, POST_SENT | 1)
    b.insn("BLX", "R6")
    b.insn("LDR", "R0, [R7, #0x4]")
    b.insn("ADD", "R0, R0, #0x1")
    b.insn("STR", "R0, [R7, #0x4]")
    b.insn("MOV", "R0, #0x7F")
    b.insn("B", "ret")

    # ---- 0x64: close the session ----------------------------------------------------------------------------------------------
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
