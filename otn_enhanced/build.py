"""Build the Vanilla+ or Enhanced ROM by applying steps.STEPS to one in-memory ROM.

    python -m otn_enhanced.build                      # Enhanced, about 6 minutes
    python -m otn_enhanced.build --vanilla-plus       # stops at steps.VANILLA_PLUS_END, about 90 s
    python -m otn_enhanced.build --compare data/over_the_nexus/working/rom_known_good.nds
    python -m otn_enhanced.build --only cards.jet_synchron -v
    python -m otn_enhanced.build --upto 20

The speed comes from session.py (one compression per overlay instead of one per step).
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from otn_enhanced import steps as _steps
from otn_enhanced.session import Session, assert_no_table_readers
from otn_enhanced.text_guard import TextGuard

PATCH_BASE = "data/over_the_nexus/backup/unpatched/{lang}.nds"   # --patch sources: clean dumps, not the apfix ROMs
PATCH_TOOLS = {"xdelta": "xdelta3", "bps": "flips"}               # on PATH or in the repo root
CLEAN_SRC = "data/over_the_nexus/backup/eu_apfix.nds"
DEFAULT_OUT = "data/over_the_nexus/working/rom_all_patches.nds"
VANILLA_PLUS_OUT = "data/over_the_nexus/working/rom_vanilla_plus.nds"
# The FROZEN reference `--compare` is meant to run against: a snapshot of the oracle chain's
# output, refreshed only by a deliberate re-baseline (see notes/CURRENT-BASELINE.md). It is a
# separate file from DEFAULT_OUT on purpose -- this build overwrites DEFAULT_OUT every run.
BASELINE = "data/over_the_nexus/working/rom_baseline.nds"
WORK_PATH = "data/over_the_nexus/working/__ee_session__.nds"   # virtual: never written to disk


def _guard_allocations() -> None:
    """Abort before writing any ROM if two patches collide on a slot, phantom cid or row."""
    from otn_enhanced.knowledge import check_allocations
    if check_allocations.main([]) != 0:
        raise SystemExit("BUILD ABORTED: patch-slot allocation collision (see above).")


def _guard_decks() -> None:
    """Dry-run the deck step on the clean ROM so a bad YDC fails now, not at step 100+."""
    import ndspy.rom
    try:
        from otn_enhanced.data import bulk_ydcs   # importing ydc_decks also validates every YDC
        bulk_ydcs.new_deck_pac(ndspy.rom.NintendoDSRom.fromFile(CLEAN_SRC))
    except Exception as e:
        raise SystemExit(f"BUILD ABORTED: deck preflight failed: {type(e).__name__}: {e}")


def _select(args) -> list[tuple[int, _steps.Step]]:
    rows = list(enumerate(_steps.STEPS, start=1))
    if args.only:
        rows = [(i, s) for i, s in rows if args.only in (s.module, s.name)]
        if not rows:
            raise SystemExit(f"--only {args.only!r} matched no step")
    if args.start:
        rows = [(i, s) for i, s in rows if i >= args.start]
    if args.upto:
        rows = [(i, s) for i, s in rows if i <= args.upto]
    if args.vanilla_plus:
        rows = [(i, s) for i, s in rows if i <= _steps.VANILLA_PLUS_END]
    if args.c:      # converted stub forms (otn_enhanced/c_forms.py), gated and applied after everything else
        rows.append((len(_steps.STEPS) + 1, _steps.Step("C forms (build --c)", "c_forms", None, "apply", True)))
    return rows


def build(out: str, *, write_text: bool = True, verbose: bool = False, strict: bool = False,
          rows: list[tuple[int, _steps.Step]] | None = None, check_text: bool = True) -> str:
    """Apply the selected steps to one in-memory ROM and write it. Returns the sha256."""
    rows = rows if rows is not None else list(enumerate(_steps.STEPS, start=1))
    total = len(_steps.STEPS)
    guard = TextGuard() if check_text else None
    t0 = time.time()

    with Session(CLEAN_SRC, WORK_PATH, defer=not strict) as sess:
        for i, step in rows:
            t = time.time()
            sess.normalise()        # give each step the buffer types a fresh fromFile would
            sink = io.StringIO()
            ctx = contextlib.nullcontext() if verbose else contextlib.redirect_stdout(sink)
            try:
                with ctx:
                    _steps.call(step, WORK_PATH, WORK_PATH, write_text=write_text)
            except Exception:
                if not verbose:                 # the swallowed output is the diagnosis
                    sys.stdout.write(sink.getvalue())
                print(f"\n*** STEP {i}/{total} FAILED: {step.name} ({step.module}) ***")
                raise
            print(f"[{i:2d}/{total}] {step.name:62.62s} {(time.time() - t) * 1000:6.0f} ms")
            if guard is not None:
                err = guard.check(sess.rom, i, step.name)
                if err:
                    raise SystemExit("\n" + err)

        n = sess.finalize(out)

    data = Path(out).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    print(f"\n{len(rows)}/{total} steps in {time.time() - t0:.1f} s -> {out}")
    print(f"  bytes  {n}")
    print(f"  sha256 {sha}")
    return sha


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=None, help=f"default {DEFAULT_OUT} ({VANILLA_PLUS_OUT} with --vanilla-plus)")
    p.add_argument("--vanilla-plus", action="store_true",
                   help="stop at the divergence point (steps.VANILLA_PLUS_END): the vanilla+ ROM")
    p.add_argument("--no-text", action="store_true", help="skip name/description writes")
    p.add_argument("--only", metavar="MODULE", help="run just this step (module name)")
    p.add_argument("--start", type=int, metavar="N", help="start at step N")
    p.add_argument("--upto", type=int, metavar="N", help="stop after step N")
    p.add_argument("-v", "--verbose", action="store_true", help="show each module's own output")
    p.add_argument("--strict", action="store_true",
                   help="compress at every step (old behaviour) -- isolates a deferral bug from a caching bug")
    p.add_argument("--no-check-text", action="store_true", help="skip the card-text clobber guard")
    p.add_argument("--compare", metavar="BASELINE", help="sha256 the result against BASELINE and exit nonzero on a mismatch")
    p.add_argument("--c", action="store_true",
                   help="also apply the converted C / .S stub forms (c_forms.FORMS); default out rom_all_patches_c.nds")
    p.add_argument("--patch", choices=sorted(PATCH_TOOLS), action="append", metavar="{bps,xdelta}",
                   help="also emit time-stamped patches against the unpatched EU and US ROMs (repeatable)")
    args = p.parse_args(argv)
    from otn_enhanced.c_forms import C_OUT
    args.out = args.out or (C_OUT if args.c else VANILLA_PLUS_OUT if args.vanilla_plus else DEFAULT_OUT)

    # --out defaults to the canonical rom_all_patches.nds, so `--compare` against that same
    # path would hash the file this build just wrote and report IDENTICAL unconditionally.
    # Checked BEFORE the 200 s build, not after.
    if args.compare and Path(args.compare).resolve() == Path(args.out).resolve():
        raise SystemExit(
            f"--compare and --out are the same file ({args.out}).\n"
            f"That compares the build against itself and ALWAYS passes.\n"
            f"Compare against the frozen baseline instead, e.g.\n"
            f"  --compare {BASELINE}")

    tools = {}
    for fmt in args.patch or ():   # fail now, not after the 166 s build
        tools[fmt] = shutil.which(PATCH_TOOLS[fmt]) or shutil.which(PATCH_TOOLS[fmt], path=".")
        if not tools[fmt]:
            raise SystemExit(f"--patch {fmt} needs {PATCH_TOOLS[fmt]}.exe on PATH or in the repo root")

    _guard_allocations()
    _guard_decks()
    rot = assert_no_table_readers()
    if rot:
        raise SystemExit("BUILD ABORTED: a patch module now branches on overlay-table state,\n"
                         "which the deferred-compression build assumes never happens:\n  "
                         + "\n  ".join(rot))

    sha = build(args.out, write_text=not args.no_text, verbose=args.verbose, strict=args.strict,
                rows=_select(args), check_text=not args.no_check_text)

    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    for fmt, tool in tools.items():
        for lang in ("eu",):
            src = PATCH_BASE.format(lang=lang)
            out = f"{os.path.dirname(args.out)}/over_the_nexus_{lang}_{stamp}.{fmt}"
            cmd = ([tool, "-e", "-f", "-s", src, args.out, out] if fmt == "xdelta"
                   else [tool, "--create", "--bps", src, args.out, out])
            subprocess.run(cmd, check=True)
            print(f"  {fmt:6s} {out}")

    if args.compare:
        want = hashlib.sha256(Path(args.compare).read_bytes()).hexdigest()
        if want == sha:
            print(f"\nIDENTICAL {sha}")
            return 0
        print(f"\n*** MISMATCH ***\n  built    {sha}\n  baseline {want}\n"
              f"  bisect with --upto N, or re-run with --strict to tell a deferral bug\n"
              f"  from a caching bug.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
