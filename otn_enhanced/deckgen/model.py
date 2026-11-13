"""Core data types shared across the deck generator.

The one rule that matters here: **ROM values are authoritative for gameplay,
ygoprodeck supplies text and metadata only.**  Over the Nexus is a 2011 engine
and ygoprodeck carries modern errata, so where the two disagree on ATK/DEF/level
the ROM wins and :attr:`Card.stat_conflict` is set for the report.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

# ── ERA2 card_type_encoded groupings ────────────────────────────────────────
EXTRA_DECK_TYPES = frozenset({5, 7, 35, 37, 39})
TUNER_TYPES = frozenset({31, 33, 39})
SYNCHRO_TYPES = frozenset({35, 37, 39})
FUSION_TYPES = frozenset({5, 7})
RITUAL_TYPES = frozenset({9, 11})
SPELL_TYPE = 27
TRAP_TYPE = 29
TOKEN_TYPE = 21

# Non-summonable-by-normal-means main-deck types are marked via text, not here.
_MONSTER_FLAGS = {
    1: ("normal",),
    3: ("effect",),
    5: ("fusion",),
    7: ("fusion", "effect"),
    9: ("ritual",),
    11: ("ritual", "effect"),
    13: ("toon", "effect"),
    15: ("spirit", "effect"),
    17: ("union", "effect"),
    19: ("gemini", "effect"),
    21: ("token",),
    23: ("divine", "effect"),
    31: ("normal", "tuner"),
    33: ("tuner", "effect"),
    35: ("synchro",),
    37: ("synchro", "effect"),
    39: ("synchro", "tuner", "effect"),
}


def card_class_of(enc: int) -> str:
    if enc == SPELL_TYPE:
        return "spell"
    if enc == TRAP_TYPE:
        return "trap"
    return "monster"


@dataclass(frozen=True)
class Card:
    """One playable card: ROM properties joined to real English card text."""

    cid: int
    name: str
    name_key: str
    passcode: int | None
    join_status: str  # exact | tsv | alias | stat | excluded | missing
    join_note: str

    # ── ROM truth ──────────────────────────────────────────────────────────
    card_type_encoded: int
    card_type: str
    card_class: str  # monster | spell | trap
    monster_flags: frozenset[str]
    attribute: str | None
    race: str | None
    level: int | None
    atk: int  # -1 == "?"
    def_: int  # -1 == "?"
    st_subtype: str | None

    # ── ygoprodeck: text + metadata only ───────────────────────────────────
    desc: str
    archetype: str | None
    stat_conflict: bool

    @property
    def is_extra(self) -> bool:
        return self.card_type_encoded in EXTRA_DECK_TYPES

    @property
    def is_tuner(self) -> bool:
        return self.card_type_encoded in TUNER_TYPES

    @property
    def is_synchro(self) -> bool:
        return self.card_type_encoded in SYNCHRO_TYPES

    @property
    def is_monster(self) -> bool:
        return self.card_class == "monster"

    @property
    def playable(self) -> bool:
        """Usable in a normal-duel deck (excludes Tokens and Turbo-Duel cards)."""
        return self.join_status != "excluded" and self.card_type_encoded != TOKEN_TYPE

    @property
    def has_text(self) -> bool:
        return bool(self.desc)

    def to_json(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["monster_flags"] = sorted(self.monster_flags)
        return d

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "Card":
        d = dict(d)
        d["monster_flags"] = frozenset(d["monster_flags"])
        return cls(**d)


# ── Parsed-text types ───────────────────────────────────────────────────────

_CMP = {"<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b, "==": lambda a, b: a == b}


@dataclass(frozen=True)
class Predicate:
    """A card filter written on a card — what some effect *wants*.

    ``Rekindling`` yields ``Predicate(card_class="monster",
    attribute={"FIRE"}, def_=("==", 200))``.  Every field is a conjunct; a
    ``None`` field is unconstrained, and a set field is a disjunction
    (``"LIGHT or DARK monster"``).
    """

    card_class: str | None = None
    st_subtype: str | None = None
    attribute: frozenset[str] | None = None
    race: frozenset[str] | None = None
    monster_flags: frozenset[str] | None = None
    archetype: str | None = None
    exact_names: frozenset[str] | None = None
    level: tuple[str, int] | None = None
    atk: tuple[str, int] | None = None
    def_: tuple[str, int] | None = None
    board: frozenset[str] = frozenset()
    #: Explicit set of acceptable Levels, when the constraint is not an
    #: inequality.  A restricted Tuner's legal partner Levels are a *set* with
    #: holes in it -- Debris Dragon accepts 2, 3, 5, 6 but not 4 -- which the
    #: ``level`` inequality above cannot express.
    levels: frozenset[int] | None = None
    #: Monster flags the card must NOT have.  Needed for "non-Tuner", since
    #: ``monster_flags`` is a positive subset test and two Tuners cannot be used
    #: for the same Synchro Summon.
    exclude_flags: frozenset[str] | None = None
    #: True when only a MAIN-deck card can answer this want.
    #:
    #: You cannot search, draw, discard or banish-from-hand an Extra Deck
    #: monster, so one must not count as satisfying a want that is answered out
    #: of the Deck or the hand.  Two reported failures were the same bug:
    #: Elemental Hero Stratos' "1 HERO monster" was satisfied by Elemental Hero
    #: Absolute Zero, a Fusion sitting in the Extra Deck, so a Stratos with no
    #: main-deck HERO to fetch never paid the orphan penalty; and Allure of
    #: Darkness' DARK want matched 654 cards of which **67 were Extra Deck**.
    main_deck_only: bool = False
    #: True when copies do not help: the want counts DISTINCT card names.
    #:
    #: Judgment Dragon needs "4 or more 'Lightsworn' monsters with different
    #: names"; a deck holding 2 Lyla and 2 Ryko has four copies and only **two**
    #: names, and was counted as satisfied.  12 cards in the pool word a want
    #: this way — Judgment Dragon, Rainbow Dark Dragon and the Six Samurai, whose
    #: whole mechanic is needing a second, differently-named Samurai.
    distinct_names: bool = False
    confidence: float = 1.0
    raw: str = ""

    def is_empty(self) -> bool:
        """True when nothing is constrained — matches the whole pool."""
        return not any(
            (
                self.card_class,
                self.st_subtype,
                self.attribute,
                self.race,
                self.monster_flags,
                self.archetype,
                self.exact_names,
                self.level,
                self.levels,
                self.exclude_flags,
                self.atk,
                self.def_,
            )
        )

    def key(self) -> tuple:
        """Canonical identity, ignoring provenance — used to dedupe predicates.

        Memoised: the class is frozen so the answer never changes, and it was
        being rebuilt 600k times per deck build from matchindex lookups.
        """
        cached = self.__dict__.get("_key")
        if cached is not None:
            return cached
        key = (
            self.card_class,
            self.st_subtype,
            tuple(sorted(self.attribute)) if self.attribute else None,
            tuple(sorted(self.race)) if self.race else None,
            tuple(sorted(self.monster_flags)) if self.monster_flags else None,
            self.archetype,
            tuple(sorted(self.exact_names)) if self.exact_names else None,
            self.level,
            tuple(sorted(self.levels)) if self.levels else None,
            tuple(sorted(self.exclude_flags)) if self.exclude_flags else None,
            self.atk,
            self.def_,
            self.main_deck_only,
            self.distinct_names,
        )
        object.__setattr__(self, "_key", key)
        return key

    def matches(self, card: Card) -> bool:
        """Does *card* satisfy this filter?

        Semantics ported from ``power_ranking.KWARG_MAP``, with "?" ATK/DEF
        (-1 in the ROM) never satisfying a numeric bound.
        """
        if self.main_deck_only and card.is_extra:
            return False
        if self.exact_names is not None:
            return card.name_key in self.exact_names
        if self.card_class and card.card_class != self.card_class:
            return False
        if self.st_subtype and card.st_subtype != self.st_subtype:
            return False
        if self.attribute and card.attribute not in self.attribute:
            return False
        if self.race and card.race not in self.race:
            return False
        if self.monster_flags and not self.monster_flags <= card.monster_flags:
            return False
        if self.exclude_flags and self.exclude_flags & card.monster_flags:
            return False
        if self.levels is not None and card.level not in self.levels:
            return False
        if self.archetype:
            # Card text sometimes pluralises the quoted name ('as many "Nimble
            # Momongas" as possible'), so accept the singular form too.
            arch = self.archetype.lower()
            forms = {arch, arch[:-1]} if arch.endswith("s") else {arch}
            if not any(
                (card.archetype and card.archetype.lower() == f) or f in card.name.lower()
                for f in forms
            ):
                return False
        for bound, value in (
            (self.level, card.level),
            (self.atk, card.atk),
            (self.def_, card.def_),
        ):
            if bound is None:
                continue
            if value is None or value < 0:
                return False
            if not _CMP[bound[0]](value, bound[1]):
                return False
        return True


#: Matches every card — an effect that targets "1 monster" with no restriction.
Predicate.ANY = Predicate(raw="<any>")
#: Sentinel for "this card"/"it" — a self-reference, never a want.
Predicate.SELF = Predicate(raw="<self>", confidence=0.0)


@dataclass(frozen=True)
class Count:
    """How many cards a clause moves.  ``n`` is ``None`` for open-ended kinds."""

    kind: str  # fixed | up_to | as_many | all | variable
    n: int | None = None

    def nominal(self) -> float:
        """A single representative number, for coefficient arithmetic."""
        if self.kind == "fixed":
            return float(self.n or 1)
        if self.kind == "up_to":
            return float(self.n or 1)
        return 1.0


@dataclass(frozen=True)
class Clause:
    """One atomic thing a card does (or costs)."""

    kind: str  # cost | gain | condition | restriction | tag
    verb: str
    count: Count = Count("fixed", 1)
    zone_from: str | None = None
    zone_to: str | None = None
    side: str = "you"  # you | opponent | both | either
    predicate: Predicate | None = None
    self_ref: bool = False
    timing: str | None = None
    frequency: str | None = None
    optional: bool = False
    temporary: bool = False
    confidence: float = 1.0
    raw: str = ""
    #: Which bullet-point branch this came from.  0 means "always applies".
    #: On a "pick 1 of these effects" card, branches are alternatives and the
    #: economy model takes the best one rather than summing them.
    mode: int = 0


@dataclass
class ParsedCard:
    """Everything derived from one card's English text."""

    cid: int
    clauses: list[Clause] = field(default_factory=list)
    tags: frozenset[str] = frozenset()
    wants: list[tuple[Predicate, float]] = field(default_factory=list)
    parse_confidence: float = 1.0
    unparsed: list[str] = field(default_factory=list)
    #: True when the card's bullet points are alternatives ("Apply 1 of these
    #: effects"), so only one branch resolves.
    exclusive_modes: bool = False
    #: Capabilities the deck must supply before this card does anything —
    #: Divine Wind of Mist Valley requires ``bounce_self``.
    requires: frozenset[str] = frozenset()
    #: Capabilities this card supplies to others.
    provides: frozenset[str] = frozenset()
    #: Cards this pulls out of the Deck when used.  Three Upstart Goblin makes a
    #: 40-card deck behave like a 37-card one.
    thins: int = 0

    def with_tags(self, *extra: str) -> "ParsedCard":
        return replace(self, tags=self.tags | frozenset(extra))
