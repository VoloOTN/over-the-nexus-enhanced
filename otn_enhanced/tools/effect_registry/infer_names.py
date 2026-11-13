"""Heuristic, *advisory* labels for handlers, from card effect text.

This is inference, not ground truth — themes are surfaced as separate metadata,
never written into a primitive's real ``name``.

Using the verified card_prop -> indx -> desc join (cid = first u16 of each
8-byte card_prop row; English text at ``desc[ indx[8 + i*8 + 4] ]``), a handler
is tagged by the dominant gameplay theme of the cards that use it (search /
special-summon / draw / destroy / damage / negate / banish).  A handler used
overwhelmingly by "Special Summon" cards is *probably* part of a Special-Summon
effect — but the label describes its callers, not the routine's true purpose.
"""

from __future__ import annotations

import struct
from collections import Counter


# Theme keyword buckets, checked against lower-cased English effect text.
# Order matters only for tie-breaking display; a card can match several.
_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "search":          ("add 1", "add it to your hand", "to your hand",
                        "search your deck"),
    "special_summon":  ("special summon",),
    "draw":            ("draw 1", "draw 2", "draw a card", "draw cards"),
    "destroy":         ("destroy",),
    "damage":          ("inflict", "damage to your opponent", "lp damage"),
    "negate":          ("negate",),
    "banish":          ("banish", "remove from play", "removed from play"),
    "tribute":         ("tribute",),
    "graveyard":       ("from your graveyard", "in your graveyard",
                        "to the graveyard"),
}

def load_card_text() -> dict[int, tuple[str, str]]:
    """Return ``{konami_id: (name, english_desc)}`` from the base ROM's bin2.pac.

    The join, verified by matching 4294/4305 decoded names against the
    konami-id name map:

    * Each ``card_prop.bin`` 8-byte row ``i`` is one card; the Konami id is
      the first u16 (``& 0x3FFF``).
    * ``card_indx_e.bin`` has **no header** — record ``i`` is at byte ``i*8`` and
      holds ``(name_offset, desc_offset)`` as two u32s.
    * ``name_offset`` points at the exact start of the name string.
    * ``desc_offset`` points *into* the desc string (a stored cursor, ~20 bytes
      in), so the true text starts at the preceding NUL — scan back for it.
    """
    from otn_enhanced.rom import stock
    prop = stock.bin2("card_prop.bin")
    indx = stock.bin2("card_indx_e.bin")
    name = stock.bin2("card_name_e.bin")
    desc = stock.bin2("card_desc_e.bin")

    def _decode(raw: bytes) -> str:
        try:
            return raw.decode("shift-jis")
        except UnicodeDecodeError:
            return raw.decode("latin-1", "replace")

    def name_at(off: int) -> str:
        end = name.find(b"\x00", off)
        return _decode(name[off:end if end >= 0 else None])

    def desc_at(off: int) -> str:
        start = desc.rfind(b"\x00", 0, off) + 1     # back to the string boundary
        end = desc.find(b"\x00", start)
        return _decode(desc[start:end if end >= 0 else None])

    out: dict[int, tuple[str, str]] = {}
    rows = len(prop) // 8
    for i in range(rows):
        cid = struct.unpack_from("<H", prop, i * 8)[0] & 0x3FFF
        rec = i * 8                            # nds_indx.bin has no header
        if rec + 8 > len(indx):
            continue
        noff = struct.unpack_from("<I", indx, rec)[0]
        doff = struct.unpack_from("<I", indx, rec + 4)[0]
        nm = name_at(noff) if noff < len(name) else ""
        ds = desc_at(doff) if doff < len(desc) else ""
        # First write wins (the canonical record for a cid comes first).
        out.setdefault(cid, (nm, ds))
    return out


def text_themes(text: str) -> set[str]:
    """Return the gameplay themes a single effect-text string matches."""
    low = text.lower()
    return {theme for theme, kws in _THEME_KEYWORDS.items()
            if any(kw in low for kw in kws)}


def handler_themes(used_by_cids: list[int],
                   card_text: dict[int, tuple[str, str]],
                   *, min_share: float = 0.5) -> tuple[list[str], int]:
    """Themes for a handler, from the effect text of the cards that use it.

    Returns ``(themes, evidence)`` where *evidence* is the number of using cards
    that had usable effect text, and *themes* are those matched by at least
    *min_share* of that evidence.  Empty when there is too little signal.
    """
    tally: Counter[str] = Counter()
    evidence = 0
    seen: set[int] = set()
    for cid in used_by_cids:
        if cid in seen:
            continue
        seen.add(cid)
        entry = card_text.get(cid)
        if not entry or not entry[1].strip():
            continue
        evidence += 1
        for theme in text_themes(entry[1]):
            tally[theme] += 1
    if evidence == 0:
        return [], 0
    themes = sorted(t for t, n in tally.items() if n / evidence >= min_share)
    return themes, evidence
