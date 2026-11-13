"""Shooting Quasar Dragon (LIGHT / Dragon / Synchro Effect Monster / Level 12 / 4000 / 4000) on Stardust Dragon 0x211B.

    (See card_text.CARD_TEXT[0x211B] for the full printed text.)
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import (card, card_props,
                              synchro_materials_synchro_only_attack_twice_negate_activation_and_destroy_it_once_per_turn_revive_shooting_star_dragon_on_leave
                              as shooting_quasar_effects)

SPEC = card(0x211B, shooting_quasar_effects())

PROPS = card_props("LIGHT", "Dragon", level=12, atk=4000, defense=4000, card_type="Synchro Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_shooting_quasar.nds")

DONOR_CID = 0x211B          # Stardust Dragon -- KEEPS this cid

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
