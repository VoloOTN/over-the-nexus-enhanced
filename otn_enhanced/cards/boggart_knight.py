"""XX-Saber Boggart Knight (0x13A5, on Molten Behemoth). EARTH / Beast-Warrior / Level 4 / 1900 / 1000.

    "When Normal Summoned: Special Summon 1 Level 4 or lower "X-Saber" monster from your hand."
    (+ counts as an "X-Saber"; can only be Synchro Material for an "X-Saber" Synchro Monster)
"""
from __future__ import annotations

import sys

from otn_enhanced import dsl
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass
from otn_enhanced.effects.common import rows
from otn_enhanced.dsl import CLS1, CRITERIA, Compiled, LIST_CODE7, Row, _in_ov5, _template


@dataclass(frozen=True)
class normal_summon_special_summon_from_hand:
    """'When Normal Summoned: Special Summon 1 <filter> monster from your hand' -- the phantom `template`'s code-7
    membership + cls1 record (verbatim, cid swapped) + its criteria row (`filter` = (b, handler, word), asserted
    against the template). A second row for one cid is shadowed (leftmost wins), so each insert must land as itself."""
    template: int
    slots: tuple                       # the template's cls1 action slots, asserted at build
    filter: tuple[int, int, int]
    phantoms: tuple[int, int, int]     # (code-7 list, cls1, criteria) cids dropped

    def rows(self, view, cid: int) -> tuple:
        ph7, ph1, phc = self.phantoms
        hi = _template(view, CLS1, self.template, self.slots)[1]
        b, h, fl = self.filter
        # A later card may spend the template's criteria row as ITS phantom (tg_rush_rhino spends 0x2346), so once the
        # donor owns its own row the template is no longer needed and is not re-asserted (verify re-compiles the spec).
        if not any(r[0] == cid for r in rows(view, CRITERIA)):
            assert _template(view, CRITERIA, self.template)[1:] == self.filter, "template criteria row drifted"
        return (Row(LIST_CODE7, (cid,), ph7),
                Row(CLS1, (cid, hi) + self.slots, ph1),
                Row(CRITERIA, (cid, b, h, fl), phc))

    def compile(self, view, cid) -> Compiled:
        return Compiled((), self.rows(view, cid))


_SYNCHRO_HOOK = 0x022482B2          # the replayed `ldr r0,[sp]; movs r5,#1` pair in the shared Synchro-material predicate


_SYNCHRO_HOOK_NATIVE = bytes.fromhex("00980125")


_SYNCHRO_PIVOT_LIT = 0x02248544     # must still read the template cid: anchors the predicate


@dataclass(frozen=True)
class synchro_material_only_for:
    """'Can only be used as Synchro Material for <archetype>': the predicate routes on r4 = this card's cid and r4 is
    scratch there, so a BL trampoline remapping r4 donor -> `template` makes the donor take that phantom's own
    archetype-only branch. The stub replays the two overwritten instructions and `bx lr`s back."""
    template: int
    slot: int                  # ov3 pool address (0x18 bytes)

    def compile(self, view, cid) -> Compiled:
        assert not _in_ov5(self.slot)
        b = EffectBuilder()
        b.insn("LDR", "R0, [SP, #0x0]")
        b.insn("MOV", "R5, #0x1")
        b.ldr_const(3, cid)
        b.insn("CMP", "R4, R3")
        b.insn("BNE", "other")
        b.ldr_const(4, self.template)
        b.label("other")
        b.insn("BX", "LR")
        blob = b.assemble(self.slot)
        assert_thumb1_only(blob, self.slot)
        assert len(blob) == 0x18, f"remap stub is {len(blob):#x} bytes, expected 0x18"

        def install(rom, view):
            assert view.blob(_SYNCHRO_HOOK, 4) == _SYNCHRO_HOOK_NATIVE, "synchro hook-site changed"
            assert view.u32(_SYNCHRO_PIVOT_LIT) == self.template, "synchro pivot literal changed"
            view.write(_SYNCHRO_HOOK, common_bl(_SYNCHRO_HOOK, self.slot))

        def check(c, rom, view):
            c.eq(view.blob(_SYNCHRO_HOOK, 4), common_bl(_SYNCHRO_HOOK, self.slot), "synchro hook = BL remap stub")
            c.eq(view.u32(_SYNCHRO_PIVOT_LIT), self.template, "synchro pivot literal is still the template cid")

        return Compiled(((self.slot, blob, "synchro-material remap stub"),), installs=(install,), checks=(check,))



CID = 0x13A5
BOGGART = 0x2346     # the phantom whose native rows are cloned

SPEC = dsl.card(
    CID,
    normal_summon_special_summon_from_hand(
        template=BOGGART,
        slots=(0x0220667D, 0x00000000, 0x00000000, 0x021E9A21, 0x00000000),
        filter=(0x0048, 0x0223CA71, 0x00900002),
        phantoms=(0x0E74, 0x0E11, 0x0E20)),
    synchro_material_only_for(template=BOGGART, slot=cave3.CAVE3_BOGGART),
    dsl.archetype_member(dsl.XSABER_TABLE, phantom=0x2347))

main, verify = dsl.make(SPEC, dsl.card_props("EARTH", "Beast-Warrior", 4, 1900, 1000),
                        out="data/over_the_nexus/working/rom_boggart_knight_hand_v2.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
