"""Dump the Hyper Librarian black-box recorder + summon state from a melonDS savestate.

Reads one .ml* savestate captured while a duel is running on a ROM built with
hyper_librarian (round 16) and prints everything the in-game test matrix
needs, with no debugger:

  * the recorder counters (CAVE_LIB_SCRATCH: +0x1C hook fires, +0x14
    proper-Synchro passes, +0x18 draws performed) and the dedup latch;
  * the summon descriptor (0x02298A28: packed ref +0xC, cid +0xE);
  * both players' recent-summon lists (player+0x124, count at +0xC) decoded
    field by field (cid / side bit14 / bit15 flag / instance index bits23-30 /
    packed ref), the list 0x021A25A0 searches;
  * both players' 5 monster-zone words with the same decoding (face-down =
    bit22) so the packed-ref self-exclusion compare can be eyeballed.

The main-RAM file offset is AUTO-DETECTED by locating the native prologue of
0x021A25A0 (savestate layouts differ between melonDS versions: 0x3C in the
build savestate_diff.py was calibrated on, 0x24 in the 2026-07 captures).

Usage:
    python -m otn_enhanced.tools.librarian_recorder path/to/state.ml1
"""
from __future__ import annotations

import struct
import sys

RAM0 = 0x02000000

# Native prologue bytes of the recent-summon-list lookup 0x021A25A0 (overlay 3,
# untouched by every patch in the chain): PUSH {R3,R4,R5,LR}; MOV R2,#1;
# AND R2,R0; LDR R0,[PC,#0x38]; LDR R4,[PC,#0x38]; MUL R0,R2
ANCHOR_ADDR = 0x021A25A0
ANCHOR_BYTES = bytes.fromhex("38b5012202400e480e4c5043")

# Addresses shared with hyper_librarian / ov5_cave (duplicated as plain
# ints so this parser stays importable without the patch chain's dependencies).
SCRATCH = 0x0239A588        # ov5_cave.CAVE_LIB_SCRATCH
LATCH = 0x0239A580          # ov5_cave.CAVE_LIB_LATCH
SUMMON_DESC = 0x02298A28
PLAYER = 0x0229AC94
STRIDE = 0xB3C
LIST124_OFF = 0x124         # per-player list searched by 0x021A25A0 (count at +0xC).
                            # NOT recent summons -- fresh summons never appear here
                            # (live-proven, all_patches.ml1/ml2); role unknown.
LIST55C_OFF = 0x55C         # per-player sent-to-GY list searched by 0x021A2510
                            # (count at +0x14; grew by exactly the two Synchro
                            # materials across the ml1->ml2 Synchro Summon)
ZONE_OFF = 0x34             # 5 monster zones, 0x14 bytes each
DONOR_CID = 0x1225          # the Librarian's cid (Amphibious Bugroth; was 0x2338)


def find_ram_offset(buf: bytes) -> int:
    """Locate the file offset of RAM 0x02000000 via the 0x021A25A0 anchor."""
    want = ANCHOR_ADDR - RAM0
    i = buf.find(ANCHOR_BYTES)
    while i != -1:
        if i >= want:                       # candidate base must be >= 0
            return i - want
        i = buf.find(ANCHOR_BYTES, i + 1)
    raise SystemExit("anchor 0x021A25A0 not found -- is a duel loaded in this savestate?")


def decode_word(w: int) -> str:
    cid = w & 0x3FFF
    side = (w >> 14) & 1
    b15 = (w >> 15) & 1
    idx = (w >> 23) & 0xFF
    ref = (idx << 1) | side
    tag = "  <-- LIBRARIAN" if cid == DONOR_CID else ""
    return (f"{w:08X}  cid={cid:04X} side={side} bit15={b15} "
            f"inst_idx=0x{idx:02X} packed_ref=0x{ref:04X}{tag}")


def main(path: str) -> None:
    buf = open(path, "rb").read()
    off0 = find_ram_offset(buf)
    print(f"{path}: main RAM at file offset 0x{off0:X}")

    def u32(addr: int) -> int:
        o = off0 + (addr - RAM0)
        return struct.unpack_from("<I", buf, o)[0]

    def u16(addr: int) -> int:
        o = off0 + (addr - RAM0)
        return struct.unpack_from("<H", buf, o)[0]

    print("\nrecorder (CAVE_LIB_SCRATCH):")
    print(f"  +0x1C hook fires          = {u32(SCRATCH + 0x1C)}")
    print(f"  +0x14 IS_SYNCHRO passes   = {u32(SCRATCH + 0x14)}   (ROUND 18: a Synchro-type card was summoned)")
    print(f"  +0x18 draws performed     = {u32(SCRATCH + 0x18)}")
    print(f"  +0x0C last desc kind      = 0x{u32(SCRATCH + 0x0C):04X}")
    ref = u32(SCRATCH + 0x10)
    print(f"  +0x10 last desc +0xC ref  = 0x{ref:04X}")
    print(f"  dedup latch               = 0x{u32(LATCH):08X}  ((ref<<16)|cid of last handled summon)")

    print("\nsummon descriptor 0x02298A28:")
    print(f"  subject +0x2 = 0x{u16(SUMMON_DESC + 2):04X}   kind +0x6 = 0x{u16(SUMMON_DESC + 6):04X}")
    print(f"  packed ref +0xC = 0x{u16(SUMMON_DESC + 0xC):04X}   cid +0xE = 0x{u16(SUMMON_DESC + 0xE):04X}")

    for side in (0, 1):
        base = PLAYER + side * STRIDE
        cnt124 = u32(base + 0xC)
        cnt55c = u32(base + 0x14)
        print(f"\nside {side}:")
        for slot in range(5):
            w = u32(base + ZONE_OFF + slot * 0x14)
            if w & 0x3FFF:
                fd = (w >> 22) & 1
                print(f"  zone[{slot}]  = {decode_word(w)}  facedown={fd}")
        print(f"  list+0x124 (0x021A25A0's; count {cnt124}):")
        for i in range(min(cnt124, 16)):
            print(f"    [{i:2}] = {decode_word(u32(base + LIST124_OFF + i * 4))}")
        print(f"  list+0x55C (sent-to-GY; count {cnt55c}):")
        for i in range(min(cnt55c, 16)):
            print(f"    [{i:2}] = {decode_word(u32(base + LIST55C_OFF + i * 4))}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
