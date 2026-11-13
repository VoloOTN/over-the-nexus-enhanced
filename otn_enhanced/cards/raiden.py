"""Raiden, Hand of the Lightsworn (LIGHT / Warrior / Tuner / Level 4 / 1700 / 1000) on Rogue Doll 0x0FD2.

    "During your Main Phase: You can send the top 2 cards of your Deck to the Graveyard, then if any "Lightsworn"
     monsters were sent to the Graveyard by this effect, this card gains 200 ATK until the end of your opponent's
     turn. You can only use this effect of "Raiden, Hand of the Lightsworn" once per turn. Once per turn, during your
     End Phase: Send the top 2 cards of your Deck to the Graveyard."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import archetype_member, card, card_genre_word, card_props, CLS1, CLS3, Compiled, Row, SetCodeTable, _HAS_SETCODE, _IS_MONSTER, _PLAYER_BASE
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass


LIGHTSWORN_TABLE = SetCodeTable("Lightsworn", 0x0209C94A, 15, (0x02023BC0,), (0x02023BBC,))


_STILL_THERE, _ATTACH, _NATIVE_IGNITION_COND = 0x021D2C1C, 0x021C479C, 0x021F06E8


_MILL_RAIDEN = 0x021D2148


_EP_POSTER, _EP_REG_ROW_100 = 0x02253EC9, 0x0228E1E0 + 100 * 8


_ALWAYS_OK = 0x0224A115


@dataclass(frozen=True)
class mill_two_ignition_and_end_phase:
    """'During your Main Phase: You can send the top 2 cards of your Deck to the GY, then if any "<archetype>" monsters were
    sent by this effect, this card gains 200 ATK until the end of your opponent's turn (once per turn). Once per turn,
    during your End Phase: Send the top 2 cards of your Deck to the GY.'
      C2  Jain's shape: End-Phase registry row 100 {0x02253EC9 (turn-player-only poster), phantom} -> cid rewritten, and
          cls1 {cid, EP|1, 0, 0x0224A115, 0, 0} over the same phantom (Jain's resolver defaults to 3 for an unlisted cid, so
          +04 is an ov5 copy of its guards that mills 2).
      C1  the Mystic Piper ignition recipe: cls3 {cid, RES, 0, COND, COST, 0} over a phantom. COND: desc[+7] guard, Deck >= 2
          (user decision), cid turn-log query, native 0x021F06E8. COST: turn-log post (no printed cost). RES: peek Deck[0..1]
          (player+0x304), mill 2, and if either was a <archetype> monster and this card is still there, attach rider
          {key 0x216D, kind 0x12}: 0x216D = The Fabled Ganashia's ATK-table-2 row {+200, 0}, a literal (not the +-1 sentinel),
          so the walker adds a flat 200 whatever the param; countdown 1 = until the end of the next turn.
    slots = (onfield, ep, cond, cost, res), ov5."""
    set_code: int
    gain_key: int
    gain_kind: int
    slots: tuple[int, int, int, int, int]
    phantoms: tuple[int, int]        # (End-Phase cls1/registry phantom, cls3 phantom)

    def compile(self, view, cid) -> Compiled:
        onf, ep, cond, cost, res = self.slots
        ph_ep, ph3 = self.phantoms

        def player(b, dst, side, tmp, base=_PLAYER_BASE):
            skip = f"p_{dst!r}_{side!r}"
            b.insn("MOV", f"{tmp!r}, #0x1")
            b.insn("AND", f"{side!r}, {tmp!r}")
            b.ldr_const(int(dst), base)
            b.insn("CMP", f"{side!r}, #0x0")
            b.insn("BEQ", skip)
            b.ldr_const(int(tmp), 0xB3C)
            b.insn("ADD", f"{dst!r}, {dst!r}, {tmp!r}")
            b.label(skip)

        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("LDRB", "R1, [R0, #0x3]")
        b.insn("LSL", "R3, R1, #0x4")
        b.insn("LSL", "R1, R1, #0x2")
        b.insn("ADD", "R3, R3, R1")
        b.insn("LDRB", "R2, [R0, #0x2]")
        player(b, R4, R2, R1)
        b.insn("ADD", "R4, R4, R3")
        b.insn("LDR", "R1, [R4, #0x34]")
        b.insn("LSL", "R2, R1, #0x11")
        b.insn("LSR", "R2, R2, #0x1F")
        b.insn("LSL", "R1, R1, #0x1")
        b.insn("LSR", "R1, R1, #0x18")
        b.insn("LSL", "R1, R1, #0x1")
        b.insn("ADD", "R1, R1, R2")
        b.insn("LDRH", "R2, [R0, #0xC]")
        b.insn("CMP", "R2, R1")
        b.insn("BNE", "no")
        b.insn("LDR", "R1, [R4, #0x44]")
        b.insn("LSR", "R1, R1, #0x1A")
        b.insn("MOV", "R2, #0x1")
        b.insn("AND", "R1, R2")
        b.insn("BNE", "no")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        onb = b.assemble(onf, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(onf, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "out")
        b.call_addr(_STILL_THERE, R4, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "out")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDRB", "R1, [R4, #0x2]")
        b.call_addr(_MILL_RAIDEN, R0, R1, 2, via=R7)
        b.label("out")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R7, PC}")
        epb = b.assemble(ep, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "chain")
        b.insn("LDRB", "R0, [R4, #0x2]")
        player(b, R1, R0, R2, _PLAYER_BASE + 0x10)
        b.insn("LDR", "R1, [R1, #0x0]")
        b.insn("CMP", "R1, #0x2")
        b.insn("BLT", "no")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRH", "R2, [R4, #0x0]")
        b.turnlog_query(R0, R2, 1, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.label("chain")
        b.call_addr(_NATIVE_IGNITION_COND, R4, via=R7)
        b.insn("POP", "{R4, R7, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R7, PC}")
        cb = b.assemble(cond, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.turnlog_post(R0, R1, 1, via=R7)
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R7, PC}")
        kb = b.assemble(cost, pad="nop")

        def check_slot(b, slot, skip):
            b.insn("LDR", f"R0, [R5, #{slot * 4:#x}]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("STR", "R0, [SP, #0x0]")
            b.call_addr(_IS_MONSTER, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", skip)
            b.insn("LDR", "R0, [SP, #0x0]")
            b.insn("MOV", f"R1, #{self.set_code:#x}")
            b.call_addr(_HAS_SETCODE, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", skip)
            b.insn("MOV", "R6, #0x1")
            b.label(skip)

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("SUB", "SP, #0x8")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        player(b, R5, R0, R1)
        b.insn("LDR", "R0, [R5, #0x10]")
        b.insn("STR", "R0, [SP, #0x4]")
        b.ldr_const(1, 0x304)
        b.insn("ADD", "R5, R5, R1")
        b.insn("MOV", "R6, #0x0")
        b.insn("LDR", "R0, [SP, #0x4]")
        b.insn("CMP", "R0, #0x1")
        b.insn("BLT", "mill")
        check_slot(b, 0, "c0")
        b.insn("LDR", "R0, [SP, #0x4]")
        b.insn("CMP", "R0, #0x2")
        b.insn("BLT", "mill")
        check_slot(b, 1, "c1")
        b.label("mill")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDRB", "R1, [R4, #0x2]")
        b.call_addr(_MILL_RAIDEN, R0, R1, 2, via=R7)
        b.insn("CMP", "R6, #0x0")
        b.insn("BEQ", "done")
        b.call_addr(onf, R4, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "done")
        b.insn("MOV", "R0, #0xC8")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRB", "R1, [R4, #0x3]")
        b.call_addr(_ATTACH, R0, R1, self.gain_key, self.gain_kind, via=R7)
        b.label("done")
        b.insn("MOV", "R0, #0x0")
        b.insn("ADD", "SP, #0x8")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        rb = b.assemble(res, pad="nop")
        blobs = (onb, epb, cb, kb, rb)
        for blob, addr in zip(blobs, self.slots):
            assert_thumb1_only(blob, addr)

        def install(rom, view):
            fn, cur = view.unpack(_EP_REG_ROW_100, "<IH")
            if cur != cid:
                assert (fn, cur) == (_EP_POSTER, ph_ep), f"registry row 100 is {fn:#x}/{cur:#x}"
                view.set_u16(_EP_REG_ROW_100 + 4, cid)

        def check(c, rom, view):
            c.eq(view.unpack(_EP_REG_ROW_100, "<IH"), (_EP_POSTER, cid), "End-Phase registry row 100")

        names = ("on-field check", "End-Phase mill", "ignition cond", "ignition cost", "ignition resolver")
        return Compiled(tuple(zip(self.slots, blobs, names)),
                        (Row(CLS1, (cid, 0, ep | 1, 0, _ALWAYS_OK, 0, 0), ph_ep),
                         Row(CLS3, (cid, res | 1, 0, cond | 1, cost | 1, 0), ph3)),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x0FD2,
    archetype_member(LIGHTSWORN_TABLE, phantom=0x1E45),              # Lightsworn Sabre leaves the set (user)
    mill_two_ignition_and_end_phase(
        set_code=0x33, gain_key=0x216D, gain_kind=0x12,
        slots=(ov5_cave.CAVE_RAIDEN_ONFIELD, ov5_cave.CAVE_RAIDEN_EP, ov5_cave.CAVE_RAIDEN_COND,
               ov5_cave.CAVE_RAIDEN_COST, ov5_cave.CAVE_RAIDEN_RES),
        phantoms=(0x0ECB, 0x0EBC)),
    card_genre_word(1 << 35))

PROPS = card_props("LIGHT", "Warrior", level=4, atk=1700, defense=1000, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_raiden.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
