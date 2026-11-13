"""Translate text-assembler blocks into ThumbAssembler programs and compare the bytes.

    uv run python -m otn_enhanced.tools.asm_probe <calls.json[.gz]>

`translate` and `classify` are the seed of the planned stub_port tool: they turn one `asm(base, text)` block
into a builder program and say whether `assemble(base, pad="nop")` reproduces the original bytes.
"""
from __future__ import annotations

import collections
import gzip
import json
import re
import sys

from otn_enhanced.asm.effect_shim import ThumbAssembler

# Thumb-1 ALU mnemonics: the builder's encoder takes the unified (non-"s") spelling.
FLAGGED = {"movs": "MOV", "adds": "ADD", "subs": "SUB", "ands": "AND", "orrs": "ORR", "eors": "EOR",
           "lsls": "LSL", "lsrs": "LSR", "asrs": "ASR", "muls": "MUL", "mvns": "MVN", "negs": "NEG"}
BRANCHES = ("b", "beq", "bne", "bgt", "blt", "bge", "ble", "bmi", "bpl")


class Unsupported(Exception):
    pass


def load_calls(path: str) -> list[dict]:
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def _reg(tok: str) -> int:
    t = tok.strip().lower()
    if re.fullmatch(r"r[0-7]", t):
        return int(t[1])
    raise Unsupported(f"high or odd register {tok!r}")


def _fix_operands(ops: list[str]) -> str:
    s = ", ".join(ops)
    s = re.sub(r"\br([0-7])\b", lambda m: f"R{m.group(1)}", s, flags=re.I)
    s = re.sub(r"\b(sp|lr|pc)\b", lambda m: m.group(1).upper(), s, flags=re.I)
    s = re.sub(r"#(-?\d+)\b(?!x)", lambda m: f"#0x{int(m.group(1)):X}", s)
    s = re.sub(r"#0[xX]([0-9a-fA-F]+)", lambda m: f"#0x{int(m.group(1), 16):X}", s)
    s = re.sub(r"\[\s*(\w+)\s*,\s*", r"[\1, ", s)
    s = re.sub(r"\[\s*(\w+)\s*\]", r"[\1, #0x0]", s)      # the encoder rejects the [Rn] shorthand
    return s


def translate(text: str, symbols: dict | None = None) -> ThumbAssembler:
    """One text-assembler block as a ThumbAssembler program (not yet assembled)."""
    a = ThumbAssembler()
    for raw in text.splitlines():
        line = raw.split(";")[0].split("//")[0].strip()
        while line:
            m = re.match(r"^([A-Za-z_]\w*):\s*", line)
            if not m:
                break
            a.label(m.group(1))
            line = line[m.end():].strip()
        if not line:
            continue
        mnem, _, rest = line.partition(" ")
        mnem = mnem.lower()
        ops = ([rest.strip()] if (mnem in ("push", "pop") or rest.strip().startswith("{"))
               else ([o.strip() for o in rest.split(",")] if rest.strip() else []))
        if mnem == "ldr" and len(ops) >= 2 and ops[1].startswith("="):
            a.ldr_const(_reg(ops[0]), int(ops[1][1:], 0))
        elif mnem == "bl" and len(ops) == 1:
            t = ops[0]
            if re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+", t):
                a.bl(int(t, 0))
            elif symbols and t in symbols:
                a.bl(symbols[t])
            else:
                a.bl_label(t)
        elif mnem in BRANCHES and len(ops) == 1:
            t = ops[0]
            if symbols and t in symbols:
                t = f"0x{symbols[t]:08X}"
            a.insn(mnem.upper(), t)
        elif mnem == "blx":
            a.insn("BLX", ops[0].upper())
        else:
            a.insn(FLAGGED.get(mnem, mnem.upper()), _fix_operands(ops))
    return a


def classify(rec: dict) -> tuple[str, str]:
    """('identical' | 'error' | 'unsupported' | 'length' | 'differs', detail) for one captured block."""
    base, gold = rec["base"], bytes.fromhex(rec["hex"])
    try:
        mine = translate(rec["source"], rec.get("symbols")).assemble(base, pad="nop")
    except Unsupported as e:
        return "unsupported", str(e)
    except Exception as e:                      # encoder or layout error
        return "error", f"{type(e).__name__}: {str(e)[:70]}"
    if mine == gold:
        return "identical", ""
    if len(mine) != len(gold):
        return "length", f"{len(mine)} vs {len(gold)} bytes"
    diff = [i for i in range(0, len(gold), 2) if mine[i:i + 2] != gold[i:i + 2]]
    return "differs", (f"{len(diff)} halfword(s), first at +0x{diff[0]:X}: "
                       f"want {gold[diff[0]:diff[0] + 2].hex()} got {mine[diff[0]:diff[0] + 2].hex()}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    calls = load_calls(argv[0])
    tally: collections.Counter = collections.Counter()
    why: dict = collections.defaultdict(collections.Counter)
    example: dict = {}
    for r in calls:
        c, m = classify(r)
        tally[c] += 1
        why[c][m] += 1
        example.setdefault((c, m), r)
    n = len(calls)
    print(f"{n} blocks\n")
    for c, k in tally.most_common():
        print(f"  {c:12s} {k:4d}  ({100 * k / n:4.1f}%)")
    for c in ("unsupported", "error", "length", "differs"):
        if why[c]:
            print(f"\n-- {c}:")
            for m, k in why[c].most_common(8):
                r = example[(c, m)]
                print(f"   {k:3d}x {m}   e.g. {r['module'].split('.')[-1]}.{r['func']} base=0x{r['base']:08X}")
    return 0 if tally["identical"] == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
