"""Re-assemble modified card-effect assembly and patch it back into overlay0003.

Usage:
    python -m otn_enhanced.tools.effect_insert <rom_or_overlay> <asm_file> [-o OUTPUT]

    <rom_or_overlay>  Path to the .nds ROM *or* a decompressed overlay0003.bin
    <asm_file>        Path to the annotated assembly file produced by effect_extract
                      (possibly modified by the user)
    -o OUTPUT         Output path (default: overwrite input in-place)

If the input file ends in ``.nds``, overlay0003 is extracted, patched,
recompressed, and written back into a new ROM at *OUTPUT* (or overwrites
the input ROM).  Otherwise the file is treated as a raw decompressed
overlay binary.

The tool parses the ``.func`` / ``.endfunc`` blocks, re-encodes each
instruction, and writes the resulting bytes at the correct file offsets.

Literal-pool entries (``.pool``) are written as raw 32-bit words.

Round-trip guarantee: extracting with ``effect_extract`` and immediately
inserting with ``effect_insert`` (no edits) produces an identical binary.
"""

from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3
from otn_enhanced.asm.thumb_disasm import encode_thumb_line, ThumbEncodeError

# ---------------------------------------------------------------------------
# Overlay0003 constants (must match effect_extract)
# ---------------------------------------------------------------------------
RAM_BASE = 0x02141700


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Regex for the .func directive:  .func <name> 0xADDRESS
_FUNC_RE = re.compile(r"^\.func\s+(\S+)\s+(0x[0-9A-Fa-f]+)$")
# Regex for .endfunc
_ENDFUNC_RE = re.compile(r"^\.endfunc")
# Regex for a pool literal:  .pool 0xVALUE   (optional comment)
_POOL_RE = re.compile(r"^\.pool\s+(0x[0-9A-Fa-f]+)")
# Regex for an instruction line:
#   <hex_bytes>  <MNEMONIC> <operands>  ; optional comment
# The hex field is the original encoding (informational); we re-encode from mnemonic+ops.
_INSN_RE = re.compile(
    r"^([0-9A-Fa-f]{4,8})\s+"   # 4 or 8 hex nibbles
    r"(\S+)"                     # mnemonic
    r"(?:\s+(.+?))??"            # operands (optional, non-greedy)
    r"(?:\s+;.*)?$"              # optional comment
)


def parse_asm_file(text: str) -> list[dict]:
    """Parse the assembly text into a list of function blocks.

    Each block is::

        {
            "name": "main_handler",
            "addr": 0x021EC2AC,
            "instructions": [
                {"type": "insn", "mnemonic": "PUSH", "operands": "{R4, R5, LR}", "orig_hex": "B530"},
                {"type": "pool", "value": 0x021F3A18},
                ...
            ],
        }
    """
    blocks: list[dict] = []
    current: dict | None = None

    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith(";"):
            continue

        # .func directive
        m = _FUNC_RE.match(line)
        if m:
            if current is not None:
                raise ValueError(f"Line {lineno}: nested .func without .endfunc")
            current = {
                "name": m.group(1),
                "addr": int(m.group(2), 16),
                "instructions": [],
            }
            continue

        # .endfunc
        if _ENDFUNC_RE.match(line):
            if current is not None:
                blocks.append(current)
                current = None
            continue

        if current is None:
            continue  # skip lines outside functions

        # .pool literal
        m = _POOL_RE.match(line)
        if m:
            current["instructions"].append({
                "type": "pool",
                "value": int(m.group(1), 16),
            })
            continue

        # Instruction line
        m = _INSN_RE.match(line)
        if m:
            current["instructions"].append({
                "type": "insn",
                "orig_hex": m.group(1),
                "mnemonic": m.group(2),
                "operands": m.group(3) or "",
            })
            continue

        # If we can't parse the line, warn but continue
        print(f"Warning: line {lineno}: cannot parse: {raw_line!r}", file=sys.stderr)

    if current is not None:
        raise ValueError("Unterminated .func block at end of file")

    return blocks


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

def encode_block(block: dict) -> tuple[int, bytes]:
    """Encode a parsed function block back to bytes.

    Returns ``(file_offset, encoded_bytes)``.
    """
    addr = block["addr"]
    file_offset = addr - RAM_BASE
    parts: list[bytes] = []
    cur_addr = addr

    for item in block["instructions"]:
        if item["type"] == "pool":
            # Align to 4 bytes if needed
            if cur_addr % 4 != 0:
                # pad with a NOP (0x46C0) — shouldn't normally happen after .pool alignment
                parts.append(struct.pack("<H", 0x46C0))
                cur_addr += 2
            parts.append(struct.pack("<I", item["value"]))
            cur_addr += 4
        else:
            mn = item["mnemonic"]
            ops = item["operands"]

            # Handle .hword / .word directives directly
            if mn.upper() == ".HWORD":
                val = int(ops.strip(), 0)
                parts.append(struct.pack("<H", val & 0xFFFF))
                cur_addr += 2
                continue
            if mn.upper() == ".WORD":
                val = int(ops.strip(), 0)
                parts.append(struct.pack("<I", val & 0xFFFFFFFF))
                cur_addr += 4
                continue

            # Strip trailing comment from operands (the regex should have
            # already handled this, but be safe)
            if ";" in ops:
                ops = ops[:ops.index(";")].rstrip()

            try:
                encoded = encode_thumb_line(mn, ops, addr=cur_addr)
            except ThumbEncodeError as exc:
                raise ThumbEncodeError(
                    f"In {block['name']} at 0x{cur_addr:08X}: {exc}"
                ) from exc
            parts.append(encoded)
            cur_addr += len(encoded)

    return file_offset, b"".join(parts)


# ---------------------------------------------------------------------------
# Patch overlay
# ---------------------------------------------------------------------------

def patch_overlay(overlay: bytearray, blocks: list[dict], *,
                  strict: bool = True) -> list[str]:
    """Encode all blocks and patch them into *overlay* (modified in-place).

    If *strict* is True, raises if the new encoded bytes are larger than the
    original function extent.

    Returns a log of actions.
    """
    log: list[str] = []

    for block in blocks:
        file_off, encoded = encode_block(block)
        end_off = file_off + len(encoded)

        if end_off > len(overlay):
            raise RuntimeError(
                f"{block['name']}: encoded bytes extend past overlay end "
                f"(0x{end_off:06X} > 0x{len(overlay):06X})")

        # Compute original size from orig_hex to check for size change
        orig_size = 0
        for item in block["instructions"]:
            if item["type"] == "pool":
                orig_size += 4
            else:
                orig_size += len(bytes.fromhex(item["orig_hex"]))

        if strict and len(encoded) > orig_size:
            raise RuntimeError(
                f"{block['name']}: encoded size ({len(encoded)}) exceeds "
                f"original ({orig_size}) — would overwrite adjacent code. "
                f"Use --no-strict to force.")

        overlay[file_off:file_off + len(encoded)] = encoded
        log.append(
            f"  {block['name']:20s}  ov+0x{file_off:06X}  "
            f"{orig_size:4d} → {len(encoded):4d} bytes"
        )

    return log


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-assemble modified card-effect assembly and patch overlay0003.")
    parser.add_argument("input", help=".nds ROM file or decompressed overlay0003.bin")
    parser.add_argument("asm_file", help="Path to the assembly file (from effect_extract)")
    parser.add_argument("-o", "--output",
                        help="Output path (default: overwrite input in-place)")
    parser.add_argument("--no-strict", action="store_true",
                        help="Allow encoded size to exceed original (dangerous)")
    args = parser.parse_args()

    input_path = Path(args.input)
    is_nds = input_path.suffix.lower() == ".nds"

    # --- Load overlay ---
    if is_nds:
        rom, overlay_bytes = load_overlay3(input_path)
        overlay = bytearray(overlay_bytes)
        print(f"Extracted overlay0003 from {input_path.name} "
              f"({len(overlay)} bytes decompressed)", file=sys.stderr)
    else:
        rom = None
        overlay = bytearray(input_path.read_bytes())

    # --- Parse ASM ---
    asm_text = Path(args.asm_file).read_text(encoding="utf-8")
    blocks = parse_asm_file(asm_text)

    if not blocks:
        print("No .func blocks found in assembly file.", file=sys.stderr)
        sys.exit(1)

    print(f"Parsed {len(blocks)} function block(s):", file=sys.stderr)
    for b in blocks:
        print(f"  {b['name']} @ 0x{b['addr']:08X} ({len(b['instructions'])} items)",
              file=sys.stderr)

    # --- Patch ---
    try:
        log = patch_overlay(overlay, blocks, strict=not args.no_strict)
    except (ThumbEncodeError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Patched:", file=sys.stderr)
    for line in log:
        print(line, file=sys.stderr)

    # --- Save ---
    out_path = Path(args.output) if args.output else input_path

    if is_nds:
        save_overlay3(rom, overlay, out_path)
        print(f"Saved ROM to {out_path}", file=sys.stderr)
    else:
        out_path.write_bytes(overlay)
        print(f"Wrote {len(overlay)} bytes to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
