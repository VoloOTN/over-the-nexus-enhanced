"""Amazoness Heirloom (Equip Spell) on Molting Escape 0x2124.

    "Equip only to an "Amazoness" monster. Once per turn, that monster cannot be destroyed by battle.
     After damage calculation, if the equipped monster attacks a monster: Destroy the attacked monster."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, CLS1, Compiled, Edit, _in_ov5, _patch_bytes
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_shim import _bl as _shim_bl
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
import struct


_EQUIP_TGT_ARM = 0x021D7F38


_EQUIP_TGT_STOCK = bytes.fromhex("04982105084200d100247ce5")   # ldr r0,[sp,#0x10]; Reptile tst; ...


_EQUIP_TGT_RETURN = 0x021D817A                                   # add sp,#0x1c ; pop {r4-r7,pc}


@dataclass(frozen=True)
class equip_only_to_set_code:
    """'Equip only to a "<archetype>" monster': the donor's equip target arm (reached only from 0x021D78A8)
    is rewritten as `adds r0,r5,#0 ; bl <set-code thunk> ; b return`, the Ancient Gear arm 0x021D7C60 shape."""
    thunk: int                 # has_set_code thunk for the archetype (Amazoness = set code 0x05, 0x020237C8)

    def _arm(self) -> bytes:
        off = (_EQUIP_TGT_RETURN - (_EQUIP_TGT_ARM + 6 + 4)) // 2
        assert -1024 <= off < 1024
        return (b"\x28\x1c" + _shim_bl(_EQUIP_TGT_ARM + 2, self.thunk)
                + struct.pack("<H", 0xE000 | (off & 0x7FF)))

    def compile(self, view, cid) -> Compiled:
        arm = self._arm()

        def install(rom, view):
            cur = view.blob(_EQUIP_TGT_ARM, 12)
            assert cur in (_EQUIP_TGT_STOCK, arm + _EQUIP_TGT_STOCK[8:]), "equip target arm not stock"
            view.write(_EQUIP_TGT_ARM, arm)

        def check(c, rom, view):
            c.eq(view.blob(_EQUIP_TGT_ARM, 8), arm, "equip target arm = adds/bl set-code thunk/b return")

        return Compiled(installs=(install,), checks=(check,))


_ADC_SITE = 0x022517C6


_ADC_STOCK = bytes.fromhex("25498842")                          # ldr r1,=0x2007 ; cmp r0,r1


_THORN = 0x2007


_FIST_CLS1 = (0x1ABC, 0, 0x022048FD, 0x021E1479, 0, 0, 0)       # Ancient Gear Fist's destroy record, cls1[594]


_FIST_CLS1_ADDR = 0x02289884


_FIST_BATTLED_ARM = 0x021E1577   # uses r5 side, r6 zone, r7 desc; pops {r3-r7,pc}


_ZONE_PRED = 0x021D6E41          # (desc, side, zone, mask) -> bool


_EODS_BGE = 0x0225223E           # End-of-Damage-Step walker: donor-only branch queue -> skip


_EODS_STOCK, _EODS_NEW = struct.pack("<H", 0xDA10), struct.pack("<H", 0xDA1A)


@dataclass(frozen=True)
class equip_battle_destroys_attacked:
    """'After damage calculation, if the equipped monster attacks a monster: Destroy the attacked monster.'
    The donor takes Thorn of Malice's after-damage-calc equip event (BL to a stub comparing 0x2007 || cid),
    its cls1 record becomes Ancient Gear Fist's destroy record with +08 = a filter stub (Fist's filter, cid
    switch skipped), and the End-of-Damage-Step walker's donor-only queue branch is turned to skip --
    without that the destroy record would ALSO fire at end of Damage Step, including when defending."""
    native: tuple                       # donor's stock cls1 record
    slots: tuple[int, int]              # (post, filter), ov3 pool

    def _stubs(self, cid):
        post, filt = self.slots
        b = EffectBuilder()
        b.ldr_const(1, _THORN)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "done")
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.label("done")
        b.insn("BX", "LR")
        pb = b.assemble(post, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
        b.ldr_const(3, 0x1010)
        b.insn("ADD", "R7, R0, #0x0")
        b.insn("ADD", "R5, R1, #0x0")
        b.insn("ADD", "R6, R2, #0x0")
        b.call_addr(_ZONE_PRED, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "hit")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        b.label("hit")
        b.ldr_const(0, _FIST_BATTLED_ARM)
        b.insn("BX", "R0")
        fb = b.assemble(filt, pad="nop")
        for blob, addr in ((pb, post), (fb, filt)):
            assert_thumb1_only(blob, addr)
        return pb, fb

    def compile(self, view, cid) -> Compiled:
        post, filt = self.slots
        assert not _in_ov5(post) and not _in_ov5(filt)
        pb, fb = self._stubs(cid)
        bl = _shim_bl(_ADC_SITE, post)

        def install(rom, view):
            assert tuple(struct.unpack("<HHIIIII", view.blob(_FIST_CLS1_ADDR, 24))) == _FIST_CLS1, \
                "Fist cls1 template drifted"
            _patch_bytes(view, _ADC_SITE, _ADC_STOCK, bl, "after-damage-calc compare")
            _patch_bytes(view, _EODS_BGE, _EODS_STOCK, _EODS_NEW, "End-of-Damage-Step skip")

        def check(c, rom, view):
            c.eq(view.blob(_ADC_SITE, 4), bl, "after-damage-calc compare = BL post stub")
            c.eq(view.blob(_EODS_BGE, 2), _EODS_NEW, "End-of-Damage-Step donor branch = skip")

        patched = (cid, 0, 0x022048FD, filt | 1, 0, 0, 0)
        return Compiled(((post, pb, "post"), (filt, fb, "filter")),
                        edits=(Edit(CLS1, cid, self.native, patched),), installs=(install,), checks=(check,))



AMAZONESS_THUNK = 0x020237C8        # set code 0x05

SPEC = card(
    0x2124,
    equip_only_to_set_code(AMAZONESS_THUNK),
    equip_battle_destroys_attacked(
        native=(0x2124, 0, 0x0222D5FD, 0, 0x02201169, 0, 0),
        slots=(cave3.CAVE3_HEIRLOOM_POST, cave3.CAVE3_HEIRLOOM_FILTER)))

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_amazoness_heirloom.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
