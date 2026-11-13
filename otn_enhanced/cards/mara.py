"""Mara of the Nordic Alfar (DARK / Spellcaster / Tuner / Level 2 / 1000 / 500) on Happy Lover 0x106C.

    "When using this card as Synchro Material, the other Synchro Materials must be 2 "Nordic" monsters in your
     hand."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, _IS_MONSTER, _in_ov5
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
import ndspy.rom


_SYN_STATE, _PICK_BASE, _PICK_LIST = 0x0229ABFC, 0x0229A9FC, 0x0229AA58


_PLAYER_BLOCK, _INSTANCES = 0x0229AC94, 0x0229C33C


_IS_NORDIC = 0x02023FC4


_SYN_REJECT = 0x02249B20


_HAND_IDX_OF, _ANIM_QUEUE, _SEND_HAND_TO_GY = 0x021A25A0, 0x021C3BC8, 0x021C6E74


_NORDIC_TBL, _NORDIC_N, _NORDIC_LIT, _NORDIC_COUNT_IMM = 0x0209CEF8, 0x12, 0x02023FC0, 0x02023FA8


@dataclass(frozen=True)
class synchro_material_with_hand_cards:
    """'When using this card as Synchro Material, the other Synchro Materials must be 2 "<archetype>" monsters in your
    hand.' The donor joins the NATIVE hand-material mode (Eccentric Boy / Parallel Gear), as the 3DS does. Pieces:
      G  gate 0x022494EC's dead literal @0x02249534 -> the donor: first pick == donor makes level_sum loop the HAND
         only and the validator take its hand branch.
      V  @0x02249BEE (hand branch 'exactly one pick so far'): Mara mode = count 1 or 2, the hand card is a <archetype>
         MONSTER, and not the hand card already picked (the native hand branch has no duplicate check).
      C  @0x02249714 (level_sum completion): Mara mode with count < 3 -> required = 3, so donor + 1 never closes.
      M  @0x02249B92 `bl is_monster` (validator field path): donor at count != 0 -> reject; the donor is only ever the
         FIRST material (user ruling 'Field only').
      S  @0x0226395C step 5's `step = 6` write: native step 5 sends ONLY the first pick still in hand (in-game test 1:
         the 2nd Nordic stayed); in this mode send picks 2.. here, the native loop sends pick 1.
    Plus the archetype SUBTYPE row {cid, subtype} in the ARM9 table 0x0209CEF8 (18 x {u16 cid, s16}, count-neutral over
    a phantom). All four hooks are BLs inside ov3 and every stub target is ARM9 or ov3 (ov3 pool)."""
    gate_stock: int           # the gate literal's stock value
    subtype: int              # 2 = Alfar
    subtype_phantom: int
    slots: tuple[int, int, int, int]       # (valid, count, first, send), ov3 pool

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import thumb_bl
        v_s, c_s, m_s, s_s = self.slots
        assert not any(_in_ov5(a) for a in self.slots)

        def pick_ref(a, i):
            a.ldr_const(0, _PICK_BASE).insn("LDR", "R0, [R0, #0x58]")
            if i:
                a.insn("ADD", f"R0, #0x{i:X}")
            return (a.insn("LSL", "R0, R0, #25").insn("LSR", "R0, R0, #24")
                     .ldr_const(1, _PICK_LIST).insn("LDRH", "R0, [R1, R0]"))

        def ref_cid(a, ref):
            return (a.insn("LSL", f"R0, {ref}, #3").ldr_const(1, _INSTANCES)
                     .insn("LDR", "R0, [R1, R0]").insn("LSL", "R0, R0, #18").insn("LSR", "R0, R0, #18"))

        def first_is_donor(a):
            pick_ref(a, 0)
            ref_cid(a, "R0")
            return a.ldr_const(1, cid).insn("CMP", "R0, R1")

        a = EffectBuilder()
        a.prologue(save=[R4, R6]).insn("LDR", "R4, [R7, #0x7C]")
        first_is_donor(a)
        (a.insn("BEQ", "mara")
          .insn("ADD", "R0, R4, #0x0")
          .insn("B", "out")
          .label("mara")
          .insn("SUB", "R0, R4, #0x1")
          .insn("CMP", "R0, #0x1")
          .insn("BHI", "no")
          .insn("LDR", "R3, [SP, #0xC]")
          .insn("LSL", "R0, R3, #2")
          .ldr_const(1, 0xB3C)
          .insn("MUL", "R1, R5")
          .ldr_const(2, _PLAYER_BLOCK + 0x124)
          .insn("ADD", "R1, R1, R2")
          .insn("LDR", "R0, [R1, R0]")
          .insn("LSL", "R1, R0, #17")
          .insn("LSR", "R1, R1, #31")
          .insn("LSL", "R0, R0, #1")
          .insn("LSR", "R0, R0, #24")
          .insn("LSL", "R0, R0, #1")
          .insn("ADD", "R6, R0, R1")
          .insn("CMP", "R4, #0x2")
          .insn("BNE", "fresh"))
        pick_ref(a, 1)
        (a.insn("CMP", "R0, R6")
          .insn("BEQ", "no")
          .label("fresh"))
        ref_cid(a, "R6")
        (a.insn("ADD", "R4, R0, #0x0")
          .bl(_IS_NORDIC)
          .insn("CMP", "R0, #0x0")
          .insn("BEQ", "no")
          .insn("ADD", "R0, R4, #0x0")
          .bl(_IS_MONSTER)
          .insn("CMP", "R0, #0x0")
          .insn("BEQ", "no")
          .insn("MOV", "R0, #0x1")
          .insn("B", "out")
          .label("no")
          .insn("MOV", "R0, #0x0")
          .label("out")
          .insn("POP", "{R4, R6}")
          .insn("POP", "{R3}")
          .insn("CMP", "R0, #0x1")
          .insn("BX", "R3"))
        vb = a.assemble(v_s)

        a = EffectBuilder()
        a.prologue()
        first_is_donor(a)
        (a.insn("LDR", "R1, [R6, #0x70]")
          .insn("LDR", "R0, [R6, #0x7C]")
          .insn("BNE", "done")
          .insn("CMP", "R0, #0x3")
          .insn("BCS", "done")
          .insn("MOV", "R1, #0x3")
          .label("done")
          .insn("POP", "{PC}"))
        cb = a.assemble(c_s)

        a = EffectBuilder()
        (a.ldr_const(1, cid)
          .insn("CMP", "R0, R1")
          .insn("BNE", "tail")
          .ldr_const(1, _SYN_STATE)
          .insn("LDR", "R1, [R1, #0x7C]")
          .insn("CMP", "R1, #0x0")
          .insn("BEQ", "tail")
          .ldr_const(1, _SYN_REJECT | 1)
          .insn("BX", "R1")
          .label("tail")
          .ldr_const(1, _IS_MONSTER | 1)
          .insn("BX", "R1"))
        mb = a.assemble(m_s)

        a = EffectBuilder()
        (a.prologue(save=[R4, R5, R6, R7])
          .insn("ADD", "R0, R1, #0x1")
          .insn("STRH", "R0, [R4, #0x24]")
          .insn("LDRH", "R6, [R4, #0x2]"))
        first_is_donor(a)
        (a.insn("BNE", "done")
          .insn("MOV", "R5, #0x2")
          .label("loop")
          .ldr_const(0, _SYN_STATE)
          .insn("LDR", "R0, [R0, #0x70]")
          .insn("CMP", "R5, R0")
          .insn("BGE", "done")
          .ldr_const(0, _PICK_BASE)
          .insn("LDR", "R0, [R0, #0x58]")
          .insn("ADD", "R0, R0, R5")
          .insn("LSL", "R0, R0, #25")
          .insn("LSR", "R0, R0, #24")
          .ldr_const(1, _PICK_LIST)
          .insn("LDRH", "R7, [R1, R0]")
          .insn("ADD", "R0, R6, #0x0")
          .insn("ADD", "R1, R7, #0x0")
          .bl(_HAND_IDX_OF)
          .insn("CMP", "R0, #0x0")
          .insn("BLT", "next")
          .insn("ADD", "R4, R0, #0x0")
          .insn("MOV", "R0, #0x4D")
          .insn("CMP", "R6, #0x0")
          .insn("BEQ", "anim")
          .insn("MOV", "R1, #0x2")
          .insn("LSL", "R1, R1, #14")
          .insn("ORR", "R0, R1")
          .label("anim")
          .insn("MOV", "R1, #0xB")
          .insn("ADD", "R2, R7, #0x0")
          .insn("MOV", "R3, #0x0")
          .bl(_ANIM_QUEUE)
          .insn("ADD", "R0, R6, #0x0")
          .insn("ADD", "R1, R4, #0x0")
          .bl(_SEND_HAND_TO_GY)
          .label("next")
          .insn("ADD", "R5, #0x1")
          .insn("B", "loop")
          .label("done")
          .insn("POP", "{R4, R5, R6, R7}")
          .insn("POP", "{R3}")
          .insn("BX", "R3"))
        sb = a.assemble(s_s)
        blobs = (vb, cb, mb, sb)
        for blob, addr in zip(blobs, self.slots):
            assert_thumb1_only(blob, addr)
        hooks = ((0x02249BEE, v_s, bytes.fromhex("f86f0128")), (0x02249714, c_s, bytes.fromhex("316ff06f")),
                 (0x02249B92, m_s, thumb_bl(0x02249B92, _IS_MONSTER)), (0x0226395C, s_s, bytes.fromhex("481ca084")))
        gate_lit = 0x02249534
        subtype = self.subtype

        def install(rom, view):
            assert view.u32(gate_lit) in (self.gate_stock, cid), "gate literal not stock"
            view.pack(gate_lit, "<I", cid)
            for site, addr, stock in hooks:
                cur = view.blob(site, 4)
                assert cur in (stock, thumb_bl(site, addr)), f"{site:#010x} = {cur.hex()} -- someone else hooked it"
                view.write(site, thumb_bl(site, addr))

        def post(out):
            from otn_enhanced.effects import common
            rom = ndspy.rom.NintendoDSRom.fromFile(out)
            a9 = common.view(rom)
            assert a9.u32(_NORDIC_LIT) == _NORDIC_TBL, "Nordic literal moved"
            assert a9.u16(_NORDIC_COUNT_IMM) == 0x2200 | _NORDIC_N, "Nordic count moved"
            recs = [tuple(a9.unpack(_NORDIC_TBL + 4 * i, "<Hh")) for i in range(_NORDIC_N)]
            if (cid, subtype) in recs:
                return
            assert [r[0] for r in recs].count(self.subtype_phantom) == 1, "Nordic phantom already spent"
            new = sorted([r for r in recs if r[0] != self.subtype_phantom] + [(cid, subtype)])
            with common.arm9_edit(rom) as w:
                for i, r in enumerate(new):
                    w.pack(_NORDIC_TBL + 4 * i, "<Hh", *r)
            rom.saveToFile(out)

        def check(c, rom, view):
            from otn_enhanced.effects import common
            a9 = common.view(rom)
            recs = [tuple(a9.unpack(_NORDIC_TBL + 4 * i, "<Hh")) for i in range(_NORDIC_N)]
            c.ok(recs.count((cid, subtype)) == 1 and self.subtype_phantom not in [r[0] for r in recs]
                 and all(recs[i][0] < recs[i + 1][0] for i in range(_NORDIC_N - 1)),
                 "Nordic subtype row present, phantom dropped, 18 sorted")
            c.eq(view.u32(gate_lit), cid, "gate literal = donor")
            for site, addr, _ in hooks:
                c.eq(view.blob(site, 4), thumb_bl(site, addr), f"{site:#010x} = BL {addr:#010x}")

        names = ("validator count/archetype hook", "completion count hook", "first-material hook", "hand-send hook")
        return Compiled(tuple(zip(self.slots, blobs, names)), installs=(install,), posts=(post,), checks=(check,))



SPEC = card(
    0x106C,
    synchro_material_with_hand_cards(
        gate_stock=0x0E66, subtype=2, subtype_phantom=0x24F0,
        slots=(cave3.CAVE3_MARA_VALID, cave3.CAVE3_MARA_COUNT, cave3.CAVE3_MARA_FIRST, cave3.CAVE3_MARA_SEND)))

PROPS = card_props("DARK", "Spellcaster", level=2, atk=1000, defense=500, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_mara.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
