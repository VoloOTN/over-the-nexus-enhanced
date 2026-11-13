"""T.G. Striker (EARTH / Warrior / Tuner / Level 2 / 800 / 0) on Ally Mind 0x1F18.

    "If only your opponent controls a monster, you can Special Summon this card (from your hand).
     Once per turn, during the End Phase, if this card is in the GY because it was destroyed on the
     field and sent there this turn: You can add 1 "T.G." monster from your Deck to your hand,
     except "T.G. Striker"."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import (TG_SETCODE, TG_TABLE,add_from_deck_end_phase, archetype_member, card, card_props,
                              only_opponent_controls_monster, special_summon_self_from_hand)
from otn_enhanced.effects import cave3

SPEC = card(
    0x1F18,
    special_summon_self_from_hand(when=only_opponent_controls_monster(), slot=cave3.CAVE3_TGS_COND),
    add_from_deck_end_phase(set_code=TG_SETCODE, except_self=True,
                            slots=(cave3.CAVE3_TGS_FILTER, cave3.CAVE3_TGS_WRAPPER),
                            phantoms=(0x2347, 0x234E), populate_stock_copies=2),
    archetype_member(TG_TABLE, phantom=0x2510))

PROPS = card_props("EARTH", "Warrior", level=2, atk=800, defense=0, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_tg_striker.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
