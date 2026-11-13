# ponytail: KEEP -- unused by this work so far but wanted; ponytail-audit must skip this file (user decision 2026-10-29).
"""
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import ndspy.rom
import ndspy.code

# ---------------------------------------------------------------------------
# Input / output ROMs
# ---------------------------------------------------------------------------
SRC = "data/over_the_nexus/working/rom.nds"                      # clean EU (AP-fixed) base; never modified
OUT = "data/over_the_nexus/working/rom_all_packs.nds"          # patched output

# ---------------------------------------------------------------------------
# Frame math + literal-pool locations (decompressed images)
# ---------------------------------------------------------------------------
MATCH_LITERAL_OFFS = (0xA28D5, 0xA1AE2)   # arm9 decompressed offsets of the 144000 words
NEW_VAL = 0xFFFFFFFF

def _arm9_main_section(rom: "ndspy.rom.NintendoDSRom"):
    """Return ``(MainCodeFile, main_section)`` for the arm9 of *rom*.

    Works whether the arm9 is still BLZ-compressed (clean ROM) or already
    decompressed (after an earlier MainCodeFile-based patch in the chain).
    """
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    sec = next(s for s in mc.sections if s.ramAddress == rom.arm9RamAddress)
    return mc, sec


def _patch_arm9(rom: "ndspy.rom.NintendoDSRom") -> None:
    """Set every MATCH-timer literal in arm9 to *new_frames* (in place on *rom*)."""
    mc, sec = _arm9_main_section(rom)
    d = bytearray(sec.data)
    for off in MATCH_LITERAL_OFFS:
        # Replace d[off:off+4] with NEW_VAL (little-endian)
        struct.pack_into("<I", d, off, NEW_VAL)

    sec.data = bytes(d)
    rom.arm9 = mc.save()  # writes arm9 back (decompressed) with valid module params

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def main(
    *,
    src: str | Path = SRC,
    out: str | Path = OUT,
) -> None:
    """Patch the turn + match timer lengths and write the result ROM."""
    rom = ndspy.rom.NintendoDSRom.fromFile(str(src))
    _patch_arm9(rom)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rom.saveToFile(str(out))
    print(f"  wrote -> {out}")


def _parse_args(argv: list[str]) -> dict:
    opts = {"turn": 99, "match": 999, "do_verify": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--turn":
            i += 1; opts["turn"] = int(argv[i])
        elif a == "--match":
            i += 1; opts["match"] = int(argv[i])

        i += 1
    return opts


if __name__ == "__main__":
    o = _parse_args(sys.argv[1:])
    print("=" * 70)
    print("WiFi Turn/Match timer length patch")
    print("=" * 70)
    main(src=SRC, out=OUT)
    print("-" * 70)
