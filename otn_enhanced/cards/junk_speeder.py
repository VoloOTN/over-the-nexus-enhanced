"""Junk Speeder (WIND / Warrior / Synchro Effect / Level 5 / 1800 / 1000) on Twin-Headed Thunder Dragon 0x120B.

    1 "Synchron" Tuner + 1+ non-Tuner monsters
    If this card is Synchro Summoned: You can Special Summon as many "Synchron" Tuners with different Levels as possible
    from your Deck, in Defense Position. (See card_text.CARD_TEXT[0x120B] for the full printed text.)
"""
from __future__ import annotations

import struct
import sys

from otn_enhanced import dsl
from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R3, R4, R5, R6, R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.dsl import card, card_props, fusion_to_synchro_effect, Compiled, RES_RESERVE
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import bl as _thumb_bl
from otn_enhanced.rom.overlay_io import RAM_BASE
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
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
import ndspy.rom
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class synchro_summoned_special_summon_synchron_tuners_of_different_levels_from_deck_once_per_turn_synchron_tuner_material:
    """Junk Speeder (Twin-Headed Thunder Dragon 0x120B, a vanilla Fusion donor made a Synchro Effect Monster by `fusion_to_synchro_effect`):
    '1 "Synchron" Tuner + 1+ non-Tuner monsters. If this card is Synchro Summoned: you can Special Summon as many "Synchron" Tuners
    with different Levels as possible from your Deck in Defense Position (once per turn)...'. cls1 record cloned from Karakuri Burei over
    phantom 0x12A9, criteria row over 0x16C2 (a cloned Deck handler whose walker callback skips already-used Levels), the shared
    Synchro-Summoned trigger (summon_trigger_hook; the proper-SS list is full), a cond that makes it hard once-per-turn, six ov5 stubs
    and the Tuner-side material gate at 0x022485D8 (the card file keeps `build_tuner_gate` / `chain_tuner_gate` for dragunity_remus and
    infernoble); "Junk" set-code membership over phantom 0x2524. Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.cards import junk_speeder as _js
        from otn_enhanced.cards.junk_servant import add_junk_member
        from otn_enhanced.data import card_genre as pcg
        from otn_enhanced.data.card_stats import find_pac
        from otn_enhanced.effects import summon_trigger_hook as sth
        from otn_enhanced.effects.common import ARM9_BASE, bl as _thumb_bl, insert_row, u16 as _u16, u32 as _u32
        from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
        from otn_enhanced.rom.overlay_io import RAM_BASE
        import ndspy.code
        DONOR_CID = cid
        build_tuner_gate, _bl_target_at, apply_tuner_gate = _js.build_tuner_gate, _js._bl_target_at, _js.apply_tuner_gate

        # ---------------------------------------------------------------------------
        # Engine addresses.  Every one of these is VERIFIED/ANCHORED in docs/engine or
        # was read out of ov3  (see notes/junk-speeder-findings.md).
        # ---------------------------------------------------------------------------
        CLS1_BASE, CLS1_COUNT, CLS_STRIDE = 0x022860D4, 0x535, 24     # dispatch.cls_tables
        CRIT_BASE, CRIT_COUNT, CRIT_STRIDE = 0x022713C4, 0x56C, 12    # counter.criteria_registry_layout
        CLS_FMT, CRIT_FMT = "<HHIIIII", "<HHII"
        SUMMON_TRIGGER_LIST, SUMMON_TRIGGER_N = 0x0228F6C0, 0x24      # summon.trigger_is_a_membership_list

        # The vanilla donor owns NEITHER record, so PARTs A and B are count-neutral
        # INSERTS over phantom cids, not the in-place rewrites the Sphreeze build did.
        # Both were picked by ranking every unclaimed phantom that owns
        # EXACTLY ONE row in its table by how many OTHER structures name it:
        #   0x12A9  cls1 record[113] is its ONLY binding structure anywhere (extra = 0)
        #   0x16C2  criteria row[247]; its one leftover is an unreachable cls1 record[332]
        #           (no card_prop, so it is never dispatched) -- the best available, every
        #           other unclaimed criteria phantom carries three or more.
        CLS1_PHANTOM, CRIT_PHANTOM = 0x12A9, 0x16C2

        # the record shape Karakuri Burei 0x23A0 uses for this exact effect
        SLOT3_OPTIONAL_TRIGGER = 0x021F0419     # activation condition: gates on the criteria row
        SLOT4_TRIGGER_COST = 0x021E51E5         # the shared "no cost" trigger step
        DECK_CRIT_HANDLER = 0x0223CAB5          # the stock DECK criteria handler (Burei's)

        # --- PARTs L / M / C: Fusion Monster -> Synchro Monster ---------------------
        # accel_synchro_stardust_dragon's recipe, unchanged.  The donor's genre is
        # byte-identical to its donor's, so the constants are literally the same.
        REFERENCE_SYNCHRO_CID = 0x23FE          # Laval Twin Slayer, a plain Synchro Effect Monster
        DONOR_GENRE = 0x0000000020200000        # {21 nomi, 29 FUSION}
        NEW_GENRE = 0x0000001000200000          # {21 nomi, 36 SYNCHRO}
        FUSION_ROW_INDEX = 47                   # fusion recipe A row for the donor
        FUSION_ROW_ADDR = 0x02270B94 + FUSION_ROW_INDEX * 8
        FUSION_STOCK = (DONOR_CID, 0x114F, 0x114F, 0)   # Thunder Dragon x2
        FUSION_DEAD = 0x3FFF
        # The Synchro material-count EXCEPTION lists.  Absence from both is what makes
        # the printed "1 Tuner + 1+ non-Tuner monsters" the donor's rule; this patch
        # asserts it rather than adding anything.
        LIST_A = (0x02275AB8, 16)               # "exactly N materials"
        LIST_MIN3 = (0x02275AD8, 21)            # "at least 3 materials"

        from otn_enhanced.effects.common import ARM9_BASE

        # --- CLAUSE 1: the donor's material rule ------------------------------------
        # The vanilla Fusion donor has NO per-cid material arm at all, so both sides
        # start generic and only the TUNER side needs restricting.
        #
        # PROOF (scratch/cid_reach_probe.py).  A per-cid arm keys either on a
        # pool literal equal to the cid -- donor_scan.occurrences finds exactly one
        # binding occurrence of 0x120B anywhere in ov3 + ARM9, its fusion recipe row --
        # or on `base +/- imm8` off a pool literal (thumb.stack_based_switch), which
        # stores no cid and so needs a literal within 0xFF of the cid.  Across the whole
        # material-predicate span 0x02248280-0x02249600 (INNER 0x0224829C, OUTER
        # 0x022485B4, THIRD 0x02248A88 and their leaves) there are ZERO literals within
        # 0xFF of 0x120B -- and likewise zero for Meteor B. Dragon 0x126F, whose generic
        # "1 Tuner + 1+ non-Tuner" rule accel_synchro_stardust_dragon had in-game
        # confirmed.  (The old donor 0x24B3 had SIX, which is why the
        # Sphreeze build needed a PART H to open its exclusive "Gusto" leaf 0x02249360.)
        # So "1+ non-Tuner monsters" is native here and nothing has to be edited for it.
        #
        # The NON-TUNER side is asserted, not assumed -- verify() re-runs the same scan.
        NONTUNER_SCAN_SPAN = (0x02248280, 0x02249600)

        # PART I -- the Tuner gate.
        INNER_PRED = 0x0224829C                 # synchro.inner_pred
        TUNER_HOOK_SITE = 0x022485D8            # OUTER's `bl 0x0224829C` -- the TUNER caller
        NONTUNER_CALLER = 0x02248AAC            # THIRD's, owned by azure_eyes
        MATERIAL_CID_OF = 0x021A3320            # (arg1, arg2) -> the material's cid
        SYNCHRON_THUNK = 0x02023E1C             # has_set_code[0x4C], setcode.synchron_table

        # --- PART J: "Junk" archetype membership ------------------------------------
        # Junk Speeder's NAME makes it a "Junk" card, so Junk support should find it.
        # setcode.junk_table: set code 0x50, a sorted 13-entry u16 list @0x0209C842 that
        # ships with TWO phantoms, 0x2500 and 0x2524 -- the real Konami ids of Junk
        # Servant and Junk Berserker.  junk_servant already spent 0x2500, so this
        # patch spends 0x2524; the insert stays count-neutral and the list stays sorted,
        # which the consumer thunk's hardcoded `movs r2,#0x0D` requires.
        JUNK_PHANTOM = 0x2524

        # --- PART K: the hard once-per-turn (clause 5) -------------------------------
        # dispatch.turnlog_once_per_turn_pair (VERIFIED), and the same pair
        # shooting_quasar PART K already ships in-game.
        TURNLOG_QUERY = 0x021A14E8      # (side, 0x0B, cid, kind) -> nonzero iff already logged
        TURNLOG_POST = 0x021D2584       # (side, cid, kind, 0) -> log it
        IS_RESOLVE_CTX = 0x021D2B88     # nonzero in a resolve/replay context
        TURNLOG_SLOT = 0x0B
        TURNLOG_KIND = 1                # kind 1 IS swept at end of turn -> per TURN
                                        # (kind 5 is never swept -> per DUEL; see
                                        #  dispatch.turnlog_once_per_duel_is_kind_5)
        CAVE_COND = ov5_cave.CAVE_JSP_COND
        COND_RESERVE = 0x50
        # Quickdraw Synchron.  Printed "Cannot be used as a Synchro Material, except for
        # the Synchro Summon of a monster that LISTS a 'Synchron' Tuner as material" --
        # and the engine implements that as a NINE-CID WHITELIST inside INNER (Road
        # Warrior, Junk Warrior, Nitro Warrior, Turbo Warrior, Junk Archer, Drill
        # Warrior, Junk Destroyer, Junk Gardna, Chevalier de Fleur).  Junk Speeder DOES
        # list a "Synchron" Tuner but postdates the game, so it is not in that list and
        # INNER refuses Quickdraw for it.  MEASURED: sweeping all 140 Synchro monsters
        # gives exactly those 9; sweeping every Synchron Tuner as material against the
        # donor shows Quickdraw is the ONLY one refused.  The gate overrides that single
        # rejection and nothing else.
        QUICKDRAW_CID = 0x20F7

        CAVE_TUNER = ov5_cave.CAVE_JSP_TUNER
        TUNER_RESERVE = 0x80

        # primitives the resolver calls (all decoded in ninjitsu_art_super_transformation)
        PHASE_BLOCK = 0x0229AAFC                # [+0x70] = the current resolver phase
        SS_FREE_ZONE = 0x021AD870               # (side) -> free monster zones; 0 = cannot SS
        SS_LEGAL_A = 0x021B9ECC                 # (side)
        SS_LEGAL_B = 0x021B9ED8                 # (side)
        PARAM_PROVIDER = 0x02234E78             # (desc) -> the criteria `param`
        CRIT_CANDIDATE_COUNT = 0x02243FA8       # (side, cid, param) -> n; CALLS OUR ROW HANDLER
        MESSAGE = 0x0219A818                    # (side, code); 0x0D = "there is none"
        SS_COMMIT = 0x0226925C                  # (side, &locator, face_up, position, [sp]=cid<<16)
        RESOLUTION_TEARDOWN = 0x021D269C        # (side)
        LIST_PICKER = 0x0219C430                # (side, mode=6, cid, param) opens the list picker
        PICK_READBACK = 0x0219C510              # () -> &LOCATOR_ARRAY[picked index]  (a POINTER)
        MESSAGE_CHOOSE = 0x30                   # the "choose a card" message code (chassis phase 0x7F)
        DECK_WALKER = 0x0223BC3C                # (side, cid, callback, &aux, [sp]=word, [sp+4]=mode)
        DECK_WALKER_CALLBACK = 0x0223C825       # the literal 0x0223CAB4 passes in r2
        DECK_WALKER_MODE = 0x0A                 # the literal 0x0223CAB4 passes at [sp+4]
        CALLBACK_MATCHER = 0x020240D8           # the stock callback's tail target (cid, selector)
        LEVEL_OF = 0x0202ABD8                   # (cid) -> the card's ORIGINAL Level

        # The pooled-picker revision (user request): one prompt per summon
        # offering every eligible "Synchron" Tuner whose Level has not been used yet.
        # The criteria word CANNOT express a Level SET (one field, op exactly/>=/<=), so
        # the per-Level filter moves into a clone of the walker's per-candidate callback.
        CAVE_USED = ov5_cave.CAVE_JSP_USED      # 16 bytes, one per Level 0..15
        CAVE_CB = ov5_cave.CAVE_JSP_CB          # the callback clone
        USED_RESERVE, CB_RESERVE = 0x20, 0x50
        MAX_LEVEL_SLOTS = 16

        SYNCHRON_SET_CODE = 0x004C              # setcode.synchron_table (VERIFIED)
        # low half: bit 1 = is a real card, bit 15 = IS A TUNER.  High half = the Level
        # field, written at runtime as (k << 2) << 16 with op 0 = "Level exactly k".
        BASE_CRIT_WORD = 0x00008002
        # ov5 slots (claimed in ov5_cave.py; the ledger guard is the backstop)
        CAVE_DATA = ov5_cave.CAVE_JSP_DATA
        CAVE_CRIT = ov5_cave.CAVE_JSP_CRIT
        CAVE_RES = ov5_cave.CAVE_JSP_RES
        # CAVE_DATA is a 0x10 B block: +0x00 the criteria word, +0x04 the aux cell.
        # +0x08 used to hold a Level counter for the ascending sweep; the pooled-picker
        # revision replaced that with the used-Level array CAVE_JSP_USED, so the word is
        # now CONSTANT and the resolver never writes this block at all.
        # RES_RESERVE was 0x120 while the cave was full, which left the round-3
        # resolver 4 bytes of slack; widened to 0x200 once RESERVE grew to 64 KB so
        # clauses 1/3/4/5 are not fighting for bytes.  CAVE_FREE moved with it.
        DATA_RESERVE, CRIT_RESERVE, RES_RESERVE = 0x10, 0x40, 0x200

        # ---------------------------------------------------------------------------
        # Card identity (PART E).  The name and description come from card_text.CARD_TEXT
        # — NEVER from a local constant.  0x120B is a CARD_TEXT cid, so it takes the
        # INDEX-ORDER RE-EMIT path (the full printed text, no in-place slot limit), and
        # a local copy would silently go stale the way five shipped modules' did.
        # ---------------------------------------------------------------------------
        NEW_LEVEL, NEW_ATK, NEW_DEF = 5, 1800, 1000
        NEW_ATTRIBUTE, NEW_RACE = "WIND", "Warrior"
        # PART L already copies a real Synchro's whole card_prop record; passing the
        # encoded type here as well keeps apply_stats_and_text's own write consistent.
        NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Synchro Effect Monster"]


        # ===========================================================================
        # PART D1 — the criteria-row handler (ov5)
        # ===========================================================================

        def build_crit_stub(base: int) -> bytes:
            """(r0 = criteria row, r1 = side, r2 = param) -> candidate count.

            A clone of the stock DECK handler 0x0223CAB4 with ONE semantic change: the
            criteria WORD is read from CAVE_DATA+0 instead of row[+8], so the resolver
            can vary the Level field per iteration without ever writing to the ov3
            criteria table.  Mode 0x0A and callback 0x0223C825 are copied verbatim.

            ⚠️ The walker takes the aux BY REFERENCE in r3 (the stock handler points it
            at its own stack slot).  We point it at CAVE_DATA+4 and REFRESH that cell
            from row[+2] on every call, so the cell cannot go stale and it does not
            matter whether the walker writes through the pointer.

            ⚠️ The stock handler builds its outgoing stack arguments out of the slots
            that `push {r1,r2,r3,lr}` just reserved.  We do the same with a split push
            so that r4 is available to hold the far call target (this assembler has no
            long-form BL): after `push {r4,lr}` + `push {r1,r2,r3}`, [sp] and [sp+4] are
            the walker's two stack arguments.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("PUSH", "{R1, R2, R3}")
            b.insn("ADD", "R2, R0, #0x0")
            b.ldr_const(3, base_aux_cell())
            b.insn("LDRH", "R0, [R2, #0x2]")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("ASR", "R0, R0, #0x10")
            b.insn("STR", "R0, [R3, #0x0]")
            b.ldr_const(0, CAVE_DATA)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("STR", "R0, [SP, #0x0]")
            b.insn("MOV", f"R0, #0x{DECK_WALKER_MODE:X}")
            b.insn("STR", "R0, [SP, #0x4]")
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("LDRH", "R1, [R2, #0x0]")
            b.call_addr(DECK_WALKER, R0, R1, CAVE_CB | 1, via=R4)
            b.insn("POP", "{R1, R2, R3}")
            b.insn("POP", "{R4, PC}")
            blob = b.assemble(base, pad="nop")
            assert len(blob) <= CRIT_RESERVE, f"crit {len(blob):#x} > reserve {CRIT_RESERVE:#x}"
            assert_thumb1_only(blob, base)
            return blob


        def base_aux_cell() -> int:
            """CAVE_DATA+4 — the aux (set code) cell the walker reads through r3."""
            return CAVE_DATA + 4


        # ===========================================================================
        # PART D1b — the Deck-walker CALLBACK clone (the per-Level veto)
        # ===========================================================================
        def build_callback_stub(base: int) -> bytes:
            """The walker's per-candidate hook, with "this Level is already used" added.

            A clone of the stock callback 0x0223C824, which is:

                ldr r0,[sp] ; ldr r1,[sp,#4] ; ldr r0,[r0] ; ldr r1,[r1]
                lsls r0,#0x12 ; lsrs r0,#0x12          ; r0 = the candidate's CID
                ldr r3,=0x020240D9 ; bx r3             ; TAIL-call the matcher

            MEASURED, not assumed (thumbemu over rom_junk_speeder.ml3, twice):
              * it executes exactly ONCE PER ACCEPTED CANDIDATE -- 10 executions for a
                count of 10, 2 for a count of 2 -- so it runs after the criteria word
                has already filtered, on each survivor;
              * its return value is a HARD VETO -- forcing `movs r0,#0 ; bx lr` takes the
                candidate count from 10 to 0, and forcing 1 leaves it at 10.

            ⚠️ THE ORIGINAL HAS NO STACK FRAME.  Its arguments live at [sp] and [sp+4]
            of the WALKER's frame, so this clone loads both BEFORE it pushes anything.
            ⚠️ The tail target 0x020240D8 takes (cid, SELECTOR < 0x70) and dispatches
            through a pointer table; that second argument is NOT the criteria word, so
            do not "simplify" this by passing the word.
            """
            b = EffectBuilder()
            b.insn("LDR", "R0, [SP, #0x0]")
            b.insn("LDR", "R1, [SP, #0x4]")
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LDR", "R1, [R1, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(CALLBACK_MATCHER, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "cbout")
            b.call("cid_level", R4, via=R5)
            b.ldr_const(5, CAVE_USED)
            b.insn("LDRB", "R1, [R5, R0]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BNE", "cbveto")
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "cbout")
            b.label("cbveto")
            b.insn("MOV", "R0, #0x0")
            b.label("cbout")
            b.insn("POP", "{R4, R5, PC}")
            blob = b.assemble(base, pad="nop")
            assert len(blob) <= CB_RESERVE, f"callback {len(blob):#x} > {CB_RESERVE:#x}"
            assert_thumb1_only(blob, base)
            return blob


        # ===========================================================================
        # PART D2 — the resolver (ov5), cls1[donor] +04
        # ===========================================================================
        def build_resolver_stub(base: int) -> bytes:
            """(r0 = descriptor) -> the next phase.  Our OWN phase machine.

            Deliberately NOT a wrapper around the shared chassis 0x02206CAD.  NAST
            delegated to a native resolver three times and froze the game every time;
            that stub owns every phase itself and so does this one.  The phase window is
            0x78..0x80 (`subs r1,#0x78 ; cmp r1,#8 ; bls` in the chassis prologue), and
            the driver re-enters with whatever nonzero value we return; 0 stops.

            ROUND 3 runs the chassis's OWN prompt cycle -- message 0x7F, picker 0x7E,
            read-back 0x7C -- once per Level, so the player chooses WHICH "Synchron"
            Tuner is summoned at each Level.  ("As many as possible with different
            Levels" fixes how many and at what Levels, but not which card, and the user
            asked for a prompt at EVERY Level, even where only one card qualifies.)

              0x80  the chassis's own three Special-Summon legality gates, then set the
                    Level counter to 1 and go to 0x7F.
                    (No candidate probe: slot3 0x021F0419 has ALREADY run the same
                    criteria lookup -- 0x02243FE0 and 0x02243FA8 both go through
                    0x02243B9C to the row's handler -- so the effect cannot be
                    activated at all unless the Deck holds at least one "Synchron"
                    Tuner.  The old probe, its 0x0D message and the 0x7B cleanup arm
                    were dead code and are gone.)
              0x7F  FIND THE NEXT LEVEL THAT HAS CANDIDATES.  Stops at MAX_LEVEL or
                    when the monster zones fill.  Publishes "Level exactly k, Tuner,
                    real card" into CAVE_DATA and runs 0x02243FA8; on 0 it advances k
                    and loops (searching costs nothing and summons nothing, so this
                    loop is safe inside one phase -- unlike a summon loop, which is the
                    round-1 bug below).  On a hit it shows message 0x30 ("choose") and
                    goes to 0x7E, leaving CAVE_DATA holding THAT Level's word so the
                    picker enumerates the same set.
              0x7E  0x0219C430(side, 6, cid, param) opens the list picker, then 0x7C.
              0x7C  0x0219C510() -> &LOCATOR[picked]; summon it face-up in DEFENCE;
                    advance the Level counter; return 0x7F for the next Level.
              0x78  restore CAVE_DATA to the resting word, 0x021D269C(side) teardown,
                    then return 0x64 = STOP.  (NAST returns 1 here instead because it
                    attaches a phase-1 rider; this card has no rider, so the chassis's
                    own 0x64 is correct.)

            *** WHY 0x78 RESTORES CAVE_DATA -- a bug caught before it shipped. ***
            The ov5 criteria handler takes its word from CAVE_DATA, and the ACTIVATION
            GATE goes through that same handler (slot3 0x021F0419 -> 0x02243FE0 ->
            0x02243B9C -> row[+4]).  Without the restore, CAVE_DATA would still hold the
            last Level word after a resolution, so the NEXT Junk Speeder in the same
            duel would have its activation tested as "Level exactly 12 Synchron Tuner",
            find nothing, and never be offered.  Every path that writes a Level word
            (only 0x7F does) terminates through 0x78, and the "cannot Special Summon"
            path leaves the resting word untouched, so the cell is always clean.

            *** WHY 0x7E RE-ENTERS ITSELF INSTEAD OF LOOPING — the round-1 bug. ***
            Round 1 ran the whole Level sweep inside ONE phase-0x7E invocation, calling
            0x0226925C twelve times in a row.  In-game that summoned exactly ONE monster:
            Quickdraw Synchron, the HIGHEST matching Level, i.e. the LAST iteration with
            a hit.  Proven by savestate emulation (notes/junk-speeder-findings.md):
              * every Level's search worked — Levels 1..5 returned counts 4/2/3/3/2 and
                0x02243FA8 really does repopulate the locator array;
              * but 0x0226925C DOES NOT PLACE THE CARD.  It fills the single global
                summon descriptor 0x02298A28 and returns; two consecutive emulated calls
                left the monster-zone records untouched and BOTH got zone 1 back from
                0x021AD8C4 ("first free zone"), so the second simply overwrote the first.
            Placement is deferred and driven from that one descriptor, so N calls in one
            phase can only ever produce ONE summon.  The engine's own sequencing is the
            fix: the invoke site 0x02218032..0x0221804C publishes [r4+0x18] to
            [0x0229AAFC+0x70], calls slot1 ONCE, stores the returned phase back, and
            then RETURNS 0x64 to the outer step machine (or 0x0A when the resolver
            returns 0).  So a nonzero return ends this step and the resolver is
            re-invoked on a later one — which is precisely the gap the deferred
            placement needs.  Returning 0x7E therefore yields one summon per step, and
            the free-zone check becomes meaningful (in round 1 the zones never changed
            mid-loop, so it could never fire).  Bounded by LEVEL_CELL: at most
            MAX_LEVEL + 1 re-entries, so it cannot spin.

            Frame: `push {{r3,r4,r5,r6,r7,lr}}` — the r3 slot is the scratch word at
            [sp] that 0x0226925C takes as its fifth argument, exactly NAST's frame.
            r5 = descriptor, r6 = side; r4 holds the phase and then the Level, r7 the
            LEVEL_CELL pointer.  The Level counter CANNOT live in a register: it has to
            survive between phase invocations.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R6, [R5, #0x2]")
            b.insn("LDRB", "R0, [R5, #0x6]")
            b.insn("EOR", "R6, R0")
            b.ldr_const(4, PHASE_BLOCK)
            b.insn("LDR", "R4, [R4, #0x70]")
            b.insn("CMP", "R4, #0x78")
            b.insn("BEQ", "ph78")
            b.insn("CMP", "R4, #0x80")
            b.insn("BEQ", "ph80")
            b.insn("CMP", "R4, #0x7F")
            b.insn("BEQ", "ph7f")
            b.insn("CMP", "R4, #0x7E")
            b.insn("BEQ", "ph7e")
            b.insn("CMP", "R4, #0x7C")
            b.insn("BEQ", "ph7c")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("ph78")
            b.ldr_const(0, CAVE_USED)
            b.insn("MOV", "R1, #0x0")
            b.insn("STR", "R1, [R0, #0x0]")
            b.insn("STR", "R1, [R0, #0x4]")
            b.insn("STR", "R1, [R0, #0x8]")
            b.insn("STR", "R1, [R0, #0xC]")
            b.call_addr(RESOLUTION_TEARDOWN, R6, via=R3)
            b.insn("MOV", "R0, #0x64")
            b.insn("B", "ret")
            b.label("stop0")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("ph80")
            b.call_addr(SS_FREE_ZONE, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop0")
            b.call_addr(SS_LEGAL_A, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop0")
            b.call_addr(SS_LEGAL_B, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "stop0")
            b.ldr_const(0, CAVE_USED)
            b.insn("MOV", "R1, #0x0")
            b.insn("STR", "R1, [R0, #0x0]")
            b.insn("STR", "R1, [R0, #0x4]")
            b.insn("STR", "R1, [R0, #0x8]")
            b.insn("STR", "R1, [R0, #0xC]")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.insn("MOV", f"R2, #0x{TURNLOG_KIND:X}")
            b.call("turnlog_post", R0, R1, R2, 0, via=R7)
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("ph7e")
            b.call_addr(PARAM_PROVIDER, R5, via=R3)
            b.insn("ADD", "R3, R0, #0x0")
            b.insn("LDRH", "R2, [R5, #0x0]")
            b.insn("MOV", "R1, #0x6")
            b.call_addr(LIST_PICKER, R6, via=R7)
            b.insn("MOV", "R0, #0x7C")
            b.insn("B", "ret")
            b.label("ph7c")
            b.call_addr(PICK_READBACK, via=R3)
            b.insn("ADD", "R7, R0, #0x0")
            b.insn("LDR", "R0, [R7, #0x0]")
            b.insn("LSL", "R0, R0, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.call("cid_level", via=R3)
            b.ldr_const(2, CAVE_USED)
            b.insn("MOV", "R1, #0x1")
            b.insn("STRB", "R1, [R2, R0]")
            b.insn("LDRH", "R0, [R5, #0x0]")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("STR", "R0, [SP, #0x0]")
            b.call_addr(SS_COMMIT, R6, R7, 1, 1, via=R4)
            b.insn("MOV", "R0, #0x7F")
            b.insn("B", "ret")
            b.label("ph7f")
            b.call_addr(SS_FREE_ZONE, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ph7fdone")
            b.call_addr(PARAM_PROVIDER, R5, via=R3)
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(CRIT_CANDIDATE_COUNT, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ph7fdone")
            b.insn("ADD", "R0, R6, #0x0")
            b.insn("MOV", f"R1, #0x{MESSAGE_CHOOSE:X}")
            b.call_addr(MESSAGE, via=R3)
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("ph7fdone")
            b.insn("MOV", "R0, #0x78")
            b.label("ret")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            blob = b.assemble(base, pad="nop")
            assert len(blob) <= RES_RESERVE, f"resolver {len(blob):#x} > reserve {RES_RESERVE:#x}"
            assert_thumb1_only(blob, base)
            return blob


        def build_data_block() -> bytes:
            """CAVE_DATA: [0] the live criteria word, [4] the aux cell, [8] the Level counter.

            All three are rewritten at runtime; the image values are the resting state,
            and give verify() something non-zero to anchor on.  The Level counter rests
            at 0 and is initialised to 1 by phase 0x80, so a second activation always
            starts from Level 1 rather than inheriting the previous resolution's count.
            """
            return struct.pack("<III", BASE_CRIT_WORD, SYNCHRON_SET_CODE, 0) + bytes(4)


        # ===========================================================================
        # ov3 table helpers
        # ===========================================================================




        def _u16s(ov: bytes, addr: int, n: int) -> tuple:
            return struct.unpack_from(f"<{n}H", ov, addr - RAM_BASE)


        def _w16(ov: bytearray, addr: int, v: int) -> None:
            struct.pack_into("<H", ov, addr - RAM_BASE, v)


        def _w32(ov: bytearray, addr: int, v: int) -> None:
            struct.pack_into("<I", ov, addr - RAM_BASE, v)


        def _find_row(ov: bytes, base: int, count: int, stride: int, cid: int,
                      width: int, label: str) -> int:
            """Index of the (single) row for *cid*.  Anchored on the CID, never on an
            index literal — see otn-chain-build-verify-artifact."""
            read = _u16 if width == 2 else _u32
            hits = [i for i in range(count) if read(ov, base + i * stride) == cid]
            assert len(hits) == 1, f"{label}: expected exactly one row for 0x{cid:04X}, got {hits}"
            return hits[0]


        # ===========================================================================
        # PART A — the cls1 record
        # ===========================================================================
        def cls1_record() -> tuple:
            """Karakuri Burei's cls1 shape, with our own resolver and OPT gate.

            +04 RESOLVER    -> the ov5 phase machine (the chassis summons ONE monster)
            +08             -> no on-field candidate predicate
            +0C             -> PART K's hard OPT gate, which chains the native 0x021F0419
            +10             -> the shared "no cost" trigger step
            +14             -> no target declaration (clause 2 declares none)
            """
            return (DONOR_CID, 0, CAVE_RES | 1, 0, CAVE_COND | 1, SLOT4_TRIGGER_COST, 0)


        def apply_cls1_record(ov: bytearray) -> None:
            """Count-neutral sorted INSERT of the donor's cls1 record.

            The vanilla Fusion donor owns no record, so unlike the Sphreeze build this is
            an insert over a phantom, not an in-place rewrite.
            """
            insert_row(ov, CLS1_BASE, CLS1_COUNT, CLS_STRIDE, CLS_FMT,
                           cls1_record(), CLS1_PHANTOM, "A cls1")


        # ===========================================================================
        # PART B — the criteria row
        # ===========================================================================
        def criteria_row() -> tuple:
            """{cid, aux = the "Synchron" set code, handler = our ov5 clone, word}.

            The handler is the ov5 clone so the resolver can vary the Level field; the
            word in the table is the resting value (the clone reads CAVE_DATA, not
            row[+8]) — but slot3's activation gate 0x021F0419 runs the SAME lookup, so
            the row must still name the right handler and aux.
            """
            return (DONOR_CID, SYNCHRON_SET_CODE, CAVE_CRIT | 1, BASE_CRIT_WORD)


        def apply_criteria_row(ov: bytearray) -> None:
            """Count-neutral sorted INSERT of the donor's criteria row."""
            insert_row(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, CRIT_FMT,
                           criteria_row(), CRIT_PHANTOM, "B criteria")


        # ===========================================================================
        # PART C — kill the donor's fusion recipe

        def assert_generic_material_rule(ov: bytes) -> None:
            """The donor must reach the GENERIC material leaves on both sides.

            Two independent conditions, both re-checked on every build because a later
            patch could add either:

              1. Absence from the two material-COUNT exception lists.  That absence IS
                 the "1 Tuner + 1+ non-Tuner" rule -- there is nothing to insert.
              2. No per-cid ARM anywhere in the material predicates.  A per-cid compare
                 keys on a pool literal equal to the cid, or on `base +/- imm8` off one
                 (thumb.stack_based_switch, which stores no cid) -- and the second form
                 cannot reach a cid from a literal further than 0xFF away.  Zero
                 literals within 0xFF over the whole span therefore CLOSES the question.
                 Meteor B. Dragon 0x126F scores zero on the same span and its generic
                 rule is in-game confirmed; Daigusto Sphreeze 0x24B3 scored six, which
                 is what the retired PART H had to undo.
            """
            for base, n in (LIST_A, LIST_MIN3):
                assert DONOR_CID not in _u16s(ov, base, n), (
                    f"H donor 0x{DONOR_CID:04X} joined the material-count list 0x{base:08X} "
                    f"-- the printed '1+ non-Tuner monsters' no longer holds")
            lo, hi = NONTUNER_SCAN_SPAN
            near = [(a, _u32(ov, a)) for a in range(lo, hi, 4) if abs(_u32(ov, a) - DONOR_CID) <= 0xFF]
            assert not near, (
                f"H a literal within 0xFF of 0x{DONOR_CID:04X} appeared in the material "
                f"predicates: {[(hex(a), hex(v)) for a, v in near]} -- a per-cid arm may now "
                f"select this donor and clause 1 is no longer proven")
            print(f"H material rule is generic: donor absent from both count lists, and 0 "
                  f"literals within 0xFF of 0x{DONOR_CID:04X} in 0x{lo:08X}-0x{hi:08X}")


        # ===========================================================================
        # PARTs L + M — card_prop / card_genre: make the Fusion donor a Synchro monster

        def build_cond_stub(base: int) -> bytes:
            """(r0 = descriptor, r1 = arg1) -> the activation code, gated on the turn log.

            Pot of Duality's own shape, and the shim shooting_quasar PART K already
            ships in-game:

                if IS_RESOLVE_CTX(desc):  chain the native condition
                    -- a RESOLVING effect must not re-deny itself, or the effect that is
                       already on the chain would abort halfway.
                if TURNLOG_QUERY(desc[+2], 0x0B, desc[+0], 1):  return 0
                else: chain the native condition 0x021F0419

            ⚠️ r1 is carried through in r4 and restored: 0x021F0419 is a TWO-argument
            condition, and Quasar's notes record an in-game regression caused by chaining
            a 2-arg native without restoring its second argument.

            kind 1 is the end-of-turn-swept kind, which is what makes this per TURN.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R4, R1, #0x0")
            b.call_addr(IS_RESOLVE_CTX, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "native")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("MOV", f"R1, #0x{TURNLOG_SLOT:X}")
            b.insn("LDRH", "R2, [R5, #0x0]")
            b.insn("MOV", f"R3, #0x{TURNLOG_KIND:X}")
            b.call("turnlog_query", via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "deny")
            b.label("native")
            b.call_addr(SLOT3_OPTIONAL_TRIGGER, R5, R4, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("deny")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            blob = b.assemble(base, pad="nop")
            assert len(blob) <= COND_RESERVE, f"cond {len(blob):#x} > {COND_RESERVE:#x}"
            assert_thumb1_only(blob, base)
            return blob

        def apply_ov5(rom) -> None:
            for addr, blob, reserve, label in (
                    (CAVE_DATA, build_data_block(), DATA_RESERVE, "runtime words"),
                    (CAVE_USED, bytes(MAX_LEVEL_SLOTS), USED_RESERVE, "used-Level array"),
                    (CAVE_CB, build_callback_stub(CAVE_CB), CB_RESERVE, "walker callback"),
                    (CAVE_COND, build_cond_stub(CAVE_COND), COND_RESERVE, "once-per-turn gate"),
                    (CAVE_CRIT, build_crit_stub(CAVE_CRIT), CRIT_RESERVE, "criteria handler"),
                    (CAVE_RES, build_resolver_stub(CAVE_RES), RES_RESERVE, "resolver")):
                if ov5_cave.read_cave(rom, addr, len(blob)) != blob:
                    ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                print(f"D {label:<18} -> ov5 0x{addr:08X} ({len(blob)} B of 0x{reserve:X})")


        # ===========================================================================
        # Preconditions — refuse to build on a ROM that is not what this patch assumes
        # ===========================================================================
        def check_preconditions(ov: bytes) -> None:
            # The donor is NOT a member and cannot become one -- the list is 36 real cids
            # with no phantom and its neighbours are packed flush.  PART N's shared ov5
            # hook is what supplies the trigger, so assert the list is exactly what that
            # hook assumes: still sorted (it is binary-searched) and still without us.
            n = [_u16(ov, SUMMON_TRIGGER_LIST + 2 * k) for k in range(SUMMON_TRIGGER_N)]
            assert DONOR_CID not in n, (
                f"0x{DONOR_CID:04X} unexpectedly joined the Synchro-summon trigger list "
                f"0x{SUMMON_TRIGGER_LIST:08X} — the ov5 arm would then be redundant"
            )
            assert all(n[k] < n[k + 1] for k in range(len(n) - 1)), "trigger list lost its order"
            assert any(a[0] == DONOR_CID for a in sth.ARMS), \
                "N the trigger arm must be registered in summon_trigger_hook"
            # the template this patch copies must still look like the template
            i = _find_row(ov, CLS1_BASE, CLS1_COUNT, CLS_STRIDE, 0x23A0, 4, "cls1")
            rec = CLS1_BASE + i * CLS_STRIDE
            assert (_u32(ov, rec + 0x0C), _u32(ov, rec + 0x10)) == (
                SLOT3_OPTIONAL_TRIGGER, SLOT4_TRIGGER_COST), (
                "Karakuri Burei's cls1 record no longer has the shape this patch copies")
            j = _find_row(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, 0x23A0, 2, "criteria")
            assert _u32(ov, CRIT_BASE + j * CRIT_STRIDE + 4) == DECK_CRIT_HANDLER, (
                "Karakuri Burei's criteria row no longer uses the stock DECK handler")
            # Tuning's row is the cross-validation for aux 0x4C + the Tuner bit
            t = _find_row(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, 0x23A2, 2, "criteria")
            trow = CRIT_BASE + t * CRIT_STRIDE
            assert (_u16(ov, trow + 2), _u32(ov, trow + 8)) == (SYNCHRON_SET_CODE, BASE_CRIT_WORD), (
                "Tuning 0x23A2 no longer carries {aux 0x4C, word 0x00008002} — the "
                "'Synchron Tuner' filter this patch reuses is unconfirmed")
            print("P preconditions OK (donor outside the trigger list, Burei template, "
                  "Tuning cross-check)")

        stubs = tuple((addr, blob, label) for addr, blob, label in (
            (CAVE_DATA, build_data_block(), "runtime words"), (CAVE_USED, bytes(MAX_LEVEL_SLOTS), "used-Level array"),
            (CAVE_CB, build_callback_stub(CAVE_CB), "walker callback"), (CAVE_COND, build_cond_stub(CAVE_COND), "once-per-turn gate"),
            (CAVE_CRIT, build_crit_stub(CAVE_CRIT), "criteria handler"), (CAVE_RES, build_resolver_stub(CAVE_RES), "resolver")))

        def junk_post(out):
            add_junk_member(out, DONOR_CID, JUNK_PHANTOM)

        def install(rom, view):
            ov = view.buf
            check_preconditions(bytes(ov))
            assert_generic_material_rule(bytes(ov))
            apply_cls1_record(ov)
            apply_criteria_row(ov)
            sth.apply(ov)
            apply_tuner_gate(ov, rom)
            sth.install(rom)

        def check_fn(c, rom, view):
            ov = bytes(view.buf)

            def check(cond, msg):
                return bool(cond)

            ok = True
            # -- A: the cls1 record (a count-neutral insert over CLS1_PHANTOM)
            i = _find_row(ov, CLS1_BASE, CLS1_COUNT, CLS_STRIDE, DONOR_CID, 4, "cls1")
            rec = struct.unpack_from(CLS_FMT, ov, CLS1_BASE + i * CLS_STRIDE - RAM_BASE)
            ok &= check(rec == cls1_record(),
                        f"A cls1[{i}] = {' '.join(f'{v:08X}' for v in rec)}")
            cids = [_u32(ov, CLS1_BASE + k * CLS_STRIDE) for k in range(CLS1_COUNT)]
            ok &= check(all(cids[k] <= cids[k + 1] for k in range(CLS1_COUNT - 1)),
                        "A cls1 is still sorted by cid (binary-search precondition)")
            ok &= check(cids.count(DONOR_CID) == 1 and CLS1_PHANTOM not in cids,
                        f"A exactly one cls1 row for the donor; phantom 0x{CLS1_PHANTOM:04X} spent "
                        f"(count {CLS1_COUNT} unchanged)")

            # -- B: the criteria row (likewise)
            j = _find_row(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, DONOR_CID, 2, "criteria")
            row = struct.unpack_from(CRIT_FMT, ov, CRIT_BASE + j * CRIT_STRIDE - RAM_BASE)
            ok &= check(row == criteria_row(),
                        f"B criteria[{j}] = cid 0x{row[0]:04X} aux 0x{row[1]:04X} "
                        f"handler 0x{row[2]:08X} word 0x{row[3]:08X}")
            ccids = [_u16(ov, CRIT_BASE + k * CRIT_STRIDE) for k in range(CRIT_COUNT)]
            ok &= check(all(ccids[k] <= ccids[k + 1] for k in range(CRIT_COUNT - 1)),
                        "B criteria registry is still sorted by cid")
            ok &= check(ccids.count(DONOR_CID) == 1 and CRIT_PHANTOM not in ccids,
                        f"B exactly one criteria row for the donor; phantom 0x{CRIT_PHANTOM:04X} "
                        f"spent (count {CRIT_COUNT} unchanged)")

            # -- C: the fusion recipe is dead
            ok &= check(_u16s(ov, FUSION_ROW_ADDR, 4) == (DONOR_CID, FUSION_DEAD, FUSION_DEAD, 0),
                        f"C fusion recipe A[{FUSION_ROW_INDEX}] materials are 0x{FUSION_DEAD:04X} "
                        f"(the CPU fusion planner can no longer build the donor)")

            # -- D: the ov5 stubs, byte-exact and Thumb-1
            for addr, blob, label in ((CAVE_DATA, build_data_block(), "runtime words"),
                                      (CAVE_CB, build_callback_stub(CAVE_CB), "walker callback"),
                                      (CAVE_COND, build_cond_stub(CAVE_COND), "once-per-turn gate"),
                                      (CAVE_CRIT, build_crit_stub(CAVE_CRIT), "criteria handler"),
                                      (CAVE_RES, build_resolver_stub(CAVE_RES), "resolver")):
                got = ov5_cave.read_cave(rom, addr, len(blob))
                good = got == blob
                ok &= check(good, f"D {label} @0x{addr:08X} ({len(blob)} B) is byte-exact")
                if good and label != "runtime words":
                    assert_thumb1_only(got, addr)
                    ok &= check(True, f"D {label} is Thumb-1 only")

            # -- D2: the criteria handler must route through OUR callback, not the stock one,
            #        and the used-Level array must exist and be clean in the image
            crit = build_crit_stub(CAVE_CRIT)
            ok &= check(struct.pack("<I", CAVE_CB | 1) in crit,
                        f"D criteria handler passes our callback 0x{CAVE_CB | 1:08X} in r2")
            ok &= check(struct.pack("<I", DECK_WALKER_CALLBACK) not in crit,
                        f"D criteria handler no longer passes the stock callback "
                        f"0x{DECK_WALKER_CALLBACK:08X}")
            used = ov5_cave.read_cave(rom, CAVE_USED, MAX_LEVEL_SLOTS)
            ok &= check(used == bytes(MAX_LEVEL_SLOTS),
                        f"D used-Level array @0x{CAVE_USED:08X} is {MAX_LEVEL_SLOTS} zero bytes "
                        f"in the image (cleared at 0x80 and 0x78 at runtime)")

            # -- J: "Junk" set-code membership
            jrom = rom
            jmc = ndspy.code.MainCodeFile(bytes(jrom.arm9), jrom.arm9RamAddress)
            jsec = next(x for x in jmc.sections if x.ramAddress == ARM9_BASE)
            jd = jsec.data
            junk = [struct.unpack_from("<H", jd, 0x0209C842 - ARM9_BASE + 2 * i)[0] for i in range(13)]
            ok &= check(DONOR_CID in junk, f"J donor is a \"Junk\" member: {[hex(x) for x in junk]}")
            ok &= check(JUNK_PHANTOM not in junk,
                        f"J phantom 0x{JUNK_PHANTOM:04X} was dropped (count-neutral)")
            ok &= check(all(junk[i] < junk[i + 1] for i in range(12)),
                        "J the Junk list is still sorted (its binary search requires it)")
            ok &= check(struct.unpack_from("<H", jd, 0x02023E60 - ARM9_BASE)[0] == 0x220D,
                        "J the Junk count immediate is still movs r2,#0x0D (count-neutral)")

            # -- K: the hard once-per-turn gate
            ok &= check(_u32(ov, CLS1_BASE + i * CLS_STRIDE + 0x0C) == (CAVE_COND | 1),
                        f"K cls1 slot3 -> the OPT gate 0x{CAVE_COND | 1:08X}")
            cond = build_cond_stub(CAVE_COND)
            gotc = ov5_cave.read_cave(rom, CAVE_COND, len(cond))
            ok &= check(gotc == cond, f"K OPT gate @0x{CAVE_COND:08X} ({len(cond)} B) is byte-exact")
            if gotc == cond:
                assert_thumb1_only(gotc, CAVE_COND)
                ok &= check(True, "K OPT gate is Thumb-1 only")
            ok &= check(struct.pack("<I", SLOT3_OPTIONAL_TRIGGER) in cond,
                        "K the OPT gate still CHAINS the native condition 0x021F0419")
            res = build_resolver_stub(CAVE_RES)
            ok &= check(struct.pack("<I", TURNLOG_POST | 1) in res,
                        "K the resolver stamps the turn log (phase 0x80)")

            # -- N: the trigger comes from the SHARED ov5 hook, not the list
            trig = [_u16(ov, SUMMON_TRIGGER_LIST + 2 * k) for k in range(SUMMON_TRIGGER_N)]
            ok &= check(DONOR_CID not in trig and len(trig) == SUMMON_TRIGGER_N,
                        "N the proper-SS list 0x0228F6C0 is untouched (the donor joins via ov5)")
            ok &= check(sth.verify(bytearray(ov), check, rom=rom), "N shared summon-trigger hook")

            # -- H: clause 1, non-Tuner side is generic, and stays that way
            lo, hi = NONTUNER_SCAN_SPAN
            near = [a for a in range(lo, hi, 4) if abs(_u32(ov, a) - DONOR_CID) <= 0xFF]
            ok &= check(not near,
                        f"H 0 literals within 0xFF of 0x{DONOR_CID:04X} in the material predicates "
                        f"0x{lo:08X}-0x{hi:08X} -- no per-cid arm can select this donor")
            for base, n in (LIST_A, LIST_MIN3):
                ok &= check(DONOR_CID not in _u16s(ov, base, n),
                            f"H donor absent from the material-count list 0x{base:08X} "
                            f"(= '1 Tuner + 1+ non-Tuner monsters')")

            # -- I: clause 1, Tuner side is gated on "Synchron"
            want_bl = _thumb_bl(TUNER_HOOK_SITE, CAVE_TUNER)
            got_bl = bytes(ov[TUNER_HOOK_SITE - RAM_BASE:TUNER_HOOK_SITE - RAM_BASE + 4])
            ok &= check(got_bl == want_bl,
                        f"I 0x{TUNER_HOOK_SITE:08X} calls the Tuner gate 0x{CAVE_TUNER:08X}")
            # the live stub may be chained behind another gate; accept either shape
            _live_next = _bl_target_at(ov, TUNER_HOOK_SITE)
            stub = build_tuner_gate(CAVE_TUNER)
            _got = ov5_cave.read_cave(rom, CAVE_TUNER, len(stub))
            if _got != stub:
                for _cand in (getattr(ov5_cave, "CAVE_DR_C1", None),):
                    if _cand is None:
                        continue
                    _alt = build_tuner_gate(CAVE_TUNER, _cand)
                    if ov5_cave.read_cave(rom, CAVE_TUNER, len(_alt)) == _alt:
                        stub = _alt
                        break
            ok &= check(struct.pack("<I", QUICKDRAW_CID) in stub,
                        f"I Tuner gate carries the Quickdraw override literal "
                        f"0x{QUICKDRAW_CID:04X} (its 9-cid whitelist predates this card)")
            got_stub = ov5_cave.read_cave(rom, CAVE_TUNER, len(stub))
            ok &= check(got_stub == stub,
                        f"I Tuner gate @0x{CAVE_TUNER:08X} ({len(stub)} B) is byte-exact")
            if got_stub == stub:
                assert_thumb1_only(got_stub, CAVE_TUNER)
                ok &= check(True, "I Tuner gate is Thumb-1 only")
            # the NON-Tuner caller must be untouched -- it belongs to azure_eyes
            nt = bytes(ov[NONTUNER_CALLER - RAM_BASE:NONTUNER_CALLER - RAM_BASE + 4])
            ok &= check(nt == _thumb_bl(NONTUNER_CALLER, INNER_PRED) or nt != want_bl,
                        f"I THIRD's call @0x{NONTUNER_CALLER:08X} is not claimed by this patch")

            # -- L + M: the Fusion donor really is a Synchro monster now
            rom3 = rom
            _, pac3, arch3 = find_pac(rom3)
            f3 = {f.get_clean_name().lower(): f for f in arch3.files}
            cp3, gn3 = f3["card_prop.bin"], f3["card_genre.bin"]
            n3 = (cp3.size - 8) // 8
            idx3 = next(k for k in range(n3)
                        if int.from_bytes(pac3[cp3.address + 8 + k * 8:cp3.address + 16 + k * 8],
                                          "little") & 0x3FFF == DONOR_CID)
            prop3 = int.from_bytes(pac3[cp3.address + 8 + idx3 * 8:cp3.address + 16 + idx3 * 8], "little")
            genre3 = int.from_bytes(pac3[gn3.address + 8 + idx3 * 8:gn3.address + 16 + idx3 * 8], "little")
            ok &= check((prop3 >> 32) & 0x3F == NEW_CARD_TYPE,
                        f"L card_prop[{idx3}] card_type is {(prop3 >> 32) & 0x3F} "
                        f"(expected {NEW_CARD_TYPE} = Synchro Effect Monster)")
            ok &= check(genre3 in pcg.accepted(DONOR_CID, NEW_GENRE),
                        f"M card_genre[{idx3}] = 0x{genre3:016X} (expected 0x{NEW_GENRE:016X}: "
                        f"bit 29 FUSION clear, bit 36 SYNCHRO set)")

            c.ok(ok, "Junk Speeder: cls1/criteria rows, ov5 stubs, Junk membership, OPT gate, shared trigger hook, material rule, Tuner gate")

        return Compiled(stubs, installs=(install,), posts=(junk_post,), checks=(check_fn,))


speeder_effects = synchro_summoned_special_summon_synchron_tuners_of_different_levels_from_deck_once_per_turn_synchron_tuner_material

SPEC = card(
    0x120B,
    fusion_to_synchro_effect(row=47, stock=(0x114F, 0x114F)),
    speeder_effects())

PROPS = card_props("WIND", "Warrior", level=5, atk=1800, defense=1000, card_type="Synchro Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_junk_speeder.nds")

# Names and helpers other modules read (infernoble: LIST_A / LIST_MIN3; dragunity_remus and dsl: the shared Tuner-side gate).
DONOR_CID = 0x120B                      # Twin-Headed Thunder Dragon (vanilla Fusion, Level 7)
LIST_A = (0x02275AB8, 16)               # "exactly N materials"
LIST_MIN3 = (0x02275AD8, 21)            # "at least 3 materials"
INNER_PRED = 0x0224829C                 # synchro.inner_pred
TUNER_HOOK_SITE = 0x022485D8            # OUTER's `bl 0x0224829C` -- the TUNER caller
NONTUNER_CALLER = 0x02248AAC            # THIRD's, owned by azure_eyes
MATERIAL_CID_OF = 0x021A3320            # (arg1, arg2) -> the material's cid
SYNCHRON_THUNK = 0x02023E1C             # has_set_code[0x4C], setcode.synchron_table
QUICKDRAW_CID = 0x20F7

CAVE_TUNER = ov5_cave.CAVE_JSP_TUNER
TUNER_RESERVE = 0x80

def build_tuner_gate(base: int, next_link: int = None) -> bytes:
    """(r0 = Synchro cid, r1, r2, r3) -> the INNER verdict, ANDed with "is the
    material a Synchron" when the Synchro is our donor.

    *** CHAINING (added 2026-09-21 for dragunity_remus C1). ***
    0x022485D8 is the ONLY Tuner-side material gate (synchro.tuner_gate_hook) and
    more than one card needs it, so this stub's "call INNER" is a PARAMETER:
    *next_link* defaults to INNER 0x0224829C and may instead be another gate stub
    that itself ends by calling INNER.  Junk Speeder's own rule is unchanged --
    only the address it delegates the base verdict to moves -- so a chained build
    is byte-identical for every Synchro except the ones the other gate restricts.
    Use chain_tuner_gate(); do not hand-edit the site.

    Installed over OUTER's `bl 0x0224829C` @0x022485D8.  That call site is
    TUNER-ONLY BY CONSTRUCTION: INNER has exactly two callers, and the other one
    (0x02248AAC, inside THIRD) is the non-Tuner path.  So this gate never sees a
    non-Tuner and needs no is-a-Tuner test of its own.

    Every other Synchro gets INNER's verdict returned completely unchanged.

    The material's cid comes from `0x021A3320(arg1, arg2)` -- the same accessor
    OUTER itself uses at 0x022485CA and the donor's non-Tuner leaf uses at
    0x0224938A -- so this stub introduces no new way of resolving a material.
    """
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.insn("ADD", "R6, R2, #0x0")
    b.ldr_const(7, (next_link if next_link is not None else INNER_PRED) | 1)
    b.insn("BLX", "R7")
    b.insn("ADD", "R7, R0, #0x0")
    b.ldr_const(0, DONOR_CID)
    b.insn("CMP", "R4, R0")
    b.insn("BNE", "out")
    b.call_addr(MATERIAL_CID_OF, R5, R6, via=R3)
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("CMP", "R7, #0x0")
    b.insn("BNE", "chk")
    b.ldr_const(0, QUICKDRAW_CID)
    b.insn("CMP", "R4, R0")
    b.insn("BNE", "rej")
    b.label("chk")
    b.call_addr(SYNCHRON_THUNK, R4, via=R3)
    b.insn("ADD", "R7, R0, #0x0")
    b.insn("B", "out")
    b.label("rej")
    b.insn("MOV", "R7, #0x0")
    b.label("out")
    b.insn("ADD", "R1, R5, #0x0")
    b.insn("ADD", "R2, R6, #0x0")
    b.insn("MOV", "R3, #0x0")
    b.insn("ADD", "R0, R7, #0x0")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    blob = b.assemble(base, pad="nop")
    assert len(blob) <= TUNER_RESERVE, f"tuner gate {len(blob):#x} > {TUNER_RESERVE:#x}"
    assert_thumb1_only(blob, base)
    return blob




def _bl_target_at(ov: bytearray, site: int) -> int | None:
    """Decode the BL at *site* in overlay 3, or None if it is not a BL pair."""
    hw1, hw2 = struct.unpack_from("<2H", ov, site - RAM_BASE)
    if (hw1 & 0xF800) != 0xF000 or (hw2 & 0xF800) != 0xF800:
        return None
    off = (hw1 & 0x7FF) << 12
    if off & (1 << 22):
        off -= (1 << 23)
    return site + 4 + off + ((hw2 & 0x7FF) << 1)


def _reinstall_tuner_gate(rom, blob: bytes) -> None:
    """Re-write THIS patch's own cave slot with a rebuilt stub.

    ov5_cave.install_cave deliberately refuses a non-zero slot, which is the right
    default -- it is what stops two patches silently overlapping. Re-chaining
    rewrites a slot this module already owns, so it clears it first rather than
    weakening that guard.
    """
    try:
        cur = ov5_cave.read_cave(rom, CAVE_TUNER, TUNER_RESERVE)
    except Exception:
        cur = b""
    if cur[:len(blob)] == blob:
        return
    if any(cur):
        ov5 = ov5_cave._load_ov5_decompressed(rom)
        data = bytearray(ov5.data)
        off = CAVE_TUNER - ov5_cave.OV5_RAM_BASE
        data[off:off + TUNER_RESERVE] = bytes(TUNER_RESERVE)
        ov5_cave._save_ov5(rom, ov5, bytes(data))
    ov5_cave.install_cave(rom, CAVE_TUNER, blob, reserve=TUNER_RESERVE)


def chain_tuner_gate(ov: bytearray, rom, next_link: int) -> None:
    """Rebuild this patch's Tuner gate so it delegates the base verdict to *next_link*.

    For another patch that needs the same single hook site. The caller's stub must
    take (r0 = Synchro cid, r1, r2, r3) and end by calling INNER 0x0224829C, exactly
    as this one does when unchained. Idempotent; safe in either build order.
    """
    stub = build_tuner_gate(CAVE_TUNER, next_link)
    _reinstall_tuner_gate(rom, stub)
    o = TUNER_HOOK_SITE - RAM_BASE
    ov[o:o + 4] = _thumb_bl(TUNER_HOOK_SITE, CAVE_TUNER)
    print(f"I TUNER gate CHAINED: 0x{TUNER_HOOK_SITE:08X} -> 0x{CAVE_TUNER:08X} "
          f"-> 0x{next_link:08X} -> INNER 0x{INNER_PRED:08X}")


def apply_tuner_gate(ov: bytearray, rom) -> None:
    o = TUNER_HOOK_SITE - RAM_BASE
    cur_target = _bl_target_at(ov, TUNER_HOOK_SITE)
    # Someone else already claimed the site with their own gate: adopt it as our
    # next link rather than clobbering it (synchro.tuner_gate_hook is unique).
    next_link = None
    if cur_target is not None and cur_target not in (INNER_PRED, CAVE_TUNER):
        next_link = cur_target
        print(f"I TUNER gate: site 0x{TUNER_HOOK_SITE:08X} already calls "
              f"0x{cur_target:08X} -- adopting it as this gate's next link")
    stub = build_tuner_gate(CAVE_TUNER, next_link)
    _reinstall_tuner_gate(rom, stub)
    want = _thumb_bl(TUNER_HOOK_SITE, CAVE_TUNER)
    cur = bytes(ov[o:o + 4])
    if cur != want:
        assert cur_target in (INNER_PRED,) or next_link is not None, (
            f"0x{TUNER_HOOK_SITE:08X} holds {cur.hex()}, which is neither the native "
            f"`bl 0x{INNER_PRED:08X}` nor a chainable gate"
        )
        ov[o:o + 4] = want
    print(f"I TUNER gate -> ov5 0x{CAVE_TUNER:08X} ({len(stub)} B of 0x{TUNER_RESERVE:X}); "
          f"hooked `bl 0x{INNER_PRED:08X}` @0x{TUNER_HOOK_SITE:08X} (OUTER = the Tuner caller)")


# ===========================================================================

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
