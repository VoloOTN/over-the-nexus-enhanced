"""Immortal Phoenix Gearfried (0x0FC7, donor Judge Man), whole card.

SINGLE-CARD TEST ROM ONLY (user rule): layered on the chain ROM (which carries Disguise, Medraut, Tyranno, Dragon Rulers ...); NOT in
steps.STEPS / SHIPPED. Design, proofs, rulings: notes/immortal-phoenix-gearfried-findings.md.

  C1  "You can banish 1 Equip Spell from your field or GY; Special Summon this card from your hand."
        VIRTUAL cls2 hand record (find_event_handler miss-tail front 0x0224A86A, AHEAD of Dragon Rulers' H1): no cls2 phantom is left.
        COND / RES = Disguise C1 shape (C); COST = Ojamassimilation / Sacred Sword's banish machine (asm): picker over a VIRTUAL
        criteria row 0xFF20 (GY builder + own face-up S/T 5..9), mover split GY / field. Hand offer = ARM9 H4 front.
  C2  "At the start of the Damage Step, if this card attacks: You can equip 1 face-up monster on the field to this card (max. 1)
        as an Equip Spell that gives this card 500 ATK."   cls1 over a phantom, the start-of-Damage-Step poster front AHEAD of
        Tyranno's, Allure's equip resolver 0x0220BFFD, +500 via a stat front on 0x021B7088.
  C3  "When a monster effect is activated (Quick Effect): You can send 1 face-up Equip Card you control to the GY; negate the
        activation, and if you do, destroy it."   cls3 over a phantom + speed-2 list swap + Damage-Step offer list 0x0226D8B0.
  Each effect is once per turn (separate keys, user 2026-11-04).

    uv run python _build_immortal_phoenix_gearfried.py
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R3, R4, R5, R6, R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS1, CLS3, Compiled, Row, card, card_props, archetype_member, SetCodeTable
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target, list_insert

GF = 0x0FC7
C_DIR = Path(__file__).resolve().parent / "c"
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_immortal_phoenix_gearfried.nds"

KEY_GF1, KEY_GF3, KEY_GF2 = 0x5FC7, 0x6FC7, 0x7FC7
IDX = 0xFF20                                    # virtual criteria index (Disguise 0xFF00|j, Medraut 0xFF10)

# --- natives (Thumb, odd) ----------------------------------------------------------------------------------------
SHORTCIRCUIT, MESSAGE, PICKER, READBACK = 0x021D2BC9, 0x0219A819, 0x0219C431, 0x0219C511
CHAIN_PUSH, CHAIN_POP = 0x021D28A5, 0x021D2965
GY_INDEX, GY_BANISH, ON_FIELD, FIELD_BANISH = 0x021A2511, 0x021C7105, 0x021A241D, 0x021CF40D
GY_BUILDER, RECORD = 0x0223C4E9, 0x02243B2D
GET_SPELLTYPE, GET_RACE, IS_MONSTER = 0x0202ABE9, 0x0202ABB9, 0x02029E61
CARD_CID_AT, ZONE_PRED = 0x021A36ED, 0x021D6E41
IS_NEGATED, MONSTER_ACT, FIELD_COUNT, OFFER_GATE = 0x021AB90D, 0x021D2AD9, 0x0224AA95, 0x021F06E9
ALLURE_RES, TSEL_ALLURE, YOU_CAN = 0x0220BFFD, 0x02234D99, 0x021E51E5
NEGATE_RES = 0x022062F9
RES_STATE, FIELD = 0x0229AAFC, 0x0229ACC8
H3_RESUME = 0x02243F71
MSG_BANISH = 0x46
DMG_LIT, DMG_HIT, TYRANNO_M = 0x0224F730, 0x0224F668, 0x021F065D
for _v in (SHORTCIRCUIT, MESSAGE, PICKER, READBACK, CHAIN_PUSH, CHAIN_POP, GY_INDEX, GY_BANISH, ON_FIELD, FIELD_BANISH, GY_BUILDER,
           RECORD, GET_SPELLTYPE, GET_RACE, IS_MONSTER, CARD_CID_AT, ZONE_PRED, IS_NEGATED, MONSTER_ACT, FIELD_COUNT, OFFER_GATE,
           ALLURE_RES, TSEL_ALLURE, YOU_CAN, NEGATE_RES, H3_RESUME, TYRANNO_M):
    assert _v & 1, f"{_v:#x}: blx/bx to an even literal switches to ARM state -> freeze"

# --- shared sites and the owner each must hold BEFORE us (chain ROM 2026-11-04) ----------------------------------------
H1_SITE, H1_PREV = 0x0224A86A, 0x021F1008                    # find_event_handler miss tail -> Dragon Rulers' H1 (cave3)
H2_SITE, H2_PREV = 0x02243F24, O5.CAVE_MK_H2                 # Medraut's front
H3_SITE, H3_PREV = 0x02243F62, O5.CAVE_MK_H3
H4_SITE, H4_PREV = 0x02023566, O5.CAVE_DC_H4                 # ARM9, Disguise's front
STAT_SITE, STAT_PREV = 0x021B7088, O5.CAVE_DC_N1_FRONT       # Disguise's N1 front (-> Captain Oliver's)

S = {n: getattr(O5, f"CAVE_GF_{n}") for n in (
    "ROWS", "C1_COND", "C1_RES", "C1_COST", "C1_H", "C1_PRED", "C1_S5", "VREC", "H1", "H2", "H3", "H4", "C2_FILT", "C2_COND",
    "C2_RES", "STAT", "DMG", "C3_FILT", "C3_COND", "C3_COST")}
RESERVE = {"ROWS": 0x20, "C1_COND": 0xD0, "C1_RES": 0x40, "C1_COST": 0xC0, "C1_H": 0x80, "C1_PRED": 0x50, "C1_S5": 0x10, "VREC": 0x30, "H1": 0x30, "H2": 0x20, "H3": 0x30, "H4": 0x20, "C2_FILT": 0x30, "C2_COND": 0x90, "C2_RES": 0x50, "STAT": 0x40, "DMG": 0x20, "C3_FILT": 0x50, "C3_COND": 0x70, "C3_COST": 0x40}

# --- table records ---------------------------------------------------------------------------------------------------
C1_REC = (GF, 0, S["C1_RES"] | 1, 0, S["C1_COND"] | 1, S["C1_COST"] | 1, S["C1_S5"] | 1)       # virtual cls2 (24 B, "<HHIIIII")
C2_REC = (GF, 0, S["C2_RES"] | 1, S["C2_FILT"] | 1, S["C2_COND"] | 1, YOU_CAN, TSEL_ALLURE)   # cls1 over a phantom
C3_REC = (GF, NEGATE_RES, S["C3_FILT"] | 1, S["C3_COND"] | 1, S["C3_COST"] | 1, 0)             # cls3 ("<IIIIII") over a phantom
C2_PHANTOM, C3_PHANTOM = 0x0E39, 0x0E47
SPEED2_PHANTOM = 0x0EB2
DS_LIST, DS_COUNT, DS_PHANTOM = 0x0226D8B0, 0x30, 0x0E5B
ROW = (GF, 0xFFFF, S["C1_H"] | 1, 0x00000002)                     # virtual criteria row {cid, aux, handler, word}
ROWS_BLOB = struct.pack("<HHII", *ROW) + bytes(0x14)
VREC_BLOB = struct.pack("<HHIIIII", *C1_REC) + bytes(0x18)
SPEED2_TABLE = SetCodeTable("spell-speed-2", 0x0209C118, 0x76, (0x020234A4,), (0x02023490,))


def _c(stub: str, slot: str) -> bytes:
    blob = compile_c(C_DIR / "gearfried.c", S[slot], {"STUB": stub})
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    return blob


def _asm(b: EffectBuilder, slot: str) -> bytes:
    blob = b.assemble(S[slot], pad="nop")
    assert_thumb1_only(blob, S[slot])
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    return blob


# --- C1: banish machine ------------------------------------------------------------------------------------------------
def c1_pred() -> bytes:
    """C1_PRED slot = [+0] is_equip_spell(cid) (r0 = cid -> 1/0), [+0x30] the GY-builder callback ([sp] = &card word at entry)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.ldr_const(3, GET_SPELLTYPE)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x3")
    b.insn("BNE", "no")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, GET_RACE)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x17")
    b.insn("BNE", "no")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, PC}")
    fn = b.assemble(S["C1_PRED"], pad="nop")
    fn += b"\x00\xbf" * ((0x30 - len(fn)) // 2)
    assert len(fn) == 0x30, f"is_equip_spell is {len(fn):#x} B, must fit 0x30"
    cb = EffectBuilder()
    cb.insn("PUSH", "{R3, LR}")
    cb.insn("LDR", "R0, [SP, #0x8]")
    cb.insn("LDR", "R0, [R0, #0x0]")
    cb.insn("LSL", "R0, R0, #0x12")
    cb.insn("LSR", "R0, R0, #0x12")
    cb.ldr_const(3, S["C1_PRED"] | 1)
    cb.insn("BLX", "R3")
    cb.insn("POP", "{R3, PC}")
    blob = fn + cb.assemble(S["C1_PRED"] + 0x30, pad="nop")
    assert_thumb1_only(blob, S["C1_PRED"])
    assert len(blob) <= RESERVE["C1_PRED"], f"C1_PRED {len(blob):#x} B"
    return blob


def c1_handler() -> bytes:
    """virtual criteria handler (r0 = &row, r1 = side, r2 = param; Ojamassimilation's banish branch): GY builder with the Equip Spell
    predicate (flags 0x10000), then own face-up S/T zones 5..9 holding an Equip Spell -> recorder."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("SUB", "SP, #0x8")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("ADD", "R4, R1, #0x0")
    b.insn("MOV", "R0, #0x2")
    b.insn("STR", "R0, [SP, #0x0]")
    b.ldr_const(0, 0x10000)
    b.insn("STR", "R0, [SP, #0x4]")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("LDRH", "R1, [R5, #0x0]")
    b.ldr_const(2, (S["C1_PRED"] + 0x30) | 1)
    b.insn("MOV", "R3, #0x0")
    b.ldr_const(6, GY_BUILDER)
    b.insn("BLX", "R6")
    b.ldr_const(7, FIELD)
    b.insn("MOV", "R0, #0x1")
    b.insn("AND", "R0, R4")
    b.insn("BEQ", "p0")
    b.ldr_const(0, 0xB3C)
    b.insn("ADD", "R7, R7, R0")
    b.label("p0")
    b.insn("ADD", "R7, #0x64")                 # zone 5
    b.insn("MOV", "R6, #0x5")
    b.label("lp")
    b.insn("CMP", "R6, #0xA")
    b.insn("BGE", "out")
    b.insn("LDRH", "R0, [R7, #0x0]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "nx")
    b.insn("LDRH", "R0, [R7, #0x8]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "nx")
    b.insn("LDR", "R0, [R7, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.ldr_const(3, S["C1_PRED"] | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "nx")
    b.call_addr(RECORD, R4, R6, 0, via=R3)
    b.label("nx")
    b.insn("ADD", "R7, #0x14")
    b.insn("ADD", "R6, #0x1")
    b.insn("B", "lp")
    b.label("out")
    b.insn("ADD", "SP, #0x8")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return _asm(b, "C1_H")


def c1_cost() -> bytes:
    """cls2 +10 (Sacred Sword / Ojamassimilation cost protocol on [RES_STATE+0x7C]: 0 prompt | 1 picker | else banish the pick, return 1)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.ldr_const(3, SHORTCIRCUIT)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "done")
    b.insn("LDRB", "R5, [R4, #0x2]")
    b.ldr_const(6, RES_STATE)
    b.insn("LDR", "R0, [R6, #0x7C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "ph0")
    b.insn("CMP", "R0, #0x1")
    b.insn("BEQ", "ph1")
    b.ldr_const(3, READBACK)
    b.insn("BLX", "R3")
    b.insn("ADD", "R7, R0, #0x0")              # r7 = &pick
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R1, R0, #0x11")
    b.insn("LSR", "R1, R1, #0x1F")             # side bit
    b.insn("LSL", "R0, R0, #0x1")
    b.insn("LSR", "R0, R0, #0x18")
    b.insn("LSL", "R0, R0, #0x1")
    b.insn("ADD", "R6, R1, R0")                # r6 = key (side bit + 2 * zone byte)
    b.ldr_const(3, CHAIN_PUSH)
    b.insn("BLX", "R3")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("ADD", "R1, R6, #0x0")
    b.ldr_const(3, GY_INDEX)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BLT", "field")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("ADD", "R1, R7, #0x0")
    b.insn("MOV", "R2, #0x0")
    b.ldr_const(3, GY_BANISH)
    b.insn("BLX", "R3")
    b.insn("B", "pop")
    b.label("field")
    b.insn("ADD", "R0, R6, #0x0")
    b.ldr_const(3, ON_FIELD)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BLT", "pop")
    b.insn("LSL", "R1, R0, #0x10")
    b.insn("LSR", "R1, R1, #0x18")
    b.insn("LSL", "R0, R0, #0x18")
    b.insn("LSR", "R0, R0, #0x18")
    b.insn("MOV", "R2, #0x0")
    b.ldr_const(3, FIELD_BANISH)
    b.insn("BLX", "R3")
    b.label("pop")
    b.ldr_const(3, CHAIN_POP)
    b.insn("BLX", "R3")
    b.label("done")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    b.label("ph0")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", f"R1, #0x{MSG_BANISH:X}")
    b.ldr_const(3, MESSAGE)
    b.insn("BLX", "R3")
    b.insn("B", "next")
    b.label("ph1")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("MOV", "R1, #0x6")
    b.insn("LDRH", "R2, [R4, #0x0]")
    b.insn("MOV", "R3, #0x0")
    b.ldr_const(7, PICKER)
    b.insn("BLX", "R7")
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


# --- fronts ----------------------------------------------------------------------------------------------------------
def h1_front() -> bytes:
    """find_event_handler miss tail (r4 = desc, [sp] = key cid, frame = push {r1-r7,lr}): Gearfried's HAND cls2 lookup
    (desc[+5] == 2, [+3] == 0xB, [+4] == 0) -> r0 = &virtual record and pop the frame; everything else tails to Dragon Rulers' H1."""
    b = EffectBuilder()
    b.insn("LDR", "R0, [SP, #0x0]")
    b.ldr_const(1, GF)
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "prev")
    b.insn("LDRB", "R1, [R4, #0x5]")
    b.insn("CMP", "R1, #0x2")
    b.insn("BNE", "prev")
    b.insn("LDRB", "R1, [R4, #0x3]")
    b.insn("CMP", "R1, #0xB")
    b.insn("BNE", "prev")
    b.insn("LDRB", "R1, [R4, #0x4]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BNE", "prev")
    b.ldr_const(0, S["VREC"])
    b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
    b.label("prev")
    b.ldr_const(3, H1_PREV | 1)
    b.insn("BX", "R3")
    return _asm(b, "H1")


def h2_front() -> bytes:
    """criteria resolver miss tail (r5 = cid): Gearfried -> index 0xFF20 and pop the caller's frame, else onward to Medraut's front."""
    b = EffectBuilder()
    b.ldr_const(0, GF)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, IDX)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _asm(b, "H2")


def h3_front() -> bytes:
    """invoker row compute (r6 = index): 0xFF20 -> r0 = CAVE_GF_ROWS, r3 = [r0+4], resume 0x02243F70; else tail to Medraut's H3."""
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
    """ARM9 0x02023566 BL (r0 = cid): Gearfried -> 1 (hand effect offered), else Disguise's front."""
    b = EffectBuilder()
    b.ldr_const(3, GF)
    b.insn("CMP", "R0, R3")
    b.insn("BNE", "prev")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.label("prev")
    b.ldr_const(3, H4_PREV | 1)
    b.insn("BX", "R3")
    return _asm(b, "H4")


def stat_front() -> bytes:
    """BL over `ldr r1,=0x0226DFB0 ; adds r0,r5,#0` @0x021B7088 (recompute 0x021B44C0; r5 = equip card cid; [sp+0xC]/[sp+0x10] holder
    side / zone, [sp+0xB0] ATK accumulator): holder 0x0FC7 and the equip card a MONSTER (race < 23) -> +500. Then tail to Disguise's front."""
    b = EffectBuilder()
    b.insn("PUSH", "{R2, R3, R4, R6, R7, LR}")
    b.insn("LDR", "R0, [SP, #0x24]")
    b.insn("LDR", "R1, [SP, #0x28]")
    b.call_addr(CARD_CID_AT, via=R3)
    b.ldr_const(1, GF)
    b.insn("CMP", "R0, R1")
    b.insn("BNE", "done")
    b.insn("ADD", "R0, R5, #0x0")
    b.ldr_const(3, GET_RACE)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x17")
    b.insn("BGE", "done")
    b.insn("LDR", "R0, [SP, #0xC8]")
    b.insn("MOV", "R1, #0x7D")
    b.insn("LSL", "R1, R1, #0x2")
    b.insn("ADD", "R0, R0, R1")
    b.insn("STR", "R0, [SP, #0xC8]")
    b.label("done")
    b.insn("POP", "{R2, R3, R4, R6, R7}")
    b.insn("POP", "{R0}")
    b.insn("MOV", "LR, R0")
    b.ldr_const(0, STAT_PREV | 1)
    b.insn("BX", "R0")
    return _asm(b, "STAT")


def dmg_front(prev: int) -> bytes:
    """start-of-Damage-Step poster root (entered by `bx r3` from 0x0224F58A with r4 = attacker cid; clobbers r0/r3 only):
    Gearfried -> the hit leaf; everyone else -> the previous owner (Tyranno's M stub, which replays the root)."""
    b = EffectBuilder()
    b.ldr_const(3, GF)
    b.insn("CMP", "R4, R3")
    b.insn("BNE", "prev")
    b.ldr_const(0, DMG_HIT | 1)
    b.insn("BX", "R0")
    b.label("prev")
    b.ldr_const(0, prev)
    b.insn("BX", "R0")
    return _asm(b, "DMG")


# --- C2 ---------------------------------------------------------------------------------------------------------------
def c2_res() -> bytes:
    """cls1 +04: phase 0x80 re-checks + stamps the OPT, then Allure's equip resolver (target declared at activation, user-approved)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.ldr_const(6, RES_STATE)
    b.insn("LDR", "R0, [R6, #0x70]")
    b.insn("CMP", "R0, #0x80")
    b.insn("BNE", "allure")
    b.insn("LDRB", "R0, [R4, #0x2]")
    b.turnlog_query(R0, KEY_GF2, 1, via=R6)
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "zero")
    b.insn("LDRB", "R0, [R4, #0x2]")
    b.turnlog_post(R0, KEY_GF2, 1, via=R6)
    b.label("allure")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("ADD", "R1, R5, #0x0")
    b.ldr_const(3, ALLURE_RES)
    b.insn("BLX", "R3")
    b.insn("POP", "{R4, R5, R6, PC}")
    b.label("zero")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, PC}")
    return _asm(b, "C2_RES")


# --- C3 ---------------------------------------------------------------------------------------------------------------
def c3_filt() -> bytes:
    """cls3 +08 (desc, side, zone), the native field cost's candidate filter: your face-up card in S/T 5..9 that is an Equip Spell,
    or a monster (only an equipped monster can sit there)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R5, R1, #0x0")
    b.insn("ADD", "R6, R2, #0x0")
    b.call_addr(ZONE_PRED, R0, R1, R2, 5, via=R7)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "no")
    b.insn("CMP", "R6, #0x5")
    b.insn("BLT", "no")
    b.insn("CMP", "R6, #0x9")
    b.insn("BGT", "no")
    b.call_addr(CARD_CID_AT, R5, R6, via=R7)
    b.insn("ADD", "R4, R0, #0x0")
    b.ldr_const(3, IS_MONSTER)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "yes")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, S["C1_PRED"] | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "no")
    b.label("yes")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return _asm(b, "C3_FILT")


def c3_cond() -> bytes:
    """cls3 +0C (r0 = my desc, r1 = the activation's desc): Qoatlus' / Wall's pre-checks with the monster-effect test 0x021D2AD8 in place of
    the Spell/Trap test (Divine Wrath's precondition), no opponent-side requirement, this copy's OPT at menu time, an Equip Card to send,
    then the generic offer gate."""
    b = EffectBuilder()
    b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("ADD", "R4, R1, #0x0")
    b.insn("BEQ", "ret0")
    b.insn("LDRB", "R0, [R4, #0x3]")
    b.insn("CMP", "R0, #0xD")
    b.insn("BEQ", "ret0")
    b.call_addr(IS_NEGATED, R4, 1, via=R7)
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "ret0")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, MONSTER_ACT)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "ret0")
    b.insn("LDRB", "R0, [R5, #0x7]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "have")
    b.insn("LDRB", "R0, [R5, #0x2]")
    b.turnlog_query(R0, KEY_GF3, 1, via=R7)
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "ret0")
    b.label("have")
    b.call_addr(FIELD_COUNT, R5, via=R7)
    b.insn("CMP", "R0, #0x0")
    b.insn("BLE", "ret0")
    b.call_addr(OFFER_GATE, R5, R4, via=R7)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("ret0")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    return _asm(b, "C3_COND")


def _bl_pair(src: int, dst: int) -> bytes:
    return common_bl(src, dst)


@dataclass(frozen=True)
class gearfried_whole_card:
    def compile(self, view, cid) -> Compiled:
        assert cid == GF

        def built(prev_dmg: int) -> tuple:
            return (
                (S["ROWS"], ROWS_BLOB, "virtual criteria row 0xFF20"),
                (S["VREC"], VREC_BLOB, "virtual cls2 hand record"),
                (S["C1_COND"], _c("C1COND", "C1_COND"), "C1 +0C hand cond"),
                (S["C1_RES"], _c("C1RES", "C1_RES"), "C1 +04 hand SS"),
                (S["C1_COST"], c1_cost(), "C1 +10 banish cost"),
                (S["C1_H"], c1_handler(), "C1 criteria handler"),
                (S["C1_PRED"], c1_pred(), "Equip Spell predicate + GY builder callback"),
                (S["C1_S5"], c1_s5(), "C1 +14"),
                (S["H1"], h1_front(), "find_event_handler front"),
                (S["H2"], h2_front(), "H2 front"),
                (S["H3"], h3_front(), "H3 front"),
                (S["H4"], h4_front(), "ARM9 H4 front"),
                (S["C2_FILT"], _c("C2FILT", "C2_FILT"), "C2 +08"),
                (S["C2_COND"], _c("C2COND", "C2_COND"), "C2 +0C"),
                (S["C2_RES"], c2_res(), "C2 +04"),
                (S["STAT"], stat_front(), "stat front (+500)"),
                (S["DMG"], dmg_front(prev_dmg), "Damage-Step poster front"),
                (S["C3_FILT"], c3_filt(), "C3 +08"),
                (S["C3_COND"], c3_cond(), "C3 +0C"),
                (S["C3_COST"], _c("C3COST", "C3_COST"), "C3 +10"))

        cur_lit = struct.unpack("<I", view.blob(DMG_LIT, 4))[0]
        prev_dmg = TYRANNO_M
        assert cur_lit in (TYRANNO_M, S["DMG"] | 1), f"poster literal @{DMG_LIT:#x} = {cur_lit:#x}, expected Tyranno's {TYRANNO_M:#x}"
        stubs = built(prev_dmg)
        rows = (Row(CLS1, C2_REC, C2_PHANTOM), Row(CLS3, C3_REC, C3_PHANTOM))

        def _front(view, site, prev, mine, what):
            cur = ov3_bl_target(view.buf, site)
            assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
            view.write(site, common_bl(site, mine))

        def install(rom, view):
            _front(view, H1_SITE, H1_PREV, S["H1"], "find_event_handler miss tail")
            _front(view, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front(view, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            _front(view, STAT_SITE, STAT_PREV, S["STAT"], "equip stat site")
            view.pack(DMG_LIT, "<I", S["DMG"] | 1)
            list_insert(view.buf, DS_LIST, DS_COUNT, GF, DS_PHANTOM, "Damage-Step offer list")
            mc, sec = O5._arm9_main(rom)
            d = bytearray(sec.data)
            a = H4_SITE - 0x02000000
            assert bytes(d[a:a + 4]) in (common_bl(H4_SITE, H4_PREV), common_bl(H4_SITE, S["H4"])), \
                f"ARM9 H4 site {H4_SITE:#x} is not Disguise's front"
            d[a:a + 4] = common_bl(H4_SITE, S["H4"])
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def check(c, rom, view):
            for site, slot in ((H1_SITE, "H1"), (H2_SITE, "H2"), (H3_SITE, "H3"), (STAT_SITE, "STAT")):
                t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()          # later owners' fronts (predaplant) may sit ahead of ours
                while t != S[slot] and t in nxt:
                    t = nxt[t]
                c.eq(t, S[slot], f"bl @{site:#x} -> {slot}")
            c.eq(struct.unpack("<I", view.blob(DMG_LIT, 4))[0], S["DMG"] | 1, "poster literal -> DMG front")
            lst = [struct.unpack("<H", view.blob(DS_LIST + 2 * i, 2))[0] for i in range(DS_COUNT)]
            c.ok(GF in lst and DS_PHANTOM not in lst and lst == sorted(lst) and len(set(lst)) == DS_COUNT,
                 "Damage-Step offer list: Gearfried in, phantom out, sorted")
            mc, sec = O5._arm9_main(rom)
            a = H4_SITE - 0x02000000
            c.ok(bytes(sec.data[a:a + 4]) in {common_bl(H4_SITE, f) for f in O5.dc_ahead_of(S["H4"])}, "ARM9 bl @0x02023566 -> H4 front (or a later owner's front ahead of it)")
            for label, addr, blob, _ in ((l, ad, bl, 0) for ad, bl, l in stubs):
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{label} installed @{addr:#x}")

        return Compiled(stubs, rows, installs=(install,), checks=(check,))


SPEC = card(GF, gearfried_whole_card(), archetype_member(SPEED2_TABLE, SPEED2_PHANTOM))
PROPS = card_props("FIRE", "Warrior", level=9, atk=3000, defense=2200, card_type="Effect Monster")

_main, _verify = dsl.make(SPEC, PROPS, out=OUT)


def main(write_text: bool = True, src: str = CHAIN, out: str = OUT) -> None:
    _main(write_text=write_text, src=src, out=out)


def verify(out: str = OUT) -> bool:
    return _verify(out) is not False
