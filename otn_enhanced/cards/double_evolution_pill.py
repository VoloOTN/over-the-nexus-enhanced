"""Double Evolution Pill on Share the Pain 0x1319 (Normal Spell, keep-cid).

    Banish 1 Dinosaur monster and 1 non-Dinosaur monster from your hand and/or GY; Special Summon 1 Level 7 or higher
    Dinosaur monster from your hand or Deck, ignoring its Summoning conditions. You can only activate 1 "Double
    Evolution Pill" per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, CLS0, CRITERIA, Compiled, Edit, NATIVE_COND, Row
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass


@dataclass(frozen=True)
class banish_dinosaur_and_non_dinosaur_summon_high_level_dinosaur:
    """'Banish 1 Dinosaur monster and 1 non-Dinosaur monster from your hand and/or GY; Special Summon 1 Level N or higher
    Dinosaur monster from your hand or Deck, ignoring its Summoning conditions. You can only activate 1 per turn.'
      cls0 {resolver 0x02206F41 (Emergency Teleport's hand-or-Deck SS), 0, COND, COST, 0} rewritten IN PLACE.
      ONE criteria row {cid, 0xFFFF, HAND, word} over a phantom: the shared criteria_row_hook has no branch range left
      for another arm, so HAND switches mode itself. COST MODE ([0x0229AAFC+0x7C] != 0 and the acting descriptor
      [0x0229A9FC+0x50] is ours and desc[+0x12] < 2): HAND + GY builders, flags 0x10000 (banish), filter by desc[+0x12]
      (0 Dinosaur, 1 non-Dinosaur monster). TARGET MODE: Emergency Teleport's row verbatim (HAND flags 2, DECK flags
      0xA) plus a SECOND Deck pass (type 2, no summonability gate) keeping only restricted-class cids, so 'ignoring its
      Summoning conditions' holds for a nomi Dinosaur (Ultimate Conductor Tyranno) the type-0xA pass drops.
      COND = once per turn + a direct hand/GY scan (Dinosaur AND non-Dinosaur) + native 0x021F0419; COST = Dark Simorgh's
      two-pick protocol over [0x0229AAFC+0x7C] phases, mixed hand/GY banish commit, then the 1/turn node."""
    native: tuple            # the donor's stock cls0 record, asserted
    resolver: int
    word: int                # criteria word: Dinosaur, Level >= N, monster
    cond: int
    cost: int
    hand: int
    filt: int                # Dinosaur filter; the non-Dinosaur filter sits at +0x30
    nomi: int
    phantom: int

    def compile(self, view, cid) -> Compiled:
        RACE_GETTER, DINO, SPELL = 0x0202ABB9, 9, 23
        HAND_BUILDER, GY_BUILDER, DECK_BUILDER = 0x0223C16D, 0x0223C4E9, 0x0223BC3D
        BANISH_FLAGS, CLASSIFIER = 0x10000, 0x020231C9
        PLAYER, STRIDE, HAND_OFF, HAND_COUNT, GY_OFF, GY_COUNT = 0x0229AC94, 0xB3C, 0x124, 0x0C, 0x55C, 0x14
        NATIVE_COND, ONCE_CHECK, COPY_EXEMPT, SHORT = 0x021F0419, 0x021F6DD9, 0x021D2B89, 0x021D2BC9
        ACTING, STATE, MESSAGE, PROMPT, PICKER, READBACK = 0x0229A9FC, 0x0229AAFC, 0x0219A819, 0x56, 0x0219C431, 0x0219C511
        CPUSH, CPOP, HINDEX, HBANISH, R2W, GBANISH = 0x021D28A5, 0x021D2965, 0x021A25A1, 0x021C6E99, 0x021A25E9, 0x021C7105
        filt_non = self.filt + 0x30

        def flt(base, dino):
            b = EffectBuilder()
            b.insn("PUSH", "{R3, LR}")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call_addr(RACE_GETTER, via=R3)
            if dino:
                b.insn("CMP", f"R0, #{DINO}")
                b.insn("BNE", "no")
            else:
                b.insn("CMP", f"R0, #{DINO}")
                b.insn("BEQ", "no")
                b.insn("CMP", f"R0, #{SPELL}")
                b.insn("BGE", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R3, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R3, PC}")
            return b.assemble(base, pad="nop")

        d, n = flt(self.filt, True), flt(filt_non, False)
        assert len(d) <= 0x30
        filt_blob = d.ljust(0x30, b"\0") + n

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("SUB", "SP, #0xC")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("ADD", "R4, R1, #0x0")
        b.insn("MOV", "R0, #0x0")
        b.insn("STR", "R0, [SP, #0x8]")
        b.ldr_const(0, STATE)
        b.insn("LDR", "R0, [R0, #0x7C]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "target")
        b.ldr_const(0, ACTING)
        b.insn("LDR", "R0, [R0, #0x50]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "target")
        b.insn("LDRH", "R1, [R0, #0x0]")
        b.insn("LDRH", "R2, [R5, #0x0]")
        b.insn("CMP", "R1, R2")
        b.insn("BNE", "target")
        b.insn("LDRH", "R1, [R0, #0x12]")
        b.insn("CMP", "R1, #0x2")
        b.insn("BGE", "target")
        b.ldr_const(6, self.filt | 1)
        b.insn("CMP", "R1, #0x0")
        b.insn("BEQ", "cost")
        b.ldr_const(6, filt_non | 1)
        b.label("cost")
        for builder in (HAND_BUILDER, GY_BUILDER):
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x0]")
            b.ldr_const(0, BANISH_FLAGS)
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.insn("ADD", "R2, R6, #0x0")
            b.insn("ADD", "R3, SP, #0x8")
            b.call_addr(builder, via=R7)
        b.insn("B", "out")
        b.label("target")
        b.insn("LDR", "R0, [R5, #0x8]")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("MOV", "R0, #0x2")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.call_addr(HAND_BUILDER, R4, R1, 0, 0, via=R7)
        b.insn("LDR", "R0, [R5, #0x8]")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("MOV", "R0, #0xA")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.call_addr(DECK_BUILDER, R4, R1, 0, 0, via=R7)
        b.insn("LDR", "R0, [R5, #0x8]")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("MOV", "R0, #0x2")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.call_addr(DECK_BUILDER, R4, R1, self.nomi | 1, 0, via=R7)
        b.label("out")
        b.insn("ADD", "SP, #0xC")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        hand = b.assemble(self.hand, pad="nop")

        b = EffectBuilder()                  # restricted-class predicate; at entry [sp] = &card word
        b.insn("PUSH", "{R3, LR}")
        b.insn("LDR", "R0, [SP, #0x8]")
        b.insn("LDR", "R0, [R0, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.call_addr(CLASSIFIER, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.insn("MOV", "R0, #0x1")
        b.label("no")
        b.insn("POP", "{R3, PC}")
        nomi = b.assemble(self.nomi, pad="nop")

        def scan(b, tag, off, count_off):
            """OR into r5: bit 0 = a Dinosaur, bit 1 = a non-Dinosaur monster, in player r7's zone."""
            b.insn("LDR", f"R0, [R7, #0x{count_off:X}]")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R6, #0x0")
            b.label(f"{tag}lp")
            b.insn("LDR", "R0, [SP, #0x4]")
            b.insn("CMP", "R6, R0")
            b.insn("BGE", f"{tag}end")
            b.insn("LSL", "R0, R6, #0x2")
            b.insn("ADD", "R0, R7, R0")
            b.ldr_const(1, off)
            b.insn("ADD", "R0, R0, R1")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call_addr(RACE_GETTER, via=R3)
            b.insn("CMP", f"R0, #{DINO}")
            b.insn("BNE", f"{tag}nd")
            b.insn("MOV", "R1, #0x1")
            b.insn("ORR", "R5, R1")
            b.insn("B", f"{tag}nx")
            b.label(f"{tag}nd")
            b.insn("CMP", f"R0, #{SPELL}")
            b.insn("BGE", f"{tag}nx")
            b.insn("MOV", "R1, #0x2")
            b.insn("ORR", "R5, R1")
            b.label(f"{tag}nx")
            b.insn("ADD", "R6, #0x1")
            b.insn("B", f"{tag}lp")
            b.label(f"{tag}end")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("SUB", "SP, #0x8")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("STR", "R1, [SP, #0x0]")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "native")
        b.insn("ADD", "R0, R4, #0x0")
        b.call_addr(ONCE_CHECK, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRB", "R1, [R4, #0x6]")
        b.insn("EOR", "R0, R1")
        b.ldr_const(7, PLAYER)
        b.insn("MOV", "R1, #0x1")
        b.insn("AND", "R0, R1")
        b.insn("BEQ", "p0")
        b.ldr_const(1, STRIDE)
        b.insn("ADD", "R7, R7, R1")
        b.label("p0")
        b.insn("MOV", "R5, #0x0")
        scan(b, "h", HAND_OFF, HAND_COUNT)
        scan(b, "g", GY_OFF, GY_COUNT)
        b.insn("CMP", "R5, #0x3")
        b.insn("BNE", "no")
        b.label("native")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDR", "R1, [SP, #0x0]")
        b.call_addr(NATIVE_COND, via=R3)
        b.insn("ADD", "SP, #0x8")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("ADD", "SP, #0x8")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        cond = b.assemble(self.cond, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(SHORT, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "done")
        b.insn("LDRB", "R5, [R4, #0x2]")
        b.ldr_const(6, STATE)
        b.insn("LDR", "R0, [R6, #0x7C]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "ph0")
        b.insn("CMP", "R0, #0x1")
        b.insn("BEQ", "ph1")
        b.insn("CMP", "R0, #0x2")
        b.insn("BEQ", "ph2")
        b.insn("CMP", "R0, #0x3")
        b.insn("BEQ", "ph3")
        b.call_addr(CPUSH, via=R3)
        b.insn("MOV", "R7, #0x0")
        b.label("lp")
        b.insn("LSL", "R0, R7, #0x1")
        b.insn("ADD", "R0, R4, R0")
        b.insn("LDRH", "R6, [R0, #0x14]")
        b.call_addr(HINDEX, R5, R6, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BLT", "gy")
        b.insn("ADD", "R1, R0, #0x0")
        b.call_addr(HBANISH, R5, via=R3)
        b.insn("B", "nx")
        b.label("gy")
        b.call_addr(R2W, R6, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "nx")
        b.insn("ADD", "R1, R0, #0x0")
        b.call_addr(GBANISH, R5, R1, 0, via=R3)
        b.label("nx")
        b.insn("ADD", "R7, #0x1")
        b.insn("CMP", "R7, #0x2")
        b.insn("BLT", "lp")
        b.call_addr(CPOP, via=R3)
        b.call_addr(COPY_EXEMPT, R4, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "done")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.turnlog_post(R0, R1, 1, via=R7)
        b.label("done")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("ph0")
        b.insn("MOV", "R0, #0x0")
        b.insn("STRH", "R0, [R4, #0x12]")
        b.insn("B", "next")
        b.label("ph1")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", f"R1, #0x{PROMPT:X}")
        b.call_addr(MESSAGE, via=R3)
        b.insn("B", "next")
        b.label("ph2")
        b.ldr_const(0, ACTING)
        b.insn("STR", "R4, [R0, #0x50]")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", "R1, #0x6")
        b.insn("LDRH", "R2, [R4, #0x0]")
        b.call_addr(PICKER, R0, R1, R2, 0, via=R7)
        b.insn("B", "next")
        b.label("ph3")
        b.call_addr(READBACK, via=R3)
        b.insn("LDR", "R1, [R0, #0x0]")
        b.insn("LSL", "R0, R1, #0x11")
        b.insn("LSR", "R0, R0, #0x1F")
        b.insn("LSL", "R1, R1, #0x1")
        b.insn("LSR", "R1, R1, #0x18")
        b.insn("LSL", "R1, R1, #0x1")
        b.insn("ADD", "R1, R1, R0")
        b.insn("LDRH", "R0, [R4, #0x12]")
        b.insn("LSL", "R2, R0, #0x1")
        b.insn("ADD", "R2, R4, R2")
        b.insn("STRH", "R1, [R2, #0x14]")
        b.insn("ADD", "R0, #0x1")
        b.insn("STRH", "R0, [R4, #0x12]")
        b.insn("MOV", "R1, #0x4")
        b.insn("CMP", "R0, #0x2")
        b.insn("BGE", "setp")
        b.insn("MOV", "R1, #0x1")
        b.label("setp")
        b.insn("STR", "R1, [R6, #0x7C]")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("next")
        b.insn("LDR", "R0, [R6, #0x7C]")
        b.insn("ADD", "R0, #0x1")
        b.insn("STR", "R0, [R6, #0x7C]")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        cost = b.assemble(self.cost, pad="nop")

        stubs = ((self.filt, filt_blob, "Dinosaur / non-Dinosaur filters"), (self.hand, hand, "criteria handler"),
                 (self.nomi, nomi, "restricted-class predicate"), (self.cond, cond, "cls0 +0C cond"),
                 (self.cost, cost, "cls0 +10 cost"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        patched = (cid, self.resolver, 0, self.cond | 1, self.cost | 1, 0)
        return Compiled(stubs,
                        (Row(CRITERIA, (cid, 0xFFFF, self.hand | 1, self.word), self.phantom),),
                        (Edit(CLS0, cid, self.native, patched),))



SPEC = card(
    0x1319,
    banish_dinosaur_and_non_dinosaur_summon_high_level_dinosaur(
        native=(0x1319, 0x0220DFED, 0, 0x021F3C0D, 0x021E7BE5, 0),
        resolver=0x02206F41,                                # Emergency Teleport's hand-or-Deck SS resolver
        word=0x485C0002,                                    # Dinosaur, Level >= 7, monster
        cond=ov5_cave.CAVE_DEP_COND, cost=ov5_cave.CAVE_DEP_COST, hand=ov5_cave.CAVE_DEP_HAND,
        filt=ov5_cave.CAVE_DEP_FILT, nomi=ov5_cave.CAVE_DEP_NOMI, phantom=0x16FD))

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_double_evolution_pill.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
