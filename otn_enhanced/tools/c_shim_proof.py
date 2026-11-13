"""C-migration Phase 0 step 5: prove asm/c/shim.S on real shipped hooks.

    uv run python -m otn_enhanced.tools.c_shim_proof

Each proof builds asm/c/proofs/<name>.S + .c at the hook's slot and runs c_equiv against the slot's ROM bytes
(scratch/c_corpus.json), comparing all of r0-r7 on return and allowing the declared frame access.
"""
from __future__ import annotations

import json
from pathlib import Path

from otn_enhanced.asm.cc import C_DIR, compile_c
from otn_enhanced.tools.c_equiv import EquivError, equiv

PROOFS = C_DIR / "proofs"
ENGINE_REGS = (0x02300000, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77)   # distinct live r0-r7 at the site
CASES = [  # (slot, proof name, shim, frame access allowed)
    ("CAVE3_SL_ATKRESET", "sl_atkreset", "SPLICE + frame write [sp+0xB0]", True),
    ("CAVE3_SK_NSMATCH", "sk_nsmatch", "FRONT (return with r1=K / tail-jump)", False),
]


def main() -> None:
    corpus = {s["name"]: s for s in json.load(open("scratch/c_corpus.json"))["slots"]}
    for slot, name, shim, frame_ok in CASES:
        s = corpus[slot]
        base, old = int(s["addr"], 16), bytes.fromhex(s["bytes"])
        new = compile_c([PROOFS / f"{name}.S", PROOFS / f"{name}.c"], base)
        for r0 in (ENGINE_REGS[0], 0x3E50):          # 0x3E50 = Sakitama's K: takes the front's match exit
            rep = equiv(old, new, base, args=(r0, *ENGINE_REGS[1:]), frame_ok=frame_ok, all_regs=True)
        bad = old.replace(bytes.fromhex("0024"), bytes.fromhex("0124"), 1) if b"\x00\x24" in old \
            else old.replace((0x3E50).to_bytes(4, "little"), (0x3E51).to_bytes(4, "little"))   # r4=1 / K+1
        try:
            for r0 in (ENGINE_REGS[0], 0x3E50):
                equiv(bad, new, base, args=(r0, *ENGINE_REGS[1:]), frame_ok=frame_ok, all_regs=True)
            raise AssertionError(f"{slot}: a mutated old stub still matched: the proof is blind")
        except EquivError:
            pass
        fits = "fits" if len(new) <= s["size"] else "does NOT fit"
        print(f"{slot}: {shim}: equal over {rep['paths']} paths; C+shim {len(new)} B vs slot {s['size']} B ({fits})")


if __name__ == "__main__":
    main()
