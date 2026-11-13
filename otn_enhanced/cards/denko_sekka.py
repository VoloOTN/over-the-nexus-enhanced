"""Denko Sekka (LIGHT / Thunder / Level 4 / 1700 / 1000) on Kojikocy 0x0FE8.

    "Cannot be Special Summoned. While you control no Set Spells/Traps, neither player can Set Spells/Traps
     nor activate Spell/Trap Cards that are Set on the field."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import CANNOT_SS_TABLE, archetype_member, card, card_props, Compiled, _in_ov5
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass


_ZONE0 = 0x0229ACC8          # player-0 zone record 0 (0x0229AC94 + 0x34); stride 0x14, player 0xB3C


_SET_SITE, _SET_STOCK = 0x021A1B4C, 0x020235F0


_FIG_SITE, _FIG_STOCK = 0x021ED614, 0x021A1430


_FIG_SITE_PRE = bytes.fromhex("a078e178674a")   # ldrb r0,[r4,#2]; ldrb r1,[r4,#3]; ldr r2,=0x1DF6


@dataclass(frozen=True)
class no_set_spell_trap_while_no_set_backrow:
    """'While you control no Set Spells/Traps, neither player can Set Spells/Traps nor activate Spell/Trap Cards
    that are Set on the field.' lock() = some side has a face-up donor in monster zones 0..4 AND no face-down card
    in its zones 5..10 (zone record player+0x34+z*0x14: +0 word, +8 face-up). Two 4-byte BL fronts in ov3 gates
    EVERY card passes, so the stubs live in the ov3 pool (puzzle-safe):
      Set  0x021A1B4C = the tail `bl 0x020235F0(cid)` of the S/T "cannot be Set" check: stock || lock().
      Fig  0x021ED614 = Cursed Fig's `bl 0x021A1430(side, zone, 0x1DF6)` in the activation-prohibited predicate
           (r4 = desc, desc[+3] = absolute zone): stock || (zone 5..10 && card there face-down && lock()).
    Monster Sets use 0x021B9690 instead and are untouched."""
    slots: tuple[int, int, int]      # (lock, fig, set), ov3 pool

    def _stubs(self, cid):
        lock, fig, setg = self.slots
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("MOV", "R6, #0x0")
        b.label("side")
        b.ldr_const(4, _ZONE0)
        b.ldr_const(0, 0xB3C)
        b.insn("MUL", "R0, R6")
        b.insn("ADD", "R4, R4, R0")
        b.insn("ADD", "R1, R4, #0x0")
        b.insn("MOV", "R5, #0x5")
        b.label("mon")
        b.insn("LDR", "R0, [R1, #0x0]")
        b.insn("LSL", "R0, R0, #18")
        b.insn("LSR", "R0, R0, #18")
        b.ldr_const(2, cid)
        b.insn("CMP", "R0, R2")
        b.insn("BNE", "mnext")
        b.insn("LDRH", "R0, [R1, #0x8]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "found")
        b.label("mnext")
        b.insn("ADD", "R1, #0x14")
        b.insn("SUB", "R5, #0x1")
        b.insn("BNE", "mon")
        b.insn("B", "snext")
        b.label("found")
        b.insn("ADD", "R1, R4, #0x0")
        b.insn("ADD", "R1, #0x64")
        b.insn("MOV", "R5, #0x6")
        b.label("st")
        b.insn("LDR", "R0, [R1, #0x0]")
        b.insn("LSL", "R0, R0, #18")
        b.insn("BEQ", "stnext")
        b.insn("LDRH", "R0, [R1, #0x8]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "snext")
        b.label("stnext")
        b.insn("ADD", "R1, #0x14")
        b.insn("SUB", "R5, #0x1")
        b.insn("BNE", "st")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("snext")
        b.insn("ADD", "R6, #0x1")
        b.insn("CMP", "R6, #0x2")
        b.insn("BLT", "side")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        lb = b.assemble(lock, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{LR}")
        b.bl(_FIG_STOCK)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "out")
        b.insn("LDRB", "R1, [R4, #0x3]")
        b.insn("CMP", "R1, #0x5")
        b.insn("BLT", "no")
        b.insn("CMP", "R1, #0xA")
        b.insn("BGT", "no")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("MOV", "R2, #0x1")
        b.insn("AND", "R0, R2")
        b.ldr_const(2, 0xB3C)
        b.insn("MUL", "R0, R2")
        b.insn("MOV", "R2, #0x14")
        b.insn("MUL", "R1, R2")
        b.insn("ADD", "R0, R0, R1")
        b.ldr_const(1, _ZONE0)
        b.insn("ADD", "R0, R0, R1")
        b.insn("LDR", "R1, [R0, #0x0]")
        b.insn("LSL", "R1, R1, #18")
        b.insn("BEQ", "no")
        b.insn("LDRH", "R1, [R0, #0x8]")
        b.insn("CMP", "R1, #0x0")
        b.insn("BNE", "no")
        b.bl(lock)
        b.insn("POP", "{PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.label("out")
        b.insn("POP", "{PC}")
        fb = b.assemble(fig, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{LR}")
        b.bl(_SET_STOCK)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "out")
        b.bl(lock)
        b.label("out")
        b.insn("POP", "{PC}")
        sb = b.assemble(setg, pad="nop")
        for blob, addr in zip((lb, fb, sb), self.slots):
            assert_thumb1_only(blob, addr)
        return lb, fb, sb

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import ov3_bl_target
        lock, fig, setg = self.slots
        assert not any(_in_ov5(a) for a in self.slots)
        lb, fb, sb = self._stubs(cid)

        def install(rom, view):
            assert view.blob(_FIG_SITE - 6, 6) == _FIG_SITE_PRE, "Fig site context changed"
            assert view.blob(_SET_SITE - 2, 2) == bytes.fromhex("281c"), "Set site: no adds r0,r5"
            for site, stock, front in ((_SET_SITE, _SET_STOCK, setg), (_FIG_SITE, _FIG_STOCK, fig)):
                cur = ov3_bl_target(view.buf, site)
                assert cur in (stock, front), f"site {site:#x} calls {cur:#x}, not stock {stock:#x}"
                view.write(site, common_bl(site, front))

        def check(c, rom, view):
            c.eq(ov3_bl_target(view.buf, _SET_SITE), setg, "Set-site bl -> lock-aware Set front")
            c.eq(ov3_bl_target(view.buf, _FIG_SITE), fig, "Fig-site bl -> lock-aware activation front")

        return Compiled(((lock, lb, "lock"), (fig, fb, "activation front"), (setg, sb, "set front")),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x0FE8,
    archetype_member(CANNOT_SS_TABLE, 0x19A8),
    no_set_spell_trap_while_no_set_backrow(
        slots=(cave3.CAVE3_DENKO_LOCK, cave3.CAVE3_DENKO_FIG, cave3.CAVE3_DENKO_SET)))

PROPS = card_props("LIGHT", "Thunder", level=4, atk=1700, defense=1000)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_denko_sekka.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
