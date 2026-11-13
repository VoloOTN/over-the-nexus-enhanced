"""Moulinglacia the Elemental Lord (WATER / Sea Serpent / Level 8 / 2800 / 2200) on Venom Cobra 0x1C1A.

    "Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 WATER monsters
     in your GY. If this card is Special Summoned: Discard 2 random cards from your opponent's hand (or their
     entire hand, if less than 2). You can only use this effect of "Moulinglacia the Elemental Lord" once per
     turn. If this face-up card leaves the field, skip the Battle Phase of your next turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import ELEMENTAL_LORD_CIDS, NOMI_CLASS_2_TABLE, archetype_member, card, card_props, hand_special_summon_by_gy_attribute, leave_field_skip_next_battle_phase, CLS1, Compiled, LIST_NS_OR_SS, Row, _HOPT_KIND
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass


_DISCARD_RANDOM, _HAND_COUNT = 0x022599C9, 0x0229ACA0


@dataclass(frozen=True)
class discard_random_opponent_cards_once_per_turn:
    """'If this card is Special Summoned: Discard N random cards from your opponent's hand (or their entire hand, if
    less than N). Once per turn.' cls1 shape = Fortune Lady Water / Thestalos: +10 == 0 (timing class 0: mandatory, no
    timing arm), +0C a real condition (turn log clear -> 2, else 0). Discard = Don Zaloog's call
    0x022599C8(1 - desc[2], 1, n) in one phase, return 0; clamp = Wiraqocha Rasca's (hand count word
    [0x0229ACA0 + opp * 0xB3C]; opp is 0/1, so a branch, not a mul). USER RULING: an empty opponent hand still
    activates and spends the HOPT, so the turn log is posted BEFORE the n == 0 skip."""
    count: int
    slots: tuple[int, int]            # (res, cond), ov5
    phantoms: tuple[int, int]         # (N-or-SS list, cls1)

    def compile(self, view, cid) -> Compiled:
        res, cond = self.slots
        ph_list, ph1 = self.phantoms
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_post(R0, cid, _HOPT_KIND, via=R5)
        b.insn("LDRB", "R1, [R4, #0x2]")
        b.insn("MOV", "R0, #0x1")
        b.insn("SUB", "R5, R0, R1")
        b.insn("AND", "R5, R0")
        b.insn("MOV", "R3, #0x0")
        b.insn("CMP", "R5, #0x0")
        b.insn("BEQ", "side0")
        b.ldr_const(3, 0xB3C)
        b.label("side0")
        b.ldr_const(0, _HAND_COUNT)
        b.insn("LDR", "R2, [R0, R3]")
        b.insn("CMP", f"R2, #0x{self.count:X}")
        b.insn("BLE", "clamped")
        b.insn("MOV", f"R2, #0x{self.count:X}")
        b.label("clamped")
        b.insn("CMP", "R2, #0x0")
        b.insn("BEQ", "out")
        b.call_addr(_DISCARD_RANDOM, R5, 1, via=R3)
        b.label("out")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        rb = b.assemble(res, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("LDRB", "R0, [R0, #0x2]")
        b.turnlog_query(R0, cid, _HOPT_KIND, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "used")
        b.insn("MOV", "R0, #0x2")
        b.insn("POP", "{R4, PC}")
        b.label("used")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        cb = b.assemble(cond, pad="nop")
        for blob, addr in ((rb, res), (cb, cond)):
            assert_thumb1_only(blob, addr)
        return Compiled(((res, rb, "+04 resolver"), (cond, cb, "+0C cond")),
                        (Row(LIST_NS_OR_SS, (cid,), ph_list),
                         Row(CLS1, (cid, 0, res | 1, 0, cond | 1, 0, 0), ph1)))



SPEC = card(
    0x1C1A,
    archetype_member(NOMI_CLASS_2_TABLE, 0x0EB3),
    hand_special_summon_by_gy_attribute(attribute=3, count=5, slot=ov5_cave.CAVE_ML_SSCOND),
    discard_random_opponent_cards_once_per_turn(
        count=2, slots=(ov5_cave.CAVE_ML_RES, ov5_cave.CAVE_ML_COND), phantoms=(0x0E17, 0x1C5F)),
    leave_field_skip_next_battle_phase(ELEMENTAL_LORD_CIDS))

PROPS = card_props("WATER", "Sea Serpent", level=8, atk=2800, defense=2200)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_moulinglacia.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
