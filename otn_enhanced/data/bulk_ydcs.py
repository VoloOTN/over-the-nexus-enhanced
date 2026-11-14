"""Bulk deck (``deck.pac``) composition changes. Migrated from
``finished_patches/ydc_decks.py``, which stays the oracle -- :data:`CHANGES`, the
:class:`YDC` records and the doTheThing/ydc_codec plumbing are reused from it unchanged, only
the ROM I/O is rewritten.

WHY THIS ONE NEEDED MIGRATING (not just a speed refactor)
-----------------------------------------------------------
The original module edits the ROM through the standalone CLI helpers ``extract_file`` /
``replace_file``, both of which call ``ndspy.rom.NintendoDSRom.fromFile`` on a **different
path** than the one it was given (``out + ".bak"``), and it finishes with
``os.remove(out); shutil.copy(out + ".bak", out)``.

That is transparent to the OLD chain (``apply_all_patches.py``), where every step's ``src``/
``out`` is a real file on disk and each step genuinely re-reads what the last one wrote. It is
NOT transparent to this build's ``Session`` (see ``session.py``): the fast build never writes
the work path to disk mid-build, and only intercepts real ROM I/O that touches that *exact*
path. ``out + ".bak"`` is a different path, so the original module reads a **stale on-disk
copy** (the one-time clean-ROM stub ``Session`` materialises only so
``bulk_card_props``'s raw ``open()`` calls don't crash), edits it, and writes it right
back to that same disconnected copy -- ``sess.rom``, the object ``Session.finalize`` actually
serialises to the output ROM, is never touched. The deck edits are computed and thrown away.
Worse, the final ``shutil.copy(out+'.bak', out)`` IS a same-path copy, so ``Session`` treats it
as a no-op ("the session ROM already holds this content") and the on-disk stub file is left
deleted (from the preceding ``os.remove(out)``) with nothing copied back.

This module does it the way ``bulk_card_pack`` (the sibling "None"-shape step immediately
before this one in ``steps.STEPS``, which the fast build has always applied correctly) does it:
load the ROM object through ``ndspy.rom.NintendoDSRom.fromFile(src)`` (which ``Session`` hooks
to hand back the live ``sess.rom`` when ``src`` is the work path), mutate ``rom.files[fid]`` in
place, and call ``rom.saveToFile(out)`` (which ``Session`` hooks to a no-op, correctly, because
the mutation already happened in place). No intermediate ``.bak`` file, no ``os.remove``. This
is also exactly what the old chain does when ``src``/``out`` are real distinct files, so
behaviour there is unchanged.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import ndspy.rom

from otn_enhanced.data.ydc_decks import CHANGES, YDC, _convert_deck_format_to_ydc_codec
from otn_enhanced.rom.identify_decks_from_pac import doTheThing
from otn_enhanced.rom.pac import build_modified_pac, parse_format_v1, parse_pac
from otn_enhanced.rom.ydc_codec import _entry_to_konami_id, encode_ydc_from_json

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_test.nds"

DECK_PAC_PATH = "Data_arc_pac/deck.pac"


def _clean(name: str) -> str:
    """Mirror pac.PACFile.get_clean_name() for name matching: printable only, AND no invalid filename
    characters -- without the second filter ':wcs084_formula.ydc' never matched and that deck was silently skipped."""
    return "".join(c for c in name if c.isprintable() and c not in '<>:"/\\|?*')


def new_deck_pac(rom) -> tuple[int, bytes, int]:
    """Compute the patched deck.pac for *rom* without writing it: (file id, bytes, decks changed).

    Raises on any bad deck, so build.py can call it as a preflight against the clean ROM.
    """
    fid = rom.filenames.idOf(DECK_PAC_PATH)
    deck_pac_data = bytes(rom.files[fid])

    # doTheThing() only knows how to read a real file off disk -- hand it a scratch copy.
    with tempfile.NamedTemporaryFile(suffix=".pac", delete=False) as tmp:
        tmp.write(deck_pac_data)
        tmp_path = tmp.name
    try:
        deck_data = doTheThing(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    for f, ydc in CHANGES.items():
        fn = ydc.file_name
        if not isinstance(ydc, YDC):
            raise ValueError(f"CHANGES entry for {fn} is not a YDC instance")
        if fn not in deck_data:
            raise ValueError(f"Deck file {fn} not found in deck.pac")
        deck_entry = deck_data[fn]
        deck_entry["main_deck_names"] = ydc.main
        deck_entry["extra_deck_names"] = ydc.extra
        deck_entry["main_deck_size"] = len(ydc.main)
        deck_entry["extra_deck_size"] = len(ydc.extra)

    archive = parse_pac(deck_pac_data, DECK_PAC_PATH)
    # deck_data is keyed by doTheThing()'s decode of the raw embedded name (control bytes and
    # all -- e.g. "Brave RD"'s name has a genuine leading \x1b in the ROM). archive.files'
    # get_clean_name() strips non-printables for display/matching. Bridge clean -> raw here so
    # a stray control byte in one deck's name doesn't silently drop it from replacements_by_index.
    raw_by_clean = {_clean(ydc.file_name): ydc.file_name for ydc in CHANGES.values()}
    replacements_by_index = {}
    for idx, pac_file in enumerate(archive.files):
        clean_name = pac_file.get_clean_name()
        raw_name = raw_by_clean.get(clean_name)
        if raw_name is not None:
            converted_deck = _convert_deck_format_to_ydc_codec(deck_data[raw_name])
            ydc_binary = encode_ydc_from_json(json.dumps(converted_deck))
            replacements_by_index[idx] = ydc_binary

    if not replacements_by_index:
        raise ValueError(
            "No decks in CHANGES matched deck.pac contents -- nothing to patch. "
            f"Expected one of {sorted(raw_by_clean)} in the archive."
        )

    return fid, build_modified_pac(deck_pac_data, DECK_PAC_PATH, replacements_by_index), len(replacements_by_index)


def main(src: str = SRC, out: str = OUT) -> None:
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    fid, pac, n = new_deck_pac(rom)
    rom.files[fid] = pac
    rom.saveToFile(out)
    print(f"bulk_ydcs: wrote {out} ({n} deck(s) changed)")


def _deck_cids(pac: bytes) -> dict[str, tuple[list[int], list[int]]]:
    """{deck file name: (main cids, extra cids)}, read straight from deck.pac.

    Compares cids, not names: doTheThing() names cards from the stock table, so a renamed donor
    (Wattkid for Wattcobra) never equals the rom-hack name CHANGES uses.
    """
    out = {}
    for f in parse_format_v1(pac, DECK_PAC_PATH).files:
        name = f.name.decode("utf-8", errors="ignore").rstrip("\x00").strip().rstrip("\x19").strip()
        d = pac[f.address:f.address + f.size]
        n = int.from_bytes(d[8:10], "little")
        main = [int.from_bytes(d[10 + 2 * i:12 + 2 * i], "little") for i in range(n)]
        at = 10 + 2 * n
        m = int.from_bytes(d[at:at + 2], "little")
        extra = [int.from_bytes(d[at + 2 + 2 * i:at + 4 + 2 * i], "little") for i in range(m)]
        out[name] = (main, extra)
    return out


def verify(out: str = OUT) -> bool:
    """Re-read deck.pac from *out* and confirm every changed deck matches CHANGES."""
    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    decks = _deck_cids(bytes(rom.files[rom.filenames.idOf(DECK_PAC_PATH)]))

    ok = True
    for f, ydc in CHANGES.items():
        entry = decks.get(ydc.file_name)
        if entry is None:
            print(f"[FAIL] {f} ({ydc.file_name}) missing from deck.pac")
            ok = False
            continue
        want = ([_entry_to_konami_id(e) for e in ydc.main], [_entry_to_konami_id(e) for e in ydc.extra])
        if entry != want:
            print(f"[FAIL] {f} ({ydc.file_name}) does not match CHANGES")
            ok = False
    if ok:
        print(f"[OK] all {len(CHANGES)} deck(s) match CHANGES")
    return ok


if __name__ == "__main__":
    main()
    print()
    verify()
