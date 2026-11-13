"""Rebuild the deck generator's data files, which are not distributed with the repo.

    uv run python -m otn_enhanced.tools.fetch_deckgen_inputs --rom path/to/eu_rom.nds

Makes, in order (1 and 2 are skipped if they already exist, unless --force):

  1. scratch/ygoprodeck_cache.json    YGOPRODeck card database, one download
  2. scratch/cid_to_name.json         card names by cid, read from YOUR ROM
  3. scratch/formatlibrary_decks.json tournament decklists from formatlibrary.com (~1.5 h)
  4. data/deckgen/wiki_categories.json card categories from the Yu-Gi-Oh! Fandom wiki (~3 min, 50 pages a request)

Steps 3 and 4 are slow on purpose (polite request pacing) and always run, fetching
only what is not cached yet, so an interrupted run resumes: just run the command again.
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

from otn_enhanced.deckgen import resources

YGOPRODECK = "https://db.ygoprodeck.com/api/v7/cardinfo.php?misc=yes"


def ygoprodeck(out: Path) -> None:
    req = urllib.request.Request(YGOPRODECK, headers={"User-Agent": "otn-deckgen/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"  {len(data['data'])} cards")


def cid_to_name(out: Path, rom: Path) -> None:
    from otn_enhanced.rom.konami_id_to_card_name import load_card_name_to_konami_id_map
    names: dict[str, str] = {}
    for name, cid in load_card_name_to_konami_id_map(str(rom)):
        names.setdefault(str(cid), name)          # first printing wins over alt arts
    out.write_text(json.dumps(names, ensure_ascii=False), encoding="utf-8")
    print(f"  {len(names)} names")


def formatlibrary(out: Path, force: bool) -> None:
    from otn_enhanced.deckgen.validate import tournament
    tournament.fetch_decks(force=force)                             # top 2, 150 per format, every format
    tournament.fetch_decks(per_format=None, placements=None,        # + every era-format entry
                           formats=tournament.ERA_FORMATS)


def wiki(out: Path, force: bool) -> None:
    from otn_enhanced.deckgen import wiki_categories
    if force:
        out.unlink(missing_ok=True)
    if wiki_categories.main(["--run"]) != 0:    # non-empty argv, or main() reads OUR sys.argv
        raise SystemExit("wiki_categories failed")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rom", type=Path, required=True, help="your EU (BYYP) Over the Nexus ROM")
    ap.add_argument("--force", action="store_true", help="rebuild files that already exist")
    args = ap.parse_args(argv)
    if not args.rom.is_file():
        raise SystemExit(f"ROM not found: {args.rom}")
    resources.set_rom_path(args.rom)                # the wiki step builds the card pool from it

    steps = [   # (file, maker, resumable: always re-run, it only fetches what is missing)
        (resources.ygopro_cache(), lambda p: ygoprodeck(p), False),
        (resources.cid_to_name(), lambda p: cid_to_name(p, args.rom), False),
        (resources.formatlibrary_decks(), lambda p: formatlibrary(p, args.force), True),
        (resources.wiki_categories(), lambda p: wiki(p, args.force), True),
    ]
    for path, make, resumable in steps:
        if path.exists() and not (args.force or resumable):
            print(f"skip {path} (exists)")
            continue
        print(f"make {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        make(path)
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
