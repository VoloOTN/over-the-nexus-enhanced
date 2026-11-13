"""Wattkyuki (LIGHT / Thunder / Synchro Effect / Level 8 / 1600 / 1700) on St. Joan 0x1458.

    1 "Watt" Tuner + 1+ non-Tuner Thunder monsters
    This card can attack directly. When this card inflicts battle damage to your opponent by a direct attack: You can
    shuffle both 1 "Watt" Tuner from your GY and 1 face-up non-Tuner Thunder monster you control into the Deck, and if
    you do, Special Summon 1 "Watt" Synchro Monster from your Extra Deck, except "Wattkyuki". You can only use this
    effect of "Wattkyuki" once per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.cards.wattcobra import WATT_TABLE
from otn_enhanced.dsl import archetype_member, card, card_props, fusion_to_synchro_effect, CLS1, CRITERIA, Compiled, Row
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.effects.common import Table
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class direct_attack_battle_damage_shuffle_watt_tuner_and_thunder_special_summon_watt_synchro_from_extra_deck:
    """'This card can attack directly. When this card inflicts battle damage to your opponent by a direct attack: You can
    shuffle both 1 "Watt" Tuner from your GY and 1 face-up non-Tuner Thunder monster you control into the Deck, and if you
    do, Special Summon 1 "Watt" Synchro Monster from your Extra Deck, except this card. Once per turn.' Material routing
    (C0): two private 4-byte detours send the donor to the native Watt-Tuner / same-race leaves of Wattchimera's recipe
    (the shared gates are untouched). C1: direct-attack list over a phantom. C2: trigger = LIST A ("by a direct attack")
    + one cls1 row (Wattuna's shape) + ONE criteria row whose ov5 handler dispatches on the resolver's phase word (no ov5
    RAM cell: ov5 runtime state gets wiped), and a phase-machine resolver of its own (never wrap a native one). The
    Extra-Deck builder flags are Starlight Road's (8): Cyber-Stein's bit 2 drops every Synchro."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import summon_trigger_hook as sth
        from otn_enhanced.rom.overlay_io import RAM_BASE
        _off = lambda a: a - RAM_BASE
        DONOR_CID = cid

        # --- C0 ---------------------------------------------------------------------
        LIST_A, LIST_MIN3 = (0x02275AB8, 16), (0x02275AD8, 21)    # material-count exceptions
        NAMED_MAT = (0x02275B04, 23)                              # {synchro, named material} x 23
        WATTHYDRA = 0x2477
        OUTER_SITE, OUTER_NATIVE, OUTER_KEY = 0x02248660, bytes.fromhex("7f498d42"), 0x221A  # ldr r1,=0x221A ; cmp r5,r1
        OUTER_LEAF = 0x02248A40             # Watt Tuner leaf: adds r0,r4,#0 ; bl 0x02023EF4 ; pop
        THIRD_SITE, THIRD_NATIVE, THIRD_KEY = 0x02248AFA, bytes.fromhex("89488542"), 0x1E9A  # ldr r0,=0x1E9A ; cmp r5,r0
        THIRD_LEAF = 0x02248FD8             # race(material) == race(Synchro)
        LEAF_SIGS = ((OUTER_LEAF, bytes.fromhex("201cdbf5")), (THIRD_LEAF, bytes.fromhex("002f19d0")))

        # --- C1 ---------------------------------------------------------------------
        DA_LIST, DA_COUNT, DA_DROP = 0x0226D730, 25, 0x1133

        # --- Watt set code 0x58 (ARM9) ---------------------------------------------
        WATT_LIST, WATT_LIST_COUNT = 0x0209CBEA, 22
        WATT_LIST_LIT, WATT_COUNT_IMM = 0x02023EFC, 0x02023EF8
        WATT_DROP = 0x232A                  # Wattcannon -- displaced by user decision

        def _router(key: int, reg: int, leaf: int):
            """BL from a `ldr <reg>,=key ; cmp r5,<reg>` pair: 0x1458 -> leaf, else replay (flags survive bx)."""
            def build(base: int) -> bytes:
                b = EffectBuilder()
                b.ldr_const(reg, DONOR_CID)
                b.insn("CMP", f"R5, R{reg}")
                b.insn("BEQ", "wk")
                b.ldr_const(reg, key)
                b.insn("CMP", f"R5, R{reg}")
                b.insn("BX", "LR")
                b.label("wk")
                b.ldr_const(reg, leaf | 1)
                b.insn("BX", f"R{reg}")
                return b.assemble(base, pad="nop")
            return build

        # --- C2 ---------------------------------------------------------------------
        # Trigger: LIST A 0x0226EE7C ("inflicts battle damage BY A DIRECT ATTACK") + one cls1 row (Wattuna's
        # shape). Selections: ONE criteria row whose ov5 handler dispatches on the resolver's own phase word, so
        # no ov5 RAM cell is needed (Assault Synchron: ov5 runtime state gets wiped).
        LISTA, LISTA_COUNT, LISTA_DROP = 0x0226EE7C, 19, 0x1A1F
        CLS1_BASE, CLS1_COUNT, CLS_FMT = 0x022860D4, 0x535, "<HHIIIII"
        CRIT_BASE, CRIT_COUNT, CRIT_FMT = 0x022713C4, 0x56C, "<HHII"
        ROW_PHANTOM = 0x0E9B                # owns exactly one cls1 row and one criteria row; no card_prop; unclaimed
        ZONE_PRED, TAG_YOU_CAN, ALWAYS = 0x021E32D5, 0x021E51E5, 0x0224A115   # Wattuna's U4 row
        CLS1_ROW = (DONOR_CID, 0, ov5_cave.CAVE_WK_RES | 1, ZONE_PRED, ov5_cave.CAVE_WK_COND | 1,
                    TAG_YOU_CAN, ov5_cave.CAVE_WK_COST | 1)
        CRIT_ROW = (DONOR_CID, 0xFFFF, ov5_cave.CAVE_WK_HAND | 1, 0x00000002)
        KIND = 1                            # turn-log kind for "once per turn"

        STATE = 0x0229AAFC                  # +0x70 resolver phase, +0x74/+0x78 resolver scratch
        PICKBLK = 0x0229944C                # +6 candidate count
        MESSAGE, PICKER, PARAM = 0x0219A819, 0x0219C431, 0x02234E79
        PICK_WORD, PICK_ZONE = 0x0219C511, 0x0219C535
        COUNT = 0x02243FA9                  # (side, cid, param) -> candidates
        SS_COMMIT, MAY_SS, FREE_ZONE = 0x0226925D, 0x021B9ECD, 0x021AD871
        CHAIN_PUSH, CHAIN_POP = 0x021D28A5, 0x021D2965
        GY_TO_DECK, FIELD_TO_DECK, SHUFFLE_RECEIVED = 0x021C6A0D, 0x021CF591, 0x021D26CD
        ZONE_CID, IS_TUNER_AT, LIVE_RACE = 0x021A36ED, 0x021A1C7D, 0x021B8E31
        FACEUP_BASE = 0x0229ACD0
        RECORD = 0x02243B2D
        GY_BUILDER, ED_BUILDER, SETCODE_PRED = 0x0223C4E9, 0x0223BE41, 0x0223C825
        HAS_SET, CARD_TYPE_HALF, RACE_GETTER = 0x020240D9, 0x0202ABF9, 0x0202ABB9
        TURNLOG_QUERY, TURNLOG_POST, COST_SETTLED = 0x021A14E9, 0x021D2585, 0x021D2BC9
        WATT = 0x58
        # Extra-Deck builder flags = Starlight Road's 0x022423D8 (a Synchro from the Extra Deck by effect).
        # Cyber-Stein's 0xA carries bit 2, which drops every Synchro (measured: 0 vs 2 candidates on
        # rom_wattuna_cobra.ml3 with Wattchimera + Watthydra in the Extra Deck -- scratch/wattkyuki_pool_probe.py).
        ED_FLAGS = 8
        for _v in (MESSAGE, PICKER, PARAM, PICK_WORD, PICK_ZONE, COUNT, SS_COMMIT, MAY_SS, FREE_ZONE,
                   CHAIN_PUSH, CHAIN_POP, GY_TO_DECK, FIELD_TO_DECK, SHUFFLE_RECEIVED, ZONE_CID,
                   IS_TUNER_AT, LIVE_RACE, RECORD, GY_BUILDER, ED_BUILDER, SETCODE_PRED, HAS_SET,
                   CARD_TYPE_HALF, RACE_GETTER, TURNLOG_QUERY, TURNLOG_POST, COST_SETTLED, ALWAYS):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

        HAND = ov5_cave.CAVE_WK_HAND
        SUB_GY, SUB_ED, SUB_FIELD = HAND + 0x40, HAND + 0x80, HAND + 0xC0

        def build_hand(base: int) -> bytes:
            """Criteria handler (row, side) + three sub-handlers (side) -> candidate count."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R1, #0x0")
            b.ldr_const(0, STATE)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x7B")
            b.insn("BEQ", "fld")
            b.insn("CMP", "R0, #0x7A")
            b.insn("BEQ", "fld")
            b.insn("CMP", "R0, #0x79")
            b.insn("BEQ", "ed")
            b.insn("CMP", "R0, #0x78")
            b.insn("BEQ", "ed")
            b.insn("CMP", "R0, #0x77")
            b.insn("BEQ", "ed")
            b.ldr_const(3, SUB_GY | 1)
            b.insn("B", "go")
            b.label("fld")
            b.ldr_const(3, SUB_FIELD | 1)
            b.insn("B", "go")
            b.label("ed")
            b.ldr_const(3, SUB_ED | 1)
            b.label("go")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("BLX", "R3")
            b.insn("POP", "{R4, PC}")
            main = b.assemble(base, pad="nop")
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("MOV", f"R1, #0x{WATT:X}")
            b.insn("STR", "R1, [SP, #0x8]")
            b.ldr_const(1, 0x8002)
            b.insn("STR", "R1, [SP, #0x0]")
            b.insn("MOV", "R1, #0x0")
            b.insn("STR", "R1, [SP, #0x4]")
            b.ldr_const(1, DONOR_CID)
            b.ldr_const(2, SETCODE_PRED)
            b.insn("ADD", "R3, SP, #0x8")
            b.call_addr(GY_BUILDER, via=R4)
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, PC}")
            gy = b.assemble(SUB_GY, pad="nop")
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call("get_race", DONOR_CID, via=R3)
            b.insn("ADD", "R7, R0, #0x0")
            b.insn("MOV", "R5, #0x0")
            b.label("loop")
            b.call_addr(ZONE_CID, R4, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "next")
            b.ldr_const(0, FACEUP_BASE)
            b.insn("LSL", "R1, R4, #0x1F")
            b.insn("BEQ", "p0")
            b.ldr_const(1, 0xB3C)
            b.insn("ADD", "R0, R0, R1")
            b.label("p0")
            b.insn("LSL", "R1, R5, #0x4")
            b.insn("ADD", "R0, R0, R1")
            b.insn("LSL", "R1, R5, #0x2")
            b.insn("ADD", "R0, R0, R1")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "next")
            b.call_addr(IS_TUNER_AT, R4, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "next")
            b.call_addr(LIVE_RACE, R4, R5, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "next")
            b.call_addr(RECORD, R4, R5, 0, via=R3)
            b.label("next")
            b.insn("ADD", "R5, #0x1")
            b.insn("CMP", "R5, #0x5")
            b.insn("BLT", "loop")
            b.ldr_const(0, PICKBLK)
            b.insn("LDRH", "R0, [R0, #0x6]")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("ASR", "R0, R0, #0x10")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            fld = b.assemble(SUB_FIELD, pad="nop")
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("MOV", "R1, #0x2")
            b.insn("STR", "R1, [SP, #0x0]")
            b.insn("MOV", f"R1, #0x{ED_FLAGS:X}")
            b.insn("STR", "R1, [SP, #0x4]")
            b.call_addr(ED_BUILDER, R0, DONOR_CID, ov5_cave.CAVE_WK_EDPRED | 1, 0, via=R4)
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{R4, PC}")
            ed = b.assemble(SUB_ED, pad="nop")
            assert len(main) <= 0x40 and len(gy) <= 0x40 and len(ed) <= 0x40, (len(main), len(gy), len(ed))
            assert len(fld) <= 0xA0, f"field sub-handler {len(fld)} B > 0xA0"
            return main.ljust(0x40, b"\0") + gy.ljust(0x40, b"\0") + ed.ljust(0x40, b"\0") + fld


        def build_edpred(base: int) -> bytes:
            """Extra-Deck builder predicate ([sp] = &card word): Watt Synchro, not Wattkyuki."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R4, R0, #0x12")
            b.ldr_const(1, DONOR_CID)
            b.insn("CMP", "R4, R1")
            b.insn("BEQ", "no")
            b.call_addr(HAS_SET, R4, WATT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(CARD_TYPE_HALF, R4, via=R3)
            b.insn("CMP", "R0, #0x11")
            b.insn("BLT", "no")
            b.insn("CMP", "R0, #0x13")
            b.insn("BGT", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def _call(b: EffectBuilder, addr: int) -> None:
            """ldr r3,=addr ; blx r3 (addr already carries its Thumb bit)."""
            b.ldr_const(3, addr)
            b.insn("BLX", "R3")


        def _pool(b: EffectBuilder, sub: int) -> None:
            """Zero the pick count, run the sub-handler on r6, branch to `no` if no candidate."""
            b.ldr_const(0, PICKBLK)
            b.insn("MOV", "R1, #0x0")
            b.insn("STRH", "R1, [R0, #0x6]")
            b.insn("ADD", "R0, R6, #0x0")
            _call(b, sub | 1)
            _count_read(b)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")


        def _count_read(b: EffectBuilder) -> None:
            b.ldr_const(0, PICKBLK)
            b.insn("LDRH", "R0, [R0, #0x6]")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("ASR", "R0, R0, #0x10")


        def build_cond(base: int) -> bytes:
            """cls1 +0C (desc, r1): turn log -> 0; any pool empty -> 0; else the native 'activatable'."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", "R1, #0xB")
            b.ldr_const(2, DONOR_CID)
            b.insn("MOV", f"R3, #0x{KIND:X}")
            b.ldr_const(6, TURNLOG_QUERY)
            b.insn("BLX", "R6")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            b.insn("LDRB", "R6, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x6]")
            b.insn("EOR", "R6, R0")
            _pool(b, SUB_GY)
            _pool(b, SUB_FIELD)
            _pool(b, SUB_ED)
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            _call(b, ALWAYS)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        def _go(b: EffectBuilder, ph: int, lbl: str) -> None:
            b.insn("CMP", f"R4, #0x{ph:X}")
            b.insn("BNE", f"n{ph:x}")
            b.insn("B", lbl)
            b.label(f"n{ph:x}")


        def _msg_then(b: EffectBuilder, nxt: int) -> None:
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("MOV", "R1, #0x30")
            _call(b, MESSAGE)
            b.insn("MOV", f"R0, #0x{nxt:X}")
            b.insn("B", "ret")


        def _picker(b: EffectBuilder, nxt: int) -> None:
            b.insn("ADD", "R0, R5, #0x0")
            _call(b, PARAM)
            b.insn("ADD", "R3, R0, #0x0")
            b.insn("LDRH", "R2, [R5, #0x0]")
            b.insn("MOV", "R1, #0x6")
            b.insn("ADD", "R0, R6, #0x0")
            b.ldr_const(7, PICKER)
            b.insn("BLX", "R7")
            b.insn("MOV", f"R0, #0x{nxt:X}")
            b.insn("B", "ret")


        def _count(b: EffectBuilder) -> None:
            """r0 = COUNT(side, cid, param) for the CURRENT phase's pool."""
            b.insn("ADD", "R0, R5, #0x0")
            _call(b, PARAM)
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.insn("ADD", "R0, R6, #0x0")
            _call(b, COUNT)


        def build_res(base: int) -> bytes:
            """cls1 +04 (desc) -> next phase, 0 = stop. Own machine (NAST: never wrap a native resolver).

              0x80  GY Watt Tuner AND own face-up non-Tuner Thunder exist, else stop; msg 0x30
              0x7F  picker (handler -> GY)                           0x7E  CHAIN_PUSH
              0x7D  0x021C6A0C(desc, side, ref(pick), 1) -> [+0x74]  0x7C  CHAIN_POP; moved? msg 0x30 : stop
              0x7B  picker (handler -> FIELD)                        0x7A  slot -> [+0x78]; 0x021CF590 (queued)
              0x79  0x021D26CC shuffle; slot empty? may-SS, free zone, Extra pool > 0 : stop; msg 0x30
              0x78  picker (handler -> EXTRA)                        0x77  0x0226925C(side, pick, 1, 2), [sp]=cid<<16
              0x76  stop
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R6, [R5, #0x2]")
            b.insn("LDRB", "R0, [R5, #0x6]")
            b.insn("EOR", "R6, R0")
            b.ldr_const(7, STATE)
            b.insn("LDR", "R4, [R7, #0x70]")
            for ph in (0x80, 0x7F, 0x7E, 0x7D, 0x7C, 0x7B, 0x7A, 0x79, 0x78, 0x77):
                _go(b, ph, f"p{ph:x}")
            b.label("stop")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            b.label("p80")
            b.ldr_const(0, PICKBLK)
            b.insn("MOV", "R1, #0x0")
            b.insn("STRH", "R1, [R0, #0x6]")
            b.insn("ADD", "R0, R6, #0x0")
            _call(b, SUB_FIELD | 1)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "stop")
            _count(b)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "stop")
            _msg_then(b, 0x7F)
            b.label("p7f")
            _picker(b, 0x7E)
            b.label("p7e")
            _call(b, CHAIN_PUSH)
            b.insn("MOV", "R0, #0x7D")
            b.insn("B", "ret")
            b.label("p7d")
            _call(b, PICK_WORD)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R0, #0x1")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R1, R1, #0x1")
            b.insn("LSL", "R2, R0, #0x11")
            b.insn("LSR", "R2, R2, #0x1F")
            b.insn("ADD", "R2, R1, R2")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.insn("MOV", "R3, #0x1")
            b.ldr_const(4, GY_TO_DECK)
            b.insn("BLX", "R4")
            b.ldr_const(7, STATE)
            b.insn("STR", "R0, [R7, #0x74]")
            b.insn("MOV", "R0, #0x7C")
            b.insn("B", "ret")
            b.label("p7c")
            _call(b, CHAIN_POP)
            b.insn("LDR", "R0, [R7, #0x74]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop")
            _msg_then(b, 0x7B)
            b.label("p7b")
            _picker(b, 0x7A)
            b.label("p7a")
            _call(b, PICK_ZONE)
            b.ldr_const(7, STATE)
            b.insn("STR", "R0, [R7, #0x78]")
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.insn("ADD", "R0, R5, #0x0")
            _call(b, FIELD_TO_DECK)
            b.insn("MOV", "R0, #0x79")
            b.insn("B", "ret")
            b.label("p79")
            _call(b, SHUFFLE_RECEIVED)
            b.ldr_const(7, STATE)
            b.insn("LDR", "R1, [R7, #0x78]")
            b.insn("ADD", "R0, R6, #0x0")
            _call(b, ZONE_CID)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "stop")
            b.insn("ADD", "R0, R6, #0x0")
            _call(b, MAY_SS)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop")
            b.insn("ADD", "R0, R6, #0x0")
            _call(b, FREE_ZONE)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop")
            _count(b)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "stop")
            _msg_then(b, 0x78)
            b.label("p78")
            _picker(b, 0x77)
            b.label("p77")
            _call(b, PICK_WORD)
            b.insn("ADD", "R1, R0, #0x0")
            b.insn("LDRH", "R0, [R5, #0x0]")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("MOV", "R2, #0x1")
            b.insn("MOV", "R3, #0x2")
            b.ldr_const(7, SS_COMMIT)
            b.insn("BLX", "R7")
            b.insn("MOV", "R0, #0x76")
            b.insn("B", "ret")
            return b.assemble(base, pad="nop")


        def build_cost(base: int) -> bytes:
            """cls1 +14 (desc): settled -> 1; else stamp turn-log KIND, return 1 (wattuna.opt_cost_stub)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(COST_SETTLED, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "done")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, KIND, via=R4)
            b.label("done")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        CAVES = ((ov5_cave.CAVE_WK_OUTER, _router(OUTER_KEY, 1, OUTER_LEAF), 0x20),
                 (ov5_cave.CAVE_WK_THIRD, _router(THIRD_KEY, 0, THIRD_LEAF), 0x20),
                 (ov5_cave.CAVE_WK_RES, build_res, 0x200),
                 (ov5_cave.CAVE_WK_HAND, build_hand, 0x160),
                 (ov5_cave.CAVE_WK_EDPRED, build_edpred, 0x40),
                 (ov5_cave.CAVE_WK_COND, build_cond, 0xA0),
                 (ov5_cave.CAVE_WK_COST, build_cost, 0x30))
        HOOKS = ((OUTER_SITE, OUTER_NATIVE, ov5_cave.CAVE_WK_OUTER, "C0 Tuner: OUTER switch entry"),
                 (THIRD_SITE, THIRD_NATIVE, ov5_cave.CAVE_WK_THIRD, "C0 non-Tuner: THIRD tree pair"))

        def _u16s(ov, base, n):
            return struct.unpack_from(f"<{n}H", ov, _off(base))


        def check_material_preconditions(ov) -> None:
            for base, n in (LIST_A, LIST_MIN3):
                assert DONOR_CID not in _u16s(ov, base, n), f"0x{DONOR_CID:04X} joined count list {base:#x}"
            assert DONOR_CID not in _u16s(ov, NAMED_MAT[0], NAMED_MAT[1] * 2)[0::2], \
                "donor has a named-material row -- OUTER would never reach the cid switch"
            for leaf, sig in LEAF_SIGS:
                assert bytes(ov[_off(leaf):_off(leaf) + 4]) == sig, f"leaf {leaf:#x} drifted"

        stubs = tuple((base, build(base), "stub") for base, build, _r in CAVES)
        for base, blob, _w in stubs:
            assert_thumb1_only(blob, base)
        for (base, build, reserve), (_a, blob, _w) in zip(CAVES, stubs):
            assert len(blob) <= reserve, f"{base:#x}: {len(blob)} B > reserve {reserve:#x}"

        def install(rom, view):
            ov = view.buf
            check_material_preconditions(ov)
            for site, native, cave, label in HOOKS:
                want = sth._bl(site, cave)
                cur = bytes(ov[_off(site):_off(site) + 4])
                if cur != want:
                    assert cur == native, f"{label} @{site:#x} is {cur.hex()} -- another patch owns it"
                    ov[_off(site):_off(site) + 4] = want
            assert DONOR_CID not in _u16s(ov, 0x0226EEA4, 51), "donor is in LIST B (ungated) -- must not be"

        def check(c, rom, view):
            ov = view.buf
            try:
                check_material_preconditions(ov)
                c.ok(True, "C0 donor absent from count lists / named table; both native leaves intact")
            except AssertionError as e:
                c.ok(False, f"C0 preconditions: {e}")
            for site, _native, cave, label in HOOKS:
                c.eq(bytes(ov[_off(site):_off(site) + 4]), sth._bl(site, cave), f"{label} @{site:#x} -> {cave:#x}")
            c.ok(DONOR_CID not in _u16s(ov, 0x0226EEA4, 51), "C2 donor NOT in LIST B")

        return Compiled(
            stubs,
            rows=(Row(Table(DA_LIST, DA_COUNT, 2, "<H", label="direct-attack list"), (cid,), DA_DROP),
                  Row(Table(LISTA, LISTA_COUNT, 2, "<H", label="LIST A (direct-attack damage)"), (cid,), LISTA_DROP),
                  Row(CLS1, CLS1_ROW, ROW_PHANTOM), Row(CRITERIA, CRIT_ROW, ROW_PHANTOM)),
            installs=(install,), checks=(check,))


watt_synchro_effects = direct_attack_battle_damage_shuffle_watt_tuner_and_thunder_special_summon_watt_synchro_from_extra_deck

SPEC = card(
    0x1458,
    fusion_to_synchro_effect(row=58, stock=(0x1457, 0x1459)),
    watt_synchro_effects(),
    archetype_member(WATT_TABLE, phantom=0x232A))        # Wattcannon, displaced by user decision

PROPS = card_props("LIGHT", "Thunder", level=8, atk=1600, defense=1700, card_type="Synchro Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_wattkyuki.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
