"""Parse the whole pool, derive tags and wants, and report coverage.

``wants`` is the load-bearing output: the predicates a card needs *other cards
in the deck* to satisfy.  Only clauses that pull from a private zone create a
want — searching your Deck for a FIRE monster means the deck must contain FIRE
monsters, whereas destroying a monster your opponent controls says nothing
about your own deck.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

from otn_enhanced.deckgen import wikitags
from otn_enhanced.deckgen.model import Card, Clause, ParsedCard, Predicate
from otn_enhanced.deckgen.text import clauses as clause_mod
from otn_enhanced.deckgen.text.grammar import parse_predicate
from otn_enhanced.deckgen.text.segment import is_exclusive, segment

#: Verbs that make the deck's own contents matter.
WANT_VERBS = frozenset({"search", "special_summon", "send", "mill", "equip", "normal_summon"})
#: Zones that are yours to stock.
WANT_ZONES = frozenset({"deck", "gy", "extra", "hand"})
#: Verbs that *spend* a specific card of yours — paying them requires owning it.
COST_WANT_VERBS = frozenset({"banish", "tribute", "discard", "send", "summon_cost"})

#: Levels a Synchro Monster can be in this pool.  Filled on first use.
_SYNCHRO_LEVELS_BY_RACE: dict[str, frozenset[int]] = {}


def _synchro_levels(race: str | None, archetype: str | None) -> frozenset[int]:
    """Levels at which a Synchro matching this material restriction exists."""
    from otn_enhanced.deckgen import cardpool

    key = f"{race}|{archetype}"
    hit = _SYNCHRO_LEVELS_BY_RACE.get(key)
    if hit is None:
        out = set()
        for c in cardpool.load_pool():
            if not (c.is_synchro and c.playable and c.level):
                continue
            if race and (c.race or "") != race:
                continue
            if archetype and archetype not in (c.archetype or "") and archetype not in c.name:
                continue
            out.add(c.level)
        hit = frozenset(out)
        _SYNCHRO_LEVELS_BY_RACE[key] = hit
    return hit


def _tighten_synchro_revival(card, clauses, wants):
    """Narrow a Tuner's "revive a monster" want to monsters it can Synchro with.

    Debris Dragon reads "target 1 monster with 500 or less ATK in your GY;
    Special Summon that target" — which the parser turned into a want satisfied
    by any of 459 cards.  But the *point* of reviving it is to Synchro with it,
    and Debris Dragon can only make a Dragon, cannot use a Level 4 partner, and
    cannot pair with another Tuner.  That leaves Levels 2, 3, 5 and 6 — i.e. in
    practice Card Trooper, Lonefire Blossom, Dandylion.  Scored loosely, the want
    read "satisfied" off a lone Herald of Orange Light that could never be used.

    Applies to any restricted Tuner that Special Summons a monster from the GY,
    so it generalises past Debris Dragon rather than special-casing it.
    """
    from otn_enhanced.deckgen import material

    if not (card.is_monster and card.is_tuner and card.level):
        return wants
    rule = material.rule_for(card)
    if rule.never or rule.unknown:
        return wants
    if not any(
        c.verb == "special_summon" and c.zone_from == "gy" for c in clauses
    ) and not any(c.verb == "target" and c.zone_from == "gy" for c in clauses):
        return wants

    reachable = _synchro_levels(rule.target_race, rule.target_archetype)
    if not reachable:
        return wants
    legal = frozenset(
        lv
        for lv in range(1, 13)
        if lv not in rule.partner_level_ban and (card.level + lv) in reachable
    )
    if not legal or len(legal) >= 11:
        return wants

    out = []
    for pred, weight in wants:
        if pred.card_class == "monster" and pred.levels is None and pred.level is None:
            pred = replace(
                pred,
                levels=legal,
                exclude_flags=frozenset({"tuner"}),  # monster_flags are lowercase
                raw=f"{pred.raw} (Synchro partner for {card.name})",
            )
        out.append((pred, weight))
    return out

#: Self-revival from the Graveyard, worded **zone first**: "If this card is in
#: your GY: You can banish 1 'Frog' monster; Special Summon this card."
#:
#: The `recursion` and `self_ss` patterns below only matched the other order
#: ("Special Summon … from your GY"), so 11 cards of this shape were tagged
#: inconsistently or not at all — Plaguespreader Zombie (66 era decks) and
#: Glow-Up Bulb (54) got only `tuner`, and **Ronintoadin got nothing**, scoring
#: impact −0.79 for what is a free recurring body.
_GY_SELF_REVIVE_SRC = (
    r"(?:while|if) this card is in your (?:GY|Graveyard)[^.]{0,90}?"
    r"Special Summon this card"
)

#: Acts on the OPPONENT'S turn.  Read card-by-card off the era's most-played
#: list: 8 of the top 25 are this (Mirror Force, Torrential Tribute, Dimensional
#: Prison, Bottomless Trap Hole, both Solemns, Effect Veiler, Book of Moon).
#: Economy prices every one as a flat 1-for-1 and cannot see the thing that makes
#: them format-defining -- they interact while the opponent commits resources,
#: costing you no turn of your own.
_OPPONENT_TURN = re.compile(
    r"During (?:either player's|your opponent's) turn|\(Quick Effect\)"
    r"|opponent's monster declares an attack"
    r"|your opponent (?:Normal |Flip |Special )*Summons"
    r"|would be Summoned"
    r"|your opponent would Special Summon"
    r"|a Spell/Trap Card is activated"
    r"|monster\(s\) is Summoned",
    re.I,
)

#: Answers a threat AS IT ARRIVES, so its on-summon effect never resolves --
#: strictly better than removing the same body a turn later, and invisible to an
#: axis that only counts cards.  Solemn Judgment, Solemn Warning, Bottomless
#: Trap Hole, Torrential Tribute, Thunder King Rai-Oh.
_SUMMON_ANSWER = re.compile(
    r"would be Summoned"
    r"|your opponent (?:Normal |Flip |Special )*Summons"
    r"|your opponent would Special Summon"
    r"|negate the Summon"
    r"|monster\(s\) is Summoned",
    re.I,
)

#: Arrives WITHOUT using the Normal Summon -- the one hard per-turn resource the
#: model does not represent at all.  Gorz, Gale, Sirocco, Dark Armed Dragon,
#: Black Luster Soldier, Chaos Sorcerer, Cyber Dragon.
_FREE_BODY = re.compile(
    r"Special Summon this card"
    r"|can be Special Summoned"
    r"|without Tributing",
    re.I,
)

#: Bodies from nowhere — Tokens cost no card and are Tribute / Synchro fodder.
_TOKEN_MAKER = re.compile(r"\bSpecial Summon \d+ .{0,40}?Token", re.I)

#: Uses the banished zone as a resource, rather than banishing as a cost.
_BANISH_PAYOFF = re.compile(
    r"\bbanished monsters?\b|\breturn (?:them|it|that target) to the (?:GY|Graveyard)\b"
    r"|\bfrom (?:among )?your banished\b|\bthat is banished\b",
    re.I,
)

#: Last-resort verb -> mechanic name, in priority order: the first match wins, so
#: the most descriptive verb on the card is the one that names it.
_FALLBACK_TAGS = (
    ("destroy", "destruction"), ("banish", "banish_cost"),
    ("equip", "equip_effect"), ("tribute", "tribute_cost"),
    ("damage", "burn"), ("change_position", "tempo"),
    ("attack_restriction", "attack_lock"), ("set", "set_card"),
    ("pay_lp", "lp_cost"), ("continuous_condition", "continuous_effect"),
    ("flip", "flip_enabler"), ("target", "targeting"),
    ("once_per_turn", "limited_use"), ("frequency_limit", "limited_use"),
    ("material", "extra_vanilla"),
    # tail of the tail: one-verb cards the map above did not reach
    ("stat_gain", "stat_boost"), ("normal_summon", "summoner"),
    ("special_summon", "summoner"), ("treated_as", "name_change"),
    ("summon_trigger", "summon_payoff"), ("leave_trigger", "leave_payoff"),
    ("requires_control", "conditional"), ("activation_condition", "conditional"),
    ("nomi", "conditional"), ("mill", "gy_filler"), ("send", "gy_filler"),
    ("discard", "discard_outlet"), ("draw", "draw"), ("search", "searcher"),
    ("negate", "negate"), ("reveal", "information"),
    ("level_mod", "level_mod"), ("control_swap", "control_theft"),
    ("spin", "spot_removal"), ("bounce", "spot_removal"),
    ("shuffle", "spot_removal"), ("gain_lp", "lifegain"),
)

_TAG_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("floodgate", re.compile(
        r"\b(?:neither player can|your opponent cannot|cannot be (?:Special )?Summoned|"
        r"cannot activate|cannot attack|cannot target|monsters cannot)\b", re.I)),
    ("protection", re.compile(
        r"\bcannot be (?:destroyed|targeted)\b|\bis not destroyed\b|\bunaffected by\b", re.I)),
    ("piercing", re.compile(r"\binflicts? piercing\b|\bpiercing battle damage\b", re.I)),
    ("direct_attack", re.compile(r"\bcan attack (?:your opponent|directly)\b", re.I)),
    ("double_attack", re.compile(r"\bcan attack twice\b", re.I)),
    ("nomi", re.compile(
        r"\bcannot be Normal Summoned\b|\bMust (?:first )?be Special Summoned\b", re.I)),
    ("recursion", re.compile(
        r"\bSpecial Summon .{0,40}from your (?:GY|Graveyard)\b|\badd .{0,40}from your "
        r"(?:GY|Graveyard) to your hand\b|" + _GY_SELF_REVIVE_SRC, re.I)),
    # A body that puts ITSELF back from the Graveyard is a recurring resource,
    # and being discarded or milled is upside rather than a cost — it wants to be
    # down there.  That is `gy_payoff`, which pairs with the deck's gy_filler in
    # synergy_cycles, plus `self_ss` for the tax relief.
    ("gy_payoff", re.compile(_GY_SELF_REVIVE_SRC, re.I)),
    ("self_ss", re.compile(_GY_SELF_REVIVE_SRC, re.I)),
    ("stat_boost", re.compile(r"\bgains? [\d,]+ ATK\b", re.I)),
    # Graveyard denial.  "Any card sent to the Graveyard is banished instead"
    # does not just fail to help a GY deck — it TURNS OFF the gy_filler/gy_payoff
    # engine the deck is built on.  Untagged, the model happily put Dimensional
    # Fissure in a Graveyard deck and still paid the full GY cycle bonus.
    ("gy_denial", re.compile(
        r"\bany (?:card|monster)s? sent to the (?:GY|Graveyard) (?:is|are) banished instead\b|"
        r"\b(?:cards|monsters) (?:are|is) banished instead of being sent to the "
        r"(?:GY|Graveyard)\b", re.I)),
    # Milling the OPPONENT's Deck is not card advantage, it is progress toward an
    # alternate win condition, so it is a tag rather than an economy term.
    ("deckout", re.compile(
        r"\bsend the top [\w-]+ cards? of your opponent's Deck to the (?:GY|Graveyard)\b|"
        r"\byour opponent sends the top [\w-]+ cards?\b", re.I)),
    # Must be damage to the OPPONENT.  A bare "takes N damage" also matches "you
    # take 800 damage", which is a cost, and tagged 187 cards as burn -- enough
    # to hand a Fairy deck a +4.97 burn bonus it had no business earning.
    ("burn", re.compile(
        r"\binflicts? [\d,]+ damage to your opponent\b|"
        r"\byour opponent takes [\d,]+ damage\b", re.I)),
    # A Fusion Monster's materials are its first line; a deck holding one without
    # a way to Fusion Summon is holding a blank.
    ("fusion_payoff", re.compile(r"\bFusion Summon\b", re.I)),
    # Self-Special-Summoning bodies.  `power._summon_tax` keys its relief off
    # this tag, so an untagged Cyber Dragon (694 corpus appearances) was paying
    # the full Level 5 tribute tax for a monster that Summons itself for free.
    ("self_ss", re.compile(
        r"\byou can Special Summon this card\b|"
        r"\bSpecial Summon this card \((?:from your hand|by)\b|"
        r"\bcan be Special Summoned from your hand\b|"
        r"\bSpecial Summon this card from your hand\b", re.I)),
    # Cards that act from hand on the opponent's turn.  The model has no turn
    # structure, so this is the one piece of it that can be read off the text.
    ("hand_trap", re.compile(
        r"\bDuring either player's turn[^.]{0,60}(?:discard|from your hand)\b|"
        r"\b(?:discard|send) this card (?:from your hand )?to the (?:GY|Graveyard)[^.]{0,40}"
        r"(?:negate|destroy)\b", re.I)),
    ("flip_effect", re.compile(r"\bFLIP\s*:", re.I)),
    # Summonable ONLY by one named card, or only after being properly Summoned
    # its own way first.  Either way a generic "Special Summon a Fusion Monster"
    # — Instant Fusion — cannot put it on the field.
    #
    # The line is drawn from in-game behaviour, and it is NOT where the text
    # suggests.  Two wordings look equally restrictive and are not:
    #
    #   "Must be Fusion Summoned and cannot be Special Summoned by other ways"
    #       -> Elemental HERO Mariner, Steam Healer.  Instant Fusion CAN summon
    #          these.  Deliberately excluded.
    #   "cannot be Special Summoned except with 'NEX'"
    #       -> Neo-Spacian Marine Dolphin, Twinkle Moss.  It cannot.
    #   "Must first be Special Summoned … by shuffling the above cards"
    #       -> the Neos contact Fusions.  Must be contact-Summoned once first.
    #
    # Corrected after an initial version keyed on "Must be Fusion Summoned",
    # which wrongly locked Mariner.  Play behaviour is the authority here — see
    # also the modern-errata note on Instant Fusion in CLAUDE.md; ygoprodeck
    # gives it "(This is treated as a Fusion Summon.)", which this 2011 engine
    # does not have.
    ("summon_locked", re.compile(
        r"Must first be Special Summoned|cannot be Special Summoned except",
        re.I)),
    ("flip_enabler", re.compile(
        r"\bchange (?:that|1) .{0,30}to face-down Defense Position\b|"
        r"\bflip (?:1|that|it) .{0,20}face-down\b", re.I)),
    # Tempo: neutralising a monster WITHOUT removing a card.  Turning a threat
    # face-down or flipping it to Defense is not card advantage and is not a
    # printed stat, so both scoring axes read Book of Moon (28% of era decks) and
    # Enemy Controller (15%) as a flat self-spend of -1.00.  This is the one
    # channel that can see them; it deliberately excludes "change YOUR monster",
    # which is a setup effect rather than interaction.
    ("tempo", re.compile(
        r"\bchange (?:that target'?s?|that|1|its) .{0,40}?battle position\b|"
        r"\bchange (?:that|1) .{0,40}?to face-down Defense Position\b|"
        r"\bchange (?:that|1) .{0,40}?to (?:face-up )?Defense Position\b|"
        r"\bflip (?:1|that|it) .{0,20}face-down\b", re.I)),
    # Level modulation feeds Synchro reach, which now enforces material rules and
    # is therefore more sensitive to it than before.
    ("level_mod", re.compile(
        r"\bincrease the Level of\b|\breduce the Level of\b|"
        r"\bLevel becomes\b|\bbecomes? Level \d+\b|\bits Level is increased\b", re.I)),
    ("ritual_payoff", re.compile(r"\bRitual Summon(?:ed)?\b", re.I)),
    ### Combat channel.
    ###
    ### Retro formats are decided in the Battle Phase, and the model had no
    ### representation of it at all -- D.D. Warrior Lady (411 corpus
    ### appearances) scored identically to Smashing Ground.  These tags are the
    ### readable part of that axis; they are priced in [power], not [economy],
    ### because combat is not card advantage.
    ("battle_removal", re.compile(
        r"\b(?:when|if) this card battles\b[^.]{0,80}\b(?:banish|destroy)\b|"
        r"\bafter damage calculation[^.]{0,90}\b(?:banish|destroy)\b|"
        r"\bwhen an opponent's monster declares an attack\b[^.]{0,70}\bdestroy\b", re.I)),
    ("battle_immune", re.compile(
        r"\bis not destroyed by battle\b|\bcannot be destroyed by battle\b|"
        r"\bthe first time this card would be destroyed by battle\b", re.I)),
    # Honest and friends: a body in hand that wins a combat outright.
    ("combat_trick", re.compile(
        r"\bDuring (?:the |your opponent's |either player's )?(?:Battle Phase|Damage Step)\b|"
        r"\bat the start of the Damage Step\b", re.I)),
    # "Increase the ATK of this card by 500 for each ..." — a scaling body the
    # stat model reads as a vanilla with its printed ATK.
    ("atk_scaling", re.compile(
        r"\b(?:increase the ATK of this card by|this card gains) [\d,]+ (?:ATK )?"
        r"(?:points )?for each\b", re.I)),
    # Fiber Jar / Cyber Jar / Morphing Jar: symmetric full resets.  Not card
    # advantage in any direction the economy model can express, but decisive.
    ("board_reset", re.compile(
        r"\beach player shuffles all cards from their hand, field,? and "
        r"(?:GY|Graveyard)\b|\bdestroy all monsters on the field, then both players\b", re.I)),
)

#: Cards that only work with several copies of THEMSELVES on the field or in
#: hand.  "7" needs three face-up "7" cards to do anything; drawing into that is
#: a three-card combo for a one-card payoff, and it scored +1.92 while appearing
#: in zero tournament decks.
_SELF_COPIES = re.compile(
    r'there are (\d+) face-up "[^"]+" cards'
    r'|if you have (?:exactly )?(\d+) "[^"]+"'
    r'|control (\d+) or more "[^"]+" cards',
    re.I,
)

_MASS = re.compile(r"\bdestroy all\b|\bbanish all\b|\breturn all\b", re.I)

### Trigger enablers.
###
### Some cards only do anything if the deck can perform a specific action first.
### Divine Wind of Mist Valley reads "if a WIND monster you control returns to
### the hand: Special Summon 1 Level 4 or lower WIND monster from your Deck" —
### the payoff parses fine, but nothing was checking that the deck can *bounce
### its own monsters*, so it read as a free Special Summon and got played in a
### deck with no way to trigger it at all.
###
### Each entry maps a trigger phrase to a capability the deck must supply; the
### matching `_PROVIDES` rules say which cards supply it.  Unmet pairs are
### charged in deckscore.
_REQUIRES: tuple[tuple[str, re.Pattern], ...] = (
    ("bounce_self", re.compile(
        r"\b(?:is |are )?returns? to (?:the|your|its owner's) hand\b|"
        r"\bis returned to (?:the|your) hand\b", re.I)),
    ("discard_self", re.compile(
        r"\bthis card is discarded\b|\bwhen .{0,30}is discarded\b", re.I)),
    ("tribute_self", re.compile(r"\bis Tributed\b|\bwhen .{0,30}is Tributed\b", re.I)),
    ("send_gy", re.compile(
        r"\bis sent (?:from the Deck )?to the (?:GY|Graveyard)\b", re.I)),
    ("banish_self", re.compile(r"\bis banished\b", re.I)),
    ("counter", re.compile(r"\bA-Counter\b|\bwith a .{0,20}Counter\b", re.I)),
)

_PROVIDES: tuple[tuple[str, re.Pattern], ...] = (
    ("bounce_self", re.compile(
        r"\breturn (?:1|2|\d+|it|them|that|this) .{0,50}to (?:the|your|its owner's) hand\b",
        re.I)),
    ("counter", re.compile(r"\bplace .{0,20}Counter\b", re.I)),
    # Anything that performs the Fusion Summon itself: Polymerization, Miracle
    # Fusion, Overload Fusion, Instant Fusion, Fusion Gate.  Matched on the verb
    # phrase rather than a card list so new donors are picked up automatically.
    ("fusion_summon", re.compile(
        r"\bFusion Summon \d+ .{0,60}Fusion Monster\b|"
        r"\bSpecial Summon \d+ .{0,40}Fusion Monster from your Extra Deck\b", re.I)),
    # A Ritual Spell is the only thing that can put a Ritual Monster on the
    # board, exactly as a Fusion spell is for a Fusion Monster.
    ("ritual_summon", re.compile(
        r"\bThis card (?:can be|is) used to Ritual Summon\b|"
        r"\bRitual Summon \d+\b|"
        r"\bused for (?:the|a) Ritual Summon\b", re.I)),
)


#: A Fusion Monster's material line: the text before the first sentence break,
#: with the materials joined by " + ".  136 of the pool's 147 Fusion Monsters
#: are written this way ('"Cyber Dragon" + "Cyber Dragon" + "Cyber Dragon"',
#: '"Elemental HERO" monster + 1 WATER monster').
_FUSION_SPLIT = re.compile(r"\s\+\s")

#: Monsters that stand in for a named Fusion Material: King of the Swamp,
#: Versago the Destroyer, Beastking of the Swamps, Goddess with the Third Eye,
#: Mystical Sheep #1 (hyphenated "Fusion-Material"), and the three Hex-Sealed
#: Fusions.  Note the deliberate exclusion of "Synchro Material" — Quickdraw
#: Synchron substitutes on the Synchro side, which is a different mechanic.
_FUSION_SUB = re.compile(
    r"\bsubstitute (?:this card )?for any 1 Fusion[- ]Material\b|"
    r"\bcan be used as a substitute for any 1 Fusion[- ]Material\b",
    re.I,
)
#: ``name_key`` -> Attribute the substitute forces the other materials to have
#: (``None`` for the unrestricted ones).
_SUB_NAMES: dict[str, str | None] | None = None
#: ``name_key`` -> Attribute, for resolving a named material to its Attribute.
_ATTR_BY_NAME: dict[str, str | None] | None = None


def _substitutes() -> dict[str, str | None]:
    """Fusion Material substitutes, mapped to their partner-Attribute demand."""
    global _SUB_NAMES, _ATTR_BY_NAME
    if _SUB_NAMES is None:
        from otn_enhanced.deckgen import cardpool
        from otn_enhanced.deckgen import material

        pool = cardpool.load_pool()
        _ATTR_BY_NAME = {c.name_key: c.attribute for c in pool}
        _SUB_NAMES = {
            c.name_key: material.fusion_partner_attribute(c)
            for c in pool
            if c.is_monster and not c.is_extra and c.desc and _FUSION_SUB.search(c.desc)
        }
    return _SUB_NAMES


def _substitute_names_for(other_attrs: set[str]) -> frozenset[str]:
    """Substitutes usable alongside materials of *other_attrs*.

    The Light - Hex-Sealed Fusion may only stand in when every other material is
    LIGHT, so it is not a free extra body in a Cyber Dragon deck.  Substitutes
    whose demand cannot be checked (no Attribute resolvable for the other
    materials) are admitted: over-restricting deletes legal lines, which is the
    worse error -- the same call made for Synchro material rules.
    """
    out = set()
    for name, needs in _substitutes().items():
        if needs is None or not other_attrs or other_attrs <= {needs}:
            out.add(name)
    return frozenset(out)


#: "You can Ritual Summon this card with <X>." / "...Ritual Summon this card."
_RITUAL_SELF = re.compile(
    r"\bRitual Summon(?:ed)? (?:this card|with)\b|\bmust (?:first )?be Ritual Summoned\b",
    re.I,
)
#: The Ritual Spell that names its monster: 'This card is used to Ritual Summon
#: "Black Luster Soldier".'
_RITUAL_NAMES = re.compile(r'Ritual Summon\s+"([^"]+)"', re.I)


def _is_ritual_monster(card: Card) -> bool:
    return bool(
        card.is_monster
        and not card.is_extra
        and card.desc
        and _RITUAL_SELF.search(card.desc)
    )


def _ritual_partners(card: Card, known_names) -> list[tuple[Predicate, float]]:
    """Wants binding a Ritual Spell to its monster and vice versa.

    Ritual Summoning is the last summoning method the model could not see.  The
    binding is written on the card as a quoted name in both directions -- the
    Spell names the monster it Summons -- so it needs no curated list.
    """
    if not card.desc:
        return []
    out: list[tuple[Predicate, float]] = []
    for name in set(_RITUAL_NAMES.findall(card.desc)):
        pred, _c, _r = parse_predicate(f'"{name}"', known_names=known_names)
        if pred is not None and not pred.is_empty():
            out.append((pred, 1.0))
    return out


#: "…cannot be Special Summoned except with 'X'".  Only a QUOTED name is taken:
#: the same sentence shape far more often describes a *method* ("except by
#: Tributing…", "except by sending…"), and 22 of the 34 matches in this pool are
#: that.  A quoted name is unambiguous and is the same convention the Ritual
#: binding already uses.
#: Suffix marking a want that names the ONE card allowed to Summon this monster,
#: as opposed to a material want.  Borrowing the opponent's monsters can supply
#: materials; it cannot supply a Spell you do not run.
SOLE_SUMMONER_MARK = " (its only Summoner)"

_NAMED_SUMMONER = re.compile(
    r"cannot be Special Summoned except (?:with|by)\s+\"([^\"]{2,60})\"", re.I
)


def _named_summoner(card: Card) -> list[tuple[Predicate, float]]:
    """The single card that is allowed to Summon this one, as a want."""
    m = _NAMED_SUMMONER.search(card.desc or "")
    if not m:
        return []
    from otn_enhanced.deckgen.namematch import normalize

    return [(
        Predicate(exact_names=frozenset({normalize(m.group(1))}),
                  raw=f'"{m.group(1)}"{SOLE_SUMMONER_MARK}'),
        1.0,
    )]


#: Weight for a Type / Attribute support want.  The same 0.5 a non-search clause
#: want carries: "this card is built to go with Plants" is a real deckbuilding
#: constraint, but weaker than "this card cannot resolve without a Plant".  The
#: orphan penalty then scales it by exclusivity, so supporting a 72-card Type
#: costs more than supporting a 352-card one, which is the right shape.
#: Marks a want that came from the wiki's "Supports:" categories rather
#: than from the card's own text.  Consumers that reason about MATERIALS
#: must skip these -- a Fusion's "supports LIGHT" is not one of its
#: materials.  Same idea as SOLE_SUMMONER_MARK.
SUPPORT_WANT_PREFIX = "supports "

_SUPPORT_WEIGHT = 0.5


def _support_wants(card: Card) -> list[tuple[Predicate, float]]:
    """Wants from the wiki's ``Supports: <Type>`` / ``<Attribute>`` categories.

    The gap this closes was named in the previous session and could not be built
    from text: nothing stopped the generator putting The Sanctuary in the Sky
    (Fairy support) in a Dragon deck or Super Rejuvenation (Dragon) in a Fairy
    deck.  550 cards support a Type and 252 an Attribute; only 122 of those Type
    supports were already visible as a text want, so this is 481 cards the model
    could not see a constraint on at all.

    **One want per axis, not one per value.**  Forest supports Insect, Beast,
    Beast-Warrior and Plant; four separate wants would leave a Plant deck
    orphaning three of them and paying for a card that is doing its job.  A
    ``race`` set is a disjunction in :meth:`Predicate.matches`, so the four
    become one "any of these" want, exactly as ``split_conjunctions`` keeps a
    genuine "LIGHT or DARK" together.
    """
    types, attrs = wikitags.supported_kinds(card.cid)
    out: list[tuple[Predicate, float]] = []
    # Main deck only: a support card is live because you can DRAW the thing it
    # supports.  Allure of Darkness' DARK want was being answered by Extra Deck
    # DARKs, which can never be in hand to banish.
    if types:
        out.append((
            Predicate(card_class="monster", race=types, main_deck_only=True,
                      raw=f"{SUPPORT_WANT_PREFIX}{'/'.join(sorted(types))}"),
            _SUPPORT_WEIGHT,
        ))
    if attrs:
        out.append((
            Predicate(card_class="monster", attribute=attrs, main_deck_only=True,
                      raw=f"{SUPPORT_WANT_PREFIX}{'/'.join(sorted(attrs))}"),
            _SUPPORT_WEIGHT,
        ))
    return out


def _fusion_materials(card: Card, known_names) -> list[tuple[Predicate, float]]:
    """Wants for a Fusion Monster's materials.

    Fusion Summoning was the single largest hole in the model: 147 Extra Deck
    Fusions and every Fusion spell parsed to nothing, which is why Instant Fusion
    and Future Fusion each needed a hand-written bundle to work at all, and why
    Gem-Knight and Elemental HERO decks were among the least understood in the
    corpus.  The materials are written on the card; read them.
    """
    if not (card.is_extra and not card.is_synchro and card.desc):
        return []
    head = re.split(r"(?<=[.\n])", card.desc, maxsplit=1)[0]
    if " + " not in head:
        return []
    parts = [q.strip().rstrip(".") for q in _FUSION_SPLIT.split(head) if q.strip()]
    # Attributes of the materials as written, used to decide whether an
    # Attribute-restricted substitute (the Hex-Sealed Fusions) is legal here.
    _substitutes()
    other_attrs: set[str] = set()
    for part in parts:
        pr, _c, _r = parse_predicate(part, known_names=known_names)
        if pr is None:
            continue
        if pr.attribute:
            other_attrs |= set(pr.attribute)
        for nm in pr.exact_names or ():
            a = (_ATTR_BY_NAME or {}).get(nm)
            if a:
                other_attrs.add(a)
    subs = _substitute_names_for(other_attrs)

    out: list[tuple[Predicate, float]] = []
    seen: set[tuple] = set()
    counts: dict[tuple, int] = {}
    for part in _FUSION_SPLIT.split(head):
        part = part.strip().rstrip(".")
        if not part:
            continue
        pred, _count, _residue = parse_predicate(part, known_names=known_names)
        if pred is None or pred.is_empty():
            continue
        # A named material can be supplied by a substitute instead.  Without
        # this, King of the Swamp satisfied nothing at all: the want is an
        # exact-name filter and he is not named on any Fusion Monster.  Widening
        # the name set is enough — the existing bitset machinery does the rest.
        if pred.exact_names:
            pred = replace(
                pred,
                exact_names=pred.exact_names | subs,
                raw=f"{pred.raw} (or a Fusion substitute)",
            )
        counts[pred.key()] = counts.get(pred.key(), 0) + 1
        if pred.key() in seen:
            continue
        seen.add(pred.key())
        out.append((pred, 1.0))
    # '"Cyber Dragon" + "Cyber Dragon" + "Cyber Dragon"' is ONE want that needs
    # three copies.  Emitting three wants would farm triple synergy; emitting one
    # at unit weight understated it.  Weight by the multiplicity instead, damped
    # so a 3-material Fusion is not three times the deckbuilding constraint.
    return [
        (pred, w * (1.0 + 0.5 * (counts[pred.key()] - 1)))
        for pred, w in out
    ]


def _capabilities(card: Card, cl: list[Clause]) -> tuple[frozenset[str], frozenset[str]]:
    """``(requires, provides)`` capability tags for the trigger-enabler model."""
    desc = card.desc
    requires = {name for name, pat in _REQUIRES if pat.search(desc)}
    provides = {name for name, pat in _PROVIDES if pat.search(desc)}

    # Structural providers, read off the clauses rather than the raw text.
    for c in cl:
        # Taking or swapping control puts the OPPONENT's monsters on your field,
        # where they are legal Fusion / Synchro material.  A deck running Mind
        # Control (123 era decks) or Brain Control (129) can therefore assemble a
        # Fusion whose named materials it does not run a single copy of —
        # Chimeratech Fortress Dragon off a stolen Cyber Dragon being the
        # textbook case.  Anything that checks "are this card's materials in my
        # deck" has to stand down when this is present.
        if c.verb in ("take_control", "control_swap"):
            provides.add("borrow_monster")
        if c.verb == "bounce" and c.side == "you":
            provides.add("bounce_self")
        if c.verb == "discard" and c.kind == "cost":
            provides.add("discard_self")
        if c.verb == "tribute" and c.kind == "cost":
            provides.add("tribute_self")
        if c.verb in ("mill", "send") and c.zone_from in ("deck", "hand"):
            provides.add("send_gy")
        if c.verb == "banish" and c.side == "you":
            provides.add("banish_self")

    # …and from the wiki, for the deck-mills the grammar does not reach.
    #
    # Future Fusion's "send the Fusion Materials listed on it from your Main Deck
    # to the GY" yields no mill/send clause at all, so it did not provide
    # `send_gy` and every card REQUIRING one — Dandylion, Necro Gardna, Treeborn
    # Frog — took the no-enabler penalty next to it.  **33 cards** are in that
    # state: Painful Choice, Reasoning, Monster Gate, Card Trooper, Destiny Hero
    # - Diamond Dude among them.  The wiki's "Sends from your Deck to your
    # Graveyard" category names the fact directly, and `gy_setup` is mapped from
    # exactly that, so it is the same claim by a more reliable route.
    if "gy_setup" in (wikitags.tags_for(card) or frozenset()):
        provides.add("send_gy")
    # An Extra Deck Fusion cannot be Summoned by the Synchro machinery, so it is
    # dead unless the main deck supplies a Fusion spell.  This is what makes the
    # generic enabler penalty catch it, instead of a per-card curated bundle.
    #
    # …except for a CONTACT Fusion, which summons itself by shuffling or
    # banishing its own materials and says so: "(You do not use
    # 'Polymerization.')".  21 cards in this pool do — every Gladiator Beast
    # Fusion, the XYZ-Dragon Cannon family, the Neos family — and requiring a
    # Fusion spell they never use cost them the p_enabler penalty (4.00) in the
    # very decks built to summon them.  Seeded on Gyzarus, the generator left
    # Heraklinos out entirely.
    # …and not when exactly one NAMED card is allowed to Summon it: Neo-Spacian
    # Marine Dolphin comes down with "NEX", never with a Fusion Spell, so
    # requiring one on top of its named Summoner made it permanently unsummonable
    # (the want was satisfied and the capability never could be).
    if (
        card.is_extra
        and not card.is_synchro
        and not _is_contact_fusion(card)
        and not _NAMED_SUMMONER.search(card.desc or "")
    ):
        requires.add("fusion_summon")
    # A Ritual Monster sits in the MAIN deck but is every bit as dead as a Fusion
    # without its enabler: 31 of the pool's 38 carried no requirement at all, so
    # Black Luster Soldier read as a free Level 8 body.
    if _is_ritual_monster(card):
        requires.add("ritual_summon")
    # "Any card sent to the Graveyard IS BANISHED instead" trips the banish_self
    # trigger pattern, which reads it as a card waiting for the deck to banish
    # something.  It is the opposite: it is the thing doing the banishing.
    if "banished instead" in desc.lower():
        requires.discard("banish_self")
        provides.add("banish_self")
    # A card that both needs and supplies a capability is self-sufficient.
    return frozenset(requires - provides), frozenset(provides)


def _thinning(card: Card, cl: list[Clause]) -> int:
    """How many cards this removes from the Deck when used — deck *thinning*.

    A card that replaces itself makes the deck functionally smaller, which
    raises the draw odds of everything left.  Three Upstart Goblin is the
    canonical case: it is universally described as playing a 37-card deck, and
    that is a real, measurable consistency gain the model was blind to.

    Counts cards pulled out of the Deck (draws, searches, mills, sends), not the
    card's cost — economy already prices the cost.  Capped at 2 because past
    that the card is a combo piece rather than a thinner.
    """
    if card.card_class == "monster":
        return 0
    pulled = 0
    for c in cl:
        if c.kind not in ("gain", "cost") or c.side != "you":
            continue
        if c.verb == "draw":
            pulled += int(c.count.n or 1)
        elif c.verb in ("search", "mill") and c.zone_from == "deck":
            pulled += int(c.count.n or 1)
        elif c.verb == "send" and c.zone_from == "deck":
            pulled += int(c.count.n or 1)
    return min(2, pulled)


#: A Token is created by the effect that names it, never drawn from the Deck, so
#: it is not a deck requirement.  Gorz asks for "1 Emissary of Darkness Token" —
#: a want nothing in a 4,076-card pool can satisfy, which left every deck running
#: Gorz permanently paying an orphan penalty for a card it manufactures itself.
_TOKEN_REF = re.compile(r"\btokens?\b", re.I)


def _references_token(pred: Predicate) -> bool:
    if pred.archetype and _TOKEN_REF.search(pred.archetype):
        return True
    if pred.exact_names and any(_TOKEN_REF.search(n) for n in pred.exact_names):
        return True
    return bool(_TOKEN_REF.search(pred.raw))


def _is_want(c: Clause) -> bool:
    """Does this clause make the deck's own contents matter?"""
    if c.predicate is None or c.side == "opponent" or c.predicate.is_empty():
        return False
    if _references_token(c.predicate):
        return False

    # An archetype or named-card reference is a deck requirement whatever the
    # clause does with it.  "Ancient City - Rainbow Ruins" only functions with
    # "Crystal Beast" cards in the Spell & Trap Zone, but that is stated as a
    # *condition*, not a search — so without this, such cards looked free and the
    # search happily put narrow archetype support into decks with no archetype.
    if c.predicate.archetype or c.predicate.exact_names:
        return True

    # A cost paid with *specific* cards is a deck requirement as surely as a
    # search is.  Dark Armed Dragon banishing "1 DARK monster from your GY" needs
    # DARK monsters in the deck; Chaos Sorcerer's summoning condition needs LIGHT
    # and DARK.  Restricting wants to fetch-verbs meant every card whose
    # requirement is a cost looked like it had no requirement at all.
    if c.verb in COST_WANT_VERBS and c.zone_from in WANT_ZONES:
        return True
    if c.verb == "summon_cost":
        return True

    if c.verb not in WANT_VERBS:
        return False
    zone = c.zone_from or ("" if c.verb == "equip" else None)
    if c.verb in ("search", "special_summon", "send", "mill"):
        return zone in WANT_ZONES
    return True


#: "1 LIGHT and 1 DARK monster" is a conjunction; "1 LIGHT or DARK monster" is a
#: disjunction.  The grammar folds both into one attribute set, which reads as OR
#: — so a deck of 18 DARK monsters and no LIGHT satisfied Chaos Sorcerer on paper
#: while being unable to summon it.
_CONJUNCTION = re.compile('\\band\\b', re.I)
_DISJUNCTION = re.compile('\\bor\\b', re.I)


def split_conjunctions(pred: Predicate) -> list[Predicate]:
    """Split an AND-joined predicate into one predicate per requirement.

    Rather than teaching :class:`Predicate` conjunction semantics, an AND becomes
    *several wants*, each satisfied independently.  That is what the card
    actually asks for — one LIGHT monster and one DARK monster are two separate
    things the deck must contain — and it means the orphan penalty fires if
    either half is missing instead of only when both are.
    """
    import dataclasses

    if not pred.attribute or len(pred.attribute) < 2:
        return [pred]
    if _DISJUNCTION.search(pred.raw) or not _CONJUNCTION.search(pred.raw):
        return [pred]  # a genuine "LIGHT or DARK" stays one disjunctive want
    return [
        dataclasses.replace(pred, attribute=frozenset({a}), raw=f"{a} half of {pred.raw}")
        for a in sorted(pred.attribute)
    ]


def derive_tags(card: Card, cl: list[Clause]) -> frozenset[str]:
    """Behavioural tags used by the power model and the tag synergy channel."""
    tags: set[str] = set()
    desc = card.desc

    for tag, pat in _TAG_PATTERNS:
        if pat.search(desc):
            tags.add(tag)

    # "is not destroyed by battle" satisfies the general `protection` pattern as
    # well as the new battle-specific one, and both are paid in power.py — Dark
    # Resonator's power jumped to +2.37 off one clause counted twice.  Keep the
    # broader tag, which is the one with a fitted coefficient.
    if "battle_immune" in tags and "protection" in tags:
        tags.discard("battle_immune")

    verbs = {c.verb for c in cl}
    if "search" in verbs:
        tags.add("searcher")
    if "draw" in verbs:
        tags.add("draw")
    if "negate" in verbs:
        tags.add("negate")
    if any(c.verb in ("mill", "send") and c.zone_from == "deck" for c in cl):
        tags.add("gy_filler")
    if any(c.verb == "discard" and c.kind == "cost" for c in cl):
        tags.add("discard_outlet")
    if any(c.zone_from == "gy" and c.side == "you" for c in cl):
        tags.add("gy_payoff")
    if re.search(r"\bthis card is (?:discarded|sent to the (?:GY|Graveyard))", desc, re.I):
        tags.add("discard_payoff")
    if _MASS.search(desc):
        tags.add("mass_removal")
    if re.search(r"\ball monsters (?:on the field|your opponent controls)\b", desc, re.I):
        tags.add("symmetric")
    if any(c.verb == "special_summon" and c.zone_from in ("deck", "gy") for c in cl):
        tags.add("summoner")
    if card.is_tuner:
        tags.add("tuner")
    if card.card_class == "monster" and not card.desc:
        tags.add("vanilla")
    if _SELF_COPIES.search(desc):
        tags.add("needs_self_copies")
    # Cheats ITSELF onto the field.  Gorz is Level 7 but Special Summons from
    # hand when you take damage, so taxing it two tributes is wrong -- and its
    # condition is a trigger, not a , so the GY-condition exemption
    # never covered it.
    if any(
        c.verb == "special_summon" and c.self_ref and c.zone_from in ("hand", "gy")
        for c in cl
    ):
        tags.add("self_ss")
    # Sending from your own Deck to the GY is setup, not loss — it is why
    # Foolish Burial is a staple.  Tagged so the power model can pay for it and
    # so it pairs with gy_payoff cards.
    if any(
        c.verb in ("send", "mill") and c.zone_from == "deck" and c.side == "you"
        for c in cl
    ):
        tags.add("gy_setup")

    # ── mechanic tags, read off the CLAUSES rather than the raw text ─────────
    #
    # Derived from what the card was parsed to *do*, so they cannot drift out of
    # step with the economy model the way a second set of regexes would.
    #
    # Found by listing the cards the format actually plays whose only tag was
    # structural: 26 main-deck cards in >=5 era decks, and they fell into five
    # clean groups.  The parser understood every one of them — it had simply
    # never given the behaviour a name, so no deck-level channel could see it.
    _opp = ("opponent", "both", "either")
    if any(
        c.kind == "gain" and c.side in _opp and c.count.kind in ("fixed", "up_to")
        and c.verb in ("destroy", "banish", "bounce", "shuffle", "spin")
        for c in cl
    ):
        # Single-target answers: MST, Dimensional Prison, Compulsory Evacuation
        # Device, Icarus Attack.  `mass_removal` existed; its one-for-one
        # counterpart, which is most of what a deck's interaction actually is,
        # did not.
        tags.add("spot_removal")
    if any(c.verb in ("take_control", "control_swap") for c in cl):
        # Brain Control (129 era decks) and Mind Control (123).  Also the thing
        # that lets a deck supply Fusion/Synchro material it does not own — see
        # the `borrow_monster` capability.
        tags.add("control_theft")
    if any(c.kind == "gain" and c.verb == "discard" and c.side == "opponent" for c in cl):
        tags.add("hand_disruption")
    if _OPPONENT_TURN.search(desc):
        tags.add("opponent_turn")
    if _SUMMON_ANSWER.search(desc) and any(
        c.verb in ("negate", "destroy", "banish", "bounce") for c in cl
    ):
        tags.add("summon_answer")
    if card.card_class == "monster" and _FREE_BODY.search(desc):
        tags.add("free_body")
    # ── mechanics found by clustering the 746 cards that PARSED but had no
    # mechanic tag, ranked by how much the era corpus plays them ─────────────
    if any(c.verb == "battle_trigger" for c in cl) or any(
        c.verb == "trigger_object" and c.side == "opponent" for c in cl
    ):
        # 189 era-deck appearances, the largest uncovered group.  An effect that
        # fires FROM COMBAT is paid for by attacking, which the deck was doing
        # anyway -- Goyo Guardian (187 decks) is the headline, and it had no tag
        # of any kind.  Distinct from `battle_removal`, which is the subset that
        # removes the monster it fought.
        tags.add("battle_payoff")
    if any(c.verb == "stat_loss" for c in cl):
        # 122 era decks.  `stat_boost` existed for pumping your own monster; its
        # mirror -- shrinking theirs -- did not, though it wins the same combats.
        tags.add("stat_debuff")
    if any(c.verb in ("once_per_turn", "standby_trigger") for c in cl) and any(
        c.kind == "gain" for c in cl
    ):
        # A repeatable effect is an ENGINE, not a one-shot.  economy has
        # `mod.recurrence` for Continuous cards but nothing named it, so a
        # monster with a once-per-turn payoff read like a vanilla body.
        tags.add("recurring")
    if any(c.verb == "gain_lp" for c in cl):
        tags.add("lifegain")
    if "summoner" not in tags and any(
        c.kind == "gain" and c.verb == "special_summon" and c.side == "you"
        and not c.self_ref
        for c in cl
    ):
        # 204 era decks' worth of cards that put a body on the field and were
        # never called summoners, because the existing rule wanted a zone.
        tags.add("summoner")
    if _TOKEN_MAKER.search(desc):
        # Scapegoat's four bodies are tribute and Synchro fodder, which is the
        # one thing the model never prices about them.
        tags.add("token_maker")
    if _BANISH_PAYOFF.search(desc):
        tags.add("banish_payoff")

    # Graveyard denial is a FLOODGATE and it is SYMMETRIC.  Dimensional Fissure,
    # Macro Cosmos and Banisher of the Radiance shut off an entire strategy —
    # every GY engine in the format — for BOTH players, which is the Macro
    # Cosmos family's whole identity.  They carried only `gy_denial`, which is
    # the deck-level ANTI-synergy (it charges the holder for voiding its own
    # engine) and says nothing about what the card does to the opponent.
    if "gy_denial" in tags:
        tags.add("floodgate")
        tags.add("symmetric")

    # ── the wiki overrides every tag it can express ──────────────────────────
    #
    # Everything above is a reconstruction of "what does this card do" from
    # regexes; the Fandom wiki carries that answer hand-curated, per card, and
    # `wikitags` maps it onto this same vocabulary.  Where both speak, the wiki
    # wins — the regexes were an approximation of it, and the diff says so:
    # `floodgate` had 292 false positives (every Nomi monster, via "cannot be
    # Special Summoned"), `recursion` found 77 of 432, and `battle_immune`
    # matched **zero** cards because the dedup below always discarded it.
    #
    # A tag with no wiki counterpart keeps its regex (see wikitags.DERIVED_ONLY),
    # and a card the scrape never resolved keeps all of them.
    wiki = wikitags.tags_for(card)
    if wiki is not None:
        tags = (tags - wikitags.AUTHORITATIVE) | wiki

    # ── fallback: name whatever the card DOES, for anything still unnamed ────
    #
    # 484 cards parsed cleanly and still had no mechanic tag.  They are not
    # exotic — they are the long tail of one-verb cards (a bare targeting
    # effect, an equip, a tribute cost) plus 57 Extra Deck monsters whose ONLY
    # clause is their material line, i.e. vanilla beaters with no effect at all
    # (Gaia Knight, X-Saber Urbellum, Junk Warrior).
    #
    # Applied ONLY when nothing above fired, so it never dilutes a card that
    # already has a real mechanic.  These name behaviour rather than claim value:
    # every one ships at 0.00 and the fit decides.
    if not tags:
        verbs = {c.verb for c in cl}
        if card.is_extra and verbs <= {"material", "frequency_limit", "once_per_turn"}:
            tags.add("extra_vanilla")
        for verb, name in _FALLBACK_TAGS:
            if verb in verbs:
                tags.add(name)
                break

    # ── structural tags: EVERY card gets at least one ────────────────────────
    #
    # 1,503 of the 4,076 playable cards came out with no tags at all — 233
    # Normal Monsters, 579 Effect Monsters, 346 Spells, 345 Traps — so anything
    # that reasons over tags (the deck-level channels, mining's tag_play_rate,
    # the randomiser's fallback when per-cid play rate is untrustworthy) simply
    # could not see a third of the pool.  A card with nothing to say about itself
    # should still say *what it is*.
    #
    # `vanilla` in particular was declared in _TAG_KEYS and priced at -0.30 in
    # params.toml and assigned to **zero cards** — a dead coefficient, like
    # gain.negate_destroy was.  A Normal Monster really is worth less than its
    # stat line suggests, and now that is charged.
    if card.card_class == "monster":
        tags.add("vanilla" if "normal" in card.monster_flags else "effect_monster")
    elif card.card_class == "spell":
        tags.add("spell_card")
    else:
        tags.add("trap_card")
    return frozenset(tags)


#: Board tags on a target predicate that imply which zone a pronoun came from.
_BOARD_ZONE = {"your_gy": "gy", "either_gy": "gy", "field": "field"}

#: A Fusion that puts ITSELF onto the field out of its own materials, with no
#: Fusion spell involved.  The card always says so explicitly, in one of two
#: idioms: the parenthetical disclaimer, or "Must first be Special Summoned … by
#: shuffling/banishing/sending the above cards you control".
_CONTACT_FUSION = re.compile(
    r"do not use ['\"]Polymerization|without using ['\"]Polymerization"
    r"|Must first be Special Summoned \(from your Extra Deck\) by "
    r"(?:shuffling|banishing|sending|returning|Tributing)",
    re.I,
)


def _is_contact_fusion(card) -> bool:
    return bool(card.desc) and bool(_CONTACT_FUSION.search(card.desc))


#: An EXPLICIT self-reference, which is never a pronoun awaiting an antecedent.
#: ``Clause.self_ref`` cannot tell "it" from "this card" — both simply have no
#: predicate — so without this, D.D. Warrior Lady's "banish that monster, also
#: banish **this card**" bound its own removal to the opponent's monster and the
#: card scored +2.09, being paid twice for banishing one thing and itself.
_EXPLICIT_SELF = re.compile(
    r"\bthis (?:face-up )?card\b|\bitself\b|\bthis monster\b", re.I
)

#: Removal verbs that consume the card they resolve against.
_CONSUMING = frozenset({"destroy", "banish", "bounce", "shuffle", "send", "spin"})

#: An anaphoric noun phrase — "those cards", "that target", "them".  These parse
#: into a Predicate that is non-None but carries no constraint at all, so
#: ``self_ref`` is False and the pronoun binding below skipped them entirely.
#: Brionac, in 95% of the era's decks, says "target the same number of cards your
#: opponent controls; return **those cards** to the hand": the bounce kept an
#: empty predicate and side="you", ``_gain_key`` returned None for it, and the
#: best card in the format scored econ **-0.00**.
_ANAPHOR = re.compile(r"^\s*(?:those|these|that|the)\s+\w+|^\s*(?:them|they|it)\b", re.I)


def _is_anaphor(pred) -> bool:
    """A predicate that only points back at something already named."""
    return (
        pred is not None
        and pred.is_empty()
        and bool(_ANAPHOR.match(pred.raw or ""))
    )


#: "4 or more \"Lightsworn\" monsters with different names" — copies do not
#: help.  See Predicate.distinct_names.
_DISTINCT_NAMES = re.compile(r"with (?:a )?different names?", re.I)


#: A pronoun clause that states its own number keeps it.
_HAS_DIGIT = re.compile(r"\d")


def resolve_pronouns(clauses: list[Clause]) -> list[Clause]:
    """Bind ``"destroy it"`` to whatever the sentence targeted.

    Without this, ``"Target 1 Spell/Trap on the field; destroy it"`` looks like a
    card destroying *itself* and Mystical Space Typhoon scores −1 instead of 0.
    A pronoun only falls back to meaning "this card" when the sentence set up no
    target at all — which is the Rekindling case ("banish **them**", meaning the
    monsters it just summoned), and that one is correctly left as a self-ref.
    """
    from dataclasses import replace

    antecedent: Clause | None = None
    #: Antecedent keys already removed by an earlier gain in this sentence.
    consumed: set = set()
    out: list[Clause] = []
    for c in clauses:
        # Any *condition* that names a card can be the antecedent — both an
        # explicit "Target 1 …" requirement and a trigger like "When your
        # opponent Special Summons a monster with 1500 or more ATK".  Restricting
        # this to targets alone is why Bottomless Trap Hole scored −0.92: its
        # "Destroy that monster" looked like the card destroying itself, so the
        # removal was dropped and one of the format's most-played traps read as
        # a dead card.  Gain clauses deliberately do NOT become antecedents, or
        # Rekindling's "banish them" would be charged as a cost on top of the
        # `temporary` modifier that already prices it.
        if c.kind == "condition" and c.predicate is not None:
            antecedent = c
        elif (
            (c.self_ref and c.predicate is None) or _is_anaphor(c.predicate)
        ) and antecedent is not None and not _EXPLICIT_SELF.search(c.raw):
            key = antecedent.predicate.key()
            # "Destroy that monster, and if you do, banish it" moves ONE card.
            # Binding both to the antecedent and paying for both made Bottomless
            # Trap Hole +1.10 of card advantage for removing a single monster.
            # A second removal against an already-removed target is a
            # *replacement effect*, not a second card.
            if c.kind == "gain" and c.verb in _CONSUMING and key in consumed:
                continue
            zone = c.zone_from
            if zone is None:
                zone = next(
                    (_BOARD_ZONE[b] for b in antecedent.predicate.board if b in _BOARD_ZONE),
                    None,
                )
            # …and how MANY it moves.  "Target 2 cards on the field; destroy
            # them" bound the predicate and the side but kept `destroy`'s
            # default count of 1, so Icarus Attack — tribute 1, destroy 2 —
            # priced as a 1-for-2 at −1.00 economy and sat at rank 817 of the
            # 876 cards the era actually plays, despite being the signature
            # Blackwing trap.  Guarded twice: only when the anaphor took the
            # default count, and only when its own text states no number, so
            # "destroy 1 of them" keeps its own 1.
            count = c.count
            if (
                c.count.kind == "fixed"
                and c.count.n == 1
                and antecedent.count != c.count
                and not _HAS_DIGIT.search(c.raw)
            ):
                count = antecedent.count
            c = replace(
                c,
                predicate=antecedent.predicate,
                count=count,
                zone_from=zone,
                side=antecedent.side,
                self_ref=False,
            )
        # Any removal that names its target consumes it, whether it was written
        # out in full or bound from a pronoun.  Bottomless Trap Hole's "Destroy
        # that monster with 1500 or more ATK" carries its own predicate and so
        # never enters the branch above — leaving "banish it" free to bind and be
        # paid a second time for the same monster.
        if c.kind == "gain" and c.verb in _CONSUMING and c.predicate is not None:
            consumed.add(c.predicate.key())
        out.append(c)
    return out


def _by_sentence(card: Card, known_names):
    """Yield ``(clauses, segments)`` grouped by sentence.

    Grouping matters because ``"Target 1 Spell/Trap on the field; destroy it."``
    is one sentence split into two segments — the antecedent lives in the first
    and the pronoun in the second.
    """
    groups: list[tuple[str, list]] = []
    for seg in segment(card.desc):
        if groups and groups[-1][0] == seg.sentence:
            groups[-1][1].append(seg)
        else:
            groups.append((seg.sentence, [seg]))
    for _, segs in groups:
        clauses: list = []
        for seg in segs:
            clauses.extend(clause_mod.extract(seg, known_names=known_names))
        yield clauses, segs


def parse_card(card: Card, *, known_names: frozenset[str] | None = None) -> ParsedCard:
    """Parse one card's text into clauses, tags and wants."""
    if not card.desc:
        return ParsedCard(cid=card.cid, tags=derive_tags(card, []), parse_confidence=1.0)

    cl: list[Clause] = []
    unparsed: list[str] = []
    for sentence_clauses, segs in _by_sentence(card, known_names):
        cl.extend(resolve_pronouns(sentence_clauses))
        if not sentence_clauses:
            unparsed.extend(
                s.text for s in segs if s.role == "effect" and len(s.text) > 12
            )

    # One want per distinct predicate, keeping the strongest weight.  Morphtronic
    # Remoten's text mentions "Morphtronic" six times; counted separately those
    # six wants earned six times the synergy of a normal card, which is how a
    # two-card Morphtronic package bootstrapped its way into a Rekindling deck.
    best: dict[tuple, tuple[Predicate, float]] = {}
    for c in cl:
        if not _is_want(c):
            continue
        weight = 1.0 if c.verb in ("search", "special_summon") else 0.5
        if c.temporary:
            weight *= 0.6
        # A want is a deckbuilding requirement, and the only pile you draw from
        # is the Main Deck — so an Extra Deck monster cannot answer one UNLESS
        # the clause explicitly reaches the Extra Deck.  Instant Fusion's
        # "Special Summon 1 Fusion Monster" genuinely wants an Extra Deck card;
        # Stratos' "add 1 HERO monster" genuinely cannot use one.
        main_only = "extra" not in (c.zone_from or "", c.zone_to or "")
        # "…with different names" counts NAMES, not copies — see
        # Predicate.distinct_names.
        distinct = bool(_DISTINCT_NAMES.search(c.raw or ""))
        for pred in split_conjunctions(c.predicate):
            if main_only and not pred.main_deck_only:
                pred = replace(pred, main_deck_only=True)
            if distinct and not pred.distinct_names:
                pred = replace(pred, distinct_names=True)
            key = pred.key()
            if key not in best or best[key][1] < weight:
                best[key] = (pred, weight)
    wants = _tighten_synchro_revival(card, cl, list(best.values()))
    # A Fusion Monster's materials are wants like any other, so the search pulls
    # the pieces in and the orphan penalty fires when it cannot.
    for pred, weight in _fusion_materials(card, known_names):
        if pred.key() not in best:
            wants.append((pred, weight))
    # A Ritual Spell wants the monster it names, and nothing else can supply it.
    for pred, weight in _ritual_partners(card, known_names):
        if pred.key() not in best:
            wants.append((pred, weight))
    # "…cannot be Special Summoned except with 'NEX'" — exactly one card in the
    # world can put this on the field, so it wants that card as hard as a Ritual
    # Monster wants its Spell.  Neo-Spacian Marine Dolphin was the top-ranked
    # Extra Deck card in the model with zero plays in the era corpus.
    for pred, weight in _named_summoner(card):
        if pred.key() not in best:
            wants.append((pred, weight))
    # "Supports: Plant" — the Type/Attribute constraint the text does not state.
    for pred, weight in _support_wants(card):
        if pred.key() not in best:
            wants.append((pred, weight))

    load_bearing = [c.confidence for c in cl if c.kind in ("gain", "cost")]
    confidence = min(load_bearing) if load_bearing else (0.5 if unparsed else 1.0)

    requires, provides = _capabilities(card, cl)
    thins = _thinning(card, cl)
    return ParsedCard(
        cid=card.cid,
        clauses=cl,
        tags=derive_tags(card, cl),
        wants=wants,
        parse_confidence=confidence,
        unparsed=unparsed,
        exclusive_modes=is_exclusive(card.desc),
        requires=requires,
        provides=provides,
        thins=thins,
    )


#: Card types whose ``desc`` is flavour text, not rules text.  A Normal Monster
#: yielding no clause is a correct parse, so counting it as a miss would make
#: the coverage metric unfalsifiable in the wrong direction.
FLAVOUR_ONLY_TYPES = frozenset({1, 31, 5, 9, 35})  # Normal, Normal Tuner, and
# effect-less Fusion/Ritual/Synchro (their text is only a material line)


def effect_bearing(card: Card) -> bool:
    """True when the card's text is supposed to describe an effect."""
    return card.has_text and card.card_type_encoded not in FLAVOUR_ONLY_TYPES


### Which archetypes are real *mechanics* rather than shared names.
###
### ygoprodeck tags Chaos Sorcerer, Chaos Command Magician, Sphere of Chaos and
### Chaos Trap Hole all as archetype "Chaos", but no card in the game searches
### for or supports "Chaos" — it is a naming family, not an engine.  Treating it
### as a theme made the generator build a Chaos Sorcerer deck out of cards that
### merely share a word, including Chaos Trap Hole at impact -0.62.
###
### A theme is real if some card's *text* references it.  Blackwing, Flamvell,
### Six Samurai, Gladiator Beast and Lightsworn all pass; Chaos does not.
_REFERENCED: frozenset[str] = frozenset()


def referenced_archetypes() -> frozenset[str]:
    """Archetypes some card's text actually names, lowercased."""
    return _REFERENCED


def is_real_archetype(name: str | None) -> bool:
    """True when *name* is a mechanical archetype, not just a shared word."""
    return bool(name) and name.lower() in _REFERENCED


@dataclass
class CoverageReport:
    """Parser health — the gate that says whether the model can be trusted."""

    cards: int
    with_text: int
    effect_bearing: int
    with_clause: int
    total_clauses: int
    wants: int
    #: Predicates matching *no* card in the pool.  Either a mis-parse or a real
    #: reference to an archetype this 2011 ROM never shipped — both worth seeing.
    empty_predicates: list[str]
    #: Predicates naming an archetype or card this ROM's 4,076-card pool does not
    #: contain.  Correct parses of cards that are simply unplayable here.
    absent_archetypes: list[str]
    #: Predicates matching most of the pool.  Usually correct but unrestrictive
    #: ("1 monster"); the synergy model discounts these, it does not reject them.
    generic_predicates: int
    distinct_predicates: int
    low_confidence: list[tuple[int, float]]
    unparsed_samples: list[tuple[str, str]]

    @property
    def clause_rate(self) -> float:
        """Fraction of *effect-bearing* cards that yielded at least one clause."""
        return self.with_clause / self.effect_bearing if self.effect_bearing else 0.0

    @property
    def empty_rate(self) -> float:
        if not self.distinct_predicates:
            return 0.0
        return len(self.empty_predicates) / self.distinct_predicates

    def format(self) -> str:
        return "\n".join(
            [
                f"cards parsed        : {self.cards} ({self.with_text} with text)",
                f"effect-bearing      : {self.effect_bearing} (excludes Normal-Monster flavour text)",
                f"yielded >=1 clause  : {self.with_clause}  ({self.clause_rate:.1%})",
                f"clauses extracted   : {self.total_clauses}",
                f"wants (deck-facing) : {self.wants} over {self.distinct_predicates} distinct predicates",
                f"  mis-parsed (0 hits): {len(self.empty_predicates)} ({self.empty_rate:.1%})",
                f"  archetype absent  : {len(self.absent_archetypes)} (correct; not in this ROM)",
                f"  generic (>800)    : {self.generic_predicates} (correct but unrestrictive)",
                f"low-confidence cards: {len(self.low_confidence)}",
            ]
        )


def parse_pool(cards: list[Card]) -> tuple[dict[int, ParsedCard], CoverageReport]:
    """Parse every card and measure how well the grammar did."""
    known = frozenset(c.name_key for c in cards)
    parsed = {c.cid: parse_card(c, known_names=known) for c in cards}

    # A predicate that matches nothing, or nearly the whole pool, is almost
    # always a mis-parse rather than a real card filter.
    reps: dict[tuple, Predicate] = {}
    for pc in parsed.values():
        for pred, _ in pc.wants:
            reps.setdefault(pred.key(), pred)
    # Two very different reasons a want can match nothing, and only one is a bug:
    # a mis-parse, versus a card correctly asking for an archetype this 2011 ROM
    # never shipped ("Ultimate Crystal").  The latter is useful information — the
    # card is genuinely unplayable here — so it is counted separately rather than
    # held against the parser.
    empty: list[str] = []
    absent_archetype: list[str] = []
    generic = 0
    for pred in reps.values():
        n = sum(1 for c in cards if pred.matches(c))
        if n == 0:
            if pred.archetype or pred.exact_names:
                absent_archetype.append(pred.raw)
            else:
                empty.append(pred.raw)
        elif n > 800:
            generic += 1

    global _REFERENCED
    _REFERENCED = frozenset(
        pred.archetype.lower()
        for pc in parsed.values()
        for pred, _ in pc.wants
        if pred.archetype
    )

    live = [c for c in cards if effect_bearing(c)]
    by_cid = {c.cid: c for c in cards}
    unparsed = [
        (by_cid[cid].name, u)
        for cid, pc in parsed.items()
        for u in pc.unparsed
        if effect_bearing(by_cid[cid])
    ]
    return parsed, CoverageReport(
        cards=len(cards),
        with_text=sum(1 for c in cards if c.has_text),
        effect_bearing=len(live),
        with_clause=sum(1 for c in live if parsed[c.cid].clauses),
        total_clauses=sum(len(pc.clauses) for pc in parsed.values()),
        wants=sum(len(pc.wants) for pc in parsed.values()),
        empty_predicates=sorted(empty),
        absent_archetypes=sorted(absent_archetype),
        generic_predicates=generic,
        distinct_predicates=len(reps),
        low_confidence=sorted(
            (
                (cid, pc.parse_confidence)
                for cid, pc in parsed.items()
                if pc.parse_confidence < 0.6 and effect_bearing(by_cid[cid])
            ),
            key=lambda t: t[1],
        ),
        unparsed_samples=unparsed,
    )


# ── memoised access ─────────────────────────────────────────────────────────
# The parse is pure over (pool, grammar), and the grammar lives in source, so
# the module files hash into the cache key: editing a rule invalidates it.

_MODULE_SOURCES = tuple(
    [Path(__file__).parent / f
     for f in ("grammar.py", "clauses.py", "segment.py", "parse.py")]
    # The pickled objects are Clause / Predicate / Count / ParsedCard, so an edit
    # to their definitions has to invalidate the artifact as surely as an edit to
    # the parser does.  material.py feeds the Synchro-material wants; wikitags.py
    # and the scrape it reads decide most of the tags.
    + [Path(__file__).resolve().parents[1] / f
       for f in ("model.py", "material.py", "wikitags.py")]
    + [wikitags.CACHE]
)
SCHEMA = "deckgen.parsed.v2"


def load_parsed(
    cards: list[Card] | None = None, *, force: bool = False
) -> tuple[list[Card], dict[int, ParsedCard], CoverageReport]:
    """Parse the playable pool, reusing the cached result when nothing changed.

    The parse itself is cached, not just its report.  The previous version
    re-parsed all 4,076 cards on **every** invocation on the grounds that clause
    objects were "cheap to rebuild"; measured, that was 9.2s of a 12.7s startup —
    by far the largest fixed cost in the tool, paid by every build, every
    `explain`, and every one of the ~1,400 deck scores in a training run.
    """
    from otn_enhanced.deckgen import cache, cardpool

    if cards is None:
        cards = cardpool.playable(cardpool.load_pool())

    key = cache.source_map(
        [*_MODULE_SOURCES, cache.CACHE_DIR / f"{cardpool.SCHEMA}.json"]
    )
    hit = None if force else cache.load_pickle(SCHEMA, key)
    if hit is not None:
        return cards, hit["parsed"], hit["report"]

    parsed, report = parse_pool(cards)
    cache.store_pickle(SCHEMA, key, {"parsed": parsed, "report": report})
    return cards, parsed, report


def _report_to_json(r: CoverageReport) -> dict:
    return {
        "cards": r.cards,
        "with_text": r.with_text,
        "effect_bearing": r.effect_bearing,
        "with_clause": r.with_clause,
        "clause_rate": r.clause_rate,
        "total_clauses": r.total_clauses,
        "wants": r.wants,
        "empty_predicates": r.empty_predicates,
        "absent_archetypes": r.absent_archetypes,
        "generic_predicates": r.generic_predicates,
        "distinct_predicates": r.distinct_predicates,
        "low_confidence": r.low_confidence[:200],
    }
