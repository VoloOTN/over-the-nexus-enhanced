"""NDS ROM overlay I/O helpers for overlay0003.

Provides a clean API to extract, decompress, recompress, and reinsert
overlay 3 from/into a Yu-Gi-Oh! NDS ROM file.

Typical round-trip::

    rom, overlay_data = load_overlay3("game.nds")
    # ... modify overlay_data ...
    save_overlay3(rom, overlay_data, "modified_game.nds")
"""

from __future__ import annotations

from pathlib import Path

import ndspy.rom


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OVERLAY_ID = 3
RAM_BASE = 0x02141700


# ---------------------------------------------------------------------------
# Extract / load
# ---------------------------------------------------------------------------

def load_overlay3(nds_path: str | Path) -> tuple["ndspy.rom.NintendoDSRom", bytes]:
    """Load a .nds ROM and return ``(rom, decompressed_overlay3_bytes)``.

    The returned *rom* object is kept open so it can be passed to
    :func:`save_overlay3` later.
    """
    rom = ndspy.rom.NintendoDSRom.fromFile(str(nds_path))
    overlays = rom.loadArm9Overlays([OVERLAY_ID])
    ov = overlays[OVERLAY_ID]
    # ndspy auto-decompresses on load; ov.data is already decompressed
    return rom, bytes(ov.data)


# ---------------------------------------------------------------------------
# Recompress / save
# ---------------------------------------------------------------------------

def save_overlay3(
    rom: "ndspy.rom.NintendoDSRom",
    decompressed: bytes | bytearray,
    out_path: str | Path,
) -> None:
    """Recompress *decompressed* overlay data and save the full ROM.

    *rom* should be the same object returned by :func:`load_overlay3`.
    """
    import struct

    overlays = rom.loadArm9Overlays([OVERLAY_ID])
    ov = overlays[OVERLAY_ID]
    ov.data = bytes(decompressed)
    ov.ramSize = len(decompressed)
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed

    # ndspy keeps the arm9 overlay table as a separate bytearray and does NOT
    # automatically propagate ov.ramSize / new compressed size back into it.
    # Without this writeback the loader copies the original (smaller) ramSize
    # bytes from the recompressed file -> instant crash on overlay use.
    tbl = rom.arm9OverlayTable
    entry = OVERLAY_ID * 32
    struct.pack_into("<I", tbl, entry + 0x08, len(decompressed))  # ramSize
    flags_word = struct.unpack_from("<I", tbl, entry + 0x1C)[0]
    flags = flags_word >> 24
    csz = len(compressed) & 0xFFFFFF
    struct.pack_into("<I", tbl, entry + 0x1C, (flags << 24) | csz)

    rom.saveToFile(str(out_path))
