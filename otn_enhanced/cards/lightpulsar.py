"""Lightpulsar Dragon (LIGHT / Dragon / Effect Monster / Level 6 / 2500 / 1500) on Sword Arm of Dragon 0x0FB1.

    (See card_text.CARD_TEXT[0x0FB1] for the full printed text.)
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, SRC
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R6
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class special_summon_self_from_hand_or_graveyard_by_banishing_light_and_dark_hand_clause_sent_to_graveyard_revive_light_or_dark_dragon:
    """Lightpulsar Dragon (Sword Arm of Dragon 0x0FB1, LIGHT / Dragon / Level 6 / 2500 / 1500): clause 1 'You can Special Summon this card from your
    hand or Graveyard by banishing 1 LIGHT and 1 DARK monster', clause 2 (hand LIGHT+DARK gate, send-to-GY cost) and clause 3 (when sent to the
    Graveyard, revive a monster; leave-mask row + timing class). Routing/count/criteria/membership edits, the shared banish-cost payment side, the
    summon-procedure row, the donor's hand rows, the cls2 record, the GY-action registry row, the leave-mask row and the shared timing hook run in
    `apply_effect`; the shared criteria-row hook, the two dispatchers and the clause-2 cost/condition stubs go to ov5. Original code embedded verbatim
    and run in `install` in the old order (the module global _PAY2_STUB_BASE is a compile-local via nonlocal)."""

    def compile(self, view, cid) -> Compiled:
        import struct
        from otn_enhanced.asm import effect_verify
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.effects import handss_banish_cost as banish
        from otn_enhanced.effects import criteria_row_hook as rowhook
        from otn_enhanced.effects import timing_class_hook as timinghook
        from otn_enhanced.cards import boggart_knight as boggart
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R3, R4, R6
        from otn_enhanced.effects.common import ov3_off as _off
        from otn_enhanced.effects.common import bl as _bl
        from otn_enhanced.effects.common import b as _b

        SRC = "data/over_the_nexus/working/rom.nds"
        OUT = "data/over_the_nexus/working/rom_lightpulsar.nds"

        # ---------------------------------------------------------------------------
        # THE ROW HOOK -- how this donor reaches criteria rows past index 1.
        #
        # Dark Simorgh reaches its rows 2/3 through a HAND-WRITTEN ARM in the compiled
        # disambiguation switch inside 0x02243B9C (dispatch.simorgh_row_offset_is_a_
        # bespoke_switch_arm): for a param below 1<<28 it does r4 = 2 + (desc[+0x12] != 0).
        # A donor cannot be added to that switch by data, so we hook 0x02243BEC and supply
        # the equivalent arm ourselves -- which is what lets clause 2's rows sit on the
        # DONOR at rel 2/3 and clause 3's at rel 4.
        #
        # (Historical: an earlier design used a PROXY cid plus a desc[+0] swap instead.
        # The swap broke re-entry -- find_event_handler binary-searches cls2 by desc[+0],
        # so the cost was never called a second time -- and the whole scaffolding, proxy
        # cid included, went away when this hook replaced it. Only the proxy's two
        # criteria rows are still consumed, as the count-neutral drop for the rel-2/3
        # insert. See notes/lightpulsar-findings.md.)
        #
        # ⚠️⚠️ THE HOOK IS ON THE SHARED ROW RESOLVER and its stub is in ov5, so in a
        # PUZZLE every card that selects anything would jump into overlay-41 data.
        # DUEL-ONLY, by explicit user decision.
        # ---------------------------------------------------------------------------

        ROWHOOK_SITE = 0x02243BEC       # `ldr r1,=0x0227134C ; adds r0,r5,#0`  (4 B)
        ROWHOOK_RESUME = 0x02243BF0     # the `movs r2,#0x3b` that follows
        ROWHOOK_TAIL = 0x02243EEE       # the common tail: r2 = leftmost + r4
        LISTA_LIT = 0x0227134C

        DONOR_CID = 0x0FB1                  # Sword Arm of Dragon

        # ---------------------------------------------------------------------------
        # PART A -- the dead arm we repoint
        # ---------------------------------------------------------------------------
        ARM_CMP = 0x0225E6E0                # `adds r0,#imm8`; r0 = ARM_BASE + imm8
        ARM_BASE = 0x0EB3                   # value in r0 when the arm is reached
        ARM_OLD_IMM = 0x17                  # -> 0x0ECA, a phantom
        ARM_NEW_IMM = DONOR_CID - ARM_BASE  # -> 0x0FB1
        assert 0 <= ARM_NEW_IMM <= 0xFF, "donor cid outside the repointable window"

        ARM_BL = 0x0225E6E6
        ARM_BL_OLD = 0x0225F7EC             # the dead leaf
        ARM_BL_NEW = 0x0225FA46             # the LIGHT+DARK cost leaf

        # ---------------------------------------------------------------------------
        # PART B -- the required-count branch
        # ---------------------------------------------------------------------------
        COUNT_BRANCH = 0x0225CF5E
        COUNT_RET0 = 0x0225D09C             # `movs r0,#0 ; bx lr`
        COUNT_RET1 = 0x0225D06A             # `movs r0,#1 ; bx lr`

        # ---------------------------------------------------------------------------
        # PART C -- the criteria registry (a.k.a. boggart_knight's POP_BASE)
        # ---------------------------------------------------------------------------
        CRIT_BASE = 0x022713C4
        CRIT_COUNT = 0x56C                  # 1388 -- literal at CRIT_COUNT_LIT; must NOT change
        CRIT_STRIDE = 12
        CRIT_COUNT_LIT = 0x02243DF8
        CRIT_FMT = "<HHII"
        CRIT_PROBE = 0x02243FE0                 # (side, cid, param) -> candidate count
        CRIT_HANDLER = 0x0223CA11           # the banish-cost enumerator
        CRIT_AUX = 0xFFFF
        CRIT_WORD_LIGHT = 0x01000002
        CRIT_WORD_DARK = 0x02000002
        CRIT_DROP_PHANTOM = 0x0E79          # a phantom owning exactly 2 rows; both are dropped

        CRIT_ROWS = ((DONOR_CID, CRIT_AUX, CRIT_HANDLER, CRIT_WORD_LIGHT),
                     (DONOR_CID, CRIT_AUX, CRIT_HANDLER, CRIT_WORD_DARK))

        # The 2-row disambiguation register.
        LISTA_BASE = 0x0227134C
        LISTA_COUNT = 0x3B                  # 59, hard-coded
        LISTA_DROP_PHANTOM = 0x0E6B

        # ---------------------------------------------------------------------------
        # PARTS D/E/F -- THE COST PAYMENT (found by the failed in-game test)
        #
        # IN-GAME TEST 1 FAILED: the card summoned itself WITHOUT banishing anything.
        # PARTS A/B/C only make the summon LEGAL; they say nothing about PAYING for it.
        # The payment is driven by TWO MORE per-cid dispatches, in a state machine on
        # [rec+0x24] where `rec` = the summon record 0x02298A28 (and [rec+0x28] is the
        # PASS INDEX -- the very value the legality leaf mirrors into the criteria
        # `param`). Neither dispatch knows our donor, so it fell to their default arms:
        #
        #   dispatch 1, root 0x02262962 -- picks r5 = HOW MANY CARDS TO SELECT this pass
        #       family arm 0x02262A5A : `movs r5,#2` (or 1 when [rec+0x28] == 0)
        #       our donor  0x02262AAE : generic default, no selection set up
        #
        #   dispatch 2, root 0x02262C24 -- THE TWO-PASS DRIVER
        #       family arm 0x02262C8C : [rec+0x28] += 1 ; if the OLD index was 0 then
        #                               [rec+0x24] = 4, i.e. GO ROUND AGAIN. This is the
        #                               only thing that makes the DARK pass happen.
        #       our donor  0x02262CA4 : finish immediately -- one pass, nothing banished.
        #
        # Both are hooked at their DISPATCH ROOT with a 4-byte BL into the ov3 cave.
        #
        # *** DO NOT hook the shared arm 0x02262CA4 instead: 0x02262C8C's completion path
        #     branches THERE, so a cid test at 0x02262CA4 would send the donor back to
        #     0x02262C8C forever. An earlier draft of this patch had exactly that bug. ***
        #
        # Only r2 is clobbered by the stubs. In both dispatches r2 is a scratch compare
        # register (loaded from the pool at 0x0226296C / 0x02262C26), never an argument,
        # so it is dead at every arm -- EXCEPT on dispatch 2's `bgt` path, where
        # 0x02262C5E does `adds r1,r2,#0` and needs r2 == 0x1BC8. Stub B therefore
        # restores r2 and returns via `push {r2}` / `pop {pc}`, which preserves both the
        # replayed compare's flags and r2. (`pop {pc}` is deliberate here -- see
        # thumb.pop_into_lr: Thumb-1 POP can load PC but never LR.)
        # ---------------------------------------------------------------------------
        # *** THE PAYMENT SIDE IS SHARED, AND IT MOVED. ***
        # Each payment dispatch has exactly ONE 4-byte BL hook, so a stub that hardcodes a
        # single donor cid can only ever serve one card. Darkflare Dragon has the SAME
        # printed summon procedure and needs the same two dispatches, so the stubs, the
        # ov3 dead run that hosts them, and the donor REGISTER now live in
        # handss_banish_cost.py; this module just calls it. The stub bytes therefore now
        # cover 0x0FB1 AND 0x1646, and the D-arm invariant is stated as the thing that
        # actually matters ("no arm branches INTO the cave") rather than the stricter
        # "the arm points at the reject leaf" -- Darkflare ROUTES one of those arms at a
        # real leaf, which keeps the cave just as unreachable.
        # Nothing about Lightpulsar's own path through the stubs changed.
        CAVE = banish.CAVE
        CAVE_LEN = banish.CAVE_LEN
        DEAD_ARMS = banish.DEAD_ARMS
        REJECT_LEAF = banish.REJECT_LEAF
        PAY1_HOOK = banish.PAY1_HOOK
        PAY2_HOOK = banish.PAY2_HOOK
        PAY2_FAMILY = banish.PAY2_FAMILY

        assert DONOR_CID in banish.DONOR_CIDS, (
            f"donor 0x{DONOR_CID:04X} is not in handss_banish_cost.DONOR_CIDS -- the shared "
            f"payment stubs would never route it and the card would summon FOR FREE")


        # ---------------------------------------------------------------------------
        # PART L -- THE SELECTION PARAM  (found by the DIAG in-game test)
        #
        # With the condition forced true the effect DID activate from the GY -- proving
        # PART K and the whole enumeration chain -- but only ONE card in the hand could be
        # picked. That symptom decodes exactly:
        #
        #   cost 0x021EC57D (Dark Simorgh's) is a 4-state machine on [0x0229AAFC+0x7C]:
        #     state 0  desc[+0x12] = 0            <- THE PASS INDEX lives in the descriptor
        #     state 1  0x0224B9F0(side, cid, r2 = 0, callback 0x022065F9)
        #              *** `movs r2,#0` @0x021EC5B6 is a HARDCODED IMMEDIATE, both passes ***
        #     state 2  take the pick, desc[+0x12]++, loop to state 1 while < 2
        #     state 3  send both picks
        #
        #   0x0224B9F0 is pure setup: [0x0229DD94+0x50] = param, [0x0229DE14+0x0C] = callback.
        #   The per-candidate filter is the CALLBACK 0x022065F9:
        #     desc = [0x0229A9FC+0x50]
        #     reject unless the candidate's controller matches desc[+2]^desc[+6]
        #     *** reject unless the candidate's ZONE == 0x0B -- THE HAND, hardcoded here ***
        #     0x02243FE0(side, desc[+0], param)   <- the criteria probe; param picks the ROW
        #
        # ⚠️ SO THE ZONE IS ENFORCED BY THE CALLBACK, NOT BY THE ROW'S HANDLER. That
        # corrects dispatch.criteria_zone_is_the_handler for this path, and it means
        # clause 2 needs NO hand-zone rows at all: clause 1's existing rows 0 (LIGHT) and
        # 1 (DARK) already carry the right attributes, and the callback supplies "from the
        # hand". The PART H rows at rel 2/3 are unreachable (see below) and now redundant.
        #
        #   And the row index comes from 0x02243B9C(cid, param), whose disambiguation for a
        #   cid in MEMBERSHIP LIST A is, read at 0x02243BEC..0x02243C00:
        #         if cid in list A:  r4 = (param == 0) ? 0 : 1      -- a pure 0/1 FLAG
        #   Our donor is in list A (clause 1 needs it), so param 0 -> row 0 = LIGHT and any
        #   non-zero param -> row 1 = DARK. Clause 1 passes 0 then 1 as bare immediates and
        #   therefore works. The cost passes 0 BOTH times, so it asked for LIGHT twice --
        #   and the test hand held exactly one LIGHT monster (our own second copy of the
        #   donor), which is the single selectable card the player saw.
        #
        # THE FIX IS ONE VALUE: param must be the PASS INDEX desc[+0x12], not 0.
        # 0x021EC57D is Dark Simorgh's shared cost and cannot be edited in place, so
        # instead we repoint the CALLBACK POINTER it loads and override param there. The
        # trampoline is CID-SCOPED, so Dark Simorgh keeps its original param exactly.
        #
        # ⚠️ ov3 dead code, NEVER the ov5 cave: 0x021EC57D is shared engine code that also
        # runs for Dark Simorgh in a PUZZLE, where ov41 evicts ov5 and a jump into the cave
        # would execute overlay-41 data (mem.ov5_ov41_share_base).
        #
        # ⚠️ The literal slot 0x021EC644 has EXACTLY ONE loader (`ldr r3,[pc,#0x8c]`
        # @0x021EC5B4) -- verified by resolving every PC-relative LDR in ov3. The callback
        # address 0x022065F9 appears in 27 other literal pools; none of them is touched.
        # ---------------------------------------------------------------------------
        C2_CB_NATIVE = 0x022065F9           # the native per-zone selection callback
        C2_ARM_TARGET = 0x0224B9F0          # arm a selection: (side, cid, param, callback)
        C2_STATE = 0x0229AAFC               # the phase machine's state lives at +0x7C
        C2_PROMPT = 0x0219A818              # (side, msg) -- the "select a card" prompt
        C2_PROMPT_MSG = 0x015D              # the message id Simorgh's cost uses
        C2_TAKE_PICK = 0x0224BBB0           # () -> nonzero once the player has picked
        C2_SEL_INDEX = 0x0229DE14           # [+0] = the index the player picked
        C2_PLAYER = 0x0229AC94              # player struct base, stride 0x0B3C
        C2_PLAYER_STRIDE = 0x0B3C
        C2_HAND_OFF = 0x124                 # player + 0x124 = the HAND array (savestate-proven)
        C2_PRE_MOVE = 0x021D28A4            # Simorgh's state-3 preamble
        C2_REF_TO_WORD = 0x021A25A0         # (side, ref) -> &cardword
        C2_SEND_TO_GY = 0x021C6E74          # hand 0x0B -> GY 0x0E   (Simorgh uses 0x021C6E98,
                                            #                          hand -> BANISHED 0x0F)
        C2_POST_MOVE = 0x021D2964           # Simorgh's state-3 tail
        C2_COST_RESERVE = 0x180             # 236 B shipped, more with instrumentation
        C2_ROW_LOOKUP = 0x02243B9C          # (cid, param) -> criteria row index


        def _arm_block(b: EffectBuilder) -> None:
            """State 1's arming, which differs between the two designs.

            Exactly what Dark Simorgh's cost does -- arm with the card's
            REAL cid and a constant param 0, and let the hooked disambiguation
            (criteria_row_hook.ARM_LP) turn that into rows 2/3 from desc[+0x12]. No proxy, and
            crucially NO desc[+0] swap, because the hook keys on the real cid.

            Default: arm with the PROXY cid and the real pass index, and swap desc[+0]
            to the proxy so the enumerator (which reads desc[+0], not the armed global)
            resolves the proxy's rows.
            """
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.insn("MOV", "R2, #0x0")


        def _probe_block(b: EffectBuilder) -> None:
            """Instrumentation prelude for the cost's state 1 (empty unless instrumenting).

            Asks 0x02243B9C the one question the in-game evidence and the static reading
            disagree about -- WHICH criteria row does the engine resolve for the armed cid
            -- and parks the answers in CAVE_LP_DIAG for a savestate to read.

            r4 (descriptor), r5 (state ptr) and r6 are AAPCS callee-saved, so they survive
            the calls; r0-r3 are rebuilt by the arming code that follows.
            """
            if not DIAG_C2_INSTRUMENT:
                return
            S = ov5_cave.CAVE_LP_DIAG
            L = C2_ROW_LOOKUP | 1
            b.ldr_const(6, S)
            b.ldr_const(0, 0x4C504431)
            b.insn("STR", "R0, [R6, #0x0]")
            for slot, (cid, param) in enumerate(((PROXY_CID, 0), (PROXY_CID, 1),
                                                 (DONOR_CID, 0), (DONOR_CID, 1)), start=1):
                b.ldr_const(0, cid)
                b.insn("MOV", f"R1, #0x{param:X}")
                b.ldr_const(3, L)
                b.insn("BLX", "R3")
                b.ldr_const(6, S)
                b.insn("STR", f"R0, [R6, #0x{slot * 4:X}]")
            # the live pass index, and the row the proxy's param-0 lookup landed on
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("STR", "R0, [R6, #0x14]")
            b.insn("LDR", "R0, [R6, #0x4]")
            b.ldr_const(1, 0x1000)
            b.insn("CMP", "R0, R1")
            b.insn("BGE", "noRow")
            b.insn("CMP", "R0, #0x0")
            b.insn("BLT", "noRow")
            b.insn("LSL", "R1, R0, #0x1")
            b.insn("ADD", "R1, R1, R0")
            b.insn("LSL", "R1, R1, #0x2")
            b.ldr_const(0, CRIT_BASE)
            b.insn("ADD", "R1, R0, R1")
            b.insn("LDR", "R0, [R1, #0x4]")
            b.insn("STR", "R0, [R6, #0x18]")
            b.insn("LDR", "R0, [R1, #0x8]")
            b.insn("STR", "R0, [R6, #0x1C]")
            b.label("noRow")


        # PART T's stub moved to timing_class_hook.py  (ARM_LP), because the
        # classifier site 0x0224AF96 is a SINGLE 4-byte BL and Jet Synchron needed a second
        # arm -- the same lift criteria_row_hook.py already went through for the row hook.
        # The arm body is byte-identical; only its host changed. See that module's docstring
        # for the measurement (in-game) that made this hook load-bearing.


        def _stub_res_disp(base: int) -> bytes:
            """The cls2 record's +04 RESOLVER slot, split between clauses 2 and 3.

            r0 = the descriptor, r1 = the invoker's arg (0x0224AEFC does
            `adds r0,r5,#0 ; adds r1,r4,#0 ; blx r2`), and r2/r3 are free scratch. Both
            targets are function ENTRIES, so a register-preserving `bx` is legal -- the
            2026-08-14 freeze came from jumping into a mid-function arm, not from a tail
            jump as such (dispatch.midfunction_tail_needs_prologue_frame).
            """
            b = EffectBuilder()
            b.insn("LDRB", "R2, [R0, #0x3]")
            b.insn("CMP", f"R2, #0x{C3_ZONE_GY:X}")
            b.insn("BNE", "clause2")
            b.insn("LDRB", "R2, [R0, #0x4]")
            b.insn("CMP", f"R2, #0x{C3_EVENT_MIN - 1:X}")
            b.insn("BLE", "clause2")
            b.ldr_const(3, C3_RESOLVER)
            b.insn("BX", "R3")
            b.label("clause2")
            b.ldr_const(3, C2_RESOLVER)
            b.insn("BX", "R3")
            return b.assemble(base, pad="nop")


        def _stub_tgt_disp(base: int) -> bytes:
            """The cls2 record's +14 TARGET-DECLARATION slot, split the same way.

            Clause 3 gets the native off-field picker; clause 2 gets `movs r0,#1`, which
            is EXACTLY what the engine does for a null slot -- the slot5 wrapper
            0x0224AE84 falls to `movs r0,#1 ; pop` when [rec+0x14] == 0. So clause 2's
            behaviour is unchanged from when this slot was 0.
            """
            b = EffectBuilder()
            b.insn("LDRB", "R2, [R0, #0x3]")
            b.insn("CMP", f"R2, #0x{C3_ZONE_GY:X}")
            b.insn("BNE", "clause2")
            b.insn("LDRB", "R2, [R0, #0x4]")
            b.insn("CMP", f"R2, #0x{C3_EVENT_MIN - 1:X}")
            b.insn("BLE", "clause2")
            b.ldr_const(3, C3_PICKER)
            b.insn("BX", "R3")
            b.label("clause2")
            b.insn("MOV", "R0, #0x1")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def _stub_c2_cost(base: int) -> bytes:
            """Clause 2's cost: our own clone of Dark Simorgh's selection state machine.

            Two deliberate differences from 0x021EC57D, both forced by evidence:

              0. **the ACTING DESCRIPTOR's cid is swapped to the proxy for the duration of
                 the selection** (`strh` at state 1, restored at state 3 and on cancel).
                 MEASURED from rom_lightpulsar_diag.ml3: the enumerator keys off
                 `desc[+0]`, NOT the armed global `[0x0229DD94+0x60]`. The probe showed the
                 arming was perfect -- `0x02243B9C(0x1303, 0)` -> row 94, handler
                 0x0223CB19 (HAND-select), word 0x01000002 (LIGHT) -- while the acting
                 descriptor at 0x0229A7FC still read cid 0x0FB1, so the engine enumerated
                 the DONOR's row 0: 0x0223CA11, a GY-select row, against a HAND selection.
                 Candidate count [0x0229944C+6] was 1, matching the single selectable card.
              1. **the selection is armed with the PROXY cid and the real pass index**, so
                 the engine's own criteria row filters each pass: param 0 -> proxy row 0
                 (LIGHT from hand), param 1 -> proxy row 1 (DARK). MEASURED:
                 a fresh pass 0 with one LIGHT in hand gives [0x0229944C+6] == 1, and
                 pass 1 with one DARK gives 1 -- the row DOES filter by attribute.
                 ⚠️ The picker DRAWS the whole hand, so a non-candidate looks clickable and
                 silently does nothing; that is the engine, not us. Our own per-pick check
                 below therefore MATCHES the row (LIGHT then DARK) instead of trying to be
                 order-free -- an earlier order-free version let a DARK through on pass 0
                 and left pass 1 with only the already-taken card.
                 Simorgh's cost does `movs r2,#0` @0x021EC5B6 on BOTH passes and relies on
                 its own 4-row criteria block being addressable at rel 2/3. Our donor's cid
                 resolves to row 0 (or 0/1 in membership list A) and can NEVER reach rows
                 2/3 -- so it arms with 0x1303, whose rows 0/1 ARE the hand-select
                 LIGHT/DARK pair, and with desc[+0x12], the genuine pass index.
              2. **state 3 SENDS to the Graveyard instead of banishing** -- 0x021C6E74
                 (source zone 0x0B, dest 0x0E) rather than 0x021C6E98 (dest 0x0F). The two
                 wrappers are otherwise identical thin calls into the relocation core
                 0x021C6B00 and take the same (side, &cardword) arguments.

            Everything else -- the phase encoding, the prompt, the pick-to-ref maths and
            the two-pass loop -- is Simorgh's, copied instruction for instruction, because
            that half demonstrably works in-game.

            r0 = the descriptor. Returns 1 only from the final state, 0 otherwise.

            *** CLAUSE 3 (2026-08-17) shares this slot. *** It has no cost, so its arm is
            a tail jump to 0x021E51E5 -- the native "You can" slot4 tag that Colossal
            Fighter and Botanical Girl carry, and the thing that actually makes an
            optional trigger ASK (event.optional_trigger_is_record_shape: optionality is
            a property of the +0C/+10 pair, never of the resolver). The test runs before
            the prologue so r0/r1 reach it untouched; r2/r3 are free scratch.
            """
            b = EffectBuilder()
            b.insn("LDRB", "R2, [R0, #0x3]")
            b.insn("CMP", f"R2, #0x{C3_ZONE_GY:X}")
            b.insn("BNE", "c2cost")
            b.insn("LDRB", "R2, [R0, #0x4]")
            b.insn("CMP", f"R2, #0x{C3_EVENT_MIN - 1:X}")
            b.insn("BLE", "c2cost")
            b.ldr_const(3, C3_COST_TAG)
            b.insn("BX", "R3")
            b.label("c2cost")
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(5, C2_STATE)
            b.insn("LDR", "R0, [R5, #0x7C]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "st0")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "st1")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "st2")
            b.insn("CMP", "R0, #0x3")
            b.insn("BEQ", "st3")
            b.insn("B", "ret0")
            b.label("st0")
            b.insn("MOV", "R0, #0x0")
            b.insn("STRH", "R0, [R4, #0x12]")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(C2_PROMPT, R0, C2_PROMPT_MSG, via=R6)
            b.insn("B", "bump")
            b.label("st1")
            _probe_block(b)
            _arm_block(b)
            b.call_addr(C2_ARM_TARGET, R0, R1, R2, C2_CB_NATIVE, via=R6)
            b.insn("B", "bump")
            b.label("st2")
            b.call_addr(C2_TAKE_PICK, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "reset")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R0, R1")
            b.ldr_const(1, C2_PLAYER + C2_HAND_OFF)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "side0")
            b.ldr_const(0, C2_PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("side0")
            b.ldr_const(0, C2_SEL_INDEX)
            b.insn("LDR", "R0, [R0, #0x0]")
            b.insn("LSL", "R0, R0, #0x2")
            b.insn("LDR", "R0, [R1, R0]")
            b.insn("ADD", "R6, R0, #0x0")
            b.insn("LSL", "R2, R0, #0x11")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSR", "R2, R2, #0x1F")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R2, R2, R0")
            b.insn("PUSH", "{R2}")
            b.ldr_const(0, 0x3fff)
            b.insn("AND", "R0, R6")
            b.call_addr(ATTR_ACCESSOR, via=R1)
            b.insn("LDRH", "R1, [R4, #0x12]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BNE", "wantDark")
            b.insn("CMP", f"R0, #0x{ATTR_LIGHT:X}")
            b.insn("BEQ", "attrOk")
            b.insn("B", "attrBad")
            b.label("wantDark")
            b.insn("CMP", f"R0, #0x{ATTR_DARK:X}")
            b.insn("BEQ", "attrOk")
            b.label("attrBad")
            b.insn("POP", "{R2}")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [R5, #0x7C]")
            b.insn("B", "ret0")
            b.label("attrOk")
            b.insn("POP", "{R2}")
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "bank")
            b.insn("LDRH", "R1, [R4, #0x14]")
            b.insn("CMP", "R1, R2")
            b.insn("BNE", "bank")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [R5, #0x7C]")
            b.insn("B", "ret0")
            b.label("bank")
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("ADD", "R0, R4, R0")
            b.insn("STRH", "R2, [R0, #0x14]")
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("ADD", "R0, R0, #0x1")
            b.insn("STRH", "R0, [R4, #0x12]")
            b.insn("CMP", "R0, #0x2")
            b.insn("BGE", "bump")
            b.insn("MOV", "R0, #0x1")
            b.insn("STR", "R0, [R5, #0x7C]")
            b.insn("B", "ret0")
            b.label("st3")
            b.call_addr(C2_PRE_MOVE, via=R6)
            b.insn("MOV", "R6, #0x0")
            b.label("loop")
            b.insn("LSL", "R1, R6, #0x1")
            b.insn("ADD", "R1, R4, R1")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R1, #0x14]")
            b.call_addr(C2_REF_TO_WORD, via=R3)
            b.insn("ADD", "R1, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(C2_SEND_TO_GY, via=R3)
            b.insn("ADD", "R6, R6, #0x1")
            b.insn("CMP", "R6, #0x2")
            b.insn("BLT", "loop")
            b.call_addr(C2_POST_MOVE, via=R6)
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("bump")
            b.insn("LDR", "R0, [R5, #0x7C]")
            b.insn("ADD", "R0, R0, #0x1")
            b.insn("STR", "R0, [R5, #0x7C]")
            b.insn("B", "ret0")
            b.label("reset")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R5, #0x7C]")
            b.label("ret0")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        # (_stub_pay1 / _stub_pay2 moved to handss_banish_cost.py -- they are shared with
        #  Darkflare Dragon and now take the whole donor register, not one cid.)


        # ---------------------------------------------------------------------------
        # PART G -- THE SUMMON-PROCEDURE REGISTRY  (found by savestate, in-game test 2)
        #
        # IN-GAME TEST 2 still summoned for free -- but it now correctly offered the
        # option ONLY when a LIGHT and a DARK were in the GY, so PARTS A/B/C were right
        # and the failure had moved. The savestates settled it:
        #   * the patched ov3 IS resident (stubs and hooks byte-identical in RAM);
        #   * the summon record 0x02298A28 had +0x0E == 0x0FB1, so the donor's summon
        #     really was running;
        #   * but +0x28 (the pass index) never left 0 and +0x24 ended at 0x17, i.e. the
        #     payment state machine 0x0226292C (states 0..4) NEVER RAN.
        #
        # The reason: the hand-SS tree only builds a BITMASK of available options --
        # 0x0225F216 is literally `movs r0,#4 ; orrs r5,r0`, i.e. "bit 2 = can be Special
        # Summoned from the hand". It does not select a cost. WHICH COST TO PAY comes
        # from a separate per-cid REGISTRY:
        #
        #   0x02264DAE  ldr  r1, =0x0228F158   ; {u32 cid, u32 handler}, stride 8, SORTED
        #   0x02264DB0  movs r2, #0x85         ; 133 rows -- a hard-coded imm8...
        #   0x02264DB2  movs r3, #8            ; ...duplicated at 0x022651C2
        #   0x02264DB4  bl   0x02022E44        ; generic binary search on the cid
        #   0x02264DB8  cmp  r0, #0
        #   0x02264DBA  beq  0x02264DC2        ; NOT FOUND -> generic summon, NO COST
        #   0x02264DBC  ldr  r0, [r0, #4]
        #   0x02264DBE  blx  r0                ; else call the procedure handler
        #
        # The whole Chaos family maps to handler 0x0226292D -- the very state machine
        # PARTS E/F patch. Our donor had NO ROW, so the search missed, the engine took
        # the not-found branch, and the card summoned itself for nothing. PARTS E/F were
        # correct but unreachable.
        #
        # 0x02261F8D is the registry's "no special procedure" handler (the second searcher
        # at 0x022651D4 explicitly tests for it), which is what all the phantom rows use.
        # ---------------------------------------------------------------------------
        PROC_BASE = 0x0228F158
        PROC_COUNT = 0x85                   # 133; imm8 at BOTH searchers -- must NOT change
        PROC_STRIDE = 8
        PROC_COUNT_LITS = (0x02264DB0, 0x022651C2)   # `movs r2,#0x85` == 0x2285
        PROC_HANDLER = 0x0226292D           # the banish-cost payment state machine (Thumb)
        PROC_DROP_PHANTOM = 0x0ECA          # phantom row sitting immediately before our slot

        # ---------------------------------------------------------------------------
        # PARTS H/I -- CLAUSE 2: "You can Special Summon this card (from your GY) by
        # sending 1 LIGHT and 1 DARK monster from your hand to the GY."
        #
        # TEMPLATE: Dark Simorgh 0x1E5A, a structural twin of this whole card. It owns TWO
        # cls2 records (one per summon direction) and a FOUR-row criteria block laid out
        # exactly as we need -- GY-pair at rel 0/1, HAND-pair at rel 2/3:
        #
        #   cls2[374]  +04 0x02206ABD  +0C 0x021FEBA9  +10 0x021EB7AD   SS from HAND, pay from GY
        #   cls2[375]  +04 0x0220731D  +0C 0x021FEBA9  +10 0x021EC57D   SS from GY, pay from HAND  <- clause 2
        #
        #   row 741  fn 0x0223CA11  word 0x02000002   DARK from the GRAVEYARD
        #   row 742  fn 0x0223CA11  word 0x06000002   WIND from the GRAVEYARD
        #   row 743  fn 0x0223CB19  word 0x02000002   DARK from the HAND
        #   row 744  fn 0x0223CB19  word 0x06000002   WIND from the HAND
        #
        # *** THE ZONE IS THE HANDLER, NOT THE WORD (dispatch.criteria_zone_is_the_handler).
        #     Dark Simorgh pays the same two attributes from either zone and its two row
        #     PAIRS carry IDENTICAL words, differing only in handler -- one cid, one text,
        #     everything else controlled for. 0x0223CA11 = select from GY, 0x0223CB19 =
        #     select from HAND. So clause 2's rows are clause 1's words UNCHANGED with the
        #     handler swapped. (An earlier theory that the word's low half encoded the zone
        #     was WRONG -- only 71 of the 148 rows carrying low half 0x0802 involve the hand
        #     at all; Time Wizard and Cyber-Stein are counter-examples.) ***
        #
        # ⚠️ ROW ORDER: clause 2's rows MUST follow clause 1's at rel 2/3. Clause 1 is
        # SHIPPED AND IN-GAME CONFIRMED and its leaf 0x0225FA46 passes param 0/1 as bare
        # immediates, so renumbering rows 0/1 would break a working clause.
        #
        # ⚠️ UNPROVEN, and the thing the in-game test must settle: Dark Simorgh's cost
        # 0x021EC57D drives its selection through 0x0224B9F0(side, cid, param, callback)
        # with a per-candidate CALLBACK in r3 (0x022065F9), not obviously through the
        # criteria rows. If the filter turns out to come from that callback rather than our
        # rows, clause 2 will summon but offer the WRONG candidates (any monster instead of
        # LIGHT then DARK) -- a visible, testable outcome, and the next step would be a
        # bespoke pair of attribute predicates. Shipping this to find out is deliberate:
        # the rows and record are well-founded and cannot break clause 1.
        # ---------------------------------------------------------------------------
        # ---------------------------------------------------------------------------
        # PART H (REWRITTEN) -- THE PROXY CID.
        #
        # The first design gave the DONOR two extra rows at relative indices 2/3. Measured
        # in-game and then traced: *** cid 0x0FB1 CAN NEVER ADDRESS ROWS 2 OR 3. ***
        # 0x02243B9C's disambiguation gives it, at best, a 0/1 flag:
        #     in membership list A -> r4 = (param == 0) ? 0 : 1     @0x02243BFA
        #     in neither list      -> the BST 0x02243C1C walks 0x208A> 0x1895> 0x0E79<
        #                             -> 0x02243C56, 0x1686> -> 0x02243C60, != 0x1522
        #                             -> 0x02243EEC = `movs r4,#0`, i.e. row 0 ONLY
        # So a 4-row block is unreadable past row 1 and leaving list A would break clause
        # 1's DARK pass as well.
        #
        # THE WAY ROUND IT: probe under a DIFFERENT CID. The native filter itself does
        # exactly this for four cards (its BST at 0x02206612 redirects 0x183E / 0x1935 /
        # 0x201E / 0x219E to a cid fetched elsewhere), so it is an idiom the engine
        # already relies on.
        #
        # PHANTOM 0x1303 IS A PERFECT PROXY, and it costs nothing:
        #   * it is a phantom (no card_prop), so no real card can be affected;
        #   * it ALREADY owns exactly two criteria rows, at indices 94/95;
        #   * it is ALREADY in membership list A, so its param 1 really reaches its row 1.
        # Rewriting those two rows in place is therefore a pure 24-byte overwrite: no
        # insert, no count change, no sort to maintain, no membership-list edit -- and the
        # DONOR goes back to the two rows clause 1 needs, restoring the "list A => exactly
        # two rows" invariant the 4-row block had broken.
        # ---------------------------------------------------------------------------
        # ⚠️⚠️ HANDLER CORRECTED (in-game: nothing was selectable at all).
        # 0x0223CB19 is DARK SIMORGH's hand handler -- and Simorgh BANISHES from the hand.
        # The only card whose cost SENDS from the hand is Fabled Soulkius 0x202C, and its
        # row is {fn 0x0223CB65, word 0x0000002E}. The two handlers are NOT a symmetric
        # pair with 0x0223CA11: they call different enumerators with different argument
        # layouts -- 0x0223CA11 -> 0x0223C4E8 (word at [sp], 1<<16 at [sp+4]),
        # 0x0223CB19 -> 0x0223BFD4 (0 at [sp], word at [sp+4], 0x10 at [sp+8]) -- so
        # "same word, different handler = different zone" was never true at the code level.
        # I mapped the 3DS pair (0x004B1A90 / 0x004ABE08) onto them BY POSITION, which
        # reproduced Simorgh's BANISH semantics instead of a send.
        # So clause 2's rows are SOULKIUS's word with the attribute nibble filled in --
        # which is exactly what the recon derived before the Simorgh lead
        # displaced it (see "CLAUSE 2 ENCODING UNBLOCKED" in the findings).
        # ⚠️⚠️ EMPIRICAL. Three handlers were tried for the proxy's rows:
        #   0x0223CB65 (Fabled Soulkius, "send from hand")  -> picker opens, NOTHING selectable
        #   0x0223CB19 (Dark Simorgh,   "banish from hand") -> picker opens with the HAND's
        #                                                      MONSTERS selectable  <-- use this
        #   ...with word 0x0100002E (Soulkius' low half)    -> nothing selectable
        # The row's ONLY job now is to open the hand list: clause 2 enforces "1 LIGHT and
        # 1 DARK, and not the same card twice" itself, in the condition AND in the cost,
        # via the engine's attribute accessor 0x0202ABC8. So pick the handler that
        # empirically produces the right list rather than the one whose name matches the
        # printed verb -- the send-vs-banish distinction is carried by the COST's state 3
        # (0x021C6E74 hand->GY, not 0x021C6E98 hand->banished), not by this row.
        C2_HANDLER = 0x0223CB19             # opens the HAND's monsters for selection
        PROXY_CID = 0x1303                  # phantom: 2 rows @94/95, already in list A
        # ⚠️ LOW HALF CORRECTED: 0x0002, not Soulkius' 0x002E. Cross-checked
        # every row carrying handler 0x0223CB65 against its printed text -- 20 of 25 use
        # low half 0x0002, INCLUDING every attribute-filtered one, and Soulkius' 0x002E is
        # the outlier because its cost is "any 2 cards". The attribute nibble agrees with
        # the text on all five that set it: Abyss Soldier 0x03 WATER, Lady Ninja Yae 0x06
        # WIND, Dark Crusader / Darklord Zerato 0x02 DARK, Chaos Goddess 0x01 LIGHT.
        #
        # *** CHAOS GODDESS 0x2273 IS CLAUSE 2's FIRST PASS VERBATIM: ***
        #     row 1159  fn 0x0223CB65  word 0x01000002
        #     "send 1 LIGHT monster from your hand to the GY, then target 1 Level 5 or
        #      higher DARK monster in your GY; Special Summon it"
        # so this pair is an attested native encoding, not a construction.
        # ⚠️⚠️ THE WORD IS "ANY MONSTER IN HAND", NOT THE ATTRIBUTE-FILTERED ONE.
        # MEASURED: with a hand holding TWO LIGHT monsters -- Divine Dragon
        # Ragnarok 0x1859 (LIGHT, *Normal* Monster) and Mind Master 0x1E22 (LIGHT, *Tuner*)
        # -- an attribute-filtered row 0x01000002 reported candidates == 1, so only ONE of
        # the two was offered. The same over-filtering excluded a second copy of the card
        # itself (0x0FB1, LIGHT) from paying its own cost, which is legal by the rules.
        # The word's LOW HALF is an undecoded selection/sub-kind field (the KB has never
        # decoded it; 0x0002 is the commonest of ten values) and it discriminates between
        # Normal / Tuner / Effect monsters here.
        #
        # Since clause 2 enforces the attributes ITSELF -- the condition requires a LIGHT
        # and a DARK in hand, and the cost requires LIGHT on pass 0, DARK on pass 1, and
        # refuses a repeat, all via the engine's accessor 0x0202ABC8 -- the row's only job
        # is to OPEN the widest correct list: every monster in the hand. Attribute nibble 0
        # = no attribute filter. This shape is attested natively: Ape Magician 0x218B is
        # {fn 0x0223CB65, word 0x00000002} = "send 1 monster from your hand to the GY".
        # *** THE CRITERIA WORD IS NOW FULLY DECODED (deep static pass). ***
        # The matcher is 0x0223BA24(side, zone, &cardword, WORD):
        #   bits 31:27  RACE       vs 0x0202ABB8(cid)   (0x021B1EE8 when zone == 0x0E)
        #   bits 26:24  ATTRIBUTE  vs 0x0202ABC8(cid)   (0x021B1F7C when zone == 0x0E)
        #   bits 21:18  LEVEL      vs 0x0202ABD8(cid); bit 22 = ">=", bit 23 = "<=", else "=="
        #   *** THE LOW HALF IS A BITMASK OF PREDICATES, NOT AN ENUM ***
        #     bit  1 (0x0002)  the basic "is a real card" test, 0x02029E60   <- what we want
        #     bit 10 (0x0400)  0x021B2094 (hand) / 0x02022FF0 (else)
        #     bit 13 (0x2000)  ATK <= 0x5DC (1500)  -- the Shining Angel / Mystic Tomato family
        #     bit 14 (0x4000)  0x02023188 == 1      bit 15 (0x8000) 0x02023110 == 1
        #     bit 16 (0x10000) 0x021B1E68
        # So 0x01000002 == "any LIGHT monster, no other constraint" and 0x02000002 the DARK
        # equivalent -- exactly clause 2's cost. Chaos Goddess 0x2273 ships 0x01000002 for
        # "send 1 LIGHT monster from your hand to the GY".
        #
        # The only other gate a candidate must pass is 0x021B945C(side, cid, 0), reached
        # because our handler sets flag 0x10; with flags == 0 it is a two-cid blocklist
        # (0x12EA, 0x1D16) and otherwise falls through to `movs r0,#1`. Neither of those is
        # a card we care about.
        #
        # => NOTHING in the engine excludes a second copy of the donor, a Tuner, or a Normal
        # Monster. The attribute-filtered rows are correct AND give the intuitive UI, since
        # the engine then only accepts valid cards. Widening to 0x00000002 ("any monster")
        # was a workaround for a limitation that does not exist; it made every monster
        # clickable and pushed the filtering into our silent re-ask, which is worse UX.
        C2_WORD_LIGHT_HAND = 0x01000002     # any LIGHT monster in hand (== Chaos Goddess)
        C2_WORD_DARK_HAND = 0x02000002      # any DARK  monster in hand
        C2_ROWS = ((PROXY_CID, CRIT_AUX, C2_HANDLER, C2_WORD_LIGHT_HAND),
                   (PROXY_CID, CRIT_AUX, C2_HANDLER, C2_WORD_DARK_HAND))

        CLS2_BASE = 0x02275C04
        CLS2_COUNT = 0x2B9
        CLS2_STRIDE = 24
        CLS2_DROP_PHANTOM = 0x0E10          # phantom cls2 row dropped to stay count-neutral

        # ---------------------------------------------------------------------------
        # The PROXY needs a cls2 record of its own, or the cost deadlocks.
        #
        # MEASURED (rom_lightpulsar.ml2/3/4): with desc[+0] swapped to 0x1303
        # the enumeration is finally right, but the cost is never re-entered -- the
        # activation machine re-finds the handler through find_event_handler(desc), which
        # binary-searches cls2 by desc[+0], and 0x1303 owned no record. The savestates show
        # it exactly: desc[+0] = 0x1303 in ALL THREE states (so neither restore ever ran),
        # the state machine fell back to 0, desc[+0x14]/[+0x16] stayed 0, nothing was sent
        # and nothing was summoned.
        #
        # So the proxy gets a record whose +10 is the same cost, giving re-entry somewhere
        # to land while the descriptor carries the proxy cid. Its +0C is NULL on purpose:
        # the condition is only consulted when OFFERING an effect, which always happens
        # through the donor's own record, and pointing it at Simorgh's 0x021FEBA9 would
        # make that condition validate a GY slot holding cid 0x0FB1 against desc[+0] =
        # 0x1303. A null +0C is a legal, common shape (155 of 697 native cls2 records).
        # 0x1303 is a phantom with no card_prop, so it can never sit in a zone and can
        # never be independently offered.
        # ---------------------------------------------------------------------------
        PROXY_CLS2_DROP = 0x1435            # unclaimed phantom cls2 row, dropped for the proxy

        # ---------------------------------------------------------------------------
        # PART J -- the CONDITION, and why the verbatim clone failed in-game
        #
        # IN-GAME TEST (user savestate): with Lightpulsar in the GY and a LIGHT
        # + a DARK monster in hand the effect was **NOT activatable**, while Dark Simorgh in
        # the same GY with a DARK + a WIND in hand WAS. A perfect A/B, and the cause is in
        # the condition we cloned verbatim:
        #
        #   0x021FEBB6  movs r2,#2 ; lsls r2,r2,#0x1c   -> param 0x20000000  = DARK
        #   0x021FEBBC  bl 0x02243FE0                   -> "any DARK candidate?"
        #   0x021FEBCA  movs r2,#6 ; lsls r2,r2,#0x1c   -> param 0x60000000  = WIND
        #   0x021FEBD0  bl 0x02243FE0                   -> "any WIND candidate?"
        #
        # *** THE ATTRIBUTE IS PARAM'S TOP NIBBLE, baked in as an immediate. *** The clone
        # was therefore asking for 1 DARK and 1 WIND -- Dark Simorgh's cost, not ours -- so
        # with no WIND in hand it correctly refused. (This also shows the two HAND criteria
        # rows of PART H are not what supplies the attribute here; they are retained because
        # they are the correct zone-tagged rows for this cid and cost nothing, but the
        # filter on THIS path comes from param.)
        #
        # PART J is Dark Simorgh's condition with exactly those two immediates changed to
        # LIGHT(1) and DARK(2), tail-jumping back into its own epilogue at 0x021FEBDC so the
        # remaining checks (0x021F0384, 0x021BA440) stay shared rather than duplicated.
        #
        # ⚠️ AND WITHOUT SIMORGH'S `[desc+3] == 0xB` GATE. The first build kept it verbatim
        # and the effect was still un-activatable in-game even though the savestate showed
        # BOTH the ov5 stub and the cls2 record correctly resident in RAM (so the condition
        # was definitely being called and definitely returning 0). That gate is how Simorgh
        # tells its TWO records apart -- 0xB selects its from-GY half -- and our card owns
        # only ONE record, so its descriptor carries a different value and the gate rejected
        # us outright. A donor cloning a multi-record card's condition must drop any such
        # record-selector test.
        #
        # ⚠️ HOSTED IN OV5, so CLAUSE 2 IS NORMAL-DUEL-ONLY (user decision): the
        # ov3 dead run had only 46 B contiguous left and this needs ~0x38. Clauses 1 and 3
        # are pure ov3 and remain puzzle-capable, so this card's behaviour differs by duel
        # mode -- say so in the card text.
        #
        # ⚠️ STILL UNPROVEN: the COST 0x021EC57D selects through
        # 0x0224B9F0(side, cid, param=0, callback=0x022065F9) -- a per-candidate CALLBACK,
        # not an attribute immediate. If that callback is Simorgh-specific, the card will
        # become activatable (this part works) but may offer the WRONG cards to send. That
        # is the next thing the in-game test settles.
        # ---------------------------------------------------------------------------
        # ⚠️⚠️ CORRECTED -- WE WERE TAIL-JUMPING INTO THE WRONG HALF.
        # [desc+3] is the ZONE (event.register_prim_descriptor_layout), so Simorgh's
        # `cmp [desc+3],#0xB` at 0x021FEBB0 asks "is THIS COPY in the HAND?" and picks
        # between its two directions:
        #     zone 0x0B (hand) -> 0x021FEBB4.. probe attributes, tail 0x021FEBDC
        #                         = 0x021F0384 + 0x021BA440   <- cls2[374], SS FROM HAND
        #     otherwise (GY)   -> 0x021FEBFE.. = 0x021F04FC, 0x021BABE8, 0x0224401C
        #                                                    <- cls2[375], SS FROM GY
        # Clause 2's card sits in the GRAVEYARD, so the from-HAND tail was flatly wrong:
        # 0x021F0384 runs 0x021F0114(side) + 0x021B9EC0(side, cid), the hand-summonability
        # pair. The from-GY arm's first check 0x021F04FC resolves [desc+0xC] (the packed
        # ref) against **player + 0x55C** -- measured to be the GRAVEYARD array
        # (savestate rom_lightpulsar.ml3: 3 entries, count at player+0x14, holding Reload,
        # Upstart Goblin and our donor 0x0FB1) -- and validates it with 0x021A2618.
        # So we keep the LIGHT/DARK probes and hand off to the GY arm instead, restoring
        # r0 = desc / r1 = the original arg, which is the register state Simorgh's own
        # `bne 0x021FEBFE` arrives with. Frame-compatible: 0x021FEBFE returns through the
        # same `pop {r3,r4,r5,pc}` our prologue pushed.
        C2_COND_GY_ARM = 0x021FEBFE         # Simorgh's SS-from-GY arm (mid-function -- see the stub)
        C2_COND_NATIVE = 0x021FEBA9         # Simorgh's condition ENTRY (zone test + GY checks)
        ATTR_ACCESSOR = 0x0202ABC8          # (cid) -> monster/spell FLAG<<3 | ATTRIBUTE
                                            #   0x0202A084 resolves the 8-byte card_prop
                                            #   record; this reads [rec+4] bits 9:6.
                                            #   card_prop's ERA2 layout puts attribute at
                                            #   record bits 40:38 == [rec+4] bits 8:6, and
                                            #   record bit 41 (== [rec+4] bit 9) is the
                                            #   monster/spell-trap flag. So for a MONSTER
                                            #   this returns the attribute unchanged
                                            #   (1 LIGHT .. 7 DIVINE) and for a SPELL it
                                            #   returns >= 8, which fails both tests -- a
                                            #   free spell/trap rejection.
                                            # ⚠️ NOT 0x0202ABE8: that reads [rec+4] bits
                                            #   16:14 == record 48:46 = spell_trap_subtype,
                                            #   which is 0 for EVERY monster. Using it would
                                            #   have rejected every pick.
                                            # Verified against the ROM's own card_prop with
                                            #   game_constants.DEFAULT_CONSTANTS (ERA2):
                                            #   Mind Master LIGHT=1, Krebons DARK=2,
                                            #   Psychic Commander EARTH=5, Ragnarok LIGHT=1,
                                            #   REDMD DARK=2, Chaos Sorcerer DARK=2,
                                            #   Dragunity Arma Leyvaten WIND=6 -- 8/8.
        ATTR_LIGHT, ATTR_DARK = 1, 2
        C2_PROBE_RESET = 0x02243FA8         # (side, cid, param) -> count for THAT row alone
                                            #   (resets [0x0229944C+6] first; 0x02243FE0 does not)
        C2_COND_RESERVE = 0x120
        C2_HAND_ARRAY = C2_PLAYER + C2_HAND_OFF   # player + 0x124
        C2_HAND_COUNT = C2_PLAYER + 0x0C          # player + 0x0C


        # DIAGNOSTIC: when True, clause 2's condition returns 1 unconditionally. This does
        # NOT ship -- it exists to split the search space after three falsified hypotheses.
        # If the GY effect is OFFERED with this on, the record and its dispatch are correct
        # and the fault is inside the condition (which probe fails, and why). If it is STILL
        # not offered, the condition is irrelevant and something upstream never reaches the
        # record at all. Either answer halves the remaining work.
        DIAG_C2_ALWAYS_TRUE = False

        # DIAGNOSTIC: when True, clause 2's cost probes the criteria-row resolver for the
        # proxy and the donor and writes the answers to CAVE_LP_DIAG, where a savestate can
        # read them. It turns the one remaining unknown -- WHICH criteria row the engine
        # resolves for the armed cid -- into a number, instead of another hypothesis.
        # The in-game evidence that forced this: the savestate proves our cost armed the
        # picker with cid 0x1303 / param 0 / the native callback, which by the static
        # reading of 0x02243B9C should select the proxy's row 0 (LIGHT from hand) -- yet
        # only the DARK card in hand was selectable. Something between the arming and the
        # enumeration disagrees with that reading; this measures where.
        # ⚠️ MUST NOT SHIP.
        DIAG_C2_INSTRUMENT = False


        def _c3_diag_block(b: EffectBuilder) -> None:
            """PART Q: park the descriptor and the resolved row index in CAVE_LP_DIAG.

            Emitted at the top of the +0C stub, so it runs for BOTH clauses and captures
            the clause-3 trigger the first time it ever fires. Cheap and always on --
            the alternative was budgeting a second duel to answer the same questions.

            On entry r4 = the descriptor and {r1} is on the stack; r0-r3 and r5-r7 are
            all rebuilt by whichever arm runs next, so the block may use them freely.
            r6 is reloaded after the call rather than trusted to be callee-saved.
            """
            if not C3_DIAG:
                return
            S = ov5_cave.CAVE_LP_DIAG
            b.ldr_const(6, S)
            b.ldr_const(0, C3_DIAG_MAGIC)
            b.insn("STR", "R0, [R6, #0x0]")
            b.insn("LDRH", "R0, [R4, #0x0]")
            b.insn("STR", "R0, [R6, #0x4]")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x3]")
            b.insn("LSL", "R1, R1, #0x8")
            b.insn("ORR", "R0, R1")
            b.insn("LDRB", "R1, [R4, #0x4]")
            b.insn("LSL", "R1, R1, #0x10")
            b.insn("ORR", "R0, R1")
            b.insn("LDRB", "R1, [R4, #0x5]")
            b.insn("LSL", "R1, R1, #0x18")
            b.insn("ORR", "R0, R1")
            b.insn("STR", "R0, [R6, #0x8]")
            b.insn("LDRH", "R0, [R4, #0x12]")
            b.insn("STR", "R0, [R6, #0xC]")
            b.ldr_const(0, ACTING_DESC)
            b.insn("LDR", "R0, [R0, #0x50]")
            b.insn("STR", "R0, [R6, #0x10]")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("STR", "R0, [R6, #0x14]")
            b.call_addr(C2_ROW_LOOKUP, DONOR_CID, 0, via=R3)
            b.ldr_const(6, S)
            b.insn("STR", "R0, [R6, #0x18]")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("CMP", f"R0, #0x{C3_EVENT_MIN - 1:X}")
            b.insn("BLE", "noLatch")
            b.insn("LDR", "R1, [R6, #0x1C]")
            b.insn("CMP", "R1, #0x0")
            b.insn("BNE", "bumpN")
            b.insn("LDRB", "R1, [R4, #0x3]")
            b.insn("LSL", "R1, R1, #0x8")
            b.insn("ORR", "R0, R1")
            b.insn("MOV", "R1, #0x1")
            b.insn("LSL", "R1, R1, #0x10")
            b.insn("ORR", "R0, R1")
            b.insn("STR", "R0, [R6, #0x1C]")
            b.label("bumpN")
            b.insn("LDR", "R0, [R6, #0x20]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R6, #0x20]")
            b.label("noLatch")


        def _stub_c2_cond(base: int) -> bytes:
            """The cls2 record's +0C ACTIVATION CONDITION, split between clauses 2 and 3.

            Clause 3 (desc[+4] == 0x1E) defers to Colossal Fighter's own condition
            0x021F03B5 -- "may I Special Summon?" AND "does a legal target exist?",
            the latter through 0x02234E78 -> 0x02243FE0, i.e. our criteria row via the
            hooked disambiguation. It is called as a FUNCTION (r0 = desc, r1 = the arg),
            not jumped into: it is a real entry point, and this module has already been
            burned once by tail-jumping into a mid-function arm
            (dispatch.midfunction_tail_needs_prologue_frame).

            Clause 2 keeps the hand scan below: 1 LIGHT + 1 DARK candidate, else 0.
            """
            if DIAG_C2_ALWAYS_TRUE:
                b = EffectBuilder()
                b.insn("MOV", "R0, #0x1")
                b.insn("BX", "LR")
                return b.assemble(base, pad="nop")
            # ⚠️⚠️⚠️ DO NOT REINTRODUCE A BARE THUNK HERE. A build that made this stub
            # `ldr r3,=0x021FEBFF ; bx r3` FROZE THE GAME the moment Lightpulsar reached
            # the Graveyard (in-game, savestate rom_lightpulsar.ml2 confirms
            # the 8-byte thunk `004b 1847` was resident). Simorgh's from-GY arm is the
            # TAIL OF A FUNCTION, not a function: it reads the descriptor out of **r4**
            # and returns through `pop {r3,r4,r5,pc}` @0x021FEC3E. Jumping into it without
            # first executing Simorgh's own prologue (`push {r3,r4,r5,lr} ; adds r4,r0,#0
            # ; adds r5,r1,#0`) pops four words that were never pushed and returns to
            # garbage. Anything entering at 0x021FEBFE must reproduce that frame exactly.
            #
            # Which is why the shipped record now points +0C at the NATIVE condition
            # 0x021FEBA9 instead (C2_COND_NATIVE): it does its own prologue, tests the
            # zone itself, and routes a GY card into the very same arm. That also makes
            # clause 2 ov3-only -- so, like clause 1, it is now PUZZLE-SAFE, and the ov5
            # cave slot is used only by the DIAG build below.
            #
            # ⚠️⚠️ THE ATTRIBUTE PROBES ARE GONE. They were cloned from
            # Simorgh's FROM-HAND arm, which passes the attribute in param's top nibble --
            # an idiom that only works for a cid whose row resolver honours param. Our
            # donor is in MEMBERSHIP LIST A, where 0x02243B9C clamps the row to
            # `param == 0 ? 0 : 1` (read at 0x02243BEC..0x02243C00), so BOTH probes
            # resolved to row 1 (DARK) and the pair was a spurious double DARK test.
            #
            # Simorgh's from-GY arm already does the right check on its own and is
            # entirely CID-GENERIC: 0x021F04FC (the card really is in your GY -- it
            # indexes player+0x55C, the Graveyard array), 0x021BABE8(side) (you may
            # Special Summon), then 0x0224401C(desc) TWICE with desc[+0x12] = 0 then 1 --
            # the same pass index the cost uses. So the whole condition is that tail.
            #
            # ⚠️ THE NATIVE CONDITION IS NOT ENOUGH -- in-game the effect was
            # activatable with only ONE DARK in hand. 0x021FEBA9's GY arm calls
            # 0x0224401C twice, and that resolves rows through desc[+0], which is still
            # the DONOR at condition time (the proxy swap happens in the COST). So it was
            # checking the donor's rows 0/1 -- the GY-select pair -- i.e. asking about the
            # GRAVEYARD, not the hand.
            #
            # So gate it ourselves against the PROXY's HAND rows first, then defer to the
            # native condition for the zone/in-GY/can-SS checks. 0x02243FA8 is used rather
            # than 0x02243FE0 because it RESETS the shared counter [0x0229944C+6] before
            # enumerating, so each probe returns the count for that row alone.
            prog = EffectBuilder()
            prog.insn("PUSH", "{R4, R5, R6, R7, LR}")
            prog.insn("ADD", "R4, R0, #0x0")
            prog.insn("PUSH", "{R1}")
            _c3_diag_block(prog)
            prog.insn("LDRB", "R0, [R4, #0x3]")
            prog.insn("CMP", f"R0, #0x{C3_ZONE_GY:X}")
            prog.insn("BNE", "clause2")
            prog.insn("LDRB", "R0, [R4, #0x4]")
            prog.insn("CMP", f"R0, #0x{C3_EVENT_MIN - 1:X}")
            prog.insn("BLE", "clause2")
            prog.insn("POP", "{R1}")
            prog.call_addr(C3_CONDITION, R4, via=R3)
            prog.insn("POP", "{R4, R5, R6, R7, PC}")
            prog.label("clause2")
            prog.insn("LDRB", "R0, [R4, #0x2]")
            prog.insn("MOV", "R1, #0x1")
            prog.insn("AND", "R0, R1")
            prog.ldr_const(6, C2_HAND_ARRAY)
            prog.ldr_const(5, C2_HAND_COUNT)
            prog.insn("CMP", "R0, #0x0")
            prog.insn("BEQ", "side0")
            prog.ldr_const(0, C2_PLAYER_STRIDE)
            prog.insn("ADD", "R6, R6, R0")
            prog.insn("ADD", "R5, R5, R0")
            prog.label("side0")
            prog.insn("LDR", "R5, [R5, #0x0]")
            prog.insn("MOV", "R7, #0x0")
            prog.label("scan")
            prog.insn("LSL", "R0, R7, #0x18")
            prog.insn("LSR", "R0, R0, #0x18")
            prog.insn("CMP", "R0, R5")
            prog.insn("BGE", "scanned")
            prog.insn("LSL", "R1, R0, #0x2")
            prog.insn("LDR", "R0, [R6, R1]")
            prog.ldr_const(1, 0x3fff)
            prog.insn("AND", "R0, R1")
            prog.call_addr(ATTR_ACCESSOR, via=R1)
            prog.insn("CMP", f"R0, #0x{ATTR_LIGHT:X}")
            prog.insn("BNE", "chkDark")
            prog.insn("MOV", "R0, #0x1")
            prog.insn("LSL", "R0, R0, #0x8")
            prog.insn("ORR", "R7, R0")
            prog.insn("B", "nextI")
            prog.label("chkDark")
            prog.insn("CMP", f"R0, #0x{ATTR_DARK:X}")
            prog.insn("BNE", "nextI")
            prog.insn("MOV", "R0, #0x2")
            prog.insn("LSL", "R0, R0, #0x8")
            prog.insn("ORR", "R7, R0")
            prog.label("nextI")
            prog.insn("ADD", "R7, R7, #0x1")
            prog.insn("B", "scan")
            prog.label("scanned")
            prog.insn("LSR", "R0, R7, #0x8")
            prog.insn("CMP", "R0, #0x3")
            prog.insn("BNE", "no")
            prog.insn("POP", "{R1}")
            prog.call_addr(C2_COND_NATIVE, R4, via=R3)
            prog.insn("POP", "{R4, R5, R6, R7, PC}")
            prog.label("no")
            prog.insn("POP", "{R1}")
            prog.insn("MOV", "R0, #0x0")
            prog.insn("POP", "{R4, R5, R6, R7, PC}")
            return prog.assemble(base, pad="nop")


        # cls2 record: Dark Simorgh cls2[375] verbatim apart from the cid.
        # +0C is the NATIVE condition (ov3, puzzle-safe); only the DIAG build swaps in the
        # ov5 stub so the condition can be forced true.
        def _proxy_cls2_record() -> tuple:
            """The proxy's re-entry record: same resolver and cost, no condition."""
            return (PROXY_CID, 0x0220731D, 0x00000000, 0x00000000,
                    ov5_cave.CAVE_LP_C2COST | 1, 0x00000000)


        def _cls2_record() -> tuple:
            # ONE record, FOUR dispatching slots. Clauses 2 and 3 must share it -- a second
            # same-cid cls2 record is unreachable (find_event_handler only applies its +1
            # offset for cls1, and relocation events are always class 2), which is the
            # Warwolf E1/E2 shadow. Every slot branches on desc[+4], the event code:
            #
            #   +04 resolver   0x1E -> 0x02207191 (cls2 GY revive) else 0x0220731D
            #   +08            unused by both clauses
            #   +0C condition  0x1E -> 0x021F03B5 (Colossal Fighter) else the hand scan
            #   +10 cost       0x1E -> 0x021E51E5 ("You can" tag)   else the selection machine
            #   +14 target     0x1E -> 0x02235605 (off-field picker) else `movs r0,#1`
            #
            # +14's clause-2 arm returns 1 because that is exactly what the engine does for
            # a null slot (0x0224AE84), so clause 2 is bit-for-bit unchanged.
            return (DONOR_CID,
                    ov5_cave.CAVE_LP_RESDISP | 1,
                    0x00000000,
                    ov5_cave.CAVE_LP_C2COND2 | 1,
                    ov5_cave.CAVE_LP_C2COST | 1,
                    ov5_cave.CAVE_LP_TGTDISP | 1)

        # ---------------------------------------------------------------------------
        # PART K -- THE GY-ACTION REGISTRY  (why clause 2 was never offered at all)
        #
        # Clause 2 had criteria rows, a cls2 record and a condition stub, all confirmed
        # resident in RAM by savestate -- and the effect was STILL never offered from the
        # Graveyard. A GDB control showed Dark Simorgh's cls2 condition firing while ours
        # never fired even once. Traced offline, the gate is a table nobody had
        # found:
        #
        #   0x0228DDF8, 60 rows x 0x10 B, {u32 cid, u32 zone, u32 check_fn, u32 post_fn}
        #
        # It is UNSORTED and LINEAR-SCANNED -- four scanners, each bounded by a hardcoded
        # `cmp rX,#0x3C`: 0x0224C88E (by zone), 0x0224CD14 (by cid, then blx [row+0xC]),
        # 0x0224CBD8 and 0x0224CD42 (by post_fn). The offer path it drives:
        #
        #   registry row {cid, 0x0E, 0x0224C591, 0x0224C6C1}
        #     -> 0x0224C590(side, cid, ref)  builds a 0x24-B descriptor (zone 0x0E,
        #                                    class 2, event code from the queue 0x0229A37C)
        #     -> 0x021EC740 -> 0x021EDA14 (the COMMIT body)
        #     -> 0x0224AD94 -> find_event_handler 0x0224A118 -> record[+0x0C]
        #
        # 0x0224C590 and 0x0224C6C0 have ZERO BL callers in ov3 -- they are reachable only
        # as this registry's function pointers. No row => no descriptor => the condition is
        # never called. Every ignition-style GY summoner is in the table (Dark Simorgh
        # 0x1E5A, Plaguespreader 0x1EA9, Quillbolt 0x1E15, Soulkius 0x202C, Spore 0x225B,
        # Glow-Up Bulb 0x2387, Ronintoadin 0x2269); our donor was not.
        #
        # *** TREEBORN FROG IS NOT A VALID CONTROL. *** It owns cls2[199] and nothing else,
        # which is what produced the earlier (wrong) rule "a self-SS-from-GY card needs only
        # a cls2 record". Treeborn is a STANDBY-PHASE trigger wired through its own
        # structures (0x0228EB24, 0x0226D384) and is the one family member absent from this
        # registry. Profile Plaguespreader or Soulkius instead.
        #
        # *** And this is why the earlier "missing registry row" hypothesis was ruled out
        # in error: it searched 0x0228E000..0x0228F160, a window that starts INSIDE this
        # table and misses its first 32 rows -- exactly the rows holding Simorgh,
        # Plaguespreader, Quillbolt and Soulkius. ***
        #
        # THE FIX: the table is unsorted and its length is an immediate at every scanner,
        # so a count-neutral insert is just an in-place rewrite of one PHANTOM row's cid
        # word -- 4 bytes, no sort to maintain, no bound to bump. Three phantoms already
        # carry the right family and zone: 0x0EB2 (row 15), 0x0E3E (row 47), 0x0E64 (row
        # 48). We take 0x0E3E, which sits inside the contiguous 0x0224C591 block (its
        # neighbours are A/D Changer and Chain Dog); 0x0EB2 is embedded in the 0x0224C55D
        # block, so leave it for a card that wants that family.
        # ---------------------------------------------------------------------------
        GYREG_BASE = 0x0228DDF8
        GYREG_STRIDE = 0x10
        GYREG_COUNT = 0x3C                  # 60 rows; an imm8 at EVERY scanner
        GYREG_COUNT_SITES = (0x0224C99A, 0x0224CD30)   # `cmp rX,#0x3C` -- must NOT change
        GYREG_FMT = "<4I"
        GYREG_ZONE_GY = 0x0E
        GYREG_CHECK = 0x0224C591            # the GY-effect family (45 of the 60 rows)
        GYREG_POST = 0x0224C6C1
        GYREG_DROP_PHANTOM = 0x0E3E         # row 47 @0x0228E0E8; same family, same zone

        # ===========================================================================
        # CLAUSE 3 -- "When this card is sent from the field to the GY: You can target
        #              1 Level 5 or higher DARK Dragon monster in your GY; Special
        #              Summon that target."
        # ===========================================================================
        # Every piece below is a NATIVE structure copied from a shipping card. Nothing
        # is constructed, and the one value the earlier sessions had to derive by hand
        # (the criteria word) is now attested in a shipping Konami build.
        #
        # PART M  the TRIGGER      -- a leave-mask row, count-neutral
        # PART N  the TARGET FILTER-- one criteria row on the donor at rel 4
        # PART O  the ROW INDEX    -- a third arm on the SHARED row hook
        # PART P  the ACTION       -- the cls2 record's four slots, split by desc[+4]
        # PART Q  instrumentation  -- always on; writes to the unused CAVE_LP_DIAG
        #
        # ---------------------------------------------------------------------------
        # THE DISCRIMINATOR: desc[+4], THE EVENT CODE.
        #
        # Clause 2 and clause 3 must share ONE cls2 record. A second same-cid cls2
        # record is unreachable: find_event_handler applies its +1 offset only when
        # desc[+5] == 1 (cls1), and EVERY relocation event is class 2
        # (dispatch.find_event_handler_second_record + event.register_prim_descriptor_
        # layout). Giving the donor two records is the Warwolf E1/E2 shadow.
        #
        # The two descriptors share the cid AND the zone (0x0E), so the zone cannot
        # separate them -- only the event code can. MEASURED by parsing the
        # acting descriptor [0x0229A9FC+0x50] out of the existing savestates:
        #
        #   rom_eclipse_wyvern.ml2  cid 0x1859 zone 0x0E event 0x1E cls 2   sent-to-GY
        #   rom_all_patches.ml3     cid 0x1859 zone 0x0E event 0x1E cls 2   same
        #   rom_eclipse_wyvern.ml3  cid 0x1859 zone 0x0F event 0x20 cls 2   EW's banish
        #                                          trigger -- matches event.gy_to_banished_mover
        #   rom_lightpulsar.ml3/4/5 cid 0x1303 zone 0x0E event 0x00 cls 2   CLAUSE 2
        #
        # Independently, clause 2's descriptor can never carry a code above 6: it comes
        # off the GY-action registry path, whose off-field gate 0x021ECC28 requires
        # desc[+4] <= 6.
        #
        # ⚠️⚠️ CORRECTED AFTER IN-GAME TEST 1. The first build tested
        # `desc[+4] == 0x1E` and the trigger silently routed itself to CLAUSE 2 instead.
        # 0x1E is the code the RELOCATION APPLIER 0x021D1300 posts (which is how Eclipse
        # Wyvern's any-location trigger arrives). The LEAVE-FIELD dispatcher posts its own,
        # and picks it at 0x021C809C:
        #
        #     [sp+0x44] (destroyed BY BATTLE) != 0  ->  event 0x17
        #     otherwise                             ->  event 0x1D
        #     ... then `str r0,[sp,#0x1c]`, and every native arm ORs [sp+0x1C] << 0x19
        #         into the packed word (0x021C9396..0x021C93A2).
        #
        # CONFIRMED BY SAVESTATE: Reborn Tengu (Minefieldriller 0x2085), a SHIPPED,
        # in-game-working field-leave trigger on a records-free donor, appears in
        # rom_all_patches.ml4/ml5 with {cid 0x2085, zone 0x0E, event 0x1D, cls 2}.
        #
        # So the test is a RANGE, not a constant: clause 3 takes everything above clause
        # 2's proven ceiling, which covers the battle code 0x17, the non-battle code 0x1D
        # and the relocation code 0x1E without having to enumerate them.
        # ---------------------------------------------------------------------------
        C3_EVENT_MIN = 7                    # clause 3 iff desc[+4] > 6 AND desc[+3] == 0x0E
        C3_ZONE_GY = 0x0E                   # the descriptor's zone is the DESTINATION zone,
                                            #   so requiring 0x0E is what makes clause 3 fire
                                            #   only when the card is sent TO THE GRAVEYARD --
                                            #   not when it is bounced or banished off the field

        # ---------------------------------------------------------------------------
        # PART M -- THE TRIGGER. The leave dispatcher has THREE registration paths and
        # they are NOT interchangeable. Disassembled 0x021C80BC..0x021C8114:
        #
        #   0x021C80BC  [sp+0x44] && [sp+0x90] && [sp+0x144]      battle && DESTROYED && to-GY
        #                 && bsearch(list106 0x0226E990, 0x6A)  -> [sp+0x18] = 1
        #   0x021C80E0  [sp+0x2C] && [sp+0x144]                   left the FIELD && to-GY
        #                 && bsearch(list30  0x0226E904, 0x1E)  -> [sp+0x18] = 1
        #   0x021C80FE  if [sp+0x18] == 0 ONLY:
        #                 bsearch(mask table 0x0226EC1C, 0x98, stride 4)
        #
        # Membership settles the semantics outright:
        #   * list30  = "sent from the FIELD to the GY" -- Botanical Girl 0x1ED4, Sangan
        #     0x0FD6, Witch of the Black Forest, Goblin Zombie, Dupe Frog, Naturia Cliff,
        #     Naturia Eggplant, Gusto Gulldo, Gem-Knight Aquamarine, Junk Gardna, Masked
        #     Beast Des Gardius, Emissary of the Afterlife, Deepsea Macrotrema, E-Hero
        #     The Shining, PLUS the equip spells (Axe of Despair, Black Pendant, Horn of
        #     Light, Horn of the Unicorn, Malevolent Nuzzler, Magic Formula, Crystal
        #     Release, Cursed Armaments). All 30 members are worded exactly that way.
        #   * list106 = "destroyed by battle and sent to the GY" -- Colossal Fighter
        #     0x1E12, Lord Poison 0x156D, Sun Dragon Inti 0x21CD.
        #   * mask table = "sent to the Graveyard" -- the Dandylion 0x19FE family.
        #
        # *** list30 is the semantically exact register and CANNOT BE USED: all 30
        #     entries are real cards (no phantom to drop) and the array cannot grow --
        #     leave.attached_card_destroy_list abuts it at 0x0226E940. ***
        #
        # So we take the mask table, which is FIELD-ONLY anyway: event.leave_mask_is_
        # field_only (VERIFIED) proves it is read at exactly ONE site, inside this
        # dispatcher, and never on a hand discard. That is Eclipse Wyvern's shipped
        # PART A -- and EW measured precisely this configuration as field-only BEFORE
        # its PART E existed.
        #
        # ⚠️⚠️ DO NOT ALSO HOOK THE SENT-TO-GY CID SWITCH 0x021D1392. That switch is
        # EW's PART E, the ANY-LOCATION widener: with it, EW's trigger fires from a hand
        # DISCARD and a DECK MILL as well. Clause 3 says "from the field", so admitting
        # the donor there would be a bug, not a bonus.
        # ---------------------------------------------------------------------------
        MASK_BASE, MASK_COUNT, MASK_STRIDE = 0x0226EC1C, 0x98, 4   # {u16 cid, s16 mask}, sorted
        MASK_FMT = "<Hh"
        MASK_COUNT_SITE = 0x021C8108        # `movs r2,#0x98` -- must NOT change
        MASK_SENT_TO_GY = 0x0800            # the Dandylion family's mask
        MASK_DROP_PHANTOM = 0x0E80          # phantom (mask 0x0644), unclaimed; 22 phantoms exist
        MASK_NEW = (DONOR_CID, MASK_SENT_TO_GY)
        # Asserted untouched so a future patch that registers here trips the guard.
        LIST30_BASE, LIST30_COUNT = 0x0226E904, 0x1E
        LIST106_BASE, LIST106_COUNT = 0x0226E990, 0x6A
        GY_SWITCH_ARM = 0x021D147A          # the 0x16F5 arm of the any-location switch
        GY_SWITCH_ARM_STOCK = bytes.fromhex("b630854252d0")   # must stay stock

        # ---------------------------------------------------------------------------
        # PART N -- THE TARGET FILTER. One criteria row, taken verbatim from the 3DS.
        #
        # 3DS FIRST (CLAUDE.md), and it settled the whole question in one command:
        #     ... -m otn_enhanced.tools.threeds_lookup "Lightpulsar Dragon"
        #     main_effect [1568]  FFFF26E3  004B1B74  0A550002
        # i.e. the shipping Konami build gives cid 0x26E3 exactly ONE main-effect row,
        # and that row IS clause 3.
        #
        # Handler equivalence 0x004B1B74 == 0x0223C9D1, proven on FOUR independent cards
        # (the session was burned by mapping a 3DS handler pair onto the NDS
        # BY POSITION, so this time it is a join, not a guess):
        #     Chaos Goddess       0x2273  3DS 004B1B74 w 02560002 | NDS 0x0223C9D1 w 0x02550002
        #     Lord Poison         0x156D  3DS 004B1B74 w 68010022 | NDS 0x0223C9D1 w 0x68010022
        #     Call of the Haunted 0x137D  3DS 004B1B74 w 00010002 | NDS 0x0223C9D1 w 0x00010002
        #     Decoy Dragon        0x1C4F  3DS 004B1B74 w 085D0002 | NDS 0x0223C9D1 w 0x085D0002
        #
        # And the word decodes exactly as printed, against dispatch.criteria_word_fully_
        # decoded (bits 31:27 race, 26:24 attribute, 21:18 level with op bits 22/23, low
        # half a predicate bitmask):
        #     0x0A = race Dragon(1) << 3 | DARK(2)
        #     0x55 = op ">=", level 5
        #     0x0002 = bit 1, the basic "is a real card" test
        # Chaos Goddess's NDS row 1160 is 0x02550002 -- the same thing minus the Dragon
        # race nibble -- which corroborates it a third time.
        #
        # The row lands at RELATIVE INDEX 4 (the donor already owns rel 0/1 for clause 1
        # and rel 2/3 for clause 2). No native cid owns a 5-row block, but nothing in the
        # lookup cares: dispatch.criteria_registry_lookup_default walks back to the
        # LEFTMOST row for the cid (block-size agnostic) and the tail at 0x02243F08
        # bounds leftmost + r4 against CRIT_COUNT. What DOES care is the disambiguation
        # stage, and that is ours already -- see PART O.
        # ---------------------------------------------------------------------------
        C3_HANDLER = 0x0223C9D1             # "target 1 filtered monster in your GY; SS it"
        C3_WORD = 0x0A550002                # Lv5+ DARK Dragon -- the 3DS's own row for 0x26E3
        C3_ROW = (DONOR_CID, CRIT_AUX, C3_HANDLER, C3_WORD)
        C3_ROW_REL = 4
        C3_DROP_PHANTOM = 0x1138            # nearest phantom above the donor -> smallest memmove

        # ---------------------------------------------------------------------------
        # PART P -- THE ACTION. Colossal Fighter 0x1E12 is the record template.
        #
        # Its OTN effect is clause 3's shape verbatim ("...sent from the field to the
        # GY: you can target 1 Warrior-Type monster in your GY; Special Summon that
        # target"), and its cls2[357] is:
        #     +04 0x02207191   +08 0   +0C 0x021F03B5   +10 0x021E51E5   +14 0x02235605
        #
        #   * 0x02207191 is THE cls2 GY-REVIVE RESOLVER -- ~40 native cls2 records pair
        #     it with +14 = 0x02235605 (Lord Poison, Sun Dragon Inti, Moon Dragon Quilla,
        #     Lightning Tricorn, Dragunity Arma Leyvaten, the /Assault Mode family).
        #     ⚠️ NOT 0x02207529: that is the cls0 SPELL revive resolver (Premature
        #     Burial, Call of the Haunted, Monster Reborn) and has no cls2 member.
        #     Like every shared resolver here its per-cid switch only picks MODES
        #     (r4 = 1, r5 = 2 set at 0x02207198/0x0220719A) and the unnamed-cid
        #     fall-through is 0x022072DA = `0x02204730(desc, r4, r5)`, the generic body.
        #     So a records-free donor cid runs it -- the same argument already proven for
        #     0x0220731D (clause 2) and 0x02207529.
        #   * 0x021F03B5 = `0x021F0384(side)` (may you Special Summon?) then
        #     `0x02234E78(desc)` -> param then `0x02243FE0(side, desc[+0], param)`,
        #     returning 1 iff a legal target exists. Entirely cid-generic.
        #   * 0x021E51E5 is the "YOU CAN" tag -- the very slot4 value Botanical Girl
        #     carries (event.optional_trigger_is_record_shape). Optionality is a property
        #     of the +0C/+10 pair, not of the resolver, so this is what makes clause 3
        #     ask instead of resolving silently.
        #   * 0x02235605 is the off-field picker; it reads param from 0x02234E78
        #     (@0x02235610) and enumerates with 0x02243FA8(side, desc[+0], param)
        #     (@0x0223562E) -- i.e. it goes through PART O just like the condition does.
        #
        # Colossal Fighter's own criteria handler is 0x0223D6E1 (3DS 0x004A713C), a
        # DIFFERENT revive handler; we take Lightpulsar's own 0x0223C9D1 as the 3DS
        # ships it. Lord Poison 0x156D is the cls2 precedent for that handler.
        #
        # THE SLOT SPLIT. +04 and +14 differ between the two clauses and are read by the
        # engine straight out of the record, so each becomes a two-way dispatcher in
        # ov5; +0C and +10 are already our own stubs and just gain a branch:
        #
        #     slot            clause 2 (unchanged)      clause 3
        #     +04 resolver    0x0220731D                0x02207191      CAVE_LP_RESDISP
        #     +08             0                         0               (unchanged)
        #     +0C condition   the hand LIGHT/DARK scan  0x021F03B5      CAVE_LP_C2COND2
        #     +10 cost        the selection machine     0x021E51E5      CAVE_LP_C2COST
        #     +14 target      `movs r0,#1 ; bx lr`      0x02235605      CAVE_LP_TGTDISP
        #
        # ⚠️ +14's clause-2 arm returns 1 because that is EXACTLY what the engine does
        # for a null slot: the slot5 wrapper 0x0224AE84 falls to `movs r0,#1 ; pop` when
        # [rec+0x14] == 0 (and the slot4 wrapper 0x0224AE5E does the same for +0x10). So
        # clause 2's behaviour is bit-for-bit what it was with +14 = 0.
        #
        # ⚠️ All four dispatch targets are FUNCTION ENTRIES, so a register-preserving
        # `bx` is legal. dispatch.midfunction_tail_needs_prologue_frame forbids jumping
        # into a mid-function ARM -- doing that to Simorgh's 0x021FEBFE is what froze the
        # game  -- but none of these is one.
        #
        # ⚠️ ov5 is safe for both new stubs: they are reached ONLY through our own cls2
        # record, so no native card can jump into them when ov41 evicts ov5 in a puzzle.
        # The card is already duel-only because of the row hook.
        #
        # ABI (confirmed by disassembly): every slot wrapper calls with r0 = the
        # DESCRIPTOR and r1 = the invoker's arg -- 0x0224AEFC/0x0224AE98/0x0224AE64 all
        # do `adds r0,r5,#0 ; adds r1,r4,#0 ; blx r2`, and the native slot bodies read
        # the descriptor straight out of r0 (0x02207190 `ldrh r1,[r0]`, 0x021F03B4
        # `ldrb r3,[r0,#2]`, 0x02235604 `ldrb r2,[r0,#2]`). r2/r3 are free scratch.
        # ---------------------------------------------------------------------------
        PARAM_PROVIDER = 0x02234E78         # (desc) -> criteria `param`; returns 0 for our donor
                                            #   (it is in NONE of the three provider lists
                                            #   0x022710E2 / 0x02271104 / 0x022710B2 -- traced
                                            # to the fall-through leaf 0x022355F0).
                                            #   Both clause-3 consumers call it, which is why the
                                            #   row hook only ever has to answer param 0.
        C3_RESOLVER = 0x02207191            # cls2 GY-revive resolver (Colossal Fighter)
        C3_CONDITION = 0x021F03B5           # "may I SS?" + "does a legal target exist?"
        C3_COST_TAG = 0x021E51E5            # the optional-trigger ("You can") slot4 tag
        C3_PICKER = 0x02235605              # off-field / list-zone target picker
        C2_RESOLVER = 0x0220731D            # handss.self_ss_from_gy_resolver (clause 2)
        RESDISP_RESERVE = 0x20
        TGTDISP_RESERVE = 0x20

        # ---------------------------------------------------------------------------
        # PART Q -- INSTRUMENTATION, always on.
        #
        # User decision: spend ONE in-game test, and make a failure
        # self-diagnosing rather than budget a second duel. The +0C stub parks the
        # descriptor it was handed, the GLOBAL acting descriptor the row hook keys off,
        # and the row index the registry actually resolves, in CAVE_LP_DIAG -- 0x40 B of
        # scratch the shipped build otherwise never touches, so a nonzero magic proves
        # the probe ran.
        #
        #   +0x00  magic 0x4C503343 ('C3PL')
        #   +0x04  desc[+0] cid
        #   +0x08  desc[+2] | desc[+3]<<8 | desc[+4]<<16 | desc[+5]<<24   (side/zone/EVENT/cls)
        #   +0x0C  desc[+0x12], the pass index
        #   +0x10  [0x0229A9FC+0x50], the GLOBAL acting descriptor pointer
        #   +0x14  r0, the descriptor we were actually handed
        #   +0x18  0x02243B9C(DONOR, 0), the resolved criteria-row index
        #   +0x1C  *** LATCH *** the FIRST desc[+4] > 6 ever seen, as
        #          0x10000 | (zone << 8) | event -- write-once, so clause 2's constant
        #          polling can never erase it
        #   +0x20  how many such calls have happened
        #
        # ⚠️ THE LATCH EXISTS BECAUSE THE FIRST VERSION DID NOT HAVE ONE. Slots +0x00..
        # +0x18 are overwritten on EVERY call, and clause 2's GY-action poll runs
        # constantly, so after IN-GAME TEST 1 the scratch held only a clause-2 record and
        # "no clause-3 call was seen" was strong evidence rather than proof. It is proof
        # now.
        #
        # +0x10 vs +0x14 is the one assumption PART O rests on: the row hook reads the
        # GLOBAL descriptor while the condition and picker are handed one in r0. If they
        # ever differ, this says so in a single savestate.
        #
        # 0x02243B9C is a pure lookup (binary search + disambiguation, no writes), so
        # probing it cannot perturb the selection it measures -- the same argument that
        # made the instrumentation safe.
        # ---------------------------------------------------------------------------
        # ---------------------------------------------------------------------------
        # PART S -- THE TRIGGER, TAKE 2. The leave dispatcher DOES run for our cid; it
        # just never posts, because cid 0x0FB1 falls into the switch's DEFAULT arm.
        #
        # IN-GAME TEST 2 proved it with the write-once latch: CAVE_LP_DIAG
        # +0x1C == 0 and +0x20 == 0 after Lightpulsar was destroyed on the field, i.e.
        # NO descriptor with desc[+4] > 6 ever reached our cls2 record, while the stub
        # itself was demonstrably running (magic set, clause-2 polls recorded).
        #
        # TRACED: the per-cid leave switch at 0x021C8216 is a sorted binary search, and
        # cid 0x0FB1 walks
        #     0x021C8240  cmp r4,#0x13A1  -> blt
        #     0x021C824C  cmp r4,#0x0EBF  -> bgt
        #     0x021C8272  cmp r4,#0x1174  -> neither -> 0x021C827A: bl 0x021C93D0
        # and 0x021C93D0 is the DEFAULT leaf -- it sits immediately after the native post
        # (0x021C93B8 `bl 0x021D3168` ; `b 0x021C93D0`), i.e. it is the path that SKIPS
        # posting. 60+ switch sites bl into it.
        #
        # ⚠️ WHY NOT the shared any-leave trampoline at 0x021C8216 (CAVE_TG_ARMTRAMP):
        # it has 4 BYTES of headroom, and relocating it would re-wire three shipped,
        # in-game-confirmed cards (T.G. Striker / Warwolf / Rush Rhino and Quasar). Its
        # match path also gates on [sp+0x90] DESTROYED, which is narrower than "sent from
        # the field to the GY" (it would miss a Tribute or a Synchro Material use).
        #
        # ⚠️ WHY NOT a PART-A-style dead-arm repoint: there is no dead arm on this cid's
        # search path. The only equality test 0x0FB1 reaches is against 0x1174, and that
        # constant is also the binary-search PIVOT, so moving it re-routes every real cid
        # in (0x0FB1, 0x1174]. That is the same sorted-binary-search trap that made
        # Eclipse Wyvern's 0x16F5 repoint a silent no-op (event.sent_to_gy_cid_switch).
        #
        # THE HOOK: retarget the 4-byte `bl 0x021C93D0` at 0x021C827A. It is reached by
        # exactly the cids in the open interval (0x0EBF, 0x1174), and every one of them
        # currently does nothing but call the default leaf -- which our stub calls for
        # them, unchanged. So only our cid can behave differently, by construction (the
        # same argument as clause 1's payment stubs, PARTS E/F, which are in-game
        # confirmed).
        #
        # THE POST is the engine's own construction, copied instruction for instruction
        # from the native arm at 0x021C9376..0x021C93B8:
        #     zone  = ([sp+0x200] << 9) >> 0x1C, then << 16 masked 0x001F0000
        #     side  = [sp+0x98] << 31
        #     event = ([sp+0x1C] << 0x19) masked 0x7E000000     (0x17 battle / 0x1D else)
        #     cls   = 1 << 22                                    (selector 2)
        #     cid   = r4 & 0xFFFF
        #     r1    = [sp+0x9C] & 0xFFFF                         (the packed ref)
        #     r2    = [sp+0x200]                                 (the card word, per the
        #                                                         sibling post 0x021C94F6)
        #     bl 0x021D3168
        #
        # The gate is [sp+0x2C] (left the FIELD) AND [sp+0x144] (destination is the GY)
        # -- exactly the printed wording, and the same two slots list30's own arm tests
        # at 0x021C80E0.
        #
        # ⚠️ ov5 on a path shared with real cards, so it would freeze them in a puzzle.
        # That is already true of this card via the row hook (which sits on the SHARED
        # row resolver), so the blast radius is unchanged, not widened.
        # ---------------------------------------------------------------------------
        LEAVE_BL_SITE = 0x021C827A          # `bl 0x021C93D0`, reached only by (0x0EBF, 0x1174)
        LEAVE_DEFAULT_LEAF = 0x021C93D0     # the switch's do-nothing leaf
        # stack slots at the hook, read off the native post (leave.descriptor_slots)

        # ---------------------------------------------------------------------------
        # PART T -- "MISSED THE TIMING". The trigger fires; the engine just files it as
        # a WHEN effect, so using Lightpulsar as Synchro Material loses it.
        #
        # IN-GAME: with PART M restored the effect IS recognised -- the game
        # said "missed the timing" when the card was sent to the GY as Synchro Material.
        # That is a timing CLASS verdict, so the trigger, the record, the discriminator
        # and the dispatchers are all working; only the classification is wrong.
        #
        # THE CLASSIFIER IS 0x0224AF7C (timing.classifier) and it reads the record's
        # +0x10 LITERAL -- it never calls the slot, so nothing our stub does at runtime
        # can influence it:
        #
        #     0x0224AF8E  bl find_event_handler
        #     0x0224AF96  ldr r0,[rec,#0x10]      ; the RAW tag value
        #     0x0224AF98  cmp r0,#0
        #     0x0224AF9A  bne ...                 ; +10 == 0            -> class 0
        #     0x0224AFA0  cmp r0,=0x021E51E5      ; the "You can" tag   -> class 2
        #     0x0224AFAA  cmp r0,=0x021E50DD                            -> class 1
        #     ... a long chain of known tags, all -> 1 ...
        #
        # Our +0x10 is CAVE_LP_C2COST (clause 2 needs a real cost function there), which
        # matches none of the cases, so the card can never land in the mandatory class.
        #
        # *** class 0 (+10 == 0) IS THE ONE THAT CANNOT MISS THE TIMING. *** That is
        # Sangan 0x0FD6's shape (its cls2 +10 is literally 0), and
        # gravekeepers_recruiter ships exactly that pairing -- "the effect is
        # MANDATORY and fires on EVERY send-to-GY -- battle destruction, effect
        # destruction, Tribute AND Synchro Material".
        #
        # THE FIX: displace `ldr r0,[rec,#0x10] ; cmp r0,#0` at 0x0224AF96 into a stub
        # that performs the same load, and then -- for our cid, on a leave event, only --
        # substitutes 0, so the classifier sees Sangan's shape. It replays the `cmp` so
        # the caller's own `bne` gets the right flags. Every other card reaches the chain
        # with its real tag, unchanged.
        #
        # ⚠️ +0C is deliberately LEFT as 0x021F03B5. Matching Sangan exactly would mean
        # nulling it too, but that is the "does a legal target exist" gate, and removing
        # an equivalent gate is what gave Eclipse Wyvern an empty-deck FREEZE. One
        # variable at a time: this build changes the timing class and nothing else.
        # ---------------------------------------------------------------------------
        # TIMING_* now live in timing_class_hook.py (the shared owner of 0x0224AF96).

        C3_DIAG = True
        C3_DIAG_MAGIC = 0x4C503343          # 'C3PL' -- distinct from the probe's
        ACTING_DESC = 0x0229A9FC            # + 0x50 = the acting descriptor pointer
        # (the row lookup itself is C2_ROW_LOOKUP = 0x02243B9C, defined with clause 2's
        #  constants above: r0 = cid, r1 = param -> absolute criteria row index)

        # ---------------------------------------------------------------------------
        # card_prop / text
        # ---------------------------------------------------------------------------
        NEW_ATTRIBUTE = "LIGHT"             # donor is EARTH
        NEW_RACE = "Dragon"                 # donor is Dinosaur
        NEW_LEVEL = 6                       # donor is ALREADY Level 6
        NEW_ATK = 2500                      # donor was 1750
        NEW_DEF = 1500                      # donor was 2030
        NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Effect Monster"]
        NEW_NAME = b"Lightpulsar Dragon"
        # ALL THREE CLAUSES (updated -- it had still described only clause 1,
        # even though clause 2 shipped).
        #
        # ⚠️⚠️ THE DESCRIPTION IS WRITTEN STRICTLY IN PLACE and any language whose original
        # slot is smaller is SKIPPED (boggart_knight.apply_stats_and_text -- appending
        # a description is deliberately NOT done, because card_desc is read into a
        # fixed-size buffer and overrunning it blanks text and freezes rendering). So the
        # budget is the donor's ORIGINAL slot, per language. MEASURED from the
        # writer's own report for 0x0FB1:
        #
        #     e 98   f 120   g 126   i 95   s 115   j 48   k 57   r 96
        #
        # *** AND THAT MEANS THE PREVIOUS TEXT NEVER SHIPPED. *** The clause-1 description
        # this module carried until now was 108 B, i.e. larger than the English slot, so it
        # was SKIPPED in every language and the card has been showing Sword Arm of Dragon's
        # original flavour text in-game all along. Nothing reported it because a skip is a
        # printed note, not an error.
        #
        # 95 B (the 'i' slot) covers e/f/g/i/s/r. j and k are 48/57 and cannot hold any
        # useful English at all; they keep the original, which is the same compromise every
        # other patch in this repo makes.
        DESC_SLOT_MIN = 95                  # the 'i' slot; re-measure if the donor changes
        NEW_DESC = (b"SS from hand/GY by banishing/sending 1 LIGHT+1 DARK. "
                    b"Field to GY: SS 1 Lv5+ DARK Dragon.")
        assert len(NEW_DESC) <= DESC_SLOT_MIN, (
            f"description is {len(NEW_DESC)} B > the {DESC_SLOT_MIN} B slot -- it would be "
            f"SKIPPED and the card would keep Sword Arm of Dragon's flavour text")
        from otn_enhanced.data.card_stats import TEXT_LANGS


        # ---------------------------------------------------------------------------
        # helpers
        # ---------------------------------------------------------------------------






        def _adds_imm8(rd: int, imm: int) -> bytes:
            """Thumb-1 2-operand `ADDS Rd,#imm8` (format 3).

            NOTE the 3-operand `ADD Rd,Rs,#imm3` caps imm at 7 and silently miscodes
            above that (thumb.add_sub_imm3) -- this is the 2-operand form, imm8.
            """
            assert 0 <= imm <= 0xFF, f"imm8 out of range: {imm:#x}"
            return struct.pack("<H", 0x3000 | (rd << 8) | imm)




        def _u16(ov: bytearray, ram: int) -> int:
            return struct.unpack_from("<H", ov, _off(ram))[0]


        def _is_cmp_imm8(halfword: int, imm: int) -> bool:
            """True for any Thumb-1 `CMP Rd,#imm8` with this immediate, whatever Rd is.

            Format 3 puts the register in bits 8..10, so a bare equality test against
            0x2800 | imm would only ever match r0.
            """
            return (halfword & 0xF800) == 0x2800 and (halfword & 0xFF) == imm


        def _crit_rows(ov: bytearray) -> list[tuple]:
            return [struct.unpack_from(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE))
                    for i in range(CRIT_COUNT)]


        def _lista(ov: bytearray) -> list[int]:
            return [_u16(ov, LISTA_BASE + 2 * i) for i in range(LISTA_COUNT)]


        # ---------------------------------------------------------------------------
        # PART A
        # ---------------------------------------------------------------------------
        def apply_routing(ov: bytearray) -> None:
            cur_cmp = bytes(ov[_off(ARM_CMP):_off(ARM_CMP) + 2])
            cur_bl = bytes(ov[_off(ARM_BL):_off(ARM_BL) + 4])
            want_cmp = _adds_imm8(0, ARM_NEW_IMM)
            want_bl = _bl(ARM_BL, ARM_BL_NEW)

            if cur_cmp == want_cmp and cur_bl == want_bl:
                print("A  routing: already repointed (idempotent)")
                return
            assert cur_cmp == _adds_imm8(0, ARM_OLD_IMM), (
                f"A  the dead arm's compare @0x{ARM_CMP:08X} is {cur_cmp.hex()}, expected "
                f"{_adds_imm8(0, ARM_OLD_IMM).hex()} -- another patch took this arm")
            assert cur_bl == _bl(ARM_BL, ARM_BL_OLD), (
                f"A  the dead arm's BL @0x{ARM_BL:08X} is {cur_bl.hex()}, expected the dead "
                f"leaf 0x{ARM_BL_OLD:08X} -- another patch took this arm")

            ov[_off(ARM_CMP):_off(ARM_CMP) + 2] = want_cmp
            ov[_off(ARM_BL):_off(ARM_BL) + 4] = want_bl
            print(f"A  routing: dead arm repointed -- cmp 0x{ARM_BASE:04X}+0x{ARM_OLD_IMM:02X} "
                  f"-> +0x{ARM_NEW_IMM:02X} (= 0x{DONOR_CID:04X}), "
                  f"BL 0x{ARM_BL_OLD:08X} -> 0x{ARM_BL_NEW:08X}")


        # ---------------------------------------------------------------------------
        # PART B
        # ---------------------------------------------------------------------------
        def apply_count(ov: bytearray) -> None:
            cur = bytes(ov[_off(COUNT_BRANCH):_off(COUNT_BRANCH) + 2])
            want = _b(COUNT_BRANCH, COUNT_RET1)
            if cur == want:
                print("B  required-count branch: already retargeted (idempotent)")
                return
            assert cur == _b(COUNT_BRANCH, COUNT_RET0), (
                f"B  the count branch @0x{COUNT_BRANCH:08X} is {cur.hex()}, expected a branch "
                f"to the return-0 leaf 0x{COUNT_RET0:08X} -- another patch edited it")
            ov[_off(COUNT_BRANCH):_off(COUNT_BRANCH) + 2] = want
            print(f"B  required-count branch: 0x{COUNT_BRANCH:08X} -> 0x{COUNT_RET1:08X} "
                  f"(returns 1, was 0)")


        # ---------------------------------------------------------------------------
        # PART C
        # ---------------------------------------------------------------------------
        def apply_criteria_rows(ov: bytearray) -> None:
            """Count-neutral insert of the donor's LIGHT+DARK row pair.

            Both the insertion point and the phantom are located BY CID at apply time,
            never by a hardcoded index: earlier patches in the chain (boggart_knight,
            sea_lancer, shiens_dojo) insert into this same table and shift everything
            after their edits.
            """
            rows = _crit_rows(ov)
            if list(CRIT_ROWS) == [r for r in rows if r[0] == DONOR_CID][:2]:
                print(f"C1 criteria rows for 0x{DONOR_CID:04X}: already inserted (idempotent)")
                return

            cids = [r[0] for r in rows]
            assert all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)), \
                "C1 the registry is not sorted on entry -- an earlier patch broke the binary search"
            assert DONOR_CID not in cids, f"C1 cid 0x{DONOR_CID:04X} already owns a criteria row"

            drop = [i for i, c in enumerate(cids) if c == CRIT_DROP_PHANTOM]
            assert len(drop) == len(CRIT_ROWS), (
                f"C1 phantom 0x{CRIT_DROP_PHANTOM:04X} owns {len(drop)} row(s), need exactly "
                f"{len(CRIT_ROWS)} -- another patch probably took it")

            kept = [r for i, r in enumerate(rows) if i not in set(drop)]
            pos = sum(1 for r in kept if r[0] < DONOR_CID)
            new = kept[:pos] + list(CRIT_ROWS) + kept[pos:]

            assert len(new) == CRIT_COUNT, f"C1 insert was not count-neutral ({len(new)} rows)"
            ncids = [r[0] for r in new]
            assert all(ncids[i] <= ncids[i + 1] for i in range(len(ncids) - 1)), \
                "C1 the registry lost its sort order"

            for i, r in enumerate(new):
                struct.pack_into(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE), *r)
            print(f"C1 criteria rows: inserted LIGHT+DARK for 0x{DONOR_CID:04X} at [{pos}],[{pos + 1}], "
                  f"dropped both rows of phantom 0x{CRIT_DROP_PHANTOM:04X} at {drop}")

            lit = struct.unpack_from("<I", ov, _off(CRIT_COUNT_LIT))[0]
            assert lit == CRIT_COUNT, f"C1 registry count literal changed to 0x{lit:X}"


        def apply_membership(ov: bytearray) -> None:
            """Count-neutral insert of the donor into membership list A.

            Without this the lookup returns r4 = 0 for the donor, so the param-1 (DARK)
            pass would re-read the LIGHT row and the DARK half of the cost would vanish.
            """
            lst = _lista(ov)
            if DONOR_CID in lst:
                print(f"C2 membership list A: 0x{DONOR_CID:04X} already present (idempotent)")
                return
            assert all(lst[i] <= lst[i + 1] for i in range(len(lst) - 1)), \
                "C2 membership list A is not sorted on entry"
            assert LISTA_DROP_PHANTOM in lst, (
                f"C2 phantom 0x{LISTA_DROP_PHANTOM:04X} is not in list A -- another patch took it")

            kept = [c for c in lst if c != LISTA_DROP_PHANTOM]
            pos = sum(1 for c in kept if c < DONOR_CID)
            new = kept[:pos] + [DONOR_CID] + kept[pos:]
            assert len(new) == LISTA_COUNT, f"C2 insert was not count-neutral ({len(new)})"
            assert all(new[i] <= new[i + 1] for i in range(len(new) - 1)), "C2 list A lost its sort"

            for i, c in enumerate(new):
                struct.pack_into("<H", ov, _off(LISTA_BASE + 2 * i), c)
            print(f"C2 membership list A: inserted 0x{DONOR_CID:04X} at [{pos}], "
                  f"dropped phantom 0x{LISTA_DROP_PHANTOM:04X}")


        def apply_payment(ov: bytearray) -> None:
            """PARTS D/E/F -- the SHARED payment side (handss_banish_cost).

            Idempotent and order-independent: it writes stubs covering every registered
            banish-cost donor, so it does not matter whether this card or Darkflare
            Dragon gets there first.
            """
            nonlocal _PAY2_STUB_BASE
            _PAY2_STUB_BASE = banish.apply(ov)


        _PAY2_STUB_BASE = None


        def _proc_rows(ov: bytearray) -> list[tuple[int, int]]:
            return [struct.unpack_from("<II", ov, _off(PROC_BASE + i * PROC_STRIDE))
                    for i in range(PROC_COUNT)]


        def apply_procedure_row(ov: bytearray) -> None:
            """PART G: give the donor a row in the summon-procedure registry.

            Without this the binary search at 0x02264DB4 misses, the engine takes its
            not-found branch, and the card Special Summons for FREE -- the exact in-game
            failure of tests 1 and 2. Count-neutral: phantom 0x0ECA is dropped.
            """
            rows = _proc_rows(ov)
            want = (DONOR_CID, PROC_HANDLER)
            if want in rows:
                print(f"G summon-procedure row for 0x{DONOR_CID:04X}: already present (idempotent)")
                return

            cids = [c for c, _ in rows]
            assert all(cids[i] < cids[i + 1] for i in range(len(cids) - 1)), \
                "G the procedure registry is not strictly sorted -- the binary search would break"
            assert DONOR_CID not in cids, f"G cid 0x{DONOR_CID:04X} already owns a procedure row"
            assert PROC_DROP_PHANTOM in cids, (
                f"G phantom 0x{PROC_DROP_PHANTOM:04X} is gone -- another patch took it")

            kept = [r for r in rows if r[0] != PROC_DROP_PHANTOM]
            pos = sum(1 for c, _ in kept if c < DONOR_CID)
            new = kept[:pos] + [want] + kept[pos:]
            assert len(new) == PROC_COUNT, f"G insert was not count-neutral ({len(new)} rows)"
            ncids = [c for c, _ in new]
            assert all(ncids[i] < ncids[i + 1] for i in range(len(ncids) - 1)), \
                "G the registry lost its strict sort"

            for i, r in enumerate(new):
                struct.pack_into("<II", ov, _off(PROC_BASE + i * PROC_STRIDE), *r)
            print(f"G summon-procedure row: {{0x{DONOR_CID:04X} -> 0x{PROC_HANDLER:08X}}} at [{pos}], "
                  f"dropped phantom 0x{PROC_DROP_PHANTOM:04X}")

            for lit in PROC_COUNT_LITS:
                got = _u16(ov, lit)
                assert got == (0x2200 | PROC_COUNT), (
                    f"G the row-count immediate at 0x{lit:08X} is {got:#06x}, expected "
                    f"{0x2200 | PROC_COUNT:#06x} (`movs r2,#{PROC_COUNT:#x}`)")




        def _cls2_rows(ov: bytearray) -> list[tuple]:
            return [struct.unpack_from("<6I", ov, _off(CLS2_BASE + i * CLS2_STRIDE))
                    for i in range(CLS2_COUNT)]


        def apply_clause2_record(ov: bytearray) -> None:
            """PART I: the cls2 record, cloned from Dark Simorgh's GY-summon record [375]."""
            rows = _cls2_rows(ov)
            rec = _cls2_record()
            if rec in rows:
                print("I clause-2 cls2 record: already present (idempotent)")
                return

            cids = [r[0] for r in rows]
            assert all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)), \
                "I the cls2 table is not sorted on entry"
            assert DONOR_CID not in cids, f"I cid 0x{DONOR_CID:04X} already owns a cls2 record"
            assert CLS2_DROP_PHANTOM in cids, (
                f"I phantom 0x{CLS2_DROP_PHANTOM:04X} is gone -- another patch took it")

            kept = [r for r in rows if r[0] != CLS2_DROP_PHANTOM]
            pos = sum(1 for r in kept if r[0] < DONOR_CID)
            new = kept[:pos] + [rec] + kept[pos:]
            assert len(new) == CLS2_COUNT, f"I insert was not count-neutral ({len(new)})"
            ncids = [r[0] for r in new]
            assert all(ncids[i] <= ncids[i + 1] for i in range(len(ncids) - 1)), \
                "I the cls2 table lost its sort order"

            for i, r in enumerate(new):
                struct.pack_into("<6I", ov, _off(CLS2_BASE + i * CLS2_STRIDE), *r)
            print(f"I clause-2 cls2 record at [{pos}]: resolver 0x{rec[1]:08X}, "
                  f"cond 0x{rec[3]:08X}, cost 0x{rec[4]:08X} "
                  f"(cloned from Dark Simorgh cls2[375]); dropped phantom 0x{CLS2_DROP_PHANTOM:04X}")


        def _gyreg_rows(ov: bytearray) -> list[tuple[int, int, int, int]]:
            return [struct.unpack_from(GYREG_FMT, ov, _off(GYREG_BASE + i * GYREG_STRIDE))
                    for i in range(GYREG_COUNT)]


        def apply_donor_hand_rows(ov: bytearray) -> None:
            """PART H: clause 2's rows go on the DONOR at rel 2/3, like Simorgh's.

            Reachable only because criteria_row_hook.ARM_LP supplies the `r4 = 2 + pass` arm that
            the compiled switch has for 0x1E5A and cannot have for us. Count-neutral:
            phantom 0x1303's two rows are dropped (it is no longer needed as a proxy).
            """
            rows = _crit_rows(ov)
            want = ((DONOR_CID, CRIT_AUX, C2_HANDLER, C2_WORD_LIGHT_HAND),
                    (DONOR_CID, CRIT_AUX, C2_HANDLER, C2_WORD_DARK_HAND))
            mine = [r for r in rows if r[0] == DONOR_CID]
            if len(mine) == 4 and tuple(mine[2:]) == want:
                print("H donor hand rows: already at rel 2,3 (idempotent)")
                return
            assert len(mine) == 2 and tuple(mine) == CRIT_ROWS, (
                f"H expected clause 1's 2 rows on 0x{DONOR_CID:04X}, found {len(mine)}")
            cids = [r[0] for r in rows]
            drop = [i for i, c in enumerate(cids) if c == PROXY_CID]
            assert len(drop) == 2, f"H phantom 0x{PROXY_CID:04X} owns {len(drop)} rows, need 2"
            kept = [r for i, r in enumerate(rows) if i not in set(drop)]
            pos = max(i for i, r in enumerate(kept) if r[0] == DONOR_CID) + 1
            new = kept[:pos] + list(want) + kept[pos:]
            assert len(new) == CRIT_COUNT, f"H insert not count-neutral ({len(new)})"
            n = [r[0] for r in new]
            assert all(n[i] <= n[i + 1] for i in range(len(n) - 1)), "H registry lost its sort"
            for i, r in enumerate(new):
                struct.pack_into(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE), *r)
            print(f"H donor hand rows at [{pos}],[{pos+1}] (rel 2,3), phantom 0x{PROXY_CID:04X} dropped")


        def apply_row_hook(ov: bytearray) -> None:
            """PART O: hook the criteria-row disambiguation at 0x02243BEC.

            ⚠️ THE SITE HAS EXACTLY ONE 4-BYTE BL AND IT IS NOW SHARED. The stub, the arms
            and the cid register moved to criteria_row_hook.py on 2026-08-18 when Darkflare
            Dragon needed an arm of its own -- the same lift handss_banish_cost.py did to
            the payment stubs, and for the same reason: re-pointing the hook would have
            broken clauses 2 AND 3 here. This card's arm is `rowhook.ARM_LP`.
            """
            rowhook.apply(ov)


        def apply_gy_registry(ov: bytearray) -> None:
            """PART K: give the donor a row in the GY-action registry 0x0228DDF8.

            Without this the enumerator 0x0224C590 is never invoked for our cid, so no
            descriptor is ever built and the cls2 record's condition is never called --
            the exact in-game symptom (savestate-resident wiring, zero offers).

            Count-neutral by construction: a phantom row's cid word is rewritten in
            place. The table is unsorted, so no ordering has to be preserved.
            """
            # The row count is an imm8 at every scanner; if one drifted, our index range
            # would no longer match what the engine walks. Bits 8..10 hold the register
            # (r6 @0x0224C99A, r4 @0x0224CD30), so mask it out and compare the imm8 only.
            for site in GYREG_COUNT_SITES:
                got = _u16(ov, site)
                assert _is_cmp_imm8(got, GYREG_COUNT), (
                    f"K the row-count immediate at 0x{site:08X} is {got:#06x}, expected "
                    f"`cmp rX,#{GYREG_COUNT:#x}`")

            rows = _gyreg_rows(ov)
            want = (DONOR_CID, GYREG_ZONE_GY, GYREG_CHECK, GYREG_POST)
            if want in rows:
                print(f"K GY-action registry row for 0x{DONOR_CID:04X}: already present (idempotent)")
                return

            cids = [r[0] for r in rows]
            assert cids.count(DONOR_CID) == 0, (
                f"K cid 0x{DONOR_CID:04X} already owns a GY-action registry row")
            assert cids.count(GYREG_DROP_PHANTOM) == 1, (
                f"K phantom 0x{GYREG_DROP_PHANTOM:04X} owns {cids.count(GYREG_DROP_PHANTOM)} "
                f"row(s), need exactly 1 -- another patch took it")

            idx = cids.index(GYREG_DROP_PHANTOM)
            row = rows[idx]
            assert row[1:] == (GYREG_ZONE_GY, GYREG_CHECK, GYREG_POST), (
                f"K the phantom row [{idx}] is {row!r}, expected zone 0x{GYREG_ZONE_GY:02X} "
                f"with the GY-effect family 0x{GYREG_CHECK:08X}/0x{GYREG_POST:08X}")

            struct.pack_into("<I", ov, _off(GYREG_BASE + idx * GYREG_STRIDE), DONOR_CID)
            print(f"K GY-action registry: row [{idx}] @0x{GYREG_BASE + idx * GYREG_STRIDE:08X} "
                  f"phantom 0x{GYREG_DROP_PHANTOM:04X} -> 0x{DONOR_CID:04X} "
                  f"(zone 0x{GYREG_ZONE_GY:02X}, check 0x{GYREG_CHECK:08X})")


        def _mask_rows(ov: bytearray) -> list[tuple[int, int]]:
            return [struct.unpack_from(MASK_FMT, ov, _off(MASK_BASE + i * MASK_STRIDE))
                    for i in range(MASK_COUNT)]


        def apply_leave_mask(ov: bytearray) -> None:
            """PART M: clause 3's TRIGGER -- a `sent to the GY` row in the leave-mask table.

            *** THIS IS THE RIGHT MECHANISM. It was briefly unwired on 2026-08-17 on a
            misreading, and unwiring it is what made IN-GAME TEST 2 fail. ***

            THE MECHANISM, traced properly the third time. The leave dispatcher's per-cid
            switch at 0x021C8216 sends cid 0x0FB1 to `bl 0x021C93D0` at 0x021C827A -- and
            SANGAN 0x0FD6, whose any-means sent-to-GY trigger works natively and is the
            template gravekeepers_recruiter ships, lands on THE SAME SITE (both are
            in the interval (0x0EBF, 0x1174)). 0x021C93D0 is not a do-nothing leaf; it is
            the generic tail. So the switch arm is not what distinguishes them --
            `[sp+0x18]` is, and that flag is set by exactly three things
            (event.leave_dispatcher_three_registers):

                list106 0x0226E990   [sp+0x44] battle && [sp+0x90] destroyed && [sp+0x144] to-GY
                list30  0x0226E904   [sp+0x2C] left the field && [sp+0x144] to-GY
                mask    0x0226EC1C   consulted ONLY if neither list armed it; each set bit
                                     adds a precondition, and bit 11 (0x0800) requires
                                     [sp+0x144], destination is the GY

            Sangan and Botanical Girl are natively in list30. Our donor is in none of them
            and list30 is FULL (30/30 real cards, and leave.attached_card_destroy_list abuts
            it at 0x0226E940), so we take the mask table -- which reaches the same flag, and
            with mask 0x0800 carries the same meaning, because the whole dispatcher is
            field-only (event.leave_mask_is_field_only).

            Count-neutral: drop one phantom row, insert ours at the sorted position.
            """
            # the count immediate the engine's own binary search uses
            got = _u16(ov, MASK_COUNT_SITE)
            assert got == (0x2200 | MASK_COUNT), (
                f"M the mask-table count at 0x{MASK_COUNT_SITE:08X} is {got:#06x}, expected "
                f"`movs r2,#{MASK_COUNT:#x}`")
            # ⚠️ the any-location widener must stay stock -- see the PART M note
            arm = bytes(ov[_off(GY_SWITCH_ARM):_off(GY_SWITCH_ARM) + len(GY_SWITCH_ARM_STOCK)])
            assert arm == GY_SWITCH_ARM_STOCK, (
                f"M the sent-to-GY cid switch @0x{GY_SWITCH_ARM:08X} is not stock ({arm.hex()}) -- "
                f"clause 3 must NOT be admitted there or it fires from a discard and a mill too")

            rows = _mask_rows(ov)
            if MASK_NEW in rows:
                print(f"M leave-mask row for 0x{DONOR_CID:04X}: already present (idempotent)")
                return
            cids = [c for c, _ in rows]
            assert all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)), \
                "M the leave-mask table is not sorted on entry"
            assert cids.count(DONOR_CID) == 0, f"M cid 0x{DONOR_CID:04X} already owns a mask row"
            assert cids.count(MASK_DROP_PHANTOM) == 1, (
                f"M phantom 0x{MASK_DROP_PHANTOM:04X} owns {cids.count(MASK_DROP_PHANTOM)} mask "
                f"row(s), need exactly 1 -- another patch took it")
            # Eclipse Wyvern owns 0x16F5 in this same table; its row must survive untouched.
            kept = [r for r in rows if r[0] != MASK_DROP_PHANTOM]
            pos = sum(1 for c, _ in kept if c < DONOR_CID)
            new = kept[:pos] + [MASK_NEW] + kept[pos:]
            assert len(new) == MASK_COUNT, f"M insert was not count-neutral ({len(new)})"
            n = [c for c, _ in new]
            assert all(n[i] <= n[i + 1] for i in range(len(n) - 1)), "M mask table lost its sort"
            for i, r in enumerate(new):
                struct.pack_into(MASK_FMT, ov, _off(MASK_BASE + i * MASK_STRIDE), *r)
            print(f"M leave-mask row [{pos}] {{0x{DONOR_CID:04X}, 0x{MASK_SENT_TO_GY:04X}}} "
                  f"(sent from the field to the GY); dropped phantom 0x{MASK_DROP_PHANTOM:04X}")


        def apply_clause3_row(ov: bytearray) -> None:
            """PART N: clause 3's target filter -- one criteria row on the donor at rel 4.

            {0x0FB1, 0xFFFF, 0x0223C9D1, 0x0A550002} == the 3DS's own row for the
            natively-shipped Lightpulsar Dragon (cid 0x26E3), with the handler mapped by
            a four-card join rather than by position.

            Reachable only because criteria_row_hook.ARM_LP's clause-3 branch returns r4 = 4 for a
            descriptor carrying event 0x1E. Count-neutral: single-row phantom 0x1138.
            """
            rows = _crit_rows(ov)
            mine = [r for r in rows if r[0] == DONOR_CID]
            if len(mine) == 5 and mine[C3_ROW_REL] == C3_ROW:
                print(f"N clause-3 criteria row: already at rel {C3_ROW_REL} (idempotent)")
                return
            assert len(mine) == 4, (
                f"N expected the donor's 4 rows (clause 1 at rel 0/1, clause 2 at rel 2/3), "
                f"found {len(mine)} -- run apply_donor_hand_rows first")
            assert tuple(mine[:2]) == CRIT_ROWS, "N clause 1's rows 0/1 are not intact"
            cids = [r[0] for r in rows]
            assert cids.count(C3_DROP_PHANTOM) == 1, (
                f"N phantom 0x{C3_DROP_PHANTOM:04X} owns {cids.count(C3_DROP_PHANTOM)} criteria "
                f"row(s), need exactly 1 -- another patch took it")
            di = cids.index(C3_DROP_PHANTOM)
            kept = rows[:di] + rows[di + 1:]
            pos = max(i for i, r in enumerate(kept) if r[0] == DONOR_CID) + 1
            new = kept[:pos] + [C3_ROW] + kept[pos:]
            assert len(new) == CRIT_COUNT, f"N insert not count-neutral ({len(new)})"
            n = [r[0] for r in new]
            assert all(n[i] <= n[i + 1] for i in range(len(n) - 1)), "N registry lost its sort"
            for i, r in enumerate(new):
                struct.pack_into(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE), *r)
            print(f"N clause-3 criteria row at [{pos}] (rel {C3_ROW_REL}): handler "
                  f"0x{C3_HANDLER:08X}, word 0x{C3_WORD:08X} (Lv5+ DARK Dragon in your GY); "
                  f"dropped phantom 0x{C3_DROP_PHANTOM:04X}")


        def apply_leave_hook(ov: bytearray) -> None:
            """⛔ PART S -- UNNECESSARY. NOT CALLED. Kept for the switch trace, which is real.

            Written on 2026-08-17 to post the leave event by hand, on the belief that the
            switch's arm for our cid (`bl 0x021C93D0` @0x021C827A) was a do-nothing leaf.
            IT IS NOT: Sangan 0x0FD6 reaches the same arm and triggers correctly. The arm
            is generic; what it needs is the `[sp+0x18]` flag, which PART M supplies. This
            would have hooked a site shared by 692 cids (316 real cards, Blue-Eyes and Dark
            Magician among them) to fix a problem that did not exist.

            THE TRACE ITSELF IS STILL WORTH HAVING: cid 0x0FB1 walks the sorted binary
            search 0x021C8240 (vs 0x13A1, blt) -> 0x021C824C (vs 0x0EBF, bgt) ->
            0x021C8272 (vs 0x1174, neither) -> 0x021C827A. There is no dead arm on that
            path -- the only equality test it reaches is against 0x1174, which is also the
            pivot -- so a PART-A-style repoint is impossible for this cid either way.
            """
            raise AssertionError(
                "PART S is unnecessary and unwired -- the leave arm is generic and PART M's "
                "mask row is what arms it; see this function's docstring")



        def apply_timing(ov: bytearray) -> None:
            """PART T: hook the timing classifier's +10 read so clause 3 IS classified.

            Delegates to the SHARED timing_class_hook (which owns the single 4-byte site
            0x0224AF96 and carries this card's arm as ARM_LP). Without the hook the card is
            in no timing class and the engine stays SILENT when the trigger is lost; with it
            the game correctly reports "missed the timing".
            """
            timinghook.apply(ov)


        def apply_effect(ov: bytearray) -> None:
            apply_routing(ov)
            apply_count(ov)
            apply_criteria_rows(ov)
            apply_membership(ov)
            apply_payment(ov)
            apply_procedure_row(ov)
            apply_donor_hand_rows(ov)   # PART H  -- clause 2's rows at rel 2/3
            apply_clause3_row(ov)       # PART N  -- clause 3's row at rel 4 (must follow H)
            apply_clause2_record(ov)    # PART I  -- the single shared cls2 record
            apply_gy_registry(ov)       # PART K  -- makes clause 2 offerable from the GY
            apply_row_hook(ov)          # PART O  -- supplies the row offset for both clauses
            apply_leave_mask(ov)        # PART M  -- clause 3's trigger
            apply_timing(ov)            # PART T  -- ...classified as a WHEN trigger
                # ⛔ PART S (a code hook on the leave switch) IS NOT CALLED -- see
                #    apply_leave_hook's docstring. It solved a problem that did not exist.



        def install(rom, view):
            ov = view.buf
            apply_effect(ov)

            # PART J: the condition. The SHIPPED record points +0C at the native 0x021FEBA9 (all ov3); only the DIAG build installs an ov5 stub.
            rowhook.install(rom)

            # PART P -- the two record slots the engine reads directly, so each needs a dispatcher of its own.
            rd = _stub_res_disp(ov5_cave.CAVE_LP_RESDISP)
            effect_verify.assert_thumb1_only(rd, ov5_cave.CAVE_LP_RESDISP)
            assert len(rd) <= RESDISP_RESERVE, f"P resolver dispatcher is {len(rd)} B > reserve"
            ov5_cave.install_cave(rom, ov5_cave.CAVE_LP_RESDISP, rd, reserve=RESDISP_RESERVE)

            timinghook.install(rom)     # PART T, the shared stub (ARM_LP is this card)

            td = _stub_tgt_disp(ov5_cave.CAVE_LP_TGTDISP)
            effect_verify.assert_thumb1_only(td, ov5_cave.CAVE_LP_TGTDISP)
            assert len(td) <= TGTDISP_RESERVE, f"P target dispatcher is {len(td)} B > reserve"
            ov5_cave.install_cave(rom, ov5_cave.CAVE_LP_TGTDISP, td, reserve=TGTDISP_RESERVE)

            cost = _stub_c2_cost(ov5_cave.CAVE_LP_C2COST)
            effect_verify.assert_thumb1_only(cost, ov5_cave.CAVE_LP_C2COST)
            assert len(cost) <= C2_COST_RESERVE, f"clause-2 cost stub is {len(cost)} B > the {C2_COST_RESERVE:#x} reserve"
            ov5_cave.install_cave(rom, ov5_cave.CAVE_LP_C2COST, cost, reserve=C2_COST_RESERVE)

            blob = _stub_c2_cond(ov5_cave.CAVE_LP_C2COND2)
            effect_verify.assert_thumb1_only(blob, ov5_cave.CAVE_LP_C2COND2)
            assert len(blob) <= C2_COND_RESERVE, f"J condition stub is {len(blob)} B > reserve"
            ov5_cave.install_cave(rom, ov5_cave.CAVE_LP_C2COND2, blob, reserve=C2_COND_RESERVE)

        def check_fn(c, rom, view):
            def check(cond, msg):
                c.ok(bool(cond), msg)
                return bool(cond)

            ov = view.buf
            _rom = rom

            ok = True

            # -- A: the dead arm is repointed at the donor and at the LIGHT+DARK leaf
            ok &= check(bytes(ov[_off(ARM_CMP):_off(ARM_CMP) + 2]) == _adds_imm8(0, ARM_NEW_IMM),
                        f"A routing compare @0x{ARM_CMP:08X} selects 0x{DONOR_CID:04X}")
            ok &= check(bytes(ov[_off(ARM_BL):_off(ARM_BL) + 4]) == _bl(ARM_BL, ARM_BL_NEW),
                        f"A routing BL @0x{ARM_BL:08X} -> LIGHT+DARK leaf 0x{ARM_BL_NEW:08X}")

            # the enclosing range compares must be untouched, or other cids get misrouted
            ok &= check(_u16(ov, 0x0225E6CC) == 0x494F and _u16(ov, 0x0225E6D4) == 0x484E,
                        "A the arm's enclosing range compares are unmodified")
            # the leaf itself must still be the generic two-pass cost
            ok &= check(_u16(ov, 0x0225FA6A) == 0x2100 and _u16(ov, 0x0225FA8A) == 0x2101,
                        "A leaf 0x0225FA46 still writes pass indices 0 then 1")

            # -- B: the count branch, and the invariant that bounds its blast radius
            ok &= check(bytes(ov[_off(COUNT_BRANCH):_off(COUNT_BRANCH) + 2])
                        == _b(COUNT_BRANCH, COUNT_RET1),
                        f"B count branch @0x{COUNT_BRANCH:08X} -> return-1 leaf")
            ok &= check(_u16(ov, COUNT_RET1) == 0x2001 and _u16(ov, COUNT_RET1 + 2) == 0x4770,
                        "B the return-1 leaf really is `movs r0,#1 ; bx lr`")
            # The blast-radius argument depends on the NATIVE banish-cost routes being
            # unchanged: if a later patch repoints one of these at a cid < 0x1466, that
            # card would silently inherit our required-count of 1.
            def _bl_target(src: int) -> int:
                w1, w2 = struct.unpack_from("<HH", ov, _off(src))
                off = ((w1 & 0x7FF) << 12) | ((w2 & 0x7FF) << 1)
                if off & (1 << 22):
                    off -= (1 << 23)
                return src + 4 + off

            ok &= check(_bl_target(0x0225E8E0) == 0x0225FA46,
                        "B the native LIGHT+DARK route (Chaos family) is unchanged")
            ok &= check(_bl_target(0x0225E838) == 0x0225FA36,
                        "B the native single-attribute route (Fenrir family) is unchanged")

            # -- C1: criteria rows -- exactly two, right shape, right order, sorted, count kept
            rows = _crit_rows(ov)
            cids = [r[0] for r in rows]
            mine = [r for r in rows if r[0] == DONOR_CID]
            # clause 2 adds two more rows at rel 2/3 and clause 3 a fifth at rel 4, so
            # clause 1 always owns the FIRST two -- which is what the next check pins.
            ok &= check(len(mine) in (2, 4, 5),
                        f"C1 donor owns 2 (clause 1), 4 (+ clause 2) or 5 (+ clause 3) "
                        f"criteria rows (found {len(mine)})")
            ok &= check(tuple(mine[:2]) == CRIT_ROWS,
                        "C1 rel 0,1 are {LIGHT, DARK} with aux 0xFFFF and handler 0x0223CA11")
            ok &= check(bool(mine) and mine[0][3] == CRIT_WORD_LIGHT,
                        "C1 LIGHT is the FIRST row (param 0) -- order is load-bearing")
            ok &= check(CRIT_DROP_PHANTOM not in cids,
                        f"C1 phantom 0x{CRIT_DROP_PHANTOM:04X} fully dropped")
            ok &= check(all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)),
                        "C1 registry still sorted (the binary search's precondition)")
            ok &= check(len(rows) == CRIT_COUNT
                        and struct.unpack_from("<I", ov, _off(CRIT_COUNT_LIT))[0] == CRIT_COUNT,
                        f"C1 registry still {CRIT_COUNT} rows and the count literal agrees")

            # -- C2: the membership entry that makes param 1 resolve
            lst = _lista(ov)
            ok &= check(lst.count(DONOR_CID) == 1,
                        f"C2 0x{DONOR_CID:04X} is in membership list A exactly once")
            ok &= check(LISTA_DROP_PHANTOM not in lst,
                        f"C2 phantom 0x{LISTA_DROP_PHANTOM:04X} dropped")
            ok &= check(all(lst[i] <= lst[i + 1] for i in range(len(lst) - 1)),
                        "C2 membership list A still sorted")
            ok &= check(len(lst) == LISTA_COUNT, f"C2 list A still {LISTA_COUNT} entries")

            # -- D/E/F: the SHARED payment side (stubs, both hooks, the cave invariant)
            ok &= banish.verify(ov, check)
            ok &= check(DONOR_CID in banish.DONOR_CIDS,
                        f"E/F 0x{DONOR_CID:04X} is in the shared banish-cost donor register "
                        f"(without it the card summons for FREE)")

            # -- G: the summon-procedure row -- WITHOUT THIS THE CARD SUMMONS FOR FREE
            prows = _proc_rows(ov)
            pcids = [c for c, _ in prows]
            ok &= check(pcids.count(DONOR_CID) == 1,
                        f"G exactly 1 summon-procedure row for 0x{DONOR_CID:04X}")
            ok &= check((DONOR_CID, PROC_HANDLER) in prows,
                        f"G the row maps 0x{DONOR_CID:04X} -> the payment handler 0x{PROC_HANDLER:08X}")
            ok &= check(PROC_DROP_PHANTOM not in pcids,
                        f"G phantom 0x{PROC_DROP_PHANTOM:04X} dropped")
            ok &= check(all(pcids[i] < pcids[i + 1] for i in range(len(pcids) - 1)),
                        "G registry still strictly sorted (the binary search's precondition)")
            ok &= check(len(prows) == PROC_COUNT, f"G registry still {PROC_COUNT} rows")
            ok &= check(all(_u16(ov, lit) == (0x2200 | PROC_COUNT) for lit in PROC_COUNT_LITS),
                        "G both searchers' row-count immediates still agree")
            # the Chaos family must still map to the same handler we borrowed
            ok &= check(all((cid, PROC_HANDLER) in prows for cid in (0x16C9, 0x16CB, 0x16E4)),
                        "G the Chaos family still maps to the same payment handler")

            # -- H: where clause 2's rows live differs between the two designs
            block = [r for r in rows if r[0] == DONOR_CID]
            proxy = [r for r in rows if r[0] == PROXY_CID]
            ok &= check(len(block) == 5, f"H donor owns 5 criteria rows (found {len(block)}) "
                                         f"-- Simorgh's 4 plus clause 3's revive row")
            ok &= check(block[:2] == list(CRIT_ROWS),
                        "H clause 1's GY LIGHT/DARK are STILL rel 0,1 (its leaf passes param 0/1)")
            ok &= check(all(r[2] == C2_HANDLER for r in block[2:4]),
                        f"H clause 2's HAND pair is rel 2,3 under handler 0x{C2_HANDLER:08X}")
            ok &= check(not proxy, f"H proxy 0x{PROXY_CID:04X} owns no rows (not needed)")
            ok &= check(DONOR_CID in lst, f"H donor 0x{DONOR_CID:04X} is in membership list A (clause 1)")

            # -- I: the cls2 record
            c2 = _cls2_rows(ov)
            c2cids = [r[0] for r in c2]
            ok &= check(c2cids.count(DONOR_CID) == 1,
                        f"I exactly 1 cls2 record for 0x{DONOR_CID:04X}")
            ok &= check(_cls2_record() in c2,
                        "I the cls2 record matches Dark Simorgh cls2[375]'s shape")
            ok &= check(_cls2_record()[3] == (ov5_cave.CAVE_LP_C2COND2 | 1),
                        "J +0C is our condition stub (hand LIGHT+DARK gate, then the native check)")
            ok &= check(_u16(ov, C2_COND_NATIVE & ~1) == 0xB538,
                        f"J the native condition 0x{C2_COND_NATIVE:08X} we call is unmoved")
            ok &= check(c2cids.count(PROXY_CID) == 0,
                        f"I2 no proxy cls2 record needed (desc[+0] is never swapped)")
            ok &= check(CLS2_DROP_PHANTOM not in c2cids,
                        f"I phantom 0x{CLS2_DROP_PHANTOM:04X} dropped")
            ok &= check(all(c2cids[i] <= c2cids[i + 1] for i in range(len(c2cids) - 1)),
                        "I cls2 table still sorted")
            ok &= check(len(c2) == CLS2_COUNT, f"I cls2 table still {CLS2_COUNT} records")
            # the template must be intact -- we cloned it
            ok &= check((0x1E5A, 0x0220731D, 0, 0x021FEBA9, 0x021EC57D, 0) in c2,
                        "I Dark Simorgh's GY-summon record (the template) is unchanged")

            # -- K: the GY-action registry row -- WITHOUT THIS THE EFFECT IS NEVER OFFERED
            greg = _gyreg_rows(ov)
            gcids = [r[0] for r in greg]
            ok &= check(gcids.count(DONOR_CID) == 1,
                        f"K exactly 1 GY-action registry row for 0x{DONOR_CID:04X}")
            ok &= check((DONOR_CID, GYREG_ZONE_GY, GYREG_CHECK, GYREG_POST) in greg,
                        f"K the row is zone 0x{GYREG_ZONE_GY:02X} with the GY-effect family "
                        f"0x{GYREG_CHECK:08X}/0x{GYREG_POST:08X}")
            ok &= check(GYREG_DROP_PHANTOM not in gcids,
                        f"K phantom 0x{GYREG_DROP_PHANTOM:04X} dropped")
            ok &= check(len(greg) == GYREG_COUNT and all(
                _is_cmp_imm8(_u16(ov, s), GYREG_COUNT) for s in GYREG_COUNT_SITES),
                        f"K registry still {GYREG_COUNT} rows and every scanner bound agrees")
            # composition guard: the native GY summoners must keep their rows, or this
            # patch has silently disabled a shipped card's Graveyard effect.
            ok &= check(all(cid in gcids for cid in (0x1E5A, 0x1EA9, 0x202C, 0x1E15, 0x225B)),
                        "K Simorgh / Plaguespreader / Soulkius / Quillbolt / Spore keep their rows")

            # -- L: clause 2 owns its cost; NOTHING hooks Dark Simorgh's any more
            ok &= check(struct.unpack_from("<I", ov, _off(0x021EC644))[0] == C2_CB_NATIVE,
                        "L Simorgh's selection callback literal is untouched")
            ok &= check(bytes(ov[_off(0x021EC5B8):_off(0x021EC5B8) + 4]) == _bl(0x021EC5B8, C2_ARM_TARGET),
                        "L Simorgh's cost still calls 0x0224B9F0 directly (our hook is gone)")
            ok &= check(_u16(ov, C2_SEND_TO_GY) == 0xB51C and _u16(ov, 0x021C6E98) == 0xB51C,
                        f"L the send-to-GY wrapper 0x{C2_SEND_TO_GY:08X} and the banish wrapper "
                        f"0x021C6E98 are still the sibling pair")
            ok &= check(_u16(ov, 0x0220660C) == 0x290B,
                        "L the native selection callback still pins its probe to the HAND")
            ok &= rowhook.verify(ov, check, rom=_rom)
            ok &= check(DONOR_CID in [c for c, *_ in rowhook.ARMS],
                        f"R cid 0x{DONOR_CID:04X} has an arm on the SHARED row hook")

            # ================= CLAUSE 3 =================
            # -- N: the revive row at rel 4, and clauses 1/2 unmoved above it
            ok &= check(block[C3_ROW_REL] == C3_ROW,
                        f"N clause 3's row is rel {C3_ROW_REL}: handler 0x{C3_HANDLER:08X}, "
                        f"word 0x{C3_WORD:08X} (== the 3DS's own row for cid 0x26E3)")
            ok &= check(C3_DROP_PHANTOM not in cids,
                        f"N phantom 0x{C3_DROP_PHANTOM:04X} dropped (count-neutral)")
            ok &= check(len(rows) == CRIT_COUNT
                        and all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)),
                        f"N criteria registry still {CRIT_COUNT} rows and sorted")
            # a 5-row block is unattested, so pin the bound the tail checks it against
            ok &= check(struct.unpack_from("<I", ov, _off(CRIT_COUNT_LIT))[0] == CRIT_COUNT,
                        f"N the registry count literal @0x{CRIT_COUNT_LIT:08X} is still "
                        f"0x{CRIT_COUNT:X} (leftmost + r4 is bounds-checked against it)")

            # -- M: THE TRIGGER. A row in the leave-mask table 0x0226EC1C is what sets
            # [sp+0x18], the flag the leave switch's generic arm needs. Sangan 0x0FD6
            # reaches the SAME arm as our donor and triggers natively purely on its
            # list30 membership, so the arm is generic and only the flag matters.
            mrows = _mask_rows(ov)
            mcids = [c for c, _ in mrows]
            ok &= check(MASK_NEW in mrows,
                        f"M leave-mask row {{0x{DONOR_CID:04X}, 0x{MASK_SENT_TO_GY:04X}}} present "
                        f"-- THE TRIGGER (removing it is what broke in-game test 2)")
            ok &= check(mcids.count(DONOR_CID) == 1, "M exactly one mask row for the donor")
            ok &= check(MASK_DROP_PHANTOM not in mcids,
                        f"M phantom 0x{MASK_DROP_PHANTOM:04X} dropped (count-neutral)")
            ok &= check(len(mrows) == MASK_COUNT and _u16(ov, MASK_COUNT_SITE) == (0x2200 | MASK_COUNT),
                        f"M mask table still 0x{MASK_COUNT:X} rows and the search bound agrees")
            ok &= check(all(mcids[i] <= mcids[i + 1] for i in range(len(mcids) - 1)),
                        "M mask table still sorted")
            # composition: Eclipse Wyvern shares this table, and the Dandylion family
            # must keep the rows their own triggers depend on
            ok &= check(all(c in mcids for c in (0x19FE, 0x17C5, 0x1D9B, 0x1EAA, 0x12A2)),
                        "M the Dandylion sent-to-GY family keeps its mask rows")
            ok &= check(bytes(ov[_off(GY_SWITCH_ARM):_off(GY_SWITCH_ARM) + len(GY_SWITCH_ARM_STOCK)])
                        == GY_SWITCH_ARM_STOCK,
                        f"M the ANY-LOCATION cid switch @0x{GY_SWITCH_ARM:08X} is stock -- clause 3 "
                        f"must NOT fire from a hand discard or a deck mill")
            l30 = [_u16(ov, LIST30_BASE + i * 2) for i in range(LIST30_COUNT)]
            ok &= check(DONOR_CID not in l30 and _u16(ov, 0x021C80F0) == (0x2200 | LIST30_COUNT),
                        "M list30 untouched (full, and the donor is not in it -- the mask "
                        "table is only consulted when neither list armed [sp+0x18])")
            ok &= check(0x0FD6 in l30,
                        "M Sangan 0x0FD6 -- which reaches the SAME leave arm as our donor -- "
                        "keeps its list30 row, the control that proves the arm is generic")
            ok &= check(_u16(ov, 0x021C80A2) == 0x2017 and _u16(ov, 0x021C80A6) == 0x201D,
                        "M the leave event codes are still 0x17 (battle) / 0x1D (otherwise) "
                        "-- both > 6, so both route to clause 3")
            # -- S: the code hook is NOT installed; that site must be stock
            ok &= check(bytes(ov[_off(LEAVE_BL_SITE):_off(LEAVE_BL_SITE) + 4])
                        == _bl(LEAVE_BL_SITE, LEAVE_DEFAULT_LEAF),
                        f"S the leave arm @0x{LEAVE_BL_SITE:08X} is STOCK -- PART S is unwired "
                        f"(it would hook a site shared by 316 real cards for nothing)")

            # -- T: the timing class. WITHOUT this the card is in no class at all and
            # the engine says nothing when the trigger is lost; WITH it the game
            # correctly reports "missed the timing" on a Synchro Material send.
            ok &= timinghook.verify(ov, check, rom=_rom)
            ok &= check(_u16(ov, 0x0224AF9C) == 0x2000,
                        "T `+10 == 0 -> class 0` (Sangan's mandatory shape) is still the "
                        "verdict we impersonate")
            # ⚠️ FIND SANGAN BY CID, NEVER BY ROW INDEX.  This check used to read row 40
            # directly (0x02275C04 + 40*24).  The cls2 table is a SHARED, count-neutral
            # resource: any patch that inserts a record drops a phantom and shifts every
            # row between the two, so a hardcoded index silently comes to mean a different
            # card.  darksoul's re-home did exactly that -- it dropped
            # phantom 0x0E15 (row 7) and inserted its donor at row 143, moving Sangan from
            # row 40 to row 39 -- and this assertion failed against a ROM in which Sangan's
            # record is perfectly intact.  Same lesson as otn-chain-build-verify-artifact:
            # anchor a chain precondition on a CID, never on a row index.
            SANGAN_CID = 0x0FD6
            _cls2_base = _off(0x02275C04)
            _sangan = next((i for i in range(0x2B9)
                            if struct.unpack_from("<H", ov, _cls2_base + i * 24)[0] == SANGAN_CID), None)
            ok &= check(_sangan is not None
                        and struct.unpack_from("<I", ov, _cls2_base + _sangan * 24 + 0x10)[0] == 0,
                        f"T Sangan 0x{SANGAN_CID:04X} (cls2 row {_sangan}) still has +10 == 0 "
                        f"-- the control for class 0")

            # -- P: the record's four slots, and the targets they dispatch to
            rec = _cls2_record()
            ok &= check(rec[1] == (ov5_cave.CAVE_LP_RESDISP | 1),
                        "P +04 is the resolver dispatcher (clause 2 / clause 3 by desc[+4])")
            ok &= check(rec[5] == (ov5_cave.CAVE_LP_TGTDISP | 1),
                        "P +14 is the target dispatcher (0 for clause 2 == `movs r0,#1`)")
            for addr, word, what in ((C3_RESOLVER, 0xB570, "cls2 GY-revive resolver"),
                                     (C3_CONDITION, 0xB538, "Colossal Fighter's condition"),
                                     (C3_COST_TAG, 0xB508, "the 'You can' slot4 tag"),
                                     (C3_PICKER, 0xB5F8, "the off-field target picker"),
                                     (C2_RESOLVER, 0xB5F8, "clause 2's self-SS-from-GY resolver")):
                ok &= check(_u16(ov, addr & ~1) == word,
                            f"P 0x{addr:08X} ({what}) is unmoved -- entry halfword {word:#06x}")
            # the record slots must still fall through to `movs r0,#1` when NULL, which
            # is what our +14 clause-2 arm reproduces
            ok &= check(_u16(ov, 0x0224AEA0) == 0x2001 and _u16(ov, 0x0224AE6C) == 0x2001,
                        "P the slot4/slot5 wrappers still answer 1 for a NULL slot")
            # clause 3's condition resolves its row through the same provider the picker
            # uses, so the hook has to be the only thing that moves the offset
            ok &= check(_u16(ov, PARAM_PROVIDER) == 0xB5F8,
                        f"P the param provider 0x{PARAM_PROVIDER:08X} is unmoved "
                        f"(it returns 0 for our donor, so both clause-3 consumers ask for param 0)")


        return Compiled(installs=(install,), checks=(check_fn,))


lightpulsar_effects = special_summon_self_from_hand_or_graveyard_by_banishing_light_and_dark_hand_clause_sent_to_graveyard_revive_light_or_dark_dragon

SPEC = card(0x0FB1, lightpulsar_effects())

PROPS = card_props("LIGHT", "Dragon", level=6, atk=2500, defense=1500)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_lightpulsar.nds")

DONOR_CID = 0x0FB1          # Sword Arm of Dragon -- KEEPS this cid

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
