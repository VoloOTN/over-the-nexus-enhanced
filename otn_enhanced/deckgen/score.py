"""Combine economy and power into one ``impact`` scalar.

::

    impact = w_economy * 2*tanh(economy.exp / scale)  +  w_power * power.value

The ``tanh`` squash keeps ±1 card roughly linear and saturates past about ±4, so
one mis-parsed "draw 10" cannot dominate the whole pool ranking.  Reports show
``economy.exp`` unsquashed, because "+1.0 cards" is the number a human wants.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from otn_enhanced.deckgen import cache
from otn_enhanced.deckgen.economy import EconomyResult, economy
from otn_enhanced.deckgen.matchindex import MatchIndex
from otn_enhanced.deckgen.model import Card, ParsedCard
from otn_enhanced.deckgen.params import Params, default
from otn_enhanced.deckgen.power import (
    PowerResult, StatBaseline, power, synchro_level_value, synchro_levels,
)

SCHEMA = "deckgen.scores.v1"


@dataclass
class Scored:
    """A card with everything the search needs to rank it."""

    card: Card
    parsed: ParsedCard
    econ: EconomyResult
    pow_: PowerResult
    impact: float

    @property
    def cid(self) -> int:
        return self.card.cid

    @property
    def name(self) -> str:
        return self.card.name

    def explain(self) -> str:
        lines = [
            f"{self.card.name}  [{self.card.card_type}"
            + (f" {self.card.attribute}/{self.card.race} L{self.card.level} "
               f"{self.card.atk}/{self.card.def_}" if self.card.is_monster else "")
            + "]",
            f"  impact  {self.impact:+.3f}",
            f"  economy {self.econ.exp:+.2f} cards (range {self.econ.min:+.2f} .. "
            f"{self.econ.max:+.2f}"
            + (f", gross {self.econ.gross_max:.0f}" if self.econ.gross_max else "")
            + (", deck-dependent" if self.econ.context_sensitive else "")
            + ")",
        ]
        for k, v in self.econ.breakdown:
            lines.append(f"      {k:32} {v:+.3f}")
        lines.append(f"  power   {self.pow_.value:+.3f}")
        for k, v in self.pow_.breakdown:
            lines.append(f"      {k:32} {v:+.3f}")
        if self.parsed.tags:
            lines.append(f"  tags    {', '.join(sorted(self.parsed.tags))}")
        return "\n".join(lines)


def impact_from_exp(
    exp: float, pow_value: float, p: Params, evidence: float = 0.0
) -> float:
    """Impact for a given expected economy, so a deck-adjusted score can reuse it."""
    squashed = 2.0 * math.tanh(exp / float(p["impact.econ_scale"]))
    return round(
        float(p["impact.w_economy"]) * squashed
        + float(p["impact.w_power"]) * pow_value
        + float(p["impact.w_evidence"]) * evidence,
        4,
    )


def impact_of(econ: EconomyResult, pow_: PowerResult, p: Params) -> float:
    return impact_from_exp(econ.exp, pow_.value, p, pow_.evidence)


def score_pool(
    cards: list[Card],
    parsed: dict[int, ParsedCard],
    idx: MatchIndex | None = None,
    p: Params | None = None,
    *,
    play_rate: dict[int, float] | None = None,
    tag_rates: dict[str, float] | None = None,
    use_evidence: bool | None = None,
) -> dict[int, Scored]:
    """Score every card in the pool.

    Impact is **normalised to a fixed spread** across the pool before being
    returned. Only the ordering of impact is identifiable from data — the
    training objective is a rank correlation, so it is scale-invariant and will
    happily double every weight. But the deck objective adds impact to synergy
    terms, so the *magnitude* is load-bearing: an unnormalised fit that doubled
    the weights silently halved the influence of every synergy term and turned
    themed decks back into goodstuff piles. Fixing the spread here decouples the
    two: training chooses the shape, this chooses the units.
    """
    from otn_enhanced.deckgen import cardpool

    p = p or default()
    # ── which of the two modes is this? ─────────────────────────────────────
    #
    # Two genuinely different feature sets, so two coefficient sets.  With
    # evidence, per-cid tournament play rate is the model's single largest
    # signal.  Without it — after a randomiser run, where a cid no longer holds
    # the card that earned the statistic — `play_rate_for` falls back to per-TAG
    # rates, a different feature on a different scale that was nonetheless being
    # read through coefficients fitted for the per-cid one.
    #
    # Measured on the era corpus: per-cid +0.6302, per-tag +0.4988, neither
    # +0.2973.  The per-tag fallback is worth having; it is not worth reading
    # through the wrong coefficients.  See Params.with_profile.
    #
    # `use_evidence=None` auto-detects (the default, and what a normal run
    # wants).  Passing it explicitly forces a mode — `deckgen gen
    # --no-use-evidence` builds as if the ROM were randomised, which is also how
    # the randomised profile is fitted, there being no randomised ROM to hand.
    if use_evidence is None:
        use_evidence = not cardpool.is_randomised(cards)
    altered = not use_evidence
    if altered:
        p = p.with_profile("randomised")
    idx = idx or MatchIndex.build(cards, parsed)
    baseline = StatBaseline.build(cards, p)
    syn = synchro_levels(cards)

    # Empirical play rate from tournament decklists, if it has been mined.
    # Optional so the model still works on a clean checkout with no network.
    #
    # `play_rate` can be overridden by the fitter.  It has to be: the evidence
    # channel turns play rate into a *feature*, so scoring impact against play
    # rate measures the lookup, not the model.  Measured — Spearman is +0.7377
    # with the evidence channel on and **+0.2039** with it off, so ~three
    # quarters of the apparent correlation was play rate predicting itself.
    # training.fit therefore mines the feature from the fit half of the decks
    # and evaluates on the held-out half, which keeps w_staple honest: it can
    # still earn its weight by generalising, but not by memorising.
    play: dict[int, float] = play_rate or {}
    tag_rates = tag_rates or {}
    if play_rate is None:
        try:
            from otn_enhanced.deckgen import mining

            m = mining.load(cards)
            play, tag_rates = m.play_rate, m.tag_play_rate
        except (FileNotFoundError, OSError, KeyError):
            pass

    # If the ROM's card properties have been altered (a randomiser run), a
    # monster's *identity* no longer implies its stat line, so "this cid is a
    # staple" is no longer true of the card sitting at that cid.  Fall back to
    # the transferable half of the evidence — what tags tend to get played —
    # which stays valid because it describes behaviour, not a specific card.
    # Spells and traps are untouched by the randomiser, so they keep per-cid rates.
    def play_rate_for(c: Card) -> float:
        if not (altered and c.is_monster):
            return play.get(c.cid, 0.0)
        tags = parsed[c.cid].tags
        return max((tag_rates.get(t, 0.0) for t in tags), default=0.0)

    # Same per-cid problem one level down: "Level 8 Synchros are the good ones"
    # is true because *Stardust Dragon* is Level 8, so after a randomiser run it
    # describes a card that is no longer there.  `power.tuner_value` is built
    # from this, so leaving it weighted was the same leak `play_rate_for` above
    # exists to close.
    level_value = synchro_level_value(cards, {} if altered else play)
    non_tuner_levels = {
        c.level for c in cards
        if c.is_monster and not c.is_extra and not c.is_tuner and c.level
    }

    raw: dict[int, tuple[Card, ParsedCard, EconomyResult, PowerResult, float]] = {}
    for c in cards:
        pc = parsed[c.cid]
        e = economy(c, pc, p)
        w = power(
            c, pc, baseline, idx, syn, p,
            play_rate=play_rate_for(c), level_value=level_value,
            non_tuner_levels=non_tuner_levels,
        )
        raw[c.cid] = (c, pc, e, w, impact_of(e, w, p))

    values = [v[4] for v in raw.values() if v[0].playable]
    scale = 1.0
    if values:
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / len(values)
        sd = math.sqrt(var)
        if sd > 1e-6:
            scale = float(p.get("impact.target_spread", 1.0)) / sd

    return {
        cid: Scored(card=c, parsed=pc, econ=e, pow_=w, impact=round(val * scale, 4))
        for cid, (c, pc, e, w, val) in raw.items()
    }


def load_scored(
    *, force: bool = False, use_evidence: bool | None = None
) -> tuple[list[Card], dict[int, ParsedCard], MatchIndex, dict[int, Scored]]:
    """Pool + parse + index + scores, the standard entry point for the search.

    *use_evidence* selects the scoring mode; ``None`` auto-detects.  See
    :func:`score_pool`.
    """
    from otn_enhanced.deckgen.text.parse import load_parsed

    cards, parsed, _ = load_parsed(force=force)
    idx = MatchIndex.load(cards, parsed, force=force)
    scored = score_pool(cards, parsed, idx, use_evidence=use_evidence)
    return cards, parsed, idx, scored


def top(scored: dict[int, Scored], n: int = 30, *, predicate=None) -> list[Scored]:
    """The *n* highest-impact cards, optionally filtered."""
    vals = [s for s in scored.values() if predicate is None or predicate(s)]
    return sorted(vals, key=lambda s: -s.impact)[:n]
