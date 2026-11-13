"""Sakitama (Spirit / LIGHT / Fairy / Level 4 / 400 / 900) on Grand Tiki Elder 0x13E5.

    Cannot be Special Summoned. Once per turn, during the End Phase, if this card was Normal Summoned or flipped
    face-up this turn: Return this card to the hand. You can only use each of the following effects of "Sakitama" once
    per turn. You can reveal this card in your hand; immediately after this effect resolves, Normal Summon 1 Spirit
    monster from your hand. If this card is Tributed: Target 1 Spirit monster in your GY; add it to your hand.
"""
import struct
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_genre_word, card_props, CLS1, CLS2, CRITERIA, Compiled, Row
from otn_enhanced.effects import cave3, ov5_cave
from otn_enhanced.asm.effect_builder import EffectBuilder, Reg
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import cave3
from dataclasses import dataclass
import ndspy.rom
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class spirit_cannot_special_summon_returns_reveals_hand_to_normal_summon_spirit_and_tributed_returns_spirit_from_gy:
    """Sakitama: Spirit with 'Cannot be Special Summoned' + the shared End-Phase return (one cls1 row, ARM9 flipped-face-up
    list, hand-effect LIST B); ONE cls2 record switching on desc[+3] (0xB = hand reveal that grants an ADDITIONAL Normal
    Summon of a Spirit, else Tributed -> add a Spirit from the GY). The grant rides eight ov3 fronts on the shared Normal
    Summon path, each chaining Scrap Raptor's stub (granter key K = 0x3E50, not the cid: the arm's native spent check is
    kind-agnostic), and a front over Assault Synchron's leave BL for the Tribute arm. The resolver posts the spent mark when
    the native summon resolver finishes (in-game test 1: the grant otherwise outlived the effect). Later cards (Nikitama,
    Scrap Raptor, Ninishi) chain on these fronts; see the card file's `unfronted`."""

    def compile(self, view, cid) -> Compiled:
        import ndspy.code
        from otn_enhanced.effects.common import ARM9_BASE
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid
        K = 0x3E50                  # granter / spent key: > every cid, < 0x4000 (Assault's 0x4000|ref keys)

        CLS_FMT = "<HHIIIII"
        CLS1_BASE, CLS1_COUNT = 0x022860D4, 0x535
        CLS2_BASE, CLS2_COUNT = 0x02275C04, 0x2B9
        CRIT_BASE, CRIT_COUNT, CRIT_FMT = 0x022713C4, 0x56C, "<HHII"
        PH_CLS1, PH_CLS2, PH_CRIT = 0x1500, 0x1774, 0x1446
        ASURA_PRIEST, IZANAMI = 0x1505, 0x1DFD
        RETURN_SLOTS = (0x0220A901, 0, 0, 0x021E88A9, 0)
        CRIT_ROW = (DONOR_CID, 0x0007, 0x022409C9, 0x00010002)

        from otn_enhanced.effects.common import ARM9_BASE
        HANDFX_B, HANDFX_B_COUNT, PH_HANDFX = 0x0209BC8C, 0x24, 0x1774
        FLIP_LIST, FLIP_COUNT, PH_FLIP = 0x0209BB5C, 0x13, 0x1535

        # engine entry points (Thumb; called by `bl`)
        TLQ, ANYQ, POST = 0x021A14E8, 0x021A1430, 0x021D2584
        IS_SPIRIT = 0x020230D4
        REVEAL, SUMMONABLE, NS_GATE = 0x021D2598, 0x0225D6D4, 0x021B9E6C
        PARAM, CRIT_COUNT_FN = 0x02234E78, 0x02243FE0
        PLAYER, STRIDE, HAND_ARR = 0x0229AC94, 0xB3C, 0x124
        DUEL = 0x0229DD14                   # +0x34 turn player, +0x48 phase (2 MP1, 4 MP2)
        ARM_POOL = 0x02261F84               # the granter arm's cid literal
        NS_RESOLVER, GY_RESOLVER, OFFFIELD_PICKER = 0x0220D80D, 0x02208181, 0x02235605
        SELECTOR = 0x0220D7B4

        # ---- hook sites: (site, stock-or-chained before-image target, stub) -----------------------------------
        SEL_SITE = 0x0220D81C
        SITE1, SITE2, SITE3_PRED, SITE3_FIELD, SITE3_COUNT, SITE4_MATCH = (
            0x021B9634, 0x021B9F9C, 0x02261E3E, 0x02261E68, 0x02261E92, 0x0226515C)
        LEAVE_SITE = 0x021C93D0

        # ---- slots (registered in cave3.py / ov5_cave.py) -----------------------------------------------------
        OV3 = dict(filter=cave3.CAVE3_SK_FILTER, select=cave3.CAVE3_SK_SELECT, arm=cave3.CAVE3_SK_NSARM,
                   spent=cave3.CAVE3_SK_NSSPENT, pred=cave3.CAVE3_SK_NSPRED, field=cave3.CAVE3_SK_NSFIELD,
                   count=cave3.CAVE3_SK_NSCOUNT, match=cave3.CAVE3_SK_NSMATCH)
        OV5 = dict(cond=(ov5_cave.CAVE_SK_COND, 0xF0), cost=(ov5_cave.CAVE_SK_COST, 0x30),
                   res=(ov5_cave.CAVE_SK_RES, 0x30), tgt=(ov5_cave.CAVE_SK_TGT, 0x20),
                   leave=(ov5_cave.CAVE_SK_LEAVE, 0x30))
        # Card-only stubs ship in ov5 (user: "move to ov5 and ship it"); the eight shared Normal-Summon
        # path stubs above stay in ov3 (every Normal Summon runs them). Builds 2-4 tested from an all-ov3 test home.
        CARD = OV5
        ASSAULT_HOOK = ov5_cave.CAVE_ASSAULT_LEAVEHOOK

        def _hand_word(b: EffectBuilder, dst: Reg, idx: Reg, side: Reg, tmp: Reg) -> None:
            """dst = player[side].hand[idx] word (clobbers tmp)."""
            b.insn("MOV", f"{dst!r}, #0x1")
            b.insn("AND", f"{dst!r}, {side!r}")
            b.ldr_const(int(tmp), STRIDE)
            b.insn("MUL", f"{dst!r}, {tmp!r}")
            b.ldr_const(int(tmp), PLAYER)
            b.insn("ADD", f"{dst!r}, {tmp!r}, {dst!r}")
            b.insn("LSL", f"{tmp!r}, {idx!r}, #0x2")
            b.insn("ADD", f"{dst!r}, {dst!r}, {tmp!r}")
            b.ldr_const(int(tmp), HAND_ARR)
            b.insn("LDR", f"{dst!r}, [{dst!r}, {tmp!r}]")

        def filter_stub(base: int) -> bytes:
            """C3 resolver filter (side, zone, idx) -> 0x10 (Normal Summon) for a Spirit in hand, else 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("CMP", "R1, #0xB")
            b.insn("BNE", "zero")
            _hand_word(b, R3, R2, R0, R1)
            b.insn("LSL", "R0, R3, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call_addr(IS_SPIRIT)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.insn("MOV", "R0, #0x10")
            b.insn("POP", "{R4, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def select_stub(base: int) -> bytes:
            """BL'd from the resolver @0x0220D81C in place of 0x0220D7B4(cid): the donor gets the Spirit filter."""
            b = EffectBuilder()
            b.ldr_const(1, DONOR_CID)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "native")
            b.ldr_const(0, cave3.CAVE3_SK_FILTER | 1)
            b.insn("BX", "LR")
            b.label("native")
            b.ldr_const(1, SELECTOR | 1)
            b.insn("BX", "R1")
            return b.assemble(base, pad="nop")


        def _grant_live(b: EffectBuilder, side: Reg, fail: str) -> None:
            """Branch to *fail* unless kind-1 grant on DONOR exists and K is unspent (any-kind node on K)."""
            b.call_addr(TLQ, side, 0xB, DONOR_CID, 1)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", fail)
            b.call_addr(ANYQ, side, 0xB, K)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", fail)


        def nsarm_stub(base: int) -> bytes:
            """SITE1 (r5 side, r4 hand cid or 0). Exits through the host's pop {r3-r7,pc}, like Raptor's."""
            b = EffectBuilder()
            b.insn("CMP", "R4, #0x0")
            b.insn("BEQ", "grant")
            b.call_addr(IS_SPIRIT, R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "chain")
            b.label("grant")
            _grant_live(b, R5, "chain")
            b.ldr_const(0, K)
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            b.label("chain")
            b.call_addr(cave3.CAVE3_SR_NSARM)
            return b.assemble(base, pad="nop")


        def nsspent_stub(base: int) -> bytes:
            """SITE2 'has Normal Summoned this turn' chain (r0 previous answer, r5 side, r4 = 1)."""
            b = EffectBuilder()
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "keep")
            b.call_addr(ANYQ, R5, 0xB, K)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "chain")
            b.label("keep")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            b.label("chain")
            b.call_addr(cave3.CAVE3_SR_NSSPENT, 0)
            return b.assemble(base, pad="nop")


        def nspred_stub(base: int) -> bytes:
            """SITE3 predicate (r0 hand cid, r4 summon desc, [r4] side). Takes the arm ONLY while the grant is
            live, so a Spirit without it still reaches every later granter arm (Ultimate Offering etc.)."""
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.call_addr(IS_SPIRIT)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "chain")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.call("turnlog_query", R0, 0xB, DONOR_CID, 1)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "chain")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.call_addr(ANYQ, R0, 0xB, K)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "chain")
            b.ldr_const(1, K)
            b.ldr_const(2, ARM_POOL)
            b.insn("STR", "R1, [R2, #0x0]")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{PC}")
            b.label("chain")
            b.insn("LDRH", "R0, [R4, #0xE]")
            b.call_addr(cave3.CAVE3_SR_NSPRED)
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        def nsfield_stub(base: int) -> bytes:
            """SITE3 'where is the granter' (r0 side, r1 pool cid): K -> 0 if the grant node exists, else -1."""
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.ldr_const(2, K)
            b.insn("CMP", "R1, R2")
            b.insn("BNE", "chain")
            b.call("turnlog_query", R0, 0xB, DONOR_CID, 1)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "absent")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{PC}")
            b.label("absent")
            b.insn("MOV", "R0, #0x0")
            b.insn("SUB", "R0, #0x1")
            b.insn("POP", "{PC}")
            b.label("chain")
            b.call_addr(cave3.CAVE3_SR_NSFIELD)
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        def nscount_stub(base: int) -> bytes:
            """SITE3 counter (r0 side): 0 for K (-> grant spent, announce skipped), else Raptor's chain."""
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.ldr_const(1, ARM_POOL)
            b.insn("LDR", "R1, [R1, #0x0]")
            b.ldr_const(2, K)
            b.insn("CMP", "R1, R2")
            b.insn("BNE", "chain")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{PC}")
            b.label("chain")
            b.call_addr(cave3.CAVE3_SR_NSCOUNT)
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        def nsmatch_stub(base: int) -> bytes:
            """SITE4 (r0 = desc+0x12): leave Z and r1 = K on a match; else tail-jump Raptor's (bx keeps LR)."""
            b = EffectBuilder()
            b.ldr_const(1, K)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "out")
            b.ldr_const(1, cave3.CAVE3_SR_NSMATCH | 1)
            b.insn("BX", "R1")
            b.label("out")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        OV3_BUILDERS = dict(filter=filter_stub, select=select_stub, arm=nsarm_stub, spent=nsspent_stub,
                            pred=nspred_stub, field=nsfield_stub, count=nscount_stub, match=nsmatch_stub)


        # ======================================================================================================
        # ov5 stubs (card-only: reached through Sakitama's own cls2 record / the Assault-owned leave site)
        # ======================================================================================================
        def cond_stub(base: int) -> bytes:
            """r7 = this side's player struct, computed once (callee-saved across the loop's calls)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x7]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "ok")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xB")
            b.insn("BNE", "c4")
            b.ldr_const(0, DUEL)
            b.insn("LDR", "R1, [R0, #0x34]")
            b.insn("CMP", "R1, R5")
            b.insn("BNE", "no")
            b.insn("LDR", "R1, [R0, #0x48]")
            b.insn("CMP", "R1, #0x2")
            b.insn("BEQ", "phase_ok")
            b.insn("CMP", "R1, #0x4")
            b.insn("BNE", "no")
            b.label("phase_ok")
            b.call("turnlog_query", R5, 0xB, DONOR_CID, 1)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            b.call_addr(NS_GATE, R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R7, #0x1")
            b.insn("AND", "R7, R5")
            b.ldr_const(0, STRIDE)
            b.insn("MUL", "R7, R0")
            b.ldr_const(0, PLAYER)
            b.insn("ADD", "R7, R0, R7")
            b.insn("MOV", "R6, #0x0")
            b.label("loop")
            b.insn("LDR", "R0, [R7, #0xC]")
            b.insn("CMP", "R6, R0")
            b.insn("BGE", "no")
            b.insn("LSL", "R0, R6, #0x2")
            b.insn("ADD", "R0, R7, R0")
            b.ldr_const(1, HAND_ARR)
            b.insn("LDR", "R0, [R0, R1]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call_addr(IS_SPIRIT)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "next")
            b.insn("LSL", "R0, R6, #0x2")
            b.insn("ADD", "R0, R7, R0")
            b.ldr_const(1, HAND_ARR)
            b.insn("LDR", "R2, [R0, R1]")
            b.insn("LSL", "R1, R2, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R2, R2, #0x1")
            b.insn("LSR", "R2, R2, #0x18")
            b.insn("LSL", "R2, R2, #0x1")
            b.insn("ADD", "R1, R1, R2")
            b.call_addr(SUMMONABLE, R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "ok")
            b.label("next")
            b.insn("ADD", "R6, #0x1")
            b.insn("B", "loop")
            b.label("c4")
            b.call("turnlog_query", R5, 0xB, DONOR_CID, 2)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            b.call_addr(PARAM, R4)
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x6]")
            b.insn("EOR", "R0, R1")
            b.call_addr(CRIT_COUNT_FN, R0, DONOR_CID)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")
            b.label("ok")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def cost_stub(base: int) -> bytes:
            """C3: reveal self, post kind 1 (OPT + grant). C4: post kind 2 (OPT). Always done (1)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("MOV", "R2, #0x2")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xB")
            b.insn("BNE", "post")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0xC]")
            b.call_addr(REVEAL)
            b.insn("MOV", "R2, #0x1")
            b.label("post")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call("turnlog_post", R0, DONOR_CID, R2, 0)
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def res_stub(base: int) -> bytes:
            """C3: run the native NS resolver; when it returns 0 (resolution over -- phase 0x7D returns 0 only once
            [0x02298A28+0x1A] == 0, i.e. the summon has completed) post the spent mark (side, K, 1) so the grant
            cannot outlive the effect. IN-GAME TEST 1: a 0x0220D80C-launched summon never reaches the consume path,
            so without this the grant stayed live and ate the next regular Normal Summon of a Spirit."""
            b = EffectBuilder()
            b.insn("LDRB", "R1, [R0, #0x3]")
            b.insn("CMP", "R1, #0xB")
            b.insn("BNE", "c4")
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(NS_RESOLVER & ~1)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "out")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call("turnlog_post", R0, K, 1, 0)
            b.insn("MOV", "R0, #0x0")
            b.label("out")
            b.insn("POP", "{R4, PC}")
            b.label("c4")
            b.ldr_const(1, GY_RESOLVER)
            b.insn("BX", "R1")
            return b.assemble(base, pad="nop")


        def tgt_stub(base: int) -> bytes:
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xB")
            b.insn("BNE", "c4")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("c4")
            b.ldr_const(3, OFFFIELD_PICKER)
            b.insn("BX", "R3")
            return b.assemble(base, pad="nop")


        STOCK_LEAVE = bytes.fromhex("11980028")     # 0x021C93D0 stock: ldr r0,[sp,#0x44] ; cmp r0,#0


        def leave_stub(base: int, chain: bool = True) -> bytes:
            """BL'd from 0x021C93D0; dispatcher frame + 8 (two pushed words). chain=True: in front of Assault's
            stub. chain=False (a base WITHOUT assault_synchron): replay the two displaced stock
            instructions itself -- `bx lr` keeps the flags for the native `beq` @0x021C93D4."""
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2}")
            b.ldr_const(1, DONOR_CID)
            b.insn("CMP", "R4, R1")
            b.insn("BNE", "go")
            b.insn("LDR", "R0, [SP, #0x34]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "go")
            b.insn("LDR", "R0, [SP, #0x14]")
            b.insn("MOV", "R1, #0x1")
            b.insn("LSL", "R1, R1, #0xC")
            b.insn("AND", "R0, R1")
            b.insn("BEQ", "go")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x20]")
            b.label("go")
            b.insn("POP", "{R1, R2}")
            if chain:
                b.ldr_const(0, ASSAULT_HOOK | 1)
                b.insn("BX", "R0")
            else:
                b.insn("LDR", "R0, [SP, #0x44]")
                b.insn("CMP", "R0, #0x0")
                b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        OV5_BUILDERS = dict(cond=cond_stub, cost=cost_stub, res=res_stub, tgt=tgt_stub, leave=leave_stub)

        CLS2_RECORD = (DONOR_CID, 0, CARD["res"][0] | 1, 0, CARD["cond"][0] | 1,
                       CARD["cost"][0] | 1, CARD["tgt"][0] | 1)

        def _bl(src: int, dst: int) -> bytes:
            off = (dst - (src + 4)) >> 1
            assert -0x200000 <= off < 0x200000
            return struct.pack("<HH", 0xF000 | ((off >> 11) & 0x7FF), 0xF800 | (off & 0x7FF))


        HOOKS = (
            (SEL_SITE, SELECTOR, OV3["select"], "resolver filter selector"),
            (SITE1, cave3.CAVE3_SR_NSARM, OV3["arm"], "site 1 granter arm"),
            (SITE2, cave3.CAVE3_SR_NSSPENT, OV3["spent"], "site 2 has-Normal-Summoned"),
            (SITE3_PRED, cave3.CAVE3_SR_NSPRED, OV3["pred"], "site 3 predicate"),
            (SITE3_FIELD, cave3.CAVE3_SR_NSFIELD, OV3["field"], "site 3 granter lookup"),
            (SITE3_COUNT, cave3.CAVE3_SR_NSCOUNT, OV3["count"], "site 3 counter"),
            (SITE4_MATCH, cave3.CAVE3_SR_NSMATCH, OV3["match"], "site 4 granter match"),
            (LEAVE_SITE, ov5_cave.CAVE_ASSAULT_LEAVEHOOK, CARD["leave"][0], "C4 Tribute arm front"),
        )

        def _rows(ov, base, count, fmt):
            st = struct.calcsize(fmt)
            return [struct.unpack_from(fmt, ov, base - RAM_BASE + i * st) for i in range(count)]


        def _templates(ov) -> tuple:
            """The cls1 return row (from Asura Priest) and the criteria row's template (Izanami), asserted."""
            asura = [r for r in _rows(ov, CLS1_BASE, CLS1_COUNT, CLS_FMT) if r[0] == ASURA_PRIEST]
            assert len(asura) == 1 and asura[0][2:] == RETURN_SLOTS, f"Asura Priest cls1 drifted: {asura}"
            iz = [r for r in _rows(ov, CRIT_BASE, CRIT_COUNT, CRIT_FMT) if r[0] == IZANAMI]
            assert iz == [(IZANAMI,) + CRIT_ROW[1:]], f"Izanami criteria drifted: {iz}"
            return (DONOR_CID, asura[0][1]) + RETURN_SLOTS

        def _hook(ov, site, before, after, what) -> None:
            o = site - RAM_BASE
            cur, old, new = bytes(ov[o:o + 4]), _bl(site, before), _bl(site, after)
            assert cur in (old, new), f"E  @{site:#x} is {cur.hex()}, expected bl {before:#x} -- {what}"
            ov[o:o + 4] = new
            print(f"E  @{site:#010x} bl {before:#010x} -> bl {after:#010x}  {what}")

        def _arm9_lists(rom) -> list[str]:
            """Swap the donor into hand-effect LIST B and the flipped-face-up list (sorted, count-neutral)."""
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
            d = bytearray(sec.data)
            log = []
            for base, count, ph, what in ((HANDFX_B, HANDFX_B_COUNT, PH_HANDFX, "hand-effect LIST B"),
                                          (FLIP_LIST, FLIP_COUNT, PH_FLIP, "flipped-face-up list")):
                cur = list(struct.unpack_from(f"<{count}H", d, base - ARM9_BASE))
                assert cur == sorted(cur), f"{what} not sorted"
                if DONOR_CID not in cur:
                    assert ph in cur, f"{what}: phantom {ph:#06x} already spent"
                    cur = sorted([c for c in cur if c != ph] + [DONOR_CID])
                    struct.pack_into(f"<{count}H", d, base - ARM9_BASE, *cur)
                log.append(f"G  {what} @{base:#010x}: 0x{DONOR_CID:04X} in, 0x{ph:04X} out")
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            return log

        chain = view.blob(LEAVE_SITE, 4) != STOCK_LEAVE      # Assault Synchron present on this base?
        stubs = [(OV3[k], OV3_BUILDERS[k](OV3[k]), f"ov3 {k}") for k in OV3_BUILDERS]
        for k in ("cond", "cost", "res", "tgt"):
            stubs.append((CARD[k][0], OV5_BUILDERS[k](CARD[k][0]), f"ov5 {k}"))
        stubs.append((CARD["leave"][0], leave_stub(CARD["leave"][0], chain), "ov5 leave"))
        for addr, blob, what in stubs:
            assert_thumb1_only(blob, addr)
        for k in ("cond", "cost", "res", "tgt", "leave"):
            assert len([s for s in stubs if s[0] == CARD[k][0]][0][1]) <= CARD[k][1], k

        def install(rom, view):
            ov = view.buf
            for site, before, after, what in HOOKS:
                if site != LEAVE_SITE:
                    _hook(ov, site, before, after, what)
            o = LEAVE_SITE - RAM_BASE
            if chain:
                _hook(ov, LEAVE_SITE, ov5_cave.CAVE_ASSAULT_LEAVEHOOK, CARD["leave"][0], "C4 Tribute arm front")
            else:
                ov[o:o + 4] = _bl(LEAVE_SITE, CARD["leave"][0])
            _arm9_lists(rom)

        def check(c, rom, view):
            from otn_enhanced.cards import nikitama as _nk      # ships later; fronts six of these sites
            for site, _before, after, what in HOOKS:
                c.ok(code_reaches(rom, site, after), f"hook @{site:#x} reaches {after:#x} ({what}, directly or via later fronts)")
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            d = next(s for s in mc.sections if s.ramAddress == ARM9_BASE).data
            for base, count, ph, what in ((HANDFX_B, HANDFX_B_COUNT, PH_HANDFX, "hand-effect LIST B"),
                                          (FLIP_LIST, FLIP_COUNT, PH_FLIP, "flipped-face-up list")):
                cur = list(struct.unpack_from(f"<{count}H", d, base - ARM9_BASE))
                c.ok(DONOR_CID in cur and ph not in cur and cur == sorted(cur), what)

        return Compiled(
            tuple(stubs),
            rows=(Row(CLS1, _templates(view.buf), PH_CLS1), Row(CLS2, CLS2_RECORD, PH_CLS2), Row(CRITERIA, CRIT_ROW, PH_CRIT)),
            installs=(install,), checks=(check,))


sakitama_effects = spirit_cannot_special_summon_returns_reveals_hand_to_normal_summon_spirit_and_tributed_returns_spirit_from_gy

SPEC = card(0x13E5, sakitama_effects(), card_genre_word(0x0000000001400040))     # Recover from GY, (Flip), (Spirit)

PROPS = card_props("LIGHT", "Fairy", level=4, atk=400, defense=900, card_type="Spirit Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_sakitama.nds")

# (site, what the site BLs without Sakitama, Sakitama's front): scrap_raptor / dsl read `unfronted`.
_FRONTS = ((0x0220D81C, 0x0220D7B4, cave3.CAVE3_SK_SELECT),
           (0x021B9634, cave3.CAVE3_SR_NSARM, cave3.CAVE3_SK_NSARM),
           (0x021B9F9C, cave3.CAVE3_SR_NSSPENT, cave3.CAVE3_SK_NSSPENT),
           (0x02261E3E, cave3.CAVE3_SR_NSPRED, cave3.CAVE3_SK_NSPRED),
           (0x02261E68, cave3.CAVE3_SR_NSFIELD, cave3.CAVE3_SK_NSFIELD),
           (0x02261E92, cave3.CAVE3_SR_NSCOUNT, cave3.CAVE3_SK_NSCOUNT),
           (0x0226515C, cave3.CAVE3_SR_NSMATCH, cave3.CAVE3_SK_NSMATCH),
           (0x021C93D0, ov5_cave.CAVE_ASSAULT_LEAVEHOOK, ov5_cave.CAVE_SK_LEAVE))


def _bl(src: int, dst: int) -> bytes:
    off = (dst - (src + 4)) >> 1
    assert -0x200000 <= off < 0x200000
    return struct.pack("<HH", 0xF000 | ((off >> 11) & 0x7FF), 0xF800 | (off & 0x7FF))


def unfronted(ov, site: int) -> bytes:
    """The 4 bytes *site* would hold without Sakitama: the chained before-image if the site BLs Sakitama's front, else
    whatever is there."""
    from otn_enhanced.cards import nikitama           # ships later; fronts six of these sites
    cur = nikitama.unfronted(ov, site)
    for s, before, after in _FRONTS:
        if s == site and cur == _bl(site, after):
            return _bl(site, before)
    return cur


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
