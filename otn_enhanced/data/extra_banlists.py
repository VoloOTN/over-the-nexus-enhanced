"""Four extra built-in Forbidden/Limited lists: Mar 2010, Mar 2011, Sep 2011, Mar 2012.

Duelist Menu -> Forbidden/Limited Card List. bin.pac ships limit200609/200709/200809/
200909.bin (plus 200703) but the game only ever opens the one path literal
"Bin/limit201009.bin" (arm9 0x020AB848). Each file's header +2 is its own name id
(text 0x514+id). Since 2026-10-08 those four unused files are REWRITTEN from LISTS below
(fill in the card names) and stamped with the name ids of the game's own, otherwise
unused, labels: 0x13 "List - March, 2010", 0x15 "List - March, 2011",
0x16 "List - September, 2011", 0x17 "List - March, 2012". No text is edited.

load_list (arm9 Thumb 0x0202AC90), kind 0 (built-in) section 0x0202ACCE..0x0202AD46 is
rewritten IN PLACE (no free arm9 space is proven) to:
  * write "YY" into the path (chars 11,12) before opening it:
        idx 0..3 -> "10" (2010-09; idx 1/2 keep their No Banlist / Up-to-1 stamps)
        idx 4..7 -> "06","07","08","09"  (= idx+2)
  * stamp idx 1/2 the same as stock (name 0x52+idx, flags = idx), compacted, and buffer+4 =
    0x100+idx*16 (stock). Fixed 2026-10-05: the first shipped build wrote that to cache+4 =
    0x02122118, a separate struct, instead of buffer+4;
  * drop the stock's redundant second "*r6 = 0" (the prologue 0x0202AC96 already did it).
The exit 0x0202AD46 and the literal pool 0x0202AD4C/50/54 stay where they are (the
kind-1 section uses them).

Menu builder (overlay 8, 0x02168654), built-in loop:
  0x02168678  cmp r0,#0          -> orrs r0,r0,r6,lsr #2   idx>=4 shown regardless of the
                                                            save's enable bitmap (word0 has
                                                            bits 0..2 only); idx 3 stays hidden
  0x021686BC  cmp r6,#3          -> cmp r6,#8

Mar 2007 (limit200703) is NOT exposed: it needs a third path digit and the block has no room.
Ceiling: the menu array holds 88 entries (+0xCC..+0x64C), so 4 more built-ins overflow it
only if more than 80 of the 85 saved-list slots are in use.
"""
from __future__ import annotations

import struct
from pathlib import Path

import capstone
import ndspy.code
import ndspy.rom

from otn_enhanced.effects import common

SRC = "data/over_the_nexus/working/rom_no_banlist_test.nds"
OUT = "data/over_the_nexus/working/rom_extra_banlists_test.nds"

ARM9 = 0x02000000
BLOCK, EXIT = 0x0202ACCE, 0x0202AD46
LIT_CACHE, LIT_BUF, LIT_PATH = 0x0202AD4C, 0x0202AD50, 0x0202AD54
FILE_LOAD, MEMSET, MEMCPY, FILE_FREE = 0x020168E8, 0x020895FC, 0x02089774, 0x020164DC
STOCK_BLOCK = bytes.fromhex(
    "002e01d0002030701d4801888d4202d14088844230d01b4804210022ebf7fdfd"
    "0a22174f061c381c002192015ef080ec3388f822301cd21a53000a229201391c"
    "d21a5ef030ed0d48012c0580448002d0022c04d007e053207880012002e05420"
    "78800220f880012021010002091804488180301cebf7cbfb")

# Menu slot (file the path digits open) -> the list it holds. Fill in CARD NAMES (as in
# default_banlist). Cards not listed may be used at 3. Max 248 entries per list:
# load_list copies 0x90 + 2*count bytes into the 0x280-byte buffer 0x02121E94.
LISTS = {
    "limit200609.bin": {"name_id": 0x13,       # List - March, 2010
                        "Forbidden": [
                            'Black Luster Soldier - Envoy of the Beginning',
                            'Chaos Emperor Dragon - Envoy of the End',
                            'Cyber Jar',
                            'Cyber-Stein',
                            'Dark Magician of Chaos',
                            'Destiny Hero - Disk Commander',
                            'Fiber Jar',
                            'Magical Scientist',
                            'Magician of Faith',
                            'Makyura the Destructor',
                            'Sinister Serpent',
                            'Tribe-Infecting Virus',
                            'Tsukuyomi',
                            'Victory Dragon',
                            'Witch of the Black Forest',
                            'Yata-Garasu',
                            'Thousand-Eyes Restrict',
                            'Dark Strike Fighter',
                            'Change of Heart',
                            'Confiscation',
                            'Dark Hole',
                            'Delinquent Duo',
                            'Dimension Fusion',
                            'Graceful Charity',
                            'Harpie\'s Feather Duster',
                            'Metamorphosis',
                            'Monster Reborn',
                            'Painful Choice',
                            'Pot of Greed',
                            'Raigeki',
                            'The Forceful Sentry',
                            'Card of Safe Return',
                            'Mirage of Nightmare',
                            'Temple of the Kings',
                            'Butterfly Dagger - Elma',
                            'Premature Burial',
                            'Snatch Steal',
                            'Crush Card Virus',
                            'Exchange of the Spirit',
                            'Last Turn',
                            'Ring of Destruction',
                            'Sixth Sense',
                            'Time Seal',
                            'Imperial Order',
                        ], "Limited": [
                            'Blackwing - Gale the Whirlwind',
                            'Card Trooper',
                            'Chaos Sorcerer',
                            'Dark Armed Dragon',
                            'Elemental Hero Stratos',
                            'Exodia the Forbidden One',
                            'Gladiator Beast Bestiari',
                            'Gorz the Emissary of Darkness',
                            'Lumina, Lightsworn Summoner',
                            'Marshmallon',
                            'Mezuki',
                            'Mind Master',
                            'Morphing Jar',
                            'Necro Gardna',
                            'Necroface',
                            'Neo-Spacian Grand Mole',
                            'Night Assailant',
                            'Plaguespreader Zombie',
                            'Rescue Cat',
                            'Sangan',
                            'Snipe Hunter',
                            'Spirit Reaper',
                            'Summoner Monk',
                            'Tragoedia',
                            'Left Arm of the Forbidden One',
                            'Right Arm of the Forbidden One',
                            'Left Leg of the Forbidden One',
                            'Right Leg of the Forbidden One',
                            'Black Rose Dragon',
                            'Brionac, Dragon of the Ice Barrier',
                            'Goyo Guardian',
                            'Allure of Darkness',
                            'Brain Control',
                            'Card Destruction',
                            'Charge of the Light Brigade',
                            'Cold Wave',
                            'Destiny Draw',
                            'Foolish Burial',
                            'Giant Trunade',
                            'Heavy Storm',
                            'Mind Control',
                            'Monster Gate',
                            'One for One',
                            'Overload Fusion',
                            'Reasoning',
                            'Reinforcement of the Army',
                            'Swords of Revealing Light',
                            'Future Fusion',
                            'Level Limit - Area B',
                            'Burial from a Different Dimension',
                            'Emergency Teleport',
                            'Limiter Removal',
                            'Mystical Space Typhoon',
                            'Scapegoat',
                            'Megamorph',
                            'Advanced Ritual Art',
                            'Ceasefire',
                            'Magic Cylinder',
                            'Magical Explosion',
                            'Mind Crush',
                            'Mirror Force',
                            'Ojama Trio',
                            'Return from the Different Dimension',
                            'The Transmigration Prophecy',
                            'Torrential Tribute',
                            'Trap Dustshoot',
                            'Call of the Haunted',
                            'Gravity Bind',
                            'Solemn Judgment',
                            'Wall of Revealing Light'
                        ], "Semi-Limited": [
                            'Cyber Dragon',
                            'Dandylion',
                            'Destiny Hero - Malicious',
                            'Goblin Zombie',
                            'Honest',
                            'Judgment Dragon',
                            'Lonefire Blossom',
                            'Treeborn Frog',
                            'Demise, King of Armageddon',
                            'Dewloren, Tiger King of the Ice Barrier',
                            'Gold Sarcophagus',
                            'Magical Stone Excavation',
                            'Black Whirlwind',
                            'Chain Strike',
                            'United We Stand',
                            'Bottomless Trap Hole',
                            'Royal Decree',
                            'Royal Oppression',
                            'Skill Drain',
                            'Ultimate Offering'
                        ]},
    "limit200709.bin": {"name_id": 0x15,       # List - March, 2011
                        "Forbidden": [
                            'Black Luster Soldier - Envoy of the Beginning',
                            'Chaos Emperor Dragon - Envoy of the End',
                            'Cyber Jar',
                            'Cyber-Stein',
                            'Dark Magician of Chaos',
                            'Destiny Hero - Disk Commander',
                            'Fiber Jar',
                            'Magical Scientist',
                            'Magician of Faith',
                            'Makyura the Destructor',
                            'Rescue Cat',
                            'Sinister Serpent',
                            'Substitoad',
                            'Tribe-Infecting Virus',
                            'Tsukuyomi',
                            'Victory Dragon',
                            'Witch of the Black Forest',
                            'Yata-Garasu',
                            'Thousand-Eyes Restrict',
                            'Dark Strike Fighter',
                            'Goyo Guardian',
                            'Brain Control',
                            'Change of Heart',
                            'Cold Wave',
                            'Confiscation',
                            'Delinquent Duo',
                            'Dimension Fusion',
                            'Graceful Charity',
                            'Harpie\'s Feather Duster',
                            'Heavy Storm',
                            'Metamorphosis',
                            'Painful Choice',
                            'Pot of Greed',
                            'Raigeki',
                            'The Forceful Sentry',
                            'Card of Safe Return',
                            'Mass Driver',
                            'Mirage of Nightmare',
                            'Temple of the Kings',
                            'Butterfly Dagger - Elma',
                            'Premature Burial',
                            'Snatch Steal',
                            'Crush Card Virus',
                            'Exchange of the Spirit',
                            'Last Turn',
                            'Ring of Destruction',
                            'Time Seal',
                            'Imperial Order'
                        ], "Limited": [
                            'Blackwing - Gale the Whirlwind',
                            'Blackwing - Kalut the Moon Shadow',
                            'Dandylion',
                            'Dark Armed Dragon',
                            'Elemental Hero Stratos',
                            'Exodia the Forbidden One',
                            'Gladiator Beast Bestiari',
                            'Gorz the Emissary of Darkness',
                            'Honest',
                            'Lumina, Lightsworn Summoner',
                            'Marshmallon',
                            'Mezuki',
                            'Mind Master',
                            'Morphing Jar',
                            'Necro Gardna',
                            'Necroface',
                            'Neo-Spacian Grand Mole',
                            'Night Assailant',
                            'Plaguespreader Zombie',
                            'Sangan',
                            'Summoner Monk',
                            'Tragoedia',
                            'Left Arm of the Forbidden One',
                            'Left Leg of the Forbidden One',
                            'Right Arm of the Forbidden One',
                            'Right Leg of the Forbidden One',
                            'Brionac, Dragon of the Ice Barrier',
                            'Trishula, Dragon of the Ice barrier',
                            'Advanced Ritual Art',
                            'Allure of Darkness',
                            'Black Whirlwind',
                            'Book of Moon',
                            'Burial from a Different Dimension',
                            'Card Destruction',
                            'Charge of the Light Brigade',
                            'Dark Hole',
                            'Destiny Draw',
                            'Emergency Teleport',
                            'Foolish Burial',
                            'Future Fusion',
                            'Gateway of the Six',
                            'Giant Trunade',
                            'Infernity Launcher',
                            'Level Limit - Area B',
                            'Limiter Removal',
                            'Mind Control',
                            'Monster Gate',
                            'Monster Reborn',
                            'One for One',
                            'Reasoning',
                            'Reinforcement of the Army',
                            'Scapegoat',
                            'Swords of Revealing Light',
                            'Call of the Haunted',
                            'Ceasefire',
                            'Gravity Bind',
                            'Magical Explosion',
                            'Mind Crush',
                            'Mirror Force',
                            'Return from the Different Dimension',
                            'Royal Oppression',
                            'Solemn Judgment',
                            'The Transmigration Prophecy',
                            'Torrential Tribute',
                            'Trap Dustshoot',
                            'Wall of Revealing Light',
                        ], "Semi-Limited": [
                            'Archlord Kristya',
                            'Card Trooper',
                            'Debris Dragon',
                            'Destiny Hero - Malicious',
                            'Judgment Dragon',
                            'Lonefire Blossom',
                            'Spirit Reaper',
                            'Chain Strike',
                            'Magical Stone Excavation',
                            'Megamorph',
                            'Mystical Space Typhoon',
                            'Overload Fusion',
                            'Royal Tribute',
                            'Bottomless Trap Hole',
                            'Icarus Attack',
                            'Magic Cylinder',
                            'Ojama Trio',
                            'Solemn Warning',
                        ]},
    "limit200809.bin": {"name_id": 0x16,       # List - September, 2011
                        "Forbidden": [
                            'Chaos Emperor Dragon - Envoy of the End',
                            'Cyber Jar',
                            'Cyber-Stein',
                            'Dark Magician of Chaos',
                            'Dark Strike Fighter',
                            'Destiny Hero - Disk Commander',
                            'Fiber Jar',
                            'Fishborg Blaster',
                            'Goyo Guardian',
                            'Magical Scientist',
                            'Magician of Faith',
                            'Makyura the Destructor',
                            'Mind Master',
                            'Rescue Cat',
                            'Sinister Serpent',
                            'Substitoad',
                            'Thousand-Eyes Restrict',
                            'Tribe-Infecting Virus',
                            'Tsukuyomi',
                            'Victory Dragon',
                            'Witch of the Black Forest',
                            'Yata-Garasu',
                            'Brain Control',
                            'Butterfly Dagger - Elma',
                            'Card of Safe Return',
                            'Change of Heart',
                            'Cold Wave',
                            'Confiscation',
                            'Delinquent Duo',
                            'Dimension Fusion',
                            'Giant Trunade',
                            'Graceful Charity',
                            'Harpie\'s Feather Duster',
                            'Mass Driver',
                            'Metamorphosis',
                            'Mirage of Nightmare',
                            'Painful Choice',
                            'Pot of Greed',
                            'Premature Burial',
                            'Raigeki',
                            'Snatch Steal',
                            'Temple of the Kings',
                            'The Forceful Sentry',
                            'Crush Card Virus',
                            'Exchange of the Spirit',
                            'Imperial Order',
                            'Last Turn',
                            'Ring of Destruction',
                            'Royal Oppression',
                            'Sixth Sense',
                            'Time Seal',
                        ], "Limited": [
                            'Black Luster Soldier - Envoy of the Beginning',
                            'Blackwing - Gale the Whirlwind',
                            'Blackwing - Kalut the Moon Shadow',
                            'Brionac, Dragon of the Ice Barrier',
                            'Dark Armed Dragon',
                            'Dandylion',
                            'Debris Dragon',
                            'Elemental Hero Stratos',
                            'Formula Synchron',
                            'Exodia the Forbidden One',
                            'Gladiator Beast Bestiari',
                            'Gorz the Emissary of Darkness',
                            'Honest',
                            'Left Arm of the Forbidden One',
                            'Left Leg of the Forbidden One',
                            'Legendary Six Samurai - Shi En',
                            'Lonefire Blossom',
                            'Lumina, Lightsworn Summoner',
                            'Marshmallon',
                            'Mezuki',
                            'Morphing Jar',
                            'Necroface',
                            'Neo-Spacian Grand Mole',
                            'Night Assailant',
                            'Plaguespreader Zombie',
                            'Right Arm of the Forbidden One',
                            'Right Leg of the Forbidden One',
                            'Sangan',
                            'T.G. Hyper Librarian',
                            'Trishula, Dragon of the Ice barrier',
                            'Advanced Ritual Art',
                            'Allure of Darkness',
                            'Black Whirlwind',
                            'Book of Moon',
                            'Burial from a Different Dimension',
                            'Card Destruction',
                            'Charge of the Light Brigade',
                            'Dark Hole',
                            'Emergency Teleport',
                            'Foolish Burial',
                            'Future Fusion',
                            'Gateway of the Six',
                            'Heavy Storm',
                            'Infernity Launcher',
                            'Level Limit - Area B',
                            'Limiter Removal',
                            'Mind Control',
                            'Monster Gate',
                            'Monster Reborn',
                            'One for One',
                            'Pot of Avarice',
                            'Primal Seed',
                            'Reasoning',
                            'Reinforcement of the Army',
                            'Scapegoat',
                            'Shien\'s Smoke Signal',
                            'Ceasefire',
                            'Magical Explosion',
                            'Mirror Force',
                            'Return from the Different Dimension',
                            'Solemn Judgment',
                            'The Transmigration Prophecy',
                            'Torrential Tribute',
                            'Trap Dustshoot',
                            'Wall of Revealing Light',
                        ], "Semi-Limited": [
                            'Archlord Kristya',
                            'Card Trooper',
                            'Destiny Hero - Malicious',
                            'Dewloren, Tiger King of the Ice Barrier',
                            'Necro Gardna',
                            'Summoner Monk',
                            'Tragoedia',
                            'Chain Strike',
                            'Destiny Draw',
                            'Magical Stone Excavation',
                            'Royal Tribute',
                            'Swords of Revealing Light',
                            'Bottomless Trap Hole',
                            'Call of the Haunted',
                            'Magic Cylinder',
                            'Mind Crush',
                            'Ojama Trio',
                            'Solemn Warning',
                        ]},
    "limit200909.bin": {"name_id": 0x17,       # List - March, 2012
                        "Forbidden": [
                            'Chaos Emperor Dragon - Envoy of the End',
                            'Cyber Jar',
                            'Cyber-Stein',
                            'Dark Magician of Chaos',
                            'Dark Strike Fighter',
                            'Destiny Hero - Disk Commander',
                            'Fiber Jar',
                            'Fishborg Blaster',
                            'Glow-Up Bulb',
                            'Goyo Guardian',
                            'Magical Scientist',
                            'Magician of Faith',
                            'Makyura the Destructor',
                            'Mind Master',
                            'Rescue Cat',
                            'Sinister Serpent',
                            'Spore',
                            'Substitoad',
                            'Thousand-Eyes Restrict',
                            'Tribe-Infecting Virus',
                            'Trishula, Dragon of the Ice barrier',
                            'Tsukuyomi',
                            'Victory Dragon',
                            'Witch of the Black Forest',
                            'Yata-Garasu',
                            'Brain Control',
                            'Butterfly Dagger - Elma',
                            'Card of Safe Return',
                            'Change of Heart',
                            'Cold Wave',
                            'Confiscation',
                            'Delinquent Duo',
                            'Dimension Fusion',
                            'Giant Trunade',
                            'Graceful Charity',
                            'Harpie\'s Feather Duster',
                            'Mass Driver',
                            'Metamorphosis',
                            'Mirage of Nightmare',
                            'Painful Choice',
                            'Pot of Greed',
                            'Premature Burial',
                            'Raigeki',
                            'Snatch Steal',
                            'Temple of the Kings',
                            'The Forceful Sentry',
                            'Crush Card Virus',
                            'Exchange of the Spirit',
                            'Imperial Order',
                            'Last Turn',
                            'Ring of Destruction',
                            'Royal Oppression',
                            'Sixth Sense',
                            'Time Seal',
                            'Trap Dustshoot',
                        ], "Limited": [
                            'Black Luster Soldier - Envoy of the Beginning',
                            'Blackwing - Gale the Whirlwind',
                            'Blackwing - Kalut the Moon Shadow',
                            'Brionac, Dragon of the Ice Barrier',
                            'Dark Armed Dragon',
                            'Debris Dragon',
                            'Dandylion',
                            'Elemental Hero Stratos',
                            'Formula Synchron',
                            'Exodia the Forbidden One',
                            'Gladiator Beast Bestiari',
                            'Gorz the Emissary of Darkness',
                            'Honest',
                            'Left Arm of the Forbidden One',
                            'Left Leg of the Forbidden One',
                            'Legendary Six Samurai - Shi En',
                            'Lonefire Blossom',
                            'Mezuki',
                            'Morphing Jar',
                            'Necroface',
                            'Neo-Spacian Grand Mole',
                            'Night Assailant',
                            'Plaguespreader Zombie',
                            'Right Arm of the Forbidden One',
                            'Right Leg of the Forbidden One',
                            'Sangan',
                            'T.G. Hyper Librarian',
                            'T.G. Striker',
                            'The Agent of Mystery - Earth',
                            'Advanced Ritual Art',
                            'Allure of Darkness',
                            'Black Whirlwind',
                            'Book of Moon',
                            'Burial from a Different Dimension',
                            'Card Destruction',
                            'Charge of the Light Brigade',
                            'Dark Hole',
                            'Foolish Burial',
                            'Future Fusion',
                            'Gateway of the Six',
                            'Heavy Storm',
                            'Infernity Launcher',
                            'Limiter Removal',
                            'Mind Control',
                            'Monster Gate',
                            'Monster Reborn',
                            'One for One',
                            'Pot of Avarice',
                            'Primal Seed',
                            'Reasoning',
                            'Reinforcement of the Army',
                            'Scapegoat',
                            'Ceasefire',
                            'Magical Explosion',
                            'Mirror Force',
                            'Return from the Different Dimension',
                            'Solemn Judgment',
                            'The Transmigration Prophecy',
                            'Wall of Revealing Light',
                        ], "Semi-Limited": [
                            'Archlord Kristya',
                            'Card Trooper',
                            'Destiny Hero - Malicious',
                            'Dewloren, Tiger King of the Ice Barrier',
                            'Lumina, Lightsworn Summoner',
                            'Marshmallon',
                            'Necro Gardna',
                            'Reborn Tengu',
                            'Summoner Monk',
                            'Tragoedia',
                            'Chain Strike',
                            'Destiny Draw',
                            'Emergency Teleport',
                            'Level Limit - Area B',
                            'Magical Stone Excavation',
                            'Royal Tribute',
                            'Shien\'s Smoke Signal',
                            'Swords of Revealing Light',
                            'Bottomless Trap Hole',
                            'Magic Cylinder',
                            'Mind Crush',
                            'Ojama Trio',
                            'Solemn Warning',
                            'Torrential Tribute',
                            'Ultimate Offering',
                        ]},
}
MAX_ENTRIES = 0xF8
BIN_PAC = "Data_arc_pac/bin.pac"
STATUS = {"Forbidden": 0x0000, "Limited": 0x4000, "Semi-Limited": 0x8000}

OV8 = 8
OV8_EDITS = {  # ram addr: (stock, patched) ARM words
    0x02168678: (0xE3500000, 0xE1900126),   # cmp r0,#0 -> orrs r0,r0,r6,lsr #2
    0x021686BC: (0xE3560003, 0xE3560008),   # cmp r6,#3 -> cmp r6,#8
}

# ---------------------------------------------------------------------------
# Thumb-1 encoders (only what this block needs; checked against capstone below)
# ---------------------------------------------------------------------------
COND = {"eq": 0, "ne": 1, "hi": 8, "ls": 9}


def _ldr_pc(at, rd, lit):
    off = lit - ((at + 4) & ~3)
    assert 0 <= off < 1024 and off % 4 == 0
    return 0x4800 | rd << 8 | off >> 2


def _bcond(at, cond, dst):
    off = (dst - (at + 4)) >> 1
    assert -128 <= off < 128
    return 0xD000 | COND[cond] << 8 | (off & 0xFF)


def _blx_arm(at, dst):
    assert dst % 4 == 0
    off = dst - ((at + 4) & ~3)                    # BLX target = (pc+off) & ~3; low bit must be 0
    return [0xF000 | ((off >> 12) & 0x7FF), 0xE800 | ((off >> 1) & 0x7FF)]


def _block():
    """Return (bytes, expected capstone listing) for the new kind-0 block."""
    prog = [  # (label or None, op, expected text)
        (None, lambda a: _ldr_pc(a, 0, LIT_CACHE), "ldr r0, [pc, #{}]"),
        (None, lambda a: 0x8801, "ldrh r1, [r0]"),
        (None, lambda a: 0x428D, "cmp r5, r1"),
        (None, lambda a: _bcond(a, "ne", L["path"]), "bne #{path}"),
        (None, lambda a: 0x8840, "ldrh r0, [r0, #2]"),
        (None, lambda a: 0x4284, "cmp r4, r0"),
        (None, lambda a: _bcond(a, "eq", EXIT), "beq #0x202ad46"),
        ("path", lambda a: _ldr_pc(a, 0, LIT_PATH), "ldr r0, [pc, #{}]"),
        (None, lambda a: 0x2131, "movs r1, #0x31"),
        (None, lambda a: 0x2230, "movs r2, #0x30"),
        (None, lambda a: 0x2C03, "cmp r4, #3"),
        (None, lambda a: _bcond(a, "ls", L["digits"]), "bls #{digits}"),
        (None, lambda a: 0x2130, "movs r1, #0x30"),
        (None, lambda a: 0x1CA2, "adds r2, r4, #2"),
        (None, lambda a: 0x3230, "adds r2, #0x30"),
        ("digits", lambda a: 0x72C1, "strb r1, [r0, #0xb]"),
        (None, lambda a: 0x7302, "strb r2, [r0, #0xc]"),
        (None, lambda a: 0x2104, "movs r1, #4"),
        (None, lambda a: 0x2200, "movs r2, #0"),
        (None, lambda a: list(struct.unpack("<HH", common.bl(a, FILE_LOAD))), "bl #0x20168e8"),
        (None, lambda a: 0x220A, "movs r2, #0xa"),
        (None, lambda a: _ldr_pc(a, 7, LIT_BUF), "ldr r7, [pc, #{}]"),
        (None, lambda a: 0x1C06, "adds r6, r0, #0"),
        (None, lambda a: 0x1C38, "adds r0, r7, #0"),
        (None, lambda a: 0x2100, "movs r1, #0"),
        (None, lambda a: 0x0192, "lsls r2, r2, #6"),
        (None, lambda a: _blx_arm(a, MEMSET), "blx #0x20895fc"),
        (None, lambda a: 0x8833, "ldrh r3, [r6]"),
        (None, lambda a: 0x22F8, "movs r2, #0xf8"),
        (None, lambda a: 0x1C30, "adds r0, r6, #0"),
        (None, lambda a: 0x1AD2, "subs r2, r2, r3"),
        (None, lambda a: 0x0053, "lsls r3, r2, #1"),
        (None, lambda a: 0x220A, "movs r2, #0xa"),
        (None, lambda a: 0x0192, "lsls r2, r2, #6"),
        (None, lambda a: 0x1C39, "adds r1, r7, #0"),
        (None, lambda a: 0x1AD2, "subs r2, r2, r3"),
        (None, lambda a: _blx_arm(a, MEMCPY), "blx #0x2089774"),
        (None, lambda a: _ldr_pc(a, 0, LIT_CACHE), "ldr r0, [pc, #{}]"),
        (None, lambda a: 0x8005, "strh r5, [r0]"),
        (None, lambda a: 0x8044, "strh r4, [r0, #2]"),
        (None, lambda a: 0x1E61, "subs r1, r4, #1"),
        (None, lambda a: 0x2901, "cmp r1, #1"),
        (None, lambda a: _bcond(a, "hi", L["tag"]), "bhi #{tag}"),
        (None, lambda a: 0x3153, "adds r1, #0x53"),
        (None, lambda a: 0x8079, "strh r1, [r7, #2]"),
        (None, lambda a: 0x80FC, "strh r4, [r7, #6]"),
        ("tag", lambda a: 0x0121, "lsls r1, r4, #4"),
        (None, lambda a: 0x31FF, "adds r1, #0xff"),
        (None, lambda a: 0x3101, "adds r1, #1"),
        # buffer+4 (r7), as stock -- NOT r0 (the cache): 0x02122118 is a separate struct (13 refs)
        (None, lambda a: 0x80B9, "strh r1, [r7, #4]"),
        (None, lambda a: 0x1C30, "adds r0, r6, #0"),
        (None, lambda a: list(struct.unpack("<HH", common.bl(a, FILE_FREE))), "bl #0x20164dc"),
    ]
    sizes = {"bl #0x20168e8": 4, "bl #0x20164dc": 4, "blx #0x20895fc": 4, "blx #0x2089774": 4}
    global L
    L, at = {}, BLOCK
    addrs = []
    for lab, _, txt in prog:
        if lab:
            L[lab] = at
        addrs.append(at)
        at += sizes.get(txt, 2)
    assert at <= EXIT, f"block overflows by {at - EXIT} bytes"
    hw = []
    for (_, op, _), a in zip(prog, addrs):
        v = op(a)
        hw += v if isinstance(v, list) else [v]
    hw += [0x46C0] * ((EXIT - at) // 2)            # nop (mov r8,r8) up to the stock exit
    code = struct.pack(f"<{len(hw)}H", *hw)
    want = []
    for (_, _, txt), a in zip(prog, addrs):
        if "[pc, #{}]" in txt:
            txt = txt.replace("{}", "")             # offset checked via the literal target below
        want.append(txt.format(**{k: hex(v) for k, v in L.items()}))
    return code, want


def _check_block(code):
    _, want = _block()
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    ins = list(md.disasm(code, BLOCK))
    got = [(i.address, f"{i.mnemonic} {i.op_str}") for i in ins]
    assert ins and ins[-1].address + ins[-1].size == EXIT, "disassembly did not reach the exit"
    lits = []
    for (a, g), w in zip(got, want):
        if w.endswith("[pc, #]"):
            assert g.startswith(w[:-2]), (hex(a), g, w)
            lits.append(((a + 4) & ~3) + int(g.split("#")[1].rstrip("]"), 16))
        else:
            assert g == w, f"{a:#x}: got {g!r}, want {w!r}"
    assert lits == [LIT_CACHE, LIT_PATH, LIT_BUF, LIT_CACHE], [hex(x) for x in lits]
    assert all(g == "mov r8, r8" for _, g in got[len(want):])


# ---------------------------------------------------------------------------
# ROM plumbing
# ---------------------------------------------------------------------------
def _main_section(rom):
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    return mc, next(s for s in mc.sections if s.ramAddress == rom.arm9RamAddress)


def _save_overlay(rom, ov_id, ov, data):
    ov.data = bytes(data)
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed
    tbl = rom.arm9OverlayTable
    e = ov_id * 32
    flags = struct.unpack_from("<I", tbl, e + 0x1C)[0]
    struct.pack_into("<I", tbl, e + 0x1C, ((flags >> 24) << 24) | (len(compressed) & 0xFFFFFF))


def _limit_file(spec) -> bytes:
    from otn_enhanced.rom.ydc_codec import card_name_to_konami_id
    entries, seen = [], set()
    for status, flag in STATUS.items():
        for name in spec[status]:
            cid = card_name_to_konami_id(name)
            assert cid is not None, f"{name!r} is not a card name"  # typo'd card name
            assert cid not in seen, f"{name!r} is in more than one category"
            seen.add(cid)
            entries.append(flag | cid)
    assert len(entries) <= MAX_ENTRIES, f"{len(entries)} entries > {MAX_ENTRIES}"
    return struct.pack(f"<4H{len(entries)}H", len(entries), spec["name_id"], 0, 0, *entries)


def _write_lists(rom) -> None:
    from otn_enhanced.rom.pac import build_modified_pac, parse_pac
    blob = bytes(rom.getFileByName(BIN_PAC))
    by = {f.get_clean_name(): i for i, f in enumerate(parse_pac(blob, BIN_PAC).files)}
    rom.setFileByName(BIN_PAC, build_modified_pac(
        blob, BIN_PAC, {by[fn]: _limit_file(spec) for fn, spec in LISTS.items()}))


def _read_list(rom, fn) -> bytes:
    from otn_enhanced.rom.pac import parse_pac
    blob = bytes(rom.getFileByName(BIN_PAC))
    f = next(f for f in parse_pac(blob, BIN_PAC).files if f.get_clean_name() == fn)
    return blob[f.address:f.address + f.size]


def apply(rom) -> None:
    _write_lists(rom)
    code, _ = _block()
    _check_block(code)
    mc, sec = _main_section(rom)
    d = bytearray(sec.data)
    o, n = BLOCK - ARM9, EXIT - BLOCK
    cur = bytes(d[o:o + n])
    if cur != code:
        assert cur == STOCK_BLOCK, "load_list kind-0 block is not stock -- wrong base ROM?"
        d[o:o + n] = code
        sec.data = bytes(d)
        rom.arm9 = mc.save()

    ov = rom.loadArm9Overlays([OV8])[OV8]
    od = bytearray(ov.data)
    for addr, (old, new) in OV8_EDITS.items():
        k = addr - ov.ramAddress
        cur = struct.unpack_from("<I", od, k)[0]
        if cur != new:
            assert cur == old, f"ov8 @0x{addr:08X} = {cur:08X}, expected {old:08X}"
            struct.pack_into("<I", od, k, new)
    if bytes(od) != ov.data:
        _save_overlay(rom, OV8, ov, od)


def main(write_text=None, src=SRC, out=OUT) -> None:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(src))
    apply(rom)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rom.saveToFile(str(out))
    print(f"  wrote -> {out}")


def verify(out=OUT) -> None:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(out))
    _, sec = _main_section(rom)
    code, _ = _block()
    assert sec.data[BLOCK - ARM9:EXIT - ARM9] == code, "load_list block not patched"
    _check_block(bytes(sec.data[BLOCK - ARM9:EXIT - ARM9]))
    ov = rom.loadArm9Overlays([OV8])[OV8]
    for addr, (_, new) in OV8_EDITS.items():
        assert struct.unpack_from("<I", ov.data, addr - ov.ramAddress)[0] == new, f"ov8 @0x{addr:08X}"
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    txt = [f"{i.mnemonic} {i.op_str}" for addr in OV8_EDITS
           for i in md.disasm(ov.data[addr - ov.ramAddress:][:4], addr)]
    assert txt == ["orrs r0, r0, r6, lsr #2", "cmp r6, #8"], txt
    for fn, spec in LISTS.items():
        assert _read_list(rom, fn) == _limit_file(spec), f"{fn} does not hold its LISTS entry"
    print("  [OK] extra banlists patched")


if __name__ == "__main__":
    main()
    verify()
