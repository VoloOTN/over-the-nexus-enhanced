"""Save storage for NEW card records (index >= 0x10D2) in the unused bits 6/7 of the per-card flag bytes.

The save keeps one owned-count nibble (master+0x906) and one flag byte (master+0x116F) per card_prop
record, sized for exactly 4306 records, and the SYS block cannot grow (its two copies are adjacent in
the save). Flag bits 6/7 are never used (wrappers cover bits 0..5 only; no save has them set), so new
card k = record 0x10D2 + k keeps its 10 bits there as "planes":

    field bit j (0..3 = count, 4 + b = flag bit b)  ->  byte FLG + 1 + j*64 + (k >> 1), bit 6 + (k & 1)

i.e. host records 1..640, up to 128 new cards. Every access to the two arrays lives in the arm9 block
0x0202AEF8..0x0202B49C, so the four accessors are rewritten IN PLACE at their original entry points
(same length, no cave) and the two inline "set bit 1" sites call the new flagset_idx. Stock records
behave byte-identically -- proven by `python -m otn_enhanced.cards.new_card_save`, which
runs stock and patched code side by side in scratch/thumbemu. Evidence: notes/new-cid-card-findings.md.

⚠️ Internal calls use `a.bl(address)`: ThumbAssembler sizes `insn("BL", "<label>")` as 2 bytes but
emits 4, which shifts every later label by 2.
"""
from __future__ import annotations

import hashlib
import struct

from otn_enhanced.asm.effect_shim import ThumbAssembler
from otn_enhanced.effects import common

MASTER = 0x0212406C
CNT = MASTER + 0x906
FLG = MASTER + 0x116F
OLD = 0x10D2                 # stock card_prop record count
P = 64                       # bytes per plane
CAPACITY = 2 * P             # new cards
HOST0 = FLG + 1              # plane bytes start at record 1's flag byte
CID2INT = 0x02029E1C

A = (0x0202AEF8, 0x0202AF48)   # cntget_idx(idx)
B = (0x0202AF60, 0x0202AFCC)   # cntset(cid, val)
C = (0x0202B0F8, 0x0202B190)   # flagset(cid, bit, on) ; flagget(cid, bit) at FLAGGET
D = (0x0202B0A0, 0x0202B0D4)   # clear flag bit 3 on every card
FLAGGET = 0x0202B154
INLINE = {0x0202B32E: 4, 0x0202B474: 5}    # inline "flag bit 1" sites -> register holding idx
INLINE_LEN = 24

STOCK_SHA1 = {A[0]: "021aa8253872", B[0]: "d1359b14c9e6", D[0]: "3c024a466499", C[0]: "52ed71ceabcc",
              0x0202B32E: "87919176f339", 0x0202B474: "b501fc86798e"}


def _nf_ptr(a):
    """r0 = k, r1 = plane -> r0 = byte address, r1 = mask. Clobbers r2, r3."""
    a.label("nf_ptr")
    a.insn("LSL", "R1, R1, #6")
    a.insn("LSR", "R2, R0, #1")
    a.insn("ADD", "R1, R1, R2")
    a.ldr_const(2, HOST0)
    a.insn("ADD", "R2, R2, R1")
    a.insn("MOV", "R1, #0x40")
    a.insn("LSL", "R3, R0, #31")
    a.insn("BEQ", "nf_even")
    a.insn("LSL", "R1, R1, #1")
    a.label("nf_even")
    a.insn("ADD", "R0, R2, #0")
    a.insn("BX", "LR")


def _region_c(pad: int, fa: int = C[0]):
    a = ThumbAssembler()
    # flagset(cid, bit, on)
    a.insn("PUSH", "{R4, R5, R6, LR}")
    a.insn("ADD", "R5, R1, #0")
    a.insn("ADD", "R6, R2, #0")
    a.ldr_const(4, 0x3FFF)
    a.insn("AND", "R0, R4")
    a.bl(CID2INT)
    a.insn("AND", "R0, R4")
    a.insn("B", "fs_common")
    # flagset_idx(idx, bit, on)
    a.label("flagset_idx")
    a.insn("PUSH", "{R4, R5, R6, LR}")
    a.insn("ADD", "R5, R1, #0")
    a.insn("ADD", "R6, R2, #0")
    a.label("fs_common")
    a.insn("ADD", "R1, R5, #0")
    a.bl(fa)
    a.insn("LDRB", "R2, [R0, #0]")
    a.insn("CMP", "R6, #0")
    a.insn("BEQ", "fs_clr")
    a.insn("ORR", "R2, R1")
    a.insn("B", "fs_st")
    a.label("fs_clr")
    a.insn("BIC", "R2, R1")
    a.label("fs_st")
    a.insn("STRB", "R2, [R0, #0]")
    a.insn("POP", "{R4, R5, R6, PC}")
    # flag_addr(idx, bit) -> r0 address, r1 mask; new cards fall through into nf_ptr
    a.label("flag_addr")
    a.ldr_const(2, OLD)
    a.insn("CMP", "R0, R2")
    a.insn("BGE", "fa_new")
    a.ldr_const(2, FLG)
    a.insn("ADD", "R0, R0, R2")
    a.insn("MOV", "R2, #1")
    a.insn("LSL", "R2, R1")
    a.insn("ADD", "R1, R2, #0")
    a.insn("BX", "LR")
    a.label("fa_new")
    a.insn("SUB", "R0, R0, R2")
    a.insn("ADD", "R1, #4")
    _nf_ptr(a)
    for _ in range(pad):
        a.raw(0x46C0)                                   # mov r8, r8
    # flagget(cid, bit) -- must start exactly at FLAGGET
    a.label("flagget")
    a.insn("PUSH", "{R3, R4, R5, LR}")
    a.insn("ADD", "R5, R1, #0")
    a.ldr_const(4, 0x3FFF)
    a.insn("AND", "R0, R4")
    a.bl(CID2INT)
    a.insn("AND", "R0, R4")
    a.insn("ADD", "R1, R5, #0")
    a.bl(fa)
    a.insn("LDRB", "R0, [R0, #0]")
    a.insn("TST", "R0, R1")
    a.insn("BEQ", "fg_zero")
    a.insn("MOV", "R0, #1")
    a.insn("POP", "{R3, R4, R5, PC}")
    a.label("fg_zero")
    a.insn("MOV", "R0, #0")
    a.insn("POP", "{R3, R4, R5, PC}")
    return a


def _region_a(nf: int):
    a = ThumbAssembler()
    a.ldr_const(1, OLD)
    a.insn("CMP", "R0, R1")
    a.insn("BGE", "new")
    a.ldr_const(1, CNT)
    a.insn("LSR", "R2, R0, #1")
    a.insn("LDRB", "R2, [R1, R2]")
    a.insn("LSR", "R0, R0, #1")                       # carry = odd
    a.insn("BCC", "lo")
    a.insn("LSR", "R2, R2, #4")
    a.label("lo")
    a.insn("MOV", "R0, #0xF")
    a.insn("AND", "R0, R2")
    a.insn("BX", "LR")
    a.label("new")
    a.insn("PUSH", "{R4, R5, R6, LR}")
    a.insn("SUB", "R4, R0, R1")                       # k
    a.insn("MOV", "R5, #0")
    a.insn("MOV", "R6, #0")
    a.label("loop")
    a.insn("ADD", "R0, R4, #0")
    a.insn("ADD", "R1, R6, #0")
    a.bl(nf)
    a.insn("LDRB", "R0, [R0, #0]")
    a.insn("TST", "R0, R1")
    a.insn("BEQ", "skip")
    a.insn("MOV", "R0, #1")
    a.insn("LSL", "R0, R6")
    a.insn("ORR", "R5, R0")
    a.label("skip")
    a.insn("ADD", "R6, #1")
    a.insn("CMP", "R6, #4")
    a.insn("BLT", "loop")
    a.insn("ADD", "R0, R5, #0")
    a.insn("POP", "{R4, R5, R6, PC}")
    return a


def _region_b(nf: int):
    a = ThumbAssembler()
    a.insn("PUSH", "{R4, R5, R6, LR}")
    a.insn("ADD", "R4, R1, #0")                       # val
    a.ldr_const(5, 0x3FFF)
    a.insn("AND", "R0, R5")
    a.bl(CID2INT)
    a.insn("AND", "R0, R5")
    a.ldr_const(1, OLD)
    a.insn("CMP", "R0, R1")
    a.insn("BGE", "new")
    a.ldr_const(1, CNT)
    a.insn("LSR", "R2, R0, #1")
    a.insn("ADD", "R1, R1, R2")
    a.insn("LDRB", "R2, [R1, #0]")
    a.insn("LSL", "R4, R4, #28")
    a.insn("LSR", "R0, R0, #1")                       # carry = odd
    a.insn("BCS", "odd")
    a.insn("LSR", "R4, R4, #28")
    a.insn("MOV", "R3, #0xF0")
    a.insn("B", "st")
    a.label("odd")
    a.insn("LSR", "R4, R4, #24")
    a.insn("MOV", "R3, #0xF")
    a.label("st")
    a.insn("AND", "R2, R3")
    a.insn("ORR", "R2, R4")
    a.insn("STRB", "R2, [R1, #0]")
    a.insn("POP", "{R4, R5, R6, PC}")
    a.label("new")
    a.insn("SUB", "R5, R0, R1")                       # k
    a.insn("MOV", "R6, #0")
    a.label("loop")
    a.insn("ADD", "R0, R5, #0")
    a.insn("ADD", "R1, R6, #0")
    a.bl(nf)
    a.insn("LDRB", "R2, [R0, #0]")
    a.insn("ORR", "R2, R1")
    a.insn("ADD", "R3, R4, #0")
    a.insn("LSR", "R3, R6")
    a.insn("LSR", "R3, R3, #1")                       # carry = bit j of val
    a.insn("BCS", "keep")
    a.insn("BIC", "R2, R1")
    a.label("keep")
    a.insn("STRB", "R2, [R0, #0]")
    a.insn("ADD", "R6, #1")
    a.insn("CMP", "R6, #4")
    a.insn("BLT", "loop")
    a.insn("POP", "{R4, R5, R6, PC}")
    return a


def _region_d():
    a = ThumbAssembler()
    a.ldr_const(0, FLG - 1)                           # count-down: indexes base .. base+n-1
    a.ldr_const(2, OLD)
    a.insn("MOV", "R3, #0xF7")
    a.label("l1")
    a.insn("LDRB", "R1, [R0, R2]")
    a.insn("AND", "R1, R3")
    a.insn("STRB", "R1, [R0, R2]")
    a.insn("SUB", "R2, #1")
    a.insn("BNE", "l1")
    a.insn("ADD", "R0, #0xFF")                        # -> HOST0 + 7*P - 1
    a.insn("ADD", "R0, #0xC2")
    a.insn("MOV", "R2, #0x40")
    a.insn("MOV", "R3, #0x3F")
    a.label("l2")
    a.insn("LDRB", "R1, [R0, R2]")
    a.insn("AND", "R1, R3")
    a.insn("STRB", "R1, [R0, R2]")
    a.insn("SUB", "R2, #1")
    a.insn("BNE", "l2")
    a.insn("BX", "LR")
    return a


def build() -> tuple[dict[int, bytes], int, int]:
    """({addr: bytes}, nf_ptr, flagset_idx) -- every blob exactly its region's stock length."""
    assert 0xFF + 0xC2 == 1 + 7 * P
    for pad in range(64):
        labels = _region_c(pad)._layout()[1]
        if C[0] + labels["flagget"] == FLAGGET:
            break
    else:
        raise AssertionError("flagget cannot be placed at its entry")
    a = _region_c(pad, C[0] + labels["flag_addr"])
    assert a._layout()[1] == labels
    nf, fsi = C[0] + labels["nf_ptr"], C[0] + labels["flagset_idx"]
    out = {C[0]: a.assemble(C[0]), A[0]: _region_a(nf).assemble(A[0]),
           B[0]: _region_b(nf).assemble(B[0]), D[0]: _region_d().assemble(D[0])}
    for lo, hi in (A, B, C, D):
        assert len(out[lo]) <= hi - lo, f"0x{lo:08X}: {len(out[lo])} > {hi - lo}"
        out[lo] += b"\xC0\x46" * ((hi - lo - len(out[lo])) // 2)
    for site, reg in INLINE.items():
        blob = struct.pack("<3H", 0x1C00 | (reg << 3), 0x2101, 0x2201) + common.bl(site + 6, fsi)
        out[site] = blob + b"\xC0\x46" * ((INLINE_LEN - len(blob)) // 2)
    return out, nf, fsi


def apply(a9, n_new: int) -> None:
    """Patch an arm9 Ov view (from enhanced_edition_definitive.arm9.arm9_edit) in place."""
    assert n_new <= CAPACITY, f"{n_new} new cards > plane capacity {CAPACITY}"
    blobs, _, _ = build()
    for addr, blob in blobs.items():
        got = hashlib.sha1(a9.blob(addr, len(blob))).hexdigest()[:12]
        assert got == STOCK_SHA1[addr], f"arm9 0x{addr:08X} is not stock ({got}) -- already patched?"
        a9.write(addr, blob)


def applied(a9) -> bool:
    return all(a9.blob(addr, len(b)) == b for addr, b in build()[0].items())


# ---------------------------------------------------------------------------------------------------
# Self-check: stock vs patched in the Thumb emulator, over a real SYS block.
# ---------------------------------------------------------------------------------------------------
def _selfcheck(rom_path="data/over_the_nexus/working/rom_ov3_compact.nds",
               sav_path="data/over_the_nexus/working/rom_all_patches.sav") -> int:
    import importlib.util, random
    import ndspy.rom, ndspy.code
    spec = importlib.util.spec_from_file_location("thumbemu", "scratch/thumbemu.py")
    te = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(te)                       # by path: scratch/dis.py shadows the stdlib

    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    stock = bytes(ndspy.code.MainCodeFile(bytes(rom.arm9), 0x02000000).sections[0].data)
    patched = bytearray(stock)
    blobs, nf, fsi = build()
    for addr, blob in blobs.items():
        patched[addr - 0x02000000:addr - 0x02000000 + len(blob)] = blob
    sysblk = open(sav_path, "rb").read()[0x8500:0x8500 + 0x3338]
    # an intid that also maps 0x25E3 -> record OLD (k = 0)
    from otn_enhanced.rom.pac import parse_format_v1
    b2 = rom.getFileByName("Data_arc_pac/bin2.pac")
    f = next(x for x in parse_format_v1(b2, "bin2").files if x.get_clean_name() == "card_intid.bin")
    intid = bytes(b2[f.address:f.address + f.size])
    intid += bytes(0x25E3 - 0x24E9 << 1) + struct.pack("<H", 0x8000 | OLD)

    class Ram:
        def __init__(self, img, end):
            self.b = bytearray(0x400000)
            self.b[:len(img)] = img
            struct.pack_into("<I", self.b, 0x29E44, end)
            self.b[MASTER - 0x02000000:MASTER - 0x02000000 + len(sysblk)] = sysblk
            struct.pack_into("<I", self.b, 0x121A6C, 0x02300000)
            struct.pack_into("<I", self.b, 0x30003C, 0x02310000)
            self.b[0x310000:0x310000 + len(intid)] = intid

        def u8(self, a):
            return self.b[a - 0x02000000]

    def mem(img, end):
        return te.Mem(Ram(img, end))

    def run(m, *args):
        return te.Emu(m).run(args[0], args[1:])

    def sysb(m):
        out = bytearray(m.ss.b[MASTER - 0x02000000:MASTER - 0x02000000 + 0x3338])
        for a, v in m.w.items():
            if MASTER <= a < MASTER + 0x3338:
                out[a - MASTER] = v
        return out

    fails = 0
    cids = [0xD48 + i for i in range(len(intid) // 2)
            if 0 < (struct.unpack_from("<H", intid, i * 2)[0] & 0x3FFF) < OLD]
    s, p = mem(stock, 0x24E9), mem(bytes(patched), 0x25E4)
    for cid in cids:                                   # exhaustive getters
        fails += run(s, 0x0202AF48, cid) != run(p, 0x0202AF48, cid)
        fails += sum(run(s, FLAGGET, cid, b) != run(p, FLAGGET, cid, b) for b in range(6))
    rng = random.Random(1)
    for _ in range(400):                               # random writers: whole SYS must match
        cid = rng.choice(cids)
        args = rng.choice([(0x0202AF60, cid, rng.randrange(10)), (0x0202B0F8, cid, rng.randrange(6), rng.randrange(2)),
                           (0x0202AFCC, cid, rng.randrange(1, 4)), (0x0202B030, cid, rng.randrange(1, 4)), (0x0202B0A0,)])
        s, p = mem(stock, 0x24E9), mem(bytes(patched), 0x25E4)
        run(s, *args); run(p, *args)
        fails += sysb(s) != sysb(p)
    m = mem(bytes(patched), 0x25E4)                    # new card 0x25E3 (k = 0)
    run(m, 0x0202AF60, 0x25E3, 7); fails += run(m, 0x0202AF48, 0x25E3) != 7
    run(m, 0x0202AFCC, 0x25E3, 5); fails += run(m, 0x0202AF48, 0x25E3) != 9
    run(m, 0x0202B030, 0x25E3, 4); fails += run(m, 0x0202AF48, 0x25E3) != 5
    for b in range(6):
        run(m, 0x0202B0F8, 0x25E3, b, 1); fails += run(m, FLAGGET, 0x25E3, b) != 1
        run(m, 0x0202B0F8, 0x25E3, b, 0); fails += run(m, FLAGGET, 0x25E3, b) != 0
    before = sysb(m)
    for k in range(CAPACITY):
        run(m, fsi, OLD + k, k % 6, 1)
    run(m, 0x0202B0A0)
    after = sysb(m)
    for k in range(CAPACITY):
        for b in range(6):
            got = after[HOST0 - MASTER + (4 + b) * P + (k >> 1)] >> (6 + (k & 1)) & 1
            fails += got != (b == k % 6 and b != 3)
    fails += run(m, 0x0202AEF8, OLD) != 5
    o = FLG - MASTER
    fails += any(before[o + i] & 0x37 != after[o + i] & 0x37 for i in range(OLD))
    fails += before[0x906:0x906 + 2153] != after[0x906:0x906 + 2153]
    print(f"new_card_save self-check: {len(cids)} stock cards exhaustive, 400 random writes, "
          f"{CAPACITY} new cards x 6 flags -> {fails} failure(s)")
    return fails


if __name__ == "__main__":
    raise SystemExit(1 if _selfcheck() else 0)
