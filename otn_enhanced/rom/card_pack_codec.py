"""Codec for card_pack.bin: decode raw bytes to structured JSON and encode back.

Each card_pack entry is 8 bytes.  The layout is:

| Byte | Field             | Description                    |
|------|-------------------|--------------------------------|
| 0    | rarity_1          | Primary rarity value           |
| 1    | rarity_2          | Secondary rarity value         |
| 2    | unused_rarity_3   | Unused (always 0 in data)      |
| 3    | pack_1            | Primary pack ID                |
| 4    | pack_2            | Secondary pack ID              |
| 5    | unused_pack_3     | Unused                         |
| 6    | unused_byte_1     | Unused                         |
| 7    | unused_byte_2     | Unused                         |

Rarity values:
  0 = Not available / Common
  2 = Ultra Rare
  3 = Super Rare
  4 = Rare

The file starts with an 8-byte header (all zeros in WC2007, may vary in
other games).  Card entries follow immediately after.

Round-trip fidelity is maintained by preserving the raw header/trailer bytes
in the returned metadata.
"""

from __future__ import annotations

import base64
import json
import struct
from collections import defaultdict
from typing import Any


RARITY_MAP: dict[int, str] = {
    0: "Common",
    2: "Ultra Rare",
    3: "Super Rare",
    4: "Rare",
}


def _rarity_label(value: int) -> str:
    """Return human-readable rarity label."""
    return RARITY_MAP.get(value, f"Unknown({value})")


def decode_card_pack(
    data: bytes,
    card_names: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Decode card_pack.bin into editable JSON with pack summaries.

    Parameters
    ----------
    data : bytes
        Raw ``card_pack.bin`` content (8-byte header + N×8 body).
    card_names : list[str] | None
        Optional list of card names (from ``card_name_e.bin``).

    Returns a ``(json_text, meta)`` tuple.  *meta* carries the header/trailer
    bytes needed by :func:`encode_card_pack` to round-trip losslessly.
    """
    if len(data) < 8:
        raise ValueError("card_pack.bin is too small")

    header = data[:8]
    body = data[8:]
    entry_count = len(body) // 8
    trailing = body[entry_count * 8:]

    rows: list[dict[str, Any]] = []
    # Track cards per pack: pack_id → list of {index, name, rarity_label}
    pack_cards: dict[int, list[dict[str, Any]]] = defaultdict(list)
    # Track rarity counts per pack: pack_id → rarity_label → count
    pack_rarity_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for i in range(entry_count):
        chunk = body[i * 8 : (i + 1) * 8]
        fields = struct.unpack("<8B", chunk)

        rarity_1 = fields[0]
        rarity_2 = fields[1]
        unused_rarity_3 = fields[2]
        pack_1 = fields[3]
        pack_2 = fields[4]
        unused_pack_3 = fields[5]
        unused_byte_1 = fields[6]
        unused_byte_2 = fields[7]

        name = card_names[i] if card_names and i < len(card_names) else ""

        row: dict[str, Any] = {
            "index": i,
            "name": name,
            "rarity_1": rarity_1,
            "rarity_1_label": _rarity_label(rarity_1),
            "rarity_2": rarity_2,
            "rarity_2_label": _rarity_label(rarity_2),
            "unused_rarity_3": unused_rarity_3,
            "pack_1": pack_1,
            "pack_2": pack_2,
            "unused_pack_3": unused_pack_3,
            "unused_byte_1": unused_byte_1,
            "unused_byte_2": unused_byte_2,
        }
        rows.append(row)

        # Accumulate pack summary for pack_1
        if pack_1 > 0:
            r1_label = _rarity_label(rarity_1)
            pack_cards[pack_1].append({
                "index": i,
                "name": name,
                "rarity": r1_label,
            })
            pack_rarity_counts[pack_1][r1_label] += 1

        # Accumulate pack summary for pack_2
        if pack_2 > 0:
            r2_label = _rarity_label(rarity_2)
            pack_cards[pack_2].append({
                "index": i,
                "name": name,
                "rarity": r2_label,
            })
            pack_rarity_counts[pack_2][r2_label] += 1

    # Build pack summaries sorted by pack ID
    pack_summary: list[dict[str, Any]] = []
    for pack_id in sorted(pack_cards.keys()):
        cards = pack_cards[pack_id]
        rarity_breakdown = dict(pack_rarity_counts[pack_id])
        pack_summary.append({
            "pack_id": pack_id,
            "card_count": len(cards),
            "rarity_breakdown": rarity_breakdown,
            "cards": cards,
        })

    payload = {
        "format": "card_pack.v1",
        "entry_count": entry_count,
        "pack_summary": pack_summary,
        "rows": rows,
    }

    meta = {
        "format": "card_pack.v1",
        "entry_count": entry_count,
        "header_b64": base64.b64encode(header).decode("ascii"),
        "trailing_b64": base64.b64encode(trailing).decode("ascii"),
    }

    return json.dumps(payload, ensure_ascii=False, indent=2), meta


def encode_card_pack(text: str, meta: dict[str, Any] | None = None) -> bytes:
    """Encode edited JSON for card_pack.bin back to bytes.

    Only the ``rows`` array is used for encoding.  The ``pack_summary``
    section is derived data and is regenerated on the next decode.

    Parameters
    ----------
    text : str
        JSON text (the same format returned by :func:`decode_card_pack`).
    meta : dict | None
        Metadata dict from a prior :func:`decode_card_pack` call, carrying
        the original header/trailer.  If *None*, an 8-byte zero header is
        used with no trailer.
    """
    parsed = json.loads(text)

    if isinstance(parsed, dict):
        rows = parsed.get("rows", [])
    elif isinstance(parsed, list):
        rows = parsed
    else:
        raise ValueError("Invalid card_pack JSON format")

    if meta:
        expected_count = int(meta.get("entry_count", 0))
        if expected_count and len(rows) != expected_count:
            raise ValueError(
                f"Row count mismatch. Expected {expected_count}, got {len(rows)}"
            )
        header = base64.b64decode(str(meta.get("header_b64", "")))
        trailing = base64.b64decode(str(meta.get("trailing_b64", "")))
    else:
        header = b"\x00" * 8
        trailing = b""

    body = bytearray()
    for row in rows:
        entry = struct.pack(
            "<8B",
            int(row.get("rarity_1", 0)),
            int(row.get("rarity_2", 0)),
            int(row.get("unused_rarity_3", 0)),
            int(row.get("pack_1", 0)),
            int(row.get("pack_2", 0)),
            int(row.get("unused_pack_3", 0)),
            int(row.get("unused_byte_1", 0)),
            int(row.get("unused_byte_2", 0)),
        )
        body.extend(entry)

    return header + bytes(body) + trailing
