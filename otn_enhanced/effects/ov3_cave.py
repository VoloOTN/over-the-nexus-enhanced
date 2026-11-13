"""Universal (all-duel-modes) code cave carved from OVERLAY 3's own BSS.

WHY: the ov5 cave (``ov5_cave.py``) is **normal-duel-only**.  Measured 2026-07-22
by matching each overlay's decompressed image against savestate RAM:

    overlay        ml1 duel  ml2 puzzle  ml3 turbo  ml4 tag  ml5
    ov3  0x02141700   100%      100%       100%      100%   100%
    ov5  0x022C5900   100%      *3.5%*     100%      100%   100%
    ov41 0x022C5900    2.9%     *100%*      2.9%      2.9%   2.9%

In a puzzle, overlay 41 loads at 0x022C5900 and EVICTS ov5, so every ov5 stub is
inert there.  Overlay 3 -- the card-effect engine -- is resident in every mode,
which makes it the only viable host for mode-independent injected code.

HOW IT WORKS: ov3 declares data 0x152CE0 (ending 0x022943E0) then BSS 0x31520
(ending 0x022C5900 == ov5/ov41's base).  Only the lower ~40 KB of that BSS is
ever live.  We GROW ov3's file data into its own BSS and shrink bssSize by the
same amount, so the RAM FOOTPRINT END DOES NOT MOVE:

    size  0x152CE0 -> 0x180900   (+0x2DC20 of zero padding)
    bss   0x031520 -> 0x003900
    end   0x022C5900             <-- UNCHANGED

The overlay loader memcpy's data then memset's BSS.  Padding the converted range
with zeros is byte-identical to what the BSS zeroing did, so ov3's live statics
below the windows behave exactly as before.  Unlike ``ov5_cave`` this needs NO
arena-lo raise and NO heap shrink -- the ARM9 literal at 0x51ED8 is untouched.

*** ISA: the NDS ARM9 is ARMv5TE = Thumb-1 ONLY.  Injected stubs must never use
    Thumb-2 (movw/movt/b.w/cbz...).  Validate every emitted blob with
    ``effect_verify.assert_thumb1_only`` -- capstone will happily disassemble
    illegal Thumb-2 as valid. ***

STATUS: the two windows below are backed by two independent tests (0 nonzero
bytes across 92 savestates; 0 pointers into them from the ARM9 or any of the 50
overlays) but NOT yet by an in-game canary run.  See notes/ov3-cave-findings.md.
**Do not claim a CAVE3_* slot until the canary passes.**
"""
from __future__ import annotations

import struct

import ndspy.rom

# ---------------------------------------------------------------------------
# Overlay 3 geometry (EU rom.nds)
# ---------------------------------------------------------------------------
OV3_ID = 3
OV3_RAM_BASE = 0x02141700               # ov3 load address
OV3_NATIVE_DATA_LEN = 0x152CE0          # native file-image length
OV3_NATIVE_DATA_END = OV3_RAM_BASE + OV3_NATIVE_DATA_LEN    # 0x022943E0
OV3_NATIVE_BSS = 0x31520
OV3_FOOTPRINT_END = OV3_NATIVE_DATA_END + OV3_NATIVE_BSS    # 0x022C5900 == ov5/ov41 base

# Grow the file image up to here; everything above stays BSS.
OV3_NEW_DATA_END = 0x022C2000
OV3_NEW_DATA_LEN = OV3_NEW_DATA_END - OV3_RAM_BASE          # 0x180900
OV3_NEW_BSS = OV3_FOOTPRINT_END - OV3_NEW_DATA_END          # 0x3900

# The footprint must never move: it butts directly against ov5/ov41.
assert OV3_NEW_DATA_END + OV3_NEW_BSS == OV3_FOOTPRINT_END
assert OV3_NEW_DATA_LEN > OV3_NATIVE_DATA_LEN

# ---------------------------------------------------------------------------
# The two proven-clean windows inside the converted region.
#
# Each satisfies BOTH tests (see notes/ov3-cave-findings.md):
#   * 0 nonzero bytes across all 92 layout-matching savestates in
#     data/over_the_nexus/working/ (all ROM variants, all five duel modes);
#   * 0 four-byte-aligned words anywhere in the ARM9 (3 sections) or any of the
#     50 overlays hold a pointer into the range.
# The gap between them (0x022ACC00..0x022B9000) is NOT clean -- ov3 statics live
# there -- so the two windows are deliberately disjoint, not one big span.
# ---------------------------------------------------------------------------
WINDOW_PRIMARY = (0x022B9000, 0x022C2000)       # 36.0 KB
WINDOW_SECONDARY = (0x022A7000, 0x022ACC00)     # 23.0 KB
WINDOWS = (WINDOW_PRIMARY, WINDOW_SECONDARY)

CANARY_BYTE = 0xA5

# ---------------------------------------------------------------------------
# CONTROL PROBE (round 2).  Round 1 came back with both windows 100% zero in all
# five modes -- which is ambiguous: either the loader copied our bytes and the
# game then cleared its BSS, or our grown ov3 image never reached RAM at all.
# This probe discriminates.  It sits in a 75-byte run of zeros inside ov3's
# NATIVE data image (0x0226CA9D-0x0226CAE8) that stays zero in RAM across all
# five canary states -- i.e. dead padding the engine neither reads nor writes.
# It is copied by the SAME memcpy/decompress that would carry the windows.
#   probe 0xA5 + windows 0x00  => loader fine, the ENGINE clears ov3's BSS
#   probe 0x00 + windows 0x00  => our ov3 image never reaches RAM; the BSS
#                                 verdict is premature and the build is at fault
# ---------------------------------------------------------------------------
NATIVE_PROBE = (0x0226CAA0, 0x0226CAE0)         # 64 bytes, 4-aligned, inside that run

# ---------------------------------------------------------------------------
# Cave slot map -- INTENTIONALLY EMPTY until the canary run passes.
# Add CAVE3_* constants here (same comment convention ov5_cave.py uses, so
# check_allocations.py can parse them) and set CAVE3_FREE past the last one.
# ---------------------------------------------------------------------------
CAVE3_FREE = WINDOW_PRIMARY[0]          # first free address for FUTURE patches


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _load_ov3(rom: "ndspy.rom.NintendoDSRom"):
    """Return ov3's Overlay object (ndspy auto-decompresses ov.data on load)."""
    return rom.loadArm9Overlays([OV3_ID])[OV3_ID]


def _save_ov3(rom: "ndspy.rom.NintendoDSRom", ov, data: bytes, bss: int) -> None:
    """Recompress ov3 *data*, store it, and update size+bss+compressedSize in the table.

    Overlay-table entry layout: +0x00 id, +0x04 ramAddress, +0x08 ramSize,
    +0x0C bssSize, +0x10/+0x14 static-init, +0x18 fileID,
    +0x1C (flags << 24) | compressedSize.
    """
    ov.data = bytes(data)
    ov.ramSize = len(data)
    ov.bssSize = bss
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed

    tbl = rom.arm9OverlayTable
    entry = OV3_ID * 32
    struct.pack_into("<I", tbl, entry + 0x08, len(data))
    struct.pack_into("<I", tbl, entry + 0x0C, bss)
    flags_word = struct.unpack_from("<I", tbl, entry + 0x1C)[0]
    struct.pack_into("<I", tbl, entry + 0x1C,
                     ((flags_word >> 24) << 24) | (len(compressed) & 0xFFFFFF))


def _expand(rom: "ndspy.rom.NintendoDSRom"):
    """Grow ov3's data into its own BSS (idempotent).  Returns the Overlay object."""
    ov = _load_ov3(rom)
    if len(ov.data) == OV3_NEW_DATA_LEN:
        return ov                                   # already expanded by an earlier patch
    if len(ov.data) != OV3_NATIVE_DATA_LEN:
        raise AssertionError(
            f"ov3 length 0x{len(ov.data):X} is neither native 0x{OV3_NATIVE_DATA_LEN:X} "
            f"nor expanded 0x{OV3_NEW_DATA_LEN:X} -- wrong base ROM?"
        )
    if ov.ramAddress != OV3_RAM_BASE:
        raise AssertionError(f"ov3 loads at 0x{ov.ramAddress:08X}, expected 0x{OV3_RAM_BASE:08X}")
    _save_ov3(rom, ov, bytes(ov.data) + bytes(OV3_NEW_DATA_LEN - OV3_NATIVE_DATA_LEN),
              OV3_NEW_BSS)
    return _load_ov3(rom)


def _in_window(lo: int, hi: int) -> bool:
    return any(w0 <= lo and hi <= w1 for w0, w1 in WINDOWS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def install_cave(rom: "ndspy.rom.NintendoDSRom", ram_addr: int, blob: bytes,
                 *, reserve: int) -> int:
    """Write *blob* into the converted ov3 region at *ram_addr*.

    Idempotent for the expansion (the first patch in a chain grows ov3; later
    patches see it already grown and just write their own distinct slot).
    Asserts the slot is 4-aligned, lies wholly inside a proven-clean window, is
    currently zero, and that *blob* fits in *reserve*.  Operates ON the live
    *rom* object (no file save); the caller saves the ROM afterwards.
    """
    assert ram_addr % 4 == 0, f"cave 0x{ram_addr:08X} must be 4-aligned"
    assert len(blob) <= reserve, f"blob {len(blob)}B exceeds reserve 0x{reserve:X}"
    assert _in_window(ram_addr, ram_addr + reserve), (
        f"cave 0x{ram_addr:08X}+0x{reserve:X} is outside the proven-clean windows "
        f"{[(hex(a), hex(b)) for a, b in WINDOWS]}"
    )

    ov = _expand(rom)
    data = bytearray(ov.data)
    off = ram_addr - OV3_RAM_BASE
    assert all(data[off + i] == 0 for i in range(len(blob))), (
        f"ov3 cave 0x{ram_addr:08X} is not free ({len(blob)} bytes)"
    )
    data[off:off + len(blob)] = blob
    _save_ov3(rom, ov, bytes(data), OV3_NEW_BSS)
    return ram_addr


def fill_canary(rom: "ndspy.rom.NintendoDSRom", value: int = CANARY_BYTE) -> None:
    """Fill BOTH windows with *value* so an in-game run can prove they survive.

    This is the Step-1 experiment: if the engine reclaims any part of a window,
    the byte there will no longer be *value* in a savestate captured after play.
    """
    ov = _expand(rom)
    data = bytearray(ov.data)
    for lo, hi in WINDOWS:
        data[lo - OV3_RAM_BASE:hi - OV3_RAM_BASE] = bytes([value]) * (hi - lo)

    # control probe in NATIVE data -- must currently be all zeros (dead padding)
    plo, phi = NATIVE_PROBE
    assert phi <= OV3_NATIVE_DATA_END, "probe must live in ov3's NATIVE data"
    poff = plo - OV3_RAM_BASE
    assert all(data[poff + i] == 0 for i in range(phi - plo)), (
        f"native probe 0x{plo:08X}-0x{phi:08X} is not dead padding any more"
    )
    data[poff:poff + (phi - plo)] = bytes([value]) * (phi - plo)

    _save_ov3(rom, ov, bytes(data), OV3_NEW_BSS)


def geometry(rom: "ndspy.rom.NintendoDSRom") -> dict:
    """Read back ov3's live geometry from the overlay table (for verification)."""
    tbl = rom.arm9OverlayTable
    entry = OV3_ID * 32
    _, ram, size, bss = struct.unpack_from("<IIII", tbl, entry)
    comp = struct.unpack_from("<I", tbl, entry + 0x1C)[0]
    return {
        "ram": ram, "size": size, "bss": bss,
        "end": ram + size + bss,
        "compressed_size": comp & 0xFFFFFF, "flags": comp >> 24,
    }
