"""Gravekeeper's Recruiter (DARK / Spellcaster / Level 3 / 1200 / 1500) on Battle Steer 0x0FB4.

    "If this card you control is sent to your GY: Add 1 "Gravekeeper's" monster with 1500 or less DEF
     from your Deck to your hand."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import archetype_member, card, card_props, CLS2, CLS2_SEARCH_RESOLVER, CRITERIA_1389, Compiled, LEAVE_MASK, LIST_106, LIST_30, POP_FLAGS, Row, SetCodeTable, _GET_DEF, _HAS_SETCODE, _deck_search_wrapper, _in_ov5, _template
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass


GK_TABLE =SetCodeTable("Gravekeeper's", 0x0209C986, 0x10, (0x02023778, 0x020237A4), (0x02023774, 0x02023792))


_SANGAN = 0x0FD6                      # cls2 clone source (any-means mandatory wiring)


_MASK_COUNT_SITE = 0x021C8108         # `movs r2,#0x98` -- must NOT change


_MASK_SENT_TO_GY = 0x0800             # bit 11 = destination is the GY


@dataclass(frozen=True)
class sent_to_gy_add_from_deck:
    """'If this card you control is sent to your GY: add 1 <archetype> monster with N or less DEF from your Deck.'
    Trigger = a leave-MASK row {cid, sent-to-GY}, NOT list30/list106: either list arms the dispatcher and the mask
    table is then skipped, so the donor must be in neither. The cls2 record is Sangan's any-means mandatory wiring
    (+0C=0, +10=0); mixing a list registration with a destruction-only +0C froze an earlier build.
    The search needs ONE filter doing set-code AND DEF (the engine's filters test a single property).
    `phantoms` = (cls2, populate, mask) cids dropped."""
    set_code: int
    max_def: int
    slots: tuple[int, int]      # (filter, wrapper) ov3 pool addresses
    phantoms: tuple[int, int, int]

    def compile(self, view, cid) -> Compiled:
        filt, wrap = self.slots
        assert not any(_in_ov5(a) for a in self.slots)
        cls2_tail = _template(view, CLS2, _SANGAN)[1:]
        assert cls2_tail == (0, CLS2_SEARCH_RESOLVER, 0, 0, 0, 0), "Sangan's wiring drifted"
        assert view.u16(_MASK_COUNT_SITE) == 0x2200 | LEAVE_MASK.count, "leave-mask count immediate moved"
        for lst in (LIST_30, LIST_106):
            assert cid not in view.keys(lst.base, count=lst.count, stride=2), f"donor is in {lst.label}"

        def cid_low14(b):
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")

        fb = EffectBuilder()                 # native DEF filter (0x0223C89C) with has_set_code prepended
        fb.insn("PUSH", "{R3, LR}")
        cid_low14(fb)
        fb.call_addr(_HAS_SETCODE, R0, self.set_code)
        fb.if_eq(R0, 0, "reject")
        cid_low14(fb)
        fb.call_addr(_GET_DEF, R0)
        fb.insn("LDR", "R1, [SP, #0xC]")     # criteria ptr -> the DEF ceiling (the populate 'b')
        fb.insn("LDR", "R1, [R1, #0x0]")
        fb.insn("CMP", "R0, R1")
        fb.insn("BGT", "reject")
        fb.insn("MOV", "R0, #0x1")
        fb.insn("POP", "{R3, PC}")
        fb.label("reject")
        fb.insn("MOV", "R0, #0x0")
        fb.insn("POP", "{R3, PC}")
        blobs = (fb.assemble(filt), _deck_search_wrapper(filt).assemble(wrap))
        for blob, addr in zip(blobs, self.slots):
            assert_thumb1_only(blob, addr)
        stubs = tuple(zip(self.slots, blobs, ("set-code AND DEF filter", "deck-search wrapper")))
        p2, pp, pm = self.phantoms
        rows_ = (Row(CLS2, (cid, 0, CLS2_SEARCH_RESOLVER, 0, 0, 0, 0), p2),
                 Row(CRITERIA_1389, (cid, self.max_def, wrap | 1, POP_FLAGS), pp),
                 Row(LEAVE_MASK, (cid, _MASK_SENT_TO_GY), pm))

        def check(c, rom, view):
            from otn_enhanced.asm.thumb_disasm import decode_thumb
            fins = decode_thumb(blobs[0], filt, overlay_data=bytes(view.buf), ram_base=view.base)
            c.eq({i.branch_target for i in fins if i.mnemonic == "BL"}, {_HAS_SETCODE, _GET_DEF},
                 "filter BLs -> has_set_code + get_def")
            for lst in (LIST_30, LIST_106):
                c.ok(cid not in view.keys(lst.base, count=lst.count, stride=2),
                     f"donor in NEITHER {lst.label} -- so the mask lookup is reached")
            c.eq(view.u16(_MASK_COUNT_SITE), 0x2200 | LEAVE_MASK.count, "leave-mask count immediate unchanged")

        return Compiled(stubs, rows_, checks=(check,))



GK_SETCODE = 0x0002

SPEC = card(
    0x0FB4,
    sent_to_gy_add_from_deck(set_code=GK_SETCODE, max_def=1500,
                             slots=(cave3.CAVE3_GK_FILTER, cave3.CAVE3_GK_WRAPPER),
                             phantoms=(0x0E16, 0x0E2B, 0x0E49)),
    archetype_member(GK_TABLE, phantom=0x2442))

PROPS = card_props("DARK", "Spellcaster", level=3, atk=1200, defense=1500)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_gravekeepers_recruiter.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
