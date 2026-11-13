"""Pairwise synergy, used to *prefilter* candidates before exact scoring.

The search's real objective is :func:`deckscore.score`, which works off the
deck's accumulators.  This module answers the cheaper question "which 200 of the
4,076 cards are even worth evaluating against this deck?" — running the exact
marginal gain on the whole pool at every step would be 40x slower for no gain in
deck quality.
"""

from __future__ import annotations

from otn_enhanced.deckgen.matchindex import MatchIndex, exclusivity
from otn_enhanced.deckgen.score import Scored


#: How much a one-card Synchro line is worth, times the Level's play rate.
#: A Firedog -> Magician -> Level 8 line lands at ~2.4 with Stardust at 94%.
W_ONE_CARD_SYNCHRO = 2.5

#: NOTE: the Fusion-mill bonus deliberately does NOT live here.  `synergy.pair`
#: is only the candidate PREFILTER — `deckscore.score` never calls it — so a
#: term added here reshuffles which cards get evaluated without ever rewarding
#: the pairing.  Measured: it moved millable payoffs across four decks 15 -> 13,
#: i.e. noise in the wrong direction.  It lives in `deckscore` as
#: `deck.w_fusion_mill`, fed by DeckState.millable_payoff / fusion_millers.




def _is_fusion_material(idx: MatchIndex, cid: int) -> bool:
    """Could SOME Fusion Monster's material line name this card?

    Answered against the whole pool rather than the chosen Extra Deck, and that
    is the point: Future Fusion may name any Fusion, and the Extra Deck is not
    chosen until phase 3 — after every main-deck slot is already spent.  "Could
    some Fusion mill this card" is answerable while the main deck is being
    built; "does the Extra Deck I have not built yet mill it" is not.

    The mask is precomputed once per pool in :meth:`MatchIndex.build`.
    """
    bit = idx.index_of.get(cid)
    if bit is None:
        return False
    return bool(idx.fusion_material_mask >> bit & 1)


def _norm_impact(s: Scored) -> float:
    """Impact folded into roughly 0..1 so it scales a synergy weight sanely."""
    return max(0.0, min(1.5, s.impact + 0.5)) / 1.5


def directed(a: Scored, b: Scored, idx: MatchIndex) -> float:
    """How much *a* wants *b* — one bit test per want."""
    total = 0.0
    for pred, weight in a.parsed.wants:
        if idx.satisfies(pred, b.cid):
            total += weight * exclusivity(idx.count(pred)) * _norm_impact(b)
    return total


#: Verbs that put the *other* card straight onto the field from a private zone.
_ONE_CARD_VERBS = frozenset({"special_summon"})


def one_card_synchro(
    a: Scored, b: Scored, idx: MatchIndex, level_value: dict[int, float]
) -> float:
    """Does *a* put *b* on the field such that the two make a Synchro together?

    This is the Flamvell Firedog + Flamvell Magician pattern: Firedog destroys a
    monster by battle and Special Summons a FIRE monster with 200 or less DEF
    from the Deck.  Magician is a legal target *and* a Level 4 Tuner, so one card
    becomes Level 4 + Level 4 = a Level 8 Synchro.

    That is worth far more than either body's stats, and nothing else in the
    model sees it: `tuner_value` only knows what a Tuner could make in the
    abstract, and the want channel only knows that Firedog wants *a* FIRE
    monster.  The combination is the point.
    """
    if not (a.card.is_monster and b.card.is_monster):
        return 0.0
    if a.card.is_tuner == b.card.is_tuner:
        return 0.0  # a Synchro needs exactly one Tuner
    if not (a.card.level and b.card.level):
        return 0.0
    total = a.card.level + b.card.level
    value = level_value.get(total, 0.0)
    if value <= 0:
        return 0.0
    summons = any(
        c.verb in _ONE_CARD_VERBS
        and c.zone_from in ("deck", "gy")
        and c.side == "you"
        and c.predicate is not None
        and idx.satisfies(c.predicate, b.cid)
        for c in a.parsed.clauses
    )
    return value if summons else 0.0


#: (a cid, b cid, whether Synchro-combo value was supplied) -> synergy.
#:
#: `pair` became the single biggest cost in a build once the score loop was
#: optimised: **200,065 calls and 2.22s of a 9.4s profile**, because `_prefilter`
#: re-ranks the whole pool at every step and every beam.  The answer depends only
#: on the two cards' parsed text and the pool, so it is the same every time.
#:
#: `level_value` is not part of the key beyond "present or absent": it comes from
#: `_level_value(cards)` / `synchro_level_value(cards, play_rate)`, both pure
#: functions of the pool, so every non-None value in a process has identical
#: content.  `best_partners` is the one caller that passes None, and that
#: genuinely changes the result — hence the flag.
_PAIR_CACHE: dict[tuple[int, int, bool], float] = {}


def pair(a: Scored, b: Scored, idx: MatchIndex, level_value=None) -> float:
    """Symmetric synergy between two cards.  Memoised; see :data:`_PAIR_CACHE`."""
    if a.cid == b.cid:
        return 0.0
    key = (a.cid, b.cid, level_value is not None)
    hit = _PAIR_CACHE.get(key)
    if hit is not None:
        return hit
    _PAIR_CACHE[key] = out = _pair_uncached(a, b, idx, level_value)
    return out


def _pair_uncached(a: Scored, b: Scored, idx: MatchIndex, level_value=None) -> float:
    if a.cid == b.cid:
        return 0.0
    total = directed(a, b, idx) + directed(b, a, idx)

    # Shared archetype, and the shape-level pairings that no card filter states.
    from otn_enhanced.deckgen.text.parse import is_real_archetype

    if (
        a.card.archetype
        and a.card.archetype == b.card.archetype
        and is_real_archetype(a.card.archetype)
    ):
        total += 0.6
    tags_a, tags_b = a.parsed.tags, b.parsed.tags
    if "gy_filler" in tags_a and "gy_payoff" in tags_b:
        total += 0.4
    if "gy_payoff" in tags_a and "gy_filler" in tags_b:
        total += 0.4
    if "discard_outlet" in tags_a and "discard_payoff" in tags_b:
        total += 0.45
    if "discard_payoff" in tags_a and "discard_outlet" in tags_b:
        total += 0.45
    if a.card.is_monster and b.card.is_monster:
        if a.card.attribute and a.card.attribute == b.card.attribute:
            total += 0.15
        if a.card.race and a.card.race == b.card.race:
            total += 0.10
    if level_value:
        combo = one_card_synchro(a, b, idx, level_value) + one_card_synchro(
            b, a, idx, level_value
        )
        total += W_ONE_CARD_SYNCHRO * combo
    return total


def best_partners(
    seed: Scored, scored: dict[int, Scored], idx: MatchIndex, n: int = 20
) -> list[tuple[Scored, float]]:
    """The *n* cards with the strongest pairwise synergy to *seed*."""
    ranked = (
        (s, pair(seed, s, idx))
        for s in scored.values()
        if s.cid != seed.cid and s.card.playable
    )
    return sorted((r for r in ranked if r[1] > 0), key=lambda t: -t[1])[:n]
