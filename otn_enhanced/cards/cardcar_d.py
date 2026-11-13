"""Cardcar D (EARTH / Machine / Level 2 / 800 / 400) on Mushroom Man 0x0FAE.

    "Cannot be Special Summoned. During your Main Phase 1, if this card was Normal Summoned this turn: You can
     Tribute this card; draw 2 cards, then it becomes the End Phase. You cannot Special Summon during the turn
     you activate this effect."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import CANNOT_SS_TABLE, archetype_member, card, card_props, CLS3, Compiled, NATIVE_COND, NATIVE_TRIB, Row, _DUEL_STATE, _ZONE_WORD
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass


_QUEUE = 0x021C3BC8            # command-queue append (op, a1, a2, a3)


_TURN_FLAGS = 0x0229ADB4       # per-player turn flags; bit 18 = Special Summoned this turn


_POD_KEY = 0x2321              # Pot of Duality: the can-SS mega-gate's native "cannot SS this turn" key


@dataclass(frozen=True)
class main_phase_1_after_normal_summon:
    """'During your Main Phase 1, if this card was Normal Summoned this turn' + 'you cannot Special Summon during
    the turn you activate this effect' (backward half): phase [duel+0x48] == 2, turn player [duel+0x34] == side,
    turn-flags bit 18 (Special Summoned this turn) clear, zone word bit 16 set; then the generic offer gate.
    Skipped once the cost ran (desc cost_ran): the Tribute clears the zone bit before the post-cost re-check."""

    def lower_cond(self, b):
        b.prologue(save=[R4])
        b.insn("ADD", "R4, R0, #0x0")
        b.ctx_field("cost_ran", dest=R0, ctx=R4)
        b.if_ne(R0, 0, "chain")
        b.ldr_const(1, _DUEL_STATE)
        b.insn("LDR", "R0, [R1, #0x48]")
        b.insn("CMP", "R0, #0x2")
        b.insn("BNE", "fail")
        b.ctx_field("controller", dest=R2, ctx=R4)
        b.insn("LDR", "R0, [R1, #0x34]")
        b.insn("CMP", "R0, R2")
        b.insn("BNE", "fail")
        b.insn("MOV", "R0, #0x1")
        b.insn("AND", "R0, R2")
        b.ldr_const(1, 0xB3C)
        b.insn("MUL", "R0, R1")
        b.ldr_const(1, _TURN_FLAGS)
        b.insn("LDR", "R1, [R0, R1]")
        b.insn("LSR", "R1, R1, #0x12")
        b.insn("MOV", "R3, #0x1")
        b.insn("TST", "R1, R3")
        b.insn("BNE", "fail")
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
        b.label("chain")
        b.insn("ADD", "R0, R4, #0x0")
        b.bl(NATIVE_COND)
        b.insn("POP", "{R4, PC}")
        b.label("fail")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")


@dataclass(frozen=True)
class tribute_self_and_lock_special_summon:
    """'Tribute this card' + 'you cannot Special Summon during the turn you activate this effect' (forward half):
    the cost posts Pot of Duality's native lock node (side, 0x2321, 1) that the can-SS mega-gate denies on, then the
    native Tribute. Side effect: PoD's own once-per-turn latch is spent for that player (unobservable: the
    effect moves the turn to the End Phase)."""

    def lower_cost(self, b):
        b.prologue(save=[R4])
        b.insn("ADD", "R4, R0, #0x0")
        b.ctx_field("controller", dest=R0, ctx=R4)
        b.turnlog_post(R0, _POD_KEY, 1)
        b.insn("ADD", "R0, R4, #0x0")
        b.bl(NATIVE_TRIB)
        b.insn("POP", "{R4, PC}")


@dataclass(frozen=True)
class draw_then_end_phase:
    """'draw N cards, then it becomes the End Phase': DRAW(side, N), then Neko Mane King's End-Phase body without its
    [0x0229C294+0x78]&1 branch -- queue (0x1A|side<<15, 1, 5, 0) and (0xF|turn player<<15, 0, 0, 0)."""
    count: int

    def lower_resolver(self, b):
        b.prologue(save=[R4])
        b.ctx_field("controller", dest=R4)
        b.call("draw", R4, self.count)
        b.ldr_const(1, _DUEL_STATE)
        b.insn("LDR", "R0, [R1, #0x48]")
        b.insn("CMP", "R0, #0x5")
        b.insn("BEQ", "done")
        b.insn("MOV", "R0, #0x1A")
        b.insn("CMP", "R4, #0x0")
        b.insn("BEQ", "op1")
        b.ldr_const(0, 0x801A)
        b.label("op1")
        b.insn("MOV", "R1, #0x1")
        b.insn("MOV", "R2, #0x5")
        b.insn("MOV", "R3, #0x0")
        b.bl(_QUEUE)
        b.insn("MOV", "R0, #0xF")
        b.ldr_const(1, _DUEL_STATE)
        b.insn("LDR", "R1, [R1, #0x34]")
        b.insn("CMP", "R1, #0x0")
        b.insn("BEQ", "op2")
        b.ldr_const(0, 0x800F)
        b.label("op2")
        b.insn("MOV", "R1, #0x0")
        b.insn("MOV", "R2, #0x0")
        b.insn("MOV", "R3, #0x0")
        b.bl(_QUEUE)
        b.label("done")
        b.epilogue(ret=0)


@dataclass(frozen=True)
class ignition_with:
    """An ignition effect (one cls3 record over `phantom`) whose condition / cost / resolver are phrase verbs with
    lower_cond / lower_cost / lower_resolver. slots = (resolver, condition, cost); ov5 if >= OV5_NATIVE_END."""
    cid: int
    condition: object
    cost: object
    effect: object
    slots: tuple[int, int, int]
    phantom: int

    def compile(self, view, cid) -> Compiled:
        assert cid == self.cid
        res, cond, cost = self.slots
        blobs = []
        for addr, lower in ((res, self.effect.lower_resolver), (cond, self.condition.lower_cond),
                            (cost, self.cost.lower_cost)):
            b = EffectBuilder()
            lower(b)
            blob = b.assemble(addr)
            assert_thumb1_only(blob, addr)
            blobs.append(blob)
        stubs = tuple(zip(self.slots, blobs, ("resolver", "condition", "cost")))
        return Compiled(stubs, (Row(CLS3, (cid, res | 1, 0, cond | 1, cost | 1, 0), self.phantom),))



SPEC = card(
    0x0FAE,
    archetype_member(CANNOT_SS_TABLE, 0x193B),
    ignition_with(
        0x0FAE,
        condition=main_phase_1_after_normal_summon(),
        cost=tribute_self_and_lock_special_summon(),
        effect=draw_then_end_phase(2),
        slots=(ov5_cave.CAVE_CARDCAR_RES, ov5_cave.CAVE_CARDCAR_COND, ov5_cave.CAVE_CARDCAR_COST),
        phantom=0x0EC8))

PROPS = card_props("EARTH", "Machine", level=2, atk=800, defense=400)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_cardcar_d.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
