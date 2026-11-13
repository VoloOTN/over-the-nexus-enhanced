"""Steam Synchron (WATER / Machine / Tuner / Level 3 / 600 / 800) on Cyber-Tech Alligator 0x12B6.

    During your opponent's Main Phase, you can: Immediately after this effect resolves, Synchro Summon using this card you
    control (this is a Quick Effect).
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import SetCodeTable, archetype_member, card, card_props, CLS3, CRITERIA, Compiled, Row
from otn_enhanced.effects.common import read_thunk_list as _read_thunk_list, swap_in_list as _swap_in_list  # accel_synchron
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class opponents_main_phase_quick_effect_synchro_summon_using_this_card:
    """'During your opponent's Main Phase, you can: Immediately after this effect resolves, Synchro Summon using this
    card you control (this is a Quick Effect).' Formula Synchron 0x239E ships this clause, so it is Formula's per-cid DATA
    copied onto a records-free donor -- no injected code, no ov5 slot, live in every duel mode incl. puzzles:
      cls3 {resolver 0x02249EC1 (card-agnostic phase machine), 0, condition 0x021F1491, 0, 0} over a phantom whose row is its
        only occurrence; the condition (opponent's turn, Main Phase 1/2, legal Synchro Summon, turn-log once-per-turn) is
        Formula's, so the printed card's missing once-per-turn is a KNOWN, user-accepted deviation;
      criteria row {cid, 0xFFFF, 0x0223D21D, 0x0802} over a phantom;
      ARM9 spell-speed-2 list (the responder compares speeds before ever reaching slot3; a monster is speed 1 unless listed):
        a phantom out, the donor in, count immediate + pool asserted."""
    source: int                       # Formula Synchron, the transplant source (asserted intact)
    resolver: int
    condition: int
    crit: tuple[int, int, int]        # (aux, handler, word)
    qe: tuple[int, int, int, int, int]    # (list, count imm, pool word, phantom, expected count)
    phantoms: tuple[int, int]         # (cls3, criteria)

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import read_thunk_list, swap_in_list
        ph3, phc = self.phantoms
        qe_list, qe_imm, qe_pool, qe_ph, _n = self.qe
        src3 = [r for r in rows(view, CLS3) if r[0] == self.source]
        assert src3 and src3[0][1] == self.resolver and src3[0][3] == self.condition and src3[0][2] == src3[0][4] == src3[0][5] == 0, \
            "Formula's cls3 slots drifted -- refusing to transplant"
        srcc = [r for r in rows(view, CRITERIA) if r[0] == self.source]
        assert srcc and srcc[0][1:] == self.crit, "Formula's criteria row drifted"

        def install(rom, view):
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)
            base, n, lst = read_thunk_list(bytes(d), qe_pool, qe_imm, qe_list, "spell-speed-2 list")
            if cid in lst:
                return
            assert 0x17C2 in lst and 0x0FE0 in lst and 0x1B44 in lst, "not the Quick Effect list"
            out = swap_in_list(lst, qe_ph, cid, "spell-speed-2 list")
            struct.pack_into(f"<{n}H", d, base - 0x02000000, *out)
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def check(c, rom, view):
            mc, sec = ov5_cave._arm9_main(rom)
            _, n, lst = read_thunk_list(bytes(sec.data), qe_pool, qe_imm, qe_list, "spell-speed-2")
            c.ok(cid in lst and qe_ph not in lst and n == self.qe[4] and lst == sorted(lst),
                 "spell-speed-2 list holds the donor, phantom gone, sorted, count unchanged")

        return Compiled((),
                        (Row(CLS3, (cid, self.resolver, 0, self.condition, 0, 0), ph3),
                         Row(CRITERIA, (cid,) + self.crit, phc)),
                        installs=(install,), checks=(check,))



# Names the KB proofs (author_facts.py) and accel_synchron read from this module.
RESOLVER, CONDITION = 0x02249EC1, 0x021F1491
CLS3_DROP_PHANTOM, CRIT_DROP_PHANTOM, QUICKEFFECT_DROP = 0x1528, 0x0E6E, 0x1774
SYNCHRON_STALE = 0x229E
CLS3_INDEX_ANCHORS = (223, 233, 334, 370, 527)       # cls3 rows other patches anchor BY INDEX

SYNCHRON_TABLE = SetCodeTable("Synchron", 0x0209C968, 15, (0x02023E24,), (0x02023E20,))

SPEC = card(
    0x12B6,
    opponents_main_phase_quick_effect_synchro_summon_using_this_card(
        source=0x239E,                                      # Formula Synchron
        resolver=0x02249EC1, condition=0x021F1491,
        crit=(0xFFFF, 0x0223D21D, 0x0802),
        qe=(0x0209C118, 0x02023490, 0x020234A4, 0x1774, 0x76),
        phantoms=(0x1528, 0x0E6E)),
    archetype_member(SYNCHRON_TABLE, phantom=0x229E))        # the stale member (tour_guide's old donor)

PROPS = card_props("WATER", "Machine", level=3, atk=600, defense=800, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_steam_synchron.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
