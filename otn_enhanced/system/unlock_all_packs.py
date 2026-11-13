"""Unlock every booster pack in the card shop ("Getpack" screen).

Mechanism
---------
The shop's pack list is gated by a bitfield, *not* by a saved flag.  Overlay 10
(the Getpack screen) owns a singleton at EU ``0x02158D10``; at ``+0x10AC`` it
holds a ``u32[]`` where bit *i* means "pack ID *i+1* is available".  Two loops in
ov10 read it and nothing in ov10 writes it::

    ov10 0x0214DA50   ldr r2, [r0, #0xac]   ; loop A -- syncs master per-pack records (i = 0..80)
    ov10 0x0214DF20   ldr r2, [r2, #0xac]   ; loop B -- builds the visible list  (i = 0..59)

The bitfield is **recomputed from scratch every time the shop opens** by a
function in overlay 1 (ov1 is resident under ov10: ov1 ends at 0x0214C840, which
is exactly ov10's load address).  ov10 calls it at ``0x0214DEA8`` and
``0x0214DEE4`` passing ``&bitfield`` in r0::

    ov1 0x021450F8  unlock_mask(u32 *bits, int)
        r7 = 0
      loop:
        r0 = r7 + 1                          ; pack ID
        cmp r0, #0x3c
        addls pc, pc, r0, lsl #2             ; <-- jump table, one arm per pack ID 1..60
        <arm: evaluate that pack's unlock condition>
          fail -> b 0x02145d8c  (loop tail, bit left clear)
          pass -> b 0x02145bc0  (shared set-bit tail, + "new pack" notify)
      0x02145d8c:
        add r7, r7, #1 ; cmp r7, #0x3c ; blt loop

The per-pack arms are hardcoded conditions: packs 1-4 are unconditional (they
branch straight to the plain set-bit arm at ``0x02145218``), the rest test story
event flags (``blx 0x0201B36C`` with IDs 0x4E40, 0x4E41, ...), progress counters
(``blx 0x0202F6EC`` >= 50 / >= 100), or "beat these duelists at rank >= N" via the
helper at ``0x02144F08`` walking ``master[0x0212406C + duelist*4 + 0x2EC]``.

Because the mask is derived rather than stored, there is nothing in the .sav to
edit -- the fix has to live in the derivation.

The patch
---------
One instruction.  Replace the jump-table dispatch with an unconditional branch to
the plain set-bit arm, so every pack ID 1..60 takes the "unconditional" path::

    0x0214511C   addls pc, pc, r0, lsl #2   ->   b 0x02145218

Routing through ``0x02145218`` (rather than the condition-met tail at
``0x02145bc0``) is deliberate: that tail also calls the "new pack unlocked!"
notifier, which would fire 60 times on every shop entry.

The mask keeps being computed normally, so the pack count at ``+0x10A4``, the
visible list and the master per-pack record sync all stay self-consistent.  Only
IDs 1..60 are touched -- the loop bound is 0x3c and the stock game never sets
bits 60..80, so this patch does not invent packs the shop cannot display.

Addresses are **EU (BYYP)**.  The US build's ov1/ov10 are the same code 0xE0
higher; this module refuses to run on anything whose bytes don't match.
"""
from __future__ import annotations

import shutil
import struct
from pathlib import Path

import ndspy.rom

# ---------------------------------------------------------------------------
# Input / output ROMs
# ---------------------------------------------------------------------------
SRC = "data/over_the_nexus/working/rom.nds"                       # clean EU (AP-fixed) base
OUT = "data/over_the_nexus/working/rom_all_packs.nds"             # patched output

# ---------------------------------------------------------------------------
# Overlay 1 geometry + patch site (EU)
# ---------------------------------------------------------------------------
OVERLAY_ID = 1
OV1_BASE = 0x02141700

UNLOCK_FN = 0x021450F8      # unlock_mask(u32 *bits, int)
DISPATCH = 0x0214511C       # addls pc, pc, r0, lsl #2   <- the instruction we replace
SET_BIT_ARM = 0x02145218    # the unconditional "set bit r7 in *sb*" arm

ORIG_DISPATCH = 0x908FF100  # addls pc, pc, r0, lsl #2

# Byte signatures that must hold before we write anything.  Each is
# (address, expected bytes) in the decompressed overlay-1 image.
SIGNATURES = (
    # unlock_mask prologue: push {r3-r8,sb,sl,fp,lr} / sub sp, sp, #0xe0
    (UNLOCK_FN, bytes.fromhex("f84f2de9e0d04de2")),
    # loop head, up to but NOT including the dispatch word we rewrite:
    #   add r0, r7, #1 / cmp r0, #0x3c
    (UNLOCK_FN + 0x1C, bytes.fromhex("010087e23c0050e3")),
    # the unconditional set-bit arm we retarget to (asr r0, r7, #4 ...)
    (SET_BIT_ARM, bytes.fromhex("4702a0e1a00d87e0c032a0e1")),
    # ... ending in str r0, [sb, r3, lsl #2] -> loop tail
    (SET_BIT_ARM + 0x20, bytes.fromhex("030189e7")),
)


def _branch(frm: int, to: int) -> int:
    """Encode an ARM ``B`` from *frm* to *to* (AL condition)."""
    delta = to - (frm + 8)
    assert delta % 4 == 0, f"unaligned branch {frm:#x} -> {to:#x}"
    imm = delta // 4
    assert -(1 << 23) <= imm < (1 << 23), f"branch out of range {frm:#x} -> {to:#x}"
    return 0xEA000000 | (imm & 0xFFFFFF)


NEW_DISPATCH = _branch(DISPATCH, SET_BIT_ARM)   # 0xEA00003D -> b 0x02145218


# ---------------------------------------------------------------------------
# Overlay 1 load / save (mirrors overlay_io.save_overlay3, which is ov3-only)
# ---------------------------------------------------------------------------
def _load_ov1(rom: "ndspy.rom.NintendoDSRom") -> tuple[object, bytearray]:
    ov = rom.loadArm9Overlays([OVERLAY_ID])[OVERLAY_ID]
    assert ov.ramAddress == OV1_BASE, (
        f"overlay 1 loads at {ov.ramAddress:#010x}, expected {OV1_BASE:#010x} "
        "-- this is not the EU (BYYP) ROM this patch was built against"
    )
    return ov, bytearray(ov.data)


def _save_ov1(rom: "ndspy.rom.NintendoDSRom", ov, data: bytes) -> None:
    """Write *data* back as overlay 1, refreshing the overlay-table entry.

    ndspy keeps the arm9 overlay table as a separate bytearray and does not
    propagate ramSize / compressed-size back into it; without the writeback the
    loader copies a stale byte count out of the recompressed file.
    """
    ov.data = bytes(data)
    ov.ramSize = len(data)
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed

    tbl = rom.arm9OverlayTable
    entry = OVERLAY_ID * 32
    struct.pack_into("<I", tbl, entry + 0x08, len(data))          # ramSize
    flags_word = struct.unpack_from("<I", tbl, entry + 0x1C)[0]
    flags = flags_word >> 24
    struct.pack_into("<I", tbl, entry + 0x1C,
                     (flags << 24) | (len(compressed) & 0xFFFFFF))


def _check_signatures(data: bytes) -> None:
    for addr, expect in SIGNATURES:
        off = addr - OV1_BASE
        got = bytes(data[off:off + len(expect)])
        if got != expect:
            raise AssertionError(
                f"overlay 1 signature mismatch at {addr:#010x}: "
                f"expected {expect.hex()}, found {got.hex()}"
            )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def main(*, write_text: bool | None = None, src: str | Path = SRC,
         out: str | Path = OUT) -> None:
    """Force every booster pack's unlock condition to pass.

    *write_text* is accepted for apply-all-patches chain uniformity and ignored
    (this patch touches no card text).
    """
    del write_text

    src, out = str(src), str(out)
    if src != out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out)

    rom = ndspy.rom.NintendoDSRom.fromFile(out)
    ov, data = _load_ov1(rom)
    _check_signatures(data)

    off = DISPATCH - OV1_BASE
    cur = struct.unpack_from("<I", data, off)[0]
    if cur == NEW_DISPATCH:
        print(f"  overlay 1 {DISPATCH:#010x} already patched -- nothing to do")
        return
    assert cur == ORIG_DISPATCH, (
        f"{DISPATCH:#010x} holds {cur:#010x}, expected "
        f"{ORIG_DISPATCH:#010x} (addls pc, pc, r0, lsl #2)"
    )
    struct.pack_into("<I", data, off, NEW_DISPATCH)

    _save_ov1(rom, ov, data)
    rom.saveToFile(out)
    print(f"  ov1 {DISPATCH:#010x}: {ORIG_DISPATCH:#010x} -> {NEW_DISPATCH:#010x} "
          f"(b {SET_BIT_ARM:#010x})")
    print(f"  wrote -> {out}")


def verify(*, out: str | Path = OUT) -> bool:
    """Re-read the built ROM and confirm the dispatch branch is in place."""
    rom = ndspy.rom.NintendoDSRom.fromFile(str(out))
    ov, data = _load_ov1(rom)
    _check_signatures(data)          # untouched neighbourhood still intact

    got = struct.unpack_from("<I", data, DISPATCH - OV1_BASE)[0]
    ok = got == NEW_DISPATCH
    print(f"  [{'OK ' if ok else 'BAD'}] ov1 {DISPATCH:#010x} = {got:#010x} "
          f"(want {NEW_DISPATCH:#010x})")
    return ok


if __name__ == "__main__":
    main()
    verify()
