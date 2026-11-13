"""A tiny label-resolving Thumb-1 assembler for injected stubs.

WHY THIS EXISTS: hand-encoding stubs as raw halfword lists produced SIX distinct
bugs in one session (a wrong `LDR Rn,[Rm,#imm]` offset, two mis-indexed literal-pool
slots, an inverted BEQ/BNE, a wrong `LDRB` offset, and a stale branch distance).
Every one assembled cleanly and passed ``effect_verify.assert_thumb1_only`` -- that
check rejects Thumb-2, it does NOT check that the code means what you intended.
Branch distances and pool indices are exactly the things a human recomputes wrongly
after every edit, so they belong to a tool.

Supports only what injected stubs need, and REFUSES anything it does not know rather
than emitting something plausible.  Thumb-1 only by construction (no wide encodings
exist in the table), but callers should still run ``assert_thumb1_only`` and
disassemble the result -- this tool removes a bug class, it does not remove the rule.

    from otn_enhanced.asm.thumb_asm import asm
    blob = asm(0x0239C014, '''
        push    {r4,r5,r6,lr}
        adds    r4, r0, #0
        ldr     r5, =0x0229AAFC
        ldr     r5, [r5, #0x70]
        cmp     r5, #0x7e
        bne     native
        ...
      native:
        blx     r3
        pop     {r4,r5,r6,pc}
    ''')

`ldr rD, =VALUE` allocates (and de-duplicates) a word in a 4-aligned pool placed
after the code.  Labels are `name:` on their own line or leading a line.
"""
from __future__ import annotations

import re
import struct

_REG = {f"r{i}": i for i in range(8)}
_REG.update({"sp": 13, "lr": 14, "pc": 15})


class AsmError(Exception):
    pass


def _reg(tok: str) -> int:
    t = tok.strip().lower()
    if t not in _REG:
        raise AsmError(f"not a register: {tok!r}")
    return _REG[t]


def _imm(tok: str) -> int:
    t = tok.strip()
    if not t.startswith("#"):
        raise AsmError(f"not an immediate: {tok!r}")
    return int(t[1:], 0)


def _reglist(tok: str) -> list[int]:
    inner = tok.strip()
    if not (inner.startswith("{") and inner.endswith("}")):
        raise AsmError(f"not a register list: {tok!r}")
    return [_reg(p) for p in inner[1:-1].split(",") if p.strip()]


def labels_of(base: int, source: str) -> dict[str, int]:
    """Absolute address of every label in *source* assembled at *base* (no encoding)."""
    _, labels, _ = _parse(source)
    return {k: base + 2 * v for k, v in labels.items()}


def asm(base: int, source: str, symbols: dict[str, int] | None = None) -> bytes:
    """Assemble *source* for load address *base*; returns code + literal pool.

    *symbols* resolves branch targets that are not local labels (absolute addresses, e.g. the
    labels of another fragment -- ov3_compaction.cave3.asm_split). ``bl TARGET`` is the
    two-halfword ARMv4T BL; used as a far branch it CLOBBERS LR, so only after LR is saved."""
    # An ODD-halfword base is legal: the pool offset is rounded up from the real
    # address, so a 2-mod-4 base simply costs no padding. Some ov3 dead blocks only
    # fit if you start 2 bytes in (0x021B57EE), so do not force 4-alignment here.
    if base % 2:
        raise AsmError(f"base {base:#x} must be halfword-aligned")
    items, labels, pool = _parse(source)

    def target(t: str) -> int:
        if t in labels:
            return base + 2 * labels[t]
        if symbols and t in symbols:
            return symbols[t]
        if re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+", t):   # absolute address (`bl 0x021D12F4`)
            return int(t, 0)
        raise AsmError(f"undefined label {t!r}")

    return _encode(base, items, pool, target)


def _parse(source: str) -> tuple[list[tuple], dict[str, int], list[int]]:
    # ---- pass 1: parse into items, collecting labels and pool entries ---------
    items: list[tuple] = []          # (kind, ...) one per emitted halfword-producer
    labels: dict[str, int] = {}
    pool: list[int] = []

    for raw in source.splitlines():
        line = raw.split(";")[0].split("//")[0].strip()
        while line:
            m = re.match(r"^([A-Za-z_]\w*):\s*", line)
            if not m:
                break
            labels[m.group(1)] = len(items)
            line = line[m.end():].strip()
        if not line:
            continue
        mnem, _, rest = line.partition(" ")
        mnem = mnem.lower()
        # register lists and memory operands contain commas -- keep them whole
        if mnem in ("push", "pop") or rest.strip().startswith("{"):
            ops = [rest.strip()]
        else:
            ops = [o.strip() for o in rest.split(",")] if rest.strip() else []

        # `ldr rD, =VALUE`  /  `ldr rD, [rN, #imm]`
        if mnem == "ldr" and len(ops) >= 2 and ops[1].startswith("="):
            val = int(ops[1][1:], 0)
            if val not in pool:
                pool.append(val)
            items.append(("ldrlit", _reg(ops[0]), pool.index(val)))
            continue
        if mnem in ("b", "beq", "bne", "bgt", "blt", "bge", "ble", "bmi", "bpl") and len(ops) == 1:
            items.append(("branch", mnem, ops[0]))
            continue
        if mnem == "bl" and len(ops) == 1:      # two halfwords, both encoded from the first's address
            items.append(("bl", 0, ops[0]))
            items.append(("bl", 1, ops[0]))
            continue
        items.append(("plain", mnem, ops))
    return items, labels, pool


def _encode(base: int, items: list[tuple], pool: list[int], target) -> bytes:
    # ---- pass 2: encode ------------------------------------------------------
    code_hw = len(items)
    pool_off = base + code_hw * 2
    pool_off += (4 - pool_off % 4) % 4
    pad = (pool_off - (base + code_hw * 2)) // 2

    out: list[int] = []
    for idx, it in enumerate(items):
        if it[0] == "ldrlit":
            _, rd, li = it
            addr = base + idx * 2
            off = (pool_off + li * 4) - ((addr + 4) & ~3)
            if not (0 <= off <= 0x3FC and off % 4 == 0):
                raise AsmError(f"literal out of range at {addr:#x}: {off}")
            out.append(0x4800 | (rd << 8) | (off // 4))
            continue
        if it[0] == "bl":
            _, half, t = it
            addr = base + (idx - half) * 2
            off = target(t) - (addr + 4)
            if off % 2 or not (-(1 << 22) <= off < (1 << 22)):
                raise AsmError(f"BL out of range at {addr:#x}: {off:#x}")
            out.append(0xF000 | ((off >> 12) & 0x7FF) if half == 0 else 0xF800 | ((off >> 1) & 0x7FF))
            continue
        if it[0] == "branch":
            _, mnem, t = it
            delta, odd = divmod(target(t) - (base + idx * 2 + 4), 2)
            if odd:
                raise AsmError(f"odd branch target {t!r}")
            if mnem == "b":
                if not (-1024 <= delta <= 1023):
                    raise AsmError(f"B out of range: {delta}")
                out.append(0xE000 | (delta & 0x7FF))
            else:
                cond = {"beq": 0, "bne": 1, "bmi": 4, "bpl": 5, "bge": 10, "blt": 11,
                        "bgt": 12, "ble": 13}[mnem]
                if not (-128 <= delta <= 127):
                    raise AsmError(f"{mnem} out of range: {delta}")
                out.append(0xD000 | (cond << 8) | (delta & 0xFF))
            continue

        _, mnem, ops = it
        if mnem == "push":
            rs = _reglist(ops[0])
            out.append(0xB400 | (0x100 if 14 in rs else 0)
                       | sum(1 << r for r in rs if r < 8))
        elif mnem == "pop":
            rs = _reglist(ops[0])
            out.append(0xBC00 | (0x100 if 15 in rs else 0)
                       | sum(1 << r for r in rs if r < 8))
        elif mnem == "movs" and ops[1].startswith("#"):
            out.append(0x2000 | (_reg(ops[0]) << 8) | (_imm(ops[1]) & 0xFF))
        elif mnem in ("add", "sub") and ops[0] == "sp" and len(ops) == 2:
            v = _imm(ops[1])                     # ADD/SUB SP, #imm7*4
            if v % 4 or v > 0x1FC:
                raise AsmError(f"{mnem} sp imm {v:#x} must be a multiple of 4 <= 0x1FC")
            out.append((0xB000 if mnem == "add" else 0xB080) | (v >> 2))
        elif mnem == "add" and len(ops) == 3 and ops[1] == "sp":
            v = _imm(ops[2])                     # ADD Rd, SP, #imm8*4
            if v % 4 or v > 0x3FC:
                raise AsmError(f"add rd, sp imm {v:#x} must be a multiple of 4 <= 0x3FC")
            out.append(0xA800 | (_reg(ops[0]) << 8) | (v >> 2))
        elif mnem in ("adds", "subs"):
            base_op = 0x1800 if mnem == "adds" else 0x1A00
            if len(ops) == 3 and ops[2].startswith("#"):
                v = _imm(ops[2])
                if v > 7:
                    raise AsmError(
                        f"3-operand {mnem} imm must be <= 7 (thumb.add_sub_imm3); "
                        f"use the 2-operand form for {v:#x}")
                out.append((0x1C00 if mnem == "adds" else 0x1E00)
                           | (v << 6) | (_reg(ops[1]) << 3) | _reg(ops[0]))
            elif len(ops) == 3:
                out.append(base_op | (_reg(ops[2]) << 6)
                           | (_reg(ops[1]) << 3) | _reg(ops[0]))
            elif len(ops) == 2 and ops[1].startswith("#"):
                out.append((0x3000 if mnem == "adds" else 0x3800)
                           | (_reg(ops[0]) << 8) | (_imm(ops[1]) & 0xFF))
            else:
                raise AsmError(f"unsupported {mnem} {ops}")
        elif mnem == "cmp":
            if ops[1].startswith("#"):
                out.append(0x2800 | (_reg(ops[0]) << 8) | (_imm(ops[1]) & 0xFF))
            else:
                out.append(0x4280 | (_reg(ops[1]) << 3) | _reg(ops[0]))
        elif mnem == "eors":
            out.append(0x4040 | (_reg(ops[1]) << 3) | _reg(ops[0]))
        elif mnem == "muls":                    # MULS Rd, Rm (Rd = Rd * Rm)
            out.append(0x4340 | (_reg(ops[1]) << 3) | _reg(ops[0]))
        elif mnem == "orrs":
            out.append(0x4300 | (_reg(ops[1]) << 3) | _reg(ops[0]))
        elif mnem == "ands":
            out.append(0x4000 | (_reg(ops[1]) << 3) | _reg(ops[0]))
        elif mnem in ("lsls", "lsrs", "asrs") and len(ops) == 2:
            # shift-by-register (ALU) family: Rd = Rd <<>> Rs
            out.append({"lsls": 0x4080, "lsrs": 0x40C0, "asrs": 0x4100}[mnem]
                       | (_reg(ops[1]) << 3) | _reg(ops[0]))
        elif mnem in ("lsls", "lsrs", "asrs"):
            # shift-by-immediate family: LSL 0x0000, LSR 0x0800, ASR 0x1000
            out.append({"lsls": 0x0000, "lsrs": 0x0800, "asrs": 0x1000}[mnem]
                       | ((_imm(ops[2]) & 0x1F) << 6) | (_reg(ops[1]) << 3)
                       | _reg(ops[0]))
        elif mnem in ("ldr", "ldrh", "ldrb", "str", "strh", "strb"):
            m = re.match(r"\[\s*(\w+)\s*(?:,\s*(.+?))?\s*\]", ", ".join(ops[1:]).strip())
            if not m:
                raise AsmError(f"bad memory operand: {ops}")
            rn, disp = m.group(1), (m.group(2) or "#0").strip()
            rt = _reg(ops[0])
            if not disp.startswith("#"):        # register offset form
                base_op = {"strh": 0x5200, "ldrh": 0x5A00,
                           "str": 0x5000, "ldr": 0x5800,
                           "strb": 0x5400, "ldrb": 0x5C00}[mnem]
                out.append(base_op | (_reg(disp) << 6) | (_reg(rn) << 3) | rt)
            elif _reg(rn) == 13:                # SP-relative
                op = {"ldr": 0x9800, "str": 0x9000}[mnem]
                out.append(op | (rt << 8) | ((_imm(disp) // 4) & 0xFF))
            else:
                shift, opbase = {"ldr": (2, 0x6800), "str": (2, 0x6000),
                                 "ldrh": (1, 0x8800), "strh": (1, 0x8000),
                                 "ldrb": (0, 0x7800), "strb": (0, 0x7000)}[mnem]
                v = _imm(disp) >> shift
                if v > 0x1F:
                    raise AsmError(f"{mnem} offset {disp} too large")
                out.append(opbase | (v << 6) | (_reg(rn) << 3) | rt)
        elif mnem == "blx":
            out.append(0x4780 | (_reg(ops[0]) << 3))
        elif mnem == "bx":
            out.append(0x4700 | (_reg(ops[0]) << 3))
        elif mnem == "nop":
            out.append(0x46C0)
        else:
            raise AsmError(f"unsupported instruction: {mnem} {ops}")

    out.extend([0x46C0] * pad)
    return struct.pack(f"<{len(out)}H", *out) + struct.pack(f"<{len(pool)}I", *pool)
