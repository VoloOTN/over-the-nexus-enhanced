"""Stage: regenerate every .ydc in deck.pac with deckgen, against the new stats."""
from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path

from otn_enhanced.randomise.config import Config, Progress
from otn_enhanced.randomise.props import BIN2_PATH, _card_names
from otn_enhanced.randomise.seedpile import (
    DECKGEN_UNAVAILABLE, SeedPileError, deckgen_available, deckgen_missing,
    load_seed_pile, validate_seed_pile,
)
from otn_enhanced.randomise.cardprop import decode_entry
from otn_enhanced.rom.pac_inplace import parse_pac_v1, write_v1_grow
from otn_enhanced.rom.ydc_codec import decode_ydc_ids as decode_ydc
from otn_enhanced.rom.ydc_codec import encode_ydc_ids as encode_ydc

DECK_PATH = "Data_arc_pac/deck.pac"


def format_decklist(main: list[int], extra: list[int], side: list[int],
                    cid2name: dict[int, str]) -> list[str]:
    """Render a deck as an indented, counted decklist.

    Grouped by card with a copy count, in descending-count then name order, so
    the list reads like a decklist rather than the engine's internal ordering.
    """
    lines: list[str] = []
    for label, cids in (("MAIN", main), ("EXTRA", extra), ("SIDE", side)):
        if not cids:
            continue
        counts: dict[int, int] = {}
        for cid in cids:
            counts[cid] = counts.get(cid, 0) + 1
        lines.append(f"      {label} ({len(cids)}):")
        for cid, n in sorted(counts.items(),
                             key=lambda kv: (-kv[1], cid2name.get(kv[0], ""))):
            lines.append(f"        {n}x {cid2name.get(cid) or f'cid 0x{cid:04X}'}")
    return lines


# ---------------------------------------------------------------------------
# Turbo (Riding) duel decks
# ---------------------------------------------------------------------------
# A Turbo Duel deck may only run Speed Spells, never ordinary Spells; monsters
# and Traps are unrestricted, and Speed World is NOT a deck card (measured over
# all 305 stock decks: 84 hold Speed Spells and *zero* of them hold an ordinary
# Spell).  deckgen cannot build these itself -- `namematch` marks every
# "Speed Spell - *" card `excluded` ("turbo duel only") and `Card.playable` is
# False for them, so they are absent from its pool and unscored.  So the spells
# of a turbo deck are fixed up here after deckgen returns.
#: Deck files emptied rather than randomised.  These two are the PLAYER's own
#: starting decks -- ``syoki`` is 初期, "initial" -- so a randomised one would hand
#: the player a pre-built pile instead of making them build from what they own.
#: Matched on a normalised name because the PAC filename parser prefixes a stray
#: character on a few entries.
EMPTY_DECKS = ("rpg001_0_syoki.ydc", "rpg002_0_rd.ydc")


def _deck_key(name: str) -> str:
    """Normalise a .ydc name for comparison (drops the parser's stray prefixes)."""
    return "".join(c for c in name.lower() if c.isalnum() or c in "._")


EMPTY_DECK_KEYS = frozenset(_deck_key(n) for n in EMPTY_DECKS)


def empty_ydc(header: bytes) -> bytes:
    """A .ydc with no cards at all, keeping this deck's own 8-byte header."""
    return encode_ydc({"header": header, "main": [], "extra": [], "side": [],
                       "trailing": b""})


SPEED_PREFIX = "Speed Spell - "
SPEED_WORLD_PREFIX = "Speed World"
SPELL_TYPE = 27
MAX_COPIES = 3


def _is_speed_name(name: str) -> bool:
    return name.startswith(SPEED_PREFIX) or name.startswith(SPEED_WORLD_PREFIX)


def card_tables(rom) -> tuple[dict[int, str], dict[int, int], dict[str, int]]:
    """Build cid -> name, cid -> card_type and name -> cid from bin2.pac.

    card_name_e.bin is index-aligned with card_prop.bin (both 4305 entries), and
    a .ydc stores engine cids -- the same values as card_prop's card_id field.
    """
    pac = bytes(rom.getFileByName(BIN2_PATH))
    archive = parse_pac_v1(pac)
    entry = archive.by_name("card_prop.bin")
    cp = archive.payload(pac, entry)
    count = (len(cp) - 8) // 8
    names = _card_names(pac, archive, count)

    cid2name: dict[int, str] = {}
    cid2type: dict[int, int] = {}
    name2cid: dict[str, int] = {}
    for i in range(count):
        fields = decode_entry(cp[8 + i * 8:16 + i * 8])
        cid = fields["cid"]
        name = names[i] if i < len(names) else ""
        cid2name.setdefault(cid, name)
        cid2type.setdefault(cid, fields["card_type"])
        if name:
            name2cid.setdefault(name, cid)
    return cid2name, cid2type, name2cid


def speed_tables(name2cid: dict[str, int]) -> tuple[dict[str, int], list[int]]:
    """``base card name -> Speed Spell cid``, plus every Speed Spell cid.

    111 of the 148 Speed Spells are named ``Speed Spell - <the normal card>`` and
    so can be substituted by name; the other 37 (Speed Force, Star Force,
    Overtune, …) are Turbo-only and have no ordinary counterpart.
    """
    by_base: dict[str, int] = {}
    every: list[int] = []
    for name, cid in name2cid.items():
        if not name.startswith(SPEED_PREFIX):
            continue
        every.append(cid)
        by_base.setdefault(name[len(SPEED_PREFIX):], cid)
    return by_base, sorted(every)


def deck_is_turbo(cids: list[int], cid2name: dict[int, str]) -> bool:
    """True if a *stock* deck is a Turbo Duel deck.

    Detected from contents, **not** the filename: only 29 of the 84 turbo decks
    are named ``*_rd.ydc``; the rest are the ``rtlr*``, ``wrd*`` and ``rpg*``
    families, which a suffix test misses entirely.
    """
    return any(_is_speed_name(cid2name.get(c, "")) for c in cids)


def to_turbo_spells(main: list[int], cid2name, cid2type, by_base, every_speed,
                    rng: random.Random) -> tuple[list[int], int, int]:
    """Replace every ordinary Spell in *main* with a Speed Spell.

    Translates by name where a ``Speed Spell - <name>`` exists, otherwise draws
    an unused Speed Spell at random.  Deck size and the monster/Trap picks are
    preserved, so deckgen's actual scoring still decides the deck's shape; only
    the spells -- which deckgen cannot legally choose for a Turbo Duel -- change.
    Returns ``(new_main, translated, substituted)``.
    """
    counts: dict[int, int] = {}
    for cid in main:
        counts[cid] = counts.get(cid, 0) + 1

    def room(cid: int) -> bool:
        return counts.get(cid, 0) < MAX_COPIES

    pool = [c for c in every_speed if c not in counts]
    rng.shuffle(pool)

    out: list[int] = []
    translated = substituted = 0
    for cid in main:
        if cid2type.get(cid) != SPELL_TYPE or _is_speed_name(cid2name.get(cid, "")):
            out.append(cid)
            continue
        counts[cid] -= 1
        swap = by_base.get(cid2name.get(cid, ""))
        if swap is not None and room(swap):
            translated += 1
        else:
            swap = next((c for c in pool if room(c)), None)
            if swap is None:
                # Nothing legal left to put here; drop the slot and let the
                # caller top the deck back up.
                continue
            pool.remove(swap)
            substituted += 1
        counts[swap] = counts.get(swap, 0) + 1
        out.append(swap)
    return out, translated, substituted


def card_tables(rom) -> tuple[dict[int, str], dict[int, int], dict[str, int]]:
    """Build cid -> name, cid -> card_type and name -> cid from bin2.pac.

    card_name_e.bin is index-aligned with card_prop.bin (both 4305 entries), and
    a .ydc stores engine cids -- the same values as card_prop's card_id field.
    """
    pac = bytes(rom.getFileByName(BIN2_PATH))
    archive = parse_pac_v1(pac)
    entry = archive.by_name("card_prop.bin")
    cp = archive.payload(pac, entry)
    count = (len(cp) - 8) // 8
    names = _card_names(pac, archive, count)

    cid2name: dict[int, str] = {}
    cid2type: dict[int, int] = {}
    name2cid: dict[str, int] = {}
    for i in range(count):
        fields = decode_entry(cp[8 + i * 8:16 + i * 8])
        cid = fields["cid"]
        name = names[i] if i < len(names) else ""
        cid2name.setdefault(cid, name)
        cid2type.setdefault(cid, fields["card_type"])
        if name:
            name2cid.setdefault(name, cid)
    return cid2name, cid2type, name2cid


_W: dict = {}


def _gen_init(profile: str, rom_path: str) -> None:
    """Load the card pool once per worker, against the randomised ROM.

    The parent rebuilds the pool first, so by the time workers run this the
    on-disk cache is already keyed to *rom_path* and each worker gets a hit.
    """
    import logging
    logging.disable(logging.CRITICAL)
    from otn_enhanced.deckgen import resources
    from otn_enhanced.deckgen.params import default
    from otn_enhanced.deckgen.score import load_scored

    resources.set_rom_path(rom_path)
    cards, _, idx, scored = load_scored()
    _W["cards"] = cards
    _W["idx"] = idx
    _W["scored"] = scored
    _W["by_cid"] = {c.cid: c for c in cards}
    _W["params"] = default().with_profile(profile) if profile else default()


def _gen_one(task: tuple) -> dict:
    """Generate one deck for one deck-file slot."""
    import random as _random
    from otn_enhanced.deckgen import emit, search
    from otn_enhanced.deckgen.constraints import Limits, MonsterFilter

    name, recipe, rng_seed = task
    cards, scored, idx = _W["cards"], _W["scored"], _W["idx"]
    params = _W["params"]
    banlist = str(recipe.get("banlist", "none")).lower()
    limits = (Limits.flat(int(params["deck.max_copies"]))
              if banlist in ("none", "off", "") else Limits.named(banlist))
    opts = search.GenOptions(
        size=int(recipe.get("size", 40)),
        beam_width=recipe.get("beam", 4),
        restarts=[recipe.get("lam", 1.0)],
        candidate_width=recipe.get("candidates", 60),
        rng=_random.Random(rng_seed),
        limits=limits,
        monster_filter=MonsterFilter.parse(
            cards, races=recipe.get("allowed_types"),
            attributes=recipe.get("allowed_attributes")),
    )
    try:
        deck = search.generate(list(recipe["seed"]), cards, scored, idx, params, opts)
    except Exception as exc:  # noqa: BLE001 -- reported by the parent
        return {"name": name, "seed": list(recipe["seed"]), "error": str(exc)}
    payload = emit.to_ydc_json(deck, _W["by_cid"])
    return {
        "name": name,
        "seed": list(recipe["seed"]),
        "rng": rng_seed,
        "main": list(payload["main_deck"]),
        "extra": list(payload["extra_deck"]),
    }


#: How many different seeds to try before a deck slot is left at stock contents.
DECK_ATTEMPTS = 4


def _log_gen(log, r: dict, done: int, total: int, t0: float,
             label: str = "generating decks") -> None:
    """Progress line with an ETA, since a full run generates hundreds of decks."""
    import time
    rate = (time.time() - t0) / max(done, 1)
    eta = rate * (total - done)
    what = (f"FAILED ({r['error']})" if "error" in r
            else f"{len(r['main'])}+{len(r['extra'])}")
    tag = "" if label.startswith("generating") else "retry "
    log(f"  [{tag}{done}/{total}] {r['name']}: {r['seed']} -> {what}"
        + (f"   eta {eta / 60:.0f} min" if eta > 90 else f"   eta {eta:.0f}s"))

def stage_decks(rom, cfg: Config, log, progress=None) -> int:
    """Regenerate every .ydc in deck.pac, at run time, from a randomly drawn seed.

    There is no filename -> seed mapping by design: the pile is flat and each deck
    draws from it, so the pile can be extended without renaming anything.

    Decks are generated **now**, against the properties this run just wrote, and
    are never cached between runs.  deckgen's pool is keyed by cid and carries each
    card's Attribute, Type, Level, ATK and DEF, so a deck computed before the
    properties moved is a deck built around cards that no longer exist.  That is
    what ``cardpool.is_randomised`` warns about, and it is why the pool is rebuilt
    from the randomised ROM below rather than reused.
    """
    if not cfg.randomise_decks:
        return 0
    progress = progress or Progress()

    pac = bytearray(rom.getFileByName(DECK_PATH))
    archive = parse_pac_v1(bytes(pac))
    decks = sorted((e for e in archive.entries if e.name.lower().endswith(".ydc")),
                   key=lambda e: e.name)
    log(f"  deck.pac: {len(decks)} decks")

    # The player's own starting decks are EMPTIED, not randomised.  Chosen from the
    # WHOLE list before --deck-limit is applied (that flag limits generation, a
    # testing convenience, and must not leave a stock starting deck behind), and
    # before the deckgen gates below, because blanking needs no card pool: a build
    # that cannot generate should still hand the player an empty deck.
    blanks = [e for e in decks if _deck_key(e.name) in EMPTY_DECK_KEYS]
    decks = [e for e in decks if _deck_key(e.name) not in EMPTY_DECK_KEYS]
    if cfg.deck_limit:
        decks = decks[:cfg.deck_limit]
        log(f"  limited to the first {len(decks)} deck(s) for generation")
    built = 0
    if blanks:
        progress.stage("emptying the starting decks", len(blanks))
        for entry in blanks:
            original = decode_ydc(archive.payload(bytes(pac), entry))
            blank = empty_ydc(original["header"])
            if not cfg.dry_run:
                write_v1_grow(pac, archive, entry, blank)
            progress.step()
            log(f"  {entry.name}: emptied "
                f"({len(original['main'])}+{len(original['extra'])}"
                f"+{len(original['side'])} -> 0+0+0, {len(blank)} bytes)")
            built += 1

    def commit(n: int) -> int:
        """Write deck.pac back if anything changed, and report the count."""
        if n and not cfg.dry_run:
            rom.setFileByName(DECK_PATH, bytes(pac))
        return n

    try:
        pile = load_seed_pile(cfg.seed_pile_path)
    except SeedPileError as exc:
        log(f"  deck generation skipped: {exc}")
        return commit(built)
    if not pile:
        log(f"  deck generation skipped: seed pile at "
            f"{cfg.seed_pile_path or '<unset>'} has no usable entries")
        return commit(built)
    if not deckgen_available():
        log(f"  deck generation skipped: {DECKGEN_UNAVAILABLE}")
        for m in deckgen_missing()[:5]:
            log(f"    missing: {m}")
        return commit(built)

    import tempfile
    import time
    from otn_enhanced.deckgen import resources as dg_res
    from otn_enhanced.deckgen.score import load_scored

    # The pool must be REBUILT from the randomised ROM, so the build inputs have to
    # be present.  Without this guard a bundled build would sail past on its
    # shipped stock-ROM pool (trust_cache skips the staleness check) and generate
    # every deck around properties the player's ROM no longer has.
    if not dg_res.can_build_pool():
        log("  deck generation skipped: the card pool has to be rebuilt from the "
            "randomised ROM, and the inputs for that are not present here.")
        for m in dg_res.missing_pool_inputs():
            log(f"    missing: {m}")
        log("    A pre-built pool describes the stock stats and would silently "
            "mis-build every deck, so this is refused rather than approximated.")
        return commit(built)

    log(f"  seed pile has {len(pile)} recipe(s)")

    cid2name, cid2type, name2cid = card_tables(rom)
    by_base, every_speed = speed_tables(name2cid)
    turbo_names = {e.name for e in decks
                   if deck_is_turbo(decode_ydc(archive.payload(bytes(pac), e))["main"],
                                    cid2name)}
    log(f"  {len(turbo_names)} of these are Turbo Duel decks "
        f"(detected by contents, not filename); {len(every_speed)} Speed Spells available")

    # Point deckgen at the ROM as it stands *now* -- properties already randomised.
    # This changes the pool cache key, so load_scored rebuilds against the real
    # properties instead of silently reusing a stock-ROM pool.
    # The filename must be STABLE for a given set of property settings, not unique
    # per process.  cache.source_map keys any path outside the repo/bundle root by
    # its absolute path, so a pid in the name changed the cache key on every launch
    # and the 30 s pool rebuild was paid every single run despite a valid cache
    # sitting there.  Derived from the settings that determine card_prop, so two
    # different configs still get different files and cannot race.
    stamp = hashlib.sha256("\x00".join([
        cfg.seed,
        str(cfg.randomise_attribute), str(cfg.randomise_race),
        str(cfg.randomise_level), str(cfg.randomise_synchro_level),
        str(cfg.randomise_atk), str(cfg.randomise_def),
        str(cfg.balanced), repr(sorted(cfg.caps.items())),
    ]).encode()).hexdigest()[:12]
    tmp_rom = Path(tempfile.gettempdir()) / f"otn_rando_pool_{stamp}.nds"
    try:
        log("  writing the randomised ROM for deckgen to read...")
        rom.saveToFile(str(tmp_rom))
        dg_res.set_rom_path(tmp_rom)

        log("  building the deckgen pool from the RANDOMISED properties "
            "(slow the first time; it reflects the new stats, not the stock ones)")
        progress.stage("rebuilding the card pool from the randomised stats")
        t_pool = time.time()
        cards = load_scored()[0]
        log(f"    pool ready in {time.time() - t_pool:.0f}s")
        try:
            from otn_enhanced.deckgen.cardpool import is_randomised
            log(f"    deckgen sees this ROM as randomised: {is_randomised(cards)}")
        except Exception:  # noqa: BLE001 -- informational only
            pass

        problems = validate_seed_pile(pile, cid2name, cards)
        if problems:
            log(f"  deck stage skipped: {len(problems)} problem(s) in the seed pile:")
            for p in problems:
                log(f"    - {p}")
            return 0
        del cards

        # Per-slot draws, derived from (master seed, deck filename, attempt).
        # Deterministic and independent of ordering, so adding a deck or changing
        # --deck-limit does not reshuffle every other slot, and a retry lands on a
        # reproducible replacement rather than wherever the RNG happened to be.
        def draw(name: str, attempt: int, exclude: set) -> tuple:
            h = hashlib.sha256(
                f"{cfg.seed}\u0000deck\u0000{name}\u0000{attempt}".encode()).digest()
            r = random.Random(int.from_bytes(h[:8], "little"))
            # Exclude every recipe sharing a seed card with one already tried: a
            # sibling variant (same card, different Type/Attribute filter) is not a
            # different seed and tends to fail the same way.
            bad = {tuple(pile[i]["seed"]) for i in exclude}
            choices = [i for i in range(len(pile)) if tuple(pile[i]["seed"]) not in bad] or list(
                range(len(pile)))
            i = r.choice(choices)
            recipe = dict(pile[i], banlist="none") if cfg.no_banlist else pile[i]
            return i, recipe, r.getrandbits(32)

        def run_batch(batch: list, label: str) -> list:
            """Generate a batch of decks, sequentially or across a process pool."""
            out: list = []
            if jobs == 1:
                _gen_init("randomised", str(tmp_rom))
                for task in batch:
                    out.append(_gen_one(task))
                    progress.step()
                    _log_gen(log, out[-1], len(out), len(batch), t_batch[0], label)
            else:
                import multiprocessing as mp
                ctx = mp.get_context("spawn")
                with ctx.Pool(processes=jobs, initializer=_gen_init,
                              initargs=("randomised", str(tmp_rom))) as pool:
                    for r in pool.imap_unordered(_gen_one, batch):
                        out.append(r)
                        progress.step()
                        _log_gen(log, r, len(out), len(batch), t_batch[0], label)
            return out

        tried: dict = {}
        tasks = []
        for entry in decks:
            i, recipe, rng_seed = draw(entry.name, 0, set())
            tried[entry.name] = {i}
            tasks.append((entry.name, recipe, rng_seed))

        jobs = max(1, min(cfg.jobs or (os.cpu_count() or 1), len(tasks)))
        log(f"  generating {len(tasks)} deck(s) on {jobs} process(es)")
        t0 = time.time()
        t_batch = [t0]
        done: dict = {}

        # A recipe can fail for this ROM -- a seed card the randomised properties
        # made unbuildable, a monster filter with nothing left to satisfy it.  Draw
        # a DIFFERENT seed and try again rather than leaving the slot at its stock
        # contents, which would quietly leave un-randomised decks in the ROM.
        pending = tasks
        for attempt in range(DECK_ATTEMPTS):
            if not pending:
                break
            label = "generating decks" if attempt == 0 else f"retrying decks (pass {attempt + 1})"
            progress.stage(label, len(pending))
            t_batch[0] = time.time()
            if attempt:
                log(f"  {len(pending)} deck(s) failed -- retrying with different "
                    f"seeds (pass {attempt + 1} of {DECK_ATTEMPTS})")
            batch = run_batch(pending, label)
            retry = []
            for r in batch:
                if "error" not in r:
                    done[r["name"]] = r
                    continue
                name = r["name"]
                log(f"    {name}: {r['seed']} failed -- {r['error']}", detail=True)
                if attempt + 1 < DECK_ATTEMPTS:
                    i, recipe, rng_seed = draw(name, attempt + 1, tried.get(name, set()))
                    tried.setdefault(name, set()).add(i)
                    retry.append((name, recipe, rng_seed))
                else:
                    done[name] = r        # exhausted; reported below
            pending = retry

        results = list(done.values())
        elapsed = time.time() - t0
        ok = sum(1 for r in results if "error" not in r)
        log(f"  generated in {elapsed:.0f}s "
            f"({elapsed / max(len(results), 1):.1f}s per deck, wall clock)")
        if ok != len(results):
            log(f"  {len(results) - ok} deck(s) still failed after {DECK_ATTEMPTS} "
                f"attempts and keep their stock contents")

        by_name = {r["name"]: r for r in results}
        progress.stage("writing decks into deck.pac", len(decks))
        for entry in decks:
            progress.step()
            r = by_name.get(entry.name)
            if r is None:
                continue
            if "error" in r:
                log(f"  {entry.name}: FAILED ({r['error']}) -- left at stock contents")
                continue
            original = decode_ydc(archive.payload(bytes(pac), entry))
            main, extra_cids = list(r["main"]), list(r["extra"])
            note = ""
            if entry.name in turbo_names:
                want = len(main)
                main, xlat, subbed = to_turbo_spells(
                    main, cid2name, cid2type, by_base, every_speed,
                    random.Random(r["rng"] ^ 0x5EED))
                note = f" [turbo: {xlat} translated, {subbed} substituted]"
                short = want - len(main)
                if short > 0:
                    spare = [c for c in every_speed if c not in main]
                    random.Random(r["rng"]).shuffle(spare)
                    main.extend(spare[:short])
                    note = note[:-1] + f", {short} topped up]"
            # Keep this deck's own 8-byte header and its side deck; there are four
            # distinct headers across the 305 decks and 32 carry a 15-card side deck.
            rebuilt = encode_ydc({
                "header": original["header"],
                "main": main,
                "extra": extra_cids,
                "side": original["side"],
                "trailing": b"",
            })
            if not cfg.dry_run:
                write_v1_grow(pac, archive, entry, rebuilt)
            log(f"  {entry.name}: seed {r['seed']} rng {r['rng']} -> "
                f"{len(main)}+{len(extra_cids)} ({len(rebuilt)} bytes){note}",
                detail=True)
            # The full decklist goes to the report unconditionally; it only reaches
            # the console with -v, since 305 decks is several thousand lines.
            for line in format_decklist(main, extra_cids, original["side"], cid2name):
                log(line, detail=True)
            built += 1
    finally:
        dg_res.set_rom_path(None)
        try:
            tmp_rom.unlink(missing_ok=True)
        except OSError:
            pass

    return commit(built)
