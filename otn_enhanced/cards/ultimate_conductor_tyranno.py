"""Ultimate Conductor Tyranno (LIGHT / Dinosaur / Level 10 / 3500 / 3200) on Sengenjin 0x1265.

    Cannot be Normal Summoned/Set. Must first be Special Summoned (from your hand) by banishing 2 Dinosaur-Type monsters
    from your Graveyard.
    Once per turn, during either player's Main Phase: You can destroy 1 monster in your hand or field, and if you do,
    change all face-up monsters your opponent controls to face-down Defense Position.
    This card can attack all monsters your opponent controls, once each.
    At the start of the Damage Step, if this card attacks a Defense Position monster: You can inflict 1000 damage to your
    opponent, and if you do, send that Defense Position monster to the Graveyard.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, RES_RESERVE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
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
class special_summon_from_hand_banishing_two_dinosaurs_destroy_one_face_down_all_attack_all_damage_step_burn_and_send:
    """Ultimate Conductor Tyranno (Sengenjin 0x1265): cannot be Normal Summoned/Set; hand Special Summon by banishing 2
    Dinosaurs from the GY (Doom Dozer's recipe: criteria row, summon-procedure registry row, ARM9 nomi class-2 list, shared hand-SS
    trampoline, payment dispatch root detoured to set the count 2, ov3 host = the dead body of phantom 0x1AC7); once per turn in
    either Main Phase destroy 1 monster in hand or field, then flip all face-up opponent monsters face-down Defense (cls3 over
    phantom 0x0E46, speed-2 list); attacks all monsters once each (the attack-all lookup is hooked: its list has no phantom);
    at the start of the Damage Step vs a Defense monster burn 1000 and send it to the GY (Sasuke-family cls1 row over 0x0E54
    with a new Zephyros-style phase resolver). Normal duels only (ov5); the ov3 hosts keep working in puzzles. Build on the chain
    ROM: 0x022234C0 is dead only after the chain dropped phantom 0x1AC7. The original code is embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import tg_table
        from otn_enhanced.effects.common import insert_row, read_thunk_list as _read_thunk_list, swap_in_list as _swap_in_list
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid
        PHANTOM = 0x1758                     # in criteria, registry AND class-2 list; no card_prop

        # --- A / B / G: overlay-3 tables --------------------------------------------------------
        CRIT_BASE, CRIT_COUNT, CRIT_FMT = 0x022713C4, 0x56C, "<HHII"
        CRIT_ROW = (DONOR_CID, 0xFFFF, 0x0223CA11, 0x48000002)
        REG_BASE, REG_COUNT, REG_FMT = 0x0228F158, 133, "<II"
        REG_ROW = (DONOR_CID, 0x0226292D)
        CLS_FMT = "<HHIIIII"
        CLS1_BASE, CLS1_COUNT, CLS1_PHANTOM = 0x022860D4, 0x535, 0x0E54
        SASUKE_DEF_COND, YOU_CAN = 0x021F842D, 0x021E51E5
        SASUKE_FD_COND = 0x021F5A1D            # Sasuke Samurai family: face-DOWN Defense ([ACD0]==0, [ACCE]!=0)
        C4COND, C4COND_RESERVE = ov5_cave.CAVE_UCT_C4COND, 0x20

        # --- C: ARM9 nomi class-2 list (dispatch.summon_restriction_classifier) -------------------
        NOMI_LIST, NOMI_POOL, NOMI_COUNT_IMM = 0x0209BE9C, 0x0202321C, 0x020231E0
        DOOM_DOZER = 0x19CA

        # --- D / H: ov5 --------------------------------------------------------------------------
        SSCOND, SSCOND_RESERVE = ov5_cave.CAVE_UCT_SSCOND, 0x40
        RES, RES_RESERVE = ov5_cave.CAVE_UCT_RES, 0xB0

        # --- E / F: ov3 dead body of phantom 0x1AC7 ------------------------------------------------
        OV3_HOST, OV3_HOST_LEN = 0x022234C0, 68
        PAY1_ROOT, PAY1_LIT = 0x02262962, 0x02262BBC           # `ldr r1,[pc,#0x258]` ; `cmp r0,r1`
        PAY1_NECRO, PAY1_RESUME, PAY1_CID = 0x02262A52, 0x02262966, 0x1C81
        AT_THUNK_LIT = 0x021A3FEC                              # thunk 0x021A3FE0's `=0x02022E15`
        BSEARCH = 0x02022E14
        AT_BL_SITES = (0x021A4252, 0x021A58D0, 0x021A67AC)


        def _o(addr: int) -> int:
            return addr - RAM_BASE


        def _a9(addr: int) -> int:
            return addr - 0x02000000


        def _bl(src: int, dst: int) -> bytes:
            off = dst - (src + 4)
            assert -(1 << 22) <= off < (1 << 22), f"BL out of range {off:#x}"
            return struct.pack("<HH", 0xF000 | ((off >> 12) & 0x7FF), 0xF800 | ((off >> 1) & 0x7FF))


        # ---------------------------------------------------------------------------- stubs ----
        def pay1_stub(base: int) -> bytes:
            """E. Entered by `bx r1` from 0x02262964 with r0 = cid, r7 = count (0x0225CF28's answer)."""
            b = EffectBuilder()
            b.ldr_const(1, DONOR_CID)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "native")
            b.insn("MOV", "R7, #0x2")
            b.ldr_const(1, PAY1_NECRO | 1)
            b.insn("BX", "R1")
            b.label("native")
            b.ldr_const(2, PAY1_RESUME | 1)
            b.insn("PUSH", "{R2}")
            b.ldr_const(1, PAY1_CID)
            b.insn("CMP", "R0, R1")
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        def at_stub(base: int) -> bytes:
            """F. Drop-in for bsearch(r0 = cid, r1 = list, r2 = count); clobbers r3 only."""
            b = EffectBuilder()
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R0, R3")
            b.insn("BEQ", "hit")
            b.ldr_const(3, BSEARCH | 1)
            b.insn("BX", "R3")
            b.label("hit")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def ov3_layout() -> tuple[bytes, int, bytes, int]:
            a = pay1_stub(OV3_HOST)
            a += b"\x00" * (-len(a) % 4)
            at_base = OV3_HOST + len(a)
            b = at_stub(at_base)
            assert len(a) + len(b) <= OV3_HOST_LEN, f"ov3 stubs {len(a) + len(b)} B > {OV3_HOST_LEN}"
            return a, at_base, b, OV3_HOST


        def sscond_stub(base: int) -> bytes:
            """D. r0 = side -> nonzero iff the hand-SS offer should appear (0x0225D0D0 with count 2)."""
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
            b.insn("CMP", "R0, #0x2")
            b.insn("BLT", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def _defender(b: EffectBuilder) -> None:
            """Inline: r4 = side, r6 = zone of the attacked monster, or branch to to7e.

            0x02215109's own guards: battle ctx 0x02298AD8 [+5] must be 0, and 0x02196928(side, zone)
            must say a card is there. ldrb/ldrh (the assembler has no ldrsb/ldrsh), so a -1 "no
            defender" reads as 0xFF/0xFFFF and is rejected by the explicit bounds instead.
            """
            b.ldr_const(3, 0x02298AD8)
            b.insn("LDRB", "R0, [R3, #0x5]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "to7e")
            b.insn("LDRB", "R4, [R3, #0x1]")
            b.insn("LDRH", "R6, [R3, #0xA]")
            b.insn("CMP", "R4, #0x1")
            b.insn("BGT", "to7e")
            b.insn("CMP", "R6, #0x4")
            b.insn("BGT", "to7e")
            b.call_addr(0x02196928, R4, R6, via=R3)   # is there a card at (side, zone)?
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "to7e")


        def res_stub(base: int) -> bytes:
            """H. cls1 +04 (r0 = desc, r1 = as received). Phase in [0x0229AAFC + 0x70]."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.ldr_const(3, 0x0229AAFC)
            b.insn("LDR", "R1, [R3, #0x70]")
            b.insn("CMP", "R1, #0x7E")
            b.insn("BEQ", "close")
            b.insn("CMP", "R1, #0x7F")
            b.insn("BEQ", "send")
            b.insn("CMP", "R1, #0x80")
            b.insn("BNE", "ret0")
            b.call_addr(0x021D28A4, via=R3)
            _defender(b)
            b.call_addr(0x021CFBC8, R5, R4, 1000, via=R3)
            b.insn("MOV", "R0, #0x7F")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("send")
            _defender(b)
            b.insn("LSL", "R4, R4, #0x4")
            b.insn("ADD", "R2, R6, R4")
            b.insn("MOV", "R1, #0x1")
            b.insn("LSL", "R1, R2")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R2, #0xE")
            b.insn("MOV", "R3, #0x1")
            b.insn("LSL", "R3, R3, #0xC")
            b.call_addr(0x021CDD4C, via=R7)
            b.label("to7e")
            b.insn("MOV", "R0, #0x7E")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("close")
            b.call_addr(0x021D2964, R5, via=R3)
            b.label("ret0")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        # ------------------------------------------------------------------------------ C2 ----
        # J  cls3 {0x1265, 0, C2RES|1, 0, C2COND|1, 0x021E5061, 0} over phantom 0x0E46 = Junk Defender 0x23FF's
        #    shape ("once per turn, during either player's turn", untargeted): +0C per-copy OPT latch 0x021F01C1
        #    (key 0x0FB6), +10 its stamp 0x021E5061.  C2COND adds the Main-Phase gate ([0x0229DD14+0x48] in {2,4}).
        # K  speed-2 list 0x0209C118: phantom 0x1529 -> 0x1265 (what lets it be used on the opponent's turn).
        # L  C2RES: Hands/Field prompt -> own candidate list through the native recorder -> native picker UI ->
        #    destroy (field 0x021CF374 / hand 0x021D2478) -> if it left, Book of Eclipse's flip on the opponent only.
        CLS3_BASE, CLS3_COUNT, CLS3_PHANTOM = 0x02279D74, 0x308, 0x0E46
        OPT_LATCH_COND, OPT_LATCH_COST = 0x021F01C1, 0x021E5061
        QE_LIST, QE_POOL, QE_COUNT_IMM, QE_PHANTOM = 0x0209C118, 0x020234A4, 0x02023490, 0x1529
        JUNK_DEFENDER = 0x23FF
        C2COND, C2COND_RESERVE = ov5_cave.CAVE_UCT_C2COND, 0x30
        C2HELP, C2HELP_RESERVE = ov5_cave.CAVE_UCT_C2HELP, 0xA0
        C2RES, C2RES_RESERVE = ov5_cave.CAVE_UCT_C2RES, 0x220
        CLS3_REC = (DONOR_CID, 0, C2RES | 1, 0, C2COND | 1, OPT_LATCH_COST, 0)

        PLAYER_HAND_COUNT = 0x0229ACA0          # + side*0xB3C  (player + 0x0C)
        FIELD_CID = 0x0229ACC8                  # + side*0xB3C + zone*0x14: packed card word (player+0x34), low u16 0 = empty.
                                                # NOT 0x0229ACD0 -- that is the FACE-UP flag (0 for a set monster).
        PLAYER_STRIDE = 0xB3C
        SLOT = 0x0219CA29                       # (side, zone code, index) -> &card word
        RECORD = 0x02243B2D                     # (side, zone code, index) -> append to the picker list
        IS_MONSTER = 0x02029E61                 # (cid)
        PROMPT = 0x0219ABB5                     # (desc, title, l0, l1, [sp] l2, [sp+4] l3, [sp+8] mask)
        TITLE, LBL_HAND, LBL_FIELD, MSG_DESTROY = 0x103, 0x192, 0x23C, 0x6D
        MESSAGE = 0x0219A819                    # (side, dlg id)
        PICK_UI = 0x0219C99D                    # (0x37, side, code, 0)
        PICK_HDR, PICK_WORDS, PICK_LOCS = 0x0229944C, 0x02299458, 0x02299908
        CHOICE_STATE = 0x0229DD94               # +0x34 answer, +0x30 / +0x2C picker side / code+0xF
        CTRL_TYPE = 0x0229911C                  # + side*4: 1 = AI, 4 = (no UI)
        DESTROY_FIELD = 0x021CF375              # (desc, side, zone)
        DESTROY_HAND = 0x021D2479               # (side, idx, &slot, src cid, [sp] flag)
        FLIP_OK = 0x021E271D                    # Book of Eclipse's filter (desc, side, zone)
        FLIP = 0x021C5895                       # (desc, side, zone): Book of Moon's face-down DEFENSE (0x02214116).
                                                # NOT 0x021C4F24 -- that is Darkness Approaches' face-down, position kept
                                                # (fix2 in-game: face-down Attack Position).
        OPEN, CLOSE = 0x021D28A5, 0x021D2965
        PICK_CODE = 6                           # "select 1" (souleating_oviraptor PICKER(side, 6, ...))


        def c2_cond_stub(base: int) -> bytes:
            """J +0C: Main Phase of either player (skipped on the desc[+7] re-check), then the OPT latch."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R1, [R4, #0x7]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BNE", "latch")
            b.ldr_const(1, 0x0229DD14)
            b.insn("LDR", "R1, [R1, #0x48]")
            b.insn("CMP", "R1, #0x2")
            b.insn("BEQ", "latch")
            b.insn("CMP", "R1, #0x4")
            b.insn("BEQ", "latch")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            b.label("latch")
            b.call_addr(OPT_LATCH_COND, R4, via=R3)
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def c2_help_stub(base: int) -> bytes:
            """(r0 side, r1 mode 0 = hand / 1 = field, r2 record?) -> count of own monsters there.

            Hand: every hand card whose cid is a monster (0x02029E60). Field: monster zones 0..4 holding a
            card (face-up or face-down). With r2 != 0 each one is also appended to the picker list.
            """
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
            b.ldr_const(1, PLAYER_HAND_COUNT)
            b.insn("CMP", "R4, #0x0")
            b.insn("BEQ", "h0")
            b.ldr_const(0, PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("h0")
            b.insn("LDR", "R0, [R1, #0x0]")
            b.insn("CMP", "R5, R0")
            b.insn("BGE", "done")
            b.call_addr(SLOT, R4, 0xB, R5, via=R3)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call("is_monster", via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "hnext")
            b.insn("ADD", "R6, #0x1")
            b.insn("CMP", "R7, #0x0")
            b.insn("BEQ", "hnext")
            b.call_addr(RECORD, R4, 0xB, R5, via=R3)
            b.label("hnext")
            b.insn("ADD", "R5, #0x1")
            b.insn("B", "hand")
            b.label("field")
            b.insn("CMP", "R5, #0x4")
            b.insn("BGT", "done")
            b.ldr_const(1, FIELD_CID)
            b.insn("CMP", "R4, #0x0")
            b.insn("BEQ", "f0")
            b.ldr_const(0, PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("f0")
            b.insn("LSL", "R0, R5, #0x4")
            b.insn("ADD", "R1, R1, R0")
            b.insn("LSL", "R0, R5, #0x2")
            b.insn("ADD", "R1, R1, R0")
            b.insn("LDRH", "R0, [R1, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "fnext")
            b.insn("ADD", "R6, #0x1")
            b.insn("CMP", "R7, #0x0")
            b.insn("BEQ", "fnext")
            b.call_addr(RECORD, R4, R5, 0, via=R3)
            b.label("fnext")
            b.insn("ADD", "R5, #0x1")
            b.insn("B", "field")
            b.label("done")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("POP", "{R1, R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def c2_res_stub(base: int) -> bytes:
            """L. cls3 +04 (r0 = desc). desc[+0x18] = 0 hand / 1 field, [+0x1A] = picked zone code,
            [+0x1C] = hand count before the destroy. Private phases 0x90..0x94 round-trip (Oviraptor)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2, R3, R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R6, [R5, #0x2]")
            b.insn("LDRB", "R0, [R5, #0x6]")
            b.insn("EOR", "R6, R0")
            b.insn("MOV", "R0, #0x1")
            b.insn("AND", "R6, R0")
            b.ldr_const(4, 0x0229AAFC)
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
            b.insn("CMP", "R0, #0x7E")
            b.insn("BEQ", "p7ej")
            b.insn("B", "stop")
            b.label("p92j")
            b.insn("B", "p92")
            b.label("p93j")
            b.insn("B", "p93")
            b.label("p94j")
            b.insn("B", "p94")
            b.label("p7ej")
            b.insn("B", "p7e")
            b.label("p80")
            b.call_addr(OPEN, R5, 0x80, via=R3)
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
            b.call_addr(PROMPT, R5, TITLE, LBL_HAND, LBL_FIELD, via=R7)
            b.insn("MOV", "R0, #0x90")
            b.insn("B", "ret")
            b.label("onlyfield")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "to7e")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "setans")
            b.label("onlyhand")
            b.insn("MOV", "R0, #0x0")
            b.label("setans")
            b.insn("STRH", "R0, [R5, #0x18]")
            b.insn("MOV", "R0, #0x91")
            b.insn("B", "ret")
            b.label("p90")
            b.ldr_const(0, CHOICE_STATE)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("STRH", "R0, [R5, #0x18]")
            b.insn("MOV", "R0, #0x91")
            b.insn("B", "ret")
            b.label("p91")
            b.call_addr(MESSAGE, R6, MSG_DESTROY, via=R3)
            b.insn("MOV", "R0, #0x92")
            b.insn("B", "ret")
            b.label("to7e")
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("p92")
            b.ldr_const(1, CHOICE_STATE)
            b.insn("STR", "R6, [R1, #0x30]")
            b.insn("MOV", f"R0, #0x{PICK_CODE + 0xF:X}")
            b.insn("STR", "R0, [R1, #0x2C]")
            b.ldr_const(1, PICK_HDR)
            b.insn("STRH", "R6, [R1, #0x0]")
            b.insn("MOV", f"R0, #0x{PICK_CODE:X}")
            b.insn("STRH", "R0, [R1, #0x2]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STRH", "R0, [R1, #0x4]")
            b.insn("STRH", "R0, [R1, #0x6]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("LDRH", "R1, [R5, #0x18]")
            b.call_addr(C2HELP, R0, R1, 1, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "to7e")
            b.insn("LSL", "R0, R6, #0x2")
            b.ldr_const(1, CTRL_TYPE)
            b.insn("LDR", "R0, [R1, R0]")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "auto")
            b.insn("CMP", "R0, #0x4")
            b.insn("BEQ", "auto")
            b.call_addr(PICK_UI, 0x37, R6, PICK_CODE, 0, via=R7)
            b.label("auto")
            b.insn("MOV", "R0, #0x93")
            b.insn("B", "ret")
            b.label("p93")
            b.ldr_const(1, PICK_HDR)
            b.insn("LDRH", "R4, [R1, #0x4]")
            b.insn("LSL", "R0, R4, #0x1")
            b.ldr_const(1, PICK_LOCS)
            b.insn("LDRH", "R0, [R1, R0]")
            b.insn("LSL", "R0, R0, #0x1A")
            b.insn("LSR", "R0, R0, #0x1B")
            b.insn("STRH", "R0, [R5, #0x1A]")
            b.insn("CMP", "R0, #0x4")
            b.insn("BGT", "handkill")
            b.insn("ADD", "R2, R0, #0x0")
            b.call_addr(DESTROY_FIELD, R5, R6, via=R3)
            b.insn("MOV", "R0, #0x94")
            b.insn("B", "ret")
            b.label("handkill")
            b.insn("LSL", "R0, R4, #0x2")
            b.ldr_const(1, PICK_WORDS)
            b.insn("LDR", "R7, [R1, R0]")
            b.ldr_const(1, PLAYER_HAND_COUNT)
            b.insn("CMP", "R6, #0x0")
            b.insn("BEQ", "hk0")
            b.ldr_const(0, PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("hk0")
            b.insn("LDR", "R0, [R1, #0x0]")
            b.insn("STRH", "R0, [R5, #0x1C]")
            b.insn("MOV", "R4, #0x0")
            b.label("hkloop")
            b.insn("LDRH", "R0, [R5, #0x1C]")
            b.insn("CMP", "R4, R0")
            b.insn("BGE", "to7e")
            b.call_addr(SLOT, R6, 0xB, R4, via=R3)
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
            b.call_addr(DESTROY_HAND, R6, R4, via=R7)
            b.insn("MOV", "R0, #0x94")
            b.insn("B", "ret")
            b.label("p94")
            b.insn("LDRH", "R0, [R5, #0x1A]")
            b.insn("CMP", "R0, #0x4")
            b.insn("BGT", "hchk")
            b.ldr_const(1, FIELD_CID)
            b.insn("CMP", "R6, #0x0")
            b.insn("BEQ", "c0")
            b.ldr_const(2, PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R2")
            b.label("c0")
            b.insn("LSL", "R2, R0, #0x4")
            b.insn("ADD", "R1, R1, R2")
            b.insn("LSL", "R2, R0, #0x2")
            b.insn("ADD", "R1, R1, R2")
            b.insn("LDRH", "R0, [R1, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "to7e2")
            b.insn("B", "flip")
            b.label("hchk")
            b.ldr_const(1, PLAYER_HAND_COUNT)
            b.insn("CMP", "R6, #0x0")
            b.insn("BEQ", "hc0")
            b.ldr_const(0, PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("hc0")
            b.insn("LDR", "R0, [R1, #0x0]")
            b.insn("LDRH", "R1, [R5, #0x1C]")
            b.insn("CMP", "R0, R1")
            b.insn("BGE", "to7e2")
            b.label("flip")
            b.insn("MOV", "R7, #0x1")
            b.insn("EOR", "R7, R6")
            b.insn("MOV", "R4, #0x0")
            b.label("floop")
            b.call_addr(FLIP_OK, R5, R7, R4, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "fnx")
            b.call_addr(FLIP, R5, R7, R4, via=R6)
            b.label("fnx")
            b.insn("ADD", "R4, #0x1")
            b.insn("CMP", "R4, #0x4")
            b.insn("BLE", "floop")
            b.label("to7e2")
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("p7e")
            b.call_addr(CLOSE, R5, 0x7E, via=R3)
            b.label("stop")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        # ------------------------------------------------------------------------------ C4 fix ----
        # M  The start-of-Damage-Step poster 0x0224F588..0x0224F666 is a hard-coded BST over the ATTACKER cid (r4);
        #    only a hit reaches 0x0224F668, which posts event 0x15 (0x021D3230) -- without it the cls1 row G is never
        #    offered (in-game test: "no prompt").  Its root `ldr r3,=0x1C2C; cmp r4,r3` becomes
        #    `ldr r3,=M ; bx r3` (literal 0x0224F730, read only there); M sends 0x1265 to the hit leaf and replays the
        #    root for everyone else.  Host: phantom cls3 0x0E46's private cond body 0x021F065C (64 B), dead once J
        #    drops 0x0E46 (no other pointer / BL in stock, the chain or this ROM).  ov3: battles run in puzzles too.
        DMG_ROOT, DMG_LIT, DMG_HIT, DMG_RESUME, DMG_PIVOT = 0x0224F588, 0x0224F730, 0x0224F668, 0x0224F58C, 0x1C2C
        M_HOST, M_HOST_LEN = 0x021F065C, 64


        def dmg_stub(base: int) -> bytes:
            """Entered by `bx r3` from 0x0224F58A with r4 = attacker cid. Clobbers r0 (dead) and r3 only."""
            b = EffectBuilder()
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R4, R3")
            b.insn("BNE", "native")
            b.ldr_const(0, DMG_HIT | 1)
            b.insn("BX", "R0")
            b.label("native")
            b.ldr_const(0, DMG_RESUME | 1)
            b.insn("PUSH", "{R0}")
            b.ldr_const(3, DMG_PIVOT)
            b.insn("CMP", "R4, R3")
            b.insn("POP", "{PC}")
            return b.assemble(base, pad="nop")


        def apply_dmg_hook(ov: bytearray, stock_ov3: bytes) -> None:
            blob = dmg_stub(M_HOST)
            assert_thumb1_only(blob, M_HOST)
            assert len(blob) <= M_HOST_LEN, f"M stub {len(blob)} B > {M_HOST_LEN}"
            keys = [struct.unpack_from("<H", ov, _o(CLS3_BASE + i * 24))[0] for i in range(CLS3_COUNT)]
            assert CLS3_PHANTOM not in keys, "M: host is only dead after J has dropped cls3 phantom 0x0E46"
            cur = bytes(ov[_o(M_HOST):_o(M_HOST) + len(blob)])
            if cur != blob:
                assert cur == stock_ov3[_o(M_HOST):_o(M_HOST) + len(blob)], f"M host {M_HOST:#x} is not stock"
                ov[_o(M_HOST):_o(M_HOST) + len(blob)] = blob
                print(f"M  Damage-Step poster stub @{M_HOST:#x} ({len(blob)} B)")
            assert struct.unpack_from("<H", ov, _o(DMG_ROOT))[0] == 0x4B69, "M root is not ldr r3,[pc,#0x1A4]"
            assert struct.unpack_from("<I", ov, _o(DMG_LIT))[0] in (DMG_PIVOT, M_HOST | 1), "M literal drifted"
            assert struct.unpack_from("<H", ov, _o(DMG_ROOT + 2))[0] in (0x429C, 0x4718), "M root+2 drifted"
            struct.pack_into("<I", ov, _o(DMG_LIT), M_HOST | 1)
            struct.pack_into("<H", ov, _o(DMG_ROOT + 2), 0x4718)            # bx r3


        def _ov5_blobs() -> list[tuple[str, int, bytes, int]]:
            return [("D  hand-SS cond", SSCOND, sscond_stub(SSCOND), SSCOND_RESERVE),
                    ("H  C4 resolver", RES, res_stub(RES), RES_RESERVE),
                    ("G  C4 cond", C4COND, c4cond_stub(C4COND), C4COND_RESERVE),
                    ("J  C2 cond", C2COND, c2_cond_stub(C2COND), C2COND_RESERVE),
                    ("L  C2 list helper", C2HELP, c2_help_stub(C2HELP), C2HELP_RESERVE),
                    ("L  C2 resolver", C2RES, c2_res_stub(C2RES), C2RES_RESERVE)]


        def c4cond_stub(base: int) -> bytes:
            """G +0C. "if this card attacks a Defense Position monster" = either face.  0x021F842D alone is face-UP only
            (it requires the face-up flag 0x0229ACD0 != 0) -- in-game 2026-09-28 a face-down target got no prompt."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(SASUKE_DEF_COND, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "out")
            b.call_addr(SASUKE_FD_COND, R4, via=R3)
            b.label("out")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        CLS1_REC = (DONOR_CID, 0, RES | 1, 0, C4COND | 1, YOU_CAN, 0)


        # ---------------------------------------------------------------------------- apply ----
        def apply_overlay(ov: bytearray, stock_ov3: bytes) -> None:
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, CRIT_ROW, PHANTOM, "A  criteria")
            insert_row(ov, REG_BASE, REG_COUNT, 8, REG_FMT, REG_ROW, PHANTOM, "B  registry")
            insert_row(ov, CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, CLS1_REC, CLS1_PHANTOM, "G  cls1")
            jd = [struct.unpack_from(CLS_FMT, ov, _o(CLS3_BASE + i * 24)) for i in range(CLS3_COUNT)]
            assert (JUNK_DEFENDER, 0, 0x02208499, 0, OPT_LATCH_COND, OPT_LATCH_COST, 0) in jd, \
                "J: Junk Defender's cls3 template drifted"
            insert_row(ov, CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, CLS3_REC, CLS3_PHANTOM, "J  cls3")

            a, at_base, b, host = ov3_layout()
            for blob, base in ((a, host), (b, at_base)):
                assert_thumb1_only(blob, base)
            blob = a + b
            cur = bytes(ov[_o(host):_o(host) + len(blob)])
            if cur != blob:
                assert cur == stock_ov3[_o(host):_o(host) + len(blob)], \
                    f"E/F host {host:#x} is not 0x1AC7's stock dead body -- claimed by someone else?"
                ov[_o(host):_o(host) + len(blob)] = blob
                print(f"E/F ov3 stubs @{host:#x} ({len(a)} + {len(b)} B)")

            # E: dispatch-1 root -> PAY1
            lit = struct.unpack_from("<I", ov, _o(PAY1_LIT))[0]
            assert lit in (PAY1_CID, host | 1), f"E literal {PAY1_LIT:#x} = {lit:#x}"
            assert struct.unpack_from("<H", ov, _o(PAY1_ROOT))[0] == 0x4996, "E root is not ldr r1,[pc,#0x258]"
            assert struct.unpack_from("<H", ov, _o(PAY1_ROOT + 2))[0] in (0x4288, 0x4708), "E root+2 drifted"
            struct.pack_into("<I", ov, _o(PAY1_LIT), host | 1)
            struct.pack_into("<H", ov, _o(PAY1_ROOT + 2), 0x4708)            # bx r1

            # F: the thunk's bsearch literal + the three inline bsearch calls -> AT
            lit = struct.unpack_from("<I", ov, _o(AT_THUNK_LIT))[0]
            assert lit in (BSEARCH | 1, at_base | 1), f"F thunk literal = {lit:#x}"
            struct.pack_into("<I", ov, _o(AT_THUNK_LIT), at_base | 1)
            for site in AT_BL_SITES:
                cur = bytes(ov[_o(site):_o(site) + 4])
                assert cur in (_bl(site, BSEARCH), _bl(site, at_base)), f"F {site:#x} is not bl bsearch"
                ov[_o(site):_o(site) + 4] = _bl(site, at_base)


        def apply_arm9(rom) -> None:
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)
            base, n, lst = _read_thunk_list(bytes(d), NOMI_POOL, NOMI_COUNT_IMM, NOMI_LIST, "C  nomi class 2")
            if DONOR_CID not in lst:
                assert DOOM_DOZER in lst, "C: Doom Dozer missing -- wrong list"
                struct.pack_into(f"<{n}H", d, _a9(base), *_swap_in_list(lst, PHANTOM, DONOR_CID, "C nomi"))
                print(f"C  nomi class 2: {PHANTOM:#06x} -> {DONOR_CID:#06x}")
            base, n, lst = _read_thunk_list(bytes(d), QE_POOL, QE_COUNT_IMM, QE_LIST, "K  speed-2")
            if DONOR_CID not in lst:
                assert JUNK_DEFENDER in lst, "K: Junk Defender missing -- wrong list"
                struct.pack_into(f"<{n}H", d, _a9(base), *_swap_in_list(lst, QE_PHANTOM, DONOR_CID, "K speed-2"))
                print(f"K  speed-2: {QE_PHANTOM:#06x} -> {DONOR_CID:#06x}")
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        def install(rom, view):
            from otn_enhanced.rom import stock as _stock
            stock = _stock.ov3()
            apply_overlay(view.buf, stock)
            apply_dmg_hook(view.buf, stock)
            tg_table.register_tg_handss(rom, view.buf, DONOR_CID, SSCOND)
            apply_arm9(rom)

        def check_fn(c, rom, view):
            ov = view.buf

            def check(cond, msg):
                c.ok(bool(cond), msg)

            for label, base, cnt, stride, fmt, rec, ph in (
                    ("A criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, CRIT_ROW, PHANTOM),
                    ("B registry", REG_BASE, REG_COUNT, 8, REG_FMT, REG_ROW, PHANTOM),
                    ("G cls1", CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, CLS1_REC, CLS1_PHANTOM),
                    ("J cls3", CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, CLS3_REC, CLS3_PHANTOM)):
                rows = [struct.unpack_from(fmt, ov, base - RAM_BASE + i * stride) for i in range(cnt)]
                keys = [r[0] for r in rows]
                check(all(keys[i] <= keys[i + 1] for i in range(cnt - 1)), f"{label} still sorted")
                check([r for r in rows if r[0] == DONOR_CID] == [rec], f"{label} donor row == spec")
                check(ph not in keys, f"{label} phantom {ph:#06x} dropped")

            a, at_base, b, host = ov3_layout()
            check(bytes(ov[_o(host):_o(host) + len(a + b)]) == a + b, f"E/F ov3 stubs @{host:#x}")
            check(struct.unpack_from("<I", ov, _o(PAY1_LIT))[0] == host | 1
                  and struct.unpack_from("<H", ov, _o(PAY1_ROOT + 2))[0] == 0x4708, "E dispatch-1 root -> PAY1")
            check(struct.unpack_from("<I", ov, _o(AT_THUNK_LIT))[0] == at_base | 1, "F thunk literal -> AT")
            mb = dmg_stub(M_HOST)
            check(bytes(ov[_o(M_HOST):_o(M_HOST) + len(mb)]) == mb, f"M Damage-Step stub @{M_HOST:#x}")
            check(struct.unpack_from("<I", ov, _o(DMG_LIT))[0] in (M_HOST | 1, ov5_cave.CAVE_GF_DMG | 1)   # Gearfried's front may sit ahead
                  and struct.unpack_from("<H", ov, _o(DMG_ROOT + 2))[0] == 0x4718, "M poster root -> stub")
            for site in AT_BL_SITES:
                check(bytes(ov[_o(site):_o(site) + 4]) == _bl(site, at_base), f"F bl @{site:#x} -> AT")

            for label, addr, blob, _ in _ov5_blobs():
                check(ov5_cave.read_cave(rom, addr, len(blob)) == blob, f"{label} installed @{addr:#x}")
            check(tg_table.tg_handss_ok(rom, ov, DONOR_CID), "D hand-SS trampoline row")

            mc, sec = ov5_cave._arm9_main(rom)
            _, _, l9 = _read_thunk_list(bytes(sec.data), NOMI_POOL, NOMI_COUNT_IMM, NOMI_LIST, "C")
            check(DONOR_CID in l9 and PHANTOM not in l9 and all(l9[i] < l9[i + 1] for i in range(len(l9) - 1)),
                  "C nomi class 2: donor in, phantom gone, strictly sorted")
            _, _, q9 = _read_thunk_list(bytes(sec.data), QE_POOL, QE_COUNT_IMM, QE_LIST, "K")
            check(DONOR_CID in q9 and QE_PHANTOM not in q9 and all(q9[i] < q9[i + 1] for i in range(len(q9) - 1)),
                  "K speed-2: donor in, phantom gone, strictly sorted")

        stubs = tuple((addr, blob, label) for label, addr, blob, reserve in _ov5_blobs())
        for addr, blob, _l in stubs:
            assert_thumb1_only(blob, addr)
        return Compiled(stubs, installs=(install,), checks=(check_fn,))


tyranno_effects = special_summon_from_hand_banishing_two_dinosaurs_destroy_one_face_down_all_attack_all_damage_step_burn_and_send

SPEC = card(0x1265, tyranno_effects())

PROPS = card_props("LIGHT", "Dinosaur", level=10, atk=3500, defense=3200)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_ultimate_conductor_tyranno.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
