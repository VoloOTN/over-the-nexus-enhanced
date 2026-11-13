"""Azure-Eyes Silver Dragon (LIGHT / Dragon / Synchro Effect Monster / Level 9 / 2500 / 3000) on Ally of Justice Light Gazer 0x1E9C.

    1 Tuner + 1 or more non-Tuner Normal Monsters
    When this card is Special Summoned: Dragon monsters you control cannot be targeted or destroyed by card effects until the end of the
    next turn. Once per turn, during your Standby Phase: You can Special Summon 1 Normal Monster from your GY.
    (See card_text.CARD_TEXT[0x1E9C] for the full printed text.)
"""
from __future__ import annotations

import struct
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
from otn_enhanced.effects import ov5_cave
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import cave3
from dataclasses import dataclass
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class synchro_one_tuner_and_non_tuner_normal_monsters_on_special_summon_dragons_protected_standby_special_summon_normal_from_graveyard:
    """Azure-Eyes Silver Dragon (Ally of Justice Light Gazer 0x1E9C, an Extra Deck donor made a LIGHT Dragon Synchro Effect Monster): '1 Tuner +
    1 or more non-Tuner Normal Monsters. When this card is Special Summoned: Dragon monsters you control cannot be targeted or destroyed by
    card effects until the end of the next turn. Once per turn, during your Standby Phase: You can Special Summon 1 Normal Monster from your
    GY.' Standby registry row over phantom 0x16FE, cls1 record over 0x1C27, criteria row over 0x1ABE, the donor's stat-engine ATK arm
    neutralised, the Normal-only non-Tuner material gate (third-predicate hook), the on-SS Dragon protection (summon-trigger hook + the
    protection query link inside the affect predicate), and the donor dropped from the ARM9 Ally of Justice set-code list. Stubs are
    installed by the embedded apply_* functions into ov5. Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        import struct
        import ndspy.code
        import ndspy.rom
        from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.effects import cave3
        from otn_enhanced.cards import boggart_knight as boggart
        from otn_enhanced.effects.common import ov3_off as _off

        DONOR_CID = 0x1E9C          # Ally of Justice Light Gazer

        # ---------------------------------------------------------------------------
        # PART A -- effect registry (the Standby-Phase trigger)
        # ---------------------------------------------------------------------------
        # Stride 8, [resolver u32][cid u16][pad u16]. The section is walked LINEARLY and is
        # NOT sorted, so rewriting one row's cid in place is count-neutral and order-free.
        REG_BASE = 0x0228E1E0
        REG_ROW = 341                       # inside the Standby section (rows 293..428)
        REG_SECTION_LO = 293
        REG_SECTION_COUNT = 0x88            # the immediate at 0x02258378
        REG_STANDBY_RESOLVER = 0x02256F7D   # "1/turn, during your Standby Phase: you can ..."
        REG_DROP_PHANTOM = 0x16FE           # inert: no card_prop record, so the zone scan
                                            # in 0x02256F7C can never match it
        # Fallback rows carrying the same resolver with a phantom cid, if 0x16FE is ever
        # claimed by another patch: reg[316] 0x1338, reg[342] 0x18F8, reg[345] 0x1147,
        # reg[374] 0x11CF, reg[418] 0x11EA, reg[421] 0x0E9B.

        # ---------------------------------------------------------------------------
        # PART B -- cls1 (dispatcher event-class table 1)
        # ---------------------------------------------------------------------------
        CLS1_BASE = 0x022860D4
        CLS1_COUNT = 0x535          # 1333 records, stride 24 (hard-coded in find_event_handler)
        CLS1_STRIDE = 24
        # Captain Tenacious 0x1A03's slots, verbatim:
        #   +04 0x02207191  resolver -- a per-cid compare tree ending in
        #                   `bl 0x02204730(desc, r4, r5)`. Executed symbolically for the
        #                   donor: it takes the DEFAULT arm, r4=1 r5=2. r5 is the summon
        #                   POSITION MODE -- the same walk routes Silent Doom 0x14F7 (the
        #                   only one of the family printed "in face-up Defense Position")
        #                   to r5=1, and Swing of Memories / Captain Tenacious / Supervise
        #                   to r5=2. Default 2 = player chooses, which is exactly what
        #                   "Special Summon it" wants.
        #   +0C 0x021F03B5  activation condition -- the generic "is there a legal candidate
        #                   in a list zone" predicate.
        #   +10 0x021E50DD  the "you can" confirm slot (3-step state machine on [r6+0x7C]).
        #   +14 0x02235605  target declaration -- the OFF-FIELD list-zone template (the
        #                   on-field board template cannot reach the Graveyard).
        CLS1_NEW = (DONOR_CID, 0x02207191, 0x00000000, 0x021F03B5, 0x021E50DD, 0x02235605)
        # Phantom dropped to keep the count. 0x1C27 has NO card_prop record (so no instance
        # can ever carry the cid and the record is unreachable), owns exactly ONE cls1 row,
        # appears exactly ONCE as an aligned u32 anywhere in overlay 3 -- in that very row --
        # and is claimed by no other patch.
        CLS1_DROP_PHANTOM = 0x1C27
        CLS1_PHANTOM_BEFORE = (0x1C27, 0x022049C9, 0x021E1FF1, 0x0224A115, 0x00000000, 0x02234DD9)

        # ---------------------------------------------------------------------------
        # PART C -- criteria / populate registry
        # ---------------------------------------------------------------------------
        CRIT_BASE = 0x022713C4
        CRIT_COUNT = 1388
        CRIT_STRIDE = 12
        CRIT_FMT = "<HHIHH"         # {cid, aux, handler, flags, extra}
        # handler 0x0223DE05 + word 0x00010002 == "1 Normal Monster in your Graveyard".
        # All four NDS rows carrying that pair are printed "Special Summon 1 Normal Monster
        # from your Graveyard": Silent Doom 0x14F7, Soul Resurrection 0x17B7, Birthright
        # 0x1B65, Swing of Memories 0x1C58. The 3DS agrees independently (see the docstring).
        CRIT_NEW = (DONOR_CID, 0xFFFF, 0x0223DE05, 0x0002, 0x0001)
        CRIT_DROP_PHANTOM = 0x1ABE  # no card_prop; owns exactly one row; unclaimed
        CRIT_PHANTOM_BEFORE = (0x1ABE, 0xFFFF, 0x0223CBB1, 0x0004, 0x0001)

        # ---------------------------------------------------------------------------
        # PART D1 -- kill the donor's native continuous ATK gain
        # ---------------------------------------------------------------------------
        # Light Gazer is printed "This card gains 200 ATK for each LIGHT monster in your
        # opponent's Graveyard", and that IS implemented -- in the continuous stat-recompute
        # engine's per-cid compare tree (root 0x021B4C38: `movs r1,#2 ; ldrsh r2,[r7,r1]`,
        # so r2 = the cid).
        #
        # /!\ THE OBVIOUS EDIT IS WRONG. The word 0x1E9C at 0x021B53A8 is the PIVOT of an
        # ordered binary search, and the arms below it are `base +/- imm` off that same
        # register, so repointing the literal would mis-route every card in the subtree:
        #
        #     021B516E  ldr r0,=0x1E9C
        #     021B5170  cmp r2, r0
        #     021B5172  bgt 0x021B51EA     ; upper subtree
        #     021B5174  blt 0x021B517A     ; lower subtree -- and r0 is ITS base
        #     021B5176  bl  0x021B5B8C     ; cid == 0x1E9C -> Light Gazer's private leaf
        #
        # Instead retarget that ONE `bl` on the `==` arm, which only cid 0x1E9C can execute,
        # to the tree's default "no continuous bonus" terminal. Proved closed by executing
        # the tree for every cid 1..0x26FF before and after: EXACTLY ONE cid changes
        # terminal (0x1E9C), onto the default. The same sweep validates itself -- of the 126
        # cids on a non-default leaf, all 110 real cards are printed "gains ATK for each X"
        # (Swamp/Lava Battleguard, Maha Vailo, Insect Queen, Buster Blader, Dark Paladin,
        # Batteryman AA, Uria, ...), and Goka 0x236B lands on its own leaf, independently
        # confirming the KB's "Goka is this engine's template".
        STAT_ARM_SITE = 0x021B5176      # the `bl` on the cid == 0x1E9C arm
        STAT_ARM_OLD = 0x021B5B8C       # Light Gazer's bonus leaf (reached by NO other cid)
        STAT_ARM_NEW = 0x021B5E6E       # the default terminal: 9857 of 9975 cids reach it

        # ---------------------------------------------------------------------------
        # PART D2 -- drop the donor from the "Ally of Justice" set-code table
        # ---------------------------------------------------------------------------
        # Sorted 21-entry u16 cid table in ARM9, consulted from EXACTLY ONE site: the thunk
        # at 0x02023B70 (`ldr r1,=0x0209CB96 ; movs r2,#0x15 ; ldr r3,=0x02022E15 ; bx r3`).
        # The count is a hard-coded immediate and the table is packed against the Dragunity
        # table with a 0-byte gap, so it must stay 21 entries.
        #
        # There is NO phantom cid anywhere in 0x1E94..0x1E9F -- every one is a real card --
        # so the donor's slot cannot simply be overwritten with an inert cid.
        #
        # /!\ COMPOSITION -- THIS IS WHY THE OBVIOUS TWO FIXES BOTH FAIL.
        # elder_six_samurai PART E ALREADY EDITS THIS TABLE: it removes cid 0x1F1D by
        # shifting the tail left and DECREMENTING the count immediate 0x15 -> 0x14, and it
        # asserts the result is a STRICTLY sorted 20-entry set while hardcoding 21 as the
        # count it expects to find. So:
        #   * overwriting our slot with a DUPLICATE of a neighbour (0x1E93) leaves the array
        #     non-strictly sorted -> Elder's assertion trips when it runs after us;
        #   * removing our entry by shifting left and DECREMENTING the count leaves Elder
        #     finding 0x14 where it hardcodes 0x15 -> Elder trips again.
        # Both were tried; both abort the chain in one of the two orders.
        #
        # What works is to shift the tail left past the donor and refill the vacated LAST
        # slot with a SENTINEL cid above every real card (max real cid is 0x24E8), leaving
        # the count immediate untouched. The array stays the same length AND strictly
        # sorted, the binary search never matches the sentinel because no card carries that
        # cid, and Elder's arithmetic is undisturbed in either order:
        #   * azure then elder -- elder still sees count 21, still sees a strictly sorted
        #     table, removes 0x1F1D and decrements to 20 as usual;
        #   * elder then azure -- azure reads the live count 20 and does the same shift
        #     within 20 entries.
        from otn_enhanced.effects.common import ARM9_BASE
        AOJ_TBL = 0x0209CB96
        AOJ_COUNT_NATIVE = 0x15         # 21 entries in the CLEAN ROM
        AOJ_COUNT_ELDER = 0x14          # 20 after elder_six_samurai PART E
        AOJ_TBL_PTR = 0x02023B78        # pool word holding the table address
        AOJ_COUNT_IMM = 0x02023B74      # `movs r2,#<count>` feeding the bsearch
        AOJ_SENTINEL = 0x2700           # phantom, and > every real cid (max is 0x24E8), so it
                                        # sorts last and can never match a card

        # ---------------------------------------------------------------------------
        # PART E -- card identity
        # ---------------------------------------------------------------------------
        NEW_ATTRIBUTE = "LIGHT"                                     # donor is DARK
        NEW_RACE = "Dragon"                                         # donor is Machine
        NEW_LEVEL = 9                                               # donor is 8
        NEW_ATK = 2500                                              # donor is 2400
        NEW_DEF = 3000                                              # donor is 1600
        NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Synchro Effect Monster"]   # 37 -- ALREADY is



        # ---------------------------------------------------------------------------
        # PART F -- CLAUSE 1: the non-Tuner materials must be NORMAL MONSTERS
        # ---------------------------------------------------------------------------
        # Printed: "1 Tuner + 1+ non-Tuner Normal Monsters". Two halves, and only the
        # second one needs code:
        #
        #   * "1 Tuner + 1 OR MORE non-Tuner" is ALREADY correct -- the donor is absent
        #     from LIST_A 0x02275AB8, and absence is exactly what unlocks the "N or more"
        #     form. PART F must therefore NOT touch LIST_A: adding the donor would impose
        #     "EXACTLY 1 non-Tuner" and break a half that already works.
        #   * "the non-Tuners must be NORMAL MONSTERS" is what this part adds.
        #
        # THE MATERIAL SUBSYSTEM, and why the hook is where it is.
        # A BL-scan of the whole overlay-3 image shows the subsystem is CLOSED over one
        # driver, with exactly two callers per predicate:
        #
        #   INNER 0x0224829C  <- 0x022485D8 (inside OUTER) and 0x02248AAC (inside THIRD)
        #   OUTER 0x022485B4  <- 0x02249CC8, 0x02249D12   (the driver)
        #   THIRD 0x02248A88  <- 0x02249C98, 0x02249D96   (the driver)
        #
        # and the driver (0x02249C60..0x02249DA0) routes the TUNER to the OUTER predicate
        # and every NON-TUNER to the THIRD one:
        #
        #   branch FALSE (0x02249CD4), the live path for every ordinary Synchro:
        #       N = 0x02248280(synchro)          -- 2 for 0x239F / 0x24B2, else 1
        #       index <  N -> 0x021A1C7C(side,idx) must be NON-ZERO (IS a Tuner) -> OUTER
        #       index >= N -> per-Synchro switch 0x02249D1C -> for this donor the GENERIC
        #                     rule 0x02249D66, which requires 0x021A1C7C == 0 /
        #                     0x02023110(cid) == 0 (NOT a Tuner)                 -> THIRD
        #   branch TRUE  (0x02249C78):
        #       index 0 requires 0x021A1C7C == 0 (not a Tuner)                   -> THIRD
        #       index 1 requires 0x02023138(cid) != 0                            -> OUTER
        #       any other index is rejected outright
        #
        # *** In BOTH branches the third predicate is entered only after the engine has
        # already PROVED the material is not a Tuner. *** The only edges into
        # `bl 0x02248A88` that skip that check are four hardcoded per-Synchro shortcuts
        # (cids 0x208E, 0x21CB, 0x239D, 0x239F and 0x211B) -- none of them this donor.
        #
        # So a gate installed inside the THIRD predicate is non-Tuner-only BY
        # CONSTRUCTION. That matters: the clause restricts only the non-Tuners, the Tuner
        # may be any Tuner at all, and a naive "every material must be a Normal Monster"
        # test would wrongly refuse the ordinary (non-Normal) Tuners that are most of them.
        #
        # WHY NOT 0x022482B6 (the site the KB advertises for material gates): it is taken
        # TWICE ALREADY -- boggart_knight owns 0x022482B2 and shooting_quasar
        # owns 0x022482B6, and the two chain into 0x022482BC. The only 4 bytes left there
        # are the switch head itself, and a gate on it would run for every material of
        # every Synchro. PART F touches NEITHER site; it takes an unclaimed one whose
        # blast radius is just the non-Tuner path. (0x022482B6 could also have told Tuner
        # from non-Tuner via the pushed LR at [sp+0x1C] -- the inner pushes {r1-r7,lr}, so
        # that word is 0x022485DD for the Tuner and 0x02248AB1 for a non-Tuner -- but that
        # is strictly worse than hooking the non-Tuner caller directly.)
        #
        # THE SITE IS REACHED -- MEASURED, not assumed. shooting_quasar records a
        # live GDB trace of this very predicate during a material-selection sweep:
        # "verdict of 0x02248A88 = 0 (REJECT) x364 hits, while its INNER call returns 1".
        # That inner call IS 0x02248AAC, the instruction this part replaces, executing 364
        # times on the non-Tuner candidate path.
        NORMALMAT_HOOK   = 0x02248AAC          # the `bl 0x0224829C` the THIRD predicate makes
        INNER_PRED       = 0x0224829C          # inner material predicate (switch on the material)
        THIRD_PRED       = 0x02248A88          # third predicate -- THE NON-TUNER CALLER
        THIRD_PRED_SIG   = bytes.fromhex("f8b584b0051c101c")   # push {r3-r7,lr} ; sub sp,#0x10 ; ...
        INNER_PRED_SIG   = bytes.fromhex("feb50e1c071c0092")   # KB synchro.inner_pred signature
        # 0x0219CAE4(arg1, arg2, arg3) -> the material's cid. It is what the inner predicate
        # itself calls at 0x022482AC to derive r4, and it is PURE: disassembled end to end
        # (0x0219CAE4..0x0219CBA2) every arm is a single masked table read --
        # 0x0229AC94 + 0xB3C*(side&1) + <zone off> + idx*4 (zone offsets 0x124, 0x304,
        # 0x4E4 = the Extra Deck, 0x55C, 0x7B4) or + 0x14*idx + 0x34 -- followed by
        # `lsls #0x12 / lsrs #0x12 / pop {r4,pc}`. There is not one store in the function,
        # so calling it a second time with the same arguments is free and returns exactly
        # what the inner predicate computed.
        MATERIAL_CID     = 0x0219CAE4
        # 0x0202ABF8(cid) -> card_prop's card_type field SHIFTED RIGHT BY ONE
        # (dispatch.card_type_reader). 0 = Normal Monster, 1 = Effect, 2/3 = Fusion,
        # 15 = Normal Tuner, 16 = Tuner, 17/18/19 = Synchro. So "is this a Normal Monster?"
        # is `0x0202ABF8(cid) in (0, 15)`. It lives in ARM9, resident in every duel mode.
        CARD_TYPE_GETTER = 0x0202ABF8
        CARD_TYPE_NORMAL       = 0        # Normal Monster
        CARD_TYPE_NORMAL_TUNER = 15       # Normal Tuner -- a Normal Monster too. UNREACHABLE
                                          # here in practice (0x02023110 calls type 15 a Tuner,
                                          # so it can never arrive on the non-Tuner path); kept
                                          # so the test is literally "is a Normal Monster".
        NORMALMAT_STUB    = ov5_cave.CAVE_AZURE_NORMALMAT
        NORMALMAT_RESERVE = 0x50
        # The two neighbouring hook sites this part must leave strictly alone.
        # CLAUSE 1's OTHER half. "1 Tuner + 1 OR MORE non-Tuner" is legal only while the
        # donor stays ABSENT from LIST_A -- membership there means "EXACTLY this many
        # materials, extras forbidden" (synchro.list_a). PART F must never add it; verify()
        # asserts the absence so a later edit cannot regress the half that already works.
        LIST_A       = 0x02275AB8         # sorted u16 cid list; membership => extras forbidden
        LIST_A_COUNT = 0x10               # 16 -- `movs r2,#0x10` at 0x02248268
        BOGGART_HOOK = 0x022482B2         # boggart_knight's X-Saber material remap
        QUASAR_HOOK  = 0x022482B6         # shooting_quasar's Synchro-only gate
        QUASAR_HOOK_NATIVE = bytes.fromhex("0b2800d0")   # cmp r0,#0xb ; beq 0x022482BC
        BOGGART_HOOK_NATIVE = bytes.fromhex("00980125")  # ldr r0,[sp] ; movs r5,#1
        # Boggart's stub moved ov5 -> ov3 (ov3 compaction Phase D); accept either home.
        _BOGGART_HOMES = (ov5_cave.CAVE_BOGGART, cave3.CAVE3_BOGGART)


        # ===========================================================================
        # PART G -- CLAUSE 2: "When this card is Special Summoned: Dragon-Type monsters
        #                      you currently control cannot be targeted or destroyed by
        #                      card effects until the end of the next turn."
        # ===========================================================================
        # (a) THE TRIGGER lives in a DATA table, not in the cls record.
        # 0x02265768(r0 = event code) is the summon-trigger evaluator: r4 = 0x02298A28, the
        # global summon record ({+02 side, +04 zone, +0E cid, +10 flags}).  Three callers:
        # 0x02267A38 passes 7 (Normal Summon), 0x02268B7C passes 8 (Flip), 0x0226878A passes
        # 9 (SPECIAL SUMMON).  It decides ONE flag from nine sorted cid lists and, if the flag
        # is set, posts a selector-1 event at 0x02265CA8 (`movs r6,#2 ; lsls r6,#0x14` forces
        # bit 21) whose cls1 record is the card's trigger body.
        #
        # ⚠️ 0x0224A115 -- the handoff's prime candidate for "was I Synchro Summoned" -- is
        # 0x0224A114|1 = `movs r0,#2 ; bx lr`, the ubiquitous slot3 "activatable
        # unconditionally" stub.  It says nothing about the summon.
        #
        # Because that event ALWAYS carries selector 1, a summon trigger can only reach a
        # cls1 record; cls3 is unreachable.  And find_event_handler's `leftmost + 1` second
        # cls1 record is gated on 0x020230D4(cid) = "card_type >> 1 == 7" = SPIRIT MONSTER
        # (0x0224A7E6, the default arm of its per-cid switch, which is where 0x1E9C lands).
        # Our donor is card_type 37, so it can never own a reachable second record.  All
        # three of the obvious homes for clause 2 are therefore closed -- which is why the
        # trigger is taken at the LIST SEARCH instead, where the engine's own answer for our
        # cid is 0 and stays 0, so NO event is posted and clause 3's record is never touched.
        SS_TRIGGER_HOOK = 0x022658B8     # the `bl 0x02022E14` searching list 0x0228F63A
        LIST_SEARCH     = 0x02022E14     # (value, sorted s16 table, count) -> 1/0  [ARM9]
        SS_EVAL         = 0x02265768     # the summon-trigger evaluator
        SS_EVAL_SIG     = bytes.fromhex("f8b588b09b4c061c")     # push {r3-r7,lr} ; sub sp,#0x20 ;
                                                               # ldr r4,=0x02298A28 ; adds r6,r0,#0
        SS_LIST_PLAIN   = 0x0228F63A     # 0x1F cids: "when this card is Special Summoned"
        SS_LIST_PROPER  = 0x0228F6C0     # 0x24 cids: "when Synchro/Fusion/Ritual Summoned"
        SS_LIST_PROPER_HOOK = 0x022658FC  # its search -- the reachability anchor (see below)
        SUMMON_RECORD   = 0x02298A28     # +02 side, +04 zone, +0E cid
        SUMMON_REC_CID  = 0x0E
        SUMMON_REC_SIDE = 0x02
        # The four native "when this card is Synchro Summoned" cards named in the handoff --
        # Mist Wurm, Locomotion R-Genex, Trishula, Vylon Alpha -- are all members of
        # SS_LIST_PROPER, i.e. they are found by the search at SS_LIST_PROPER_HOOK.  Every
        # instruction between our hook and theirs is a fall-through or a forward `beq` that
        # rejoins, so reaching theirs REQUIRES having executed ours.  That is the CLAUDE.md
        # "the hook site is actually reached on the target code path" evidence, structural.
        SS_LIST_PROPER_MEMBERS = (0x1D7D, 0x2045, 0x221C, 0x24B1)

        # (b)+(d) THE PAYLOAD is one rider node per Dragon-occupied monster zone.
        # 0x021C479C(r0 = side, r1 = slot, r2 = key, r3 = kind BYTE, [sp+0] = param) queues
        # animation command 0x35; its handler 0x021BE044 unpacks it and calls the node writer
        # 0x0219F190(side, slot, kind, key, param).  The FULL kind byte survives, and
        # 0x0219F190 splits it: low nibble -> the node's kind, high nibble -> a DURATION
        # COUNTER.  0x02265768 already makes this exact call natively at 0x02265C6C, so it is
        # legal from the function we hook.
        ATTACH_NODE   = 0x021C479C
        ZONE_CID      = 0x021A36EC       # (side, slot) -> the cid in that zone, 0 if empty
        RACE_GETTER   = 0x0202ABB8       # (cid) -> race; [record+4] << 0xA >> 0x1B   [ARM9]
        RACE_DRAGON   = 1
        MONSTER_ZONES = 5
        PROT_KEY      = DONOR_CID        # a PRIVATE key: 0x1E9C has no other live reference
                                         # (PART D1 retargeted its ov3 arm, PART D2 removed its
                                         # arm9 table entry), and both generic kind dispatchers
                                         # route it to their default arm -- the sweeper's
                                         # kind-1/2 arm never reads the key at all, and
                                         # 0x0219FE0C compares it against [sp+0x28] = 0x1E08.
        PROT_KIND     = 0x02            # node kind 2 -> family 1 (0x021A1430 sees it) AND the
                                         # per-turn countdown arm 0x0219FA3E of the sweeper
        PROT_DURATION = 1               # THE "until the end of the NEXT turn" NUMBER.
                                         # The node sweeper 0x0219F9E0 runs EXACTLY once per
                                         # turn: its only caller 0x021C1358 is inside the
                                         # handler for animation opcode 3, queued by the
                                         # phase-8 handler 0x02258C3C at step 0, and that same
                                         # handler's next step queues opcode 4 -> 0x021C102C,
                                         # the sole site that does
                                         #   [0x0229DD14+0x34] ^= 1   (toggle turn player)
                                         #   [0x0229DD14+0x40] += 1   (turn counter)
                                         # The kind-1/2 arm is `n = [node+2]>>4 ;
                                         # if n == 0: free else n -= 1`, so n = 1 survives the
                                         # sweep at the end of the summoning turn and is freed
                                         # by the sweep at the end of the following one.
        PROT_KIND_BYTE = PROT_KIND | (PROT_DURATION << 4)      # 0x12
        SS_STUB        = ov5_cave.CAVE_AZURE_SSPROT
        SS_STUB_RESERVE = 0x60

        # (c) THE PROTECTION. 0x021B021C is the general "may this card effect affect this
        # monster" predicate; 0x021B0296 is its PROTECTED exit (it returns the caller's
        # [sp+0x58], which the main wrapper 0x021B0848 supplies as 0) and 0x021B081E its
        # "affectable" exit.  At 0x021B058C it queries Vehicroid Connection Zone's family-1
        # rider and, on a hit, takes the protected exit.
        #
        # WHY THIS LINK AND NOT HEART OF CLEAR WATER'S AT 0x021B05CC:
        #   1. 0x021B05CC is already claimed by safe_zone PART D.
        #   2. 0x021B05CC is INSIDE the `targets` block (the flag is read at 0x021B05BE),
        #      which is the entire origin of Safe Zone's documented divergence
        #      "a non-targeting destruction still resolves".  0x021B0592 is BEFORE that gate.
        #   3. A non-targeting destruction demonstrably passes through here: caller
        #      0x02245B7A calls the wrapper with targets = 0 and, only if the predicate says
        #      "affectable", calls 0x021CF35C -> 0x021CF31C -> 0x021CDD4C(desc, mask, 0x0E, 2)
        #      -- destination zone 0x0E = the Graveyard, i.e. it destroys the monster.
        #   4. It is on the live path, proven by a SHIPPED in-game result: Safe Zone PART D's
        #      hook at 0x021B05CC is in-game confirmed, and control reaches 0x021B05CC only
        #      by first executing 0x021B0592.
        # Neither this link nor Dreadmaster's at 0x021B05FA applies a controller test, so
        # simply omitting Safe Zone's opponent check gives "neither player" for free.
        PROT_HOOK      = 0x021B0592      # the `bl 0x021A1430` querying VCZ's rider
        NODE_QUERY_F1  = 0x021A1430      # family-1 rider query (kind < 6, key@+0 IS a cid)
        AFFECT_PRED    = 0x021B021C      # the enclosing predicate
        AFFECT_PRED_SIG = bytes.fromhex("f8b590b00e1c1699")     # push {r3-r7,lr} ; sub sp,#0x40 ; ...
        VCZ_CID        = 0x1A5C          # Vehicroid Connection Zone -- its query is replayed
        SAFE_ZONE_HOOK = 0x021B05CC      # safe_zone PART D's link in the SAME function
        SAFE_ZONE_HOOK_NATIVE = bytes.fromhex("f0f7c0f9")      # bl 0x021A0950


        def _sz_target3() -> int:
            from otn_enhanced.effects import cave3
            return cave3.CAVE3_SZ_TARGET
        PROT_STUB      = ov5_cave.CAVE_AZURE_PROT
        PROT_STUB_RESERVE = 0x30


        # ===========================================================================
        # helpers
        # ===========================================================================


        def _cls1_records(ov: bytearray) -> list[tuple[int, ...]]:
            """Read cls1 as (cid, slot1..slot5) tuples; the pad halfword must be zero."""
            out = []
            for i in range(CLS1_COUNT):
                o = _off(CLS1_BASE + i * CLS1_STRIDE)
                cid, pad = struct.unpack_from("<HH", ov, o)
                assert pad == 0, f"cls1[{i}] has nonzero pad 0x{pad:04X}"
                out.append((cid,) + struct.unpack_from("<5I", ov, o + 4))
            return out


        def _write_cls1(ov: bytearray, recs: list[tuple[int, ...]]) -> None:
            for i, r in enumerate(recs):
                struct.pack_into("<HH5I", ov, _off(CLS1_BASE + i * CLS1_STRIDE), r[0], 0, *r[1:])


        def _crit_rows(ov: bytearray) -> list[tuple[int, ...]]:
            return [struct.unpack_from(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE))
                    for i in range(CRIT_COUNT)]


        def _write_crit(ov: bytearray, rows: list[tuple[int, ...]]) -> None:
            for i, r in enumerate(rows):
                struct.pack_into(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE), *r)


        def _anchor_ok() -> tuple[bytes, ...]:
            """The encodings SS_LIST_PROPER_HOOK may legally hold.

            The anchor's job is to prove OUR hook at SS_TRIGGER_HOOK is on the live
            straight-line block, by showing the sibling search 0x44 bytes later is still
            a `bl` in the same run of code.  orient_dragon (shipped 2026-09-07)
            legitimately retargets that sibling to CAVE_OD_TRIG, which compares one cid
            and TAIL-CALLS 0x02022E14 -- so the block, the call and the reachability
            argument are all intact, and only the immediate branch target differs.
            Accept either encoding; anything else means the evaluator really has moved.

            ⚠️ Do NOT relax this to "is it a BL": the point is that this specific site
            still calls the specific list search, directly or through a shim we know.
            """
            return (_bl(SS_LIST_PROPER_HOOK, LIST_SEARCH),
                    _bl(SS_LIST_PROPER_HOOK, ov5_cave.CAVE_OD_TRIG),
                    _bl(SS_LIST_PROPER_HOOK, 0x021F1464))   # cave3.CAVE3_OD_TRIG (orient_dragon ov3=True)


        def _bl(src: int, dst: int) -> bytes:
            """ARMv4T two-halfword BL (Thumb-1 long branch-with-link)."""
            off = dst - (src + 4)
            assert -(1 << 22) <= off < (1 << 22), f"BL 0x{src:08X}->0x{dst:08X} out of range"
            return struct.pack("<HH", 0xF000 | ((off >> 12) & 0x7FF), 0xF800 | ((off >> 1) & 0x7FF))


        def _dup_groups(cids: list[int]) -> dict[int, list[int]]:
            """cid -> its row indices, for every cid owning more than one row."""
            g: dict[int, list[int]] = {}
            for i, c in enumerate(cids):
                g.setdefault(c, []).append(i)
            return {c: v for c, v in g.items() if len(v) > 1}


        def _count_neutral_swap(recs: list[tuple[int, ...]], drop: tuple[int, ...],
                                insert: tuple[int, ...], label: str) -> list[tuple[int, ...]]:
            """Drop *drop* (which must occur exactly once) and insert *insert* sorted.

            Asserts sortedness before and after, an unchanged count, and -- the check that
            generic table editors miss -- that no cid which owned SEVERAL adjacent rows ends
            up split by the edit. find_event_handler reaches a cid's SECOND record via
            `leftmost + 1`, so wedging a foreign record between a pair would silently make
            the second one unreachable.
            """
            cids = [r[0] for r in recs]
            assert all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)), \
                f"{label}: not sorted before edit"
            before_groups = _dup_groups(cids)

            hits = [i for i, r in enumerate(recs) if r == drop]
            assert len(hits) == 1, (
                f"{label}: expected exactly ONE record {tuple(hex(v) for v in drop)}, "
                f"found {len(hits)}")

            out = list(recs)
            out.pop(hits[0])
            pos = next((i for i, r in enumerate(out) if r[0] > insert[0]), len(out))
            out.insert(pos, insert)

            assert len(out) == len(recs), f"{label}: count changed"
            new_cids = [r[0] for r in out]
            assert all(new_cids[i] <= new_cids[i + 1] for i in range(len(new_cids) - 1)), \
                f"{label}: not sorted after edit"
            after_groups = _dup_groups(new_cids)
            assert set(after_groups) == set(before_groups) - {drop[0]}, \
                f"{label}: the set of multi-row cids changed"
            for c, idxs in after_groups.items():
                assert idxs == list(range(idxs[0], idxs[0] + len(idxs))), \
                    f"{label}: cid 0x{c:04X}'s rows were split apart by the insert"

            print(f"   {label}: dropped phantom 0x{drop[0]:04X} (row {hits[0]}), inserted "
                  f"0x{insert[0]:04X} at row {pos} -- count {len(out)}, sorted, "
                  f"{len(after_groups)} multi-row cids all still contiguous")
            return out


        def _arm9_open(path: str):
            """Open the ROM and return (rom, mc, sec, bytearray(sec.data)) for ARM9 main."""
            rom = ndspy.rom.NintendoDSRom.fromFile(path)
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
            return rom, mc, sec, bytearray(sec.data)


        # ===========================================================================
        # PARTS A / B / C / D1 -- overlay 3
        # ===========================================================================
        def apply_effect(ov: bytearray) -> None:
            # --- PART A: the Standby-Phase registry row -------------------------------
            o = _off(REG_BASE + REG_ROW * 8)
            resolver, cid = struct.unpack_from("<IH", ov, o)
            if cid == DONOR_CID:
                print(f"A  registry row {REG_ROW} already points at 0x{DONOR_CID:04X}")
            else:
                assert resolver == REG_STANDBY_RESOLVER, (
                    f"reg[{REG_ROW}] resolver is 0x{resolver:08X}, expected "
                    f"0x{REG_STANDBY_RESOLVER:08X} (the Standby-Phase machine)")
                assert cid == REG_DROP_PHANTOM, (
                    f"reg[{REG_ROW}] cid is 0x{cid:04X}, expected the phantom "
                    f"0x{REG_DROP_PHANTOM:04X} -- someone else claimed this row")
                struct.pack_into("<H", ov, o + 4, DONOR_CID)
                print(f"A  registry row {REG_ROW}: cid 0x{REG_DROP_PHANTOM:04X} -> "
                      f"0x{DONOR_CID:04X} (resolver 0x{resolver:08X} kept)")

            # --- PART B: the cls1 record ---------------------------------------------
            recs = _cls1_records(ov)
            if any(r[0] == DONOR_CID for r in recs):
                print(f"B  cls1 already carries 0x{DONOR_CID:04X}")
            else:
                _write_cls1(ov, _count_neutral_swap(
                    recs, CLS1_PHANTOM_BEFORE, CLS1_NEW, "B  cls1"))

            # --- PART C: the criteria row --------------------------------------------
            rows = _crit_rows(ov)
            if any(r[0] == DONOR_CID for r in rows):
                print(f"C  criteria registry already carries 0x{DONOR_CID:04X}")
            else:
                _write_crit(ov, _count_neutral_swap(
                    rows, CRIT_PHANTOM_BEFORE, CRIT_NEW, "C  criteria"))

            # --- PART D1: kill the native continuous ATK gain -------------------------
            o = _off(STAT_ARM_SITE)
            cur = bytes(ov[o:o + 4])
            if cur == _bl(STAT_ARM_SITE, STAT_ARM_NEW):
                print("D1 stat-engine arm already neutralised")
            else:
                assert cur == _bl(STAT_ARM_SITE, STAT_ARM_OLD), (
                    f"0x{STAT_ARM_SITE:08X} is {cur.hex()}, expected "
                    f"{_bl(STAT_ARM_SITE, STAT_ARM_OLD).hex()} "
                    f"(bl 0x{STAT_ARM_OLD:08X}) -- the stat tree moved")
                ov[o:o + 4] = _bl(STAT_ARM_SITE, STAT_ARM_NEW)
                print(f"D1 stat-engine: 0x{STAT_ARM_SITE:08X} bl 0x{STAT_ARM_OLD:08X} -> "
                      f"bl 0x{STAT_ARM_NEW:08X} (donor's +200 ATK/LIGHT-in-opp-GY removed)")


        # ===========================================================================
        # PART D2 -- ARM9 set-code table
        # ===========================================================================
        def apply_setcode_drop(path: str) -> None:
            rom, mc, sec, data = _arm9_open(path)

            def u16(a):
                return struct.unpack_from("<H", data, a - ARM9_BASE)[0]

            assert struct.unpack_from("<I", data, AOJ_TBL_PTR - ARM9_BASE)[0] == AOJ_TBL, \
                "the Ally of Justice table pointer moved"
            count = u16(AOJ_COUNT_IMM) & 0xFF
            assert count in (AOJ_COUNT_NATIVE, AOJ_COUNT_ELDER), (
                f"the Ally of Justice count immediate is {count} -- expected "
                f"{AOJ_COUNT_NATIVE} (clean) or {AOJ_COUNT_ELDER} (after elder_six_samurai)")

            entries = [u16(AOJ_TBL + 2 * i) for i in range(count)]
            if DONOR_CID not in entries:
                print(f"D2 0x{DONOR_CID:04X} already absent from the Ally of Justice table")
                return
            i = entries.index(DONOR_CID)
            new = [c for c in entries if c != DONOR_CID] + [AOJ_SENTINEL]
            assert len(new) == count, "the Ally of Justice count changed"
            assert all(new[k] < new[k + 1] for k in range(count - 1)), (
                "the Ally of Justice table would no longer be STRICTLY sorted "
                f"({[hex(x) for x in new]}) -- elder_six_samurai asserts strictness")
            struct.pack_into(f"<{count}H", data, AOJ_TBL - ARM9_BASE, *new)

            sec.data = bytes(data)
            rom.arm9 = mc.save()
            rom.saveToFile(path)
            print(f"D2 Ally of Justice table: removed 0x{DONOR_CID:04X} (was entry {i}), "
                  f"tail shifted left, slot {count - 1} refilled with sentinel "
                  f"0x{AOJ_SENTINEL:04X} (count {count} unchanged, strictly sorted)")


        # ===========================================================================
        # PART F -- the non-Tuner materials must be Normal Monsters
        # ===========================================================================
        def _build_normal_material_stub(base: int) -> bytes:
            """Assemble the "this non-Tuner material must be a Normal Monster" gate.

            Entered by BL from 0x02248AAC, where the THIRD (non-Tuner) material predicate
            calls the inner one, so on entry the registers are exactly the inner
            predicate's four arguments:

                r0 = the SYNCHRO's cid      r1 = arg1 (side/context)
                r2 = arg2 (zone selector)   r3 = arg3 (index)

            and LR = 0x02248AB1.  The stub calls the inner predicate itself and returns
            ITS verdict untouched for every Synchro except the donor, so Shooting Quasar
            and XX-Saber Boggart Knight -- which hook the same predicate 0x1FE / 0x7FA
            bytes away -- see byte-identical behaviour.

            Contracts honoured:
              * r4-r7 are callee-saved: pushed and popped (the inner predicate preserves
                them across our call, since it pops the same list it pushed).
              * The inner predicate also restores r1/r2/r3 from its own push, and the
                third predicate may rely on that, so every exit re-establishes them from
                the saved copies.  This is why arg1/arg2/arg3 are saved BEFORE the call
                even though only the donor path reads them back.
              * POP {..,PC} is the return -- Thumb-1 cannot POP into LR
                (thumb-pop-into-lr-footgun), and the pushed LR is what lands in PC.
            """
            from otn_enhanced.asm.effect_builder import EffectBuilder, R3, R4, R5, R6, R7
            from otn_enhanced.asm.effect_verify import assert_thumb1_only

            a = EffectBuilder()
            a.prologue([R4, R5, R6, R7])
            a.insn("MOV", "R4, R1")          # arg1 -- side / context
            a.insn("MOV", "R5, R2")          # arg2 -- zone selector
            a.insn("MOV", "R6, R3")          # arg3 -- index within that zone
            a.insn("MOV", "R7, R0")          # arg0 -- the SYNCHRO's cid
            a.bl(INNER_PRED)                 # the native verdict, unchanged
            a.insn("CMP", "R0, #0x0")
            a.insn("BEQ", "out")             # engine already rejects -> keep the rejection
            a.ldr_const(3, DONOR_CID)
            a.insn("CMP", "R7, R3")
            a.insn("BNE", "restore")         # any other Synchro -> native verdict, r3 fixed
            a.insn("MOV", "R7, R0")          # stash the native verdict
            a.insn("MOV", "R0, R4")          # re-issue the inner predicate's own lookup
            a.insn("MOV", "R1, R5")
            a.insn("MOV", "R2, R6")
            a.bl(MATERIAL_CID)               # -> r0 = this material's cid (pure table read)
            a.bl(CARD_TYPE_GETTER)           # -> r0 = card_prop card_type >> 1
            a.insn("CMP", f"R0, #0x{CARD_TYPE_NORMAL:X}")
            a.insn("BEQ", "keep")            # 0  = Normal Monster
            a.insn("CMP", f"R0, #0x{CARD_TYPE_NORMAL_TUNER:X}")
            a.insn("BEQ", "keep")            # 15 = Normal Tuner (a Normal Monster too)
            a.insn("MOV", "R0, #0x0")        # anything else -> REJECT this non-Tuner material
            a.insn("B", "restore")
            a.label("keep")
            a.insn("MOV", "R0, R7")          # hand back the engine's own verdict
            a.label("restore")
            a.insn("MOV", "R1, R4")          # honour the inner predicate's r1/r2/r3 contract
            a.insn("MOV", "R2, R5")
            a.insn("MOV", "R3, R6")
            a.label("out")
            a.insn("POP", "{R4, R5, R6, R7, PC}")

            code = a.assemble(base)
            assert_thumb1_only(code, base)   # never a bare capstone disasm -- it accepts Thumb-2
            assert len(code) <= NORMALMAT_RESERVE, (
                f"PART F stub is {len(code)}B > the {NORMALMAT_RESERVE}B cave reserve")
            return code


        def apply_normal_material_gate(ov: bytearray, rom) -> None:
            """Install the CLAUSE 1 non-Tuner-must-be-Normal gate (PART F). Idempotent."""
            o = _off(NORMALMAT_HOOK)
            cur = bytes(ov[o:o + 4])
            bl = _bl(NORMALMAT_HOOK, NORMALMAT_STUB)
            if cur == bl:
                print("F  Normal-Monster material gate already installed -> no change")
                return
            assert cur == _bl(NORMALMAT_HOOK, INNER_PRED), (
                f"0x{NORMALMAT_HOOK:08X} is {cur.hex()}, expected "
                f"{_bl(NORMALMAT_HOOK, INNER_PRED).hex()} (bl 0x{INNER_PRED:08X}) -- the "
                f"third material predicate moved, re-derive before patching")

            # Anchor BOTH predicates: the stub replays one and is hosted inside the other,
            # so a drift in either invalidates every register assumption above.
            assert bytes(ov[_off(THIRD_PRED):_off(THIRD_PRED) + 8]) == THIRD_PRED_SIG, (
                f"third material predicate 0x{THIRD_PRED:08X} signature drifted")
            assert bytes(ov[_off(INNER_PRED):_off(INNER_PRED) + 8]) == INNER_PRED_SIG, (
                f"inner material predicate 0x{INNER_PRED:08X} signature drifted "
                f"(KB fact synchro.inner_pred)")

            # COMPOSITION: this patch shares the material predicates with two shipped,
            # in-game-confirmed cards. Assert we are not standing on either of their hooks
            # -- each site must be either still native or carrying its own owner's BL.
            for site, native, owner, caves in (
                    (BOGGART_HOOK, BOGGART_HOOK_NATIVE, "boggart_knight", _BOGGART_HOMES),
                    (QUASAR_HOOK, QUASAR_HOOK_NATIVE, "shooting_quasar",
                     (ov5_cave.CAVE_QSR_PRED, 0x021F1698))):   # + cave3.CAVE3_QSR_PRED
                raw = bytes(ov[_off(site):_off(site) + 4])
                assert raw in (native, *(_bl(site, c) for c in caves)), (
                    f"0x{site:08X} = {raw.hex()} is neither native nor {owner}'s BL -- "
                    f"someone else took it; resolve the collision before building")

            stub = _build_normal_material_stub(NORMALMAT_STUB)
            ov5_cave.install_cave(rom, NORMALMAT_STUB, stub, reserve=NORMALMAT_RESERVE)
            ov[o:o + 4] = bl
            print(f"F  hook 0x{NORMALMAT_HOOK:08X} (third predicate's inner call) -> stub "
                  f"0x{NORMALMAT_STUB:08X} ({len(stub)}B)  => 0x{DONOR_CID:04X}'s non-Tuner "
                  f"materials must be Normal Monsters (card_type>>1 in {{0, 15}})")


        # ===========================================================================
        # PART G -- CLAUSE 2: the on-Special-Summon Dragon protection
        # ===========================================================================
        def _build_ss_protect_stub(base: int) -> bytes:
            """Assemble the on-Special-Summon "protect my Dragons" stub.

            Entered by BL from 0x022658B8, inside the `cmp r6,#9` (Special Summon) block of
            the summon-trigger evaluator 0x02265768, where the engine is asking whether the
            just-summoned card is a member of the "plain when-this-card-is-Special-Summoned"
            list.  On entry the registers are exactly that search's arguments:

                r0 = the summoned card's cid   r1 = 0x0228F63A   r2 = 0x1F

            with r4 = 0x02298A28 (the summon record) and r5/r6/r7 live in the caller.

            The stub replays the search and hands back ITS answer untouched, so for every
            card -- including ours, which is not a member -- the engine's own decision is
            byte-identical.  Our donor therefore posts NO cls1 event, which is what keeps
            the shipped clause-3 record out of this path entirely.

            On the way, when the summoned card IS the donor, it walks the summoner's five
            monster zones and attaches one rider node to every Dragon it finds:

                key      = 0x1E9C   (private -- see PROT_KEY)
                kind     = 2        (< 6, so the family-1 query 0x021A1430 sees it)
                duration = 1        ("until the end of the next turn"; see PROT_DURATION)

            Attaching per ZONE is what makes "Dragon monsters you CURRENTLY control" a
            snapshot for free: a Dragon summoned afterwards simply has no node.

            Contracts honoured:
              * PUSH/POP {R3-R7,...} -- six words, matching the engine's own idiom here, so
                the stack stays 8-aligned across the SUB SP, #8 scratch slot that
                0x021C479C's fifth argument needs.
              * POP {..,PC} is the return; Thumb-1 cannot POP into LR
                (thumb-pop-into-lr-footgun).
              * `ADD R5, #1` is the TWO-operand imm8 form -- the 3-operand Format-2 ADD caps
                its immediate at 7 and silently miscodes above that
                (thumb-add-sub-imm3-footgun).
              * `MOV Rd, Rs` on low registers is `LSL Rd, Rs, #0` and SETS FLAGS, so no MOV
                is placed between a CMP and the branch that reads it.
            """
            from otn_enhanced.asm.effect_builder import EffectBuilder, R3, R4, R5, R6, R7
            from otn_enhanced.asm.effect_verify import assert_thumb1_only

            a = EffectBuilder()
            a.prologue([R3, R4, R5, R6, R7])
            a.insn("SUB", "SP, #0x8")            # scratch: 0x021C479C reads param from [sp]
            a.bl(LIST_SEARCH)                    # replay -- r0/r1/r2 are the caller's args
            a.insn("MOV", "R7, R0")              # the engine's own verdict, returned verbatim
            a.ldr_const(4, SUMMON_RECORD)
            a.insn("LDRH", f"R0, [R4, #0x{SUMMON_REC_CID:X}]")   # the summoned card's cid
            a.ldr_const(1, DONOR_CID)
            a.insn("CMP", "R0, R1")
            a.insn("BNE", "out")                 # any other card -> nothing but the replay
            a.insn("LDRH", f"R6, [R4, #0x{SUMMON_REC_SIDE:X}]")  # side = its controller
            a.insn("MOV", "R5, #0x0")            # zone
            a.label("loop")
            a.insn("MOV", "R0, R6")
            a.insn("MOV", "R1, R5")
            a.bl(ZONE_CID)                       # -> cid in that zone (0 when empty)
            a.insn("CMP", "R0, #0x0")
            a.insn("BEQ", "next")
            a.bl(RACE_GETTER)                    # -> race
            a.insn("CMP", f"R0, #0x{RACE_DRAGON:X}")
            a.insn("BNE", "next")                # not a Dragon -> leave it unprotected
            a.insn("MOV", "R0, #0x0")
            a.insn("STR", "R0, [SP, #0x0]")      # param = 0, as the native call at 0x02265C6C
            a.insn("MOV", "R0, R6")              # side
            a.insn("MOV", "R1, R5")              # slot
            a.ldr_const(2, PROT_KEY)
            a.insn("MOV", f"R3, #0x{PROT_KIND_BYTE:X}")          # kind | duration << 4
            a.bl(ATTACH_NODE)
            a.label("next")
            a.insn("ADD", "R5, #0x1")
            a.insn("CMP", f"R5, #0x{MONSTER_ZONES:X}")
            a.insn("BLT", "loop")
            a.label("out")
            a.insn("MOV", "R0, R7")
            a.insn("ADD", "SP, #0x8")
            a.insn("POP", "{R3, R4, R5, R6, R7, PC}")

            code = a.assemble(base)
            assert_thumb1_only(code, base)
            assert len(code) <= SS_STUB_RESERVE, (
                f"PART G SS stub is {len(code)}B > the {SS_STUB_RESERVE}B cave reserve")
            return code


        def _build_protect_query_stub(base: int) -> bytes:
            """Assemble the protection query link for 0x021B021C.

            Entered by BL from 0x021B0592, where the "may this card effect affect this
            monster" predicate asks whether Vehicroid Connection Zone's rider is on the
            target.  On entry:

                r0 = the TARGET's side (r6)   r1 = the TARGET's slot (r5)   r2 = 0x1A5C

            and the caller's own test is `cmp r0,#0 ; beq <continue> ; b 0x021B0296`, so a
            non-zero return is already wired to the predicate's PROTECTED exit -- this stub
            needs no frame surgery at all, unlike safe_zone PART D's insert.

            It replays VCZ's query untouched and only on a MISS asks the same question about
            our own key, so Vehicroid Connection Zone keeps working byte-for-byte.

            NO controller test: the clause protects from BOTH players, and neither this link
            nor Dreadmaster's at 0x021B05FA applies one, so omitting it is the whole change.
            """
            from otn_enhanced.asm.effect_builder import EffectBuilder, R3, R4, R5, R6, R7
            from otn_enhanced.asm.effect_verify import assert_thumb1_only

            a = EffectBuilder()
            a.prologue([R3, R4, R5, R6, R7])
            a.insn("MOV", "R4, R0")              # side
            a.insn("MOV", "R5, R1")              # slot
            a.bl(NODE_QUERY_F1)                  # replay -- r0/r1/r2 are the caller's args
            a.insn("CMP", "R0, #0x0")
            a.insn("BNE", "done")                # VCZ matched -> hand back its answer
            a.insn("MOV", "R0, R4")
            a.insn("MOV", "R1, R5")
            a.ldr_const(2, PROT_KEY)
            a.bl(NODE_QUERY_F1)                  # our rider -> 1 = protected
            a.label("done")
            a.insn("POP", "{R3, R4, R5, R6, R7, PC}")

            code = a.assemble(base)
            assert_thumb1_only(code, base)
            assert len(code) <= PROT_STUB_RESERVE, (
                f"PART G protect stub is {len(code)}B > the {PROT_STUB_RESERVE}B cave reserve")
            return code


        def apply_ss_protection(ov: bytearray, rom) -> None:
            """Install CLAUSE 2 -- the on-SS Dragon protection (PART G). Idempotent."""
            # --- G1: the trigger + snapshot -----------------------------------------
            o = _off(SS_TRIGGER_HOOK)
            cur = bytes(ov[o:o + 4])
            bl = _bl(SS_TRIGGER_HOOK, SS_STUB)
            if cur == bl:
                print("G1 on-SS Dragon-protection trigger already installed -> no change")
            else:
                assert cur == _bl(SS_TRIGGER_HOOK, LIST_SEARCH), (
                    f"0x{SS_TRIGGER_HOOK:08X} is {cur.hex()}, expected "
                    f"{_bl(SS_TRIGGER_HOOK, LIST_SEARCH).hex()} (bl 0x{LIST_SEARCH:08X}) -- "
                    f"the summon-trigger evaluator moved, re-derive before patching")
                assert bytes(ov[_off(SS_EVAL):_off(SS_EVAL) + len(SS_EVAL_SIG)]) == SS_EVAL_SIG, (
                    f"summon-trigger evaluator 0x{SS_EVAL:08X} signature drifted")

                # REACHABILITY, asserted against the image rather than believed: the sibling
                # search 0x44 bytes later must still be a `bl 0x02022E14`, and the four native
                # "when this card is Synchro Summoned" cards must still be in the list it
                # searches. If either drifts, the argument that our hook is on the live path
                # (they are in one straight-line block) no longer holds.
                assert bytes(ov[_off(SS_LIST_PROPER_HOOK):_off(SS_LIST_PROPER_HOOK) + 4]) \
                    in _anchor_ok(), (
                        f"0x{SS_LIST_PROPER_HOOK:08X} is no longer the sibling list search -- "
                        f"the reachability anchor is gone")
                proper = struct.unpack_from("<36H", ov, _off(SS_LIST_PROPER))
                for cid in SS_LIST_PROPER_MEMBERS:
                    assert cid in proper, (
                        f"0x{cid:04X} left the \"when Synchro Summoned\" list "
                        f"0x{SS_LIST_PROPER:08X} -- re-derive the reachability argument")

                stub = _build_ss_protect_stub(SS_STUB)
                ov5_cave.install_cave(rom, SS_STUB, stub, reserve=SS_STUB_RESERVE)
                ov[o:o + 4] = bl
                print(f"G1 hook 0x{SS_TRIGGER_HOOK:08X} (Special-Summon trigger list search) -> "
                      f"stub 0x{SS_STUB:08X} ({len(stub)}B)  => on any Special Summon of "
                      f"0x{DONOR_CID:04X}, every Dragon in its controller's monster zones gets "
                      f"a {{key 0x{PROT_KEY:04X}, kind {PROT_KIND}, duration {PROT_DURATION}}} rider")

            # --- G2: the protection query -------------------------------------------
            o = _off(PROT_HOOK)
            cur = bytes(ov[o:o + 4])
            bl = _bl(PROT_HOOK, PROT_STUB)
            if cur == bl:
                print("G2 protection query link already installed -> no change")
                return
            assert cur == _bl(PROT_HOOK, NODE_QUERY_F1), (
                f"0x{PROT_HOOK:08X} is {cur.hex()}, expected "
                f"{_bl(PROT_HOOK, NODE_QUERY_F1).hex()} (bl 0x{NODE_QUERY_F1:08X}) -- "
                f"Vehicroid Connection Zone's link moved, re-derive before patching")
            assert bytes(ov[_off(AFFECT_PRED):_off(AFFECT_PRED) + len(AFFECT_PRED_SIG)]) \
                == AFFECT_PRED_SIG, (
                    f"affect predicate 0x{AFFECT_PRED:08X} signature drifted")

            # COMPOSITION: safe_zone PART D hooks a DIFFERENT link in this same
            # function. Assert we are not standing on it -- it must be native or its BL.
            raw = bytes(ov[_off(SAFE_ZONE_HOOK):_off(SAFE_ZONE_HOOK) + 4])
            # Safe Zone's PART D stub lives in the ov5 cave or the ov3 pool -- both are its BL.
            sz_bls = (_bl(SAFE_ZONE_HOOK, ov5_cave.CAVE_SZ_TARGET), _bl(SAFE_ZONE_HOOK, _sz_target3()))
            assert raw == SAFE_ZONE_HOOK_NATIVE or raw in sz_bls, (
                f"0x{SAFE_ZONE_HOOK:08X} = {raw.hex()} is neither native nor "
                f"safe_zone's BL -- resolve the collision before building")

            stub = _build_protect_query_stub(PROT_STUB)
            ov5_cave.install_cave(rom, PROT_STUB, stub, reserve=PROT_STUB_RESERVE)
            ov[o:o + 4] = bl
            print(f"G2 hook 0x{PROT_HOOK:08X} (Vehicroid Connection Zone's rider link inside "
                  f"0x{AFFECT_PRED:08X}) -> stub 0x{PROT_STUB:08X} ({len(stub)}B)  => a monster "
                  f"carrying the 0x{PROT_KEY:04X} rider is not affectable by card effects, "
                  f"from EITHER player")


        def install(rom, view):
            ov = view.buf
            apply_effect(ov)                      # PARTS A/B/C/D1
            apply_normal_material_gate(ov, rom)   # PART F: clause 1 -- non-Tuners must be Normals
            apply_ss_protection(ov, rom)          # PART G: clause 2 -- on-SS Dragon protection

        def check_fn(c, rom, view):
            from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
            from otn_enhanced.data.card_stats import iter_paths
            from otn_enhanced.rom.pac import parse_pac
            ov = bytearray(view.buf)

            def check(cond: bool, msg: str) -> None:
                c.ok(bool(cond), msg)

            # --- A: the registry row --------------------------------------------------
            resolver, cid = struct.unpack_from("<IH", ov, _off(REG_BASE + REG_ROW * 8))
            check(resolver == REG_STANDBY_RESOLVER,
                  f"reg[{REG_ROW}] resolver == 0x{REG_STANDBY_RESOLVER:08X} (Standby machine)")
            check(cid == DONOR_CID, f"reg[{REG_ROW}] cid == 0x{DONOR_CID:04X}")
            check(REG_SECTION_LO <= REG_ROW < REG_SECTION_LO + REG_SECTION_COUNT,
                  f"reg[{REG_ROW}] is inside the Standby section "
                  f"({REG_SECTION_LO}..{REG_SECTION_LO + REG_SECTION_COUNT - 1})")

            # --- B: the cls1 record ---------------------------------------------------
            recs = _cls1_records(ov)
            mine = [r for r in recs if r[0] == DONOR_CID]
            check(len(mine) == 1, f"cls1 has exactly ONE 0x{DONOR_CID:04X} row (got {len(mine)})")
            if mine:
                check(mine[0] == CLS1_NEW,
                      f"cls1 slots == Captain Tenacious's ({[hex(v) for v in mine[0][1:]]})")
            cids = [r[0] for r in recs]
            check(len(recs) == CLS1_COUNT, f"cls1 count still {CLS1_COUNT}")
            check(all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)), "cls1 still sorted")
            check(CLS1_DROP_PHANTOM not in cids,
                  f"cls1 phantom 0x{CLS1_DROP_PHANTOM:04X} dropped")

            # --- C: the criteria row --------------------------------------------------
            rows = _crit_rows(ov)
            mine = [r for r in rows if r[0] == DONOR_CID]
            check(len(mine) == 1, f"criteria has exactly ONE 0x{DONOR_CID:04X} row")
            if mine:
                check(mine[0] == CRIT_NEW,
                      "criteria row == {0xFFFF, 0x0223DE05, 0x0002, 0x0001} "
                      "(1 Normal Monster in your GY)")
            ccids = [r[0] for r in rows]
            check(len(rows) == CRIT_COUNT, f"criteria count still {CRIT_COUNT}")
            check(all(ccids[i] <= ccids[i + 1] for i in range(len(ccids) - 1)),
                  "criteria still sorted")
            check(CRIT_DROP_PHANTOM not in ccids,
                  f"criteria phantom 0x{CRIT_DROP_PHANTOM:04X} dropped")

            # --- D1: the stat-engine arm ---------------------------------------------
            o = _off(STAT_ARM_SITE)
            check(bytes(ov[o:o + 4]) == _bl(STAT_ARM_SITE, STAT_ARM_NEW),
                  f"0x{STAT_ARM_SITE:08X} == bl 0x{STAT_ARM_NEW:08X} (donor ATK gain removed)")


            # --- F: the CLAUSE 1 non-Tuner-must-be-Normal material gate ---------------
            from otn_enhanced.asm.effect_verify import assert_thumb1_only

            o = _off(NORMALMAT_HOOK)
            check(bytes(ov[o:o + 4]) == _bl(NORMALMAT_HOOK, NORMALMAT_STUB),
                  f"0x{NORMALMAT_HOOK:08X} == bl 0x{NORMALMAT_STUB:08X} "
                  f"(the third predicate's inner call is hooked)")
            check(bytes(ov[_off(THIRD_PRED):_off(THIRD_PRED) + 8]) == THIRD_PRED_SIG,
                  f"third material predicate 0x{THIRD_PRED:08X} signature intact")
            check(bytes(ov[_off(INNER_PRED):_off(INNER_PRED) + 8]) == INNER_PRED_SIG,
                  f"inner material predicate 0x{INNER_PRED:08X} signature intact")

            # The stub really is in the cave, byte-for-byte, and is legal Thumb-1.
            rom_f = rom
            want = _build_normal_material_stub(NORMALMAT_STUB)
            got = ov5_cave.read_cave(rom_f, NORMALMAT_STUB, len(want))
            check(got == want, f"ov5 cave 0x{NORMALMAT_STUB:08X} holds the {len(want)}B PART F stub")
            try:
                assert_thumb1_only(want, NORMALMAT_STUB)
                check(True, "PART F stub is Thumb-1 only (no Thumb-2 in injected code)")
            except AssertionError as e:
                check(False, f"PART F stub is NOT Thumb-1 only: {e}")

            # COMPOSITION: the two shipped cards that hook this same predicate are untouched.
            for site, native, owner, caves in (
                    (BOGGART_HOOK, BOGGART_HOOK_NATIVE, "boggart_knight", _BOGGART_HOMES),
                    (QUASAR_HOOK, QUASAR_HOOK_NATIVE, "shooting_quasar",
                     (ov5_cave.CAVE_QSR_PRED, 0x021F1698))):   # + cave3.CAVE3_QSR_PRED
                raw = bytes(ov[_off(site):_off(site) + 4])
                owned = raw in tuple(_bl(site, c) for c in caves)
                who = "native" if raw == native else (
                    f"{owner}'s BL" if owned else f"UNKNOWN ({raw.hex()})")
                check(raw == native or owned,
                      f"0x{site:08X} is {who} -- PART F did not steal it")

            # --- G: the CLAUSE 2 on-Special-Summon Dragon protection ------------------
            o = _off(SS_TRIGGER_HOOK)
            check(bytes(ov[o:o + 4]) == _bl(SS_TRIGGER_HOOK, SS_STUB),
                  f"0x{SS_TRIGGER_HOOK:08X} == bl 0x{SS_STUB:08X} "
                  f"(the Special-Summon trigger list search is hooked)")
            check(bytes(ov[_off(SS_EVAL):_off(SS_EVAL) + len(SS_EVAL_SIG)]) == SS_EVAL_SIG,
                  f"summon-trigger evaluator 0x{SS_EVAL:08X} signature intact")

            # The reachability argument, re-checked against the built image: the sibling
            # search is still there and still finds the four native "when this card is
            # Synchro Summoned" cards, so our hook is still in the block they execute.
            check(bytes(ov[_off(SS_LIST_PROPER_HOOK):_off(SS_LIST_PROPER_HOOK) + 4])
                  in _anchor_ok(),
                  f"0x{SS_LIST_PROPER_HOOK:08X} is still a sibling `bl` to the list search, "
                  f"directly or via orient_dragon's trampoline (the reachability anchor)")
            proper = struct.unpack_from("<36H", ov, _off(SS_LIST_PROPER))
            missing = [c for c in SS_LIST_PROPER_MEMBERS if c not in proper]
            check(not missing,
                  f"Mist Wurm / Locomotion / Trishula / Vylon Alpha still in the "
                  f"\"when Synchro Summoned\" list 0x{SS_LIST_PROPER:08X}"
                  + (f" -- MISSING {[hex(c) for c in missing]}" if missing else ""))

            # The donor must stay OUT of every Special-Summon trigger list, or the engine
            # would post a cls1 event and drag the shipped clause-3 record onto this path.
            plain = struct.unpack_from("<31H", ov, _off(SS_LIST_PLAIN))
            check(DONOR_CID not in plain and DONOR_CID not in proper,
                  f"donor absent from BOTH Special-Summon trigger lists -- no cls1 event is "
                  f"posted for it, so clause 3's record is never consulted here")

            o = _off(PROT_HOOK)
            check(bytes(ov[o:o + 4]) == _bl(PROT_HOOK, PROT_STUB),
                  f"0x{PROT_HOOK:08X} == bl 0x{PROT_STUB:08X} "
                  f"(Vehicroid Connection Zone's rider link is chained)")
            check(bytes(ov[_off(AFFECT_PRED):_off(AFFECT_PRED) + len(AFFECT_PRED_SIG)])
                  == AFFECT_PRED_SIG,
                  f"affect predicate 0x{AFFECT_PRED:08X} signature intact")

            # COMPOSITION: safe_zone PART D's link in this same function is untouched.
            raw = bytes(ov[_off(SAFE_ZONE_HOOK):_off(SAFE_ZONE_HOOK) + 4])
            sz_bls = (_bl(SAFE_ZONE_HOOK, ov5_cave.CAVE_SZ_TARGET), _bl(SAFE_ZONE_HOOK, _sz_target3()))
            who = "native" if raw == SAFE_ZONE_HOOK_NATIVE else (
                "safe_zone's BL" if raw in sz_bls else f"UNKNOWN ({raw.hex()})")
            if who.startswith("UNKNOWN") and code_reaches(rom, SAFE_ZONE_HOOK, _sz_target3()):
                who = "a later front that tails to safe_zone's stub (march)"
            check(raw == SAFE_ZONE_HOOK_NATIVE or raw in sz_bls or code_reaches(rom, SAFE_ZONE_HOOK, _sz_target3()),
                  f"0x{SAFE_ZONE_HOOK:08X} is {who} -- PART G did not steal Safe Zone's link")

            for label, addr, builder, reserve in (
                    ("G1 on-SS", SS_STUB, _build_ss_protect_stub, SS_STUB_RESERVE),
                    ("G2 query", PROT_STUB, _build_protect_query_stub, PROT_STUB_RESERVE)):
                want = builder(addr)
                got = ov5_cave.read_cave(rom_f, addr, len(want))
                check(got == want, f"ov5 cave 0x{addr:08X} holds the {len(want)}B {label} stub")
                check(len(want) <= reserve,
                      f"{label} stub {len(want)}B fits its 0x{reserve:X}B reserve")
                try:
                    assert_thumb1_only(want, addr)
                    check(True, f"{label} stub is Thumb-1 only")
                except AssertionError as e:
                    check(False, f"{label} stub is NOT Thumb-1 only: {e}")

            # The duration byte IS the clause's "until the end of the next turn".
            check(PROT_KIND_BYTE == 0x12 and PROT_KIND < 6,
                  f"rider kind byte 0x{PROT_KIND_BYTE:02X} = kind {PROT_KIND} (family 1, seen "
                  f"by 0x{NODE_QUERY_F1:08X}) | duration {PROT_DURATION} << 4")

            # CLAUSE 1's OTHER half: "1 or more" survives only while the donor stays OUT of
            # LIST_A. Adding it there would silently impose "EXACTLY 1 non-Tuner".
            list_a = list(struct.unpack_from(f"<{LIST_A_COUNT}H", ov, _off(LIST_A)))
            check(DONOR_CID not in list_a,
                  f"donor absent from LIST_A 0x{LIST_A:08X} -- the \"1 OR MORE non-Tuner\" "
                  f"form is intact ({[hex(x) for x in list_a]})")

            # --- D2 + E: ARM9 and card_prop ------------------------------------------
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
            data = sec.data
            # read the LIVE count -- elder_six_samurai lowers it from 21 to 20
            count = struct.unpack_from("<H", data, AOJ_COUNT_IMM - ARM9_BASE)[0] & 0xFF
            entries = [struct.unpack_from("<H", data, AOJ_TBL + 2 * i - ARM9_BASE)[0]
                       for i in range(count)]
            check(count in (AOJ_COUNT_NATIVE, AOJ_COUNT_ELDER),
                  f"Ally of Justice count immediate is {count} (21 clean / 20 after elder)")
            check(DONOR_CID not in entries,
                  f"0x{DONOR_CID:04X} absent from the Ally of Justice table")
            check(all(entries[i] < entries[i + 1] for i in range(count - 1)),
                  f"Ally of Justice table still {count} entries and STRICTLY sorted")
            check(entries[-1] == AOJ_SENTINEL,
                  f"Ally of Justice tail slot holds the sentinel 0x{AOJ_SENTINEL:04X}")

            pac_path = next(p for p in iter_paths(rom.filenames)
                            if p.lower().endswith("bin2.pac"))
            blob = bytes(rom.files[rom.filenames.idOf(pac_path)])
            ar = parse_pac(blob, pac_path)
            cpf = next(f for f in ar.files if f.get_clean_name().lower() == "card_prop.bin")
            cp = blob[cpf.address:cpf.address + cpf.size]
            idx = next(i for i in range((cpf.size - 8) // 8)
                       if int.from_bytes(cp[8 + i * 8:16 + i * 8], "little") & 0x3FFF == DONOR_CID)
            f = GC.decode_entry(cp[8 + idx * 8:16 + idx * 8])
            check(f["attribute"] == NEW_ATTRIBUTE,
                  f"card_prop attribute == {NEW_ATTRIBUTE} (got {f['attribute']})")
            check(f["race"] == NEW_RACE, f"card_prop race == {NEW_RACE} (got {f['race']})")
            check(f["level"] == NEW_LEVEL, f"card_prop level == {NEW_LEVEL}")
            check(f["real_atk"] == NEW_ATK, f"card_prop ATK == {NEW_ATK}")
            check(f["real_def"] == NEW_DEF, f"card_prop DEF == {NEW_DEF}")
            check(f["card_type_encoded"] == NEW_CARD_TYPE, "card_prop type == Synchro Effect")

        return Compiled(installs=(install,), posts=(apply_setcode_drop,), checks=(check_fn,))


azure_effects = synchro_one_tuner_and_non_tuner_normal_monsters_on_special_summon_dragons_protected_standby_special_summon_normal_from_graveyard

SPEC = card(0x1E9C, azure_effects())

PROPS = card_props("LIGHT", "Dragon", level=9, atk=2500, defense=3000, card_type="Synchro Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_azure.nds")

# Names other modules read (miscellaneousaurus: _bl; the DSL verbs for the protection link: PROT_*, NODE_QUERY_F1, _build_protect_query_stub).
DONOR_CID = 0x1E9C          # Ally of Justice Light Gazer

PROT_KEY      = DONOR_CID        # a PRIVATE key: 0x1E9C has no other live reference
                                 # (PART D1 retargeted its ov3 arm, PART D2 removed its
                                 # arm9 table entry), and both generic kind dispatchers
                                 # route it to their default arm -- the sweeper's
                                 # kind-1/2 arm never reads the key at all, and
                                 # 0x0219FE0C compares it against [sp+0x28] = 0x1E08.
PROT_KIND     = 0x02            # node kind 2 -> family 1 (0x021A1430 sees it) AND the
                                 # per-turn countdown arm 0x0219FA3E of the sweeper
PROT_DURATION = 1               # THE "until the end of the NEXT turn" NUMBER.
                                 # The node sweeper 0x0219F9E0 runs EXACTLY once per
                                 # turn: its only caller 0x021C1358 is inside the
                                 # handler for animation opcode 3, queued by the
                                 # phase-8 handler 0x02258C3C at step 0, and that same
                                 # handler's next step queues opcode 4 -> 0x021C102C,
                                 # the sole site that does
                                 #   [0x0229DD14+0x34] ^= 1   (toggle turn player)
                                 #   [0x0229DD14+0x40] += 1   (turn counter)
                                 # The kind-1/2 arm is `n = [node+2]>>4 ;
                                 # if n == 0: free else n -= 1`, so n = 1 survives the
                                 # sweep at the end of the summoning turn and is freed
                                 # by the sweep at the end of the following one.
PROT_KIND_BYTE = PROT_KIND | (PROT_DURATION << 4)      # 0x12
SS_STUB        = ov5_cave.CAVE_AZURE_SSPROT
SS_STUB_RESERVE = 0x60

# (c) THE PROTECTION. 0x021B021C is the general "may this card effect affect this
# monster" predicate; 0x021B0296 is its PROTECTED exit (it returns the caller's
# [sp+0x58], which the main wrapper 0x021B0848 supplies as 0) and 0x021B081E its
# "affectable" exit.  At 0x021B058C it queries Vehicroid Connection Zone's family-1
# rider and, on a hit, takes the protected exit.
#
# WHY THIS LINK AND NOT HEART OF CLEAR WATER'S AT 0x021B05CC:
#   1. 0x021B05CC is already claimed by safe_zone PART D.
#   2. 0x021B05CC is INSIDE the `targets` block (the flag is read at 0x021B05BE),
#      which is the entire origin of Safe Zone's documented divergence
#      "a non-targeting destruction still resolves".  0x021B0592 is BEFORE that gate.
#   3. A non-targeting destruction demonstrably passes through here: caller
#      0x02245B7A calls the wrapper with targets = 0 and, only if the predicate says
#      "affectable", calls 0x021CF35C -> 0x021CF31C -> 0x021CDD4C(desc, mask, 0x0E, 2)
#      -- destination zone 0x0E = the Graveyard, i.e. it destroys the monster.
#   4. It is on the live path, proven by a SHIPPED in-game result: Safe Zone PART D's
#      hook at 0x021B05CC is in-game confirmed, and control reaches 0x021B05CC only
#      by first executing 0x021B0592.
# Neither this link nor Dreadmaster's at 0x021B05FA applies a controller test, so
# simply omitting Safe Zone's opponent check gives "neither player" for free.
PROT_HOOK      = 0x021B0592      # the `bl 0x021A1430` querying VCZ's rider
NODE_QUERY_F1  = 0x021A1430      # family-1 rider query (kind < 6, key@+0 IS a cid)
AFFECT_PRED    = 0x021B021C      # the enclosing predicate
AFFECT_PRED_SIG = bytes.fromhex("f8b590b00e1c1699")     # push {r3-r7,lr} ; sub sp,#0x40 ; ...
VCZ_CID        = 0x1A5C          # Vehicroid Connection Zone -- its query is replayed
SAFE_ZONE_HOOK = 0x021B05CC      # safe_zone PART D's link in the SAME function
SAFE_ZONE_HOOK_NATIVE = bytes.fromhex("f0f7c0f9")      # bl 0x021A0950


def _sz_target3() -> int:
    from otn_enhanced.effects import cave3
    return cave3.CAVE3_SZ_TARGET
PROT_STUB      = ov5_cave.CAVE_AZURE_PROT
PROT_STUB_RESERVE = 0x30


# ===========================================================================
# helpers
# ===========================================================================


def _bl(src: int, dst: int) -> bytes:
    """ARMv4T two-halfword BL (Thumb-1 long branch-with-link)."""
    off = dst - (src + 4)
    assert -(1 << 22) <= off < (1 << 22), f"BL 0x{src:08X}->0x{dst:08X} out of range"
    return struct.pack("<HH", 0xF000 | ((off >> 12) & 0x7FF), 0xF800 | ((off >> 1) & 0x7FF))



def _build_protect_query_stub(base: int) -> bytes:
    """Assemble the protection query link for 0x021B021C.

    Entered by BL from 0x021B0592, where the "may this card effect affect this
    monster" predicate asks whether Vehicroid Connection Zone's rider is on the
    target.  On entry:

        r0 = the TARGET's side (r6)   r1 = the TARGET's slot (r5)   r2 = 0x1A5C

    and the caller's own test is `cmp r0,#0 ; beq <continue> ; b 0x021B0296`, so a
    non-zero return is already wired to the predicate's PROTECTED exit -- this stub
    needs no frame surgery at all, unlike safe_zone PART D's insert.

    It replays VCZ's query untouched and only on a MISS asks the same question about
    our own key, so Vehicroid Connection Zone keeps working byte-for-byte.

    NO controller test: the clause protects from BOTH players, and neither this link
    nor Dreadmaster's at 0x021B05FA applies one, so omitting it is the whole change.
    """
    from otn_enhanced.asm.effect_builder import EffectBuilder, R3, R4, R5, R6, R7
    from otn_enhanced.asm.effect_verify import assert_thumb1_only

    a = EffectBuilder()
    a.prologue([R3, R4, R5, R6, R7])
    a.insn("MOV", "R4, R0")              # side
    a.insn("MOV", "R5, R1")              # slot
    a.bl(NODE_QUERY_F1)                  # replay -- r0/r1/r2 are the caller's args
    a.insn("CMP", "R0, #0x0")
    a.insn("BNE", "done")                # VCZ matched -> hand back its answer
    a.insn("MOV", "R0, R4")
    a.insn("MOV", "R1, R5")
    a.ldr_const(2, PROT_KEY)
    a.bl(NODE_QUERY_F1)                  # our rider -> 1 = protected
    a.label("done")
    a.insn("POP", "{R3, R4, R5, R6, R7, PC}")

    code = a.assemble(base)
    assert_thumb1_only(code, base)
    assert len(code) <= PROT_STUB_RESERVE, (
        f"PART G protect stub is {len(code)}B > the {PROT_STUB_RESERVE}B cave reserve")
    return code



if __name__ == "__main__":
    if "--verify" in sys.argv:
        raise SystemExit(0 if verify() else 1)
    main(write_text="--text" in sys.argv)
