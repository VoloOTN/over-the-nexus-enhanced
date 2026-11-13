"""Add golden rows for functions `stub_port --apply` could not convert, BEFORE you hand-port them.

    uv run python -m otn_enhanced.tools.golden_rows <module> <func> [<func> ...]

For each named function, finds its captured `asm()` call(s) in tests/golden_asm.json.gz, checks that the CURRENT (still
unported) function reproduces the captured bytes, and appends a row to tests/golden_ported.json. A function that does
not reproduce its row post-processes the `asm()` bytes (eva.gy_stub, grapha.arm_stub): it is reported and skipped, and
the full build is its only proof. Functions taking more than the address are not golden-checkable at all
(the test calls f(base)): compare them with tools/compare_orig.py.
"""
from __future__ import annotations

import gzip
import importlib
import json
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1] / "tests"


def main(module: str, funcs: list[str]) -> None:
    dotted = f"otn_enhanced.cards.{module}"
    mod = importlib.import_module(dotted)
    golden = json.load(gzip.open(TESTS / "golden_asm.json.gz", "rt"))
    path = TESTS / "golden_ported.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    have = {(r["func"], r["base"]) for r in rows if r["module"] == dotted}
    for r in golden:
        if r["module"] != dotted or r["func"] not in funcs:
            continue
        ok = getattr(mod, r["func"])(r["base"]).hex() == r["hex"]
        print(module, r["func"], hex(r["base"]), "original reproduces its row:", ok)
        if ok and (r["func"], r["base"]) not in have:
            rows.append({"module": dotted, "func": r["func"], "base": r["base"], "hex": r["hex"]})
    path.write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
