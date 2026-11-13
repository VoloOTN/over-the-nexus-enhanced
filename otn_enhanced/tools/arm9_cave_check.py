"""Check whether the ARM9 main-section cave survived live play (round-3 verdict).

Reads melonDS savestates captured from rom_arm9_canary.nds and asserts that the
appended region [0x020AF120, 0x020B7120) is still entirely 0xA5. A 64-byte
control probe at 0x020AD8E0 (dead zeros inside the ORIGINAL static module, which
is loaded and never cleared) decides how to read the region result:

    probe 0xA5 + region 0xA5   -> PASS: the ARM9 cave is real, mode-independent
    probe 0xA5 + region wiped  -> the crt0 clear or the runtime allocator still
                                  owns it; the first reclaimed offset is reported
    probe 0x00                 -> the grown ARM9 never reached RAM (build/boot
                                  broke); the region verdict is void

RAM0 file offset is auto-detected via the ov3 prologue anchor at 0x021A25A0, so
a NON-duel savestate (deck editor / story map) -- where ov3 is not loaded -- is
handled specially: the anchor is absent, but the ARM9 static module IS resident,
so we fall back to detecting RAM0 via the arm9 entry vector at 0x02000000. That
is the whole point of an ARM9 cave: it must survive where ov3 does not.

Usage:
    python -m otn_enhanced.tools.arm9_cave_check [state.ml1 ...]
"""
from __future__ import annotations

import glob
import os
import sys

RAM0 = 0x02000000
RAM_SIZE = 4 * 1024 * 1024
CANARY_BYTE = 0xA5

APPEND_LO, APPEND_HI = 0x020AF120, 0x020B7120
PROBE_LO, PROBE_HI = 0x020AD8E0, 0x020AD920

# ov3 anchor (duel states); librarian_recorder / ov3_cave_check use the same.
ANCHOR_ADDR = 0x021A25A0
ANCHOR_BYTES = bytes.fromhex("38b5012202400e480e4c5043")

# ARM9 static-module anchor for NON-duel states: the first bytes at 0x02000000
# are the arm9 secure-area / entry, stable across modes. Captured from the clean
# ROM's decompressed arm9 (constant in RAM in every savestate we have).
ARM9_ANCHOR_ADDR = 0x02000004      # skip the very first word (branch, can vary)
DEFAULT_GLOB = "data/over_the_nexus/working/rom_arm9_canary.ml*"


def _probe_offset(buf: bytes, ram_addr: int, want: bytes) -> int | None:
    off = ram_addr - RAM0
    i = buf.find(want)
    while i != -1:
        base = i - off
        if base >= 0 and base + RAM_SIZE <= len(buf):
            return base
        i = buf.find(want, i + 1)
    return None


def find_ram_offset(buf: bytes) -> tuple[int | None, str]:
    """Return (file_offset_of_RAM0, how). Try the ov3 anchor, then the arm9 anchor."""
    off = _probe_offset(buf, ANCHOR_ADDR, ANCHOR_BYTES)
    if off is not None:
        return off, "ov3-anchor (duel)"
    # non-duel: use a stable 16-byte signature from the clean arm9 at 0x02000004
    sig = _arm9_sig()
    if sig is not None:
        off = _probe_offset(buf, ARM9_ANCHOR_ADDR, sig)
        if off is not None:
            return off, "arm9-anchor (non-duel)"
    return None, "no anchor"


_ARM9_SIG_CACHE: bytes | None = None
_ARM9_SIG_TRIED = False


def _arm9_sig() -> bytes | None:
    global _ARM9_SIG_CACHE, _ARM9_SIG_TRIED
    if _ARM9_SIG_TRIED:
        return _ARM9_SIG_CACHE
    _ARM9_SIG_TRIED = True
    try:
        import ndspy.code
        import ndspy.rom
        rom = ndspy.rom.NintendoDSRom.fromFile("data/over_the_nexus/working/rom.nds")
        d = bytes(ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress).sections[0].data)
        _ARM9_SIG_CACHE = d[ARM9_ANCHOR_ADDR - RAM0:ARM9_ANCHOR_ADDR - RAM0 + 16]
    except Exception:
        _ARM9_SIG_CACHE = None
    return _ARM9_SIG_CACHE


def check_state(path: str) -> tuple[bool, bool, list[str]]:
    """Return (ok, counted, messages)."""
    buf = open(path, "rb").read()
    off0, how = find_ram_offset(buf)
    if off0 is None:
        return True, False, ["  SKIP (no usable anchor -- unknown melonDS layout)"]

    msgs = [f"  main RAM at file offset 0x{off0:X}  [{how}]"]
    pseg = buf[off0 + (PROBE_LO - RAM0):off0 + (PROBE_HI - RAM0)]
    probe_ok = all(b == CANARY_BYTE for b in pseg)
    msgs.append(f"  [{'PASS' if probe_ok else 'FAIL'}] CONTROL PROBE "
                f"0x{PROBE_LO:08X}-0x{PROBE_HI:08X}: "
                f"{'0xA5 intact -- grown ARM9 reached RAM' if probe_ok else 'cleared -- ARM9 image did NOT load'}")

    seg = buf[off0 + (APPEND_LO - RAM0):off0 + (APPEND_HI - RAM0)]
    bad = [i for i, b in enumerate(seg) if b != CANARY_BYTE]
    if not bad:
        msgs.append(f"  [PASS] APPENDED REGION 0x{APPEND_LO:08X}-0x{APPEND_HI:08X} "
                    f"({(APPEND_HI - APPEND_LO) / 1024:.0f} KB) intact")
        return True, True, msgs

    first, last = APPEND_LO + bad[0], APPEND_LO + bad[-1]
    vals = sorted({seg[i] for i in bad})[:8]
    msgs.append(f"  [FAIL] APPENDED REGION: {len(bad)} byte(s) reclaimed, "
                f"first 0x{first:08X} last 0x{last:08X}, values {[hex(v) for v in vals]}")
    if probe_ok:
        msgs.append(f"         -> the region is owned live from 0x{first:08X}; the ARM9 "
                    f"arena-lo raise did not fully protect it (raise more copies / larger).")
    else:
        msgs.append("         -> IGNORE: control probe failed, nothing loaded to compare.")
    return False, True, msgs


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    paths = argv or sorted(glob.glob(DEFAULT_GLOB))
    if not paths:
        print(f"no savestates matched {DEFAULT_GLOB}")
        print("Build the canary (_build_arm9_canary.py), play all modes + one non-duel")
        print("screen, save states, then re-run this checker.")
        return 2

    print(f"canary byte = 0x{CANARY_BYTE:02X};  appended region "
          f"0x{APPEND_LO:08X}-0x{APPEND_HI:08X} ({(APPEND_HI - APPEND_LO) // 1024} KB)\n")
    all_ok = True
    counted = 0
    for p in paths:
        print(os.path.basename(p) + ":")
        ok, cnt, msgs = check_state(p)
        for m in msgs:
            print(m)
        counted += 1 if cnt else 0
        all_ok &= ok
        print()

    if counted == 0:
        print("VERDICT: INCONCLUSIVE -- no state had a usable anchor.")
        return 2
    print(f"VERDICT: {'PASS' if all_ok else 'FAIL'}  ({counted} state(s) checked)")
    if all_ok:
        print("The ARM9 static cave survives in every tested mode -- mode-independent, "
              "safe to build on. Promote to ov9_cave.py + claim slots.")
    else:
        print("Report the first reclaimed address; do not work around it.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
