"""Codec for limit*.bin (ban list) files: decode to structured JSON and encode back.

Each ``limit*.bin`` file inside ``bin.pac`` defines a Yu-Gi-Oh! Forbidden
& Limited list.  The binary format is:

Header (8 bytes)
~~~~~~~~~~~~~~~~
::

    Offset  Type       Field
    ------  ---------  ---------------------------------
    0       uint16 LE  Total entry count
    2       uint16 LE  Banned monster count (see below)
    4       uint16 LE  Unused (always 0)
    6       uint16 LE  Unused (always 0)

Body (N × 2 bytes)
~~~~~~~~~~~~~~~~~~
Each entry is a **uint16 LE** value whose upper 2 bits encode the ban
status and whose lower 14 bits are the Konami card ID:

::

    Bits 15-14  Status
    ----------  ----------------
    0b00        Forbidden (Banned)
    0b01        Limited   (1 copy)
    0b10        Semi-Limited (2 copies)

Ordering
~~~~~~~~
Entries are stored contiguously by status group:

1. Forbidden (banned) entries
2. Limited entries
3. Semi-limited entries

Within each group, **monsters** appear first followed by **spells/traps**.
The header field at offset 2 records the number of banned *monsters*
(i.e. how many entries at the very start of the body are banned monsters).

Round-trip fidelity
~~~~~~~~~~~~~~~~~~~
Header padding bytes and the ``banned_monster_count`` field are preserved
in the returned metadata so that :func:`encode_limit` reproduces the
original binary exactly.
"""

from __future__ import annotations

import base64
import json
import struct
from typing import Any

# ── Status flag constants ──────────────────────────────────────────
FLAG_BANNED: int = 0x0000
FLAG_LIMITED: int = 0x4000
FLAG_SEMI_LIMITED: int = 0x8000
FLAG_MASK: int = 0xC000
KONAMI_ID_MASK: int = 0x3FFF

STATUS_FLAG_TO_LABEL: dict[int, str] = {
    FLAG_BANNED: "Forbidden",
    FLAG_LIMITED: "Limited",
    FLAG_SEMI_LIMITED: "Semi-Limited",
}

LABEL_TO_STATUS_FLAG: dict[str, int] = {v: k for k, v in STATUS_FLAG_TO_LABEL.items()}


def decode_limit(data: bytes) -> tuple[str, dict[str, Any]]:
    """Decode a ``limit*.bin`` file into editable JSON.

    Parameters
    ----------
    data : bytes
        Raw limit file content (8-byte header + N × 2 body).

    Returns
    -------
    tuple[str, dict[str, Any]]
        ``(json_text, meta)`` where *meta* carries header details needed
        by :func:`encode_limit` for lossless round-trip.
    """
    if len(data) < 8:
        raise ValueError("limit file is too small (need ≥ 8 bytes)")

    total_count, banned_monster_count, reserved_1, reserved_2 = struct.unpack(
        "<4H", data[:8]
    )

    body = data[8:]
    actual_entries = len(body) // 2
    trailing = body[actual_entries * 2:]

    forbidden: list[int] = []
    limited: list[int] = []
    semi_limited: list[int] = []

    for i in range(actual_entries):
        raw = struct.unpack_from("<H", body, i * 2)[0]
        flag = raw & FLAG_MASK
        konami_id = raw & KONAMI_ID_MASK
        if flag == FLAG_BANNED:
            forbidden.append(konami_id)
        elif flag == FLAG_LIMITED:
            limited.append(konami_id)
        elif flag == FLAG_SEMI_LIMITED:
            semi_limited.append(konami_id)

    payload: dict[str, Any] = {
        "format": "limit.v1",
        "banned_monster_count": banned_monster_count,
        "Forbidden": forbidden,
        "Limited": limited,
        "Semi-Limited": semi_limited,
    }

    meta: dict[str, Any] = {
        "format": "limit.v1",
        "banned_monster_count": banned_monster_count,
        "reserved_1": reserved_1,
        "reserved_2": reserved_2,
        "trailing_b64": base64.b64encode(trailing).decode("ascii"),
    }

    return json.dumps(payload, ensure_ascii=False, indent=2), meta


def encode_limit(text: str, meta: dict[str, Any] | None = None) -> bytes:
    """Encode edited JSON back to ``limit*.bin`` bytes.

    The JSON contains three lists of Konami IDs keyed by status:
    ``"Forbidden"``, ``"Limited"``, ``"Semi-Limited"``.

    Parameters
    ----------
    text : str
        JSON text (same format returned by :func:`decode_limit`).
    meta : dict | None
        Metadata dict from a prior :func:`decode_limit` call.
    """
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Invalid limit JSON format")

    forbidden = [int(v) & KONAMI_ID_MASK for v in parsed.get("Forbidden", [])]
    limited = [int(v) & KONAMI_ID_MASK for v in parsed.get("Limited", [])]
    semi_limited = [int(v) & KONAMI_ID_MASK for v in parsed.get("Semi-Limited", [])]

    entries: list[int] = []
    for kid in forbidden:
        entries.append(FLAG_BANNED | kid)
    for kid in limited:
        entries.append(FLAG_LIMITED | kid)
    for kid in semi_limited:
        entries.append(FLAG_SEMI_LIMITED | kid)

    total_count = len(entries)

    # Prefer the value from the JSON payload, then meta, then count
    # leading Forbidden entries as a fallback.
    banned_monster_count: int | None = None
    if "banned_monster_count" in parsed:
        banned_monster_count = int(parsed["banned_monster_count"])
    if banned_monster_count is None and meta and "banned_monster_count" in meta:
        banned_monster_count = int(meta["banned_monster_count"])
    if banned_monster_count is None:
        banned_monster_count = len(forbidden)

    reserved_1 = 0
    reserved_2 = 0
    trailing = b""
    if meta:
        reserved_1 = int(meta.get("reserved_1", 0))
        reserved_2 = int(meta.get("reserved_2", 0))
        trailing_b64 = str(meta.get("trailing_b64", ""))
        if trailing_b64:
            trailing = base64.b64decode(trailing_b64)

    header = struct.pack("<4H", total_count, banned_monster_count, reserved_1, reserved_2)
    body = struct.pack(f"<{total_count}H", *entries)

    return header + body + trailing
