"""Orient Dragon (WIND / Dragon / Synchro Effect / Level 6 / 2300 / 1000) on Gaia the Dragon Champion 0x0FCB.

    1 Tuner + 1 or more non-Tuner monsters
    If this card is Synchro Summoned: Target 1 Synchro Monster your opponent controls; banish it.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, fusion_to_synchro_effect, CLS1, Compiled, Row
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass


@dataclass(frozen=True)
class synchro_summoned_banish_opponents_synchro_monster:
    """'If this card is Synchro Summoned: Target 1 Synchro Monster your opponent controls; banish it.' The proper-Synchro-
    Summon trigger list 0x0228F6C0 (36 entries, ONE reader) is full, so the membership-search `bl` at `site` goes to a
    trampoline (r0 = cid, r1 = table, r2 = count) answering 1 for the donor and the native binary search otherwise
    (r3 is preserved: the native routine PUSHes it). cls1 {banish-target resolver, opponent's face-up Synchros filter,
    standard trigger tail, +10 = 0 MANDATORY, board target-declaration} over a phantom; every slot is a native address."""
    slots: tuple                      # the cls1 action slots (+04..+14)
    phantom: int
    tramp: int                        # ov3 pool slot, 0x1C B
    site: int = 0x022658FC
    count: int = 0x24
    search: int = 0x02022E14

    def compile(self, view, cid) -> Compiled:
        b = EffectBuilder()
        b.insn("PUSH", "{R3, LR}")
        b.ldr_const(3, cid)
        b.insn("CMP", "R0, R3")
        b.insn("BEQ", "hit")
        b.call_addr(self.search, via=R3)
        b.insn("POP", "{R3, PC}")
        b.label("hit")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R3, PC}")
        blob = b.assemble(self.tramp, pad="nop")
        assert_thumb1_only(blob, self.tramp)
        assert len(blob) <= 0x1C

        def install(rom, view):
            cur, want = view.blob(self.site, 4), common_bl(self.site, self.tramp)
            if cur == want:
                return
            assert cur == common_bl(self.site, self.search), f"{self.site:#010x} holds {cur.hex()}, not the stock `bl {self.search:#010x}`"
            lst, cnt = view.u16(self.site - 4), view.u16(self.site - 2)
            assert (lst & 0xF800) == 0x4800, "expected `ldr r1,[pc,#imm]` before the call"
            assert cnt == (0x2000 | (2 << 8) | self.count), f"expected `movs r2,#{self.count:#x}` before the call, got {cnt:#06x}"
            view.write(self.site, want)

        def check(c, rom, view):
            c.eq(view.blob(self.site, 4), common_bl(self.site, self.tramp), f"hook {self.site:#010x} -> trampoline {self.tramp:#010x}")
            c.eq(view.u32(0x02265A30), 0x0228F6C0, "the pool word still names the trigger list")
            trig = [view.u16(0x0228F6C0 + i * 2) for i in range(self.count)]
            c.ok(len(set(trig)) == self.count and all(trig[i] < trig[i + 1] for i in range(self.count - 1)),
                 "the trigger list is untouched and sorted-unique")
            c.ok(cid not in trig, "the donor was NOT inserted into the list (the trampoline is the route)")

        return Compiled(((self.tramp, blob, "trigger trampoline"),),
                        (Row(CLS1, (cid, 0) + tuple(self.slots), self.phantom),),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x0FCB,
    fusion_to_synchro_effect(row=6, stock=(0x0FCC, 0x0FCD)),
    synchro_summoned_banish_opponents_synchro_monster(
        slots=(0x02219B3D,      # +04 banish the declared target
               0x021E3F01,      # +08 opponent's face-up SYNCHRO monsters
               0x0224A115,      # +0C standard trigger tail
               0x00000000,      # +10 MANDATORY (no "You can" tag)
               0x02234E11),     # +14 board target-declaration, prompt 0x125 "banish"
        phantom=0x1048, tramp=cave3.CAVE3_OD_TRIG))

PROPS = card_props("WIND", "Dragon", level=6, atk=2300, defense=1000, card_type="Synchro Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_orient_dragon.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
