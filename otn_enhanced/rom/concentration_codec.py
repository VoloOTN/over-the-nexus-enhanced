# ponytail: KEEP -- unused by this work so far but wanted; ponytail-audit must skip this file (user decision 2026-10-29).
"""Codec for the concentration mini-game card pool (Over the Nexus).

The card pool data is stored across three LZ10-compressed script files inside
``RPG_SCRIPT_J.pac``:

* **duel01.ws** (idx 30) — duel_ids 1–97 plus 251 (story mode)
* **duel02.ws** (idx 95) — duel_ids 98–119 (post-game)
* **black01.ws** (idx 12) — duel_ids 120–141, 68–69 (challenge mode)

Each record is 60 bytes:

+--------+---------+----------+-------------------------------------------+
| Offset | Type    | Field    | Notes                                     |
+========+=========+==========+===========================================+
|  0     | uint16  | opcode   | 5,6,7,8,9,10,11,15                       |
|  2     | uint16  | duel_id  | Identifies the NPC duelist                |
|  4..15 | uint16×6| cards    | 6 Konami IDs (same as .ydc deck files)    |
| 16     | uint16  | seq_num  | Sequential record number                  |
| 18     | uint16  | field18  | 0 for duel01, 1 for duel02/black01        |
| 20     | uint16  | param    | Variable (difficulty/reward)              |
| 22..59 | bytes   | padding  | Zeros                                     |
+--------+---------+----------+-------------------------------------------+

Card IDs are the same ``uint16`` Konami IDs used in ``.ydc`` deck files
(see :data:`otn_enhanced.rom.konami_id_to_card_name.KONAMI_ID_TO_CARD_NAME`).
"""

from __future__ import annotations

import struct
from typing import Any

RECORD_SIZE: int = 60
NUM_CARDS: int = 6

_OPCODE_OFFSET: int = 0
_DUEL_ID_OFFSET: int = 2
_CARDS_OFFSET: int = 4
_SEQ_NUM_OFFSET: int = 16
_FIELD18_OFFSET: int = 18
_PARAM_OFFSET: int = 20
_PADDING_START: int = 22

_KNOWN_OPCODES: frozenset[int] = frozenset({5, 6, 7, 8, 9, 10, 11, 15})
_CARD_ID_MIN: int = 3000
_CARD_ID_MAX: int = 10000

# Script file indices inside RPG_SCRIPT_J.pac
SCRIPT_DUEL01_IDX: int = 30
SCRIPT_DUEL02_IDX: int = 95
SCRIPT_BLACK01_IDX: int = 12


def _is_valid_record(data: bytes, offset: int) -> bool:
    """Return True if *data[offset]* looks like a valid concentration pool record."""
    if offset + RECORD_SIZE > len(data):
        return False
    opcode = struct.unpack_from("<H", data, offset + _OPCODE_OFFSET)[0]
    if opcode not in _KNOWN_OPCODES:
        return False
    duel_id = struct.unpack_from("<H", data, offset + _DUEL_ID_OFFSET)[0]
    if not (1 <= duel_id <= 300):
        return False
    cards = [
        struct.unpack_from("<H", data, offset + _CARDS_OFFSET + i * 2)[0]
        for i in range(NUM_CARDS)
    ]
    if not all(_CARD_ID_MIN <= c <= _CARD_ID_MAX for c in cards):
        return False
    # field18 must be small (0 for duel01, 1 for duel02/black01)
    field18 = struct.unpack_from("<H", data, offset + _FIELD18_OFFSET)[0]
    if field18 > 10:
        return False
    # seq_num at +16 must be plausible
    seq_num = struct.unpack_from("<H", data, offset + _SEQ_NUM_OFFSET)[0]
    if not (1 <= seq_num <= 1000):
        return False
    return True


def parse_concentration_pool(data: bytes) -> list[dict[str, Any]]:
    """Parse all concentration pool records from decompressed script bytes.

    Scans for contiguous runs of 60-byte records that satisfy the record
    format constraints.  Finds multiple blocks (unlike the old single-table
    approach).  Returns all found records sorted by *duel_id*.

    Each returned dict has keys:

    * ``duel_id`` (int) – NPC identifier
    * ``opcode`` (int) – game-logic opcode
    * ``cards`` (list[int]) – 6 Konami IDs
    * ``seq_num`` (int) – sequential record number
    * ``field18`` (int) – mode field (0 or 1)
    * ``param`` (int) – variable field (difficulty / reward)
    * ``offset`` (int) – byte offset within *data*
    """
    seen: set[int] = set()
    records: list[dict[str, Any]] = []

    i = 0
    while i <= len(data) - RECORD_SIZE * 2:
        if not _is_valid_record(data, i):
            i += 2
            continue
        if not _is_valid_record(data, i + RECORD_SIZE):
            i += 2
            continue
        # Found at least 2 consecutive valid records — walk the block
        offset = i
        while _is_valid_record(data, offset) and offset not in seen:
            seen.add(offset)
            opcode = struct.unpack_from("<H", data, offset)[0]
            duel_id = struct.unpack_from("<H", data, offset + 2)[0]
            cards = [
                struct.unpack_from("<H", data, offset + _CARDS_OFFSET + j * 2)[0]
                for j in range(NUM_CARDS)
            ]
            seq_num = struct.unpack_from("<H", data, offset + _SEQ_NUM_OFFSET)[0]
            field18 = struct.unpack_from("<H", data, offset + _FIELD18_OFFSET)[0]
            param = struct.unpack_from("<H", data, offset + _PARAM_OFFSET)[0]
            records.append(
                {
                    "opcode": opcode,
                    "duel_id": duel_id,
                    "cards": cards,
                    "seq_num": seq_num,
                    "field18": field18,
                    "param": param,
                    "offset": offset,
                }
            )
            offset += RECORD_SIZE
        # Continue scanning for additional blocks
        i = offset + 2

    records.sort(key=lambda r: r["duel_id"])
    return records


def patch_concentration_pool(
    data: bytes,
    record_offset: int,
    new_cards: list[int],
) -> bytes:
    """Return a copy of *data* with the six card slots at *record_offset* replaced.

    Args:
        data: Decompressed ``duel01.lzws`` bytes.
        record_offset: Byte offset of the record (from :func:`parse_concentration_pool`).
        new_cards: Exactly 6 Konami IDs to write.

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
