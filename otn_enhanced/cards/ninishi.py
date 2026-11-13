"""Karakuri Komachi mdl 224 "Ninishi" (EARTH / Machine / Tuner / Level 3 / 0 / 1900) on Dark Chimera 0x0FFD.

    This card must attack if able. When this face-up card is selected as an attack target, change its battle position.
    While this card is face-up on the field, once per turn during your Main Phase, you can Normal Summon 1 "Karakuri"
    monster in addition to your Normal Summon or Set. (You can only gain this effect once per turn.)

Clause 1 ('must attack if able') is karakuri_haipa's shared stub + MUSTATK_ADMIT list; clause 2 rides the shared ov3
attack-target admit list. Dverg 0x245B (the previous donor) keeps its cid, records and own grant.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import KARAKURI_TABLE, archetype_member, card, card_props, CLS1, CLS2, Compiled, Row
from otn_enhanced.effects import cave3
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass
from dataclasses import field
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class karakuri_toggle_position_and_extra_normal_summon_granter_on_normal_donor:
    """'When this face-up card is selected as an attack target, change its battle position. While this card is face-up on the
    field, once per turn during your Main Phase, you can Normal Summon 1 <set> monster in addition to your Normal Summon or Set.
    (You can only gain this effect once per turn.)' (clause 1, 'must attack if able', is karakuri_haipa's shared stub + admit list.)
      A  FIVE stubs + hooks on the four shared granter code sites (every cid there is only ever 'the granter's cid': a hand-search
         key, a rider key, a descriptor stamp, a compare), so this adds a FIFTH granter arm keyed on the donor and the previous donor
         (Dverg) KEEPS its cid, records and own grant. NS_FIELD is a node-free slot scan for the donor (tail-calling the native
         0x021ABE4C for every other cid): the native one also requires a kind<6 node keyed by the card's OWN cid, which is Dverg's
         'after you Normal Summon this card' window and made the first in-game build never offer the summon.
      A5 cls1 graft over a phantom -> the SYMMETRICAL position stubs: +0C = always (the disjunction of the two stock gates), +04 =
         the stock resolver minus the direction compare (the flip primitive takes no target and TOGGLES). Both pointers carry the
         Thumb bit (the dispatcher BLXes them).
      Sites hooked: SITE1 0x021B9634 arm, SITE2 0x021B9F9C spent, SITE3 0x02261E3E predicate (self-modifying pool word: Nordic or
      Karakuri, writes the matching granter cid), SITE4 0x0226515C match + its 2-byte rider patch, and the three `bl ON_FIELD` lookups.
      Clause 2 rides the shared ov3 attack-target admit list (effects/atktgt_gate)."""
    slots: dict                  # pos_cond, pos_res, field, arm, spent, pred, match -> ov3 slot
    dverg: int                   # the previous donor, keeps its grant
    phantom: int
    dverg_cls0_keep: tuple
    dverg_pools: tuple

    def compile(self, view, cid) -> Compiled:
        s = self.slots
        IS_NORDIC, IS_KARAKURI, NODE_QUERY, PLAYER_SLOT = 0x02023FC4, 0x02023F44, 0x021A1430, 0x0B
        ON_FIELD, CID_AT, SLOT_ALIVE = 0x021ABE4C, 0x021A36EC, 0x021A32B4
        PLAYER_BASE, PLAYER_STRIDE, SLOT_STRIDE, SLOT_FLAGS, DISABLE_MASK, MAX_SLOT = 0x0229AC94, 0x0B3C, 0x14, 0x44, 0x0229C314, 0x0A
        S1, S1B, S2, S2B = 0x021B9634, bytes.fromhex("002c04d0"), 0x021B9F9C, bytes.fromhex("002800d1")
        S3, S3POOL, S3DESC = 0x02261E3E, 0x02261F84, 0x0E
        S4, S4B, S4R, S4RB, S4RA = 0x0226515C, bytes.fromhex("15498842"), 0x02265174, 0x490F, 0x8A61
        EPI1 = EPI2 = "{R3, R4, R5, R6, R7, PC}"
        FIELD_CALLS = (0x02261E68, 0x02261EA0, 0x02265164)
        POS_GATE, POS_PRESTEP, POS_FLIP = 0x021D2C1C, 0x021D2D18, 0x021C5324

        b = EffectBuilder()          # SITE 1: run for the previous donor then for this one
        for i, (granter, pred, on_fail) in enumerate(((self.dverg, IS_NORDIC, "arm2"), (cid, IS_KARAKURI, "fail"))):
            if i:
                b.label("arm2")
            b.ldr_const(6, granter)
            b.insn("CMP", "R4, #0x0")
            b.insn("BEQ", f"field{i}")
            b.insn("ADD", "R0, R4, #0x0")
            b.bl(pred)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", on_fail)
            b.label(f"field{i}")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.bl(s["field"])
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", on_fail)
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", f"R1, #0x{PLAYER_SLOT:X}")
            b.insn("ADD", "R2, R6, #0x0")
            b.bl(NODE_QUERY)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ" if i == 0 else "BNE", "hit" if i == 0 else "fail")
        b.label("hit")
        b.insn("ADD", "R0, R6, #0x0")
        b.insn("POP", EPI1)
        b.label("fail")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", EPI1)
        arm = b.assemble(s["arm"])

        b = EffectBuilder()          # SITE 2: keep the previous donor's answer, else ask for this donor
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "done")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("MOV", f"R1, #0x{PLAYER_SLOT:X}")
        b.ldr_const(2, cid)
        b.bl(NODE_QUERY)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "done")
        b.insn("MOV", "R4, #0x0")
        b.label("done")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("POP", EPI2)
        spent = b.assemble(s["spent"])

        b = EffectBuilder()          # SITE 3: "Nordic OR Karakuri", and tell the arm which granter it is running for
        b.insn("PUSH", "{LR}")
        b.bl(IS_NORDIC)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "try_karakuri")
        b.ldr_const(1, self.dverg)
        b.insn("B", "store")
        b.label("try_karakuri")
        b.insn("LDRH", f"R0, [R4, #0x{S3DESC:X}]")
        b.bl(IS_KARAKURI)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "out")
        b.ldr_const(1, cid)
        b.label("store")
        b.ldr_const(2, S3POOL)
        b.insn("STR", "R1, [R2, #0x0]")
        b.insn("MOV", "R0, #0x1")
        b.label("out")
        b.insn("POP", "{PC}")
        pred = b.assemble(s["pred"])

        b = EffectBuilder()          # SITE 4: leave Z and r1 = the matched cid
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "out")
        b.ldr_const(1, self.dverg)
        b.insn("CMP", "R0, R1")
        b.label("out")
        b.insn("BX", "LR")
        match = b.assemble(s["match"])

        b = EffectBuilder()          # 'where is the granter' WITHOUT the summoned-this-turn node gate (donor only)
        b.ldr_const(3, cid)
        b.insn("CMP", "R1, R3")
        b.insn("BNE", "native")
        b.insn("PUSH", "{R4, R5, R6, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.insn("ADD", "R6, R1, #0x0")
        b.insn("MOV", "R4, #0x0")
        b.label("loop")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("ADD", "R1, R4, #0x0")
        b.bl(CID_AT)
        b.insn("CMP", "R0, R6")
        b.insn("BNE", "next")
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("ADD", "R1, R4, #0x0")
        b.bl(SLOT_ALIVE)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "next")
        b.ldr_const(0, PLAYER_STRIDE)
        b.insn("MOV", "R1, #0x1")
        b.insn("ADD", "R2, R5, #0x0")
        b.insn("AND", "R2, R1")
        b.insn("MUL", "R0, R2")
        b.ldr_const(2, PLAYER_BASE)
        b.insn("ADD", "R0, R0, R2")
        b.insn("MOV", f"R2, #0x{SLOT_STRIDE:X}")
        b.insn("MUL", "R2, R4")
        b.insn("ADD", "R0, R0, R2")
        b.insn("LDR", f"R0, [R0, #0x{SLOT_FLAGS:X}]")
        b.insn("LSR", "R0, R0, #0x1A")
        b.insn("AND", "R0, R1")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "next")
        b.ldr_const(0, DISABLE_MASK)
        b.insn("LDR", "R0, [R0, #0x0]")
        b.insn("ADD", "R2, R5, #0x0")
        b.insn("LSL", "R2, R2, #0x4")
        b.insn("ADD", "R2, R2, R4")
        b.insn("LSR", "R0, R2")
        b.insn("AND", "R0, R1")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "next")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("next")
        b.insn("ADD", "R4, #0x1")
        b.insn("CMP", f"R4, #0x{MAX_SLOT:X}")
        b.insn("BLE", "loop")
        b.insn("MOV", "R0, #0x0")
        b.insn("MVN", "R0, R0")
        b.insn("POP", "{R4, R5, R6, PC}")
        b.label("native")
        b.ldr_const(3, ON_FIELD | 1)
        b.insn("BX", "R3")
        field = b.assemble(s["field"])

        b = EffectBuilder()
        b.insn("MOV", "R0, #0x1")
        b.insn("BX", "LR")
        pos_cond = b.assemble(s["pos_cond"])
        b = EffectBuilder()
        b.insn("PUSH", "{R3, R4, R5, LR}")
        b.insn("ADD", "R5, R0, #0x0")
        b.bl(POS_GATE)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "out")
        b.insn("ADD", "R0, R5, #0x0")
        b.bl(POS_PRESTEP)
        b.insn("ADD", "R0, R5, #0x0")
        b.insn("LDRB", "R1, [R5, #0x2]")
        b.insn("LDRB", "R2, [R5, #0x3]")
        b.insn("MOV", "R3, #0x0")
        b.insn("MOV", "R4, #0x1")
        b.insn("STR", "R4, [SP, #0x0]")
        b.bl(POS_FLIP)
        b.label("out")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R3, R4, R5, PC}")
        pos_res = b.assemble(s["pos_res"])
        reserves = {"pos_cond": 0x10, "pos_res": 0x40, "field": 0x90, "arm": 0x70, "spent": 0x20, "pred": 0x30, "match": 0x20}
        blobs = dict(pos_cond=pos_cond, pos_res=pos_res, field=field, arm=arm, spent=spent, pred=pred, match=match)
        for k, blob in blobs.items():
            assert len(blob) <= reserves[k], f"{k} is {len(blob)}B (reserve {reserves[k]:#x})"
            assert_thumb1_only(blob, s[k])
        stubs = tuple((s[k], blobs[k], k) for k in ("pos_cond", "pos_res", "field", "arm", "spent", "pred", "match"))
        hooks = ((S1, S1B, s["arm"]), (S2, S2B, s["spent"]), (S3, None, s["pred"]), (S4, S4B, s["match"]),
                 *((x, None, s["field"]) for x in FIELD_CALLS))
        rec = (cid, 0, s["pos_res"] | 1, 0, s["pos_cond"] | 1, 0, 0)

        def before(site, b_):
            return b_ if b_ is not None else common_bl(site, IS_NORDIC if site == S3 else ON_FIELD)

        def dverg_intact(view):
            assert rows(view, CLS2).count(self.dverg_cls0_keep) == 1, "Dverg's Nordic Relic recovery record is gone"
            for pool in self.dverg_pools:
                assert view.u32(pool) == self.dverg, f"granter pool {pool:#010x} = {view.u32(pool):#010x}, expected Dverg"

        def patch(view, addr, bf, af, what):
            assert len(bf) == len(af)
            cur = view.blob(addr, len(af))
            if cur == af:
                return
            assert cur == bf, f"@{addr:#010x} = {cur.hex()} (expected {bf.hex()}) -- {what}"
            view.write(addr, af)

        def install(rom, view):
            from otn_enhanced.effects import atktgt_gate
            dverg_intact(view)
            for site, bf, target in hooks:
                patch(view, site, before(site, bf), common_bl(site, target), "granter hook")
            patch(view, S4R, struct.pack("<H", S4RB), struct.pack("<H", S4RA), "site 4 spent-rider reads desc[+0x12]")
            atktgt_gate.install(view.buf, cid)

        def check(c, rom, view):
            from otn_enhanced.cards import sakitama as _sk, scrap_raptor as _sr
            from otn_enhanced.effects import atktgt_gate
            on_ov3 = True
            raptor_blobs = {a: build(a) for a, _r, build, _w in _sr.c1b_stubs(on_ov3)}
            chained_via = {ns: sr for sr, ns, _w in _sr.c1b_chain_targets(on_ov3)}
            for site, bf, target in hooks:
                cur = _sk.unfronted(view.buf, site)
                good = cur == common_bl(site, target)
                if not good:
                    sr = chained_via.get(target)
                    good = sr is not None and cur == common_bl(site, sr) and view.blob(sr, len(raptor_blobs[sr])) == raptor_blobs[sr]
                c.ok(good, f"granter hook @{site:#010x} (directly or via scrap_raptor's chain)")
            c.eq(view.u16(S4R), S4RA, "site 4 spent-rider reads desc[+0x12], not a literal")
            c.ok(atktgt_gate.hooked(view.buf) and cid in atktgt_gate.admitted(view.buf), f"clause 2: gate hooked, {cid:#06x} admitted")
            from otn_enhanced.cards import karakuri_haipa as _haipa
            c.ok(cid in _haipa.MUSTATK_ADMIT, "clause 1 'must attack if able': donor in haipa's MUSTATK_ADMIT")
            try:
                dverg_intact(view)
                c.ok(True, "Dverg keeps its Nordic-Relic record AND all four granter pools")
            except AssertionError as exc:
                c.ok(False, f"Dverg regressed: {exc}")
            c.ok(all(r[1] == 0 for r in rows(view, CLS1)), "no cls1 record grew a nonzero pad halfword")

        return Compiled(stubs, (Row(CLS1, rec, self.phantom),), installs=(install,), checks=(check,))



SPEC = card(
    0x0FFD,
    karakuri_toggle_position_and_extra_normal_summon_granter_on_normal_donor(
        slots=dict(pos_cond=cave3.CAVE3_NIN_POSCOND, pos_res=cave3.CAVE3_NIN_POSRES, field=cave3.CAVE3_NS_FIELD,
                   arm=cave3.CAVE3_NS_ARM, spent=cave3.CAVE3_NS_SPENT, pred=cave3.CAVE3_NS_PRED, match=cave3.CAVE3_NS_MATCH),
        dverg=0x245B, phantom=0x1140,
        dverg_cls0_keep=(0x245B, 0x0000, 0x02208181, 0x00000000, 0x0224A115, 0x00000000, 0x02235605),
        dverg_pools=(0x021B9670, 0x021B9FBC, 0x02261F84, 0x022651B4)),
    archetype_member(KARAKURI_TABLE, phantom=0x1140))

PROPS = card_props("EARTH", "Machine", level=3, atk=0, defense=1900, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_ninishi.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
