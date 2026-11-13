"""Jet Synchron (FIRE / Machine / Tuner Monster / Level 1 / 500 / 0) on Changer Synchron 0x224C.

    If this card is sent to the GY as Synchro Material: You can add 1 "Junk" monster from your Deck to your hand. If this card is in
    your GY: You can send 1 card from your hand to the GY; Special Summon this card, but banish it when it leaves the field. You can
    only use 1 "Jet Synchron" effect per turn, and only once that turn. (See card_text.CARD_TEXT[0x224C] for the full printed text.)
"""
from __future__ import annotations

import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, RIDER_ATTACH
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from dataclasses import dataclass
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class sent_to_graveyard_as_synchro_material_add_junk_from_deck_and_in_graveyard_send_hand_card_special_summon_banish_on_leave_once_per_turn:
    """Jet Synchron (Changer Synchron 0x224C, a Tuner already in the "Synchron" set-code list): 'If this card is sent to the GY as
    Synchro Material: You can add 1 "Junk" monster from your Deck to your hand. If this card is in your GY: You can send 1 card from
    your hand to the GY; Special Summon this card, but banish it when it leaves the field. You can only use 1 "Jet Synchron" effect
    per turn.' One shared cls2 record whose +04/+0C/+10 slots are ov5 two-way dispatchers (clause 1 iff desc[+3]==0x0E && desc[+4]>6),
    two criteria rows (Deck Junk at rel 0, hand any-card at rel 1) over phantoms 0x0EAF / 0x0E4A, the GY-action registry row 48
    (0x0E64), the shared criteria-row, timing-class and summon-rider hooks (arms registered in their own modules), and a hand-send
    cost machine cloned from Plaguespreader Zombie. The cid-keyed turn log is the once-per-turn for both clauses. Original code
    embedded verbatim (the retired pre-lift rider stub is dropped)."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.asm import effect_verify
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.effects import criteria_row_hook as rowhook
        from otn_enhanced.effects import timing_class_hook as timinghook
        from otn_enhanced.effects import summon_rider_hook as riderhook
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R4, R5, R6, R7
        from otn_enhanced.effects.common import ov3_off as _off, bl as _bl, ARM9_BASE
        import ndspy.code

        DONOR_CID = 0x224C          # "Changer Synchron" -- KEEPS this cid (stays sorted / visible / obtainable)

        # ===========================================================================
        # PART A -- cls2 (the effect record)
        # ===========================================================================
        CLS2_BASE = 0x02275C04      # base of the cls2 master effect table
        CLS2_STRIDE = 24            # bytes per record
        CLS2_COUNT = 0x2B9          # 697 records (the hard count the binary search uses)

        # (+04, +08, +0C, +10, +14) before -> after.  BEFORE is Changer Synchron's stock
        # battle-position effect; AFTER is the three exemplars' shared shape.
        CLS2_BEFORE = (0x022076A5, 0x021E0501, 0x0224A115, 0x00000000, 0x02234E01)
        CLS2_AFTER = (0x02207EF5, 0x00000000, 0x021F0821, 0x021E51E5, 0x00000000)

        # ===========================================================================
        # PART B -- the criteria / populate registry
        # ===========================================================================
        CRIT_BASE = 0x022713C4      # 1388 x 12 B, sorted by the u16 cid at +0x00
        CRIT_COUNT = 0x56C          # 1388 -- the literal at CRIT_COUNT_LIT; must NOT change
        CRIT_STRIDE = 12
        CRIT_COUNT_LIT = 0x02243DF8  # the hard count the binary search 0x02243B9C reads
        CRIT_FMT = "<HHIHH"         # {cid, aux, handler, flags, extra}

        CRIT_AUX = 0x0050           # the "Junk" set code (setcode.junk_table)
        CRIT_HANDLER = 0x0223CAF5   # select from DECK -> add to HAND
        CRIT_FLAGS = 0x0002         # Monster (Junk Blader's row pins this exact value)
        CRIT_EXTRA = 0x0000         # no level / race bound

        CRIT_ROW = (DONOR_CID, CRIT_AUX, CRIT_HANDLER, CRIT_FLAGS, CRIT_EXTRA)

        # The phantom whose row is dropped to keep the insert count-neutral.
        # ⚠️ WAS 0x234A until. That is tg_warwolf's POP_PHANTOM, and
        # Warwolf runs EARLIER in apply_all_patches, so in the chain 0x234A owns no row
        # by the time this patch runs -- the chain build died on exactly that assert
        # while the single-card build (where Warwolf is absent) had passed for two days.
        # 0x0EAF is the replacement: it owns exactly ONE criteria row in BOTH the stock
        # image AND the fully-chained ROM, which is now the standard this constant is
        # chosen against.  No card_prop
        # record, exactly one criteria row, unclaimed.  Registered in check_allocations
        # under the "populate_table" pool.
        CRIT_DROP_PHANTOM = 0x0EAF

        SYNCHRON_LIST = 0x0209C968   # sorted 15 x u16, count hardcoded `movs r2,#0x0F` @0x02023E20
        SYNCHRON_COUNT = 15

        # ===========================================================================

        # ===========================================================================
        # CLAUSE 2 + CLAUSE 3
        # ===========================================================================
        # CLAUSE 2  "If this card is in your GY: You can send 1 card from your hand to
        #            the GY; Special Summon this card, but banish it when it leaves the
        #            field."
        # CLAUSE 3  "You can only use 1 'Jet Synchron' effect per turn, and only once
        #            that turn."  ONE cid-keyed turn-log stamp locks BOTH clauses.
        #
        # ARCHITECTURE A -- ONE shared cls2 record, each conflicting slot an ov5 two-way
        # dispatcher.  This is lightpulsar's structure with the roles swapped (its
        # clause 2 = our clause 2, its clause 3 = our clause 1); that card ships the
        # identical conflict in the identical slots and is in-game confirmed.
        #
        #   slot          clause 1, confirmed)  clause 2 (this block)
        #   +04 resolver  0x02207EF5  add-to-hand        0x0220731D  GY self-SS
        #   +08 filter    0                              0        (shared, no dispatcher)
        #   +0C condition 0x021F0821                     hand count + 0x021FF06D
        #   +10 cost/tag  0x021E51E5  "You can" tag      the hand-send cost machine
        #   +14 target    0                              0        (shared, no dispatcher)
        #
        # THE DISCRIMINATOR is Lightpulsar's constant, verbatim -- `desc[+3] == 0x0E &&
        # desc[+4] > 6` selects clause 1 -- and it is safe in BOTH directions, proven, not
        # assumed:
        #
        #   * clause 2 can never carry a code above 6.  Its descriptor is built by the
        #     GY-action builder 0x0224C590, which hardcodes desc[+3] = 0x0E, and the
        #     off-field offer gate 0x021ECC6C -> 0x021ECC28 then refuses it unless
        #     desc[+4] <= 6.  The gate's two escape hatches close for this donor: 0x224C
        #     is in neither the five-cid whitelist {0x131E, 0x14D7, 0x154C, 0x1E08,
        #     0x2272} nor the quick-effect list 0x0209C118, so 0x021A87BC returns speed 1.
        #     See dispatch.gy_action_offer_caps_the_event_code.
        #   * clause 1 can never carry a code at or below 6.  A class-2 descriptor with
        #     zone 0x0E reaching this record comes only from the leave / relocation path,
        #     whose two code sources are 0x021C809C (0x17 battle / 0x1D otherwise) and the
        #     relocation applier 0x021D1300 (0x1E).
        #
        # ⚠️ The handoff called this constant "actively unsafe", reasoning that
        # the event-code array 0x0229ABB4 is never cleared, so a stale Special-Summon code
        # 0x09 sitting at index 0 during a GY ignition would satisfy `> 6` and misroute
        # clause 2 into clause 1's arm.  The gate above makes that impossible: with a
        # stale code above 6 the GY effect is simply NOT OFFERED.  That residual -- the GY
        # effect being briefly unavailable -- is what Grapha and Lightpulsar already ship.
        #
        # ⚠️⚠️ THIS CLAUSE COSTS THE CARD ITS PUZZLE SAFETY.  Clause 1 is two overlay-3
        # table writes and is puzzle-safe.  Clause 2 needs an arm on the SHARED
        # criteria_row_hook, whose stub is in the ov5 cave and sits inside 0x02243B9C, the
        # row resolver every card that selects anything passes through; a puzzle loads
        # overlay 41 over ov5, so the first selection by ANY card would crash.  Accepted
        # by explicit user decision -- the same trade lightpulsar,
        # darkflare and upstart_golden_ninja already carry.
        # ===========================================================================
        C2_ZONE_GY = 0x0E           # the descriptor's zone is the DESTINATION zone
        C2_EVENT_MIN = 7            # clause 1 iff desc[+4] > 6

        C1_RESOLVER = 0x02207EF5    # add 1 card from the Deck to the hand
        C1_CONDITION = 0x021F0821   # activatable iff a Deck candidate exists
        C1_TAG_BODY = 0x021E50DD    # the costless "You can" BODY (NOT the 0x021E51E5 thunk)

        C2_RESOLVER = 0x0220731D    # the GY self-Special-Summon resolver.  68 cls2 records
                                    #   share it; its position switch 0x02207424 gives any
                                    #   unlisted cid the DEFAULT arm r4 = 2 / r6 = 1, i.e.
                                    #   "the player chooses, face-up" (decoded).
        C2_CONDITION = 0x021FF06D   # Plaguespreader Zombie's own GY-revive gate:
                                    #   0x021F0168(desc, arg) && 0x021F04FC(desc, arg).
                                    #   ⚠️ Neither half touches the criteria evaluator
                                    #   (0x021F0168 -> 0x021B945C; 0x021F04FC -> 0x021A2510
                                    #   / 0x021A2618), which is why this card's row-hook arm
                                    #   needs no synchronous probe flag.

        # --- CLAUSE 3, the shared once-per-turn ------------------------------------
        # dispatch.once_per_turn_must_stamp_at_activation: a stamp written in the RESOLVER
        # loses to the chain -- measured in-game on card.maiden_clause1, eight acceptances
        # in one chain window, because every activation queries the log before any of them
        # resolves.  So the QUERY lives in +0C and the STAMP lives in +10, and the stamp
        # fires only once the player has actually committed: for clause 1 when the "You
        # can" body returns 1 (the player said yes), for clause 2 when the cost machine
        # reaches its final phase (the card has been sent).  DECLINING burns nothing.
        TURNLOG_QUERY = 0x021A14E9  # (side, 0x0B, cid, 1) -> nonzero iff already logged
        TURNLOG_POST = 0x021D2585   # (side, cid, 1, 0)
        TURNLOG_ZONE = 0x0B

        # --- clause 2's hand-send cost machine -------------------------------------
        # A re-implementation of Plaguespreader Zombie's 0x021E9038
        # (dispatch.hand_cost_machine_0x021E9038) rather than a byte-for-byte relocation:
        # the machine opens with a per-cid switch that sets only r4 / [sp] / [sp+4], and a
        # concrete cid collapses it to constants, leaving a short body.
        #
        # We take PLAGUESPREADER's values (r4 = 0, [sp] = 0, [sp+4] = 1), not the default
        # arm's (r4 = 1), because Plaguespreader is the exemplar whose behaviour has been
        # observed.  r4 gates one `bl 0x021D26CC` in phase 2 -- an opcode-0x55 broadcast
        # over 0x0229DD14, not a cost -- and [sp] gates a 0x021D2598 call; both are
        # therefore skipped, exactly as they are for Plaguespreader.
        COST_STATE = 0x0229AAFC          # + 0x7C = the record-driven cost's phase counter
        COST_STATE_OFF = 0x7C
        COST_SHORTCIRCUIT = 0x021D2BC9   # (desc) -> nonzero: this cost is already settled
        COST_PROMPT = 0x0219A819         # (side, msg) -- open the "select a card" prompt
        COST_PROMPT_MSG = 0x1F           # the message id 0x021E9038 itself passes
        COST_ARM = 0x0224B9F1            # (side, kind, param, callback) -- arm the picker
        COST_ARM_KIND = 0x13             # ⚠️ NOT a cid.  It lands at [0x0229DD94+0x60],
                                         #   which the picker does not filter on; the filter
                                         #   keys off the ACTING DESCRIPTOR's cid instead
                                         #   (measured for lightpulsar).
                                         #   That is why this card needs a SECOND criteria
                                         #   row and an arm on the shared row hook.
        COST_CALLBACK = 0x022065F9       # the native per-zone candidate filter: it rejects
                                         #   unless zone == 0x0B (HAND) and then tail-calls
                                         #   0x02243FE0(side, acting cid, candidate index)
        COST_TAKE_PICK = 0x0224BBB1      # () -> nonzero once the player has picked
        COST_SEL_SIDE = 0x0229DD94       # + 0x78 = the acting side (bit 0)
        COST_SEL_SIDE_OFF = 0x78
        COST_SEL_INDEX = 0x0229DE14      # + 0x00 = the index the player picked
        COST_FINISH = 0x021D29E9         # (side, 2, 0) -- the machine's phase-2 tail

        # *** THE ONE SEMANTIC CHANGE. ***  Plaguespreader's machine calls 0x021C6988 at
        # 0x021E9120 -- hand -> DECK ([sp] = 0x0D), which is its printed "place 1 card
        # from your hand on top of the Deck".  Jet Synchron sends to the GY, as a COST.
        # 0x021C6DB4 takes the SAME (side, index) in r0/r1 and ignores the third argument,
        # so this is a substitution and not a re-marshalling (both disassembled).
        COST_MOVER = 0x021C6DB5          # hand -> GY, kind 1 = COST, destination 0x0E

        # The Graverobber sub-clause, reproduced VERBATIM.  It is a hard-coded per-card
        # clause riding inside the shared machine -- the grep-the-template-cards-text-too
        # pattern, the same way Zephyros's 400 damage rode into Grapha -- and it fires only
        # when the card the player discarded IS Graverobber.  Copying it keeps that one
        # interaction exactly as the engine already has it for Plaguespreader; omitting it
        # would silently change it.  ⚠️ The packed card reference it needs is computed
        # BEFORE the mover runs, because by then the card has left the hand array and the
        # index no longer identifies it -- which is the order the native uses.
        GR_CID = 0x1379                  # Graverobber
        GR_QUERY = 0x021A14B5            # (side, 0x0B, cid, ref)
        GR_POST1 = 0x021CF8D1            # (side, cid)
        GR_POST2 = 0x021CFB8D            # (side, 0x7D0, 0, cid)
        GR_AMOUNT = 0x07D0

        # --- the player struct (ram.container_for_zone_code, savestate-proven) ------
        PLAYER = 0x0229AC94
        PLAYER_STRIDE = 0x0B3C
        HAND_COUNT_OFF = 0x0C            # re-measured over four savestates x two
                                         #   sides: [+0x0C] equals the hand's live span every
                                         #   time (rom_all_patches.ml2 gives 4 and 5)
        HAND_ARRAY_OFF = 0x124

        # --- the banish rider (rider.banish_marker_attach_site) --------------------
        RIDER_SITE = 0x02268666          # the summon-event per-cid switch's DEFAULT leaf
        RIDER_NATIVE = bytes.fromhex("e089154e")   # ldrh r0,[r4,#0xe] ; ldr r6,[pc,#0x54]
        RIDER_RESUME = 0x0226866A        # the `cmp r0,r6` that consumes the replayed pair
        RIDER_R6_LITERAL = 0x000014FC    # what the displaced `ldr r6,[pc,#0x54]` loads
        RIDER_ATTACH = 0x021C479D        # (side, slot, key, kind, [sp] = param)
        RIDER_KEY = 0x1E15               # ⚠️ a MARKER CONSTANT, not a reference to Quillbolt
        RIDER_KIND = 3                   # family 1: the walker 0x021A1430 compares node@+0
                                         #   against the key directly, and rider.turn_sweeper
                                         #   frees kind 3 only for keys 0x18D9 / 0x1F6A, so a
                                         #   0x1E15 node survives every turn sweep
        RIDER_EVENT = 0x02298A28         # the summon-event handler's GLOBAL event record
        RIDER_EVENT_SIDE_OFF = 0x02
        RIDER_EVENT_SLOT_OFF = 0x04
        RIDER_EVENT_CID_OFF = 0x12

        # --- the GY-action registry (dispatch.gy_action_registry) ------------------
        # Row 48 is the LAST free phantom in the only family that can host a GY self-SS.
        # Its sibling family {chk 0x0224C55D, post 0x0224C669} has three spare rows and
        # CANNOT be used: it builds no class descriptor at all (so there are no +04/+0C/
        # +10 slots to hang an effect on) and both halves gate on the card being in the
        # HAND -- falsified by disassembling both functions.
        GYREG_BASE = 0x0228DDF8
        GYREG_STRIDE = 16
        GYREG_PHANTOM = 0x0E64
        GYREG_ZONE_GY = 0x0E
        GYREG_CHECK = 0x0224C591
        GYREG_POST = 0x0224C6C1

        # --- clause 2's criteria row (the COST's hand filter) ----------------------
        # Plaguespreader Zombie's own row 766 {0x1EA9, aux 0xFFFF, 0x0223CB19, 0x0E} with
        # the cid changed: no archetype filter, select from HAND, Monster|Spell|Trap --
        # literally "1 card in your hand", which is clause 2's printed cost.
        #
        # ⚠️ ORDER IS LOAD-BEARING.  0x02243B9C returns `leftmost row for this cid + r4`,
        # so the two rows must be ADJACENT and in the order the row-hook arm expects, and
        # rel 0 MUST stay the DECK row: dispatch.offer_check_probes_rel0_only -- the
        # offer-check probes rel 0 only, and on a HAND row 0x02243FE0's param is a
        # candidate INDEX rather than a row selector, so a hand row at rel 0 would test
        # hand slot 0 and nothing else.  A sorted insert that places a new record BEFORE
        # existing equal keys silently swaps them and still passes a "both rows present"
        # check (card.ninja_grandmaster_hanzo_clause2 paid for that), which is why the
        # insert below is explicitly AFTER same-cid rows, and why it is asserted.
        C2_CRIT_AUX = 0xFFFF
        C2_CRIT_HANDLER = 0x0223CB19     # select from HAND
        C2_CRIT_FLAGS = 0x000E           # Monster | Spell | Trap -- any card
        C2_CRIT_EXTRA = 0x0000
        C2_CRIT_ROW = (DONOR_CID, C2_CRIT_AUX, C2_CRIT_HANDLER, C2_CRIT_FLAGS, C2_CRIT_EXTRA)

        # The second count-neutral drop.  0x0E4A: no card_prop record, owns exactly ONE
        # criteria row (index 33 in the stock image), and unclaimed.  It is named by two
        # other structures -- a leave-mask row at 0x0226EC38 and a cls2 record at
        # 0x02275DB4 -- and BOTH are left alone and are unreachable, because a cid with no
        # card_prop can never be an obtainable card.  That is the same argument clause 1's
        # phantom 0x234A rests on, and the same one azure_eyes / eclipse_wyvern / maiden
        # already ship.  Chosen by ranking every unclaimed single-row phantom by how few
        # aligned-u16 mentions it has anywhere in arm9 + ov3; 0x0E4A ties for fewest.
        C2_CRIT_DROP_PHANTOM = 0x0E4A

        # The four ov5 stubs, and the slot values that point at them.  All four are
        # reached ONLY through our own cls2 record or our own cid gate.  The banish
        # rider's stub is no longer among them: it was lifted into summon_rider_hook.py
        #  (CAVE_JS_RIDER retired -> CAVE_RIDERHOOK) so a second card could
        # take an arm on the same 4-byte site.  Arm 0x224C there is ours.
        CLS2_C2 = (ov5_cave.CAVE_JS_RESDISP | 1, 0x00000000, ov5_cave.CAVE_JS_COND | 1,
                   ov5_cave.CAVE_JS_SLOT4 | 1, 0x00000000)


        # ===========================================================================
        # Helpers
        # ===========================================================================


        def _cls2_index(ov: bytearray, cid: int) -> int:
            """Index of the (single) cls2 record whose +00 cid is *cid*."""
            hits = [i for i in range(CLS2_COUNT)
                    if struct.unpack_from("<H", ov, _off(CLS2_BASE + i * CLS2_STRIDE))[0] == cid]
            assert len(hits) == 1, f"expected exactly 1 cls2 record for 0x{cid:04X}, got {hits}"
            return hits[0]


        def _cls2_slots(ov: bytearray, i: int) -> tuple:
            return struct.unpack_from("<5I", ov, _off(CLS2_BASE + i * CLS2_STRIDE) + 4)


        def _crit_rows(ov: bytearray) -> list[tuple]:
            return [struct.unpack_from(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE))
                    for i in range(CRIT_COUNT)]


        # ===========================================================================
        # PART A
        # ===========================================================================
        def apply_cls2(ov: bytearray) -> None:
            """Transplant the exemplars' action slots onto cls2[0x224C], in place."""
            i = _cls2_index(ov, DONOR_CID)
            cur = _cls2_slots(ov, i)
            if cur == CLS2_AFTER:
                print(f"A  cls2[{i}] 0x{DONOR_CID:04X}: already transplanted (idempotent)")
                return
            assert cur == CLS2_BEFORE, (
                f"A  cls2[{i}] for 0x{DONOR_CID:04X} is {[f'0x{v:08X}' for v in cur]}, expected "
                f"Changer Synchron's stock slots {[f'0x{v:08X}' for v in CLS2_BEFORE]} -- "
                f"another patch already edited this record")
            off = _off(CLS2_BASE + i * CLS2_STRIDE) + 4
            for k, v in enumerate(CLS2_AFTER):
                struct.pack_into("<I", ov, off + k * 4, v)
            print(f"A  cls2[{i}] 0x{DONOR_CID:04X} @0x{CLS2_BASE + i * CLS2_STRIDE:08X}: "
                  + " ".join(f"+{4 + k * 4:02X}=0x{v:08X}" for k, v in enumerate(CLS2_AFTER)))


        # ===========================================================================
        # PART B
        # ===========================================================================
        def apply_criteria_row(ov: bytearray) -> None:
            """Count-neutral insert of the donor's "1 Junk monster from your Deck" row.

            The insertion point and the phantom are located BY CID at apply time, never by
            a hardcoded index: several shipped patches insert into this same table and
            shift everything after their edits.
            """
            rows = _crit_rows(ov)
            mine = [r for r in rows if r[0] == DONOR_CID]
            if mine == [CRIT_ROW]:
                print(f"B  criteria row for 0x{DONOR_CID:04X}: already inserted (idempotent)")
                return

            cids = [r[0] for r in rows]
            assert all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)), \
                "B  the criteria registry is not sorted on entry -- an earlier patch broke the binary search"
            assert not mine, f"B  cid 0x{DONOR_CID:04X} already owns a criteria row: {mine}"

            drop = [i for i, c in enumerate(cids) if c == CRIT_DROP_PHANTOM]
            assert len(drop) == 1, (
                f"B  phantom 0x{CRIT_DROP_PHANTOM:04X} owns {len(drop)} row(s), need exactly 1 -- "
                f"another patch probably took it")

            kept = [r for i, r in enumerate(rows) if i != drop[0]]
            pos = sum(1 for r in kept if r[0] < DONOR_CID)
            new = kept[:pos] + [CRIT_ROW] + kept[pos:]

            assert len(new) == CRIT_COUNT, f"B  insert was not count-neutral ({len(new)} rows)"
            ncids = [r[0] for r in new]
            assert all(ncids[i] <= ncids[i + 1] for i in range(len(ncids) - 1)), \
                "B  the criteria registry lost its sort order"

            for i, r in enumerate(new):
                struct.pack_into(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE), *r)
            print(f"B  criteria row: {{0x{DONOR_CID:04X}, aux 0x{CRIT_AUX:04X}, "
                  f"0x{CRIT_HANDLER:08X}, flags 0x{CRIT_FLAGS:04X}, extra 0x{CRIT_EXTRA:04X}}} "
                  f"inserted at [{pos}], dropped phantom 0x{CRIT_DROP_PHANTOM:04X} at [{drop[0]}]")

            lit = struct.unpack_from("<I", ov, _off(CRIT_COUNT_LIT))[0]
            assert lit == CRIT_COUNT, f"B  registry count literal changed to 0x{lit:X}"



        # ===========================================================================
        # The clause-2 ov5 stubs
        # ===========================================================================
        # SLOT ABI, confirmed by disassembly in lightpulsar: every slot wrapper
        # calls with **r0 = the DESCRIPTOR, r1 = the invoker's arg**; r2/r3 are free
        # scratch.  All the dispatch targets used here are function ENTRIES, so a
        # register-preserving `bx` is legal -- dispatch.midfunction_tail_needs_prologue_
        # frame forbids jumping into a mid-function ARM, which is what froze the game on
        #, not a tail jump as such.
        #
        # DESCRIPTOR FIELDS (dispatch.cls_table_selector):
        #   +0x00 u16 cid   +0x02 u8 side   +0x03 u8 zone   +0x04 u8 event code
        #   +0x05 u8 record class          +0x12 u16 pass index
        # ===========================================================================
        def _stub_resdisp(base: int) -> bytes:
            """+04 RESOLVER: clause 1's add-to-hand, or clause 2's GY self-Special-Summon.

            The clause-2 arm also ARMS THE RIDER: it sets the one-shot byte
            CAVE_JS_ARM before tail-jumping into the summon, and the SHARED hook
            summon_rider_hook (CAVE_RIDERHOOK, arm 0x224C) consumes it when the summon
            event fires.  The byte is deliberately NOT cleared here --
            the commit 0x0226925C can finish after this resolver has returned, which is
            exactly the timing window that killed card.upstart_golden_ninja's first STAGE
            latch, so only the consumer may clear it.
            """
            b = EffectBuilder()
            b.insn("LDRB", "R2, [R0, #0x3]")
            b.insn("CMP", f"R2, #0x{C2_ZONE_GY:X}")
            b.insn("BNE", "clause2")
            b.insn("LDRB", "R2, [R0, #0x4]")
            b.insn("CMP", f"R2, #0x{C2_EVENT_MIN - 1:X}")
            b.insn("BLE", "clause2")
            b.ldr_const(3, C1_RESOLVER)
            b.insn("BX", "R3")
            b.label("clause2")
            b.ldr_const(2, ov5_cave.CAVE_JS_ARM)
            b.insn("MOV", "R3, #0x1")
            b.insn("STRB", "R3, [R2, #0x0]")
            b.ldr_const(3, C2_RESOLVER)
            b.insn("BX", "R3")
            return b.assemble(base, pad="nop")


        def _stub_cond(base: int) -> bytes:
            """+0C CONDITION: CLAUSE 3 for both clauses, then each clause's own gate.

            The turn-log query is FIRST and shared, because clause 3 is one limit across
            both clauses and the log is keyed on the cid alone.  Then:

              clause 1 -> 0x021F0821, "a legal Deck candidate exists" (unchanged from the
                          shipped, in-game-confirmed build apart from the clause-3 query)
              clause 2 -> the hand must not be empty, then Plaguespreader's own GY-revive
                          gate 0x021FF06D

            The hand test reads the COUNT at player+0x0C directly rather than probing a
            criteria row.  That is deliberate: 0x02243FE0's param is a candidate INDEX on
            a HAND row, so a probe would only ever test hand slot 0 -- the bug that made
            card.upstart_golden_ninja offer an empty, inescapable picker (its TEST 3).
            Reading the count cannot have that failure mode, and it is the right test for
            a printed cost of "1 card" with no filter.

            ⚠️ WATCH IN-GAME (oracle items 4 and 5).  dispatch.slot3_reevaluated_after_cost
            says this slot can run again mid-activation.  If it does so AFTER +10 has
            stamped the turn log, the query here would return "already used" and abort the
            card's own resolution.  card.maiden_clause1 ships the identical query/stamp
            split and is in-game confirmed, but on a cls3 record, not a cls2 one -- so this
            is a PRECEDENT, not a proof.  The distinguishable symptom is "the effect is
            offered, the prompt is accepted, and then nothing happens".
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", f"R1, #0x{TURNLOG_ZONE:X}")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call("turnlog_query", R0, R1, R2, 1, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "refuse")
            b.insn("LDRB", "R0, [R4, #0x3]")
            b.insn("CMP", f"R0, #0x{C2_ZONE_GY:X}")
            b.insn("BNE", "c2")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("CMP", f"R0, #0x{C2_EVENT_MIN - 1:X}")
            b.insn("BLE", "c2")
            b.call_addr(C1_CONDITION, R4, R5, via=R6)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("c2")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", "R1, #0x1")
            b.insn("AND", "R0, R1")
            b.ldr_const(1, PLAYER + HAND_COUNT_OFF)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "hs0")
            b.ldr_const(0, PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("hs0")
            b.insn("LDR", "R0, [R1, #0x0]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "refuse")
            b.call_addr(C2_CONDITION, R4, R5, via=R6)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("refuse")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        def _stub_slot4(base: int) -> bytes:
            """+10 ACTIVATION PROCEDURE, and where CLAUSE 3 is stamped.

            clause 1 -> the costless "You can" BODY 0x021E50DC (NOT the thunk 0x021E51E5),
                        then the turn-log stamp, and ONLY when the body returned 1.
                        Decoded in maiden_eyes_of_blue: 0x021E50DC runs on its own
                        phase counter [0x0229AAFC+0x7C] with phase 0 = run slot3 then open
                        the Yes/No dialog, phase 1 = read the answer, and the non-zero arm
                        (the player accepted) is the ONLY one that returns 1.  So DECLINING
                        the prompt does not burn the once-per-turn -- the correct reading of
                        "you can".
            clause 2 -> CAVE_JS_COST, which stamps for itself when its final phase runs.

            ⚠️ THIS SLOT IS ALSO THE TIMING-CLASS LITERAL.  timing.class_is_the_slot4_
            literal: the WHEN-vs-IF classifier 0x0224AF7C reads +0x10 RAW and never calls
            it, and an unrecognised value leaves the card in NO timing class -- the trigger
            then evaporates silently (it cost lightpulsar a withdraw-and-restore).
            A cave address is exactly such a value.  That is why this card MUST register an
            arm on the SHARED timing_class_hook, which makes the classifier see clause 1's
            original 0x021E51E5 in clause 1's window.  ⚠️ 0x0224AF7C returns 0 at once for
            record classes 0 and 3, so maiden_eyes_of_blue could do this WITHOUT a
            hook -- its record is cls3.  Ours is cls2 and cannot.
            """
            b = EffectBuilder()
            b.insn("LDRB", "R2, [R0, #0x3]")
            b.insn("CMP", f"R2, #0x{C2_ZONE_GY:X}")
            b.insn("BNE", "c2cost")
            b.insn("LDRB", "R2, [R0, #0x4]")
            b.insn("CMP", f"R2, #0x{C2_EVENT_MIN - 1:X}")
            b.insn("BLE", "c2cost")
            b.insn("PUSH", "{R4, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(C1_TAG_BODY, via=R6)
            b.insn("CMP", "R0, #0x1")
            b.insn("BNE", "out")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, 1, via=R6)
            b.insn("MOV", "R0, #0x1")
            b.label("out")
            b.insn("POP", "{R4, R6, PC}")
            b.label("c2cost")
            b.ldr_const(2, ov5_cave.CAVE_JS_COST | 1)
            b.insn("BX", "R2")
            return b.assemble(base, pad="nop")


        def _stub_cost(base: int) -> bytes:
            """Clause 2's cost: "send 1 card from your hand to the GY".

            Plaguespreader Zombie's machine 0x021E9038, re-implemented rather than
            relocated, with ONE semantic change (the mover) and the per-cid switch
            collapsed to Plaguespreader's own constants.  See the COST_* block above for
            why those constants and not the default arm's.

            Phase protocol, copied from the native:
              short-circuit  0x021D2BC8(desc) nonzero -> return 1 (already settled)
              phase 0        open the prompt, ARM the picker, bump the state, return 0
              phase 1        read the answer (0 = cancelled: UNbump and return 0), then
                             compute the packed card reference, PAY, and run the
                             Graverobber sub-clause; bump and return 0
              phase 2        finish, STAMP CLAUSE 3, return 1
              anything else  return 0

            ⚠️ THE REFERENCE IS COMPUTED BEFORE THE MOVER RUNS.  After 0x021C6DB4 the card
            has left the hand array and the picked index no longer identifies it.  The
            native does the same thing in the same order (0x021E90F0..0x021E9108 before
            0x021E9120); an earlier draft of this stub had the two the other way round and
            the disassembly review caught it.

            ⚠️ Returning 1 is what the caller reads as "the cost is paid", so the clause-3
            stamp sits in phase 2 and nowhere else: a cancel at phase 1 never reaches it.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.call_addr(COST_SHORTCIRCUIT, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "phases")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("phases")
            b.ldr_const(6, COST_STATE)
            b.insn("LDR", f"R0, [R6, #0x{COST_STATE_OFF:X}]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ph0")
            b.insn("CMP", "R0, #0x1")
            b.insn("BEQ", "ph1")
            b.insn("CMP", "R0, #0x2")
            b.insn("BEQ", "ph2")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("ph0")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.call_addr(COST_PROMPT, R0, COST_PROMPT_MSG, via=R6)
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.call_addr(COST_ARM, R0, COST_ARM_KIND, 0, COST_CALLBACK, via=R6)
            b.insn("B", "bump")
            b.label("ph1")
            b.call_addr(COST_TAKE_PICK, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "unbump")
            b.ldr_const(6, COST_SEL_SIDE)
            b.insn("LDR", f"R4, [R6, #0x{COST_SEL_SIDE_OFF:X}]")
            b.ldr_const(6, COST_SEL_INDEX)
            b.insn("LDR", "R7, [R6, #0x0]")
            b.insn("MOV", "R0, #0x1")
            b.insn("AND", "R0, R4")
            b.ldr_const(1, PLAYER + HAND_ARRAY_OFF)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "gr0")
            b.ldr_const(0, PLAYER_STRIDE)
            b.insn("ADD", "R1, R1, R0")
            b.label("gr0")
            b.insn("LSL", "R0, R7, #0x2")
            b.insn("LDR", "R0, [R1, R0]")
            b.insn("LSL", "R1, R0, #0x11")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x1")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("ADD", "R6, R0, R1")
            b.insn("PUSH", "{R6}")
            b.call_addr(COST_MOVER, R4, R7, via=R6)
            b.insn("POP", "{R7}")
            b.call_addr(GR_QUERY, R4, TURNLOG_ZONE, GR_CID, R7, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "bump")
            b.call_addr(GR_POST1, R4, GR_CID, via=R6)
            b.call_addr(GR_POST2, R4, GR_AMOUNT, 0, GR_CID, via=R6)
            b.insn("B", "bump")
            b.label("ph2")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.call_addr(COST_FINISH, R0, 2, 0, via=R6)
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.turnlog_post(R0, R1, 1, via=R6)
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("bump")
            b.ldr_const(6, COST_STATE)
            b.insn("LDR", f"R0, [R6, #0x{COST_STATE_OFF:X}]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", f"R0, [R6, #0x{COST_STATE_OFF:X}]")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("unbump")
            b.ldr_const(6, COST_STATE)
            b.insn("LDR", f"R0, [R6, #0x{COST_STATE_OFF:X}]")
            b.insn("SUB", "R0, #0x1")
            b.insn("STR", f"R0, [R6, #0x{COST_STATE_OFF:X}]")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        # The reserves each stub is installed under.  install_clause2 asserts every blob
        # fits, and check_allocations independently asserts the slots do not overlap.
        C2_RESERVES = {
            "CAVE_JS_RESDISP": 0x40,
            "CAVE_JS_COND": 0x80,
            "CAVE_JS_SLOT4": 0x40,
            "CAVE_JS_COST": 0x140,
        }




        # ===========================================================================
        # PART E -- the cls2 record's three conflicting slots become dispatchers
        # ===========================================================================
        def apply_cls2_clause2(ov: bytearray) -> None:
            """Retarget +04 / +0C / +10 at the ov5 dispatchers. Runs AFTER apply_cls2."""
            i = _cls2_index(ov, DONOR_CID)
            cur = _cls2_slots(ov, i)
            if cur == CLS2_C2:
                print(f"E  cls2[{i}] 0x{DONOR_CID:04X}: already dispatched (idempotent)")
                return
            assert cur == CLS2_AFTER, (
                f"E  cls2[{i}] is {[f'0x{v:08X}' for v in cur]}, expected clause 1's slots "
                f"{[f'0x{v:08X}' for v in CLS2_AFTER]} -- run apply_cls2 first")
            off = _off(CLS2_BASE + i * CLS2_STRIDE) + 4
            for k, v in enumerate(CLS2_C2):
                struct.pack_into("<I", ov, off + k * 4, v)
            print(f"E  cls2[{i}] 0x{DONOR_CID:04X}: +04 -> 0x{CLS2_C2[0]:08X} (resolver disp), "
                  f"+0C -> 0x{CLS2_C2[2]:08X} (condition disp), +10 -> 0x{CLS2_C2[3]:08X} (slot4 disp)")


        # ===========================================================================
        # PART F -- clause 2's criteria row, immediately AFTER clause 1's
        # ===========================================================================
        def apply_criteria_row_c2(ov: bytearray) -> None:
            """Count-neutral insert of "any 1 card in your hand", at rel 1.

            ⚠️ The insert is AFTER same-cid rows on purpose: the Deck row must stay at
            rel 0 (dispatch.offer_check_probes_rel0_only), and a sorted insert of the
            natural `sum(k < new)` form would put the hand row FIRST and still pass a
            "both rows present" check.  The order is asserted, not assumed.
            """
            rows = _crit_rows(ov)
            mine = [r for r in rows if r[0] == DONOR_CID]
            if mine == [CRIT_ROW, C2_CRIT_ROW]:
                print(f"F  clause-2 criteria row for 0x{DONOR_CID:04X}: already inserted (idempotent)")
                return
            assert mine == [CRIT_ROW], (
                f"F  cid 0x{DONOR_CID:04X} owns {mine}, expected exactly clause 1's row -- "
                f"run apply_criteria_row first")

            cids = [r[0] for r in rows]
            assert all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)), \
                "F  the criteria registry is not sorted on entry"

            drop = [i for i, c in enumerate(cids) if c == C2_CRIT_DROP_PHANTOM]
            assert len(drop) == 1, (
                f"F  phantom 0x{C2_CRIT_DROP_PHANTOM:04X} owns {len(drop)} row(s), need exactly 1 "
                f"-- another patch probably took it")

            kept = [r for i, r in enumerate(rows) if i != drop[0]]
            pos = sum(1 for r in kept if r[0] <= DONOR_CID)      # AFTER same-cid rows
            new = kept[:pos] + [C2_CRIT_ROW] + kept[pos:]

            assert len(new) == CRIT_COUNT, f"F  insert was not count-neutral ({len(new)} rows)"
            ncids = [r[0] for r in new]
            assert all(ncids[i] <= ncids[i + 1] for i in range(len(ncids) - 1)), \
                "F  the criteria registry lost its sort order"
            block = [r for r in new if r[0] == DONOR_CID]
            assert block == [CRIT_ROW, C2_CRIT_ROW], (
                f"F  the donor's rows are in the WRONG ORDER: {block}. rel 0 must be the DECK "
                f"row (handler 0x{CRIT_HANDLER:08X}), rel 1 the HAND row "
                f"(handler 0x{C2_CRIT_HANDLER:08X})")

            for i, r in enumerate(new):
                struct.pack_into(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE), *r)
            print(f"F  clause-2 criteria row {{0x{DONOR_CID:04X}, aux 0x{C2_CRIT_AUX:04X}, "
                  f"0x{C2_CRIT_HANDLER:08X}, flags 0x{C2_CRIT_FLAGS:04X}}} inserted at [{pos}] "
                  f"(rel 1, after the Deck row), dropped phantom "
                  f"0x{C2_CRIT_DROP_PHANTOM:04X} at [{drop[0]}]")

            lit = struct.unpack_from("<I", ov, _off(CRIT_COUNT_LIT))[0]
            assert lit == CRIT_COUNT, f"F  registry count literal changed to 0x{lit:X}"


        # ===========================================================================
        # PART G -- the GY-action registry row: what makes clause 2 offerable at all
        # ===========================================================================
        def apply_gy_registry(ov: bytearray) -> None:
            """Take row 48, the LAST free phantom in the Grapha family."""
            rows = [struct.unpack_from("<4I", ov, _off(GYREG_BASE + i * GYREG_STRIDE))
                    for i in range(60)]
            mine = [i for i, r in enumerate(rows) if r[0] == DONOR_CID]
            if mine:
                assert len(mine) == 1 and rows[mine[0]][1:] == (GYREG_ZONE_GY, GYREG_CHECK, GYREG_POST)
                print(f"G  GY-action registry row [{mine[0]}]: already claimed (idempotent)")
                return
            cand = [i for i, r in enumerate(rows) if r[0] == GYREG_PHANTOM]
            assert len(cand) == 1, (
                f"G  phantom 0x{GYREG_PHANTOM:04X} appears in {len(cand)} rows, need exactly 1 "
                f"-- another patch probably took it")
            idx = cand[0]
            assert rows[idx][1:] == (GYREG_ZONE_GY, GYREG_CHECK, GYREG_POST), (
                f"G  row [{idx}] is {[f'0x{v:08X}' for v in rows[idx]]}, expected the Grapha "
                f"family (zone 0x{GYREG_ZONE_GY:02X}, chk 0x{GYREG_CHECK:08X}, "
                f"post 0x{GYREG_POST:08X})")
            struct.pack_into("<I", ov, _off(GYREG_BASE + idx * GYREG_STRIDE), DONOR_CID)
            print(f"G  GY-action registry row [{idx}] @0x{GYREG_BASE + idx * GYREG_STRIDE:08X}: "
                  f"phantom 0x{GYREG_PHANTOM:04X} -> 0x{DONOR_CID:04X} "
                  f"(zone 0x{GYREG_ZONE_GY:02X}, chk 0x{GYREG_CHECK:08X})")


        # ===========================================================================
        # PART R -- the rider hook, on the summon-event switch's default leaf
        # ===========================================================================
        def apply_rider_hook(ov: bytearray) -> None:
            """Install the SHARED summon-rider hook (ARM 0x224C is ours).

            LIFTED 2026-09-07 into summon_rider_hook.py.  The site 0x02268666 is a single
            4-byte BL, so it can serve only one stub; Jet Warrior needed a second arm and
            re-pointing the hook would have broken this card, which is in-game confirmed.
            CAVE_JS_RIDER is retired; the stub now lives at CAVE_RIDERHOOK with a cid
            register.  Behaviour for cid 0x224C is unchanged -- proved by executing both
            blobs in scratch/rider_hook_equiv.py.
            """
            riderhook.apply(ov)


        # ===========================================================================

        def install(rom, view):
            ov = view.buf
            apply_cls2(ov)              # PART A -- clause 1's action slots
            apply_criteria_row(ov)      # PART B -- clause 1's Deck row, at rel 0
            apply_cls2_clause2(ov)      # PART E -- the three slots become dispatchers
            apply_criteria_row_c2(ov)   # PART F -- the Hand row, at rel 1 (MUST follow B)
            apply_gy_registry(ov)       # PART G -- makes clause 2 offerable from the GY
            apply_rider_hook(ov)        # PART R -- "banish it when it leaves the field"
            rowhook.apply(ov)           # PART H -- the SHARED 4-byte criteria-row hook
            timinghook.apply(ov)        # PART T -- the SHARED 4-byte timing-class hook
            rowhook.install(rom)        # the shared stubs in ov5 (ARM_JS is ours)
            timinghook.install(rom)     # (ARM_JET is ours)
            riderhook.install(rom)      # (arm 0x224C is ours; also writes every arm's one-shot byte, CLEAR)

        def check_fn(c, rom, view):
            ov = bytearray(view.buf)
            _romobj = rom
            ok = True

            def check(cond: bool, label: str) -> bool:
                c.ok(bool(cond), label)
                return bool(cond)

            # --- A: the cls2 record --------------------------------------------------
            cids = [struct.unpack_from("<H", ov, _off(CLS2_BASE + i * CLS2_STRIDE))[0]
                    for i in range(CLS2_COUNT)]
            check(cids.count(DONOR_CID) == 1,
                  f"A cls2 holds exactly one record for 0x{DONOR_CID:04X} "
                  f"(got {cids.count(DONOR_CID)}) -- a second one would shadow it via "
                  f"find_event_handler's leftmost-record rule")
            check(all(cids[i] <= cids[i + 1] for i in range(CLS2_COUNT - 1)),
                  "A cls2 is still sorted")
            if cids.count(DONOR_CID) == 1:
                i = cids.index(DONOR_CID)
                slots = _cls2_slots(ov, i)
                check(slots == CLS2_C2,
                      f"A/E cls2[{i}] slots are the two-clause dispatchers "
                      f"({' '.join(f'{v:08X}' for v in slots)})")
                check(slots[1] == 0 and slots[4] == 0,
                      "A/E +08 and +14 stay 0 -- both clauses want the engine's own "
                      "null-slot behaviour, so neither needs a dispatcher")
                check(slots[3] == ov5_cave.CAVE_JS_SLOT4 | 1,
                      "A/E +10 is the slot4 DISPATCHER -- which is exactly why PART T is "
                      "MANDATORY: the classifier 0x0224AF7C reads this literal RAW, and an "
                      "unrecognised value leaves the card in NO timing class at all")

            # --- B: the criteria row -------------------------------------------------
            rows = _crit_rows(ov)
            rcids = [r[0] for r in rows]
            check(len(rows) == CRIT_COUNT, f"B the registry still has {CRIT_COUNT} rows")
            check(all(rcids[i] <= rcids[i + 1] for i in range(len(rcids) - 1)),
                  "B the registry is still sorted (the binary search depends on it)")
            check(rcids.count(DONOR_CID) == 2,
                  f"B/F exactly TWO criteria rows for 0x{DONOR_CID:04X} -- clause 1's Deck row "
                  f"at rel 0 and clause 2's Hand row at rel 1 (got {rcids.count(DONOR_CID)})")
            check(CRIT_DROP_PHANTOM not in rcids,
                  f"B phantom 0x{CRIT_DROP_PHANTOM:04X} fully dropped (count stayed neutral)")
            check(C2_CRIT_DROP_PHANTOM not in rcids,
                  f"F phantom 0x{C2_CRIT_DROP_PHANTOM:04X} fully dropped (count stayed neutral)")
            if rcids.count(DONOR_CID) == 2:
                i0 = rcids.index(DONOR_CID)
                block = rows[i0:i0 + 2]
                check(block == [CRIT_ROW, C2_CRIT_ROW],
                      "B/F the donor's two rows are ADJACENT and IN CLAUSE ORDER: rel 0 the "
                      f"DECK row (0x{CRIT_HANDLER:08X}, aux 0x{CRIT_AUX:04X} = Junk), rel 1 the "
                      f"HAND row (0x{C2_CRIT_HANDLER:08X}, aux 0x{C2_CRIT_AUX:04X} = any card)")
                check(block[0][4] == 0x0000,
                      "B extra = 0 -- no level bound, which is what the printed search has")
            lit = struct.unpack_from("<I", ov, _off(CRIT_COUNT_LIT))[0]
            check(lit == CRIT_COUNT,
                  f"B the count literal @0x{CRIT_COUNT_LIT:08X} is still 0x{CRIT_COUNT:X}")


            # --- G: the GY-action registry row (without it clause 2 is never offered) -
            gyrows = [struct.unpack_from("<4I", ov, _off(GYREG_BASE + i * GYREG_STRIDE))
                      for i in range(60)]
            gcids = [r[0] for r in gyrows]
            check(gcids.count(DONOR_CID) == 1,
                  f"G exactly one GY-action registry row for 0x{DONOR_CID:04X}")
            check(GYREG_PHANTOM not in gcids,
                  f"G phantom 0x{GYREG_PHANTOM:04X} fully consumed (row count unchanged)")
            if gcids.count(DONOR_CID) == 1:
                gr = gyrows[gcids.index(DONOR_CID)]
                check(gr[1:] == (GYREG_ZONE_GY, GYREG_CHECK, GYREG_POST),
                      f"G the row is the Grapha family: zone 0x{GYREG_ZONE_GY:02X}, "
                      f"chk 0x{GYREG_CHECK:08X}, post 0x{GYREG_POST:08X}")

            # --- R: the rider hook, now the SHARED module (arm 0x224C is ours) -------
            riderhook.verify(_romobj, ov, check)
            check(any(cid == DONOR_CID for cid, *_ in riderhook.ARMS),
                  f"R 0x{DONOR_CID:04X} is a registered arm on the shared summon-rider hook")
            check(struct.unpack_from("<H", ov, _off(0x02268660))[0] == 0x2303,
                  "R the engine's own shared attach @0x02268660 is unmodified (`movs r3,#3`)")
            check(struct.unpack_from("<H", ov, _off(0x022680A8))[0] == 0x8A62,
                  "R the summon-event switch still reads its cid from [r4,#0x12] "
                  "(the field our stub reads too)")

            # --- the two SHARED hooks, each a single 4-byte site --------------------
            ok_rh = rowhook.verify(ov, check, rom=_romobj)
            ok_th = timinghook.verify(ov, check, rom=_romobj)
            check(any(cid == DONOR_CID for cid, *_ in rowhook.ARMS),
                  f"H 0x{DONOR_CID:04X} is a registered arm on the shared criteria-row hook")
            check(any(cid == DONOR_CID for cid, *_ in timinghook.ARMS),
                  f"T 0x{DONOR_CID:04X} is a registered arm on the shared timing-class hook")

            # --- P: every ov5 blob is actually present ------------------------------
            for name, fn in (("CAVE_JS_RESDISP", _stub_resdisp), ("CAVE_JS_COND", _stub_cond),
                             ("CAVE_JS_SLOT4", _stub_slot4), ("CAVE_JS_COST", _stub_cost)):
                addr = getattr(ov5_cave, name)
                blob = fn(addr)
                check(ov5_cave.read_cave(_romobj, addr, len(blob)) == blob,
                      f"P {name} is present in ov5 @0x{addr:08X} ({len(blob)} B)")

            # --- the primitives the stubs call, pinned so a drift is caught here ----
            check(struct.unpack_from("<H", ov, _off(0x021C6DB4))[0] == 0xB51C,
                  "P 0x021C6DB4 (hand->GY as a COST) still has its own prologue")
            check(struct.unpack_from("<H", ov, _off(0x021E9038))[0] == 0xB5FE,
                  "P Plaguespreader's cost machine 0x021E9038 -- the template this clone "
                  "reproduces -- is UNMODIFIED (we cloned it, we did not edit it)")

            # --- the donor's environment, which this patch DEPENDS on and never writes -
            # It is already a "Synchron" (set code 0x4C) in ARM9, so Tuning / Junk Speeder
            # reach it with no table edit.  Read from the ROM, not asserted from memory.
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
            syn = [struct.unpack_from("<H", bytes(sec.data), SYNCHRON_LIST - ARM9_BASE + 2 * i)[0]
                   for i in range(SYNCHRON_COUNT)]
            check(DONOR_CID in syn,
                  f"D 0x{DONOR_CID:04X} is still a member of the ARM9 Synchron set-code list "
                  f"@0x0209C968 (no edit needed, none made)")




        stubs = tuple((addr, fn(addr), what) for addr, fn, what in (
            (ov5_cave.CAVE_JS_RESDISP, _stub_resdisp, "+04 resolver dispatcher"),
            (ov5_cave.CAVE_JS_COND, _stub_cond, "+0C condition dispatcher (clause 3's query)"),
            (ov5_cave.CAVE_JS_SLOT4, _stub_slot4, "+10 slot4 dispatcher (clause 3's stamp)"),
            (ov5_cave.CAVE_JS_COST, _stub_cost, "the hand-send cost machine")))
        for addr, blob, _w in stubs:
            effect_verify.assert_thumb1_only(blob, addr)     # ARMv5TE = Thumb-1 ONLY
        return Compiled(stubs, installs=(install,), checks=(check_fn,))


jet_synchron_effects = sent_to_graveyard_as_synchro_material_add_junk_from_deck_and_in_graveyard_send_hand_card_special_summon_banish_on_leave_once_per_turn

SPEC = card(0x224C, jet_synchron_effects())

PROPS = card_props("FIRE", "Machine", level=1, atk=500, defense=0, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_jet_synchron.nds")

# Names the KB proofs (jet_warrior, allocation ledger) read.
DONOR_CID = 0x224C                      # Changer Synchron
CRIT_DROP_PHANTOM = 0x0EAF              # clause 1's count-neutral criteria-row drop

if __name__ == "__main__":
    if "--verify" in sys.argv:
        raise SystemExit(0 if verify() else 1)
    main(write_text="--text" in sys.argv)
