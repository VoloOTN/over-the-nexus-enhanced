"""WiFi Turn / Match timer length patch for Yu-Gi-Oh! WC2011 Over the Nexus (EU).

Bakes the two "freeze timer" Action Replay tweaks into the ROM as PERMANENT new
default lengths, by editing the constants the engine loads when it initialises
each timer (no AR / cheat device needed).

Both timers count down at 60 fps, so a length in minutes is  minutes * 60 * 60
frames.  The defaults below reproduce the user's request:
    * TURN timer  : 99  minutes  (default game value = 3  min = 10800  frames)
    * MATCH timer : 999 minutes  (default game value = 40 min = 144000 frames)

WHERE THE CONSTANTS LIVE (verified by disassembly against working/rom.nds, EU BYYP):

  TURN timer  -> OVERLAY 3 (the duel / card-effect overlay, file id 3)
    The current-turn-timer field is the runtime struct at RAM 0x022943F8, offsets
    +0x12C and +0x130 (these are the two addresses the AR "Freeze Turn Timer" code
    writes: 0x02294524 / 0x02294528).  Both the initial-set site (0x02148C84) and
    the per-turn reset site (0x02149338) load the start value from ONE shared
    literal-pool word at decompressed overlay-3 offset 0x8340 (= 10800), then do
    `str <val>,[base+0x12C]` and `str <val>,[base+0x130]`.  Patching that single
    word changes the turn length for every path.

  MATCH timer -> ARM9 main binary (NOT an overlay)
    The match-timer field is arm9 .bss struct 0x020B880C +0x38 (the AR "Freeze
    Match Timer" address 0x020B8844).  Two init paths set it to 40 minutes from
    two literal-pool words: arm9 decompressed offsets 0x19294 (mode-select path
    0x0201926E) and 0x172BC (init path 0x020171B0).  Both are patched.
    (A separate 15-minute mode constant at 0x19298 = 54000 is a different match
    format and is intentionally left untouched.)

All edits are 32-bit literal-pool words, so the values themselves keep their size; the
timer fields are read/written with full-word LDR/STR everywhere (verified - no 16-bit
LDRH/STRH access), so the large values are safe.

ARM9 WRITE-BACK: the arm9 is edited via ndspy.code.MainCodeFile (the same proven path
the X-Saber arm9 table edits use), NOT a raw codeCompression round-trip. The arm9 is a
multi-section module (main + ITCM/DTCM); re-BLZ-compressing it as one flat blob yields a
structurally invalid binary that boots to a WHITE SCREEN. MainCodeFile writes it back
correctly (decompressed, with valid module params), so the arm9 region grows but boots.

NOTE on display: the in-duel clock is rendered MM:SS; a 999-minute match shows a
3-digit minute count which may look cramped, but the enforced time is correct.

Usage:
    python -m otn_enhanced.system.wifi_timers
    python -m otn_enhanced.system.wifi_timers --turn 99 --match 999
    python -m otn_enhanced.system.wifi_timers --verify
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
OUT = "data/over_the_nexus/working/rom_wifi_timers.nds"          # patched output

# ---------------------------------------------------------------------------
# Frame math + literal-pool locations (decompressed images)
# ---------------------------------------------------------------------------
FPS = 60
SECONDS_PER_MINUTE = 60

OVERLAY_ID = 3
TURN_LITERAL_OFF = 0x8340          # ov3 decompressed offset of the shared 10800 word
TURN_DEFAULT_FRAMES = 10800        # stock 3:00 turn timer (before-assert guard)

MATCH_LITERAL_OFFS = (0x19294, 0x172BC)   # arm9 decompressed offsets of the 144000 words
MATCH_DEFAULT_FRAMES = 144000      # stock 40:00 match timer (before-assert guard)


def minutes_to_frames(minutes: int) -> int:
    """Convert a duration in minutes to the engine's frame count (60 fps)."""
    return minutes * SECONDS_PER_MINUTE * FPS


# ---------------------------------------------------------------------------
# ARM9 helpers
# ---------------------------------------------------------------------------
# The ARM9 main binary is NOT a single code blob -- it is a MULTI-SECTION module
# (main @0x02000000 plus ITCM/DTCM sections) wrapped by an auto-load list. A raw
# ndspy.codeCompression decompress->edit->recompress flattens all sections into one
# blob and re-BLZ-compresses it, producing a structurally invalid arm9 that boots to
# a WHITE SCREEN. We therefore use ndspy.code.MainCodeFile -- the SAME proven path
# the X-Saber arm9 table edits use (xsaber_table.py) -- which parses the real section
# layout, lets us edit the main section in place, and writes the arm9 back correctly
# (decompressed, with valid module params). The match-timer literals both live in the
# main section, so their offsets are unchanged.
def _arm9_main_section(rom: "ndspy.rom.NintendoDSRom"):
    """Return ``(MainCodeFile, main_section)`` for the arm9 of *rom*.

    Works whether the arm9 is still BLZ-compressed (clean ROM) or already
    decompressed (after an earlier MainCodeFile-based patch in the chain).
    """
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    sec = next(s for s in mc.sections if s.ramAddress == rom.arm9RamAddress)
    return mc, sec


def _patch_arm9(rom: "ndspy.rom.NintendoDSRom", new_frames: int) -> None:
    """Set every MATCH-timer literal in arm9 to *new_frames* (in place on *rom*)."""
    mc, sec = _arm9_main_section(rom)
    d = bytearray(sec.data)
    for off in MATCH_LITERAL_OFFS:
        cur = struct.unpack_from("<I", d, off)[0]
        assert cur == MATCH_DEFAULT_FRAMES, (
            f"arm9 @0x{off:X}: expected stock match value {MATCH_DEFAULT_FRAMES} "
            f"(0x{MATCH_DEFAULT_FRAMES:X}), found {cur} (0x{cur:X}) -- wrong base ROM?"
        )
        struct.pack_into("<I", d, off, new_frames)
    sec.data = bytes(d)
    rom.arm9 = mc.save()  # writes arm9 back (decompressed) with valid module params


def _patch_overlay3(rom: "ndspy.rom.NintendoDSRom", new_frames: int) -> None:
    """Set the TURN-timer literal in overlay 3 to *new_frames* (in place on *rom*)."""
    overlays = rom.loadArm9Overlays([OVERLAY_ID])
    ov = overlays[OVERLAY_ID]
    dec = bytearray(ov.data)
    cur = struct.unpack_from("<I", dec, TURN_LITERAL_OFF)[0]
    assert cur == TURN_DEFAULT_FRAMES, (
        f"ov3 @0x{TURN_LITERAL_OFF:X}: expected stock turn value {TURN_DEFAULT_FRAMES} "
        f"(0x{TURN_DEFAULT_FRAMES:X}), found {cur} (0x{cur:X}) -- wrong base ROM?"
    )
    struct.pack_into("<I", dec, TURN_LITERAL_OFF, new_frames)

    ov.data = bytes(dec)
    ov.ramSize = len(dec)
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed
    # ndspy does not propagate ramSize / compressed-size back into the overlay
    # table on its own -> write them so the loader copies the right byte count.
    tbl = rom.arm9OverlayTable
    entry = OVERLAY_ID * 32
    struct.pack_into("<I", tbl, entry + 0x08, len(dec))
    flags_word = struct.unpack_from("<I", tbl, entry + 0x1C)[0]
    struct.pack_into("<I", tbl, entry + 0x1C, ((flags_word >> 24) << 24) | (len(compressed) & 0xFFFFFF))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def main(
    *,
    turn_minutes: int = 99,
    match_minutes: int = 999,
    src: str | Path = SRC,
    out: str | Path = OUT,
) -> None:
    """Patch the turn + match timer lengths and write the result ROM."""
    turn_frames = minutes_to_frames(turn_minutes)
    match_frames = minutes_to_frames(match_minutes)

    print(f"  TURN  timer: {turn_minutes:>4d} min -> {turn_frames} frames (0x{turn_frames:X})")
    print(f"  MATCH timer: {match_minutes:>4d} min -> {match_frames} frames (0x{match_frames:X})")

    rom = ndspy.rom.NintendoDSRom.fromFile(str(src))
    _patch_arm9(rom, match_frames)          # MATCH timer (arm9)
    _patch_overlay3(rom, turn_frames)       # TURN timer (overlay 3)

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rom.saveToFile(str(out))
    print(f"  wrote -> {out}")


def verify(out: str | Path = OUT, *, turn_minutes: int = 99, match_minutes: int = 999) -> bool:
    """Re-open the patched ROM and confirm every timer literal holds the new value."""
    turn_frames = minutes_to_frames(turn_minutes)
    match_frames = minutes_to_frames(match_minutes)
    rom = ndspy.rom.NintendoDSRom.fromFile(str(out))

    ok = True
    _, sec = _arm9_main_section(rom)
    arm9 = bytes(sec.data)
    for off in MATCH_LITERAL_OFFS:
        v = struct.unpack_from("<I", arm9, off)[0]
        good = v == match_frames
        ok &= good
        print(f"    arm9 @0x{off:X} = {v} (0x{v:X})  {'OK' if good else 'FAIL'}")
    ov3 = bytes(rom.loadArm9Overlays([OVERLAY_ID])[OVERLAY_ID].data)
    v = struct.unpack_from("<I", ov3, TURN_LITERAL_OFF)[0]
    good = v == turn_frames
    ok &= good
    print(f"    ov3  @0x{TURN_LITERAL_OFF:X} = {v} (0x{v:X})  {'OK' if good else 'FAIL'}")
    print(f"  VERIFY {'PASS' if ok else 'FAIL'}")
    return ok


def _parse_args(argv: list[str]) -> dict:
    opts = {"turn": 99, "match": 999, "do_verify": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--turn":
            i += 1; opts["turn"] = int(argv[i])
        elif a == "--match":
            i += 1; opts["match"] = int(argv[i])
        elif a == "--verify":
            opts["do_verify"] = True
        i += 1
    return opts


if __name__ == "__main__":
    o = _parse_args(sys.argv[1:])
    print("=" * 70)
    print("WiFi Turn/Match timer length patch")
    print("=" * 70)
    main(turn_minutes=o["turn"], match_minutes=o["match"])
    print("-" * 70)
    verify(turn_minutes=o["turn"], match_minutes=o["match"])
