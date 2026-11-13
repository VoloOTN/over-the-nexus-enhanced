"""Extract :class:`~..model.Clause` records from labelled text segments.

Each verb gets a pattern that captures the phrase naming *what* it acts on;
that phrase goes to :func:`grammar.parse_predicate`.  Target capture stops at
the first clause connector so ``"destroy 1 monster your opponent controls and
draw 1 card"`` does not swallow the draw into the destroy's predicate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from otn_enhanced.deckgen.model import Clause, Count, Predicate
from otn_enhanced.deckgen.text.grammar import parse_count, parse_predicate
from otn_enhanced.deckgen.text.segment import Segment

# Where a target phrase ends.  Deliberately excludes " in " and " with " so that
# "in your GY" and "with 200 DEF" stay attached to the predicate.
_STOP = (
    # " and " normally ends a target phrase, but not inside the compound head
    # noun "Spell and Trap Cards" — splitting there made Heavy Storm parse as
    # "destroy all Spell" and lose its symmetric side detection entirely.
    # NOT a bare `\s+to\s`: stopping at every "to" truncates target phrases that
    # legitimately continue, which cost 85 wants and -0.006 Spearman when tried.
    # The infinitive-of-purpose case ("Tribute this card **to destroy** …") is
    # handled by _LEADING_SELF at the capture site instead.
    r"(?=\s+from\s|\s+to\s+(?:your|the|its)\s|\s+and\s+(?!Trap|Spell)|\s+then\s|"
    r"\s+but\s|\s+also\s|[,;.]|$)"
)
_T = r"(.{0,120}?)"

ZONES = {
    "deck": "deck", "your deck": "deck", "the deck": "deck",
    "graveyard": "gy", "gy": "gy", "your graveyard": "gy", "your gy": "gy",
    "the graveyard": "gy", "the gy": "gy",
    "either graveyard": "gy", "either gy": "gy",
    "hand": "hand", "your hand": "hand", "the hand": "hand",
    # Disjunctive zones: take the better half, which is the one the card is
    # played for.  _ZONE_ALT sorts longest-first, so these win over "hand".
    "hand or deck": "deck", "deck or hand": "deck",
    "hand or graveyard": "gy", "hand or gy": "gy",
    "graveyard or hand": "gy", "gy or hand": "gy",
    "extra deck": "extra", "your extra deck": "extra",
    "field": "field", "the field": "field",
    "banished": "banished",
}
_ZONE_ALT = "|".join(sorted((re.escape(z) for z in ZONES), key=len, reverse=True))

_NUM = r"(\d+|one|two|three|１|２|３)"
_WORD_NUM = {"one": 1, "two": 2, "three": 3}


def _num(raw: str) -> int:
    raw = raw.strip().lower()
    return _WORD_NUM.get(raw, int(raw) if raw.isdigit() else 1)


@dataclass(frozen=True)
class VerbRule:
    verb: str
    pattern: re.Pattern
    zone_from: str | None = None
    zone_to: str | None = None
    #: group index of the target phrase, or None when the verb takes no target
    target_group: int | None = 1
    #: group index of a zone name to resolve dynamically
    zone_group: int | None = None
    side: str = "auto"


def _rx(p: str) -> re.Pattern:
    return re.compile(p, re.I)


RULES: tuple[VerbRule, ...] = (
    # ── card advantage ──────────────────────────────────────────────────────
    VerbRule("draw", _rx(rf"\bdraw {_NUM} cards?"), target_group=None),
    # "draw a number of cards equal to …" — the count is deck-dependent, not a
    # literal, so the rule above matched nothing and Super Rejuvenation (a draw
    # engine that pays off discarding and Tributing Dragons) parsed to zero
    # clauses.  Counted as `as_many`, which is how the model already handles a
    # count it cannot know without seeing the deck.
    VerbRule(
        "draw",
        _rx(r"\bdraw a number of cards equal to\b|\bdraw that many cards\b"),
        target_group=None,
    ),
    VerbRule(
        "mill",
        _rx(rf"\bsend the top {_NUM} cards? of (?:your|the) Deck to the (?:GY|Graveyard)"),
        zone_from="deck", zone_to="gy", target_group=None,
    ),
    VerbRule(
        "search",
        _rx(rf"\badd {_T} from (?:your|the) ({_ZONE_ALT}) to (?:your|the) hand"),
        zone_to="hand", zone_group=2,
    ),
    VerbRule("search", _rx(rf"\badd {_T} to (?:your|the) hand"), zone_to="hand"),
    # "Return it to YOUR hand" is recovery, not a bounce.  The bounce rule below
    # only accepts "the"/"its owner's" hand, so a card that rebuys one of its own
    # resources -- Dimensional Alchemist pulling a banished monster back --
    # matched nothing at all and scored -0.00 despite being a straight +1.
    # Ordered ahead of `bounce` so the "your hand" reading wins.
    VerbRule("search", _rx(rf"\breturn {_T} to your hand"), zone_to="hand"),
    # Zone-first word order: "Special Summon from your GY as many FIRE monsters".
    VerbRule(
        "special_summon",
        _rx(rf"\bSpecial Summon from (?:your|the) ({_ZONE_ALT}) {_T}{_STOP}"),
        target_group=2, zone_group=1,
    ),
    VerbRule(
        "special_summon",
        _rx(rf"\bSpecial Summon {_T} from (?:your|the) ({_ZONE_ALT})"),
        zone_group=2,
    ),
    # "Fusion Summon 1 'Elemental HERO' Fusion Monster from your Extra Deck".
    # Without this the Fusion spells raised no want, so nothing reserved an
    # Extra Deck slot for the Fusion they exist to summon -- a Miracle Fusion
    # deck came out with fifteen Synchros and no HERO Fusion at all.
    VerbRule("special_summon", _rx(rf"\bFusion Summon {_T}{_STOP}"), zone_from="extra"),
    VerbRule("special_summon", _rx(rf"\bSpecial Summon {_T}{_STOP}")),
    VerbRule("normal_summon", _rx(rf"\bNormal Summon {_T}{_STOP}")),
    # ── interaction ─────────────────────────────────────────────────────────
    VerbRule("destroy", _rx(rf"\bdestroy {_T}{_STOP}")),
    VerbRule("banish", _rx(rf"\bbanish {_T}{_STOP}")),
    VerbRule("banish", _rx(rf"\bremove {_T} from play")),
    VerbRule("bounce", _rx(rf"\breturn {_T} to (?:the|its owner's|their owner's) hand"), zone_to="hand"),
    # Spin: back to the TOP of the Deck.  Strictly better than a bounce -- the
    # card is gone AND it eats their next draw -- so it gets its own coefficient
    # above bounce_opp rather than sharing shuffle's.  Ordered before shuffle so
    # the more specific "top of the Deck" reading wins.
    VerbRule("spin", _rx(rf"\breturn {_T} to the top of the Deck"), zone_to="deck"),
    VerbRule("spin", _rx(rf"\bplace {_T} on (?:the )?top of the Deck"), zone_to="deck"),
    # Zone-bearing form FIRST: the dedup key is (verb, offset), so the bare rule
    # below would claim the same span and `from your hand` — which _STOP excludes
    # from the target capture — would be lost.  Without the zone a self-directed
    # shuffle is indistinguishable from an opponent-directed one, and Moray of
    # Greed put two cards back for free.
    VerbRule(
        "shuffle",
        _rx(rf"\bshuffle {_T} from (?:your|the) ({_ZONE_ALT}) into the Deck"),
        zone_to="deck", zone_group=2,
    ),
    VerbRule("shuffle", _rx(rf"\bshuffle {_T} into the Deck"), zone_to="deck"),
    # "return it to his/her Deck" is the 2004-era wording for a shuffle-back, and
    # it was matched by nothing at all — The Forceful Sentry (223 decks) produced
    # only a target condition and scored a flat -1.00 for doing nothing.
    # "its owner's" is Trap Dustshoot, the most-played card in the era corpus.
    VerbRule(
        "shuffle",
        _rx(rf"\breturn {_T} to (?:his/her|their|its owner's|the owner's"
            rf"|their owner's|your opponent's|the) Deck"),
        zone_to="deck",
    ),
    # Denying a draw is a card the opponent never gets: Time Seal and Drop Off
    # parsed to nothing at all.
    VerbRule(
        "draw_denial",
        _rx(r"\bSkip the Draw Phase of your opponent\b|\bskips? (?:their|his/her) Draw Phase\b"),
        target_group=None,
        side="opponent",
    ),
    # Creature Swap is the 4th most-played card the parser had nothing to say
    # about (186 appearances across the two corpora).  Trading your worst body
    # for their best is not card advantage, but it is real removal-equivalent
    # tempo, so it is scored as a discounted take_control.
    VerbRule(
        "control_swap",
        _rx(r"\bswitch(?:es)? control of those monsters\b|\bswitch control of the monsters\b"),
        target_group=None,
    ),
    # Milling the OPPONENT's Deck: progress toward decking them out, not cards.
    # The economy value is ~0; the `deckout` tag carries it at deck level.
    VerbRule(
        "mill_opponent",
        _rx(r"\bSend the top [\w-]+ cards? of your opponent's Deck to the (?:GY|Graveyard)"),
        target_group=None,
        side="opponent",
        zone_from="deck",
        zone_to="gy",
    ),
    VerbRule("negate", _rx(r"\bnegate (?:the activation|the effect|its effects?|the summon|the attack)"), target_group=None),
    VerbRule("negate", _rx(r"\bnegate\b"), target_group=None),
    # ── costs ───────────────────────────────────────────────────────────────
    # `discards?`: only the imperative matched, so "your opponent **discards** 1
    # random card" (Delinquent Duo) produced no clause at all and half the card
    # went unscored.
    VerbRule("discard", _rx(rf"\bdiscards? {_T}{_STOP}"), zone_from="hand", zone_to="gy"),
    VerbRule("tribute", _rx(rf"\bTribute {_T}{_STOP}"), zone_from="field", zone_to="gy"),
    VerbRule(
        "send",
        _rx(rf"\bsend {_T} from (?:your|the) ({_ZONE_ALT}) to the (?:GY|Graveyard)"),
        zone_to="gy", zone_group=2,
    ),
    VerbRule("pay_lp", _rx(rf"\bpay ([\d,]+) (?:LP|Life Points)"), target_group=None),
    # "Pay half your LP" -- see HALF_LP and the note in the extractor.
    VerbRule("pay_lp", _rx(r"\bpay (half) your (?:LP|Life Points)"), target_group=None),
    # ── numbers, not cards ──────────────────────────────────────────────────
    VerbRule("damage", _rx(rf"\binflict ([\d,]+) damage"), target_group=None),
    VerbRule("gain_lp", _rx(rf"\bgain ([\d,]+) (?:LP|Life Points)"), target_group=None),
    VerbRule("equip", _rx(rf"\bequip {_T}{_STOP}")),
    VerbRule("set", _rx(rf"\bSet {_T}{_STOP}")),
    # ── continuous / static effects ─────────────────────────────────────────
    # These move no cards, so they contribute nothing to economy — but they are
    # most of what a monster's text says, and a card whose text yields no clause
    # at all is indistinguishable from an unparsed one in the coverage report.
    VerbRule("stat_gain", _rx(r"\bgains? ([\d,]+|X) (?:ATK|DEF)"), target_group=None),
    VerbRule("stat_loss", _rx(r"\bloses? ([\d,]+|X) (?:ATK|DEF)"), target_group=None),
    VerbRule("cannot_destroy", _rx(r"\bcannot be destroyed\b"), target_group=None),
    VerbRule("cannot_target", _rx(r"\bcannot be targeted\b"), target_group=None),
    VerbRule("cannot_attack", _rx(r"\bcannot attack\b"), target_group=None),
    VerbRule("cannot_summon", _rx(r"\bcannot be (?:Normal |Special )?Summoned\b"), target_group=None),
    VerbRule("cannot_activate", _rx(r"\bcannot activate\b"), target_group=None),
    VerbRule("unaffected", _rx(r"\bunaffected by\b"), target_group=None),
    VerbRule("piercing", _rx(r"\bpiercing battle damage\b"), target_group=None),
    VerbRule("direct_attack", _rx(r"\bcan attack (?:your opponent )?directly\b"), target_group=None),
    VerbRule("double_attack", _rx(r"\bcan attack twice\b"), target_group=None),
    VerbRule("take_control", _rx(rf"\btake control of {_T}{_STOP}")),
    VerbRule("change_position", _rx(r"\bchange .{0,60}? to (?:face-up )?(?:Attack|Defense) Position"), target_group=None),
    VerbRule("flip", _rx(r"\bflip .{0,40}? face-(?:up|down)"), target_group=None),
    VerbRule("treated_as", _rx(r"\bis (?:also )?treated as\b"), target_group=None),
    VerbRule("reveal", _rx(rf"\breveal {_T}{_STOP}")),
    VerbRule("target", _rx(rf"\bTarget {_T}{_STOP}")),
    # "Activate this card by TARGETING 1 monster in your GY" — the gerund is how
    # continuous revival is templated, and only the imperative was matched.  So
    # Call of the Haunted raised no target at all, "Special Summon that target"
    # had nothing to bind to, and it fell back to `ss_unspecified` (0.35) instead
    # of `ss_from_gy` (1.00) — the single most-played card in the corpus scoring
    # a flat 0.00.
    VerbRule("target", _rx(rf"\btargeting {_T}{_STOP}")),
    # "Select 1 X" / "Choose 1 X" is the 2005-2010 wording for "Target 1 X", and
    # it is what most cards in this ROM actually say.  Without it, Rain Storm's
    # "Select 1 'Cloudian' monster you control" produced no clause at all, the
    # Cloudian requirement vanished, and the card scored as free removal in a
    # deck containing no Cloudians whatsoever.
    VerbRule("target", _rx(rf"\bSelect {_T}{_STOP}")),
    VerbRule("target", _rx(rf"\bChoose {_T}{_STOP}")),
    # Material lines: "1 Tuner + 1 or more non-Tuner monsters", or the older
    # named form '"Cyber Dragon" + "Cyber Dragon" + "Cyber Dragon"'.
    VerbRule("material", _rx(r"^\s*\d+ [^+\n]{0,60}\+ [^\n]{0,80}$"), target_group=None),
    VerbRule("material", _rx(r"^\s*\"[^\"]{2,60}\" \+ "), target_group=None),
    VerbRule(
        "tribute_requirement",
        _rx(r"\bRequires? (\d+) Tributes? to Normal Summon"),
        target_group=None,
    ),
    VerbRule(
        "prevent_damage",
        # The window was 30 characters, which is shorter than the sentence
        # actually is: The Sanctuary in the Sky reads "Battle damage to the
        # controller of a Fairy monster from a battle involving that monster
        # becomes 0" — ~60 characters — so it produced no clause at all.  It is
        # a Waboku-style damage shield and the Fairy/Agent decks' Field Spell.
        _rx(r"\byou take no battle damage\b|\bbattle damage .{0,80}?becomes 0\b"
            r"|\btake no battle damage\b"),
        target_group=None,
    ),
    # ── restrictions and timing, in the older pre-PSCT wordings the ROM era
    #    is full of.  These move no cards but they are most of what is left.
    # Summoning conditions state a DECK requirement, not just a restriction:
    # Chaos Sorcerer needs LIGHT and DARK monsters in the GY, Dark Armed Dragon
    # needs three DARKs.  The gerund forms matched no rule at all, so these cards
    # produced zero wants and the search built "Chaos" decks out of cards sharing
    # a word instead of the LIGHT/DARK engine the text actually asks for.
    #
    # Capture deliberately runs past "and" so "1 LIGHT and 1 DARK monster" yields
    # both attributes.  The predicate then reads as LIGHT-or-DARK rather than
    # LIGHT-and-DARK, which understates it, but a deck satisfying either is far
    # closer than one satisfying neither.
    VerbRule(
        "summon_cost",
        _rx(r"by banishing (.{0,80}?) from your (?:GY|Graveyard)"),
        zone_from="gy",
    ),
    VerbRule(
        "summon_cost",
        _rx(r"by having (?:exactly )?(.{0,80}?) in your (?:GY|Graveyard)"),
        zone_from="gy",
    ),
    VerbRule("summon_cost", _rx(rf"by Tributing {_T}{_STOP}"), zone_from="field"),
    VerbRule("summon_cost", _rx(rf"by sending {_T}{_STOP}"), zone_from="deck"),
    VerbRule(
        "nomi",
        _rx(r"\bmust (?:first )?be Special Summoned\b|\bcannot be Normal Summoned\b"),
        target_group=None,
    ),
    VerbRule(
        "frequency_limit",
        _rx(
            r"\byou can only (?:activate|use|control|Special Summon)\b|"
            r"\bthere can only be\b|\bthis (?:card|effect) can only\b|"
            r"\bcan only be (?:used|activated)\b"
        ),
        target_group=None,
    ),
    VerbRule("once_per_turn", _rx(r"\bonce per turn\b"), target_group=None),
    # An activation requirement naming cards you must control is a *deck*
    # requirement, so it has to carry a predicate.  Parsed as a bare tag,
    # "Activate only while you control an 'Alien' monster" looked free, and the
    # search happily played Mass Hypnosis in a deck with no Aliens at all.
    VerbRule(
        "requires_control",
        _rx(rf"\bActivate only while you control {_T}{_STOP}"),
    ),
    VerbRule("requires_control", _rx(rf"\bwhile you control {_T}{_STOP}")),
    # "If the ONLY monster you control is X" is a stricter requirement than
    # "if you control X", and it matched neither pattern.  Worm Yagan revives
    # itself only while Worm Xex is your sole monster; unparsed, it was credited
    # a free +0.95 revival in a deck holding no Worm Xex at all.
    VerbRule(
        "requires_control",
        _rx(rf"\bthe only (?:monster|card)s? you control (?:is|are) {_T}{_STOP}"),
    ),
    VerbRule("requires_control", _rx(rf"\byou control no {_T}{_STOP}")),
    VerbRule("requires_control", _rx(rf"\bif you control {_T}{_STOP}")),
    VerbRule("requires_control", _rx(rf"\byou must control {_T}{_STOP}")),
    VerbRule(
        "named_card_trigger",
        _rx('when your opponent activates "[^"]{2,40}"'),
        target_group=None,
    ),
    VerbRule(
        "activation_condition",
        _rx(r"\bactivate only (?:when|while|if|during)\b|\bcan be activated only\b"),
        target_group=None,
    ),
    VerbRule(
        "battle_trigger",
        _rx(
            r"\bif this card attacks\b|\bwhen this card destroys\b|"
            r"\bduring battle between\b|\bwhen this card is attacked\b|"
            r"\bat the end of the Battle Phase\b"
        ),
        target_group=None,
    ),
    VerbRule(
        "summon_trigger",
        _rx(r"\bwhen this card is (?:Normal |Special |Flip )?Summoned\b"),
        target_group=None,
    ),
    VerbRule(
        "leave_trigger",
        _rx(
            r"\bwhen this card is (?:destroyed|sent to the (?:GY|Graveyard)|removed from the field)\b"
        ),
        target_group=None,
    ),
    # ── triggers that NAME the card the effect then acts on ─────────────────
    #
    # The trigger rules above all take `target_group=None`, so they carry no
    # predicate and cannot be an antecedent.  That is why "When your opponent
    # Summons 1 monster with 1000 or more ATK: Target that monster; destroy that
    # target" resolved nothing: Trap Hole's payoff was dropped as a self-
    # reference and it scored a flat -1.00.  Same shape for every "if this card
    # battles X: destroy that monster" Synchro (Catastor, D.D. Warrior Lady).
    #
    # These fire ALONGSIDE the tag rules above — different verb, so the dedup by
    # (verb, offset) does not suppress either — and land as `condition` kind via
    # REQUIREMENT_ONLY, so they are antecedents for resolve_pronouns and
    # contribute no economy of their own.  side is forced: whatever this card
    # battles, and whatever the opponent Summons, is theirs by definition.
    VerbRule(
        "trigger_object",
        _rx(rf"\bwhen your opponent (?:Normal |Flip |Special |or )*Summons? {_T}{_STOP}"),
        side="opponent",
    ),
    VerbRule(
        "trigger_object",
        _rx(rf"\b(?:when|if) this card battles {_T}{_STOP}"),
        side="opponent",
    ),
    VerbRule(
        "trigger_object",
        _rx(rf"\bwhen this card destroys {_T} by battle"),
        side="opponent",
    ),
    VerbRule(
        "continuous_condition",
        _rx(r"\bwhile this card is\b|\bas long as this card\b|\bwhile you control\b"),
        target_group=None,
    ),
    VerbRule(
        "stat_gain",
        _rx(r"\bgains? (?:ATK|DEF) equal to\b|\bATK (?:is|becomes) (?:equal to|doubled)\b"),
        target_group=None,
    ),
    VerbRule(
        "damage",
        _rx(r"\binflict ([\d,]+) damage to your opponent"),
        target_group=None,
    ),
    VerbRule(
        "damage",
        _rx(r"\binflict damage to (?:your opponent|both players)\b"),
        target_group=None,
    ),
    VerbRule(
        "gain_lp",
        _rx(r"\bincrease your Life Points by ([\d,]+)"),
        target_group=None,
    ),
    VerbRule(
        "lose_lp",
        _rx(r"\bdecrease your Life Points by ([\d,]+)|\bhalve your Life Points\b"),
        target_group=None,
    ),
    VerbRule(
        "attack_restriction",
        _rx(r"\bcannot conduct your Battle Phase\b|\bcannot declare an attack\b"),
        target_group=None,
    ),
    VerbRule(
        "fusion_requirement",
        _rx(r"\bA Fusion Summon of this card\b|\bmust be Fusion Summoned\b"),
        target_group=None,
    ),
    VerbRule(
        "spell_trap_trigger",
        _rx(r"\beach time a (?:Spell|Trap|monster)\b|\bwhen a (?:Spell|Trap) Card is activated\b"),
        target_group=None,
    ),
    VerbRule(
        "standby_trigger",
        _rx(r"\bduring each of your (?:Standby|End|Draw) Phases\b"),
        target_group=None,
    ),
)

#: What "pay half your LP" costs, in life points.
#:
#: Half of the 8,000 starting total.  It is an upper bound rather than an
#: average — you are often below 8,000 when you pay — but these cards are
#: strongest early, when the total is highest, and picking the payment you would
#: actually make at full LP keeps the number derived rather than invented.
HALF_LP = 4000

#: Verbs whose numeric group is a count of cards rather than a target phrase.
_NUMERIC_VERBS = {"draw", "mill"}
#: Verbs whose numeric group is life points / damage.
_LP_VERBS = {"pay_lp", "damage", "gain_lp"}
#: Verbs that change the board without moving a card — no economy contribution.
STATIC_VERBS = frozenset(
    {
        "stat_gain", "stat_loss", "cannot_destroy", "cannot_target", "cannot_attack",
        "cannot_summon", "cannot_activate", "unaffected", "piercing",
        "direct_attack", "double_attack", "change_position", "flip", "treated_as",
        "material", "nomi", "frequency_limit", "once_per_turn", "requires_control",
        "summon_cost",
        "activation_condition", "battle_trigger", "summon_trigger", "named_card_trigger",
        "leave_trigger", "continuous_condition", "attack_restriction",
        "fusion_requirement", "spell_trap_trigger", "standby_trigger",
        "prevent_damage", "tribute_requirement",
    }
)
#: Verbs that state a requirement rather than an effect.
REQUIREMENT_ONLY = frozenset({"target", "reveal", "trigger_object"})

_OPPONENT = re.compile(r"\byour opponent(?:'s)?\b|\bopponent controls\b", re.I)
#: An explicit possessive settles ownership outright and must beat the
#: both-sides heuristic.  "banish 2 LIGHT monsters from your Graveyard" is
#: unambiguously a cost, but the rest of Freed the Brave Wanderer's sentence says
#: "on the field", so the heuristic fired and scored its cost as +2.2 of removal
#: against the opponent -- turning a fair card into the pool's best trap.
_EXPLICIT_YOURS = re.compile(
    r"\bfrom your (?:Graveyard|GY|hand|Deck|field|Extra Deck)\b|\byou control\b", re.I
)
#: "make your opponent Tribute 1 monster" — the opponent pays, so it is a gain.
_OPPONENT_CAUSED = re.compile(r"(?:makes?|have|has) your opponent\s*$", re.I)

#: A trigger fired by something the opponent did.  The card that answers such a
#: trigger acts on the opponent's card even though the effect clause never says
#: so: Bottomless Trap Hole reads "When your opponent Summons a monster with 1500
#: or more ATK: Destroy that monster".  Reading that destroy as hitting *our*
#: side made the format's second-most-played trap score -1.00, i.e. a dead card.
_OPPONENT_TRIGGER = re.compile(
    # "When your opponent…", "When an opponent's monster declares an attack…"
    r"\b(?:when|if|while)\s+(?:an?\s+|the\s+)?(?:your\s+)?opponent(?:'s)?\b"
    r"|\byour opponent (?:Normal |Special |Flip )?Summons\b"
    r"|\byour opponent activates\b"
    r"|\bopponent(?:'s)? monster declares an attack\b"
    r"|\bmonster your opponent controls (?:declares|attacks)\b"
    r"|\bis attacked by\b",
    re.I,
)
#: Verbs where the "whose card is it" question changes the sign of the term.
#: ``target`` is included so the side propagates to the pronoun that follows it:
#: "When an opponent's monster declares an attack: Target the attacking monster;
#: banish it" resolves "it" from the target clause, so if the target is marked as
#: ours the banish is charged as a cost and Dimensional Prison reads as -1.00.
_SIDE_SENSITIVE = frozenset(
    # `discard` belongs here: whose hand empties is the entire sign of the
    # clause.  Without it, Delinquent Duo and Confiscation — 340 and 362 of the
    # corpus's 1,201 decks — billed the OPPONENT's discard as our own cost and
    # came out at -2.20 cards apiece.
    {"destroy", "banish", "bounce", "shuffle", "negate", "take_control", "target",
     "discard"}
)

#: Sentence-level signal that the OPPONENT'S HAND is what is being operated on.
#: Distinct from _OPPONENT_TRIGGER, which is trigger-shaped ("when your
#: opponent…") and so never fired for the hand-disruption family: Confiscation
#: opens "Look at your opponent's hand", which is a statement, not a trigger.
_OPPONENT_HAND = re.compile(
    r"\byour opponent'?s? hand\b|\byour opponent discards?\b"
    r"|\blook at your opponent'?s\b|\bfrom their hand\b|\bhis/her\b",
    re.I,
)

#: "destroy this face-up card" is a drawback, not removal.  Playful Possum
#: destroys itself; read as hitting the opponent it scored +1.90, and no
#: tournament deck in the corpus has ever played it.
_SELF_TARGET = re.compile(r"\bthis (?:face-up )?card\b|\bthis monster\b", re.I)
#: A target phrase that BEGINS with a self-reference and then runs on into an
#: infinitive of purpose: "this card to destroy 1 monster your opponent
#: controls".  The capture cannot stop at a bare " to " without truncating real
#: target phrases (measured: -85 wants, -0.006 Spearman), so the run-on is
#: trimmed here instead.  Left whole, the phrase is not a SELF_WORD, so the
#: clause loses `self_ref`, keeps a bogus predicate, and `_side_of` reads the
#: trailing "your opponent" and hands the COST to them as a gain.
_LEADING_SELF = re.compile(r"^(this (?:face-up )?card|this monster)\s+to\s+\S", re.I)
_BOTH = re.compile(r"\ball monsters on the field\b|\bboth players\b|\bon the field\b", re.I)
_TEMPORARY = re.compile(
    r"during the End Phase|until the End Phase|at the end of (?:the|this) turn|"
    r"return(?:ed)? .{0,30}during the End Phase",
    re.I,
)
_ONCE = re.compile(r"\bonce per turn\b", re.I)
_HARD_ONCE = re.compile(r"you can only use (?:this|1) effect", re.I)


#: Where a clause's own scope ends, for the purpose of reading which side it hits.
_CLAUSE_BREAK = re.compile(r"[,;.]|\bthen\b|\band then\b", re.I)


def _forward_window(text: str, start: int, limit: int = 90) -> str:
    """Text from *start* up to the next clause boundary (at most *limit* chars)."""
    window = text[start : start + limit]
    # Skip a break that sits inside the verb phrase itself ("Destroy all Spell
    # and Trap Cards your opponent controls" has no break; "Discard 1 card, then
    # …" breaks at the comma).
    m = _CLAUSE_BREAK.search(window, 8)
    return window[: m.start()] if m else window


def _side_of(text: str, pred: Predicate | None) -> str:
    if _EXPLICIT_YOURS.search(text) and not _OPPONENT.search(text):
        return "you"
    if pred is not None:
        if "opponent_controls" in pred.board:
            return "opponent"
        if "you_control" in pred.board or "your_gy" in pred.board:
            return "you"
    if _OPPONENT.search(text):
        return "opponent"
    if _BOTH.search(text):
        return "both"
    return "you"


def extract(seg: Segment, *, known_names: frozenset[str] | None = None) -> list[Clause]:
    """Pull every clause out of one segment."""
    text = seg.text
    if not text:
        return []

    kind = {"cost": "cost", "condition": "condition", "requirement": "condition"}.get(
        seg.role, "gain"
    )
    temporary = bool(_TEMPORARY.search(seg.sentence))
    frequency = (
        "hard_opt" if _HARD_ONCE.search(seg.sentence)
        else "once_per_turn" if _ONCE.search(seg.sentence)
        else None
    )

    # (match offset, insertion order, clause).  Clauses come out of the rule loop
    # in RULES order, which is priority order and has nothing to do with where
    # the words sit in the sentence — so `resolve_pronouns`, which scans forward
    # looking for an antecedent, could meet the pronoun first and give up.
    # Confiscation is the case: "select 1 card in it and discard that card"
    # emitted the discard BEFORE the target, so "that card" never bound and one
    # of the corpus's most-played cards scored its cost and none of its payoff.
    # The insertion index breaks ties so equal offsets keep rule priority.
    out: list[tuple[int, int, Clause]] = []
    seen: set[tuple[str, int]] = set()
    for rule in RULES:
        for m in rule.pattern.finditer(text):
            if (rule.verb, m.start()) in seen:
                continue
            # A later, looser rule for the same verb must not re-fire on text an
            # earlier rule already consumed.
            if any(v == rule.verb and abs(s - m.start()) < 4 for v, s in seen):
                continue
            seen.add((rule.verb, m.start()))

            pred: Predicate | None = None
            count = Count("fixed", 1)
            confidence = 1.0

            # Some wordings state no number at all ("inflict damage equal to…",
            # "halve your Life Points"), so the numeric group may be absent.
            digits = None
            if rule.target_group is None and rule.pattern.groups:
                raw = (m.group(1) or "").replace(",", "")
                digits = int(raw) if raw.isdigit() else None
                # "Pay half your LP" states a fraction, not a number, so the
                # digits-only rule matched nothing and eight cards paid their
                # cost for FREE -- Solemn Judgment, Return from the Different
                # Dimension, A Hero Lives, Gandora.  Solemn Judgment read as an
                # exact 0.00 one-for-one because that missing cost happened to
                # cancel an underpriced negate+destroy.
                if digits is None and raw.lower() == "half":
                    digits = HALF_LP

            if rule.verb in _NUMERIC_VERBS:
                count = Count("fixed", digits if digits is not None else 1)
            elif rule.verb in _LP_VERBS or rule.verb in ("stat_gain", "stat_loss", "lose_lp"):
                count = (
                    Count("fixed", digits) if digits is not None else Count("variable")
                )
            elif rule.target_group is not None:
                phrase = m.group(rule.target_group) or ""
                # "this card to destroy 1 monster your opponent controls" — trim
                # the infinitive of purpose so the phrase is recognisably a
                # self-reference.  See _LEADING_SELF.
                lead = _LEADING_SELF.match(phrase.strip())
                if lead:
                    phrase = lead.group(1)
                pred, count, residue = parse_predicate(phrase, known_names=known_names)
                if pred is None and not phrase.strip():
                    continue
                confidence = pred.confidence if pred else 0.9

            zone_from = rule.zone_from
            if rule.zone_group is not None:
                zone_from = ZONES.get((m.group(rule.zone_group) or "").lower(), zone_from)

            # Look just behind the match for "make your opponent <verb>" — the
            # window is deliberately tiny, so "destroy 1 monster your opponent
            # controls and draw 1 card" does not make the draw the opponent's.
            before = text[: m.start()]
            if _OPPONENT_CAUSED.search(before[-32:]):
                side = "opponent"
            elif rule.side != "auto":
                side = rule.side
            else:
                # Look forward from the verb, not just at the matched span: the
                # phrase naming the side ("on the field", "your opponent
                # controls") usually sits just past where capture ends.  Clip at
                # the next clause boundary, or "Discard 1 card, then target 1
                # monster your opponent controls" would make the discard theirs.
                side = _side_of(_forward_window(text, m.start()), pred)
                # The effect clause often omits whose card it is, leaving it to
                # the trigger in the same sentence.  Only applied when the clause
                # itself gave no signal ("you control" in the predicate always
                # wins) and only for verbs where the side flips the sign.
                if (
                    side == "you"
                    and rule.verb in _SIDE_SENSITIVE
                    and not (pred and pred.board & {"you_control", "your_gy"})
                    # An explicit "from your GY" / "this face-up card" outranks
                    # the sentence's trigger.  Insect Neglect banishes from YOUR
                    # graveyard and Playful Possum destroys ITSELF, but both sit
                    # in opponent-triggered sentences, so the fallback flipped
                    # their costs into +1.0 removal against the opponent.
                    and not _EXPLICIT_YOURS.search(m.group(0))
                    and not _SELF_TARGET.search(m.group(0))
                    and (
                        _OPPONENT_TRIGGER.search(seg.sentence)
                        or _OPPONENT_HAND.search(seg.sentence)
                    )
                ):
                    side = "opponent"

            # A clause whose own target is "this card" acts on YOUR card, and no
            # amount of opponent-talk later in the sentence changes that.
            # `_side_of` reads a forward window, so "Tribute this card to destroy
            # 1 monster your opponent controls" handed the TRIBUTE to the
            # opponent — turning a self-tribute cost into +0.95 of
            # `gain.opp_tribute`, and Turbo Booster into +2.04 economy on a card
            # two decks in the corpus play.
            if pred is None and rule.target_group is not None and side == "opponent":
                side = "you"

            # "on the field" reads as both sides, but when the effect picks a
            # single card *you* choose, so it is the opponent's.  Only untargeted
            # mass removal ("destroy all monsters") is genuinely symmetric.
            #
            # Unless the card names itself or your own zone: "destroy this
            # face-up card on the field" is Playful Possum's drawback, and
            # coercing it to the opponent's side turned that drawback into +1.90
            # of removal on a card no tournament deck plays.
            if (
                side == "both"
                and count.kind != "all"
                and not _SELF_TARGET.search(m.group(0))
                and not _EXPLICIT_YOURS.search(m.group(0))
            ):
                side = "opponent"

            if rule.verb in STATIC_VERBS:
                eff_kind = "tag"
            elif rule.verb in REQUIREMENT_ONLY:
                eff_kind = "condition"
            else:
                eff_kind = kind
                # A cost verb that the *opponent* pays is a gain for us.
                if kind == "cost" and side == "opponent":
                    eff_kind = "gain"
                elif kind == "gain" and side == "you" and rule.verb in (
                    "discard", "tribute", "pay_lp"
                ):
                    eff_kind = "cost"

            out.append((m.start(), len(out), Clause(
                    kind=eff_kind,
                    verb=rule.verb,
                    count=count,
                    zone_from=zone_from,
                    zone_to=rule.zone_to,
                    side=side,
                    predicate=pred,
                    self_ref=pred is None and rule.target_group is not None,
                    timing=seg.role if seg.role == "condition" else None,
                    frequency=frequency,
                    optional=seg.optional,
                    temporary=temporary,
                    confidence=confidence,
                    raw=m.group(0).strip(),
                    mode=seg.mode,
                )
            ))
    out.sort(key=lambda t: (t[0], t[1]))
    return [c for _, _, c in out]
