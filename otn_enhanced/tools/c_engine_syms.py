"""C-migration Phase 0 step 7: which engine routines do the stubs call, and which can engine_syms.txt cite?

    uv run python -m otn_enhanced.tools.c_engine_syms   # -> scratch/c_engine_syms.json + summary

A call target is a BL target, or a ``ldr rN,=X ; blx rN`` literal, that lands outside every corpus slot. Each is
matched to KB facts graded VERIFIED/ANCHORED whose ``address`` is exactly that routine (what cc.py demands), and to
a curated name (effect_builder.PRIMITIVES / primitive_names). ``prologue`` says whether the target starts with
``push {.., lr}``: a real function entry, so an anchor fact for it is cheap to add.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from otn_enhanced.asm.thumb_disasm import decode_thumb

KB = Path(__file__).resolve().parents[1] / "docs" / "engine"


def kb_by_address() -> dict[int, list[str]]:
    out, cur, conf = defaultdict(list), None, None
    for p in KB.glob("*.yaml"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if m := re.match(r'- id: "(.+)"', line):
                cur, conf = m.group(1), None
            elif m := re.match(r'  confidence: "(\w+)"', line):
                conf = m.group(1)
            elif cur and conf in ("VERIFIED", "ANCHORED") and (m := re.match(r"  address: (0x[0-9A-Fa-f]+)", line)):
                out[int(m.group(1), 16)].append(cur)
    return out


def call_targets(corpus: list[dict]) -> dict[int, set[str]]:
    spans = [(int(s["addr"], 16), int(s["addr"], 16) + s["size"]) for s in corpus]
    ours = lambda a: any(lo <= a < hi for lo, hi in spans)
    out: dict[int, set[str]] = defaultdict(set)
    for s in corpus:
        if s["empty"]:
            continue
        base, raw = int(s["addr"], 16), bytes.fromhex(s["bytes"])
        pool = {}
        for i in decode_thumb(raw, base):
            reg = i.operands.split(",")[0].strip().upper()
            if i.is_pool_ref:
                o = i.pool_addr - base
                pool[reg] = int.from_bytes(raw[o:o + 4], "little") if 0 <= o <= len(raw) - 4 else None
            elif i.mnemonic == "BL" and not ours(i.branch_target):
                out[i.branch_target].add(s["name"])
            elif i.mnemonic == "BLX" and pool.get(reg) and not ours(pool[reg] & ~1) and pool[reg] & 1:
                out[pool[reg] & ~1].add(s["name"])
            elif not i.mnemonic.startswith(("CMP", "CMN", "TST", "STR", "PUSH", "B")):
                pool.pop(reg, None)
    return out


def main() -> None:
    from otn_enhanced.tools.c_callee_audit import Image
    from otn_enhanced.tools.c_corpus import DEFAULT_ROM
    import sys
    from otn_enhanced.tools.effect_registry import primitive_names as pn
    names = {p.addr: n for n, p in __import__("otn_enhanced.asm.effect_builder", fromlist=["PRIMITIVES"]).PRIMITIVES.items()}
    for attr in dir(pn):
        v = getattr(pn, attr)
        if isinstance(v, dict):
            for k, e in v.items():
                a = getattr(e, "addr", None) if not isinstance(k, int) else k
                n = getattr(e, "name", None) or (k if isinstance(k, str) else None)
                if isinstance(a, int) and n:
                    names.setdefault(a & ~1, n)
    img = Image(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROM)
    corpus = json.load(open("scratch/c_corpus.json"))["slots"]
    kb = kb_by_address()
    rows = []
    for a, users in sorted(call_targets(corpus).items()):
        try:
            prologue = (img.u16(a) & 0xFE00) == 0xB400 and bool(img.u16(a) & 0x100)
        except KeyError:
            prologue = None
        rows.append({"addr": f"0x{a:08X}", "name": names.get(a), "kb": kb.get(a, []), "prologue": prologue,
                     "callers": len(users), "slots": sorted(users)[:6]})
    json.dump(rows, open("scratch/c_engine_syms.json", "w"), indent=1)
    have = sum(bool(r["kb"]) for r in rows)
    named_gap = sum(bool(r["name"]) and not r["kb"] for r in rows)
    pro_gap = sum(r["prologue"] is True and not r["kb"] for r in rows)
    print(f"{len(rows)} engine routines called; {have} already have a VERIFIED/ANCHORED fact at that address; "
          f"{len(rows) - have} need one ({named_gap} of those have a curated name, {pro_gap} start with push{{..lr}})")
    print("-> scratch/c_engine_syms.json")


if __name__ == "__main__":
    main()
