"""Diff two melonDS savestates (.ml1/.ml2) over the NDS main-RAM region.

melonDS savestates start with a 12-byte "MELN" header (magic + version + total
file length) followed by a chunk stream beginning with an "NDSG" tag. Empirically
(confirmed by locating a known overlay-3 byte pattern in a captured savestate and
solving for the offset), NDS main RAM (0x02000000, 4MB) is mapped at a fixed file
offset of 0x3C in this format -- i.e. right after the header, with no further
chunk-length parsing needed for this specific region.

Usage:
    python -m otn_enhanced.tools.savestate_diff before.ml1 after.ml2 [--start ADDR --size N]
"""
from __future__ import annotations

import argparse

RAM0 = 0x02000000
RAM_SIZE = 4 * 1024 * 1024   # 4MB NDS main RAM
FILE_OFF_OF_RAM0 = 0x3C      # file offset of RAM address 0x02000000 in a melonDS savestate


def ram_to_file_offset(addr: int) -> int:
    return FILE_OFF_OF_RAM0 + (addr - RAM0)


def diff_region(a: bytes, b: bytes, start: int, size: int) -> list[tuple[int, int]]:
    """Return a list of (ram_addr_start, ram_addr_end) byte runs that differ."""
    fo = ram_to_file_offset(start)
    seg_a = a[fo:fo + size]
    seg_b = b[fo:fo + size]
    runs = []
    i = 0
    n = len(seg_a)
    while i < n:
        if seg_a[i] != seg_b[i]:
            j = i
            while j < n and seg_a[j] != seg_b[j]:
                j += 1
            runs.append((start + i, start + j))
            i = j
        else:
            i += 1
    return runs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--start", type=lambda s: int(s, 0), default=RAM0)
    ap.add_argument("--size", type=lambda s: int(s, 0), default=RAM_SIZE)
    args = ap.parse_args()

    with open(args.before, "rb") as f:
        a = f.read()
    with open(args.after, "rb") as f:
        b = f.read()

    fo = ram_to_file_offset(args.start)
    runs = diff_region(a, b, args.start, args.size)
    print(f"region 0x{args.start:08X}..0x{args.start + args.size:08X}: {len(runs)} diff run(s)")
    for s, e in runs:
        sa = a[fo + (s - args.start):fo + (e - args.start)]
        sb = b[fo + (s - args.start):fo + (e - args.start)]
        print(f"  0x{s:08X}-0x{e:08X} ({e - s}B): {sa.hex()} -> {sb.hex()}")


if __name__ == "__main__":
    main()
