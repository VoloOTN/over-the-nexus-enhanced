"""Codec for duel reward card pools (Over the Nexus).

Rewards are split across **two** locations in the ROM:

1. **Overlay 7** — record_ids 142–251 (16-byte records, BLZ-compressed)
2. **RPG_SCRIPT_J.pac** script files — duel_ids 1–141 (60-byte records,
   LZ10-compressed inside duel01.ws / duel02.ws / black01.ws)

Overlay 7 record format (16 bytes, all uint16 LE):

+--------+-----------+-------------------+
| Offset | Type      | Field             |
+========+===========+===================+
|  0–11  | uint16×6  | cards (Konami ID) |
| 12–13  | uint16    | value (always 100)|
| 14–15  | uint16    | record_id         |
+--------+-----------+-------------------+

Script file record format (60 bytes):

+--------+-----------+-------------------+
| Offset | Type      | Field             |
+========+===========+===================+
|  0–1   | uint16    | opcode            |
|  2–3   | uint16    | duel_id           |
|  4–15  | uint16×6  | cards (Konami ID) |
| 16–17  | uint16    | seq_num           |
| 18–19  | uint16    | field18           |
| 20–21  | uint16    | param             |
| 22–59  | bytes     | padding (zeros)   |
+--------+-----------+-------------------+

Card IDs are the same Konami database IDs used in ``.ydc`` deck files
(see :data:`otn_enhanced.rom.konami_id_to_card_name.KONAMI_ID_TO_CARD_NAME`).
"""

from __future__ import annotations

import struct
from typing import Any

# ─── Constants ─────────────────────────────────────────────────────────────────

OVERLAY_ID: int = 7
"""ARM9 overlay containing the reward table."""

TABLE_OFFSET: int = 0x12340
"""Byte offset of the first record within the decompressed overlay."""

RECORD_SIZE: int = 16
"""Bytes per record."""

NUM_CARDS: int = 6
"""Number of card slots per record."""

NUM_RECORDS: int = 111
"""Total number of records in the table (including header/sentinel)."""

TABLE_SIZE: int = RECORD_SIZE * NUM_RECORDS
"""Total byte length of the table."""

_CARDS_OFFSET: int = 0
_VALUE_OFFSET: int = 12
_RECORD_ID_OFFSET: int = 14

_CARD_ID_MIN: int = 1
_CARD_ID_MAX: int = 10000
_SENTINEL_ID: int = 0xFFFF


# ─── Public API ────────────────────────────────────────────────────────────────


def parse_duel_rewards(data: bytes) -> list[dict[str, Any]]:
    """Parse all duel reward records from decompressed overlay 7 bytes.

    Skips the header/sentinel records (record 0 with zeros, record 1 with
    0xFFFF values).

    Args:
        data: Full decompressed overlay 7 data.

    Returns:
        List of record dicts sorted by ``record_id``, each containing:

        * ``record_id`` (int) – duel/opponent identifier
        * ``cards`` (list[int]) – 6 Konami IDs
        * ``value`` (int) – constant field (typically 100)
        * ``offset`` (int) – byte offset within *data*
        * ``table_index`` (int) – 0-based index within the table
    """
    records: list[dict[str, Any]] = []

    for i in range(NUM_RECORDS):
        offset = TABLE_OFFSET + i * RECORD_SIZE
        if offset + RECORD_SIZE > len(data):
            break

        cards = [
            struct.unpack_from("<H", data, offset + j * 2)[0]
            for j in range(NUM_CARDS)
        ]
        value = struct.unpack_from("<H", data, offset + _VALUE_OFFSET)[0]
        record_id = struct.unpack_from("<H", data, offset + _RECORD_ID_OFFSET)[0]

        # Skip header/sentinel entries
        if record_id == _SENTINEL_ID:
            continue
        if all(c == 0 or c >= 0x8000 for c in cards) and record_id == _SENTINEL_ID:
            continue
        # Skip records where cards are all zero or clearly invalid
        if all(c == 0 for c in cards):
            continue
        # Skip records where no card is in valid Konami ID range
        if not any(_CARD_ID_MIN <= c <= _CARD_ID_MAX for c in cards):
            continue

        records.append({
            "record_id": record_id,
            "cards": cards,
            "value": value,
            "offset": offset,
            "table_index": i,
        })

    records.sort(key=lambda r: r["record_id"])
    return records


def patch_duel_reward(
    data: bytes,
    record_offset: int,
    new_cards: list[int],
) -> bytes:
    """Return a copy of *data* with the six card slots at *record_offset* replaced.

    Args:
        data: Decompressed overlay 7 bytes.
        record_offset: Byte offset of the record (from :func:`parse_duel_rewards`).
        new_cards: Exactly 6 Konami IDs to write.

    Returns:
        Modified overlay data with the card slots patched.

    Raises:
        ValueError: If arguments are invalid.
    """
    if len(new_cards) != NUM_CARDS:
        raise ValueError(f"Expected {NUM_CARDS} card IDs, got {len(new_cards)}")
    if record_offset < 0 or record_offset + RECORD_SIZE > len(data):
        raise ValueError(
            f"record_offset {record_offset:#x} out of range for data size {len(data)}"
        )
    if not all(isinstance(c, int) and 0 < c < 0xFFFF for c in new_cards):
        raise ValueError("All card IDs must be positive uint16 values")

    out = bytearray(data)
    for i, card_id in enumerate(new_cards):
        struct.pack_into("<H", out, record_offset + _CARDS_OFFSET + i * 2, card_id)
    return bytes(out)


# ─── Script-file record support (RPG_SCRIPT_J.pac, duel_ids 1–141) ────────────

SCRIPT_RECORD_SIZE: int = 60
"""Bytes per record in the script-file format."""

SCRIPT_DUEL01_IDX: int = 30
"""Index of duel01.lzws inside RPG_SCRIPT_J.pac."""

SCRIPT_DUEL02_IDX: int = 95
"""Index of duel02.lzws inside RPG_SCRIPT_J.pac."""

SCRIPT_BLACK01_IDX: int = 12
"""Index of black01.lzws inside RPG_SCRIPT_J.pac."""

_SCRIPT_OPCODE_OFFSET: int = 0
_SCRIPT_DUEL_ID_OFFSET: int = 2
_SCRIPT_CARDS_OFFSET: int = 4
_SCRIPT_SEQ_NUM_OFFSET: int = 16
_SCRIPT_FIELD18_OFFSET: int = 18
_SCRIPT_PARAM_OFFSET: int = 20

_KNOWN_OPCODES: frozenset[int] = frozenset({5, 6, 7, 8, 9, 10, 11, 15})


def _is_valid_script_record(data: bytes, offset: int) -> bool:
    """Return True if *data[offset]* looks like a valid script reward record."""
    if offset + SCRIPT_RECORD_SIZE > len(data):
        return False
    opcode = struct.unpack_from("<H", data, offset + _SCRIPT_OPCODE_OFFSET)[0]
    if opcode not in _KNOWN_OPCODES:
        return False
    duel_id = struct.unpack_from("<H", data, offset + _SCRIPT_DUEL_ID_OFFSET)[0]
    if not (1 <= duel_id <= 300):
        return False
    cards = [
        struct.unpack_from("<H", data, offset + _SCRIPT_CARDS_OFFSET + i * 2)[0]
        for i in range(NUM_CARDS)
    ]
    if not all(_CARD_ID_MIN <= c <= _CARD_ID_MAX for c in cards):
        return False
    field18 = struct.unpack_from("<H", data, offset + _SCRIPT_FIELD18_OFFSET)[0]
    if field18 > 10:
        return False
    seq_num = struct.unpack_from("<H", data, offset + _SCRIPT_SEQ_NUM_OFFSET)[0]
    if not (1 <= seq_num <= 1000):
        return False
    return True


def parse_script_rewards(data: bytes) -> list[dict[str, Any]]:
    """Parse reward records from a decompressed script file (duel01/duel02/black01).

    Uses the 60-byte record format found inside RPG_SCRIPT_J.pac script files.

    Each returned dict has keys:

    * ``duel_id`` (int) – NPC identifier (same as record_id in overlay table)
    * ``cards`` (list[int]) – 6 Konami IDs
    * ``opcode`` (int) – game-logic opcode
    * ``seq_num`` (int) – sequential record number
    * ``field18`` (int) – mode field
    * ``param`` (int) – variable field
    * ``offset`` (int) – byte offset within *data*
    """
    seen: set[int] = set()
    records: list[dict[str, Any]] = []

    i = 0
    while i <= len(data) - SCRIPT_RECORD_SIZE * 2:
        if not _is_valid_script_record(data, i):
            i += 2
            continue
        if not _is_valid_script_record(data, i + SCRIPT_RECORD_SIZE):
            i += 2
            continue
        # Found at least 2 consecutive valid records — walk the block
        offset = i
        while _is_valid_script_record(data, offset) and offset not in seen:
            seen.add(offset)
            opcode = struct.unpack_from("<H", data, offset)[0]
            duel_id = struct.unpack_from("<H", data, offset + 2)[0]
            cards = [
                struct.unpack_from("<H", data, offset + _SCRIPT_CARDS_OFFSET + j * 2)[0]
                for j in range(NUM_CARDS)
            ]
            seq_num = struct.unpack_from("<H", data, offset + _SCRIPT_SEQ_NUM_OFFSET)[0]
            field18 = struct.unpack_from("<H", data, offset + _SCRIPT_FIELD18_OFFSET)[0]
            param = struct.unpack_from("<H", data, offset + _SCRIPT_PARAM_OFFSET)[0]
            records.append({
                "duel_id": duel_id,
                "cards": cards,
                "opcode": opcode,
                "seq_num": seq_num,
                "field18": field18,
                "param": param,
                "offset": offset,
            })
            offset += SCRIPT_RECORD_SIZE
        i = offset + 2

    records.sort(key=lambda r: r["duel_id"])
    return records


def patch_script_reward(
    data: bytes,
    record_offset: int,
    new_cards: list[int],
) -> bytes:
    """Return a copy of *data* with the six card slots at *record_offset* replaced.

    Args:
        data: Decompressed script file bytes (duel01/duel02/black01).
        record_offset: Byte offset of the record.
        new_cards: Exactly 6 Konami IDs to write.

    Raises:
        ValueError: If arguments are invalid.
    """
    if len(new_cards) != NUM_CARDS:
        raise ValueError(f"Expected {NUM_CARDS} card IDs, got {len(new_cards)}")
    if record_offset < 0 or record_offset + SCRIPT_RECORD_SIZE > len(data):
        raise ValueError(
            f"record_offset {record_offset:#x} out of range for data size {len(data)}"
        )
    if not all(isinstance(c, int) and 0 < c < 0xFFFF for c in new_cards):
        raise ValueError("All card IDs must be positive uint16 values")

    out = bytearray(data)
    for i, card_id in enumerate(new_cards):
        struct.pack_into("<H", out, record_offset + _SCRIPT_CARDS_OFFSET + i * 2, card_id)
    return bytes(out)
