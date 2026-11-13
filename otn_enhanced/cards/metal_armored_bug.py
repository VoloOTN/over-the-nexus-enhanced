"""Metal Armored Bug (EARTH / Insect / Level 8 / 2800 / 1500) on Basic Insect 0x0FD8.

    "A gigantic insect-like creature covered by thick armor. Everything in his path is destroyed."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card_props, Compiled
from dataclasses import dataclass


@dataclass(frozen=True)
class stats_only:
    """No effect: a vanilla donor re-statted and re-texted by `card_props` + CARD_TEXT. Compiles to nothing."""
    cid: int

    def compile(self, view=None) -> Compiled:
        return Compiled()



SPEC = stats_only(0x0FD8)

PROPS = card_props("EARTH", "Insect", level=8, atk=2800, defense=1500, card_type="Normal Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_test.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
