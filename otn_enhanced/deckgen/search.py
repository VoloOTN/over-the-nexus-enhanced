"""Build a deck from a seed card.

Four phases, in the order a human builds:

1. **monsters** — grow to 18-22, each pick scored against the seed *and*
   everything already chosen;
2. **spells/traps** — fill to 40 with cards that are either strong standalone or
   synergistic with the monsters actually chosen;
3. **Extra Deck** — only Synchros whose Level the chosen Tuners and non-Tuners
   can actually make, weighted by how likely that pair is to be in hand;
4. **bundles** — enforced continuously, not as a phase.

Beam search with restarts, because the objective is not submodular (the payoff
and orphan penalties are quadratic / negative), so greedy has no guarantee here.
Restarts sweep ``lambda_synergy`` from "generic good cards" to "hard theme" and
keep the best result, reporting the others as alternates.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field

from otn_enhanced.deckgen import deckscore, synergy
from otn_enhanced.deckgen.bundles import BundleIndex
from otn_enhanced.deckgen.constraints import (
    Limits,
    MonsterFilter,
    legal_addition,
    violations,
)
from otn_enhanced.deckgen.deckstate import DeckState
from otn_enhanced.deckgen.matchindex import MatchIndex
from otn_enhanced.deckgen.model import Card
from otn_enhanced.deckgen.params import Params, default
from otn_enhanced.deckgen.score import Scored

#: How many prefiltered candidates get exact marginal-gain evaluation per step.
CANDIDATE_WIDTH = 200
#: Default for :attr:`GenOptions.resize_top`.
RESIZE_TOP = 24


def _is_real_archetype(name: str | None) -> bool:
    from otn_enhanced.deckgen.text.parse import is_real_archetype

    return is_real_archetype(name)


def _null_log(msg: str) -> None:
    """Default progress sink: say nothing."""


@dataclass
class GenOptions:
    #: Where progress messages go.  `cli gen -v` wires this to stderr so a long
    #: build shows which phase it is in and what it is picking, rather than
    #: sitting silent for minutes.
    log: "callable" = _null_log
    size: int = 40
    extra_size: int = 15
    beam_width: int | None = None
    restarts: list[float] | None = None
    limits: Limits | None = None
    candidate_width: int = CANDIDATE_WIDTH
    seed_copies: int = 3
    #: Quality bar for the engine phase, as marginal gain per slot.  The engine
    #: is built first because staples are worth ~+8 impact per slot against ~+0.7
    #: for an engine piece, so a pure marginal-gain search never tries the engine
    #: at all and leaves three dead Rekindlings in a goodstuff pile.
    #:
    #: A *cutoff* rather than a card count: a fixed quota forced whatever was
    #: left into a thin engine (three Sorcerer of Dark Magic at impact -3.53 went
    #: into a Chaos deck purely to reach the target).  A rich engine now takes as
    #: many cards as clear the bar and a thin one simply stops early.
    engine_cutoff: float = 0.0
    #: Ceiling, so a very broad engine cannot consume the whole deck before the
    #: staples get a look.
    engine_max: int = 24
    #: How many top candidates enter the probability draw at each step.
    sample_top: int = 10
    #: How many leading candidates get their OTHER playset sizes measured.
    #:
    #: Pricing all of 3/2/1 copies for all ``candidate_width`` candidates is
    #: three exact deck scores each and ~600 per beam per step, of which only
    #: ``sample_top`` are ever drawn from.  So every candidate is priced once at
    #: the size ``_copies_prior`` puts first (the empirical tournament count when
    #: there is one), and only the leaders are re-priced at the other sizes.
    #: Kept well above ``sample_top`` so a card whose better size would promote
    #: it into the draw still gets the chance.
    resize_top: int = RESIZE_TOP
    #: Softmax temperature over marginal gain.  0 = deterministic argmax.
    temperature: float = 0.35
    #: Seeded so a build is reproducible; change it to explore alternatives.
    rng: "random.Random" = field(default_factory=lambda: random.Random(0))
    #: Leave-one-out refinement passes after the deck is built.  0 = off.
    #: Bounded because it both thrashes and overfits the scorer; see bootstrap().
    bootstrap_rounds: int = 0
    #: Check whether the finished deck would ask for its own seeds back.
    seed_holdout: bool = True
    #: Cards that must NEVER appear in the generated deck, by name or cid.
    #: Applied as a zero copy limit — see Limits.forbidding for why.
    anti_seeds: list = field(default_factory=list)
    #: Restrict which monsters the build may consider, by Type and/or Attribute.
    #: Applied the same way anti-seeds are, as a zero copy limit on every monster
    #: the filter excludes.  Empty (the default) constrains nothing.
    monster_filter: MonsterFilter = field(default_factory=MonsterFilter)


@dataclass
class BuildStats:
    """Where a build spent its wall clock, and on how many deck scores.

    Almost all of a build's time is inside ``deckscore.score``, so "seconds" and
    "score calls" together localise a slowdown immediately: a phase that got
    slower at constant call count is a scoring regression, and one that got
    slower because the count exploded is a search-shape regression.  Guessing at
    which of the two it was is how the last round of perf work started.
    """

    rows: list[tuple[str, float, int]] = field(default_factory=list)

    def record(self, name: str, seconds: float, calls: int) -> None:
        self.rows.append((name, seconds, calls))

    @property
    def total(self) -> float:
        return sum(s for _, s, _ in self.rows)

    def format(self) -> list[str]:
        out = [f"  {'phase':22} {'seconds':>9} {'score calls':>12} {'us/call':>9}"]
        for name, secs, calls in self.rows:
            per = f"{secs / calls * 1e6:9.0f}" if calls else " " * 9
            out.append(f"  {name:22} {secs:9.2f} {calls:12,} {per}")
        total_calls = sum(c for _, _, c in self.rows)
        out.append(f"  {'TOTAL':22} {self.total:9.2f} {total_calls:12,}")
        return out


class _Timer:
    """Context manager that books one phase into a :class:`BuildStats`."""

    def __init__(self, stats: BuildStats, name: str, log):
        self.stats, self.name, self.log = stats, name, log

    def __enter__(self):
        self.t0 = time.time()
        self.c0 = deckscore.CALLS
        return self

    def __exit__(self, *exc):
        secs = time.time() - self.t0
        calls = deckscore.CALLS - self.c0
        self.stats.record(self.name, secs, calls)
        rate = f", {secs / calls * 1e6:.0f}us/call" if calls else ""
        self.log(f"    -> {self.name}: {secs:.1f}s ({calls:,} score calls{rate})")
        return False


@dataclass
class GeneratedDeck:
    seed: Scored
    state: DeckState
    score: deckscore.DeckScore
    lambda_synergy: float
    bundle_debt: list[str]
    #: Every seed the deck was built around; ``seed`` is the first of them.
    seeds: list = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    alternates: list["GeneratedDeck"] = field(default_factory=list)
    #: Swaps made by the leave-one-out refinement, in order.
    swaps: list[str] = field(default_factory=list)
    #: (seed name, rank the deck would re-pick it at, marginal gain).
    holdout: list = field(default_factory=list)
    #: Wall clock and score-call count per phase; rendered by report.render.
    stats: "BuildStats" = field(default_factory=lambda: BuildStats())
    #: Cards the caller banned from this build.
    anti_seeds: list = field(default_factory=list)
    #: The Type/Attribute restriction this build ran under, for the report.
    monster_filter: MonsterFilter = field(default_factory=MonsterFilter)
    #: Seeds the filter would have excluded but which were kept anyway.
    filter_exempt: list = field(default_factory=list)
    #: Cards added by the force-fill guarantee because the search stopped short.
    #: Non-empty means the search stalled — worth reading as a signal, not just
    #: as a list of cards.
    filled: list = field(default_factory=list)

    @property
    def main(self) -> dict[int, int]:
        return self.state.copies

    @property
    def extra(self) -> dict[int, int]:
        return self.state.extra


@dataclass
class _Beam:
    state: DeckState
    value: float


def _copies_prior(
    cand: Scored, idx: MatchIndex, p: Params, playset: dict[int, int] | None = None
) -> list[int]:
    """Playset sizes worth trying.

    All of these get evaluated — the order only matters for tie-breaking — but
    when tournament data says how many copies of this card people actually run,
    that number goes first.  Deck builders run 3 Pot of Duality and 1 Monster
    Reborn, and that is a fact about the card no marginal-gain calculation
    reliably rediscovers.
    """
    empirical = (playset or {}).get(cand.cid)
    if empirical:
        rest = [k for k in (3, 2, 1) if k != empirical]
        return [empirical, *rest]
    findable = idx.searchability(cand.cid)
    heavy = cand.card.is_monster and (cand.card.level or 0) >= 7
    if heavy or findable >= 8:
        return [1, 2, 3]
    if findable >= 3:
        return [2, 3, 1]
    return [3, 2, 1]


def _sample_picks(best, width: int, opts) -> list:
    """Choose which candidates to expand, by probability rather than by rank.

    Taking the argmax every step makes the search brittle: two cards a hair
    apart in marginal gain are treated as decisively different, and the same
    deck comes out every run so nothing explores the alternatives. The top
    ``sample_top`` candidates are instead softmaxed into probabilities and drawn
    without replacement.

    Temperature controls it: ``0`` reproduces the old argmax behaviour exactly,
    higher values flatten toward uniform. The RNG is seeded, so a run is still
    reproducible — you get variety across seeds, not across invocations.
    """
    pool = best[: max(width, opts.sample_top)]
    if opts.temperature <= 0 or len(pool) <= width:
        return pool[:width]

    rng = opts.rng
    remaining = list(pool)
    chosen = []
    while remaining and len(chosen) < width:
        top = max(g for g, _, _ in remaining)
        weights = [math.exp((g - top) / opts.temperature) for g, _, _ in remaining]
        total = sum(weights)
        if total <= 0:
            chosen.append(remaining.pop(0))
            continue
        r = rng.random() * total
        acc = 0.0
        for i, w in enumerate(weights):
            acc += w
            if acc >= r:
                chosen.append(remaining.pop(i))
                break
        else:
            chosen.append(remaining.pop())
    return chosen


def _mined_playsets(by_cid: dict[int, Card]) -> dict[int, int]:
    """How many copies tournament decks actually run of each card, if mined.

    Dropped for monsters when the ROM's card properties have been altered: "run
    three of this cid" is a fact about the card that *used* to sit there, and
    after a randomiser run it says nothing about the one that does now.
    """
    try:
        from otn_enhanced.deckgen import cardpool, mining

        cards = list(by_cid.values())
        playset = mining.load(cards).playset
    except (FileNotFoundError, OSError, KeyError):
        return {}

    if not cardpool.is_randomised(cards):
        return playset
    return {
        cid: n for cid, n in playset.items()
        if cid in by_cid and not by_cid[cid].is_monster
    }


def _level_value(cards) -> dict[int, float]:
    """What a Synchro at each Level is worth.

    Weighted by tournament play rate — but that weighting is **per cid**, so it
    only means anything while each cid still holds the Synchro that earned it.
    ``_mined_playsets`` has always dropped its per-cid evidence after a
    randomiser run and this did not, so a randomised pool kept rating Level 8
    highly because Stardust Dragon *used* to be there.  Falls back to the
    unweighted Level set, which is a pool fact and stays true.
    """
    from otn_enhanced.deckgen.power import synchro_level_value

    try:
        from otn_enhanced.deckgen import cardpool, mining

        if cardpool.is_randomised(list(cards)):
            return synchro_level_value(cards)
        return synchro_level_value(cards, mining.load(cards).play_rate)
    except (FileNotFoundError, OSError, KeyError):
        return synchro_level_value(cards)


def seed_affinity(
    seed: Scored, scored: dict[int, Scored], idx: MatchIndex, level_value=None
) -> dict[int, float]:
    """How related each pool card is to the seed, in 0..1.

    Computed once per generate() and read in the inner loop, so anchoring the
    synergy term to the seed costs nothing per candidate.  Two hops: cards the
    seed directly wants (or that want the seed), then cards sharing the archetype
    or attribute of that first ring — which is how a Rekindling deck reaches
    Flamvell Firedog *and* the Pyro/FIRE support around it.
    """
    direct: dict[int, float] = {}
    for s in scored.values():
        v = synergy.pair(seed, s, idx, level_value)
        if v > 0:
            direct[s.cid] = v
    if not direct:
        return {}
    top = max(direct.values())
    affinity = {cid: min(1.0, v / top) for cid, v in direct.items()}
    affinity[seed.cid] = 1.0

    # Second ring: the themes the strongly-related cards belong to.
    core = [scored[c] for c, v in affinity.items() if v >= 0.5 and c in scored]
    archetypes = {
        s.card.archetype for s in core
        if s.card.archetype and _is_real_archetype(s.card.archetype)
    }
    attributes = {s.card.attribute for s in core if s.card.attribute}
    races = {s.card.race for s in core if s.card.race}
    for s in scored.values():
        if affinity.get(s.cid, 0.0) >= 0.5:
            continue
        bump = 0.0
        if s.card.archetype and s.card.archetype in archetypes:
            bump = max(bump, 0.8)
        if s.card.attribute and s.card.attribute in attributes:
            bump = max(bump, 0.5)
        if s.card.race and s.card.race in races:
            bump = max(bump, 0.4)
        if bump:
            affinity[s.cid] = max(affinity.get(s.cid, 0.0), bump)
    return affinity


#: A want matching more cards than this describes no engine.  Monster Reborn
#: wants "1 monster in either GY" — 2,478 cards — and admitting that made the
#: engine over half the pool, so engine *size* rewarded vagueness instead of
#: theme.  Matched to matchindex.DEDICATED_MAX for the same reason.
ENGINE_MAX_MATCHES = 200


def engine_pool(
    seed: Scored, scored: dict[int, Scored], idx: MatchIndex
) -> set[int]:
    """Cards that are the seed's engine, by a *direct* link — not fuzzy affinity.

    Membership means one of:

    * the card satisfies one of the seed's own want predicates (for Rekindling,
      the FIRE monsters with 200 DEF it revives);
    * the card's want is satisfied by the seed;
    * it shares the seed's archetype.

    Deliberately narrower than :func:`seed_affinity`, which spreads through
    shared attribute and race and ends up marking most of the pool as related.
    """
    pool: set[int] = {seed.cid}
    for pred, _ in seed.parsed.wants:
        if idx.count(pred) <= ENGINE_MAX_MATCHES:
            pool.update(idx.matching_cids(pred))
    for s in scored.values():
        if not s.card.playable or s.card.is_extra:
            continue
        if any(
            idx.satisfies(pred, seed.cid) and idx.count(pred) <= ENGINE_MAX_MATCHES
            for pred, _ in s.parsed.wants
        ):
            pool.add(s.cid)
        if (
            seed.card.archetype
            and s.card.archetype == seed.card.archetype
            and _is_real_archetype(seed.card.archetype)
        ):
            pool.add(s.cid)
    return pool


def _prefilter(
    state: DeckState,
    seed: Scored,
    scored: dict[int, Scored],
    idx: MatchIndex,
    *,
    want: str,
    width: int,
    engine: set[int] | None = None,
    level_value=None,
    seed_pair: dict[int, float] | None = None,
    limits: Limits | None = None,
) -> list[Scored]:
    """Cheaply rank the pool, so exact scoring only runs on plausible picks.

    *limits* is consulted HERE, not only in ``legal_addition`` downstream,
    because this is a top-``width`` cut: a card at 0 copies would otherwise
    occupy one of the ~60 candidate slots and be rejected afterwards, so a ban
    that covers most of the pool leaves a window of nothing but forbidden cards
    and the phase stalls with "no legal additions left".  With one or two
    anti-seeds that only wasted a slot; a Type/Attribute filter bans thousands
    and stopped the monster phase dead at 9 monsters.
    """
    recent = [scored[cid] for cid in list(state.copies)[-3:] if cid in scored]
    out: list[tuple[float, Scored]] = []
    for s in scored.values():
        if not s.card.playable or s.card.is_extra:
            continue
        if limits is not None and limits.max_copies(s.cid) <= 0:
            continue
        if want == "engine" and s.cid not in (engine or ()):
            continue
        if want == "monster" and not s.card.is_monster:
            continue
        if want == "spelltrap" and s.card.is_monster:
            continue
        # pair(seed, card) is constant across steps; recomputing it for all
        # 4,076 cards on every step was the largest remaining cost.
        score = s.impact + (
            seed_pair[s.cid] if seed_pair is not None
            else synergy.pair(seed, s, idx, level_value)
        )
        for r in recent:
            score += 0.5 * synergy.pair(r, s, idx, level_value)
        out.append((score, s))
    out.sort(key=lambda t: -t[0])
    return [s for _, s in out[:width]]


def refinement_pool(
    seeds: list[Scored],
    scored: dict[int, Scored],
    idx: MatchIndex,
    state: DeckState,
    engine: set[int],
    level_value,
    width: int,
    limits: Limits | None = None,
) -> list[Scored]:
    """The pool that :func:`bootstrap` and :func:`seed_holdout` rank against.

    Ranked by ``impact + best seed synergy`` — the same quantity :func:`_prefilter`
    drives the build with — and *not* by raw impact.

    Ranking by raw impact was a false negative by construction for every engine
    piece.  The top 200 cards by impact are the 200 best staples in the game, so
    Hecatrice (impact +1.16) and Valhalla itself (+0.06) were never in it: the
    holdout check reported "NOT competitive" for a seed whose real marginal was
    +3.58, and bootstrap could only ever swap a themed card *out* for a staple,
    which is most of the drift the theme tolerance was added to fight.

    The seeds, everything already in the deck, and the seed's engine are admitted
    unconditionally — "would this deck take its own seed back?" is not a question
    a list truncated by staple quality can answer at all.  That unconditional
    admission is also why *limits* filters the ranked body but not ``keep``: an
    off-filter seed is exempt from the ban precisely so the deck can hold it, and
    the holdout must still be able to rank it.
    """
    keep = {s.cid for s in seeds} | set(state.copies) | set(engine)
    ranked: list[tuple[float, Scored]] = []
    for s in scored.values():
        if not s.card.playable or s.card.is_extra:
            continue
        if limits is not None and limits.max_copies(s.cid) <= 0 and s.cid not in keep:
            continue
        affinity = max(
            (synergy.pair(seed, s, idx, level_value) for seed in seeds), default=0.0
        )
        ranked.append((s.impact + affinity, s))
    ranked.sort(key=lambda t: -t[0])

    out = [s for _, s in ranked[:width]]
    seen = {s.cid for s in out}
    out.extend(
        s
        for cid in keep
        if cid not in seen
        and (s := scored.get(cid)) is not None
        and s.card.playable
        and not s.card.is_extra
    )
    return out


def _without(state: DeckState, scored: dict[int, Scored], cid: int, k: int) -> DeckState:
    """A copy of *state* with *k* fewer copies of *cid*, rebuilt from scratch.

    DeckState has no remove(): add() updates about twenty accumulators, several
    of them non-invertible (``cheatable`` is a set with no record of which pair
    put a cid in it, and want ``askers`` is a Counter over contributors).  An
    approximate unwind would silently corrupt every score downstream, so this
    replays the deck instead — the same construction path validate/run.py uses.
    """
    fresh = DeckState(
        idx=state.idx,
        seed_affinity=state.seed_affinity,
        level_value=state.level_value,
        engine_cids=state.engine_cids,
    )
    for other, n in state.copies.items():
        n = n - k if other == cid else n
        s = scored.get(other)
        if s is not None and n > 0:
            fresh.add(s, n)
    for other, n in state.extra.items():
        s = scored.get(other)
        if s is not None and n > 0:
            fresh.add(s, n)
    return fresh


def bootstrap(
    state: DeckState,
    scored: dict[int, Scored],
    idx,
    p: Params,
    limits: Limits,
    candidates: list[Scored],
    rounds: int,
    log=None,
    protect: frozenset[int] = frozenset(),
) -> list[str]:
    """Leave-one-out refinement: is every card still the best card for the slot?

    The construction search is greedy and order-dependent — a card picked at
    slot 3 was chosen against a deck that did not yet exist, and by slot 30 it
    may no longer be the right answer.  Each round drops one copy of each card
    in turn and re-asks what the best occupant of that slot would be; a strictly
    better answer replaces it.

    Bounded on purpose.  Left to run free this thrashes: A is swapped for B,
    which changes the deck so that A now beats B, forever — and each pass also
    fits the deck harder to its own scoring quirks, which is overfitting the
    objective rather than improving the deck.  Hence *rounds*.
    """
    #: Terms that encode "this deck is about something".  A swap that raises the
    #: total by trading a themed card for a staple lowers these, which is exactly
    #: the drift observed when refinement ran unguarded.
    theme_terms = (
        "synergy_wants", "synergy_cycles", "synergy_combo",
        "concentration", "context_payoff", "synergy_flip",
    )

    def theme_of(st: DeckState) -> float:
        terms = deckscore.score(st, scored, p).terms
        return sum(terms.get(k, 0.0) for k in theme_terms)

    def gap_of(st: DeckState) -> float:
        """How badly the deck misses the interaction band (0 = inside it)."""
        return -deckscore.score(st, scored, p).terms.get("penalty_role_balance", 0.0)

    tol = float(p["deck.bootstrap_theme_tolerance"])
    look = int(p["deck.bootstrap_lookahead"])
    swaps: list[str] = []
    for round_no in range(max(0, rounds)):
        before = deckscore.score(state, scored, p)
        before_theme = sum(before.terms.get(k, 0.0) for k in theme_terms)
        before_gap = gap_of(state)

        # Score every swap the deck admits, then walk them best-first.
        ranked: list[tuple[float, int, Scored]] = []
        for cid in list(state.copies):
            if cid in protect or state.copies.get(cid, 0) <= 0:
                continue
            held = scored.get(cid)
            if held is None:
                continue
            trial = _without(state, scored, cid, 1)
            base = deckscore.score(trial, scored, p).total
            keep = deckscore.marginal(trial, held, 1, scored, p, base=base)
            for cand in candidates:
                if cand.cid == cid or not legal_addition(trial, cand, 1, limits, p):
                    continue
                gain = deckscore.marginal(trial, cand, 1, scored, p, base=base) - keep
                if gain > 1e-6:
                    ranked.append((gain, cid, cand))
        if not ranked:
            break
        ranked.sort(key=lambda r: -r[0])

        # Take the best swap that is ALLOWED, rather than stopping at the best
        # swap outright.  Stopping meant one theme-costly staple hid every
        # thematic upgrade ranked below it -- and a themed card that improves the
        # deck is exactly what refinement should be finding.
        picked = None
        for gain, cid, cand in ranked[:look]:
            after = _without(state, scored, cid, 1)
            after.add(cand, 1)
            d_theme = sum(
                deckscore.score(after, scored, p).terms.get(k, 0.0) for k in theme_terms
            ) - before_theme
            # A staple that costs theme is still right when it fills a hole the
            # deck actually has: an all-engine deck with no interaction loses to
            # one that has some, and the role-balance term is what measures that.
            fills_gap = gap_of(after) < before_gap - 1e-6
            if d_theme >= -tol or fills_gap:
                picked = (gain, cid, cand, after, d_theme, fills_gap)
                break
        if picked is None:
            if log:
                log(f"  bootstrap exhausted r{round_no + 1}: no swap in the top "
                    f"{look} keeps the theme")
            break

        gain, cid, cand, after, d_theme, fills_gap = picked
        held = scored[cid]
        state.__dict__.update(after.__dict__)
        why = " fills-gap" if fills_gap else ""
        swaps.append(
            f"r{round_no + 1}: {held.name} -> {cand.name} "
            f"({gain:+.3f}, theme {d_theme:+.2f}{why})"
        )
        if log:
            log(f"  bootstrap {swaps[-1]}")
    return swaps


def seed_holdout(
    state: DeckState,
    seeds: list[Scored],
    scored: dict[int, Scored],
    p: Params,
    limits: Limits,
    candidates: list[Scored],
) -> list[tuple[str, int, float]]:
    """Would the finished deck ask for its own seeds back?

    Strip every copy of a seed, then rank what the deck now wants most.  If the
    seed comes back at or near the top, the deck really was built around it; if
    it ranks 200th, the search drifted onto a generically good pile that happens
    to contain the seed.  Returns ``(name, rank, marginal)`` per seed, rank 1
    being the best possible answer and ``-1`` meaning it was not competitive.

    *candidates* must come from :func:`refinement_pool`.  Ranked against a
    top-by-impact list instead, a seed that is not itself a staple gets rank -1
    whatever its marginal — which is a verdict about the list, not the deck.
    """
    out: list[tuple[str, int, float]] = []
    for seed in seeds:
        trial = _without(state, scored, seed.cid, state.copies.get(seed.cid, 0))
        base = deckscore.score(trial, scored, p).total
        ranked = []
        for cand in candidates:
            if not legal_addition(trial, cand, 1, limits, p):
                continue
            ranked.append((deckscore.marginal(trial, cand, 1, scored, p, base=base), cand.cid))
        ranked.sort(reverse=True)
        mine = deckscore.marginal(trial, seed, 1, scored, p, base=base)
        rank = next((i + 1 for i, (_g, c) in enumerate(ranked) if c == seed.cid), -1)
        out.append((seed.name, rank, mine))
    return out


def _proper_fusion_summoner(pc) -> bool:
    """Does this card actually *Fusion Summon*, or merely Special Summon from
    the Extra Deck?  Polymerization does the former, Instant Fusion the latter."""
    return any(
        c.verb == "special_summon" and "fusion summon" in (c.raw or "").lower()
        for c in pc.clauses
    )


def _legal_target_for(cand: Scored, want, scored: dict[int, Scored]) -> bool:
    """Can the cards that raised *want* actually Summon *cand*?

    An Extra Deck monster tagged ``summon_locked`` — "Must be Fusion Summoned and
    cannot be Special Summoned by other ways" — is a fine Polymerization target
    and an **illegal** Instant Fusion one.  The distinction is a property of the
    *asker*, not of the candidate, so it cannot live in the want predicate:
    Elemental HERO Mariner must stay reservable for a deck running Polymerization
    while being refused to Instant Fusion.

    Reported from play: Instant Fusion kept reserving Mariner, which the 2011 ROM
    will not let it Summon.  (Its modern erratum would; this engine predates it.)
    """
    if "summon_locked" not in cand.parsed.tags:
        return True
    return any(
        (a := scored.get(cid)) is not None and _proper_fusion_summoner(a.parsed)
        for cid in want.askers
    )


def _wanted_extra(
    state: DeckState, scored: dict[int, Scored], limits: Limits
) -> list[Scored]:
    """Extra Deck cards that a card already in the main deck explicitly asks for.

    One card per unmet want, best-impact answer first, most-wanted want first.
    Returned in the order they should be reserved.
    """
    out: list[tuple[float, Scored]] = []
    taken: set[int] = set()
    ranked = sorted(
        (w for w in state.wants.values() if not w.met),
        key=lambda w: -(w.weight * w.exclusivity),
    )
    for want in ranked:
        # Only reserve for wants the main deck CANNOT answer.  "1 Level 5 or
        # lower Fusion Monster" has no main-deck answer anywhere in the pool, so
        # the Extra Deck is the only place it can come from; "3 DARK monsters" is
        # the main deck's job and spending an Extra slot on it would be waste.
        if any(
            s.card.playable and not s.card.is_extra and state.idx.satisfies(want.pred, s.cid)
            for s in scored.values()
        ):
            continue
        best: Scored | None = None
        best_rank = float("-inf")
        for s in scored.values():
            if not s.card.is_extra or not s.card.playable:
                continue
            if s.cid in taken or state.extra.get(s.cid):
                continue
            if limits.max_copies(s.cid) < 1:
                continue
            if not state.idx.satisfies(want.pred, s.cid):
                continue
            if not _legal_target_for(s, want, scored):
                continue
            # A Fusion whose materials this deck does not run is not an answer.
            #
            # The fallback pass at the bottom of `_fill_extra` has always
            # applied `_fusion_ready`; this reservation pass did not, so
            # Overload Fusion's "1 DARK Machine Fusion Monster" want reserved
            # Chimeratech Overdragon into a deck holding no Cyber Dragon and no
            # Machines.  Phase 3 runs after the main deck is locked, so the
            # Fusion's own material wants arrive too late to pull anything in —
            # the only place to catch it is here, by refusing to reserve it.
            #
            # If nothing ready exists the want simply stays unmet, and the
            # orphan penalty then prices the card that asked for it, which is
            # the honest outcome: Overload Fusion in a deck with no Machines IS
            # a dead card.
            if not s.card.is_synchro and not _fusion_ready(state, s):
                continue
            # Same depth weighting as the fallback pass: prefer the answer whose
            # materials this deck actually runs several of.
            rank = s.impact * (1.0 if s.card.is_synchro else _material_depth(state, s))
            if best is None or rank > best_rank:
                best, best_rank = s, rank
        if best is not None:
            taken.add(best.cid)
            out.append((want.weight * want.exclusivity, best))
    return [s for _, s in out]


def _extra_candidates(
    state: DeckState, scored: dict[int, Scored], p: Params
) -> list[tuple[Scored, float]]:
    """Rank Synchros by impact x how reachable their Level actually is."""
    total_main = max(1, state.main_total)

    def seen_probability(copies: int) -> float:
        """Chance of opening at least one copy in five cards."""
        if copies <= 0:
            return 0.0
        miss = 1.0
        for i in range(5):
            miss *= max(0.0, (total_main - copies - i)) / max(1, (total_main - i))
        return 1.0 - miss

    tuner_p = {lvl: seen_probability(n) for lvl, n in state.tuner_levels.items()}
    non_p = {lvl: seen_probability(n) for lvl, n in state.non_tuner_levels.items()}

    reach: dict[int, float] = {}
    for tl, tp in tuner_p.items():
        for nl, np_ in non_p.items():
            reach[tl + nl] = max(reach.get(tl + nl, 0.0), tp * np_)
            for nl2, np2 in non_p.items():
                lvl = tl + nl + nl2
                reach[lvl] = max(reach.get(lvl, 0.0), tp * np_ * np2 * 0.6)

    # A Synchro is only a candidate if some Tuner in the deck may legally make
    # it.  Level arithmetic alone put Stardust Dragon in a deck whose only Level
    # 4 Tuner was Debris Dragon -- which cannot be material for a non-Dragon, and
    # cannot pair with a Level 4 partner either, so the 4+4=8 line it was ranked
    # on does not exist.
    legal = state.summonable_synchros(scored)
    out = [
        (s, reach.get(s.card.level or 0, 0.0))
        for s in scored.values()
        if s.card.is_synchro and s.card.playable and s.card.level and s.cid in legal
    ]
    return sorted((o for o in out if o[1] > 0.01), key=lambda t: -(t[0].impact * t[1]))


def _grow(
    beams: list[_Beam],
    seed: Scored,
    scored: dict[int, Scored],
    idx: MatchIndex,
    bundle_idx: BundleIndex,
    by_cid: dict[int, Card],
    p: Params,
    opts: GenOptions,
    lam: float,
    *,
    want: str,
    stop: callable,
    engine: set[int] | None = None,
) -> list[_Beam]:
    """Extend every beam until *stop* holds, keeping the best ``beam_width``."""
    import time

    limits = opts.limits or Limits.flat(int(p["deck.max_copies"]))
    width = opts.beam_width or int(p["deck.beam_width"])
    playset = _mined_playsets(by_cid)
    level_value = _level_value(list(by_cid.values()))
    seed_pair = {
        s.cid: synergy.pair(seed, s, idx, level_value) for s in scored.values()
    }
    step = 0
    t0 = time.time()
    seen_before = set(beams[0].state.copies) if beams else set()

    while not all(stop(b.state) for b in beams):
        before_total = max(b.state.main_total for b in beams) if beams else 0
        nxt: dict[frozenset, _Beam] = {}
        for beam in beams:
            if stop(beam.state):
                nxt.setdefault(beam.state.signature(), beam)
                continue
            base = beam.value
            best: list[tuple[float, Scored, int]] = []
            #: (stage-1 gain, candidate, size priced, sizes not yet priced)
            staged: list[tuple[float, Scored, int, list[int]]] = []
            for cand in _prefilter(
                beam.state, seed, scored, idx, want=want,
                width=opts.candidate_width, engine=engine,
                level_value=level_value, seed_pair=seed_pair, limits=limits,
            ):
                # Every legal playset size still gets measured for the cards that
                # can actually be picked — breaking after the first size the
                # prior suggested is why the Rekindling deck ran two Flamvell
                # Firedog rather than three, and per-slot marginal gain only
                # makes 3-ofs and 1-ofs comparable if both are measured.  What
                # changed is *which* cards get the full sweep; see resize_top.
                legal = [
                    k for k in _copies_prior(cand, idx, p, playset)
                    if legal_addition(beam.state, cand, k, limits, p)
                ]
                if not legal:
                    continue
                # Stage 1: one exact price per candidate, at the prior's choice.
                gain = _bundled_marginal(
                    beam.state, cand, legal[0], scored, idx, bundle_idx, by_cid,
                    p, lam, base, limits,
                )
                if gain is not None:
                    staged.append((gain, cand, legal[0], legal[1:]))

            # Stage 2: re-price only the leaders at their other playset sizes.
            # Everything below `resize_top` keeps its stage-1 size, which costs
            # nothing real: it is far outside the `sample_top` draw either way.
            staged.sort(key=lambda t: -t[0])
            for rank, (gain, cand, k, rest) in enumerate(staged):
                if rank < opts.resize_top:
                    for k2 in rest:
                        alt = _bundled_marginal(
                            beam.state, cand, k2, scored, idx, bundle_idx,
                            by_cid, p, lam, base, limits,
                        )
                        if alt is not None and alt > gain:
                            gain, k = alt, k2
                # The engine phase has a card *count* target, so with a thin
                # engine pool it used to keep adding whatever was left --
                # three Sorcerer of Dark Magic at impact -3.53 went into a
                # Chaos deck purely to reach engine_min.  A card that makes
                # the deck worse is never engine, however short we are.
                if want == "engine" and gain <= opts.engine_cutoff:
                    continue
                best.append((gain, cand, k))
            if not best:
                nxt.setdefault(beam.state.signature(), beam)
                continue
            best.sort(key=lambda t: -t[0])
            for gain, cand, k in _sample_picks(best, width, opts):
                trial = beam.state.clone()
                trial.add(cand, k)
                _autofill_bundles(trial, cand, scored, bundle_idx, by_cid, limits, p)
                value = deckscore.score(trial, scored, p, lambda_synergy=lam).total
                value += bundle_idx.adjust(trial, by_cid, float(p["deck.p_bundle"]))[0]
                sig = trial.signature()
                if sig not in nxt or nxt[sig].value < value:
                    nxt[sig] = _Beam(state=trial, value=value)
        beams = sorted(nxt.values(), key=lambda b: -b.value)[:width]
        if not beams:
            break
        # If no beam grew this round, nothing legal is left to add and `stop`
        # will never become true — the engine phase on a seed whose engine pool
        # is exhausted (or was only a card or two to begin with) otherwise spins
        # forever, which is what hung the seed-ranker validation.
        if max(b.state.main_total for b in beams) <= before_total:
            opts.log(f"    [{want:9}] no legal additions left; ending phase")
            break
        step += 1
        lead = beams[0].state
        picked = set(lead.copies) - seen_before
        names = ", ".join(
            f"{lead.copies[c]}x {by_cid[c].name}" for c in picked if c in by_cid
        )
        seen_before = set(lead.copies)
        elapsed = time.time() - t0
        opts.log(
            f"    [{want:9}] step {step:2}  {lead.main_total:2}/{opts.size} cards "
            f"({lead.monsters}m/{lead.spells}s/{lead.traps}t)  "
            f"score {beams[0].value:+8.2f}  {elapsed:5.1f}s"
            + (f"  + {names}" if names else "")
        )
    return beams


def force_fill_main(
    state: DeckState,
    scored: dict[int, Scored],
    p: Params,
    limits: Limits,
    log=_null_log,
) -> list[str]:
    """Top the main deck up to exactly ``deck.size``, whatever the search left.

    The beam phases can stop short, and a deck that is not 40 cards is not a
    deck: the ROM will not accept it and ``violations`` rejects it.  Every stall
    has the same shape — the phase reports "no legal additions left" because
    *its* candidate window is exhausted — so this pass ignores the window and
    ranks the **whole** pool by impact, which is what makes it a guarantee
    rather than one more thing that can come up short.

    Two passes, and the order is the point:

    1. Honour every rule, monsters first while the deck is under
       ``deck.min_monsters``.  A short deck is usually short *because* it is
       monster-starved, and the reserved slots only free up once the minimum is
       met, so filling monsters first is what unblocks the Spells and Traps.
    2. If it is still short, drop the monster reservation (see
       ``legal_addition``) and fill with anything legal.  Copy limits,
       ``max_monsters`` and ``max_traps`` are still absolute — this pass trades
       the *ratio* preference for the *size* requirement, never legality.

    Returns what it added, for the report.  An empty list is the good case: the
    search filled the deck on its own.
    """
    size = int(p["deck.size"])
    min_monsters = int(p["deck.min_monsters"])
    # Impact alone, not marginal gain: the deck is already broken by the time
    # this runs, and a full pass of exact deck scoring per slot over the whole
    # pool costs more than the situation is worth.
    ranked = sorted(
        (s for s in scored.values() if s.card.playable and not s.card.is_extra),
        key=lambda s: -s.impact,
    )
    added: list[str] = []

    def best(*, monsters_only: bool, reserve: bool) -> Scored | None:
        return next(
            (
                s
                for s in ranked
                if (s.card.is_monster or not monsters_only)
                and legal_addition(state, s, 1, limits, p, reserve_monsters=reserve)
            ),
            None,
        )

    for reserve in (True, False):
        while state.main_total < size:
            short_on_monsters = state.monsters < min_monsters
            pick = best(monsters_only=short_on_monsters, reserve=reserve)
            if pick is None and short_on_monsters:
                # No monster can be added at all — the filter, the copy limits or
                # max_monsters have closed that door.  Take the size over the
                # ratio; `violations` still reports the monster count, so the
                # compromise is visible rather than silent.
                pick = best(monsters_only=False, reserve=reserve)
            if pick is None:
                break
            state.add(pick, 1)
            added.append(pick.name)
        if state.main_total >= size:
            break

    if added:
        log(f"  force-fill main: +{len(added)} to reach {state.main_total}/{size}")
    if state.main_total < size:
        log(f"  force-fill main: STILL SHORT at {state.main_total}/{size} — "
            f"nothing legal left in the pool")
    return added


def force_fill_extra(
    state: DeckState,
    scored: dict[int, Scored],
    p: Params,
    opts: GenOptions,
    limits: Limits,
    log=_null_log,
) -> list[str]:
    """Top the Extra Deck up to exactly ``extra_size``.

    :func:`_fill_extra` deliberately leaves slots empty rather than reserve a
    boss the deck cannot Summon, and for the *main* deck that instinct is right
    — a dead card there is a card you draw.  The Extra Deck is never drawn, so
    an unusable slot costs nothing and an empty one wastes a free option.

    Ranked so the preference still gets first refusal: monsters this deck can
    actually put on the field (a legally Summonable Synchro, or a Fusion whose
    materials it runs) come first, and only what is left over is filled purely
    on impact.  Breadth before depth — a second copy of something is only taken
    once every distinct option has been offered a slot.
    """
    target = opts.extra_size
    usable = state.summonable_synchros(scored)
    ranked = sorted(
        (s for s in scored.values() if s.card.is_extra and s.card.playable),
        key=lambda s: (
            not (s.cid in usable or _fusion_ready(state, s)),
            -s.impact,
        ),
    )
    added: list[str] = []
    while sum(state.extra.values()) < target:
        room = [s for s in ranked if state.extra.get(s.cid, 0) < limits.max_copies(s.cid)]
        if not room:
            break
        pick = next((s for s in room if s.cid not in state.extra), room[0])
        state.add(pick, 1)
        added.append(pick.name)

    have = sum(state.extra.values())
    if added:
        log(f"  force-fill extra: +{len(added)} to reach {have}/{target}")
    if have < target:
        # Not a stall — the pool is simply out of legal Extra Deck cards, which
        # under a narrow --allowed-types is the filter doing its job.  Say which,
        # so a short Extra Deck never reads as a search failure.
        log(f"  force-fill extra: {have}/{target} — the pool has no other legal "
            f"Extra Deck card left (copy limits / monster filter exhausted)")
    return added


def _bundled_marginal(
    state: DeckState,
    cand: Scored,
    k: int,
    scored: dict[int, Scored],
    idx: MatchIndex,
    bundle_idx: BundleIndex,
    by_cid: dict[int, Card],
    p: Params,
    lam: float,
    base: float,
    limits: Limits | None = None,
) -> float | None:
    """Marginal gain including any partners the candidate drags in.

    Returns ``None`` when a ``hard`` bundle cannot be satisfied — the anchor is
    then rejected rather than added as a brick.
    """
    trial = state.clone()
    trial.add(cand, k)
    slots = k
    # PRE-EXISTING BUG, not just an anti-seed one: this built `Limits.flat`, so a
    # bundle partner bypassed the Forbidden/Limited list outright — a card banned
    # by the 2010.09 list could be dragged in as somebody's partner.
    limits = limits or Limits.flat(int(p["deck.max_copies"]))

    for bundle in bundle_idx.for_card(cand.card, curated_only=True):
        for partner in bundle.unmet(trial, by_cid):
            pick = bundle_idx.best_partner(partner, scored, by_cid)
            need = partner.min_copies - partner.satisfied_by(trial, by_cid)
            if pick is None or need <= 0:
                if pick is None and bundle.mode == "hard":
                    return None
                continue
            if not legal_addition(trial, pick, need, limits, p):
                if bundle.mode == "hard":
                    return None
                continue
            trial.add(pick, need)
            if not pick.card.is_extra:
                slots += need

    after = deckscore.score(trial, scored, p, lambda_synergy=lam).total
    after += bundle_idx.adjust(trial, by_cid, float(p["deck.p_bundle"]))[0]
    return (after - base) / max(1, slots)


def _autofill_bundles(
    state: DeckState,
    cand: Scored,
    scored: dict[int, Scored],
    bundle_idx: BundleIndex,
    by_cid: dict[int, Card],
    limits: Limits,
    p: Params,
) -> None:
    """Actually add the partners that ``_bundled_marginal`` priced in."""
    for bundle in bundle_idx.for_card(cand.card, curated_only=True):
        for partner in bundle.unmet(state, by_cid):
            pick = bundle_idx.best_partner(partner, scored, by_cid)
            need = partner.min_copies - partner.satisfied_by(state, by_cid)
            if pick is None or need <= 0:
                continue
            if legal_addition(state, pick, need, limits, p):
                state.add(pick, need)


def generate(
    seed: str | int,
    cards: list[Card],
    scored: dict[int, Scored],
    idx: MatchIndex,
    p: Params | None = None,
    opts: GenOptions | None = None,
) -> GeneratedDeck:
    """Build the best deck the model can find around *seed*."""
    from otn_enhanced.deckgen import cardpool

    p = p or default()
    opts = opts or GenOptions()
    by_cid = {c.cid: c for c in cards}
    bundle_idx = BundleIndex.with_mined(cards)
    limits = opts.limits or Limits.flat(int(p["deck.max_copies"]))

    # One seed or several.  With several, the engine is the *union* of their
    # engines and affinity is the elementwise max, so a card only needs to relate
    # to one of the seeds to count — which is what "build a deck around these
    # together" means. The seeds compete for slots on marginal gain like anything
    # else, so naming two seeds with nothing in common produces a deck that
    # serves both badly rather than silently dropping one.
    requested = seed if isinstance(seed, (list, tuple)) else [seed]
    seed_cards = [
        cardpool.find(cards, s) if isinstance(s, (str, int)) else s for s in requested
    ]
    seeds = [scored[c.cid] for c in seed_cards]
    seed_scored = seeds[0]

    # Anti-seeds: banned outright for this build.  Resolved the same way seeds
    # are, so `--anti-seed "Pot of Duality"` and a raw cid both work.
    anti_cards = [
        cardpool.find(cards, a) if isinstance(a, (str, int)) else a
        for a in (opts.anti_seeds or [])
    ]
    clash = {c.name for c in anti_cards} & {c.name for c in seed_cards}
    if clash:
        raise ValueError(
            f"{sorted(clash)} listed as both a seed and an anti-seed — "
            f"the build cannot both require and forbid it"
        )
    if anti_cards:
        limits = limits.forbidding(c.cid for c in anti_cards)
        # `_grow` re-derives its limits from `opts.limits`, so rebinding the
        # local here is invisible to it.  Write it back, or the ban silently
        # does nothing — which is exactly what the first version of this did.
        opts.limits = limits
        opts.log(f"anti-seeds: {', '.join(c.name for c in anti_cards)} (banned)")

    # Type/Attribute restriction: the same zero-copy-limit mechanism, and for the
    # same reason (see Limits.forbidding).
    #
    # **Seeds take precedence over the filter.**  Naming a card as a seed IS the
    # instruction to build around it, so an off-filter seed is exempted from the
    # ban and keeps its normal copy limit, while the filter still governs
    # everything the search is offered afterwards.  Refusing the combination
    # would make the useful request — `--seed <a Warrior> --allowed-types Dragon`,
    # meaning "this Warrior, then only Dragons around it" — impossible to state.
    mfilter = opts.monster_filter or MonsterFilter()
    filter_exempt: list[Card] = []
    if mfilter:
        exempt = {c.cid for c in seed_cards}
        filter_exempt = [c for c in seed_cards if not mfilter.allows(c)]
        excluded = mfilter.rejected_cids(cards) - exempt
        if excluded:
            limits = limits.forbidding(excluded, label="off-filter monster")
            opts.limits = limits
        # MAIN-deck monsters only: `deck.min_monsters` is a main-deck rule, so
        # counting Extra Deck monsters here inflates it — and would do so
        # catastrophically under --no-filter-extra-deck, where every Extra Deck
        # monster in the pool is "allowed" and a Type with 5 main-deck monsters
        # would sail past a floor of 18 and then fail to build.
        # An exempted seed is a monster the deck really can hold, so it counts.
        kept = sum(
            1 for c in cards
            if c.is_monster and c.playable and not c.is_extra
            and (mfilter.allows(c) or c.cid in exempt)
        )
        opts.log(
            f"monster filter: {mfilter.describe()} — {kept} monsters offered, "
            f"{len(excluded)} excluded"
        )
        if filter_exempt:
            opts.log(
                "  seeds kept despite the filter: "
                + ", ".join(
                    f"{c.name} [{c.attribute} {c.race}]" for c in filter_exempt
                )
            )
        if kept < int(p["deck.min_monsters"]):
            raise ValueError(
                f"monster filter ({mfilter.describe()}) leaves only {kept} playable "
                f"monsters, below the {int(p['deck.min_monsters'])} a legal deck needs"
            )

    lambdas = opts.restarts or list(p["deck.restarts"])

    for s in seeds:
        opts.log(f"seed: {s.name} (impact {s.impact:+.2f})")
    opts.log(f"bundles: {len(bundle_idx.bundles)} (curated + mined)")
    lv = _level_value(cards)
    affinity: dict[int, float] = {}
    for s in seeds:
        for cid, v in seed_affinity(s, scored, idx, lv).items():
            affinity[cid] = max(affinity.get(cid, 0.0), v)
    strong = sum(1 for v in affinity.values() if v >= 0.5)
    opts.log(f"seed affinity: {len(affinity)} related cards, {strong} strongly")

    stats = BuildStats()
    # The engine is a property of the seeds, not of the restart, so it is built
    # once and reused — the refinement pool below needs it after the loop too.
    with _Timer(stats, "engine pool", opts.log):
        engine: set[int] = set()
        for s in seeds:
            engine |= engine_pool(s, scored, idx)

    results: list[GeneratedDeck] = []
    for lam in lambdas:
        opts.log(f"--- restart lambda_synergy={lam} ---")
        state = DeckState(
            idx=idx, seed_affinity=affinity, level_value=lv,
            engine_cids=frozenset(engine),
        )
        for s in seeds:
            k = min(opts.seed_copies, limits.max_copies(s.cid))
            if k:
                state.add(s, k)
            _autofill_bundles(state, s, scored, bundle_idx, by_cid, limits, p)
        beams = [_Beam(state=state, value=deckscore.score(state, scored, p, lambda_synergy=lam).total)]

        # Phase 0 — the seed's engine, before staples are allowed to compete.
        opts.log(f"  phase 0: engine ({len(engine)} candidates, "
                 f"cutoff {opts.engine_cutoff:+.2f}/slot, max {opts.engine_max})")
        with _Timer(stats, f"lam {lam}: engine", opts.log):
            beams = _grow(
                beams, seed_scored, scored, idx, bundle_idx, by_cid, p, opts, lam,
                want="engine",
                engine=engine,
                # No count target: the phase ends when nothing clears the cutoff,
                # which the progress guard in _grow detects.  These are ceilings.
                stop=lambda st: (
                    sum(n for cid, n in st.copies.items() if cid in engine)
                    >= opts.engine_max
                    or st.main_total >= opts.size
                    or st.monsters >= int(p["deck.max_monsters"])
                ),
            )

        # Phase 1 — monsters.
        opts.log("  phase 1: monsters")
        with _Timer(stats, f"lam {lam}: monsters", opts.log):
            beams = _grow(
                beams, seed_scored, scored, idx, bundle_idx, by_cid, p, opts, lam,
                want="monster",
                stop=lambda st: st.monsters >= int(p["deck.min_monsters"]),
            )
        # Phase 2 — spells and traps
        opts.log("  phase 2: spells and traps")
        with _Timer(stats, f"lam {lam}: spell/trap", opts.log):
            beams = _grow(
                beams, seed_scored, scored, idx, bundle_idx, by_cid, p, opts, lam,
                want="spelltrap",
                stop=lambda st: st.main_total >= opts.size,
            )
        # Anything still short (a monster seed that filled slowly) tops up freely.
        with _Timer(stats, f"lam {lam}: top-up", opts.log):
            beams = _grow(
                beams, seed_scored, scored, idx, bundle_idx, by_cid, p, opts, lam,
                want="any",
                stop=lambda st: st.main_total >= opts.size,
            )

        best = max(beams, key=lambda b: b.value)
        # Before phase 3, not after: the Extra Deck ranking reads the finished
        # main deck (Tuner/non-Tuner Levels, main_total) to decide what is
        # reachable, so filling the main deck afterwards would rank the Synchros
        # against a deck that no longer exists.
        with _Timer(stats, f"lam {lam}: force-fill", opts.log):
            filled = force_fill_main(best.state, scored, p, limits, opts.log)
        opts.log("  phase 3: extra deck")
        with _Timer(stats, f"lam {lam}: extra deck", opts.log):
            _fill_extra(best.state, scored, p, opts, limits)
            filled += force_fill_extra(best.state, scored, p, opts, limits, opts.log)
        opts.log(
            f"  done lambda={lam}: {best.state.main_total} main, "
            f"{sum(best.state.extra.values())} extra"
        )
        final = deckscore.score(best.state, scored, p, lambda_synergy=lam)
        bonus, debt = bundle_idx.adjust(best.state, by_cid, float(p["deck.p_bundle"]))
        final.terms["bundles"] = round(bonus, 3)
        final.total = round(final.total + bonus, 4)
        results.append(
            GeneratedDeck(
                seed=seed_scored,
                seeds=list(seeds),
                state=best.state,
                score=final,
                lambda_synergy=lam,
                bundle_debt=debt,
                anti_seeds=[c.name for c in anti_cards],
                monster_filter=mfilter,
                filter_exempt=[c.name for c in filter_exempt],
                filled=filled,
                violations=violations(best.state, by_cid, p, limits),
            )
        )

    results.sort(key=lambda r: -r.score.total)
    winner = results[0]
    winner.alternates = results[1:]

    # Refinement and validation run on the WINNER only: both are expensive, and
    # applying them per restart would just re-rank the restarts by how much
    # polish they happened to absorb.
    with _Timer(stats, "refinement pool", opts.log):
        pool = refinement_pool(
            seeds, scored, idx, winner.state, engine, lv,
            max(opts.candidate_width, 200), limits,
        )
    opts.log(f"  refinement pool: {len(pool)} cards "
             f"({sum(1 for s in pool if s.cid in engine)} from the engine)")

    # Measured BEFORE refinement: the question is whether the search built the
    # deck around its seeds, and bootstrap reshuffling the list afterwards would
    # answer a different one.
    if opts.seed_holdout:
        with _Timer(stats, "seed holdout", opts.log):
            winner.holdout = seed_holdout(
                winner.state, list(seeds), scored, p, limits, pool
            )

    if opts.bootstrap_rounds > 0:
        opts.log(f"  phase 5: bootstrap ({opts.bootstrap_rounds} rounds)")
        with _Timer(stats, "bootstrap", opts.log):
            winner.swaps = bootstrap(
                winner.state, scored, idx, p, limits, pool,
                opts.bootstrap_rounds, log=opts.log,
                protect=frozenset(s.cid for s in seeds),
            )
        winner.score = deckscore.score(
            winner.state, scored, p, lambda_synergy=winner.lambda_synergy
        )
        bonus, debt = bundle_idx.adjust(winner.state, by_cid, float(p["deck.p_bundle"]))
        winner.score.terms["bundles"] = round(bonus, 3)
        winner.score.total = round(winner.score.total + bonus, 4)
        winner.bundle_debt = debt
        winner.violations = violations(winner.state, by_cid, p, limits)

    winner.stats = stats
    opts.log("  build timing:")
    for line in stats.format():
        opts.log("  " + line)
    return winner


#: Copies of a milled Graveyard payoff, as a bonus to a Fusion's Extra Deck rank.
#: Sized against `_material_depth`, which scales impact over 0..1: three milled
#: payoffs are worth about as much as a full-depth material line.
W_MILL_TARGET = 0.35


def _mill_value(state: DeckState, s: Scored) -> float:
    """How many Graveyard payoffs this Fusion would mill out of THIS deck.

    The other half of `deck.w_fusion_mill`.  That term makes the main deck hold
    payoffs some Fusion could mill; this one picks the Fusion that actually
    mills the ones it holds — Elemental Hero Gaia gets the slot because it lists
    "1 EARTH monster" and the deck runs Dandylion.

    Cheap because it runs in phase 3, once per candidate, with the main deck
    already decided — not inside the score loop.  And it needs no phase
    reordering: Future Fusion does not have to *Summon* the Fusion it names, so
    any Extra Deck slot will do and the only question is which name mills best.
    """
    if not state.fusion_millers or s.card.is_synchro or not s.card.is_extra:
        return 0.0
    from otn_enhanced.deckgen.text.parse import SUPPORT_WANT_PREFIX

    total = 0
    for pred, _ in s.parsed.wants:
        if (pred.raw or "").startswith(SUPPORT_WANT_PREFIX):
            continue
        for cid, n in state.copies.items():
            other = state._scored_cache.get(cid) if state._scored_cache else None
            if other is None or "gy_payoff" not in other.parsed.tags:
                continue
            if state.idx.satisfies(pred, cid):
                total += n
    return float(total)


def _material_depth(state: DeckState, s: Scored) -> float:
    """How WELL this deck supplies the Fusion's materials, 0..1.

    ``_fusion_ready`` is a boolean — "can I assemble this at all" — so a Fusion
    needing an off-theme splash ranked identically to one the deck feeds
    naturally, and raw impact broke the tie.  Reported case: a LIGHT-heavy HERO
    deck took **Elemental Hero Absolute Zero** (1 HERO + 1 WATER) over
    **Elemental Hero The Shining** (1 Elemental HERO + 1 LIGHT), because
    Absolute Zero's on-leave board wipe scores +2.20 of economy against The
    Shining's +1.90 of search.  In that deck The Shining is **6 copies deep** on
    its scarcest material and Absolute Zero is **1**.

    Scored on the bottleneck — the scarcest material is what actually gates the
    Summon — and saturating at 3 copies, past which more does not help much.
    Support wants are skipped: "supports LIGHT" is not a material.
    """
    from otn_enhanced.deckgen.text.parse import SUPPORT_WANT_PREFIX

    counts = [
        sum(n for cid, n in state.copies.items() if state.idx.satisfies(pred, cid))
        for pred, _ in s.parsed.wants
        if not (pred.raw or "").startswith(SUPPORT_WANT_PREFIX)
    ]
    if not counts:
        return 1.0
    return min(min(counts), 3) / 3.0


def _fusion_ready(state: DeckState, s: Scored) -> bool:
    """Can this deck actually Summon this Fusion?

    Its material line is parsed into ``wants``, so "can I make it" is just "does
    the deck hold something answering every one of them" — plus a Fusion spell,
    unless it is a contact Fusion that shuffles its own materials away (see
    ``text.parse._is_contact_fusion``).

    Deliberately strict: filling empty Extra Deck slots with bosses the deck
    cannot summon would be worse than leaving them empty, which is what the
    Synchro-reach ranking already guarantees for Synchros.
    """
    if not s.card.is_extra or s.card.is_synchro or not s.parsed.wants:
        return False
    if "fusion_summon" in s.parsed.requires and not state.provides.get("fusion_summon"):
        return False
    # Mind Control / Creature Swap put the opponent's monsters on your field,
    # where they are legal Fusion material — so "do I run these materials" stops
    # being the right question.  The named sole Summoner (NEX) still is.
    from otn_enhanced.deckgen.text.parse import SOLE_SUMMONER_MARK

    borrow = bool(state.provides.get("borrow_monster"))
    return all(
        state._count_matching(pred) > 0
        for pred, _ in s.parsed.wants
        if not (borrow and not pred.raw.endswith(SOLE_SUMMONER_MARK))
    )


def _fill_extra(
    state: DeckState,
    scored: dict[int, Scored],
    p: Params,
    opts: GenOptions,
    limits: Limits,
) -> None:
    """Phase 3: Synchros the deck can actually make, with level diversity."""
    covered: set[int] = set()

    # Reserve the Extra Deck slots the MAIN deck actually depends on, before the
    # reach ranking spends all 15.  _extra_candidates only ever yields Synchros
    # (a Fusion has no Tuner + non-Tuner Level maths to rank it by), so a Fusion
    # Monster could not be picked here at all and Instant Fusion shipped in decks
    # with nothing to Summon — the want stayed unmet no matter how many slots
    # were free.  Answering the dependency first is also the right priority: a
    # card that turns on a main-deck card beats one more generically good boss.
    for cand in _wanted_extra(state, scored, limits):
        if sum(state.extra.values()) >= opts.extra_size:
            break
        state.add(cand, 1)
        if cand.card.is_synchro and cand.card.level:
            covered.add(cand.card.level)

    # Reserve the Fusion a Fusion-milling enabler would NAME.
    #
    # Future Fusion's payoff is the mill first and the Summon second, so the
    # right Extra Deck slot is whichever Fusion sends the most Graveyard payoffs
    # this deck actually runs — Elemental Hero Gaia lists "1 EARTH monster" and
    # the deck runs Dandylion.  It has to be reserved HERE rather than left to
    # the fallback at the bottom: the Synchro reach ranking spends the other 14
    # slots first, so a deck was ending up with a single Fusion chosen for its
    # own stats and a mill of zero.
    #
    # No phase reordering needed, and that is the point — naming a Fusion does
    # not require Summoning it, so any slot will do and the main deck is already
    # known by the time this runs.
    if state.fusion_millers and sum(state.extra.values()) < opts.extra_size:
        best = max(
            (s for s in scored.values()
             if s.card.is_extra and not s.card.is_synchro and s.card.playable
             and limits.max_copies(s.cid) >= 1 and not state.extra.get(s.cid)),
            key=lambda s: (_mill_value(state, s), s.impact),
            default=None,
        )
        if best is not None and _mill_value(state, best) > 0:
            state.add(best, 1)

    for cand, reach in _extra_candidates(state, scored, p):
        if sum(state.extra.values()) >= opts.extra_size:
            break
        level = cand.card.level or 0
        # Prefer covering a new Level before doubling up on one already served.
        priority = cand.impact * reach * (1.0 if level not in covered else 0.45)
        if priority < 0.01:
            continue
        # The copy limit has to clamp BOTH branches.  It used to bind only the
        # new-Level one, so a card at limit 0 whose Level was already covered
        # took `k = 1` unconditionally and went into the Extra Deck anyway —
        # which let an --anti-seed Synchro through, and would let every
        # off-filter one through, since both are expressed as a zero limit.
        k = min(1 if level in covered else 2, limits.max_copies(cand.cid))
        k = min(k, opts.extra_size - sum(state.extra.values()))
        if k <= 0:
            continue
        state.add(cand, k)
        covered.add(level)

    # Fallback: a deck with no Tuners reaches no Synchro Levels at all, so the
    # ranking above yields nothing and the Extra Deck is left mostly EMPTY —
    # a Gladiator Beast deck seeded on Gyzarus shipped with 4 of its 15 slots
    # used.  Top up with Fusions this deck can genuinely put on the field.
    if sum(state.extra.values()) < opts.extra_size:
        # The seed's OWN engine first, then impact.  Ranking this purely by
        # impact filled a Gladiator Beast deck with Elemental HERO Fusions —
        # Absolute Zero scores +3.04 against Heraklinos's +0.54, and the two
        # stray HEROes in the main deck were enough to make them "ready".  A
        # generically stronger boss the deck can *technically* assemble is not
        # what an archetype deck wants in the slot.
        # Weighted by how deeply the deck supplies the materials, not just by
        # whether it can assemble them at all — see `_material_depth` — plus what
        # a Fusion-milling enabler would mill by naming it (`_mill_value`).
        ready = sorted(
            (s for s in scored.values() if _fusion_ready(state, s)),
            key=lambda s: (s.cid not in state.engine_cids,
                           -(s.impact * _material_depth(state, s)
                             + W_MILL_TARGET * _mill_value(state, s))),
        )
        for cand in ready:
            free = opts.extra_size - sum(state.extra.values())
            if free <= 0:
                break
            k = min(free, limits.max_copies(cand.cid),
                    2 if (cand.card.level or 0) in covered else 3)
            if k > 0 and state.extra.get(cand.cid, 0) < limits.max_copies(cand.cid):
                state.add(cand, min(k, limits.max_copies(cand.cid)
                                    - state.extra.get(cand.cid, 0)))
                covered.add(cand.card.level or 0)
