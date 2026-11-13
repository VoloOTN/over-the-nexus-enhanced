"""Split card text into segments and label each as condition / cost / effect.

Yu-Gi-Oh! problem-solving card text is punctuated to a fixed shape::

    <activation condition>: <cost or requirement>; <effect>

Not every card uses every slot.  The one judgement call here is that the
pre-semicolon slot is only a **cost** when its verb actually spends something —
``"Discard 1 card; ..."`` is a cost, but ``"Target 1 monster; ..."`` and
``"Reveal 1 card; ..."`` are requirements that cost no card advantage.  Getting
that wrong would double-count every targeting effect as a −1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Pre-semicolon verbs that genuinely spend a resource.
COST_VERBS = frozenset(
    {"discard", "tribute", "pay", "banish", "send", "return", "shuffle", "detach", "remove"}
)

#: Pre-semicolon verbs that are requirements, not costs.
REQUIREMENT_VERBS = frozenset({"target", "reveal", "declare", "select", "choose", "show"})

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_LEADING_VERB = re.compile(r"^\s*(?:you can\s+)?([a-z]+)", re.I)

# Parenthetical rulings and reminder text carry no mechanics.
_PARENS = re.compile(r"\([^)]*\)")


#: Cards that offer a menu of alternatives rather than a list of abilities.
#: Summing the branches of a "pick one" card is the single largest way to
#: over-score it -- Six Strike - Triple Impact would read as three board wipes.
_EXCLUSIVE = re.compile(
    r"\b(?:apply|activate|use|select|choose)\s+(?:only\s+)?1 of (?:these|the following)"
    r"|\bone of the following effects\b",
    re.I,
)
_BULLET = re.compile(r"[●○•]")


def is_exclusive(desc: str) -> bool:
    """True when the card's bullet points are alternatives, not cumulative."""
    return bool(_EXCLUSIVE.search(desc or ""))


@dataclass(frozen=True)
class Segment:
    """One punctuation-delimited piece of card text."""

    role: str  # condition | cost | requirement | effect
    text: str
    optional: bool  # introduced by "You can"
    sentence: str  # the whole sentence it came from, for context lookups
    #: 0 for text that always applies; 1..n for each bullet-point alternative.
    mode: int = 0


def _leading_verb(text: str) -> str:
    m = _LEADING_VERB.match(text.strip())
    return m.group(1).lower() if m else ""


def segment(desc: str) -> list[Segment]:
    """Split *desc* into labelled :class:`Segment` pieces, tagged by mode."""
    desc = _PARENS.sub(" ", desc or "")
    out: list[Segment] = []
    for mode, chunk in enumerate(_BULLET.split(desc)):
        out.extend(_segment_chunk(chunk, mode))
    return out


def _segment_chunk(chunk: str, mode: int) -> list[Segment]:
    out: list[Segment] = []
    for sentence in _SENTENCE_SPLIT.split(chunk):
        sentence = sentence.strip()
        if not sentence:
            continue

        head, sep, tail = sentence.partition(":")
        if sep and len(head) < 160:
            out.append(Segment("condition", head.strip(), False, sentence, mode))
            body = tail
        else:
            body = sentence

        optional = bool(re.search(r"\byou can\b", body, re.I))
        pre, sep, post = body.partition(";")
        if not sep:
            out.append(Segment("effect", body.strip(), optional, sentence, mode))
            continue

        verb = _leading_verb(pre)
        if verb in COST_VERBS:
            role = "cost"
        elif verb in REQUIREMENT_VERBS:
            role = "requirement"
        else:
            # Ambiguous lead ("You can discard 1 card; ...") — look deeper.
            role = "cost" if re.search(
                r"\b(discard|tribute|pay|banish|send)\b", pre, re.I
            ) else "requirement"
        out.append(Segment(role, pre.strip(), optional, sentence, mode))
        out.append(Segment("effect", post.strip(), optional, sentence, mode))
    return out
