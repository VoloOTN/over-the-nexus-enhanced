"""The SHARED code-0x13 "selected as an attack target" gate -- owned by no single card.

Split out of maiden_eyes_of_blue (PART A3) on 2026-10-08 so the vanilla+ half of the
build (Ninishi, Haipa) gets the gate WITHOUT Maiden with Eyes of Blue. Every user calls
``install(ov, cid)``: the first caller hooks 0x021C6624 and writes the gate, every caller
appends its own cid to the admit list. Order-independent; the gate bytes are unchanged.

Mechanism (see maiden_eyes_of_blue PART A3): the code-0x13 post at 0x021C6798 is
guarded by a per-cid switch at 0x021C6620 that accepts only 26 cids. The gate replaces the
switch's `bl 0x021A37D8` (cid_at) and remaps any admitted cid to ACCEPTED, a phantom the
native switch already accepts. Lives in the ov3 pool, so it also runs in puzzles.
"""
from __future__ import annotations

import struct

from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.rom.overlay_io import RAM_BASE
from otn_enhanced.effects import cave3
from otn_enhanced.effects.common import ov3_off as _off

BL_SITE = 0x021C6624          # the `bl 0x021A37D8` inside 0x021C6620
HELPER = 0x021A37D8           # cid_at(side, slot) -- the original callee
ACCEPTED = 0x1CB1             # a PHANTOM cid the native switch already accepts
GATE = cave3.CAVE3_ATKTGT_GATE
LIST = cave3.CAVE3_ATKTGT_LIST
LIST_CAP = 3                  # the 8-byte slot: 3 u16 cids + terminator


def _bl(src: int, dst: int) -> bytes:
    """ARMv4T two-halfword BL (Thumb-1 long branch-with-link)."""
    off = dst - (src + 4)
    assert -(1 << 22) <= off < (1 << 22), f"BL 0x{src:08X}->0x{dst:08X} out of range: {off:#x}"
    return struct.pack("<HH", 0xF000 | ((off >> 12) & 0x7FF), 0xF800 | ((off >> 1) & 0x7FF))




def gate_code(base: int, lst: int = LIST) -> bytes:
    """Same ABI as cid_at; returns the cid in r0, remapped to ACCEPTED if it is in *lst*."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.ldr_const(4, HELPER | 1)
    b.insn("BLX", "R4")
    b.ldr_const(4, lst)
    b.label("scan")
    b.insn("LDRH", "R5, [R4, #0]")
    b.insn("CMP", "R5, #0")
    b.insn("BEQ", "out")
    b.insn("CMP", "R5, R0")
    b.insn("BEQ", "hit")
    b.insn("ADD", "R4, #2")
    b.insn("B", "scan")
    b.label("hit")
    b.ldr_const(0, ACCEPTED)
    b.label("out")
    b.insn("POP", "{R4, R5, PC}")
    return b.assemble(base, pad="nop")


def admitted(ov) -> list[int]:
    out = []
    for i in range(LIST_CAP):
        c = struct.unpack_from("<H", ov, _off(LIST) + 2 * i)[0]
        if c == 0:
            break
        out.append(c)
    return out


def hooked(ov) -> bool:
    return bytes(ov[_off(BL_SITE):_off(BL_SITE) + 4]) == _bl(BL_SITE, GATE)


def install(ov: bytearray, cid: int) -> None:
    """Hook + gate (once) and admit *cid*. Needs step 0 (ov3_compact) on *ov*."""
    from otn_enhanced.effects.tg_table import _put3
    _put3(ov, GATE, gate_code(GATE))
    if not hooked(ov):
        cur = bytes(ov[_off(BL_SITE):_off(BL_SITE) + 4])
        assert cur == _bl(BL_SITE, HELPER), (
            f"0x{BL_SITE:08X} is neither the stock `bl 0x{HELPER:08X}` nor our gate "
            f"(found {cur.hex()}) -- the gate moved, re-run the switch simulation")
        ov[_off(BL_SITE):_off(BL_SITE) + 4] = _bl(BL_SITE, GATE)
    cids = admitted(ov)
    if cid not in cids:
        assert len(cids) < LIST_CAP, f"attack-target admit list full: {[hex(c) for c in cids]}"
        struct.pack_into("<H", ov, _off(LIST) + 2 * len(cids), cid)
    print(f"   attack-target gate @0x{BL_SITE:08X} -> 0x{GATE:08X}, "
          f"admits {[hex(c) for c in admitted(ov)]}")
