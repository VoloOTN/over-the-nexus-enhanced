"""Koa'ki Meiru Wall (EARTH / Rock / Level 4 / 1900 / 1200) on Dark Rabbit 0x1126, cloned from Sandman 0x2264.

    "During each of your End Phases, destroy this card unless you send 1 "Iron Core of Koa'ki Meiru" from your
     hand to the Graveyard or reveal 1 Rock monster in your hand. When your opponent activates a Spell Card
     (Quick Effect): You can Tribute this card; negate the activation, and if you do, destroy that card."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import archetype_member, card, card_props, CLS3, CRITERIA, Compiled, Row, SetCodeTable, _in_ov5, _template
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass


KOAKI_TABLE = SetCodeTable("Koa'ki Meiru", 0x0209CCD8, 0x1B, (0x02023D9C,), (0x02023D98,))


SPELL_SPEED_2_TABLE = SetCodeTable("spell-speed-2", 0x0209C118, 0x76, (0x020234A4,), (0x02023490,))


_HAND_CRIT_LIST, _HAND_CRIT_COUNT_IMM, _HAND_CRIT_STOCK = 0x0228EF48, 0x0225A418, 0x1F


_IS_NEGATED = 0x021AB90D             # (act, 1) != 0 -> already negated


_IS_SPELL = 0x02022FC9               # (cid) card_type>>1 == 0xD


_OFFER_GATE = 0x021F06E9             # (mine, act) generic offer gate


@dataclass(frozen=True)
class koaki_upkeep:
    """'During each of your End Phases, destroy this card unless you send 1 "Iron Core of Koa'ki Meiru" from your hand
    to the GY or reveal 1 Rock monster in your hand.' No per-cid row: the generic Koa'ki upkeep walker 0x02255959
    serves every set-code-0x46 monster through the monster's own criteria row (`filter` = (handler, word); word>>3
    = race), plus the hand-criteria list 0x0228EF48 (31 real cids, no phantom), GROWN by one into its u16 alignment
    pad with the count immediate `movs r2,#0x1F` @0x0225A418 bumped."""
    filter: tuple[int, int]
    phantom: int                 # criteria cid dropped (count-neutral)
    template: int                # a native member of the hand list (Sandman)

    def compile(self, view, cid) -> Compiled:
        handler, word = self.filter

        def hand(view):
            imm = view.u16(_HAND_CRIT_COUNT_IMM)
            assert imm & 0xFF00 == 0x2200, f"hand-list count is not movs r2,#N ({imm:#06x})"
            n = imm & 0xFF
            return n, list(view.unpack(_HAND_CRIT_LIST, f"<{n}H"))

        def install(rom, view):
            n, lst = hand(view)
            if cid in lst:
                return
            assert n == _HAND_CRIT_STOCK and self.template in lst, f"hand list not stock (count {n:#x})"
            assert view.u16(_HAND_CRIT_LIST + n * 2) == 0, "hand-list alignment pad already used"
            new = sorted(lst + [cid])
            assert all(new[i] < new[i + 1] for i in range(n)), "hand list not strictly sorted"
            view.pack(_HAND_CRIT_LIST, f"<{n + 1}H", *new)
            view.pack(_HAND_CRIT_COUNT_IMM, "<H", 0x2200 | (n + 1))

        def check(c, rom, view):
            n, lst = hand(view)
            c.ok(n == _HAND_CRIT_STOCK + 1 and cid in lst and self.template in lst
                 and all(lst[i] < lst[i + 1] for i in range(n - 1)), "hand-criteria list 32, donor in, sorted")

        return Compiled(rows=(Row(CRITERIA, (cid, 0xFFFF, handler, word), self.phantom),),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class quick_tribute_negate_spell:
    """'When your opponent activates a Spell Card (Quick Effect): You can Tribute this card; negate the activation,
    and if you do, destroy that card.' One cls3 record cloned from `template` (Sandman) with +0C swapped for a
    stub: the template's condition is a cid switch (unlisted cid -> 0) whose case is shared with A-Team. The stub =
    that condition's pre-checks + the template case with the Trap test 0x02022FDC swapped for the Spell test 0x02022FC8.
    slots = (condition,) ov3 pool."""
    template: int
    template_slots: tuple      # (0, +0C cond, +10 cost, 0) of the template's cls3 record
    res: int                   # negate + destroy resolver
    cost: int                  # Tribute self
    slot: int
    phantom: int

    def compile(self, view, cid) -> Compiled:
        assert _template(view, CLS3, self.template, self.template_slots)[1] == self.res, "template resolver drifted"
        assert not _in_ov5(self.slot)
        b = EffectBuilder()
        b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("ADD", "R4, R1, #0x0")
        b.insn("BEQ", "ret0")
        b.insn("LDRB", "R0, [R4, #0x3]")
        b.insn("CMP", "R0, #0xA")
        b.insn("BGT", "ret0")
        b.insn("LDRB", "R0, [R4, #0x5]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "ret0")
        b.call_addr(_IS_NEGATED, R4, 1, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "ret0")
        b.insn("LDRB", "R1, [R4, #0x2]")
        b.insn("LDRB", "R0, [R4, #0x6]")
        b.insn("ADD", "R2, R1, #0x0")
        b.insn("EOR", "R2, R0")
        b.insn("LDRB", "R1, [R5, #0x2]")
        b.insn("LDRB", "R0, [R5, #0x6]")
        b.insn("EOR", "R0, R1")
        b.insn("CMP", "R2, R0")
        b.insn("BEQ", "ret0")
        b.insn("LDRH", "R0, [R4, #0x0]")
        b.call_addr(_IS_SPELL, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "ret0")
        b.call_addr(_OFFER_GATE, R5, R4, via=R7)
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        b.label("ret0")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        blob = b.assemble(self.slot, pad="nop")
        assert_thumb1_only(blob, self.slot)
        return Compiled(((self.slot, blob, "condition"),),
                        (Row(CLS3, (cid, self.res, 0, self.slot | 1, self.cost, 0), self.phantom),))



SPEC = card(
    0x1126,
    archetype_member(KOAKI_TABLE, 0x2444),
    koaki_upkeep(filter=(0x02241471, 0x30000002), phantom=0x0E39, template=0x2264),
    quick_tribute_negate_spell(
        template=0x2264,
        template_slots=(0, 0x021F2D01, 0x021E50CD, 0),
        res=0x022062F9, cost=0x021E50CD,
        slot=cave3.CAVE3_KMW_COND, phantom=0x0E22),
    archetype_member(SPELL_SPEED_2_TABLE, 0x0E63))

PROPS = card_props("EARTH", "Rock", level=4, atk=1900, defense=1200)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_koaki_meiru_wall.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
