"""Reborn Tengu (WIND / Beast-Warrior / Level 4 / 1700 / 600 / Effect Monster) on The Portrait's Secret 0x1463.

    "If this face-up card leaves the field: Special Summon 1 "Reborn Tengu" from your Deck."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card_props, CLS2, CRITERIA, Compiled, LEAVE_MASK, LIST_106, LIST_30, Row, _DECK_SEARCHER
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass


_MASK_LEAVES_FIELD = 0x000C           # face-up (0x0008) + left the field (0x0004)


_LEAVE_RESOLVER = 0x02206F41          # leave -> deck-SS state machine (cls2 +04)


_LEAVE_CONDITION = 0x021F0419         # can-I-Special-Summon: stops a MANDATORY trigger fizzling (cls2 +0C)


_SELF_FROM_DECK_HANDLER = 0x0223D075  # native ov3 criteria handler: Deck searcher + "same card as self" filter


_SELF_FROM_DECK_FILTER_LIT = 0x0223D09C


_SELF_FROM_DECK_BL = 0x0223D094


_YUBEL_FILTER = 0x0223C6F1


_CRIT_SELF_FROM_DECK_WORD = 0x00000802


@dataclass(frozen=True)
class leave_field_special_summon_self_from_deck:
    """'If this face-up card leaves the field: Special Summon 1 "<this card>" from your Deck' -- mandatory.
    Leave-mask row {face-up + left the field} + cls2 record (+10 == 0 => MANDATORY) + a criteria row whose
    handler is the native Deck self-search. The donor must be in neither list30 nor list106 (either arms
    the dispatcher first and the mask table is skipped). `phantoms` = (mask, cls2, criteria) cids dropped."""
    cid: int
    phantoms: tuple[int, int, int]

    def compile(self, view) -> Compiled:
        assert self.cid not in view.keys(LIST_30.base, count=LIST_30.count, stride=2), "donor is in list30"
        assert self.cid not in view.keys(LIST_106.base, count=LIST_106.count, stride=2), "donor is in list106"
        assert (view.u32(_SELF_FROM_DECK_FILTER_LIT) == _YUBEL_FILTER
                and view.blob(_SELF_FROM_DECK_BL, 4) == common_bl(_SELF_FROM_DECK_BL, _DECK_SEARCHER)), (
            "native handler is not the Deck/self-filter selector")
        pm, p2, pc = self.phantoms
        return Compiled((), (
            Row(LEAVE_MASK, (self.cid, _MASK_LEAVES_FIELD), pm),
            Row(CLS2, (self.cid, 0, _LEAVE_RESOLVER, 0, _LEAVE_CONDITION, 0, 0), p2),
            Row(CRITERIA, (self.cid, self.cid, _SELF_FROM_DECK_HANDLER, _CRIT_SELF_FROM_DECK_WORD), pc)))



SPEC = leave_field_special_summon_self_from_deck(0x1463, phantoms=(0x14E9, 0x14E9, 0x1452))

PROPS = card_props("WIND", "Beast-Warrior", level=4, atk=1700, defense=600)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_reborn_tengu.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
