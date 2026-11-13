"""Score a whole deck, and the marginal gain of adding a card to it.

The objective has three jobs:

1. reward good cards (``impact_sum``);
2. reward cards that answer each other's needs (the saturating synergy terms);
3. **stop the greedy search from building a deck of nothing but searchers.**

Job 3 is the one that needs deliberate machinery.  Searchers have high standalone
impact, so a plain greedy maximiser picks twelve of them and zero payoffs.  Two
terms prevent it: synergy *saturates*, so the sixth copy satisfying a want earns
almost nothing, and ``penalty.payoff`` charges quadratically once searcher value
outruns the value of the things being searched for.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from otn_enhanced.deckgen.deckstate import DeckState, sat
from otn_enhanced.deckgen.economy import deck_adjusted_exp
from otn_enhanced.deckgen.params import Params, default
from otn_enhanced.deckgen.score import Scored, impact_from_exp


@dataclass
class DeckScore:
    total: float
    terms: dict[str, float] = field(default_factory=dict)

    def format(self) -> str:
        rows = "\n".join(f"    {k:26} {v:+8.3f}" for k, v in self.terms.items() if v)
        return f"deck score {self.total:+.3f}\n{rows}"


#: Available Synchro Levels, memoised per scored-pool.  Deriving this inside
#: score() scanned all 4,076 cards on every call — 24.4 MILLION `is_synchro`
#: checks in one build, and the single largest cost in the profile — to
#: recompute a value that never changes.
_SYNCHRO_LEVELS: dict[int, set[int]] = {}

#: How many times :func:`score` has been called this process.  A build makes tens
#: of thousands of these and almost all of its time is inside them, so this is
#: the one number that explains "why is the builder slow" — the search reports it
#: per phase.  Incrementing an int is free next to the work the call does.
CALLS = 0


def _available_levels(scored: dict[int, Scored]) -> set[int]:
    key = id(scored)
    hit = _SYNCHRO_LEVELS.get(key)
    if hit is None:
        hit = {s.card.level for s in scored.values() if s.card.is_synchro and s.card.level}
        _SYNCHRO_LEVELS[key] = hit
    return hit


#: cid -> "does this card answer the opponent?".  A property of the card's own
#: parsed text, so it never changes, but the role-balance term used to re-derive
#: it by scanning every clause of every deck card on every score call.
_INTERACTION: dict[int, bool] = {}

#: Verbs that count as interacting with the opponent's board.
_INTERACTION_VERBS = frozenset(
    {"destroy", "banish", "bounce", "negate", "shuffle", "take_control",
     "control_swap"}
)


def _is_interaction(s: Scored) -> bool:
    """Does this card remove, negate or floodgate the opponent?

    Any Trap that removes counts: Dimensional Prison and Bottomless Trap Hole put
    their removal in a ``condition``-kind clause, so gating on ``kind == "gain"``
    saw four interaction cards in a deck holding eleven and pinned the
    role-balance penalty at its maximum.
    """
    hit = _INTERACTION.get(s.cid)
    if hit is None:
        _INTERACTION[s.cid] = hit = bool(
            s.parsed.tags & {"negate", "floodgate", "mass_removal", "hand_trap"}
            or s.card.card_class == "trap"
            or any(
                c.verb in _INTERACTION_VERBS
                and c.side in ("opponent", "both", "either", "auto")
                for c in s.parsed.clauses
            )
        )
    return hit


def _concentration(counter, tau: float) -> float:
    """Saturating reward for a deck that commits to one attribute / race."""
    if not counter:
        return 0.0
    return sat(max(counter.values()), tau)


def score(
    state: DeckState,
    scored: dict[int, Scored],
    p: Params | None = None,
    *,
    lambda_synergy: float | None = None,
) -> DeckScore:
    """Score *state*.  Higher is better; the search maximises this."""
    global CALLS
    CALLS += 1
    p = p or default()
    lam = lambda_synergy if lambda_synergy is not None else float(p["deck.lambda_synergy"])
    terms: dict[str, float] = {"impact": round(state.impact_sum, 3)}

    # ── the card actually getting what it asked for ───────────────────────
    # This is the term that makes a *themed* deck beat a pile of individually
    # strong cards.  economy() is context-free by design, so Rekindling scores
    # -1.00 in isolation; once the deck holds nine FIRE monsters with 200 DEF it
    # is really about +0.80, and the difference is credited here.  Without it,
    # `impact` (~100 across 40 cards) simply drowns out every synergy term.
    ctx = 0.0
    for cid, n in state.copies.items():
        s = scored.get(cid)
        if s is None or not s.econ.context_sensitive:
            continue
        available = 0
        for pred, _ in s.parsed.wants:
            want = state.wants.get(pred.key())
            if want is not None and want.open_ended:
                available = max(available, want.met)
        if available <= 0:
            continue
        adjusted = deck_adjusted_exp(s.card, s.parsed, available, p)
        ctx += n * (impact_from_exp(adjusted, s.pow_.value, p, s.pow_.evidence) - s.impact)
    terms["context_payoff"] = round(ctx, 3)

    # ── predicate channel: are the cards' stated needs met? ────────────────
    #
    # Each want is weighted by how closely the card that asked for it relates to
    # the seed.  Without that anchoring, any two cards that happen to want each
    # other form a closed clique and farm synergy regardless of the deck's theme
    # — which is exactly how a Morphtronic package ended up in a Rekindling deck.
    tau = float(p["deck.tau_want"])
    tau_open = float(p["deck.tau_want_open"])
    scale = float(p["deck.w_want_scale"])
    floor = float(p["deck.affinity_floor"])
    syn = 0.0
    for want in state.wants.values():
        t = tau_open if want.open_ended else tau
        affinity = max(
            (state.seed_affinity.get(cid, 1.0) for cid in want.askers), default=1.0
        )
        syn += want.weight * want.exclusivity * sat(want.met, t) * max(floor, affinity)
    terms["synergy_wants"] = round(lam * scale * syn, 3)

    # ── trigger enablers: can the deck actually turn these cards on? ───────
    unmet = 0.0
    for cap, n in state.requires.items():
        if not state.provides.get(cap):
            unmet += n
    terms["penalty_no_enabler"] = -round(float(p["deck.p_enabler"]) * unmet, 3)

    # ── tag channel: the synergies not written as a card filter ────────────
    tau_tag = float(p["deck.tau_tag"])
    tags = state.tags
    cycles = 0.0
    cycles += float(p["deck.w_gy_cycle"]) * sat(tags["gy_filler"], tau_tag) * sat(
        tags["gy_payoff"], tau_tag
    )
    cycles += float(p["deck.w_discard_cycle"]) * sat(tags["discard_outlet"], tau_tag) * sat(
        tags["discard_payoff"], tau_tag
    )
    # Milling a Graveyard payoff ON PURPOSE, on top of the generic cycle above.
    #
    # Future Fusion does not mill the top of the Deck and hope — it names a
    # Fusion and sends *that Fusion's materials*, so a payoff which is one of
    # those materials is chosen.  Elemental Hero Gaia lists "1 Elemental HERO
    # monster + 1 EARTH monster"; Dandylion is an EARTH monster that pays off
    # for being sent.  Gated on the payoff actually being somebody's Fusion
    # material, so it cannot pay for a Spell with a Graveyard effect.
    if state.fusion_millers and state.millable_payoff:
        cycles += float(p["deck.w_fusion_mill"]) * sat(
            state.fusion_millers, tau_tag
        ) * sat(state.millable_payoff, tau_tag)
    terms["synergy_cycles"] = round(lam * cycles, 3)

    # ── Graveyard denial: an anti-synergy, not a missing synergy ──────────────
    # Dimensional Fissure banishes everything that would be sent to the GY, so it
    # does not merely fail to help a Graveyard deck, it switches the deck off.
    # Nothing was modelling that, so the search could pay the full gy_cycle bonus
    # above while holding the card that voids it.  Charged in proportion to how
    # much Graveyard machinery is actually being cancelled.
    if tags["gy_denial"]:
        voided = sat(tags["gy_payoff"], tau_tag) * sat(tags["gy_filler"], tau_tag)
        terms["penalty_gy_denial"] = -round(
            float(p["deck.p_gy_denial"]) * sat(tags["gy_denial"], 1.5) * voided, 3
        )

    # ── deck-out as a real win condition ─────────────────────────────────────
    # The model otherwise knows exactly one way to win (card advantage into
    # board), which is why the ROM's Needle Worm / Warm Worm mill decks were
    # among the least understood in the corpus.  Mill is worthless in ones and
    # twos and a win condition in bulk, so it is rewarded super-linearly up to a
    # cap rather than per card.
    if tags["deckout"] >= int(p["deck.deckout_min"]):
        terms["synergy_deckout"] = round(
            lam * float(p["deck.w_deckout"]) * sat(tags["deckout"], float(p["deck.tau_deckout"])), 3
        )
    # Burn is the other alternate win condition, and behaves the same way: one
    # Tremendous Fire is a bad Fireball, eight of them are a deck.
    if tags["burn"] >= int(p["deck.burn_min"]):
        terms["synergy_burn"] = round(
            lam * float(p["deck.w_burn"]) * sat(tags["burn"], float(p["deck.tau_deckout"])), 3
        )
    # Flip effects want a way to flip them on demand rather than waiting to be
    # attacked; same shape as the gy_filler <-> gy_payoff pair.
    cyc_flip = float(p["deck.w_flip_cycle"]) * sat(tags["flip_effect"], tau_tag) * sat(
        tags["flip_enabler"], tau_tag
    )
    if cyc_flip:
        terms["synergy_flip"] = round(lam * cyc_flip, 3)

    # ── role balance: engine vs interaction ──────────────────────────────────
    # The model priced MST and Bottomless Trap Hole correctly as economy but had
    # no way to say a deck was ALL engine and would brick, or all answers with
    # nothing to do.  Interaction is anything that removes, negates or floodgates
    # the opponent; the target share is a soft band, penalised on both sides.
    interaction = sum(
        n for cid, n in state.copies.items()
        if (s := scored.get(cid)) is not None and _is_interaction(s)
    )
    if state.main_total >= int(p["deck.size"]):
        share = interaction / max(1, state.main_total)
        lo_i, hi_i = float(p["deck.interaction_min"]), float(p["deck.interaction_max"])
        gap = max(0.0, lo_i - share) + max(0.0, share - hi_i)
        terms["penalty_role_balance"] = -round(
            float(p["deck.p_role_balance"]) * gap * state.main_total, 3
        )

    # One-card Synchro lines: a recruiter that summons its own Synchro partner
    # out of the Deck.  Flamvell Firedog + Flamvell Magician is one card for a
    # Level 8, which is worth far more than either body's stats and is invisible
    # to every other term.
    terms["synergy_combo"] = round(
        lam * float(p["deck.w_one_card_combo"]) * state.combo_score(), 3
    )

    # ── tribute tax refunded where the deck can cheat the body out ────────
    # A Level 8 Zombie in a Call of the Mummy deck did not pay two tributes for
    # it.  The tax is charged per card by power.py, which cannot see the deck, so
    # the refund has to happen here.
    refund = 0.0
    for cid in state.cheatable:
        s = scored.get(cid)
        if s is not None and s.pow_.summon_tax < 0:
            refund += (
                state.copies.get(cid, 0)
                * abs(s.pow_.summon_tax)
                * float(p["power.tax_refund_when_cheatable"])
                * float(p["impact.w_evidence"])
            )
    terms["summon_cheat"] = round(refund, 3)

    # ── opening hand ──────────────────────────────────────────────────────
    # Consistency is the single biggest difference between a pile of good cards
    # and a deck: how often does the opening hand actually do something?  And
    # combo targets stranded in hand are the cost of over-running them.
    consistency, dead_draws = state.opening_score(scored)
    terms["opening_consistency"] = round(
        float(p["deck.w_consistency"]) * consistency, 3
    )
    terms["penalty_dead_draws"] = -round(
        float(p["deck.p_dead_draw"]) * dead_draws, 3
    )
    # …and how reliably it reaches the specific card it is built around, which
    # `opening_consistency` cannot see: that term pools every starter and asks
    # "did I open anything live", so three Hecatrice look identical to three
    # unrelated Fairies that happen to search.  Here they are three extra copies
    # of Valhalla.  See DeckState.access_score.
    terms["search_access"] = round(
        float(p["deck.w_search_access"]) * state.access_score(scored, floor), 3
    )

    arch = float(p["deck.w_archetype"]) * _concentration(
        state.archetypes, float(p["deck.tau_concentration"])
    )
    attr = float(p["deck.w_attribute_concentration"]) * _concentration(
        state.attributes, float(p["deck.tau_concentration"])
    )
    race = float(p["deck.w_race_concentration"]) * _concentration(
        state.races, float(p["deck.tau_concentration"])
    )
    terms["concentration"] = round(lam * (arch + attr + race), 3)

    # ── Synchro reach: a Tuner is only worth what it can actually make ─────
    reach = state.reachable_synchro_levels()
    available = _available_levels(scored)
    terms["tuner_reach"] = round(
        lam * float(p["deck.w_tuner_reach"]) * sat(len(reach & available), 4.0), 3
    )
    # Two Tuners cannot Synchro together, so a Tuner-heavy deck bricks.  This is
    # P(>=1 Tuner AND >=1 non-Tuner in the opening hand) and it is the only term
    # that prices the ratio; without it a Tuner was a pure bonus and the search
    # built 8 Tuners against 10 non-Tuners.
    if state.extra:
        terms["synchro_ready"] = round(
            float(p["deck.w_synchro_ready"]) * state.synchro_ready(), 3
        )

    # ── penalties ─────────────────────────────────────────────────────────
    # Too much search, not enough to find.
    # "Is this card wanted by anything in the deck?" — one bit test against the
    # union of the active want masks, rather than a scan over every want.
    bit_of = state.idx.index_of
    wanted = state.wants_mask
    payoff_value = sum(
        n * scored[cid].impact
        for cid, n in state.copies.items()
        if (b := bit_of.get(cid)) is not None and wanted >> b & 1
    )
    excess = max(0.0, state.searcher_impact - float(p["deck.rho_payoff"]) * payoff_value)
    terms["penalty_payoff"] = -round(float(p["deck.p_payoff"]) * excess * excess, 3)

    # Cards whose own needs the deck never met — the implicit-bundle penalty that
    # catches every "dead without a partner" card without curating a list.
    orphan = 0.0
    for want in state.wants.values():
        t = tau_open if want.open_ended else tau
        orphan += want.weight * want.exclusivity * (1.0 - sat(want.met, t))
    terms["penalty_orphan"] = -round(float(p["deck.p_orphan"]) * orphan, 3)

    # ── unresolvable advantage ────────────────────────────────────────────
    #
    # The orphan term above is proportional to how *specific* a want is.  But the
    # damage a dead card does is proportional to how much advantage it claimed —
    # that is exactly why the search wanted it.  Rain Storm reads as +2.00 of
    # removal and needs a "Cloudian" monster the deck does not have; charging it
    # only the generic orphan rate left it comfortably worth playing.  Here the
    # penalty scales with the card's own economy, so the more a card promises
    # while being unresolvable, the harder it is hit.
    dead = 0.0
    for cid, n in state.copies.items():
        s = scored.get(cid)
        if s is None or s.econ.exp <= 0:
            continue
        unmet_here = [
            w
            for pred, _ in s.parsed.wants
            if (w := state.wants.get(pred.key())) is not None
            and not w.met
            # exclude_flags is only ever set by the Synchro-partner tightening in
            # text.parse, which fires exactly when a card is useless without a
            # specific partner.  Without it here, Debris Dragon's want was too
            # generic to count as dead advantage (no archetype, no card name), so
            # three copies stayed in a deck holding nothing it could Synchro with.
            and (pred.archetype or pred.exact_names or pred.exclude_flags)
        ]
        missing_caps = [c for c in s.parsed.requires if not state.provides.get(c)]
        if unmet_here or missing_caps:
            dead += n * s.econ.exp
    terms["penalty_dead_advantage"] = -round(float(p["deck.p_dead_advantage"]) * dead, 3)

    # An Extra Deck card the deck cannot legally Summon is a blank slot.  Nothing
    # charged for it: Extra Deck cards do not register wants, so their materials
    # were never checked against the deck at all.
    dead_extra = state.unsummonable_extra(scored)
    terms["penalty_unsummonable"] = -round(
        float(p["deck.p_unsummonable"]) * dead_extra, 3
    )

    # A deck that cannot open with a playable body loses to one that can.
    low = sum(n for lvl, n in state.levels.items() if lvl <= 4)
    if state.monsters:
        share = low / state.monsters
        gap = max(0.0, float(p["deck.low_level_target"]) - share)
        terms["penalty_curve"] = -round(float(p["deck.p_curve"]) * gap * state.monsters, 3)

    # Ratio guards, as a soft penalty so the search can pass through a bad state.
    lo, hi = int(p["deck.min_monsters"]), int(p["deck.max_monsters"])
    over = max(0, state.monsters - hi) + max(0, lo - state.monsters if state.main_total >= int(p["deck.size"]) else 0)
    over += max(0, state.traps - int(p["deck.max_traps"]))
    terms["penalty_ratio"] = -round(float(p["deck.p_ratio"]) * over, 3)

    return DeckScore(total=round(sum(terms.values()), 4), terms=terms)


def marginal(
    state: DeckState,
    cand: Scored,
    k: int,
    scored: dict[int, Scored],
    p: Params | None = None,
    *,
    lambda_synergy: float | None = None,
    base: float | None = None,
) -> float:
    """Per-slot gain from adding *k* copies of *cand*.

    Dividing by *k* is what lets a 1-of boss monster compete fairly against a
    3-of engine piece: the comparison is value *per deck slot*, not per card.
    """
    p = p or default()
    if base is None:
        base = score(state, scored, p, lambda_synergy=lambda_synergy).total
    trial = state.clone()
    trial.add(cand, k)
    after = score(trial, scored, p, lambda_synergy=lambda_synergy).total
    return (after - base) / k
