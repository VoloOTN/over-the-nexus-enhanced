"""Synchro Material restrictions carried by MAIN-deck monsters.

A Tuner is only worth the Synchros it can actually make.  The reach model in
:mod:`deckstate` works purely in Level arithmetic — Tuner Level + non-Tuner
Level(s) — which silently assumes every Tuner can pair with every non-Tuner and
make anything.  Fourteen main-deck monsters in this ROM's pool say otherwise, and
Debris Dragon says it twice::

    Cannot be used as Synchro Material, except for the Synchro Summon of a
    Dragon monster.  The other Synchro Material(s) cannot be Level 4.

In a LIGHT Fairy deck whose non-Tuners are Levels 8/6/4/4/4/7/7, that leaves
Debris Dragon with *nothing*: the three Level 4s are banned outright, and
4+8, 4+6, 4+7 hit Levels 12/10/11, which had no Synchro in the Extra Deck at
all.  The search still paid it full Tuner value.

Restrictions are read off the card text rather than stored on ParsedCard so the
parse cache does not have to change shape; ``rule_for`` is memoised per cid.

Anything the patterns do not understand is reported as ``unknown``, which the
callers treat as *unrestricted*.  Over-restricting would silently delete legal
lines, which is the worse failure — a missing restriction costs accuracy, an
invented one costs the deck a card.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from otn_enhanced.deckgen.model import Card

#: "Dragon monster" / "Beast-Type monster" / "Warrior-Type Synchro Monster"
_RACE = re.compile(r'^(?:an?\s+)?"?([A-Z][a-z]+(?:[- ][A-Z][a-z]+)?)"?(?:-Type)?\s+(?:Synchro\s+)?[Mm]onster')
#: '"Blackwing" monster' — a quoted name is an archetype, not a Race.
_ARCH = re.compile(r'^(?:an?\s+)?"([^"]+)"\s+(?:Synchro\s+)?[Mm]onster')

_MATERIAL_ONLY = re.compile(
    r"cannot be used as (?:a )?Synchro Material(?: Monster)?,?\s*"
    r"except for the Synchro Summon of\s+([^.]+)",
    re.I,
)
_PARTNER_LEVEL_BAN = re.compile(
    r"other Synchro Material(?:\(s\)|s)? cannot be Level (\d+)", re.I
)
_PARTNER_MUST = re.compile(
    r"(?:all )?(?:the )?other Synchro Material(?:\(s\)|s)?(?: Monsters?)? must be\s+([^.]+)",
    re.I,
)
#: "the other Fusion Material Monster(s) must be LIGHT" — the price the three
#: Hex-Sealed Fusions charge for standing in as any material.
_FUSION_PARTNER_ATTR = re.compile(
    r"other Fusion[- ]Material(?:\(s\)|s)?(?: Monsters?)?(?:\(s\))? must be\s+"
    r"(LIGHT|DARK|EARTH|WATER|FIRE|WIND|DIVINE)\b",
    re.I,
)


def fusion_partner_attribute(card) -> str | None:
    """Attribute this card forces the OTHER Fusion Materials to have, if any."""
    m = _FUSION_PARTNER_ATTR.search(card.desc or "")
    return m.group(1).upper() if m else None
#: Bare "Cannot be used as a Synchro Material." with no exception clause.
_NEVER = re.compile(r"[Cc]annot be used as (?:a )?Synchro Material(?: Monster)?\s*\.")

#: These qualify the restriction with a state this model does not track ("if it
#: was Special Summoned", "while face-up on the field", "this turn").  Treating
#: them as absolute would wrongly delete lines that are legal most of the time.
_CONDITIONAL = re.compile(
    r"\b(?:if this card was|while this card is|this turn|during the turn|"
    r"this face-up card)\b",
    re.I,
)


@dataclass(frozen=True)
class MaterialRule:
    """What a main-deck monster may be used as Synchro Material for."""

    #: Cannot be Synchro Material at all, unconditionally.
    never: bool = False
    #: The Synchro Monster must have this Race …
    target_race: str | None = None
    #: … or belong to this archetype.
    target_archetype: str | None = None
    #: Levels the OTHER materials may not be.
    partner_level_ban: frozenset[int] = field(default_factory=frozenset)
    #: True when the text restricts something these patterns could not decode;
    #: callers treat it as unrestricted rather than guess.
    unknown: bool = False

    @property
    def restricts_target(self) -> bool:
        return bool(self.target_race or self.target_archetype)


_NONE = MaterialRule()


def _interpret(phrase: str) -> tuple[str | None, str | None, bool]:
    """``(race, archetype, unknown)`` for the noun phrase after "except for"."""
    phrase = phrase.strip()
    m = _ARCH.match(phrase)
    if m:
        return None, m.group(1), False
    m = _RACE.match(phrase)
    if m:
        # "Beast-Type monster": the optional second word of the Race pattern
        # happily swallows "-Type", which then matches no ROM Race at all.
        return re.sub(r"-Type$", "", m.group(1)), None, False
    return None, None, True


@lru_cache(maxsize=None)
def _rule_from_desc(desc: str) -> MaterialRule:
    if not desc:
        return _NONE
    race = arch = None
    unknown = never = False
    bans: set[int] = set()

    for sentence in re.split(r"(?<=\.)\s+", desc):
        conditional = bool(_CONDITIONAL.search(sentence))
        m = _MATERIAL_ONLY.search(sentence)
        if m and not conditional:
            race, arch, unknown = _interpret(m.group(1))
        elif _NEVER.search(sentence) and not conditional and not m:
            never = True
        m = _PARTNER_LEVEL_BAN.search(sentence)
        if m:
            bans.add(int(m.group(1)))
        elif _PARTNER_MUST.search(sentence):
            # "all other Synchro Materials must be <X>" — decodable in principle,
            # but no card in this pool phrases it in a way the reach model can
            # act on, so it is recorded as unknown instead of half-applied.
            unknown = True

    if not (race or arch or bans or never):
        return MaterialRule(unknown=unknown) if unknown else _NONE
    return MaterialRule(
        never=never,
        target_race=race,
        target_archetype=arch,
        partner_level_ban=frozenset(bans),
        unknown=unknown,
    )


def rule_for(card: Card) -> MaterialRule:
    """The material restriction *card* carries; ``_NONE`` when unrestricted."""
    if card.is_extra or not card.is_monster:
        return _NONE
    return _rule_from_desc(card.desc or "")


def allows_target(rule: MaterialRule, synchro: Card) -> bool:
    """May a monster carrying *rule* be material for *synchro*?"""
    if rule.never:
        return False
    if rule.target_race and (synchro.race or "") != rule.target_race:
        return False
    if rule.target_archetype:
        name = synchro.name or ""
        arch = synchro.archetype or ""
        if rule.target_archetype not in arch and rule.target_archetype not in name:
            return False
    return True


def partner_levels(rule: MaterialRule, levels) -> list[int]:
    """*levels* minus the ones this rule forbids the other materials to be."""
    if not rule.partner_level_ban:
        return list(levels)
    return [lv for lv in levels if lv not in rule.partner_level_ban]
