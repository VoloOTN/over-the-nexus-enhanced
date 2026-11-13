"""Decoder/encoder utilities for YDQ puzzle-duel files.

Binary layout
=============
Offset  Size  Description
------  ----  -----------
0       2     Magic ``0x59 0x51``
2       2     Player 1 life-points  (uint16 LE)
4       2     Player 2 life-points  (uint16 LE)
6       2     Unknown / flags       (preserved as opaque bytes)

--- Player 1 section ---
8       3*N   Field-card triplets   (2-byte Konami ID LE + 1-byte position)
                Read greedily while the next uint16 is a known card ID.
var     ...   Zone lists            (Hand → ED → Deck → GY → Banish)
                Each zone: 1 byte count + count×2-byte card IDs.
                Read greedily while the count byte yields all-valid IDs.

--- Separator ---
var     1     Separator byte        (opaque, preserved)
var     1     P2 flag byte          (0x00 or 0x01 observed; opaque, preserved)

--- Player 2 section ---
var     3*N   Field-card triplets   (same encoding as P1)
                Read greedily until uint16 == 0 or unknown ID.
var     ...   Zone lists            (same encoding as P1)

--- Tail ---
var     1     Terminator ``0x00``
var     N     Optional speed-world / turbo-duel appendix (preserved opaque)

Position byte reference (field cards)
-------------------------------------
0x00  Face-down
0x01  Face-up Spell/Trap zone
0x03  Face-up DEF monster
0x11  Face-up ATK monster
"""

from __future__ import annotations

import base64
import json
from typing import Any

from otn_enhanced.rom.konami_id_to_card_name import KONAMI_ID_TO_CARD_NAME, card_name_to_konami_id

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ZONE_ORDER = ("hand", "extra_deck", "deck", "graveyard", "banish")


def _u16(data: bytes, offset: int) -> int:
    """Read little-endian uint16."""
    if offset + 2 > len(data):
        raise ValueError(f"Unexpected end of data at offset {offset}")
    return int.from_bytes(data[offset : offset + 2], "little")


def _card_name(kid: int) -> str:
    return KONAMI_ID_TO_CARD_NAME.get(kid, f"UNKNOWN_{kid}")


def _is_known_card(kid: int) -> bool:
    return kid in KONAMI_ID_TO_CARD_NAME


# ---------------------------------------------------------------------------
# Decode
# ---------------------------------------------------------------------------

def _read_field_cards(data: bytes, off: int) -> tuple[list[dict], int]:
    """Read field-card triplets greedily while the next u16 is a known card."""
    cards: list[dict] = []
    while off + 2 < len(data):
        kid = _u16(data, off)
        if not _is_known_card(kid):
            break
        pos = data[off + 2]
        cards.append({"card": _card_name(kid), "position": pos})
        off += 3
    return cards, off


def _read_zones(data: bytes, off: int) -> tuple[dict[str, list[str]], int]:
    """Read zone lists greedily (count + count×u16 card IDs).

    Stops when the count byte would produce an invalid card ID in that zone,
    or the count exceeds a sane limit.
    """
    zones: dict[str, list[str]] = {}
    zone_idx = 0
    while off < len(data) and zone_idx < len(_ZONE_ORDER):
        count = data[off]
        # Sanity: a zone with >20 cards is almost certainly a mis-read
        if count > 20 or off + 1 + count * 2 > len(data):
            break
        # Validate every card ID in the tentative zone
        zone_cards: list[str] = []
        valid = True
        for j in range(count):
            kid = _u16(data, off + 1 + j * 2)
            if not _is_known_card(kid):
                valid = False
                break
            zone_cards.append(_card_name(kid))
        if not valid:
            break
        off += 1 + count * 2
        zones[_ZONE_ORDER[zone_idx]] = zone_cards
        zone_idx += 1
    return zones, off


def decode_ydq(data: bytes) -> dict[str, Any]:
    """Decode raw YDQ bytes into a structured dictionary."""
    if len(data) < 8:
        raise ValueError("YDQ data too small")
    if data[0:2] != b"\x59\x51":
        raise ValueError(f"Bad YDQ magic: {data[0:2].hex()}")

    result: dict[str, Any] = {
        "format": "ydq.v1",
        "p1_lp": _u16(data, 2),
        "p2_lp": _u16(data, 4),
        "unknown_b64": base64.b64encode(data[6:8]).decode("ascii"),
    }

    off = 8

    # -- Player 1 --
    p1_field, off = _read_field_cards(data, off)
    p1_zones, off = _read_zones(data, off)
    result["p1_field"] = p1_field
    result["p1_zones"] = p1_zones

    # -- Separator (2 opaque bytes) + Player 2 --
    if off + 2 <= len(data):
        result["separator"] = data[off]
        result["p2_flag"] = data[off + 1]
        off += 2

        p2_field, off = _read_field_cards(data, off)
        p2_zones, off = _read_zones(data, off)
        result["p2_field"] = p2_field
        result["p2_zones"] = p2_zones

    # -- Remaining bytes (may include a 0x00 end-marker and/or speed-world appendix) --
    if off < len(data):
        result["tail_b64"] = base64.b64encode(data[off:]).decode("ascii")

    return result


# ---------------------------------------------------------------------------
# Encode
# ---------------------------------------------------------------------------

def _entry_to_konami_id(entry: Any) -> int:
    """Resolve a card entry (str name, int ID, or ``UNKNOWN_<id>``) to a Konami ID."""
    if isinstance(entry, int):
        return entry & 0xFFFF
    if isinstance(entry, str):
        cid = card_name_to_konami_id(entry)
        if cid is not None:
            return cid & 0xFFFF
        if entry.startswith("UNKNOWN_"):
            return int(entry.split("UNKNOWN_", 1)[1]) & 0xFFFF
        raise ValueError(f"Unknown card name: {entry}")
    raise ValueError(f"Unsupported card entry: {entry}")


def _resolve_card(entry: Any) -> int:
    """Resolve a field-card entry (str or dict with ``card`` key)."""
    if isinstance(entry, str):
        return _entry_to_konami_id(entry)
    if isinstance(entry, dict) and "card" in entry:
        return _entry_to_konami_id(entry["card"])
    raise ValueError(f"Unsupported field card entry: {entry}")


def _write_field_cards(buf: bytearray, cards: list[Any]) -> None:
    for fc in cards:
        if isinstance(fc, dict):
            kid = _resolve_card(fc)
            pos = int(fc.get("position", 0))
        else:
            kid = _entry_to_konami_id(fc)
            pos = 0
        buf.extend(kid.to_bytes(2, "little"))
        buf.append(pos & 0xFF)


def _write_zones(buf: bytearray, zones: dict[str, list[Any]]) -> None:
    # Find the last zone (by position) that is present in the dict.
    # Intermediate absent zones are written as 0-count to preserve positional order
    # so the decoder maps every zone to the correct slot.
    last_idx = -1
    for i, zn in enumerate(_ZONE_ORDER):
        if zn in zones:
            last_idx = i
    for i, zn in enumerate(_ZONE_ORDER):
        if i > last_idx:
            break
        cards = zones.get(zn, [])
        buf.append(len(cards) & 0xFF)
        for c in cards:
            kid = _entry_to_konami_id(c)
            buf.extend(kid.to_bytes(2, "little"))


def encode_ydq(payload: dict[str, Any]) -> bytes:
    """Encode a structured YDQ payload back into bytes."""
    buf = bytearray()

    # Header magic
    buf.extend(b"\x59\x51")

    # Life-points
    buf.extend(int(payload["p1_lp"]).to_bytes(2, "little"))
    buf.extend(int(payload["p2_lp"]).to_bytes(2, "little"))

    # Unknown 2 bytes
    unknown = base64.b64decode(payload.get("unknown_b64", "AAA="))
    if len(unknown) != 2:
        raise ValueError("unknown_b64 must decode to exactly 2 bytes")
    buf.extend(unknown)

    # Player 1
    _write_field_cards(buf, payload.get("p1_field", []))
    _write_zones(buf, payload.get("p1_zones", {}))

    # Separator + Player 2 (only if the decoded data contains them)
    if "separator" in payload:
        buf.append(int(payload["separator"]) & 0xFF)
        buf.append(int(payload.get("p2_flag", 0)) & 0xFF)

        _write_field_cards(buf, payload.get("p2_field", []))
        _write_zones(buf, payload.get("p2_zones", {}))

    # Tail (trailing bytes preserved verbatim — includes end-marker / speed-world data)
    tail = payload.get("tail_b64")
    if tail:
        buf.extend(base64.b64decode(tail))

    return bytes(buf)


# ---------------------------------------------------------------------------
# JSON convenience wrappers (used by the Dash conversion layer)
# ---------------------------------------------------------------------------

def decode_ydq_to_json(data: bytes) -> str:
    """Decode YDQ bytes to indented JSON text for editing."""
    return json.dumps(decode_ydq(data), ensure_ascii=False, indent=2)


def encode_ydq_from_json(text: str) -> bytes:
    """Encode edited JSON text back to YDQ bytes."""
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("YDQ JSON must be an object")
    return encode_ydq(payload)
