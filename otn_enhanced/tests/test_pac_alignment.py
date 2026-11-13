"""Self-check for the v1 PAC repacker's inner-file alignment.

Run:  uv run python -m otn_enhanced.tests.test_pac_alignment

Guards the invariant that broke silently before 2026-09-08: every inner file of
bin2.pac starts on a 0x200 boundary, and the repacker used to preserve the
inter-file GAP LENGTH rather than that boundary -- so growing any inner file by a
non-0x200 amount pushed 90 of the 99 files onto odd addresses. card_indx_*.bin is
a u32 offset table, so a misaligned load there reads rotated garbage.
"""
from __future__ import annotations

import sys

import ndspy.rom

from otn_enhanced.rom.pac import build_modified_pac, parse_format_v1

ROM = "data/over_the_nexus/working/rom.nds"
PAC = "Data_arc_pac/bin2.pac"


def _iter_paths(folder, prefix=""):
    for name in folder.files:
        yield prefix + name
    for sub_name, sub in folder.folders:
        yield from _iter_paths(sub, prefix + sub_name + "/")


def _load_bin2() -> bytes:
    rom = ndspy.rom.NintendoDSRom.fromFile(ROM)
    path = next(p for p in _iter_paths(rom.filenames) if p.lower().endswith("bin2.pac"))
    return bytes(rom.files[rom.filenames.idOf(path)])


def main() -> int:
    original = _load_bin2()
    archive = parse_format_v1(original, PAC)
    files = archive.get_files_sorted_by_address()

    # The invariant the repacker has to preserve.
    assert all(f.address % 0x200 == 0 for f in files), \
        "bin2.pac inner files are not 0x200-aligned in the stock ROM"
    assert all(
        not any(original[files[i].address + files[i].size:files[i + 1].address])
        for i in range(len(files) - 1)
    ), "an inter-file gap holds non-zero bytes; it is not pure padding"

    index = {f.get_clean_name().lower(): i for i, f in enumerate(archive.files)}
    desc_i = index["card_desc_e.bin"]
    desc = archive.files[desc_i]
    body = original[desc.address:desc.address + desc.size]

    # 1. No-op edit round-trips byte-for-byte.
    assert build_modified_pac(original, PAC, {desc_i: body}) == original, \
        "same-size replacement no longer reproduces the PAC byte-for-byte"

    # 2. A growth that is NOT a multiple of 0x200 keeps every file on its boundary,
    #    and leaves every untouched file byte-identical.
    grown = build_modified_pac(original, PAC, {desc_i: body + b"X" * 101 + b"\x00"})
    rebuilt = parse_format_v1(grown, PAC)
    misaligned = [f.get_clean_name() for f in rebuilt.files if f.address % 0x200]
    assert not misaligned, f"{len(misaligned)} inner files misaligned after growth: {misaligned[:5]}"

    by_name = {f.get_clean_name().lower(): f for f in rebuilt.files}
    for old in archive.files:
        name = old.get_clean_name().lower()
        if name == "card_desc_e.bin":
            continue
        new = by_name[name]
        assert grown[new.address:new.address + new.size] == \
            original[old.address:old.address + old.size], f"{name} changed content"

    new_desc = by_name["card_desc_e.bin"]
    assert new_desc.size == desc.size + 102, "grown file's table size is wrong"
    assert grown[new_desc.address:new_desc.address + new_desc.size] == body + b"X" * 101 + b"\x00", \
        "grown file's content is wrong"

    print(f"OK  {len(archive.files)} inner files, boundary 0x200")
    print(f"OK  no-op repack byte-identical ({len(original):,} B)")
    print(f"OK  +102 B growth -> {len(grown):,} B, all files still 0x200-aligned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
