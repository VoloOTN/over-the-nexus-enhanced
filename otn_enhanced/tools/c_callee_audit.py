"""C-migration Phase 0 step 4: may a front's native callee be called from C instead of tail-jumped to?

    uv run python -m otn_enhanced.tools.c_callee_audit [ROM]   # audit every front target in the corpus

A front that ends ``ldr rN,=native; bx rN`` (or ``b native``) hands the engine's registers AND the engine's
stack frame to ``native``. As C (``return native(a, b, c, d);``) it gets a fresh frame, so that's only safe
if ``native``:
  - reads no stack argument / caller frame: no ``sp``-relative access at or above its entry ``sp``;
  - takes no hidden register input: never reads r4-r12 before writing them (``push`` excepted).
The walk follows every branch (tail ``b`` into another function included, with the ``sp`` delta carried) and
gives up (UNKNOWN, a human look) on an indirect jump, ``mov rX, sp``, a ``pc`` write or ARM code.
"""
from __future__ import annotations

import json
import sys

import ndspy.rom

MAX_INSNS = 4000
CALLEE_SAVED = set(range(4, 13))


class Image:
    """arm9 + overlays 3 and 5 as one address space."""

    def __init__(self, rom_path: str):
        rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
        self.parts = [(0x02000000, bytes(rom.arm9))]
        for ov in rom.loadArm9Overlays([3, 5]).values():
            self.parts.append((ov.ramAddress, bytes(ov.data)))

    def u16(self, a: int) -> int:
        for b, d in self.parts:
            if b <= a < b + len(d) - 1:
                return d[a - b] | d[a - b + 1] << 8
        raise KeyError(f"0x{a:08X} not in arm9/ov3/ov5")


def audit(img, entry: int, bounds: tuple[int, int] | None = None, facts: dict | None = None) -> tuple[str, str]:
    """-> ("PASS" | "FAIL" | "UNKNOWN", reason).

    With *facts* (a dict) nothing FAILs: the walk records into it instead -- ``frame`` / ``hidden_read`` (first
    hit), ``clobber`` (r4-r7 written without being pushed), ``exits`` ({"ret", "jump"}), ``targets`` (b-out
    addresses). With *bounds* (lo, hi) the walk stops where control leaves the range (a stub's slot)."""
    if facts is not None:
        facts.setdefault("exits", set()); facts.setdefault("targets", set()); facts.setdefault("clobber", set())
    pushed: set[int] = set()
    if not entry & 1:
        return "UNKNOWN", f"0x{entry:08X} is ARM code"
    probe = facts is not None and facts.get("probe")   # arity probe: r0-r3 count as unwritten too
    todo = [(entry & ~1, 0, frozenset() if probe else frozenset(range(4)))]     # (pc, sp delta, defined regs)
    seen, n = set(), 0
    while todo:
        pc, spd, d = todo.pop()
        while True:
            if bounds and not bounds[0] <= pc < bounds[1]:
                facts["exits"].add("jump"); facts["targets"].add(pc)
                break
            if (pc, spd) in seen:
                break
            seen.add((pc, spd))
            n += 1
            if n > MAX_INSNS:
                return "UNKNOWN", f"over {MAX_INSNS} instructions"
            op = img.u16(pc)
            at = f"0x{pc:08X}"

            def need(*regs):
                bad = [r for r in regs if (r < 13 if probe else r in CALLEE_SAVED) and r not in d]
                if bad and facts is not None:
                    facts.setdefault("reads", set()).update(bad)
                if bad and facts is not None:
                    facts.setdefault("hidden_read", f"{at} r{bad[0]}")
                elif bad:
                    raise _Fail(f"{at} reads r{bad[0]} before writing it (hidden register input)")

            def sp_access(off):
                if spd + off >= 0 and facts is not None:
                    facts.setdefault("frame", f"{at} sp+0x{spd + off:X}")
                elif spd + off >= 0:
                    raise _Fail(f"{at} touches entry sp+0x{spd + off:X} (caller frame / stack arg)")
            try:
                nxt = pc + 2
                if op >> 13 == 0 and op >> 11 != 3:                     # shift imm
                    need(op >> 3 & 7); d |= {op & 7}
                elif op >> 11 == 3:                                     # add/sub reg/imm3
                    need(op >> 3 & 7, *(() if op >> 10 & 1 else (op >> 6 & 7,))); d |= {op & 7}
                elif op >> 13 == 1:                                     # mov/cmp/add/sub imm8
                    k, rd = op >> 11 & 3, op >> 8 & 7
                    if k:
                        need(rd)
                    if k != 1:
                        d |= {rd}
                elif op >> 10 == 0x10:                                  # ALU
                    o, rs, rd = op >> 6 & 0xF, op >> 3 & 7, op & 7
                    need(rs, *(() if o in (9, 0xF) else (rd,)))
                    if o not in (8, 0xA, 0xB):
                        d |= {rd}
                elif op >> 10 == 0x11:                                  # hi-reg ops / bx
                    o, rd, rs = op >> 8 & 3, (op & 7) | (op >> 4 & 8), op >> 3 & 0xF
                    if o == 3:
                        if rs == 14 and not op >> 7 & 1:
                            _ret(at, spd, d, pushed, facts)
                            break
                        if op >> 7 & 1:                     # blx rN: a call through a register
                            if probe:                           # unknown callee: assume it reads them all
                                facts["reads"] = facts.get("reads", set()) | ({0, 1, 2, 3} - d)
                            d |= {0, 1, 2, 3, 12}
                            pc = nxt
                            continue
                        if facts is not None:
                            if probe:                           # indirect tail-jump: it may read them all
                                facts["reads"] = facts.get("reads", set()) | ({0, 1, 2, 3} - d)
                            facts["exits"].add("jump")
                            break
                        return "UNKNOWN", f"{at} indirect bx/blx r{rs}"
                    if 13 in (rd, rs) or rd == 15:
                        return "UNKNOWN", f"{at} hi-reg op on sp/pc (sp escape or jump table)"
                    need(rs, *((rd,) if o < 2 else ()))
                    if o != 1:
                        d |= {rd}
                elif op >> 11 == 9:                                     # ldr pc-rel
                    d |= {op >> 8 & 7}
                elif op >> 12 == 5:                                     # ld/st reg offset
                    o = op >> 9 & 7
                    need(op >> 3 & 7, op >> 6 & 7, *((op & 7,) if o < 3 else ()))
                    if o >= 3:
                        d |= {op & 7}
                elif op >> 13 == 3 or op >> 12 == 8:                    # ld/st imm5, ldrh/strh
                    need(op >> 3 & 7, *(() if op >> 11 & 1 else (op & 7,)))
                    if op >> 11 & 1:
                        d |= {op & 7}
                elif op >> 12 == 9:                                     # ld/st [sp,#imm]
                    sp_access((op & 0xFF) * 4)
                    if op >> 11 & 1:
                        d |= {op >> 8 & 7}
                    else:
                        need(op >> 8 & 7)
                elif op >> 12 == 0xA:                                   # add rd, pc/sp, #imm
                    if op >> 11 & 1:
                        sp_access((op & 0xFF) * 4)
                    d |= {op >> 8 & 7}
                elif op & 0xFF00 == 0xB000:                             # add/sub sp
                    spd += -(op & 0x7F) * 4 if op >> 7 & 1 else (op & 0x7F) * 4
                elif op & 0xF600 == 0xB400:                             # push/pop
                    cnt = bin(op & 0xFF).count("1") + (op >> 8 & 1)
                    if op >> 11 & 1:
                        d |= {i for i in range(8) if op >> i & 1}
                        spd += cnt * 4
                        if op >> 8 & 1:
                            _ret(at, spd, d, pushed, facts)
                            break
                    else:
                        spd -= cnt * 4
                        pushed |= {i for i in range(8) if op >> i & 1}
                elif op >> 12 == 0xC:                                   # ldmia/stmia
                    regs = [i for i in range(8) if op >> i & 1]
                    need(op >> 8 & 7, *(() if op >> 11 & 1 else regs))
                    d |= set(regs) | {op >> 8 & 7} if op >> 11 & 1 else {op >> 8 & 7}
                elif op >> 12 == 0xD:                                   # bcc / swi
                    if op >> 8 & 0xF >= 0xE:
                        return "UNKNOWN", f"{at} swi/undefined"
                    off = op & 0xFF
                    todo.append((pc + 4 + (off - 0x100 if off & 0x80 else off) * 2, spd, d))
                elif op >> 11 == 0x1C:                                  # b
                    off = op & 0x7FF
                    nxt = pc + 4 + (off - 0x800 if off & 0x400 else off) * 2
                elif op >> 11 == 0x1E:                                  # bl / blx pair: a call
                    if probe:
                        lo = img.u16(pc + 2)
                        hi = (op & 0x7FF) - (0x800 if op & 0x400 else 0)
                        tgt = pc + 4 + (hi << 12) + ((lo & 0x7FF) << 1)
                        facts["reads"] = facts.get("reads", set()) | (
                            ({0, 1, 2, 3} if lo >> 11 != 0x1F else arg_regs(img, tgt)) - d)
                    d |= {0, 1, 2, 3, 12}
                    nxt = pc + 4
                else:
                    return "UNKNOWN", f"{at} unhandled opcode 0x{op:04X}"
            except _Fail as f:
                return "FAIL", str(f)
            pc = nxt
    return "PASS", f"{len(seen)} instructions walked"


_ARGS: dict[int, set[int]] = {}


def arg_regs(img, entry: int) -> set[int]:
    """Which of r0-r3 *entry* (a Thumb function) may read before writing, following nested BLs. An upper bound:
    an indirect call, a cycle or a walk that gives up counts as reading all four."""
    a = entry & ~1
    if a not in _ARGS:
        _ARGS[a] = {0, 1, 2, 3}                 # cycle guard
        f = {"probe": 1}
        verdict, _ = audit(img, a | 1, facts=f)
        _ARGS[a] = {0, 1, 2, 3} if verdict == "UNKNOWN" else {r for r in f.get("reads", ()) if r < 4}
    return _ARGS[a]


class _Fail(Exception):
    pass


def _ret(at, spd, d, pushed, facts):
    if facts is None:
        if spd:
            raise _Fail(f"{at} returns with sp delta {spd}")
        return
    facts["exits"].add("ret")
    facts["clobber"] |= (set(d) & {4, 5, 6, 7}) - pushed
    if spd:
        facts.setdefault("sp_unbalanced", f"{at} delta {spd}")


def front_targets(corpus: list[dict]) -> dict[int, list[str]]:
    """native address -> the front slots that tail-jump to it (``ldr rN,=X; bx rN`` or ``b X`` out of the slot)."""
    from otn_enhanced.asm.thumb_disasm import decode_thumb
    out: dict[int, list[str]] = {}
    for s in corpus:
        base, raw = int(s["addr"], 16), bytes.fromhex(s["bytes"])
        if s["empty"]:
            continue
        pool = {}
        for i in decode_thumb(raw, base):
            if i.is_pool_ref:
                o = i.pool_addr - base
                pool[i.operands.split(",")[0].strip().upper()] = (int.from_bytes(raw[o:o + 4], "little")
                                                                  if 0 <= o <= len(raw) - 4 else None)
            elif i.mnemonic == "BX" and not i.is_return and pool.get(i.operands.strip().upper()) is not None:
                out.setdefault(pool[i.operands.strip().upper()], []).append(s["name"])
            elif i.mnemonic == "B" and not (base <= i.branch_target < base + len(raw)):
                out.setdefault(i.branch_target | 1, []).append(s["name"])
            elif i.mnemonic not in ("CMP", "CMN", "TST", "BX") and not i.mnemonic.startswith(("STR", "PUSH", "B")):
                pool.pop(i.operands.split(",")[0].strip().upper(), None)   # overwritten: no longer the literal
    return out


if __name__ == "__main__":
    from otn_enhanced.tools.c_corpus import DEFAULT_ROM
    rom = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROM
    img = Image(rom)
    # self-check on synthetic code placed over a known-blank address
    fake = {0x02000000: bytes.fromhex("10b5" "0098" "10bd"),     # push {r4,lr}; ldr r0,[sp]=saved r4: own frame
            0x02000010: bytes.fromhex("10b5" "0298" "10bd"),     # ldr r0,[sp,#8]: entry sp+0 -> stack arg
            0x02000020: bytes.fromhex("2000" "7047"),            # movs r0,r4: hidden r4 input
            0x02000030: bytes.fromhex("10b5" "2000" "10bd")}     # push then read r4: still hidden input
    class _F:
        def u16(self, a):
            for b, dta in fake.items():
                if b <= a < b + len(dta):
                    return dta[a - b] | dta[a - b + 1] << 8
            raise KeyError(hex(a))
    got = [audit(_F(), a | 1)[0] for a in fake]
    assert got == ["PASS", "FAIL", "FAIL", "FAIL"], got
    corpus = json.load(open("scratch/c_corpus.json"))["slots"]
    rows = []
    spans = [(int(s["addr"], 16), int(s["addr"], 16) + s["size"], s["name"]) for s in corpus]
    for tgt, fronts in sorted(front_targets(corpus).items()):
        own = next((n for lo, hi, n in spans if lo <= tgt & ~1 < hi), None)
        if own:      # a jump into our own code (shared tail / next stub): not a native callee
            verdict, why = "INTERNAL", own
        else:
            try:
                verdict, why = audit(img, tgt)
            except KeyError as e:
                verdict, why = "UNKNOWN", str(e)
        rows.append({"callee": f"0x{tgt & ~1:08X}", "verdict": verdict, "why": why, "fronts": fronts})
    json.dump(rows, open("scratch/c_callee_audit.json", "w"), indent=1)
    from collections import Counter
    print("self-check OK;", dict(Counter(r["verdict"] for r in rows)), f"over {len(rows)} callees",
          f"/ {sum(len(r['fronts']) for r in rows)} fronts -> scratch/c_callee_audit.json")
