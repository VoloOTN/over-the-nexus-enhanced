"""Animadorned Archosaur (LIGHT / Dinosaur / Level 1 / 0 / 0) on Swordsman of Landstar 0x1297.

    If this card is Normal or Special Summoned: You can destroy 1 Dinosaur monster in your hand or face-up field, except
    "Animadorned Archosaur", then add 1 Reptile, Sea Serpent, or Winged Beast monster with the same original Level as that
    destroyed monster, OR 1 "Evolution Pill" Spell, from your Deck to your hand. You can only use this effect of
    "Animadorned Archosaur" once per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS1, CRITERIA, Compiled, LIST_NS_OR_SS, Row, _TURNLOG_POST, _TURNLOG_QUERY
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass


def deck_walker_race_or_named_spell_pred(base: int, races: tuple, pills: tuple) -> bytes:
    """Deck-walker predicate (r0 side, r1 zone, r2 idx, r3 row cid, [sp] &card word, [sp+4] list): keeps monsters of the listed
    races and Spells in `pills`. The walker has already required 'monster OR Spell' (word 0x6) and, for monsters, the Level."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, LR}")
    b.insn("LDR", "R0, [SP, #0x8]")
    b.insn("LDR", "R0, [R0, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R4, R0, #0x12")
    b.insn("ADD", "R0, R4, #0x0")
    b.call("is_monster", via=R3)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "spell")
    b.insn("ADD", "R0, R4, #0x0")
    b.call("get_race", via=R3)
    for r in races:
        b.insn("CMP", f"R0, #0x{r:X}")
        b.insn("BEQ", "yes")
    b.insn("B", "no")
    b.label("spell")
    for p in pills:
        b.ldr_const(1, p)
        b.insn("CMP", "R4, R1")
        b.insn("BEQ", "yes")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, PC}")
    b.label("yes")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, PC}")
    return b.assemble(base, pad="nop")


@dataclass(frozen=True)
class summoned_destroy_dinosaur_add_same_level_monster_or_named_spell_once_per_turn:
    """'If this card is Normal or Special Summoned: You can destroy 1 Dinosaur monster in your hand or face-up field, except this
    card, then add 1 <race list> monster with the same original Level as that destroyed monster, OR 1 <named> Spell, from your
    Deck to your hand. Once per turn.' User rulings: offered iff a destroyable Dinosaur exists (no search target required).
      NS-or-SS trigger list + cls1 {RES, 0, COND, SLOT4, 0} (Oviraptor C1's shape) + ONE criteria row {cid, 0xFFFF, CRIT, 0x6}
      (word 0x6 = monster OR Spell for the Deck walker; its +0xA Level byte is written at resolution).
      RES = Tyranno C2's Hand/Field prompt + own candidate list (HELP) + picker on private phases 0x90..0x94 (chain-depth bracket
      closed before handing off), the destroyed card's ORIGINAL Level into this cid's criteria row +0xA, then phase 0x80 handed to
      the native add-to-hand resolver 0x02207EF5 (which owns every phase < 0x80). Shared timing_class_hook arm."""
    res: int
    cond: int
    slot4: int
    help: int
    pred: int
    crit: int
    races: tuple
    pills: tuple
    phantoms: tuple[int, int, int]     # (NS-or-SS list, cls1, criteria)

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import timing_class_hook as tch
        ADD_TO_HAND, TAG, DECK_WALKER, ROW_INDEX = 0x02207EF5, 0x021E51E5, 0x0223BC3D, 0x02243B9D
        PHASE_STATE, CHOICE_STATE, HAND_COUNT, FIELD_CID, STRIDE = 0x0229AAFC, 0x0229DD94, 0x0229ACA0, 0x0229ACC8, 0xB3C
        SLOT, RECORD, PROMPT, MESSAGE, PICK_UI = 0x0219CA29, 0x02243B2D, 0x0219ABB5, 0x0219A819, 0x0219C99D
        PICK_HDR, PICK_WORDS, PICK_LOCS, CTRL_TYPE = 0x0229944C, 0x02299458, 0x02299908, 0x0229911C
        DESTROY_FIELD, DESTROY_HAND, OPEN, CLOSE, RACE_LIVE = 0x021CF375, 0x021D2479, 0x021D28A5, 0x021D2965, 0x021B88F1
        TITLE, LBL_HAND, LBL_FIELD, MSG_DESTROY, PICK_CODE, DINO = 0x103, 0x192, 0x23C, 0x6D, 6, 9
        helpp = self.help | 1

        b = EffectBuilder()          # (r0 side, r1 mode 0 hand / 1 field, r2 record?) -> count of own destroyable Dinosaurs
        b.insn("PUSH", "{R1, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("ADD", "R7, R2, #0x0")
        b.insn("MOV", "R6, #0x0")
        b.insn("MOV", "R5, #0x0")
        b.insn("LDR", "R0, [SP, #0x0]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "field")
        b.label("hand")
        b.ldr_const(1, HAND_COUNT)
        b.insn("CMP", "R4, #0x0")
        b.insn("BEQ", "h0")
        b.ldr_const(0, STRIDE)
        b.insn("ADD", "R1, R1, R0")
        b.label("h0")
        b.insn("LDR", "R0, [R1, #0x0]")
        b.insn("CMP", "R5, R0")
        b.insn("BGE", "done")
        b.call_addr(SLOT, R4, 0xB, R5, via=R3)
        b.insn("LDR", "R0, [R0, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "hnext")
        b.insn("STR", "R0, [SP, #0x0]")
        b.call("is_monster", via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "hnext")
        b.insn("LDR", "R0, [SP, #0x0]")
        b.call("get_race", via=R3)
        b.insn("CMP", f"R0, #0x{DINO:X}")
        b.insn("BNE", "hnext")
        b.insn("ADD", "R6, #0x1")
        b.insn("CMP", "R7, #0x0")
        b.insn("BEQ", "hnext")
        b.call_addr(RECORD, R4, 0xB, R5, via=R3)
        b.label("hnext")
        b.insn("ADD", "R5, #0x1")
        b.insn("B", "hand")
        b.label("field")
        b.insn("CMP", "R5, #0x4")
        b.insn("BGT", "done")
        b.ldr_const(1, FIELD_CID)
        b.insn("CMP", "R4, #0x0")
        b.insn("BEQ", "f0")
        b.ldr_const(0, STRIDE)
        b.insn("ADD", "R1, R1, R0")
        b.label("f0")
        b.insn("LSL", "R0, R5, #0x4")
        b.insn("ADD", "R1, R1, R0")
        b.insn("LSL", "R0, R5, #0x2")
        b.insn("ADD", "R1, R1, R0")
        b.insn("LDRH", "R0, [R1, #0x0]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "fnext")
        b.insn("LDRH", "R2, [R1, #0x8]")
        b.insn("CMP", "R2, #0x0")
        b.insn("BEQ", "fnext")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "fnext")
        b.call_addr(RACE_LIVE, R4, R5, 0, via=R3)
        b.insn("CMP", f"R0, #0x{DINO:X}")
        b.insn("BNE", "fnext")
        b.insn("ADD", "R6, #0x1")
        b.insn("CMP", "R7, #0x0")
        b.insn("BEQ", "fnext")
        b.call_addr(RECORD, R4, R5, 0, via=R3)
        b.label("fnext")
        b.insn("ADD", "R5, #0x1")
        b.insn("B", "field")
        b.label("done")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("POP", "{R1, R4, R5, R6, R7, PC}")
        help_blob = b.assemble(self.help, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.turnlog_query(R0, cid, 1, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.insn("LDRB", "R4, [R5, #0x2]")
        b.insn("LDRB", "R0, [R5, #0x6]")
        b.insn("EOR", "R4, R0")
        b.insn("MOV", "R0, #0x1")
        b.insn("AND", "R4, R0")
        b.call_addr(helpp, R4, 0, 0, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "yes")
        b.call_addr(helpp, R4, 1, 0, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.label("yes")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, PC}")
        cond = b.assemble(self.cond, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(TAG, via=R2)
        b.insn("CMP", "R0, #0x1")
        b.insn("BNE", "out")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_post(R0, cid, 1, via=R4)
        b.insn("ADD", "R0, R5, #0x0")
        b.label("out")
        b.insn("POP", "{R4, R5, PC}")
        slot4 = b.assemble(self.slot4, pad="nop")

        pred = deck_walker_race_or_named_spell_pred(self.pred, self.races, self.pills)

        b = EffectBuilder()          # criteria-row handler (r0 row, r1 side, r2 param) -> candidate count (0x0223CAF4's shape)
        b.insn("PUSH", "{R4, LR}")
        b.insn("SUB", "SP, #0x8")
        b.insn("LDR", "R3, [R0, #0x8]")
        b.insn("STR", "R3, [SP, #0x0]")
        b.insn("MOV", "R3, #0x2")
        b.insn("STR", "R3, [SP, #0x4]")
        b.insn("ADD", "R3, R0, #0x0")
        b.insn("ADD", "R0, R1, #0x0")
        b.insn("LDRH", "R1, [R3, #0x0]")
        b.call_addr(DECK_WALKER, R0, R1, self.pred | 1, 0, via=R4)
        b.insn("ADD", "SP, #0x8")
        b.insn("POP", "{R4, PC}")
        crit = b.assemble(self.crit, pad="nop")

        def set_level(b):
            b.call("cid_level", via=R3)
            b.insn("LSL", "R7, R0, #0x2")
            b.insn("LDRH", "R0, [R5, #0x0]")
            b.call_addr(ROW_INDEX, R0, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "abortj")
            b.insn("LSL", "R1, R0, #0x3")
            b.insn("LSL", "R0, R0, #0x2")
            b.insn("ADD", "R0, R0, R1")
            b.ldr_const(1, CRITERIA.base)
            b.insn("ADD", "R0, R0, R1")
            b.insn("STRB", "R7, [R0, #0xA]")

        b = EffectBuilder()          # cls1 +04 (r0 = desc); desc[+0x18] = 0 hand / 1 field, [+0x1A] picked zone code, [+0x1C] hand count
        b.insn("PUSH", "{R1, R2, R3, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R6, [R5, #0x2]")
        b.insn("LDRB", "R0, [R5, #0x6]")
        b.insn("EOR", "R6, R0")
        b.insn("MOV", "R0, #0x1")
        b.insn("AND", "R6, R0")
        b.ldr_const(4, PHASE_STATE)
        b.insn("LDR", "R0, [R4, #0x70]")
        b.insn("CMP", "R0, #0x80")
        b.insn("BEQ", "p80")
        b.insn("BGT", "private")
        b.insn("B", "addhand")
        b.label("private")
        b.insn("CMP", "R0, #0x90")
        b.insn("BEQ", "p90")
        b.insn("CMP", "R0, #0x91")
        b.insn("BEQ", "p91")
        b.insn("CMP", "R0, #0x92")
        b.insn("BEQ", "p92j")
        b.insn("CMP", "R0, #0x93")
        b.insn("BEQ", "p93j")
        b.insn("CMP", "R0, #0x94")
        b.insn("BEQ", "p94j")
        b.insn("B", "stop")
        b.label("p92j")
        b.insn("B", "p92")
        b.label("p93j")
        b.insn("B", "p93")
        b.label("p94j")
        b.insn("B", "p94")
        b.label("p80")
        b.call_addr(OPEN, R5, 0x80, via=R3)
        b.call_addr(helpp, R6, 0, 0, via=R3)
        b.insn("ADD", "R7, R0, #0x0")
        b.call_addr(helpp, R6, 1, 0, via=R3)
        b.insn("CMP", "R7, #0x0")
        b.insn("BEQ", "onlyfield")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "onlyhand")
        b.insn("MOV", "R0, #0x0")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("MOV", "R0, #0x3")
        b.insn("STR", "R0, [SP, #0x8]")
        b.call_addr(PROMPT, R5, TITLE, LBL_HAND, LBL_FIELD, via=R7)
        b.insn("MOV", "R0, #0x90")
        b.insn("B", "ret")
        b.label("onlyfield")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "abortj")
        b.insn("MOV", "R0, #0x1")
        b.insn("B", "setans")
        b.label("onlyhand")
        b.insn("MOV", "R0, #0x0")
        b.label("setans")
        b.insn("STRH", "R0, [R5, #0x18]")
        b.insn("MOV", "R0, #0x91")
        b.insn("B", "ret")
        b.label("p90")
        b.ldr_const(0, CHOICE_STATE)
        b.insn("LDR", "R0, [R0, #0x34]")
        b.insn("STRH", "R0, [R5, #0x18]")
        b.insn("MOV", "R0, #0x91")
        b.insn("B", "ret")
        b.label("p91")
        b.call_addr(MESSAGE, R6, MSG_DESTROY, via=R3)
        b.insn("MOV", "R0, #0x92")
        b.insn("B", "ret")
        b.label("abortj")
        b.insn("B", "abort")
        b.label("p92")
        b.ldr_const(1, CHOICE_STATE)
        b.insn("STR", "R6, [R1, #0x30]")
        b.insn("MOV", f"R0, #0x{PICK_CODE + 0xF:X}")
        b.insn("STR", "R0, [R1, #0x2C]")
        b.ldr_const(1, PICK_HDR)
        b.insn("STRH", "R6, [R1, #0x0]")
        b.insn("MOV", f"R0, #0x{PICK_CODE:X}")
        b.insn("STRH", "R0, [R1, #0x2]")
        b.insn("MOV", "R0, #0x0")
        b.insn("STRH", "R0, [R1, #0x4]")
        b.insn("STRH", "R0, [R1, #0x6]")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("LDRH", "R1, [R5, #0x18]")
        b.call_addr(helpp, R0, R1, 1, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "abortj")
        b.insn("LSL", "R0, R6, #0x2")
        b.ldr_const(1, CTRL_TYPE)
        b.insn("LDR", "R0, [R1, R0]")
        b.insn("CMP", "R0, #0x1")
        b.insn("BEQ", "auto")
        b.insn("CMP", "R0, #0x4")
        b.insn("BEQ", "auto")
        b.call_addr(PICK_UI, 0x37, R6, PICK_CODE, 0, via=R7)
        b.label("auto")
        b.insn("MOV", "R0, #0x93")
        b.insn("B", "ret")
        b.label("p93")
        b.ldr_const(1, PICK_HDR)
        b.insn("LDRH", "R4, [R1, #0x4]")
        b.insn("LSL", "R0, R4, #0x1")
        b.ldr_const(1, PICK_LOCS)
        b.insn("LDRH", "R0, [R1, R0]")
        b.insn("LSL", "R0, R0, #0x1A")
        b.insn("LSR", "R0, R0, #0x1B")
        b.insn("STRH", "R0, [R5, #0x1A]")
        b.insn("CMP", "R0, #0x4")
        b.insn("BGT", "handkill")
        b.ldr_const(1, FIELD_CID)
        b.insn("CMP", "R6, #0x0")
        b.insn("BEQ", "z0")
        b.ldr_const(2, STRIDE)
        b.insn("ADD", "R1, R1, R2")
        b.label("z0")
        b.insn("LSL", "R2, R0, #0x4")
        b.insn("ADD", "R1, R1, R2")
        b.insn("LSL", "R2, R0, #0x2")
        b.insn("ADD", "R1, R1, R2")
        b.insn("LDRH", "R0, [R1, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        set_level(b)
        b.insn("LDRH", "R2, [R5, #0x1A]")
        b.call_addr(DESTROY_FIELD, R5, R6, via=R3)
        b.insn("MOV", "R0, #0x94")
        b.insn("B", "ret")
        b.label("handkill")
        b.insn("LSL", "R0, R4, #0x2")
        b.ldr_const(1, PICK_WORDS)
        b.insn("LDR", "R0, [R1, R0]")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        set_level(b)
        b.insn("LDR", "R7, [SP, #0x4]")
        b.ldr_const(1, HAND_COUNT)
        b.insn("CMP", "R6, #0x0")
        b.insn("BEQ", "hk0")
        b.ldr_const(0, STRIDE)
        b.insn("ADD", "R1, R1, R0")
        b.label("hk0")
        b.insn("LDR", "R0, [R1, #0x0]")
        b.insn("STRH", "R0, [R5, #0x1C]")
        b.insn("MOV", "R4, #0x0")
        b.label("hkloop")
        b.insn("LDRH", "R0, [R5, #0x1C]")
        b.insn("CMP", "R4, R0")
        b.insn("BGE", "abort")
        b.call_addr(SLOT, R6, 0xB, R4, via=R3)
        b.insn("LDR", "R1, [R0, #0x0]")
        b.insn("CMP", "R1, R7")
        b.insn("BEQ", "hkfound")
        b.insn("ADD", "R4, #0x1")
        b.insn("B", "hkloop")
        b.label("hkfound")
        b.insn("ADD", "R2, R0, #0x0")
        b.insn("MOV", "R0, #0x0")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("LDRH", "R3, [R5, #0x0]")
        b.call_addr(DESTROY_HAND, R6, R4, via=R7)
        b.insn("MOV", "R0, #0x94")
        b.insn("B", "ret")
        b.label("p94")
        b.insn("LDRH", "R0, [R5, #0x1A]")
        b.insn("CMP", "R0, #0x4")
        b.insn("BGT", "hchk")
        b.ldr_const(1, FIELD_CID)
        b.insn("CMP", "R6, #0x0")
        b.insn("BEQ", "c0")
        b.ldr_const(2, STRIDE)
        b.insn("ADD", "R1, R1, R2")
        b.label("c0")
        b.insn("LSL", "R2, R0, #0x4")
        b.insn("ADD", "R1, R1, R2")
        b.insn("LSL", "R2, R0, #0x2")
        b.insn("ADD", "R1, R1, R2")
        b.insn("LDRH", "R0, [R1, #0x0]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "abort")
        b.insn("B", "destroyed")
        b.label("hchk")
        b.ldr_const(1, HAND_COUNT)
        b.insn("CMP", "R6, #0x0")
        b.insn("BEQ", "hc0")
        b.ldr_const(0, STRIDE)
        b.insn("ADD", "R1, R1, R0")
        b.label("hc0")
        b.insn("LDR", "R0, [R1, #0x0]")
        b.insn("LDRH", "R1, [R5, #0x1C]")
        b.insn("CMP", "R0, R1")
        b.insn("BGE", "abort")
        b.label("destroyed")
        b.call_addr(CLOSE, R5, 0x7E, via=R3)
        b.insn("MOV", "R0, #0x80")
        b.ldr_const(4, PHASE_STATE)
        b.insn("STR", "R0, [R4, #0x70]")
        b.label("addhand")
        b.call_addr(ADD_TO_HAND, R5, 0, via=R3)
        b.insn("B", "ret")
        b.label("abort")
        b.call_addr(CLOSE, R5, 0x7E, via=R3)
        b.label("stop")
        b.insn("MOV", "R0, #0x0")
        b.label("ret")
        b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
        res = b.assemble(self.res, pad="nop")
        stubs = ((self.cond, cond, "cls1 cond"), (self.slot4, slot4, "cls1 slot4"), (self.help, help_blob, "Dinosaur helper"),
                 (self.pred, pred, "deck-walker predicate"), (self.crit, crit, "criteria handler"), (self.res, res, "cls1 resolver"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        for a_ in (ADD_TO_HAND, TAG, _TURNLOG_QUERY, _TURNLOG_POST, DECK_WALKER, ROW_INDEX, SLOT, RECORD, PROMPT, MESSAGE, PICK_UI,
                   DESTROY_FIELD, DESTROY_HAND, OPEN, CLOSE, RACE_LIVE):
            assert a_ & 1, f"{a_:#x}: blx to an even literal switches to ARM state -> freeze"
        assert any(a[0] == cid for a in tch.ARMS), "the timing arm must be registered in timing_class_hook"
        phl, ph1, phc = self.phantoms
        crit_row = (cid, 0xFFFF, self.crit | 1, 0x00000006)

        def install(rom, view):
            tch.apply(view.buf)
            tch.install(rom, quiet=True)

        def check(c, rom, view):
            tch.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)

        return Compiled(stubs,
                        (Row(LIST_NS_OR_SS, (cid,), phl),
                         Row(CLS1, (cid, 0, self.res | 1, 0, self.cond | 1, self.slot4 | 1, 0), ph1),
                         Row(CRITERIA, crit_row, phc)),
                        installs=(install,), checks=(check,))



DECK_WALKER = 0x0223BC3D       # overtex_qoatlus asserts these
TYPE_ADD = 2
RACES = (20, 5, 16)            # Reptile, Sea Serpent, Winged Beast
PILLS = (0x1AA3, 0x1715, 0x1319)    # Big / Ultra / Double Evolution Pill

# Engine entry points overtex_qoatlus clones for its own Hand/Field prompt + picker (read as `A.<name>`).
PHASE_STATE, CHOICE_STATE, PLAYER_HAND_COUNT, FIELD_CID, PLAYER_STRIDE = 0x0229AAFC, 0x0229DD94, 0x0229ACA0, 0x0229ACC8, 0xB3C
SLOT, RECORD, PROMPT, MESSAGE, PICK_UI = 0x0219CA29, 0x02243B2D, 0x0219ABB5, 0x0219A819, 0x0219C99D
PICK_HDR, PICK_WORDS, PICK_LOCS, CTRL_TYPE = 0x0229944C, 0x02299458, 0x02299908, 0x0229911C
DESTROY_FIELD, DESTROY_HAND, OPEN, CLOSE = 0x021CF375, 0x021D2479, 0x021D28A5, 0x021D2965
IS_MONSTER, RACE_PRINTED, RACE_LIVE = 0x02029E61, 0x0202ABB9, 0x021B88F1
TITLE, LBL_HAND, LBL_FIELD, MSG_DESTROY, PICK_CODE = 0x103, 0x192, 0x23C, 0x6D, 6

SPEC = card(
    0x1297,
    summoned_destroy_dinosaur_add_same_level_monster_or_named_spell_once_per_turn(
        res=ov5_cave.CAVE_ARCH_RES, cond=ov5_cave.CAVE_ARCH_COND, slot4=ov5_cave.CAVE_ARCH_SLOT4, help=ov5_cave.CAVE_ARCH_HELP,
        pred=ov5_cave.CAVE_ARCH_PRED, crit=ov5_cave.CAVE_ARCH_CRIT, races=RACES, pills=PILLS,
        phantoms=(0x0E77, 0x12A6, 0x0EAE)))

PROPS = card_props("LIGHT", "Dinosaur", level=1, atk=0, defense=0)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_animadorned_archosaur.nds")


def pred_stub(base: int) -> bytes:     # overtex_qoatlus builds this to compare against its own copy
    return deck_walker_race_or_named_spell_pred(base, RACES, PILLS)


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
