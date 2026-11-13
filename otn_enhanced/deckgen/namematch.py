"""Resolve a ROM card name to its real ygoprodeck entry.

Two things make this non-trivial:

* Neither ROM name table is correct on its own.  ``scratch/cid_to_name.json``
  matches ``card_prop.bin`` exactly but carries Shift-JIS mojibake on ~16 rows;
  ``konami_id_to_card_name.tsv`` has clean UTF-8 but is wrong on a handful of
  names (0x19BC is Proto-Cyber Dragon, not Cyber Dragon).  We take the first and
  repair from the second.
* Over the Nexus shipped **pre-TCG-release translations** of OCG cards, later
  renamed: ``Laval Twin Slayer`` -> ``Laval Dual Slasher``, ``Crimson Mefist``
  -> ``Blood Mefist``, ``Kinetic Soldier`` -> ``Cipher Soldier``.

Resolution order, most to least trustworthy — the first hit wins:

1. exact normalized name,
2. the TSV's alternate spelling, normalized,
3. an explicit entry in ``data/aliases.toml``,
4. an exact **ROM-stat** match (ATK/DEF/level/attribute/race) — this resolves
   every remaining monster and is *derived*, not typed,
5. unresolved: the card stays in the pool with no effect text.

Only Spells and Traps ever need step 3, because they have no stats to match on.
"""

from __future__ import annotations

import difflib
import re
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
ALIASES_TOML = DATA_DIR / "aliases.toml"

# Card types that carry no ATK/DEF/level and so cannot use the stat matcher.
_STATLESS_TYPES = frozenset({21, 27, 29})  # Token, Spell Card, Trap Card

_ABBREV = ((re.compile(r"\bb\."), "black"),)  # "Red-Eyes B. Dragon"


#: Memo for :func:`normalize`.  Its domain is the card pool's names and
#: join_notes — a few thousand distinct strings — but the deck search calls it
#: from inside ``Partner.satisfied_by``, once per deck card per bundle partner
#: per score.  Profiled at **7.9 million calls and 53s of a 164s build**, a third
#: of the total, all of it recomputing answers it had already produced.  A plain
#: dict beats lru_cache here: str keys, no eviction wanted, no thread safety
#: needed, and the miss path is the whole original function.
_NORMALIZED: dict[str, str] = {}

_PUNCT = re.compile(r"[^a-z0-9]+")


def normalize(name: str) -> str:
    """Fold a card name to a join key.

    Strips diacritics and non-ASCII (which also neutralises the Shift-JIS
    mojibake), lowercases — which alone reconciles ``Elemental Hero`` with
    ygoprodeck's ``Elemental HERO`` — expands ``B.`` to ``Black``, and collapses
    all punctuation to single spaces.

    Memoised; pure, so the cache can never go stale.
    """
    hit = _NORMALIZED.get(name)
    if hit is not None:
        return hit
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    for pat, repl in _ABBREV:
        s = pat.sub(repl, s)
    out = _PUNCT.sub(" ", s).strip()
    _NORMALIZED[name] = out
    return out


@dataclass(frozen=True)
class AliasTable:
    alias: dict[str, str]
    exclude: dict[str, str]
    unresolved: dict[str, str]

    @classmethod
    def load(cls, path: Path = ALIASES_TOML) -> "AliasTable":
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        return cls(
            alias={normalize(k): v for k, v in raw.get("alias", {}).items()},
            exclude={normalize(k): v for k, v in raw.get("exclude", {}).items()},
            unresolved={normalize(k): v for k, v in raw.get("unresolved", {}).items()},
        )


@dataclass
class Resolution:
    """Outcome of resolving one cid."""

    name: str  # the display name (ROM, mojibake repaired)
    entry: dict | None  # the matched ygoprodeck record
    status: str  # exact | tsv | alias | stat | speed_spell | excluded | missing
    note: str = ""


class Resolver:
    """Resolve ROM names against a ygoprodeck card list."""

    def __init__(self, ygopro_cards: list[dict], aliases: AliasTable | None = None):
        self.aliases = aliases or AliasTable.load()
        self.by_name: dict[str, dict] = {}
        for c in ygopro_cards:
            self.by_name.setdefault(normalize(c["name"]), c)
        # (atk, def, level, attribute, race) -> candidate records
        self.by_stats: dict[tuple, list[dict]] = {}
        for c in ygopro_cards:
            if "atk" not in c:
                continue
            key = (c["atk"], c.get("def"), c["level"], c["attribute"], c["race"])
            self.by_stats.setdefault(key, []).append(c)

    def resolve(self, rom_name: str, tsv_name: str | None, prop: dict) -> Resolution:
        """Resolve one card.  *prop* is a ``decode_entry`` dict from card_prop.bin."""
        # Prefer the TSV spelling when the primary name contains mojibake, since
        # the replacement character means the primary name lost information.
        display = rom_name
        if tsv_name and ("�" in rom_name or not rom_name.isascii()):
            if tsv_name.isascii():
                display = tsv_name

        key = normalize(rom_name)
        if rom_name.startswith("Speed Spell -") or key in self.aliases.exclude:
            why = self.aliases.exclude.get(key, "turbo duel only")
            return Resolution(display, None, "excluded", why)

        hit = self.by_name.get(key)
        if hit is not None:
            return Resolution(display, hit, "exact")

        if tsv_name:
            hit = self.by_name.get(normalize(tsv_name))
            if hit is not None:
                return Resolution(display, hit, "tsv")

        for k in (key, normalize(tsv_name or "")):
            target = self.aliases.alias.get(k)
            if target:
                hit = self.by_name.get(normalize(target))
                if hit is not None:
                    return Resolution(display, hit, "alias", target)

        if key in self.aliases.unresolved:
            return Resolution(display, None, "missing", self.aliases.unresolved[key])

        hit = self._by_stats(display, tsv_name, prop)
        if hit is not None:
            return Resolution(display, hit, "stat", hit["name"])

        return Resolution(display, None, "missing", "no candidate")

    def _by_stats(self, rom_name: str, tsv_name: str | None, prop: dict) -> dict | None:
        """Match a monster on its exact ROM stat line, disambiguating by name.

        Now a **fallback only** — every card it used to resolve is recorded in
        data/aliases.toml, so the normal path never reaches here.  That matters
        because this lookup keys on the very properties a randomiser rewrites:
        shuffle ATK/DEF/level/attribute/race and these cards would silently lose
        their effect text.  Kept for a ROM whose name table drifts further.

        To regenerate the baked entries, clear the stat-matched block in
        aliases.toml and dump [(c.name, c.join_note) for c in load_pool()
        if c.join_status == "stat"] against a pristine ROM.
        """
        if prop.get("card_type_encoded") in _STATLESS_TYPES:
            return None
        key = (
            prop["real_atk"],
            prop["real_def"],
            prop["level"],
            prop["attribute"],
            prop["race"],
        )
        cands = self.by_stats.get(key)
        if not cands:
            return None
        if len(cands) == 1:
            return cands[0]
        # Several cards share the stat line — pick the closest name.  A stat
        # match already proves it is one of these, so no cutoff is needed.
        keys = [normalize(c["name"]) for c in cands]
        best = difflib.get_close_matches(normalize(tsv_name or rom_name), keys, n=1, cutoff=0.0)
        if not best:
            return None
        return next(c for c in cands if normalize(c["name"]) == best[0])
