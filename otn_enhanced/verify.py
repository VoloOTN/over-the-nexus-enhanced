"""Run every shipped module's `verify()` against a built ROM.

    ... -m otn_enhanced.verify data/over_the_nexus/working/rom_all_patches.nds

`build.py` applies but does not verify, exactly as `apply_all_patches` does not -- this is that
sweep. It exists because a chain can die at step 32 of 41, exit 0, and leave a plausible ROM.

TWO TRAPS, both of which have produced a fake wall of regressions before:

1. **Call `verify()` POSITIONALLY.** The first parameter is `out` in 47 modules and `out_path`
   in 15 (armory_arm, darksoul, gravekeepers_recruiter, elder_six_samurai, escuridao, ninishi,
   safe_zone, sea_lancer, shiens_dojo, tg_rush_rhino, tg_striker, tg_warwolf,
   thunder_sea_horse, w_nebula_meteorite, wattcobra). A keyword call TypeErrors on all 15.

2. **A `None` return is a PASS, not a failure.** Five modules return None on success
   (animation_speed, battle_speed, duel_fastforward, skip_animations, wonder_wand).
   Only an explicit `False` -- or a raised exception -- is a failure.

Import order also matters: several shared hooks register their arms at import time, so every
module is imported BEFORE any is verified.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import time

from otn_enhanced import steps as _steps

DEFAULT_ROM = "data/over_the_nexus/working/rom_all_patches.nds"


def _shipped() -> list[str]:
    """Every step module, once, in build order."""
    return list(dict.fromkeys(s.module for s in _steps.STEPS))


def sweep(rom: str, *, verbose: bool = False, only: str | None = None) -> int:
    mods = {}
    for n in _shipped():                              # import ALL first, even with --only: shared hooks register on import
        try:
            mods[n] = importlib.import_module(f"{_steps._PKG}.{n}")
        except Exception as exc:
            print(f"  [ERROR] {n}: import failed -- {type(exc).__name__}: {exc}")

    # Warm-up: many cards register their arms into SHARED stubs (prefind_hook, c79_trigger_hook, ...)
    # inside verify(), not at import. The build has every arm by the end, so an early card's verify
    # would compare the ROM against a stub missing later cards' arms. One silent pass fills every
    # registry (register() dedupes) so the real pass sees the same registries the build did.
    # ponytail: doubles sweep time; upgrade path is splitting each card's register() out of verify().
    if only is None:
        for n, mod in mods.items():
            fn = getattr(mod, "verify", None)
            if fn is None:
                continue
            with contextlib.redirect_stdout(io.StringIO()), contextlib.suppress(Exception):
                try:
                    fn(rom)
                except TypeError:
                    fn(out=rom)

    passed, failed, skipped = [], [], []
    for n, mod in mods.items():
        if only not in (None, n):
            continue
        fn = getattr(mod, "verify", None)
        if fn is None:
            skipped.append(n)
            continue
        t = time.time()
        sink = io.StringIO()
        ctx = contextlib.nullcontext() if verbose else contextlib.redirect_stdout(sink)
        try:
            with ctx:
                try:
                    result = fn(rom)                  # POSITIONAL -- see trap 1
                except TypeError:                     # system.* verifies are keyword-only: verify(*, out=)
                    result = fn(out=rom)
        except Exception as exc:
            if not verbose:
                print(sink.getvalue())
            print(f"  [FAIL] {n}: {type(exc).__name__}: {exc}")
            failed.append(n)
            continue
        if result is False:                           # None means PASS -- see trap 2
            if not verbose:
                print(sink.getvalue())
            print(f"  [FAIL] {n}")
            failed.append(n)
        else:
            print(f"  [PASS] {n:52.52s} {(time.time() - t) * 1000:6.0f} ms")
            passed.append(n)

    print(f"\n{len(passed)} passed, {len(failed)} failed, {len(skipped)} without verify()")
    if skipped:
        print("  no verify(): " + ", ".join(sorted(skipped)))
    if failed:
        print("  FAILED: " + ", ".join(failed))
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rom", nargs="?", default=DEFAULT_ROM)
    p.add_argument("--only", help="verify just this module")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    print(f"verifying {args.rom}\n")
    return sweep(args.rom, verbose=args.verbose, only=args.only)


if __name__ == "__main__":
    raise SystemExit(main())
