"""card_prop.bin entry layout (ERA2: SA / RoA / OTN) and the randomiser's value pools.

Each entry is a **64-bit little-endian bitfield**, not byte fields: ATK straddles
bytes 1-2, DEF bytes 2-3, attribute bytes 4-5.  Every write goes through
:func:`encode_entry`, which starts from the original u64 so bit 41 (monster vs
spell/trap), the spell/trap subtype and the reserved bits survive untouched.
Mirrors ``rom.game_constants.ERA2_LAYOUT``; ``randomise.run.selftest`` cross-checks.
"""
from __future__ import annotations

#: (lsb, width) for every known field of the 64-bit entry.
F_CID = (0, 14)
F_ATK = (14, 9)
F_DEF = (23, 9)
F_TYPE = (32, 6)
F_ATTR = (38, 3)
F_LEVEL = (42, 4)
F_STSUB = (46, 3)
F_RACE = (49, 5)

#: ATK/DEF sentinel meaning "?" (Sinister Serpent-style variable stats).  The
#: field is 9 bits, so 511 is the top value and is reserved for this.
UNKNOWN_STAT = 511

#: ATK/DEF are stored divided by ten.
STAT_DIVISOR = 10

ATTRIBUTES = {
    0: "NONE", 1: "LIGHT", 2: "DARK", 3: "WATER",
    4: "FIRE", 5: "EARTH", 6: "WIND", 7: "DIVINE",
}

RACES = {
    0: "NONE", 1: "Dragon", 2: "Zombie", 3: "Fiend", 4: "Pyro",
    5: "Sea Serpent", 6: "Rock", 7: "Machine", 8: "Fish", 9: "Dinosaur",
    10: "Insect", 11: "Beast", 12: "Beast-Warrior", 13: "Plant", 14: "Aqua",
    15: "Warrior", 16: "Winged Beast", 17: "Fairy", 18: "Spellcaster",
    19: "Thunder", 20: "Reptile", 21: "Psychic", 22: "Divine-Beast",
}

CARD_TYPES = {
    1: "Normal Monster", 3: "Effect Monster", 5: "Fusion Monster",
    7: "Fusion Effect Monster", 9: "Ritual Monster", 11: "Ritual Effect Monster",
    13: "Toon Monster", 15: "Spirit Monster", 17: "Union Monster",
    19: "Gemini Monster", 21: "Token", 23: "Divine Monster",
    27: "Spell Card", 29: "Trap Card", 31: "Normal Tuner Monster",
    33: "Tuner Monster", 35: "Synchro Monster", 37: "Synchro Effect Monster",
    39: "Synchro Tuner Effect Monster",
}

#: Not monsters -- never touched.
SPELL_TRAP_TYPES = frozenset({27, 29})
#: Tokens have no meaningful printed stats; excluded from randomisation.
TOKEN_TYPE = 21
#: Extra-Deck Synchros.  Their level is only randomised on explicit request,
#: because a Synchro's level is what its materials must sum to.
SYNCHRO_TYPES = frozenset({35, 37, 39})

#: The six attributes the randomiser draws from.  DIVINE (7) is deliberately
#: absent as both source and target, so the Egyptian Gods keep their attribute.
ATTRIBUTE_POOL = (1, 2, 3, 4, 5, 6)
#: Dragon..Psychic.  Divine-Beast (22) excluded both ways, same rationale.
RACE_POOL = tuple(range(1, 22))

MIN_LEVEL, MAX_LEVEL = 1, 12
#: A Synchro needs at least one Tuner plus one non-Tuner, so 2 is its floor.
MIN_SYNCHRO_LEVEL = 2

MAX_STAT = 5000
STAT_STEP = 50

#: Balanced mode: highest ATK/DEF permitted for each level band.
DEFAULT_CAPS: dict[tuple[int, int], int] = {
    (1, 4): 2000,
    (5, 6): 3000,
    (7, 8): 3500,
    (9, 10): 4000,
    (11, 12): 5000,
}


def get_field(val: int, fld: tuple[int, int]) -> int:
    start, width = fld
    return (val >> start) & ((1 << width) - 1)


def set_field(val: int, fld: tuple[int, int], new: int) -> int:
    start, width = fld
    mask = (1 << width) - 1
    return (val & ~(mask << start)) | ((new & mask) << start)


def decode_entry(raw: bytes) -> dict:
    """Decode an 8-byte card_prop entry.  ``raw_u64`` is kept for re-encoding."""
    val = int.from_bytes(raw, "little")
    atk_enc = get_field(val, F_ATK)
    def_enc = get_field(val, F_DEF)
    return {
        "raw_u64": val,
        "cid": get_field(val, F_CID),
        "atk_encoded": atk_enc,
        "def_encoded": def_enc,
        "atk": -1 if atk_enc == UNKNOWN_STAT else atk_enc * STAT_DIVISOR,
        "def": -1 if def_enc == UNKNOWN_STAT else def_enc * STAT_DIVISOR,
        "card_type": get_field(val, F_TYPE),
        "attribute": get_field(val, F_ATTR),
        "level": get_field(val, F_LEVEL),
        "spell_trap_subtype": get_field(val, F_STSUB),
        "race": get_field(val, F_RACE),
    }


def encode_entry(fields: dict) -> bytes:
    """Re-encode a decoded entry, preserving every bit we do not name.

    Starting from ``raw_u64`` is the whole point: bit 41 (monster vs spell/trap),
    the spell/trap subtype and the reserved bits [54:57] are carried through
    rather than zeroed.
    """
    val = fields["raw_u64"]
    val = set_field(val, F_ATK, fields["atk_encoded"])
    val = set_field(val, F_DEF, fields["def_encoded"])
    val = set_field(val, F_ATTR, fields["attribute"])
    val = set_field(val, F_LEVEL, fields["level"])
    val = set_field(val, F_RACE, fields["race"])
    return val.to_bytes(8, "little")


def cap_for_level(level: int, caps: dict[tuple[int, int], int]) -> int:
    """Highest ATK/DEF allowed at *level* under balanced mode."""
    for (lo, hi), limit in caps.items():
        if lo <= level <= hi:
            return limit
    return MAX_STAT

