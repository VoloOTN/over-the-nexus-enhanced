"""C-migration Phase 4: emit a `.S` fallback for a corpus slot, to be gated byte-identical by c_forms (gate="identical").

    uv run python -m otn_enhanced.tools.c_s_gen SLOT_NAME out.S

The code is decoded from the slot's bytes in scratch/c_corpus.json (ponytail: linear decode up to the first literal
pool; ceiling = code that interleaves data with instructions). In-slot branches become labels; external B/BL are
absolute (`bl 0xADDR`, ld resolves the PC offset, since the stub links at the slot address); `ldr =` pools are
kept as .word at their original place. Unified syntax needs the flag-setting `s`, picked from the raw halfword.
"""
import json
import sys

from otn_enhanced.asm.thumb_disasm import decode_thumb


def _mn(hw: int, m: str, nops: int) -> str:
    m = m.lower()
    top = hw >> 11
    if top <= 0b00010:                       # shift-by-immediate (lsl #0 prints as MOV)
        return "movs" if m == "mov" else m + "s"
    if top == 0b00011:                       # add/sub, 3 regs or imm3
        return m + "s"
    if top >> 2 == 0b001:                    # mov/cmp/add/sub imm8
        return m if m == "cmp" else m + "s"
    if hw >> 10 == 0b010000:                 # ALU ops
        return m if m in ("tst", "cmp", "cmn") else m + "s"
    return m


def gen(name: str, corpus_path: str = "scratch/c_corpus.json") -> str:
    s = next(x for x in json.load(open(corpus_path))["slots"] if x["name"] == name)
    raw, base = bytes.fromhex(s["bytes"]), int(s["addr"], 16)
    ins = decode_thumb(raw, base)
    for k, i in enumerate(ins):                      # a pool ref leaving the slot = trailing junk, not code
        if i.is_pool_ref and not base <= i.pool_addr < base + len(raw):
            ins = ins[:k]
            break
    pools = sorted({i.pool_addr for i in ins if i.is_pool_ref})
    end = pools[0] if pools else base + len(raw)
    code = [i for i in ins if i.addr < end]
    labels = {i.branch_target for i in code if i.is_branch and i.mnemonic in ("B",) or
              (i.is_branch and i.mnemonic.startswith("B") and i.mnemonic not in ("BL", "BLX", "BX") and i.operands.startswith("0x"))}
    labels = {t for t in labels if base <= t < base + len(raw)}
    out = ["    .syntax unified", "    .thumb", "    .section .text.entry", "    .global entry", "    .thumb_func", "entry:"]
    for i in code:
        if i.addr in labels or i.addr in pools:
            out.append(f".L{i.addr:08X}:")
        hw = int.from_bytes(i.raw[:2], "little")
        ops = i.operands
        if i.is_pool_ref:
            r = ops.split(",")[0].lower()
            if base % 4 == 2:       # gas aligns pools to the section start, which sits 2 off the real 4-alignment
                out.append(f"    .hword 0x{hw:04X}    @ ldr {r}, =pool 0x{i.pool_addr:08X}")
            else:
                out.append(f"    ldr {r}, .L{i.pool_addr:08X}")
        elif i.mnemonic == "BL":
            out.append(f"    bl 0x{i.branch_target:08X}")
        elif i.is_branch and ops.startswith("0x") and i.mnemonic != "BLX":
            t = i.branch_target
            out.append(f"    {i.mnemonic.lower()} " + (f".L{t:08X}" if base <= t < base + len(raw) else f"0x{t:08X}"))
        else:
            parts = [o.strip().replace("#-", "#") for o in ops.split(",")]
            if hw >> 11 == 0b00011 and hw >> 10 & 1 and (hw & 7) == (hw >> 3 & 7):
                # gas turns `adds rN, rN, #imm3` into the imm8 form; keep the original encoding
                out.append(f"    .hword 0x{hw:04X}    @ {i.mnemonic.lower()}s {ops.lower()}")
                continue
            if hw >> 13 == 0b001 and i.mnemonic in ("ADD", "SUB") and len(parts) == 3:   # imm8 form is 2-operand
                parts = parts[:1] + parts[2:]
            out.append(f"    {_mn(hw, i.mnemonic, len(parts))} {', '.join(parts).lower()}".rstrip())
    # data: everything from the code end to the last referenced pool word
    last = (pools[-1] + 4) if pools else end
    a = code[-1].addr + code[-1].size if code else base
    while a < last:
        if a in pools or a % 4 == 0 and a in pools:
            pass
        if a in pools:
            out.append(f".L{a:08X}:")
            out.append(f"    .word 0x{int.from_bytes(raw[a - base:a - base + 4], 'little'):08X}")
            a += 4
        else:
            out.append(f"    .hword 0x{int.from_bytes(raw[a - base:a - base + 2], 'little'):04X}")
            a += 2
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    text = gen(sys.argv[1])
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8").write(text)
    else:
        print(text)
