"""Codec for card_prop.bin: decode raw bytes to structured JSON and encode back.

Each card_prop entry is an 8-byte (64-bit) little-endian bitfield.  The
bit layout differs between ERA1 (WC2007/WC2008) and ERA2 (SA/RoA/OTN).
Decoding and encoding are delegated to :class:`GameConstants`, which knows
the correct bitfield positions for each era.

Round-trip fidelity is maintained by preserving the raw ``u64`` value in
each decoded row.  Unknown/reserved bits are carried through untouched.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS, GameConstants


def decode_card_prop(
    data: bytes,
    card_names: list[str] | None = None,
    gc: GameConstants | None = None,
) -> tuple[str, dict[str, Any]]:
    """Decode card_prop.bin into editable JSON with optional card names.

    Parameters
    ----------
    data : bytes
        Raw ``card_prop.bin`` content (8-byte header + N×8 body).
    card_names : list[str] | None
        Optional list of card names (from ``card_name_e.bin``).
    gc : GameConstants | None
        Game-specific constants.  Defaults to era-2 (OTN) encoding.

    Returns a ``(json_text, meta)`` tuple.  *meta* carries the header/trailer
    bytes needed by :func:`encode_card_prop` to round-trip losslessly.
    """
    if gc is None:
        gc = DEFAULT_CONSTANTS

    if len(data) < 8:
        raise ValueError("card_prop.bin is too small")

    header = data[:8]
    body = data[8:]
    entry_count = len(body) // 8
    trailing = body[entry_count * 8:]
    rows: list[dict[str, Any]] = []

    for i in range(entry_count):
        chunk = body[i * 8 : (i + 1) * 8]
        decoded = gc.decode_entry(chunk)
        decoded["index"] = i
        decoded["name"] = card_names[i] if card_names and i < len(card_names) else ""
        rows.append(decoded)

    payload = {
        "format": "card_prop.v2",
        "entry_count": entry_count,
        "era": gc.era,
        "rows": rows,
    }
    meta = {
        "format": "card_prop.v2",
        "entry_count": entry_count,
        "era": gc.era,
        "header_b64": base64.b64encode(header).decode("ascii"),
        "trailing_b64": base64.b64encode(trailing).decode("ascii"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2), meta


def encode_card_prop(text: str, meta: dict[str, Any], gc: GameConstants | None = None) -> bytes:
    """Encode edited JSON for card_prop.bin back to bytes.

    The ``raw_u64`` field in each row is used as the base value, ensuring
    that unknown/reserved bits survive the round-trip.  Only fields that
    have been explicitly modified will change the output.
    """
    if gc is None:
        gc = DEFAULT_CONSTANTS

    parsed = json.loads(text)
    if isinstance(parsed, dict):
        rows = parsed.get("rows", [])
    elif isinstance(parsed, list):
        rows = parsed
    else:
        raise ValueError("Invalid card_prop JSON format")

    expected_count = int(meta.get("entry_count", 0))
    if len(rows) != expected_count:
        raise ValueError(f"Row count mismatch. Expected {expected_count}, got {len(rows)}")

    header = base64.b64decode(str(meta.get("header_b64", "")))
    trailing = base64.b64decode(str(meta.get("trailing_b64", "")))

    body = bytearray()
    for row in rows:
        entry_bytes = gc.encode_entry(row)
        body.extend(entry_bytes)

    return header + bytes(body) + trailing


def encode_card_prop_text(text: str) -> bytes:
    """Encode card_prop.bin text back into raw UTF-8 bytes (passthrough)."""
    return text.encode("utf-8")
