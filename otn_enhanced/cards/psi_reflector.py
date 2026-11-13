"""Psi-Reflector (DARK / Psychic / Tuner / Level 1 / 400 / 300) on Clown Zombie 0x1008.

    If this card is Normal or Special Summoned: You can add 1 "Assault Mode Activate", or 1 card that specifically lists
    "Assault Mode Activate" in its text, from your Deck to your hand, except "Psi-Reflector". You can reveal 1 "Assault
    Mode Activate" in your hand, then target 1 monster in your GY that specifically lists "Assault Mode Activate" in its
    text, except "Psi-Reflector"; Special Summon it, and if you do, increase its Level by 1 to 4. You can only use each
    effect of "Psi-Reflector" once per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS1, CLS3, CRITERIA, Compiled, LIST_CODE7, LIST_CODE9, Row, _AS_OFFFIELD_PICKER, _TURNLOG_POST, _TURNLOG_QUERY, _append_criteria_row
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
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class set_code_repointed_to_cave_list:
    """A set code whose consumer thunk reads a hardcoded N-entry cid list that cannot hold the group: the thunk's list
    literal is repointed to a longer sorted list in the ov5 cave and its `movs r2,#N` raised. A SIBLING set code that
    reads the stock list through its own literal keeps the stock list bytes (never touched). The ov5 list is a
    'stub' (data blob) so it is checked like one."""
    setcode: int
    thunk: int
    count_imm: int
    list_lit: int
    stock_list: int
    stock_members: tuple
    sibling_lit: int
    group: tuple
    group_addr: int
    ptr_table: int = 0x0209D0D8

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import ARM9_BASE
        assert list(self.group) == sorted(set(self.group)) and cid not in self.group
        n = len(self.group)

        def state(d):
            u32 = lambda a: struct.unpack_from("<I", d, a - ARM9_BASE)[0]
            return (u32(self.ptr_table + self.setcode * 4), u32(self.list_lit),
                    struct.unpack_from("<H", d, self.count_imm - ARM9_BASE)[0], u32(self.sibling_lit))

        def install(rom, view):
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)
            slot, lit, imm, sib = state(bytes(d))
            assert slot == self.thunk | 1, f"has_set_code[{self.setcode:#x}] = {slot:#x}"
            assert sib == self.stock_list, f"sibling set code's literal moved: {sib:#x}"
            if (lit, imm) == (self.group_addr, 0x2200 | n):
                return
            assert (lit, imm) == (self.stock_list, 0x2200 | len(self.stock_members)), \
                f"set code {self.setcode:#x} thunk not stock: lit {lit:#x} imm {imm:#x}"
            assert tuple(struct.unpack_from(f"<{len(self.stock_members)}H", d, self.stock_list - ARM9_BASE)) \
                == self.stock_members, "stock list is not the expected phantoms"
            struct.pack_into("<I", d, self.list_lit - ARM9_BASE, self.group_addr)
            struct.pack_into("<H", d, self.count_imm - ARM9_BASE, 0x2200 | n)
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def check(c, rom, view):
            mc, sec = ov5_cave._arm9_main(rom)
            slot, lit, imm, sib = state(bytes(sec.data))
            c.ok(slot == self.thunk | 1 and lit == self.group_addr and imm == 0x2200 | n,
                 f"set code {self.setcode:#x} -> {self.group_addr:#x} x {n}")
            c.ok(sib == self.stock_list and tuple(struct.unpack_from(f"<{len(self.stock_members)}H", sec.data,
                                                                     self.stock_list - ARM9_BASE)) == self.stock_members,
                 "sibling set code's literal and the stock list are untouched")

        blob = struct.pack(f"<{n}H", *self.group)
        return Compiled(((self.group_addr, blob, "set-code group list"),), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class normal_or_special_summoned_search_group_once_per_turn:
    """'If this card is Normal or Special Summoned: You can add 1 <group> card from your Deck to your hand, except this
    card. Once per turn.' code-7 + code-9 lists; cls1 {add-to-hand, 0, +0C, +10, 0} (a Gearframe-shaped record);
    criteria rel 0 {cid, aux = the group's set code, Deck->hand handler, word}. +0C = turn-log clear -> native
    `have_target`; +10 = 'You can' tag, a Yes stamps. Class-2 'You can' = the shared timing_class_hook arm."""
    add_to_hand: int
    have_target: int
    tag: int
    template: int                     # cid whose cls1 record carries (add_to_hand, 0, have_target, tag, 0)
    crit: tuple[int, int, int]        # (aux, handler, word)
    cond: int
    slot4: int
    phantoms: tuple[int, int, int, int]   # (code-7 list, code-9 list, cls1, criteria rel 0)
    kind: int = 1

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import timing_class_hook as tch
        aux = self.crit[0]
        assert all(a != aux or c == cid for c, a, _h, _w in rows(view, CRITERIA)), f"aux {aux:#x} already used"
        assert any(r[0] == self.template and r[2:] == (self.add_to_hand, 0, self.have_target, self.tag, 0)
                   for r in rows(view, CLS1)), "cls1 template drifted"
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.turnlog_query(R0, cid, self.kind, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "used")
        b.call_addr(self.have_target, R5, via=R4)
        b.insn("POP", "{R4, R5, PC}")
        b.label("used")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, PC}")
        cb = b.assemble(self.cond, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(self.tag, via=R2)
        b.insn("CMP", "R0, #0x1")
        b.insn("BNE", "out")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_post(R0, cid, self.kind, via=R4)
        b.insn("ADD", "R0, R5, #0x0")
        b.label("out")
        b.insn("POP", "{R4, R5, PC}")
        sb = b.assemble(self.slot4, pad="nop")
        for blob, addr in ((cb, self.cond), (sb, self.slot4)):
            assert_thumb1_only(blob, addr)
        for a_ in (self.add_to_hand, self.have_target, self.tag, _TURNLOG_QUERY, _TURNLOG_POST, self.crit[1]):
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

        return Compiled(((self.cond, cb, "C1 +0C cond"), (self.slot4, sb, "C1 +10 slot4")),
                        (Row(LIST_CODE7, (cid,), ph7), Row(LIST_CODE9, (cid,), ph9),
                         Row(CLS1, (cid, 0, self.add_to_hand, 0, self.cond | 1, self.slot4 | 1, 0), ph1)),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class reveal_hand_card_revive_gy_monster_with_level_rider:
    """'You can reveal 1 <named> in your hand, then target 1 <group> monster in your GY, except this card; Special
    Summon it, and if you do, increase its Level by 1 to 4. Once per turn.'
    cls3 {RES, 0, COND, COST, picker 0x02235605}: COND = kind-2 clear, the named card in hand (a direct hand scan: a
    hand ROW probe tests one slot only), then the GY candidate gate; COST = the reveal cost 0x021EAAA1 (the UI path for
    an unlisted cid), a Yes stamps kind 2; RES = Call of the Haunted's phases: 0x80 SS (player picks the position),
    0x7F number picker 1..N, 0x7E Level rider (write key 0x22EB kind 3 on the revived card's zone), 0x64 chain pop.
    criteria rel 1 {cid, set code, GY handler, word} + rel 2 {cid, named, hand-by-name handler, word} appended after
    rel 0; criteria_row_hook arm: cls3 -> [0x0229AAFC+0x7C] != 0 ? rel 2 : rel 1."""
    named: int
    set_code: int
    gy_crit: tuple[int, int]               # rel 1: (handler, word)
    hand_crit: tuple[int, int]             # rel 2: (handler, word)
    cond: int
    cost: int
    res: int
    phantoms: tuple[int, int, int]         # (cls3, criteria rel 1, criteria rel 2)
    kind: int = 2

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import criteria_row_hook as crh
        kind = self.kind
        PLAYER_BASE, PLAYER_STRIDE, PHASE_STATE = 0x0229AC94, 0xB3C, 0x0229AAFC
        GY_CAND, REVEAL = 0x021F03B5, 0x021EAAA1
        CHAIN_PUSH, CHAIN_POP, GENERIC_REVIVE, GET_TARGET, LOCATE = 0x021D28A5, 0x021D2965, 0x02204731, 0x02234965, 0x021A241D
        NUMBER_PICKER, CHOICE_STATE, RIDER_WRITE, LEVEL_KEY = 0x0219AE11, 0x0229DD94, 0x021C479D, 0x22EB
        TITLE, ITEM = 0x016E, 0x011B
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.turnlog_query(R0, cid, kind, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.insn("LDRB", "R1, [R5, #0x6]")
        b.insn("EOR", "R0, R1")
        b.ldr_const(6, PLAYER_BASE)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "side0")
        b.ldr_const(1, PLAYER_STRIDE)
        b.insn("ADD", "R6, R6, R1")
        b.label("side0")
        b.insn("LDR", "R4, [R6, #0xC]")
        b.ldr_const(1, 0x124)
        b.insn("ADD", "R6, R6, R1")
        b.insn("MOV", "R2, #0x0")
        b.ldr_const(3, self.named)
        b.label("loop")
        b.insn("CMP", "R2, R4")
        b.insn("BGE", "no")
        b.insn("LDR", "R0, [R6, #0x0]")
        b.insn("LSL", "R0, R0, #0x12")
        b.insn("LSR", "R0, R0, #0x12")
        b.insn("CMP", "R0, R3")
        b.insn("BEQ", "have")
        b.insn("ADD", "R6, #0x4")
        b.insn("ADD", "R2, #0x1")
        b.insn("B", "loop")
        b.label("have")
        b.call_addr(GY_CAND, R5, via=R4)
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        cond = b.assemble(self.cond, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(REVEAL, via=R2)
        b.insn("CMP", "R0, #0x1")
        b.insn("BNE", "out")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_post(R0, cid, kind, via=R4)
        b.insn("ADD", "R0, R5, #0x0")
        b.label("out")
        b.insn("POP", "{R4, R5, PC}")
        cost = b.assemble(self.cost, pad="nop")

        b = EffectBuilder()                 # r2/r3 are pushed only to reserve [sp] / [sp+4] for the callees' stack args
        b.insn("PUSH", "{R2, R3, R4, R5, R6, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.ldr_const(0, PHASE_STATE)
        b.insn("LDR", "R0, [R0, #0x70]")
        b.insn("CMP", "R0, #0x80")
        b.insn("BEQ", "p80")
        b.insn("CMP", "R0, #0x7F")
        b.insn("BEQ", "p7f")
        b.insn("CMP", "R0, #0x7E")
        b.insn("BEQ", "p7e")
        b.insn("CMP", "R0, #0x64")
        b.insn("BEQ", "p64")
        b.insn("B", "zero")
        b.label("p80")
        b.call_addr(CHAIN_PUSH, via=R3)
        b.call_addr(GENERIC_REVIVE, R4, 1, 2, via=R3)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "p64")
        b.insn("MOV", "R0, #0x7F")
        b.insn("B", "out")
        b.label("p64")
        b.call_addr(CHAIN_POP, via=R3)
        b.label("zero")
        b.insn("MOV", "R0, #0x0")
        b.label("out")
        b.insn("POP", "{R2, R3, R4, R5, R6, R7, PC}")
        b.label("p7f")
        b.call_addr(GET_TARGET, R4, 0, via=R3)
        b.call_addr(LOCATE, via=R3)
        b.insn("LSL", "R1, R0, #0x10")
        b.insn("LSR", "R1, R1, #0x18")
        b.insn("CMP", "R1, #0x5")
        b.insn("BGE", "done")
        b.insn("MOV", "R0, #0x1")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("MOV", "R0, #0x4")
        b.insn("STR", "R0, [SP, #0x4]")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.call_addr(NUMBER_PICKER, R0, R1, TITLE, ITEM, via=R5)
        b.insn("MOV", "R0, #0x7E")
        b.insn("B", "out")
        b.label("done")
        b.insn("MOV", "R0, #0x64")
        b.insn("B", "out")
        b.label("p7e")
        b.call_addr(GET_TARGET, R4, 0, via=R3)
        b.call_addr(LOCATE, via=R3)
        b.insn("LSL", "R7, R0, #0x10")
        b.insn("LSR", "R7, R7, #0x18")
        b.insn("CMP", "R7, #0x5")
        b.insn("BGE", "done")
        b.insn("LSL", "R6, R0, #0x18")
        b.insn("LSR", "R6, R6, #0x18")
        b.ldr_const(0, CHOICE_STATE)
        b.insn("LDR", "R0, [R0, #0x34]")
        b.insn("CMP", "R0, #0x1")
        b.insn("BGE", "lo_ok")
        b.insn("MOV", "R0, #0x1")
        b.label("lo_ok")
        b.insn("CMP", "R0, #0x4")
        b.insn("BLE", "hi_ok")
        b.insn("MOV", "R0, #0x4")
        b.label("hi_ok")
        b.insn("STR", "R0, [SP, #0x0]")
        b.call_addr(RIDER_WRITE, R6, R7, LEVEL_KEY, 3, via=R5)
        b.insn("B", "done")
        res = b.assemble(self.res, pad="nop")
        stubs = ((self.res, res, "C2 resolver"), (self.cond, cond, "C2 cond"), (self.cost, cost, "C2 cost"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        for a_ in (GY_CAND, REVEAL, CHAIN_PUSH, CHAIN_POP, GENERIC_REVIVE, GET_TARGET, LOCATE, NUMBER_PICKER,
                   RIDER_WRITE, _AS_OFFFIELD_PICKER, self.gy_crit[0], self.hand_crit[0]):
            assert a_ & 1, f"{a_:#x}: blx/bx to an even literal switches to ARM state -> freeze"
        assert any(a[0] == cid for a in crh.ARMS), "the row arm must be registered in criteria_row_hook"
        ph3, phc1, phc2 = self.phantoms
        row1, row2 = (cid, self.set_code) + self.gy_crit, (cid, self.named) + self.hand_crit

        def install(rom, view):
            row0s = [r for r in rows(view, CRITERIA) if r[0] == cid]
            assert len(row0s) >= 1, "criteria rel 0 must be inserted first"
            _append_criteria_row(view, cid, row1, phc1, row0s[:1])
            _append_criteria_row(view, cid, row2, phc2, row0s[:1] + [row1])
            crh.apply(view.buf)
            crh.install(rom, quiet=True)

        def check(c, rom, view):
            recs = rows(view, CRITERIA)
            ks = [r[0] for r in recs]
            mine = [r for r in recs if r[0] == cid]
            c.ok(ks == sorted(ks) and len(mine) == 3 and mine[1:] == [row1, row2]
                 and not any(p in ks for p in (phc1, phc2)),
                 "criteria rel 1 + rel 2 under the donor after rel 0, in order; phantoms dropped; sorted")
            crh.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)

        return Compiled(stubs,
                        (Row(CLS3, (cid, self.res | 1, 0, self.cond | 1, self.cost | 1, _AS_OFFFIELD_PICKER), ph3),),
                        installs=(install,), checks=(check,))



AMA = 0x1F7A        # "Assault Mode Activate"
GROUP = (0x1F47, 0x1F51, 0x1F52, 0x1F53, 0x1F54, 0x1F55, 0x1F56, 0x1F57, 0x1F70, 0x1F7A, 0x1F9B, 0x1FCA)

SPEC = card(
    0x1008,
    set_code_repointed_to_cave_list(
        setcode=0x6E, thunk=0x02024088, count_imm=0x0202408C, list_lit=0x02024090, stock_list=0x0209C5CA,
        stock_members=(0x250B, 0x250C, 0x250D, 0x2532), sibling_lit=0x020240D0,
        group=GROUP, group_addr=ov5_cave.CAVE_PSI_GROUP),
    normal_or_special_summoned_search_group_once_per_turn(
        add_to_hand=0x02207EF5, have_target=0x021F0821, tag=0x021E51E5, template=0x21F5,   # Machina Gearframe
        crit=(0x6E, 0x0223CAF5, 0x0000000E),                                                # Deck->hand, any card type
        cond=ov5_cave.CAVE_PSI_COND, slot4=ov5_cave.CAVE_PSI_SLOT4,
        phantoms=(0x0E7F, 0x167C, 0x0E38, 0x0E75)),
    reveal_hand_card_revive_gy_monster_with_level_rider(
        named=AMA, set_code=0x6E, gy_crit=(0x0223C9ED, 0x00010002), hand_crit=(0x02241769, 0x0000000E),
        cond=ov5_cave.CAVE_PSI_C2COND, cost=ov5_cave.CAVE_PSI_C2COST, res=ov5_cave.CAVE_PSI_C2RES,
        phantoms=(0x0E40, 0x0E40, 0x0E3A)))

PROPS = card_props("DARK", "Psychic", level=1, atk=400, defense=300, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_psi_reflector.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
