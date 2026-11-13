"""C-migration Phase 0 step 6: propose a target form for every corpus stub, with the reason.

    uv run python -m otn_enhanced.tools.c_classify [ROM]   # -> scratch/c_classify.json + summary

Forms: C (plain function), C+front (FRONT_SHIM), C+splice (SPLICE_SHIM: live registers and/or engine frame),
.S (tiny thunk, or a front a verifier pattern-matches), REVIEW (the walker gave up: a human look).
C-direct is a front whose every native target passed the callee audit, so C can just ``return native(...)``.
Facts come from c_callee_audit's walker run inside the slot. ``tight`` marks a slot too small for the shim
plus a minimal hook: expect a byte-identical .S fallback there (Phase 4), but measure.
"""
from __future__ import annotations

import json
import sys
from collections import Counter

from otn_enhanced.tools.c_callee_audit import Image, audit
from otn_enhanced.tools.c_corpus import DEFAULT_ROM

SHIM_COST = {"C+splice": 10, "C+front": 28}   # shim.S bytes, before the C hook
MIN_HOOK = 8                                   # a 2-instruction C hook + its return


def _verifier_front(raw: bytes) -> bool:
    """The exact list-search pre-check effect_verify.addr_reaches follows: keep it byte-identical."""
    if len(raw) < 14:
        return False
    hw = [int.from_bytes(raw[i:i + 2], "little") for i in range(0, 14, 2)]
    return hw[0] >> 8 == 0x4B and hw[1] == 0x4298 and hw[2] >> 8 == 0xD1 and hw[3] == 0x2001 and hw[4] == 0x4770


_NO_FLAGS = ("LDR", "STR", "PUSH", "POP", "B", "BL", "BX", "BLX", "NOP", "LDMIA", "STMIA")


def _flag_contract(raw: bytes, base: int) -> str:
    """A condition-flag contract C can't express: a conditional branch on the CALLER's flags (before anything
    here sets them), or a compare right before a return (the result is the flags)."""
    from otn_enhanced.asm.thumb_disasm import decode_thumb
    ins = decode_thumb(raw, base)
    for i in ins:
        if i.mnemonic.startswith("B") and i.mnemonic not in ("B", "BL", "BX", "BLX", "BIC"):
            return f"branches on the caller's flags at 0x{i.addr:08X}"
        hi = any(r in i.operands.upper() for r in ("SP", "PC", "R8", "R9", "R10", "R11", "R12", "LR"))
        if not (i.mnemonic.startswith(_NO_FLAGS) or (i.mnemonic in ("MOV", "ADD") and hi)):
            break
    for k, b in enumerate(ins):
        if not b.is_return:
            continue
        j = k - 1
        while j >= 0 and ins[j].mnemonic == "POP" and "PC" not in ins[j].operands.upper():
            j -= 1
        if j < 0:
            continue
        a = ins[j]
        if a.mnemonic in ("CMP", "CMN", "TST"):
            return f"returns its result in the flags (compare at 0x{a.addr:08X} then return)"
        dst = a.operands.split(",")[0].strip().upper()
        if dst in ("R1", "R2", "R3") and not a.mnemonic.startswith(("STR", "CMP", "B", "PUSH")):
            return f"returns a value in {dst} (written at 0x{a.addr:08X} right before the return)"
    return ""


def classify(img, s: dict, audit_rows: dict[int, str]) -> tuple[str, str, bool]:
    base, raw = int(s["addr"], 16), bytes.fromhex(s["bytes"])
    used = len(raw.rstrip(b"\0"))
    if used <= 6:
        return ".S", f"tiny ({used} B used): C gains nothing", False
    if _verifier_front(raw):
        return ".S", "verifier pattern-matches this list-search front (effect_verify.addr_reaches)", False
    flags = _flag_contract(raw, base)
    if flags:
        return ".S", flags, False
    f: dict = {}
    verdict, why = audit(img, base | 1, bounds=(base, base + s["size"]), facts=f)
    if verdict == "UNKNOWN":
        return "REVIEW", why, False
    if f.get("sp_unbalanced"):
        return ".S", f"sp unbalanced at an exit ({f['sp_unbalanced']}): works in its caller's frame", False
    live = [k for k in ("hidden_read", "clobber", "frame") if f.get(k)]
    if live:
        form = "C+splice" if live != ["frame"] or "ret" in f["exits"] else "C+front"
        reason = "; ".join(f"{k} {sorted(f[k]) if k == 'clobber' else f[k]}" for k in live)
    elif "jump" in f["exits"]:
        tv = [audit_rows.get(t | 1, "UNKNOWN") for t in f["targets"]]
        if f["targets"] and all(v == "PASS" for v in tv) and "ret" not in f["exits"]:
            return "C", f"tail-jump to audited callee(s) {[hex(t) for t in f['targets']]}: return native(...)", False
        form, reason = "C+front", f"exits {sorted(f['exits'])}, targets {[hex(t) for t in f['targets']] or 'indirect'}"
    else:
        return "C", "plain function: returns, no live registers, no frame access", False
    if "jump" in f["exits"] and "ret" in f["exits"] and form == "C+splice":
        form = "C+front"      # FRONT_SHIM carries Regs too, and it can also return
    if f.get("sp_unbalanced"):
        reason += f"; sp unbalanced {f['sp_unbalanced']}"
    return form, reason, s["size"] < SHIM_COST[form] + MIN_HOOK


def main() -> None:
    rom = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROM
    img = Image(rom)
    corpus = json.load(open("scratch/c_corpus.json"))["slots"]
    audit_rows = {int(r["callee"], 16) | 1: r["verdict"] for r in json.load(open("scratch/c_callee_audit.json"))}
    rows = []
    for s in corpus:
        if s["empty"]:
            continue
        form, reason, tight = classify(img, s, audit_rows)
        rows.append({"slot": s["name"], "owner": s["owner"], "addr": s["addr"], "size": s["size"],
                     "form": form, "tight": tight, "reason": reason})
    json.dump(rows, open("scratch/c_classify.json", "w"), indent=1)
    c = Counter(r["form"] for r in rows)
    t = Counter(r["form"] for r in rows if r["tight"])
    for form, n in c.most_common():
        print(f"{form:9} {n:4}" + (f"  ({t[form]} tight: expect .S fallback)" if t[form] else ""))
    print(f"-> scratch/c_classify.json ({len(rows)} stubs)")


if __name__ == "__main__":
    main()
