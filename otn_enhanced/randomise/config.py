"""Run configuration, logging and progress hooks shared by every stage."""
from __future__ import annotations

import hashlib
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

from otn_enhanced.randomise.cardprop import DEFAULT_CAPS
from otn_enhanced.randomise.packs import (
    LAST_PACK, PACK_MODE_ALL, PACK_MODE_ONLY_LAST, PACK_MODE_STOCK,
)


@dataclass
class Config:
    rom_in: str = ""
    rom_out: str = ""
    seed: str = ""

    randomise_attribute: bool = False
    randomise_race: bool = False
    randomise_level: bool = False
    randomise_synchro_level: bool = False
    randomise_atk: bool = False
    randomise_def: bool = False
    balanced: bool = False
    caps: dict = field(default_factory=lambda: dict(DEFAULT_CAPS))

    pack_mode: str = PACK_MODE_STOCK

    zero_puzzle_lp: bool = True
    puzzle_lp: int = 0

    randomise_decks: bool = False
    seed_pile_path: str = ""
    #: Parallel worker processes for deck generation.  0 = one per core.
    jobs: int = 0
    #: Rebuild only the first N decks (name-sorted).  0 = all 305.  A full run is
    #: ~4s per deck, so this exists to test a handful before committing 20 minutes.
    deck_limit: int = 0
    #: Ignore each recipe's banlist: decks are built with the flat copy limit only.
    no_banlist: bool = False

    unlock_duelists: bool = False       # placeholder -- not implemented

    dry_run: bool = False
    #: Where the full report goes.  Empty means "derive it from the output ROM";
    #: see :func:`report_path_for`.  Suppressed entirely by *no_report*.
    log_path: str = ""
    no_report: bool = False

    def touches_properties(self) -> bool:
        return any((self.randomise_attribute, self.randomise_race,
                    self.randomise_level, self.randomise_synchro_level,
                    self.randomise_atk, self.randomise_def))



def _stream(seed: str, label: str) -> random.Random:
    """A private RNG for one field, derived from the master seed.

    Each field gets its own stream and every eligible card draws from it in index
    order **whether or not that field is enabled**.  So toggling the ATK checkbox
    cannot reshuffle races, and a given seed always means the same thing.
    """
    digest = hashlib.sha256(f"{seed}\x00{label}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "little"))


def report_path_for(cfg: Config) -> str:
    """Where the report lands: alongside the output ROM, as ``<stem>_report.txt``.

    An explicit ``--log`` always wins.  A dry run writes nothing unless one was
    given -- "show me what would change" should not leave a file behind, and with
    no output ROM the only place to derive a name from is the *input*, which is
    the one file this tool must never touch.
    """
    if cfg.log_path:
        return cfg.log_path
    if cfg.dry_run or not cfg.rom_out:
        return ""
    p = Path(cfg.rom_out)
    return str(p.with_name(p.stem + "_report.txt"))


def describe(cfg: Config) -> list[str]:
    """Human-readable summary of what this run was asked to do.

    Written at the top of the report so a ROM found six months later can be
    traced back to the seed and switches that produced it.
    """
    fields = []
    if cfg.randomise_attribute:
        fields.append("Attribute")
    if cfg.randomise_race:
        fields.append("Type/Race")
    if cfg.randomise_level:
        fields.append("Level 1-12" + (" (+Synchros 2-12)"
                                      if cfg.randomise_synchro_level else ""))
    if cfg.randomise_atk:
        fields.append("ATK")
    if cfg.randomise_def:
        fields.append("DEF")

    packs = {PACK_MODE_STOCK: "as shipped",
             PACK_MODE_ALL: "all 60 unlocked",
             PACK_MODE_ONLY_LAST: f"only pack {LAST_PACK} unlocked"}[cfg.pack_mode]

    out = [
        "=" * 72,
        "Over the Nexus randomiser report",
        "=" * 72,
        f"  input ROM   : {cfg.rom_in}",
        f"  output ROM  : {cfg.rom_out or '(dry run -- nothing written)'}",
        f"  seed        : {cfg.seed}",
        f"  randomised  : {', '.join(fields) if fields else 'nothing'}",
    ]
    if cfg.balanced and (cfg.randomise_atk or cfg.randomise_def):
        caps = ", ".join(f"Lv{lo}-{hi}<={v}"
                         for (lo, hi), v in sorted(cfg.caps.items()))
        out.append(f"  balanced    : {caps}")
    out.append(f"  packs       : {packs}")
    out.append(f"  puzzles     : "
               + (f"tume01-10 opponent LP -> {cfg.puzzle_lp}"
                  if cfg.zero_puzzle_lp else "untouched"))
    if cfg.randomise_decks:
        out.append(f"  decks       : regenerated from {cfg.seed_pile_path}"
                   + (f" (first {cfg.deck_limit} only)" if cfg.deck_limit else "")
                   + (", no banlist" if cfg.no_banlist else ""))
    out.append("=" * 72)
    out.append("")
    return out


class Progress:
    """Progress reporting hook.  The base class does nothing.

    A stage with ``total == 0`` is of unknown length (the card-pool rebuild), which
    a UI can show as an indeterminate/marquee bar.
    """

    def stage(self, label: str, total: int = 0) -> None:
        """Begin a new stage."""

    def step(self, n: int = 1) -> None:
        """Advance the current stage by *n* units."""

    def finish(self) -> None:
        """All stages complete."""


def random_seed() -> str:
    """A fresh seed, for when the user has not chosen one.

    The default used to be the fixed string "20111", which meant every run that
    did not set a seed produced the *same* ROM -- not much of a randomiser.  The
    generated value is always reported and written into the report header, so a
    result stays reproducible after the fact.
    """
    return str(random.SystemRandom().randrange(10 ** 9))


class Logger:
    """Collects output for the GUI pane, the console and an optional log file."""

    def __init__(self, sink=None, verbose: bool = False):
        self.sink = sink
        self.verbose = verbose
        self.lines: list[str] = []

    def __call__(self, msg: str, detail: bool = False) -> None:
        self.lines.append(msg)
        if detail and not self.verbose:
            return
        if self.sink:
            self.sink(msg)
            return
        # A PyInstaller --windowed build launched without a console has
        # sys.stdout is None, so a bare print() would raise.  The lines are still
        # collected, and main() writes them to a log file in that case.
        if sys.stdout is None:
            return
        try:
            print(msg)
        except UnicodeEncodeError:
            sys.stdout.buffer.write(msg.encode("utf-8", "replace") + b"\n")
