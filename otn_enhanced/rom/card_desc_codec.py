"""Codec for card_desc_e.bin: decode raw bytes to structured JSON and encode back.

``card_desc_e.bin`` lives inside ``bin2.pac`` (or ``bin.pac`` for WC2007) and
contains one **null-terminated, Shift-JIS-encoded, 4-byte-aligned** description
string per card.  There is no header — entries start at byte 0.

Layout::

    [str_0 \\x00 <pad>] [str_1 \\x00 <pad>] ... [str_N \\x00 <pad>] [trailing]

Each string is null-terminated and then padded with additional null bytes so
that the *next* entry begins on a 4-byte-aligned offset from the start of the
file.  Empty descriptions (cards with no text) are stored as a single ``\\x00``
followed by alignment padding.

Round-trip fidelity is maintained by:
* Storing each description's original raw Shift-JIS bytes (base64-encoded) so
  that encoding can reproduce the *exact* original binary even if the decoded
  Unicode string would re-encode differently.
* Preserving any trailing bytes after the last entry.
"""

from __future__ import annotations

import base64
import json
from typing import Any


_ENCODING = "shift-jis"
_FALLBACK_ENCODING = "latin-1"
_ALIGNMENT = 4


def _decode_string(raw: bytes) -> str:
    """Decode a single Shift-JIS string with latin-1 fallback."""
    try:
        return raw.decode(_ENCODING)
    except UnicodeDecodeError:
        return raw.decode(_FALLBACK_ENCODING)


def _parse_aligned_strings(data: bytes) -> tuple[list[bytes], bytes]:
    """Parse 4-byte-aligned null-terminated strings from *data*.

    Returns ``(entries, trailing)`` where *entries* is a list of raw byte
    strings (without terminators/padding) and *trailing* is any leftover
    bytes after the last parseable entry.
    """
    entries: list[bytes] = []
    pos = 0
    while pos < len(data):
        null_idx = data.find(b"\x00", pos)
        if null_idx == -1:
            # No more null terminators — rest is trailing data.
            break
        entries.append(data[pos:null_idx])
        # Advance past null terminator, then pad to next 4-byte boundary.
        pos = null_idx + 1
        remainder = pos % _ALIGNMENT
        if remainder != 0:
            pos += _ALIGNMENT - remainder
    # Anything beyond the last parsed entry is trailing.
    trailing = data[pos:] if pos < len(data) and data.find(b"\x00", pos) == -1 else b""
    return entries, trailing


def decode_card_desc(
    data: bytes,
    card_names: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Decode card_desc_e.bin into editable JSON.

    Parameters
    ----------
    data : bytes
        Raw ``card_desc_e.bin`` content (4-byte-aligned null-terminated
        Shift-JIS strings, no header).
    card_names : list[str] | None
        Optional list of card names (from ``card_name_e.bin``) used to
        annotate each entry.  Note: the dash app currently extracts names
        by filtering out empties, so the list may be shorter than the
        number of description entries.  In that case only the first
        ``len(card_names)`` annotations are populated.

    Returns a ``(json_text, meta)`` tuple.  *meta* carries the trailing
    bytes needed by :func:`encode_card_desc` to round-trip losslessly.
    """
    raw_entries, trailing = _parse_aligned_strings(data)

    # card_names is typically extracted by filtering empty strings from
    # card_name_e.bin, so it may be shorter than raw_entries when the file
    # has leading empty placeholder entries.  Compute the offset so that
    # card_names[0] lines up with the first non-empty description.
    name_offset = len(raw_entries) - len(card_names) if card_names else 0

    rows: list[dict[str, Any]] = []
    for i, raw in enumerate(raw_entries):
        text = _decode_string(raw)
        ni = i - name_offset
        row: dict[str, Any] = {
            "index": i,
            "name": card_names[ni] if card_names and 0 <= ni < len(card_names) else "",
            "desc": text,
            "raw_b64": base64.b64encode(raw).decode("ascii"),
        }
        rows.append(row)

    payload = {
        "format": "card_desc.v2",
        "entry_count": len(rows),
        "rows": rows,
    }

    meta = {
        "format": "card_desc.v2",
        "entry_count": len(rows),
        "trailing_b64": base64.b64encode(trailing).decode("ascii"),
    }

    return json.dumps(payload, ensure_ascii=False, indent=2), meta


def encode_card_desc(text: str, meta: dict[str, Any] | None = None) -> bytes:
    """Encode edited JSON back to card_desc_e.bin bytes.

    For each row the encoder checks whether the ``desc`` text matches the
    original ``raw_b64`` bytes.  If the description was **not** modified the
    original raw bytes are used verbatim (perfect round-trip).  If it *was*
    modified the new text is re-encoded to Shift-JIS.

    Each entry is null-terminated and padded to the next 4-byte boundary.

    Parameters
    ----------
    text : str
        JSON text (same format returned by :func:`decode_card_desc`).
    meta : dict | None
        Metadata dict from a prior :func:`decode_card_desc` call, carrying
        the original trailing bytes.  If *None*, no trailing bytes are
        appended.
    """
    parsed = json.loads(text)

    if isinstance(parsed, dict):
        rows = parsed.get("rows", [])
    elif isinstance(parsed, list):
        rows = parsed
    else:
        raise ValueError("Invalid card_desc JSON format")

    if meta:
        expected_count = int(meta.get("entry_count", 0))
        if expected_count and len(rows) != expected_count:
            raise ValueError(
                f"Row count mismatch. Expected {expected_count}, got {len(rows)}"
            )
        trailing = base64.b64decode(str(meta.get("trailing_b64", "")))
        # Support legacy v1 meta that had header_b64 (ignored now).
    else:
        trailing = b""

    body = bytearray()
    for row in rows:
        desc = str(row.get("desc", ""))
        raw_b64 = row.get("raw_b64")

        if raw_b64:
            original_raw = base64.b64decode(raw_b64)
            # Check if the decoded text still matches the original raw bytes.
            if _decode_string(original_raw) == desc:
                body.extend(original_raw)
            else:
                body.extend(desc.encode(_ENCODING, errors="replace"))
        else:
            body.extend(desc.encode(_ENCODING, errors="replace"))

        body.append(0x00)  # null terminator

        # Pad to 4-byte alignment.
        remainder = len(body) % _ALIGNMENT
        if remainder != 0:
            body.extend(b"\x00" * (_ALIGNMENT - remainder))

    return bytes(body) + trailing
