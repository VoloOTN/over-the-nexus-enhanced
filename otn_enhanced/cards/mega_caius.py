"""Caius the Mega Monarch's resolver stub (imported by mega_monarch; the criteria handler/row/fronts are mega_raiza's, instantiated for this cid).

"If this card is Tribute Summoned: Target 1 card on the field; banish it, and if you do, inflict 1000 damage to your opponent, then, if it is a DARK Monster Card,
banish all cards with that name from the hand, Main Deck, Extra Deck, and GY of the player who controlled it. If this card was Tribute Summoned by Tributing a DARK
monster, add this additional effect. * You can target 2 cards, instead."

cls1 record = Caius the Shadow Monarch's own targeting ({cid, 0, RESC, 0x021E24D1 (any card on the field), 0x0224A115, 0, 0x02234E11 (the native single-target
selector, prompt 0x125)}), so the FIRST card is a real target chosen at activation.  RESC is the +04 phase machine on [0x0229AAFC+0x70]:
  0x80  read target 0 (desc +0x14 via 0x022349B0) -> its (side, zone); remember it; open the pick session (0x021D28A4); after a DARK Tribute (latch bit 2) go to 0x7F,
        else straight to 0x7C
  0x7F  count the candidates (virtual criteria row 0xFF52, mode 0 = any field card except target 0); none -> 0x7C; else prompt 0x125 -> 0x7E
  0x7E  picker 0x0219C430(controller, 6, cid, 0)  |  0x7D read the pick, locate it (0x021A220C) as the SECOND card -> 0x7C
  0x7C  for each card: still valid (0x0224A924), read its cid, banish it (0x021CF43C), inflict 1000 (0x021CFBC8(desc, 1 - controller, 1000)); a DARK Monster Card
        also loses every card with the same cid from the hand / Extra Deck / Deck / GY of the player who controlled it (0x021C69D0 to zone 0xF, bottom-up)
  0x64  close the session (0x021D2964), consume the latch.
KNOWN GAPS (stated, not deviations): (1) the SECOND card (DARK Tribute) is chosen at resolution, not targeted, and is not optional ('You can target 2 cards, instead');
(2) 'cards with that name' = the same cid (alternate-art cids of one name are not matched); (3) the 1000 damage is dealt once PER banished card (the text is silent for
2 targets: a ruling to confirm with the user); (4) 'if you do' is assumed (no check that the banish happened); (5) the banish mover 0x021C69D0 -> zone 0xF is used for
the hand / Extra Deck / Deck / GY copies without the native banish-replacement check or a 'banished' event (UNVERIFIED).
"""
from __future__ import annotations

from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.cards import mega_raiza as MR

TARGET_AT = 0x022349B0
ZONE_CID = 0x021A36EC
GET_ATTR = 0x0202ABC8
IS_MONSTER = 0x02029E60
VALID = 0x0224A924                 # (desc, side, zone) -> can this target still be affected
BANISH_FIELD = 0x021CF43C          # (desc, side, zone, 0) queued field -> banished (the native Caius the Shadow Monarch's call)
DAMAGE = 0x021CFBC8                # (desc, side to hurt, amount)
ZONE_MOVE = 0x021C69D0
SLOT_PTR = 0x0219CA28
STATE = 0x0229AAFC
MSG_BANISH = 0x125                 # the native selector's own prompt
DARK = 2
NONE = 0xFFFF
SIDE_STRIDE = 0x0B3C
# (zone code, player-0 count address): hand 0xB (+0x0C), Extra 0xC (+0x18), Deck 0xD (+0x10), GY 0xE (+0x14)
COPY_ZONES = ((0x0B, 0x0229ACA0), (0x0C, 0x0229ACAC), (0x0D, 0x0229ACA4), (0x0E, 0x0229ACA8))
for _a in (TARGET_AT, ZONE_CID, GET_ATTR, IS_MONSTER, VALID, BANISH_FIELD, DAMAGE, ZONE_MOVE, SLOT_PTR):
    assert _a % 2 == 0

_N = [0]
_INV = {"BEQ": "BNE", "BNE": "BEQ", "BLE": "BGT", "BGT": "BLE", "BGE": "BLT", "BLT": "BGE"}


def _far(b: EffectBuilder, cond: str, target: str) -> None:
    """A conditional branch to a label that may be > 256 B away: the inverse condition hops over an unconditional B."""
    _N[0] += 1
    tmp = f"far{_N[0]}"
    b.insn(_INV[cond], tmp)
    b.insn("B", target)
    b.label(tmp)


def _apply(b: EffectBuilder) -> None:
    """The subroutine `ap` (called with BL from RESC, which pushed LR): the card whose location (side | zone << 8) is in r5, r4 = desc.  Its own `push {lr}` shifts the
    caller's frame by 4: [sp+8] = controller, [sp+0xC] = cid."""
    which = "x"
    skip = "skipx"
    b.label("ap")
    b.insn("PUSH", "{LR}")
    b.insn("LSL", "R1, R5, #0x18")
    b.insn("LSR", "R6, R1, #0x18")               # side
    b.insn("LSL", "R1, R5, #0x10")
    b.insn("LSR", "R7, R1, #0x18")               # zone
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("ADD", "R1, R6, #0x0")
    b.insn("ADD", "R2, R7, #0x0")
    b.ldr_const(3, VALID | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    _far(b, "BEQ", skip)
    b.insn("ADD", "R0, R6, #0x0")
    b.insn("ADD", "R1, R7, #0x0")
    b.ldr_const(3, ZONE_CID | 1)
    b.insn("BLX", "R3")
    b.insn("STR", "R0, [SP, #0xC]")              # the cid
    b.insn("STR", "R6, [SP, #0x8]")              # its controller
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("ADD", "R1, R6, #0x0")
    b.insn("ADD", "R2, R7, #0x0")
    b.insn("MOV", "R3, #0x0")
    b.ldr_const(6, BANISH_FIELD | 1)
    b.insn("BLX", "R6")
    b.insn("LDRB", "R1, [R4, #0x2]")
    b.insn("MOV", "R2, #0x1")
    b.insn("EOR", "R1, R2")                      # the opponent of the effect's controller
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("MOV", "R2, #0xFA")
    b.insn("LSL", "R2, R2, #0x2")                # 1000
    b.ldr_const(3, DAMAGE | 1)
    b.insn("BLX", "R3")
    b.insn("LDR", "R0, [SP, #0xC]")
    b.ldr_const(3, IS_MONSTER | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    _far(b, "BEQ", skip)
    b.insn("LDR", "R0, [SP, #0xC]")
    b.ldr_const(3, GET_ATTR | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #" + hex(DARK))
    _far(b, "BNE", skip)
    # ---- every copy of that cid, hand / Extra Deck / Deck / GY of the controller, bottom-up ----
    for zone, count0 in COPY_ZONES:
        lab = f"{which}z{zone:x}"
        b.ldr_const(0, count0)
        b.ldr_const(1, SIDE_STRIDE)
        b.insn("LDR", "R2, [SP, #0x8]")
        b.insn("MUL", "R1, R2")
        b.insn("LDR", "R7, [R0, R1]")            # count
        b.label(lab + "l")
        b.insn("CMP", "R7, #0x0")
        b.insn("BLE", lab + "e")
        b.insn("SUB", "R7, #0x1")
        b.insn("LDR", "R0, [SP, #0x8]")
        b.insn("MOV", "R1, #" + hex(zone))
        b.insn("ADD", "R2, R7, #0x0")
        b.ldr_const(3, SLOT_PTR | 1)
        b.insn("BLX", "R3")
        b.insn("LDR", "R6, [R0, #0x0]")          # the card word
        b.insn("LSL", "R0, R6, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.insn("LDR", "R1, [SP, #0xC]")
        b.insn("CMP", "R0, R1")
        b.insn("BNE", lab + "l")
        b.insn("LSL", "R1, R6, #1")              # ref
        b.insn("LSR", "R1, R1, #0x18")
        b.insn("LSL", "R1, R1, #1")
        b.insn("LSL", "R2, R6, #0x11")
        b.insn("LSR", "R2, R2, #0x1F")
        b.insn("ADD", "R2, R1, R2")
        b.insn("SUB", "SP, #0xC")
        b.insn("MOV", "R0, #0xF")
        b.insn("STR", "R0, [SP, #0x0]")          # destination = banished
        b.insn("MOV", "R0, #0x1")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("MOV", "R0, #0x0")
        b.insn("STR", "R0, [SP, #0x8]")
        b.insn("LDR", "R0, [SP, #0x14]")         # the controller (3 argument words + the pushed LR in between)
        b.insn("MOV", "R1, #" + hex(zone))
        b.insn("ADD", "R3, R0, #0x0")
        b.ldr_const(6, ZONE_MOVE | 1)
        b.insn("BLX", "R6")
        b.insn("ADD", "SP, #0xC")
        b.insn("B", lab + "l")
        b.label(lab + "e")
    b.label(skip)
    b.insn("POP", "{PC}")


def resc_stub(base: int, rst: int, flag: int) -> bytes:
    """r0 = desc, r1 = ev.  rst: +4 excluded ref (target 0), +8 second card ref, +0x10 / +0x14 locations of the two cards (side | zone << 8, 0xFFFF = none)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("SUB", "SP, #0x14")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("STR", "R1, [SP, #0x0]")
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

    # ---- 0x80 ----
    b.label("p80")
    b.ldr_const(5, NONE)
    b.insn("STR", "R5, [R7, #0x4]")
    b.insn("STR", "R5, [R7, #0x8]")
    b.insn("STR", "R5, [R7, #0x10]")
    b.insn("STR", "R5, [R7, #0x14]")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("MOV", "R1, #0x0")
    b.insn("ADD", "R2, SP, #0x8")
    b.ldr_const(3, TARGET_AT | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "noT")
    b.insn("LDR", "R5, [SP, #0x8]")              # target 0: side | zone << 8 (| more bits)
    b.insn("LSL", "R5, R5, #0x10")
    b.insn("LSR", "R5, R5, #0x10")
    b.insn("STR", "R5, [R7, #0x10]")
    # its ref, to exclude it from the second pick: the card word at (side, zone)
    b.insn("LSL", "R0, R5, #0x18")
    b.insn("LSR", "R0, R0, #0x18")               # side
    b.insn("LSL", "R1, R5, #0x10")
    b.insn("LSR", "R1, R1, #0x18")               # zone
    b.insn("MOV", "R2, #0x0")
    b.ldr_const(3, SLOT_PTR | 1)
    b.insn("BLX", "R3")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R1, R0, #1")
    b.insn("LSR", "R1, R1, #0x18")
    b.insn("LSL", "R1, R1, #1")
    b.insn("LSL", "R2, R0, #0x11")
    b.insn("LSR", "R2, R2, #0x1F")
    b.insn("ADD", "R1, R1, R2")
    b.insn("STR", "R1, [R7, #0x4]")
    b.label("noT")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("LDR", "R1, [SP, #0x0]")
    b.ldr_const(3, MR.CPUSH | 1)
    b.insn("BLX", "R3")
    b.ldr_const(1, flag)
    b.insn("LDR", "R1, [R1, #0x0]")
    b.insn("LSR", "R1, R1, #" + str(DARK))
    b.insn("MOV", "R2, #0x1")
    b.insn("AND", "R1, R2")
    b.insn("BEQ", "to7c")
    b.insn("MOV", "R0, #0x7F")
    b.insn("B", "ret")
    b.label("to7c")
    b.insn("MOV", "R0, #0x7C")
    b.insn("B", "ret")

    # ---- 0x7F: is there a second card to pick? ----
    b.label("p7f")
    b.insn("LDRB", "R5, [R4, #0x2]")
    b.insn("LDRB", "R0, [R4, #0x6]")
    b.insn("EOR", "R5, R0")
    b.insn("MOV", "R0, #0x1")
    b.insn("AND", "R5, R0")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("LDRH", "R1, [R4, #0x0]")
    b.insn("MOV", "R2, #0x0")
    b.ldr_const(3, MR.COUNT_C | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BGT", "ask")
    b.insn("MOV", "R0, #0x7C")
    b.insn("B", "ret")
    b.label("ask")
    b.insn("ADD", "R0, R5, #0x0")
    b.ldr_const(1, MSG_BANISH)
    b.ldr_const(3, MR.MESSAGE | 1)
    b.insn("BLX", "R3")
    b.insn("MOV", "R0, #0x7E")
    b.insn("B", "ret")

    # ---- 0x7E ----
    b.label("p7e")
    b.insn("LDRB", "R5, [R4, #0x2]")
    b.insn("LDRB", "R0, [R4, #0x6]")
    b.insn("EOR", "R5, R0")
    b.insn("MOV", "R0, #0x1")
    b.insn("AND", "R0, R5")
    b.insn("MOV", "R1, #0x6")
    b.insn("LDRH", "R2, [R4, #0x0]")
    b.insn("MOV", "R3, #0x0")
    b.ldr_const(6, MR.PICKER | 1)
    b.insn("BLX", "R6")
    b.insn("MOV", "R0, #0x7D")
    b.insn("B", "ret")

    # ---- 0x7D ----
    b.label("p7d")
    b.ldr_const(3, MR.READBACK | 1)
    b.insn("BLX", "R3")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R1, R0, #1")
    b.insn("LSR", "R1, R1, #0x18")
    b.insn("LSL", "R1, R1, #1")
    b.insn("LSL", "R2, R0, #0x11")
    b.insn("LSR", "R2, R2, #0x1F")
    b.insn("ADD", "R0, R1, R2")                  # ref
    b.ldr_const(3, MR.LOCATOR | 1)
    b.insn("BLX", "R3")                          # (zone << 8) | side
    b.insn("LSL", "R0, R0, #0x10")
    b.insn("LSR", "R0, R0, #0x10")
    b.insn("STR", "R0, [R7, #0x14]")
    b.insn("MOV", "R0, #0x7C")
    b.insn("B", "ret")

    # ---- 0x7C: apply to each card ----
    b.label("p7c")
    for which, off in (("a", 0x10), ("b", 0x14)):
        b.insn("LDR", "R5, [R7, #" + hex(off) + "]")
        b.ldr_const(0, NONE)
        b.insn("CMP", "R5, R0")
        b.insn("BEQ", f"no{which}")
        b.bl_label("ap")
        b.ldr_const(7, rst)                      # `ap` clobbers r6 / r7 (zone, loop index): r7 = the state block must be reloaded (this was the 2026-11-10 data abort)
        b.label(f"no{which}")
    b.insn("MOV", "R0, #0x64")
    b.insn("B", "ret")

    b.label("p64")
    b.ldr_const(3, MR.CPOP | 1)
    b.insn("BLX", "R3")
    b.ldr_const(1, flag)
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [R1, #0x0]")
    b.label("ret")
    b.insn("ADD", "SP, #0x14")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    _apply(b)
    return b.assemble(base, pad="nop")
