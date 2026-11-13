"""Enable Konami's own duel fast-forward -- the lever for AI thinking time.

Not ported from an AR code. Found 2026-09-10 while asking why battle_speed
did nothing for animations or the AI; see notes/battle-speed-ar-findings.md.

WHY battle_speed CANNOT SPEED UP THE AI
--------------------------------------------
The frame body's sub-pass loop breaks out the moment the duel engine is busy:

    021460CC  blx 0x0219D470     ; the duel tick
    021460D0  mov r6, r0         ; r6 = "am I busy"
    ...
    021460E4  cmp r6, #0
    021460E8  bne 0x02146104     ; BUSY -> skip the counter AND the back edge
    021460EC..F8  counter++
    021460FC  cmp r1, r7         ; <- battle_speed edits this word
    02146100  ble 0x02146014

So SPEED multiplies only the frames on which the duel tick reports idle. Every
frame with an animation playing or the AI thinking runs exactly one pass no
matter what SPEED says. Raising SPEED cannot touch either.

THE ACTUAL LEVER
----------------
Immediately above that, the retail build carries a disabled fast-forward:

    021460A8  ldr r0, <0x020B7C8C>
    021460AC  ldr r0, [r0, #0xF54]
    021460B0  cmp r0, #0
    021460B4  beq 0x021460CC     ; <- gate. clear in retail, so the block below is dead
    021460B8  mov r6, #0
    021460BC  blx 0x0219D470     ; EXTRA duel ticks, NOT gated on the busy result
    021460C0  add r6, r6, #1
    021460C4  cmp r6, #4         ; <- extra-tick count
    021460C8  blt 0x021460BC
    021460CC  blx 0x0219D470     ; the normal tick (always runs)

`[0x020B7C8C+0xF54]` is 0 in all 184 layout-matching savestates, so those extra
ticks never happen in a retail duel. They sit BEFORE the busy check, so turning
them on advances the duel tick during animations and during AI thinking -- which
is exactly what SPEED cannot reach.

The duel tick is `0x0219D470` -> handler table 0x0226D2B0 [0] = `0x0219D320`, the
cooperative chain whose `bl 0x021D6D34` @0x0219D388 is the **AI turn controller**
(notes/dueling-ai-findings.md). Multiplying the tick multiplies the AI's compute
budget per rendered frame, so the "thinking" pause shortens in proportion.

WHAT IS WRITTEN: one or two words in ov3, no stub, no cave, no allocation claim.

    0x021460B4  beq 0x021460CC -> nop      (force the gate open)
    0x021460C4  cmp r6, #4     -> cmp r6, #TICKS-1   (only if TICKS != 5)

COMPOSES WITH the other two duel patches -- all three edit disjoint words:
  battle_speed      0x021460FC, 0x0214603C, 0x021B54FC
  skip_animations   0x02148B88..0x02148BF4
  this                    0x021460B4, 0x021460C4

STATUS: AWAITING IN-GAME TEST.
"""
from __future__ import annotations

import struct

from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3, RAM_BASE

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_duel_ff.nds"

# ---------------------------------------------------------------------------
# TICKS = duel-tick calls per sub-pass. 5 is Konami's own value (4 extra + the
# normal one) and is the only value the shipped code was ever built around, so
# it is the default. Raising it gives the AI more compute per rendered frame and
# shortens animations further; the ceiling is legibility, exactly as with SPEED.
# ---------------------------------------------------------------------------
TICKS = 5

GATE_SITE = 0x021460B4
GATE_OLD = 0x0A000004            # beq 0x021460CC
NOP = 0xE1A00000                 # mov r0, r0

COUNT_SITE = 0x021460C4
COUNT_OLD = 0xE3560004           # cmp r6, #4

# Preconditions -- the whole block must be the one we decoded.
EXPECT = {
    0x021460A8: 0xE59F0150,      # ldr r0,[pc,#0x150]  -> 0x020B7C8C
    0x021460AC: 0xE5900F54,      # ldr r0,[r0,#0xf54]  -- the gate field
    0x021460B0: 0xE3500000,      # cmp r0,#0
    0x021460B8: 0xE3A06000,      # mov r6,#0
    0x021460BC: 0xFA015CEB,      # blx 0x0219D470      -- the extra tick
    0x021460C0: 0xE2866001,      # add r6,r6,#1
    0x021460C8: 0xBAFFFFFB,      # blt 0x021460BC
    0x021460CC: 0xFA015CE7,      # blx 0x0219D470      -- the normal tick
    0x021460E4: 0xE3560000,      # cmp r6,#0           -- the busy break
    0x021460E8: 0x1A000005,      # bne 0x02146104
}
GATE_POOL = 0x02146200
GATE_STRUCT = 0x020B7C8C
DUEL_TICK = 0x0219D470


def _w(ov: bytearray, addr: int) -> int:
    return struct.unpack_from("<I", ov, addr - RAM_BASE)[0]


def _setw(ov: bytearray, addr: int, val: int) -> None:
    struct.pack_into("<I", ov, addr - RAM_BASE, val)


def main(ticks: int = TICKS, src: str = SRC, out: str = OUT, write_text: bool = False) -> None:
    assert 2 <= ticks <= 256, "ticks must be 2..256 (1 = stock, i.e. nothing to do)"
    extra = ticks - 1                       # the `cmp r6,#extra` immediate
    assert extra <= 0xFF, "extra-tick count needs a rotated ARM immediate"

    rom, data = load_overlay3(src)
    ov = bytearray(data)

    for addr, want in EXPECT.items():
        assert _w(ov, addr) == want, f"{addr:08X} = {_w(ov, addr):08X}, want {want:08X}"
    assert _w(ov, GATE_SITE) == GATE_OLD, f"{GATE_SITE:08X} is not the gate `beq`"
    assert _w(ov, COUNT_SITE) == COUNT_OLD, f"{COUNT_SITE:08X} is not `cmp r6,#4`"
    assert _w(ov, GATE_POOL) == GATE_STRUCT, "gate literal moved"

    _setw(ov, GATE_SITE, NOP)
    if extra != 4:
        _setw(ov, COUNT_SITE, 0xE3560000 | extra)

    save_overlay3(rom, bytes(ov), out)
    print(f"duel fast-forward ON: {ticks} duel ticks per sub-pass "
          f"({extra} extra + 1); gate @0x{GATE_SITE:08X} forced open")
    print(f"wrote {out}")


def verify(out: str = OUT) -> None:
    _, data = load_overlay3(out)
    ov = bytearray(data)

    assert _w(ov, GATE_SITE) == NOP, f"gate not opened: {_w(ov, GATE_SITE):08X}"
    got = _w(ov, COUNT_SITE)
    assert (got & 0xFFFFFF00) == 0xE3560000, f"tick count clobbered: {got:08X}"
    ticks = (got & 0xFF) + 1

    # the block the gate protects must be intact -- opening a gate onto edited
    # code would be worse than leaving it shut
    for addr, want in EXPECT.items():
        assert _w(ov, addr) == want, f"{addr:08X} changed under the open gate"

    print(f"PASS duel_fastforward: gate open, {ticks} ticks/pass, "
          f"tick 0x{DUEL_TICK:08X} (-> AI controller 0x021D6D34) intact")


if __name__ == "__main__":
    assert (0xE3560000 | (TICKS - 1)) == COUNT_OLD or TICKS != 5
    main()
    verify()
