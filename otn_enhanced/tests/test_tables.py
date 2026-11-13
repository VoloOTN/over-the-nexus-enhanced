"""Prove `tables.insert_sorted` produces the SAME BYTES as both shipped implementations.

    uv run python -m otn_enhanced.tests.test_tables

`finished_patches/` has two different count-neutral-insert algorithms with incompatible
signatures (see tables.py). Nine modules depend on one or the other having produced exactly
the bytes that are in the shipped ROM. Replacing them is only safe if the replacement is
byte-identical to BOTH -- so this runs all three against the real criteria registry from the
working ROM and diffs the resulting table region.

The insert positions are chosen to hit every branch that differs between the two algorithms:
before the phantom, after it, adjacent to it, and at both ends of the table (the last of which
makes variant B's `next(...)` raise StopIteration -- a real latent bug this replacement fixes).
"""
from __future__ import annotations

import struct

from otn_enhanced.effects.common import Ov
from otn_enhanced.effects.common import Table, insert_sorted, keys
from otn_enhanced.cards import grapha, tg_striker
from otn_enhanced.effects.common import insert_row_by_stride
from otn_enhanced.rom.overlay_io import load_overlay3

ROM = "data/over_the_nexus/working/rom.nds"

# the criteria registry -- geometry per jet_synchron.py:220-224
CRIT = Table(base=0x022713C4, count=0x56C, stride=12, fmt="<HHII", label="criteria")


def _region(buf: bytearray, t: Table) -> bytes:
    o = t.base - 0x02141700
    return bytes(buf[o:o + t.count * t.stride])


def _variant_a(buf: bytearray, t: Table, record: tuple, drop: int) -> bytes:
    b = bytearray(buf)
    grapha._insert_sorted(b, t.base, t.count, t.stride, t.fmt, record, drop, "A", False)
    return _region(b, t)


def _variant_b(buf: bytearray, t: Table, record: tuple, drop: int) -> bytes:
    b = bytearray(buf)
    # NOTE the argument order: stride and count are SWAPPED relative to variant A.
    insert_row_by_stride(b, t.base, t.stride, t.count, t.fmt, record, drop, "B")
    return _region(b, t)


def _mine(buf: bytearray, t: Table, record: tuple, drop: int) -> bytes:
    view = Ov(bytearray(buf))
    insert_sorted(view, t, record, drop=drop, quiet=True)
    return _region(view.buf, t)


def test_three_implementations_agree() -> None:
    _, raw = load_overlay3(ROM)
    buf = bytearray(raw)
    view = Ov(buf)
    ks = keys(view, CRIT)

    # a phantom to spend: a cid present exactly once, comfortably inside the table
    counts = {k: ks.count(k) for k in set(ks)}
    drop = next(k for k in ks[len(ks) // 2:] if counts[k] == 1)
    di = ks.index(drop)
    print(f"  phantom 0x{drop:04X} @ index {di} of {len(ks)}")

    # insert positions that exercise every differing branch
    targets = {
        "far before phantom": ks[di // 2] - 1,
        "just before phantom": drop - 1,
        "just after phantom": drop + 1,
        "far after phantom": ks[(di + len(ks)) // 2] + 1,
        "smallest in table": max(ks[0] - 1, 1),
        "largest in table": ks[-1] + 1,
    }

    agreed = 0
    for name, cid in targets.items():
        if cid in ks or cid <= 0 or cid > 0xFFFF:
            print(f"  [skip] {name}: 0x{cid:04X} unusable")
            continue
        record = (cid, 0x0001, 0x0223CA11, 0x0A550002)

        mine = _mine(buf, CRIT, record, drop)
        a = _variant_a(buf, CRIT, record, drop)
        try:
            b = _variant_b(buf, CRIT, record, drop)
        except StopIteration:
            # variant B's `next(r[0] > cid)` has no fallback for a new largest key
            assert name == "largest in table", f"unexpected StopIteration on {name}"
            print(f"  [PASS] {name}: variant B raises StopIteration (latent bug); mine and A agree")
            assert mine == a, f"{name}: mine != variant A"
            agreed += 1
            continue

        assert mine == a, f"{name}: mine != variant A (0x{cid:04X})"
        assert mine == b, f"{name}: mine != variant B (0x{cid:04X})"
        assert a == b, f"{name}: the two SHIPPED variants disagree with each other (0x{cid:04X})"
        print(f"  [PASS] {name}: 0x{cid:04X} -- all three identical")
        agreed += 1

    assert agreed >= 5, f"only {agreed} positions actually compared"


def test_count_and_sort_are_preserved() -> None:
    _, raw = load_overlay3(ROM)
    view = Ov(bytearray(raw))
    ks = keys(view, CRIT)
    counts = {k: ks.count(k) for k in set(ks)}
    drop = next(k for k in ks[len(ks) // 2:] if counts[k] == 1)
    cid = next(c for c in range(0x2500, 0x2600) if c not in ks)

    before = len(ks)
    pos = insert_sorted(view, CRIT, (cid, 0, 0x0223CA11, 0), drop=drop, quiet=True)
    after = keys(view, CRIT)

    assert len(after) == before, "count changed -- the engine's row-count literal would be wrong"
    assert after == sorted(after), "table lost its sort order -- binary search would break"
    assert after[pos] == cid
    assert drop not in after, "phantom was not actually dropped"

    # idempotent: a second insert is a no-op
    again = insert_sorted(view, CRIT, (cid, 0, 0x0223CA11, 0), drop=drop, quiet=True)
    assert again == pos and keys(view, CRIT) == after, "second insert was not a no-op"


def test_spent_phantom_is_a_loud_failure() -> None:
    """A phantom another patch already spent must raise, not silently corrupt the table."""
    _, raw = load_overlay3(ROM)
    view = Ov(bytearray(raw))
    absent = next(c for c in range(0x2500, 0x2600) if c not in keys(view, CRIT))
    try:
        insert_sorted(view, CRIT, (0x2599, 0, 0, 0), drop=absent, quiet=True)
    except AssertionError as exc:
        assert "not present to drop" in str(exc)
    else:
        raise AssertionError("insert_sorted accepted a phantom that is not in the table")


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"{t.__name__}:")
        t()
        print(f"[PASS] {t.__name__}\n")
    print(f"{len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
