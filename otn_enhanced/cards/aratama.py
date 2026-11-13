"""Aratama (DARK / Fiend / Spirit / Level 4 / 800 / 1800) on Souleater 0x13AC.

    "Cannot be Special Summoned. During the End Phase of the turn this card is Normal Summoned or flipped
     face-up: Return it to the hand. When this card is Normal Summoned or flipped face-up: You can add
     1 Spirit monster from your Deck to your hand, except "Aratama"."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import FLIPPED_FACE_UP_TABLE, archetype_member, card, card_genre_word, card_props, CLS1, CRITERIA, Compiled, LIST_CODE78, Row
from dataclasses import dataclass
from otn_enhanced.effects.common import rows


@dataclass(frozen=True)
class spirit_summon_search:
    """Spirit with 'When Normal Summoned or flipped face-up: add 1 <filter> monster from your Deck to your hand':
    card_type Spirit does 'cannot be Special Summoned' natively and its FIRST cls1 record must be the shared bounce
    (find_event_handler offsets to leftmost+1 for Spirits), so a cls1 PAIR [bounce, search] goes under the cid, both
    over the two rows of one phantom Spirit. The bounce is `bounce_template`'s first record; the search is
    `search_template`'s with +10 swapped to `search_slots`' (every native flipped-face-up 'you can'). The criteria
    row is `filter` = (aux, handler, word). Flip Summon only is covered by the code-7-or-8 list; a battle flip
    needs `archetype_member(FLIPPED_FACE_UP_TABLE, ...)` too."""
    bounce_template: int
    bounce_slots: tuple          # the bounce record's action slots, asserted
    search_template: int
    search_template_slots: tuple  # the search template's slots, asserted
    search_slots: tuple           # what the donor's search record carries
    filter: tuple[int, int, int]
    phantoms: tuple[int, int, int]   # (code-7-or-8 list, cls1 PAIR, criteria) cids dropped

    def _pair(self, view, cid):
        mah = [r for r in rows(view, CLS1) if r[0] == self.bounce_template]
        sen = [r for r in rows(view, CLS1) if r[0] == self.search_template]
        assert len(mah) == 2 and mah[0][2:] == self.bounce_slots, f"bounce cls1 drifted: {mah}"
        assert len(sen) == 1 and sen[0][2:] == self.search_template_slots, f"search cls1 drifted: {sen}"
        return [(cid, mah[0][1]) + self.bounce_slots, (cid, sen[0][1]) + self.search_slots]

    def compile(self, view, cid) -> Compiled:
        ph78, ph1, phc = self.phantoms
        pair = self._pair(view, cid)
        aux, handler, word = self.filter

        def install(rom, view):
            """Count-neutral: drop both rows of the phantom, insert the pair adjacent, bounce first."""
            recs = list(rows(view, CLS1))
            if [r for r in recs if r[0] == cid] == pair:
                return
            assert not any(r[0] == cid for r in recs), "donor already owns cls1 rows"
            assert sum(r[0] == ph1 for r in recs) == 2, f"phantom {ph1:#06x} lost its 2 cls1 rows"
            recs = [r for r in recs if r[0] != ph1]
            pos = sum(1 for r in recs if r[0] <= cid)
            recs[pos:pos] = pair
            assert len(recs) == CLS1.count and [r[0] for r in recs] == sorted(r[0] for r in recs)
            for i, r in enumerate(recs):
                view.pack(CLS1.addr(i), CLS1.fmt, *r)

        def check(c, rom, view):
            recs = rows(view, CLS1)
            ks = [r[0] for r in recs]
            c.ok([r for r in recs if r[0] == cid] == pair and ph1 not in ks and ks == sorted(ks),
                 "cls1 pair [bounce, search] under the donor, phantom spent, sorted")

        return Compiled(rows=(Row(LIST_CODE78, (cid,), ph78),
                              Row(CRITERIA, (cid, aux, handler, word), phc)),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x13AC,
    spirit_summon_search(
        bounce_template=0x14FD,                             # Maharaghi
        bounce_slots=(0x0220A901, 0, 0, 0x021E88A9, 0),
        search_template=0x1334,                             # Senju of the Thousand Hands
        search_template_slots=(0x02207EF5, 0, 0x021F0821, 0x021E50DD, 0),
        search_slots=(0x02207EF5, 0, 0x021F0821, 0x021E51E5, 0),
        filter=(0x0007, 0x02241EA5, 0x00000022),            # Spirit, not this card
        phantoms=(0x12B4, 0x1506, 0x0E9D)),
    archetype_member(FLIPPED_FACE_UP_TABLE, 0x1527),
    card_genre_word(0x0000000001400020))

PROPS = card_props("DARK", "Fiend", level=4, atk=800, defense=1800, card_type="Spirit Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_aratama.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
