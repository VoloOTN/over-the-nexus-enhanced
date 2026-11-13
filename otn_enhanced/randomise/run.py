"""Driver: apply every enabled stage, write the ROM and the report; plus the selftest."""
from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

import ndspy.rom

from otn_enhanced.randomise.cardprop import RACES, decode_entry, encode_entry
from otn_enhanced.randomise.config import (
    Config, Logger, Progress, PACK_MODE_STOCK, describe, random_seed, report_path_for,
)
from otn_enhanced.randomise.decks import (
    DECK_PATH, EMPTY_DECKS, SPELL_TYPE, _deck_key, _is_speed_name, card_tables,
    deck_is_turbo, speed_tables, stage_decks,
)
from otn_enhanced.randomise.packs import stage_packs
from otn_enhanced.randomise.props import BIN2_PATH, stage_properties
from otn_enhanced.randomise.puzzles import (
    PUZZLE_NAMES, PUZZLE_PATH, YDQ_MAGIC, stage_puzzles,
)
from otn_enhanced.randomise.seedpile import (
    SeedPileError, deckgen_available, load_seed_pile, validate_seed_pile,
)
from otn_enhanced.rom.pac_inplace import parse_pac_v1, parse_pac_v2
from otn_enhanced.rom.ydc_codec import decode_ydc_ids as decode_ydc
from otn_enhanced.rom.ydc_codec import encode_ydc_ids as encode_ydc

DUELIST_NOT_SOLVED = (
    "Unlocking CPU duelists is not solved yet.  See "
    "notes/cpu-duelist-unlock-findings.md for what is known and the next "
    "experiment; nothing is written until the gate is actually located."
)


def stage_duelists(rom, cfg: Config, log) -> int:
    """Intentionally inert.  The gate has not been found; see the findings note."""
    if cfg.unlock_duelists:
        log(f"  {DUELIST_NOT_SOLVED}")
    return 0


def run(cfg: Config, sink=None, verbose: bool = False, progress=None) -> Logger:
    """Apply every enabled stage and write the output ROM."""
    log = Logger(sink, verbose)
    progress = progress or Progress()
    if not cfg.rom_in or not os.path.exists(cfg.rom_in):
        raise ValueError(f"input ROM not found: {cfg.rom_in!r}")
    if not cfg.dry_run and not cfg.rom_out:
        raise ValueError("no output ROM path given")
    if not cfg.dry_run and os.path.abspath(cfg.rom_in) == os.path.abspath(cfg.rom_out):
        raise ValueError("refusing to overwrite the input ROM -- choose another output")

    # Resolve the seed BEFORE describe(), or the report header -- the thing that
    # makes a ROM reproducible months later -- would record an empty seed.
    seed_note = ""
    if not cfg.seed:
        cfg.seed = random_seed()
        seed_note = "   (generated -- pass --seed to reproduce this ROM)"

    # The header is recorded but not echoed -- the console already shows the
    # settings the user just chose; the report is what needs them written down.
    for line in describe(cfg):
        log(line, detail=True)

    log(f"reading {cfg.rom_in}")
    rom = ndspy.rom.NintendoDSRom.fromFile(cfg.rom_in)
    code = bytes(rom.idCode).decode("ascii", "replace")
    log(f"game code: {code}")
    if code != "BYYP":
        log(f"  WARNING: expected BYYP (Over the Nexus, EU).  Card data will still "
            f"decode, but the overlay-1 pack addresses are EU-only.")
    log(f"seed: {cfg.seed}{seed_note}" + ("   [DRY RUN -- nothing will be written]" if cfg.dry_run else ""))

    if cfg.touches_properties():
        log("properties:")
        log(f"  {stage_properties(rom, cfg, log, progress)} card(s) changed")
    else:
        log("properties: nothing enabled")

    if cfg.pack_mode != PACK_MODE_STOCK:
        log("packs:")
        progress.stage("unlocking booster packs")
        stage_packs(rom, cfg, log)

    if cfg.zero_puzzle_lp:
        log("puzzles:")
        progress.stage("neutralising duel puzzles")
        log(f"  {stage_puzzles(rom, cfg, log)} puzzle(s) updated")

    if cfg.randomise_decks:
        log("decks:")
        log(f"  {stage_decks(rom, cfg, log, progress)} deck(s) rebuilt")

    stage_duelists(rom, cfg, log)

    if cfg.dry_run:
        log("dry run complete -- no ROM written")
    else:
        progress.stage("writing the ROM")
        Path(cfg.rom_out).parent.mkdir(parents=True, exist_ok=True)
        rom.saveToFile(cfg.rom_out)
        log(f"wrote {cfg.rom_out}")

    report = "" if cfg.no_report else report_path_for(cfg)
    if report:
        Path(report).parent.mkdir(parents=True, exist_ok=True)
        with open(report, "w", encoding="utf-8") as fh:
            fh.write("\n".join(log.lines) + "\n")
        # Appended after writing so the line itself is not missing from the file.
        log(f"report -> {report}  ({len(log.lines)} lines)")
    progress.finish()
    return log


def selftest(rom_path: str, sink=None, pile_path: str | None = None) -> bool:
    """Prove every reader and writer round-trips before any randomisation.

    Where the repo is importable this also cross-checks the inlined card_prop
    layout and PAC reader against ``rom.game_constants`` and ``rom.pac``, which is what stops the
    duplicated copies drifting from the validated originals.
    """
    log = Logger(sink, verbose=True)
    ok = True

    def check(label: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and passed
        log(f"  [{'OK ' if passed else 'BAD'}] {label}{(' -- ' + detail) if detail else ''}")

    log(f"selftest against {rom_path}")
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)

    # --- bin2.pac / card_prop.bin ---
    bin2 = bytes(rom.getFileByName(BIN2_PATH))
    a2 = parse_pac_v1(bin2)
    check("bin2.pac parsed", len(a2.entries) == 99, f"{len(a2.entries)} entries")
    cp_entry = a2.by_name("card_prop.bin")
    cp = a2.payload(bin2, cp_entry)
    count = (len(cp) - 8) // 8
    check("card_prop.bin sized", len(cp) == 8 + count * 8, f"{count} entries")

    bad = [i for i in range(count)
           if encode_entry(decode_entry(cp[8 + i * 8:16 + i * 8])) != cp[8 + i * 8:16 + i * 8]]
    check("card_prop round-trip", not bad, f"{len(bad)} mismatch(es)")

    # --- puzzle.pac ---
    puz = bytes(rom.getFileByName(PUZZLE_PATH))
    ap = parse_pac_v2(puz)
    check("puzzle.pac parsed", len(ap.entries) == 17, f"{len(ap.entries)} entries")
    missing = [n for n in PUZZLE_NAMES if ap.by_name(n) is None]
    check("all ten tume puzzles present", not missing, str(missing))
    non_yq = [e.name for e in ap.entries if puz[e.address:e.address + 2] != YDQ_MAGIC]
    check("non-YQ entries identified", non_yq == ["lghost_rd.ydq"], str(non_yq))

    # lghost_rd.ydq's table entry claims 2501 bytes while the next entry starts
    # 512 bytes later, so its declared range overlaps tume10/01/02.  Harmless
    # here -- puzzle writes are 2 bytes at a known offset -- but any future
    # size-changing write to puzzle.pac must bound itself by the next entry's
    # address rather than trusting the size word.
    srt = sorted(ap.entries, key=lambda e: e.address)
    overlaps = [e.name for i, e in enumerate(srt)
                if i + 1 < len(srt) and e.address + e.size > srt[i + 1].address]
    check("only lghost_rd.ydq overlaps its neighbour",
          overlaps == ["lghost_rd.ydq"], str(overlaps))
    tume_overlap = [n for n in overlaps if n in PUZZLE_NAMES]
    check("no tume puzzle overlaps another entry", not tume_overlap, str(tume_overlap))

    # --- deck.pac / .ydc ---
    dp = bytes(rom.getFileByName(DECK_PATH))
    ad = parse_pac_v1(dp)
    check("deck.pac parsed", len(ad.entries) == 305, f"{len(ad.entries)} entries")
    ydc_bad, ydc_trailing = [], 0
    for e in ad.entries:
        raw = ad.payload(dp, e)
        deck = decode_ydc(raw)
        if encode_ydc(deck) != raw:
            ydc_bad.append(e.name)
        if deck["trailing"]:
            ydc_trailing += 1
    check("ydc round-trip", not ydc_bad, f"{len(ydc_bad)} mismatch(es)")
    check("ydc trailing bytes", ydc_trailing == 0, f"{ydc_trailing} with trailing data")

    # --- table offsets point at the sizes we read ---
    slots_ok = all(
        struct.unpack_from("<I", dp, e.table_offset + 4)[0] == e.size
        for e in ad.entries
    )
    check("v1 table offsets locate the size words", slots_ok)

    # --- Turbo Duel decks and the Speed Spell pool ---
    cid2name, cid2type, name2cid = card_tables(rom)
    by_base, every_speed = speed_tables(name2cid)
    check("Speed Spell pool found", len(every_speed) == 148, f"{len(every_speed)} cards")
    # Only the ones whose base name is itself a real card can be reached by
    # translating a deckgen pick; the rest (Speed Force, Star Force, Overtune, …)
    # are Turbo-only and can only arrive as a random substitution.
    reachable = sum(1 for base in by_base if base in name2cid)
    check("Speed Spells reachable by translating a normal card",
          reachable == 111, f"{reachable} of {len(by_base)}")

    turbo, by_suffix, illegal = [], 0, []
    for e in ad.entries:
        main = decode_ydc(ad.payload(dp, e))["main"]
        if "_rd" in e.name.lower():
            by_suffix += 1
        if deck_is_turbo(main, cid2name):
            turbo.append(e.name)
            # The rule the fix-up enforces: a turbo deck runs no ordinary Spell.
            if any(cid2type.get(c) == SPELL_TYPE and not _is_speed_name(cid2name.get(c, ""))
                   for c in main):
                illegal.append(e.name)
    present = {_deck_key(e.name) for e in ad.entries}
    lost = [n for n in EMPTY_DECKS if _deck_key(n) not in present]
    check("the starting decks that get emptied are present in deck.pac",
          not lost, f"missing {lost}")

    check("turbo decks detected by contents", len(turbo) == 84, f"{len(turbo)} decks")
    check("the _rd suffix alone would miss most of them",
          by_suffix == 29, f"{by_suffix} named *_rd.ydc of {len(turbo)} turbo")
    check("no stock turbo deck runs an ordinary Spell", not illegal, str(illegal[:3]))

    # --- the seed pile: are the cards it names real cards? ---
    if not pile_path or not os.path.exists(pile_path):
        log(f"  [--] no seed pile at {pile_path} -- nothing to validate")
    else:
        try:
            pile = load_seed_pile(pile_path)
        except SeedPileError as exc:
            check("seed pile is valid JSON", False, str(exc))
        else:
            check("seed pile is valid JSON", True, f"{len(pile)} usable recipe(s)")
            pool = None
            if deckgen_available():
                try:
                    from otn_enhanced.deckgen.score import load_scored
                    pool = load_scored()[0]
                except Exception as exc:  # noqa: BLE001
                    log(f"  [--] could not load the deckgen pool ({exc}); "
                        "seed names checked against the ROM name table only")
            problems = validate_seed_pile(pile, cid2name, pool)
            check("every seed-pile card resolves to a real card"
                  + (" (checked against the deckgen pool)" if pool else
                     " (checked against the ROM name table)"),
                  not problems, f"{len(problems)} problem(s)")
            for p in problems:
                log(f"        - {p}")
            if not pile:
                log("  [--] seed pile has no usable recipes yet "
                    "-- the deck stage will skip until it does")

    # --- anti-drift: compare against rom.game_constants and rom.pac ---
    try:
        from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
        from otn_enhanced.rom.pac import parse_pac as repo_parse
    except Exception:
        log("  [--] rom modules not importable -- skipping anti-drift cross-check")
    else:
        drift = []
        for i in range(count):
            mine = decode_entry(cp[8 + i * 8:16 + i * 8])
            theirs = GC.decode_entry(cp[8 + i * 8:16 + i * 8])
            # game_constants exposes race as a name, so mirror its unmapped
            # fallback rather than comparing against None.  Spells and Traps
            # carry race 23 and 24 -- outside the 0..22 monster range -- so a
            # bare RACES.get() would report all 1755 of them as drift.
            my_race = RACES.get(mine["race"], f"Unknown({mine['race']})")
            if (mine["cid"] != theirs["card_id"]
                    or mine["atk_encoded"] != theirs["atk_encoded"]
                    or mine["def_encoded"] != theirs["def_encoded"]
                    or mine["card_type"] != theirs["card_type_encoded"]
                    or mine["attribute"] != theirs["attribute_encoded"]
                    or mine["level"] != theirs["level"]
                    or my_race != theirs["race"]):
                drift.append(i)
        check("card_prop layout matches rom.game_constants",
              not drift, f"{len(drift)} row(s) differ")

        for label, blob, mine_arch in (("bin2.pac", bin2, a2), ("deck.pac", dp, ad),
                                       ("puzzle.pac", puz, ap)):
            repo = repo_parse(blob, label)
            same = (len(repo.files) == len(mine_arch.entries) and all(
                r.get_clean_name() == m.name and r.address == m.address and r.size == m.size
                for r, m in zip(repo.files, mine_arch.entries)))
            check(f"{label} reader matches rom.pac", same)

    log("selftest PASSED" if ok else "selftest FAILED")
    return ok
