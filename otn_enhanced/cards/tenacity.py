"""Tenacity of the Monarchs (Normal Spell) on De-Spell 0x12EB.  Single-card TEST ROM, NOT SHIPPED, nothing here is in-game confirmed.

    "Reveal 1 monster in your hand with 2400 ATK & 1000 DEF, or 2800 ATK & 1000 DEF; add 1 "Monarch" Spell/Trap Card from your
     Deck to your hand, except "Tenacity of the Monarchs". You can only activate 1 "Tenacity of the Monarchs" per turn."

Clauses  C1 cost: reveal a 2400/1000 or 2800/1000 monster from the hand.  C2: add 1 "Monarch" Spell/Trap (not Tenacity) Deck -> hand.  C3: once per turn.
Design   (notes/monarch-megas-findings.md Session 22/22c)
  * cls0 {RES, 0, COND, COST, 0} rewritten in place over the donor's native record (Sacred Sword / Tenki shape).  De-Spell owns no criteria row.
  * TWO virtual criteria rows under the one cid (Predaplant Ophrys's pattern): H2 front on the criteria miss tail answers 0xFF61 (hand reveal)
    while the probe byte is up or the cost machine runs ([0x0229AAFC+0x7C] != 0), else 0xFF60 (Deck search); H3 front maps the index to the
    row copy in ov5.  0xFF60 = {aux 0x6D, Deck->hand 0x0223CAF5, 0x2E (any card type | except self)};  0xFF61 = {aux 0x6C, hand handler 0x0223CB39
    (set-code predicate, flags 0x10), 0x02 (monster)}.
  * "Monarch" = set code 0x6D, whose thunk literal is repointed to a 5-cid ov5 list (psi_reflector's recipe; 0x6F, which reads the stock list
    through its own literal, is untouched).  The reveal filter = set code 0x6C repointed to a 22-cid list of every monster printed 2400/1000 or
    2800/1000 (computed 2026-11-10 from the stock card data; the Mega Monarch donors are NOT in it, add them when both ship).
  * COND (menu only): OPT node absent, >= 1 revealable hand monster (direct hand scan, has_set_code 0x6C), >= 1 Monarch S/T in the Deck (native RotA test).
    COST: native reveal 0x021EAAA1 under the probe, then post the OPT node.  RES: native Deck -> hand 0x02207EF5.
UNPROVEN  that the set-code hand handler enumerates correctly with these arguments; that the native reveal UI offers exactly the listed cards;
          that the cost-state test separates the two rows during RES; the Monarch group holds the donors of Return / Restoration / Stormforth /
          March, which are only Monarch cards in a ROM that carries those patches.

    uv run python _build_tenacity.py
"""
from __future__ import annotations

import struct
import sys
from dataclasses import dataclass

from otn_enhanced import dsl
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import CLS0, Compiled, Edit, _COPY_EXEMPT_BX, _HAS_CANDIDATE, _DECK_TO_HAND, _TURNLOG_POST_ODD, _TURNLOG_QUERY_ODD
from otn_enhanced.effects import ov5_cave as O5
from otn_enhanced.effects.common import ARM9_BASE, bl as common_bl, ov3_bl_target

TEN = 0x12EB
CHAIN = "data/over_the_nexus/working/rom_all_patches.nds"
OUT = "data/over_the_nexus/working/rom_tenacity.nds"
NATIVE = (TEN, 0x0220AAA9, 0x021D88ED, 0, 0, 0x02234DA5)      # De-Spell's cls0 record, stock (read 2026-11-10; the chain does not touch it)

REVEAL, HAS_SET_CODE = 0x021EAAA1, 0x020240D9
PLAYER_BASE, PLAYER_STRIDE = 0x0229AC94, 0xB3C
DECK_SEARCH, HAND_SET = 0x0223CAF5, 0x0223CB39
H3_RESUME = 0x02243F71
for _v in (HAS_SET_CODE, REVEAL, DECK_SEARCH, HAND_SET, H3_RESUME, _HAS_CANDIDATE, _DECK_TO_HAND, _COPY_EXEMPT_BX):
    assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

MONARCH_SET, REVEAL_SET = 0x6D, 0x6C
IDX_DECK, IDX_HAND = 0xFF60, 0xFF61
WORD_ANY_EXCEPT_SELF, WORD_MONSTER = 0x0000002E, 0x00000002
COST_STATE = 0x0229AAFC            # + 0x7C = the cost machine's step
H2_SITE, H3_SITE = 0x02243F24, 0x02243F62

# "Monarch" Spell/Trap group: Tenacity + the donors of Return (Vengeful Bog Spirit), Restoration (Burning Spear), Stormforth (Tailor of the
# Fickle) and March (Kishido Spirit).  A donor is only a Monarch card in a ROM that carries its patch.
MONARCH = tuple(sorted((TEN, 0x14A1, 0x12EE, 0x1328, 0x15EC, 0x1633, 0x1923, 0x14C3, 0x1DCD, 0x135E, 0x0DE4, 0x10F3, 0x1800, 0x14CF, 0x249B, 0x12F6)))   # + Monarchic Perfection (donor Call of the Grave, 2026-11-12)   # + Escalation of the Monarchs (donor Enervating Mist)   # + The Monarchs Erupt (donor Respect Play)   # + Frost Blast (donor Double Snare) and The Monarchs Revolt (donor Short Circuit); the list slot is 0x30 B (24 u16) since 2026-11-11   # + The Monarchs Awaken (donor Disarmament) and Pantheism of the Monarchs (donor Des Croaking)
# every monster printed 2400/1000 or 2800/1000 in the stock card data (scratch/_reveal_list.py, 2026-11-10)
REVEAL_LIST = (0x1728, 0x174D, 0x17DB, 0x17E2, 0x1816, 0x182E, 0x185F, 0x190E, 0x1A1D, 0x1BCD, 0x1BEA, 0x1CA7, 0x1CFD, 0x1D5C,
               0x1D86, 0x1DEB, 0x1E12, 0x1FDC, 0x20D6, 0x20E0, 0x214D, 0x239A)
assert list(MONARCH) == sorted(set(MONARCH)) and list(REVEAL_LIST) == sorted(set(REVEAL_LIST))

S = {n: getattr(O5, f"CAVE_TN_{n}") for n in ("COND", "COST", "RES", "ROWS", "PROBE", "H2", "H3", "MON", "REV")}
RESERVE = {"COND": 0x90, "COST": 0x50, "RES": 0x20, "ROWS": 0x20, "PROBE": 0x10, "H2": 0x50, "H3": 0x30, "MON": 0x30, "REV": 0x30}
ROWS_BLOB = b"".join(struct.pack("<HHII", *r) + bytes(4) for r in (
    (TEN, MONARCH_SET, DECK_SEARCH, WORD_ANY_EXCEPT_SELF),        # 0xFF60
    (TEN, REVEAL_SET, HAND_SET, WORD_MONSTER)))                   # 0xFF61
MON_BLOB = struct.pack(f"<{len(MONARCH)}H", *MONARCH).ljust(RESERVE["MON"], b"\0")
REV_BLOB = struct.pack(f"<{len(REVEAL_LIST)}H", *REVEAL_LIST).ljust(RESERVE["REV"], b"\0")

_DN = O5.dc_next()
H2_PREV, H3_PREV = _DN[O5.CAVE_TN_H2], _DN[O5.CAVE_TN_H3]


def _asm(b: EffectBuilder, slot: str) -> bytes:
    blob = b.assemble(S[slot], pad="nop")
    assert_thumb1_only(blob, S[slot])
    assert len(blob) <= RESERVE[slot], f"{slot}: {len(blob):#x} B > {RESERVE[slot]:#x}"
    return blob


def _probe(b: EffectBuilder, value: int) -> None:
    b.ldr_const(0, S["PROBE"])
    b.insn("MOV", f"R1, #{value}")
    b.insn("STRB", "R1, [R0, #0x0]")


def cond_stub() -> bytes:
    """Menu check only.  The hand scan is DIRECT (every hand card tested with has_set_code(cid, 0x6C)): a criteria-row probe tests ONE hand
    slot, which the first trace caught (count 0 whenever the monster was not in slot 0)."""
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("LDRB", "R5, [R4, #0x2]")
    b.insn("LDRB", "R0, [R4, #0x6]")
    b.insn("EOR", "R5, R0")
    b.insn("LDRB", "R0, [R4, #0x7]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "yes")                                   # not the menu check: nothing to test
    b.insn("ADD", "R0, R5, #0x0")                          # OPT node (kind 1) already posted this turn?
    b.insn("MOV", "R1, #0xB")
    b.ldr_const(2, TEN)
    b.insn("MOV", "R3, #0x1")
    b.ldr_const(6, _TURNLOG_QUERY_ODD)
    b.insn("BLX", "R6")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "no")
    b.ldr_const(6, PLAYER_BASE)                            # hand of side r5: count at +0xC, cards at +0x124
    b.insn("MOV", "R0, #0x1")
    b.insn("AND", "R0, R5")
    b.insn("BEQ", "s0")
    b.ldr_const(1, PLAYER_STRIDE)
    b.insn("ADD", "R6, R6, R1")
    b.label("s0")
    b.insn("LDR", "R7, [R6, #0xC]")
    b.ldr_const(1, 0x124)
    b.insn("ADD", "R6, R6, R1")
    b.label("loop")
    b.insn("CMP", "R7, #0x0")
    b.insn("BLE", "no")
    b.insn("LDR", "R0, [R6, #0x0]")
    b.insn("LSL", "R0, R0, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("MOV", f"R1, #0x{REVEAL_SET:X}")
    b.ldr_const(3, HAS_SET_CODE)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "found")
    b.insn("ADD", "R6, #0x4")
    b.insn("SUB", "R7, #0x1")
    b.insn("B", "loop")
    b.label("found")
    b.insn("ADD", "R0, R4, #0x0")                          # a Monarch Spell/Trap in the Deck: RotA's candidate test on the Deck row
    b.ldr_const(3, _HAS_CANDIDATE)
    b.insn("BLX", "R3")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    b.label("yes")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    b.label("no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return _asm(b, "COND")


def cost_stub() -> bytes:
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    _probe(b, 1)
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, REVEAL)
    b.insn("BLX", "R3")
    b.insn("ADD", "R5, R0, #0x0")
    _probe(b, 0)
    b.insn("CMP", "R5, #0x1")
    b.insn("BNE", "out")
    b.insn("ADD", "R0, R4, #0x0")
    b.ldr_const(3, _COPY_EXEMPT_BX)
    b.insn("BLX", "R3")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "out")
    b.insn("LDRB", "R0, [R4, #0x2]")
    b.insn("LDRB", "R1, [R4, #0x6]")
    b.insn("EOR", "R0, R1")
    b.ldr_const(1, TEN)
    b.insn("MOV", "R2, #0x1")
    b.insn("MOV", "R3, #0x0")
    b.ldr_const(6, _TURNLOG_POST_ODD)
    b.insn("BLX", "R6")
    b.label("out")
    b.insn("ADD", "R0, R5, #0x0")
    b.insn("POP", "{R4, R5, R6, PC}")
    return _asm(b, "COST")


def res_stub() -> bytes:
    b = EffectBuilder()
    b.insn("PUSH", "{R4, LR}")
    b.insn("MOV", "R1, #0x0")
    b.ldr_const(3, _DECK_TO_HAND)
    b.insn("BLX", "R3")
    b.insn("POP", "{R4, PC}")
    return _asm(b, "RES")


def h2_front() -> bytes:
    """criteria resolver miss tail (r5 = cid): Tenacity -> 0xFF61 while the probe is up or the cost machine runs, else 0xFF60, and pop the
    caller's frame; everyone else: BL onward (the chain ends in a front that pops)."""
    b = EffectBuilder()
    b.ldr_const(0, TEN)
    b.insn("CMP", "R5, R0")
    b.insn("BNE", "miss")
    b.ldr_const(0, S["PROBE"])
    b.insn("LDRB", "R0, [R0, #0x0]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "hand")
    b.ldr_const(0, COST_STATE)
    b.insn("LDR", "R0, [R0, #0x7C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "hand")
    b.ldr_const(0, IDX_DECK)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("hand")
    b.ldr_const(0, IDX_HAND)
    b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
    b.label("miss")
    b.bl(H2_PREV)
    return _asm(b, "H2")


def h3_front() -> bytes:
    """invoker row compute (r6 = index): 0xFF60..0xFF61 -> r0 = ROWS + 0x10 * (index - 0xFF60), r3 = [r0+4], resume 0x02243F70; else tail to the previous H3."""
    b = EffectBuilder()
    b.ldr_const(0, IDX_DECK)
    b.insn("SUB", "R0, R6, R0")
    b.insn("CMP", "R0, #0x2")
    b.insn("BCS", "prev")
    b.insn("LSL", "R0, R0, #0x4")
    b.ldr_const(3, S["ROWS"])
    b.insn("ADD", "R0, R0, R3")
    b.insn("LDR", "R3, [R0, #0x4]")
    b.ldr_const(6, H3_RESUME)
    b.insn("BX", "R6")
    b.label("prev")
    b.ldr_const(0, H3_PREV | 1)
    b.insn("BX", "R0")
    return _asm(b, "H3")


@dataclass(frozen=True)
class repointed_group:
    """A set code's thunk literal repointed to a longer sorted ov5 list and its `movs r2,#N` set (psi_reflector's recipe)."""
    setcode: int
    thunk: int
    stock_list: int
    stock_members: tuple
    group: tuple
    group_addr: int
    sibling_lit: int | None = None
    ptr_table: int = 0x0209D0D8

    @property
    def count_imm(self) -> int:
        return self.thunk + 4

    @property
    def list_lit(self) -> int:
        return self.thunk + 8

    def state(self, d: bytes):
        u32 = lambda a: struct.unpack_from("<I", d, a - ARM9_BASE)[0]
        return (u32(self.ptr_table + self.setcode * 4), u32(self.list_lit), struct.unpack_from("<H", d, self.count_imm - ARM9_BASE)[0],
                None if self.sibling_lit is None else u32(self.sibling_lit))

    def install(self, rom, view):
        mc, sec = O5._arm9_main(rom)
        d = bytearray(sec.data)
        slot, lit, imm, sib = self.state(bytes(d))
        n = len(self.group)
        assert slot == self.thunk | 1, f"has_set_code[{self.setcode:#x}] = {slot:#x}"
        if (lit, imm) == (self.group_addr, 0x2200 | n):
            return
        assert (lit, imm) == (self.stock_list, 0x2200 | len(self.stock_members)), \
            f"set code {self.setcode:#x} thunk not stock: lit {lit:#x} imm {imm:#x}"
        assert tuple(struct.unpack_from(f"<{len(self.stock_members)}H", d, self.stock_list - ARM9_BASE)) == self.stock_members, "stock list moved"
        struct.pack_into("<I", d, self.list_lit - ARM9_BASE, self.group_addr)
        struct.pack_into("<H", d, self.count_imm - ARM9_BASE, 0x2200 | n)
        sec.data = bytes(d)
        rom.arm9 = mc.save()

    def check(self, c, rom, view):
        mc, sec = O5._arm9_main(rom)
        slot, lit, imm, sib = self.state(bytes(sec.data))
        c.ok(slot == self.thunk | 1 and lit == self.group_addr and imm == 0x2200 | len(self.group),
             f"set code {self.setcode:#x} -> {self.group_addr:#x} x {len(self.group)}")
        c.ok(tuple(struct.unpack_from(f"<{len(self.stock_members)}H", sec.data, self.stock_list - ARM9_BASE)) == self.stock_members,
             f"set code {self.setcode:#x}: the stock list bytes are untouched (a sibling may read them)")


GROUPS = (
    repointed_group(MONARCH_SET, 0x02024078, 0x0209C6C6, (0x0E4C, 0x0E51, 0x0E56, 0x2430, 0x2431, 0x2432, 0x2531), MONARCH, S["MON"], sibling_lit=0x020240CC),
    repointed_group(REVEAL_SET, 0x02024068, 0x0209C586, (0x2374, 0x23EC), REVEAL_LIST, S["REV"]),
)


def _front_at(view, site: int, prev: int, mine: int, what: str) -> None:
    cur = ov3_bl_target(view.buf, site)
    assert cur in (prev, mine), f"{what} @{site:#x} calls {cur:#x}, expected {prev:#x} (or ours {mine:#x})"
    view.write(site, common_bl(site, mine))


def _reaches(view, site: int, slot: str) -> bool:
    t, nxt = ov3_bl_target(view.buf, site), O5.dc_next()          # later owners' fronts may sit ahead of ours
    while t != S[slot] and t in nxt:
        t = nxt[t]
    return t == S[slot]


class tenacity:
    cid: int = TEN

    def compile(self, view=None) -> Compiled:
        stubs = ((S["COND"], cond_stub(), "cond"), (S["COST"], cost_stub(), "cost: reveal + OPT"), (S["RES"], res_stub(), "res: Deck -> hand"),
                 (S["ROWS"], ROWS_BLOB, "virtual criteria rows 0xFF60/0xFF61"), (S["PROBE"], bytes(0x10), "DATA: hand-row probe byte (ships clear)"),
                 (S["H2"], h2_front(), "H2 front"), (S["H3"], h3_front(), "H3 front"),
                 (S["MON"], MON_BLOB, "Monarch set-code list"), (S["REV"], REV_BLOB, "reveal set-code list"))
        patched = (TEN, S["RES"] | 1, 0, S["COND"] | 1, S["COST"] | 1, 0)

        def install(rom, v):
            _front_at(v, H2_SITE, H2_PREV, S["H2"], "criteria miss tail")
            _front_at(v, H3_SITE, H3_PREV, S["H3"], "criteria row compute")
            for g in GROUPS:
                g.install(rom, v)

        def check(c, rom, v):
            for site, slot in ((H2_SITE, "H2"), (H3_SITE, "H3")):
                c.ok(_reaches(v, site, slot), f"bl @{site:#x} reaches the Tenacity {slot} front")
            c.eq(O5.read_cave(rom, S["ROWS"], len(ROWS_BLOB)), ROWS_BLOB, "virtual rows resident")
            c.eq(O5.read_cave(rom, S["PROBE"], 4), bytes(4), "probe byte ships clear")
            for g in GROUPS:
                g.check(c, rom, v)

        return Compiled(stubs, edits=(Edit(CLS0, TEN, NATIVE, patched),), installs=(install,), checks=(check,))


SPEC = tenacity()
main, verify = dsl.make(SPEC, None, out=OUT)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
