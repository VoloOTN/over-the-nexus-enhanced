"""Behavioural tags read off the Yu-Gi-Oh! Fandom wiki's curated categories.

``text.parse.derive_tags`` reconstructs "what does this card do" from regexes
over the card text.  The wiki already carries that answer, hand-curated, in each
card page's ``cardtable-categories`` block — "Negates attacks", "Special Summons
itself from your hand", "Does not require specific Synchro Materials".
``wiki_categories.py`` scrapes it; this module turns it into the tag vocabulary
the model already reasons over.

**The wiki wins where it speaks.**  Every tag in :data:`AUTHORITATIVE` is taken
from the wiki and the derived regex for it is discarded — the regex was an
approximation of exactly this list.  Tags *not* in that set have no wiki
counterpart (``opponent_turn``, ``mass_removal``, ``needs_self_copies``) or are
deliberately kept because in-game behaviour, not text, defines them
(``summon_locked``); those stay derived.  See :data:`DERIVED_ONLY` for the
reasons.

Three things about the wiki's vocabulary that the mapping depends on, all
checked against samples rather than assumed:

* **Side is encoded in the wording.**  ``your`` / ``the player's`` means the
  card's *controller* — "Prevents the player's Normal Summons" is Scapegoat and
  Stray Lambs, a **drawback**.  ``your opponent's`` means the opponent, and a
  bare "Prevents Special Summons" means both (Vanity's Emptiness, Jowgen).  So
  "Prevents your monsters from attacking" is Instant Fusion, not a floodgate.
* **A category is a fact, not a value judgement.**  "Destroys your Monster
  Cards" is a cost; "Destroys your opponent's Monster Cards" is removal.  They
  are never collapsed here.
* **An empty category block is a real answer.**  A Normal Monster has no effect,
  so its page carries no block at all — 77 of the pool.  That is *no tags*, not
  *unknown*, which is why :func:`tags_for` distinguishes "cid absent from the
  scrape" (fall back to the regexes) from "cid present with nothing to say".
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from otn_enhanced.deckgen.model import Card

from otn_enhanced.deckgen import resources as _res

#: Via resources so the path follows a PyInstaller bundle when frozen.
CACHE = _res.wiki_categories()

#: ``(group, matcher, tags)``.  A matcher starting with ``~`` is a regex
#: **searched** in the value (anchor it with ``^``/``$`` when the whole value
#: must match); anything else is compared literally.  A card gets every tag whose
#: rule matches any value it carries in that group.
#:
#: Ordered by group so the table reads next to the scrape dump.
_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    # ── Actions ─────────────────────────────────────────────────────────────
    ("Actions", "Adds from Deck to hand", ("searcher",)),
    ("Actions", "Adds from Graveyard to hand", ("recursion",)),
    ("Actions", "Returns from your Graveyard to your hand", ("recursion",)),
    ("Actions", "Returns itself from Graveyard to hand", ("recursion", "gy_payoff")),
    ("Actions", "You draw cards", ("draw",)),
    ("Actions", "Replaces normal draw", ("draw",)),
    ("Actions", "Activates from your Graveyard", ("gy_payoff",)),
    ("Actions", "Activates while banished", ("banish_payoff",)),
    ("Actions", "Returns itself to the field while banished", ("banish_payoff",)),
    ("Actions", "Adds banished cards to the hand", ("banish_payoff",)),
    ("Actions", "Returns banished cards to the field", ("banish_payoff",)),
    ("Actions", "~^Returns the player's banished cards", ("banish_payoff",)),
    # Getting a card out of YOUR hand and into the Graveyard is the outlet a Dark
    # World / Lightsworn deck is built around.  Cost or effect makes no
    # difference to the payoff card — golden.toml asserts Card Destruction, whose
    # only discard categories are "You discard" and "Discards for effect".
    ("Actions", "~^Discards( itself)? for [Cc]ost$", ("discard_outlet",)),
    ("Actions", "You discard", ("discard_outlet",)),
    ("Actions", "~^Discards for [Ee]ffect$", ("discard_outlet",)),
    ("Actions", "~^Sends( itself)? from (your )?hand to (your )?Graveyard$",
     ("discard_outlet",)),
    ("Actions", "~^Sends( itself)? from (your )?hand to (your )?Graveyard for cost$",
     ("discard_outlet",)),
    ("Actions", "~^Sends from your hand to your Graveyard for cost$", ("discard_outlet",)),
    ("Actions", "Your opponent discards", ("hand_disruption",)),
    ("Actions", "~^Sends from your opponent's hand to your opponent's Graveyard",
     ("hand_disruption",)),
    ("Actions", "~^Discards from your opponent's hand", ("hand_disruption",)),
    ("Actions", "Changes control", ("control_theft",)),
    ("Actions", "Takes control of equipped", ("control_theft",)),
    ("Actions", "Changes battle positions", ("tempo",)),
    ("Actions", "~^Flips monsters face-(up|down)$", ("tempo",)),
    ("Actions", "Flips monsters face-down", ("flip_enabler",)),
    ("Actions", "Flips itself face-down", ("flip_enabler",)),
    ("Actions", "Activates upon being flipped face-up", ("flip_effect",)),
    # Combat.  An effect that fires FROM the Battle Phase is paid for by
    # attacking, which the deck was doing anyway.
    ("Actions", "Activates when it destroys a monster by battle", ("battle_payoff",)),
    ("Actions", "Activates when it inflicts battle damage", ("battle_payoff",)),
    ("Actions", "Activates if destroyed by battle", ("battle_payoff",)),
    ("Actions", "Activates if you take battle damage", ("battle_payoff",)),
    # NOT `battle_payoff` and NOT `combat_trick`.  Measured: this category and
    # the regex `combat_trick` agree on **zero** cards.  They are different
    # facts — this is Mirror Force and Dimensional Prison (a card that answers an
    # attack), while `combat_trick` is Honest and Kalut (a card in hand that wins
    # the combat), and Honest's page carries no attack category at all.
    ("Actions", "Activates upon attack declaration", ("attack_trigger",)),
    ("Actions", "Returns battling monster to hand after damage calculation",
     ("battle_removal",)),
    ("Actions", "~^Tributes( itself)? for cost$", ("tribute_cost",)),
    ("Actions", "Tributes as an effect", ("tribute_cost",)),
    ("Actions", "Tributes opponent's monsters", ("spot_removal",)),
    # Loading YOUR OWN Graveyard is setup, not loss — it is why Foolish Burial is
    # a staple.  The opponent's deck is the deckout axis instead.
    ("Actions", "~^Sends from (the top of )?your Deck to your Graveyard",
     ("gy_setup", "gy_filler")),
    ("Actions", "~^Sends from Deck to Graveyard", ("gy_setup", "gy_filler")),
    ("Actions", "~^Sends from (the top of )?your opponent's Deck to your opponent's "
                "Graveyard", ("deckout",)),
    ("Actions", "Returns to the Deck cards that would be sent to the Graveyard",
     ("gy_denial",)),
    ("Actions", "~^Returns from your opponent's field to your opponent's "
                "(hand|Deck|Extra Deck)$", ("spot_removal",)),
    ("Actions", "~^Equips (self|monsters) from", ("equip_effect",)),
    ("Actions", "Moves Equip Cards", ("equip_effect",)),
    ("Actions", "Activates when it leaves the field", ("leave_payoff",)),
    ("Actions", "Activates if destroyed by card effect", ("leave_payoff",)),
    ("Actions", "Activates if destroyed while Set", ("leave_payoff",)),
    ("Actions", "Activates if Tributed", ("leave_payoff",)),
    ("Actions", "Activates if returned from the field to the hand", ("leave_payoff",)),
    ("Actions", "~^Activates upon (Normal|Special|Flip|Tribute|Synchro|Fusion|Ritual) "
                "Summon$", ("summon_payoff",)),
    ("Actions", "Activates if used as Synchro Material", ("summon_payoff",)),
    ("Actions", "Applies effect when used as Synchro Material", ("summon_payoff",)),
    ("Actions", "~^Reveals your opponent's (hand|Deck)$", ("information",)),
    ("Actions", "Reveals face-down cards", ("information",)),
    ("Actions", "~^Looks at cards from the top of", ("information",)),
    ("Actions", "Cannot conduct Battle Phase", ("attack_lock",)),
    # Floodgates whose category lives under Actions rather than Summoning.
    # Thunder King Rai-Oh is the one that matters: without this rule the wiki
    # would call the format's premier hate body a plain beater.
    ("Actions", "Prevents adding cards from Deck to hand", ("floodgate",)),
    ("Actions", "~^Prevents (Battle|battle) [Pp]osition changes$", ("floodgate",)),
    ("Actions", "Prevents returning cards from field to Deck", ("floodgate",)),
    ("Banished categories", "Prevents cards from being banished", ("floodgate",)),
    ("Monster/Spell/Trap categories", "Prevents cards from being discarded",
     ("floodgate",)),
    ("Actions", "Prevents the opponent's Tributes", ("floodgate",)),
    ("Actions", "Prevents your opponent's Sets", ("floodgate",)),
    ("Actions", "~^Uses cards .* as Fusion Materials$", ("fusion_payoff",)),
    ("Actions", "Returns Fusion Materials for Contact Fusion to Deck", ("fusion_payoff",)),
    ("Actions", "~Deck order$", ("deck_stack",)),
    ("Actions", "~^Places cards from .* on the (top|bottom) of the Deck", ("deck_stack",)),
    ("Actions", "~^Excavates from", ("deck_stack",)),

    # ── Summoning categories ────────────────────────────────────────────────
    # A body that arrives WITHOUT the Normal Summon.  The wiki states this
    # directly; the regex it replaces guessed at it from "can be Special
    # Summoned", which also fires on cards that summon something else.
    ("Summoning categories", "~^Special Summons itself", ("free_body", "self_ss")),
    ("Summoning categories", "Special Summons copies of itself", ("free_body",)),
    ("Summoning categories", "Normal Summon without Tribute", ("free_body",)),
    ("Summoning categories", "~^Special Summons itself from your Graveyard",
     ("recursion", "gy_payoff")),
    ("Summoning categories", "Special Summons itself from your Banished Zone",
     ("banish_payoff",)),
    ("Summoning categories", "~^Special Summons (from|excavated|(its )?Materials)",
     ("summoner",)),
    ("Summoning categories", "~^Special Summons (the player's|the opponent's) banished",
     ("summoner", "banish_payoff")),
    ("Summoning categories", "~^Special Summons from your( opponent's)? Graveyard",
     ("recursion",)),
    ("Summoning categories", "~^Special Summons Tokens", ("token_maker", "summoner")),
    ("Summoning categories", "Nomi", ("nomi",)),
    ("Summoning categories", "Semi-Nomi", ("nomi",)),
    ("Summoning categories", "Cannot be Normal Summoned", ("nomi",)),
    ("Summoning categories", "Special Summon-only monster", ("nomi",)),
    ("Summoning categories", "Performs a Fusion Summon", ("fusion_payoff",)),
    ("Summoning categories", "Strict fusion-performing card", ("fusion_payoff",)),
    ("Summoning categories", "Fusion Summons specific Fusion Monster", ("fusion_payoff",)),
    ("Summoning categories", "Contact Fusion", ("fusion_payoff",)),
    ("Summoning categories", "~^Negates (Special|Normal|Flip) Summons$",
     ("negate", "summon_answer")),
    # Floodgates: opponent-directed or symmetric.  "the player's" is the
    # controller and is a drawback — see the module docstring.
    ("Summoning categories", "~^Prevents your opponent's", ("floodgate",)),
    ("Summoning categories",
     "~^Prevents (Special|Normal|Flip|Tribute|Fusion|Synchro) Summons$", ("floodgate",)),
    ("Summoning categories", "Prevents Tributes", ("floodgate",)),
    ("Summoning categories", "Prevents the opponent's Tributes", ("floodgate",)),
    ("Summoning categories", "Prevents the opponent placing cards on the field",
     ("floodgate",)),
    ("Summoning categories", "Prevents activations upon Summon", ("floodgate",)),
    # The exact fact `power.w_extra_generic` was built to infer.
    ("Summoning categories", "Does not require specific Synchro Materials",
     ("generic_material",)),
    ("Summoning categories", "Does not require specific non-Tuner Synchro Materials",
     ("generic_nontuner",)),
    ("Summoning categories", "Does not require specific Tuner Synchro Materials",
     ("generic_tuner",)),
    ("Summoning categories", "Allows multiple Normal Summons", ("extra_normal_summon",)),

    # ── Monster/Spell/Trap categories ───────────────────────────────────────
    ("Monster/Spell/Trap categories", "~^Destroys your opponent's", ("spot_removal",)),
    ("Monster/Spell/Trap categories",
     "~^Destroys (face-up |face-down |Defense Position |Attack Position |negated |"
     "Special Summoned |Normal Summoned |Flip Summoned )*"
     "(Monster|Spell|Trap|Equip) Cards?$", ("spot_removal",)),
    # "Destroys Special Summoned monsters" is the wiki's way of saying Bottomless
    # Trap Hole answers the Summon itself.
    ("Monster/Spell/Trap categories", "~^Destroys (Special Summoned|Normal Summoned|"
                                      "Flip Summoned) [Mm]onsters$",
     ("spot_removal", "summon_answer")),
    ("Monster/Spell/Trap categories", "Destroys equipped", ("spot_removal",)),
    ("Monster/Spell/Trap categories", "Destroys hand", ("hand_disruption",)),
    ("Monster/Spell/Trap categories", "~^Negates", ("negate",)),
    # Denying an ACTIVATION continuously is the floodgate; negating one
    # activation is interaction and is `negate` above.
    ("Monster/Spell/Trap categories",
     "~^Prevents (the )?activation of (your opponent's |Flip monsters'? )?"
     "(Spell|Trap|Effect|Monster|effects)", ("floodgate",)),
    ("Monster/Spell/Trap categories", "Prevents cards from being used", ("floodgate",)),
    ("Monster/Spell/Trap categories", "Restricts Monster Zones", ("floodgate",)),
    ("Monster/Spell/Trap categories", "Restricts Spell & Trap Zones", ("floodgate",)),
    ("Monster/Spell/Trap categories", "Cannot be destroyed by card effects",
     ("protection",)),
    ("Monster/Spell/Trap categories", "Cannot be targeted by card effects", ("protection",)),
    ("Monster/Spell/Trap categories", "~^Unaffected by", ("protection",)),
    ("Monster/Spell/Trap categories", "Equipped cannot be destroyed by card effects",
     ("protection",)),
    ("Monster/Spell/Trap categories", "Redirects destruction", ("protection",)),
    ("Monster/Spell/Trap categories", "~battling monster", ("battle_removal",)),
    ("Monster/Spell/Trap categories", "Treated as Equip Card", ("equip_effect",)),
    ("Monster/Spell/Trap categories", "Treats monsters as Equip Cards", ("equip_effect",)),
    ("Monster/Spell/Trap categories", "Treated as Continuous Spell Card",
     ("continuous_effect",)),
    ("Monster/Spell/Trap categories", "Remains on the field", ("continuous_effect",)),

    # ── Attack categories ───────────────────────────────────────────────────
    ("Attack categories", "Piercing", ("piercing",)),
    ("Attack categories", "Direct attacker", ("direct_attack",)),
    ("Attack categories", "Allows direct attacks", ("direct_attack",)),
    ("Attack categories", "Equipped direct attacks", ("direct_attack",)),
    ("Attack categories", "Multiple attacker", ("double_attack",)),
    ("Attack categories", "~^Allows multiple attacks", ("double_attack",)),
    ("Attack categories", "Can make multiple attacks on monsters", ("double_attack",)),
    ("Attack categories", "Cannot be destroyed by battle", ("battle_immune",)),
    ("Attack categories", "Equipped cannot be destroyed by battle", ("battle_immune",)),
    ("Attack categories", "~^Negates? [Aa]ttacks?$", ("negate",)),
    ("Attack categories", "Prevents attacks", ("floodgate",)),
    ("Attack categories", "Prevents your opponent's monsters from attacking",
     ("floodgate",)),
    ("Attack categories", "~^Cannot attack", ("attack_lock",)),
    ("Attack categories", "Prevents your monsters from attacking", ("attack_lock",)),
    ("Attack categories", "Prevents equipped monster from attacking", ("attack_lock",)),
    ("Attack categories", "Must attack", ("attack_lock",)),
    ("Attack categories", "~^Must (pay|Tribute)", ("attack_lock",)),
    ("Attack categories", "Manages attack targets", ("attack_redirect",)),

    # ── Stat changes ────────────────────────────────────────────────────────
    # "Your opponent's monsters gain ATK" is deliberately absent: it is the same
    # sentence pointed the wrong way, and 19 cards carry it.
    ("Stat changes",
     "~^(This card|Your monsters|Equipped|All monsters) gains? (ATK|DEF)$",
     ("stat_boost",)),
    ("Stat changes", "Doubles ATK", ("stat_boost",)),
    ("Stat changes", "~^(Your opponent's|All) monsters lose (ATK|DEF)$", ("stat_debuff",)),
    ("Stat changes", "~^Reduces (ATK|DEF) to 0$", ("stat_debuff",)),
    ("Stat changes", "~^Halves (ATK|DEF)$", ("stat_debuff",)),
    ("Stat changes", "~^Equipped loses (ATK|DEF)$", ("stat_debuff",)),
    ("Stat changes", "Your opponent's monsters lose Levels", ("stat_debuff",)),
    ("Stat changes", "Switches ATK and DEF", ("stat_debuff",)),
    ("Stat changes", "~Level", ("level_mod",)),
    ("Stat changes", "Treats monsters as Tuner monsters", ("level_mod",)),
    ("Stat changes", "~^(Copies|Changes( own| card)?) names?", ("name_change",)),
    ("Stat changes", "~^Treated as (multiple names|a Normal Monster)$", ("name_change",)),
    ("Stat changes", "Copies effects", ("name_change",)),

    # ── LP ──────────────────────────────────────────────────────────────────
    ("LP", "~^[Dd]amages your opponent$", ("burn",)),
    ("LP", "Your opponent loses LP", ("burn",)),
    ("LP", "Halves the opponent's LP", ("burn",)),
    ("LP", "Increases effect damage", ("burn",)),
    ("LP", "~^You gain L(P|ife Points)$", ("lifegain",)),
    ("LP", "Converts damage to LP gain", ("lifegain",)),
    ("LP", "~^Pays L(P|ife Points) for cost$", ("lp_cost",)),
    ("LP", "Maintenance cost", ("lp_cost",)),
    # A card that hurts its own controller.  The regex tagger deliberately
    # excluded self-damage from `burn` and then had nowhere to put it.
    ("LP", "Damages you", ("self_damage",)),
    ("LP", "You lose LP", ("self_damage",)),
    ("LP", "Halves the player's LP", ("self_damage",)),
    # Damage prevention is neither card advantage nor a stat, so no channel saw
    # it at all: Waboku and Threatening Roar scored as blank 1-for-1 spends.
    ("LP", "~^(Prevents|Reduces) (battle|effect) damage$", ("damage_block",)),
    ("LP", "Redirects effect damage", ("damage_block",)),

    # ── Banished categories ─────────────────────────────────────────────────
    ("Banished categories", "~for cost$", ("banish_cost",)),
    ("Banished categories", "~^Banishes from your opponent's field$", ("spot_removal",)),
    ("Banished categories", "~^Banishes from your opponent's (hand|Deck)$",
     ("hand_disruption",)),
    ("Banished categories", "~battling monster", ("battle_removal",)),
    ("Banished categories", "Banishes cards that would be sent to the Graveyard",
     ("gy_denial",)),
    # NOT `summon_answer`: "Banishes negated Summons" is carried by Macro Cosmos,
    # Dimensional Fissure and Banisher of the Radiance, which do not answer a
    # Summon at all — the monster is banished because THEIR replacement effect
    # catches it after someone else negated it.
    ("Banished categories", "Banishes negated Summons", ("gy_denial",)),
    # Spending your OWN Graveyard is `gy_payoff` (Miracle Fusion, King of the
    # Skull Servants), not `banish_payoff` — it feeds the banished zone rather
    # than harvesting it.  Only the harvest side is a payoff, and those values
    # live under Actions and Summoning categories above.
    ("Banished categories", "~^Banishes (itself )?from (your )?Graveyard", ("gy_payoff",)),
    ("Banished categories", "~^Banishes from your Graveyard", ("gy_payoff",)),

    # ── Miscellaneous ───────────────────────────────────────────────────────
    # An activation LIMIT is the marker of a repeatable engine: nobody limits a
    # one-shot.  Gated to bodies and permanents in `_recurring_ok` — a Normal
    # Spell with "you can only activate 1 per turn" is a deckbuilding rule, not
    # an engine.
    ("Miscellaneous", "Limited activations", ("recurring?",)),
    ("Miscellaneous", "Only once per turn", ("recurring?",)),
    ("Miscellaneous", "Only twice per turn", ("recurring?",)),
    ("Miscellaneous", "Once while face-up on the field", ("recurring?",)),
    ("Miscellaneous", "Turn limited effects", ("recurring?",)),
    ("Miscellaneous", "Gain this effect once per turn", ("recurring?",)),
    ("Miscellaneous", "~^Requires control of", ("conditional",)),
    ("Miscellaneous", "Requires having no cards in hand", ("conditional",)),
    ("LP", "Requires specific LP", ("conditional",)),
    ("Miscellaneous", "Archetype condition", ("conditional",)),
    ("Miscellaneous", "Archetype-exclusion condition", ("conditional",)),
    # A coin flip is a real drawback the model had no way to see: Arcana Force
    # and Second Coin Toss are priced as if their good half always happens.
    ("Miscellaneous", "Coin toss", ("random_outcome",)),
    ("Miscellaneous", "Die roll", ("random_outcome",)),
    ("Miscellaneous", "Special Summon Monster", ("nomi",)),
    ("Miscellaneous", "Pseudo-Flip Effect", ("flip_effect",)),
    ("Miscellaneous", "Trap Monster", ("free_body",)),
)

#: Tags the wiki ADDS to rather than replaces.  Both are places where the wiki
#: is measurably *incomplete* rather than merely different, so replacing would
#: lose cards — the diff is the evidence, not a hunch.
#:
#: * ``flip_effect`` — a FLIP monster is marked by its *type line* on the wiki,
#:   not by a category, so Ryko (69 era decks) carries no flip category at all.
#:   The ROM text's "FLIP:" prefix is complete and unambiguous, so the regex
#:   keeps the tag and the wiki's "Pseudo-Flip Effect" (Snowman Eater and
#:   friends, which the regex misses) is unioned in.
#: * ``summon_answer`` — Torrential Tribute's page lists exactly one category,
#:   "Destroys Monster Cards"; nothing records *when* it activates.  The regex
#:   version was hand-checked to land on the right seven, and dropping it would
#:   lose the two most-played answers in the format (Torrential 238 decks,
#:   Bottomless 152).
ADDITIVE: frozenset[str] = frozenset({"flip_effect", "summon_answer"})

#: Tags the wiki owns.  Built from the rule table, so adding a rule for a tag
#: automatically retires its regex — there is no second list to keep in step.
AUTHORITATIVE: frozenset[str] = frozenset(
    t.rstrip("?") for _, _, tags in _RULES for t in tags
) - ADDITIVE

#: Why each remaining derived tag is *not* in the table above.  Documentation,
#: and asserted by :func:`selftest` so a future rule cannot silently take over a
#: tag listed here as unreachable.
DERIVED_ONLY: dict[str, str] = {
    "opponent_turn": "no wiki category records WHEN a card acts; the strongest "
                     "tag in the evidence-off fit (+1.20, 5/5)",
    "mass_removal": "'Destroys Monster Cards' does not say how many",
    "symmetric": "no category distinguishes 'both players' from 'the opponent'",
    "needs_self_copies": "no category for 'needs N copies of itself'",
    "atk_scaling": "'This card gains ATK' does not say whether it scales",
    "board_reset": "2 cards; no category for a full reset",
    "hand_trap": "no category for 'acts from the hand on either turn'",
    "combat_trick": "measured: the nearest category ('Activates upon attack "
                    "declaration') agrees with the regex on ZERO cards — it is "
                    "Mirror Force, not Honest",
    "discard_payoff": "no category for 'rewards being discarded'",
    "summon_locked": "the line is drawn from IN-GAME behaviour, not text — the "
                     "wiki's modern wording would re-lock Elemental HERO "
                     "Mariner, which Instant Fusion can summon here",
    "ritual_payoff": "no 'performs a Ritual Summon' category",
    "vanilla": "the ROM's card type is authoritative",
    "effect_monster": "structural, from the ROM",
    "spell_card": "structural, from the ROM",
    "trap_card": "structural, from the ROM",
    "tuner": "structural, from the ROM",
    "extra_vanilla": "structural: an Extra Deck monster whose only clause is its "
                     "material line",
    "targeting": "fallback verb tag",
    "destruction": "fallback verb tag",
    "limited_use": "fallback verb tag",
    "set_card": "fallback verb tag",
}
# `conditional` is not listed above: the wiki owns it ("Requires control of …"),
# but it is ALSO a fallback verb tag, and the fallback runs after the overlay —
# so a card the wiki has nothing to say about can still earn it from a clause.

_MISSING = object()


def _compile(matcher: str) -> object:
    return re.compile(matcher[1:]) if matcher.startswith("~") else matcher


_COMPILED = tuple((g, _compile(m), tags) for g, m, tags in _RULES)


@lru_cache(maxsize=1)
def load() -> dict[int, dict[str, list[str]]]:
    """``{cid: {group: [values]}}`` for every card the scrape resolved."""
    if not CACHE.exists():
        return {}
    raw = json.loads(CACHE.read_text(encoding="utf-8"))
    return {
        int(cid): (row.get("categories") or {})
        for cid, row in raw.items()
        if row.get("found")
    }


def categories(cid: int) -> dict[str, list[str]] | None:
    """This card's category groups, or None when the scrape has no row for it."""
    return load().get(cid)


def _matches(matcher, value: str) -> bool:
    if isinstance(matcher, str):
        return matcher == value
    return matcher.search(value) is not None


def _recurring_ok(card: Card) -> bool:
    """Is an activation limit evidence of an ENGINE on this card?

    Only for something that stays on the field to use it again — a body or a
    permanent.  "You can only activate 1 'Card Destruction' per turn" is a
    deckbuilding rule on a one-shot Normal Spell, not a repeatable effect.
    """
    return card.is_monster or card.st_subtype in ("Continuous", "Field", "Equip")


def tags_for(card: Card) -> frozenset[str] | None:
    """Wiki tags for *card*, or None when the scrape never resolved its page.

    None means "ask the regexes"; an **empty** set means "the wiki says this card
    does nothing", which is the correct answer for a Normal Monster.
    """
    cats = categories(card.cid)
    if cats is None:
        return None
    out: set[str] = set()
    for group, matcher, tags in _COMPILED:
        values = cats.get(group)
        if not values:
            continue
        if any(_matches(matcher, v) for v in values):
            for t in tags:
                if t.endswith("?"):
                    if not _recurring_ok(card):
                        continue
                    t = t[:-1]
                out.add(t)
    # Note: `battle_immune` and `protection` are BOTH kept when both fire.  They
    # are two separate wiki entries ("Cannot be destroyed by battle" under Attack
    # categories, "Cannot be destroyed by card effects" under Monster/Spell/Trap)
    # rather than one sentence matched by two regexes, so the tagger's dedup —
    # which existed only to stop that double count — does not apply and would
    # throw away the battle half.
    return frozenset(out)


def supports(cid: int) -> list[str]:
    """The card's ``Supports`` values — Types, Attributes and named cards."""
    return list((categories(cid) or {}).get("Supports", ()))


def supports_archetypes(cid: int) -> list[str]:
    return list((categories(cid) or {}).get("Supports archetypes", ()))


#: The 22 monster Types and 6 Attributes this ROM ships, as the wiki spells them.
#: Anything else under ``Supports`` is a named card ("The Sanctuary in the Sky")
#: or a card class ("Equip Spell Card"), which the want machinery cannot express.
TYPES = frozenset({
    "Aqua", "Beast", "Beast-Warrior", "Dinosaur", "Divine-Beast", "Dragon", "Fairy",
    "Fiend", "Fish", "Insect", "Machine", "Plant", "Psychic", "Pyro", "Reptile",
    "Rock", "Sea Serpent", "Spellcaster", "Thunder", "Warrior", "Winged Beast",
    "Zombie",
})
ATTRIBUTES = frozenset({"DARK", "DIVINE", "EARTH", "FIRE", "LIGHT", "WATER", "WIND"})


def supported_kinds(cid: int) -> tuple[frozenset[str], frozenset[str]]:
    """``(types, attributes)`` this card supports, as ROM-spelled values."""
    vals = supports(cid)
    return (frozenset(v for v in vals if v in TYPES),
            frozenset(v for v in vals if v in ATTRIBUTES))


def material_genericity(card: Card) -> float | None:
    """How freely this Extra Deck monster's materials can be supplied: 0.0-1.0.

    ``power.w_extra_generic`` used to *infer* this from "does any parsed want
    carry an archetype or a card name", which reads the whole card — so Scrap
    Dragon (179 era decks) counted as locked because its **effect** mentions an
    archetype, while its material line is the fully generic "1 Tuner + 1 or more
    non-Tuner monsters".  The wiki states the fact about the materials directly.

    Graded rather than boolean, because the wiki grades it: a Synchro can be
    generic in its Tuner, its non-Tuners, both, or neither, and Goyo Guardian
    (EARTH non-Tuners) is genuinely easier to make than Blackwing Armor Master
    and harder than Catastor.

    Returns None when the scrape has no row for the card, so the caller can fall
    back to the inferred test.
    """
    cats = categories(card.cid)
    if cats is None:
        return None
    summ = cats.get("Summoning categories", ())
    if card.is_synchro:
        if "Does not require specific Synchro Materials" in summ:
            return 1.0
        return 0.5 * sum(
            1 for v in ("Does not require specific non-Tuner Synchro Materials",
                        "Does not require specific Tuner Synchro Materials")
            if v in summ
        )
    # Fusions never carry a "Does not require…" category — the wiki only ever
    # states the restriction — so the absence of every "Requires … Material" is
    # the generic case.
    return 0.0 if any(v.startswith("Requires") and "Material" in v for v in summ) else 1.0


def coverage(cards: Iterable[Card]) -> tuple[int, int, int]:
    """``(resolved, with_categories, absent)`` over *cards*."""
    resolved = with_cats = absent = 0
    for c in cards:
        cats = categories(c.cid)
        if cats is None:
            absent += 1
        else:
            resolved += 1
            with_cats += 1 if cats else 0
    return resolved, with_cats, absent


def selftest() -> int:
    """Invariants that a future edit to the rule table could break."""
    bad = 0
    overlap = AUTHORITATIVE & set(DERIVED_ONLY)
    if overlap:
        bad += 1
        print(f"  FAIL tags claimed by BOTH the wiki table and DERIVED_ONLY: "
              f"{sorted(overlap)}")
    for group, matcher, _ in _COMPILED:
        if isinstance(matcher, str):
            continue
        try:
            matcher.fullmatch("")
        except re.error as exc:  # pragma: no cover — compile already raised
            bad += 1
            print(f"  FAIL bad regex in {group}: {exc}")
    # Every rule must match at least one card in the scrape, or it is dead: a
    # typo'd category name is silent otherwise.
    store = load()
    seen = {(g, v) for cats in store.values() for g, vs in cats.items() for v in vs}
    for (group, matcher, _), (_, src, _) in zip(_COMPILED, _RULES):
        if not any(g == group and _matches(matcher, v) for g, v in seen):
            bad += 1
            print(f"  FAIL dead rule: {group} :: {src}")
    print(f"wikitags: {len(_RULES)} rules, {len(AUTHORITATIVE)} tags claimed, "
          f"{'OK' if not bad else str(bad) + ' PROBLEMS'}")
    return 1 if bad else 0


if __name__ == "__main__":
    import sys

    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(selftest())
