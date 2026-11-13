"""Overtex Qoatlus (DARK / Dinosaur / Level 7 / 2700 / 2100) on Prevent Rat 0x10A5.

    Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by shuffling 5 of your banished
    Dinosaur-Type monsters into the Main Deck.
    Once per turn, when your opponent activates a Spell/Trap Card (Quick Effect): You can destroy 1 Dinosaur-Type
    monster in your hand or face-up on your field, and if you do, negate the activation, and if you do that, destroy
    that card.
    If this card is sent to the Graveyard by a card effect: You can add 1 "Evolution Pill" Spell Card from your Deck
    to your hand. You can only use this effect of "Overtex Qoatlus" once per turn.
"""
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
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
from otn_enhanced.effects.common import keys
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class hand_special_summon_shuffling_five_banished_dinosaurs_negate_spell_trap_by_destroying_dinosaur_and_add_evolution_pill:
    """Overtex Qoatlus (Prevent Rat 0x10A5): cannot be Normal Summoned/Set; hand Special Summon by shuffling 5 banished non-Extra-Deck
    Dinosaurs into the Deck (Tyranno's recipe with the payment machine 0x0226292D replaced by a registry-row wrapper); once per turn
    when the opponent activates a Spell/Trap (Quick Effect): destroy 1 Dinosaur in hand or face-up, negate and destroy that card
    (cls3 + spell speed 2 via a speed-lookup front chained to Miscellaneousaurus's); if sent to the GY by a card effect: add 1
    "Evolution Pill" Spell from the Deck (cls2 + leave-mask row, Shadow Mist's sent-to-GY chain node re-fronted, miss-timing blocks
    B -> C, a timing-class arm, Archosaur's Pill predicate). Original code embedded verbatim."""

    def __post_init__(self):
        # Declared to snoww's switch walker at CONSTRUCTION, as the module did at import.
        from otn_enhanced.cards import snoww as sn
        sn.register_switch_stub(0x021F0680, 28, {0x10A5: 0x021F0680 + 12})

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.cards import shadow_mist as _sm, snoww as _snoww
        from otn_enhanced.effects import criteria_row_hook as crh, tg_table, timing_class_hook as tch
        from otn_enhanced.effects.common import insert_row, read_thunk_list as _read_thunk_list, swap_in_list as _swap_in_list
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid
        CRIT_PHANTOM = 0x0E92               # one criteria row, no card_prop, claimed nowhere
        PROC_PHANTOM = 0x18B9               # registry row (0x02261F8D) + class-2 list, no card_prop

        # --- A / B: overlay-3 tables ------------------------------------------------------------
        CRIT_BASE, CRIT_COUNT, CRIT_FMT = 0x022713C4, 0x56C, "<HHII"
        REG_BASE, REG_COUNT, REG_FMT = 0x0228F158, 133, "<II"

        # --- C: ARM9 nomi class-2 list --------------------------------------------------------------
        NOMI_LIST, NOMI_POOL, NOMI_COUNT_IMM = 0x0209BE9C, 0x0202321C, 0x020231E0
        DOOM_DOZER = 0x19CA

        # --- D / P: ov5 --------------------------------------------------------------------------
        SSCOND, SSCOND_RESERVE = ov5_cave.CAVE_OQ_SSCOND, 0x40
        PAY, PAY_RESERVE = ov5_cave.CAVE_OQ_PAY, 0xC0
        CRIT, CRIT_RESERVE = ov5_cave.CAVE_OQ_CRIT, 0xA0
        REG_ROW = (DONOR_CID, PAY | 1)
        CRIT_ROW = (DONOR_CID, 0xFFFF, CRIT | 1, 0x48000002)

        REC = 0x02298A28                    # summon record: +2 side, +0xE cid, +0x24 state, +0x26 count/index
        PAY_NATIVE = 0x0226292D
        PICKS = 0x0229DD94                  # [+0x34] = number of picks made
        COUNT = 5

        # --- C3 --------------------------------------------------------------------------------------
        CLS_FMT = "<HHIIIII"
        MASK_BASE, MASK_COUNT, MASK_FMT = 0x0226EC1C, 0x98, "<Hh"
        MASK_ROW, MASK_PHANTOM = (DONOR_CID, 0x0A04), 0x174E
        CLS2_BASE, CLS2_COUNT, CLS2_PHANTOM = 0x02275C04, 0x2B9, 0x14DD
        C3COND, C3SLOT4, C3_RESERVE = ov5_cave.CAVE_OQ_C3COND, ov5_cave.CAVE_OQ_C3SLOT4, 0x30
        ADD_TO_HAND = 0x02207EF5
        CLS2_REC = (DONOR_CID, 0, ADD_TO_HAND, 0, C3COND | 1, C3SLOT4 | 1, 0)
        ACTING_DESC = 0x0229A9FC            # +0x50 = the running activation's descriptor (scoped per slot call)
        DECK_WALKER, TYPE_ADD, PILL_WORD = 0x0223BC3D, 2, 0x00000004
        PILLS = (0x1AA3, 0x1715, 0x1319)    # asserted against animadorned_archosaur.PILLS in verify
        TURNLOG_QUERY, TURNLOG_POST = 0x021A14E9, 0x021D2585
        HAVE_TARGET, TAG_YOU_CAN = 0x021F0821, 0x021E51E5
        C3_KIND = 2                          # C2 keeps kind 1 free

        GY_NODE = _sm.GATE_NODE              # 0x021D13CC, Shadow Mist's re-keyed node
        GY_STUB = 0x021F0680                 # ov3: tail of Tyranno's dead 0x0E46 body (28 B free, all used)
        GY_STUB_LEN = 28
        MISS_B, MISS_C = _sm.MISS_BLOCK_B, 0x021B5840     # C = tail of the 0x1827 dead block (8 B free)

        def _o(addr: int) -> int:
            return addr - RAM_BASE


        def _a9(addr: int) -> int:
            return addr - 0x02000000


        # ---------------------------------------------------------------------------- stubs ----
        def sscond_stub(base: int) -> bytes:
            """D. r0 = side -> nonzero iff the hand-SS offer should appear (0x0225D0D0 with count 5)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(0x021B9ECC, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(0x021AD870, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(0x02243FE0, R4, DONOR_CID, 0, via=R3)
            b.insn("CMP", f"R0, #0x{COUNT:X}")
            b.insn("BLT", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def pay_stub(base: int) -> bytes:
            """P. The registry handler for 0x10A5 (no args; returns 0 = call again, 1 = done)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.ldr_const(4, REC)
            b.insn("LDRH", "R0, [R4, #0x24]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "s0")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "s2")
            b.call_addr(PAY_NATIVE, via=R3)
            b.insn("POP", "{R4, PC}")
            b.label("s0")
            b.call_addr(0x021D28A4, via=R3)
            b.call_addr(0x0219A6F4, 0xD6, via=R3)
            b.insn("LDRH", "R0, [R4, #0xE]")
            b.call("get_race", via=R3)
            b.call_addr(0x0219A7B8, via=R3)
            b.call_addr(0x0219A7F8, COUNT, via=R3)
            b.insn("MOV", f"R0, #0x{COUNT:X}")
            b.insn("STRH", "R0, [R4, #0x26]")
            b.insn("MOV", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x24]")
            b.insn("LDRH", "R0, [R4, #0x2]")
            b.call_addr(0x0219A818, R0, 1, via=R3)
            b.insn("B", "ret0")
            b.label("s2")
            b.insn("LDRH", "R0, [R4, #0x26]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x26]")
            b.ldr_const(2, PICKS)
            b.insn("LDR", "R2, [R2, #0x34]")
            b.insn("CMP", "R0, R2")
            b.insn("BGT", "done")
            b.call_addr(0x0219C94C, via=R3)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R1, R1, R0")
            b.insn("LDRH", "R0, [R4, #0x2]")
            b.call_addr(0x021C727C, via=R3)
            b.insn("B", "ret0")
            b.label("done")
            b.insn("LDRH", "R0, [R4, #0x2]")
            b.call_addr(0x021D269C, via=R3)
            b.insn("MOV", "R0, #0x3")
            b.insn("STRH", "R0, [R4, #0x24]")
            b.label("ret0")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def crit_stub(base: int) -> bytes:
            """A/G. Criteria handler (r0 = row, r1 = side), mode-switched on the acting descriptor.

            C3 (Qoatlus's cls2 activation running): Deck walk, word 0x4, Archosaur's Pill predicate.
            Otherwise (C1 legality + payment picker): 0x0223DB24 with r2 = PRED instead of 0.  PRED follows.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2, R3, R4, LR}")     # [sp] / [sp+4] = the walker's two stack args
            b.ldr_const(3, ACTING_DESC)
            b.insn("LDR", "R3, [R3, #0x50]")
            b.insn("CMP", "R3, #0x0")
            b.insn("BEQ", "banish")
            b.insn("LDRH", "R2, [R3, #0x0]")
            b.ldr_const(4, DONOR_CID)
            b.insn("CMP", "R2, R4")
            b.insn("BNE", "banish")
            b.insn("LDRB", "R2, [R3, #0x5]")
            b.insn("CMP", "R2, #0x2")
            b.insn("BNE", "banish")
            b.insn("MOV", f"R2, #{PILL_WORD}")
            b.insn("STR", "R2, [SP, #0x0]")
            b.insn("MOV", f"R2, #{TYPE_ADD}")
            b.insn("STR", "R2, [SP, #0x4]")
            b.insn("LDRH", "R2, [R0, #0x0]")           # row cid
            b.insn("ADD", "R0, R1, #0x0")              # side
            b.insn("ADD", "R1, R2, #0x0")
            b.ldr_const(2, ov5_cave.CAVE_ARCH_PRED | 1)
            b.insn("MOV", "R3, #0x0")
            b.ldr_const(4, DECK_WALKER)
            b.insn("BLX", "R4")
            b.insn("POP", "{R1, R2, R3, R4, PC}")
            b.label("banish")
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDR", "R0, [R2, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")            # criteria word (race / kind filter)
            b.insn("MOV", "R0, #0x8")
            b.insn("STR", "R0, [SP, #0x4]")            # type 8, as 0x0223DB24
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("LDRH", "R1, [R2, #0x0]")
            b.ldr_const(2, _pred_base(base) | 1)
            b.insn("MOV", "R3, #0x0")
            b.ldr_const(4, 0x0223C6AD)
            b.insn("BLX", "R4")
            b.insn("POP", "{R1, R2, R3, R4, PC}")
            return b.assemble(base, pad="nop")


        def _pred_base(crit_base: int) -> int:
            return crit_base + 0x70


        def pred_stub(base: int) -> bytes:
            """A. Walker predicate (r0 side, r1 zone, r2 idx, r3 row cid, [sp] &card word, [sp+4] list): not Extra Deck."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call_addr(0x0202307C, via=R3)
            b.insn("MOV", "R1, #0x1")
            b.insn("EOR", "R0, R1")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def _ov5_blobs() -> list[tuple[str, int, bytes, int]]:
            c = crit_stub(CRIT)
            assert len(c) <= _pred_base(CRIT) - CRIT, f"crit stub {len(c)} B overruns PRED"
            c += b"\x00" * (_pred_base(CRIT) - CRIT - len(c))
            return [("D  hand-SS cond", SSCOND, sscond_stub(SSCOND), SSCOND_RESERVE),
                    ("P  payment", PAY, pay_stub(PAY), PAY_RESERVE),
                    ("A  criteria handler + predicate", CRIT, c + pred_stub(_pred_base(CRIT)), CRIT_RESERVE)]


        # ------------------------------------------------------------------------------- C3 ----
        def c3_cond_stub(base: int) -> bytes:
            """F +0C: turn log kind 2 clear -> native have-target 0x021F0821 with (desc, r1) intact."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_query(R0, DONOR_CID, C3_KIND, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "used")
            b.call_addr(HAVE_TARGET, R4, R5, via=R6)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("used")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        def c3_slot4_stub(base: int) -> bytes:
            """F +10: "You can"; only a Yes stamps the lock."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(TAG_YOU_CAN, via=R2)
            b.insn("CMP", "R0, #0x1")
            b.insn("BNE", "out")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_post(R0, DONOR_CID, C3_KIND, via=R4)
            b.insn("ADD", "R0, R5, #0x0")
            b.label("out")
            b.insn("POP", "{R4, R5, PC}")
            return b.assemble(base, pad="nop")


        def gy_stub(base: int = GY_STUB) -> bytes:
            """H. BL'd from 0x021D13CC inside 0x021D1300's frame (r5 = cid, r1 = 0x1185); returns Z = accept.

            r0/r1 are dead at the node (both exits reload them); LR is 0x021D1300's pushed one.
            """
            b = EffectBuilder()
            b.insn("SUB", "R1, #0x66")
            b.insn("CMP", "R5, R1")
            b.insn("BEQ", "ret")
            b.insn("SUB", "R1, #0x7A")
            b.insn("CMP", "R5, R1")
            b.insn("BNE", "ret")
            b.insn("LDR", "R1, [SP, #0x34]")
            b.insn("SUB", "R1, #0xB")
            b.insn("LDR", "R0, [SP, #0x10]")
            b.insn("SUB", "R0, #0x1")
            b.insn("ORR", "R1, R0")
            b.insn("LSR", "R1, R1, #0x1F")
            b.label("ret")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def _b(src: int, dst: int) -> int:
            off = (dst - (src + 4)) >> 1
            assert -1024 <= off <= 1023, f"B out of range {src:#x}->{dst:#x}"
            return 0xE000 | (off & 0x7FF)


        def miss_block_b() -> bytes:
            """J. Shadow Mist's block B with its `bx lr` replaced by a branch to C (flags survive a `b`)."""
            return struct.pack("<5H", 0x2189, 0x0149, 0x3901, 0x428B, _b(MISS_B + 8, MISS_C))


        def miss_block_c() -> bytes:
            """J. Z already set -> return; else test 0x10A5 = 0x111F - 0x7A.  r1 is dead on both exits."""
            return struct.pack("<4H", 0xD001,          # beq  ret
                               0x397A,                 # subs r1,#0x7a
                               0x428B,                 # cmp  r3,r1
                               0x4770)                 # ret: bx lr


        ARM_OQ_T = f"""
                ldrb    r1, [r4, #0x5]
                cmp     r1, #0x2
                bne     out
                ldr     r0, ={TAG_YOU_CAN:#x}
                b       out
        """
        def timing_arms() -> tuple:
            if any(c == DONOR_CID for c, *_ in tch.ARMS):
                return tch.ARMS
            return tch.ARMS + ((DONOR_CID, "oq", ARM_OQ_T, "Overtex Qoatlus: desc[+5] == 2 (C3 cls2) -> class 2"),)






        def apply_c3_overlay(ov: bytearray, stock_ov3: bytes) -> None:
            insert_row(ov, MASK_BASE, MASK_COUNT, 4, MASK_FMT, MASK_ROW, MASK_PHANTOM, "E  leave mask")
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, CLS2_REC, CLS2_PHANTOM, "F  cls2")
            # H: Shadow Mist must already own the node (it is in the chain, and this card is layered on it)
            tail = _sm.GATE_PATCHED[4:]
            assert bytes(ov[GY_NODE - RAM_BASE + 4:GY_NODE - RAM_BASE + 8]) == tail, "H node tail is not Shadow Mist's"
            _put(ov, GY_STUB, gy_stub(), stock_ov3[GY_STUB - RAM_BASE:GY_STUB - RAM_BASE + GY_STUB_LEN], "H  GY stub")
            _put(ov, GY_NODE, tch._bl(GY_NODE, GY_STUB), _sm.GATE_PATCHED[:4], "H  chain node -> BL GY stub")
            # J: Shadow Mist's block B must be installed; C is a stock dead tail
            _put(ov, MISS_C, miss_block_c(), stock_ov3[MISS_C - RAM_BASE:MISS_C - RAM_BASE + 8], "J  miss block C")
            _put(ov, MISS_B, miss_block_b(), _sm.miss_block_b(), "J  miss block B -> C")
            tch.apply(ov, quiet=True)


        def install_c3_ov5(rom) -> None:
            for label, addr, blob, reserve in (("F  C3 cond", C3COND, c3_cond_stub(C3COND), C3_RESERVE),
                                               ("F  C3 slot4", C3SLOT4, c3_slot4_stub(C3SLOT4), C3_RESERVE)):
                assert_thumb1_only(blob, addr)
                assert len(blob) <= reserve, f"{label} is {len(blob)} B > {reserve:#x}"
                if ov5_cave.read_cave(rom, addr, len(blob)) != blob:
                    ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                    print(f"{label} ov5 @{addr:#010x}  {len(blob)} B")
            _rewrite_shared(rom, ov5_cave.CAVE_TIMINGHOOK, tch.RESERVE, tch.stub(ov5_cave.CAVE_TIMINGHOOK),
                            tch.stub(ov5_cave.CAVE_TIMINGHOOK, timing_arms()), "T  timing stub")


        from otn_enhanced.cards import animadorned_archosaur as _arch  # noqa: E402
        from otn_enhanced.cards import miscellaneousaurus as _misc  # noqa: E402
        from otn_enhanced.effects.common import put as _put, rewrite_shared as _rewrite_shared

        CLS3_BASE, CLS3_COUNT, CLS3_PHANTOM = 0x02279D74, 0x308, 0x0E4C
        C2COND, C2COND_RESERVE = ov5_cave.CAVE_OQ_C2COND, 0xA0
        C2HELP, C2HELP_RESERVE = ov5_cave.CAVE_OQ_C2HELP, 0xE0
        C2RES, C2RES_RESERVE = ov5_cave.CAVE_OQ_C2RES, 0x240
        C2ACT = ov5_cave.CAVE_OQ_C2ACT          # 4 B: the activation descriptor, stashed on the 0x80 entry
        SPEED, SPEED_RESERVE = ov5_cave.CAVE_OQ_SPEED, 0x20
        OPT_LATCH_COND, OPT_LATCH_COST = 0x021F01C1, 0x021E5061   # Junk Defender's per-copy latch (rider 0x0FB6)
        IS_NEGATED, IS_SPELL, IS_TRAP = 0x021AB90D, 0x02022FC9, 0x02022FDD
        OFFER_GATE = 0x021F06E9                 # (mine, act) -- Koa'ki Meiru Wall's tail
        NEGATE = 0x022062F9                     # (mine, act): negate + destroy (Wall / Sandman / Magic Jammer)
        CLS3_REC = (DONOR_CID, 0, C2RES | 1, 0, C2COND | 1, OPT_LATCH_COST, 0)
        SPEED_SITE = _misc.SPEED_SITE           # 0x021A894C, the speed lookup's default leaf (Misc's BL + nop)
        RACE_DINOSAUR = 9

        def c2_help_stub(base: int) -> bytes:
            """(r0 side, r1 mode 0 hand / 1 field, r2 record?) -> own destroyable Dinosaurs.  Archosaur's helper
            WITHOUT its self-exclusion: "1 Dinosaur monster in your hand or face-up on your field" (any, incl. this)."""
            A = _arch
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R7, R2, #0x0")
            b.insn("MOV", "R6, #0x0")
            b.insn("MOV", "R5, #0x0")
            b.insn("LDR", "R0, [SP, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "field")
            b.label("hand")
            b.ldr_const(1, A.PLAYER_HAND_COUNT)
            b.insn("CMP", "R4, #0x0")
            b.insn("BEQ", "h0")
            b.ldr_const(0, A.PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("h0")
            b.insn("LDR", "R0, [R1, #0x0]")
            b.insn("CMP", "R5, R0")
            b.insn("BGE", "done")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("MOV", "R1, #0xB")
            b.insn("ADD", "R2, R5, #0x0")
            b.ldr_const(3, A.SLOT)
            b.insn("BLX", "R3")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("STR", "R0, [SP, #0x0]")
            b.ldr_const(3, A.IS_MONSTER)
            b.insn("BLX", "R3")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "hnext")
            b.insn("LDR", "R0, [SP, #0x0]")
            b.ldr_const(3, A.RACE_PRINTED)
            b.insn("BLX", "R3")
            b.insn("CMP", f"R0, #0x{RACE_DINOSAUR:X}")
            b.insn("BNE", "hnext")
            b.insn("ADD", "R6, #0x1")
            b.insn("CMP", "R7, #0x0")
            b.insn("BEQ", "hnext")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("MOV", "R1, #0xB")
            b.insn("ADD", "R2, R5, #0x0")
            b.ldr_const(3, A.RECORD)
            b.insn("BLX", "R3")
            b.label("hnext")
            b.insn("ADD", "R5, #0x1")
            b.insn("B", "hand")
            b.label("field")
            b.insn("CMP", "R5, #0x4")
            b.insn("BGT", "done")
            b.ldr_const(1, A.FIELD_CID)
            b.insn("CMP", "R4, #0x0")
            b.insn("BEQ", "f0")
            b.ldr_const(0, A.PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("f0")
            b.insn("LSL", "R0, R5, #0x4")
            b.insn("ADD", "R1, R1, R0")
            b.insn("LSL", "R0, R5, #0x2")
            b.insn("ADD", "R1, R1, R0")
            b.insn("LDRH", "R0, [R1, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "fnext")
            b.insn("LDRH", "R2, [R1, #0x8]")
            b.insn("CMP", "R2, #0x0")
            b.insn("BEQ", "fnext")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.insn("MOV", "R2, #0x0")
            b.ldr_const(3, A.RACE_LIVE)
            b.insn("BLX", "R3")
            b.insn("CMP", f"R0, #0x{RACE_DINOSAUR:X}")
            b.insn("BNE", "fnext")
            b.insn("ADD", "R6, #0x1")
            b.insn("CMP", "R7, #0x0")
            b.insn("BEQ", "fnext")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.insn("MOV", "R2, #0x0")
            b.ldr_const(3, A.RECORD)
            b.insn("BLX", "R3")
            b.label("fnext")
            b.insn("ADD", "R5, #0x1")
            b.insn("B", "field")
            b.label("done")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("POP", "{R1, R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def c2_cond_stub(base: int) -> bytes:
            """cls3 +0C (r0 = my desc, r1 = the activation's desc).  Wall's pre-checks with Spell OR Trap, then
            this copy's once-per-turn latch, then a destroyable Dinosaur, then Wall's generic offer gate."""
            b = EffectBuilder()
            b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R4, R1, #0x0")
            b.insn("BEQ", "ret0")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xA")
            b.insn("BGT", "ret0")
            b.insn("LDRB", "R0, [R4, #0x5]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "ret0")
            b.call_addr(IS_NEGATED, R4, 1, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "ret0")
            b.insn("LDRB", "R1, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x6]")
            b.insn("ADD", "R2, R1, #0x0")
            b.insn("EOR", "R2, R0")
            b.insn("LDRB", "R1, [R5, #0x2]")
            b.insn("LDRB", "R0, [R5, #0x6]")
            b.insn("EOR", "R0, R1")
            b.insn("CMP", "R2, R0")
            b.insn("BEQ", "ret0")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.call_addr(IS_SPELL, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "st")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.call_addr(IS_TRAP, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ret0")
            b.label("st")
            b.call_addr(OPT_LATCH_COND, R5, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ret0")
            b.insn("LDRB", "R6, [R5, #0x2]")
            b.insn("LDRB", "R0, [R5, #0x6]")
            b.insn("EOR", "R6, R0")
            b.insn("MOV", "R0, #0x1")
            b.insn("AND", "R6, R0")
            b.call_addr(C2HELP, R6, 0, 0, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "have")
            b.call_addr(C2HELP, R6, 1, 0, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ret0")
            b.label("have")
            b.call_addr(OFFER_GATE, R5, R4, via=R7)
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            b.label("ret0")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def c2_res_stub(base: int) -> bytes:
            """cls3 +04 (r0 = desc, r1 = the activation being negated -- valid on the 0x80 entry, as for Wall's
            0x022062F9; stashed in C2ACT there so later phases do not depend on r1).  desc[+0x18] = 0 hand / 1 field,
            [+0x1A] = picked zone code, [+0x1C] = hand count before the destroy.  Archosaur's pick/destroy on private
            phases 0x90..0x94; once the Dinosaur has left: close, then NEGATE(desc, act) = negate + destroy that card."""
            A = _arch
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2, R3, R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R6, [R5, #0x2]")
            b.insn("LDRB", "R0, [R5, #0x6]")
            b.insn("EOR", "R6, R0")
            b.insn("MOV", "R0, #0x1")
            b.insn("AND", "R6, R0")
            b.ldr_const(4, A.PHASE_STATE)
            b.insn("LDR", "R0, [R4, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BEQ", "p80")
            b.insn("CMP", "R0, #0x90")
            b.insn("BEQ", "p90")
            b.insn("CMP", "R0, #0x91")
            b.insn("BEQ", "p91")
            b.insn("CMP", "R0, #0x92")
            b.insn("BEQ", "p92j")
            b.insn("CMP", "R0, #0x93")
            b.insn("BEQ", "p93j")
            b.insn("CMP", "R0, #0x94")
            b.insn("BEQ", "p94j")
            b.insn("B", "stop")
            b.label("p92j")
            b.insn("B", "p92")
            b.label("p93j")
            b.insn("B", "p93")
            b.label("p94j")
            b.insn("B", "p94")
            b.label("p80")
            b.insn("LDR", "R0, [SP, #0x0]")
            b.ldr_const(3, C2ACT)
            b.insn("STR", "R0, [R3, #0x0]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R1, #0x80")
            b.ldr_const(3, A.OPEN)
            b.insn("BLX", "R3")
            b.call_addr(C2HELP, R6, 0, 0, via=R3)
            b.insn("ADD", "R7, R0, #0x0")
            b.call_addr(C2HELP, R6, 1, 0, via=R3)
            b.insn("CMP", "R7, #0x0")
            b.insn("BEQ", "onlyfield")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "onlyhand")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R0, #0x3")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("ADD", "R0, R5, #0x0")
            b.ldr_const(1, A.TITLE)
            b.ldr_const(2, A.LBL_HAND)
            b.ldr_const(3, A.LBL_FIELD)
            b.ldr_const(7, A.PROMPT)
            b.insn("BLX", "R7")
            b.insn("MOV", "R0, #0x90")
            b.insn("B", "ret")
            b.label("onlyfield")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "abortj")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "setans")
            b.label("onlyhand")
            b.insn("MOV", "R0, #0x0")
            b.label("setans")
            b.insn("STRH", "R0, [R5, #0x18]")
            b.insn("MOV", "R0, #0x91")
            b.insn("B", "ret")
            b.label("p90")
            b.ldr_const(0, A.CHOICE_STATE)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("STRH", "R0, [R5, #0x18]")
            b.insn("MOV", "R0, #0x91")
            b.insn("B", "ret")
            b.label("p91")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("MOV", f"R1, #0x{A.MSG_DESTROY:X}")
            b.ldr_const(3, A.MESSAGE)
            b.insn("BLX", "R3")
            b.insn("MOV", "R0, #0x92")
            b.insn("B", "ret")
            b.label("abortj")
            b.insn("B", "abort")
            b.label("p92")
            b.ldr_const(1, A.CHOICE_STATE)
            b.insn("STR", "R6, [R1, #0x30]")
            b.insn("MOV", f"R0, #0x{A.PICK_CODE + 0xF:X}")
            b.insn("STR", "R0, [R1, #0x2C]")
            b.ldr_const(1, A.PICK_HDR)
            b.insn("STRH", "R6, [R1, #0x0]")
            b.insn("MOV", f"R0, #0x{A.PICK_CODE:X}")
            b.insn("STRH", "R0, [R1, #0x2]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STRH", "R0, [R1, #0x4]")
            b.insn("STRH", "R0, [R1, #0x6]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("LDRH", "R1, [R5, #0x18]")
            b.call_addr(C2HELP, R0, R1, 1, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "abortj")
            b.insn("LSL", "R0, R6, #0x2")
            b.ldr_const(1, A.CTRL_TYPE)
            b.insn("LDR", "R0, [R1, R0]")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "auto")
            b.insn("CMP", "R0, #0x4")
            b.insn("BEQ", "auto")
            b.insn("MOV", "R0, #0x37")
            b.insn("ADD", "R1, R6, #0x0")
            b.insn("MOV", f"R2, #0x{A.PICK_CODE:X}")
            b.insn("MOV", "R3, #0x0")
            b.ldr_const(7, A.PICK_UI)
            b.insn("BLX", "R7")
            b.label("auto")
            b.insn("MOV", "R0, #0x93")
            b.insn("B", "ret")
            b.label("p93")
            b.ldr_const(1, A.PICK_HDR)
            b.insn("LDRH", "R4, [R1, #0x4]")
            b.insn("LSL", "R0, R4, #0x1")
            b.ldr_const(1, A.PICK_LOCS)
            b.insn("LDRH", "R0, [R1, R0]")
            b.insn("LSL", "R0, R0, #0x1A")
            b.insn("LSR", "R0, R0, #0x1B")
            b.insn("STRH", "R0, [R5, #0x1A]")
            b.insn("CMP", "R0, #0x4")
            b.insn("BGT", "handkill")
            b.insn("LDRH", "R2, [R5, #0x1A]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.ldr_const(3, A.DESTROY_FIELD)
            b.insn("BLX", "R3")
            b.insn("MOV", "R0, #0x94")
            b.insn("B", "ret")
            b.label("handkill")
            b.insn("LSL", "R0, R4, #0x2")
            b.ldr_const(1, A.PICK_WORDS)
            b.insn("LDR", "R7, [R1, R0]")
            b.ldr_const(1, A.PLAYER_HAND_COUNT)
            b.insn("CMP", "R6, #0x0")
            b.insn("BEQ", "hk0")
            b.ldr_const(0, A.PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("hk0")
            b.insn("LDR", "R0, [R1, #0x0]")
            b.insn("STRH", "R0, [R5, #0x1C]")
            b.insn("MOV", "R4, #0x0")
            b.label("hkloop")
            b.insn("LDRH", "R0, [R5, #0x1C]")
            b.insn("CMP", "R4, R0")
            b.insn("BGE", "abort")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("MOV", "R1, #0xB")
            b.insn("ADD", "R2, R4, #0x0")
            b.ldr_const(3, A.SLOT)
            b.insn("BLX", "R3")
            b.insn("LDR", "R1, [R0, #0x0]")
            b.insn("CMP", "R1, R7")
            b.insn("BEQ", "hkfound")
            b.insn("ADD", "R4, #0x1")
            b.insn("B", "hkloop")
            b.label("hkfound")
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("LDRH", "R3, [R5, #0x0]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("ADD", "R1, R4, #0x0")
            b.ldr_const(7, A.DESTROY_HAND)
            b.insn("BLX", "R7")
            b.insn("MOV", "R0, #0x94")
            b.insn("B", "ret")
            b.label("p94")
            b.insn("LDRH", "R0, [R5, #0x1A]")
            b.insn("CMP", "R0, #0x4")
            b.insn("BGT", "hchk")
            b.ldr_const(1, A.FIELD_CID)
            b.insn("CMP", "R6, #0x0")
            b.insn("BEQ", "c0")
            b.ldr_const(2, A.PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R2")
            b.label("c0")
            b.insn("LSL", "R2, R0, #0x4")
            b.insn("ADD", "R1, R1, R2")
            b.insn("LSL", "R2, R0, #0x2")
            b.insn("ADD", "R1, R1, R2")
            b.insn("LDRH", "R0, [R1, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "abort")
            b.insn("B", "destroyed")
            b.label("hchk")
            b.ldr_const(1, A.PLAYER_HAND_COUNT)
            b.insn("CMP", "R6, #0x0")
            b.insn("BEQ", "hc0")
            b.ldr_const(0, A.PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("hc0")
            b.insn("LDR", "R0, [R1, #0x0]")
            b.insn("LDRH", "R1, [R5, #0x1C]")
            b.insn("CMP", "R0, R1")
            b.insn("BGE", "abort")
            b.label("destroyed")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R1, #0x7E")
            b.ldr_const(3, A.CLOSE)
            b.insn("BLX", "R3")
            b.insn("ADD", "R0, R5, #0x0")
            b.ldr_const(1, C2ACT)
            b.insn("LDR", "R1, [R1, #0x0]")
            b.call_addr(NEGATE, via=R3)
            b.insn("B", "stop")
            b.label("abort")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R1, #0x7E")
            b.ldr_const(3, A.CLOSE)
            b.insn("BLX", "R3")
            b.label("stop")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def speed_stub(base: int) -> bytes:
            """BL'd from 0x021A894C (the speed lookup's default leaf) with r0 = desc, r2 = cid, lr = 0x021A8951.
            0x10A5's cls3 record -> spell speed 2 (a Quick Effect); everything else -> Miscellaneousaurus's stub,
            which itself falls back to the native 0x0202345C.  r0/r2/lr are untouched on the fall-through."""
            b = EffectBuilder()
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R2, R3")
            b.insn("BNE", "next")
            b.insn("LDRB", "R3, [R0, #0x5]")
            b.insn("CMP", "R3, #0x3")
            b.insn("BNE", "next")
            b.insn("MOV", "R0, #0x2")
            b.insn("BX", "LR")
            b.label("next")
            b.ldr_const(3, _misc.SPEED_ADDR | 1)
            b.insn("BX", "R3")
            return b.assemble(base, pad="nop")


        SPEED_OURS = tch._bl(SPEED_SITE, SPEED) + struct.pack("<H", 0x46C0)


        def _c2_blobs() -> list[tuple[str, int, bytes, int]]:
            return [("K  C2 cond", C2COND, c2_cond_stub(C2COND), C2COND_RESERVE),
                    ("K  C2 helper", C2HELP, c2_help_stub(C2HELP), C2HELP_RESERVE),
                    ("L  C2 resolver", C2RES, c2_res_stub(C2RES), C2RES_RESERVE),
                    ("M  speed", SPEED, speed_stub(SPEED), SPEED_RESERVE)]


        def apply_c2_overlay(ov: bytearray) -> None:
            insert_row(ov, CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, CLS3_REC, CLS3_PHANTOM, "K  cls3")
            _put(ov, SPEED_SITE, SPEED_OURS, _misc.SPEED_HOOKED, "M  speed leaf -> Qoatlus -> Misc")


        def install_c2_ov5(rom) -> None:
            for label, addr, blob, reserve in _c2_blobs():
                assert_thumb1_only(blob, addr)
                assert len(blob) <= reserve, f"{label} is {len(blob)} B > {reserve:#x}"
                if ov5_cave.read_cave(rom, addr, len(blob)) != blob:
                    ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                    print(f"{label} ov5 @{addr:#010x}  {len(blob)} B")


        # ---------------------------------------------------------------------------- apply ----
        def apply_overlay(ov: bytearray) -> None:
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, CRIT_ROW, CRIT_PHANTOM, "A  criteria")
            insert_row(ov, REG_BASE, REG_COUNT, 8, REG_FMT, REG_ROW, PROC_PHANTOM, "B  registry")


        def apply_arm9(rom) -> None:
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)
            base, n, lst = _read_thunk_list(bytes(d), NOMI_POOL, NOMI_COUNT_IMM, NOMI_LIST, "C  nomi class 2")
            if DONOR_CID not in lst:
                assert DOOM_DOZER in lst, "C: Doom Dozer missing -- wrong list"
                struct.pack_into(f"<{n}H", d, _a9(base), *_swap_in_list(lst, PROC_PHANTOM, DONOR_CID, "C nomi"))
                print(f"C  nomi class 2: {PROC_PHANTOM:#06x} -> {DONOR_CID:#06x}")
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def install(rom, view):
            from otn_enhanced.rom import stock as _stock
            stock = _stock.ov3()
            ov = view.buf
            apply_overlay(ov)
            apply_c3_overlay(ov, stock)
            apply_c2_overlay(ov)
            install_c3_ov5(rom)
            install_c2_ov5(rom)
            tg_table.register_tg_handss(rom, ov, DONOR_CID, SSCOND)
            apply_arm9(rom)

        def check_fn(c, rom, view):
            ov = bytes(view.buf)

            def check(cond, msg):
                c.ok(bool(cond), msg)

            for label, base, cnt, stride, fmt, recs, phs in (
                    ("A criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, [CRIT_ROW], (CRIT_PHANTOM,)),
                    ("B registry", REG_BASE, REG_COUNT, 8, REG_FMT, [REG_ROW], (PROC_PHANTOM,)),
                    ("E mask", MASK_BASE, MASK_COUNT, 4, MASK_FMT, [MASK_ROW], (MASK_PHANTOM,)),
                    ("F cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, [CLS2_REC], (CLS2_PHANTOM,)),
                    ("K cls3", CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, [CLS3_REC], (CLS3_PHANTOM,))):
                rows = [struct.unpack_from(fmt, ov, base - RAM_BASE + i * stride) for i in range(cnt)]
                keys = [r[0] for r in rows]
                check(all(keys[i] <= keys[i + 1] for i in range(cnt - 1)), f"{label} still sorted")
                check([r for r in rows if r[0] == DONOR_CID] == recs, f"{label} donor rows == spec, in order")
                check(not any(p in keys for p in phs), f"{label} phantoms {[hex(p) for p in phs]} dropped")

            for label, addr, blob, _ in _ov5_blobs():
                check(ov5_cave.read_cave(rom, addr, len(blob)) == blob, f"{label} installed @{addr:#x}")
            check(tg_table.tg_handss_ok(rom, ov, DONOR_CID), "D hand-SS trampoline row")

            # --- C3 ---
            from otn_enhanced.cards import animadorned_archosaur as _arch
            check(tuple(_arch.PILLS) == PILLS, "G Archosaur's Pill list is the three Evolution Pills")
            pred = _arch.pred_stub(ov5_cave.CAVE_ARCH_PRED)
            check(ov5_cave.read_cave(rom, ov5_cave.CAVE_ARCH_PRED, len(pred)) == pred
                  and _arch.DECK_WALKER == DECK_WALKER and _arch.TYPE_ADD == TYPE_ADD,
                  "G Archosaur's Pill predicate is installed (CRIT's C3 mode borrows it)")
            for label, addr, blob in (("F C3 cond", C3COND, c3_cond_stub(C3COND)),
                                      ("F C3 slot4", C3SLOT4, c3_slot4_stub(C3SLOT4))):
                check(ov5_cave.read_cave(rom, addr, len(blob)) == blob, f"{label} installed @{addr:#x}")
            ob = bytes(ov)
            check(ob[GY_STUB - RAM_BASE:GY_STUB - RAM_BASE + GY_STUB_LEN] == gy_stub(), f"H GY stub @{GY_STUB:#x}")
            check(ob[GY_NODE - RAM_BASE:GY_NODE - RAM_BASE + 8] == tch._bl(GY_NODE, GY_STUB) + _sm.GATE_PATCHED[4:],
                  f"H node {GY_NODE:#x} -> BL GY stub, Shadow Mist's beq/b kept")
            check(_snoww._switch_leaf(ob, DONOR_CID) == GY_STUB + 12, "H simulated chain: 0x10A5 reaches the GY stub's test")
            check(_snoww._switch_leaf(ob, _sm.DONOR_CID) == _sm.GATE_ACCEPT_LEAF, "H simulated chain: Shadow Mist still accepts")
            check(ob[MISS_B - RAM_BASE:MISS_B - RAM_BASE + 10] == miss_block_b()
                  and ob[MISS_C - RAM_BASE:MISS_C - RAM_BASE + 8] == miss_block_c(), "J miss blocks B -> C installed")
            new = tch.stub(ov5_cave.CAVE_TIMINGHOOK, timing_arms())
            check(ov5_cave.read_cave(rom, ov5_cave.CAVE_TIMINGHOOK, len(new)) == new,
                  f"T timing stub carries the 0x10A5 arm ({len(new)}/{tch.RESERVE} B)")
            check(not any(c == DONOR_CID for c, *_ in crh.ARMS), "G no row-hook arm (one mode-switched row instead)")

            # --- C2 ---
            for label, addr, blob, _ in _c2_blobs():
                check(ov5_cave.read_cave(rom, addr, len(blob)) == blob, f"{label} installed @{addr:#x}")
            check(code_reaches(rom, SPEED_SITE, SPEED),
                  f"M speed leaf {SPEED_SITE:#x} reaches the Qoatlus speed stub (which tails to Misc's)")
            check(ov5_cave.read_cave(rom, _misc.SPEED_ADDR, 0x10) == _misc._build_speed(_misc.SPEED_ADDR)[:0x10],
                  "M Miscellaneousaurus's speed stub is intact (our fall-through target)")

            mc, sec = ov5_cave._arm9_main(rom)
            _, _, l9 = _read_thunk_list(bytes(sec.data), NOMI_POOL, NOMI_COUNT_IMM, NOMI_LIST, "C")
            check(DONOR_CID in l9 and PROC_PHANTOM not in l9 and all(l9[i] < l9[i + 1] for i in range(len(l9) - 1)),
                  "C nomi class 2: donor in, phantom gone, strictly sorted")

        stubs = tuple((addr, blob, label) for label, addr, blob, reserve in _ov5_blobs())
        return Compiled(stubs, installs=(install,), checks=(check_fn,))


qoatlus_effects = hand_special_summon_shuffling_five_banished_dinosaurs_negate_spell_trap_by_destroying_dinosaur_and_add_evolution_pill

SPEC = card(0x10A5, qoatlus_effects())

PROPS = card_props("DARK", "Dinosaur", level=7, atk=2700, defense=2100)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_overtex_qoatlus.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
