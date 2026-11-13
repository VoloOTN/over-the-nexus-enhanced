"""Run every KB proof and print a PASS / FAIL / UNVERIFIED table.

    uv run python -m otn_enhanced.knowledge.verify_knowledge
    make verify-knowledge          # or verify-knowledge.cmd on Windows

Exit status is non-zero iff a fact graded VERIFIED or ANCHORED FAILs — that is
the loud signal the knowledge base has rotted (an address drifted or a claim was
transcribed wrong).  UNVERIFIED facts (narrative, or savestate/ov5 proofs with
their input absent) never fail the run; they are surfaced so a session knows
exactly what still needs proving.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from otn_enhanced.knowledge.env import load_env
from otn_enhanced.knowledge.loader import Result, load_facts, run_all

_MARK = {"PASS": "PASS ", "FAIL": "FAIL ", "UNVERIFIED": "UNVER"}


def _print_table(results: list[Result], env) -> None:
    width = max((len(r.fact.id) for r in results), default=20)
    by_sub: dict[str, list[Result]] = {}
    for r in results:
        by_sub.setdefault(r.fact.subsystem, []).append(r)

    for sub in sorted(by_sub):
        rows = by_sub[sub]
        print(f"\n=== {sub} ===")
        for r in rows:
            addr = f"0x{r.fact.address:08X}" if r.fact.address else "-".rjust(10)
            note = f"  {r.message}" if r.message and r.status != "PASS" else ""
            print(f"  [{_MARK[r.status]}] {r.fact.id:<{width}}  {r.fact.confidence:<10} {addr}{note}")

    p = sum(r.status == "PASS" for r in results)
    f = sum(r.status == "FAIL" for r in results)
    u = sum(r.status == "UNVERIFIED" for r in results)
    print("\n" + "=" * 60)
    print(f"TOTAL {len(results)} facts:  {p} PASS   {f} FAIL   {u} UNVERIFIED")
    print(f"oracles: arm9=yes ov3=yes  ov5={'yes' if env.ov5 else 'NO (no rom.nds)'}  "
          f"savestate={env.ss_path.name if env.ss_path else 'NO'}")
    if f:
        print("\nFAILURES (VERIFIED/ANCHORED facts whose proof did not hold):")
        for r in results:
            if r.status == "FAIL":
                print(f"  {r.fact.file}:{r.fact.id}  [{r.fact.confidence}]  {r.message}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify the engine knowledge base.")
    ap.add_argument("--savestate", type=Path, help="duel .ml* for RAM proofs "
                    "(default: data/over_the_nexus/working/rom_all_patches.ml1)")
    ap.add_argument("--rom", type=Path, help="rom.nds for ov5 proofs "
                    "(default: data/over_the_nexus/working/rom.nds)")
    ap.add_argument("--subsystem", help="only run one subsystem's facts")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)

    env = load_env(rom_path=args.rom, savestate_path=args.savestate)
    facts = load_facts(subsystem=args.subsystem)
    results = run_all(env, facts)

    # A FAIL only counts against us for a fact that was *claimed* provable.
    hard_fail = any(r.status == "FAIL" and r.fact.confidence in ("VERIFIED", "ANCHORED")
                    for r in results)

    if args.json:
        print(json.dumps([{
            "id": r.fact.id, "subsystem": r.fact.subsystem,
            "confidence": r.fact.confidence, "status": r.status,
            "address": r.fact.address, "message": r.message,
        } for r in results], indent=2))
    else:
        _print_table(results, env)

    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
