"""Extract a card's effect handler code from overlay0003 and produce annotated
Thumb assembly.

Usage:
    python -m otn_enhanced.tools.effect_extract <rom_or_overlay> <card> [-o OUTPUT]

    <rom_or_overlay>  Path to the .nds ROM *or* a decompressed overlay0003.bin
    <card>            Card name (exact match) or hex Konami ID (e.g. 0x1335)
    -o OUTPUT         Optional output path (default: stdout)

If the input file ends in ``.nds``, overlay0003 is extracted and
decompressed automatically.  Otherwise the file is treated as a raw
decompressed overlay binary.

The output is a self-contained text file that can be fed back into
``effect_insert`` to patch a modified binary.
"""

from __future__ import annotations

import argparse
import struct
import sys
import textwrap
from pathlib import Path

from otn_enhanced.rom.overlay_io import load_overlay3
from otn_enhanced.asm.thumb_disasm import decode_thumb, ThumbInsn, pool_start_index
from otn_enhanced.rom.konami_id_to_card_name import (
    KONAMI_ID_TO_CARD_NAME,
    CARD_NAME_TO_KONAMI_ID,
    card_name_to_konami_id,
)
from otn_enhanced.rom.game_constants import ERA2_ATTRIBUTE_MAP, ERA2_RACE_MAP, ERA2_CARD_TYPE_MAP

# ---------------------------------------------------------------------------
# Overlay0003 constants (Over the Nexus – EU)
# ---------------------------------------------------------------------------
RAM_BASE = 0x02141700
HANDLER_TABLE_OFFSET = 0x134508
HANDLER_ENTRY_SIZE = 24        # 5 × u32 pointers + u32 card_id
HANDLER_ENTRY_COUNT = 4116
HANDLER_SLOT_NAMES = [
    "main_handler",
    "sub_handler",
    "activation_cond",
    "target_filter",
    "resolution",
]

# ---------------------------------------------------------------------------
# Card context struct layout
# The card context pointer is passed as the first argument (R0) and is
# typically saved to R4 or R5 in the function prologue.
# Keys: (byte_offset, access_type)  access_type: B=byte, H=halfword, W=word
# ---------------------------------------------------------------------------
CARD_CONTEXT_FIELDS: dict[tuple[int, str], str] = {
    (0x00, "H"): "this card's Konami ID",
    (0x00, "W"): "card data (word)",
    (0x02, "B"): "controlling player",
    (0x03, "B"): "card race",
    (0x04, "B"): "trigger type",
    (0x05, "B"): "trigger category",
    (0x06, "B"): "slot / phase info",
    (0x06, "H"): "slot / phase (halfword)",
    (0x08, "W"): "context word 0x08",
    (0x0C, "H"): "card instance / zone ref",
    (0x0C, "B"): "card instance (low byte)",
    (0x0D, "B"): "zone ref (high byte)",
    (0x10, "H"): "field 0x10",
    (0x12, "H"): "field 0x12",
    (0x14, "H"): "field 0x14",
    (0x16, "H"): "field 0x16",
}

# ---------------------------------------------------------------------------
# Known engine subroutines (overlay file offset → inferred description)
# Names are best-effort from calling patterns and game behaviour analysis.
# ---------------------------------------------------------------------------
KNOWN_SUBROUTINES: dict[int, str] = {
    0x058FF4: "get_phase_info",
    0x059118: "ui_event_post",   # 0x0219A818; was a heuristic label (KB-verified)
    0x05AD30: "list_picker",   # 0x0219C430; was a heuristic label (KB-verified)
    0x05AE10: "picker_readback",   # 0x0219C510; was a heuristic label (KB-verified)
    0x05AE34: "get_duel_state_3",
    0x05FD30: "count_matching_in_deck",
    0x05FDB4: "count_matching_in_deck_ex",
    0x060B0C: "get_card_info",
    0x060D1C: "get_card_zone_info",
    0x060E10: "check_location_change",
    0x060EA0: "check_location_change_ex",
    0x060EE8: "get_location_info",
    0x061954: "get_battle_info",
    0x061C20: "get_card_location",
    0x06B868: "check_hand_count",
    0x06C170: "ss_gate_a",   # 0x021AD870; was a heuristic label (KB-verified)
    0x0704E8: "check_zone_available",
    0x076914: "get_card_property",
    0x076964: "get_card_property_2",
    0x077730: "check_field_condition",
    0x077C8C: "check_chain_link",
    0x0787CC: "ss_gate_b",   # 0x021B9ECC; was a heuristic label (KB-verified)
    0x078D40: "check_activation_permission",
    0x08309C: "apply_card_modification",
    0x08E4C8: "modify_card_stats",
    0x08F188: "send_to_graveyard",
    0x090E84: "turnlog_post",          # 0x021D2584; was mislabelled special_summon_from_deck (KB-verified turn log)
    0x0911A4: "depth_push",   # 0x021D28A4; was a heuristic label (KB-verified)
    0x091264: "depth_pop",   # 0x021D2964; was a heuristic label (KB-verified)
    0x09151C: "check_effect_condition",
    0x0914C8: "apply_effect",
    0x095740: "execute_effect_action",
    0x09895A: "finish_effect_processing",
    0x09BF80: "search_deck",
    0x09CA68: "draw_card",
    0x0A3960: "evaluate_target",
    0x0A39DC: "filter_valid_targets",
    0x0AEC84: "check_activation_sub",
    0x0F30B0: "apply_effect_to_target",
    0x0F3204: "select_target",
    0x0F32B0: "setup_effect_params",
    0x0F3778: "resolve_effect",
    0x1028E0: "register_card_effect",
    0x1091C0: "check_summon_condition",
    0x109224: "set_card_properties",
    0x10A4B0: "apply_damage",
    0x127B5C: "search_and_add_to_hand",
}

# ---------------------------------------------------------------------------
# Conditional branch descriptions
# ---------------------------------------------------------------------------
BRANCH_COND_DESC: dict[str, str] = {
    "BEQ": "if equal (zero)",
    "BNE": "if not equal (non-zero)",
    "BCS": "if carry set (unsigned >=)",
    "BCC": "if carry clear (unsigned <)",
    "BMI": "if negative",
    "BPL": "if positive or zero",
    "BVS": "if overflow",
    "BVC": "if no overflow",
    "BHI": "if unsigned higher",
    "BLS": "if unsigned lower/same",
    "BGE": "if signed >=  ",
    "BLT": "if signed <",
    "BGT": "if signed >",
    "BLE": "if signed <=",
}


# ---------------------------------------------------------------------------
# Helper: resolve a card argument to a Konami ID
# ---------------------------------------------------------------------------

def resolve_card(card_arg: str) -> int:
    """Return the integer Konami ID from a name or hex literal."""
    card_arg = card_arg.strip()
    # Try as hex number
    if card_arg.lower().startswith("0x"):
        return int(card_arg, 16)
    try:
        return int(card_arg)
    except ValueError:
        pass
    # Name lookup
    # Exact match first, then case-insensitive; first record wins either way
    kid = card_name_to_konami_id(card_arg)
    if kid is not None:
        return kid
    low = card_arg.lower()
    for name, kid in CARD_NAME_TO_KONAMI_ID:
        if name.lower() == low:
            return kid
    raise ValueError(f"Card not found: {card_arg!r}")


# ---------------------------------------------------------------------------
# Look up handler table entry
# ---------------------------------------------------------------------------

def find_handler_entry(overlay: bytes, konami_id: int) -> dict | None:
    """Search the master handler table for *konami_id*.

    Returns a dict with keys: index, card_id, and the 5 slot function
    pointers (RAM addresses with Thumb bit set, or 0 if empty).
    """
    for idx in range(HANDLER_ENTRY_COUNT):
        off = HANDLER_TABLE_OFFSET + idx * HANDLER_ENTRY_SIZE
        ptrs = struct.unpack_from("<5I", overlay, off)
        cid = struct.unpack_from("<I", overlay, off + 20)[0]
        if cid == konami_id:
            entry: dict = {"index": idx, "card_id": cid}
            for si, name in enumerate(HANDLER_SLOT_NAMES):
                entry[name] = ptrs[si]
            return entry
    return None


# ---------------------------------------------------------------------------
# Determine function extent (PUSH … POP {…, PC} / BX LR)
# ---------------------------------------------------------------------------

def detect_function_size(overlay: bytes, file_offset: int, *, max_size: int = 2048) -> int:
    """Heuristically detect the end of a Thumb function.

    Scans from *file_offset* forward looking for either:
      - POP {…, PC}   (0xBDxx)
      - BX LR         (0x4770)
    then includes any trailing literal-pool words (aligned data after the
    last instruction until the next PUSH or until max_size is hit).
    """
    i = 0
    last_return = -1
    while i < max_size and file_offset + i + 2 <= len(overlay):
        hw = struct.unpack_from("<H", overlay, file_offset + i)[0]
        # POP {…, PC}
        if (hw & 0xFF00) == 0xBD00:
            last_return = i + 2
        # BX LR
        elif hw == 0x4770:
            last_return = i + 2
        # If we've already seen a return, check if this looks like the start
        # of a new function (PUSH {…, LR}) — stop here
        elif last_return > 0 and (hw & 0xFF00) == 0xB500:
            break
        # Another heuristic: after a return, if we see a 32-bit aligned word
        # that looks like a RAM pointer (0x02xxxxxx) or a literal constant,
        # include it in the pool.  Otherwise stop.
        elif last_return > 0 and i >= last_return:
            # Include literal pool words that follow the return
            # Stop at next PUSH or if we've consumed too many pool words
            pool_words = (i - last_return) // 2
            if pool_words > 32:
                break
        i += 2

    if last_return > 0:
        # Include any trailing literal pool (align to 4 bytes)
        end = i
        return end
    # Fallback: just return max_size
    return min(max_size, len(overlay) - file_offset)


# ---------------------------------------------------------------------------
# Annotate decoded instructions with game-specific knowledge
# ---------------------------------------------------------------------------

def _safe_parse_imm(s: str) -> int | None:
    """Parse ``#0xFE``, ``0x1234``, ``#42`` etc. to *int*, or *None*."""
    s = s.strip().lstrip("#")
    try:
        return int(s, 16) if s.startswith(("0x", "0X")) else int(s)
    except ValueError:
        return None


def _detect_ctx_register(insns: list[ThumbInsn]) -> str | None:
    """Detect which register the card context pointer (R0) is saved into."""
    for insn in insns[:6]:
        if insn.mnemonic == "ADD":
            parts = [p.strip() for p in insn.operands.split(",")]
            if len(parts) == 3 and parts[1] == "R0" and parts[2] == "#0x0":
                return parts[0]
        if insn.mnemonic == "MOV":
            parts = [p.strip() for p in insn.operands.split(",")]
            if len(parts) == 2 and parts[1] == "R0":
                return parts[0]
    return None


# ------------------------------------------------------------------
# Per-instruction comment builders
# ------------------------------------------------------------------

def _comment_push_pop(insn: ThumbInsn, all_insns: list, idx: int) -> str:
    mn, ops = insn.mnemonic, insn.operands
    if mn == "PUSH":
        return ("save registers and return address (function prologue)"
                if "LR" in ops else "save registers")
    # POP
    if "PC" in ops:
        if idx > 0 and all_insns[idx - 1].mnemonic == "MOV" \
                and all_insns[idx - 1].operands.startswith("R0, #"):
            return "restore registers and return (R0 = return value)"
        return "restore registers and return"
    return "restore registers"


def _comment_bl(insn: ThumbInsn, overlay: bytes) -> str:
    target = insn.branch_target
    if not target:
        return "call function"
    ov_off = target - RAM_BASE
    if 0 <= ov_off < len(overlay):
        name = KNOWN_SUBROUTINES.get(ov_off)
        if name:
            return f"call {name} (ov+0x{ov_off:06X})"
        return f"call subroutine (ov+0x{ov_off:06X})"
    return f"call ARM9 function (0x{target:08X})"


def _comment_branch(insn: ThumbInsn) -> str:
    mn = insn.mnemonic
    target = insn.branch_target
    toff_s = f" -> ov+0x{target - RAM_BASE:06X}" if target else ""
    if mn in BRANCH_COND_DESC:
        return f"branch {BRANCH_COND_DESC[mn]}{toff_s}"
    if mn == "B" and insn.is_branch:
        return f"unconditional jump{toff_s}"
    return ""


def _comment_pool_load(insn: ThumbInsn, overlay: bytes) -> str:
    val = insn.pool_value
    parts = [p.strip() for p in insn.operands.split(",") if p.strip()]
    rd = parts[0] if parts else "Rd"
    if val in KONAMI_ID_TO_CARD_NAME:
        return f"{rd} = 0x{val:04X}  card: {KONAMI_ID_TO_CARD_NAME[val]}"
    if (val & 1) and RAM_BASE <= (val & ~1) < RAM_BASE + len(overlay):
        foff = (val & ~1) - RAM_BASE
        name = KNOWN_SUBROUTINES.get(foff, f"ov+0x{foff:06X}")
        return f"{rd} = ptr to func {name}"
    if 0x02000000 <= val < 0x02400000:
        return f"{rd} = 0x{val:08X}  (RAM data pointer)"
    return f"{rd} = 0x{val:08X}  (literal pool)"


def _comment_ctx_access(mn: str, ops: str, ctx_reg: str) -> str | None:
    """Annotate a load/store that uses the card-context register."""
    raw = ops.replace("[", ",").replace("]", "").split(",")
    clean = [p.strip() for p in raw if p.strip()]
    if len(clean) < 2 or clean[1] != ctx_reg:
        return None
    rd = clean[0]
    access = "W" if mn in ("LDR", "STR") else \
             "H" if mn in ("LDRH", "STRH", "LDSH") else "B"
    is_load = mn.startswith("LDR") or mn.startswith("LDS")
    if len(clean) == 3 and clean[2].startswith("#"):
        imm = _safe_parse_imm(clean[2])
        if imm is not None:
            desc = CARD_CONTEXT_FIELDS.get((imm, access))
            if desc:
                return f"{rd} = card.{desc}" if is_load else f"card.{desc} = {rd}"
            size_tag = {"W": "word", "H": "half", "B": "byte"}[access]
            return (f"{rd} = card[+0x{imm:X}] ({size_tag})" if is_load
                    else f"card[+0x{imm:X}] = {rd} ({size_tag})")
    return None


def _comment_load(mn: str, ops: str) -> str:
    size = {"LDR": "word", "LDRH": "halfword", "LDRB": "byte",
            "LDSB": "signed byte", "LDSH": "signed half"}.get(mn, "")
    raw = ops.replace("[", ",").replace("]", "").split(",")
    c = [p.strip() for p in raw if p.strip()]
    if len(c) == 3:
        return f"{c[0]} = {size} [{c[1]} + {c[2]}]"
    if len(c) == 2:
        return f"{c[0]} = {size} [{c[1]}]"
    return f"load {size}"


def _comment_store(mn: str, ops: str) -> str:
    size = {"STR": "word", "STRH": "halfword", "STRB": "byte"}.get(mn, "")
    raw = ops.replace("[", ",").replace("]", "").split(",")
    c = [p.strip() for p in raw if p.strip()]
    if len(c) == 3:
        return f"store {c[0]} ({size}) to [{c[1]} + {c[2]}]"
    if len(c) == 2:
        return f"store {c[0]} ({size}) to [{c[1]}]"
    return f"store {size}"


def _comment_mov(parts: list[str], all_insns: list, idx: int) -> str:
    if len(parts) != 2:
        return ""
    dst, src = parts
    if src.startswith("#"):
        imm = _safe_parse_imm(src)
        if imm is not None:
            # return-value pattern: MOV R0, #val  then POP {PC}
            if dst == "R0" and idx + 1 < len(all_insns):
                nxt = all_insns[idx + 1]
                if nxt.mnemonic == "POP" and "PC" in nxt.operands:
                    if imm == 0:
                        return "R0 = 0  (return false / cannot activate)"
                    if imm == 1:
                        return "R0 = 1  (return true / can activate)"
                    return f"R0 = 0x{imm:X}  (return value)"
            if imm in KONAMI_ID_TO_CARD_NAME:
                return f"{dst} = 0x{imm:X}  card: {KONAMI_ID_TO_CARD_NAME[imm]}"
            return f"{dst} = 0x{imm:X}"
    return f"{dst} = {src}"


def _comment_cmp(parts: list[str]) -> str:
    if len(parts) != 2:
        return ""
    reg, operand = parts
    if operand.startswith("#"):
        imm = _safe_parse_imm(operand)
        if imm is not None:
            if imm == 0:
                return f"test if {reg} is zero"
            return f"compare {reg} with 0x{imm:X} ({imm})"
    return f"compare {reg} with {operand}"


def _comment_add_sub(mn: str, parts: list[str], insn: ThumbInsn,
                     all_insns: list, idx: int) -> str:
    op = "+" if mn == "ADD" else "-"
    if len(parts) == 3:
        dst, src, val = parts
        if val == "#0x0":
            # register copy — check BL (return value) before context pointer
            if idx > 0 and all_insns[idx - 1].mnemonic == "BL":
                return f"{dst} = R0  (save function result)"
            if src == "R0" and idx < 6:
                return f"{dst} = R0  (card context pointer)"
            return f"{dst} = {src}"
        return f"{dst} = {src} {op} {val.lstrip('#')}"
    if len(parts) == 2:
        dst, val = parts
        if dst == "SP":
            return f"adjust stack: SP {op}= {val.lstrip('#')}"
        if val.startswith("#"):
            return f"{dst} {op}= {val.lstrip('#')}"
        return f"{dst} {op}= {val}"
    return ""


def _comment_shift(mn: str, parts: list[str]) -> str:
    name = {"LSL": "left", "LSR": "logical right", "ASR": "arithmetic right"}[mn]
    if len(parts) == 3:
        return f"{parts[0]} = {parts[1]} shift {name} by {parts[2].lstrip('#')}"
    if len(parts) == 2:
        return f"{parts[0]} shift {name} by {parts[1].lstrip('#')}"
    return ""


# ------------------------------------------------------------------
# Post-return pool data annotation
# ------------------------------------------------------------------

def _annotate_as_pool(insn: ThumbInsn, overlay: bytes) -> None:
    off = insn.addr - RAM_BASE
    if insn.addr % 4 == 0 and off + 4 <= len(overlay):
        val = struct.unpack_from("<I", overlay, off)[0]
        cmt = f"literal pool: 0x{val:08X}"
        if val in KONAMI_ID_TO_CARD_NAME:
            cmt += f"  = {KONAMI_ID_TO_CARD_NAME[val]}"
        elif (val & 1) and RAM_BASE <= (val & ~1) < RAM_BASE + len(overlay):
            foff = (val & ~1) - RAM_BASE
            name = KNOWN_SUBROUTINES.get(foff, f"ov+0x{foff:06X}")
            cmt += f"  = func {name}"
        elif 0x02000000 <= val < 0x02400000:
            cmt += "  (RAM data pointer)"
        insn.comment = cmt
    else:
        insn.comment = "(2nd half of literal pool value)"


# ------------------------------------------------------------------
# Main annotation entry point
# ------------------------------------------------------------------

def annotate_instructions(insns: list[ThumbInsn], overlay: bytes) -> None:
    """Add comprehensive game-specific comments to every instruction."""
    ctx_reg = _detect_ctx_register(insns)

    # The pool boundary (first instruction that is literal-pool data, not code)
    # is computed by the shared helper in thumb_disasm.
    pool_start_idx = pool_start_index(insns)

    for idx, insn in enumerate(insns):
        # Instructions past the pool boundary are literal-pool data
        if idx >= pool_start_idx:
            _annotate_as_pool(insn, overlay)
            continue

        mn = insn.mnemonic
        ops = insn.operands
        parts = [p.strip() for p in ops.split(",") if p.strip()]

        # PUSH / POP
        if mn in ("PUSH", "POP"):
            insn.comment = _comment_push_pop(insn, insns, idx)
            continue

        # BL (function call)
        if mn == "BL":
            insn.comment = _comment_bl(insn, overlay)
            continue

        # BLX
        if mn == "BLX":
            if insn.is_branch and insn.branch_target:
                insn.comment = f"call ARM-mode (0x{insn.branch_target:08X})"
            else:
                insn.comment = f"call via {ops}"
            continue

        # BX
        if mn == "BX":
            insn.comment = "return to caller" if ops == "LR" else f"branch via {ops}"
            continue

        # Conditional & unconditional branches
        if (mn.startswith("B") and mn in BRANCH_COND_DESC) or \
           (mn == "B" and insn.is_branch):
            insn.comment = _comment_branch(insn)
            continue

        # LDR Rd, [PC, #imm]  (literal pool)
        if mn == "LDR" and insn.is_pool_ref:
            insn.comment = _comment_pool_load(insn, overlay)
            continue

        # Memory access through the card context register
        if ctx_reg and mn in ("LDR", "LDRH", "LDRB", "LDSB", "LDSH",
                              "STR", "STRH", "STRB"):
            cmt = _comment_ctx_access(mn, ops, ctx_reg)
            if cmt:
                insn.comment = cmt
                continue

        # Generic loads / stores
        if mn in ("LDR", "LDRH", "LDRB", "LDSB", "LDSH"):
            insn.comment = _comment_load(mn, ops)
            continue
        if mn in ("STR", "STRH", "STRB"):
            insn.comment = _comment_store(mn, ops)
            continue

        # ADD / SUB
        if mn in ("ADD", "SUB"):
            insn.comment = _comment_add_sub(mn, parts, insn, insns, idx)
            continue

        # MOV
        if mn == "MOV":
            insn.comment = _comment_mov(parts, insns, idx)
            continue

        # CMP
        if mn == "CMP":
            insn.comment = _comment_cmp(parts)
            continue

        # Shifts
        if mn in ("LSL", "LSR", "ASR"):
            insn.comment = _comment_shift(mn, parts)
            continue

        # ALU register-register
        _alu = {
            "AND": lambda: f"{parts[0]} &= {parts[1]}  (bitwise AND)",
            "ORR": lambda: f"{parts[0]} |= {parts[1]}  (bitwise OR)",
            "EOR": lambda: f"{parts[0]} ^= {parts[1]}  (XOR)",
            "BIC": lambda: f"{parts[0]} &= ~{parts[1]}  (clear bits)",
            "TST": lambda: f"test {parts[0]} & {parts[1]}  (flags only)",
            "MVN": lambda: f"{parts[0]} = ~{parts[1]}  (NOT)",
            "NEG": lambda: f"{parts[0]} = -{parts[1]}",
            "MUL": lambda: f"{parts[0]} *= {parts[1]}",
            "ADC": lambda: f"{parts[0]} += {parts[1]} + carry",
            "SBC": lambda: f"{parts[0]} -= {parts[1]} - borrow",
            "ROR": lambda: f"{parts[0]} rotate right by {parts[1]}",
            "CMN": lambda: f"compare {parts[0]} with -{parts[1]}",
        }
        if mn in _alu and len(parts) >= 2:
            insn.comment = _alu[mn]()
            continue

        # NOP / SWI / LDM / STM
        if mn == "NOP":
            insn.comment = "no operation"
            continue
        if mn == "SWI":
            insn.comment = f"software interrupt {ops}"
            continue
        if mn == "LDMIA":
            insn.comment = f"load multiple from [{parts[0]}]"
            continue
        if mn == "STMIA":
            insn.comment = f"store multiple to [{parts[0]}]"
            continue

        # Directives / unknown
        if mn == ".hword":
            insn.comment = "data halfword"
            continue


# ---------------------------------------------------------------------------
# Top-level: extract and format
# ---------------------------------------------------------------------------

def _load_overlay(input_path: str | Path) -> bytes:
    """Load decompressed overlay0003 from a .nds ROM or raw .bin file."""
    p = Path(input_path)
    if p.suffix.lower() == ".nds":
        _, data = load_overlay3(p)
        return data
    return p.read_bytes()


def extract_card_effect(input_path: str | Path, card_arg: str) -> str:
    """Extract a card's effect handlers and return annotated assembly text.

    *input_path* may be a ``.nds`` ROM (overlay0003 is extracted
    automatically) or a raw decompressed overlay binary.
    """
    overlay = _load_overlay(input_path)
    return extract_card_effect_from_bytes(overlay, card_arg,
                                          source_name=Path(input_path).name)


def extract_card_effect_from_bytes(
    overlay: bytes, card_arg: str, *, source_name: str = "overlay0003"
) -> str:
    """Extract a card's effect handlers from pre-loaded overlay bytes.

    This avoids reloading the ROM/file and is suitable for batch extraction.
    """
    konami_id = resolve_card(card_arg)
    card_name = KONAMI_ID_TO_CARD_NAME.get(konami_id, f"Unknown(0x{konami_id:04X})")

    entry = find_handler_entry(overlay, konami_id)
    if entry is None:
        raise RuntimeError(
            f"Card 0x{konami_id:04X} ({card_name}) not found in handler table")

    lines: list[str] = []
    lines.append(f"; ================================================================")
    lines.append(f"; Card Effect Assembly — {card_name}")
    lines.append(f"; Konami ID: 0x{konami_id:04X}  (decimal {konami_id})")
    lines.append(f"; Handler table index: {entry['index']}")
    lines.append(f"; Source: {source_name}")
    lines.append(f"; RAM base: 0x{RAM_BASE:08X}")
    lines.append(f"; ================================================================")
    lines.append(f";")
    lines.append(f"; Handler table entry (file offset 0x{HANDLER_TABLE_OFFSET + entry['index'] * HANDLER_ENTRY_SIZE:06X}):")
    for sname in HANDLER_SLOT_NAMES:
        ptr = entry[sname]
        if ptr:
            foff = (ptr & ~1) - RAM_BASE
            lines.append(f";   {sname:20s} = 0x{ptr:08X}  (ov+0x{foff:06X})")
        else:
            lines.append(f";   {sname:20s} = NULL")
    lines.append(f";")
    lines.append("")

    # Track which addresses we've already disassembled (for shared handlers)
    seen_addrs: set[int] = set()

    for slot_name in HANDLER_SLOT_NAMES:
        ptr = entry[slot_name]
        if not ptr:
            continue
        func_addr = ptr & ~1   # clear Thumb bit
        file_off = func_addr - RAM_BASE

        if func_addr in seen_addrs:
            lines.append(f"; --- {slot_name}: same as above (0x{func_addr:08X}) ---")
            lines.append("")
            continue
        seen_addrs.add(func_addr)

        # Detect function size
        func_size = detect_function_size(overlay, file_off)
        func_data = overlay[file_off:file_off + func_size]

        # Disassemble
        insns = decode_thumb(func_data, func_addr, overlay_data=overlay, ram_base=RAM_BASE)
        annotate_instructions(insns, overlay)

        lines.append(f"; === {slot_name} ===")
        lines.append(f"; Address: 0x{func_addr:08X}  (ov+0x{file_off:06X})")
        lines.append(f"; Size: {func_size} bytes ({func_size // 2} halfwords)")
        lines.append(f"; Pointer value: 0x{ptr:08X}")
        lines.append(f".func {slot_name} 0x{func_addr:08X}")

        for insn in insns:
            # Check for literal-pool data after function return
            if insn.mnemonic == ".hword" and insn.comment == "unknown":
                # Might be a literal pool word — try reading as 32-bit
                pool_off = insn.addr - RAM_BASE
                if pool_off + 4 <= len(overlay) and (insn.addr % 4 == 0):
                    val = struct.unpack_from("<I", overlay, pool_off)[0]
                    cmt = ""
                    if val in KONAMI_ID_TO_CARD_NAME:
                        cmt = f"  card:{KONAMI_ID_TO_CARD_NAME[val]}"
                    elif (val & 1) and RAM_BASE <= (val & ~1) < RAM_BASE + len(overlay):
                        foff2 = (val & ~1) - RAM_BASE
                        cmt = f"  func:ov+0x{foff2:06X}"
                    lines.append(f"    .pool 0x{val:08X}          ; addr=0x{insn.addr:08X}{cmt}")
                    continue

            # Format address + hex + asm
            foff_insn = insn.addr - RAM_BASE
            hexstr = insn.raw.hex().upper()
            asm_part = f"{insn.mnemonic:<8s}{insn.operands}" if insn.operands else insn.mnemonic
            cmt = f"  ; {insn.comment}" if insn.comment else ""
            line = f"    {hexstr:<12s}{asm_part}{cmt}"
            lines.append(line)

        lines.append(f".endfunc  ; {slot_name}")
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract a card's effect handlers from overlay0003 as annotated Thumb assembly.")
    parser.add_argument("input", help=".nds ROM file or decompressed overlay0003.bin")
    parser.add_argument("card", help="Card name or hex Konami ID (e.g. 0x1335)")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    args = parser.parse_args()

    try:
        text = extract_card_effect(args.input, args.card)
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote {len(text)} bytes to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
