"""T.G. Rush Rhino (EARTH / Beast / Level 4 / 1600 / 800) on Dash Warrior 0x22E6.

    "If this card attacks, it gains 400 ATK during the Damage Step only. Once per turn, during the End Phase, if
     this card is in the GY because it was destroyed on the field and sent there this turn: You can add 1 "T.G."
     monster from your Deck to your hand, except "T.G. Rush Rhino"."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import TG_SETCODE, TG_TABLE, add_from_deck_end_phase, archetype_member, card, card_props, Compiled
from otn_enhanced.effects import cave3
from dataclasses import dataclass


@dataclass(frozen=True)
class native_attack_boost_retuned:
    """'If this card attacks, it gains N ATK during the Damage Step only' when the donor's OWN native effect already
    does it (Dash Warrior, GDB/savestate-confirmed): its handler builds the amount as `MOV R0,#imm ; LSL R0,R0,#4`,
    so one immediate (amount = imm x 16) is rewritten. No hook, no stub; the timing is the engine's."""
    site: int
    native_imm: int
    new_imm: int

    def compile(self, view, cid) -> Compiled:
        native, new = 0x2000 | self.native_imm, 0x2000 | self.new_imm

        def install(rom, view):
            cur = view.u16(self.site)
            if cur != new:
                assert cur == native, f"ATK-amount site @{self.site:#010x} = {cur:#06x}, expected MOV R0,#{self.native_imm:#x}"
                view.set_u16(self.site, new)

        def check(c, rom, view):
            c.eq(view.u16(self.site), new, f"ATK amount @{self.site:#010x} = MOV R0,#{self.new_imm:#x} ({self.new_imm * 16})")

        return Compiled(installs=(install,), checks=(check,))



SPEC = card(
    0x22E6,
    native_attack_boost_retuned(site=0x0224DE6E, native_imm=0x4B, new_imm=0x19),
    add_from_deck_end_phase(set_code=TG_SETCODE, except_self=True,
                            slots=(cave3.CAVE3_TGR_FILTER, cave3.CAVE3_TGR_WRAPPER),
                            phantoms=(0x234E, 0x2346), shared_invoke=True),
    archetype_member(TG_TABLE, phantom=0x2514))

PROPS = card_props("EARTH", "Beast", level=4, atk=1600, defense=800)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_tg_rush_rhino.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
