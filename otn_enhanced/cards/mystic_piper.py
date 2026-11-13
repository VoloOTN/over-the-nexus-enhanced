"""Mystic Piper (LIGHT / Spellcaster / Level 1 / 0 / 0) on Flame Dancer 0x13B8.

    "You can Tribute this card to draw and reveal 1 card. If that card is a Level 1 Monster Card,
     draw 1 more card. The effect of "Mystic Piper" can only be activated once per turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card_props, draw, ignition, once_per_turn, revealed, tribute_self
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R5
from dataclasses import dataclass


@dataclass(frozen=True)
class draw_and_reveal:
    """'draw and reveal N card(s)'. Peeks the Deck top first: the engine's draw is queued."""
    count: int

    def lower(self, b, ctx):
        assert self.count == 1, "peek reads the top card only"
        b.call("reveal_top", ctx.side)
        ctx.revealed = b.peek_deck_top_cid(ctx.side, dest=R5, scratch=(R2, R3))
        b.call("draw", ctx.side, 1)


@dataclass(frozen=True)
class if_:
    cond: object
    then: tuple

    def __init__(self, cond, *then):
        object.__setattr__(self, "cond", cond)
        object.__setattr__(self, "then", then)

    def lower(self, b, ctx):
        done = ctx.label()
        self.cond.lower_skip(b, ctx, done)
        for a in self.then:
            a.lower(b, ctx)
        b.label(done)



SPEC = ignition(
    0x13B8,
    cost=tribute_self(),
    limit=once_per_turn(),
    effect=[draw_and_reveal(1), if_(revealed.is_level(1), draw(1))],
    slots=(cave3.CAVE3_PIPER_RES, cave3.CAVE3_PIPER_COND, cave3.CAVE3_PIPER_COST),
    phantom=0x1436)

PROPS = card_props("LIGHT", "Spellcaster", level=1, atk=0, defense=0)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_mystic_piper.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
