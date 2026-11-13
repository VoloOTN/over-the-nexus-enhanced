"""Shorten the summon / card-activation animation instead of skipping it.

Companion to (and alternative to) skip_animations. Found 2026-09-10 by
following what the AR "remove animation" code actually suppresses; see
notes/battle-speed-ar-findings.md.

WHAT PLAYS THE ANIMATION
------------------------
0x02148AA4 is not an animation player, it is a duel COMMAND INTERPRETER: r6 is
the command id, args come off the stack, each case starts something and returns
1. Command 30 -- one of the five the AR code neutralises -- does:

    0214A5C0  ldr r1,[sp,#0x28C] / ldr r2,[sp,#0x290]
    0214A5C8  ldr r0, =0x022963F8   ; bl 0x0216A36C
    0214A5D4  ldr r0, =0x0229777C   ; mov r2,sb ; mov r1,#4 ; bl 0x0218E2C4

So the animation itself lives in the module whose context is **0x0229777C**:

    0x0218E2C4(ctx, mode, arg)  starts it -- [ctx+0xC0C] = mode, and it clears
                                the counters at +0xC18/+0xC1C/+0xCA8/+0xDC0
    0x0218D324(ctx)             steps it once per frame; it is subsystem idx9 of
                                the frame body, dispatching on [ctx+0xC0C]

Inside that module, **+0xC0C and +0xC18 are phase indices and +0xC1C is the frame
counter within the current phase**: `+= 1` each frame, and the phase advances when
it passes a threshold.

WHY THIS SCALES THE THRESHOLDS AND NOT THE STEP
-----------------------------------------------
The obvious lever -- make the counter step by N instead of 1 -- is a trap. A full
enumeration of every load of +0xC1C in 0x0218C000..0x02190000 found 8 thresholds,
and **4 of them are equality-gated**:

    0218FB94  cmp #1   / bne          0218FCD8  cmp #16  / bne
    0218FDEC  cmp #1   / bne          0218FEFC  cmp #1   / bne

plus a COUNTDOWN path that triggers on exactly zero:

    0218FC84  ldr r0,[sb,#0xC1C] / subs r0,r0,#1 / str
    0218FC90  moveq r0,#0x10 / streq r0,[sb,#0xC18]      ; fires only at == 0

A step of 2 jumps straight over every one of those, and the animation stalls
forever instead of playing faster. Making it safe would mean 13 edits including 5
hand-reasoned equality->inequality conversions.

Scaling the DURATION instead leaves the counter stepping by 1, so every equality
test still fires exactly as before -- it just fires sooner. Five words, no
semantic change, no stall risk from a skipped comparison.

WHAT IS WRITTEN: the five phase-length thresholds, all `cmp <counter>, #16`:

    0218FC40 (gt)   0218FCAC (gt)   0218FCD8 (ne)   0218FE10 (gt)   0218FFA8 (gt)

The three `cmp #1` thresholds are already one frame and are left alone.

SCOPE LIMIT -- READ THIS
------------------------
This is ONE module: the summon / card-activation cut-in player (ctx 0x0229777C),
which is exactly what the AR code's five commands drive. Card movement, attacks
and damage-step animations live in other modules with their own counters and are
NOT affected. Do not expect this to shorten a whole duel by itself.

STATUS: AWAITING IN-GAME TEST.
"""
from __future__ import annotations

import struct

from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3, RAM_BASE

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_anim_speed.nds"

# ---------------------------------------------------------------------------
# DIVISOR: phase length becomes NATIVE_LEN // DIVISOR (floored at 1 frame).
# 2 = half-length phases. The counter still advances one per frame, so this is
# purely "the phase ends sooner", not a change to how the animation is stepped.
# ---------------------------------------------------------------------------
DIVISOR = 2

NATIVE_LEN = 16
COUNTER_OFF = 0xC1C

# Every `cmp <+0xC1C>, #16` in the player, with the condition of the instruction
# that consumes the flags. Enumerated, not sampled: derived from every ldr of
# +0xC1C in 0x0218C000..0x02190000.
THRESHOLDS: dict[int, str] = {
    0x0218FC40: "gt",
    0x0218FCAC: "gt",
    0x0218FCD8: "ne",
    0x0218FE10: "gt",
    0x0218FFA8: "gt",
}
CMP_MASK = 0x0FF0F000
CMP_FORM = 0x03500000

# Left deliberately alone: already one frame, and all three are `bne`, so they
# must keep firing on an exact value.
ONE_FRAME_THRESHOLDS = (0x0218FB94, 0x0218FDEC, 0x0218FEFC)

# The countdown path -- asserted intact so a future edit cannot silently break it.
COUNTDOWN = {
    0x0218FC84: 0xE5990C1C,     # ldr r0,[sb,#0xC1C]
    0x0218FC88: 0xE2500001,     # subs r0,r0,#1
    0x0218FC8C: 0xE5890C1C,     # str r0,[sb,#0xC1C]
    0x0218FC90: 0x03A00010,     # moveq r0,#0x10   <- fires only at exactly 0
}

PLAYER_START = 0x0218E2C4
PLAYER_STEP = 0x0218D324
PLAYER_CTX = 0x0229777C


def _w(ov: bytearray, addr: int) -> int:
    return struct.unpack_from("<I", ov, addr - RAM_BASE)[0]


def _setw(ov: bytearray, addr: int, val: int) -> None:
    struct.pack_into("<I", ov, addr - RAM_BASE, val)


def new_len(divisor: int = DIVISOR) -> int:
    return max(1, NATIVE_LEN // divisor)


def main(divisor: int = DIVISOR, src: str = SRC, out: str = OUT,
         write_text: bool = False) -> None:
    assert 1 <= divisor <= NATIVE_LEN, f"divisor must be 1..{NATIVE_LEN}"
    length = new_len(divisor)

    rom, data = load_overlay3(src)
    ov = bytearray(data)

    # the module must be the one we mapped
    assert _w(ov, PLAYER_START) == 0xE92D4078, "player entry 0x0218E2C4 changed"
    assert _w(ov, PLAYER_STEP) == 0xE92D4FF8, "player step 0x0218D324 changed"
    for addr, want in COUNTDOWN.items():
        assert _w(ov, addr) == want, (
            f"countdown path {addr:08X} = {_w(ov, addr):08X}, want {want:08X}")
    for addr in ONE_FRAME_THRESHOLDS:
        w = _w(ov, addr)
        assert (w & CMP_MASK) == CMP_FORM and (w & 0xFF) == 1, (
            f"{addr:08X} is not the `cmp #1` we left alone: {w:08X}")

    for addr, cond in sorted(THRESHOLDS.items()):
        w = _w(ov, addr)
        assert (w & CMP_MASK) == CMP_FORM, f"{addr:08X} is not a `cmp rX,#imm`: {w:08X}"
        assert (w & 0xFF) == NATIVE_LEN, (
            f"{addr:08X} threshold is {w & 0xFF}, expected the native {NATIVE_LEN}")
        _setw(ov, addr, (w & ~0xFF) | length)
        print(f"  {addr:08X}  cmp #{NATIVE_LEN} -> cmp #{length}   (consumed by '{cond}')")

    save_overlay3(rom, bytes(ov), out)
    print(f"animation speed: summon/activation phases {NATIVE_LEN} -> {length} frames "
          f"(1/{divisor}); counter still steps by 1")
    print(f"wrote {out}")


def verify(out: str = OUT) -> None:
    _, data = load_overlay3(out)
    ov = bytearray(data)

    lengths = set()
    for addr in sorted(THRESHOLDS):
        w = _w(ov, addr)
        assert (w & CMP_MASK) == CMP_FORM, f"{addr:08X} is no longer a `cmp rX,#imm`"
        lengths.add(w & 0xFF)
    assert len(lengths) == 1, f"thresholds disagree: {sorted(lengths)}"
    length = lengths.pop()
    assert 1 <= length <= NATIVE_LEN, f"threshold {length} out of range"

    # the parts we must NOT have touched
    for addr, want in COUNTDOWN.items():
        assert _w(ov, addr) == want, f"countdown path {addr:08X} was modified"
    for addr in ONE_FRAME_THRESHOLDS:
        assert (_w(ov, addr) & 0xFF) == 1, f"{addr:08X} one-frame threshold changed"
    assert _w(ov, PLAYER_START) == 0xE92D4078 and _w(ov, PLAYER_STEP) == 0xE92D4FF8

    print(f"PASS animation_speed: 5 phases at {length} frames (native {NATIVE_LEN}), "
          f"countdown + 3 one-frame thresholds intact, ctx 0x{PLAYER_CTX:08X}")


if __name__ == "__main__":
    assert new_len(1) == 16 and new_len(2) == 8 and new_len(16) == 1
    assert new_len(32) == 1  # floor guard
    print("length arithmetic self-check OK")
    main()
    verify()
