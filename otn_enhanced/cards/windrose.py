"""Windrose the Elemental Lord (WIND / Winged Beast / Level 8 / 2800 / 2200) on Soitsu 0x190B.

    "Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 WIND monsters
     in your GY. If this card is Special Summoned: Destroy all Spells and Traps your opponent controls. You can only
     use this effect of "Windrose the Elemental Lord" once per turn. If this face-up card leaves the field, skip the
     Battle Phase of your next turn."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import ELEMENTAL_LORD_CIDS, archetype_member, card, card_props, hand_special_summon_by_gy_attribute, leave_field_skip_next_battle_phase, CLS1, Compiled, Row, SetCodeTable, _HOPT_KIND
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave


NOMI_CLASS_4_TABLE = SetCodeTable("nomi class 4", 0x0209BC14, 0x1D, (0x02023224,), (0x02023206,))


_CLASSIFY = 0x020231C9


@dataclass(frozen=True)
class cpu_planner_reads_class_2:
    """Every rules caller of 0x020231C8 treats summon-restriction classes 2 and 4 alike (0x020233F4); only the CPU
    hand-SS planner (ov5 0x02368B40) skips class 4, so its `bl 0x020231C8` at `site` is re-pointed at an ov5 stub that
    reports the native class but 2 for the donor."""
    site: int
    native: bytes
    slot: int            # ov5

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.summon_trigger_hook import _bl
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(_CLASSIFY, via=R1)
        b.ldr_const(1, cid)
        b.insn("CMP", "R4, R1")
        b.insn("BNE", "out")
        b.insn("MOV", "R0, #0x2")
        b.label("out")
        b.insn("POP", "{R4, PC}")
        blob = b.assemble(self.slot, pad="nop")
        assert_thumb1_only(blob, self.slot)
        want = _bl(self.site, self.slot)

        def install(rom, view):
            ov5 = ov5_cave._load_ov5_decompressed(rom)
            data = bytearray(ov5.data)
            o = self.site - ov5_cave.OV5_RAM_BASE
            if bytes(data[o:o + 4]) == want:
                return
            assert bytes(data[o:o + 4]) == self.native, f"ov5 {self.site:#x} is {bytes(data[o:o + 4]).hex()} -- not native"
            data[o:o + 4] = want
            ov5_cave._save_ov5(rom, ov5, bytes(data))

        def check(c, rom, view):
            o5 = ov5_cave._load_ov5_decompressed(rom).data
            o = self.site - ov5_cave.OV5_RAM_BASE
            c.ok(bytes(o5[o:o + 4]) in {_bl(self.site, f) for f in ov5_cave.dc_ahead_of(self.slot)}, f"CPU planner {self.site:#x} -> {self.slot:#x} (or a later owner's front ahead of it)")

        return Compiled(((self.slot, blob, "CPU class view"),), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class destroy_all_opponent_spells_traps_once_per_turn:
    """'If this card is Special Summoned: Destroy all Spells and Traps your opponent controls. Once per turn.' (no
    opponent S/T still activates and spends the HOPT, as the 3DS +0C). cls1 {RES, +08 Harpie's Feather Duster filter,
    +0C COND, 0, 0} over a phantom = Moisture Creature's native shape: RES posts the turn log then runs HFD's resolver
    0x022048FD on the same desc (it builds its destroy mask from the TRIGGERING record's +08); +0C returns 2 (activatable,
    skip the +08 sweep) unless the turn log says used. The N-or-SS list is FULL, so the trigger rides the SHARED
    c79_trigger_hook module (installed here idempotently)."""
    resolver: int
    filter: int
    slots: tuple[int, int]         # (res, cond), ov5
    phantom: int                   # cls1 cid dropped

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import c79_trigger_hook
        res, cond = self.slots
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_post(R0, cid, _HOPT_KIND, via=R5)
        b.call_addr(self.resolver, R4, via=R5)
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        rb = b.assemble(res, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("LDRB", "R0, [R0, #0x2]")
        b.turnlog_query(R0, cid, _HOPT_KIND, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "used")
        b.insn("MOV", "R0, #0x2")
        b.insn("POP", "{R4, PC}")
        b.label("used")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        cb = b.assemble(cond, pad="nop")
        for blob, addr in ((rb, res), (cb, cond)):
            assert_thumb1_only(blob, addr)

        def install(rom, view):
            c79_trigger_hook.install(rom)
            c79_trigger_hook.apply(view.buf)

        def check(c, rom, view):
            c79_trigger_hook.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)

        return Compiled(((res, rb, "+04 resolver"), (cond, cb, "+0C cond")),
                        (Row(CLS1, (cid, 0, res | 1, self.filter, cond | 1, 0, 0), self.phantom),),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class closes_union_lock_for_retired_cid:
    """A union monster's lock names the donor's retired cid (here Doitsu 0x1917 names Soitsu 0x190B at 0x021D811A);
    its `beq accept` is nopped so it can no longer equip to the donor (the old card no longer exists). User decision."""
    site: int
    native: bytes

    def compile(self, view, cid) -> Compiled:
        nop = bytes.fromhex("c046")

        def install(rom, view):
            cur = view.blob(self.site, 2)
            if cur != nop:
                assert cur == self.native, f"union lock @{self.site:#x} is {cur.hex()}, not stock"
                view.write(self.site, nop)

        def check(c, rom, view):
            c.eq(view.blob(self.site, 2), nop, f"union lock beq @{self.site:#x} nopped")

        return Compiled(installs=(install,), checks=(check,))



SPEC = card(
    0x190B,
    archetype_member(NOMI_CLASS_4_TABLE, 0x19A8),
    cpu_planner_reads_class_2(site=0x0236A1BA, native=bytes.fromhex("b9f405f8"), slot=ov5_cave.CAVE_WR_AICLASS),
    hand_special_summon_by_gy_attribute(attribute=6, count=5, slot=ov5_cave.CAVE_WR_SSCOND),
    destroy_all_opponent_spells_traps_once_per_turn(
        resolver=0x022048FD, filter=0x021DA081,
        slots=(ov5_cave.CAVE_WR_RES, ov5_cave.CAVE_WR_COND), phantom=0x18E5),
    leave_field_skip_next_battle_phase(ELEMENTAL_LORD_CIDS),
    closes_union_lock_for_retired_cid(site=0x021D811E, native=bytes.fromhex("25d0")))

PROPS = card_props("WIND", "Winged Beast", level=8, atk=2800, defense=2200)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_windrose.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
