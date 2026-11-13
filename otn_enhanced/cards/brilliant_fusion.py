"""Brilliant Fusion on Temple of the Sun 0x21D5 (Continuous Spell, keep-cid).

    When this card is activated: Fusion Summon 1 "Gem-Knight" Fusion Monster from your Extra Deck, using monsters from your
    Deck as Fusion Material, but change its ATK/DEF to 0. If this card leaves the field, destroy that monster. Once per
    turn: You can discard 1 Spell; the monster Special Summoned by this card's effect gains ATK/DEF equal to its original
    ATK/DEF, until the end of your opponent's turn. You can only activate 1 "Brilliant Fusion" per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, CLS0, CLS3, CRITERIA, Compiled, Row
from otn_enhanced.effects import ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.effects.common import Table
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
from otn_enhanced.effects.common import rows


LIST_CRITERIA_ROW_OFFSET = Table(0x0227134C, 0x3B, 2, "<H", label="criteria row-offset list A")


LIST_LEAVE_CLEANUP = Table(0x0226E940, 40, 2, "<H", label="leave-cleanup list")


@dataclass(frozen=True)
class continuous_spell_fusion_summon_from_deck_stats_zeroed_destroyed_on_leave:
    """'When this card is activated: Fusion Summon 1 <archetype> Fusion Monster from your Extra Deck, using monsters from your
    Deck as Fusion Material, but change its ATK/DEF to 0. If this card leaves the field, destroy that monster. Once per turn: You
    can discard 1 Spell; the monster Special Summoned by this card's effect gains ATK/DEF equal to its original ATK/DEF, until
    the end of your opponent's turn. You can only activate 1 per turn.' (donor: a Continuous Spell)
      A  cls0 INSERT {shared Fusion-spell resolver->RES wrapper, COND, COST} over a phantom.
      B  criteria rows cloned from Gem-Knight Fusion rows 1197/1198 (target row THEN the material-pool row) over two phantoms.
      L  the donor joins criteria row-offset list A so the criteria resolver returns row 1 for a param != 0.
      H1 the fusion MODE classifier 0x022325B4 is a LEAF: all ten `bl` sites go to MODE, which returns 2 (Deck materials) for the
         donor and tail-jumps to the native otherwise. H2 the resolver's material loop has no Deck->GY arm: DECKGY calls the
         Deck relocation core with GY and arms the zero-stat rider.
      R  ATK/DEF -> 0 = rider node {key 0x1F64, kind 3} attached by the shared summon_rider_hook LATCH arm.
      E  C2: the donor joins the leave-cleanup list; RES attaches the kind-0x17 link {key = this card's zone<<8|side} to the
         summoned monster on resolver phase 1 (Future Fusion's recipe); the destination switch defaults the donor to destroy.
      G  C3: cls3 ignition {C3RES, 0, C3COND, native discard-1-Spell cost 0x021E8FD5, 0} over a phantom: C3COND needs the linked
         monster (C3FIND) + Chiron's cid-blind condition; C3RES reads its ORIGINAL ATK/DEF and attaches two {key 0x221D, kind
         0x12} riders (the stat-switch pair leaf adds them AFTER the 0/0 key). Once per turn rides Soul Charge's pair."""
    res: int
    cond: int
    cost: int
    mode: int
    deckgy: int
    c3find: int
    c3cond: int
    c3res: int
    arm: int
    phantoms: dict      # cls0, cls3, crit (2), lista, leave

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import summon_rider_hook as riderhook
        FUSION_RESOLVER, FUSION_COND, MODE_FN = 0x02232CFD, 0x02232CB0, 0x022325B4
        PHASE_STATE, FUSION_UI, SUMMON_EVENT, LINK_ATTACH, LINK_KIND = 0x0229AAFC, 0x0229ABFC, 0x02298A28, 0x021C479D, 0x17
        DECK_RELOCATE, DECK_FLAGS = 0x021D1DAD, 0x10
        ONCE_CHECK, COPY_EXEMPT = 0x021F6DD9, 0x021D2B89
        C3_COND_NATIVE, LINK_LOOKUP, STAT_READ, GAIN_KEY, GAIN_KIND = 0x021F7375, 0x021A0C95, 0x021B44B5, 0x221D, 0x12
        C3_COST = 0x021E8FD5
        MODE_SITES = (0x02232E12, 0x02232E46, 0x02232E8A, 0x02233A7E, 0x02233CD2,
                      0x02233FB8, 0x022340D8, 0x022341EE, 0x022343AA, 0x0223BE56)
        DECKGY_SITE, DECKGY_NATIVE = 0x02233564, bytes.fromhex("01980f28")
        LATCH_ARMS = riderhook.LATCH_ARMS
        assert LATCH_ARMS[0][1:4] == (self.arm, 0x1F64, cid)
        crit_rows = ((cid, 0x0054, 0x0223ED09, 0x802), (cid, 0xFFFF, 0x0223C939, 0x002))

        b = EffectBuilder()
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BNE", "native")
        b.insn("MOV", "R0, #0x2")
        b.insn("BX", "LR")
        b.label("native")
        b.ldr_const(1, MODE_FN | 1)
        b.insn("BX", "R1")
        mode = b.assemble(self.mode, pad="nop")

        b = EffectBuilder()          # host frame at 0x02233564: [sp,#4] = destination zone, r4 side, r7 descriptor
        b.insn("LDR", "R0, [SP, #0x4]")
        b.insn("CMP", "R0, #0xE")
        b.insn("BNE", "orig")
        b.insn("LDRH", "R0, [R7, #0x0]")
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BNE", "orig")
        b.insn("PUSH", "{R4, R5, LR}")
        b.insn("LDR", "R2, [SP, #0x1C]")
        b.insn("PUSH", "{R0}")
        b.call_addr(DECK_RELOCATE, R4, 0, R2, DECK_FLAGS, via=R5)
        b.insn("POP", "{R0}")
        b.ldr_const(0, self.arm)
        b.insn("MOV", "R1, #0x1")
        b.insn("STRB", "R1, [R0, #0x0]")
        b.insn("MOV", "R0, #0x1")
        b.insn("CMP", "R0, #0xF")
        b.insn("POP", "{R4, R5, PC}")
        b.label("orig")
        b.insn("LDR", "R0, [SP, #0x4]")
        b.insn("CMP", "R0, #0xF")
        b.insn("BX", "LR")
        deckgy = b.assemble(self.deckgy, pad="nop")

        b = EffectBuilder()          # desc[+7] set = a re-check after the cost already posted our node
        b.insn("PUSH", "{R4, R5, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("ADD", "R5, R1, #0x0")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "native")
        b.call_addr(ONCE_CHECK, R4, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "no")
        b.label("native")
        b.call_addr(FUSION_COND, R4, R5, via=R7)
        b.insn("POP", "{R4, R5, R7, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R7, PC}")
        cond = b.assemble(self.cond, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.ldr_const(0, self.arm)
        b.insn("MOV", "R1, #0x0")
        b.insn("STRB", "R1, [R0, #0x0]")
        b.call_addr(COPY_EXEMPT, R4, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "done")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("LDRH", "R1, [R4, #0x0]")
        b.turnlog_post(R0, R1, 1, via=R7)
        b.label("done")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{R4, R7, PC}")
        cost = b.assemble(self.cost, pad="nop")

        b = EffectBuilder()          # phase 1 is driven because commit phase 0x32 returns 1 (also when nothing was summoned)
        b.insn("PUSH", "{R4, R5, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("ADD", "R5, R1, #0x0")
        b.ldr_const(0, PHASE_STATE)
        b.insn("LDR", "R0, [R0, #0x70]")
        b.insn("CMP", "R0, #0x1")
        b.insn("BNE", "native")
        b.ldr_const(3, SUMMON_EVENT)
        b.insn("LDRH", "R0, [R3, #0x12]")
        b.ldr_const(1, cid)
        b.insn("CMP", "R0, R1")
        b.insn("BNE", "native")
        b.insn("LDRH", "R0, [R3, #0xE]")
        b.ldr_const(1, FUSION_UI)
        b.insn("LDR", "R1, [R1, #0x68]")
        b.insn("CMP", "R0, R1")
        b.insn("BNE", "native")
        b.insn("LDRB", "R2, [R4, #0x3]")
        b.insn("LSL", "R2, R2, #0x8")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.insn("ORR", "R2, R0")
        b.insn("LDRB", "R1, [R4, #0x6]")
        b.insn("EOR", "R0, R1")
        b.insn("LDRH", "R1, [R3, #0x4]")
        b.insn("MOV", "R3, #0x0")
        b.insn("PUSH", "{R3}")
        b.call_addr(LINK_ATTACH, R0, R1, R2, LINK_KIND, via=R7)
        b.insn("POP", "{R3}")
        b.label("native")
        b.call_addr(FUSION_RESOLVER, R4, R5, via=R7)
        b.insn("POP", "{R4, R5, R7, PC}")
        res = b.assemble(self.res, pad="nop")

        b = EffectBuilder()          # the leave-destroy loop's test: link kind != 0 and != 0xC
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("ADD", "R6, R0, #0x0")
        b.insn("MOV", "R4, #0x0")
        b.label("side")
        b.insn("MOV", "R5, #0x0")
        b.label("slot")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("ADD", "R1, R5, #0x0")
        b.insn("LDRB", "R2, [R6, #0x2]")
        b.insn("LDRB", "R3, [R6, #0x3]")
        b.call_addr(LINK_LOOKUP, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "next")
        b.insn("CMP", "R0, #0xC")
        b.insn("BEQ", "next")
        b.insn("LSL", "R0, R4, #0x8")
        b.insn("ORR", "R0, R5")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        b.label("next")
        b.insn("ADD", "R5, #0x1")
        b.insn("CMP", "R5, #0x5")
        b.insn("BLT", "slot")
        b.insn("ADD", "R4, #0x1")
        b.insn("CMP", "R4, #0x2")
        b.insn("BLT", "side")
        b.insn("MOV", "R0, #0x0")
        b.insn("SUB", "R0, #0x1")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        c3find = b.assemble(self.c3find, pad="nop")

        b = EffectBuilder()
        b.insn("PUSH", "{R4, R5, R7, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("ADD", "R5, R1, #0x0")
        b.call_addr(self.c3find, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BLT", "no")
        b.call_addr(C3_COND_NATIVE, R4, R5, via=R7)
        b.insn("POP", "{R4, R5, R7, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, R5, R7, PC}")
        c3cond = b.assemble(self.c3cond, pad="nop")

        b = EffectBuilder()          # [sp] = attach's 5th arg; [sp+4..] = stat buffer (orig ATK -> sp+0x1C, orig DEF -> sp+0x20)
        b.insn("PUSH", "{R4, R5, R6, R7, LR}")
        b.insn("SUB", "SP, #0x2C")
        b.insn("ADD", "R6, R0, #0x0")
        b.call_addr(self.c3find, via=R7)
        b.insn("CMP", "R0, #0x0")
        b.insn("BLT", "done")
        b.insn("LSR", "R4, R0, #0x8")
        b.insn("LSL", "R5, R0, #0x18")
        b.insn("LSR", "R5, R5, #0x18")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("ADD", "R1, R5, #0x0")
        b.insn("ADD", "R2, SP, #0x4")
        b.call_addr(STAT_READ, R0, R1, R2, 0, via=R7)
        b.ldr_const(7, LINK_ATTACH)
        for off in (0x1C, 0x20):
            b.insn("LDR", "R0, [SP, #0x%X]" % off)
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("LSR", "R0, R0, #0x10")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.ldr_const(2, GAIN_KEY)
            b.insn("MOV", f"R3, #0x{GAIN_KIND:X}")
            b.insn("BLX", "R7")
        b.label("done")
        b.insn("MOV", "R0, #0x0")
        b.insn("ADD", "SP, #0x2C")
        b.insn("POP", "{R4, R5, R6, R7, PC}")
        c3res = b.assemble(self.c3res, pad="nop")
        stubs = ((self.res, res, "RES"), (self.c3find, c3find, "C3FIND"), (self.c3cond, c3cond, "C3COND"),
                 (self.c3res, c3res, "C3RES"), (self.mode, mode, "MODE"), (self.deckgy, deckgy, "DECKGY"),
                 (self.cond, cond, "COND"), (self.cost, cost, "COST"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        ph = self.phantoms
        cls3_rec = (cid, self.c3res | 1, 0, self.c3cond | 1, C3_COST, 0)

        def install(rom, view):
            riderhook.install(rom, latch_arms=LATCH_ARMS)
            riderhook.apply(view.buf, latch_arms=LATCH_ARMS)
            recs = list(rows(view, CRITERIA))
            if crit_rows[0] not in recs:
                cids = [r[0] for r in recs]
                assert cids == sorted(cids) and cid not in cids, "criteria table state"
                for p in ph["crit"]:
                    assert cids.count(p) == 1, f"criteria phantom {p:#06x} spent or duplicated"
                recs = [r for r in recs if r[0] not in ph["crit"]]
                at = sum(1 for r in recs if r[0] <= cid)
                recs[at:at] = list(crit_rows)                # row 0 (target) THEN row 1 (pool)
                assert len(recs) == CRITERIA.count and [r[0] for r in recs] == sorted(r[0] for r in recs)
                for i, r in enumerate(recs):
                    view.pack(CRITERIA.addr(i), CRITERIA.fmt, *r)
            for site in MODE_SITES:
                cur, want = view.blob(site, 4), common_bl(site, self.mode)
                if cur != want:
                    assert cur == common_bl(site, MODE_FN), f"{site:#010x} is {cur.hex()}, not `bl {MODE_FN:#010x}`"
                    view.write(site, want)
            cur, want = view.blob(DECKGY_SITE, 4), common_bl(DECKGY_SITE, self.deckgy)
            if cur != want:
                assert cur == DECKGY_NATIVE, f"{DECKGY_SITE:#010x} is {cur.hex()}, not stock"
                view.write(DECKGY_SITE, want)

        def check(c, rom, view):
            recs = rows(view, CRITERIA)
            cids = [r[0] for r in recs]
            i = cids.index(cid) if cid in cids else -1
            c.ok(i >= 0 and tuple(recs[i:i + 2]) == crit_rows and cids.count(cid) == 2,
                 "criteria: target row THEN pool row, nothing else")
            c.ok(not set(ph["crit"]) & set(cids) and cids == sorted(cids), "criteria: phantoms spent, sorted")
            c3 = rows(view, CLS3)
            k3 = [r[0] for r in c3]
            c.ok(k3[527] == 0x1FFC and k3[645] == cid,
                 "cls3: Sea Lancer's by-index row 527 still 0x1FFC; donor at [645] (shift range 645..711 only)")
            c.ok(0x1A7E in keys(view, LIST_LEAVE_CLEANUP), "leave-cleanup list: Future Fusion still a member")
            for site in MODE_SITES:
                c.eq(view.blob(site, 4), common_bl(site, self.mode), f"H1 {site:#010x} -> MODE")
            c.eq(view.blob(DECKGY_SITE, 4), common_bl(DECKGY_SITE, self.deckgy), "H2 0x02233564 -> DECKGY")
            riderhook.verify(rom, view.buf, lambda ok, what: c.ok(bool(ok), what), latch_arms=LATCH_ARMS)

        return Compiled(stubs,
                        (Row(CLS0, (cid, self.res | 1, 0, self.cond | 1, self.cost | 1, 0), ph["cls0"]),
                         Row(CLS3, cls3_rec, ph["cls3"]),
                         Row(LIST_CRITERIA_ROW_OFFSET, (cid,), ph["lista"]),
                         Row(LIST_LEAVE_CLEANUP, (cid,), ph["leave"])),
                        installs=(install,), checks=(check,))



SPEC = card(
    0x21D5,
    continuous_spell_fusion_summon_from_deck_stats_zeroed_destroyed_on_leave(
        res=ov5_cave.CAVE_BF_RES, cond=ov5_cave.CAVE_BF_COND, cost=ov5_cave.CAVE_BF_COST, mode=ov5_cave.CAVE_BF_MODE,
        deckgy=ov5_cave.CAVE_BF_DECKGY, c3find=ov5_cave.CAVE_BF_C3FIND, c3cond=ov5_cave.CAVE_BF_C3COND,
        c3res=ov5_cave.CAVE_BF_C3RES, arm=ov5_cave.CAVE_BF_ARM,
        phantoms=dict(cls0=0x143B, cls3=0x234B, crit=(0x1507, 0x1508), lista=0x1303, leave=0x0E48)))

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_brilliant_fusion.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
