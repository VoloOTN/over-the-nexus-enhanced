"""Fit scoring coefficients against tournament decklists.

The supervised signal is **play rate**: how often a card appears across
1st/2nd-place decks in formats whose card pool sits inside this ROM. A scoring
model that is any good should rank Bottomless Trap Hole above Ancient City -
Rainbow Ruins, and play rate says so without anyone hand-labelling anything.

The objective is Spearman correlation between ``impact`` and play rate, measured
over cards that are *legal in the relevant formats* — cards nobody plays are
mostly cards nobody had, so the correlation is computed on the cards that appear
at least once plus a matched sample of those that never do.

Coordinate descent over a small set of coefficients, fit on one half of the
decks and reported on the other. This exists because hand-tuning weights against
one's own intuition is how the model ended up preferring Ancient City to
Mystical Space Typhoon in the first place.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field

from otn_enhanced.deckgen import score as score_mod
from otn_enhanced.deckgen.matchindex import MatchIndex
from otn_enhanced.deckgen.model import Card, ParsedCard
from otn_enhanced.deckgen.params import Params
from otn_enhanced.deckgen.validate import metrics
from otn_enhanced.deckgen.validate.tournament import TournamentDeck

### What each objective is allowed to own.
###
### Deliberately small in both cases: these are the balance knobs, not the
### economy definitions, which stay pinned by data/golden.toml.
###
### The two search spaces used to overlap on eight coefficients, including
### `impact.w_power`.  That is not a redundancy, it is a race: whichever fit ran
### last won, and the card-level grid for w_power started at 0.35, so a routine
### `train --apply` would silently undo the deck fit's 0.10 — the exact value
### params.toml documents as the thing the card-level objective gets *wrong*
### (deck-level AUC: economy 0.625, power 0.393, anti-correlated).
###
### They are disjoint now, split on which question each objective can actually
### answer:
###
### * **card play rate** owns per-card quality — is this a good card?  Tag
###   weights and gain coefficients.
### * **deck AUC** (:data:`DECK_SEARCH_SPACE`) owns everything about how card
###   scores *aggregate into a deck*: the economy/power/evidence balance, the
###   stat and searchability channels that summing over 40 cards distorts, and
###   every deck.* term.
###
### `impact.w_economy` is in neither: score_pool renormalises impact to
### `target_spread`, so only the ratios of w_economy / w_power / w_evidence are
### identifiable and w_economy is the numeraire the other two move against.
SEARCH_SPACE: dict[str, list[float]] = {
    "power.tag_floodgate": [0.5, 1.0, 1.5, 2.2],
    "power.tag_protection": [0.3, 0.8, 1.3],
    "power.tag_nomi": [-1.6, -0.9, -0.4],
    "mod.recurrence": [1.0, 1.4, 1.8, 2.4],
    # Hand-set when the combat channel was introduced and never measured.
    "power.tag_battle_immune": [0.0, 0.20, 0.40, 0.70],
    "power.tag_atk_scaling": [0.0, 0.15, 0.30, 0.55],
    # New this session; 0.0 in range so the fit can reject them outright.
    "power.tag_tempo": [0.0, 0.30, 0.55, 0.90],
    "power.w_extra_generic": [0.0, 0.60, 1.20, 2.00],
    "power.tag_spot_removal": [0.0, 0.25, 0.50, 0.90],
    "power.tag_control_theft": [0.0, 0.30, 0.70, 1.20],
    "power.tag_hand_disruption": [0.0, 0.30, 0.70, 1.20],
    "power.tag_token_maker": [0.0, 0.30, 0.70, 1.20],
    "power.tag_banish_payoff": [0.0, 0.30, 0.70],
    "power.tag_opponent_turn": [0.0, 0.30, 0.70, 1.20],
    "power.tag_summon_answer": [0.0, 0.40, 0.90, 1.50],
    "power.tag_free_body": [0.0, 0.30, 0.70, 1.20],
    "power.tag_battle_payoff": [0.0, 0.30, 0.70, 1.20],
    "power.tag_stat_debuff": [0.0, 0.30, 0.70],
    "power.tag_recurring": [0.0, 0.30, 0.70, 1.20],
    "power.tag_lifegain": [-0.30, 0.0, 0.30],
    # From the wiki categories, 2026-07-30.  `random_outcome` and `self_damage`
    # are drawbacks, so their grids run negative.
    "power.tag_damage_block": [0.0, 0.30, 0.70],
    "power.tag_random_outcome": [-0.70, -0.30, 0.0],
    "power.tag_self_damage": [-0.70, -0.30, 0.0],
    # ── scored for a long time, never actually fitted ───────────────────────
    "power.tag_piercing": [0.0, 0.25, 0.55],
    "power.tag_direct_attack": [0.0, 0.35, 0.75],
    "power.tag_double_attack": [0.0, 0.45, 0.90],
    "power.tag_gy_setup": [0.0, 0.35, 0.70, 1.10],
    # NOT tag_battle_removal: DECK_SEARCH_SPACE already owns it, and the guard
    # below rejects a coefficient claimed by both.
    # ── the 21 wiki tags nothing could price until now ──────────────────────
    #
    # Grids point the way the mechanic points, and every one contains 0.0 so the
    # fit can refuse.  The last six are expected to refuse: they restate an
    # economy cost key or `w_extra_generic`, and a nonzero value there is double
    # counting rather than a finding.
    "power.tag_stat_boost": [0.0, 0.20, 0.45, 0.80],
    "power.tag_summon_payoff": [0.0, 0.30, 0.70, 1.20],
    "power.tag_conditional": [-0.90, -0.45, 0.0],
    "power.tag_attack_lock": [-1.20, -0.60, 0.0],
    "power.tag_equip_effect": [-0.60, -0.30, 0.0, 0.30],
    "power.tag_leave_payoff": [0.0, 0.30, 0.70, 1.20],
    "power.tag_attack_trigger": [0.0, 0.30, 0.70, 1.20],
    "power.tag_attack_redirect": [0.0, 0.30, 0.70],
    "power.tag_information": [0.0, 0.30, 0.70],
    "power.tag_name_change": [0.0, 0.30, 0.70],
    "power.tag_level_mod": [0.0, 0.30, 0.70],
    "power.tag_deck_stack": [0.0, 0.30, 0.70],
    "power.tag_fusion_payoff": [-0.60, -0.30, 0.0, 0.30],
    "power.tag_continuous_effect": [0.0, 0.30, 0.70],
    "power.tag_extra_normal_summon": [0.0, 0.40, 0.90],
    "power.tag_tribute_cost": [-0.70, -0.30, 0.0],
    "power.tag_banish_cost": [-0.70, -0.30, 0.0],
    "power.tag_lp_cost": [-0.70, -0.30, 0.0],
    "power.tag_generic_material": [0.0, 0.30, 0.70],
    "power.tag_generic_tuner": [0.0, 0.30, 0.70],
    "power.tag_generic_nontuner": [0.0, 0.30, 0.70],
    "gain.negate": [0.50, 0.70, 0.90, 1.10],
    "gain.negate_destroy": [0.70, 1.00, 1.30],
    "gain.spin_opp": [0.55, 0.75, 0.95, 1.20],
    "gain.draw_denial": [0.40, 0.65, 0.85, 1.10],
    "gain.control_swap": [0.20, 0.45, 0.70],
}


@dataclass
class PlayRate:
    """How often each cid appears across a set of tournament decks."""

    decks: int
    copies: dict[int, int] = field(default_factory=dict)
    presence: dict[int, int] = field(default_factory=dict)

    def rate(self, cid: int) -> float:
        """Decks containing the card, as a fraction of all decks."""
        return self.presence.get(cid, 0) / self.decks if self.decks else 0.0

    @classmethod
    def build(cls, decks: list[TournamentDeck]) -> "PlayRate":
        pr = cls(decks=len(decks))
        for d in decks:
            seen = set()
            for cid in list(d.main) + list(d.extra):
                pr.copies[cid] = pr.copies.get(cid, 0) + 1
                seen.add(cid)
            for cid in seen:
                pr.presence[cid] = pr.presence.get(cid, 0) + 1
        return pr


def evaluation_set(
    pr: PlayRate, cards: list[Card], rng: random.Random, negatives_per_positive: float = 1.0
) -> list[Card]:
    """Cards to score the fit on: everything played, plus matched unplayed cards.

    Including all 4,076 cards would make the correlation mostly a measure of "is
    this card in the format at all", which the model cannot and should not know.
    """
    played = [c for c in cards if pr.presence.get(c.cid)]
    unplayed = [c for c in cards if not pr.presence.get(c.cid)]
    rng.shuffle(unplayed)
    n = int(len(played) * negatives_per_positive)
    return played + unplayed[:n]


def mined_play_rate(decks: list[TournamentDeck], cards: list[Card]) -> dict[int, float]:
    """Play rate to FEED the evidence channel, from a specific set of decks.

    Kept separate from the :class:`PlayRate` used to score the objective so the
    two can be drawn from disjoint halves of the corpus.  Without that, the fit
    is scoring a play-rate lookup against play rate — see the note in
    ``score.score_pool``.
    """
    pr = PlayRate.build(decks)
    return {cid: pr.rate(cid) for cid in pr.presence}


def objective(
    params: Params,
    cards: list[Card],
    parsed: dict[int, ParsedCard],
    idx: MatchIndex,
    pr: PlayRate,
    sample: list[Card],
    feature_play_rate: dict[int, float] | None = None,
) -> float:
    """Spearman correlation between model impact and tournament play rate."""
    scored = score_mod.score_pool(
        cards, parsed, idx, params, play_rate=feature_play_rate
    )
    xs = [scored[c.cid].impact for c in sample]
    ys = [pr.rate(c.cid) for c in sample]
    return metrics.spearman(xs, ys)


def _with(params: Params, path: str, value: float) -> Params:
    raw = copy.deepcopy(params._raw)  # noqa: SLF001 — deliberate: fitting a copy
    node = raw
    parts = path.split(".")
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value
    return Params(raw)


@dataclass
class FitResult:
    params: Params
    fit_score: float
    held_score: float
    baseline_fit: float
    baseline_held: float
    changes: dict[str, tuple[float, float]]
    #: The value every searched coefficient started at, so a multi-seed run can
    #: report "3 of 5 seeds moved this" against a common origin.
    params_start: dict[str, float] = field(default_factory=dict)

    #: Shared interface with DeckFitResult, so one multi-seed driver runs both.
    @property
    def held(self) -> float:
        return self.held_score

    @property
    def base_held(self) -> float:
        return self.baseline_held

    def format(self) -> str:
        lines = [
            f"objective: Spearman(impact, tournament play rate)",
            f"  before  fit {self.baseline_fit:+.4f}   held-out {self.baseline_held:+.4f}",
            f"  after   fit {self.fit_score:+.4f}   held-out {self.held_score:+.4f}",
            f"  held-out gain {self.held_score - self.baseline_held:+.4f}",
            "",
            "coefficient changes:",
        ]
        if not self.changes:
            lines.append("  (none — the starting values were already optimal on the grid)")
        for path, (old, new) in sorted(self.changes.items()):
            lines.append(f"  {path:28} {old:+.3f} -> {new:+.3f}")
        return "\n".join(lines)


def fit(
    cards: list[Card],
    parsed: dict[int, ParsedCard],
    idx: MatchIndex,
    decks: list[TournamentDeck],
    base: Params,
    *,
    seed: int = 1,
    rounds: int = 2,
    min_gain: float = 0.001,
    verbose: bool = True,
) -> FitResult:
    """Coordinate descent over :data:`SEARCH_SPACE`, fit/held-out split by deck.

    Same two corrections as :func:`fit_deck`: the parameter order is randomised
    per round (dict order handicapped every coefficient added late) and
    ``min_gain`` is a real threshold rather than ``1e-6``, which was small enough
    to accept noise and report it as a finding.
    """
    rng = random.Random(seed)
    shuffled = list(decks)
    rng.shuffle(shuffled)
    cut = len(shuffled) // 2
    pr_fit = PlayRate.build(shuffled[:cut])
    pr_held = PlayRate.build(shuffled[cut:])

    sample_fit = evaluation_set(pr_fit, cards, rng)
    sample_held = evaluation_set(pr_held, cards, rng)

    # The evidence feature comes from the FIT half; the held-out half is scored
    # against a model that has never seen its play rates.  Nothing else makes
    # `power.w_staple` measurable rather than tautological.
    feat = mined_play_rate(shuffled[:cut], cards)

    def obj(params, pr, sample):
        return objective(params, cards, parsed, idx, pr, sample, feat)

    current = base
    baseline_fit = obj(current, pr_fit, sample_fit)
    baseline_held = obj(current, pr_held, sample_held)
    best_fit = baseline_fit
    changes: dict[str, tuple[float, float]] = {}

    for round_no in range(rounds):
        improved = False
        order = list(SEARCH_SPACE)
        rng.shuffle(order)
        for path in order:
            grid = SEARCH_SPACE[path]
            start = float(current[path])
            best_val, best_obj = start, best_fit
            for value in grid:
                if value == start:
                    continue
                trial = _with(current, path, value)
                o_ = obj(trial, pr_fit, sample_fit)
                if o_ > best_obj + min_gain:
                    best_val, best_obj = value, o_
            if best_val != start:
                current = _with(current, path, best_val)
                original = changes.get(path, (start, start))[0]
                changes[path] = (original, best_val)
                best_fit = best_obj
                improved = True
                if verbose:
                    print(f"  round {round_no + 1}: {path} {start:+.3f} -> {best_val:+.3f}"
                          f"  (fit {best_obj:+.4f})", flush=True)
        if not improved:
            break

    held = obj(current, pr_held, sample_held)
    return FitResult(
        params=current,
        fit_score=best_fit,
        held_score=held,
        baseline_fit=baseline_fit,
        baseline_held=baseline_held,
        changes={k: v for k, v in changes.items() if v[0] != v[1]},
    )


### ── stage 2: the deck-level objective ──────────────────────────────────────
###
### Fitting card impact is not enough.  The deck score adds synergy and
### concentration terms whose weights were hand-set to force themed decks, and
### with those values the model rated Konami's AI decks ABOVE tournament winners
### (AUC 0.462).  Those weights get their own supervised signal: tournament decks
### should outscore ROM decks.

DECK_SEARCH_SPACE: dict[str, list[float]] = {
    "deck.w_want_scale": [1.0, 2.0, 4.0, 8.0],
    "deck.w_archetype": [0.5, 1.5, 3.0, 5.0],
    "deck.w_attribute_concentration": [0.0, 1.0, 3.0, 6.0],
    "deck.w_race_concentration": [0.0, 1.0, 3.0],
    "deck.w_gy_cycle": [0.5, 1.5, 3.0],
    "deck.w_tuner_reach": [0.5, 1.5, 2.5],
    "deck.p_orphan": [1.0, 3.0, 5.0, 8.0],
    "deck.p_enabler": [0.5, 1.5, 2.5, 4.0],
    "deck.p_curve": [0.0, 0.35, 1.0],
    # The economy/power balance belongs here too.  Fitting it against card-level
    # play rate said "raise w_stat" -- but summing stat_eff across 40 cards
    # rewards beater piles, which is exactly what the ROM's AI decks are, and at
    # the deck level power turned out ANTI-correlated with quality (AUC 0.393 vs
    # economy's 0.625).  The deck objective is the one that matters here.
    "impact.w_power": [0.10, 0.25, 0.55, 1.10],
    # NOTE: `impact.w_economy` is deliberately absent.  score_pool normalises the
    # impact distribution to `target_spread`, so scaling w_economy, w_power and
    # w_evidence together is exactly a no-op and only their *ratios* are
    # identifiable.  Leaving all three free lets coordinate descent wander along
    # that degenerate direction and report "changes" that change nothing.
    # w_economy is the numeraire; the other two move against it.
    "impact.econ_scale": [1.0, 2.0, 3.0],
    "power.w_stat": [0.10, 0.30, 0.60, 1.30],
    "power.w_searchability": [0.15, 0.35, 0.60],
    # The evidence channel (tournament play rate, ATK floor, hard drawbacks).
    # Added after it was split out of w_power, which the earlier fit had crushed
    # to 0.10 -- disabling the most predictive signals in the model as a side
    # effect of correctly finding stat-summing anti-correlated.
    "impact.w_evidence": [0.50, 1.00, 1.60, 2.40],
    "power.w_staple": [1.0, 3.0, 5.0, 8.0],
    "power.p_atk_floor": [0.0, 0.6, 1.2, 2.0],
    "power.tag_needs_self_copies": [-4.0, -2.5, -1.0],
    "deck.p_dead_advantage": [0.5, 2.0, 4.0],
    "deck.p_unsummonable": [0.0, 1.5, 3.0, 6.0],
    # The hypergeometric terms, previously hand-set to produce sensible copy
    # counts and never fitted.
    "deck.w_consistency": [5.0, 15.0, 25.0, 45.0, 70.0],
    "deck.p_dead_draw": [0.0, 1.5, 3.0, 6.0],
    "deck.w_one_card_combo": [2.0, 5.0, 8.0, 14.0],
    # The searcher-consistency channel, hand-set at 3.00 when the self-discard
    # charge removed a full card of economy from every Hecatrice-class searcher.
    "deck.w_search_access": [0.0, 1.5, 3.0, 6.0],
    # The summon-tax family, all hand-set when introduced and never fitted.
    "power.tax_level_5_6": [-0.60, -1.30, -2.20],
    "power.tax_level_7_plus": [-1.50, -3.00, -4.50],
    "power.tax_level_9_plus": [-2.50, -4.50, -7.00],
    "power.self_ss_tax_relief": [0.0, 0.25, 0.60, 1.0],
    "power.tax_refund_when_cheatable": [0.3, 0.55, 0.80, 1.0],
    # Everything added while closing the blind spots, all hand-set and none of it
    # measured against anything.  p_role_balance especially: it has been pinned
    # at its cap on every build so far, which makes it a constant offset rather
    # than a term.  Zero is in every range so the fit can reject them outright.
    "deck.p_role_balance": [0.0, 0.75, 1.50, 3.00],
    "deck.interaction_min": [0.0, 0.10, 0.20, 0.30],
    "deck.interaction_max": [0.40, 0.50, 0.65, 1.0],
    "deck.p_gy_denial": [0.0, 3.0, 6.0, 10.0],
    "deck.w_deckout": [0.0, 3.0, 6.0, 12.0],
    "deck.w_burn": [0.0, 2.0, 4.0, 8.0],
    "deck.w_flip_cycle": [0.0, 0.6, 1.2, 2.4],
    "power.tag_battle_removal": [0.0, 0.30, 0.55, 0.90],
    "power.tag_combat_trick": [0.0, 0.25, 0.45, 0.80],
    "power.tag_board_reset": [0.0, 0.30, 0.60, 1.00],
}

#: The two objectives must not fit the same coefficient — see the note above
#: SEARCH_SPACE.  Asserted at import so re-adding one is a hard error rather
#: than a race whose winner depends on the order the commands were run in.
_CONTESTED = set(SEARCH_SPACE) & set(DECK_SEARCH_SPACE)
if _CONTESTED:  # pragma: no cover — a wiring mistake, not a runtime condition
    raise RuntimeError(
        "SEARCH_SPACE and DECK_SEARCH_SPACE both fit "
        f"{sorted(_CONTESTED)}; whichever fit runs last would silently win"
    )


def deck_objective(
    params: Params,
    cards: list[Card],
    parsed: dict[int, ParsedCard],
    idx: MatchIndex,
    good: list[tuple[list[int], list[int]]],
    poor: list[tuple[list[int], list[int]]],
    feature_play_rate: dict[int, float] | None = None,
) -> float:
    """AUC that a tournament deck outscores a ROM AI deck.

    The pool is rescored for every trial because ``impact`` itself depends on the
    coefficients being fitted — the balance between economy and power is exactly
    what this objective is meant to decide.

    *feature_play_rate* must be mined from decks NOT in *good*, or the evidence
    channel hands the answer to the objective: cards played in these very decks
    get a staple bonus, so these very decks score higher.
    """
    from otn_enhanced.deckgen import deckscore
    from otn_enhanced.deckgen.deckstate import DeckState

    scored = score_mod.score_pool(
        cards, parsed, idx, params, play_rate=feature_play_rate
    )

    def score_one(main: list[int], extra: list[int]) -> float:
        state = DeckState(idx=idx)
        counts: dict[int, int] = {}
        for cid in main:
            counts[cid] = counts.get(cid, 0) + 1
        for cid, n in counts.items():
            if cid in scored:
                state.add(scored[cid], n)
        for cid in extra:
            if cid in scored:
                state.add(scored[cid], 1)
        return deckscore.score(state, scored, params).total

    return metrics.auc([score_one(*d) for d in good], [score_one(*d) for d in poor])


@dataclass
class DeckFitResult:
    params: Params
    fit_auc: float
    held_auc: float
    baseline_fit: float
    baseline_held: float
    changes: dict[str, tuple[float, float]]
    #: The value every searched coefficient started at, so a multi-seed run can
    #: report "3 of 5 seeds moved this" against a common origin.
    params_start: dict[str, float] = field(default_factory=dict)

    @property
    def held(self) -> float:
        return self.held_auc

    @property
    def base_held(self) -> float:
        return self.baseline_held

    def format(self) -> str:
        lines = [
            "objective: AUC(tournament deck scores above ROM AI deck)",
            f"  before  fit {self.baseline_fit:.4f}   held-out {self.baseline_held:.4f}",
            f"  after   fit {self.fit_auc:.4f}   held-out {self.held_auc:.4f}",
            f"  held-out gain {self.held_auc - self.baseline_held:+.4f}",
            "",
            "coefficient changes:",
        ]
        if not self.changes:
            lines.append("  (none)")
        for path, (old, new) in sorted(self.changes.items()):
            lines.append(f"  {path:34} {old:+.3f} -> {new:+.3f}")
        return "\n".join(lines)


def fit_deck(
    cards: list[Card],
    parsed: dict[int, ParsedCard],
    idx: MatchIndex,
    good: list[tuple[list[int], list[int]]],
    poor: list[tuple[list[int], list[int]]],
    base: Params,
    *,
    seed: int = 1,
    rounds: int = 2,
    min_gain: float = 0.002,
    feature_play_rate: dict[int, float] | None = None,
    verbose: bool = True,
) -> DeckFitResult:
    """Coordinate descent on the deck-level weights.

    Two deliberate departures from the card-level :func:`fit`:

    * **Parameter order is randomised per round.**  Coordinate descent is
      order-dependent and dict order is insertion order, so every parameter added
      to the grid later was evaluated against a deck the earlier ones had already
      claimed the credit for — a systematic handicap on exactly the coefficients
      that most needed measuring.
    * **``min_gain`` is a real threshold, not ``1e-6``.**  This objective is an
      AUC over a few hundred deck pairs; a 1e-6 improvement is one pair swapping
      order, and accepting it means fitting noise and reporting it as a result.
    """
    rng = random.Random(seed)
    good, poor = list(good), list(poor)
    rng.shuffle(good)
    rng.shuffle(poor)
    gf, gh = good[: len(good) // 2], good[len(good) // 2:]
    pf, ph = poor[: len(poor) // 2], poor[len(poor) // 2:]

    # Evidence mined from the HELD-OUT good decks, so the decks being scored on
    # the fit half never contributed to their own staple bonus.
    feat = feature_play_rate if feature_play_rate is not None else {}

    current = base
    baseline_fit = deck_objective(current, cards, parsed, idx, gf, pf, feat)
    baseline_held = deck_objective(current, cards, parsed, idx, gh, ph, feat)
    best = baseline_fit
    changes: dict[str, tuple[float, float]] = {}

    for round_no in range(rounds):
        improved = False
        order = list(DECK_SEARCH_SPACE)
        rng.shuffle(order)
        for path in order:
            grid = DECK_SEARCH_SPACE[path]
            start = float(current[path])
            best_val, best_obj = start, best
            for value in grid:
                if value == start:
                    continue
                trial = _with(current, path, value)
                obj = deck_objective(trial, cards, parsed, idx, gf, pf, feat)
                if obj > best_obj + min_gain:
                    best_val, best_obj = value, obj
            if best_val != start:
                current = _with(current, path, best_val)
                original = changes.get(path, (start, start))[0]
                changes[path] = (original, best_val)
                best = best_obj
                improved = True
                if verbose:
                    print(f"  round {round_no + 1}: {path} {start:+.3f} -> {best_val:+.3f}"
                          f"  (AUC {best_obj:.4f})", flush=True)
        if not improved:
            break

    return DeckFitResult(
        params=current,
        fit_auc=best,
        held_auc=deck_objective(current, cards, parsed, idx, gh, ph, feat),
        baseline_fit=baseline_fit,
        baseline_held=baseline_held,
        changes={k: v for k, v in changes.items() if v[0] != v[1]},
    )


@dataclass
class MultiFitResult:
    """Several independent deck fits, and what they agree on.

    A single coordinate-descent run reports one path through a non-convex grid,
    and the card-level work already showed how misleading that is: the
    incumbent-based single-seed run "found" ``tag_floodgate 0.50`` that four of
    five neutral seeds rejected.  Only the coefficients most seeds land on
    independently are worth writing.
    """

    runs: list
    #: path -> the value each seed settled on.
    choices: dict[str, list[float]] = field(default_factory=dict)
    #: What the objective measures, for the report header.
    objective: str = "AUC(tournament deck scores above ROM AI deck)"

    @property
    def held_gains(self) -> list[float]:
        return [r.held - r.base_held for r in self.runs]

    def consensus(self, min_seeds: int) -> dict[str, tuple[float, float]]:
        """``{path: (old, new)}`` for values at least *min_seeds* runs agreed on.

        Ties break toward leaving the parameter alone: a coefficient the seeds
        split on is evidence of nothing, and this fit is confounded enough (see
        the concentration note in params.toml) that a weak majority is not a
        licence to move a hand-reasoned value.
        """
        out: dict[str, tuple[float, float]] = {}
        for path, values in self.choices.items():
            start = self.runs[0].params_start.get(path)
            if start is None:
                continue
            top = max(set(values), key=values.count)
            if values.count(top) >= min_seeds and top != start:
                out[path] = (start, top)
        return out

    def format(self, min_seeds: int) -> str:
        gains = self.held_gains
        mean = sum(gains) / len(gains)
        sd = (sum((g - mean) ** 2 for g in gains) / len(gains)) ** 0.5
        lines = [
            f"objective: {self.objective}",
            f"  {len(self.runs)} seeds, held-out gain {mean:+.4f} +/- {sd:.4f} "
            f"({sum(1 for g in gains if g > 0)}/{len(gains)} positive)",
            "  per seed: " + "  ".join(f"{r.base_held:+.3f}->{r.held:+.3f}"
                                       for r in self.runs),
            "",
            f"{'coefficient':34} {'start':>7}  per-seed choices",
        ]
        for path in sorted(self.choices):
            values = self.choices[path]
            start = self.runs[0].params_start.get(path, float("nan"))
            top = max(set(values), key=values.count)
            agree = values.count(top)
            mark = "*" if agree >= min_seeds and top != start else " "
            lines.append(
                f"{mark}{path:33} {start:+7.2f}  "
                + " ".join(f"{v:+6.2f}" for v in values)
                + f"   [{agree}/{len(values)} on {top:+.2f}]"
            )
        lines.append("")
        lines.append(f"* = agreed by >= {min_seeds} seeds and different from the "
                     f"current value; only these are written")
        return "\n".join(lines)


def fit_multi(
    cards: list[Card],
    parsed: dict[int, ParsedCard],
    idx: MatchIndex,
    decks: list[TournamentDeck],
    base: Params,
    *,
    seeds: list[int],
    rounds: int = 2,
    min_gain: float = 0.001,
    verbose: bool = True,
) -> MultiFitResult:
    """Run the card-level :func:`fit` from the same base under several splits."""
    runs: list[FitResult] = []
    choices: dict[str, list[float]] = {path: [] for path in SEARCH_SPACE}
    for seed in seeds:
        if verbose:
            print(f"--- seed {seed} ---", flush=True)
        r = fit(cards, parsed, idx, decks, base, seed=seed, rounds=rounds,
                min_gain=min_gain, verbose=verbose)
        r.params_start = {path: float(base[path]) for path in SEARCH_SPACE}
        runs.append(r)
        for path in SEARCH_SPACE:
            choices[path].append(float(r.params[path]))
    return MultiFitResult(
        runs=runs, choices=choices,
        objective="Spearman(impact, tournament play rate)",
    )


def fit_deck_multi(
    cards: list[Card],
    parsed: dict[int, ParsedCard],
    idx: MatchIndex,
    good: list[tuple[list[int], list[int]]],
    poor: list[tuple[list[int], list[int]]],
    base: Params,
    *,
    seeds: list[int],
    rounds: int = 2,
    min_gain: float = 0.002,
    feature_play_rate: dict[int, float] | None = None,
    verbose: bool = True,
) -> MultiFitResult:
    """Run :func:`fit_deck` from the same neutral base under several splits."""
    runs: list[DeckFitResult] = []
    choices: dict[str, list[float]] = {path: [] for path in DECK_SEARCH_SPACE}
    for seed in seeds:
        if verbose:
            print(f"--- seed {seed} ---", flush=True)
        r = fit_deck(cards, parsed, idx, good, poor, base, seed=seed,
                     rounds=rounds, min_gain=min_gain,
                     feature_play_rate=feature_play_rate, verbose=verbose)
        r.params_start = {path: float(base[path]) for path in DECK_SEARCH_SPACE}
        runs.append(r)
        for path in DECK_SEARCH_SPACE:
            choices[path].append(float(r.params[path]))
    return MultiFitResult(runs=runs, choices=choices)


def write_params(result, path, *, only: set[str] | None = None) -> None:
    """Rewrite numeric values in params.toml, preserving comments and layout.

    Walks the file line by line tracking the current ``[section]`` header rather
    than matching a regex across a whole block: ``restarts = [0.60, 1.00, 1.60]``
    contains brackets, which made a block-spanning pattern fail to find any key
    defined after it.

    *only* restricts the write to a subset of the fitted changes, for when some
    of them are judged to be fitting a confound rather than a real effect.
    """
    import re
    from pathlib import Path

    path = Path(path)
    wanted = {
        k: v for k, v in result.changes.items() if only is None or k in only
    }
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    section = ""
    written: set[str] = set()
    header = re.compile(r"^\s*\[([^\]]+)\]\s*$")
    assign = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*=\s*)(-?[\d.]+)(.*)$")

    for i, line in enumerate(lines):
        m = header.match(line)
        if m:
            section = m.group(1)
            continue
        a = assign.match(line)
        if not a:
            continue
        dotted = f"{section}.{a.group(2)}"
        if dotted in wanted:
            new = wanted[dotted][1]
            lines[i] = f"{a.group(1)}{a.group(2)}{a.group(3)}{new:.2f}{a.group(5)}\n"
            written.add(dotted)

    missing = set(wanted) - written
    if missing:
        raise RuntimeError(f"could not locate {sorted(missing)} in {path}")
    path.write_text("".join(lines), encoding="utf-8")
