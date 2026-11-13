"""Elder of the Six Samurai (EARTH / Warrior / Level 3 / 400 / 0) on Flame Cerebrus 0x11B7.

    "If your opponent controls a monster and you control no monsters, you can Special Summon this card (from your
     hand)."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import (SetCodeTable, archetype_member, card, card_props, only_opponent_controls_monster,
                              special_summon_self_from_hand)
from otn_enhanced.effects import cave3

SIX_SAMURAI_TABLE = SetCodeTable("Six Samurai", 0x0209CA8C, 0x12, (0x02023A38, 0x02023A48), (0x02023A1C, 0x02023A44))

SPEC = card(
    0x11B7,
    special_summon_self_from_hand(when=only_opponent_controls_monster(), slot=cave3.CAVE3_ELDER_SSCOND),
    archetype_member(SIX_SAMURAI_TABLE, phantom=0x251B))

PROPS = card_props("EARTH", "Warrior", level=3, atk=400, defense=0)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_elder_six_samurai.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
