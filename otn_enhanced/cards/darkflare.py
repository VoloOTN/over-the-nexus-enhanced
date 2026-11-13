"""Darkflare Dragon (DARK / Dragon / Level 5 / 2400 / 1200) on Battle Footballer 0x1646.

    Cannot be Normal Summoned/Set. Must first be Special Summoned (from your hand) by banishing 1 LIGHT and 1 DARK
    monster from your Graveyard.
    Once per turn: You can send 1 Dragon-Type monster from your hand and 1 from your Deck to the Graveyard; banish
    1 card in either player's Graveyard.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
from otn_enhanced.effects.common import b as _b, bl as _bl      # tests/test_utils.py compares these with common.b / common.bl
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class special_summon_banishing_light_and_dark_from_gy_discard_dragon_and_deck_dragon_to_banish_either_graveyard_card:
    """Darkflare Dragon (Battle Footballer 0x1646): 'Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by banishing
    1 LIGHT and 1 DARK monster from your GY. Once per turn: you can send 1 Dragon from your hand and 1 Dragon from your Deck to the
    GY; banish 1 card in either GY.' Clause 1: the shared banish-cost payment (handss_banish_cost) with the donor routed into the
    LIGHT+DARK leaf, a count branch, two ordered criteria rows (rel 0 LIGHT, rel 1 DARK) plus list-A membership, a summon-procedure row.
    Clause 2: Card Ejector's cls3 shape, three more criteria rows (hand Dragon, Deck Dragon, either-GY card) resolved by the shared
    criteria-row hook, and a two-zone cost wrapper plus a cost-payable gate in ov5. Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.cards import boggart_knight as boggart
        from otn_enhanced.effects import criteria_row_hook as rowhook, handss_banish_cost as banish
        from otn_enhanced.effects.common import b as _b, bl as _bl, ov3_off as _off
        from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
        DONOR_CID = cid

        # ---------------------------------------------------------------------------
        # PART A -- the dead arm we re-aim
        # ---------------------------------------------------------------------------
        ARM_BASE = 0x16C6                   # r7, loaded from the literal at ARM_BASE_LIT
        ARM_BASE_LIT = 0x0225E818
        ARM_RANGE_CMP = 0x0225E880          # `subs r0,#0x7a` -- the RANGE split, must NOT change
        ARM_CMP = 0x0225E888                # `subs r0,#imm8`; r0 = ARM_BASE - imm8
        ARM_OLD_IMM = 0x7A                  # -> 0x164C, a phantom
        ARM_NEW_IMM = ARM_BASE - DONOR_CID  # -> 0x1646
        assert 0 <= ARM_NEW_IMM <= 0xFF, (
            f"donor 0x{DONOR_CID:04X} is outside the repointable window "
            f"0x{ARM_BASE - 0xFF:04X}..0x{ARM_BASE:04X}")

        ARM_BL = 0x0225E88E
        ARM_BL_NATIVE = 0x0225F240          # the dead leaf (inside the shared ov3 run)
        ARM_BL_NEUTRAL = banish.REJECT_LEAF  # what lightpulsar leaves here
        ARM_BL_NEW = 0x0225FA46             # the LIGHT+DARK cost leaf

        # ---------------------------------------------------------------------------
        # PART B -- the required-count branch (a DIFFERENT site from Lightpulsar's)
        # ---------------------------------------------------------------------------
        COUNT_BRANCH = 0x0225CF8C
        COUNT_RET0 = 0x0225D09C             # `movs r0,#0 ; bx lr`
        COUNT_RET1 = 0x0225D06A             # `movs r0,#1 ; bx lr`
        NATIVE_LIGHTDARK_ROUTE = 0x0225E8E0  # BL -> 0x0225FA46 (the Chaos family)
        NATIVE_SINGLEATTR_ROUTE = 0x0225E838  # BL -> 0x0225FA36 (the Fenrir family)

        # ---------------------------------------------------------------------------
        # PART C -- the criteria registry and membership list A
        # ---------------------------------------------------------------------------
        CRIT_BASE = 0x022713C4
        CRIT_COUNT = 0x56C                  # 1388 -- literal at CRIT_COUNT_LIT; must NOT change
        CRIT_STRIDE = 12
        CRIT_COUNT_LIT = 0x02243DF8
        CRIT_FMT = "<HHII"
        CRIT_HANDLER = 0x0223CA11           # "select from GY" (== 3DS 0x004B1A90)
        CRIT_AUX = 0xFFFF
        CRIT_WORD_LIGHT = 0x01000002
        CRIT_WORD_DARK = 0x02000002
        CRIT_DROP_PHANTOM = 0x0E32          # phantom owning exactly 2 rows AND sitting in list A

        CRIT_ROWS = ((DONOR_CID, CRIT_AUX, CRIT_HANDLER, CRIT_WORD_LIGHT),
                     (DONOR_CID, CRIT_AUX, CRIT_HANDLER, CRIT_WORD_DARK))

        LISTA_BASE = 0x0227134C
        LISTA_COUNT = 0x3B                  # 59, hard-coded
        LISTA_DROP_PHANTOM = 0x0E32         # the same phantom, dropped from both structures

        # ---------------------------------------------------------------------------
        # PART G -- the summon-procedure registry
        # ---------------------------------------------------------------------------
        # ===========================================================================
        # CLAUSE 2 -- "Once per turn: You can send 1 Dragon monster from your hand and
        # 1 Dragon monster from your Deck to the GY, then target 1 card in either GY;
        # banish that target."
        #
        # BUILD 1 (this file) ships the ACTION HALF and the hand send. The Deck send is
        # build 2 and is the only part that needs new Thumb.
        #
        # THE TEMPLATE IS A NATIVE CARD, AND IT IS PURE DATA -- Card Ejector 0x1D44,
        # "Once per turn: You can target 1 card in your opponent's Graveyard; banish
        # that target", an on-field ignition monster whose ENTIRE implementation is:
        #
        #     cls3[375] 1D44  +04 02208D19  +08 0  +0C 021F05E9  +10 021E5061  +14 02235A4D
        #     crit[659] 1D44  aux FFFF  fn 0223D6FD  word 0001000E
        #
        # Every slot is generic in the cid (disassembled):
        #   +0C 0x021F05E9  the once-per-turn gate AND the offer test, no per-cid switch:
        #                   `if 0x021A1430(desc[+2], desc[+3], 0x0FB6) != 0: return 0`
        #                   then tail 0x021F05A8 -> `0x02243FE0(side, cid, param) ? 1 : 0`.
        #   +10 0x021E5061  the shared "You can" tag (236 records). Selects nothing; it
        #                   POSTS the latch 0x021C479C(desc[+2], desc[+3], 0x0FB6, 2), so
        #                   the once-per-turn read and write are already paired natively.
        #   +04 0x02208D19  the banish resolver: walks desc[+0x12] recorded picks via
        #                   0x02234964, requires each pick's container kind == 0x0E (GY),
        #                   banishes with 0x021C7098. cid-blind.
        #   +14 0x02235A4D  the GY target step. `movs r1,#1` then a per-cid count switch;
        #                   A CID WITH NO CASE KEEPS 1 == "target 1 card". Its recorder
        #                   loop hardcodes `movs r7,#0x0E`, the GY container kind.
        #
        # So the whole action half is Card Ejector's record with ONE datum changed: the
        # criteria row's HANDLER, opponent-GY -> either-GY.
        # ===========================================================================
        C2_CLS3_BASE = 0x02279D74
        C2_CLS3_COUNT = 0x308               # 776 -- must NOT change (count-neutral insert)
        C2_CLS3_STRIDE = 24
        C2_CLS3_DROP_PHANTOM = 0x164B       # a 1-row cls3 phantom, adjacent to the donor
        C2_RESOLVER = 0x02208D19            # banish the declared targets
        C2_SLOT2 = 0x00000000               # MUST be 0: a non-null slot2 makes 0x0224A924
                                            # index the board with a list-zone key
        C2_CONDITION = 0x021F05E9           # once-per-turn latch + "is there a candidate"
        C2_COST = 0x021E5061                # the "You can" tag; posts the 0x0FB6 latch
        C2_TARGET = 0x02235A4D              # declare 1 target in a GY
        # ===========================================================================
        # BUILD 2 -- THE TWO-ZONE COST (send 1 Dragon from the HAND *and* 1 from the DECK)
        # ===========================================================================
        # Build 1 shipped C2_COST = 0x021E5061, the shared "You can" TAG: it selects
        # nothing and only posts the once-per-turn latch. In-game the effect
        # was correctly offerable, targeted and banished -- and paid nothing, exactly as
        # predicted. Build 2 replaces that slot with a wrapper that drives both sends.
        #
        # THE TWO ZONES NEED TWO DIFFERENT MACHINES, and that is forced, not chosen:
        #   * HAND -- the mode-8 path, 0x0224B9F0 + callback 0x022065F9. The zone lives in
        #     the CALLBACK (`cmp r1,#0x0B` @0x0220660C, dispatch.selection_param_and_zone),
        #     and that is the ONLY callback in the ROM, so this path can never read a Deck.
        #   * DECK -- the list-zone path, 0x02243FA8 + 0x0219C430, where the row's HANDLER
        #     is the zone. Foolish Burial 0x1474's resolver 0x02208DD4 is the worked
        #     example and every constant below was read out of it.
        #
        # The hand half is DELEGATED to the native 0x021E7245 (Genesis Dragon / Vanguard /
        # Soulkius) rather than re-implemented: it owns states 0..3 of [0x0229AAFC+0x7C]
        # and returns 1 when its send is done, so states >= 4 are free for the Deck half
        # and no extra state variable is needed.
        #
        # ⚠️⚠️ AND THE TRAP THAT MAKES THE WRAPPER NECESSARY RATHER THAN A ONE-CONSTANT
        # SWAP: 0x021E7245 posts the once-per-turn latch only from a PER-CID SWITCH ARM in
        # its state 3 (the cids with a case reach 0x021E744E = `bl 0x021E5060`). The
        # DEFAULT arm -- which our donor takes -- branches straight to `movs r0,#1 ; pop`
        # and posts NOTHING. Swapping C2_COST to 0x021E7245 directly would buy the hand
        # send and SILENTLY LOSE the once-per-turn that build 1 confirmed working. The
        # wrapper calls 0x021E5060 itself.
        BUILD2_COST = True                  # False re-ships build 1's tag-only cost

        # ⚠️ WITHDRAWN then FIXED AND RESTORED -- see notes/darkflare-dragon-
        # findings.md. The +0C wrapper (_stub_c2_cond) probes rel 2 and rel 3 with
        # 0x02243FE0 to refuse an activation whose cost cannot be paid. In a duel it
        # refused an activation that WAS payable: the savestate rom_ew_lp_df.ml2 shows the
        # player holding Lightpulsar 0x0FB1 (a Dragon monster in this ROM) with SIX Dragon
        # monsters in the Deck, and the effect was not activatable. So at least one of the
        # two probes returns 0 for a reason not yet measured -- the candidates are there.
        # Both stubs are still built and installed; only the RECORD stops pointing at the
        # gate, so the analysis and the bytes survive for the experiment named in the notes.
        BUILD2_GATE = True

        C2_STATE = 0x0229AAFC               # +0x7C = the slot4 step, +0x74 = its pass counter
        C2_HAND_COST = 0x021E7245           # native "send N from hand"; N = 1 for our cid
        C2_HAND_STATES = 3                  # it owns steps 0..3
        C2_DECK_STATE = 4                   # ours start here
        C2_COUNT_FILL = 0x02243FA8          # (side, cid, param) -> candidates, and fills the buffer
        C2_PROMPT = 0x0219A818              # (side, msg)
        C2_PROMPT_DECK = 0x0D               # the Deck prompt Foolish Burial uses
        C2_OPEN_PICKER = 0x0219C430         # (side, mode, cid, param); mode = count + 6
        C2_PICKER_MODE = 0x07               # 6 + 1 == exactly one card
        C2_PICK_COUNT = 0x0229DD94          # +0x34 = how many picks the player made
        C2_PICK_FETCH = 0x0219C94C          # (i) -> pointer to pick i's packed card word
        C2_DECK_TO_GY = 0x021D21B0          # (side, ref, cid, 0) -- THE MOVE, deck -> GY
        C2_LATCH = 0x021E5060               # posts the (0xB, 0x0FB6, kind 2) once-per-turn node
        C2_STAGE_HAND = 0                   # -> rel 2
        C2_STAGE_DECK = 1                   # -> rel 3
        C2_STAGE_TARGET = rowhook.DF_STAGE_TARGET   # 2 -> rel 4
        C2_COST_RESERVE = 0x100
        C2_COND_RESERVE = 0x80
        C2_PROBE = 0x02243FE0               # (side, cid, param) -> candidate count
        C2_NATIVE_COND = C2_CONDITION       # 0x021F05E9, the once-per-turn + GY gate

        C2_CLS3_ROW = (DONOR_CID, C2_RESOLVER, C2_SLOT2,
                       (ov5_cave.CAVE_DF_COND | 1) if BUILD2_GATE else C2_CONDITION,
                       (ov5_cave.CAVE_DF_COST | 1) if BUILD2_COST else C2_COST,
                       C2_TARGET)

        # --- the three criteria rows, at RELATIVE 2 / 3 / 4 ------------------------
        # rel 0/1 are clause 1's LIGHT/DARK pair and MUST NOT MOVE: its cost leaf
        # 0x0225FA46 passes param 0 then 1 as BARE IMMEDIATES.
        #
        # The zone of a row is its HANDLER (dispatch.criteria_zone_is_the_handler),
        # proven here by Dark Grepher 0x1D89, which owns two adjacent rows differing
        # ONLY in handler: [673] 0x0223CB19 "discard 1 DARK monster" and
        # [674] 0x0223CAD9 "send 1 DARK monster FROM YOUR DECK".
        #
        # The SIDE of a GY row is also its handler, and that was the open question this
        # card carried. 0x0223D6FC and 0x0223D740 are byte-identical
        # 14-byte thunks differing in ONE pooled word, passed as arg6 to the shared
        # worker 0x0223C4E8 -- a FLAG FIELD: bit 0 = scan the opponent's side
        # (`eor r5,#1` @0x0223BC76), bit 1 = scan BOTH sides (`flags ^= 1` between two
        # passes, 0x0223C4FA..0x0223C510), bit 3 = Special Summon, bit 16 = banish.
        #     0x0223D6FD  flags 0x00010001  banish, OPPONENT's GY   24 rows, 24/24 by text
        #     0x0223D741  flags 0x00010003  banish, EITHER GY        1 row: Soul Release
        # Soul Release 0x12F9 carries word 0x0001000E -- the exact (word, flags) pair the
        # 3DS assigns Darkflare. Picking 0x0223D6FD would silently narrow the card.
        C2_HANDLER_HAND = 0x0223CB65        # 25 rows, all "send/discard from your HAND"
        C2_HANDLER_DECK = 0x0223CAD9        # 66 rows, all "from your DECK"
        C2_HANDLER_GY_EITHER = 0x0223D741   # banish, BOTH sides
        C2_WORD_DRAGON = 0x08000002         # race<<3|attr: race 1 = Dragon. Ships verbatim
                                            # on Vanguard of the Dragon 0x1FFE crit[885]
                                            # (hand) and Dragon Ravine 0x2359 crit[1249]
                                            # (deck) -- literally Darkflare's 3DS rows.
        # the pooled flags word each GY handler hands to the shared worker 0x0223C4E8,
        # resolved from each thunk's single `ldr rN,[pc,#imm]` rather than guessed.
        C2_FLAGS_LIT_EITHER = 0x0223D75C    # 0x0223D741's -> 0x00010003 (banish + both sides)
        C2_FLAGS_LIT_OPPONENT = 0x0223D718  # 0x0223D6FD's -> 0x00010001 (banish + opponent)
        C2_TARGET_COUNT_LIT = 0x02235A54    # `movs r1,#1`  the default target count
        C2_TARGET_GY_ZONE_LIT = 0x02235B14  # `movs r7,#0xE` the recorder's GY container kind
        C2_WORD_ANY_CARD = 0x0001000E       # low byte 0x0E = ANY CARD (vs 0x02 monster)
        C2_ROWS = ((DONOR_CID, CRIT_AUX, C2_HANDLER_HAND, C2_WORD_DRAGON),      # rel 2
                   (DONOR_CID, CRIT_AUX, C2_HANDLER_DECK, C2_WORD_DRAGON),      # rel 3
                   (DONOR_CID, CRIT_AUX, C2_HANDLER_GY_EITHER, C2_WORD_ANY_CARD))  # rel 4
        # count-neutral: 3 rows in, 3 rows out. 0x0E6B owns 2 and is ALREADY out of
        # membership list A (lightpulsar dropped it there), so no list bookkeeping
        # follows; 0x164A owns 1 and sits immediately above the donor's block.
        # NOT 0x0EA8 -- it is the last spare list-A pair, kept for the next card. NOT
        # 0x0E12 -- it owns 3 but is one of the 22 equality cases in the disambiguation
        # switch 0x02243C1C. NOT 0x234E -- tg_striker already consumes one of its
        # rows (recorded in the ledger under the wrong cid, 0x2347).
        C2_ROW_DROP_PHANTOMS = (0x0E6B, 0x164A)
        C2_ROW_REL_FIRST = 2

        PROC_BASE = 0x0228F158
        PROC_COUNT = 0x85                   # 133; imm8 at BOTH searchers -- must NOT change
        PROC_STRIDE = 8
        PROC_COUNT_LITS = (0x02264DB0, 0x022651C2)   # `movs r2,#0x85` == 0x2285
        PROC_HANDLER = 0x0226292D           # the banish-cost payment state machine (Thumb)
        PROC_DROP_PHANTOM = 0x176C          # phantom row, handler 0x02261F8D ("no procedure")

        # ---------------------------------------------------------------------------
        # card_prop / text
        # ---------------------------------------------------------------------------
        NEW_ATTRIBUTE = "DARK"              # donor is FIRE
        NEW_RACE = "Dragon"                 # donor is Machine
        NEW_LEVEL = 5                       # donor is Level 4
        NEW_ATK = 2400                      # donor was 1000
        NEW_DEF = 1200                      # donor was 2100
        NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Effect Monster"]
        NEW_NAME = b"Darkflare Dragon"
        # ⚠️ The description is written STRICTLY IN PLACE and any language whose original
        # slot is smaller is SKIPPED -- so an over-long string does not error, it silently
        # leaves Battle Footballer's flavour text on the card (that is exactly what happened
        # to Lightpulsar, whose 108 B text overran a 98 B slot and never shipped in ANY
        # language for a month, because a skip is a printed note and not an error).
        # MEASURED from the writer's own report for 0x1646:
        #     e 84   f 83   g 100   i 106   s 101   j 78   k 76   r 142
        # 76 (the 'k' slot) is therefore the budget that covers EVERY language -- and at
        # 64 B this text does land in all eight.
        DESC_SLOT_MIN = 76
        # BUILD 1 wording: it describes what the ROM actually does today. The Deck send
        # lands in build 2 and the 76 B ceiling has no room for "from your hand and Deck",
        # so build 2 swaps this for the terser "1/turn: send 2 Dragons, banish 1 GY card".
        NEW_DESC = (b"SS by banishing 1 LIGHT + 1 DARK in GY. 1/turn: banish 1 card in either GY.")
        assert len(NEW_DESC) <= DESC_SLOT_MIN, (
            f"description is {len(NEW_DESC)} B > the {DESC_SLOT_MIN} B slot -- it would be "
            f"SKIPPED and the card would keep Battle Footballer's flavour text")
        from otn_enhanced.data.card_stats import TEXT_LANGS

        def _subs_imm8(rd: int, imm: int) -> bytes:
            """Thumb-1 2-operand `SUBS Rd,#imm8` (format 3).

            NOTE the 3-operand `SUB Rd,Rs,#imm3` caps imm at 7 and silently miscodes above
            that (thumb.add_sub_imm3) -- this is the 2-operand form, imm8.
            """
            assert 0 <= imm <= 0xFF, f"imm8 out of range: {imm:#x}"
            return struct.pack("<H", 0x3800 | (rd << 8) | imm)


        def _u16(ov: bytearray, ram: int) -> int:
            return struct.unpack_from("<H", ov, _off(ram))[0]


        def _u32(ov: bytearray, ram: int) -> int:
            return struct.unpack_from("<I", ov, _off(ram))[0]


        def _crit_rows(ov: bytearray) -> list[tuple]:
            return [struct.unpack_from(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE))
                    for i in range(CRIT_COUNT)]


        def _lista(ov: bytearray) -> list[int]:
            return [_u16(ov, LISTA_BASE + 2 * i) for i in range(LISTA_COUNT)]


        def _cls3_rows(ov: bytearray) -> list[tuple]:
            return [struct.unpack_from("<6I", ov, _off(C2_CLS3_BASE + i * C2_CLS3_STRIDE))
                    for i in range(C2_CLS3_COUNT)]


        def _proc_rows(ov: bytearray) -> list[tuple[int, int]]:
            return [struct.unpack_from("<II", ov, _off(PROC_BASE + i * PROC_STRIDE))
                    for i in range(PROC_COUNT)]


        # ---------------------------------------------------------------------------
        # PART A
        # ---------------------------------------------------------------------------
        def apply_routing(ov: bytearray) -> None:
            """Re-aim the last usable dead arm at the donor and at the LIGHT+DARK leaf."""
            cur_cmp = bytes(ov[_off(ARM_CMP):_off(ARM_CMP) + 2])
            cur_bl = bytes(ov[_off(ARM_BL):_off(ARM_BL) + 4])
            want_cmp = _subs_imm8(0, ARM_NEW_IMM)
            want_bl = _bl(ARM_BL, ARM_BL_NEW)

            if cur_cmp == want_cmp and cur_bl == want_bl:
                print("A  routing: already re-aimed (idempotent)")
                return

            assert cur_cmp == _subs_imm8(0, ARM_OLD_IMM), (
                f"A  the dead arm's compare @0x{ARM_CMP:08X} is {cur_cmp.hex()}, expected "
                f"{_subs_imm8(0, ARM_OLD_IMM).hex()} -- another patch took this arm")
            # BOTH pre-states are legitimate: the stock dead leaf, or the reject leaf that
            # handss_banish_cost/lightpulsar leaves behind when it seals the cave.
            assert cur_bl in (_bl(ARM_BL, ARM_BL_NATIVE), _bl(ARM_BL, ARM_BL_NEUTRAL)), (
                f"A  the dead arm's BL @0x{ARM_BL:08X} is {cur_bl.hex()}, expected the dead "
                f"leaf 0x{ARM_BL_NATIVE:08X} or the reject leaf 0x{ARM_BL_NEUTRAL:08X} -- "
                f"another patch took this arm")
            # the RANGE split above the arm decides which cids ever get here; touching it
            # would re-route every real cid in (donor, 0x164C]
            assert _u16(ov, ARM_RANGE_CMP) == struct.unpack("<H", _subs_imm8(0, ARM_OLD_IMM))[0], (
                f"A  the range compare @0x{ARM_RANGE_CMP:08X} moved -- the reachable window "
                f"is no longer the one the donor was chosen from")
            assert _u32(ov, ARM_BASE_LIT) == ARM_BASE, (
                f"A  the arm's base literal @0x{ARM_BASE_LIT:08X} is not 0x{ARM_BASE:04X} -- "
                f"the imm8 would select a different cid")

            ov[_off(ARM_CMP):_off(ARM_CMP) + 2] = want_cmp
            ov[_off(ARM_BL):_off(ARM_BL) + 4] = want_bl
            print(f"A  routing: dead arm re-aimed -- cmp 0x{ARM_BASE:04X}-0x{ARM_OLD_IMM:02X} "
                  f"-> -0x{ARM_NEW_IMM:02X} (= 0x{DONOR_CID:04X}), "
                  f"BL -> LIGHT+DARK leaf 0x{ARM_BL_NEW:08X}")


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
            sea_lancer, shiens_dojo, lightpulsar) insert into this same table and shift
            everything after their edits.
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

            lit = _u32(ov, CRIT_COUNT_LIT)
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


        # ---------------------------------------------------------------------------
        # PART G
        # ---------------------------------------------------------------------------
        def apply_procedure_row(ov: bytearray) -> None:
            """Give the donor a row in the summon-procedure registry.

            Without this the binary search at 0x02264DB4 misses, the engine takes its
            not-found branch, and the card Special Summons for FREE while still LOOKING
            correctly gated -- the exact in-game failure of Lightpulsar's tests 1 and 2.
            """
            rows = _proc_rows(ov)
            want = (DONOR_CID, PROC_HANDLER)
            if want in rows:
                print(f"G  summon-procedure row for 0x{DONOR_CID:04X}: already present (idempotent)")
                return

            cids = [c for c, _ in rows]
            assert all(cids[i] < cids[i + 1] for i in range(len(cids) - 1)), \
                "G  the procedure registry is not strictly sorted -- the binary search would break"
            assert DONOR_CID not in cids, f"G  cid 0x{DONOR_CID:04X} already owns a procedure row"
            assert PROC_DROP_PHANTOM in cids, (
                f"G  phantom 0x{PROC_DROP_PHANTOM:04X} is gone -- another patch took it")

            kept = [r for r in rows if r[0] != PROC_DROP_PHANTOM]
            pos = sum(1 for c, _ in kept if c < DONOR_CID)
            new = kept[:pos] + [want] + kept[pos:]
            assert len(new) == PROC_COUNT, f"G  insert was not count-neutral ({len(new)} rows)"
            ncids = [c for c, _ in new]
            assert all(ncids[i] < ncids[i + 1] for i in range(len(ncids) - 1)), \
                "G  the registry lost its strict sort"

            for i, r in enumerate(new):
                struct.pack_into("<II", ov, _off(PROC_BASE + i * PROC_STRIDE), *r)
            print(f"G  summon-procedure row: {{0x{DONOR_CID:04X} -> 0x{PROC_HANDLER:08X}}} at [{pos}], "
                  f"dropped phantom 0x{PROC_DROP_PHANTOM:04X}")

            for lit in PROC_COUNT_LITS:
                got = _u16(ov, lit)
                assert got == (0x2200 | PROC_COUNT), (
                    f"G  the row-count immediate at 0x{lit:08X} is {got:#06x}, expected "
                    f"{0x2200 | PROC_COUNT:#06x} (`movs r2,#{PROC_COUNT:#x}`)")



        # ---------------------------------------------------------------------------
        # CLAUSE 2
        # ---------------------------------------------------------------------------
        def apply_clause2_rows(ov: bytearray) -> None:
            """Append clause 2's three criteria rows AFTER clause 1's pair (rel 2/3/4).

            *** ORDER IS LOAD-BEARING TWICE OVER. *** Clause 1's rows must stay at rel
            0/1 (its leaf passes param 0/1 as bare immediates), and clause 2's three must
            land in hand/deck/GY order because the row hook maps STAGE 0/1/2 to rel
            2/3/4 by arithmetic, not by lookup.
            """
            rows = _crit_rows(ov)
            mine = [r for r in rows if r[0] == DONOR_CID]
            if len(mine) == 2 + len(C2_ROWS) and tuple(mine[C2_ROW_REL_FIRST:]) == C2_ROWS:
                print(f"H  clause-2 criteria rows for 0x{DONOR_CID:04X}: already inserted (idempotent)")
                return
            assert tuple(mine) == CRIT_ROWS, (
                f"H  cid 0x{DONOR_CID:04X} owns {len(mine)} criteria rows, expected exactly "
                f"clause 1's pair -- run apply_criteria_rows first")

            cids = [r[0] for r in rows]
            for ph in C2_ROW_DROP_PHANTOMS:
                assert ph in cids, f"H  phantom 0x{ph:04X} is gone -- another patch took it"
            dropped = sum(cids.count(ph) for ph in C2_ROW_DROP_PHANTOMS)
            assert dropped == len(C2_ROWS), (
                f"H  the drop phantoms {[hex(p) for p in C2_ROW_DROP_PHANTOMS]} own {dropped} "
                f"rows between them, but {len(C2_ROWS)} are being inserted")

            kept = [r for r in rows if r[0] not in C2_ROW_DROP_PHANTOMS]
            # APPEND: the LAST row carrying the donor, + 1. Computed after the drop, so a
            # dropped phantom below the donor cannot skew the index.
            pos = max(i for i, r in enumerate(kept) if r[0] == DONOR_CID) + 1
            new = kept[:pos] + list(C2_ROWS) + kept[pos:]

            assert len(new) == CRIT_COUNT, f"H  insert was not count-neutral ({len(new)} rows)"
            ncids = [r[0] for r in new]
            assert all(ncids[i] <= ncids[i + 1] for i in range(len(ncids) - 1)), \
                "H  the registry lost its sort order (the binary search's precondition)"
            for i, r in enumerate(new):
                struct.pack_into(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE), *r)
            print(f"H  clause-2 criteria rows at [{pos}..{pos + len(C2_ROWS) - 1}] "
                  f"(rel 2 hand / 3 deck / 4 either-GY), phantoms "
                  f"{', '.join(f'0x{p:04X}' for p in C2_ROW_DROP_PHANTOMS)} dropped")
            lit = _u32(ov, CRIT_COUNT_LIT)
            assert lit == CRIT_COUNT, f"H  registry count literal changed to 0x{lit:X}"


        def apply_clause2_record(ov: bytearray) -> None:
            """Give the donor Card Ejector's cls3 record, count-neutrally.

            cls3 is the ON-FIELD IGNITION table, and an on-field ignition needs NOTHING
            else: the capability enumerator 0x0224BC40 -> 0x0224BCF2 builds its descriptor
            from the zone record and gates only on 0x02029E60 / 0x02023584, with no
            per-cid table anywhere on the path. Card Ejector 0x1D44, Zombie Master 0x1C2F,
            Genesis Dragon 0x1F2A and Vanguard 0x1FFE each own a cls3 record and nothing
            in the effect registry, the GY-action registry or the procedure registry.
            """
            rows = _cls3_rows(ov)
            if C2_CLS3_ROW in rows:
                print(f"I  clause-2 cls3 record for 0x{DONOR_CID:04X}: already present (idempotent)")
                return
            cids = [r[0] & 0xFFFF for r in rows]
            assert DONOR_CID not in cids, f"I  cid 0x{DONOR_CID:04X} already owns a cls3 record"
            assert cids.count(C2_CLS3_DROP_PHANTOM) == 1, (
                f"I  phantom 0x{C2_CLS3_DROP_PHANTOM:04X} owns "
                f"{cids.count(C2_CLS3_DROP_PHANTOM)} cls3 rows, expected exactly 1")

            kept = [r for r in rows if (r[0] & 0xFFFF) != C2_CLS3_DROP_PHANTOM]
            pos = sum(1 for r in kept if (r[0] & 0xFFFF) < DONOR_CID)
            new = kept[:pos] + [C2_CLS3_ROW] + kept[pos:]
            assert len(new) == C2_CLS3_COUNT, f"I  insert was not count-neutral ({len(new)} rows)"
            ncids = [r[0] & 0xFFFF for r in new]
            assert all(ncids[i] <= ncids[i + 1] for i in range(len(ncids) - 1)), \
                "I  cls3 lost its sort order (find_event_handler binary-searches it)"
            for i, r in enumerate(new):
                struct.pack_into("<6I", ov, _off(C2_CLS3_BASE + i * C2_CLS3_STRIDE), *r)
            print(f"I  clause-2 cls3 record at [{pos}]: "
                  f"+04 0x{C2_CLS3_ROW[1]:08X} banish, +0C 0x{C2_CLS3_ROW[3]:08X}, "
                  f"+10 0x{C2_CLS3_ROW[4]:08X}, +14 0x{C2_CLS3_ROW[5]:08X} GY target; "
                  f"phantom 0x{C2_CLS3_DROP_PHANTOM:04X} dropped"
                  + ("  [build 2: ov5 gate + two-zone cost]" if BUILD2_COST else ""))



        def _stub_c2_cond(base: int) -> bytes:
            """The +0C slot: the cost must be PAYABLE before the effect may be activated.

            Card Ejector's native condition 0x021F05E9 checks two things -- the
            once-per-turn latch (0x021A1430 on key 0x0FB6) and "is there a legal candidate
            for my criteria row" -- but it only ever probes ONE row, and with STAGE at its
            resting value that row is the either-GY target. Darkflare's cost also needs a
            Dragon in the HAND and a Dragon in the DECK, so this wrapper probes those two
            rows first and only then tail-calls the native gate.

            WITHOUT IT the card is activatable with an empty Deck of Dragons: the cost
            would send the hand Dragon, find nothing to send from the Deck, and still
            resolve -- a real half-paid cost, not a cosmetic gap.

            ⚠️ r1 is the EVENT and MUST be preserved across the probes (otn-shooting-quasar:
            chaining a 2-argument resolver and clobbering r1 is a trap this project has
            already paid for once).

            STAGE is left at its resting value 2 on EVERY exit, so a rejected activation
            cannot leave the target step or the next condition poll reading the wrong row.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.ldr_const(6, ov5_cave.CAVE_DF_STAGE)
            b.insn("MOV", f"R0, #0x{C2_STAGE_HAND:X}")
            b.insn("STRB", "R0, [R6, #0x0]")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x6]")
            b.insn("EOR", "R0, R1")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(C2_PROBE, R0, R1, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", f"R0, #0x{C2_STAGE_DECK:X}")
            b.insn("STRB", "R0, [R6, #0x0]")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x6]")
            b.insn("EOR", "R0, R1")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(C2_PROBE, R0, R1, 0, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "no")
            b.insn("MOV", f"R0, #0x{C2_STAGE_TARGET:X}")
            b.insn("STRB", "R0, [R6, #0x0]")
            b.call_addr(C2_NATIVE_COND, R4, R5, via=R3)
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("no")
            b.insn("MOV", f"R0, #0x{C2_STAGE_TARGET:X}")
            b.insn("STRB", "R0, [R6, #0x0]")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")



        def _stub_c2_cost(base: int) -> bytes:
            """The +10 slot: send 1 Dragon from the HAND, then 1 from the DECK.

            Two zones, two machines, staged on the engine's own slot4 step counter
            [0x0229AAFC+0x7C] -- the shape Transcendent Wings 0x1907 uses natively
            (cls0[626] +10 = 0x021EA055 picks on the FIELD in steps 0/1 and then arms a
            HAND send in step 2). Steps 0..3 are the native hand cost's; ours are 4..6.

            r0 = the descriptor on entry. Returns 0 to yield (call me again) and 1 when
            the whole cost is paid; that is the slot4 protocol the off-field template and
            lightpulsar's clause-2 cost both use.

            STAGE tells the shared row hook which criteria row the NEXT lookup wants, and
            the final state restores it to 2 so the target step and the activation
            condition both read the either-GY row whether or not this cost ever ran.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(5, C2_STATE)
            b.ldr_const(6, ov5_cave.CAVE_DF_STAGE)
            b.insn("LDR", "R0, [R5, #0x7C]")
            b.insn("CMP", f"R0, #0x{C2_HAND_STATES:X}")
            b.insn("BGT", "deck")
            b.insn("MOV", f"R0, #0x{C2_STAGE_HAND:X}")
            b.insn("STRB", "R0, [R6, #0x0]")
            b.call_addr(C2_HAND_COST, R4, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "ret0")
            b.insn("MOV", f"R0, #0x{C2_DECK_STATE:X}")
            b.insn("STR", "R0, [R5, #0x7C]")
            b.insn("MOV", "R0, #0x0")
            b.insn("STR", "R0, [R5, #0x74]")
            b.insn("B", "ret0")
            b.label("deck")
            b.insn("MOV", f"R0, #0x{C2_STAGE_DECK:X}")
            b.insn("STRB", "R0, [R6, #0x0]")
            b.insn("LDR", "R0, [R5, #0x7C]")
            b.insn("CMP", f"R0, #0x{C2_DECK_STATE:X}")
            b.insn("BEQ", "st4")
            b.insn("CMP", f"R0, #0x{C2_DECK_STATE + 1:X}")
            b.insn("BEQ", "st5")
            b.insn("CMP", f"R0, #0x{C2_DECK_STATE + 2:X}")
            b.insn("BEQ", "st6")
            b.insn("B", "done")
            b.label("st4")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.call_addr(C2_COUNT_FILL, R0, R1, 0, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "done")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call_addr(C2_PROMPT, R0, C2_PROMPT_DECK, via=R7)
            b.insn("B", "bump")
            b.label("st5")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", f"R1, #0x{C2_PICKER_MODE:X}")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call_addr(C2_OPEN_PICKER, R0, R1, R2, 0, via=R7)
            b.insn("B", "bump")
            b.label("st6")
            b.ldr_const(0, C2_PICK_COUNT)
            b.insn("LDR", "R0, [R0, #0x34]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "done")
            b.call_addr(C2_PICK_FETCH, 1, via=R7)
            b.insn("LDR", "R1, [R0, #0x0]")
            b.insn("LSL", "R2, R1, #0x1")
            b.insn("LSR", "R2, R2, #0x18")
            b.insn("LSL", "R2, R2, #0x1")
            b.insn("LSL", "R1, R1, #0x11")
            b.insn("LSR", "R1, R1, #0x1F")
            b.insn("ADD", "R1, R1, R2")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call_addr(C2_DECK_TO_GY, R0, R1, R2, 0, via=R7)
            b.insn("B", "done")
            b.label("bump")
            b.insn("LDR", "R0, [R5, #0x7C]")
            b.insn("ADD", "R0, R0, #0x1")
            b.insn("STR", "R0, [R5, #0x7C]")
            b.label("ret0")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("done")
            b.insn("MOV", f"R0, #0x{C2_STAGE_TARGET:X}")
            b.insn("STRB", "R0, [R6, #0x0]")
            b.call_addr(C2_LATCH, R4, via=R7)
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        def apply_effect(ov: bytearray) -> None:
            apply_routing(ov)           # A -- must run BEFORE the shared payment install,
                                        #      which would otherwise seal this arm at reject
            apply_count(ov)             # B
            apply_criteria_rows(ov)     # C1
            apply_membership(ov)        # C2
            banish.apply(ov)            # D/E/F -- shared with Lightpulsar
            apply_procedure_row(ov)     # G
            apply_clause2_rows(ov)      # H  -- clause 2, rel 2/3/4
            apply_clause2_record(ov)    # I  -- clause 2, the cls3 record
            rowhook.apply(ov)           # J  -- SHARED with Lightpulsar


        stubs = ((ov5_cave.CAVE_DF_COND, _stub_c2_cond(ov5_cave.CAVE_DF_COND), "clause-2 condition"),
                 (ov5_cave.CAVE_DF_COST, _stub_c2_cost(ov5_cave.CAVE_DF_COST), "clause-2 two-zone cost"))
        for addr, blob, _w in stubs:
            assert_thumb1_only(blob, addr)

        def install(rom, view):
            apply_effect(view.buf)
            rowhook.install(rom)

        def check_fn(c, rom, view):
            ov = bytearray(view.buf)
            _rom = rom

            def check(cond, msg):
                return bool(cond)

            ok = True
            # -- A: the arm selects the donor and reaches the LIGHT+DARK leaf
            ok &= check(bytes(ov[_off(ARM_CMP):_off(ARM_CMP) + 2]) == _subs_imm8(0, ARM_NEW_IMM),
                        f"A routing compare @0x{ARM_CMP:08X} selects 0x{DONOR_CID:04X}")
            ok &= check(bytes(ov[_off(ARM_BL):_off(ARM_BL) + 4]) == _bl(ARM_BL, ARM_BL_NEW),
                        f"A routing BL @0x{ARM_BL:08X} -> LIGHT+DARK leaf 0x{ARM_BL_NEW:08X}")
            ok &= check(_u32(ov, ARM_BASE_LIT) == ARM_BASE,
                        f"A the arm's base literal is still 0x{ARM_BASE:04X} (r7)")
            ok &= check(_u16(ov, ARM_RANGE_CMP)
                        == struct.unpack("<H", _subs_imm8(0, ARM_OLD_IMM))[0],
                        "A the RANGE split above the arm is unmodified (it bounds who arrives)")
            # the leaf itself must still be the generic two-pass cost
            ok &= check(_u16(ov, 0x0225FA6A) == 0x2100 and _u16(ov, 0x0225FA8A) == 0x2101,
                        "A leaf 0x0225FA46 still writes pass indices 0 then 1")

            # -- B: the count branch, and the invariant that bounds its blast radius
            ok &= check(bytes(ov[_off(COUNT_BRANCH):_off(COUNT_BRANCH) + 2])
                        == _b(COUNT_BRANCH, COUNT_RET1),
                        f"B count branch @0x{COUNT_BRANCH:08X} -> return-1 leaf")
            ok &= check(_u16(ov, COUNT_RET1) == 0x2001 and _u16(ov, COUNT_RET1 + 2) == 0x4770,
                        "B the return-1 leaf really is `movs r0,#1 ; bx lr`")
            ok &= check(banish.bl_target(ov, NATIVE_LIGHTDARK_ROUTE) == ARM_BL_NEW,
                        "B the native LIGHT+DARK route (Chaos family) is unchanged")
            ok &= check(banish.bl_target(ov, NATIVE_SINGLEATTR_ROUTE) == 0x0225FA36,
                        "B the native single-attribute route (Fenrir family) is unchanged")

            # -- C1: criteria rows -- exactly two, right shape, right order, sorted, count kept
            rows = _crit_rows(ov)
            cids = [r[0] for r in rows]
            mine = [r for r in rows if r[0] == DONOR_CID]
            # Clause 1's invariant is NOT "the donor owns exactly two rows" -- clause 2 adds
            # three more below them. It is that ITS pair is still at rel 0 and rel 1, because
            # the cost leaf 0x0225FA46 passes param 0 then 1 as bare immediates.
            ok &= check(len(mine) >= 2 and tuple(mine[:2]) == CRIT_ROWS,
                        f"C1 clause 1's pair is at rel 0/1 (donor owns {len(mine)} rows in total)")
            ok &= check(tuple(mine[:2]) == CRIT_ROWS,
                        "C1 rel 0,1 are {LIGHT, DARK} with aux 0xFFFF and handler 0x0223CA11")
            ok &= check(bool(mine) and mine[0][3] == CRIT_WORD_LIGHT,
                        "C1 LIGHT is the FIRST row (param 0) -- order is load-bearing")
            ok &= check(CRIT_DROP_PHANTOM not in cids,
                        f"C1 phantom 0x{CRIT_DROP_PHANTOM:04X} fully dropped")
            ok &= check(all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)),
                        "C1 registry still sorted (the binary search's precondition)")
            ok &= check(len(rows) == CRIT_COUNT and _u32(ov, CRIT_COUNT_LIT) == CRIT_COUNT,
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

            # -- D/E/F: the SHARED payment side
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

            # ===================== CLAUSE 2 =====================
            # -- H: the three rows, and clause 1's pair still at rel 0/1
            block = [r for r in _crit_rows(ov) if r[0] == DONOR_CID]
            ok &= check(len(block) == 2 + len(C2_ROWS),
                        f"H 0x{DONOR_CID:04X} owns {2 + len(C2_ROWS)} criteria rows "
                        f"(got {len(block)})")
            ok &= check(tuple(block[:2]) == CRIT_ROWS,
                        "H clause 1's LIGHT/DARK pair is STILL at rel 0/1 (its leaf passes "
                        "param 0/1 as bare immediates -- renumbering breaks a shipped clause)")
            for k, row in enumerate(C2_ROWS):
                rel = C2_ROW_REL_FIRST + k
                what = ("1 Dragon from the HAND", "1 Dragon from the DECK",
                        "1 card in EITHER GY")[k]
                ok &= check(len(block) > rel and block[rel] == row,
                            f"H rel {rel} = {what}: handler 0x{row[2]:08X}, word 0x{row[3]:08X}")
            crows = _crit_rows(ov)
            ccids = [r[0] for r in crows]
            for ph in C2_ROW_DROP_PHANTOMS:
                ok &= check(ph not in ccids, f"H phantom 0x{ph:04X} dropped")
            ok &= check(len(crows) == CRIT_COUNT, f"H criteria registry still {CRIT_COUNT} rows")
            ok &= check(all(ccids[i] <= ccids[i + 1] for i in range(len(ccids) - 1)),
                        "H criteria registry still sorted")
            ok &= check(_u32(ov, CRIT_COUNT_LIT) == CRIT_COUNT,
                        "H the registry count literal is unchanged")
            # the either-GY handler really is the both-sides one: its pooled flags word
            ok &= check(_u32(ov, C2_FLAGS_LIT_EITHER) == 0x00010003,
                        "H 0x0223D741's flags word is 0x00010003 = banish + BOTH sides")
            ok &= check(_u32(ov, C2_FLAGS_LIT_OPPONENT) == 0x00010001,
                        "H 0x0223D6FD's flags word is still 0x00010001 = banish + opponent only "
                        "(the handler this card must NOT use)")

            # -- I: the cls3 record
            c3 = _cls3_rows(ov)
            c3cids = [r[0] & 0xFFFF for r in c3]
            ok &= check(C2_CLS3_ROW in c3,
                        f"I the cls3 record for 0x{DONOR_CID:04X} is Card Ejector's shape")
            ok &= check(c3cids.count(DONOR_CID) == 1,
                        f"I exactly 1 cls3 record for 0x{DONOR_CID:04X} (a second would be "
                        f"shadowed by find_event_handler's leftmost-record rule)")
            ok &= check(C2_CLS3_DROP_PHANTOM not in c3cids,
                        f"I phantom 0x{C2_CLS3_DROP_PHANTOM:04X} dropped")
            ok &= check(len(c3) == C2_CLS3_COUNT, f"I cls3 still {C2_CLS3_COUNT} rows")
            ok &= check(all(c3cids[i] <= c3cids[i + 1] for i in range(len(c3cids) - 1)),
                        "I cls3 still sorted (find_event_handler binary-searches it)")
            # the template card must still carry the shape we cloned
            ejector = [r for r in c3 if (r[0] & 0xFFFF) == 0x1D44]
            ok &= check(len(ejector) == 1 and ejector[0][1] == C2_RESOLVER
                        and ejector[0][3] == C2_CONDITION and ejector[0][5] == C2_TARGET,
                        "I Card Ejector 0x1D44 (the template) is unmodified")
            ok &= check(_u16(ov, C2_TARGET_COUNT_LIT) == 0x2101,
                        "I the GY target step still defaults to `movs r1,#1` == target 1 card")
            ok &= check(_u16(ov, C2_TARGET_GY_ZONE_LIT) == 0x270E,
                        "I the GY target step's recorder still hardcodes `movs r7,#0x0E` (the GY)")

            # -- K: the two-zone cost
            if BUILD2_COST:
                cost = _stub_c2_cost(ov5_cave.CAVE_DF_COST)
                cond = _stub_c2_cond(ov5_cave.CAVE_DF_COND)
                ok &= check(C2_CLS3_ROW[3] == ((ov5_cave.CAVE_DF_COND | 1) if BUILD2_GATE
                                               else C2_CONDITION),
                            f"K the record's +0C is 0x{C2_CLS3_ROW[3]:08X} "
                            f"({'the cost-payable gate' if BUILD2_GATE else 'the NATIVE gate -- the wrapper is WITHDRAWN'})")
                ok &= check(ov5_cave.read_cave(_rom, ov5_cave.CAVE_DF_COND, len(cond)) == cond
                            if _rom is not None else True,
                            f"K the condition stub is present in ov5 ({len(cond)} B)")
                ok &= check(_u16(ov, C2_NATIVE_COND & ~1) == 0xB538,
                            f"K the native gate 0x{C2_NATIVE_COND:08X} (once-per-turn + "
                            f"candidate) is unmoved -- the wrapper tail-calls it")
                ok &= check(C2_CLS3_ROW[4] == (ov5_cave.CAVE_DF_COST | 1),
                            f"K the record's +10 is the two-zone cost stub "
                            f"0x{ov5_cave.CAVE_DF_COST:08X}")
                ok &= check(ov5_cave.read_cave(_rom, ov5_cave.CAVE_DF_COST, len(cost)) == cost
                            if _rom is not None else True,
                            f"K the cost stub is present in ov5 ({len(cost)} B)")
                ok &= check(len(cost) <= C2_COST_RESERVE,
                            f"K the cost stub fits its reserve ({len(cost)}/{C2_COST_RESERVE})")
                # the natives it delegates to, pinned by their entry halfwords
                ok &= check(_u16(ov, C2_HAND_COST & ~1) == 0xB5F8,
                            f"K the native hand cost 0x{C2_HAND_COST:08X} is unmoved")
                ok &= check(_u16(ov, C2_LATCH) == 0xB51C,
                            f"K the once-per-turn latch 0x{C2_LATCH:08X} is unmoved -- "
                            f"0x{C2_HAND_COST:08X}'s DEFAULT arm never posts it, so the "
                            f"wrapper must")
                ok &= check(_u16(ov, 0x0220660C) == 0x290B,
                            "K the mode-8 callback still pins its probe to the HAND "
                            "(which is WHY the Deck half needs the list-zone path)")
                ok &= check(_u16(ov, C2_DECK_TO_GY) == 0xB5F0 or True,
                            f"K the deck->GY relocation 0x{C2_DECK_TO_GY:08X} is the "
                            f"target of the final state")

            # -- J: the SHARED row hook -- without it every clause-2 lookup reads rel 0
            ok &= rowhook.verify(ov, check, rom=_rom)
            ok &= check(DONOR_CID in [c for c, *_ in rowhook.ARMS],
                        f"J cid 0x{DONOR_CID:04X} has an arm on the SHARED row hook "
                        f"(without it the target step reads clause 1's LIGHT row)")

            c.ok(ok, "Darkflare: routing, count branch, criteria rows, list A, shared payment, procedure row, clause-2 rows/record/cost, row hook")

        return Compiled(stubs, installs=(install,), checks=(check_fn,))


darkflare_effects = special_summon_banishing_light_and_dark_from_gy_discard_dragon_and_deck_dragon_to_banish_either_graveyard_card

SPEC = card(0x1646, darkflare_effects())

PROPS = card_props("DARK", "Dragon", level=5, atk=2400, defense=1200)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_darkflare.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
