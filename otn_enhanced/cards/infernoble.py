"""The Infernoble family on vanilla donors (Knights, Arms, Horn of Olifant, Noble Arms Museum, The Continuing Epic of Charles).

    13 monsters + 7 Spell/Trap donors, all through one verb. The spec carries the last Spell/Trap card, The Continuing Epic of Charles 0x16DB
    (card_prop unchanged, text only); every other card's stats and text are written by the verb's post. (See card_text.CARD_TEXT for the full
    printed texts.)
"""
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, Compiled, DRAW_COUNT, SRC
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.data.card_stats import apply_stats_and_text
from otn_enhanced.data import card_text
from otn_enhanced.effects import cave3
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class infernoble_knights_and_arms_family_equip_link_hand_or_graveyard_summons_and_arms_lock_on_vanilla_and_spell_donors:
    """The Infernoble family on vanilla donors -- Knights Ogier / Maugis / Oliver / Turpin / Renaud / Ricciardetto / Roland / Astolfo / Bradamante /
    Captain Roland / Captain Oliver / Emperor Charles / Angelica, the Arms Joyeuse / Durendal / Almace / Hauteclere, Horn of Olifant, Noble Arms Museum
    and The Continuing Epic of Charles (13 monsters + 7 Spell/Trap donors). Cave stubs in ov5 and the ov3 pool, shared c79 / timing-class / GY-vrow
    hooks, count-neutral table inserts and the per-card applies run in `install` in the old order; the identity (Synchro type) rewrites and the
    stats + text of every card are posts (always writing text). The last Spell/Trap card, Epic of Charles, is `spec.cid` with props=None, so
    dsl.make writes its text last, exactly where the old loop did. Original code embedded verbatim; the two import-time snoww switch-stub
    registrations (Maugis's GY node, Roland's GY front) move to __post_init__."""

    def __post_init__(self):
        from otn_enhanced.cards import snoww as _s
        _s.register_switch_stub(0x021FAE44, 0x10, {0x139A: 0x021D19BE})   # CAVE3_IK_M_GYNODE, {MAUGIS: GY_ACCEPT_LEAF}
        _s.register_switch_stub(0x02237E1C, 0x1C, {0x0FDB: 0x021D19BE})   # RO_GY_FRONT, RO_GY_FRONT_LEN, {ROLAND: GY_ACCEPT_LEAF}

    def compile(self, view, cid) -> Compiled:
        import struct
        from otn_enhanced.asm import effect_verify
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R3, R4, R5, R6, R7
        from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.effects import c79_trigger_hook as c79, gy_vrow_hook as gyv
        from otn_enhanced.data import card_text
        from otn_enhanced.effects import ov5_cave as O5, timing_class_hook as tch
        from otn_enhanced.effects.common import insert_row
        from otn_enhanced.data.card_stats import apply_stats_and_text
        from otn_enhanced.effects.timing_class_hook import _bl

        SRC = "data/over_the_nexus/working/rom_all_patches.nds"
        OUT = "data/over_the_nexus/working/rom_infernoble.nds"

        OGIER, MAUGIS, OLIVER = 0x13A3, 0x139A, 0x1E04   # Robotic Knight, Wolf Axwielder, Tune Warrior (cids KEPT)
        STATS = {OGIER: dict(attribute="FIRE", race="Warrior", level=4, atk=1500, defense=2000,
                             card_type=ERA2_CARD_TYPE_REVERSE["Effect Monster"]),
                 MAUGIS: dict(attribute="FIRE", race="Warrior", level=4, atk=1500, defense=1000,
                              card_type=ERA2_CARD_TYPE_REVERSE["Effect Monster"]),
                 OLIVER: dict(attribute="FIRE", race="Warrior", level=4, atk=1000, defense=1500,
                              card_type=ERA2_CARD_TYPE_REVERSE["Tuner Monster"]),
                 0x0FC1: dict(attribute="FIRE", race="Warrior", level=4, atk=1400, defense=1700,
                              card_type=ERA2_CARD_TYPE_REVERSE["Effect Monster"]),
                 0x1E05: dict(attribute="FIRE", race="Warrior", level=1, atk=500, defense=500,
                              card_type=ERA2_CARD_TYPE_REVERSE["Effect Monster"]),
                 0x0FE6: dict(attribute="FIRE", race="Warrior", level=1, atk=500, defense=0,
                              card_type=ERA2_CARD_TYPE_REVERSE["Tuner Monster"]),
                 0x0FDB: dict(attribute="FIRE", race="Warrior", level=1, atk=500, defense=500,
                              card_type=ERA2_CARD_TYPE_REVERSE["Effect Monster"]),
                 0x0FD4: dict(attribute="FIRE", race="Warrior", level=1, atk=500, defense=200,
                              card_type=ERA2_CARD_TYPE_REVERSE["Effect Monster"]),
                 0x160B: dict(attribute="FIRE", race="Warrior", level=1, atk=500, defense=200,
                              card_type=ERA2_CARD_TYPE_REVERSE["Tuner Monster"]),
                 0x0FEB: dict(attribute="FIRE", race="Warrior", level=5, atk=2000, defense=500,
                              card_type=ERA2_CARD_TYPE_REVERSE["Synchro Tuner Effect Monster"]),
                 0x1118: dict(attribute="FIRE", race="Warrior", level=5, atk=2000, defense=500,
                              card_type=ERA2_CARD_TYPE_REVERSE["Synchro Effect Monster"]),
                 0x17EF: dict(attribute="FIRE", race="Warrior", level=9, atk=3000, defense=200,
                              card_type=ERA2_CARD_TYPE_REVERSE["Synchro Effect Monster"]),
                 0x1002: dict(attribute="FIRE", race="Warrior", level=5, atk=1200, defense=2400,
                              card_type=ERA2_CARD_TYPE_REVERSE["Synchro Effect Monster"])}
        TEXT_ONLY = (0x1976, 0x15E3, 0x1663, 0x1C39, 0x1F71, 0x1346, 0x16DB)   # Horn, Joyeuse, Durendal, Almace, Hauteclere, Museum
        C2KEY = 0x4000 | OGIER                     # C2's own once-per-turn turn-log key (bit 15 clear)
        WARRIOR_BIT = 15                           # race code 15 (KB dispatch.criteria_word_race_attribute)
        FIRE_WARRIOR = ((15 << 3) | 4) << 24 | 0x0002

        # --- natives -----------------------------------------------------------------------------------
        TURNLOG_QUERY, TURNLOG_POST = 0x021A14E9, 0x021D2585
        EQUIP_FROM_GY_RES, VYLON_FILTER, VYLON_SLOT5 = 0x02210961, 0x021D8465, 0x02234D81
        IGN_DISPATCH, VYLON_F1, VYLON_F2 = 0x021F0BDD, 0x021F8049, 0x022043F5
        ARMAGEDDON_RES, ARMAGEDDON_COND, TAG_YOU_CAN = 0x02208DD5, 0x021F0B19, 0x021E51E5
        CRIT_WORKER = 0x0223BC3C
        CARD_CID_AT, EQUIP_TARGET_OF = 0x021A36ED, 0x021A0DF9
        for _v in (TURNLOG_QUERY, TURNLOG_POST, EQUIP_FROM_GY_RES, VYLON_FILTER, VYLON_SLOT5, IGN_DISPATCH, VYLON_F1,
                   VYLON_F2, ARMAGEDDON_RES, ARMAGEDDON_COND, TAG_YOU_CAN, CARD_CID_AT, EQUIP_TARGET_OF):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

        # --- tables ------------------------------------------------------------------------------------
        CLS_FMT = "<HHIIIII"
        CLS1_BASE, CLS1_COUNT, CLS1_PHANTOM = 0x022860D4, 0x535, 0x1370
        CLS2_BASE, CLS2_COUNT, CLS2_PHANTOM = 0x02275C04, 0x2B9, 0x1B48
        CRIT_BASE, CRIT_COUNT, CRIT_FMT, CRIT_PHANTOM = 0x022713C4, 0x56C, "<HHII", 0x0E7E
        IGN_BASE, IGN_COUNT, IGN_FMT, IGN_PHANTOM = 0x0226FAFC, 0x92, "<HHII", 0x0E86

        L = {n: getattr(O5, f"CAVE_IK_{n}") for n in ("EQFILT", "PROT", "C3F2", "C3COST", "C2H", "C2CB", "C2COND", "C2SLOT4")}
        RESERVE = {"EQFILT": 0x80, "PROT": 0xA0, "C3F2": 0x30, "C3COST": 0x20, "C2H": 0x30, "C2CB": 0x20,
                   "C2COND": 0x30, "C2SLOT4": 0x30}

        CLS2_REC = (OGIER, 0, EQUIP_FROM_GY_RES, VYLON_FILTER, IGN_DISPATCH, L["C3COST"] | 1, VYLON_SLOT5)
        IGN_REC = (OGIER, 0, VYLON_F1, L["C3F2"] | 1)
        CLS1_REC = (OGIER, 0, ARMAGEDDON_RES, 0, L["C2COND"] | 1, L["C2SLOT4"] | 1, 0)
        CRIT_REC = (OGIER, 0xFFFF, L["C2H"] | 1, 0x00000006)         # Monster | Spell; AR_NACB filters (Noble Arms half)

        # --- hook sites --------------------------------------------------------------------------------
        EQ_SITE, EQ_STOCK, EQ_RET = 0x021D73A0, bytes.fromhex("0099aa4f"), 0x021D817B   # ldr r1,[sp] ; ldr r7,=0x1ABA
        PROT_SITE, PROT_STOCK = 0x021B059C, bytes.fromhex("042d00dd")                    # cmp r5,#4 ; ble 0x021B05A2
        PROT_MONSTER, PROT_PROTECTED = 0x021B05A3, 0x021B0297
        SITES = ((EQ_SITE, EQ_STOCK, L["EQFILT"]), (PROT_SITE, PROT_STOCK, L["PROT"]))

        # ARM_JET's test with a LOCAL skip and an unconditional `b out` (+-2 KB). Every arm's conditional `bne out`
        # targets the stub's far end, so APPENDING any arm pushes an EARLY arm (Jet Warrior's ARM_JW) past Thumb-1's
        # +-256 B conditional range. Maugis's arm is therefore PREPENDED: every existing arm keeps its exact distance to
        # `out`, and only this arm's own exit is far -- which the unconditional `b` covers.
        ARM_IKM = f"""
                ldrb    r1, [r4, #0x3]
                cmp     r1, #0xe
                bne     ikmskip
                ldrb    r1, [r4, #0x4]
                cmp     r1, #6
                ble     ikmskip
                ldr     r0, ={TAG_YOU_CAN:#x}
              ikmskip:
                b       out
        """
        C79_ARMS = c79.ARMS                                       # Ogier + Ricciardetto now live in c79_trigger_hook.ARMS
        # Roland's arm: same shape as ARM_IKM, also PREPENDED (zone GY = its End-Phase C2).
        ARM_RO = f"""
                ldrb    r1, [r4, #0x3]
                cmp     r1, #0xe
                bne     roskip
                ldr     r0, ={TAG_YOU_CAN:#x}
              roskip:
                b       out
        """
        ARM_BR = ARM_RO.replace("roskip", "brskip")
        TCH_ARMS = tch.ARMS                                       # the Infernoble arms now live in timing_class_hook.ARMS


        # =================================================================================================
        # stubs
        # =================================================================================================
        def eqfilt_stub() -> EffectBuilder:
            """BL over `ldr r1,[sp] ; ldr r7,=0x1ABA` @0x021D73A0 (r0 = candidate cid, r6 = its side, [sp+0x10] = its race
            mask).  Not ours: replay both loads (only r1/r2/r7 touched; 0x021D73A4 reloads r2) and return.  Ours: r0 = 1
            iff Warrior and the candidate's side == desc[+2], out through the switch's common return 0x021D817A."""
            b = EffectBuilder()
            b.insn("LDR", "R1, [SP, #0x0]")
            b.insn("LDRH", "R2, [R1, #0x0]")
            b.ldr_const(7, OGIER)
            b.insn("CMP", "R2, R7")
            b.insn("BEQ", "ours")
            b.ldr_const(7, MAUGIS)
            b.insn("CMP", "R2, R7")
            b.insn("BEQ", "ours")
            b.ldr_const(7, OLIVER)
            b.insn("CMP", "R2, R7")
            b.insn("BEQ", "ours")
            b.ldr_const(7, TURPIN)
            b.insn("CMP", "R2, R7")
            b.insn("BEQ", "ours")
            b.ldr_const(7, BRADA)
            b.insn("CMP", "R2, R7")
            b.insn("BEQ", "ours")
            b.ldr_const(7, CAPROL)
            b.insn("CMP", "R2, R7")
            b.insn("BEQ", "ours")
            b.ldr_const(7, ROLAND)
            b.insn("CMP", "R2, R7")
            b.insn("BEQ", "rol")
            b.ldr_const(7, 0x1aba)
            b.insn("BX", "LR")
            b.label("rol")
            b.insn("MOV", "R0, #0x0")
            b.insn("LDRB", "R2, [R1, #0x2]")
            b.insn("CMP", "R2, R6")
            b.insn("BNE", "done")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "done")
            b.label("ours")
            b.insn("MOV", "R0, #0x0")
            b.insn("LDRB", "R2, [R1, #0x2]")
            b.insn("CMP", "R2, R6")
            b.insn("BNE", "done")
            b.insn("LDR", "R2, [SP, #0x10]")
            b.insn("MOV", "R3, #0x1")
            b.insn("LSL", f"R3, R3, #0x{WARRIOR_BIT:X}")
            b.insn("AND", "R2, R3")
            b.insn("BEQ", "done")
            b.insn("MOV", "R0, #0x1")
            b.label("done")
            b.ldr_const(3, EQ_RET)
            b.insn("BX", "R3")
            return b


        def prot_stub() -> EffectBuilder:
            """BL over `cmp r5,#4 ; ble 0x021B05A2` @0x021B059C; lr = 0x021B05A0 (`b 0x021B07EA`, the S/T tail).
            r6 = target side, r5 = target slot, r7 = acting desc (all live).  Monster slot: protected iff some S/T card
            of cid 0x13A3 is equipped to (r6, r5) (Ogier: any card effect), or one of cid 0x1E04 is (Oliver: only when the
            predicate's TARGETS flag -- its [sp], here [sp+0x10] -- is set AND the acting desc's controller is the target's
            opponent, Safe Zone's "1 - desc[+2] == side" test; pushed r7 = desc at [sp+0xC], pushed r6 = side at [sp+8])."""
            b = EffectBuilder()
            b.insn("CMP", "R5, #0x4")
            b.insn("BLE", "mon")
            b.insn("BX", "LR")
            b.label("mon")
            b.insn("PUSH", "{R4, R5, R6, R7}")
            b.insn("LSL", "R7, R5, #0x8")
            b.insn("ORR", "R7, R6")
            b.insn("MOV", "R4, #0x0")
            b.label("sloop")
            b.insn("MOV", "R5, #0x5")
            b.label("zloop")
            b.call_addr(CARD_CID_AT, R4, R5, via=R2)
            b.ldr_const(1, OGIER)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "linked")
            b.ldr_const(1, OLIVER)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "next")
            b.insn("LDR", "R1, [SP, #0x10]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "next")
            b.insn("LDR", "R1, [SP, #0xC]")
            b.insn("LDRB", "R1, [R1, #0x2]")
            b.insn("MOV", "R2, #0x1")
            b.insn("SUB", "R1, R2, R1")
            b.insn("LDR", "R2, [SP, #0x8]")
            b.insn("CMP", "R1, R2")
            b.insn("BNE", "next")
            b.label("linked")
            b.call_addr(EQUIP_TARGET_OF, R4, R5, via=R2)
            b.insn("CMP", "R0, R7")
            b.insn("BEQ", "prot")
            b.label("next")
            b.insn("ADD", "R5, #0x1")
            b.insn("CMP", "R5, #0x9")
            b.insn("BLE", "zloop")
            b.insn("ADD", "R4, #0x1")
            b.insn("CMP", "R4, #0x1")
            b.insn("BLE", "sloop")
            b.insn("POP", "{R4, R5, R6, R7}")
            b.ldr_const(0, PROT_MONSTER)
            b.insn("BX", "R0")
            b.label("prot")
            b.insn("POP", "{R4, R5, R6, R7}")
            b.ldr_const(0, PROT_PROTECTED)
            b.insn("BX", "R0")
            return b


        def _opt_gate_stub(key: int, tail: int) -> EffectBuilder:
            """(desc, r1): 0 if the turn log holds (side, 0xB, key, 1), else tail(desc, r1)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.turnlog_query(R0, key, 1, via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "used")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.ldr_const(4, tail)
            b.insn("BLX", "R4")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("used")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def c3cost_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDRB", "R0, [R0, #0x2]")
            b.turnlog_post(R0, OGIER, 1, via=R4)
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            return b


        def c2h_stub() -> EffectBuilder:
            """0x0223CAD9 + r2 = C2CB, r3 = the excluded cid (the callback's [sp+4])."""
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2, R3, LR}")
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDR", "R0, [R2, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("LDRH", "R1, [R2, #0x0]")
            b.call_addr(CRIT_WORKER, R0, R1, O5.CAVE_IK_AR_NACB | 1, OGIER)
            b.insn("POP", "{R1, R2, R3, PC}")
            return b


        def c2cb_stub() -> EffectBuilder:
            """Worker callback: [sp] = &candidate card word, [sp+4] = excluded cid -> 1 keep / 0 reject."""
            b = EffectBuilder()
            b.insn("LDR", "R0, [SP, #0x0]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("LDR", "R1, [SP, #0x4]")
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b


        def c2slot4_stub() -> EffectBuilder:
            """Magician's Rod / Psi-Reflector slot4: "You can" tag, and on 1 post the OPT node."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(TAG_YOU_CAN, via=R2)
            b.insn("CMP", "R0, #0x1")
            b.insn("BNE", "out")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_post(R0, C2KEY, 1, via=R4)
            b.insn("ADD", "R0, R5, #0x0")
            b.label("out")
            b.insn("POP", "{R4, R5, PC}")
            return b


        # =================================================================================================
        # card 2: Wolf Axwielder 0x139A -> Infernoble Knight Maugis (whole card; notes/infernoble-maugis-findings.md)
        #   C1 equipped monster cannot be destroyed by battle -> M_BATTLE fronts Mist Body's query BL @0x021984C8.
        #   C2 "If this card is sent to the GY: You can shuffle 3 of your other FIRE Warriors (banished and/or GY) into the
        #      Deck; draw 1"  (user option "a": targets on activation, banished allowed).
        #   C3 Ogier's GY equip.   C2 and C3 share ONE cls2 record (find_event_handler is leftmost-only), its slots switched
        #      on Jet Synchron's discriminator desc[+3] == 0x0E && desc[+4] > 6 (leave/relocation codes) vs a GY-action
        #      offer (code <= 6, dispatch.gy_action_offer_caps_the_event_code).
        # =================================================================================================
        from otn_enhanced.effects import cave3                                           # noqa: E402
        from otn_enhanced.cards import snoww as _snoww                         # noqa: E402

        M_C2KEY = 0x4000 | MAUGIS
        M_FIRE_WARRIOR_GY = ((15 << 3) | 4) << 24 | 0x00010002          # Royal Firestorm / Psychic Overload word shape
        SLOT5_TAIL, SLOT5_TEXT, SLOT5_THREE = 0x02235913, 0x116, 9     # r4 = 9 -> count r4 - 6 = 3 (Psychic Overload arm)
        ROW_PARAM, ROW_COUNT = 0x02234E79, 0x02243FE1
        GY_LOOK, BAN_LOOK = 0x021A2511, 0x021A2559
        TGT_REF, TGT_VALID = 0x02234965, 0x022349B1
        GY_TO_DECK, BAN_TO_DECK = 0x021C6A0D, 0x021C6A9D
        CHAIN_PUSH, RES_END_A, RES_END_B, DRAW_RES = 0x021D28A5, 0x021D2965, 0x021D26CD, 0x022065B9
        GY_WORKER, BAN_WORKER = 0x0223C4E8, 0x0223C6AC
        MIST_QUERY = 0x021A0951
        for _v in (ROW_PARAM, ROW_COUNT, GY_LOOK, BAN_LOOK, TGT_REF, TGT_VALID, GY_TO_DECK, BAN_TO_DECK, CHAIN_PUSH, RES_END_A,
                   RES_END_B, DRAW_RES, MIST_QUERY, SLOT5_TAIL):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

        ML = {n: getattr(O5, f"CAVE_IK_M_{n}") for n in ("RES", "FILT", "COND", "SLOT4", "SLOT5", "C2RES", "C2H", "C3F2",
                                                          "BATTLE")}
        MRESERVE = {"RES": 0x20, "FILT": 0x20, "COND": 0x60, "SLOT4": 0x50, "SLOT5": 0x30, "C2RES": 0x120, "C2H": 0x40,
                    "C3F2": 0x30, "BATTLE": 0x60}
        M_CLS2_PHANTOM, M_IGN_PHANTOM, M_CRIT_PHANTOM = 0x1B49, 0x0E7D, 0x0E7F      # unclaimed in their pools (free_phantoms.py)
        M_MASK_PHANTOM, M_DRAW_PHANTOM = 0x0E1D, 0x0E19
        MASK_BASE, MASK_COUNT, DRAW_BASE, DRAW_COUNT = 0x0226EC1C, 0x98, 0x022704A4, 189
        M_CLS2_REC = (MAUGIS, 0, ML["RES"] | 1, ML["FILT"] | 1, ML["COND"] | 1, ML["SLOT4"] | 1, ML["SLOT5"] | 1)
        M_IGN_REC = (MAUGIS, 0, VYLON_F1, ML["C3F2"] | 1)
        M_CRIT_REC = (MAUGIS, 0xFFFF, ML["C2H"] | 1, 0x00010006)   # Monster | Spell (+ GY bit 16); AR_NACB filters
        M_MASK_REC = (MAUGIS, 0x0800)                    # sent to the GY from the field (Shadow Mist / Cross Porter mask)
        M_DRAW_REC = (MAUGIS, 1)

        BATTLE_SITE, BATTLE_STOCK = 0x021984C8, bytes.fromhex("08f042fa")                # bl 0x021A0950 (Mist Body query)
        GYNODE_SITE, GYNODE_STOCK = 0x021D13F6, bytes.fromhex("833a9542")                # subs r2,#0x83 ; cmp r5,r2
        GY_ACCEPT_LEAF = 0x021D19BE                                                      # _switch_leaf's accept report
        MISS_SITE = 0x021EE10C                                                           # Shadow Mist's node (BL, chained)


        def _trig(b: EffectBuilder, reg: str, c3: str) -> None:
            """Branch to *c3* unless desc (r0) is the sent-to-GY trigger: zone 0x0E and event code > 6."""
            b.insn("LDRB", f"{str(reg).upper()}, [R0, #0x3]")
            b.insn("CMP", f"{str(reg).upper()}, #0xE")
            b.insn("BNE", f"{c3}")
            b.insn("LDRB", f"{str(reg).upper()}, [R0, #0x4]")
            b.insn("CMP", f"{str(reg).upper()}, #0x6")
            b.insn("BLE", f"{c3}")


        def m_res_stub() -> EffectBuilder:
            b = EffectBuilder()
            _trig(b, "r3", "c3")
            b.ldr_const(3, ML['C2RES'] | 1)
            b.insn("BX", "R3")
            b.label("c3")
            b.ldr_const(3, EQUIP_FROM_GY_RES)
            b.insn("BX", "R3")
            return b


        def m_filt_stub() -> EffectBuilder:
            b = EffectBuilder()
            _trig(b, "r3", "c3")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            b.label("c3")
            b.ldr_const(3, VYLON_FILTER)
            b.insn("BX", "R3")
            return b


        def m_cond_stub() -> EffectBuilder:
            """C2: OPT (M_C2KEY) clear and >= 3 criteria candidates -> 2 (Royal Firestorm's 0x0224A115 code); C3: the
            GY-ignition dispatch 0x021F0BDD (-> ignition row f1 && f2)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            _trig(b, "r3", "c3")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.turnlog_query(R0, M_C2KEY, 1, via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            b.call_addr(ROW_PARAM, R5, via=R4)
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(ROW_COUNT, via=R4)
            b.insn("CMP", "R0, #0x3")
            b.insn("BLT", "no")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("c3")
            b.call_addr(IGN_DISPATCH, R5, R6, via=R4)
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def m_slot4_stub() -> EffectBuilder:
            """C2: the plain "You can" tag -- NO stamp here (BUILD 3): slot5's shared tail re-runs +0C at phase 0
            (0x0223599C), so a stamp on "Yes" made the re-check refuse and the picker never opened (in-game test 1).  The
            C2 OPT is checked-and-stamped at resolver phase 0x80 instead.  C3: post (side, 0x139A, 1), return 1."""
            b = EffectBuilder()
            _trig(b, "r3", "c3")
            b.ldr_const(3, TAG_YOU_CAN)
            b.insn("BX", "R3")
            b.label("c3")
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDRB", "R0, [R0, #0x2]")
            b.turnlog_post(R0, MAUGIS, 1, via=R4)
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            return b


        def m_slot5_stub() -> EffectBuilder:
            """C2: replay slot5 0x02235700's prologue exactly (push {r3-r7,lr}; r5 = desc; [sp] = r1; r6 = 0x116) with the
            Psychic Overload arm's r4 = 9 and enter its shared tail 0x02235912.  C3: Vylon's slot5."""
            b = EffectBuilder()
            _trig(b, "r3", "c3")
            b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("STR", "R1, [SP, #0x0]")
            b.insn("MOV", f"R4, #0x{SLOT5_THREE:X}")
            b.ldr_const(6, SLOT5_TEXT)
            b.ldr_const(0, SLOT5_TAIL)
            b.insn("BX", "R0")
            b.label("c3")
            b.ldr_const(3, VYLON_SLOT5)
            b.insn("BX", "R3")
            return b


        def m_c2res_stub() -> EffectBuilder:
            """0x0221FB94's phase machine for THIS card, with each target found in the GY (0x021A2510) OR banished
            (0x021A2558) and moved by the matching twin (0x021C6A0C / 0x021C6A9C, flag 1 as every native caller).
            Draw = the native default arm 0x022065B8 (draw-count row {0x139A, 1})."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x4")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BEQ", "p80")
            b.insn("CMP", "R0, #0x7F")
            b.insn("BEQ", "p7f")
            b.insn("CMP", "R0, #0x7E")
            b.insn("BEQ", "p7e")
            b.insn("CMP", "R0, #0x7D")
            b.insn("BEQ", "p7d")
            b.label("ret0")
            b.insn("MOV", "R0, #0x0")
            b.label("out")
            b.insn("ADD", "SP, #0x4")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("p80")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_query(R0, M_C2KEY, 1, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "ret0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_post(R0, M_C2KEY, 1, via=R5)
            b.insn("LDRH", "R5, [R4, #0x12]")
            b.insn("CMP", "R5, #0x0")
            b.insn("BEQ", "ret0")
            b.insn("MOV", "R7, #0x0")
            b.label("l80")
            b.insn("CMP", "R7, R5")
            b.insn("BGE", "ok80")
            b.call_addr(TGT_REF, R4, R7, via=R3)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDR", "R1, [SP, #0x0]")
            b.call_addr(GY_LOOK, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BGE", "n80")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDR", "R1, [SP, #0x0]")
            b.call_addr(BAN_LOOK, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "ret0")
            b.label("n80")
            b.insn("ADD", "R7, #0x1")
            b.insn("B", "l80")
            b.label("ok80")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x74]")
            b.insn("STR", "R5, [R6, #0x78]")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "out")
            b.label("p7f")
            b.insn("LDR", "R1, [R6, #0x78]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "to7e")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("SUB", "R1, #0x1")
            b.call_addr(TGT_VALID, R0, R1, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "fail")
            b.insn("LDR", "R1, [R6, #0x78]")
            b.insn("SUB", "R1, #0x1")
            b.call_addr(TGT_REF, R4, via=R3)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRB", "R1, [R4, #0x2]")
            b.insn("LDR", "R2, [SP, #0x0]")
            b.call_addr(GY_TO_DECK, R0, R1, R2, 1, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "dec")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDR", "R1, [SP, #0x0]")
            b.call_addr(BAN_TO_DECK, R0, R1, 1, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "dec")
            b.label("fail")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R6, #0x74]")
            b.label("dec")
            b.insn("LDR", "R1, [R6, #0x78]")
            b.insn("SUB", "R1, #0x1")
            b.insn("STR", "R1, [R6, #0x78]")
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "out")
            b.label("to7e")
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "out")
            b.label("p7e")
            b.call_addr(RES_END_A, via=R3)
            b.call_addr(RES_END_B, via=R3)
            b.insn("MOV", "R0, #0x7D")
            b.insn("B", "out")
            b.label("p7d")
            b.insn("LDR", "R0, [R6, #0x74]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ret0")
            b.call_addr(DRAW_RES, R4, via=R3)
            b.insn("B", "ret0")
            return b


        def m_c2h_stub() -> EffectBuilder:
            """Criteria handler (row, side, param): GY worker (mode 0, 0x0223CBB0's call) + banished worker (mode 0xC,
            0x0223E5D0's call), counts summed (0x0223C4E8 itself sums two worker passes); both with Ogier's exclude-cid
            callback (cid != [sp+4] = 0x139A: 'your OTHER FIRE Warriors')."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.insn("LDR", "R0, [R5, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(GY_WORKER, R0, R1, O5.CAVE_IK_AR_NACB | 1, MAUGIS)
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDR", "R0, [R5, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0xC")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(BAN_WORKER, R0, R1, O5.CAVE_IK_AR_NACB | 1, MAUGIS)
            b.insn("ADD", "R0, R4, R0")
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def m_battle_stub() -> EffectBuilder:
            """BL over Mist Body's `bl 0x021A0950` @0x021984C8 (r0 = side = r5, r1 = slot = r4, r2 = 0x1992): the native
            answer, OR an S/T card of cid 0x139A equipped to (r5, r4) -- Ogier's PROT scan."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.call_addr(MIST_QUERY, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "out")
            b.insn("LSL", "R7, R4, #0x8")
            b.insn("ORR", "R7, R5")
            b.insn("MOV", "R4, #0x0")
            b.label("sloop")
            b.insn("MOV", "R5, #0x5")
            b.label("zloop")
            b.call_addr(CARD_CID_AT, R4, R5, via=R2)
            b.ldr_const(1, MAUGIS)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "next")
            b.call_addr(EQUIP_TARGET_OF, R4, R5, via=R2)
            b.insn("CMP", "R0, R7")
            b.insn("BEQ", "yes")
            b.label("next")
            b.insn("ADD", "R5, #0x1")
            b.insn("CMP", "R5, #0x9")
            b.insn("BLE", "zloop")
            b.insn("ADD", "R4, #0x1")
            b.insn("CMP", "R4, #0x1")
            b.insn("BLE", "sloop")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "out")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.label("out")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def m_gynode_stub() -> EffectBuilder:
            """ov3, BL over `subs r2,#0x83 ; cmp r5,r2` @0x021D13F6 -- 0x139A's TERMINAL node in the sent-to-GY chain
            (traced by execution: 0x1309 -> bgt 0x021D13F6; r2 = 0x1466 on entry, the node tests Archfiend of Gilfer
            0x13E3, a real card).  0x139A (= 0x13E3 - 0x49) -> Z set, so the caller's `bne 0x021D13FE` falls through to
            the native accept `b 0x021D1938`; else the replayed compare.  r0 is dead on both exits (accept / reject
            reload it).  Only bgt @0x021D13EC branches here, to the node's first byte."""
            b = EffectBuilder()
            b.insn("SUB", "R2, #0x83")
            b.insn("MOV", "R0, #0x49")
            b.insn("SUB", "R0, R2, R0")
            b.insn("CMP", "R5, R0")
            b.insn("BEQ", "ret")
            b.insn("CMP", "R5, R2")
            b.label("ret")
            b.insn("BX", "LR")
            return b


        def m_miss_stub(prev: int) -> EffectBuilder:
            """ov3, the miss-timing node's front (r3 = cid; Eva's shape): 0x139A -> Z (never miss), else tail-jump to
            whatever the node BL'd before (Eva's front -> Shadow Mist's block A ...).  r1 is dead on both exits."""
            b = EffectBuilder()
            b.insn("MOV", "R1, #0x9D")
            b.insn("LSL", "R1, R1, #0x5")
            b.insn("SUB", "R1, #0x6")
            b.insn("CMP", "R3, R1")
            b.insn("BEQ", "ret")
            b.ldr_const(1, prev | 1)
            b.insn("BX", "R1")
            b.label("ret")
            b.insn("BX", "LR")
            return b


        MSTUBS = {"RES": m_res_stub, "FILT": m_filt_stub, "COND": m_cond_stub, "SLOT4": m_slot4_stub, "SLOT5": m_slot5_stub,
                 "C2RES": m_c2res_stub, "C2H": m_c2h_stub, "C3F2": lambda: _opt_gate_stub(MAUGIS, VYLON_F2),
                 "BATTLE": m_battle_stub}


        # =================================================================================================
        # card 3: Tune Warrior 0x1E04 -> Infernoble Knight Oliver (whole card; notes/infernoble-oliver-findings.md)
        #   C1 opponent cannot target the equipped monster -> PROT (shared with Ogier), Oliver arm.
        #   C2 (hand) "You can send 1 FIRE Warrior monster or 1 Equip Spell from your hand or face-up field to the GY;
        #      Special Summon this card from your hand as a Level 1 monster."  (user: build the mixed cost)
        #   C3 Ogier's GY equip.  C2 (hand, desc[+3] == 0x0B) and C3 (GY) share ONE cls2 record (Sakitama's switch).
        #   Hand offer = ARM9 LIST B 0x0209BC8C over phantom 0x1A86 (KB: hand effects need LIST A or B membership).
        # =================================================================================================
        O_C2KEY = 0x4000 | OLIVER
        LISTB_BASE, LISTB_COUNT, LISTB_PHANTOM = 0x0209BC8C, 0x24, 0x1A86
        HAND_SS_RES, LOCATE, RIDER_WRITE, LEVEL_SET_KEY = 0x02206ABD, 0x021A241D, 0x021C479D, 0x1EC1
        HAND_COST, FIELD_COST, SHORTCIRCUIT, PROMPT = 0x021E7245, 0x021E712D, 0x021D2BC9, 0x0219ABB5
        CHOICE, ZONE_PRED, FREE_MZ, FIELD_COUNT = 0x0229DD94, 0x021D6E41, 0x021AD871, 0x0224AA95
        HAND_WORKER = 0x0223BFD4
        GET_RACE, GET_ATTR, GET_SPELLTYPE = 0x0202ABB9, 0x0202ABC9, 0x0202ABE9
        RACE_WARRIOR, RACE_SPELL, ATTR_FIRE, SPELL_EQUIP = 15, 23, 4, 3
        DLG_SEND_TITLE, DLG_HANDS, DLG_FIELD = 0x3A, 0x192, 0x23C       # dlg_text_e, read
        for _v in (HAND_SS_RES, LOCATE, RIDER_WRITE, HAND_COST, FIELD_COST, SHORTCIRCUIT, PROMPT, ZONE_PRED, FREE_MZ,
                   FIELD_COUNT, GET_RACE, GET_ATTR, GET_SPELLTYPE):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"

        OL = {n: getattr(O5, f"CAVE_IK_O_{n}") for n in ("SLOT5", "RES", "FILT", "HANDCB", "FIELD", "COND", "COST", "C2RES",
                                                          "HANDH", "C3F2", "HANDANY")}
        ORESERVE = {"SLOT5": 0x20, "RES": 0x20, "FILT": 0x20, "HANDCB": 0x60, "FIELD": 0x70, "COND": 0x80, "COST": 0x100,
                    "C2RES": 0x90, "HANDH": 0x30, "C3F2": 0x30, "HANDANY": 0x40}
        HAND_COUNT_PTR = 0x0229AC94 + 0x0C       # player + 0x0C = hand count (jet_synchron; .ml2: 8 == the 8 cards)
        O_CLS2_PHANTOM, O_IGN_PHANTOM, O_CRIT_PHANTOM = 0x1B4A, 0x0EA9, 0x0ECA
        O_CLS2_REC = (OLIVER, 0, OL["RES"] | 1, OL["FILT"] | 1, OL["COND"] | 1, OL["COST"] | 1, OL["SLOT5"] | 1)
        O_IGN_REC = (OLIVER, 0, VYLON_F1, OL["C3F2"] | 1)
        O_CRIT_REC = (OLIVER, 0xFFFF, OL["HANDH"] | 1, 0x00000000)       # word 0 = any card; HANDCB filters


        def _hand(b: EffectBuilder, reg: str, c3: str) -> None:
            """Branch to *c3* unless desc (r0) is the HAND offer (zone 0x0B, the hand probe 0x021EDD90's value)."""
            b.insn("LDRB", f"{str(reg).upper()}, [R0, #0x3]")
            b.insn("CMP", f"{str(reg).upper()}, #0xB")
            b.insn("BNE", f"{c3}")


        def o_res_stub() -> EffectBuilder:
            b = EffectBuilder()
            _hand(b, "r3", "c3")
            b.ldr_const(3, OL['C2RES'] | 1)
            b.insn("BX", "R3")
            b.label("c3")
            b.ldr_const(3, EQUIP_FROM_GY_RES)
            b.insn("BX", "R3")
            return b


        def o_filt_stub() -> EffectBuilder:
            b = EffectBuilder()
            _hand(b, "r3", "c3")
            b.ldr_const(3, OL['FIELD'] | 1)
            b.insn("BX", "R3")
            b.label("c3")
            b.ldr_const(3, VYLON_FILTER)
            b.insn("BX", "R3")
            return b


        def o_slot5_stub() -> EffectBuilder:
            """Hand: no target declaration -> 1 (advance, dispatch.cls_slot_roles).  C3: Vylon's slot5."""
            b = EffectBuilder()
            _hand(b, "r3", "c3")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("c3")
            b.ldr_const(3, VYLON_SLOT5)
            b.insn("BX", "R3")
            return b


        def _fire_warrior_or_equip(b: EffectBuilder, cid_reg: str, yes: str, no: str, fw_only: bool = False) -> None:
            """cid in r4 (preserved): Equip Spell (race 23 && spell type 3) or FIRE Warrior (race 15 && attr 4)."""
            if not fw_only:
                b.insn("ADD", f"R0, {cid_reg.upper()}, #0")
                b.ldr_const(3, GET_SPELLTYPE)
                b.insn("BLX", "R3")
                b.insn("CMP", f"R0, #{SPELL_EQUIP}")
                b.insn("BNE", f"fw_{yes}")
                b.insn("ADD", f"R0, {cid_reg.upper()}, #0")
                b.ldr_const(3, GET_RACE)
                b.insn("BLX", "R3")
                b.insn("CMP", f"R0, #{RACE_SPELL}")
                b.insn("BEQ", yes)
            b.label(f"fw_{yes}")
            b.insn("ADD", f"R0, {cid_reg.upper()}, #0")
            b.ldr_const(3, GET_RACE)
            b.insn("BLX", "R3")
            b.insn("CMP", f"R0, #{RACE_WARRIOR}")
            b.insn("BNE", no)
            b.insn("ADD", f"R0, {cid_reg.upper()}, #0")
            b.ldr_const(3, GET_ATTR)
            b.insn("BLX", "R3")
            b.insn("CMP", f"R0, #{ATTR_FIRE}")
            b.insn("BNE", no)
            b.insn("B", yes)


        def o_handcb_stub() -> EffectBuilder:
            """Hand worker callback ([sp] = &card word, [sp+4] = excluded cid 0x1E04): keep FIRE Warrior / Equip Spell."""
            b = EffectBuilder()
            b.insn("LDR", "R0, [SP, #0x0]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("LDR", "R1, [SP, #0x4]")
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "no0")
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            _fire_warrior_or_equip(b, "r4", "yes", "no")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            b.label("no0")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b


        def o_field_stub() -> EffectBuilder:
            """Field-cost +08 (desc, side, zone): 0x021D6E40 mask 0x05 (your side, face-up), then monster zone -> FIRE
            Warrior, S/T zone 5..9 -> Equip Spell or a FIRE Warrior card held there as an equip."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.call_addr(ZONE_PRED, R0, R1, R2, 5, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(CARD_CID_AT, R5, R6, via=R7)
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("CMP", "R6, #0x9")
            b.insn("BGT", "no")
            b.insn("CMP", "R6, #0x4")
            b.insn("BGT", "st")
            b.insn("B", "fw_yes")
            b.label("st")
            _fire_warrior_or_equip(b, "r4", "yes", "no")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def o_cond_stub() -> EffectBuilder:
            """Hand: C2 OPT clear, a free Monster Zone, and a hand OR field cost -> 2.  C3: 0x021F0BDD."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            _hand(b, "r3", "c3")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.turnlog_query(R0, O_C2KEY, 1, via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.call_addr(FREE_MZ, via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(OL['HANDANY'], R5, via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "yes")
            b.call_addr(FIELD_COUNT, R5, via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")
            b.label("yes")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("c3")
            b.call_addr(IGN_DISPATCH, R5, R6, via=R4)
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def o_cost_stub() -> EffectBuilder:
            """+10.  C3: post (side, 0x1E04, 1), return 1 (Ogier's C3COST).  HAND (C2), on the cost phase [0x0229AAFC+0x7C]
            (protocol 0 = yield, 1 = done, -1 = abort; dragon_rulers.cost_stub):
              settled (0x021D2BC8)        -> 1
              phase 0    hand? field? -> both: "Hands / Field" prompt, phase = 0x40, yield; one: mode -> desc[+0x18], delegate
              phase 0x40 mode = answer + 1 -> desc[+0x18], phase = 0, delegate NOW (the machine bumps its own phase)
              else       delegate by desc[+0x18]: 1 = hand machine 0x021E7245 (criteria row 0), 2 = field machine 0x021E712D
                         (the record's +08 = O_FIELD).  No OPT stamp here (slot3 re-check hazard): it is at resolution."""
            b = EffectBuilder()
            _hand(b, "r3", "c3")
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.call_addr(SHORTCIRCUIT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "go")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("go")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x7C]")
            b.insn("CMP", "R0, #0x40")
            b.insn("BEQ", "pick")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "deleg")
            b.insn("MOV", "R7, #0x0")
            b.call_addr(OL['HANDANY'], R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "nohand")
            b.insn("MOV", "R7, #0x1")
            b.label("nohand")
            b.call_addr(FIELD_COUNT, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "nofield")
            b.insn("MOV", "R0, #0x2")
            b.insn("ORR", "R7, R0")
            b.label("nofield")
            b.insn("CMP", "R7, #0x3")
            b.insn("BEQ", "ask")
            b.insn("CMP", "R7, #0x0")
            b.insn("BEQ", "abort")
            b.insn("STRH", "R7, [R4, #0x18]")
            b.insn("B", "deleg")
            b.label("ask")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R0, #0x3")
            b.insn("STR", "R0, [SP, #0x8]")
            b.call_addr(PROMPT, R4, DLG_SEND_TITLE, DLG_HANDS, DLG_FIELD, via=R7)
            b.insn("MOV", "R0, #0x40")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("pick")
            b.ldr_const(0, CHOICE)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x18]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.label("deleg")
            b.insn("LDRH", "R0, [R4, #0x18]")
            b.ldr_const(3, HAND_COST)
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "call")
            b.ldr_const(3, FIELD_COST)
            b.label("call")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.insn("BLX", "R3")
            b.insn("B", "ret")
            b.label("abort")
            b.insn("MOV", "R0, #0x0")
            b.insn("SUB", "R0, #0x1")
            b.label("ret")
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("c3")
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDRB", "R0, [R0, #0x2]")
            b.turnlog_post(R0, OLIVER, 1, via=R4)
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            return b


        def o_c2res_stub() -> EffectBuilder:
            """C2 resolver: phase 0x80 = OPT check+stamp (key 0x5E04), then the native hand self-SS 0x02206ABD.  The native
            summons in its 0x80 (`bl 0x02269314 ; movs r0,#0x7f` @0x02206C1E) and ends in its 0x7F with 0 -- BUILD 4 passed
            that 0 through, so the Level phase never ran (in-game test 1, .ml4: Oliver on field, no rider).  BUILD 5: ANY
            native 0 becomes our 0x7E = LOCATE(desc[+0xC]) and, on a monster zone, the Level SET rider {0x1EC1, kind 3, 1}
            (Psi-Reflector's write, one phase after the summon)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R2, R3, R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BEQ", "p80")
            b.insn("CMP", "R0, #0x7E")
            b.insn("BEQ", "p7e")
            b.label("native")
            b.call_addr(HAND_SS_RES, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "out")
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "out")
            b.label("p80")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_query(R0, O_C2KEY, 1, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "zero")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_post(R0, O_C2KEY, 1, via=R5)
            b.call_addr(HAND_SS_RES, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "out")
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "out")
            b.label("p7e")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R1, R0, #0x10")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("CMP", "R1, #0x5")
            b.insn("BGE", "zero")
            b.insn("LSL", "R0, R0, #0x18")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("MOV", "R2, #0x1")
            b.insn("STR", "R2, [SP, #0x0]")
            b.call_addr(RIDER_WRITE, R0, R1, LEVEL_SET_KEY, 3, via=R5)
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.label("out")
            b.insn("POP", "{R2, R3, R4, R5, R6, PC}")
            return b


        def o_handh_stub() -> EffectBuilder:
            """Criteria handler (row, side, param): hand worker 0x0223BFD4 in mode 0x11 (0x0223CB64's send-from-hand) with
            callback HANDCB (r3) and its arg [sp] = 0x1E04 (excluded); r2 = param passes through as in the native."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("SUB", "SP, #0x10")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(0, OLIVER)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("LDR", "R0, [R4, #0x8]")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R0, #0x11")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(HAND_WORKER, R0, R1, R2, OL['HANDCB'] | 1)
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{R4, PC}")
            return b


        def o_handany_stub() -> EffectBuilder:
            """(desc) -> 1 iff some hand index i passes 0x02243FE0(side, cid, i).  BUILD 5: for a HAND criteria row the third
            argument is a hand INDEX, not a row param (in-game test 1 / savestate .ml2: param 0 only ever tested slot 0)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R0, R1")
            b.ldr_const(1, 0xb3c)
            b.insn("MUL", "R0, R1")
            b.ldr_const(1, HAND_COUNT_PTR)
            b.insn("ADD", "R1, R1, R0")
            b.insn("LDR", "R7, [R1, #0x0]")
            b.insn("MOV", "R4, #0x0")
            b.label("loop")
            b.insn("CMP", "R4, R7")
            b.insn("BGE", "none")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(ROW_COUNT, R0, R1, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "yes")
            b.insn("ADD", "R4, #0x1")
            b.insn("B", "loop")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("none")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        OSTUBS = {"HANDANY": o_handany_stub, "SLOT5": o_slot5_stub, "RES": o_res_stub, "FILT": o_filt_stub, "HANDCB": o_handcb_stub, "FIELD": o_field_stub,
                 "COND": o_cond_stub, "COST": o_cost_stub, "C2RES": o_c2res_stub, "HANDH": o_handh_stub,
                 "C3F2": lambda: _opt_gate_stub(OLIVER, VYLON_F2)}


        def _listb(rom):
            mc, sec = O5._arm9_main(rom)
            d = bytearray(sec.data)
            lst = list(struct.unpack_from(f"<{LISTB_COUNT}H", d, LISTB_BASE - 0x02000000))
            return mc, sec, d, lst


        def apply_listb(rom) -> None:
            from otn_enhanced.effects.common import swap_in_list as _swap_in_list
            mc, sec, d, lst = _listb(rom)
            if OLIVER in lst:
                return
            new = _swap_in_list(lst, LISTB_PHANTOM, OLIVER, "O LIST B")
            struct.pack_into(f"<{LISTB_COUNT}H", d, LISTB_BASE - 0x02000000, *new)
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            print(f"O  hand-effect LIST B {LISTB_BASE:#x}: phantom {LISTB_PHANTOM:#06x} -> {OLIVER:#06x}")


        # =================================================================================================
        # card 4: Beaver Warrior 0x0FC1 -> Infernoble Knight Turpin (whole card; notes/infernoble-turpin-findings.md)
        #   C1 equipped monster can be treated as a Tuner (Synchro Material) -> front of Dragunity Partisan's
        #      "equipped with 0x220D" test 0x021A09BC @0x021A1D06 inside the runtime is-Tuner wrapper 0x021A1C7C.
        #   C2 if you control a monster equipped with an Equip Card: SS this card from hand or GY (GY: banish when it leaves).
        #   C3 GY equip.  ONE cls2 record: hand (C2) / GY: "Use which effect?" (C2 SS vs C3 equip) when both legal (user
        #), mode in desc[+0x18] (1 = SS, 2 = equip); +0C resets it to 0 (re-run before +10 only).
        #   OPT stamps at resolution (Maugis lesson).  Hand offer: front of Rulers' ARM9 H4 site 0x02023566 (LIST B full).
        # =================================================================================================
        TURPIN = 0x0FC1
        T_C2KEY = 0x4000 | TURPIN
        GY_SELF_SS, CHAIN_POP = 0x0220731D, 0x021D2965
        PARTISAN_TEST, PARTISAN_SITE, PARTISAN_STOCK = 0x021A09BD, 0x021A1D06, bytes.fromhex("fef759fe")
        H4_SITE = 0x02023566
        DLG_WHICH, DLG_SS, DLG_EQUIP = 0x103, 0x19F, 0x1A1
        for _v in (GY_SELF_SS, CHAIN_POP, PARTISAN_TEST):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        TL = {n: getattr(O5, f"CAVE_IK_T_{n}") for n in ("RES", "FILT", "EQX", "LEGAL", "COND", "COST", "SLOT5", "HANDRES",
                                                          "GYSS", "EQRES", "H4", "TUNER")}
        TRESERVE = {"RES": 0x40, "FILT": 0x30, "EQX": 0x60, "LEGAL": 0x80, "COND": 0x30, "COST": 0x90, "SLOT5": 0x30,
                    "HANDRES": 0x50, "GYSS": 0x70, "EQRES": 0x50, "H4": 0x20, "TUNER": 0x60}
        T_CLS2_PHANTOM = 0x1A8A
        T_CLS2_REC = (TURPIN, 0, TL["RES"] | 1, TL["FILT"] | 1, TL["COND"] | 1, TL["COST"] | 1, TL["SLOT5"] | 1)


        def _post(b: EffectBuilder, key: int, side_from: str = "r4") -> None:
            b.insn("LDRB", f"R0, [{str(side_from).upper()}, #0x2]")
            b.turnlog_post(R0, key, 1, via=R5)


        def _used(b: EffectBuilder, key: int, side_from: str, used: str) -> None:
            b.insn("LDRB", f"R0, [{str(side_from).upper()}, #0x2]")
            b.turnlog_query(R0, key, 1, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", f"{used}")


        def t_res_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xE")
            b.insn("BEQ", "gy")
            b.ldr_const(3, TL['HANDRES'] | 1)
            b.insn("BX", "R3")
            b.label("gy")
            b.insn("LDRH", "R3, [R0, #0x18]")
            b.insn("CMP", "R3, #0x1")
            b.insn("BNE", "eq")
            b.ldr_const(3, TL['GYSS'] | 1)
            b.insn("BX", "R3")
            b.label("eq")
            b.ldr_const(3, TL['EQRES'] | 1)
            b.insn("BX", "R3")
            return b


        def t_filt_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xE")
            b.insn("BNE", "zero")
            b.insn("LDRH", "R3, [R0, #0x18]")
            b.insn("CMP", "R3, #0x1")
            b.insn("BEQ", "zero")
            b.ldr_const(3, VYLON_FILTER)
            b.insn("BX", "R3")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b


        def t_slot5_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xE")
            b.insn("BNE", "one")
            b.insn("LDRH", "R3, [R0, #0x18]")
            b.insn("CMP", "R3, #0x2")
            b.insn("BNE", "one")
            b.ldr_const(3, VYLON_SLOT5)
            b.insn("BX", "R3")
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            return b


        def t_eqx_stub() -> EffectBuilder:
            """(desc) -> 1 iff some S/T card (either side, zones 5..9) is equipped (0x021A0DF8) to a monster zone of desc[+2]."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("LDRB", "R6, [R0, #0x2]")
            b.insn("MOV", "R4, #0x0")
            b.label("sl")
            b.insn("MOV", "R5, #0x5")
            b.label("zl")
            b.call_addr(EQUIP_TARGET_OF, R4, R5, via=R3)
            b.insn("LSL", "R1, R0, #0x18")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("CMP", "R1, R6")
            b.insn("BNE", "nx")
            b.insn("LSL", "R1, R0, #0x10")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("CMP", "R1, #0x4")
            b.insn("BGT", "nx")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("nx")
            b.insn("ADD", "R5, #0x1")
            b.insn("CMP", "R5, #0x9")
            b.insn("BLE", "zl")
            b.insn("ADD", "R4, #0x1")
            b.insn("CMP", "R4, #0x1")
            b.insn("BLE", "sl")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def t_legal_stub() -> EffectBuilder:
            """(desc) -> bit0 = C2 SS legal (OPT 0x4FC1 clear, free Monster Zone, a monster of yours equipped),
            bit1 = C3 equip legal (GY only: OPT 0x0FC1 clear, Vylon f1 (still in GY + free S/T), >= 1 +08 target)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("MOV", "R6, #0x0")
            _used(b, T_C2KEY, "r4", "c3")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_MZ, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "c3")
            b.call_addr(TL['EQX'], R4, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "c3")
            b.insn("MOV", "R6, #0x1")
            b.label("c3")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xE")
            b.insn("BNE", "done")
            _used(b, TURPIN, "r4", "done")
            b.call_addr(VYLON_F1, R4, 0, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "done")
            b.call_addr(FIELD_COUNT, R4, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "done")
            b.insn("MOV", "R0, #0x2")
            b.insn("ORR", "R6, R0")
            b.label("done")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def t_cond_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDRB", "R1, [R0, #0x3]")
            b.insn("CMP", "R1, #0xE")
            b.insn("BNE", "go")
            b.insn("MOV", "R1, #0x0")
            b.insn("STRH", "R1, [R0, #0x18]")
            b.label("go")
            b.call_addr(TL['LEGAL'], via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "z")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, PC}")
            b.label("z")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b


        def t_cost_stub() -> EffectBuilder:
            """Hand: no cost -> 1.  GY: LEGAL both -> "Use which effect?" (SS / Equip), phase 0x40, yield; answer -> mode;
            one -> mode; none -> -1.  Return 1 = done (the driver zeroes the cost phase before +14)."""
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xE")
            b.insn("BEQ", "gy")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("gy")
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x7C]")
            b.insn("CMP", "R0, #0x40")
            b.insn("BEQ", "pick")
            b.call_addr(TL['LEGAL'], R4, via=R3)
            b.insn("ADD", "R7, R0, #0x0")
            b.insn("CMP", "R7, #0x3")
            b.insn("BEQ", "ask")
            b.insn("CMP", "R7, #0x0")
            b.insn("BEQ", "abort")
            b.insn("STRH", "R7, [R4, #0x18]")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("ask")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R0, #0x3")
            b.insn("STR", "R0, [SP, #0x8]")
            b.call_addr(PROMPT, R4, DLG_WHICH, DLG_SS, DLG_EQUIP, via=R7)
            b.insn("MOV", "R0, #0x40")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("pick")
            b.ldr_const(0, CHOICE)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x18]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("abort")
            b.insn("MOV", "R0, #0x0")
            b.insn("SUB", "R0, #0x1")
            b.label("ret")
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def t_handres_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, T_C2KEY, "r4", "zero")
            _post(b, T_C2KEY)
            b.label("nat")
            b.call_addr(HAND_SS_RES, R4, via=R3)
            b.insn("POP", "{R4, R5, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def t_gyss_stub() -> EffectBuilder:
            """Dragunity Remus C3a's in-game-confirmed GY self-SS resolver + our OPT and arm byte."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BEQ", "p80")
            b.insn("CMP", "R0, #0x7F")
            b.insn("BEQ", "p7f")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("p80")
            _used(b, T_C2KEY, "r4", "zero")
            _post(b, T_C2KEY)
            b.call_addr(CHAIN_PUSH, via=R3)
            b.ldr_const(0, O5.CAVE_IK_T_ARM)
            b.insn("MOV", "R1, #0x1")
            b.insn("STRB", "R1, [R0, #0x0]")
            b.call_addr(GY_SELF_SS, R4, R6, via=R3)
            b.insn("MOV", "R0, #0x7F")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("p7f")
            b.call_addr(CHAIN_POP, via=R3)
            b.insn("MOV", "R0, #0x64")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def t_eqres_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, TURPIN, "r4", "zero")
            _post(b, TURPIN)
            b.label("nat")
            b.call_addr(EQUIP_FROM_GY_RES, R4, via=R3)
            b.insn("POP", "{R4, R5, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def t_h4_stub() -> EffectBuilder:
            """ARM9 0x02023566 BL (r0 = cid, r1 = LIST B, r2 = 0x24; caller then `pop {r4,pc}`): Turpin -> 1, else tail-jump
            to Rulers' CAVE3_RUL_H4 with every register and lr intact.  Ricciardetto (C1 from the hand) joins the same arm."""
            from otn_enhanced.effects import cave3 as _c3
            b = EffectBuilder()
            b.ldr_const(3, TURPIN)
            b.insn("CMP", "R0, R3")
            b.insn("BEQ", "yes")
            b.ldr_const(3, RICC)
            b.insn("CMP", "R0, R3")
            b.insn("BNE", "prev")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("prev")
            b.ldr_const(3, _c3.CAVE3_RUL_H4 | 1)
            b.insn("BX", "R3")
            return b


        def t_tuner_stub() -> EffectBuilder:
            """BL over Partisan's `bl 0x021A09BC` @0x021A1D06 inside the is-Tuner wrapper (r5 = side, r4 = idx, both
            callee-saved there): the native answer, else an S/T card of cid 0x0FC1 equipped to (r5, r4) (Ogier's scan)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.call_addr(PARTISAN_TEST, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "out")
            b.insn("LDR", "R6, [SP, #0x0]")
            b.insn("LDR", "R7, [SP, #0x4]")
            b.insn("LSL", "R6, R6, #0x8")
            b.insn("ORR", "R6, R7")
            b.insn("MOV", "R4, #0x0")
            b.label("sl")
            b.insn("MOV", "R5, #0x5")
            b.label("zl")
            b.call_addr(CARD_CID_AT, R4, R5, via=R2)
            b.ldr_const(1, TURPIN)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "nx")
            b.call_addr(EQUIP_TARGET_OF, R4, R5, via=R2)
            b.insn("CMP", "R0, R6")
            b.insn("BEQ", "yes")
            b.label("nx")
            b.insn("ADD", "R5, #0x1")
            b.insn("CMP", "R5, #0x9")
            b.insn("BLE", "zl")
            b.insn("ADD", "R4, #0x1")
            b.insn("CMP", "R4, #0x1")
            b.insn("BLE", "sl")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "out")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.label("out")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def rider_arms() -> tuple:
            from otn_enhanced.effects import summon_rider_hook as rh
            return rh.ARMS if any(a[0] == TURPIN for a in rh.ARMS) else rh.ARMS + ((TURPIN, "tp", O5.CAVE_IK_T_ARM,
                               "Infernoble Knight Turpin: C2's GY self-SS resolver sets the byte at phase 0x80 (0x0FC1 reaches "
                               "the default leaf, scratch/summon_event_sim walk 2026-10-20) -- LOCAL until shipped"),)


        def latch_arms() -> tuple:
            from otn_enhanced.effects import summon_rider_hook as rh
            return rh.LATCH_ARMS            # unchanged: Renaud's latch is its OWN front (the 0x50 prefix home is full)


        def r_latch_stub() -> EffectBuilder:
            """Front at the summon-event default leaf (RIDER_SITE BL), ahead of the shared latch prefix: one latch arm
            (summon_rider_hook.latch_stub's exact body) for Renaud -- byte CAVE_IK_R_ARM set AND the event's SOURCE cid
            [r4+0x12] == 0x1E05 -> consume, attach {0x1E40 (Lightwave Tuning's 'treated as a Tuner'), kind 3} to the summoned
            card's (side, slot), replay the displaced pair, return; else tail-jump to CAVE_RIDERLATCH with lr intact."""
            from otn_enhanced.effects import summon_rider_hook as rh
            return _latch_stub(O5.CAVE_IK_R_ARM, RENAUD, O5.CAVE_RIDERLATCH)


        def _latch_stub(armbyte: int, cid: int, nxt: int) -> EffectBuilder:
            from otn_enhanced.effects import summon_rider_hook as rh
            b = EffectBuilder()
            b.ldr_const(0, armbyte)
            b.insn("LDRB", "R1, [R0, #0x0]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "shared")
            b.insn("LDRH", f"R1, [R4, #0x{rh.RIDER_EVENT_CID_OFF:X}]")
            b.ldr_const(2, cid)
            b.insn("CMP", "R1, R2")
            b.insn("BNE", "shared")
            b.insn("MOV", "R1, #0x0")
            b.insn("STRB", "R1, [R0, #0x0]")
            b.insn("PUSH", "{R4, R5, R7, LR}")
            b.insn("MOV", "R3, #0x0")
            b.insn("PUSH", "{R3}")
            b.insn("LDRH", f"R0, [R4, #0x{rh.RIDER_EVENT_SIDE_OFF:X}]")
            b.insn("LDRH", f"R1, [R4, #0x{rh.RIDER_EVENT_SLOT_OFF:X}]")
            b.ldr_const(2, 0x1e40)
            b.insn("MOV", f"R3, #0x{rh.RIDER_KIND:X}")
            b.ldr_const(7, rh.RIDER_ATTACH)
            b.insn("BLX", "R7")
            b.insn("POP", "{R3}")
            b.insn("LDRH", "R0, [R4, #0xE]")
            b.ldr_const(6, rh.RIDER_R6_LITERAL)
            b.insn("POP", "{R4, R5, R7, PC}")
            b.label("shared")
            b.ldr_const(0, nxt | 1)
            b.insn("BX", "R0")
            return b


        def apply_riders(rom, ov: bytearray) -> None:
            """Shared rider hook stub with Turpin's LOCAL arm; the rider site BL -> Renaud's front -> the shared prefix."""
            from otn_enhanced.effects import summon_rider_hook as rh
            hook = rh.stub(O5.CAVE_RIDERHOOK, rider_arms())
            effect_verify.assert_thumb1_only(hook, O5.CAVE_RIDERHOOK)
            _put5(rom, O5.CAVE_RIDERHOOK, rh.RESERVE, hook)
            o = rh.RIDER_SITE - RAM_BASE
            if bytes(ov[o:o + 4]) not in (_bl(rh.RIDER_SITE, RL["LATCH"]), _bl(rh.RIDER_SITE, RCL["LATCH"])):
                rh.apply(ov, quiet=True, latch_arms=latch_arms())
            ov[o:o + 4] = _bl(rh.RIDER_SITE, RCL["LATCH"])          # Ricciardetto's front -> Renaud's -> the shared prefix
            for b in (O5.CAVE_IK_T_ARM, O5.CAVE_IK_R_ARM, O5.CAVE_IK_RC_ARM):
                _put5(rom, b, 0x10, bytes(1))


        def apply_turpin(rom, ov: bytearray) -> None:
            apply_riders(rom, ov)
            o = PARTISAN_SITE - RAM_BASE
            assert bytes(ov[o:o + 4]) in (PARTISAN_STOCK, _bl(PARTISAN_SITE, TL["TUNER"])), "T Partisan site not stock"
            ov[o:o + 4] = _bl(PARTISAN_SITE, TL["TUNER"])
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, T_CLS2_REC, T_CLS2_PHANTOM, "T cls2 (C2 hand/GY + C3 GY)")
            from otn_enhanced.effects import cave3 as _c3
            mc, sec = O5._arm9_main(rom)
            d = bytearray(sec.data)
            a = H4_SITE - 0x02000000
            assert bytes(d[a:a + 4]) in (_bl(H4_SITE, _c3.CAVE3_RUL_H4), _bl(H4_SITE, TL["H4"])), \
                f"T ARM9 H4 site {H4_SITE:#x} is not Dragon Rulers' BL"
            d[a:a + 4] = _bl(H4_SITE, TL["H4"])
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            print(f"T  rider arm byte, Partisan front @{PARTISAN_SITE:#x}, ARM9 H4 front @{H4_SITE:#x}, cls2 record")


        def verify_turpin(rom, ov, check) -> None:
            from otn_enhanced.effects import summon_rider_hook as rh
            from otn_enhanced.effects import cave3 as _c3
            blob = rh.stub(O5.CAVE_RIDERHOOK, rider_arms())
            check(O5.read_cave(rom, O5.CAVE_RIDERHOOK, len(blob)) == blob, "T shared rider stub carries the 0x0FC1 arm")
            pre = rh.latch_stub(O5.CAVE_RIDERLATCH, latch_arms())
            check(O5.read_cave(rom, O5.CAVE_RIDERLATCH, len(pre)) == pre, "R shared latch prefix unchanged (Brilliant Fusion)")
            check(bytes(ov[rh.RIDER_SITE - RAM_BASE:rh.RIDER_SITE - RAM_BASE + 4]) in (_bl(rh.RIDER_SITE, RCL["LATCH"]),
                                                                                  _bl(rh.RIDER_SITE, COL["LATCH"])),
                  f"RC rider site @{rh.RIDER_SITE:#x} -> Ricciardetto's latch front (-> Renaud's -> CAVE_RIDERLATCH)")
            check(bytes(ov[PARTISAN_SITE - RAM_BASE:PARTISAN_SITE - RAM_BASE + 4]) == _bl(PARTISAN_SITE, TL["TUNER"]),
                  f"T bl @{PARTISAN_SITE:#x} -> Tuner front")
            mc, sec = O5._arm9_main(rom)
            a = H4_SITE - 0x02000000
            check(bytes(sec.data[a:a + 4]) in {_bl(H4_SITE, f) for f in O5.dc_ahead_of(ROL["H4"])},
                  f"T ARM9 bl @{H4_SITE:#x} -> H4 front (-> Rulers; disguise_copycat's front may sit ahead)")
            rows = _rows(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT)
            check([r for r in rows if r[0] == TURPIN] == [T_CLS2_REC], "T cls2: exactly one 0x0fc1 row")
            check([r[0] for r in rows] == sorted(r[0] for r in rows), "T cls2: sorted")


        # =================================================================================================
        # card 5: Water Spirit 0x1E05 -> Infernoble Knight - Renaud (whole card; notes/infernoble-renaud-findings.md)
        #   C1 hand-SS procedure "if you control a FIRE Warrior", once per turn THIS WAY: tg_table hand-SS registry (R_SSCOND)
        #      + ss_commit_hook row {0x1E05, kind 1} (stamped on a Special Summon from the hand, Unknown Synchron's recipe).
        #   C2 "If Summoned this way, treat this card as a Tuner": R_SSCOND arms CAVE_IK_R_ARM; the rider LATCH arm attaches
        #      Lightwave Tuning's key 0x1E40 when a summon's SOURCE cid is 0x1E05 (ASSUMED: a procedure summon's source = self).
        #   C3 "If this card is Special Summoned: You can target 1 FIRE Warrior or Equip Spell of yours in GY/banished, except
        #      Renaud; add it to your hand" (OPT): c9_trigger_hook + cls1 {R_RES -> 0x02208181, 0, R_COND, "You can" 0x021E51E5,
        #      target step 0x02235605} -- the add resolver Magical Stone Excavation (GY) AND Light of Redemption (banished) share.
        # =================================================================================================
        RENAUD = 0x1E05
        R_C3KEY = 0x4000 | RENAUD
        CAN_SS, FACE_UP, ADD_TARGET_RES, TARGET_STEP = 0x021B9ECD, 0x021A32B5, 0x02208181, 0x02235605
        for _v in (CAN_SS, FACE_UP, ADD_TARGET_RES, TARGET_STEP):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        RL = {n: getattr(O5, f"CAVE_IK_R_{n}") for n in ("SSCOND", "COND", "RES", "C3H", "LATCH")}
        RRESERVE = {"SSCOND": 0x90, "COND": 0x50, "RES": 0x50, "C3H": 0x40, "LATCH": 0x50}
        R_CLS1_PHANTOM, R_CRIT_PHANTOM = 0x0E5F, 0x0E68
        R_CLS1_REC = (RENAUD, 0, RL["RES"] | 1, 0, RL["COND"] | 1, TAG_YOU_CAN, TARGET_STEP)
        R_CRIT_REC = (RENAUD, 0xFFFF, RL["C3H"] | 1, 0x00000000)


        def r_sscond_stub() -> EffectBuilder:
            """Hand-SS offer (r0 = side): can SS, a free Monster Zone, procedure OPT (side, 0xB, 0x1E05, 1) clear, and a
            face-up FIRE Warrior in zones 0..4 of that side.  On yes, arm the Tuner latch byte."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(CAN_SS, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(FREE_MZ, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("ADD", "R0, R4, #0x0")
            b.turnlog_query(R0, RENAUD, 1, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            b.insn("MOV", "R5, #0x0")
            b.label("zl")
            b.insn("CMP", "R5, #0x4")
            b.insn("BGT", "no")
            b.call_addr(FACE_UP, R4, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "nx")
            b.call_addr(CARD_CID_AT, R4, R5, via=R3)
            b.insn("ADD", "R6, R0, #0x0")
            b.call("get_race", via=R3)
            b.insn("CMP", f"R0, #0x{RACE_WARRIOR:X}")
            b.insn("BNE", "nx")
            b.call_addr(GET_ATTR, R6, via=R3)
            b.insn("CMP", f"R0, #0x{ATTR_FIRE:X}")
            b.insn("BNE", "nx")
            b.ldr_const(0, O5.CAVE_IK_R_ARM)
            b.insn("MOV", "R1, #0x1")
            b.insn("STRB", "R1, [R0, #0x0]")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("nx")
            b.insn("ADD", "R5, #0x1")
            b.insn("B", "zl")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def r_cond_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            _used(b, R_C3KEY, "r4", "no")
            b.call_addr(ROW_PARAM, R4, via=R5)
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(ROW_COUNT, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def r_res_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, R_C3KEY, "r4", "zero")
            _post(b, R_C3KEY)
            b.label("nat")
            b.call_addr(ADD_TARGET_RES, R4, via=R3)
            b.insn("POP", "{R4, R5, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def r_c3h_stub() -> EffectBuilder:
            """Criteria handler (row, side, param): Maugis's GY + banished workers, with Oliver's callback (FIRE Warrior or
            Equip Spell, cid != [sp+4] = 0x1E05)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.insn("LDR", "R0, [R5, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(GY_WORKER, R0, R1, OL['HANDCB'] | 1, RENAUD)
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDR", "R0, [R5, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0xC")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(BAN_WORKER, R0, R1, OL['HANDCB'] | 1, RENAUD)
            b.insn("ADD", "R0, R4, R0")
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        RSTUBS = {"SSCOND": r_sscond_stub, "COND": r_cond_stub, "RES": r_res_stub, "C3H": r_c3h_stub, "LATCH": r_latch_stub}


        def apply_renaud(rom, ov: bytearray) -> None:
            from otn_enhanced.effects import c9_trigger_hook as c9, ss_commit_hook as sch, tg_table
            tg_table.register_tg_handss(rom, ov, RENAUD, RL["SSCOND"])
            sch.register(rom, ov, RENAUD, 1)
            c9.install(rom)
            c9.apply(ov)
            insert_row(ov, CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, R_CLS1_REC, R_CLS1_PHANTOM, "R C3 cls1")
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, R_CRIT_REC, R_CRIT_PHANTOM, "R C3 criteria row")


        def verify_renaud(rom, ov, check) -> None:
            from otn_enhanced.effects import c9_trigger_hook as c9, ss_commit_hook as sch, tg_table
            check(tg_table.tg_handss_ok(rom, ov, RENAUD), "R hand-SS procedure registered (tg_table)")
            check(sch.ok(rom, ov, RENAUD, 1), "R ss_commit_hook row {0x1E05, kind 1}")
            c9.verify(ov, check, rom=rom)
            for label, base, count, stride, fmt, rec in (("cls1", CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, R_CLS1_REC),
                                                         ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, R_CRIT_REC)):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == RENAUD] == [rec], f"R {label}: exactly one 0x1e05 row")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"R {label}: sorted")


        # =================================================================================================
        # card 6: Tiger Axe 0x0FE6 -> Infernoble Knight Ricciardetto (whole card; notes/infernoble-ricciardetto-findings.md)
        #   C1 (hand OR GY ignition) cost banish this card; SS 1 Lv<=4 FIRE Warrior from your hand AS A TUNER:
        #      cls2 {RC_RES -> Stygian Street Patrol's hand-SS resolver 0x0220667D, 0, RC_COND, RC_COST, 0}; criteria rel 0
        #      {0x0223CA51 hand handler, 0x7C900002}; GY offer = gy_vrow_hook row, hand offer = Turpin's ARM9 H4 front;
        #      cost GY = Stygian's 0x021E5709, hand = Dragon Rulers' HAND_INDEX + HAND_BANISH; Tuner = RC_ARM byte + a rider
        #      LATCH front (source cid 0x0FE6, proven to reach the default leaf) attaching Lightwave Tuning's 0x1E40.
        #   C2 (NS or SS trigger, "You can") target 1 Lv<=4 FIRE Warrior in your GY except Ricciardetto; SS it; Warrior-only
        #      SS lock: c79_trigger_hook arm + cls1 {RC_C2RES -> Junk Synchron's 0x02207191, 0, RC_C2CND -> 0x021F03B5,
        #      "You can" 0x021E51E5, 0x02235605}; criteria rel 1 {RC_C2H (GY worker flags 8 + Ogier's C2CB excl 0x0FE6),
        #      0x7C910002} reached via a criteria_row_hook arm (cls1 desc -> rel 1); lock = front at 0x021BA368 ahead of
        #      Obedience Schooled's LOCK: turn-log {0xB, 0x4FE6} && race != Warrior -> deny.
        #   C3 one shared turn-log key (side, 0xB, 0x0FE6, kind 1), checked in both +0C, stamped at resolution 0x80.
        # =================================================================================================
        RICC = 0x0FE6
        RC_LOCKKEY = 0x4000 | RICC
        HAND_SS_ANY, STYGIAN_COST, STYGIAN_F1, STYGIAN_F2 = 0x0220667D, 0x021E5709, 0x021F047D, 0x021F0A11
        HAND_COUNT_DESC, CAN_BANISH, HAND_INDEX, HAND_BANISH = 0x0224401D, 0x021BAC01, 0x021A25A1, 0x021C6E99
        CHAIN_POP_C = 0x021D2965
        REVIVE_RES, JUNK_COND, HAND_SS_H = 0x02207191, 0x021F03B5, 0x0223CA51
        for _v in (HAND_SS_ANY, STYGIAN_COST, STYGIAN_F1, STYGIAN_F2, HAND_COUNT_DESC, CAN_BANISH, HAND_INDEX, HAND_BANISH,
                   CHAIN_POP_C, REVIVE_RES, JUNK_COND, HAND_SS_H):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        RCL = {n: getattr(O5, f"CAVE_IK_RC_{n}") for n in ("COND", "COST", "RES", "C2CND", "C2RES", "C2H", "LOCK", "LATCH",
                                                            "ROW")}
        RCRESERVE = {"COND": 0x70, "COST": 0x50, "RES": 0x60, "C2CND": 0x30, "C2RES": 0x70, "C2H": 0x30, "LOCK": 0x40,
                     "LATCH": 0x50, "ROW": 0x40}
        RC_CLS2_PHANTOM, RC_CLS1_PHANTOM, RC_CRIT_PHANTOMS = 0x1B8F, 0x0E61, (0x0E42, 0x0E4B)
        RC_CLS2_REC = (RICC, 0, RCL["RES"] | 1, 0, RCL["COND"] | 1, RCL["COST"] | 1, 0)
        RC_CLS1_REC = (RICC, 0, RCL["C2RES"] | 1, 0, RCL["C2CND"] | 1, TAG_YOU_CAN, TARGET_STEP)
        RC_CRIT_RECS = ((RICC, 0xFFFF, HAND_SS_H, 0x7C900002),          # rel 0: C1 hand Lv<=4 FIRE Warrior
                        (RICC, 0xFFFF, RCL["C2H"] | 1, 0x7C910002))     # rel 1: C2 GY Lv<=4 FIRE Warrior, excl 0x0FE6


        def rc_row_stub() -> EffectBuilder:
            """FRONT at the criteria row hook 0x02243BEC (the shared stub's prelude `beq native` is at its Thumb-1 range
            limit, so one more arm cannot be appended): row cid r5 == 0x0FE6 AND acting descriptor cid == 0x0FE6 AND
            desc[+5] == 1 (cls1 = C2) -> r4 = 1, the common tail; else tail-jump to the unchanged shared stub.
            r0/r1/r3 are scratch at the site (criteria_row_hook REGISTER CONTRACT); r4..r7 untouched on the shared path."""
            from otn_enhanced.effects import criteria_row_hook as crh
            b = EffectBuilder()
            b.ldr_const(1, RICC)
            b.insn("CMP", "R5, R1")
            b.insn("BNE", "shared")
            b.ldr_const(3, crh.ACTING_DESC)
            b.insn("LDR", "R3, [R3, #0x50]")
            b.insn("CMP", "R3, #0x0")
            b.insn("BEQ", "shared")
            b.insn("LDRH", "R0, [R3, #0x0]")
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "shared")
            b.insn("LDRB", "R0, [R3, #0x5]")
            b.insn("CMP", "R0, #0x1")
            b.insn("BNE", "shared")
            b.insn("MOV", "R4, #0x1")
            b.ldr_const(3, crh.ROWHOOK_TAIL | 1)
            b.insn("BX", "R3")
            b.label("shared")
            b.ldr_const(3, O5.CAVE_ROWHOOK | 1)
            b.insn("BX", "R3")
            return b


        def rc_cond_stub() -> EffectBuilder:
            """cls2 +0C (desc, arg): OPT clear; Stygian's f1 (free zone, can SS, >= 1 hand candidate); GY: Stygian's f2 (in
            GY, can banish) -> its value; hand (0x0B): >= 2 hand candidates (this card counts itself) and can banish -> 2."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            _used(b, RICC, "r4", "no")
            b.call_addr(STYGIAN_F1, R4, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xE")
            b.insn("BNE", "hand")
            b.call_addr(STYGIAN_F2, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("hand")
            b.insn("CMP", "R0, #0xB")
            b.insn("BNE", "no")
            b.call_addr(HAND_COUNT_DESC, R4, via=R3)
            b.insn("CMP", "R0, #0x2")
            b.insn("BLT", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(CAN_BANISH, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def rc_cost_stub() -> EffectBuilder:
            """cls2 +10: GY -> Stygian's banish-self 0x021E5709; hand -> banish this card (Dragon Rulers' hand banish) -> 1."""
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xE")
            b.insn("BNE", "hand")
            b.ldr_const(3, STYGIAN_COST)
            b.insn("BX", "R3")
            b.label("hand")
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0xC]")
            b.call_addr(HAND_INDEX, via=R3)
            b.insn("MOV", "R5, #0x1")
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "fail")
            b.insn("ADD", "R1, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(HAND_BANISH, via=R3)
            b.insn("B", "done")
            b.label("fail")
            b.insn("MOV", "R5, #0x0")
            b.insn("SUB", "R5, #0x1")
            b.label("done")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def rc_res_stub() -> EffectBuilder:
            """cls2 +04: phase 0x80 -> OPT check + stamp, arm the Tuner latch byte; then the native hand-SS resolver."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, RICC, "r4", "zero")
            _post(b, RICC)
            b.ldr_const(0, O5.CAVE_IK_RC_ARM)
            b.insn("MOV", "R1, #0x1")
            b.insn("STRB", "R1, [R0, #0x0]")
            b.label("nat")
            b.call_addr(HAND_SS_ANY, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def rc_c2cnd_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            _used(b, RICC, "r4", "no")
            b.call_addr(JUNK_COND, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def rc_c2res_stub() -> EffectBuilder:
            """cls1 +04: phase 0x80 -> OPT check + stamp, post the Warrior-lock node, clear C1's latch byte; then revive."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, RICC, "r4", "zero")
            _post(b, RICC)
            _post(b, RC_LOCKKEY)
            b.ldr_const(0, O5.CAVE_IK_RC_ARM)
            b.insn("MOV", "R1, #0x0")
            b.insn("STRB", "R1, [R0, #0x0]")
            b.label("nat")
            b.call_addr(REVIVE_RES, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def rc_c2h_stub() -> EffectBuilder:
            """Criteria handler: Junk Synchron's 0x0223C9D1 (GY worker, flags 8) + Ogier's C2CB rejecting cid 0x0FE6."""
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2, R3, LR}")
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDR", "R0, [R2, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x8")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("LDRH", "R1, [R2, #0x0]")
            b.call_addr(GY_WORKER, R0, R1, L['C2CB'] | 1, RICC)
            b.insn("POP", "{R1, R2, R3, PC}")
            return b


        def rc_lock_stub() -> EffectBuilder:
            """Replaces `bl` @0x021BA368 inside the SS gate 0x021BA258 (caller r5 = cid, r7 = side), ahead of Obedience
            Schooled's LOCK: that verdict first; a pass becomes a deny when side r7's turn log holds {0xB, 0x4FE6, 1} and
            the cid is not a Warrior (race 15)."""
            from otn_enhanced.cards import obedience_schooled as _os
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.ldr_const(3, _os.LOCK | 1)
            b.insn("BLX", "R3")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "out")
            b.insn("ADD", "R0, R7, #0x0")
            b.turnlog_query(R0, RC_LOCKKEY, 1, via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "allow")
            b.call("get_race", R5, via=R3)
            b.insn("CMP", f"R0, #0x{RACE_WARRIOR:X}")
            b.insn("BEQ", "allow")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            b.label("allow")
            b.insn("MOV", "R0, #0x1")
            b.label("out")
            b.insn("POP", "{R4, PC}")
            return b


        RCSTUBS = {"COND": rc_cond_stub, "COST": rc_cost_stub, "RES": rc_res_stub, "C2CND": rc_c2cnd_stub, "C2RES": rc_c2res_stub,
                  "C2H": rc_c2h_stub, "LOCK": rc_lock_stub, "ROW": rc_row_stub,
                  "LATCH": lambda: _latch_stub(O5.CAVE_IK_RC_ARM, RICC, RL["LATCH"])}
        LOCK_SITE = 0x021BA368


        def _append_rows(ov: bytearray, recs: tuple, phantoms: tuple) -> None:
            """Criteria rows rel 0, rel 1, ... for ONE cid, adjacent and in order (the row resolver adds r4 to the LEFTMOST);
            each drops one phantom row.  Idempotent."""
            off = CRIT_BASE - RAM_BASE
            rows = [struct.unpack_from(CRIT_FMT, ov, off + i * 12) for i in range(CRIT_COUNT)]
            if [r for r in rows if r[0] == recs[0][0]] == list(recs):
                return
            assert not any(r[0] == recs[0][0] for r in rows), f"RC criteria: {recs[0][0]:#x} already has other rows"
            for ph in phantoms:
                assert [r[0] for r in rows].count(ph) == 1, f"RC criteria phantom {ph:#x} must own exactly one row"
                rows.pop([r[0] for r in rows].index(ph))
            pos = sum(1 for r in rows if r[0] < recs[0][0])
            rows[pos:pos] = list(recs)
            for i, r in enumerate(rows):
                struct.pack_into(CRIT_FMT, ov, off + i * 12, *r)
            keys = [r[0] for r in rows]
            assert len(rows) == CRIT_COUNT and keys == sorted(keys), "RC criteria unsorted / resized"
            print(f"RC criteria: dropped {', '.join(f'{p:#x}' for p in phantoms)}, inserted rel 0..{len(recs) - 1} @{pos}")


        def apply_ricc(rom, ov: bytearray) -> None:
            from otn_enhanced.cards import obedience_schooled as _os
            o = LOCK_SITE - RAM_BASE
            assert _bl_target(ov, LOCK_SITE) in (_os.LOCK, RCL["LOCK"]), \
                f"RC SS-gate bl @{LOCK_SITE:#x} -> {_bl_target(ov, LOCK_SITE):#x}, expected Obedience Schooled's LOCK"
            ov[o:o + 4] = _bl(LOCK_SITE, RCL["LOCK"])
            from otn_enhanced.effects import criteria_row_hook as crh
            o = crh.ROWHOOK_SITE - RAM_BASE
            assert bytes(ov[o:o + 4]) in (_bl(crh.ROWHOOK_SITE, O5.CAVE_ROWHOOK), _bl(crh.ROWHOOK_SITE, RCL["ROW"])),         f"RC criteria row hook site {crh.ROWHOOK_SITE:#x} is not the shared stub's BL"
            ov[o:o + 4] = _bl(crh.ROWHOOK_SITE, RCL["ROW"])
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, RC_CLS2_REC, RC_CLS2_PHANTOM, "RC C1 cls2")
            insert_row(ov, CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, RC_CLS1_REC, RC_CLS1_PHANTOM, "RC C2 cls1")
            _append_rows(ov, RC_CRIT_RECS, RC_CRIT_PHANTOMS)


        def verify_ricc(rom, ov, check) -> None:
            check(_bl_target(ov, LOCK_SITE) in (RCL["LOCK"], O5.CAVE_IK_HO_LOCK),
                  f"RC bl @{LOCK_SITE:#x} -> Warrior-lock front (or Horn of Olifant's front ahead of it)")
            from otn_enhanced.effects import criteria_row_hook as crh
            check(_bl_target(ov, crh.ROWHOOK_SITE) in (RCL["ROW"], O5.CAVE_IK_JO_ROW, O5.CAVE_IK_DU_ROW),
                  f"RC bl @{crh.ROWHOOK_SITE:#x} -> row front (or Joyeuse's front ahead of it)")
            blob = crh.stub(O5.CAVE_ROWHOOK)
            check(O5.read_cave(rom, O5.CAVE_ROWHOOK, len(blob)) == blob, "RC shared criteria-row stub unchanged")
            for label, base, count, stride, fmt, recs in (("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, [RC_CLS2_REC]),
                                                          ("cls1", CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, [RC_CLS1_REC]),
                                                          ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT,
                                                           list(RC_CRIT_RECS))):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == RICC] == recs, f"RC {label}: exactly the 0x0fe6 row(s), in order")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"RC {label}: sorted")


        # =================================================================================================
        # card 7: Killer Needle 0x0FDB -> Infernoble Knight - Roland (whole card; notes/infernoble-roland-findings.md)
        #   ONE cls2 record, switched on desc[+3] / desc[+4]:
        #   C1 HAND (0x0B), Quick Effect: Vylon's equip-THIS-card resolver 0x02210961 (zone-agnostic: it checks the card is
        #      still in desc[+3] and moves it with 0x021C7484, whose r1 = the card's CURRENT zone), Vylon filter / slot5,
        #      +0C = OPT 0x4FDB + Vylon f1 (free S/T zone) + f2 (>= 1 legal target); EQFILT arm: any monster you control;
        #      +500 ATK = equip grant table 0x0226DFB0 row {0x0FDB, 500, 0}; hand offer = LIST B via the ARM9 H4 front
        #      (Effect Veiler / Honest are LIST B too); Damage Step excluded by the engine's offer gate (KB).
        #   C2 GY: the End-Phase walker 0x02254120 (registry row {0x02254221, 0x0FDB}, Fox Fire's) needs a turn-log node
        #      {key 0x0FDB, kind 1, ref} whose card is in the GY NOW.  Roland posts it itself: the sent-to-GY event
        #      (desc[+4] > 6; reached via an ov3 front on the 0x021D13C2 node + a leave-mask row) makes +0C post the node
        #      and return 0.  The walker's event has desc[+4] == 6 (word 0x0C400000, decoded from 0x021D3168) -> +0C =
        #      OPT 0x2FDB + >= 1 Deck candidate -> resolver 0x02207EF5 (T.G. Striker's End-Phase Deck search, same
        #      dispatch leaf 0x02207FCC) with criteria {Deck worker + Oliver's HANDCB excl 0x0FDB}; "You can" = timing arm.
        # =================================================================================================
        ROLAND = 0x0FDB
        RO_C1KEY, RO_C2KEY = 0x4000 | ROLAND, 0x2000 | ROLAND     # NOT 0x0FDB: that key is the walker's sent-this-turn node
        ADD_FROM_DECK_RES, ACCEPT_GY = 0x02207EF5, 0x021D1939
        ROW_PARAM_C, ROW_COUNT_C = 0x02234E79, 0x02243FE1
        for _v in (ADD_FROM_DECK_RES, ACCEPT_GY, ROW_PARAM_C, ROW_COUNT_C):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        ROL = {n: getattr(O5, f"CAVE_IK_RO_{n}") for n in ("RES", "FILT", "COND", "COST", "SLOT5", "C2H", "H4")}
        RORESERVE = {"RES": 0x90, "FILT": 0x20, "COND": 0xB0, "COST": 0x20, "SLOT5": 0x20, "C2H": 0x30, "H4": 0x40}
        RO_CLS2_PHANTOM, RO_CRIT_PHANTOM, RO_MASK_PHANTOM, RO_GRANT_PHANTOM = 0x0E34, 0x0E48, 0x0E66, 0x15D1
        RO_CLS2_REC = (ROLAND, 0, ROL["RES"] | 1, ROL["FILT"] | 1, ROL["COND"] | 1, ROL["COST"] | 1, ROL["SLOT5"] | 1)
        RO_CRIT_REC = (ROLAND, 0xFFFF, ROL["C2H"] | 1, 0x00000000)      # word 0 = any card; HANDCB filters
        RO_MASK_REC = (ROLAND, 0x0800)                                   # sent to the GY from the field (Maugis's row)
        RO_GRANT_REC = (ROLAND, 500, 0)
        GRANT_BASE, GRANT_COUNT = 0x0226DFB0, 94
        EPREG_BASE, RO_EPREG_ROW = 0x0228E1E0, 133
        RO_EPREG_NATIVE, RO_EPREG_REC = (0x022540F5, 0x0E8B), (0x02254221, ROLAND)   # Fox Fire's walker row shape
        RO_GY_SITE, RO_GY_FRONT, RO_GY_FRONT_LEN = 0x021D13C2, 0x02237E1C, 0x1C       # node: `ldr r0,=0x0EC9 ; cmp r5,r0`


        def _ro_zone(b: EffectBuilder, c2: str) -> None:
            """Branch to *c2* unless desc (r0) is the HAND (0x0B)."""
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xB")
            b.insn("BNE", f"{c2}")


        def ro_res_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xB")
            b.insn("BNE", "g80")
            _used(b, RO_C1KEY, "r4", "zero")
            _post(b, RO_C1KEY)
            b.insn("B", "nat")
            b.label("g80")
            _used(b, RO_C2KEY, "r4", "zero")
            _post(b, RO_C2KEY)
            b.label("nat")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.insn("LDRB", "R3, [R4, #0x3]")
            b.insn("CMP", "R3, #0xB")
            b.insn("BNE", "gy")
            b.call_addr(EQUIP_FROM_GY_RES, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("gy")
            b.call_addr(ADD_FROM_DECK_RES, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def ro_filt_stub() -> EffectBuilder:
            b = EffectBuilder()
            _ro_zone(b, "zero")
            b.ldr_const(3, VYLON_FILTER)
            b.insn("BX", "R3")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b


        def ro_cond_stub() -> EffectBuilder:
            """HAND: OPT 0x4FDB, Vylon f1 (free S/T zone) and f2 (>= 1 legal +08 target) -> 1.  GY: event 6 (End-Phase
            walker) -> OPT 0x2FDB and >= 1 Deck candidate -> 2 (BUILD 10: 1 made 0x0224AD94 demand a legal +08 target, and +08
            is 0 outside the hand -> the End-Phase search was never activated, in-game BUILD 9); event > 6 (sent to the GY) -> post the walker's node
            {side, 0x0FDB, kind 1, ref desc[+0xC]} and return 0.  Anything else -> 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xB")
            b.insn("BNE", "gy")
            _used(b, RO_C1KEY, "r4", "no")
            b.call_addr(VYLON_F1, R4, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(VYLON_F2, R4, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("gy")
            b.insn("CMP", "R0, #0xE")
            b.insn("BNE", "no")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("CMP", "R0, #0x6")
            b.insn("BEQ", "ep")
            b.insn("BLT", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.ldr_const(1, ROLAND)
            b.insn("MOV", "R2, #0x1")
            b.insn("LDRH", "R3, [R4, #0xC]")
            b.call("turnlog_post", via=R5)
            b.insn("B", "no")
            b.label("ep")
            _used(b, RO_C2KEY, "r4", "no")
            b.call_addr(ROW_PARAM_C, R4, via=R5)
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(ROW_COUNT_C, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def ro_cost_stub() -> EffectBuilder:
            b = EffectBuilder()
            _ro_zone(b, "gy")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("gy")
            b.ldr_const(3, TAG_YOU_CAN)
            b.insn("BX", "R3")
            return b


        def ro_slot5_stub() -> EffectBuilder:
            b = EffectBuilder()
            _ro_zone(b, "one")
            b.ldr_const(3, VYLON_SLOT5)
            b.insn("BX", "R3")
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            return b


        def ro_c2h_stub() -> EffectBuilder:
            """Ogier's C2H shape: Deck worker 0x0223BC3C (flags 2) + Oliver's HANDCB (FIRE Warrior or Equip Spell), excl 0x0FDB."""
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2, R3, LR}")
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDR", "R0, [R2, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("LDRH", "R1, [R2, #0x0]")
            b.call_addr(CRIT_WORKER, R0, R1, OL['HANDCB'] | 1, ROLAND)
            b.insn("POP", "{R1, R2, R3, PC}")
            return b


        def ro_h4_stub() -> EffectBuilder:
            """ARM9 0x02023566 LIST B membership front (Turpin's t_h4 grown): Turpin / Ricciardetto / Roland -> 1, else
            tail-jump to Rulers' CAVE3_RUL_H4 with every register and lr intact."""
            from otn_enhanced.effects import cave3 as _c3
            b = EffectBuilder()
            b.ldr_const(3, TURPIN)
            b.insn("CMP", "R0, R3")
            b.insn("BEQ", "yes")
            b.ldr_const(3, RICC)
            b.insn("CMP", "R0, R3")
            b.insn("BEQ", "yes")
            b.ldr_const(3, ROLAND)
            b.insn("CMP", "R0, R3")
            b.insn("BEQ", "yes")
            b.ldr_const(3, ASTOLFO)
            b.insn("CMP", "R0, R3")
            b.insn("BEQ", "yes")
            b.ldr_const(3, BRADA)
            b.insn("CMP", "R0, R3")
            b.insn("BNE", "prev")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("prev")
            b.ldr_const(3, _c3.CAVE3_RUL_H4 | 1)
            b.insn("BX", "R3")
            return b


        def ro_gy_front_stub() -> EffectBuilder:
            """ov3 (puzzle-safe), BL'd from the sent-to-GY node 0x021D13C2 ahead of Nikitama's front: 0x0FDB -> the
            any-location accept 0x021D1938 (Nikitama's / Eva's target); else tail-jump to Nikitama's front, lr intact."""
            from otn_enhanced.effects import cave3 as _c3
            b = EffectBuilder()
            b.ldr_const(0, ROLAND)
            b.insn("CMP", "R5, R0")
            b.insn("BEQ", "acc")
            b.ldr_const(0, _c3.CAVE3_NK_GYNODE | 1)
            b.insn("BX", "R0")
            b.label("acc")
            b.ldr_const(0, ACCEPT_GY)
            b.insn("BX", "R0")
            return b


        ROSTUBS = {"RES": ro_res_stub, "FILT": ro_filt_stub, "COND": ro_cond_stub, "COST": ro_cost_stub, "SLOT5": ro_slot5_stub,
                  "C2H": ro_c2h_stub, "H4": ro_h4_stub}


        def apply_roland(rom, ov: bytearray) -> None:
            from otn_enhanced.effects import cave3 as _c3
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, RO_CLS2_REC, RO_CLS2_PHANTOM, "RO cls2 (C1 hand / C2 GY)")
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, RO_CRIT_REC, RO_CRIT_PHANTOM, "RO C2 criteria row")
            insert_row(ov, MASK_BASE, MASK_COUNT, 4, "<Hh", RO_MASK_REC, RO_MASK_PHANTOM, "RO leave-mask row")
            insert_row(ov, GRANT_BASE, GRANT_COUNT, 6, "<Hhh", RO_GRANT_REC, RO_GRANT_PHANTOM, "RO equip grant row")
            o = EPREG_BASE + RO_EPREG_ROW * 8 - RAM_BASE
            assert struct.unpack_from("<II", ov, o) in (RO_EPREG_NATIVE, RO_EPREG_REC), "RO End-Phase registry row 133 moved"
            struct.pack_into("<II", ov, o, *RO_EPREG_REC)
            blob = ro_gy_front_stub().assemble(RO_GY_FRONT, pad="nop")
            effect_verify.assert_thumb1_only(blob, RO_GY_FRONT)
            assert len(blob) <= RO_GY_FRONT_LEN, f"RO GY front {len(blob)} B > {RO_GY_FRONT_LEN:#x}"
            f = RO_GY_FRONT - RAM_BASE
            assert bytes(ov[f:f + RO_GY_FRONT_LEN]) in (bytes(RO_GY_FRONT_LEN), blob + bytes(RO_GY_FRONT_LEN - len(blob))), \
                "RO ov3 host 0x02237E1C is not zero (The Seal's legacy non-ov3 C3 home?)"
            ov[f:f + len(blob)] = blob
            s = RO_GY_SITE - RAM_BASE
            assert bytes(ov[s:s + 4]) in (_bl(RO_GY_SITE, _c3.CAVE3_NK_GYNODE), _bl(RO_GY_SITE, RO_GY_FRONT)), \
                f"RO GY node {RO_GY_SITE:#x} is not Nikitama's BL"
            ov[s:s + 4] = _bl(RO_GY_SITE, RO_GY_FRONT)
            mc, sec = O5._arm9_main(rom)
            d = bytearray(sec.data)
            a = H4_SITE - 0x02000000
            assert bytes(d[a:a + 4]) in (_bl(H4_SITE, TL["H4"]), _bl(H4_SITE, ROL["H4"])), "RO ARM9 H4 site is not Turpin's BL"
            d[a:a + 4] = _bl(H4_SITE, ROL["H4"])
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            print(f"RO rows, End-Phase row {RO_EPREG_ROW}, ov3 GY front @{RO_GY_FRONT:#x}, ARM9 H4 -> {ROL['H4']:#x}")


        def verify_roland(rom, ov, check) -> None:
            for label, base, count, stride, fmt, rec in (("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, RO_CLS2_REC),
                                                         ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, RO_CRIT_REC),
                                                         ("leave-mask", MASK_BASE, MASK_COUNT, 4, "<Hh", RO_MASK_REC),
                                                         ("equip grant", GRANT_BASE, GRANT_COUNT, 6, "<Hhh", RO_GRANT_REC)):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == ROLAND] == [rec], f"RO {label}: exactly one 0x0fdb row = {rec}")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"RO {label}: sorted")
            check(struct.unpack_from("<II", ov, EPREG_BASE + RO_EPREG_ROW * 8 - RAM_BASE) == RO_EPREG_REC,
                  "RO End-Phase registry row 133 = {0x02254221, 0x0FDB}")
            blob = ro_gy_front_stub().assemble(RO_GY_FRONT, pad="nop")
            check(bytes(ov[RO_GY_FRONT - RAM_BASE:RO_GY_FRONT - RAM_BASE + len(blob)]) == blob, "RO ov3 GY front byte-exact")
            check(_bl_target(ov, RO_GY_SITE) == RO_GY_FRONT, f"RO bl @{RO_GY_SITE:#x} -> GY front (-> Nikitama's)")
            check(_snoww._switch_leaf(bytes(ov), ROLAND) == GY_ACCEPT_LEAF, "RO sent-to-GY chain: 0x0FDB -> accept")
            mc, sec = O5._arm9_main(rom)
            a = H4_SITE - 0x02000000
            check(bytes(sec.data[a:a + 4]) in {_bl(H4_SITE, f) for f in O5.dc_ahead_of(ROL["H4"])},
                  f"RO ARM9 bl @{H4_SITE:#x} -> H4 front (3 cids; disguise_copycat's front may sit ahead)")




        # =================================================================================================
        # card 8: Griffore 0x0FD4 -> Infernoble Knight Astolfo (whole card; notes/infernoble-astolfo-findings.md)
        #   ONE cls2 record switched on desc[+3]; +08 / +14 = 0 (no targets), so every live +0C branch returns 2.
        #   C1 HAND: cost = Dragon Rulers' banish machine cut to one pick (hand+GY FIRE Warrior, this card excluded BY REF);
        #      resolver = Oliver's hand self-SS wrapper (0x02206ABD, final 0 -> our 0x7E) + Tenki's Yes/No -> Level SET rider
        #      {0x1EC1, kind 3, banished Level}.  Hand offer = the ARM9 H4 front.
        #   C2 GY (gy_vrow_hook row): cost = Stygian's banish-self 0x021E5709; resolver posts the delayed-return node
        #      {key 0x0FD4, kind byte 0x41 = kind 1, countdown 4, ref}: Drill Warrior's Standby walker 0x02257738 (registry
        #      row 294, section 293..428) only sees countdown 0 -> my Standby T+4 = "2nd Standby Phase after activation".
        #   C2 BANISHED (zone 0xF, event 2 from the walker): SS this card (summon commit 0x02269315 from its current zone),
        #      then Yes/No -> pick 1 FIRE Warrior in GY / banished -> summon it.
        #   C3 once per DUEL: turn-log kind 5 (never swept; Twin-Headed Behemoth / Glow-Up Bulb), keys 0x4FD4 / 0x2FD4.
        # =================================================================================================
        ASTOLFO = 0x0FD4
        AS_C1KEY, AS_C2KEY, AS_RET_KIND = 0x4000 | ASTOLFO, 0x2000 | ASTOLFO, 0x41
        from otn_enhanced.cards import dragon_rulers as _rul          # noqa: E402
        AS_MSG_BANISH, AS_MESSAGE, AS_PICKER, AS_READBACK = _rul.MSG_BANISH, _rul.MESSAGE, _rul.PICKER, _rul.READBACK
        AS_REF_TO_WORD, AS_GY_BANISH, AS_HAND_BUILDER, AS_GY_BUILDER = (_rul.REF_TO_WORD, _rul.GY_BANISH, _rul.HAND_BUILDER,
                                                                        _rul.GY_BUILDER)
        AS_BANISH_FLAGS, ACTING_DESC_P = _rul.BANISH_FLAGS, 0x0229A9FC
        AS_SUMMON, AS_YESNO, AS_LEVEL_OF, AS_ZONE_OF, MSG_SS_ONE = 0x02269315, 0x0219AAAD, 0x0202ABD9, 0x021A220D, 0x11D
        AS_UI = 0x0229DD94
        for _v in (AS_MESSAGE, AS_PICKER, AS_READBACK, AS_REF_TO_WORD, AS_GY_BANISH, AS_HAND_BUILDER, AS_GY_BUILDER, AS_SUMMON,
                   AS_YESNO, AS_LEVEL_OF, AS_ZONE_OF):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        ASL = {n: getattr(O5, f"CAVE_IK_AS_{n}") for n in ("COND", "COST", "RES", "COSTM", "C1RES", "C2ACT", "C2RET", "CRIT",
                                                           "FILT")}
        ASRESERVE = {"COND": 0x100, "COST": 0x20, "RES": 0x30, "COSTM": 0xe0, "C1RES": 0xc0, "C2ACT": 0x50, "C2RET": 0x130, "CRIT": 0xa0, "FILT": 0x60}
        AS_CLS2_PHANTOM, AS_CRIT_PHANTOM = 0x0E3A, 0x0E49
        AS_CLS2_REC = (ASTOLFO, 0, ASL["RES"] | 1, 0, ASL["COND"] | 1, ASL["COST"] | 1, 0)
        AS_CRIT_REC = (ASTOLFO, 0xFFFF, ASL["CRIT"] | 1, 0x00000000)          # word 0 = any card; AS_FILT filters
        AS_REG_ROW, AS_REG_NATIVE, AS_REG_REC = 294, (0x022573DD, 0x1775), (0x02257739, ASTOLFO)   # Drill Warrior's walker
        P_HAND_ARR, P_HAND_CNT, P_GY_ARR, P_GY_CNT = 0x124, 0x0C, 0x55C, 0x14


        def _kind5_used(b: EffectBuilder, key: int, used: str) -> None:
            """Branch to *used* when (desc[+2], 0xB, key, kind 5) is in the turn log (r4 = desc).  Clobbers r0-r3, r5."""
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_query(R0, key, 5, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", f"{used}")


        def _kind5_post(b: EffectBuilder, key: int) -> None:
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_post(R0, key, 5, via=R5)


        def as_cond_stub() -> EffectBuilder:
            """HAND: C1 unused, may SS, free MZ, >= 2 FIRE Warriors in hand + GY (this card counts itself) -> 2.
            GY (GY action, event 0): C2 unused and Stygian's f2 (in the GY, can banish) -> 2.
            BANISHED, event 2 (the Standby walker): -> 2 (mandatory return).  Else 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xB")
            b.insn("BEQ", "hand")
            b.insn("CMP", "R0, #0xE")
            b.insn("BEQ", "gy")
            b.insn("CMP", "R0, #0xF")
            b.insn("BNE", "no")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BNE", "no")
            b.insn("B", "two")
            b.label("gy")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            _kind5_used(b, AS_C2KEY, "no")
            b.call_addr(STYGIAN_F2, R4, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("B", "two")
            b.label("hand")
            _kind5_used(b, AS_C1KEY, "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(CAN_SS, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_MZ, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R0, R1")
            b.ldr_const(1, _rul.STRIDE)
            b.insn("MUL", "R0, R1")
            b.ldr_const(7, _rul.PLAYER)
            b.insn("ADD", "R7, R7, R0")
            b.insn("MOV", "R6, #0x0")
            b.insn("LDR", f"R0, [R7, #0x{P_HAND_CNT:X}]")
            b.ldr_const(1, P_HAND_ARR)
            b.insn("ADD", "R1, R7, R1")
            b.bl_label("scan")
            b.insn("LDR", f"R0, [R7, #0x{P_GY_CNT:X}]")
            b.ldr_const(1, P_GY_ARR)
            b.insn("ADD", "R1, R7, R1")
            b.bl_label("scan")
            b.insn("CMP", "R6, #0x2")
            b.insn("BLT", "no")
            b.label("two")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("scan")
            b.insn("PUSH", "{R4, R5, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.label("slp")
            b.insn("CMP", "R4, #0x0")
            b.insn("BLE", "sdone")
            b.insn("LDR", "R7, [R5, #0x0]")
            b.insn("LSL", "R7, R7, #0x12")
            b.insn("LSR", "R7, R7, #0x12")
            _fire_warrior_or_equip(b, "r7", "shit", "snext", fw_only=True)
            b.label("shit")
            b.insn("ADD", "R6, #0x1")
            b.label("snext")
            b.insn("ADD", "R5, #0x4")
            b.insn("SUB", "R4, #0x1")
            b.insn("B", "slp")
            b.label("sdone")
            b.insn("POP", "{R4, R5, R7, PC}")
            return b


        def as_cost_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xB")
            b.insn("BNE", "g")
            b.ldr_const(3, ASL['COSTM'] | 1)
            b.insn("BX", "R3")
            b.label("g")
            b.insn("CMP", "R3, #0xE")
            b.insn("BNE", "one")
            b.ldr_const(3, STYGIAN_COST)
            b.insn("BX", "R3")
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            return b


        def as_res_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xB")
            b.insn("BNE", "g")
            b.ldr_const(3, ASL['C1RES'] | 1)
            b.insn("BX", "R3")
            b.label("g")
            b.insn("CMP", "R3, #0xE")
            b.insn("BNE", "b")
            b.ldr_const(3, ASL['C2ACT'] | 1)
            b.insn("BX", "R3")
            b.label("b")
            b.ldr_const(3, ASL['C2RET'] | 1)
            b.insn("BX", "R3")
            return b


        def as_costm_stub() -> EffectBuilder:
            """Hand +10 on [STATE+0x7C] (0 yield / 1 done / -1 abort), Dragon Rulers' machine cut to ONE pick:
               settled -> 1 | 0 message | 1 picker (acting desc = ours -> AS_CRIT hand mode) | 2 readback: ref -> desc+0x1C,
               Level -> desc+0x1E | 3 banish it (hand index or GY) -> 1."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(SHORTCIRCUIT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ph")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("ph")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x7C]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ph0")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "ph1")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "ph2")
            b.insn("B", "ph3")
            b.label("ph0")
            b.call_addr(AS_MESSAGE, R5, AS_MSG_BANISH, via=R3)
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "setp")
            b.label("ph1")
            b.ldr_const(0, ACTING_DESC_P)
            b.insn("STR", "R4, [R0, #0x50]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R1, #0x6")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call_addr(AS_PICKER, R0, R1, R2, 0, via=R7)
            b.insn("MOV", "R0, #0x2")
            b.insn("B", "setp")
            b.label("ph2")
            b.call_addr(AS_READBACK, via=R3)
            b.insn("LDR", "R7, [R0, #0x0]")
            b.insn("LSL", "R0, R7, #0x11")
            b.insn("LSR", "R0, R0, #0x1F")
            b.insn("LSL", "R1, R7, #0x1")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R1, R1, #0x1")
            b.insn("ADD", "R1, R1, R0")
            b.insn("STRH", "R1, [R4, #0x1C]")
            b.insn("LSL", "R0, R7, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call("cid_level", via=R3)
            b.insn("STRH", "R0, [R4, #0x1E]")
            b.insn("MOV", "R0, #0x3")
            b.label("setp")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("ph3")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("LDRH", "R7, [R4, #0x1C]")
            b.call_addr(HAND_INDEX, R5, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "bgy")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(HAND_BANISH, R5, via=R3)
            b.insn("B", "bdone")
            b.label("bgy")
            b.call_addr(AS_REF_TO_WORD, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "bdone")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(AS_GY_BANISH, R5, R1, 0, via=R3)
            b.label("bdone")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("MOV", "R0, #0x1")
            b.label("ret")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def as_c1res_stub() -> EffectBuilder:
            """Oliver's o_c2res shape: 0x80 once-per-Duel check + stamp (0x4FD4 kind 5) -> native hand self-SS; any native 0
            -> our 0x7E = Yes/No (Tenki's 0xFA) when the banished Level differs -> 0x7D = on Yes, Level SET rider
            {0x1EC1, kind 3, desc[+0x1E]} on this card's (side, zone)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R2, R3, R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BEQ", "p80")
            b.insn("CMP", "R0, #0x7E")
            b.insn("BEQ", "p7e")
            b.insn("CMP", "R0, #0x7D")
            b.insn("BEQ", "p7d")
            b.label("native")
            b.call_addr(HAND_SS_RES, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "out")
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "out")
            b.label("p80")
            _kind5_used(b, AS_C1KEY, "zero")
            _kind5_post(b, AS_C1KEY)
            b.insn("B", "native")
            b.label("p7e")
            b.insn("LDRH", "R0, [R4, #0x1E]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R1, R0, #0x10")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("CMP", "R1, #0x5")
            b.insn("BGE", "zero")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("MOV", "R1, #0xFA")
            b.insn("LDRH", "R2, [R4, #0xC]")
            b.call_addr(AS_YESNO, via=R3)
            b.insn("MOV", "R0, #0x7D")
            b.insn("B", "out")
            b.label("p7d")
            b.ldr_const(0, AS_UI)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R1, R0, #0x10")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("CMP", "R1, #0x5")
            b.insn("BGE", "zero")
            b.insn("LSL", "R0, R0, #0x18")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LDRH", "R2, [R4, #0x1E]")
            b.insn("STR", "R2, [SP, #0x0]")
            b.call_addr(RIDER_WRITE, R0, R1, LEVEL_SET_KEY, 3, via=R5)
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.label("out")
            b.insn("POP", "{R2, R3, R4, R5, R6, PC}")
            return b


        def as_c2act_stub() -> EffectBuilder:
            """GY activation resolver (Astolfo already banished by the cost): 0x80 once-per-Duel check + stamp (0x2FD4 kind 5),
            then the delayed-return node {side, 0x0FD4, kind byte 0x41, ref}.  Done in one phase."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "zero")
            _kind5_used(b, AS_C2KEY, "zero")
            _kind5_post(b, AS_C2KEY)
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.ldr_const(1, ASTOLFO)
            b.insn("MOV", f"R2, #0x{AS_RET_KIND:X}")
            b.insn("LDRH", "R3, [R4, #0xC]")
            b.call("turnlog_post", via=R5)
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def as_c2ret_stub() -> EffectBuilder:
            """Banished-zone return (event 2), phases on [STATE+0x70]:
               0x80 chain push; this card still banished, may SS, free MZ -> summon it (0x02269315) -> 0x7F; else -> 0x78
               0x7F may SS, free MZ, >= 1 FIRE Warrior in GY / banished (row count, acting desc = ours -> AS_CRIT worker mode)
                    -> Yes/No 0xFA -> 0x7E; else -> 0x78
               0x7E Yes -> message 0x11D -> 0x7D; No -> 0x78
               0x7D picker -> 0x7C | 0x7C readback -> summon it -> 0x78 | 0x78 chain pop -> 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BEQ", "p80")
            b.insn("CMP", "R0, #0x7F")
            b.insn("BEQ", "p7f")
            b.insn("CMP", "R0, #0x7E")
            b.insn("BEQ", "p7e")
            b.insn("CMP", "R0, #0x7D")
            b.insn("BEQ", "p7d")
            b.insn("CMP", "R0, #0x7C")
            b.insn("BEQ", "p7c")
            b.insn("CMP", "R0, #0x78")
            b.insn("BEQ", "p78")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("p80")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(AS_ZONE_OF, via=R3)
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("CMP", "R0, #0xF")
            b.insn("BNE", "to78")
            b.bl_label("room")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "to78")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(AS_REF_TO_WORD, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "to78")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(AS_SUMMON, R5, R1, 1, ASTOLFO << 16, via=R7)
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("p7f")
            b.bl_label("room")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "to78")
            b.call_addr(ROW_PARAM_C, R4, via=R3)
            b.insn("ADD", "R2, R0, #0x0")
            b.call_addr(ROW_COUNT_C, R5, ASTOLFO, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "to78")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("MOV", "R1, #0xFA")
            b.insn("LDRH", "R2, [R4, #0xC]")
            b.call_addr(AS_YESNO, via=R3)
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("p7e")
            b.ldr_const(0, AS_UI)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "to78")
            b.call_addr(AS_MESSAGE, R5, MSG_SS_ONE, via=R3)
            b.insn("MOV", "R0, #0x7D")
            b.insn("B", "ret")
            b.label("p7d")
            b.ldr_const(0, ACTING_DESC_P)
            b.insn("STR", "R4, [R0, #0x50]")
            b.call_addr(AS_PICKER, R5, 6, ASTOLFO, 0, via=R7)
            b.insn("MOV", "R0, #0x7C")
            b.insn("B", "ret")
            b.label("p7c")
            b.call_addr(AS_READBACK, via=R3)
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(AS_SUMMON, R5, R1, 1, ASTOLFO << 16, via=R7)
            b.label("to78")
            b.insn("MOV", "R0, #0x78")
            b.insn("B", "ret")
            b.label("p78")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("room")
            b.insn("PUSH", "{LR}")
            b.call_addr(CAN_SS, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "rno")
            b.call_addr(FREE_MZ, R5, via=R3)
            b.label("rno")
            b.insn("POP", "{PC}")
            return b


        def as_crit_stub() -> EffectBuilder:
            """Criteria handler (row r0, side r1, param r2), mode from the ACTING descriptor (Dragon Rulers' crit shape):
            a HAND (0x0B) desc of 0x0FD4 -> list builders HAND + GY with flags (2, 0x10000) (the C1 banish pick);
            anything else -> GY worker (flags 0) + banished worker (flags 0xC) (the C2 follow-up pick).  AS_FILT filters."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R4, R1, #0x0")
            b.ldr_const(0, ACTING_DESC_P)
            b.insn("LDR", "R6, [R0, #0x50]")
            b.insn("CMP", "R6, #0x0")
            b.insn("BEQ", "wk")
            b.insn("LDRH", "R0, [R6, #0x0]")
            b.ldr_const(1, ASTOLFO)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "wk")
            b.insn("LDRB", "R0, [R6, #0x3]")
            b.insn("CMP", "R0, #0xB")
            b.insn("BNE", "wk")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x0]")
            b.ldr_const(0, AS_BANISH_FLAGS)
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.ldr_const(2, ASL['FILT'] | 1)
            b.insn("ADD", "R3, SP, #0x8")
            b.call_addr(AS_HAND_BUILDER, via=R6)
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x0]")
            b.ldr_const(0, AS_BANISH_FLAGS)
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.ldr_const(2, ASL['FILT'] | 1)
            b.insn("ADD", "R3, SP, #0x8")
            b.call_addr(AS_GY_BUILDER, via=R6)
            b.insn("B", "out")
            b.label("wk")
            b.insn("LDR", "R0, [R5, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(GY_WORKER, R0, R1, ASL['FILT'] | 1, 0)
            b.insn("ADD", "R7, R0, #0x0")
            b.insn("LDR", "R0, [R5, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0xC")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(BAN_WORKER, R0, R1, ASL['FILT'] | 1, 0)
            b.insn("ADD", "R0, R7, R0")
            b.label("out")
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def as_filt_stub() -> EffectBuilder:
            """Candidate callback (builders and workers both enter with [sp] = &card word): keep a FIRE Warrior; while the
            acting desc is Astolfo's HAND desc, drop THIS card (ref == desc[+0xC]) -- a 2nd Astolfo stays legal."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("LDR", "R0, [SP, #0x10]")
            b.insn("LDR", "R4, [R0, #0x0]")
            b.insn("LSL", "R0, R4, #0x11")
            b.insn("LSR", "R0, R0, #0x1F")
            b.insn("LSL", "R1, R4, #0x1")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R1, R1, #0x1")
            b.insn("ADD", "R6, R1, R0")
            b.ldr_const(0, ACTING_DESC_P)
            b.insn("LDR", "R5, [R0, #0x50]")
            b.insn("CMP", "R5, #0x0")
            b.insn("BEQ", "chk")
            b.insn("LDRH", "R0, [R5, #0x0]")
            b.ldr_const(1, ASTOLFO)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "chk")
            b.insn("LDRB", "R0, [R5, #0x3]")
            b.insn("CMP", "R0, #0xB")
            b.insn("BNE", "chk")
            b.insn("LDRH", "R0, [R5, #0xC]")
            b.insn("CMP", "R0, R6")
            b.insn("BEQ", "no")
            b.label("chk")
            b.insn("LSL", "R4, R4, #0x12")
            b.insn("LSR", "R4, R4, #0x12")
            _fire_warrior_or_equip(b, "r4", "yes", "no", fw_only=True)
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        ASSTUBS = {"COND": as_cond_stub, "COST": as_cost_stub, "RES": as_res_stub, "COSTM": as_costm_stub, "C1RES": as_c1res_stub,
                  "C2ACT": as_c2act_stub, "C2RET": as_c2ret_stub, "CRIT": as_crit_stub, "FILT": as_filt_stub}


        def apply_astolfo(rom, ov: bytearray) -> None:
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, AS_CLS2_REC, AS_CLS2_PHANTOM, "AS cls2 (C1 hand / C2 GY+banished)")
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, AS_CRIT_REC, AS_CRIT_PHANTOM, "AS criteria row")
            o = EPREG_BASE + AS_REG_ROW * 8 - RAM_BASE
            assert struct.unpack_from("<II", ov, o) in (AS_REG_NATIVE, AS_REG_REC), "AS registry row 294 moved"
            struct.pack_into("<II", ov, o, *AS_REG_REC)
            print(f"AS cls2 + criteria rows, registry row {AS_REG_ROW} -> Drill Warrior's Standby walker")


        def verify_astolfo(rom, ov, check) -> None:
            for label, base, count, stride, fmt, rec in (("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, AS_CLS2_REC),
                                                         ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, AS_CRIT_REC)):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == ASTOLFO] == [rec], f"AS {label}: exactly one 0x0fd4 row = {rec}")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"AS {label}: sorted")
            check(struct.unpack_from("<II", ov, EPREG_BASE + AS_REG_ROW * 8 - RAM_BASE) == AS_REG_REC,
                  "AS registry row 294 = {0x02257739, 0x0FD4}")


        # =================================================================================================
        # card 9: Sonic Duck 0x160B -> Courageous Crimson Chevalier Bradamante (notes/infernoble-bradamante-findings.md)
        #   C0 "always treated as an Infernoble Knight card": card text only (user).
        #   C1 HAND: discard this card; target 1 Warrior you control; equip it with 1 Equip Spell from the Deck that can equip
        #      to it = Vylon Sigma / Dragunity Primus Pilus resolver 0x0222DC49 in Pilus's DECLARED-TARGET branch (two cid
        #      fronts), criteria = Deck worker + the native legality callback 0x0223E395 against the target's location.
        #   C2 GY (list106 battle-destroyed-to-GY trigger): not equipped (leave-time marker), SS this card, then Allure Queen's
        #      equip-that-monster resolver 0x0220BFFD on "the monster it battled" (Fist filter copy, opponent's side).
        # =================================================================================================
        BRADA = 0x160B
        BR_C1KEY, BR_C2KEY, BR_EQKEY = 0x4000 | BRADA, 0x2000 | BRADA, 0x6000 | BRADA
        SIGMA_RES, ALLURE_RES, DISCARD_SELF, LEGAL_CB = 0x0222DC49, 0x0220BFFD, 0x021E6FD9, 0x0223E395
        PILUS_TSTEP, ALLURE_TSTEP, FIST_TAIL, FIST_PRED, TARGET_LOC = 0x02234D8D, 0x02234D99, 0x021E1577, 0x021D6E41, 0x02234905
        FREE_ST, TL_REMOVE = 0x021AE645, 0x021C4975
        for _v in (SIGMA_RES, ALLURE_RES, DISCARD_SELF, LEGAL_CB, PILUS_TSTEP, ALLURE_TSTEP, FIST_TAIL, FIST_PRED, TARGET_LOC,
                   FREE_ST, TL_REMOVE):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        BRL = {n: getattr(O5, f"CAVE_IK_BR_{n}") for n in ("COND", "COST", "FILT", "SLOT5", "RES", "C1RES", "C2RES", "FIST",
                                                           "CRIT", "LEAVE", "CIDA", "CIDB")}
        BRRESERVE = {"COND": 0x100, "COST": 0x20, "FILT": 0x20, "SLOT5": 0x20, "RES": 0x20, "C1RES": 0x60, "C2RES": 0xC0,
                     "FIST": 0x40, "CRIT": 0x50, "LEAVE": 0xB0, "CIDA": 0x20, "CIDB": 0x20}
        BR_CLS2_PHANTOM, BR_CRIT_PHANTOM, BR_L106_PHANTOM = 0x0E3E, 0x1529, 0x1B18
        BR_CLS2_REC = (BRADA, 0, BRL["RES"] | 1, BRL["FILT"] | 1, BRL["COND"] | 1, BRL["COST"] | 1, BRL["SLOT5"] | 1)
        BR_CRIT_REC = (BRADA, 0xFFFF, BRL["CRIT"] | 1, 0x00000204)         # Sigma's word (Equip Spell)
        L106_BASE, L106_COUNT = 0x0226E990, 0x6A
        CIDA_SITE, CIDA_STOCK = 0x0222DC50, bytes.fromhex("5a498a42")     # ldr r1,=0x2170 ; cmp r2,r1
        CIDB_SITE, CIDB_STOCK = 0x0222DCBE, bytes.fromhex("3f488142")     # ldr r0,=0x2170 ; cmp r1,r0
        LEAVE_SITE = 0x021C8216
        P_DECK_ARR, P_DECK_CNT = 0x304, 0x10


        def _br_zone(b: EffectBuilder, gy: str) -> None:
            """Branch to *gy* unless desc (r0) is the HAND."""
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xB")
            b.insn("BNE", f"{gy}")


        def br_cond_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xB")
            b.insn("BEQ", "hand")
            b.insn("CMP", "R0, #0xE")
            b.insn("BNE", "no")
            _used(b, BR_C2KEY, "r4", "no")
            _used(b, BR_EQKEY, "r4", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(CAN_SS, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_MZ, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("B", "st")
            b.label("hand")
            _used(b, BR_C1KEY, "r4", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R0, R1")
            b.ldr_const(1, _rul.STRIDE)
            b.insn("MUL", "R0, R1")
            b.ldr_const(7, _rul.PLAYER)
            b.insn("ADD", "R7, R7, R0")
            b.insn("LDR", f"R5, [R7, #0x{P_DECK_CNT:X}]")
            b.ldr_const(0, P_DECK_ARR)
            b.insn("ADD", "R7, R7, R0")
            b.label("dlp")
            b.insn("CMP", "R5, #0x0")
            b.insn("BLE", "no")
            b.insn("LDR", "R6, [R7, #0x0]")
            b.insn("LSL", "R6, R6, #0x12")
            b.insn("LSR", "R6, R6, #0x12")
            b.call("get_race", R6, via=R3)
            b.insn("CMP", f"R0, #0x{RACE_SPELL:X}")
            b.insn("BNE", "dnx")
            b.call_addr(GET_SPELLTYPE, R6, via=R3)
            b.insn("CMP", f"R0, #0x{SPELL_EQUIP:X}")
            b.insn("BEQ", "st")
            b.label("dnx")
            b.insn("ADD", "R7, #0x4")
            b.insn("SUB", "R5, #0x1")
            b.insn("B", "dlp")
            b.label("st")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_ST, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def br_cost_stub() -> EffectBuilder:
            b = EffectBuilder()
            _br_zone(b, "gy")
            b.ldr_const(3, DISCARD_SELF)
            b.insn("BX", "R3")
            b.label("gy")
            b.ldr_const(3, TAG_YOU_CAN)
            b.insn("BX", "R3")
            return b


        def br_filt_stub() -> EffectBuilder:
            b = EffectBuilder()
            _br_zone(b, "gy")
            b.ldr_const(3, VYLON_FILTER)
            b.insn("BX", "R3")
            b.label("gy")
            b.ldr_const(3, BRL['FIST'] | 1)
            b.insn("BX", "R3")
            return b


        def br_slot5_stub() -> EffectBuilder:
            b = EffectBuilder()
            _br_zone(b, "gy")
            b.ldr_const(3, PILUS_TSTEP)
            b.insn("BX", "R3")
            b.label("gy")
            b.ldr_const(3, ALLURE_TSTEP)
            b.insn("BX", "R3")
            return b


        def br_res_stub() -> EffectBuilder:
            b = EffectBuilder()
            _br_zone(b, "gy")
            b.ldr_const(3, BRL['C1RES'] | 1)
            b.insn("BX", "R3")
            b.label("gy")
            b.ldr_const(3, BRL['C2RES'] | 1)
            b.insn("BX", "R3")
            return b


        def br_c1res_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, BR_C1KEY, "r4", "zero")
            _post(b, BR_C1KEY)
            b.label("nat")
            b.call_addr(SIGMA_RES, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def br_c2res_stub() -> EffectBuilder:
            """GY C2.  [0x70] 0x80 & desc[+0x1E] == 0: OPT check + stamp, mark, chain push, GY self-SS 0x0220731D -> 0x91 |
            0x91 chain pop -> 0x92 | 0x92 this card on a monster zone? desc[+3] = that zone AND desc[+0xE] = its new instance
            bits (BUILD 13: 0x021D2C1C compares them; stale bits sent the target to the GY in-game), [0x70] = 0x80, Allure |
            anything else (Allure's own 0x80 re-entry, 0x7F, 0x7E) -> Allure's resolver."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(7, 0x0229aafc)
            b.insn("LDR", "R0, [R7, #0x70]")
            b.insn("CMP", "R0, #0x91")
            b.insn("BEQ", "p91")
            b.insn("CMP", "R0, #0x92")
            b.insn("BEQ", "p92")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "allure")
            b.insn("LDRB", "R0, [R4, #0x1E]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "allure")
            _used(b, BR_C2KEY, "r4", "zero")
            _post(b, BR_C2KEY)
            b.insn("MOV", "R0, #0x1")
            b.insn("STRB", "R0, [R4, #0x1E]")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.call_addr(GY_SELF_SS, R4, R6, via=R3)
            b.insn("MOV", "R0, #0x91")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("p91")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("MOV", "R0, #0x92")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("p92")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R1, R0, #0x10")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("CMP", "R1, #0x5")
            b.insn("BGE", "zero")
            b.insn("STRB", "R1, [R4, #0x3]")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.insn("LSL", "R0, R0, #0x3")
            b.ldr_const(2, 0x0229c33c)
            b.insn("LDR", "R0, [R2, R0]")
            b.insn("LSL", "R0, R0, #0xB")
            b.insn("LSR", "R0, R0, #0x1E")
            b.insn("STRB", "R0, [R4, #0xE]")
            b.insn("MOV", "R0, #0x80")
            b.insn("STR", "R0, [R7, #0x70]")
            b.label("allure")
            b.call_addr(ALLURE_RES, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def br_fist_stub() -> EffectBuilder:
            """+08 (desc, side, zone): Fist's prologue (zone predicate 0x1010) + an opponent-side test, then Fist's own arm
            0x021E1576 ('a battle participant that is not the equipped monster'), which pops this same frame."""
            b = EffectBuilder()
            b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
            b.ldr_const(3, 0x1010)
            b.insn("ADD", "R7, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.call_addr(FIST_PRED, via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRB", "R0, [R7, #0x2]")
            b.insn("CMP", "R5, R0")
            b.insn("BEQ", "no")
            b.ldr_const(4, FIST_TAIL)
            b.insn("BX", "R4")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            return b


        def br_crit_stub() -> EffectBuilder:
            """Criteria handler (row, side, param): Sigma's 0x02242C18 with the callback's location = the ACTING descriptor's
            declared target 0x02234904(desc, 0) (Pilus's branch), not the param."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("SUB", "SP, #0x10")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R4, R1, #0x0")
            b.ldr_const(0, ACTING_DESC_P)
            b.insn("LDR", "R0, [R0, #0x50]")
            b.insn("MOV", "R1, #0x0")
            b.insn("SUB", "R1, #0x1")
            b.insn("STR", "R1, [SP, #0x8]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "go")
            b.call_addr(TARGET_LOC, R0, 0, via=R3)
            b.insn("STR", "R0, [SP, #0x8]")
            b.label("go")
            b.insn("LDR", "R0, [R5, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.ldr_const(2, LEGAL_CB)
            b.insn("ADD", "R3, SP, #0x8")
            b.call_addr(CRIT_WORKER)
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def br_leave_stub() -> EffectBuilder:
            """BL @0x021C8216 (per-cid leave switch; r4 = cid; [sp+0x44] by battle, [sp+0x90] destroyed, [sp+0x98] side,
            [sp+0xA0] zone, read BEFORE any push).  0x160B destroyed by battle: an S/T card on either side whose equip target
            0x021A0DF8 is (zone<<8|side) -> post marker {0x760B, kind 1}; else queue its removal; then replay the displaced
            `movs r1,#0x77 ; lsls r1,#6` and return (= the T.G. trampoline's own non-member path).  Every other cid tail-jumps
            to the T.G. arm trampoline with lr intact."""
            from otn_enhanced.effects import cave3 as _c3
            b = EffectBuilder()
            b.ldr_const(1, BRADA)
            b.insn("CMP", "R4, R1")
            b.insn("BNE", "prev")
            b.insn("LDR", "R1, [SP, #0x44]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "prev")
            b.insn("LDR", "R1, [SP, #0x90]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "prev")
            b.insn("PUSH", "{R0, R2, R3, R4, R5, R6, R7, LR}")
            b.insn("LDR", "R7, [SP, #0xB8]")
            b.insn("LDR", "R6, [SP, #0xC0]")
            b.insn("LSL", "R6, R6, #0x8")
            b.insn("ORR", "R6, R7")
            b.insn("MOV", "R4, #0x0")
            b.label("sl")
            b.insn("MOV", "R5, #0x5")
            b.label("zl")
            b.call_addr(CARD_CID_AT, R4, R5, via=R2)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "nx")
            b.call_addr(EQUIP_TARGET_OF, R4, R5, via=R2)
            b.insn("CMP", "R0, R6")
            b.insn("BEQ", "yes")
            b.label("nx")
            b.insn("ADD", "R5, #0x1")
            b.insn("CMP", "R5, #0x9")
            b.insn("BLE", "zl")
            b.insn("ADD", "R4, #0x1")
            b.insn("CMP", "R4, #0x1")
            b.insn("BLE", "sl")
            b.call_addr(TL_REMOVE, R7, 0xB, BR_EQKEY, 0, via=R4)
            b.insn("B", "done")
            b.label("yes")
            b.insn("ADD", "R0, R7, #0x0")
            b.turnlog_post(R0, BR_EQKEY, 1, via=R4)
            b.label("done")
            b.insn("MOV", "R1, #0x77")
            b.insn("LSL", "R1, R1, #0x6")
            b.insn("POP", "{R0, R2, R3, R4, R5, R6, R7, PC}")
            b.label("prev")
            b.ldr_const(1, _c3.CAVE3_TGSH_ARMTRAMP | 1)
            b.insn("BX", "R1")
            return b


        def _cid_front(cid_reg: int, tmp: int) -> EffectBuilder:
            b = EffectBuilder()
            b.ldr_const(tmp, 0x2170)
            b.insn("CMP", f"R{cid_reg}, R{tmp}")
            b.insn("BEQ", "out")
            b.ldr_const(tmp, BRADA)
            b.insn("CMP", f"R{cid_reg}, R{tmp}")
            b.label("out")
            b.insn("BX", "LR")
            return b


        BRSTUBS = {"COND": br_cond_stub, "COST": br_cost_stub, "FILT": br_filt_stub, "SLOT5": br_slot5_stub, "RES": br_res_stub,
                  "C1RES": br_c1res_stub, "C2RES": br_c2res_stub, "FIST": br_fist_stub, "CRIT": br_crit_stub, "LEAVE": br_leave_stub,
                  "CIDA": lambda: _cid_front(2, 1), "CIDB": lambda: _cid_front(1, 0)}


        def apply_brada(rom, ov: bytearray) -> None:
            from otn_enhanced.effects import cave3 as _c3
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, BR_CLS2_REC, BR_CLS2_PHANTOM, "BR cls2 (C1 hand / C2 GY)")
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, BR_CRIT_REC, BR_CRIT_PHANTOM, "BR criteria row")
            from otn_enhanced.effects.common import list_insert as _list_insert
            _list_insert(ov, L106_BASE, L106_COUNT, BRADA, BR_L106_PHANTOM, "BR list106")
            for site, stock, dst in ((CIDA_SITE, CIDA_STOCK, BRL["CIDA"]), (CIDB_SITE, CIDB_STOCK, BRL["CIDB"]),
                                     (LEAVE_SITE, _bl(LEAVE_SITE, _c3.CAVE3_TGSH_ARMTRAMP), BRL["LEAVE"])):
                o = site - RAM_BASE
                assert bytes(ov[o:o + 4]) in (stock, _bl(site, dst)), f"BR site {site:#x} = {bytes(ov[o:o + 4]).hex()}"
                ov[o:o + 4] = _bl(site, dst)
            print("BR cls2 + criteria + list106 rows; fronts @0x0222DC50 / 0x0222DCBE / 0x021C8216")


        def verify_brada(rom, ov, check) -> None:
            for label, base, count, stride, fmt, rec in (("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, BR_CLS2_REC),
                                                         ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, BR_CRIT_REC)):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == BRADA] == [rec], f"BR {label}: exactly one 0x160b row = {rec}")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"BR {label}: sorted")
            l106 = [struct.unpack_from("<H", ov, L106_BASE + 2 * i - RAM_BASE)[0] for i in range(L106_COUNT)]
            check(BRADA in l106 and BR_L106_PHANTOM not in l106 and l106 == sorted(l106), "BR list106: 0x160B in, sorted")
            for site, dst in ((CIDA_SITE, BRL["CIDA"]), (CIDB_SITE, BRL["CIDB"])):
                check(_bl_target(ov, site) == dst, f"BR bl @{site:#x} -> {dst:#x}")
            check(_bl_target(ov, LEAVE_SITE) in LEAVE_FRONTS, "BR leave site -> its front (or a later card's ahead of it)")


        # =================================================================================================
        # card 10: Thousand Dragon 0x0FEB -> Infernoble Knight Captain Roland (notes/infernoble-captain-roland-findings.md)
        #   Identity: ASSD / Junk Speeder recipe -- card_prop from a real Synchro TUNER (Formula Synchron 0x239E), genre
        #      FUSION -> SYNCHRO, fusion recipe A[8] materials -> 0x3FFF; the material rule is the generic one (proven walk).
        #   C1 "If Synchro Summoned: You can ... during the End Phase of this turn, send 1 Equip Spell from the Deck to the GY,
        #      then add 1 Warrior from the Deck to the hand": trigger = ov5 front at the proper-Summon site 0x02265900; cls1
        #      resolver posts {0x0FEB, kind 1, ref}; End-Phase row 99 {0x0225432D (Into the Void's rider thunk, zone 0x10 = card
        #      anywhere), 0x0FEB} -> cls2 event 6 -> Armageddon's send-from-Deck 0x02208DD5 then the Deck add 0x02207EF5.
        #   C2 (GY Quick Effect, Main Phase): NOT BUILT YET -- waiting on the GY Quick Effect measurement (Necro Gardna).
        # =================================================================================================
        CAPROL = 0x0FEB
        CR_C1KEY = 0x4000 | CAPROL
        CR_REF_SYNCHRO_TUNER = 0x239E                                     # Formula Synchron
        CR_FUSION_ROW, CR_FUSION_STOCK, CR_FUSION_DEAD = 0x02270BD4, (CAPROL, 0x0FB6, 0x0FAA, 0), 0x3FFF
        CR_EP_ROW, CR_EP_NATIVE, CR_EP_REC = 99, (0x0225432D, 0x0EC3), (0x0225432D, CAPROL)
        CRL = {n: getattr(O5, f"CAVE_IK_CR_{n}") for n in ("FRONT", "COND1", "RES1", "COND2", "RES2", "CRIT", "CB", "RESW",
                                                           "FILT", "CONDX", "SLOT5", "C2RES", "SPEED", "SPD9")}
        CRRESERVE = {"FRONT": 0x20, "COND1": 0x40, "RES1": 0x60, "COND2": 0x20, "RES2": 0x80, "CRIT": 0x40, "CB": 0x60,
                     "RESW": 0x20, "FILT": 0x20, "CONDX": 0x80, "SLOT5": 0x20, "C2RES": 0x50, "SPEED": 0x20, "SPD9": 0x20}
        # The GY enumerator 0x0224C820 prefilters every row with the NATIVE ARM9 speed 0x0202345C(row cid) >= 2 -- at
        # 0x0224C8AC (quick-only pass) and at 0x0224C8E4 (whenever it is NOT the turn player's own Main Phase).  Measured
        # over rom_infernoble.ml3 (opponent's Main Phase): without these fronts 0x0FEB's row is never checked.
        NATIVE_SPEED, SPD9_SITES = 0x0202345D, (0x0224C8AC, 0x0224C8E4)
        CR_C2KEY = 0x2000 | CAPROL
        CR_GRANT_PHANTOM, CR_GRANT_REC = 0x0E6D, (CAPROL, 500, 0)
        SPEED_LEAF = 0x021A894C
        CR_CLS1_PHANTOM, CR_CLS2_PHANTOM, CR_CRIT_PHANTOM = 0x0E65, 0x0E41, 0x0E6C
        CR_CLS1_REC = (CAPROL, 0, CRL["RES1"] | 1, 0, CRL["COND1"] | 1, TAG_YOU_CAN, 0)
        CR_CLS2_REC = (CAPROL, 0, CRL["RESW"] | 1, CRL["FILT"] | 1, CRL["CONDX"] | 1, 0, CRL["SLOT5"] | 1)
        CR_CRIT_REC = (CAPROL, 0xFFFF, CRL["CRIT"] | 1, 0x00000000)         # word 0 = any card; CR_CB filters by stage


        def cr_front_stub() -> EffectBuilder:
            """BL @0x02265900 (`cmp r0,#0 ; beq`): native member -> the shared stub; 0x0FEB -> return to lr (member path);
            else the shared cave3 stub with r0 = 0 and lr intact (it adds the non-member skip itself)."""
            from otn_enhanced.effects import cave3 as _c3
            b = EffectBuilder()
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "shared")
            b.insn("LDRH", "R1, [R4, #0xE]")
            b.ldr_const(0, CAPROL)
            b.insn("CMP", "R1, R0")
            b.insn("BNE", "miss")
            b.insn("BX", "LR")
            b.label("miss")
            b.insn("MOV", "R0, #0x0")
            b.label("shared")
            b.ldr_const(1, _c3.CAVE3_SUMMONTRIG | 1)
            b.insn("BX", "R1")
            return b


        def cr_cond1_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            _used(b, CR_C1KEY, "r4", "no")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def cr_res1_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "zero")
            _used(b, CR_C1KEY, "r4", "zero")
            _post(b, CR_C1KEY)
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.ldr_const(1, CAPROL)
            b.insn("MOV", "R2, #0x1")
            b.insn("LDRH", "R3, [R4, #0xC]")
            b.call("turnlog_post", via=R5)
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def cr_cond2_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("LDRB", "R1, [R0, #0x3]")
            b.insn("CMP", "R1, #0x10")
            b.insn("BNE", "no")
            b.insn("LDRB", "R1, [R0, #0x4]")
            b.insn("CMP", "R1, #0x6")
            b.insn("BNE", "no")
            b.insn("MOV", "R0, #0x2")
            b.insn("BX", "LR")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b


        def cr_res2_stub() -> EffectBuilder:
            """Stage desc[+0x1E]: 0 = Armageddon's send-from-Deck 0x02208DD5 until it returns 0, then stage 1 with
            [0x70] = 0x80 = the Deck add 0x02207EF5 (both read the criteria row through the acting desc -> CR_CB)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(7, 0x0229aafc)
            b.insn("LDRB", "R0, [R4, #0x1E]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "st1")
            b.call_addr(ARMAGEDDON_RES, R4, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "ret")
            b.insn("MOV", "R0, #0x1")
            b.insn("STRB", "R0, [R4, #0x1E]")
            b.insn("MOV", "R0, #0x80")
            b.insn("STR", "R0, [R7, #0x70]")
            b.label("st1")
            b.call_addr(ADD_FROM_DECK_RES, R4, R6, via=R3)
            b.label("ret")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def cr_crit_stub() -> EffectBuilder:
            """Ogier's c2h shape: Deck worker 0x0223BC3C (flags 2), callback CR_CB."""
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2, R3, LR}")
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDR", "R0, [R2, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("LDRH", "R1, [R2, #0x0]")
            b.call_addr(CRIT_WORKER, R0, R1, CRL['CB'] | 1, 0)
            b.insn("POP", "{R1, R2, R3, PC}")
            return b


        def cr_cb_stub() -> EffectBuilder:
            """[sp] = &card word: acting desc stage 0 -> Equip Spell (race 23 && spell type 3); else a Warrior (race 15)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("LDR", "R0, [SP, #0xC]")
            b.insn("LDR", "R4, [R0, #0x0]")
            b.insn("LSL", "R4, R4, #0x12")
            b.insn("LSR", "R4, R4, #0x12")
            b.ldr_const(0, ACTING_DESC_P)
            b.insn("LDR", "R5, [R0, #0x50]")
            b.insn("MOV", "R1, #0x0")
            b.insn("CMP", "R5, #0x0")
            b.insn("BEQ", "st")
            b.insn("LDRB", "R1, [R5, #0x1E]")
            b.label("st")
            b.insn("ADD", "R5, R1, #0x0")
            b.call("get_race", R4, via=R3)
            b.insn("CMP", "R5, #0x0")
            b.insn("BNE", "war")
            b.insn("CMP", f"R0, #0x{RACE_SPELL:X}")
            b.insn("BNE", "no")
            b.call_addr(GET_SPELLTYPE, R4, via=R3)
            b.insn("CMP", f"R0, #0x{SPELL_EQUIP:X}")
            b.insn("BNE", "no")
            b.insn("B", "yes")
            b.label("war")
            b.insn("CMP", f"R0, #0x{RACE_WARRIOR:X}")
            b.insn("BNE", "no")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def _cr_gy(b: EffectBuilder, other: str) -> None:
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xE")
            b.insn("BNE", f"{other}")


        def cr_resw_stub() -> EffectBuilder:
            b = EffectBuilder()
            _cr_gy(b, "ep")
            b.ldr_const(3, CRL['C2RES'] | 1)
            b.insn("BX", "R3")
            b.label("ep")
            b.ldr_const(3, CRL['RES2'] | 1)
            b.insn("BX", "R3")
            return b


        def cr_filt_stub() -> EffectBuilder:
            b = EffectBuilder()
            _cr_gy(b, "zero")
            b.ldr_const(3, VYLON_FILTER)
            b.insn("BX", "R3")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b


        def cr_slot5_stub() -> EffectBuilder:
            b = EffectBuilder()
            _cr_gy(b, "one")
            b.ldr_const(3, VYLON_SLOT5)
            b.insn("BX", "R3")
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            return b


        def cr_condx_stub() -> EffectBuilder:
            """zone 0x10 -> the End-Phase condition; GY (0x0E) GY action, ANY event code (own-turn menu passes 0, the
            opponent's-turn 0xFFFE enumeration passes 7 -- measured over .ml3 2026-10-22): either player's Main Phase
            ([0x0229DD14+0x48] 2 or 4), C2 OPT 0x2FEB clear, Vylon f1 (still in the GY + free S/T zone) and f2 (>= 1 legal
            +08 target = a Warrior you control) -> 1 (the +08 sweep then finds that target).  Else 0."""
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0x10")
            b.insn("BNE", "gy")
            b.ldr_const(3, CRL['COND2'] | 1)
            b.insn("BX", "R3")
            b.label("gy")
            b.insn("CMP", "R3, #0xE")
            b.insn("BNE", "z")
            b.ldr_const(3, 0x0229dd14)
            b.insn("LDR", "R3, [R3, #0x48]")
            b.insn("CMP", "R3, #0x2")
            b.insn("BEQ", "mp")
            b.insn("CMP", "R3, #0x4")
            b.insn("BNE", "z")
            b.label("mp")
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            _used(b, CR_C2KEY, "r4", "no")
            b.call_addr(VYLON_F1, R4, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(VYLON_F2, R4, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("z")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b


        def cr_c2res_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, CR_C2KEY, "r4", "zero")
            _post(b, CR_C2KEY)
            b.label("nat")
            b.call_addr(EQUIP_FROM_GY_RES, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def cr_speed_stub() -> EffectBuilder:
            """BL'd from the speed lookup's default leaf 0x021A894C (r0 = desc, r2 = cid, lr = 0x021A8951; Overtex's
            contract): Captain Roland's GY descriptor -> 2 (Quick Effect); everything else -> Overtex's stub, intact."""
            b = EffectBuilder()
            b.ldr_const(3, CAPROL)
            b.insn("CMP", "R2, R3")
            b.insn("BNE", "next")
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xE")
            b.insn("BNE", "next")
            b.insn("MOV", "R0, #0x2")
            b.insn("BX", "LR")
            b.label("next")
            b.ldr_const(3, O5.CAVE_OQ_SPEED | 1)
            b.insn("BX", "R3")
            return b


        def cr_spd9_stub() -> EffectBuilder:
            """BL over `bl 0x0202345C` (r0 = row cid; the caller compares the result with 2): 0x0FEB -> 2, else the native."""
            b = EffectBuilder()
            b.ldr_const(1, CAPROL)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "nat")
            b.insn("MOV", "R0, #0x2")
            b.insn("BX", "LR")
            b.label("nat")
            b.ldr_const(1, NATIVE_SPEED)
            b.insn("BX", "R1")
            return b


        CRSTUBS = {"FRONT": cr_front_stub, "COND1": cr_cond1_stub, "RES1": cr_res1_stub, "COND2": cr_cond2_stub,
                  "RES2": cr_res2_stub, "CRIT": cr_crit_stub, "CB": cr_cb_stub, "RESW": cr_resw_stub, "FILT": cr_filt_stub,
                  "CONDX": cr_condx_stub, "SLOT5": cr_slot5_stub, "C2RES": cr_c2res_stub, "SPEED": cr_speed_stub,
                  "SPD9": cr_spd9_stub}


        def apply_caprol(rom, ov: bytearray) -> None:
            from otn_enhanced.effects import summon_trigger_hook as sth
            from otn_enhanced.cards.junk_speeder import LIST_A, LIST_MIN3
            from otn_enhanced.effects import cave3 as _c3
            insert_row(ov, CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, CR_CLS1_REC, CR_CLS1_PHANTOM, "CR C1 cls1 (Synchro trigger)")
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, CR_CLS2_REC, CR_CLS2_PHANTOM, "CR C1 cls2 (End Phase)")
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, CR_CRIT_REC, CR_CRIT_PHANTOM, "CR criteria row")
            o = EPREG_BASE + CR_EP_ROW * 8 - RAM_BASE
            assert struct.unpack_from("<II", ov, o) in (CR_EP_NATIVE, CR_EP_REC), "CR End-Phase row 99 moved"
            struct.pack_into("<II", ov, o, *CR_EP_REC)
            f = CR_FUSION_ROW - RAM_BASE
            row = struct.unpack_from("<4H", ov, f)
            assert row in (CR_FUSION_STOCK, (CAPROL, CR_FUSION_DEAD, CR_FUSION_DEAD, 0)), f"CR fusion row {row}"
            struct.pack_into("<2H", ov, f + 2, CR_FUSION_DEAD, CR_FUSION_DEAD)
            for base, n in (LIST_A, LIST_MIN3):
                assert CAPROL not in [struct.unpack_from("<H", ov, base + 2 * i - RAM_BASE)[0] for i in range(n)], \
                    f"CR 0x0FEB joined material-count list {base:#x}"
            s = sth.TRIG_SITE - RAM_BASE
            assert bytes(ov[s:s + 4]) in (_bl(sth.TRIG_SITE, _c3.CAVE3_SUMMONTRIG), _bl(sth.TRIG_SITE, CRL["FRONT"])), \
                "CR proper-Summon site is not the shared cave3 stub's BL"
            ov[s:s + 4] = _bl(sth.TRIG_SITE, CRL["FRONT"])
            insert_row(ov, GRANT_BASE, GRANT_COUNT, 6, "<Hhh", CR_GRANT_REC, CR_GRANT_PHANTOM, "CR equip grant row")
            s = SPEED_LEAF - RAM_BASE
            assert bytes(ov[s:s + 4]) in (_bl(SPEED_LEAF, O5.CAVE_OQ_SPEED), _bl(SPEED_LEAF, CRL["SPEED"])), \
                "CR speed leaf is not Overtex's BL"
            ov[s:s + 4] = _bl(SPEED_LEAF, CRL["SPEED"])
            for site in SPD9_SITES:
                s = site - RAM_BASE
                assert bytes(ov[s:s + 4]) in (_bl(site, NATIVE_SPEED & ~1), _bl(site, CRL["SPD9"])), \
                    f"CR enumerator speed prefilter {site:#x} is not the native BL"
                ov[s:s + 4] = _bl(site, CRL["SPD9"])
            print("CR cls1 + cls2 + criteria rows, End-Phase row 99, fusion recipe A[8] killed, trigger + speed fronts")


        def apply_caprol_identity(out: str) -> None:
            """card_prop <- Formula Synchron's whole record (cid swapped); genre: clear 29 FUSION, set 36 SYNCHRO."""
            import ndspy.rom
            from otn_enhanced.data.card_stats import find_pac as _find_pac
            rom = ndspy.rom.NintendoDSRom.fromFile(out)
            fid, orig, archive = _find_pac(rom)
            pac = bytearray(orig)
            files = {f.get_clean_name().lower(): f for f in archive.files}
            cp, gn = files["card_prop.bin"], files["card_genre.bin"]
            n = (cp.size - 8) // 8

            def prop_at(cid):
                hits = [i for i in range(n)
                        if int.from_bytes(pac[cp.address + 8 + i * 8:cp.address + 16 + i * 8], "little") & 0x3FFF == cid]
                assert len(hits) == 1, f"{cid:#x}: {hits}"
                return hits[0]

            want_type = ERA2_CARD_TYPE_REVERSE["Synchro Tuner Effect Monster"]
            i, r = prop_at(CAPROL), prop_at(CR_REF_SYNCHRO_TUNER)
            ref = int.from_bytes(pac[cp.address + 8 + r * 8:cp.address + 16 + r * 8], "little")
            assert (ref >> 32) & 0x3F == want_type, "CR reference is not a Synchro Tuner Effect Monster"
            po, go = cp.address + 8 + i * 8, gn.address + 8 + i * 8
            if (int.from_bytes(pac[po:po + 8], "little") >> 32) & 0x3F != want_type:
                pac[po:po + 8] = ((ref & ~0x3FFF) | CAPROL).to_bytes(8, "little")
            g = int.from_bytes(pac[go:go + 8], "little")
            pac[go:go + 8] = ((g & ~(1 << 29)) | (1 << 36)).to_bytes(8, "little")
            rom.files[fid] = bytes(pac)
            rom.saveToFile(out)
            print(f"CR card_prop[{i}] <- Formula Synchron template; genre {g:#x} -> {(g & ~(1 << 29)) | (1 << 36):#x}")


        def verify_caprol(rom, ov, check) -> None:
            from otn_enhanced.effects import summon_trigger_hook as sth
            for label, base, count, stride, fmt, rec in (("cls1", CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, CR_CLS1_REC),
                                                         ("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, CR_CLS2_REC),
                                                         ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, CR_CRIT_REC)):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == CAPROL] == [rec], f"CR {label}: exactly one 0x0feb row = {rec}")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"CR {label}: sorted")
            check(struct.unpack_from("<II", ov, EPREG_BASE + CR_EP_ROW * 8 - RAM_BASE) == CR_EP_REC, "CR End-Phase row 99")
            check(struct.unpack_from("<4H", ov, CR_FUSION_ROW - RAM_BASE) == (CAPROL, CR_FUSION_DEAD, CR_FUSION_DEAD, 0),
                  "CR fusion recipe A[8] materials dead")
            check(_bl_target(ov, sth.TRIG_SITE) == CRL["FRONT"], "CR proper-Summon site -> Captain Roland front")
            check(code_reaches(rom, SPEED_LEAF, CRL["SPEED"]), "CR speed leaf reaches Captain Roland front (-> Overtex)")
            for site in SPD9_SITES:
                check(_bl_target(ov, site) == CRL["SPD9"], f"CR GY enumerator speed prefilter @{site:#x} -> front")
            rows = _rows(ov, GRANT_BASE, GRANT_COUNT, 6, "<Hhh")
            check([r for r in rows if r[0] == CAPROL] == [CR_GRANT_REC], "CR equip grant row {0x0FEB, 500, 0}")


        # =================================================================================================
        # card 11: Labyrinth Tank 0x1118 -> Infernoble Knight Captain Oliver (notes/infernoble-captain-oliver-findings.md)
        #   Identity: Captain Roland's recipe with a plain Synchro reference (Laval Twin Slayer 0x23FE); recipe A[21] killed.
        #   C1 "When this card declares an attack while equipped: You can target 1 face-up card on the field; destroy it":
        #      attack-declaration list 0x0226E740 (x0x11, read @0x021C637A) over phantom 0x0E11 + cls1 {Catsith's destroy
        #      0x02204899, filter 0x021E3BD5 (face-up card), CO_C1COND (equipped), "You can", target 0x02234DA5}.
        #   C2 GY ignition, own Main Phase, not the turn sent to the GY: target a Warrior you control; SS this card as a Tuner,
        #      then equip that monster to it (+500): Bradamante's GY self-SS + desc re-point + Allure 0x0220BFFD; Tuner latch
        #      front; "sent this turn" = leave-switch front marker; +500 = front at the recompute's equip-bonus site 0x021B7088.
        # =================================================================================================
        CAPOLI = 0x1118
        CO_C2KEY, CO_SENTKEY = 0x2000 | CAPOLI, 0x6000 | CAPOLI
        CO_REF_SYNCHRO = 0x23FE                                            # Laval Twin Slayer (Junk Speeder's reference)
        CO_FUSION_ROW, CO_FUSION_STOCK = 0x02270C3C, (CAPOLI, 0x1142, 0x11A6, 0)
        ATKLIST_BASE, ATKLIST_COUNT, CO_ATK_PHANTOM = 0x0226E740, 0x11, 0x0E11
        CATSITH_RES, CATSITH_FILT, CATSITH_TSTEP = 0x02204899, 0x021E3BD5, 0x02234DA5
        STAT_SITE, STAT_STOCK = 0x021B7088, bytes.fromhex("3949281c")      # ldr r1,=0x0226DFB0 ; adds r0,r5,#0
        for _v in (CATSITH_RES, CATSITH_FILT, CATSITH_TSTEP):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        COL = {n: getattr(O5, f"CAVE_IK_CO_{n}") for n in ("C1COND", "C2COND", "C2RES", "C2FILT", "LATCH", "LEAVE", "STAT")}
        CORESERVE = {"C1COND": 0x60, "C2COND": 0xA0, "C2RES": 0xC0, "C2FILT": 0x50, "LATCH": 0x50, "LEAVE": 0x50, "STAT": 0x60}
        CO_CLS1_PHANTOM, CO_CLS2_PHANTOM = 0x0E6D, 0x0E4A
        CO_CLS1_REC = (CAPOLI, 0, CATSITH_RES, CATSITH_FILT, COL["C1COND"] | 1, TAG_YOU_CAN, CATSITH_TSTEP)
        CO_CLS2_REC = (CAPOLI, 0, COL["C2RES"] | 1, COL["C2FILT"] | 1, COL["C2COND"] | 1, 0, ALLURE_TSTEP)


        def _co_equipped(b: EffectBuilder, yes: str, no: str) -> None:
            """r6 = this card's (zone<<8|side) locator: an S/T card on either side whose equip target is r6 -> *yes*.
            Uses r0-r5; r6 preserved."""
            b.insn("MOV", "R4, #0x0")
            b.label("eqs")
            b.insn("MOV", "R5, #0x5")
            b.label("eqz")
            b.call_addr(CARD_CID_AT, R4, R5, via=R2)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "eqn")
            b.call_addr(EQUIP_TARGET_OF, R4, R5, via=R2)
            b.insn("CMP", "R0, R6")
            b.insn("BEQ", f"{yes}")
            b.label("eqn")
            b.insn("ADD", "R5, #0x1")
            b.insn("CMP", "R5, #0x9")
            b.insn("BLE", "eqz")
            b.insn("ADD", "R4, #0x1")
            b.insn("CMP", "R4, #0x1")
            b.insn("BLE", "eqs")
            b.insn("B", f"{no}")


        def co_c1cond_stub() -> EffectBuilder:
            """cls1 +0C (attack declared): this card on the field with an Equip Card equipped to it -> 1 (+08 target sweep)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("LDRH", "R0, [R0, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R6, R0, #0x10")
            b.insn("LSR", "R6, R6, #0x10")
            b.insn("LSR", "R1, R6, #0x8")
            b.insn("CMP", "R1, #0x5")
            b.insn("BGE", "no")
            _co_equipped(b, "yes", "no")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def co_c2cond_stub() -> EffectBuilder:
            """cls2 +0C, GY: own turn + Main Phase, OPT 0x3118 clear, NOT the turn sent to the GY (marker 0x7118 kind 1),
            may SS, free MZ, free S/T -> 1 (the GY-action offer only runs for a card in the GY)."""
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x3]")
            b.insn("CMP", "R3, #0xE")
            b.insn("BNE", "z")
            b.ldr_const(3, 0x0229dd14)
            b.insn("LDR", "R2, [R3, #0x34]")
            b.insn("LDRB", "R1, [R0, #0x2]")
            b.insn("CMP", "R2, R1")
            b.insn("BNE", "z")
            b.insn("LDR", "R3, [R3, #0x48]")
            b.insn("CMP", "R3, #0x2")
            b.insn("BEQ", "mp")
            b.insn("CMP", "R3, #0x4")
            b.insn("BNE", "z")
            b.label("mp")
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            _used(b, CO_C2KEY, "r4", "no")
            _used(b, CO_SENTKEY, "r4", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(CAN_SS, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_MZ, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_ST, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("z")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b


        def co_c2filt_stub() -> EffectBuilder:
            """+08 (desc, side, zone): a face-up monster of desc[+2]'s side that is a Warrior."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("CMP", "R5, R0")
            b.insn("BNE", "no")
            b.insn("CMP", "R6, #0x4")
            b.insn("BGT", "no")
            b.call_addr(FACE_UP, R5, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(CARD_CID_AT, R5, R6, via=R3)
            b.call("get_race", via=R3)
            b.insn("CMP", f"R0, #0x{RACE_WARRIOR:X}")
            b.insn("BNE", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def co_c2res_stub() -> EffectBuilder:
            """Bradamante's BR_C2RES with the OPT key 0x3118 and the Tuner latch byte armed before the GY self-SS."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(7, 0x0229aafc)
            b.insn("LDR", "R0, [R7, #0x70]")
            b.insn("CMP", "R0, #0x91")
            b.insn("BEQ", "p91")
            b.insn("CMP", "R0, #0x92")
            b.insn("BEQ", "p92")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "allure")
            b.insn("LDRB", "R0, [R4, #0x1E]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "allure")
            _used(b, CO_C2KEY, "r4", "zero")
            _post(b, CO_C2KEY)
            b.insn("MOV", "R0, #0x1")
            b.insn("STRB", "R0, [R4, #0x1E]")
            b.ldr_const(0, O5.CAVE_IK_CO_ARM)
            b.insn("MOV", "R1, #0x1")
            b.insn("STRB", "R1, [R0, #0x0]")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.call_addr(GY_SELF_SS, R4, R6, via=R3)
            b.insn("MOV", "R0, #0x91")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("p91")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("MOV", "R0, #0x92")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("p92")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R1, R0, #0x10")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("CMP", "R1, #0x5")
            b.insn("BGE", "zero")
            b.insn("STRB", "R1, [R4, #0x3]")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.insn("LSL", "R0, R0, #0x3")
            b.ldr_const(2, 0x0229c33c)
            b.insn("LDR", "R0, [R2, R0]")
            b.insn("LSL", "R0, R0, #0xB")
            b.insn("LSR", "R0, R0, #0x1E")
            b.insn("STRB", "R0, [R4, #0xE]")
            b.insn("MOV", "R0, #0x80")
            b.insn("STR", "R0, [R7, #0x70]")
            b.label("allure")
            b.call_addr(ALLURE_RES, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def co_leave_stub() -> EffectBuilder:
            """BL @0x021C8216 (leave switch; r4 = cid; [sp+0x144] = destination is the GY, read before any push): 0x1118
            going to the GY -> post the 'sent this turn' marker {0x7118, kind 1} on [sp+0x98]'s side, then replay the displaced
            `movs r1,#0x77 ; lsls r1,#6` and return (= the T.G. trampoline's own non-member path; 0x1118 is in neither
            Bradamante's front nor the T.G. list).  Every other cid tail-jumps to Bradamante's front, lr intact."""
            b = EffectBuilder()
            b.ldr_const(1, CAPOLI)
            b.insn("CMP", "R4, R1")
            b.insn("BNE", "next")
            b.insn("LDR", "R1, [SP, #0x144]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "next")
            b.insn("PUSH", "{R0, R2, R3, R4, R5, R6, R7, LR}")
            b.insn("LDR", "R0, [SP, #0xB8]")
            b.turnlog_post(R0, CO_SENTKEY, 1, via=R4)
            b.insn("MOV", "R1, #0x77")
            b.insn("LSL", "R1, R1, #0x6")
            b.insn("POP", "{R0, R2, R3, R4, R5, R6, R7, PC}")
            b.label("next")
            b.ldr_const(1, BRL['LEAVE'] | 1)
            b.insn("BX", "R1")
            return b


        def co_stat_stub() -> EffectBuilder:
            """BL over `ldr r1,=0x0226DFB0 ; adds r0,r5,#0` @0x021B7088 inside the stat recompute 0x021B44C0 (its frame:
            [sp+0xC] holder side, [sp+0x10] holder zone, [sp+0xB0] equip ATK accumulator; r5 = this equip card's cid).
            Holder cid 0x1118 or 0x17EF (Emperor Charles) and the equip card a MONSTER (race < 23) -> [sp+0xB0] += 500.
            Then replay the pair."""
            b = EffectBuilder()
            b.insn("PUSH", "{R2, R3, R4, R6, R7, LR}")
            b.insn("LDR", "R0, [SP, #0x24]")
            b.insn("LDR", "R1, [SP, #0x28]")
            b.call_addr(CARD_CID_AT, via=R3)
            b.ldr_const(1, CAPOLI)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "hold")
            b.ldr_const(1, CHARLES)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "done")
            b.label("hold")
            b.call("get_race", R5, via=R3)
            b.insn("CMP", f"R0, #0x{RACE_SPELL:X}")
            b.insn("BGE", "done")
            b.insn("LDR", "R0, [SP, #0xC8]")
            b.insn("MOV", "R1, #0x7D")
            b.insn("LSL", "R1, R1, #0x2")
            b.insn("ADD", "R0, R0, R1")
            b.insn("STR", "R0, [SP, #0xC8]")
            b.label("done")
            b.insn("ADD", "R0, R5, #0x0")
            b.ldr_const(1, 0x0226dfb0)
            b.insn("POP", "{R2, R3, R4, R6, R7, PC}")
            return b


        COSTUBS = {"C1COND": co_c1cond_stub, "C2COND": co_c2cond_stub, "C2RES": co_c2res_stub, "C2FILT": co_c2filt_stub,
                  "LATCH": lambda: _latch_stub(O5.CAVE_IK_CO_ARM, CAPOLI, RCL["LATCH"]), "LEAVE": co_leave_stub,
                  "STAT": co_stat_stub}


        def apply_capoli(rom, ov: bytearray) -> None:
            from otn_enhanced.effects import summon_rider_hook as rh
            from otn_enhanced.effects.common import list_insert as _list_insert
            from otn_enhanced.cards.junk_speeder import LIST_A, LIST_MIN3
            insert_row(ov, CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, CO_CLS1_REC, CO_CLS1_PHANTOM, "CO C1 cls1 (attack declared)")
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, CO_CLS2_REC, CO_CLS2_PHANTOM, "CO C2 cls2 (GY)")
            _list_insert(ov, ATKLIST_BASE, ATKLIST_COUNT, CAPOLI, CO_ATK_PHANTOM, "CO attack-declaration list")
            f = CO_FUSION_ROW - RAM_BASE
            row = struct.unpack_from("<4H", ov, f)
            assert row in (CO_FUSION_STOCK, (CAPOLI, CR_FUSION_DEAD, CR_FUSION_DEAD, 0)), f"CO fusion row {row}"
            struct.pack_into("<2H", ov, f + 2, CR_FUSION_DEAD, CR_FUSION_DEAD)
            for base, n in (LIST_A, LIST_MIN3):
                assert CAPOLI not in [struct.unpack_from("<H", ov, base + 2 * i - RAM_BASE)[0] for i in range(n)]
            for site, wants, dst in ((rh.RIDER_SITE, (RCL["LATCH"],), COL["LATCH"]),
                                     (LEAVE_SITE, (BRL["LEAVE"],), COL["LEAVE"])):
                assert _bl_target(ov, site) in wants + (dst,), f"CO site {site:#x} -> {_bl_target(ov, site):#x}"
                ov[site - RAM_BASE:site - RAM_BASE + 4] = _bl(site, dst)
            o = STAT_SITE - RAM_BASE
            assert bytes(ov[o:o + 4]) in (STAT_STOCK, _bl(STAT_SITE, COL["STAT"])), "CO stat site not stock"
            ov[o:o + 4] = _bl(STAT_SITE, COL["STAT"])
            print("CO cls1 + cls2 + attack list, recipe A[21] killed, latch / leave / stat fronts")


        def apply_capoli_identity(out: str) -> None:
            _synchro_identity(out, CAPOLI, CO_REF_SYNCHRO, "CO")


        def _synchro_identity(out: str, cid: int, ref_cid: int, tag: str) -> None:
            """card_prop <- a plain Synchro Effect Monster's whole record (cid swapped); genre: clear 29 FUSION, set 36."""
            import ndspy.rom
            from otn_enhanced.data.card_stats import find_pac as _find_pac
            rom = ndspy.rom.NintendoDSRom.fromFile(out)
            fid, orig, archive = _find_pac(rom)
            pac = bytearray(orig)
            files = {f.get_clean_name().lower(): f for f in archive.files}
            cp, gn = files["card_prop.bin"], files["card_genre.bin"]
            n = (cp.size - 8) // 8

            def prop_at(cid):
                hits = [i for i in range(n)
                        if int.from_bytes(pac[cp.address + 8 + i * 8:cp.address + 16 + i * 8], "little") & 0x3FFF == cid]
                assert len(hits) == 1, f"{cid:#x}: {hits}"
                return hits[0]

            want_type = ERA2_CARD_TYPE_REVERSE["Synchro Effect Monster"]
            i, r = prop_at(cid), prop_at(ref_cid)
            ref = int.from_bytes(pac[cp.address + 8 + r * 8:cp.address + 16 + r * 8], "little")
            assert (ref >> 32) & 0x3F == want_type, f"{tag} reference is not a Synchro Effect Monster"
            po, go = cp.address + 8 + i * 8, gn.address + 8 + i * 8
            if (int.from_bytes(pac[po:po + 8], "little") >> 32) & 0x3F != want_type:
                pac[po:po + 8] = ((ref & ~0x3FFF) | cid).to_bytes(8, "little")
            g = int.from_bytes(pac[go:go + 8], "little")
            pac[go:go + 8] = ((g & ~(1 << 29)) | (1 << 36)).to_bytes(8, "little")
            rom.files[fid] = bytes(pac)
            rom.saveToFile(out)
            print(f"{tag} card_prop[{i}] <- {ref_cid:#x} template; genre {g:#x} -> {(g & ~(1 << 29)) | (1 << 36):#x}")


        def verify_capoli(rom, ov, check) -> None:
            from otn_enhanced.effects import summon_rider_hook as rh
            for label, base, count, stride, fmt, rec in (("cls1", CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, CO_CLS1_REC),
                                                         ("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, CO_CLS2_REC)):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == CAPOLI] == [rec], f"CO {label}: exactly one 0x1118 row")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"CO {label}: sorted")
            al = [struct.unpack_from("<H", ov, ATKLIST_BASE + 2 * i - RAM_BASE)[0] for i in range(ATKLIST_COUNT)]
            check(CAPOLI in al and CO_ATK_PHANTOM not in al and al == sorted(al), "CO attack-declaration list: 0x1118 in")
            check(struct.unpack_from("<4H", ov, CO_FUSION_ROW - RAM_BASE) == (CAPOLI, CR_FUSION_DEAD, CR_FUSION_DEAD, 0),
                  "CO fusion recipe A[21] dead")
            for site, dst in ((rh.RIDER_SITE, COL["LATCH"]), (LEAVE_SITE, COL["LEAVE"]), (STAT_SITE, COL["STAT"])):
                ok = LEAVE_FRONTS if site == LEAVE_SITE else (dst,)    # the Arms front the leave switch ahead of it
                check(O5.dc_skip(_bl_target(ov, site)) in ok, f"CO bl @{site:#x} -> {dst:#x}")

        # =================================================================================================
        # card 12: Master of Oz 0x17EF -> Infernoble Knight Emperor Charles (notes/infernoble-emperor-charles-findings.md)
        #   Identity: Captain Oliver's recipe (Laval Twin Slayer 0x23FE reference); recipe A[73] killed.
        #   ONE cls1 record (a 2nd cls1 is Spirit-only) over phantom 0x1337, mode-switched on desc[+4]:
        #   C1 event 0x19 "an Equip Card becomes equipped to a monster": front at the cid compare 0x021C4B4E inside the one
        #      equip routine 0x021C4A68 posts 0x021D3230(side, zone, 0x19, target<<16 | equip) -- Gearfried the Iron Knight's
        #      own post -- to every face-up 0x17EF on either side.  Effect = Dark Voltanis's non-target destroy record
        #      {0x02204899, 0x021DE5A9, -, -, 0x02234DA5}; OPT 0x57EF stamped at resolution.
        #   C2 event 6 from End-Phase row 198 {0x02253F89, 0x1337 -> 0x17EF} (Genex Neutron's on-field poster): Vylon Sigma's
        #      pick / zone / move / link machine, stage A an "appropriate" Equip Spell from the hand or GY (The Kick Man's
        #      word 0x10204 + legality callback 0x0223E395), stage B (Yes/No) a FIRE Warrior from the Deck (source 0xD, link
        #      kind 0xA -- was 0xC until, which skipped the +500); +500 = Captain Oliver's stat front.  OPT 0x37EF.
        # =================================================================================================
        CHARLES = 0x17EF
        CH_C1KEY, CH_C2KEY = 0x4000 | CHARLES, 0x2000 | CHARLES
        CH_FUSION_ROW, CH_FUSION_STOCK = 0x02270DDC, (CHARLES, 0x16B6, 0x16B7, 0)
        CH_EP_ROW, CH_EP_NATIVE, CH_EP_REC = 198, (0x02253F89, 0x1337), (0x02253F89, CHARLES)
        EQTRIG_SITE, EQTRIG_STOCK = 0x021C4B4E, bytes.fromhex("22498842")    # ldr r1,=0x13C3 ; cmp r0,r1
        FACE_CID_AT, POST_TRIG, VOLT_FILT, VALIDATE = 0x021AC005, 0x021D3230, 0x021DE5A9, 0x021D2C1D
        ZONE_UI, MOVER, EQUIP_LINK, ZONE_PICK = 0x0225BDD9, 0x021C7485, 0x021C4A69, 0x0229DE54
        MSG_EQUIP, KICKMAN_WORD, EV_EQUIPPED, EV_ENDPHASE = 0x5E, 0x10204, 0x19, 6
        for _v in (FACE_CID_AT, VOLT_FILT, VALIDATE, ZONE_UI, MOVER, EQUIP_LINK):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        CHL = {n: getattr(O5, f"CAVE_IK_CH_{n}") for n in ("EQ", "COND", "FILT", "SLOT5", "RESW", "C2RES", "CRIT")}
        CHRESERVE = {"EQ": 0x50, "COND": 0x80, "FILT": 0x20, "SLOT5": 0x20, "RESW": 0x60, "C2RES": 0x1c0, "CRIT": 0x70}
        CH_CLS1_PHANTOM, CH_CRIT_PHANTOM = 0x1337, 0x0E9C
        CH_CLS1_REC = (CHARLES, 0, CHL["RESW"] | 1, CHL["FILT"] | 1, CHL["COND"] | 1, TAG_YOU_CAN, CHL["SLOT5"] | 1)
        CH_CRIT_REC = (CHARLES, 0xFFFF, CHL["CRIT"] | 1, 0x00000000)         # CH_CRIT picks the word from the param


        def ch_eq_stub() -> EffectBuilder:
            """BL over `ldr r1,=0x13C3 ; cmp r0,r1` @0x021C4B4E (r0 = the equipped monster's cid, r6 = equip loc, r7 = target
            loc; r2/r3 dead): post the 'equipped' cls1 event to each face-up 0x17EF, then replay the pair (flags live)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R0, R4, R5, LR}")
            b.insn("MOV", "R4, #0x0")
            b.label("s")
            b.insn("MOV", "R5, #0x0")
            b.label("z")
            b.call_addr(FACE_CID_AT, R4, R5, CHARLES, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "n")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.insn("MOV", f"R2, #0x{EV_EQUIPPED:X}")
            b.insn("LSL", "R3, R7, #0x10")
            b.insn("ORR", "R3, R6")
            b.call_addr(POST_TRIG)
            b.label("n")
            b.insn("ADD", "R5, #0x1")
            b.insn("CMP", "R5, #0x4")
            b.insn("BLE", "z")
            b.insn("ADD", "R4, #0x1")
            b.insn("CMP", "R4, #0x1")
            b.insn("BLE", "s")
            b.ldr_const(1, 0x13c3)
            b.insn("LDR", "R0, [SP, #0x0]")
            b.insn("CMP", "R0, R1")
            b.insn("POP", "{R0, R4, R5, PC}")
            return b


        def _ch_loc(b: EffectBuilder) -> None:
            """r0 <- this card's (zone<<8 | side) from desc r4."""
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("LSR", "R0, R0, #0x10")


        def ch_cond_stub() -> EffectBuilder:
            """+0C: event 0x19 -> C1 OPT clear -> 2.  Event 6 (End Phase, face-up via the poster) -> C2 OPT clear, a free S/T
            zone and >= 1 appropriate Equip Spell in the hand / GY -> 2.  Else 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("CMP", f"R0, #0x{EV_EQUIPPED:X}")
            b.insn("BNE", "c2")
            _used(b, CH_C1KEY, "r4", "no")
            b.insn("B", "yes")
            b.label("c2")
            b.insn("CMP", f"R0, #0x{EV_ENDPHASE:X}")
            b.insn("BNE", "no")
            _used(b, CH_C2KEY, "r4", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_ST, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")
            _ch_loc(b)
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(ROW_COUNT_C, R0, CHARLES, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.label("yes")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def ch_filt_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x4]")
            b.insn("CMP", f"R3, #0x{EV_EQUIPPED:X}")
            b.insn("BNE", "z")
            b.ldr_const(3, VOLT_FILT)
            b.insn("BX", "R3")
            b.label("z")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b


        def ch_slot5_stub() -> EffectBuilder:
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #0x4]")
            b.insn("CMP", f"R3, #0x{EV_EQUIPPED:X}")
            b.insn("BNE", "one")
            b.ldr_const(3, CATSITH_TSTEP)
            b.insn("BX", "R3")
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            return b


        def ch_resw_stub() -> EffectBuilder:
            """Event 0x19: phase 0x80 C1 OPT check + stamp, then Voltanis's destroy 0x02204899.  Else the C2 machine."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("CMP", f"R0, #0x{EV_EQUIPPED:X}")
            b.insn("BNE", "c2")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, CH_C1KEY, "r4", "zero")
            _post(b, CH_C1KEY)
            b.label("nat")
            b.ldr_const(3, CATSITH_RES)
            b.insn("B", "go")
            b.label("c2")
            b.ldr_const(3, CHL['C2RES'] | 1)
            b.label("go")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.insn("BLX", "R3")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def ch_c2res_stub() -> EffectBuilder:
            """Phases on [0x0229AAFC+0x70] (Vylon Sigma's machine twice; stage B = the same four steps 6 lower):
               0x80 chain push; OPT 0x37EF check + stamp; still on the field, free S/T, >= 1 Equip Spell -> message 0x5E -> 0x7F
               0x7F/0x79 picker (param = loc, | 0x10000 = Deck mode) | 0x7E/0x78 readback -> desc[+0x1C]; zone UI
               0x7D/0x77 move (hand 0xB / GY 0xE, Deck 0xD) | 0x7C/0x76 equip link (kind 0xA for both: 0xC skips the stat loop's equip path, user 2026-10-27)
               0x7B free S/T + >= 1 FIRE Warrior in the Deck -> Yes/No 0xFA | 0x7A Yes -> message 0x5E -> 0x79
               0x76 link -> 0x71 | 0x71 chain pop -> 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "d1")
            b.insn("B", "p80")
            b.label("d1")
            b.insn("CMP", "R0, #0x7B")
            b.insn("BNE", "d2")
            b.insn("B", "p7b")
            b.label("d2")
            b.insn("CMP", "R0, #0x7A")
            b.insn("BNE", "d3")
            b.insn("B", "p7a")
            b.label("d3")
            b.insn("MOV", "R7, #0x0")
            b.insn("CMP", "R0, #0x7B")
            b.insn("BGE", "st")
            b.insn("MOV", "R7, #0x1")
            b.insn("ADD", "R0, #0x6")
            b.label("st")
            b.insn("CMP", "R0, #0x7F")
            b.insn("BEQ", "pick")
            b.insn("CMP", "R0, #0x7E")
            b.insn("BEQ", "read")
            b.insn("CMP", "R0, #0x7D")
            b.insn("BEQ", "move")
            b.insn("CMP", "R0, #0x7C")
            b.insn("BNE", "d4")
            b.insn("B", "link")
            b.label("d4")
            b.insn("B", "p71")
            b.label("pick")
            _ch_loc(b)
            b.insn("LSL", "R3, R7, #0x10")
            b.insn("ORR", "R3, R0")
            b.call_addr(AS_PICKER, R5, 6, CHARLES, via=R7)
            b.insn("B", "next")
            b.label("read")
            b.call_addr(AS_READBACK, via=R3)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R2, R0, R1")
            b.insn("STRH", "R2, [R4, #0x1C]")
            b.call_addr(ZONE_UI, R5, R5, via=R3)
            b.insn("B", "next")
            b.label("move")
            b.insn("MOV", "R1, #0xD")
            b.insn("CMP", "R7, #0x0")
            b.insn("BNE", "mv")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x1C]")
            b.call_addr(HAND_INDEX, via=R3)
            b.insn("MOV", "R1, #0xB")
            b.insn("CMP", "R0, #0x0")
            b.insn("BGE", "mv")
            b.insn("MOV", "R1, #0xE")
            b.label("mv")
            b.ldr_const(0, ZONE_PICK)
            b.insn("LDRH", "R0, [R0, #0x24]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R2, [R4, #0x1C]")
            b.call_addr(MOVER, R0, R1, R2, R5, via=R7)
            b.insn("B", "next")
            b.label("link")
            _ch_loc(b)
            b.insn("ADD", "R2, R0, #0x0")
            b.ldr_const(0, ZONE_PICK)
            b.insn("LDRH", "R1, [R0, #0x24]")
            b.insn("LSL", "R1, R1, #0x18")
            b.insn("LSR", "R1, R1, #0x10")
            b.insn("ORR", "R1, R5")
            b.insn("MOV", "R3, #0xA")
            b.call_addr(EQUIP_LINK, R5, via=R7)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x7C")
            b.insn("BEQ", "next")
            b.insn("MOV", "R0, #0x71")
            b.insn("B", "ret")
            b.label("next")
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("SUB", "R0, #0x1")
            b.insn("B", "ret")
            b.label("p80")
            b.call_addr(CHAIN_PUSH, via=R3)
            _used(b, CH_C2KEY, "r4", "p71")
            _post(b, CH_C2KEY)
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.call_addr(VALIDATE, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "p71")
            b.insn("MOV", "R7, #0x0")
            b.bl_label("room")
            b.insn("BEQ", "p71")
            b.insn("B", "msg")
            b.label("p7b")
            b.insn("MOV", "R7, #0x1")
            b.bl_label("room")
            b.insn("BEQ", "p71")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("MOV", "R1, #0xFA")
            b.insn("LDRH", "R2, [R4, #0xC]")
            b.call_addr(AS_YESNO, via=R3)
            b.insn("MOV", "R0, #0x7A")
            b.insn("B", "ret")
            b.label("p7a")
            b.ldr_const(0, AS_UI)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "p71")
            b.label("msg")
            b.call_addr(AS_MESSAGE, R5, MSG_EQUIP, via=R3)
            b.insn("B", "next")
            b.label("p71")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("room")
            b.insn("PUSH", "{LR}")
            b.call_addr(FREE_ST, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "rz")
            _ch_loc(b)
            b.insn("LSL", "R2, R7, #0x10")
            b.insn("ORR", "R2, R0")
            b.call_addr(ROW_COUNT_C, R5, CHARLES, via=R3)
            b.insn("B", "rc")
            b.label("rz")
            b.insn("MOV", "R0, #0x0")
            b.label("rc")
            b.insn("CMP", "R0, #0x0")
            b.insn("POP", "{PC}")
            return b


        def ch_crit_stub() -> EffectBuilder:
            """Criteria handler (row r0, side r1, param r2): param bit 16 clear -> hand builder + GY worker, word 0x10204,
            callback 0x0223E395 with cb arg &param (= this card's loc: 'an Equip Spell that can equip to it'); set -> Deck
            worker, word FIRE Warrior, Ogier's C2CB excluding 0x17EF (an Extra Deck cid: keeps every candidate)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("SUB", "SP, #0x10")
            b.insn("STR", "R2, [SP, #0xC]")
            b.insn("ADD", "R4, R1, #0x0")
            b.insn("LDRH", "R5, [R0, #0x0]")
            b.insn("LSR", "R0, R2, #0x10")
            b.insn("BNE", "deck")
            b.bl_label("sp0")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.ldr_const(2, LEGAL_CB)
            b.insn("ADD", "R3, SP, #0xC")
            b.call_addr(AS_HAND_BUILDER, via=R6)
            b.insn("ADD", "R6, R0, #0x0")
            b.bl_label("sp0")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.ldr_const(2, LEGAL_CB)
            b.insn("ADD", "R3, SP, #0xC")
            b.call_addr(GY_WORKER)
            b.insn("ADD", "R0, R0, R6")
            b.insn("B", "out")
            b.label("deck")
            b.ldr_const(0, FIRE_WARRIOR)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.call_addr(CRIT_WORKER, R4, R5, L['C2CB'] | 1, CHARLES)
            b.label("out")
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("sp0")
            b.ldr_const(0, KICKMAN_WORD)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("BX", "LR")
            return b


        CHSTUBS = {"EQ": ch_eq_stub, "COND": ch_cond_stub, "FILT": ch_filt_stub, "SLOT5": ch_slot5_stub, "RESW": ch_resw_stub,
                  "C2RES": ch_c2res_stub, "CRIT": ch_crit_stub}


        def apply_charles(rom, ov: bytearray) -> None:
            from otn_enhanced.cards.junk_speeder import LIST_A, LIST_MIN3
            insert_row(ov, CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, CH_CLS1_REC, CH_CLS1_PHANTOM, "CH cls1 (C1 equip + C2 EP)")
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, CH_CRIT_REC, CH_CRIT_PHANTOM, "CH criteria row")
            o = EPREG_BASE + CH_EP_ROW * 8 - RAM_BASE
            assert struct.unpack_from("<II", ov, o) in (CH_EP_NATIVE, CH_EP_REC), "CH End-Phase row 198 moved"
            struct.pack_into("<II", ov, o, *CH_EP_REC)
            f = CH_FUSION_ROW - RAM_BASE
            row = struct.unpack_from("<4H", ov, f)
            assert row in (CH_FUSION_STOCK, (CHARLES, CR_FUSION_DEAD, CR_FUSION_DEAD, 0)), f"CH fusion row {row}"
            struct.pack_into("<2H", ov, f + 2, CR_FUSION_DEAD, CR_FUSION_DEAD)
            for base, n in (LIST_A, LIST_MIN3):
                assert CHARLES not in [struct.unpack_from("<H", ov, base + 2 * i - RAM_BASE)[0] for i in range(n)]
            o = EQTRIG_SITE - RAM_BASE
            assert bytes(ov[o:o + 4]) in (EQTRIG_STOCK, _bl(EQTRIG_SITE, CHL["EQ"])), "CH equip-routine site not stock"
            ov[o:o + 4] = _bl(EQTRIG_SITE, CHL["EQ"])
            print("CH cls1 + criteria rows, End-Phase row 198, recipe A[73] killed, equip-trigger front")


        def verify_charles(rom, ov, check) -> None:
            for label, base, count, stride, fmt, rec in (("cls1", CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, CH_CLS1_REC),
                                                         ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, CH_CRIT_REC)):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == CHARLES] == [rec], f"CH {label}: exactly one 0x17ef row")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"CH {label}: sorted")
            check(struct.unpack_from("<II", ov, EPREG_BASE + CH_EP_ROW * 8 - RAM_BASE) == CH_EP_REC, "CH End-Phase row 198")
            check(struct.unpack_from("<4H", ov, CH_FUSION_ROW - RAM_BASE) == (CHARLES, CR_FUSION_DEAD, CR_FUSION_DEAD, 0),
                  "CH fusion recipe A[73] dead")
            check(_bl_target(ov, EQTRIG_SITE) == CHL["EQ"], f"CH bl @{EQTRIG_SITE:#x} -> equip-trigger front")


        # =================================================================================================
        # card 13: Rabid Horseman 0x1002 -> Angelica, Princess of Noble Arms (notes/infernoble-angelica-findings.md)
        #   Identity: Captain Oliver's recipe (Laval Twin Slayer 0x23FE reference); recipe A[10] killed.
        #   C1 "If this card is Special Summoned: You can add 1 'Horn of Olifant', or 1 card that mentions Emperor Charles":
        #      c9_trigger_hook arm + cls1 (event != 0x13) -> Deck add 0x02207EF5 through criteria mode 0 = AN_SEARCH cids.
        #   C2 Quick, "a card or effect is activated that targets this card": cls3 over 0x0E51, +0C = Blue-Eyes Shining
        #      Dragon's target test 0x021F8135; "targeted for an attack": attack-target tree pool literal 0x0E65 -> 0x1002
        #      (execution-proven, scratch/infernoble/atktgt_tree.py) = cls1 event 0x13.  Effect: send 1 FIRE Warrior from the
        #      Deck (0x021D21B0, Armageddon's call), banish this card with Interdimensional Matter Transporter's encoding +
        #      node {0x1002, kind 1}, End-Phase row 152 {0x022546FD, 0x1002} + cls2 {0x02216E21, -, 0x021F68D9} return it;
        #      then Yes/No -> 1 "Roland" (0x0FDB Deck / 0x0FEB Extra Deck builder flags 8) via SS commit 0x0226925D.
        # =================================================================================================
        ANGELICA = 0x1002
        CLS3_BASE, CLS3_COUNT = 0x02279D74, 0x308
        AN_C1KEY, AN_C2KEY = 0x4000 | ANGELICA, 0x2000 | ANGELICA
        AN_FUSION_ROW, AN_FUSION_STOCK = 0x02270BE4, (ANGELICA, 0x0FC0, 0x1001, 0)
        AN_EP_ROW, AN_EP_NATIVE, AN_EP_REC = 152, (0x02253EC9, 0x0EA0), (0x022546FD, ANGELICA)
        ATKTGT_POOL, ATKTGT_STOCK = 0x021C68C0, 0x0E65
        ROLAND_CIDS = (0x0FDB, 0x0FEB)                       # Roland (Main Deck), Captain Roland (Extra Deck)
        AN_SEARCH: tuple[int, ...] = (0x1976, 0x1346, 0x16DB)   # Horn of Olifant, Noble Arms Museum, The Continuing Epic of Charles
        EV_ATTACK_TARGET, MSG_SEND, MSG_SS = 0x13, 0x3A, 0x11D
        DECK_SEND, BANISH_AT, POS_FLAG, BESD_TGT = 0x021D21B1, 0x021CF451, 0x021AF1E9, 0x021F8135
        RETURN_RES, RETURN_COND, SS_COMMIT, ED_BUILDER = 0x02216E21, 0x021F68D9, 0x0226925D, 0x0223BE41
        for _v in (DECK_SEND, BANISH_AT, POS_FLAG, BESD_TGT, RETURN_RES, RETURN_COND, SS_COMMIT, ED_BUILDER):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        ANL = {n: getattr(O5, f"CAVE_IK_AN_{n}") for n in ("COND1", "COND3", "RES1", "C2RES", "CRIT", "SRCHCB", "ROLCB")}
        ANRESERVE = {"COND1": 0x80, "COND3": 0x60, "RES1": 0x60, "C2RES": 0x280, "CRIT": 0x90, "SRCHCB": 0x40, "ROLCB": 0x30}
        AN_CLS1_PHANTOM, AN_CLS3_PHANTOM, AN_CLS2_PHANTOM, AN_CRIT_PHANTOM = 0x0EA0, 0x0E51, 0x0E67, 0x16C1
        AN_CLS1_REC = (ANGELICA, 0, ANL["RES1"] | 1, 0, ANL["COND1"] | 1, TAG_YOU_CAN, 0)
        AN_CLS3_REC = (ANGELICA, 0, ANL["C2RES"] | 1, 0, ANL["COND3"] | 1, 0, 0)
        AN_CLS2_REC = (ANGELICA, 0, RETURN_RES, 0, RETURN_COND, 0, 0)
        AN_CRIT_REC = (ANGELICA, 0xFFFF, ANL["CRIT"] | 1, 0x00000000)        # mode = param >> 16 (0 search, 1 FW, 2 Roland)
        AN_C9_ARM = (ANGELICA, "Rabid Horseman -> Angelica, Princess of Noble Arms C1 (C2 in-game confirmed by user 2026-10-22 on Barox; re-donored, infernoble)")


        def _an_count(b: EffectBuilder, mode: int, no: str) -> None:
            """ROW_COUNT_C(side, 0x1002, mode << 16) == 0 -> *no*.  r4 = desc; uses r0-r3."""
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.ldr_const(1, ANGELICA)
            b.ldr_const(2, mode << 16)
            b.call_addr(ROW_COUNT_C, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", f"{no}")


        def an_cond1_stub() -> EffectBuilder:
            """cls1 +0C: event 0x13 (targeted for an attack) -> C2 OPT clear + a FIRE Warrior in the Deck -> 2; any other
            event (the c9 Special Summon trigger) -> C1 OPT clear + a searchable card -> 2.  Else 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("CMP", f"R0, #0x{EV_ATTACK_TARGET:X}")
            b.insn("BNE", "c1")
            _used(b, AN_C2KEY, "r4", "no")
            _an_count(b, 1, "no")
            b.insn("B", "yes")
            b.label("c1")
            _used(b, AN_C1KEY, "r4", "no")
            _an_count(b, 0, "no")
            b.label("yes")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def an_cond3_stub() -> EffectBuilder:
            """cls3 +0C (desc, r1 = the activation being answered): C2 OPT clear, a FIRE Warrior in the Deck, then Blue-Eyes
            Shining Dragon's 'that activation targets this card' 0x021F8135 (0 / 1)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            _used(b, AN_C2KEY, "r4", "no")
            _an_count(b, 1, "no")
            b.call_addr(BESD_TGT, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def an_res1_stub() -> EffectBuilder:
            """cls1 +04: event 0x13 -> the C2 machine; else C1: phase 0x80 OPT check + stamp, then the Deck add 0x02207EF5."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("CMP", f"R0, #0x{EV_ATTACK_TARGET:X}")
            b.insn("BNE", "c1")
            b.ldr_const(3, ANL['C2RES'] | 1)
            b.insn("B", "go")
            b.label("c1")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, AN_C1KEY, "r4", "zero")
            _post(b, AN_C1KEY)
            b.label("nat")
            b.ldr_const(3, ADD_FROM_DECK_RES)
            b.label("go")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R6, #0x0")
            b.insn("BLX", "R3")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def an_c2res_stub() -> EffectBuilder:
            """Phases on [0x0229AAFC+0x70]:
               0x80 chain push; OPT 0x2FFC check + stamp; still where it was; a FIRE Warrior in the Deck -> message 0x3A -> 0x6E
               0x6E picker (mode 1) | 0x6D readback -> send it 0x021D21B0 (cause 0x1002); failed -> end
               0x6C banish THIS card (0x021CF450, IMT's 0x80 body), keep IMT's encoded word in desc[+0x1C]
               0x6B banished ([0x0229C314+0x14]) -> node {0x1002, kind 1, word}; free MZ + a Roland -> Yes/No 0xFA; else end
               0x6A Yes -> message 0x11D | 0x69 picker (mode 2) | 0x68 readback -> SS commit 0x0226925D -> 0x66
               0x66 chain pop -> 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x10")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "d1")
            b.insn("B", "p80")
            b.label("d1")
            b.insn("CMP", "R0, #0x6E")
            b.insn("BEQ", "p6e")
            b.insn("CMP", "R0, #0x6D")
            b.insn("BEQ", "p6d")
            b.insn("CMP", "R0, #0x6C")
            b.insn("BNE", "d2")
            b.insn("B", "p6c")
            b.label("d2")
            b.insn("CMP", "R0, #0x6B")
            b.insn("BNE", "d3")
            b.insn("B", "p6b")
            b.label("d3")
            b.insn("CMP", "R0, #0x6A")
            b.insn("BNE", "d4")
            b.insn("B", "p6a")
            b.label("d4")
            b.insn("CMP", "R0, #0x69")
            b.insn("BNE", "d5")
            b.insn("B", "p69")
            b.label("d5")
            b.insn("CMP", "R0, #0x68")
            b.insn("BNE", "d6")
            b.insn("B", "p68")
            b.label("d6")
            b.insn("B", "end")
            b.label("p6e")
            b.call_addr(AS_PICKER, R5, 6, ANGELICA, 0x10000, via=R7)
            b.insn("MOV", "R0, #0x6D")
            b.insn("B", "ret")
            b.label("p6d")
            b.bl_label("word")
            b.insn("ADD", "R1, R0, #0x0")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x0]")
            b.call_addr(DECK_SEND, R5, R1, ANGELICA, 0, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "t6c")
            b.insn("B", "end")
            b.label("t6c")
            b.insn("MOV", "R0, #0x6C")
            b.insn("B", "ret")
            b.label("p6c")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R1, R0, #0x10")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("STR", "R1, [SP, #0x8]")
            b.insn("CMP", "R1, #0x4")
            b.insn("BGT", "e6c")
            b.insn("LSL", "R0, R0, #0x18")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("STR", "R0, [SP, #0xC]")
            b.insn("MOV", "R2, #0x1")
            b.insn("AND", "R2, R0")
            b.ldr_const(3, 0xb3c)
            b.insn("MUL", "R2, R3")
            b.insn("MOV", "R3, #0x14")
            b.insn("MUL", "R3, R1")
            b.insn("ADD", "R7, R2, R3")
            b.ldr_const(0, 0x0229acc8)
            b.insn("LDR", "R0, [R0, R7]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R0, R0, R1")
            b.insn("LSL", "R0, R0, #0x4")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDR", "R1, [SP, #0xC]")
            b.insn("LDR", "R2, [SP, #0x8]")
            b.call_addr(BANISH_AT, R0, R1, R2, 0x80, via=R6)
            b.ldr_const(6, 0x0229aafc)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "e6c")
            b.ldr_const(0, 0x0229acd0)
            b.insn("LDRH", "R0, [R0, R7]")
            b.insn("LDR", "R1, [SP, #0x4]")
            b.insn("ADD", "R1, R1, R0")
            b.ldr_const(0, 0x0229acce)
            b.insn("LDRH", "R0, [R0, R7]")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R1, R1, R0")
            b.insn("LDR", "R0, [SP, #0xC]")
            b.insn("LSL", "R0, R0, #0x3")
            b.insn("ADD", "R1, R1, R0")
            b.insn("STR", "R1, [SP, #0x4]")
            b.insn("LDR", "R0, [SP, #0xC]")
            b.insn("LDR", "R1, [SP, #0x8]")
            b.call_addr(POS_FLAG, R0, R1, 1, via=R3)
            b.insn("LSL", "R0, R0, #0x2")
            b.insn("LDR", "R1, [SP, #0x4]")
            b.insn("ADD", "R1, R1, R0")
            b.insn("STRH", "R1, [R4, #0x1C]")
            b.insn("MOV", "R0, #0x6B")
            b.insn("B", "ret")
            b.label("e6c")
            b.insn("B", "end")
            b.label("p6b")
            b.ldr_const(0, 0x0229c314)
            b.insn("LDR", "R0, [R0, #0x14]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "rol")
            b.insn("ADD", "R0, R5, #0x0")
            b.ldr_const(1, ANGELICA)
            b.insn("MOV", "R2, #0x1")
            b.insn("LDRH", "R3, [R4, #0x1C]")
            b.call("turnlog_post", via=R7)
            b.label("rol")
            b.call_addr(CAN_SS, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "e6b")
            b.call_addr(FREE_MZ, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "e6b")
            _an_count(b, 2, "e6b")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("MOV", "R1, #0xFA")
            b.insn("LDRH", "R2, [R4, #0xC]")
            b.call_addr(AS_YESNO, via=R3)
            b.insn("MOV", "R0, #0x6A")
            b.insn("B", "ret")
            b.label("e6b")
            b.insn("B", "end")
            b.label("p6a")
            b.ldr_const(0, AS_UI)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "end")
            b.call_addr(AS_MESSAGE, R5, MSG_SS, via=R3)
            b.insn("MOV", "R0, #0x69")
            b.insn("B", "ret")
            b.label("p69")
            b.call_addr(AS_PICKER, R5, 6, ANGELICA, 0x20000, via=R7)
            b.insn("MOV", "R0, #0x68")
            b.insn("B", "ret")
            b.label("p68")
            b.call_addr(AS_READBACK, via=R3)
            b.insn("ADD", "R1, R0, #0x0")
            b.ldr_const(0, ANGELICA << 16)
            b.insn("STR", "R0, [SP, #0x0]")
            b.call_addr(SS_COMMIT, R5, R1, 1, 2, via=R7)
            b.insn("MOV", "R0, #0x66")
            b.insn("B", "ret")
            b.label("p80")
            b.call_addr(CHAIN_PUSH, via=R3)
            _used(b, AN_C2KEY, "r4", "end")
            _post(b, AN_C2KEY)
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.call_addr(VALIDATE, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "end")
            _an_count(b, 1, "end")
            b.call_addr(AS_MESSAGE, R5, MSG_SEND, via=R3)
            b.insn("MOV", "R0, #0x6E")
            b.insn("B", "ret")
            b.label("end")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("word")
            b.insn("PUSH", "{LR}")
            b.call_addr(AS_READBACK, via=R3)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R0, R0, R1")
            b.insn("POP", "{PC}")
            return b


        def an_crit_stub() -> EffectBuilder:
            """Criteria handler (row r0, side r1, param r2), mode = param >> 16: 0 -> Deck, any card type (word 0xE), cid in
            AN_SEARCH (the native Deck add passes param 0); 1 -> Deck FIRE Warriors (Ogier's C2CB, excluding 0x1002); 2 ->
            Deck + Extra Deck (builder flags 8) "Roland" monsters (AN_ROLCB)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("ADD", "R4, R1, #0x0")
            b.insn("LDRH", "R5, [R0, #0x0]")
            b.insn("LSR", "R0, R2, #0x10")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "fw")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "rol")
            b.insn("MOV", "R0, #0xE")
            b.ldr_const(2, ANL['SRCHCB'] | 1)
            b.bl_label("deck")
            b.insn("B", "out")
            b.label("fw")
            b.ldr_const(0, FIRE_WARRIOR)
            b.ldr_const(2, L['C2CB'] | 1)
            b.bl_label("deck")
            b.insn("B", "out")
            b.label("rol")
            b.insn("MOV", "R0, #0x2")
            b.ldr_const(2, ANL['ROLCB'] | 1)
            b.bl_label("deck")
            b.insn("ADD", "R6, R0, #0x0")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x8")
            b.insn("STR", "R0, [SP, #0x4]")
            b.call_addr(ED_BUILDER, R4, R5, ANL['ROLCB'] | 1, 0, via=R7)
            b.insn("ADD", "R0, R0, R6")
            b.label("out")
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("deck")
            b.insn("PUSH", "{LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.call_addr(CRIT_WORKER, R4, R5, R2, ANGELICA)
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{PC}")
            return b


        def _cid_in_cb(cids) -> EffectBuilder:
            """Worker / builder callback: [sp] = &candidate card word -> 1 iff its cid is in *cids*."""
            b = EffectBuilder()
            if not cids:
                b.insn("MOV", "R0, #0")
                b.insn("BX", "LR")
                return b
            b.insn("LDR", "R0, [SP, #0x0]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            for c in cids:
                b.ldr_const(1, c)
                b.insn("CMP", "R0, R1")
                b.insn("BEQ", "yes")
            b.insn("MOV", "R0, #0")
            b.insn("BX", "LR")
            b.label("yes")
            b.insn("MOV", "R0, #1")
            b.insn("BX", "LR")
            return b


        ANSTUBS = {"COND1": an_cond1_stub, "COND3": an_cond3_stub, "RES1": an_res1_stub, "C2RES": an_c2res_stub,
                  "CRIT": an_crit_stub, "SRCHCB": lambda: _cid_in_cb(AN_SEARCH), "ROLCB": lambda: _cid_in_cb(ROLAND_CIDS)}


        def apply_angelica(rom, ov: bytearray) -> None:
            from otn_enhanced.cards.junk_speeder import LIST_A, LIST_MIN3
            for base, count, rec, ph, label in ((CLS1_BASE, CLS1_COUNT, AN_CLS1_REC, AN_CLS1_PHANTOM, "AN cls1 (C1 + attack target)"),
                                                (CLS3_BASE, CLS3_COUNT, AN_CLS3_REC, AN_CLS3_PHANTOM, "AN cls3 (targeted)"),
                                                (CLS2_BASE, CLS2_COUNT, AN_CLS2_REC, AN_CLS2_PHANTOM, "AN cls2 (End-Phase return)")):
                insert_row(ov, base, count, 24, CLS_FMT, rec, ph, label)
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, AN_CRIT_REC, AN_CRIT_PHANTOM, "AN criteria row")
            o = EPREG_BASE + AN_EP_ROW * 8 - RAM_BASE
            assert struct.unpack_from("<II", ov, o) in (AN_EP_NATIVE, AN_EP_REC), "AN End-Phase row 152 moved"
            struct.pack_into("<II", ov, o, *AN_EP_REC)
            o = ATKTGT_POOL - RAM_BASE
            assert struct.unpack_from("<I", ov, o)[0] in (ATKTGT_STOCK, ANGELICA), "AN attack-target pool literal moved"
            struct.pack_into("<I", ov, o, ANGELICA)
            f = AN_FUSION_ROW - RAM_BASE
            row = struct.unpack_from("<4H", ov, f)
            assert row in (AN_FUSION_STOCK, (ANGELICA, CR_FUSION_DEAD, CR_FUSION_DEAD, 0)), f"AN fusion row {row}"
            struct.pack_into("<2H", ov, f + 2, CR_FUSION_DEAD, CR_FUSION_DEAD)
            for base, n in (LIST_A, LIST_MIN3):
                assert ANGELICA not in [struct.unpack_from("<H", ov, base + 2 * i - RAM_BASE)[0] for i in range(n)]
            print("AN cls1 + cls3 + cls2 + criteria rows, End-Phase row 152, attack-target literal, recipe A[10] killed")


        def verify_angelica(rom, ov, check) -> None:
            from otn_enhanced.effects import c9_trigger_hook as c9
            for label, base, count, stride, fmt, rec in (("cls1", CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, AN_CLS1_REC),
                                                         ("cls3", CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, AN_CLS3_REC),
                                                         ("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, AN_CLS2_REC),
                                                         ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, AN_CRIT_REC)):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == ANGELICA] == [rec], f"AN {label}: exactly one 0x1002 row")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"AN {label}: sorted")
            check(struct.unpack_from("<II", ov, EPREG_BASE + AN_EP_ROW * 8 - RAM_BASE) == AN_EP_REC, "AN End-Phase row 152")
            check(struct.unpack_from("<I", ov, ATKTGT_POOL - RAM_BASE)[0] == ANGELICA, "AN attack-target literal 0x0E65 -> 0x1002")
            check(struct.unpack_from("<4H", ov, AN_FUSION_ROW - RAM_BASE) == (ANGELICA, CR_FUSION_DEAD, CR_FUSION_DEAD, 0),
                  "AN fusion recipe A[10] dead")
            check(any(c == ANGELICA for c, _ in c9.ARMS), "AN c9_trigger_hook arm registered")


        # =================================================================================================
        # extra card: Simultaneous Loss 0x1976 -> Horn of Olifant (Normal Trap; notes/infernoble-horn-of-olifant-findings.md)
        #   Donor's cls0 record re-pointed in place: {HO_RES, 0, HO_COND, HO_COST, 0}.  ONE record + own "Use which effect?"
        #   menu (Turpin / Uni-Zombie shape), NEXT's 1-per-turn activation gate 0x021F6DD9 + node.  Mode in desc[+0x18].
        #   A: pick 1 card = your S/T card equipped to something (Equip Spell OR a monster "as an Equip Spell", user) or an
        #      Equip Spell in your GY -> banish it; Yes/No 0x161 -> pick 1 card on the field -> destroy (0x0224A924 + 0x021CF388).
        #   B: pick 1 Roland / Captain Roland you control -> destroy; then FIRE Warriors from the Deck one at a time, face-up
        #      DEF, only cards that still let the Levels total exactly 9 within min(3, free zones) picks (user: not offered
        #      when no combination exists); negated = NEXT's precheck on both negate lists (0x02268090 / 0x021EE418, key 0x1976);
        #      Warrior-only lock = turn-log {0x5976} read by a front ahead of Ricciardetto's lock @0x021BA368 (countdown:
        #      own turn 2, opponent's turn 1 = "until the end of your next turn").
        # =================================================================================================
        HORN = 0x1976
        HO_LOCKKEY = 0x4000 | HORN
        HO_CLS0_STOCK = (HORN, 0, 0x0221FD19, 0, 0x021F9FA5, 0, 0)
        HO_CRIT_PHANTOM = 0x1748
        ONCE_CHECK, COPY_EXEMPT, RECORD, DESTROY_AT, VALID_AT = 0x021F6DD9, 0x021D2B89, 0x02243B2D, 0x021CF389, 0x0224A925
        PICKBLK, PICKMETA = 0x0229944C, 0x02299908
        NEG_SITE, NEG_TAIL, POST_SITE, POST_TAIL = 0x021EE418, 0x021FBC94, 0x02268090, 0x0223F8E4   # NEXT's prechecks
        HO_LABEL_A, HO_LABEL_B, HO_TITLE = 0x16D, 0x1AB, 0x103
        MSG_BANISH1, YN_DESTROY, MSG_DESTROY, MSG_OWN_DESTROY, MSG_DECK_SS = 0x125, 0x161, 0x119, 0x7B, 0x30
        for _v in (ONCE_CHECK, COPY_EXEMPT, RECORD, DESTROY_AT, VALID_AT):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        HOL = {n: getattr(O5, f"CAVE_IK_HO_{n}") for n in ("LEGAL", "COND", "COST", "RES", "CRIT", "EQSPCB", "HISTCB", "LVCB",
                                                           "LOCK", "PRENEG", "PREPOST")}
        HORESERVE = {"LEGAL": 0x90, "COND": 0x40, "COST": 0xa0, "RES": 0x340, "CRIT": 0x140, "EQSPCB": 0x40, "HISTCB": 0x30, "LVCB": 0x80, "LOCK": 0x40, "PRENEG": 0x20, "PREPOST": 0x20}
        HO_CLS0_REC = (HORN, 0, HOL["RES"] | 1, 0, HOL["COND"] | 1, HOL["COST"] | 1, 0)
        HO_CRIT_REC = (HORN, 0xFFFF, HOL["CRIT"] | 1, 0x00000000)   # mode = param >> 16: 1 A pool, 2 any card, 3 Roland, 4 Deck
        CLS0_BASE, CLS0_COUNT = 0x0227E64C, 0x51A


        def _ho_side(b: EffectBuilder, reg: str = "r5") -> None:
            """reg <- the controller (desc[+2] ^ desc[+6]) & 1, desc in r4 (NEXT's res_stub)."""
            b.insn("LDRB", f"{str(reg).upper()}, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x6]")
            b.insn("EOR", f"{str(reg).upper()}, R0")
            b.insn("MOV", "R0, #0x1")
            b.insn("AND", f"{str(reg).upper()}, R0")


        _HO_N = [0]


        def _ho_count(b: EffectBuilder, param: int | None, no: str) -> None:
            """ROW_COUNT_C(side r5, 0x1976, param) == 0 -> *no* (an unconditional `b`: the resolver is past bcc range).
            *param* (None = leave r2 as it is) is loaded into r2."""
            _HO_N[0] += 1
            ok = f"hc{_HO_N[0]}"
            if param is not None:
                b.ldr_const(2, param)
            b.insn("ADD", "R0, R5, #0")
            b.ldr_const(1, HORN)
            b.ldr_const(3, ROW_COUNT_C)
            b.insn("BLX", "R3")
            b.insn("CMP", "R0, #0")
            b.insn("BNE", ok)
            b.insn("B", no)
            b.label(ok)


        def ho_legal_stub() -> EffectBuilder:
            """(desc) -> mask: bit 0 = A has a card to banish; bit 1 = B (a Roland you control, may SS, and a FIRE Warrior that
            starts an exact-9 set within min(3, free zones + 1) picks)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            _ho_side(b)
            b.insn("MOV", "R6, #0x0")
            _ho_count(b, 0x10000, "nob0")
            b.insn("MOV", "R6, #0x1")
            b.label("nob0")
            _ho_count(b, 0x30000, "out")
            b.call_addr(CAN_SS, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "out")
            b.call_addr(FREE_MZ, R5, via=R3)
            b.insn("ADD", "R0, #0x1")
            b.insn("CMP", "R0, #0x3")
            b.insn("BLE", "k3")
            b.insn("MOV", "R0, #0x3")
            b.label("k3")
            b.ldr_const(2, 0x40900)
            b.insn("ORR", "R2, R0")
            _ho_count(b, None, "out")
            b.insn("MOV", "R0, #0x2")
            b.insn("ORR", "R6, R0")
            b.label("out")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def ho_cond_stub() -> EffectBuilder:
            """cls0 +0C: menu check (desc[+7] == 0) -> NEXT's 1-per-turn gate 0x021F6DD9; then any legal mode -> 1."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x7]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "leg")
            b.call_addr(ONCE_CHECK, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.label("leg")
            b.call_addr(HOL['LEGAL'], R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b


        def ho_cost_stub() -> EffectBuilder:
            """cls0 +10 on [0x0229AAFC+0x7C] (0 yield / 1 done / -1 abort): settled -> 1; phase 0x40 -> mode = answer + 1;
            phase 0: both legal -> "Use which effect?" (0x103: A 0x16D / B 0x1AB), phase 0x40, yield; one -> that mode.
            Mode -> desc[+0x18], then the 1-per-turn node (NEXT's cost_stub: skipped in a replay)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(SHORTCIRCUIT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "one")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x7C]")
            b.insn("CMP", "R0, #0x40")
            b.insn("BNE", "ph0")
            b.ldr_const(0, CHOICE)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x18]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.insn("B", "stamp")
            b.label("ph0")
            b.call_addr(HOL['LEGAL'], R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "abort")
            b.insn("CMP", "R0, #0x3")
            b.insn("BEQ", "ask")
            b.insn("STRH", "R0, [R4, #0x18]")
            b.label("stamp")
            b.call_addr(COPY_EXEMPT, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "one")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, 1, via=R7)
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("ask")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R0, #0x3")
            b.insn("STR", "R0, [SP, #0x8]")
            b.call_addr(PROMPT, R4, HO_TITLE, HO_LABEL_A, HO_LABEL_B, via=R7)
            b.insn("MOV", "R0, #0x40")
            b.insn("STR", "R0, [R6, #0x7C]")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("abort")
            b.insn("MOV", "R0, #0x0")
            b.insn("SUB", "R0, #0x1")
            b.label("ret")
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def _ho_pickloc(b: EffectBuilder) -> None:
            """r1 <- side, r2 <- zone of the current pick (list meta 0x02299908[[0x0229944C+4]]: bit 0 side, bits 1..5 zone)."""
            b.ldr_const(1, PICKBLK)
            b.insn("LDRH", "R0, [R1, #0x4]")
            b.insn("LSL", "R0, R0, #0x1")
            b.ldr_const(1, PICKMETA)
            b.insn("LDRH", "R0, [R1, R0]")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R1, R0")
            b.insn("LSL", "R2, R0, #0x1A")
            b.insn("LSR", "R2, R2, #0x1B")


        def _ho_pick(b: EffectBuilder, param: int, nxt: int) -> None:
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R1, #0x6")
            b.ldr_const(2, HORN)
            b.ldr_const(3, param)
            b.call_addr(AS_PICKER, via=R7)
            b.insn("MOV", f"R0, #0x{nxt:X}")
            b.insn("B", "ret")


        def _ho_msg(b: EffectBuilder, code: int, nxt: int) -> None:
            b.insn("ADD", "R0, R5, #0x0")
            b.ldr_const(1, code)
            b.call_addr(AS_MESSAGE, via=R3)
            b.insn("MOV", f"R0, #0x{nxt:X}")
            b.insn("B", "ret")


        def _ho_destroy_pick(b: EffectBuilder) -> None:
            """Destroy the current pick if it is still there (Catsith's 0x0224A924 re-check + 0x021CF388)."""
            _HO_N[0] += 1
            n = _HO_N[0]
            _ho_pickloc(b)
            b.insn("STR", "R1, [SP, #0x8]")
            b.insn("STR", "R2, [SP, #0xC]")
            b.call_addr(VALID_AT, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", f"dv{n}")
            b.insn("B", "end")
            b.label(f"dv{n}")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDR", "R1, [SP, #0x8]")
            b.insn("LDR", "R2, [SP, #0xC]")
            b.call_addr(DESTROY_AT, via=R3)


        def ho_res_stub() -> EffectBuilder:
            """Phases on [0x0229AAFC+0x70]; mode desc[+0x18] (1 = A, 2 = B).
               0x80 chain push -> A 0x7F / B 0x70 (same frame)
               A 0x7F message 0x125 | 0x7E picker mode 1 | 0x7D banish it (GY: Rulers' GY banish; field: 0x021CF450)
                 0x7C any card on the field -> Yes/No 0x161 | 0x7B Yes -> message 0x119 | 0x7A picker mode 2 | 0x79 destroy
               B 0x70 message 0x7B | 0x6F picker mode 3 | 0x6E destroy the Roland; rem 9 -> desc[+0x1C], count 0 -> [+0x1E]
                 0x6D destroyed -> Warrior-lock node 0x5976 | 0x6C rem && count < 3 && may SS && k = min(3 - count, free
                 zones) && a candidate -> message 0x30 | 0x6B picker mode 4 (rem, k) | 0x6A summon it face-up DEF, rem -= Lv,
                 count++ -> 0x6C.   end: chain pop -> 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x10")
            b.insn("ADD", "R4, R0, #0x0")
            _ho_side(b)
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "d0")
            b.insn("B", "p80")
            b.label("d0")
            b.insn("CMP", "R0, #0x7E")
            b.insn("BNE", "d1")
            b.insn("B", "p7e")
            b.label("d1")
            b.insn("CMP", "R0, #0x7D")
            b.insn("BNE", "d2")
            b.insn("B", "p7d")
            b.label("d2")
            b.insn("CMP", "R0, #0x7C")
            b.insn("BNE", "d3")
            b.insn("B", "p7c")
            b.label("d3")
            b.insn("CMP", "R0, #0x7B")
            b.insn("BNE", "d4")
            b.insn("B", "p7b")
            b.label("d4")
            b.insn("CMP", "R0, #0x7A")
            b.insn("BNE", "d5")
            b.insn("B", "p7a")
            b.label("d5")
            b.insn("CMP", "R0, #0x79")
            b.insn("BNE", "d6")
            b.insn("B", "p79")
            b.label("d6")
            b.insn("CMP", "R0, #0x6F")
            b.insn("BNE", "d7")
            b.insn("B", "p6f")
            b.label("d7")
            b.insn("CMP", "R0, #0x6E")
            b.insn("BNE", "d8")
            b.insn("B", "p6e")
            b.label("d8")
            b.insn("CMP", "R0, #0x6D")
            b.insn("BNE", "d9")
            b.insn("B", "p6d")
            b.label("d9")
            b.insn("CMP", "R0, #0x6C")
            b.insn("BNE", "da")
            b.insn("B", "p6c")
            b.label("da")
            b.insn("CMP", "R0, #0x6B")
            b.insn("BNE", "db")
            b.insn("B", "p6b")
            b.label("db")
            b.insn("CMP", "R0, #0x6A")
            b.insn("BNE", "dc")
            b.insn("B", "p6a")
            b.label("dc")
            b.insn("B", "end")
            b.label("p80")
            b.call_addr(CHAIN_PUSH, via=R3)
            b.insn("LDRH", "R0, [R4, #0x18]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BNE", "pa")
            b.insn("B", "pb")
            b.label("pa")
            _ho_count(b, 0x10000, "end")
            _ho_msg(b, MSG_BANISH1, 0x7E)
            b.label("p7e")
            _ho_pick(b, 0x10000, 0x7D)
            b.label("p7d")
            _ho_pickloc(b)
            b.insn("CMP", "R2, #0xE")
            b.insn("BNE", "fban")
            b.call_addr(AS_READBACK, via=R3)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R0, R0, R1")
            b.call_addr(AS_REF_TO_WORD, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "t7c")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(AS_GY_BANISH, R5, R1, 0, via=R3)
            b.insn("B", "t7c")
            b.label("fban")
            b.call_addr(BANISH_AT, R4, R1, R2, 0x80, via=R7)
            b.label("t7c")
            b.insn("MOV", "R0, #0x7C")
            b.insn("B", "ret")
            b.label("p7c")
            _ho_count(b, 0x20000, "end")
            b.insn("ADD", "R0, R4, #0x0")
            b.ldr_const(1, YN_DESTROY)
            b.insn("LDRH", "R2, [R4, #0xC]")
            b.call_addr(AS_YESNO, via=R3)
            b.insn("MOV", "R0, #0x7B")
            b.insn("B", "ret")
            b.label("p7b")
            b.ldr_const(0, AS_UI)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "y7b")
            b.insn("B", "end")
            b.label("y7b")
            _ho_msg(b, MSG_DESTROY, 0x7A)
            b.label("p7a")
            _ho_pick(b, 0x20000, 0x79)
            b.label("p79")
            _ho_destroy_pick(b)
            b.insn("B", "end")
            b.label("pb")
            _ho_count(b, 0x30000, "end")
            _ho_msg(b, MSG_OWN_DESTROY, 0x6F)
            b.label("p6f")
            _ho_pick(b, 0x30000, 0x6E)
            b.label("p6e")
            _ho_destroy_pick(b)
            b.insn("MOV", "R0, #0x9")
            b.insn("STRH", "R0, [R4, #0x1C]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STRH", "R0, [R4, #0x1E]")
            b.insn("MOV", "R0, #0x6D")
            b.insn("B", "ret")
            b.label("p6d")
            b.ldr_const(0, 0x0229c314)
            b.insn("LDR", "R0, [R0, #0x14]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "d6d")
            b.insn("B", "end")
            b.label("d6d")
            b.insn("MOV", "R2, #0x11")
            b.ldr_const(0, 0x0229dd14)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("CMP", "R0, R5")
            b.insn("BNE", "lk")
            b.insn("MOV", "R2, #0x21")
            b.label("lk")
            b.call("turnlog_post", R5, HO_LOCKKEY, R2, 0, via=R7)
            b.insn("MOV", "R0, #0x6C")
            b.insn("B", "ret")
            b.label("p6c")
            b.bl_label("kparam")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "c6c")
            b.insn("B", "end")
            b.label("c6c")
            b.insn("ADD", "R2, R0, #0x0")
            _ho_count(b, None, "end")
            _ho_msg(b, MSG_DECK_SS, 0x6B)
            b.label("p6b")
            b.bl_label("kparam")
            b.insn("ADD", "R3, R0, #0x0")
            b.call_addr(AS_PICKER, R5, 6, HORN, via=R7)
            b.insn("MOV", "R0, #0x6A")
            b.insn("B", "ret")
            b.label("p6a")
            b.call_addr(AS_READBACK, via=R3)
            b.insn("ADD", "R7, R0, #0x0")
            b.insn("LDR", "R0, [R7, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call("cid_level", via=R3)
            b.insn("LDRH", "R1, [R4, #0x1C]")
            b.insn("SUB", "R1, R1, R0")
            b.insn("BPL", "rok")
            b.insn("MOV", "R1, #0x0")
            b.label("rok")
            b.insn("STRH", "R1, [R4, #0x1C]")
            b.insn("LDRH", "R1, [R4, #0x1E]")
            b.insn("ADD", "R1, #0x1")
            b.insn("STRH", "R1, [R4, #0x1E]")
            b.ldr_const(0, HORN << 16)
            b.insn("STR", "R0, [SP, #0x0]")
            b.call_addr(SS_COMMIT, R5, R7, 1, 1, via=R7)
            b.insn("MOV", "R0, #0x6C")
            b.insn("B", "ret")
            b.label("end")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("kparam")
            b.insn("PUSH", "{R6, LR}")
            b.insn("LDRH", "R6, [R4, #0x1C]")
            b.insn("CMP", "R6, #0x0")
            b.insn("BEQ", "kz")
            b.insn("LDRH", "R0, [R4, #0x1E]")
            b.insn("CMP", "R0, #0x3")
            b.insn("BGE", "kz")
            b.call_addr(CAN_SS, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "kz")
            b.call_addr(FREE_MZ, R5, via=R3)
            b.insn("LDRH", "R1, [R4, #0x1E]")
            b.insn("MOV", "R2, #0x3")
            b.insn("SUB", "R2, R2, R1")
            b.insn("CMP", "R0, R2")
            b.insn("BLE", "kmin")
            b.insn("ADD", "R0, R2, #0x0")
            b.label("kmin")
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "kz")
            b.insn("LSL", "R6, R6, #0x8")
            b.insn("ORR", "R0, R6")
            b.insn("MOV", "R1, #0x4")
            b.insn("LSL", "R1, R1, #0x10")
            b.insn("ORR", "R0, R1")
            b.insn("POP", "{R6, PC}")
            b.label("kz")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R6, PC}")
            return b


        def ho_crit_stub() -> EffectBuilder:
            """Criteria handler (row r0, side r1, param r2), mode = param >> 16:
               1 = your S/T zones 5..9 holding a card equipped to something (EQUIP_TARGET_OF != 0xFFFF) -> RECORD, + GY worker
                   (word 4 = Spell) with HO_EQSPCB (an Equip Spell);  2 = every occupied zone 0..10 of both sides -> RECORD;
               3 = your zones 0..4 holding Roland / Captain Roland -> RECORD;  4 = Deck FIRE Warriors: histogram pass
                   (HO_HISTCB) then the exact-9 filter pass (HO_LVCB), ctx = {{hist[16], rem = (param >> 8) & 0xFF, k = param & 0xFF}}."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x20")
            b.insn("ADD", "R4, R1, #0x0")
            b.insn("ADD", "R5, R2, #0x0")
            b.insn("MOV", "R6, #0x0")
            b.insn("LSR", "R0, R5, #0x10")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "ma")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "many")
            b.insn("CMP", "R0, #0x3")
            b.insn("BEQ", "mrol")
            b.insn("CMP", "R0, #0x4")
            b.insn("BNE", "out0")
            b.insn("B", "mdeck")
            b.label("out0")
            b.insn("B", "out")
            b.label("ma")
            b.insn("MOV", "R7, #0x5")
            b.label("maz")
            b.call_addr(CARD_CID_AT, R4, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "man")
            b.call_addr(EQUIP_TARGET_OF, R4, R7, via=R3)
            b.ldr_const(1, 0xffff)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "man")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R7, #0x0")
            b.bl_label("rec")
            b.label("man")
            b.insn("ADD", "R7, #0x1")
            b.insn("CMP", "R7, #0x9")
            b.insn("BLE", "maz")
            b.insn("MOV", "R0, #0x4")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.call_addr(GY_WORKER, R4, HORN, HOL['EQSPCB'] | 1, 0)
            b.insn("ADD", "R6, R6, R0")
            b.insn("B", "out")
            b.label("many")
            b.insn("MOV", "R5, #0x0")
            b.label("mas")
            b.insn("MOV", "R7, #0x0")
            b.label("maz2")
            b.call_addr(CARD_CID_AT, R5, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "man2")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R7, #0x0")
            b.bl_label("rec")
            b.label("man2")
            b.insn("ADD", "R7, #0x1")
            b.insn("CMP", "R7, #0xA")
            b.insn("BLE", "maz2")
            b.insn("ADD", "R5, #0x1")
            b.insn("CMP", "R5, #0x1")
            b.insn("BLE", "mas")
            b.insn("B", "out")
            b.label("mrol")
            b.insn("MOV", "R7, #0x0")
            b.label("mrz")
            b.call_addr(CARD_CID_AT, R4, R7, via=R3)
            b.ldr_const(1, ROLAND_CIDS[0])
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "mrh")
            b.ldr_const(1, ROLAND_CIDS[1])
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "mrn")
            b.label("mrh")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R7, #0x0")
            b.bl_label("rec")
            b.label("mrn")
            b.insn("ADD", "R7, #0x1")
            b.insn("CMP", "R7, #0x4")
            b.insn("BLE", "mrz")
            b.insn("B", "out")
            b.label("mdeck")
            b.insn("MOV", "R0, #0x0")
            b.insn("MOV", "R1, #0x0")
            b.label("mzh")
            b.insn("ADD", "R2, SP, #0x8")
            b.insn("STRB", "R0, [R2, R1]")
            b.insn("ADD", "R1, #0x1")
            b.insn("CMP", "R1, #0x10")
            b.insn("BLT", "mzh")
            b.insn("LSR", "R0, R5, #0x8")
            b.insn("ADD", "R2, SP, #0x8")
            b.insn("STRB", "R0, [R2, #0x10]")
            b.insn("STRB", "R5, [R2, #0x11]")
            b.ldr_const(2, HOL['HISTCB'] | 1)
            b.bl_label("deck")
            b.ldr_const(2, HOL['LVCB'] | 1)
            b.bl_label("deck")
            b.insn("ADD", "R6, R0, #0x0")
            b.label("out")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("ADD", "SP, #0x20")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("rec")
            b.insn("PUSH", "{LR}")
            b.call_addr(RECORD, R0, R1, 0, via=R3)
            b.insn("ADD", "R6, #0x1")
            b.insn("POP", "{PC}")
            b.label("deck")
            b.insn("PUSH", "{LR}")
            b.insn("SUB", "SP, #0x8")
            b.ldr_const(0, FIRE_WARRIOR)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.ldr_const(1, HORN)
            b.insn("ADD", "R3, SP, #0x14")
            b.call_addr(CRIT_WORKER)
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{PC}")
            return b


        def ho_eqspcb_stub() -> EffectBuilder:
            """Worker callback ([sp] = &card word): an Equip Spell (race 23, spell type 3)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R4, R0, #0x12")
            b.insn("LSR", "R4, R4, #0x12")
            b.call("get_race", R4, via=R3)
            b.insn("CMP", f"R0, #0x{RACE_SPELL:X}")
            b.insn("BNE", "no")
            b.call_addr(GET_SPELLTYPE, R4, via=R3)
            b.insn("CMP", f"R0, #0x{SPELL_EQUIP:X}")
            b.insn("BNE", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b


        def ho_histcb_stub() -> EffectBuilder:
            """Worker callback ([sp] = &card word, [sp+4] = ctx): hist[Level]++ (Level < 16); never records (0)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDR", "R4, [SP, #0xC]")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call("cid_level", via=R3)
            b.insn("CMP", "R0, #0xF")
            b.insn("BGT", "z")
            b.insn("LDRB", "R1, [R4, R0]")
            b.insn("ADD", "R1, #0x1")
            b.insn("STRB", "R1, [R4, R0]")
            b.label("z")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b


        def ho_lvcb_stub() -> EffectBuilder:
            """Worker callback ([sp] = &card word, [sp+4] = ctx {{hist[16], rem, k}}): keep Level L iff 1 <= L <= rem and
            (L == rem or (k >= 2 and the rest rem - L is reachable in k - 1 more picks from the Deck minus this copy)):
            1 more pick: hist[r] >= 1;  2 more: also some a + b = r with hist[a] >= 1, hist[b] >= 1 + (a == b)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("LDR", "R4, [SP, #0x18]")
            b.insn("LDR", "R0, [SP, #0x14]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call("cid_level", via=R3)
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRB", "R6, [R4, #0x10]")
            b.insn("CMP", "R5, R6")
            b.insn("BGT", "no")
            b.insn("BEQ", "yes")
            b.insn("LDRB", "R7, [R4, #0x11]")
            b.insn("CMP", "R7, #0x2")
            b.insn("BLT", "no")
            b.insn("SUB", "R6, R6, R5")
            b.insn("SUB", "R7, #0x1")
            b.insn("LDRB", "R0, [R4, R5]")
            b.insn("SUB", "R0, #0x1")
            b.insn("STRB", "R0, [R4, R5]")
            b.insn("MOV", "R0, #0x0")
            b.insn("CMP", "R6, #0xF")
            b.insn("BGT", "two")
            b.insn("LDRB", "R1, [R4, R6]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BNE", "hit")
            b.label("two")
            b.insn("CMP", "R7, #0x2")
            b.insn("BLT", "fin")
            b.insn("MOV", "R2, #0x1")
            b.label("al")
            b.insn("CMP", "R2, R6")
            b.insn("BGE", "fin")
            b.insn("LDRB", "R1, [R4, R2]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "an")
            b.insn("SUB", "R3, R6, R2")
            b.insn("CMP", "R3, #0xF")
            b.insn("BGT", "an")
            b.insn("LDRB", "R1, [R4, R3]")
            b.insn("CMP", "R2, R3")
            b.insn("BNE", "need1")
            b.insn("SUB", "R1, #0x1")
            b.label("need1")
            b.insn("CMP", "R1, #0x0")
            b.insn("BGT", "hit")
            b.label("an")
            b.insn("ADD", "R2, #0x1")
            b.insn("B", "al")
            b.label("hit")
            b.insn("MOV", "R0, #0x1")
            b.label("fin")
            b.insn("LDRB", "R1, [R4, R5]")
            b.insn("ADD", "R1, #0x1")
            b.insn("STRB", "R1, [R4, R5]")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("yes")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def ho_lock_stub() -> EffectBuilder:
            """New front @0x021BA368 (caller r5 = cid, r7 = side): Ricciardetto's lock verdict (-> Obedience's) first; a pass
            becomes a deny when side r7's turn log holds {0xB, 0x5976, 1} and the cid is not a Warrior."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.call_addr(RCL['LOCK'], via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "out")
            b.insn("ADD", "R0, R7, #0x0")
            b.turnlog_query(R0, HO_LOCKKEY, 1, via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "allow")
            b.call("get_race", R5, via=R3)
            b.insn("CMP", f"R0, #0x{RACE_WARRIOR:X}")
            b.insn("BEQ", "allow")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            b.label("allow")
            b.insn("MOV", "R0, #0x1")
            b.label("out")
            b.insn("POP", "{R4, PC}")
            return b


        def _ho_precheck(tail: int) -> EffectBuilder:
            """NEXT's precheck: list search (r0 key, r1 list, r2 count): key 0x1976 -> 1, else tail-call *tail*."""
            b = EffectBuilder()
            b.ldr_const(3, HORN)
            b.insn("CMP", "R0, R3")
            b.insn("BNE", "miss")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("miss")
            b.ldr_const(3, tail | 1)
            b.insn("BX", "R3")
            return b


        HOSTUBS = {"LEGAL": ho_legal_stub, "COND": ho_cond_stub, "COST": ho_cost_stub, "RES": ho_res_stub, "CRIT": ho_crit_stub,
                  "EQSPCB": ho_eqspcb_stub, "HISTCB": ho_histcb_stub, "LVCB": ho_lvcb_stub, "LOCK": ho_lock_stub,
                  "PRENEG": lambda: _ho_precheck(NEG_TAIL), "PREPOST": lambda: _ho_precheck(POST_TAIL)}


        def apply_horn(rom, ov: bytearray) -> None:
            rows = _rows(ov, CLS0_BASE, CLS0_COUNT, 24, CLS_FMT)
            hits = [i for i, r in enumerate(rows) if r[0] == HORN]
            assert len(hits) == 1 and rows[hits[0]] in (HO_CLS0_STOCK, HO_CLS0_REC), f"HO cls0 rows {hits}"
            struct.pack_into(CLS_FMT, ov, CLS0_BASE + hits[0] * 24 - RAM_BASE, *HO_CLS0_REC)
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, HO_CRIT_REC, HO_CRIT_PHANTOM, "HO criteria row")
            for site, wants, dst in ((NEG_SITE, (NEG_TAIL,), HOL["PRENEG"]), (POST_SITE, (POST_TAIL,), HOL["PREPOST"]),
                                     (LOCK_SITE, (RCL["LOCK"],), HOL["LOCK"])):
                assert _bl_target(ov, site) in wants + (dst,), f"HO site {site:#x} -> {_bl_target(ov, site):#x}"
                ov[site - RAM_BASE:site - RAM_BASE + 4] = _bl(site, dst)
            print("HO cls0 re-pointed, criteria row, negate prechecks x2, Warrior-lock front")


        def verify_horn(rom, ov, check) -> None:
            rows = _rows(ov, CLS0_BASE, CLS0_COUNT, 24, CLS_FMT)
            check([r for r in rows if r[0] == HORN] == [HO_CLS0_REC], "HO cls0: exactly one 0x1976 row (re-pointed)")
            rows = _rows(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT)
            check([r for r in rows if r[0] == HORN] == [HO_CRIT_REC], "HO criteria: exactly one 0x1976 row")
            check([r[0] for r in rows] == sorted(r[0] for r in rows), "HO criteria: sorted")
            for site, dst in ((NEG_SITE, HOL["PRENEG"]), (POST_SITE, HOL["PREPOST"]), (LOCK_SITE, HOL["LOCK"])):
                check(code_reaches(rom, site, dst), f"HO bl @{site:#x} reaches {dst:#x}")


        # =================================================================================================
        # Infernoble Arms 1: Demotion 0x15E3 -> Infernoble Arms - Joyeuse (Equip Spell; notes/infernoble-arms-findings.md)
        #   Equip to any monster, no ATK change (user).  Demotion's own "-2 Levels" lives in the Level recompute
        #   0x021B807C's stack cid table ([sp+0xCC] / [sp+0xD0] = 0x15C7 + 0x1C): both imm8s -> 0x3A (= 0x1601, no card).
        #   E1 cls3 (Spark Blaster's ignition-on-a-face-up-Equip-Spell shape) over 0x0E56: target 1 FIRE Warrior in your GY
        #      (Renaud's add-target 0x02208181 + off-field template 0x02235605, criteria rel 1), then destroy this card.
        #   E2 cls2 over 0x0E69: "sent to the GY because the equipped monster is sent to the GY" = the leave switch's equip
        #      reason bit 0x400000 + [sp+0x144] -> Sword of Dark Rites' accept arm 0x021C9334 (front ahead of Captain
        #      Oliver's @0x021C8216); "You can" SS 1 FIRE Warrior from your hand = Ricciardetto's 0x0220667D + rel 0 0x0223CA51.
        #   One OPT 0x55E3 for both.  Criteria rel 0 / rel 1 via a row front ahead of Ricciardetto's @0x02243BEC (acting
        #   desc cid 0x15E3 && cls3 -> rel 1).
        # =================================================================================================
        JOYEUSE = 0x15E3
        JO_KEY = 0x4000 | JOYEUSE
        DEMOTION_IMMS, DEMOTION_STOCK, DEMOTION_DEAD = (0x021B845C, 0x021B8464), 0x301C, 0x303A   # adds r0,#0x1C -> #0x3A
        SWORD_ACCEPT = 0x021C9335
        JO_CLS3_PHANTOM, JO_CLS2_PHANTOM, JO_CRIT_PHANTOMS = 0x0E56, 0x0E69, (0x1534, 0x167D)   # 0x167D = parked Magician's Rod's phantom (NOT 0x2511: that is tg_warwolf's live E2 populate row)
        JOL = {n: getattr(O5, f"CAVE_IK_JO_{n}") for n in ("E1COND", "E1RES", "E2COND", "E2RES", "LEAVE", "ROW")}
        JORESERVE = {"E1COND": 0x70, "E1RES": 0x90, "E2COND": 0x40, "E2RES": 0x50, "LEAVE": 0x30, "ROW": 0x40}
        JO_CLS3_REC = (JOYEUSE, 0, JOL["E1RES"] | 1, 0, JOL["E1COND"] | 1, 0, TARGET_STEP)
        JO_CLS2_REC = (JOYEUSE, 0, JOL["E2RES"] | 1, 0, JOL["E2COND"] | 1, TAG_YOU_CAN, 0)
        JO_CRIT_RECS = ((JOYEUSE, 0xFFFF, HAND_SS_H, FIRE_WARRIOR),               # rel 0: E2 hand FIRE Warrior
                        (JOYEUSE, 0xFFFF, 0x0223CA11, FIRE_WARRIOR))               # rel 1: E1 GY FIRE Warrior (target)


        def jo_e1cond_stub() -> EffectBuilder:
            """cls3 +0C: this card face-up in a S/T zone and equipped to something, OPT 0x55E3 clear, >= 1 FIRE Warrior in your
            GY (0x0223CA11's own worker call) -> 1."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R6, [R4, #0x3]")
            b.insn("CMP", "R6, #0x5")
            b.insn("BLT", "no")
            b.insn("CMP", "R6, #0x9")
            b.insn("BGT", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(EQUIP_TARGET_OF, R0, R6, via=R3)
            b.ldr_const(1, 0xffff)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "no")
            _used(b, JO_KEY, "r4", "no")
            b.ldr_const(0, FIRE_WARRIOR)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x1")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(GY_WORKER, R0, JOYEUSE, 0, 0)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def jo_e1res_stub() -> EffectBuilder:
            """cls3 +04: phase 0x80 (first call) OPT check + stamp; Renaud's add-target 0x02208181 until it returns 0; then
            destroy this card (0x0224A924 re-check + 0x021CF388) once (stage byte desc[+0x1E])."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x1E]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "dest")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, JO_KEY, "r4", "zero")
            _post(b, JO_KEY)
            b.label("nat")
            b.call_addr(ADD_TARGET_RES, R4, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "ret")
            b.insn("MOV", "R0, #0x1")
            b.insn("STRB", "R0, [R4, #0x1E]")
            b.label("dest")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R1, R0, #0x18")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R2, R0, #0x10")
            b.insn("LSR", "R2, R2, #0x18")
            b.insn("CMP", "R2, #0x9")
            b.insn("BGT", "zero")
            b.insn("PUSH", "{R1, R2}")
            b.call_addr(VALID_AT, R4, via=R3)
            b.insn("POP", "{R1, R2}")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.call_addr(DESTROY_AT, R4, via=R3)
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def jo_e2cond_stub() -> EffectBuilder:
            """cls2 +0C (desc, arg): OPT 0x55E3 clear -> Stygian's f1 (free zone, may SS, >= 1 hand candidate, rel 0)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            _used(b, JO_KEY, "r4", "no")
            b.call_addr(STYGIAN_F1, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def jo_e2res_stub() -> EffectBuilder:
            """cls2 +04: phase 0x80 OPT check + stamp; then Ricciardetto's hand SS 0x0220667D (criteria rel 0)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, JO_KEY, "r4", "zero")
            _post(b, JO_KEY)
            b.label("nat")
            b.call_addr(HAND_SS_ANY, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def jo_leave_stub() -> EffectBuilder:
            """BL @0x021C8216 (leave switch; r4 = cid, [sp+0xC] = reason, [sp+0x144] = to the GY): 0x15E3 going to the GY
            with reason bit 0x400000 (its equipped monster went to the GY) -> Sword of Dark Rites' accept arm 0x021C9334
            (`movs r0,#1` -> post flag [sp+0x18]); everything else tail-jumps to Captain Oliver's front, lr intact."""
            b = EffectBuilder()
            b.ldr_const(1, JOYEUSE)
            b.insn("CMP", "R4, R1")
            b.insn("BNE", "next")
            b.insn("LDR", "R1, [SP, #0x144]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "next")
            b.insn("LDR", "R1, [SP, #0xC]")
            b.insn("LSL", "R1, R1, #0x9")
            b.insn("BPL", "next")
            b.ldr_const(1, SWORD_ACCEPT)
            b.insn("BX", "R1")
            b.label("next")
            b.ldr_const(1, COL['LEAVE'] | 1)
            b.insn("BX", "R1")
            return b


        def jo_row_stub() -> EffectBuilder:
            """FRONT at the criteria row hook 0x02243BEC ahead of Ricciardetto's: row cid r5 == 0x15E3 AND acting desc cid
            == 0x15E3 AND desc[+5] == 3 (cls3 = E1) -> r4 = 1 (rel 1 = GY), the common tail; else Ricciardetto's front."""
            from otn_enhanced.effects import criteria_row_hook as crh
            b = EffectBuilder()
            b.ldr_const(1, JOYEUSE)
            b.insn("CMP", "R5, R1")
            b.insn("BNE", "next")
            b.ldr_const(3, crh.ACTING_DESC)
            b.insn("LDR", "R3, [R3, #0x50]")
            b.insn("CMP", "R3, #0x0")
            b.insn("BEQ", "next")
            b.insn("LDRH", "R0, [R3, #0x0]")
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "next")
            b.insn("LDRB", "R0, [R3, #0x5]")
            b.insn("CMP", "R0, #0x3")
            b.insn("BNE", "next")
            b.insn("MOV", "R4, #0x1")
            b.ldr_const(3, crh.ROWHOOK_TAIL | 1)
            b.insn("BX", "R3")
            b.label("next")
            b.ldr_const(3, RCL['ROW'] | 1)
            b.insn("BX", "R3")
            return b


        JOSTUBS = {"E1COND": jo_e1cond_stub, "E1RES": jo_e1res_stub, "E2COND": jo_e2cond_stub, "E2RES": jo_e2res_stub,
                  "LEAVE": jo_leave_stub, "ROW": jo_row_stub}


        def apply_joyeuse(rom, ov: bytearray) -> None:
            from otn_enhanced.effects import criteria_row_hook as crh
            for a in DEMOTION_IMMS:
                o = a - RAM_BASE
                assert struct.unpack_from("<H", ov, o)[0] in (DEMOTION_STOCK, DEMOTION_DEAD), f"JO Demotion imm @{a:#x} moved"
                struct.pack_into("<H", ov, o, DEMOTION_DEAD)
            insert_row(ov, CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, JO_CLS3_REC, JO_CLS3_PHANTOM, "JO E1 cls3")
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, JO_CLS2_REC, JO_CLS2_PHANTOM, "JO E2 cls2")
            _append_rows(ov, JO_CRIT_RECS, JO_CRIT_PHANTOMS)
            for site, wants, dst in ((LEAVE_SITE, (COL["LEAVE"],), JOL["LEAVE"]), (crh.ROWHOOK_SITE, (RCL["ROW"],), JOL["ROW"])):
                assert _bl_target(ov, site) in wants + (dst,), f"JO site {site:#x} -> {_bl_target(ov, site):#x}"
                ov[site - RAM_BASE:site - RAM_BASE + 4] = _bl(site, dst)
            print("JO Demotion Level arm retired, cls3 + cls2 + criteria rel 0/1, leave + row fronts")


        def verify_joyeuse(rom, ov, check) -> None:
            from otn_enhanced.effects import criteria_row_hook as crh
            check(all(struct.unpack_from("<H", ov, a - RAM_BASE)[0] == DEMOTION_DEAD for a in DEMOTION_IMMS),
                  "JO Demotion's Level-recompute cid slots -> 0x1601")
            for label, base, count, stride, fmt, recs in (("cls3", CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, [JO_CLS3_REC]),
                                                          ("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, [JO_CLS2_REC]),
                                                          ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, list(JO_CRIT_RECS))):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == JOYEUSE] == recs, f"JO {label}: exactly the 0x15e3 row(s), in order")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"JO {label}: sorted")
            check(_bl_target(ov, LEAVE_SITE) in LEAVE_FRONTS, f"JO bl @{LEAVE_SITE:#x} -> a leave-chain front")
            check(_bl_target(ov, crh.ROWHOOK_SITE) in (JOL["ROW"], O5.CAVE_IK_DU_ROW), f"JO row front (or Durendal's ahead of it)")


        # =================================================================================================
        # Infernoble Arms 2: Rod of the Mind's Eye 0x1663 -> Infernoble Arms - Durendal (Equip Spell)
        #   Rod's own per-cid code retired: the battle-damage stack table @0x02199C44 (0x16A3 - 0x40 -> - 0x2C = 0x1677,
        #   no card).  NOT the Equip-Spell activation tree @0x021F076E: that arm is reached by a branch with r0 = 0x1EFA,
        #   so it builds 0x1EF3 (another card) -- Rod is not in that tree (baseimm_scan's straight-line tracking misread it).
        #   E1 cls3 over 0x0E5E: add 1 Level 5 or lower FIRE Warrior from your Deck (0x02207EF5, criteria rel 0 Deck
        #      0x0223CAD9 word 0x7C940002), then destroy this card.
        #   E2 cls2 over 0x0E6B: Joyeuse's leave arm (0x400000 -> Sword of Dark Rites' accept); "You can" target 1 Level 5 or
        #      lower FIRE Warrior in your GY (0x02235605, rel 1 GY 0x0223CA11) -> Junk Synchron's revive 0x02207191; Warrior-only
        #      SS for the rest of the turn = Ricciardetto's lock node {0x4FE6, kind 1} (its front reads it).
        #   One OPT 0x5663.  Row front ahead of Joyeuse's: acting desc cid 0x1663 && cls2 -> rel 1.
        # =================================================================================================
        DURENDAL = 0x1663
        DU_KEY = 0x4000 | DURENDAL
        DU_WORD = 0x7C940002                                   # FIRE Warrior, Level <= 5
        ROD_BATTLE_IMM, ROD_BATTLE_STOCK, ROD_BATTLE_DEAD = 0x02199C44, 0x3840, 0x382C   # subs r0,#0x40 -> #0x2C
        DU_CLS3_PHANTOM, DU_CLS2_PHANTOM, DU_CRIT_PHANTOMS = 0x0E5E, 0x0E6B, (0x0E66, 0x14DD)
        DUL = {n: getattr(O5, f"CAVE_IK_DU_{n}") for n in ("E1COND", "E1RES", "E2COND", "E2RES", "LEAVE", "ROW")}
        DURESERVE = {"E1COND": 0x70, "E1RES": 0x90, "E2COND": 0x40, "E2RES": 0x60, "LEAVE": 0x30, "ROW": 0x40}
        DU_CLS3_REC = (DURENDAL, 0, DUL["E1RES"] | 1, 0, DUL["E1COND"] | 1, 0, 0)
        DU_CLS2_REC = (DURENDAL, 0, DUL["E2RES"] | 1, 0, DUL["E2COND"] | 1, TAG_YOU_CAN, TARGET_STEP)
        DU_CRIT_RECS = ((DURENDAL, 0xFFFF, 0x0223CAD9, DU_WORD),                 # rel 0: E1 Deck Lv<=5 FIRE Warrior
                        (DURENDAL, 0xFFFF, 0x0223CA11, DU_WORD))                 # rel 1: E2 GY Lv<=5 FIRE Warrior (target)


        def du_e1cond_stub() -> EffectBuilder:
            """cls3 +0C: face-up in a S/T zone and equipped, OPT 0x5663 clear, >= 1 Level <= 5 FIRE Warrior in the Deck
            (0x0223CAD9's own worker call) -> 1."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R6, [R4, #0x3]")
            b.insn("CMP", "R6, #0x5")
            b.insn("BLT", "no")
            b.insn("CMP", "R6, #0x9")
            b.insn("BGT", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(EQUIP_TARGET_OF, R0, R6, via=R3)
            b.ldr_const(1, 0xffff)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "no")
            _used(b, DU_KEY, "r4", "no")
            b.ldr_const(0, DU_WORD)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(CRIT_WORKER, R0, DURENDAL, 0, 0)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def du_e1res_stub() -> EffectBuilder:
            """cls3 +04: phase 0x80 (first call) OPT check + stamp; the Deck add 0x02207EF5 until it returns 0; then destroy
            this card once (stage byte desc[+0x1E])."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x1E]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "dest")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, DU_KEY, "r4", "zero")
            _post(b, DU_KEY)
            b.label("nat")
            b.call_addr(ADD_FROM_DECK_RES, R4, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "ret")
            b.insn("MOV", "R0, #0x1")
            b.insn("STRB", "R0, [R4, #0x1E]")
            b.label("dest")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R1, R0, #0x18")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R2, R0, #0x10")
            b.insn("LSR", "R2, R2, #0x18")
            b.insn("CMP", "R2, #0x9")
            b.insn("BGT", "zero")
            b.insn("PUSH", "{R1, R2}")
            b.call_addr(VALID_AT, R4, via=R3)
            b.insn("POP", "{R1, R2}")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.call_addr(DESTROY_AT, R4, via=R3)
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def du_e2cond_stub() -> EffectBuilder:
            """cls2 +0C (desc, arg): OPT 0x5663 clear -> Junk Synchron's 'a legal candidate in the list zone' 0x021F03B5."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            _used(b, DU_KEY, "r4", "no")
            b.call_addr(JUNK_COND, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def du_e2res_stub() -> EffectBuilder:
            """cls2 +04: phase 0x80 OPT check + stamp + Ricciardetto's Warrior-lock node {0x4FE6, kind 1} (rest of the turn);
            then Junk Synchron's revive 0x02207191 (the declared GY target)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, DU_KEY, "r4", "zero")
            _post(b, DU_KEY)
            _post(b, RC_LOCKKEY)
            b.label("nat")
            b.call_addr(REVIVE_RES, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def du_leave_stub() -> EffectBuilder:
            """BL @0x021C8216 ahead of Joyeuse's front: 0x1663 to the GY with reason bit 0x400000 -> Sword of Dark Rites'
            accept arm; else Joyeuse's front, lr intact."""
            b = EffectBuilder()
            b.ldr_const(1, DURENDAL)
            b.insn("CMP", "R4, R1")
            b.insn("BNE", "next")
            b.insn("LDR", "R1, [SP, #0x144]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "next")
            b.insn("LDR", "R1, [SP, #0xC]")
            b.insn("LSL", "R1, R1, #0x9")
            b.insn("BPL", "next")
            b.ldr_const(1, SWORD_ACCEPT)
            b.insn("BX", "R1")
            b.label("next")
            b.ldr_const(1, JOL['LEAVE'] | 1)
            b.insn("BX", "R1")
            return b


        def du_row_stub() -> EffectBuilder:
            """Row front ahead of Joyeuse's: row cid 0x1663 && acting desc cid 0x1663 && cls2 (E2) -> rel 1 (GY)."""
            from otn_enhanced.effects import criteria_row_hook as crh
            b = EffectBuilder()
            b.ldr_const(1, DURENDAL)
            b.insn("CMP", "R5, R1")
            b.insn("BNE", "next")
            b.ldr_const(3, crh.ACTING_DESC)
            b.insn("LDR", "R3, [R3, #0x50]")
            b.insn("CMP", "R3, #0x0")
            b.insn("BEQ", "next")
            b.insn("LDRH", "R0, [R3, #0x0]")
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "next")
            b.insn("LDRB", "R0, [R3, #0x5]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BNE", "next")
            b.insn("MOV", "R4, #0x1")
            b.ldr_const(3, crh.ROWHOOK_TAIL | 1)
            b.insn("BX", "R3")
            b.label("next")
            b.ldr_const(3, JOL['ROW'] | 1)
            b.insn("BX", "R3")
            return b


        DUSTUBS = {"E1COND": du_e1cond_stub, "E1RES": du_e1res_stub, "E2COND": du_e2cond_stub, "E2RES": du_e2res_stub,
                  "LEAVE": du_leave_stub, "ROW": du_row_stub}


        def apply_durendal(rom, ov: bytearray) -> None:
            from otn_enhanced.effects import criteria_row_hook as crh
            for a, stock, dead in ((ROD_BATTLE_IMM, ROD_BATTLE_STOCK, ROD_BATTLE_DEAD),):
                o = a - RAM_BASE
                assert struct.unpack_from("<H", ov, o)[0] in (stock, dead), f"DU Rod arm @{a:#x} moved"
                struct.pack_into("<H", ov, o, dead)
            insert_row(ov, CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, DU_CLS3_REC, DU_CLS3_PHANTOM, "DU E1 cls3")
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, DU_CLS2_REC, DU_CLS2_PHANTOM, "DU E2 cls2")
            _append_rows(ov, DU_CRIT_RECS, DU_CRIT_PHANTOMS)
            for site, wants, dst in ((LEAVE_SITE, (JOL["LEAVE"],), DUL["LEAVE"]), (crh.ROWHOOK_SITE, (JOL["ROW"],), DUL["ROW"])):
                assert _bl_target(ov, site) in wants + (dst,), f"DU site {site:#x} -> {_bl_target(ov, site):#x}"
                ov[site - RAM_BASE:site - RAM_BASE + 4] = _bl(site, dst)
            print("DU Rod's battle-damage slot retired, cls3 + cls2 + criteria rel 0/1, leave + row fronts")


        def verify_durendal(rom, ov, check) -> None:
            from otn_enhanced.effects import criteria_row_hook as crh
            check(struct.unpack_from("<H", ov, 0x021F076E - RAM_BASE)[0] == 0x1FC0, "DU 0x021F076E stock (0x1EF3's arm, not Rod's)")
            check(struct.unpack_from("<H", ov, ROD_BATTLE_IMM - RAM_BASE)[0] == ROD_BATTLE_DEAD, "DU Rod's battle-damage slot -> 0x1677")
            for label, base, count, stride, fmt, recs in (("cls3", CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, [DU_CLS3_REC]),
                                                          ("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, [DU_CLS2_REC]),
                                                          ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, list(DU_CRIT_RECS))):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == DURENDAL] == recs, f"DU {label}: exactly the 0x1663 row(s), in order")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"DU {label}: sorted")
            check(_bl_target(ov, LEAVE_SITE) in LEAVE_FRONTS, f"DU bl @{LEAVE_SITE:#x} -> a leave-chain front")
            check(_bl_target(ov, crh.ROWHOOK_SITE) == DUL["ROW"], f"DU bl @{crh.ROWHOOK_SITE:#x} -> row front")


        # =================================================================================================
        # Infernoble Arms 3: Broken Bamboo Sword 0x1C39 -> Infernoble Arms - Almace (Equip Spell)
        #   Bamboo's own per-cid code retired: stack cid table @0x021C42A6 (0x1D01 - 0xC8 -> - 0x17 = 0x1CEA, no card).
        #   ONE criteria row over 0x19C0, handler mode = param >> 16: 0 = E2 FIRE Warriors in your GY + banished (the native
        #   target template 0x02235605 passes 0), 1 = E1 "Infernoble Arms" (Joyeuse / Durendal / Hauteclere) in your Deck +
        #   GY, 2 = your face-up monsters (the Arms equip to any monster).
        #   E1 cls3 over 0x0E62: own machine -- pick the Arms (1), pick your monster (2), zone UI, move (Deck 0xD / GY 0xE from
        #      the pick's list meta), equip link 0x021C4A68 (kind 0xA), then destroy this card.
        #   E2 cls2 over 0x0E49: Joyeuse's leave arm (DU chain); target (0x02235605, mode 0) -> Renaud's add-target 0x02208181
        #      (GY and banished).  One OPT 0x5C39.
        # =================================================================================================
        ALMACE = 0x1C39
        LEAVE_FRONTS = (O5.CAVE_IK_BR_LEAVE, O5.CAVE_IK_CO_LEAVE, O5.CAVE_IK_JO_LEAVE, O5.CAVE_IK_DU_LEAVE,
                        O5.CAVE_IK_AL_LEAVE, O5.CAVE_PG_LEAVE)  # the leave-switch front chain, head .. tail (any may be the head; Phoenix Gearblade's sits ahead)
        HAUTECLERE = 0x1F71
        ARMS_CIDS = (JOYEUSE, DURENDAL, ALMACE, HAUTECLERE)        # "Infernoble Arms" / "Noble Arms" (user)
        AL_KEY = 0x4000 | ALMACE
        BAMBOO_IMM, BAMBOO_STOCK, BAMBOO_DEAD = 0x021C42A6, 0x38C8, 0x3817   # subs r0,#0xC8 -> #0x17
        AL_CLS3_PHANTOM, AL_CLS2_PHANTOM, AL_CRIT_PHANTOM = 0x0E62, 0x0E49, 0x19C0
        MSG_EQUIP_WHICH, MSG_EQUIP_TO = 0x139, 0x79
        ALL = {n: getattr(O5, f"CAVE_IK_AL_{n}") for n in ("E1COND", "E1RES", "E2COND", "E2RES", "LEAVE", "CRIT", "ARMCB")}
        ALRESERVE = {"E1COND": 0x90, "E1RES": 0x1e0, "E2COND": 0x50, "E2RES": 0x50, "LEAVE": 0x30, "CRIT": 0xd0, "ARMCB": 0x40}
        AL_CLS3_REC = (ALMACE, 0, ALL["E1RES"] | 1, 0, ALL["E1COND"] | 1, 0, 0)
        AL_CLS2_REC = (ALMACE, 0, ALL["E2RES"] | 1, 0, ALL["E2COND"] | 1, TAG_YOU_CAN, TARGET_STEP)
        AL_CRIT_REC = (ALMACE, 0xFFFF, ALL["CRIT"] | 1, 0x00000000)


        def _al_count(b: EffectBuilder, param: int, no: str) -> None:
            """ROW_COUNT_C(desc[+2], 0x1C39, param) == 0 -> *no* (desc in r4)."""
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.ldr_const(1, ALMACE)
            b.ldr_const(2, param)
            b.call_addr(ROW_COUNT_C, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", f"{no}")


        def al_e1cond_stub() -> EffectBuilder:
            """cls3 +0C: face-up in a S/T zone and equipped, OPT 0x5C39 clear, a free S/T zone, >= 1 Arms in Deck / GY and
            >= 1 face-up monster you control -> 1."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R6, [R4, #0x3]")
            b.insn("CMP", "R6, #0x5")
            b.insn("BLT", "no")
            b.insn("CMP", "R6, #0x9")
            b.insn("BGT", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(EQUIP_TARGET_OF, R0, R6, via=R3)
            b.ldr_const(1, 0xffff)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "no")
            _used(b, AL_KEY, "r4", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_ST, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")
            _al_count(b, 0x10000, "no")
            _al_count(b, 0x20000, "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def al_e1res_stub() -> EffectBuilder:
            """cls3 +04, phases on [0x0229AAFC+0x70]:
               0x80 chain push; OPT check + stamp; still there; a free S/T zone + both pools -> message 0x139 -> 0x7F
               0x7F picker mode 1 | 0x7E source zone (list meta) -> desc[+0x18], ref -> desc[+0x1C]; message 0x79
               0x7D picker mode 2 | 0x7C target zone -> desc[+0x1E]; zone UI | 0x7B move (Deck 0xD / GY 0xE)
               0x7A equip link (kind 0xA) to (side, target zone) -> 0x79 | 0x79 destroy this card | end: chain pop -> 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "d1")
            b.insn("B", "p80")
            b.label("d1")
            b.insn("CMP", "R0, #0x7F")
            b.insn("BEQ", "p7f")
            b.insn("CMP", "R0, #0x7E")
            b.insn("BEQ", "p7e")
            b.insn("CMP", "R0, #0x7D")
            b.insn("BEQ", "p7d")
            b.insn("CMP", "R0, #0x7C")
            b.insn("BEQ", "p7c")
            b.insn("CMP", "R0, #0x7B")
            b.insn("BEQ", "p7b")
            b.insn("CMP", "R0, #0x7A")
            b.insn("BNE", "d2")
            b.insn("B", "p7a")
            b.label("d2")
            b.insn("CMP", "R0, #0x79")
            b.insn("BNE", "d3")
            b.insn("B", "p79")
            b.label("d3")
            b.insn("B", "end")
            b.label("p7f")
            b.call_addr(AS_PICKER, R5, 6, ALMACE, 0x10000, via=R7)
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("p7e")
            _ho_pickloc(b)
            b.insn("STRH", "R2, [R4, #0x18]")
            b.call_addr(AS_READBACK, via=R3)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R0, R0, R1")
            b.insn("STRH", "R0, [R4, #0x1C]")
            b.call_addr(AS_MESSAGE, R5, MSG_EQUIP_TO, via=R3)
            b.insn("MOV", "R0, #0x7D")
            b.insn("B", "ret")
            b.label("p7d")
            b.call_addr(AS_PICKER, R5, 6, ALMACE, 0x20000, via=R7)
            b.insn("MOV", "R0, #0x7C")
            b.insn("B", "ret")
            b.label("p7c")
            _ho_pickloc(b)
            b.insn("STRH", "R2, [R4, #0x1E]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.insn("LDRH", "R2, [R4, #0x1C]")
            b.call_addr(ZONE_UI, via=R3)
            b.insn("MOV", "R0, #0x7B")
            b.insn("B", "ret")
            b.label("p7b")
            b.ldr_const(0, ZONE_PICK)
            b.insn("LDRH", "R0, [R0, #0x24]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("LDRH", "R1, [R4, #0x18]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R2, [R4, #0x1C]")
            b.call_addr(MOVER, R0, R1, R2, R5, via=R7)
            b.insn("MOV", "R0, #0x7A")
            b.insn("B", "ret")
            b.label("p7a")
            b.ldr_const(0, ZONE_PICK)
            b.insn("LDRH", "R1, [R0, #0x24]")
            b.insn("LSL", "R1, R1, #0x18")
            b.insn("LSR", "R1, R1, #0x10")
            b.insn("ORR", "R1, R5")
            b.insn("LDRH", "R2, [R4, #0x1E]")
            b.insn("LSL", "R2, R2, #0x8")
            b.insn("ORR", "R2, R5")
            b.insn("MOV", "R3, #0xA")
            b.call_addr(EQUIP_LINK, R5, via=R7)
            b.insn("MOV", "R0, #0x79")
            b.insn("B", "ret")
            b.label("p79")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R1, R0, #0x18")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R2, R0, #0x10")
            b.insn("LSR", "R2, R2, #0x18")
            b.insn("CMP", "R2, #0x9")
            b.insn("BGT", "end")
            b.insn("STR", "R1, [SP, #0x0]")
            b.insn("STR", "R2, [SP, #0x4]")
            b.call_addr(VALID_AT, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "end")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDR", "R1, [SP, #0x0]")
            b.insn("LDR", "R2, [SP, #0x4]")
            b.call_addr(DESTROY_AT, via=R3)
            b.insn("B", "end")
            b.label("p80")
            b.call_addr(CHAIN_PUSH, via=R3)
            _used(b, AL_KEY, "r4", "end")
            _post(b, AL_KEY)
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.call_addr(VALIDATE, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "end")
            b.call_addr(FREE_ST, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "end")
            _al_count(b, 0x10000, "end")
            _al_count(b, 0x20000, "end")
            b.call_addr(AS_MESSAGE, R5, MSG_EQUIP_WHICH, via=R3)
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("end")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def al_e2cond_stub() -> EffectBuilder:
            """cls2 +0C (desc, arg): OPT 0x5C39 clear and >= 1 FIRE Warrior of yours in the GY / banished (mode 0) -> 1."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            _used(b, AL_KEY, "r4", "no")
            _al_count(b, 0, "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def al_e2res_stub() -> EffectBuilder:
            """cls2 +04: phase 0x80 OPT check + stamp; then Renaud's add-target 0x02208181 (GY or banished target)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, AL_KEY, "r4", "zero")
            _post(b, AL_KEY)
            b.label("nat")
            b.call_addr(ADD_TARGET_RES, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def al_leave_stub() -> EffectBuilder:
            """BL @0x021C8216 ahead of Durendal's front: 0x1C39 to the GY with reason bit 0x400000 -> Sword of Dark Rites'
            accept arm; else Durendal's front, lr intact."""
            b = EffectBuilder()
            b.ldr_const(1, ALMACE)
            b.insn("CMP", "R4, R1")
            b.insn("BNE", "next")
            b.insn("LDR", "R1, [SP, #0x144]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "next")
            b.insn("LDR", "R1, [SP, #0xC]")
            b.insn("LSL", "R1, R1, #0x9")
            b.insn("BPL", "next")
            b.ldr_const(1, SWORD_ACCEPT)
            b.insn("BX", "R1")
            b.label("next")
            b.ldr_const(1, DUL['LEAVE'] | 1)
            b.insn("BX", "R1")
            return b


        def al_crit_stub() -> EffectBuilder:
            """Criteria handler (row r0, side r1, param r2), mode = param >> 16:
               0 = your GY (worker, flags 0) + banished (worker, flags 0xC) FIRE Warriors;  1 = Deck (worker flags 2) + GY
               Spells kept by AL_ARMCB (Joyeuse / Durendal / Hauteclere);  2 = your face-up monsters (zones 0..4) -> RECORD."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("ADD", "R4, R1, #0x0")
            b.insn("MOV", "R6, #0x0")
            b.insn("LSR", "R0, R2, #0x10")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "m1")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "m2")
            b.ldr_const(0, FIRE_WARRIOR)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R2, #0x0")
            b.bl_label("gyw")
            b.insn("ADD", "R6, R0, #0x0")
            b.ldr_const(0, FIRE_WARRIOR)
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0xC")
            b.insn("STR", "R0, [SP, #0x4]")
            b.call_addr(BAN_WORKER, R4, ALMACE, 0, 0)
            b.insn("ADD", "R6, R6, R0")
            b.insn("B", "out")
            b.label("m1")
            b.insn("MOV", "R0, #0x4")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.call_addr(CRIT_WORKER, R4, ALMACE, ALL['ARMCB'] | 1, 0)
            b.insn("ADD", "R6, R0, #0x0")
            b.insn("MOV", "R0, #0x4")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.ldr_const(2, ALL['ARMCB'] | 1)
            b.bl_label("gyw")
            b.insn("ADD", "R6, R6, R0")
            b.insn("B", "out")
            b.label("m2")
            b.insn("MOV", "R7, #0x0")
            b.label("mz")
            b.call_addr(FACE_UP, R4, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "mn")
            b.call_addr(CARD_CID_AT, R4, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "mn")
            b.call_addr(RECORD, R4, R7, 0, via=R3)
            b.insn("ADD", "R6, #0x1")
            b.label("mn")
            b.insn("ADD", "R7, #0x1")
            b.insn("CMP", "R7, #0x4")
            b.insn("BLE", "mz")
            b.label("out")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("gyw")
            b.insn("PUSH", "{LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("LDR", "R0, [SP, #0xC]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("LDR", "R0, [SP, #0x10]")
            b.insn("STR", "R0, [SP, #0x4]")
            b.call_addr(GY_WORKER, R4, ALMACE, R2, 0)
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{PC}")
            return b


        def al_armcb_stub() -> EffectBuilder:
            """Worker callback ([sp] = &card word): cid is Joyeuse, Durendal or Hauteclere (an "Infernoble Arms" but Almace)."""
            return _cid_in_cb(tuple(c for c in ARMS_CIDS if c != ALMACE))


        ALSTUBS = {"E1COND": al_e1cond_stub, "E1RES": al_e1res_stub, "E2COND": al_e2cond_stub, "E2RES": al_e2res_stub,
                  "LEAVE": al_leave_stub, "CRIT": al_crit_stub, "ARMCB": al_armcb_stub}


        def apply_almace(rom, ov: bytearray) -> None:
            o = BAMBOO_IMM - RAM_BASE
            assert struct.unpack_from("<H", ov, o)[0] in (BAMBOO_STOCK, BAMBOO_DEAD), "AL Bamboo slot moved"
            struct.pack_into("<H", ov, o, BAMBOO_DEAD)
            insert_row(ov, CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, AL_CLS3_REC, AL_CLS3_PHANTOM, "AL E1 cls3")
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, AL_CLS2_REC, AL_CLS2_PHANTOM, "AL E2 cls2")
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, AL_CRIT_REC, AL_CRIT_PHANTOM, "AL criteria row")
            assert _bl_target(ov, LEAVE_SITE) in (DUL["LEAVE"], ALL["LEAVE"]), f"AL leave site -> {_bl_target(ov, LEAVE_SITE):#x}"
            ov[LEAVE_SITE - RAM_BASE:LEAVE_SITE - RAM_BASE + 4] = _bl(LEAVE_SITE, ALL["LEAVE"])
            print("AL Bamboo slot retired, cls3 + cls2 + criteria row, leave front")


        def verify_almace(rom, ov, check) -> None:
            check(struct.unpack_from("<H", ov, BAMBOO_IMM - RAM_BASE)[0] == BAMBOO_DEAD, "AL Bamboo's stack cid slot -> 0x1CEA")
            for label, base, count, stride, fmt, recs in (("cls3", CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, [AL_CLS3_REC]),
                                                          ("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, [AL_CLS2_REC]),
                                                          ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, [AL_CRIT_REC])):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == ALMACE] == recs, f"AL {label}: exactly the 0x1c39 row")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"AL {label}: sorted")
            check(_bl_target(ov, LEAVE_SITE) in LEAVE_FRONTS, f"AL bl @{LEAVE_SITE:#x} -> a leave-chain front")


        # =================================================================================================
        # Infernoble Arms, shared: their E2 is "IF...: You can" -> must not miss timing (user: Synchro Material
        #   case).  "You can" triggers go through the miss-timing test 0x021EE0E0; its node 0x021EE10C (r3 = cid) is fronted
        #   by Maugis's ov3 stub (-> Eva -> Shadow Mist ...).  AR_MISS sits ahead of it: an Arms cid -> return with Z set
        #   (= the test's IF-card tree hit, never miss); else tail-jump to Maugis's front, registers intact (r1 dead).
        # =================================================================================================
        ARL = {"MISS": O5.CAVE_IK_AR_MISS, "NACB": O5.CAVE_IK_AR_NACB}
        ARRESERVE = {"MISS": 0x40, "NACB": 0x60}


        # Knights whose printed trigger is "If ..." (user 2026-11-06: Copycat -> Ogier "missed timing").  Maugis is already
        #   never-miss in the next front.  Not in ARMS_CIDS: that tuple also drives the Arms-only pick filters.
        IF_KNIGHT_CIDS = (OGIER, RENAUD, RICC, CAPROL, CHARLES)
        AR_MISS_CIDS = ARMS_CIDS + IF_KNIGHT_CIDS


        def ar_miss_stub() -> EffectBuilder:
            """r3 = cid.  Walk a zero-terminated halfword table (inline after the code; 14 insns = 28 B before it); hit ->
            return with Z set (= never miss, flags from the CMP survive POP), else tail-jump to Maugis's front.  r2 is saved
            because only r1 is known dead at this node."""
            b = EffectBuilder()
            b.insn("PUSH", "{R2}")
            b.ldr_const(1, O5.CAVE_IK_AR_MISS + 28)
            b.label("loop")
            b.insn("LDRH", "R2, [R1, #0]")
            b.insn("CMP", "R2, #0")
            b.insn("BEQ", "miss")
            b.insn("CMP", "R3, R2")
            b.insn("BEQ", "hit")
            b.insn("ADD", "R1, #2")
            b.insn("B", "loop")
            b.label("hit")
            b.insn("POP", "{R2}")
            b.insn("BX", "LR")
            b.label("miss")
            b.insn("POP", "{R2}")
            b.ldr_const(1, cave3.CAVE3_IK_M_MISS | 1)
            b.insn("BX", "R1")
            for c in AR_MISS_CIDS + (0,):
                b.raw(c)
            return b


        def ar_nacb_stub() -> EffectBuilder:
            """Worker callback for Ogier C2 (Deck) and Maugis C2 (GY + banished), user 2026-10-20: "Noble Arms" = the four
            Infernoble Arms.  [sp] = &card word, [sp+4] = excluded cid (Ogier / Maugis: "except" / "other").  Keep iff
            cid != excluded AND (cid is an Infernoble Arms OR (race Warrior AND attribute FIRE)) -- the row words are now
            type-only (Monster | Spell), so this callback carries the whole filter."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("LDR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R4, R0, #0x12")
            b.insn("LSR", "R4, R4, #0x12")
            b.insn("LDR", "R1, [SP, #0xc]")
            b.insn("CMP", "R4, R1")
            b.insn("BEQ", "no")
            for c in ARMS_CIDS:
                b.ldr_const(1, c)
                b.insn("CMP", "R4, R1")
                b.insn("BEQ", "yes")
            b.insn("ADD", "R0, R4, #0")
            b.ldr_const(3, GET_RACE)
            b.insn("BLX", "R3")
            b.insn("CMP", f"R0, #{RACE_WARRIOR}")
            b.insn("BNE", "no")
            b.insn("ADD", "R0, R4, #0")
            b.ldr_const(3, GET_ATTR)
            b.insn("BLX", "R3")
            b.insn("CMP", f"R0, #{ATTR_FIRE}")
            b.insn("BNE", "no")
            b.label("yes")
            b.insn("MOV", "R0, #1")
            b.insn("POP", "{R4, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0")
            b.insn("POP", "{R4, PC}")
            return b


        ARSTUBS = {"MISS": ar_miss_stub, "NACB": ar_nacb_stub}


        def apply_arms_shared(rom, ov: bytearray) -> None:
            assert _bl_target(ov, MISS_SITE) in (cave3.CAVE3_IK_M_MISS, ARL["MISS"]), f"AR miss node -> {_bl_target(ov, MISS_SITE):#x}"
            ov[MISS_SITE - RAM_BASE:MISS_SITE - RAM_BASE + 4] = _bl(MISS_SITE, ARL["MISS"])
            print("AR miss-timing node -> Arms never-miss front (-> Maugis's)")


        def verify_arms_shared(rom, ov, check) -> None:
            check(O5.dc_skip(_bl_target(ov, MISS_SITE)) == ARL["MISS"], f"AR bl @{MISS_SITE:#x} -> Arms never-miss front")


        # =================================================================================================
        # Infernoble Arms 4: Psychic Sword 0x1F71 -> Infernoble Arms - Hauteclere (Equip Spell)
        #   Psychic Sword's "Psychic only" gate WAS there, missed by the scans: equip-legality switch @0x021D78EC (base 0x200D
        #   - 0x9C), retired (PSY_GATE; user: "no valid target offered").  The ATK-difference effect is still
        #   ASSUMED gone (HA2).
        #   E1 cls3 over 0x0E70: target 1 face-up monster you control -> Wonder Clover 0x2009's own code with desc[0] = 0x2009
        #      for the two calls: 0x021E8180 posts the player node {0x2009, kind 1, this card's ref} (others cannot attack,
        #      battle check @0x021A52AE) and 0x02208849 (default arm) attaches the kind-2 rider {0x2009} to the target (second
        #      attack: rider-key list @0x021A3EFA..).  Then destroy this card.
        #   E2 cls2 over 0x0E4B: Joyeuse's leave arm (AL chain); target 1 face-up monster on the field -> The Fabled Catsith's
        #      destroy 0x02204899 (+14 0x02234DA5); NEVER MISSES (user): front at the miss-timing tree pair 0x021EE12A
        #      (`subs r1,r2,#3 ; cmp r3,r1` -> 0x1F71 gets `cmp r3,r3`: Z set, blt not taken, beq -> never miss).
        #   One OPT 0x5F71.
        # =================================================================================================
        HA_KEY = 0x4000 | HAUTECLERE
        WONDER_CLOVER, WC_PLAYER_NODE, RIDER_RES, WC_TSTEP = 0x2009, 0x021E8181, 0x02208849, 0x02234D8D
        MISS2_SITE, MISS2_STOCK = 0x021EE12A, bytes.fromhex("d11e8b42")        # subs r1,r2,#3 ; cmp r3,r1
        # Psychic Sword's "Psychic only" equip gate: equip-legality switch 0x021D7348, `subs r3,#0x9c` (0x200D -> 0x1F71) ->
        # arm 0x021D7F2A (accept iff race bit 21).  #0x9C -> #0xA2 builds 0x1F6B, below this subtree's 0x1F6C floor = dead.
        # Execution-proven over rom_all_patches.ml2: 0x1F71 0 -> 1 on own monsters, 0x1F6D..0x1F70 unchanged.
        PSY_GATE, PSY_GATE_STOCK, PSY_GATE_DEAD = 0x021D78EC, 0x3B9C, 0x3BA2
        HA_CLS3_PHANTOM, HA_CLS2_PHANTOM = 0x0E70, 0x0E4B
        HAL = {n: getattr(O5, f"CAVE_IK_HA_{n}") for n in ("E1COND", "E1FILT", "E1RES", "E2COND", "E2FILT", "E2RES", "LEAVE",
                                                           "MISS")}
        HARESERVE = {"E1COND": 0x60, "E1FILT": 0x40, "E1RES": 0xA0, "E2COND": 0x40, "E2FILT": 0x40, "E2RES": 0x50,
                     "LEAVE": 0x30, "MISS": 0x20}
        HA_CLS3_REC = (HAUTECLERE, 0, HAL["E1RES"] | 1, HAL["E1FILT"] | 1, HAL["E1COND"] | 1, 0, WC_TSTEP)
        HA_CLS2_REC = (HAUTECLERE, 0, HAL["E2RES"] | 1, HAL["E2FILT"] | 1, HAL["E2COND"] | 1, TAG_YOU_CAN, CATSITH_TSTEP)
        LEAVE_FRONTS = LEAVE_FRONTS + (O5.CAVE_IK_HA_LEAVE,)


        def _ha_faceup_filter(own_only: bool) -> EffectBuilder:
            """+08 (desc, side, zone): a face-up monster (zone 0..4)""" + (" of desc[+2]'s side" if own_only else "") + "."
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            if own_only:
                b.insn("LDRB", "R0, [R4, #0x2]")
                b.insn("CMP", "R5, R0")
                b.insn("BNE", "no")
            b.insn("CMP", "R6, #0x4")
            b.insn("BGT", "no")
            b.call_addr(FACE_UP, R5, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(CARD_CID_AT, R5, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def ha_e1cond_stub() -> EffectBuilder:
            """cls3 +0C: face-up in a S/T zone and equipped, OPT 0x5F71 clear -> 1 (the +08 sweep needs a monster you control)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R6, [R4, #0x3]")
            b.insn("CMP", "R6, #0x5")
            b.insn("BLT", "no")
            b.insn("CMP", "R6, #0x9")
            b.insn("BGT", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(EQUIP_TARGET_OF, R0, R6, via=R3)
            b.ldr_const(1, 0xffff)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "no")
            _used(b, HA_KEY, "r4", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def ha_e1res_stub() -> EffectBuilder:
            """cls3 +04 (one pass): OPT check + stamp; desc[0] = 0x2009 -> Wonder Clover's player node 0x021E8180 + rider
            resolver 0x02208849 (default arm: kind-2 rider {0x2009} on the declared target); desc[0] restored; destroy this card (no VALID_AT: it runs E1FILT, which rejects the S/T zone)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            _used(b, HA_KEY, "r4", "zero")
            _post(b, HA_KEY)
            b.ldr_const(0, WONDER_CLOVER)
            b.insn("STRH", "R0, [R4, #0x0]")
            b.call_addr(WC_PLAYER_NODE, R4, 0, via=R3)
            b.call_addr(RIDER_RES, R4, R6, via=R3)
            b.ldr_const(0, HAUTECLERE)
            b.insn("STRH", "R0, [R4, #0x0]")
            b.insn("LDRH", "R0, [R4, #0xC]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R1, R0, #0x18")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R2, R0, #0x10")
            b.insn("LSR", "R2, R2, #0x18")
            b.insn("CMP", "R2, #0x5")
            b.insn("BLT", "zero")
            b.insn("CMP", "R2, #0x9")
            b.insn("BGT", "zero")
            b.call_addr(DESTROY_AT, R4, via=R3)
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def ha_e2cond_stub() -> EffectBuilder:
            """cls2 +0C: OPT 0x5F71 clear -> 1 (the +08 sweep needs a face-up monster on the field)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            _used(b, HA_KEY, "r4", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def ha_e2res_stub() -> EffectBuilder:
            """cls2 +04: phase 0x80 OPT check + stamp; then The Fabled Catsith's destroy 0x02204899 (declared target)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R6, R1, #0x0")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("CMP", "R0, #0x80")
            b.insn("BNE", "nat")
            _used(b, HA_KEY, "r4", "zero")
            _post(b, HA_KEY)
            b.label("nat")
            b.call_addr(CATSITH_RES, R4, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def ha_leave_stub() -> EffectBuilder:
            """BL @0x021C8216 ahead of Almace's front: 0x1F71 to the GY with reason bit 0x400000 -> Sword of Dark Rites'
            accept arm; else Almace's front, lr intact."""
            b = EffectBuilder()
            b.ldr_const(1, HAUTECLERE)
            b.insn("CMP", "R4, R1")
            b.insn("BNE", "next")
            b.insn("LDR", "R1, [SP, #0x144]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "next")
            b.insn("LDR", "R1, [SP, #0xC]")
            b.insn("LSL", "R1, R1, #0x9")
            b.insn("BPL", "next")
            b.ldr_const(1, SWORD_ACCEPT)
            b.insn("BX", "R1")
            b.label("next")
            b.ldr_const(1, ALL['LEAVE'] | 1)
            b.insn("BX", "R1")
            return b


        def ha_miss_stub() -> EffectBuilder:
            """BL over `subs r1,r2,#3 ; cmp r3,r1` @0x021EE12A in the miss-timing test's cid tree (r3 = cid, r2 = 0x2082):
            0x1F71 -> `cmp r3,r3` (Z set, N == V: the caller's blt falls through, beq -> never miss); else the pair."""
            b = EffectBuilder()
            b.ldr_const(1, HAUTECLERE)
            b.insn("CMP", "R3, R1")
            b.insn("BNE", "rep")
            b.insn("CMP", "R3, R3")
            b.insn("BX", "LR")
            b.label("rep")
            b.insn("SUB", "R1, R2, #0x3")
            b.insn("CMP", "R3, R1")
            b.insn("BX", "LR")
            return b


        HASTUBS = {"E1COND": ha_e1cond_stub, "E1FILT": lambda: _ha_faceup_filter(True), "E1RES": ha_e1res_stub,
                  "E2COND": ha_e2cond_stub, "E2FILT": lambda: _ha_faceup_filter(False), "E2RES": ha_e2res_stub,
                  "LEAVE": ha_leave_stub, "MISS": ha_miss_stub}


        def apply_hauteclere(rom, ov: bytearray) -> None:
            o = PSY_GATE - RAM_BASE
            assert struct.unpack_from("<H", ov, o)[0] in (PSY_GATE_STOCK, PSY_GATE_DEAD), "HA Psychic Sword equip gate moved"
            struct.pack_into("<H", ov, o, PSY_GATE_DEAD)
            insert_row(ov, CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, HA_CLS3_REC, HA_CLS3_PHANTOM, "HA E1 cls3")
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, HA_CLS2_REC, HA_CLS2_PHANTOM, "HA E2 cls2")
            assert _bl_target(ov, LEAVE_SITE) in (ALL["LEAVE"], HAL["LEAVE"]), f"HA leave site -> {_bl_target(ov, LEAVE_SITE):#x}"
            ov[LEAVE_SITE - RAM_BASE:LEAVE_SITE - RAM_BASE + 4] = _bl(LEAVE_SITE, HAL["LEAVE"])
            o = MISS2_SITE - RAM_BASE
            assert bytes(ov[o:o + 4]) in (MISS2_STOCK, _bl(MISS2_SITE, HAL["MISS"])), "HA miss-tree pair not stock"
            ov[o:o + 4] = _bl(MISS2_SITE, HAL["MISS"])
            print("HA cls3 + cls2, leave front, never-miss front @0x021EE12A")


        def verify_hauteclere(rom, ov, check) -> None:
            for label, base, count, stride, fmt, recs in (("cls3", CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, [HA_CLS3_REC]),
                                                          ("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, [HA_CLS2_REC])):
                rows = _rows(ov, base, count, stride, fmt)
                check([r for r in rows if r[0] == HAUTECLERE] == recs, f"HA {label}: exactly the 0x1f71 row")
                check([r[0] for r in rows] == sorted(r[0] for r in rows), f"HA {label}: sorted")
            check(O5.dc_skip(_bl_target(ov, LEAVE_SITE)) == HAL["LEAVE"], f"HA bl @{LEAVE_SITE:#x} -> leave front")   # a Phoenix Gearblade front may sit ahead (dc_next)
            check(_bl_target(ov, MISS2_SITE) == HAL["MISS"], f"HA bl @{MISS2_SITE:#x} -> never-miss front")
            check(struct.unpack_from("<H", ov, PSY_GATE - RAM_BASE)[0] == PSY_GATE_DEAD, "HA Psychic Sword equip gate retired")


        # =================================================================================================
        # Noble Arms Museum: Molten Destruction 0x1346 (Field Spell -> Field Spell, keep-cid)
        #   Molten's only per-cid code is its field-spell stat arm 0x021B28FA (field.arm_map; no cls record, no criteria row,
        #   base+-imm scan empty).  The ov5 AI mirror switches (0x022C971C / 0x02331E94 pivots) are left alone, as for the Seal.
        #   C1 arm -> `bl MU_STAT ; b 0x021B2B48`: own side ([sp] == r7), race Warrior ([r6+8] bit 15), FIRE ([r6+0xC] bit 4)
        #      -> r4 += 500 (ATK only).  The 6 B after the branch are dead.
        #   C2 + C3 ONE cls3 record over 0x14B8 (one record per class per cid).  They are never both legal: C3 needs C2's
        #      "applied" node, C2 needs its own OPT clear.  Mode -> desc[+0x18] in +10 (Horn's carrier), read by +14 and +04.
        #      C2: +10 posts OPT 0x5346 + pays 1200 LP (0x021CF924, Premature Burial's payment; +0C asks LP > 1200 like the
        #          generic cost 0x021E780C).  +04 posts "applied" 0x3346, then the native Deck-add machine's phases (message
        #          0x33 | picker | readback -> 0x021C72CC | 0x021D269C) over Almace's criteria row in NEW MODE 3 (Deck, the four
        #          Arms) -- criteria phantoms are exhausted, and Almace's row handler is FRONTED (MU_CRITF), so Almace's own
        #          bytes and modes 0..2 are untouched.
        #      C3: +10 posts OPT 0x7346 and, without a face-up Emperor Charles (0x021AC0C8), Horn's Warrior-only lock node
        #          0x5976 (Horn's front already reads it).  +14 = the generic target step (Wonder Clover's message); +08 = your
        #          S/T zone 5..9 holding a face-up Infernoble monster (KNIGHTS).  +04 = Dragunity Phalanx / Armory Arm's S/T ->
        #          monster zone commit 0x0226925C(side, &zone record, 1, 2 = position of choice, [sp] = 0x1346 << 16).
        # =================================================================================================
        MUSEUM = 0x1346
        KNIGHTS = tuple(STATS)                                  # "Noble Knight" == "Infernoble Knight" here (user)
        MU_C2KEY, MU_APPKEY, MU_C3KEY = 0x4000 | MUSEUM, 0x2000 | MUSEUM, 0x6000 | MUSEUM
        MOLTEN_ARM, FIELD_EPILOGUE = 0x021B28FA, 0x021B2B48
        MOLTEN_STOCK = bytes.fromhex("0c20315e1020084211d0ede7")   # movs r0,#0xc ; ldrsh ; movs r0,#0x10 ; tst ; beq ; b
        LP_PAY, PRESENCE, DECK_TO_HAND, DECK_DONE = 0x021CF925, 0x021AC0C9, 0x021C72CD, 0x021D269D
        MSG_ADD, PICK_ONE, LP_BASE, MU_LP = 0x33, 6, 0x0229AC94, 1200
        for _v in (LP_PAY, PRESENCE, DECK_TO_HAND, DECK_DONE):
            assert _v & 1, f"{_v:#x}: blx to an even literal switches to ARM state -> freeze"
        MU_CLS3_PHANTOM = 0x14B8
        MUL = {n: getattr(O5, f"CAVE_IK_MU_{n}") for n in ("STAT", "COND", "FILT", "COST", "SLOT5", "RES", "CRITF", "ARMCB",
                                                           "KNCB")}
        MURESERVE = {"STAT": 0x20, "COND": 0xc0, "FILT": 0x60, "COST": 0xa0, "SLOT5": 0x20, "RES": 0x150, "CRITF": 0x80, "ARMCB": 0x40, "KNCB": 0xa0}
        MU_CLS3_REC = (MUSEUM, 0, MUL["RES"] | 1, MUL["FILT"] | 1, MUL["COND"] | 1, MUL["COST"] | 1, MUL["SLOT5"] | 1)
        AL_CRIT_REC = (ALMACE, 0xFFFF, MUL["CRITF"] | 1, 0x00000000)    # Almace's row, handler fronted (mode 3 = Museum)


        def _mu_arm(base: int = MOLTEN_ARM) -> bytes:
            off = (FIELD_EPILOGUE - (base + 4) - 4) >> 1
            assert -1024 <= off < 1024
            blob = _bl(base, MUL["STAT"]) + struct.pack("<H", 0xE000 | (off & 0x7FF))
            effect_verify.assert_thumb1_only(blob, base)
            return blob


        def mu_stat_stub() -> EffectBuilder:
            """BL from Molten's field arm (frame intact: [sp] = field-spell side, r7 = monster side, r6 = monster record):
            own FIRE Warrior -> r4 += 500.  r0/r1 scratch; returns to the arm's `b 0x021B2B48`."""
            b = EffectBuilder()
            b.insn("LDR", "R0, [SP, #0x0]")
            b.insn("CMP", "R7, R0")
            b.insn("BNE", "out")
            b.insn("LDR", "R1, [R6, #0x8]")
            b.insn("LSL", "R1, R1, #0x10")
            b.insn("BPL", "out")
            b.insn("LDRH", "R1, [R6, #0xC]")
            b.insn("LSL", "R1, R1, #0x1B")
            b.insn("BPL", "out")
            b.insn("ADD", "R4, #0xFA")
            b.insn("ADD", "R4, #0xFA")
            b.label("out")
            b.insn("BX", "LR")
            return b


        def _mu_query(b: EffectBuilder, key: int, side: str = "r7") -> None:
            b.insn("ADD", f"R0, {str(side).upper()}, #0x0")
            b.turnlog_query(R0, key, 1, via=R5)


        def mu_cond_stub() -> EffectBuilder:
            """cls3 +0C: in the Field Zone.  C2 OPT clear: LP > 1200 and >= 1 Arms in the Deck -> 2.  Else C2 applied this
            turn, C3 OPT clear, can SS + a free monster zone -> 1 (the +08 sweep then needs a Noble Knight in your S/T)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R7, [R4, #0x2]")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xA")
            b.insn("BNE", "no")
            _mu_query(b, MU_C2KEY)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "c3")
            b.ldr_const(1, 0xB3C)
            b.insn("MUL", "R1, R7")
            b.ldr_const(0, LP_BASE)
            b.insn("LDR", "R0, [R0, R1]")
            b.ldr_const(1, MU_LP)
            b.insn("CMP", "R0, R1")
            b.insn("BLE", "no")
            b.insn("MOV", "R0, #0x4")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.call_addr(CRIT_WORKER, R7, ALMACE, MUL['ARMCB'] | 1, 0)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x2")
            b.insn("B", "ret")
            b.label("c3")
            _mu_query(b, MU_APPKEY)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            _mu_query(b, MU_C3KEY)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "no")
            b.call_addr(CAN_SS, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(FREE_MZ, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def mu_filt_stub() -> EffectBuilder:
            """cls3 +08 (desc, side, zone): desc's own side, zone 5..9, face-up, cid in KNIGHTS (via MU_KNCB on the zone word)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("CMP", "R5, R0")
            b.insn("BNE", "no")
            b.insn("CMP", "R6, #0x5")
            b.insn("BLT", "no")
            b.insn("CMP", "R6, #0x9")
            b.insn("BGT", "no")
            b.call_addr(FACE_UP, R5, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.ldr_const(0, 0xB3C)
            b.insn("MUL", "R0, R5")
            b.ldr_const(1, LP_BASE + 0x34)
            b.insn("ADD", "R0, R0, R1")
            b.insn("MOV", "R1, #0x14")
            b.insn("MUL", "R1, R6")
            b.insn("ADD", "R0, R0, R1")
            b.insn("PUSH", "{R0}")
            b.call_addr(MUL['KNCB'], via=R3)
            b.insn("ADD", "SP, #0x4")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def mu_cost_stub() -> EffectBuilder:
            """cls3 +10 (one call -> 1; replay -> 1 untouched): C2 OPT clear -> mode 1, post it, pay 1200 LP.  Else mode 2,
            post C3's OPT, and without a face-up Emperor Charles post Horn's Warrior-only lock node."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R7, [R4, #0x2]")
            b.call_addr(SHORTCIRCUIT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "one")
            _mu_query(b, MU_C2KEY)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "c3")
            b.insn("MOV", "R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x18]")
            _post(b, MU_C2KEY)
            b.call_addr(LP_PAY, R7, MU_LP, via=R3)
            b.insn("B", "one")
            b.label("c3")
            b.insn("MOV", "R0, #0x2")
            b.insn("STRH", "R0, [R4, #0x18]")
            _post(b, MU_C3KEY)
            b.insn("ADD", "R0, R7, #0x0")
            b.ldr_const(1, CHARLES)
            b.insn("MOV", "R2, #0x0")
            b.insn("SUB", "R2, #0x1")
            b.call_addr(PRESENCE, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "one")
            _post(b, HO_LOCKKEY)
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def mu_slot5_stub() -> EffectBuilder:
            """cls3 +14: mode 2 (C3) -> the generic target step (Wonder Clover's message); mode 1 (C2) -> 1, no target."""
            b = EffectBuilder()
            b.insn("LDRH", "R3, [R0, #0x18]")
            b.insn("CMP", "R3, #0x2")
            b.insn("BNE", "one")
            b.ldr_const(3, WC_TSTEP)
            b.insn("BX", "R3")
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            return b


        def mu_res_stub() -> EffectBuilder:
            """cls3 +04 on [0x0229AAFC+0x70], mode desc[+0x18]:
               C2 (1): 0x80 post "applied", >= 1 Arms in the Deck -> message 0x33 -> 0x7E | 0x7E picker (Almace row, mode 3)
                       -> 0x7D | 0x7D readback -> 0x021C72CC add to hand -> 0x64 | 0x64 0x021D269C -> 0 (the native add's tail).
               C3 (2): 0x80 declared target still valid, on your side in zone 5..9, can SS + a free monster zone -> the S/T
                       commit 0x0226925C(side, &zone record, 1, 2, [sp] = 0x1346 << 16) -> 0x78 | 0x78 -> 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0x8")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R7, [R4, #0x2]")
            b.ldr_const(0, 0x0229aafc)
            b.insn("LDR", "R6, [R0, #0x70]")
            b.insn("LDRH", "R0, [R4, #0x18]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "c3")
            b.insn("CMP", "R6, #0x80")
            b.insn("BEQ", "p80")
            b.insn("CMP", "R6, #0x7E")
            b.insn("BEQ", "p7e")
            b.insn("CMP", "R6, #0x7D")
            b.insn("BEQ", "p7d")
            b.insn("CMP", "R6, #0x64")
            b.insn("BNE", "zero")
            b.call_addr(DECK_DONE, R7, via=R3)
            b.insn("B", "zero")
            b.label("p80")
            _post(b, MU_APPKEY)
            b.insn("MOV", "R0, #0x4")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.call_addr(CRIT_WORKER, R7, ALMACE, MUL['ARMCB'] | 1, 0)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.call_addr(AS_MESSAGE, R7, MSG_ADD, via=R3)
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("p7e")
            b.insn("ADD", "R0, R7, #0x0")
            b.insn("MOV", f"R1, #0x{PICK_ONE:X}")
            b.ldr_const(2, ALMACE)
            b.insn("MOV", "R3, #0x3")
            b.insn("LSL", "R3, R3, #0x10")
            b.call_addr(AS_PICKER, via=R6)
            b.insn("MOV", "R0, #0x7D")
            b.insn("B", "ret")
            b.label("p7d")
            b.call_addr(AS_READBACK, via=R3)
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(DECK_TO_HAND, R7, via=R3)
            b.insn("MOV", "R0, #0x64")
            b.insn("B", "ret")
            b.label("c3")
            b.insn("CMP", "R6, #0x80")
            b.insn("BNE", "zero")
            b.call_addr(TGT_VALID, R4, 0, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.call_addr(TGT_REF, R4, 0, via=R3)
            b.call_addr(LOCATE, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "zero")
            b.insn("LSL", "R1, R0, #0x18")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("CMP", "R1, R7")
            b.insn("BNE", "zero")
            b.insn("LSL", "R6, R0, #0x10")
            b.insn("LSR", "R6, R6, #0x18")
            b.insn("CMP", "R6, #0x5")
            b.insn("BLT", "zero")
            b.insn("CMP", "R6, #0x9")
            b.insn("BGT", "zero")
            b.call_addr(CAN_SS, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.call_addr(FREE_MZ, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.ldr_const(0, MUSEUM << 16)
            b.insn("STR", "R0, [SP, #0x0]")
            b.ldr_const(0, 0xB3C)
            b.insn("MUL", "R0, R7")
            b.ldr_const(1, LP_BASE + 0x34)
            b.insn("ADD", "R1, R0, R1")
            b.insn("MOV", "R0, #0x14")
            b.insn("MUL", "R0, R6")
            b.insn("ADD", "R1, R1, R0")
            b.call_addr(SS_COMMIT, R7, R1, 1, 2, via=R6)
            b.insn("MOV", "R0, #0x78")
            b.insn("B", "ret")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0x8")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def mu_critf_stub() -> EffectBuilder:
            """FRONT on Almace's criteria row handler (row r0, side r1, param r2), mode = param >> 16; modes 0..2 -> Almace's
            handler, untouched.  3 = Deck Spells (worker flags 2, word 4) kept by MU_ARMCB (Museum C2); 4 = hand Spells
            (hand builder, word 4) kept by MU_ARMCB (Continuing Epic: the Arms to reveal); 5 = hand + Deck monsters (word 2)
            kept by MU_KNCB (Continuing Epic: the Knight to summon / equip).  Returns the number recorded."""
            b = EffectBuilder()
            b.insn("LSR", "R3, R2, #0x10")
            b.insn("CMP", "R3, #0x3")
            b.insn("BGE", "mine")
            b.ldr_const(3, ALL['CRIT'] | 1)
            b.insn("BX", "R3")
            b.label("mine")
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("SUB", "SP, #0x10")
            b.insn("ADD", "R4, R1, #0x0")
            b.insn("ADD", "R5, R3, #0x0")
            b.insn("MOV", "R6, #0x0")
            b.insn("STR", "R6, [SP, #0xC]")
            b.insn("CMP", "R5, #0x3")
            b.insn("BNE", "hand")
            b.ldr_const(2, MUL['ARMCB'] | 1)
            b.insn("MOV", "R0, #0x4")
            b.insn("B", "deck")
            b.label("hand")
            b.insn("MOV", "R0, #0x4")
            b.ldr_const(2, MUL['ARMCB'] | 1)
            b.insn("CMP", "R5, #0x4")
            b.insn("BEQ", "hb")
            b.insn("MOV", "R0, #0x2")
            b.ldr_const(2, MUL['KNCB'] | 1)
            b.label("hb")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R4, #0x0")
            b.ldr_const(1, ALMACE)
            b.insn("ADD", "R3, SP, #0xC")
            b.call_addr(AS_HAND_BUILDER, via=R6)
            b.insn("ADD", "R6, R0, #0x0")
            b.insn("CMP", "R5, #0x4")
            b.insn("BEQ", "out")
            b.insn("MOV", "R0, #0x2")
            b.ldr_const(2, MUL['KNCB'] | 1)
            b.label("deck")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x2")
            b.insn("STR", "R0, [SP, #0x4]")
            b.call_addr(CRIT_WORKER, R4, ALMACE, R2, 0)
            b.insn("ADD", "R6, R6, R0")
            b.label("out")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("ADD", "SP, #0x10")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b

        MUSTUBS = {"STAT": mu_stat_stub, "COND": mu_cond_stub, "FILT": mu_filt_stub, "COST": mu_cost_stub, "SLOT5": mu_slot5_stub,
                  "RES": mu_res_stub, "CRITF": mu_critf_stub, "ARMCB": lambda: _cid_in_cb(ARMS_CIDS),
                  "KNCB": lambda: _cid_in_cb(KNIGHTS)}


        def apply_museum(rom, ov: bytearray) -> None:
            o = MOLTEN_ARM - RAM_BASE
            cur = bytes(ov[o:o + len(MOLTEN_STOCK)])
            assert cur == MOLTEN_STOCK or cur[:6] == _mu_arm(), f"MU Molten arm moved: {cur.hex()}"
            ov[o:o + 6] = _mu_arm()
            insert_row(ov, CLS3_BASE, CLS3_COUNT, 24, CLS_FMT, MU_CLS3_REC, MU_CLS3_PHANTOM, "MU C2/C3 cls3")
            print("MU Molten's field arm -> MU_STAT, cls3 (C2/C3), Almace row fronted (mode 3)")


        def verify_museum(rom, ov, check) -> None:
            check(bytes(ov[MOLTEN_ARM - RAM_BASE:MOLTEN_ARM - RAM_BASE + 6]) == _mu_arm(), "MU Molten's field arm -> MU_STAT")
            rows = _rows(ov, CLS3_BASE, CLS3_COUNT, 24, CLS_FMT)
            check([r for r in rows if r[0] == MUSEUM] == [MU_CLS3_REC], "MU cls3: exactly the 0x1346 row")
            check([r[0] for r in rows] == sorted(r[0] for r in rows), "MU cls3: sorted")
            crit = _rows(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT)
            check([r for r in crit if r[0] == ALMACE] == [AL_CRIT_REC], "MU Almace's criteria row -> MU_CRITF")
            check(not [r for r in crit if r[0] == MUSEUM], "MU no criteria row of its own")


        # =================================================================================================
        # The Continuing Epic of Charles: Big Burn 0x16DB (Normal Trap -> Normal Trap, keep-cid)
        #   Big Burn's only per-cid code is its own cls0 record (base+-imm scan empty), re-pointed in place (Horn's shape).
        #   Lists come from Almace's fronted criteria row (MU_CRITF): mode 4 = "Noble Arms" in your hand, mode 5 =
        #   Infernoble monsters (KNIGHTS, user) in your hand + Deck.
        #   E1 cls0: +0C NEXT's once-per-turn gate 0x021F6DD9 (menu) + both lists + can SS + a free monster zone -> 2;
        #      +10 posts {0x16DB, kind 1} (Horn's cost); +04 machine: pick the Arms to reveal (hand, ref -> desc[+0x1C]) |
        #      pick the Knight (hand or Deck) -> SS commit 0x0226925C(side, &word, 1, 2, [sp] = 0x16DB << 16) (source zone from
        #      the card's ref, 0x021A220C), its ref -> desc[+0x1E] | the Arms still in hand + the Knight on your field + a free
        #      S/T zone -> Yes/No 0xFA -> zone UI -> move hand 0xB -> equip link kind 0xA (Charles C2 stage A) ; No / not
        #      possible -> hand -> GY via 0x021C6D90 (kind 2 = neither a cost nor an effect DISCARD; the text says "send").
        #   E2 cls2 over 0x0E63 + a gy_vrow_hook row: +10 Stygian's banish-self 0x021E5709, +14 the generic target step,
        #      +08 a face-up Emperor Charles you control; +04 = Charles C2 stage B: pick a Knight (hand or Deck) -> zone UI ->
        #      move (hand 0xB / Deck 0xD) -> equip link kind 0xA to the target (0xC = Allure's kind, never reaches the stat front).  +500 = Captain Oliver's stat front, which
        #      already gives 0x17EF +500 per MONSTER equip.  OPT 0x56DB stamped at resolution.
        # =================================================================================================
        EPIC = 0x16DB
        EP_E2KEY = 0x4000 | EPIC
        EP_CLS0_STOCK = (EPIC, 0, 0x0221A059, 0, 0x021F7709, 0, 0)
        EP_CLS2_PHANTOM = 0x0E63
        HAND_TO_GY = 0x021C6D91                                  # kind 2 hand -> GY (dispatch.three_hand_to_gy_movers)
        MSG_REVEAL = MSG_EQUIP_WHICH
        assert HAND_TO_GY & 1
        EPL = {n: getattr(O5, f"CAVE_IK_EP_{n}") for n in ("COND", "COST", "RES", "E2COND", "E2FILT", "E2RES")}
        EPRESERVE = {"COND": 0x70, "COST": 0x40, "RES": 0x220, "E2COND": 0x70, "E2FILT": 0x40, "E2RES": 0x170}
        EP_CLS0_REC = (EPIC, 0, EPL["RES"] | 1, 0, EPL["COND"] | 1, EPL["COST"] | 1, 0)
        EP_CLS2_REC = (EPIC, 0, EPL["E2RES"] | 1, EPL["E2FILT"] | 1, EPL["E2COND"] | 1, STYGIAN_COST, WC_TSTEP)


        def _ep_ref(b: EffectBuilder, dst: str) -> None:
            """r0 = &card word -> *dst* = that card's ref (the engine's own formula, 0x0226929x)."""
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", f"{str(dst).upper()}, R0, R1")


        def _ep_jump(b: EffectBuilder, code: int, label: str) -> None:
            b.insn("CMP", f"R0, #0x{code:X}")
            b.insn("BNE", f"n{label}")
            b.insn("B", f"{label}")
            b.label(f"n{label}")


        def _ep_pick(b: EffectBuilder, mode: int) -> None:
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", f"R1, #0x{PICK_ONE:X}")
            b.ldr_const(2, ALMACE)
            b.insn("MOV", f"R3, #0x{mode:X}")
            b.insn("LSL", "R3, R3, #0x10")
            b.call_addr(AS_PICKER, via=R7)


        def ep_cond_stub() -> EffectBuilder:
            """cls0 +0C: menu check (desc[+7] == 0) -> NEXT's once-per-turn gate; Arms in hand (mode 4), a Knight in hand /
            Deck (mode 5), can SS, a free monster zone -> 2."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x7]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "leg")
            b.call_addr(ONCE_CHECK, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.label("leg")
            _al_count(b, 0x40000, "no")
            _al_count(b, 0x50000, "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(CAN_SS, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_MZ, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def ep_cost_stub() -> EffectBuilder:
            """cls0 +10 (one call -> 1): post the once-per-turn node {0x16DB, kind 1} unless replayed / copy-exempt."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(SHORTCIRCUIT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "one")
            b.call_addr(COPY_EXEMPT, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "one")
            _post(b, EPIC)
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def ep_res_stub() -> EffectBuilder:
            """cls0 +04 on [0x0229AAFC+0x70]:
               0x80 chain push; both lists, can SS, a free monster zone -> message (reveal) -> 0x7F
               0x7F picker mode 4 | 0x7E readback -> Arms ref desc[+0x1C]; message 0x11D | 0x7D picker mode 5
               0x7C readback -> Knight ref desc[+0x1E]; SS commit -> 0x7B
               0x7B Arms still in hand + Knight on your field (zone 0..4) + free S/T -> Yes/No 0xFA -> 0x7A; else 0x77
               0x7A Yes -> zone UI -> 0x79 | No -> 0x77 | 0x79 move hand 0xB -> picked S/T zone | 0x78 link kind 0xA -> end
               0x77 Arms still in hand -> 0x021C6D90 (hand -> GY) | end: chain pop -> 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x70]")
            for c in (0x80, 0x7F, 0x7E, 0x7D, 0x7C, 0x7B, 0x7A, 0x79, 0x78, 0x77):
                _ep_jump(b, c, f"p{c:x}")
            b.insn("B", "end")
            b.label("p80")
            b.call_addr(CHAIN_PUSH, via=R3)
            _al_count(b, 0x40000, "e80")
            _al_count(b, 0x50000, "e80")
            b.call_addr(CAN_SS, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "e80")
            b.call_addr(FREE_MZ, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "e80")
            b.call_addr(AS_MESSAGE, R5, MSG_REVEAL, via=R3)
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("e80")
            b.insn("B", "end")
            b.label("p7f")
            _ep_pick(b, 4)
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("p7e")
            b.call_addr(AS_READBACK, via=R3)
            _ep_ref(b, "r2")
            b.insn("STRH", "R2, [R4, #0x1C]")
            b.call_addr(AS_MESSAGE, R5, MSG_SS_ONE, via=R3)
            b.insn("MOV", "R0, #0x7D")
            b.insn("B", "ret")
            b.label("p7d")
            _ep_pick(b, 5)
            b.insn("MOV", "R0, #0x7C")
            b.insn("B", "ret")
            b.label("p7c")
            b.call_addr(AS_READBACK, via=R3)
            b.insn("ADD", "R7, R0, #0x0")
            _ep_ref(b, "r2")
            b.insn("STRH", "R2, [R4, #0x1E]")
            b.ldr_const(0, EPIC << 16)
            b.insn("STR", "R0, [SP, #0x0]")
            b.call_addr(SS_COMMIT, R5, R7, 1, 2, via=R7)
            b.insn("MOV", "R0, #0x7B")
            b.insn("B", "ret")
            b.label("p7b")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x1C]")
            b.call_addr(HAND_INDEX, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "g77")
            b.call_addr(FREE_ST, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "g77")
            b.insn("LDRH", "R0, [R4, #0x1E]")
            b.call_addr(LOCATE, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "g77")
            b.insn("LSL", "R1, R0, #0x18")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("CMP", "R1, R5")
            b.insn("BNE", "g77")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("CMP", "R0, #0x4")
            b.insn("BGT", "g77")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("MOV", "R1, #0xFA")
            b.insn("LDRH", "R2, [R4, #0xC]")
            b.call_addr(AS_YESNO, via=R3)
            b.insn("MOV", "R0, #0x7A")
            b.insn("B", "ret")
            b.label("g77")
            b.insn("B", "p77")
            b.label("p7a")
            b.ldr_const(0, AS_UI)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "g77")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.insn("LDRH", "R2, [R4, #0x1C]")
            b.call_addr(ZONE_UI, via=R3)
            b.insn("MOV", "R0, #0x79")
            b.insn("B", "ret")
            b.label("p79")
            b.ldr_const(0, ZONE_PICK)
            b.insn("LDRH", "R0, [R0, #0x24]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("MOV", "R1, #0xB")
            b.insn("LDRH", "R2, [R4, #0x1C]")
            b.call_addr(MOVER, R0, R1, R2, R5, via=R7)
            b.insn("MOV", "R0, #0x78")
            b.insn("B", "ret")
            b.label("p78")
            b.insn("LDRH", "R0, [R4, #0x1E]")
            b.call_addr(LOCATE, via=R3)
            b.insn("LSL", "R2, R0, #0x10")
            b.insn("LSR", "R2, R2, #0x10")
            b.ldr_const(0, ZONE_PICK)
            b.insn("LDRH", "R1, [R0, #0x24]")
            b.insn("LSL", "R1, R1, #0x18")
            b.insn("LSR", "R1, R1, #0x10")
            b.insn("ORR", "R1, R5")
            b.insn("MOV", "R3, #0xA")
            b.call_addr(EQUIP_LINK, R5, via=R7)
            b.insn("B", "end")
            b.label("p77")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x1C]")
            b.call_addr(HAND_INDEX, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "end")
            b.insn("ADD", "R1, R0, #0x0")
            b.call_addr(HAND_TO_GY, R5, via=R3)
            b.label("end")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        def ep_e2cond_stub() -> EffectBuilder:
            """cls2 +0C (desc, arg): in the GY (0x0E), OPT 0x56DB clear, a face-up Emperor Charles of yours, a free S/T zone,
            >= 1 Knight in hand / Deck (mode 5) -> 1 (the +08 sweep then finds Charles)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", "R0, #0xE")
            b.insn("BNE", "no")
            _used(b, EP_E2KEY, "r4", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.ldr_const(1, CHARLES)
            b.insn("MOV", "R2, #0x0")
            b.insn("SUB", "R2, #0x1")
            b.call_addr(PRESENCE, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_ST, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "no")
            _al_count(b, 0x50000, "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b


        def ep_e2filt_stub() -> EffectBuilder:
            """cls2 +08 (desc, side, zone): desc's own side, zone 0..4, face-up, cid == Emperor Charles."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("CMP", "R5, R0")
            b.insn("BNE", "no")
            b.insn("CMP", "R6, #0x4")
            b.insn("BGT", "no")
            b.call_addr(FACE_UP, R5, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.call_addr(CARD_CID_AT, R5, R6, via=R3)
            b.ldr_const(1, CHARLES)
            b.insn("CMP", "R0, R1")
            b.insn("BNE", "no")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b


        def ep_e2res_stub() -> EffectBuilder:
            """cls2 +04 on [0x0229AAFC+0x70]:
               0x80 chain push; OPT check + stamp; target valid -> its loc desc[+0x18]; free S/T + a Knight (mode 5)
                    -> message 0x5E -> 0x7F
               0x7F picker mode 5 | 0x7E readback -> ref desc[+0x1C]; zone UI | 0x7D move (hand 0xB / Deck 0xD)
               0x7C equip link kind 0xA to the target (0xC skips the stat loop's equip path) -> end | end: chain pop -> 0."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("SUB", "SP, #0xC")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R5, [R4, #0x2]")
            b.ldr_const(6, 0x0229aafc)
            b.insn("LDR", "R0, [R6, #0x70]")
            for c in (0x80, 0x7F, 0x7E, 0x7D, 0x7C):
                _ep_jump(b, c, f"p{c:x}")
            b.insn("B", "end")
            b.label("p80")
            b.call_addr(CHAIN_PUSH, via=R3)
            _used(b, EP_E2KEY, "r4", "end")
            _post(b, EP_E2KEY)
            b.call_addr(TGT_VALID, R4, 0, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "end")
            b.call_addr(TGT_REF, R4, 0, via=R3)
            b.call_addr(LOCATE, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "end")
            b.insn("STRH", "R0, [R4, #0x18]")
            b.call_addr(FREE_ST, R5, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "end")
            _al_count(b, 0x50000, "end")
            b.call_addr(AS_MESSAGE, R5, MSG_EQUIP, via=R3)
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("p7f")
            _ep_pick(b, 5)
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("p7e")
            b.call_addr(AS_READBACK, via=R3)
            _ep_ref(b, "r2")
            b.insn("STRH", "R2, [R4, #0x1C]")
            b.call_addr(ZONE_UI, R5, R5, via=R3)
            b.insn("MOV", "R0, #0x7D")
            b.insn("B", "ret")
            b.label("p7d")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x1C]")
            b.call_addr(HAND_INDEX, via=R3)
            b.insn("MOV", "R1, #0xB")
            b.insn("CMP", "R0, #0x0")
            b.insn("BGE", "mv")
            b.insn("MOV", "R1, #0xD")
            b.label("mv")
            b.ldr_const(0, ZONE_PICK)
            b.insn("LDRH", "R0, [R0, #0x24]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R2, [R4, #0x1C]")
            b.call_addr(MOVER, R0, R1, R2, R5, via=R7)
            b.insn("MOV", "R0, #0x7C")
            b.insn("B", "ret")
            b.label("p7c")
            b.ldr_const(0, ZONE_PICK)
            b.insn("LDRH", "R1, [R0, #0x24]")
            b.insn("LSL", "R1, R1, #0x18")
            b.insn("LSR", "R1, R1, #0x10")
            b.insn("ORR", "R1, R5")
            b.insn("LDRH", "R2, [R4, #0x18]")
            b.insn("MOV", "R3, #0xA")
            b.call_addr(EQUIP_LINK, R5, via=R7)
            b.label("end")
            b.call_addr(CHAIN_POP_C, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.label("ret")
            b.insn("ADD", "SP, #0xC")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b


        EPSTUBS = {"COND": ep_cond_stub, "COST": ep_cost_stub, "RES": ep_res_stub, "E2COND": ep_e2cond_stub,
                  "E2FILT": ep_e2filt_stub, "E2RES": ep_e2res_stub}


        def apply_epic(rom, ov: bytearray) -> None:
            rows = _rows(ov, CLS0_BASE, CLS0_COUNT, 24, CLS_FMT)
            hits = [i for i, r in enumerate(rows) if r[0] == EPIC]
            assert len(hits) == 1 and rows[hits[0]] in (EP_CLS0_STOCK, EP_CLS0_REC), f"EP cls0 rows {hits}"
            struct.pack_into(CLS_FMT, ov, CLS0_BASE + hits[0] * 24 - RAM_BASE, *EP_CLS0_REC)
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, EP_CLS2_REC, EP_CLS2_PHANTOM, "EP E2 cls2 (GY)")
            print("EP cls0 re-pointed (E1), cls2 (E2, gy_vrow_hook row)")


        def verify_epic(rom, ov, check) -> None:
            rows = _rows(ov, CLS0_BASE, CLS0_COUNT, 24, CLS_FMT)
            check([r for r in rows if r[0] == EPIC] == [EP_CLS0_REC], "EP cls0: exactly one 0x16DB row (re-pointed)")
            rows = _rows(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT)
            check([r for r in rows if r[0] == EPIC] == [EP_CLS2_REC], "EP cls2: exactly one 0x16DB row")
            check([r[0] for r in rows] == sorted(r[0] for r in rows), "EP cls2: sorted")
            check(any(c == EPIC for c, _ in gyv.ARMS), "EP gy_vrow_hook row registered")



        TSTUBS = {"RES": t_res_stub, "FILT": t_filt_stub, "EQX": t_eqx_stub, "LEGAL": t_legal_stub, "COND": t_cond_stub,
                 "COST": t_cost_stub, "SLOT5": t_slot5_stub, "HANDRES": t_handres_stub, "GYSS": t_gyss_stub,
                 "EQRES": t_eqres_stub, "H4": t_h4_stub, "TUNER": t_tuner_stub}


        STUBS = {"EQFILT": eqfilt_stub, "PROT": prot_stub, "C3F2": lambda: _opt_gate_stub(OGIER, VYLON_F2),
                "C3COST": c3cost_stub, "C2H": c2h_stub, "C2CB": c2cb_stub,
                "C2COND": lambda: _opt_gate_stub(C2KEY, ARMAGEDDON_COND), "C2SLOT4": c2slot4_stub}


        def ov5_blobs() -> list[tuple[str, int, int, bytes]]:
            out = []
            for srcs, lay, res, pre in ((STUBS, L, RESERVE, ""), (MSTUBS, ML, MRESERVE, "M_"), (OSTUBS, OL, ORESERVE, "O_"),
                                        (TSTUBS, TL, TRESERVE, "T_"), (RSTUBS, RL, RRESERVE, "R_"),
                                        (RCSTUBS, RCL, RCRESERVE, "RC_"), (ROSTUBS, ROL, RORESERVE, "RO_"),
                                        (ASSTUBS, ASL, ASRESERVE, "AS_"), (BRSTUBS, BRL, BRRESERVE, "BR_"),
                                        (CRSTUBS, CRL, CRRESERVE, "CR_"), (COSTUBS, COL, CORESERVE, "CO_"),
                                        (CHSTUBS, CHL, CHRESERVE, "CH_"), (ANSTUBS, ANL, ANRESERVE, "AN_"),
                                        (HOSTUBS, HOL, HORESERVE, "HO_"), (JOSTUBS, JOL, JORESERVE, "JO_"),
                                        (DUSTUBS, DUL, DURESERVE, "DU_"), (ALSTUBS, ALL, ALRESERVE, "AL_"),
                                        (ARSTUBS, ARL, ARRESERVE, "AR_"), (HASTUBS, HAL, HARESERVE, "HA_"),
                                        (MUSTUBS, MUL, MURESERVE, "MU_"), (EPSTUBS, EPL, EPRESERVE, "EP_")):
                for n, f in srcs.items():
                    blob = f().assemble(lay[n], pad="nop")
                    effect_verify.assert_thumb1_only(blob, lay[n])
                    assert len(blob) <= res[n], f"{pre}{n}: {len(blob)} B > {res[n]:#x}"
                    out.append((pre + n, lay[n], res[n], blob))
            return out


        def ov3_blobs(prev_miss: int) -> list[tuple[str, int, int, bytes, int, bytes]]:
            """(name, slot, size, blob, site, the site's expected pre-hook bytes or None)."""
            gy = m_gynode_stub().assemble(cave3.CAVE3_IK_M_GYNODE, pad="nop")
            miss = m_miss_stub(prev_miss).assemble(cave3.CAVE3_IK_M_MISS, pad="nop")
            for a, b, n in ((cave3.CAVE3_IK_M_GYNODE, gy, 0x10), (cave3.CAVE3_IK_M_MISS, miss, 0x1A)):
                effect_verify.assert_thumb1_only(b, a)
                assert len(b) <= n, f"ov3 {a:#x}: {len(b)} B > {n:#x}"
            return [("M_GYNODE", cave3.CAVE3_IK_M_GYNODE, 0x10, gy, GYNODE_SITE, GYNODE_STOCK),
                    ("M_MISS", cave3.CAVE3_IK_M_MISS, 0x1A, miss, MISS_SITE, None)]


        def _bl_target(ov, site: int) -> int:
            h1, h2 = struct.unpack_from("<HH", ov, site - RAM_BASE)
            off = ((h1 & 0x7FF) << 12) | ((h2 & 0x7FF) << 1)
            return site + 4 + (off - (1 << 23) if off & (1 << 22) else off)


        def _miss_prev(ov) -> int:
            """What the miss node BLs when our front is NOT installed (in the chain: Eva's front)."""
            t = O5.dc_skip(_bl_target(ov, MISS_SITE))      # disguise_copycat's never-miss front may sit ahead
            if t == O5.CAVE_IK_AR_MISS:                    # the Arms never-miss front sits ahead of Maugis's
                t = cave3.CAVE3_IK_M_MISS
            if t != cave3.CAVE3_IK_M_MISS:
                return t
            lit = bytes(ov[t - RAM_BASE:t - RAM_BASE + 0x1A])
            return next(struct.unpack_from("<I", lit, i)[0] & ~1 for i in range(len(lit) - 4, -1, -2)
                        if struct.unpack_from("<I", lit, i)[0] & 1 and 0x02000000 < struct.unpack_from("<I", lit, i)[0] < 0x02400000)


        def shared_blobs() -> list[tuple[str, int, int, bytes]]:
            """The two shared stubs re-emitted with Ogier's LOCAL arm (until shipped)."""
            return [("c79", O5.CAVE_C79TRIG, c79.RESERVE, c79.stub(O5.CAVE_C79TRIG, C79_ARMS)),
                    ("timing", O5.CAVE_TIMINGHOOK, tch.RESERVE, tch.stub(O5.CAVE_TIMINGHOOK, TCH_ARMS))]


        def _put5(rom, addr: int, reserve: int, blob: bytes) -> None:
            assert len(blob) <= reserve, f"ov5 {addr:#x}: {len(blob)} B > {reserve:#x}"
            if O5.read_cave(rom, addr, reserve) == blob + bytes(reserve - len(blob)):
                return
            ov5 = O5._load_ov5_decompressed(rom)
            data = bytearray(ov5.data)
            o = addr - O5.OV5_RAM_BASE
            data[o:o + reserve] = blob + bytes(reserve - len(blob))
            O5._save_ov5(rom, ov5, bytes(data))


        # =================================================================================================
        # apply / verify
        # =================================================================================================
        def _rows(ov, base, count, stride, fmt):
            return [struct.unpack_from(fmt, ov, base + i * stride - RAM_BASE) for i in range(count)]



        def _exits(base: int, blob: bytes) -> set[int]:
            """Branch targets a stub can leave by: its BL targets and the odd code literals in its own pool."""
            from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
            out = set()
            for i in Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(blob, base):
                if i.mnemonic == "bl":
                    out.add(int(i.op_str.lstrip("#"), 0))
                elif i.mnemonic == "ldr" and "pc" in i.op_str:
                    lit = (i.address + 4 & ~3) + int(i.op_str.split("#")[-1].rstrip("]"), 0)
                    if base <= lit <= base + len(blob) - 4:
                        v = struct.unpack_from("<I", blob, lit - base)[0]
                        if v & 1 and 0x02000000 < v < 0x02400000:
                            out.add(v & ~1)
            return out



        def install(rom, view):
            ov = view.buf
            # ONE ov5 decompress + ONE recompress for every stub (was 2 decompress + 1 recompress PER stub, ~15 min at
            # 9 cards).  Safe as a single buffer: nothing else touches ov5 before this loop ends.
            ov5 = O5._load_ov5_decompressed(rom)
            data = bytearray(ov5.data)
            for n, addr, reserve, blob in ov5_blobs() + shared_blobs():
                effect_verify.assert_thumb1_only(blob, addr)
                assert len(blob) <= reserve, f"ov5 {addr:#x}: {len(blob)} B > {reserve:#x}"
                o = addr - O5.OV5_RAM_BASE
                data[o:o + reserve] = blob + bytes(reserve - len(blob))
                print(f"ov5 {n:8s} @{addr:#010x}  {len(blob)} B / {reserve:#x}")
            if bytes(data) != bytes(ov5.data):
                O5._save_ov5(rom, ov5, bytes(data))
            c79.apply(ov)
            tch.apply(ov)
            gyv.install(rom, ov)
            for site, stock, dst in SITES:
                o = site - RAM_BASE
                cur = bytes(ov[o:o + 4])
                assert cur in (stock, _bl(site, dst)), f"site {site:#x} = {cur.hex()}, expected stock {stock.hex()}"
                ov[o:o + 4] = _bl(site, dst)
                print(f"bl @{site:#010x} -> {dst:#010x}")
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, CLS2_REC, CLS2_PHANTOM, "C3 cls2")
            insert_row(ov, IGN_BASE, IGN_COUNT, 12, IGN_FMT, IGN_REC, IGN_PHANTOM, "C3 ignition row")
            insert_row(ov, CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, CLS1_REC, CLS1_PHANTOM, "C2 cls1")
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, CRIT_REC, CRIT_PHANTOM, "C2 criteria row")
            # --- Maugis -----------------------------------------------------------------------------------
            o = BATTLE_SITE - RAM_BASE
            assert bytes(ov[o:o + 4]) in (BATTLE_STOCK, _bl(BATTLE_SITE, ML["BATTLE"])), "M C1 Mist Body site not stock"
            ov[o:o + 4] = _bl(BATTLE_SITE, ML["BATTLE"])
            print(f"M  bl @{BATTLE_SITE:#010x} -> {ML['BATTLE']:#010x} (Mist Body query front)")
            for n, slot, _sz, blob, site, stock in ov3_blobs(_miss_prev(ov)):
                cave3.put(ov, slot, blob, n)
                o = site - RAM_BASE
                cur = bytes(ov[o:o + 4])
                assert stock is None or cur in (stock, _bl(site, slot)), f"M {n} site {site:#x} = {cur.hex()}"
                ov[o:o + 4] = _bl(site, slot)
                print(f"M  ov3 {n} @{slot:#010x} ({len(blob)} B); bl @{site:#010x}")
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, M_CLS2_REC, M_CLS2_PHANTOM, "M cls2 (C2+C3)")
            insert_row(ov, IGN_BASE, IGN_COUNT, 12, IGN_FMT, M_IGN_REC, M_IGN_PHANTOM, "M C3 ignition row")
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, M_CRIT_REC, M_CRIT_PHANTOM, "M C2 criteria row")
            insert_row(ov, MASK_BASE, MASK_COUNT, 4, "<Hh", M_MASK_REC, M_MASK_PHANTOM, "M C2 leave-mask row")
            insert_row(ov, DRAW_BASE, DRAW_COUNT, 4, "<Hh", M_DRAW_REC, M_DRAW_PHANTOM, "M C2 draw-count row")
            # --- Oliver -----------------------------------------------------------------------------------
            insert_row(ov, CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, O_CLS2_REC, O_CLS2_PHANTOM, "O cls2 (C2 hand + C3 GY)")
            insert_row(ov, IGN_BASE, IGN_COUNT, 12, IGN_FMT, O_IGN_REC, O_IGN_PHANTOM, "O C3 ignition row")
            insert_row(ov, CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, O_CRIT_REC, O_CRIT_PHANTOM, "O C2 hand-cost criteria row")
            apply_listb(rom)
            apply_turpin(rom, ov)
            apply_renaud(rom, ov)
            apply_ricc(rom, ov)
            apply_roland(rom, ov)
            apply_astolfo(rom, ov)
            apply_brada(rom, ov)
            apply_caprol(rom, ov)
            apply_capoli(rom, ov)
            apply_charles(rom, ov)
            apply_angelica(rom, ov)
            apply_horn(rom, ov)
            apply_joyeuse(rom, ov)
            apply_durendal(rom, ov)
            apply_almace(rom, ov)
            apply_arms_shared(rom, ov)
            apply_hauteclere(rom, ov)
            apply_museum(rom, ov)
            apply_epic(rom, ov)

        def post(out):
            apply_caprol_identity(out)
            apply_capoli_identity(out)
            _synchro_identity(out, CHARLES, CO_REF_SYNCHRO, "CH")
            _synchro_identity(out, ANGELICA, CO_REF_SYNCHRO, "AN")
            for cid_, st in STATS.items():
                name, desc = card_text.CARD_TEXT[cid_]["e"]
                apply_stats_and_text(out, cid=cid_, name=name.encode(), desc=desc.encode(),
                                     langs="".join(card_text.LANGS), write_text=True, **st)
            for cid_ in TEXT_ONLY[:-1]:                 # Spell / Trap donors: card_prop unchanged, text only; the last one is spec.cid
                card_text.apply_to_rom(out, cid_)

        def check_fn(c, rom, view):
            def check(cond, msg):
                c.ok(bool(cond), msg)

            ov = view.buf
            out = c.out
            ov5data = bytes(O5._load_ov5_decompressed(rom).data)          # one decompress for every stub check
            live_c79 = c79.where()[0]           # later cards' arms move the shared c79 stub to a bigger slot
            for n, addr, _r, blob in ov5_blobs() + shared_blobs():
                if n == "c79":
                    addr, blob = live_c79, c79.stub(live_c79)
                o = addr - O5.OV5_RAM_BASE
                check(ov5data[o:o + len(blob)] == blob, f"ov5 {n} @{addr:#x} byte-exact")
            blobs = {addr: blob for _n, addr, _r, blob in ov5_blobs()}
            for front, nxt in O5.ik_next().items():           # the owners' chain map must match the fronts' real exits
                check(nxt in _exits(front, blobs[front]), f"IK_NEXT {front:#x} -> {nxt:#x} is an exit of that front")
            for site, _stock, dst in SITES:
                check(code_reaches(rom, site, dst), f"bl @{site:#x} reaches {dst:#x}")
            check(bytes(ov[c79.SITE - RAM_BASE:c79.SITE - RAM_BASE + 4]) == _bl(c79.SITE, c79.where()[0]), "c79 site hooked")
            check(bytes(ov[tch.TIMING_SITE - RAM_BASE:tch.TIMING_SITE - RAM_BASE + 4]) == _bl(tch.TIMING_SITE, O5.CAVE_TIMINGHOOK),
                  "timing-class site hooked")
            gyv.verify(rom, ov, check)
            for label, base, count, stride, fmt, rec, ph in (
                    ("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, CLS2_REC, CLS2_PHANTOM),
                    ("ignition", IGN_BASE, IGN_COUNT, 12, IGN_FMT, IGN_REC, IGN_PHANTOM),
                    ("cls1", CLS1_BASE, CLS1_COUNT, 24, CLS_FMT, CLS1_REC, CLS1_PHANTOM),
                    ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, CRIT_REC, CRIT_PHANTOM)):
                rows = _rows(ov, base, count, stride, fmt)
                keys = [r[0] for r in rows]
                check([r for r in rows if r[0] == OGIER] == [rec], f"{label}: exactly one {OGIER:#x} row = {rec}")
                check(keys == sorted(keys), f"{label}: sorted")
            # --- Maugis ---
            check(bytes(ov[BATTLE_SITE - RAM_BASE:BATTLE_SITE - RAM_BASE + 4]) == _bl(BATTLE_SITE, ML["BATTLE"]),
                  f"M bl @{BATTLE_SITE:#x} -> Mist Body front")
            for n, slot, _sz, blob, site, _st in ov3_blobs(_miss_prev(ov)):
                check(bytes(ov[slot - RAM_BASE:slot - RAM_BASE + len(blob)]) == blob, f"M ov3 {n} @{slot:#x} byte-exact")
                ok = ((_bl(site, slot), _bl(site, O5.CAVE_IK_AR_MISS), _bl(site, O5.CAVE_DC_MISS)) if site == MISS_SITE
                      else (_bl(site, slot),))
                got = bytes(ov[site - RAM_BASE:site - RAM_BASE + 4])
                if site == MISS_SITE:                    # a Disguise / Phoenix Gearblade never-miss front may sit ahead (dc_next)
                    got = _bl(site, O5.dc_skip(_bl_target(ov, site)))
                check(got in ok, f"M bl @{site:#x} -> {n} (or the Arms front ahead)")
            for label, base, count, stride, fmt, rec in (
                    ("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, M_CLS2_REC),
                    ("ignition", IGN_BASE, IGN_COUNT, 12, IGN_FMT, M_IGN_REC),
                    ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, M_CRIT_REC),
                    ("leave-mask", MASK_BASE, MASK_COUNT, 4, "<Hh", M_MASK_REC),
                    ("draw-count", DRAW_BASE, DRAW_COUNT, 4, "<Hh", M_DRAW_REC)):
                rows = _rows(ov, base, count, stride, fmt)
                keys = [r[0] for r in rows]
                check([r for r in rows if r[0] == MAUGIS] == [rec], f"M {label}: exactly one {MAUGIS:#x} row = {rec}")
                check(keys == sorted(keys), f"M {label}: sorted")
            check(_snoww._switch_leaf(bytes(ov), MAUGIS) == GY_ACCEPT_LEAF, "M sent-to-GY chain: 0x139A -> accept")
            check(_snoww._switch_leaf(bytes(ov), 0x13E3) == GY_ACCEPT_LEAF, "M sent-to-GY chain: Archfiend of Gilfer still accepted")
            check(_snoww._switch_leaf(bytes(ov), 0x139B) == 0x021D19C0, "M sent-to-GY chain: neighbour 0x139B still rejected")
            # --- Oliver ---
            for label, base, count, stride, fmt, rec in (
                    ("cls2", CLS2_BASE, CLS2_COUNT, 24, CLS_FMT, O_CLS2_REC),
                    ("ignition", IGN_BASE, IGN_COUNT, 12, IGN_FMT, O_IGN_REC),
                    ("criteria", CRIT_BASE, CRIT_COUNT, 12, CRIT_FMT, O_CRIT_REC)):
                rows = _rows(ov, base, count, stride, fmt)
                keys = [r[0] for r in rows]
                check([r for r in rows if r[0] == OLIVER] == [rec], f"O {label}: exactly one {OLIVER:#x} row = {rec}")
                check(keys == sorted(keys), f"O {label}: sorted")
            lst = _listb(rom)[3]
            check(OLIVER in lst and LISTB_PHANTOM not in lst and all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)),
                  f"O hand-effect LIST B: 0x1E04 in, phantom 0x1A86 out, strictly sorted")
            verify_turpin(rom, ov, check)
            verify_renaud(rom, ov, check)
            verify_ricc(rom, ov, check)
            verify_roland(rom, ov, check)
            verify_astolfo(rom, ov, check)
            verify_brada(rom, ov, check)
            verify_caprol(rom, ov, check)
            verify_capoli(rom, ov, check)
            verify_charles(rom, ov, check)
            verify_angelica(rom, ov, check)
            verify_horn(rom, ov, check)
            verify_joyeuse(rom, ov, check)
            verify_durendal(rom, ov, check)
            verify_almace(rom, ov, check)
            verify_arms_shared(rom, ov, check)
            verify_hauteclere(rom, ov, check)
            verify_museum(rom, ov, check)
            verify_epic(rom, ov, check)
            for cid in list(STATS) + list(TEXT_ONLY):
                ok, msg = card_text.check_rom_text(out, cid, "".join(card_text.LANGS))
                check(ok, f"text {cid:#x}: {msg}")


        return Compiled(installs=(install,), posts=(post,), checks=(check_fn,))


infernoble_effects = infernoble_knights_and_arms_family_equip_link_hand_or_graveyard_summons_and_arms_lock_on_vanilla_and_spell_donors

SPEC = card(0x16DB, infernoble_effects())

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_infernoble.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
