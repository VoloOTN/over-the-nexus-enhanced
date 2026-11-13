"""Ojamassimilation (Normal Spell) on Gryphon's Feather Duster 0x170F.

See notes/ojamassimilation-findings.md and card_text.CARD_TEXT[0x170F] for the printed text (a custom Ojama card:
reveal / banish Ojamas to Special Summon, with a Graveyard effect and "Ojama" set-code membership).
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, Compiled
from otn_enhanced.asm.effect_builder import EffectBuilder, Reg
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
class normal_spell_reveal_ojama_banish_or_ss_ojama_tokens_and_banished_ojama_to_deck_add_by_gy_banish:
    """Ojamassimilation (Gryphon's Feather Duster 0x170F, a Normal Spell; an Ojama-family card, in-game confirmed in the old docstring with
    the old date undated here): the donor's cls0 record is rewritten in place to {resolver, 0, cond, cost, 0}, one named-multizone criteria
    row over phantom 0x0EA9 whose ov5 handler walks hand/field/GY/Deck/banished pools, a GY effect (cls2 over 0x1452 + GY-action registry
    phantom row converted to the Grapha family) and "Ojama" set-code membership by swapping phantom 0x0EB0 for the donor in the ARM9 list.
    Twelve ov5 stubs. Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.cards import reborn_tengu as tengu
        from otn_enhanced.effects.common import ARM9_BASE, insert_row_wide, ov3_off as _off
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid

        # --- A: cls0 -------------------------------------------------------------------------------
        CLS0_BASE, CLS0_COUNT, CLS0_STRIDE = 0x0227E64C, 0x51A, 24
        CLS0_NATIVE = (DONOR_CID, 0x022137F5, 0x021DF06D, 0, 0, 0)

        # --- B: criteria ---------------------------------------------------------------------------
        CRIT_BASE, CRIT_COUNT, CRIT_FMT = 0x022713C4, 0x56C, "<HHII"
        PHANTOM = 0x0EA9
        ROW_WORD = 0x0802                         # the eleven named-multizone rows' word (0x0223E2C9)

        # --- slots ---------------------------------------------------------------------------------
        OJ, OPRED, HAS = ov5_cave.CAVE_OJ_OJ, ov5_cave.CAVE_OJ_OPRED, ov5_cave.CAVE_OJ_HAS
        ZCAP, RPRED, HANDLER = ov5_cave.CAVE_OJ_ZCAP, ov5_cave.CAVE_OJ_RPRED, ov5_cave.CAVE_OJ_HANDLER
        COND, COST, RES = ov5_cave.CAVE_OJ_COND, ov5_cave.CAVE_OJ_COST, ov5_cave.CAVE_OJ_RES
        GYCOND, GYSEL, GYRES = ov5_cave.CAVE_OJ_GYCOND, ov5_cave.CAVE_OJ_GYSEL, ov5_cave.CAVE_OJ_GYRES
        RESERVE = {OJ: 0x40, OPRED: 0x20, HAS: 0xB0, ZCAP: 0x60, RPRED: 0x60,
                   HANDLER: 0x1B0, COND: 0x60, COST: 0x260, RES: 0x170,
                   GYCOND: 0x40, GYSEL: 0x100, GYRES: 0x100}

        CLS0_PATCHED = (DONOR_CID, RES | 1, 0, COND | 1, COST | 1, 0)
        CRIT_ROW = (DONOR_CID, 0xFFFF, HANDLER | 1, ROW_WORD)

        # --- E: C3 (cls2 + GY-action row) ------------------------------------------------------------
        CLS2_BASE, CLS2_COUNT, CLS2_STRIDE = 0x02275C04, 0x2B9, 24
        CLS2_PHANTOM = 0x1452
        BANISH_SELF = 0x021E5709                  # native "banish this card from your GY" cost (Skill Successor)
        CLS2_ROW = (DONOR_CID, GYRES | 1, 0, GYCOND | 1, BANISH_SELF, GYSEL | 1)
        GYREG_BASE, GYREG_COUNT = 0x0228DDF8, 60
        GYREG_PHANTOM_ROW = (CLS2_PHANTOM, 0x0E, 0x0224C55D, 0x0224C669)   # row 13, sibling family
        GYREG_ROW = (DONOR_CID, 0x0E, 0x0224C591, 0x0224C6C1)              # the Grapha (GY-effect) family

        # --- F: "Ojama" set code 0x0D (Ojama Blue's Deck search: row aux 0x0D -> has_set_code) ---------
        from otn_enhanced.effects.common import ARM9_BASE
        SETCODE_PTR_TABLE, SETCODE = 0x0209D0D8, 0x0D
        THUNK, COUNT_IMM, LIST_LIT = 0x02023894, 0x02023898, 0x0202389C
        OJAMA_LIST = 0x0209C9E6
        OJAMA_STOCK = (0x0EB0, 0x0F4B, 0x0F4C, 0x0F4D, 0x166A, 0x1681, 0x16B3, 0x16B4,
                       0x16CF, 0x17EE, 0x1945, 0x1946, 0x1C0B, 0x2048, 0x2049, 0x204A)
        OJAMA_DROPPED = 0x0EB0                    # phantom: no card_prop, in no other set list
        OJAMA_GROUP = tuple(sorted(set(OJAMA_STOCK) - {OJAMA_DROPPED} | {DONOR_CID}))
        assert len(OJAMA_GROUP) == len(OJAMA_STOCK)

        # --- params --------------------------------------------------------------------------------
        P_REVEAL, P_BANISH, P_BANISHED, P_MAT, P_ONE = 0, 1, 2, 0x10000, 0x20000
        WORD_MONSTER, BANISHED_FLAGS = 0x00010002, 8   # Miracle Dig's row 153 (0x0223DB24)
        TARGETS = 3
        COUNT_CODE, MSG_TARGET = 9, 0x116              # Miracle Dig: exactly 3 (KB dispatch.multiselect_target_template)
        EXCL_SHIFT = 20
        MAX_N = 3                                 # XYZ-Dragon Cannon lists the most distinct names (3)

        # --- natives -------------------------------------------------------------------------------
        PLAYER, STRIDE = 0x0229AC94, 0xB3C        # hand +0x124/#+0x0C, Deck +0x304/#+0x10, GY +0x55C/#+0x14
        FIELD = 0x0229ACC8                        # + side*0xB3C + zone*0x14: +0 card word, +8 face-up
        TOKENS = (0x0F4B, 0x0F4D)                 # Ojama Tokens (members of the Ojama list)
        LITERAL = 0xBB8                           # recipe slot >= 0xBB8 is a card id (0x02240550 / 0x0224050C)
        WORD_LIGHT_MACHINE = 0x39000002           # race 7 << 27 | attribute 1 << 24 | real card
        SAME_NAME = 0x02022E99                    # (cid, cid) -> nonzero when the names match
        IS_MONSTER, IS_OJAMA = 0x02029E61, 0x02023895
        RECIPE_COUNT, RECIPE_SLOT = 0x02231E09, 0x02231E8D
        ED_WALKER, DECK_B, GY_B, HAND_B = 0x0223BE41, 0x0223BC3D, 0x0223C4E9, 0x0223C16D
        LIST_FILTER = 0x0223C715
        RECORD = 0x02243B2D                       # (side, zone, idx) -> append a field card to the pick list
        COUNT = 0x02243FA9                        # (side, cid, param) -> candidate count
        MAY_SS, FREE_ZONE = 0x021AD871, 0x021B9ECD
        STATE = 0x0229AAFC                        # +0x7C cost phase, +0x70 resolver phase
        UI = 0x0229DD94                           # +0x34 number / pick-count answer
        SHORTCIRCUIT = 0x021D2BC9
        MESSAGE, PICKER, READBACK, PICK_AT = 0x0219A819, 0x0219C431, 0x0219C511, 0x0219C94D
        NUMBER = 0x0219AE11                       # (side, cid, title, item, [sp] min, [sp+4] max)
        UI_CMD = 0x021C3BC9                       # (code, zone, ref, x)
        ED_CLOSE, ED_TOP = 0x021D2661, 0x021C7655 # Prisma's post-reveal pair (cmd 0x59 / 0x28)
        CHAIN_PUSH, CHAIN_POP = 0x021D28A5, 0x021D2965
        GY_INDEX, GY_BANISH = 0x021A2511, 0x021C7105
        HAND_INDEX, HAND_BANISH = 0x021A25A1, 0x021C6E99
        ON_FIELD, FIELD_BANISH = 0x021A241D, 0x021CF40D
        SUMMON, SHUFFLE = 0x02269315, 0x021D269D
        BANISHED_WALK = 0x0223C6AD                # (side, cid, pred, ctx, [sp] word, [sp+4] flags)
        COUNT_ND = 0x02243FE1                     # (side, cid, param) -> count, picker header restored
        SEL_STEP = 0x0229AB7C                     # +0 slot5 sub-step, +4 pick index
        SET_PROMPT, SET_MAX = 0x0219A6F5, 0x0219A7F9
        PICK_SEL, PICK_ZONE = 0x0219C93D, 0x0219C535
        REC_BOARD, REC_LIST = 0x022347B1, 0x02234881
        PICK, TARGET_OK = 0x02234965, 0x022349B1  # (desc, i) -> target ref / still valid
        BAN_INDEX, BAN_TO_DECK = 0x021A2559, 0x021C727D
        DECK_SHUFFLE, DRAW = 0x021D26CD, 0x021D12F5
        MSG_REVEAL, MSG_BANISH, MSG_SS = 0x155, 0x46, 0x11D
        NUM_TITLE, NUM_ITEM = 0xA4, 0x11B

        def _check(blob: bytes, base: int, what: str) -> bytes:
            assert len(blob) <= RESERVE[base], f"{what} {len(blob):#x} > reserve {RESERVE[base]:#x}"
            assert_thumb1_only(blob, base)
            return blob


        def _player(b: EffectBuilder, reg: Reg, side: Reg, base: int, tag: str) -> None:
            """reg = base + (side & 1) * STRIDE.  Clobbers r0."""
            b.ldr_const(int(reg), base)
            b.insn("MOV", "R0, #0x1")
            b.insn("AND", f"R0, {side!r}")
            b.insn("BEQ", tag)
            b.ldr_const(0, STRIDE)
            b.insn("ADD", f"{reg!r}, {reg!r}, R0")
            b.label(tag)


        # ------------------------------------------------------------------------------- helpers ----
        def build_oj(base: int) -> bytes:
            """(cid) -> 1 iff an "Ojama" MONSTER that is not an Ojama Token."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(1, TOKENS[0])
            b.insn("CMP", "R0, R1")
            b.insn("BLT", "real")
            b.ldr_const(1, TOKENS[1])
            b.insn("CMP", "R0, R1")
            b.insn("BLE", "no")
            b.label("real")
            b.call("is_monster", via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(IS_OJAMA, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return _check(b.assemble(base, pad="nop"), base, "OJ")


        def build_opred(base: int) -> bytes:
            """Hand / GY builder filter (at entry [sp] = &card word): OJ(cid)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R3, LR}")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call_addr(OJ, via=R3)
            b.insn("POP", "{R3, PC}")
            return _check(b.assemble(base, pad="nop"), base, "OPRED")


        def build_has(base: int) -> bytes:
            """(side, cid) -> 1 iff a card with that NAME is in the player's hand, Deck or GY."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R1, R0, #0x0")
            _player(b, R4, R1, PLAYER, "p0")
            for tag, off, cnt in (("h", 0x124, 0x0C), ("d", 0x304, 0x10), ("g", 0x55C, 0x14)):
                b.insn("MOV", "R6, #0x0")
                b.label(f"{tag}lp")
                b.insn("LDR", f"R0, [R4, #0x{cnt:X}]")
                b.insn("CMP", "R6, R0")
                b.insn("BGE", f"{tag}end")
                b.insn("LSL", "R0, R6, #0x2")
                b.insn("ADD", "R0, R4, R0")
                b.ldr_const(1, off)
                b.insn("ADD", "R0, R0, R1")
                b.insn("LDR", "R0, [R0, #0x0]")
                b.insn("LSL", "R0, R0, #0x12")
                b.insn("LSR", "R0, R0, #0x12")
                b.insn("ADD", "R1, R5, #0x0")
                b.call_addr(SAME_NAME, via=R3)
                b.insn("CMP", "R0, #0x0")
                b.insn("BNE", "yes")
                b.insn("ADD", "R6, #0x1")
                b.insn("B", f"{tag}lp")
                b.label(f"{tag}end")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            return _check(b.assemble(base, pad="nop"), base, "HAS")


        def build_zcap(base: int) -> bytes:
            """(side) -> empty Monster Zones + own face-up Ojama monsters (zones a banish could free)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R1, R0, #0x0")
            _player(b, R4, R1, FIELD, "p0")
            b.insn("MOV", "R5, #0x0")
            b.insn("MOV", "R6, #0x0")
            b.label("lp")
            b.insn("CMP", "R6, #0x5")
            b.insn("BGE", "end")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "occ")
            b.insn("ADD", "R5, #0x1")
            b.insn("B", "nx")
            b.label("occ")
            b.insn("LDRH", "R0, [R4, #0x8]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "nx")
            b.insn("LDR", "R0, [R4, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call_addr(OJ, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "nx")
            b.insn("ADD", "R5, #0x1")
            b.label("nx")
            b.insn("ADD", "R4, #0x14")
            b.insn("ADD", "R6, #0x1")
            b.insn("B", "lp")
            b.label("end")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return _check(b.assemble(base, pad="nop"), base, "ZCAP")


        def build_rpred(base: int) -> bytes:
            """Extra-Deck walker predicate (r0 side, at entry [sp] = &card word): some literal recipe slot
            of this Fusion names a card in the player's hand / Deck / GY (Prisma's 0x0224050C, three zones)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
            b.insn("ADD", "R6, R0, #0x0")
            b.insn("LDR", "R0, [SP, #0x18]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R7, R0, #0x12")
            b.call_addr(RECIPE_COUNT, R7, via=R3)
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("MOV", "R4, #0x0")
            b.label("lp")
            b.insn("CMP", "R4, R5")
            b.insn("BGE", "no")
            b.call_addr(RECIPE_SLOT, R7, R4, via=R3)
            b.ldr_const(1, LITERAL)
            b.insn("CMP", "R0, R1")
            b.insn("BLT", "nx")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(HAS, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "yes")
            b.label("nx")
            b.insn("ADD", "R4, #0x1")
            b.insn("B", "lp")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, "RPRED")


        # ------------------------------------------------------------------------------- handler ----
        def _call3(b: EffectBuilder, builder: int, flags: int) -> None:
            b.ldr_const(0, ROW_WORD)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", f"R0, #0x{flags:X}")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.ldr_const(2, LIST_FILTER)
            b.insn("ADD", "R3, R7, #0x0")
            b.ldr_const(6, builder)
            b.insn("BLX", "R6")


        def _banish_b(b: EffectBuilder, builder: int) -> None:
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x0]")
            b.ldr_const(0, 0x10000)
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.ldr_const(2, OPRED | 1)
            b.insn("MOV", "R3, #0x0")
            b.ldr_const(6, builder)
            b.insn("BLX", "R6")


        def build_handler(base: int) -> bytes:
            """Criteria handler (r0 row, r1 side, r2 param) -- module doc B.
            Frame: [sp] / [sp+4] builder stack args, [sp+8..0x1F] cid list, [sp+0x20] fusion,
            [sp+0x24] n, [sp+0x28] i, [sp+0x2C] k."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x30")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R4, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.insn("CMP", f"R6, #0x{P_REVEAL:X}")
            b.insn("BEQ", "reveal")
            b.insn("CMP", f"R6, #0x{P_BANISH:X}")
            b.insn("BEQ", "banishj")
            b.insn("CMP", f"R6, #0x{P_BANISHED:X}")
            b.insn("BEQ", "banishedj")
            b.insn("ADD", "R7, SP, #0x8")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("LSR", "R0, R0, #0x11")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R0, R1")
            b.insn("BEQ", "mat")
            b.insn("LSL", "R0, R6, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("STR", "R0, [R7, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R7, #0x4]")
            b.insn("B", "build")
            b.label("banishj")
            b.insn("B", "banish")
            b.label("banishedj")
            b.insn("B", "banished")
            b.label("mat")
            b.insn("LSL", "R0, R6, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("STR", "R0, [SP, #0x20]")
            b.call_addr(RECIPE_COUNT, via=R3)
            b.insn("STR", "R0, [SP, #0x24]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x28]")
            b.insn("STR", "R0, [SP, #0x2C]")
            b.label("mlp")
            b.insn("LDR", "R0, [SP, #0x28]")
            b.insn("LDR", "R1, [SP, #0x24]")
            b.insn("CMP", "R0, R1")
            b.insn("BGE", "mend")
            b.insn("ADD", "R1, R0, #0x0")
            b.insn("ADD", f"R1, #0x{EXCL_SHIFT:X}")
            b.insn("ADD", "R2, R6, #0x0")
            b.insn("LSR", "R2, R1")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R2, R1")
            b.insn("BNE", "mnx")
            b.insn("LDR", "R0, [SP, #0x20]")
            b.insn("LDR", "R1, [SP, #0x28]")
            b.call_addr(RECIPE_SLOT, via=R3)
            b.ldr_const(1, LITERAL)
            b.insn("CMP", "R0, R1")
            b.insn("BLT", "mnx")
            b.insn("LDR", "R1, [SP, #0x2C]")
            b.insn("LSL", "R2, R1, #0x2")
            b.insn("STR", "R0, [R7, R2]")
            b.insn("ADD", "R1, #0x1")
            b.insn("STR", "R1, [SP, #0x2C]")
            b.label("mnx")
            b.insn("LDR", "R0, [SP, #0x28]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x28]")
            b.insn("B", "mlp")
            b.label("mend")
            b.insn("LDR", "R1, [SP, #0x2C]")
            b.insn("LSL", "R1, R1, #0x2")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R7, R1]")
            b.label("build")
            _call3(b, DECK_B, 0)
            _call3(b, GY_B, 4)
            _call3(b, HAND_B, 0)
            b.insn("B", "out")
            b.label("reveal")
            b.ldr_const(0, WORD_LIGHT_MACHINE)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(ED_WALKER, R0, R1, RPRED | 1, 0, via=R6)
            b.insn("B", "out")
            b.label("banished")
            b.ldr_const(0, WORD_MONSTER)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", f"R0, #0x{BANISHED_FLAGS:X}")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(BANISHED_WALK, R0, R1, OPRED | 1, 0, via=R6)
            b.insn("B", "out")
            b.label("banish")
            _banish_b(b, HAND_B)
            _banish_b(b, GY_B)
            _player(b, R7, R4, FIELD, "f0")
            b.insn("MOV", "R6, #0x0")
            b.label("flp")
            b.insn("CMP", "R6, #0x5")
            b.insn("BGE", "out")
            b.insn("LDRH", "R0, [R7, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "fnx")
            b.insn("LDRH", "R0, [R7, #0x8]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "fnx")
            b.insn("LDR", "R0, [R7, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call_addr(OJ, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "fnx")
            b.call_addr(RECORD, R4, R6, 0, via=R3)
            b.label("fnx")
            b.insn("ADD", "R7, #0x14")
            b.insn("ADD", "R6, #0x1")
            b.insn("B", "flp")
            b.label("out")
            b.insn("ADD", "SP, #0x30")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, "HANDLER")


        # ---------------------------------------------------------------------------- cls0 slots ----
        def build_cond(base: int) -> bytes:
            """+0C (desc, arg): may Special Summon, a zone can be had, >= 1 revealable Fusion, >= 1 Ojama.
            desc[+7] (the post-cost re-check) passes, as Soul Charge / Double Evolution Pill."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x7]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "yes")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x6]")
            b.insn("EOR", "R5, R0")
            b.call_addr(MAY_SS, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(ZCAP, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, R0, R1, P_REVEAL, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, R0, R1, P_BANISH, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return _check(b.assemble(base, pad="nop"), base, "COND")


        def build_cost(base: int) -> bytes:
            """+10 (desc, arg), phase [STATE+0x7C]:
            0 reveal prompt | 1 pick the Fusion (REVEAL) | 2 store it (desc+0x14 cid, +0x18 ref), M = min(
            names available, Ojama candidates, ZCAP, 3), number picker 1..M if M > 1 | 3 N -> desc+0x12,
            banish prompt | 4 pick exactly N (BANISH) | 5 reveal (cmd 0x58) + banish every pick, the
            payment machine's GY / hand / field order | 6 Prisma's ED close pair, return 1.
            Frame: [sp] i / min, [sp+4] n / max / ref, [sp+8] previous literal."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x10")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(SHORTCIRCUIT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "go")
            b.insn("B", "done")
            b.label("go")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.ldr_const(6, STATE)
            b.insn("LDR", "R0, [R6, #0x7C]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ph0")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "ph1")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "ph2")
            b.insn("CMP", "R0, #0x3")
            b.insn("BEQ", "ph3j")
            b.insn("CMP", "R0, #0x4")
            b.insn("BEQ", "ph4j")
            b.insn("CMP", "R0, #0x5")
            b.insn("BEQ", "ph5j")
            b.insn("B", "ph6")
            b.label("ph3j")
            b.insn("B", "ph3")
            b.label("ph4j")
            b.insn("B", "ph4")
            b.label("ph5j")
            b.insn("B", "ph5")
            b.label("ph0")
            b.call_addr(MESSAGE, R5, MSG_REVEAL, via=R3)
            b.insn("B", "nextj")
            b.label("ph1")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R1, #0x6")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call_addr(PICKER, R0, R1, R2, P_REVEAL, via=R7)
            b.insn("B", "nextj")
            b.label("ph2")
            b.call_addr(READBACK, via=R3)
            b.insn("LDR", "R1, [R0, #0x0]")
            b.insn("LSL", "R0, R1, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("STRH", "R0, [R4, #0x14]")
            b.insn("LSL", "R0, R1, #0x11")
            b.insn("LSR", "R0, R0, #0x1F")
            b.insn("LSL", "R1, R1, #0x1")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R1, R1, #0x1")
            b.insn("ADD", "R1, R1, R0")
            b.insn("STRH", "R1, [R4, #0x18]")
            b.insn("MOV", "R7, #0x0")
            b.insn("LDRH", "R0, [R4, #0x14]")
            b.call_addr(RECIPE_COUNT, via=R3)
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("STR", "R0, [SP, #0x8]")
            b.label("nl")
            b.insn("LDR", "R0, [SP, #0x0]")
            b.insn("LDR", "R1, [SP, #0x4]")
            b.insn("CMP", "R0, R1")
            b.insn("BGE", "nend")
            b.insn("LDRH", "R0, [R4, #0x14]")
            b.insn("LDR", "R1, [SP, #0x0]")
            b.call_addr(RECIPE_SLOT, via=R3)
            b.ldr_const(1, LITERAL)
            b.insn("CMP", "R0, R1")
            b.insn("BLT", "nnx")
            b.insn("LDR", "R1, [SP, #0x8]")
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "nnx")
            b.insn("STR", "R0, [SP, #0x8]")
            b.ldr_const(2, P_ONE)
            b.insn("ORR", "R2, R0")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "nnx")
            b.insn("ADD", "R7, #0x1")
            b.label("nnx")
            b.insn("LDR", "R0, [SP, #0x0]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("B", "nl")
            b.label("nextj")
            b.insn("B", "next")
            b.label("nend")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, R0, R1, P_BANISH, via=R3)
            b.insn("CMP", "R7, R0")
            b.insn("BLE", "c1")
            b.insn("ADD", "R7, R0, #0x0")
            b.label("c1")
            b.call_addr(ZCAP, R5, via=R3)
            b.insn("CMP", "R7, R0")
            b.insn("BLE", "c2")
            b.insn("ADD", "R7, R0, #0x0")
            b.label("c2")
            b.insn("CMP", f"R7, #0x{MAX_N:X}")
            b.insn("BLE", "c3")
            b.insn("MOV", f"R7, #0x{MAX_N:X}")
            b.label("c3")
            b.insn("CMP", "R7, #0x1")
            b.insn("BGT", "ask")
            b.insn("MOV", "R7, #0x1")
            b.insn("STRH", "R7, [R4, #0x12]")
            b.insn("B", "next")
            b.label("ask")
            b.insn("STRH", "R7, [R4, #0x12]")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("STR", "R7, [SP, #0x4]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.insn("MOV", f"R2, #0x{NUM_TITLE:X}")
            b.call_addr(NUMBER, R0, R1, R2, NUM_ITEM, via=R7)
            b.insn("B", "next")
            b.label("ph3")
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("CMP", "R0, #0x1")
            b.insn("BLE", "p3msg")
            b.ldr_const(1, UI)
            b.insn("LDR", "R1, [R1, #0x34]")
            b.insn("CMP", "R1, #0x1")
            b.insn("BGE", "p3a")
            b.insn("MOV", "R1, #0x1")
            b.label("p3a")
            b.insn("CMP", "R1, R0")
            b.insn("BLE", "p3b")
            b.insn("ADD", "R1, R0, #0x0")
            b.label("p3b")
            b.insn("STRH", "R1, [R4, #0x12]")
            b.label("p3msg")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", f"R1, #0x{MSG_BANISH:X}")
            b.call_addr(MESSAGE, via=R3)
            b.insn("B", "next")
            b.label("ph4")
            b.insn("LDRH", "R1, [R4, #0x12]")
            b.insn("ADD", "R1, #0x6")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call_addr(PICKER, R0, R1, R2, P_BANISH, via=R7)
            b.insn("B", "next")
            b.label("ph5")
            b.insn("MOV", "R0, #0x58")
            b.insn("CMP", "R5, #0x0")
            b.insn("BEQ", "rv")
            b.ldr_const(1, 0x8000)
            b.insn("ORR", "R0, R1")
            b.label("rv")
            b.insn("MOV", "R1, #0xC")
            b.insn("LDRH", "R2, [R4, #0x18]")
            b.call_addr(UI_CMD, R0, R1, R2, 0, via=R7)
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("MOV", "R7, #0x1")
            b.label("blp")
            b.ldr_const(0, UI)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("CMP", "R7, R0")
            b.insn("BGT", "bend")
            b.call_addr(PICK_AT, R7, via=R3)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R1, R1, R0")
            b.insn("STR", "R1, [SP, #0x4]")
            b.call_addr(GY_INDEX, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "notgy")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDR", "R1, [SP, #0x0]")
            b.call_addr(GY_BANISH, R0, R1, 0, via=R3)
            b.insn("B", "bnx")
            b.label("notgy")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDR", "R1, [SP, #0x4]")
            b.call_addr(HAND_INDEX, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "noth")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(HAND_BANISH, R5, via=R3)
            b.insn("B", "bnx")
            b.label("noth")
            b.insn("LDR", "R0, [SP, #0x4]")
            b.call_addr(ON_FIELD, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "bnx")
            b.insn("LSL", "R1, R0, #0x10")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R0, R0, #0x18")
            b.insn("LSR", "R0, R0, #0x18")
            b.call_addr(FIELD_BANISH, R0, R1, 0, via=R3)
            b.label("bnx")
            b.insn("ADD", "R7, #0x1")
            b.insn("B", "blp")
            b.label("bend")
            b.call_addr(CHAIN_POP, via=R3)
            b.insn("B", "next")
            b.label("ph6")
            b.call_addr(ED_CLOSE, R5, via=R3)
            b.call_addr(ED_TOP, R5, via=R3)
            b.call_addr(ED_CLOSE, R5, via=R3)
            b.label("done")
            b.insn("MOV", "R0, #0x1")
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("next")
            b.insn("LDR", "R0, [R6, #0x7C]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.insn("MOV", "R0, #0x0")
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, "COST")


        def _mat_param(b: EffectBuilder, reg: Reg) -> None:
            """reg = P_MAT | fusion (desc+0x14) | excl (desc+0x16) << EXCL_SHIFT.  Clobbers r0."""
            b.insn("LDRH", f"{reg!r}, [R4, #0x16]")
            b.insn("LSL", f"{reg!r}, {reg!r}, #{EXCL_SHIFT}")
            b.insn("LDRH", "R0, [R4, #0x14]")
            b.insn("ORR", f"{reg!r}, R0")
            b.ldr_const(0, P_MAT)
            b.insn("ORR", f"{reg!r}, R0")


        def build_res(base: int) -> bytes:
            """+04 (desc, ev), phase [STATE+0x70]: 0x80 open, excl = k = 0 | 0x7F k < N, may SS, free zone,
            a MAT candidate -> prompt | 0x7E pick 1 (MAT) | 0x7D exclude every slot naming it, k++,
            Special Summon it (0x02269314 as 0x02206F40) -> 0x7F | 0x78 shuffle, close.
            desc: +0x12 N, +0x14 fusion cid, +0x16 excluded recipe slots, +0x1A k.
            Frame: [sp] ev, [sp+4] picked cid, [sp+8] recipe count."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x10")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("STR", "R1, [SP, #0x0]")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x6]")
            b.insn("EOR", "R5, R0")
            b.ldr_const(6, STATE)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BEQ", "p80")
            b.insn("CMP", "R0, #0x7F")
            b.insn("BEQ", "p7f")
            b.insn("CMP", "R0, #0x7E")
            b.insn("BEQ", "p7e")
            b.insn("CMP", "R0, #0x7D")
            b.insn("BEQ", "p7d")
            b.insn("CMP", "R0, #0x78")
            b.insn("BEQ", "p78j")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("p78j")
            b.insn("B", "p78")
            b.label("p80")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDR", "R1, [SP, #0x0]")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.insn("STRH", "R0, [R4, #0x16]")
            b.insn("STRH", "R0, [R4, #0x1A]")
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("p7f")
            b.insn("LDRH", "R0, [R4, #0x1A]")
            b.insn("LDRH", "R1, [R4, #0x12]")
            b.insn("CMP", "R0, R1")
            b.insn("BGE", "to78")
            b.call_addr(MAY_SS, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "to78")
            b.call_addr(FREE_ZONE, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "to78")
            _mat_param(b, R7)
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, R0, R1, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "to78")
            b.call_addr(MESSAGE, R5, MSG_SS, via=R3)
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("to78")
            b.insn("MOV", "R0, #0x78")
            b.insn("B", "ret")
            b.label("p7e")
            _mat_param(b, R7)
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R1, #0x6")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call_addr(PICKER, R0, R1, R2, R7, via=R6)
            b.insn("MOV", "R0, #0x7D")
            b.insn("B", "ret")
            b.label("p7d")
            b.call_addr(READBACK, via=R3)
            b.insn("ADD", "R7, R0, #0x0")
            b.insn("LDR", "R0, [R7, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("LDRH", "R0, [R4, #0x14]")
            b.call_addr(RECIPE_COUNT, via=R3)
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("MOV", "R6, #0x0")
            b.label("xl")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("CMP", "R6, R0")
            b.insn("BGE", "xend")
            b.insn("LDRH", "R0, [R4, #0x14]")
            b.call_addr(RECIPE_SLOT, R0, R6, via=R3)
            b.ldr_const(1, LITERAL)
            b.insn("CMP", "R0, R1")
            b.insn("BLT", "xnx")
            b.insn("ADD", "R1, R0, #0x0")
            b.insn("LDR", "R0, [SP, #0x4]")
            b.call_addr(SAME_NAME, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "xnx")
            b.insn("MOV", "R0, #0x1")
            b.insn("LSL", "R0, R6")
            b.insn("LDRH", "R1, [R4, #0x16]")
            b.insn("ORR", "R1, R0")
            b.insn("STRH", "R1, [R4, #0x16]")
            b.label("xnx")
            b.insn("ADD", "R6, #0x1")
            b.insn("B", "xl")
            b.label("xend")
            b.insn("LDRH", "R0, [R4, #0x1A]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x1A]")
            b.insn("LDRH", "R3, [R4, #0x0]")
            b.insn("LSL", "R3, R3, #0x10")
            b.call_addr(SUMMON, R5, R7, 1, via=R6)
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("p78")
            b.call_addr(SHUFFLE, R5, via=R3)
            b.call_addr(CHAIN_POP, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, "RES")


        # ----------------------------------------------------------------------------- cls2 (C3) ----
        def build_gycond(base: int) -> bytes:
            """+0C (desc, arg): >= 3 own banished Ojama monsters (param BANISHED).  desc[+7] passes."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x7]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "yes")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x6]")
            b.insn("EOR", "R0, R1")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT_ND, R0, R1, P_BANISHED, via=R3)
            b.insn("CMP", f"R0, #0x{TARGETS:X}")
            b.insn("BGE", "yes")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            return _check(b.assemble(base, pad="nop"), base, "GYCOND")


        def build_gysel(base: int) -> bytes:
            """+14 (desc, arg): the multi-select template's tail 0x02235912, sub-step [SEL_STEP], with the
            count code / prompt fixed (Miracle Dig) and the param fixed to BANISHED instead of 0x02234E78(desc).
            0 count >= 3 else return 1; prompt | 1 picker | 2.. record pick i (the native recorders)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x6]")
            b.insn("EOR", "R5, R0")
            b.ldr_const(6, SEL_STEP)
            b.insn("LDR", "R0, [R6, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "s0")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "s1")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "s2")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("s0")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT_ND, R0, R1, P_BANISHED, via=R3)
            b.insn("CMP", f"R0, #0x{TARGETS:X}")
            b.insn("BGE", "s0ok")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("s0ok")
            b.call_addr(SET_PROMPT, MSG_TARGET, via=R3)
            b.call_addr(SET_MAX, COUNT_CODE - 6, via=R3)
            b.call_addr(MESSAGE, R5, 1, via=R3)
            b.insn("B", "bump")
            b.label("s1")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", f"R1, #0x{COUNT_CODE:X}")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call_addr(PICKER, R0, R1, R2, P_BANISHED, via=R7)
            b.insn("LDR", "R0, [R6, #0x0]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R6, #0x4]")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("s2")
            b.insn("LDR", "R3, [R6, #0x4]")
            b.insn("ADD", "R0, R3, #0x1")
            b.insn("STR", "R0, [R6, #0x4]")
            b.ldr_const(2, UI)
            b.insn("LDR", "R2, [R2, #0x34]")
            b.insn("CMP", "R3, R2")
            b.insn("BGE", "bump")
            b.call_addr(PICK_AT, via=R3)
            b.insn("ADD", "R7, R0, #0x0")
            b.insn("LDR", "R0, [R6, #0x4]")
            b.call_addr(PICK_SEL, via=R3)
            b.call_addr(PICK_ZONE, via=R3)
            b.insn("CMP", "R0, #0xA")
            b.insn("BGT", "lst")
            b.call_addr(PICK_ZONE, via=R3)
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDRB", "R1, [R4, #0x2]")
            b.call_addr(REC_BOARD, R4, via=R3)
            b.insn("B", "ret0")
            b.label("lst")
            b.call_addr(PICK_ZONE, via=R3)
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDR", "R3, [R7, #0x0]")
            b.insn("LSL", "R1, R3, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R3, R3, #0x1")
            b.insn("LSR", "R3, R3, #0x18")
            b.insn("LSL", "R3, R3, #0x1")
            b.insn("ADD", "R3, R1, R3")
            b.call_addr(REC_LIST, R4, via=R7)
            b.insn("B", "ret0")
            b.label("bump")
            b.insn("LDR", "R0, [R6, #0x0]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x0]")
            b.label("ret0")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, "GYSEL")


        def build_gyres(base: int) -> bytes:
            """+04 (desc, ev) = Pot of Avarice 0x0221FB94 on the banished zone, phase [STATE+0x70]:
            0x80 every target still banished (else 0: nothing happens), ok = 1, left = n, open -> 0x7F |
            0x7F per target (last first): still a legal target -> banished->Deck, else ok = 0 -> 0x7F; none
            left -> 0x7E | 0x7E close + Deck shuffle -> 0x7D | 0x7D ok -> draw 1.  [STATE+0x74] ok, +0x78 left."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x6]")
            b.insn("EOR", "R5, R0")
            b.ldr_const(6, STATE)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BEQ", "p80")
            b.insn("CMP", "R0, #0x7F")
            b.insn("BEQ", "p7f")
            b.insn("CMP", "R0, #0x7E")
            b.insn("BEQ", "p7e")
            b.insn("CMP", "R0, #0x7D")
            b.insn("BEQ", "p7d")
            b.insn("B", "zero")
            b.label("p80")
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.insn("MOV", "R7, #0x0")
            b.label("chk")
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("CMP", "R7, R0")
            b.insn("BGE", "chkok")
            b.call_addr(PICK, R4, R7, via=R3)
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(BAN_INDEX, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "zero")
            b.insn("ADD", "R7, #0x1")
            b.insn("B", "chk")
            b.label("chkok")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x74]")
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("STR", "R0, [R6, #0x78]")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("MOV", "R0, #0x7F")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("p7f")
            b.insn("LDR", "R7, [R6, #0x78]")
            b.insn("CMP", "R7, #0x0")
            b.insn("BEQ", "to7e")
            b.insn("SUB", "R7, #0x1")
            b.call_addr(TARGET_OK, R4, R7, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "bad")
            b.call_addr(PICK, R4, R7, via=R3)
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(BAN_TO_DECK, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "dec")
            b.label("bad")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R6, #0x74]")
            b.label("dec")
            b.insn("STR", "R7, [R6, #0x78]")
            b.insn("MOV", "R0, #0x7F")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("to7e")
            b.insn("MOV", "R0, #0x7E")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("p7e")
            b.call_addr(CHAIN_POP, via=R3)
            b.call_addr(DECK_SHUFFLE, via=R3)
            b.insn("MOV", "R0, #0x7D")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("p7d")
            b.insn("LDR", "R0, [R6, #0x74]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.call("draw", R5, 1, via=R3)
            b.call_addr(CHAIN_POP, via=R3)
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, "GYRES")


        STUBS = ((OJ, build_oj), (OPRED, build_opred), (HAS, build_has), (ZCAP, build_zcap),
                 (RPRED, build_rpred), (HANDLER, build_handler), (COND, build_cond),
                 (COST, build_cost), (RES, build_res),
                 (GYCOND, build_gycond), (GYSEL, build_gysel), (GYRES, build_gyres))


        # ------------------------------------------------------------------------------ tables -----


        def _rows(ov) -> list[tuple]:
            return [struct.unpack_from(CRIT_FMT, ov, _off(CRIT_BASE) + i * 12) for i in range(CRIT_COUNT)]


        def _cls0_addr(ov) -> int:
            for i in range(CLS0_COUNT):
                a = CLS0_BASE + i * CLS0_STRIDE
                if struct.unpack_from("<H", ov, _off(a))[0] == DONOR_CID:
                    return a
            raise AssertionError(f"no cls0 record for 0x{DONOR_CID:04X}")


        def _gyreg(ov) -> list[tuple]:
            return [struct.unpack_from("<4I", ov, _off(GYREG_BASE) + i * 16) for i in range(GYREG_COUNT)]


        def _cls2(ov) -> list[tuple]:
            return [struct.unpack_from("<6I", ov, _off(CLS2_BASE) + i * CLS2_STRIDE) for i in range(CLS2_COUNT)]


        def apply_c3_tables(ov: bytearray) -> None:
            insert_row_wide(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, "<6I", CLS2_ROW, CLS2_PHANTOM,
                                 "E  cls2", wide=True)
            rows = _gyreg(ov)
            if GYREG_ROW in rows:
                print("E  GY-action registry: already converted")
                return
            assert DONOR_CID not in [r[0] for r in rows], "GY-action registry: donor already has a row"
            i = rows.index(GYREG_PHANTOM_ROW)
            struct.pack_into("<4I", ov, _off(GYREG_BASE) + i * 16, *GYREG_ROW)
            print(f"E  GY-action registry row {i}: phantom 0x{CLS2_PHANTOM:04X} -> 0x{DONOR_CID:04X}, Grapha family")


        def apply_tables(ov: bytearray) -> None:
            apply_c3_tables(ov)
            a = _cls0_addr(ov)
            cur = struct.unpack_from("<6I", ov, _off(a))
            if cur != CLS0_PATCHED:
                assert cur == CLS0_NATIVE, f"cls0 0x{DONOR_CID:04X} = {[hex(x) for x in cur]}, not stock"
                struct.pack_into("<6I", ov, _off(a), *CLS0_PATCHED)
            print(f"A  cls0 @0x{a:08X} -> {[hex(x) for x in CLS0_PATCHED]}")

            rows = _rows(ov)
            if [r for r in rows if r[0] == DONOR_CID] == [CRIT_ROW]:
                print("B  criteria: already applied")
                return
            assert DONOR_CID not in [r[0] for r in rows], "criteria: donor already has rows"
            kept = [r for r in rows if r[0] != PHANTOM]
            assert len(kept) == CRIT_COUNT - 1, f"criteria: phantom 0x{PHANTOM:04X} owns {CRIT_COUNT - len(kept)} rows"
            pos = sum(1 for r in kept if r[0] < DONOR_CID)
            out = kept[:pos] + [CRIT_ROW] + kept[pos:]
            keys = [r[0] for r in out]
            assert keys == sorted(keys), "criteria lost its sort"
            for i, r in enumerate(out):
                struct.pack_into(CRIT_FMT, ov, _off(CRIT_BASE) + i * 12, *r)
            print(f"B  criteria: dropped 0x{PHANTOM:04X}, inserted 0x{DONOR_CID:04X} @{pos}")


        def _thunk_state(d: bytes) -> tuple:
            u32 = lambda a: struct.unpack_from("<I", d, a - ARM9_BASE)[0]
            return (u32(SETCODE_PTR_TABLE + SETCODE * 4), u32(LIST_LIT),
                    struct.unpack_from("<H", d, COUNT_IMM - ARM9_BASE)[0])


        def _ojama_list(d: bytes) -> tuple:
            return struct.unpack_from(f"<{len(OJAMA_STOCK)}H", d, OJAMA_LIST - ARM9_BASE)


        def apply_setcode(rom) -> None:
            """raiden's recipe: swap the phantom for the donor in place, re-sorted, thunk untouched."""
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)
            assert _thunk_state(bytes(d)) == (THUNK | 1, OJAMA_LIST, 0x2200 | len(OJAMA_STOCK)), "F thunk not stock"
            cur = _ojama_list(bytes(d))
            if cur == OJAMA_GROUP:
                return
            assert cur == OJAMA_STOCK, "F stock Ojama list moved"
            struct.pack_into(f"<{len(OJAMA_GROUP)}H", d, OJAMA_LIST - ARM9_BASE, *OJAMA_GROUP)
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            print(f"F  set code 0x0D: phantom 0x{OJAMA_DROPPED:04X} -> 0x{DONOR_CID:04X} in the ARM9 Ojama list")

        stubs = tuple((addr, build(addr), f"stub @{addr:#x}") for addr, build in STUBS)

        def install(rom, view):
            apply_setcode(rom)
            apply_tables(view.buf)

        def check_fn(c, rom, view):
            ov = bytes(view.buf)
            rows = _rows(ov)
            keys = [r[0] for r in rows]
            ok_text, msg = True, ""
            a9 = bytes(ov5_cave._arm9_main(rom)[1].data)
            checks = [
                ("F set code 0x0D thunk stock",
                 _thunk_state(a9) == (THUNK | 1, OJAMA_LIST, 0x2200 | len(OJAMA_STOCK))),
                ("F ARM9 Ojama list = stock - 0x0EB0 + 0x170F, sorted", _ojama_list(a9) == OJAMA_GROUP),
                ("A cls0 record", struct.unpack_from("<6I", ov, _off(_cls0_addr(ov))) == CLS0_PATCHED),
                ("B criteria row (by cid)", [r for r in rows if r[0] == DONOR_CID] == [CRIT_ROW]),
                ("B phantom gone, table sorted", PHANTOM not in keys and keys == sorted(keys)),
                ("E cls2 record (by cid, exactly one)", [r for r in _cls2(ov) if r[0] == DONOR_CID] == [CLS2_ROW]),
                ("E cls2 phantom gone, table sorted",
                 CLS2_PHANTOM not in [r[0] for r in _cls2(ov)]
                 and [r[0] for r in _cls2(ov)] == sorted(r[0] for r in _cls2(ov))),
                ("E GY-action row converted", _gyreg(ov).count(GYREG_ROW) == 1
                 and GYREG_PHANTOM_ROW not in _gyreg(ov)),
                ("C ov5 stubs", all(ov5_cave.read_cave(rom, a, len(b(a))) == b(a) for a, b in STUBS)),
                (f"D text: {msg}", ok_text),
            ]
            for label, good in checks:
                c.ok(good, label)

        return Compiled(stubs, installs=(install,), checks=(check_fn,))


ojamassimilation_effects = normal_spell_reveal_ojama_banish_or_ss_ojama_tokens_and_banished_ojama_to_deck_add_by_gy_banish

SPEC = card(0x170F, ojamassimilation_effects())

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_ojamassimilation.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
