"""Command-line front end.  ``python -m otn_enhanced.randomiser --help``."""
from __future__ import annotations

import argparse
import sys

from otn_enhanced.randomise.cardprop import DEFAULT_CAPS
from otn_enhanced.randomise.config import Config
from otn_enhanced.randomise.packs import PACK_MODE_ALL, PACK_MODE_ONLY_LAST, PACK_MODE_STOCK
from otn_enhanced.randomise.run import run, selftest
from otn_enhanced.randomiser.paths import default_seed_pile


def _parse_caps(text: str) -> dict[tuple[int, int], int]:
    """Parse ``1-4:2000,5-6:3000,...`` into a caps table."""
    caps: dict[tuple[int, int], int] = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        band, _, limit = part.partition(":")
        lo, _, hi = band.partition("-")
        caps[(int(lo), int(hi or lo))] = int(limit)
    return caps


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="otn_randomiser",
        description="Randomise card properties in Yu-Gi-Oh! Over the Nexus (NDS).")
    p.add_argument("--rom", help="input ROM (never modified)")
    p.add_argument("--out", help="output ROM")
    p.add_argument("--seed", default="", metavar="TEXT",
                   help="master seed (any text); a random one is used and "
                        "reported if you omit it")

    p.add_argument("--attribute", action="store_true", help="randomise monster Attribute")
    p.add_argument("--race", action="store_true", help="randomise monster Type/Race")
    p.add_argument("--level", action="store_true", help="randomise monster Level (1-12)")
    p.add_argument("--synchro-level", action="store_true",
                   help="also randomise Synchro monster levels (2-12)")
    p.add_argument("--atk", action="store_true", help="randomise ATK (0-5000, step 50)")
    p.add_argument("--def", dest="def_", action="store_true",
                   help="randomise DEF (0-5000, step 50)")
    p.add_argument("--balanced", action="store_true",
                   help="cap ATK/DEF by level band")
    p.add_argument("--caps", default=None, metavar="BANDS",
                   help="override balanced caps, e.g. '1-4:2000,5-6:3000,7-8:3500'")

    packs = p.add_mutually_exclusive_group()
    packs.add_argument("--unlock-all-packs", action="store_true",
                       help="every booster pack available from the start")
    packs.add_argument("--only-pack-60", action="store_true",
                       help="only pack 60 available; 1-59 locked")

    p.add_argument("--no-puzzle-lp", action="store_true",
                   help="leave the ten duel puzzles alone")
    p.add_argument("--puzzle-lp", type=int, default=0,
                   help="opponent LP to write into tume01-10 (default 0)")

    p.add_argument("--decks", action="store_true", help="regenerate every .ydc via deckgen")
    p.add_argument("--seed-pile", default=default_seed_pile(),
                   help="path to the deck seed pile JSON")
    p.add_argument("--deck-limit", type=int, default=0, metavar="N",
                   help="rebuild only the first N decks (name-sorted); 0 = all")
    p.add_argument("--no-banlist", action="store_true",
                   help="build decks without any banlist (flat copy limit only)")
    p.add_argument("--jobs", "-j", type=int, default=0, metavar="N",
                   help="parallel processes for deck generation (default: all cores)")

    p.add_argument("--unlock-duelists", action="store_true",
                   help="placeholder: not implemented, prints why")

    p.add_argument("--dry-run", action="store_true", help="report changes, write nothing")
    p.add_argument("--log", default="", metavar="FILE",
                   help="where to write the report (default: <output ROM>_report.txt)")
    p.add_argument("--no-report", action="store_true",
                   help="do not write the report file")
    p.add_argument("-v", "--verbose", action="store_true", help="print per-card changes")
    p.add_argument("--selftest", action="store_true",
                   help="round-trip every structure in the ROM and exit")
    p.add_argument("--gui", action="store_true", help="force the GUI even with args")
    return p


def cfg_from_args(args) -> Config:
    return Config(
        rom_in=args.rom or "",
        rom_out=args.out or "",
        seed=args.seed,
        randomise_attribute=args.attribute,
        randomise_race=args.race,
        randomise_level=args.level,
        randomise_synchro_level=args.synchro_level,
        randomise_atk=args.atk,
        randomise_def=args.def_,
        balanced=args.balanced,
        caps=_parse_caps(args.caps) if args.caps else dict(DEFAULT_CAPS),
        pack_mode=(PACK_MODE_ALL if args.unlock_all_packs
                   else PACK_MODE_ONLY_LAST if args.only_pack_60
                   else PACK_MODE_STOCK),
        zero_puzzle_lp=not args.no_puzzle_lp,
        puzzle_lp=args.puzzle_lp,
        randomise_decks=args.decks,
        seed_pile_path=args.seed_pile,
        jobs=args.jobs,
        deck_limit=args.deck_limit,
        no_banlist=args.no_banlist,
        unlock_duelists=args.unlock_duelists,
        dry_run=args.dry_run,
        log_path=args.log,
        no_report=args.no_report,
    )


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.selftest:
        if not args.rom:
            sys.stderr.write("--selftest needs --rom\n")
            return 2
        return 0 if selftest(args.rom, pile_path=args.seed_pile) else 1

    if args.gui or not args.rom:
        from otn_enhanced.randomiser.gui import launch_gui
        return launch_gui(cfg_from_args(args))

    cfg = cfg_from_args(args)
    # A --windowed bundle started with arguments has no console; the report file
    # is written either way, so there is nothing extra to arrange here beyond
    # surfacing the outcome in a box.
    headless = sys.stdout is None
    try:
        log = run(cfg, verbose=args.verbose)
    except (ValueError, OSError) as exc:
        if headless:
            _popup("Randomiser failed", str(exc), error=True)
        else:
            sys.stderr.write(f"error: {exc}\n")
        return 1
    if headless:
        _popup("Randomiser finished", "\n".join(log.lines[-12:]))
    return 0


def _popup(title: str, message: str, error: bool = False) -> None:
    """Best-effort message box, for when there is no console to write to."""
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        (messagebox.showerror if error else messagebox.showinfo)(title, message)
        root.destroy()
    except Exception:
        pass

