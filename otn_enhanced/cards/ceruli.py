"""Ceruli, Guru of Dark World on Kahkki 0x1B3E (DARK / Fiend / Level 1 / 100 / 300).

    If this card is discarded to the Graveyard by a card effect: Special Summon this card from the Graveyard to
    your opponent's side of the field in face-up Defense Position. When this card is Special Summoned by the
    effect of a "Dark World" card: Your opponent must discard 1 card.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS2, Compiled, Edit
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import ov3_bl_target as common_bl_target
from dataclasses import dataclass
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows


@dataclass(frozen=True)
class discarded_by_effect_special_summon_to_opponents_defense_then_opponent_discards:
    """'If this card is discarded to the GY by a card effect: Special Summon this card from the GY to your opponent's side
    of the field in face-up Defense Position. When this card is Special Summoned by the effect of a "Dark World" card: your
    opponent must discard 1 card.' The donor (a Dark World effect-discard cid, its trigger is the hardcoded arm) keeps its
    cls2 record, rewritten IN PLACE to the mandatory {resolver, 0, 0, 0, 0} shape; ONE ov5 resolver holds both clauses.
    Clause 1 is the native self-SS-from-GY tail with face-up/Defense, r0 = the OPPONENT's side (r0 places the card; bit 4 of
    the 5th arg only re-attributes it). Clause 2 is a follow-on in a LATER phase (the resolver returns 0x7F; the phase is
    tested == 0x7F with clause 1 the fall-through, so a wrong entry phase costs the ordering, never the summon): the post
    and return 0 is the native idiom, target = desc[+2] = the owner, skipped on an empty hand."""
    stub: int
    donor_stock: tuple      # the donor's stock cls2 slots (+04..+14), asserted
    sibling: int            # the cid sharing the donor's handlers; must keep its own record untouched
    sibling_stock: tuple    # its stock cls2 slots (+04..+14)
    shape_cid: int          # a native card whose record is the {resolver, 0, 0, 0, 0} shape being copied
    shape_stock: tuple
    dw_cids: tuple          # every cid that must still reach the Dark World discard arm
    reserve: int = 0xC0

    def compile(self, view, cid) -> Compiled:
        import struct as _st
        from otn_enhanced.cards import snoww as _snoww
        zone_of, locator, proper_ss = 0x021A220D, 0x021A25E9, 0x021A2619
        ss_precheck, ss_zonecheck, ss_commit = 0x021B9FC1, 0x021BA259, 0x0226925D
        effect_discard = 0x022598A1
        state_hand, state_stride, state_phase, followup = 0x0229ACA0, 0x0B3C, 0x0229AAFC, 0x7F
        dw_arm, dw_tbl, dw_count_imm = 0x021D185C, 0x0209CA06, 0x020238B8

        b = EffectBuilder()
        b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.ldr_const(4, state_phase)
        b.insn("LDR", "R4, [R4, #0x70]")
        b.insn("CMP", f"R4, #0x{followup:X}")
        b.insn("BEQ", "clause2")
        b.insn("LDRH", "R0, [R5, #0xC]")
        b.call_addr(zone_of, via=R4)
        b.insn("LSL", "R0, R0, #0x10")
        b.insn("LSR", "R0, R0, #0x18")
        b.insn("LDRB", "R1, [R5, #0x3]")
        b.insn("CMP", "R1, R0")
        b.insn("BNE", "fail")
        b.insn("LDRH", "R0, [R5, #0xC]")
        b.call_addr(locator, via=R4)
        b.insn("ADD", "R7, R0, #0x0")
        b.call_addr(proper_ss, R7, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "fail")
        b.insn("MOV", "R6, #0x1")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.insn("SUB", "R6, R6, R0")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.insn("LDRB", "R2, [R5, #0x3]")
        b.call_addr(ss_precheck, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "fail")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.insn("LDRH", "R2, [R5, #0xC]")
        b.insn("LDRB", "R3, [R5, #0x3]")
        b.call_addr(ss_zonecheck, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "fail")
        b.insn("LDRH", "R0, [R5, #0x0]")
        b.insn("LSL", "R0, R0, #0x10")
        b.insn("MOV", "R1, #0x10")
        b.insn("ORR", "R0, R1")
        b.insn("STR", "R0, [SP, #0x0]")
        b.call_addr(ss_commit, R6, R7, 1, 1, via=R4)
        b.insn("MOV", f"R0, #0x{followup:X}")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        b.label("clause2")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.ldr_const(2, state_hand)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "c2hc")
        b.ldr_const(3, state_stride)
        b.insn("ADD", "R2, R2, R3")
        b.label("c2hc")
        b.insn("LDR", "R2, [R2, #0x0]")
        b.insn("CMP", "R2, #0x0")
        b.insn("BEQ", "fail")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.call_addr(effect_discard, R0, 1, 0, 1, via=R4)
        b.label("fail")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        blob = b.assemble(self.stub, pad="nop")
        assert_thumb1_only(blob, self.stub)
        assert len(blob) <= self.reserve, f"resolver {len(blob)} B > {self.reserve:#x}"

        rec = [r for r in rows(view, CLS2) if r[0] == cid]
        assert len(rec) == 1, f"{cid:#06x} owns {len(rec)} cls2 records"
        native = rec[0][:2] + tuple(self.donor_stock)
        patched = (cid, rec[0][1], self.stub | 1, 0, 0, 0, 0)

        def dark_world(rom):
            import ndspy.code
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            main = next(x for x in mc.sections if x.ramAddress == rom.arm9RamAddress)
            imm = _st.unpack_from("<H", main.data, dw_count_imm - rom.arm9RamAddress)[0]
            assert (imm & 0xFF00) == 0x2200, f"Dark World count immediate is {imm:#06x}, not `movs r2,#N`: the set-code thunk moved"
            n = imm & 0xFF
            return list(_st.unpack_from(f"<{n}H", main.data, dw_tbl - rom.arm9RamAddress))

        def install(rom, view):
            lst = dark_world(rom)
            assert cid in lst and lst == sorted(lst) and len(set(lst)) == len(lst), \
                f"the donor {cid:#06x} is not in the sorted Dark World set-code table: {[hex(x) for x in lst]}"
            sib = [r for r in rows(view, CLS2) if r[0] == self.sibling]
            assert len(sib) == 1 and tuple(sib[0][2:]) == tuple(self.sibling_stock)
            shape = [r for r in rows(view, CLS2) if r[0] == self.shape_cid]
            assert len(shape) == 1 and tuple(shape[0][2:]) == tuple(self.shape_stock), "the mandatory-shape record moved"
            assert view.u16(dw_arm) == 0x980D, "the Dark World effect-discard arm moved"
            for k in self.dw_cids:
                leaf = _snoww._switch_leaf(bytes(view.buf), k)
                assert leaf == dw_arm, f"{k:#06x} does not reach the discard arm in the base ROM (leaf {leaf:#010x})"
            for addr, want, what in ((0x0226927C, 0x2010, "0x0226925C `movs r0,#0x10` (bit-4 test)"),
                                     (0x0226928A, 0x4068, "0x0226925C `eors r0,r5`"),
                                     (0x0226928C, 0x8020, "0x0226925C `strh r0,[r4]`"),
                                     (0x021BA44A, 0xF7FF, "0x021BA440's BL to 0x021B9FC0"),
                                     (0x021D3190, 0x70A0, "0x021D3168 `strb r0,[r4,#2]` (desc[+2] = owner)"),
                                     (0x022598A0, 0xB538, "0x022598A0 prologue (effect-discard post)"),
                                     (0x022598A2, 0x1C0D, "0x022598A0 `adds r5,r1,#0`"),
                                     (0x0222EB2E, 0x78A0, "native discard caller `ldrb r0,[r4,#2]`"),
                                     (0x0222EB34, 0x1A08, "native discard caller `subs r0,r1,r0`"),
                                     (0x0222EB3C, 0x2001, "native post-and-return-0 `movs r0,#1`")):
                assert view.u16(addr) == want, f"{what} drifted at {addr:#010x}: {view.u16(addr):#06x} != {want:#06x}"
            assert common_bl_target(view.buf, 0x0222EB38) == effect_discard & ~1, "0x0222EB38 no longer calls the effect-discard post"

        def check(c, rom, view):
            lst = dark_world(rom)
            c.ok(cid in lst and lst == sorted(lst), "the donor is still in the sorted ARM9 Dark World set-code table")
            sib = [r for r in rows(view, CLS2) if r[0] == self.sibling]
            c.eq([tuple(r[2:]) for r in sib], [tuple(self.sibling_stock)], f"{self.sibling:#06x} keeps its own stock cls2 record")
            for k in self.dw_cids:
                c.eq(_snoww._switch_leaf(bytes(view.buf), k), dw_arm, f"{k:#06x} still reaches the Dark World discard arm")
            c.ok(self.stub + self.reserve <= ov5_cave.CAVE_FREE, "the slot ends before CAVE_FREE")

        return Compiled(((self.stub, blob, "resolver (both clauses)"),), edits=(Edit(CLS2, cid, native, patched),),
                        installs=(install,), checks=(check,))



DONOR_CID = 0x1B3E          # Kahkki
GREN_CID = 0x1B3F           # shares Kahkki's handlers, owns its own record
KAHKKI_STOCK = (0x02204899, 0x021D8CE5, 0x0224A115, 0x00000000, 0x02234DA5)
DW_ARM_CIDS = (0x1965, 0x1966, 0x1968, 0x1969, 0x1B3E, 0x1B3F)

SPEC = card(
    DONOR_CID,
    discarded_by_effect_special_summon_to_opponents_defense_then_opponent_discards(
        stub=ov5_cave.CAVE_CERULI_RES, donor_stock=KAHKKI_STOCK, sibling=GREN_CID,
        sibling_stock=(0x02204899, 0x021DB3BD, 0x0224A115, 0x00000000, 0x02234DA5),
        shape_cid=0x1965, shape_stock=(0x0220731D, 0, 0, 0, 0), dw_cids=DW_ARM_CIDS))

PROPS = card_props("DARK", "Fiend", level=1, atk=100, defense=300)

# Names author_facts.py proof strings read off this module.
RES_STUB, RES_RESERVE = ov5_cave.CAVE_CERULI_RES, 0xC0
EFFECT_DISCARD, SS_COMMIT, SS_ZONECHECK = 0x022598A1, 0x0226925D, 0x021BA259
STATE_A_HAND, STATE_A_STRIDE, STATE_PHASE, PHASE_FOLLOWUP = 0x0229ACA0, 0x0B3C, 0x0229AAFC, 0x7F


def res_stub(base: int = None) -> bytes:
    from otn_enhanced.effects.common import Ov
    from otn_enhanced.rom.overlay_io import load_overlay3
    _, ovb = load_overlay3(dsl.SRC)
    return SPEC.compile(Ov(bytearray(ovb))).stubs[0][1]


main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_ceruli.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
