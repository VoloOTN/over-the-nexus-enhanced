"""Life Stream Dragon (EARTH / Dragon / Synchro Tuner / Level 8 / 2900 / 2400) on Steam Gyroid 0x18FA.

    "1 Tuner + "Power Tool Dragon"
     When this card is Synchro Summoned: You can make your LP become 4000. You take no effect damage.
     If this face-up card on the field would be destroyed, you can banish 1 Equip Spell Card from your Graveyard
     instead."
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_prop_copied_from_template, card_props, fusion_recipe_blanked, CLS1, CRITERIA, Compiled, Row
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
import ndspy.rom


def _bl_hooks(hooks):
    """(install, check) for 4-byte BL detours: (site, native bytes, cave, label); a site already detoured is left."""
    from otn_enhanced.effects import summon_trigger_hook as sth

    def install(rom, view):
        for site, native, cave, label in hooks:
            want = sth._bl(site, cave)
            cur = view.blob(site, 4)
            if cur != want:
                assert cur == native, f"{label} @{site:#x} is {cur.hex()} -- another patch owns it"
                view.write(site, want)

    def check(c, rom, view):
        for site, _native, cave, label in hooks:
            c.eq(view.blob(site, 4), sth._bl(site, cave), f"{label} @{site:#x} -> {cave:#x}")

    return install, check


@dataclass(frozen=True)
class set_code_slot_to_phantom:
    """The donor leaves an ARM9 set-code list by overwriting its OWN slot `index` with a phantom cid (sorted stays
    sorted by choice of phantom): e.g. Life Stream Dragon stops being a "roid" (KB setcode.roid_list_holds_steam_gyroid)."""
    base: int
    count: int
    index: int
    phantom: int

    def compile(self, view, cid) -> Compiled:
        def post(out):
            from otn_enhanced.effects import common
            rom = ndspy.rom.NintendoDSRom.fromFile(out)
            a9 = common.view(rom)
            lst = list(a9.unpack(self.base, f"<{self.count}H"))
            if lst[self.index] == self.phantom:
                return
            assert lst[self.index] == cid, f"set-code list slot {self.index} is {lst[self.index]:#x}"
            with common.arm9_edit(rom) as w:
                w.pack(self.base + 2 * self.index, "<H", self.phantom)
            rom.saveToFile(out)

        def check(c, rom, view):
            from otn_enhanced.effects import common
            lst = list(common.view(rom).unpack(self.base, f"<{self.count}H"))
            c.ok(cid not in lst and lst[self.index] == self.phantom and lst == sorted(lst),
                 "set-code list no longer holds the donor, still sorted")

        return Compiled(posts=(post,), checks=(check,))


_LSD_TREE_KEY, _LSD_MAT_LEAF = 0x219D, 0x02249478


_LSD_PHASE_STATE, _LSD_SET_LP, _LSD_ON_FIELD = 0x0229AAFC, 0x021CF8F5, 0x021AC0C9


_LSD_DMG_IMMUNE, _LSD_DES_WOMBAT = 0x021BACDC, 0x18C4


_LAVAL = 0x22D3


@dataclass(frozen=True)
class named_nontuner_material_leaf:
    """'1 Tuner + "<named card>"': the NDS still carries the real card's non-Tuner leaf (KB
    synchro.life_stream_named_nontuner_leaf, material cid 0x1FC9 Power Tool Dragon): the 4-byte THIRD cid-tree entry
    0x02248AB8 (`ldr r0,=0x219D ; str r0,[sp,#0xC]`) is detoured to a stub which sends Synchro `cid` to that leaf and
    otherwise replays the entry. Exactly 2 materials follows from the Levels."""
    slot: int          # ov3 pool

    def compile(self, view, cid) -> Compiled:
        b = EffectBuilder()
        b.ldr_const(0, cid)
        b.insn("CMP", "R5, R0")
        b.insn("BEQ", "lsd")
        b.ldr_const(0, _LSD_TREE_KEY)
        b.insn("STR", "R0, [SP, #0xC]")
        b.insn("BX", "LR")
        b.label("lsd")
        b.ldr_const(0, _LSD_MAT_LEAF | 1)
        b.insn("BX", "R0")
        blob = b.assemble(self.slot, pad="nop")
        assert_thumb1_only(blob, self.slot)
        install, check = _bl_hooks(((0x02248AB8, bytes.fromhex("97480390"), self.slot, "THIRD cid-tree entry"),))
        return Compiled(((self.slot, blob, "material leaf stub"),), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class synchro_summoned_set_lp:
    """'When this card is Synchro Summoned: You can make your LP become N.' Shared summon_trigger_hook (the donor is
    already in its ARMS); cls1 {+04 RES, +0C 0x021F0385 (Ljosalf's pre-check only: 0x021F0419 needs a criteria row),
    +10 'You can' 0x021E51E5} over a phantom (Karakuri Burei's optional-trigger shape); the resolver sets LP via
    0x021CF8F4(side, N) at phase 0x80 (KB lp.set_lp_primitive)."""
    lp: int
    slot: int          # ov3 pool
    phantom: int
    cond: int
    tag: int

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import summon_trigger_hook as sth
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.ldr_const(0, _LSD_PHASE_STATE)
        b.insn("LDR", "R0, [R0, #0x70]")
        b.insn("CMP", "R0, #0x80")
        b.insn("BNE", "done")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call_addr(_LSD_SET_LP, R0, self.lp, via=R3)
        b.insn("MOV", "R0, #0x7F")
        b.insn("POP", "{R4, PC}")
        b.label("done")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        blob = b.assemble(self.slot, pad="nop")
        assert_thumb1_only(blob, self.slot)

        def install(rom, view):
            sth.apply(view.buf, ov3=True)
            sth.install(rom, quiet=True, ov=view.buf)

        def check(c, rom, view):
            c.ok(any(k == cid for k, _ in sth.ARMS), "registered in summon_trigger_hook.ARMS")
            sth.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)

        return Compiled(((self.slot, blob, "resolver"),),
                        (Row(CLS1, (cid, 0, self.slot | 1, 0, self.cond, self.tag, 0), self.phantom),),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class no_effect_damage_while_on_field:
    """'You take no effect damage.' The Des Wombat arm of the effect-damage gate (0x021BACCC, KB
    damage.effect_damage_immunity_gate) is detoured: 0x021AC0C9(side, cid, -1) != 0 -> immune (jump to the gate's
    `movs r0,#0 ; pop` at 0x021BACDC), else the native arm."""
    slot: int          # ov3 pool

    def compile(self, view, cid) -> Compiled:
        b = EffectBuilder()
        b.insn("PUSH", "{LR}")
        b.call_addr(_LSD_ON_FIELD, R5, cid, 0xffffffff, via=R3)
        b.insn("POP", "{R3}")
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "native")
        b.ldr_const(3, _LSD_DMG_IMMUNE | 1)
        b.label("native")
        b.insn("MOV", "R2, #0x0")
        b.ldr_const(1, _LSD_DES_WOMBAT)
        b.insn("BX", "R3")
        blob = b.assemble(self.slot, pad="nop")
        assert_thumb1_only(blob, self.slot)
        install, check = _bl_hooks(((0x021BACCC, bytes.fromhex("00222449"), self.slot, "Des Wombat arm"),))
        return Compiled(((self.slot, blob, "damage immunity stub"),), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class banish_from_gy_instead_of_destruction:
    """'If this face-up card on the field would be destroyed, you can banish 1 <filter> from your Graveyard instead.'
    Laval the Greater's NATIVE substitute with the donor's own criteria row (the 3DS row of the real card) over a
    phantom. Five 4-byte detours add the donor where Laval's cid is tested (binary trees, so the donor is caught at the
    `ldr r1,=0x1C8B ; cmp r5,r1` head of the low branch): decide switch -> Laval arm 0x021CE940, Yes-consumer -> arm
    0x021CF066, UI step 9 phases 0/1 (message 0x56, row picker mode 6), executor survive leaf (clear [0x0229C314+4]).
    slots = (dec, ack, step9, surv), ov3 pool."""
    row: tuple               # (cid, 0xFFFF, handler, word)
    phantom: int
    slots: tuple[int, int, int, int]

    def compile(self, view, cid) -> Compiled:
        dec_s, ack_s, step9_s, surv_s = self.slots

        def redirect(base, native_key, target):
            b = EffectBuilder()
            b.ldr_const(1, cid)
            b.insn("CMP", "R5, R1")
            b.insn("BEQ", "lsd")
            b.ldr_const(1, native_key)
            b.insn("CMP", "R5, R1")
            b.insn("BX", "LR")
            b.label("lsd")
            b.ldr_const(1, target | 1)
            b.insn("BX", "R1")
            return b.assemble(base, pad="nop")

        db = redirect(dec_s, 0x1C8B, 0x021CE940)
        ab = redirect(ack_s, 0x1C8B, 0x021CF066)
        b = EffectBuilder()
        b.ldr_const(1, _LAVAL)
        b.insn("CMP", "R4, R1")
        b.insn("BEQ", "out")
        b.ldr_const(1, cid)
        b.insn("CMP", "R4, R1")
        b.label("out")
        b.insn("BX", "LR")
        sb = b.assemble(step9_s, pad="nop")
        b = EffectBuilder()
        b.insn("LDR", "R1, [SP, #0x64]")
        b.ldr_const(4, cid)
        b.insn("CMP", "R1, R4")
        b.insn("BEQ", "out")
        b.ldr_const(4, _LAVAL)
        b.label("out")
        b.insn("BX", "LR")
        kb = b.assemble(surv_s, pad="nop")
        blobs = (db, ab, sb, kb)
        for blob, addr in zip(blobs, self.slots):
            assert_thumb1_only(blob, addr)
        install, check = _bl_hooks((
            (0x021CE89C, bytes.fromhex("8b498d42"), dec_s, "substitute decide switch"),
            (0x021CF00E, bytes.fromhex("5f498d42"), ack_s, "Yes-consumer switch"),
            (0x0225CAC8, bytes.fromhex("20498c42"), step9_s, "UI step 9 phase 0"),
            (0x0225CAF2, bytes.fromhex("16498c42"), step9_s, "UI step 9 phase 1"),
            (0x021CC656, bytes.fromhex("874c1999"), surv_s, "executor survive leaf")))
        names = ("decide redirect", "Yes-consumer redirect", "UI step 9", "survive leaf")
        return Compiled(tuple(zip(self.slots, blobs, names)), (Row(CRITERIA, self.row, self.phantom),),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x18FA,
    fusion_recipe_blanked(row=81, stock=(0x18FA, 0x18F1, 0x18F2, 0)),
    named_nontuner_material_leaf(slot=cave3.CAVE3_LSD_MAT),
    synchro_summoned_set_lp(lp=4000, slot=cave3.CAVE3_LSD_RES, phantom=0x0E59, cond=0x021F0385, tag=0x021E51E5),
    no_effect_damage_while_on_field(slot=cave3.CAVE3_LSD_DMG),
    banish_from_gy_instead_of_destruction(
        row=(0x18FA, 0xFFFF, 0x0223CA11, 0x00000204), phantom=0x0E93,           # GY, Equip Spell
        slots=(cave3.CAVE3_LSD_DEC, cave3.CAVE3_LSD_ACK, cave3.CAVE3_LSD_STEP9, cave3.CAVE3_LSD_SURV)),
    set_code_slot_to_phantom(base=0x0209CD0E, count=28, index=9, phantom=0x18F8),
    card_prop_copied_from_template(ref_cid=0x239E, card_type="Synchro Tuner Effect Monster",
                                   donor_genre=0x0000000020200000, new_genre=0x0000001800200000))

PROPS = card_props("EARTH", "Dragon", level=8, atk=2900, defense=2400, card_type="Synchro Tuner Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_life_stream_dragon.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
