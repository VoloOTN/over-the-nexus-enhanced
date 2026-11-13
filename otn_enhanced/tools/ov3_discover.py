"""Recursive-descent function discovery over overlay 3 (stock EU ROM).

``run(rom) -> {start: Func}``: every ov3 function with its mode (Thumb/ARM),
instruction set, literal-pool words, switch tables, calls and the evidence that
made it a function entry.

Entry evidence, strongest first: card handler table / static-init array; a
code pointer in ov3 or ov5; a PUSH/STMFD prologue in an uncovered gap; a BL
from a *different* function.  mwcc emits ``BL <label>`` as a far branch inside
large functions, so a BL target with no independent evidence that lies in the
caller's own span is followed as a branch, and any two functions whose code
overlaps are resolved by demoting the weaker-evidenced one to a fragment.
arm9/ov41 values that look like ov3 pointers were measured as noise (141/142
arm9 hits lack a prologue) and are ignored.
"""
import struct
import sys
from dataclasses import dataclass, field

import capstone
import ndspy.rom

B = 0x02141700
HTAB = B + 0x134508          # card handler table (5 x thumb ptr + cid) x 4116
HTAB_N = 4116
INIT_LO, INIT_HI = 0x0228FA28, 0x0228FA50
CORESIDENT = (5, 41, 47, 48, 49)


@dataclass
class Func:
    start: int
    mode: str                       # "thumb" | "arm"
    seeds: set = field(default_factory=set)
    code: set = field(default_factory=set)      # instruction start addrs
    sizes: dict = field(default_factory=dict)   # insn addr -> size
    pool: set = field(default_factory=set)      # 4-byte literal words
    tables: dict = field(default_factory=dict)  # table addr -> (size, esize)
    calls: set = field(default_factory=set)     # (target, mode)
    tailcalls: set = field(default_factory=set)
    farbr: set = field(default_factory=set)     # BL used as a far branch
    bad: str = ""                   # first invalid-instruction reason
    end: int = 0


def u16(d, o): return struct.unpack_from("<H", d, o)[0]
def u32(d, o): return struct.unpack_from("<I", d, o)[0]


class Ov3:
    def __init__(self, rom):
        r = ndspy.rom.NintendoDSRom.fromFile(str(rom))
        self.ov = bytes(r.loadArm9Overlays([3])[3].data)
        self.end = B + len(self.ov)
        self.arm9 = bytes(r.arm9)
        ovs = r.loadArm9Overlays(list(CORESIDENT))
        self.others = {i: bytes(ovs[i].data) for i in CORESIDENT}
        self.cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)

    def inside(self, a): return B <= a < self.end
    def h(self, a): return u16(self.ov, a - B)
    def w(self, a): return u32(self.ov, a - B)


# ----------------------------------------------------------------- Thumb
_VALID_B = {0xB0, 0xB4, 0xB5, 0xBC, 0xBD}


def thumb_step(o, a):
    """Decode one Thumb-1 insn at a. Returns dict or None(invalid)."""
    if not o.inside(a + 1):
        return None
    hw = o.h(a)
    top5 = hw >> 11
    if top5 == 0b11110:
        if not o.inside(a + 3):
            return None
        hw2 = o.h(a + 2)
        t2 = hw2 >> 11
        if t2 not in (0b11111, 0b11101):
            return None
        hi = hw & 0x7FF
        if hi & 0x400:
            hi -= 0x800
        tgt = a + 4 + (hi << 12) + ((hw2 & 0x7FF) << 1)
        if t2 == 0b11101:
            if hw2 & 1:
                return None
            return dict(size=4, kind="blx", tgt=tgt & ~3)
        return dict(size=4, kind="bl", tgt=tgt)
    if top5 in (0b11101, 0b11111):
        return None
    hi8 = hw >> 8
    if hi8 >> 4 == 0xB and hi8 not in _VALID_B:
        return None
    if hi8 == 0xDE or hi8 == 0xBE:
        return None
    # PC-relative LDR
    if hw >> 11 == 0b01001:
        pa = ((a + 4) & ~3) + (hw & 0xFF) * 4
        return dict(size=2, kind="ldrpc", pool=pa, rd=(hw >> 8) & 7)
    # conditional branch
    if hw >> 12 == 0xD:
        if hi8 == 0xDF:
            return dict(size=2, kind="seq")
        off = hw & 0xFF
        if off & 0x80:
            off -= 0x100
        return dict(size=2, kind="bcc", tgt=a + 4 + off * 2)
    if hw >> 11 == 0b11100:
        off = hw & 0x7FF
        if off & 0x400:
            off -= 0x800
        return dict(size=2, kind="b", tgt=a + 4 + off * 2)
    if hw & 0xFF00 == 0xBD00:
        return dict(size=2, kind="ret")
    if hw & 0xFF80 == 0x4700:          # BX Rm
        if hw & 7:
            return None
        return dict(size=2, kind="ret")
    if hw & 0xFF80 == 0x4780:          # BLX Rm (v5) - call through register
        return dict(size=2, kind="seq")
    if hw & 0xFF87 == 0x4687:          # MOV PC, Rm
        return dict(size=2, kind="ret")
    if hw & 0xFF87 == 0x4487:          # ADD PC, Rm -> jump table
        return dict(size=2, kind="addpc", rm=(hw >> 3) & 0xF)
    return dict(size=2, kind="seq")


def thumb_jumptable(o, a_addpc):
    """Parse the mwcc switch idiom ending at ADD PC,Rx (a_addpc).

    CMP Rn,#N ; BHI dflt ; ADD Rx,Rn,Rn|ADD Rx,Rn,#0 ; ADD Rx,PC ; LDRH|LDRB Rx,[Rx,#imm]
    ; LSL Rx,#16 ; ASR Rx,#16 ; ADD PC,Rx      -> entries at (ADD Rx,PC)+4+imm,
    target = a_addpc + 4 + entry
    Returns (table_addr, n, esize, [targets]) or None.
    """
    a = a_addpc
    seq = [o.h(a - 2 * k) for k in range(1, 9)]
    # find ADD Rx, PC (0x4478 | rx) and LDRH/LDRB just after it
    for k in range(1, 6):
        hw = o.h(a - 2 * k)
        if hw & 0xFFF8 == 0x4478:
            ld = o.h(a - 2 * k + 2)
            if ld >> 11 == 0b10001:        # LDRH imm5*2
                esize, imm = 2, ((ld >> 6) & 0x1F) * 2
            elif ld >> 11 == 0b01111:      # LDRB imm5
                esize, imm = 1, (ld >> 6) & 0x1F
            else:
                return None
            tab = (a - 2 * k) + 4 + imm
            break
    else:
        return None
    # Table length: CMP Rn,#N then BHI dflt (N+1) / BLS ok;B dflt (N+1) /
    # BCS dflt (N).  Register-bounded switches (SUB;BMI) have no CMP #imm: then
    # read until the first case body (mwcc lays bodies after the table) or the
    # first entry that cannot be a case target.
    bound = None
    for k in range(1, 11):
        hw = o.h(a - 2 * k)
        nxt = o.h(a - 2 * k + 2) >> 8
        if hw >> 11 == 0b00101 and nxt in (0xD8, 0xD9, 0xD2):
            bound = (hw & 0xFF) + (0 if nxt == 0xD2 else 1)
            break
    tg = []
    lim = a + 4 + 0x10000
    i = 0
    while (bound is None and tab + esize * (i + 1) <= lim) or (bound is not None and i < bound):
        e = o.h(tab + 2 * i) if esize == 2 else o.ov[tab + i - B]
        if esize == 2 and e & 0x8000:
            e -= 0x10000
        t = a + 4 + e
        if t <= a or t & 1 or not o.inside(t):
            if bound is not None:
                return None
            break
        tg.append(t)
        lim = min(lim, t)
        i += 1
    n = len(tg)
    if not n:
        return None
    return tab, n, esize, tg


# ------------------------------------------------------------------- ARM
_ARM_V6PLUS = {"movw", "movt", "ldrex", "strex", "rev", "uxth", "uxtb", "sxth",
               "sxtb", "cpsid", "cpsie", "dmb", "dsb", "isb", "bfi", "bfc",
               "ubfx", "sbfx", "rbit", "udiv", "sdiv", "pld", "ldrd", "strd"}


def arm_step(o, a):
    if not o.inside(a + 3) or a & 3:
        return None
    w = o.w(a)
    insns = list(o.cs.disasm(struct.pack("<I", w), a, 1))
    if not insns:
        return None
    i = insns[0]
    mn = i.mnemonic
    cond = w >> 28
    base = mn.rstrip(".w")
    if cond == 0xF and not mn.startswith("blx"):
        return None
    if any(base.startswith(x) for x in _ARM_V6PLUS) and base not in ("ldrd", "strd"):
        return None
    d = dict(size=4, kind="seq", txt=f"{mn} {i.op_str}".strip())
    op = i.op_str
    # literal load
    if (w & 0x0F7F0000) == 0x051F0000:          # LDR Rd,[PC,#+-imm]
        imm = w & 0xFFF
        pa = a + 8 + (imm if w & 0x00800000 else -imm)
        if ((w >> 12) & 0xF) == 15:
            return dict(d, kind="ret" if cond == 0xE else "seq")
        return dict(d, kind="ldrpc", pool=pa)
    if (w & 0x0E000000) == 0x0A000000:           # B / BL / BLX imm
        off = w & 0xFFFFFF
        if off & 0x800000:
            off -= 0x1000000
        tgt = a + 8 + off * 4
        if cond == 0xF:
            return dict(d, kind="blx", tgt=tgt + (2 if w & 0x01000000 else 0) | 1)
        if w & 0x01000000:
            return dict(d, kind="bl", tgt=tgt)
        return dict(d, kind="b" if cond == 0xE else "bcc", tgt=tgt)
    if (w & 0x0FFFFFF0) == 0x012FFF10:           # BX Rm
        return dict(d, kind="ret" if cond == 0xE else "seq")
    if (w & 0x0FFFFFF0) == 0x012FFF30:           # BLX Rm
        return dict(d, kind="seq")
    if (w & 0x0E108000) == 0x08108000:           # LDM with PC
        return dict(d, kind="ret" if cond == 0xE else "seq")
    rd = (w >> 12) & 0xF
    if rd == 15 and (w & 0x0C000000) == 0:       # data-processing writing PC
        if (w & 0x0FFFF000) == 0x008FF000 and ((w >> 25) & 1) == 0:
            # ADDcc PC, PC, Rm, LSL #2  -> jump table
            return dict(d, kind="armtab", cond=cond)
        if (w & 0x0FFFFFFF) == 0x01A0F00E:       # MOV PC, LR
            return dict(d, kind="ret" if cond == 0xE else "seq")
        return dict(d, kind="ret" if cond == 0xE else "seq")
    if rd == 15 and (w & 0x0C100000) == 0x04100000:   # LDR PC, [...]
        return dict(d, kind="ret" if cond == 0xE else "seq")
    return d


def arm_jumptable(o, a):
    """ADDcc PC,PC,Rn,LSL#2: slot a+4 = default, one insn per case from a+8.
    Count = CMP Rn,#N (+1) just before; else B-words until the lowest target."""
    for k in range(1, 4):
        w = o.w(a - 4 * k)
        if (w & 0x0FF00000) == 0x03500000:
            rot = ((w >> 8) & 0xF) * 2
            imm = w & 0xFF
            n = ((imm >> rot) | (imm << (32 - rot))) & 0xFFFFFFFF
            return a + 8, n + 1
    tab, n, lim = a + 8, 0, o.end
    while tab + 4 * n < lim and (o.w(tab + 4 * n) >> 24) == 0xEA:
        off = o.w(tab + 4 * n) & 0xFFFFFF
        if off & 0x800000:
            off -= 0x1000000
        lim = min(lim, tab + 4 * n + 8 + off * 4)
        n += 1
    return (tab, n) if n else None


# --------------------------------------------------------------- descent
_MEMO = {}
import bisect
SPAN = []        # sorted STRONG starts once the span rule is switched on


def span_end(a):
    """Next independently-evidenced entry point after a (0 while rule is off)."""
    if not SPAN:
        return 0
    j = bisect.bisect_right(SPAN, a)
    return SPAN[j] if j < len(SPAN) else 0


FRAGMENT = set()   # proven pieces of a larger function (overlap resolution)
FORCE_FAR = set()  # BL sites proven far-branches by the retry in descend_retry
STRONG = set()   # addresses with independent evidence of being a function entry


def _step(o, a, mode):
    k = (a, mode)
    if k not in _MEMO:
        _MEMO[k] = (thumb_step if mode == "thumb" else arm_step)(o, a)
    return _MEMO[k]


def descend(o, f, starts):
    step = lambda o_, a_: _step(o_, a_, f.mode)
    work = [f.start]
    while work:
        a = work.pop()
        while True:
            if a in f.code:
                break
            if a != f.start and a in starts:
                f.tailcalls.add(a)
                break
            if not o.inside(a):
                f.bad = f.bad or f"leaves ov3 at 0x{a:08X}"
                break
            d = step(o, a)
            if d is None:
                f.bad = f.bad or f"invalid insn at 0x{a:08X}"
                break
            f.code.add(a)
            f.sizes[a] = d["size"]
            k = d["kind"]
            nxt = a + d["size"]
            if k == "ldrpc":
                if o.inside(d["pool"]) and d["pool"] < o.end - 3:
                    f.pool.add(d["pool"])
            elif k == "bl":
                t = d["tgt"]
                # mwcc far branch: BL <label in this function>; NOP; pool
                if (f.mode == "thumb" and t > f.start
                        and (not plausible_entry(o, t) or t in FRAGMENT
                             or (t not in STRONG
                                 and ((o.inside(nxt + 1) and o.h(nxt) == 0x46C0)
                                      or a in FORCE_FAR or t < span_end(f.start))))):
                    f.farbr.add(a)
                    a = t
                    continue
                f.calls.add((t, f.mode))
            elif k == "blx":
                f.calls.add((d["tgt"] & ~1, "arm" if f.mode == "thumb" else "thumb"))
            elif k == "bcc":
                work.append(d["tgt"])
            elif k == "b":
                t = d["tgt"]
                if t != f.start and t in starts:
                    f.tailcalls.add(t)
                    break
                a = t
                continue
            elif k == "ret":
                break
            elif k == "addpc":
                jt = thumb_jumptable(o, a)
                if jt is None:
                    f.bad = f.bad or f"unparsed jump table at 0x{a:08X}"
                    break
                tab, n, es, tg = jt
                f.tables[tab] = (n * es, es)
                work.extend(tg)
                break
            elif k == "armtab":
                jt = arm_jumptable(o, a)
                if jt is None:
                    f.bad = f.bad or f"unparsed ARM jump table at 0x{a:08X}"
                    break
                tab, n = jt
                work.extend(tab + 4 * i for i in range(n))
                work.append(a + 4)   # default slot (out-of-range case)
                break
            a = nxt
    if f.code:
        hi = max(x + f.sizes[x] for x in f.code)
        hi = max([hi] + [p + 4 for p in f.pool if p > f.start and p - hi < 0x400]
                 + [t + s for t, (s, _) in f.tables.items()])
        f.end = hi + (hi & 1)


def descend_retry(o, f, starts):
    """On an invalid insn, the culprit is usually a BL used as a far branch with
    the pool right behind it (no NOP pad).  Re-classify the non-STRONG BL whose
    return address is the closest one below the bad address, and retry."""
    for _ in range(8):
        descend(o, f, starts)
        if not f.bad.startswith("invalid") or f.mode != "thumb":
            return
        bad = int(f.bad.split()[-1], 16)
        cands = [x for x in f.code if f.sizes[x] == 4 and x + 4 <= bad
                 and x not in FORCE_FAR and x not in f.farbr
                 and _step(o, x, "thumb")["kind"] == "bl"
                 and _step(o, x, "thumb")["tgt"] > f.start
                 and _step(o, x, "thumb")["tgt"] not in STRONG]
        if not cands:
            return
        FORCE_FAR.add(max(cands))
        f.__init__(f.start, f.mode, f.seeds)


# --------------------------------------------------------------- seeds
def is_thumb_start_plausible(o, a):
    if a & 1 or not o.inside(a + 1):
        return False
    return thumb_step(o, a) is not None


def gather_seeds(o):
    seeds = {}   # addr -> (mode, set(reasons))

    def add(a, mode, why):
        m, r = seeds.setdefault(a, (mode, set()))
        if m != mode:
            # conflicting mode claims: keep first, note
            r.add(f"modeclash:{mode}")
        r.add(why)

    for i in range(HTAB_N):
        off = HTAB - B + i * 24
        for s, p in enumerate(struct.unpack_from("<5I", o.ov, off)):
            if p and o.inside(p):
                add(p & ~1, "thumb" if p & 1 else "arm", "handler_table")
    for a in range(INIT_LO, INIT_HI, 4):
        p = o.w(a)
        if p:
            add(p & ~1, "thumb" if p & 1 else "arm", "static_init")
    # pointers: ov3 data words + arm9 + co-resident overlays
    # arm9 / ov41 "pointers" into ov3 measured as noise (141/142 arm9 hits have
    # no prologue): arm9 cannot reference an overlay that shares its address
    # range with ov0/1/11/27.  Only ov3 itself and ov5 count.
    blobs = [("ov3", o.ov), ("ov5", o.others[5])]
    ptrs = {}
    for name, d in blobs:
        for off in range(0, len(d) - 3, 4):
            p = u32(d, off)
            if B <= p < o.end:
                ptrs.setdefault(p, set()).add(name)
    return seeds, ptrs


def arm_prologue(o, a):
    if a & 3 or not o.inside(a + 3):
        return False
    w = o.w(a)
    return (w & 0xFFFF4000) == 0xE92D4000 or (w & 0xFFFFFFFF) == 0xE52DE004


def plausible_entry(o, a):
    """A non-PUSH Thumb entry must not sit right after a conditional branch or
    a BL (that is mid-function fall-through)."""
    if thumb_prologue(o, a):
        return True
    if not o.inside(a - 4):
        return True
    p = o.h(a - 2)
    if 0xD0 <= p >> 8 <= 0xDD:
        return False
    if o.h(a - 4) >> 11 == 0b11110 and p >> 11 in (0b11111, 0b11101):
        return False
    return True


def thumb_prologue(o, a):
    return not (a & 1) and o.inside(a + 1) and (o.h(a) & 0xFF00) == 0xB500


def run(rom):
    o = Ov3(rom)
    seeds, ptrs = gather_seeds(o)
    funcs: dict[int, Func] = {}
    claimed = set()      # bytes covered by code/pool/tables

    def coverage(f):
        cov = set()
        for x in f.code:
            cov.update(range(x, x + f.sizes[x]))
        for p in f.pool:
            cov.update(range(p, p + 4))
        for t, (s, _) in f.tables.items():
            cov.update(range(t, t + s))
        return cov

    starts = set()
    cov = set()
    tried = set()

    def try_add(a, mode, why, strict):
        if a in funcs:
            funcs[a].seeds.add(why)
            return True
        if (a, mode, strict) in tried:
            return False
        tried.add((a, mode, strict))
        if strict and a in cov:
            return False
        f = Func(a, mode, {why})
        starts.add(a)
        descend_retry(o, f, starts)
        if f.bad and strict:
            starts.discard(a)
            return False
        funcs[a] = f
        cov.update(coverage(f))
        return True

    STRONG.update(seeds)
    STRONG.update(p & ~1 for p in ptrs if p & 1 and plausible_entry(o, p & ~1))
    STRONG.update(a for a in range(B, o.end - 1, 2) if thumb_prologue(o, a))
    pending = [(a, m, ",".join(sorted(r)), False) for a, (m, r) in seeds.items()]
    # odd pointers anywhere -> thumb candidates (strict); even ptrs with ARM prologue
    for p, src in ptrs.items():
        why = "ptr:" + ",".join(sorted(src))
        if p & 1:
            if plausible_entry(o, p & ~1):
                pending.append((p & ~1, "thumb", why, True))
        elif arm_prologue(o, p):
            pending.append((p, "arm", why, True))
    rounds = 0
    while pending:
        rounds += 1
        nxt = []
        for a, m, why, strict in pending:
            try_add(a, m, why, strict)
        for f in list(funcs.values()):
            for t, m in f.calls:
                if o.inside(t) and t not in funcs and (t, m, False) not in tried:
                    nxt.append((t, m, f"call:{f.start:08X}", False))
        # gap prologue scan once direct discovery is exhausted
        if not nxt:
            for a in range(B, o.end - 4, 2):
                if a in cov or a in funcs:
                    continue
                if thumb_prologue(o, a):
                    nxt.append((a, "thumb", "gap_prologue", True))
                elif arm_prologue(o, a):
                    nxt.append((a, "arm", "gap_prologue", True))
            nxt = [x for x in nxt if x[0] not in funcs and (x[0], x[1], x[3]) not in tried]
            # only one gap pass per fixpoint, then re-run calls
            if not nxt:
                break
        pending = nxt
        print(f"round {rounds}: funcs={len(funcs)} pending={len(pending)}", file=sys.stderr)

    # final pass.  A BL target is a function entry only with independent
    # evidence (pointer / handler table / prologue / ARM / BL'd from >=2
    # functions); otherwise a BL into the caller's own span is mwcc's far
    # branch.  Rebuild from the evidenced entries, following real calls only.
    STRONG.update(a for a, f in funcs.items() if f.mode == "arm")
    span0 = sorted(STRONG)

    def span_of(x):
        j = bisect.bisect_right(span0, x) - 1
        return span0[j] if j >= 0 else 0

    sites = set()
    for f in funcs.values():
        for x in f.code:
            if f.mode == "thumb" and f.sizes[x] == 4:
                d = _step(o, x, "thumb")
                if d["kind"] == "bl":
                    sites.add((x, d["tgt"]))
                elif d["kind"] == "blx":
                    STRONG.add(d["tgt"])
            elif f.mode == "arm":
                d = _step(o, x, "arm")
                if d["kind"] in ("bl", "blx"):
                    STRONG.add(d["tgt"] & ~1)
    # BL'd from outside its own span => a real callee
    STRONG.update(t for x, t in sites if span_of(x) != span_of(t) and plausible_entry(o, t))
    # a Thumb "entry" inside an ARM function's instruction bytes is a constant
    armbytes = set()
    for f in funcs.values():
        if f.mode == "arm":
            for x in f.code:
                armbytes.update(range(x, x + 4))
    hard = {a for a, f in funcs.items()
            if any("handler_table" in x or "static_init" in x for x in f.seeds)}
    for a, f in funcs.items():
        if f.mode == "thumb" and a in armbytes and a not in hard:
            STRONG.discard(a)
    SPAN[:] = sorted(STRONG)
    modes0 = {a: f.mode for a, f in funcs.items()}
    seeds0 = {a: set(f.seeds) for a, f in funcs.items()}

    def rank(a, seeds):
        j = " ".join(seeds)
        if "handler_table" in j or "static_init" in j:
            return 3
        if "ptr:" in j:
            return 2
        if modes0.get(a) == "arm" or thumb_prologue(o, a):
            return 1
        return 0

    for it in range(12):
        modes = dict(modes0)
        seeds_of = {a: set(v) for a, v in seeds0.items()}
        final = {}
        queue = [a for a in funcs if a in STRONG and a not in FRAGMENT]
        starts = set(queue)
        while queue:
            a = queue.pop()
            if a in final:
                continue
            g = Func(a, modes.get(a, "thumb"), set(seeds_of.get(a, ())))
            descend_retry(o, g, starts)
            final[a] = g
            for t, m in g.calls:
                if o.inside(t) and t not in final:
                    if t not in modes:
                        modes[t] = m
                        seeds_of[t] = set()
                    seeds_of[t].add(f"call:{a:08X}")
                    if t not in starts:
                        starts.add(t)
                        queue.append(t)
        # re-descend once with the complete start set (tail-call stops)
        starts = set(final)
        cur = {}
        for a, f in final.items():
            g = Func(a, f.mode, seeds_of.get(a, set()) | f.seeds)
            descend_retry(o, g, starts)
            cur[a] = g
        # overlap => the weaker-evidenced side is a fragment of the other
        owner = {}
        newfrag = set()
        for a in sorted(cur):
            g = cur[a]
            for x in g.code:
                for b_ in range(x, x + g.sizes[x]):
                    if b_ in owner and owner[b_] != a:
                        other = owner[b_]
                        ra, ro = rank(a, cur[a].seeds), rank(other, cur[other].seeds)
                        if ra < ro or (ra == ro and ra < 2 and a > other):
                            newfrag.add(a)
                        elif ro < ra or (ra == ro and ro < 2):
                            newfrag.add(other)
                    else:
                        owner[b_] = a
        newfrag -= FRAGMENT
        print(f"overlap pass {it}: funcs={len(cur)} new fragments={len(newfrag)}", file=sys.stderr)
        funcs = cur
        if not newfrag:
            break
        FRAGMENT.update(newfrag)
        STRONG.difference_update(newfrag)
        SPAN[:] = sorted(STRONG)
    return o, funcs
