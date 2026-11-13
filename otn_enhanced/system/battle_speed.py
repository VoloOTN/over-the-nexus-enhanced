"""Duel speed multiplier -- run the duel logic N times per rendered frame.

Ported from a community Action Replay "battle speed up" code (decoded 2026-09-10,
see notes/battle-speed-ar-findings.md). The AR code's two guard lines fingerprint
0x0214503C and 0x0214603C and both match this EU (BYYP) ROM byte-for-byte, so it
was written for exactly this build.

WHAT THE ENGINE ALREADY DOES
----------------------------
0x02145FC0 is the duel per-frame tick. Its body 0x02146014..0x02146100 updates
~14 subsystems (`ldr r0,<ctx literal>; bl <update>`) and is ALREADY a sub-pass
loop:

    0214600C  str r5,[r0,#0x13c]    ; r0 = 0x022943F8  -> counter := 0
    ...       14x  ldr r0,<ctx> / bl <subsystem update>
    021460F4  str r1,[r0,#0x13c]    ; counter++        (counter @ 0x02294534)
    021460FC  cmp r1, r7            ; r7 = sub-pass bound
    02146100  ble 0x02146014

r7 comes from 0x02145FE4: `min([0x020B7C8C+0x2C], 4)` when the mode getter
0x0201757C (returns [0x020B9970+0x4C]) reads 2, else **r7 = 0** -> one pass.
That mode field is 0 in all 184 layout-matching savestates in
data/over_the_nexus/working/, so in real play the loop always runs exactly once
and Konami's own frame-skip path is dead code. Raising the bound is the speedup.

WHAT THIS PATCH WRITES (3 words + a 16-byte stub, overlay 3 only)
-----------------------------------------------------------------
PART A  0x021460FC : `cmp r1,r7` -> `cmp r1,#SPEED-1`.  Forces the bound in every
        mode regardless of r7. This single word IS the speedup.
PART B  0x0214603C : `bl 0x02159F1C` -> `b <stub>`, and a 16-byte ARM stub that
        re-issues the call ONLY on sub-pass 0, then rejoins at 0x02146040. The
        AR code throttles this subsystem for a reason we could not name (it is a
        large multi-call module), so the throttle is ported faithfully.

DELIBERATE DEVIATION FROM THE AR CODE
-------------------------------------
The AR code carries a SECOND throttle on `bl 0x0216D624` @0x0214604C whose guard
is `halfword[0x020B87E4] == 0 OR counter == 0`. That halfword is 0 in all 184
savestates, i.e. the guard is always true and the throttle never actually skips
the call -- it is a no-op in every state we have. It is dropped here because ov3
dead-code space is scarce (54 B total free before this patch). If in-game testing
shows that subsystem misbehaving, the fix is to restore it; it needs ~20 B
(0x022963F8 - 0x02294534 = 0x1EC4 > the 4095 ldr immediate, so it costs one more
instruction than PART B's stub).

WHY OVERLAY 3 AND NOT A CAVE
----------------------------
The hook site runs in EVERY duel mode, puzzles included, so the stub must be
resident everywhere. ov5 is evicted by ov41 in puzzles (branching there = freeze);
the ov3 BSS cave's canary FAILED (the engine clears ov3 BSS); the ARM9 main cave
is recorded as "NOT a usable host". The only always-resident host left is the ov3
dead-code pool (check_allocations.OV3_DEAD_BLOCKS), so the stub goes in the 16-byte
free tail of block 0x021B54E0 -- the ONLY 16-byte contiguous hole in that pool.
It is ARM code in a Thumb leaf's body, which is fine: the bytes are ours, the
address is 4-aligned, and every branch in and out is ARM->ARM (no interworking).

STATUS: AWAITING IN-GAME TEST. Nothing here has been confirmed in melonDS.
"""
from __future__ import annotations

import struct

from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3, RAM_BASE  # overlay-3 I/O + RAM base (0x02141700)

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_battle_speed.nds"

# ---------------------------------------------------------------------------
# The knob.  SPEED = logic passes per rendered frame; 1 = stock.
#
# HOW HIGH CAN IT GO?  The bound is a plain ARM `cmp` immediate, so anything up
# to 256 encodes.  What actually limits it is behaviour, not encoding:
#   * Konami's own path clamps at 5 (`movge r7,#4` @0x02145FF8) -- 5 is the
#     highest value the engine was ever built to tolerate, and what the AR code
#     used.  Treat >5 as untested.
#   * Input is sampled once per RENDERED frame, so the duel logic advances SPEED
#     steps per input sample; high values make timed prompts harder to hit and
#     make animations skip rather than play fast.
#   * Per-pass countdowns (e.g. [0x022943F8+0x124], decremented once per pass in
#     the loop body) tick SPEED times faster, which is the point, but anything
#     keyed to them scales too.
# Try 5 first, then raise; this is one word to rebuild.
# ---------------------------------------------------------------------------
SPEED = 5

# --- PART A: the loop bound ------------------------------------------------
BOUND_SITE = 0x021460FC
BOUND_OLD = 0xE1510007           # cmp r1, r7

# --- PART B: throttle `bl 0x02159F1C` to sub-pass 0 -------------------------
HOOK_SITE = 0x0214603C
HOOK_OLD = 0xEB004FB6            # bl 0x02159F1C
CTX_LOAD_SITE = 0x02146038       # ldr r0,[pc,#0x1d0] -- puts the ctx in r0
CTX_LOAD_OLD = 0xE59F01D0
CTX_POOL = 0x02146210            # -> 0x022952E4, the ctx the throttled call takes
CTX_VALUE = 0x022952E4
SUBSYSTEM = 0x02159F1C           # the throttled subsystem update
REJOIN = 0x02146040              # the instruction after the hooked bl

COUNTER = 0x02294534             # [0x022943F8+0x13C], the sub-pass counter
CTX_TO_COUNTER = CTX_VALUE - COUNTER          # 0xDB0, fits the 4095 ldr immediate

# The stub's home: the free tail of ov3 dead block 0x021B54E0 (44 B, 28 B claimed
# by escuridao).  Quoted from docs/engine/allocations.yaml:
#   - addr: 0x021B54E0  size: 44  used: 28  owners: [escuridao]
STUB = 0x021B54FC
STUB_LEN = 16
STUB_BLOCK_END = 0x021B54E0 + 44
STUB_ORIG = bytes.fromhex("01409b489b4a48431018002600251590")   # native dead-leaf bytes

# The mode getter's field, read only as a build-time sanity note (not patched).
MODE_ELSE_SITE = 0x02146000
MODE_ELSE_OLD = 0xE1A07005       # mov r7, r5  -- the r7 = 0 (normal) path


def _b(frm: int, to: int, link: bool = False, cond: int = 0xE) -> int:
    """Encode an ARM B/BL from *frm* to *to* with condition *cond*."""
    off = (to - (frm + 8)) >> 2
    assert -(1 << 23) <= off < (1 << 23), f"branch {frm:08X}->{to:08X} out of range"
    return (cond << 28) | (0xB000000 if link else 0xA000000) | (off & 0xFFFFFF)


def build_stub(base: int = STUB) -> bytes:
    """The 16-byte ARM throttle stub.

        ldr  r12, [r0, #-0xDB0]     ; r12 = [0x02294534], the sub-pass counter
        cmp  r12, #0                ; first pass of this rendered frame?
        bleq 0x02159F1C             ; yes -> do the call the hook displaced
        b    0x02146040             ; rejoin the frame body either way

    r0 (the ctx argument) is untouched; r12 and LR are caller-saved and already
    clobbered by every `bl` in the frame body, and the frame function returns via
    `pop {r3-r7,pc}` so the live LR is dead here.  Flags are not read at REJOIN.
    """
    assert 0 < CTX_TO_COUNTER <= 0xFFF, "ctx->counter offset no longer fits an ldr immediate"
    words = [
        0xE5100000 | (0xC << 12) | CTX_TO_COUNTER,   # ldr r12,[r0,#-0xDB0]
        0xE35C0000,                                   # cmp r12,#0
        _b(base + 8, SUBSYSTEM, link=True, cond=0x0),  # bleq SUBSYSTEM
        _b(base + 12, REJOIN),                        # b REJOIN
    ]
    blob = b"".join(struct.pack("<I", w) for w in words)
    assert len(blob) == STUB_LEN
    return blob


def _w(ov: bytearray, addr: int) -> int:
    return struct.unpack_from("<I", ov, addr - RAM_BASE)[0]


def _setw(ov: bytearray, addr: int, val: int) -> None:
    struct.pack_into("<I", ov, addr - RAM_BASE, val)


def main(speed: int = SPEED, src: str = SRC, out: str = OUT, write_text: bool = False) -> None:
    assert 1 <= speed <= 256, "speed must be 1..256"
    bound = speed - 1
    assert bound <= 0xFF, "loop bound needs a rotated ARM immediate; keep speed <= 256"
    assert STUB + STUB_LEN <= STUB_BLOCK_END, "stub overruns dead block 0x021B54E0"

    rom, data = load_overlay3(src)
    ov = bytearray(data)

    # --- preconditions: every site is the instruction we decoded ------------
    assert _w(ov, BOUND_SITE) == BOUND_OLD, f"{BOUND_SITE:08X} is not `cmp r1,r7`"
    assert _w(ov, HOOK_SITE) == HOOK_OLD, f"{HOOK_SITE:08X} is not `bl 0x02159F1C`"
    assert _w(ov, CTX_LOAD_SITE) == CTX_LOAD_OLD, f"{CTX_LOAD_SITE:08X} is not the ctx load"
    assert _w(ov, CTX_POOL) == CTX_VALUE, "ctx literal moved; the -0xDB0 offset is invalid"
    assert _w(ov, MODE_ELSE_SITE) == MODE_ELSE_OLD, "r7 default path changed"
    assert bytes(ov[STUB - RAM_BASE:STUB - RAM_BASE + STUB_LEN]) == STUB_ORIG, (
        f"dead block tail 0x{STUB:08X} is not the native bytes -- someone else claimed it")

    # --- PART A -------------------------------------------------------------
    _setw(ov, BOUND_SITE, 0xE3510000 | bound)          # cmp r1, #speed-1

    # --- PART B -------------------------------------------------------------
    stub = build_stub()
    ov[STUB - RAM_BASE:STUB - RAM_BASE + STUB_LEN] = stub
    _setw(ov, HOOK_SITE, _b(HOOK_SITE, STUB))          # b STUB

    save_overlay3(rom, bytes(ov), out)
    print(f"battle speed: {speed} logic passes per frame "
          f"(cmp r1,#{bound} @0x{BOUND_SITE:08X}); throttle stub {STUB_LEN} B @0x{STUB:08X}")
    print(f"wrote {out}")


def verify(out: str = OUT) -> None:
    _, data = load_overlay3(out)
    ov = bytearray(data)

    got = _w(ov, BOUND_SITE)
    assert (got & 0xFFFFFF00) == 0xE3510000, f"PART A missing: {got:08X}"
    speed = (got & 0xFF) + 1

    assert _w(ov, HOOK_SITE) == _b(HOOK_SITE, STUB), "PART B hook missing"
    stub = bytes(ov[STUB - RAM_BASE:STUB - RAM_BASE + STUB_LEN])
    assert stub == build_stub(), f"stub mismatch: {stub.hex()}"
    assert STUB + STUB_LEN <= STUB_BLOCK_END, "stub overruns its dead block"

    # the stub's operands must still point where we think
    assert _w(ov, CTX_POOL) == CTX_VALUE, "ctx literal moved under the stub"
    assert _w(ov, CTX_LOAD_SITE) == CTX_LOAD_OLD, "ctx load site changed"

    print(f"PASS battle_speed: {speed} passes/frame, throttle stub @0x{STUB:08X} "
          f"({STUB_LEN} B, ARM), ctx 0x{CTX_VALUE:08X} -> counter 0x{COUNTER:08X}")


if __name__ == "__main__":
    # Self-check: the emitted stub must decode to exactly the four intended
    # instructions and land inside its dead block.
    s = build_stub()
    assert s.hex() == struct.pack("<4I",
        0xE510CDB0, 0xE35C0000,
        _b(STUB + 8, SUBSYSTEM, link=True, cond=0x0),
        _b(STUB + 12, REJOIN)).hex(), s.hex()
    assert STUB % 4 == 0 and STUB + len(s) <= STUB_BLOCK_END
    print("stub self-check OK:", s.hex())
    main()
    verify()
