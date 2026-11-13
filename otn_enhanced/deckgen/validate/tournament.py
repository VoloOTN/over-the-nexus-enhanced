"""Tournament-winning decklists from formatlibrary.com, as a fitting corpus.

The ROM's own 305 decks are what Konami shipped for an AI to play; they are not
good decks. These are 1st/2nd place lists from real events, which is a far better
answer to "what does a strong deck look like".

The formats matter more than the count. **Tengu** is the 2011 format Over the
Nexus itself covers, and Edison / Trishula / TeleDAD / Goat all sit inside the
ROM's card pool. Anything later (HAT 2014, Wind-Up 2012, modern) is filtered out
automatically by requiring that most of a deck maps onto the pool.

Fetched once and cached; nothing here hits the network on a normal run.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from otn_enhanced.deckgen import cache
from otn_enhanced.deckgen.model import Card
from otn_enhanced.deckgen.namematch import normalize

API = "https://formatlibrary.com/api"
INDEX_CACHE = cache.REPO_ROOT / "scratch" / "formatlibrary_index.json"
DECKS_CACHE = cache.REPO_ROOT / "scratch" / "formatlibrary_decks.json"

#: Retro formats to scrape, user-specified 2026-07-30.  Used to select and
#: prioritise fetching; the real filter on training data is per-deck pool
#: coverage, so a format listed here contributes nothing unless its decks
#: actually map onto the ROM.
#:
#: Every name is the API's own ``formatName`` — checked against ``/api/formats``,
#: which returns 122 canonical names.  ``report --check-formats`` re-checks them,
#: because a renamed format fails silently: it simply fetches nothing.
ERA_FORMATS_TCG = (
    "Yugi-Kaiba", "Critter", "Treasure", "Imperial", "Android", "Joey-Pegasus",
    "Fiber", "Yata", "Scientist", "Vampire", "Warrior", "Chaos", "Cyber",
    "Chimeratech", "Perfect Circle", "Starstrike", "Trishula", "Goat", "Edison",
    "Tengu", "Wind-Up", "Reaper", "Chaos Return", "Stein", "Demise", "Trooper",
    "Zombie", "DAD Return", "Gladiator", "TeleDAD", "Cat", "Lightsworn", "Frog",
    "X-Saber", "Dino Rabbit", "Miami",
)

#: The OCG side.  All 30 are real formats; several hold only a handful of lists
#: (Exodia, Cannon, OCG Android and OCG Yata have one each), and 15 of them had
#: **zero** decks in the index as of 2026-07-30 — they are listed anyway so a
#: later re-fetch picks up anything added.
ERA_FORMATS_OCG = (
    "OCG Goat", "Destiny", "Nexus", "Tokyo Dome", "Crow", "Mirror", "Exodia",
    "OCG Treasure", "Snake", "Cannon", "OCG Imperial", "OCG Android", "Makyura",
    "OCG Yata", "Demon", "Goblin", "Envoy", "OCG Chaos", "Catapult", "Whale",
    "Victory", "Baboon", "OCG Airblade", "Armageddon", "Dark Cat", "OCG TeleDAD",
    "Dark Strike", "Lightlord", "Infernity", "Agent",
)

ERA_FORMATS = ERA_FORMATS_TCG + ERA_FORMATS_OCG

#: A deck must map this well onto the ROM pool to be usable as training data.
MIN_COVERAGE = 0.90


def _get(url: str, retries: int = 3):
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "YGO-DeckProxy/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if attempt < retries and exc.code >= 500:
                time.sleep(2 * attempt)
            else:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries:
                time.sleep(2 * attempt)
            else:
                raise


def fetch_index(*, force: bool = False) -> list[dict]:
    """The deck summary list (one cheap paginated call per 100 decks)."""
    if INDEX_CACHE.exists() and not force:
        return json.loads(INDEX_CACHE.read_text(encoding="utf-8"))
    out: list[dict] = []
    page = 1
    while True:
        batch = _get(f"{API}/decks?page={page}&limit=100")
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.03)
    INDEX_CACHE.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def fetch_decks(
    per_format: int | None = 150,
    *,
    force: bool = False,
    verbose: bool = True,
    placements: tuple[int, ...] | None = (1, 2),
    formats: tuple[str, ...] | None = None,
) -> list[dict]:
    """Full decklists from the index, filtered by placement / format / cap.

    The defaults reproduce the original behaviour — 1st and 2nd place only,
    150 per format — because that is what the shipped corpus was built with.

    ``placements=None`` takes **every entry** in an event, not just the top
    finishes.  The index holds placements out to 16th, and they are not a long
    tail: for the 25 era formats it is 5,858 further lists against the 1,443 the
    top-2 filter had kept, and 328 of those are 1st-place decks the per-format
    cap had simply cut off.  ``per_format=None`` (or 0) lifts the cap.

    Placement is recorded on every row, so a later objective can weight by it
    rather than choosing between "top cut only" and "everything".
    """
    existing: dict[int, dict] = {}
    if DECKS_CACHE.exists() and not force:
        existing = {d["id"]: d for d in json.loads(DECKS_CACHE.read_text(encoding="utf-8"))}

    index = fetch_index()
    top = [d for d in index
           if placements is None or d.get("placement") in placements]
    if formats is not None:
        top = [d for d in top if d.get("formatName") in formats]
    # Prioritise era-relevant formats, then fill with whatever else is available.
    # Within a format, better placements first, so an interrupted run still holds
    # the strongest evidence.
    top.sort(key=lambda d: (d.get("formatName") not in ERA_FORMATS,
                            d.get("formatName") or "",
                            d.get("placement") or 99))

    seen: dict[str, int] = {}
    wanted: list[dict] = []
    for d in top:
        fmt = d.get("formatName") or "?"
        if per_format and seen.get(fmt, 0) >= per_format:
            continue
        seen[fmt] = seen.get(fmt, 0) + 1
        wanted.append(d)

    todo = [d for d in wanted if d["id"] not in existing]
    if verbose:
        print(f"{len(wanted)} decks wanted, {len(existing)} cached, {len(todo)} to fetch")

    for i, summary in enumerate(todo, 1):
        try:
            full = _get(f"{API}/decks/{summary['id']}")
        except Exception as exc:  # noqa: BLE001 — one bad deck must not stop the run
            if verbose:
                print(f"  skip {summary['id']}: {exc}")
            continue
        existing[summary["id"]] = {
            "id": summary["id"],
            "format": summary.get("formatName"),
            "deck_type": summary.get("deckTypeName"),
            "event": summary.get("eventAbbreviation"),
            "placement": summary.get("placement"),
            # 'event' (a real tournament result) or 'user' (someone's submitted
            # list).  Perfectly correlated with placement: all 12,721 event rows
            # carry one, none of the 196 user rows do.  See map_to_pool.
            "origin": summary.get("origin"),
            "main": [c["name"] for c in (full.get("main") or [])],
            "extra": [c["name"] for c in (full.get("extra") or [])],
            "side": [c["name"] for c in (full.get("side") or [])],
        }
        if verbose and i % 50 == 0:
            # flush: a 6,000-deck run is 45 minutes, and buffered progress on a
            # redirected stdout means no way to tell it apart from a hang.
            print(f"  {i}/{len(todo)}", flush=True)
            DECKS_CACHE.write_text(
                json.dumps(list(existing.values()), ensure_ascii=False), encoding="utf-8"
            )
        time.sleep(0.03)

    DECKS_CACHE.write_text(
        json.dumps(list(existing.values()), ensure_ascii=False), encoding="utf-8"
    )
    if verbose:
        print(f"cached {len(existing)} decks to {DECKS_CACHE}")
    return list(existing.values())


@dataclass
class TournamentDeck:
    """A tournament deck mapped onto ROM cids."""

    id: int
    format: str
    deck_type: str
    placement: int
    main: list[int]
    extra: list[int]
    coverage: float
    unmapped: list[str] = field(default_factory=list)

    def counts(self) -> dict[int, int]:
        out: dict[int, int] = {}
        for cid in self.main:
            out[cid] = out.get(cid, 0) + 1
        return out


def map_to_pool(raw: list[dict], cards: list[Card]) -> list[TournamentDeck]:
    """Resolve modern card names onto ROM cids, keeping only well-covered decks.

    The name index is keyed on *both* the ROM's spelling and the real card name
    each cid resolved to, so a modern list saying "Laval Dual Slasher" finds the
    cid the ROM calls "Laval Twin Slayer".
    """
    from otn_enhanced.deckgen import cardpool

    idx = cardpool.index_by_name(cards)
    out: list[TournamentDeck] = []
    for d in raw:
        main: list[int] = []
        extra: list[int] = []
        unmapped: list[str] = []
        for section, dest in (("main", main), ("extra", extra)):
            for name in d.get(section, []):
                hit = idx.get(normalize(name))
                if hit is None or not hit.playable:
                    unmapped.append(name)
                    continue
                dest.append(hit.cid)
        total = len(d.get("main", [])) + len(d.get("extra", []))
        coverage = (len(main) + len(extra)) / total if total else 0.0
        if coverage < MIN_COVERAGE or len(main) < 30:
            continue
        # Drop user-submitted lists.  The corpus exists to answer "what does a
        # strong deck look like", and these are not tournament results at all --
        # `origin` is 'user', no event, no placement.  Measured against the ROM's
        # AI decks they score deck-AUC **0.876**, where every real placement band
        # from 1st to 9th+ sits at 0.949-0.957.  Keyed off placement rather than
        # `origin` so rows cached before that field was recorded still filter.
        if not (d.get("placement") or 0):
            continue
        out.append(
            TournamentDeck(
                id=d["id"],
                format=d.get("format") or "?",
                deck_type=d.get("deck_type") or "?",
                placement=d.get("placement") or 0,
                main=main,
                extra=extra,
                coverage=coverage,
                unmapped=sorted(set(unmapped)),
            )
        )
    return out


def load(cards: list[Card], *, per_format: int = 150) -> list[TournamentDeck]:
    """Cached tournament decks mapped onto the ROM pool."""
    if not DECKS_CACHE.exists():
        raise FileNotFoundError(
            f"{DECKS_CACHE} not found — run "
            "`python -m otn_enhanced.deckgen.validate.tournament fetch` first"
        )
    raw = json.loads(DECKS_CACHE.read_text(encoding="utf-8"))
    return map_to_pool(raw, cards)


def check_formats() -> list[str]:
    """Names in :data:`ERA_FORMATS` the API does not recognise.

    A typo'd or renamed format is invisible otherwise — ``fetch_decks`` just
    quietly selects nothing for it.
    """
    live = {f.get("name") for f in _get(f"{API}/formats")}
    return [f for f in ERA_FORMATS if f not in live]


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["fetch", "report"])
    ap.add_argument("--per-format", type=int, default=150,
                    help="cap per format; 0 means no cap")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--all-placements", action="store_true",
                    help="every entry in an event, not just 1st/2nd place")
    ap.add_argument("--era-only", action="store_true",
                    help="restrict to ERA_FORMATS (the retro TCG + OCG list)")
    ap.add_argument("--refresh-index", action="store_true",
                    help="re-pull the deck index before fetching")
    ap.add_argument("--check-formats", action="store_true",
                    help="report ERA_FORMATS names the API does not know")
    args = ap.parse_args(argv)

    if args.check_formats:
        bad = check_formats()
        print(f"ERA_FORMATS: {len(ERA_FORMATS)} names, "
              + (f"UNKNOWN TO THE API: {bad}" if bad else "all recognised"))
        return 1 if bad else 0

    if args.action == "fetch":
        if args.refresh_index:
            fetch_index(force=True)
        fetch_decks(
            per_format=args.per_format or None,
            force=args.force,
            placements=None if args.all_placements else (1, 2),
            formats=ERA_FORMATS if args.era_only else None,
        )
        return 0

    from collections import Counter

    from otn_enhanced.deckgen import cardpool

    cards = cardpool.playable(cardpool.load_pool())
    raw = json.loads(DECKS_CACHE.read_text(encoding="utf-8"))
    decks = load(cards, per_format=args.per_format)
    print(f"{len(decks)} of {len(raw)} fetched decks map >= {MIN_COVERAGE:.0%} onto the pool")
    for fmt, n in Counter(d.format for d in decks).most_common(70):
        print(f"  {n:5}  {fmt}")
    print("\nby placement:")
    for pl, n in sorted(Counter(d.placement for d in decks).items()):
        print(f"  {n:5}  place {pl}")
    print("\ntop deck types:")
    for t, n in Counter(d.deck_type for d in decks).most_common(15):
        print(f"  {n:5}  {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
