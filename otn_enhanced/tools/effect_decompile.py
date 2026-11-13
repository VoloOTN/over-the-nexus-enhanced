"""Lift a Thumb card-effect handler from overlay0003 into pseudo-Python.

The output is *not* runnable — it is a structured, readable representation
intended as a decompilation aid.  Each ARMv4T register becomes a local
variable (``r0`` … ``r7``), engine subroutines become calls into a stub
``engine`` module, and accesses through the card-context register become
attribute reads on a ``ctx`` parameter.

Control flow is recovered as follows:

* Forward conditional branches over a single fall-through block become an
  ``if cond: ...`` with the branch target reached after the block.
* Branch targets that are not handled by the simple ``if`` recogniser are
  emitted as Python labels (comments ``# L_xxxxxx:``) with explicit
  ``goto`` comments — readable but not runnable.
* Unconditional branches inside the function become ``# goto L_xxxxxx``.
* ``POP {…, PC}`` and ``BX LR`` become ``return rN``.

The lifter is best-effort.  Complex flow (irreducible loops, computed
branches, jump tables) is preserved in label form rather than synthesised.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from otn_enhanced.asm.thumb_disasm import decode_thumb, ThumbInsn, pool_start_index
from otn_enhanced.tools.effect_extract import (
    RAM_BASE,
    HANDLER_TABLE_OFFSET,
    HANDLER_ENTRY_SIZE,
    HANDLER_ENTRY_COUNT,
    HANDLER_SLOT_NAMES,
    KNOWN_SUBROUTINES,
    CARD_CONTEXT_FIELDS,
    detect_function_size,
)
from otn_enhanced.tools.effect_structurer import Block, Structurer, build_blocks, COND_TO_PY
from otn_enhanced.rom.konami_id_to_card_name import KONAMI_ID_TO_CARD_NAME


# ---------------------------------------------------------------------------
# Branch-condition → Python expression
# ---------------------------------------------------------------------------

# We track CMP / TST / ALU operations to record the last comparison so the
# branch condition can be turned into a meaningful Python expression.
COND_TO_PY_EQ = {
    "BEQ": "{a} == {b}",
    "BNE": "{a} != {b}",
    "BCS": "uge({a}, {b})",   # unsigned >=
    "BCC": "ult({a}, {b})",   # unsigned <
    "BMI": "{a} < 0",
    "BPL": "{a} >= 0",
    "BVS": "overflow()",
    "BVC": "not overflow()",
    "BHI": "ugt({a}, {b})",
    "BLS": "ule({a}, {b})",
    "BGE": "{a} >= {b}",
    "BLT": "{a} < {b}",
    "BGT": "{a} > {b}",
    "BLE": "{a} <= {b}",
}

# Condition when branch is *not* taken (used to invert for if/else)
COND_INVERT = {
    "BEQ": "BNE", "BNE": "BEQ",
    "BCS": "BCC", "BCC": "BCS",
    "BMI": "BPL", "BPL": "BMI",
    "BVS": "BVC", "BVC": "BVS",
    "BHI": "BLS", "BLS": "BHI",
    "BGE": "BLT", "BLT": "BGE",
    "BGT": "BLE", "BLE": "BGT",
}


# ---------------------------------------------------------------------------
# Helpers for translating registers / immediates
# ---------------------------------------------------------------------------

def _reg_var(reg: str) -> str:
    """Map ``R0``…``R7``/``SP``/``LR``/``PC`` to a Python identifier."""
    reg = reg.strip().upper()
    if reg.startswith("R"):
        return reg.lower()
    return {"SP": "_sp", "LR": "_lr", "PC": "_pc"}.get(reg, reg.lower())


def _fmt_imm(s: str) -> str:
    s = s.strip().lstrip("#")
    try:
        n = int(s, 16) if s.lower().startswith("0x") else int(s)
    except ValueError:
        return s
    return hex(n) if n >= 16 else str(n)


def _split_ops(ops: str) -> list[str]:
    return [p.strip() for p in ops.split(",") if p.strip()]


def _resolve_pool(insn: ThumbInsn, overlay: bytes) -> str:
    """Render a literal-pool value as a Python expression."""
    val = insn.pool_value
    if val in KONAMI_ID_TO_CARD_NAME:
        name = KONAMI_ID_TO_CARD_NAME[val].replace('"', '\\"')
        return f'CARD(0x{val:04X})  # {name}'
    if (val & 1) and RAM_BASE <= (val & ~1) < RAM_BASE + len(overlay):
        foff = (val & ~1) - RAM_BASE
        name = KNOWN_SUBROUTINES.get(foff)
        if name:
            return f"engine.{name}"
        return f"func_{foff:06x}"
    if 0x02000000 <= val < 0x02400000:
        return f"RAM(0x{val:08X})"
    return f"0x{val:08X}"


# ---------------------------------------------------------------------------
# Lift a single function
# ---------------------------------------------------------------------------

@dataclass
class LiftedLine:
    addr: int
    text: str
    is_label: bool = False
    indent: int = 0


def _detect_ctx_register(insns: list[ThumbInsn]) -> str | None:
    """Detect which register stores the card-context pointer (mirrors the
    extractor's heuristic)."""
    for insn in insns[:6]:
        if insn.mnemonic == "ADD":
            parts = _split_ops(insn.operands)
            if len(parts) == 3 and parts[1] == "R0" and parts[2] == "#0x0":
                return parts[0]
        if insn.mnemonic == "MOV":
            parts = _split_ops(insn.operands)
            if len(parts) == 2 and parts[1] == "R0":
                return parts[0]
    return None


def _ctx_field_name(offset: int, access: str) -> str | None:
    """Map (offset, access) → ctx field name from CARD_CONTEXT_FIELDS."""
    desc = CARD_CONTEXT_FIELDS.get((offset, access))
    if not desc:
        return None
    # turn the description into a pythonic attribute name
    name = (desc
            .replace("this card's ", "this_")
            .replace(" / ", "_")
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_"))
    return name


def lift_function(
    overlay: bytes,
    func_addr: int,
    func_name: str,
    *,
    max_size: int = 4096,
) -> str:
    """Lift one Thumb function to a Python source string with structured
    control flow (if/elif/else/while)."""
    file_off = func_addr - RAM_BASE
    func_size = detect_function_size(overlay, file_off, max_size=max_size)
    func_data = overlay[file_off:file_off + func_size]
    insns = decode_thumb(func_data, func_addr,
                         overlay_data=overlay, ram_base=RAM_BASE)

    # Pool boundary: instructions past this index are literal data.
    pool_start = pool_start_index(insns)

    code_insns = insns[:pool_start]
    if not code_insns:
        return f"def {func_name}(ctx, r0=None, r1=None, r2=None, r3=None):\n    pass\n"

    ctx_reg = _detect_ctx_register(code_insns)

    # ----------------------------------------------------------
    # Build basic blocks and propagate the most-recent CMP/TST
    # state into each block's terminator so branch conditions can
    # be rendered as real Python expressions.
    # ----------------------------------------------------------
    blocks = build_blocks(code_insns)
    _annotate_block_conditions(blocks)

    # ----------------------------------------------------------
    # Per-block renderer: emit the non-terminator instructions
    # ----------------------------------------------------------
    def render_block(blk: Block) -> list[str]:
        body: list[str] = []
        # Skip the terminator if it's a branch we'll express via control flow
        last = blk.insns[-1] if blk.insns else None
        skip_last = bool(last and (last.is_branch and not last.is_return)
                         and last.mnemonic != "BL" and last.mnemonic != "BLX")
        for ins in blk.insns[:-1] if skip_last else blk.insns:
            # POP {…, PC} is a return: the structurer emits `return r0`,
            # so don't render it twice.
            if ins.is_return:
                continue
            line = _lift_one(ins, ctx_reg, overlay, None)
            if line:
                body.append(line)
        return body

    structurer = Structurer(blocks, render_block)
    body_lines = structurer.emit()

    # ----------------------------------------------------------
    # Assemble final Python source
    # ----------------------------------------------------------
    out: list[str] = []
    out.append(f"def {func_name}(ctx, r0=None, r1=None, r2=None, r3=None):")
    out.append(f'    """Lifted from ov+0x{file_off:06X} (RAM 0x{func_addr:08X}), '
               f'{func_size} bytes."""')
    out.append("    r4 = r5 = r6 = r7 = None")
    if ctx_reg and ctx_reg != "R0":
        out.append(f"    {ctx_reg.lower()} = ctx  # card context "
                   f"(detected via {ctx_reg} = R0)")
    out.append("")
    if body_lines:
        out.extend(body_lines)
    else:
        out.append("    pass")

    if pool_start < len(insns):
        out.append("")
        out.append("    # ---- literal pool ----")
        for ins in insns[pool_start:]:
            if ins.addr % 4 == 0 and ins.addr - RAM_BASE + 4 <= len(overlay):
                val = struct.unpack_from(
                    "<I", overlay, ins.addr - RAM_BASE)[0]
                tag = ""
                if val in KONAMI_ID_TO_CARD_NAME:
                    tag = f"  # card: {KONAMI_ID_TO_CARD_NAME[val]}"
                elif (val & 1) and RAM_BASE <= (val & ~1) < RAM_BASE + len(overlay):
                    foff = (val & ~1) - RAM_BASE
                    nm = KNOWN_SUBROUTINES.get(foff, f"func_{foff:06x}")
                    tag = f"  # -> {nm}"
                out.append(f"    # @0x{ins.addr:08X}: 0x{val:08X}{tag}")

    return "\n".join(out)


def _annotate_block_conditions(blocks: list[Block]) -> None:
    """For each block whose terminator is a conditional branch, walk back
    through prior instructions to find the most recent CMP/TST/SUB-imm and
    record the comparison's left/right operands as Python expressions."""
    for blk in blocks:
        if not blk.cond_mn or blk.cond_mn == "B":
            continue
        lhs, rhs = "?", "0"
        # Search back through the block (and prior blocks if needed) for the
        # most recent flag-setting instruction.
        found = False
        for ins in reversed(blk.insns[:-1]):
            mn = ins.mnemonic
            parts = [p.strip() for p in ins.operands.split(",") if p.strip()]
            if mn == "CMP" and len(parts) == 2:
                lhs = _reg_var(parts[0])
                rhs = (_fmt_imm(parts[1]) if parts[1].startswith("#")
                       else _reg_var(parts[1]))
                found = True
                break
            if mn == "TST" and len(parts) == 2:
                lhs = f"({_reg_var(parts[0])} & {_reg_var(parts[1])})"
                rhs = "0"
                found = True
                break
            if mn == "SUB" and len(parts) == 3 and parts[2].startswith("#"):
                lhs = _reg_var(parts[1])
                rhs = _fmt_imm(parts[2])
                found = True
                break
            # Most ALU ops on the same flags would clobber, but we accept the
            # last MOV/ADD/SUB result against zero as a fallback.
            if mn in ("MOV", "ADD", "SUB", "AND", "ORR", "EOR", "MUL",
                      "LSL", "LSR", "ASR") and parts:
                lhs = _reg_var(parts[0])
                rhs = "0"
                found = True
                break
        if not found:
            # No flag-setting insn in this block; common after a BL where the
            # call's return value (in r0) is then tested.
            lhs, rhs = "r0", "0"
        blk.cmp_lhs = lhs
        blk.cmp_rhs = rhs


# ---------------------------------------------------------------------------
# Per-instruction lift
# ---------------------------------------------------------------------------

def _lift_one(insn: ThumbInsn, ctx_reg: str | None, overlay: bytes,
              last_cmp: tuple[str, str] | None) -> str:
    """Render one ThumbInsn as a Python statement (or comment)."""
    mn = insn.mnemonic
    ops = insn.operands
    parts = _split_ops(ops)

    # ----- prologue / epilogue noise -----
    if mn == "PUSH":
        return f"# PUSH {ops}"
    if mn == "POP":
        if "PC" in ops:
            return "return r0"
        return f"# POP {ops}"
    if mn == "BX" and ops.strip().upper() == "LR":
        return "return r0"

    # ----- function calls -----
    if mn == "BL":
        target = insn.branch_target
        if target:
            foff = target - RAM_BASE
            name = KNOWN_SUBROUTINES.get(foff)
            if name:
                callee = f"engine.{name}"
                tag = f"ov+0x{foff:06X}"
            elif 0 <= foff < len(overlay):
                callee = f"func_{foff:06x}"
                tag = f"ov+0x{foff:06X}"
            else:
                # Branch into ARM9 main, not the overlay
                callee = f"arm9_func_0x{target:08X}"
                tag = f"arm9 0x{target:08X}"
        else:
            callee = "??"
            tag = "?"
        return f"r0 = {callee}(r0, r1, r2, r3)  # BL {tag}"

    if mn == "BLX":
        if insn.branch_target:
            return (f"r0 = arm_func_0x{insn.branch_target:08X}(r0, r1, r2, r3)"
                    f"  # BLX")
        return f"r0 = call({_reg_var(ops)})(r0, r1, r2, r3)  # BLX via reg"

    # ----- branches -----
    if mn.startswith("B") and insn.is_branch and mn != "BX" and mn != "BL" \
            and mn != "BLX":
        target = insn.branch_target
        label = f"L_{target & 0xFFFFFF:06X}"
        if mn == "B":
            return f"# goto {label}"
        # Conditional
        if last_cmp:
            tmpl = COND_TO_PY_EQ.get(mn, "{a} ?? {b}")
            cond = tmpl.format(a=last_cmp[0], b=last_cmp[1])
        else:
            cond = f"flag_{mn[1:].lower()}()"
        return f"if {cond}: goto({label!r})  # {mn}"

    if mn == "BX":
        return f"# BX {ops}"

    # ----- literal pool load -----
    if mn == "LDR" and insn.is_pool_ref:
        rd = _reg_var(parts[0])
        return f"{rd} = {_resolve_pool(insn, overlay)}"

    # ----- context-struct access -----
    if ctx_reg and mn in ("LDR", "LDRH", "LDRB", "LDSB", "LDSH",
                          "STR", "STRH", "STRB"):
        # Operands look like:  R0, [R4, #0x4]
        clean = [p.strip() for p in ops.replace("[", ",").replace("]", "").split(",")
                 if p.strip()]
        if len(clean) >= 2 and clean[1] == ctx_reg:
            access = ("W" if mn in ("LDR", "STR")
                      else "H" if mn in ("LDRH", "STRH", "LDSH") else "B")
            is_load = mn.startswith("LDR") or mn.startswith("LDS")
            rd = _reg_var(clean[0])
            imm = 0
            if len(clean) == 3 and clean[2].startswith("#"):
                imm = int(clean[2].lstrip("#"), 16) if clean[2].lower().startswith("#0x") \
                    else int(clean[2].lstrip("#"))
            field = _ctx_field_name(imm, access)
            ctx_lhs = "ctx" if ctx_reg == "R0" else _reg_var(ctx_reg)
            if field:
                return f"{rd} = {ctx_lhs}.{field}" if is_load \
                    else f"{ctx_lhs}.{field} = {rd}"
            sz = {"W": "u32", "H": "u16", "B": "u8"}[access]
            return (f"{rd} = read_{sz}({ctx_lhs} + 0x{imm:X})" if is_load
                    else f"write_{sz}({ctx_lhs} + 0x{imm:X}, {rd})")

    # ----- generic loads / stores -----
    if mn in ("LDR", "LDRH", "LDRB", "LDSB", "LDSH",
              "STR", "STRH", "STRB"):
        clean = [p.strip() for p in ops.replace("[", ",").replace("]", "").split(",")
                 if p.strip()]
        if len(clean) >= 2:
            rd = _reg_var(clean[0])
            base = _reg_var(clean[1])
            offs = ""
            if len(clean) == 3:
                offs = (" + " + (_fmt_imm(clean[2]) if clean[2].startswith("#")
                                 else _reg_var(clean[2])))
            sz = {"LDR": "u32", "LDRH": "u16", "LDRB": "u8",
                  "LDSB": "i8", "LDSH": "i16",
                  "STR": "u32", "STRH": "u16", "STRB": "u8"}[mn]
            if mn.startswith("LD"):
                return f"{rd} = read_{sz}({base}{offs})"
            return f"write_{sz}({base}{offs}, {rd})"

    # ----- arithmetic / logic -----
    if mn == "MOV" and len(parts) == 2:
        dst = _reg_var(parts[0])
        src = parts[1]
        if src.startswith("#"):
            n = _fmt_imm(src)
            try:
                ni = int(n, 16) if n.startswith("0x") else int(n)
                if ni in KONAMI_ID_TO_CARD_NAME:
                    return (f"{dst} = {n}  # card: "
                            f"{KONAMI_ID_TO_CARD_NAME[ni]}")
            except ValueError:
                pass
            return f"{dst} = {n}"
        return f"{dst} = {_reg_var(src)}"

    if mn == "CMP" and len(parts) == 2:
        a = _reg_var(parts[0])
        b = (_fmt_imm(parts[1]) if parts[1].startswith("#")
             else _reg_var(parts[1]))
        return f"# CMP {a}, {b}"

    if mn == "TST" and len(parts) == 2:
        a = _reg_var(parts[0])
        b = _reg_var(parts[1])
        return f"# TST {a}, {b}"

    if mn == "ADD" and len(parts) == 3:
        dst, src, val = parts
        if val == "#0x0":
            # register copy idiom
            return f"{_reg_var(dst)} = {_reg_var(src)}"
        v = _fmt_imm(val) if val.startswith("#") else _reg_var(val)
        return f"{_reg_var(dst)} = {_reg_var(src)} + {v}"
    if mn == "ADD" and len(parts) == 2:
        dst, val = parts
        v = _fmt_imm(val) if val.startswith("#") else _reg_var(val)
        return f"{_reg_var(dst)} += {v}"

    if mn == "SUB" and len(parts) == 3:
        dst, src, val = parts
        v = _fmt_imm(val) if val.startswith("#") else _reg_var(val)
        return f"{_reg_var(dst)} = {_reg_var(src)} - {v}"
    if mn == "SUB" and len(parts) == 2:
        dst, val = parts
        v = _fmt_imm(val) if val.startswith("#") else _reg_var(val)
        return f"{_reg_var(dst)} -= {v}"

    if mn in ("LSL", "LSR", "ASR") and len(parts) == 3:
        sym = {"LSL": "<<", "LSR": ">>", "ASR": ">>"}[mn]
        return (f"{_reg_var(parts[0])} = {_reg_var(parts[1])} {sym} "
                f"{_fmt_imm(parts[2])}")
    if mn in ("LSL", "LSR", "ASR") and len(parts) == 2:
        sym = {"LSL": "<<=", "LSR": ">>=", "ASR": ">>="}[mn]
        return f"{_reg_var(parts[0])} {sym} {_fmt_imm(parts[1])}"

    if mn in ("AND", "ORR", "EOR", "BIC") and len(parts) == 2:
        dst, src = _reg_var(parts[0]), _reg_var(parts[1])
        sym = {"AND": "&=", "ORR": "|=", "EOR": "^=", "BIC": "&= ~"}[mn]
        if mn == "BIC":
            return f"{dst} &= ~{src}"
        return f"{dst} {sym} {src}"

    if mn == "MVN" and len(parts) == 2:
        return f"{_reg_var(parts[0])} = ~{_reg_var(parts[1])}"
    if mn == "NEG" and len(parts) == 2:
        return f"{_reg_var(parts[0])} = -{_reg_var(parts[1])}"
    if mn == "MUL" and len(parts) == 2:
        return f"{_reg_var(parts[0])} *= {_reg_var(parts[1])}"

    if mn == "NOP":
        return "pass  # NOP"
    if mn == "SWI":
        return f"swi({_fmt_imm(ops)})"

    if mn == "LDMIA":
        return f"# LDMIA {ops}"
    if mn == "STMIA":
        return f"# STMIA {ops}"

    # Unknown halfwords
    if mn == ".hword":
        return f"# .hword {ops}"

    return f"# {mn} {ops}"


# ---------------------------------------------------------------------------
# Iterate the master handler table
# ---------------------------------------------------------------------------

def iter_handler_entries(overlay: bytes) -> Iterable[dict]:
    for idx in range(HANDLER_ENTRY_COUNT):
        off = HANDLER_TABLE_OFFSET + idx * HANDLER_ENTRY_SIZE
        ptrs = struct.unpack_from("<5I", overlay, off)
        cid = struct.unpack_from("<I", overlay, off + 20)[0]
        if cid == 0 and all(p == 0 for p in ptrs):
            continue
        entry = {"index": idx, "card_id": cid}
        for si, name in enumerate(HANDLER_SLOT_NAMES):
            entry[name] = ptrs[si]
        yield entry


# ---------------------------------------------------------------------------
# Lift one entry → full module text
# ---------------------------------------------------------------------------

def lift_card_module(overlay: bytes, entry: dict) -> str:
    cid = entry["card_id"]
    name = KONAMI_ID_TO_CARD_NAME.get(cid, f"Unknown_{cid:04X}")
    safe_name = "".join(c if c.isalnum() else "_" for c in name)

    out: list[str] = []
    out.append('"""')
    out.append(f"Card effect (decompiled from overlay0003)")
    out.append("")
    out.append(f"  Card name : {name}")
    out.append(f"  Konami ID : 0x{cid:04X} ({cid})")
    out.append(f"  Table idx : {entry['index']}")
    out.append('"""')
    out.append("from .._engine import engine, CARD, RAM, ult, ule, ugt, uge, "
               "read_u8, read_u16, read_u32, read_i8, read_i16, "
               "write_u8, write_u16, write_u32, swi, goto, overflow")
    out.append("")
    out.append(f"KONAMI_ID = 0x{cid:04X}")
    out.append(f"CARD_NAME = {name!r}")
    out.append("")

    seen: dict[int, str] = {}
    any_emitted = False
    for slot in HANDLER_SLOT_NAMES:
        ptr = entry[slot]
        if not ptr:
            out.append(f"# {slot}: NULL")
            continue
        addr = ptr & ~1
        if addr in seen:
            out.append(f"# {slot}: same as {seen[addr]} (RAM 0x{addr:08X})")
            out.append(f"{slot} = {seen[addr]}")
            out.append("")
            continue
        seen[addr] = slot
        try:
            body = lift_function(overlay, addr, slot)
        except Exception as exc:  # noqa: BLE001
            out.append(f"# {slot}: lift failed: {exc!r}")
            continue
        out.append(body)
        out.append("")
        any_emitted = True

    if not any_emitted:
        out.append("# (no non-null slots — all handlers are NULL)")

    return "\n".join(out) + "\n"
