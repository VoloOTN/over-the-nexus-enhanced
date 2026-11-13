"""Codec for card_genre.bin — per-card genre/category flags.

card_genre.bin lives in bin2.pac and is indexed parallel to card_prop.bin.
Each card has an 8-byte (u64 LE) record containing category and summon-type flags.

Format:
  - 8-byte header
  - Then 8 bytes per card (in card_prop.bin record order)

Known bitfield (OTN / ERA2):
  - Bit 10:  Genre category flag (set on Spells/Traps)
  - Bit 21:  "Special Summon only / Cannot be Normal Summoned" flag
           (set on inherent nomi types: Fusion, Synchro, Ritual, Toon, and main-deck nomi Effects)
  - Other bits: Unknown / unused

Reference:
  - ygo_tools.tools.patch_yubel_cardprop.py: copies entire 8-byte genre records
  - HOWTO.md §4: Spell/Trap conversion requires clearing genre "flag bits"
"""

from __future__ import annotations

import json
import struct
from base64 import b64encode, b64decode


def decode_card_genre(data: bytes) -> tuple[str, dict]:
    """Decode card_genre.bin → (json_text, metadata).
    
    Args:
        data: Full binary contents of card_genre.bin (8-byte header + records)
    
    Returns:
        Tuple of (JSON text, metadata dict)
        - JSON contains: format, rows (list of genre records with card_index, raw_u64, bits)
        - Metadata contains: format, header_b64, trailing_b64
    """
    if len(data) < 8:
        raise ValueError("card_genre.bin too short (need at least 8 bytes for header)")
    
    header = data[:8]
    body = data[8:]
    
    if len(body) % 8 != 0:
        raise ValueError(f"card_genre.bin body not multiple of 8: {len(body)} bytes")
    
    entry_count = len(body) // 8
    rows = []
    
    for i in range(entry_count):
        off = i * 8
        val = int.from_bytes(body[off:off+8], "little")
        
        # Decode known bitfields
        genre_bit = (val >> 10) & 1
        nomi_bit = (val >> 21) & 1
        
        rows.append({
            "card_index": i,
            "raw_u64": val,
            "genre_category_bit_10": genre_bit,
            "special_summon_only_bit_21": nomi_bit,
        })
    
    payload = {
        "format": "card_genre.v1",
        "rows": rows,
    }
    
    meta = {
        "format": "card_genre.v1",
        "header_b64": b64encode(header).decode("ascii"),
        "trailing_b64": b64encode(b"").decode("ascii"),  # no trailing data
    }
    
    return json.dumps(payload, indent=2), meta


def encode_card_genre(text: str, meta: dict) -> bytes:
    """Encode json_text + metadata → card_genre.bin binary.
    
    Args:
        text: JSON text from decode_card_genre
        meta: Metadata dict from decode_card_genre
    
    Returns:
        Binary card_genre.bin (8-byte header + records)
    """
    parsed = json.loads(text)
    rows = parsed.get("rows", [])
    
    header = b64decode(meta.get("header_b64", ""))
    if len(header) == 0:
        header = b"\x00" * 8
    
    body = bytearray()
    for row in rows:
        # Use raw_u64 as the base (preserves unknown bits)
        val = row.get("raw_u64", 0)
        
        # Inject known bitfields if they're present in the row
        if "genre_category_bit_10" in row:
            bit = row["genre_category_bit_10"] & 1
            val = (val & ~(1 << 10)) | (bit << 10)
        
        if "special_summon_only_bit_21" in row:
            bit = row["special_summon_only_bit_21"] & 1
            val = (val & ~(1 << 21)) | (bit << 21)
        
        body.extend(val.to_bytes(8, "little"))
    
    return header + bytes(body)
