"""Miscellaneousaurus (FIRE / Dinosaur / Level 4 / 1800 / 1000) on Krokodilus 0x0FF2.

    During either player's Main Phase: You can send this card from your hand to the Graveyard; during this Main
    Phase, Dinosaur-Type monsters you control are unaffected by your opponent's activated effects. You can banish any
    number of Dinosaur-Type monsters from your Graveyard, including this card; Special Summon 1 Dinosaur-Type monster
    from your Deck with a Level equal to the total number of monsters banished to activate this effect, but destroy it
    during the End Phase. You can only use this effect of "Miscellaneousaurus" once per turn.
"""
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, RES_RESERVE
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
class hand_discard_dinosaurs_unaffected_and_graveyard_banish_dinosaurs_summon_deck_dinosaur_destroyed_at_end_phase:
    """C1 'During either player's Main Phase: send this card from your hand to the GY; Dinosaurs you control are
    unaffected by your opponent's activated effects' (accepted simplification: all card effects, until end of turn, via
    Azure-Eyes' private protection key 0x1E9C) and C2 'banish any number of Dinosaurs from your GY, including this card;
    Special Summon 1 Dinosaur from your Deck with a Level equal to the number banished, destroy it during the End Phase,
    once per turn'. ONE cls2 record serves both (find_event_handler is leftmost-only): every stub splits on desc[+3]
    (0x0E = GY action, 0x0B = hand). Wiring: GY-action registry phantom row converted, cls2 + criteria (Deck/GY pair) +
    list A over phantom pairs, End-Phase destroy list + registry row 254, ARM9 hand list B + speed-2 list, the speed
    lookup's default leaf hooked (GY path stays speed 1), Azure-Eyes' protection link installed if absent. The cost
    never mutates the GY before the picker (glitched picker, in-game 2026-09-22). Four ov5 stubs."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.cards import azure_eyes as az
        from otn_enhanced.effects.common import ARM9_BASE
        from otn_enhanced.rom.overlay_io import RAM_BASE
        _off = lambda a: a - RAM_BASE
        DONOR_CID = cid
        # --- tables ------------------------------------------------------------------------
        GYREG_BASE, GYREG_COUNT = 0x0228DDF8, 60
        GYREG_PHANTOM_ROW = (0x144C, 0x0E, 0x0224C55D, 0x0224C669)
        GYREG_ROW = (DONOR_CID, 0x0E, 0x0224C591, 0x0224C6C1)
        CLS2_BASE, CLS2_COUNT, CLS_FMT = 0x02275C04, 0x2B9, "<HHIIIII"
        CRIT_BASE, CRIT_COUNT, CRIT_FMT = 0x022713C4, 0x56C, "<HHII"
        LISTA_BASE, LISTA_COUNT = 0x0227134C, 59
        EPLIST_BASE, EPLIST_COUNT = 0x0228F708, 0x24
        EPREG_ROW = 0x0228E1E0 + 254 * 8
        EPREG_BEFORE, EPREG_AFTER = (0x02254ED1, 0x0E43), (0x02254E95, DONOR_CID)
        PH_CLS2, PH_CRIT, PH_EPLIST = 0x0EBF, 0x0EA8, 0x0E2E

        DECK_HANDLER, GY_HANDLER, DINO_WORD = 0x0223CA99, 0x0223CA11, 0x48000002
        CRIT_ROWS = ((DONOR_CID, 0xFFFF, DECK_HANDLER, DINO_WORD),     # rel0: the Special Summon
                     (DONOR_CID, 0xFFFF, GY_HANDLER, DINO_WORD))       # rel1: the banish cost

        # --- natives -----------------------------------------------------------------------
        TURNLOG_QUERY, TURNLOG_POST = 0x021A14E9, 0x021D2585   # (side,0x0B,cid,1) / (side,cid,1,0)
        SS_GATES = (0x021AD871, 0x021B9ECD, 0x021B9ED9)       # (side) -> 0 = cannot Special Summon
        CANDIDATES = 0x02243FA9         # (side, cid, param) -> candidate count
        ROW_INDEX = 0x02243B9D          # (cid, param) -> criteria row index (<0 = none)
        SHORTCIRCUIT = 0x021D2BC9       # (desc) -> nonzero: cost already settled (0x021E5322)
        SELF_BANISH = 0x021E5709        # (desc) banish this card from the GY (Necro Gardna's cost)
        MESSAGE = 0x0219A819            # (side, code)
        PICKER = 0x0219C431             # (side, count code, cid, param)
        PICK_AT = 0x0219C94D            # (i+1) -> &card word of pick i
        BANISH = 0x021C7105             # (side, &card word, 0) GY -> banished
        CHAIN_PUSH, CHAIN_POP = 0x021D28A5, 0x021D2965
        PICK_READBACK = 0x0219C511      # () -> &locator of the picked Deck card
        SS_COMMIT = 0x0226925D          # (side, &loc, 1, 2, [sp] = source cid << 16)
        NO_CANDIDATE_CLEANUP = 0x0225BF31
        TEARDOWN = 0x021D269D
        STATE = 0x0229AAFC              # +0x70 resolver phase, +0x7C cost phase
        PICKS = 0x0229DD94              # +0x34 = how many the player picked (0x021E5318's literals @0x021E55E8 /
                                        #   0x021E56E4). NOT STATE+0x34: build 2 read that, got 0, ignored every pick.
        ANY_NUMBER = 0x47               # KB dispatch.multiselect_count_code_ranges
        BANISH_PROMPT = 0x56            # 0x021E5318's own prompt

        # --- C1 ----------------------------------------------------------------------------
        ZONE_GY, ZONE_HAND = 0x0E, 0x0B
        DUEL_STATE = 0x0229DD14         # +0x48 phase: 2 = Main Phase 1, 4 = Main Phase 2
        HAND_COST = 0x021E8FB9          # (desc) send THIS card from hand to GY (Effect Veiler / Honest)
        ZONE_CID = 0x021A36ED           # (side, slot) -> cid, 0 if empty
        FACEUP_BASE = 0x0229ACD0        # u16 != 0 = face-up (0x021AC9FC); + (side&1)*0xB3C + slot*0x14
        RACE_GETTER = 0x0202ABB9        # (cid) -> race   [ARM9]
        RACE_DINOSAUR = 9
        ATTACH_NODE = 0x021C479D        # (side, slot, key, kind byte, [sp] = param)
        PROT_KEY = 0x1E9C               # azure_eyes.PROT_KEY -- read by its link 0x021B0592
        PROT_KIND_BYTE = 0x02           # kind 2 (family 1), duration 0 = until the end of THIS turn
        LISTB_BASE, LISTB_COUNT, PH_LISTB = 0x0209BC8C, 36, 0x0E63      # ARM9 hand quick-effect list
        QE_BASE, QE_COUNT, PH_QE = 0x0209C118, 0x76, 0x1534             # ARM9 spell-speed-2 list
        SPEED_SITE = 0x021A894C         # `adds r0,r2,#0 ; bl 0x0202345C` then 0x021A8952 pop {r4,pc}
        SPEED_ARM9 = 0x0202345D

        COND_ADDR, COND_RESERVE = ov5_cave.CAVE_MISC_COND, 0xD0
        COST_ADDR, COST_RESERVE = ov5_cave.CAVE_MISC_COST, 0x110
        RES_ADDR, RES_RESERVE = ov5_cave.CAVE_MISC_RES, 0x1B0
        SPEED_ADDR, SPEED_RESERVE = ov5_cave.CAVE_MISC_SPEED, 0x20

        CLS2_RECORD = (DONOR_CID, 0, RES_ADDR | 1, 0, COND_ADDR | 1, COST_ADDR | 1, 0)
        SPEED_NATIVE = struct.pack("<H", 0x1C10) + az._bl(SPEED_SITE + 2, SPEED_ARM9 & ~1)
        SPEED_HOOKED = az._bl(SPEED_SITE, SPEED_ADDR) + struct.pack("<H", 0x46C0)

        def _row0_ptr(b: EffectBuilder) -> None:
            """r7 <- &criteria row 0 (row index in r0; clobbers r0/r1). Row stride 12 = (i<<3)+(i<<2)."""
            b.insn("LSL", "R1, R0, #0x3")
            b.insn("LSL", "R0, R0, #0x2")
            b.insn("ADD", "R0, R0, R1")
            b.ldr_const(1, CRIT_BASE)
            b.insn("ADD", "R7, R0, R1")


        def _ss_gates(b: EffectBuilder) -> None:
            """Each Special Summon gate (side in r5) -> 0 = cannot: branch to `no`. Clobbers r0/r7."""
            for g in SS_GATES:
                b.insn("ADD", "R0, R5, #0x0")
                b.call_addr(g, R0, via=R7)
                b.insn("CMP", "R0, #0x0")
                b.insn("BEQ", "no")


        def _build_cond(base: int) -> bytes:
            """+0C (desc, arg) -> 2 activatable / 0 not. C1 (hand): Main Phase 1/2, either turn.
            C2 (GY): skipped on the post-cost re-check (desc[+7])."""
            b = EffectBuilder()
            b.insn("LDRB", "R2, [R0, #0x3]")
            b.insn("CMP", f"R2, #0x{ZONE_GY:X}")
            b.insn("BEQ", "c2")
            b.insn("CMP", f"R2, #0x{ZONE_HAND:X}")
            b.insn("BNE", "c1no")
            b.ldr_const(1, DUEL_STATE)
            b.insn("LDR", "R1, [R1, #0x48]")
            b.insn("CMP", "R1, #0x2")
            b.insn("BEQ", "c1ok")
            b.insn("CMP", "R1, #0x4")
            b.insn("BEQ", "c1ok")
            b.label("c1no")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            b.label("c1ok")
            b.insn("MOV", "R0, #0x2")
            b.insn("BX", "LR")
            b.label("c2")
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x7]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "yes")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x6]")
            b.insn("EOR", "R5, R0")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R1, #0xB")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call("turnlog_query", R0, R1, R2, 1, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            _ss_gates(b)
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(CANDIDATES, R0, R1, 1, via=R7)
            b.insn("ADD", "R6, R0, #0x0")
            b.insn("CMP", "R6, #0xF")
            b.insn("BLE", "kok")
            b.insn("MOV", "R6, #0xF")
            b.label("kok")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.call_addr(ROW_INDEX, R0, 0, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "no")
            _row0_ptr(b)
            b.label("loop")
            b.insn("CMP", "R6, #0x0")
            b.insn("BLE", "miss")
            b.insn("LSL", "R0, R6, #0x2")
            b.insn("STRB", "R0, [R7, #0xA]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(CANDIDATES, R0, R1, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "hit")
            b.insn("SUB", "R6, #0x1")
            b.insn("B", "loop")
            b.label("hit")
            b.insn("MOV", "R0, #0x0")
            b.insn("STRB", "R0, [R7, #0xA]")
            b.label("yes")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("miss")
            b.insn("MOV", "R0, #0x0")
            b.insn("STRB", "R0, [R7, #0xA]")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, COND_RESERVE, "cond")


        def _build_cost(base: int) -> bytes:
            """+10 (desc, arg): the phase machine of 0x021E5318, native order -- pick over ALL GY
            Dinosaurs (this card included), banish the picks, then this card if it was not picked.

            ⚠️ Never mutate the GY before the picker: the first build banished this card in phase 0
            and the picker came up glitched with the banished card still a candidate (savestate
            rom_miscellaneousaurus.ml3, in-game 2026-09-22).
            ponytail: "was this card picked" = a pick with our cid; with two copies in the GY a pick of
            the OTHER copy counts, so N stays right but this copy is not banished."""
            b = EffectBuilder()
            b.insn("LDRB", "R2, [R0, #0x3]")
            b.insn("CMP", f"R2, #0x{ZONE_GY:X}")
            b.insn("BEQ", "c2")
            b.ldr_const(3, HAND_COST)
            b.insn("BX", "R3")
            b.label("c2")
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(SHORTCIRCUIT, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "done")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.ldr_const(6, STATE)
            b.insn("LDR", "R0, [R6, #0x7C]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ph0")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "ph1")
            b.ldr_const(6, PICKS)
            b.insn("LDR", "R0, [R6, #0x34]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x14]")
            b.insn("MOV", "R7, #0x0")
            b.label("scan")
            b.insn("LDR", "R0, [R6, #0x34]")
            b.insn("CMP", "R7, R0")
            b.insn("BGE", "scandone")
            b.insn("ADD", "R0, R7, #0x1")
            b.call_addr(PICK_AT, via=R3)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "scnext")
            b.insn("LDR", "R0, [R6, #0x34]")
            b.insn("STRH", "R0, [R4, #0x14]")
            b.label("scnext")
            b.insn("ADD", "R7, #0x1")
            b.insn("B", "scan")
            b.label("scandone")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("MOV", "R7, #0x0")
            b.label("lp")
            b.insn("LDR", "R0, [R6, #0x34]")
            b.insn("CMP", "R7, R0")
            b.insn("BGE", "lpdone")
            b.insn("ADD", "R0, R7, #0x1")
            b.call_addr(PICK_AT, via=R3)
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(BANISH, R5, R1, 0, via=R3)
            b.insn("ADD", "R7, #0x1")
            b.insn("B", "lp")
            b.label("lpdone")
            b.insn("LDRH", "R0, [R4, #0x14]")
            b.insn("LDR", "R1, [R6, #0x34]")
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "popit")
            b.call_addr(SELF_BANISH, R4, via=R3)
            b.label("popit")
            b.call_addr(CHAIN_POP, via=R3)
            b.insn("B", "stamp")
            b.label("ph0")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(CANDIDATES, R0, R1, 1, via=R7)
            b.insn("CMP", "R0, #0x1")
            b.insn("BGT", "ask")
            b.call_addr(SELF_BANISH, R4, via=R7)
            b.insn("MOV", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x14]")
            b.insn("B", "stamp")
            b.label("ask")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", f"R1, #0x{BANISH_PROMPT:X}")
            b.call_addr(MESSAGE, via=R7)
            b.insn("B", "next")
            b.label("ph1")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", f"R1, #0x{ANY_NUMBER:X}")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call_addr(PICKER, R0, R1, R2, 1, via=R7)
            b.label("next")
            b.insn("LDR", "R0, [R6, #0x7C]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("stamp")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, 1, via=R7)
            b.label("done")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, COST_RESERVE, "cost")


        def _build_res(base: int) -> bytes:
            """+04 (desc, event) -> next phase. ninjitsu_art_super_transformation PART F3 minus
            its target verb and its phase-1 link; teardown returns the chassis's 0x64."""
            b = EffectBuilder()
            b.insn("LDRB", "R2, [R0, #0x3]")
            b.insn("CMP", f"R2, #0x{ZONE_GY:X}")
            b.insn("BEQ", "c2")
            b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
            b.ldr_const(1, STATE)
            b.insn("LDR", "R1, [R1, #0x70]")
            b.insn("CMP", "R1, #0x80")
            b.insn("BNE", "c1out")
            b.insn("LDRB", "R6, [R0, #0x2]")
            b.insn("LDRB", "R1, [R0, #0x6]")
            b.insn("EOR", "R6, R1")
            b.insn("MOV", "R5, #0x0")
            b.label("c1lp")
            b.call_addr(ZONE_CID, R6, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "c1nx")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(2, FACEUP_BASE)
            b.insn("ADD", "R1, R6, #0x0")
            b.insn("MOV", "R3, #0x1")
            b.insn("AND", "R1, R3")
            b.insn("BEQ", "c1s0")
            b.ldr_const(3, 0x00000B3C)
            b.insn("ADD", "R2, R2, R3")
            b.label("c1s0")
            b.insn("LSL", "R1, R5, #0x4")
            b.insn("ADD", "R2, R2, R1")
            b.insn("LSL", "R1, R5, #0x2")
            b.insn("ADD", "R2, R2, R1")
            b.insn("LDRH", "R1, [R2, #0x0]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "c1nx")
            b.call("get_race", R4, via=R3)
            b.insn("CMP", f"R0, #0x{RACE_DINOSAUR:X}")
            b.insn("BNE", "c1nx")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.ldr_const(2, PROT_KEY)
            b.insn("MOV", f"R3, #0x{PROT_KIND_BYTE:X}")
            b.call_addr(ATTACH_NODE, via=R7)
            b.label("c1nx")
            b.insn("ADD", "R5, #0x1")
            b.insn("CMP", "R5, #0x5")
            b.insn("BLT", "c1lp")
            b.label("c1out")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            b.label("c2")
            b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R6, [R5, #0x2]")
            b.insn("LDRB", "R0, [R5, #0x6]")
            b.insn("EOR", "R6, R0")
            b.ldr_const(4, STATE)
            b.insn("LDR", "R4, [R4, #0x70]")
            b.insn("CMP", "R4, #0x80")
            b.insn("BEQ", "ph80")
            b.insn("CMP", "R4, #0x7F")
            b.insn("BEQ", "ph7f")
            b.insn("CMP", "R4, #0x7E")
            b.insn("BEQ", "ph7e")
            b.insn("CMP", "R4, #0x7C")
            b.insn("BEQ", "ph7c")
            b.insn("CMP", "R4, #0x7B")
            b.insn("BEQ", "ph7b")
            b.insn("CMP", "R4, #0x78")
            b.insn("BEQ", "ph78")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("ph7f")
            b.call_addr(MESSAGE, R6, 0x30, via=R3)
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("ph7e")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("MOV", "R1, #0x6")
            b.insn("LDRH", "R2, [R5, #0x0]")
            b.call_addr(PICKER, R0, R1, R2, 0, via=R7)
            b.insn("MOV", "R0, #0x7C")
            b.insn("B", "ret")
            b.label("ph7c")
            b.call_addr(PICK_READBACK, via=R7)
            b.insn("ADD", "R1, R0, #0x0")
            b.insn("LDRH", "R0, [R5, #0x0]")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("STR", "R0, [SP, #0x0]")
            b.call_addr(SS_COMMIT, R6, R1, 1, 2, via=R7)
            b.insn("MOV", "R0, #0x78")
            b.insn("B", "ret")
            b.label("ph7b")
            b.insn("MOV", "R0, #0x1")
            b.insn("SUB", "R0, R0, R6")
            b.call_addr(NO_CANDIDATE_CLEANUP, via=R3)
            b.insn("MOV", "R0, #0x78")
            b.insn("B", "ret")
            b.label("ph78")
            b.insn("LDRH", "R0, [R5, #0x0]")
            b.call_addr(ROW_INDEX, R0, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "td")
            _row0_ptr(b)
            b.insn("MOV", "R0, #0x0")
            b.insn("STRB", "R0, [R7, #0xA]")
            b.label("td")
            b.call_addr(TEARDOWN, R6, via=R3)
            b.insn("MOV", "R0, #0x64")
            b.insn("B", "ret")
            b.label("ph80")
            b.call_addr(SS_GATES[0], R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop")
            b.call_addr(SS_GATES[1], R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop")
            b.call_addr(SS_GATES[2], R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop")
            b.insn("LDRH", "R0, [R5, #0x0]")
            b.call_addr(ROW_INDEX, R0, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "stop")
            _row0_ptr(b)
            b.insn("LDRH", "R0, [R5, #0x14]")
            b.insn("CMP", "R0, #0xF")
            b.insn("BLE", "lvl")
            b.insn("MOV", "R0, #0xF")
            b.label("lvl")
            b.insn("LSL", "R0, R0, #0x2")
            b.insn("STRB", "R0, [R7, #0xA]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(CANDIDATES, R0, R1, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "p80ok")
            b.call_addr(MESSAGE, R6, 0xD, via=R3)
            b.insn("MOV", "R0, #0x7B")
            b.insn("B", "ret")
            b.label("p80ok")
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("stop")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            return _check(b.assemble(base, pad="nop"), base, RES_RESERVE, "resolver")


        def _speed_chained() -> bytes:
            """The leaf when overtex_qoatlus chains its own speed stub in FRONT of ours (it tails to SPEED_ADDR)."""
            q = getattr(ov5_cave, "CAVE_OQ_SPEED", None)
            return az._bl(SPEED_SITE, q) + struct.pack("<H", 0x46C0) if q else SPEED_HOOKED


        def _build_speed(base: int) -> bytes:
            """Entered by BL from 0x021A894C (the speed lookup's default leaf) with r2 = cid; for 0x0FF2
            r0 is still the descriptor (only other cids' own arms clobber r0 before this leaf)."""
            b = EffectBuilder()
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R2, R3")
            b.insn("BNE", "nat")
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", f"R3, #0x{ZONE_GY:X}")
            b.insn("BNE", "nat")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("nat")
            b.insn("ADD", "R0, R2, #0x0")
            b.ldr_const(3, SPEED_ARM9)
            b.insn("BX", "R3")
            return _check(b.assemble(base, pad="nop"), base, SPEED_RESERVE, "speed")


        def _check(blob: bytes, base: int, reserve: int, what: str) -> bytes:
            assert len(blob) <= reserve, f"{what} {len(blob):#x} > reserve {reserve:#x}"
            assert_thumb1_only(blob, base)
            return blob

        def _rows(ov, base: int, count: int, fmt: str, ram0: int = RAM_BASE) -> list[tuple]:
            n = struct.calcsize(fmt)
            return [struct.unpack_from(fmt, ov, base - ram0 + i * n) for i in range(count)]


        def _swap_rows(ov: bytearray, base: int, count: int, fmt: str, new: tuple, drop: int, label: str,
                       ram0: int = RAM_BASE) -> None:
            """Count-neutral sorted replace: every row keyed *drop* out, the *new* rows in (keyed by cid)."""
            rows = _rows(ov, base, count, fmt, ram0)
            if [r for r in rows if r[0] == DONOR_CID] == list(new):
                print(f"{label}: already applied")
                return
            assert DONOR_CID not in [r[0] for r in rows], f"{label}: 0x{DONOR_CID:04X} already present"
            kept = [r for r in rows if r[0] != drop]
            assert len(kept) == count - len(new), \
                f"{label}: phantom 0x{drop:04X} owns {count - len(kept)} row(s), need {len(new)}"
            pos = sum(1 for r in kept if r[0] < DONOR_CID)
            out = kept[:pos] + list(new) + kept[pos:]
            keys = [r[0] for r in out]
            assert keys == sorted(keys), f"{label}: lost its sort"
            n = struct.calcsize(fmt)
            for i, r in enumerate(out):
                struct.pack_into(fmt, ov, base - ram0 + i * n, *r)
            print(f"{label}: dropped 0x{drop:04X}, inserted 0x{DONOR_CID:04X} x{len(new)} @{pos}")


        def apply_effect(ov: bytearray) -> None:
            gy = _rows(ov, GYREG_BASE, GYREG_COUNT, "<4I")
            if GYREG_ROW not in gy:
                i = gy.index(GYREG_PHANTOM_ROW)
                struct.pack_into("<4I", ov, _off(GYREG_BASE + i * 16), *GYREG_ROW)
                print(f"A  GY-action row {i}: 0x144C -> 0x{DONOR_CID:04X}, Grapha family")
            _swap_rows(ov, CLS2_BASE, CLS2_COUNT, CLS_FMT, (CLS2_RECORD,), PH_CLS2, "B  cls2")
            _swap_rows(ov, CRIT_BASE, CRIT_COUNT, CRIT_FMT, CRIT_ROWS, PH_CRIT, "C  criteria")
            _swap_rows(ov, LISTA_BASE, LISTA_COUNT, "<H", ((DONOR_CID,),), PH_CRIT, "C  list A")
            _swap_rows(ov, EPLIST_BASE, EPLIST_COUNT, "<H", ((DONOR_CID,),), PH_EPLIST, "D  End-Phase list")
            cur = struct.unpack_from("<IH", ov, _off(EPREG_ROW))
            if cur != EPREG_AFTER:
                assert cur == EPREG_BEFORE, f"End-Phase registry row 254 is {cur}"
                struct.pack_into("<IH", ov, _off(EPREG_ROW), *EPREG_AFTER)
            print("D  End-Phase registry row 254 -> {0x02254E95, 0x0FF2}")
            o = _off(SPEED_SITE)
            if bytes(ov[o:o + 6]) != SPEED_HOOKED:
                assert bytes(ov[o:o + 6]) == SPEED_NATIVE, f"speed leaf 0x{SPEED_SITE:08X} is {ov[o:o + 6].hex()}"
                ov[o:o + 6] = SPEED_HOOKED
            print(f"H  speed hook 0x{SPEED_SITE:08X} -> 0x{SPEED_ADDR:08X}")


        def apply_azure_link(ov: bytearray, rom) -> None:
            """G: Azure-Eyes' protection link 0x021B0592, byte-identical to azure_eyes G2 (skipped
            when that patch already installed it, i.e. in the chain)."""
            assert az.PROT_KEY == PROT_KEY, "Azure-Eyes' private key changed"
            o = _off(az.PROT_HOOK)
            bl = az._bl(az.PROT_HOOK, az.PROT_STUB)
            if bytes(ov[o:o + 4]) == bl:
                print("G  Azure-Eyes protection link already installed")
                return
            assert bytes(ov[o:o + 4]) == az._bl(az.PROT_HOOK, az.NODE_QUERY_F1), "0x021B0592 not native"
            ov5_cave.install_cave(rom, az.PROT_STUB, az._build_protect_query_stub(az.PROT_STUB),
                                  reserve=az.PROT_STUB_RESERVE)
            ov[o:o + 4] = bl
            print(f"G  Azure-Eyes protection link 0x{az.PROT_HOOK:08X} -> 0x{az.PROT_STUB:08X}")


        def apply_arm9(rom) -> None:
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)
            _swap_rows(d, LISTB_BASE, LISTB_COUNT, "<H", ((DONOR_CID,),), PH_LISTB, "G  hand list B", ARM9_BASE)
            _swap_rows(d, QE_BASE, QE_COUNT, "<H", ((DONOR_CID,),), PH_QE, "G  speed-2 list", ARM9_BASE)
            sec.data = bytes(d)
            rom.arm9 = mc.save()

        stubs = ((COND_ADDR, _build_cond(COND_ADDR), "condition"), (COST_ADDR, _build_cost(COST_ADDR), "cost"),
                 (RES_ADDR, _build_res(RES_ADDR), "resolver"), (SPEED_ADDR, _build_speed(SPEED_ADDR), "speed hook"))

        def install(rom, view):
            apply_effect(view.buf)
            apply_azure_link(view.buf, rom)
            apply_arm9(rom)

        def check(c, rom, view):
            ov = bytes(view.buf)
            import ndspy.rom as _nr
            ov5 = bytes(rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID].data)
            at = lambda a, k: ov5[a - ov5_cave.OV5_RAM_BASE:a - ov5_cave.OV5_RAM_BASE + k]

            def only(base, count, fmt, want, ph):
                rs = _rows(ov, base, count, fmt)
                keys = [r[0] for r in rs]
                return [r for r in rs if r[0] == DONOR_CID] == list(want) and ph not in keys and keys == sorted(keys)

            a9 = ov5_cave._arm9_main(rom)[1].data
            for label, good in (
                    ("A GY-action row", _rows(ov, GYREG_BASE, GYREG_COUNT, "<4I").count(GYREG_ROW) == 1),
                    ("B cls2 record", only(CLS2_BASE, CLS2_COUNT, CLS_FMT, (CLS2_RECORD,), PH_CLS2)),
                    ("C criteria rows", only(CRIT_BASE, CRIT_COUNT, CRIT_FMT, CRIT_ROWS, PH_CRIT)),
                    ("C list A", only(LISTA_BASE, LISTA_COUNT, "<H", ((DONOR_CID,),), PH_CRIT)),
                    ("D End-Phase list", only(EPLIST_BASE, EPLIST_COUNT, "<H", ((DONOR_CID,),), PH_EPLIST)),
                    ("D End-Phase registry row 254", struct.unpack_from("<IH", ov, _off(EPREG_ROW)) == EPREG_AFTER),
                    ("E ov5 stubs (+ Azure link stub)",
                     all(at(a, len(b)) == b for a, b, _ in stubs)
                     and at(az.PROT_STUB, len(az._build_protect_query_stub(az.PROT_STUB)))
                     == az._build_protect_query_stub(az.PROT_STUB)),
                    ("G Azure link 0x021B0592", bytes(ov[_off(az.PROT_HOOK):_off(az.PROT_HOOK) + 4])
                     == az._bl(az.PROT_HOOK, az.PROT_STUB)),
                    ("G hand list B", [r[0] for r in _rows(a9, LISTB_BASE, LISTB_COUNT, "<H", ARM9_BASE)].count(DONOR_CID) == 1),
                    ("G speed-2 list", [r[0] for r in _rows(a9, QE_BASE, QE_COUNT, "<H", ARM9_BASE)].count(DONOR_CID) == 1),
                    ("H speed hook", code_reaches(rom, SPEED_SITE, SPEED_ADDR))):
                c.ok(good, label)

        return Compiled(stubs, installs=(install,), checks=(check,))


dinosaur_effects = hand_discard_dinosaurs_unaffected_and_graveyard_banish_dinosaurs_summon_deck_dinosaur_destroyed_at_end_phase

SPEC = card(0x0FF2, dinosaur_effects())

PROPS = card_props("FIRE", "Dinosaur", level=4, atk=1800, defense=1000)

import struct

from otn_enhanced.cards import azure_eyes as az
from otn_enhanced.effects import ov5_cave

# overtex_qoatlus reads these.
SPEED_SITE = 0x021A894C
SPEED_ADDR = ov5_cave.CAVE_MISC_SPEED
SPEED_HOOKED = az._bl(SPEED_SITE, SPEED_ADDR) + struct.pack("<H", 0x46C0)


def _build_speed(base: int = None) -> bytes:
    from otn_enhanced.effects.common import Ov
    from otn_enhanced.rom.overlay_io import load_overlay3
    _, ovb = load_overlay3(dsl.SRC)
    return SPEC.compile(Ov(bytearray(ovb))).stubs[3][1]


main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_miscellaneousaurus.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
