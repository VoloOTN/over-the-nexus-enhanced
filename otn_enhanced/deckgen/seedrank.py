"""Rank cards by how good a *seed* they are.

A seed is only useful if a deck can be built around it, and that is a different
question from whether the card is good. Worm Yagan is a perfectly reasonable
card that makes a bad seed — its engine is one other card, behind a board
restriction. Rekindling is a mediocre card in isolation (economy −1.00) that
makes an excellent seed, because 25 pool cards answer its want.

Scored from five things, all cheap enough to run over the whole pool:

``engine``       how many cards link to it, log-scaled — a seed with no engine
                 cannot anchor a deck
``quality``      how good the best of those engine cards are
``specificity``  how *restrictive* its wants are; "1 monster" is not a theme
``reciprocity``  how many engine cards want the seed back, which is what makes
                 an engine self-reinforcing rather than a one-way search
``combo``        the best one-card Synchro line available inside the engine

This is a proxy for "what would `generate` produce from this seed", which is the
real quantity but far too slow to evaluate 4,076 times. :func:`validate` checks
the proxy against actual builds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from otn_enhanced.deckgen import synergy
from otn_enhanced.deckgen.matchindex import MatchIndex, exclusivity
from otn_enhanced.deckgen.model import Card
from otn_enhanced.deckgen.score import Scored

#: Engine members considered when judging quality — roughly a deck's worth.
TOP_K = 12


@dataclass
class SeedScore:
    card: Card
    engine_size: int
    engine: float
    quality: float
    specificity: float
    reciprocity: float
    combo: float
    total: float

    def row(self) -> str:
        return (
            f"{self.total:6.2f}  {self.card.name[:34]:36} "
            f"engine {self.engine_size:4}  qual {self.quality:5.2f}  "
            f"spec {self.specificity:4.2f}  recip {self.reciprocity:4.1f}  "
            f"combo {self.combo:4.2f}"
        )


def score_seed(
    seed: Scored,
    scored: dict[int, Scored],
    idx: MatchIndex,
    level_value: dict[int, float],
) -> SeedScore:
    """Score one card's potential as a deck seed."""
    from otn_enhanced.deckgen.search import engine_pool

    pool = engine_pool(seed, scored, idx) - {seed.cid}
    members = [scored[c] for c in pool if c in scored and scored[c].card.playable]

    # Engine breadth, log-scaled: 0 members is fatal, 40 is not four times 10.
    engine = math.log1p(len(members))

    # Quality is the mean of the best TOP_K engine members, but averaged over
    # the *full* TOP_K rather than however many exist.  Otherwise a one-member
    # engine scores the quality of that single card: Starlight Road's only
    # engine link is Stardust Dragon, the highest-impact card in the pool, which
    # made a card with no engine at all look like a top-ten seed.
    top = sorted(members, key=lambda s: -s.impact)[:TOP_K]
    quality = sum(s.impact for s in top) / TOP_K if top else 0.0

    # Specificity: how much a want narrows the pool.  A seed asking for "1
    # monster" describes no deck.
    specificity = 0.0
    if seed.parsed.wants:
        specificity = max(
            exclusivity(idx.count(pred)) for pred, _ in seed.parsed.wants
        )

    # Reciprocity: engine members that want the seed back.
    reciprocity = sum(
        1.0
        for s in members
        if any(idx.satisfies(pred, seed.cid) for pred, _ in s.parsed.wants)
    )

    combo = 0.0
    for s in members:
        combo = max(
            combo,
            synergy.one_card_synchro(seed, s, idx, level_value),
            synergy.one_card_synchro(s, seed, idx, level_value),
        )
        for other in top:
            combo = max(combo, synergy.one_card_synchro(s, other, idx, level_value))

    total = (
        1.20 * engine
        + 1.00 * quality
        + 2.50 * specificity
        + 0.35 * math.log1p(reciprocity)
        + 1.50 * combo
        + 0.40 * max(0.0, seed.impact)
    )
    return SeedScore(
        card=seed.card,
        engine_size=len(members),
        engine=round(engine, 3),
        quality=round(quality, 3),
        specificity=round(specificity, 3),
        reciprocity=reciprocity,
        combo=round(combo, 3),
        total=round(total, 3),
    )


def rank(
    cards: list[Card],
    scored: dict[int, Scored],
    idx: MatchIndex,
    *,
    only=None,
    engines: dict[int, set[int]] | None = None,
) -> list[SeedScore]:
    """Score every playable card as a seed, best first.

    Pass a dict as *engines* to collect each seed's engine pool on the way
    through; pair scoring reuses them so it never recomputes a pool.
    """
    from otn_enhanced.deckgen.search import _level_value, engine_pool

    lv = _level_value(cards)
    out = []
    for c in cards:
        if not c.playable or c.is_extra:
            continue
        s = scored[c.cid]
        if only is not None and not only(s):
            continue
        out.append(score_seed(s, scored, idx, lv))
        if engines is not None:
            engines[c.cid] = engine_pool(s, scored, idx) - {c.cid}
    return sorted(out, key=lambda r: -r.total)


@dataclass
class PairScore:
    a: Card
    b: Card
    shared: int
    overlap: float
    mutual: bool
    total: float

    def row(self) -> str:
        link = "<->" if self.mutual else " + "
        return (
            f"{self.total:6.2f}  {self.a.name[:26]:28}{link}{self.b.name[:26]:28} "
            f"shared {self.shared:4}  overlap {self.overlap:4.2f}"
            + ("  mutual" if self.mutual else "")
        )


#: Two seeds whose engines overlap more than this are the same deck named twice.
SAME_ENGINE = 0.90
#: Overlap that makes a pair genuinely *complementary* rather than redundant.
COMPLEMENT_PEAK = 0.55
COMPLEMENT_WIDTH = 0.22


def engine_families(
    ranked: list[SeedScore], engines: dict[int, set[int]]
) -> dict[int, int]:
    """Group seeds that draw on the same engine, best-scoring one as representative.

    Nine Dragon cards sharing one 175-card engine generate 36 pairs that are all
    the same suggestion. Families collapse that: a pair is only reported once per
    pair of families, and two seeds in the *same* family are not a combination at
    all — they are synonyms.
    """
    family: dict[int, int] = {}
    reps: list[int] = []
    for r in ranked:
        e = engines.get(r.card.cid)
        if not e:
            continue
        for rep in reps:
            er = engines.get(rep, set())
            if not er:
                continue
            if len(e & er) / min(len(e), len(er)) >= SAME_ENGINE:
                family[r.card.cid] = rep
                break
        else:
            reps.append(r.card.cid)
            family[r.card.cid] = r.card.cid
    return family


def complement(overlap: float) -> float:
    """How *complementary* two engines are, peaked rather than monotonic.

    Rewarding overlap monotonically maximises at "these two cards are
    interchangeable", which is how the ranking filled up with synonyms. The
    interesting pairing shares a core but each side brings something, so the
    curve peaks around 0.55 and falls off toward both 0 (disjoint, nothing in
    common) and 1 (identical, no reason to name both).
    """
    return math.exp(-((overlap - COMPLEMENT_PEAK) ** 2) / (2 * COMPLEMENT_WIDTH ** 2))


def rank_pairs(
    ranked: list[SeedScore],
    engines: dict[int, set[int]],
    scored: dict[int, Scored],
    idx: MatchIndex,
    *,
    top: int = 150,
    limit: int = 40,
) -> list[PairScore]:
    """Rank *pairs* of seeds by whether they complement each other.

    Two seeds are only worth naming together if they draw on overlapping but not
    identical engines. Rekindling + Machine Duplication share *nothing* (overlap
    0.00) and produced a deck where Machine Duplication was dead; nine Dragon
    cards share *everything* (overlap 0.99) and are one deck, not a pairing.
    """
    head = ranked[:top]
    family = engine_families(ranked, engines)
    out: list[PairScore] = []
    seen_families: set[tuple[int, int]] = set()

    for i, ra in enumerate(head):
        ea = engines.get(ra.card.cid, set())
        if not ea:
            continue
        fa = family.get(ra.card.cid)
        for rb in head[i + 1:]:
            eb = engines.get(rb.card.cid, set())
            if not eb:
                continue
            fb = family.get(rb.card.cid)
            if fa is not None and fa == fb:
                continue  # same engine: synonyms, not a combination
            shared = len(ea & eb)
            if not shared:
                continue
            overlap = shared / min(len(ea), len(eb))
            mutual = rb.card.cid in ea or ra.card.cid in eb
            total = (
                0.5 * (ra.total + rb.total)
                + 6.0 * complement(overlap)
                + math.log1p(shared)
                + (1.5 if mutual else 0.0)
            )
            out.append(
                PairScore(ra.card, rb.card, shared, round(overlap, 3), mutual, round(total, 3))
            )

    out.sort(key=lambda r: -r.total)
    # One entry per family pair, so a family with ten members reports its best
    # partner once rather than ten near-identical rows.
    deduped: list[PairScore] = []
    for r in out:
        key = tuple(sorted((family.get(r.a.cid, r.a.cid), family.get(r.b.cid, r.b.cid))))
        if key in seen_families:
            continue
        seen_families.add(key)
        deduped.append(r)
        if len(deduped) >= limit:
            break
    return deduped
