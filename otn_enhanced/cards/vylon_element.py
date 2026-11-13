"""Vylon Element (Continuous Spell) on 0x24B5.

    "If any face-up "Vylon" Equip Card(s) you control are destroyed (except during the Damage Step): You can
     Special Summon 1 "Vylon" Tuner monster from your Deck. It cannot be used as Synchro Material, except for
     the Synchro Summon of a "Vylon" Synchro Monster."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, CLS1, Compiled, Edit, _template
from dataclasses import dataclass


@dataclass(frozen=True)
class cls1_transplant:
    """The donor's cls1 record rewritten in place to a native `template`'s whole action slots (+04 driver, +0C
    condition, +10 tag, +14 tail) -- every partial transplant resolves to NOTHING, so all move together. E.g.
    Gravekeeper's Spy's: driver 0x02206CAD (populate -> pick-1 menu -> Special Summon), +0C 0x0224A115 (offered
    unconditionally), +10 = 0 (class 0: a properly classified trigger with NO Yes/No prompt; NOT a miss-timing
    bypass and NOT "IF"), +14 none. `native` is the donor's stock record; `slots` asserted against the template."""
    native: tuple
    template: int
    slots: tuple

    def compile(self, view, cid) -> Compiled:
        _template(view, CLS1, self.template, self.slots)
        return Compiled(edits=(Edit(CLS1, cid, self.native, (cid, 0) + self.slots),))



SPEC = card(
    0x24B5,
    cls1_transplant(
        native=(0x24B5, 0, 0x0221DA95, 0, 0x021F0419, 0x021E51E5, 0x0223913D),
        template=0x1585,                                        # Gravekeeper's Spy
        slots=(0x02206CAD, 0, 0x0224A115, 0, 0)))

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_vylon_element.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
