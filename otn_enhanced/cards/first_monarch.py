"""The First Monarch (Continuous Trap, a native TRAP MONSTER) on Tiki Soul 0x249B.  TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "Special Summon this card as an Effect Monster (Fiend-Type/DARK/Level 6/ATK 1000/DEF 2400). (This card is also still a Trap Card.) If Summoned this way: You can discard 1 card, then
     declare 1 Attribute; this card becomes that Attribute, and can be treated as 2 Tributes for the Tribute Summon of a monster with the same Attribute as this card. If this card was
     Summoned this way, you cannot Special Summon monsters, except monsters with this card's Attribute."

Donor technique on a NATIVE trap monster (notes/first-monarch-findings.md): the engine already ships the scaffold for Tiki Soul -- the cls0 record {0x0221853D SS-as-monster, 0, 0x021F6EA5},
the ARM9 trap-monster list 0x0209BA7A (is-trap-monster thunk 0x02023378) and a stat arm in 0x021B3790.  This module
  * rewrites Tiki Soul's stat arm (Rock/LIGHT/4/1000/1800 -> Fiend/DARK/6/1000/2400; the DEF literal 0x708 is shared with two other arms, so the arm is re-assembled with `movs #0x4B ; lsls #5`),
  * neutralises Tiki Soul's own three effect arms (ov3 literals 0x249B -> the dead phantom 0x1449), and
  * joins the "Monarch" set list (tenacity.MONARCH).
BUILT: the Trap Monster itself (clause 1).  NOT BUILT yet: the discard + declare-an-Attribute effect, the 2-Tribute clause and the Special Summon restriction.

    uv run python -m otn_enhanced.cards.first_monarch
"""
from __future__ import annotations

import struct
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import Compiled

FM = 0x249B
DEAD = 0x1449                                    # a phantom cid no card owns: the neutralised arms search for it and find nothing
STAT_ARM = 0x021B3892                            # Tiki Soul's arm in the trap-monster stat tree 0x021B3790
STAT_LEN = 26                                    # the stock arm (24 B) + the padding nop after it
# the stock arm: movs #6 ; strh [r1,#4] ; movs #1 ; strh [r1,#6] ; movs #4 ; strh [r1,#0xe] ; movs #0xfa ; lsls #2 ; str [r1,#0x18] ; ldr r0,=0x708 ; str [r1,#0x1c] ; bx lr ; nop
_HW = (0x2003, 0x8088, 0x2002, 0x80C8, 0x2006, 0x81C8, 0x20FA, 0x0080, 0x6188, 0x204B, 0x0140, 0x61C8, 0x4770)
STAT_NEW = b"".join(struct.pack("<H", h) for h in _HW)   # race 3 Fiend, attribute 2 DARK, Level 6, ATK 1000, DEF 2400 (little-endian halfwords: a hex-string version of this once had the strh bytes swapped = ldrh = a data-abort freeze)
_DIS = [f"{i.mnemonic} {i.op_str}" for i in __import__("capstone").Cs(__import__("capstone").CS_ARCH_ARM, __import__("capstone").CS_MODE_THUMB).disasm(STAT_NEW, STAT_ARM)]
assert _DIS == ["movs r0, #3", "strh r0, [r1, #4]", "movs r0, #2", "strh r0, [r1, #6]", "movs r0, #6", "strh r0, [r1, #0xe]", "movs r0, #0xfa", "lsls r0, r0, #2",
                "str r0, [r1, #0x18]", "movs r0, #0x4b", "lsls r0, r0, #5", "str r0, [r1, #0x1c]", "bx lr"], _DIS
ARM_LITERALS = (0x021CCB88, 0x021CEDFC, 0x021CF2EC)      # Tiki Soul's effect arms: `ldr rX,=0x249B ; bl 0x021ABECC(side, cid, zone)` zone searches
TREE_LITERAL = 0x021B38C0                                  # the stat tree's own compare: stays

# The stat tree's other edits (notes/first-monarch-findings.md, session 2): (addr, stock halfwords, new halfwords, intended disassembly).
# 1. EXIT FIX: the tree's two no-match exits branched to 0x021B38A8, the stock arm's `bx lr`, which the rewrite above turned into `str r0,[r1,#0x1c]` -> retarget them to the `bx lr` @0x021B37E0.
# 2. The Prime Monarch 0x14CF (its GY half Special Summons it as a Fairy / LIGHT / Level 5 / 1000 / 2400 monster): the dead phantom 0x0EA9's route and arm become 0x14CF's.
#    The arm ends in `b 0x021B389E` = the First Monarch arm's ATK 1000 / DEF 2400 tail above.
PRIME = 0x14CF
TREE_EDITS = (
    (0x021B37D2, (0xDC69,), (0xDC05,), ["bgt #0x21b37e0"]),
    (0x021B37D8, (0xDB66,), (0xDB02,), ["blt #0x21b37e0"]),
    (0x021B37A0, (0xDC04, 0xDA27, 0x4A43, 0x4290, 0xD01B, 0x4770, 0x3BF9, 0x4298), (0xD028, 0x4A44, 0x4290, 0xD01C, 0x3BF9, 0x4298, 0xD02E, 0x4770),
     ["beq #0x21b37f4", "ldr r2, [pc, #0x110]", "cmp r0, r2", "beq #0x21b37e2", "subs r3, #0xf9", "cmp r0, r3", "beq #0x21b380c", "bx lr"]),
    (0x021B37E2, (0x2012, 0x8088, 0x2001, 0x80C8, 0x81C8, 0x2000, 0x6188), (0x2011, 0x8088, 0x2001, 0x80C8, 0x2005, 0x81C8, 0xE056),
     ["movs r0, #0x11", "strh r0, [r1, #4]", "movs r0, #1", "strh r0, [r1, #6]", "movs r0, #5", "strh r0, [r1, #0xe]", "b #0x21b389e"]),
)
PRIME_LITERAL = 0x021B38B4                                 # was 0x0EA9 (the only load: `ldr r2` @0x021B37A2 after the reroute)
TM_LIST, TM_COUNT = 0x0209BA7A, 9                          # ARM9 trap-monster list (sorted u16; the count is an immediate in the thunk 0x02023378)
TM_STOCK = (0x0EA9, 0x1472, 0x1636, 0x172F, 0x1809, 0x1ACA, 0x21ED, 0x249A, 0x249B)
TM_NEW = tuple(sorted((PRIME,) + TM_STOCK[1:]))


def _hw(t) -> bytes:
    return b"".join(struct.pack("<H", h) for h in t)


def _dis(blob: bytes, addr: int) -> list[str]:
    import capstone
    return [f"{i.mnemonic} {i.op_str}" for i in capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB).disasm(blob, addr)]


for _a, _old, _new, _want in TREE_EDITS:
    assert _dis(_hw(_new), _a) == _want, (_a, _dis(_hw(_new), _a))


def _arm9_list(rom):
    from otn_enhanced.effects import ov5_cave as O5
    mc, sec = O5._arm9_main(rom)
    a = TM_LIST - 0x02000000
    assert a + 2 * TM_COUNT <= len(sec.data), "trap-monster list outside the ARM9 main section"
    return mc, sec, a


class the_first_monarch:
    cid: int = FM

    def compile(self, view=None) -> Compiled:
        def install(rom, v):
            cur = bytes(v.blob(STAT_ARM, STAT_LEN))
            if cur != STAT_NEW:
                assert cur[:2] == bytes.fromhex("0620") and cur[22:24] == bytes.fromhex("7047") and cur[24:] == bytes.fromhex("c046"), f"stat arm @{STAT_ARM:#x} is {cur.hex()}"
                v.write(STAT_ARM, STAT_NEW)
            for a in ARM_LITERALS:
                cur = struct.unpack("<I", bytes(v.blob(a, 4)))[0]
                assert cur in (FM, DEAD), f"literal @{a:#x} is {cur:#x}, expected 0x{FM:04X}"
                v.write(a, struct.pack("<I", DEAD))
            assert struct.unpack("<I", bytes(v.blob(TREE_LITERAL, 4)))[0] == FM, "the stat tree's compare literal moved"
            for a, old, new, _ in TREE_EDITS:
                cur = bytes(v.blob(a, 2 * len(new)))
                assert cur in (_hw(old), _hw(new)), f"stat tree @{a:#x} is {cur.hex()}"
                v.write(a, _hw(new))
            cur = struct.unpack("<I", bytes(v.blob(PRIME_LITERAL, 4)))[0]
            assert cur in (0x0EA9, PRIME), f"tree literal @{PRIME_LITERAL:#x} is {cur:#x}"
            v.write(PRIME_LITERAL, struct.pack("<I", PRIME))
            mc, sec, a = _arm9_list(rom)
            d = bytearray(sec.data)
            cur = struct.unpack_from(f"<{TM_COUNT}H", d, a)
            assert cur in (TM_STOCK, TM_NEW), f"trap-monster list is {[hex(x) for x in cur]}"
            struct.pack_into(f"<{TM_COUNT}H", d, a, *TM_NEW)
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def check(c, rom, v):
            for a, _, new, want in TREE_EDITS:
                c.eq(_dis(bytes(v.blob(a, 2 * len(new))), a), want, f"stat tree @0x{a:08X} DISASSEMBLES as intended")
            c.eq(struct.unpack("<I", bytes(v.blob(PRIME_LITERAL, 4)))[0], PRIME, "stat tree literal routes 0x14CF (was the phantom 0x0EA9)")
            mc, sec, a = _arm9_list(rom)
            c.eq(struct.unpack_from(f"<{TM_COUNT}H", sec.data, a), TM_NEW, "ARM9 trap-monster list: 0x0EA9 -> 0x14CF, sorted")
            c.eq(bytes(v.blob(STAT_ARM, STAT_LEN)), STAT_NEW, "Tiki Soul's stat arm now says Fiend / DARK / Level 6 / ATK 1000 / DEF 2400")
            import capstone
            dis = [f"{i.mnemonic} {i.op_str}" for i in capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB).disasm(bytes(v.blob(STAT_ARM, STAT_LEN)), STAT_ARM)]
            c.eq(dis, _DIS, "the ROM's stat arm DISASSEMBLES to the intended stores (independent of the byte constant: the first build had strh bytes swapped into ldrh)")
            for a in ARM_LITERALS:
                c.eq(struct.unpack("<I", bytes(v.blob(a, 4)))[0], DEAD, f"Tiki Soul effect-arm literal @0x{a:08X} neutralised")
            c.eq(struct.unpack("<I", bytes(v.blob(TREE_LITERAL, 4)))[0], FM, "the stat tree still routes 0x249B to the (rewritten) arm")

        return Compiled(stubs=(), installs=(install,), checks=(check,))


SPEC = the_first_monarch()
main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_first_monarch.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
