"""The ``h`` helper object exposed to every proof snippet.

A proof body runs with three names in scope: ``env`` (the :class:`~env.Env`
oracles), ``h`` (this helper), and ``Skip`` (raise it to report UNVERIFIED).
Helpers that need an absent oracle (ov5 without rom.nds, RAM without a
savestate) raise :class:`Skip` themselves, so a proof that reads them degrades
to UNVERIFIED rather than FAIL — the KB contract.

Design note: helpers make *semantic-structural* assertions cheap (sortedness,
table membership, BL-target decoding, Thumb-1 legality) so a fact can be graded
VERIFIED rather than merely ANCHORED wherever the engine's own invariants make
that possible.
"""
from __future__ import annotations

import struct

from otn_enhanced.knowledge.env import Env


class Skip(Exception):
    """Raised by a proof (directly or via a helper) to report UNVERIFIED.

    Distinct from ``AssertionError`` (which the runner reports as FAIL): a Skip
    means "the input needed to check this is not present", not "the claim is
    false".
    """


class Helpers:
    def __init__(self, env: Env):
        self.env = env

    # -- ROM / overlay byte access -----------------------------------------
    def oracle_for(self, addr: int) -> str:
        return self.env.oracle_name(addr)

    def _image(self, addr: int, oracle: str | None) -> tuple[bytes, int]:
        oracle = oracle or self.env.oracle_name(addr)
        if oracle == "unknown":
            raise Skip(f"0x{addr:08X} is outside every known oracle range")
        img = self.env.image(oracle)
        if img is None:
            reason = "no rom.nds (ov5 not loaded)" if oracle == "ov5" else f"{oracle} unavailable"
            raise Skip(f"oracle '{oracle}' for 0x{addr:08X} unavailable: {reason}")
        return img, self.env.base(oracle)

    def bytes_at(self, addr: int, n: int, oracle: str | None = None) -> bytes:
        """Return *n* bytes at runtime address *addr* from the owning oracle.

        *oracle* auto-selected by address range when omitted.  Raises
        :class:`Skip` if the needed oracle (ov5 / savestate) is absent.
        """
        img, base = self._image(addr, oracle)
        off = addr - base
        if not (0 <= off and off + n <= len(img)):
            raise AssertionError(
                f"0x{addr:08X}+{n} is outside oracle image "
                f"[0x{base:08X}, 0x{base + len(img):08X})")
        return img[off:off + n]

    def u8(self, addr: int, oracle: str | None = None) -> int:
        return self.bytes_at(addr, 1, oracle)[0]

    def u16(self, addr: int, oracle: str | None = None) -> int:
        return struct.unpack("<H", self.bytes_at(addr, 2, oracle))[0]

    def u32(self, addr: int, oracle: str | None = None) -> int:
        return struct.unpack("<I", self.bytes_at(addr, 4, oracle))[0]

    def u16_table(self, addr: int, count: int, oracle: str | None = None) -> list[int]:
        raw = self.bytes_at(addr, count * 2, oracle)
        return list(struct.unpack(f"<{count}H", raw))

    # -- Thumb decoding -----------------------------------------------------
    def bl_target(self, addr: int, oracle: str | None = None) -> int:
        """Decode the ARMv4T ``BL``/``BLX`` halfword pair at *addr* to its target.

        The engine's long calls are two-halfword BL (0xF000|hi, 0xF800|lo) or
        BLX (…0xE800|lo).  Returns the absolute branch target.  Raises
        AssertionError if the pair is not a BL/BLX.
        """
        hw1, hw2 = struct.unpack("<2H", self.bytes_at(addr, 4, oracle))
        if (hw1 >> 11) != 0b11110:
            raise AssertionError(f"0x{addr:08X}: 0x{hw1:04X} is not a BL/BLX prefix")
        top2 = hw2 >> 11
        if top2 not in (0b11111, 0b11101):
            raise AssertionError(f"0x{addr:08X}: 0x{hw2:04X} is not a BL/BLX suffix")
        high = hw1 & 0x7FF
        low = hw2 & 0x7FF
        off = (high << 12) | (low << 1)
        if off & (1 << 22):
            off -= (1 << 23)                 # sign-extend 23-bit offset
        target = (addr + 4 + off) & 0xFFFFFFFF
        if top2 == 0b11101:                  # BLX -> word-align, into ARM state
            target &= ~3
        return target

    def assert_thumb1(self, blob: bytes, base: int = 0) -> None:
        """Assert *blob* is legal ARM9 Thumb-1 (no freezing Thumb-2). HOWTO §11."""
        from otn_enhanced.asm.effect_verify import assert_thumb1_only
        assert_thumb1_only(blob, base)

    @staticmethod
    def is_sorted_unique(seq) -> bool:
        return all(seq[i] < seq[i + 1] for i in range(len(seq) - 1))

    # -- live RAM (savestate) ----------------------------------------------
    @property
    def ss(self):
        if self.env.ss is None:
            raise Skip("no savestate loaded (pass --savestate PATH to a duel .ml*)")
        return self.env.ss

    def ram_u8(self, addr: int) -> int:
        return self.ss.u8(addr)

    def ram_u16(self, addr: int) -> int:
        return self.ss.u16(addr)

    def ram_u32(self, addr: int) -> int:
        return self.ss.u32(addr)

    def ram_bytes(self, addr: int, n: int) -> bytes:
        return self.ss.read(addr, n)

    @staticmethod
    def decode_card_word(w: int) -> dict:
        """Unpack an on-field / list card-ref word (mirror of librarian_recorder)."""
        return {
            "cid": w & 0x3FFF,
            "side": (w >> 14) & 1,
            "bit15": (w >> 15) & 1,
            "facedown": (w >> 22) & 1,
            "inst_idx": (w >> 23) & 0xFF,
            "packed_ref": (((w >> 23) & 0xFF) << 1) | ((w >> 14) & 1),
        }
