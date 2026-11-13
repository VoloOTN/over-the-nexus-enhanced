"""Hard deck legality, checked on every candidate.

Soft preferences (ratios, curve) are penalties in :mod:`.deckscore`; the rules
here are absolute, and a deck that violates one is never emitted.  The final
check also pre-flights ``patch_bulk_ydcs.YDC.validate`` so a generated deck
cannot fail at patch time.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from otn_enhanced.deckgen.deckstate import DeckState
from otn_enhanced.deckgen.model import Card
from otn_enhanced.deckgen.params import Params, default
from otn_enhanced.deckgen.score import Scored


#: Section name in the baked lists -> copies that section allows.
_SECTION_MAX = {"Forbidden": 0, "Limited": 1, "Semi-Limited": 2}

_BANLISTS: dict | None = None


def _banlists() -> dict:
    """The baked Forbidden/Limited lists, loaded once."""
    global _BANLISTS
    if _BANLISTS is None:
        from otn_enhanced.deckgen.bake_banlists import DATA_PATH

        _BANLISTS = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return _BANLISTS


@dataclass
class Limits:
    """Copy limits, either the flat maximum or an in-ROM Forbidden/Limited list."""

    default_max: int
    per_cid: dict[int, int]
    name: str = "none"

    def max_copies(self, cid: int) -> int:
        return self.per_cid.get(cid, self.default_max)

    @classmethod
    def flat(cls, n: int = 3) -> "Limits":
        return cls(default_max=n, per_cid={}, name="none (3 of anything)")

    def forbidding(self, cids, label: str = "anti-seed") -> "Limits":
        """A copy of these limits with *cids* banned outright.

        Anti-seeds are implemented as a zero copy limit rather than as a filter
        somewhere in the search, because "0 copies allowed" is a rule the whole
        pipeline already obeys: every path that can put a card into a deck —
        beam growth, bundle auto-fill, the Extra Deck fill, bootstrap swaps, the
        seed-holdout ranking — goes through ``legal_addition`` or
        ``max_copies``.  A new filter would have to be threaded into all six and
        would silently miss the next one added.

        :class:`MonsterFilter` rides the same mechanism for the same reason, so
        *label* names whichever of the two put the ban there — it only shows up
        in ``name``, which the CLI prints.
        """
        cids = frozenset(cids)
        if not cids:
            return self
        per = dict(self.per_cid)
        for cid in cids:
            per[cid] = 0
        return Limits(
            default_max=self.default_max,
            per_cid=per,
            name=f"{self.name} + {len(cids)} {label}(s)",
        )

    @staticmethod
    def available() -> list[str]:
        """Every Forbidden/Limited list name, oldest first."""
        return list(_banlists()["lists"])

    @classmethod
    def named(cls, list_name: str = "limit201009", default_max: int = 3) -> "Limits":
        """One of the ROM's six Forbidden/Limited lists, from baked data.

        Reads ``data/banlists.json`` rather than the ROM.  The lists are static —
        they ship inside the image and never change — but going to the ROM meant
        opening the whole NDS file with ndspy, locating ``bin.pac``, parsing the
        archive and decoding an entry on **every invocation**: 0.24s a run, and a
        hard dependency on the ROM being present just to know that Pot of Greed
        is Forbidden.  Regenerate with ``-m deckgen.bake_banlists``.
        """
        lists = _banlists()["lists"]
        if list_name not in lists:
            raise ValueError(
                f"unknown banlist {list_name!r}; available: {', '.join(lists)}"
            )
        per: dict[int, int] = {}
        for section, allowed in _SECTION_MAX.items():
            for cid in lists[list_name].get(section, ()):
                per[int(cid)] = allowed
        return cls(default_max=default_max, per_cid=per, name=list_name)

    @classmethod
    def from_rom(cls, list_name: str = "limit201009", default_max: int = 3) -> "Limits":
        """Read one of the six Forbidden/Limited lists straight from the ROM.

        Kept as the source of truth that :meth:`named` is baked from — see
        ``bake_banlists`` — and as the fallback for a ROM whose lists have been
        edited without re-baking.  Prefer :meth:`named`.
        """
        import json

        import ndspy.rom

        from otn_enhanced.deckgen.cardpool import ROM_PATH, _iter_paths
        from otn_enhanced.rom.limit_codec import decode_limit
        from otn_enhanced.rom.pac import parse_pac

        rom = ndspy.rom.NintendoDSRom.fromFile(str(ROM_PATH))
        path = next(p for p in _iter_paths(rom.filenames) if p.lower().endswith("bin.pac"))
        raw = bytes(rom.files[rom.filenames.idOf(path)])
        archive = parse_pac(raw, path)
        entry = next(
            f for f in archive.files if f.get_clean_name().lower() == f"{list_name}.bin"
        )
        text, _ = decode_limit(raw[entry.address : entry.address + entry.size])
        data = json.loads(text)
        per: dict[int, int] = {}
        for cid in data.get("Forbidden", []):
            per[int(cid)] = 0
        for cid in data.get("Limited", []):
            per[int(cid)] = 1
        for cid in data.get("Semi-Limited", []):
            per[int(cid)] = 2
        return cls(default_max=default_max, per_cid=per, name=list_name)


def _fold(s: str) -> str:
    """Loose key for matching a user-typed Type/Attribute to the pool's spelling.

    ``beast warrior``, ``Beast-Warrior`` and ``BEASTWARRIOR`` are the same
    request; nobody should have to reproduce the ROM's hyphenation to filter
    on it.
    """
    return re.sub(r"[^a-z0-9]", "", s.casefold())


@dataclass(frozen=True)
class MonsterFilter:
    """Which monsters a build may consider at all.

    Yu-Gi-Oh! "Type" (Warrior, Dragon, Sea Serpent) is :attr:`Card.race` in this
    codebase and "Attribute" (DARK, FIRE) is :attr:`Card.attribute`; the CLI
    spells them ``--allowed-types`` and ``--allowed-attributes`` because that is
    what they are called on the card.

    Values *within* one flag are a disjunction and the two flags are a
    conjunction, so ``--allowed-types Warrior Beast-Warrior --allowed-attributes
    DARK`` means "DARK Warriors and DARK Beast-Warriors".  An unset flag
    constrains nothing.

    **Spells and Traps are never filtered.**  A Type/Attribute says nothing
    about them, and a deck barred from holding any would break the ratio rules
    in :func:`violations` outright.

    **Seeds outrank the filter.**  This object describes what the search may be
    *offered*, not what the deck may contain, so a seed the filter excludes is
    still built around — see the exemption in :func:`search.generate`.

    :attr:`extra_deck` scopes the filter to the Extra Deck, and the two settings
    answer genuinely different requests:

    * **on** (the default) — the Extra Deck obeys the filter too.  Required for
      any deck whose payoff counts *Types across the whole Graveyard*: Solidarity
      gives +800 ATK only "if you have only 1 Type of monster in your GY", and a
      single off-Type Synchro dying once turns it off for the rest of the duel.
      An Extra Deck monster reaches the GY as readily as a main-deck one, so for
      those decks it is not a cosmetic slot — it is the combo.
    * **off** — Extra Deck monsters are exempt, so the Extra Deck fills to a
      full 15 from the whole pool.  The right answer when the Type restriction
      is about the *engine* (search targets, a Level-modifying archetype) rather
      than about what ends up in the Graveyard.

    It matters because a narrow Type cannot fill 15 slots under the strict
    setting: the ROM ships 3 Sea Serpent and 4 Fish Extra Deck monsters in total.
    """

    races: frozenset[str] | None = None
    attributes: frozenset[str] | None = None
    #: Apply the filter to Extra Deck monsters as well as main-deck ones.
    extra_deck: bool = True

    def __bool__(self) -> bool:
        return self.races is not None or self.attributes is not None

    def allows(self, card: Card) -> bool:
        """May *card* be considered for a deck under this filter?"""
        if not card.is_monster:
            return True
        if card.is_extra and not self.extra_deck:
            return True
        if self.races is not None and card.race not in self.races:
            return False
        if self.attributes is not None and card.attribute not in self.attributes:
            return False
        return True

    def rejected_cids(self, cards) -> set[int]:
        """Every cid this filter excludes — fed straight to :meth:`Limits.forbidding`."""
        return {c.cid for c in cards if not self.allows(c)}

    def describe(self) -> str:
        parts = []
        if self.races is not None:
            parts.append("types " + "/".join(sorted(self.races)))
        if self.attributes is not None:
            parts.append("attributes " + "/".join(sorted(self.attributes)))
        if not parts:
            return "unconstrained"
        scope = "main + extra deck" if self.extra_deck else "main deck only"
        return f"{' and '.join(parts)} ({scope})"

    @classmethod
    def parse(
        cls, cards, *, races=None, attributes=None, extra_deck: bool = True
    ) -> "MonsterFilter":
        """Build a filter from user-typed names, validated against *cards*.

        Canonicalised against the vocabulary the **pool actually holds** rather
        than against :mod:`game_constants`, so this stays correct for either
        card_prop era and for a randomised ROM whose Types have been reshuffled.
        A name that matches nothing is an error listing what is available — a
        typo that silently narrowed the pool to nothing would otherwise surface
        much later as an unexplained "not enough monsters" build failure.
        """

        def canon(values, field: str, label: str) -> frozenset[str] | None:
            if values is None:
                return None
            known: dict[str, str] = {}
            for c in cards:
                v = getattr(c, field)
                if v:
                    known.setdefault(_fold(v), v)
            out, bad = set(), []
            for raw in values:
                hit = known.get(_fold(raw))
                if hit is None:
                    bad.append(raw)
                else:
                    out.add(hit)
            if bad:
                raise ValueError(
                    f"unknown monster {label}: {', '.join(repr(b) for b in bad)}; "
                    f"available: {', '.join(sorted(set(known.values())))}"
                )
            return frozenset(out)

        return cls(
            races=canon(races, "race", "Type"),
            attributes=canon(attributes, "attribute", "Attribute"),
            extra_deck=extra_deck,
        )


def legal_addition(
    state: DeckState,
    cand: Scored,
    k: int,
    limits: Limits,
    p: Params | None = None,
    *,
    reserve_monsters: bool = True,
) -> bool:
    """Can *k* copies of *cand* be added without breaking a hard rule?

    *reserve_monsters* controls only the forward-looking part of the rule set:
    the slots held back so the monster minimum is still reachable.  That
    reservation is right while the search still has picks to make and wrong once
    it has stopped making them — a deck stuck below the minimum with no legal
    monster left would otherwise refuse every Spell and Trap too and be emitted
    short.  :func:`search.force_fill_main` turns it off for exactly that case;
    nothing on the normal search path should.
    """
    p = p or default()
    if not state.can_add(cand, k, limits.max_copies(cand.cid)):
        return False
    if cand.card.is_extra:
        return sum(state.extra.values()) + k <= int(p["deck.extra_size"])
    size = int(p["deck.size"])
    if state.main_total + k > size:
        return False
    if cand.card.is_monster:
        return state.monsters + k <= int(p["deck.max_monsters"])

    # Non-monsters were only bounded by the deck size, so the trap cap and the
    # monster *minimum* were checked after the fact by violations() and the deck
    # got emitted illegal anyway.  A thin engine (or randomised card properties,
    # which shrink every predicate's match set) reliably produced 10 monsters and
    # 15 traps in a 40-card deck.
    if cand.card.card_class == "trap" and state.traps + k > int(p["deck.max_traps"]):
        return False
    if not reserve_monsters:
        return True
    # Reserve the slots still needed to reach the monster minimum.
    shortfall = max(0, int(p["deck.min_monsters"]) - state.monsters)
    return state.main_total + k <= size - shortfall


def violations(
    state: DeckState, by_cid: dict[int, Card], p: Params | None = None, limits: Limits | None = None
) -> list[str]:
    """Every hard-rule breach in a finished deck; empty means legal."""
    p = p or default()
    limits = limits or Limits.flat(int(p["deck.max_copies"]))
    out: list[str] = []

    size = int(p["deck.size"])
    if state.main_total != size:
        out.append(f"main deck has {state.main_total} cards, expected {size}")
    extra = sum(state.extra.values())
    if extra > int(p["deck.extra_size"]):
        out.append(f"extra deck has {extra} cards, max {p['deck.extra_size']}")

    for cid, n in list(state.copies.items()) + list(state.extra.items()):
        cap = limits.max_copies(cid)
        if n > cap:
            name = by_cid[cid].name if cid in by_cid else hex(cid)
            out.append(f"{name}: {n} copies, limit {cap}")

    for cid in state.copies:
        card = by_cid.get(cid)
        if card is not None and card.is_extra:
            out.append(f"{card.name} is an Extra Deck card but is in the main deck")
    for cid in list(state.copies) + list(state.extra):
        card = by_cid.get(cid)
        if card is not None and not card.playable:
            out.append(f"{card.name} is not playable in a normal duel ({card.join_note})")

    lo, hi = int(p["deck.min_monsters"]), int(p["deck.max_monsters"])
    if not lo <= state.monsters <= hi:
        out.append(f"{state.monsters} monsters, expected {lo}-{hi}")
    if state.traps > int(p["deck.max_traps"]):
        out.append(f"{state.traps} traps, max {p['deck.max_traps']}")
    return out
