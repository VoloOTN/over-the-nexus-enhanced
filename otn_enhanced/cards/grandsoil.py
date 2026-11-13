"""Grandsoil the Elemental Lord (EARTH / Beast-Warrior / Level 8 / 2800 / 2200) on Millennium Shield 0x1110.

    "Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 EARTH monsters
     in your GY. When this card is Special Summoned: You can target 1 monster in either player's GY; Special
     Summon that target. You can only use this effect of "Grandsoil the Elemental Lord" once per turn. If this
     face-up card leaves the field, skip the Battle Phase of your next turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import ELEMENTAL_LORD_CIDS, NOMI_CLASS_2_TABLE, archetype_member, card, card_props, hand_special_summon_by_gy_attribute, leave_field_skip_next_battle_phase, CLS1, CRITERIA, Compiled, LIST_NS_OR_SS, Row, _HOPT_KIND, _NATIVE_OFFER_COND, _hopt_you_can_stub, _timing_arms_check, _timing_arms_install
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import rows


@dataclass(frozen=True)
class revive_either_gy_once_per_turn:
    """'When this card is Special Summoned: You can target 1 monster in either player's GY; Special Summon that
    target. Once per turn.' N-or-SS list membership + a cls1 record cloned from `template` (Junk Synchron's) with
    +0C / +10 wrapped in ov5 (Souleating Oviraptor's confirmed HOPT shape): +0C = turn log (side, 0xB, cid, 1) clear,
    then the native offer gate; +10 = 'You can' 0x021E51E5, on Yes post (side, cid, 1, 0) -- declining is free. The
    criteria row is `reborn`'s (either GY, target comes to YOUR side). The class-2 'You can' timing arm for this cid
    lives in the SHARED timing_class_hook.ARMS (+ its ov3 hook and ov5 stub, installed here idempotently)."""
    template: int
    template_cls1: tuple          # the template's whole cls1 record, asserted
    reborn: tuple                 # Monster Reborn's whole criteria row, asserted
    slots: tuple[int, int]        # (+0C cond, +10 slot4), ov5
    phantoms: tuple[int, int, int]  # (N-or-SS list, cls1, criteria)

    def compile(self, view, cid) -> Compiled:
        ph_list, ph1, phc = self.phantoms
        cond, slot4 = self.slots
        assert self.template_cls1 in rows(view, CLS1), "cls1 template changed"
        assert self.reborn in rows(view, CRITERIA), "criteria template changed"
        res = self.template_cls1[2]
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.turnlog_query(R0, cid, _HOPT_KIND, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "used")
        b.call_addr(_NATIVE_OFFER_COND, R5, via=R4)
        b.insn("POP", "{R4, R5, PC}")
        b.label("used")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, PC}")
        cb = b.assemble(cond, pad="nop")
        sb = _hopt_you_can_stub(slot4, cid)
        assert_thumb1_only(cb, cond)
        return Compiled(((cond, cb, "+0C cond"), (slot4, sb, "+10 slot4")),
                        (Row(LIST_NS_OR_SS, (cid,), ph_list),
                         Row(CLS1, (cid, 0, res, 0, cond | 1, slot4 | 1, self.template_cls1[6]), ph1),
                         Row(CRITERIA, (cid,) + self.reborn[1:], phc)),
                        installs=(_timing_arms_install,), checks=(_timing_arms_check,))



SPEC = card(
    0x1110,
    archetype_member(NOMI_CLASS_2_TABLE, 0x0E63),
    hand_special_summon_by_gy_attribute(attribute=5, count=5, slot=ov5_cave.CAVE_GS_SSCOND),
    revive_either_gy_once_per_turn(
        template=0x1E07,                                                   # Junk Synchron
        template_cls1=(0x1E07, 0, 0x02207191, 0, 0x021F03B5, 0x021E51E5, 0x02235605),
        reborn=(0x12EA, 0xFFFF, 0x0223D6E1, 0x00010002),                   # Monster Reborn
        slots=(ov5_cave.CAVE_GS_COND, ov5_cave.CAVE_GS_SLOT4),
        phantoms=(0x1B6B, 0x0E5D, 0x0E94)),
    leave_field_skip_next_battle_phase(ELEMENTAL_LORD_CIDS))

PROPS = card_props("EARTH", "Beast-Warrior", level=8, atk=2800, defense=2200)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_grandsoil.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
