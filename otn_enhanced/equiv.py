"""Prove a rewritten card produces the same bytes as a reference version.

    python -m otn_enhanced.equiv cards.darksoul                 # vs the old-tree original
    python -m otn_enhanced.equiv cards.darksoul --ref some.module
    python -m otn_enhanced.equiv cards.darksoul --self          # runs the module twice

Both versions run against the same in-memory ROM state and the results are diffed byte for byte:

    steps 1..N-1  ->  snapshot S
    S -> reference.main()  -> A
    S -> otn_enhanced.<module>.main()  -> B
    assert A == B

Run a full `build --compare` afterwards: a per-module diff cannot see two cards fighting over one
shared row. `--self` checks the harness and that a module is deterministic.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import shutil
import sys
import time

from otn_enhanced import steps as _steps
from otn_enhanced.session import Session

CLEAN_SRC = "data/over_the_nexus/backup/eu_apfix.nds"
WORK_PATH = "data/over_the_nexus/working/__ee_equiv__.nds"

# Originals whose ROM I/O goes through a DIFFERENT path than the one they are given
# (ydc_decks: shutil.copy -> out+".bak", extract_file/replace_file on it, then a
# same-path copy back that Session swallows). Inside a Session they silently change nothing,
# so the A side is run for real on disk instead -- see _run_on_disk.
REAL_IO = {"data.bulk_ydcs"}


OLD_TREE = "ygo_tools.tools.finished_patches"


def _default_ref(module: str) -> str:
    # elbow: the reference is the pre-refactor tree. Once that is deleted, pass --ref to a
    # frozen copy of the card instead.
    # elbow: cards moved to the ov3 pool (main(ov3=True)) never match an ov5-only original (arm9
    # arena-lo, ov5 growth and the stub addresses all differ). The old harness had the same limit.
    # Compare such a card against a copy built with the same ov3 default, or use `build --compare`.
    base = module.rsplit(".", 1)[-1]
    return f"{OLD_TREE}.patch_{'next' if base == 'next_card' else base}"


def _capture(sess: Session) -> dict:
    return {
        "arm9": bytes(sess.rom.arm9),
        "table": bytes(sess.rom.arm9OverlayTable),
        "files": [bytes(f) for f in sess.rom.files],
        "ov": {i: (bytes(o.data), o.ramSize, o.flags, o.compressedSize)
               for i, o in sess.overlays.items()},
        "dirty": set(sess.dirty),
    }


def _restore(sess: Session, snap: dict) -> None:
    sess.rom.arm9 = bytearray(snap["arm9"])
    sess.rom.arm9OverlayTable = bytearray(snap["table"])
    sess.rom.files = [bytearray(f) for f in snap["files"]]
    # An overlay the step loaded for the FIRST time is not in the snapshot, so there is nothing
    # to restore it from -- drop it and let Session._load_overlays rebuild it from the (already
    # restored) rom.files. Without this the second run inherits the first run's edits: step 1
    # has an empty prefix, so its snapshot holds no overlays at all and `install_cave` fails
    # with "ov5 cave is not free" on the replacement run.
    for i in [i for i in sess.overlays if i not in snap["ov"]]:
        del sess.overlays[i]
    for i, (data, ram, flags, csz) in snap["ov"].items():
        ov = sess.overlays[i]
        ov.data, ov.ramSize, ov.flags, ov.compressedSize = bytearray(data), ram, flags, csz
    sess.dirty = set(snap["dirty"])


def _first_diff(a: bytes, b: bytes) -> int:
    lo, n = 0, min(len(a), len(b))
    while lo < n and a[lo] == b[lo]:
        lo += 1
    return lo


def _diff(a: dict, b: dict, ov_bases: dict[int, int]) -> list[str]:
    """Human-readable differences between two captures. Empty list == identical."""
    out: list[str] = []

    for key in ("arm9", "table"):
        if a[key] != b[key]:
            off = _first_diff(a[key], b[key])
            out.append(f"{key}: differs at +0x{off:X} "
                       f"(len {len(a[key])} vs {len(b[key])}): "
                       f"{a[key][off:off+8].hex()} != {b[key][off:off+8].hex()}")

    for i in sorted(set(a["ov"]) | set(b["ov"])):
        da, db = a["ov"].get(i, (b"",))[0], b["ov"].get(i, (b"",))[0]
        if da != db:
            off = _first_diff(da, db)
            ram = ov_bases.get(i, 0) + off
            out.append(f"overlay {i}: differs at +0x{off:X} (RAM 0x{ram:08X}) "
                       f"(len 0x{len(da):X} vs 0x{len(db):X}): "
                       f"{da[off:off+8].hex()} != {db[off:off+8].hex()}")

    if len(a["files"]) != len(b["files"]):
        out.append(f"file count: {len(a['files'])} vs {len(b['files'])}")
    else:
        for i, (fa, fb) in enumerate(zip(a["files"], b["files"])):
            if fa != fb:
                off = _first_diff(fa, fb)
                out.append(f"file {i}: differs at +0x{off:X} (len {len(fa)} vs {len(fb)})")
    return out


def check(module: str, *, ref: str | None = None, self_test: bool = False, verbose: bool = False) -> bool:
    """Run *module*'s original and replacement against identical state; report any difference."""
    idx = next((i for i, s in enumerate(_steps.STEPS) if s.module == module), None)
    if idx is None:
        raise SystemExit(f"{module!r} is not a step in steps.STEPS")
    step = _steps.STEPS[idx]

    alt = f"{_steps._PKG}.{module}"
    orig = alt if self_test else (ref or _default_ref(module))

    quiet = contextlib.nullcontext() if verbose else contextlib.redirect_stdout(io.StringIO())

    with Session(CLEAN_SRC, WORK_PATH) as sess, quiet:
        t0 = time.time()
        for i, prior in list(enumerate(_steps.STEPS, 1))[:idx]:
            sess.normalise()
            _steps.call(prior, WORK_PATH, WORK_PATH, write_text=True)
        base = _capture(sess)
        ov_bases = {i: o.ramAddress for i, o in sess.overlays.items()}
        prefix_s = time.time() - t0

        def run(path: str) -> dict:
            _restore(sess, base)
            sess.normalise()
            fn = getattr(importlib.import_module(path), step.entry)
            if step.positional:
                fn(WORK_PATH, WORK_PATH)
            elif step.text is None:
                fn(src=WORK_PATH, out=WORK_PATH)
            else:
                fn(write_text=True, src=WORK_PATH, out=WORK_PATH)
            return _capture(sess)

        def run_on_disk(path: str) -> dict:
            """Serialise the prefix state, run *path* on real files, fold its file edits back in."""
            import ndspy.rom
            from pathlib import Path

            _restore(sess, base)
            sess.normalise()
            tmp_in, tmp_out = WORK_PATH + ".in.nds", WORK_PATH + ".out.nds"   # not the work path
            try:
                sess.finalize(tmp_in)
                shutil.copyfile(tmp_in, tmp_out)          # the original os.remove()s its out first
                fn = getattr(importlib.import_module(path), step.entry)
                if step.text is None:
                    fn(src=tmp_in, out=tmp_out)
                else:
                    fn(write_text=True, src=tmp_in, out=tmp_out)
                r_in, r_out = ndspy.rom.NintendoDSRom.fromFile(tmp_in), ndspy.rom.NintendoDSRom.fromFile(tmp_out)
                assert (r_in.arm9, r_in.arm9OverlayTable, len(r_in.files)) == \
                       (r_out.arm9, r_out.arm9OverlayTable, len(r_out.files)), \
                    f"{path} touched arm9/overlays; REAL_IO only folds back plain files"
                changed = {i: bytes(f) for i, f in enumerate(r_out.files) if f != r_in.files[i]}
            finally:
                for p in (tmp_in, tmp_out):
                    Path(p).unlink(missing_ok=True)
            _restore(sess, base)
            snap = _capture(sess)
            for i, f in changed.items():
                snap["files"][i] = f
            return snap

        a = run_on_disk(orig) if module in REAL_IO and not self_test else run(orig)
        b = run(alt)

    diffs = _diff(a, b, ov_bases)
    label = f"{module} ({'self' if self_test else alt})"
    if not diffs:
        print(f"[IDENTICAL] {label}  (prefix {idx} steps, {prefix_s:.1f} s)")
        return True
    print(f"[DIFFERS] {label}")
    for line in diffs[: (None if verbose else 12)]:
        print(f"    {line}")
    if not verbose and len(diffs) > 12:
        print(f"    ... {len(diffs) - 12} more (use -v)")
    return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("module", nargs="?", help="step module, e.g. cards.darksoul")
    p.add_argument("--ref", help="reference module to compare against (default: the old-tree original)")
    p.add_argument("--self", dest="self_test", action="store_true",
                   help="run the ORIGINAL twice -- checks the harness and the module's determinism")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    if not args.module:
        p.error("give a module, e.g. cards.mystic_piper")
    ok = check(args.module, ref=args.ref, self_test=args.self_test, verbose=args.verbose)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
