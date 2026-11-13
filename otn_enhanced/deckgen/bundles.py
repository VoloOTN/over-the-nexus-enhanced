"""Curated card bundles — "A is dead without B".

Enforced during the search rather than patched up afterwards: adding an anchor
attempts an **atomic co-add** of the anchor plus its partners, so the marginal
gain is evaluated for the whole package.  A ``hard`` bundle whose partner cannot
be fitted rejects the anchor outright; a ``soft`` one is allowed but charged.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from otn_enhanced.deckgen.deckstate import DeckState
from otn_enhanced.deckgen.model import Card, Predicate
from otn_enhanced.deckgen.namematch import normalize
from otn_enhanced.deckgen.score import Scored

BUNDLES_TOML = Path(__file__).resolve().parent / "data" / "bundles.toml"


def _predicate_from_toml(raw: dict) -> Predicate:
    """Build a Predicate from the bundle file's inline table syntax."""
    def bound(v):
        return (v[0], int(v[1])) if v else None

    return Predicate(
        card_class=raw.get("card_class"),
        st_subtype=raw.get("st_subtype"),
        attribute=frozenset(raw["attribute"]) if raw.get("attribute") else None,
        race=frozenset(raw["race"]) if raw.get("race") else None,
        monster_flags=frozenset(raw["monster_flags"]) if raw.get("monster_flags") else None,
        archetype=raw.get("archetype"),
        level=bound(raw.get("level")),
        atk=bound(raw.get("atk")),
        def_=bound(raw.get("def")),
        raw=f"<bundle:{raw}>",
    )


@dataclass(frozen=True)
class Partner:
    zone: str  # main | extra
    min_copies: int
    name_key: str | None = None
    predicate: Predicate | None = None

    def matches(self, card: Card) -> bool:
        """Does *card* answer this partner slot?"""
        if self.name_key is not None:
            return (
                card.name_key == self.name_key
                or normalize(card.join_note) == self.name_key
            )
        return self.predicate is not None and self.predicate.matches(card)

    def match_cids(self, by_cid: dict[int, Card]) -> frozenset[int]:
        """Every pool cid this partner accepts, computed once.

        ``satisfied_by`` runs per bundle per score call, and the score runs tens
        of thousands of times per build: re-deriving the answer card-by-card cost
        **7.7 million ``normalize`` calls and 13s** of a 97s profile, all of it
        asking whether fixed cards match a fixed filter.  Memoised onto the
        frozen instance the same way ``Predicate.key`` does.

        Assumes the card pool is fixed for the life of the Partner, which it is:
        partners are built by ``BundleIndex.with_mined(cards)`` and bound to that
        pool, and the pool is loaded once per process.
        """
        hit = self.__dict__.get("_cids")
        if hit is None:
            hit = frozenset(
                cid for cid, card in by_cid.items() if self.matches(card)
            )
            object.__setattr__(self, "_cids", hit)
        return hit

    def satisfied_by(self, state: DeckState, by_cid: dict[int, Card]) -> int:
        pool = state.extra if self.zone == "extra" else state.copies
        cids = self.match_cids(by_cid)
        return sum(n for cid, n in pool.items() if cid in cids)


@dataclass
class Bundle:
    id: str
    anchor_key: str
    mode: str
    bonus: float
    partners: list[Partner] = field(default_factory=list)
    note: str = ""
    #: Mined from co-occurrence rather than curated.  These only ever *score* --
    #: they must never trigger an atomic co-add, because every partner has its
    #: own mined partners and the cascade drags whole unrelated archetypes in.
    #: Letting them co-add turned a Rekindling deck into a Gladiator Beast /
    #: Six Samurai / Gravekeeper's pile with zero Rekindling targets.
    mined: bool = False

    def unmet(self, state: DeckState, by_cid: dict[int, Card]) -> list[Partner]:
        return [p for p in self.partners if p.satisfied_by(state, by_cid) < p.min_copies]


@dataclass
class BundleIndex:
    bundles: list[Bundle]
    by_anchor: dict[str, list[Bundle]] = field(default_factory=dict)
    _anchor_cache: dict[str, set[int]] | None = field(default=None, repr=False)

    @classmethod
    def load(cls, path: Path = BUNDLES_TOML) -> "BundleIndex":
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        bundles: list[Bundle] = []
        for b in raw.get("bundle", []):
            partners = [
                Partner(
                    zone=pt.get("zone", "main"),
                    min_copies=int(pt.get("min_copies", 1)),
                    name_key=normalize(pt["name"]) if pt.get("name") else None,
                    predicate=_predicate_from_toml(pt["predicate"]) if pt.get("predicate") else None,
                )
                for pt in b.get("partners", [])
            ]
            bundles.append(
                Bundle(
                    id=b["id"],
                    anchor_key=normalize(b["anchor"]),
                    mode=b.get("mode", "soft"),
                    bonus=float(b.get("bonus", 1.0)),
                    partners=partners,
                    note=b.get("note", ""),
                )
            )
        idx = cls(bundles=bundles)
        for b in bundles:
            idx.by_anchor.setdefault(b.anchor_key, []).append(b)
        return idx

    @classmethod
    def with_mined(cls, cards, path: Path = BUNDLES_TOML) -> "BundleIndex":
        """Curated bundles plus packages mined from tournament co-occurrence.

        The mined half is what makes archetype packages travel together without
        anyone writing them down: Six Samurai United shows up with Gateway of the
        Six far more often than either card's play rate alone would predict, so
        picking one makes the other cheap.  Soft only — a mined correlation is
        evidence, not a rule.
        """
        idx = cls.load(path)
        try:
            from otn_enhanced.deckgen import mining

            m = mining.load(cards)
        except (FileNotFoundError, OSError, KeyError):
            return idx

        by_cid = {c.cid: c for c in cards}
        for a, b, lift, n in m.pairs:
            if a not in by_cid or b not in by_cid:
                continue
            ca, cb = by_cid[a], by_cid[b]
            bundle = Bundle(
                id=f"mined:{ca.name}+{cb.name}",
                anchor_key=ca.name_key,
                mode="soft",
                bonus=min(2.0, 0.25 * lift ** 0.5),
                partners=[Partner(zone="extra" if cb.is_extra else "main",
                                  min_copies=1, name_key=cb.name_key)],
                note=f"co-occur in {n} tournament decks, lift {lift:.1f}",
                mined=True,
            )
            idx.bundles.append(bundle)
            idx.by_anchor.setdefault(ca.name_key, []).append(bundle)
        return idx

    def for_card(self, card: Card, *, curated_only: bool = False) -> list[Bundle]:
        """Bundles anchored on *card*, matched under either of its names."""
        out = list(self.by_anchor.get(card.name_key, ()))
        if card.join_note:
            out.extend(self.by_anchor.get(normalize(card.join_note), ()))
        return [b for b in out if not (curated_only and b.mined)]

    def best_partner(
        self, partner: Partner, scored: dict[int, Scored], by_cid: dict[int, Card]
    ) -> Scored | None:
        """Highest-impact pool card that satisfies *partner*, if any exists."""
        cids = partner.match_cids(by_cid)
        cands = [
            s
            for cid in cids
            if (s := scored.get(cid)) is not None
            and (s.card.is_extra if partner.zone == "extra" else not s.card.is_extra)
        ]
        return max(cands, key=lambda s: s.impact, default=None)

    def _anchor_cids(self, by_cid: dict[int, Card]) -> dict[str, set[int]]:
        """anchor key -> cids, cached.

        ``adjust`` used to rescan every bundle against the whole deck on each
        call.  With mined bundles that is ~400 x 40 comparisons per deck score,
        and the score runs tens of thousands of times per generate() — it turned
        a 20-second build into a ten-minute one.
        """
        if self._anchor_cache is None:
            cache: dict[str, set[int]] = {}
            for cid, card in by_cid.items():
                for key in {card.name_key, normalize(card.join_note)}:
                    if key in self.by_anchor:
                        cache.setdefault(key, set()).add(cid)
            self._anchor_cache = cache
        return self._anchor_cache

    def adjust(self, state: DeckState, by_cid: dict[int, Card], p_bundle: float) -> tuple[float, list[str]]:
        """Bonus for complete bundles, penalty for unmet soft ones."""
        total = 0.0
        debt: list[str] = []
        anchors = self._anchor_cids(by_cid)
        present = set(state.copies) | set(state.extra)
        # Which anchor keys are actually in the deck.  Iterating all ~400 mined
        # bundles per score call cost 2.1s of a 23s build; almost none of them
        # are ever anchored.
        live = {k for k, cids in anchors.items() if present & cids}
        if not live:
            return 0.0, []
        for b in self.bundles:
            if b.anchor_key not in live:
                continue
            if not (anchors.get(b.anchor_key, ()) and present & anchors[b.anchor_key]):
                continue
            missing = b.unmet(state, by_cid)
            if not missing:
                total += b.bonus
            elif not b.mined:
                # A mined pair not being present is normal; only a curated
                # "dead without this" bundle is a debt.
                total -= p_bundle * len(missing)
                debt.append(b.id)
        return total, debt
