"""Command line for the generative deck builder.

::

    python -m otn_enhanced.deckgen.cli build-pool
    python -m otn_enhanced.deckgen.cli parse [--unparsed N]
    python -m otn_enhanced.deckgen.cli explain "Rekindling"
    python -m otn_enhanced.deckgen.cli partners "Rekindling"
    python -m otn_enhanced.deckgen.cli gen --seed "Rekindling" [--ydc rpg001_x.ydc]
    python -m otn_enhanced.deckgen.cli gen --seed "Marauding Captain" \
        --allowed-types Warrior --allowed-attributes EARTH
    python -m otn_enhanced.deckgen.cli golden
    python -m otn_enhanced.deckgen.cli validate
"""

from __future__ import annotations

import argparse
import json
import sys

from otn_enhanced.deckgen import cardpool, emit, golden, report, search, synergy
from otn_enhanced.deckgen.constraints import Limits, MonsterFilter
from otn_enhanced.deckgen.params import default
from otn_enhanced.deckgen.score import load_scored, top


def _cmd_build_pool(args) -> int:
    cards = cardpool.load_pool(force=args.force)
    print(cardpool.report(cards).format())
    playable = cardpool.playable(cards)
    print(f"playable          : {len(playable)} "
          f"({sum(1 for c in playable if c.has_text)} with effect text)")
    return 0


def _cmd_parse(args) -> int:
    from otn_enhanced.deckgen.text.parse import load_parsed

    _, _, rep = load_parsed(force=args.force)
    print(rep.format())
    if rep.empty_predicates:
        print("\npredicates matching no card in this ROM's pool:")
        for raw in rep.empty_predicates:
            print(f"  {raw!r}")
    if args.unparsed:
        print(f"\nfirst {args.unparsed} text segments that yielded no clause:")
        for name, text in rep.unparsed_samples[: args.unparsed]:
            print(f"  {name[:26]:28} {text[:88]!r}")
    return 0


def _cmd_explain(args) -> int:
    cards, _, idx, scored = load_scored(use_evidence=getattr(args, 'use_evidence', None))
    card = cardpool.find(cards, args.card)
    print(scored[card.cid].explain())
    print(f"\n  text: {card.desc}")
    print(f"  dedicated searchers: {idx.searchability(card.cid):.2f}")
    for pred, weight in scored[card.cid].parsed.wants:
        print(f"  wants {pred.raw!r} -> {idx.count(pred)} pool cards (weight {weight})")
    return 0


def _cmd_partners(args) -> int:
    cards, _, idx, scored = load_scored(use_evidence=getattr(args, 'use_evidence', None))
    card = cardpool.find(cards, args.card)
    print(f"best synergy partners for {card.name}:")
    for s, v in synergy.best_partners(scored[card.cid], scored, idx, args.n):
        print(f"  synergy {v:5.2f}  impact {s.impact:+6.2f}  {s.name[:44]:46} "
              f"{s.card.card_type}")
    return 0


def _cmd_top(args) -> int:
    _, _, _, scored = load_scored(use_evidence=getattr(args, 'use_evidence', None))
    pred = None
    if args.monsters:
        pred = lambda s: s.card.is_monster and not s.card.is_extra  # noqa: E731
    elif args.spells:
        pred = lambda s: not s.card.is_monster  # noqa: E731
    for s in top(scored, args.n, predicate=pred):
        print(f"  {s.impact:+6.2f} econ{s.econ.exp:+6.2f} pow{s.pow_.value:+6.2f}  "
              f"{s.name[:44]:46} {s.card.card_type}")
    return 0


def _cmd_gen(args) -> int:
    import time

    # Resolve the profile HERE, not just inside score_pool.  `search.generate`
    # takes its own Params and does `p or default()`, so deck-level weights were
    # reading the stock table even in randomised mode — anything fitted into
    # [profile.randomised] under [deck] would have been silently ignored.
    # score_pool resolves it again internally, which is idempotent.
    p = default()
    if not getattr(args, "use_evidence", False):
        p = p.with_profile("randomised")
    t0 = time.time()
    cards, _, idx, scored = load_scored(use_evidence=getattr(args, 'use_evidence', None))
    load_secs = time.time() - t0
    by_cid = {c.cid: c for c in cards}

    # Narrow search by DEFAULT.  Measured paired over 2 seeds x 3 RNG seeds, the
    # wide search (3 restarts, 200 candidates, beam 8) scores 139.16 +/- 16.91
    # against 143.18 +/- 7.66 for the narrow one — a paired difference of
    # +4.02 +/- 16.49, i.e. nothing, at 36.0s against 3.9s.  The search samples
    # its picks stochastically, so its RNG variance is several times larger than
    # anything the extra width buys.
    #
    # The practical consequence is worth knowing: at ~4s a build you can run
    # nine different --rng-seed values in the time one wide build takes and keep
    # the best, which beats the wide search outright.
    #
    # Only knobs left unset are lowered, so `--beam 8` still means beam 8.
    if not args.thorough:
        if args.beam is None:
            args.beam = 4
        if args.candidates == search.CANDIDATE_WIDTH:
            args.candidates = 60
        if args.lam is None:
            args.lam = 1.0
    if args.banlist.lower() in ("none", "off", ""):
        limits = Limits.flat(int(p["deck.max_copies"]))
        print("copy limits: none (3 of anything)")
    else:
        limits = Limits.named(args.banlist)
        banned = sum(1 for v in limits.per_cid.values() if v == 0)
        ltd = sum(1 for v in limits.per_cid.values() if v == 1)
        semi = sum(1 for v in limits.per_cid.values() if v == 2)
        print(f"copy limits from {limits.name}: "
              f"{banned} forbidden, {ltd} limited, {semi} semi-limited")

    # Validated here rather than inside the search so a typo'd Type fails before
    # the build starts, with the pool's own vocabulary in the message.
    try:
        mfilter = MonsterFilter.parse(
            cards, races=args.allowed_types, attributes=args.allowed_attributes,
            extra_deck=args.filter_extra_deck,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if mfilter:
        print(f"monster filter: {mfilter.describe()}")

    def log(msg: str) -> None:
        print(msg, file=sys.stderr, flush=True)

    opts = search.GenOptions(
        log=log if args.verbose else search._null_log,
        size=args.size,
        beam_width=args.beam,
        restarts=[args.lam] if args.lam else None,
        candidate_width=args.candidates,
        engine_cutoff=args.engine_cutoff,
        engine_max=args.engine_max,
        sample_top=args.sample_top,
        temperature=args.temperature,
        rng=__import__("random").Random(args.rng_seed),
        limits=limits,
        bootstrap_rounds=args.bootstrap,
        seed_holdout=not args.no_holdout,
        resize_top=args.resize_top,
        anti_seeds=args.anti_seed or [],
        monster_filter=mfilter,
    )
    try:
        deck = search.generate(args.seed, cards, scored, idx, p, opts)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(report.render(deck, cards, scored, idx))
    print(f"\n  startup (pool + parse + index + score): {load_secs:.1f}s")

    if args.ydc:
        entry = emit.to_changes_entry(deck, by_cid, args.ydc)
        path = args.out or f"deckgen_{args.ydc}.json"
        emit.write_changes_json(entry, path)
        print(f"\nwrote patch_bulk_ydcs entry to {path}")
        payload = emit.to_ydc_json(deck, by_cid)
        good, why = emit.round_trip_ok(payload)
        print(f"ydc round-trip: {why}")
        if not good:
            return 1
    return 0


def _cmd_seeds(args) -> int:
    """Rank cards by how good a deck seed they make."""
    from otn_enhanced.deckgen import seedrank

    cards, _, idx, scored = load_scored(use_evidence=getattr(args, 'use_evidence', None))
    only = None
    if args.spells:
        only = lambda s: not s.card.is_monster  # noqa: E731
    elif args.monsters:
        only = lambda s: s.card.is_monster  # noqa: E731
    ranked = seedrank.rank(cards, scored, idx, only=only)

    if args.card:
        card = cardpool.find(cards, args.card)
        hit = next((r for r in ranked if r.card.cid == card.cid), None)
        if hit is None:
            print(f"{card.name} is not rankable as a seed (Extra Deck or unplayable)")
            return 1
        place = ranked.index(hit) + 1
        print(hit.row())
        print(f"  rank {place} of {len(ranked)}")
        return 0

    print(f"{'score':>6}  {'card':36} engine       quality  specificity  reciprocity  combo")
    for r in ranked[: args.n]:
        print(r.row())
    if args.validate:
        print()
        print("-- validation: does the proxy track the deck it actually builds? --")
        print(seedrank.validate(ranked, cards, scored, idx, sample=args.validate))
    return 0


def _cmd_train(args) -> int:
    """Fit the balance coefficients against tournament play rate."""
    from otn_enhanced.deckgen import mining, training
    from otn_enhanced.deckgen.params import PARAMS_TOML
    from otn_enhanced.deckgen.validate import tournament

    cards, parsed, idx, _ = load_scored(use_evidence=getattr(args, 'use_evidence', None))
    if args.fetch:
        tournament.fetch_decks(per_format=args.per_format)
    # The decks cache spans ~100 formats from Goat (2005) to 2024.  This ROM is a
    # 2011 game whose default banlist is 2010.09, so fitting against all of them
    # rewards Goat staples (Premature Burial, Delinquent Duo, Confiscation) that
    # are FORBIDDEN here.  `mining` already restricts to the era for exactly this
    # reason; the objectives now agree with it.
    decks = tournament.load(cards) if args.all_formats else mining.era_decks(cards)
    print(f"fitting against {len(decks)} decks "
          f"({'all formats' if args.all_formats else str(mining.ERA_FORMATS)})")

    # Asking whether the model's OWN REASONING predicts play rate.
    #
    # `power.w_staple` (8.00) is a lookup of the very play rate this objective
    # measures, so any tag correlated with being played is redundant with it and
    # the fit returns 0.00 for everything — that is why the first pass at the
    # mechanic tags reported all five as worthless.  Turning the channel off is
    # the only way to ask whether a tag carries signal of its own.  The value is
    # NOT written back: `impact.w_evidence` is not in SEARCH_SPACE, so only the
    # coefficients under test are ever applied.
    base = default()
    if args.no_evidence:
        base = training._with(base, "impact.w_evidence", 0.0)  # noqa: SLF001
        print("evidence channel OFF — fitting the model's own reasoning")

    print(f"searching {len(training.SEARCH_SPACE)} coefficients, "
          f"{args.rounds} rounds, seeds {args.seeds}, min gain {args.min_gain}")
    result = training.fit_multi(
        cards, parsed, idx, decks, base,
        seeds=list(args.seeds), rounds=args.rounds, min_gain=args.min_gain,
    )
    print()
    print(result.format(args.min_seeds))

    agreed = result.consensus(args.min_seeds)
    if not agreed:
        print("\nno coefficient reached consensus — nothing to write")
        return 0
    if args.apply:
        training.write_params(argparse.Namespace(changes=agreed), PARAMS_TOML)
        print(f"\nwrote {len(agreed)} coefficients to {PARAMS_TOML}")
        failures = golden.run()
        if failures:
            print(f"golden tests now FAIL ({len(failures)}) — revert or re-tune:")
            for f in failures:
                print(f"  {f}")
            return 1
        print("golden tests still pass")
    else:
        print("\n(dry run — pass --apply to write params.toml)")
    return 0


def _cmd_train_deck(args) -> int:
    """Fit the DECK-level weights against 'tournament decks beat ROM AI decks'.

    A separate command from `train` on purpose.  `train` optimises Spearman
    against card play rate, and that objective is actively misleading for the
    economy/power balance: summing power across 40 cards rewards big-beater
    piles, which is what the ROM's AI decks are.  Measured separately, economy
    sum has deck-level AUC 0.625 and power sum 0.393 — anti-correlated.  So
    `impact.w_power` must be decided here, not there.
    """
    from otn_enhanced.deckgen import training
    from otn_enhanced.deckgen.params import PARAMS_TOML
    from otn_enhanced.deckgen.validate import corpus, tournament

    p = default()
    cards, parsed, idx, _ = load_scored(use_evidence=getattr(args, 'use_evidence', None))
    by_cid = {c.cid: c for c in cards}

    from otn_enhanced.deckgen import mining

    src = tournament.load(cards) if args.all_formats else mining.era_decks(cards)
    # Evidence feature mined from a disjoint slice of the SAME corpus, so a deck
    # never contributes to its own staple bonus.  Without this the objective is
    # partly self-fulfilling; measured, the evidence channel alone carries
    # Spearman from +0.20 (model only) to +0.74.
    import random as _r
    shuf = list(src); _r.Random(0).shuffle(shuf)
    holdout = shuf[: len(shuf) // 4]
    feat = training.mined_play_rate(holdout, cards)
    good = [(d.main, d.extra) for d in shuf[len(shuf) // 4:]]
    stock = [d for d in corpus.load_stock_decks() if not d.is_turbo(by_cid)]
    poor = [(d.main, d.extra) for d in stock]
    print(f"{len(good)} tournament decks (good) vs {len(poor)} ROM AI decks (poor); "
          f"evidence mined from {len(holdout)} held-out decks "
          f"({'all formats' if args.all_formats else str(mining.ERA_FORMATS)})")
    print(f"searching {len(training.DECK_SEARCH_SPACE)} coefficients, "
          f"{args.rounds} rounds, seeds {args.seeds}, min gain {args.min_gain}")
    print()

    result = training.fit_deck_multi(
        cards, parsed, idx, good, poor, p,
        seeds=list(args.seeds), rounds=args.rounds, min_gain=args.min_gain,
    )
    print()
    print(result.format(args.min_seeds))

    agreed = result.consensus(args.min_seeds)
    if not agreed:
        print("\nno coefficient reached consensus — nothing to write")
        return 0
    if args.apply:
        shim = argparse.Namespace(changes=agreed)
        training.write_params(shim, PARAMS_TOML)
        print(f"\nwrote {len(agreed)} coefficients to {PARAMS_TOML}")
        failures = golden.run()
        if failures:
            print(f"golden tests now FAIL ({len(failures)}) — revert or re-tune:")
            for f in failures:
                print(f"  {f}")
            return 1
        print("golden tests still pass")
    else:
        print("\n(dry run — pass --apply to write params.toml)")
    return 0


def _cmd_golden(args) -> int:
    return golden.main()


def _cmd_validate(args) -> int:
    from otn_enhanced.deckgen.validate import run

    # argparse.REMAINDER keeps a literal "--" separator, which run's own parser
    # would then reject; drop it so both `validate --reconstruct 30` and
    # `validate -- --reconstruct 30` work.
    rest = [a for a in args.rest if a != "--"]
    return run.main(rest)


#: Shared by every command that scores the pool.  Kept as a parent parser so the
#: flag is defined once and cannot drift between subcommands.
#:
#: **The default is OFF, and that is a deliberate reversal (2026-07-30).**
#:
#: `power.w_staple` is a per-cid lookup of tournament play rate, and it is 73% of
#: what separates one card from another.  Every metric in this repo rewards it,
#: because every metric scores agreement with the same tournament corpus — but
#: that corpus is survivor-biased: these are the decks that won money, so they
#: converge on whatever the meta settled on.  Optimising toward it builds the
#: meta, not a deck.
#:
#: The user play-tested both modes and preferred every deck built without it:
#: with the lookup on, generic staples crowd in regardless of seed.  Reproduced —
#: Caius the Shadow Monarch appears at 3 copies in the Six Samurai and Karakuri
#: builds and in **zero** of ten builds with the lookup off; Trap Dustshoot sits
#: in >=8 of 10 decks with it and drops out without.
#:
#: Note the aggregate proxies do NOT show this (mean pairwise Jaccard 0.253 vs
#: 0.227, seed-archetype share 40.8% vs 38.9%, over 10 seeds x 3 RNG seeds).
#: The proxy is the wrong instrument, not the evidence: the cards Caius displaces
#: are also off-archetype, so archetype share cannot see the swap.  Played
#: decks beat a proxy for played decks.
#:
#: `score_pool(use_evidence=None)` still auto-detects, which is what a library
#: caller and `deckgen validate` want; only the CLI default changed.
def _scoring_parent() -> argparse.ArgumentParser:
    q = argparse.ArgumentParser(add_help=False)
    q.add_argument(
        "--use-evidence", action=argparse.BooleanOptionalAction, default=False,
        help="score with the per-cid tournament play-rate lookup.  DEFAULT OFF "
             "-- see the note in the source.  With it on, generic staples crowd "
             "into every deck regardless of seed; with it off the model reasons "
             "from card text and the [profile.randomised] coefficients.  Pass "
             "--use-evidence to restore the lookup.",
    )
    return q


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="deckgen", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    scoring = [_scoring_parent()]

    q = sub.add_parser("build-pool", help="join card_prop to real card text")
    q.add_argument("--force", action="store_true")
    q.set_defaults(fn=_cmd_build_pool)

    q = sub.add_parser("parse", help="parse effect text and report coverage")
    q.add_argument("--force", action="store_true")
    q.add_argument("--unparsed", type=int, default=0)
    q.set_defaults(fn=_cmd_parse)

    q = sub.add_parser("explain", parents=scoring, help="show one card's economy and power breakdown")
    q.add_argument("card")
    q.set_defaults(fn=_cmd_explain)

    q = sub.add_parser("partners", parents=scoring, help="best synergy partners for a card")
    q.add_argument("card")
    q.add_argument("-n", type=int, default=20)
    q.set_defaults(fn=_cmd_partners)

    q = sub.add_parser("top", parents=scoring, help="highest-impact cards in the pool")
    q.add_argument("-n", type=int, default=25)
    q.add_argument("--monsters", action="store_true")
    q.add_argument("--spells", action="store_true")
    q.set_defaults(fn=_cmd_top)

    q = sub.add_parser("gen", parents=scoring, help="build a deck from a seed card")
    q.add_argument("--seed", required=True, nargs="+",
                   help="one or more seed cards to build a single deck around")
    q.add_argument("--anti-seed", nargs="+", default=None, metavar="CARD",
                   help="cards that must never appear in the deck (by name or "
                        "cid); applied as a zero copy limit, so nothing anywhere "
                        "in the search can pick them up")
    q.add_argument("--allowed-types", nargs="+", default=None, metavar="TYPE",
                   help="restrict the build to monsters of these Types "
                        "(Warrior, Dragon, Sea Serpent, ...). Case- and "
                        "punctuation-insensitive, so 'beast warrior' finds "
                        "Beast-Warrior. Spells and Traps are unaffected; Extra "
                        "Deck monsters are filtered too. --seed always wins: an "
                        "off-filter seed is still built around, and the filter "
                        "governs everything offered around it")
    q.add_argument("--allowed-attributes", nargs="+", default=None, metavar="ATTR",
                   help="restrict the build to monsters of these Attributes "
                        "(DARK, LIGHT, EARTH, WATER, FIRE, WIND, DIVINE). "
                        "Combined with --allowed-types as an AND: "
                        "'--allowed-types Warrior --allowed-attributes DARK' "
                        "admits only DARK Warriors")
    q.add_argument(
        "--filter-extra-deck", action=argparse.BooleanOptionalAction, default=True,
        help="apply --allowed-types/--allowed-attributes to the Extra Deck as "
             "well (DEFAULT ON). Keep it on for decks that count Types across "
             "the whole Graveyard -- Solidarity gives +800 ATK only 'if you "
             "have only 1 Type of monster in your GY', and one off-Type Synchro "
             "dying turns it off for the rest of the duel. Pass "
             "--no-filter-extra-deck when the restriction is about the engine "
             "rather than the Graveyard: the Extra Deck then fills to a full 15 "
             "from the whole pool, which a narrow Type cannot do on its own "
             "(the ROM ships 3 Sea Serpent and 4 Fish Extra Deck monsters).",
    )
    q.add_argument("--size", type=int, default=40)
    q.add_argument("--beam", type=int, default=None)
    q.add_argument("--lam", type=float, default=None,
                   help="fix lambda_synergy instead of sweeping the restarts")
    q.add_argument("--candidates", type=int, default=search.CANDIDATE_WIDTH)
    # The 2010.09 list is the newest one shipped in the ROM and the closest to
    # the format this game covers, so it is the sensible default; pass
    # --banlist none to build without copy limits.
    q.add_argument("--banlist", default="limit201009",
                   choices=[*Limits.available(), "none"],
                   help="which of the ROM's six Forbidden/Limited lists to "
                        "enforce (default: %(default)s; 'none' disables copy "
                        "limits). Baked into data/banlists.json -- regenerate "
                        "with -m deckgen.bake_banlists after changing the ROM.")
    q.add_argument("--ydc", default=None, help="target .ydc filename to emit for")
    q.add_argument("--out", default=None)
    q.add_argument("--engine-cutoff", type=float, default=0.0,
                   help="marginal gain per slot an engine card must clear (default 0)")
    q.add_argument("--engine-max", type=int, default=24,
                   help="ceiling on engine cards before staples compete")
    q.add_argument("--sample-top", type=int, default=10,
                   help="how many top candidates enter the probability draw")
    q.add_argument("--temperature", type=float, default=0.35,
                   help="softmax temperature; 0 = deterministic argmax")
    q.add_argument("--rng-seed", type=int, default=0,
                   help="change to get a different deck from the same seed card")
    q.add_argument("--bootstrap", type=int, default=0,
                   help="leave-one-out refinement passes after the build "
                        "(0 = off; each pass also overfits the scorer, so keep it low)")
    q.add_argument("--no-holdout", action="store_true",
                   help="skip the seed-holdout check")
    q.add_argument("--thorough", action="store_true",
                   help="wide search: all 3 lambda restarts, 200 candidates/step, "
                        "beam 8. ~36s instead of ~4s, and measured to be worth "
                        "nothing (+4.02 +/- 16.49 paired) -- the RNG spread is "
                        "bigger. Prefer several --rng-seed values instead.")
    q.add_argument("--resize-top", type=int, default=search.RESIZE_TOP,
                   help="how many leading candidates get every playset size "
                        "priced (default %(default)s)")
    q.add_argument("-v", "--verbose", action="store_true",
                   help="log each search step to stderr")
    q.set_defaults(fn=_cmd_gen)

    q = sub.add_parser("seeds", parents=scoring, help="rank cards by deck-seed potential")
    q.add_argument("-n", type=int, default=30)
    q.add_argument("--card", default=None, help="score one card and show its rank")
    q.add_argument("--monsters", action="store_true")
    q.add_argument("--spells", action="store_true")
    q.add_argument("--validate", type=int, default=0,
                   help="build N decks each from the top/middle/bottom and correlate")
    q.set_defaults(fn=_cmd_seeds)

    q = sub.add_parser("train", help="fit balance coefficients to tournament play rate")
    q.add_argument("--apply", action="store_true", help="write the fitted params.toml")
    q.add_argument("--fetch", action="store_true", help="refresh the decklist cache first")
    q.add_argument("--per-format", type=int, default=150)
    q.add_argument("--rounds", type=int, default=2)
    q.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5],
                   help="one coordinate-descent run per seed, from the same base")
    q.add_argument("--min-seeds", type=int, default=3,
                   help="how many seeds must agree before a value is written")
    q.add_argument("--min-gain", type=float, default=0.001,
                   help="Spearman improvement a move must clear to be accepted")
    q.add_argument("--all-formats", action="store_true",
                   help="fit against all ~100 formats instead of the ROM's era "
                        "(Tengu/Edison/Crow/Trishula)")
    q.add_argument("--no-evidence", action="store_true",
                   help="zero impact.w_evidence for the fit: asks whether the "
                        "model's own reasoning predicts play rate, instead of "
                        "measuring the play-rate lookup against itself.  The "
                        "objective for any tag weight")
    q.set_defaults(fn=_cmd_train)

    q = sub.add_parser("train-deck",
                       help="fit the DECK-level weights (tournament > ROM AI deck)")
    q.add_argument("--apply", action="store_true", help="write the agreed params.toml")
    q.add_argument("--rounds", type=int, default=2)
    q.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5],
                   help="one coordinate-descent run per seed, from the same base")
    q.add_argument("--min-seeds", type=int, default=3,
                   help="how many seeds must agree before a value is written")
    q.add_argument("--min-gain", type=float, default=0.002,
                   help="AUC improvement a move must clear to be accepted")
    q.add_argument("--all-formats", action="store_true",
                   help="fit against all ~100 formats instead of the ROM's era "
                        "(Tengu/Edison/Crow/Trishula)")
    q.set_defaults(fn=_cmd_train_deck)

    q = sub.add_parser("golden", help="run the ground-truth economy assertions")
    q.set_defaults(fn=_cmd_golden)

    q = sub.add_parser("validate", help="validate against the 305 shipped decks")
    q.add_argument("rest", nargs=argparse.REMAINDER)
    q.set_defaults(fn=_cmd_validate)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
