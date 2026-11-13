"""TEST HARNESS -- rewrite every CPU opponent deck to nothing but removal Spells.

*** THIS IS NOT A CARD PATCH AND MUST NEVER GO INTO apply_all_patches. ***
It exists to make one specific question cheap to answer in a duel: does a
protection effect actually stop a NON-TARGETING destruction?  Sitting through
40 turns hoping the CPU draws its single Dark Hole is not a test; a deck that is
nothing but Dark Hole and Smashing Ground is.

WHY THESE TWO CARDS (text read from scratch/ygoprodeck_cache.json, not recall):

    Dark Hole               Normal Spell -- "Destroy all monsters on the field."
    Offerings to the Doomed Quick-Play   -- "Target 1 face-up monster on the field;
                            destroy that target, also skip your next Draw Phase."

They are a MATCHED PAIR, one on each side of the distinction a protection effect
has to get right:

  * Dark Hole destroys WITHOUT targeting, and en masse.  That is the question
    safe_zone's PART D could not answer at all, and the one clause 2 was
    built to answer -- see notes/azure-eyes-clause2-findings.md.  It also proves
    whether the OTHER Dragons on your board are covered, not just the summoned one.
  * Offerings to the Doomed TARGETS.  Without it the harness could not produce
    oracle 1 (an opponent's targeting effect refused) at all.  Being Quick-Play,
    the CPU can also fire it from a Set card during YOUR turn, which exercises the
    protection at a different point in the turn for free.

Smashing Ground ("Destroy the 1 face-up monster your opponent controls that has
the highest DEF") was the original second card and is still a good one: it is
non-targeting AND it picks the highest DEF you control, so with Azure-Eyes at DEF
3000 it aims itself at the card under test.  Swap it back into DECK_CARDS if you
want two flavours of non-targeting removal instead of one of each.

WHAT IT DOES, AND WHY IT IS THE MINIMAL EDIT
Each .ydc inside Data_arc_pac/deck.pac is
``{8 B header}{u16 main_size}{main_size x u16 konami id}{u16 extra_size}{...}``.
This patch overwrites ONLY the main-deck id array, in place, keeping the deck's
existing main_size and leaving the Extra Deck untouched.  Every inner file
therefore keeps its exact byte length, so the PAC needs no repack and no offset
in the archive moves -- the whole change is `main_size` halfwords per deck.
Leaving the Extra Deck alone costs nothing: with no monsters in the Main Deck the
CPU can never Synchro Summon, so those cards are inert.

*** THE BANLIST DOES NOT NEED TOUCHING, AND THAT WAS MEASURED, NOT ASSUMED. ***
Dark Hole is Forbidden on five of the game's six selectable limit lists and
Limited on the sixth, so "20 copies" looks illegal.  It is not checked: decoding
all six limit*.bin lists out of bin.pac and every shipped deck out of deck.pac,
**39 shipped deck/card pairs exceed the allowance even on the newest list**
(limit201009) -- sd05_soldier.ydc ships cards that are outright Forbidden -- and
wcs053_sinparadox.ydc ships Dark Hole itself while five of the six lists forbid
it.  Konami would not ship decks the loader rejects, so stored decks are simply
not validated.  ``python -m otn_enhanced.system.testbench_decks
--audit`` re-runs that scan against the ROM you point it at.

WHAT IS DELIBERATELY LEFT ALONE
The 21 ``sd*`` shop structure decks, the player's starting deck
``rpg001_0_syoki.ydc`` and ``default_jf.ydc``.  Those are the decks the game hands
the PLAYER; turning them into Dark Hole spam would take away the board you need in
order to test anything.  Everything else -- 281 of the 305 decks, every story,
World Championship and tag opponent -- becomes the removal deck.

WHAT IT DOES NOT DO
It only ever arms the CPU.  Oracle 3 -- "your OWN targeting effect on your own
Dragon is also refused" -- needs a targeting effect in YOUR deck; the starting
player deck's removal (Fissure, Hammer Shot) does not target.
Change DECK_CARDS below for a different mix: any name in
ydc_codec.CARD_NAME_TO_KONAMI_ID works, and the deck is filled by cycling through
the list, so a 3-tuple gives a 3-way split.

USAGE
    uv run python -m otn_enhanced.system.testbench_decks \\
        --src data/over_the_nexus/working/rom_azure.nds \\
        --out data/over_the_nexus/working/rom_azure_test.nds
or, together with the card itself, ``uv run python _build_azure_testbench.py``.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import struct
import sys

import ndspy.rom

from otn_enhanced.rom.pac import parse_format_v1, parse_pac
from otn_enhanced.rom.ydc_codec import card_name_to_konami_id

SRC = "data/over_the_nexus/working/rom_azure.nds"
OUT = "data/over_the_nexus/working/rom_azure_test.nds"

DECK_PAC = "Data_arc_pac/deck.pac"
BIN_PAC = "Data_arc_pac/bin.pac"

# The cards every opponent deck is filled with, cycled in order. One destroys
# WITHOUT targeting (Dark Hole), one WITH (Offerings to the Doomed) -- that pair is
# the whole point. "Smashing Ground" is the other good non-targeting option: it
# picks the highest DEF you control, i.e. Azure-Eyes at DEF 3000.
DECK_CARDS = ("Dark Hole", "Offerings to the Doomed")

# Decks the PLAYER receives. Left untouched so you still have a board to test with.
KEEP = frozenset({
    "rpg001_0_syoki.ydc",   # the deck a new game hands you ("syoki" = initial)
    "default_jf.ydc",
} | {f"sd{n:02d}_{name}.ydc" for n, name in (
    (1, "dragon"), (2, "undead"), (3, "fire"), (4, "umi"), (5, "soldier"),
    (6, "magician"), (7, "ganseki"), (8, "wind"), (9, "dino"), (10, "machine"),
    (11, "angel"), (12, "dark"), (13, "dragon"), (14, "mikado"), (15, "undead"),
    (16, "magician"), (17, "soldier"), (18, "machine"), (19, "dragunity"),
    (20, "angel"),
)} | {"sd_starter10.ydc"})

# A .ydc name inside deck.pac, as the PAC name field decodes it.
_NAME_RE = re.compile(r"(rpg|wcs|wrd|rtlr|rtl|qrtlr|pg|sd|default)[0-9a-z_]*\.ydc")

# Layout of a .ydc: 8-byte header, then the main deck, then the extra deck.
HDR = 8
MAIN_SIZE_OFF = HDR         # u16
MAIN_IDS_OFF = HDR + 2      # main_size x u16


def _clean(raw: bytes) -> str:
    """Decode a PAC name field the way identify_decks_from_pac does."""
    return raw.decode("utf-8", errors="ignore").rstrip("\x00").strip().rstrip("\x19").strip()


def _norm(name: str) -> str:
    """Normalise a decoded .ydc name.

    11 of the 305 entries carry one stray leading byte in the PAC name field
    ('\\x1brpg103_7_brave_rd.ydc', '4rpg077_8_crow.ydc', 'Pwcs001_moja.ydc', ...).
    Matching the known filename shape and dropping a single junk prefix character
    recovers the real name; anything that still does not match is returned as-is
    and is simply never in KEEP, so it gets the removal deck.
    """
    for cand in (name, name[1:], name.lower(), name[1:].lower()):
        if _NAME_RE.fullmatch(cand):
            return cand
    return name


def _konami_ids() -> list[int]:
    ids = []
    for name in DECK_CARDS:
        cid = card_name_to_konami_id(name)
        if cid is None:
            raise KeyError(
                f"{name!r} is not in ydc_codec.CARD_NAME_TO_KONAMI_ID -- pick a name "
                f"that table knows, or pass the konami id as an int")
        ids.append(cid)
    return ids


def _decks(pac_bytes: bytes) -> list[tuple[str, int, int, int]]:
    """Return (normalised name, file offset, main_size, extra_size) per .ydc."""
    archive = parse_format_v1(pac_bytes, DECK_PAC)
    out = []
    for f in archive.files:
        name = _norm(_clean(f.name))
        blob = pac_bytes[f.address:f.address + f.size]
        main_size = struct.unpack_from("<H", blob, MAIN_SIZE_OFF)[0]
        extra_off = MAIN_IDS_OFF + main_size * 2
        extra_size = struct.unpack_from("<H", blob, extra_off)[0]
        assert extra_off + 2 + extra_size * 2 <= f.size, (
            f"{name}: main {main_size} + extra {extra_size} overruns its {f.size}B entry")
        out.append((name, f.address, main_size, extra_size))
    return out


def _expected_main(main_size: int, ids: list[int]) -> list[int]:
    """The deck this patch writes: *ids* cycled to fill main_size slots."""
    return [ids[i % len(ids)] for i in range(main_size)]


# ===========================================================================
# the patch
# ===========================================================================
def main(src: str = SRC, out: str = OUT) -> None:
    ids = _konami_ids()
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    fid = rom.filenames.idOf(DECK_PAC)
    if fid is None:
        raise FileNotFoundError(f"{DECK_PAC} is not in {src}")
    original = rom.files[fid]
    data = bytearray(original)

    decks = _decks(bytes(original))
    changed = kept = 0
    sizes = collections.Counter()
    for name, addr, main_size, _extra in decks:
        if name in KEEP:
            kept += 1
            continue
        want = _expected_main(main_size, ids)
        struct.pack_into(f"<{main_size}H", data, addr + MAIN_IDS_OFF, *want)
        sizes[main_size] += 1
        changed += 1

    assert len(data) == len(original), (
        f"deck.pac changed size {len(original)} -> {len(data)}; the edit must be "
        f"in place so no PAC offset moves")
    rom.files[fid] = bytes(data)
    rom.saveToFile(out)

    print(f"testbench decks: rewrote {changed} opponent decks, left {kept} player decks alone")
    for size, n_decks in sorted(sizes.items()):
        split = ", ".join(
            f"{DECK_CARDS[i]} x{sum(1 for k in range(size) if k % len(ids) == i)}"
            for i in range(len(ids)))
        print(f"  {n_decks:3d} deck(s) of {size} cards -> {split}")
    print(f"  Extra Decks untouched; deck.pac byte length unchanged ({len(data)} B)")
    print(f"wrote {out}")


# ===========================================================================
# verification
# ===========================================================================
def verify(out: str = OUT, src: str = SRC) -> bool:
    ids = _konami_ids()
    ok = True

    def check(cond: bool, msg: str) -> None:
        nonlocal ok
        print(f"  {'OK  ' if cond else 'FAIL'} {msg}")
        ok = ok and bool(cond)

    print("verify testbench_decks:")
    rom_out = ndspy.rom.NintendoDSRom.fromFile(out)
    rom_src = ndspy.rom.NintendoDSRom.fromFile(src)
    after = rom_out.files[rom_out.filenames.idOf(DECK_PAC)]
    before = rom_src.files[rom_src.filenames.idOf(DECK_PAC)]

    check(len(after) == len(before),
          f"deck.pac is still {len(before)} B (in-place edit, no PAC repack)")

    decks_a = _decks(after)
    decks_b = _decks(before)
    check([(n, a, m) for n, a, m, _ in decks_a] == [(n, a, m) for n, a, m, _ in decks_b],
          f"all {len(decks_a)} .ydc entries keep their name, offset and main size")

    bad_main, bad_extra, bad_kept = [], [], []
    changed = kept = 0
    for (name, addr, main_size, extra_size) in decks_a:
        blob_a = after[addr:addr + MAIN_IDS_OFF + main_size * 2 + 2 + extra_size * 2]
        blob_b = before[addr:addr + MAIN_IDS_OFF + main_size * 2 + 2 + extra_size * 2]
        if name in KEEP:
            kept += 1
            if blob_a != blob_b:
                bad_kept.append(name)
            continue
        changed += 1
        got = list(struct.unpack_from(f"<{main_size}H", after, addr + MAIN_IDS_OFF))
        if got != _expected_main(main_size, ids):
            bad_main.append(name)
        extra_off = addr + MAIN_IDS_OFF + main_size * 2
        n = 2 + extra_size * 2
        if after[extra_off:extra_off + n] != before[extra_off:extra_off + n]:
            bad_extra.append(name)

    check(not bad_main,
          f"all {changed} opponent decks hold exactly {' / '.join(DECK_CARDS)}"
          + (f" -- WRONG in {bad_main[:5]}" if bad_main else ""))
    check(not bad_extra,
          f"all {changed} rewritten Extra Decks are byte-identical to the source"
          + (f" -- CHANGED in {bad_extra[:5]}" if bad_extra else ""))
    check(not bad_kept,
          f"all {kept} player decks ({', '.join(sorted(KEEP))[:60]}...) are untouched"
          + (f" -- CHANGED in {bad_kept}" if bad_kept else ""))
    check(kept == len(KEEP),
          f"every name in KEEP was found in deck.pac ({kept} of {len(KEEP)})")

    # Nothing outside deck.pac may have moved: this patch touches one file.
    others = [p for p in (BIN_PAC, "Data_arc_pac/bin2.pac")
              if rom_out.filenames.idOf(p) is not None
              and rom_out.files[rom_out.filenames.idOf(p)]
              != rom_src.files[rom_src.filenames.idOf(p)]]
    check(not others, "bin.pac / bin2.pac untouched (the banlist is NOT edited)"
          + (f" -- CHANGED: {others}" if others else ""))

    print(f"verify: {'PASS' if ok else 'FAIL'}")
    return ok


# ===========================================================================
# the audit that decided the banlist does not matter
# ===========================================================================
def audit_banlist(src: str = SRC) -> None:
    """Show that stored decks are NOT validated against the limit lists.

    For every limit*.bin in bin.pac, count the (deck, card) pairs in deck.pac
    that already exceed that list's allowance. A non-zero count on the newest
    list means the loader cannot be enforcing it.
    """
    from otn_enhanced.rom.limit_codec import decode_limit

    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    bin_bytes = rom.files[rom.filenames.idOf(BIN_PAC)]
    deck_bytes = rom.files[rom.filenames.idOf(DECK_PAC)]

    lists = {}
    for f in parse_pac(bin_bytes, BIN_PAC).files:
        name = f.get_clean_name()
        if not name.lower().startswith("limit"):
            continue
        text, _ = decode_limit(bin_bytes[f.address:f.address + f.size])
        j = json.loads(text)
        allow = {}
        for group, cap in (("Forbidden", 0), ("Limited", 1), ("Semi-Limited", 2)):
            for kid in j[group]:
                allow[kid] = cap
        lists[name] = allow

    archive = parse_format_v1(deck_bytes, DECK_PAC)
    print(f"banlist audit of {src}:")
    for list_name, allow in sorted(lists.items()):
        violations = []
        for f in archive.files:
            blob = deck_bytes[f.address:f.address + f.size]
            main_size = struct.unpack_from("<H", blob, MAIN_SIZE_OFF)[0]
            cards = list(struct.unpack_from(f"<{main_size}H", blob, MAIN_IDS_OFF))
            extra_off = MAIN_IDS_OFF + main_size * 2
            extra_size = struct.unpack_from("<H", blob, extra_off)[0]
            cards += list(struct.unpack_from(f"<{extra_size}H", blob, extra_off + 2))
            for kid, n in collections.Counter(cards).items():
                if n > allow.get(kid, 3):
                    violations.append((_norm(_clean(f.name)), kid, n, allow.get(kid, 3)))
        print(f"  {list_name}: {len(violations):4d} shipped (deck, card) pairs over the "
              f"allowance" + (f"  e.g. {violations[0]}" if violations else ""))
    print("  A non-zero count means stored decks are NOT validated -- so filling a deck")
    print("  with 20 copies of a Forbidden card is safe.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--audit", action="store_true",
                    help="only run the banlist audit against --src and exit")
    a = ap.parse_args()
    if a.audit:
        audit_banlist(a.src)
        raise SystemExit(0)
    main(src=a.src, out=a.out)
    print()
    raise SystemExit(0 if verify(out=a.out, src=a.src) else 1)
