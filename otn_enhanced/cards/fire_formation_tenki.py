"""Fire Formation - Tenki (Continuous Spell) on Marshmallon Glasses 0x1777.

    "When this card is activated: You can add 1 Level 4 or lower Beast-Warrior monster from your Deck to your hand.
     All Beast-Warrior monsters you control gain 100 ATK. You can only activate 1 "Fire Formation - Tenki" per turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, CLS0, Compiled, Row, _COPY_EXEMPT_BX, _DECK_TO_HAND, _H2_SITE, _H3_SITE, _HAS_CANDIDATE, _RES_STATE, _TURNLOG_POST_ODD, _TURNLOG_QUERY_ODD, _UI_RESULT, _YESNO
from otn_enhanced.effects import cave3, ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import cave3
from otn_enhanced.effects.common import bl as common_bl
from otn_enhanced.effects.common import ov3_bl_target as common_bl_target
from dataclasses import dataclass
import struct


_ST_STAT_BGT, _ST_STAT_BGT_STOCK = 0x021B3284, 0xDC04     # bgt 0x021B3290 in the S/T-card stat switch (fn 0x021B2B7C)


_ST_STAT_SEAL, _ST_STAT_SEAL_STOCK = 0x021B3274, 0xD036   # phantom arm's own beq


_ST_STAT_ARM = 0x021B32E4


_ST_STAT_ARM_STOCK = bytes.fromhex("1899301cf0f71af870f68efd002830d07d48f9f763fefa2189001de0")   # stock AND chain


_MM_BLOCK_LIT = 0x021A6644


@dataclass(frozen=True)
class continuous_spell_race_atk_bonus:
    """'All <race> monsters you control gain N ATK.' The S/T-card stat switch (fn 0x021B2B7C: r4 = S/T cid, r5 = ATK
    bonus, r6/r7 = card/monster side, [sp] = monster record, race bitmask at +8): the donor reaches `bgt 0x021B3290`
    @0x021B3284 (the node Shien's Dojo NOP'd, left alone), retargeted to a phantom's dead 28 B leaf: donor && same side
    && race bit -> +N; any other cid -> back to 0x021B3290. The phantom's own beq @0x021B3274 is sealed (NOP). The donor's
    stock attack-target block (literal @0x021A6644 = donor cid) is re-pointed at the phantom: never face-up, so the
    block is skipped."""
    race_bit: int          # 12 = Beast-Warrior
    amount: int
    phantom: int

    def compile(self, view, cid) -> Compiled:
        assert self.race_bit == 12 and self.amount == 100
        b = EffectBuilder()
        b.insn("MOV", "R0, #0x17")
        b.insn("LSL", "R0, R0, #0x8")
        b.insn("ADD", "R0, #0x77")
        b.insn("CMP", "R4, R0")
        b.insn("BNE", "next")
        b.insn("CMP", "R6, R7")
        b.insn("BNE", "out")
        b.insn("LDR", "R0, [SP, #0x0]")
        b.insn("LDR", "R1, [R0, #0x8]")
        b.insn("LSL", "R1, R1, #0x13")
        b.insn("BPL", "out")
        b.insn("ADD", "R5, #0x64")
        b.label("out")
        b.insn("B", "0x21B355E")
        b.label("next")
        b.insn("B", "0x21B3290")
        blob = b.assemble(_ST_STAT_ARM, pad="nop")
        assert len(blob) <= 28 and cid == 0x1777
        assert_thumb1_only(blob, _ST_STAT_ARM)
        arm = blob + bytes(28 - len(blob))
        bgt = 0xDC00 | (((_ST_STAT_ARM - (_ST_STAT_BGT + 4)) >> 1) & 0xFF)

        def install(rom, view):
            assert view.blob(_ST_STAT_ARM, 28) in (_ST_STAT_ARM_STOCK, arm), "phantom leaf is neither stock nor ours"
            view.write(_ST_STAT_ARM, arm)
            for site, stock, new in ((_ST_STAT_BGT, _ST_STAT_BGT_STOCK, bgt), (_ST_STAT_SEAL, _ST_STAT_SEAL_STOCK, 0x46C0)):
                assert view.u16(site) in (stock, new), f"{site:#x} = {view.u16(site):#06x}, not stock {stock:#06x}"
                view.pack(site, "<H", new)
            cur = view.u32(_MM_BLOCK_LIT)
            assert cur in (cid, self.phantom), f"literal @{_MM_BLOCK_LIT:#x} = {cur:#x}"
            view.pack(_MM_BLOCK_LIT, "<I", self.phantom)

        def check(c, rom, view):
            c.eq(view.blob(_ST_STAT_ARM, len(blob)), blob, "stat arm")
            c.eq(view.u16(_ST_STAT_BGT), bgt, "bgt -> arm")
            c.eq(view.u16(_ST_STAT_SEAL), 0x46C0, "phantom beq sealed")
            c.eq((view.u16(0x021B3292), view.u16(0x021B3296)), (0x4284, 0xE162), "Shien's Dojo node untouched")
            c.eq(view.u32(_MM_BLOCK_LIT), self.phantom, "donor attack-block literal -> phantom")

        return Compiled(installs=(install,), checks=(check,))


@dataclass(frozen=True)
class continuous_spell_optional_deck_search_once_per_turn:
    """'When this card is activated: You can add 1 <filter> monster from your Deck to your hand. You can only activate
    1 "<card>" per turn.' cls0 {RES, 0, COND, COST, 0} over a phantom (Sekka's Light shape).
      COND  menu check (desc[+7] == 0): OPT kind 1 not posted this turn; else 1 (activatable with no target).
      COST  post OPT kind 1 at activation (skipped in a replay, 0x021D2B89).
      RES   0x80: a Deck candidate (RotA cond 0x021F0821)? Yes/No 0x0219AAAD(desc, 0xFA, desc[+0xC]) -> private 0x90,
            else end. 0x90: No -> end; Yes -> phase back to 0x80, then 0x02207EF5 (RotA) for every later phase.
      row   the Deck criteria row is VIRTUAL (no criteria phantom left): an ov3 front on the resolver miss tail
            0x02243F24 (owned by Dragon Rulers' H2 front) answers the donor with index `virtual_index`, which Rulers'
            own H3 maps to an ov5 copy of `row`. MUST run after Dragon Rulers.
    slots = (cond, cost, res) ov5; row_slot ov5; front ov3 pool; rulers_h2 = Dragon Rulers' H2 front."""
    row: tuple                  # the virtual criteria row (cid, 0xFFFF, handler, word)
    slots: tuple[int, int, int]
    row_slot: int
    front: int
    rulers_h2: int
    virtual_index: int
    phantom: int                # cls0 cid dropped

    def compile(self, view, cid) -> Compiled:
        cond, cost, res = self.slots

        def side(b, dst, desc):
            b.insn("LDRB", f"R{dst}, [R{desc}, #0x2]")
            b.insn("LDRB", "R0, [R%d, #0x6]" % desc)
            b.insn("EOR", f"R{dst}, R0")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        side(b, 5, 4)
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "yes")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0xB")
        b.ldr_const(2, cid)
        b.insn("MOV", "R3, #0x1")
        b.ldr_const(6, _TURNLOG_QUERY_ODD)
        b.insn("BLX", "R6")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.label("yes")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        cb = b.assemble(cond, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.ldr_const(3, _COPY_EXEMPT_BX)
        b.insn("BLX", "R3")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "done")
        side(b, 5, 4)
        b.insn("ADD", "R0, R5, #0x0")
        b.ldr_const(1, cid)
        b.insn("MOV", "R2, #0x1")
        b.insn("MOV", "R3, #0x0")
        b.ldr_const(4, _TURNLOG_POST_ODD)
        b.insn("BLX", "R4")
        b.label("done")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, PC}")
        kb = b.assemble(cost, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.ldr_const(5, _RES_STATE)
        b.insn("LDR", "R0, [R5, #0x70]")
        b.insn("CMP", "R0, #0x80")
        b.insn("BNE", "not80")
        b.insn("ADD", "R0, R4, #0x0")
        b.ldr_const(3, _HAS_CANDIDATE)
        b.insn("BLX", "R3")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "done")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("MOV", "R1, #0xFA")
        b.insn("LDRH", "R2, [R4, #0xC]")
        b.ldr_const(3, _YESNO)
        b.insn("BLX", "R3")
        b.insn("MOV", "R0, #0x90")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("not80")
        b.insn("CMP", "R0, #0x90")
        b.insn("BNE", "go")
        b.ldr_const(0, _UI_RESULT)
        b.insn("LDR", "R0, [R0, #0x34]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "done")
        b.insn("MOV", "R0, #0x80")
        b.insn("STR", "R0, [R5, #0x70]")
        b.label("go")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("MOV", "R1, #0x0")
        b.ldr_const(3, _DECK_TO_HAND)
        b.insn("BLX", "R3")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("done")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        rb = b.assemble(res, pad="nop")
        for blob, addr in ((cb, cond), (kb, cost), (rb, res)):
            assert_thumb1_only(blob, addr)
        b = EffectBuilder()
        b.insn("MOV", "R0, #0x17")
        b.insn("LSL", "R0, R0, #0x8")
        b.insn("ADD", "R0, #0x77")
        b.insn("CMP", "R5, R0")
        b.insn("BNE", "rulers")
        b.insn("MOV", f"R0, #0x{self.virtual_index >> 8:X}")
        b.insn("LSL", "R0, R0, #0x8")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        b.label("rulers")
        b.bl(self.rulers_h2)
        fb = b.assemble(self.front, pad="nop")
        assert_thumb1_only(fb, self.front)
        row_blob = struct.pack("<HHII", *self.row)

        def install(rom, view):
            cur = common_bl_target(view.buf, _H2_SITE)
            assert cur in (self.rulers_h2, self.front), f"H2 site {_H2_SITE:#x} calls {cur:#x}, not Dragon Rulers' H2"
            view.write(_H2_SITE, common_bl(_H2_SITE, self.front))

        def check(c, rom, view):
            # sacred_sword_seven_stars (a later step) may front this front: its stub's tail bl must land here
            tgt = ov5_cave.dc_skip(common_bl_target(view.buf, _H2_SITE))     # disguise_copycat fronts SSS's front
            c.ok(tgt == self.front or (tgt == cave3.CAVE3_SSS_H2
                                       and common_bl_target(view.buf, cave3.CAVE3_SSS_H2 + 0x10) == self.front),
                 "bl @0x02243F24 -> front")
            c.eq(ov5_cave.dc_skip(common_bl_target(view.buf, _H3_SITE)), cave3.CAVE3_RUL_H3,
                 "Dragon Rulers' H3 still installed (behind disguise_copycat's front)")

        return Compiled(((self.row_slot, row_blob, "virtual criteria row"), (cond, cb, "cond"), (cost, kb, "cost"),
                         (res, rb, "resolver"), (self.front, fb, "H2 front")),
                        (Row(CLS0, (cid, res | 1, 0, cond | 1, cost | 1, 0), self.phantom),),
                        installs=(install,), checks=(check,))



VIDX = (0x40 + (ov5_cave.CAVE_TENKI_ROW - ov5_cave.CAVE_RUL_ROWS) // 0x40) << 8

SPEC = card(
    0x1777,
    continuous_spell_race_atk_bonus(race_bit=12, amount=100, phantom=0x0E2C),
    continuous_spell_optional_deck_search_once_per_turn(
        row=(0x1777, 0xFFFF, 0x0223CAD9, 0x60900002),
        slots=(ov5_cave.CAVE_TENKI_COND, ov5_cave.CAVE_TENKI_COST, ov5_cave.CAVE_TENKI_RES),
        row_slot=ov5_cave.CAVE_TENKI_ROW, front=cave3.CAVE3_TENKI_H2, rulers_h2=cave3.CAVE3_RUL_H2,
        virtual_index=VIDX, phantom=0x1765))

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_fire_formation_tenki.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
