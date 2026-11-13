"""Human-readable deck report.

Shows per-card economy and power so a decision can be argued with, plus the two
things that are easy to get wrong and invisible in a bare card list: which cards
are in the deck to satisfy which *want*, and which Synchro Levels the chosen
Tuners and non-Tuners can actually make.
"""

from __future__ import annotations

from collections import Counter

from otn_enhanced.deckgen.deckstate import DeckState
from otn_enhanced.deckgen.matchindex import MatchIndex
from otn_enhanced.deckgen.model import Card
from otn_enhanced.deckgen.score import Scored
from otn_enhanced.deckgen.search import GeneratedDeck


def _card_line(card: Card, n: int, s: Scored, in_deck: float | None = None) -> str:
    stats = ""
    if card.is_monster:
        lvl = f"L{card.level}" if card.level else "  "
        atk = "?" if card.atk < 0 else str(card.atk)
        dfn = "?" if card.def_ < 0 else str(card.def_)
        stats = f"{card.attribute or '':6} {card.race or '':14} {lvl:>3} {atk:>5}/{dfn:<5}"
    else:
        stats = f"{card.st_subtype or 'Normal':<10} {card.card_class:<6}{'':15}"
    # For a deck-dependent card the context-free economy is misleading on its own:
    # Rekindling reads -1.00 in isolation but is positive in a deck that feeds it.
    econ = f"econ{s.econ.exp:+6.2f}"
    if in_deck is not None and abs(in_deck - s.econ.exp) > 0.05:
        econ = f"econ{s.econ.exp:+6.2f} ->{in_deck:+5.2f} in deck"
    return f"  {n}x {card.name[:34]:36} {stats} {econ}  impact{s.impact:+6.2f}"


def _in_deck_econ(card: Card, st: DeckState, scored: dict[int, Scored]) -> float | None:
    """A context-sensitive card's economy given what this deck actually holds."""
    from otn_enhanced.deckgen.economy import deck_adjusted_exp

    s = scored.get(card.cid)
    if s is None or not s.econ.context_sensitive:
        return None
    available = 0
    for pred, _ in s.parsed.wants:
        want = st.wants.get(pred.key())
        if want is not None and want.open_ended:
            available = max(available, want.met)
    return deck_adjusted_exp(card, s.parsed, available) if available else None


def _group(deck: GeneratedDeck, by_cid: dict[int, Card], counts: dict[int, int]):
    rows = [(by_cid[cid], n) for cid, n in counts.items() if cid in by_cid]
    return sorted(rows, key=lambda t: (not t[0].is_monster, t[0].card_class, -t[1], t[0].name))


def render(
    deck: GeneratedDeck,
    cards: list[Card],
    scored: dict[int, Scored],
    idx: MatchIndex,
) -> str:
    by_cid = {c.cid: c for c in cards}
    st = deck.state
    out: list[str] = []

    out.append("=" * 78)
    names = ", ".join(s.name for s in (deck.seeds or [deck.seed]))
    out.append(f"DECK from seed{'s' if len(deck.seeds or [1]) > 1 else ''}: {names}")
    out.append("=" * 78)
    out.append(f"  {st.main_total} main ({st.monsters} monsters / {st.spells} spells / "
               f"{st.traps} traps)   {sum(st.extra.values())} extra")
    out.append(f"  lambda_synergy = {deck.lambda_synergy}")
    out.append("")
    out.append(deck.score.format())

    if deck.violations:
        out.append("")
        out.append("  ILLEGAL:")
        out.extend(f"    - {v}" for v in deck.violations)
    if deck.bundle_debt:
        out.append(f"  unmet bundles: {', '.join(deck.bundle_debt)}")

    # Card counts in the headers, because the two lists are both monster-heavy and
    # run together when the report is scrolled: an Extra Deck full of Synchros
    # reads as though it were still part of the main deck.
    out.append("")
    out.append(f"-- MAIN DECK ({st.main_total} cards) " + "-" * 52)
    for card, n in _group(deck, by_cid, st.copies):
        out.append(_card_line(card, n, scored[card.cid], _in_deck_econ(card, st, scored)))

    if st.extra:
        n_extra = sum(st.extra.values())
        out.append("")
        out.append(f"-- EXTRA DECK ({n_extra} cards) " + "=" * 51)
        for card, n in sorted(
            ((by_cid[c], n) for c, n in st.extra.items()), key=lambda t: (t[0].level or 0)
        ):
            out.append(_card_line(card, n, scored[card.cid]))
        out.append("-" * 78)

    # ── did the deck stay built around its seeds? ─────────────────────────
    if getattr(deck, "holdout", None):
        out.append("")
        out.append("-- SEED HOLDOUT " + "-" * 61)
        out.append("  (strip each seed, then ask what the deck wants most)")
        for name, rank, gain in deck.holdout:
            if rank == 1:
                verdict = "the deck's top pick"
            elif rank > 0 and rank <= 10:
                verdict = f"still top-{rank}"
            elif rank > 0:
                verdict = f"rank {rank} — deck drifted off this seed"
            else:
                verdict = "NOT competitive — deck is not built around it"
            out.append(f"  {name[:36]:38} {gain:+7.3f}  {verdict}")

    if getattr(deck, "anti_seeds", None):
        out.append("")
        out.append("-- ANTI-SEEDS " + "-" * 63)
        out.append("  banned from this build: " + ", ".join(deck.anti_seeds))

    short_extra = 15 - sum(deck.extra.values())
    if getattr(deck, "filled", None) or short_extra > 0:
        out.append("")
        out.append("-- FORCE-FILLED " + "-" * 61)
    if getattr(deck, "filled", None):
        out.append("  the search stopped short; these were added on impact "
                   "to reach 40 main / 15 extra:")
        for name, n in Counter(deck.filled).most_common():
            out.append(f"  {n}x {name}")
    if short_extra > 0:
        out.append(f"  extra deck is {sum(deck.extra.values())}/15 — the pool has no "
                   f"other legal Extra Deck card left")
        out.append("  (copy limits / --allowed-types exhausted, not a search failure)")

    if getattr(deck, "monster_filter", None):
        out.append("")
        out.append("-- MONSTER FILTER " + "-" * 59)
        out.append("  monsters restricted to: " + deck.monster_filter.describe())
        if getattr(deck, "filter_exempt", None):
            out.append("  seeds kept despite the filter: "
                       + ", ".join(deck.filter_exempt))

    if getattr(deck, "swaps", None):
        out.append("")
        out.append("-- BOOTSTRAP SWAPS " + "-" * 58)
        for s in deck.swaps:
            out.append(f"  {s}")

    # ── where the build spent its time ────────────────────────────────────
    # Always shown, not just under -v: "the builder is slow" was previously a
    # complaint with no evidence attached, and `us/call` separates a scoring
    # regression from a search-shape one without reaching for a profiler.
    stats = getattr(deck, "stats", None)
    if stats is not None and stats.rows:
        out.append("")
        out.append("-- BUILD TIMING " + "-" * 61)
        out.extend(stats.format())

    # ── which wants the deck actually answers ──────────────────────────────
    out.append("")
    out.append("-- WANTS " + "-" * 68)
    wants = sorted(st.wants.values(), key=lambda w: -(w.weight * w.exclusivity))
    for w in wants[:14]:
        asked_by = ", ".join(
            by_cid[cid].name for cid in list(w.askers)[:2] if cid in by_cid
        )
        mark = "OK " if w.met else "-- "
        # "+N found" is the search-access channel: N more cards in the deck can
        # go and get one, so the want is effectively met+N copies deep on the
        # opening hand even though only `met` are physically in the deck.
        found = f" +{w.fetchers} found" if w.fetchers else ""
        out.append(
            f"  {mark}{w.met:2} copies satisfy {w.pred.raw[:44]:46} "
            f"(pool {idx.count(w.pred):4}){found} <- {asked_by[:30]}"
        )
    unmet = [w for w in wants if not w.met]
    if unmet:
        out.append(f"  {len(unmet)} want(s) unsatisfied — each costs the orphan penalty")

    # ── Synchro reach ──────────────────────────────────────────────────────
    out.append("")
    out.append("-- SYNCHRO REACH " + "-" * 60)
    out.append(f"  tuner levels     : {dict(sorted(st.tuner_levels.items()))}")
    out.append(f"  non-tuner levels : {dict(sorted(st.non_tuner_levels.items()))}")
    reach = st.reachable_synchro_levels()
    in_extra = Counter(by_cid[c].level for c in st.extra if c in by_cid)
    avail = {s.card.level for s in scored.values() if s.card.is_synchro and s.card.level}
    out.append(f"  reachable levels : {sorted(l for l in reach if l in avail)}")
    out.append(f"  extra deck levels: {dict(sorted(in_extra.items()))}")
    orphans = [lvl for lvl in in_extra if lvl not in reach]
    if orphans:
        out.append(f"  UNREACHABLE in extra deck: {sorted(orphans)}")

    # ── curve and composition ──────────────────────────────────────────────
    out.append("")
    out.append("-- COMPOSITION " + "-" * 62)
    out.append(f"  levels     : {dict(sorted(st.levels.items()))}")
    out.append(f"  attributes : {dict(st.attributes.most_common())}")
    out.append(f"  races      : {dict(st.races.most_common(6))}")
    if st.archetypes:
        out.append(f"  archetypes : {dict(st.archetypes.most_common(5))}")
    out.append(f"  tags       : {dict(st.tags.most_common(10))}")

    errata = [by_cid[c].name for c in st.copies if by_cid[c].stat_conflict]
    out.append("")
    out.append("  NOTE: effect text comes from ygoprodeck and reflects MODERN errata;")
    out.append("        Over the Nexus is a 2011 engine, so some cards behave differently")
    out.append("        in-ROM than the text implies.  ROM stats always win.")
    if errata:
        out.append(f"        stat disagreements in this deck: {errata}")

    if deck.alternates:
        out.append("")
        out.append("-- ALTERNATES " + "-" * 63)
        for alt in deck.alternates:
            uniq = set(alt.main) - set(deck.main)
            out.append(
                f"  lambda={alt.lambda_synergy}: score {alt.score.total:+.2f}, "
                f"{len(uniq)} different cards"
            )
    return "\n".join(out)
