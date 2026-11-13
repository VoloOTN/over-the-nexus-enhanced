"""XX-Saber Darksoul (0x1783, on Gigobyte). EARTH / Beast / Level 3 / 100 / 100.

    "During the End Phase, if this card was sent from your side of the field to your
     Graveyard this turn: You can add 1 "X-Saber" monster from your Deck to your hand."
"""
from __future__ import annotations

import sys

from otn_enhanced import dsl
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass
import struct
from otn_enhanced.dsl import CLS2, CLS2_DELAYED_END_PHASE, CLS2_SEARCH_RESOLVER, CRITERIA_1389, Compiled, POP_FLAGS, REG_ENDPHASE_RESOLVER, Row, _in_ov5


_ANY_LEAVE_ROOT = 0x021C9F1C         # leave-tree 2 root: `ldr r0,[pc,#0x9C]; cmp r4,r0` (NOT the T.G. tree at 0x021C8216)


_ANY_LEAVE_NATIVE = (0x4827, 0x4284)


_ANY_LEAVE_LIT = 0x00001A64          # what that LDR loads, replayed by the stub


_ANY_LEAVE_GATE = 0x021CA640         # arms the End-Phase trigger for r4 with NO destroyed test


CLS2_ANY_ELIGIBLE_ENDPHASE = 0x021F0821


REG_ANYLEAVE_ROW = 0x0228E598        # spare registry row (position 119 == timing, End-Phase section)


REG_ANYLEAVE_BEFORE = (0x02254321, 0x0E6C)


@dataclass(frozen=True)
class end_phase_add_if_sent_to_gy:
    """'During the End Phase, if this card was sent from your side of the field to your GY this turn (by ANY
    means): you can add 1 <archetype> monster from your Deck.' Arms on ANY leave via leave-tree 2's root, never
    the shared T.G. trampoline (it gates on DESTROYED: battle armed, Synchro Material did not). The stub's
    `cmp r4,r0` MUST stay last before `bx lr`: 0x021C9F20 is a BLE consuming those flags.
    `filter` = (populate `b`, native archetype Deck filter handler). `phantoms` = (cls2, populate) cids dropped."""
    filter: tuple[int, int]
    slot: int                   # ov3 pool address of the arming trampoline
    phantoms: tuple[int, int]
    registry_phantom: int = 0x0E6C

    def compile(self, view, cid) -> Compiled:
        assert not _in_ov5(self.slot)
        b = EffectBuilder()
        b.ldr_const(1, cid)
        b.insn("CMP", "R4, R1")
        b.insn("BNE", "other")
        b.ldr_const(1, _ANY_LEAVE_GATE | 1)
        b.insn("BX", "R1")
        b.label("other")
        b.ldr_const(0, _ANY_LEAVE_LIT)
        b.insn("CMP", "R4, R0")
        b.insn("BX", "LR")
        blob = b.assemble(self.slot)
        assert_thumb1_only(blob, self.slot)
        p2, pp = self.phantoms
        rows_ = (Row(CLS2, (cid, 0, CLS2_SEARCH_RESOLVER, 0, CLS2_ANY_ELIGIBLE_ENDPHASE, CLS2_DELAYED_END_PHASE, 0), p2),
                 Row(CRITERIA_1389, (cid, self.filter[0], self.filter[1], POP_FLAGS), pp))

        def install(rom, view):
            want = struct.unpack("<2H", common_bl(_ANY_LEAVE_ROOT, self.slot))
            assert view.unpack(_ANY_LEAVE_ROOT, "<2H") == _ANY_LEAVE_NATIVE, "any-leave hook site moved"
            view.pack(_ANY_LEAVE_ROOT, "<2H", *want)
            assert view.unpack(REG_ANYLEAVE_ROW, "<IH") == REG_ANYLEAVE_BEFORE, "registry row 119 is not the phantom"
            view.pack(REG_ANYLEAVE_ROW, "<IH", REG_ENDPHASE_RESOLVER, cid)

        def check(c, rom, view):
            from otn_enhanced.effects.tg_table import CAVE_TG_ARM_OK
            c.eq(view.unpack(REG_ANYLEAVE_ROW, "<IH"), (REG_ENDPHASE_RESOLVER, cid), "registry row 119 invokes the End-Phase registrar")
            c.eq(view.blob(_ANY_LEAVE_ROOT, 4), common_bl(_ANY_LEAVE_ROOT, self.slot), "any-leave hook = BL arming trampoline")
            c.ok(not CAVE_TG_ARM_OK(rom, view.buf, cid), "NOT on the DESTROYED-filtered T.G. trampoline (0x021C8216)")

        return Compiled(((self.slot, blob, "any-leave arming trampoline"),), rows_, installs=(install,), checks=(check,))



CID = 0x1783

SPEC = dsl.card(
    CID,
    end_phase_add_if_sent_to_gy(filter=(0x0048, 0x0223CAF5), slot=cave3.CAVE3_DS_ARMTRAMP,
                                    phantoms=(0x0E15, 0x0E21)),
    dsl.archetype_member(dsl.XSABER_TABLE, phantom=0x2346))

main, verify = dsl.make(SPEC, dsl.card_props("EARTH", "Beast", 3, 100, 100),
                        out="data/over_the_nexus/working/rom_darksoul.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
