"""Sacred Sword of Seven Stars (Normal Spell) on Block Attack 0x130A.

    "Banish 1 Level 7 monster from your hand or face-up from your side of the field; draw 2 cards. You can only
     activate 1 "Sacred Sword of Seven Stars" per turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import CLS0, Compiled, Edit, _CHAIN_POP, _CHAIN_PUSH, _COPY_EXEMPT_BX, _H2_SITE, _H3_SITE, _RES_STATE, _TURNLOG_POST_ODD, _TURNLOG_QUERY_ODD
from otn_enhanced.effects import cave3, ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import cave3
from otn_enhanced.effects.common import bl as common_bl
from otn_enhanced.effects.common import ov3_bl_target as common_bl_target
from dataclasses import dataclass
import struct


_CAN_DRAW, _DRAW_ODD = 0x021BAE31, 0x021D12F5


_COUNT_CANDS, _SHORTCIRCUIT = 0x02243FA9, 0x021D2BC9


_MESSAGE, _PICKER_ODD, _READBACK = 0x0219A819, 0x0219C431, 0x0219C511


_HAND_INDEX, _HAND_BANISH, _NSB_ON_FIELD, _FIELD_BANISH = 0x021A25A1, 0x021C6E99, 0x021A241D, 0x021CF40D   # NOT _ON_FIELD (0x021A241C, line 378)


_NSB_HAND_BUILDER, _LEVEL_OF_ZONE, _RECORD_FIELD = 0x0223C16D, 0x021B8065, 0x02243B2D   # NOT _HAND_BUILDER: that name is 0x0223C16C above


_FIELD_ZONES = 0x0229ACC8


@dataclass(frozen=True)
class normal_spell_banish_level_monster_draw:
    """'Banish 1 Level N monster from your hand or face-up from your side of the field; draw 2 cards. You can only
    activate 1 "<card>" per turn.' A FIELD monster counts by its CURRENT Level, hand cards by printed Level (user
    ruling). The donor's cls0 record is rewritten in place -> {RES, 0, COND, COST, 0} (Sekka's Light shape):
      COND  menu (desc[+7] == 0): OPT kind 1 not posted AND >= 1 candidate (count on the virtual row); can draw 2.
      COST  phase [STATE+0x7C]: 0 post OPT kind 1 (skipped in a replay) + banish prompt | 1 picker (pick 1) | 2 hand ->
            0x021C6E98, else field -> 0x021CF40C (Ojamassimilation's mover split); return 1.
      RES   draw 2.
      row   the criteria row is VIRTUAL: an ov3 front on the resolver miss tail 0x02243F24 answers the donor with
            `virtual_index`, else tails into the NEXT front (Fire Formation - Tenki's). Rulers' H3 maps the index to an
            ov5 copy of the row {cid, 0xFFFF, HANDLER, word}. MUST run after Dragon Rulers and Tenki.
      HANDLER (row, side): hand builder 0x0223C16C with the row word, flags 0x10000 (banish) -- printed Level; then own
            zones 0..4: occupied && face-up && LEVEL_OF_ZONE == N -> recorder 0x02243B2C."""
    level: int
    word: int                 # 3DS row word: Level << 18
    native: tuple             # donor's stock cls0 record
    slots: tuple              # (row, handler, cond, cost, res) ov5
    front: int                # ov3 pool
    next_front: int           # Tenki's front
    virtual_index: int

    def compile(self, view, cid) -> Compiled:
        row_s, hand_s, cond_s, cost_s, res_s = self.slots

        def side(b, dst, desc):
            b.insn("LDRB", f"R{dst}, [R{desc}, #0x2]")
            b.insn("LDRB", "R0, [R%d, #0x6]" % desc)
            b.insn("EOR", f"R{dst}, R0")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("SUB", "SP, #0x8")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("ADD", "R4, R1, #0x0")
        b.insn("LDR", "R0, [R5, #0x8]")
        b.insn("STR", "R0, [SP, #0x0]")
        b.ldr_const(0, 0x10000)
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.insn("MOV", "R2, #0x0")
        b.insn("MOV", "R3, #0x0")
        b.ldr_const(6, _NSB_HAND_BUILDER)
        b.insn("BLX", "R6")
        b.ldr_const(7, _FIELD_ZONES)
        b.insn("MOV", "R0, #0x1")
        b.insn("AND", "R0, R4")
        b.insn("BEQ", "p0")
        b.ldr_const(0, 0xB3C)
        b.insn("ADD", "R7, R7, R0")
        b.label("p0")
        b.insn("MOV", "R6, #0x0")
        b.label("lp")
        b.insn("CMP", "R6, #0x5")
        b.insn("BGE", "out")
        b.insn("LDRH", "R0, [R7, #0x0]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "nx")
        b.insn("LDRH", "R0, [R7, #0x8]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "nx")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("ADD", "R1, R6, #0x0")
        b.ldr_const(3, _LEVEL_OF_ZONE)
        b.insn("BLX", "R3")
        b.insn("CMP", f"R0, #{self.level}")
        b.insn("BNE", "nx")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("ADD", "R1, R6, #0x0")
        b.insn("MOV", "R2, #0x0")
        b.ldr_const(3, _RECORD_FIELD)
        b.insn("BLX", "R3")
        b.label("nx")
        b.insn("ADD", "R7, #0x14")
        b.insn("ADD", "R6, #0x1")
        b.insn("B", "lp")
        b.label("out")
        b.insn("ADD", "SP, #0x8")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        hb = b.assemble(hand_s, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        side(b, 5, 4)
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "draw")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0xB")
        b.ldr_const(2, cid)
        b.insn("MOV", "R3, #1")
        b.ldr_const(6, _TURNLOG_QUERY_ODD)
        b.insn("BLX", "R6")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.insn("MOV", "R2, #0x0")
        b.ldr_const(3, _COUNT_CANDS)
        b.insn("BLX", "R3")
        b.insn("CMP", "R0, #0x0")
        b.insn("BLE", "no")
        b.label("draw")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0x2")
        b.ldr_const(3, _CAN_DRAW)
        b.insn("BLX", "R3")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        cb = b.assemble(cond_s, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.ldr_const(3, _SHORTCIRCUIT)
        b.insn("BLX", "R3")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "done")
        b.insn("LDRB", "R5, [R4, #0x2]")
        b.ldr_const(6, _RES_STATE)
        b.insn("LDR", "R0, [R6, #0x7C]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "ph0")
        b.insn("CMP", "R0, #0x1")
        b.insn("BEQ", "ph1")
        b.ldr_const(3, _READBACK)
        b.insn("BLX", "R3")
        b.insn("LDR", "R0, [R0, #0x0]")
        b.insn("LSL", "R7, R0, #0x11")
        b.insn("LSR", "R7, R7, #0x1F")
        b.insn("LSL", "R0, R0, #0x1")
        b.insn("LSR", "R0, R0, #0x18")
        b.insn("LSL", "R0, R0, #0x1")
        b.insn("ADD", "R7, R7, R0")
        b.ldr_const(3, _CHAIN_PUSH)
        b.insn("BLX", "R3")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("ADD", "R1, R7, #0x0")
        b.ldr_const(3, _HAND_INDEX)
        b.insn("BLX", "R3")
        b.insn("CMP", "R0, #0x0")
        b.insn("BLT", "field")
        b.insn("ADD", "R1, R0, #0x0")
        b.insn("ADD", "R0, R5, #0x0")
        b.ldr_const(3, _HAND_BANISH)
        b.insn("BLX", "R3")
        b.insn("B", "pop")
        b.label("field")
        b.insn("ADD", "R0, R7, #0x0")
        b.ldr_const(3, _NSB_ON_FIELD)
        b.insn("BLX", "R3")
        b.insn("CMP", "R0, #0x0")
        b.insn("BLT", "pop")
        b.insn("LSL", "R1, R0, #0x10")
        b.insn("LSR", "R1, R1, #0x18")
        b.insn("LSL", "R0, R0, #0x18")
        b.insn("LSR", "R0, R0, #0x18")
        b.insn("MOV", "R2, #0x0")
        b.ldr_const(3, _FIELD_BANISH)
        b.insn("BLX", "R3")
        b.label("pop")
        b.ldr_const(3, _CHAIN_POP)
        b.insn("BLX", "R3")
        b.label("done")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("ph0")
        b.insn("ADD", "R0, R4, #0x0")
        b.ldr_const(3, _COPY_EXEMPT_BX)
        b.insn("BLX", "R3")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "msg")
        b.insn("LDRB", "R0, [R4, #0x6]")
        b.insn("EOR", "R0, R5")
        b.ldr_const(1, cid)
        b.insn("MOV", "R2, #1")
        b.insn("MOV", "R3, #0x0")
        b.ldr_const(7, _TURNLOG_POST_ODD)
        b.insn("BLX", "R7")
        b.label("msg")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0x56")
        b.ldr_const(3, _MESSAGE)
        b.insn("BLX", "R3")
        b.insn("B", "next")
        b.label("ph1")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #6")
        b.insn("LDRH", "R2, [R4, #0x0]")
        b.insn("MOV", "R3, #0x0")
        b.ldr_const(7, _PICKER_ODD)
        b.insn("BLX", "R7")
        b.label("next")
        b.insn("LDR", "R0, [R6, #0x7C]")
        b.insn("ADD", "R0, #0x1")
        b.insn("STR", "R0, [R6, #0x7C]")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        kb = b.assemble(cost_s, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        side(b, 4, 0)
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("MOV", "R1, #0x2")
        b.ldr_const(3, _DRAW_ODD)
        b.insn("BLX", "R3")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        rb = b.assemble(res_s, pad="nop")

        b = EffectBuilder()
        b.insn("MOV", f"R0, #0x{cid >> 8:X}")
        b.insn("LSL", "R0, R0, #0x8")
        b.insn("ADD", f"R0, #0x{cid & 0xFF:X}")
        b.insn("CMP", "R5, R0")
        b.insn("BNE", "tenki")
        b.insn("MOV", f"R0, #0x{self.virtual_index >> 8:X}")
        b.insn("LSL", "R0, R0, #0x8")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        b.label("tenki")
        b.bl(self.next_front)
        fb = b.assemble(self.front, pad="nop")
        for blob, addr in ((hb, hand_s), (cb, cond_s), (kb, cost_s), (rb, res_s), (fb, self.front)):
            assert_thumb1_only(blob, addr)
        row_blob = struct.pack("<HHII", cid, 0xFFFF, hand_s | 1, self.word)

        def install(rom, view):
            cur = common_bl_target(view.buf, _H2_SITE)
            assert cur in (self.next_front, self.front), f"H2 site {_H2_SITE:#x} calls {cur:#x}, not Tenki's front"
            view.write(_H2_SITE, common_bl(_H2_SITE, self.front))

        def check(c, rom, view):
            c.eq(ov5_cave.dc_skip(common_bl_target(view.buf, _H2_SITE)), self.front,
                 "bl @0x02243F24 -> front (disguise_copycat's front may sit ahead)")
            c.eq(common_bl_target(view.buf, self.next_front + 0x10), cave3.CAVE3_RUL_H2, "Tenki's front still installed")
            c.eq(ov5_cave.dc_skip(common_bl_target(view.buf, _H3_SITE)), cave3.CAVE3_RUL_H3, "Rulers' H3 still installed")

        return Compiled(((row_s, row_blob, "virtual criteria row"), (hand_s, hb, "handler"), (cond_s, cb, "cond"),
                         (cost_s, kb, "cost"), (res_s, rb, "resolver"), (self.front, fb, "H2 front")),
                        edits=(Edit(CLS0, cid, self.native, (cid, res_s | 1, 0, cond_s | 1, cost_s | 1, 0)),),
                        installs=(install,), checks=(check,))



VIDX = (0x40 + (ov5_cave.CAVE_SSS_ROW - ov5_cave.CAVE_RUL_ROWS) // 0x40) << 8

SPEC = dsl.card(
    0x130A,
    normal_spell_banish_level_monster_draw(
        level=7, word=0x001C0002,
        native=(0x130A, 0x022076A5, 0x021DB1F9, 0, 0, 0x02234E01),
        slots=(ov5_cave.CAVE_SSS_ROW, ov5_cave.CAVE_SSS_HANDLER, ov5_cave.CAVE_SSS_COND,
               ov5_cave.CAVE_SSS_COST, ov5_cave.CAVE_SSS_RES),
        front=cave3.CAVE3_SSS_H2, next_front=cave3.CAVE3_TENKI_H2, virtual_index=VIDX))

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_sacred_sword.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
