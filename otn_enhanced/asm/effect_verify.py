"""Validate authored card-effect stubs before they go into a ROM.

Two checks, both dependency-free (built on the in-repo Thumb-1 decoder — no
capstone):

* :func:`assert_thumb1_only` enforces the ARMv5TE / Thumb-1 rule from HOWTO
  §11.  The NDS ARM9 is an ARM946E-S; a 32-bit Thumb-2 instruction
  (``movw``/``movt``/``b.w``/``cbz`` …) is an *undefined instruction* there and
  freezes the console — and capstone happily disassembles it, so a disasm-grep
  would not catch it.  This walks the encoding directly: the only legal 32-bit
  forms are ``BL``/``BLX``; any other 32-bit prefix in *code* is banned.

* :func:`verify_against_overlay` is the corpus oracle: a stub that re-emits an
  existing handler must reproduce that handler's original overlay bytes.

Literal-pool words (which can contain any bit pattern, including bytes that
look like a 32-bit prefix) are excluded from the Thumb-2 scan the same way the
shim emitter excludes them: words referenced by an in-function ``LDR [PC,#imm]``
and everything past the trailing-pool boundary.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from otn_enhanced.asm.thumb_disasm import decode_thumb, ThumbInsn, pool_start_index

# Banned 32-bit Thumb-2 mnemonics, for the error message (not exhaustive — the
# check is structural, by encoding, not by name).
_BANNED_EXAMPLES = "movw / movt / b.w / bl.w / cbz / cbnz / it / tbb / tbh"


class Thumb2Error(ValueError):
    """Raised when a stub contains a banned 32-bit Thumb-2 instruction."""


@dataclass(frozen=True)
class Thumb2Hit:
    """A flagged 32-bit Thumb-2 halfword: its byte offset and raw value."""
    offset: int
    halfword: int


def _pool_byte_ranges(insns: list[ThumbInsn], base: int,
                      blob_len: int) -> list[tuple[int, int]]:
    """Byte ranges (relative to *base*) occupied by literal-pool data.

    Mirrors the shim emitter: words referenced by an ``LDR [PC,#imm]`` plus
    everything from the trailing-pool boundary onward.
    """
    ranges: list[tuple[int, int]] = []
    for ins in insns:
        if ins.is_pool_ref:
            start = ins.pool_addr - base
            ranges.append((start, start + 4))
    ps = pool_start_index(insns)
    if ps < len(insns):
        ranges.append((insns[ps].addr - base, blob_len))
    return ranges


def find_thumb2(blob: bytes, base: int = 0) -> list[Thumb2Hit]:
    """Return every banned 32-bit Thumb-2 halfword in *blob*.

    *base* is the runtime start address (only its low bits matter, for
    resolving ``LDR [PC,#imm]`` pool offsets).  ``BL``/``BLX`` pairs and bytes
    inside literal-pool words are not flagged.
    """
    insns = decode_thumb(blob, base, overlay_data=blob, ram_base=base)
    pool_ranges = _pool_byte_ranges(insns, base, len(blob))

    def in_pool(off: int) -> bool:
        return any(lo <= off < hi for lo, hi in pool_ranges)

    hits: list[Thumb2Hit] = []
    i = 0
    n = len(blob)
    while i + 2 <= n:
        if in_pool(i):
            i += 2
            continue
        hw = struct.unpack_from("<H", blob, i)[0]
        top5 = hw >> 11
        if top5 == 0b11110:        # 32-bit prefix: BL/BLX (legal) or Thumb-2
            if i + 4 <= n:
                hw2 = struct.unpack_from("<H", blob, i + 2)[0]
                if (hw2 >> 11) in (0b11111, 0b11101):  # BL (F800) / BLX (E800)
                    i += 4
                    continue
                hits.append(Thumb2Hit(i, hw))  # complete 32-bit non-BL → Thumb-2
            # else: dangling prefix at end-of-blob — incomplete, not Thumb-2
        elif top5 in (0b11101, 0b11111):       # standalone 32-bit half → Thumb-2
            hits.append(Thumb2Hit(i, hw))
        elif (hw & 0xF500) == 0xB100:          # CBZ / CBNZ (16-bit, ARMv4T-undefined)
            hits.append(Thumb2Hit(i, hw))
        i += 2
    return hits


def assert_thumb1_only(blob: bytes, base: int = 0) -> None:
    """Raise :class:`Thumb2Error` if *blob* contains banned Thumb-2 (HOWTO §11).

    The NDS ARM9 executes Thumb-1 only; a 32-bit Thumb-2 op freezes it.
    """
    hits = find_thumb2(blob, base)
    if hits:
        detail = ", ".join(f"+0x{h.offset:X} (0x{h.halfword:04X})" for h in hits)
        raise Thumb2Error(
            f"banned non-Thumb-1 instruction at {detail}; the NDS ARM9 is "
            f"ARMv5TE / Thumb-1 only (no {_BANNED_EXAMPLES}) — these freeze "
            f"the console")


def bl_reaches(image: bytes, ram_base: int, site: int, stub: int) -> bool:
    """True iff the BL at *site* calls *stub*, directly or through a CHAIN of list-search pre-checks (at most 8)
    of the exact shape ``ldr r3,=key ; cmp r0,r3 ; bne miss ; movs r0,#1 ; bx lr ; miss: ldr r3,=next|1 ; bx r3``
    (obedience_schooled fronts two shared list searches this way, and next_card fronts OS's fronts; each
    miss path is the previous call)."""
    def u16(a: int) -> int:
        return struct.unpack_from("<H", image, a - ram_base)[0]
    h1, h2 = u16(site), u16(site + 2)
    if h1 >> 11 != 0b11110 or h2 >> 11 != 0b11111:
        return False
    off = ((h1 & 0x7FF) << 12) | ((h2 & 0x7FF) << 1)
    return addr_reaches(image, ram_base, site + 4 + (off - (1 << 23) if off & (1 << 22) else off), stub)


def addr_reaches(image: bytes, ram_base: int, t, stub: int) -> bool:
    """bl_reaches from an ADDRESS instead of a BL site (e.g. where an ov5 front chain ends, ov5_cave.ik_tail)."""
    def u16(a: int) -> int:
        return struct.unpack_from("<H", image, a - ram_base)[0]
    if t is None:
        return False
    for _ in range(8):
        if t == stub:
            return True
        if not ram_base <= t < ram_base + len(image) - 14:
            return False
        hw = [u16(t + 2 * i) for i in range(7)]
        if not (hw[0] >> 8 == 0x4B and hw[1] == 0x4298 and hw[2] >> 8 == 0xD1 and hw[3] == 0x2001
                and hw[4] == 0x4770 and hw[5] >> 8 == 0x4B and hw[6] == 0x4718):
            return False
        lit = ((t + 10 + 4) & ~3) + (hw[5] & 0xFF) * 4
        t = struct.unpack_from("<I", image, lit - ram_base)[0] & ~1
    return t == stub


def verify_against_overlay(blob: bytes, addr: int, overlay: bytes,
                           ram_base: int) -> None:
    """Assert *blob* equals the *overlay* bytes at runtime address *addr*.

    The corpus oracle: a stub that re-emits an existing handler must reproduce
    the shipped bytes exactly.  *ram_base* is the overlay's load address
    (``effect_extract.RAM_BASE`` for overlay0003).
    """
    file_off = addr - ram_base
    if not (0 <= file_off and file_off + len(blob) <= len(overlay)):
        raise ValueError(
            f"address 0x{addr:08X} (+{len(blob)}B) is outside the overlay "
            f"[0x{ram_base:08X}, 0x{ram_base + len(overlay):08X})")
    original = overlay[file_off:file_off + len(blob)]
    if blob != original:
        for k in range(0, len(blob), 2):
            if blob[k:k + 2] != original[k:k + 2]:
                raise AssertionError(
                    f"stub diverges from overlay at +0x{k:X}: "
                    f"got {blob[k:k+2].hex()}, overlay {original[k:k+2].hex()}")
        raise AssertionError(  # length mismatch with no earlier byte diff
            f"stub length {len(blob)} != overlay region")
