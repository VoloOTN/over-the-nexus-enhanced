"""Mega Monarchs (single-card TEST ROM, NOT SHIPPED).  Built so far: GRANMARG (0x0FD7, donor Big Insect) and MOBIUS (0x0FF3, donor Grappler).

GRANMARG THE MEGA MONARCH: "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. When this card is Tribute Summoned: Target up to 2 Set cards on
    the field; destroy those targets. If this card was Tribute Summoned by Tributing an EARTH monster, add this additional effect. * Also, draw 1 card after that."
    M0 + E1 + E2 in-game confirmed by user 2026-11-10 ("All of them").
MOBIUS THE MEGA MONARCH:   "... When this card is Tribute Summoned: You can target up to 3 Spell/Trap Cards on the field; destroy those targets. If this card was Tribute
    Summoned by Tributing a WATER monster, add this additional effect. * Your opponent cannot activate the targeted cards in response to this effect's activation."
    M0 + E1 built (AWAITING IN-GAME TEST).  E2 (the WATER response lock) is NOT BUILT, a known gap, not a deviation: the engine hook exists
    (0x021ECDA4, "activation-prohibited" predicate, reads the activating card's ref at desc+0xC) but needs the target refs captured between selection and
    the chain response window; see notes/monarch-megas-findings.md.  The WATER Tribute IS recorded (latch bit 3) for when it is built.

SHARED MECHANISMS (static + CPU-trace proven; Granmarg user-tested)
M0  0x021AE148(player r0, summoned cid r1, candidate side r2, slot r3) is the engine's native "this monster counts as 2 Tributes for the card being summoned" predicate (the
    Tribute picker lists the monster twice; the CPU's Tribute AI calls it too).  A Mega is Level 8 = 2 Tributes, so ONE own monster that counts as 2 pays the whole cost.
    "Tribute Summoned" = zone flag word bit 3 (CPU trace: 0x410108 -> 0x108 on Level 5-6 Tribute Summons, clear on Level<=4 Normal and Special Summons).
    BL over `adds r5,r3,#0 ; adds r6,r1,#0` @0x021AE14A returns TRUE straight out of the host on a hit.
Trigger  The Normal-Summon event dispatcher 0x02265768 only searches the Monarch list 0x0228F5B8 when [0x02298A28+0x2C] != 0 (>= 1 Tribute paid).  That list is full, so the
    `bl 0x02022E14` @0x022657B8 gets a front answering 1 for the Mega cids; the event is posted with selector 1 = a cls1 record.
Selector  cls1 +14 = Mobius the Frost Monarch's multi-target arm of 0x02237A74 (r6 = max targets, r7 = prompt 0x8D, [sp+4] = 0x21) entered at 0x02237C3E with the prologue
    replicated by the stub; Granmarg passes 2, Mobius 3.  Resolver: the native up-to-N destroy 0x022046B8 (cid-blind: iterates the targets in the desc).
Tribute capture  The Tributed monsters are gone by resolution, so the four Tribute-payment BLs of 0x021CF68C (0x02262574 / 0x02266F7E / 0x02267BF6 / 0x02268DA4) are fronted:
    when the summoned cid ([0x02298A28+0xE]) is a Mega, each selected entry ([0x02298A28+0x30+2i], count +0x2C) -> (side, slot) 0x021A241C -> cid 0x021A36EC -> BASE
    attribute 0x0202ABC8 and CAVE_MM_FLAG |= 1 << attribute (reset on every Mega payment).  Granmarg's RES tests bit 5 (EARTH) and draws 1 (0x021D12F4) after the destroy.
    WARNING: BASE attribute, not the current one; which payment BL a human Summon takes is UNPROVEN (all four fronted).

    uv run python _build_mega_monarch.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

import ndspy.rom

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.data import card_text
from otn_enhanced.data.card_stats import TEXT_LANGS, apply_stats_and_text
from otn_enhanced.dsl import CLS1, Compiled, Row, card_props
from otn_enhanced.effects import cave3, ov5_cave as O5
from otn_enhanced.cards import angmarl as AG
from otn_enhanced.cards import mega_caius as MC
from otn_enhanced.cards import mega_raiza as MR
from otn_enhanced.cards import mega_zaborg as MZ
from otn_enhanced.effects.common import bl as common_bl, insert_sorted, rows
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE

CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_mega_monarch.nds"

GRANMARG, MOBIUS, ZABORG, RAIZA, CAIUS, THESTALOS = 0x0FD7, 0x0FF3, 0x139B, 0x1E87, 0x0FC5, 0x127B
MEGAS = (GRANMARG, MOBIUS, ZABORG, RAIZA, CAIUS, THESTALOS)
ANGMARL = AG.ANGMARL                                # not a Mega: a Level 6 Monarch with its own Tribute Summon trigger (the TRIG front answers for it, M0 / CAP do not)
TRIGGERS = MEGAS + (ANGMARL,)
EHTHER = 0x1312                                     # Ehther the Heavenly Monarch (cards/erebus.py hosts both)
EREBUS = 0x1313                                     # Erebus the Underworld Monarch (cards/erebus.py): M0 + the Tribute Summon trigger front answer for it; everything else is its own module
CLS1_PHANTOMS = {GRANMARG: 0x0E21, MOBIUS: 0x0E3D, ZABORG: 0x0E41, RAIZA: 0x0E48, CAIUS: 0x0E74, THESTALOS: 0x0E77, ANGMARL: 0x0E7E}

# --- engine natives (Thumb; the |1 is the interworking bit) -------------------------------------------------------------------
LIST_SEARCH = 0x02022E14                         # (cid, sorted u16 list, count) -> 1/0
TRIB_PAY = 0x021CF68C                            # (player, slot mask): Tribute the masked monsters
REF_TO_ZONE = 0x021A241C                         # packed ref -> side | slot << 8
ZONE_CID = 0x021A36EC                            # (side, slot) -> cid
GET_ATTR = 0x0202ABC8
DRAW = 0x021D12F4                                # (side, count)
DESTROY_UP_TO_N = 0x022046B8                     # native cls1 resolver body: effect-destroy every target in the desc
NATIVE_UP_TO_N = 0x022048A5                      # the same as a full cls1 +04 resolver (Mobius the Frost Monarch's)
SEL_MID = 0x02237C3E                             # inside Mobius' multi-target selector: after its arm set r6/r7/r0
SET_FILTER = 0x021DFD1D                          # vanilla Granmarg the Rock Monarch's cls1 +08 ("Set card")
ST_FILTER = 0x021DB3BD                           # vanilla Mobius the Frost Monarch's cls1 +08 (Spell/Trap Card)
YOU_CAN = 0x021E50DD                             # cls1 +10: the native "You can" prompt (Mobius / Senju)
ALWAYS = 0x0224A115                              # `movs r0,#2 ; bx lr` -- the always-activatable cond stub
SUMMON = 0x02298A28
EARTH, WATER, LIGHT = 5, 3, 1
DESTROY_ONE = 0x02204674                        # native 'destroy target 0' body of the cls1 +04 resolver 0x02204899 (Zaborg the Thunder Monarch's)
CID_LEVEL = 0x0202ABD8                          # (cid) -> Level
ZONE_MOVE = 0x021C69D0                          # (side, src zone, ref, side, [sp]=dest zone, [sp+4]=1, [sp+8]=0): the engine's generic zone-to-zone mover (Extra 0xC, GY 0xE)
POST_SENT = 0x022391CC                          # (0x26, 0): the 'sent to the GY' event the native GY mover 0x021C6A18 posts after moving
EXTRA_COUNT0 = 0x0229ACAC                       # player 0 Extra Deck count; +side*0xB3C
EXTRA_ARRAY0 = 0x0229AC94 + 0x4E4              # player 0 Extra Deck packed words; +side*0xB3C
ZAB_FILTER = 0x021D8CE5                         # Zaborg the Thunder Monarch's cls1 +08 (a monster on the field)
ZAB_SEL = 0x02234DA5                            # his cls1 +14 (the single-target selector, prompt 0x119)
PHASEBASE = 0x0229DD14                          # +0x34 turn player, +0x48 phase
TARGET_AT = 0x022349B0                          # (desc, i, &out) -> out = side | zone << 8 of target i
DESTROY_NATIVE_FULL = 0x022048A4                # Mobius the Frost Monarch's cls1 +04 (even address; the record carries |1)
PRED_SITES = (0x021EDA2E, 0x021D6B5C, 0x021FC116)   # the three BLs to the activation-prohibited predicate 0x021ECDA4
LOCK_TAIL = cave3.CAVE3_SEKKA_LOCK              # what those BLs reach in the CHAIN ROM (Sekka's Light front, which calls the native predicate); a stock ROM is NOT supported
for _a in (LIST_SEARCH, TRIB_PAY, REF_TO_ZONE, ZONE_CID, GET_ATTR, DRAW, DESTROY_UP_TO_N, SEL_MID, TARGET_AT, DESTROY_NATIVE_FULL, DESTROY_ONE, CID_LEVEL, ZONE_MOVE, POST_SENT):
    assert _a % 2 == 0

# --- hook sites ----------------------------------------------------------------------------------------------------------------
HOOK = 0x021AE14A
HOOK_NATIVE = bytes.fromhex("1d1c0e1c")          # adds r5,r3,#0 ; adds r6,r1,#0
FLAGS = 0x0229ACD8
SIDE_STRIDE = 0x0B3C
BIT_TRIBUTE_SUMMONED = 3
BIT_NOT_A_CANDIDATE = 6                          # the host already rejects bit 6: keep it
TRIG_SITE = 0x022657B8                           # bl 0x02022E14 on the Monarch list 0x0228F5B8 (count 0x12)
PAY_SITES = (0x02262574, 0x02266F7E, 0x02267BF6, 0x02268DA4)

H2_SITE, H2_PREV = 0x02243F24, O5.CAVE_BD_H2               # the chain heads (Block Dragon shipped 2026-11-09); ours sit AHEAD
H3_SITE, H3_PREV = 0x02243F62, O5.CAVE_BD_H3
DATA_STUBS = ("ZROW", "RROW", "CROW", "AG_ROWS", "AG_DATA")                          # raw data, not code: skip the Thumb-1 scan
CAIUS_IDX = 0xFF52
FIELD_ANY_FILTER = 0x021E24D1                     # vanilla Caius the Shadow Monarch cls1 +08: any card on the field
FIELD_ANY_SEL = 0x02234E11                        # his +14: the native single-target selector (prompt 0x125)
RESERVES = {**AG.reserves(), "REST": 0xA0, "RESC": 0x320, "CRH": 0xA0, "CROW": 0x20, "CH2": 0x20, "CH3": 0x30, "RESR": 0x1D0, "RRH": 0xA0, "RROW": 0x20, "RH2": 0x20, "RH3": 0x30, "ZROW": 0x20, "ZH": 0x50, "ZH2": 0x20, "ZH3": 0x30, "M0": 0xA0, "TRIG": 0x80, "SEL": 0x18, "SEL3": 0xA0, "RESM": 0x20, "LKF": 0x70, "RES": 0x50, "CAP": 0xA0, "RESZ": 0x200}


def m0_stub(base: int, megas=MEGAS) -> bytes:
    b = EffectBuilder()
    for k, cid in enumerate(megas):
        last = k == len(megas) - 1
        b.ldr_const(4, cid)
        b.insn("CMP", "R1, R4")
        b.insn("BNE" if last else "BEQ", "miss" if last else "cand")
    b.label("cand")
    b.insn("CMP", "R2, R0")                      # own monsters only
    b.insn("BNE", "miss")
    b.ldr_const(4, SIDE_STRIDE)
    b.insn("MOV", "R5, #0x1")
    b.insn("AND", "R5, R2")
    b.insn("MUL", "R4, R5")                      # side * 0xB3C
    b.insn("MOV", "R5, #0x14")
    b.insn("MUL", "R5, R3")                      # slot * 0x14
    b.insn("ADD", "R4, R4, R5")
    b.ldr_const(5, FLAGS)
    b.insn("LDR", "R4, [R4, R5]")                # the zone flag word
    b.insn("MOV", "R6, #0x1")
    b.insn("LSR", f"R5, R4, #{BIT_NOT_A_CANDIDATE}")
    b.insn("TST", "R5, R6")
    b.insn("BNE", "miss")
    b.insn("LSR", f"R5, R4, #{BIT_TRIBUTE_SUMMONED}")
    b.insn("TST", "R5, R6")
    b.insn("BEQ", "miss")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")    # return TRUE from the host (its frame is exactly this push)
    b.label("miss")
    b.insn("ADD", "R5, R3, #0")                  # replay the displaced pair
    b.insn("ADD", "R6, R1, #0")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def trig_stub(base: int, megas=MEGAS) -> bytes:
    """`bl 0x02022E14` front: r0 = cid, r1 = list, r2 = count.  A Mega answers 1; everything else tail-calls the native search (LR untouched)."""
    b = EffectBuilder()
    for cid in megas:
        b.ldr_const(3, cid)
        b.insn("CMP", "R0, R3")
        b.insn("BEQ", "hit")
    b.ldr_const(3, LIST_SEARCH | 1)
    b.insn("BX", "R3")
    b.label("hit")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    return b.assemble(base, pad="nop")


def sel_stub(base: int, count: int) -> bytes:
    """cls1 +14: Mobius' arm (r6 = targets, r7 = prompt 0x8D, r0 -> [sp+4] = 0x21, [sp] = 0) entered at 0x02237C3E with the selector's own frame."""
    b = EffectBuilder()
    b.insn("PUSH", "{R1, R2, R3, R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0")
    b.insn("MOV", "R1, #0x0")
    b.insn("STR", "R1, [SP, #0x0]")
    b.insn("MOV", "R6, #" + hex(count))
    b.insn("MOV", "R7, #0x8D")
    b.insn("MOV", "R0, #0x21")
    b.ldr_const(3, SEL_MID | 1)
    b.insn("BX", "R3")
    return b.assemble(base, pad="nop")


def res_stub(base: int, flag: int) -> bytes:
    """Granmarg cls1 +04: native destroy, then E2 (draw 1 if latch bit EARTH is set; the latch is consumed)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, LR}")
    b.insn("ADD", "R4, R0, #0")
    b.ldr_const(1, DESTROY_UP_TO_N | 1)
    b.insn("BLX", "R1")
    b.ldr_const(1, flag)
    b.insn("LDR", "R0, [R1, #0x0]")
    b.insn("LSR", f"R0, R0, #{EARTH}")
    b.insn("MOV", "R2, #0x1")
    b.insn("TST", "R0, R2")
    b.insn("BEQ", "done")
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [R1, #0x0]")
    b.insn("LDRB", "R0, [R4, #0x2]")             # the controller
    b.insn("MOV", "R1, #0x1")
    b.ldr_const(2, DRAW | 1)
    b.insn("BLX", "R2")
    b.label("done")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, PC}")
    return b.assemble(base, pad="nop")


def cap_stub(base: int, flag: int, megas=MEGAS, tail: int = TRIB_PAY) -> bytes:
    """Front over `bl 0x021CF68C(player r0, mask r1)`: when the summoned cid is a Mega, latch 1 << attribute of every selected Tribute; then run the native payment."""
    b = EffectBuilder()
    b.insn("PUSH", "{R0, R1, R4, R5, R6, R7, LR}")
    b.ldr_const(4, SUMMON)
    b.insn("LDRH", "R0, [R4, #0xE]")
    for cid in megas:
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "go")
    b.insn("B", "tail")
    b.label("go")
    b.insn("MOV", "R5, #0x0")
    b.ldr_const(7, flag)
    b.insn("MOV", "R0, #0x0")
    b.insn("STR", "R0, [R7, #0x0]")
    b.label("loop")
    b.insn("LDRH", "R0, [R4, #0x2C]")
    b.insn("CMP", "R5, R0")
    b.insn("BGE", "tail")
    b.insn("LSL", "R0, R5, #1")
    b.insn("ADD", "R0, R4, R0")
    b.insn("LDRH", "R0, [R0, #0x30]")            # the entry's packed ref
    b.ldr_const(1, REF_TO_ZONE | 1)
    b.insn("BLX", "R1")                          # r0 = side | slot << 8
    b.insn("LSL", "R1, R0, #0x18")
    b.insn("LSR", "R6, R1, #0x18")               # r6 = side
    b.insn("LSL", "R0, R0, #0x10")
    b.insn("LSR", "R1, R0, #0x18")               # r1 = slot
    b.insn("ADD", "R0, R6, #0")
    b.ldr_const(2, ZONE_CID | 1)
    b.insn("BLX", "R2")                          # r0 = cid
    b.ldr_const(1, GET_ATTR | 1)
    b.insn("BLX", "R1")                          # r0 = attribute
    b.insn("MOV", "R1, #0x1")
    b.insn("LSL", "R1, R0")                      # 1 << attribute
    b.insn("LDR", "R2, [R7, #0x0]")
    b.insn("ORR", "R2, R1")
    b.insn("STR", "R2, [R7, #0x0]")
    b.insn("ADD", "R5, R5, #0x1")
    b.insn("B", "loop")
    b.label("tail")
    b.insn("POP", "{R0, R1, R4, R5, R6, R7}")
    b.insn("POP", "{R2}")                        # the saved LR
    b.insn("MOV", "LR, R2")
    b.ldr_const(2, tail | 1)
    b.insn("BX", "R2")
    return b.assemble(base, pad="nop")


def sel3_stub(base: int, flag: int, lock: int, count: int = 3) -> bytes:
    """Two passes: the first learns the offset of label `cont`, the second loads base+off as the selector frame's return address."""
    first = _sel3(base, flag, lock, count, base)
    off = first[1]["cont"]
    return _sel3(base, flag, lock, count, base + off)[0]


def _sel3(base: int, flag: int, lock: int, count: int, cont_addr: int):
    """Mobius cls1 +14.  Same as sel_stub but the selector body RETURNS here (the frame's saved LR is the continuation), so when it reports 'selection done' (r0 != 0)
    and the Tribute was WATER (latch bit 3), the targets' (side, zone) bits are latched into the E2 lock {mask, phase, turn player, controller}."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, LR}")                   # the engine's caller context
    b.ldr_const(3, cont_addr | 1)                # the selector frame returns to `cont`
    b.insn("MOV", "LR, R3")
    b.insn("PUSH", "{R1, R2, R3, R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0")
    b.insn("MOV", "R1, #0x0")
    b.insn("STR", "R1, [SP, #0x0]")
    b.insn("MOV", "R6, #" + hex(count))
    b.insn("MOV", "R7, #0x8D")
    b.insn("MOV", "R0, #0x21")
    b.ldr_const(3, SEL_MID | 1)
    b.insn("BX", "R3")
    b.label("cont")                              # r0 = the selector's result, r4 = desc
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "out")
    b.insn("PUSH", "{R0, R5, R6, R7}")
    b.ldr_const(0, flag)
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSR", f"R0, R0, #{WATER}")
    b.insn("MOV", "R1, #0x1")
    b.insn("TST", "R0, R1")
    b.insn("BEQ", "done")
    b.insn("MOV", "R5, #0x0")
    b.insn("MOV", "R6, #0x0")
    b.insn("SUB", "SP, #0x8")
    b.label("loop")
    b.insn("LDRB", "R0, [R4, #0x10]")
    b.insn("CMP", "R5, R0")
    b.insn("BGE", "fin")
    b.insn("ADD", "R0, R4, #0")
    b.insn("ADD", "R1, R5, #0")
    b.insn("ADD", "R2, SP, #0")
    b.ldr_const(3, TARGET_AT | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "next")
    b.insn("LDR", "R1, [SP, #0x0]")
    b.insn("LSL", "R2, R1, #0x18")
    b.insn("LSR", "R2, R2, #0x18")               # side
    b.insn("LSL", "R1, R1, #0x10")
    b.insn("LSR", "R1, R1, #0x18")               # zone
    b.insn("LSL", "R2, R2, #4")
    b.insn("ADD", "R2, R2, R1")
    b.insn("MOV", "R0, #0x1")
    b.insn("LSL", "R0, R2")
    b.insn("ORR", "R6, R0")
    b.label("next")
    b.insn("ADD", "R5, R5, #0x1")
    b.insn("B", "loop")
    b.label("fin")
    b.insn("ADD", "SP, #0x8")
    b.ldr_const(0, lock)
    b.insn("STR", "R6, [R0, #0x0]")
    b.ldr_const(1, PHASEBASE)
    b.insn("LDR", "R2, [R1, #0x48]")
    b.insn("STR", "R2, [R0, #0x4]")
    b.insn("LDR", "R2, [R1, #0x34]")
    b.insn("STR", "R2, [R0, #0x8]")
    b.insn("LDRB", "R2, [R4, #0x2]")
    b.insn("LDRB", "R1, [R4, #0x6]")
    b.insn("EOR", "R2, R1")
    b.insn("MOV", "R1, #0x1")
    b.insn("AND", "R2, R1")
    b.insn("STR", "R2, [R0, #0xC]")
    b.label("done")
    b.insn("POP", "{R0, R5, R6, R7}")
    b.label("out")
    b.insn("POP", "{R4, PC}")
    return b.assemble(base, pad="nop"), b._layout()[1]


def resm_stub(base: int, lock: int) -> bytes:
    """Mobius cls1 +04: the native up-to-N destroy, then the E2 lock is cleared (the response window is over)."""
    b = EffectBuilder()
    b.insn("PUSH", "{LR}")
    b.ldr_const(1, DESTROY_NATIVE_FULL | 1)
    b.insn("BLX", "R1")
    b.ldr_const(1, lock)
    b.insn("MOV", "R2, #0x0")
    b.insn("STR", "R2, [R1, #0x0]")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{PC}")
    return b.assemble(base, pad="nop")


def lkf_stub(base: int, lock: int, tail: int) -> bytes:
    """Front over each `bl <activation-prohibited predicate chain head>`: r0 = desc.  Prior verdict (the chain's `tail`) || E2 lock: live (same phase and turn player),
    activating player != the Mobius controller, the card sits in an S/T zone 5..10 whose bit is in the latched mask.  Returns 1 = prohibited."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, LR}")
    b.insn("ADD", "R4, R0, #0")
    b.ldr_const(1, tail | 1)
    b.insn("BLX", "R1")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "out")
    b.ldr_const(1, lock)
    b.insn("LDR", "R2, [R1, #0x0]")
    b.insn("CMP", "R2, #0x0")
    b.insn("BEQ", "zero")
    b.ldr_const(0, PHASEBASE)
    b.insn("LDR", "R2, [R0, #0x48]")
    b.insn("LDR", "R3, [R1, #0x4]")
    b.insn("CMP", "R2, R3")
    b.insn("BNE", "zero")
    b.insn("LDR", "R2, [R0, #0x34]")
    b.insn("LDR", "R3, [R1, #0x8]")
    b.insn("CMP", "R2, R3")
    b.insn("BNE", "zero")
    b.insn("LDRB", "R0, [R4, #0x2]")
    b.insn("LDRB", "R2, [R4, #0x6]")
    b.insn("EOR", "R0, R2")
    b.insn("MOV", "R2, #0x1")
    b.insn("AND", "R0, R2")
    b.insn("LDR", "R3, [R1, #0xC]")
    b.insn("CMP", "R0, R3")
    b.insn("BEQ", "zero")
    b.insn("LDRB", "R0, [R4, #0x3]")             # the card's zone
    b.insn("CMP", "R0, #0x5")
    b.insn("BLT", "zero")
    b.insn("CMP", "R0, #0xA")
    b.insn("BGT", "zero")
    b.insn("LDRB", "R2, [R4, #0x2]")
    b.insn("MOV", "R3, #0x1")
    b.insn("AND", "R2, R3")
    b.insn("LSL", "R2, R2, #4")
    b.insn("ADD", "R0, R0, R2")
    b.insn("MOV", "R2, #0x1")
    b.insn("LSL", "R2, R0")
    b.insn("LDR", "R3, [R1, #0x0]")
    b.insn("TST", "R3, R2")
    b.insn("BEQ", "zero")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, PC}")
    b.label("zero")
    b.insn("MOV", "R0, #0x0")
    b.label("out")
    b.insn("POP", "{R4, PC}")
    return b.assemble(base, pad="nop")



def _fit_rest() -> bytes:
    from pathlib import Path
    from otn_enhanced.asm.cc import compile_c
    blob = compile_c(Path(__file__).resolve().parent / "c" / "thestalos.c", O5.CAVE_MM_REST, {"FLAG": f"0x{O5.CAVE_MM_FLAG:08X}"})
    assert len(blob) <= RESERVES["REST"], f"REST stub {len(blob):#x} B > {RESERVES['REST']:#x}"
    return blob


@dataclass(frozen=True)
class mega_set:
    """The Mega Monarchs built so far (see the module docstring). `cid` = the first card, for dsl.make."""
    cid: int = GRANMARG

    def blobs(self):
        return {
            "M0": (O5.CAVE_MM_M0, m0_stub(O5.CAVE_MM_M0, MEGAS + (EREBUS, EHTHER)), "M0 alternate Tribute front"),
            "TRIG": (O5.CAVE_MM_TRIG, MR.trig_stub(O5.CAVE_MM_TRIG, TRIGGERS + (EREBUS, EHTHER), LIST_SEARCH), "Tribute Summon trigger front"),
            "SEL": (O5.CAVE_MM_SEL, sel_stub(O5.CAVE_MM_SEL, 2), "Granmarg cls1 +14 up-to-2 selector"),
            "SEL3": (O5.CAVE_MM_SEL3, sel3_stub(O5.CAVE_MM_SEL3, O5.CAVE_MM_FLAG, O5.CAVE_MM_LOCK), "Mobius cls1 +14 up-to-3 selector + E2 lock latch"),
            "RESM": (O5.CAVE_MM_RESM, resm_stub(O5.CAVE_MM_RESM, O5.CAVE_MM_LOCK), "Mobius cls1 +04 destroy + clear the E2 lock"),
            "LKF": (O5.CAVE_MM_LKF, lkf_stub(O5.CAVE_MM_LKF, O5.CAVE_MM_LOCK, LOCK_TAIL), "E2 lock front on the activation-prohibited predicate"),
            "RESZ": (O5.CAVE_MM_RESZ, MZ.resz_stub(O5.CAVE_MM_RESZ, O5.CAVE_MM_ZST, O5.CAVE_MM_FLAG), "Zaborg cls1 +04 destroy + Extra Deck picker phases"),
            "ZROW": (O5.CAVE_MM_ZROW, MZ.row_blob(ZABORG, O5.CAVE_MM_ZH), "Zaborg virtual criteria row 0xFF50"),
            "ZH": (O5.CAVE_MM_ZH, MZ.zh_stub(O5.CAVE_MM_ZH), "Zaborg Extra Deck criteria handler"),
            "ZH2": (O5.CAVE_MM_ZH2, MZ.h2_front(O5.CAVE_MM_ZH2, ZABORG, H2_PREV), "criteria miss-tail front"),
            "ZH3": (O5.CAVE_MM_ZH3, MZ.h3_front(O5.CAVE_MM_ZH3, O5.CAVE_MM_ZROW, H3_PREV), "criteria row-compute front"),
            "RESR": (O5.CAVE_MM_RESR, MR.resr_stub(O5.CAVE_MM_RESR, O5.CAVE_MM_RRST, O5.CAVE_MM_FLAG), "Raiza cls1 +04 phase machine"),
            "RRH": (O5.CAVE_MM_RRH, MR.rh_stub(O5.CAVE_MM_RRH, O5.CAVE_MM_RRST), "Raiza criteria handler"),
            "RROW": (O5.CAVE_MM_RROW, MR.row_blob(RAIZA, O5.CAVE_MM_RRH), "Raiza virtual criteria row 0xFF51"),
            "RH2": (O5.CAVE_MM_RH2, MR.h2_front(O5.CAVE_MM_RH2, RAIZA, O5.CAVE_MM_ZH2), "Raiza criteria miss-tail front"),
            "RH3": (O5.CAVE_MM_RH3, MR.h3_front(O5.CAVE_MM_RH3, O5.CAVE_MM_RROW, O5.CAVE_MM_ZH3), "Raiza criteria row-compute front"),
            "RESC": (O5.CAVE_MM_RESC, MC.resc_stub(O5.CAVE_MM_RESC, O5.CAVE_MM_CST, O5.CAVE_MM_FLAG), "Caius cls1 +04 phase machine"),
            "CRH": (O5.CAVE_MM_CRH, MR.rh_stub(O5.CAVE_MM_CRH, O5.CAVE_MM_CST), "Caius criteria handler"),
            "CROW": (O5.CAVE_MM_CROW, MR.row_blob(CAIUS, O5.CAVE_MM_CRH), "Caius virtual criteria row 0xFF52"),
            "CH2": (O5.CAVE_MM_CH2, MR.h2_front(O5.CAVE_MM_CH2, CAIUS, O5.CAVE_MM_RH2, CAIUS_IDX), "Caius criteria miss-tail front"),
            "CH3": (O5.CAVE_MM_CH3, MR.h3_front(O5.CAVE_MM_CH3, O5.CAVE_MM_CROW, O5.CAVE_MM_RH3, CAIUS_IDX), "Caius criteria row-compute front"),
            "RES": (O5.CAVE_MM_RES, res_stub(O5.CAVE_MM_RES, O5.CAVE_MM_FLAG), "Granmarg cls1 +04 destroy + E2 draw"),
            "REST": (O5.CAVE_MM_REST, _fit_rest(), "Thestalos cls1 +04 (look at the opponent's hand, discard, Level x 200 damage, FIRE +1000)"),
            **AG.blobs(O5.CAVE_MM_CH2, O5.CAVE_MM_CH3),
            "CAP": (O5.CAVE_MM_CAP, cap_stub(O5.CAVE_MM_CAP, O5.CAVE_MM_FLAG, tail=O5.CAVE_SF_PAY if O5.combo() else TRIB_PAY), "Tribute-payment capture front"),
        }

    def records(self):  # noqa: D102
        return {
            GRANMARG: (GRANMARG, 0, O5.CAVE_MM_RES | 1, SET_FILTER, ALWAYS, 0, O5.CAVE_MM_SEL | 1),
            MOBIUS: (MOBIUS, 0, O5.CAVE_MM_RESM | 1, ST_FILTER, 0, YOU_CAN, O5.CAVE_MM_SEL3 | 1),
            ZABORG: (ZABORG, 0, O5.CAVE_MM_RESZ | 1, ZAB_FILTER, ALWAYS, 0, ZAB_SEL),
            RAIZA: (RAIZA, 0, O5.CAVE_MM_RESR | 1, 0, 0, 0, 0),
            ANGMARL: AG.cls1_record(),
            THESTALOS: (THESTALOS, 0, O5.CAVE_MM_REST | 1, 0, 0, 0, 0),     # Thestalos the Firestorm Monarch's shape: a trigger with no targeting step
            CAIUS: (CAIUS, 0, O5.CAVE_MM_RESC | 1, FIELD_ANY_FILTER, ALWAYS, 0, FIELD_ANY_SEL),   # Caius the Shadow Monarch's own targeting             # Thestalos the Firestorm Monarch's shape: a trigger with no targeting step
        }

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            assert len(blob) <= RESERVES[key], f"{key} stub is {len(blob)} B > {RESERVES[key]:#x}"
            if key not in DATA_STUBS:
                assert_thumb1_only(blob, addr)
        recs = self.records()

        def sites():
            yield HOOK, HOOK_NATIVE, common_bl(HOOK, O5.CAVE_MM_M0), "M0"
            yield TRIG_SITE, common_bl(TRIG_SITE, LIST_SEARCH), common_bl(TRIG_SITE, O5.CAVE_MM_TRIG), "trigger"
            for s in PAY_SITES:
                yield s, common_bl(s, TRIB_PAY), common_bl(s, O5.CAVE_MM_CAP), f"payment {s:#x}"
            for s in PRED_SITES:
                yield s, common_bl(s, LOCK_TAIL), common_bl(s, O5.CAVE_MM_LKF), f"E2 lock {s:#x}"
            yield H2_SITE, common_bl(H2_SITE, H2_PREV), common_bl(H2_SITE, O5.CAVE_AG_H2), "Monarch criteria miss-tail fronts (Angmarl -> Caius -> Raiza -> Zaborg -> Block Dragon)"
            yield H3_SITE, common_bl(H3_SITE, H3_PREV), common_bl(H3_SITE, O5.CAVE_AG_H3), "Monarch criteria row-compute fronts (Angmarl -> Caius -> Raiza -> Zaborg -> Block Dragon)"

        def install(rom, v):
            # dsl.make's verify compares every Row against the FIRST card's cid, so only Granmarg's cls1 row goes through `rows`; the others insert here.
            for cid in MEGAS[1:] + (ANGMARL,):
                insert_sorted(v, CLS1, recs[cid], drop=CLS1_PHANTOMS[cid])
            for site, native, want, what in sites():
                cur = v.blob(site, 4)
                if cur == want:
                    continue
                assert cur == native, f"{what} site 0x{site:08X} is {cur.hex()}, expected the native {native.hex()}: another patch owns it"
                v.write(site, want)

        def check(c, rom, v):
            for site, native, want, what in sites():
                c.ok(code_reaches(rom, site, O5.bl_dst(want, 0, site)), f"hook installed: {what} @0x{site:08X} (reached, later fronts may sit ahead)")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present in the ov5 cave @0x{addr:08X} ({len(blob)} B)")
            allrows = rows(v, CLS1)
            for cid, rec in recs.items():
                c.ok([r for r in allrows if r[0] == cid] == [rec], f"cls1 record under 0x{cid:04X}: {[hex(x) for x in rec]}")
            ks = [r[0] for r in allrows]
            c.ok(all(p not in ks for p in CLS1_PHANTOMS.values()) and ks == sorted(ks) and len(ks) == CLS1.count,
                 f"cls1 phantoms {[hex(p) for p in CLS1_PHANTOMS.values()]} spent, table sorted and count-neutral")
            for cid in TRIGGERS:
                ok_text, msg = card_text.check_rom_text(c.out, cid)
                c.ok(ok_text, f"text 0x{cid:04X}: {msg}")

        return Compiled(stubs=tuple(blobs.values()),
                        rows=(Row(CLS1, recs[GRANMARG], CLS1_PHANTOMS[GRANMARG]),),
                        installs=(install,), checks=(check,))


SPEC = mega_set(GRANMARG)
PROPS = {
    GRANMARG: card_props("EARTH", "Rock", level=8, atk=2800, defense=1000, card_type="Effect Monster"),
    MOBIUS: card_props("WATER", "Aqua", level=8, atk=2800, defense=1000, card_type="Effect Monster"),
    ZABORG: card_props("LIGHT", "Thunder", level=8, atk=2800, defense=1000, card_type="Effect Monster"),
    RAIZA: card_props("WIND", "Winged Beast", level=8, atk=2800, defense=1000, card_type="Effect Monster"),
    CAIUS: card_props("DARK", "Fiend", level=8, atk=2800, defense=1000, card_type="Effect Monster"),
    THESTALOS: card_props("FIRE", "Pyro", level=8, atk=2800, defense=1000, card_type="Effect Monster"),
    ANGMARL: card_props("DARK", "Fiend", level=6, atk=2400, defense=1000, card_type="Effect Monster"),
}

_main, verify = dsl.make(SPEC, PROPS[GRANMARG], out=OUT)


def main(write_text: bool = False, src: str = dsl.SRC, out: str = OUT) -> None:
    """dsl.make's main does the shared stubs, both cls1 rows and the FIRST card's stats/text; the other cards' stats/text are applied after."""
    _main(write_text=write_text, src=src, out=out)
    for cid in MEGAS[1:] + (ANGMARL,):
        p = PROPS[cid]
        name, desc = (s.encode("ascii", "replace") for s in card_text.CARD_TEXT[cid]["e"])
        apply_stats_and_text(out, cid=cid, attribute=p.attribute, race=p.race, level=p.level, atk=p.atk, defense=p.defense,
                             card_type=ERA2_CARD_TYPE_REVERSE[p.card_type], name=name, desc=desc, langs=TEXT_LANGS, write_text=write_text)


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
