"""Upstart Golden Ninja (LIGHT / Warrior / Level 4 / 500 / 1800) on The Gross Ghost of Fled Dreams 0x1464.

    Once per turn: You can send 1 Trap Card from your hand to the Graveyard; Special Summon 1 Level 4 or lower "Ninja"
    monster from your Deck.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import SetCodeTable, archetype_member, card, card_props, Compiled
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
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class once_per_turn_per_copy_send_trap_from_hand_special_summon_level_4_ninja_from_deck:
    """'Once per turn: send 1 Trap from your hand to the GY; Special Summon 1 Level 4 or lower "Ninja" monster from your Deck.'
    cls3 record (Gem-Knight Alexandrite's deck-SS resolver) + ignition-condition registry row cloned from Beast Striker
    (0x021F0BDD is a per-cid registry LOOKUP, not a generic condition: an unregistered donor is never offered) + two criteria rows
    in this order: rel 0 = the Deck effect row (the offer check probes rel 0 and a hand row there is index-only), rel 1 = the
    hand Trap cost row; the shared row-disambiguation hook arm picks rel 0 / rel 1 from the cost machine's state word. ov5: a
    condition that scans the hand for a legal cost (else the discard picker soft-locks) and a cost that posts the PER-COPY 0x0FB6
    rider via the shared "you can" tag (a cid-keyed turn log locked every copy) and runs the native hand send."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.effects import criteria_row_hook
        from otn_enhanced.effects.common import ov3_off, row_keys, record_present, insert_row_wide
        DONOR_CID = cid
        PLAYER_BASE = 0x0229AC94           # side 0; side 1 is + PLAYER_STRIDE
        PLAYER_STRIDE = 0xB3C
        HAND_COUNT_OFF = 0x0C              # ram.container_for_zone_code: hand @+0x124, count @+0x0C
        CANDIDATE_PROBE = 0x02243FE0       # (side, cid, param) -- param is the HAND INDEX here
        SETCODE_PTR_TABLE = 0x0209D0D8     # has_set_code pointer table; index N -> thunk for code N
        NINJA_SETCODE = 0x06
        NINJA_THUNK = 0x020237D8
        NINJA_COUNT_IMM = 0x020237DC       # `movs r2,#9`
        NINJA_LIST_POOL = 0x020237E0
        NINJA_LIST = 0x0209C722
        NINJA_COUNT = 9
        NINJA_DROP = 0x16B8                # Crimson Ninja, Lv1 400/700 -- the weakest member, and
                                           # the only sort-neutral choice in BOTH chain orders

        # ===========================================================================
        # PART B -- the two criteria rows
        # ===========================================================================
        CRIT_BASE = 0x022713C4
        CRIT_STRIDE = 12
        CRIT_COUNT = 1391                  # includes the trailing a=0xFFFF sentinel
        CRIT_FMT = "<HHII"

        HAND_SEND = 0x0223CB65             # send/discard from the HAND
        DECK_SS = 0x0223CAB5               # set-code-filtered Special Summon from the DECK
        NINJA_AUX = NINJA_SETCODE          # aux 0x06 -- the "Ninja" has_set_code index
        AUX_NONE = 0xFFFF                  # no set-code filter

        WORD_TRAP = 0x00000008             # card-type bitmask: 8 = Trap
        WORD_LV4_MONSTER = 0x00900002      # (0x80 | 4 << 2) << 16 | 2 = "Level 4 or lower monster"

        CRIT_COST = (DONOR_CID, AUX_NONE, HAND_SEND, WORD_TRAP)          # rel 0
        CRIT_EFFECT = (DONOR_CID, NINJA_AUX, DECK_SS, WORD_LV4_MONSTER)  # rel 1
        CRIT_DROP_COST = 0x1449            # crit[130], phantom, unclaimed in every pool
        CRIT_DROP_EFFECT = 0x144C          # crit[131], phantom, unclaimed; PART D retires it too

        # ===========================================================================
        # PART D -- the cls3 record
        # ===========================================================================
        CLS3_BASE = 0x02279D74
        CLS3_STRIDE = 24
        CLS3_COUNT = 0x308
        CLS3_FMT = "<IIIIII"
        CLS3_DROP = 0x144C                 # cls3[71], the same phantom PART B retires

        DECK_SS_RESOLVER = 0x02206CAD      # counter.deck_ss_resolver
        IGNITION_COND = 0x021F0BDD         # shared by Beast Striker 0x20B8 + Alexandrite 0x22C0
        HAND_COST = 0x021E7245             # native "send N from hand"; donor default N = 1

        # ===========================================================================
        # PART H -- the ignition-condition registry row  (THE FIX FOR IN-GAME TEST 1)
        # ===========================================================================
        # In-game test 1 FAILED: selecting the donor showed no activate-effect
        # prompt.  The savestate cleared every table -- both criteria rows live and in the
        # right order, the cls3 record live, all three ov5 stubs resident, the donor face-up
        # on side 0 zone 2, a Ninjitsu Art Trap in hand and three Level 4 Ninjas in the Deck.
        #
        # THE CAUSE: 0x021F0BDD IS NOT A GENERIC CONDITION.  It is a per-cid REGISTRY LOOKUP:
        #
        #     021F0BE4  ldr  r1,=0x0226FAFC   ; 146 rows
        #     021F0BE6  movs r2,#0x92 ; movs r3,#0xC
        #     021F0BEA  bl   0x02022E44       ; binary search BY CID
        #     021F0BF0  beq  0x021F0C0C       ; NOT FOUND -> movs r0,#0 ; return   <<< THE GATE
        #     021F0BF2  ldr  r2,[r4,#4] ; blx r2      ; f1, a precondition
        #     021F0BFE  ldr  r2,[r4,#8] ; blx r2      ; f2, the candidate check -> the result
        #
        # so an unregistered donor is never offered.  Reasoning that this slot was
        # "card-agnostic" because Beast Striker AND Alexandrite share it was the error: a
        # SHARED slot is not a CID-BLIND one.
        #
        # THE ROW is Beast Striker's -- the native card with this exact shape ("Once per
        # turn, you can discard 1 card to Special Summon 1 'Moja' from your Deck").  BOTH of
        # its function pointers were checked for cid gates this time instead of assumed:
        #   f1 0x021F024D -- `ldrb r0,[r5,#2] ; ldrb r1,[r5,#3] ; ldr r2,=0x0FB6 ;
        #      bl 0x021A1430` = the attached-node walker querying the 0x0FB6 once-per-turn
        #      rider, then chaining 0x021F0220.  NO cid compare.
        #   f2 0x021F0419 -- side = desc[+2]^desc[+6], gate 0x021F0384, then
        #      param = 0x02234E78(desc) and 0x02243FE0(side, desc[+0], param) = the candidate
        #      count.  NO cid compare.  At the menu desc[+7] == 0, so it probes rel 0 = the
        #      Trap-in-hand row, and the tested hand did hold 0x17FF.
        # NOTE f1 enforces once-per-turn through the 0x0FB6 rider, which this patch never
        # posts -- so f1 always passes and PART E's turn-log latch remains what enforces OPT.
        # The two mechanisms do not conflict; the native one is simply inert here.
        IGNITION_REG = 0x0226FAFC
        IGNITION_REG_COUNT = 0x92
        IGNITION_REG_STRIDE = 0xC
        IGNITION_REG_FMT = "<HHII"
        IGNITION_F1 = 0x021F024D           # Beast Striker's precondition (0x0FB6 rider query)
        IGNITION_F2 = 0x021F0419           # Beast Striker's candidate check
        IGNITION_NEW = (DONOR_CID, 0x0000, IGNITION_F1, IGNITION_F2)
        IGNITION_DROP = 0x1446             # phantom row 11, ALREADY at the donor's sorted
                                           # position (0x1446 < 0x1464 < 0x14A7 Rope of Life),
                                           # so the insert shifts ZERO rows.  The table's
                                           # seven phantoms are 0x0E3E 0x0E7D 0x0E86 0x0EA9
                                           # 0x0EAE 0x1446 0x1748; this is the only one at
                                           # the donor's index.

        # ===========================================================================
        # PART E -- the once-per-turn stubs
        # ===========================================================================
        # ⚠️ NOT the cid-keyed turn log any more.  In-game test 2: with the turn log, the
        # FIRST copy's use locked EVERY copy for the turn, so a second Upstart summoned by
        # the first had no effect in its menu (rom_upstart.ml4 shows both donors on the
        # field).  The printed text is once per turn PER COPY.
        # 0x021E5060 is the shared "you can" tag and it posts the PER-COPY 0x0FB6 rider:
        #     021E5070  ldrb r0,[r4,#2]   ; side
        #     021E5072  ldrb r1,[r4,#3]   ; SLOT  <- per copy, not per cid
        #     021E5074  ldr  r2,=0x0FB6
        #     021E5078  bl   0x021C479C   ; attach
        # which is exactly what PART H's registry row f1 (0x021F024D) already QUERIES via
        # 0x021A1430(desc[+2], desc[+3], 0x0FB6).  Posting it here means the native
        # condition enforces once-per-turn per copy and this patch needs no condition stub
        # of its own -- cls3 +0C goes back to the stock 0x021F0BDD.
        YOU_CAN_TAG = 0x021E5060           # posts the per-copy 0x0FB6 once-per-turn rider
        COST_STATE_BLOCK = 0x0229AAFC      # the cost's own state word lives at +0x7C
        COST_STATE_OFF = 0x7C
        CAVE_RESERVE_COST = 0x60
        CAVE_RESERVE_COND = 0x80

        def build_cond_stub(base: int) -> bytes:
            """cls3 +0C: refuse the effect unless the hand actually holds a legal cost.

            THE SOFT-LOCK THIS FIXES (in-game test 3): the stock condition 0x021F0BDD
            probes rel 0 only -- the DECK row -- so with a Ninja in the Deck but NO TRAP
            in hand the effect was still offered, and activating it opened the discard
            picker with zero candidates and no way out.  The user's words: "I am trapped
            in the 'choose a card to discard' but cannot select a card to discard."

            ⚠️ THE SCAN MUST LOOP.  0x02243FE0 tests only hand slot `param` -- measured on
            rom_upstart.ml3: a hand of [filler, Trap] returns 0 at param 0 and 1 at
            param 1, and [filler, filler, Trap] returns 1 only at param 2.  A single
            param-0 probe is exactly the mistake that made in-game test 1 fail.

            While the scan runs, CAVE_UGN_PROBE tells the shared row hook to hand back
            rel 1 (the Hand/Trap row).  That latch is safe -- unlike the STAGE byte test 2
            killed -- because 0x02243FE0 is a SYNCHRONOUS count that has already returned
            before the byte is cleared, not an asynchronous picker.

            r4 = desc, r5 = side, r6 = hand count, r7 = the loop index.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x6]")
            b.insn("EOR", "R0, R1")
            b.insn("ADD", "R5, R0, #0x0")
            b.ldr_const(6, PLAYER_BASE)
            b.insn("CMP", "R5, #0x0")
            b.insn("BEQ", "havebase")
            b.ldr_const(0, PLAYER_STRIDE)
            b.insn("ADD", "R6, R6, R0")
            b.label("havebase")
            b.insn("LDR", f"R6, [R6, #0x{HAND_COUNT_OFF:X}]")
            b.insn("MOV", "R7, #0x0")
            b.label("loop")
            b.insn("CMP", "R7, R6")
            b.insn("BGE", "none")
            b.ldr_const(0, ov5_cave.CAVE_UGN_PROBE)
            b.insn("MOV", "R1, #0x1")
            b.insn("STRB", "R1, [R0, #0x0]")
            b.insn("ADD", "R0, R5, #0x0")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(CANDIDATE_PROBE, R0, R1, R7, via=R3)
            b.insn("ADD", "R1, R0, #0x0")
            b.ldr_const(0, ov5_cave.CAVE_UGN_PROBE)
            b.insn("MOV", "R2, #0x0")
            b.insn("STRB", "R2, [R0, #0x0]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BNE", "found")
            b.insn("ADD", "R7, #0x1")
            b.insn("B", "loop")
            b.label("none")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("found")
            b.call_addr(IGNITION_COND, R4, via=R3)
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def build_cost_stub(base: int) -> bytes:
            """cls3 +10: stamp the once-per-turn latch once, then run the native cost.

            Called as slot4(desc, r1) -> the native cost's own return value.  The native
            0x021E7245 is a four-state machine on [0x0229AAFC + 0x7C]; the latch is posted
            on STATE 0 only, which is the activation moment.

            ⚠️ dispatch.once_per_turn_must_stamp_at_activation: a latch stamped in the
            RESOLVER loses to the chain -- measured in-game on Maiden, which could be
            activated twice in one chain.  Stamping here, in the cost, is the fix.
            ⚠️ r1 is preserved across the wrapper: the native cost is a 2-argument entry
            and the slot4 wrapper 0x0224AE50 supplies r1.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.ldr_const(6, COST_STATE_BLOCK)
            b.insn("LDR", f"R6, [R6, #0x{COST_STATE_OFF:X}]")
            b.insn("CMP", "R6, #0x0")
            b.insn("BNE", "run")
            b.call_addr(YOU_CAN_TAG, R4, via=R6)
            b.label("run")
            b.call_addr(HAND_COST, R4, R5, via=R2)
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")

        def _assert_preconditions(ov: bytearray) -> None:
            """Everything this patch reuses must still be where it is believed to be.

            Anchored on CIDS and on instruction bytes, never on a row index
            (otn-chain-build-verify-artifact: a row index moves when an earlier patch in
            the chain inserts).
            """
            crit = row_keys(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, False)

            def row_of(cid: int) -> tuple:
                i = crit.index(cid)
                return struct.unpack_from(CRIT_FMT, ov, ov3_off(CRIT_BASE + i * CRIT_STRIDE))

            # the two template rows this patch clones, still byte-exact
            assert row_of(0x2182) == (0x2182, 0xFFFF, HAND_SEND, 0x00000004), \
                "B  Naturia Landoise's hand-send row changed -- the cost template is gone"
            assert row_of(0x1B3A) == (0x1B3A, 0x001E, DECK_SS, 0x008C0002), \
                "B  Shien's Footsoldier's deck-SS row changed -- the effect template is gone"

            # the cls3 template record (Gem-Knight Alexandrite), still byte-exact
            cls3 = row_keys(ov, CLS3_BASE, CLS3_COUNT, CLS3_STRIDE, True)
            i = cls3.index(0x22C0)
            alex = struct.unpack_from(CLS3_FMT, ov, ov3_off(CLS3_BASE + i * CLS3_STRIDE))
            assert alex == (0x22C0, DECK_SS_RESOLVER, 0, IGNITION_COND, 0x021E50CD, 0), \
                f"D  Gem-Knight Alexandrite's cls3 record changed: {[hex(x) for x in alex]}"

            # the donor is genuinely records-free in the two tables this patch writes
            assert DONOR_CID not in cls3 or record_present(
                ov, CLS3_BASE, CLS3_COUNT, CLS3_STRIDE, CLS3_FMT, _cls3_record()), \
                f"D  0x{DONOR_CID:04X} already owns a cls3 record that is not ours"

            # PART H: the gate that broke in-game test 1, and Beast Striker's template row.
            # Pinned by INSTRUCTION BYTES so a future session cannot re-derive the same
            # "this slot is generic" mistake -- if the lookup ever stops being a per-cid
            # search, this assert is where that shows up.
            assert struct.unpack_from("<H", ov, ov3_off(0x021F0BE6))[0] == 0x2292, \
                "H  0x021F0BE6 is no longer `movs r2,#0x92` -- the ignition registry resized"
            assert struct.unpack_from("<H", ov, ov3_off(0x021F0BE8))[0] == 0x230C, \
                "H  0x021F0BE8 is no longer `movs r3,#0xC` -- the registry stride changed"
            ign = row_keys(ov, IGNITION_REG, IGNITION_REG_COUNT, IGNITION_REG_STRIDE, False)
            assert all(ign[i] <= ign[i + 1] for i in range(len(ign) - 1)), \
                "H  the ignition-condition registry is not sorted (it is binary-searched)"
            bs = ign.index(0x20B8)
            assert struct.unpack_from(IGNITION_REG_FMT, ov,
                                      ov3_off(IGNITION_REG + bs * IGNITION_REG_STRIDE)) == \
                (0x20B8, 0x0000, IGNITION_F1, IGNITION_F2), \
                "H  Beast Striker's ignition registry row changed -- the template is gone"

            # PART E's two call targets, pinned by their prologues
            assert struct.unpack_from("<H", ov, ov3_off(HAND_COST & ~1))[0] == 0xB5F8, \
                f"E  the native hand cost 0x{HAND_COST:08X} lost its `push {{r3-r7,lr}}`"
            # ... and its donor-default send count of exactly 1 (`movs r7,#1`)
            assert struct.unpack_from("<H", ov, ov3_off(0x021E724C))[0] == 0x2701, \
                "E  0x021E724C is no longer `movs r7,#1` -- the donor's send count may not be 1"

            # PART C's discriminator: the activation machine still sets desc[+7] after the cost
            assert struct.unpack_from("<H", ov, ov3_off(0x02217F8E))[0] == 0x79E8, \
                "C  0x02217F8E is no longer `ldrb r0,[r5,#7]` -- the cost flag moved"
            assert struct.unpack_from("<H", ov, ov3_off(0x02217FB4))[0] == 0x71E8, \
                "C  0x02217FB4 is no longer `strb r0,[r5,#7]` -- the cost flag moved"


        def _cls3_record() -> tuple:
            # +0C is OUR condition stub, which scans the hand for a legal cost and only
            # then chains the stock 0x021F0BDD (whose f1 checks the per-copy 0x0FB6 rider
            # and whose f2 checks the Deck).  Without that scan the effect is offered with
            # no Trap in hand and the discard picker soft-locks -- in-game test 3.
            return (DONOR_CID, DECK_SS_RESOLVER, 0,
                    ov5_cave.CAVE_UGN_COND | 1, ov5_cave.CAVE_UGN_COST | 1, 0)


        def apply_effect(ov: bytearray) -> None:
            _assert_preconditions(ov)

            # -- PART B: the EFFECT row FIRST (rel 0), then the cost row (rel 1) ------
            # ⚠️ THIS ORDER IS THE OPPOSITE OF THE FIRST BUILD, AND THE REASON IS MEASURED.
            # The offer-check 0x021F0419 probes REL 0, and on a HAND row 0x02243FE0's param
            # is a candidate INDEX rather than a row selector -- so a hand row at rel 0 only
            # ever tests hand slot 0.  In-game test 1 failed exactly there: the Trap sat at
            # hand index 4 and the effect was never offered.  With the DECK row at rel 0 the
            # probe returns a real count (measured: 5 legal Ninjas on that same board) and
            # slot3 returns 1 = offered.
            insert_row_wide(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, CRIT_FMT,
                           CRIT_EFFECT, CRIT_DROP_EFFECT, "B1 criteria (C2 effect, Lv<=4 Ninja)",
                           wide=False)
            insert_row_wide(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, CRIT_FMT,
                           CRIT_COST, CRIT_DROP_COST, "B2 criteria (C1 cost, Trap from hand)",
                           wide=False, after_same_cid=True, expect_dupe=True)
            _assert_row_order(ov)

            # -- PART D: the cls3 record ---------------------------------------------
            insert_row_wide(ov, CLS3_BASE, CLS3_COUNT, CLS3_STRIDE, CLS3_FMT,
                           _cls3_record(), CLS3_DROP, "D  cls3 record", wide=True)

            # -- PART H: the ignition-condition registry row -------------------------
            # Without this the effect is never OFFERED: 0x021F0BDD binary-searches this
            # table by cid and returns 0 on a miss.  (In-game test 1 failed exactly here.)
            insert_row_wide(ov, IGNITION_REG, IGNITION_REG_COUNT, IGNITION_REG_STRIDE,
                           IGNITION_REG_FMT, IGNITION_NEW, IGNITION_DROP,
                           "H  ignition-condition registry row", wide=False)

            # -- PART C: the shared row-disambiguation hook ---------------------------
            criteria_row_hook.apply(ov)


        def _donor_rows(ov: bytearray) -> list[tuple]:
            crit = row_keys(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, False)
            return [struct.unpack_from(CRIT_FMT, ov, ov3_off(CRIT_BASE + i * CRIT_STRIDE))
                    for i, c in enumerate(crit) if c == DONOR_CID]


        def _assert_row_order(ov: bytearray) -> None:
            """rel 0 MUST be the EFFECT (Deck) row and rel 1 MUST be the COST (hand) row.

            Load-bearing, not cosmetic, and the order that in-game test 1 got wrong:
            the offer-check probes rel 0, and a HAND row there is only ever tested at
            hand slot `param` (= 0), so the card was offered only when the Trap happened
            to be the first card in hand.  PART C's arm hands out rel 0 / rel 1 from the
            STAGE byte in this exact order.
            """
            rows = _donor_rows(ov)
            assert len(rows) == 2, f"B  the donor owns {len(rows)} criteria rows, expected 2"
            assert rows[0] == CRIT_EFFECT, \
                f"B  rel 0 is {[hex(x) for x in rows[0]]}, expected the C2 effect (Deck) row"
            assert rows[1] == CRIT_COST, \
                f"B  rel 1 is {[hex(x) for x in rows[1]]}, expected the C1 cost (hand) row"
            print(f"B  row order OK: rel 0 = effect/Deck {[hex(x) for x in rows[0]]}, "
                  f"rel 1 = cost/hand {[hex(x) for x in rows[1]]}")

        def install(rom, view):
            apply_effect(view.buf)
            criteria_row_hook.install(rom)

        def check_fn(c, rom, view):
            ov = view.buf

            def check(cond, msg):
                c.ok(bool(cond), msg)
                return bool(cond)

            rows = _donor_rows(ov)
            check(len(rows) == 2, f"B  the donor owns exactly 2 criteria rows (has {len(rows)})")
            if len(rows) == 2:
                check(rows[0] == CRIT_EFFECT,
                      f"B  rel 0 is the C2 effect row {{0x{NINJA_AUX:04X}, 0x{DECK_SS:08X}, "
                      f"0x{WORD_LV4_MONSTER:08X}}} (Lv<=4 Ninja from the DECK -- rel 0 because "
                      f"the offer-check probes it and a hand row there is index-only)")
                check(rows[1] == CRIT_COST,
                      f"B  rel 1 is the C1 cost row {{0xFFFF, 0x{HAND_SEND:08X}, 0x{WORD_TRAP:08X}}} "
                      f"(Trap, from the hand)")
            crit = row_keys(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, False)
            check(all(crit[i] <= crit[i + 1] for i in range(len(crit) - 1)),
                  "B  the criteria table is still sorted")
            check(CRIT_DROP_COST not in crit and CRIT_DROP_EFFECT not in crit,
                  f"B  both phantoms 0x{CRIT_DROP_COST:04X}/0x{CRIT_DROP_EFFECT:04X} were consumed")
            check(len(crit) == CRIT_COUNT, f"B  the criteria table is still {CRIT_COUNT} rows")

            # the two native templates must be unregressed
            def row_of(cid: int) -> tuple:
                i = crit.index(cid)
                return struct.unpack_from(CRIT_FMT, ov, ov3_off(CRIT_BASE + i * CRIT_STRIDE))

            check(row_of(0x2182) == (0x2182, 0xFFFF, HAND_SEND, 0x00000004),
                  "B  Naturia Landoise's row is unregressed")
            check(row_of(0x1B3A) == (0x1B3A, 0x001E, DECK_SS, 0x008C0002),
                  "B  Shien's Footsoldier's row is unregressed")

            # -- PART D ---------------------------------------------------------------
            cls3 = row_keys(ov, CLS3_BASE, CLS3_COUNT, CLS3_STRIDE, True)
            check(record_present(ov, CLS3_BASE, CLS3_COUNT, CLS3_STRIDE, CLS3_FMT, _cls3_record()),
                  "D  the donor's cls3 record is present and byte-exact")
            check(cls3.count(DONOR_CID) == 1, "D  the donor owns exactly ONE cls3 record")
            check(CLS3_DROP not in cls3, f"D  phantom 0x{CLS3_DROP:04X} was consumed")
            check(len(cls3) == CLS3_COUNT and all(cls3[i] <= cls3[i + 1] for i in range(len(cls3) - 1)),
                  f"D  cls3 is still {CLS3_COUNT} records and sorted")
            i = cls3.index(0x22C0)
            check(struct.unpack_from(CLS3_FMT, ov, ov3_off(CLS3_BASE + i * CLS3_STRIDE))
                  == (0x22C0, DECK_SS_RESOLVER, 0, IGNITION_COND, 0x021E50CD, 0),
                  "D  Gem-Knight Alexandrite's cls3 record is unregressed")

            # -- PART H ---------------------------------------------------------------
            ign = row_keys(ov, IGNITION_REG, IGNITION_REG_COUNT, IGNITION_REG_STRIDE, False)
            check(record_present(ov, IGNITION_REG, IGNITION_REG_COUNT, IGNITION_REG_STRIDE,
                                  IGNITION_REG_FMT, IGNITION_NEW),
                  "H  the donor's ignition-condition registry row is present and byte-exact "
                  "(without it 0x021F0BDD returns 0 and the effect is never OFFERED)")
            check(ign.count(DONOR_CID) == 1, "H  the donor owns exactly ONE registry row")
            check(IGNITION_DROP not in ign, f"H  phantom 0x{IGNITION_DROP:04X} was consumed")
            check(len(ign) == IGNITION_REG_COUNT
                  and all(ign[i] <= ign[i + 1] for i in range(len(ign) - 1)),
                  f"H  the registry is still {IGNITION_REG_COUNT} rows and sorted")
            bs = ign.index(0x20B8)
            check(struct.unpack_from(IGNITION_REG_FMT, ov,
                                     ov3_off(IGNITION_REG + bs * IGNITION_REG_STRIDE))
                  == (0x20B8, 0x0000, IGNITION_F1, IGNITION_F2),
                  "H  Beast Striker's registry row is unregressed")

            # -- PART E ---------------------------------------------------------------
            for addr, blob, what in (
                    (ov5_cave.CAVE_UGN_COST, build_cost_stub(ov5_cave.CAVE_UGN_COST), "cost"),
                    (ov5_cave.CAVE_UGN_COND, build_cond_stub(ov5_cave.CAVE_UGN_COND),
                     "condition (hand scan)")):
                check(ov5_cave.read_cave(rom, addr, len(blob)) == blob,
                      f"E  the {what} stub is installed at 0x{addr:08X} ({len(blob)} B)")
            check(ov5_cave.read_cave(rom, ov5_cave.CAVE_UGN_PROBE, 4) == b"\0" * 4,
                  "E  the hand-probe flag ships CLEAR (it is set only inside the scan)")
            check(struct.unpack_from("<H", ov, ov3_off(0x021E724C))[0] == 0x2701,
                  "E  the native hand cost still defaults to `movs r7,#1` (send exactly 1)")

            # -- PART C ---------------------------------------------------------------
            criteria_row_hook.verify(ov, check, rom=rom)
            check(any(cid == DONOR_CID for cid, _t, _b, _d in criteria_row_hook.ARMS),
                  f"C  0x{DONOR_CID:04X} is a registered arm on the shared row hook")
            # The arm keys on the cost machine's state word, so what must hold is that the
            # activation machine ZEROES it once the cost is done -- otherwise the deck-SS
            # resolver would keep reading the Hand row.
            check(struct.unpack_from("<H", ov, ov3_off(0x02217FB6))[0] == 0x2100,
                  "C  0x02217FB6 is still `movs r1,#0`")
            check(struct.unpack_from("<H", ov, ov3_off(0x02217FBA))[0] == 0x67E1,
                  "C  the activation machine still zeroes the cost state [0x0229AAFC+0x7C] "
                  "when the cost finishes (the arm's whole basis)")
            # and the per-copy once-per-turn rider the cost posts is the one f1 queries
            check(struct.unpack_from("<H", ov, ov3_off(0x021E5070))[0] == 0x78A0,
                  "E  0x021E5070 is still `ldrb r0,[r4,#2]` (side) in the you-can tag")
            check(struct.unpack_from("<H", ov, ov3_off(0x021E5072))[0] == 0x78E1,
                  "E  0x021E5072 is still `ldrb r1,[r4,#3]` -- the tag keys on the SLOT, "
                  "which is what makes the once-per-turn latch PER COPY")

        stubs = ((ov5_cave.CAVE_UGN_COST, build_cost_stub(ov5_cave.CAVE_UGN_COST), "cost"),
                 (ov5_cave.CAVE_UGN_COND, build_cond_stub(ov5_cave.CAVE_UGN_COND), "condition"))
        for addr, blob, _w in stubs:
            assert_thumb1_only(blob, addr)
        return Compiled(stubs, installs=(install,), checks=(check_fn,))


upstart_effect = once_per_turn_per_copy_send_trap_from_hand_special_summon_level_4_ninja_from_deck

NINJA_TABLE = SetCodeTable("Ninja", 0x0209C722, 9, (0x020237E0,), (0x020237DC,))

SPEC = card(
    0x1464,
    upstart_effect(),
    archetype_member(NINJA_TABLE, phantom=0x16B8))     # Crimson Ninja: the weakest member, sort-neutral in both chain orders

PROPS = card_props("LIGHT", "Warrior", level=4, atk=500, defense=1800)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_upstart.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
