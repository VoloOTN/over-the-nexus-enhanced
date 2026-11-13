"""Naturia Pineapple (EARTH / Plant / Level 2 / 100 / 100) on Headless Knight 0x1465.

    "All face-up monsters you control are treated as Plant-Type. During your Standby Phase, if you do not control
     a face-up "Naturia Pineapple", and have no monsters in your Graveyard except Plant or Beast-Type: You can
     Special Summon this card from your Graveyard. You must not control any Spell or Trap Cards to activate and
     resolve this effect."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import archetype_member, card, card_props, CLS2, Compiled, Row, SetCodeTable, _in_ov5, _patch_bytes
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import rows
import struct


NATURIA_TABLE = SetCodeTable("Naturia", 0x0209CEB0, 36, (0x02023CE0,), (0x02023CDC,))


_ST_COUNT, _CID_COUNT, _GY_MONSTERS, _GY_RACE = 0x021AE4AD, 0x021AC9FD, 0x021B16F1, 0x021B1771


_COND_TAIL, _GY_SS = 0x021F04FD, 0x0220731D


_REG_STANDBY_ROW = 0x0228EB08 + (316 - 293) * 8


_REG_STANDBY_STOCK = (0x02256F7D, 0x1338)


_REG_GY_POSTER = 0x022573DD


_RACE_SITE, _RACE_STOCK = 0x021B8ACC, bytes.fromhex("eaf70efe")


_CID_AT, _FACE_UP, _NEXT_ZONE = 0x021A36ED, 0x021A32B5, 0x021B8BB1


@dataclass(frozen=True)
class standby_revive_from_gy_with_no_backrow:
    """'During your Standby Phase, if you do not control a face-up <self>, and have no monsters in your GY except
    <race A> or <race B>-Type: You can Special Summon this card from your GY. You must not control any Spell or Trap
    Cards to activate and resolve this effect.' (3DS: Treeborn Frog's machine.) Standby-section registry row 316
    {0x02256F7D, phantom} -> {the cid-agnostic GY poster 0x022573DD, donor}; cls2 {+04 RES, +0C COND, +10 IF tag}
    over a phantom in Treeborn's record shape. COND = S/T count == 0 && own copies == 0 && GY race A + race B ==
    all GY monsters, then the shared check 0x021F04FD; RES = S/T recheck, then the shared GY-SS resolver
    0x0220731D (a foreign cid takes its default arm, which has no recheck)."""
    races: tuple[int, int]
    template: int                    # Treeborn Frog
    template_cls2: tuple             # its whole cls2 record, asserted
    if_tag: int
    slots: tuple[int, int]           # (cond, res), ov3 pool
    phantom: int                     # cls2 cid dropped

    def compile(self, view, cid) -> Compiled:
        cond, res = self.slots
        a, bb = self.races
        assert self.template_cls2 in rows(view, CLS2), "Treeborn's cls2 template drifted"
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("ADD", "R5, R1, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call_addr(_ST_COUNT, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "fail")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.call_addr(_CID_COUNT, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "fail")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call_addr(_GY_RACE, R0, a, via=R3)
        b.insn("ADD", "R6, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call_addr(_GY_RACE, R0, bb, via=R3)
        b.insn("ADD", "R6, R6, R0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call_addr(_GY_MONSTERS, via=R3)
        b.insn("CMP", "R0, R6")
        b.insn("BNE", "fail")
        b.call_addr(_COND_TAIL, R4, R5, via=R3)
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("fail")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        cb = b.assemble(cond, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("ADD", "R5, R1, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call_addr(_ST_COUNT, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "fizzle")
        b.call_addr(_GY_SS, R4, R5, via=R3)
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("fizzle")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        rb = b.assemble(res, pad="nop")
        for blob, addr in ((cb, cond), (rb, res)):
            assert_thumb1_only(blob, addr)
            assert not _in_ov5(addr)
        new_row = struct.pack("<IH", _REG_GY_POSTER, cid)

        def install(rom, view):
            _patch_bytes(view, _REG_STANDBY_ROW, struct.pack("<IH", *_REG_STANDBY_STOCK), new_row, "Standby row 316")

        def check(c, rom, view):
            c.eq(view.blob(_REG_STANDBY_ROW, 6), new_row, "Standby registry row 316 = GY poster, donor")

        return Compiled(((cond, cb, "condition"), (res, rb, "resolver")),
                        (Row(CLS2, (cid, 0, res | 1, 0, cond | 1, self.if_tag, 0), self.phantom),),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class all_face_up_monsters_treated_as_race:
    """'All face-up monsters you control are treated as <race>-Type.' The live race resolver 0x021B88F0's board-scan
    cid fetch `bl 0x021A36EC` @0x021B8ACC becomes a BL to a stub which, for the donor in monster zones 0..4 on the
    source side (not a Set card, face-up, not negated), runs Parasite Paracide's monster arm (0x021B8AF6) with race
    `race`, then continues at 0x021B8BB0; otherwise returns the fetched cid unchanged. slot = ov3 pool."""
    race: int
    slot: int

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.asm.effect_shim import _bl
        b = EffectBuilder()
        b.insn("PUSH", "{LR}")
        b.call_addr(_CID_AT, R7, R5, via=R2)
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BNE", "out")
        b.insn("CMP", "R5, #0x4")
        b.insn("BGT", "out")
        b.insn("LDR", "R2, [SP, #0x28]")
        b.insn("CMP", "R2, #0x0")
        b.insn("BGT", "out")
        b.insn("LDR", "R2, [SP, #0x4]")
        b.insn("CMP", "R2, R7")
        b.insn("BNE", "out")
        b.call_addr(_FACE_UP, R7, R5, via=R2)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "fail")
        b.insn("LDR", "R0, [R4, #0x44]")
        b.insn("LSR", "R0, R0, #0x1A")
        b.insn("MOV", "R1, #0x1")
        b.insn("AND", "R0, R1")
        b.insn("BNE", "fail")
        b.insn("LDRH", "R6, [R4, #0x38]")
        b.insn("MOV", f"R0, #0x{self.race:X}")
        b.insn("STR", "R0, [SP, #0xC]")
        b.insn("POP", "{R3}")
        b.ldr_const(0, _NEXT_ZONE)
        b.insn("BX", "R0")
        b.label("fail")
        b.ldr_const(0, cid)
        b.label("out")
        b.insn("POP", "{PC}")
        blob = b.assemble(self.slot, pad="nop")
        assert_thumb1_only(blob, self.slot)
        assert not _in_ov5(self.slot)
        want = _bl(_RACE_SITE, self.slot)

        def install(rom, view):
            _patch_bytes(view, _RACE_SITE, _RACE_STOCK, want, "race-resolver BL")

        def check(c, rom, view):
            c.eq(view.blob(_RACE_SITE, 4), want, "race-resolver BL -> treated-as-race stub")

        return Compiled(((self.slot, blob, "race stub"),), installs=(install,), checks=(check,))



IF_TAG = 0x021E7969

SPEC = card(
    0x1465,
    standby_revive_from_gy_with_no_backrow(
        races=(13, 11),                                              # Plant, Beast
        template=0x19CB,                                             # Treeborn Frog
        template_cls2=(0x19CB, 0, 0x0220731D, 0, 0x021FA585, IF_TAG, 0),
        if_tag=IF_TAG, slots=(cave3.CAVE3_PINE_COND, cave3.CAVE3_PINE_RES), phantom=0x1435),
    all_face_up_monsters_treated_as_race(race=13, slot=cave3.CAVE3_PINE_RACE),
    archetype_member(NATURIA_TABLE, 0x23F4))

PROPS = card_props("EARTH", "Plant", level=2, atk=100, defense=100)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_naturia_pineapple.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
