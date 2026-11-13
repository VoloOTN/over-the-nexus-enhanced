"""Load the 305 shipped ``.ydc`` decks from the ROM as scorable deck states."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import ndspy.rom

from otn_enhanced.deckgen import cache
from otn_enhanced.deckgen.cardpool import ROM_PATH, _iter_paths
from otn_enhanced.deckgen.deckstate import DeckState
from otn_enhanced.deckgen.matchindex import MatchIndex
from otn_enhanced.deckgen.model import Card
from otn_enhanced.deckgen.score import Scored
from otn_enhanced.rom.pac import parse_pac
from otn_enhanced.rom.ydc_codec import decode_ydc

DECK_PAC = "Data_arc_pac/deck.pac"
SCHEMA = "deckgen.decks.v1"

### Difficulty tiers, read off the filename prefix.
###
### CORRECTION, made by reading deck contents (not by looking at model output):
### an earlier version of this file assumed `rtl*` "rental" decks were the
### weakest tier, on the reasoning that a rented deck is a beginner's deck.  That
### is backwards for Over the Nexus.  The rental decks are the game's *meta*
### builds -- rtl003 is Blackwing, rtl008 Infernity, rtl011 X-Saber, rtl013 Six
### Samurai, rtl005 Lightsworn, rtl009 Gladiator Beast -- i.e. the top 2011
### archetypes.  The `sd*` structure decks are the genuinely weak ones: 2005-era
### pre-cons built on Marauding Captain, Mother Grizzly and Pot of Greed.
###
### Rental and championship are therefore merged into one "competitive" tier
### rather than ranked against each other, because deck contents justify "both
### are strong" but give no basis for ordering them.
_TIER_NAMES = {
    0: "structure",
    1: "story-early",
    2: "story-late",
    3: "competitive",
}


#: Filenames in deck.pac sometimes carry a leading garbage byte from the
#: shift-jis decode ("qrtlr009.ydc", "(wrd012_dashguy.ydc"), so the prefix is
#: matched with a search rather than startswith.
_PREFIX = re.compile(r"(rtlr|rtl|sd|rpg|wcs|wrd)(\d+)")


def _prefix_of(name: str) -> tuple[str, int] | None:
    m = _PREFIX.search(name.lower())
    return (m.group(1), int(m.group(2))) if m else None


def tier_of(name: str) -> int:
    hit = _prefix_of(name)
    if hit is None:
        return 1
    kind, n = hit
    if kind == "sd":
        return 0
    if kind == "rpg":
        return 1 if n < 100 else 2
    return 3  # rtl / rtlr / wcs / wrd — all competitive builds


def story_number(name: str) -> int | None:
    """The ``NNN`` in ``rpgNNN_*``, which tracks story progression."""
    hit = _prefix_of(name)
    return hit[1] if hit and hit[0] == "rpg" else None


@dataclass
class StockDeck:
    """One shipped deck."""

    file_name: str
    main: list[int]
    extra: list[int]
    side: list[int]
    payload: dict = field(repr=False, default_factory=dict)

    @property
    def tier(self) -> int:
        return tier_of(self.file_name)

    @property
    def tier_name(self) -> str:
        return _TIER_NAMES[self.tier]

    @property
    def story(self) -> int | None:
        return story_number(self.file_name)

    def counts(self) -> dict[int, int]:
        out: dict[int, int] = {}
        for cid in self.main:
            out[cid] = out.get(cid, 0) + 1
        return out

    def is_turbo(self, by_cid: dict[int, Card]) -> bool:
        """True for a Turbo Duel deck.

        These are built around Speed Spells and Speed World, which cannot be
        played in a normal duel, so a normal-duel model has nothing useful to say
        about them and they are excluded from the validation corpus.

        Detected as "holds cards that are not in the playable pool at all" —
        *by_cid* is the playable pool, and the Turbo-only cards are exactly the
        ones excluded from it.
        """
        missing = sum(1 for cid in self.main if cid not in by_cid)
        return missing >= 3

    def to_state(
        self, idx: MatchIndex, scored: dict[int, Scored]
    ) -> tuple[DeckState, list[int]]:
        """Build a :class:`DeckState`; also returns cids absent from the pool."""
        state = DeckState(idx=idx)
        unknown: list[int] = []
        for cid, n in self.counts().items():
            s = scored.get(cid)
            if s is None:
                unknown.append(cid)
                continue
            state.add(s, n)
        for cid in self.extra:
            s = scored.get(cid)
            if s is None:
                unknown.append(cid)
                continue
            state.add(s, 1)
        return state, unknown


def read_ydc_cids(data: bytes) -> tuple[list[int], list[int], list[int]]:
    """Read a ``.ydc`` as raw cids: ``(main, extra, side)``.

    ``ydc_codec.decode_ydc`` is not used here because it converts ids to *names*
    through ``KONAMI_ID_TO_CARD_NAME``, which is the table with a handful of
    wrong entries (0x19BC, 0x1E6C, 0x2269, 0x19A6).  Round-tripping through it
    would silently corrupt those cards.  Format is header + three length-prefixed
    u16-LE arrays.
    """
    def u16(off: int) -> int:
        return int.from_bytes(data[off : off + 2], "little")

    pos = 8
    out: list[list[int]] = []
    for _ in range(3):
        n = u16(pos)
        pos += 2
        out.append([u16(pos + 2 * i) for i in range(n)])
        pos += 2 * n
    return out[0], out[1], out[2]


def _build() -> list[dict]:
    rom = ndspy.rom.NintendoDSRom.fromFile(str(ROM_PATH))
    path = next(p for p in _iter_paths(rom.filenames) if p.lower().endswith("deck.pac"))
    raw = bytes(rom.files[rom.filenames.idOf(path)])
    archive = parse_pac(raw, path)
    out: list[dict] = []
    for f in archive.files:
        name = f.get_clean_name()
        if not name.lower().endswith(".ydc"):
            continue
        blob = raw[f.address : f.address + f.size]
        main, extra, side = read_ydc_cids(blob)
        out.append(
            {
                "file_name": name,
                "main": main,
                "extra": extra,
                "side": side,
                "payload": decode_ydc(blob),
            }
        )
    return out


def load_stock_decks(*, force: bool = False) -> list[StockDeck]:
    """Every ``.ydc`` in ``deck.pac``, cached."""
    raw = cache.cached(SCHEMA, [ROM_PATH], _build, force=force)
    return [StockDeck(**d) for d in raw]


def card_frequency(decks: list[StockDeck]) -> dict[int, int]:
    """How often each cid appears across all stock decks — the honest null model."""
    freq: dict[int, int] = {}
    for d in decks:
        for cid in d.main:
            freq[cid] = freq.get(cid, 0) + 1
    return freq
