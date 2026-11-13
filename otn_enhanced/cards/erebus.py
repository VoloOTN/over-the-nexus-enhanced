"""Erebus the Underworld Monarch (DARK / Zombie / Level 8 / 2800 / 1000) on Man-Eating Treasure Chest 0x1313, and (2026-11-12, same module) Ehther the Heavenly Monarch
(LIGHT / Fairy / Level 8 / 2800 / 1000) on Baron of the Fiend Sword 0x1312: M0 + the Tribute trigger + the shared E1 cost; Ehther's E1 effect = the native Deck-SS machine over a
2400+/1000 Deck row, its summon is marked by a kind-2 node keyed on the source cid (a front on the summon-rider list search @0x02268090) and returned to the hand by an End-Phase
registry row {0x02254EF1, 0x1312} (row 144, phantom cid 0x11CF; Supay's return-to-hand body).  Ehther E2 (Quick Effect Tribute Summon) is NOT built.

Erebus:  TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.
Donors Baron of the Fiend Sword 0x1312 / Man-Eating Treasure Chest 0x1313 proposed 2026-11-12 (donor_scan CLEAN), user approved ("Approve donors, build Erebus now").

    "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: You can send 2 "Monarch" Spell/Trap Cards with different
     names from your hand and/or Deck to the Graveyard, and if you do, shuffle 1 card from your opponent's hand (at random), Graveyard, or their side of the field into the Deck.
     Once per turn, during either player's Main Phase, if this card is in your Graveyard: You can discard 1 "Monarch" Spell/Trap Card, then target 1 monster in your Graveyard
     with 2400 or more ATK and 1000 DEF; add it to your hand."

BUILT   M0 (mega_monarch's alternate-Tribute front answers for 0x1313), the Tribute Summon trigger (mega_monarch's list front answers for it), E1's cost (2 Monarch S/T with
        different cids from hand and/or Deck) and E1's opponent-GY half.
NOT BUILT  E1's opponent hand (random) and field halves; E2 (the GY effect: cls2 has NO free phantom -> Strike's virtual cls2 via prefind_hook).  See notes/erebus-findings.md.

    uv run python _build_erebus.py   (or the Monarch session: scratch/_monarch_session.py, ORDER 'erebus')
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.cards import tenacity as TN
from otn_enhanced.dsl import CLS0, CLS1, CLS3, Compiled, Row, card_props
from otn_enhanced.effects import c79_trigger_hook, gy_vrow_hook as gyv, ov5_cave as O5, prefind_hook
from otn_enhanced.effects.common import bl as common_bl, find, insert_sorted, ov3_bl_target

EB = 0x1313
EH = 0x1312
PRIME = 0x14CF                                   # The Prime Monarch (donor The A. Forces, converted to a Continuous Trap): C1 only
IDX_PGY = 0xFFE6
PERF = 0x12F6                                   # Monarchic Perfection (donor Call of the Grave, converted to a Continuous Trap; stubs in c/perfection.c)
IDX_PFCOST, IDX_PFEFF = 0xFFEA, 0xFFEB         # its GY Monarch S/T cost row (MODE 7) / its field-candidate row
PF_PHANTOM = 0x0EC4                             # cls1 phantom dropped for its trigger record
PF_TRIG_SITE, PF_TRIG_PREV, PF_REGISTER = 0x02266524, 0x02023C90, 0x021D3504   # the summon-event handler's Special-Summon block (r6 == 9 = event, r7 = ctx): its one UNCONDITIONAL call `bl 0x02023C90(cid)`;
# 0x021D3504(side, cid, event, ctx) = the FIELD responder registrar (same block @0x022664B6 calls it with r6 / r7): every face-up copy of cid on side whose zone flag bit 5 is clear gets 0x021D3230(side, zone, event, ctx) (the offer) and bit 5 set.
# (0x022443C8 only SETS bit 5 -- it arms counter cards and would BLOCK this offer: CPU trace 2026-11-12.)
# (Everliving Underworld Cannon's own poster @0x0226658A is NOT usable: it only runs for a Zombie -- [sp+0x54] is the summoned monster's race mask, bit 2 -- CPU trace 2026-11-12.)
DLG_BASE = 596                                  # dlg_text ids appended for the menu labels (every language has 596 entries)
PF_LABELS = ("Destroy 1 monster.", "Destroy up to 2 Spells/Traps.", "Discard 1 random card.", "Destroy 1 face-down card.", "Place 1 card on top of Deck.", "Banish 1 card.", "Show other effects.", "Add it to your hand.", "Special Summon it.", "Normal Summon a Monarch.")   # 603 / 604 = Eidos the Underworld Monarch E3 (cards/eidos_monarch.py)
MISS_SITE, MISS_PREV = 0x021E510A, 0x0221AC08    # the "You can" body 0x021E50DC's bl to the miss-timing test 0x021EE0E0; chain head = the Dragon Rulers' cave3 front CAVE3_RUL_MISS
# Every Monarch-set card added by these modules (30 cids): their optional triggers must never miss the timing (user 2026-11-12: "make sure none of these effects can miss timing").
# Printed "When ... : You can" (by the printed text these COULD miss): Mobius 0x0FF3, Angmarl 0x14D8, Return of the Monarchs 0x14A1 -- included on the user's instruction.
NEVER_MISS = tuple(sorted((0x0FD7, 0x0FF3, 0x139B, 0x1E87, 0x0FC5, 0x127B, 0x14D8, 0x1313, 0x1312, 0x1230, 0x0FDC, 0x0FE2, 0x1123, 0x15EC, 0x1328, 0x12EB, 0x14A1,
                                0x12EE, 0x1633, 0x1923, 0x14C3, 0x1DCD, 0x0D6A, 0x0DE4, 0x10F3, 0x135E, 0x1800, 0x14CF, 0x249B, 0x12F6)))
IDX_PBAN = 0xFFE9                               # Prime Monarch GY half: the banish cost row (Monarch S/T, except self), MODE 6
GY_SELF_SS = 0x0220731D                          # native GY self-SS resolver (Plaguespreader / Quillbolt / Jet Warrior)
POS_SITE, POS_PREV = 0x022074E6, O5.CAVE_JW_C2_POS    # its `ldrb r0,[r5,#2] ; adds r3,r4,#0` pair, already Jet Warrior's BL front
FM = 0x249B                                    # The First Monarch (donor Tiki Soul; stats in cards/first_monarch.py): E1 here
IDX_FM = 0xFFE8                                # its hand row (the discard cost)
FM_PH1 = 0x0EC5
M0_SITE, M0_NATIVE_TAIL = 0x021AE14A, (O5.CAVE_RS_TRIBW if O5.combo() else O5.CAVE_MM_M0)   # the M0 hook BL and its current head (Restoration's double-Tribute front, which tails to mega_monarch's M0 stub)
SSE_SITE, SSE_TAIL = 0x02269266, O5.CAVE_MA_HE                 # SS engine free-zone check BL and March's front
HAND_ANY = 0x0223CB19                          # hand handler, no predicate (the native hand-discard row)
IDX_EHGY = 0xFFE7                               # Ehther E2: the GY Monarch S/T row (the banish cost)
H4_SITE = 0x02023566                           # ARM9: the hand-effect (list B) offer, a BL front chain
H4_PREV = O5.CAVE_T1_H4 if O5.combo() else O5.CAVE_BD_H4
SPEED_SITE, SPEED_TAIL = 0x021A894C, 0x023A9950   # ov3 speed lookup default leaf: `bl front ; nop`; the chain head (Captain Roland's front)
HAND_ZONE = 0x0B
GY_SETCODE = 0x0223CA2D                        # GY handler with the set-code predicate (Frost Blast / Revolt's Monarch GY row)
PM_PH0, PM_PH3 = 0x0E72, 0x152D
ALWAYS = 0x0224A115
CHAIN = "data/over_the_nexus/working/rom_chain_19C00.nds"
OUT = "data/over_the_nexus/working/rom_erebus.nds"
C_DIR = Path(__file__).resolve().parent / "c"

TAG_YOU_CAN = 0x021E51E5
OPP_GY_HANDLER = 0x0223D6FD                      # Card Ejector's criteria handler: the opponent's Graveyard
WORD_ST = 0x0000000C                             # Spell | Trap
WORD_GY = 0x0001000E                             # Card Ejector's row word
IDX_COST, IDX_EFF, IDX_HAND, IDX_GYM = 0xFFE0, 0xFFE1, 0xFFE2, 0xFFE3
IDX_HCOST, IDX_HDECK = 0xFFE4, 0xFFE5                 # Ehther: the shared cost row / the Deck Special Summon row
EP_ROW, EP_ROW_STOCK, EP_RETURN_HAND = 0x0228E1E0 + 144 * 8, (0x02253EC9, 0x11CF), 0x02254EF1   # End-Phase registry row 144 (a phantom) -> Supay's return-to-hand body
SUMLIST_SITE, LIST_SEARCH = 0x02268090, 0x02022E14    # summon-event handler: `bl list_search` on list 0x0228F708 by the SOURCE cid (full list: front it)
EH_PHANTOM = 0x0EB8
HAND_SETCODE = 0x0223CB39                        # Tenacity / Pantheism hand handler with the set-code predicate
WORD_ST_NOT_SELF = 0x0000002C
GY_ZONE = 0x0E
GY_SELECTOR, GY_TO_HAND = 0x02235605, 0x02208181   # native cls2 +14 GY list-zone selector / +04 add-target-to-hand resolver
MODE_ADDR = O5.CAVE_EB_DATA + 4
STATE = 0x0229AAFC
CLS1_PHANTOM = 0x0EB1
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
for _v in (TAG_YOU_CAN, OPP_GY_HANDLER, HAND_SETCODE, GY_SELECTOR, GY_TO_HAND, H3_RESUME, GY_SETCODE, ALWAYS):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

S = {**{n: getattr(O5, f"CAVE_EB_{n}") for n in ("COND", "COST", "RES", "PRED", "ROWH", "ROWS", "H2", "H3", "DATA", "COND2", "COST2", "RES2", "PRED2", "GYH", "VREC", "EHRES", "EHDH", "EHTR")},
     **{"PCOND": O5.CAVE_PM_COND, "PCOST": O5.CAVE_PM_COST, "PRES": O5.CAVE_PM_RES, "PTINY": O5.CAVE_PM_TINY,
        "FROWH": O5.CAVE_EB_FROWH, "RES2X": O5.CAVE_EB_RESX, "FLOCK": O5.CAVE_FM_LOCK, "FTRIB": O5.CAVE_FM_TRIB, "FLOCKF": O5.CAVE_FM_LOCKF, "FM0F": O5.CAVE_FM_M0F, "FCOND": O5.CAVE_FM_COND, "FCOST": O5.CAVE_FM_COST, "FRES": O5.CAVE_FM_RES, "H4": O5.CAVE_EB_H4, "SPD": O5.CAVE_EB_SPD, "COND3": O5.CAVE_EB_COND3, "COST3": O5.CAVE_EB_COST3, "VREC2": O5.CAVE_EB_VREC2, "PCOND2": O5.CAVE_PM_COND2, "PCOST2": O5.CAVE_PM_COST2, "PVREC": O5.CAVE_PM_VREC, "PPOS": O5.CAVE_PM_POS, "PPRED": O5.CAVE_PM_PRED, "PGYH": O5.CAVE_PM_GYH,
        "FCOND_PF": O5.CAVE_PF_COND, "FROWH_PF": O5.CAVE_PF_FROWH, "FCOST_PF": O5.CAVE_PF_COST, "FDATA_PF": O5.CAVE_PF_DATA, "FTINY_PF": O5.CAVE_PF_TINY, "FTRIG_PF": O5.CAVE_PF_TRIG, "FRES_PF": O5.CAVE_PF_RES}}
RESERVE = {"COND": 0xC0, "COST": 0x150, "RES": 0xC0, "PRED": 0x50, "ROWH": 0x80, "ROWS": 0xC0, "H2": 0xD0, "H3": 0x30, "DATA": 0x10, "COND2": 0x100, "COST2": 0x50, "RES2": 0x20, "PRED2": 0x40, "GYH": 0x30, "VREC": 0x20, "EHRES": 0x30, "EHDH": 0x30, "EHTR": 0x50, "PCOND": 0x90, "PCOST": 0x20, "PRES": 0xE8, "PTINY": 0x10, "FROWH": 0xA0, "RES2X": 0x150, "FLOCK": 0x70, "FTRIB": 0x70, "FLOCKF": 0x30, "FM0F": 0x40, "FCOND": 0x80, "FCOST": 0xD0, "FRES": 0x70, "H4": 0x20, "SPD": 0x60, "COND3": 0xC0, "COST3": 0x30, "VREC2": 0x20, "PCOND2": 0x100, "PCOST2": 0x90, "PVREC": 0x20, "PPOS": 0x30, "PPRED": 0x50, "PGYH": 0x30, "FCOND_PF": 0x140, "FROWH_PF": 0x80, "FCOST_PF": 0x20, "FDATA_PF": 0x10, "FTINY_PF": 0x10, "FTRIG_PF": 0x30, "FRES_PF": 0x300}
_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_EB_H2], _DN[O5.CAVE_EB_H3]
ROWS_BLOB = (struct.pack("<HHII", EB, TN.MONARCH_SET, S["ROWH"] | 1, WORD_ST) + bytes(4)
             + struct.pack("<HHII", EB, 0xFFFF, S["FROWH"] | 1, WORD_GY) + bytes(4)
             + struct.pack("<HHII", EB, TN.MONARCH_SET, HAND_SETCODE, WORD_ST_NOT_SELF) + bytes(4)
             + struct.pack("<HHII", EB, 0xFFFF, S["GYH"] | 1, 0x2) + bytes(4)
             + struct.pack("<HHII", EH, TN.MONARCH_SET, S["ROWH"] | 1, WORD_ST) + bytes(4)
             + struct.pack("<HHII", EH, 0xFFFF, S["EHDH"] | 1, 0x2) + bytes(4)
             + struct.pack("<HHII", PRIME, TN.MONARCH_SET, GY_SETCODE, WORD_ST) + bytes(4)
             + struct.pack("<HHII", EH, TN.MONARCH_SET, GY_SETCODE, WORD_ST) + bytes(4)
             + struct.pack("<HHII", FM, 0xFFFF, HAND_ANY, 0xE) + bytes(4)
             + struct.pack("<HHII", PRIME, 0xFFFF, S["PGYH"] | 1, WORD_ST) + bytes(4)
             + struct.pack("<HHII", PERF, TN.MONARCH_SET, GY_SETCODE, WORD_ST) + bytes(4)
             + struct.pack("<HHII", PERF, 0xFFFF, S["FROWH_PF"] | 1, 0) + bytes(4))
N_ROWS = len(ROWS_BLOB) // 16
assert all(struct.unpack_from("<I", ROWS_BLOB, 4 + 16 * k)[0] for k in range(N_ROWS)), "a virtual row's handler is missing (blx 0 = freeze)"
CLS1_REC = (EB, 0, S["RES2X"] | 1, 0, S["COND"] | 1, TAG_YOU_CAN, S["COST"] | 1)
FM_REC = (FM, 0, S["FRES"] | 1, 0, S["FCOND"] | 1, TAG_YOU_CAN, S["FCOST"] | 1)
EH2_REC = (EH, 0, 0x0220D80D, 0, S["COND3"] | 1, S["COST3"] | 1, 0)     # +04 = Cry Havoc!'s effect-Normal-Summon resolver (predicate: cards/escalation.py's front, keyed 0x1312)
VREC2_BLOB = struct.pack("<HH5I", *EH2_REC).ljust(RESERVE["VREC2"], b"\0")
PF_REC0 = (PERF, S["FTINY_PF"] + 4 | 1, 0, ALWAYS, S["FTINY_PF"] | 1, 0)       # the Continuous Trap activation (replaces Call of the Grave's own cls0 record in place)
PF_STOCK0 = (PERF, 0x0220DA01, 0, 0x021F2D01, 0, 0)    # Call of the Grave's stock cls0 record
PF_REC1 = (PERF, 0, S["FRES_PF"] | 1, 0, S["FCOND_PF"] | 1, TAG_YOU_CAN, S["FCOST_PF"] | 1)
PM_REC0 = (PRIME, S["PTINY"] + 4 | 1, 0, ALWAYS, S["PTINY"] | 1, 0)
PM_REC3 = (PRIME, S["PRES"] | 1, 0, S["PCOND"] | 1, S["PCOST"] | 1, 0)
EH_REC = (EH, 0, S["EHRES"] | 1, 0, S["COND"] | 1, TAG_YOU_CAN, S["COST"] | 1)       # the cost and condition are Erebus' (cid-blind; the rows are per cid)
PVREC_BLOB = struct.pack("<HH5I", PRIME, 0, GY_SELF_SS, 0, S["PCOND2"] | 1, S["PCOST2"] | 1, 0).ljust(RESERVE["PVREC"], bytes(1))
VREC_BLOB = struct.pack("<HH5I", EB, 0, S["RES2"] | 1, 0, S["COND2"] | 1, S["COST2"] | 1, GY_SELECTOR).ljust(RESERVE["VREC"], b"\0")


def _fit(blob: bytes, slot: str) -> bytes:
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _cpf(stub: str, slot: str) -> bytes:
    d = {"STUB": stub, "EBDATA": f"0x{S['DATA']:08X}", "PFDATA": f"0x{S['FDATA_PF']:08X}", "LMORE": str(DLG_BASE + 6)}
    d.update({f"L{i}": str(DLG_BASE + i) for i in range(6)})
    return _fit(compile_c(C_DIR / "perfection.c", S[slot], d), slot)


def _c(stub: str, slot: str) -> bytes:
    return _fit(compile_c(C_DIR / "erebus.c", S[slot], {"STUB": stub, "DATA": f"0x{S['DATA']:08X}", "PRED_ADDR": f"0x{S['PRED'] | 1:08X}", "PRED2_ADDR": f"0x{S['PRED2'] | 1:08X}", "PMPRED_ADDR": f"0x{S['PPRED'] | 1:08X}"}), slot)


SUMLIST_TAIL = 0x023AAC50                         # the chain head the summon-rider list site holds (Dragon Rulers / NEXT / Obedience / Petiteranodon fronts)


def ehtr_stub() -> bytes:
    """`bl 0x02022E14` front (r0 = the SOURCE cid): Ehther answers 1 (-> the kind-2 node keyed 0x1312 on the summoned monster); everything else tail-calls the previous head."""
    b = EffectBuilder()
    b.ldr_const(3, EH)
    b.insn("CMP", "R0, R3")
    b.insn("BEQ", "hit")
    b.ldr_const(3, SUMLIST_TAIL | 1)
    b.insn("BX", "R3")
    b.label("hit")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    return _fit(b.assemble(S["EHTR"], pad="nop"), "EHTR")


def h4_stub() -> bytes:
    """ARM9 0x02023566 BL (r0 = cid): Ehther -> 1 (the hand effect is offered), else the previous front."""
    b = EffectBuilder()
    b.ldr_const(3, EH)
    b.insn("CMP", "R0, R3")
    b.insn("BNE", "miss")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.label("miss")
    b.ldr_const(3, H4_PREV | 1)
    b.insn("BX", "R3")
    return _fit(b.assemble(S["H4"], pad="nop"), "H4")


def spd_stub() -> bytes:
    """Speed lookup default leaf (r2 = cid, r0 = desc): Ehther's hand cls2 effect -> speed 2 (Quick Effect); everything else tails to the chain head."""
    b = EffectBuilder()
    b.ldr_const(3, EH)
    b.insn("CMP", "R2, R3")
    b.insn("BNE", "gy")
    b.insn("LDRB", "R3, [R0, #0x3]")
    b.insn("CMP", f"R3, #0x{HAND_ZONE:X}")
    b.insn("BNE", "next")
    b.insn("LDRB", "R3, [R0, #0x5]")
    b.insn("CMP", "R3, #0x2")
    b.insn("BNE", "next")
    b.insn("MOV", "R0, #0x2")
    b.insn("BX", "LR")
    b.label("gy")
    b.ldr_const(3, EB)                                # Erebus E2: a GY quick effect (\"during either player's Main Phase\"); the cond restricts the phase
    b.insn("CMP", "R2, R3")
    b.insn("BNE", "next")
    b.insn("LDRB", "R3, [R0, #0x3]")
    b.insn("CMP", f"R3, #0x{GY_ZONE:X}")
    b.insn("BNE", "next")
    b.insn("MOV", "R0, #0x2")
    b.insn("BX", "LR")
    b.label("next")
    b.ldr_const(3, SPEED_TAIL | 1)
    b.insn("BX", "R3")
    return _fit(b.assemble(S["SPD"], pad="nop"), "SPD")


def fm_m0_front() -> bytes:
    """Over the M0 hook BL (r0 player, r1 summoned cid, r2 candidate side, r3 candidate slot): the First Monarch counts as 2 Tributes for a same-Attribute monster -> return TRUE out of the
    host (pop its frame); everything else tails to mega_monarch's M0 stub with every register and LR restored."""
    b = EffectBuilder()
    b.insn("PUSH", "{R0, R1, R2, R3, LR}")
    b.ldr_const(4, S["FTRIB"] | 1)
    b.insn("BLX", "R4")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "miss")
    b.insn("ADD", "SP, #0x14")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.insn("POP", "{R0, R1, R2, R3, R4}")
    b.insn("MOV", "LR, R4")
    b.ldr_const(4, M0_NATIVE_TAIL | 1)
    b.insn("BX", "R4")
    return _fit(b.assemble(S["FM0F"], pad="nop"), "FM0F")


def fm_lock_front() -> bytes:
    """Over `bl 0x021AD8C4(side)` in the SS engine (r6 = &card word): -1 ('no free zone', the engine's own bail-out) when The First Monarch forbids this Special Summon, else March's front."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("LDR", "R1, [R6, #0x0]")
    b.ldr_const(3, S["FLOCK"] | 1)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "pass")
    b.insn("MOV", "R0, #0x0")
    b.insn("MVN", "R0, R0")
    b.insn("POP", "{R4, R5, PC}")
    b.label("pass")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, SSE_TAIL | 1)
    b.insn("BLX", "R3")
    b.insn("POP", "{R4, R5, PC}")
    return _fit(b.assemble(S["FLOCKF"], pad="nop"), "FLOCKF")


def ptiny_stub(slot: str = "PTINY") -> bytes:
    """+0 cost (movs r0,#1 ; bx lr), +4 res (movs r0,#0 ; bx lr): The Prime Monarch's (and Monarchic Perfection's) Continuous Trap activation."""
    b = EffectBuilder()
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.insn("MOV", "R0, #0x0")
    b.insn("BX", "LR")
    return _fit(b.assemble(S[slot], pad="nop"), slot)


def nomiss_front() -> bytes:
    """Over `bl 0x021EE0E0(desc)` @0x021E510A in the "You can" body: a cid in NEVER_MISS -> 0 (never misses the timing), else tail to the previous head (r0 / LR intact)."""
    b = EffectBuilder()
    b.insn("LDRH", "R1, [R0, #0x0]")
    b.ldr_const(2, O5.CAVE_MON_NOMISS + 0x20)
    b.label("loop")
    b.insn("LDRH", "R3, [R2, #0x0]")
    b.insn("CMP", "R3, #0x0")
    b.insn("BEQ", "prev")
    b.insn("ADD", "R2, #0x2")
    b.insn("CMP", "R3, R1")
    b.insn("BNE", "loop")
    b.insn("MOV", "R0, #0x0")
    b.insn("BX", "LR")
    b.label("prev")
    b.ldr_const(3, MISS_PREV | 1)
    b.insn("BX", "R3")
    code = b.assemble(O5.CAVE_MON_NOMISS, pad="nop")
    assert len(code) <= 0x20, hex(len(code))
    assert_thumb1_only(code, O5.CAVE_MON_NOMISS)
    blob = code.ljust(0x20, bytes(1)) + b"".join(struct.pack("<H", c) for c in NEVER_MISS) + bytes(2)
    assert len(blob) <= 0x60, hex(len(blob))
    return blob


def pf_trig_front() -> bytes:
    """Over `bl 0x02023C90(cid)` @0x02266524 in the summon-event handler's Special-Summon block (r4 = the summon record: +2 summoner side; r6 = event; r7 = ctx):
    register every face-up Monarchic Perfection of the OTHER side as a responder (0x021D3504([r4+2] ^ 1, 0x12F6, r6, r7)), then make the original call with r0 intact
    and return its r0."""
    b = EffectBuilder()
    b.insn("PUSH", "{R0, LR}")
    b.insn("LDRH", "R0, [R4, #0x2]")
    b.insn("MOV", "R1, #0x1")
    b.insn("EOR", "R0, R1")
    b.ldr_const(1, PERF)
    b.insn("ADD", "R2, R6, #0x0")
    b.insn("ADD", "R3, R7, #0x0")
    b.bl(PF_REGISTER)
    b.insn("POP", "{R0}")
    b.bl(PF_TRIG_PREV)
    b.insn("POP", "{PC}")
    return _fit(b.assemble(S["FTRIG_PF"], pad="nop"), "FTRIG_PF")


def ppos_front() -> bytes:
    """Over the BL @0x022074E6 in the GY self-SS resolver (r5 = desc; the BL replaced `ldrb r0,[r5,#2] ; adds r3,r4,#0`): The Prime Monarch -> r3 = 1 (forced Defense),
    the caller's [sp] (the commit's (cid << 16) | flag word, already stored) gets flag 1 = 'Summon as a Trap Monster' (what 0x0221853D passes @0x022185B0; it makes the placement
    step @0x021C3130 test the trap-monster list and set zone-record +0x10 bit 10, so the stats come from the tree), and r0 = side.  Every other cid tails to Jet Warrior's front
    with LR untouched (it rebuilds r0 / r3 itself).  This stub pushes nothing, so [sp] here IS the resolver's [sp]."""
    b = EffectBuilder()
    b.insn("LDRH", "R0, [R5, #0x0]")
    b.ldr_const(3, PRIME)
    b.insn("CMP", "R0, R3")
    b.insn("BNE", "prev")
    b.insn("MOV", "R3, #0x1")
    b.insn("LDR", "R0, [SP, #0x0]")
    b.insn("ORR", "R0, R3")
    b.insn("STR", "R0, [SP, #0x0]")
    b.insn("LDRB", "R0, [R5, #0x2]")
    b.insn("BX", "LR")
    b.label("prev")
    b.ldr_const(3, POS_PREV | 1)
    b.insn("BX", "R3")
    return _fit(b.assemble(S["PPOS"], pad="nop"), "PPOS")


def h2_front() -> bytes:
    """criteria miss tail (r5 = cid): 0x1313 -> the cost row while the cost machine runs ([STATE+0x7C] != 0), else the effect row (opponent GY).  Pops the caller's frame."""
    b = EffectBuilder()
    b.ldr_const(0, EB)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, MODE_ADDR)
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, #0x2")
    b.insn("BEQ", "hand")
    b.insn("CMP", "R0, #0x3")
    b.insn("BEQ", "gym")
    b.ldr_const(0, STATE)
    b.insn("LDR", "R0, [R0, #0x7C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "cost")
    b.ldr_const(0, IDX_EFF)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("cost")
    b.ldr_const(0, IDX_COST)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("hand")
    b.ldr_const(0, IDX_HAND)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("gym")
    b.ldr_const(0, IDX_GYM)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.ldr_const(0, EH)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "prev")
    b.ldr_const(0, MODE_ADDR)
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, #0x4")
    b.insn("BEQ", "ehgy")
    b.ldr_const(0, STATE)
    b.insn("LDR", "R0, [R0, #0x7C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "hcost")
    b.ldr_const(0, IDX_HDECK)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("hcost")
    b.ldr_const(0, IDX_HCOST)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("ehgy")
    b.ldr_const(0, IDX_EHGY)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("prev")
    b.ldr_const(0, PRIME)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "prev2")
    b.ldr_const(0, MODE_ADDR)
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, #0x6")
    b.insn("BEQ", "pban")
    b.ldr_const(0, IDX_PGY)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("pban")
    b.ldr_const(0, IDX_PBAN)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("prev2")
    b.ldr_const(0, FM)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "prev3")
    b.ldr_const(0, IDX_FM)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("prev3")
    b.ldr_const(0, PERF)                              # Monarchic Perfection: MODE 7 -> the GY cost row 0xFFEA, else the field row 0xFFEB
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "prev4")
    b.ldr_const(0, MODE_ADDR)
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, #0x7")
    b.ldr_const(0, IDX_PFCOST)
    b.insn("BEQ", "pfc")
    b.insn("ADD", "R0, #0x1")
    b.label("pfc")
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("prev4")
    b.bl(H2_PREV)
    return _fit(b.assemble(S["H2"], pad="nop"), "H2")


def h3_front() -> bytes:
    b = EffectBuilder()
    b.ldr_const(0, IDX_COST)
    b.insn("SUB", "R0, R6, R0")
    b.insn("CMP", f"R0, #0x{N_ROWS:X}")
    b.insn("BCS", "prev")
    b.insn("LSL", "R0, R0, #0x4")
    b.ldr_const(3, S["ROWS"])
    b.insn("ADD", "R0, R0, R3")
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, H3_PREV | 1)
    b.insn("BX", "R0")
    return _fit(b.assemble(S["H3"], pad="nop"), "H3")


BIN2_PAC = "Data_arc_pac/bin2.pac"
DLG_LANGS_ASCII = ("e", "f", "g", "i", "s")      # latin-1 tables: get the English labels
DLG_LANGS_OTHER = ("j", "k", "r")                # other encodings: the new ids point at the existing 0x103 string ("Use which effect?" in that language)


def _dlg_files(rom):
    from otn_enhanced.rom.pac import parse_pac
    blob = bytes(rom.getFileByName(BIN2_PAC))
    archive = parse_pac(blob, BIN2_PAC)
    by_name = {f.get_clean_name(): i for i, f in enumerate(archive.files)}
    get = lambda n: bytes(blob[archive.files[by_name[n]].address:archive.files[by_name[n]].address + archive.files[by_name[n]].size])
    return blob, by_name, get


def _append_dlg_labels(rom) -> None:
    """Append Perfection's 7 menu labels as dlg_text ids 596..602 in every language (idempotent).  Index entries are u32 byte offsets into dlg_text_<L>.bin."""
    from otn_enhanced.rom.pac import build_modified_pac
    blob, by_name, get = _dlg_files(rom)
    repl = {}
    for lang in DLG_LANGS_ASCII + DLG_LANGS_OTHER:
        idx, txt = bytearray(get(f"dlg_indx_{lang}.bin")), bytearray(get(f"dlg_text_{lang}.bin"))
        n = len(idx) // 4
        if n == DLG_BASE + len(PF_LABELS):
            continue
        assert n == DLG_BASE, f"dlg_indx_{lang}: {n} entries, expected {DLG_BASE}"
        for k, label in enumerate(PF_LABELS):
            if lang in DLG_LANGS_ASCII:
                txt.extend(b"\0" * (-len(txt) % 4))
                off = len(txt)
                txt.extend(label.encode("ascii") + b"\0")
            else:
                off = struct.unpack_from("<I", idx, 0x103 * 4)[0]
            idx.extend(struct.pack("<I", off))
        txt.extend(b"\0" * (-len(txt) % 4))
        repl[by_name[f"dlg_indx_{lang}.bin"]] = bytes(idx)
        repl[by_name[f"dlg_text_{lang}.bin"]] = bytes(txt)
    if repl:
        rom.setFileByName(BIN2_PAC, build_modified_pac(blob, BIN2_PAC, repl))


def _dlg_labels_ok(rom) -> bool:
    blob, by_name, get = _dlg_files(rom)
    for lang in DLG_LANGS_ASCII:
        idx, txt = get(f"dlg_indx_{lang}.bin"), get(f"dlg_text_{lang}.bin")
        if len(idx) // 4 != DLG_BASE + len(PF_LABELS):
            return False
        for k, label in enumerate(PF_LABELS):
            off = struct.unpack_from("<I", idx, (DLG_BASE + k) * 4)[0]
            if txt[off:txt.index(b"\0", off)] != label.encode("ascii"):
                return False
    return all(len(get(f"dlg_indx_{lang}.bin")) // 4 == DLG_BASE + len(PF_LABELS) for lang in DLG_LANGS_OTHER)


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _reaches(view, site: int, slot: str) -> bool:
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


class erebus_the_underworld_monarch:
    cid: int = EB

    def blobs(self):
        return {"COND": (S["COND"], _c("EB_COND", "COND"), "cls1 +0C cond (C)"),
                "COST": (S["COST"], _c("EB_COST", "COST"), "cls1 +14 cost (C)"),
                "RES": (S["RES"], _c("EB_RES", "RES"), "cls1 +04 resolver (C)"),
                "PRED": (S["PRED"], _c("EB_PRED", "PRED"), "list predicate (C)"),
                "ROWH": (S["ROWH"], _c("EB_ROWH", "ROWH"), "cost row handler (C)"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria rows 0xFFE0 / 0xFFE1"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"),
                "DATA": (S["DATA"], bytes(RESERVE["DATA"]), "DATA: first pick's cid, MODE (ship clear)"),
                "COND2": (S["COND2"], _c("EB_COND2", "COND2"), "E2 virtual cls2 +0C cond (C)"),
                "COST2": (S["COST2"], _c("EB_COST2", "COST2"), "E2 virtual cls2 +10 cost (C)"),
                "RES2": (S["RES2"], _c("EB_RES2", "RES2"), "E2 virtual cls2 +04 resolver (C)"),
                "PRED2": (S["PRED2"], _c("EB_PRED2", "PRED2"), "GY predicate (C)"),
                "GYH": (S["GYH"], _c("EB_GYH", "GYH"), "GY monster row handler (C)"),
                "VREC": (S["VREC"], VREC_BLOB, "E2 virtual cls2 record (data)"),
                "EHRES": (S["EHRES"], _c("EH_RES", "EHRES"), "Ehther cls1 +04 native Deck SS (C)"),
                "EHDH": (S["EHDH"], _c("EH_DH", "EHDH"), "Ehther Deck SS row handler (C)"),
                "EHTR": (S["EHTR"], ehtr_stub(), "summon-rider list front: Ehther's source cid -> 1"),
                "PCOND": (S["PCOND"], _c("PM_COND", "PCOND"), "Prime Monarch cls3 +0C cond (C)"),
                "PCOST": (S["PCOST"], _c("PM_COST", "PCOST"), "Prime Monarch cls3 +10 stamp (C)"),
                "PRES": (S["PRES"], _c("PM_RES", "PRES"), "Prime Monarch cls3 +04 resolver (C)"),
                "PTINY": (S["PTINY"], ptiny_stub(), "Prime Monarch cls0 cost / res"),
                "FROWH": (S["FROWH"], _c("EB_FROWH", "FROWH"), "E1 effect row handler: opponent GY + field (C)"),
                "RES2X": (S["RES2X"], _c("EB_RES2X", "RES2X"), "cls1 +04 resolver v2 (C)"),
                "FLOCK": (S["FLOCK"], _c("FM_LOCK", "FLOCK"), "First Monarch SS-lock helper (C)"),
                "FTRIB": (S["FTRIB"], _c("FM_TRIB", "FTRIB"), "First Monarch 2-Tribute helper (C)"),
                "FLOCKF": (S["FLOCKF"], fm_lock_front(), "SS engine free-zone front: First Monarch lock"),
                "FM0F": (S["FM0F"], fm_m0_front(), "M0 hook front: First Monarch counts as 2 Tributes"),
                "FCOND": (S["FCOND"], _c("FM_COND", "FCOND"), "First Monarch E1 cls1 +0C cond (C)"),
                "FCOST": (S["FCOST"], _c("FM_COST", "FCOST"), "First Monarch E1 cls1 +14 cost (C)"),
                "FRES": (S["FRES"], _c("FM_RES", "FRES"), "First Monarch E1 cls1 +04 resolver (C)"),
                "H4": (S["H4"], h4_stub(), "ARM9 H4 hand-offer front: Ehther -> 1"),
                "SPD": (S["SPD"], spd_stub(), "speed default-leaf front: Ehther hand cls2 -> 2"),
                "COND3": (S["COND3"], _c("EH2_COND", "COND3"), "Ehther E2 virtual cls2 +0C cond (C)"),
                "COST3": (S["COST3"], _c("EH2_COST", "COST3"), "Ehther E2 virtual cls2 +10 cost (C)"),
                "VREC2": (S["VREC2"], VREC2_BLOB, "Ehther E2 virtual cls2 record (data)"),
                "PCOND2": (S["PCOND2"], _c("PM2_COND", "PCOND2"), "Prime Monarch GY half virtual cls2 +0C cond (C)"),
                "PCOST2": (S["PCOST2"], _c("PM2_COST", "PCOST2"), "Prime Monarch GY half virtual cls2 +10 cost (C)"),
                "PVREC": (S["PVREC"], PVREC_BLOB, "Prime Monarch GY half virtual cls2 record (data)"),
                "PPOS": (S["PPOS"], ppos_front(), "GY self-SS resolver position front: 0x14CF -> Defense"),
                "PPRED": (S["PPRED"], _c("PM_PRED", "PPRED"), "row 0xFFE9 predicate: Monarch S/T, not the source card (C)"),
                "PGYH": (S["PGYH"], _c("PM_GYH", "PGYH"), "row 0xFFE9 GY handler (C)"),
                "FCOND_PF": (S["FCOND_PF"], _cpf("PF_COND", "FCOND_PF"), "Monarchic Perfection cls1 +0C cond (C)"),
                "FCOST_PF": (S["FCOST_PF"], _cpf("PF_COST", "FCOST_PF"), "Monarchic Perfection cls1 +14 cost: GY banish (C)"),
                "FRES_PF": (S["FRES_PF"], _cpf("PF_RES", "FRES_PF"), "Monarchic Perfection cls1 +04 resolver: menu + picker + effects (C)"),
                "FROWH_PF": (S["FROWH_PF"], _cpf("PF_FROWH", "FROWH_PF"), "Monarchic Perfection row 0xFFEB field handler (C)"),
                "FDATA_PF": (S["FDATA_PF"], bytes(RESERVE["FDATA_PF"]), "Monarchic Perfection DATA (ship clear)"),
                "FTINY_PF": (S["FTINY_PF"], ptiny_stub("FTINY_PF"), "Monarchic Perfection cls0 cost / res"),
                "NOMISS": (O5.CAVE_MON_NOMISS, nomiss_front(), "never-miss-timing front for the Monarch set (code + cid table)"),
                "FTRIG_PF": (S["FTRIG_PF"], pf_trig_front(), "SS-event front: registers the opponent's face-up Monarchic Perfection as a responder")}

    def compile(self, view=None) -> Compiled:
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            if key not in ("ROWS", "DATA", "VREC", "VREC2", "PVREC", "FDATA_PF", "NOMISS"):
                assert_thumb1_only(blob, addr)

        c79_trigger_hook.register_extra(FM, "Tiki Soul -> The First Monarch E1 (Summoned as a Trap Monster; test ROM, not shipped)")
        prefind_hook.register(EB, S["VREC"], "Erebus E2 GY ignition", cls=2, zone=GY_ZONE, any_sub=True)
        prefind_hook.register(EH, S["VREC2"], "Ehther E2 hand quick effect", cls=2, zone=HAND_ZONE, any_sub=False)
        prefind_hook.register(PRIME, S["PVREC"], "The Prime Monarch GY half (GY ignition)", cls=2, zone=GY_ZONE, any_sub=True)

        def install(rom, v):
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            gyv.install(rom, v.buf, arms=gyv.ARMS + gyv.MONARCH_ARMS, layout=gyv.GYV2)
            prefind_hook.install(rom, v)
            insert_sorted(v, CLS1, EH_REC, drop=EH_PHANTOM)
            insert_sorted(v, CLS1, FM_REC, drop=FM_PH1)
            c79_trigger_hook.install(rom)
            c79_trigger_hook.apply(v.buf)
            for site, tail, mine, what in ((M0_SITE, M0_NATIVE_TAIL, S["FM0F"], "M0 hook"), (SSE_SITE, SSE_TAIL, S["FLOCKF"], "SS engine free-zone check")):
                cur = ov3_bl_target(v.buf, site)
                assert cur in (tail, mine), f"{what} @{site:#x} calls {cur:#x}, expected {tail:#x} (or ours)"
                v.write(site, common_bl(site, mine))
            _front_at(v, POS_SITE, POS_PREV, S["PPOS"], "GY self-SS resolver position BL")
            insert_sorted(v, CLS0, PM_REC0, drop=PM_PH0)
            i0 = find(v, CLS0, PERF)                            # Monarchic Perfection: Call of the Grave's own cls0 record rewritten in place (count-neutral)
            assert i0 is not None, "cls0 record for 0x12F6 missing"
            cur = tuple(v.unpack(CLS0.addr(i0), CLS0.fmt))
            assert cur in (PF_STOCK0, PF_REC0), f"cls0 0x12F6 is {[hex(x) for x in cur]}"
            v.pack(CLS0.addr(i0), CLS0.fmt, *PF_REC0)
            insert_sorted(v, CLS1, PF_REC1, drop=PF_PHANTOM)
            _front_at(v, PF_TRIG_SITE, PF_TRIG_PREV, S["FTRIG_PF"], "summon-event SS block bl 0x02023C90")
            _append_dlg_labels(rom)
            _front_at(v, MISS_SITE, MISS_PREV, O5.CAVE_MON_NOMISS, "You-can body miss-timing BL")
            insert_sorted(v, CLS3, PM_REC3, drop=PM_PH3)
            cur = ov3_bl_target(v.buf, SUMLIST_SITE)
            assert cur in (SUMLIST_TAIL, S["EHTR"]), f"summon-rider list site @{SUMLIST_SITE:#x} calls {cur:#x}, expected the chain head {SUMLIST_TAIL:#x}"
            v.write(SUMLIST_SITE, common_bl(SUMLIST_SITE, S["EHTR"]))
            row = tuple(v.unpack(EP_ROW, "<II"))
            assert row in (EP_ROW_STOCK, (EP_RETURN_HAND, EH)), f"End-Phase registry row 144 = {row}"
            v.write(EP_ROW, struct.pack("<II", EP_RETURN_HAND, EH))
            cur = bytes(v.blob(SPEED_SITE, 6))
            want = common_bl(SPEED_SITE, S["SPD"]) + struct.pack("<H", 0x46C0)
            assert cur == want or cur == common_bl(SPEED_SITE, SPEED_TAIL) + struct.pack("<H", 0x46C0), f"speed default leaf @{SPEED_SITE:#x} is {cur.hex()}: the chain head moved"
            v.write(SPEED_SITE, want)
            mc, sec = O5._arm9_main(rom)
            d = bytearray(sec.data)
            a = H4_SITE - 0x02000000
            assert bytes(d[a:a + 4]) in (common_bl(H4_SITE, H4_PREV), common_bl(H4_SITE, S["H4"])), f"ARM9 H4 site {H4_SITE:#x} is not the expected front"
            d[a:a + 4] = common_bl(H4_SITE, S["H4"])
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Erebus {slot} front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            prefind_hook.verify(rom, v, lambda ok, msg: c.ok(bool(ok), msg))
            for cid in (EB, PRIME):
                c.ok(any(r[0] == cid for r in gyv.rows(rom, gyv.ARMS + gyv.MONARCH_ARMS, gyv.GYV2["MAX"])), f"virtual GY-action row for 0x{cid:04X}")
            c.eq(ov3_bl_target(v.buf, POS_SITE), S["PPOS"], "GY self-SS resolver position BL -> the Prime Monarch Defense front")
            c.eq(ov3_bl_target(v.buf, SUMLIST_SITE), S["EHTR"], "summon-rider list search -> Ehther's front")
            c.eq(tuple(v.unpack(EP_ROW, "<II")), (EP_RETURN_HAND, EH), "End-Phase registry row 144 -> return to hand for Ehther")
            from otn_enhanced.effects.common import rows as _rows
            c.ok([r for r in _rows(v, CLS1) if r[0] == EH] == [EH_REC], "cls1 record under 0x1312")
            c.eq(bytes(v.blob(SPEED_SITE, 6)), common_bl(SPEED_SITE, S["SPD"]) + struct.pack("<H", 0x46C0), "speed default leaf -> Ehther's front")
            mc, sec = O5._arm9_main(rom)
            a = H4_SITE - 0x02000000
            c.ok(bytes(sec.data[a:a + 4]) in {common_bl(H4_SITE, f) for f in O5.dc_ahead_of(S["H4"]) | {S["H4"]}}, "ARM9 bl @0x02023566 -> H4 front (or a later owner's front ahead of it)")
            c.eq(ov3_bl_target(v.buf, M0_SITE), S["FM0F"], "M0 hook BL -> the First Monarch 2-Tribute front")
            c.eq(ov3_bl_target(v.buf, SSE_SITE), S["FLOCKF"], "SS engine free-zone BL -> the First Monarch lock front")
            c.ok([r for r in _rows(v, CLS1) if r[0] == FM] == [FM_REC], "cls1 record under 0x249B")
            c79_trigger_hook.verify(v.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)
            c.ok([r for r in _rows(v, CLS0) if r[0] == PRIME] == [PM_REC0], "cls0 record under 0x14CF")
            c.ok([r for r in _rows(v, CLS3) if r[0] == PRIME] == [PM_REC3], "cls3 record under 0x14CF")
            c.ok([r for r in _rows(v, CLS0) if r[0] == PERF] == [PF_REC0], "cls0 record under 0x12F6 (Continuous Trap activation)")
            c.ok([r for r in _rows(v, CLS1) if r[0] == PERF] == [PF_REC1], "cls1 trigger record under 0x12F6")
            c.eq(ov3_bl_target(v.buf, PF_TRIG_SITE), S["FTRIG_PF"], "summon-event SS block BL @0x02266524 -> Perfection trigger front")
            c.eq(ov3_bl_target(v.buf, MISS_SITE), O5.CAVE_MON_NOMISS, "You-can body miss-timing BL @0x021E510A -> the Monarch never-miss front")
            c.ok(_dlg_labels_ok(rom), "dlg_text ids 596..605 = the Perfection / Eidos menu labels in every language")
            ok_pf, msg_pf = __import__("otn_enhanced.data.card_text", fromlist=["x"]).check_rom_text(c.out, PERF)
            c.ok(ok_pf, f"text 0x12F6: {msg_pf}")
            ok_text, msg = __import__("otn_enhanced.data.card_text", fromlist=["x"]).check_rom_text(c.out, PRIME)
            c.ok(ok_text, f"text 0x14CF: {msg}")

        return Compiled(tuple(blobs.values()), rows=(Row(CLS1, CLS1_REC, CLS1_PHANTOM),), installs=(install,), checks=(check,))


SPEC = erebus_the_underworld_monarch()
PROPS = card_props("DARK", "Zombie", level=8, atk=2800, defense=1000, card_type="Effect Monster")
_dsl_main, verify = dsl.make(SPEC, PROPS, out=OUT)

# CPU row: The A. Forces' stock row (id 0x7D4CF, a Spell evaluator) never lets the CPU use the card's field effect.  Re-key it the way Escalation's stock row reads (id 0x3C000 | cid,
# the always-true evaluator 0x023107C1: the card's own cond decides) -- the same edit Pantheism / Strike make to their rows.
AI_ALWAYS = 0x023107C1


def _patch_prime_ai_row(out: str, cid: int = PRIME) -> None:
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov = O5._load_ov5_decompressed(rom)
    data = bytearray(ov.data)
    hits = []
    for off in range(0x02390000 - ov.ramAddress, min(len(data), 0x02397200 - ov.ramAddress) - 8, 4):
        w, h = struct.unpack_from("<II", data, off)
        if (w & 0x3FFF) == cid and (h & 1) and (w >> 16) and (w >> 16) & 0xFFF0 == 0:
            hits.append(off)
    if not hits and any(struct.unpack_from("<II", data, o) == (0x3C000 | cid, AI_ALWAYS) for o in range(0x02390000 - ov.ramAddress, min(len(data), 0x02397200 - ov.ramAddress) - 8, 4)):
        return                                        # already re-keyed (idempotent)
    assert len(hits) == 1, f"CPU rows for 0x{cid:04X}: {len(hits)}"
    struct.pack_into("<II", data, hits[0], 0x3C000 | cid, AI_ALWAYS)
    O5._save_ov5(rom, ov, bytes(data))
    rom.saveToFile(out)
EH_PROPS = card_props("LIGHT", "Fairy", level=8, atk=2800, defense=1000, card_type="Effect Monster")


def main(write_text: bool = False, src: str = dsl.SRC, out: str = OUT) -> None:
    """dsl.make's main does the stubs, Erebus' cls1 row and his stats/text; Ehther's cls1 row is inserted by install(), his stats/text are applied here."""
    from otn_enhanced.data import card_text
    from otn_enhanced.data.card_stats import TEXT_LANGS, apply_stats_and_text
    from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
    from otn_enhanced.dsl import apply_card_stat_edits, card_stat_edit
    apply_card_stat_edits([card_stat_edit(PRIME, copy_from=0x1800), card_stat_edit(PERF, copy_from=0x1800)], src=src, out=out)   # + Call of the Grave (Normal Trap) -> Continuous Trap      # first (a fresh, normalised ROM): The A. Forces (Continuous Spell) -> a Continuous Trap's card_prop record
    _dsl_main(write_text=write_text, src=out, out=out)
    if write_text:
        card_text.apply_to_rom(out, PRIME)
        card_text.apply_to_rom(out, PERF)
    _patch_prime_ai_row(out)
    _patch_prime_ai_row(out, PERF)
    p = EH_PROPS
    name, desc = (x.encode("ascii", "replace") for x in card_text.CARD_TEXT[EH]["e"])
    apply_stats_and_text(out, cid=EH, attribute=p.attribute, race=p.race, level=p.level, atk=p.atk, defense=p.defense,
                         card_type=ERA2_CARD_TYPE_REVERSE[p.card_type], name=name, desc=desc, langs=TEXT_LANGS, write_text=write_text)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
