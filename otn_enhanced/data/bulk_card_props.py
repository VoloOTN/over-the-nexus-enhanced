from otn_enhanced.dsl import apply_card_stat_edits, card_stat_edit as edit, verify_card_stat_edits

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_test.nds"

# Reference cards for copying genre records
REFERENCE_NORMAL_SPELL_CID = 0x12E3  # Fissure
REFERENCE_QUICKPLAY_SPELL_CID = 0x132D # MST
REFERENCE_CONTINUOUS_SPELL_CID = 0x132C # Chain Energy
REFERENCE_FIELD_SPELL_CID = 0x10F0 # Forest
REFERENCE_EQUIP_SPELL_CID = 0x10D6 # Axe of Despair
REFERENCE_NORMAL_TRAP_CID = 0x12E4 # Trap Hole
REFERENCE_CONTINUOUS_TRAP_CID = 0x12F3 # Ultimate Offering
REFERENCE_COUNTER_TRAP_CID = 0x1300 # Horn of Heaven

QUICKPLAY = REFERENCE_QUICKPLAY_SPELL_CID

EDITS = (
    edit(0x20B8, atk_encoded=195),                                          # Beast Striker
    # edit(0x1F7A, copy_from=QUICKPLAY),                                      # Assault Mode Activate
    edit(0x24B9, copy_from=QUICKPLAY),                                      # Means of Infestation
    edit(0x23E3, copy_from=QUICKPLAY),                                      # Infestation Wave
    edit(0x24B8, copy_from=QUICKPLAY),                                      # Infestation Ripples
    edit(0x16F7, def_encoded=20, race="Zombie"),                            # Molten Zombie
    edit(0x17C7, level=8),                                                  # Andro Sphinx
    edit(0x17C8, level=8),                                                  # Sphinx Teleia
    edit(0x17C9, level=8),                                                  # Theinen the Great Sphinx
    edit(0x22F5, atk_encoded=190),                                          # Hypnocorn
    edit(0x217D, level=5),                                                  # General Raiho
    edit(0x20D6, level=7),                                                  # General Grunard
    edit(0x16A4, copy_from=QUICKPLAY),                                      # Archfiend's Roar
    edit(0x18F4, level=4),                                                  # UFOroid
    edit(0x1291, atk_encoded=180, attribute_encoded=1),                     # Gazelle the King of Mythical Beasts
    edit(0x1293, level=4),                                                  # Berformet
    edit(0x1294, level=5),                                                  # Chimera the Flying Mythical Beast
    edit(0x1DB3, level=4, atk_encoded=130),                                 # Batteryman Charger
    edit(0x24B7, copy_from=QUICKPLAY),                                      # Pyroxene Fusion
    edit(0x22D9, copy_from=QUICKPLAY),                                      # Gem-Enhancement
    edit(0x12BE, copy_from=REFERENCE_FIELD_SPELL_CID),                      # Toon World
    edit(0x1B2A, race="Beast", level=2), # PB Cross-Wing
    edit(0x1B2D, race="Beast"), # PB Rock-Lizard
    edit(0x1B2C, race="Beast", level=2), # PB Thunder Pegasus
    edit(0x1B2B, race="Beast"), # PB Wild Horn
    edit(0x22F1, level=2), # Mine Mole
    edit(0x174A, level=3),
    edit(0x1723, level=4)
)


def main(src: str = SRC, out: str = OUT) -> None:
    apply_card_stat_edits(EDITS, src=src, out=out)


def verify(out: str = OUT) -> bool:
    return verify_card_stat_edits(EDITS, out)


if __name__ == "__main__":
    main()
