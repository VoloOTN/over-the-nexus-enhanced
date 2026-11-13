"""Skip the summon / card-activation animations.

Ported from the community AR code "Remove Summoning And Card Activation
Animation" (decoded 2026-09-10, see notes/battle-speed-ar-findings.md). Both of
its guard words match this EU (BYYP) ROM byte-for-byte:
    [0x02147B00] == 0xE20310FF   and   [0x02148B00] == 0xE59F5F34

MECHANISM
---------
0x02148B08 is an 80-case animation state machine:

    02148B04  cmp   r6, #0x4f
    02148B08  addls pc, pc, r6, lsl #2      ; pc reads as 0x02148B10
    02148B0C  b     <default>               ; r6 > 0x4F falls through to here
    02148B10  b     <case 0>                ; <-- table base
    ...       (80 `b` entries, ending 0x02148C4C)
    02148C50  <-- the function's own epilogue, immediately after the table

The epilogue at 0x02148C50 does the two optional `[sp,#0x290]` callbacks
(0x021468C4 / 0x02146944) and then:

    02148C70  add sp, sp, #0x264
    02148C74  mov r0, #1
    02148C78  pop {r4-r8, sb, sl, fp, lr}
    02148C7C  add sp, sp, #0x10
    02148C80  bx  lr

i.e. "this animation state is DONE, return 1". Retargeting a case's table entry
straight at 0x02148C50 makes that animation complete instantly through the
engine's own completion path -- it is not a skipped/short-circuited frame, it is
the same return value and the same teardown the animation would have produced
after playing out. That is why this is safe in a way that clamping a timer is not.

⚠️ Case 79 (the LAST table entry, 0x02148C4C) already branches to 0x02148C50
natively -- `b` with offset -1. So "route this case straight to the epilogue" is
not our invention: it is the engine's own encoding for "this animation state does
nothing, report done". That is the strongest evidence available that the five
retargets are well-formed, and it is why NATIVE_DONE exists below rather than the
verifier simply asserting that nothing else reaches 0x02148C50.

WHAT IS WRITTEN: five HALFWORDS (the low half of five `b` instructions -- the
branch offset), all ov3, no stub, no cave, no allocation claim.

    entry       case  before      after
    02148B88     30   0214A5C0 -> 02148C50
    02148B98     34   0214A284 -> 02148C50
    02148BC0     44   021497B0 -> 02148C50
    02148BF0     56   0214AD14 -> 02148C50
    02148BF4     57   0214ADEC -> 02148C50

Only 5 of the 80 cases are touched, so every other animation (attacks, damage
steps, phase banners, ...) still plays. If more should go, add the case index to
SKIP_CASES -- the offset is computed, not hardcoded.

INDEPENDENT OF battle_speed: different function, disjoint edit sites
(0x021460FC / 0x0214603C / 0x021B54FC vs 0x02148B88..0x02148BF4). The two
compose by simply running both over the same ov3 image.

STATUS: AWAITING IN-GAME TEST.
"""
from __future__ import annotations

import struct

from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3, RAM_BASE

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_skip_anim.nds"

# --- the dispatch, asserted before anything is written ---------------------
GUARD_A = (0x02147B00, 0xE20310FF)      # AR guard 1 (and r1, r3, #0xFF)
GUARD_B = (0x02148B00, 0xE59F5F34)      # AR guard 2 (ldr r5, [pc, #0xf34])
CMP_SITE = 0x02148B04
CMP_WORD = 0xE356004F                   # cmp r6, #0x4f
ADDPC_SITE = 0x02148B08
ADDPC_WORD = 0xE08FF106                 # addls pc, pc, r6, lsl #2  (cond ls = 0x9)
TABLE = ADDPC_SITE + 8                  # 0x02148B10 -- pc-relative base of the table
N_CASES = 0x50                          # 80, from the `cmp r6,#0x4f`
DONE = 0x02148C50                       # the shared epilogue: "done, return 1"

# The five cases the AR code retargets, with the native target each must still
# have before we touch it (a stale ROM must fail loudly, not silently mis-patch).
SKIP_CASES: dict[int, int] = {
    30: 0x0214A5C0,
    34: 0x0214A284,
    44: 0x021497B0,
    56: 0x0214AD14,
    57: 0x0214ADEC,
}

# Cases that point at DONE in the STOCK ROM (the engine's own "nothing to animate,
# report done" encoding). Not ours; the verifier must not read them as strays.
NATIVE_DONE: frozenset[int] = frozenset({79})


def _w(ov: bytearray, addr: int) -> int:
    return struct.unpack_from("<I", ov, addr - RAM_BASE)[0]


def _entry(case: int) -> int:
    assert 0 <= case < N_CASES, f"case {case} outside the {N_CASES}-entry table"
    return TABLE + case * 4


def _branch_target(entry_addr: int, word: int) -> int:
    off = word & 0xFFFFFF
    if off & 0x800000:
        off -= 0x1000000
    return entry_addr + 8 + off * 4


def _retarget(entry_addr: int, to: int) -> int:
    """Rebuild an unconditional ARM `b` at *entry_addr* so it lands on *to*."""
    off = (to - (entry_addr + 8)) >> 2
    assert 0 <= off <= 0xFFFF, (
        f"offset {off:#x} for {entry_addr:08X}->{to:08X} does not fit the low halfword; "
        "the AR code only rewrites 16 bits, so a forward branch under 256 KB is required")
    return 0xEA000000 | off


def main(src: str = SRC, out: str = OUT, cases: dict[int, int] | None = None,
         write_text: bool = False) -> None:
    cases = SKIP_CASES if cases is None else cases
    rom, data = load_overlay3(src)
    ov = bytearray(data)

    for addr, want in (GUARD_A, GUARD_B):
        assert _w(ov, addr) == want, f"guard {addr:08X} = {_w(ov, addr):08X}, want {want:08X}"
    assert _w(ov, CMP_SITE) == CMP_WORD, "case count changed"
    assert (_w(ov, ADDPC_SITE) & 0x0FFFFFFF) == (ADDPC_WORD & 0x0FFFFFFF), "dispatch changed"

    # The engine's own no-op cases must already point at DONE -- this is what
    # licenses the retarget below, so it is asserted, not assumed.
    for c in NATIVE_DONE:
        e = _entry(c)
        assert _branch_target(e, _w(ov, e)) == DONE, (
            f"case {c} was expected to natively target the epilogue {DONE:08X}")

    for case, native in sorted(cases.items()):
        e = _entry(case)
        cur = _w(ov, e)
        assert (cur & 0xFF000000) == 0xEA000000, f"case {case} @{e:08X} is not a `b`"
        got = _branch_target(e, cur)
        assert got == native, (
            f"case {case} @{e:08X} targets {got:08X}, expected the native {native:08X}")
        struct.pack_into("<I", ov, e - RAM_BASE, _retarget(e, DONE))
        print(f"  case {case:2d} @0x{e:08X}: 0x{native:08X} -> 0x{DONE:08X}")

    save_overlay3(rom, bytes(ov), out)
    print(f"skip animations: {len(cases)} of {N_CASES} cases routed to the epilogue")
    print(f"wrote {out}")


def verify(out: str = OUT, cases: dict[int, int] | None = None) -> None:
    cases = SKIP_CASES if cases is None else cases
    _, data = load_overlay3(out)
    ov = bytearray(data)

    assert _w(ov, CMP_SITE) == CMP_WORD, "case count changed"
    assert (_w(ov, ADDPC_SITE) & 0x0FFFFFFF) == (ADDPC_WORD & 0x0FFFFFFF), "dispatch changed"

    for case in sorted(cases):
        e = _entry(case)
        assert _w(ov, e) == _retarget(e, DONE), f"case {case} @{e:08X} not retargeted"

    # every OTHER case must still play its own animation -- i.e. nothing else got
    # routed to the epilogue by accident. NATIVE_DONE is stock, not ours.
    others = [c for c in range(N_CASES) if c not in cases]
    for c in others:
        e = _entry(c)
        w = _w(ov, e)
        assert (w & 0xFF000000) == 0xEA000000, f"case {c} is no longer a `b`"
        if c not in NATIVE_DONE:
            assert _branch_target(e, w) != DONE, f"case {c} was retargeted by accident"
        else:
            assert _branch_target(e, w) == DONE, f"stock no-op case {c} was moved"

    print(f"PASS skip_animations: {len(cases)} cases -> 0x{DONE:08X}, "
          f"{len(others)} cases untouched, dispatch intact")


if __name__ == "__main__":
    # Self-check: the offset arithmetic must round-trip against the real table.
    for case, native in SKIP_CASES.items():
        e = _entry(case)
        assert _branch_target(e, _retarget(e, DONE)) == DONE, case
    assert _entry(0) == 0x02148B10 and _entry(N_CASES - 1) == 0x02148C4C
    print("table arithmetic self-check OK")
    main()
    verify()
