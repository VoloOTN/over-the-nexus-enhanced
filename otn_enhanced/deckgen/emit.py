"""Turn a generated deck into something the ROM tooling accepts.

Two output shapes:

* :func:`to_changes_entry` — the ``{"file_name", "main", "extra"}`` form that
  ``patch_bulk_ydcs.CHANGES`` consumes, using the **ROM's** card names so
  ``CARD_NAME_TO_KONAMI_ID`` resolves them.
* :func:`to_ydc_json` — a full ``ydc_codec`` payload, ready to encode.

``to_ydc_json`` deliberately does *not* reuse
``patch_bulk_ydcs._convert_deck_format_to_ydc_codec``: that helper hardcodes
``side_size: 0`` and drops ``trailing_b64``, which would silently delete the
15-card side deck from the 32 stock decks that have one.  When replacing an
existing deck, pass its decoded payload as *template* and the side deck and
trailing bytes are carried through untouched.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

from otn_enhanced.deckgen.model import Card
from otn_enhanced.deckgen.search import GeneratedDeck

#: A ydc header that every stock deck shares the first four bytes of.  Used only
#: when creating a deck from nothing rather than replacing an existing one.
DEFAULT_HEADER_B64 = base64.b64encode(bytes([0x01, 0xCC, 0xCC, 0xCC, 0x80, 0x8F, 0x99, 0x47])).decode()


@dataclass
class EmitError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def _expand(counts: dict[int, int], by_cid: dict[int, Card]) -> list[int]:
    """Flatten ``{cid: copies}`` into a sorted cid list, as the ROM stores it."""
    out: list[int] = []
    for cid, n in counts.items():
        out.extend([cid] * n)
    return sorted(out)


def deck_cids(deck: GeneratedDeck, by_cid: dict[int, Card]) -> tuple[list[int], list[int]]:
    main, extra = _expand(deck.main, by_cid), _expand(deck.extra, by_cid)
    # Backstop for the one corruption the ROM will not survive: a Fusion or
    # Synchro written into the main deck.  DeckState.add routes by is_extra and
    # constraints.violations checks it, but this is the single choke point every
    # emitted deck passes through, so enforce it here too rather than trusting
    # whichever path produced the state.
    strays = sorted({by_cid[c].name for c in main if c in by_cid and by_cid[c].is_extra})
    if strays:
        raise EmitError(f"Extra Deck cards found in the main deck: {strays}")
    return main, extra


def to_changes_entry(
    deck: GeneratedDeck, by_cid: dict[int, Card], target_ydc: str
) -> dict[str, object]:
    """Build a ``patch_bulk_ydcs.CHANGES``-shaped entry.

    Names are the ROM's own spelling, not the modern one, because that is what
    ``CARD_NAME_TO_KONAMI_ID`` is keyed on.
    """
    from otn_enhanced.rom.konami_id_to_card_name import card_name_to_konami_id

    main_cids, extra_cids = deck_cids(deck, by_cid)
    main = [by_cid[c].name for c in main_cids]
    extra = [by_cid[c].name for c in extra_cids]

    # Emit each card as {"konami_id": cid, "card_name": name}.  The deckgen `cid`
    # IS the Konami ID — verified: all 4,305 pool cards are keys of
    # KONAMI_ID_TO_CARD_NAME — so the id is exact and the name rides along purely
    # so the generated JSON stays readable.  ydc_codec._entry_to_konami_id
    # prefers the id, and patch_bulk_ydcs.YDC.validate accepts it.
    #
    # A pure-name entry cannot express every card, and worse, can name the WRONG
    # one; the check below stays as a diagnostic of that.
    #
    # `CARD_NAME_TO_KONAMI_ID` now comes from the ROM's card_name_e.bin, so names
    # are right, but a duplicated name (alt arts, tokens) still resolves to its
    # FIRST record only — the second Blue-Eyes printing is unreachable by name.
    bad: list[str] = []
    for cid in list(main_cids) + list(extra_cids):
        name = by_cid[cid].name
        got = card_name_to_konami_id(name)
        if got is None:
            bad.append(f"{name!r} (0x{cid:04X}): name not in the id table")
        elif got != cid:
            other = by_cid.get(got)
            bad.append(
                f"{name!r} (0x{cid:04X}): the name resolves to 0x{got:04X}"
                + (f" = {other.name!r}" if other else "")
            )
    # No longer fatal: the entry carries the id, so the deck patches correctly
    # whatever the name table says.  Recorded on the entry so the damage stays
    # visible rather than being silently papered over.
    name_table_broken = sorted(bad)
    if not 40 <= len(main) <= 60:
        raise EmitError(f"main deck has {len(main)} cards; YDC.validate requires 40-60")
    if len(extra) > 15:
        raise EmitError(f"extra deck has {len(extra)} cards; YDC.validate requires <=15")

    entry = {
        "file_name": target_ydc,
        "main": [{"konami_id": c, "card_name": by_cid[c].name} for c in main_cids],
        "extra": [{"konami_id": c, "card_name": by_cid[c].name} for c in extra_cids],
    }
    if name_table_broken:
        entry["name_table_warnings"] = name_table_broken
    return entry


def to_ydc_json(
    deck: GeneratedDeck, by_cid: dict[int, Card], template: dict | None = None
) -> dict:
    """Build a ``ydc_codec`` payload, preserving *template*'s side deck if given."""
    main_cids, extra_cids = deck_cids(deck, by_cid)
    tmpl = template or {}
    return {
        "format": "ydc.v1",
        "header_b64": tmpl.get("header_b64", DEFAULT_HEADER_B64),
        "main_size": len(main_cids),
        "main_deck": main_cids,
        "extra_size": len(extra_cids),
        "extra_deck": extra_cids,
        # Carried straight through — dropping these is how side decks get lost.
        "side_size": tmpl.get("side_size", 0),
        "side_deck": list(tmpl.get("side_deck", [])),
        "trailing_b64": tmpl.get("trailing_b64", ""),
    }


def round_trip_ok(payload: dict) -> tuple[bool, str]:
    """Encode the payload and confirm the bytes read back as the same cids.

    Compared at the **cid** level, not against ``decode_ydc``'s output: that
    function converts ids to names via the name table that has a few wrong
    entries, so a name-level comparison would fail on correct bytes.
    """
    from otn_enhanced.deckgen.validate.corpus import read_ydc_cids
    from otn_enhanced.rom.ydc_codec import decode_ydc, encode_ydc

    try:
        blob = encode_ydc(payload)
    except Exception as exc:  # noqa: BLE001 — surface any codec complaint verbatim
        return False, f"encode failed: {exc}"

    main, extra, side = read_ydc_cids(blob)
    for label, got, want in (
        ("main_deck", main, payload["main_deck"]),
        ("extra_deck", extra, payload["extra_deck"]),
        ("side_size", len(side), payload["side_size"]),
    ):
        expect = want if label == "side_size" else list(want)
        actual = got if label == "side_size" else list(got)
        if actual != expect:
            return False, f"{label} changed: {expect!r} -> {actual!r}"
    # Re-encode the decoded payload, but compare at the **cid** level, exactly as
    # above.  `decode_ydc` turns ids into names via the table with 16 wrong
    # entries, so a byte comparison here re-introduced the very name path this
    # function's docstring says it avoids: a deck holding Dupe Frog (0x1E6C)
    # decoded to "Des Frog", re-encoded to 0x2269 (Ronintoadin) and reported
    # "re-encoding produced different bytes" on bytes that were perfectly correct.
    again, again_x, _ = read_ydc_cids(encode_ydc(decode_ydc(blob)))
    lossy = sorted(set(main + extra) - set(again + again_x))
    if lossy:
        # NOT a failure of these bytes.  The cid comparison above already proved
        # the encoded deck is exactly right, and that is what gets patched.  This
        # leg tests `decode_ydc` -> `encode_ydc` symmetry, which routes through
        # the name table with 16 wrong entries: Dupe Frog (0x1E6C) decodes to
        # "Des Frog" and re-encodes to 0x2269 (Ronintoadin).  Reported so the
        # codec limitation is visible without condemning a correct deck.
        return True, ("ok (bytes correct; note decode->re-encode is lossy for "
                      + ", ".join(f"0x{c:04X}" for c in lossy) + " — name table)")
    return True, "ok"


def write_changes_json(entry: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(entry, fh, indent=2, ensure_ascii=False)
