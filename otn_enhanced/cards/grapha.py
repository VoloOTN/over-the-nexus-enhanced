"""Grapha, Dragon Lord of Dark World (DARK / Fiend / Effect Monster / Level 8 / 2700 / 1800) on Zure, Knight of Dark World 0x1961.

    You can Special Summon this card (from your Graveyard) by returning 1 "Dark World" monster you control to the hand, except "Grapha, Dragon
    Lord of Dark World". (See card_text.CARD_TEXT[0x1961] for the full printed text.)
"""
from __future__ import annotations

import struct
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, RES_RESERVE, SRC
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class graveyard_special_summon_by_returning_dark_world_monster_to_hand_discard_trigger_destroy_opponent_card_then_look_at_random_hand_card:
    """Grapha, Dragon Lord of Dark World (Zure, Knight of Dark World 0x1961, DARK / Fiend / Level 8 / 2700 / 1800): 'You can Special Summon this
    card (from your Graveyard) by returning 1 "Dark World" monster you control to the hand, except "Grapha, Dragon Lord of Dark World".' (clause 1,
    the GY-action registry row over phantom 0x0EB2 + the cls2 record over phantom 0x1A86 whose five slots are ov5 dispatchers: Zephyros's bounce
    cost, a resolver without his 400 damage, a Dark-World-monster filter, a free-zone-bypassing gate) plus the discard trigger (clause 2: destroy
    1 card the opponent controls, via the PART H switch-node stub in ov3 dead space) and clause 3 (the shared look-at-a-random-hand-card halves
    that conscription_c3 also names). Original code embedded verbatim; the import-time snoww switch-stub registration moves to __post_init__.
    The card_prop rewrite and name/description now come from dsl.make (the legacy in-place text writer is dropped: the card is in CARD_TEXT)."""

    def __post_init__(self):
        from otn_enhanced.cards import snoww as _s
        _s.register_switch_stub(0x021B594A, 16, {0x1961: 0x021D185C})   # ARM_STUB, ARM_STUB_LEN, {DONOR_CID: DW_ARM}

    def compile(self, view, cid) -> Compiled:
        import struct
        import ndspy.rom
        from otn_enhanced.asm import effect_verify
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.cards import snoww as _snoww
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.rom.pac import parse_pac
        from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
        from otn_enhanced.data import card_text as _card_text
        from otn_enhanced.asm.effect_builder import EffectBuilder, Reg, R0, R1, R2, R3, R4, R5, R6, R7
        from otn_enhanced.effects.common import ov3_off as _off

        SRC = "data/over_the_nexus/working/rom.nds"            # clean (AP-fixed) EU base ROM
        OUT = "data/over_the_nexus/working/rom_grapha.nds"     # single-card test ROM

        DONOR_CID = 0x1961          # Zure, Knight of Dark World (keep-cid rule)
        TEMPLATE_CID = 0x241C       # Blackwing - Zephyrus the Elite -- asserted, never written

        from otn_enhanced.effects.common import ARM9_BASE
        # ARM9 "Dark World" set-code list -- ASSERTED, never written.  Set code 0x0F,
        # thunk 0x020238B5 (pointer table 0x0209D0D8 index 0x0F), 16 sorted entries.
        DW_LIST, DW_LIST_COUNT = 0x0209CA06, 16
        DW_THUNK_SLOT = 0x0209D0D8 + 0x0F * 4
        DW_THUNK = 0x020238B5

        # ---------------------------------------------------------------------------
        # PART C -- the GY-action registry row
        # ---------------------------------------------------------------------------
        # 0x0228DDF8, 60 rows x 0x10 B: {u32 cid, u32 zone, u32 check_fn, u32 post_fn}.
        # UNSORTED and linear-scanned with a hard-coded `cmp rX,#0x3C`, so a row is
        # claimed IN PLACE -- no shifting, inherently count-neutral.
        GYACT_BASE, GYACT_COUNT, GYACT_STRIDE = 0x0228DDF8, 0x3C, 0x10
        GYACT_ZONE_GY = 0x0E
        GYACT_CHECK, GYACT_POST = 0x0224C591, 0x0224C6C1     # the 45-row GY-EFFECT family
        # Row 15 already carries EXACTLY the shape we need with a phantom cid: 0x0EB2 has
        # no card_prop record, so its membership is inert and no card can ever reach it.
        GYACT_ROW = 15
        GYACT_DROP_PHANTOM = 0x0EB2

        # ---------------------------------------------------------------------------
        # PART D -- the cls2 record
        # ---------------------------------------------------------------------------
        CLS2_BASE, CLS2_COUNT, CLS2_STRIDE = 0x02275C04, 0x2B9, 0x18
        ZEPH_RESOLVER = 0x02230EBD    # +04 -- ⚠️ NOT reusable, see THE 400-DAMAGE TRAP; asserted
                                      #     intact so Zephyros keeps his own resolver
        ZEPH_COST     = 0x021EB1B1    # +10, the shared bounce-cost machine
        # Zephyrus's own record, asserted intact so a future edit to the template is loud.
        ZEPH_CLS2 = (0x241C, 0x02230EBD, 0x021E454D, 0x021F44D9, 0x021EB1B1, 0x00000000)
        # Phantom 0x1A86: no card_prop record, owns exactly ONE cls2 row (index 219), and
        # that row is its ONLY aligned occurrence anywhere in overlay 3, so dropping it
        # cannot disturb anything.  It is the nearest unclaimed phantom to the donor's
        # insert point.  Registered in check_allocations.PHANTOM_CLAIMS as cls2_table.
        CLS2_DROP_PHANTOM = 0x1A86

        # ---------------------------------------------------------------------------
        # PART E/F -- the ov5 stubs
        # ---------------------------------------------------------------------------
        FILT_STUB, FILT_RESERVE = ov5_cave.CAVE_GRAPHA_FILT, 0x50
        GATE_STUB, GATE_RESERVE = ov5_cave.CAVE_GRAPHA_GATE, 0xB0
        RES_STUB,  RES_RESERVE  = ov5_cave.CAVE_GRAPHA_RES, 0x50
        # ---- CLAUSE 2 ------------------------------------------------
        DIAG_BLOCK  = ov5_cave.CAVE_GRAPHA_DIAG
        DIAG_RESERVE = 0x40
        DECL_STUB, DECL_RESERVE = ov5_cave.CAVE_GRAPHA_DECL, 0x40
        RES2_STUB, RES2_RESERVE = ov5_cave.CAVE_GRAPHA_RES2, 0x60
        FILT2_STUB, FILT2_RESERVE = ov5_cave.CAVE_GRAPHA_FILT2, 0x50
        DIAG2_BLOCK, DIAG2_RESERVE = ov5_cave.CAVE_GRAPHA_DIAG2, 0x40
        GATE2_STUB, GATE2_RESERVE = ov5_cave.CAVE_GRAPHA_GATE2, 0x60
        COST2_STUB, COST2_RESERVE = ov5_cave.CAVE_GRAPHA_COST2, 0x40

        # *** MEASURED (round 2 savestates rom_grapha_test.ml2/.ml3, taken
        # AFTER a discard fully resolved): the resolver was NEVER entered on the discard
        # path -- "+04 entries with event != 0" == 0, and the +04/+14 counts (4 and 2) are
        # exactly two clause-1 activations at two phases each.  So clause 2 was not being
        # mis-routed; IT WAS NEVER OFFERED. ***
        #
        # dispatch.cls_slot_roles: +0C slot3 is the ACTIVATION CONDITION and returns a
        # CODE -- 0 = cannot activate, 1 = activatable if slot2 finds a target, >=2 =
        # activatable unconditionally -- and +10 slot4 is the COST / activation-procedure
        # step.  Both are driven by the activation state machine 0x02217F80, and BOTH of
        # Grapha's carry clause 1's answers: +0C is clause 1's GY-offer gate (which
        # legitimately returns 0 for a discard) and +10 is the bounce-cost machine.  That
        # is event.optional_trigger_is_record_shape's COMPOSITION TRAP, verbatim: "one cls
        # record cannot be half-optional ... must point +0C/+10 at stubs that branch on
        # the descriptor, exactly as its resolver already branches on desc[+3]".
        #
        # THE BRANCH KEY IS desc[+3], THE ZONE (the cls3 descriptor fact: [+0] cid,
        # [+2] side, [+3] zone, [+4] index, [+5] record class -- the first diagnostic
        # recorded [+4] and [+5] by mistake and got index 0 / class 2).  The discard arm
        # 0x021D185C gates on SOURCE ZONE == 0x0B (the hand), so the trigger descriptor
        # should carry 0x0B while clause 1's carries the Graveyard.
        # ⚠️ WRITTEN IN THE SAFE DIRECTION: clause 2 only when desc[+3] == 0x0B, clause 1
        # otherwise.  If the trigger descriptor turns out to carry something else, clause
        # 2 stays inert and CLAUSE 1 -- confirmed working again this round -- is untouched.
        # *** THE DISCRIMINATOR, FOUND BY DECODING THE EVENT-POST PRIMITIVE 0x021D32A0. ***
        # That function unpacks the packed event word into the 0x24-byte descriptor every
        # slot receives, and the unpacking is:
        #     strh r5,[r0]                                    desc[+0] = event & 0xFFFF (cid)
        #     movs r1,#0x1F ; lsls r1,#0x10 ; ands r1,r5
        #     lsrs r1,#0x10 ; strb r1,[r0,#3]                 desc[+3] = (event >> 16) & 0x1F
        #     movs r1,#0xE  ; lsls r1,#0x14 ; ands r1,r5
        #     lsrs r1,#0x15 ; strb r1,[r0,#5]                 desc[+5] = (event >> 21) & 0x07
        #
        # So on an EVENT-POSTED descriptor, desc[+3] and desc[+5] are NOT a zone and a
        # record class -- they are THE EVENT CODE, split across two fields (code bits 0..4
        # and 5..7).  Three earlier rounds read desc[+3] == 0x0E as "the Graveyard" and
        # built discriminators on it; it is actually the low half of code 0x4E.
        #
        # The event-post primitive has exactly FOUR call sites and their codes are
        # 0x01 (0x0224B154), 0x4B (0x0224B1BE), 0x1F (0x0224B31C) and 0x4E (0x0224C6EE,
        # THE GY-ACTION REGISTRY'S OWN post_fn = clause 1).  Their low five bits are
        # 0x01 / 0x0B / 0x1F / 0x0E -- ALL DISTINCT -- so
        #
        #     desc[+3] == 0x0E  <=>  event code 0x4E  <=>  CLAUSE 1 (the Graveyard summon)
        #
        # is a one-byte test, available from r0 in EVERY slot including the filter, which
        # receives no event and defeated every previous attempt.  It also explains the
        # round-5 bug exactly: LR == 0x0224AE13 was matching CLAUSE 1, so the gate latched
        # clause 2 for the Graveyard summon and Grapha destroyed instead of summoning.
        GY_ACTION_CODE_LOW5 = 0x0E    # 0x4E & 0x1F      -> desc[+3]
        GY_ACTION_CODE_HIGH3 = 2      # (0x4E >> 5) & 7  -> desc[+5]
        # ⚠️⚠️ ROUND 8 -- THE ABOVE TWO BYTES DO NOT DISCRIMINATE ANYTHING.
        # THE DISCARD TRIGGER POSTS EVENT CODE 0x4E TOO.  Disassembling the whole of the
        # relocation applier 0x021D1300 (the function PART H's switch lives in) down to
        # its posting site proves it end to end -- event.discard_trigger_posts_the_same_0x4E:
        #
        #   * the per-cid switch at 0x021D1392 is reached ONLY when KIND == 0x0E
        #     (`LDR R0,[SP,#0x30] ; CMP R0,#0x0E ; BEQ 0x021D1392 ; BL 0x021D1B98`, where
        #     the BL is a LONG BRANCH past the switch, not a call);
        #   * the Dark World arm 0x021D185C only sets the result flag [sp+0x14];
        #   * every arm converges on ONE post site, 0x021D1D56, which builds
        #         event = cid | (KIND << 16) | (1 << 22) | ((arg0 & 0x3F) << 25) | (side << 31)
        #     and calls the register-prim 0x021D3168.
        #
        # So the discard post carries desc[+3] = KIND = 0x0E and desc[+5] = 2 (bit 22 is
        # HARDCODED) -- i.e. 0x0E | (2 << 5) == 0x4E, byte-identical to clause 1's.  ⚠️ THIS
        # ALSO REFUTES ROUND 7's HEADLINE: reading (0x0E, 2) on every descriptor was taken
        # as proof the discard had never fired, when it is exactly what a FIRING discard
        # posts.  No refinement of a desc[+3]/desc[+5] test can work.
        #
        # ⭐ desc[+4] IS THE DISCRIMINATOR, AND IT IS FREE.  The arm demands
        # `[sp+0x18] != 0`, which means arg0 == 0x1F EXACTLY, so the discard post's
        # desc[+4] = arg0 = 0x1F.  Clause 1's post 0x0224C6EE goes through the near-twin
        # primitive 0x021D32A0, which NEVER STORES [+4] at all -- and both primitives
        # zero-fill the 0x24-byte descriptor first with 0x0209A080, a proven memset -- so
        # the GY offer's desc[+4] is 0.
        DISCARD_CODE_MID6 = 0x1F      # desc[+4] on the DISCARD post; the GY offer leaves it 0
        ALWAYS_ACTIVATABLE = 2        # what 0x0224A114 (`movs r0,#2 ; bx lr`) returns

        # The two native halves clause 2 reuses, both confirmed by the 3DS row for Grapha
        # (dispatch.threeds_discard_trigger_registry): Grapha shares its filter with Goldd
        # and its target declaration with Kahkki/Gren in the 3DS, and these are the NDS
        # counterparts of exactly those two.
        DESTROY_RES   = 0x02204899    # Kahkki/Gren cls2 +04: `bl 0x02204674 ; movs r0,#0`
        GOLDD_FILTER  = 0x021DE7C9    # Goldd cls2 +08: "cards your opponent controls",
                                      #   mask 0x00001472 (side bits 0b10, zone field 0x70)
        TARGET_DECL   = 0x02234DA5    # Kahkki/Gren cls2 +14: the shared picker, param 0x119
        # *** MEASURED, savestates rom_grapha_test.ml2/.ml3/.ml4. ***
        # The first build guessed that the GY-action path could be recognised by the 0x4E
        # event code that its post site 0x0224C6EE stamps into bits 16..23 of the event
        # word.  THAT IS WRONG, and it regressed clause 1: the diagnostic block shows the
        # resolver and the declaration are both entered with **r1 == 0x00000000** on the
        # clause-1 path (phase 0x80, [0x0229AAFC+0x74] == 0), so the 0x4E test failed and
        # both slots took the CLAUSE-2 arm -- the cost was paid and Kahkki's destroy ran
        # instead of the summon.  The event word never reaches the resolver; r1 is simply
        # 0, which matches the THREE invoker call sites that pass `movs r1,#0` literally
        # (0x0221803E, 0x02228F92, 0x0225BCF8).
        #
        # So the test is now the measured one, in the SAFE direction: clause 1 iff the
        # event is ZERO.  If the discard path also passes 0, clause 2 stays inert and
        # clause 1 -- the in-game-confirmed clause -- still works.
        GY_EVENT_IS_ZERO = True       # documentation only; the stubs compare r1 against 0
        KAHKKI_CID, GREN_CID = 0x1B3E, 0x1B3F     # asserted intact, never written

        # ---------------------------------------------------------------------------
        # CLAUSE 3 -- "...then, if this card was discarded from your hand to your
        # Graveyard by an OPPONENT's card effect, look at 1 random card in your
        # opponent's hand, then, if it was a monster, you can Special Summon it to your
        # side of the field."
        #
        # THE PAYLOAD IS NOT DUPLICATED HERE.  It lives in ov5 as two SHARED halves
        # installed by conscription_c3 -- CAVE_C3_POST and CAVE_C3_FINISH -- and is
        # IN-GAME CONFIRMED (dispatch.summon_from_opponent_hand_recipe) through
        # the Conscription test card, which drives the very same two addresses from its own
        # phase shell.  This patch supplies only the CONDITION and the phase chaining.
        #
        # THE CONDITION is dispatch.opponent_effect_discard_test, read off Sillva 0x1968's
        # resolver 0x0221FAA0 and already SHIPPED by snoww as its clause-2 slot5 gate
        #.  Both facts come out of the SAME descriptor:
        #     desc[+0x20]  the packed card word the relocation applier posted
        #     desc[+0x02]  the ACTING side
        #     bit 18 of the word MUST DIFFER from desc[+2]  -> by an OPPONENT's effect
        #     bit  9 of the word MUST EQUAL  desc[+2]       -> from YOUR hand
        # ⚠️ desc[+0x20] exists because 0x021D3168 stores its THIRD argument -- the packed
        # word itself -- there (event.discard_trigger_posts_the_same_0x4E).  An earlier pass
        # traced only the event word, concluded the acting side never reached the descriptor,
        # and called clause 3 blocked; it is not.
        #
        # THE CHAINING.  Clause 2's arm is today a single call to Kahkki/Gren's destroy
        # 0x02204899, which returns 0 = done.  Clause 3 turns that arm into a two-phase
        # machine on the SAME phase values the shared payload already uses, so no phase
        # translation is needed:
        #     phase 0x80  destroy (clause 2), then C3a; if it passes, post the pick and
        #                 return 0x7F, else return 0 exactly as before
        #     phase 0x7F  run the shared finish half, return 0
        C3_POST = ov5_cave.CAVE_C3_POST | 1       # (desc) -> 1 if the pick was posted
        C3_FINISH = ov5_cave.CAVE_C3_FINISH | 1   # (desc) -> the look-at + conditional summon
        C3_ARM, C3_ARM_RESERVE = ov5_cave.CAVE_GRAPHA_C3, 0xA0
        C3_POST_STUB, C3_POST_RESERVE = ov5_cave.CAVE_C3_POST, 0x60
        C3_FIN_STUB, C3_FIN_RESERVE = ov5_cave.CAVE_C3_FINISH, 0xE0
        C3_DIAG, C3_DIAG_RESERVE = ov5_cave.CAVE_C3_DIAG, 0x40

        # the engine entry points the two SHARED halves call.  Thumb bit set: all BLX targets.
        HAND_COUNT  = 0x0229ACA0      # == STATE_A + 0x0C, the HAND COUNT
        EFFECT_CTX  = 0x0229DE94      # shared effect-context block; +6 u16 = the chosen index
        PEEK_POST   = 0x022599F9      # (opponent, 0) -> post "look at 1 random card", kind 5
        REVEAL      = 0x021D2599      # (side, ref) -> the actual look-at
        IS_MONSTER  = 0x02029E61      # (cid) -> is this cid a monster
        MAY_SUMMON  = 0x021BA685      # ⚠️ A PREDICATE (side, cid, ref, ZONE) -> 0/1.  It summons
                                      # NOTHING; every path ends movs r0,#1 / movs r0,#0.  Calling
                                      # it as if it were the action cost one in-game test.
        SS_ALLOWED  = 0x021AD871      # (side) -> may this player SS now.  ⚠️ Returns a truthy
                                      # COUNT (measured 5), never a boolean -- test against ZERO.
        SUMMON      = 0x02269315      # THE ACTUAL SUMMON: (side, SLOT POINTER, 1, 0).  r1 is a
                                      # POINTER to the card-word slot, not a cid/ref pair.

        # ---------------------------------------------------------------------------
        # PART H -- admit the donor to the Dark World EFFECT-DISCARD arm (overlay-3)
        # ---------------------------------------------------------------------------
        # The per-cid chain 0x021D1392 routes cids to relocation arms.  Traced with a
        # register simulator: the donor 0x1961 reaches the terminal node 0x021D14E2
        # with r1 = 0x1969 and falls to the DEFAULT leaf 0x021D19C0, while the native
        # Dark World monsters reach the arm 0x021D185C.  The node is
        #     0x021D14E2  subs r1,#0x23      ; r1 = 0x1946 (Ojamagic)
        #     0x021D14E4  cmp  r5,r1
        #     0x021D14E6  bne  0x021D14EA    ; -> default
        #     0x021D14E8  b    0x021D18C4    ; Ojamagic's arm  (BRANCH TARGET, must survive)
        #     0x021D14EA  b    0x021D19C0    ; default
        # Nothing in overlay 3 branches to 0x021D14E2 or 0x021D14E4 (asserted), so those
        # two halfwords are replaced by a BL to ARM_STUB, which reproduces the node's
        # arithmetic and flags for every other cid and long-branches OUR cid into
        # 0x021D185C.  0x021D14E6/E8/EA are left untouched.
        #
        # ⚠️ THE STUB MUST LIVE IN OVERLAY 3, NOT ov5: this is a SHARED path -- every
        # effect discard of every card runs it -- and a puzzle loads overlay 41 over the
        # ov5 cave, so an ov5 target here would freeze the game (mem.ov5_ov41_share_base).
        SWITCH_HOOK = 0x021D14E2
        SWITCH_HOOK_NATIVE = bytes.fromhex("23398d42")     # subs r1,#0x23 ; cmp r5,r1
        SWITCH_R1_ON_ENTRY = 0x1969        # asserted: the node's live base register
        OJAMAGIC_CID = 0x1946              # = r1 - 0x23, the node's native occupant
        DW_ARM = 0x021D185C                # the effect-discard arm (source zone 0x0B + kind 0)
        # Two ADJACENT 8-byte ov3 dead blocks (phantom cids 0x19D1 / 0x19D3), both wholly
        # unclaimed in the ledger, giving exactly the 16 bytes needed.  Their only inbound
        # branches (0x021B4FEE -> 0x021B594A, 0x021B4FD4 -> 0x021B5952) are from those
        # phantoms' own dead arms, which is why the blocks are classified free at all --
        # the same property snoww's 0x021B56B8 relies on.
        ARM_STUB = 0x021B594A
        ARM_STUB_LEN = 16
        ARM_STUB_NATIVE = bytes.fromhex("00210398795e08e021980121084200d1")



        # engine entry points the stubs call (Thumb bit set where they are BLX targets)
        ZONE_CID      = 0x021A36ED    # (side, zone) -> cid at that zone
        HAS_DW        = 0x020238B5    # (cid) -> is this cid in the Dark World set-code list
        ZONE_PRED     = 0x021D6E41    # (src_desc, cand_side, cand_zone, mask) -> bool
        # ⚠️ Zephyros's own mask is 0x00208075, and its zone-class field (bits 4-6) is 0x70 =
        # NO ZONE RESTRICTION -- correct for him, because his printed cost is "return 1 face-up
        # CARD you control".  Grapha's is "1 'Dark World' MONSTER", and FIVE of the sixteen
        # members of the Dark World set-code list are Spells/Traps (Dark World Lightning 0x1970,
        # Gateway to Dark World 0x1973, Dark World Dealings 0x1B5A, The Gates of Dark World
        # 0x1C8B, Dark World Grimoire 0x1D25) -- so with 0x70 they would all be legal picks.
        # The field is set to 0x10 instead, Genex Ally Birdman's value, whose arm is
        # `cmp r5,#5 ; blt continue` = MONSTER ZONES ONLY (and matches the 3DS filter's own
        # `cmp r4,#4 ; bgt reject`).  Bit 21 is KEPT: its arm is the candidate-level version of
        # "the cost frees the zone it needs".
        GRAPHA_MASK   = 0x00208015
        ZEPH_MASK     = 0x00208075    # asserted intact, never written
        # the resolver's own callees, transcribed into RES_STUB minus the damage phase
        RES_ENTER     = 0x021D28A5    # (desc, phase) -- chain-depth push,  [0x0229AB7C+0x28]++
        RES_BODY      = 0x0220731D    # (desc, arg1)  -- the actual Special Summon
        RES_LEAVE     = 0x021D2965    # (desc, phase) -- chain-depth pop,   [0x0229AB7C+0x28]--
        DAMAGE_PRIM   = 0x021CFBC8    # (desc, side, amount) -- what phase 0x7F called with 400
        STATE_PHASE   = 0x0229AAFC    # [+0x70] = the resolver phase
        RIDER_GATE    = 0x021A14E9    # (side, 0xB, cid, 5) -- 0x021F44D8's prologue gate
        ZONE_INDEX    = 0x021A2511    # (side, desc[+0xC]) -> index, <0 = fail
        ZONE_CHECK    = 0x021A2619    # (ptr) -> bool          (0x021F04FC's second gate)
        CHAIN_PROBE   = 0x0224AF7D    # (desc) -> bool         (the escape hatch)
        FREE_ZONE     = 0x021B9ECD    # (side) -> bool = 0x021B9708(side, 8, 0), THE TRIPLE'S
                                      #   BRANCH: no free-zone precondition, cid-less
        GY_FINAL      = 0x021BA441    # (desc) -> bool         (0x021F04FC's tail)
        STATE_A       = 0x0229AC94    # zone-record array base
        STATE_A_SIDE  = 0x00000B3C    # per-side stride
        STATE_A_OFF   = 0x0000055C    # the sub-array 0x021F0522 adds
        STATE_B       = 0x0229AB7C    # the [+0x18] escape-hatch flag

        # ---------------------------------------------------------------------------
        # PART A/B -- the visible card
        # ---------------------------------------------------------------------------
        NEW_ATTRIBUTE = "DARK"       # unchanged from the donor
        NEW_RACE = "Fiend"           # unchanged from the donor
        NEW_LEVEL = 8
        NEW_ATK = 2700
        NEW_DEF = 1800
        NEW_CARD_TYPE = 3            # Effect Monster (the donor is 1 = Normal Monster);
                                     # event.promoted_vanilla_cardprop_is_correct
        # The donor's English name slot is 26 B and "Grapha, Dragon Lord of Dark World"
        # is 33 B.  Slots are a HARD ceiling (donor.name_blob_has_no_slack: no trailing
        # padding, no unreferenced strings, the spare card_indx entry is a zero-length
        # sentinel), so the name is truncated -- chosen by the user.  It still
        # contains the literal "Dark World" so an in-game name search finds it, and NO
        # engine behaviour depends on it: Dark World membership is the cid list, not the
        # name.
        NEW_NAME = b"Grapha, Dark World Lord"
        NEW_DESC = (b"You can Special Summon this card from your GY by returning 1 other "
                    b"Dark World monster you control to the hand.")
        from otn_enhanced.data.card_stats import TEXT_LANGS


        # ---------------------------------------------------------------------------
        # small helpers (ported verbatim from snoww / reborn_tengu)
        # ---------------------------------------------------------------------------


        def _keys(ov: bytearray, base: int, count: int, stride: int, wide: bool) -> list[int]:
            fmt = "<I" if wide else "<H"
            return [struct.unpack_from(fmt, ov, _off(base + i * stride))[0] for i in range(count)]


        def _insert_sorted(ov: bytearray, base: int, count: int, stride: int, fmt: str,
                           record: tuple, drop_cid: int, label: str, wide: bool) -> None:
            """Count-neutral sorted insert: delete the phantom row, shift, write *record*."""
            keys = _keys(ov, base, count, stride, wide)
            new_cid = record[0]
            if new_cid in keys:
                print(f"{label}: 0x{new_cid:04X} already present (idempotent) -- skipped")
                return
            assert drop_cid in keys, f"{label}: phantom 0x{drop_cid:04X} not found -- table already edited?"
            dst = keys.index(drop_cid)
            pos = sum(1 for k in keys if k < new_cid)
            if pos > dst:
                blk = bytes(ov[_off(base + (dst + 1) * stride):_off(base + pos * stride)])
                ov[_off(base + dst * stride):_off(base + (pos - 1) * stride)] = blk
                pos -= 1
            elif pos < dst:
                blk = bytes(ov[_off(base + pos * stride):_off(base + dst * stride)])
                ov[_off(base + (pos + 1) * stride):_off(base + (dst + 1) * stride)] = blk
            struct.pack_into(fmt, ov, _off(base + pos * stride), *record)
            moved = abs(pos - dst)
            print(f"{label}: dropped phantom 0x{drop_cid:04X} @{dst}, inserted 0x{new_cid:04X} @{pos} "
                  f"({moved} row{'' if moved == 1 else 's'} shifted, count {count} unchanged)")
            after = _keys(ov, base, count, stride, wide)
            assert all(after[i] <= after[i + 1] for i in range(count - 1)), \
                f"{label}: table lost its sort order"


        def _bl(site: int, target: int) -> bytes:
            """Encode a 32-bit ARMv4T Thumb BL from *site* to *target*."""
            offset = (target - (site + 4)) & 0x7FFFFF
            return struct.pack("<HH", 0xF000 | ((offset >> 12) & 0x7FF),
                               0xF800 | ((offset >> 1) & 0x7FF))


        def _route(ov: bytes, cid: int) -> int:
            """Which relocation arm *cid* reaches, following PART H's stub.

            snoww's tracer used to stop at any BL whose target was not its OWN stub,
            so a cid routed through PART H's node looked like it had changed leaf -- which
            failed that module's whole-table regression walk on a patch that changed
            nothing for it.  It now walks into any REGISTERED stub, and PART H's is
            modelled by its own instructions rather than by a second hand-written model
            that could drift from them.  Registering here (not at import) keeps the
            dependency one-way.
            """
            return _snoww._switch_leaf(ov, cid)


        def _read_cstr(buf: bytes, start: int) -> bytes:
            return buf[start:buf.index(b"\x00", start)]


        def _iter_paths(folder, prefix=""):
            """Yield every file path inside an ndspy filename folder tree."""
            for f in getattr(folder, "files", []) or []:
                yield f"{prefix}{f}"
            folders = getattr(folder, "folders", []) or []
            items = folders.items() if isinstance(folders, dict) else folders
            for item in items:
                if isinstance(item, tuple) and len(item) >= 2:
                    yield from _iter_paths(item[1], prefix=f"{prefix}{item[0]}/")


        def _open_pac(rom):
            """Return (file_id, mutable bin2.pac bytes, parsed archive)."""
            pac_path = next((p for p in _iter_paths(rom.filenames)
                             if p.lower().endswith("bin2.pac")), None)
            if pac_path is None:
                raise RuntimeError("bin2.pac not found in ROM")
            fid = rom.filenames.idOf(pac_path)
            data = bytearray(rom.files[fid])
            return fid, data, parse_pac(bytes(data), pac_path)


        def _find_prop(pac_data: bytes, archive, cid: int) -> tuple[int, int]:
            """Return (absolute offset, card_prop index) of *cid*'s record."""
            cpf = next((f for f in archive.files
                        if f.get_clean_name().lower() == "card_prop.bin"), None)
            if cpf is None:
                raise RuntimeError("card_prop.bin not found in bin2.pac")
            body_start = cpf.address + 8                       # records follow an 8-byte header
            for i in range((cpf.size - 8) // 8):
                off = body_start + i * 8
                if int.from_bytes(pac_data[off:off + 8], "little") & 0x3FFF == cid:
                    return off, i
            raise RuntimeError(f"card_id 0x{cid:04X} not found in card_prop.bin")


        def _place_string(pac_data: bytearray, file_base: int, file_size: int,
                          old_off: int, new_bytes: bytes, pad_cursor: dict) -> int | None:
            """Write *new_bytes* for the string at *old_off*, keeping the file the SAME size."""
            old_str = _read_cstr(pac_data, file_base + old_off)
            if len(new_bytes) <= len(old_str):
                slot = len(old_str)
                abs_off = file_base + old_off
                pac_data[abs_off:abs_off + slot + 1] = new_bytes + b"\x00" * (slot + 1 - len(new_bytes))
                return old_off
            need = len(new_bytes) + 1
            # *** RELOCATION DISABLED -- see notes/card-text-blob-findings.md. ***
            # This used to scavenge the file's "trailing zero padding" by walking BACK from
            # the end over NUL bytes. On a blob re-emitted in index order by
            # card_text.rebuild_blobs, a language whose trailing entries are empty strings
            # (Korean) is a long NUL run, so that walk strides back over real strings and
            # lands on ANOTHER CARD'S TERMINATOR, fusing two cards' names (measured on
            # snoww's identical copy, chain step 30). Nothing needs relocation any
            # more: every renamed card gets its full printed text from
            # card_text.apply_to_rom, which re-emits the whole blob in index order.
            return None                                            # doesn't fit -- keep the donor's text


        # ---------------------------------------------------------------------------
        # PART E -- the candidate filter (cls2 +08)
        # ---------------------------------------------------------------------------
        def filt_stub(base: int = None) -> bytes:
            """(r0 = source desc, r1 = cand side, r2 = cand zone) -> 0 reject / nonzero accept.

            The two tests the 3DS has and the NDS's Zephyrus lacks, then Zephyrus's own
            generic predicate with his own mask:

                cid = 0x021A36EC(cand_side, cand_zone)      ; the card in that zone
                if cid == DONOR_CID:      reject            ; except "Grapha"
                if !0x020238B4(cid):      reject            ; must be a "Dark World" card
                return 0x021D6E40(src_desc, cand_side, cand_zone, 0x00208075)

            Every external call is `LDR Rn,=target|1 ; BLX Rn` rather than a long BL: BLX
            clobbers LR, which is why the original LR is pushed and the stub returns via
            POP {..., PC} (thumb.pop_into_lr_footgun).
            """
            base = FILT_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.call_addr(ZONE_CID, R5, R6, via=R3)
            b.ldr_const(1, DONOR_CID)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "reject")
            b.call_addr(HAS_DW, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "reject")
            b.call_addr(ZONE_PRED, R4, R5, R6, GRAPHA_MASK, via=R7)
            b.insn("B", "out")
            b.label("reject")
            b.insn("MOV", "R0, #0x0")
            b.label("out")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        # PART G -- the resolver (cls2 +04), Zephyros's minus his 400 LP self-damage
        # ---------------------------------------------------------------------------
        def res_stub(base: int = None) -> bytes:
            """(r0 = desc, r1 = arg1) -> next phase.  0x02230EBC with phase 0x7F deleted.

            THE 400-DAMAGE TRAP.  Zephyros's resolver is a 3-phase machine on
            [0x0229AAFC+0x70], and its phase 0x7F is nothing but

                0x02230EEC  ldrb r1,[r5,#2]          ; side
                0x02230EEE  movs r2,#0x19
                0x02230EF0  lsls r2,r2,#4            ; r2 = 0x190 = 400
                0x02230EF2  bl   0x021CFBC8          ; inflict it
                0x02230EF6  movs r0,#0x7e            ; -> phase 0x7E

            which is his printed text, not boilerplate: "Special Summon this card, and
            if you do, TAKE 400 DAMAGE".  Grapha has no such clause.  Because 0x7F does
            nothing else and falls straight to 0x7E, having phase 0x80 return 0x7E
            unconditionally -- instead of branching on [0x0229AAFC+0x74] -- is exactly
            equivalent MINUS the damage.  Everything else is transcribed verbatim,
            including passing the loaded phase in r1 to both chain-depth calls.
            """
            base = RES_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R3, R4, R5, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R4, R1, #0x0")
            b.ldr_const(3, STATE_PHASE)
            b.insn("LDR", "R1, [R3, #0x70]")
            b.insn("CMP", "R1, #0x7E")
            b.insn("BEQ", "ph7e")
            b.insn("CMP", "R1, #0x80")
            b.insn("BNE", "none")
            b.call_addr(RES_ENTER, R5, via=R3)
            b.call_addr(RES_BODY, R5, R4, via=R3)
            b.insn("MOV", "R0, #0x7E")
            b.insn("POP", "{R3, R4, R5, PC}")
            b.label("ph7e")
            b.call_addr(RES_LEAVE, R5, via=R3)
            b.label("none")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R3, R4, R5, PC}")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        # THE DISCRIMINATOR, emitted once and shared by all five dispatchers
        # ---------------------------------------------------------------------------
        def _clause2_test(b: EffectBuilder, reg: Reg, yes: str, no: str) -> None:
            """Branch to *yes* iff the descriptor in *reg* is the DISCARD post.

            All three fields are checked, though only desc[+4] separates the two paths:
            desc[+3]/desc[+5] are kept so that an unrelated event whose arg0 happens to
            be 0x1F cannot be mistaken for the trigger.

            ⚠️ THE FALL-THROUGH IS CLAUSE 1, which INVERTS the polarity of every round
            before this one.  Clause 1 is the in-game-confirmed clause, so anything not
            positively identified as the discard must behave exactly as it does today.
            The *no* label is emitted here; the caller's clause-1 arm follows it.
            """
            b.insn("LDRB", f"R0, [{reg!r}, #0x4]")
            b.insn("CMP", f"R0, #0x{DISCARD_CODE_MID6:02X}")
            b.insn("BNE", no)
            b.insn("LDRB", f"R0, [{reg!r}, #0x3]")
            b.insn("CMP", f"R0, #0x{GY_ACTION_CODE_LOW5:02X}")
            b.insn("BNE", no)
            b.insn("LDRB", f"R0, [{reg!r}, #0x5]")
            b.insn("CMP", f"R0, #{GY_ACTION_CODE_HIGH3}")
            b.insn("BEQ", yes)
            b.label(no)


        # ---------------------------------------------------------------------------
        # PART M -- cls2 +0C, the ACTIVATION-CONDITION dispatcher (ov5)
        # ---------------------------------------------------------------------------
        def gate2_stub(base: int = None) -> bytes:
            """(r0 = desc, r1 = arg1) -> activation code.  0 = no, >=2 = unconditionally.

            Clause 2 must answer 2 ("activatable unconditionally"), which is what the 3DS
            row pairs Grapha with (0x00404260 -> NDS 0x0224A115) and what stops slot2
            being consulted with the wrong clause's filter.  Clause 1 keeps its own gate.
            """
            base = GATE2_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("ADD", "R4, R1, #0x0")
            b.ldr_const(6, DIAG2_BLOCK)
            b.insn("LDR", "R0, [R6, #0x0]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x0]")
            b.insn("LDRB", "R0, [R5, #0x4]")
            b.insn("STR", "R0, [R6, #0x4]")
            b.insn("LDR", "R1, [R6, #0xC]")
            b.insn("ORR", "R0, R1")
            b.insn("STR", "R0, [R6, #0xC]")
            b.insn("LDRB", "R0, [R5, #0x5]")
            b.insn("STR", "R0, [R6, #0x8]")
            _clause2_test(b, R5, "clause2", "c1")
            b.call_addr(GATE_STUB, R5, R4, via=R3)
            b.insn("STR", "R0, [R6, #0x28]")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("clause2")
            b.insn("LDR", "R0, [R6, #0x10]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x10]")
            b.insn("MOV", f"R0, #0x{ALWAYS_ACTIVATABLE:X}")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        # PART N -- cls2 +10, the COST dispatcher (ov5)
        # ---------------------------------------------------------------------------
        def cost2_stub(base: int = None) -> bytes:
            """(r0 = desc, r1 = arg1).  Clause 1's bounce cost, or nothing for clause 2.

            ⚠️ Clause 2 MUST RETURN 1, NOT 0.  An absent slot4 is reported as 1 by the
            wrapper at 0x0224AE50, and returning 0 means "not done, call me again" --
            measured in-game as a hang with the slot entered 6,455 times.
            """
            base = COST2_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.ldr_const(6, DIAG2_BLOCK)
            b.insn("LDR", "R0, [R6, #0x1C]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x1C]")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("STR", "R0, [R6, #0x20]")
            _clause2_test(b, R4, "clause2", "c1")
            b.call_addr(ZEPH_COST, R4, R5, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("clause2")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        # PART H -- the switch-node stub (overlay 3)
        # ---------------------------------------------------------------------------
        def arm_stub(base: int = None) -> bytes:
            """Reproduce the terminal node, and long-branch the donor into the DW arm.

                subs r1,#8       ; r1 = 0x1969 - 8   = 0x1961  (the donor)
                cmp  r5,r1
                beq  ours
                subs r1,#0x1b    ; r1 = 0x1961 - 0x1B = 0x1946 (Ojamagic) -- the value and
                cmp  r5,r1       ;   the flags the caller's `bne 0x021D14EA` expects
                bx   lr
           ours BL   0x021D185C  ; a 4-byte long jump; LR is dead here (the enclosing
                                 ;   function returns by POPping PC, never via LR)

            Exactly 16 bytes, which is exactly what the two dead blocks provide.
            """
            base = ARM_STUB if base is None else base
            b = EffectBuilder()
            b.insn("SUB", "R1, #0x8")
            b.insn("CMP", "R5, R1")
            b.insn("BEQ", "ours")
            b.insn("SUB", "R1, #0x1B")
            b.insn("CMP", "R5, R1")
            b.insn("BX", "LR")
            b.label("ours")
            b.insn("NOP")
            b.insn("NOP")
            body = b.assemble(base, pad="nop")
            blob = bytearray(body[:12])                       # the six real instructions
            blob += _bl(base + 12, DW_ARM)                    # ours: BL the Dark World arm
            assert len(blob) == ARM_STUB_LEN, len(blob)
            return bytes(blob)


        # ---------------------------------------------------------------------------
        # PART I -- cls2 +14, the target declaration (ov5)
        # ---------------------------------------------------------------------------
        def decl_stub(base: int = None) -> bytes:
            """(r0 = desc, r1 = arg1) -> declare a target, or 1 = SKIP.

            Clause 2 targets ("target 1 card your opponent controls"); clause 1 must not.
            """
            base = DECL_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.ldr_const(6, DIAG_BLOCK)
            b.insn("LDR", "R0, [R6, #0x18]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x18]")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("STR", "R0, [R6, #0x1C]")
            _clause2_test(b, R4, "doit", "skip")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("doit")
            b.insn("LDR", "R0, [R6, #0x28]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x28]")
            b.call_addr(TARGET_DECL, R4, R5, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        # PART J -- cls2 +04, the resolver DISPATCHER (ov5)
        # ---------------------------------------------------------------------------
        def res2_stub(base: int = None) -> bytes:
            """(r0 = desc, r1 = event) -> next phase.  Clause 1's summon or clause 2's destroy.

            CAVE_GRAPHA_RES (clause 1, in-game confirmed) is byte-identical and simply
            called.
            """
            base = RES2_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.ldr_const(6, DIAG_BLOCK)
            b.insn("LDR", "R0, [R6, #0x0]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x0]")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("STR", "R0, [R6, #0x3C]")
            b.insn("LDRB", "R0, [R4, #0x5]")
            b.insn("STR", "R0, [R6, #0x34]")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.insn("STR", "R0, [R6, #0x38]")
            _clause2_test(b, R4, "clause2", "c1")
            b.call_addr(RES_STUB, R4, R5, via=R3)
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("clause2")
            b.call_addr(C3_ARM, R4, R5, via=R3)
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        # PART P -- the two SHARED clause-3 halves (ov5)
        #
        # IN-GAME CONFIRMED through the Conscription test harness, which drives
        # these very addresses from its own phase shell: it summoned Battle Ox 0x0FC0 out of
        # the opponent's hand, with the slot pointer measured at 0x0229B8F8 == STATE_A +
        # 1*0xB3C + 0x124 + 1*4.  See dispatch.summon_from_opponent_hand_recipe.
        #
        # ⚠️ THEY LIVE HERE, NOT IN THE HARNESS, because the harness never ships.  Grapha
        # clause 3 calls them, so the module that ships has to be the one that writes them.
        # ---------------------------------------------------------------------------
        def c3_post_stub(base: int = None) -> bytes:
            """SHARED half 1.  (r0 = desc) -> 1 if the random pick was posted, else 0.

            Grapha clause 3 calls this from its OWN phase machine, so the phase test
            deliberately lives in the caller rather than here.
            """
            base = C3_POST_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.ldr_const(4, C3_DIAG)
            b.insn("LDR", "R0, [R4, #0xC]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R4, #0xC]")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("MOV", "R1, #0x1")
            b.insn("SUB", "R0, R1, R0")
            b.insn("AND", "R0, R1")
            b.insn("STR", "R0, [R4, #0x30]")
            b.ldr_const(2, HAND_COUNT)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "hc0")
            b.ldr_const(1, STATE_A_SIDE)
            b.insn("ADD", "R2, R2, R1")
            b.label("hc0")
            b.insn("LDR", "R1, [R2, #0x0]")
            b.insn("STR", "R1, [R4, #0x2C]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "empty")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("MOV", "R1, #0x1")
            b.insn("SUB", "R0, R1, R0")
            b.insn("AND", "R0, R1")
            b.call_addr(PEEK_POST, R0, 0, via=R3)
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, PC}")
            b.label("empty")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b.assemble(base, pad="nop")


        def c3_finish_stub(base: int = None) -> bytes:
            """SHARED half 2.  (r0 = desc).  The confirmed look-at + conditional summon.

            IN-GAME CONFIRMED 2026-08-28 as part of the Conscription harness -- see
            dispatch.summon_from_opponent_hand_recipe.  ⚠️ Two traps are baked in here:
            0x021BA684 is a PREDICATE whose answer must be tested, and 0x021AD870
            returns a truthy COUNT (measured 5), so both are tested against zero.
            """
            base = C3_FIN_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.ldr_const(4, C3_DIAG)
            b.insn("LDR", "R0, [R4, #0x10]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R4, #0x10]")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("MOV", "R1, #0x1")
            b.insn("SUB", "R1, R1, R0")
            b.insn("MOV", "R0, #0x1")
            b.insn("AND", "R1, R0")
            b.ldr_const(2, STATE_A)
            b.insn("CMP", "R1, #0x0")
            b.insn("BEQ", "pb0")
            b.ldr_const(3, STATE_A_SIDE)
            b.insn("ADD", "R2, R2, R3")
            b.label("pb0")
            b.insn("MOV", "R3, #0x49")
            b.insn("LSL", "R3, R3, #0x2")
            b.insn("ADD", "R2, R2, R3")
            b.ldr_const(3, EFFECT_CTX)
            b.insn("LDRH", "R3, [R3, #0x6]")
            b.insn("STR", "R3, [R4, #0x14]")
            b.insn("LSL", "R3, R3, #0x2")
            b.insn("ADD", "R2, R2, R3")
            b.insn("STR", "R2, [R4, #0x34]")
            b.insn("LDR", "R6, [R2, #0x0]")
            b.insn("STR", "R6, [R4, #0x18]")
            b.insn("LSL", "R2, R6, #0x11")
            b.insn("LSR", "R2, R2, #0x1F")
            b.insn("ADD", "R1, R6, #0x0")
            b.insn("LSL", "R1, R1, #0x1")
            b.insn("LSR", "R1, R1, #0x18")
            b.insn("LSL", "R1, R1, #0x1")
            b.insn("ADD", "R7, R2, R1")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.call_addr(REVEAL, R0, R7, via=R3)
            b.insn("LSL", "R0, R6, #0x12")
            b.insn("LSR", "R0, R0, #0x12")
            b.insn("STR", "R0, [R4, #0x1C]")
            b.call("is_monster", via=R3)
            b.insn("STR", "R0, [R4, #0x20]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "done")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("LDR", "R1, [R4, #0x1C]")
            b.insn("ADD", "R2, R7, #0x0")
            b.ldr_const(6, MAY_SUMMON)
            b.insn("MOV", "R3, #0xB")
            b.insn("BLX", "R6")
            b.insn("STR", "R0, [R4, #0x38]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "done")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.call_addr(SS_ALLOWED, via=R3)
            b.insn("STR", "R0, [R4, #0x3C]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "done")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.call_addr(FREE_ZONE, via=R3)
            b.insn("STR", "R0, [R4, #0x24]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "done")
            b.insn("LDR", "R0, [R4, #0x28]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R4, #0x28]")
            b.insn("LDR", "R1, [R4, #0x34]")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.call_addr(SUMMON, R0, R1, 1, 0, via=R4)
            b.label("done")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")



        # ---------------------------------------------------------------------------
        # PART O -- clause 2 + clause 3, the discard-path arm (ov5)
        # ---------------------------------------------------------------------------
        def c3_arm_stub(base: int = None) -> bytes:
            """(r0 = desc, r1 = event) -> the next phase.  Clause 2's destroy, then clause 3.

            Lives in its own cave slot because it does not fit inside CAVE_GRAPHA_RES2's
            0x60, and because keeping it separate means the clause-1 path is untouched
            bytes rather than untouched-by-inspection.

            Phase 0x80 destroys (clause 2, in-game confirmed 2026-08-28) and then applies
            CLAUSE 3's condition; phase 0x7F runs the shared finish half.  Both phase
            values are the ones the shared payload already uses, so nothing is translated.

            ⚠️ THE CONDITION IS SHIPPED CODE, NOT A NEW GUESS -- it is snoww's
            clause-2 slot5 gate verbatim (dispatch.opponent_effect_discard_test, itself
            read off native Sillva 0x1968), and Snoww clause 2 is in-game confirmed.
            Both facts come out of the one descriptor: desc[+0x20] is the packed card
            word, desc[+2] the acting side, bit 18 must DIFFER (an opponent's effect) and
            bit 9 must MATCH (from your hand).
            """
            base = C3_ARM if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.ldr_const(6, DIAG_BLOCK)
            b.ldr_const(0, STATE_PHASE)
            b.insn("LDR", "R0, [R0, #0x70]")
            b.insn("STR", "R0, [R6, #0x24]")
            b.insn("CMP", "R0, #0x7F")
            b.insn("BEQ", "c3fin")
            b.insn("LDR", "R0, [R6, #0x20]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x20]")
            b.call_addr(DESTROY_RES, R4, R5, via=R3)
            b.insn("LDRB", "R3, [R4, #0x2]")
            b.insn("LDR", "R2, [R4, #0x20]")
            b.insn("ADD", "R1, R2, #0x0")
            b.insn("LSL", "R1, R1, #0xD")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("CMP", "R3, R1")
            b.insn("BEQ", "c3no")
            b.insn("ADD", "R1, R2, #0x0")
            b.insn("LSL", "R1, R1, #0x16")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("CMP", "R3, R1")
            b.insn("BNE", "c3no")
            b.insn("LDR", "R0, [R6, #0x2C]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x2C]")
            b.call_addr(C3_POST, R4, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "c3no")
            b.insn("MOV", "R0, #0x7F")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("c3no")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("c3fin")
            b.insn("LDR", "R0, [R6, #0x30]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x30]")
            b.call_addr(C3_FINISH, R4, via=R3)
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        # PART K -- cls2 +08, the filter DISPATCHER (ov5)
        # ---------------------------------------------------------------------------
        def filt2_stub(base: int = None) -> bytes:
            """(r0 = src desc, r1 = cand side, r2 = cand zone) -> 0 reject / nonzero accept.

            The filter receives no event, but it does receive the SOURCE DESCRIPTOR, and
            desc[+3] carries the posted event code -- which is what finally makes this
            slot decidable.  Clause 2 -> Goldd's "cards your opponent controls"
            0x021DE7C9 (the 3DS pairs Grapha with Goldd on this very slot).
            """
            base = FILT2_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.ldr_const(7, DIAG_BLOCK)
            b.insn("LDR", "R0, [R7, #0x10]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R7, #0x10]")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("STR", "R0, [R7, #0x14]")
            _clause2_test(b, R4, "clause2", "c1")
            b.call_addr(FILT_STUB, R4, R5, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("clause2")
            b.call_addr(GOLDD_FILTER, R4, R5, R6, via=R3)
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        # PART F -- the "may this GY effect be offered" gate (cls2 +0C)
        # ---------------------------------------------------------------------------
        def gate_stub(base: int = None) -> bytes:
            """(r0 = desc, r1 = arg1) -> bool.  0x021F44D8 + 0x021F04FC, triple branch forced.

            Transcribed instruction-for-instruction from the two native functions, with
            exactly one deviation: where 0x021F04FC tests the source cid against the
            hard-coded triple {0x1B20, 0x20B9, 0x241C} and sends only those three to the
            cid-less free-zone check 0x021B9ECC, this stub goes there unconditionally --
            because it is only ever reached for the donor's own cid.  Everything the
            generic branch (0x021F0384) would add is a FREE-MONSTER-ZONE precondition,
            which is wrong for a card whose cost frees a zone.

            `arg1` is deliberately unused: 0x021F04FC forwards it only to 0x021F0384,
            the branch this stub never takes.
            """
            base = GATE_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.turnlog_query(R0, R2, 5, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "reject")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0xC]")
            b.call_addr(ZONE_INDEX, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "reject")
            b.insn("LSL", "R0, R0, #0x2")
            b.insn("LDRB", "R3, [R4, #0x2]")
            b.insn("MOV", "R2, #0x1")
            b.insn("AND", "R3, R2")
            b.insn("MOV", "R2, #0x0")
            b.insn("CMP", "R3, #0x0")
            b.insn("BEQ", "side0")
            b.ldr_const(2, STATE_A_SIDE)
            b.label("side0")
            b.ldr_const(1, STATE_A)
            b.insn("ADD", "R2, R1, R2")
            b.ldr_const(1, STATE_A_OFF)
            b.insn("ADD", "R1, R2, R1")
            b.insn("ADD", "R0, R1, R0")
            b.call_addr(ZONE_CHECK, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "reject")
            b.ldr_const(0, STATE_B)
            b.insn("LDR", "R0, [R0, #0x18]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "freezone")
            b.call_addr(CHAIN_PROBE, R4, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "accept")
            b.label("freezone")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(FREE_ZONE, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "reject")
            b.call_addr(GY_FINAL, R4, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "reject")
            b.label("accept")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("reject")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        # preconditions -- everything this patch READS but never writes
        # ---------------------------------------------------------------------------
        def _assert_preconditions(ov: bytearray) -> None:
            def u32(a):
                return struct.unpack_from("<I", ov, _off(a))[0]

            # the template's cls2 record is intact
            c2 = _keys(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, True)
            assert c2.count(TEMPLATE_CID) == 1, "Zephyrus lost (or gained) a cls2 record"
            rec = struct.unpack_from("<6I", ov, _off(CLS2_BASE + c2.index(TEMPLATE_CID) * CLS2_STRIDE))
            assert rec == ZEPH_CLS2, f"the Zephyrus template moved: {['%08X' % w for w in rec]}"
            assert c2.count(DONOR_CID) == 0, \
                f"the donor 0x{DONOR_CID:04X} already owns a cls2 record -- a second would shadow it"
            assert all(c2[i] <= c2[i + 1] for i in range(CLS2_COUNT - 1)), "cls2 is not sorted"

            # the GY-action row we are about to claim still holds the phantom + the shape
            row = GYACT_BASE + GYACT_ROW * GYACT_STRIDE
            got = (u32(row), u32(row + 4), u32(row + 8), u32(row + 12))
            assert got == (GYACT_DROP_PHANTOM, GYACT_ZONE_GY, GYACT_CHECK, GYACT_POST), \
                f"GY-action row {GYACT_ROW} is not the expected phantom row: {['%08X' % w for w in got]}"
            # ... and Zephyrus's own row is in the same family, which is what makes the
            # claimed row the right shape for a GY self-Special-Summon.
            zeph = [i for i in range(GYACT_COUNT)
                    if u32(GYACT_BASE + i * GYACT_STRIDE) == TEMPLATE_CID]
            assert len(zeph) == 1, "Zephyrus lost its GY-action row"
            z = GYACT_BASE + zeph[0] * GYACT_STRIDE
            assert (u32(z + 4), u32(z + 8), u32(z + 12)) == (GYACT_ZONE_GY, GYACT_CHECK, GYACT_POST), \
                "the Zephyrus GY-action row changed shape"
            print(f"0  template Zephyrus 0x{TEMPLATE_CID:04X}: cls2 row + GY-action row {zeph[0]} intact")

            # the free-zone trap: the hard-coded triple must still be a triple
            for site, want in ((0x021F059C, 0x1B20), (0x021F05A0, 0x20B9), (0x021F05A4, 0x241C)):
                assert u32(site) == want, \
                    f"0x021F04FC's cid triple changed at 0x{site:08X} (expected 0x{want:04X})"
            print("0  0x021F04FC's free-zone-bypass triple {0x1B20, 0x20B9, 0x241C} intact")

            # -- CLAUSE 2 preconditions ---------------------------------------------
            # the templates whose halves clause 2 reuses
            for cid, want in ((KAHKKI_CID, (KAHKKI_CID, DESTROY_RES, 0x021D8CE5, 0x0224A115,
                                            0, TARGET_DECL)),
                              (GREN_CID, (GREN_CID, DESTROY_RES, 0x021DB3BD, 0x0224A115,
                                          0, TARGET_DECL))):
                i = c2.index(cid)
                got = struct.unpack_from("<6I", ov, _off(CLS2_BASE + i * CLS2_STRIDE))
                assert got == want, f"the 0x{cid:04X} template moved: {['%08X' % w for w in got]}"
            gi = c2.index(0x1969)
            assert struct.unpack_from("<I", ov, _off(CLS2_BASE + gi * CLS2_STRIDE + 8))[0] \
                == GOLDD_FILTER, "Goldd's candidate filter moved"
            print(f"0  clause-2 templates intact: Kahkki/Gren destroy 0x{DESTROY_RES:08X} + "
                  f"declaration 0x{TARGET_DECL:08X}, Goldd filter 0x{GOLDD_FILTER:08X}")

            # the switch node PART H replaces, and that nothing branches into it
            assert bytes(ov[_off(SWITCH_HOOK):_off(SWITCH_HOOK) + 4]) == SWITCH_HOOK_NATIVE, \
                "the 0x021D14E2 switch node is not the stock `subs r1,#0x23 ; cmp r5,r1`"
            for site in (SWITCH_HOOK, SWITCH_HOOK + 2):
                for a in range(0x021D1392, 0x021D19C0, 2):
                    hw = struct.unpack_from("<H", ov, _off(a))[0]
                    tgt = None
                    if (hw & 0xF800) == 0xE000:
                        imm = hw & 0x7FF
                        tgt = a + 4 + (imm - 0x800 if imm & 0x400 else imm) * 2
                    elif (hw & 0xF000) == 0xD000 and (hw & 0x0F00) != 0x0F00:
                        imm = hw & 0xFF
                        tgt = a + 4 + (imm - 0x100 if imm & 0x80 else imm) * 2
                    assert tgt != site, f"0x{a:08X} branches into the hook site 0x{site:08X}"
            # the donor's own arithmetic: r1 == 0x1969 there, so 0x1961 = r1-8 and
            # Ojamagic 0x1946 = r1-0x23, which is what arm_stub reproduces
            assert DONOR_CID == SWITCH_R1_ON_ENTRY - 8, "the donor is not r1-8 at the node"
            assert OJAMAGIC_CID == SWITCH_R1_ON_ENTRY - 0x23, "Ojamagic is not r1-0x23"
            # the two dead blocks the stub spans
            assert bytes(ov[_off(ARM_STUB):_off(ARM_STUB) + ARM_STUB_LEN]) == ARM_STUB_NATIVE, \
                "the ov3 dead blocks at 0x021B594A are not stock"
            print(f"H  switch node 0x{SWITCH_HOOK:08X} stock, no inbound branches; "
                  f"{ARM_STUB_LEN} B ov3 dead space at 0x{ARM_STUB:08X} stock")


        def _assert_arm9_setcode(rom) -> list[int]:
            """The donor must ALREADY be a Dark World card.  Asserted, never written."""
            import ndspy.code
            arm9 = ndspy.code.MainCodeFile(rom.arm9, rom.arm9RamAddress)
            sec = next(s for s in arm9.sections
                       if s.ramAddress <= DW_LIST < s.ramAddress + len(s.data))
            o = DW_LIST - sec.ramAddress
            lst = list(struct.unpack_from(f"<{DW_LIST_COUNT}H", sec.data, o))
            assert all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)), \
                "the Dark World set-code list is not strictly sorted"
            assert DONOR_CID in lst, \
                f"donor 0x{DONOR_CID:04X} is NOT in the Dark World set-code list"
            tsec = next(s for s in arm9.sections
                        if s.ramAddress <= DW_THUNK_SLOT < s.ramAddress + len(s.data))
            slot = struct.unpack_from("<I", tsec.data, DW_THUNK_SLOT - tsec.ramAddress)[0]
            assert slot == DW_THUNK, f"has_set_code[0x0F] moved: 0x{slot:08X}"
            return lst


        # ---------------------------------------------------------------------------
        # the overlay-3 edits
        # ---------------------------------------------------------------------------
        def apply_effect(ov: bytearray) -> None:
            _assert_preconditions(ov)

            # -- PART C: the GY-action registry row ----------------------------------
            row = GYACT_BASE + GYACT_ROW * GYACT_STRIDE
            struct.pack_into("<I", ov, _off(row), DONOR_CID)
            print(f"C  GY-action[{GYACT_ROW}] @0x{row:08X}: phantom 0x{GYACT_DROP_PHANTOM:04X} -> "
                  f"0x{DONOR_CID:04X} {{zone 0x{GYACT_ZONE_GY:02X}, chk 0x{GYACT_CHECK:08X}, "
                  f"post 0x{GYACT_POST:08X}}} (in place, count {GYACT_COUNT} unchanged)")

            # -- PART D: the cls2 record ---------------------------------------------
            # -- PART H: admit the donor to the Dark World effect-discard arm --------
            ov[_off(SWITCH_HOOK):_off(SWITCH_HOOK) + 4] = _bl(SWITCH_HOOK, ARM_STUB)
            blob = arm_stub()
            ov[_off(ARM_STUB):_off(ARM_STUB) + len(blob)] = blob
            print(f"H  0x{SWITCH_HOOK:08X} -> BL 0x{ARM_STUB:08X} ({ARM_STUB_LEN} B ov3 stub): "
                  f"cid 0x{DONOR_CID:04X} now reaches the effect-discard arm 0x{DW_ARM:08X}, "
                  f"0x{OJAMAGIC_CID:04X} still reaches its own")

            record = (DONOR_CID, RES2_STUB | 1, FILT2_STUB | 1, GATE2_STUB | 1,
                      COST2_STUB | 1, DECL_STUB | 1)
            _insert_sorted(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, "<6I",
                           record, CLS2_DROP_PHANTOM,
                           f"D  cls2 {{+04 resolver, +08 filter, +0C gate, "
                           f"+10 0x{ZEPH_COST:08X} cost, +14 declaration}}", wide=True)


        stubs = []
        for blob, addr, reserve, label in (
                (filt_stub(), FILT_STUB, FILT_RESERVE, "E  candidate filter (cls2 +08)"),
                (gate_stub(), GATE_STUB, GATE_RESERVE, "F  offer gate (cls2 +0C)"),
                (res_stub(),  RES_STUB,  RES_RESERVE,  "G  resolver, no 400 damage (cls2 +04)"),
                (bytes(DIAG_RESERVE), DIAG_BLOCK, DIAG_RESERVE, "L  clause-2 diagnostic block"),
                (decl_stub(), DECL_STUB, DECL_RESERVE, "I  target declaration (cls2 +14)"),
                (res2_stub(), RES2_STUB, RES2_RESERVE, "J  resolver dispatcher (cls2 +04)"),
                (filt2_stub(), FILT2_STUB, FILT2_RESERVE, "K  filter dispatcher (cls2 +08)"),
                (bytes(DIAG2_RESERVE), DIAG2_BLOCK, DIAG2_RESERVE, "L2 slot3/slot4 diagnostics"),
                (gate2_stub(), GATE2_STUB, GATE2_RESERVE, "M  activation-condition dispatcher (+0C)"),
                (cost2_stub(), COST2_STUB, COST2_RESERVE, "N  cost dispatcher (cls2 +10)"),
                (c3_arm_stub(), C3_ARM, C3_ARM_RESERVE, "O  clause 2+3 discard arm"),
                (c3_post_stub(), C3_POST_STUB, C3_POST_RESERVE, "P1 SHARED C3 post half"),
                (c3_finish_stub(), C3_FIN_STUB, C3_FIN_RESERVE, "P2 SHARED C3 finish half"),
                (bytes(C3_DIAG_RESERVE), C3_DIAG, C3_DIAG_RESERVE, "P3 C3 diagnostic block")):
            effect_verify.assert_thumb1_only(blob, addr)
            assert len(blob) <= reserve, f"{label}: {len(blob)} B exceeds the {reserve} B reservation"
            stubs.append((addr, blob, label))

        def install(rom, view):
            _assert_arm9_setcode(rom)
            apply_effect(view.buf)

        def check_fn(c, rom, view):
            def check(cond, msg):
                c.ok(bool(cond), msg)
                return bool(cond)

            ov = view.buf

            def u32(a):
                return struct.unpack_from("<I", ov, _off(a))[0]

            row = GYACT_BASE + GYACT_ROW * GYACT_STRIDE
            check((u32(row), u32(row + 4), u32(row + 8), u32(row + 12))
                  == (DONOR_CID, GYACT_ZONE_GY, GYACT_CHECK, GYACT_POST),
                  f"C  GY-action[{GYACT_ROW}] = {{0x{DONOR_CID:04X}, zone 0x0E, 0x{GYACT_CHECK:08X}, 0x{GYACT_POST:08X}}}")
            gy = [u32(GYACT_BASE + i * GYACT_STRIDE) for i in range(GYACT_COUNT)]
            check(gy.count(DONOR_CID) == 1, "C  exactly one GY-action row for the donor (a duplicate would shadow it)")
            check(GYACT_DROP_PHANTOM not in gy, f"C  phantom 0x{GYACT_DROP_PHANTOM:04X} dropped (count {GYACT_COUNT} unchanged)")
            check(gy.count(TEMPLATE_CID) == 1, "C  Zephyrus still owns his GY-action row")

            c2 = _keys(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, True)
            want = (DONOR_CID, RES2_STUB | 1, FILT2_STUB | 1, GATE2_STUB | 1, COST2_STUB | 1, DECL_STUB | 1)
            if check(c2.count(DONOR_CID) == 1,
                     f"D  exactly one cls2 record for 0x{DONOR_CID:04X} (a second would be shadowed by find_event_handler's leftmost rule)"):
                rec = struct.unpack_from("<6I", ov, _off(CLS2_BASE + c2.index(DONOR_CID) * CLS2_STRIDE))
                check(rec == want,
                      f"D  cls2 = {{+04 0x{RES2_STUB | 1:08X}, +08 0x{FILT2_STUB | 1:08X}, +0C 0x{GATE2_STUB | 1:08X}, "
                      f"+10 0x{COST2_STUB | 1:08X}, +14 0x{DECL_STUB | 1:08X}}}")
            check(CLS2_DROP_PHANTOM not in c2, f"D  phantom 0x{CLS2_DROP_PHANTOM:04X} dropped from cls2 (count-neutral)")
            check(all(c2[i] <= c2[i + 1] for i in range(CLS2_COUNT - 1)), "D  cls2 still sorted")
            if c2.count(TEMPLATE_CID) == 1:
                check(struct.unpack_from("<6I", ov, _off(CLS2_BASE + c2.index(TEMPLATE_CID) * CLS2_STRIDE)) == ZEPH_CLS2,
                      "D  the Zephyrus template's cls2 record is untouched")
            else:
                check(False, "D  Zephyrus lost his cls2 record")
            check(all(u32(s) == w for s, w in ((0x021F059C, 0x1B20), (0x021F05A0, 0x20B9), (0x021F05A4, 0x241C))),
                  "D  0x021F04FC's cid triple untouched (the gate stub bypasses it instead)")

            check(bytes(ov[_off(SWITCH_HOOK):_off(SWITCH_HOOK) + 4]) == _bl(SWITCH_HOOK, ARM_STUB),
                  f"H  0x{SWITCH_HOOK:08X} = BL 0x{ARM_STUB:08X}")
            check(bytes(ov[_off(ARM_STUB):_off(ARM_STUB) + ARM_STUB_LEN]) == arm_stub(),
                  f"H  the {ARM_STUB_LEN} B ov3 switch stub matches the rebuild")
            check(struct.unpack_from("<3H", ov, _off(SWITCH_HOOK + 4)) == (0xD100, 0xE1EC, 0xE269),
                  "H  0x021D14E6/E8/EA (bne / Ojamagic / default) are untouched")
            for cid_, want_leaf, lbl in ((DONOR_CID, DW_ARM, "the donor"),
                                         (OJAMAGIC_CID, 0x021D18C4, "Ojamagic 0x1946"),
                                         (0x1B3E, DW_ARM, "Kahkki"),
                                         (0x1969, DW_ARM, "Goldd"),
                                         (0x1965, DW_ARM, "Beiige")):
                check(_route(bytes(ov), cid_) == want_leaf, f"H  {lbl} still routes to 0x{want_leaf:08X}")

            for blob, addr, label in ((filt_stub(), FILT_STUB, "E  candidate filter"),
                                      (gate_stub(), GATE_STUB, "F  offer gate"),
                                      (res_stub(),  RES_STUB,  "G  resolver"),
                                      (decl_stub(), DECL_STUB, "I  target declaration"),
                                      (res2_stub(), RES2_STUB, "J  resolver dispatcher"),
                                      (filt2_stub(), FILT2_STUB, "K  filter dispatcher"),
                                      (gate2_stub(), GATE2_STUB, "M  activation condition"),
                                      (cost2_stub(), COST2_STUB, "N  cost dispatcher")):
                effect_verify.assert_thumb1_only(blob, addr)
                check(ov5_cave.read_cave(rom, addr, len(blob)) == blob, f"{label} @0x{addr:08X}: {len(blob)} B match the rebuild")

            try:
                lst = _assert_arm9_setcode(rom)
                check(True, f"G  Dark World set-code list still {len(lst)} sorted entries and contains the donor 0x{DONOR_CID:04X} "
                            f"(never written by this patch)")
            except AssertionError as e:
                check(False, f"G  Dark World set-code list: {e}")

            _fid, pac_data, archive = _open_pac(rom)
            target_off, card_index = _find_prop(bytes(pac_data), archive, DONOR_CID)
            f = GC.decode_entry(pac_data[target_off:target_off + 8])
            check(f["level"] == NEW_LEVEL and f["real_atk"] == NEW_ATK and f["real_def"] == NEW_DEF
                  and f["attribute"] == NEW_ATTRIBUTE and f["race"] == NEW_RACE and f["card_type"] == "Effect Monster",
                  f"A  card_prop lvl={f['level']} atk={f['real_atk']} def={f['real_def']} {f['attribute']}/{f['race']} type={f['card_type']}")

        return Compiled(stubs=tuple(stubs), installs=(install,), checks=(check_fn,))


grapha_effects = graveyard_special_summon_by_returning_dark_world_monster_to_hand_discard_trigger_destroy_opponent_card_then_look_at_random_hand_card

SPEC = card(0x1961, grapha_effects())

PROPS = card_props("DARK", "Fiend", level=8, atk=2700, defense=1800)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_grapha.nds")

# Names the KB proofs and conscription_c3 read from this module (verbatim from the original).
from otn_enhanced.effects import ov5_cave  # noqa: E402
from otn_enhanced.rom.pac import parse_pac  # noqa: E402
from otn_enhanced.asm.effect_builder import EffectBuilder, Reg, R0, R1, R2, R3, R4, R5, R6, R7  # noqa: E402
from otn_enhanced.effects.common import ov3_off as _off  # noqa: E402

SRC = "data/over_the_nexus/working/rom.nds"            # clean (AP-fixed) EU base ROM
OUT = "data/over_the_nexus/working/rom_grapha.nds"     # single-card test ROM

DONOR_CID = 0x1961          # Zure, Knight of Dark World (keep-cid rule)
TEMPLATE_CID = 0x241C       # Blackwing - Zephyrus the Elite -- asserted, never written

from otn_enhanced.effects.common import ARM9_BASE
# ARM9 "Dark World" set-code list -- ASSERTED, never written.  Set code 0x0F,
# thunk 0x020238B5 (pointer table 0x0209D0D8 index 0x0F), 16 sorted entries.
DW_LIST, DW_LIST_COUNT = 0x0209CA06, 16
DW_THUNK_SLOT = 0x0209D0D8 + 0x0F * 4
DW_THUNK = 0x020238B5

# ---------------------------------------------------------------------------
# PART C -- the GY-action registry row
# ---------------------------------------------------------------------------
# 0x0228DDF8, 60 rows x 0x10 B: {u32 cid, u32 zone, u32 check_fn, u32 post_fn}.
# UNSORTED and linear-scanned with a hard-coded `cmp rX,#0x3C`, so a row is
# claimed IN PLACE -- no shifting, inherently count-neutral.
GYACT_BASE, GYACT_COUNT, GYACT_STRIDE = 0x0228DDF8, 0x3C, 0x10
GYACT_ZONE_GY = 0x0E
GYACT_CHECK, GYACT_POST = 0x0224C591, 0x0224C6C1     # the 45-row GY-EFFECT family
# Row 15 already carries EXACTLY the shape we need with a phantom cid: 0x0EB2 has
# no card_prop record, so its membership is inert and no card can ever reach it.
GYACT_ROW = 15
GYACT_DROP_PHANTOM = 0x0EB2

# ---------------------------------------------------------------------------
# PART D -- the cls2 record
# ---------------------------------------------------------------------------
CLS2_BASE, CLS2_COUNT, CLS2_STRIDE = 0x02275C04, 0x2B9, 0x18
ZEPH_RESOLVER = 0x02230EBD    # +04 -- ⚠️ NOT reusable, see THE 400-DAMAGE TRAP; asserted
                              #     intact so Zephyros keeps his own resolver
ZEPH_COST     = 0x021EB1B1    # +10, the shared bounce-cost machine
# Zephyrus's own record, asserted intact so a future edit to the template is loud.
ZEPH_CLS2 = (0x241C, 0x02230EBD, 0x021E454D, 0x021F44D9, 0x021EB1B1, 0x00000000)
# Phantom 0x1A86: no card_prop record, owns exactly ONE cls2 row (index 219), and
# that row is its ONLY aligned occurrence anywhere in overlay 3, so dropping it
# cannot disturb anything.  It is the nearest unclaimed phantom to the donor's
# insert point.  Registered in check_allocations.PHANTOM_CLAIMS as cls2_table.
CLS2_DROP_PHANTOM = 0x1A86

# ---------------------------------------------------------------------------
# PART E/F -- the ov5 stubs
# ---------------------------------------------------------------------------
FILT_STUB, FILT_RESERVE = ov5_cave.CAVE_GRAPHA_FILT, 0x50
GATE_STUB, GATE_RESERVE = ov5_cave.CAVE_GRAPHA_GATE, 0xB0
RES_STUB,  RES_RESERVE  = ov5_cave.CAVE_GRAPHA_RES, 0x50
# ---- CLAUSE 2 ------------------------------------------------
DIAG_BLOCK  = ov5_cave.CAVE_GRAPHA_DIAG
DIAG_RESERVE = 0x40
DECL_STUB, DECL_RESERVE = ov5_cave.CAVE_GRAPHA_DECL, 0x40
RES2_STUB, RES2_RESERVE = ov5_cave.CAVE_GRAPHA_RES2, 0x60
FILT2_STUB, FILT2_RESERVE = ov5_cave.CAVE_GRAPHA_FILT2, 0x50
DIAG2_BLOCK, DIAG2_RESERVE = ov5_cave.CAVE_GRAPHA_DIAG2, 0x40
GATE2_STUB, GATE2_RESERVE = ov5_cave.CAVE_GRAPHA_GATE2, 0x60
COST2_STUB, COST2_RESERVE = ov5_cave.CAVE_GRAPHA_COST2, 0x40

# *** MEASURED (round 2 savestates rom_grapha_test.ml2/.ml3, taken
# AFTER a discard fully resolved): the resolver was NEVER entered on the discard
# path -- "+04 entries with event != 0" == 0, and the +04/+14 counts (4 and 2) are
# exactly two clause-1 activations at two phases each.  So clause 2 was not being
# mis-routed; IT WAS NEVER OFFERED. ***
#
# dispatch.cls_slot_roles: +0C slot3 is the ACTIVATION CONDITION and returns a
# CODE -- 0 = cannot activate, 1 = activatable if slot2 finds a target, >=2 =
# activatable unconditionally -- and +10 slot4 is the COST / activation-procedure
# step.  Both are driven by the activation state machine 0x02217F80, and BOTH of
# Grapha's carry clause 1's answers: +0C is clause 1's GY-offer gate (which
# legitimately returns 0 for a discard) and +10 is the bounce-cost machine.  That
# is event.optional_trigger_is_record_shape's COMPOSITION TRAP, verbatim: "one cls
# record cannot be half-optional ... must point +0C/+10 at stubs that branch on
# the descriptor, exactly as its resolver already branches on desc[+3]".
#
# THE BRANCH KEY IS desc[+3], THE ZONE (the cls3 descriptor fact: [+0] cid,
# [+2] side, [+3] zone, [+4] index, [+5] record class -- the first diagnostic
# recorded [+4] and [+5] by mistake and got index 0 / class 2).  The discard arm
# 0x021D185C gates on SOURCE ZONE == 0x0B (the hand), so the trigger descriptor
# should carry 0x0B while clause 1's carries the Graveyard.
# ⚠️ WRITTEN IN THE SAFE DIRECTION: clause 2 only when desc[+3] == 0x0B, clause 1
# otherwise.  If the trigger descriptor turns out to carry something else, clause
# 2 stays inert and CLAUSE 1 -- confirmed working again this round -- is untouched.
# *** THE DISCRIMINATOR, FOUND BY DECODING THE EVENT-POST PRIMITIVE 0x021D32A0. ***
# That function unpacks the packed event word into the 0x24-byte descriptor every
# slot receives, and the unpacking is:
#     strh r5,[r0]                                    desc[+0] = event & 0xFFFF (cid)
#     movs r1,#0x1F ; lsls r1,#0x10 ; ands r1,r5
#     lsrs r1,#0x10 ; strb r1,[r0,#3]                 desc[+3] = (event >> 16) & 0x1F
#     movs r1,#0xE  ; lsls r1,#0x14 ; ands r1,r5
#     lsrs r1,#0x15 ; strb r1,[r0,#5]                 desc[+5] = (event >> 21) & 0x07
#
# So on an EVENT-POSTED descriptor, desc[+3] and desc[+5] are NOT a zone and a
# record class -- they are THE EVENT CODE, split across two fields (code bits 0..4
# and 5..7).  Three earlier rounds read desc[+3] == 0x0E as "the Graveyard" and
# built discriminators on it; it is actually the low half of code 0x4E.
#
# The event-post primitive has exactly FOUR call sites and their codes are
# 0x01 (0x0224B154), 0x4B (0x0224B1BE), 0x1F (0x0224B31C) and 0x4E (0x0224C6EE,
# THE GY-ACTION REGISTRY'S OWN post_fn = clause 1).  Their low five bits are
# 0x01 / 0x0B / 0x1F / 0x0E -- ALL DISTINCT -- so
#
#     desc[+3] == 0x0E  <=>  event code 0x4E  <=>  CLAUSE 1 (the Graveyard summon)
#
# is a one-byte test, available from r0 in EVERY slot including the filter, which
# receives no event and defeated every previous attempt.  It also explains the
# round-5 bug exactly: LR == 0x0224AE13 was matching CLAUSE 1, so the gate latched
# clause 2 for the Graveyard summon and Grapha destroyed instead of summoning.
GY_ACTION_CODE_LOW5 = 0x0E    # 0x4E & 0x1F      -> desc[+3]
GY_ACTION_CODE_HIGH3 = 2      # (0x4E >> 5) & 7  -> desc[+5]
# ⚠️⚠️ ROUND 8 -- THE ABOVE TWO BYTES DO NOT DISCRIMINATE ANYTHING.
# THE DISCARD TRIGGER POSTS EVENT CODE 0x4E TOO.  Disassembling the whole of the
# relocation applier 0x021D1300 (the function PART H's switch lives in) down to
# its posting site proves it end to end -- event.discard_trigger_posts_the_same_0x4E:
#
#   * the per-cid switch at 0x021D1392 is reached ONLY when KIND == 0x0E
#     (`LDR R0,[SP,#0x30] ; CMP R0,#0x0E ; BEQ 0x021D1392 ; BL 0x021D1B98`, where
#     the BL is a LONG BRANCH past the switch, not a call);
#   * the Dark World arm 0x021D185C only sets the result flag [sp+0x14];
#   * every arm converges on ONE post site, 0x021D1D56, which builds
#         event = cid | (KIND << 16) | (1 << 22) | ((arg0 & 0x3F) << 25) | (side << 31)
#     and calls the register-prim 0x021D3168.
#
# So the discard post carries desc[+3] = KIND = 0x0E and desc[+5] = 2 (bit 22 is
# HARDCODED) -- i.e. 0x0E | (2 << 5) == 0x4E, byte-identical to clause 1's.  ⚠️ THIS
# ALSO REFUTES ROUND 7's HEADLINE: reading (0x0E, 2) on every descriptor was taken
# as proof the discard had never fired, when it is exactly what a FIRING discard
# posts.  No refinement of a desc[+3]/desc[+5] test can work.
#
# ⭐ desc[+4] IS THE DISCRIMINATOR, AND IT IS FREE.  The arm demands
# `[sp+0x18] != 0`, which means arg0 == 0x1F EXACTLY, so the discard post's
# desc[+4] = arg0 = 0x1F.  Clause 1's post 0x0224C6EE goes through the near-twin
# primitive 0x021D32A0, which NEVER STORES [+4] at all -- and both primitives
# zero-fill the 0x24-byte descriptor first with 0x0209A080, a proven memset -- so
# the GY offer's desc[+4] is 0.
DISCARD_CODE_MID6 = 0x1F      # desc[+4] on the DISCARD post; the GY offer leaves it 0
ALWAYS_ACTIVATABLE = 2        # what 0x0224A114 (`movs r0,#2 ; bx lr`) returns

# The two native halves clause 2 reuses, both confirmed by the 3DS row for Grapha
# (dispatch.threeds_discard_trigger_registry): Grapha shares its filter with Goldd
# and its target declaration with Kahkki/Gren in the 3DS, and these are the NDS
# counterparts of exactly those two.
DESTROY_RES   = 0x02204899    # Kahkki/Gren cls2 +04: `bl 0x02204674 ; movs r0,#0`
GOLDD_FILTER  = 0x021DE7C9    # Goldd cls2 +08: "cards your opponent controls",
                              #   mask 0x00001472 (side bits 0b10, zone field 0x70)
TARGET_DECL   = 0x02234DA5    # Kahkki/Gren cls2 +14: the shared picker, param 0x119
# *** MEASURED, savestates rom_grapha_test.ml2/.ml3/.ml4. ***
# The first build guessed that the GY-action path could be recognised by the 0x4E
# event code that its post site 0x0224C6EE stamps into bits 16..23 of the event
# word.  THAT IS WRONG, and it regressed clause 1: the diagnostic block shows the
# resolver and the declaration are both entered with **r1 == 0x00000000** on the
# clause-1 path (phase 0x80, [0x0229AAFC+0x74] == 0), so the 0x4E test failed and
# both slots took the CLAUSE-2 arm -- the cost was paid and Kahkki's destroy ran
# instead of the summon.  The event word never reaches the resolver; r1 is simply
# 0, which matches the THREE invoker call sites that pass `movs r1,#0` literally
# (0x0221803E, 0x02228F92, 0x0225BCF8).
#
# So the test is now the measured one, in the SAFE direction: clause 1 iff the
# event is ZERO.  If the discard path also passes 0, clause 2 stays inert and
# clause 1 -- the in-game-confirmed clause -- still works.
GY_EVENT_IS_ZERO = True       # documentation only; the stubs compare r1 against 0
KAHKKI_CID, GREN_CID = 0x1B3E, 0x1B3F     # asserted intact, never written

# ---------------------------------------------------------------------------
# CLAUSE 3 -- "...then, if this card was discarded from your hand to your
# Graveyard by an OPPONENT's card effect, look at 1 random card in your
# opponent's hand, then, if it was a monster, you can Special Summon it to your
# side of the field."
#
# THE PAYLOAD IS NOT DUPLICATED HERE.  It lives in ov5 as two SHARED halves
# installed by conscription_c3 -- CAVE_C3_POST and CAVE_C3_FINISH -- and is
# IN-GAME CONFIRMED (dispatch.summon_from_opponent_hand_recipe) through
# the Conscription test card, which drives the very same two addresses from its own
# phase shell.  This patch supplies only the CONDITION and the phase chaining.
#
# THE CONDITION is dispatch.opponent_effect_discard_test, read off Sillva 0x1968's
# resolver 0x0221FAA0 and already SHIPPED by snoww as its clause-2 slot5 gate
#.  Both facts come out of the SAME descriptor:
#     desc[+0x20]  the packed card word the relocation applier posted
#     desc[+0x02]  the ACTING side
#     bit 18 of the word MUST DIFFER from desc[+2]  -> by an OPPONENT's effect
#     bit  9 of the word MUST EQUAL  desc[+2]       -> from YOUR hand
# ⚠️ desc[+0x20] exists because 0x021D3168 stores its THIRD argument -- the packed
# word itself -- there (event.discard_trigger_posts_the_same_0x4E).  An earlier pass
# traced only the event word, concluded the acting side never reached the descriptor,
# and called clause 3 blocked; it is not.
#
# THE CHAINING.  Clause 2's arm is today a single call to Kahkki/Gren's destroy
# 0x02204899, which returns 0 = done.  Clause 3 turns that arm into a two-phase
# machine on the SAME phase values the shared payload already uses, so no phase
# translation is needed:
#     phase 0x80  destroy (clause 2), then C3a; if it passes, post the pick and
#                 return 0x7F, else return 0 exactly as before
#     phase 0x7F  run the shared finish half, return 0
C3_POST = ov5_cave.CAVE_C3_POST | 1       # (desc) -> 1 if the pick was posted
C3_FINISH = ov5_cave.CAVE_C3_FINISH | 1   # (desc) -> the look-at + conditional summon
C3_ARM, C3_ARM_RESERVE = ov5_cave.CAVE_GRAPHA_C3, 0xA0
C3_POST_STUB, C3_POST_RESERVE = ov5_cave.CAVE_C3_POST, 0x60
C3_FIN_STUB, C3_FIN_RESERVE = ov5_cave.CAVE_C3_FINISH, 0xE0
C3_DIAG, C3_DIAG_RESERVE = ov5_cave.CAVE_C3_DIAG, 0x40

# the engine entry points the two SHARED halves call.  Thumb bit set: all BLX targets.
HAND_COUNT  = 0x0229ACA0      # == STATE_A + 0x0C, the HAND COUNT
EFFECT_CTX  = 0x0229DE94      # shared effect-context block; +6 u16 = the chosen index
PEEK_POST   = 0x022599F9      # (opponent, 0) -> post "look at 1 random card", kind 5
REVEAL      = 0x021D2599      # (side, ref) -> the actual look-at
IS_MONSTER  = 0x02029E61      # (cid) -> is this cid a monster
MAY_SUMMON  = 0x021BA685      # ⚠️ A PREDICATE (side, cid, ref, ZONE) -> 0/1.  It summons
                              # NOTHING; every path ends movs r0,#1 / movs r0,#0.  Calling
                              # it as if it were the action cost one in-game test.
SS_ALLOWED  = 0x021AD871      # (side) -> may this player SS now.  ⚠️ Returns a truthy
                              # COUNT (measured 5), never a boolean -- test against ZERO.
SUMMON      = 0x02269315      # THE ACTUAL SUMMON: (side, SLOT POINTER, 1, 0).  r1 is a
                              # POINTER to the card-word slot, not a cid/ref pair.

# ---------------------------------------------------------------------------
# PART H -- admit the donor to the Dark World EFFECT-DISCARD arm (overlay-3)
# ---------------------------------------------------------------------------
# The per-cid chain 0x021D1392 routes cids to relocation arms.  Traced with a
# register simulator: the donor 0x1961 reaches the terminal node 0x021D14E2
# with r1 = 0x1969 and falls to the DEFAULT leaf 0x021D19C0, while the native
# Dark World monsters reach the arm 0x021D185C.  The node is
#     0x021D14E2  subs r1,#0x23      ; r1 = 0x1946 (Ojamagic)
#     0x021D14E4  cmp  r5,r1
#     0x021D14E6  bne  0x021D14EA    ; -> default
#     0x021D14E8  b    0x021D18C4    ; Ojamagic's arm  (BRANCH TARGET, must survive)
#     0x021D14EA  b    0x021D19C0    ; default
# Nothing in overlay 3 branches to 0x021D14E2 or 0x021D14E4 (asserted), so those
# two halfwords are replaced by a BL to ARM_STUB, which reproduces the node's
# arithmetic and flags for every other cid and long-branches OUR cid into
# 0x021D185C.  0x021D14E6/E8/EA are left untouched.
#
# ⚠️ THE STUB MUST LIVE IN OVERLAY 3, NOT ov5: this is a SHARED path -- every
# effect discard of every card runs it -- and a puzzle loads overlay 41 over the
# ov5 cave, so an ov5 target here would freeze the game (mem.ov5_ov41_share_base).
SWITCH_HOOK = 0x021D14E2
SWITCH_HOOK_NATIVE = bytes.fromhex("23398d42")     # subs r1,#0x23 ; cmp r5,r1
SWITCH_R1_ON_ENTRY = 0x1969        # asserted: the node's live base register
OJAMAGIC_CID = 0x1946              # = r1 - 0x23, the node's native occupant
DW_ARM = 0x021D185C                # the effect-discard arm (source zone 0x0B + kind 0)
# Two ADJACENT 8-byte ov3 dead blocks (phantom cids 0x19D1 / 0x19D3), both wholly
# unclaimed in the ledger, giving exactly the 16 bytes needed.  Their only inbound
# branches (0x021B4FEE -> 0x021B594A, 0x021B4FD4 -> 0x021B5952) are from those
# phantoms' own dead arms, which is why the blocks are classified free at all --
# the same property snoww's 0x021B56B8 relies on.
ARM_STUB = 0x021B594A
ARM_STUB_LEN = 16
ARM_STUB_NATIVE = bytes.fromhex("00210398795e08e021980121084200d1")



# engine entry points the stubs call (Thumb bit set where they are BLX targets)
ZONE_CID      = 0x021A36ED    # (side, zone) -> cid at that zone
HAS_DW        = 0x020238B5    # (cid) -> is this cid in the Dark World set-code list
ZONE_PRED     = 0x021D6E41    # (src_desc, cand_side, cand_zone, mask) -> bool
# ⚠️ Zephyros's own mask is 0x00208075, and its zone-class field (bits 4-6) is 0x70 =
# NO ZONE RESTRICTION -- correct for him, because his printed cost is "return 1 face-up
# CARD you control".  Grapha's is "1 'Dark World' MONSTER", and FIVE of the sixteen
# members of the Dark World set-code list are Spells/Traps (Dark World Lightning 0x1970,
# Gateway to Dark World 0x1973, Dark World Dealings 0x1B5A, The Gates of Dark World
# 0x1C8B, Dark World Grimoire 0x1D25) -- so with 0x70 they would all be legal picks.
# The field is set to 0x10 instead, Genex Ally Birdman's value, whose arm is
# `cmp r5,#5 ; blt continue` = MONSTER ZONES ONLY (and matches the 3DS filter's own
# `cmp r4,#4 ; bgt reject`).  Bit 21 is KEPT: its arm is the candidate-level version of
# "the cost frees the zone it needs".
GRAPHA_MASK   = 0x00208015
ZEPH_MASK     = 0x00208075    # asserted intact, never written
# the resolver's own callees, transcribed into RES_STUB minus the damage phase
RES_ENTER     = 0x021D28A5    # (desc, phase) -- chain-depth push,  [0x0229AB7C+0x28]++
RES_BODY      = 0x0220731D    # (desc, arg1)  -- the actual Special Summon
RES_LEAVE     = 0x021D2965    # (desc, phase) -- chain-depth pop,   [0x0229AB7C+0x28]--
DAMAGE_PRIM   = 0x021CFBC8    # (desc, side, amount) -- what phase 0x7F called with 400
STATE_PHASE   = 0x0229AAFC    # [+0x70] = the resolver phase
RIDER_GATE    = 0x021A14E9    # (side, 0xB, cid, 5) -- 0x021F44D8's prologue gate
ZONE_INDEX    = 0x021A2511    # (side, desc[+0xC]) -> index, <0 = fail
ZONE_CHECK    = 0x021A2619    # (ptr) -> bool          (0x021F04FC's second gate)
CHAIN_PROBE   = 0x0224AF7D    # (desc) -> bool         (the escape hatch)
FREE_ZONE     = 0x021B9ECD    # (side) -> bool = 0x021B9708(side, 8, 0), THE TRIPLE'S
                              #   BRANCH: no free-zone precondition, cid-less
GY_FINAL      = 0x021BA441    # (desc) -> bool         (0x021F04FC's tail)
STATE_A       = 0x0229AC94    # zone-record array base
STATE_A_SIDE  = 0x00000B3C    # per-side stride
STATE_A_OFF   = 0x0000055C    # the sub-array 0x021F0522 adds
STATE_B       = 0x0229AB7C    # the [+0x18] escape-hatch flag

# ---------------------------------------------------------------------------
# PART A/B -- the visible card
# ---------------------------------------------------------------------------
NEW_ATTRIBUTE = "DARK"       # unchanged from the donor
NEW_RACE = "Fiend"           # unchanged from the donor
NEW_LEVEL = 8
NEW_ATK = 2700
NEW_DEF = 1800
NEW_CARD_TYPE = 3            # Effect Monster (the donor is 1 = Normal Monster);
                             # event.promoted_vanilla_cardprop_is_correct
# The donor's English name slot is 26 B and "Grapha, Dragon Lord of Dark World"
# is 33 B.  Slots are a HARD ceiling (donor.name_blob_has_no_slack: no trailing
# padding, no unreferenced strings, the spare card_indx entry is a zero-length
# sentinel), so the name is truncated -- chosen by the user.  It still
# contains the literal "Dark World" so an in-game name search finds it, and NO
# engine behaviour depends on it: Dark World membership is the cid list, not the
# name.
NEW_NAME = b"Grapha, Dark World Lord"
NEW_DESC = (b"You can Special Summon this card from your GY by returning 1 other "
            b"Dark World monster you control to the hand.")
from otn_enhanced.data.card_stats import TEXT_LANGS


def _keys(ov: bytearray, base: int, count: int, stride: int, wide: bool) -> list[int]:
    fmt = "<I" if wide else "<H"
    return [struct.unpack_from(fmt, ov, _off(base + i * stride))[0] for i in range(count)]


def _insert_sorted(ov: bytearray, base: int, count: int, stride: int, fmt: str,
                   record: tuple, drop_cid: int, label: str, wide: bool) -> None:
    """Count-neutral sorted insert: delete the phantom row, shift, write *record*."""
    keys = _keys(ov, base, count, stride, wide)
    new_cid = record[0]
    if new_cid in keys:
        print(f"{label}: 0x{new_cid:04X} already present (idempotent) -- skipped")
        return
    assert drop_cid in keys, f"{label}: phantom 0x{drop_cid:04X} not found -- table already edited?"
    dst = keys.index(drop_cid)
    pos = sum(1 for k in keys if k < new_cid)
    if pos > dst:
        blk = bytes(ov[_off(base + (dst + 1) * stride):_off(base + pos * stride)])
        ov[_off(base + dst * stride):_off(base + (pos - 1) * stride)] = blk
        pos -= 1
    elif pos < dst:
        blk = bytes(ov[_off(base + pos * stride):_off(base + dst * stride)])
        ov[_off(base + (pos + 1) * stride):_off(base + (dst + 1) * stride)] = blk
    struct.pack_into(fmt, ov, _off(base + pos * stride), *record)
    moved = abs(pos - dst)
    print(f"{label}: dropped phantom 0x{drop_cid:04X} @{dst}, inserted 0x{new_cid:04X} @{pos} "
          f"({moved} row{'' if moved == 1 else 's'} shifted, count {count} unchanged)")
    after = _keys(ov, base, count, stride, wide)
    assert all(after[i] <= after[i + 1] for i in range(count - 1)), \
        f"{label}: table lost its sort order"


def _bl(site: int, target: int) -> bytes:
    """Encode a 32-bit ARMv4T Thumb BL from *site* to *target*."""
    offset = (target - (site + 4)) & 0x7FFFFF
    return struct.pack("<HH", 0xF000 | ((offset >> 12) & 0x7FF),
                       0xF800 | ((offset >> 1) & 0x7FF))

def _read_cstr(buf: bytes, start: int) -> bytes:
    return buf[start:buf.index(b"\x00", start)]


def _iter_paths(folder, prefix=""):
    """Yield every file path inside an ndspy filename folder tree."""
    for f in getattr(folder, "files", []) or []:
        yield f"{prefix}{f}"
    folders = getattr(folder, "folders", []) or []
    items = folders.items() if isinstance(folders, dict) else folders
    for item in items:
        if isinstance(item, tuple) and len(item) >= 2:
            yield from _iter_paths(item[1], prefix=f"{prefix}{item[0]}/")


def _open_pac(rom):
    """Return (file_id, mutable bin2.pac bytes, parsed archive)."""
    pac_path = next((p for p in _iter_paths(rom.filenames)
                     if p.lower().endswith("bin2.pac")), None)
    if pac_path is None:
        raise RuntimeError("bin2.pac not found in ROM")
    fid = rom.filenames.idOf(pac_path)
    data = bytearray(rom.files[fid])
    return fid, data, parse_pac(bytes(data), pac_path)


def _find_prop(pac_data: bytes, archive, cid: int) -> tuple[int, int]:
    """Return (absolute offset, card_prop index) of *cid*'s record."""
    cpf = next((f for f in archive.files
                if f.get_clean_name().lower() == "card_prop.bin"), None)
    if cpf is None:
        raise RuntimeError("card_prop.bin not found in bin2.pac")
    body_start = cpf.address + 8                       # records follow an 8-byte header
    for i in range((cpf.size - 8) // 8):
        off = body_start + i * 8
        if int.from_bytes(pac_data[off:off + 8], "little") & 0x3FFF == cid:
            return off, i
    raise RuntimeError(f"card_id 0x{cid:04X} not found in card_prop.bin")


def _place_string(pac_data: bytearray, file_base: int, file_size: int,
                  old_off: int, new_bytes: bytes, pad_cursor: dict) -> int | None:
    """Write *new_bytes* for the string at *old_off*, keeping the file the SAME size."""
    old_str = _read_cstr(pac_data, file_base + old_off)
    if len(new_bytes) <= len(old_str):
        slot = len(old_str)
        abs_off = file_base + old_off
        pac_data[abs_off:abs_off + slot + 1] = new_bytes + b"\x00" * (slot + 1 - len(new_bytes))
        return old_off
    need = len(new_bytes) + 1
    # *** RELOCATION DISABLED -- see notes/card-text-blob-findings.md. ***
    # This used to scavenge the file's "trailing zero padding" by walking BACK from
    # the end over NUL bytes. On a blob re-emitted in index order by
    # card_text.rebuild_blobs, a language whose trailing entries are empty strings
    # (Korean) is a long NUL run, so that walk strides back over real strings and
    # lands on ANOTHER CARD'S TERMINATOR, fusing two cards' names (measured on
    # snoww's identical copy, chain step 30). Nothing needs relocation any
    # more: every renamed card gets its full printed text from
    # card_text.apply_to_rom, which re-emits the whole blob in index order.
    return None                                            # doesn't fit -- keep the donor's text


# ---------------------------------------------------------------------------
# PART E -- the candidate filter (cls2 +08)
# ---------------------------------------------------------------------------
def filt_stub(base: int = None) -> bytes:
    """(r0 = source desc, r1 = cand side, r2 = cand zone) -> 0 reject / nonzero accept.

    The two tests the 3DS has and the NDS's Zephyrus lacks, then Zephyrus's own
    generic predicate with his own mask:

        cid = 0x021A36EC(cand_side, cand_zone)      ; the card in that zone
        if cid == DONOR_CID:      reject            ; except "Grapha"
        if !0x020238B4(cid):      reject            ; must be a "Dark World" card
        return 0x021D6E40(src_desc, cand_side, cand_zone, 0x00208075)

    Every external call is `LDR Rn,=target|1 ; BLX Rn` rather than a long BL: BLX
    clobbers LR, which is why the original LR is pushed and the stub returns via
    POP {..., PC} (thumb.pop_into_lr_footgun).
    """
    base = FILT_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.insn("ADD", "R6, R2, #0x0")
    b.call_addr(ZONE_CID, R5, R6, via=R3)
    b.ldr_const(1, DONOR_CID)
    b.insn("CMP", "R0, R1")
    b.insn("BEQ", "reject")
    b.call_addr(HAS_DW, via=R3)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "reject")
    b.call_addr(ZONE_PRED, R4, R5, R6, GRAPHA_MASK, via=R7)
    b.insn("B", "out")
    b.label("reject")
    b.insn("MOV", "R0, #0x0")
    b.label("out")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return b.assemble(base, pad="nop")


# ---------------------------------------------------------------------------
# PART G -- the resolver (cls2 +04), Zephyros's minus his 400 LP self-damage
# ---------------------------------------------------------------------------
def res_stub(base: int = None) -> bytes:
    """(r0 = desc, r1 = arg1) -> next phase.  0x02230EBC with phase 0x7F deleted.

    THE 400-DAMAGE TRAP.  Zephyros's resolver is a 3-phase machine on
    [0x0229AAFC+0x70], and its phase 0x7F is nothing but

        0x02230EEC  ldrb r1,[r5,#2]          ; side
        0x02230EEE  movs r2,#0x19
        0x02230EF0  lsls r2,r2,#4            ; r2 = 0x190 = 400
        0x02230EF2  bl   0x021CFBC8          ; inflict it
        0x02230EF6  movs r0,#0x7e            ; -> phase 0x7E

    which is his printed text, not boilerplate: "Special Summon this card, and
    if you do, TAKE 400 DAMAGE".  Grapha has no such clause.  Because 0x7F does
    nothing else and falls straight to 0x7E, having phase 0x80 return 0x7E
    unconditionally -- instead of branching on [0x0229AAFC+0x74] -- is exactly
    equivalent MINUS the damage.  Everything else is transcribed verbatim,
    including passing the loaded phase in r1 to both chain-depth calls.
    """
    base = RES_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R3, R4, R5, LR}")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("ADD", "R4, R1, #0x0")
    b.ldr_const(3, STATE_PHASE)
    b.insn("LDR", "R1, [R3, #0x70]")
    b.insn("CMP", "R1, #0x7E")
    b.insn("BEQ", "ph7e")
    b.insn("CMP", "R1, #0x80")
    b.insn("BNE", "none")
    b.call_addr(RES_ENTER, R5, via=R3)
    b.call_addr(RES_BODY, R5, R4, via=R3)
    b.insn("MOV", "R0, #0x7E")
    b.insn("POP", "{R3, R4, R5, PC}")
    b.label("ph7e")
    b.call_addr(RES_LEAVE, R5, via=R3)
    b.label("none")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R3, R4, R5, PC}")
    return b.assemble(base, pad="nop")


# ---------------------------------------------------------------------------
# THE DISCRIMINATOR, emitted once and shared by all five dispatchers
# ---------------------------------------------------------------------------
def _clause2_test(b: EffectBuilder, reg: Reg, yes: str, no: str) -> None:
    """Branch to *yes* iff the descriptor in *reg* is the DISCARD post.

    All three fields are checked, though only desc[+4] separates the two paths:
    desc[+3]/desc[+5] are kept so that an unrelated event whose arg0 happens to
    be 0x1F cannot be mistaken for the trigger.

    ⚠️ THE FALL-THROUGH IS CLAUSE 1, which INVERTS the polarity of every round
    before this one.  Clause 1 is the in-game-confirmed clause, so anything not
    positively identified as the discard must behave exactly as it does today.
    The *no* label is emitted here; the caller's clause-1 arm follows it.
    """
    b.insn("LDRB", f"R0, [{reg!r}, #0x4]")
    b.insn("CMP", f"R0, #0x{DISCARD_CODE_MID6:02X}")
    b.insn("BNE", no)
    b.insn("LDRB", f"R0, [{reg!r}, #0x3]")
    b.insn("CMP", f"R0, #0x{GY_ACTION_CODE_LOW5:02X}")
    b.insn("BNE", no)
    b.insn("LDRB", f"R0, [{reg!r}, #0x5]")
    b.insn("CMP", f"R0, #{GY_ACTION_CODE_HIGH3}")
    b.insn("BEQ", yes)
    b.label(no)


# ---------------------------------------------------------------------------
# PART M -- cls2 +0C, the ACTIVATION-CONDITION dispatcher (ov5)
# ---------------------------------------------------------------------------
def gate2_stub(base: int = None) -> bytes:
    """(r0 = desc, r1 = arg1) -> activation code.  0 = no, >=2 = unconditionally.

    Clause 2 must answer 2 ("activatable unconditionally"), which is what the 3DS
    row pairs Grapha with (0x00404260 -> NDS 0x0224A115) and what stops slot2
    being consulted with the wrong clause's filter.  Clause 1 keeps its own gate.
    """
    base = GATE2_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, LR}")
    b.insn("ADD", "R5, R0, #0x0")
    b.insn("ADD", "R4, R1, #0x0")
    b.ldr_const(6, DIAG2_BLOCK)
    b.insn("LDR", "R0, [R6, #0x0]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R6, #0x0]")
    b.insn("LDRB", "R0, [R5, #0x4]")
    b.insn("STR", "R0, [R6, #0x4]")
    b.insn("LDR", "R1, [R6, #0xC]")
    b.insn("ORR", "R0, R1")
    b.insn("STR", "R0, [R6, #0xC]")
    b.insn("LDRB", "R0, [R5, #0x5]")
    b.insn("STR", "R0, [R6, #0x8]")
    _clause2_test(b, R5, "clause2", "c1")
    b.call_addr(GATE_STUB, R5, R4, via=R3)
    b.insn("STR", "R0, [R6, #0x28]")
    b.insn("POP", "{R4, R5, R6, PC}")
    b.label("clause2")
    b.insn("LDR", "R0, [R6, #0x10]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R6, #0x10]")
    b.insn("MOV", f"R0, #0x{ALWAYS_ACTIVATABLE:X}")
    b.insn("POP", "{R4, R5, R6, PC}")
    return b.assemble(base, pad="nop")


# ---------------------------------------------------------------------------
# PART N -- cls2 +10, the COST dispatcher (ov5)
# ---------------------------------------------------------------------------
def cost2_stub(base: int = None) -> bytes:
    """(r0 = desc, r1 = arg1).  Clause 1's bounce cost, or nothing for clause 2.

    ⚠️ Clause 2 MUST RETURN 1, NOT 0.  An absent slot4 is reported as 1 by the
    wrapper at 0x0224AE50, and returning 0 means "not done, call me again" --
    measured in-game as a hang with the slot entered 6,455 times.
    """
    base = COST2_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.ldr_const(6, DIAG2_BLOCK)
    b.insn("LDR", "R0, [R6, #0x1C]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R6, #0x1C]")
    b.insn("LDRB", "R0, [R4, #0x4]")
    b.insn("STR", "R0, [R6, #0x20]")
    _clause2_test(b, R4, "clause2", "c1")
    b.call_addr(ZEPH_COST, R4, R5, via=R3)
    b.insn("POP", "{R4, R5, R6, PC}")
    b.label("clause2")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, R6, PC}")
    return b.assemble(base, pad="nop")


# ---------------------------------------------------------------------------
# PART H -- the switch-node stub (overlay 3)
# ---------------------------------------------------------------------------
def arm_stub(base: int = None) -> bytes:
    """Reproduce the terminal node, and long-branch the donor into the DW arm.

        subs r1,#8       ; r1 = 0x1969 - 8   = 0x1961  (the donor)
        cmp  r5,r1
        beq  ours
        subs r1,#0x1b    ; r1 = 0x1961 - 0x1B = 0x1946 (Ojamagic) -- the value and
        cmp  r5,r1       ;   the flags the caller's `bne 0x021D14EA` expects
        bx   lr
   ours BL   0x021D185C  ; a 4-byte long jump; LR is dead here (the enclosing
                         ;   function returns by POPping PC, never via LR)

    Exactly 16 bytes, which is exactly what the two dead blocks provide.
    """
    base = ARM_STUB if base is None else base
    b = EffectBuilder()
    b.insn("SUB", "R1, #0x8")
    b.insn("CMP", "R5, R1")
    b.insn("BEQ", "ours")
    b.insn("SUB", "R1, #0x1B")
    b.insn("CMP", "R5, R1")
    b.insn("BX", "LR")
    b.label("ours")
    b.insn("NOP")
    b.insn("NOP")
    body = b.assemble(base, pad="nop")
    blob = bytearray(body[:12])                       # the six real instructions
    blob += _bl(base + 12, DW_ARM)                    # ours: BL the Dark World arm
    assert len(blob) == ARM_STUB_LEN, len(blob)
    return bytes(blob)


# ---------------------------------------------------------------------------
# PART I -- cls2 +14, the target declaration (ov5)
# ---------------------------------------------------------------------------
def decl_stub(base: int = None) -> bytes:
    """(r0 = desc, r1 = arg1) -> declare a target, or 1 = SKIP.

    Clause 2 targets ("target 1 card your opponent controls"); clause 1 must not.
    """
    base = DECL_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.ldr_const(6, DIAG_BLOCK)
    b.insn("LDR", "R0, [R6, #0x18]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R6, #0x18]")
    b.insn("LDRB", "R0, [R4, #0x4]")
    b.insn("STR", "R0, [R6, #0x1C]")
    _clause2_test(b, R4, "doit", "skip")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, R6, PC}")
    b.label("doit")
    b.insn("LDR", "R0, [R6, #0x28]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R6, #0x28]")
    b.call_addr(TARGET_DECL, R4, R5, via=R3)
    b.insn("POP", "{R4, R5, R6, PC}")
    return b.assemble(base, pad="nop")


# ---------------------------------------------------------------------------
# PART J -- cls2 +04, the resolver DISPATCHER (ov5)
# ---------------------------------------------------------------------------
def res2_stub(base: int = None) -> bytes:
    """(r0 = desc, r1 = event) -> next phase.  Clause 1's summon or clause 2's destroy.

    CAVE_GRAPHA_RES (clause 1, in-game confirmed) is byte-identical and simply
    called.
    """
    base = RES2_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.ldr_const(6, DIAG_BLOCK)
    b.insn("LDR", "R0, [R6, #0x0]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R6, #0x0]")
    b.insn("LDRB", "R0, [R4, #0x4]")
    b.insn("STR", "R0, [R6, #0x3C]")
    b.insn("LDRB", "R0, [R4, #0x5]")
    b.insn("STR", "R0, [R6, #0x34]")
    b.insn("LDRH", "R0, [R4, #0x0]")
    b.insn("STR", "R0, [R6, #0x38]")
    _clause2_test(b, R4, "clause2", "c1")
    b.call_addr(RES_STUB, R4, R5, via=R3)
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    b.label("clause2")
    b.call_addr(C3_ARM, R4, R5, via=R3)
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return b.assemble(base, pad="nop")


# ---------------------------------------------------------------------------
# PART P -- the two SHARED clause-3 halves (ov5)
#
# IN-GAME CONFIRMED through the Conscription test harness, which drives
# these very addresses from its own phase shell: it summoned Battle Ox 0x0FC0 out of
# the opponent's hand, with the slot pointer measured at 0x0229B8F8 == STATE_A +
# 1*0xB3C + 0x124 + 1*4.  See dispatch.summon_from_opponent_hand_recipe.
#
# ⚠️ THEY LIVE HERE, NOT IN THE HARNESS, because the harness never ships.  Grapha
# clause 3 calls them, so the module that ships has to be the one that writes them.
# ---------------------------------------------------------------------------
def c3_post_stub(base: int = None) -> bytes:
    """SHARED half 1.  (r0 = desc) -> 1 if the random pick was posted, else 0.

    Grapha clause 3 calls this from its OWN phase machine, so the phase test
    deliberately lives in the caller rather than here.
    """
    base = C3_POST_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, LR}")
    b.insn("ADD", "R5, R0, #0x0")
    b.ldr_const(4, C3_DIAG)
    b.insn("LDR", "R0, [R4, #0xC]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R4, #0xC]")
    b.insn("LDRB", "R0, [R5, #0x2]")
    b.insn("MOV", "R1, #0x1")
    b.insn("SUB", "R0, R1, R0")
    b.insn("AND", "R0, R1")
    b.insn("STR", "R0, [R4, #0x30]")
    b.ldr_const(2, HAND_COUNT)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "hc0")
    b.ldr_const(1, STATE_A_SIDE)
    b.insn("ADD", "R2, R2, R1")
    b.label("hc0")
    b.insn("LDR", "R1, [R2, #0x0]")
    b.insn("STR", "R1, [R4, #0x2C]")
    b.insn("CMP", "R1, #0x0")
    b.insn("BEQ", "empty")
    b.insn("LDRB", "R0, [R5, #0x2]")
    b.insn("MOV", "R1, #0x1")
    b.insn("SUB", "R0, R1, R0")
    b.insn("AND", "R0, R1")
    b.call_addr(PEEK_POST, R0, 0, via=R3)
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, PC}")
    b.label("empty")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, PC}")
    return b.assemble(base, pad="nop")


def c3_finish_stub(base: int = None) -> bytes:
    """SHARED half 2.  (r0 = desc).  The confirmed look-at + conditional summon.

    IN-GAME CONFIRMED 2026-08-28 as part of the Conscription harness -- see
    dispatch.summon_from_opponent_hand_recipe.  ⚠️ Two traps are baked in here:
    0x021BA684 is a PREDICATE whose answer must be tested, and 0x021AD870
    returns a truthy COUNT (measured 5), so both are tested against zero.
    """
    base = C3_FIN_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R5, R0, #0x0")
    b.ldr_const(4, C3_DIAG)
    b.insn("LDR", "R0, [R4, #0x10]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R4, #0x10]")
    b.insn("LDRB", "R0, [R5, #0x2]")
    b.insn("MOV", "R1, #0x1")
    b.insn("SUB", "R1, R1, R0")
    b.insn("MOV", "R0, #0x1")
    b.insn("AND", "R1, R0")
    b.ldr_const(2, STATE_A)
    b.insn("CMP", "R1, #0x0")
    b.insn("BEQ", "pb0")
    b.ldr_const(3, STATE_A_SIDE)
    b.insn("ADD", "R2, R2, R3")
    b.label("pb0")
    b.insn("MOV", "R3, #0x49")
    b.insn("LSL", "R3, R3, #0x2")
    b.insn("ADD", "R2, R2, R3")
    b.ldr_const(3, EFFECT_CTX)
    b.insn("LDRH", "R3, [R3, #0x6]")
    b.insn("STR", "R3, [R4, #0x14]")
    b.insn("LSL", "R3, R3, #0x2")
    b.insn("ADD", "R2, R2, R3")
    b.insn("STR", "R2, [R4, #0x34]")
    b.insn("LDR", "R6, [R2, #0x0]")
    b.insn("STR", "R6, [R4, #0x18]")
    b.insn("LSL", "R2, R6, #0x11")
    b.insn("LSR", "R2, R2, #0x1F")
    b.insn("ADD", "R1, R6, #0x0")
    b.insn("LSL", "R1, R1, #0x1")
    b.insn("LSR", "R1, R1, #0x18")
    b.insn("LSL", "R1, R1, #0x1")
    b.insn("ADD", "R7, R2, R1")
    b.insn("LDRB", "R0, [R5, #0x2]")
    b.call_addr(REVEAL, R0, R7, via=R3)
    b.insn("LSL", "R0, R6, #0x12")
    b.insn("LSR", "R0, R0, #0x12")
    b.insn("STR", "R0, [R4, #0x1C]")
    b.call("is_monster", via=R3)
    b.insn("STR", "R0, [R4, #0x20]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "done")
    b.insn("LDRB", "R0, [R5, #0x2]")
    b.insn("LDR", "R1, [R4, #0x1C]")
    b.insn("ADD", "R2, R7, #0x0")
    b.ldr_const(6, MAY_SUMMON)
    b.insn("MOV", "R3, #0xB")
    b.insn("BLX", "R6")
    b.insn("STR", "R0, [R4, #0x38]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "done")
    b.insn("LDRB", "R0, [R5, #0x2]")
    b.call_addr(SS_ALLOWED, via=R3)
    b.insn("STR", "R0, [R4, #0x3C]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "done")
    b.insn("LDRB", "R0, [R5, #0x2]")
    b.call_addr(FREE_ZONE, via=R3)
    b.insn("STR", "R0, [R4, #0x24]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "done")
    b.insn("LDR", "R0, [R4, #0x28]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R4, #0x28]")
    b.insn("LDR", "R1, [R4, #0x34]")
    b.insn("LDRB", "R0, [R5, #0x2]")
    b.call_addr(SUMMON, R0, R1, 1, 0, via=R4)
    b.label("done")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return b.assemble(base, pad="nop")



# ---------------------------------------------------------------------------
# PART O -- clause 2 + clause 3, the discard-path arm (ov5)
# ---------------------------------------------------------------------------
def c3_arm_stub(base: int = None) -> bytes:
    """(r0 = desc, r1 = event) -> the next phase.  Clause 2's destroy, then clause 3.

    Lives in its own cave slot because it does not fit inside CAVE_GRAPHA_RES2's
    0x60, and because keeping it separate means the clause-1 path is untouched
    bytes rather than untouched-by-inspection.

    Phase 0x80 destroys (clause 2, in-game confirmed 2026-08-28) and then applies
    CLAUSE 3's condition; phase 0x7F runs the shared finish half.  Both phase
    values are the ones the shared payload already uses, so nothing is translated.

    ⚠️ THE CONDITION IS SHIPPED CODE, NOT A NEW GUESS -- it is snoww's
    clause-2 slot5 gate verbatim (dispatch.opponent_effect_discard_test, itself
    read off native Sillva 0x1968), and Snoww clause 2 is in-game confirmed.
    Both facts come out of the one descriptor: desc[+0x20] is the packed card
    word, desc[+2] the acting side, bit 18 must DIFFER (an opponent's effect) and
    bit 9 must MATCH (from your hand).
    """
    base = C3_ARM if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.ldr_const(6, DIAG_BLOCK)
    b.ldr_const(0, STATE_PHASE)
    b.insn("LDR", "R0, [R0, #0x70]")
    b.insn("STR", "R0, [R6, #0x24]")
    b.insn("CMP", "R0, #0x7F")
    b.insn("BEQ", "c3fin")
    b.insn("LDR", "R0, [R6, #0x20]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R6, #0x20]")
    b.call_addr(DESTROY_RES, R4, R5, via=R3)
    b.insn("LDRB", "R3, [R4, #0x2]")
    b.insn("LDR", "R2, [R4, #0x20]")
    b.insn("ADD", "R1, R2, #0x0")
    b.insn("LSL", "R1, R1, #0xD")
    b.insn("LSR", "R1, R1, #0x1F")
    b.insn("CMP", "R3, R1")
    b.insn("BEQ", "c3no")
    b.insn("ADD", "R1, R2, #0x0")
    b.insn("LSL", "R1, R1, #0x16")
    b.insn("LSR", "R1, R1, #0x1F")
    b.insn("CMP", "R3, R1")
    b.insn("BNE", "c3no")
    b.insn("LDR", "R0, [R6, #0x2C]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R6, #0x2C]")
    b.call_addr(C3_POST, R4, via=R3)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "c3no")
    b.insn("MOV", "R0, #0x7F")
    b.insn("POP", "{R4, R5, R6, PC}")
    b.label("c3no")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, PC}")
    b.label("c3fin")
    b.insn("LDR", "R0, [R6, #0x30]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R6, #0x30]")
    b.call_addr(C3_FINISH, R4, via=R3)
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, PC}")
    return b.assemble(base, pad="nop")


# ---------------------------------------------------------------------------
# PART K -- cls2 +08, the filter DISPATCHER (ov5)
# ---------------------------------------------------------------------------
def filt2_stub(base: int = None) -> bytes:
    """(r0 = src desc, r1 = cand side, r2 = cand zone) -> 0 reject / nonzero accept.

    The filter receives no event, but it does receive the SOURCE DESCRIPTOR, and
    desc[+3] carries the posted event code -- which is what finally makes this
    slot decidable.  Clause 2 -> Goldd's "cards your opponent controls"
    0x021DE7C9 (the 3DS pairs Grapha with Goldd on this very slot).
    """
    base = FILT2_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("ADD", "R5, R1, #0x0")
    b.insn("ADD", "R6, R2, #0x0")
    b.ldr_const(7, DIAG_BLOCK)
    b.insn("LDR", "R0, [R7, #0x10]")
    b.insn("ADD", "R0, #0x1")
    b.insn("STR", "R0, [R7, #0x10]")
    b.insn("LDRB", "R0, [R4, #0x4]")
    b.insn("STR", "R0, [R7, #0x14]")
    _clause2_test(b, R4, "clause2", "c1")
    b.call_addr(FILT_STUB, R4, R5, R6, via=R3)
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    b.label("clause2")
    b.call_addr(GOLDD_FILTER, R4, R5, R6, via=R3)
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return b.assemble(base, pad="nop")


# ---------------------------------------------------------------------------
# PART F -- the "may this GY effect be offered" gate (cls2 +0C)
# ---------------------------------------------------------------------------
def gate_stub(base: int = None) -> bytes:
    """(r0 = desc, r1 = arg1) -> bool.  0x021F44D8 + 0x021F04FC, triple branch forced.

    Transcribed instruction-for-instruction from the two native functions, with
    exactly one deviation: where 0x021F04FC tests the source cid against the
    hard-coded triple {0x1B20, 0x20B9, 0x241C} and sends only those three to the
    cid-less free-zone check 0x021B9ECC, this stub goes there unconditionally --
    because it is only ever reached for the donor's own cid.  Everything the
    generic branch (0x021F0384) would add is a FREE-MONSTER-ZONE precondition,
    which is wrong for a card whose cost frees a zone.

    `arg1` is deliberately unused: 0x021F04FC forwards it only to 0x021F0384,
    the branch this stub never takes.
    """
    base = GATE_STUB if base is None else base
    b = EffectBuilder()
    b.insn("PUSH", "{R4, R5, R6, R7, LR}")
    b.insn("ADD", "R4, R0, #0x0")
    b.insn("LDRB", "R0, [R4, #0x2]")
    b.insn("LDRH", "R2, [R4, #0x0]")
    b.turnlog_query(R0, R2, 5, via=R7)
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "reject")
    b.insn("LDRB", "R0, [R4, #0x2]")
    b.insn("LDRH", "R1, [R4, #0xC]")
    b.call_addr(ZONE_INDEX, via=R7)
    b.insn("CMP", "R0, #0x0")
    b.insn("BLT", "reject")
    b.insn("LSL", "R0, R0, #0x2")
    b.insn("LDRB", "R3, [R4, #0x2]")
    b.insn("MOV", "R2, #0x1")
    b.insn("AND", "R3, R2")
    b.insn("MOV", "R2, #0x0")
    b.insn("CMP", "R3, #0x0")
    b.insn("BEQ", "side0")
    b.ldr_const(2, STATE_A_SIDE)
    b.label("side0")
    b.ldr_const(1, STATE_A)
    b.insn("ADD", "R2, R1, R2")
    b.ldr_const(1, STATE_A_OFF)
    b.insn("ADD", "R1, R2, R1")
    b.insn("ADD", "R0, R1, R0")
    b.call_addr(ZONE_CHECK, via=R7)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "reject")
    b.ldr_const(0, STATE_B)
    b.insn("LDR", "R0, [R0, #0x18]")
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "freezone")
    b.call_addr(CHAIN_PROBE, R4, via=R7)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "accept")
    b.label("freezone")
    b.insn("LDRB", "R0, [R4, #0x2]")
    b.call_addr(FREE_ZONE, via=R7)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "reject")
    b.call_addr(GY_FINAL, R4, via=R7)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "reject")
    b.label("accept")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    b.label("reject")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{R4, R5, R6, R7, PC}")
    return b.assemble(base, pad="nop")


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
