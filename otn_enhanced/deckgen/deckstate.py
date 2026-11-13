"""Incremental deck state.

The search evaluates tens of thousands of candidate additions, so the deck score
must be cheap to recompute.  Rather than re-deriving pairwise synergy each time,
:class:`DeckState` keeps running accumulators — how many copies satisfy each
active want, how many cards carry each tag, the level histogram — and updating
them when a card is added costs one bit test per active predicate.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from otn_enhanced.deckgen import material
from otn_enhanced.deckgen.matchindex import MatchIndex, exclusivity
from otn_enhanced.deckgen.model import Predicate
from otn_enhanced.deckgen.score import Scored


#: Tags that mark a card as something you want to open with.
_STARTER_TAGS = frozenset({"searcher", "summoner", "draw", "gy_setup", "gy_filler"})

#: Verbs that pull a named card *out of the Deck* — what makes a card findable.
_FETCH_VERBS = frozenset({"search", "special_summon"})

#: Copies at which a want is so well covered that a searcher cannot add anything
#: measurable.  P(open >=1 of 14 in 40) = 0.994, so the whole remaining headroom
#: is 0.006 before exclusivity weighting scales it further down.
_ACCESS_SATURATED = 14

#: cid -> bitmask of pool cards it can fetch out of the Deck.  Memoised per
#: MatchIndex: the masks are fixed once the pool is parsed, and rebuilding them
#: inside the score loop would cost a predicate lookup per clause per call.
_FETCH_MASKS: dict[tuple[int, int], int] = {}


def fetch_mask(s: Scored, idx: MatchIndex) -> int:
    """Bitmask of pool cards *s* can search or Special Summon from the Deck."""
    key = (id(idx), s.cid)
    hit = _FETCH_MASKS.get(key)
    if hit is None:
        hit = 0
        for c in s.parsed.clauses:
            if (
                c.verb in _FETCH_VERBS
                and c.zone_from == "deck"
                and c.side == "you"
                and not c.self_ref
                and c.predicate is not None
                and not c.predicate.is_empty()
            ):
                hit |= idx.mask(c.predicate)
        _FETCH_MASKS[key] = hit
    return hit


#: (enabler cid, target cid) -> bool, for :func:`_can_cheat_out`.  DeckState.add
#: asks this about every pair in the deck on every add, which profiled at 1.36M
#: calls and 4.5s: the answer depends only on the two cards' parsed text, so it
#: is the same every time it is asked.
_CHEAT_OUT: dict[tuple[int, int], bool] = {}


def _can_cheat_out(enabler: Scored, target: Scored) -> bool:
    """Can *enabler* Special Summon *target* from hand or Deck, skipping tribute?"""
    key = (enabler.cid, target.cid)
    hit = _CHEAT_OUT.get(key)
    if hit is not None:
        return hit
    _CHEAT_OUT[key] = out = _compute_can_cheat_out(enabler, target)
    return out


def _compute_can_cheat_out(enabler: Scored, target: Scored) -> bool:
    if not target.card.is_monster or target.card.is_extra:
        return False
    return any(
        c.verb == "special_summon"
        and c.zone_from in ("hand", "deck")
        and c.side == "you"
        and not c.self_ref
        and c.predicate is not None
        and c.predicate.matches(target.card)
        for c in enabler.parsed.clauses
    )


def _real_archetype(name: str | None) -> bool:
    from otn_enhanced.deckgen.text.parse import is_real_archetype

    return is_real_archetype(name)


def _copy_counter(c: Counter) -> Counter:
    """Copy a Counter without going through ``Counter.__init__``.

    ``Counter.copy()`` is ``self.__class__(self)``, which routes through
    ``__init__`` -> ``update`` -> the mapping fast path.  Beam search clones a
    DeckState per candidate evaluation and each clone copies nine Counters, so
    this was 1.2M constructions and ~6s of a 78s profile.  Counter carries no
    state beyond its dict, so populating the dict directly is equivalent.
    """
    new = Counter.__new__(Counter)
    dict.update(new, c)
    return new


def sat(n: float, tau: float) -> float:
    """Saturating return: the first copy matters, the tenth barely does."""
    if n <= 0:
        return 0.0
    return 1.0 - math.exp(-n / tau)


@dataclass
class ActiveWant:
    """A want contributed by some card already in the deck."""

    pred: Predicate
    weight: float
    #: How specific the want is — a want matched by 2,000 cards earns little.
    exclusivity: float
    #: The predicate's pool bitmask, resolved once.  Fixed for the life of the
    #: want, and the access term needs it on every score call.
    mask: int
    #: True for "as many as possible" wants, which keep scaling with copy count.
    open_ended: bool
    #: Which cards asked for it (so removing a card can retire the want).
    askers: Counter = field(default_factory=Counter)
    #: Copies in the deck that satisfy it.
    satisfied: int = 0
    #: Copies in the deck that can *fetch* a satisfier out of the Deck.  Three
    #: Hecatrice make the "1 Valhalla" want six copies deep, not three.
    fetchers: int = 0
    #: Of those, copies belonging to the cards that asked for it.
    #:
    #: A want must not be satisfiable by the asker's own copies, or a card whose
    #: text names its own archetype bootstraps itself: three Gladiator Beast's
    #: Respite were the only "Gladiator Beast" cards in the deck and counted as
    #: satisfying their own requirement, and Mystical Cards of Light asks for
    #: "another Mystical Cards of Light" — a want whose entire matching pool is
    #: itself.
    self_satisfied: int = 0

    @property
    def met(self) -> int:
        """Copies satisfying this want that did not also ask for it."""
        return max(0, self.satisfied - self.self_satisfied)


@dataclass
class DeckState:
    """A partially built deck, with everything the score needs pre-aggregated."""

    idx: MatchIndex
    copies: dict[int, int] = field(default_factory=dict)
    extra: dict[int, int] = field(default_factory=dict)

    main_total: int = 0
    monsters: int = 0
    spells: int = 0
    traps: int = 0

    wants: dict[tuple, ActiveWant] = field(default_factory=dict)
    tags: Counter = field(default_factory=Counter)
    attributes: Counter = field(default_factory=Counter)
    races: Counter = field(default_factory=Counter)
    archetypes: Counter = field(default_factory=Counter)
    levels: Counter = field(default_factory=Counter)
    tuner_levels: Counter = field(default_factory=Counter)
    non_tuner_levels: Counter = field(default_factory=Counter)

    #: Capability -> copies that need it / copies that supply it.
    requires: Counter = field(default_factory=Counter)
    provides: Counter = field(default_factory=Counter)

    #: Cards the deck removes from itself when its thinners are used.
    thinning: int = 0
    #: cids some OTHER card in the deck can Special Summon from hand or Deck.
    #: Call of the Mummy, Valhalla and Lonefire Blossom put big bodies down for
    #: free, so a Level 8 Zombie alongside Call of the Mummy is not really paying
    #: two tributes for it.  Maintained incrementally: recomputing it inside the
    #: score would be O(deck^2 x clauses) on every one of ~6,000 score calls.
    cheatable: set = field(default_factory=set)

    #: Cumulative impact of the cards in the deck.
    impact_sum: float = 0.0
    #: Impact carried by searcher/draw cards, for the anti-greedy penalty.
    searcher_impact: float = 0.0
    #: Per-cid affinity to the seed, set once by the search; weights synergy so a
    #: self-satisfying clique unrelated to the seed cannot farm points.
    seed_affinity: dict[int, float] = field(default_factory=dict)
    #: Value of Levels reachable as a ONE-CARD Synchro line (a recruiter that
    #: Special Summons its own Synchro partner from the Deck).  Accumulated as
    #: cards are added, because recomputing it over every monster pair on each
    #: score call would be O(monsters^2) in the search's innermost loop.
    combo_value: float = 0.0
    #: Level -> (value, cid_a, cid_b) for the best one-card line at that Level.
    #: The cids are kept so the score can weight the line by how likely you are
    #: to actually draw both pieces — otherwise the search takes a 1-of of six
    #: different Tuners (six "lines" it will never assemble) instead of three
    #: Firedog and three Magician.
    combo_levels: dict[int, tuple[float, int, int]] = field(default_factory=dict)
    #: Synchro Level -> how good the best Synchro there is, set by the search.
    level_value: dict[int, float] = field(default_factory=dict)
    #: Copies of a gy_payoff card that is also somebody's Fusion material.
    millable_payoff: int = 0
    #: Copies of an enabler that mills the Deck BY NAMING A FUSION (Future
    #: Fusion).  Distinct from a plain gy_filler: it chooses what it sends.
    fusion_millers: int = 0
    #: cid -> Scored, so combo detection can reach the other cards in the deck.
    _scored_cache: dict = field(default_factory=dict, repr=False)
    #: The seed's engine, set by the search.  Opening consistency is measured
    #: against these, not against every card carrying a searcher tag: pooling all
    #: ~20 of those gives P(open one) ~= 1.0 for literally any deck, so the term
    #: saturated at its cap and stopped discriminating between decks at all.
    engine_cids: frozenset = frozenset()

    #: Bit set over the pool for every cid in this deck, Extra included, so a
    #: "can this searcher reach a card I actually run?" test is one int AND.
    deck_mask: int = 0
    #: OR of every active want's mask — "is this card wanted by ANYTHING here?".
    #: The payoff penalty asked that question per card per want per score call
    #: (2.4M `satisfies` calls in one profiled build); against this it is a
    #: single bit test.  Wants are only ever added, never retired in place
    #: (``_without`` rebuilds from scratch), so OR-ing on creation stays correct.
    wants_mask: int = 0
    #: cid -> copies, restricted to main-deck cards that fetch *something* out of
    #: the Deck.  Kept separate so the access term walks ~8 cards, not ~40.
    searchers: Counter = field(default_factory=Counter)
    #: cid -> that card's fetch bitmask, resolved once when it is added.
    searcher_masks: dict = field(default_factory=dict)

    # ── mutation ───────────────────────────────────────────────────────────
    def can_add(self, s: Scored, k: int, max_copies: int) -> bool:
        pool = self.extra if s.card.is_extra else self.copies
        return pool.get(s.cid, 0) + k <= max_copies

    def add(self, s: Scored, k: int = 1) -> None:
        """Add *k* copies of *s*, updating every accumulator."""
        bit = self.idx.index_of.get(s.cid)
        if bit is not None:
            self.deck_mask |= 1 << bit
        if s.card.is_extra:
            self.extra[s.cid] = self.extra.get(s.cid, 0) + k
            self._add_synchro_shape(s, k)
            # An Extra Deck card still ANSWERS wants: Instant Fusion asks for a
            # Level 5 or lower Fusion Monster and only the Extra Deck can supply
            # one.  This early return used to skip the want accounting entirely,
            # so that want read "unsatisfied" even with the Fusion sitting in the
            # deck, and the orphan penalty was charged forever.
            #
            # It deliberately does NOT contribute wants of its own: a Synchro's
            # "1 Tuner + 1 or more non-Tuner monsters" is summoning material, not
            # a deckbuilding requirement, and treating it as one would have every
            # Synchro demand Tuners the deck is already counting elsewhere.
            self._satisfy_wants(s, k)
            return

        self.copies[s.cid] = self.copies.get(s.cid, 0) + k
        self.main_total += k
        if s.card.is_monster:
            self.monsters += k
        elif s.card.card_class == "spell":
            self.spells += k
        else:
            self.traps += k

        self.impact_sum += k * s.impact
        if s.parsed.tags & {"searcher", "draw"}:
            self.searcher_impact += k * s.impact
        fm = fetch_mask(s, self.idx)
        if fm:
            self.searchers[s.cid] += k
            self.searcher_masks[s.cid] = fm

        for tag in s.parsed.tags:
            self.tags[tag] += k
        # Copies of a Graveyard payoff that some Fusion lists as a MATERIAL, so
        # a Fusion-milling enabler can send it on purpose rather than by luck.
        # See deckscore's fusion_mill term and synergy._is_fusion_material.
        if "gy_payoff" in s.parsed.tags:
            from otn_enhanced.deckgen.synergy import _is_fusion_material

            if _is_fusion_material(self.idx, s.cid):
                self.millable_payoff += k
        if ("fusion_payoff" in s.parsed.tags
                and "gy_setup" in s.parsed.tags
                and "send_gy" in s.parsed.provides):
            self.fusion_millers += k
        for cap in s.parsed.requires:
            self.requires[cap] += k
        for cap in s.parsed.provides:
            self.provides[cap] += k
        self.thinning += k * s.parsed.thins
        if s.card.is_monster:
            if s.card.attribute:
                self.attributes[s.card.attribute] += k
            if s.card.race:
                self.races[s.card.race] += k
            if s.card.level:
                self.levels[s.card.level] += k
                bucket = self.tuner_levels if s.card.is_tuner else self.non_tuner_levels
                bucket[s.card.level] += k
        # Only mechanically real archetypes count toward concentration; a shared
        # word ("Chaos") is not a theme.  See text.parse.is_real_archetype.
        if s.card.archetype and _real_archetype(s.card.archetype):
            self.archetypes[s.card.archetype] += k

        # Which big bodies this deck can now cheat onto the field.
        for cid in list(self.copies):
            other = self._scored_cache.get(cid)
            if other is None:
                continue
            if cid != s.cid and _can_cheat_out(s, other):
                self.cheatable.add(cid)
            if cid != s.cid and _can_cheat_out(other, s):
                self.cheatable.add(s.cid)

        # One-card Synchro lines this card opens up with what is already here.
        if self.level_value and s.card.is_monster and s.card.level:
            from otn_enhanced.deckgen import synergy as _syn

            for cid in list(self.copies):
                other = self._scored_cache.get(cid) if self._scored_cache else None
                if other is None or cid == s.cid:
                    continue
                v = max(
                    _syn.one_card_synchro(s, other, self.idx, self.level_value),
                    _syn.one_card_synchro(other, s, self.idx, self.level_value),
                )
                if v <= 0:
                    continue
                lvl = (s.card.level or 0) + (other.card.level or 0)
                if v > self.combo_levels.get(lvl, (0.0, 0, 0))[0]:
                    self.combo_levels[lvl] = (v, s.cid, other.cid)
        if self._scored_cache is not None:
            self._scored_cache[s.cid] = s

        # This card may satisfy wants already in the deck …
        self._satisfy_wants(s, k)
        # … and it contributes wants of its own.
        for pred, weight in s.parsed.wants:
            key = pred.key()
            want = self.wants.get(key)
            if want is None:
                n = self.idx.count(pred)
                want = ActiveWant(
                    pred=pred,
                    weight=weight,
                    exclusivity=exclusivity(n),
                    mask=self.idx.mask(pred),
                    open_ended=self._is_open(s, pred),
                    satisfied=self._count_matching(pred),
                )
                self.wants[key] = want
                self.wants_mask |= want.mask
            want.askers[s.cid] += k
            # Copies of the asker already counted as satisfying its own want.
            if self.idx.satisfies(pred, s.cid):
                want.self_satisfied = self.copies.get(s.cid, 0)

    def effective_deck_size(self) -> int:
        """Deck size after self-replacing cards are accounted for.

        Every hypergeometric figure below is computed against this rather than
        the raw 40, which is exactly the "3 Upstart = 37-card deck" reasoning.
        Floored so a thinner-heavy deck cannot drive the maths to nonsense.
        """
        return max(30, self.main_total - self.thinning)

    def combo_score(self) -> float:
        """One-card Synchro value x the real odds of assembling the line.

        Asymmetric on purpose: the starter has to be *drawn*, the target has to
        still be *in the Deck* for the starter to summon.  See
        :func:`hypergeom.combo_probability`.
        """
        from otn_enhanced.deckgen.hypergeom import combo_probability

        deck = self.effective_deck_size()
        total = 0.0
        for value, starter, target in self.combo_levels.values():
            ns, nt = self.copies.get(starter, 0), self.copies.get(target, 0)
            if not (ns and nt):
                continue
            total += value * combo_probability(ns, nt, deck)
        return total

    def opening_score(self, scored: dict) -> tuple[float, float]:
        """``(consistency, dead_draws)`` for the deck as built.

        *consistency* is the chance of opening at least one card that starts the
        deck doing something; *dead_draws* is the expected number of pure combo
        targets stranded in hand, which is the cost of over-running them.
        """
        from otn_enhanced.deckgen.hypergeom import (
            dead_draw_cost,
            opener_consistency,
        )

        deck = self.effective_deck_size()
        engine = self.engine_cids or self._derived_engine()
        starters, dead = [], 0.0
        for cid, n in self.copies.items():
            s = scored.get(cid)
            if s is None:
                continue
            if self.is_deck_target(cid, scored):
                dead += dead_draw_cost(n, deck)
                continue
            # A starter is a card that gets the *seed's* engine going, not any
            # card that happens to search something.
            if cid in engine and (
                s.parsed.tags & _STARTER_TAGS or s.impact > 0.0
            ):
                starters.append(n)
        return opener_consistency(starters, deck), dead

    def access_score(self, scored: dict, floor: float = 0.0) -> float:
        """How much consistency this deck's searchers buy for what it asks for.

        The want channel says "the deck contains three Valhalla"; it has no way
        to say "and six of my forty cards produce one".  That difference is what
        a searcher is actually *for* — its economy is a flat 1-for-1 once the
        self-discard is charged — so it needs its own term or the model has no
        reason left to run Hecatrice at all.

        Weighted exactly like ``synergy_wants``: by how much the want narrows the
        pool (``exclusivity``) and how close the asker sits to the seed, so
        making "1 monster" more findable earns nothing while making "1 Valhalla"
        more findable earns most of the term.
        """
        if not self.searchers or not self.wants:
            return 0.0
        from otn_enhanced.deckgen.hypergeom import search_access

        deck = self.effective_deck_size()
        total = 0.0
        for want in self.wants.values():
            met = want.met
            # A want with nothing answering it is the orphan penalty's business.
            # Fetchers cannot make a card the deck does not run any more findable.
            #
            # `met >= _ACCESS_SATURATED` is the cheap early-out that matters: at
            # 14 copies in 40 P(open) is already 0.994, so no number of searchers
            # can buy more than 0.006 — and those broad wants ("1 Machine
            # monster", met=25) are the ones every deck has several of.  Testing
            # two ints before touching a 4,076-bit mask is most of this term's
            # cost avoided.
            if met <= 0 or met >= _ACCESS_SATURATED or not want.weight:
                want.fetchers = 0  # so the report never shows a stale count
                continue
            targets = want.mask & self.deck_mask
            fetchers = 0
            for cid, n in self.searchers.items():
                # Clear the searcher's own bit: a card that satisfies a want and
                # also fetches it must not count as its own extra copy.
                bit = self.idx.index_of.get(cid)
                reachable = targets & ~(1 << bit) if bit is not None else targets
                if self.searcher_masks.get(cid, 0) & reachable:
                    fetchers += n
            want.fetchers = fetchers
            if not fetchers:
                continue
            affinity = max(
                (self.seed_affinity.get(cid, 1.0) for cid in want.askers), default=1.0
            )
            total += (
                want.weight
                * want.exclusivity
                * max(floor, affinity)
                * search_access(met, fetchers, deck)
            )
        return total

    def unsummonable_extra(self, scored: dict) -> int:
        """Copies in the Extra Deck this deck cannot legally put on the field.

        Nothing measured this.  ``DeckState.add`` deliberately does not register
        an Extra Deck card's wants — a Synchro's "1 Tuner + 1 or more non-Tuner
        monsters" is summoning material, not a deckbuilding requirement — but the
        side effect was that **an Extra Deck card's materials were never checked
        at all**, so a Fusion whose named pieces the deck does not run sat there
        costing nothing.  Its wants are read directly here instead of going
        through the want machinery, precisely to avoid re-introducing that.

        Only **certain** cases count:

        * a **Fusion** needing a Fusion Spell the deck does not run (contact
          Fusions are exempt — they shuffle their own materials away);
        * anything whose named materials, or named sole Summoner, are absent.

        **Synchro Level reach is deliberately NOT checked**, though it was in the
        first version.  Measured: that flagged **2.02 unsummonable copies per
        tournament deck against 0.41 per ROM AI deck** — backwards — and cost
        0.021 of deck AUC.  `reachable_synchro_levels` only sums Tuner + one or
        two non-Tuner Levels from the main deck, so it misses every real line
        built on Level modulation, a searched Tuner, or a Synchro revived from
        the Graveyard.  It was measuring the model's own blind spots rather than
        the deck's.  Construction already gates Synchro *selection* on reach in
        `_extra_candidates`; the penalty must not second-guess decks built
        elsewhere on a weaker approximation.
        """
        if not self.extra:
            return 0
        borrow = bool(self.provides.get("borrow_monster"))
        dead = 0
        for cid, n in self.extra.items():
            s = scored.get(cid)
            if s is None or s.card.is_synchro:
                continue
            if "fusion_summon" in s.parsed.requires and not self.provides.get(
                "fusion_summon"
            ):
                dead += n
                continue
            # Only *named* requirements are checked.  A generic material line
            # ("1 Tuner + 1+ non-Tuner") describes the summon, not a dependency,
            # and every deck with monsters can answer it.
            from otn_enhanced.deckgen.text.parse import SOLE_SUMMONER_MARK

            named = [
                pred for pred, _ in s.parsed.wants
                if (pred.exact_names or pred.archetype)
                # A deck that can steal the opponent's monsters can supply named
                # MATERIALS it does not run — Chimeratech Fortress Dragon off a
                # borrowed Cyber Dragon.  It cannot conjure a named SUMMONER
                # (NEX), which is a card you either run or do not.
                and not (
                    borrow and not pred.raw.endswith(SOLE_SUMMONER_MARK)
                )
            ]
            if named and not all(self._count_matching(p) > 0 for p in named):
                dead += n
        return dead

    def _derived_engine(self) -> frozenset:
        """The deck's own engine, for decks scored without a seed.

        A card is engine if it takes part in a want this deck actually satisfies
        — either it asks for something present, or it answers someone's ask.
        That is computable for any deck (the tournament and ROM corpora have no
        seed) and it discriminates: a goodstuff pile has almost none, a themed
        deck has most of its monsters.
        """
        out: set[int] = set()
        for want in self.wants.values():
            if not want.met:
                continue
            out.update(want.askers)
            for cid in self.copies:
                if self.idx.satisfies(want.pred, cid):
                    out.add(cid)
        return frozenset(out)

    def synchro_ready(self) -> float:
        """P(the opening hand holds exactly the pieces a Synchro needs)."""
        from otn_enhanced.deckgen.hypergeom import p_synchro_ready

        return p_synchro_ready(
            sum(self.tuner_levels.values()),
            sum(self.non_tuner_levels.values()),
            self.effective_deck_size(),
        )

    def is_deck_target(self, cid: int, scored: dict) -> bool:
        """Is this card here to be *found*, rather than drawn?

        True when some other card in the deck can Special Summon or search it out
        of the Deck, and it does little on its own — Flamvell Magician is a
        Firedog target, not a card you want in your opening hand.
        """
        s = scored.get(cid)
        if s is None or not s.card.is_monster or s.impact > 0.5:
            return False
        return any(
            other != cid
            and (o := scored.get(other)) is not None
            and any(
                c.verb in ("special_summon", "search")
                and c.zone_from == "deck"
                and c.side == "you"
                and c.predicate is not None
                and self.idx.satisfies(c.predicate, cid)
                for c in o.parsed.clauses
            )
            for other in self.copies
        )

    def _add_synchro_shape(self, s: Scored, k: int) -> None:
        """Extra-deck cards only contribute to the Extra Deck, not the ratios."""
        if s.card.archetype and _real_archetype(s.card.archetype):
            self.archetypes[s.card.archetype] += k

    @staticmethod
    def _is_open(s: Scored, pred: Predicate) -> bool:
        return any(
            c.predicate is not None
            and c.predicate.key() == pred.key()
            and c.count.kind in ("as_many", "all")
            for c in s.parsed.clauses
        )

    def _tuner_entries(self) -> list[tuple[int, "material.MaterialRule"]]:
        """``(Level, restriction)`` for every distinct Tuner in the main deck.

        Falls back to the plain Level counter when the scored cache has not seen
        a card, so this can never report *fewer* Tuners than the counter does.
        """
        out: list[tuple[int, material.MaterialRule]] = []
        seen_levels: Counter = Counter()
        for cid in self.copies:
            s = self._scored_cache.get(cid) if self._scored_cache else None
            if s is None or not s.card.is_monster or not s.card.is_tuner:
                continue
            if not s.card.level:
                continue
            out.append((s.card.level, material.rule_for(s.card)))
            seen_levels[s.card.level] += 1
        for lvl in self.tuner_levels:
            if not seen_levels[lvl]:
                out.append((lvl, material.MaterialRule()))
        return out

    def summonable_synchros(self, scored: dict[int, Scored]) -> set[int]:
        """Extra Deck Synchros some Tuner in this deck may legally Summon.

        Used to rank the Extra Deck, so it runs once per build rather than
        inside the scoring loop.
        """
        tuners = [
            (s.card, material.rule_for(s.card))
            for cid in self.copies
            if (s := (self._scored_cache or {}).get(cid)) is not None
            and s.card.is_monster
            and s.card.is_tuner
            and s.card.level
        ]
        if not tuners:
            return set()
        out: set[int] = set()
        for sy in scored.values():
            if not sy.card.is_synchro or not sy.card.level:
                continue
            for card, rule in tuners:
                if rule.never or not material.allows_target(rule, sy.card):
                    continue
                need = sy.card.level - card.level
                if need <= 0:
                    continue
                partners = material.partner_levels(rule, self.non_tuner_levels)
                if need in partners or any(
                    a + b == need for a in partners for b in partners
                ):
                    out.add(sy.cid)
                    break
        return out

    def _satisfy_wants(self, s: Scored, k: int) -> None:
        """Credit *k* copies of *s* against every want already in the deck."""
        for want in self.wants.values():
            if self.idx.satisfies(want.pred, s.cid):
                # "…with different names" counts NAMES: the second Ryko adds
                # nothing to Judgment Dragon's requirement.  Recount rather than
                # increment, since only the FIRST copy of a cid may count.
                if want.pred.distinct_names:
                    want.satisfied = self._count_matching(want.pred)
                    continue
                want.satisfied += k
                if s.cid in want.askers:
                    want.self_satisfied += k

    def _count_matching(self, pred: Predicate) -> int:
        """Copies already in the deck that satisfy *pred* (deck is <= 55 cards).

        Scans the Extra Deck too, so a want raised *after* its answer is already
        in the deck is seeded correctly.

        For a ``distinct_names`` predicate this counts distinct **cids**, not
        copies — 2 Lyla and 2 Ryko are four cards and two names, and Judgment
        Dragon wants four names.
        """
        total = 0
        for pool in (self.copies, self.extra):
            for cid, n in pool.items():
                if self.idx.satisfies(pred, cid):
                    total += 1 if pred.distinct_names else n
        return total

    def clone(self) -> "DeckState":
        """A deep-enough copy for beam search."""
        new = DeckState(
            idx=self.idx,
            copies=dict(self.copies),
            extra=dict(self.extra),
            main_total=self.main_total,
            monsters=self.monsters,
            spells=self.spells,
            traps=self.traps,
            tags=_copy_counter(self.tags),
            attributes=_copy_counter(self.attributes),
            races=_copy_counter(self.races),
            archetypes=_copy_counter(self.archetypes),
            levels=_copy_counter(self.levels),
            tuner_levels=_copy_counter(self.tuner_levels),
            non_tuner_levels=_copy_counter(self.non_tuner_levels),
            requires=_copy_counter(self.requires),
            provides=_copy_counter(self.provides),
            thinning=self.thinning,
            cheatable=set(self.cheatable),
            impact_sum=self.impact_sum,
            # Beam search clones a state per candidate, so an accumulator left
            # out here silently resets to 0 for every card the search actually
            # evaluates — the term then fires only in a direct test and never
            # during a build.  Measured that way: w_fusion_mill made no
            # difference at 1.5, 4.0 OR 10.0.
            millable_payoff=self.millable_payoff,
            fusion_millers=self.fusion_millers,
            searcher_impact=self.searcher_impact,
            seed_affinity=self.seed_affinity,  # read-only, shared deliberately
            combo_value=self.combo_value,
            combo_levels=dict(self.combo_levels),
            level_value=self.level_value,
            engine_cids=self.engine_cids,
            deck_mask=self.deck_mask,
            wants_mask=self.wants_mask,
            searchers=_copy_counter(self.searchers),
            # Shared, not copied: this is a pure cid -> mask memo.  A clone may
            # add entries, but the value for a given cid is a function of the
            # card alone, so every writer writes the same bits and leaking an
            # entry back to the parent is exactly the caching we want.
            searcher_masks=self.searcher_masks,
            _scored_cache=dict(self._scored_cache),
        )
        new.wants = {
            k: ActiveWant(
                pred=w.pred,
                weight=w.weight,
                exclusivity=w.exclusivity,
                mask=w.mask,
                open_ended=w.open_ended,
                askers=_copy_counter(w.askers),
                satisfied=w.satisfied,
                fetchers=w.fetchers,
                self_satisfied=w.self_satisfied,
            )
            for k, w in self.wants.items()
        }
        return new

    # ── queries ────────────────────────────────────────────────────────────
    def signature(self) -> frozenset:
        """Identity for beam de-duplication."""
        return frozenset(
            list(self.copies.items()) + [("x", cid, n) for cid, n in self.extra.items()]
        )

    def reachable_synchro_levels(self) -> set[int]:
        """Levels obtainable as (one Tuner + one or more non-Tuners).

        Honours the per-Tuner partner bans, which pure Level arithmetic cannot
        see: Debris Dragon's "the other Synchro Material(s) cannot be Level 4"
        removes every Level 4 non-Tuner from ITS pairings only, and in a deck
        whose non-Tuners are mostly Level 4 that is most of its apparent reach.
        """
        out: set[int] = set()
        for t, rule in self._tuner_entries():
            if rule.never:
                continue
            partners = material.partner_levels(rule, self.non_tuner_levels)
            for n in partners:
                out.add(t + n)
            # Two non-Tuners plus the Tuner is common enough to count.
            for n1 in partners:
                for n2 in partners:
                    out.add(t + n1 + n2)
        return out
