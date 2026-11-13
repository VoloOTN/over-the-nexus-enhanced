"""How strong a card is, independent of card advantage.

Economy says Monster Reborn and Smashing Ground are both 0.00 — correctly, they
are both 1-for-1s.  Power is what separates them: the body Reborn puts on the
field is worth more than the small monster Smashing Ground removes.

Every stat threshold here is **derived from the pool**, not typed.  ``stat_eff``
compares a monster to the median ATK of other monsters at its level, so "good
stats for a Level 4" needs no table — and it automatically reflects this ROM's
2011 card pool rather than a modern one.
"""

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field

from otn_enhanced.deckgen import wikitags
from otn_enhanced.deckgen.matchindex import MatchIndex
from otn_enhanced.deckgen.model import Card, ParsedCard
from otn_enhanced.deckgen.params import Params, default

#: tag -> params key.  Only tags whose value economy *cannot* already see belong
#: here; see the note in params.toml under [power].
_TAG_KEYS = {
    "floodgate": "tag_floodgate",
    "protection": "tag_protection",
    "piercing": "tag_piercing",
    "direct_attack": "tag_direct_attack",
    "double_attack": "tag_double_attack",
    "nomi": "tag_nomi",
    "vanilla": "tag_vanilla",
    # Needs multiple copies of itself drawn together: a multi-card combo for a
    # one-card payoff.  "7" scored +1.92 and appears in zero tournament decks.
    "needs_self_copies": "tag_needs_self_copies",
    # Loading your own GY is setup, not loss — Foolish Burial is a 21% staple.
    "gy_setup": "tag_gy_setup",
    # Combat channel.  Retro formats are decided in the Battle Phase and the
    # model priced only card advantage, so D.D. Warrior Lady (411 corpus
    # appearances) scored the same as any 1-for-1 removal Spell.
    "battle_removal": "tag_battle_removal",
    "battle_immune": "tag_battle_immune",
    "combat_trick": "tag_combat_trick",
    "atk_scaling": "tag_atk_scaling",
    "board_reset": "tag_board_reset",
    "tempo": "tag_tempo",
    # Mechanic tags derived from the parsed clauses.  All start at 0.00 so the
    # fit decides whether they carry signal; see the note in params.toml.
    "spot_removal": "tag_spot_removal",
    "control_theft": "tag_control_theft",
    "hand_disruption": "tag_hand_disruption",
    "token_maker": "tag_token_maker",
    "banish_payoff": "tag_banish_payoff",
    # Read card-by-card off the era's most-played list; these three are the ones
    # economy provably cannot see (it counts cards, not tempo or timing).
    "opponent_turn": "tag_opponent_turn",
    "summon_answer": "tag_summon_answer",
    "free_body": "tag_free_body",
    # From clustering the cards that parsed but had no mechanic tag.
    "battle_payoff": "tag_battle_payoff",
    "stat_debuff": "tag_stat_debuff",
    "recurring": "tag_recurring",
    "lifegain": "tag_lifegain",
    # From the wiki's curated categories: three facts no regex over the text
    # could reach.  See the note in params.toml.
    "damage_block": "tag_damage_block",
    "random_outcome": "tag_random_outcome",
    "self_damage": "tag_self_damage",
    # ── the remaining 21 wiki tags ──────────────────────────────────────────
    #
    # These were assigned to cards and then read by NOTHING: no params key, no
    # entry here, so no fit could price them.  Declared at 0.00 and put in the
    # search space — describe first, let the fit decide, which is how every tag
    # above got its value.
    #
    # Six are expected to stay 0.00 and their grids include it so the fit can
    # refuse: tribute_cost / banish_cost / lp_cost restate economy's cost keys,
    # and generic_material / generic_tuner / generic_nontuner are already read
    # by `w_extra_generic` through `wikitags.material_genericity`.  A nonzero
    # value on any of those six is double counting, not a discovery.
    "stat_boost": "tag_stat_boost",
    "summon_payoff": "tag_summon_payoff",
    "conditional": "tag_conditional",
    "attack_lock": "tag_attack_lock",
    "equip_effect": "tag_equip_effect",
    "leave_payoff": "tag_leave_payoff",
    "attack_trigger": "tag_attack_trigger",
    "attack_redirect": "tag_attack_redirect",
    "information": "tag_information",
    "name_change": "tag_name_change",
    "level_mod": "tag_level_mod",
    "deck_stack": "tag_deck_stack",
    "fusion_payoff": "tag_fusion_payoff",
    "continuous_effect": "tag_continuous_effect",
    "extra_normal_summon": "tag_extra_normal_summon",
    "tribute_cost": "tag_tribute_cost",
    "banish_cost": "tag_banish_cost",
    "lp_cost": "tag_lp_cost",
    "generic_material": "tag_generic_material",
    "generic_tuner": "tag_generic_tuner",
    "generic_nontuner": "tag_generic_nontuner",
}


@dataclass
class PowerResult:
    stat_eff: float
    summon_tax: float
    tag_power: float
    searchability: float
    tuner_value: float
    value: float
    #: Signals that are NOT stat-driven: tournament play rate, the ATK floor for
    #: Normal Summons, and hard drawbacks.  Kept separate from `value` because
    #: the deck-level fit found *stat summing* anti-correlated with deck quality
    #: and crushed w_power to 0.10 — which silently disabled these too, even
    #: though they are the most predictive signals in the model.
    evidence: float = 0.0
    breakdown: list[tuple[str, float]] = field(default_factory=list)


def stat_band(level: int | None) -> str:
    """Which summoning-cost band a monster's body competes in.

    The three bands are the real breakpoints in how a body reaches the field:
    1-4 is Normal Summonable, 5-6 costs one tribute, 7+ costs two.  Within a
    band, what matters is where the card sits against its peers.
    """
    lvl = level or 0
    if lvl >= 7:
        return "7+"
    if lvl >= 5:
        return "5-6"
    return "1-4"


@dataclass
class StatBaseline:
    """Where a monster's body ranks **within its Level band**, as a percentile.

    Replaces a z-score bucketed by ``(exact level, is_extra)``.  That bucketing
    had two failures, both visible on a Gladiator Beast deck:

    * **Exact-level buckets erase the signal on the Extra Deck.**  Gyzarus is a
      Level 6 Fusion with 2400 ATK, which is *typical of Level 6 Extra Deck
      monsters* — so it scored −0.06 and read as an average body.  But a body is
      only big or small relative to what it will actually **face**, not relative
      to other cards that happen to share its Level and its deck zone.
    * **Splitting `is_extra` compared Synchros only against Synchros**, which is
      why no feature in the model could separate a good one from a bad one
      (AUC 0.436 for `power` inside the Extra Deck — anti-correlated).

    A percentile rather than a z-score because ATK distributions inside a band
    are lumpy and long-tailed; rank is robust to that where an IQR-scaled
    z-score, floored at 400, was not.
    """

    #: band -> sorted effective-ATK values, for the percentile lookup.
    dist: dict[str, list[float]]
    clip: float = 2.0

    @staticmethod
    def effective(card: Card) -> float:
        """A high-DEF wall has real value, just less than the same ATK would be."""
        return 0.75 * card.atk + 0.25 * max(card.def_, 0)

    @classmethod
    def build(cls, cards: list[Card], p: Params | None = None) -> "StatBaseline":
        dist: dict[str, list[float]] = {}
        for c in cards:
            if c.card_class != "monster" or c.atk < 0 or c.level is None:
                continue
            dist.setdefault(stat_band(c.level), []).append(cls.effective(c))
        for vals in dist.values():
            vals.sort()
        clip = float((p or default())["power.stat_clip"])
        return cls(dist=dist, clip=clip)

    def z(self, card: Card) -> float:
        """Signed band percentile, scaled to the same +/-clip range as before.

        0.5 (median of the band) maps to 0.0, the top of the band to +clip and
        the bottom to −clip, so ``power.w_stat`` keeps its meaning across the
        change.
        """
        if card.card_class != "monster" or card.level is None or card.atk < 0:
            return 0.0
        vals = self.dist.get(stat_band(card.level))
        if not vals:
            return 0.0
        v = self.effective(card)
        lo = bisect_left(vals, v)
        hi = bisect_right(vals, v)
        # Midpoint of the tied run, so every copy of an identical stat line gets
        # the same percentile rather than depending on sort order.
        pct = (lo + hi) / (2.0 * len(vals))
        return self.clip * 2.0 * (pct - 0.5)


def synchro_levels(cards: list[Card]) -> set[int]:
    """Every Synchro Monster level available in the pool."""
    return {c.level for c in cards if c.is_synchro and c.level}


def synchro_level_value(
    cards: list[Card], play_rate: dict[int, float] | None = None
) -> dict[int, float]:
    """How good the best Synchro at each Level actually is, from tournament play.

    Counting *reachable levels* treats Level 3 the same as Level 8, which is
    badly wrong: measured over the era formats the best card at each Level is
    Catastor 97% (5), Brionac 95% (6), Black Rose 92% (7), **Stardust 94% (8)**,
    Trishula 52% (9) — while Levels 10 and 12 are near zero.  A Tuner is worth
    what it can actually make.
    """
    play_rate = play_rate or {}
    out: dict[int, float] = {}
    for c in cards:
        if not (c.is_synchro and c.level):
            continue
        out[c.level] = max(out.get(c.level, 0.0), play_rate.get(c.cid, 0.0))
    # With no mined data every level scores 0; fall back to "all levels equal"
    # so the model still runs on a clean checkout.
    return out or {lvl: 1.0 for lvl in synchro_levels(cards)}


def _summon_tax(card: Card, p: Params, pc: "ParsedCard | None" = None) -> float:
    """What it costs to get the body onto the field.

    A Special-Summon-only monster never pays a tribute: Dark Armed Dragon and
    Gorz are Level 7 but arrive for free once their condition is met, so taxing
    them as two-tribute beaters is simply wrong.  Their real cost is the
    condition itself, which is already priced by the  tag and by the wants
    parsed out of that condition.
    """
    if card.card_class != "monster":
        return 0.0
    # ...but only for monsters summoned by their own free condition.  A Ritual
    # or Fusion is also "cannot be Normal Summoned", and it is the opposite of
    # free: it needs a specific Spell *and* tributes matching its Level.  Lumping
    # them together let Sorcerer of Dark Magic (Level 9 Ritual) escape the tax
    # entirely and climb straight back into the deck.
    # The discriminator is whether the card states a condition it pays ITSELF.
    # Dark Armed Dragon ("by having exactly 3 DARK monsters in your GY") and
    # Chaos Sorcerer ("by banishing 1 LIGHT and 1 DARK") both parse a
    #  clause and arrive for free once it holds.  Sorcerer of Dark
    # Magic says "can only be Ritual Summoned with Dark Magic Ritual" -- no
    # summon_cost, because the cost lives on a *different card* -- so it keeps
    # the tax.  Card flags cannot tell these apart: this ROM types Sorcerer of
    # Dark Magic as a plain Effect Monster.
    # ...and the zone is what separates free from expensive.  A GY condition
    # (Dark Armed Dragon's "3 DARK monsters in your GY", Chaos Sorcerer's
    # "banishing 1 LIGHT and 1 DARK from your GY") spends resources you already
    # spent.  "by Tributing monsters whose total Levels equal 9" -- which is how
    # a Ritual reads, and which my own summon_cost rule matches -- spends live
    # bodies off the field and is the most expensive summon in the game.
    self_summoning = pc is not None and any(
        c.verb == "summon_cost" and c.zone_from == "gy" for c in pc.clauses
    )
    if pc is not None and "nomi" in pc.tags and self_summoning:
        return 0.0
    # A card with its own free Special Summon route still *can* be hard-cast, so
    # it keeps a reduced tax rather than none.
    relief = float(p["power.self_ss_tax_relief"]) if (
        pc is not None and "self_ss" in pc.tags
    ) else 1.0
    if card.is_extra:
        # Material COUNT, read off the card, not inferred from Level.
        #
        # The old rule was `max(2, round(level/2))`, which billed a Level 8
        # Synchro for FOUR materials and a Level 10 for five.  A Synchro Summon
        # is 1 Tuner + 1-or-more non-Tuners — two cards whether it is Level 5 or
        # Level 10; the material *Levels* sum to the Synchro's Level, the material
        # *count* does not.  Checked against the text: of the Extra Deck cards
        # that state a material line, **252 name two materials and 23 name
        # three. None names four or five.**
        #
        # It mattered because the tax then scaled with Level and the format's
        # best Synchros are high-Level, so `power` came out ANTI-correlated with
        # play rate inside the Extra Deck (AUC 0.436).
        named = next(
            (c for c in (pc.clauses if pc is not None else ()) if c.verb == "material"),
            None,
        )
        # " + " and not "+": the Synchro line reads "1 Tuner + 1+ non-Tuner
        # monsters", where the bare "+" in "1+" is a quantifier, not a separator.
        materials = (named.raw.count(" + ") + 1) if named else 2
        return float(p["power.tax_extra_per_material"]) * (max(2, materials) - 1)
    level = card.level or 0
    # Tribute cost is what actually hurts, and it is not linear in Level: 5-6
    # costs one body, 7+ costs two, and a Level 9-10 vanilla-ish beater costs two
    # bodies *and* is dead in the opening hand.  A single 7+ bracket rated
    # Sorcerer of Dark Magic (Level 9, two tributes, a conditional negate) the
    # same as a Level 7, which is how it kept earning a slot.
    if level >= 9:
        return relief * float(p["power.tax_level_9_plus"])
    if level >= 7:
        return relief * float(p["power.tax_level_7_plus"])
    if level >= 5:
        return relief * float(p["power.tax_level_5_6"])
    return 0.0


def normal_summon_atk(card: Card, pc: ParsedCard, p: Params) -> float:
    """Penalty for a main-deck body that cannot hold the field.

    Nearly every Normal-Summonable monster in a tournament deck either has
    >= ~1600 ATK or earns its slot with an effect.  A 800 ATK vanilla body that
    the model liked for its parsed economy still loses to everything it meets,
    so the shortfall is charged in proportion — and waived for cards whose text
    does enough to justify the slot.
    """
    if card.card_class != "monster" or card.is_extra or card.atk < 0:
        return 0.0
    if "nomi" in pc.tags:
        return 0.0  # never Normal Summoned; judged on its effect alone
    floor = float(p["power.normal_summon_atk_floor"])
    if card.atk >= floor:
        return 0.0
    # An effect worth the slot buys the shortfall off.
    earning = pc.tags & {
        "searcher", "summoner", "draw", "negate", "floodgate", "recursion",
        "gy_filler", "gy_setup", "protection", "tuner",
    }
    relief = min(1.0, float(p["power.atk_floor_effect_relief"]) * len(earning))
    shortfall = (floor - card.atk) / floor
    return -float(p["power.p_atk_floor"]) * shortfall * (1.0 - relief)


def power(
    card: Card,
    pc: ParsedCard,
    baseline: StatBaseline,
    idx: MatchIndex,
    syn_levels: set[int],
    p: Params | None = None,
    play_rate: float = 0.0,
    level_value: dict[int, float] | None = None,
    non_tuner_levels: set[int] | None = None,
) -> PowerResult:
    """Score one card's raw strength."""
    p = p or default()
    breakdown: list[tuple[str, float]] = []

    stat_eff = baseline.z(card)
    tax = _summon_tax(card, p, pc)

    tag_power = 0.0
    for tag in pc.tags:
        # `nomi` prices "needs a specific board before it does anything".  On an
        # EXTRA DECK monster that is not a drawback, it is the summoning rule:
        # "Must first be Special Summoned (from your Extra Deck) by shuffling the
        # above cards you control into the Deck" is how every Gladiator Beast
        # Fusion works, and every Synchro carries the equivalent.  Charging it
        # −0.90 hit precisely the Extra Deck cards with the most demanding — and
        # therefore most powerful — summoning text: Gyzarus and Heraklinos both
        # came out with NEGATIVE power on 2400 and 3000 ATK bodies.  The real
        # cost of putting them out is already in `summon_tax`.
        if tag == "nomi" and card.is_extra:
            continue
        key = _TAG_KEYS.get(tag)
        if key:
            v = float(p[f"power.{key}"])
            tag_power += v
            breakdown.append((f"tag:{tag}", v))
    if "cannot_attack" in {c.verb for c in pc.clauses}:
        v = float(p["power.tag_cannot_attack"])
        tag_power += v
        breakdown.append(("tag:cannot_attack", v))

    # Consistency: a card several others can fetch shows up more often.
    #
    # Not for the Extra Deck: you never search it, you summon out of it by
    # material.  What `searchability` actually measures there is how many cards
    # NAME this Fusion — which is an archetype lock, not consistency, and it runs
    # the wrong way.  Measured over the era corpus it was the single most
    # anti-correlated component of power for Extra Deck cards (AUC **0.402**):
    # a "HERO" Fusion that Miracle Fusion can name scores high and is playable in
    # one deck, while Brionac and Catastor — nameable by nothing, summonable by
    # everything — scored zero.
    searchability = (
        0.0 if card.is_extra else math.log1p(idx.searchability(card.cid))
    )

    # How freely this Extra Deck monster can be Summoned at all — the strongest
    # single signal available for ranking the Extra Deck, which nothing in the
    # model measured before (AUC 0.442, anti-correlated).
    #
    # Read off the wiki's material categories ("Does not require specific Synchro
    # Materials"), which state the fact this used to INFER from "does any parsed
    # want carry an archetype or a card name".  That inference read the whole
    # card: Scrap Dragon (179 era decks) counted as locked because its *effect*
    # names an archetype, though its material line is fully generic, and
    # Blackwing Armor Master counted as free though its non-Tuners must be
    # Blackwings.  Graded 1.0 / 0.5 / 0.0 rather than boolean, so Goyo Guardian
    # sits where it belongs between Catastor and Armor Master.
    #
    # Measured on the era corpus, played vs unplayed Extra Deck cards: the old
    # inferred boolean scores AUC **0.709**, this **0.686**.  The proxy wins that
    # comparison because an archetype-locked Synchro *is* played — inside its own
    # archetype — which is the orphan/want channel's job to price, not this
    # term's.  Keeping the proxy here double-counts the lock.
    extra_generic = 0.0
    if card.is_extra:
        generic = wikitags.material_genericity(card)
        if generic is None:  # card absent from the scrape — fall back
            generic = 0.0 if any(w.archetype or w.exact_names for w, _ in pc.wants) else 1.0
        extra_generic = generic * float(p["power.w_extra_generic"])

    # A Tuner is worth what it unlocks: how many distinct Synchro levels it can
    # reach alongside a plausible non-Tuner partner.
    tuner_value = 0.0
    if card.is_tuner and card.level:
        values = level_value or {lvl: 1.0 for lvl in syn_levels}
        # Partner Levels must come from actual *non-Tuner* monsters: a Tuner
        # cannot be used as non-Tuner material.
        partners = non_tuner_levels or set(range(1, 9))
        reachable = {card.level + n for n in partners} & syn_levels
        # Weighted by what is at each Level, not by how many Levels there are.
        tuner_value = sum(values.get(lvl, 0.0) for lvl in reachable)

    atk_floor = normal_summon_atk(card, pc, p)
    if atk_floor:
        breakdown.append(("normal_summon_atk", atk_floor))

    # Hard drawbacks that no amount of parsed economy should outweigh.
    drawback = 0.0
    if "needs_self_copies" in pc.tags:
        drawback += float(p["power.tag_needs_self_copies"])
        breakdown.append(("needs_self_copies", float(p["power.tag_needs_self_copies"])))

    # Evidence beats theory.  A card played in a large share of tournament decks
    # is good for reasons the text model may not capture (Book of Moon and
    # Foolish Burial both scored -1.47 while being format staples).  Asymmetric
    # on purpose: high play rate is evidence of quality, but *absence* from this
    # corpus is not evidence of badness — most of the 4,076-card pool simply
    # never had a chance to show up in Tengu or Edison.
    staple = float(p["power.w_staple"]) * (play_rate ** float(p["power.staple_exponent"]))
    if staple:
        breakdown.append(("tournament_play_rate", staple))

    value = (
        float(p["power.w_stat"]) * stat_eff
        + float(p["power.w_tags"]) * tag_power
        + float(p["power.w_searchability"]) * searchability
        + extra_generic
        + float(p["power.w_tuner"]) * tuner_value
    )
    # The summon tax is a hard drawback, not a stat: it belongs with the ATK
    # floor and the self-copy penalty in the evidence channel.  Left in
    # power.value it was multiplied by w_power (0.10), so a -4.50 tax on a
    # two-tribute Level 9 landed as -0.45 and changed nothing.
    evidence = atk_floor + staple + drawback + float(p["power.w_tax"]) * tax
    breakdown[:0] = [("stat_eff", stat_eff), ("summon_tax", tax)]
    breakdown.append(("searchability", float(p["power.w_searchability"]) * searchability))
    if extra_generic:
        breakdown.append(("extra_generic_materials", extra_generic))
    if tuner_value:
        breakdown.append(("tuner_value", float(p["power.w_tuner"]) * tuner_value))

    return PowerResult(
        stat_eff=round(stat_eff, 4),
        summon_tax=round(tax, 4),
        tag_power=round(tag_power, 4),
        searchability=round(searchability, 4),
        tuner_value=round(tuner_value, 4),
        value=round(value, 4),
        evidence=round(evidence, 4),
        breakdown=breakdown,
    )
