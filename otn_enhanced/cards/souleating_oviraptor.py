"""Souleating Oviraptor (DARK / Dinosaur / Level 4 / 1800 / 500) on Two-Headed King Rex 0x0FC6.

    If this card is Normal or Special Summoned: You can take 1 Dinosaur-Type monster from your Deck, and either add it
    to your hand or send it to the Graveyard. You can target 1 other Level 4 or lower Dinosaur-Type monster on the
    field; destroy it, then Special Summon 1 Dinosaur-Type monster from your Graveyard in Defense Position. You can only
    use each effect of "Souleating Oviraptor" once per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS1, CLS3, CRITERIA, Compiled, LIST_CODE7, LIST_CODE9, NATIVE_COND, Row, _TURNLOG_POST, _TURNLOG_QUERY, _append_criteria_row
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
from otn_enhanced.effects.common import insert_sorted
from otn_enhanced.effects.common import rows


@dataclass(frozen=True)
class normal_or_special_summoned_take_deck_card_to_hand_or_grave_once_per_turn:
    """'If this card is Normal or Special Summoned: You can take 1 <race> monster from your Deck, and either add it to your
    hand or send it to the Graveyard. Once per turn.' Same recipe as normal_or_special_summoned_search_group_once_per_turn
    (code-7 + code-9 lists, Gearframe-shaped cls1, +0C turn-log gate -> native 0x021F0821, +10 'You can' tag whose Yes
    stamps, shared timing_class_hook arm, criteria rel 0 = the plain Deck handler) with a custom resolver (+04):
    phase 0x80 asks the 2-option prompt 0x0219ABB5 (hand / Graveyard), returns private phase 0x90; 0x90 stores the answer
    in desc[+0x18] (read by neither native on the donor's default arm) and puts the phase word back to 0x80; every phase
    then runs the add-to-hand 0x02207EF5 or the Deck-send 0x02208DD5. Known shape difference: the hand/GY choice is asked
    at resolution BEFORE the Deck pick."""
    res: int
    cond: int
    slot4: int
    crit: tuple[int, int, int]               # criteria rel 0: (aux, handler, word)
    phantoms: tuple[int, int, int, int]      # (code-7 list, code-9 list, cls1, criteria rel 0)
    kind: int = 1

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import timing_class_hook as tch
        ADD_TO_HAND, DECK_SEND, HAVE_TARGET, TAG, PROMPT = 0x02207EF5, 0x02208DD5, 0x021F0821, 0x021E51E5, 0x0219ABB5
        PHASE_STATE, CHOICE_STATE, PRIVATE = 0x0229AAFC, 0x0229DD94, 0x90
        TITLE, LABEL_HAND, LABEL_GY = 0x0103, 0x58, 0x3A
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.turnlog_query(R0, cid, self.kind, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "used")
        b.call_addr(HAVE_TARGET, R5, via=R4)
        b.insn("POP", "{R4, R5, PC}")
        b.label("used")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, PC}")
        cb = b.assemble(self.cond, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(TAG, via=R2)
        b.insn("CMP", "R0, #0x1")
        b.insn("BNE", "out")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_post(R0, cid, self.kind, via=R4)
        b.insn("ADD", "R0, R5, #0x0")
        b.label("out")
        b.insn("POP", "{R4, R5, PC}")
        sb = b.assemble(self.slot4, pad="nop")
        b = EffectBuilder()                  # r1-r3 are pushed only to reserve [sp]..[sp+8] for the prompt's stack args
        b.insn("PUSH", "{R1, R2, R3, R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.ldr_const(5, PHASE_STATE)
        b.insn("LDR", "R0, [R5, #0x70]")
        b.insn("CMP", "R0, #0x80")
        b.insn("BNE", "not80")
        b.insn("MOV", "R0, #0x0")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("MOV", "R0, #0x3")
        b.insn("STR", "R0, [SP, #0x8]")
        b.call_addr(PROMPT, R4, TITLE, LABEL_HAND, LABEL_GY, via=R5)
        b.insn("MOV", f"R0, #0x{PRIVATE:X}")
        b.insn("B", "out")
        b.label("not80")
        b.insn("CMP", f"R0, #0x{PRIVATE:X}")
        b.insn("BNE", "go")
        b.ldr_const(0, CHOICE_STATE)
        b.insn("LDR", "R0, [R0, #0x34]")
        b.insn("STRH", "R0, [R4, #0x18]")
        b.insn("MOV", "R0, #0x80")
        b.insn("STR", "R0, [R5, #0x70]")
        b.label("go")
        b.ldr_const(5, ADD_TO_HAND)
        b.insn("LDRH", "R0, [R4, #0x18]")
        b.insn("CMP", "R0, #0x1")
        b.insn("BNE", "call")
        b.ldr_const(5, DECK_SEND)
        b.label("call")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("MOV", "R1, #0x0")
        b.insn("BLX", "R5")
        b.label("out")
        b.insn("POP", "{R1, R2, R3, R4, R5, PC}")
        rb = b.assemble(self.res, pad="nop")
        stubs = ((self.cond, cb, "C1 +0C cond"), (self.slot4, sb, "C1 +10 slot4"), (self.res, rb, "C1 resolver"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        for a_ in (ADD_TO_HAND, DECK_SEND, HAVE_TARGET, TAG, _TURNLOG_QUERY, _TURNLOG_POST, PROMPT):
            assert a_ & 1, f"{a_:#x}: blx to an even literal switches to ARM state -> freeze"
        assert any(a[0] == cid for a in tch.ARMS), "the timing arm must be registered in timing_class_hook"
        ph7, ph9, ph1, phc = self.phantoms
        row0 = (cid,) + self.crit

        def install(rom, view):
            insert_sorted(view, CRITERIA, row0, drop=phc, quiet=True)
            tch.apply(view.buf)
            tch.install(rom, quiet=True)

        def check(c, rom, view):
            tch.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)

        return Compiled(stubs,
                        (Row(LIST_CODE7, (cid,), ph7), Row(LIST_CODE9, (cid,), ph9),
                         Row(CLS1, (cid, 0, self.res | 1, 0, self.cond | 1, self.slot4 | 1, 0), ph1)),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class destroy_other_low_level_monster_then_revive_from_gy_once_per_turn:
    """'You can target 1 other Level N or lower <race> monster on the field; destroy it, then Special Summon 1 <race>
    monster from your Graveyard in Defense Position. Once per turn.' User rulings: the SS may pick the monster just
    destroyed; NO SS unless the destroy happened; activation needs a legal target AND a <race> in your GY.
    cls3 {RES, FILT, COND, COST, board target step 0x02234DA5} (Uria / Cyber Laser Dragon's shape): FILT = the face-up
    field wrapper, not this card's own slot, live Level <= N, live race (the native filter's exact 0x021B88F0 call);
    COND = kind-2 clear (desc[+7] guard) + a direct own-GY race scan (the row hook's acting descriptor may be stale at menu
    time) + native 0x021F01C1; COST = stamp kind 2 at ACTIVATION, then native 0x021E5061; RES phases: 0x80 destroy body ->
    0x90: [0x0229C314+0x14] == 0 -> end (the native destroy-then protocol), SS gates + candidates, then the picker /
    commit phases, position 1 = DEF. criteria rel 1 = a Graveyard row after rel 0; criteria_row_hook arm: cls3 -> rel 1."""
    templates: tuple                 # cls3 cids with the same +04/+0C/+10/+14 (asserted)
    race: int
    max_level: int
    gy_crit: tuple[int, int]         # criteria rel 1: (handler, word), aux 0xFFFF
    res: int
    filt: int
    cond: int
    cost: int
    phantoms: tuple[int, int]        # (cls3, criteria rel 1)
    kind: int = 2

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import criteria_row_hook as crh
        DESTROY_TARGET, TARGET_STEP, NATIVE_COND, NATIVE_COST = 0x02204899, 0x02234DA5, 0x021F01C1, 0x021E5061
        FACEUP, LEVEL_GETTER, RACE_LIVE = 0x021DB4F9, 0x021B807D, 0x021B88F1
        STAMP_BASE, PLAYER_BASE, PLAYER_STRIDE, GY_ARRAY, GY_COUNT = 0x0229ACCC, 0x0229AC94, 0xB3C, 0x55C, 0x14
        DESTROY_BODY, DESTROYED = 0x02204675, 0x0229C314
        SS_GATES = (0x021AD871, 0x021B9ECD, 0x021B9ED9)
        CANDIDATES, MESSAGE, PICKER, READBACK, SS_COMMIT = 0x02243FA9, 0x0219A819, 0x0219C431, 0x0219C511, 0x0226925D
        NO_CANDIDATE_CLEANUP, TEARDOWN, PHASE_STATE, PRIVATE = 0x0225BF31, 0x021D269D, 0x0229AAFC, 0x90
        race, kind = self.race, self.kind
        c3 = [r for r in rows(view, CLS3)]
        for t in self.templates:
            r = [x for x in c3 if x[0] == t]
            assert len(r) == 1 and (r[0][1], r[0][3], r[0][4], r[0][5]) == (
                DESTROY_TARGET, NATIVE_COND, NATIVE_COST, TARGET_STEP), f"cls3 template {t:#x} drifted"
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("ADD", "R6, R1, #0x0")
        b.insn("ADD", "R7, R2, #0x0")
        b.call_addr(FACEUP, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.insn("CMP", "R0, R6")
        b.insn("BNE", "notself")
        b.insn("LDRB", "R0, [R5, #0x3]")
        b.insn("CMP", "R0, R7")
        b.insn("BEQ", "no")
        b.label("notself")
        b.call_addr(LEVEL_GETTER, R6, R7, 0, via=R3)
        b.insn("CMP", f"R0, #0x{self.max_level:X}")
        b.insn("BGT", "no")
        b.insn("MOV", "R2, #0x0")
        b.insn("LDRB", "R0, [R5, #0x3]")
        b.insn("CMP", "R0, #0xA")
        b.insn("BGT", "race")
        b.insn("LSL", "R1, R0, #0x4")
        b.insn("LSL", "R0, R0, #0x2")
        b.insn("ADD", "R0, R0, R1")
        b.insn("LDRB", "R1, [R5, #0x2]")
        b.insn("MOV", "R2, #0x1")
        b.insn("AND", "R1, R2")
        b.insn("BEQ", "stamp")
        b.ldr_const(1, PLAYER_STRIDE)
        b.insn("ADD", "R0, R0, R1")
        b.label("stamp")
        b.ldr_const(1, STAMP_BASE)
        b.insn("LDRH", "R2, [R0, R1]")
        b.label("race")
        b.call_addr(RACE_LIVE, R6, R7, via=R3)
        b.insn("CMP", f"R0, #0x{race:X}")
        b.insn("BNE", "no")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        filt = b.assemble(self.filt, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "chain")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_query(R0, cid, kind, via=R5)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRB", "R1, [R4, #0x6]")
        b.insn("EOR", "R0, R1")
        b.insn("MOV", "R1, #0x1")
        b.insn("AND", "R0, R1")
        b.ldr_const(5, PLAYER_BASE)
        b.insn("BEQ", "side0")
        b.ldr_const(1, PLAYER_STRIDE)
        b.insn("ADD", "R5, R5, R1")
        b.label("side0")
        b.insn("LDR", f"R6, [R5, #0x{GY_COUNT:X}]")
        b.ldr_const(1, GY_ARRAY)
        b.insn("ADD", "R5, R5, R1")
        b.label("loop")
        b.insn("CMP", "R6, #0x0")
        b.insn("BLE", "no")
        b.insn("SUB", "R6, #0x1")
        b.insn("LSL", "R0, R6, #0x2")
        b.insn("LDR", "R0, [R5, R0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.call("get_race", via=R3)
        b.insn("CMP", f"R0, #0x{race:X}")
        b.insn("BNE", "loop")
        b.label("chain")
        b.call_addr(NATIVE_COND, R4, via=R3)
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        cond = b.assemble(self.cond, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_post(R0, cid, kind, via=R5)
        b.call_addr(NATIVE_COST, R4, via=R5)
        b.insn("POP", "{R4, R5, PC}")
        cost = b.assemble(self.cost, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R6, [R5, #0x2]")
        b.insn("LDRB", "R0, [R5, #0x6]")
        b.insn("EOR", "R6, R0")
        b.ldr_const(4, PHASE_STATE)
        b.insn("LDR", "R4, [R4, #0x70]")
        b.insn("CMP", "R4, #0x80")
        b.insn("BEQ", "ph80")
        b.insn("CMP", f"R4, #0x{PRIVATE:X}")
        b.insn("BEQ", "ph90")
        b.insn("CMP", "R4, #0x7F")
        b.insn("BEQ", "ph7f")
        b.insn("CMP", "R4, #0x7E")
        b.insn("BEQ", "ph7e")
        b.insn("CMP", "R4, #0x7C")
        b.insn("BEQ", "ph7c")
        b.insn("CMP", "R4, #0x7B")
        b.insn("BEQ", "ph7b")
        b.insn("CMP", "R4, #0x78")
        b.insn("BEQ", "ph78")
        b.insn("B", "stop")
        b.label("ph80")
        b.call_addr(DESTROY_BODY, R5, via=R3)
        b.insn("MOV", f"R0, #0x{PRIVATE:X}")
        b.insn("B", "ret")
        b.label("ph90")
        b.ldr_const(0, DESTROYED)
        b.insn("LDR", "R0, [R0, #0x14]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "stop")
        for gate in SS_GATES:
            b.call_addr(gate, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.call_addr(CANDIDATES, R0, R1, 0, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "have")
        b.call_addr(MESSAGE, R6, 0xD, via=R3)
        b.insn("MOV", "R0, #0x7B")
        b.insn("B", "ret")
        b.label("have")
        b.insn("MOV", "R0, #0x7F")
        b.insn("B", "ret")
        b.label("ph7f")
        b.call_addr(MESSAGE, R6, 0x30, via=R3)
        b.insn("MOV", "R0, #0x7E")
        b.insn("B", "ret")
        b.label("ph7e")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("MOV", "R1, #0x6")
        b.insn("LDRH", "R2, [R5, #0x0]")
        b.call_addr(PICKER, R0, R1, R2, 0, via=R7)
        b.insn("MOV", "R0, #0x7C")
        b.insn("B", "ret")
        b.label("ph7c")
        b.call_addr(READBACK, via=R7)
        b.insn("ADD", "R1, R0, #0x0")
        b.insn("LDRH", "R0, [R5, #0x0]")
        b.insn("LSL", "R0, R0, #0x10")
        b.insn("STR", "R0, [SP, #0x0]")
        b.call_addr(SS_COMMIT, R6, R1, 1, 1, via=R7)        # position 1 = Defense
        b.insn("MOV", "R0, #0x78")
        b.insn("B", "ret")
        b.label("ph7b")
        b.insn("MOV", "R0, #0x1")
        b.insn("SUB", "R0, R0, R6")
        b.call_addr(NO_CANDIDATE_CLEANUP, via=R3)
        b.insn("MOV", "R0, #0x78")
        b.insn("B", "ret")
        b.label("ph78")
        b.call_addr(TEARDOWN, R6, via=R3)
        b.insn("MOV", "R0, #0x64")
        b.insn("B", "ret")
        b.label("stop")
        b.insn("MOV", "R0, #0x0")
        b.label("ret")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        res = b.assemble(self.res, pad="nop")
        stubs = ((self.filt, filt, "C2 filter"), (self.cond, cond, "C2 cond"), (self.cost, cost, "C2 cost"),
                 (self.res, res, "C2 resolver"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        for a_ in (DESTROY_TARGET, TARGET_STEP, NATIVE_COND, NATIVE_COST, self.gy_crit[0], FACEUP, LEVEL_GETTER, RACE_LIVE,
                   DESTROY_BODY, CANDIDATES, MESSAGE, PICKER, READBACK, SS_COMMIT, NO_CANDIDATE_CLEANUP, TEARDOWN, *SS_GATES):
            assert a_ & 1, f"{a_:#x}: blx to an even literal switches to ARM state -> freeze"
        assert any(a[0] == cid for a in crh.ARMS), "the row arm must be registered in criteria_row_hook"
        ph3, phc1 = self.phantoms
        row1 = (cid, 0xFFFF) + self.gy_crit

        def install(rom, view):
            row0s = [r for r in rows(view, CRITERIA) if r[0] == cid]
            assert len(row0s) >= 1, "criteria rel 0 must be inserted first"
            _append_criteria_row(view, cid, row1, phc1, row0s[:1])
            crh.apply(view.buf)
            crh.install(rom, quiet=True)

        def check(c, rom, view):
            recs = rows(view, CRITERIA)
            ks = [r[0] for r in recs]
            mine = [r for r in recs if r[0] == cid]
            c.ok(ks == sorted(ks) and len(mine) == 2 and mine[1] == row1 and phc1 not in ks,
                 "criteria rel 1 (GY row) after rel 0, phantom dropped, sorted")
            crh.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)

        return Compiled(stubs,
                        (Row(CLS3, (cid, self.res | 1, self.filt | 1, self.cond | 1, self.cost | 1, TARGET_STEP), ph3),),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x0FC6,
    normal_or_special_summoned_take_deck_card_to_hand_or_grave_once_per_turn(
        res=ov5_cave.CAVE_OVI_RES, cond=ov5_cave.CAVE_OVI_COND, slot4=ov5_cave.CAVE_OVI_SLOT4,
        crit=(0xFFFF, 0x0223CAD9, 0x48000002),                      # Deck, race byte 0x48 = Dinosaur
        phantoms=(0x19C0, 0x1ABF, 0x0E47, 0x0E67)),
    destroy_other_low_level_monster_then_revive_from_gy_once_per_turn(
        templates=(0x19A3, 0x19A9),                                 # Uria, Cyber Laser Dragon
        race=9, max_level=4, gy_crit=(0x0223CA11, 0x48000002),      # Survival Instinct's GY Dinosaur row
        res=ov5_cave.CAVE_OVI_C2RES, filt=ov5_cave.CAVE_OVI_C2FILT, cond=ov5_cave.CAVE_OVI_C2COND,
        cost=ov5_cave.CAVE_OVI_C2COST, phantoms=(0x0E3F, 0x0E69)))

PROPS = card_props("DARK", "Dinosaur", level=4, atk=1800, defense=500)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_souleating_oviraptor.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
