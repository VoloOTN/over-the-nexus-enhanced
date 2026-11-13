"""Accel Synchron (DARK / Machine / Synchro Tuner Effect Monster / Level 5 / 500 / 2100) on Bracchio-raidus 0x11A3.

    1 Tuner + 1 or more non-Tuner monsters
    Once per turn: You can send 1 "Synchron" monster from your Deck to the GY, then activate 1 of these effects; Increase this card's Level
    by the Level of the sent monster. Reduce this card's Level by the Level of the sent monster. During your opponent's Main Phase, you can
    (Quick Effect): Immediately after this effect resolves, Synchro Summon using this card you control. You can only Synchro Summon "Accel
    Synchron" once per turn. (See card_text.CARD_TEXT[0x11A3] for the full printed text.)
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class synchro_tuner_one_tuner_and_non_tuners_send_synchron_from_deck_to_graveyard_raise_or_lower_level_quick_effect_synchro_summon:
    """Accel Synchron (Bracchio-raidus 0x11A3, a vanilla Fusion monster made a Synchro Tuner Effect Monster from Formula Synchron's card_prop
    template): '1 Tuner + 1+ non-Tuner monsters. Once per turn: You can send 1 "Synchron" monster from your Deck to the GY, then activate 1 of
    these effects; Increase / Reduce this card's Level by the Level of the sent monster. During your opponent's Main Phase, you can (Quick Effect):
    Immediately after this effect resolves, Synchro Summon using this card you control. You can only Synchro Summon "Accel Synchron" once per
    turn.' Fusion recipe killed (for the ungated AI planner); clause 1 = a cls3 record over 0x0E13 + a "Synchron"-filtered Deck criteria row
    over 0x0E17; clause 2 = the shared deck-send follow hook (phase 0x7C body in ov5); clause 3 = the cls3 slot splitters, a Formula-style
    Quick Effect criteria row over 0x0E2A, the shared criteria-row hook and the ARM9 spell-speed-2 list over 0x0E5B. card_prop template copy and
    card_genre tags, and the "Synchron" set-code membership over 0x0D6B, are posts. Original code embedded verbatim (the legacy per-language
    description ladder is dropped: the card is in CARD_TEXT so the re-emit path ignores slots)."""

    def compile(self, view, cid) -> Compiled:
        import struct
        import ndspy.rom
        from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
        from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.data import card_genre as pcg
        from otn_enhanced.cards import boggart_knight as boggart
        from otn_enhanced.cards import unknown_synchron as unksyn
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.effects import deck_send_follow_hook
        from otn_enhanced.effects import criteria_row_hook
        from otn_enhanced.cards import steam_synchron as steam
        from otn_enhanced.effects.ov5_cave import CAVE_AS_FOLLOW, CAVE_AS_LATCH
        from otn_enhanced.asm.effect_builder import EffectBuilder
        from otn_enhanced.asm.effect_verify import assert_thumb1_only
        from otn_enhanced.data.card_stats import find_pac as _find_pac

        DONOR_CID = 0x11A3          # "Bracchio-raidus" -- the donor; KEEPS this cid

        # ---------------------------------------------------------------------------
        # PART A -- card_prop identity (reference-record copy, then the stat fields)
        # ---------------------------------------------------------------------------
        # Formula Synchron is the ONLY card_type-39 (Synchro Tuner Effect) card in the
        # game, so it is the only possible reference record for this conversion.
        REFERENCE_SYNCHRO_TUNER_CID = 0x239E

        NEW_ATTRIBUTE = "DARK"          # donor is WATER
        NEW_RACE = "Machine"            # donor is Dinosaur
        NEW_LEVEL = 5                   # donor is 6 -- and the Level is now LIVE, because
                                        # can_synchro_summon 0x02249540 reads it via
                                        # 0x0202ABD8 to size the material search.
        NEW_ATK = 500                   # donor is 2200
        NEW_DEF = 2100                  # donor is 2000
        NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Synchro Tuner Effect Monster"]   # 39

        # ---------------------------------------------------------------------------
        # PART B -- card_genre category tags
        # ---------------------------------------------------------------------------
        # Bit meanings measured by whole-table census this session (see the docstring).
        GENRE_BIT_NOMI    = 21      # "Special Summon only"; already set on the donor
        GENRE_BIT_FUSION  = 29      # must be CLEARED
        GENRE_BIT_TUNER   = 35      # must be SET
        GENRE_BIT_SYNCHRO = 36      # must be SET

        DONOR_GENRE_STOCK = (1 << GENRE_BIT_NOMI) | (1 << GENRE_BIT_FUSION)
        NEW_GENRE = ((1 << GENRE_BIT_NOMI) | (1 << GENRE_BIT_TUNER)
                     | (1 << GENRE_BIT_SYNCHRO))
        assert DONOR_GENRE_STOCK == 0x0000000020200000
        assert NEW_GENRE == 0x0000001800200000


        # ---------------------------------------------------------------------------
        # PART D -- kill the donor's fusion recipe (for the UNGATED CPU AI planner)
        # ---------------------------------------------------------------------------
        # fusion.table_a: 161 rows of 8 bytes, {u16 result_cid, u16 m1, u16 m2, u16 m3},
        # sorted by result_cid and binary-searched with the count hardcoded as 161.  We
        # touch ONLY the material columns, so the cid column, the sort order and the row
        # count are all untouched and fusion.table_a still passes.
        FUSION_TABLE_A   = 0x02270B94
        FUSION_ROW_COUNT = 161
        FUSION_ROW       = 38
        FUSION_ROW_ADDR  = FUSION_TABLE_A + FUSION_ROW * 8          # 0x02270CC4
        FUSION_STOCK_M1  = 0x0FC6
        FUSION_STOCK_M2  = 0x0FF7
        # fusion.code_classes: a material slot >= 0x33 is read as a literal CID, not as a
        # category code (the split is the `cmp r0,#0x33` at 0x02232146).  The max real cid
        # is 0x24E8, so 0x3FFF can never match a card -- and being >= 0x33 it never enters
        # that proof's `0 < v < 0x33` category census either.
        FUSION_DEAD_MATERIAL = 0x3FFF

        # ---------------------------------------------------------------------------
        # PART E -- "Synchron" set-code membership
        # ---------------------------------------------------------------------------
        # The slot the user assigned: entry 0 of setcode.synchron_table is 0x0D6B, a
        # Speed Spell.  Dropping it keeps the list a sorted 15-entry set (0x11A3 < 0x181C,
        # so the donor lands at index 0) and leaves the hardcoded count immediate alone.
        SYNCHRON_DROP_CID = 0x0D6B      # "Speed Spell - Deceased Synchron"

        # Read-only cross-checks that the printed summon procedure needs (verify()):
        LIST_A          = 0x02275AB8    # 16 x u16 -- "EXACT, extras forbidden"
        LIST_A_COUNT    = 16
        MIN3_LIST       = 0x02275AD8    # 21 x u16 -- "this Synchro needs >= 3 materials"
        MIN3_LIST_COUNT = 21
        TUNER2_CIDS     = (0x239F, 0x24B2)   # the only cids needing 2 leading Tuners


        # ===========================================================================
        # PART D -- overlay 3
        # ===========================================================================
        # =============================================================================
        # CLAUSE 1 -- "Once per turn: You can send 1 'Synchron' monster from your Deck
        #              to the GY"   ***  PURE DATA, two count-neutral row inserts  ***
        # =============================================================================
        # The template is DARKLORD ASMODEUS 0x205F, whose printed clause is
        # "Once per turn: You can send 1 Fairy-Type monster from your Deck to the
        # Graveyard" -- our sentence with a race filter instead of an archetype one.
        # Its records, read from the committed ov3 oracle:
        #     cls3[543] @0x0227D05C  {+04 0x02208DD5, +08 0, +0C 0x021F0B71,
        #                             +10 0x021E5061, +14 0}
        #     crit[936] @0x02273FA4  {aux 0xFFFF, 0x0223CAD9, 0x88000002}
        # A MONSTER ignition effect lives in cls3 (dispatch.cls_table_selector, sel 3),
        # NOT cls0 -- cls0 is the Spell/Trap activation table, which is why
        # dragon_shrine (a Normal Spell) is the wrong structural template here even
        # though it drives the same resolver.
        #
        # ⚠️ AND cls3 REALLY DOES REACH AN EXTRA-DECK MONSTER.  otn-leave-trigger-cls2
        # records that cls2 dispatch never reaches a Synchro donor; that does NOT
        # generalise.  Census of the four cls tables this session: cls3 holds 79 Synchro
        # and 43 Fusion records, including Stardust Dragon 0x1E36, Black Rose Dragon
        # 0x1EDA and Armory Arm 0x1F33.
        #
        # ⚠️⚠️ THE CRITERIA HANDLER IS 0x0223CAF5, **NOT** 0x0223CAD9.
        # dispatch.criteria_hand_vs_deck_handlers names 0x0223CAD9 as "select from the
        # DECK", and it is -- but it IGNORES the aux, so the "Synchron" filter would have
        # been silently dropped and the picker would have offered EVERY monster in the
        # Deck.  Disassembled:
        #     0x0223CAD8:  ... movs r3,#0 ... movs r2,#0 ; bl 0x0223BC3C   <- no row[+2] read
        #     0x0223CAF4:  ... ldrsh r2,[r3,r0] (= row[+2], THE AUX) ; str r2,[sp,#8]
        #                  ... ldr r2,=0x0223C825 (the set-code predicate) ; add r3,sp,#8
        #                  ... bl 0x0223BC3C                                <- same callee
        # The two are otherwise instruction-for-instruction identical -- same type 2, same
        # word, same cid -- so the ONLY difference between them is the set-code filter.
        # The destination (GY vs hand) is the RESOLVER's business, not the handler's.
        #
        # Seven native cards already pair 0x0223CAF5 + a non-0xFFFF aux + resolver
        # 0x02208DD5, i.e. already print "send 1 <archetype> monster from your Deck to the
        # GY".  THE FABLED PEGGULSUS 0x2209 (aux 0x0041, word 0x00000002) and SCRAP SHARK
        # 0x2469 (aux 0x0057, word 0x00000002) are our sentence verbatim, so the word
        # below is Konami's own value, not a reconstruction.
        CLS3_BASE, CLS3_COUNT, CLS3_STRIDE = 0x02279D74, 0x308, 24
        CRIT_BASE, CRIT_COUNT, CRIT_STRIDE = 0x022713C4, 0x56C, 12
        CRIT_FMT = "<HHII"

        DECK_SEND_RESOLVER = 0x02208DD5   # the shared 9-phase deck-send state machine
        IGNITION_ONCE_COND = 0x021F0B71   # "not used this turn (key 0x0FB6 on side+zone)"
                                          #   AND Foolish Burial's candidate-exists test
                                          #   0x021F0B18.  Shared with Scrap Hunter 0x22F9.
        IGNITION_ONCE_COST = 0x021E5061   # stamps that same key via 0x021C479C(kind 2).
                                          #   Slot 4 == the COST slot == AT ACTIVATION,
                                          #   which is what
                                          #   dispatch.once_per_turn_must_stamp_at_activation
                                          #   requires -- no shim needed.
        DECK_SETCODE_HANDLER = 0x0223CAF5  # select from the DECK, FILTERED BY aux
        SYNCHRON_SET_CODE = 0x004C         # setcode.synchron_table
        CRIT_WORD_MONSTER = 0x00000002     # low half bit 1 = MONSTER; level byte 0 because
                                           #   Deck-reading rows carry a clear zone flag.
                                           #   Deliberately NOT 0x8002 -- bit 15 = Tuner
                                           #   (dispatch.criteria_word_bit15_is_tuner) and the
                                           #   printed text says any "Synchron" MONSTER.

        CLS3_SLOTS = (DECK_SEND_RESOLVER, 0, IGNITION_ONCE_COND, IGNITION_ONCE_COST, 0)
        CRIT_ROW = (DONOR_CID, SYNCHRON_SET_CODE, DECK_SETCODE_HANDLER, CRIT_WORD_MONSTER)

        # Count-neutral inserts: the donor is records-free, so each array drops a PHANTOM
        # cid (no card_prop row) and shifts, keeping both count and sortedness exactly.
        # Both verified free in PHANTOM_CLAIMS *and* still present in the CHAINED image
        # rom_all_patches.nds (otn-register-phantom-same-edit).
        CLS3_PHANTOM = 0x0E13      # cls3[6]  -- dropped to make room
        CRIT_PHANTOM = 0x0E17      # crit[15] -- dropped to make room

        # =============================================================================
        # CLAUSE 2 -- "then activate 1 of these effects; increase / reduce this card's
        #              Level by the Level of the sent monster"
        # =============================================================================
        # Template: EGOTISTICAL APE 0x22EB (cls1[1198] {+04 0x022082A5, +10 0x021E88F5}),
        # printed "you can activate 1 of these effects: * Increase the Level of this card
        # by the Level of the Beast-Type monster. * Decrease the Level of this card by the
        # Level of the Beast-Type monster."  -- clause 2's sentence with a different
        # source zone.  (Found because the USER named the card.)
        #
        # HOW THE ENGINE SPELLS "activate 1 of these effects":
        #   * a two-option prompt 0x0219ABB4(desc, 0x0103, label0, label1,
        #     [sp]=0x01AC, [sp+4]=0, [sp+8]=legality mask)
        #   * the answer appears at [0x0229DD94+0x34] as a 0-based index
        #   * Ape stores index+1 in desc[+0x18]; its resolver leaf 0x022083DC tests
        #     `cmp desc[+0x18],#2` and NEGATES the amount for option 2.
        #
        # ⚠️ THE RIDER IS **KIND 3**, NOT KIND 2.  Two shared stat resolvers look alike and
        # their write tails differ by one immediate: 0x02208499's tail (0x0220873E) writes
        # kind 2 and serves COPY PLANT 0x1EC1, whose text is "this card's Level BECOMES
        # ..." -- a SET.  0x022082A5's tail (0x0220844E) writes kind 3 and serves
        # EGOTISTICAL APE, whose text is "INCREASE / DECREASE the Level BY ..." -- a DELTA.
        # Clause 2 is a DELTA.  Mirror the card whose PRINTED CLAUSE matches, not the
        # resolver you happened to disassemble first (grep-the-template-cards-text-too).
        #     0x0220844E: lsls r0,r4,#0x10 ; lsrs r0,r0,#0x10 ; str r0,[sp]
        #                 ldrb r0,[r5,#2] ; ldrb r1,[r5,#3] ; ldrh r2,[r5] ; movs r3,#3
        #                 bl 0x021C479C
        #
        # WHY IT LIVES IN PHASE 0x7C AND NOT IN SLOT 4 (where Ape puts it):
        # slot 4 runs BEFORE the send, so a slot-4 chooser would make the player pick the
        # direction before knowing which "Synchron" was sent.  Phase 0x7C runs AFTER the
        # send, which is the printed order.  This is possible because THE RESOLVER'S
        # RETURN VALUE IS THE NEXT PHASE (dispatch.resolver_return_is_next_phase): the
        # activation state machine stores it at 0x02218042 (`strh r0,[r4,#0x18]`) and
        # reloads it into the phase word [0x0229AAFC+0x70] at 0x02218038, looping while it
        # is nonzero.  So returning 0x7C from phase 0x7C RE-ENTERS phase 0x7C, giving a
        # two-pass follow-up with no new machinery and no slot-4 clone.
        PROMPT_TWO_OPTION = 0x0219ABB4   # the two-option prompt
        PROMPT_ID = 0x0103               # Ape's prompt id  (0x6B<<2 - 0xA9)
        PROMPT_TITLE = 0x01AC            # the default/title label (also 0x021E5748's default)
        LABEL_INCREASE = 0x016E          # Egotistical Ape's own option-0 label
        LABEL_DECREASE = 0x016F          # Egotistical Ape's own option-1 label
        # ⚠️ The labels are passed DIRECTLY, so this patch does NOT touch the option-label
        # table 0x0226F32C (191 x {s16 cid, s16 label}).  Ape only looks them up there
        # because its native code has no other way to name them; nothing else reads that
        # table for our cid.  One fewer shared table edited, one fewer phantom claimed.
        CHOICE_STATE = 0x0229DD94        # [+0x34] = the selected option index (0-based)
        CHOICE_OFF = 0x34
        RIDER_WRITE = 0x021C479C         # (side, zone, key, kind, value)
        RIDER_KIND_LEVEL_DELTA = 3
        # ⚠️⚠️ THE RIDER KEY IS **NOT** THIS CARD'S OWN CID.  The first build used
        # DONOR_CID and the effect resolved, prompted, and changed nothing -- confirmed by
        # the user in-game and then diagnosed off their savestates: the rider was
        # written and correctly linked into the zone's list ({key 0x11A3, kind 3, value
        # +2/-2}), but the Level GETTER 0x021B807C ignores it.
        #
        # That getter's kind<6 walk (0x021B81E8) dispatches on the node's KEY against a
        # HARDCODED SET -- `cmp r0,#0x18D9` (SET arm) and `cmp r0,#0x1F6A` (DELTA arm) at
        # 0x021B8206/0x021B820C, plus a stack-built table of cids at 0x021B82D6.. encoded
        # base+-imm in the thumb.stack_based_switch style (0x2334 - 0x49 = 0x22EB), which is
        # why NO PC-relative load of any of these keys exists anywhere in overlay 3.
        # So the key is a SEMANTIC SELECTOR, not "the card that created the rider" -- the
        # same idiom as the once-per-turn key 0x0FB6 (Time Wizard's cid) and the 0x1295
        # override in the sibling stat resolver.  An arbitrary donor cid can NEVER be read.
        #
        # MEASURED, not inferred (scratch/accel_level_probe.py, running the engine's own
        # getter over the user's ml4 savestate, base Level 5, A/B on the key alone):
        #     0x22EB  v=+2 -> 7   v=-2 -> 3   v=+7 -> 12   v=-7 -> 1   <-- what we want
        #     0x1F6A  v=+2 -> 3   v=-2 -> 1                (decrease only)
        #     0x1EC1  v=+2 -> 2   v=-2 -> 65534            (SET arm, u16 underflow)
        #     0x11A3  unchanged at 5 for every value       (the shipped bug)
        RIDER_KEY = 0x22EB               # Egotistical Ape's cid, used as the "Level +- N"
                                         #   SELECTOR.  Its arm ADDS the signed value to the
                                         #   base Level and clamps at 1 -- exactly clause 2's
                                         #   printed text, and exactly the sign convention
                                         #   this stub already emits.  Safe against a real
                                         #   Egotistical Ape on the field: the node list is
                                         #   per-(side, zone), so the two never share one.
        LEVEL_OF_CID = 0x0202ABD8        # card_prop word1 bits [13:10]; ARM9, always resident
        LEVEL_OF_ZONE = 0x021B8064       # (side, zone) -> the card's CURRENT Level; the
                                         #   getter Ape's own legality check uses
        PHASE_STATE = 0x0229AAFC         # r5 inside the resolver
        PHASE_SELF = 0x7C                # re-enter this same phase (pass 2)
        PHASE_DONE = 0x64                # finish
        PLAYER_BASE, PLAYER_STRIDE = 0x0229AC94, 0xB3C   # ram.gy_and_banished (VERIFIED)
        GY_ARRAY, GY_COUNT = 0x55C, 0x14


        # =============================================================================
        # CLAUSE 3 -- "During your opponent's Main Phase, you can (Quick Effect):
        #              Immediately after this effect resolves, Synchro Summon using this
        #              card you control."
        # =============================================================================
        # synchro.opponent_turn_summon_is_formulas_cls3 (VERIFIED, and ALREADY IN-GAME
        # CONFIRMED via card.steam_synchron) says this clause is THREE DATA ROWS
        # and zero code: a cls3 record {+04 0x02249EC1, +0C 0x021F1491}, a criteria row
        # {aux 0xFFFF, 0x0223D21D, 0x0802}, and membership of the ARM9 spell-speed-2 list
        # 0x0209C118.  Both the resolver and the criteria handler are cid-agnostic, and the
        # condition 0x021F1490 IS the printed timing (turn-log once-per-turn scan -> must be
        # the OPPONENT's turn -> Main Phase 1 or 2).  That fact even anticipates this card:
        # "ACCEL SYNCHRON prints the same one AND prints the once-per-turn, so for Accel the
        # inherited turn-log gate is CORRECT rather than the deviation it is for Steam
        # Synchron."
        # ⚠️ Formula's cls1 record and its 0x0228F6C0 trigger-list row belong to its DRAW
        # effect and must NOT be copied.
        #
        # *** BUT THE DONOR ALREADY OWNS A cls3 RECORD (clause 1), AND A SECOND ONE IS
        # UNREACHABLE. *** find_event_handler 0x0224A118 binary-searches the table and does a
        # LEFTMOST-EQUAL WALK-BACK (dispatch.cls_table_selector), returning exactly one
        # record per cid -- which is precisely how Warwolf E1 shadowed E2
        # (otn-warwolf-e1-native-responder-path).  So clause 3 SHARES cls3[50], and all three
        # contended slots are split by an ov5 stub.
        #
        # THE DISCRIMINATOR IS THE PRINTED TEXT, not a heuristic: clause 1 is an ignition on
        # YOUR Main Phase, clause 3 is printed "During your OPPONENT's Main Phase".  Formula's
        # own condition already computes it -- `[0x0229DD14+0x34] == 1 - desc[+2]` -- so
        #     opponent's turn  <=>  [0x0229DD14+0x34] != desc[+2]
        # is a four-instruction test, and the same one the criteria_row_hook arm uses.
        SUMMON_RESOLVER = 0x02249EC1     # Formula's Synchro-Summon resolver (cid-agnostic;
                                         #   its ONLY per-cid arm is Urgent Tuning, a TRAP)
        SUMMON_CONDITION = 0x021F1491    # Formula's opponent's-Main-Phase timing condition
        QE_CRIT_HANDLER = 0x0223D21D     # cid-agnostic: reads the cid from the descriptor
        QE_CRIT_FLAGS = 0x0802           # Formula's word, verbatim
        DUEL_STATE = 0x0229DD14
        TURN_PLAYER_OFF = 0x34

        # clause 3's criteria row -- the SECOND row on this cid.  It must sit immediately
        # AFTER clause 1's row or the two clauses swap silently
        # (otn-param-provider-internal-hook), and it is reachable ONLY because
        # criteria_row_hook now carries an arm for this cid: the row resolver forces r4 = 0
        # for a cid in neither membership list, so row 1 is otherwise unaddressable.
        CRIT_ROW_QE = (DONOR_CID, 0xFFFF, QE_CRIT_HANDLER, QE_CRIT_FLAGS)
        CRIT_PHANTOM_QE = 0x0E2A         # dropped to make room for the second row

        # ARM9 spell-speed-2 list -- without membership the responder never polls slot 3.
        QUICKEFFECT_LIST = 0x0209C118
        QUICKEFFECT_COUNT_IMM = 0x02023490   # `movs r2,#0x76` -- 118, a HARDCODED immediate
        QUICKEFFECT_POOL = 0x020234A4
        QUICKEFFECT_DROP = 0x0E5B            # a phantom BELOW the donor, so the shift is clean
                                             #   (0x1774 is spent by steam_synchron; this one
                                             #   is unclaimed in PHANTOM_CLAIMS and still
                                             #   present in the chained image)


        def _build_splitter(addr: int, on_opponent_turn: int, on_our_turn: int | None,
                            label: str) -> bytes:
            """A cls3 slot splitter: route to one native callback or the other by turn.

            The slot ABI is (r0 = descriptor, r1 = arg) and every target here has the same
            signature, so this is a pure TAIL-JUMP -- the callee returns straight to the slot
            invoker and LR never has to be saved.  The turn test therefore borrows only r2/r3
            (scratch under the ABI) and leaves r0 and r1 exactly as they arrived.

                if [0x0229DD14 + 0x34] == desc[+2]:  goto <our-turn target>
                else:                                goto <opponent-turn target>

            *on_our_turn* of None means "return 1 without doing anything", which is how the
            cost slot declines to stamp on the opponent's turn.
            """
            a = EffectBuilder()
            (a
             .ldr_const(2, DUEL_STATE)
             .insn("LDR", "R2, [R2, #0x%X]" % TURN_PLAYER_OFF)   # the turn player
             .insn("LDRB", "R3, [R0, #0x2]")                     # our side
             .insn("CMP", "R2, R3")
             .insn("BEQ", "ours"))
            if on_opponent_turn is None:
                a.insn("MOV", "R0, #0x1").insn("BX", "LR")
            else:
                a.ldr_const(3, on_opponent_turn).insn("BX", "R3")
            a.label("ours")
            if on_our_turn is None:
                a.insn("MOV", "R0, #0x1").insn("BX", "LR")
            else:
                a.ldr_const(3, on_our_turn).insn("BX", "R3")
            code = a.assemble(addr)
            assert_thumb1_only(code, addr)
            return code


        def _build_res() -> bytes:
            """cls3 slot 1 -- Formula's Synchro-Summon resolver, or clause 1's deck-send."""
            return _build_splitter(ov5_cave.CAVE_AS_RES, SUMMON_RESOLVER,
                                   DECK_SEND_RESOLVER, "resolver")


        def _build_cond() -> bytes:
            """cls3 slot 3 -- Formula's opponent's-Main-Phase timing, or clause 1's ignition."""
            return _build_splitter(ov5_cave.CAVE_AS_COND, SUMMON_CONDITION,
                                   IGNITION_ONCE_COND, "condition")


        def _build_cost() -> bytes:
            """cls3 slot 4 -- stamp clause 1's once-per-turn ONLY on our own turn.

            ⚠️ Not an optimisation, a CORRECTNESS REQUIREMENT.  Slot 4 is 0x021E5061, which
            stamps key 0x0FB6 on (side, zone) -- the exact key clause 1's condition
            0x021F0B70 queries.  Left unguarded, activating clause 3 on the opponent's turn
            would silently consume clause 1's once-per-turn for the following turn.
            Formula's own record carries slot 4 = 0, so on the opponent's turn we return 1
            (advance) and stamp nothing.
            """
            return _build_splitter(ov5_cave.CAVE_AS_COST, None,
                                   IGNITION_ONCE_COST, "cost")


        CLS3_SLOTS_MERGED = (ov5_cave.CAVE_AS_RES | 1, 0, ov5_cave.CAVE_AS_COND | 1,
                             ov5_cave.CAVE_AS_COST | 1, 0)


        def _build_follow() -> bytes:
            """CLAUSE 2 -- Accel Synchron's body for the shared phase-0x7C hook.

            Entered by a `bx` from ``deck_send_follow_hook``'s dispatcher, NOT a call: the
            resolver's own frame (`push {r1-r7,lr}` @0x02208DD4) is live, r4 = descriptor,
            r5 = 0x0229AAFC.  LR is free (the return address is on the stack) and every
            exit replicates the resolver's epilogue `pop {r1-r7,pc}` with the next phase
            in r0.

                if [LATCH] == desc: goto pass2

                ; ---- pass 1: work out the amount, then ask ----
                side = desc[+2] ^ desc[+6]
                n = player[side].gy_count ; if n == 0: return 0x64
                amount = LEVEL_OF_CID(player[side].gy[n-1] & 0x3FFF)
                if amount == 0: return 0x64                  ; nothing to add or subtract
                [LATCH+4] = amount
                mask = 4 | 1                                 ; "increase" is always legal
                if LEVEL_OF_ZONE(desc[+2], desc[+3]) > amount: mask |= 2
                PROMPT(desc, 0x0103, 0x016E, 0x016F, 0x01AC, 0, mask)
                [LATCH] = desc ; return 0x7C                 ; re-enter this phase

                ; ---- pass 2: apply ----
                pass2:
                [LATCH] = 0
                sel = [0x0229DD94+0x34] ; desc[+0x18] = sel + 1
                v = [LATCH+4] ; if sel == 1: v = -v           ; option 2 == "reduce"
                RIDER_WRITE(desc[+2], desc[+3], RIDER_KEY, 3, v & 0xFFFF)
                return 0x64

            ⚠️ RIDER_KEY is 0x22EB, NOT this card's cid -- see the constant's comment.  The
            first build used the cid, wrote a perfectly-formed node, and changed nothing,
            because the Level getter only honours keys from a hardcoded set.

            Note the two DIFFERENT side conventions, both copied from the natives they come
            from: the GY read uses `desc[+2] ^ desc[+6]` (dragon_shrine's
            `_build_follow`, dispatch.criteria_probe_side_is_xor_desc6) while the rider
            write uses the RAW desc[+2] (Ape's tail @0x02208454).  Do not "tidy" these into
            one.
            """
            a = EffectBuilder()
            (a
             .ldr_const(6, CAVE_AS_LATCH)
             .insn("LDR", "R0, [R6, #0x0]")
             .insn("CMP", "R0, R4")
             .insn("BEQ", "pass2")

             # ---------------- pass 1 -------------------------------------------------
             .insn("LDRB", "R0, [R4, #0x2]")
             .insn("LDRB", "R1, [R4, #0x6]")
             .insn("EOR", "R0, R1")                  # side = desc[+2] ^ desc[+6]
             .ldr_const(1, PLAYER_STRIDE)
             .insn("MUL", "R1, R0")
             .ldr_const(2, PLAYER_BASE)
             .insn("ADD", "R1, R1, R2")              # r1 = this side's player struct
             .insn("LDR", "R2, [R1, #0x%X]" % GY_COUNT)
             .insn("CMP", "R2, #0x0")
             .insn("BEQ", "done")
             .insn("SUB", "R2, #0x1")
             .insn("LSL", "R2, R2, #0x2")
             .ldr_const(3, GY_ARRAY)
             .insn("ADD", "R1, R1, R3")
             .insn("LDR", "R0, [R1, R2]")            # the GY top word = the card just sent
             .ldr_const(2, 0x3FFF)
             .insn("AND", "R0, R2")
             .bl(LEVEL_OF_CID)                       # r0 = its Level
             .insn("CMP", "R0, #0x0")
             .insn("BEQ", "done")                    # a Level-0 send has nothing to apply
             .insn("ADD", "R7, R0, #0x0")            # r7 = amount
             .ldr_const(6, CAVE_AS_LATCH)
             .insn("STR", "R7, [R6, #0x4]")          # carry it to pass 2

             .insn("LDRB", "R0, [R4, #0x2]")
             .insn("LDRB", "R1, [R4, #0x3]")
             .bl(LEVEL_OF_ZONE)                      # r0 = this card's CURRENT Level
             .insn("MOV", "R5, #0x5")                # mask = 4 | 1: "increase" always legal
             .insn("CMP", "R0, R7")
             .insn("BLS", "ask")                     # current <= amount -> no "reduce"
             .insn("MOV", "R0, #0x2")
             .insn("ORR", "R5, R0")

             .label("ask")
             .insn("SUB", "SP, #0x10")
             .ldr_const(0, PROMPT_TITLE)
             .insn("STR", "R0, [SP, #0x0]")
             .insn("MOV", "R0, #0x0")
             .insn("STR", "R0, [SP, #0x4]")
             .insn("STR", "R5, [SP, #0x8]")          # the legality mask
             .insn("ADD", "R0, R4, #0x0")            # desc
             .ldr_const(1, PROMPT_ID)
             .ldr_const(2, LABEL_INCREASE)
             .ldr_const(3, LABEL_DECREASE)
             .bl(PROMPT_TWO_OPTION)
             .insn("ADD", "SP, #0x10")
             .ldr_const(6, CAVE_AS_LATCH)
             .insn("STR", "R4, [R6, #0x0]")          # latch THIS activation
             .insn("MOV", "R0, #0x%X" % PHASE_SELF)
             .insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}")

             # ---------------- pass 2 -------------------------------------------------
             .label("pass2")
             .insn("MOV", "R0, #0x0")
             .insn("STR", "R0, [R6, #0x0]")          # clear the latch
             .insn("LDR", "R7, [R6, #0x4]")          # r7 = amount
             .ldr_const(0, CHOICE_STATE)
             .insn("LDR", "R5, [R0, #0x%X]" % CHOICE_OFF)   # r5 = selected index
             .insn("ADD", "R0, R5, #0x1")
             .insn("STRH", "R0, [R4, #0x18]")        # desc[+0x18] = sel + 1, as Ape does
             .insn("CMP", "R5, #0x1")
             .insn("BNE", "apply")
             .insn("NEG", "R7, R7")                  # option 2 -> reduce

             .label("apply")
             .insn("SUB", "SP, #0x10")
             .insn("LSL", "R0, R7, #0x10")
             .insn("LSR", "R0, R0, #0x10")           # truncate to u16, as the native tail does
             .insn("STR", "R0, [SP, #0x0]")
             .insn("LDRB", "R0, [R4, #0x2]")         # RAW side -- Ape's convention
             .insn("LDRB", "R1, [R4, #0x3]")         # zone
             .ldr_const(2, RIDER_KEY)                # the "Level +- N" SELECTOR, NOT our cid
             .insn("MOV", "R3, #0x%X" % RIDER_KIND_LEVEL_DELTA)
             .bl(RIDER_WRITE)
             .insn("ADD", "SP, #0x10")

             .label("done")
             .insn("MOV", "R0, #0x%X" % PHASE_DONE)
             .insn("POP", "{R1, R2, R3, R4, R5, R6, R7, PC}"))
            code = a.assemble(CAVE_AS_FOLLOW)
            assert_thumb1_only(code, CAVE_AS_FOLLOW)
            return code


        def _find_one(ov: bytes, base: int, count: int, stride: int, cid: int,
                      width: str) -> int:
            hits = [i for i in range(count)
                    if struct.unpack_from(width, ov, base + i * stride - RAM_BASE)[0] == cid]
            if len(hits) != 1:
                raise SystemExit(f"expected exactly 1 row for {cid:#06x} at {base:#010x}, "
                                 f"found {hits}")
            return hits[0]


        def _count_neutral_insert(ov: bytearray, base: int, count: int, stride: int,
                                  width: str, phantom: int, row: bytes, cid: int,
                                  label: str) -> None:
            """Drop *phantom*'s row and re-insert *row* at its sorted position.

            Both arrays are binary-searched, so the count and the sortedness are the
            invariants that matter -- neither changes here.  Idempotent.
            """
            def key(i: int) -> int:
                return struct.unpack_from(width, ov, base + i * stride - RAM_BASE)[0]

            if any(key(i) == cid for i in range(count)):
                print(f"  {label}: {cid:#06x} already present -- skipped (idempotent)")
                return
            src = _find_one(bytes(ov), base, count, stride, phantom, width)
            # where the new row belongs, once the phantom's row is gone
            dst = sum(1 for i in range(count) if i != src and key(i) < cid)
            off = base - RAM_BASE
            rows = [bytes(ov[off + i * stride: off + (i + 1) * stride]) for i in range(count)]
            rows.pop(src)
            rows.insert(dst, row)
            assert len(rows) == count, "count-neutral insert changed the row count"
            ov[off: off + count * stride] = b"".join(rows)
            keys = [struct.unpack_from(width, ov, off + i * stride)[0] for i in range(count)]
            assert all(keys[i] <= keys[i + 1] for i in range(count - 1)), \
                f"{label}: array is no longer sorted after the insert"
            print(f"  {label}: dropped phantom {phantom:#06x} at [{src}], "
                  f"inserted {cid:#06x} at [{dst}] -- {count} rows, still sorted")


        def apply_clause1(ov: bytearray) -> None:
            """PARTS F + G -- the cls3 record and the criteria row.  No code, no cave."""
            rec = struct.pack("<I", DONOR_CID) + struct.pack("<5I", *CLS3_SLOTS)
            assert len(rec) == CLS3_STRIDE
            _count_neutral_insert(ov, CLS3_BASE, CLS3_COUNT, CLS3_STRIDE, "<I",
                                  CLS3_PHANTOM, rec, DONOR_CID, "F cls3")
            row = struct.pack(CRIT_FMT, *CRIT_ROW)
            assert len(row) == CRIT_STRIDE
            _count_neutral_insert(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, "<H",
                                  CRIT_PHANTOM, row, DONOR_CID, "G criteria")


        def apply_clause3_rows(ov: bytearray) -> None:
            """PARTS J + K -- merge clause 3 into the cls3 record, and add its criteria row.

            J rewrites cls3[50]'s three contended slots to the ov5 splitters.  K inserts the
            SECOND criteria row immediately AFTER clause 1's, which is mandatory: the row
            resolver walks to the LEFTMOST row for the cid and adds an offset, so "after"
            is what makes clause 1 row 0 and clause 3 row 1
            (otn-param-provider-internal-hook).  Reaching row 1 at all needs the
            criteria_row_hook arm -- see that module.
            """
            i = _find_one(bytes(ov), CLS3_BASE, CLS3_COUNT, CLS3_STRIDE, DONOR_CID, "<I")
            rec = CLS3_BASE + i * CLS3_STRIDE
            cur = tuple(struct.unpack_from("<I", ov, rec - RAM_BASE + k)[0]
                        for k in (4, 8, 0xC, 0x10, 0x14))
            if cur == CLS3_SLOTS_MERGED:
                print(f"  J: cls3[{i}] already merged -- skipped (idempotent)")
            elif cur != CLS3_SLOTS:
                raise SystemExit(f"J: cls3[{i}] is neither clause-1-only nor merged: "
                                 f"{tuple(hex(x) for x in cur)}")
            else:
                for k, v in zip((4, 8, 0xC, 0x10, 0x14), CLS3_SLOTS_MERGED):
                    struct.pack_into("<I", ov, rec - RAM_BASE + k, v)
                print(f"  J: cls3[{i}] slots -> splitters "
                      f"{' '.join(f'{x:#010x}' for x in CLS3_SLOTS_MERGED)} "
                      f"(resolver / condition / cost split on whose turn it is)")

            cids = [struct.unpack_from("<H", ov, CRIT_BASE - RAM_BASE + k * CRIT_STRIDE)[0]
                    for k in range(CRIT_COUNT)]
            if cids.count(DONOR_CID) == 2:
                print("  K: clause-3 criteria row already present -- skipped (idempotent)")
                return
            if cids.count(DONOR_CID) != 1:
                raise SystemExit(f"K: expected clause 1's single criteria row, found "
                                 f"{cids.count(DONOR_CID)}")
            src = _find_one(bytes(ov), CRIT_BASE, CRIT_COUNT, CRIT_STRIDE,
                            CRIT_PHANTOM_QE, "<H")
            dst = cids.index(DONOR_CID) + 1          # immediately AFTER clause 1's row
            if src < dst:
                dst -= 1                             # removing the phantom shifts the target
            off = CRIT_BASE - RAM_BASE
            rows = [bytes(ov[off + k * CRIT_STRIDE: off + (k + 1) * CRIT_STRIDE])
                    for k in range(CRIT_COUNT)]
            rows.pop(src)
            rows.insert(dst, struct.pack(CRIT_FMT, *CRIT_ROW_QE))
            assert len(rows) == CRIT_COUNT, "K: count-neutral insert changed the row count"
            ov[off: off + CRIT_COUNT * CRIT_STRIDE] = b"".join(rows)
            keys = [struct.unpack_from("<H", ov, off + k * CRIT_STRIDE)[0]
                    for k in range(CRIT_COUNT)]
            assert all(keys[k] <= keys[k + 1] for k in range(CRIT_COUNT - 1)), \
                "K: criteria registry is no longer sorted"
            print(f"  K: dropped phantom {CRIT_PHANTOM_QE:#06x} at [{src}], inserted clause-3 "
                  f"row at [{dst}] (row 1 of this cid) -- {CRIT_COUNT} rows, still sorted")


        def apply_quickeffect(rom) -> None:
            """PART L -- ARM9 spell-speed-2 list membership.

            Without it the opponent's-turn responder never polls slot 3 at all
            (dispatch.responder_spell_speed_gate), so clause 3 would simply never be offered.
            Base and count are read from the CODE, never hardcoded
            (setcode.slot_addresses_are_not_stable).
            """
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)
            base, n, lst = steam._read_thunk_list(bytes(d), QUICKEFFECT_POOL,
                                                  QUICKEFFECT_COUNT_IMM, QUICKEFFECT_LIST,
                                                  "spell-speed-2 list")
            if DONOR_CID in lst:
                print(f"  L: spell-speed-2 list already holds {DONOR_CID:#06x} -- skipped")
                return
            # self-identification: prove this is the QUICK EFFECT list and not another cid list
            assert 0x17C2 in lst and 0x0FE0 in lst and 0x1B44 in lst, (
                "L: Blue-Eyes Shining Dragon / Kuriboh / D.D. Crow missing -- wrong list or "
                "wrong base ROM")
            out = steam._swap_in_list(lst, QUICKEFFECT_DROP, DONOR_CID, "spell-speed-2 list")
            struct.pack_into(f"<{n}H", d, base - 0x02000000, *out)
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            print(f"  L: spell-speed-2 list @{base:#010x}: dropped phantom "
                  f"{QUICKEFFECT_DROP:#06x}, inserted {DONOR_CID:#06x} at index "
                  f"{out.index(DONOR_CID)} -- count {n}, still strictly sorted")


        def install_clause3_caves(rom) -> None:
            """PART M -- the three cls3 slot splitters."""
            for name, blob, addr in (
                ("AS_RES", _build_res(), ov5_cave.CAVE_AS_RES),
                ("AS_COND", _build_cond(), ov5_cave.CAVE_AS_COND),
                ("AS_COST", _build_cost(), ov5_cave.CAVE_AS_COST),
            ):
                try:
                    ov5_cave.install_cave(rom, addr, blob, reserve=0x40)
                    print(f"  M: {name:8s} -> {addr:#010x}  {len(blob)} B")
                except AssertionError as exc:
                    if "not free" not in str(exc):
                        raise
                    if ov5_cave.read_cave(rom, addr, len(blob)) != blob:
                        raise
                    print(f"  M: {name:8s} already installed at {addr:#010x} -- skipped")


        def install_clause2_caves(rom) -> None:
            """PART I -- the phase-0x7C body, plus the SHARED dispatcher it hangs off."""
            for name, blob, addr, reserve in (
                ("AS_FOLLOW", _build_follow(), CAVE_AS_FOLLOW, 0x100),
                ("LATCH", b"\x00" * 8, CAVE_AS_LATCH, 0x8),
                ("HOOK", deck_send_follow_hook.build_dispatcher(),
                 ov5_cave.CAVE_FOLLOWHOOK, 0x80),
            ):
                try:
                    ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                    print(f"  I: {name:9s} -> {addr:#010x}  {len(blob)} B")
                except AssertionError as exc:
                    if "not free" not in str(exc):
                        raise
                    if ov5_cave.read_cave(rom, addr, len(blob)) != blob:
                        raise
                    print(f"  I: {name:9s} already installed at {addr:#010x} -- skipped")


        def apply_fusion_recipe_kill(ov: bytearray) -> None:
            """Blank the donor's fusion recipe materials.  Count-neutral, idempotent."""
            off = FUSION_ROW_ADDR - RAM_BASE
            result, m1, m2, m3 = struct.unpack_from("<4H", ov, off)
            assert result == DONOR_CID, (
                f"fusion table A row {FUSION_ROW} @0x{FUSION_ROW_ADDR:08X} holds result "
                f"0x{result:04X}, expected the donor 0x{DONOR_CID:04X} -- refusing to "
                f"patch a moved table")
            if (m1, m2) == (FUSION_DEAD_MATERIAL, FUSION_DEAD_MATERIAL):
                print(f"D  fusion recipe row {FUSION_ROW} already neutralised -> no change")
                return
            assert (m1, m2, m3) == (FUSION_STOCK_M1, FUSION_STOCK_M2, 0), (
                f"fusion row {FUSION_ROW} materials are (0x{m1:04X}, 0x{m2:04X}, 0x{m3:04X}), "
                f"expected the stock (0x{FUSION_STOCK_M1:04X}, 0x{FUSION_STOCK_M2:04X}, 0) "
                f"-- someone else claimed this row")
            struct.pack_into("<2H", ov, off + 2, FUSION_DEAD_MATERIAL, FUSION_DEAD_MATERIAL)
            print(f"D  fusion recipe A[{FUSION_ROW}] @0x{FUSION_ROW_ADDR:08X}: materials "
                  f"0x{m1:04X}/0x{m2:04X} -> 0x{FUSION_DEAD_MATERIAL:04X}/"
                  f"0x{FUSION_DEAD_MATERIAL:04X}  => the row can never be satisfied, so the "
                  f"ungated AI planner 0x022112B2 cannot Fusion Summon the converted card")


        # ===========================================================================
        # PARTS A1 + B -- bin2.pac, both records written IN PLACE (same size, no rebuild)
        # ===========================================================================


        def _record_offsets(pac: bytes, archive):
            """-> (card_prop record offset, card_genre record offset, card index)."""
            cpf = next((f for f in archive.files
                        if f.get_clean_name().lower() == "card_prop.bin"), None)
            gnf = next((f for f in archive.files
                        if f.get_clean_name().lower() == "card_genre.bin"), None)
            if cpf is None or gnf is None:
                raise RuntimeError("card_prop.bin / card_genre.bin not found in bin2.pac")
            n_prop = (cpf.size - 8) // 8
            n_genre = (gnf.size - 8) // 8
            assert n_prop == n_genre == 4305, (
                f"card_prop has {n_prop} records and card_genre {n_genre}; they must be "
                f"4305 and parallel for the shared index to be valid")
            for i in range(n_prop):
                off = cpf.address + 8 + i * 8
                if (int.from_bytes(pac[off:off + 8], "little") & 0x3FFF) == DONOR_CID:
                    return off, gnf.address + 8 + i * 8, i
            raise RuntimeError(f"cid 0x{DONOR_CID:04X} not found in card_prop.bin")


        def apply_card_prop_and_genre(out_path: str) -> None:
            """A1: copy Formula Synchron's whole card_prop record (cid swapped).
            B:  rewrite the card_genre record's category tags.

            Both are same-size in-place writes, so bin2.pac is NOT rebuilt here -- the
            text pass (PART C) is what rebuilds it, and it re-reads the archive from the
            ROM we save, so these edits carry through.
            """
            rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
            fid, orig, archive = _find_pac(rom)
            pac = bytearray(orig)

            prop_off, genre_off, idx = _record_offsets(bytes(pac), archive)

            # -- A1: the reference-record copy -------------------------------------
            cpf = next(f for f in archive.files
                       if f.get_clean_name().lower() == "card_prop.bin")
            ref_off = None
            for i in range((cpf.size - 8) // 8):
                o = cpf.address + 8 + i * 8
                if (int.from_bytes(pac[o:o + 8], "little") & 0x3FFF) == REFERENCE_SYNCHRO_TUNER_CID:
                    ref_off = o
                    break
            if ref_off is None:
                raise RuntimeError(
                    f"reference cid 0x{REFERENCE_SYNCHRO_TUNER_CID:04X} (Formula Synchron) "
                    f"not found in card_prop.bin")
            ref = int.from_bytes(pac[ref_off:ref_off + 8], "little")
            ref_type = (ref >> 32) & 0x3F
            assert ref_type == NEW_CARD_TYPE, (
                f"reference card 0x{REFERENCE_SYNCHRO_TUNER_CID:04X} has card_type "
                f"{ref_type}, expected {NEW_CARD_TYPE} (Synchro Tuner Effect Monster)")

            cur = int.from_bytes(pac[prop_off:prop_off + 8], "little")
            want = (ref & ~0x3FFF) | DONOR_CID
            if ((cur >> 32) & 0x3F) == NEW_CARD_TYPE:
                print(f"A1 card_prop[0x{DONOR_CID:04X}] already card_type {NEW_CARD_TYPE} "
                      f"-> no template copy")
            else:
                pac[prop_off:prop_off + 8] = want.to_bytes(8, "little")
                print(f"A1 card_prop[0x{DONOR_CID:04X}] idx {idx}: 0x{cur:016X} -> "
                      f"0x{want:016X}  (Formula Synchron 0x{REFERENCE_SYNCHRO_TUNER_CID:04X} "
                      f"template, cid swapped; the stat fields follow in PART A2)")

            # -- B: the genre category tags ----------------------------------------
            g_cur = int.from_bytes(pac[genre_off:genre_off + 8], "little")
            if g_cur == NEW_GENRE:
                print(f"B  card_genre[{idx}] already 0x{NEW_GENRE:016X} -> no change")
            else:
                assert g_cur in (DONOR_GENRE_STOCK, NEW_GENRE), (
                    f"card_genre[{idx}] is 0x{g_cur:016X}, expected the stock effectless-"
                    f"Fusion value 0x{DONOR_GENRE_STOCK:016X} -- someone else claimed it")
                pac[genre_off:genre_off + 8] = NEW_GENRE.to_bytes(8, "little")
                print(f"B  card_genre[{idx}]: 0x{g_cur:016X} -> 0x{NEW_GENRE:016X}  "
                      f"(clear bit {GENRE_BIT_FUSION} FUSION, set bit {GENRE_BIT_TUNER} TUNER "
                      f"+ bit {GENRE_BIT_SYNCHRO} SYNCHRO, keep bit {GENRE_BIT_NOMI} nomi)")

            assert len(pac) == len(orig), "bin2.pac changed size -- these edits must be in place"
            rom.files[fid] = bytes(pac)
            rom.saveToFile(out_path)

        def install(rom, view):
            ov = view.buf
            apply_fusion_recipe_kill(ov)                    # PART D
            apply_clause1(ov)                               # PARTS F + G  (clause 1, data)
            print("  H: shared phase-0x7C hook --")
            deck_send_follow_hook.apply_gate(ov)            # PART H  (clause 2, shared site)
            install_clause2_caves(rom)                      # PART I  (ov5, before the save)
            apply_clause3_rows(ov)                          # PARTS J + K  (clause 3)
            print("  N: shared criteria-row hook --")
            criteria_row_hook.apply(ov)                     # PART N  (clause 3 reaches row 1)
            criteria_row_hook.install(rom)                  # its stub, in the ov5 cave
            install_clause3_caves(rom)                      # PART M
            apply_quickeffect(rom)                          # PART L  (ARM9)

        def add_synchron_member(out_path):
            # PART E -- the "Synchron" set-code slot the user assigned (asserts the pool word, count immediate and sortedness itself)
            unksyn.add_synchron_member(out_path, DONOR_CID, SYNCHRON_DROP_CID)

        def check_fn(c, rom, view):
            ov = bytearray(view.buf)

            def check(cond: bool, msg: str) -> None:
                c.ok(bool(cond), msg)

            # -- D: the fusion recipe row ------------------------------------------
            off = FUSION_ROW_ADDR - RAM_BASE
            result, m1, m2, m3 = struct.unpack_from("<4H", ov, off)
            check(result == DONOR_CID,
                  f"D fusion A[{FUSION_ROW}] result cid is still 0x{DONOR_CID:04X} "
                  f"(got 0x{result:04X})")
            check(m1 == FUSION_DEAD_MATERIAL and m2 == FUSION_DEAD_MATERIAL,
                  f"D fusion A[{FUSION_ROW}] materials blanked to "
                  f"0x{FUSION_DEAD_MATERIAL:04X}/0x{FUSION_DEAD_MATERIAL:04X} "
                  f"(got 0x{m1:04X}/0x{m2:04X})")
            cids = [struct.unpack_from("<H", ov, FUSION_TABLE_A - RAM_BASE + i * 8)[0]
                    for i in range(FUSION_ROW_COUNT)]
            check(all(cids[i] < cids[i + 1] for i in range(FUSION_ROW_COUNT - 1)),
                  f"D fusion table A cid column is still a strictly sorted "
                  f"{FUSION_ROW_COUNT}-row set (the binary search depends on it)")

            # -- the summon procedure comes from ABSENCE, so assert the absences -----
            list_a = list(struct.unpack_from(f"<{LIST_A_COUNT}H", ov, LIST_A - RAM_BASE))
            check(DONOR_CID not in list_a,
                  f"donor is ABSENT from LIST_A @0x{LIST_A:08X} -- absence is what unlocks "
                  f'the printed "1+ non-Tuner" form (synchro.list_a)')
            min3 = list(struct.unpack_from(f"<{MIN3_LIST_COUNT}H", ov, MIN3_LIST - RAM_BASE))
            check(DONOR_CID not in min3,
                  f"donor is ABSENT from the min-3-materials list @0x{MIN3_LIST:08X} "
                  f"-> minimum 2 materials")
            check(DONOR_CID not in TUNER2_CIDS,
                  f"donor is not one of the two 2-leading-Tuner cids -> 1 Tuner")

            # -- C: the "Synchron" set-code table ----------------------------------
            import ndspy.code
            r = rom
            mc = ndspy.code.MainCodeFile(r.arm9, r.arm9RamAddress)
            sec = next(s for s in mc.sections
                       if s.ramAddress <= unksyn.SYNCHRON_TBL < s.ramAddress + len(s.data))
            d = bytes(sec.data)
            base = sec.ramAddress
            tbl = list(struct.unpack_from(f"<{unksyn.SYNCHRON_COUNT}H", d,
                                          unksyn.SYNCHRON_TBL - base))
            imm = struct.unpack_from("<H", d, unksyn.SYNCHRON_COUNT_IMM - base)[0]
            ptr = struct.unpack_from("<I", d, unksyn.SYNCHRON_POOL_PTR - base)[0]
            check(DONOR_CID in tbl, f'E donor 0x{DONOR_CID:04X} is a "Synchron" member')
            check(SYNCHRON_DROP_CID not in tbl,
                  f"E 0x{SYNCHRON_DROP_CID:04X} (Speed Spell - Deceased Synchron) was dropped")
            check(len(tbl) == unksyn.SYNCHRON_COUNT
                  and all(tbl[i] < tbl[i + 1] for i in range(len(tbl) - 1)),
                  f"E Synchron list is still a sorted {unksyn.SYNCHRON_COUNT}-entry set")
            check(imm == (0x2200 | unksyn.SYNCHRON_COUNT),
                  f"E count immediate @0x{unksyn.SYNCHRON_COUNT_IMM:08X} is still "
                  f"movs r2,#0x{unksyn.SYNCHRON_COUNT:02X}")
            check(ptr == unksyn.SYNCHRON_TBL,
                  f"E consumer pool @0x{unksyn.SYNCHRON_POOL_PTR:08X} still points at the list")

            # -- A + B: card_prop and card_genre -----------------------------------
            fid, pac, archive = _find_pac(r)
            prop_off, genre_off, idx = _record_offsets(pac, archive)
            rec = pac[prop_off:prop_off + 8]
            f = GC.decode_entry(rec)
            check((int.from_bytes(rec, "little") & 0x3FFF) == DONOR_CID,
                  f"A card_prop cid is still 0x{DONOR_CID:04X} (keep-cid rule)")
            check(f["card_type_encoded"] == NEW_CARD_TYPE,
                  f"A card_prop card_type == {NEW_CARD_TYPE} Synchro Tuner Effect Monster "
                  f"(got {f['card_type_encoded']} {f['card_type']})")
            check(f["level"] == NEW_LEVEL,
                  f"A card_prop level == {NEW_LEVEL} (got {f['level']}) -- LIVE, "
                  f"can_synchro_summon reads it")
            check(f["attribute"] == NEW_ATTRIBUTE,
                  f"A card_prop attribute == {NEW_ATTRIBUTE} (got {f['attribute']})")
            check(f["race"] == NEW_RACE, f"A card_prop race == {NEW_RACE} (got {f['race']})")
            check(f["real_atk"] == NEW_ATK, f"A card_prop ATK == {NEW_ATK} (got {f['real_atk']})")
            check(f["real_def"] == NEW_DEF, f"A card_prop DEF == {NEW_DEF} (got {f['real_def']})")

            # the reference-record copy: every bit outside cid + the fields we set must
            # match Formula Synchron, so no Fusion-flavoured bit survives.
            cpf = next(x for x in archive.files
                       if x.get_clean_name().lower() == "card_prop.bin")
            ref = None
            for i in range((cpf.size - 8) // 8):
                o = cpf.address + 8 + i * 8
                v = int.from_bytes(pac[o:o + 8], "little")
                if (v & 0x3FFF) == REFERENCE_SYNCHRO_TUNER_CID:
                    ref = v
                    break
            got = int.from_bytes(rec, "little")
            # cid[0:14] atk[14:23] def[23:32] card_type[32:38] attribute[38:41]
            # monster flag[41] level[42:46] spell_trap_subtype[46:49] race[49:54]
            set_mask = ((1 << 14) - 1) | (((1 << 18) - 1) << 14) | (((1 << 3) - 1) << 38) \
                | (((1 << 4) - 1) << 42) | (((1 << 5) - 1) << 49)
            check(ref is not None and (got & ~set_mask) == (ref & ~set_mask),
                  f"A every card_prop bit outside cid/atk/def/attribute/level/race matches "
                  f"the Formula Synchron template (no Fusion-flavoured bit survives)")

            g = int.from_bytes(pac[genre_off:genre_off + 8], "little")
            check(g in pcg.accepted(DONOR_CID, NEW_GENRE),
                  f"B card_genre[{idx}] == 0x{NEW_GENRE:016X} (got 0x{g:016X})")
            check(not (g >> GENRE_BIT_FUSION) & 1,
                  f"B card_genre FUSION tag (bit {GENRE_BIT_FUSION}) is CLEAR")
            check((g >> GENRE_BIT_SYNCHRO) & 1,
                  f"B card_genre SYNCHRO tag (bit {GENRE_BIT_SYNCHRO}) is SET")
            check((g >> GENRE_BIT_TUNER) & 1,
                  f"B card_genre TUNER tag (bit {GENRE_BIT_TUNER}) is SET")
            check((g >> GENRE_BIT_NOMI) & 1,
                  f"B card_genre nomi tag (bit {GENRE_BIT_NOMI}) is still SET")

            # -- F + G: clause 1, the two count-neutral row inserts -----------------
            c3_cids = [struct.unpack_from("<I", ov, CLS3_BASE - RAM_BASE + i * CLS3_STRIDE)[0]
                       for i in range(CLS3_COUNT)]
            check(c3_cids.count(DONOR_CID) == 1,
                  f"F cls3 holds EXACTLY ONE record for 0x{DONOR_CID:04X} "
                  f"(got {c3_cids.count(DONOR_CID)}) -- 2 would shadow via "
                  f"find_event_handler's leftmost-equal walk")
            check(CLS3_PHANTOM not in c3_cids,
                  f"F phantom 0x{CLS3_PHANTOM:04X} was dropped (count-neutral)")
            check(all(c3_cids[i] <= c3_cids[i + 1] for i in range(CLS3_COUNT - 1)),
                  f"F cls3 is still sorted over {CLS3_COUNT} rows (binary-search precondition)")
            i3 = c3_cids.index(DONOR_CID)
            # The record's slots are the clause-3 SPLITTERS (checked under J); what F owns is
            # that clause 1's three Darklord Asmodeus callbacks are still what those
            # splitters route to on OUR turn.
            for nm1, blob1, want1 in (("resolver", _build_res(), DECK_SEND_RESOLVER),
                                      ("condition", _build_cond(), IGNITION_ONCE_COND),
                                      ("cost", _build_cost(), IGNITION_ONCE_COST)):
                check(struct.pack("<I", want1) in blob1,
                      f"F clause-1 {nm1} 0x{want1:08X} (Darklord Asmodeus's) is still the "
                      f"our-turn target of the splitter")

            cr_cids = [struct.unpack_from("<H", ov, CRIT_BASE - RAM_BASE + i * CRIT_STRIDE)[0]
                       for i in range(CRIT_COUNT)]
            check(cr_cids.count(DONOR_CID) == 2,
                  f"G/K criteria registry holds EXACTLY TWO rows for 0x{DONOR_CID:04X} "
                  f"(clause 1 + clause 3); got {cr_cids.count(DONOR_CID)}")
            check(CRIT_PHANTOM not in cr_cids and CRIT_PHANTOM_QE not in cr_cids,
                  f"G/K phantoms 0x{CRIT_PHANTOM:04X} and 0x{CRIT_PHANTOM_QE:04X} were "
                  f"dropped (both count-neutral)")
            check(all(cr_cids[i] <= cr_cids[i + 1] for i in range(CRIT_COUNT - 1)),
                  f"G criteria registry is still sorted over {CRIT_COUNT} rows")
            ic = cr_cids.index(DONOR_CID)
            check(cr_cids[ic + 1] == DONOR_CID,
                  "K the two rows are ADJACENT -- the row resolver walks to the LEFTMOST and "
                  "adds an offset, so a gap would make row 1 unreachable")
            got_row = struct.unpack_from(CRIT_FMT, ov, CRIT_BASE - RAM_BASE + ic * CRIT_STRIDE)
            check(got_row == CRIT_ROW,
                  f"G criteria ROW 0 [{ic}] == {{cid, aux 0x{SYNCHRON_SET_CODE:04X}, "
                  f"0x{DECK_SETCODE_HANDLER:08X} (aux-AWARE deck), 0x{CRIT_WORD_MONSTER:08X}}}; "
                  f"got {tuple(hex(x) for x in got_row)}")
            check(got_row[2] != 0x0223CAD9,
                  "G handler is NOT 0x0223CAD9 -- that one ignores the aux, so the "
                  '"Synchron" filter would be silently dropped')
            qe_row = struct.unpack_from(CRIT_FMT, ov,
                                        CRIT_BASE - RAM_BASE + (ic + 1) * CRIT_STRIDE)
            check(qe_row == CRIT_ROW_QE,
                  f"K criteria ROW 1 [{ic + 1}] == Formula's {{aux 0xFFFF, "
                  f"0x{QE_CRIT_HANDLER:08X}, 0x{QE_CRIT_FLAGS:04X}}}; "
                  f"got {tuple(hex(x) for x in qe_row)}")

            # -- J + M + N: clause 3's merged record, splitters and shared row hook ----
            slots_now = tuple(struct.unpack_from("<I", ov,
                                                 CLS3_BASE - RAM_BASE + i3 * CLS3_STRIDE + k)[0]
                              for k in (4, 8, 0xC, 0x10, 0x14))
            check(slots_now == CLS3_SLOTS_MERGED,
                  f"J cls3[{i3}] slots are the three turn splitters "
                  f"{' '.join(f'{x:#010x}' for x in CLS3_SLOTS_MERGED)}; got "
                  f"{' '.join(f'{x:#010x}' for x in slots_now)}")
            check(c3_cids.count(DONOR_CID) == 1,
                  "J still exactly ONE cls3 record -- a second would be shadowed by "
                  "find_event_handler's leftmost-equal walk (the Warwolf bug)")
            check(any(c == DONOR_CID for c, _t, _s, _d in criteria_row_hook.ARMS),
                  f"N 0x{DONOR_CID:04X} is a registered arm of criteria_row_hook, without "
                  f"which the row resolver forces r4 = 0 and row 1 is unreachable")
            try:
                romv3 = rom
                for nm3, blob, addr in (("M AS_RES", _build_res(), ov5_cave.CAVE_AS_RES),
                                        ("M AS_COND", _build_cond(), ov5_cave.CAVE_AS_COND),
                                        ("M AS_COST", _build_cost(), ov5_cave.CAVE_AS_COST)):
                    check(ov5_cave.read_cave(romv3, addr, len(blob)) == blob,
                          f"{nm3} @0x{addr:08X} {len(blob)} B matches the emitted splitter")
                import ndspy.code
                mcv = ndspy.code.MainCodeFile(romv3.arm9, romv3.arm9RamAddress)
                secv = next(s for s in mcv.sections
                            if s.ramAddress <= QUICKEFFECT_LIST < s.ramAddress + len(s.data))
                dv = bytes(secv.data)
                nv = struct.unpack_from("<H", dv, QUICKEFFECT_COUNT_IMM - secv.ramAddress)[0] & 0xFF
                qlist = list(struct.unpack_from(f"<{nv}H", dv,
                                                QUICKEFFECT_LIST - secv.ramAddress))
                check(DONOR_CID in qlist,
                      f"L donor is in the ARM9 spell-speed-2 list (without it the "
                      f"opponent's-turn responder never polls slot 3)")
                check(QUICKEFFECT_DROP not in qlist,
                      f"L phantom 0x{QUICKEFFECT_DROP:04X} was dropped (count-neutral)")
                check(len(qlist) == nv and all(qlist[i] < qlist[i + 1] for i in range(nv - 1)),
                      f"L spell-speed-2 list is still a strictly sorted {nv}-entry set")
            except Exception as exc:                       # pragma: no cover
                check(False, f"J/L/M read failed: {exc}")

            # -- H + I: clause 2, the shared hook and the cave --------------------
            check(deck_send_follow_hook.verify_gate(ov),
                  f"H phase-0x7C gate @0x{deck_send_follow_hook.GATE_ADDR:08X} -> shared "
                  f"CAVE_FOLLOWHOOK")
            check(any(c == DONOR_CID for c, _b, _o in deck_send_follow_hook.ARMS),
                  f"H 0x{DONOR_CID:04X} is a registered arm of deck_send_follow_hook")
            try:
                romv = rom
                for nm2, blob, addr in (
                    ("I AS_FOLLOW", _build_follow(), CAVE_AS_FOLLOW),
                    ("I HOOK", deck_send_follow_hook.build_dispatcher(),
                     ov5_cave.CAVE_FOLLOWHOOK),
                ):
                    check(ov5_cave.read_cave(romv, addr, len(blob)) == blob,
                          f"{nm2} @0x{addr:08X} {len(blob)} B matches the emitted stub")
                # the regression guard for the in-game failure: the rider key
                # must be the SELECTOR 0x22EB, never this card's own cid.
                follow = _build_follow()
                check(struct.pack("<I", RIDER_KEY) in follow,
                      f"I clause-2 stub's literal pool carries the rider SELECTOR "
                      f"0x{RIDER_KEY:04X} (Egotistical Ape) as the node key")
                check(struct.pack("<I", DONOR_CID) not in follow,
                      f"I clause-2 stub does NOT use the donor cid 0x{DONOR_CID:04X} as the "
                      f"rider key -- the Level getter ignores unlisted keys (in-game 2026-09-04)")
            except Exception as exc:                       # pragma: no cover
                check(False, f"I cave read failed: {exc}")

        return Compiled(installs=(install,), posts=(apply_card_prop_and_genre, add_synchron_member), checks=(check_fn,))


accel_effects = synchro_tuner_one_tuner_and_non_tuners_send_synchron_from_deck_to_graveyard_raise_or_lower_level_quick_effect_synchro_summon

SPEC = card(0x11A3, accel_effects())

PROPS = card_props("DARK", "Machine", level=5, atk=500, defense=2100, card_type="Synchro Tuner Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_accel.nds")

DONOR_CID = 0x11A3          # Bracchio-raidus
REFERENCE_SYNCHRO_TUNER_CID = 0x239E     # Formula Synchron, the card_prop template
NEW_CARD_TYPE = 39                       # Synchro Tuner Effect Monster
NEW_GENRE = 0x0000001800200000           # nomi + TUNER + SYNCHRO
FUSION_ROW_ADDR = 0x02270CC4             # fusion table A row 38
FUSION_DEAD_MATERIAL = 0x3FFF
SYNCHRON_DROP_CID = 0x0D6B               # Speed Spell - Deceased Synchron

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
