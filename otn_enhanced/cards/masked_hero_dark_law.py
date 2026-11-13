"""Masked HERO Dark Law (DARK / Warrior / Fusion Effect / Level 6 / 2400 / 1800) on Aqua Dragon 0x1160.

    Must be Special Summoned by "Mask Change". Any card sent to your opponent's GY is banished instead. Once per turn,
    if your opponent adds a card(s) from their Deck to their hand (except during the Draw Phase or the Damage Step):
    You can banish 1 random card from your opponent's hand.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS0, CLS1, CLS2, CLS3, Compiled, Row, _SM_STOCK_SRC, _timing_arms_check, _timing_arms_install
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass
import ndspy.rom
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class masked_hero_member_with_restricted_fusion_class:
    """'Must be Special Summoned by "Mask Change".' for a Fusion donor: Mask Change's criteria predicate is has_set_code
    0x6B "Masked HERO" + attribute, nothing per-cid, so the donor needs exactly what Goka 0x236B has.
      A  Masked HERO list 0x0209C572 [Goka, Vapor] is packed, so it moves back one slot to 0x0209C570 = [cid, Goka,
         Vapor] (count 3); BOTH readers move: the set thunk (literal / count `movs r2,#N`) and the HERO composite.
      B  0x0209C570 was the 1-entry "Nitro" list: its 16-byte thunk becomes a direct compare returning the same 1/0 the
         bsearch did, so Nitro Warrior keeps its archetype (the thunk's only reference is the has_set_code table).
      C  Fusion restriction class 5 (Goka/Vapor: not Poly-summonable, revive-limited): class 3 of the classifier
         0x02023228 is an all-phantom list, so its leaf `movs r0,#3` is retagged `movs r0,#5` and a phantom is swapped for
         the donor (still sorted).
      D  the donor's fusion recipe materials -> 0x3FFF (no planner builds it)."""
    recipe_row: int
    recipe_stock: tuple
    class3_phantom: int

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.common import ARM9_BASE
        GOKA, VAPOR, NITRO = 0x236B, 0x236D, 0x1E35
        OLD, NEW = 0x0209C572, 0x0209C570
        LITS, CNTS = (0x020239EC, 0x02024060), (0x020239B0, 0x0202405C)
        THUNK = 0x02023BD8
        nitro_stock = bytes.fromhex("0149024b01221847") + struct.pack("<II", NEW, 0x02022E15)
        nitro_new = bytes.fromhex("0249" "401a" "4142" "4841" "7047" "c046") + struct.pack("<I", NITRO)
        C3_LIST, C3_LIT, C3_LEAF = 0x0209BA18, 0x020232A8, 0x02023282
        c3_stock = (0x0EA1, 0x0EA2, self.class3_phantom, 0x1C5F)
        c3_new = (0x0EA1, 0x0EA2, cid, 0x1C5F)
        u16 = lambda d, a: struct.unpack_from("<H", d, a - ARM9_BASE)[0]
        u32 = lambda d, a: struct.unpack_from("<I", d, a - ARM9_BASE)[0]
        dead = (cid, 0x3FFF, 0x3FFF, 0x3FFF)

        def install(rom, view):
            if tuple(view.unpack(self.recipe_row, "<4H")) != dead:
                assert tuple(view.unpack(self.recipe_row, "<4H")) == self.recipe_stock, "recipe row not stock"
                view.pack(self.recipe_row, "<4H", *dead)
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)
            if bytes(d[THUNK - ARM9_BASE:THUNK - ARM9_BASE + 16]) == nitro_new:
                return
            for a in LITS:
                assert u32(d, a) == OLD, f"Masked HERO literal @{a:#x} moved"
            for a in CNTS:
                assert u16(d, a) == 0x2202, f"count @{a:#x} is not movs r2,#2"
            assert [u16(d, OLD + 2 * i) for i in range(2)] == [GOKA, VAPOR], "Masked list not stock"
            assert u16(d, NEW) == NITRO, "Nitro list slot not stock"
            assert bytes(d[THUNK - ARM9_BASE:THUNK - ARM9_BASE + 16]) == nitro_stock, "Nitro thunk not stock"
            assert u32(d, C3_LIT) == C3_LIST and u16(d, C3_LEAF) == 0x2003, "class-3 arm moved"
            assert tuple(u16(d, C3_LIST + 2 * i) for i in range(4)) == c3_stock, "class-3 list not stock"
            d[THUNK - ARM9_BASE:THUNK - ARM9_BASE + 16] = nitro_new
            struct.pack_into("<3H", d, NEW - ARM9_BASE, cid, GOKA, VAPOR)
            for a in LITS:
                struct.pack_into("<I", d, a - ARM9_BASE, NEW)
            for a in CNTS:
                struct.pack_into("<H", d, a - ARM9_BASE, 0x2203)
            struct.pack_into("<4H", d, C3_LIST - ARM9_BASE, *c3_new)
            struct.pack_into("<H", d, C3_LEAF - ARM9_BASE, 0x2005)
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def check(c, rom, view):
            from otn_enhanced.asm import effect_verify
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytes(sec.data)
            srom = ndspy.rom.NintendoDSRom.fromFile(_SM_STOCK_SRC)
            _, ssec = ov5_cave._arm9_main(srom)
            s = bytes(ssec.data)
            bsearch = lambda dd, base, n, k: k in [struct.unpack_from("<h", dd, base - ARM9_BASE + 2 * i)[0] for i in range(n)]

            def member(dd, thunk, k):
                raw = bytes(dd[thunk - ARM9_BASE:thunk - ARM9_BASE + 16])
                if raw == nitro_new:
                    return k == NITRO
                assert raw[0:2] == b"\x01\x49" and raw[2:4] == b"\x02\x4b" and raw[5] == 0x22, f"thunk {thunk:#x} shape"
                return bsearch(dd, struct.unpack_from("<I", raw, 8)[0], raw[4], k)

            def fusion_class(dd, k):
                for lit, cnt_at, leaf in ((0x02023298, 0x0202322C, 0x02023238), (0x0202329C, 0x02023240, 0x0202324A),
                                          (0x020232A0, 0x02023252, 0x0202325E), (0x020232A4, 0x02023266, 0x02023270),
                                          (C3_LIT, None, C3_LEAF)):
                    n = 4 if cnt_at is None else u16(dd, cnt_at) & 0xFF
                    if bsearch(dd, u32(dd, lit), n, k):
                        return u16(dd, leaf) & 0xFF
                return None

            c.eq(bytes(d[THUNK - ARM9_BASE:THUNK - ARM9_BASE + 16]), nitro_new, f"Nitro thunk {THUNK:#x} is the direct compare")
            effect_verify.assert_thumb1_only(nitro_new[:12], THUNK)
            c.ok(all(u32(d, a) == NEW for a in LITS) and all(u16(d, a) == 0x2203 for a in CNTS),
                 "both Masked HERO readers -> 0x0209C570, count 3")
            lst = [u16(d, NEW + 2 * i) for i in range(3)]
            c.ok(lst == sorted(lst) == [cid, GOKA, VAPOR], f"Masked list = {[hex(x) for x in lst]}")
            c.ok(u16(d, C3_LEAF) == 0x2005 and u32(d, C3_LIT) == C3_LIST, "class-3 arm returns 5")
            c3 = tuple(u16(d, C3_LIST + 2 * i) for i in range(4))
            c.ok(c3 == c3_new and list(c3) == sorted(c3), f"class-3 list = {[hex(x) for x in c3]}")
            diffs = {"nitro": [], "masked": [], "hero": [], "class": []}
            for k in range(0x4000):
                if member(s, THUNK, k) != member(d, THUNK, k):
                    diffs["nitro"].append(k)
                if member(s, 0x02024058, k) != member(d, 0x02024058, k):
                    diffs["masked"].append(k)
                if (bsearch(s, u32(s, 0x020239EC), u16(s, 0x020239B0) & 0xFF, k)
                        != bsearch(d, u32(d, 0x020239EC), u16(d, 0x020239B0) & 0xFF, k)):
                    diffs["hero"].append(k)
                if fusion_class(s, k) != fusion_class(d, k):
                    diffs["class"].append(k)
            c.ok(diffs["nitro"] == [] and member(d, THUNK, NITRO), "set 0x35 membership identical to stock (Nitro Warrior kept)")
            c.eq(diffs["masked"], [cid], "Masked HERO: only the donor joins")
            c.eq(diffs["hero"], [cid], "HERO composite arm: only the donor joins")
            c.ok(set(diffs["class"]) == {cid, 0x0EA1, 0x0EA2, self.class3_phantom, 0x1C5F}
                 and fusion_class(d, cid) == 5 == fusion_class(d, GOKA) and fusion_class(d, VAPOR) == 5,
                 f"fusion class: donor -> 5 like Goka/Vapor; only the 4 class-3 phantoms else ({[hex(x) for x in diffs['class']]})")
            c.eq(tuple(view.unpack(self.recipe_row, "<4H")), dead, "recipe materials dead")

        return Compiled(installs=(install,), checks=(check,))


@dataclass(frozen=True)
class cards_sent_to_opponents_graveyard_are_banished_instead:
    """'Any card sent to your opponent's GY is banished instead.' The GY->banished replacement is the ov3 field scan
    0x021BA82C (Macro Cosmos / Banishers / Dimensional Fissure), one 16-bit half per player P; bit 4 of P's half = "P's own
    cards bound for the GY are banished" (read by decision 0x021BA94C, which every GY move consults, and by the can-go-to-GY
    check 0x021BA910). Its only arm tests a phantom face-up on P's field: that arm now tests the donor on P's OPPONENT's
    field (literal -> donor, `adds r0,r4,#0` -> `subs r0,r7,r4`, r7 == 1 all loop)."""
    lit: int
    side: int
    lit_stock: int

    def compile(self, view, cid) -> Compiled:
        stock, new = 0x1C20, 0x1B38

        def install(rom, view):
            cur = (view.u32(self.lit), view.u16(self.side))
            if cur == (cid, new):
                return
            assert cur == (self.lit_stock, stock), f"scan arm not stock ({cur[0]:#x}, {cur[1]:#06x})"
            view.pack(self.lit, "<I", cid)
            view.pack(self.side, "<H", new)

        def check(c, rom, view):
            c.ok(view.u32(self.lit) == cid and view.u16(self.side) == new, "scan bit-4 arm = the donor on the opponent's field")
            assert_thumb1_only(struct.pack("<H", new), self.side)
            c.eq(view.blob(0x021BA82C, 0x1E), bytes.fromhex("feb52b48002600900d3800902848012101900c300190301c071c00240f43"),
                 "arm context stock (r7 := 1 ...)")
            c.eq(view.blob(0x021BA8B4, 4) + view.blob(0x021BA8BA, 2), bytes.fromhex("00220c49") + bytes.fromhex("d243"),
                 "arm context stock (movs r2,#0; ldr r1,=lit; mvns r2,r2)")

        return Compiled(installs=(install,), checks=(check,))


@dataclass(frozen=True)
class opponent_adds_from_deck_banish_random_hand_card_once_per_turn:
    """'Once per turn, if your opponent adds a card(s) from their Deck to their hand (except during the Draw Phase or the
    Damage Step): You can banish 1 random card from your opponent's hand.' Draws (event 0x1B) and Deck->hand adds (0x1C)
    reach a FIELD monster only through the cid-keyed poster 0x021D3438(side, cid, code, arg).
      cls1 {RES, 0, COND, SLOT4, 0} over phantom 0x1AC7's dead row; the draw handler's phantom arm (literal -> donor,
      bl -> S_DRAW, which clears the word's low 9 bits so the trigger never misses its timing, then posts); the Deck->hand
      mover's move-log bl -> S_ADD (the log call, then, unless the mover's own no-post mode, the post). S_DRAW / S_ADD live
      in that phantom's DEAD resolver body in ov3 (both hosts run in puzzles). ov5: COND (code 0x1B/0x1C, phase != Draw,
      opponent hand non-empty, per-copy rider gate), SLOT4 ('You can', Yes stamps at ACTIVATION), RES (0x80 random pick of
      the opponent's hand, 0x7F face-up banish). Shared timing_class_hook arm. The Damage Step exclusion is NOT built."""
    res: int
    cond: int
    slot4: int
    host: int                  # S_DRAW; S_ADD follows, 4-aligned
    host_end: int
    phantom: int               # cls1 row + the dead resolver body's cid

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import timing_class_hook as tch
        POSTER, MOVE_LOG, MODE_BLOCK = 0x021D3439, 0x022391CD, 0x0229C294
        DRAW_LIT, DRAW_BL, ADD_BL = 0x021D12EC, 0x021D1288, 0x021C743E
        DRAW_BL_STOCK, ADD_BL_STOCK = 0x021D3438, 0x022391CC
        PLAYER_BASE, PLAYER_STRIDE, PHASE_BLOCK, RES_PHASE, PICK_BLOCK = 0x0229AC94, 0xB3C, 0x0229DD14, 0x0229AAFC, 0x0229DE94
        OPT_GATE, OPT_STAMP, TAG, CAN_BANISH, RANDOM_PICK, BANISH_FROM = 0x021F01C1, 0x021E5061, 0x021E51E5, 0x021BABE9, 0x022599F9, 0x021C6E4D
        stock_head = bytes.fromhex("f8b5051cea78ae78")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("LSR", "R3, R3, #0x9")
        b.insn("LSL", "R3, R3, #0x9")
        b.call_addr(POSTER, via=R4)
        b.insn("POP", "{R4, PC}")
        s_draw = b.assemble(self.host, pad="nop")
        s_add_addr = self.host + ((len(s_draw) + 3) & ~3)
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.call_addr(MOVE_LOG, via=R4)
        b.ldr_const(0, MODE_BLOCK)
        b.insn("LDR", "R0, [R0, #0x78]")
        b.insn("LSL", "R0, R0, #0x1F")
        b.insn("BNE", "done")
        b.insn("MOV", "R0, #0x1")
        b.insn("SUB", "R0, R0, R5")
        b.ldr_const(1, cid)
        b.insn("MOV", "R2, #0x1C")
        b.insn("LSR", "R3, R7, #0x9")
        b.insn("LSL", "R3, R3, #0x9")
        b.call_addr(POSTER, via=R4)
        b.label("done")
        b.insn("POP", "{R4, PC}")
        s_add = b.assemble(s_add_addr, pad="nop")
        assert s_add_addr + len(s_add) <= self.host_end, "ov3 stubs overrun the dead body"

        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x4]")
        b.insn("CMP", "R0, #0x1B")
        b.insn("BEQ", "code_ok")
        b.insn("CMP", "R0, #0x1C")
        b.insn("BNE", "no")
        b.label("code_ok")
        b.ldr_const(0, PHASE_BLOCK)
        b.insn("LDR", "R0, [R0, #0x48]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("MOV", "R1, #0x1")
        b.insn("EOR", "R0, R1")
        b.insn("AND", "R0, R1")
        b.ldr_const(1, PLAYER_BASE)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "base0")
        b.ldr_const(2, PLAYER_STRIDE)
        b.insn("ADD", "R1, R1, R2")
        b.label("base0")
        b.insn("LDR", "R1, [R1, #0xC]")
        b.insn("CMP", "R1, #0x0")
        b.insn("BEQ", "no")
        b.call_addr(OPT_GATE, R4, via=R1)
        b.insn("POP", "{R4, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        cond = b.assemble(self.cond, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(TAG, via=R2)
        b.insn("CMP", "R0, #0x1")
        b.insn("BNE", "out")
        b.insn("ADD", "R5, R0, #0x0")
        b.call_addr(OPT_STAMP, R4, via=R2)
        b.insn("ADD", "R0, R5, #0x0")
        b.label("out")
        b.insn("POP", "{R4, R5, PC}")
        slot4 = b.assemble(self.slot4, pad="nop")

        b = EffectBuilder()                  # r4 = desc, r5 = opponent, r6 = opponent's player block
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R5, [R4, #0x2]")
        b.insn("MOV", "R0, #0x1")
        b.insn("EOR", "R5, R0")
        b.insn("AND", "R5, R0")
        b.ldr_const(6, PLAYER_BASE)
        b.insn("CMP", "R5, #0x0")
        b.insn("BEQ", "base0")
        b.ldr_const(0, PLAYER_STRIDE)
        b.insn("ADD", "R6, R6, R0")
        b.label("base0")
        b.ldr_const(0, RES_PHASE)
        b.insn("LDR", "R0, [R0, #0x70]")
        b.insn("CMP", "R0, #0x7F")
        b.insn("BEQ", "banish")
        b.insn("CMP", "R0, #0x80")
        b.insn("BNE", "zero")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call_addr(CAN_BANISH, via=R1)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "zero")
        b.insn("LDR", "R0, [R6, #0xC]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "zero")
        b.call_addr(RANDOM_PICK, R5, 0, via=R2)
        b.insn("MOV", "R0, #0x7F")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("banish")
        b.ldr_const(1, PICK_BLOCK)
        b.insn("LDRH", "R1, [R1, #0x6]")
        b.insn("LSL", "R1, R1, #0x2")
        b.insn("ADD", "R1, R6, R1")
        b.ldr_const(0, 0x124)
        b.insn("ADD", "R1, R1, R0")
        b.call_addr(BANISH_FROM, R5, R1, 1, via=R3)
        b.label("zero")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        res = b.assemble(self.res, pad="nop")
        stubs = ((self.cond, cond, "C3 cond"), (self.slot4, slot4, "C3 slot4"), (self.res, res, "C3 resolver"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        for blob, addr in ((s_draw, self.host), (s_add, s_add_addr)):
            assert_thumb1_only(blob, addr)
        for a_ in (POSTER, MOVE_LOG, OPT_GATE, OPT_STAMP, TAG, CAN_BANISH, RANDOM_PICK, BANISH_FROM):
            assert a_ & 1, f"{a_:#x}: blx to an even literal switches to ARM state -> freeze"
        ov3_blobs = ((self.host, s_draw), (s_add_addr, s_add))

        def install(rom, view):
            _timing_arms_install(rom, view)
            if view.u32(DRAW_LIT) == cid:
                return
            assert view.u32(DRAW_LIT) == self.phantom, "draw literal moved"
            assert view.blob(DRAW_BL, 4) == common_bl(DRAW_BL, DRAW_BL_STOCK), "draw bl"
            assert view.blob(ADD_BL, 4) == common_bl(ADD_BL, ADD_BL_STOCK), "add bl"
            assert view.blob(self.host, 8) == stock_head, "dead resolver body not stock"
            for a, blob in ov3_blobs:
                view.write(a, blob)
            view.pack(DRAW_LIT, "<I", cid)
            view.write(DRAW_BL, common_bl(DRAW_BL, self.host))
            view.write(ADD_BL, common_bl(ADD_BL, s_add_addr))

        def check(c, rom, view):
            _timing_arms_check(c, rom, view)
            c.ok(view.u32(DRAW_LIT) == cid and view.blob(DRAW_BL, 4) == common_bl(DRAW_BL, self.host),
                 "draw poster: literal -> donor, bl -> S_DRAW")
            c.eq(view.blob(ADD_BL, 4), common_bl(ADD_BL, s_add_addr), "Deck->hand log bl -> S_ADD")
            for a, blob in ov3_blobs:
                c.eq(view.blob(a, len(blob)), blob, f"ov3 stub @{a:#x} present")
            dead = [(t.label, i) for t in (CLS0, CLS1, CLS2, CLS3) for i in range(t.count)
                    for f in struct.unpack_from("<5I", view.buf, t.addr(i) - view.base + 4)
                    if self.host <= (f & ~1) < self.host_end]
            c.eq(dead, [], "no cls record points into the reclaimed ov3 body")

        return Compiled(stubs,
                        (Row(CLS1, (cid, 0, self.res | 1, 0, self.cond | 1, self.slot4 | 1, 0), self.phantom),),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x1160,
    masked_hero_member_with_restricted_fusion_class(
        recipe_row=0x02270B94 + 28 * 8, recipe_stock=(0x1160, 0x1201, 0x1218, 0x112F), class3_phantom=0x1C55),
    cards_sent_to_opponents_graveyard_are_banished_instead(lit=0x021BA8E8, side=0x021BA8B8, lit_stock=0x1444),
    opponent_adds_from_deck_banish_random_hand_card_once_per_turn(
        res=ov5_cave.CAVE_DL_RES, cond=ov5_cave.CAVE_DL_COND, slot4=ov5_cave.CAVE_DL_SLOT4,
        host=0x02223450, host_end=0x02223504, phantom=0x1AC7))

PROPS = card_props("DARK", "Warrior", level=6, atk=2400, defense=1800, card_type="Fusion Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_dark_law.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
