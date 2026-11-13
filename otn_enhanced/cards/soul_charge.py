"""Soul Charge (Normal Spell) on donor Breath of Light 0x123D.

    "Target any number of monsters in your GY; Special Summon them, and if you do, you lose 1000 LP
     for each monster Special Summoned by this effect. You cannot conduct your Battle Phase the turn
     you activate this card. You can only activate 1 "Soul Charge" per turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import once_per_turn, CLS0, CRITERIA, Compiled, Edit, Row, _DUEL_STATE, _PHASE_STATE
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass


_SPELL_COND = 0x021F03B4       # native: can SS && >= 1 criteria candidate


_ONCE_CHECK = 0x021F6DD8       # (desc) -> 0 iff this cid's turn node exists


_COPY_EXEMPT = 0x021D2B88      # (desc) -> nonzero: natives skip the lock / 1-turn logic


_TURN_NODE = 0x021D2584        # (side, cid, 1, ref) -> post a turn node


_BP_LOCK_CID = 0x0EBD          # checked by the Battle Phase gate 0x0224CD84


_GY_RESOLVER = 0x0221B4E0      # native GY multi-summon resolver


_PICK = 0x02234964             # (desc, i) -> pick i's packed ref


_ON_FIELD = 0x021A241C         # (ref) -> side|slot<<8, or -1 when not on the field


_LP_PAY = 0x021CF924           # (side, amount)


_MULTI_PROLOGUE = (0xB5F8, 0x1C05, 0x9100)   # 0x02235700: push {r3-r7,lr}; adds r5,r0,#0; str r1,[sp]


_MULTI_TAIL = 0x02235912       # needs r4 count code, r5 desc, r6 prompt, [sp] = r1


_ANY_NUMBER, _GY_SUMMON_PROMPT = 0x47, 0x11D    # Barcha's "any number" count code (0x29 capped at 3)


CRIT_SELECT_FROM_GY_SUMMON = 0x0223C9D1         # Premature Burial / Call of the Haunted row


CRIT_ANY_MONSTER_IN_GY = 0x00010002


@dataclass(frozen=True)
class main_phase_1_only:
    """'Activate only during your Main Phase 1' -- skipped on the desc[+7] mid-activation re-check."""

    def lower_cond(self, b):
        b.ldr_const(1, _DUEL_STATE)
        b.insn("LDR", "R0, [R1, #0x48]")
        b.insn("CMP", "R0, #0x2")
        b.insn("BNE", "no")


@dataclass(frozen=True)
class no_battle_phase:
    """'You cannot conduct your Battle Phase the turn you activate this card' -- a turn node on 0x0EBD
    posted in the cost, which the Battle Phase gate 0x0224CD84 checks."""

    def lower_cost(self, b):
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.ldr_const(1, _BP_LOCK_CID)
        b.insn("MOV", "R2, #0x1")
        b.insn("LDRH", "R3, [R4, #0xC]")
        b.bl(_TURN_NODE)


def _once_cond(b):
    b.insn("ADD", "R0, R4, #0x0")
    b.bl(_ONCE_CHECK)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "no")


def _once_cost(b):
    b.insn("LDRB", "R0, [R4, #0x2]")
    b.insn("LDRH", "R1, [R4, #0x0]")
    b.insn("MOV", "R2, #0x1")
    b.insn("MOV", "R3, #0x0")
    b.bl(_TURN_NODE)


@dataclass(frozen=True)
class special_summon_from_gy:
    """'Target any number of monsters in your GY; Special Summon them' -- the native GY multi-summon
    resolver plus a multi-select template with the count fixed at 'any number'."""
    any_number: bool = True


@dataclass(frozen=True)
class lose_lp_each:
    """'you lose N LP for each monster Special Summoned by this effect' -- in the final resolver phase
    (0x78) pay N x (picks now on the field); a pick still in the GY was not summoned, not charged."""
    amount: int

    def lower_resolver(self, b):
        b.ldr_const(0, _PHASE_STATE)
        b.insn("LDR", "R0, [R0, #0x70]")
        b.insn("CMP", "R0, #0x78")
        b.insn("BNE", "native")
        b.insn("MOV", "R5, #0x0")
        b.insn("MOV", "R6, #0x0")
        b.ldr_const(7, self.amount)
        b.label("loop")
        b.insn("LDRH", "R0, [R4, #0x12]")
        b.insn("CMP", "R5, R0")
        b.insn("BGE", "pay")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("ADD", "R1, R5, #0x0")
        b.bl(_PICK)
        b.bl(_ON_FIELD)
        b.insn("CMP", "R0, #0x0")
        b.insn("BLT", "next")
        b.insn("ADD", "R6, R6, R7")
        b.label("next")
        b.insn("ADD", "R5, #0x1")
        b.insn("B", "loop")
        b.label("pay")
        b.insn("ADD", "R1, R6, #0x0")
        b.insn("LDRB", "R2, [R4, #0x2]")
        b.insn("LDRB", "R0, [R4, #0x6]")
        b.insn("EOR", "R0, R2")             # side = desc[+2] ^ desc[+6], as the cost path does
        b.bl(_LP_PAY)


@dataclass(frozen=True)
class gy_summon_spell:
    """cls0 record of the donor Spell rewritten in place (+04 resolver, +08 0, +0C cond, +10 cost,
    +14 select) plus a criteria row cloned from Premature Burial; `phantom` is the criteria cid dropped."""
    cid: int
    native: tuple                    # the donor's stock cls0 record, asserted at build
    gates: tuple                     # condition/cost phrases: main_phase_1_only, once_per_turn, no_battle_phase
    effect: tuple                    # (special_summon_from_gy, lose_lp_each)
    slots: tuple[int, int, int, int]  # resolver, condition, cost, select (ov5 cave)
    phantom: int

    def compile(self, view=None) -> Compiled:
        res, cond, cost, sel = self.slots
        summon, lose = self.effect
        assert isinstance(summon, special_summon_from_gy) and summon.any_number
        blobs = (_spell_resolver(lose, res), _spell_condition(self.gates, cond),
                 _spell_cost(self.gates, cost), _spell_select(sel))
        for blob, addr in zip(blobs, self.slots):
            assert_thumb1_only(blob, addr)
        stubs = tuple(zip(self.slots, blobs, ("resolver", "condition", "cost", "select")))
        patched = (self.cid, res | 1, 0, cond | 1, cost | 1, sel | 1)
        return Compiled(stubs,
                        (Row(CRITERIA, (self.cid, 0xFFFF, CRIT_SELECT_FROM_GY_SUMMON,
                                        CRIT_ANY_MONSTER_IN_GY), self.phantom),),
                        (Edit(CLS0, self.cid, self.native, patched),))


def _spell_resolver(lose: lose_lp_each, addr: int) -> bytes:
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    lose.lower_resolver(b)
    b.label("native")
    b.insn("ADD", "R0, R4, #0x0")
    b.bl(_GY_RESOLVER)
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return b.assemble(addr)


def _spell_condition(gates: tuple, addr: int) -> bytes:
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.insn("LDRB", "R0, [R4, #0x7]")        # desc[+7]: the cost already ran, skip the gates
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "native")
    for g in gates:
        if isinstance(g, main_phase_1_only):
            g.lower_cond(b)
        elif isinstance(g, once_per_turn):
            _once_cond(b)
    b.label("native")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("ADD", "R1, R5, #0x0")
    b.bl(_SPELL_COND)
    b.insn("POP", "{R4, R5, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, PC}")
    return b.assemble(addr)


def _spell_cost(gates: tuple, addr: int) -> bytes:
    b = EffectBuilder()
    b.insn("PUSH", "{R4, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.bl(_COPY_EXEMPT)
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "done")
    for g in gates:
        if isinstance(g, once_per_turn):
            _once_cost(b)
        elif isinstance(g, no_battle_phase):
            g.lower_cost(b)
    b.label("done")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, PC}")
    return b.assemble(addr)


def _spell_select(addr: int) -> bytes:
    """0x02235700 with its per-cid switch replaced by fixed (r4, r6)."""
    b = EffectBuilder()
    for hw in _MULTI_PROLOGUE:
        b.raw(hw)
    b.insn("MOV", f"R4, #0x{_ANY_NUMBER:X}")
    b.insn("MOV", f"R6, #0x{_GY_SUMMON_PROMPT >> 1:X}")
    b.insn("LSL", "R6, R6, #1")
    b.insn("ADD", f"R6, #0x{_GY_SUMMON_PROMPT & 1:X}")
    b.bl(_MULTI_TAIL)                       # LR already pushed: a plain jump; the tail pops pc
    return b.assemble(addr)



SPEC = gy_summon_spell(
    0x123D,
    native=(0x123D, 0x022048FD, 0x021D8DB9, 0, 0, 0),
    gates=(main_phase_1_only(), once_per_turn(), no_battle_phase()),
    effect=(special_summon_from_gy(), lose_lp_each(1000)),
    slots=(ov5_cave.CAVE_SC_RES, ov5_cave.CAVE_SC_COND, ov5_cave.CAVE_SC_COST, ov5_cave.CAVE_SC_SELECT),
    phantom=0x12D6)

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_soul_charge.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
