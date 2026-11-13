"""Tessera the Primal Squire T1 (hand ignition) on Toon Alligator 0x1123 -- the second half of cards/tessera.py.  TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "You can reveal 1 "Monarch" Spell/Trap in your hand; Special Summon this card from your hand."  (once per turn)

A VIRTUAL cls2 hand record (Immortal Phoenix Gearfried C1's shape) reached through the new find_event_handler PRE-DISPATCH hook (effects/prefind_hook.py), because Tessera's real cls2 record
(T3, the sent-to-GY trigger) would otherwise shadow it.  COND / COST / RES in tessera_hand.c; the reveal runs over the virtual hand row 0xFFD5 {Monarch set code 0x6D, hand set-code
handler 0x0223CB39, Spell|Trap}, chosen by an H2 front while the cost machine runs ([0x0229AAFC+0x7C] != 0); an ARM9 H4 front offers the effect from the hand.  Apply AFTER cards/tessera.py.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from otn_enhanced import dsl
from otn_enhanced.asm.cc import compile_c
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.cards import tenacity as TN
from otn_enhanced.dsl import Compiled
from otn_enhanced.effects import ov5_cave as O5, prefind_hook
from otn_enhanced.effects.common import bl as common_bl, ov3_bl_target

TS = 0x1123
OUT = "data/over_the_nexus/working/rom_tessera_hand.nds"
C_DIR = Path(__file__).resolve().parent / "c"
IDX_HAND = 0xFFD5
HAND_SETCODE, WORD_ST = 0x0223CB39, 0x0000000C
STATE = 0x0229AAFC
H2_SITE, H3_SITE, H3_RESUME = 0x02243F24, 0x02243F62, 0x02243F71
H4_SITE = 0x02023566
for _v in (HAND_SETCODE, H3_RESUME):
    assert _v & 1

S = {n: getattr(O5, f"CAVE_T1_{n}") for n in ("COND", "COST", "RES", "VREC", "ROWS", "H2", "H3", "H4")}
RESERVE = {"COND": 0x80, "COST": 0x30, "RES": 0x40, "VREC": 0x20, "ROWS": 0x10, "H2": 0x30, "H3": 0x30, "H4": 0x20}
_DN = O5.dc_next()
H2_PREV, H3_PREV, H4_PREV = _DN[O5.CAVE_T1_H2], _DN[O5.CAVE_T1_H3], _DN[O5.CAVE_T1_H4]
ROWS_BLOB = struct.pack("<HHII", TS, TN.MONARCH_SET, HAND_SETCODE, WORD_ST) + bytes(4)
S5 = S["VREC"] + 0x18
VREC_BLOB = struct.pack("<HHIIIII", TS, 0, S["RES"] | 1, 0, S["COND"] | 1, S["COST"] | 1, S5 | 1) + bytes.fromhex("0120" "7047") + bytes(4)   # +0x18: movs r0,#1 ; bx lr (the +14 stub)
assert len(VREC_BLOB) == 0x1E + 2


def _fit(blob, slot):
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    assert_thumb1_only(blob, S[slot])
    return blob


def _c(stub, slot):
    return _fit(compile_c(C_DIR / "tessera_hand.c", S[slot], {"STUB": stub}), slot)


def h2_front():
    b = EffectBuilder()
    b.ldr_const(0, TS)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, STATE)
    b.insn("LDR", "R0, [R0, #0x7C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "miss")
    b.ldr_const(0, IDX_HAND)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _fit(b.assemble(S["H2"], pad="nop"), "H2")


def h3_front():
    b = EffectBuilder()
    b.ldr_const(0, IDX_HAND)
    b.insn("CMP", "R6, R0")
    b.insn("BNE", "prev")
    b.ldr_const(0, S["ROWS"])
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, H3_PREV | 1)
    b.insn("BX", "R0")
    return _fit(b.assemble(S["H3"], pad="nop"), "H3")


def h4_front():
    b = EffectBuilder()
    b.ldr_const(3, TS)
    b.insn("CMP", "R0, R3")
    b.insn("BNE", "prev")
    b.insn("MOV", "R0, #0x1")
    b.insn("BX", "LR")
    b.label("prev")
    b.ldr_const(3, H4_PREV | 1)
    b.insn("BX", "R3")
    return _fit(b.assemble(S["H4"], pad="nop"), "H4")


def _front_at(view, site, prev, mine, what):
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _reaches(view, site, slot):
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


class tessera_hand_ignition:
    cid = TS

    def blobs(self):
        return {"COND": (S["COND"], _c("T1_COND", "COND"), "T1 +0C cond (C)"), "COST": (S["COST"], _c("T1_COST", "COST"), "T1 +10 reveal cost (C)"),
                "RES": (S["RES"], _c("T1_RES", "RES"), "T1 +04 resolver (C)"), "VREC": (S["VREC"], VREC_BLOB, "T1 virtual cls2 hand record"),
                "ROWS": (S["ROWS"], ROWS_BLOB, "virtual criteria row 0xFFD5 (hand Monarch Spell/Trap)"),
                "H2": (S["H2"], h2_front(), "H2 front"), "H3": (S["H3"], h3_front(), "H3 front"), "H4": (S["H4"], h4_front(), "ARM9 H4 hand-offer front")}

    def compile(self, view=None):
        prefind_hook.register(TS, S["VREC"], "Tessera T1 hand ignition")
        blobs = self.blobs()
        for key, (addr, blob, _) in blobs.items():
            if key not in ("ROWS", "VREC"):
                assert_thumb1_only(blob, addr)
        group = TN.GROUPS[0]

        def install(rom, v):
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            prefind_hook.install(rom, v)
            group.install(rom, v)
            mc, sec = O5._arm9_main(rom)
            d = bytearray(sec.data)
            a = H4_SITE - 0x02000000
            assert bytes(d[a:a + 4]) in (common_bl(H4_SITE, H4_PREV), common_bl(H4_SITE, S["H4"])), f"ARM9 H4 site {H4_SITE:#x} is not the expected front"
            d[a:a + 4] = common_bl(H4_SITE, S["H4"])
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Tessera T1 {slot} front")
            for key, (addr, blob, _) in blobs.items():
                c.ok(O5.read_cave(rom, addr, len(blob)) == blob, f"{key} stub present @0x{addr:08X} ({len(blob)} B)")
            prefind_hook.verify(rom, v, lambda ok, msg: c.ok(bool(ok), msg))
            mc, sec = O5._arm9_main(rom)
            a = H4_SITE - 0x02000000
            c.ok(bytes(sec.data[a:a + 4]) in {common_bl(H4_SITE, f) for f in O5.dc_ahead_of(S["H4"])}, "ARM9 bl @0x02023566 -> H4 front (or a later owner's front ahead of it)")
            group.check(c, rom, v)

        return Compiled(tuple(blobs.values()), installs=(install,), checks=(check,))


SPEC = tessera_hand_ignition()
main, verify = dsl.make(SPEC, None, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
