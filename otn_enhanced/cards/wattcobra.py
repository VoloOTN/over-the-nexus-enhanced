"""Wattcobra (LIGHT / Thunder / Level 4 / 1000 / 500) on Wattkid 0x0FD3.

    "This card can attack your opponent directly. When this card inflicts Battle Damage to your opponent by a
     direct attack: Add 1 "Watt" monster from your Deck to your hand."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import SetCodeTable, card, card_props, CLS1, CRITERIA_PAST_SENTINEL, Compiled, Row, _GET_DEF, _HAS_SETCODE, _IS_MONSTER, _deck_search_wrapper, _in_ov5
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.effects.common import Table
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
from otn_enhanced.effects.common import rows


LIST_DIRECT_ATTACK = Table(0x0226D730, 0x19, 2, "<H", label="direct-attack list")


LIST_DIRECT_ATTACK_DAMAGE = Table(0x0226EE7C, 0x13, 2, "<H", label="direct-attack-damage trigger list")


_BATTLE_DAMAGE_LIST_B = (0x0226EEA4, 0x33)     # the UNGATED 'inflicts Battle Damage' neighbour, asserted untouched


@dataclass(frozen=True)
class direct_attack_damage_add_from_deck:
    """'This card can attack your opponent directly. When this card inflicts Battle Damage to your opponent by a
    direct attack: Add 1 <archetype> monster from your Deck to your hand.' The trigger is a MEMBERSHIP LIST and the
    list SPLIT is the whole effect: at 0x021D020A the engine reads the direct-attack flag; if set it searches LIST A
    (the direct-attack-damage list), a MISS posts no cls1 event; right after it searches LIST B (plain 'inflicts Battle
    Damage') UNGATED. Joining A and deliberately NOT B *is* 'by a direct attack' (asserted: B untouched).
      A1 direct-attack grant list   A2 LIST A   A3 cls1 cloned from `template`'s with ONLY +04 swapped to the shared
      add-from-Deck resolver (+08 is a masked ZONE predicate, not a direct-attack test)   A4 populate row -> cloned
      wrapper + custom filter   A5 filter = set-code && IS-MONSTER && DEF <= ceiling. The is-monster test is
      load-bearing: the set-code table also lists the archetype's Spells/Traps (DEF decodes 0).
    The archetype table is ASSERTED to already hold the donor, never written. `old_donor` is handed back and pinned."""
    set_code: int
    def_ceiling: int
    template: int                 # Fane the Steel Chain's cls1 record is the template
    template_slots: tuple         # its (+04, +08, +0C, +10, +14), asserted
    resolver: int                 # the shared add-from-Deck resolver for +04
    slots: tuple[int, int]        # (filter, wrapper), ov3 pool
    phantoms: tuple[int, int, int, int]   # (direct-attack list, LIST A, cls1, populate)
    table: SetCodeTable           # the archetype table the donor must already be in

    def compile(self, view, cid) -> Compiled:
        filt, wrap = self.slots
        ph_da, ph_dad, ph1, php = self.phantoms
        assert not any(_in_ov5(a) for a in self.slots)
        tmpl = [r for r in rows(view, CLS1) if r[0] == self.template]
        assert len(tmpl) == 1 and tmpl[0][2:] == self.template_slots, f"template {self.template:#06x} cls1 not stock"
        assert self.template in keys(view, LIST_DIRECT_ATTACK) and self.template in keys(view, LIST_DIRECT_ATTACK_DAMAGE), \
            "the template lost a list membership"
        b = EffectBuilder()

        def load_cid():
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")

        b.insn("PUSH", "{R3, LR}")
        load_cid()
        b.call_addr(_HAS_SETCODE, R0, self.set_code)
        b.if_eq(R0, 0, "reject")
        load_cid()
        b.call_addr(_IS_MONSTER, R0)
        b.if_eq(R0, 0, "reject")
        load_cid()
        b.call_addr(_GET_DEF, R0)
        b.insn("LDR", "R1, [SP, #0xC]")
        b.insn("LDR", "R1, [R1, #0x0]")
        b.insn("CMP", "R0, R1")
        b.insn("BGT", "reject")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R3, PC}")
        b.label("reject")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R3, PC}")
        fb = b.assemble(filt)
        wb = _deck_search_wrapper(filt).assemble(wrap, pad="nop")
        for blob, addr in ((fb, filt), (wb, wrap)):
            assert_thumb1_only(blob, addr)
        t = self.template_slots
        record = (cid, 0, self.resolver) + t[1:]

        def install(rom, view):
            bd = view.keys(_BATTLE_DAMAGE_LIST_B[0], count=_BATTLE_DAMAGE_LIST_B[1], stride=2)
            assert cid not in bd, "the donor is in the ungated Battle Damage list"

        def check(c, rom, view):
            from otn_enhanced.effects import common
            bd = view.keys(_BATTLE_DAMAGE_LIST_B[0], count=_BATTLE_DAMAGE_LIST_B[1], stride=2)
            c.ok(cid not in bd and all(bd[i] < bd[i + 1] for i in range(len(bd) - 1)),
                 "LIST B (ungated 'inflicts Battle Damage') untouched and the donor absent -- direct-attack ONLY")
            for tbl in (LIST_DIRECT_ATTACK, LIST_DIRECT_ATTACK_DAMAGE):
                lst = keys(view, tbl)
                c.ok(all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)), f"{tbl.label}: STRICTLY sorted")
            c.eq(keys(view, CRITERIA_PAST_SENTINEL)[-1], 0xFFFF, "populate sentinel intact")
            a9 = common.view(rom)
            tb = self.table
            c.ok(a9.u32(tb.pool_ptrs[0]) == tb.base and a9.u16(tb.count_imms[0]) == 0x2200 | tb.count
                 and cid in a9.unpack(tb.base, f"<{tb.count}H"),
                 f"{tb.name} set-code table holds the donor and is stock")

        return Compiled(((filt, fb, "set-code && monster && DEF filter"), (wrap, wb, "deck-search wrapper")),
                        (Row(LIST_DIRECT_ATTACK, (cid,), ph_da), Row(LIST_DIRECT_ATTACK_DAMAGE, (cid,), ph_dad),
                         Row(CLS1, record, ph1),
                         Row(CRITERIA_PAST_SENTINEL, (cid, self.def_ceiling & 0xFFFF, wrap | 1, 0x00000002), php)),
                        installs=(install,), checks=(check,))



WATT_TABLE = SetCodeTable("Watt", 0x0209CBEA, 0x16, (0x02023EFC,), (0x02023EF8,))

SPEC = card(
    0x0FD3,
    direct_attack_damage_add_from_deck(
        set_code=0x58, def_ceiling=1500,
        template=0x2069,                                                  # Blackwing - Fane the Steel Chain
        template_slots=(0x022076A5, 0x021E32D5, 0x0224A115, 0, 0x02234E01),
        resolver=0x02207EF5,
        slots=(cave3.CAVE3_WATT_FILTER, cave3.CAVE3_WATT_WRAPPER),
        phantoms=(0x0EB3, 0x0EC0, 0x0E14, 0x2347), table=WATT_TABLE))

PROPS = card_props("LIGHT", "Thunder", level=4, atk=1000, defense=500)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_wattcobra.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
