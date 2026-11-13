"""Mathematician (EARTH / Spellcaster / Level 3 / 1500 / 500) on Boneheimer 0x13B6.

    "When this card is Normal Summoned: You can send 1 Level 4 or lower monster from your Deck to the GY.
     When this card is destroyed by battle and sent to the GY: You can draw 1 card."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card_props, CLS1, CLS2, CRITERIA, Compiled, DRAW_COUNT, LIST_106, LIST_CODE7, Row, _template
from dataclasses import dataclass


CRIT_SELECT_FROM_DECK = 0x0223CAD9


LEVEL_4_OR_LOWER_MONSTER = 0x00900002   # 0x0090 = the level bits Reinforcement of the Army ships on this handler


@dataclass(frozen=True)
class normal_summon_send_from_deck:
    """'When Normal Summoned: send 1 <filter> monster from your Deck to the GY' -- the native
    `template` card's code-7 membership + cls1 record, plus the criteria row that picks the monster."""
    template: int
    slots: tuple                     # the template's cls1 action slots, asserted at build
    filter: int                      # criteria word (what the Deck-send may pick)
    phantoms: tuple[int, int, int]   # (code-7 list, cls1, criteria) cids dropped

    def rows(self, view, cid: int) -> tuple:
        ph7, ph1, phc = self.phantoms
        hi = _template(view, CLS1, self.template, self.slots)[1]
        return (Row(LIST_CODE7, (cid,), ph7),
                Row(CLS1, (cid, hi) + self.slots, ph1),
                Row(CRITERIA, (cid, 0xFFFF, CRIT_SELECT_FROM_DECK, self.filter), phc))


@dataclass(frozen=True)
class battle_destroyed_draw:
    """'When destroyed by battle and sent to the GY: you can draw N card(s)' -- the native `template`'s
    list106 membership + cls2 record. The draw-count row is load-bearing: without it 0x02206304 returns 0
    and 0x021F069D never offers the effect."""
    template: int
    slots: tuple                     # the template's cls2 action slots, asserted at build
    count: int
    phantoms: tuple[int, int, int]   # (list106, cls2, draw-count) cids dropped

    def rows(self, view, cid: int) -> tuple:
        ph106, ph2, phd = self.phantoms
        hi = _template(view, CLS2, self.template, self.slots)[1]
        assert _template(view, DRAW_COUNT, self.template)[1] == self.count, "template draws a different count"
        return (Row(LIST_106, (cid,), ph106),
                Row(CLS2, (cid, hi) + self.slots, ph2),
                Row(DRAW_COUNT, (cid, self.count), phd))


@dataclass(frozen=True)
class table_card:
    """A card made only of table rows (no injected code): works in every duel mode."""
    cid: int
    effects: tuple

    def __init__(self, cid, *effects):
        object.__setattr__(self, "cid", cid)
        object.__setattr__(self, "effects", effects)

    def compile(self, view) -> Compiled:
        return Compiled((), tuple(r for e in self.effects for r in e.rows(view, self.cid)))



SPEC = table_card(
    0x13B6,
    normal_summon_send_from_deck(      # Armageddon Knight 0x1CFF, minus its DARK filter
        template=0x1CFF,
        slots=(0x02208DD5, 0, 0x021F0B19, 0x021E51E5, 0),
        filter=LEVEL_4_OR_LOWER_MONSTER,
        phantoms=(0x15D0, 0x0E1F, 0x0E3C)),
    battle_destroyed_draw(             # Cyber Phoenix 0x1A07
        template=0x1A07,
        slots=(0x022065B9, 0, 0x021F069D, 0x021E51E5, 0),
        count=1,
        phantoms=(0x1B46, 0x0E1C, 0x16C1)))

PROPS = card_props("EARTH", "Spellcaster", level=3, atk=1500, defense=500)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_mathematician.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
