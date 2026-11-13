"""Opening-hand probabilities, and the hand-versus-deck distinction.

Two things a deck builder trades off that a flat copy count cannot express:

* **Cards you want to SEE.** Starters, staples, hand traps — value comes from
  holding one in the opening hand, so what matters is ``P(at least one in 5)``.
  That curve is steeply saturating: going 1 -> 2 copies buys far more than
  2 -> 3, which is why real lists run 3 of the card that starts the deck and 1 of
  the boss it eventually makes.

* **Cards you want in the DECK.** Combo targets are the opposite. Flamvell
  Magician is not a card you want to draw — it is a card you want Flamvell
  Firedog to *find*. Drawing it is close to a dead card, and running out of
  copies makes the searcher whiff. Its value is ``P(a copy is still in the
  Deck)`` weighted against ``E[copies stranded in hand]``.

Treating both as "more copies is better, saturating" is what produced a deck
with one Firedog and one Magician: a line that exists on paper and is assembled
essentially never.
"""

from __future__ import annotations

from functools import lru_cache
from math import comb

#: Cards seen by the time you act on turn one, going second-ish.
DEFAULT_HAND = 5


# Every function here is a pure function of two-to-four small integers, and the
# search calls them from inside the score loop: ~962k calls to p_at_least_k
# alone in one profiled build, over maybe a few hundred distinct argument
# tuples.  Caching them is free correctness-wise and removes the binomials.
@lru_cache(maxsize=8192)
def p_at_least_k(copies: int, deck: int, hand: int = DEFAULT_HAND, k: int = 1) -> float:
    """Probability of drawing at least *k* copies in an opening hand of *hand*.

    ``copies`` is clamped to ``deck``: :func:`opener_consistency` pools every
    starter into one group, and that pooled count can legitimately exceed the
    *effective* deck size once thinning is subtracted.
    """
    copies = min(max(copies, 0), max(deck, 0))
    if copies <= 0 or deck <= 0 or hand <= 0 or k > copies:
        return 0.0
    hand = min(hand, deck)
    total = comb(deck, hand)
    if total == 0:
        return 0.0
    # P(at least k) = 1 - sum_{i<k} P(exactly i)
    below = 0
    for i in range(0, min(k, copies + 1)):
        rest = hand - i
        if rest < 0 or rest > deck - copies:
            continue
        below += comb(copies, i) * comb(deck - copies, rest)
    return max(0.0, 1.0 - below / total)


def p_open(copies: int, deck: int = 40, hand: int = DEFAULT_HAND) -> float:
    """Probability of holding at least one copy in the opening hand."""
    return p_at_least_k(copies, deck, hand, 1)


def expected_in_hand(copies: int, deck: int = 40, hand: int = DEFAULT_HAND) -> float:
    """Expected number of copies drawn — the hypergeometric mean."""
    if deck <= 0:
        return 0.0
    return copies * min(hand, deck) / deck


@lru_cache(maxsize=4096)
def p_left_in_deck(copies: int, deck: int = 40, hand: int = DEFAULT_HAND) -> float:
    """Probability at least one copy is still in the Deck after the opening hand.

    This is what a search or recruit target needs: not to be *drawn*, but to be
    *there*.  Equal to 1 - P(all copies were drawn).
    """
    copies = min(max(copies, 0), max(deck, 0))
    if copies <= 0 or deck <= 0:
        return 0.0
    hand = min(hand, deck)
    if copies > hand:
        return 1.0
    total = comb(deck, hand)
    if total == 0:
        return 0.0
    return 1.0 - comb(deck - copies, hand - copies) / total


def combo_probability(
    starter_copies: int,
    target_copies: int,
    deck: int = 40,
    hand: int = DEFAULT_HAND,
) -> float:
    """Chance of assembling a one-card line: starter in hand, target in Deck.

    Deliberately asymmetric.  Firedog wants to be *drawn*; Magician wants to be
    *left in the Deck* for Firedog to summon.  Multiplying two "more is better"
    curves instead treats the target like a second starter and undervalues the
    third Firedog while overvaluing the third Magician.
    """
    return p_open(starter_copies, deck, hand) * p_left_in_deck(target_copies, deck, hand)


def opener_consistency(starter_copies: list[int], deck: int = 40, hand: int = DEFAULT_HAND) -> float:
    """How live the opening hand is, pooling the starters into one group.

    Blends ``P(>=1)`` with ``P(>=2)``.  ``P(>=1)`` alone is a bad discriminator:
    any competent deck runs enough engine that it sits at 0.99+, so the term
    saturated and stopped separating decks.  Opening two live cards instead of
    one is most of the difference between a good hand and a mediocre one, and
    that probability has real spread.
    """
    total = sum(c for c in starter_copies if c > 0)
    if total <= 0:
        return 0.0
    return 0.5 * p_at_least_k(total, deck, hand, 1) + 0.5 * p_at_least_k(
        total, deck, hand, 2
    )


@lru_cache(maxsize=4096)
def p_synchro_ready(
    tuners: int, non_tuners: int, deck: int = 40, hand: int = DEFAULT_HAND
) -> float:
    """Probability the opening hand can actually Synchro Summon.

    A Synchro needs **exactly one Tuner plus one or more non-Tuners** — two
    Tuners cannot be used together.  So the quantity that matters is
    ``P(>=1 Tuner AND >=1 non-Tuner)``, by inclusion-exclusion, and it is what
    fixes the Tuner ratio without anyone naming a target ratio: it peaks around
    a third of the monsters being Tuners and falls off in both directions.

    Nothing in the model measured this before, so a Tuner was a pure bonus and
    the search happily built 8 Tuners against 10 non-Tuners.
    """
    if deck <= 0 or hand <= 0:
        return 0.0
    tuners = max(0, min(tuners, deck))
    non_tuners = max(0, min(non_tuners, deck - tuners))
    hand = min(hand, deck)
    total = comb(deck, hand)
    if total == 0 or tuners == 0 or non_tuners == 0:
        return 0.0

    def miss(exclude: int) -> int:
        rest = deck - exclude
        return comb(rest, hand) if rest >= hand else 0

    no_t = miss(tuners)
    no_n = miss(non_tuners)
    neither = miss(tuners + non_tuners)
    return max(0.0, 1.0 - (no_t + no_n - neither) / total)


def dead_draw_cost(copies: int, deck: int = 40, hand: int = DEFAULT_HAND) -> float:
    """Expected copies of a deck-only card stranded in the opening hand."""
    return expected_in_hand(copies, deck, hand)


def effective_copies(copies: int, fetchers: int, deck: int = 40) -> int:
    """Copies of a card, counting everything in the deck that can go and get it.

    A searcher is, for the purpose of "do I open my payoff", another copy of the
    payoff.  Three Hecatrice alongside three Valhalla is a deck with **six** ways
    to have Valhalla in hand, not three — and nothing in the model said so.
    """
    return min(max(copies, 0) + max(fetchers, 0), max(deck, 0))


def search_access(
    copies: int, fetchers: int, deck: int = 40, hand: int = DEFAULT_HAND
) -> float:
    """How much consistency a searcher buys for the card it finds.

    ``P(open effective) - P(open raw)``: for Valhalla at 3 copies in 40, three
    Hecatrice move it from 34% to 58%, and that 0.24 is the whole reason the card
    is in the deck.  Its economy is a flat 1-for-1 (see
    :func:`economy._spent_from_hand`), so without this term the model had no way
    left to want it at all.

    Saturating by construction — 3 -> 6 effective copies buys 0.24, 6 -> 9 buys
    0.13 — so this cannot be farmed by stacking searchers.
    """
    raw = p_open(copies, deck, hand)
    return max(0.0, p_open(effective_copies(copies, fetchers, deck), deck, hand) - raw)
