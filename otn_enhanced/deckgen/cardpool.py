"""Build the playable card pool: ROM properties joined to real card text.

``card_prop.bin`` (inside ``Data_arc_pac/bin2.pac``) defines the pool — 4,305
8-byte records, decoded by :meth:`GameConstants.decode_entry`.  Names come from
``scratch/cid_to_name.json`` with ``konami_id_to_card_name.tsv`` as a repair
source, and effect text from ``scratch/ygoprodeck_cache.json`` via
:mod:`.namematch`.

The result is cached, so this only re-reads the 20 MB ygoprodeck dump when one
of its sources actually changes.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import ndspy.rom

from otn_enhanced.deckgen import cache
from otn_enhanced.deckgen.model import Card, card_class_of, _MONSTER_FLAGS
from otn_enhanced.deckgen.namematch import AliasTable, Resolver, normalize
from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
from otn_enhanced.rom.pac import parse_pac

from otn_enhanced.deckgen import resources

REPO_ROOT = cache.REPO_ROOT
#: Resolved via :mod:`resources` so these follow the bundle when frozen.  Only
#: read when the pool is actually rebuilt, which a bundle never does.
ROM_PATH = resources.rom_path()
YGOPRO_CACHE = resources.ygopro_cache()
CID_TO_NAME = resources.cid_to_name()
KONAMI_TSV = resources.konami_tsv()

SCHEMA = "deckgen.cards.v1"


def _iter_paths(folder, prefix: str = ""):
    """Yield every file path inside an ndspy filename tree."""
    for f in getattr(folder, "files", []) or []:
        yield f"{prefix}{f}"
    folders = getattr(folder, "folders", []) or []
    items = folders.items() if isinstance(folders, dict) else folders
    for item in items:
        if isinstance(item, tuple) and len(item) >= 2:
            yield from _iter_paths(item[1], prefix=f"{prefix}{item[0]}/")


def read_card_prop(rom_path: str | Path = ROM_PATH) -> dict[int, dict]:
    """Decode every ``card_prop.bin`` record from the ROM, keyed by cid."""
    rom = ndspy.rom.NintendoDSRom.fromFile(str(rom_path))
    pac_path = next(
        (p for p in _iter_paths(rom.filenames) if p.lower().endswith("bin2.pac")), None
    )
    if pac_path is None:
        raise RuntimeError("bin2.pac not found in ROM")
    raw = bytes(rom.files[rom.filenames.idOf(pac_path)])
    archive = parse_pac(raw, pac_path)
    entry = next(
        (f for f in archive.files if f.get_clean_name().lower() == "card_prop.bin"), None
    )
    if entry is None:
        raise RuntimeError("card_prop.bin not found in bin2.pac")
    body = raw[entry.address : entry.address + entry.size]
    out: dict[int, dict] = {}
    for i in range((entry.size - 8) // 8):
        rec = GC.decode_entry(body[8 + i * 8 : 16 + i * 8])
        out[rec["card_id"]] = rec
    return out


def _load_names() -> tuple[dict[int, str], dict[int, str]]:
    """Return ``(primary, alternate)`` cid -> name maps."""
    primary = {int(k): v for k, v in json.loads(CID_TO_NAME.read_text(encoding="utf-8")).items()}
    from otn_enhanced.rom.konami_id_to_card_name import KONAMI_ID_TO_CARD_NAME as tsv

    return primary, dict(tsv)


@dataclass
class PoolReport:
    """Build diagnostics — printed by ``cli build-pool``."""

    total: int
    by_status: dict[str, int]
    with_text: int
    stat_conflicts: int
    unresolved: list[tuple[int, str]]

    def format(self) -> str:
        lines = [
            f"card_prop records : {self.total}",
            f"joined to text    : {self.with_text}",
            "join status       : "
            + ", ".join(f"{k}={v}" for k, v in sorted(self.by_status.items())),
            f"stat conflicts    : {self.stat_conflicts} (ROM stats differ from modern errata)",
        ]
        if self.unresolved:
            lines.append(f"unresolved        : {len(self.unresolved)}")
            for cid, name in self.unresolved[:20]:
                lines.append(f"    0x{cid:04X}  {name}")
        return "\n".join(lines)


def _build() -> list[dict]:
    # resources.rom_path() rather than the ROM_PATH constant, so a caller that
    # redirected it (set_rom_path) actually gets its ROM read.  The pool encodes
    # card properties BY CID, so building it from the wrong ROM silently describes
    # cards that are not in play -- see is_randomised().
    props = read_card_prop(resources.rom_path())
    primary, alt = _load_names()
    ygopro = json.loads(YGOPRO_CACHE.read_text(encoding="utf-8"))["data"]
    resolver = Resolver(ygopro, AliasTable.load())

    cards: list[dict] = []
    for cid, prop in sorted(props.items()):
        rom_name = primary.get(cid) or alt.get(cid) or f"Unknown 0x{cid:04X}"
        res = resolver.resolve(rom_name, alt.get(cid), prop)
        entry = res.entry or {}
        enc = prop["card_type_encoded"]

        # ROM wins on stats; flag disagreement for the report.
        conflict = False
        if entry and "atk" in entry:
            conflict = (
                entry.get("atk") != prop["real_atk"]
                or entry.get("def") != prop["real_def"]
                or entry.get("level") != prop["level"]
            )

        card = Card(
            cid=cid,
            name=res.name,
            name_key=normalize(res.name),
            passcode=entry.get("id"),
            join_status=res.status,
            join_note=res.note,
            card_type_encoded=enc,
            card_type=prop["card_type"],
            card_class=card_class_of(enc),
            monster_flags=frozenset(_MONSTER_FLAGS.get(enc, ())),
            attribute=prop["attribute"] if card_class_of(enc) == "monster" else None,
            race=prop["race"] if card_class_of(enc) == "monster" else None,
            level=prop["level"] if card_class_of(enc) == "monster" else None,
            atk=prop["real_atk"],
            def_=prop["real_def"],
            st_subtype=prop["spell_trap_subtype"] if card_class_of(enc) != "monster" else None,
            desc=entry.get("desc", ""),
            archetype=entry.get("archetype"),
            stat_conflict=conflict,
        )
        cards.append(card.to_json())
    return cards


def load_pool(*, force: bool = False) -> list[Card]:
    """Return every card_prop record as a :class:`Card`, cached.

    The ROM is listed among the cache sources and read via ``resources.rom_path()``,
    so pointing that at a *randomised* ROM changes the cache key and rebuilds the
    pool against the properties actually in play.
    """
    raw = cache.cached(
        SCHEMA,
        [resources.rom_path(), YGOPRO_CACHE, CID_TO_NAME, KONAMI_TSV,
         cache.DATA_DIR / "aliases.toml"],
        _build,
        force=force,
    )
    return [Card.from_json(d) for d in raw]


def playable(cards: list[Card]) -> list[Card]:
    """Filter to cards that may appear in a normal-duel deck."""
    return [c for c in cards if c.playable]


def report(cards: list[Card]) -> PoolReport:
    status = Counter(c.join_status for c in cards)
    return PoolReport(
        total=len(cards),
        by_status=dict(status),
        with_text=sum(1 for c in cards if c.has_text),
        stat_conflicts=sum(1 for c in cards if c.stat_conflict),
        unresolved=[(c.cid, c.name) for c in cards if c.join_status == "missing"],
    )


def index_by_name(cards: list[Card]) -> dict[str, Card]:
    """Name-key -> card, for seed lookup and golden tests.

    Cards are reachable under both the name the ROM prints and the real card
    name they resolved to, so ``"Laval Twin Slayer"`` and ``"Laval Dual
    Slasher"`` both find the same cid.  The ROM name always wins a collision.
    """
    idx: dict[str, Card] = {}
    for c in cards:
        if c.join_note and c.join_status in ("alias", "stat"):
            idx.setdefault(normalize(c.join_note), c)
    for c in cards:
        idx[c.name_key] = c
    return idx


def find(cards: list[Card], seed: str | int) -> Card:
    """Look up a card by cid or by either of its names.  Raises if unknown."""
    if isinstance(seed, int):
        hit = next((c for c in cards if c.cid == seed), None)
        if hit is None:
            raise KeyError(f"no card with cid 0x{seed:04X}")
        return hit
    idx = index_by_name(cards)
    hit = idx.get(normalize(seed))
    if hit is None:
        import difflib

        near = difflib.get_close_matches(normalize(seed), list(idx), n=3, cutoff=0.6)
        hint = f"  did you mean: {[idx[n].name for n in near]}" if near else ""
        raise KeyError(f"no card named {seed!r}.{hint}")
    return hit


#: Share of text-bearing monsters whose ROM stats disagree with the real card
#: before the pool is treated as randomised.
RANDOMISED_THRESHOLD = 0.2


def is_randomised(cards: list[Card]) -> bool:
    """Have the ROM's card properties been shuffled out from under their cids?

    Everything mined from tournament decklists is keyed on **cid**, and a cid is
    only a meaningful key while it still holds the card that earned the
    statistic.  After a randomiser run "decks run three of this cid" and "Level 8
    Synchros are the good ones" are both facts about cards that used to sit
    there.  Spells and traps are untouched by the randomiser, so their per-cid
    evidence survives; monsters' does not.

    Was duplicated in ``score.score_pool`` and ``search._mined_playsets`` and
    **missing** from ``search._level_value``, which therefore kept weighting
    Synchro Levels by pre-randomisation play rate.
    """
    monsters = [c for c in cards if c.is_monster and c.has_text]
    if not monsters:
        return False
    conflicts = sum(1 for c in monsters if c.stat_conflict)
    return conflicts / len(monsters) > RANDOMISED_THRESHOLD
