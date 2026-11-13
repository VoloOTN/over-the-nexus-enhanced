"""Wattuna (LIGHT / Thunder / Tuner / Level 4 / 800 / 700) on Spirit of the Harp 0x1050.

See notes/wattuna-findings.md for the printed text (a custom card; in neither the NDS nor the 3DS build): can attack
directly; hand self-Special Summon after your monster inflicts battle damage; Synchro Summon a "Watt" using it after a
direct-attack battle damage, each once per turn.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class direct_attack_hand_special_summon_after_battle_damage_and_synchro_summon_watt_from_extra_deck:
    """Wattuna (Spirit of the Harp 0x1050, a Tuner): 'This card can attack directly; if your monster inflicts battle damage to your opponent:
    you can Special Summon this card from your hand (once per turn); when this card inflicts battle damage by a direct attack: you can
    Synchro Summon 1 "Watt" Synchro Monster using it and hand/field Watts (once per turn).' U1 direct-attack list; U3 cls2 record (hand
    self-SS main + Watapon's condition) behind once-per-turn cond/cost stubs, ARM9 hand-responder list, the battle-damage hand poster
    retargeted from the field poster, the Deck->hand self-SS chain extended; U4 LIST A trigger + cls1 Synchro-summon resolver + a Watt
    criteria row whose ov5 handler offers the Extra-Deck Synchros; the hand-material gate stub (only while the forced slot is set), the
    level_sum hand loop rewritten (hand, then field); "Watt" set code displacing Wattkey 0x2481. Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.asm.effect_shim import _bl
        from otn_enhanced.cards.maiden_eyes_of_blue import CRIT_BASE, CRIT_STRIDE, CRIT_FMT
        from otn_enhanced.effects.common import (ARM9_BASE, CLS1_BASE, CLS1_COUNT, CLS1_FMT, CLS1_STRIDE, crit_count, insert_row,
                                                 list_insert, ov3_off as _off, thumb_bl, u16_keys)
        DONOR_CID = cid
        DA_LIST, DA_COUNT = 0x0226D730, 25
        DA_DROP = 0x1129                   # phantom; no card_prop, unclaimed in every pool

        # --- PART C: U3 ---------------------------------------------------------
        CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, CLS2_FMT = 0x02275C04, 0x2B9, 0x18, "<IIIIII"
        CLS2_DROP = 0x0EC3                 # phantom; one row; unclaimed
        HANDSS_MAIN = 0x02206ABD           # "Special Summon this card from the hand"
        HANDSS_COND = 0x021F0A39           # the Watapon / Rose Fairy / Battle Fader condition
        OPTIONAL_TAG = 0x021E51E5          # slot4 "You can" -- 168 cls1 + the whole hand-SS family
        # U2 for U3: "You can only use each... once per turn" = the cid-keyed turn log
        # (dispatch.turnlog_once_per_turn_pair; locks every copy).  Eva 0x160A's shape: QUERY in +0C,
        # STAMP in the +14 cost (runs only after a Yes, before the chain resolves), so +10 keeps the
        # native "You can" tag and NO timing_class_hook arm is needed (that shared stub is 248/256 B).
        # Kind 1 = U3; U4 will take kind 2 ("each of the following effects").  ov5 -> duel-only.
        U3_KIND = 1
        TURNLOG_QUERY, TURNLOG_POST = 0x021A14E9, 0x021D2585
        COST_SHORTCIRCUIT = 0x021D2BC9     # (desc) != 0 -> cost already settled, return 1
        U3COND, U3COST, U3_RESERVE = ov5_cave.CAVE_WU_U3COND, ov5_cave.CAVE_WU_U3COST, 0x30
        CLS2_NEW = (DONOR_CID, HANDSS_MAIN, 0x00000000, U3COND | 1, OPTIONAL_TAG, U3COST | 1)


        def opt_cond_stub(base: int, kind: int, native: int) -> bytes:
            """+0C (desc, r1): turn log `kind` set -> 0, else tail the record's native condition."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_query(R0, DONOR_CID, kind, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "used")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("ADD", "R1, R5, #0x0")
            b.ldr_const(6, native)
            b.insn("BLX", "R6")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("used")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        def opt_cost_stub(base: int, kind: int) -> bytes:
            """+14 slot5 (desc): settled -> 1; else stamp turn log `kind` and return 1 (done)."""
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(COST_SHORTCIRCUIT, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "done")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, kind, via=R4)
            b.label("done")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")


        def _u3_blobs():
            return (("U2 U3 cond", U3COND, opt_cond_stub(U3COND, U3_KIND, HANDSS_COND)),
                    ("U2 U3 cost", U3COST, opt_cost_stub(U3COST, U3_KIND)),
                    ("U2 U4 cond", U4COND, opt_cond_stub(U4COND, U4_KIND, ALWAYS_ACTIVATABLE)),
                    ("U2 U4 cost", U4COST, opt_cost_stub(U4COST, U4_KIND)),
                    ("E3 U4 offer handler", OFFER, offer_handler(OFFER)))

        HANDRESP_LIST, HANDRESP_COUNT = 0x0209BD20, 0x26      # the third ARM9 hand list (see docstring)
        HANDRESP_THUNK = 0x02023574                            # ldr/ldr/movs r2,#0x26/bx r3
        HANDRESP_COUNT_IMM = 0x02023578                        # the `movs r2,#0x26` halfword
        HANDRESP_LIT = 0x0202357C                              # the sole list literal
        HANDRESP_DROP = 0x0E68                                 # phantom at index 0; unclaimed

        # --- PART D: U4 trigger -------------------------------------------------
        LISTA, LISTA_COUNT = 0x0226EE7C, 19
        LISTA_DROP = 0x1DB6                # phantom; its cls1 row is already spent, so the
                                           # list entry is its last surviving occurrence
        LISTB = 0x0226EEA4                 # the ungated trigger -- asserted UNTOUCHED

        # --- PART E: U4 resolver ------------------------------------------------
        SYNCHRO_RESOLVER = 0x02249EC1      # shared; Formula Synchron + Urgent Tuning
        ZONE_PRED = 0x021E32D5             # Fane/Wattcobra's masked zone predicate (+08)
        ALWAYS_ACTIVATABLE = 0x0224A115    # `movs r0,#2 ; bx lr`
        CLS1_DROP = 0x1147                 # phantom; one row; unclaimed
        # U2 for U4: separate turn-log kind 2 ("each of the following effects").  +14 = slot5, run by the
        # activation machine after the Yes (desc[+8] done-flag); Kuribandit ships a cls1 +14 in-game.
        U4_KIND = 2
        U4COND, U4COST = ov5_cave.CAVE_WU_U4COND, ov5_cave.CAVE_WU_U4COST
        CLS1_NEW = (DONOR_CID, SYNCHRO_RESOLVER, ZONE_PRED, U4COND | 1,
                    OPTIONAL_TAG, U4COST | 1)

        # Blackwing - Aurora the Northern Lights 0x2385's OWN criteria handler, used
        # VERBATIM AND UNMODIFIED.  It is cid-blind: it reads the set code from the row's
        # `b` field (`movs r0,#2 ; ldrsh r0,[r2,r0]` -> [sp+8]), sets mode `movs r0,#4`
        # = is_synchro, and calls the Extra-Deck enumerator 0x0223BE40 with the stock
        # set-code filter 0x0223C825.  So `b = 0x0058` IS the entire Watt restriction and
        # this patch injects no code at all.
        #   ⚠️ DO NOT "TIGHTEN" THE MODE BYTE TO 0x24.  Build 1 cloned this handler into
        #   the ov5 cave with `movs r0,#4` -> `movs r0,#0x24` to add can_synchro
        #   0x02249540 on top of is_synchro.  can_synchro only walks the 10 FIELD slots
        #   (synchro.procedure_picks_and_sends_hand_materials), and Wattuna's materials
        #   may come from the HAND, so the dry run answered "cannot summon" for every
        #   candidate, the probe returned 0, phase 0x80 never advanced to the picker and
        #   the effect fizzled with the prompt still opening.  That was the whole of
        #   in-game failure 1 (user); root-caused offline by
        #   scratch/wattuna_u4_probe.py.  The looseness is Formula Synchron's own, and is
        #   in-game confirmed via steam_synchron.
        AURORA_HANDLER = 0x022430A0
        AURORA_LEN = 0x24
        AURORA_STOCK = bytes.fromhex(
            "0eb5021c0220105e02ab02909068009004200190081c1188014af8f7c1fe0ebd25c82302")
        ED_ENUMERATOR = 0x0223BE40
        SETCODE_FILTER = 0x0223C825        # stock ov3, reached via Aurora's own pool word

        WATT_SETCODE = 0x0058
        CRIT_DROP = 0x0EB9                 # phantom; one row; unclaimed
        CRIT_NEW = (DONOR_CID, WATT_SETCODE, ov5_cave.CAVE_WU_OFFER | 1, 0x0802, 0x0000)   # E3: was AURORA_HANDLER|1

        # --- PART E2: U4's hand material, scoped to U4 ---------------------------
        # The old PART E retargeted the gate's dead literal 0x02249534 (0x0E66) -> 0x1050.  That was
        # (a) ALWAYS ON -- any Synchro with Wattuna first could take a hand material (build-4 defect),
        # and (b) the literal now belongs to mara (user: "Take the literal").  So the gate
        # 0x022494EC (leaf, bx lr) gets its LAST literal test replaced by a tail jump:
        #     0x02249516  ldr r0,[0x0224953C] ; bx r0       (pool 0x2353 -> GATE_STUB|1; bx keeps LR)
        # and GATE_STUB (r1 = first-pick cid) returns 1 for Malefic Parallel Gear 0x2353 (as stock), or
        # for 0x1050 only while the forced-material slot 0x0229AC7C is nonzero -- the shared Synchro
        # resolver 0x02249EC0 stores desc[+0xC] there @0x0224A094 before polling the procedure, and the
        # procedure's init zeroes it @0x022634E0, so a plain Synchro Summon sees 0 (measured 2 in .ml5).
        # MUST be ov3 (the gate runs for every Synchro material check, puzzles included): it lives in
        # phantom 0x1433's dead leaf 0x021BB288 (64 B: entered only via `cmp r4,=0x1433 ; bne` @0x021BB286,
        # no inbound branch/BL/pointer, no card_prop), whose arm is sealed bne -> b.  The validator's
        # hand branch still demands count == 1 (one hand material: the user-approved U4 deviation).
        GATE_HOOK = 0x02249516
        GATE_HOOK_STOCK = bytes.fromhex("09488142")         # ldr r0,[pc,#0x24] ; cmp r1,r0
        GATE_HOOK_NEW = struct.pack("<2H", 0x4809, 0x4700)  # ldr r0,[0x0224953C] ; bx r0
        GATE_POOL, GATE_POOL_STOCK = 0x0224953C, 0x2353
        FORCED_SLOT = 0x0229AC7C
        GATE_STUB, GATE_STUB_SIZE, GATE_PHANTOM = 0x021BB288, 64, 0x1433
        GATE_SEAL, GATE_SEAL_STOCK, GATE_SEAL_NEW = 0x021BB286, 0xD11F, 0xE01F   # bne/b 0x021BB2C8


        # --- PART E3: the U4 Extra-Deck offer lists only MAKEABLE Watt Synchros ----------
        # Build 9 in-game: Aurora's handler (mode 4 = is_synchro) offered every Watt Synchro, incl. an
        # unmakeable Watthydra.  Mode 0x24 adds can_synchro, which the enumerator calls as
        # can_synchro(side, cid, 0, 1) @0x0223BF76 -- forced = 0, so the E2 stub refused the hand and
        # the count was 0.  Offline over the user's .ml3 (scratch/wattuna_u4_offer_probe.py): with the hand
        # granted to a Wattuna first pick, mode 0x24 gives count 1 = Wattchimera, as the user expects.  So:
        # OFFER = Aurora's handler with mode 0x24 that raises OFFER_PROBE around the enumerator call, and the
        # E2 stub also grants while OFFER_PROBE != 0.  (Build 1's "can_synchro is field-only" was an emulator
        # abort on the ARM divide 0x020989A4, never a measurement.)
        # Deviation: during the probe Wattuna is not FORCED into the materials, so a Watt Synchro makeable
        # from other field cards alone could still be listed.  OFFER_PROBE lives in ov5: in a puzzle the
        # gate reads an ov41 word there, which can only ever matter for a Wattuna first pick.
        OFFER, OFFER_PROBE = ov5_cave.CAVE_WU_OFFER, ov5_cave.CAVE_WU_PROBE
        OFFER_RESERVE = 0x40


        def offer_handler(base: int = OFFER) -> bytes:
            """Criteria handler (row r0, side r1): Aurora 0x022430A0 with mode 0x24, OFFER_PROBE raised."""
            b = EffectBuilder()
            b.insn("PUSH", "{R1, R2, R3, R4, R5, LR}")
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDRH", "R0, [R2, #0x2]")
            b.insn("STR", "R0, [SP, #0x8]")
            b.insn("LDR", "R0, [R2, #0x8]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", "R0, #0x24")
            b.insn("STR", "R0, [SP, #0x4]")
            b.ldr_const(4, OFFER_PROBE)
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [R4, #0x0]")
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("LDRH", "R1, [R2, #0x0]")
            b.ldr_const(2, SETCODE_FILTER)
            b.insn("ADD", "R3, SP, #0x8")
            b.call_addr(ED_ENUMERATOR, via=R5)
            b.insn("MOV", "R1, #0x0")
            b.insn("STR", "R1, [R4, #0x0]")
            b.insn("POP", "{R1, R2, R3, R4, R5, PC}")
            return b.assemble(base, pad="nop")


        def gate_stub(base: int = GATE_STUB) -> bytes:
            """Tail of gate 0x022494EC (r1 = first-pick cid, LR = the gate's caller)."""
            b = EffectBuilder()
            b.ldr_const(0, GATE_POOL_STOCK)
            b.insn("CMP", "R1, R0")
            b.insn("BEQ", "one")
            b.insn("MOV", "R0, #0x83")
            b.insn("LSL", "R0, R0, #0x5")
            b.insn("SUB", "R0, #0x10")
            b.insn("CMP", "R1, R0")
            b.insn("BNE", "zero")
            b.ldr_const(0, FORCED_SLOT)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "wmode")
            b.ldr_const(0, OFFER_PROBE)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "zero")
            b.label("wmode")
            b.insn("CMP", "R6, #0xB")
            b.insn("BLT", "zero")
            b.label("one")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            b.label("zero")
            b.insn("MOV", "R0, #0x0")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")

        # --- PART E4: U4 materials from the hand AND/OR the face-up field ---------------------
        # User report (rom_wattkyuki.ml2): empty hand, Wattuna + Wattcobra on the field, direct hit -> no Synchro
        # offered although Wattkyuki (4 + 4 = 8) is makeable.  Cause: native hand-material mode (gate 0x022494EC,
        # KB synchro.native_hand_material_mode) is ALL-OR-NOTHING -- when true the validator 0x02249AFC accepts only
        # hand cells and level_sum 0x0224966C's "is another pick available?" scan walks only the hand, so with a
        # Wattuna first pick a field non-Tuner could never count.  Measured (scratch/wattuna_mixed_gate_probe.py):
        # U4 offer count 0 -> fixed only by BOTH halves below:
        #   (1) gate stub `wmode`: hand mode per CELL (r6 >= 0xB; validator r6 = kind, level_sum r6 = a pointer);
        #   (2) level_sum's gate-true hand loop 0x0224992C..0x02249999 rewritten IN PLACE (pool 0x02249944..7F
        #       untouched): r6 (0x0229ABFC) is kept, the cell r7 / hand count go to the frame's dead slots
        #       [sp+0x14] / [sp+0x18] (the epilogue reads only +0x20 / +0x24), and a miss restores r7 and FALLS
        #       INTO the native field scan 0x0224999A instead of giving up ("hand, then field").
        # Natives in hand mode (Eccentric Boy, Parallel Gear, Mara's literal) keep gate-true for every cell, so the
        # validator rejects every field cell and the added scan finds nothing: same answer.  ov3 only (puzzle-safe).
        # Board results (offer): user board 0 -> 1, + junk hand card 0 -> 1, Lv4 Thunder in hand 1 -> 1, hand-only 1 -> 1.
        LS_A, LS_B = 0x0224992C, 0x02249980
        LS_VALIDATOR, LS_FOUND, LS_FIELD_SCAN, LS_LOOP_COND = 0x02249AFC, 0x02249920, 0x0224999A, 0x02249990
        LS_POOL_B3C, LS_POOL_PLAYER = 0x02249978, 0x0224997C
        LS_A_STOCK = bytes.fromhex("f06e0121071c0f403a1c0a400f49104851430024461826e0")
        LS_B_STOCK = bytes.fromhex("381c0b21221c00f0b9f8002800d0c7e7641cf0688442f3d321e0")


        def _hb(at: int, tgt: int) -> int:
            return 0xE000 | (((tgt - (at + 4)) >> 1) & 0x7FF)


        def _hbc(at: int, tgt: int, cond: int) -> int:
            off = (tgt - (at + 4)) >> 1
            assert -128 <= off <= 127, hex(at)
            return 0xD000 | (cond << 8) | (off & 0xFF)


        def level_sum_loop() -> tuple[bytes, bytes]:
            a = [0x6800 | (0x6C // 4) << 6 | 6 << 3 | 0,                  # ldr  r0,[r6,#0x6c]  (r6 = 0x0229ABFC)
                 0x9000 | 7 << 8 | 0x14 // 4,                             # str  r7,[sp,#0x14]  save the cell
                 0x0000 | 31 << 6 | 0 << 3 | 7,                           # lsls r7,r0,#31
                 0x0800 | 31 << 6 | 7 << 3 | 7,                           # lsrs r7,r7,#31      r7 = side
                 0x4900 | (LS_POOL_B3C - ((LS_A + 8 + 4) & ~3)) // 4,     # ldr  r1,=0xB3C      (native pool)
                 0x4800 | (LS_POOL_PLAYER - ((LS_A + 10 + 4) & ~3)) // 4, # ldr  r0,=0x0229AC94 (native pool)
                 0x4340 | 7 << 3 | 1,                                     # muls r1,r7
                 0x1800 | 1 << 6 | 0 << 3 | 0,                            # adds r0,r0,r1       player
                 0x6800 | (0xC // 4) << 6 | 0 << 3 | 0,                   # ldr  r0,[r0,#0xc]   hand count
                 0x9000 | 0 << 8 | 0x18 // 4,                             # str  r0,[sp,#0x18]
                 0x2400]                                                  # movs r4,#0
            a.append(_hb(LS_A + 2 * len(a), LS_LOOP_COND))                # b    loop condition
            off = LS_VALIDATOR - (LS_B + 6 + 4)
            b = [0x1C38, 0x210B, 0x1C22,                                  # adds r0,r7 ; movs r1,#0xb ; adds r2,r4
                 0xF000 | ((off >> 12) & 0x7FF), 0xF800 | ((off >> 1) & 0x7FF),   # bl validator(side, 0xB, i)
                 0x2800]                                                  # cmp  r0,#0
            b.append(_hbc(LS_B + 2 * len(b), LS_FOUND, 1))                # bne  found (r5 = 1)
            b += [0x3401, 0x9800 | 0x18 // 4, 0x4284]                     # adds r4,#1 ; ldr r0,[sp,#0x18] ; cmp r4,r0
            b.append(_hbc(LS_B + 2 * len(b), LS_B, 3))                    # blo  loop
            b += [0x9F00 | 0x14 // 4, 0x46C0]                             # ldr r7,[sp,#0x14] ; nop -> field scan
            blob_a, blob_b = struct.pack(f"<{len(a)}H", *a), struct.pack(f"<{len(b)}H", *b)
            assert len(blob_a) == len(LS_A_STOCK) and LS_B + len(blob_b) == LS_FIELD_SCAN
            assert LS_B + 2 * b.index(0x9800 | 0x18 // 4) == LS_LOOP_COND
            return blob_a, blob_b


        # --- PART F: "Watt" set-code membership -- NOT optional, see the docstring ----
        WATT_LIST, WATT_LIST_COUNT = 0x0209CBEA, 0x16      # sorted u16 cids, 22 entries
        WATT_THUNK = 0x02023EF4                            # has_set_code[0x58]; ptr table 0x0209D0D8[0x58]
        WATT_LIST_LIT = 0x02023EFC                         # its list pool word
        WATT_COUNT_IMM = 0x02023EF8                        # `movs r2,#0x16`
        WATT_BSEARCH_LIT = 0x02023F00                      # = 0x02022E15, asserted unchanged
        # The list is BOXED IN: Dragunity 0x4A (0x0209CBC0 x21) ends exactly at 0x0209CBEA and
        # Karakuri 0x5D (0x0209CC16 x22) begins exactly where this one ends, so it cannot grow
        # in place -- setcode.dragunity_table_is_full_and_boxed_in, re-measured.
        # The user chose a COUNT-NEUTRAL DISPLACEMENT over relocating the list,
        # nominating Wattkey / Wattcannon / Wattcine / Wattcastle as expendable.  All four are
        # Watt SPELL/TRAPs whose own archetype membership nothing reads: every "Watt" consumer
        # in this ROM looks for Watt MONSTERS (Wattcobra's filter explicitly ANDs in the
        # card_intid monster bit), and none of the four refers to itself.
        WATT_DROP = 0x2481                                 # Wattkey (Normal Spell) -- user-approved

        # --- PART G: U3 -- join the Deck->hand mover's "Special Summon me" cid chain ----
        # U3 as reframed by the user is Watapon's trigger: added from the Deck
        # to the hand by a card effect (Wattcobra) -> Special Summon itself.  cls2 + list
        # 0x0209BD20 (PART C) were necessary but NOT sufficient (build-4 in-game failure):
        # the Deck->hand mover 0x021C72CC posts event 0x4B (`bl 0x021D3168` @0x021C740E) only
        # for cids in a HARDCODED chain @0x021C73BE = {Watapon 0x17CC, R-Genex Oracle 0x20D3,
        # Rose Fairy 0x21B0 (= 0x20D3+0xDD, never stored), Breeze 0x224B}.  The ordered
        # compare tree is rewritten in place as a linear list, built from stock pool words.
        #
        # BUILD 6: the chain is skipped while [0x0229C294+0x78] bit 0 is set, and that bit
        # means "a battle is in progress" (set @0x021BC176 at attack start, cleared with the
        # attacker's bit 25 @0x021BC1CE).  Wattcobra adds Wattuna in the Damage Step, so build 5
        # never reached the chain (GDB probe #2: mover entered from Cobra's resolver, flag 0xB).
        # So the region now starts at the flag test and checks 0x1050 FIRST: Wattuna posts even
        # mid-battle; every other cid keeps the stock flag skip.
        # USER-ACCEPTED DEVIATION: after Wattuna's post the mover falls through to
        # 0x021C7412, so for a Wattuna added during battle the Puppet King (0x021D36C0, 0x1A43)
        # and 0x20D2 (0x021D3438) posters also run, which stock skips in battle.
        HANDCHAIN = 0x021C73AE
        HANDCHAIN_STOCK = bytes.fromhex(
            "2948816fc90741d130682d4a8004800c904204d80fd22b49884211d022e0111cdd31884203d8dd3290"
            "4209d01ae02649884205d016e0")
        HANDCHAIN_NEW = struct.pack("<27H",
            0x6830,             # 73AE ldr  r0,[r6]          ; moved card word
            0x0480, 0x0C80,     # 73B0 lsls/lsrs r0,#18      ; r0 = cid
            0x2183, 0x0149, 0x3910,   # 73B4 movs r1,#0x83 ; lsls r1,r1,#5 ; subs r1,#0x10 = 0x1050
            0x4288, 0xD017,     # 73BA cmp r0,r1 ; beq 0x021C73EE (MATCH) -- before the battle flag
            0x4925,             # 73BE ldr  r1,[0x021C7454]  ; =0x0229C294 (stock pool word)
            0x6F89,             # 73C0 ldr  r1,[r1,#0x78]
            0x07C9,             # 73C2 lsls r1,r1,#31
            0xD139,             # 73C4 bne  0x021C743A       ; battle: skip the posters (stock target)
            0x4A2A,             # 73C6 ldr  r2,[0x021C7470]  ; 0x20D3 R-Genex Oracle
            0x4290, 0xD00B,     # 73C8 cmp r0,r2 ; beq 0x021C73E4 (its extra check, stock target)
            0x4929,             # 73CC ldr  r1,[0x021C7474]  ; 0x17CC Watapon
            0x4288, 0xD00D,     # 73CE cmp ; beq MATCH
            0x1C11, 0x31DD,     # 73D2 adds r1,r2,#0 ; adds r1,#0xDD   ; 0x21B0 Rose Fairy
            0x4288, 0xD009,     # 73D6 cmp ; beq MATCH
            0x4927,             # 73DA ldr  r1,[0x021C7478]  ; 0x224B Breeze
            0x4288, 0xD006,     # 73DC cmp ; beq MATCH
            0xE017,             # 73E0 b    0x021C7412       ; NO MATCH (stock target)
            0x46C0)             # 73E2 nop  (mov r8,r8)
        assert len(HANDCHAIN_NEW) == len(HANDCHAIN_STOCK) == 0x36

        # --- PART H: U3 PRINTED timing -- "if your monster inflicts battle damage: SS from hand" ---
        # Precedent = Tragoedia 0x1F99: the battle-damage handler (logs move code 0x10 @0x021D0824;
        # r7 = the player TAKING damage, r6 = arg) posts to HAND cards via 0x021D36C0(side, cid,
        # 0x10, r6) @0x021D07B8, and Tragoedia's cls2 record is identical to ours.  The very next
        # call @0x021D07C4 posts to phantom 0x0EC4 (no card_prop, unclaimed) through the FIELD
        # poster -- dead code.  It is repurposed in place: cid 0x1050, side = r7+1 (the poster masks
        # the side with &1, so this is the ATTACKER), hand poster.  Pure data; no flag gate (the
        # hand poster has none -- Tragoedia relies on that mid-battle).
        DMG_SITE = 0x021D07C4
        DMG_POOL = 0x021D0834                  # sole loader: 0x021D07C4
        DMG_PHANTOM = 0x0EC4
        FIELD_POSTER, HAND_POSTER = 0x021D3438, 0x021D36C0
        DMG_STOCK = bytes.fromhex("1b49381c1022331c02f034fe")
        DMG_NEW = (struct.pack("<4H", 0x491B,  # ldr  r1,[0x021D0834]  ; = 0x1050
                               0x1C78,         # adds r0,r7,#1         ; attacker side (callee &1)
                               0x2210,         # movs r2,#0x10         ; code (stock)
                               0x1C33)         # adds r3,r6,#0         ; arg (stock)
                   + _bl(DMG_SITE + 8, HAND_POSTER))
        assert _bl(DMG_SITE + 8, FIELD_POSTER) == DMG_STOCK[8:]


        def _arm9_list(sec, base: int, count: int) -> list[int]:
            return [struct.unpack_from("<H", sec.data, base + 2 * i - sec.ramAddress)[0]
                    for i in range(count)]

        def apply_effect(ov: bytearray) -> None:
            before_listb = bytes(ov[_off(LISTB):_off(LISTB) + 2 * 51])

            # PART B -- U1
            list_insert(ov, DA_LIST, DA_COUNT, DONOR_CID, DA_DROP,
                         f"B direct-attack list @0x{DA_LIST:08X}")

            # PART C -- U3's cls2 record (the ARM9 half is apply_handresp)
            insert_row(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, CLS2_FMT,
                           CLS2_NEW, CLS2_DROP, "C cls2 (hand self-SS)")

            # PART D -- U4's trigger
            list_insert(ov, LISTA, LISTA_COUNT, DONOR_CID, LISTA_DROP,
                         f"D LIST A (damage by DIRECT attack) @0x{LISTA:08X}")

            # PART E -- U4's resolver
            insert_row(ov, CLS1_BASE, CLS1_COUNT, CLS1_STRIDE, CLS1_FMT,
                           CLS1_NEW, CLS1_DROP, "E cls1 (Synchro-summon resolver)")
            insert_row(ov, CRIT_BASE, crit_count(ov), CRIT_STRIDE, CRIT_FMT,
                           CRIT_NEW, CRIT_DROP, "E criteria row (Watt Synchro, set code 0x58)")

            # PART E2 -- hand material only during U4 (gate tail -> ov3 stub in phantom 0x1433's leaf)
            stub = gate_stub()
            assert len(stub) <= GATE_STUB_SIZE
            assert_thumb1_only(stub, GATE_STUB)
            assert_thumb1_only(GATE_HOOK_NEW, GATE_HOOK)
            cur = (bytes(ov[_off(GATE_HOOK):_off(GATE_HOOK) + 4]),
                   struct.unpack_from("<I", ov, _off(GATE_POOL))[0],
                   struct.unpack_from("<H", ov, _off(GATE_SEAL))[0],
                   bytes(ov[_off(GATE_STUB):_off(GATE_STUB) + len(stub)]))
            if cur == (GATE_HOOK_NEW, GATE_STUB | 1, GATE_SEAL_NEW, stub):
                print("E2 hand-material gate: already hooked (idempotent)")
            elif cur[:3] == (GATE_HOOK_NEW, GATE_STUB | 1, GATE_SEAL_NEW):
                # an older E2 stub is installed (pre-E4 build): upgrade it in place, same slot
                ov[_off(GATE_STUB):_off(GATE_STUB) + GATE_STUB_SIZE] = stub.ljust(GATE_STUB_SIZE, b"\0")
                print(f"E2 hand-material gate stub upgraded in place @0x{GATE_STUB:08X} ({len(stub)} B, E4 per-cell)")
            else:
                assert cur[:3] == (GATE_HOOK_STOCK, GATE_POOL_STOCK, GATE_SEAL_STOCK), (
                    f"E2 gate/seal sites not stock: {cur[0].hex()} {cur[1]:#x} {cur[2]:#x}")
                struct.pack_into("<H", ov, _off(GATE_SEAL), GATE_SEAL_NEW)
                ov[_off(GATE_STUB):_off(GATE_STUB) + len(stub)] = stub
                struct.pack_into("<I", ov, _off(GATE_POOL), GATE_STUB | 1)
                ov[_off(GATE_HOOK):_off(GATE_HOOK) + 4] = GATE_HOOK_NEW
                print(f"E2 hand-material gate @0x{GATE_HOOK:08X} -> ov3 stub 0x{GATE_STUB:08X} ({len(stub)} B, "
                      f"phantom 0x{GATE_PHANTOM:04X} leaf, arm sealed): 0x2353 as stock, 0x{DONOR_CID:04X} "
                      f"only while [0x{FORCED_SLOT:08X}] != 0")

            # PART E4 -- level_sum's hand loop: hand, then field (in place, pool untouched)
            for site, stock, new in zip((LS_A, LS_B), (LS_A_STOCK, LS_B_STOCK), level_sum_loop()):
                assert_thumb1_only(new, site)
                cur = bytes(ov[_off(site):_off(site) + len(new)])
                if cur == new:
                    print(f"E4 level_sum loop @0x{site:08X}: already rewritten (idempotent)")
                    continue
                assert cur == stock, f"E4 level_sum @0x{site:08X} is not stock: {cur.hex()}"
                ov[_off(site):_off(site) + len(new)] = new
                print(f"E4 level_sum hand loop @0x{site:08X} rewritten ({len(new)} B): a hand miss falls into the field scan")

            # PART G -- U3's add-to-hand trigger
            cur = bytes(ov[_off(HANDCHAIN):_off(HANDCHAIN) + len(HANDCHAIN_NEW)])
            if cur == HANDCHAIN_NEW:
                print("G Deck->hand self-SS chain: already rewritten (idempotent)")
            else:
                assert cur == HANDCHAIN_STOCK, f"G chain @0x{HANDCHAIN:08X} is not stock: {cur.hex()}"
                assert_thumb1_only(HANDCHAIN_NEW, HANDCHAIN)
                ov[_off(HANDCHAIN):_off(HANDCHAIN) + len(HANDCHAIN_NEW)] = HANDCHAIN_NEW
                print(f"G Deck->hand self-SS chain @0x{HANDCHAIN:08X}: +0x{DONOR_CID:04X}, tested before "
                      f"the battle flag (Watapon/Oracle/Rose Fairy/Breeze kept, stock battle skip)")

            # PART H -- U3 printed timing (your monster inflicts battle damage)
            cur = (bytes(ov[_off(DMG_SITE):_off(DMG_SITE) + len(DMG_NEW)]),
                   struct.unpack_from("<I", ov, _off(DMG_POOL))[0])
            if cur == (DMG_NEW, DONOR_CID):
                print("H battle-damage hand post: already retargeted (idempotent)")
            else:
                assert cur == (DMG_STOCK, DMG_PHANTOM), f"H site @0x{DMG_SITE:08X} not stock: {cur[0].hex()} {cur[1]:#x}"
                assert_thumb1_only(DMG_NEW, DMG_SITE)
                ov[_off(DMG_SITE):_off(DMG_SITE) + len(DMG_NEW)] = DMG_NEW
                struct.pack_into("<I", ov, _off(DMG_POOL), DONOR_CID)
                print(f"H battle-damage poster @0x{DMG_SITE:08X}: phantom 0x{DMG_PHANTOM:04X} field post -> "
                      f"0x{DONOR_CID:04X} HAND post for the attacker")

            # Tripwires: the two things this patch must NOT disturb.
            assert bytes(ov[_off(LISTB):_off(LISTB) + 2 * 51]) == before_listb, \
                "LIST B (ungated battle damage) was modified -- U4 would fire on any damage"
            assert bytes(ov[_off(AURORA_HANDLER):_off(AURORA_HANDLER) + AURORA_LEN]) == AURORA_STOCK, \
                "Blackwing Aurora's native criteria handler was modified"

        def apply_watt_setcode(rom) -> None:
            """PART F -- make the donor a "Watt" so the Watt Synchros accept it as material."""
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)

            lit = struct.unpack_from("<I", d, WATT_LIST_LIT - ARM9_BASE)[0]
            imm = struct.unpack_from("<H", d, WATT_COUNT_IMM - ARM9_BASE)[0]
            bse = struct.unpack_from("<I", d, WATT_BSEARCH_LIT - ARM9_BASE)[0]
            assert lit == WATT_LIST, f"F Watt list pool word moved: 0x{lit:08X}"
            assert imm == (0x2200 | WATT_LIST_COUNT), f"F Watt count immediate drifted: 0x{imm:04X}"
            assert bse == 0x02022E15, f"F the Watt thunk's bsearch pointer moved: 0x{bse:08X}"

            cur = [struct.unpack_from("<H", d, WATT_LIST + 2 * i - ARM9_BASE)[0]
                   for i in range(WATT_LIST_COUNT)]
            if DONOR_CID in cur:
                print(f"F Watt set code: 0x{DONOR_CID:04X} already a member (idempotent)")
                return
            assert WATT_DROP in cur, f"F 0x{WATT_DROP:04X} is not in the Watt list -- already spent?"
            assert all(cur[i] < cur[i + 1] for i in range(len(cur) - 1)),         "F the Watt list is not strictly sorted in the base ROM"
            new = sorted([c for c in cur if c != WATT_DROP] + [DONOR_CID])
            assert len(new) == WATT_LIST_COUNT and all(new[i] < new[i + 1] for i in range(len(new) - 1))
            struct.pack_into(f"<{WATT_LIST_COUNT}H", d, WATT_LIST - ARM9_BASE, *new)
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            print(f"F Watt set code @0x{WATT_LIST:08X} (x{WATT_LIST_COUNT}, count/geometry unchanged): "
                  f"displaced 0x{WATT_DROP:04X}, inserted 0x{DONOR_CID:04X} @{new.index(DONOR_CID)}")


        def apply_handresp(rom) -> None:
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)

            lit = struct.unpack_from("<I", d, HANDRESP_LIT - ARM9_BASE)[0]
            imm = struct.unpack_from("<H", d, HANDRESP_COUNT_IMM - ARM9_BASE)[0]
            assert lit == HANDRESP_LIST, f"C hand-responder literal moved: 0x{lit:08X}"
            assert imm == (0x2200 | HANDRESP_COUNT), f"C count immediate drifted: 0x{imm:04X}"

            cur = [struct.unpack_from("<H", d, HANDRESP_LIST + 2 * i - ARM9_BASE)[0]
                   for i in range(HANDRESP_COUNT)]
            if DONOR_CID in cur:
                print(f"C hand-responder list: 0x{DONOR_CID:04X} already a member (idempotent)")
                return
            assert HANDRESP_DROP in cur, f"C phantom 0x{HANDRESP_DROP:04X} already spent"
            assert all(cur[i] < cur[i + 1] for i in range(len(cur) - 1)), \
                "C the hand-responder list is not strictly sorted in the base ROM"
            new = sorted([c for c in cur if c != HANDRESP_DROP] + [DONOR_CID])
            assert len(new) == HANDRESP_COUNT and all(new[i] < new[i + 1] for i in range(len(new) - 1))
            struct.pack_into(f"<{HANDRESP_COUNT}H", d, HANDRESP_LIST - ARM9_BASE, *new)
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            print(f"C hand-responder list @0x{HANDRESP_LIST:08X} (x{HANDRESP_COUNT}): dropped "
                  f"0x{HANDRESP_DROP:04X}, inserted 0x{DONOR_CID:04X} @{new.index(DONOR_CID)}")

        stubs = tuple((addr, blob, label) for label, addr, blob in _u3_blobs())

        def install(rom, view):
            apply_effect(view.buf)
            apply_handresp(rom)
            apply_watt_setcode(rom)

        def check_fn(c, rom, view):
            ov = bytearray(view.buf)

            def check(cond, label):
                c.ok(bool(cond), label)

            # PART B
            da = u16_keys(ov, DA_LIST, DA_COUNT, 2)
            check(len(da) == DA_COUNT and DONOR_CID in da and DA_DROP not in da,
                  f"B direct-attack list x{DA_COUNT}, 0x{DONOR_CID:04X} in, 0x{DA_DROP:04X} out")
            check(all(da[i] < da[i + 1] for i in range(len(da) - 1)),
                  "B direct-attack list still strictly sorted")

            # PART C
            k2 = u16_keys(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE)
            check(k2.count(DONOR_CID) == 1 and CLS2_DROP not in k2,
                  f"C exactly one cls2 row for 0x{DONOR_CID:04X}, phantom dropped")
            if DONOR_CID in k2:
                rec = struct.unpack_from(CLS2_FMT, ov, _off(CLS2_BASE + k2.index(DONOR_CID) * CLS2_STRIDE))
                check(rec == CLS2_NEW, f"C cls2 record == {[hex(v) for v in CLS2_NEW]} (reads {[hex(v) for v in rec]})")
            check(all(k2[i] <= k2[i + 1] for i in range(len(k2) - 1)), "C cls2 table still sorted")

            mc, sec = ov5_cave._arm9_main(rom)
            hr = _arm9_list(sec, HANDRESP_LIST, HANDRESP_COUNT)
            check(len(hr) == HANDRESP_COUNT and DONOR_CID in hr and HANDRESP_DROP not in hr,
                  f"C hand-responder list x{HANDRESP_COUNT}, 0x{DONOR_CID:04X} in")
            check(all(hr[i] < hr[i + 1] for i in range(len(hr) - 1)),
                  "C hand-responder list still strictly sorted")
            check(struct.unpack_from("<H", sec.data, HANDRESP_COUNT_IMM - ARM9_BASE)[0]
                  == (0x2200 | HANDRESP_COUNT), "C hand-responder count immediate unchanged")
            check(0x21A9 in hr and 0x17CC in hr and 0x21B0 in hr,
                  "C Battle Fader / Watapon / Rose Fairy still in the hand-responder list")

            # PART D
            la = u16_keys(ov, LISTA, LISTA_COUNT, 2)
            check(len(la) == LISTA_COUNT and DONOR_CID in la and LISTA_DROP not in la,
                  f"D LIST A x{LISTA_COUNT}, 0x{DONOR_CID:04X} in, 0x{LISTA_DROP:04X} out")
            check(all(la[i] < la[i + 1] for i in range(len(la) - 1)), "D LIST A still strictly sorted")
            lb = u16_keys(ov, LISTB, 51, 2)
            check(DONOR_CID not in lb, "D LIST B (ungated damage) does NOT contain the donor")

            # PART E
            k1 = u16_keys(ov, CLS1_BASE, CLS1_COUNT, CLS1_STRIDE)
            check(k1.count(DONOR_CID) == 1 and CLS1_DROP not in k1,
                  f"E exactly one cls1 row for 0x{DONOR_CID:04X}, phantom dropped")
            if DONOR_CID in k1:
                rec = struct.unpack_from(CLS1_FMT, ov, _off(CLS1_BASE + k1.index(DONOR_CID) * CLS1_STRIDE))
                check(rec == CLS1_NEW, f"E cls1 record == {[hex(v) for v in CLS1_NEW]} (reads {[hex(v) for v in rec]})")
            check(all(k1[i] <= k1[i + 1] for i in range(len(k1) - 1)), "E cls1 table still sorted")

            ccount = crit_count(ov)
            kc = u16_keys(ov, CRIT_BASE, ccount, CRIT_STRIDE)
            check(kc.count(DONOR_CID) == 1 and CRIT_DROP not in kc,
                  f"E exactly one criteria row for 0x{DONOR_CID:04X}, phantom dropped")
            if DONOR_CID in kc:
                row = struct.unpack_from(CRIT_FMT, ov, _off(CRIT_BASE + kc.index(DONOR_CID) * CRIT_STRIDE))
                check(row == CRIT_NEW, f"E criteria row == {[hex(v) for v in CRIT_NEW]} (reads {[hex(v) for v in row]})")

            stub = gate_stub()
            check(bytes(ov[_off(GATE_HOOK):_off(GATE_HOOK) + 4]) == GATE_HOOK_NEW
                  and struct.unpack_from("<I", ov, _off(GATE_POOL))[0] == GATE_STUB | 1,
                  f"E2 gate tail @0x{GATE_HOOK:08X} -> ldr/bx ov3 stub 0x{GATE_STUB:08X}")
            check(bytes(ov[_off(GATE_STUB):_off(GATE_STUB) + len(stub)]) == stub
                  and struct.unpack_from("<H", ov, _off(GATE_SEAL))[0] == GATE_SEAL_NEW,
                  f"E2 stub in phantom 0x{GATE_PHANTOM:04X}'s leaf, arm sealed (bne -> b)")
            for site, new in zip((LS_A, LS_B), level_sum_loop()):
                check(bytes(ov[_off(site):_off(site) + len(new)]) == new,
                      f"E4 level_sum hand loop @0x{site:08X} rewritten (hand, then field)")
            check(all(struct.unpack_from("<I", ov, _off(a))[0] == v
                      for a, v in ((LS_POOL_B3C, 0xB3C), (LS_POOL_PLAYER, 0x0229AC94))),
                  "E4 level_sum literal pool untouched")
            check(struct.unpack_from("<I", ov, _off(0x02249538))[0] == 0x2184
                  and struct.unpack_from("<I", ov, _off(0x02249534))[0] != DONOR_CID,
                  "E2 Eccentric Boy literal untouched; 0x02249534 is NOT ours (Mara's in the chain)")

            check(bytes(ov[_off(AURORA_HANDLER):_off(AURORA_HANDLER) + AURORA_LEN]) == AURORA_STOCK,
                  "E Aurora's handler is byte-identical to stock (we point AT it, never edit it)")
            check(struct.unpack_from("<H", ov, _off(AURORA_HANDLER + 0x10))[0] == 0x2004,
                  "E Aurora's mode byte is still `movs r0,#4` -- NOT 0x24 (in-game failure 1)")

            # PART F
            wl = _arm9_list(sec, WATT_LIST, WATT_LIST_COUNT)
            check(len(wl) == WATT_LIST_COUNT and DONOR_CID in wl and WATT_DROP not in wl,
                  f"F Watt list x{WATT_LIST_COUNT}, 0x{DONOR_CID:04X} in, 0x{WATT_DROP:04X} displaced")
            check(all(wl[i] < wl[i + 1] for i in range(len(wl) - 1)),
                  "F Watt list still strictly sorted")
            check(struct.unpack_from("<I", sec.data, WATT_LIST_LIT - ARM9_BASE)[0] == WATT_LIST
                  and struct.unpack_from("<H", sec.data, WATT_COUNT_IMM - ARM9_BASE)[0]
                  == (0x2200 | WATT_LIST_COUNT)
                  and struct.unpack_from("<I", sec.data, WATT_BSEARCH_LIT - ARM9_BASE)[0] == 0x02022E15,
                  "F the Watt thunk is otherwise stock (list ptr, count imm, bsearch ptr)")
            check(all(c in wl for c in (0x230F, 0x2477, 0x0FD3, 0x2261, 0x22FD)),
                  "F Wattchimera / Watthydra / Wattkid / Wattgiraffe / Wattpheasant still Watts")

            # PART G
            check(bytes(ov[_off(HANDCHAIN):_off(HANDCHAIN) + len(HANDCHAIN_NEW)]) == HANDCHAIN_NEW,
                  f"G Deck->hand self-SS chain @0x{HANDCHAIN:08X} includes 0x{DONOR_CID:04X}")
            check(struct.unpack_from("<3I", ov, _off(0x021C7470)) == (0x20D3, 0x17CC, 0x224B)
                  and struct.unpack_from("<I", ov, _off(0x021C7454))[0] == 0x0229C294,
                  "G chain pool words (Oracle / Watapon / Breeze / battle-flag block) untouched")

            # U2 (U3 once per turn)
            for label, addr, blob in _u3_blobs():
                check(ov5_cave.read_cave(rom, addr, len(blob)) == blob, f"{label} installed @{addr:#x}")

            # PART H
            check(bytes(ov[_off(DMG_SITE):_off(DMG_SITE) + len(DMG_NEW)]) == DMG_NEW
                  and struct.unpack_from("<I", ov, _off(DMG_POOL))[0] == DONOR_CID,
                  f"H battle-damage handler posts 0x{DONOR_CID:04X} to the attacker's HAND @0x{DMG_SITE:08X}")
            check(struct.unpack_from("<2I", ov, _off(0x021D082C)) == (0x199E, 0x1F99)
                  and struct.unpack_from("<2I", ov, _off(0x021D0838)) == (0x1B8C, 0x1CF7),
                  "H Gorz / Tragoedia / Gellenduo / Volcanic Counter posters untouched")


        return Compiled(stubs, installs=(install,), checks=(check_fn,))


wattuna_effects = direct_attack_hand_special_summon_after_battle_damage_and_synchro_summon_watt_from_extra_deck

SPEC = card(0x1050, wattuna_effects())

PROPS = card_props("LIGHT", "Thunder", level=4, atk=800, defense=700, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_wattuna.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
