"""Prove the `compress_lz11` speedup is byte-identical to the version it replaces.

`lz_compression.compress_lz11` is 81% of `field_backgrounds`, which is 45% of the whole
build (see ``notes/field-backgrounds-cost.md``). The speedup is a loop-invariant hoist, so it
should change nothing at all -- but "should" is not a check.

This file keeps a VERBATIM copy of the pre-hoist implementation and asserts the live one agrees
with it byte for byte. It is deliberately self-contained: no ROM build, no session, no ndspy.

    uv run python -m otn_enhanced.tests.test_lz11

WHY A FROZEN COPY AND NOT A ROM DIFF: `lz_compression.py` sits outside `finished_patches/`, so
both the oracle chain and the new engine import the SAME function. A `--compare` between two
freshly-built chains would agree even if the compressor's output had changed. The frozen copy
below is the only thing that actually pins the old behaviour.
"""
from __future__ import annotations

import pathlib
import struct
import sys

from otn_enhanced.rom.lz_compression import compress_lz10, compress_lz11

CLEAN_SRC = pathlib.Path("data/over_the_nexus/backup/eu_apfix.nds")


def _compress_lz11_pre_hoist(data: bytes) -> bytes:
    """VERBATIM copy of lz_compression.compress_lz11 as of 2026-09-11, before the hoist.

    Do not tidy, reformat or "fix" this. Its only job is to be the old bytes.
    """
    output = bytearray()

    output.append(0x11)
    size = len(data)
    if size < 0x1000000:
        output.append(size & 0xFF)
        output.append((size >> 8) & 0xFF)
        output.append((size >> 16) & 0xFF)
    else:
        output.extend([0, 0, 0])
        output.extend(struct.pack('<I', size))

    pos = 0

    while pos < len(data):
        flags = 0
        block = bytearray()

        for i in range(8):
            if pos >= len(data):
                break

            best_length = 0
            best_disp = 0

            search_start = max(0, pos - 0x1000)

            for search_pos in range(search_start, pos):
                length = 0
                max_length = min(0x10110, len(data) - pos)  # LZ11 max length

                while length < max_length:
                    if data[search_pos + length] != data[pos + length]:
                        break
                    length += 1
                    if search_pos + length >= pos:
                        while length < max_length:
                            ref_pos = search_pos + (length % (pos - search_pos))
                            if data[ref_pos] != data[pos + length]:
                                break
                            length += 1
                        break

                if length >= 3 and length > best_length:
                    best_length = length
                    best_disp = pos - search_pos

            if best_length >= 3:
                flags |= (0x80 >> i)
                disp_encoded = best_disp - 1

                if best_length <= 0x10:
                    length_encoded = best_length - 1
                    byte1 = (length_encoded << 4) | ((disp_encoded >> 8) & 0x0F)
                    byte2 = disp_encoded & 0xFF
                    block.extend([byte1, byte2])
                elif best_length <= 0x110:
                    length_encoded = best_length - 0x11
                    byte1 = (length_encoded >> 4) & 0x0F
                    byte2 = ((length_encoded & 0x0F) << 4) | ((disp_encoded >> 8) & 0x0F)
                    byte3 = disp_encoded & 0xFF
                    block.extend([byte1, byte2, byte3])
                else:
                    length_encoded = best_length - 0x111
                    byte1 = 0x10 | ((length_encoded >> 12) & 0x0F)
                    byte2 = (length_encoded >> 4) & 0xFF
                    byte3 = ((length_encoded & 0x0F) << 4) | ((disp_encoded >> 8) & 0x0F)
                    byte4 = disp_encoded & 0xFF
                    block.extend([byte1, byte2, byte3, byte4])

                pos += best_length
            else:
                block.append(data[pos])
                pos += 1

        output.append(flags)
        output.extend(block)

    return bytes(output)


def _compress_lz10_pre_hoist(data: bytes) -> bytes:
    """VERBATIM copy of lz_compression.compress_lz10 as of 2026-09-11, before the hoist.

    `compress()` defaults to LZ10, and card_art plus five codecs call it, so this path
    carried the identical loop-invariant defect. Do not tidy this copy.
    """
    output = bytearray()

    output.append(0x10)
    size = len(data)
    if size < 0x1000000:
        output.append(size & 0xFF)
        output.append((size >> 8) & 0xFF)
        output.append((size >> 16) & 0xFF)
    else:
        output.extend([0, 0, 0])
        output.extend(struct.pack('<I', size))

    pos = 0

    while pos < len(data):
        flags = 0
        block = bytearray()

        for i in range(8):
            if pos >= len(data):
                break

            best_length = 0
            best_disp = 0

            search_start = max(0, pos - 0x1000)

            for search_pos in range(search_start, pos):
                length = 0
                max_length = min(18, len(data) - pos)  # Max length is 18 (15 + 3)

                while length < max_length:
                    if data[search_pos + length] != data[pos + length]:
                        break
                    length += 1
                    if search_pos + length >= pos:
                        while length < max_length:
                            ref_pos = search_pos + (length % (pos - search_pos))
                            if data[ref_pos] != data[pos + length]:
                                break
                            length += 1
                        break

                if length >= 3 and length > best_length:
                    best_length = length
                    best_disp = pos - search_pos
                    if length >= 18:  # Maximum possible length
                        break

            if best_length >= 3:
                flags |= (0x80 >> i)
                length_encoded = best_length - 3
                disp_encoded = best_disp - 1

                byte1 = ((length_encoded & 0x0F) << 4) | ((disp_encoded >> 8) & 0x0F)
                byte2 = disp_encoded & 0xFF

                block.append(byte1)
                block.append(byte2)
                pos += best_length
            else:
                block.append(data[pos])
                pos += 1

        output.append(flags)
        output.extend(block)

    return bytes(output)


def _lcg(n: int, seed: int = 0x1234567) -> bytes:
    """Deterministic pseudo-random bytes -- the incompressible worst case."""
    out = bytearray()
    x = seed
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)


def _cases() -> list[tuple[str, bytes]]:
    cases = [
        ("empty", b""),
        ("one byte", b"A"),
        ("two bytes (below min match)", b"AB"),
        ("all identical (maximal matches)", b"A" * 2048),
        ("periodic 256", bytes(range(256)) * 8),
        ("incompressible", _lcg(2048)),
        # the run-length path: a match that overlaps its own source
        ("overlapping run", b"XYZ" + b"Q" * 600 + b"XYZ" * 40),
        # --- the OVERLAP cases specifically. The `search_pos + best_length < pos` half of the
        # prune in compress_lz11/compress_lz10 exists because at/after `pos` the match length is
        # computed modulo (pos - search_pos), not from the raw byte. Data whose best matches run
        # right up to and past `pos` is what exercises that, so these are the cases that would
        # catch a prune written without the guard.
        ("period 2 (maximal overlap)", b"AB" * 1024),
        ("period 3 after a run", b"A" * 50 + b"ABC" * 400),
        ("period 5, odd length", b"QWERT" * 409 + b"QWE"),
        ("run then period", b"Z" * 300 + b"ZY" * 300),
    ]
    if CLEAN_SRC.exists():
        blob = CLEAN_SRC.read_bytes()
        # real ROM bytes: an arm9-ish region and a graphics-ish region
        cases.append(("real ROM slice @0x4000", blob[0x4000:0x4000 + 2048]))
        cases.append(("real ROM slice @0x2000000", blob[0x2000000:0x2000000 + 2048]))
    else:
        print(f"  (skipping real-ROM cases: {CLEAN_SRC} not found)")
    return cases


def _assert_same(name: str, new_fn, old_fn) -> None:
    for label, data in _cases():
        want = old_fn(data)
        got = new_fn(data)
        assert got == want, (
            f"{name} / {label}: output changed "
            f"({len(want)} -> {len(got)} bytes, first diff at "
            f"{next((i for i, (a, b) in enumerate(zip(want, got)) if a != b), min(len(want), len(got)))})"
        )
        print(f"  [PASS] {name} {label:<34} {len(data):>5} -> {len(got):>5} bytes")


def test_lz11_hoist_is_byte_identical() -> None:
    _assert_same("lz11", compress_lz11, _compress_lz11_pre_hoist)


def test_lz10_hoist_is_byte_identical() -> None:
    _assert_same("lz10", compress_lz10, _compress_lz10_pre_hoist)


def test_roundtrips_through_the_decompressor() -> None:
    """Equality with the old bytes is the real gate; this catches a shared pre-existing bug."""
    from otn_enhanced.rom.lz_compression import decompress
    for label, data in _cases():
        if not data:
            continue
        for name, fn in (("lz11", compress_lz11), ("lz10", compress_lz10)):
            back = decompress(fn(data))
            assert bytes(back) == data, (
                f"{name} / {label}: round-trip mismatch ({len(back)} vs {len(data)})")
    print("  [PASS] every case round-trips through decompress() for lz10 and lz11")


def main() -> int:
    tests = [test_lz11_hoist_is_byte_identical,
             test_lz10_hoist_is_byte_identical,
             test_roundtrips_through_the_decompressor]
    failed = 0
    for t in tests:
        try:
            print(f"{t.__name__}:")
            t()
            print(f"[PASS] {t.__name__}\n")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}\n")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
