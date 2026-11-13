"""Minimal ARMv4T Thumb disassembler / assembler for NDS overlay hacking.

Covers the subset of Thumb instructions found in Yu-Gi-Oh! NDS overlay0003
card-effect handlers.  Not a full-coverage disassembler — just enough for
the short handler stubs and shared routines used by the game engine.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Condition codes
# ---------------------------------------------------------------------------
COND_NAMES = [
    "EQ", "NE", "CS", "CC", "MI", "PL", "VS", "VC",
    "HI", "LS", "GE", "LT", "GT", "LE",
]

# ---------------------------------------------------------------------------
# Register-list helpers
# ---------------------------------------------------------------------------

def _reglist(mask: int, extra: Optional[str] = None) -> str:
    """Format a bitmask of R0-R7 (+ optional LR/PC) as ``{R0, R1, ...}``."""
    regs = [f"R{i}" for i in range(8) if mask & (1 << i)]
    if extra:
        regs.append(extra)
    return "{" + ", ".join(regs) + "}"


# ---------------------------------------------------------------------------
# Dataclass for one decoded instruction
# ---------------------------------------------------------------------------

@dataclass
class ThumbInsn:
    """One decoded Thumb instruction (16-bit or 32-bit for BL/BLX)."""
    addr: int                 # RAM address of the instruction
    size: int                 # 2 or 4 bytes
    raw: bytes                # raw instruction bytes
    mnemonic: str             # e.g. "LDR", "PUSH", "BL"
    operands: str             # e.g. "R0, [R1, #0x4]"
    comment: str = ""         # annotation (pool value, branch target name, …)
    is_pool_ref: bool = False # True if this is a PC-relative LDR
    pool_addr: int = 0        # resolved literal-pool address
    pool_value: int = 0       # 32-bit value at pool address
    branch_target: int = 0    # resolved branch target (for B/BL/Bcc)
    is_branch: bool = False
    is_return: bool = False   # POP {…,PC} or BX LR

    @property
    def file_offset(self) -> int:
        """Overlay file offset (addr - ram_base), set externally."""
        return getattr(self, "_file_offset", 0)

    def asm_line(self, ram_base: int = 0) -> str:
        """Format as a single assembly line with address, hex, mnemonic, operands, comment."""
        foff = self.addr - ram_base if ram_base else self.addr
        hexstr = self.raw.hex().upper()
        left = f"    {self.mnemonic:<8s}{self.operands}"
        cmt = f"  ; {self.comment}" if self.comment else ""
        return f"    {hexstr:<12s}{left}{cmt}"


# ---------------------------------------------------------------------------
# Thumb decoder
# ---------------------------------------------------------------------------

def decode_thumb(data: bytes, base_addr: int, *, overlay_data: bytes | None = None,
                 ram_base: int = 0) -> list[ThumbInsn]:
    """Decode *data* as Thumb code starting at *base_addr*.

    If *overlay_data* and *ram_base* are provided, literal-pool references are
    resolved and annotated.
    """
    insns: list[ThumbInsn] = []
    i = 0
    length = len(data)

    while i < length:
        addr = base_addr + i
        hw = struct.unpack_from("<H", data, i)[0]

        # ---- 32-bit BL / BLX prefix check ----
        if (hw >> 11) == 0b11110 and i + 2 < length:
            hw2 = struct.unpack_from("<H", data, i + 2)[0]
            top5 = hw2 >> 11
            if top5 in (0b11111, 0b11101):
                # BL (11111) or BLX (11101)
                offset_hi = hw & 0x7FF
                offset_lo = hw2 & 0x7FF
                if offset_hi & 0x400:
                    offset_hi |= ~0x7FF  # sign-extend
                full_offset = (offset_hi << 12) | (offset_lo << 1)
                target = addr + 4 + full_offset
                mn = "BL" if top5 == 0b11111 else "BLX"
                raw4 = data[i:i + 4]
                insn = ThumbInsn(
                    addr=addr, size=4, raw=raw4, mnemonic=mn,
                    operands=f"0x{target:08X}",
                    branch_target=target, is_branch=True,
                )
                if overlay_data and ram_base:
                    toff = target - ram_base
                    if 0 <= toff < len(overlay_data):
                        insn.comment = f"ov+0x{toff:06X}"
                insns.append(insn)
                i += 4
                continue

        raw2 = data[i:i + 2]

        # ---- Shift by immediate (Format 1) ----
        if (hw >> 13) == 0b000:
            op = (hw >> 11) & 3
            imm5 = (hw >> 6) & 0x1F
            rs = (hw >> 3) & 7
            rd = hw & 7
            if op == 0:
                mn = "LSL" if imm5 else "MOV"
                ops = f"R{rd}, R{rs}, #{imm5}" if imm5 else f"R{rd}, R{rs}"
            elif op == 1:
                mn = "LSR"
                ops = f"R{rd}, R{rs}, #{imm5 if imm5 else 32}"
            elif op == 2:
                mn = "ASR"
                ops = f"R{rd}, R{rs}, #{imm5 if imm5 else 32}"
            else:
                # Format 2: ADD/SUB register/immediate
                mn, ops = _decode_format2(hw)
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- MOV/CMP/ADD/SUB immediate (Format 3) ----
        if (hw >> 13) == 0b001:
            op = (hw >> 11) & 3
            rd = (hw >> 8) & 7
            imm8 = hw & 0xFF
            mn = ["MOV", "CMP", "ADD", "SUB"][op]
            ops = f"R{rd}, #0x{imm8:X}"
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- ALU operations (Format 4) ----
        if (hw >> 10) == 0b010000:
            op = (hw >> 6) & 0xF
            rs = (hw >> 3) & 7
            rd = hw & 7
            alu_names = [
                "AND", "EOR", "LSL", "LSR", "ASR", "ADC", "SBC", "ROR",
                "TST", "NEG", "CMP", "CMN", "ORR", "MUL", "BIC", "MVN",
            ]
            mn = alu_names[op]
            ops = f"R{rd}, R{rs}"
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- Hi register operations / BX (Format 5) ----
        if (hw >> 10) == 0b010001:
            op = (hw >> 8) & 3
            h1 = (hw >> 7) & 1
            h2 = (hw >> 6) & 1
            rs = ((hw >> 3) & 7) | (h2 << 3)
            rd = (hw & 7) | (h1 << 3)
            rn_s = f"R{rs}" if rs < 13 else ("SP" if rs == 13 else ("LR" if rs == 14 else "PC"))
            rd_s = f"R{rd}" if rd < 13 else ("SP" if rd == 13 else ("LR" if rd == 14 else "PC"))
            if op == 0:
                mn, ops = "ADD", f"{rd_s}, {rn_s}"
            elif op == 1:
                mn, ops = "CMP", f"{rd_s}, {rn_s}"
            elif op == 2:
                mn, ops = "MOV", f"{rd_s}, {rn_s}"
                if rd_s == rn_s == "R8":
                    mn, ops = "NOP", ""
            else:
                mn = "BLX" if h1 else "BX"
                ops = rn_s
                is_ret = (rn_s == "LR")
                insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn,
                                       operands=ops, is_return=is_ret, is_branch=True,
                                       branch_target=0))
                i += 2
                continue
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- PC-relative load (Format 6) ----
        if (hw >> 11) == 0b01001:
            rd = (hw >> 8) & 7
            imm8 = hw & 0xFF
            offset = imm8 * 4
            pc_val = (addr + 4) & ~2
            pool_addr = pc_val + offset
            insn = ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic="LDR",
                             operands=f"R{rd}, [PC, #0x{offset:X}]",
                             is_pool_ref=True, pool_addr=pool_addr)
            # Resolve pool value (keep original [PC, #imm] encoding for round-trip)
            if overlay_data and ram_base:
                poff = pool_addr - ram_base
                if 0 <= poff + 4 <= len(overlay_data):
                    val = struct.unpack_from("<I", overlay_data, poff)[0]
                    insn.pool_value = val
                    insn.comment = f"=0x{val:08X} pool@0x{pool_addr:08X}"
            insns.append(insn)
            i += 2
            continue

        # ---- Load/Store register offset (Format 7) ----
        if (hw >> 12) == 0b0101 and not ((hw >> 9) & 1):
            op = (hw >> 10) & 3
            ro = (hw >> 6) & 7
            rb = (hw >> 3) & 7
            rd = hw & 7
            mn = ["STR", "STRB", "LDR", "LDRB"][op]
            ops = f"R{rd}, [R{rb}, R{ro}]"
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- Load/Store sign-extended byte/halfword (Format 8) ----
        if (hw >> 12) == 0b0101 and ((hw >> 9) & 1):
            op = (hw >> 10) & 3
            ro = (hw >> 6) & 7
            rb = (hw >> 3) & 7
            rd = hw & 7
            mn = ["STRH", "LDSB", "LDRH", "LDSH"][op]
            ops = f"R{rd}, [R{rb}, R{ro}]"
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- Load/Store word immediate offset (Format 9) ----
        if (hw >> 13) == 0b011:
            is_load = (hw >> 11) & 1
            is_byte = (hw >> 12) & 1
            imm5 = (hw >> 6) & 0x1F
            rb = (hw >> 3) & 7
            rd = hw & 7
            if is_byte:
                mn = "LDRB" if is_load else "STRB"
                offset = imm5
            else:
                mn = "LDR" if is_load else "STR"
                offset = imm5 * 4
            ops = f"R{rd}, [R{rb}, #0x{offset:X}]"
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- Load/Store halfword immediate offset (Format 10) ----
        if (hw >> 12) == 0b1000:
            is_load = (hw >> 11) & 1
            imm5 = (hw >> 6) & 0x1F
            rb = (hw >> 3) & 7
            rd = hw & 7
            offset = imm5 * 2
            mn = "LDRH" if is_load else "STRH"
            ops = f"R{rd}, [R{rb}, #0x{offset:X}]"
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- SP-relative load/store (Format 11) ----
        if (hw >> 12) == 0b1001:
            is_load = (hw >> 11) & 1
            rd = (hw >> 8) & 7
            imm8 = hw & 0xFF
            offset = imm8 * 4
            mn = "LDR" if is_load else "STR"
            ops = f"R{rd}, [SP, #0x{offset:X}]"
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- Load address (Format 12): ADD Rd, PC/SP, #imm ----
        if (hw >> 12) == 0b1010:
            is_sp = (hw >> 11) & 1
            rd = (hw >> 8) & 7
            imm8 = hw & 0xFF
            offset = imm8 * 4
            src = "SP" if is_sp else "PC"
            ops = f"R{rd}, {src}, #0x{offset:X}"
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic="ADD", operands=ops))
            i += 2
            continue

        # ---- Adjust SP (Format 13) ----
        if (hw >> 8) == 0b10110000:
            imm7 = hw & 0x7F
            offset = imm7 * 4
            sign = "-" if (hw >> 7) & 1 else ""
            ops = f"SP, #{sign}0x{offset:X}"
            mn = "SUB" if (hw >> 7) & 1 else "ADD"
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- PUSH (Format 14) ----
        if (hw >> 9) == 0b1011010:
            lr = (hw >> 8) & 1
            rlist = hw & 0xFF
            ops = _reglist(rlist, "LR" if lr else None)
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic="PUSH", operands=ops))
            i += 2
            continue

        # ---- POP (Format 14) ----
        if (hw >> 9) == 0b1011110:
            pc = (hw >> 8) & 1
            rlist = hw & 0xFF
            ops = _reglist(rlist, "PC" if pc else None)
            insn = ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic="POP", operands=ops,
                             is_return=bool(pc))
            insns.append(insn)
            i += 2
            continue

        # ---- STMIA / LDMIA (Format 15) ----
        if (hw >> 12) == 0b1100:
            is_load = (hw >> 11) & 1
            rb = (hw >> 8) & 7
            rlist = hw & 0xFF
            mn = "LDMIA" if is_load else "STMIA"
            ops = f"R{rb}!, {_reglist(rlist)}"
            insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn, operands=ops))
            i += 2
            continue

        # ---- Conditional branch (Format 16) ----
        if (hw >> 12) == 0b1101:
            cond = (hw >> 8) & 0xF
            if cond == 0xF:
                # SWI
                imm8 = hw & 0xFF
                insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic="SWI",
                                       operands=f"#0x{imm8:X}"))
                i += 2
                continue
            if cond == 0xE:
                # Undefined
                insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=".hword",
                                       operands=f"0x{hw:04X}", comment="undefined"))
                i += 2
                continue
            soff = hw & 0xFF
            if soff & 0x80:
                soff -= 256
            target = addr + 4 + soff * 2
            mn = f"B{COND_NAMES[cond]}"
            insn = ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=mn,
                             operands=f"0x{target:08X}", is_branch=True,
                             branch_target=target)
            if overlay_data and ram_base:
                toff = target - ram_base
                insn.comment = f"ov+0x{toff:06X}"
            insns.append(insn)
            i += 2
            continue

        # ---- Unconditional branch (Format 18) ----
        if (hw >> 11) == 0b11100:
            soff = hw & 0x7FF
            if soff & 0x400:
                soff -= 0x800
            target = addr + 4 + soff * 2
            insn = ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic="B",
                             operands=f"0x{target:08X}", is_branch=True,
                             branch_target=target)
            if overlay_data and ram_base:
                toff = target - ram_base
                insn.comment = f"ov+0x{toff:06X}"
            insns.append(insn)
            i += 2
            continue

        # ---- Fallback: unknown halfword ----
        insns.append(ThumbInsn(addr=addr, size=2, raw=raw2, mnemonic=".hword",
                               operands=f"0x{hw:04X}", comment="unknown"))
        i += 2

    return insns


def _decode_format2(hw: int) -> tuple[str, str]:
    """Decode Format 2: ADD/SUB with register or 3-bit immediate."""
    is_imm = (hw >> 10) & 1
    is_sub = (hw >> 9) & 1
    rn_or_imm = (hw >> 6) & 7
    rs = (hw >> 3) & 7
    rd = hw & 7
    mn = "SUB" if is_sub else "ADD"
    if is_imm:
        ops = f"R{rd}, R{rs}, #0x{rn_or_imm:X}"
    else:
        ops = f"R{rd}, R{rs}, R{rn_or_imm}"
    return mn, ops


def pool_start_index(insns: list[ThumbInsn]) -> int:
    """Return the index in *insns* where code ends and the literal pool begins.

    Walks backwards to the last return (``POP {…, PC}`` / ``BX LR``) that no
    in-function branch jumps past; everything from there on is literal-pool
    data rather than code.  Returns ``len(insns)`` when the function has no
    trailing pool.  This is the single source of truth for the code/pool split
    used by the extractor, the decompiler, and the shim emitter.
    """
    branch_targets = {
        i.branch_target for i in insns if i.is_branch and i.branch_target
    }
    for i in range(len(insns) - 1, -1, -1):
        if insns[i].is_return:
            if not any(insns[j].addr in branch_targets
                       for j in range(i + 1, len(insns))):
                return i + 1
    return len(insns)


# ---------------------------------------------------------------------------
# Thumb encoder  (line-by-line, matching the disassembler's output format)
# ---------------------------------------------------------------------------

class ThumbEncodeError(Exception):
    """Raised when an assembly line cannot be encoded."""


def _parse_int(s: str) -> int:
    """Parse ``#0x1A``, ``#26``, ``0x1A``, ``26``, ``=0x…`` to int."""
    s = s.strip().lstrip("#").lstrip("=")
    if s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    return int(s)


def _parse_reglist(s: str) -> tuple[int, bool]:
    """Parse ``{R0, R3, LR}`` → (mask, has_extra) where extra is LR or PC."""
    s = s.strip().strip("{}")
    mask = 0
    has_extra = False
    for part in s.split(","):
        part = part.strip().upper()
        if part in ("LR", "PC"):
            has_extra = True
        elif part.startswith("R"):
            mask |= 1 << int(part[1:])
    return mask, has_extra


def _parse_reg(s: str) -> int:
    """``R3`` → 3, ``SP`` → 13, ``LR`` → 14, ``PC`` → 15."""
    s = s.strip().upper()
    if s == "SP":
        return 13
    if s == "LR":
        return 14
    if s == "PC":
        return 15
    if s.startswith("R"):
        return int(s[1:])
    raise ThumbEncodeError(f"bad register: {s}")


def encode_thumb_line(mnemonic: str, operands: str, addr: int = 0) -> bytes:
    """Encode a single Thumb instruction to bytes.

    Returns 2 or 4 bytes.  *addr* is needed for branch offset calculation.
    """
    mn = mnemonic.upper().strip()
    ops = operands.strip()

    # ---- Directives ----
    if mn == ".HWORD":
        val = _parse_int(ops)
        return struct.pack("<H", val & 0xFFFF)
    if mn == ".WORD":
        val = _parse_int(ops)
        return struct.pack("<I", val & 0xFFFFFFFF)

    # ---- NOP ----
    if mn == "NOP":
        return struct.pack("<H", 0x46C0)

    # ---- PUSH / POP ----
    if mn == "PUSH":
        mask, has_lr = _parse_reglist(ops)
        hw = 0xB400 | (int(has_lr) << 8) | (mask & 0xFF)
        return struct.pack("<H", hw)
    if mn == "POP":
        mask, has_pc = _parse_reglist(ops)
        hw = 0xBC00 | (int(has_pc) << 8) | (mask & 0xFF)
        return struct.pack("<H", hw)

    # ---- BX / BLX (register) ----
    if mn == "BX":
        rm = _parse_reg(ops)
        hw = 0x4700 | (rm << 3)
        return struct.pack("<H", hw)
    if mn == "BLX" and not ops.startswith("0x") and not ops.startswith("#"):
        rm = _parse_reg(ops)
        hw = 0x4780 | (rm << 3)
        return struct.pack("<H", hw)

    # ---- BL (32-bit) ----
    if mn == "BL" or (mn == "BLX" and (ops.startswith("0x") or ops.startswith("#"))):
        target = _parse_int(ops)
        offset = target - (addr + 4)
        hi_off = (offset >> 12) & 0x7FF
        lo_off = (offset >> 1) & 0x7FF
        hw1 = 0xF000 | hi_off
        hw2 = (0xF800 if mn == "BL" else 0xE800) | lo_off
        return struct.pack("<HH", hw1, hw2)

    # ---- Conditional branches ----
    for ci, cn in enumerate(COND_NAMES):
        if mn == f"B{cn}":
            target = _parse_int(ops)
            offset = target - (addr + 4)
            soff = offset >> 1
            if soff < -128 or soff > 127:
                raise ThumbEncodeError(f"conditional branch out of range: offset={offset}")
            hw = 0xD000 | (ci << 8) | (soff & 0xFF)
            return struct.pack("<H", hw)

    # ---- Unconditional branch ----
    if mn == "B" and ops.startswith("0x"):
        target = _parse_int(ops)
        offset = target - (addr + 4)
        soff = offset >> 1
        if soff < -1024 or soff > 1023:
            raise ThumbEncodeError(f"branch out of range: offset={offset}")
        hw = 0xE000 | (soff & 0x7FF)
        return struct.pack("<H", hw)

    # ---- SWI ----
    if mn == "SWI":
        imm = _parse_int(ops)
        return struct.pack("<H", 0xDF00 | (imm & 0xFF))

    # ---- Parse comma-separated operands ----
    parts = [p.strip() for p in ops.replace("[", ",").replace("]", "").split(",") if p.strip()]

    # ---- MOV Rd, #imm8 (Format 3) ----
    if mn == "MOV" and len(parts) == 2 and parts[1].startswith("#"):
        rd = _parse_reg(parts[0])
        imm = _parse_int(parts[1])
        if rd <= 7 and 0 <= imm <= 255:
            hw = 0x2000 | (rd << 8) | imm
            return struct.pack("<H", hw)
        # High register MOV
        if not parts[1].startswith("#"):
            pass  # fall through

    # ---- MOV Rd, Rs (Format 5 hi or Format 1 LSL #0) ----
    if mn == "MOV" and len(parts) == 2 and parts[1].upper().startswith("R"):
        rd = _parse_reg(parts[0])
        rs = _parse_reg(parts[1])
        if rd > 7 or rs > 7:
            h1 = (rd >> 3) & 1
            h2 = (rs >> 3) & 1
            hw = 0x4600 | (h1 << 7) | (h2 << 6) | ((rs & 7) << 3) | (rd & 7)
            return struct.pack("<H", hw)
        # Low-register MOV = LSL Rd, Rs, #0
        hw = (rs << 3) | rd
        return struct.pack("<H", hw)

    # ---- CMP Rd, #imm8 (Format 3) ----
    if mn == "CMP" and len(parts) == 2 and parts[1].startswith("#"):
        rd = _parse_reg(parts[0])
        imm = _parse_int(parts[1])
        if rd <= 7 and 0 <= imm <= 255:
            hw = 0x2800 | (rd << 8) | imm
            return struct.pack("<H", hw)

    # ---- CMP Rd, Rs (Format 4 or Format 5) ----
    if mn == "CMP" and len(parts) == 2 and not parts[1].startswith("#"):
        rd = _parse_reg(parts[0])
        rs = _parse_reg(parts[1])
        if rd <= 7 and rs <= 7:
            hw = 0x4280 | (rs << 3) | rd
            return struct.pack("<H", hw)
        h1 = (rd >> 3) & 1
        h2 = (rs >> 3) & 1
        hw = 0x4500 | (h1 << 7) | (h2 << 6) | ((rs & 7) << 3) | (rd & 7)
        return struct.pack("<H", hw)

    # ---- ADD/SUB Rd, #imm8 (Format 3) ----
    if mn in ("ADD", "SUB") and len(parts) == 2 and parts[1].startswith("#"):
        rd = _parse_reg(parts[0])
        imm = _parse_int(parts[1])
        if rd <= 7 and 0 <= imm <= 255:
            op = 2 if mn == "ADD" else 3
            hw = 0x2000 | (op << 11) | (rd << 8) | imm
            return struct.pack("<H", hw)

    # ---- ADD SP, #imm / SUB SP, #imm (Format 13) ----
    if mn in ("ADD", "SUB") and len(parts) >= 2 and parts[0].upper() == "SP" and parts[1].startswith("#"):
        imm_str = parts[1].lstrip("#")
        neg = imm_str.startswith("-")
        imm = _parse_int(imm_str.lstrip("-"))
        imm7 = imm // 4
        sign = 1 if (mn == "SUB") != neg else 0
        hw = 0xB000 | (sign << 7) | (imm7 & 0x7F)
        return struct.pack("<H", hw)

    # ---- ADD Rd, PC/SP, #imm (Format 12) ----
    if mn == "ADD" and len(parts) == 3 and parts[1].upper() in ("PC", "SP"):
        rd = _parse_reg(parts[0])
        is_sp = parts[1].upper() == "SP"
        imm = _parse_int(parts[2])
        hw = 0xA000 | (int(is_sp) << 11) | (rd << 8) | ((imm // 4) & 0xFF)
        return struct.pack("<H", hw)

    # ---- ADD Rd, Rs, Rn / ADD Rd, Rs, #imm3 (Format 2) ----
    if mn in ("ADD", "SUB") and len(parts) == 3 and parts[0].startswith("R") and parts[1].startswith("R"):
        rd = _parse_reg(parts[0])
        rs = _parse_reg(parts[1])
        is_sub = mn == "SUB"
        if parts[2].startswith("#"):
            imm3 = _parse_int(parts[2])
            if not 0 <= imm3 <= 7:
                # The 3-operand ADD/SUB Rd,Rs,#imm form (Format 2) only has a 3-bit
                # immediate. imm>7 would overflow into the is_sub/opcode bits and be
                # SILENTLY miscoded (e.g. ADD R6,R6,#0x8 -> SUB R6,R6,#0x0). If Rd==Rs,
                # the caller almost certainly wants the 2-operand ADD/SUB Rd,#imm8 form.
                raise ThumbEncodeError(
                    f"{mn} {operands!r}: immediate {imm3} out of range for the 3-operand "
                    f"Format-2 form (imm must be 0..7); use the 2-operand '{mn} R{rd}, "
                    f"#0x{imm3:X}' (imm8) form instead")
            hw = 0x1C00 | (int(is_sub) << 9) | (1 << 10) | (imm3 << 6) | (rs << 3) | rd
            return struct.pack("<H", hw)
        rn = _parse_reg(parts[2])
        hw = 0x1800 | (int(is_sub) << 9) | (rn << 6) | (rs << 3) | rd
        return struct.pack("<H", hw)

    # ---- ADD hi-register (Format 5) ----
    if mn == "ADD" and len(parts) == 2 and not parts[1].startswith("#"):
        rd = _parse_reg(parts[0])
        rs = _parse_reg(parts[1])
        if rd > 7 or rs > 7:
            h1 = (rd >> 3) & 1
            h2 = (rs >> 3) & 1
            hw = 0x4400 | (h1 << 7) | (h2 << 6) | ((rs & 7) << 3) | (rd & 7)
            return struct.pack("<H", hw)

    # ---- Shifts (Format 1) ----
    if mn in ("LSL", "LSR", "ASR") and len(parts) == 3 and parts[2].startswith("#"):
        rd = _parse_reg(parts[0])
        rs = _parse_reg(parts[1])
        imm5 = _parse_int(parts[2])
        op = {"LSL": 0, "LSR": 1, "ASR": 2}[mn]
        hw = (op << 11) | ((imm5 & 0x1F) << 6) | (rs << 3) | rd
        return struct.pack("<H", hw)

    # ---- ALU register-register (Format 4) ----
    alu_map = {
        "AND": 0, "EOR": 1, "LSL": 2, "LSR": 3, "ASR": 4, "ADC": 5,
        "SBC": 6, "ROR": 7, "TST": 8, "NEG": 9, "CMP": 10, "CMN": 11,
        "ORR": 12, "MUL": 13, "BIC": 14, "MVN": 15,
    }
    if mn in alu_map and len(parts) == 2 and not parts[1].startswith("#"):
        rd = _parse_reg(parts[0])
        rs = _parse_reg(parts[1])
        if rd <= 7 and rs <= 7:
            hw = 0x4000 | (alu_map[mn] << 6) | (rs << 3) | rd
            return struct.pack("<H", hw)

    # ---- LDR Rd, =imm (PC-relative, needs addr) ----
    if mn == "LDR" and len(parts) >= 2 and parts[1].startswith("="):
        # This is a pseudo-instruction — cannot encode without knowing pool placement.
        # Store as a directive with the value for the caller to handle.
        raise ThumbEncodeError(
            f"LDR Rd, =imm requires literal pool placement (use .word directive instead)")

    # ---- LDR/STR with immediate offset ----
    if mn in ("LDR", "STR", "LDRB", "STRB", "LDRH", "STRH"):
        # formats:  Rd, [Rb, #imm]  or  Rd, [SP, #imm]  or  Rd, [Rb, Ro]  or  Rd, [PC, #imm]
        if len(parts) == 3:
            rd = _parse_reg(parts[0])
            rb_s = parts[1].strip().upper()
            off_s = parts[2].strip()

            # SP-relative (Format 11)
            if rb_s == "SP" and off_s.startswith("#"):
                imm = _parse_int(off_s)
                is_load = mn.startswith("LDR")
                hw = 0x9000 | (int(is_load) << 11) | (rd << 8) | ((imm // 4) & 0xFF)
                return struct.pack("<H", hw)

            # PC-relative (Format 6)
            if rb_s == "PC" and off_s.startswith("#"):
                imm = _parse_int(off_s)
                hw = 0x4800 | (rd << 8) | ((imm // 4) & 0xFF)
                return struct.pack("<H", hw)

            rb = _parse_reg(rb_s)

            # Register offset (Format 7/8)
            if not off_s.startswith("#"):
                ro = _parse_reg(off_s)
                if mn == "STR":
                    hw = 0x5000 | (ro << 6) | (rb << 3) | rd
                elif mn == "STRB":
                    hw = 0x5400 | (ro << 6) | (rb << 3) | rd
                elif mn == "LDR":
                    hw = 0x5800 | (ro << 6) | (rb << 3) | rd
                elif mn == "LDRB":
                    hw = 0x5C00 | (ro << 6) | (rb << 3) | rd
                elif mn == "STRH":
                    hw = 0x5200 | (ro << 6) | (rb << 3) | rd
                elif mn == "LDRH":
                    hw = 0x5A00 | (ro << 6) | (rb << 3) | rd
                elif mn == "LDSB":
                    hw = 0x5600 | (ro << 6) | (rb << 3) | rd
                elif mn == "LDSH":
                    hw = 0x5E00 | (ro << 6) | (rb << 3) | rd
                else:
                    raise ThumbEncodeError(f"unsupported register-offset mnemonic: {mn}")
                return struct.pack("<H", hw)

            # Immediate offset (Formats 9, 10)
            imm = _parse_int(off_s)
            if mn in ("LDR", "STR"):
                imm5 = imm // 4
                is_load = mn == "LDR"
                hw = 0x6000 | (int(is_load) << 11) | ((imm5 & 0x1F) << 6) | (rb << 3) | rd
                return struct.pack("<H", hw)
            elif mn in ("LDRB", "STRB"):
                imm5 = imm
                is_load = mn == "LDRB"
                hw = 0x7000 | (int(is_load) << 11) | ((imm5 & 0x1F) << 6) | (rb << 3) | rd
                return struct.pack("<H", hw)
            elif mn in ("LDRH", "STRH"):
                imm5 = imm // 2
                is_load = mn == "LDRH"
                hw = 0x8000 | (int(is_load) << 11) | ((imm5 & 0x1F) << 6) | (rb << 3) | rd
                return struct.pack("<H", hw)

    # ---- LDMIA / STMIA ----
    if mn in ("LDMIA", "STMIA"):
        rb_s = parts[0].rstrip("!")
        rb = _parse_reg(rb_s)
        rlist_str = ops[ops.index("{"):]
        mask, _ = _parse_reglist(rlist_str)
        is_load = mn == "LDMIA"
        hw = 0xC000 | (int(is_load) << 11) | (rb << 8) | (mask & 0xFF)
        return struct.pack("<H", hw)

    raise ThumbEncodeError(f"cannot encode: {mnemonic} {operands}")
