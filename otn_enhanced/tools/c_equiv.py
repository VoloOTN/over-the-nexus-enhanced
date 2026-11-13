"""C-migration Phase 0 step 3: trace-equivalence of two stub blobs at the same slot.

    from otn_enhanced.tools.c_equiv import equiv
    rep = equiv(old_blob, new_blob, base, args=(ctx_ptr,), ss=None)   # raises EquivError on a mismatch

Both blobs run on scratch/thumbemu.py over the same memory: a savestate (``ss``, anything with ``u8(addr)``)
or, without one, deterministic hash-filled memory so every struct read has a distinct value. Any branch that
leaves the blob is an engine call: it is recorded with r0-r3 and answered from a script instead of executed.
The script is swept depth-first over ``RETURNS`` for every call, so each predicate outcome runs.

Per path the two runs must agree on: the engine call sequence and its args, every memory write outside the
stub's own stack frame, the return value and r4-r7 (or, for a tail-jump out of the blob, r0-r7 + sp at the
jump). Any read at or above the entry sp is an undeclared frame read and fails unless ``frame_ok``.

    uv run python -m otn_enhanced.tools.c_equiv     # self-check
"""
from __future__ import annotations

import functools
import hashlib
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "scratch"))   # last: scratch/dis.py shadows stdlib
from thumbemu import MAGIC_LR, Emu, Mem  # noqa: E402

SP0 = 0x027E0000          # entry sp; the frame read window is [SP0, SP0 + FRAME_WIN)
FRAME_WIN = 0x400
STACK_LO = SP0 - 0x1000   # writes in [STACK_LO, SP0) are the stub's own frame: not compared
RETURNS = (0, 1, 2, 0xFFFFFFFF)
MAX_PATHS = 4096          # ponytail: hard cap on swept paths; raise it if a stub has many predicate calls
MAX_CALLS = 64
POISON = [0xDEAD0001, 0xDEAD0002, 0xDEAD0003]


class EquivError(AssertionError):
    pass


class _HashMem:
    def __init__(self, plant: dict[int, int] | None = None):
        self.plant = plant or {}            # byte overrides: steer memory-dependent branches

    def u8(self, a: int) -> int:
        if a in self.plant:
            return self.plant[a]
        return hashlib.blake2b(a.to_bytes(4, "little"), digest_size=1).digest()[0]


class _Mem(Mem):
    def __init__(self, ss, blob: bytes, base: int):
        super().__init__(ss)
        self.code = (base, blob)
        self.frame_reads: set[int] = set()

    def r8(self, a: int) -> int:
        base, blob = self.code
        if base <= a < base + len(blob):
            return blob[a - base]
        if SP0 <= a < SP0 + FRAME_WIN and a not in self.w:
            self.frame_reads.add(a & ~3)
        return super().r8(a)


@functools.cache
def _arity() -> dict[int, int]:
    """engine address -> register-arg count, from the engine.h prototypes. A callee not in engine.h compares all
    of r0-r3, which can flag dead scratch registers: declare it in engine.h to compare only its real args."""
    c = Path(__file__).resolve().parents[1] / "asm" / "c"
    protos = {m.group(1): 0 if m.group(2).strip() in ("", "void") else m.group(2).count(",") + 1
              for m in re.finditer(r"^\w[\w\s\*]*?\b(\w+)\(([^)]*)\);", (c / "engine.h").read_text(), re.M)}
    out = {}
    for line in (c / "engine_syms.txt").read_text().splitlines():
        f = line.split()
        if len(f) >= 2 and not line.startswith("#") and f[1] in protos:
            out[int(f[0], 16)] = protos[f[1]]
    from otn_enhanced.tools.c_corpus import slot_symbols
    for name, addr in slot_symbols().items():       # our own stubs called as slot_<NAME>
        if f"slot_{name}" in protos:
            out[addr] = protos[f"slot_{name}"]
    return out


def _call_args(e, m, n: int) -> list:
    """The first n args at a call: r0-r3, then the stack words at sp (5th+). An arg pointing into the stub's own
    frame is compared by the word it points at, since the two builds lay their frames out differently."""
    vals = [e.r[i] for i in range(min(n, 4))] + [m.r32(e.r[13] + 4 * i) for i in range(max(n - 4, 0))]
    # ponytail: one pointee word; widen it if a callee takes a pointer to a bigger local struct
    return [("&frame", m.r32(v)) if STACK_LO <= v < SP0 else v for v in vals]


def _run(blob: bytes, base: int, args, ss, script: list[int], all_regs: bool = False) -> dict:
    m = _Mem(ss if hasattr(ss, "u8") else _HashMem(ss), blob, base)
    e = Emu(m, sp=SP0)
    for i, a in enumerate(args):
        e.r[i] = a & 0xFFFFFFFF
    e.r[14], e.r[15] = MAGIC_LR, base | 1
    calls, steps, just_called = [], 0, False
    while True:
        pc = e.r[15] & ~1
        if pc == MAGIC_LR & ~1:
            exit_ = ("ret", *(e.r[0:8] if all_regs else (e.r[0], *e.r[4:8])))
            break
        if not (base <= pc < base + len(blob)):
            # left the blob by BL/BLX: an engine call. Any other way out is a tail-jump, which ends the run.
            if just_called:
                k = len(calls)
                if k >= MAX_CALLS:
                    raise EquivError(f"more than {MAX_CALLS} engine calls")
                calls.append((pc, *_call_args(e, m, _arity().get(pc, 4))))
                e.r[0] = script[k] if k < len(script) else RETURNS[0]
                e.r[1:4] = POISON          # the callee clobbers r1-r3; same junk for both runs
                e.r[15] = e.r[14] | 1
                just_called = False
                continue
            exit_ = ("jump", pc, *e.r[0:8], e.r[13])
            break
        steps += 1
        if steps > 100000:
            raise EquivError(f"step limit at 0x{pc:08X}")
        op = m.r16(pc)
        just_called = op >> 11 == 0b11110 or (op & 0xFF80) == 0x4780   # BL prefix / BLX reg
        e.step()
    writes = {a: v for a, v in m.w.items() if not (STACK_LO <= a < SP0)}
    return {"calls": calls, "exit": exit_, "writes": writes, "frame_reads": m.frame_reads}


def equiv(old: bytes, new: bytes, base: int, args=(), ss=None, frame_ok: bool = False, all_regs: bool = False,
          returns: tuple = ()) -> dict:
    # ss: a savestate (anything with u8), or a {addr: byte} dict planted into the hash memory, or None
    """-> {"paths": n}. Raises EquivError naming the first diverging path. all_regs: a return compares r0-r7
    (splice / front returns land mid-function in the engine, where every register may be live)."""
    todo, paths = [[]], 0
    while todo:
        script = todo.pop()
        a, b = _run(old, base, args, ss, script, all_regs), _run(new, base, args, ss, script, all_regs)
        paths += 1
        for key in ("calls", "exit", "writes"):
            if a[key] != b[key]:
                raise EquivError(f"script {script}: {key} differ\n old {_fmt(a[key])}\n new {_fmt(b[key])}")
        if not frame_ok and (a["frame_reads"] or b["frame_reads"]):
            reads = sorted(a["frame_reads"] | b["frame_reads"])
            raise EquivError(f"script {script}: reads above entry sp at {[f'sp+0x{r - SP0:X}' for r in reads]}")
        n = len(a["calls"])
        if len(script) < n:          # the first unscripted call: branch on each return value
            todo.extend(script + [v] for v in (*RETURNS, *returns))   # returns: values a stub compares a result to
        if paths > MAX_PATHS:
            raise EquivError(f"more than {MAX_PATHS} paths")
    return {"paths": paths}


def _fmt(x) -> str:
    if isinstance(x, dict):
        return "{" + ", ".join(f"0x{k:08X}:{v:02X}" for k, v in sorted(x.items())[:16]) + "}"
    h = lambda v: hex(v) if isinstance(v, int) else f"&frame->{v[1]:#x}"
    return repr([tuple(h(v) for v in t) for t in x]) if isinstance(x, list) else repr(tuple(h(v) for v in x[1:]))


if __name__ == "__main__":
    import json
    from otn_enhanced.asm.cc import compile_c
    from otn_enhanced.effects.cave3 import CAVE3_PIPER_RES
    corpus = {s["name"]: s for s in json.load(open("scratch/c_corpus.json"))["slots"]}
    old = bytes.fromhex(corpus["CAVE3_PIPER_RES"]["bytes"])
    new = compile_c(Path("otn_enhanced/cards/c/mystic_piper.c"), CAVE3_PIPER_RES)
    ctx = 0x02300000
    rep = equiv(old, new, CAVE3_PIPER_RES, args=(ctx,))
    # negative: second draw count 1 -> 2 must be caught
    i = new.rfind(bytes.fromhex("0121"))          # movs r1, #1 before the last draw
    bad = new[:i] + bytes.fromhex("0221") + new[i + 2:]
    try:
        equiv(old, bad, CAVE3_PIPER_RES, args=(ctx,))
        raise AssertionError("mutated blob passed")
    except EquivError as err:
        caught = str(err).splitlines()[0]
    for desc, o, n in (("frame read", "009870470000", "009870470000"),     # ldr r0,[sp]; bx lr
                       ("write", "086070470000", "c04670470000")):         # str r0,[r1] vs nop; bx lr
        try:
            equiv(bytes.fromhex(o), bytes.fromhex(n), 0x02000000, args=(5, 0x02100000))
            raise AssertionError(f"{desc} not caught")
        except EquivError:
            pass
    # stack args (5th+) are read from sp, and an arg pointing into the stub's own frame becomes its pointee
    class _E:
        r = [1, 2, 3, SP0 - 0x10] + [0] * 9 + [SP0 - 0x20, 0, 0]
    fm = _Mem(_HashMem({SP0 - 0x10: 0x2A, SP0 - 0x20: 7, SP0 - 0x1C: 9}), b"", 0)
    assert _call_args(_E, fm, 6)[3:] == [("&frame", fm.r32(SP0 - 0x10)), fm.r32(SP0 - 0x20), fm.r32(SP0 - 0x1C)]
    print(f"c_equiv self-check OK: Piper old vs C equal over {rep['paths']} paths; mutation caught ({caught})")
