"""Predicate -> bitmask over the card pool.

Evaluating "does card B satisfy card A's want?" naively is 4,076² predicate
calls.  Instead: every distinct predicate is evaluated against the pool *once*
and stored as a bitmask, so the question becomes a single bit test.

The masks are plain Python ``int``s rather than a numpy array.  A 4,076-bit
integer is one object, ``&``/``|`` are C-speed, and ``int.bit_count()`` gives
population count directly — which is all this needs, with no array bookkeeping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from otn_enhanced.deckgen.model import Card, ParsedCard, Predicate

#: Verbs whose want means "I need this card in the Deck to find/summon".
SEARCH_VERBS = frozenset({"search", "special_summon", "send", "equip"})

#: A want matching more than this many cards is not a dedicated searcher.
DEDICATED_MAX = 200


def exclusivity(match_count: int) -> float:
    """How much information a predicate carries, given how many cards it matches.

    A want satisfied by 2,000 cards says almost nothing about deck construction;
    one satisfied by 6 says a lot.  Used both here (searchability) and by the
    synergy model, so the two agree on what "specific" means.
    """
    if match_count <= 0:
        return 0.0
    return 1.0 / math.log2(2.0 + match_count / 40.0)


@dataclass
class MatchIndex:
    """Bitmask lookup over a fixed card pool."""

    cards: list[Card]
    index_of: dict[int, int] = field(default_factory=dict)  # cid -> bit position
    masks: dict[tuple, int] = field(default_factory=dict)  # predicate key -> mask
    reps: dict[tuple, Predicate] = field(default_factory=dict)
    #: cid -> exclusivity-weighted count of pool cards that can search/summon it
    searchers: dict[int, float] = field(default_factory=dict)
    #: Bitmask of every card that some Fusion Monster lists as a MATERIAL.
    #:
    #: Future Fusion's real payoff is the mill, not the Summon: it names a
    #: Fusion and sends that Fusion's materials from the Deck to the GY.  So a
    #: Graveyard payoff which is also somebody's Fusion material gets milled on
    #: purpose, where an ordinary mill would have to hit it by luck.
    #: Pool-level on purpose — see synergy._is_fusion_material.
    fusion_material_mask: int = 0

    @classmethod
    def build(cls, cards: list[Card], parsed: dict[int, ParsedCard]) -> "MatchIndex":
        idx = cls(cards=cards, index_of={c.cid: i for i, c in enumerate(cards)})

        for pc in parsed.values():
            for pred, _ in pc.wants:
                idx.reps.setdefault(pred.key(), pred)
        for key, pred in idx.reps.items():
            mask = 0
            for i, c in enumerate(cards):
                if pred.matches(c):
                    mask |= 1 << i
            idx.masks[key] = mask

        # Materials of every Fusion in the pool, unioned.  Support wants are
        # skipped: a Fusion's "supports LIGHT" is not one of its materials.
        from otn_enhanced.deckgen.text.parse import SUPPORT_WANT_PREFIX

        for pc in parsed.values():
            card = cards[idx.index_of[pc.cid]] if pc.cid in idx.index_of else None
            if card is None or not card.is_extra or card.is_synchro:
                continue
            for pred, _ in pc.wants:
                if (pred.raw or "").startswith(SUPPORT_WANT_PREFIX):
                    continue
                idx.fusion_material_mask |= idx.masks.get(pred.key(), 0)

        # How findable each card is.  Derived by running every search-shaped
        # want across the pool — nothing hand-typed.
        #
        # Weighted by *exclusivity*: a card that says "add 1 monster from your
        # Deck" barely makes any particular monster more findable, whereas
        # "add 1 'Genex' monster" makes Genex Controller genuinely consistent.
        # Unweighted, every card scored 70-100 searchers and the signal vanished.
        weights = [0.0] * len(cards)
        for pc in parsed.values():
            for pred, _ in pc.wants:
                if not any(
                    c.verb in SEARCH_VERBS
                    and c.predicate is not None
                    and c.predicate.key() == pred.key()
                    for c in pc.clauses
                ):
                    continue
                mask = idx.masks.get(pred.key(), 0)
                n = mask.bit_count()
                # Only *dedicated* searchers count.  "Add 1 monster from your
                # Deck" is not what makes a card consistent, and including such
                # wants flattened this metric to a constant across the pool.
                if n == 0 or n > DEDICATED_MAX:
                    continue
                w = exclusivity(n)
                while mask:
                    low = mask & -mask
                    weights[low.bit_length() - 1] += w
                    mask ^= low
        idx.searchers = {c.cid: round(weights[i], 4) for i, c in enumerate(cards)}
        return idx

    #: Bumped whenever the meaning of a stored mask changes.
    SCHEMA = "deckgen.matchindex.v1"

    @classmethod
    def load(
        cls, cards: list[Card], parsed: dict[int, ParsedCard], *, force: bool = False
    ) -> "MatchIndex":
        """:meth:`build`, cached to disk.

        Building evaluates 768 predicates against 4,076 cards — 3.1M
        ``Predicate.matches`` calls and 2.6s — to produce integers that depend
        only on the pool and the parse, both of which are themselves cached and
        hashed.  So the answer is recomputed on every invocation for no reason.

        The masks are big ``int``s and the keys are tuples of primitives, so the
        artifact is plain data; :mod:`.cache` discards it as soon as the parse,
        the pool or this module changes.
        """
        from pathlib import Path

        from otn_enhanced.deckgen import cache
        from otn_enhanced.deckgen.text import parse as parse_mod

        key = cache.source_map(
            [
                Path(__file__).resolve(),
                Path(__file__).resolve().parent / "model.py",
                cache.CACHE_DIR / f"{parse_mod.SCHEMA}.pkl",
            ]
        )
        hit = None if force else cache.load_pickle(cls.SCHEMA, key)
        if hit is not None:
            return cls(
                cards=cards,
                index_of=hit["index_of"],
                masks=hit["masks"],
                reps=hit["reps"],
                searchers=hit["searchers"],
            )
        idx = cls.build(cards, parsed)
        cache.store_pickle(
            cls.SCHEMA,
            key,
            {
                "index_of": idx.index_of,
                "masks": idx.masks,
                "reps": idx.reps,
                "searchers": idx.searchers,
            },
        )
        return idx

    # ── queries ────────────────────────────────────────────────────────────
    def mask(self, pred: Predicate) -> int:
        """Bitmask of every pool card matching *pred*, computing it if unseen."""
        key = pred.key()
        hit = self.masks.get(key)
        if hit is None:
            hit = 0
            for i, c in enumerate(self.cards):
                if pred.matches(c):
                    hit |= 1 << i
            self.masks[key] = hit
            self.reps.setdefault(key, pred)
        return hit

    def count(self, pred: Predicate) -> int:
        """How many distinct pool cards match *pred*."""
        return self.mask(pred).bit_count()

    def satisfies(self, pred: Predicate, cid: int) -> bool:
        i = self.index_of.get(cid)
        return i is not None and bool(self.mask(pred) >> i & 1)

    def matching_cids(self, pred: Predicate) -> list[int]:
        mask = self.mask(pred)
        out: list[int] = []
        while mask:
            low = mask & -mask
            out.append(self.cards[low.bit_length() - 1].cid)
            mask ^= low
        return out

    def searchability(self, cid: int) -> float:
        """Exclusivity-weighted count of pool cards that can fetch or summon *cid*."""
        return self.searchers.get(cid, 0.0)
