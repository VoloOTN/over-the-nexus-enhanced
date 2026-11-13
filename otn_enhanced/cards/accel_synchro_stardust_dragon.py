"""Accel Synchro Stardust Dragon (WIND / Dragon / Synchro Effect / Level 8 / 2500 / 2000) on Meteor B. Dragon 0x126F.

    1 Tuner + 1 or more non-Tuner monsters
    If this card is Synchro Summoned: You can Special Summon 1 Level 2 or lower Tuner from your GY. During the Main
    Phase (Quick Effect): You can Tribute this card; Special Summon 1 "Stardust Dragon" from your Extra Deck (this is
    treated as a Synchro Summon), then, immediately after this effect resolves, Synchro Summon 1 Synchro Monster using
    monsters you control as material. You can only use each effect of "Accel Synchro Stardust Dragon" once per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_prop_copied_from_template, card_props, fusion_recipe_blanked, CLS1, CLS3, CRITERIA, Compiled, Row, _AS_DUEL_STATE, _TURNLOG_POST, _TURNLOG_QUERY, _append_criteria_row
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import insert_sorted
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


_AS_TAG_BODY = 0x021E50DD                    # costless "You can" body; 1 == the player said yes


_AS_GY_CANDIDATE_COND = 0x021F03B5


_AS_ED_SUMMON, _AS_PHASE_REG, _AS_SEL_GET, _AS_SS_ENGINE = 0x0220AF0D, 0x0229AAFC, 0x0219C511, 0x0226925D


_AS_TRIBUTE_SS_COND, _AS_TRIBUTE_TAG, _AS_SYNCHRO_RESOLVER, _AS_FORCED_MATERIAL = 0x021F90E1, 0x021E50CD, 0x02249EC1, 0x0229AC7C


_AS_REVIVE, _AS_TARGET_DECLARE = 0x02207191, 0x02235605


@dataclass(frozen=True)
class synchro_summoned_revive_gy_tuner_once_per_turn:
    """'If this card is Synchro Summoned: You can Special Summon 1 Level N or lower Tuner from your GY. Once per turn.'
    cls1 {Malefic Paradox's non-targeting revive 0x02207191, 0, COND, SLOT4, picker 0x02235605}; criteria rel 0 =
    {cid, 0xFFFF, GY handler, word}. +0C = turn-log (side, 0xB, cid, kind) clear -> the native GY candidate gate;
    +10 = the costless 'You can' body, a Yes stamps the lock (declining is free). The proper-SS list is FULL, so the
    trigger is the shared summon_trigger_hook arm (registered there) and the class-2 'You can' is the shared
    timing_class_hook arm (registered there); both ov3 hooks + ov5 stubs are installed here idempotently."""
    cond: int
    slot4: int
    crit: tuple[int, int, int]        # criteria rel 0: (aux, handler, word)
    phantoms: tuple[int, int]         # (cls1, criteria rel 0)
    kind: int = 1

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import summon_trigger_hook as sth
        from otn_enhanced.effects import timing_class_hook as tch
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("LDRB", "R0, [R5, #0x2]")
        b.turnlog_query(R0, cid, self.kind, via=R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "used")
        b.call_addr(_AS_GY_CANDIDATE_COND, R5, via=R4)
        b.insn("POP", "{R4, R5, PC}")
        b.label("used")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, PC}")
        cb = b.assemble(self.cond, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.call_addr(_AS_TAG_BODY, via=R2)
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
        for a_ in (_TURNLOG_QUERY, _TURNLOG_POST, _AS_TAG_BODY, _AS_GY_CANDIDATE_COND):
            assert a_ & 1, f"{a_:#x}: blx to an even literal switches to ARM state -> freeze"
        assert any(a[0] == cid for a in sth.ARMS), "the trigger arm must be registered in summon_trigger_hook"
        assert any(a[0] == cid for a in tch.ARMS), "the timing arm must be registered in timing_class_hook"
        ph1, phc = self.phantoms
        row0 = (cid,) + self.crit

        def install(rom, view):
            insert_sorted(view, CRITERIA, row0, drop=phc, quiet=True)
            sth.apply(view.buf)
            tch.apply(view.buf)
            sth.install(rom, quiet=True)
            tch.install(rom, quiet=True)

        def check(c, rom, view):
            sth.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)
            tch.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)

        return Compiled(((self.cond, cb, "C1 +0C cond"), (self.slot4, sb, "C1 +10 slot4")),
                        (Row(CLS1, (cid, 0, _AS_REVIVE, 0, self.cond | 1, self.slot4 | 1, _AS_TARGET_DECLARE), ph1),),
                        installs=(install,), checks=(check,))


@dataclass(frozen=True)
class quick_effect_tribute_summon_from_extra_deck_then_synchro_summon:
    """'During the Main Phase (Quick Effect): You can Tribute this card; Special Summon 1 <named> from your Extra Deck
    (this is treated as a Synchro Summon), then, immediately after this effect resolves, Synchro Summon 1 Synchro
    Monster using monsters you control as material. Once per turn.'
      cls3 {DISP, 0, COND, COST, 0}: DISP = STAGE-gated dispatcher. STAGE == 0: phase 0x7D (C2's last, a no-op for this
        cid in Cyber-Stein) -> STAGE = 1, return 0x80; any other phase -> RES. STAGE == 1: blx the shared Synchro
        resolver 0x02249EC1, zero the forced-material global (phase 0x7D stores the TRIBUTED source there, so nothing
        would be selectable), clear STAGE when it returns 0. RES = Cyber-Stein's 4-phase ED summon with its one flag
        build replayed at phase 0x7E as (cid<<16)|1. COND = Main Phase 1/2 either turn + desc[+7]-guarded kind-2 query
        + Kaibaman's Tribute-and-SS gate; COST = post kind 2, then Kaibaman's Tribute tag.
      criteria rel 1 (Starlight Road's 'named from the Extra Deck') and rel 2 (Urgent Tuning's 'using monsters you
        control') appended AFTER rel 0; criteria_row_hook arm: cls3 -> rel 1 + STAGE (registered there).
      ARM9 spell-speed-2 list: `qe` phantom out, the donor in (count immediate + pool word asserted)."""
    disp: int
    res: int
    cond: int
    cost: int
    stage: int
    named: int
    crit1: tuple[int, int]                 # criteria rel 1: (handler, word); aux = named
    crit2: tuple[int, int, int]            # criteria rel 2: (aux, handler, word)
    qe: tuple[int, int, int, int]          # (list, count imm, pool word, phantom)
    phantoms: tuple[int, int, int]         # (cls3, criteria rel 1, criteria rel 2)
    kind: int = 2

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import criteria_row_hook as crh
        from otn_enhanced.effects.common import read_thunk_list, swap_in_list
        kind = self.kind
        b = EffectBuilder()
        b.ldr_const(2, _AS_PHASE_REG)
        b.insn("LDR", "R2, [R2, #0x70]")
        b.insn("CMP", "R2, #0x7E")
        b.insn("BEQ", "summon")
        b.ldr_const(2, _AS_ED_SUMMON)
        b.insn("BX", "R2")
        b.label("summon")
        b.insn("PUSH", "{R3, R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRH", "R5, [R4, #0x0]")
        b.call_addr(_AS_SEL_GET, via=R3)
        b.insn("ADD", "R1, R0, #0x0")
        b.insn("LSL", "R0, R5, #0x10")
        b.insn("ADD", "R0, #0x1")
        b.insn("STR", "R0, [SP, #0x0]")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call_addr(_AS_SS_ENGINE, R0, R1, 1, 2, via=R5)
        b.insn("MOV", "R0, #0x7D")
        b.insn("POP", "{R3, R4, R5, PC}")
        res = b.assemble(self.res, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.ldr_const(0, _AS_DUEL_STATE)
        b.insn("LDR", "R0, [R0, #0x48]")
        b.insn("CMP", "R0, #0x2")
        b.insn("BEQ", "phase")
        b.insn("CMP", "R0, #0x4")
        b.insn("BNE", "no")
        b.label("phase")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "chain")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_query(R0, cid, kind, via=R5)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.label("chain")
        b.call_addr(_AS_TRIBUTE_SS_COND, R4, via=R5)
        b.insn("POP", "{R4, R5, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, PC}")
        cond = b.assemble(self.cond, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.turnlog_post(R0, cid, kind, via=R5)
        b.call_addr(_AS_TRIBUTE_TAG, R4, via=R5)
        b.insn("POP", "{R4, R5, PC}")
        cost = b.assemble(self.cost, pad="nop")

        b = EffectBuilder()
        b.ldr_const(2, self.stage)
        b.insn("LDRB", "R3, [R2, #0x0]")
        b.insn("CMP", "R3, #0x0")
        b.insn("BNE", "c3")
        b.ldr_const(3, _AS_PHASE_REG)
        b.insn("LDR", "R3, [R3, #0x70]")
        b.insn("CMP", "R3, #0x7D")
        b.insn("BEQ", "handoff")
        b.ldr_const(3, self.res | 1)
        b.insn("BX", "R3")
        b.label("handoff")
        b.insn("MOV", "R3, #0x1")
        b.insn("STRB", "R3, [R2, #0x0]")
        b.insn("MOV", "R0, #0x80")
        b.insn("BX", "LR")
        b.label("c3")
        b.insn("PUSH", "{R4, LR}")
        b.call_addr(_AS_SYNCHRO_RESOLVER, via=R3)
        b.ldr_const(2, _AS_FORCED_MATERIAL)
        b.insn("MOV", "R3, #0x0")
        b.insn("STR", "R3, [R2, #0x0]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "out")
        b.ldr_const(2, self.stage)
        b.insn("STRB", "R0, [R2, #0x0]")
        b.label("out")
        b.insn("POP", "{R4, PC}")
        disp = b.assemble(self.disp, pad="nop")
        stubs = ((self.res, res, "C2 resolver"), (self.cond, cond, "C2 cond"), (self.cost, cost, "C2 cost"),
                 (self.stage, b"\x00" * 4, "C3 stage byte"), (self.disp, disp, "C2/C3 dispatcher"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        for a_ in (_AS_ED_SUMMON, _AS_SEL_GET, _AS_SS_ENGINE, _AS_TRIBUTE_SS_COND, _AS_TRIBUTE_TAG, _AS_SYNCHRO_RESOLVER):
            assert a_ & 1, f"{a_:#x}: blx/bx to an even literal switches to ARM state -> freeze"
        assert any(a[0] == cid for a in crh.ARMS), "the row arm must be registered in criteria_row_hook"
        ph3, phc1, phc2 = self.phantoms
        row1, row2 = (cid, self.named) + self.crit1, (cid,) + self.crit2
        qe_list, qe_imm, qe_pool, qe_ph = self.qe

        def install(rom, view):
            row0s = [r for r in rows(view, CRITERIA) if r[0] == cid]
            assert len(row0s) >= 1, "criteria rel 0 must be inserted first"
            _append_criteria_row(view, cid, row1, phc1, row0s[:1])
            _append_criteria_row(view, cid, row2, phc2, row0s[:1] + [row1])
            crh.apply(view.buf)
            crh.install(rom, quiet=True)
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)
            base, n, lst = read_thunk_list(bytes(d), qe_pool, qe_imm, qe_list, "spell-speed-2 list")
            if cid in lst:
                return
            assert 0x17C2 in lst and 0x0FE0 in lst and 0x1B44 in lst, "not the Quick Effect list"
            out = swap_in_list(lst, qe_ph, cid, "spell-speed-2 list")
            struct.pack_into(f"<{n}H", d, base - 0x02000000, *out)
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def check(c, rom, view):
            recs = rows(view, CRITERIA)
            ks = [r[0] for r in recs]
            mine = [r for r in recs if r[0] == cid]
            c.ok(ks == sorted(ks) and len(mine) == 3 and mine[1:] == [row1, row2]
                 and not any(p in ks for p in (phc1, phc2)),
                 "criteria rel 1 + rel 2 under the donor after rel 0, in order; phantoms dropped; sorted")
            crh.verify(view.buf, lambda ok, msg: c.ok(bool(ok), msg), rom=rom)
            mc, sec = ov5_cave._arm9_main(rom)
            _, _, lst = read_thunk_list(bytes(sec.data), qe_pool, qe_imm, qe_list, "spell-speed-2")
            c.ok(cid in lst and qe_ph not in lst and all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)),
                 "spell-speed-2 list holds the donor, phantom gone, strictly sorted")

        return Compiled(stubs,
                        (Row(CLS3, (cid, self.disp | 1, 0, self.cond | 1, self.cost | 1, 0), ph3),),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x126F,
    fusion_recipe_blanked(row=52, stock=(0x126F, 0x0FF8, 0x126E, 0)),
    synchro_summoned_revive_gy_tuner_once_per_turn(
        cond=ov5_cave.CAVE_ASSD_C1_COND, slot4=ov5_cave.CAVE_ASSD_C1_SLOT4,
        crit=(0xFFFF, 0x0223C9D1, 0x00898002),              # Level 2 or lower Tuner, GY
        phantoms=(0x1280, 0x14BA)),
    quick_effect_tribute_summon_from_extra_deck_then_synchro_summon(
        disp=ov5_cave.CAVE_ASSD_C3_DISP, res=ov5_cave.CAVE_ASSD_C2_RES, cond=ov5_cave.CAVE_ASSD_C2_COND,
        cost=ov5_cave.CAVE_ASSD_C2_COST, stage=ov5_cave.CAVE_ASSD_STAGE,
        named=0x1E36,                                       # Stardust Dragon
        crit1=(0x022423C9, 0x00000802),                     # Starlight Road's row
        crit2=(0xFFFF, 0x02240EF5, 0x00000802),             # Urgent Tuning's row
        qe=(0x0209C118, 0x02023490, 0x020234A4, 0x0E82),
        phantoms=(0x14B9, 0x1445, 0x0EBE)),
    card_prop_copied_from_template(ref_cid=0x23FE, card_type="Synchro Effect Monster",
                                   donor_genre=0x0000000020200000, new_genre=0x0000001000200000))

PROPS = card_props("WIND", "Dragon", level=8, atk=2500, defense=2000, card_type="Synchro Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_accel_stardust.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
