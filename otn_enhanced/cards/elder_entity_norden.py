"""Elder Entity Norden (Fusion / WATER / Fairy / Level 4 / 2000 / 2200) on Bickuribox 0x1127.

    "1 Synchro Monster + 1 Synchro Monster
     When this card is Special Summoned: You can target 1 Level 4 or lower monster in your Graveyard; Special
     Summon it, but its effects are negated, also banish it when this card leaves the field."
"""
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS1, CRITERIA, Compiled, LIST_CODE9, Row, _FUSION_RECIPE_A
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows


_MATERIAL_JT_BASE, _MATERIAL_JT_ORIGIN = 0x02231B54, 0x02231B56


_IS_SYNCHRO_TAIL = 0x02231DCC


_IS_SYNCHRO_TAIL_BYTES = bytes.fromhex("281cf1f53ff9002800d00de0")   # adds r0,r5 ; bl is_synchro ; cmp ; beq ; b accept


_FUSION_RECIPE_A_N = 161


@dataclass(frozen=True)
class fusion_materials_any_synchro:
    """'1 Synchro Monster + 1 Synchro Monster' (no Xyz in this game). The fusion material predicate 0x02231A74
    dispatches category codes 23..50 through a halfword jump table; there is no native 'any Synchro' code (50 is
    'non-Tuner Synchro'), but its leaf's tail 0x02231DCC is a self-contained is_synchro test, so code `code`'s
    jump entry is pointed at it (Synchro Tuners accepted, unlike 50) and the donor's recipe row A[row] is rewritten
    to {code, code}. Code 46's only other user is a phantom's recipe row. Pure data, ov3, puzzle-safe."""
    code: int
    stock_entry: int          # the jump entry's stock halfword
    row: int
    stock_recipe: tuple       # (cid, mat1, mat2, 0)

    def compile(self, view, cid) -> Compiled:
        entry_addr = _MATERIAL_JT_BASE + (self.code - 23) * 2
        new_entry = _IS_SYNCHRO_TAIL - _MATERIAL_JT_ORIGIN
        row_addr = _FUSION_RECIPE_A + self.row * 8
        new_row = (cid, self.code, self.code, 0)

        def install(rom, view):
            assert view.blob(_IS_SYNCHRO_TAIL, 12) == _IS_SYNCHRO_TAIL_BYTES, "is_synchro tail 0x02231DCC is not stock"
            jt = view.u16(entry_addr)
            if jt != new_entry:
                assert jt == self.stock_entry, f"jump entry for code {self.code} is {jt:#x}, expected {self.stock_entry:#x}"
                view.pack(entry_addr, "<H", new_entry)
            cur = tuple(view.unpack(row_addr, "<4H"))
            if cur != new_row:
                assert cur == self.stock_recipe, f"recipe A[{self.row}] = {[hex(v) for v in cur]}"
                view.pack(row_addr, "<4H", *new_row)

        def check(c, rom, view):
            leaf = _MATERIAL_JT_ORIGIN + view.unpack(entry_addr, "<h")[0]
            c.eq(leaf, _IS_SYNCHRO_TAIL, f"material code {self.code} dispatches to the is_synchro tail")
            recs = [view.unpack(_FUSION_RECIPE_A + i * 8, "<4H") for i in range(_FUSION_RECIPE_A_N)]
            c.eq(tuple(recs[self.row]), new_row, f"recipe A[{self.row}] = {{Synchro, Synchro}}")
            c.ok([r[0] for r in recs] == sorted(r[0] for r in recs), "recipe table A still sorted")

        return Compiled(installs=(install,), checks=(check,))


_BSEARCH_ODD = 0x02022E15


_NEG_HOST_STOCK = bytes.fromhex("01d00020f8bdaff7c1fb002801d10020f8bda9780120ea78")


_DEST_HOST_STOCK = bytes.fromhex("01401248144b4843142151431818085a002801d00020f8bd")


@dataclass(frozen=True)
class revive_from_gy_negated_banished_when_this_leaves:
    """'When this card is Special Summoned: You can target 1 Level N or lower monster in your GY; Special Summon it,
    but its effects are negated, also banish it when this card leaves the field.'
      D  code-9 list: donor in, a phantom out (plain 'when this card is Special Summoned').
      E/H cls1 = Doomkaiser Dragon's record verbatim (the shared 'SS from GY + link' resolver 0x02207529 whose phase
         0x80 mode switch gives every unlisted cid mode 2, player picks the position; 0x7F attaches the link) with
         the cid swapped, over a phantom; all other literals native -> native timing class, no turn log.
      F  criteria row = Junk Synchron's with the level byte swapped.
      G  'effects negated' = Tour Guide's mechanism: the SS commit attaches {key = SOURCE cid, kind 3} iff the source is
         in list 0x0228F750, and the reader honours a key iff it is in 0x0226FAB4. BOTH LISTS ARE FULL, so one ov3
         stub 'r0 == cid ? 1 : tail-call bsearch' and both searches' bls go to it (write @0x02268074, read
         @0x021EE418). Host = phantom 0x1AC7's dead body (DEPENDS on masked_hero_dark_law: its cls1 drop makes it dead).
      I  whether the source's leave cleans up = list 0x0226E940 (FULL): its sole search bl @0x021CB3BC -> the stub.
      J  where the linked monster goes = [sp,#0xA8]; bl @0x021CB514 over the switch's shared tail -> a stub that
         replays the tail then, for the donor, stores 0x0F (banished). NAST's own destination hook is untouched."""
    template_cls1: tuple          # Junk Synchron's cls1 record (asserted)
    link_cls1: tuple              # Doomkaiser Dragon's cls1 record (asserted)
    template_crit: tuple          # Junk Synchron's criteria row (asserted)
    crit_word: int                # donor's criteria word
    phantoms: tuple[int, int, int]    # (code-9 list, cls1, criteria)
    neg_stub: int                 # ov3
    dest_stub: int                # ov3

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects.timing_class_hook import _bl
        ph9, ph1, phc = self.phantoms
        assert self.template_cls1 in rows(view, CLS1), "Junk Synchron's cls1 template changed"
        assert self.link_cls1 in rows(view, CLS1), "Doomkaiser's cls1 template changed"
        assert self.template_crit in rows(view, CRITERIA), "Junk Synchron's criteria template changed"
        assert self.template_cls1[3:] == self.link_cls1[3:], "the two cls1 templates differ only in the resolver"
        b = EffectBuilder()
        b.ldr_const(3, cid)
        b.insn("CMP", "R0, R3")
        b.insn("BEQ", "hit")
        b.ldr_const(3, _BSEARCH_ODD)
        b.insn("BX", "R3")
        b.label("hit")
        b.insn("MOV", "R0, #0x1")
        b.insn("BX", "LR")
        nb = b.assemble(self.neg_stub, pad="nop")
        b = EffectBuilder()
        b.insn("MOV", "R0, #0x2")
        b.insn("STR", "R0, [SP, #0xAC]")
        b.ldr_const(0, cid)
        b.insn("CMP", "R4, R0")
        b.insn("BNE", "out")
        b.insn("MOV", "R0, #0xF")
        b.insn("STR", "R0, [SP, #0xA8]")
        b.label("out")
        b.insn("BX", "LR")
        db = b.assemble(self.dest_stub, pad="nop")
        for blob, addr in ((nb, self.neg_stub), (db, self.dest_stub)):
            assert_thumb1_only(blob, addr)
        assert len(nb) <= 24 and len(db) <= 24 and self.dest_stub == self.neg_stub + 24
        sites = ((0x02268074, 0x02268114, 0x0228F750), (0x021EE418, 0x021EE4C8, 0x0226FAB4), (0x021CB3BC, 0x021CB634, 0x0226E940))
        tail_site, tail_native = 0x021CB514, bytes.fromhex("02202b90")

        def install(rom, view):
            for blob, addr, stock in ((nb, self.neg_stub, _NEG_HOST_STOCK), (db, self.dest_stub, _DEST_HOST_STOCK)):
                host = view.blob(addr, len(blob))
                if host != blob:
                    assert host == stock[:len(blob)], f"host {addr:#x} is not 0x1AC7's stock dead body"
                    view.write(addr, blob)
            for site, lit, lst in sites:
                assert view.u32(lit) == lst, f"{site:#x}'s list literal moved"
                cur = view.blob(site, 4)
                if cur != _bl(site, self.neg_stub):
                    assert cur == _bl(site, _BSEARCH_ODD & ~1), f"{site:#x} is not the native bl bsearch"
                    view.write(site, _bl(site, self.neg_stub))
            cur = view.blob(tail_site, 4)
            if cur != _bl(tail_site, self.dest_stub):
                assert cur == tail_native, f"{tail_site:#x} is not the native shared tail"
                view.write(tail_site, _bl(tail_site, self.dest_stub))

        def check(c, rom, view):
            from otn_enhanced.asm import effect_verify
            c.eq(view.blob(self.neg_stub, len(nb)), nb, "negate stub present in ov3")
            c.eq(view.blob(self.dest_stub, len(db)), db, "destination stub present in ov3")
            for site, lit, lst in sites:
                # Obedience Schooled fronts the READ site with a pre-check that tail-calls the stub.
                c.ok(code_reaches(rom, site, self.neg_stub), f"bl @{site:#x} reaches the membership stub")
            c.eq(view.blob(tail_site, 4), _bl(tail_site, self.dest_stub), "shared tail -> destination stub")

        link = (cid,) + self.link_cls1[1:]
        return Compiled((),     # the hosts are a phantom's dead (non-zero) body: written by `install`, not `stubs`
                        (Row(LIST_CODE9, (cid,), ph9), Row(CLS1, link, ph1),
                         Row(CRITERIA, (cid, 0xFFFF, self.template_crit[2], self.crit_word), phc)),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x1127,
    fusion_materials_any_synchro(code=46, stock_entry=0x0214, row=23, stock_recipe=(0x1127, 0x1005, 0x101E, 0)),
    revive_from_gy_negated_banished_when_this_leaves(
        template_cls1=(0x1E07, 0, 0x02207191, 0, 0x021F03B5, 0x021E51E5, 0x02235605),     # Junk Synchron
        link_cls1=(0x1EA8, 0, 0x02207529, 0, 0x021F03B5, 0x021E51E5, 0x02235605),         # Doomkaiser Dragon
        template_crit=(0x1E07, 0xFFFF, 0x0223C9D1, 0x00890002),
        crit_word=0x00910002,                                                             # Level 4 or lower
        phantoms=(0x1ABE, 0x0E4F, 0x0E7D),
        neg_stub=0x02223490, dest_stub=0x022234A8))

PROPS = card_props("WATER", "Fairy", level=4, atk=2000, defense=2200, card_type="Fusion Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_norden.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
