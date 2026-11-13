"""Nikitama (Spirit / LIGHT / Fairy / Level 4 / 800 / 1800) on Wolf 0x0FE3.

    Cannot be Special Summoned. During the End Phase of the turn this card is Normal Summoned or flipped face-up: Return
    it to the hand. During the turn this card was Normal Summoned or flipped face-up, you can Normal Summon 1 Spirit
    monster in addition to your Normal Summon/Set. (You can only gain this effect once per turn.) When this card is sent
    to the Graveyard: Draw 1 card. You must control a Spirit monster to activate and to resolve this effect.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import FLIPPED_FACE_UP_TABLE, archetype_member, card, card_genre_word, card_props, CLS1, CLS2, Compiled, DRAW_COUNT, LEAVE_MASK, LIST_CODE78, Row
from otn_enhanced.effects import cave3, ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import cave3
from otn_enhanced.effects.common import bl as common_bl
from dataclasses import dataclass
from dataclasses import field
from otn_enhanced.effects.common import keys
from otn_enhanced.effects.common import rows


_NS_TLQ, _NS_ANYQ, _NS_IS_SPIRIT, _NS_ARM_POOL = 0x021A14E8, 0x021A1430, 0x020230D4, 0x02261F84


_NS_SITES = dict(arm=0x021B9634, spent=0x021B9F9C, pred=0x02261E3E, field=0x02261E68, count=0x02261E92, match=0x0226515C)


def ns_front_builders(K: int, G: int) -> dict:
    """The six fronts for grant key G (kind 1 on the player slot = "gained this turn") and granter / spent key K. Each chains
    whatever the site BLs now (`prev`). Sakitama's are the same with its own keys."""
    def grant_live(b, side, fail):
        b.call_addr(_NS_TLQ, side, 0xB, G, 1)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", fail)
        b.call_addr(_NS_ANYQ, side, 0xB, K)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", fail)

    def arm(base, prev):             # SITE1 (r5 side, r4 hand cid or 0); exits through the host's pop {r3-r7,pc}
        b = EffectBuilder()
        b.insn("CMP", "R4, #0x0")
        b.insn("BEQ", "grant")
        b.call_addr(_NS_IS_SPIRIT, R4)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "chain")
        b.label("grant")
        grant_live(b, R5, "chain")
        b.ldr_const(0, K)
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        b.label("chain")
        b.call_addr(prev)
        return b.assemble(base, pad="nop")

    def spent(base, prev):           # SITE2 'has Normal Summoned this turn' chain (r0 previous answer, r5 side, r4 = 1)
        b = EffectBuilder()
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "keep")
        b.call_addr(_NS_ANYQ, R5, 0xB, K)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "chain")
        b.label("keep")
        b.insn("ADD", "R0, R4, #0x0")
        b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
        b.label("chain")
        b.call_addr(prev, 0)
        return b.assemble(base, pad="nop")

    def pred(base, prev):            # SITE3 predicate (r0 hand cid, r4 summon desc): takes the arm ONLY while the grant is live
        b = EffectBuilder()
        b.insn("PUSH", "{LR}")
        b.call_addr(_NS_IS_SPIRIT)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "chain")
        b.insn("LDRH", "R0, [R4, #0x0]")
        b.call("turnlog_query", R0, 0xB, G, 1)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "chain")
        b.insn("LDRH", "R0, [R4, #0x0]")
        b.call_addr(_NS_ANYQ, R0, 0xB, K)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "chain")
        b.ldr_const(1, K)
        b.ldr_const(2, _NS_ARM_POOL)
        b.insn("STR", "R1, [R2, #0x0]")
        b.insn("MOV", "R0, #0x1")
        b.insn("POP", "{PC}")
        b.label("chain")
        b.insn("LDRH", "R0, [R4, #0xE]")
        b.call_addr(prev)
        b.insn("POP", "{PC}")
        return b.assemble(base, pad="nop")

    def field(base, prev):           # SITE3 'where is the granter' (r0 side, r1 pool cid): K -> 0 if the grant exists, else -1
        b = EffectBuilder()
        b.insn("PUSH", "{LR}")
        b.ldr_const(2, K)
        b.insn("CMP", "R1, R2")
        b.insn("BNE", "chain")
        b.call("turnlog_query", R0, 0xB, G, 1)
        b.insn("CMP", "R0, #0x0")
        b.insn("BEQ", "absent")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{PC}")
        b.label("absent")
        b.insn("MOV", "R0, #0x0")
        b.insn("SUB", "R0, #0x1")
        b.insn("POP", "{PC}")
        b.label("chain")
        b.call_addr(prev)
        b.insn("POP", "{PC}")
        return b.assemble(base, pad="nop")

    def count(base, prev):           # SITE3 counter (r0 side): 0 for K (the grant is spent, announce skipped), else the chain
        b = EffectBuilder()
        b.insn("PUSH", "{LR}")
        b.ldr_const(1, _NS_ARM_POOL)
        b.insn("LDR", "R1, [R1, #0x0]")
        b.ldr_const(2, K)
        b.insn("CMP", "R1, R2")
        b.insn("BNE", "chain")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{PC}")
        b.label("chain")
        b.call_addr(prev)
        b.insn("POP", "{PC}")
        return b.assemble(base, pad="nop")

    def match(base, prev):           # SITE4 (r0 = desc+0x12): leave Z and r1 = K on a match; else tail-jump the chain
        b = EffectBuilder()
        b.ldr_const(1, K)
        b.insn("CMP", "R0, R1")
        b.insn("BEQ", "out")
        b.ldr_const(1, prev | 1)
        b.insn("BX", "R1")
        b.label("out")
        b.insn("BX", "LR")
        return b.assemble(base, pad="nop")

    return dict(arm=arm, spent=spent, pred=pred, field=field, count=count, match=match)


def ns_fronts_unfronted(ov, site: int, K: int, G: int, ov3: dict, prev: dict) -> bytes:
    """The 4 bytes *site* would hold without these fronts: the chained previous BL if the site BLs our front."""
    builders = ns_front_builders(K, G)
    o = site - 0x02141700
    cur = bytes(ov[o:o + 4])
    for k, s in _NS_SITES.items():
        if s == site and cur == common_bl(site, ov3[k]):
            for p in prev[k]:
                if bytes(ov[ov3[k] - 0x02141700:ov3[k] - 0x02141700 + len(builders[k](ov3[k], p))]) == builders[k](ov3[k], p):
                    return common_bl(site, p)
    return cur


@dataclass(frozen=True)
class spirit_extra_normal_summon_grant_on_normal_summon_or_flip:
    """'During the turn this card was Normal Summoned or flipped face-up, you can Normal Summon 1 Spirit monster in addition to
    your Normal Summon/Set. (You can only gain this effect once per turn.)' The shared Normal Summon path is reached through
    six ov3 fronts (`ns_front_builders`), one per site, each chaining whatever the site BLs now (`prev`: Sakitama's stub in the
    full chain, Scrap Raptor's on the compact base). The gain is a mandatory cls1 #1 (Maharaghi's NS/flip shape) with cond
    'grant node (side, G, kind 1) absent -> 2' and res 'post (side, G, 1)'; cls1 #0 is the shared Spirit return record
    (Aratama's recipe). The pair goes under the donor over one phantom's TWO rows."""
    keys: tuple[int, int]             # (K granter/spent, G grant)
    fronts: dict                      # key -> ov3 slot
    gy_slot: int
    prev: dict                        # key -> (Sakitama stub, Raptor stub)
    gcond: int
    gres: int
    phantom: int
    template: int                     # Maharaghi: source of the two hi words
    return_slots: tuple
    template_trigger: tuple
    code78_phantom: int               # Normal / Flip Summon membership (code-7-or-8 list)
    donor: int                        # the card's own cid (needed at construction, below)

    def __post_init__(self):
        # The sent-to-GY node front is declared to snoww's switch walker at CONSTRUCTION (what the module did at import), so every
        # other card's whole-chain walk sees it even when this card is not being built.
        from otn_enhanced.cards import snoww as sn
        sn.register_switch_stub(self.gy_slot, 0x1C, {self.donor: 0x021D19BE})

    def compile(self, view, cid) -> Compiled:
        K, G = self.keys
        builders = ns_front_builders(K, G)
        sites = _NS_SITES
        mah = [r for r in rows(view, CLS1) if r[0] == self.template]
        assert len(mah) == 2 and mah[0][2:] == self.return_slots and mah[1][2:] == self.template_trigger, f"Maharaghi cls1 drifted: {mah}"
        gain_slots = (self.gres | 1, 0, self.gcond | 1, 0, 0)
        pair = [(cid, mah[0][1]) + self.return_slots, (cid, mah[1][1]) + gain_slots]

        def site_prev(buf, k):
            site = sites[k]
            cur = bytes(buf[site - 0x02141700:site - 0x02141700 + 4])
            for p in self.prev[k]:
                if cur == common_bl(site, p):
                    return p
                if cur == common_bl(site, self.fronts[k]) and cave3.read_code(None, buf, self.fronts[k], len(builders[k](self.fronts[k], p))) \
                        == builders[k](self.fronts[k], p):
                    return p
            raise AssertionError(f"@{site:#x} is {cur.hex()}: neither Sakitama's nor Raptor's stub -- scrap_raptor (and ninishi) must be applied first")

        stubs = []
        chosen = {}
        for k in builders:
            p = site_prev(view.buf, k)
            chosen[k] = p
            stubs.append((self.fronts[k], builders[k](self.fronts[k], p), f"front {k}"))
        GY_NODE, GY_LIT, GY_ACCEPT = 0x021D13C2, 0x021D15A4, 0x021D1938
        GY_STOCK = bytes.fromhex("78488542")           # ldr r0,[pc,#0x1e0] ; cmp r5,r0
        lit = view.u32(GY_LIT)
        b = EffectBuilder()          # BL'd from the node in place of `ldr r0,=lit ; cmp r5,r0`
        b.ldr_const(0, cid)
        b.insn("CMP", "R5, R0")
        b.insn("BNE", "native")
        b.ldr_const(0, GY_ACCEPT | 1)
        b.insn("BX", "R0")
        b.label("native")
        b.ldr_const(0, lit)
        b.insn("CMP", "R5, R0")
        b.insn("BX", "LR")
        gy = b.assemble(self.gy_slot, pad="nop")
        stubs.append((self.gy_slot, gy, "sent-to-GY node front"))
        b = EffectBuilder()          # cls1 #1 +0C: 2 unless this player already gained the effect this turn (grant node G)
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        b.insn("LDRB", "R0, [R4, #0x7]")
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "ok")
        b.insn("LDRB", "R0, [R4, #0x2]")
        b.call("turnlog_query", R0, 0xB, G, 1)
        b.insn("CMP", "R0, #0x0")
        b.insn("BNE", "no")
        b.label("ok")
        b.insn("MOV", "R0, #0x2")
        b.insn("POP", "{R4, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        stubs.append((self.gcond, b.assemble(self.gcond, pad="nop"), "gain cond"))
        b = EffectBuilder()          # cls1 #1 +04: post the grant (side, G, kind 1) -- expires with the turn
        b.insn("PUSH", "{R4, LR}")
        b.insn("LDRB", "R0, [R0, #0x2]")
        b.call("turnlog_post", R0, G, 1, 0)
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        stubs.append((self.gres, b.assemble(self.gres, pad="nop"), "gain res"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        def install(rom, view):
            recs = list(rows(view, CLS1))
            if [r for r in recs if r[0] == cid] != pair:
                assert not any(r[0] == cid for r in recs), "donor already owns cls1 rows"
                assert sum(r[0] == self.phantom for r in recs) == 2, f"phantom {self.phantom:#06x} lost its 2 rows"
                recs = [r for r in recs if r[0] != self.phantom]
                pos = sum(1 for r in recs if r[0] <= cid)
                recs[pos:pos] = pair
                assert len(recs) == CLS1.count and [r[0] for r in recs] == sorted(r[0] for r in recs)
                for i, r in enumerate(recs):
                    view.pack(CLS1.addr(i), CLS1.fmt, *r)
            for k, site in sites.items():
                view.write(site, common_bl(site, self.fronts[k]))
            assert view.blob(GY_NODE, 4) in (GY_STOCK, common_bl(GY_NODE, self.gy_slot)), f"sent-to-GY node @{GY_NODE:#x} drifted"
            view.write(GY_NODE, common_bl(GY_NODE, self.gy_slot))

        def check(c, rom, view):
            from otn_enhanced.cards import snoww as sn2
            recs = rows(view, CLS1)
            ks = [r[0] for r in recs]
            c.ok(ks == sorted(ks) and self.phantom not in ks and [r for r in recs if r[0] == cid] == pair,
                 "cls1 pair [return, gain] under the donor, phantom spent, sorted")
            for k, site in sites.items():
                fronted = view.blob(site, 4) == common_bl(site, self.fronts[k])
                chained = any(cave3.read_code(rom, view.buf, self.fronts[k], len(builders[k](self.fronts[k], p))) == builders[k](self.fronts[k], p)
                              for p in self.prev[k])
                c.ok(fronted and chained, f"front {k} @{site:#x} -> {self.fronts[k]:#x}, chains Sakitama/Raptor")
            # infernoble (Roland) may front this node with ov3 0x02237E1C; its own verify byte-checks that.
            c.ok(view.blob(GY_NODE, 4) in (common_bl(GY_NODE, self.gy_slot), common_bl(GY_NODE, 0x02237E1C))
                 and cave3.read_code(rom, view.buf, self.gy_slot, len(gy)) == gy, "sent-to-GY node front installed")
            c.eq(sn2._switch_leaf(bytes(view.buf), cid), 0x021D19BE, f"{cid:#06x} reaches the any-location accept")

        return Compiled(tuple(stubs), (Row(LIST_CODE78, (cid,), self.code78_phantom),), installs=(install,), checks=(check,))


@dataclass(frozen=True)
class sent_to_graveyard_draw_while_controlling_face_up_spirit:
    """'When this card is sent to the Graveyard: Draw 1 card. You must control a Spirit monster to activate and to resolve
    this effect.' cls2 {RES, 0, COND, 0, 0} (mandatory, 0x1B8B's shape) over a phantom; COND and RES both demand a face-up
    Spirit on the controller's monster zones (0x021ACFE8 with is_spirit as the predicate), then defer to Cyber Phoenix's draw
    condition 0x021F069D / the draw resolver 0x022065B9. draw-count row {cid, 1} and an any-location leave-mask row
    {cid, 0x0800} (Shadow Mist / Eclipse Wyvern recipe), each over a phantom. The sent-to-GY cid chain front is part of
    `spirit_extra_normal_summon_grant_on_normal_summon_or_flip`."""
    cond: int
    res: int
    phantoms: tuple[int, int, int]      # (cls2, draw-count, leave-mask)

    def compile(self, view, cid) -> Compiled:
        COUNT_MONSTERS, IS_SPIRIT, DRAW_COND, DRAW_RES = 0x021ACFE8, 0x020230D4, 0x021F069C, 0x022065B8

        def spirit_count(b):
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x6]")
            b.insn("EOR", "R0, R1")
            b.ldr_const(1, IS_SPIRIT | 1)
            b.insn("MOV", "R2, #0x0")
            b.insn("SUB", "R2, #0x1")
            b.insn("MOV", "R3, #0x1")
            b.call_addr(COUNT_MONSTERS)

        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        spirit_count(b)
        b.insn("CMP", "R0, #0x0")
        b.insn("BLE", "no")
        b.call_addr(DRAW_COND, R4)
        b.insn("POP", "{R4, PC}")
        b.label("no")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        cond = b.assemble(self.cond, pad="nop")
        b = EffectBuilder()
        b.insn("PUSH", "{R4, LR}")
        b.insn("ADD", "R4, R0, #0x0")
        spirit_count(b)
        b.insn("CMP", "R0, #0x0")
        b.insn("BLE", "done")
        b.call_addr(DRAW_RES, R4)
        b.label("done")
        b.insn("MOV", "R0, #0x0")
        b.insn("POP", "{R4, PC}")
        res = b.assemble(self.res, pad="nop")
        for blob, addr in ((cond, self.cond), (res, self.res)):
            assert_thumb1_only(blob, addr)
        ph2, phd, phm = self.phantoms
        return Compiled(((self.cond, cond, "C4 cond"), (self.res, res, "C4 res")),
                        (Row(CLS2, (cid, 0, self.res | 1, 0, self.cond | 1, 0, 0), ph2),
                         Row(DRAW_COUNT, (cid, 1), phd),
                         Row(LEAVE_MASK, (cid, 0x0800), phm)))



DONOR_CID = 0x0FE3
K = 0x3E51                  # granter / spent key (Sakitama owns 0x3E50)
G = 0x3E52                  # grant: kind 1 on the player slot = "gained this turn"

# The chain each front may sit on: Sakitama's stub (full chain) or Scrap Raptor's (compact test base).
PREV = {
    "arm": (cave3.CAVE3_SK_NSARM, cave3.CAVE3_SR_NSARM),
    "spent": (cave3.CAVE3_SK_NSSPENT, cave3.CAVE3_SR_NSSPENT),
    "pred": (cave3.CAVE3_SK_NSPRED, cave3.CAVE3_SR_NSPRED),
    "field": (cave3.CAVE3_SK_NSFIELD, cave3.CAVE3_SR_NSFIELD),
    "count": (cave3.CAVE3_SK_NSCOUNT, cave3.CAVE3_SR_NSCOUNT),
    "match": (cave3.CAVE3_SK_NSMATCH, cave3.CAVE3_SR_NSMATCH),
}
OV3 = dict(arm=cave3.CAVE3_NK_NSARM, spent=cave3.CAVE3_NK_NSSPENT, pred=cave3.CAVE3_NK_NSPRED,
           field=cave3.CAVE3_NK_NSFIELD, count=cave3.CAVE3_NK_NSCOUNT, match=cave3.CAVE3_NK_NSMATCH,
           gy=cave3.CAVE3_NK_GYNODE)

SPEC = card(
    DONOR_CID,
    spirit_extra_normal_summon_grant_on_normal_summon_or_flip(
        keys=(K, G), fronts={k: v for k, v in OV3.items() if k != "gy"}, gy_slot=OV3["gy"], prev=PREV,
        gcond=ov5_cave.CAVE_NK_GAINCOND, gres=ov5_cave.CAVE_NK_GAINRES, phantom=0x0E2F,
        template=0x14FD,                                           # Maharaghi's NS/flip shapes
        return_slots=(0x0220A901, 0, 0, 0x021E88A9, 0), template_trigger=(0x0220FF51, 0, 0, 0, 0),
        code78_phantom=0x120E, donor=DONOR_CID),
    sent_to_graveyard_draw_while_controlling_face_up_spirit(
        cond=ov5_cave.CAVE_NK_DRAWCOND, res=ov5_cave.CAVE_NK_DRAWRES, phantoms=(0x1B18, 0x0E86, 0x0E1C)),
    archetype_member(FLIPPED_FACE_UP_TABLE, phantom=0x1534),
    card_genre_word(0x0000000001400004))                           # Increase Draw, (Flip), (Spirit)

PROPS = card_props("LIGHT", "Fairy", level=4, atk=800, defense=1800, card_type="Spirit Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_nikitama.nds")


def unfronted(ov, site: int) -> bytes:              # sakitama calls this
    return ns_fronts_unfronted(ov, site, K, G, OV3, PREV)


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
