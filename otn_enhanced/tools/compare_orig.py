"""Compare every builder function of a card module against a pre-edit copy of it.

    cp otn_enhanced/cards/<m>.py <dir>/orig_<m>.py                       # BEFORE you touch the module
    uv run python -m otn_enhanced.tools.compare_orig <dir> <m>

Calls each `*_stub` / `build_*` function of the copy and of the live module at several addresses and with each extra
argument (`prev`, `lit`, `chain`) varied, and asserts identical bytes. This covers what the golden file cannot: functions
that take more than the address. A module whose `_check` keys a RESERVE table by slot address raises at a foreign base
(ojamassimilation): then rely on the golden rows. A build-time flag (DIAG_*) is flipped by editing the module attribute on
both modules in your own loop; see notes/otn-enhanced-effectbuilder-port-findings.md (lightpulsar).
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import itertools
import sys

OPTS = {"prev": (0x021B0000, 0x023A1000, 0x0221B4A2), "lit": (0x023A1001, 0x02200001), "chain": (True, False)}


def main(orig_dir: str, name: str) -> None:
    spec = importlib.util.spec_from_file_location(f"orig_{name}", f"{orig_dir}/orig_{name}.py")
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    new = importlib.import_module(f"otn_enhanced.cards.{name}")
    n = 0
    for fn, f in inspect.getmembers(old, inspect.isfunction):
        if f.__module__ != old.__name__ or not (fn.endswith("_stub") or fn.startswith("build_")):
            continue
        params = list(inspect.signature(f).parameters)[1:]
        combos = itertools.product(*[OPTS[p] for p in params]) if params else [()]
        for base in (0x023A5000, 0x02212330, 0x021F0F9C, 0x0239D400):
            for c in combos:
                assert f(base, *c) == getattr(new, fn)(base, *c), (name, fn, hex(base), c)
                n += 1
    print("identical", n, "calls")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
