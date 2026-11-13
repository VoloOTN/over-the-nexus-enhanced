"""Eva (LIGHT / Fairy / Level 1 / 500 / 200) on Aitsu 0x160A.

    If this card is sent to the GY: You can banish up to 2 other LIGHT Fairy monsters from your field and/or GY; add
    the same number of Level 2 or lower LIGHT Fairy monsters with different names from your Deck to your hand, except
    "Eva". You can only use this effect of "Eva" once per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, CLS2, CRITERIA, Compiled, LEAVE_MASK, Row
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
from otn_enhanced.rom.overlay_io import load_overlay3
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class sent_to_graveyard_banish_light_fairies_add_same_number_of_low_level_light_fairies_with_different_names:
    """'If this card is sent to the GY: You can banish up to 2 other LIGHT Fairy monsters from your field and/or GY; add the
    same number of Level 2 or lower LIGHT Fairy monsters with different names from your Deck to your hand, except this card.
    Once per turn.' Sent from ANY location, "You can", never misses the timing (Shadow Mist C2's recipe): leave-mask row
    (field sends), cls2 record with the native "You can" tag, sent-to-GY cid chain node 0x021D1436 BL'd to an ov3 stub in a
    dead block (Neko Mane King kept, the donor routed to the unconditional accept), and the miss-timing node fronted so the
    donor never misses. One criteria row whose ov5 handler switches on param >> 16 (1 = banish candidates: GY builder plus
    own face-up field matches, 2 = Deck builder). Cost phases: stamp OPT, min(2, banish candidates, distinct Deck names),
    number picker, pick exactly N, banish; resolver adds one distinct-name target per entry with the native mover. The two
    ov3 stubs are written by `install` (the first sits on a stock dead tail, not a zero slot)."""

    def __post_init__(self):
        from otn_enhanced.cards import snoww as sn
        sn.register_switch_stub(0x02221328, 18, {0x160A: 0x021D199E})

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.cards import shadow_mist as _sm, snoww as _snoww
        from otn_enhanced.effects import timing_class_hook as tch
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid
        CLS_FMT = "<HHIIIII"
        CLS2_BASE, CLS2_COUNT, CLS2_PHANTOM = 0x02275C04, 0x2B9, 0x1775
        CRIT_BASE, CRIT_COUNT, CRIT_FMT, CRIT_PHANTOM = 0x022713C4, 0x56C, "<HHII", 0x15D0
        MASK_BASE, MASK_COUNT, MASK_FMT, MASK_PHANTOM = 0x0226EC1C, 0x98, "<Hh", 0x0E4A

        YOU_CAN = 0x021E51E5                # native class-2 "You can" tag (classifier 0x0224AFA0)
        DECK_WORD = 0x89880022              # Fairy | LIGHT | Lv<=2 | monster | except this card
        BANISH_WORD = 0x89000002            # Fairy | LIGHT | monster
        P_BANISH, P_DECK = 0x10000, 0x20000
        DECK_FLAGS, BANISH_FLAGS = 0xA, 0x10000

        BPRED, DPRED, HANDLER = ov5_cave.CAVE_EVA_BPRED, ov5_cave.CAVE_EVA_DPRED, ov5_cave.CAVE_EVA_HANDLER
        COND, COST, RES = ov5_cave.CAVE_EVA_COND, ov5_cave.CAVE_EVA_COST, ov5_cave.CAVE_EVA_RES
        RESERVE = {BPRED: 0x30, DPRED: 0x30, HANDLER: 0xC0, COND: 0x60, COST: 0x1C0, RES: 0x100}

        CLS2_REC = (DONOR_CID, 0, RES | 1, 0, COND | 1, YOU_CAN, COST | 1)
        CRIT_ROW = (DONOR_CID, 0xFFFF, HANDLER | 1, DECK_WORD)
        MASK_ROW = (DONOR_CID, 0x0800)

        # --- natives (all Thumb entry points, bit 0 set) ----------------------------------------------
        PLAYER_STRIDE = 0xB3C
        FIELD = 0x0229ACC8                  # + side*0xB3C + zone*0x14: +0 card word, +8 face-up
        SAME_NAME = 0x02022E99              # (cid, cid) -> nonzero when the names match
        DECK_B, GY_B = 0x0223BC3D, 0x0223C4E9
        MATCH = 0x0223BA25                  # (side, zone, &card word, word) -> 1 on a match
        RECORD = 0x02243B2D                 # (side, zone, idx) -> append a field card to the pick list
        COUNT = 0x02243FA9                  # (side, cid, param) -> candidate count
        CAND = 0x02299458                   # candidate card words after COUNT
        STATE = 0x0229AAFC                  # +0x7C cost phase, +0x70 resolver phase
        UI = 0x0229DD94                     # +0x34 number / pick-count answer
        SHORTCIRCUIT = 0x021D2BC9
        MESSAGE, PICKER, READBACK, PICK_AT = 0x0219A819, 0x0219C431, 0x0219C511, 0x0219C94D
        NUMBER = 0x0219AE11                 # (side, cid, title, item, [sp] min, [sp+4] max)
        CHAIN_PUSH, CHAIN_POP = 0x021D28A5, 0x021D2965
        GY_INDEX, GY_BANISH = 0x021A2511, 0x021C7105
        ON_FIELD, FIELD_BANISH = 0x021A241D, 0x021CF40D
        ADD_HAND, SHUFFLE = 0x021C72CD, 0x021D269D
        TURNLOG_QUERY, TURNLOG_POST = 0x021A14E9, 0x021D2585
        KIND = 1
        MSG_BANISH, MSG_ADD = 0x46, 0x33
        NUM_TITLE, NUM_ITEM = 0xA4, 0x11B

        for _v in (YOU_CAN, SAME_NAME, DECK_B, GY_B, MATCH, RECORD, COUNT, SHORTCIRCUIT, MESSAGE, PICKER, READBACK,
                   PICK_AT, NUMBER, CHAIN_PUSH, CHAIN_POP, GY_INDEX, GY_BANISH, ON_FIELD, FIELD_BANISH, ADD_HAND,
                   SHUFFLE, TURNLOG_QUERY, TURNLOG_POST):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

        # --- G: sent-to-GY chain node (ov3) -------------------------------------------------------------
        GATE_NODE = 0x021D1436
        GATE_NATIVE = bytes.fromhex("64388542")          # subs r0,#0x64 ; cmp r5,r0
        GATE_TAIL = bytes.fromhex("00d17de2")            # bne 0x021D143E ; b 0x021D193A  (kept)
        GY_STUB_STOCK = bytes.fromhex("e17814220123b1f787fba078e178a2890123a4f711fb16e0")   # dead 0x0E82 tail
        GATE_LIT, GATE_LIT_VAL = 0x021D15AC, 0x163F      # pool of `ldr r0,[pc,#0x1a8]` @0x021D1400
        NEKO = 0x15DB
        ACCEPT = 0x021D199E                              # movs r0,#1 ; b 0x021D19BE (str [sp,#0x14])
        GY_STUB, GY_STUB_LEN = 0x02221328, 18            # 0x0E82 dead block tail (24 B free)
        assert GATE_LIT_VAL - 0x64 == NEKO and NEKO + 0x2F == DONOR_CID
        MISS_FRONT, MISS_FRONT_RESERVE = 0x02237E38, 28  # Abyssal Designator block tail (zero, unclaimed)

        def _check(blob: bytes, base: int, what: str) -> bytes:
            assert len(blob) <= RESERVE[base], f"{what} {len(blob):#x} > reserve {RESERVE[base]:#x}"
            assert_thumb1_only(blob, base)
            return blob


        def gy_stub(base: int = GY_STUB) -> bytes:
            """BL'd from 0x021D1436 (r5 = cid, r0 = 0x163F); returns Z for Neko Mane King, BLs the accept for Eva."""
            b = EffectBuilder()
            b.insn("SUB", "R0, #0x64")
            b.insn("CMP", "R5, R0")
            b.insn("BEQ", "ret")
            b.insn("ADD", "R0, #0x2F")
            b.insn("CMP", "R5, R0")
            b.insn("BNE", "ret")
            b.insn("NOP")
            b.insn("NOP")
            b.label("ret")
            b.insn("BX", "LR")
            body = bytearray(b.assemble(base, pad="nop"))[:GY_STUB_LEN]                              # drop the assembler's 4-byte alignment pad
            assert body[-2:] == b"\x70\x47", body.hex()
            body[12:16] = tch._bl(base + 12, ACCEPT)
            blob = bytes(body)
            assert_thumb1_only(blob, base)
            return blob


        def miss_front(base: int = MISS_FRONT) -> bytes:
            """BL'd from 0x021EE10C (r3 = cid): Eva -> Z (never miss); else tail-jump to Shadow Mist's block A."""
            b = EffectBuilder()
            b.ldr_const(1, DONOR_CID)
            b.insn("CMP", "R3, R1")
            b.insn("BEQ", "ret")
            b.ldr_const(1, _sm.MISS_BLOCK_A | 1)
            b.insn("BX", "R1")
            b.label("ret")
            b.insn("BX", "LR")
            blob = b.assemble(base, pad="nop")
            assert len(blob) <= MISS_FRONT_RESERVE, len(blob)
            assert_thumb1_only(blob, base)
            return blob


        # --- ov5 stubs ----------------------------------------------------------------------------------
        def build_bpred(base: int) -> bytes:
            """GY builder filter (entry [sp] = &card word, [sp+4] = the activating card's ref): ref != ctx."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R0, R0, R1")
            b.insn("LDR", "R1, [SP, #0xC]")
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return _check(b.assemble(base, pad="nop"), base, "BPRED")


        def build_dpred(base: int) -> bytes:
            """Deck builder filter (entry [sp] = &card word, [sp+4] = excluded cid or 0): name != excl."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDR", "R1, [SP, #0xC]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "yes")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call_addr(SAME_NAME, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return _check(b.assemble(base, pad="nop"), base, "DPRED")


        def build_handler(base: int) -> bytes:
            """Criteria handler (r0 row, r1 side, r2 param), mode = param >> 16 (module doc F)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x10")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R4, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.insn("LSR", "R0, R6, #0x10")
            b.insn("CMP", "R0, #0x2")
            b.insn("BNE", "banish")
            b.insn("LDR", "R0, [R5, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", f"R0, #0x{DECK_FLAGS:X}")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.ldr_const(2, DPRED | 1)
            b.insn("LSL", "R3, R6, #0x12")
            b.insn("LSR", "R3, R3, #0x12")
            b.call_addr(DECK_B, via=R7)
            b.insn("B", "out")
            b.label("banish")
            b.ldr_const(0, BANISH_WORD)
            b.insn("STR", "R0, [SP, #0x0]")
            b.ldr_const(0, BANISH_FLAGS)
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.ldr_const(2, BPRED | 1)
            b.insn("LSL", "R3, R6, #0x10")
            b.insn("LSR", "R3, R3, #0x10")
            b.call_addr(GY_B, via=R7)
            b.ldr_const(7, FIELD)
            b.insn("MOV", "R0, #0x1")
            b.insn("AND", "R0, R4")
            b.insn("BEQ", "f0")
            b.ldr_const(0, PLAYER_STRIDE)
            b.insn("ADD", "R7, R7, R0")
            b.label("f0")
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
            b.call_addr(MATCH, R4, R6, R7, BANISH_WORD, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "fnx")
            b.call_addr(RECORD, R4, R6, 0, via=R3)
            b.label("fnx")
            b.insn("ADD", "R7, #0x14")
            b.insn("ADD", "R6, #0x1")
            b.insn("B", "flp")
            b.label("out")
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, "HANDLER")


        def _banish_param(b: EffectBuilder, reg: Reg, tmp: Reg) -> None:
            """reg = P_BANISH | desc[+0xC] (the activating card's ref)."""
            b.insn("LDRH", f"{reg!r}, [R4, #0xC]")
            b.ldr_const(int(tmp), P_BANISH)
            b.insn("ORR", f"{reg!r}, {tmp!r}")


        def build_cond(base: int) -> bytes:
            """+0C (desc, arg): desc[+7] passes; else OPT log clear, a banish candidate and a Deck target."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x7]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "yes")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", "R1, #0xB")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call("turnlog_query", R0, R1, R2, KIND, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x6]")
            b.insn("EOR", "R5, R0")
            _banish_param(b, R2, R3)
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, R0, R1, P_DECK, via=R3)
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
            """+14 (desc, arg), phase [STATE+0x7C] (module doc C2).  Frame: [sp] min / ptr, [sp+4] max / ref,
            [sp+8] banished count."""
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
            b.insn("BEQ", "ph1j")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "ph2j")
            b.insn("B", "ph3")
            b.label("ph1j")
            b.insn("B", "ph1")
            b.label("ph2j")
            b.insn("B", "ph2")
            b.label("ph0")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, KIND, via=R7)
            _banish_param(b, R2, R3)
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, via=R3)
            b.insn("CMP", "R0, #0x2")
            b.insn("BLT", "one")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, R0, R1, P_DECK, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "one")
            b.ldr_const(0, CAND)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.ldr_const(2, P_DECK)
            b.insn("ORR", "R2, R0")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "one")
            b.insn("MOV", "R0, #0x2")
            b.insn("STRH", "R0, [R4, #0x12]")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.insn("MOV", f"R2, #0x{NUM_TITLE:X}")
            b.call_addr(NUMBER, R0, R1, R2, NUM_ITEM, via=R7)
            b.insn("B", "nextj")
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x12]")
            b.label("nextj")
            b.insn("B", "next")
            b.label("ph1")
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("CMP", "R0, #0x1")
            b.insn("BLE", "p1msg")
            b.ldr_const(1, UI)
            b.insn("LDR", "R1, [R1, #0x34]")
            b.insn("CMP", "R1, #0x1")
            b.insn("BGE", "p1a")
            b.insn("MOV", "R1, #0x1")
            b.label("p1a")
            b.insn("CMP", "R1, R0")
            b.insn("BLE", "p1b")
            b.insn("ADD", "R1, R0, #0x0")
            b.label("p1b")
            b.insn("STRH", "R1, [R4, #0x12]")
            b.label("p1msg")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", f"R1, #0x{MSG_BANISH:X}")
            b.call_addr(MESSAGE, via=R3)
            b.insn("B", "next")
            b.label("ph2")
            b.insn("LDRH", "R1, [R4, #0x12]")
            b.insn("ADD", "R1, #0x6")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R2, [R4, #0x0]")
            _banish_param(b, R3, R7)
            b.call_addr(PICKER, via=R7)
            b.insn("B", "next")
            b.label("ph3")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x8]")
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
            b.insn("B", "counted")
            b.label("notgy")
            b.insn("LDR", "R0, [SP, #0x4]")
            b.call_addr(ON_FIELD, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "bnx")
            b.insn("LSL", "R1, R0, #0x10")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R0, R0, #0x18")
            b.insn("LSR", "R0, R0, #0x18")
            b.call_addr(FIELD_BANISH, R0, R1, 0, via=R3)
            b.label("counted")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x8]")
            b.label("bnx")
            b.insn("ADD", "R7, #0x1")
            b.insn("B", "blp")
            b.label("bend")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("STRH", "R0, [R4, #0x12]")
            b.call_addr(CHAIN_POP, via=R3)
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


        def _deck_param(b: EffectBuilder, reg: Reg) -> None:
            """reg = P_DECK | desc+0x14 (the first added cid, 0 before any).  Clobbers r0."""
            b.insn("LDRH", f"{reg!r}, [R4, #0x14]")
            b.ldr_const(0, P_DECK)
            b.insn("ORR", f"{reg!r}, R0")


        def build_res(base: int) -> bytes:
            """+04 (desc, ev), phase [STATE+0x70]: 0x80 open, excl = k = 0 | 0x7F k < N and a Deck target ->
            prompt | 0x7E pick 1 | 0x7D record the first name, k++, add it to the hand -> 0x7F | 0x64 shuffle,
            close.  desc: +0x12 N (from the cost), +0x14 first added cid, +0x1A k.  Frame: [sp] ev."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x8")
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
            b.insn("CMP", "R0, #0x64")
            b.insn("BEQ", "p64j")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("p64j")
            b.insn("B", "p64")
            b.label("p80")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDR", "R1, [SP, #0x0]")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.insn("STRH", "R0, [R4, #0x14]")
            b.insn("STRH", "R0, [R4, #0x1A]")
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("p7f")
            b.insn("LDRH", "R0, [R4, #0x1A]")
            b.insn("LDRH", "R1, [R4, #0x12]")
            b.insn("CMP", "R0, R1")
            b.insn("BGE", "to64")
            _deck_param(b, R7)
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(COUNT, R0, R1, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "to64")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", f"R1, #0x{MSG_ADD:X}")
            b.call_addr(MESSAGE, via=R3)
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("to64")
            b.insn("MOV", "R0, #0x64")
            b.insn("B", "ret")
            b.label("p7e")
            _deck_param(b, R7)
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
            b.insn("LDRH", "R1, [R4, #0x1A]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BNE", "cnt")
            b.insn("STRH", "R0, [R4, #0x14]")
            b.label("cnt")
            b.insn("ADD", "R1, #0x1")
            b.insn("STRH", "R1, [R4, #0x1A]")
            b.call_addr(ADD_HAND, R5, R7, via=R3)
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("p64")
            b.call_addr(SHUFFLE, R5, via=R3)
            b.call_addr(CHAIN_POP, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, "RES")


        STUBS = ((BPRED, build_bpred), (DPRED, build_dpred), (HANDLER, build_handler),
                 (COND, build_cond), (COST, build_cost), (RES, build_res))


        def _o(a: int) -> int:
            return a - RAM_BASE


        def _bl_target(ov, src: int) -> int:
            return _sm._bl_target(bytes(ov[_o(src):_o(src) + 4]), src)


        def _apply_gate(ov: bytearray) -> None:
            want = tch._bl(GATE_NODE, GY_STUB)
            blob = gy_stub()
            o = _o(GATE_NODE)
            if bytes(ov[o:o + 4]) == want and bytes(ov[_o(GY_STUB):_o(GY_STUB) + len(blob)]) == blob:
                return
            assert bytes(ov[o:o + 4]) == GATE_NATIVE, f"G node {GATE_NODE:#x} not stock -- another patch owns it"
            assert bytes(ov[o + 4:o + 8]) == GATE_TAIL, "G node tail drifted"
            assert struct.unpack_from("<I", ov, _o(GATE_LIT))[0] == GATE_LIT_VAL, "G pivot literal moved"
            assert bytes(ov[_o(GY_STUB):_o(GY_STUB) + 24]) == GY_STUB_STOCK, "G stub slot is not the stock dead tail"
            ov[_o(GY_STUB):_o(GY_STUB) + len(blob)] = blob
            ov[o:o + 4] = want
            print(f"G  sent-to-GY node {GATE_NODE:#x} -> BL {GY_STUB:#x}: 0x160A -> accept {ACCEPT:#x}, Neko kept")


        def _apply_miss(ov: bytearray) -> None:
            want = tch._bl(_sm.MISS_NODE, MISS_FRONT)
            blob = miss_front()
            o = _o(_sm.MISS_NODE)
            if bytes(ov[o:o + 4]) == want and bytes(ov[_o(MISS_FRONT):_o(MISS_FRONT) + len(blob)]) == blob:
                return
            assert bytes(ov[o:o + 4]) == tch._bl(_sm.MISS_NODE, _sm.MISS_BLOCK_A), \
                "J miss node is not Shadow Mist's BL to block A -- Shadow Mist must be applied first"
            assert bytes(ov[_o(MISS_FRONT):_o(MISS_FRONT) + MISS_FRONT_RESERVE]) == bytes(MISS_FRONT_RESERVE), \
                "J front-stub slot is not the zero-filled Abyssal Designator tail"
            ov[_o(MISS_FRONT):_o(MISS_FRONT) + len(blob)] = blob
            ov[o:o + 4] = want
            print(f"J  miss node {_sm.MISS_NODE:#x} -> BL {MISS_FRONT:#x} -> Shadow Mist block A; 0x160A never misses")

        def install(rom, view):
            _apply_gate(view.buf)
            _apply_miss(view.buf)

        def check_fn(c, rom, view):
            ov = bytes(view.buf)

            def check(cond, msg):
                c.ok(bool(cond), msg)

            from otn_enhanced.rom.overlay_io import load_overlay3
            check(_bl_target(ov, GATE_NODE) == GY_STUB and ov[_o(GATE_NODE) + 4:_o(GATE_NODE) + 8] == GATE_TAIL,
                  f"G node {GATE_NODE:#x} = BL {GY_STUB:#x}, native bne/b kept")
            check(ov[_o(GY_STUB):_o(GY_STUB) + GY_STUB_LEN] == gy_stub(), f"G ov3 stub @{GY_STUB:#x} installed")
            check(_snoww._switch_leaf(ov, DONOR_CID) == ACCEPT, f"G simulated chain: 0x160A reaches accept {ACCEPT:#x}")
            # vs STOCK (SRC is the chain ROM, which contains Eva once shipped): other chain donors may move too, but only
            # the ones their modules registered with snoww (Shadow Mist's whole-chain check, same rule).
            _, stock = load_overlay3("data/over_the_nexus/working/rom.nds")
            stock = bytes(stock)
            check(_snoww._switch_leaf(ov, NEKO) == _snoww._switch_leaf(stock, NEKO),
                  "G simulated chain: Neko Mane King 0x15DB reaches the same leaf as in stock")
            moved = [c for c in range(0x2700) if _snoww._switch_leaf(stock, c) != _snoww._switch_leaf(ov, c)]
            allowed = set(_snoww.EXTRA_SWITCH_DONORS) | {_snoww.DONOR_CID}
            check(DONOR_CID in moved and set(moved) <= allowed,
                  f"G whole-chain walk vs stock: 0x160A moved, nothing unregistered moved "
                  f"(unregistered: {[hex(c) for c in moved if c not in allowed]})")

            # A LATER front (infernoble Maugis) may sit ahead of ours: accept a node target whose literal
            # pool tail-jumps to MISS_FRONT.
            # (2026-10-22: the Infernoble Arms front in ov5 sits ahead of Maugis's -> walk the whole chain, ov5 included.)
            _t = _bl_target(ov, _sm.MISS_NODE)
            _ov5 = bytes(__import__("otn_enhanced.effects.ov5_cave", fromlist=["x"])._load_ov5_decompressed(rom).data)
            _fronted = _t != MISS_FRONT and _sm._miss_node_reaches_a(ov, _ov5, MISS_FRONT)
            check((_t == MISS_FRONT or _fronted)
                  and ov[_o(_sm.MISS_NODE) + 4:_o(_sm.MISS_NODE) + 8] == _sm.MISS_NODE_NATIVE[4:],
                  f"J miss node {_sm.MISS_NODE:#x} = BL {MISS_FRONT:#x}, caller's beq/b kept")
            check(ov[_o(MISS_FRONT):_o(MISS_FRONT) + len(miss_front())] == miss_front(),
                  f"J front stub @{MISS_FRONT:#x} installed (tail -> block A {_sm.MISS_BLOCK_A:#x})")


        return Compiled(
            tuple((base, build(base), "stub") for base, build in STUBS),
            rows=(Row(LEAVE_MASK, MASK_ROW, MASK_PHANTOM), Row(CLS2, CLS2_REC, CLS2_PHANTOM), Row(CRITERIA, CRIT_ROW, CRIT_PHANTOM)),
            installs=(install,), checks=(check_fn,))


eva_effect = sent_to_graveyard_banish_light_fairies_add_same_number_of_low_level_light_fairies_with_different_names

SPEC = card(0x160A, eva_effect())

PROPS = card_props("LIGHT", "Fairy", level=1, atk=500, defense=200)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_eva.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
