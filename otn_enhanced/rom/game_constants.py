"""Per-game encoding constants for Yu-Gi-Oh! World Championship DS ROMs.

Each card in ``card_prop.bin`` is stored as a **64-bit little-endian
bit-packed integer**.  The bit positions differ between the two encoding
eras.  This module defines the bitfield layouts and value maps for each
era and provides lookup by NDS game-code.

**Era 1 — WC2007 / WC2008** (game codes ``AY7P``, ``YG8P``):
  - 64-bit LE bitfield with 13-bit card ID, 9-bit ATK/10, 9-bit DEF/10
  - Monster race is 4 bits + 1 discriminator bit (11 base pairs → 22 types)
  - Attribute is 4 bits (upper) with 2-bit summon-type modifier (lower)
  - Validated at 100 % accuracy against YGOPRODeck API

**Era 2 — Stardust Accelerator / Reverse of Arcadia / Over the Nexus**
  (game codes ``CY8P``, ``BYXP``, ``BYYP``):
  - 64-bit LE bitfield with 14-bit card ID, 9-bit ATK/10, 9-bit DEF/10
  - Monster race is a direct 5-bit value (1–22)
  - Card type is a 6-bit value encoding monster subtype / spell / trap
  - Attribute is a direct 3-bit value
  - Validated at 100 % accuracy against YGOPRODeck API

Games without ``bin.pac`` / ``bin2.pac`` (Nightmare Troubadour, Spirit Caller)
cannot be decoded and are not listed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ────────────────────────────────────────────────────────────────────
# Bitfield layout descriptor
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BitField:
    """A single field within the 64-bit card_prop entry."""
    start: int   # LSB bit position (0-indexed)
    width: int   # number of bits

    @property
    def end(self) -> int:
        return self.start + self.width

    @property
    def mask(self) -> int:
        return (1 << self.width) - 1

    def extract(self, value: int) -> int:
        return (value >> self.start) & self.mask

    def inject(self, value: int, field_val: int) -> int:
        cleared = value & ~(self.mask << self.start)
        return cleared | ((field_val & self.mask) << self.start)


@dataclass(frozen=True)
class CardPropLayout:
    """Bitfield layout for a card_prop.bin entry (64-bit LE integer)."""

    card_id: BitField
    atk: BitField         # stored as ATK // 10
    defense: BitField     # stored as DEF // 10
    card_type: BitField   # monster subtype / spell / trap indicator
    attribute: BitField   # monster attribute
    level: BitField       # monster level / rank
    race: BitField        # monster race (type)

    # Optional sub-fields within the main fields
    spell_trap_subtype: BitField | None = None   # spell/trap sub-category
    race_discriminator: BitField | None = None   # ERA1: extra bit for race pairs
    summon_modifier: BitField | None = None      # ERA1: modifier within attribute field

    atk_divisor: int = 10
    def_divisor: int = 10
    unknown_atk_marker: int = 511   # ? ATK encoded as this value
    unknown_def_marker: int = 511   # ? DEF encoded as this value

    @property
    def known_bits_mask(self) -> int:
        """Return a 64-bit mask with 1s for every bit covered by a known field."""
        mask = 0
        for bf in (
            self.card_id, self.atk, self.defense, self.card_type,
            self.attribute, self.level, self.race,
            self.spell_trap_subtype, self.race_discriminator, self.summon_modifier,
        ):
            if bf is not None:
                mask |= bf.mask << bf.start
        return mask

    def extract_unknown_bits(self, value: int) -> dict[str, int]:
        """Extract unknown bits from a 64-bit card_prop value.

        Returns a dict mapping ``"bit_XX"`` labels to the 0/1 value of
        each individual bit that is not covered by any known field.
        """
        known = self.known_bits_mask
        bits: dict[str, int] = {}
        for bit in range(64):
            if not (known & (1 << bit)):
                bits[f"bit_{bit}"] = (value >> bit) & 1
        return bits


# ────────────────────────────────────────────────────────────────────
# Per-game constants container
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GameConstants:
    """Encoding constants for a specific game or encoding era."""

    era: str
    """Short label: ``'era1'`` (WC2007/WC2008) or ``'era2'`` (SA/RoA/OTN)."""

    game_codes: tuple[str, ...]
    """NDS game codes that use this encoding."""

    layout: CardPropLayout
    """Bitfield layout for card_prop entries."""

    attribute_map: dict[int, str]
    """Encoded attribute value → human-readable name."""

    attribute_reverse: dict[str, int]
    """Human-readable attribute name → encoded value."""

    race_map: dict[int, str] | dict[tuple[int, int], str]
    """Race value(s) → human-readable name.
    ERA1: ``(base, discriminator)`` → name.
    ERA2: direct ``int`` → name.
    """

    race_reverse: dict[str, int] | dict[str, tuple[int, int]]
    """Human-readable race → encoded value(s)."""

    card_type_map: dict[int, str]
    """Card type value → human-readable name."""

    spell_trap_subtype_map: dict[int, str]
    """Spell/trap subtype value → human-readable name."""

    def decode_entry(self, raw: bytes) -> dict[str, Any]:
        """Decode an 8-byte card_prop entry into a structured dict."""
        val = int.from_bytes(raw, "little")
        lay = self.layout

        card_id = lay.card_id.extract(val)
        atk_enc = lay.atk.extract(val)
        def_enc = lay.defense.extract(val)
        card_type_enc = lay.card_type.extract(val)
        attr_enc = lay.attribute.extract(val)
        level = lay.level.extract(val)

        # ATK / DEF
        if atk_enc == lay.unknown_atk_marker:
            real_atk = -1  # ? ATK
        else:
            real_atk = atk_enc * lay.atk_divisor

        if def_enc == lay.unknown_def_marker:
            real_def = -1  # ? DEF
        else:
            real_def = def_enc * lay.def_divisor

        # Attribute
        attribute = self.attribute_map.get(attr_enc, f"Unknown({attr_enc})")

        # Summon modifier (ERA1 only)
        summon_mod = None
        if lay.summon_modifier is not None:
            summon_mod = lay.summon_modifier.extract(val)

        # Card type
        card_type = self.card_type_map.get(card_type_enc, f"Unknown({card_type_enc})")

        # Monster race
        if self.era == "era1":
            race_base = lay.race.extract(val)
            disc = lay.race_discriminator.extract(val) if lay.race_discriminator else 0
            race = self.race_map.get((race_base, disc), f"Unknown({race_base},{disc})")
        else:
            race_enc = lay.race.extract(val)
            race = self.race_map.get(race_enc, f"Unknown({race_enc})")

        # Spell/trap subtype
        spell_trap_sub = None
        if lay.spell_trap_subtype is not None:
            st_enc = lay.spell_trap_subtype.extract(val)
            spell_trap_sub = self.spell_trap_subtype_map.get(st_enc, f"Unknown({st_enc})")

        unknown_bits = lay.extract_unknown_bits(val)

        return {
            "card_id": card_id,
            "atk_encoded": atk_enc,
            "def_encoded": def_enc,
            "real_atk": real_atk,
            "real_def": real_def,
            "card_type_encoded": card_type_enc,
            "card_type": card_type,
            "attribute_encoded": attr_enc,
            "attribute": attribute,
            "summon_modifier": summon_mod,
            "level": level,
            "race": race,
            "spell_trap_subtype": spell_trap_sub,
            "unknown_bits": unknown_bits,
            "raw_u64": val,
        }

    def encode_entry(self, fields: dict[str, Any]) -> bytes:
        """Encode a structured dict back into an 8-byte card_prop entry.

        Accepts the same dict format produced by :meth:`decode_entry`.
        For lossless round-trip, ``raw_u64`` is used as the base to
        preserve unknown/reserved bits.
        """
        lay = self.layout

        # Start from the original raw value if available (preserves unknown bits)
        val = fields.get("raw_u64", 0)

        # Inject each known field
        val = lay.card_id.inject(val, fields.get("card_id", 0))

        # ATK
        atk_enc = fields.get("atk_encoded")
        if atk_enc is None:
            real_atk = fields.get("real_atk", 0)
            if real_atk < 0:
                atk_enc = lay.unknown_atk_marker
            else:
                atk_enc = real_atk // lay.atk_divisor
        val = lay.atk.inject(val, atk_enc)

        # DEF
        def_enc = fields.get("def_encoded")
        if def_enc is None:
            real_def = fields.get("real_def", 0)
            if real_def < 0:
                def_enc = lay.unknown_def_marker
            else:
                def_enc = real_def // lay.def_divisor
        val = lay.defense.inject(val, def_enc)

        # Card type
        ct_enc = fields.get("card_type_encoded")
        if ct_enc is None:
            ct_enc = fields.get("card_type", 0)
        val = lay.card_type.inject(val, ct_enc)

        # Attribute
        val = lay.attribute.inject(val, fields.get("attribute_encoded", 0))

        # Summon modifier (ERA1)
        if lay.summon_modifier is not None and "summon_modifier" in fields and fields["summon_modifier"] is not None:
            val = lay.summon_modifier.inject(val, fields["summon_modifier"])

        # Level
        val = lay.level.inject(val, fields.get("level", 0))

        # Race
        if self.era == "era1":
            race_name = fields.get("race", "")
            if isinstance(race_name, str) and race_name in self.race_reverse:
                base, disc = self.race_reverse[race_name]
                val = lay.race.inject(val, base)
                if lay.race_discriminator is not None:
                    val = lay.race_discriminator.inject(val, disc)
        else:
            race_name = fields.get("race", "")
            if isinstance(race_name, str) and race_name in self.race_reverse:
                val = lay.race.inject(val, self.race_reverse[race_name])

        # Spell/trap subtype
        if lay.spell_trap_subtype is not None and "spell_trap_subtype" in fields:
            st_name = fields["spell_trap_subtype"]
            if st_name is not None:
                st_reverse = {v: k for k, v in self.spell_trap_subtype_map.items()}
                if st_name in st_reverse:
                    val = lay.spell_trap_subtype.inject(val, st_reverse[st_name])

        # Unknown bits — re-inject edited values into their original positions
        unk = fields.get("unknown_bits")
        if isinstance(unk, dict):
            for label, bit_val in unk.items():
                # label format: "bit_XX"
                parts = label.split("_")
                if len(parts) == 2 and parts[0] == "bit":
                    try:
                        bit_pos = int(parts[1])
                        if int(bit_val) & 1:
                            val |= (1 << bit_pos)
                        else:
                            val &= ~(1 << bit_pos)
                    except (ValueError, TypeError):
                        pass

        return val.to_bytes(8, "little")


# ────────────────────────────────────────────────────────────────────
# ERA 1 layout — WC2007 / WC2008
# ────────────────────────────────────────────────────────────────────

ERA1_LAYOUT = CardPropLayout(
    card_id=BitField(0, 13),
    atk=BitField(13, 9),
    defense=BitField(22, 9),
    card_type=BitField(31, 3),
    attribute=BitField(36, 4),       # upper 4 bits of the 6-bit attr region
    summon_modifier=BitField(34, 2), # lower 2 bits: 0=Normal/Effect/Fusion, 1=Ritual/Toon/Spirit, 2=Union/Gemini
    level=BitField(40, 4),
    spell_trap_subtype=BitField(44, 4),
    race_discriminator=BitField(47, 1),  # discriminates between the two types in each race pair
    race=BitField(48, 4),                # base race (0–10, 11 pairs)
    # [52:56] = unknown (4 bits, values 0–4)
    # [56:64] = always 0 (padding)
)

# ERA1 attribute values (bits [36:40], after stripping summon modifier)
ERA1_ATTRIBUTE_MAP: dict[int, str] = {
    0: "NONE",
    1: "LIGHT",
    2: "DARK",
    3: "WATER",
    4: "FIRE",
    5: "EARTH",
    6: "WIND",
    7: "DIVINE",
}

ERA1_ATTRIBUTE_REVERSE: dict[str, int] = {v: k for k, v in ERA1_ATTRIBUTE_MAP.items()}

# ERA1 summon-modifier values (bits [34:36])
ERA1_SUMMON_MODIFIER_MAP: dict[int, str] = {
    0: "Normal/Effect/Fusion",  # includes normal monsters, effect monsters, and fusion monsters
    1: "Ritual/Toon/Spirit",    # includes ritual, toon, and spirit monsters; also spells/traps
    2: "Union/Gemini",          # union and gemini monsters
    3: "Special",               # rare / special cases
}

# ERA1 card type values (bits [31:34])
ERA1_CARD_TYPE_MAP: dict[int, str] = {
    0: "Monster",
    1: "Monster",  # alternate monster encoding
    2: "Spell",
    3: "Trap",
}

# ERA1 monster race lookup: (base_race, discriminator_bit) → race name
ERA1_RACE_TABLE: dict[tuple[int, int], str] = {
    (0, 0): "NONE",       # no cards with base=0, disc=0
    (0, 1): "Dragon",
    (1, 0): "Zombie",
    (1, 1): "Fiend",
    (2, 0): "Pyro",
    (2, 1): "Sea Serpent",
    (3, 0): "Rock",
    (3, 1): "Machine",
    (4, 0): "Fish",
    (4, 1): "Dinosaur",
    (5, 0): "Insect",
    (5, 1): "Beast",
    (6, 0): "Beast-Warrior",
    (6, 1): "Plant",
    (7, 0): "Aqua",
    (7, 1): "Warrior",
    (8, 0): "Winged Beast",
    (8, 1): "Fairy",
    (9, 0): "Spellcaster",
    (9, 1): "Thunder",
    (10, 0): "Reptile",
    (10, 1): "Divine-Beast",
}

ERA1_RACE_REVERSE: dict[str, tuple[int, int]] = {v: k for k, v in ERA1_RACE_TABLE.items() if v != "NONE"}

# ERA1 spell/trap subtype (bits [44:48])
ERA1_SPELL_TRAP_SUBTYPE_MAP: dict[int, str] = {
    0: "Normal Spell",
    2: "Field Spell",
    3: "Equip Spell",
    4: "Continuous Spell",
    5: "Quick-Play Spell",
    6: "Ritual Spell",
    8: "Normal Trap",
    9: "Counter Trap",
    12: "Continuous Trap",
}


# ────────────────────────────────────────────────────────────────────
# ERA 2 layout — SA / RoA / OTN
# ────────────────────────────────────────────────────────────────────

ERA2_LAYOUT = CardPropLayout(
    card_id=BitField(0, 14),
    atk=BitField(14, 9),
    defense=BitField(23, 9),
    card_type=BitField(32, 6),     # encodes full monster subtype / spell / trap
    attribute=BitField(38, 3),     # direct attribute value (same numbering as ERA1)
    level=BitField(42, 4),
    spell_trap_subtype=BitField(46, 3),  # spell/trap sub-category
    race=BitField(49, 5),                # direct race value (1–22)
    # [41]    = monster/spell-trap flag (0=monster, 1=spell/trap)
    # [54:57] = unknown (3 bits, values 0–4)
    # [57:64] = always 0
    race_discriminator=None,  # not needed — race is directly encoded
    summon_modifier=None,     # not needed — card_type encodes this
)

# ERA2 attribute values (bits [38:41])
ERA2_ATTRIBUTE_MAP: dict[int, str] = {
    0: "NONE",
    1: "LIGHT",
    2: "DARK",
    3: "WATER",
    4: "FIRE",
    5: "EARTH",
    6: "WIND",
    7: "DIVINE",
}

ERA2_ATTRIBUTE_REVERSE: dict[str, int] = {v: k for k, v in ERA2_ATTRIBUTE_MAP.items()}

# ERA2 monster race (bits [49:54]) — direct 5-bit value
ERA2_RACE_MAP: dict[int, str] = {
    0: "NONE",
    1: "Dragon",
    2: "Zombie",
    3: "Fiend",
    4: "Pyro",
    5: "Sea Serpent",
    6: "Rock",
    7: "Machine",
    8: "Fish",
    9: "Dinosaur",
    10: "Insect",
    11: "Beast",
    12: "Beast-Warrior",
    13: "Plant",
    14: "Aqua",
    15: "Warrior",
    16: "Winged Beast",
    17: "Fairy",
    18: "Spellcaster",
    19: "Thunder",
    20: "Reptile",
    21: "Psychic",
    22: "Divine-Beast",
}

ERA2_RACE_REVERSE: dict[str, int] = {v: k for k, v in ERA2_RACE_MAP.items() if v != "NONE"}

# ERA2 card type (bits [32:38]) — 6-bit value
ERA2_CARD_TYPE_MAP: dict[int, str] = {
    1:  "Normal Monster",
    3:  "Effect Monster",         # includes Flip Effect Monster
    5:  "Fusion Monster",         # no effect
    7:  "Fusion Effect Monster",
    9:  "Ritual Monster",         # no effect
    11: "Ritual Effect Monster",
    13: "Toon Monster",
    15: "Spirit Monster",
    17: "Union Monster",
    19: "Gemini Monster",
    21: "Token",
    23: "Divine Monster",         # Egyptian Gods (Slifer, Ra)
    27: "Spell Card",
    29: "Trap Card",
    31: "Normal Tuner Monster",
    33: "Tuner Monster",          # effect tuner
    35: "Synchro Monster",        # no effect (e.g. Gaia Knight)
    37: "Synchro Effect Monster",
    39: "Synchro Tuner Effect Monster",
}

ERA2_CARD_TYPE_REVERSE: dict[str, int] = {v: k for k, v in ERA2_CARD_TYPE_MAP.items()}

# ERA2 spell/trap subtype (bits [46:49])
ERA2_SPELL_TRAP_SUBTYPE_MAP: dict[int, str] = {
    0: "Normal",          # Normal Spell or Normal Trap
    1: "Counter",         # Counter Trap
    2: "Field",           # Field Spell
    3: "Equip",           # Equip Spell
    4: "Continuous",      # Continuous Spell or Continuous Trap
    5: "Quick-Play",      # Quick-Play Spell
    6: "Ritual",          # Ritual Spell
}


# ────────────────────────────────────────────────────────────────────
# Constants instances
# ────────────────────────────────────────────────────────────────────

ERA1_CONSTANTS = GameConstants(
    era="era1",
    game_codes=("AY7P", "YG8P"),
    layout=ERA1_LAYOUT,
    attribute_map=ERA1_ATTRIBUTE_MAP,
    attribute_reverse=ERA1_ATTRIBUTE_REVERSE,
    race_map=ERA1_RACE_TABLE,
    race_reverse=ERA1_RACE_REVERSE,
    card_type_map=ERA1_CARD_TYPE_MAP,
    spell_trap_subtype_map=ERA1_SPELL_TRAP_SUBTYPE_MAP,
)

ERA2_CONSTANTS = GameConstants(
    era="era2",
    game_codes=("CY8P", "BYXP", "BYYP"),
    layout=ERA2_LAYOUT,
    attribute_map=ERA2_ATTRIBUTE_MAP,
    attribute_reverse=ERA2_ATTRIBUTE_REVERSE,
    race_map=ERA2_RACE_MAP,
    race_reverse=ERA2_RACE_REVERSE,
    card_type_map=ERA2_CARD_TYPE_MAP,
    spell_trap_subtype_map=ERA2_SPELL_TRAP_SUBTYPE_MAP,
)


# ────────────────────────────────────────────────────────────────────
# Registry and lookup
# ────────────────────────────────────────────────────────────────────

ALL_GAME_CONSTANTS: dict[str, GameConstants] = {}

for _gc in (ERA1_CONSTANTS, ERA2_CONSTANTS):
    for _code in _gc.game_codes:
        ALL_GAME_CONSTANTS[_code] = _gc

DEFAULT_CONSTANTS = ERA2_CONSTANTS


def get_game_constants(game_code: str | bytes | bytearray) -> GameConstants:
    """Look up game-specific constants by NDS game code.

    Falls back to :data:`DEFAULT_CONSTANTS` (era-2 / OTN) when the code
    is not recognised.
    """
    if isinstance(game_code, (bytes, bytearray)):
        game_code = game_code.decode("ascii", errors="replace").rstrip("\x00").strip()
    return ALL_GAME_CONSTANTS.get(game_code, DEFAULT_CONSTANTS)
