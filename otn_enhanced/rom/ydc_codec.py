"""Decoder/encoder utilities for YDC deck files."""

from __future__ import annotations

import base64
import json
from typing import Any

from otn_enhanced.rom.konami_id_to_card_name import (
    KONAMI_ID_TO_CARD_NAME,
    card_name_to_konami_id,
)


def _u16(data: bytes, offset: int) -> int:
    """Read little-endian uint16."""
    if offset + 2 > len(data):
        raise ValueError(f"Unexpected end of file at offset {offset}")
    return int.from_bytes(data[offset:offset + 2], byteorder="little")


def decode_ydc(data: bytes) -> dict[str, Any]:
    """Decode YDC bytes into a structured dictionary.

    Format:
    - 8 bytes header (preserved)
    - 2 bytes main size
    - main_size * 2 bytes main deck card ids (uint16)
    - 2 bytes extra size
    - extra_size * 2 bytes extra deck card ids
    - 2 bytes side size
    - side_size * 2 bytes side deck card ids
    """
    if len(data) < 14:
        raise ValueError("YDC too small")

    header = data[:8]
    pos = 8

    main_size = _u16(data, pos)
    pos += 2
    main_ids = []
    for _ in range(main_size):
        main_ids.append(_u16(data, pos))
        pos += 2

    extra_size = _u16(data, pos)
    pos += 2
    extra_ids = []
    for _ in range(extra_size):
        extra_ids.append(_u16(data, pos))
        pos += 2

    side_size = _u16(data, pos)
    pos += 2
    side_ids = []
    for _ in range(side_size):
        side_ids.append(_u16(data, pos))
        pos += 2

    trailing = data[pos:]

    def _card_names(ids: list[int]) -> list[str]:
        return [KONAMI_ID_TO_CARD_NAME.get(card_id, f"UNKNOWN_{card_id}") for card_id in ids]

    return {
        "format": "ydc.v1",
        "header_b64": base64.b64encode(header).decode("ascii"),
        "main_size": main_size,
        "extra_size": extra_size,
        "side_size": side_size,
        "main_deck": _card_names(main_ids),
        "extra_deck": _card_names(extra_ids),
        "side_deck": _card_names(side_ids),
        "trailing_b64": base64.b64encode(trailing).decode("ascii"),
    }


def _entry_to_konami_id(entry: Any) -> int:
    """Resolve a deck entry to a Konami ID.

    Supported forms:
    - int: raw Konami ID
    - str: card name (preferred for editing), or UNKNOWN_<id>
    - dict: legacy form with optional `konami_id` and/or `card_name`
    """
    if isinstance(entry, int):
        return entry & 0xFFFF

    if isinstance(entry, str):
        cid = card_name_to_konami_id(entry)
        if cid is not None:
            return cid & 0xFFFF
        if entry.startswith("UNKNOWN_"):
            suffix = entry.split("UNKNOWN_", 1)[1]
            return int(suffix) & 0xFFFF
        raise ValueError(f"Unknown card name: {entry}")

    if isinstance(entry, dict):
        if "konami_id" in entry and entry["konami_id"] is not None:
            return int(entry["konami_id"]) & 0xFFFF
        if "card_name" in entry and entry["card_name"] is not None:
            return _entry_to_konami_id(str(entry["card_name"]))

    raise ValueError(f"Unsupported deck entry: {entry}")


def encode_ydc(payload: dict[str, Any]) -> bytes:
    """Encode a structured YDC payload back into bytes."""
    header = base64.b64decode(str(payload.get("header_b64", "")))
    if len(header) != 8:
        raise ValueError("header_b64 must decode to exactly 8 bytes")

    main_entries = payload.get("main_deck", [])
    extra_entries = payload.get("extra_deck", [])
    side_entries = payload.get("side_deck", [])

    main_ids = [_entry_to_konami_id(entry) for entry in main_entries]
    extra_ids = [_entry_to_konami_id(entry) for entry in extra_entries]
    side_ids = [_entry_to_konami_id(entry) for entry in side_entries]

    out = bytearray()
    out.extend(header)
    out.extend(len(main_ids).to_bytes(2, "little"))
    for card_id in main_ids:
        out.extend(card_id.to_bytes(2, "little"))

    out.extend(len(extra_ids).to_bytes(2, "little"))
    for card_id in extra_ids:
        out.extend(card_id.to_bytes(2, "little"))

    out.extend(len(side_ids).to_bytes(2, "little"))
    for card_id in side_ids:
        out.extend(card_id.to_bytes(2, "little"))

    trailing = base64.b64decode(str(payload.get("trailing_b64", "")))
    out.extend(trailing)
    return bytes(out)


def decode_ydc_to_json(data: bytes) -> str:
    """Decode YDC bytes to JSON text for editing."""
    return json.dumps(decode_ydc(data), ensure_ascii=False, indent=2)


def encode_ydc_from_json(text: str) -> bytes:
    """Encode JSON text back to YDC bytes."""
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("YDC JSON must be an object")
    return encode_ydc(payload)


def decode_ydc_ids(data: bytes) -> dict[str, Any]:
    """Decode a .ydc into raw header + three cid lists, no name round-trip.

    Id-based on purpose: the konami-id/name table has wrong entries, and going
    through names silently swaps cards (Dupe Frog becomes Ronintoadin).
    """
    if len(data) < 14:
        raise ValueError("ydc too small")
    out: dict[str, Any] = {"header": data[:8]}
    pos = 8
    for zone in ("main", "extra", "side"):
        count = _u16(data, pos)
        pos += 2
        out[zone] = [_u16(data, pos + 2 * i) for i in range(count)]
        pos += 2 * count
    out["trailing"] = data[pos:]
    return out


def encode_ydc_ids(deck: dict[str, Any]) -> bytes:
    """Inverse of :func:`decode_ydc_ids`."""
    buf = bytearray(deck["header"])
    for zone in ("main", "extra", "side"):
        ids = deck.get(zone, [])
        buf += len(ids).to_bytes(2, "little")
        for cid in ids:
            buf += (cid & 0xFFFF).to_bytes(2, "little")
    buf += deck.get("trailing", b"")
    return bytes(buf)
