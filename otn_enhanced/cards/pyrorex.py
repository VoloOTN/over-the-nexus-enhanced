"""Pyrorex the Elemental Lord (FIRE / Dinosaur / Level 8 / 2800 / 2200) on Harpie Girl 0x181F.

    "Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 FIRE monsters
     in your GY. When this card is Special Summoned: You can target 1 monster your opponent controls; destroy it,
     and if you do, both players take damage equal to half the original ATK of the destroyed monster. You can only
     use this effect of "Pyrorex the Elemental Lord" once per turn. If this face-up card leaves the field, skip the
     Battle Phase of your next turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import ELEMENTAL_LORD_CIDS, NOMI_CLASS_2_TABLE, archetype_member, card, card_props, hand_special_summon_by_gy_attribute, leave_field_skip_next_battle_phase, CLS1, Compiled, LIST_NS_OR_SS, Row, _DESTROYED, _HOPT_KIND, _PHASE_STATE, _PLAYER_BASE, _hopt_you_can_stub, _timing_arms_check, _timing_arms_install
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
import ndspy.rom


@dataclass(frozen=True)
class destroy_opponent_monster_burn_half_atk_once_per_turn:
    """'When this card is Special Summoned: You can target 1 monster your opponent controls; destroy it, and if you do,
    both players take damage equal to half the original ATK of the destroyed monster. Once per turn.'
    N-or-SS list + cls1 {RES, +08 0x021D882D (mask 0x1412 = opponent's monster), +0C COND, +10 'You can' SLOT4, +14
    BOARD target step 0x02234DA5}. +0C returns 1 -> the engine runs the +08 target sweep, so no target = no offer. The
    BOARD step (counts via the record's +08), NOT 0x02235605 (counts via a criteria row, which this cid lacks: Yes/No
    shown, no picker, nothing destroyed). RES = native 0x02210311's destroy-then protocol (its cid switch defaults to
    1000 / no damage): 0x80 target 0x022349B0, revalidate 0x0224A924, amount = ORIGINAL ATK/2 read BEFORE the destroy,
    push 0x021D28A4, destroy 0x02204674 -> 0x7F; 0x7F: [0x0229C314+0x14] != 0 ('if you do') -> damage to both, pop."""
    filter: int
    target_step: int
    slots: tuple[int, int, int]      # (res, cond, slot4), ov5
    phantoms: tuple[int, int]        # (N-or-SS list, cls1)

    def compile(self, view, cid) -> Compiled:
        res, cond, slot4 = self.slots
        ph_list, ph1 = self.phantoms
        b = EffectBuilder()
        b.insn("PUSH", "{R1, R2, R3, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.ldr_const(7, _PHASE_STATE)
        b.insn("LDR", "R1, [R7, #0x70]")
        b.insn("CMP", "R1, #0x7F")
        b.insn("BEQ", "ph7f")
        b.insn("CMP", "R1, #0x80")
        b.insn("BNE", "stop")
        b.insn("MOV", "R1, #0x0")
        b.insn("STR", "R1, [SP, #0x0]")
        b.insn("ADD", "R2, SP, #0x4")
        b.call_addr(0x022349B1, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "stop")
        b.insn("LDR", "R1, [SP, #0x4]")
        b.insn("LSL", "R0, R1, #0x18")
        b.insn("LSR", "R4, R0, #0x18")
        b.insn("LSL", "R0, R1, #0x10")
        b.insn("LSR", "R6, R0, #0x18")
        b.call_addr(0x0224A925, R5, R4, R6, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "stop")
        b.insn("LSL", "R0, R6, #0x4")
        b.insn("LSL", "R1, R6, #0x2")
        b.insn("ADD", "R0, R0, R1")
        b.insn("MOV", "R1, #0x1")
        b.insn("AND", "R1, R4")
        b.insn("BEQ", "side0")
        b.ldr_const(1, 0xB3C)
        b.insn("ADD", "R0, R0, R1")
        b.label("side0")
        b.ldr_const(1, _PLAYER_BASE)
        b.insn("ADD", "R0, R0, R1")
        b.insn("LDR", "R0, [R0, #0x34]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.call_addr(0x0202AC09, via=R3)
        b.insn("LSR", "R2, R0, #0x1")
        b.ldr_const(0, 0xffff)
        b.insn("CMP", "R2, R0")
        b.insn("BLE", "clamped")
        b.insn("ADD", "R2, R0, #0x0")
        b.label("clamped")
        b.insn("STR", "R2, [R7, #0x74]")
        b.insn("STR", "R4, [R7, #0x78]")
        b.call_addr(0x021D28A5, via=R3)
        b.call_addr(0x02204675, R5, via=R3)
        b.insn("MOV", "R0, #0x7F")
        b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
        b.label("ph7f")
        b.ldr_const(0, _DESTROYED)
        b.insn("LDR", "R0, [R0, #0x14]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "popd")
        b.insn("LDR", "R2, [R7, #0x74]")
        b.insn("CMP", "R2, #0x0")
        b.insn("BEQ", "popd")
        b.insn("LDRB", "R1, [R5, #0x2]")
        b.insn("MOV", "R0, #0x1")
        b.insn("SUB", "R1, R0, R1")
        b.call_addr(0x021CFBC9, R5, via=R3)
        b.insn("LDRB", "R1, [R5, #0x2]")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("LDR", "R2, [R7, #0x74]")
        b.call_addr(0x021CFBC9, via=R3)
        b.label("popd")
        b.call_addr(0x021D2965, via=R3)
        b.label("stop")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
        rb = b.assemble(res, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("LDRB", "R0, [R0, #0x2]")
        b.turnlog_query(R0, cid, _HOPT_KIND, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "used")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, PC}")
        b.label("used")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        cb = b.assemble(cond, pad="nop")
        sb = _hopt_you_can_stub(slot4, cid)
        for blob, addr in ((rb, res), (cb, cond)):
            assert_thumb1_only(blob, addr)
        return Compiled(((res, rb, "+04 resolver"), (cond, cb, "+0C cond"), (slot4, sb, "+10 slot4")),
                        (Row(LIST_NS_OR_SS, (cid,), ph_list),
                         Row(CLS1, (cid, 0, res | 1, self.filter, cond | 1, slot4 | 1, self.target_step), ph1)),
                        installs=(_timing_arms_install,), checks=(_timing_arms_check,))


@dataclass(frozen=True)
class replaced_by_filler_in_set_code:
    """The donor leaves an archetype's set-code list IN PLACE for a non-card filler cid (no card_prop, keeps the list
    sorted, count + thunk stock): e.g. Pyrorex stops being a "Harpie". `ptr_table` is the set-code pointer table, whose
    entry [index] must still be `thunk`."""
    ptr_table: int
    index: int
    thunk: int
    base: int
    stock: tuple
    filler: int

    def compile(self, view, cid) -> Compiled:
        new = tuple(self.filler if c == cid else c for c in self.stock)
        assert cid in self.stock and self.filler not in self.stock

        def post(out):
            from otn_enhanced.effects import common
            rom = ndspy.rom.NintendoDSRom.fromFile(out)
            a9 = common.view(rom)
            assert a9.u32(self.ptr_table + self.index * 4) == self.thunk, "set-code thunk moved"
            cur = a9.unpack(self.base, f"<{len(self.stock)}H")
            if cur != new:
                assert cur == self.stock, f"set-code list is not stock: {[hex(c) for c in cur]}"
                with common.arm9_edit(rom) as w:
                    w.pack(self.base, f"<{len(new)}H", *new)
                rom.saveToFile(out)

        def check(c, rom, view):
            from otn_enhanced.effects import common
            c.eq(tuple(common.view(rom).unpack(self.base, f"<{len(new)}H")), new,
                 f"set-code list: {cid:#06x} replaced by filler {self.filler:#06x}, sorted")

        return Compiled(posts=(post,), checks=(check,))



SPEC = card(
    0x181F,
    archetype_member(NOMI_CLASS_2_TABLE, 0x176C),
    replaced_by_filler_in_set_code(
        ptr_table=0x0209D0D8, index=0x14, thunk=0x02023905, base=0x0209C8C4,       # Harpie
        stock=(0x0DCA, 0x0FE4, 0x0FE5, 0x1128, 0x1246, 0x1477, 0x181F,
               0x182A, 0x182B, 0x182C, 0x183F, 0x1A1E, 0x1BC7),
        filler=0x181E),
    hand_special_summon_by_gy_attribute(attribute=4, count=5, slot=ov5_cave.CAVE_PX_SSCOND),
    destroy_opponent_monster_burn_half_atk_once_per_turn(
        filter=0x021D882D, target_step=0x02234DA5,
        slots=(ov5_cave.CAVE_PX_RES, ov5_cave.CAVE_PX_COND, ov5_cave.CAVE_PX_SLOT4),
        phantoms=(0x164A, 0x17E0)),
    leave_field_skip_next_battle_phase(ELEMENTAL_LORD_CIDS))

PROPS = card_props("FIRE", "Dinosaur", level=8, atk=2800, defense=2200)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_pyrorex.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
