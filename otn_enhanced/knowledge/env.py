"""Oracle loading for the knowledge-base proof harness.

A *proof* checks a claimed fact against one of four oracles, chosen by the
claimed address:

  * ``arm9``      — ARM9 main section, base 0x02000000.  Read from the stock base
                    ROM by :mod:`otn_enhanced.rom.stock` (decompressed main section:
                    file offset == addr - 0x02000000).
  * ``ov3``       — overlay 3, base 0x02141700, also from the stock base ROM
                    (file offset == addr - 0x02141700).
  * ``ov5``       — overlay 5 cave region, base 0x022C5900.  NOT committed; loaded
                    from ``data/over_the_nexus/working/rom.nds`` if present, else
                    ``None`` -> ov5 proofs report UNVERIFIED (SKIP).
  * ``savestate`` — live duel RAM.  A ``.ml*`` melonDS savestate, parsed with the
                    version-independent auto-detect from ``librarian_recorder``.
                    Optional (``--savestate PATH``, default the on-disk
                    ``rom_all_patches.ml1``); absent -> RAM proofs SKIP.

arm9/ov3 always come from the stock base ROM (never committed: game data), so
the KB needs the user's own dump to run; ov5 and savestate facts degrade to
UNVERIFIED when their source is missing, never to FAIL.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Oracle address ranges (load bases + committed-image lengths).
# ---------------------------------------------------------------------------
from otn_enhanced.effects.common import ARM9_BASE
OV3_BASE = 0x02141700
OV5_BASE = 0x022C5900          # ov5_cave.OV5_RAM_BASE
OV5_NATIVE_END = 0x0239A120    # ov5_cave.OV5_NATIVE_END; also the duel arena-lo

# Repo layout: this file is <root>/otn_enhanced/knowledge/env.py
_ROOT = Path(__file__).resolve().parents[2]


def _ov5_reserve(default: int = 0x4000) -> int:
    """How many bytes ``ov5_cave.py`` appends to overlay 5 (its ``RESERVE``).

    PARSED rather than duplicated.  This ceiling used to be hardcoded here AND
    in ``check_allocations.py``, and a stale copy is silent but nasty: every
    cave address above the old ceiling falls outside ``oracle_name``'s ranges,
    so ov5 proofs report UNVERIFIED (oracle missing) instead of reading the
    image, and the allocation guard stops flagging out-of-region slots.
    ``ov5_cave.py`` is the single source of the cave's size.
    """
    src = _ROOT / "otn_enhanced" / "effects" / "ov5_cave.py"
    try:
        text = src.read_text(encoding="utf-8")
    except OSError:
        return default
    m = re.search(r"^RESERVE\s*=\s*(0x[0-9A-Fa-f]+|\d+)", text, re.M)
    return int(m.group(1), 0) if m else default


OV5_END = OV5_NATIVE_END + _ov5_reserve()   # == OV5_RAM_BASE + OV5_NEW_LEN
DEFAULT_ROM = _ROOT / "data" / "over_the_nexus" / "working" / "rom.nds"
# The default is an "after Synchro Summon" state with a live duel (the .ml1 of a
# pair is often a menu/pre-load frame with no overlay 3 resident); auto-detect
# needs the 0x021A25A0 anchor, which only exists mid-duel.
DEFAULT_SAVESTATE = _ROOT / "data" / "over_the_nexus" / "working" / "rom_all_patches.ml2"


class SaveState:
    """A parsed melonDS savestate with version-independent RAM addressing.

    The main-RAM file offset is auto-detected via
    :func:`librarian_recorder.find_ram_offset` (the 0x021A25A0 anchor), so this
    works regardless of the melonDS build the state was captured with.  Only
    valid when a duel is loaded in the state (the anchor lives in overlay 3).
    """

    RAM0 = 0x02000000

    def __init__(self, path: Path):
        from otn_enhanced.tools.librarian_recorder import find_ram_offset
        self.path = Path(path)
        self.buf = self.path.read_bytes()
        self.off0 = find_ram_offset(self.buf)   # raises SystemExit if no duel loaded

    def _o(self, addr: int) -> int:
        return self.off0 + (addr - self.RAM0)

    def u8(self, addr: int) -> int:
        return self.buf[self._o(addr)]

    def u16(self, addr: int) -> int:
        return struct.unpack_from("<H", self.buf, self._o(addr))[0]

    def u32(self, addr: int) -> int:
        return struct.unpack_from("<I", self.buf, self._o(addr))[0]

    def read(self, addr: int, n: int) -> bytes:
        o = self._o(addr)
        return self.buf[o:o + n]


@dataclass
class Env:
    """The oracles a proof runs against.  ``ov5``/``ss`` may be ``None``."""

    arm9: bytes
    ov3: bytes
    ov5: bytes | None
    ss: SaveState | None
    rom_path: Path | None
    ss_path: Path | None

    # -- oracle selection ---------------------------------------------------
    def oracle_name(self, addr: int) -> str:
        """Which oracle owns *addr* (by range).  'unknown' if none."""
        if ARM9_BASE <= addr < ARM9_BASE + len(self.arm9):
            return "arm9"
        if OV3_BASE <= addr < OV3_BASE + len(self.ov3):
            return "ov3"
        if OV5_BASE <= addr < OV5_END:
            return "ov5"
        return "unknown"

    def image(self, oracle: str) -> bytes | None:
        return {"arm9": self.arm9, "ov3": self.ov3, "ov5": self.ov5}.get(oracle)

    def base(self, oracle: str) -> int:
        return {"arm9": ARM9_BASE, "ov3": OV3_BASE, "ov5": OV5_BASE}[oracle]


def load_env(rom_path: Path | None = None,
             savestate_path: Path | None = None) -> Env:
    """Load the stock arm9/ov3 oracles + optional ov5/savestate.

    ``rom_path``/``savestate_path`` default to the on-disk working files; either
    may be absent, in which case its oracle is ``None`` and dependent proofs
    SKIP.  The stock base ROM is required (arm9/ov3 are read from it).
    """
    from otn_enhanced.rom import stock
    try:
        arm9, ov3 = stock.arm9(), stock.ov3()
    except FileNotFoundError as e:
        raise SystemExit(f"missing stock oracle: {e}")

    rom_path = Path(rom_path) if rom_path else DEFAULT_ROM
    ov5: bytes | None = None
    if rom_path.exists():
        try:
            import ndspy.rom
            from otn_enhanced.effects import ov5_cave
            rom = ndspy.rom.NintendoDSRom.fromFile(str(rom_path))
            ov5 = bytes(rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID].data)
        except Exception:
            ov5 = None
    else:
        rom_path = None

    ss_path = Path(savestate_path) if savestate_path else DEFAULT_SAVESTATE
    ss: SaveState | None = None
    if ss_path.exists():
        try:
            ss = SaveState(ss_path)
        except Exception:
            ss = None
    else:
        ss_path = None

    return Env(arm9=arm9, ov3=ov3, ov5=ov5, ss=ss, rom_path=rom_path, ss_path=ss_path)
