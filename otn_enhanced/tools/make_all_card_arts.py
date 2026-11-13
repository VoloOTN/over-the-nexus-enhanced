"""Run make_card_art on every {password}.jpg dropped into the card_arts folder.

The filename is the card's password; its name and frame type come from
scratch/ygoprodeck_cache.json. Output goes to card_arts/<slug>/<slug>_*.png
(32x32 / 64x64 / artwork_full). Cards whose 32x32 already exists are skipped
unless --force is given, so this is safe to re-run.

Usage (from the repo root):
    python -m otn_enhanced.tools.make_all_card_arts
    python -m otn_enhanced.tools.make_all_card_arts --force --character
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from otn_enhanced.tools.make_card_art import FRAME_TYPES, make_card_art

ART_ROOT = Path("data/over_the_nexus/card_arts")
CACHE = Path("scratch/ygoprodeck_cache.json")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="regenerate cards that already have art")
    ap.add_argument("--character", action="store_true",
                    help="also produce the background-removed character outputs (needs --extra bgremove)")
    ap.add_argument("--build-set", action="store_true",
                    help="make the art the build needs (data.card_art.CARDS) into card_arts/implemented/, "
                         "and list the card images still missing")
    args = ap.parse_args(argv)

    cards = {c["id"]: c for c in json.loads(CACHE.read_text(encoding="utf-8"))["data"]}
    if args.build_set:
        return build_set(cards, args)
    made = skipped = failed = 0
    for jpg in sorted(ART_ROOT.glob("*.jpg")):
        card = cards.get(int(jpg.stem)) if jpg.stem.isdigit() else None
        if card is None:
            print(f"  [fail] {jpg.name}: password not in ygoprodeck cache")
            failed += 1
            continue
        if card["frameType"] not in FRAME_TYPES:
            print(f"  [fail] {jpg.name} ({card['name']}): no template for frame {card['frameType']!r}")
            failed += 1
            continue
        slug = re.sub(r"[^a-z0-9]+", "_", card["name"].lower()).strip("_")
        out_dir = ART_ROOT / slug
        if not args.force and (out_dir / f"{slug}_32x32.png").exists():
            skipped += 1
            continue
        make_card_art(jpg, out_dir, slug, frame=card["frameType"], do_character=args.character)
        print(f"  {jpg.name:14} {card['frameType']:7} -> {out_dir}")
        made += 1

    print(f"done: {made} made, {skipped} skipped (already exist), {failed} failed")
    return 1 if failed else 0


def build_set(cards: dict, args) -> int:
    """Fill card_arts/implemented/ for every card the build replaces the art of.

    Each CardArt's target card is found by its English name in card_text.CARD_TEXT,
    then by that name in the ygoprodeck cache (whose id is the image filename).
    """
    from otn_enhanced.data.card_art import ART_ROOT as BUILD_ROOT, CARDS
    from otn_enhanced.data.card_text import CARD_TEXT

    by_name = {c["name"]: c for c in cards.values()}
    by_name |= {n[1:-1]: c for n, c in by_name.items() if n.startswith('"')}   # '"Infernoble Arms - X"'
    made = done = 0
    missing, unknown = [], []
    for art in CARDS:
        if not args.force and all(art.png(s).exists() for s in ("32x32", "64x64")):
            done += 1
            continue
        e = CARD_TEXT.get(art.cid, {}).get("e")
        name = e[0] if isinstance(e, tuple) else None
        card = by_name.get(name)
        if card is None or card["frameType"] not in FRAME_TYPES:
            unknown.append(f"0x{art.cid:04X} {name or art.base}")
            continue
        src = next((p for p in (ART_ROOT / f"{card['id']}.jpg", ART_ROOT / f"{card['id']}.png") if p.exists()), None)
        if src is None:
            missing.append(f"{card['id']}.jpg  {name}")
            continue
        make_card_art(src, BUILD_ROOT / art.folder, art.base, frame=card["frameType"],
                      do_character=args.character)
        print(f"  {src.name:14} {card['frameType']:7} -> {BUILD_ROOT / art.folder}")
        made += 1

    print(f"done: {made} made, {done} already present, {len(missing)} missing, {len(unknown)} unresolvable")
    if missing:
        print(f"\nPut these card images in {ART_ROOT}/ and re-run:")
        print("\n".join(f"  {m}" for m in missing))
    if unknown:
        print("\nNot in the ygoprodeck cache (refresh it, or make these by hand with make_card_art):")
        print("\n".join(f"  {u}" for u in unknown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
