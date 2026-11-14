"""Printed card text for every patched card, per language.

THE ONE PLACE CARD NAMES AND DESCRIPTIONS LIVE. `_build_card_text.py` reads this
and re-emits card_name_<L>.bin / card_desc_<L>.bin IN INDEX ORDER, so every
card_indx entry's gap stays equal to its own 4-aligned length.

*** DO NOT APPEND A STRING PAST THE END OF A BLOB. *** The deck editor derives
its description read length from the gap to the NEXT index entry. Appending
makes that gap negative; on 2026-09-08 a -779,884 gap on Lightpulsar dumped
~39.6 KB of raw bin2.pac over a NitroSDK thread control block at 0x02128E58 and
hard-froze the ARM9 in the data-abort handler. Always re-emit in index order.
(notes/card-text-blob-findings.md has the full teardown.)

TO ADD A TRANSLATION: replace the `None` for that language with
`("<name>", "<description>")`. `None` means "use English". Text is `str` and is
encoded with ENCODING[lang]; pass `bytes` instead to bypass encoding entirely.

LANGUAGE CODES -- note the last two, which are NOT what the suffix suggests:
  e English   f French   g German   i Italian   s Spanish   j Japanese
  k Korean
  r *** JAPANESE WITH RUBY ***, not Russian. card_name_r.bin holds cp932 text
    with $R<kanji>(<furigana>) markup -- e.g. entry 254 is
    "$R\u5263\u9f8d(\u30bd\u30fc\u30c9\u30fb\u30c9\u30e9\u30b4\u30f3)".
    Measured 2026-09-08; the file suffix is a red herring.

English text is quoted verbatim from scratch/ygoprodeck_cache.json (modern
wording: "GY", "banishing"). The ROM era says "Graveyard" / "removed from play";
edit here if era-accurate wording is wanted.
"""
from __future__ import annotations

LANGS = ('e', 'f', 'g', 'i', 's', 'j', 'k', 'r')

# Measured by round-tripping every stock name blob.
ENCODING = {
    "e":  'latin-1',
    "f":  'latin-1',
    "g":  'latin-1',
    "i":  'latin-1',
    "s":  'latin-1',
    "j":  'cp932',
    "k":  'cp949',
    "r":  'cp932',
}

# Proven by the stock ROM: Russian-slot (ruby-Japanese) ships a 1196 B
# description and a 110 B name, so the render buffers hold at least that.
MAX_NAME, MAX_DESC = 110, 1196

# Monarchic Perfection for the cp932 / cp949 tables: same English text, but their encodings have no \x9d, so the bullets are ● (Horn of Olifant's "j" convention).
PERFECTION_CJK = ("Monarchic Perfection",
                  "Once per Chain, if your opponent Special Summons a monster(s), and you control a Tribute Summoned monster (except during the Damage Step): You can banish 1 \"Monarch\" Spell/Trap from your GY, then activate 1 of these effects (but you can only use each effect of \"Monarchic Perfection\" once per turn);\r\n●Destroy 1 monster on the field.\r\n●Destroy up to 2 Spells/Traps on the field.\r\n●Discard 1 random card from your opponent's hand.\r\n●Destroy 1 face-down card on the field.\r\n●Place 1 card from the field on top of the Deck.\r\n●Banish 1 card on the field.")

# donor cid -> {lang: (name, desc) | None}.  None falls back to English.
CARD_TEXT: dict[int, dict[str, tuple[str, str] | bytes | None]] = {
    0x0FA9: {  # tg_warwolf -- T.G. Warwolf
        "e": ('T.G. Warwolf',
             'When a Level 4 or lower monster(s) is Special Summoned (except during the Damage Step): You can Special Summon this card from your hand. Once per turn, during the End Phase, if this card is in the GY because it was destroyed on the field and sent there this turn: You can add 1 "T.G." monster from your Deck to your hand, except "T.G. Warwolf".'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FB1: {  # lightpulsar -- Lightpulsar Dragon
        "e": ('Lightpulsar Dragon',
             'You can Special Summon this card (from your hand) by banishing 1 LIGHT and 1 DARK monster from your GY. You can Special Summon this card (from your GY) by sending 1 LIGHT and 1 DARK monster from your hand to the GY. When this card is sent from the field to the GY: You can target 1 Level 5 or higher DARK Dragon monster in your GY; Special Summon that target.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FCB: {  # orient_dragon -- Orient Dragon
        "e": ('Orient Dragon',
             '1 Tuner + 1 or more non-Tuner monsters If this card is Synchro Summoned: Target 1 Synchro Monster your opponent controls; banish that target.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FEC: {  # thunder_sea_horse -- Thunder Sea Horse (donor Fiend Kraken, re-homed off Thunder Dragon 0x114F)
        "e": ('Thunder Sea Horse',
             'You can discard this card; add 2 Level 4 LIGHT Thunder-Type monsters of the same name with 1600 or less ATK from your Deck to your hand. You can only use the effect of "Thunder Sea Horse" once per turn. You cannot Special Summon during the turn you activate this effect.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FF6: {  # scrap_raptor -- Scrap Raptor (donor Uraby
        # The donor's name slot is 5 B ("Uraby") and "Scrap Raptor" is 12 B, so this
        # cid MUST be here: the INDEX-ORDER RE-EMIT path has no slot limit, whereas
        # the in-place path would silently keep "Uraby" in every language.
        # /!\ The printed text below is the FULL card. The ROM does not implement the
        # '"Scrap Factory" or' half of the second effect -- Scrap Factory exists in
        # neither the NDS nor the 3DS build. USER-APPROVED DEVIATION, so
        # the text is written to match what the ROM ACTUALLY DOES, per the
        # vylon_element precedent (describe the implementation, not the wish).
        "e": ('Scrap Raptor',
             'You can target 1 monster you control; destroy it, also, during your Main Phase this turn, you can Normal Summon 1 "Scrap" monster in addition to your Normal Summon/Set. If this card is destroyed by the effect of a "Scrap" card and sent to your GY: You can add 1 non-Tuner "Scrap" monster from your Deck to your hand. You can only use each effect of "Scrap Raptor" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FD2: {  # raiden -- Raiden, Hand of the Lightsworn (donor Rogue Doll
               # donor slots are 10 B / 40 B floor, hence CARD_TEXT
        "e": ('Raiden, Hand of the Lightsworn',
             'During your Main Phase: You can send the top 2 cards of your Deck to the GY, then if any "Lightsworn" monsters were sent to the GY by this effect, this card gains 200 ATK until the end of your opponent\'s turn. You can only use this effect of "Raiden, Hand of the Lightsworn" once per turn. Once per turn, during your End Phase: Send the top 2 cards of your Deck to the GY.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FC8: {  # karakuri_haipa -- Karakuri Muso mdl 818 "Haipa"
        "e": ('Karakuri Muso mdl 818 "Haipa"',
             'This card must attack if able. When this face-up Attack Position card is selected as an attack target, change it to Defense Position. If this card attacks, it is changed to Defense Position at the end of the Battle Phase.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x11B7: {  # elder_six_samurai -- Elder of the Six Samurai (donor Flame Cerebrus,
               # re-donored off AoJ Cosmic Gateway 0x1F1D; native name/desc slots
               # are too small (14B/50B floor) for the printed text, hence CARD_TEXT)
        "e": ('Elder of the Six Samurai',
             'If your opponent controls a monster and you control no monsters, you can Special Summon this card (from your hand).'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FD7: {  # mega_monarch -- Granmarg the Mega Monarch (donor Big Insect; M0 only built, E1/E2 pending)
        "e": ('Granmarg the Mega Monarch',
             'You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. When this card is Tribute Summoned: Target up to 2 Set cards on the field; destroy those targets. If this card was Tribute Summoned by Tributing an EARTH monster, add this additional effect.\r\n\x9dAlso, draw 1 card after that.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ('Granmarg the Mega Monarch',
             'You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. When this card is Tribute Summoned: Target up to 2 Set cards on the field; destroy those targets. If this card was Tribute Summoned by Tributing an EARTH monster, add this additional effect.\r\n\u25cfAlso, draw 1 card after that.'),
        "k": ('Granmarg the Mega Monarch',
             'You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. When this card is Tribute Summoned: Target up to 2 Set cards on the field; destroy those targets. If this card was Tribute Summoned by Tributing an EARTH monster, add this additional effect.\r\n\u25cfAlso, draw 1 card after that.'),
        "r": ('Granmarg the Mega Monarch',
             'You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. When this card is Tribute Summoned: Target up to 2 Set cards on the field; destroy those targets. If this card was Tribute Summoned by Tributing an EARTH monster, add this additional effect.\r\n\u25cfAlso, draw 1 card after that.'),
    },
    0x0FF3: {  # mega_monarch -- Mobius the Mega Monarch (donor Grappler; M0 + E1 built, E2 response lock NOT built)
        "e": ("Mobius the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. When this card is Tribute Summoned: You can target up to 3 Spell/Trap Cards on the field; destroy those targets. If this card was Tribute Summoned by Tributing a WATER monster, add this additional effect.\r\n\x9dYour opponent cannot activate the targeted cards in response to this effect's activation."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ("Mobius the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. When this card is Tribute Summoned: You can target up to 3 Spell/Trap Cards on the field; destroy those targets. If this card was Tribute Summoned by Tributing a WATER monster, add this additional effect.\r\n\u25cfYour opponent cannot activate the targeted cards in response to this effect's activation."),
        "k": ("Mobius the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. When this card is Tribute Summoned: You can target up to 3 Spell/Trap Cards on the field; destroy those targets. If this card was Tribute Summoned by Tributing a WATER monster, add this additional effect.\r\n\u25cfYour opponent cannot activate the targeted cards in response to this effect's activation."),
        "r": ("Mobius the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. When this card is Tribute Summoned: You can target up to 3 Spell/Trap Cards on the field; destroy those targets. If this card was Tribute Summoned by Tributing a WATER monster, add this additional effect.\r\n\u25cfYour opponent cannot activate the targeted cards in response to this effect's activation."),
    },
    0x139B: {  # mega_monarch -- Zaborg the Mega Monarch (donor The Illusory Gentleman; M0 + destroy + LIGHT Extra Deck send BUILT WITHOUT player choice)
        "e": ("Zaborg the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 monster on the field; destroy it, then, if it was a LIGHT monster, both players send as many cards as possible from their Extra Deck to the GY, but not more than the original Level/Rank of that destroyed monster. If this card was Tribute Summoned by Tributing a LIGHT monster, add this additional effect.\r\n\x9dYou choose the cards your opponent sends to the GY."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ("Zaborg the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 monster on the field; destroy it, then, if it was a LIGHT monster, both players send as many cards as possible from their Extra Deck to the GY, but not more than the original Level/Rank of that destroyed monster. If this card was Tribute Summoned by Tributing a LIGHT monster, add this additional effect.\r\n\u25cfYou choose the cards your opponent sends to the GY."),
        "k": ("Zaborg the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 monster on the field; destroy it, then, if it was a LIGHT monster, both players send as many cards as possible from their Extra Deck to the GY, but not more than the original Level/Rank of that destroyed monster. If this card was Tribute Summoned by Tributing a LIGHT monster, add this additional effect.\r\n\u25cfYou choose the cards your opponent sends to the GY."),
        "r": ("Zaborg the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 monster on the field; destroy it, then, if it was a LIGHT monster, both players send as many cards as possible from their Extra Deck to the GY, but not more than the original Level/Rank of that destroyed monster. If this card was Tribute Summoned by Tributing a LIGHT monster, add this additional effect.\r\n\u25cfYou choose the cards your opponent sends to the GY."),
    },
    0x1E87: {  # mega_monarch -- Raiza the Mega Monarch (donor Mist Valley Watcher; picks at RESOLUTION, order fixed, WIND card not optional)
        "e": ("Raiza the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 card on the field and 1 card in either player's Graveyard, also if this card was Tribute Summoned by Tributing a WIND monster, you can target an additional card on the field; place the first target(s) on the top of the Deck in any order, also, after that, return the additional target (if any) to the hand."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ("Raiza the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 card on the field and 1 card in either player's Graveyard, also if this card was Tribute Summoned by Tributing a WIND monster, you can target an additional card on the field; place the first target(s) on the top of the Deck in any order, also, after that, return the additional target (if any) to the hand."),
        "k": ("Raiza the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 card on the field and 1 card in either player's Graveyard, also if this card was Tribute Summoned by Tributing a WIND monster, you can target an additional card on the field; place the first target(s) on the top of the Deck in any order, also, after that, return the additional target (if any) to the hand."),
        "r": ("Raiza the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 card on the field and 1 card in either player's Graveyard, also if this card was Tribute Summoned by Tributing a WIND monster, you can target an additional card on the field; place the first target(s) on the top of the Deck in any order, also, after that, return the additional target (if any) to the hand."),
    },
    0x0FC5: {  # mega_monarch -- Caius the Mega Monarch (donor Koumori Dragon; 2nd card chosen at resolution)
        "e": ("Caius the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 card on the field; banish it, and if you do, inflict 1000 damage to your opponent, then, if it is a DARK Monster Card, banish all cards with that name from the hand, Main Deck, Extra Deck, and GY of the player who controlled it. If this card was Tribute Summoned by Tributing a DARK monster, add this additional effect.\r\n\x9dYou can target 2 cards, instead."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ("Caius the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 card on the field; banish it, and if you do, inflict 1000 damage to your opponent, then, if it is a DARK Monster Card, banish all cards with that name from the hand, Main Deck, Extra Deck, and GY of the player who controlled it. If this card was Tribute Summoned by Tributing a DARK monster, add this additional effect.\r\n\u25cfYou can target 2 cards, instead."),
        "k": ("Caius the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 card on the field; banish it, and if you do, inflict 1000 damage to your opponent, then, if it is a DARK Monster Card, banish all cards with that name from the hand, Main Deck, Extra Deck, and GY of the player who controlled it. If this card was Tribute Summoned by Tributing a DARK monster, add this additional effect.\r\n\u25cfYou can target 2 cards, instead."),
        "r": ("Caius the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Target 1 card on the field; banish it, and if you do, inflict 1000 damage to your opponent, then, if it is a DARK Monster Card, banish all cards with that name from the hand, Main Deck, Extra Deck, and GY of the player who controlled it. If this card was Tribute Summoned by Tributing a DARK monster, add this additional effect.\r\n\u25cfYou can target 2 cards, instead."),
    },
    0x15EC: {  # march -- March of the Monarchs (donor Kishido Spirit; the Extra Deck Special Summon lock is NOT built)
        "e": ("March of the Monarchs",
             "Tribute Summoned monsters you control cannot be targeted by, or destroyed by, card effects. You cannot Special Summon monsters from the Extra Deck."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x10F3: {  # domain -- Domain of the True Monarchs (donor Sogen)
        "e": ("Domain of the True Monarchs",
             "While you have no cards in your Extra Deck and you are the only player that controls a Tribute Summoned monster, your opponent cannot Special Summon monsters from the Extra Deck. If a Tribute Summoned monster you control attacks an opponent's monster, it gains 800 ATK during damage calculation only. Once per turn: You can reduce the Level of 1 monster with 2800 ATK and 1000 DEF in your hand by 2 until the end of this turn (even after they are Summoned/Set, and even if this card leaves the field)."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0DE4: {  # strike -- Strike of the Monarchs (donor Speed Spell - Offerings to the Doomed)
        "e": ("Strike of the Monarchs",
             "You can Tribute 1 face-up Level 5 or higher Normal Summoned/Set monster, then target 1 face-up card on the field; negate its effects, then draw 1 card. (The effects remain negated until the end of this turn.) During your Main Phase, if this card is in your Graveyard: You can banish this card, then declare 1 Attribute; all face-up monsters currently on the field become that Attribute until the end of this turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x135E: {  # erupt -- The Monarchs Erupt (donor Respect Play; E3 End-Phase self-send NOT built)
        "e": ("The Monarchs Erupt",
             "Activate this card only if you have no cards in your Extra Deck and control a Tribute Summoned monster. Negate the effects of all face-up monsters on the field, while those monsters are face-up on the field, except Tribute Summoned monsters'. During your End Phase, if you control no Tribute Summoned monsters, send this card to the Graveyard."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0D6A: {  # masterplan -- The Monarchs Masterplan (donor Speed Spell - Faustian Bargain)
        "e": ("The Monarchs Masterplan",
             "Send 1 \"Monarch\" Spell/Trap from your Deck to the GY, except \"The Monarchs Masterplan\". If this card is banished: You can target 1 face-up monster your opponent controls; add 1 monster with the same Attribute that has 2400 ATK/1000 DEF, from your Deck or GY to your hand, then you can apply this effect. * Immediately after this effect resolves, Normal Summon 1 \"Zaborg the Thunder Monarch\", \"Mobius the Frost Monarch\", \"Thestalos the Firestorm Monarch\", \"Granmarg the Rock Monarch\", \"Raiza the Storm Monarch\", or \"Caius the Shadow Monarch\". You can only use this effect of \"The Monarchs Masterplan\" once per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1230: {  # eidos_monarch -- Eidos the Underworld Monarch (donor Whiptail Crow)
        "e": ("Eidos the Underworld Monarch",
             "If this card is Normal or Special Summoned: You can add 1 \"Monarch\" Spell/Trap or 1 monster with 2800 ATK/1000 DEF from your Deck or GY to your hand. You can declare 1 Attribute; make 1 face-up monster on the field become that Attribute. If you Tribute Summon a monster with 2400 or more ATK and 1000 DEF, while this card is in your GY: You can add this card to your hand or Special Summon it. You can only use each effect of \"Eidos the Underworld Monarch\" once per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1123: {  # tessera -- Tessera the Primal Squire (donor Toon Alligator)
        "e": ("Tessera the Primal Squire",
             "You can reveal 1 \"Monarch\" Spell/Trap in your hand; Special Summon this card from your hand. During your Main Phase, you can: Immediately after this effect resolves, Tribute Summon 1 monster. If this card is sent to the GY: You can Special Summon 1 monster with 800 ATK/1000 DEF from your Deck, also you cannot Special Summon from the Extra Deck for the rest of this turn. You can only use each effect of \"Tessera the Primal Squire\" once per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FE2: {  # eidos_squire -- Eidos the Underworld Squire (donor Great White)
        "e": ("Eidos the Underworld Squire",
             "If this card is Normal or Special Summoned: During your Main Phase this turn, you can Tribute Summon 1 monster, in addition to your Normal Summon/Set. (You can only gain this effect once per turn.) You can banish this card from your Graveyard, then target 1 monster with 800 ATK and 1000 DEF in your Graveyard, except \"Eidos the Underworld Squire\"; Special Summon it in Defense Position, also you cannot Special Summon monsters from the Extra Deck for the rest of this turn. You can only use this effect of \"Eidos the Underworld Squire\" once per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FDC: {  # edea -- Edea the Heavenly Squire (donor Gokibore)
        "e": ("Edea the Heavenly Squire",
             "If this card is Normal or Special Summoned: You can Special Summon 1 monster with 800 ATK and 1000 DEF from your Deck in Defense Position, except \"Edea the Heavenly Squire\", also you cannot Special Summon monsters from the Extra Deck for the rest of this turn. If this card is sent to the Graveyard: You can target 1 of your banished \"Monarch\" Spell/Trap Cards; add it to your hand. You can only use each effect of \"Edea the Heavenly Squire\" once per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1DCD: {  # revolt -- The Monarchs Revolt (donor Short Circuit)
        "e": ("The Monarchs Revolt",
             "Discard 1 card; reveal 3 monsters from your Deck, with 2400 or more ATK and 1000 DEF, and/or 800 ATK/1000 DEF, your opponent chooses 1 for you to add to your hand, and you send the rest to the GY, also for the rest of this turn after this card resolves, you cannot Special Summon from the Extra Deck. You can banish this card from your GY; Special Summon 1 monster with 800 ATK/1000 DEF from your hand. You can only use each effect of \"The Monarchs Revolt\" once per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x14C3: {  # frost_blast -- Frost Blast of the Monarchs (donor Double Snare)
        "e": ("Frost Blast of the Monarchs",
             "If you control a monster with 2400 or more ATK and 1000 DEF: Target 1 Set card on the field; destroy it. You can banish this card and 1 \"Monarch\" Spell/Trap Card from your Graveyard, then target 1 Set card on the field; destroy it."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1923: {  # pantheism -- Pantheism of the Monarchs (donor Des Croaking)
        "e": ("Pantheism of the Monarchs",
             "Send 1 \"Monarch\" Spell/Trap Card from your hand to the Graveyard; draw 2 cards. You can banish this card from your Graveyard; reveal 3 \"Monarch\" Spell/Trap Cards from your Deck, your opponent chooses 1 for you to add to your hand, and you shuffle the rest back into your Deck. You can only use this effect of \"Pantheism of the Monarchs\" once per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x14D8: {  # mega_monarch -- Angmarl the Fiendish Monarch (donor The Dragon Dwelling in the Cave)
        "e": ("Angmarl the Fiendish Monarch",
             "When this card is Tribute Summoned: You can banish 1 Spell Card from your Graveyard; add 1 card with the same name as the banished Spell Card from your Deck to your hand."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x249B: {  # first_monarch -- The First Monarch (donor Tiki Soul, a native Trap Monster; the Attribute effect is NOT built yet)
        "e": ("The First Monarch",
             "Special Summon this card as an Effect Monster (Fiend-Type/DARK/Level 6/ATK 1000/DEF 2400). (This card is also still a Trap Card.) If Summoned this way: You can discard 1 card, then declare 1 Attribute; this card becomes that Attribute, and can be treated as 2 Tributes for the Tribute Summon of a monster with the same Attribute as this card. If this card was Summoned this way, you cannot Special Summon monsters, except monsters with this card's Attribute."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x12F6: {  # erebus.py + c/perfection.c -- Monarchic Perfection (donor Call of the Grave, converted to a Continuous Trap; test ROM only)
        "e": ("Monarchic Perfection",
             "Once per Chain, if your opponent Special Summons a monster(s), and you control a Tribute Summoned monster (except during the Damage Step): You can banish 1 \"Monarch\" Spell/Trap from your GY, then activate 1 of these effects (but you can only use each effect of \"Monarchic Perfection\" once per turn);\r\n\x9dDestroy 1 monster on the field.\r\n\x9dDestroy up to 2 Spells/Traps on the field.\r\n\x9dDiscard 1 random card from your opponent's hand.\r\n\x9dDestroy 1 face-down card on the field.\r\n\x9dPlace 1 card from the field on top of the Deck.\r\n\x9dBanish 1 card on the field."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": PERFECTION_CJK,
        "k": PERFECTION_CJK,
        "r": PERFECTION_CJK,
    },
    0x14CF: {  # erebus.py -- The Prime Monarch (donor The A. Forces, converted to a Continuous Trap; GY Special Summon half built 2026-11-12, first_monarch.py owns its stat-tree arm)
        "e": ("The Prime Monarch",
             "Once per turn: You can target 2 \"Monarch\" Spell/Trap Cards in your Graveyard; shuffle them into the Deck, then draw 1 card. If this card is in your Graveyard: You can banish 1 other \"Monarch\" Spell/Trap Card from your Graveyard; Special Summon this card in Defense Position as a Normal Monster (Fairy-Type/LIGHT/Level 5/ATK 1000/DEF 2400). (This card is NOT treated as a Trap Card.) You can only use this effect of \"The Prime Monarch\" once per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1800: {  # escalation -- Escalation of the Monarchs (donor Enervating Mist)
        "e": ("Escalation of the Monarchs",
             "Once per turn, during your opponent's Main Phase or your opponent's Battle Phase, you can: Immediately after this effect resolves, Tribute Summon 1 monster."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1312: {  # erebus.py -- Ehther the Heavenly Monarch (donor Baron of the Fiend Sword)
        "e": ("Ehther the Heavenly Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: You can send 2 \"Monarch\" Spell/Trap Cards with different names from your hand and/or Deck to the Graveyard, and if you do, Special Summon 1 monster with 2400 or more ATK and 1000 DEF from your Deck, but return it to the hand during the End Phase. During your opponent's Main Phase, if this card is in your hand: You can banish 1 \"Monarch\" Spell/Trap Card from your Graveyard; immediately after this effect resolves, Tribute Summon this card (this is a Quick Effect)."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1313: {  # erebus -- Erebus the Underworld Monarch (donor Man-Eating Treasure Chest)
        "e": ("Erebus the Underworld Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: You can send 2 \"Monarch\" Spell/Trap Cards with different names from your hand and/or Deck to the Graveyard, and if you do, shuffle 1 card from your opponent's hand (at random), Graveyard, or their side of the field into the Deck. Once per turn, during either player's Main Phase, if this card is in your Graveyard: You can discard 1 \"Monarch\" Spell/Trap Card, then target 1 monster in your Graveyard with 2400 or more ATK and 1000 DEF; add it to your hand."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x127B: {  # mega_monarch -- Thestalos the Mega Monarch (donor Red Archery Girl)
        "e": ("Thestalos the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Look at your opponent's hand and discard 1 card from their hand, then, if it was a Monster Card, inflict damage to your opponent equal to its original Level x 200. If this card was Tribute Summoned by Tributing a FIRE monster, add this additional effect.\r\n\x9d Also, inflict 1000 damage to your opponent after that."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ("Thestalos the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Look at your opponent's hand and discard 1 card from their hand, then, if it was a Monster Card, inflict damage to your opponent equal to its original Level x 200. If this card was Tribute Summoned by Tributing a FIRE monster, add this additional effect.\r\n● Also, inflict 1000 damage to your opponent after that."),
        "k": ("Thestalos the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Look at your opponent's hand and discard 1 card from their hand, then, if it was a Monster Card, inflict damage to your opponent equal to its original Level x 200. If this card was Tribute Summoned by Tributing a FIRE monster, add this additional effect.\r\n● Also, inflict 1000 damage to your opponent after that."),
        "r": ("Thestalos the Mega Monarch",
             "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Look at your opponent's hand and discard 1 card from their hand, then, if it was a Monster Card, inflict damage to your opponent equal to its original Level x 200. If this card was Tribute Summoned by Tributing a FIRE monster, add this additional effect.\r\n● Also, inflict 1000 damage to your opponent after that."),
    },
    0x14A1: {  # return_monarchs -- Return of the Monarchs (donor Vengeful Bog Spirit)
        "e": ("Return of the Monarchs",
             "You cannot Special Summon monsters from the Extra Deck. When you Tribute Summon a monster: You can activate 1 of these effects;\r\n\x9dAdd, from your Deck to your hand, 1 monster with 2400 ATK and 1000 DEF with a different name from that Tribute Summoned monster.\r\n\x9dAdd, from your Deck to your hand, 1 monster with 2800 ATK and 1000 DEF with a different name from that Tribute Summoned monster.\r\nThe Tribute Summoned monster must be face-up on the field to activate and to resolve this effect. You can only use this effect of \"Return of the Monarchs\" once per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ("Return of the Monarchs",
             "You cannot Special Summon monsters from the Extra Deck. When you Tribute Summon a monster: You can activate 1 of these effects;\r\n●Add, from your Deck to your hand, 1 monster with 2400 ATK and 1000 DEF with a different name from that Tribute Summoned monster.\r\n●Add, from your Deck to your hand, 1 monster with 2800 ATK and 1000 DEF with a different name from that Tribute Summoned monster.\r\nThe Tribute Summoned monster must be face-up on the field to activate and to resolve this effect. You can only use this effect of \"Return of the Monarchs\" once per turn."),
        "k": ("Return of the Monarchs",
             "You cannot Special Summon monsters from the Extra Deck. When you Tribute Summon a monster: You can activate 1 of these effects;\r\n●Add, from your Deck to your hand, 1 monster with 2400 ATK and 1000 DEF with a different name from that Tribute Summoned monster.\r\n●Add, from your Deck to your hand, 1 monster with 2800 ATK and 1000 DEF with a different name from that Tribute Summoned monster.\r\nThe Tribute Summoned monster must be face-up on the field to activate and to resolve this effect. You can only use this effect of \"Return of the Monarchs\" once per turn."),
        "r": ("Return of the Monarchs",
             "You cannot Special Summon monsters from the Extra Deck. When you Tribute Summon a monster: You can activate 1 of these effects;\r\n●Add, from your Deck to your hand, 1 monster with 2400 ATK and 1000 DEF with a different name from that Tribute Summoned monster.\r\n●Add, from your Deck to your hand, 1 monster with 2800 ATK and 1000 DEF with a different name from that Tribute Summoned monster.\r\nThe Tribute Summoned monster must be face-up on the field to activate and to resolve this effect. You can only use this effect of \"Return of the Monarchs\" once per turn."),
    },
    0x12EB: {  # tenacity -- Tenacity of the Monarchs (donor De-Spell)
        "e": ("Tenacity of the Monarchs",
             "Reveal 1 monster in your hand with 2400 ATK & 1000 DEF, or 2800 ATK & 1000 DEF; add 1 \"Monarch\" Spell/Trap Card from your Deck to your hand, except \"Tenacity of the Monarchs\". You can only activate 1 \"Tenacity of the Monarchs\" per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1633: {  # monarchs_awaken -- The Monarchs Awaken (donor Disarmament)
        "e": ("The Monarchs Awaken",
             "If you have no cards in your Extra Deck: Target 1 face-up Tribute Summoned monster you control; its effects are negated, also it is unaffected by the effects of cards other than this card."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x12EE: {  # restoration -- Restoration of the Monarchs (donor Burning Spear)
        "e": ("Restoration of the Monarchs",
             "Activate this card by targeting 1 monster in your GY with 2400 ATK/1000 DEF, or 2800 ATK/1000 DEF; Special Summon it in Defense Position, but negate its effects, also equip it with this card. When this card leaves the field, destroy that monster. The equipped monster can be treated as 2 Tributes for a Tribute Summon. You can only activate 1 \"Restoration of the Monarchs\" per turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1328: {  # stormforth -- The Monarchs Stormforth (donor Tailor of the Fickle)
        "e": ("The Monarchs Stormforth",
             "Once during this turn, if you would Tribute a monster for a Tribute Summon, you can Tribute 1 monster your opponent controls even though you do not control it. You can only activate 1 \"The Monarchs Stormforth\" per turn. During the turn you activate this card, you cannot Special Summon monsters from the Extra Deck."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FD8: {  # metal_armored_bug -- Metal Armored Bug
        "e": ('Metal Armored Bug',
             'A gigantic insect-like creature covered by thick armor. Everything in his path is destroyed.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
# NOT LISTED: wonder_wand (donor 0x19D8, "Trial of the Princesses").
# Its PatchStep in apply_all_patches is COMMENTED OUT, so the card is not in the
# chain and nothing ever writes its text -- listing it here only made the
# whole-ROM check report 47/48 for a card that does not exist in the build.
# Add the entry back in the SAME edit that uncomments the PatchStep.
    0x11A3: {  # accel_synchron -- Accel Synchron
        "e": ('Accel Synchron',
             '1 Tuner + 1+ non-Tuner monsters Once per turn: You can send 1 "Synchron" monster from your Deck to the GY, then activate 1 of these effects; Increase this card\'s Level by the Level of the sent monster. Reduce this card\'s Level by the Level of the sent monster. During your opponent\'s Main Phase, you can (Quick Effect): Immediately after this effect resolves, Synchro Summon using this card you control. You can only Synchro Summon "Accel Synchron" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1179: {  # crimson_blader -- Crimson Blader (donor Crimson Sunbird)
        "e": ('Crimson Blader',
             "1 Tuner + 1 or more non-Tuner monsters If this card destroys an opponent's monster by battle and sends it to the Graveyard: Your opponent cannot Normal or Special Summon Level 5 or higher monsters during their next turn."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x126F: {  # accel_synchro_stardust_dragon -- Accel Synchro Stardust Dragon
        "e": ('Accel Synchro Stardust Dragon',
             '1 Tuner + 1+ non-Tuner monsters If this card is Synchro Summoned: You can Special Summon 1 Level 2 or lower Tuner from your GY. During the Main Phase (Quick Effect): You can Tribute this card; Special Summon 1 "Stardust Dragon" from your Extra Deck (this is treated as a Synchro Summon), then, immediately after this effect resolves, Synchro Summon 1 Synchro Monster using monsters you control as material. This turn, the monsters Synchro Summoned by this effect are unaffected by your opponent\'s activated effects. You can only use each effect of "Accel Synchro Stardust Dragon" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1255: {  # ninjitsu_art_super_transformation -- Ninjitsu Art of Super-Transformation
        "e": ('Ninjitsu Art of Super-Transformation',
             'Activate this card by targeting 1 "Ninja" monster you control and 1 face-up monster your opponent controls; send them to the GY, then Special Summon 1 Dragon, Dinosaur, or Sea Serpent monster from your Deck whose Level is less than or equal to the combined original Levels of the sent monster(s). When this card leaves the field, banish that monster.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x12B2: {  # white_dragon_ninja -- White Dragon Ninja
        "e": ('White Dragon Ninja',
             'Cannot be Special Summoned, except with a "Ninjitsu Art" card\'s effect. Spells/Traps you control cannot be destroyed by card effects.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x12B6: {  # steam_synchron -- Steam Synchron
        "e": ('Steam Synchron',
             "During your opponent's Main Phase, you can: Immediately after this effect resolves, Synchro Summon using this card you control (this is a Quick Effect)."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1315: {  # w_nebula_meteorite -- W Nebula Meteorite
        "e": ('W Nebula Meteorite',
             'Change all face-down monsters on the field to face-up Defense Position. During the End Phase this turn, change all face-up LIGHT Reptile-Type monsters you control to face-down Defense Position, then draw 1 card for each. After that, you can Special Summon 1 Level 7 or higher LIGHT Reptile-Type monster from your Deck.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x13C6: {  # scrap_archfiend -- Scrap Archfiend
        "e": ('Scrap Archfiend',
             '1 Tuner + 1 or more non-Tuner monsters'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x13E7: {  # ninja_grandmaster_hanzo -- Ninja Grandmaster Hanzo
        "e": ('Ninja Grandmaster Hanzo',
             'When this card is Normal Summoned: You can add 1 "Ninjitsu Art" card from your Deck to your hand. When this card is Flip or Special Summoned: You can add 1 "Ninja" monster from your Deck to your hand, except "Ninja Grandmaster Hanzo".'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1463: {  # reborn_tengu -- Reborn Tengu
        "e": ('Reborn Tengu',
             'If this face-up card leaves the field: Special Summon 1 "Reborn Tengu" from your Deck.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1464: {  # upstart_golden_ninja -- Upstart Golden Ninja
        "e": ('Upstart Golden Ninja',
             'Once per turn: You can send 1 Trap from your hand to the GY; Special Summon 1 Level 4 or lower "Ninja" monster from your Deck in face-up Defense Position or face-down Defense Position.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x14C1: {  # dragon_shrine -- Dragon Shrine
        "e": ('Dragon Shrine',
             'Send 1 Dragon monster from your Deck to the GY, then, if that monster in your GY is a Dragon Normal Monster, you can send 1 more Dragon monster from your Deck to the GY. You can only activate 1 "Dragon Shrine" per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x13A5: {  # boggart_knight -- XX-Saber Boggart Knight (donor Molten Behemoth)
        "e": ('XX-Saber Boggart Knight',
             'When this card is Normal Summoned: You can Special Summon 1 Level 4 or lower "X-Saber" monster from your hand. Cannot be used as a Synchro Material, except for the Synchro Summon of an "X-Saber" Synchro Monster.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1646: {  # darkflare -- Darkflare Dragon
        "e": ('Darkflare Dragon',
             'You can Special Summon this card (from your hand) by banishing 1 LIGHT and 1 DARK monster from your GY. Once per turn: You can send 1 Dragon monster from your hand and 1 Dragon monster from your Deck to the GY, then target 1 card in either GY; banish that target.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x16A2: {  # safe_zone -- Safe Zone
        "e": ('Safe Zone',
             "Activate this card by targeting 1 face-up Attack Position monster on the field; that face-up monster cannot be destroyed by battle or your opponent's card effects, your opponent cannot target it with card effects, also it cannot attack your opponent directly. When this card leaves the field, destroy that monster. When that monster leaves the field, destroy this card."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x17CE: {  # junk_servant -- Junk Servant
        "e": ('Junk Servant',
             'If you control a "Junk" monster, you can Special Summon this card (from your hand).'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x181C: {  # unknown_synchron -- Unknown Synchron
        "e": ('Unknown Synchron',
             'If your opponent controls a monster and you control no monsters, you can Special Summon this card (from your hand). You can only Special Summon "Unknown Synchron" once per Duel this way.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1859: {  # eclipse_wyvern -- Eclipse Wyvern
        "e": ('Eclipse Wyvern',
             "If this card is sent to the Graveyard: Banish 1 Level 7 or higher LIGHT or DARK Dragon-Type monster from your Deck. If this card is banished from your Graveyard: You can add the monster banished by this card's effect to your hand."),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1961: {  # grapha -- Grapha, Dragon Lord of Dark World
        "e": ('Grapha, Dragon Lord of Dark World',
             'You can Special Summon this card (from your Graveyard) by returning 1 "Dark World" monster you control to the hand, except "Grapha, Dragon Lord of Dark World". If this card is discarded to the Graveyard by a card effect: Target 1 card your opponent controls; destroy that target, then, if this card was discarded from your hand to your Graveyard by an opponent\'s card effect, look at 1 random card in your opponent\'s hand, then, if it was a monster, you can Special Summon it to your side of the field.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x19B2: {  # shiens_dojo -- Shien's Dojo
        "e": ("Shien's Dojo",
             'Each time a "Six Samurai" monster(s) is Normal or Special Summoned, place 1 Bushido Counter on this card. You can send this card to the GY; Special Summon 1 "Six Samurai" or "Shien" Effect Monster from your Main Deck, whose Level is less than or equal to the number of Bushido Counters on this card.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x13B8: {  # mystic_piper -- Mystic Piper (donor Flame Dancer, re-homed)
        "e": ('Mystic Piper',
             'You can Tribute this card to draw and reveal 1 card. If that card is a Level 1 Monster Card, draw 1 more card. The effect of "Mystic Piper" can only be activated once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FAE: {  # cardcar_d -- Cardcar D (donor Mushroom Man; clause 2 only)
        "e": ('Cardcar D',
             'Cannot be Special Summoned. During your Main Phase 1, if this card was Normal Summoned this turn: You can Tribute this card; draw 2 cards, then it becomes the End Phase. You cannot Special Summon during the turn you activate this effect.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FD5: {  # kuribandit -- Kuribandit (donor Torike)
        "e": ('Kuribandit',
             'During the End Phase, if this card was Normal Summoned this turn: You can Tribute this card; excavate the top 5 cards of your Deck, you can add 1 excavated Spell/Trap to your hand, also send the remaining cards to the GY.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FC6: {  # souleating_oviraptor -- Souleating Oviraptor (donor Two-Headed King Rex; C1; C2
        "e": ('Souleating Oviraptor',
             'If this card is Normal or Special Summoned: You can take 1 Dinosaur-Type monster from your Deck, and either add it to your hand or send it to the Graveyard. You can target 1 other Level 4 or lower Dinosaur-Type monster on the field; destroy it, then Special Summon 1 Dinosaur-Type monster from your Graveyard in Defense Position. You can only use each effect of "Souleating Oviraptor" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FF2: {  # miscellaneousaurus -- Miscellaneousaurus (donor Krokodilus; C2; C1 C1 sentence reworded to the implemented behaviour at the user's request)
        "e": ('Miscellaneousaurus',
             'During either player\'s Main Phase: You can send this card from your hand to the GY; until the end of this turn, face-up Dinosaur monsters you currently control are unaffected by card effects. You can banish any number of Dinosaur-Type monsters from your Graveyard, including this card; Special Summon 1 Dinosaur-Type monster from your Deck with a Level equal to the total number of monsters banished to activate this effect, but destroy it during the End Phase. You can only use this effect of "Miscellaneousaurus" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x13AE: {  # assault_synchron -- Assault Synchron (donor Shapesnatch; chassis only
        "e": ('Assault Synchron',
             'During your Main Phase: You can Special Summon this card from your hand, then take 700 damage, also you cannot Special Summon monsters from the Extra Deck, except Synchro Monsters, while this card is face-up in the Monster Zone. If a face-up Dragon Synchro Monster(s) you control is Tributed or banished (except during the Damage Step): You can banish this card from your GY, then target 1 of those monsters; Special Summon it. You can only use each effect of "Assault Synchron" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1008: {  # psi_reflector -- Psi-Reflector (donor Clown Zombie; both clauses
        "e": ('Psi-Reflector',
             'If this card is Normal or Special Summoned: You can add 1 "Assault Mode Activate", or 1 card that specifically lists "Assault Mode Activate" in its text, from your Deck to your hand, except "Psi-Reflector". You can reveal 1 "Assault Mode Activate" in your hand, then target 1 monster in your GY that specifically lists "Assault Mode Activate" in its text, except "Psi-Reflector"; Special Summon it, and if you do, increase its Level by 1 to 4. You can only use each effect of "Psi-Reflector" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1126: {  # koaki_meiru_wall -- Koa'ki Meiru Wall (donor Dark Rabbit
        "e": ("Koa'ki Meiru Wall",
             'During each of your End Phases, destroy this card unless you send 1 "Iron Core of Koa\'ki Meiru" from your hand to the GY or reveal 1 Rock monster in your hand. When your opponent activates a Spell Card (Quick Effect): You can Tribute this card; negate the activation, and if you do, destroy that card.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x111F: {  # shadow_mist -- Elemental HERO Shadow Mist (donor Ryu-Kishin Powered
        "e": ('Elemental HERO Shadow Mist',
             'If this card is Special Summoned: You can add 1 "Change" Quick-Play Spell Card from your Deck to your hand. If this card is sent to the GY: You can add 1 "HERO" monster from your Deck to your hand, except "Elemental HERO Shadow Mist". You can only use 1 "Elemental HERO Shadow Mist" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1160: {  # masked_hero_dark_law -- Masked HERO Dark Law (donor Aqua Dragon; C1 only
        "e": ('Masked HERO Dark Law',
             'Must be Special Summoned by "Mask Change". Any card sent to your opponent\'s GY is banished instead. Once per turn, if your opponent adds a card(s) from their Deck to their hand (except during the Draw Phase or the Damage Step): You can banish 1 random card from your opponent\'s hand.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x10F5: {  # seal_of_orichalcos -- The Seal of Orichalcos (donor Yami
        "e": ('The Seal of Orichalcos',
             'All monsters you control gain 500 ATK. Once per turn, this card cannot be destroyed by card effects. While you control 2 or more face-up Attack Position monsters, your opponent cannot target your monster(s) with the lowest ATK for an attack. If this card is activated: Destroy all Special Summoned monsters you control. You cannot Special Summon monsters from the Extra Deck. You can only activate "The Seal of Orichalcos" once per Duel.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1297: {  # animadorned_archosaur -- Animadorned Archosaur (donor Swordsman of Landstar
        "e": ('Animadorned Archosaur',
             'If this card is Normal or Special Summoned: You can destroy 1 Dinosaur monster in your hand or face-up field, except "Animadorned Archosaur", then add 1 Reptile, Sea Serpent, or Winged Beast monster with the same original Level as that destroyed monster, OR 1 "Evolution Pill" Spell, from your Deck to your hand. You can only use this effect of "Animadorned Archosaur" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1110: {  # grandsoil -- Grandsoil the Elemental Lord (donor Millennium Shield
        "e": ('Grandsoil the Elemental Lord',
             'Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 EARTH monsters in your GY. When this card is Special Summoned: You can target 1 monster in either player\'s GY; Special Summon that target. You can only use this effect of "Grandsoil the Elemental Lord" once per turn. If this face-up card leaves the field, skip the Battle Phase of your next turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1C1A: {  # moulinglacia -- Moulinglacia the Elemental Lord (donor Venom Cobra
        "e": ('Moulinglacia the Elemental Lord',
             'Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 WATER monsters in your GY. If this card is Special Summoned: Discard 2 random cards from your opponent\'s hand (or their entire hand, if less than 2). You can only use this effect of "Moulinglacia the Elemental Lord" once per turn. If this face-up card leaves the field, skip the Battle Phase of your next turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x181F: {  # pyrorex -- Pyrorex the Elemental Lord (donor Harpie Girl
        "e": ('Pyrorex the Elemental Lord',
             'Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 FIRE monsters in your GY. When this card is Special Summoned: You can target 1 monster your opponent controls; destroy it, and if you do, both players take damage equal to half the original ATK of the destroyed monster. You can only use this effect of "Pyrorex the Elemental Lord" once per turn. If this face-up card leaves the field, skip the Battle Phase of your next turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x190B: {  # windrose -- Windrose the Elemental Lord (donor Soitsu
        "e": ('Windrose the Elemental Lord',
             'Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 WIND monsters in your GY. If this card is Special Summoned: Destroy all Spells and Traps your opponent controls. You can only use this effect of "Windrose the Elemental Lord" once per turn. If this face-up card leaves the field, skip the Battle Phase of your next turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1127: {  # elder_entity_norden -- Elder Entity Norden (donor Bickuribox). Materials per user: Synchro + Synchro (no Xyz in this game)
        "e": ('Elder Entity Norden',
             '1 Synchro Monster + 1 Synchro Monster When this card is Special Summoned: You can target 1 Level 4 or lower monster in your Graveyard; Special Summon it, but its effects are negated, also banish it when this card leaves the field.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1465: {  # naturia_pineapple -- Naturia Pineapple (donor Headless Knight)
        "e": ('Naturia Pineapple',
             'All face-up monsters you control are treated as Plant-Type. During your Standby Phase, if you do not control a face-up "Naturia Pineapple", and have no monsters in your Graveyard except Plant or Beast-Type: You can Special Summon this card from your Graveyard. You must not control any Spell or Trap Cards to activate and resolve this effect.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x106C: {  # mara -- Mara of the Nordic Alfar (donor Happy Lover
        "e": ('Mara of the Nordic Alfar',
             'When using this card as Synchro Material, the other Synchro Materials must be 2 "Nordic" monsters in your hand.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1649: {  # revolution_synchron -- Revolution Synchron (donor Acrobat Monkey; C0+C1; C2 not implemented)
        "e": ('Revolution Synchron',
             'If you Synchro Summon a "Power Tool" monster or a Level 7 or 8 Dragon monster, this card in your hand can also be used as material. You can only use this effect of "Revolution Synchron" once per turn. If you control a Level 7 or higher Synchro Monster while this card is in your GY: You can send the top card of your Deck to the GY, and if you do, Special Summon this card, also its Level becomes 1. You can only use this effect of "Revolution Synchron" once per Duel.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1B3E: {  # ceruli -- Ceruli, Guru of Dark World
        "e": ('Ceruli, Guru of Dark World',
             'If this card is discarded to the Graveyard by a card effect: Special Summon this card from the Graveyard to your opponent\'s side of the field in face-up Defense Position. When this card is Special Summoned by the effect of a "Dark World" card: Your opponent must discard 1 card.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1C08: {  # escuridao -- Elemental HERO Escuridao
        "e": ('Elemental HERO Escuridao',
             '1 "Elemental HERO" monster + 1 DARK monster Must be Fusion Summoned and cannot be Special Summoned by other ways. This card gains 100 ATK for each "Elemental HERO" monster in your Graveyard.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1C18: {  # snoww -- Snoww, Unlight of Dark World
        "e": ('Snoww, Unlight of Dark World',
             'If this card is discarded to the Graveyard by a card effect: If it was discarded from your hand to your Graveyard by an opponent\'s card effect, you can target 1 monster in your opponent\'s Graveyard; add 1 "Dark World" card from your Deck to your hand, then Special Summon that target (if any) in face-up Defense Position.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1C8B: {  # gates_of_dark_world -- The Gates of Dark World
        "e": ('The Gates of Dark World',
             'All Fiend-Type monsters gain 300 ATK and DEF. Once per turn: You can banish 1 Fiend-Type monster from your Graveyard; discard 1 Fiend-Type monster, then draw 1 card.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1783: {  # darksoul -- XX-Saber Darksoul (donor Gigobyte, re-homed)
        "e": ('XX-Saber Darksoul',
             'During the End Phase, if this card was sent from your side of the field to your Graveyard this turn: You can add 1 "X-Saber" monster from your Deck to your hand.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1DDD: {  # infernity_barrier -- Infernity Barrier
        "e": ('Infernity Barrier',
             'When your opponent activates a Spell/Trap Card, or monster effect, while you control a face-up Attack Position "Infernity" monster and have no cards in your hand: Negate the activation, and if you do, destroy that card.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1E9C: {  # azure_eyes -- Azure-Eyes Silver Dragon
        "e": ('Azure-Eyes Silver Dragon',
             '1 Tuner + 1+ non-Tuner Normal Monsters If this card is Special Summoned: Until the end of the next turn, neither player can target Dragon monsters you currently control with card effects, also they cannot be destroyed by card effects. Once per turn, during your Standby Phase: You can target 1 Normal Monster in your GY; Special Summon it.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FB4: {  # gravekeepers_recruiter -- Gravekeeper's Recruiter (donor Battle Steer, re-homed)
        "e": ("Gravekeeper's Recruiter",
             'If this card you control is sent to your GY: Add 1 "Gravekeeper\'s" monster with 1500 or less DEF from your Deck to your hand.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1ED7: {  # maiden_eyes_of_blue -- Maiden with Eyes of Blue
        "e": ('Maiden with Eyes of Blue',
             'When a card or effect is activated that targets this card (Quick Effect): You can Special Summon 1 "Blue-Eyes White Dragon" from your hand, Deck, or GY. When this card is targeted for an attack: You can negate the attack, and if you do, change the battle position of this card, then you can Special Summon 1 "Blue-Eyes White Dragon" from your hand, Deck, or GY. You can only use 1 "Maiden with Eyes of Blue" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1F18: {  # tg_striker -- T.G. Striker
        "e": ('T.G. Striker',
             'If only your opponent controls a monster, you can Special Summon this card (from your hand). Once per turn, during the End Phase, if this card is in the GY because it was destroyed on the field and sent there this turn: You can add 1 "T.G." monster from your Deck to your hand, except "T.G. Striker".'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1F33: {  # armory_arm -- Armory Arm
        "e": ('Armory Arm',
             '1 Tuner + 1 or more non-Tuner monsters Once per turn, you can either: Target 1 monster on the field; equip this card to that target, OR: Unequip this card and Special Summon it in Attack Position. While equipped by this effect, that target gains 1000 ATK. If that target destroys a monster by battle and sends it to the Graveyard: Inflict damage to your opponent equal to the ATK of the destroyed monster in the Graveyard.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1FFC: {  # sea_lancer -- Sea Lancer
        "e": ('Sea Lancer',
             'You can target any number of your banished Fish, Sea Serpent, and Aqua-Type monsters; equip them to this card. This effect can only be used once while this card is face-up on the field. If this face-up card on the field would be destroyed, you can destroy 1 of those cards, instead. This card gains 1000 ATK while equipped with a monster(s) by this effect.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FD3: {  # wattcobra -- Wattcobra (donor Wattkid, re-homed off Fane 0x2069)
        "e": ('Wattcobra',
             'This card can attack your opponent directly. When this card inflicts Battle Damage to your opponent by a direct attack: Add 1 "Watt" monster from your Deck to your hand.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1050: {  # wattuna -- Wattuna (donor Spirit of the Harp 0x1050)
        "e": ('Wattuna',
             'This card can attack directly. You can only use each of the following effects of "Wattuna" once per turn. At the end of the Damage Step, if your monster inflicts battle damage to your opponent: You can Special Summon this card from your hand. When this card inflicts battle damage to your opponent by a direct attack: You can Tribute this card on the field and 1 or more non-Tuner monsters from your hand and/or face-up field, and Special Summon 1 "Watt" Synchro Monster from your Extra Deck whose Level equals the total Levels of those Tributed monsters.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1458: {  # wattkyuki -- Wattkyuki (donor St. Joan 0x1458)
        "e": ('Wattkyuki',
             '1 "Watt" Tuner + 1+ non-Tuner Thunder monsters This card can attack directly. When this card inflicts battle damage to your opponent by a direct attack: You can shuffle both 1 "Watt" Tuner from your GY and 1 face-up non-Tuner Thunder monster you control into the Deck, and if you do, Special Summon 1 "Watt" Synchro Monster from your Extra Deck, except "Wattkyuki". You can only use this effect of "Wattkyuki" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x211B: {  # shooting_quasar -- Shooting Quasar Dragon
        "e": ('Shooting Quasar Dragon',
             '1 Tuner Synchro Monster + 2 or more non-Tuner Synchro Monsters Must be Synchro Summoned, and cannot be Special Summoned by other ways. This card\'s maximum number of attacks per Battle Phase equals the number of non-Tuner monsters used as its Synchro Material. Once per turn, during either player\'s turn, when a card or effect is activated: You can negate the activation, and if you do, destroy it. When this card leaves the field: You can Special Summon 1 "Shooting Star Dragon" from your Extra Deck.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x224C: {  # jet_synchron -- Jet Synchron
        "e": ('Jet Synchron',
             'If this card is sent to the GY as Synchro Material: You can add 1 "Junk" monster from your Deck to your hand. If this card is in your GY: You can send 1 card from your hand to the GY; Special Summon this card, but banish it when it leaves the field. You can only use 1 "Jet Synchron" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FC2: {  # tour_guide -- Tour Guide From the Underworld (donor Rock Ogre Grotto #1)
        "e": ('Tour Guide From the Underworld',
             'When this card is Normal Summoned: You can Special Summon 1 Level 3 Fiend monster from your hand or Deck, but negate its effects, also it cannot be used as Synchro Material.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x22E6: {  # tg_rush_rhino -- T.G. Rush Rhino
        "e": ('T.G. Rush Rhino',
             'If this card attacks, it gains 400 ATK during the Damage Step only. Once per turn, during the End Phase, if this card is in the GY because it was destroyed on the field and sent there this turn: You can add 1 "T.G." monster from your Deck to your hand, except "T.G. Rush Rhino".'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1225: {  # hyper_librarian -- T.G. Hyper Librarian (re-donor; was 0x2338)
        "e": ('T.G. Hyper Librarian',
             '1 Tuner + 1+ non-Tuner monsters If a monster is Synchro Summoned: Draw 1 card. This card must be face-up on the field to activate and to resolve this effect.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x23EB: {  # jet_warrior -- Jet Warrior
        "e": ('Jet Warrior',
             '"Jet Synchron" + 1 or more non-Tuner monsters If this card is Synchro Summoned: You can target 1 card your opponent controls; return it to the hand. If this card is in your Graveyard: You can Tribute 1 Level 2 or lower monster; Special Summon this card in Defense Position, but banish it when it leaves the field. You can only use each effect of "Jet Warrior" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FFD: {  # ninishi -- Karakuri Komachi mdl 224 "Ninishi" (donor Dark Chimera, re-homed)
        "e": ('Karakuri Komachi mdl 224 "Ninishi"',
             'This card must attack if able. When this face-up card is selected as an attack target, change its battle position. While this card is face-up on the field, once per turn during your Main Phase, you can Normal Summon 1 "Karakuri" monster in addition to your Normal Summon or Set. (You can only gain this effect once per turn.)'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x120B: {  # junk_speeder -- Junk Speeder (re-donored onto Twin-Headed Thunder Dragon)
        "e": ('Junk Speeder',
             '1 "Synchron" Tuner + 1+ non-Tuner monsters If this card is Synchro Summoned: You can Special Summon as many "Synchron" Tuners as possible with different Levels from your Deck, in Defense Position. You cannot Special Summon monsters from the Extra Deck, except Synchro Monsters, the turn you activate this effect. When an attack is declared involving this card that was Synchro Summoned this turn and another monster: You can make this card\'s ATK become double its original ATK until the end of this turn. You can only use each effect of "Junk Speeder" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x123D: {  # soul_charge -- Soul Charge (donor Breath of Light; clauses 1+2 only)
        "e": ('Soul Charge',
             'Target any number of monsters in your GY; Special Summon them, and if you do, you lose 1000 LP for each monster Special Summoned by this effect. You cannot conduct your Battle Phase the turn you activate this card. You can only activate 1 "Soul Charge" per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1265: {  # ultimate_conductor_tyranno -- Ultimate Conductor Tyranno (donor Sengenjin; C1/C3/C4 built
        "e": ('Ultimate Conductor Tyranno',
             'Cannot be Normal Summoned/Set. Must first be Special Summoned (from your hand) by banishing 2 Dinosaur-Type monsters from your Graveyard. Once per turn, during either player\'s Main Phase: You can destroy 1 monster in your hand or field, and if you do, change all face-up monsters your opponent controls to face-down Defense Position. This card can attack all monsters your opponent controls, once each. At the start of the Damage Step, if this card attacks a Defense Position monster: You can inflict 1000 damage to your opponent, and if you do, send that Defense Position monster to the Graveyard.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1319: {  # double_evolution_pill -- Double Evolution Pill (donor Share the Pain)
        "e": ('Double Evolution Pill',
             'Banish 1 Dinosaur monster and 1 non-Dinosaur monster from your hand and/or GY; Special Summon 1 Level 7 or higher Dinosaur monster from your hand or Deck, ignoring its Summoning conditions. You can only activate 1 "Double Evolution Pill" per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x2124: {  # amazoness_heirloom -- Amazoness Heirloom (donor Molting Escape
        "e": ('Amazoness Heirloom',
             'Equip only to an "Amazoness" monster. Once per turn, that monster cannot be destroyed by battle. After damage calculation, if the equipped monster attacks a monster: Destroy the attacked monster.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x24B5: {  # vylon_element -- Vylon Element (name unchanged; desc only)
        # DELIBERATELY NOT the printed text (ygoprodeck id 92035412, which says "When ... You
        # can Special Summon an equal or lower number"). USER DECISION: the card runs
        # the Gravekeeper's Spy cls1 transplant, which is mandatory (no Yes/No prompt) and
        # Special Summons exactly ONE Tuner -- the driver's own select count -- so the text is
        # reworded to "If" + "1" to describe what the ROM actually does. The native "up to N"
        # resolver cannot run on the mandatory path; that is the whole trade.
        # In-game confirmed by user: summons 1, no prompt, restriction holds, and it
        # does NOT miss timing on a Rod of Silence - Kay'est board -- so "If" is now accurate.
        # (That is a property of the whole Spy record, not of the +10 tag alone: see
        # timing.class1_and_class2_differ_only_at_the_gy_offer.)
        # Routed through card_text rather than an in-place write because the English desc
        # slot is 286 B and in-place would skip English entirely.
        "e": ('Vylon Element',
             'If any face-up "Vylon" Equip Card(s) you control are destroyed (except during the Damage Step): Special Summon 1 "Vylon" Tuner monster from your Deck. It cannot be used as a Synchro Material Monster, except for the Synchro Summon of a "Vylon" Synchro Monster.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x13AC: {  # aratama -- Aratama (donor Souleater)
        "e": ('Aratama',
             'Cannot be Special Summoned. During the End Phase of the turn this card is Normal Summoned or flipped face-up: Return it to the hand. When this card is Normal Summoned or flipped face-up: You can add 1 Spirit monster from your Deck to your hand, except "Aratama".'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x13E5: {  # sakitama -- Sakitama (donor Grand Tiki Elder
        "e": ('Sakitama',
             'Cannot be Special Summoned. Once per turn, during the End Phase, if this card was Normal Summoned or flipped face-up this turn: Return this card to the hand. You can only use each of the following effects of "Sakitama" once per turn. You can reveal this card in your hand; immediately after this effect resolves, Normal Summon 1 Spirit monster from your hand. If this card is Tributed: Target 1 Spirit monster in your GY; add it to your hand.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FE3: {  # nikitama -- Nikitama (donor Wolf)
        "e": ('Nikitama',
             'Cannot be Special Summoned. During the End Phase of the turn this card is Normal Summoned or flipped face-up: Return it to the hand. During the turn this card was Normal Summoned or flipped face-up, you can Normal Summon 1 Spirit monster in addition to your Normal Summon/Set. (You can only gain this effect once per turn.) When this card is sent to the Graveyard: Draw 1 card. You must control a Spirit monster to activate and to resolve this effect.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1106: {  # neo_space_connector -- Neo Space Connector (donor Kanan the Swordmistress
        "e": ('Neo Space Connector',
             'When this card is Normal Summoned: You can Special Summon 1 "Neo-Spacian" monster or 1 "Elemental HERO Neos" from your hand or Deck in Defense Position. You can Tribute this card, then target 1 "Neo-Spacian" monster or 1 "Elemental HERO Neos" in your GY; Special Summon it in Defense Position. You can only use each effect of "Neo Space Connector" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x115F: {  # dragon_rulers -- Tidal, Dragon Ruler of Waterfalls (donor Mech Bass
        "e": ('Tidal, Dragon Ruler of Waterfalls',
             'If this card is in your hand or Graveyard: You can banish a total of 2 WATER and/or Dragon-Type monsters from your hand and/or Graveyard, except this card; Special Summon this card. During your opponent\'s End Phase, if this card was Special Summoned: Return it to the hand. You can discard this card and 1 WATER monster to the Graveyard; send 1 monster from your Deck to the Graveyard. If this card is banished: You can add 1 WATER Dragon-Type monster from your Deck to your hand. You can only use 1 "Tidal, Dragon Ruler of Waterfalls" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1145: {  # dragon_rulers -- Blaster, Dragon Ruler of Infernos (donor Mechanicalchaser
        "e": ('Blaster, Dragon Ruler of Infernos',
             'If this card is in your hand or Graveyard: You can banish a total of 2 FIRE and/or Dragon-Type monsters from your hand and/or Graveyard, except this card; Special Summon this card. During your opponent\'s End Phase, if this card was Special Summoned: Return it to the hand. You can discard this card and 1 FIRE monster to the Graveyard, then target 1 card on the field; destroy that target. If this card is banished: You can add 1 FIRE Dragon-Type monster from your Deck to your hand. You can only use 1 "Blaster, Dragon Ruler of Infernos" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1125: {  # dragon_rulers -- Tempest, Dragon Ruler of Storms (donor Parrot Dragon
        "e": ('Tempest, Dragon Ruler of Storms',
             'You can discard this card and 1 WIND monster to the GY; add 1 Dragon monster from your Deck to your hand. You can banish a total of 2 WIND and/or Dragon monsters from your hand and/or GY; Special Summon this card from your hand or GY. During your opponent\'s End Phase, if you control this Special Summoned card: Return it to the hand. If this card is banished: You can add 1 WIND Dragon monster from your Deck to your hand. You can only use 1 "Tempest, Dragon Ruler of Storms" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FF4: {  # dragon_rulers -- Reactan, Dragon Ruler of Pebbles (donor Axe Raider
        "e": ('Reactan, Dragon Ruler of Pebbles',
             'You can discard this card AND 1 Dragon-Type or EARTH monster; Special Summon 1 "Redox, Dragon Ruler of Boulders" from your Deck. It cannot attack this turn. You can only use the effect of "Reactan, Dragon Ruler of Pebbles" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x115E: {  # dragon_rulers -- Stream, Dragon Ruler of Droplets (donor 7 Colored Fish
        "e": ('Stream, Dragon Ruler of Droplets',
             'You can discard this card AND 1 Dragon-Type or WATER monster; Special Summon 1 "Tidal, Dragon Ruler of Waterfalls" from your Deck. It cannot attack this turn. You can only use the effect of "Stream, Dragon Ruler of Droplets" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FEA: {  # dragon_rulers -- Burner, Dragon Ruler of Sparks (donor Garoozis
        "e": ('Burner, Dragon Ruler of Sparks',
             'You can discard this card AND 1 Dragon-Type or FIRE monster; Special Summon 1 "Blaster, Dragon Ruler of Infernos" from your Deck. It cannot attack this turn. You can only use the effect of "Burner, Dragon Ruler of Sparks" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1CC6: {  # dragon_rulers -- Lightning, Dragon Ruler of Drafts (donor Atlantean Pikeman
        "e": ('Lightning, Dragon Ruler of Drafts',
             'You can discard this card and 1 Dragon or WIND monster; Special Summon 1 "Tempest, Dragon Ruler of Storms" from your Deck, but it cannot attack this turn. You can only use this effect of "Lightning, Dragon Ruler of Drafts" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x17CD: {  # dragon_rulers -- Redox, Dragon Ruler of Boulders (donor Charcoal Inpachi
        "e": ('Redox, Dragon Ruler of Boulders',
             'If this card is in your hand or Graveyard: You can banish a total of 2 EARTH and/or Dragon-Type monsters from your hand and/or Graveyard, except this card; Special Summon this card. During your opponent\'s End Phase, if this card was Special Summoned: Return it to the hand. You can discard this card and 1 EARTH monster to the Graveyard, then target 1 monster in your Graveyard; Special Summon that target. If this card is banished: You can add 1 EARTH Dragon-Type monster from your Deck to your hand. You can only use 1 "Redox, Dragon Ruler of Boulders" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1B22: {  # next_card -- NEXT (donor Return Soul
        "e": ('NEXT',
             'Special Summon any number of monsters with different names from your hand and/or GY, in Defense Position, that are all "Neo-Spacian" monsters or "Elemental HERO Neos", but negate their effects, and as long as you control any of those Special Summoned monsters face-up, you cannot Special Summon monsters from the Extra Deck, except Fusion Monsters. You can only activate 1 "NEXT" per turn. If you control no cards, you can activate this card from your hand.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x13B6: {  # mathematician -- Mathematician (donor Boneheimer)
        "e": ('Mathematician',
             'When this card is Normal Summoned: You can send 1 Level 4 or lower monster from your Deck to the GY. When this card is destroyed by battle and sent to the GY: You can draw 1 card.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x21D5: {  # brilliant_fusion -- Brilliant Fusion (donor Temple of the Sun)
        # FULL printed text; only C1 (Deck-material Fusion Summon, ATK/DEF 0) and C4 (1 per turn)
        # are built. C2 (leaves the field -> destroy) and C3 (discard a Spell) are NOT.
        "e": ('Brilliant Fusion',
             'When this card is activated: Fusion Summon 1 "Gem-Knight" Fusion Monster from your Extra Deck, using monsters from your Deck as Fusion Material, but change its ATK/DEF to 0. If this card leaves the field, destroy that monster. Once per turn: You can discard 1 Spell; the monster Special Summoned by this card\'s effect gains ATK/DEF equal to its original ATK/DEF, until the end of your opponent\'s turn. You can only activate 1 "Brilliant Fusion" per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FE1: {  # petiteranodon -- Petiteranodon (donor Mammoth Graveyard)
        # FULL printed text; the "cannot attack this turn" rider (clause 3) is NOT implemented yet.
        "e": ('Petiteranodon',
             'If this card is destroyed by a card effect and sent to the Graveyard: Special Summon 1 Level 4 or higher Dinosaur-Type monster from your Deck, but it cannot attack this turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x106E: {  # dragunity_remus -- Dragunity Remus (donor Petit Dragon)
        # FULL printed text, although only CLAUSE 2 is implemented in this build:
        # C1 (Synchro-material restriction) and C3 (GY self-SS + banish-on-leave +
        # Extra-Deck lock) are not built, and C4's once-per-turn latch is deferred
        # (user decision), so the discard/search can be used more than
        # once per turn. The text is left whole so it needs no edit when those land.
        # Set-code membership IS built: the "Dragunity" list 0x0209CBC0 is full
        # (21 real cards, no phantom, no slack in the region), so Remus DISPLACES
        # Dragunity Knight - Trident 0x2180 rather than joining (user's choice
        #). Dragon Ravine can fetch Remus; Trident stops counting as a
        # "Dragunity". See notes/dragunity-remus-findings.md.
        # Routed through card_text because "Dragunity Remus" (15 B) does not fit the
        # donor's in-place name slot ("Petit Dragon", 12 B).
        "e": ('Dragunity Remus',
             'Cannot be used as Synchro Material, except for the Synchro Summon of a "Dragunity" monster. You can discard this card; add 1 "Dragon Ravine" from your Deck to your hand. If you control a "Dragunity" monster: You can Special Summon this card from your GY, but banish it when it leaves the field, also you cannot Special Summon monsters from the Extra Deck for the rest of this turn, except Dragon monsters. You can only use each effect of "Dragunity Remus" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x10A5: {  # overtex_qoatlus -- Overtex Qoatlus (donor Prevent Rat
        "e": ('Overtex Qoatlus',
             'Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by shuffling 5 of your banished Dinosaur monsters into the Main Deck. Once per turn, when your opponent activates a Spell/Trap Card (Quick Effect): You can destroy 1 Dinosaur monster in your hand or face-up on your field, and if you do, negate the activation, and if you do that, destroy that card. If this card is sent to the GY by a card effect: You can add 1 "Evolution Pill" Spell from your Deck to your hand. You can only use this effect of "Overtex Qoatlus" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x18FA: {  # life_stream_dragon -- Life Stream Dragon (donor Steam Gyroid
        "e": ('Life Stream Dragon',
             '1 Tuner + "Power Tool Dragon" When this card is Synchro Summoned: You can make your LP become 4000. You take no effect damage. If this face-up card on the field would be destroyed, you can banish 1 Equip Spell Card from your Graveyard instead.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x107F: {  # coral_dragon -- Coral Dragon (donor B. Skull Dragon; whole card in-game confirmed by user 2026-11-09, SHIPPED to steps.STEPS)
        "e": ('Coral Dragon',
             '1 Tuner + 1+ non-Tuner monsters Once per turn: You can discard 1 card, then target 1 card your opponent controls; destroy it. If this Synchro Summoned card is sent from the field to the GY: You can draw 1 card. You can only use this effect of "Coral Dragon" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x170F: {  # ojamassimilation -- Ojamassimilation (donor Gryphon's Feather Duster; C1+C2, C3 pending)
        "e": ('Ojamassimilation',
             'Reveal 1 LIGHT Machine Fusion Monster from your Extra Deck and banish any number of "Ojama" monsters from your hand, face-up field, and/or GY; Special Summon Fusion Materials with different names whose names are specifically listed on the card you revealed, from your hand, Deck, and/or GY, equal to the number of monsters banished to activate this effect. You can banish this card from your GY, then target 3 of your banished "Ojama" monsters; shuffle them into the Deck, then draw 1 card.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x10E6: {  # sekkas_light -- Sekka's Light (donor Stop Defense)
        "e": ("Sekka's Light",
             'If you have no Spells/Traps in your GY: Draw 2 cards, also, for the rest of this Duel after you activate this card, you cannot activate Spell/Trap Cards or effects, except "Sekka\'s Light". You can banish this card from your GY; reveal 1 monster in your hand, shuffle it into the Deck, then, draw 1 card. You can only use each effect of "Sekka\'s Light" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x10FD: {  # that_grass_looks_greener -- That Grass Looks Greener (donor Sparks
        "e": ('That Grass Looks Greener',
             'If you have more cards in your Deck than your opponent does: Send cards from the top of your Deck to the Graveyard so you have the same number of cards in the Deck as your opponent.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x17F4: {  # obedience_schooled -- Obedience Schooled (donor Abyssal Designator)
        "e": ('Obedience Schooled',
             'If you control no monsters: Special Summon 3 Level 2 or lower Beast-Type Effect Monsters with different names from your Deck. Their effects are negated, and they are destroyed during the End Phase. If you activate this card, you cannot Special Summon for the rest of this turn, except Beast-Type monsters.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1777: {  # fire_formation_tenki -- Fire Formation - Tenki (donor Marshmallon Glasses)
        "e": ('Fire Formation - Tenki',
             'When this card is activated: You can add 1 Level 4 or lower Beast-Warrior monster from your Deck to your hand. All Beast-Warrior monsters you control gain 100 ATK. You can only activate 1 "Fire Formation - Tenki" per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x130A: {  # sacred_sword_seven_stars -- Sacred Sword of Seven Stars (donor Block Attack)
        "e": ('Sacred Sword of Seven Stars',
             'Banish 1 Level 7 monster from your hand or face-up from your side of the field; draw 2 cards. You can only activate 1 "Sacred Sword of Seven Stars" per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1E05: {  # infernoble -- Infernoble Knight - Renaud (donor Water Spirit)
        "e": ('Infernoble Knight - Renaud',
             'If you control a FIRE Warrior monster, you can Special Summon this card (from your hand). If Summoned this way, treat this card as a Tuner. You can only Special Summon "Infernoble Knight - Renaud" once per turn this way. If this card is Special Summoned: You can target 1 of your FIRE Warrior monsters, or 1 of your Equip Spells, that is banished or in your GY, except "Infernoble Knight - Renaud"; add it to your hand. You can only use this effect of "Infernoble Knight - Renaud" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1F71: {  # infernoble -- Infernoble Arms - Hauteclere (donor Psychic Sword
        "e": ('Infernoble Arms - Hauteclere',
             'While this card is equipped to a monster: You can target 1 face-up monster you control; this turn, you cannot declare attacks, except with that monster, also it gains the ability this turn to make a second attack during each Battle Phase, then destroy this card. If this card is sent to the GY because the equipped monster is sent to the GY: You can target 1 face-up monster on the field; destroy it. You can only use 1 "Infernoble Arms - Hauteclere" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1346: {  # infernoble -- Noble Arms Museum (donor Molten Destruction
        "e": ('Noble Arms Museum',
             'All FIRE Warrior monsters you control gain 500 ATK. Once per turn: You can pay 1200 LP; add 1 "Noble Arms" card from your Deck to your hand, except "Noble Arms Museum". Once per turn, if the previous effect was applied this turn: You can target 1 "Noble Knight" Monster Card in your Spell & Trap Zone; Special Summon it, also, if you activated this effect while you did not control "Infernoble Knight Emperor Charles", you cannot Special Summon monsters for the rest of this turn, except Warrior monsters.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x16DB: {  # infernoble -- The Continuing Epic of Charles (donor Big Burn
        "e": ('The Continuing Epic of Charles',
             'Reveal 1 "Noble Arms" Equip Spell in your hand, and if you do, Special Summon 1 "Infernoble Knight" monster from your hand or Deck, then either equip the revealed card to that monster, or send it to the GY. You can banish this card from your GY, then target 1 "Infernoble Knight Emperor Charles" you control; equip 1 "Noble Knight" monster from your hand or Deck to that monster as an Equip Spell that gives it 500 ATK. You can only use each effect of "The Continuing Epic of Charles" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1C39: {  # infernoble -- Infernoble Arms - Almace (donor Broken Bamboo Sword
        "e": ('Infernoble Arms - Almace',
             'While this card is equipped to a monster: You can equip 1 "Infernoble Arms" Equip Spell from your Deck or GY, except "Infernoble Arms - Almace", to 1 appropriate monster you control, then destroy this card. If this card is sent to the GY because the equipped monster is sent to the GY: You can target 1 of your FIRE Warrior monsters that is banished or in your GY; add it to your hand. You can only use 1 "Infernoble Arms - Almace" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1663: {  # infernoble -- Infernoble Arms - Durendal (donor Rod of the Mind's Eye
        "e": ('Infernoble Arms - Durendal',
             'While this card is equipped to a monster: You can add 1 Level 5 or lower FIRE Warrior monster from your Deck to your hand, then destroy this card. If this card is sent to the GY because the equipped monster is sent to the GY: You can target 1 Level 5 or lower FIRE Warrior monster in your GY; Special Summon it, also you cannot Special Summon monsters for the rest of the turn, except Warrior monsters. You can only use 1 "Infernoble Arms - Durendal" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x15E3: {  # infernoble -- Infernoble Arms - Joyeuse (donor Demotion
        "e": ('Infernoble Arms - Joyeuse',
             'While this card is equipped to a monster: You can target 1 FIRE Warrior monster in your GY; add it to your hand, then destroy this card. If this card is sent to the GY because the equipped monster is sent to the GY: You can Special Summon 1 FIRE Warrior monster from your hand. You can only use 1 "Infernoble Arms - Joyeuse" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1976: {  # infernoble -- Horn of Olifant (donor Simultaneous Loss
        "e": ('Horn of Olifant',
             'Activate 1 of these effects;\r\n\x9dBanish 1 Equip Spell you control or in your GY, then you can destroy 1 card on the field.\r\n\x9dDestroy 1 "Roland" monster you control, then Special Summon in Defense Position up to 3 FIRE Warrior monsters from your Deck, whose total Levels equal 9, but their effects are negated, also, until the end of your next turn after this effect resolves, you cannot Special Summon monsters, except Warrior monsters.\r\nYou can only activate 1 "Horn of Olifant" per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ('Horn of Olifant',
             'Activate 1 of these effects;\r\n●Banish 1 Equip Spell you control or in your GY, then you can destroy 1 card on the field.\r\n●Destroy 1 "Roland" monster you control, then Special Summon in Defense Position up to 3 FIRE Warrior monsters from your Deck, whose total Levels equal 9, but their effects are negated, also, until the end of your next turn after this effect resolves, you cannot Special Summon monsters, except Warrior monsters.\r\nYou can only activate 1 "Horn of Olifant" per turn.'),  # cp932/cp949: no 0x9D bullet -> U+25CF
        "k": ('Horn of Olifant',
             'Activate 1 of these effects;\r\n●Banish 1 Equip Spell you control or in your GY, then you can destroy 1 card on the field.\r\n●Destroy 1 "Roland" monster you control, then Special Summon in Defense Position up to 3 FIRE Warrior monsters from your Deck, whose total Levels equal 9, but their effects are negated, also, until the end of your next turn after this effect resolves, you cannot Special Summon monsters, except Warrior monsters.\r\nYou can only activate 1 "Horn of Olifant" per turn.'),  # cp932/cp949: no 0x9D bullet -> U+25CF
        "r": ('Horn of Olifant',
             'Activate 1 of these effects;\r\n●Banish 1 Equip Spell you control or in your GY, then you can destroy 1 card on the field.\r\n●Destroy 1 "Roland" monster you control, then Special Summon in Defense Position up to 3 FIRE Warrior monsters from your Deck, whose total Levels equal 9, but their effects are negated, also, until the end of your next turn after this effect resolves, you cannot Special Summon monsters, except Warrior monsters.\r\nYou can only activate 1 "Horn of Olifant" per turn.'),  # cp932/cp949: no 0x9D bullet -> U+25CF
    },
    0x1002: {  # infernoble -- Angelica, Princess of Noble Arms (donor Rabid Horseman; re-donored from Barox, C2 in-game confirmed there)
        "e": ('Angelica, Princess of Noble Arms',
             '1 Tuner + 1+ non-Tuner monsters\r\nIf this card is Special Summoned: You can add 1 "Horn of Olifant", or 1 card that mentions "Infernoble Knight Emperor Charles", from your Deck to your hand. When a card or effect is activated that targets this card on the field, or when this card is targeted for an attack (Quick Effect): You can send 1 FIRE Warrior monster from your Deck to the GY, and if you do, banish this card (until the End Phase), then you can Special Summon 1 "Roland" monster from your Deck or Extra Deck. You can only use each effect of "Angelica, Princess of Noble Arms" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x17EF: {  # infernoble -- Infernoble Knight Emperor Charles (donor Master of Oz
        "e": ('Infernoble Knight Emperor Charles',
             '1 Tuner + 1+ non-Tuner monsters\r\nIf an Equip Card becomes equipped to a monster on the field, even during the Damage Step: You can destroy 1 card on the field. During the End Phase: You can equip 1 Equip Spell from your hand or GY to this card, then you can equip 1 FIRE Warrior monster from your Deck to this card as an Equip Spell that gives it 500 ATK. You can only use each effect of "Infernoble Knight Emperor Charles" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1118: {  # infernoble -- Infernoble Knight Captain Oliver (donor Labyrinth Tank
        "e": ('Infernoble Knight Captain Oliver',
             '1 Tuner + 1+ non-Tuner monsters\r\nWhen this card declares an attack while equipped: You can target 1 face-up card on the field; destroy it. During your Main Phase, except the turn this card was sent to the GY: You can target 1 Warrior monster you control; Special Summon this card from your GY as a Tuner, and if you do, equip that monster you control to this card as an Equip Spell that gives it 500 ATK. You can only use this effect of "Infernoble Knight Captain Oliver" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FEB: {  # infernoble -- Infernoble Knight Captain Roland (donor Thousand Dragon
        "e": ('Infernoble Knight Captain Roland',
             '1 Tuner + 1+ non-Tuner monsters\r\nIf this card is Synchro Summoned: You can activate this effect; during the End Phase of this turn, send 1 Equip Spell from your Deck to the GY, then add 1 Warrior monster from your Deck to your hand. During the Main Phase, if this card is in your GY (Quick Effect): You can target 1 Warrior monster you control; equip this card to that monster you control as an Equip Spell that gives it 500 ATK. You can only use each effect of "Infernoble Knight Captain Roland" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x160B: {  # infernoble -- Courageous Crimson Chevalier Bradamante (donor Sonic Duck)
        "e": ('Courageous Crimson Chevalier Bradamante',
             '(This card is always treated as an "Infernoble Knight" card.)\r\nYou can discard this card, then target 1 Warrior monster you control; equip it with 1 Equip Spell from your Deck that can equip to it. When this card, not equipped with an Equip Card, is destroyed by battle with an opponent\'s monster and sent to the GY: You can Special Summon this card, and if you do, equip that monster your opponent controls to this card. You can only use each effect of "Courageous Crimson Chevalier Bradamante" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FD4: {  # infernoble -- Infernoble Knight Astolfo (donor Griffore)
        "e": ('Infernoble Knight Astolfo',
             'You can banish 1 FIRE Warrior monster from your hand or GY; Special Summon this card from your hand, then you can make this card\'s Level become the Level of that banished monster. You can banish this card from your GY; Special Summon this banished card during your second Standby Phase after this effect\'s activation, then you can Special Summon 1 of your FIRE Warrior monsters that is banished or in your GY. You can only use each effect of "Infernoble Knight Astolfo" once per Duel.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FDB: {  # infernoble -- Infernoble Knight - Roland (donor Killer Needle)
        "e": ('Infernoble Knight - Roland',
             '(Quick Effect): You can target 1 face-up monster you control; equip this card from your hand to that target as an Equip Spell that gives that card 500 ATK. During the End Phase, if this card is in the GY because it was sent there this turn: You can add 1 FIRE Warrior monster, except "Infernoble Knight - Roland", or 1 Equip Spell from your Deck to your hand. You can only use each effect of "Infernoble Knight - Roland" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FE6: {  # infernoble -- Infernoble Knight Ricciardetto (donor Tiger Axe)
        "e": ('Infernoble Knight Ricciardetto',
             'You can banish this card from your hand or GY; Special Summon 1 Level 4 or lower FIRE Warrior monster from your hand as a Tuner. If this card is Normal or Special Summoned: You can target 1 Level 4 or lower FIRE Warrior monster in your GY, except "Infernoble Knight Ricciardetto"; Special Summon it, also you cannot Special Summon monsters for the rest of this turn, except Warrior monsters. You can only use 1 "Infernoble Knight Ricciardetto" effect per turn, and only once that turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FC1: {  # infernoble -- Infernoble Knight Turpin (donor Beaver Warrior)
        "e": ('Infernoble Knight Turpin',
             'While this card is an Equip Card, the equipped monster can be treated as a Tuner if used as Synchro Material. You can only use each of the following effects of "Infernoble Knight Turpin" once per turn. If you control a monster equipped with an Equip Card: You can Special Summon this card from your hand or GY, but if you Summon it from the GY, banish it when it leaves the field. If this card is in your GY: You can target 1 Warrior monster you control; equip this card to that monster you control as an Equip Spell.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x1E04: {  # infernoble -- Infernoble Knight Oliver (donor Tune Warrior)
        "e": ('Infernoble Knight Oliver',
             'While this card is an Equip Card, your opponent cannot target the equipped monster with card effects. You can only use each of the following effects of "Infernoble Knight Oliver" once per turn. You can send 1 FIRE Warrior monster or 1 Equip Spell from your hand or face-up field to the GY; Special Summon this card from your hand as a Level 1 monster. If this card is in your GY: You can target 1 Warrior monster you control; equip this card to that monster you control.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x139A: {  # infernoble -- Infernoble Knight Maugis (donor Wolf Axwielder)
        "e": ('Infernoble Knight Maugis',
             'While this card is an Equip Card, the equipped monster cannot be destroyed by battle. You can only use each of the following effects of "Infernoble Knight Maugis" once per turn. If this card is sent to the GY: You can shuffle into the Deck, 3 of your other FIRE Warrior monsters and/or "Noble Arms" cards that are banished or in your GY; draw 1 card. If this card is in your GY: You can target 1 Warrior monster you control; equip this card to that monster you control.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x13A3: {  # infernoble -- Infernoble Knight Ogier (donor Robotic Knight)
        "e": ('Infernoble Knight Ogier',
             'While this card is an Equip Card, the equipped monster cannot be destroyed by card effects. You can only use each of the following effects of "Infernoble Knight Ogier" once per turn. If this card is Normal or Special Summoned: You can send 1 "Noble Arms" card, or 1 FIRE Warrior monster except "Infernoble Knight Ogier", from your Deck to the GY. If this card is in your GY: You can target 1 Warrior monster you control; equip this card to that monster you control.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x160A: {  # eva -- Eva (donor Aitsu)
        "e": ('Eva',
             'If this card is sent to the GY: You can banish up to 2 other LIGHT Fairy monsters from your field and/or GY; add the same number of Level 2 or lower LIGHT Fairy monsters with different names from your Deck to your hand, except "Eva". You can only use this effect of "Eva" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FD0: {  # uni_zombie -- Uni-Zombie (donor Illusionist Faceless Mage
        "e": ('Uni-Zombie',
             'You can target 1 face-up monster on the field; discard 1 card, and if you do, increase that target\'s Level by 1. You can target 1 face-up monster on the field; monsters you control cannot attack for the rest of this turn, except Zombie monsters, also send 1 Zombie monster from your Deck to the GY, and if you do, increase that target\'s Level by 1. You can only use each effect of "Uni-Zombie" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FE8: {  # denko_sekka -- Denko Sekka (donor Kojikocy
        "e": ('Denko Sekka',
             'Cannot be Special Summoned. While you control no Set Spells/Traps, neither player can Set Spells/Traps nor activate Spell/Trap Cards that are Set on the field.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x111E: {  # disguise_copycat -- Disguise, the Copycat Hero (donor Monster Tamer; NOT shipped)
        "e": ('Disguise, the Copycat Hero',
             'If you have an Equip Spell in your field or GY: You can Special Summon this card from your hand. If this card is Normal or Special Summoned: You can add 1 "Cursed Copycat Noble Arms" from your Deck to your hand. While this card is equipped with an Equip Card: You can target 1 non-Tuner Warrior monster on the field with a Level; this card\'s Level, also its name, become the same as that monster\'s until the End Phase. You can only use each effect of "Disguise, the Copycat Hero" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x10E3: {  # disguise_copycat -- Cursed Copycat Noble Arms (donor Cyber Shield; NOT shipped)
        "e": ('Cursed Copycat Noble Arms',
             'The equipped monster gains 200 ATK/DEF for each Equip Spell in your field and GY. While this card is equipped to a Warrior monster: You can activate this effect; you cannot Special Summon for the rest of this turn, except Warrior monsters, also Special Summon 1 Warrior monster with the same Attribute and Level as the equipped monster but a different name from your Deck, and if you do, equip it with this card, then destroy the monster this card was equipped to. You can only use this effect of "Cursed Copycat Noble Arms" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0xFD9: {  # noble_knight_medraut -- Noble Knight Medraut (donor Armored Lizard; NOT shipped)
        "e": ('Noble Knight Medraut',
             'This card is treated as a Normal Monster while face-up on the field. While equipped with a "Noble Arms" Equip Spell, this card becomes an Effect Monster with this effect.\r\n\x9dThis card becomes DARK and its Level is increased by 1. Once per turn, if you control no other monsters: You can Special Summon 1 "Noble Knight" monster from your Deck in Defense Position, except "Noble Knight Medraut", and if you do, destroy 1 Equip Spell you control.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ('Noble Knight Medraut',
             'This card is treated as a Normal Monster while face-up on the field. While equipped with a "Noble Arms" Equip Spell, this card becomes an Effect Monster with this effect.\r\n●This card becomes DARK and its Level is increased by 1. Once per turn, if you control no other monsters: You can Special Summon 1 "Noble Knight" monster from your Deck in Defense Position, except "Noble Knight Medraut", and if you do, destroy 1 Equip Spell you control.'),
        "k": ('Noble Knight Medraut',
             'This card is treated as a Normal Monster while face-up on the field. While equipped with a "Noble Arms" Equip Spell, this card becomes an Effect Monster with this effect.\r\n●This card becomes DARK and its Level is increased by 1. Once per turn, if you control no other monsters: You can Special Summon 1 "Noble Knight" monster from your Deck in Defense Position, except "Noble Knight Medraut", and if you do, destroy 1 Equip Spell you control.'),
        "r": ('Noble Knight Medraut',
             'This card is treated as a Normal Monster while face-up on the field. While equipped with a "Noble Arms" Equip Spell, this card becomes an Effect Monster with this effect.\r\n●This card becomes DARK and its Level is increased by 1. Once per turn, if you control no other monsters: You can Special Summon 1 "Noble Knight" monster from your Deck in Defense Position, except "Noble Knight Medraut", and if you do, destroy 1 Equip Spell you control.'),
    },
    0xFC7: {  # immortal_phoenix_gearfried -- Immortal Phoenix Gearfried (donor Judge Man; NOT shipped)
        "e": ('Immortal Phoenix Gearfried',
             'You can banish 1 Equip Spell from your field or GY; Special Summon this card from your hand.\r\nAt the start of the Damage Step, if this card attacks: You can equip 1 face-up monster on the field to this card (max. 1) as an Equip Spell that gives this card 500 ATK.\r\nWhen a monster effect is activated (Quick Effect): You can send 1 face-up Equip Card you control to the GY; negate the activation, and if you do, destroy it.\r\nYou can only use each effect of "Immortal Phoenix Gearfried" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ('Immortal Phoenix Gearfried',
             'You can banish 1 Equip Spell from your field or GY; Special Summon this card from your hand.\r\nAt the start of the Damage Step, if this card attacks: You can equip 1 face-up monster on the field to this card (max. 1) as an Equip Spell that gives this card 500 ATK.\r\nWhen a monster effect is activated (Quick Effect): You can send 1 face-up Equip Card you control to the GY; negate the activation, and if you do, destroy it.\r\nYou can only use each effect of "Immortal Phoenix Gearfried" once per turn.'),
        "k": ('Immortal Phoenix Gearfried',
             'You can banish 1 Equip Spell from your field or GY; Special Summon this card from your hand.\r\nAt the start of the Damage Step, if this card attacks: You can equip 1 face-up monster on the field to this card (max. 1) as an Equip Spell that gives this card 500 ATK.\r\nWhen a monster effect is activated (Quick Effect): You can send 1 face-up Equip Card you control to the GY; negate the activation, and if you do, destroy it.\r\nYou can only use each effect of "Immortal Phoenix Gearfried" once per turn.'),
        "r": ('Immortal Phoenix Gearfried',
             'You can banish 1 Equip Spell from your field or GY; Special Summon this card from your hand.\r\nAt the start of the Damage Step, if this card attacks: You can equip 1 face-up monster on the field to this card (max. 1) as an Equip Spell that gives this card 500 ATK.\r\nWhen a monster effect is activated (Quick Effect): You can send 1 face-up Equip Card you control to the GY; negate the activation, and if you do, destroy it.\r\nYou can only use each effect of "Immortal Phoenix Gearfried" once per turn.'),
    },
    0x10EA: {  # phoenix_gearblade -- Phoenix Gearblade (donor Invigoration, Equip Spell; text user-supplied 2026-11-06, NOT shipped)
        "e": ('Phoenix Gearblade',
             'Equip only to a Warrior or FIRE monster. It gains 300 ATK.\r\nAt the end of the Damage Step, if the equipped monster attacked: You can send this card to the GY; during this Battle Phase, each of your Warrior monsters and FIRE monsters can make a second attack.\r\nIf this card is sent to the GY, or banished, to activate a monster effect: You can add this card to your hand. You can only use this effect of "Phoenix Gearblade" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": ('Phoenix Gearblade',
             'Equip only to a Warrior or FIRE monster. It gains 300 ATK.\r\nAt the end of the Damage Step, if the equipped monster attacked: You can send this card to the GY; during this Battle Phase, each of your Warrior monsters and FIRE monsters can make a second attack.\r\nIf this card is sent to the GY, or banished, to activate a monster effect: You can add this card to your hand. You can only use this effect of "Phoenix Gearblade" once per turn.'),
        "k": ('Phoenix Gearblade',
             'Equip only to a Warrior or FIRE monster. It gains 300 ATK.\r\nAt the end of the Damage Step, if the equipped monster attacked: You can send this card to the GY; during this Battle Phase, each of your Warrior monsters and FIRE monsters can make a second attack.\r\nIf this card is sent to the GY, or banished, to activate a monster effect: You can add this card to your hand. You can only use this effect of "Phoenix Gearblade" once per turn.'),
        "r": ('Phoenix Gearblade',
             'Equip only to a Warrior or FIRE monster. It gains 300 ATK.\r\nAt the end of the Damage Step, if the equipped monster attacked: You can send this card to the GY; during this Battle Phase, each of your Warrior monsters and FIRE monsters can make a second attack.\r\nIf this card is sent to the GY, or banished, to activate a monster effect: You can add this card to your hand. You can only use this effect of "Phoenix Gearblade" once per turn.'),
    },
    0x0FED: {  # predaplant -- Predaplant Darlingtonia Cobra (donor Jellyfish; SHIPPED 2026-11-06; art registered in data/card_art.py 2026-11-09)
        "e": ('Predaplant Darlingtonia Cobra',
             'If this card is Special Summoned by the effect of a "Predaplant" monster: You can add 1 "Polymerization" Spell Card or "Fusion" Spell Card from your Deck to your hand. You can only use this effect of "Predaplant Darlingtonia Cobra" once per Duel.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x17CF: {  # predaplant -- Predaplant Ophrys Scorpio (donor Skull Dog Marron; SHIPPED 2026-11-06; art registered in data/card_art.py 2026-11-09)
        "e": ('Predaplant Ophrys Scorpio',
             'If this card is Normal or Special Summoned: You can send 1 monster from your hand to the GY; Special Summon 1 "Predaplant" monster from your Deck, except "Predaplant Ophrys Scorpio". You can only use this effect of "Predaplant Ophrys Scorpio" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
    0x0FDD: {  # block_dragon -- Block Dragon (donor Giant Flea; whole card in-game confirmed by user 2026-11-09, SHIPPED 2026-11-09)
        "e": ('Block Dragon',
             'Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand or GY) by banishing 3 EARTH monsters from your hand and/or GY. Rock monsters you control cannot be destroyed, except by battle. If this card is sent from the field to the GY: You can add up to 3 Rock monsters from your Deck to your hand, whose total Levels equal 8. You can only use this effect of "Block Dragon" once per turn.'),
        "f": None,
        "g": None,
        "i": None,
        "s": None,
        "j": None,
        "k": None,
        "r": None,
    },
}


def resolve(cid: int, lang: str) -> tuple[bytes, bytes]:
    """(name, desc) as encoded bytes for *lang*, falling back to English."""
    entry = CARD_TEXT[cid]
    text = entry.get(lang) or entry["e"]
    enc = ENCODING[lang]
    out = tuple(t if isinstance(t, bytes) else t.encode(enc) for t in text)
    assert len(out[0]) <= MAX_NAME, (
        f"{cid:#06x} {lang}: name is {len(out[0])} B > {MAX_NAME}")
    assert len(out[1]) <= MAX_DESC, (
        f"{cid:#06x} {lang}: desc is {len(out[1])} B > {MAX_DESC}")
    assert b'\x00' not in out[0] + out[1], f"{cid:#06x} {lang}: embedded NUL"
    return out


# ---------------------------------------------------------------------------
# The blob rewriter. ONE implementation -- _build_card_text.py and
# boggart_knight.apply_stats_and_text both use it, so the index-order
# invariant cannot drift between them.
# ---------------------------------------------------------------------------
import struct  # noqa: E402  (kept next to the code that uses it)

ALIGN = 4  # every stock card_indx offset is 4-aligned


def prop_index(prop: bytes, cid: int) -> int:
    """card_indx entry number for *cid*, read from card_prop.bin.

    Entry *i* lives at byte offset ``i * 8`` in BOTH card_prop.bin and
    card_indx_<L>.bin. ⚠️ boggart_knight's own scan uses ``8 + i * 8`` and
    so reports a number one lower for the same bytes -- convert with ``+ 1``.
    """
    for i in range(len(prop) // 8):
        if struct.unpack_from("<H", prop, i * 8)[0] & 0x3FFF == cid:
            return i
    raise KeyError(f"cid {cid:#06x} not found in card_prop.bin")


def _cstr(blob: bytes, off: int) -> bytes:
    end = blob.find(b"\x00", off)
    if end < 0:
        raise ValueError(f"unterminated string at {off:#x}")
    return blob[off:end]


def rebuild_blobs(idx: bytes, names: bytes, descs: bytes,
                  overrides: dict[int, tuple[bytes, bytes]]) -> tuple[bytes, bytes, bytes]:
    """Re-emit both blobs IN INDEX ORDER, substituting ``{entry: (name, desc)}``.

    Returns ``(idx, names, descs)`` with every offset recomputed, so each entry's
    gap to the next equals that string's own 4-aligned length -- the stock
    invariant, and the one that must never be broken (see the module docstring).
    With no overrides this is the byte-for-byte identity on a stock blob.
    """
    count = len(idx) // 8
    out_idx = bytearray(idx)
    blobs = []
    for sel, src in ((0, names), (1, descs)):
        offs = [struct.unpack_from("<II", idx, i * 8)[sel] for i in range(count)]
        # ⚠️ Every stock blob opens with a 4-BYTE PREFIX: entry 0's offset is 4,
        # not 0. Dropping it shifts every string 4 bytes earlier -- which still
        # renders (rom_cardtext.nds shipped that way and was in-game confirmed),
        # but it is a silent deviation from stock and it makes the identity
        # self-check below impossible. Carry the prefix through verbatim.
        out = bytearray(src[:offs[0]])
        for i in range(count - 1):                      # last entry is the end sentinel
            over = overrides.get(i)
            text = over[sel] if over is not None else _cstr(src, offs[i])
            struct.pack_into("<I", out_idx, i * 8 + sel * 4, len(out))
            out += text + b"\x00"
            if len(out) % ALIGN:
                out += b"\x00" * (ALIGN - len(out) % ALIGN)
        struct.pack_into("<I", out_idx, (count - 1) * 8 + sel * 4, len(out))
        blobs.append(bytes(out))
    return bytes(out_idx), blobs[0], blobs[1]


# ---------------------------------------------------------------------------
# Alphabetical order: card_sort2_<L> / card_sort_<L> / card_kana1_<L> / card_kana2_<L>
#
# Renaming a card moves where it belongs in the deck editor's A-Z list, so these
# four tables have to move with it. Measured from stock (4306 u16 each):
#
#   card_sort2_<L>[position] = card index   -- the A-Z order
#   card_sort_<L>[card index] = position    -- EXACTLY the inverse permutation,
#                                              verified in all 8 languages
#   card_kana1_<L>[card index] = first character of the name  (A-Z jump bar)
#   card_kana2_<L>[card index] = second character
#
# COLLATION, derived by fitting stock: decode cp1252, expand ligatures
# (ss/oe/ae), lowercase, fold accents, drop "-" and "'", keep spaces. That
# reproduces e / f / i EXACTLY (0 inversions, 0 positions differ out of 4306).
# g has 1 anomaly and s has 3, all on cards whose name STARTS with typographic
# punctuation ("A"-Zellen, iHuracan!, ?Bajada?) -- none of ours.
#
# ⚠️ j / k / r are NOT re-sorted. Their order is kana/hangul-based (1400-1800
# inversions under this key), and a wrong sort there is a silent regression that
# cannot be validated from here. Cards keep their existing slot in those three.
# ---------------------------------------------------------------------------
SORTED_LANGS = "efgis"          # languages whose collation is reproduced
_LIGATURES = {"ß": "ss", "œ": "oe", "æ": "ae"}
_DROP = set("-'„“”‘’")


def sort_key(raw_name: bytes) -> str:
    """Collation key for a raw-encoded card name (Latin languages)."""
    import unicodedata
    s = raw_name.decode("cp1252", "replace").lower()
    s = "".join(_LIGATURES.get(c, c) for c in s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s if c not in _DROP)


def resort(sort2: list[int], keys: dict[int, str], changed: set[int]) -> list[int]:
    """Re-place *changed* cards in the existing A-Z permutation.

    Pulls each changed card out and binary-searches it back in by key. Every
    untouched card keeps its exact stock position, so the languages whose
    collation this module does not perfectly reproduce (g, s) keep their
    anomalies instead of being "corrected" into a different order.
    """
    kept = [c for c in sort2 if c not in changed]
    for c in sorted(changed, key=lambda x: keys[x]):
        k = keys[c]
        lo, hi = 0, len(kept)
        while lo < hi:
            mid = (lo + hi) // 2
            if keys[kept[mid]] < k:
                lo = mid + 1
            else:
                hi = mid
        kept.insert(lo, c)
    return kept


def rebuild_sort(idx: bytes, names: bytes, sort2_b: bytes, kana1_b: bytes,
                 kana2_b: bytes, changed: set[int]) -> tuple[bytes, bytes, bytes, bytes]:
    """Return (card_sort2, card_sort, card_kana1, card_kana2) after a rename."""
    count = len(sort2_b) // 2
    sort2 = list(struct.unpack("<%dH" % count, sort2_b))
    k1 = list(struct.unpack("<%dH" % count, kana1_b))
    k2 = list(struct.unpack("<%dH" % count, kana2_b))

    def name_of(c):
        o = struct.unpack_from("<II", idx, c * 8)[0]
        return names[o:names.find(b"\x00", o)]

    keys = {c: sort_key(name_of(c)) for c in range(count)}
    sort2 = resort(sort2, keys, changed)

    sort1 = [0] * count
    for pos, c in enumerate(sort2):
        sort1[c] = pos

    for c in changed:                       # A-Z jump bar: first/second character
        k = keys[c]
        k1[c] = ord(k[0]) if len(k) > 0 else 0
        k2[c] = ord(k[1]) if len(k) > 1 else 0

    return (struct.pack("<%dH" % count, *sort2), struct.pack("<%dH" % count, *sort1),
            struct.pack("<%dH" % count, *k1), struct.pack("<%dH" % count, *k2))


def apply_to_rom(out_path: str, cid: int, langs: str = "".join(LANGS)) -> None:
    """Write *cid*'s full printed text into the ROM at *out_path*, in place.

    For patch modules that do NOT route through
    boggart_knight.apply_stats_and_text. Idempotent: re-running it on an
    already-written ROM produces the same bytes. A cid absent from CARD_TEXT is
    a no-op, so calling it unconditionally is safe.
    """
    if cid not in CARD_TEXT:
        return
    import ndspy.rom
    from otn_enhanced.rom.pac import build_modified_pac, parse_format_v1

    rom = ndspy.rom.NintendoDSRom.fromFile(out_path)

    def _iter(folder, prefix=""):
        for nm in folder.files:
            yield prefix + nm
        for sub_nm, sub in folder.folders:
            yield from _iter(sub, prefix + sub_nm + "/")

    pac_path = next(p for p in _iter(rom.filenames) if p.lower().endswith("bin2.pac"))
    fid = rom.filenames.idOf(pac_path)
    bin2 = bytes(rom.files[fid])
    arc = parse_format_v1(bin2, pac_path)
    by_name = {f.get_clean_name().lower(): i for i, f in enumerate(arc.files)}

    def raw(n):
        f = arc.files[by_name[n]]
        return bin2[f.address:f.address + f.size]

    entry = prop_index(raw("card_prop.bin"), cid)
    repl = {}
    for L in langs:
        if f"card_indx_{L}.bin" not in by_name:
            continue
        idx, names, descs = (raw(f"card_indx_{L}.bin"),
                             raw(f"card_name_{L}.bin"), raw(f"card_desc_{L}.bin"))
        idx, names, descs = rebuild_blobs(idx, names, descs, {entry: resolve(cid, L)})
        assert_gaps_ok(idx, names, descs, where=f"[{L}] cid {cid:#06x}")
        repl[by_name[f"card_indx_{L}.bin"]] = idx
        repl[by_name[f"card_name_{L}.bin"]] = names
        repl[by_name[f"card_desc_{L}.bin"]] = descs

        if L in SORTED_LANGS:               # move the card in the A-Z list too
            s2, s1, k1, k2 = rebuild_sort(
                idx, names, raw(f"card_sort2_{L}.bin"), raw(f"card_kana1_{L}.bin"),
                raw(f"card_kana2_{L}.bin"), {entry})
            repl[by_name[f"card_sort2_{L}.bin"]] = s2
            repl[by_name[f"card_sort_{L}.bin"]] = s1
            repl[by_name[f"card_kana1_{L}.bin"]] = k1
            repl[by_name[f"card_kana2_{L}.bin"]] = k2

    rom.files[fid] = build_modified_pac(bin2, pac_path, repl)
    rom.saveToFile(out_path)
    n, d = resolve(cid, "e")
    print(f"  card_text: {cid:#06x} {n.decode(ENCODING['e'])!r} "
          f"({len(d)}B desc) -> {len(langs)} languages")


def check_rom_text(rom_path: str, cid: int, langs: str = "".join(LANGS)) -> tuple[bool, str]:
    """Does the ROM's name+desc for *cid* equal what CARD_TEXT says it should be?

    THE correct text assertion for any cid in CARD_TEXT, and the one a patch's `verify()` should
    use. Returns (ok, one-line summary).

    WHY THIS EXISTS. `apply_stats_and_text` has two paths: a cid carried by CARD_TEXT takes the
    INDEX-ORDER RE-EMIT, which writes the full printed text and is NOT limited by the donor's
    original slot; any other cid falls back to a strictly IN-PLACE write, which is why modules
    written before that change define abbreviated `NEW_NAME` / `NEW_DESC` constants.

    Five shipped modules -- grapha, ceruli, ninja_grandmaster_hanzo, white_dragon_ninja,
    accel_synchron -- kept asserting those abbreviations in `verify()` long after their cids
    joined CARD_TEXT, so the sweep reported them as failures for months while the ROM was right
    all along. accel_synchron's check even demanded a 463 B string fit "the 44 B in-place slot".
    Asserting against CARD_TEXT instead cannot drift that way: it is the same source the writer
    uses. (See notes/verify-sweep-failures.md.)

    A cid absent from CARD_TEXT returns (True, "...not carried..."), so calling it unconditionally
    is safe -- such a card's text is the caller's own in-place constants to check.
    """
    if cid not in CARD_TEXT:
        return True, f"card_text does not carry {cid:#06x}; its text is the module's own"

    import ndspy.rom
    from otn_enhanced.rom.pac import parse_format_v1

    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)

    def _iter(folder, prefix=""):
        for nm in folder.files:
            yield prefix + nm
        for sub_nm, sub in folder.folders:
            yield from _iter(sub, prefix + sub_nm + "/")

    pac_path = next(p for p in _iter(rom.filenames) if p.lower().endswith("bin2.pac"))
    bin2 = bytes(rom.files[rom.filenames.idOf(pac_path)])
    arc = parse_format_v1(bin2, pac_path)
    by_name = {f.get_clean_name().lower(): f for f in arc.files}

    def raw(n):
        f = by_name[n]
        return bin2[f.address:f.address + f.size]

    entry = prop_index(raw("card_prop.bin"), cid)
    bad = []
    for L in langs:
        if f"card_indx_{L}.bin" not in by_name:
            continue
        idx, names, descs = (raw(f"card_indx_{L}.bin"),
                             raw(f"card_name_{L}.bin"), raw(f"card_desc_{L}.bin"))
        n_off, d_off = struct.unpack_from("<II", idx, entry * 8)
        want_n, want_d = resolve(cid, L)
        got_n, got_d = _cstr(names, n_off), _cstr(descs, d_off)
        if got_n != want_n:
            bad.append(f"[{L}] name {got_n!r} != {want_n!r}")
        elif got_d != want_d:
            bad.append(f"[{L}] desc {len(got_d)}B != card_text's {len(want_d)}B")
    if bad:
        return False, f"{cid:#06x} text differs from card_text in {len(bad)}: " + "; ".join(bad[:3])
    n, _ = resolve(cid, "e")
    return True, (f"{cid:#06x} name+desc match card_text in all {len(langs)} languages "
                  f"({n.decode(ENCODING['e'])!r})")


def assert_gaps_ok(idx: bytes, names: bytes, descs: bytes, where: str = "") -> None:
    """The invariant a freeze taught us: ascending, gap == the string's padded length."""
    count = len(idx) // 8
    for sel, blob, what in ((0, names, "name"), (1, descs, "desc")):
        offs = [struct.unpack_from("<II", idx, i * 8)[sel] for i in range(count)]
        assert offs[-1] == len(blob), f"{where} {what}: sentinel != file size"
        for i in range(count - 1):
            gap = offs[i + 1] - offs[i]
            assert gap > 0, f"{where} {what} entry {i}: NEGATIVE gap {gap}"
            want = len(_cstr(blob, offs[i])) + 1
            want += (-want) % ALIGN
            assert gap == want, f"{where} {what} entry {i}: gap {gap} != padded {want}"
