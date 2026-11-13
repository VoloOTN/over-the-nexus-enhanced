"""The Gates of Dark World (Field Spell) on Colosseum - Cage of the Gladiator Beasts 0x1C8B.

See notes/gates-of-dark-world-findings.md and card_text.CARD_TEXT[0x1C8B] for the printed text: all Fiend-Type monsters gain 300 ATK and
DEF; once per turn, banish 1 Fiend from the Graveyard, discard 1 Fiend, then draw 1 card.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, Compiled, DRAW_COUNT
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.data.card_stats import TEXT_LANGS
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class field_spell_fiend_monsters_gain_300_atk_def_banish_fiend_from_graveyard_discard_fiend_then_draw_1_once_per_turn:
    """The Gates of Dark World (Colosseum - Cage of the Gladiator Beasts 0x1C8B, a Field Spell kept as a Spell): 'All Fiend-Type monsters gain 300 ATK and
    DEF. Once per turn: You can banish 1 Fiend-Type monster from your Graveyard; discard 1 Fiend-Type monster, then draw 1 card.' Clause 1 = the donor's
    field stat arm rewritten as a Fiend +300/+300 block, its counter-accrual arm / trigger registry row / cls1 record retired; clause 2 = a cls3 record
    over 0x1AF0 (draw-N resolver, once-per-turn gate, GY banish cost, hand discard cost), two criteria rows (hand rel 0, GY rel 1) over 0x178C / 0x1795,
    the LIST B and L2 memberships (0x234F, a 28-byte provider search stub), a draw-count row over 0x1B1A, the discard-filter list, and two ov5 stubs
    (slot3 gate, cost->effect discard mover); the ARM9 Gladiator Beast set-code table is a post. Original code embedded verbatim (the legacy in-place
    f/g/i/s name/description writer is kept as a post)."""

    def compile(self, view, cid) -> Compiled:
        import struct
        import ndspy.code
        import ndspy.rom
        from otn_enhanced.asm.effect_verify import assert_thumb1_only
        from otn_enhanced.asm.effect_builder import EffectBuilder
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.cards.snoww import _open_pac, _find_prop, _read_cstr
        from otn_enhanced.data.card_stats import place_string
        from otn_enhanced.effects.common import ov3_off as _off

        DONOR_CID = 0x1C8B      # Colosseum - Cage of the Gladiator Beasts (keep-cid rule)
        DEAD_CID = 0x2500       # a phantom cid (no card_prop row) used to retire rows

        from otn_enhanced.effects.common import ARM9_BASE

        # ---------------------------------------------------------------------------
        # PART A -- the field-spell stat engine
        # ---------------------------------------------------------------------------
        FIELD_FN = 0x021B26F4           # the field-spell stat engine (bounds 0x021B26F4..0x021B2B6E)
        DONOR_ARM = 0x021B2A3E          # Colosseum's switch arm (44 B, exclusively its own)
        DONOR_ARM_END = 0x021B2A6A      # exclusive -- Realm of Light 0x1DCA's arm starts here
        ARM_ENTRY_BRANCH = 0x021B27DC   # the switch's `b DONOR_ARM` -- the arm's only inbound edge

        PLUS300_TAIL = 0x021B28CC       # Jurassic World's shared +300/+300 tail (needs r1 == 0x200)
        NO_CHANGE = 0x021B2A2C          # a nearby `b 0x021B2B48` (the "did nothing" exit)
        EPILOGUE = 0x021B2B48           # writes r4/r5 through [sp+0x2C]/[sp+0x30] and returns

        RACE_BIT_FIEND = 3              # game_constants.ERA2_RACE_MAP[3] == "Fiend"

        # Colosseum's native arm, as shipped (the 44 bytes PART A replaces):
        #   ldr r1,[sp,#0x28] ; adds r0,r7,#0 ; bl 0x021A3320   -> r0 = the monster's cid
        #   bl 0x02023AB0                                       -> "is a Gladiator Beast?"
        #   ... x100 per counter on this card ... ; b 0x021B2980 (adds r4,r4,r0 / r5,r5,r0)
        NATIVE_ARM = bytes.fromhex(
            "0a99381cf0f76dfc71f633f800287cd00098012101404648"
            "474b4843019914224a4318181158642048438ae7")

        # The +300/+300 tail, byte-exact -- PART A branches into it, so it must not move.
        PLUS300_TAIL_BYTES = bytes.fromhex("081cd438d43924186d1837e1")

        # ---------------------------------------------------------------------------
        # PART B -- the counter-accrual arm call (counter.six_samurai_arm_site idiom)
        # ---------------------------------------------------------------------------
        # 0x0226638E does `ldr r0,=<cid> ; bl 0x02244418`; the pool word is the ONLY
        # thing naming the donor there (verified: exactly one ldr [pc] resolves to it).
        COUNTER_ARM_POOL = 0x022666AC
        COUNTER_ARM_SITE = 0x0226638E
        COUNTER_ARM_FN = 0x02244418

        # ---------------------------------------------------------------------------
        # PART C -- the continuous-trigger registry (counter.trigger_registry)
        # ---------------------------------------------------------------------------
        TRIG_BASE = 0x02275510          # 181 rows x 8 {+0x00 Thumb handler, +0x04 cid}
        TRIG_COUNT = 181
        TRIG_ROW = 117                  # Colosseum's row (@0x022758B8)
        TRIG_HANDLER = 0x02244431       # shared counter-accrual handler (many cards)

        # ---------------------------------------------------------------------------
        # PART D -- the donor's cls1 record (dispatch.cls_tables / cls_table_selector)
        # ---------------------------------------------------------------------------
        CLS1_BASE = 0x022860D4
        CLS1_COUNT = 0x535              # 1333
        CLS1_STRIDE = 24
        CLS1_ROW = 706                  # Colosseum's record in the CLEAN base ROM (@0x0228A304).
                                        # ⚠️ A HINT ONLY -- never index with it. In the combined
                                        # chain karakuri_haipa drops cls1 phantom 0x0ECC
                                        # (a count-neutral swap), which shifts every row between
                                        # its drop and its insert; by step 29 the donor's record
                                        # has moved to 705 and cls1[706] holds 0x1C8C. The chain
                                        # build caught this as
                                        #   AssertionError: cls1[706] is 0x1C8C, expected 0x1C8B
                                        # Locate the record BY CID (_cls1_row_of).
        # {+04 = 0x0221A6ED, +08..+14 = 0} -- 0x0221A6ED is the shared counter-card event
        # handler (10 cids: Clock Tower Prison, Metal Shooter, Crystal Tree, Card Guard,
        # The Dragon Dwelling in the Deep, ...), so retiring it is a per-record edit.
        NATIVE_CLS1 = (0x0221A6ED, 0, 0, 0, 0)
        DEAD_CLS1 = (0, 0, 0, 0, 0)     # 6 of 1333 shipped records already have slot+04 == 0

        # ---------------------------------------------------------------------------
        # PART E -- the ARM9 "Gladiator Beast" set-code table
        # ---------------------------------------------------------------------------
        # The thunk 0x02023AB0 is `ldr r1,=0x0209CDF2 ; ldr r3,=<bsearch> ; movs r2,#0x1D ; bx r3`,
        # so base AND count are pinned by the consumer's own literals.  It is also the
        # very predicate the donor's native field arm called (bl 0x02023AB0 @0x021B2A46).
        GB_THUNK = 0x02023AB0
        GB_TBL_POOL = 0x02023AB8        # the thunk's table-base literal
        GB_TBL = 0x0209CDF2
        GB_COUNT = 0x1D                 # 29 -- `movs r2,#0x1D` @0x02023AB4
        GB_COUNT_IMM = 0x02023AB4
        GB_FILLER = 0xFFFF              # > every cid (range 0x0D48..0x24E8); can never match

        # ---------------------------------------------------------------------------
        # PART E2 -- the ARM9 "Dark World" set-code table (added)
        # ---------------------------------------------------------------------------
        # FOUND IN-GAME: with Snoww, Unlight of Dark World live, its search ("add 1
        # 'Dark World' card from your Deck to your hand") could NOT fetch this card --
        # because the donor was in no set-code table at all after PART E, so the engine
        # does not regard "The Gates of Dark World" as a "Dark World" card.  Reported by
        # the user; the search mechanism itself was confirmed working.
        #
        # The thunk 0x020238B4 is `ldr r1,=0x0209CA06 ; ldr r3,=<bsearch> ; movs r2,#0x10
        # ; bx r3`, so base AND count are pinned by the consumer's own literals, and the
        # list is BINARY-SEARCHED -- the edit must be count-neutral AND stay sorted.
        #
        # Count-neutral by dropping the phantom 0x0EC9 (index 0), which has no card_prop
        # record and can therefore never be a card in a duel; the donor is then inserted
        # at its sorted position between Renge 0x1C18 and Dark World Grimoire 0x1D25.
        # A Spell in this list is normal -- Grimoire, Dealings, Lightning and Gateway are
        # all already in it -- and it cannot make the donor findable by Scarr, whose
        # criteria row filters on card type MONSTER (word low half 0x0002).
        DW_THUNK = 0x020238B4
        DW_TBL_POOL = 0x020238BC        # the thunk's table-base literal
        DW_TBL = 0x0209CA06
        DW_COUNT = 0x10                 # 16 -- `movs r2,#0x10` @0x020238B8
        DW_COUNT_IMM = 0x020238B8
        DW_DROP_PHANTOM = 0x0EC9        # no card_prop record; its membership is inert

        # ---------------------------------------------------------------------------
        # PART F -- the card face
        # ---------------------------------------------------------------------------
        NEW_NAME = b"The Gates of Dark World"        # 23 B (+NUL = 24)
        NEW_DESC = (b"All Fiend-Type monsters gain 300 ATK and DEF. Once per turn: You "
                    b"can banish 1 Fiend-Type monster from your Graveyard; discard 1 "
                    b"Fiend-Type monster, then draw 1 card.")
        from otn_enhanced.data.card_stats import TEXT_LANGS

        # ===========================================================================
        # CLAUSE 2 -- "Once per turn: You can banish 1 Fiend-Type monster from your
        # Graveyard; discard 1 Fiend-Type monster, then draw 1 card."
        # ===========================================================================
        # Every selection step is a NATIVE function; the only new Thumb in the whole
        # clause is the 28-byte membership stub of PART I.  The slot assignment (see
        # dispatch.slot4_and_slot5_are_interchangeable_machines,
        # dispatch.gy_banish_cost_and_row_param_sources, resolver.draw_n_is_a_per_cid_table
        # and timing.once_per_turn_is_the_0fb6_rider):
        #
        #   +04 slot1  0x022065B9  "draw N", N from the per-cid table 0x022704A4   PART K
        #   +08 slot2  0           none needed (28 native records pair slot3 = 1 with 0)
        #   +0C slot3  0x021F01C1  the bare once-per-turn gate on rider key 0x0FB6
        #   +10 slot4  0x021E56E9  banish 1 Fiend from the GY, and stamp 0x0FB6
        #   +14 slot5  0x021E4EED  discard 1 Fiend from the hand
        #
        # WHICH CRITERIA ROW EACH STEP READS.  Row choice is `param & 0x10000000` for a
        # cid in LIST B (0x02243C10), and the two steps get their param from different
        # places: slot4's 0x021E5318 asks the PROVIDER 0x02234E78 (0x021E5488), while
        # slot5's 0x021E4EED hardcodes `movs r2,#0` (0x021E4F40).  So:
        #
        #   ROW 0  hand   <- slot5, param 0
        #   ROW 1  GY     <- slot4, param 0x10000000 (which PART I makes the provider return)
        #
        # That is also the row order the 3DS ships for this card (cid 0x25F3), arrived at
        # independently.  Both rows are byte-identical copies of rows already working in
        # this ROM: Fabled Valkyrus 0x1FB5's hand row and Dark Necrofear 0x1466's GY row.
        CLAUSE2 = True

        CRIT_BASE = 0x022713C4          # the criteria / populate registry
        CRIT_COUNT = 1388               # rows x 12 {u16 cid, u16 filt, u32 handler, u16 flags, u16 extra}
        CRIT_STRIDE = 12
        CRIT_NO_ARCHETYPE = 0xFFFF      # filt: no set-code filter
        CRIT_FLAGS = 0x0002             # the "is a real card" predicate bit
        CRIT_EXTRA_FIEND = 0x1800       # extra high byte 0x18 >> 3 == race 3 == Fiend
        HANDLER_HAND = 0x0223CB19       # select from HAND  -- Fabled Valkyrus 0x1FB5's handler
        HANDLER_GY = 0x0223CA11         # select from GY    -- Dark Necrofear 0x1466's handler
        # The two phantom rows PART G consumes.  Adjacent, so one memmove; neither cid has
        # a card_prop record and neither is claimed by any other patch.
        CRIT_DROP = (0x178C, 0x1795)

        LISTB_BASE = 0x02271314         # the "this cid owns a two-row pair" membership list
        LISTB_COUNT = 0x1B              # 27 -- `movs r2,#0x1b` @0x02243C06
        LISTB_COUNT_IMM = 0x02243C06
        LISTB_DROP = 0x234F             # a phantom; its own rows are unreachable without it

        L2_BASE = 0x02271104            # the provider's "return 1 << 28" list
        L2_COUNT = 0x1C                 # 28 -- `movs r2,#0x1c` @0x02234E94
        L2_COUNT_IMM = 0x02234E94
        L2_SEARCH_SITE = 0x02234E96     # the `bl 0x02022E14` PART I retargets
        L2_SEARCH_FN = 0x02022E14       # the generic sorted-u16 search (Thumb)
        # PART I lives in the 30 bytes of the donor's own field arm that clause 1 left
        # dead.  Nothing branches there (clause 1's block ends in `b PLUS300_TAIL`), and
        # being overlay-3 it is resident in puzzles too, unlike the ov5 cave.
        STUB_BASE = 0x021B2A4C          # DONOR_ARM + 14 (clause 1's block is 14 B)
        STUB_END = DONOR_ARM_END        # 0x021B2A6A

        CLS3_BASE = 0x02279D74          # the cls3 dispatch table
        CLS3_COUNT = 0x308              # 776
        CLS3_STRIDE = 24
        # CLS3_DROP: a phantom that owns TWO adjacent records, so dropping one cannot
        # orphan a card (the argument sea_lancer used for 0x234F).
        #
        # ⚠️ WHY THIS PHANTOM AND NOT ANOTHER -- cls3 IS ANCHORED BY ROW INDEX ELSEWHERE.
        # shiens_dojo drops row 223 and inserts at 233; sea_lancer hard-asserts
        # the donor cid at cls3[527].  A count-neutral swap shifts only the rows strictly
        # BETWEEN the drop index and the insert position.  0x1AF0 sits at cls3[267] and the
        # donor inserts at 340, so the shifted span is 268..339:
        #     223, 233  below the span  -> shiens_dojo unaffected
        #     527       above the span  -> sea_lancer unaffected
        #     334       INSIDE the span -> maiden_eyes_of_blue's phantom 0x1C80 moves
        #                                  to 333, which is harmless: that module locates it
        #                                  by full RECORD CONTENT (_count_neutral_swap's
        #                                  `r == drop`) and verifies by cid, never by index.
        # Dropping a phantom ABOVE the insert instead (the next ones are 710/711/712) would
        # shift 340..709 upward and move sea_lancer's hard-coded 527 -- strictly worse.
        # Any future cls3 insert must redo this arithmetic before picking its phantom.
        CLS3_DROP = 0x1AF0
        SLOT1_DRAW = 0x022065B9         # "draw N" resolver
        SLOT3_ONCE_PER_TURN = 0x021F01C1
        SLOT4_BANISH_GY = 0x021E56E9    # banish 1 (default count) + stamp the 0x0FB6 rider
        SLOT5_DISCARD_HAND = 0x021E4EED  # Fabled Valkyrus's discard cost, reading row 0

        # ---------------------------------------------------------------------------
        # PARTS L / M / N -- the two bugs from in-game test #1
        # ---------------------------------------------------------------------------
        # BUG 1  the card was activatable with NO Fiend in the Graveyard, and the cost's
        #        selection machine then froze on an empty candidate list.  slot3
        #        0x021F01C1 is the BARE once-per-turn gate -- it never checks for a legal
        #        candidate, and our slot2 is 0, so nothing did.       -> PART N
        # BUG 2  the discard was a COST, and a cost discard does NOT trigger Dark World
        #        monsters (user: Dark World Dealings / Lightning / Dragged
        #        Down / Graceful Charity / Card Destruction all trigger because they
        #        discard as an EFFECT; Hand Destruction does not, because it *sends*).
        #        Sillva was discarded and did not Special Summon.      -> PARTS L + M
        #
        # THE EFFECT-DISCARD PATH.  0x022598A0(side, count, monsters_only, f3) fills a
        # request struct (0x0225985C) and posts it; the discard subsystem fulfils it and
        # THAT is what triggers.  All 24 attributed call sites are slot1 RESOLVERS.  It
        # carries no race field -- its only filter is `monsters_only`, proven by its being
        # set on exactly one caller, The Cheerful Coffin 0x12FA "Discard up to 3 Monster
        # Cards".  The Fiend restriction therefore has to come from somewhere else:
        #
        # 0x0225A3F0(side, zone, hand_idx) is the per-candidate legality test for that
        # request.  It reads the ACTING card's cid at [0x0229AAFC+0x0A], searches the
        # 31-entry sorted list 0x0228EF48, and for a member calls
        # 0x02243FE0(side, cid, hand_idx) -- the criteria-registry candidate COUNT.  The
        # param is the hand INDEX, a small integer, so bit 28 is clear and a LIST B cid
        # resolves to ROW 0 -- which is already our HAND/Fiend row.  So membership in
        # 0x0228EF48 filters the EFFECT discard to Fiends using the row PART G shipped.
        # Its members read exactly like that: Allure of Darkness, Common Charity,
        # Familiar Knight, Drastic Drop Off and the whole Koa'ki Meiru family.
        EFFECT_DISCARD = 0x022598A0     # post the effect-discard request (side, n, mono, f3)
        DISCARD_FILTER_LIST = 0x0228EF48   # "my hand selection is criteria-filtered"
        DISCARD_FILTER_COUNT = 0x1F        # 31 -- `movs r2,#0x1f` @0x0225A418
        DISCARD_FILTER_IMM = 0x0225A418
        DISCARD_FILTER_PAD = 0x0228EF86    # the 2 B alignment pad the 32nd entry grows into
        CRITERIA_COUNT_FN = 0x02243FE0  # (side, cid, param) -> number of legal candidates
        RIDER_WALKER = 0x021A1430       # (side, zone, key) -> the attached-effect node
        ONCE_PER_TURN_KEY = 0x0FB6      # the "already used this turn" rider key
        PHASE_BLOCK = 0x0229AAFC        # [+0x70] = the resolver phase code
        ACT_PHASE = 0x80                # the phase a resolver first sees
        NEXT_PHASE = 0x7F               # "I yielded; call me again in the next phase"
        ROW1_PARAM = 0x10000000         # selects criteria ROW 1 for a LIST B cid

        # --- PART P: the cost -> effect discard mover (in-game tests #3/#4) -------
        DISCARD_MOVER_COST = 0x021C6DB4    # relocation kind 1 -- does NOT trigger Dark World
        DISCARD_MOVER_EFFECT = 0x021C6D58  # relocation kind 0 -- THE effect discard.  Its
                                           # callers are the cards that famously trigger Dark
                                           # World: Card Destruction 0x12D5, Dragged Down into
                                           # the Grave 0x14E8, Morphing Jar 0x11F5, Royal
                                           # Tribute 0x15A4, Beckoning Light 0x1769,
                                           # Confiscation 0x1324, Mind Crush 0x1803, Into the
                                           # Void 0x2278.  ⚠️ It takes THREE arguments
                                           # (side, index, flag) where the other two take two,
                                           # so the trampoline must zero r2.
                                           # (0x021C6D90 writes kind 2 and was tried in-game
                                           # the discard resolved but Dark World
                                           #  still did NOT trigger, so kind 2 is not it.)
        DISCARD_MOVER_SITE = 0x021E4F66    # the `bl` inside Valkyrus's discard cost 0x021E4EED
        RACE_ACCESSOR = 0x0202ABB8      # (cid) -> race; ((word1 << 10) & -1) >> 27, Fiend = 3
        RACE_FIEND = 3

        DRAW_BASE = 0x022704A4          # {u16 cid, s16 count}, binary-searched by 0x02206304
        DRAW_COUNT = 0xBD               # 189 -- `movs r2,#0xbd` @0x02206324
        DRAW_COUNT_IMM = 0x02206324
        DRAW_STRIDE = 4
        DRAW_N = 1
        DRAW_DROP = 0x1B1A              # unclaimed phantom row


        # ---------------------------------------------------------------------------
        # helpers
        # ---------------------------------------------------------------------------


        def _b_imm11(site: int, target: int) -> int:
            """Encode an unconditional Thumb-1 `B` at *site* to *target*."""
            delta = target - (site + 4)
            assert delta % 2 == 0, f"B 0x{site:08X} -> 0x{target:08X} is not halfword aligned"
            off = delta // 2
            assert -0x400 <= off < 0x400, (
                f"B 0x{site:08X} -> 0x{target:08X} is {off} halfwords -- out of imm11 range")
            return 0xE000 | (off & 0x7FF)


        def build_fiend_block(base: int = DONOR_ARM) -> bytes:
            """The clause-1 block: 'if the monster is Fiend-Type, +300 ATK and +300 DEF'.

            Seven halfwords of Thumb-1.  It reuses Jurassic World's own +300/+300 tail
            (PLUS300_TAIL), which is why the arithmetic needs no verification of its own:
            the tail is Konami's shipped implementation of this exact clause.

                ldr  r1,[r6,#8]     ; r1 = the monster's race bitmask (1 << race_code)
                movs r0,#8          ; Fiend = bit 3
                tst  r0,r1
                beq  NO_CHANGE      ; not a Fiend -> contribute nothing
                movs r1,#2
                lsls r1,r1,#8       ; r1 = 0x200, the amount source the tail expects
                b    PLUS300_TAIL   ; -> +300 ATK / +300 DEF -> EPILOGUE
            """
            assert RACE_BIT_FIEND < 8, "the Fiend bit must fit a movs imm8"
            b = EffectBuilder()
            b.insn("LDR", "R1, [R6, #0x8]")                       # r1 = race bitmask
            b.insn("MOV", f"R0, #{1 << RACE_BIT_FIEND}")          # movs r0,#8
            b.insn("TST", "R0, R1")
            b.insn("BEQ", f"0x{NO_CHANGE:08X}")                   # not a Fiend -> no change
            b.insn("MOV", "R1, #0x2")
            b.insn("LSL", "R1, R1, #0x8")                         # r1 = 0x200
            b.insn("B", f"0x{PLUS300_TAIL:08X}")
            # no pool: pad="nop" would tack on a nop for a base whose end is not 4-aligned
            blob = b.assemble(base, pad="nop")[:14]
            assert len(blob) <= DONOR_ARM_END - base, (
                f"the block is {len(blob)} B but the donor's arm slot is "
                f"{DONOR_ARM_END - base} B")
            assert_thumb1_only(blob, base)                # never trust a bare capstone disasm
            return blob


        def _check_arm_is_exclusive(ov: bytes) -> None:
            """The donor's arm must have exactly one inbound edge (the switch's own `b`).

            Guards the assumption that makes an in-place overwrite safe: nothing else in
            the field-spell engine jumps into the middle of the 44 bytes we are taking.
            """
            from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

            md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
            inside = set(range(DONOR_ARM, DONOR_ARM_END, 2))
            edges = []
            for i in md.disasm(bytes(ov[_off(FIELD_FN):_off(0x021B2B70)]), FIELD_FN):
                if i.mnemonic.startswith("b") and i.op_str.startswith("#"):
                    tgt = int(i.op_str[1:], 0)
                    if tgt in inside and not (DONOR_ARM <= i.address < DONOR_ARM_END):
                        edges.append((i.address, i.mnemonic, tgt))
            assert edges == [(ARM_ENTRY_BRANCH, "b", DONOR_ARM)], (
                f"the donor's arm is not exclusively its own: {[(hex(a), m, hex(t)) for a, m, t in edges]}")


        def _rows(ov, base: int, count: int, stride: int, key_size: int = 2) -> list[int]:
            """The key column of a sorted table, as a list."""
            fmt = "<H" if key_size == 2 else "<I"
            return [struct.unpack_from(fmt, ov, _off(base) + i * stride)[0]
                    for i in range(count)]


        def _drop_and_insert(ov, base: int, count: int, stride: int, key_size: int,
                             drops: tuple[int, ...], new_rows: list[bytes], label: str) -> int:
            """Count-neutral sorted insert: remove *drops*, splice *new_rows* in order.

            The array keeps its exact length and stays sorted, which is what every
            binary search over it requires.  Returns the index the first new row landed
            at.  Idempotent: if the donor is already present the table is left alone.
            """
            assert len(drops) == len(new_rows), "insert must be count-neutral"
            keys = _rows(ov, base, count, stride, key_size)
            fmt = "<H" if key_size == 2 else "<I"
            new_keys = [struct.unpack_from(fmt, r, 0)[0] for r in new_rows]
            donor = new_keys[0]

            def groups(ks: list[int]) -> dict[int, int]:
                """cid -> how many rows it owns (all of a cid's rows are adjacent)."""
                out: dict[int, int] = {}
                for k in ks:
                    out[k] = out.get(k, 0) + 1
                return out

            before = groups(keys)

            if donor in keys:                                          # already applied
                at = keys.index(donor)
                print(f"{label}: 0x{donor:04X} already present at {at} -> no change")
                return at

            blob = bytearray(ov[_off(base):_off(base) + count * stride])
            rows = [bytes(blob[i * stride:(i + 1) * stride]) for i in range(count)]

            for d in drops:
                hits = [i for i, k in enumerate(keys) if k == d]
                assert hits, f"{label}: phantom 0x{d:04X} is not in the table"
                i = hits[-1]                       # the last copy: never the leftmost record
                del rows[i]
                del keys[i]

            at = 0
            while at < len(keys) and keys[at] < donor:
                at += 1
            rows[at:at] = new_rows
            assert len(rows) == count, f"{label}: insert was not count-neutral"

            out = b"".join(rows)
            final = [struct.unpack_from(fmt, out, i * stride)[0] for i in range(count)]
            assert all(final[i] <= final[i + 1] for i in range(count - 1)), \
                f"{label}: the table is no longer sorted after the insert"
            # The check a generic table editor misses: find_event_handler reaches a cid's
            # SECOND record via `leftmost + 1` (dispatch.find_event_handler_second_record),
            # so a foreign row wedged into a multi-row group would silently orphan it.
            after = groups(final)
            for cid, n in before.items():
                if cid in drops:
                    continue
                assert after.get(cid) == n, (
                    f"{label}: cid 0x{cid:04X} owned {n} row(s) before the edit and "
                    f"{after.get(cid)} after -- a group was split")
            ov[_off(base):_off(base) + count * stride] = out
            print(f"{label}: dropped {', '.join(f'0x{d:04X}' for d in drops)}, "
                  f"inserted 0x{donor:04X} at {at} (count still {count})")
            return at


        def build_l2_stub(base: int = STUB_BASE) -> bytes:
            """PART I -- give the donor L2 membership without touching the packed list.

            ``0x02234E78`` (the param provider) decides a step's criteria ROW: for a cid
            in the list at ``L2_BASE`` it returns ``1 << 28``, which is exactly the bit
            LIST B tests at 0x02243C10 to pick row 1.  The list cannot grow (the bytes
            after it are the next packed cid list) and holds no phantom to evict -- but
            it is reached through exactly ONE call, the ``bl 0x02022E14`` at
            ``L2_SEARCH_SITE``, and its base has exactly one aligned reference in the
            whole image.  So retarget that one call at a cid-scoped stub: report "found"
            for the donor, otherwise tail-call the engine's own search and return its
            verdict byte-for-byte.  (The Azure-Eyes PART G pattern.)

                push {lr}
                ldr  r3,=0x1C8B
                cmp  r0,r3            ; r0 = the cid being searched for
                bne  native
                adds r0,r1,#0         ; "found" -- r1 is the list base, a valid non-NULL
                pop  {pc}             ;            pointer; the caller only tests != 0
            native:
                ldr  r3,=0x02022E15
                blx  r3
                pop  {pc}
            """
            assert (base + 0x14) % 4 == 0, "literal pool must be word aligned"
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R0, R3")
            b.insn("BNE", "native")
            b.insn("ADD", "R0, R1, #0x0")
            b.insn("POP", "{PC}")
            b.label("native")
            b.ldr_const(3, L2_SEARCH_FN | 1)
            b.insn("BLX", "R3")
            b.insn("POP", "{PC}")
            blob = b.assemble(base)                  # default pad="zero": 0x0000 before the pool
            assert len(blob) == 0x1C, f"stub is {len(blob)} B, expected 28"
            assert base + len(blob) <= STUB_END, (
                f"the stub is {len(blob)} B but only {STUB_END - base} B of the donor's "
                f"arm are dead")
            # never trust a bare capstone disasm: Thumb-2 would assemble and then freeze
            assert_thumb1_only(blob[:0x14], base)
            return blob


        def build_gdw_condition(base: int) -> bytes:
            """PART N -- slot3: once per turn AND at least one Fiend in the Graveyard.

            Bug 1: 0x021F01C1 is the BARE once-per-turn gate, and with slot2 == 0 nothing
            checked that a banish candidate existed -- so the card was activatable with an
            empty Graveyard and the engine froze.  This keeps 0x021F01C1's body and adds
            a candidate count against criteria ROW 1 (the GY row), selected by a param
            with bit 28 set -- the LIST B rule.

            ⚠️ IT DELIBERATELY DOES *NOT* TEST THE HAND.  An earlier build did, with
            `0x02243FE0(side, cid, 0)`, and it made the card completely unactivatable
            (in-game 2026-08-25, diagnosed from the user's .ml2).  FOR A HAND-FAMILY ROW
            THE PARAM IS THE CANDIDATE *INDEX*, NOT A ROW SELECTOR, and the caller has to
            iterate -- the shared slot3 0x021F02E4 loops r4 = 0 .. player[+0x0C]-1.  A
            bare 0 asks only "is hand slot ZERO a Fiend?", and hand slot 0 was Pot of
            Duality.  GY rows use the param as a row selector (Book of Life passes 0 then
            1), which is why the GY test below is correct as written.  See
            dispatch.candidate_count_param_is_family_dependent.
            """
            assert base % 4 == 0, "the literal pool needs a word-aligned base"
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x3]")
            b.ldr_const(2, ONCE_PER_TURN_KEY)
            b.bl(RIDER_WALKER)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "reject")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.ldr_const(1, DONOR_CID)
            b.ldr_const(2, ROW1_PARAM)
            b.bl(CRITERIA_COUNT_FN)
            b.insn("CMP", "R0, #0x0")
            b.insn("BLE", "reject")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, PC}")
            b.label("reject")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            blob = b.assemble(base)                  # code is 0x28 B, pool follows with no pad
            assert len(blob) == 0x34, f"condition blob is {len(blob)} B, expected 0x34"
            assert_thumb1_only(blob[:0x28], base)
            return blob


        def build_gdw_mover(base: int) -> bytes:
            """PART P -- make the donor's discard an EFFECT discard, not a cost one.

            ⭐ THE WHOLE COST/EFFECT DISTINCTION IS ONE ARGUMENT.  0x021C6D90 and
            0x021C6DB4 are the same function twice, byte-identical except that the former
            inserts `movs r0,#2` so that `[sp+4] = 2` where the latter leaves 1:

                0x021C6DB4  ... movs r0,#1 ; str r0,[sp] ; str r0,[sp,#4]   ; kind 1 COST
                0x021C6D90  ... movs r0,#1 ; str r0,[sp] ;
                                movs r0,#2 ; str r0,[sp,#4]                 ; kind 2 EFFECT

            Both then call 0x021C6B00(side, slot, 0, dest 0x0E) with source zone 0x0B, and
            inside it that word arrives as [sp,#0x4C] and is handed to
            0x021D1300(reason, &desc, r2, KIND) at 0x021C6CB8 -- the relocation event that
            "if this card is discarded to the Graveyard by a card effect" listens for.
            0x021C6D90 has exactly ONE caller in the image, 0x02259F42, inside the discard
            UI's request fulfilment, chosen over 0x021C6DB4 by a flag at 0x02259F3C.

            CONSEQUENCE: we do NOT need the request-based discard at all.  Keep the
            criteria-filtered picker -- slot5 0x021E4EED, which in-game test #1 proved
            offers only Fiends via criteria ROW 0 -- and simply swap its mover.  That is
            also what the 3DS does structurally: Gates 0x25F3 registers a criteria-carrying
            component for BOTH zones (hand handler 0x004A9EFC passes the word 0x18000002 to
            the registrar 0x004B16B4), rather than using an unfiltered discard request.

            0x021E4EED is shared by 19 records, so the swap is cid-scoped.  At its
            `bl 0x021C6DB4` (0x021E4F66) r5 still holds the DESCRIPTOR (set at 0x021E4EF0
            and used again at 0x021E4F6A `ldrh r1,[r5]`), so the trampoline reads the
            acting cid straight out of it.  r0/r1 are the mover's own arguments and are
            passed through untouched.

                push {lr}
                ldrh r2,[r5]          ; the acting card's cid
                ldr  r3,=DONOR_CID
                cmp  r2,r3
                bne  native
                ldr  r3,=0x021C6D91   ; the EFFECT mover  (kind 2)
                blx  r3
                pop  {pc}
            native:
                ldr  r3,=0x021C6DB5   ; the native COST mover (kind 1), byte-for-byte
                blx  r3
                pop  {pc}
            """
            assert base % 4 == 0, "the literal pool needs a word-aligned base"
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.insn("LDRH", "R2, [R5, #0x0]")         # the acting cid
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R2, R3")
            b.insn("BNE", "native")
            b.insn("MOV", "R2, #0x0")                # the 3rd arg
            b.ldr_const(3, DISCARD_MOVER_EFFECT | 1)
            b.insn("BLX", "R3")
            b.insn("POP", "{PC}")
            b.label("native")
            b.ldr_const(3, DISCARD_MOVER_COST | 1)
            b.insn("BLX", "R3")
            b.insn("POP", "{PC}")
            blob = b.assemble(base)
            assert len(blob) == 0x24, f"mover trampoline is {len(blob)} B"
            assert_thumb1_only(blob[:0x16], base)
            return blob


        def _bl_words(site: int, target: int) -> tuple[int, int]:
            """The two halfwords of an ARMv4T long `BL` at *site* targeting *target*."""
            delta = (target & ~1) - (site + 4)
            assert -(1 << 22) <= delta < (1 << 22), f"BL 0x{site:08X} -> 0x{target:08X} too far"
            return (0xF000 | ((delta >> 12) & 0x7FF), 0xF800 | ((delta >> 1) & 0x7FF))


        def _trig_row_addr(row: int) -> int:
            return TRIG_BASE + row * 8


        def _cls1_row_addr(row: int) -> int:
            return CLS1_BASE + row * CLS1_STRIDE


        def _cls1_row_of(ov, cid: int) -> int:
            """The index of *cid*'s cls1 record, found BY CID.

            cls1 is shared: other patches in the chain do count-neutral swaps that shift
            row indices, so the base-ROM index is only a hint.  Asserts the cid owns
            exactly one record, which is also the leftmost-record guard
            (find_event_handler reaches a second record via `leftmost + 1`).
            """
            cids = [struct.unpack_from("<I", ov, _off(CLS1_BASE) + i * CLS1_STRIDE)[0] & 0xFFFF
                    for i in range(CLS1_COUNT)]
            hits = [i for i, c in enumerate(cids) if c == cid]
            assert len(hits) == 1, (
                f"cls1 holds {len(hits)} records for 0x{cid:04X}, expected exactly 1")
            return hits[0]


        # ---------------------------------------------------------------------------
        # PART E (ARM9, needs its own ROM round-trip)
        # ---------------------------------------------------------------------------
        def apply_gb_setcode(out_path: str) -> None:
            """The two ARM9 set-code table edits, in ONE ROM round-trip.

            PART E -- drop the donor from "Gladiator Beast".  Count-neutral: the table
            stays 29 strictly-ascending entries (the consumer hardcodes ``movs r2,#0x1D``),
            the donor is shifted out and the freed tail slot gets 0xFFFF -- above every
            real cid (0x0D48..0x24E8), so the pure binary search can never match it.

            PART E2 -- join "Dark World".  Count-neutral over the phantom 0x0EC9: the
            table stays 16 strictly-ascending entries (``movs r2,#0x10``) and the donor
            lands between Renge 0x1C18 and Dark World Grimoire 0x1D25.  WITHOUT THIS the
            card is not a "Dark World" card to the engine, and an archetype search
            (Snoww's aux 0x000F row) cannot fetch it --.

            Both edits are idempotent and both are asserted against the consumers' own
            pinned literals before anything is written.
            """
            rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
            d = bytearray(sec.data)

            def off(addr: int) -> int:
                return addr - ARM9_BASE

            ptr = struct.unpack_from("<I", d, off(GB_TBL_POOL))[0]
            assert ptr == GB_TBL, (
                f"Gladiator Beast consumer pool @0x{GB_TBL_POOL:08X} = 0x{ptr:08X} "
                f"(expected 0x{GB_TBL:08X}); wrong base ROM?")
            imm = struct.unpack_from("<H", d, off(GB_COUNT_IMM))[0]
            assert imm == (0x2200 | GB_COUNT), (
                f"Gladiator Beast count imm @0x{GB_COUNT_IMM:08X} = 0x{imm:04X} "
                f"(expected movs r2,#0x{GB_COUNT:02X})")

            cur = list(struct.unpack_from(f"<{GB_COUNT}H", d, off(GB_TBL)))
            if DONOR_CID not in cur:                                  # idempotent
                print(f"E  Gladiator Beast set-code: 0x{DONOR_CID:04X} already absent -> no change")
            else:
                assert all(cur[i] < cur[i + 1] for i in range(len(cur) - 1)), \
                    "Gladiator Beast table is not strictly sorted in the base ROM"

                new = [c for c in cur if c != DONOR_CID] + [GB_FILLER]
                assert len(new) == GB_COUNT and all(new[i] < new[i + 1] for i in range(len(new) - 1)), \
                    f"resulting table is not a sorted {GB_COUNT}-entry set: {[hex(x) for x in new]}"
                struct.pack_into(f"<{GB_COUNT}H", d, off(GB_TBL), *new)
                sec.data = bytes(d)
                print(f"E  Gladiator Beast set-code @0x{GB_TBL:08X}: dropped 0x{DONOR_CID:04X}, "
                      f"count still {GB_COUNT}, tail filler 0x{GB_FILLER:04X}")

            # -- PART E2: join the "Dark World" set-code table -------------------------
            # Same ROM round-trip as PART E: this is a 129 MB save, do it once.
            ptr = struct.unpack_from("<I", d, off(DW_TBL_POOL))[0]
            assert ptr == DW_TBL, (
                f"Dark World consumer pool @0x{DW_TBL_POOL:08X} = 0x{ptr:08X} "
                f"(expected 0x{DW_TBL:08X}); wrong base ROM?")
            imm = struct.unpack_from("<H", d, off(DW_COUNT_IMM))[0]
            assert imm == (0x2200 | DW_COUNT), (
                f"Dark World count imm @0x{DW_COUNT_IMM:08X} = 0x{imm:04X} "
                f"(expected movs r2,#0x{DW_COUNT:02X})")

            cur = list(struct.unpack_from(f"<{DW_COUNT}H", d, off(DW_TBL)))
            if DONOR_CID in cur:                                      # idempotent
                print(f"E2 Dark World set-code: 0x{DONOR_CID:04X} already present -> no change")
            else:
                assert all(cur[i] < cur[i + 1] for i in range(len(cur) - 1)), \
                    "Dark World table is not strictly sorted in the base ROM"
                assert DW_DROP_PHANTOM in cur, (
                    f"the phantom 0x{DW_DROP_PHANTOM:04X} is not in the Dark World table -- "
                    f"another patch already spent this slot")
                new = sorted(c for c in cur if c != DW_DROP_PHANTOM)
                new = sorted(new + [DONOR_CID])
                assert len(new) == DW_COUNT and all(new[i] < new[i + 1] for i in range(len(new) - 1)), \
                    f"resulting table is not a sorted {DW_COUNT}-entry set: {[hex(x) for x in new]}"
                struct.pack_into(f"<{DW_COUNT}H", d, off(DW_TBL), *new)
                sec.data = bytes(d)
                print(f"E2 Dark World set-code @0x{DW_TBL:08X}: dropped phantom "
                      f"0x{DW_DROP_PHANTOM:04X}, inserted 0x{DONOR_CID:04X} @{new.index(DONOR_CID)}, "
                      f"count still {DW_COUNT} and strictly sorted")

            rom.arm9 = mc.save()
            rom.saveToFile(out_path)


        # ---------------------------------------------------------------------------
        # clause 2 (overlay 3 only -- five edits, four of them pure data)
        # ---------------------------------------------------------------------------
        def apply_clause2(ov: bytearray) -> None:
            """PARTS G-K: the once-per-turn banish / discard / draw ignition."""
            # -- PART G: the two criteria rows -----------------------------------------
            row_hand = struct.pack("<HHIHH", DONOR_CID, CRIT_NO_ARCHETYPE, HANDLER_HAND,
                                   CRIT_FLAGS, CRIT_EXTRA_FIEND)
            row_gy = struct.pack("<HHIHH", DONOR_CID, CRIT_NO_ARCHETYPE, HANDLER_GY,
                                 CRIT_FLAGS, CRIT_EXTRA_FIEND)
            # both must be byte-identical to the shipped rows they were copied from
            for cid, want in ((0x1FB5, row_hand), (0x1466, row_gy)):
                keys = _rows(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE)
                i = keys.index(cid)
                got = bytes(ov[_off(CRIT_BASE) + i * CRIT_STRIDE + 2:
                               _off(CRIT_BASE) + (i + 1) * CRIT_STRIDE])
                assert got == want[2:], (
                    f"G  the reference row for 0x{cid:04X} is {got.hex()}, expected "
                    f"{want[2:].hex()}; wrong base ROM?")
            _drop_and_insert(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, 2,
                             CRIT_DROP, [row_hand, row_gy],
                             "G  criteria rows (0 = hand/Fiend, 1 = GY/Fiend)")

            # -- PART H: LIST B membership ---------------------------------------------
            imm = struct.unpack_from("<H", ov, _off(LISTB_COUNT_IMM))[0]
            assert imm == (0x2200 | LISTB_COUNT), (
                f"H  list-B count imm @0x{LISTB_COUNT_IMM:08X} is {imm:#06x}, "
                f"expected movs r2,#0x{LISTB_COUNT:02X}")
            _drop_and_insert(ov, LISTB_BASE, LISTB_COUNT, 2, 2,
                             (LISTB_DROP,), [struct.pack("<H", DONOR_CID)],
                             "H  LIST B (row = param & 0x10000000)")

            # -- PART I: L2 membership, as a cid-scoped stub ---------------------------
            imm = struct.unpack_from("<H", ov, _off(L2_COUNT_IMM))[0]
            assert imm == (0x2200 | L2_COUNT), (
                f"I  L2 count imm @0x{L2_COUNT_IMM:08X} is {imm:#06x}, "
                f"expected movs r2,#0x{L2_COUNT:02X}")
            stub = build_l2_stub()
            cur = bytes(ov[_off(STUB_BASE):_off(STUB_BASE) + len(stub)])
            if cur != stub:
                assert cur == NATIVE_ARM[14:14 + len(stub)], (
                    "I  the donor's dead arm space is not in its native state -- "
                    "something else has claimed it")
                ov[_off(STUB_BASE):_off(STUB_BASE) + len(stub)] = stub
                print(f"I  L2 membership stub: {len(stub)} B @0x{STUB_BASE:08X} "
                      f"(the donor's dead arm space, {STUB_END - STUB_BASE} B)")
            else:
                print(f"I  L2 membership stub already written @0x{STUB_BASE:08X}")

            want = _bl_words(L2_SEARCH_SITE, STUB_BASE)
            got = struct.unpack_from("<HH", ov, _off(L2_SEARCH_SITE))
            if got != want:
                assert got == _bl_words(L2_SEARCH_SITE, L2_SEARCH_FN), (
                    f"I  0x{L2_SEARCH_SITE:08X} is not the native `bl 0x{L2_SEARCH_FN:08X}` "
                    f"({got[0]:#06x} {got[1]:#06x}); wrong base ROM?")
                struct.pack_into("<HH", ov, _off(L2_SEARCH_SITE), *want)
                print(f"I  retargeted the L2 lookup `bl` @0x{L2_SEARCH_SITE:08X}: "
                      f"0x{L2_SEARCH_FN:08X} -> 0x{STUB_BASE:08X}")
            else:
                print(f"I  L2 lookup @0x{L2_SEARCH_SITE:08X} already retargeted")

            # -- PART J: the cls3 record -----------------------------------------------
            # slot5 is 0: the discard moved into the RESOLVER (PART M), because a COST
            # discard does not trigger Dark World monsters.  slot3 is our own gate (N).
            # The test-#1 shape (which banished, offered ONLY Fiends, and drew) with our
            # own slot3 gate.  The discard is back in slot5: PART P makes its RELOCATION
            # an effect discard, so Dark World monsters trigger without moving the pick
            # into the resolver.
            rec = struct.pack("<6I", DONOR_CID, SLOT1_DRAW, 0,
                              ov5_cave.CAVE_GDW_COND | 1, SLOT4_BANISH_GY,
                              SLOT5_DISCARD_HAND)
            _drop_and_insert(ov, CLS3_BASE, CLS3_COUNT, CLS3_STRIDE, 4,
                             (CLS3_DROP,), [rec], "J  cls3 record")

            # -- PART L: WITHDRAWN -----------------------------------------------------
            # This used to insert the donor into 0x0228EF48, the "my HAND selection is
            # filtered by my criteria row" list, on the theory that it would filter the
            # effect discard.  IN-GAME TEST #3 SHOWED IT DOES NOTHING HERE, and the
            # savestate said why: 0x0225A3F0 keys that lookup on [0x0229DE94+0x0A], which
            # the request-driven discard never sets to our cid (it read 0x0004 -- that
            # field is written with the PICKED HAND INDEX by 0x02259EE0).  The insert also
            # spent the 2 B alignment pad at 0x0228EF86, which is a scarce resource, so it
            # is reverted rather than left in as a no-op.  PART O does the filtering.

            # -- PART P: upgrade the donor's discard from a COST to an EFFECT move -----
            want = _bl_words(DISCARD_MOVER_SITE, ov5_cave.CAVE_GDW_MOVER)
            got = struct.unpack_from("<HH", ov, _off(DISCARD_MOVER_SITE))
            if got == want:
                print(f"P  discard mover @0x{DISCARD_MOVER_SITE:08X} already retargeted")
            else:
                assert got == _bl_words(DISCARD_MOVER_SITE, DISCARD_MOVER_COST), (
                    f"P  0x{DISCARD_MOVER_SITE:08X} is not the native "
                    f"`bl 0x{DISCARD_MOVER_COST:08X}`; wrong base ROM?")
                # the two movers must still differ ONLY by the kind word
                assert struct.unpack_from("<H", ov, _off(0x021C6D80))[0] == 0x9001,             "P  0x021C6D58 no longer writes relocation kind 0"
                assert struct.unpack_from("<H", ov, _off(0x021C6DC4))[0] == 0x2001,             "P  0x021C6DB4 no longer writes kind 1"
                struct.pack_into("<HH", ov, _off(DISCARD_MOVER_SITE), *want)
                print(f"P  discard mover @0x{DISCARD_MOVER_SITE:08X}: "
                      f"0x{DISCARD_MOVER_COST:08X} -> 0x{ov5_cave.CAVE_GDW_MOVER:08X} "
                      f"(cid-scoped: effect move for the donor only)")

            # -- PART K: the draw count ------------------------------------------------
            imm = struct.unpack_from("<H", ov, _off(DRAW_COUNT_IMM))[0]
            assert imm == (0x2200 | DRAW_COUNT), (
                f"K  draw-count table imm @0x{DRAW_COUNT_IMM:08X} is {imm:#06x}, "
                f"expected movs r2,#0x{DRAW_COUNT:02X}")
            _drop_and_insert(ov, DRAW_BASE, DRAW_COUNT, DRAW_STRIDE, 2,
                             (DRAW_DROP,), [struct.pack("<Hh", DONOR_CID, DRAW_N)],
                             f"K  draw count = {DRAW_N}")


        # ---------------------------------------------------------------------------
        # PARTS M / N (overlay 5 -- needs its own ROM round-trip)
        # ---------------------------------------------------------------------------
        def apply_ov5_stubs(out_path: str) -> None:
            """Install the slot1 resolver and the slot3 activation gate in the ov5 cave.

            Idempotent: a slot already holding the blob is left alone.  ov5 is NOT mapped
            in a puzzle (overlay 41 loads over it), so both stubs are normal-duel-only --
            the accepted default for injected code.  Clause 1 is overlay-3 and unaffected.
            """
            rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
            wrote = False
            for addr, reserve, build, what in (
                    (ov5_cave.CAVE_GDW_COND, 0x50, build_gdw_condition,
                     "N  slot3 gate (once per turn + at least one Fiend in the GY)"),
                    (ov5_cave.CAVE_GDW_MOVER, 0x40, build_gdw_mover,
                     "P  discard mover (cost -> EFFECT, cid-scoped)")):
                blob = build(addr)
                if ov5_cave.read_cave(rom, addr, len(blob)) == blob:
                    print(f"{what}: already installed @0x{addr:08X}")
                    continue
                ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                wrote = True
                print(f"{what}: {len(blob)} B @0x{addr:08X}")
            if wrote:
                rom.saveToFile(out_path)
                print(f"   wrote ov5 cave stubs -> {out_path}")


        # ---------------------------------------------------------------------------
        # main
        # ---------------------------------------------------------------------------

        def install(rom, view):
            ov = view.buf
            # -- PART A: clause 1 -- the field-spell stat arm --------------------------
            _check_arm_is_exclusive(ov)
            print(f"A  donor arm 0x{DONOR_ARM:08X}..0x{DONOR_ARM_END:08X} "
                  f"({DONOR_ARM_END - DONOR_ARM} B) has exactly one inbound edge "
                  f"(b @0x{ARM_ENTRY_BRANCH:08X})")

            tail = bytes(ov[_off(PLUS300_TAIL):_off(PLUS300_TAIL) + len(PLUS300_TAIL_BYTES)])
            assert tail == PLUS300_TAIL_BYTES, (
                f"Jurassic World's +300/+300 tail @0x{PLUS300_TAIL:08X} changed "
                f"({tail.hex()}); wrong base ROM?")
            print(f"A  +300/+300 tail @0x{PLUS300_TAIL:08X} intact (Jurassic World 0x1AA7's own)")

            blob = build_fiend_block()
            cur = bytes(ov[_off(DONOR_ARM):_off(DONOR_ARM) + len(blob)])
            if cur != blob:
                assert bytes(ov[_off(DONOR_ARM):_off(DONOR_ARM_END)]) == NATIVE_ARM, (
                    "the donor's field arm is not in its native state; wrong base ROM?")
                ov[_off(DONOR_ARM):_off(DONOR_ARM) + len(blob)] = blob
                print(f"A  wrote {len(blob)} B Fiend +300/+300 block @0x{DONOR_ARM:08X} "
                      f"(race bit {RACE_BIT_FIEND} = Fiend); "
                      f"{DONOR_ARM_END - DONOR_ARM - len(blob)} B left dead")
            else:
                print(f"A  Fiend block @0x{DONOR_ARM:08X} already written")

            # -- PART B: kill the counter-accrual arm call -----------------------------
            site = struct.unpack_from("<H", ov, _off(COUNTER_ARM_SITE))[0]
            assert 0x4800 <= site <= 0x4FFF, (
                f"0x{COUNTER_ARM_SITE:08X} is not an `ldr rX,[pc,#imm]` ({site:#06x})")
            cur_cid = struct.unpack_from("<I", ov, _off(COUNTER_ARM_POOL))[0]
            assert cur_cid in (DONOR_CID, DEAD_CID), (
                f"counter arm pool @0x{COUNTER_ARM_POOL:08X} = 0x{cur_cid:08X}, "
                f"expected the donor cid; wrong base ROM?")
            struct.pack_into("<I", ov, _off(COUNTER_ARM_POOL), DEAD_CID)
            print(f"B  counter arm literal @0x{COUNTER_ARM_POOL:08X} "
                  f"(bl 0x{COUNTER_ARM_FN:08X} @0x{COUNTER_ARM_SITE:08X}): "
                  f"0x{DONOR_CID:04X} -> 0x{DEAD_CID:04X}")

            # -- PART C: retire the continuous-trigger registry row --------------------
            ra = _trig_row_addr(TRIG_ROW)
            hnd, cid = struct.unpack_from("<II", ov, _off(ra))
            assert hnd == TRIG_HANDLER, (
                f"trigger registry row {TRIG_ROW} handler is 0x{hnd:08X}, "
                f"expected 0x{TRIG_HANDLER:08X}; wrong base ROM?")
            assert cid in (DONOR_CID, DEAD_CID), (
                f"trigger registry row {TRIG_ROW} cid is 0x{cid:04X}, expected the donor")
            assert DEAD_CID != 0, "cid 0 in the trigger registry means UNCONDITIONAL -- never use it"
            struct.pack_into("<I", ov, _off(ra) + 4, DEAD_CID)
            print(f"C  trigger registry row {TRIG_ROW} @0x{ra:08X}: "
                  f"cid 0x{DONOR_CID:04X} -> 0x{DEAD_CID:04X} (count still {TRIG_COUNT})")

            # -- PART D: retire the donor's cls1 record --------------------------------
            # BY CID, not by index: cls1 shifts under us in the combined chain.
            row = _cls1_row_of(ov, DONOR_CID)
            ca = _cls1_row_addr(row)
            rec = struct.unpack_from("<6I", ov, _off(ca))
            assert rec[0] == DONOR_CID, "cls1 lookup by cid returned the wrong record"
            assert rec[1:] in (NATIVE_CLS1, DEAD_CLS1), (
                f"cls1[{CLS1_ROW}] is not in its native state: "
                f"{' '.join(f'0x{v:08X}' for v in rec[1:])}")
            struct.pack_into("<6I", ov, _off(ca), DONOR_CID, *DEAD_CLS1)
            print(f"D  cls1[{row}] @0x{ca:08X} retired (cid kept so cls1 stays "
                  f"sorted at {CLS1_COUNT}){'' if row == CLS1_ROW else f' [base-ROM index was {CLS1_ROW}]'}")

            cls1_cids = [struct.unpack_from("<I", ov, _off(CLS1_BASE) + i * CLS1_STRIDE)[0]
                         for i in range(CLS1_COUNT)]
            assert all(cls1_cids[i] <= cls1_cids[i + 1] for i in range(len(cls1_cids) - 1)), \
                "cls1 is no longer sorted -- find_event_handler would break"

            apply_clause2(ov)

        def apply_legacy_text(out):
            write_text = True
            rom2 = ndspy.rom.NintendoDSRom.fromFile(out)
            fid, pac_data, archive = _open_pac(rom2)
            _, card_index = _find_prop(bytes(pac_data), archive, DONOR_CID)

            if write_text:
                pad_cursor: dict = {}
                for L in TEXT_LANGS:
                    idxf = next((f for f in archive.files
                                 if f.get_clean_name().lower() == f"card_indx_{L}.bin"), None)
                    namef = next((f for f in archive.files
                                  if f.get_clean_name().lower() == f"card_name_{L}.bin"), None)
                    descf = next((f for f in archive.files
                                  if f.get_clean_name().lower() == f"card_desc_{L}.bin"), None)
                    if not (idxf and namef and descf):
                        print(f"F  [{L}] missing name/desc/index file -> skipped")
                        continue
                    recoff = idxf.address + 8 + card_index * 8
                    old_name_off, old_desc_off = struct.unpack_from("<II", pac_data, recoff)
                    old_name = _read_cstr(pac_data, namef.address + old_name_off)

                    n = place_string(pac_data, namef.address, namef.size,
                                      old_name_off, NEW_NAME, pad_cursor)
                    d = place_string(pac_data, descf.address, descf.size,
                                      old_desc_off, NEW_DESC, pad_cursor)
                    if n is not None:
                        struct.pack_into("<I", pac_data, recoff, n)
                    if d is not None:
                        struct.pack_into("<I", pac_data, recoff + 4, d)
                    n_note = ("in-place" if n == old_name_off
                              else f"relocated->0x{n:X}" if n is not None else "KEPT: no room")
                    d_note = ("in-place" if d == old_desc_off
                              else f"relocated->0x{d:X}" if d is not None else "KEPT: no room")
                    print(f"F  [{L}] name {old_name.decode('latin1')!r} -> "
                          f"{NEW_NAME.decode()!r} ({n_note}); desc ({d_note})")

                rom2.files[fid] = bytes(pac_data)
                rom2.saveToFile(out)
                print(f"   wrote name/desc edits -> {out}")

        def check_fn(c, rom, view):
            _rom, ov = rom, bytearray(view.buf)

            def check(cond: bool, msg: str) -> None:
                c.ok(bool(cond), msg)

            # PART A -- the clause-1 block, and the tail it depends on
            blob = build_fiend_block()
            got = bytes(ov[_off(DONOR_ARM):_off(DONOR_ARM) + len(blob)])
            check(got == blob,
                  f"A  Fiend +300/+300 block @0x{DONOR_ARM:08X} ({len(blob)} B, race bit "
                  f"{RACE_BIT_FIEND} = Fiend)")
            tail = bytes(ov[_off(PLUS300_TAIL):_off(PLUS300_TAIL) + len(PLUS300_TAIL_BYTES)])
            check(tail == PLUS300_TAIL_BYTES,
                  f"A  Jurassic World's +300/+300 tail @0x{PLUS300_TAIL:08X} unchanged")
            # the switch still routes the donor's cid at this arm
            entry = struct.unpack_from("<H", ov, _off(ARM_ENTRY_BRANCH))[0]
            check(entry == _b_imm11(ARM_ENTRY_BRANCH, DONOR_ARM),
                  f"A  switch still branches 0x{ARM_ENTRY_BRANCH:08X} -> 0x{DONOR_ARM:08X}")
            # and the six classic field spells are untouched (they share the engine)
            siblings = {0x10F0: 0x021B2856, 0x10F1: 0x021B2866, 0x10F2: 0x021B2872,
                        0x10F3: 0x021B287C, 0x10F4: 0x021B2888, 0x10F5: 0x021B28A0,
                        0x1AA7: 0x021B28C2}
            jt = [0x021B2766 + struct.unpack_from("<H", ov, _off(0x021B2764) + 2 * k)[0]
                  for k in range(6)]
            check(jt == [siblings[0x10F0 + k] for k in range(6)],
                  "A  the six classic field spells still reach their own arms")
            check(struct.unpack_from("<H", ov, _off(0x021B28C2))[0] == 0x2102,
                  "A  Jurassic World's arm @0x021B28C2 unchanged")

            # PART B -- the counter-accrual arm call no longer names the donor
            v = struct.unpack_from("<I", ov, _off(COUNTER_ARM_POOL))[0]
            check(v == DEAD_CID,
                  f"B  counter arm literal @0x{COUNTER_ARM_POOL:08X} = 0x{v:04X} (donor dropped)")

            # PART C -- the trigger registry row is retired, geometry intact
            hnd, cid = struct.unpack_from("<II", ov, _off(_trig_row_addr(TRIG_ROW)))
            check(hnd == TRIG_HANDLER and cid == DEAD_CID,
                  f"C  trigger registry row {TRIG_ROW} retired (cid 0x{cid:04X}, handler kept)")
            live = [struct.unpack_from("<I", ov, _off(_trig_row_addr(i)) + 4)[0]
                    for i in range(TRIG_COUNT)]
            check(DONOR_CID not in live,
                  f"C  the donor owns no other trigger-registry row (of {TRIG_COUNT})")

            # PART D -- cls1 retired and still sorted
            _row = _cls1_row_of(ov, DONOR_CID)
            rec = struct.unpack_from("<6I", ov, _off(_cls1_row_addr(_row)))
            check(rec[0] == DONOR_CID and rec[1:] == DEAD_CLS1,
                  f"D  cls1[{_row}] retired (cid kept; found by cid, base index {CLS1_ROW})")
            cls1_cids = [struct.unpack_from("<I", ov, _off(CLS1_BASE) + i * CLS1_STRIDE)[0]
                         for i in range(CLS1_COUNT)]
            check(all(cls1_cids[i] <= cls1_cids[i + 1] for i in range(len(cls1_cids) - 1)),
                  f"D  cls1 still {CLS1_COUNT} sorted records")
            check(sum(1 for c in cls1_cids if c == DONOR_CID) == 1,
                  "D  the donor still owns exactly one cls1 record (no leftmost-record shadow)")

            # PART E -- the ARM9 set-code table
            rom2 = rom
            mc = ndspy.code.MainCodeFile(bytes(rom2.arm9), rom2.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
            d = bytes(sec.data)
            tbl = list(struct.unpack_from(f"<{GB_COUNT}H", d, GB_TBL - ARM9_BASE))
            check(DONOR_CID not in tbl and len(tbl) == GB_COUNT
                  and all(tbl[i] < tbl[i + 1] for i in range(len(tbl) - 1)),
                  f"E  Gladiator Beast table: donor dropped, still {GB_COUNT} sorted entries")
            check(struct.unpack_from("<H", d, GB_COUNT_IMM - ARM9_BASE)[0] == (0x2200 | GB_COUNT),
                  f"E  Gladiator Beast count immediate still movs r2,#0x{GB_COUNT:02X}")

            # PART E2 -- the ARM9 "Dark World" set-code table
            dw = list(struct.unpack_from(f"<{DW_COUNT}H", d, DW_TBL - ARM9_BASE))
            check(DONOR_CID in dw,
                  f"E2 Dark World set-code table holds the donor 0x{DONOR_CID:04X} -- the card IS a "
                  f"'Dark World' card, so an archetype search can fetch it")
            check(DW_DROP_PHANTOM not in dw,
                  f"E2 phantom 0x{DW_DROP_PHANTOM:04X} dropped (count-neutral)")
            check(len(dw) == DW_COUNT and all(dw[i] < dw[i + 1] for i in range(len(dw) - 1)),
                  f"E2 Dark World table still {DW_COUNT} STRICTLY sorted entries (it is binary-searched)")
            check(struct.unpack_from("<H", d, DW_COUNT_IMM - ARM9_BASE)[0] == (0x2200 | DW_COUNT),
                  f"E2 Dark World count immediate still movs r2,#0x{DW_COUNT:02X}")
            check(struct.unpack_from("<I", d, DW_TBL_POOL - ARM9_BASE)[0] == DW_TBL,
                  f"E2 the Dark World consumer still reads the table at 0x{DW_TBL:08X}")
            # the six native Dark World discard monsters must all still be members
            check(all(c in dw for c in (0x1965, 0x1966, 0x1968, 0x1969, 0x1B3E, 0x1B3F)),
                  "E2 the six native Dark World monsters are still in the set-code table")

            # PART F -- the card face
            fid, pac_data, archive = _open_pac(rom2)
            _, card_index = _find_prop(bytes(pac_data), archive, DONOR_CID)
            named, described = [], []
            for L in TEXT_LANGS:
                idxf = next((f for f in archive.files
                             if f.get_clean_name().lower() == f"card_indx_{L}.bin"), None)
                namef = next((f for f in archive.files
                              if f.get_clean_name().lower() == f"card_name_{L}.bin"), None)
                descf = next((f for f in archive.files
                              if f.get_clean_name().lower() == f"card_desc_{L}.bin"), None)
                if not (idxf and namef):
                    continue
                no, do = struct.unpack_from("<II", pac_data, idxf.address + 8 + card_index * 8)
                named.append(_read_cstr(pac_data, namef.address + no) == NEW_NAME)
                if descf:
                    described.append(_read_cstr(pac_data, descf.address + do) == NEW_DESC)
            check(bool(named) and all(named),
                  f"F  name reads {NEW_NAME.decode()!r} in all {len(named)} present languages")
            # clause 2 quadrupled the description; _place_string writes in place ONLY when
            # the new bytes fit, so a short donor slot would silently keep the old text
            check(bool(described) and all(described),
                  f"F  description reads the full printed text ({len(NEW_DESC)} B) in all "
                  f"{len(described)} present languages")
            # and the neighbouring card's description must not have been clipped
            others = []
            for L in TEXT_LANGS:
                idxf = next((f for f in archive.files
                             if f.get_clean_name().lower() == f"card_indx_{L}.bin"), None)
                descf = next((f for f in archive.files
                              if f.get_clean_name().lower() == f"card_desc_{L}.bin"), None)
                if not (idxf and descf):
                    continue
                for nb in (card_index - 1, card_index + 1):
                    do = struct.unpack_from("<I", pac_data, idxf.address + 8 + nb * 8 + 4)[0]
                    others.append(len(_read_cstr(pac_data, descf.address + do)) > 0)
            check(bool(others) and all(others),
                  "F  the adjacent cards' descriptions are still non-empty (no blob overrun)")

            # ---- clause 2 ----------------------------------------------------------
            # PART G -- two consecutive rows, hand first, and the registry still sorted
            keys = _rows(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE)
            mine = [i for i, k in enumerate(keys) if k == DONOR_CID]
            check(len(mine) == 2 and mine[1] == mine[0] + 1,
                  f"G  the donor owns exactly 2 consecutive criteria rows ({mine})")
            if len(mine) == 2:
                got = [bytes(ov[_off(CRIT_BASE) + i * CRIT_STRIDE:
                                _off(CRIT_BASE) + (i + 1) * CRIT_STRIDE]) for i in mine]
                want = [struct.pack("<HHIHH", DONOR_CID, CRIT_NO_ARCHETYPE, h,
                                    CRIT_FLAGS, CRIT_EXTRA_FIEND)
                        for h in (HANDLER_HAND, HANDLER_GY)]
                check(got == want,
                      f"G  row 0 = hand 0x{HANDLER_HAND:08X}, row 1 = GY 0x{HANDLER_GY:08X}, "
                      f"both Fiend (extra 0x{CRIT_EXTRA_FIEND:04X})")
            check(all(keys[i] <= keys[i + 1] for i in range(CRIT_COUNT - 1)),
                  f"G  criteria registry still {CRIT_COUNT} sorted rows")
            check(0x1FB5 in keys and 0x1466 in keys,
                  "G  the donor rows' reference cards still own their own rows")

            # PART H -- LIST B membership, sorted, count-neutral
            lb = _rows(ov, LISTB_BASE, LISTB_COUNT, 2)
            check(DONOR_CID in lb and LISTB_DROP not in lb,
                  f"H  LIST B holds 0x{DONOR_CID:04X} and no longer 0x{LISTB_DROP:04X}")
            check(len(lb) == LISTB_COUNT and all(lb[i] < lb[i + 1] for i in range(len(lb) - 1)),
                  f"H  LIST B still {LISTB_COUNT} strictly sorted entries")
            check(struct.unpack_from("<H", ov, _off(LISTB_COUNT_IMM))[0] == (0x2200 | LISTB_COUNT),
                  f"H  LIST B count immediate still movs r2,#0x{LISTB_COUNT:02X}")

            # PART I -- the membership stub and the single retargeted call
            stub = build_l2_stub()
            check(bytes(ov[_off(STUB_BASE):_off(STUB_BASE) + len(stub)]) == stub,
                  f"I  L2 membership stub ({len(stub)} B) @0x{STUB_BASE:08X}")
            check(STUB_BASE >= DONOR_ARM + 14 and STUB_BASE + len(stub) <= STUB_END,
                  "I  the stub lies wholly inside the donor's own dead arm space")
            check(struct.unpack_from("<HH", ov, _off(L2_SEARCH_SITE))
                  == _bl_words(L2_SEARCH_SITE, STUB_BASE),
                  f"I  the L2 lookup @0x{L2_SEARCH_SITE:08X} calls the stub")
            check(struct.unpack_from("<I", ov, _off(0x02235104))[0] == L2_BASE,
                  "I  the L2 list itself is untouched (its single pool reference intact)")
            check(struct.unpack_from("<H", ov, _off(L2_COUNT_IMM))[0] == (0x2200 | L2_COUNT),
                  f"I  L2 count immediate still movs r2,#0x{L2_COUNT:02X}")

            # PART J -- the cls3 record, and cls3 still sorted at its hard count
            c3 = _rows(ov, CLS3_BASE, CLS3_COUNT, CLS3_STRIDE, 4)
            check(c3.count(DONOR_CID) == 1,
                  "J  the donor owns exactly one cls3 record (no leftmost-record shadow)")
            if DONOR_CID in c3:
                r = struct.unpack_from("<6I", ov, _off(CLS3_BASE) + c3.index(DONOR_CID) * CLS3_STRIDE)
                check(r[1:] == (SLOT1_DRAW, 0, ov5_cave.CAVE_GDW_COND | 1,
                                SLOT4_BANISH_GY, SLOT5_DISCARD_HAND),
                      "J  cls3 slots +04 draw / +0C gate / +10 banish / +14 Fiend discard")
            check(all(c3[i] <= c3[i + 1] for i in range(CLS3_COUNT - 1)),
                  f"J  cls3 still {CLS3_COUNT} sorted records")

            # PART K -- the draw count
            dk = _rows(ov, DRAW_BASE, DRAW_COUNT, DRAW_STRIDE)
            check(dk.count(DONOR_CID) == 1, "K  the donor owns exactly one draw-count row")
            if DONOR_CID in dk:
                n = struct.unpack_from("<h", ov,
                                       _off(DRAW_BASE) + dk.index(DONOR_CID) * DRAW_STRIDE + 2)[0]
                check(n == DRAW_N, f"K  draw count = {n}")
            check(all(dk[i] < dk[i + 1] for i in range(DRAW_COUNT - 1)),
                  f"K  draw-count table still {DRAW_COUNT} strictly sorted rows")

            # the native functions clause 2 leans on must still be where we think
            for addr, name in ((SLOT4_BANISH_GY, "banish-from-GY cost"),
                               (SLOT5_DISCARD_HAND, "discard-from-hand cost"),
                               (SLOT1_DRAW, "draw-N resolver"),
                               (SLOT3_ONCE_PER_TURN, "once-per-turn gate")):
                check(RAM_BASE <= (addr & ~1) < RAM_BASE + len(ov) and addr & 1,
                      f"   {name} 0x{addr:08X} is a Thumb overlay-3 pointer")
            check(struct.unpack_from("<H", ov, _off(0x021E4F40))[0] == 0x2200,
                  "   the discard cost still hardcodes param 0 -> criteria ROW 0 (hand/Fiend)")

            # the engine entry points PARTS M/N/O lean on
            check(struct.unpack_from("<H", ov, _off(0x0222C31C))[0] == (0x2000 | NEXT_PHASE),
                  "   Bone Temple Block still returns NEXT_PHASE after posting the discard")

            # PART P -- the donor's discard now relocates as an EFFECT
            check(struct.unpack_from("<HH", ov, _off(DISCARD_MOVER_SITE))
                  == _bl_words(DISCARD_MOVER_SITE, ov5_cave.CAVE_GDW_MOVER),
                  f"P  discard mover @0x{DISCARD_MOVER_SITE:08X} calls the cid-scoped trampoline")
            check(struct.unpack_from("<H", ov, _off(0x021C6D7E))[0] == 0x2000
                  and struct.unpack_from("<H", ov, _off(0x021C6D80))[0] == 0x9001,
                  "P  0x021C6D58 still writes relocation kind 0 (the EFFECT discard)")
            check(struct.unpack_from("<H", ov, _off(0x021C6DC4))[0] == 0x2001,
                  "P  0x021C6DB4 still writes relocation kind 1 (COST)")
            check(struct.unpack_from("<H", ov, _off(0x021E4F40))[0] == 0x2200,
                  "P  the discard cost still hardcodes param 0 -> criteria ROW 0 (hand/Fiend)")

            # PARTS N / P -- the ov5 stubs
            rom3 = rom
            for addr, build, what in (
                    (ov5_cave.CAVE_GDW_COND, build_gdw_condition, "N  slot3 gate"),
                    (ov5_cave.CAVE_GDW_MOVER, build_gdw_mover, "P  discard mover")):
                blob = build(addr)
                check(ov5_cave.read_cave(rom3, addr, len(blob)) == blob,
                      f"{what} ({len(blob)} B) @0x{addr:08X}")
            check(struct.unpack_from("<H", ov, _off(0x021E531E))[0] == 0x2401,
                  "   the banish cost still defaults to r4 = 1 (banish exactly one)")
            check(struct.unpack_from("<I", ov, _off(0x021E5080))[0] == 0x00000FB6,
                  "   the banish cost still stamps the 0x0FB6 once-per-turn rider")


        return Compiled(installs=(install,), posts=(apply_ov5_stubs, apply_gb_setcode, apply_legacy_text),
                        checks=(check_fn,))


gates_effects = field_spell_fiend_monsters_gain_300_atk_def_banish_fiend_from_graveyard_discard_fiend_then_draw_1_once_per_turn

SPEC = card(0x1C8B, gates_effects())

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_gates_dark_world.nds")

DONOR_CID = 0x1C8B          # Colosseum - Cage of the Gladiator Beasts

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
