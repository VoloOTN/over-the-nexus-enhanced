"""Kuribandit (DARK / Fiend / Level 3 / 1000 / 700) on Torike 0x0FD5.

    "During the End Phase, if this card was Normal Summoned this turn: You can Tribute this card; excavate the top
     5 cards of your Deck, you can add 1 excavated Spell/Trap to your hand, also send the remaining cards to the
     Graveyard."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS1, CRITERIA, Compiled, Row, _DECK_COUNT_WORD, _PLAYER_BASE, _RES_STATE, _UI_RESULT, _ZONE_WORD
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass


_POD_RES, _POD_HANDLER, _CANDIDATES = 0x0222FD90, 0x02242F09, 0x02243FE0


_YES_NO, _PICKER, _MILL_BL = 0x0219AAAC, 0x0219C430, 0x021D2148        # NOT _MILL (0x021D2149, line 1159)


_ENDPHASE_NS_ROW = 0x0228E1E0 + 188 * 8     # End-Phase registry section row 188


_ENDPHASE_NS_POSTER, _ENDPHASE_NS_PHANTOM = 0x02253F89, 0x1A1F


_YOU_CAN_TAG_1 = 0x021E50DD                 # class-1 "You can" tag (Yes/No, runs +0C)


_TRIBUTE_SLOT = 0x021E50CD                  # native Tribute-this-card slot


@dataclass(frozen=True)
class end_phase_tribute_excavate_add_spell_trap:
    """'During the End Phase, if this card was Normal Summoned this turn: You can Tribute this card; excavate the top
    N cards of your Deck, you can add 1 excavated Spell/Trap to your hand, also send the remaining cards to the GY.'
    User rulings: Deck < N -> cannot activate; 'you can add' = a Yes/No before the picker. Pieces, each copied from a
    native owner:
      timing  End-Phase registry row {0x02253F89, cid} (Genex Neutron's 'if Normal Summoned this turn'); the
              phantom row already carries the poster, so only its cid halfword changes.
      cls1    {+04 RES, +0C COND, +10 class-1 'You can' tag, +14 native Tribute}: a Tribute in +10 would be
              unclassified and silently dropped; the chain machine runs slot4 then slot5.
      COND    desc[+7] guard (the Tribute cleared the zone), Deck >= N, zone-word bit 16. NOT Neutron's tail
              0x021F0820 (needs a criteria candidate = hidden Deck contents).
      RES     wrapper around Pot of Duality's resolver: 0x80 list builder with N not 3; 0x7D no S/T among the top N
              -> mill N, else Yes/No 0x0219AAAC (the tag body's real prompt, NOT 0x0219A818 whose prompt 0x107 is
              the OK-only miss-timing notice); 0x7B No -> mill N, Yes -> picker; 0x64 mill N-1 (instead of PoD's
              shuffle); other phases native.
      filter  criteria row {cid, 0xFFFF, PoD's handler, Spell|Trap bits} (Deck enumerator, top-N cap = flags>>25)."""
    count: int
    slots: tuple[int, int]        # (cond, res), ov5
    phantoms: tuple[int, int]     # (cls1, criteria)
    type_bits: int                # criteria word: card-type bits Spell|Trap

    def compile(self, view, cid) -> Compiled:
        assert self.count == 5
        cond, res = self.slots
        ph1, phc = self.phantoms
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "ok")
        b.insn("LDRB", "R2, [R4, #0x2]")
        b.insn("MOV", "R0, #0x1")
        b.insn("AND", "R0, R2")
        b.ldr_const(1, 0xB3C)
        b.insn("MUL", "R0, R1")
        b.ldr_const(1, _DECK_COUNT_WORD)
        b.insn("LDR", "R1, [R0, R1]")
        b.insn("CMP", "R1, #0x5")
        b.insn("BLT", "fail")
        b.insn("LDRB", "R3, [R4, #0x3]")
        b.insn("MOV", "R1, #0x14")
        b.insn("MUL", "R1, R3")
        b.insn("ADD", "R0, R0, R1")
        b.ldr_const(1, _ZONE_WORD)
        b.insn("LDR", "R0, [R0, R1]")
        b.insn("LSR", "R0, R0, #0x10")
        b.insn("MOV", "R1, #0x1")
        b.insn("TST", "R0, R1")
        b.insn("BEQ", "fail")
        b.label("ok")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, PC}")
        b.label("fail")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        cb = b.assemble(cond)
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("ADD", "R7, R1, #0x0")
        b.insn("LDRB", "R5, [R4, #0x2]")
        b.insn("LDRB", "R0, [R4, #0x6]")
        b.insn("EOR", "R5, R0")
        b.ldr_const(6, _RES_STATE)
        b.insn("LDR", "R0, [R6, #0x70]")
        b.insn("CMP", "R0, #0x80")
        b.insn("BEQ", "build")
        b.insn("CMP", "R0, #0x7D")
        b.insn("BEQ", "ask")
        b.insn("CMP", "R0, #0x7B")
        b.insn("BEQ", "answer")
        b.insn("CMP", "R0, #0x64")
        b.insn("BEQ", "mill4")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("ADD", "R1, R7, #0x0")
        b.bl(_POD_RES)
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("build")
        b.insn("MOV", "R0, #0x1")
        b.insn("AND", "R0, R5")
        b.ldr_const(1, 0xB3C)
        b.insn("MUL", "R0, R1")
        b.ldr_const(1, _PLAYER_BASE)
        b.insn("ADD", "R6, R0, R1")
        b.insn("MOV", "R3, #0x0")
        b.insn("STRH", "R3, [R4, #0x12]")
        b.label("loop")
        b.insn("LDR", "R0, [R6, #0x10]")
        b.insn("CMP", "R3, R0")
        b.insn("BCS", "built")
        b.insn("LSL", "R0, R3, #0x2")
        b.insn("ADD", "R0, R6, R0")
        b.insn("MOV", "R1, #0xC1")
        b.insn("LSL", "R1, R1, #0x2")
        b.insn("LDR", "R1, [R0, R1]")
        b.insn("LSL", "R0, R1, #0x11")
        b.insn("LSR", "R0, R0, #0x1F")
        b.insn("LSL", "R1, R1, #0x1")
        b.insn("LSR", "R1, R1, #0x18")
        b.insn("LSL", "R1, R1, #0x1")
        b.insn("ADD", "R0, R0, R1")
        b.insn("LSL", "R1, R3, #0x1")
        b.insn("ADD", "R1, R4, R1")
        b.insn("STRH", "R0, [R1, #0x14]")
        b.insn("ADD", "R3, #0x1")
        b.insn("STRH", "R3, [R4, #0x12]")
        b.insn("CMP", "R3, #0x5")
        b.insn("BLT", "loop")
        b.label("built")
        b.ldr_const(6, _RES_STATE)
        b.insn("MOV", "R1, #0x0")
        b.insn("STR", "R1, [R6, #0x74]")
        b.insn("MOV", "R0, #0x7F")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("ask")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.insn("MOV", "R2, #0x5")
        b.bl(_CANDIDATES)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "mill5")
        b.insn("LDRH", "R2, [R4, #0xC]")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("MOV", "R1, #0xFA")
        b.bl(_YES_NO)
        b.insn("MOV", "R0, #0x7B")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("answer")
        b.ldr_const(0, _UI_RESULT)
        b.insn("LDR", "R0, [R0, #0x34]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "mill5")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0x6")
        b.insn("LDRH", "R2, [R4, #0x0]")
        b.insn("MOV", "R3, #0x5")
        b.bl(_PICKER)
        b.insn("MOV", "R0, #0x7C")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("mill5")
        b.insn("MOV", "R2, #0x5")
        b.insn("B", "mill")
        b.label("mill4")
        b.insn("MOV", "R2, #0x4")
        b.label("mill")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("ADD", "R1, R5, #0x0")
        b.bl(_MILL_BL)
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        rb = b.assemble(res)
        for blob, addr in ((cb, cond), (rb, res)):
            assert_thumb1_only(blob, addr)

        def install(rom, view):
            fn, cur = view.unpack(_ENDPHASE_NS_ROW, "<IH")
            if cur != cid:
                assert (fn, cur) == (_ENDPHASE_NS_POSTER, _ENDPHASE_NS_PHANTOM), f"registry row 188 is {fn:#x}/{cur:#x}"
                view.set_u16(_ENDPHASE_NS_ROW + 4, cid)

        def check(c, rom, view):
            c.eq(view.unpack(_ENDPHASE_NS_ROW, "<IH"), (_ENDPHASE_NS_POSTER, cid), "End-Phase registry row 188")

        return Compiled(((cond, cb, "condition"), (res, rb, "resolver")),
                        (Row(CLS1, (cid, 0, res | 1, 0, cond | 1, _YOU_CAN_TAG_1, _TRIBUTE_SLOT), ph1),
                         Row(CRITERIA, (cid, 0xFFFF, _POD_HANDLER, self.type_bits), phc)),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x0FD5,
    end_phase_tribute_excavate_add_spell_trap(
        count=5, slots=(ov5_cave.CAVE_KURIBANDIT_COND, ov5_cave.CAVE_KURIBANDIT_RES),
        phantoms=(0x1441, 0x0E34), type_bits=0x0000000C))

PROPS = card_props("DARK", "Fiend", level=3, atk=1000, defense=700)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_kuribandit.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
