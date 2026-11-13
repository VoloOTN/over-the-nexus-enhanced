"""Check whether the ov3 BSS cave windows survived live play (canary verdict).

Reads every melonDS savestate captured from the canary ROM and asserts that both
windows are still entirely 0xA5.  Any other byte means the engine reclaimed that
address and the window must be shrunk below it -- do NOT work around a failure.

The main-RAM file offset is AUTO-DETECTED via the ov3 prologue anchor at
0x021A25A0 (melonDS layouts differ between builds: 0x3C in the one
savestate_diff.py was calibrated on, 0x24 in the 2026-07 captures).  A state
whose anchor does not resolve is SKIPPED with a warning -- it is either a
different melonDS build or not inside a duel.

Usage:
    python -m otn_enhanced.tools.ov3_cave_check [state.ml1 ...]

With no arguments it globs data/over_the_nexus/working/rom_ov3_canary.ml*.
"""
from __future__ import annotations

import glob
import os
import sys

from otn_enhanced.effects import ov3_cave

RAM0 = 0x02000000
RAM_SIZE = 4 * 1024 * 1024

# Native prologue of the recent-summon-list lookup 0x021A25A0 (ov3, untouched by
# every patch in the chain) -- same anchor librarian_recorder.py uses.
ANCHOR_ADDR = 0x021A25A0
ANCHOR_BYTES = bytes.fromhex("38b5012202400e480e4c5043")

DEFAULT_GLOB = "data/over_the_nexus/working/rom_ov3_canary.ml*"


def find_ram_offset(buf: bytes) -> int | None:
    """Locate the file offset of RAM 0x02000000, or None if the anchor is absent."""
    want = ANCHOR_ADDR - RAM0
    i = buf.find(ANCHOR_BYTES)
    while i != -1:
        off = i - want
        if off >= 0 and buf[off + want:off + want + len(ANCHOR_BYTES)] == ANCHOR_BYTES:
            if off + RAM_SIZE <= len(buf):
                return off
        i = buf.find(ANCHOR_BYTES, i + 1)
    return None


def check_state(path: str) -> tuple[bool, list[str]]:
    """Return (ok, messages) for one savestate."""
    buf = open(path, "rb").read()
    off0 = find_ram_offset(buf)
    if off0 is None:
        return True, [f"  SKIP (anchor 0x{ANCHOR_ADDR:08X} not found -- not a duel, "
                      f"or a different melonDS layout)"]

    msgs = [f"  main RAM at file offset 0x{off0:X}"]

    # --- control probe first: it decides how to READ the window results ---
    plo, phi = ov3_cave.NATIVE_PROBE
    pseg = buf[off0 + (plo - RAM0):off0 + (phi - RAM0)]
    probe_ok = all(b == ov3_cave.CANARY_BYTE for b in pseg)
    msgs.append(f"  [{'PASS' if probe_ok else 'FAIL'}] CONTROL PROBE "
                f"0x{plo:08X}-0x{phi:08X} (ov3 NATIVE data): "
                f"{'0xA5 intact -- our ov3 image DID reach RAM' if probe_ok else 'cleared -- our ov3 image did NOT reach RAM'}")

    ok = True
    for name, (lo, hi) in (("PRIMARY  ", ov3_cave.WINDOW_PRIMARY),
                           ("SECONDARY", ov3_cave.WINDOW_SECONDARY)):
        seg = buf[off0 + (lo - RAM0):off0 + (hi - RAM0)]
        bad = [i for i, b in enumerate(seg) if b != ov3_cave.CANARY_BYTE]
        if not bad:
            msgs.append(f"  [PASS] {name} 0x{lo:08X}-0x{hi:08X} "
                        f"({(hi - lo) / 1024:.1f} KB) intact")
            continue
        ok = False
        first, last = lo + bad[0], lo + bad[-1]
        vals = sorted({seg[i] for i in bad})[:8]
        msgs.append(f"  [FAIL] {name} 0x{lo:08X}-0x{hi:08X}: "
                    f"{len(bad)} byte(s) reclaimed, first 0x{first:08X} last 0x{last:08X}, "
                    f"values {[hex(v) for v in vals]}")
        if probe_ok:
            msgs.append(f"         -> safe sub-window is 0x{lo:08X}-0x{first & ~0xFFF:08X} "
                        f"({max(0, (first & ~0xFFF) - lo) / 1024:.1f} KB); "
                        f"re-test before claiming any slot")
        else:
            msgs.append("         -> IGNORE this window result: the control probe "
                        "failed, so nothing was loaded to compare against")
    return ok, msgs


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    paths = argv or sorted(glob.glob(DEFAULT_GLOB))
    if not paths:
        print(f"no savestates matched {DEFAULT_GLOB}")
        print("Build the canary ROM (_build_ov3_canary.py), play all five duel modes,")
        print("save states, then re-run this checker.")
        return 2

    print(f"canary byte = 0x{ov3_cave.CANARY_BYTE:02X};  "
          f"windows = {[(hex(a), hex(b)) for a, b in ov3_cave.WINDOWS]}\n")
    all_ok = True
    checked = 0
    for p in paths:
        print(os.path.basename(p) + ":")
        ok, msgs = check_state(p)
        for m in msgs:
            print(m)
        if not any("SKIP" in m for m in msgs):
            checked += 1
        all_ok &= ok
        print()

    if checked == 0:
        print("VERDICT: INCONCLUSIVE -- no state had a duel loaded.")
        return 2
    print(f"VERDICT: {'PASS' if all_ok else 'FAIL'}  ({checked} state(s) checked)")
    if all_ok:
        print("Both windows survive live play -- safe to claim CAVE3_* slots.")
    else:
        print("Shrink the failing window below the first reclaimed address and re-run "
              "the canary. Do not work around this.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
