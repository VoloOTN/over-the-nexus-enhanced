"""Neo Space Connector (LIGHT / Warrior / Level 4 / 800 / 1800) on Kanan the Swordmistress 0x1106.

    When this card is Normal Summoned: You can Special Summon 1 "Neo-Spacian" monster or 1 "Elemental HERO Neos" from
    your hand or Deck in Defense Position. You can Tribute this card, then target 1 "Neo-Spacian" monster or 1 "Elemental
    HERO Neos" in your GY; Special Summon it in Defense Position. You can only use each effect of "Neo Space Connector"
    once per turn.
"""
import struct
import sys

import ndspy.rom

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS1, CLS3, CRITERIA, Compiled, LIST_CODE7, Row, _TURNLOG_POST, _TURNLOG_QUERY, _timing_arms_check, _timing_arms_install
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
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class normal_summoned_special_summon_group_monster_from_hand_or_deck_once_per_turn:
    """'When this card is Normal Summoned: You can Special Summon 1 <group> monster from your hand or Deck in Defense
    Position. Once per turn.' code-7 list + cls1 {RES, 0, COND, SLOT4, 0} + ONE criteria row {cid, aux, CRIT, word}
    (criteria_row_hook is full): the CRIT handler switches on the acting descriptor [0x0229A9FC+0x50] -- desc[+0] == donor and
    desc[+5] == 3 (the cls3 clause) -> GY builder (flags 8, GY word); otherwise a clone of the native hand+Deck selector
    0x0223ECB0 (hand + Deck builders). ONE predicate (`pred`: cid = word & 0x3FFF is a member of `group`) serves all builders
    and both conds. COND = kind-1 clear + a DIRECT hand + Deck scan (the acting descriptor can be stale at menu time);
    SLOT4 = 'You can' tag, a Yes stamps; RES = the Deck-SS machine (gates + candidates, message, picker, commit with
    position 1 = face-up DEFENSE, shuffle). Shared timing_class_hook arm."""
    group: tuple
    pred: int
    crit: int
    cond: int
    slot4: int
    res: int
    aux: int
    word: int
    gy_word: int
    phantoms: tuple[int, int, int]    # (code-7 list, cls1, criteria)
    kind: int = 1

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import timing_class_hook as tch
        HAND_B, DECK_B, GY_B, ACTING = 0x0223C16D, 0x0223BC3D, 0x0223C4E9, 0x0229A9FC
        TAG, PLAYER_BASE, PLAYER_STRIDE = 0x021E51E5, 0x0229AC94, 0xB3C
        HAND_ARRAY, HAND_COUNT, DECK_ARRAY, DECK_COUNT = 0x124, 0xC, 0x304, 0x10
        PHASE_STATE, CANDIDATES, MESSAGE, PICKER, READBACK = 0x0229AAFC, 0x02243FA9, 0x0219A819, 0x0219C431, 0x0219C511
        SS_COMMIT, CLEANUP, SHUFFLE = 0x0226925D, 0x0225BF31, 0x021D269D
        SS_GATES = (0x021AD871, 0x021B9ECD, 0x021B9ED9)
        assert list(self.group) == sorted(set(self.group)) and cid not in self.group
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("LDR", "R0, [SP, #0x8]")
        b.insn("LDR", "R0, [R0, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        for g in self.group:
            b.ldr_const(1, g)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "yes")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        b.label("yes")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, PC}")
        pred = b.assemble(self.pred, pad="nop")
        predp = self.pred | 1

        b = EffectBuilder()
        b.insn("PUSH", "{R1, R2, R3, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("ADD", "R4, R1, #0x0")
        b.ldr_const(0, ACTING)
        b.insn("LDR", "R0, [R0, #0x50]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "handdeck")
        b.insn("LDRH", "R1, [R0, #0x0]")
        b.ldr_const(2, cid)
        b.insn("CMP", "R1, R2")
        b.insn("BNE", "handdeck")
        b.insn("LDRB", "R1, [R0, #0x5]")
        b.insn("CMP", "R1, #0x3")
        b.insn("BNE", "handdeck")
        b.ldr_const(0, self.gy_word)
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("MOV", "R0, #0x8")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.ldr_const(2, predp)
        b.call_addr(GY_B, R0, R1, R2, 0, via=R6)
        b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
        b.label("handdeck")
        b.insn("MOV", f"R0, #0x{self.aux:X}")
        b.insn("STR", "R0, [SP, #0x8]")
        b.insn("ADD", "R7, SP, #0x8")
        b.insn("MOV", f"R0, #0x{self.word:X}")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("MOV", "R0, #0x2")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.ldr_const(2, predp)
        b.call_addr(HAND_B, R0, R1, R2, R7, via=R6)
        b.insn("MOV", f"R0, #0x{self.word:X}")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("MOV", "R0, #0xA")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("LDRH", "R1, [R5, #0x0]")
        b.ldr_const(2, predp)
        b.call_addr(DECK_B, R0, R1, R2, R7, via=R6)
        b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
        crit = b.assemble(self.crit, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_query(R0, cid, self.kind, via=R5)
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
        b.insn("LDR", f"R6, [R5, #0x{HAND_COUNT:X}]")
        b.ldr_const(7, HAND_ARRAY)
        b.insn("ADD", "R7, R5, R7")
        b.bl_label("scan")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "yes")
        b.insn("LDR", f"R6, [R5, #0x{DECK_COUNT:X}]")
        b.ldr_const(7, DECK_ARRAY)
        b.insn("ADD", "R7, R5, R7")
        b.bl_label("scan")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "yes")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("yes")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("scan")
        b.insn("PUSH", "{R3, LR}")
        b.label("sloop")
        b.insn("CMP", "R6, #0x0")
        b.insn("BLE", "snone")
        b.insn("STR", "R7, [SP, #0x0]")
        b.call_addr(self.pred)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "sout")
        b.insn("ADD", "R7, #0x4")
        b.insn("SUB", "R6, #0x1")
        b.insn("B", "sloop")
        b.label("snone")
        b.insn("MOV", "R0, #0x0")
        b.label("sout")
        b.insn("POP", "{R3, PC}")
        cond = b.assemble(self.cond, pad="nop")

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
        slot4 = b.assemble(self.slot4, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R6, [R5, #0x2]")
        b.insn("LDRB", "R0, [R5, #0x6]")
        b.insn("EOR", "R6, R0")
        b.ldr_const(4, PHASE_STATE)
        b.insn("LDR", "R4, [R4, #0x70]")
        for ph, lab in ((0x80, "ph80"), (0x7F, "ph7f"), (0x7E, "ph7e"), (0x7C, "ph7c"), (0x7B, "ph7b"), (0x78, "ph78")):
            b.insn("CMP", f"R4, #0x{ph:X}")
            b.insn("BEQ", lab)
        b.insn("B", "stop")
        b.label("ph80")
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
        b.call_addr(SS_COMMIT, R6, R1, 1, 1, via=R7)        # position 1 = face-up Defense
        b.insn("MOV", "R0, #0x78")
        b.insn("B", "ret")
        b.label("ph7b")
        b.insn("MOV", "R0, #0x1")
        b.insn("SUB", "R0, R0, R6")
        b.call_addr(CLEANUP, via=R3)
        b.insn("MOV", "R0, #0x78")
        b.insn("B", "ret")
        b.label("ph78")
        b.call_addr(SHUFFLE, R6, via=R3)
        b.insn("MOV", "R0, #0x64")
        b.insn("B", "ret")
        b.label("stop")
        b.insn("MOV", "R0, #0x0")
        b.label("ret")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        res = b.assemble(self.res, pad="nop")
        stubs = ((self.pred, pred, "group predicate"), (self.crit, crit, "criteria handler"), (self.cond, cond, "C1 cond"),
                 (self.slot4, slot4, "C1 slot4"), (self.res, res, "C1 resolver"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        for a_ in (HAND_B, DECK_B, GY_B, TAG, _TURNLOG_QUERY, _TURNLOG_POST, CANDIDATES, MESSAGE, PICKER, READBACK, SS_COMMIT,
                   CLEANUP, SHUFFLE, *SS_GATES):
            assert a_ & 1, f"{a_:#x}: blx to an even literal switches to ARM state -> freeze"
        assert any(a[0] == cid for a in tch.ARMS), "the timing arm must be registered in timing_class_hook"
        ph7, ph1, phc = self.phantoms

        def install(rom, view):
            mc, sec = ov5_cave._arm9_main(rom)             # the group must still be the live Neo-Spacian list + Neos
            o = 0x0209C702 - sec.ramAddress
            live = struct.unpack_from("<8H", sec.data, o)
            assert tuple(sorted(live + (0x19FD,))) == tuple(self.group), f"Neo-Spacian list drifted: {[hex(c) for c in live]}"
            _timing_arms_install(rom, view)

        def check(c, rom, view):
            _timing_arms_check(c, rom, view)

        return Compiled(stubs,
                        (Row(LIST_CODE7, (cid,), ph7),
                         Row(CLS1, (cid, 0, self.res | 1, 0, self.cond | 1, self.slot4 | 1, 0), ph1),
                         Row(CRITERIA, (cid, self.aux, self.crit | 1, self.word), phc)),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class tribute_this_card_revive_group_monster_from_gy_in_defense_once_per_turn:
    """'You can Tribute this card, then target 1 <group> monster in your GY; Special Summon it in Defense Position. Once
    per turn.' cls3 {RES, 0, COND, COST, off-field list-zone target template 0x02235605} in the native shape of Necro
    Linker / Blazewing Butterfly. COND: desc[+7] == 0 (menu) -> kind-2 clear AND a listed cid in the own GY (DIRECT scan,
    never the row), then always Mystic Piper's cid-blind gate 0x021F06E9; COST: stamp kind 2 at ACTIVATION, then the
    Tribute-self cost 0x021E50CD; RES: 0x02204731(desc, 1, position 1 = face-up DEFENSE) -- the native revive's default
    arm with r5 = 1 instead of 2. The +14 template reaches the clause-1 criteria row as a SLOT call with this cls3
    descriptor acting, so the handler takes its GY mode. cls3 returns before the timing-class site: no new timing arm."""
    templates: dict
    pred: int
    cond: int
    cost: int
    res: int
    phantom: int
    kind: int = 2

    def compile(self, view, cid) -> Compiled:
        TARGET, GENERIC_COND, TRIBUTE, SS_LIST = 0x02235605, 0x021F06E9, 0x021E50CD, 0x02204731
        PLAYER_BASE, PLAYER_STRIDE, GY_ARRAY, GY_COUNT = 0x0229AC94, 0xB3C, 0x55C, 0x14
        c3 = list(rows(view, CLS3))
        for t, slots in self.templates.items():
            r = [x for x in c3 if x[0] == t]
            assert len(r) == 1 and (r[0][1], r[0][2], r[0][3], r[0][4], r[0][5]) == slots, f"cls3 template {t:#x} drifted: {r}"
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "chain")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_query(R0, cid, self.kind, via=R5)
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
        b.ldr_const(7, GY_ARRAY)
        b.insn("ADD", "R7, R5, R7")
        b.insn("PUSH", "{R3}")
        b.label("sloop")
        b.insn("CMP", "R6, #0x0")
        b.insn("BLE", "snone")
        b.insn("STR", "R7, [SP, #0x0]")
        b.call_addr(self.pred)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "found")
        b.insn("ADD", "R7, #0x4")
        b.insn("SUB", "R6, #0x1")
        b.insn("B", "sloop")
        b.label("snone")
        b.insn("POP", "{R3}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("found")
        b.insn("POP", "{R3}")
        b.label("chain")
        b.call_addr(GENERIC_COND, R4, via=R3)
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        cond = b.assemble(self.cond, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_post(R0, cid, self.kind, via=R5)
        b.call_addr(TRIBUTE, R4, via=R5)
        b.insn("POP", "{R4, R5, PC}")
        cost = b.assemble(self.cost, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.call_addr(SS_LIST, R0, 1, 1, via=R3)
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        res = b.assemble(self.res, pad="nop")
        stubs = ((self.cond, cond, "C2 cond"), (self.cost, cost, "C2 cost"), (self.res, res, "C2 resolver"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        for a_ in (TARGET, GENERIC_COND, TRIBUTE, SS_LIST):
            assert a_ & 1, f"{a_:#x}: blx to an even literal switches to ARM state -> freeze"
        return Compiled(stubs,
                        (Row(CLS3, (cid, self.res | 1, 0, self.cond | 1, self.cost | 1, TARGET), self.phantom),))



# Set code 0x17 (Neo-Spacian) list 0x0209C702 re-dumped, + "Elemental HERO Neos" 0x19FD. next_card reads these.
NSC_CIDS = (0x19FD, 0x1A70, 0x1A71, 0x1A72, 0x1A73, 0x1A74, 0x1A75, 0x1C06, 0x1D11)
NEOSPACIAN_LIST, NEOSPACIAN_COUNT = 0x0209C702, 8

SPEC = card(
    0x1106,
    normal_summoned_special_summon_group_monster_from_hand_or_deck_once_per_turn(
        group=NSC_CIDS, pred=ov5_cave.CAVE_NSC_PRED, crit=ov5_cave.CAVE_NSC_CRIT, cond=ov5_cave.CAVE_NSC_COND,
        slot4=ov5_cave.CAVE_NSC_SLOT4, res=ov5_cave.CAVE_NSC_RES,
        aux=0x000E, word=0x00000002,                        # Tour Guide's hand+Deck row shape
        gy_word=0x00010002,                                 # Rite of Spirit / Psi-Reflector GY row word
        phantoms=(0x19D3, 0x11EA, 0x14D7)),
    tribute_this_card_revive_group_monster_from_gy_in_defense_once_per_turn(
        templates={0x237A: (0x02207191, 0, 0x021F0BDD, 0x021E50CD, 0x02235605),        # Necro Linker
                   0x1CAD: (0x02207191, 0, 0x021F8E89, 0x021E50CD, 0x02235605)},       # Blazewing Butterfly
        pred=ov5_cave.CAVE_NSC_PRED, cond=ov5_cave.CAVE_NSC_C2COND, cost=ov5_cave.CAVE_NSC_C2COST,
        res=ov5_cave.CAVE_NSC_C2RES, phantom=0x14D7))

PROPS = card_props("LIGHT", "Warrior", level=4, atk=800, defense=1800)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_neo_space_connector.nds")


def _assert_filter_source(rom) -> None:             # next_card calls this
    """NSC_CIDS must still be the live Neo-Spacian set-code list plus Neos."""
    _mc, sec = ov5_cave._arm9_main(rom)
    live = struct.unpack_from(f"<{NEOSPACIAN_COUNT}H", sec.data, NEOSPACIAN_LIST - sec.ramAddress)
    assert tuple(sorted(live + (0x19FD,))) == NSC_CIDS, f"Neo-Spacian list drifted: {[hex(c) for c in live]}"


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
