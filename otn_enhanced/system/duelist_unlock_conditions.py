"""CPU-duelist unlock conditions as an editable table, in the spirit of
``pack_unlock_conditions.py`` but for the duelist-roster condition records
found in overlay 18 (not the booster-pack arms in overlay 1 -- a completely
different subsystem; see notes/cpu-duelist-unlock-findings.md for the full
reverse-engineering write-up).

Edit :data:`CHANGES` below and run::

    python -m otn_enhanced.system.duelist_unlock_conditions

Only the duelist ids present in :data:`CHANGES` are touched. Every edit here
is same-size (every field is a fixed 4-byte slot in a fixed-size record), so
this is a pure in-place overlay patch -- no repack, no resize, no risk of
displacing anything else in the overlay.

Condition types
----------------
* ``BeatDuelist(ref_id, count)`` -- "beat duelist *ref_id* *count* times".
* ``StatThreshold(stat_type, value)`` -- "have counter *stat_type* >=
  *value*". ``stat_type`` is one of the :class:`Stat` constants.
* ``RawValue(value)`` -- a single un-typed threshold word. Covers the
  5 main-roster + 3 turbo "misc stat" duelists, whose per-id semantics
  differ (see :data:`_REGISTRY` comments for the unit of each -- seconds,
  a raw count, or an IEEE-754 float for the one percentage-based one).
* ``SummonCard(card_ref)`` -- "summon (or win with) a specific card".
  ``card_ref`` is a small index (~245-263 seen so far) into a card
  reference table whose exact resolution to real card ids was NOT
  cracked this session -- editable, but you need to already know (or
  find, e.g. by trial) which ``card_ref`` value names which card.
* ``SwapChapter(other_id)`` -- for the "clear chapter N" / "from the
  start" groups, which are plain id-*membership* lists, not per-id
  thresholds: the only safe edit is exchanging which duelist occupies
  which group's slot with another duelist (same-size, no list
  grows/shrinks). Apply ``CHANGES[X] = SwapChapter(Y)`` to swap X and Y's
  group membership; do not also add the reverse entry for Y (detected and
  rejected -- see :func:`apply_conditions`).
* ``BeatDuelistPair(ref_pair, count)`` / ``SummonCardPair(card_ref)`` --
  the tag-turbo team equivalents of ``BeatDuelist``/``SummonCard``, keyed
  by the *first* id of the two-duelist team (e.g. ``0xF3`` for the
  ``0xF3,0xF4`` team).

Not covered
-----------
Turbo's single-member "clear chapter 4/5/story" duelists (``0xDC-0xDE``)
and the 7th turbo "from the start" member (``0xDB``, Mefist) are never
found sitting in an editable membership list -- only as *reference targets*
inside other records. Their own gating mechanism is still unlocated, so
they are not in :data:`_REGISTRY` at all.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import ndspy.rom

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_duelist_conditions.nds"

OVERLAY_ID = 18
OV18_BASE = 0x0214C840


class Stat:
    """Known ``stat_type`` values for :class:`StatThreshold` (partial enum)."""
    TOTAL_SUMMONS = 0x11
    TOTAL_SPECIAL_SUMMONS = 0x13
    TOTAL_SYNCHRO_SUMMONS = 0x16
    TOTAL_SPEED_SPELLS = 0x1E


@dataclass
class BeatDuelist:
    ref_id: int
    count: int = 3


@dataclass
class StatThreshold:
    stat_type: int
    value: int


@dataclass
class RawValue:
    value: int


@dataclass
class SummonCard:
    card_ref: int


@dataclass
class SwapChapter:
    other_id: int


@dataclass
class BeatDuelistPair:
    ref_pair: tuple[int, int]
    count: int = 3


@dataclass
class SummonCardPair:
    card_ref: int


# ---------------------------------------------------------------------------
# Registry: duelist id -> (record address, expected kind).
# Every address was read back from the live ROM and hand-verified against
# the user's real in-game unlock conditions (notes/cpu-duelist-unlock-findings.md).
# Record layouts (word0 is always this duelist's own id, sanity-checked,
# never written):
#   BeatDuelist/StatThreshold : {id, ref_id/stat_type, count/value}   (12 B)
#   RawValue                  : {id, value}                          (8 B)
#   SummonCard                : {id, card_ref}                       (8 B)
#   BeatDuelistPair            : {pair(u16,u16), ref_pair(u16,u16), count} (12 B)
#   SummonCardPair              : {pair(u16,u16), card_ref}           (8 B)
# ---------------------------------------------------------------------------
_REGISTRY: dict[int, tuple[int, type]] = {
    # -- main roster: beat-a-duelist-3-times (0x95-0x9D) ---------------------
    0x95: (0x0215D348, BeatDuelist),
    0x96: (0x0215D354, BeatDuelist),
    0x97: (0x0215D360, BeatDuelist),
    0x98: (0x0215D36C, BeatDuelist),
    0x99: (0x0215D378, BeatDuelist),
    0x9A: (0x0215D384, BeatDuelist),
    0x9B: (0x0215D390, BeatDuelist),
    0x9C: (0x0215D39C, BeatDuelist),
    0x9D: (0x0215D3A8, BeatDuelist),
    # -- main roster: misc stat thresholds (0x9E-0xA2) -----------------------
    0x9E: (0x0215CFB0, RawValue),  # seconds of playtime (180000 = 50h)
    0x9F: (0x0215CFB8, RawValue),  # seconds of playtime (360000 = 100h)
    0xA0: (0x0215CF38, RawValue),  # IEEE-754 float fraction (0.5 = 50%)
    0xA1: (0x0215CF48, RawValue),  # raw count (consecutive wins)
    0xA2: (0x0215CF18, RawValue),  # raw count (max damage in one hit)
    # -- main roster: summon/win-with-card group (0xA3-0xAC minus 0xA7) ------
    0xA3: (0x0215D294, SummonCard),
    0xA4: (0x0215D2AC, SummonCard),
    0xA5: (0x0215D2B4, SummonCard),
    0xA6: (0x0215D29C, SummonCard),
    0xA7: (0x0215CF68, StatThreshold),  # Dragunity Arma Leyvaten: raw counter, not a card
    0xA8: (0x0215D2BC, SummonCard),
    0xA9: (0x0215D2C4, SummonCard),
    0xAA: (0x0215D2A4, SummonCard),
    0xAB: (0x0215D2CC, SummonCard),
    0xAC: (0x0215D2D4, SummonCard),
    # -- turbo roster: beat-a-duelist-3-times (0xDF-0xE2) ---------------------
    0xDF: (0x0215D218, BeatDuelist),
    0xE0: (0x0215D224, BeatDuelist),
    0xE1: (0x0215D230, BeatDuelist),
    0xE2: (0x0215D23C, BeatDuelist),
    # -- turbo roster: stat thresholds (0xE3-0xE5) ----------------------------
    0xE3: (0x0215D1B0, StatThreshold),
    0xE4: (0x0215D1BC, StatThreshold),
    0xE5: (0x0215D1C8, StatThreshold),
    # -- turbo roster: misc (0xE6) / summon (0xE7-0xE8) -----------------------
    0xE6: (0x0215D0A4, RawValue),   # speed-counter-related raw value (120; unit unconfirmed)
    0xE7: (0x0215D0AC, SummonCard),
    0xE8: (0x0215D0B4, SummonCard),
    # -- tag-turbo: beat-a-team-3-times (0xF3/0xF5/0xF7, keyed by first id) ---
    0xF3: (0x0215D150, BeatDuelistPair),
    0xF5: (0x0215D15C, BeatDuelistPair),
    0xF7: (0x0215D168, BeatDuelistPair),
    # -- tag-turbo: summon-card (0xF9/0xFB, keyed by first id) ----------------
    0xF9: (0x0215CF80, SummonCardPair),
    0xFB: (0x0215CF88, SummonCardPair),
}

# Chapter/story-clear membership lists: group name -> (list base address,
# member ids in slot order). "From the Start" is itself just a group like
# any other -- swapping a duelist into it makes them unconditional.
_GROUPS: dict[str, tuple[int, list[int]]] = {
    "main_from_start": (0x0215D034, [0x71, 0x72, 0x73, 0x74, 0x75, 0x76]),
    "main_chapter_2": (0x0215D018, [0x77, 0x78, 0x79, 0x7A, 0x7B, 0x7C]),
    "main_chapter_3": (0x0215D088, [0x7D, 0x7E, 0x7F, 0x80, 0x81, 0x82]),
    "main_chapter_4": (0x0215CFE0, [0x83, 0x84, 0x85, 0x86, 0x87, 0x88]),
    "main_chapter_5": (0x0215D050, [0x89, 0x8A, 0x8B, 0x8C, 0x8D, 0x8E]),
    "main_story_mode": (0x0215CFFC, [0x8F, 0x90, 0x91, 0x92, 0x93, 0x94]),
    "turbo_from_start": (0x0215D06C, [0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA]),
}

# duelist id -> exact slot address, derived from _GROUPS.
_SLOTS: dict[int, int] = {
    did: base + i * 4
    for base, ids in _GROUPS.values()
    for i, did in enumerate(ids)
}

CHANGES: dict[int, object] = {
    # In-game confirmed by the user: zeroing every threshold-based
    # condition's count/value (26 ids -- every BeatDuelist/StatThreshold/
    # RawValue/BeatDuelistPair id, ref_id/stat_type left untouched) makes
    # those main-roster duelists selectable from a fresh save with no story
    # progress needed. Turbo/tag-turbo ids use the same record shapes but
    # weren't directly observed (their game modes were still locked on the
    # test save). See notes/cpu-duelist-unlock-findings.md for the exact
    # wording. All commented out below -- uncomment what you actually want
    # shipped.
    # 0x95: BeatDuelist(ref_id=0x76, count=0),          # Master Hyperion: beat Tiki Curse 0 times (always true)
    # 0xA7: StatThreshold(Stat.TOTAL_SUMMONS, 0),       # Dragunity Arma Leyvaten: 0 summons instead of 666
    # 0x9E: RawValue(0),                                # Evil Hero Dark Gaia: 0 seconds instead of 50h
    # 0x71: SwapChapter(0x77),                          # swap Moja (from-start) with Tender of the Laval (chapter 2)
    # 0xF3: BeatDuelistPair(ref_pair=(0xEF, 0xF0), count=1),  # tag-turbo team: beat Food Chain Friends once instead of Sonic Sprint 3x
}


def _load_ov18(rom: ndspy.rom.NintendoDSRom):
    ov = rom.loadArm9Overlays([OVERLAY_ID])[OVERLAY_ID]
    if ov.ramAddress != OV18_BASE:
        raise AssertionError(
            f"overlay {OVERLAY_ID} loads at {ov.ramAddress:#010x}, expected {OV18_BASE:#010x} "
            "-- this is not the EU (BYYP) ROM these addresses were derived from")
    return ov, bytearray(ov.data)


def _save_ov18(rom: ndspy.rom.NintendoDSRom, ov, data: bytearray, out: str | Path) -> None:
    ov.data = bytes(data)
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed
    tbl = rom.arm9OverlayTable
    e = OVERLAY_ID * 32
    flags = struct.unpack_from("<I", tbl, e + 0x1C)[0] >> 24
    struct.pack_into("<I", tbl, e + 0x1C, (flags << 24) | (len(compressed) & 0xFFFFFF))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rom.saveToFile(str(out))


def _pack_pair(a: int, b: int) -> int:
    return (a & 0xFFFF) | ((b & 0xFFFF) << 16)


def _unpack_pair(w: int) -> tuple[int, int]:
    return w & 0xFFFF, (w >> 16) & 0xFFFF


def apply_conditions(changes: dict[int, object], *, src: str | Path = SRC, out: str | Path = OUT) -> None:
    if not changes:
        if str(src) != str(out):
            import shutil
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(src), str(out))
        print("  CHANGES is empty -- uncomment a duelist id in CHANGES to edit it")
        return

    rom = ndspy.rom.NintendoDSRom.fromFile(str(src))
    ov, data = _load_ov18(rom)

    swap_pairs_done: set[frozenset[int]] = set()

    for duelist_id, cond in changes.items():
        if isinstance(cond, SwapChapter):
            if duelist_id not in _SLOTS:
                raise ValueError(f"id {duelist_id:#x} has no known group-membership slot")
            if cond.other_id not in _SLOTS:
                raise ValueError(f"id {cond.other_id:#x} has no known group-membership slot")
            key = frozenset((duelist_id, cond.other_id))
            if key in swap_pairs_done:
                continue
            if changes.get(cond.other_id) == SwapChapter(duelist_id):
                raise ValueError(
                    f"both id {duelist_id:#x} and id {cond.other_id:#x} specify SwapChapter "
                    f"pointing at each other -- that double-swaps back to stock. Specify only one side.")
            a_off = _SLOTS[duelist_id] - OV18_BASE
            b_off = _SLOTS[cond.other_id] - OV18_BASE
            a_val = struct.unpack_from("<I", data, a_off)[0]
            b_val = struct.unpack_from("<I", data, b_off)[0]
            if a_val != duelist_id or b_val != cond.other_id:
                raise ValueError(
                    f"slot sanity check failed for {duelist_id:#x}/{cond.other_id:#x} -- "
                    f"registry address is stale, stop and re-verify")
            struct.pack_into("<I", data, a_off, cond.other_id)
            struct.pack_into("<I", data, b_off, duelist_id)
            swap_pairs_done.add(key)
            print(f"  swapped group membership: id {duelist_id:#x} <-> id {cond.other_id:#x}")
            continue

        if duelist_id not in _REGISTRY:
            raise ValueError(
                f"id {duelist_id:#x} has no known condition record -- see this module's "
                f"docstring for what's editable")
        addr, kind = _REGISTRY[duelist_id]
        if type(cond) is not kind:
            raise ValueError(f"id {duelist_id:#x} takes a {kind.__name__}, got {type(cond).__name__}")
        off = addr - OV18_BASE

        if kind in (BeatDuelist, StatThreshold):
            rom_id = struct.unpack_from("<I", data, off)[0]
            if rom_id != duelist_id:
                raise ValueError(f"id {duelist_id:#x}: record at {addr:#010x} holds id {rom_id:#x}, not "
                                  f"{duelist_id:#x} -- registry address is stale, stop and re-verify")
            a, b = (cond.ref_id, cond.count) if kind is BeatDuelist else (cond.stat_type, cond.value)
            struct.pack_into("<I", data, off + 4, a)
            struct.pack_into("<I", data, off + 8, b)
            print(f"  id {duelist_id:#x}: {cond!r}")

        elif kind in (RawValue, SummonCard):
            rom_id = struct.unpack_from("<I", data, off)[0]
            if rom_id != duelist_id:
                raise ValueError(f"id {duelist_id:#x}: record at {addr:#010x} holds id {rom_id:#x}, not "
                                  f"{duelist_id:#x} -- registry address is stale, stop and re-verify")
            val = cond.value if kind is RawValue else cond.card_ref
            struct.pack_into("<I", data, off + 4, val)
            print(f"  id {duelist_id:#x}: {cond!r}")

        elif kind is BeatDuelistPair:
            pair = struct.unpack_from("<I", data, off)[0]
            if _unpack_pair(pair) != (duelist_id, duelist_id + 1):
                raise ValueError(f"id {duelist_id:#x}: pair record at {addr:#010x} doesn't start with "
                                  f"({duelist_id:#x},{duelist_id+1:#x}) -- registry address is stale")
            struct.pack_into("<I", data, off + 4, _pack_pair(*cond.ref_pair))
            struct.pack_into("<I", data, off + 8, cond.count)
            print(f"  id {duelist_id:#x} (pair): {cond!r}")

        elif kind is SummonCardPair:
            pair = struct.unpack_from("<I", data, off)[0]
            if _unpack_pair(pair) != (duelist_id, duelist_id + 1):
                raise ValueError(f"id {duelist_id:#x}: pair record at {addr:#010x} doesn't start with "
                                  f"({duelist_id:#x},{duelist_id+1:#x}) -- registry address is stale")
            struct.pack_into("<I", data, off + 4, cond.card_ref)
            print(f"  id {duelist_id:#x} (pair): {cond!r}")

    _save_ov18(rom, ov, data, out)
    print(f"  wrote {out}")


def read_condition(duelist_id: int, *, src: str | Path = SRC):
    if duelist_id in _SLOTS and duelist_id not in _REGISTRY:
        rom = ndspy.rom.NintendoDSRom.fromFile(str(src))
        ov = rom.loadArm9Overlays([OVERLAY_ID])[OVERLAY_ID]
        return struct.unpack_from("<I", ov.data, _SLOTS[duelist_id] - OV18_BASE)[0]
    if duelist_id not in _REGISTRY:
        raise ValueError(f"id {duelist_id:#x} has no known condition record")
    addr, kind = _REGISTRY[duelist_id]
    rom = ndspy.rom.NintendoDSRom.fromFile(str(src))
    ov = rom.loadArm9Overlays([OVERLAY_ID])[OVERLAY_ID]
    off = addr - OV18_BASE

    if kind in (BeatDuelist, StatThreshold):
        _id, a, b = struct.unpack_from("<3I", ov.data, off)
        return kind(a, b)
    if kind in (RawValue, SummonCard):
        _id, a = struct.unpack_from("<2I", ov.data, off)
        return kind(a)
    if kind is BeatDuelistPair:
        _pair, ref, count = struct.unpack_from("<3I", ov.data, off)
        return kind(_unpack_pair(ref), count)
    if kind is SummonCardPair:
        _pair, ref = struct.unpack_from("<2I", ov.data, off)
        return kind(ref)
    raise AssertionError(kind)


def main(src: str = SRC, out: str = OUT, *, write_text=None) -> None:
    del write_text  # accepted for apply-all-patches uniformity
    apply_conditions(CHANGES, src=src, out=out)


def verify(*, out: str | Path = OUT) -> bool:
    if not CHANGES:
        return True
    ok = True
    for duelist_id, expected in CHANGES.items():
        if isinstance(expected, SwapChapter):
            got = read_condition(duelist_id, src=out)
            good = got == expected.other_id
            print(f"  [{'OK ' if good else 'BAD'}] id {duelist_id:#x}: now in {expected.other_id:#x}'s slot" if good
                  else f"  [BAD] id {duelist_id:#x}: slot holds {got:#x}, expected {expected.other_id:#x}")
        else:
            got = read_condition(duelist_id, src=out)
            good = got == expected
            print(f"  [{'OK ' if good else 'BAD'}] id {duelist_id:#x}: {got!r} (expected {expected!r})")
        ok &= good
    return ok


if __name__ == "__main__":
    main()
    verify()
