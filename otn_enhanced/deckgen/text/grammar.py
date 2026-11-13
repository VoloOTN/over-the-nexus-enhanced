"""Noun-phrase grammar: ``"Level 4 or lower FIRE Pyro monster with 200 DEF"``
-> :class:`~..model.Predicate`.

This is a small token-consuming parser rather than one large regular
expression.  Yu-Gi-Oh! target phrases are highly regular but the modifier slots
are *optional and reorderable* ("Reptile-Type \"Worm\" monster" vs "\"Worm\"
Reptile monster"), which a single regex handles badly and a consume-what-you-
recognise loop handles naturally.  It also degrades usefully: whatever it fails
to consume comes back as residue, so a partial parse still yields a usable
predicate and the leftovers land in the coverage report.

Shape of a phrase::

    [count] [Level N (or lower|higher)] ["Archetype"] [ATTRIBUTE] [Race[-Type]]
    [Tuner|Normal|Synchro|...]  HEAD-NOUN  [with N or less ATK] [you control]
"""

from __future__ import annotations

import re

from otn_enhanced.deckgen.model import Count, Predicate

ATTRIBUTES = {"light", "dark", "water", "fire", "earth", "wind", "divine"}

RACES = {
    "dragon": "Dragon", "zombie": "Zombie", "fiend": "Fiend", "pyro": "Pyro",
    "sea serpent": "Sea Serpent", "rock": "Rock", "machine": "Machine",
    "fish": "Fish", "dinosaur": "Dinosaur", "insect": "Insect", "beast": "Beast",
    "beast-warrior": "Beast-Warrior", "plant": "Plant", "aqua": "Aqua",
    "warrior": "Warrior", "winged beast": "Winged Beast", "fairy": "Fairy",
    "spellcaster": "Spellcaster", "thunder": "Thunder", "reptile": "Reptile",
    "psychic": "Psychic", "divine-beast": "Divine-Beast",
}
# Longest first so "beast-warrior" is not shadowed by "beast".
_RACE_KEYS = sorted(RACES, key=len, reverse=True)

# Monster subtype words that map onto Card.monster_flags.
SUBTYPES = {
    "tuner": "tuner", "normal": "normal", "effect": "effect",
    "synchro": "synchro", "fusion": "fusion", "ritual": "ritual",
    "toon": "toon", "spirit": "spirit", "union": "union", "gemini": "gemini",
}

# Head nouns -> (card_class, st_subtype)
HEADS: dict[str, tuple[str | None, str | None]] = {
    "monster": ("monster", None), "monsters": ("monster", None),
    "monster card": ("monster", None), "monster cards": ("monster", None),
    "card": (None, None), "cards": (None, None),
    "spell": ("spell", None), "spells": ("spell", None),
    "spell card": ("spell", None), "spell cards": ("spell", None),
    "trap": ("trap", None), "traps": ("trap", None),
    "trap card": ("trap", None), "trap cards": ("trap", None),
    "spell/trap": (None, None), "spell/trap card": (None, None),
    "spell/trap cards": (None, None), "spell and trap cards": (None, None),
    "equip spell card": ("spell", "Equip"), "equip spell": ("spell", "Equip"),
    "field spell card": ("spell", "Field"), "field spell": ("spell", "Field"),
    "quick-play spell": ("spell", "Quick-Play"),
    "quick-play spell card": ("spell", "Quick-Play"),
    "continuous spell": ("spell", "Continuous"),
    "continuous trap": ("trap", "Continuous"),
    "counter trap": ("trap", "Counter"),
    "counter trap card": ("trap", "Counter"),
    "ritual spell card": ("spell", "Ritual"), "ritual spell": ("spell", "Ritual"),
    "ritual monster": ("monster", None),
}
_HEAD_KEYS = sorted(HEADS, key=len, reverse=True)

# Phrases meaning "this very card" — a self-reference is never a *want*.
SELF_WORDS = {
    "this card", "it", "that monster", "that card", "this monster",
    "that target", "the target", "this face-up card", "them", "those monsters",
    "that face-up monster", "this effect", "the equipped monster",
    "that Synchro Monster", "the target monster",
}

_COUNT_RE = re.compile(
    r"^(?:"
    r"(?P<asmany>as many)|"
    r"(?P<anynum>any number of)|"
    r"(?P<all>all(?: of)?(?: the)?)|"
    r"(?P<upto>up to (?P<upton>\d+|one|two|three))|"
    r"(?P<fixed>\d+|one|two|three|a|an|the|each|1)"
    r")\s+",
    re.I,
)
_WORD_NUM = {"one": 1, "two": 2, "three": 3, "a": 1, "an": 1, "the": 1, "each": 1}

_LEVEL_RE = re.compile(r"^level (?P<n>\d+)(?: or (?P<dir>lower|higher|less|more))?\s+", re.I)
_STAT_RE = re.compile(
    r"\bwith (?P<n>[\d,]+) (?:or (?P<dir>less|more|lower|higher) )?(?P<stat>atk|def)\b", re.I
)
_QUOTED_RE = re.compile(r'"([^"]{2,60})"')

_BOARD = (
    ("you control", "you_control"),
    ("your opponent controls", "opponent_controls"),
    ("in your graveyard", "your_gy"),
    ("in your gy", "your_gy"),
    ("in either graveyard", "either_gy"),
    ("in either gy", "either_gy"),
    ("on the field", "field"),
    ("face-up", "face_up"),
    ("face-down", "face_down"),
)

# Leading noise that carries no filtering power.
_STRIP_PREFIX = re.compile(
    r"^(?:other |another |different |your |the opponent's |opponent's |1 other )+", re.I
)

#: Words that appear inside target phrases but carry no filtering power, so
#: leaving them unconsumed says nothing about parse quality.  Without this,
#: ``"the 1 face-up monster your opponent controls that has the highest DEF"``
#: parses perfectly yet scores as low-confidence because of "that has highest".
_FILLER = frozenset(
    """that has have with the a an of in on is are was to and or than
    highest lowest same name as possible instead its their this these those
    equipped selected chosen declared original current then also but only
    each any both either player players you your opponent opponents controls
    control field hand deck graveyard gy level levels total combined
    among from for by when while during if it them there""".split()
)


def _norm_name(s: str) -> str:
    """Same folding as :func:`namematch.normalize`, without the import cycle."""
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def parse_count(text: str) -> tuple[Count, str]:
    """Peel a leading quantifier off *text*.  Returns ``(count, remainder)``."""
    m = _COUNT_RE.match(text)
    if not m:
        return Count("fixed", 1), text
    rest = text[m.end():]
    if m.group("asmany"):
        return Count("as_many"), rest
    if m.group("anynum"):
        return Count("as_many"), rest
    if m.group("all"):
        return Count("all"), rest
    if m.group("upto"):
        raw = m.group("upton").lower()
        return Count("up_to", _WORD_NUM.get(raw, int(raw) if raw.isdigit() else 1)), rest
    raw = m.group("fixed").lower()
    return Count("fixed", _WORD_NUM.get(raw, int(raw) if raw.isdigit() else 1)), rest


def parse_predicate(
    phrase: str, *, known_names: frozenset[str] | None = None
) -> tuple[Predicate | None, Count, list[str]]:
    """Parse a target phrase.

    Returns ``(predicate, count, residue)``.  ``predicate`` is ``None`` for a
    self-reference (``"this card"``), :data:`Predicate.SELF` never escapes this
    function as a want.  ``residue`` lists fragments that were not understood —
    an empty list means a full parse.
    """
    original = phrase.strip().rstrip(".,;:")
    if not original:
        return None, Count("fixed", 1), []

    low = original.lower()
    if low in SELF_WORDS or low.rstrip("s") in SELF_WORDS:
        return None, Count("fixed", 1), []

    count, rest = parse_count(low)
    rest = _STRIP_PREFIX.sub("", rest).strip()
    if rest in SELF_WORDS:
        return None, count, []

    if "as possible" in rest:
        count = Count("as_many")
        rest = rest.replace("as possible", "").strip()

    board: set[str] = set()
    for needle, tag in _BOARD:
        if needle in rest:
            board.add(tag)
            rest = rest.replace(needle, " ")

    # Trailing stat bound: "with 1500 or less ATK"
    atk = def_ = None
    m = _STAT_RE.search(rest)
    if m:
        n = int(m.group("n").replace(",", ""))
        direction = (m.group("dir") or "").lower()
        op = "<=" if direction in ("less", "lower") else ">=" if direction in ("more", "higher") else "=="
        if m.group("stat").lower() == "atk":
            atk = (op, n)
        else:
            def_ = (op, n)
        rest = (rest[: m.start()] + " " + rest[m.end():]).strip()

    # Quoted strings: an exact card name if the pool knows it, else an archetype.
    archetype = None
    exact: set[str] = set()
    for q in _QUOTED_RE.findall(original):
        key = _norm_name(q)
        if known_names is not None and key in known_names:
            exact.add(key)
        else:
            archetype = q
        rest = rest.replace(f'"{q.lower()}"', " ")
    rest = rest.replace('"', " ")

    level = None
    m = _LEVEL_RE.match(rest.strip())
    if m:
        direction = (m.group("dir") or "").lower()
        op = "<=" if direction in ("lower", "less") else ">=" if direction in ("higher", "more") else "=="
        level = (op, int(m.group("n")))
        rest = rest[m.end():] if m.end() <= len(rest) else ""
    rest = rest.strip()

    attributes: set[str] = set()
    races: set[str] = set()
    flags: set[str] = set()
    head: str | None = None
    residue: list[str] = []

    # Consume recognised modifiers left-to-right until the head noun.
    while rest:
        rest = rest.lstrip(" ,")
        if not rest:
            break
        if rest.startswith("or ") or rest.startswith("and "):
            rest = rest.split(" ", 1)[1] if " " in rest else ""
            continue

        hit = next((h for h in _HEAD_KEYS if rest.startswith(h)), None)
        if hit and (len(rest) == len(hit) or not rest[len(hit)].isalnum()):
            head = hit
            rest = rest[len(hit):].strip()
            break

        hit = next((r for r in _RACE_KEYS if rest.startswith(r)), None)
        if hit:
            after = rest[len(hit):]
            if not after[:1].isalnum():
                races.add(RACES[hit])
                rest = re.sub(r"^(?:-type|type)\b", "", after.strip()).strip()
                continue

        word, _, tail = rest.partition(" ")
        bare = word.strip("-,")
        if bare in ATTRIBUTES:
            attributes.add(bare.upper())
            rest = tail
            continue
        if bare in SUBTYPES:
            flags.add(SUBTYPES[bare])
            rest = tail
            continue
        if bare in ("non-tuner", "nontuner"):
            # A *negative* constraint the Predicate cannot express; record it so
            # the caller can see the parse was lossy rather than silently wrong.
            residue.append(bare)
            rest = tail
            continue
        if bare in ("face-up", "face-down", "set", "faceup", "facedown"):
            rest = tail
            continue
        residue.append(bare)
        rest = tail

    if head is None and not (attributes or races or flags or level or exact or archetype):
        return None, count, [original]

    card_class, st_subtype = HEADS.get(head or "card", (None, None))
    if card_class is None and (attributes or races or level or flags):
        card_class = "monster"  # only monsters have these properties

    # Only *content* words left unconsumed indicate a shaky parse.
    residue = [w for w in residue if w and w not in _FILLER and not w.isdigit()]
    confidence = 1.0 if not residue else max(0.4, 1.0 - 0.12 * len(residue))
    pred = Predicate(
        card_class=card_class,
        st_subtype=st_subtype,
        attribute=frozenset(attributes) or None,
        race=frozenset(races) or None,
        monster_flags=frozenset(flags) or None,
        archetype=archetype,
        exact_names=frozenset(exact) or None,
        level=level,
        atk=atk,
        def_=def_,
        board=frozenset(board),
        confidence=confidence,
        raw=original,
    )
    return pred, count, residue
