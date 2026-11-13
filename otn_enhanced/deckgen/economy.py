"""Net card advantage, in cards.

The whole model is one line::

    economy = sum(gains) - sum(costs) - what it cost to resolve the card itself

evaluated three times against three *activation-conditioned* board states (see
:mod:`.params`), which yields a ``(min, exp, max)`` triple instead of a single
number.  Cards with fixed counts collapse to a point; ``Destroy all monsters``
spreads out because the answer genuinely depends on the board.

Two deliberate choices worth knowing about:

* **This function is context-free.**  It never looks at the rest of the deck, so
  it caches cleanly.  Rekindling therefore scores −1.00 here — the deck-dependent
  upside lives in its ``wants`` predicate and is paid out by :mod:`.synergy`.
  ``context_sensitive`` marks cards where that matters.
* **Self-references contribute nothing.**  Rekindling's "banish them during the
  End Phase" is not a −1; it is already priced by ``mod.temporary`` on the summon
  it modifies.  Counting it twice would make every temporary revival look awful.
  The one exception is a card that throws *itself away from the hand* — see
  :func:`_spent_from_hand`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from otn_enhanced.deckgen.model import Card, Clause, ParsedCard
from otn_enhanced.deckgen.params import BoardState, Params, default

#: Open-ended counts bound to the board rather than to a fixed number.
_BOARD_BOUND = frozenset({"all"})
#: Open-ended counts bound to what the deck happens to contain.
_DECK_BOUND = frozenset({"as_many"})

#: Removal verbs: a self-referential one is about this card, not card advantage.
_REMOVAL = frozenset({"destroy", "banish", "bounce", "shuffle", "send", "discard", "tribute"})

#: Clause verb -> which trigger-reliability multiplier applies.
_COND_CLASS = {
    "summon_trigger": "cond_summon",
    "battle_trigger": "cond_battle",
    "leave_trigger": "cond_leave",
    "standby_trigger": "cond_phase",
    "activation_condition": "cond_activation",
    "spell_trap_trigger": "cond_opponent_action",
    # Needs the opponent to activate one *specific* card.  Anti Raigeki and
    # Gryphon Wing are the archetypal cases: strong when they resolve, and they
    # almost never resolve.
    "named_card_trigger": "cond_named_card",
}


@dataclass
class EconomyResult:
    """Net card advantage for one card."""

    min: float
    exp: float
    max: float
    #: Opponent cards removed in the best case, ignoring what we spent.  This is
    #: the colloquial "5-for-1" reading of Dark Hole; ``max`` is the net reading.
    gross_max: float
    #: True when a count depends on deck composition, so ``exp`` understates the
    #: card inside a deck built to support it.
    context_sensitive: bool
    breakdown: list[tuple[str, float]] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.exp:+.2f} cards  (range {self.min:+.2f} .. {self.max:+.2f})"


def _self_spend_key(card: Card) -> str:
    if card.card_class == "monster":
        return "monster"
    sub = card.st_subtype or "Normal"
    if sub == "Equip":
        return "equip"
    if sub == "Continuous":
        return "continuous"
    if sub == "Field":
        return "field"
    if sub == "Quick-Play":
        return "quick_play"
    if sub == "Counter":
        return "counter_trap"
    if sub == "Ritual":
        return "ritual_spell"
    return "normal_trap" if card.card_class == "trap" else "normal_spell"


def _gain_key(c: Clause) -> str | None:
    """Map a gain clause onto a coefficient name, or ``None`` for no economy."""
    v = c.verb
    if v == "draw":
        return "draw"
    if v == "search":
        return "search"
    if v == "control_swap":
        return "control_swap"
    if v == "mill_opponent":
        # Deliberately no economy: sending 5 cards off the opponent's Deck costs
        # them no card in hand or on board.  Its value is the `deckout` tag.
        return None
    if v == "special_summon":
        return {
            "deck": "ss_from_deck",
            "gy": "ss_from_gy",
            "extra": "ss_from_extra",
            "hand": "ss_from_hand",
        }.get(c.zone_from or "", "ss_unspecified")
    # A symmetric wipe still removes the opponent's cards; the matching own-side
    # loss is charged separately in _evaluate.
    if v == "draw_denial":
        return "draw_denial" if c.side == "opponent" else None
    removal = {"destroy": "destroy_opp", "banish": "banish_opp",
               "bounce": "bounce_opp", "shuffle": "shuffle_opp",
               "spin": "spin_opp"}
    if v in removal:
        return removal[v] if c.side in ("opponent", "both", "either") else None
    if v == "discard":
        return "opp_discard" if c.side == "opponent" else None
    if v == "tribute":
        return "opp_tribute" if c.side == "opponent" else None
    if v == "negate":
        return "negate"
    if v == "take_control":
        return "take_control"
    if v == "damage":
        return "damage_per_1000"
    if v == "gain_lp":
        return "gain_lp_per_1000"
    return None


def _cost_key(c: Clause) -> str | None:
    v = c.verb
    if v == "discard":
        return "discard"
    if v == "tribute":
        return "tribute_own"
    if v == "destroy":
        return "destroy_own"
    if v == "bounce":
        return "bounce_own"
    if v == "shuffle":
        return "shuffle_own"
    if v == "banish":
        return "banish_gy" if c.zone_from == "gy" else "banish_own_field"
    if v == "send":
        return {"deck": "send_deck", "hand": "send_hand"}.get(c.zone_from or "", "send_hand")
    if v == "mill":
        return "mill"
    if v == "pay_lp":
        return "lp_per_1000"
    return None


#: Verbs that, applied to our OWN hand, spend a real card.
_OWN_HAND_SPEND = frozenset({"shuffle", "send", "banish", "discard", "bounce"})


def _uncharged_own_cost(c: Clause) -> str | None:
    """Cost key for a *gain*-kind clause that actually spends one of our cards.

    ``_gain_key`` returns ``None`` for removal aimed at our own side — correctly,
    since destroying your own card is not card advantage — but ``_cost_key`` is
    only consulted for ``kind == "cost"``.  A self-directed removal written as an
    *effect* therefore fell through both and was free: 503 cards carry a
    ``gain destroy you`` clause across 1,541 era deck-appearances, and Moray of
    Greed's "Shuffle 2 WATER monsters from your hand into the Deck, then draw 3"
    scored **+2.00** instead of +1.00.

    Deliberately restricted to ``zone_from == "hand"``.  The tempting general fix
    — route every own-side removal to ``_cost_key`` — would charge Call of the
    Haunted and Premature Burial for destroying the monster they just revived,
    which is priced by ``mod.temporary`` and must stay free, and would charge
    every "destroy this card" drawback already inside ``self_spend``.  A card
    leaving the **hand** cannot be either of those.
    """
    if c.side != "you" or c.self_ref or c.zone_from != "hand":
        return None
    if c.verb not in _OWN_HAND_SPEND:
        return None
    return _cost_key(c)


def _negates_and_destroys(pc: ParsedCard) -> bool:
    """Does this card negate something *and* destroy the card it negated?

    A bare negate leaves the card on the field — that is what ``gain.negate``
    (0.70) prices.  "Negate the Summon, AND destroy that card" takes it off the
    board for good, which is a full 1-for-1, and ``gain.negate_destroy`` (1.00)
    existed for it but **was never referenced**: ``_gain_key`` mapped every
    ``negate`` to ``gain.negate`` regardless.  So Solemn Judgment (225 of 348
    era decks) and Stardust Dragon (328) were priced as bare negates.

    The destroy half is identified by ``_gain_key`` returning ``None`` for it —
    it is the negated card, on our own side of the transaction, so it is not
    credited as opponent removal and cannot be double-counted here.
    """
    if not any(c.kind == "gain" and c.verb == "negate" for c in pc.clauses):
        return False
    return any(
        c.kind == "gain" and c.verb == "destroy" and _gain_key(c) is None
        for c in pc.clauses
    )


def _spent_from_hand(card: Card, pc: ParsedCard) -> bool:
    """Does this card's own effect throw it away *from the hand*?

    ``self_spend.monster`` is 0.00 on the reasoning that a monster going hand ->
    field is still your card.  Hecatrice never goes to the field: it discards
    itself out of the hand, and the ``self_ref`` skip below then dropped the only
    clause that would have charged for it — so a plain 1-for-1 ("discard this,
    search Valhalla") read as a **free** +0.95 search, and every card in this
    family (Gravekeeper's Commandant, Warrior of Atlantis, Thunder Dragon, Effect
    Veiler, Honest) was overpriced by a full card.

    Scoped to monsters deliberately.  A Spell or Trap already pays >= 0.35 of
    self_spend, and the ``self_ref`` flag is unreliable on them: Confiscation's
    "then discard it" is the *opponent's* card and Forced Requisition's is not a
    self-discard at all, so widening this would charge two parser artefacts.
    Field costs ("Tribute this card") and Graveyard costs ("banish this card from
    your GY") stay uncharged: the body was already paid for, and the parser reads
    "Tribute Summon" as a self-tribute on 20-odd cards including Dandylion.
    """
    if _self_spend_key(card) != "monster":
        return False
    return any(
        c.kind == "cost"
        and c.self_ref
        and (
            c.verb == "discard"
            or (c.verb in ("send", "banish") and c.zone_from == "hand")
        )
        for c in pc.clauses
    )


def _breadth(c: Clause, p: Params) -> float:
    """How often this clause's target is actually *there* to be hit.

    Raigeki Break answers "1 card on the field", Phoenix Wing Wind Blast "1 card
    your opponent controls", Karma Cut only "1 face-up monster your opponent
    controls" — and the model priced all three as one card removed.  Target
    breadth is the real difference between them, so it is folded into the
    expected count: a narrower filter simply resolves less often.
    """
    pred = c.predicate
    if pred is None:
        return 1.0
    mod = 1.0
    if pred.card_class == "monster":
        mod *= float(p["mod.target_monster_only"])
    if "face_up" in pred.board:
        mod *= float(p["mod.target_face_up_only"])
    return mod


def _board_breadth(c: Clause, p: Params) -> float:
    """How much of the board an ``all``-count clause actually sweeps.

    "Destroy ALL monsters" and "destroy ALL face-up monsters **with 0 ATK** your
    opponent controls" both resolved to the board prior of 2.2 monsters, so
    Reptilianne Hydra — a Synchro that has never been played in the era corpus —
    was billed +2.20 of removal for a clause that hits almost nothing, and it
    ranked above Brionac and Catastor.

    Counted only for board-bound counts, and only for constraints *beyond* the
    card class and board position.  That distinction is what makes this safe:
    the earlier attempt applied breadth to **fixed** counts too, which broke the
    axis's defining convention ("spend one card, remove one card, net 0.00") and
    dropped Smashing Ground to -0.19.  Here the multiplier is estimating how many
    cards the sweep removes, which is exactly what the count means.  Dark Hole,
    Heavy Storm and Mirror Force constrain nothing beyond class/position and are
    unaffected.
    """
    pred = c.predicate
    if pred is None:
        return 1.0
    narrowing = sum(
        1
        for field_ in (
            pred.attribute,
            pred.race,
            pred.archetype or pred.exact_names,
            pred.level or pred.levels,
            pred.atk or pred.def_,
            pred.monster_flags,
        )
        if field_
    )
    if not narrowing:
        return 1.0
    return float(p["economy.all_narrow_factor"]) ** narrowing


def _resolve_count(c: Clause, state: BoardState, p: Params, *, optimistic: bool) -> float:
    """How many cards this clause moves on the given board."""
    kind = c.count.kind
    # NOTE: target breadth deliberately does NOT apply here.  Discounting a
    # narrow target inside the count breaks the convention the whole economy
    # axis is denominated in -- "spend one card, remove one card, net 0.00" --
    # and Smashing Ground immediately fell to -0.19, failing its golden test.
    # Breadth is real, but it is not card advantage, so it belongs in power.
    # See _breadth, which is retained for that move and currently unused.
    if kind in ("fixed", "up_to"):
        return float(c.count.n or 1)
    if kind in _BOARD_BOUND:
        # "Banish ALL cards with the same name from your opponent's Graveyard"
        # is not a board wipe, but the board prior was answering for it — Karma
        # Cut billed ~2.4 cards of removal for it and came out the only
        # card-POSITIVE discard trap in the format.  A Graveyard-scoped "all" is
        # one or two copies, and it is denial rather than board presence.
        raw = c.raw or ""
        # "same name" is the reliable marker: the target-capture stops before
        # "from your opponent's Graveyard", so neither zone_from nor the clause
        # text carries the zone, and the board prior (2.2 monsters) answered for
        # a Graveyard search instead.
        if (
            c.zone_from == "gy"
            or "same name" in raw.lower()
            or "Graveyard" in raw
            or "GY" in raw
        ):
            return float(p["economy.gy_all_count"]) * (1.5 if optimistic else 1.0)
        # A symmetric wipe's *gain* is only the opponent's half.
        side = "opponent" if c.side == "both" else c.side
        return state.count(
            side, c.predicate.card_class if c.predicate else "monster"
        ) * _board_breadth(c, p)
    if kind in _DECK_BOUND:
        # Bound by deck contents, which economy cannot see.  Zero at the floor,
        # capped at the ceiling — synergy pays out the real value.
        return p["economy.mass_cap"] if optimistic else 0.0
    return 1.0


def _condition_mod(pc: ParsedCard, p: Params) -> float:
    """How reliable this card's trigger is."""
    worst = 1.0
    for c in pc.clauses:
        key = _COND_CLASS.get(c.verb)
        if key:
            worst = min(worst, float(p[f"mod.{key}"]))
    return worst


def _lp_scale(key: str, count: float) -> float:
    """Life-point coefficients are quoted per 1000 LP."""
    return count / 1000.0 if key.endswith("_per_1000") else count


def _evaluate(
    card: Card,
    pc: ParsedCard,
    state: BoardState,
    p: Params,
    *,
    optimistic: bool,
    collect: list[tuple[str, float]] | None = None,
) -> tuple[float, float]:
    """Return ``(net, gross_opponent_cards_removed)`` on one board state.

    On a "pick 1 of these effects" card each bullet is scored separately and the
    best one wins, because only one of them ever resolves.
    """
    if pc.exclusive_modes:
        modes = {c.mode for c in pc.clauses if c.mode}
        if modes:
            best: tuple[float, float] | None = None
            best_collect: list[tuple[str, float]] = []
            for mode in sorted(modes):
                sub = ParsedCard(
                    cid=pc.cid,
                    clauses=[c for c in pc.clauses if c.mode in (0, mode)],
                    tags=pc.tags,
                    exclusive_modes=False,
                )
                trace: list[tuple[str, float]] = []
                result = _evaluate(
                    card, sub, state, p, optimistic=optimistic, collect=trace
                )
                if best is None or result[0] > best[0]:
                    best = result
                    best_collect = [(f"mode {mode}: {k}", v) for k, v in trace]
            if collect is not None:
                collect.extend(best_collect)
            return best  # type: ignore[return-value]

    self_spend = float(p[f"self_spend.{_self_spend_key(card)}"])
    # Discarding itself out of the hand costs a whole card, and no other term
    # charges for it.  `max` rather than `+` so nothing is ever double-billed,
    # and it is evaluated per *mode*, so a card whose self-discard sits in one
    # bullet of an "apply 1 of these effects" list only pays it in that branch.
    if _spent_from_hand(card, pc):
        self_spend = max(self_spend, float(p["cost.discard"]))
    negate_destroy = _negates_and_destroys(pc)
    cond = _condition_mod(pc, p)
    recurring = card.card_class != "monster" and card.st_subtype in ("Continuous", "Field")

    net = -self_spend
    gross = 0.0
    if collect is not None:
        collect.append((f"self_spend[{_self_spend_key(card)}]", -self_spend))

    for c in pc.clauses:
        if c.kind not in ("gain", "cost"):
            continue
        # A card removing itself or its own summons is already priced by
        # self_spend / mod.temporary.
        if c.self_ref and c.verb in _REMOVAL:
            continue

        if c.kind == "gain":
            key = _gain_key(c)
            if key is None:
                # Not a gain — but it may still be one of OUR cards leaving.
                own = _uncharged_own_cost(c)
                if own is not None:
                    n = _resolve_count(c, state, p, optimistic=optimistic)
                    value = float(p[f"cost.{own}"]) * n
                    net -= value
                    if collect is not None and value:
                        collect.append((f"cost.{own}[own] x{n:g}", -value))
                continue
            if key == "negate" and negate_destroy:
                key = "negate_destroy"
            coeff = float(p[f"gain.{key}"])
            n = _lp_scale(key, _resolve_count(c, state, p, optimistic=optimistic))
            value = coeff * n * cond
            if c.temporary:
                value *= float(p["mod.temporary"])
            if c.optional:
                value *= float(p["mod.optional"])
            if recurring and c.frequency in ("once_per_turn", "hard_opt"):
                value *= float(p["mod.recurrence"])
            net += value
            # gross_max counts opponent cards removed, literally, so that Dark
            # Hole reads as the colloquial "5-for-1" alongside its net +4.
            if key in ("destroy_opp", "banish_opp", "bounce_opp", "shuffle_opp",
                       "opp_discard", "opp_tribute"):
                gross += _resolve_count(c, state, p, optimistic=optimistic)
            if collect is not None and value:
                collect.append((f"gain.{key} x{n:g}", value))
        else:
            key = _cost_key(c)
            if key is None:
                continue
            coeff = float(p[f"cost.{key}"])
            n = _lp_scale(key, _resolve_count(c, state, p, optimistic=optimistic))
            value = coeff * n
            net -= value
            if collect is not None and value:
                collect.append((f"cost.{key} x{n:g}", -value))

    # A symmetric board wipe hits our own monsters too; the board states encode
    # that we only activate when that trade is favourable.
    for c in pc.clauses:
        if c.kind == "gain" and c.side == "both" and c.count.kind in _BOARD_BOUND:
            own = state.count("you", c.predicate.card_class if c.predicate else "monster")
            key = _gain_key(Clause(kind="gain", verb=c.verb, side="opponent"))
            coeff = float(p[f"gain.{key}"]) if key else 1.0
            net -= coeff * own
            if collect is not None and own:
                collect.append((f"symmetric.own_loss x{own:g}", -coeff * own))
    return net, gross


def economy(card: Card, pc: ParsedCard, p: Params | None = None) -> EconomyResult:
    """Compute the ``(min, exp, max)`` card-advantage triple for one card."""
    p = p or default()
    boards = p.boards
    breakdown: list[tuple[str, float]] = []

    lo, _ = _evaluate(card, pc, boards["pessimistic"], p, optimistic=False)
    mid, _ = _evaluate(
        card, pc, boards["expected"], p, optimistic=False, collect=breakdown
    )
    hi, gross = _evaluate(card, pc, boards["optimistic"], p, optimistic=True)

    context_sensitive = any(
        c.count.kind in _DECK_BOUND for c in pc.clauses if c.kind in ("gain", "cost")
    )
    return EconomyResult(
        min=round(lo, 4),
        exp=round(mid, 4),
        max=round(hi, 4),
        gross_max=round(gross, 4),
        context_sensitive=context_sensitive,
        breakdown=breakdown,
    )


def deck_adjusted_exp(
    card: Card, pc: ParsedCard, matching_copies: int, p: Params | None = None
) -> float:
    """``exp`` corrected for how many of a card's open-ended targets are in-deck.

    Rekindling with 9 live 200-DEF FIRE monsters revives about three of them, so
    its −1.00 context-free score becomes roughly +0.80.
    """
    p = p or default()
    base = economy(card, pc, p)
    if not base.context_sensitive or matching_copies <= 0:
        return base.exp
    n = min(float(p["economy.mass_cap"]), float(p["economy.live_fraction"]) * matching_copies)
    bonus = 0.0
    for c in pc.clauses:
        if c.kind != "gain" or c.count.kind not in _DECK_BOUND:
            continue
        key = _gain_key(c)
        if key is None:
            continue
        value = float(p[f"gain.{key}"]) * n
        if c.temporary:
            value *= float(p["mod.temporary"])
        bonus += value
    return round(base.exp + bonus, 4)
