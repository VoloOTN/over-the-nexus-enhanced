"""Stage: neutralise the ten story duel puzzles (puzzle.pac / .ydq)."""
from __future__ import annotations

import struct

from otn_enhanced.rom.pac_inplace import parse_pac_v2

PUZZLE_PATH = "Data_arc_pac/puzzle.pac"

YDQ_MAGIC = b"\x59\x51"          # "YQ"
YDQ_P1_LP_OFFSET = 2
YDQ_P2_LP_OFFSET = 4             # the opponent

#: The ten story puzzles.  puzzle.pac also holds Ynull.ydq, four *wrgp*_bin.ydq
#: turbo-duel setups and lghost_rd.ydq -- the last of which is not even YQ-magic
#: and must not be parsed as a puzzle.
PUZZLE_NAMES = tuple(f"2011_tume{n:02d}.ydq" for n in range(1, 11))


def stage_puzzles(rom, cfg, log) -> int:
    """Set the opponent's life points in the ten story puzzles."""
    if not cfg.zero_puzzle_lp:
        return 0

    pac = bytearray(rom.getFileByName(PUZZLE_PATH))
    archive = parse_pac_v2(bytes(pac))

    touched = 0
    for name in PUZZLE_NAMES:
        entry = archive.by_name(name)
        if entry is None:
            log(f"  WARNING: {name} not found in puzzle.pac -- skipped")
            continue
        if bytes(pac[entry.address:entry.address + 2]) != YDQ_MAGIC:
            log(f"  WARNING: {name} is not YQ-magic -- skipped")
            continue
        p1 = int.from_bytes(pac[entry.address + YDQ_P1_LP_OFFSET:
                                entry.address + YDQ_P1_LP_OFFSET + 2], "little")
        old = int.from_bytes(pac[entry.address + YDQ_P2_LP_OFFSET:
                                 entry.address + YDQ_P2_LP_OFFSET + 2], "little")
        struct.pack_into("<H", pac, entry.address + YDQ_P2_LP_OFFSET, cfg.puzzle_lp)
        log(f"  {name}: opponent LP {old} -> {cfg.puzzle_lp} (player {p1})", detail=True)
        touched += 1

    if not cfg.dry_run:
        rom.setFileByName(PUZZLE_PATH, bytes(pac))
    return touched
