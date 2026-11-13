"""Ninja Grandmaster Hanzo (DARK / Warrior / Level 4 / 1800 / 1000) on Melchid the Four-Face Beast 0x13E7.

    When this card is Normal Summoned: You can add 1 "Ninjitsu Art" card from your Deck to your hand. When this card is
    Flip Summoned or Special Summoned: You can add 1 "Ninja" monster, except "Ninja Grandmaster Hanzo", from your Deck to
    your hand.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class normal_summon_add_ninjitsu_art_flip_or_special_summon_add_ninja_from_deck:
    """Ninja Grandmaster Hanzo (Melchid the Four-Face Beast 0x13E7): 'When Normal Summoned: add 1 "Ninjitsu Art" card from your Deck;
    when Flip or Special Summoned: add 1 other "Ninja" monster.' Summon-trigger lists code 7/8/9 over phantoms, a cls1 record cloned from
    Machina Gearframe, two ADJACENT criteria rows (rel 0 = Ninjitsu Art, any card type; rel 1 = Ninja, monsters only, except itself) that
    only work because the donor joins LIST A (row = leftmost + r4), "Ninjitsu Art" = repurposed inert set code 0x2A (ARM9 list swap) and
    "Ninja" membership displacing Armed Ninja 0x117B, and the criteria-param provider's first bsearch retargeted to an ov5 stub that picks
    the row from the event code. Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        import ndspy.code
        import ndspy.rom
        from otn_enhanced.effects.common import ARM9_BASE, ov3_off as _off
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid
        SETCODE_PTR_TABLE = 0x0209D0D8     # has_set_code pointer table; index N -> thunk for set code N
        HAS_SET_CODE = 0x020240D8          # has_set_code(r0=cid, r1=code); bounds-checks code < 0x70

        NA_SETCODE = 0x2A                  # the inert set-code index repurposed as "Ninjitsu Art"
        NA_THUNK = 0x02023B10              # its thunk (Thumb bit set in the pointer table)
        NA_COUNT_IMM = 0x02023B14          # `movs r2,#4` inside the thunk -- the hardcoded entry count
        NA_LIST_POOL = 0x02023B18          # the thunk's literal holding the list base
        NA_LIST = 0x0209C5D2               # the 4-entry u16 cid list
        NA_COUNT = 4
        # The stock members: every one is a PHANTOM (no card_prop record), which is what
        # makes this index safe to repurpose.
        NA_LIST_BEFORE = (0x0EA1, 0x0EA2, 0x1C55, 0x1C5F)
        # The two real "Ninjitsu Art" cards in the OTN pool.  Both are Traps -- which is
        # why PART E's word must admit non-monster card types.
        NA_TRANSFORMATION = 0x1768         # "Ninjitsu Art of Transformation"
        NA_DECOY = 0x17FF                  # "Ninjitsu Art of Decoy"
        NA_LIST_AFTER = (NA_TRANSFORMATION, NA_DECOY, 0x1C55, 0x1C5F)   # sorted, still 4 long

        # ===========================================================================
        # PART B -- the "Ninja" set code 0x06  (ARM9)
        # ===========================================================================
        NINJA_SETCODE = 0x06
        NINJA_THUNK = 0x020237D8
        NINJA_COUNT_IMM = 0x020237DC       # `movs r2,#9`
        NINJA_LIST_POOL = 0x020237E0
        NINJA_LIST = 0x0209C722
        NINJA_COUNT = 9
        NINJA_DROP = 0x117B                # "Armed Ninja" -- displaced to make room (USER-CHOSEN).
                                           # The list has no phantom, so membership costs a real Ninja.
                                           # Nothing in the stock ROM consumes set code 0x06, and both
                                           # Ninjitsu Art cards test "Ninja" through their own per-cid
                                           # switch predicates (0x021DA1C8 / 0x021E0680), not this table.

        # ===========================================================================
        # PART C -- the Normal-Summon trigger membership list  (overlay 3)
        # ===========================================================================
        # summon.trigger_is_a_membership_list: 0x02265768(event code) posts a selector-1
        # (cls1) event iff the summoned cid is in one of nine sorted lists.  Three
        # callers, three codes: 0x02267A38 -> 7 (NORMAL), 0x02268B7C -> 8 (FLIP),
        # 0x0226878A -> 9 (SPECIAL).  Clause 1 needs code 7 only.
        SUMMON_C7_LIST = 0x0228F7AC        # the "when this card is Normal Summoned" cid list
        SUMMON_C7_COUNT = 0x67
        SUMMON_C7_DROP = 0x14CC            # phantom (no card_prop) dropped to keep the insert count-neutral

        # ===========================================================================
        # PART D -- the cls1 record  (overlay 3)
        # ===========================================================================
        CLS1_BASE = 0x022860D4             # dispatch.cls_tables: 24-byte records, cid at +0x00
        CLS1_STRIDE = 24
        CLS1_COUNT = 0x535
        CLS1_DROP = 0x143E                 # free phantom row dropped for the count-neutral insert

        GEARFRAME_CID = 0x21F5             # "Machina Gearframe" -- the structural template
        ADD_TO_HAND = 0x02207EF5           # +04 shared "add a card from the Deck to the hand" resolver
        SLOT3_HAVE_TARGET = 0x021F0821     # +0C activation condition: candidate count >= r4 (default r4 = 1)
        SLOT4_GEARFRAME = 0x021E51E5       # +10 taken verbatim from Gearframe / Genex Blastfan (both "You can add")
        CLS1_NEW = (DONOR_CID, ADD_TO_HAND, 0x00000000, SLOT3_HAVE_TARGET, SLOT4_GEARFRAME, 0x00000000)

        # ===========================================================================
        # PART E -- the criteria row  (overlay 3)
        # ===========================================================================
        # dispatch.criteria_registry: stride 12, sorted by cid, trailing 0xFFFF sentinel.
        # Row layout {+0x00 u16 cid, +0x02 u16 aux, +0x04 Thumb handler, +0x08 u32 word}.
        CRIT_BASE = 0x022713C4
        CRIT_STRIDE = 12
        CRIT_COUNT = 1391                  # includes the trailing a=0xFFFF sentinel
        CRIT_FMT = "<HHII"
        CRIT_DROP = 0x143D                 # free phantom row dropped for the count-neutral insert

        DECK_TO_HAND = 0x0223CAF5          # "select from the DECK, add to hand" -- == 3DS 0x004B1C1C
        CRIT_WORD = 0x0000000E             # the 3DS Hanzo clause-1 word, verbatim; admits non-monster card types
        CRIT_NEW = (DONOR_CID, NA_SETCODE, DECK_TO_HAND, CRIT_WORD)

        # The table's real tail: row 1387 is a 0xFFFE guard and row 1388 the 0xFFFF
        # sentinel.  Neither ever moves (this patch only shifts rows 123..127), so they
        # are the cheapest proof that the rewrite stayed inside its window.
        CRIT_GUARD_ROW, CRIT_GUARD_CID = 1387, 0xFFFE
        CRIT_SENTINEL_ROW, CRIT_SENTINEL_CID = 1388, 0xFFFF

        # ===========================================================================
        # CLAUSE 2 -- "When this card is Flip or Special Summoned: You can add 1
        #             'Ninja' monster from your Deck to your hand, except this card."
        # ===========================================================================
        # A records-free donor can own only ONE cls1 record
        # (dispatch.second_cls1_record_is_spirit_only: the leftmost+offset path needs
        # card_type >> 1 == 7, i.e. a Spirit Monster, and Melchid is 3).  So clause 2
        # CANNOT have its own record -- it shares clause 1's, and the two clauses are
        # told apart by which CRITERIA ROW the step reads.  That is the whole problem,
        # and PARTS G/H/J are its three halves: the row, the right to have two rows,
        # and the code that chooses between them.
        #
        # PART G  (ov3)  clause 2's criteria row, inserted IMMEDIATELY AFTER clause 1's.
        # PART H  (ov3)  LIST A membership -- the right to be a two-row cid at all.
        # PART I  (ov3)  the Flip (code 8) and Special (code 9) summon triggers.
        # PART J  (ov3 + ov5)  the param stub that picks the row from the event code.

        # -- PART G: the criteria row ------------------------------------------------
        NINJA_AUX = NINJA_SETCODE          # aux 0x06 -- the "Ninja" has_set_code index
        # Konami's own row: 3DS main-effect registry 0x686CBC row 1541 is
        # {0x26AF, aux 0x06, 0x004B1C1C, 0x00000022}, and 3DS 0x004B1C1C == NDS
        # 0x0223CAF5 (dispatch.threeds_deck_handler_equivalence).  Machina Gearframe's
        # own row 0x00000022 is byte-identical -- same clause shape, same word.
        # Bit 5 (0x20) = "except this card": 53 of the 1388 stock rows carry it and 51
        # of those are printed with "except" (dispatch.criteria_word_bit5_is_except_self).
        # Bit 1 (0x02) = monsters only, which is the C1/C2 difference -- clause 1 says
        # "card" (both Ninjitsu Art cards are Traps) and used 0x0E; clause 2 says
        # "monster".
        CRIT_WORD_C2 = 0x00000022
        CRIT_NEW_C2 = (DONOR_CID, NINJA_AUX, DECK_TO_HAND, CRIT_WORD_C2)
        CRIT_DROP_C2 = 0x0E14              # free phantom row (no card_prop record, owns exactly
                                           # one row, unclaimed in EVERY pool of PHANTOM_CLAIMS)

        # -- PART H: LIST A ----------------------------------------------------------
        # dispatch.two_row_criteria_is_list_b_plus_l2.  0x02243B9C(cid, param) returns a
        # criteria ROW INDEX = leftmost_row_for_cid + r4, and r4 is 1 iff the cid is in
        # LIST A *and* param != 0:
        #     02243BEC  ldr r1,=LIST_A ; adds r0,r5,#0 ; movs r2,#0x3b ; bl 0x02022E14
        #     02243BF6  cmp r0,#0  ; beq <LIST B test>
        #     02243BFA  cmp r4,#0  ; beq -> 0x02243EEC (r4 = 0)   else -> 0x02243EC6 (r4 = 1)
        # It has exactly THREE callers ROM-wide: 0x02243FB6 (in 0x02243FA8), 0x02243FEE
        # (in 0x02243FE0) and 0x02244080.
        LIST_A = 0x0227134C                # 59 x u16, sorted; count immediate `movs r2,#0x3B` @0x02243BF0
        LIST_A_COUNT = 0x3B
        LIST_A_COUNT_IMM = 0x02243BF0
        LIST_A_DROP = 0x0D81               # "Speed Spell - Stardust Shimmer": a LIST A member owning
                                           # ZERO criteria rows, so its membership is vestigial and can
                                           # be dropped count-neutrally.  It and 0x0D7A are the only two
                                           # such members, and 0x0D7A is already spent by snoww.

        # -- PART I: the Flip / Special summon triggers ------------------------------
        # Same data-only route clause 1 proved in-game: 0x02265768(code) posts a cls1
        # event iff the summoned cid is in the list for that code.  No new cls1 record.
        SUMMON_C8_LIST = 0x0228F580        # code 8 = FLIP summoned
        SUMMON_C8_COUNT = 0x0C
        SUMMON_C8_DROP = 0x1A9F            # this list's ONLY phantom -- the scarcest slot in the
                                           # subsystem.  (0x1A9F is claimed by tg_striker in the
                                           # `registry_row` pool: a different resource, no conflict.)
        SUMMON_C9_LIST = 0x0228F63A        # code 9 = SPECIAL summoned
        SUMMON_C9_COUNT = 0x1F
        SUMMON_C9_DROP = 0x0E12            # one of this list's five phantoms; unclaimed in every pool

        # -- PART J: the param stub --------------------------------------------------
        # 0x02234E78(desc) -> param is five membership-list arms then a per-cid switch
        # defaulting to 0.  NO arm returns the event code, and all 80 entries of the five
        # lists are real cards (zero phantoms), so no list can be repurposed the way set
        # code 0x2A was for clause 1 and no descriptor field substitutes.  Code is the
        # only route -- which is also why gates_of_dark_world hooked the L2 search rather
        # than inserting a row.
        #
        # THREE call sites feed this card (all 60 `bl 0x02234E78` in ov3 were enumerated):
        #   0x021F0858  slot3 0x021F0820   -> 0x02243FE0   the activation condition
        #   0x02208028  resolver 0x02207EF4 -> 0x02243FA8  a GUARD only (cmp r0,r4/blt -> code 0x78)
        #   0x022080D6  resolver 0x02207EF4 -> 0x0219C430  ** THE PROMPT ** -- 0x0219C430 stashes
        #               cid/param and re-reads them at 0x0219C47C `bl 0x02243FA8`, and THAT call
        #               builds the picker list.
        # Rather than retarget three call sites, hook INSIDE the provider, which covers
        # every site at once -- the gates_of_dark_world PART I technique
        # (L2_SEARCH_SITE 0x02234E96).  Its sibling L1 lookup is unclaimed, and r5 still
        # holds the descriptor there (0x02234E7A: adds r5,r0,#0), so the event code is
        # readable as [r5,#4].
        PARAM_PROVIDER = 0x02234E78        # (desc) -> criteria `param`
        PARAM_PROLOGUE = 0xB5F8            # its `push {r3,r4,r5,r6,r7,lr}` -- the stub's unwind
                                           # depends on this exact frame, so verify() pins it
        L1_SEARCH_SITE = 0x02234E84        # the `bl 0x02022E14` this patch retargets (UNCLAIMED;
                                           # gates_of_dark_world owns the L2 one at 0x02234E96)
        BSEARCH_FN = 0x02022E14            # the shared sorted-u16 binary search (ARM9, Thumb)
        DESC_EVENT_CODE_OFF = 4            # dispatch.cls_table_selector: desc {+0 u16 cid, +4 u8 event
                                           # code, +5 u8 selector, ...}; 7 Normal / 8 Flip / 9 Special
        CAVE_PARAM_RESERVE = 0x40          # reserved slot in the ov5 cave (stub is 0x24 B)

        def _keys(ov: bytearray, base: int, count: int, stride: int, wide: bool) -> list[int]:
            fmt = "<I" if wide else "<H"
            return [struct.unpack_from(fmt, ov, _off(base + i * stride))[0] for i in range(count)]


        def _record_present(ov: bytearray, base: int, count: int, stride: int, fmt: str,
                            record: tuple) -> bool:
            """True if *record* already appears verbatim in the table (idempotency)."""
            return any(struct.unpack_from(fmt, ov, _off(base + i * stride)) == record
                       for i in range(count))


        def _bl_words(site: int, target: int) -> tuple[int, int]:
            """The two halfwords of an ARMv4T long `BL` at *site* targeting *target*.

            Thumb-1 has no `b.w`; a long branch is this two-halfword BL pair
            (thumb.thumb1_only).  Ported verbatim from gates_of_dark_world.
            """
            delta = (target & ~1) - (site + 4)
            assert -(1 << 22) <= delta < (1 << 22), f"BL 0x{site:08X} -> 0x{target:08X} too far"
            return (0xF000 | ((delta >> 12) & 0x7FF), 0xF800 | ((delta >> 1) & 0x7FF))


        def _insert_sorted(ov: bytearray, base: int, count: int, stride: int, fmt: str,
                           record: tuple, drop_cid: int, label: str, wide: bool,
                           after_same_cid: bool = False, expect_dupe: bool = False) -> None:
            """Count-neutral sorted insert: delete the phantom row, shift, write *record*.

            Ported verbatim from snoww / reborn_tengu, plus two clause-2 knobs:

            *after_same_cid* places the new record AFTER any existing rows with the same
            cid instead of before them.  The criteria table is sorted by cid alone, so a
            second row for a cid may legally go either side of the first -- but
            0x02243B9C returns ``leftmost_row_for_cid + r4``, so WHICH SIDE decides which
            clause is row 0.  The default (``<``) would put clause 2 first and silently
            swap the two clauses.

            *expect_dupe* allows the cid to already be present (clause 1's row), which
            the plain idempotency check would otherwise mistake for "already done".
            """
            keys = _keys(ov, base, count, stride, wide)
            new_cid = record[0]
            if _record_present(ov, base, count, stride, fmt, record):
                print(f"{label}: this exact record is already present (idempotent) -- skipped")
                return
            if new_cid in keys and not expect_dupe:
                print(f"{label}: 0x{new_cid:04X} already present (idempotent) -- skipped")
                return
            assert drop_cid in keys, f"{label}: phantom 0x{drop_cid:04X} not found -- table already edited?"
            dst = keys.index(drop_cid)
            pos = sum(1 for k in keys if (k <= new_cid if after_same_cid else k < new_cid))
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


        def _list_insert(ov: bytearray, base: int, count: int, new_cid: int, drop_cid: int,
                         label: str) -> None:
            """Count-neutral STRICTLY-sorted insert into a u16 membership list."""
            cur = _keys(ov, base, count, 2, False)
            if new_cid in cur:
                print(f"{label}: 0x{new_cid:04X} already a member (idempotent) -- skipped")
                return
            assert drop_cid in cur, f"{label}: 0x{drop_cid:04X} not in the list -- already spent?"
            assert all(cur[i] < cur[i + 1] for i in range(len(cur) - 1)), \
                f"{label}: the list is not strictly sorted in the base ROM"
            new = sorted([c for c in cur if c != drop_cid] + [new_cid])
            assert len(new) == count and all(new[i] < new[i + 1] for i in range(len(new) - 1)), \
                f"{label}: result is not a strictly sorted {count}-entry set"
            struct.pack_into(f"<{count}H", ov, _off(base), *new)
            print(f"{label}: dropped 0x{drop_cid:04X}, inserted 0x{new_cid:04X} @{new.index(new_cid)}, "
                  f"count still {count} and strictly sorted")


        def _arm9_section(rom) -> tuple["ndspy.code.MainCodeFile", object, bytearray]:
            """Return (MainCodeFile, the 0x02000000 section, a mutable copy of its data)."""
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
            return mc, sec, bytearray(sec.data)


        def _read_setcode_table(d: bytes, thunk: int, count_imm: int, pool: int,
                                expect_base: int, label: str) -> list[int]:
            """Read a set-code list, taking the COUNT and BASE from the thunk itself.

            setcode.slot_addresses_are_not_stable: never assume a slot address and never
            assume the count -- an earlier patch in a chain may already have rewritten
            the table.  Both are read live here, and only MEMBERSHIP is ever asserted.
            """
            def a9(addr: int) -> int:
                return addr - ARM9_BASE

            base = struct.unpack_from("<I", d, a9(pool))[0]
            assert base == expect_base, \
                f"{label}: the thunk's list literal @0x{pool:08X} is 0x{base:08X}, expected 0x{expect_base:08X}"
            imm = struct.unpack_from("<H", d, a9(count_imm))[0]
            assert (imm & 0xFF00) == 0x2200, \
                f"{label}: 0x{count_imm:08X} is not `movs r2,#N` (reads 0x{imm:04X})"
            n = imm & 0xFF
            tbl = list(struct.unpack_from(f"<{n}H", d, a9(base)))
            assert all(tbl[i] < tbl[i + 1] for i in range(n - 1)), \
                f"{label}: the list is not strictly sorted"
            return tbl


        # ---------------------------------------------------------------------------
        # PART J -- the param stub
        # ---------------------------------------------------------------------------
        def build_param_stub(base: int) -> bytes:
            """Return `param` for the donor from the SUMMON EVENT CODE; else stock behaviour.

            Reached from the retargeted `bl 0x02022E14` at L1_SEARCH_SITE, INSIDE the param
            provider 0x02234E78.  Live state there, all read off the disassembly:

                r0 = the cid being searched for   (0x02234E7C: ldrh r0,[r5])
                r1 = the L1 list base,  r2 = 0x11
                r5 = the DESCRIPTOR               (0x02234E7A: adds r5,r0,#0)
                lr = 0x02234E89                   (return into the provider)

                ldr  r3,=DONOR_CID
                cmp  r0,r3
                bne  native            ; not ours -> stock behaviour, byte for byte
                ldrb r3,[r5,#4]        ; event code: 7 Normal / 8 Flip / 9 Special
                cmp  r3,#8
                blt  native            ; 7 and below -> row 0 = clause 1
                cmp  r3,#9
                bgt  native            ; above 9    -> row 0, fail safe
                movs r0,#1             ; Flip/Special: param != 0 -> row 1 = clause 2
                add  sp,#4             ; unwind the provider's `push {r3,r4,r5,r6,r7,lr}`
                pop  {r4,r5,r6,r7,pc}  ; ... and return 1 to the provider's CALLER
            native:
                ldr  r3,=BSEARCH_FN|1
                bx   r3                ; tail-call the engine's own search; lr is untouched,
                                       ; so it returns straight into the provider

            Two things that look like shortcuts and are not:

            * Taking `native` for event code 7 is not a fallback, it is the CORRECT answer
              and it is free: DONOR_CID is in none of the provider's five lists, so the
              search misses, the per-cid switch defaults, the provider returns 0, and
              0x02243B9C picks row 0 -- clause 1.
            * The unwind is unavoidable.  The L1 "found" arm returns `desc[+0x0C]`, so we
              cannot simply report "found" and let the provider answer.  It would also be
              WRONG: desc[+0x0C] is a packed ref (inst_idx << 1) | side, which is 0 for
              slot 0 on side 0 -- that shortcut would silently fall back to row 0 for one
              board position.
            """
            assert base % 4 == 0, f"stub base 0x{base:08X} must be 4-aligned for its literal pool"
            b = EffectBuilder()
            b.ldr_const(3, DONOR_CID)                                   # 0x00 ldr  r3,=DONOR_CID
            b.insn("CMP", "R0, R3")                                     # 0x02
            b.insn("BNE", "native")                                     # 0x04
            b.insn("LDRB", f"R3, [R5, #0x{DESC_EVENT_CODE_OFF:X}]")     # 0x06 ldrb r3,[r5,#4]
            b.insn("CMP", "R3, #8")                                     # 0x08
            b.insn("BLT", "native")                                     # 0x0A
            b.insn("CMP", "R3, #9")                                     # 0x0C
            b.insn("BGT", "native")                                     # 0x0E
            b.insn("MOV", "R0, #1")                                     # 0x10 movs r0,#1
            b.insn("ADD", "SP, #4")                                     # 0x12
            b.insn("POP", "{R4, R5, R6, R7, PC}")                       # 0x14
            b.label("native")
            b.ldr_const(3, BSEARCH_FN | 1)                              # 0x16 native: ldr r3,=BSEARCH_FN|1
            b.insn("BX", "R3")                                          # 0x18 (pool word aligned by the 0x1A pad)
            blob = b.assemble(base)
            # never trust a bare capstone disasm: it silently accepts illegal Thumb-2,
            # which on this ARMv5TE core is an undefined instruction = freeze
            assert_thumb1_only(blob[:0x1A], base)
            return blob


        # ---------------------------------------------------------------------------
        # PART A + PART B -- the two ARM9 set-code tables

        def apply_arm9_setcodes(out_path: str) -> None:
            """PART A ("Ninjitsu Art" on the inert set code 0x2A) and PART B (Ninja)."""
            rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
            mc, sec, d = _arm9_section(rom)

            def a9(addr: int) -> int:
                return addr - ARM9_BASE

            # -- the pointer-table slots still hold the thunks we think they do --------
            for code, thunk in ((NA_SETCODE, NA_THUNK), (NINJA_SETCODE, NINJA_THUNK)):
                slot = struct.unpack_from("<I", d, a9(SETCODE_PTR_TABLE + code * 4))[0]
                assert slot == (thunk | 1), \
                    f"has_set_code[0x{code:02X}] = 0x{slot:08X}, expected 0x{thunk | 1:08X}"

            # -- PART A ---------------------------------------------------------------
            na = _read_setcode_table(bytes(d), NA_THUNK, NA_COUNT_IMM, NA_LIST_POOL,
                                     NA_LIST, "A  set code 0x2A")
            assert len(na) == NA_COUNT, f"A  set code 0x2A has {len(na)} entries, expected {NA_COUNT}"
            if NA_TRANSFORMATION in na and NA_DECOY in na:
                print(f"A  set code 0x{NA_SETCODE:02X} already carries the Ninjitsu Art cards "
                      f"(idempotent) -- skipped")
            else:
                assert tuple(na) == NA_LIST_BEFORE, (
                    f"A  set code 0x2A is not the stock all-phantom list "
                    f"{[hex(x) for x in NA_LIST_BEFORE]} (reads {[hex(x) for x in na]}) -- "
                    f"another patch has claimed it")
                assert all(NA_LIST_AFTER[i] < NA_LIST_AFTER[i + 1] for i in range(NA_COUNT - 1)), \
                    "A  the new Ninjitsu Art list is not strictly sorted"
                struct.pack_into(f"<{NA_COUNT}H", d, a9(NA_LIST), *NA_LIST_AFTER)
                print(f"A  set code 0x{NA_SETCODE:02X} @0x{NA_LIST:08X} = "
                      f"{[hex(x) for x in NA_LIST_AFTER]}  (\"Ninjitsu Art\": Transformation + Decoy; "
                      f"the two dropped entries 0x0EA1/0x0EA2 were phantoms)")

            # -- PART B ---------------------------------------------------------------
            nj = _read_setcode_table(bytes(d), NINJA_THUNK, NINJA_COUNT_IMM, NINJA_LIST_POOL,
                                     NINJA_LIST, "B  set code 0x06")
            assert len(nj) == NINJA_COUNT, f"B  Ninja list has {len(nj)} entries, expected {NINJA_COUNT}"
            if DONOR_CID in nj:
                print(f"B  Ninja set code already contains 0x{DONOR_CID:04X} (idempotent) -- skipped")
            else:
                assert NINJA_DROP in nj, \
                    f"B  Armed Ninja 0x{NINJA_DROP:04X} is not in the Ninja list -- already spent?"
                new = sorted([c for c in nj if c != NINJA_DROP] + [DONOR_CID])
                assert len(new) == NINJA_COUNT and all(new[i] < new[i + 1] for i in range(NINJA_COUNT - 1)), \
                    f"B  the new Ninja list is not a strictly sorted {NINJA_COUNT}-entry set"
                struct.pack_into(f"<{NINJA_COUNT}H", d, a9(NINJA_LIST), *new)
                print(f"B  Ninja set code 0x{NINJA_SETCODE:02X} @0x{NINJA_LIST:08X}: dropped Armed Ninja "
                      f"0x{NINJA_DROP:04X}, inserted 0x{DONOR_CID:04X} @{new.index(DONOR_CID)} "
                      f"(count still {NINJA_COUNT}, strictly sorted)")

            sec.data = bytes(d)
            rom.arm9 = mc.save()
            rom.saveToFile(out_path)
            print(f"wrote ARM9 set-code edits -> {out_path}")

        def apply_effect(ov: bytearray) -> None:
            """PARTS C/D/E, all count-neutral sorted table edits."""
            _assert_preconditions(ov)

            # -- PART C: the Normal-Summon trigger ------------------------------------
            _list_insert(ov, SUMMON_C7_LIST, SUMMON_C7_COUNT, DONOR_CID, SUMMON_C7_DROP,
                         "C  summon list code 7 (Normal Summon)")

            # -- PART D: the cls1 record ----------------------------------------------
            _insert_sorted(ov, CLS1_BASE, CLS1_COUNT, CLS1_STRIDE, "<6I",
                           CLS1_NEW, CLS1_DROP,
                           f"D  cls1 (Machina Gearframe 0x{GEARFRAME_CID:04X} shape)", wide=True)

            # -- PART E: the criteria row ---------------------------------------------
            _insert_sorted(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, CRIT_FMT,
                           CRIT_NEW, CRIT_DROP,
                           f"E  criteria (aux 0x{NA_SETCODE:04X} = Ninjitsu Art, DECK -> hand, "
                           f"word 0x{CRIT_WORD:08X} = any card type)", wide=False)

            # -- PART G: clause 2's criteria row --------------------------------------
            # after_same_cid: 0x02243B9C returns leftmost_row_for_cid + r4, so this row
            # must land AFTER clause 1's to be row 1.  Inserting before would silently
            # swap the two clauses.
            _insert_sorted(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, CRIT_FMT,
                           CRIT_NEW_C2, CRIT_DROP_C2,
                           f"G  criteria (aux 0x{NINJA_AUX:04X} = Ninja, DECK -> hand, "
                           f"word 0x{CRIT_WORD_C2:08X} = monsters only, except self)",
                           wide=False, after_same_cid=True, expect_dupe=True)
            _assert_row_order(ov)

            # -- PART H: LIST A membership --------------------------------------------
            _list_insert(ov, LIST_A, LIST_A_COUNT, DONOR_CID, LIST_A_DROP,
                         "H  LIST A (the right to own two criteria rows)")

            # -- PART I: the Flip / Special summon triggers ---------------------------
            _list_insert(ov, SUMMON_C8_LIST, SUMMON_C8_COUNT, DONOR_CID, SUMMON_C8_DROP,
                         "I  summon list code 8 (Flip Summon)")
            _list_insert(ov, SUMMON_C9_LIST, SUMMON_C9_COUNT, DONOR_CID, SUMMON_C9_DROP,
                         "I  summon list code 9 (Special Summon)")

            # -- PART J (ov3 half): retarget the provider's L1 lookup -----------------
            _retarget_l1_search(ov)

            # the guard + sentinel rows must survive every shift
            for row, want in ((CRIT_GUARD_ROW, CRIT_GUARD_CID), (CRIT_SENTINEL_ROW, CRIT_SENTINEL_CID)):
                got = struct.unpack_from("<H", ov, _off(CRIT_BASE + row * CRIT_STRIDE))[0]
                assert got == want, \
                    f"E  criteria row {row} is 0x{got:04X}, expected the 0x{want:04X} tail marker"


        def _donor_rows(ov: bytearray) -> list[tuple[int, tuple]]:
            """Every criteria row belonging to the donor, as (index, record), in table order."""
            return [(i, struct.unpack_from(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE)))
                    for i in range(CRIT_COUNT)
                    if struct.unpack_from("<H", ov, _off(CRIT_BASE + i * CRIT_STRIDE))[0] == DONOR_CID]


        def _assert_row_order(ov: bytearray) -> None:
            """The donor's two criteria rows must be ADJACENT and in clause order.

            0x02243B9C returns ``leftmost_row_for_cid + r4`` with r4 in {0, 1}, so row 0
            must be clause 1 (Ninjitsu Art, aux 0x2A) and row 1 clause 2 (Ninja, aux
            0x06).  Any other arrangement silently swaps the two clauses -- and would
            still pass a naive "both rows present" check.
            """
            rows = _donor_rows(ov)
            assert len(rows) == 2, \
                f"G  the donor owns {len(rows)} criteria rows, expected exactly 2"
            (i0, r0), (i1, r1) = rows
            assert i1 == i0 + 1, f"G  the donor's rows are not adjacent (index {i0} and {i1})"
            assert r0 == CRIT_NEW, f"G  row 0 is {[hex(x) for x in r0]}, expected clause 1's row"
            assert r1 == CRIT_NEW_C2, f"G  row 1 is {[hex(x) for x in r1]}, expected clause 2's row"
            print(f"G  row order OK: [{i0}] aux 0x{r0[1]:02X} (clause 1) then "
                  f"[{i1}] aux 0x{r1[1]:02X} (clause 2)")


        def _retarget_l1_search(ov: bytearray) -> None:
            """PART J (ov3 half): point the provider's L1 lookup at the ov5 stub."""
            want = _bl_words(L1_SEARCH_SITE, ov5_cave.CAVE_HANZO_PARAM)
            got = struct.unpack_from("<HH", ov, _off(L1_SEARCH_SITE))
            if got == want:
                print(f"J  the L1 lookup @0x{L1_SEARCH_SITE:08X} is already retargeted -- skipped")
                return
            assert got == _bl_words(L1_SEARCH_SITE, BSEARCH_FN), (
                f"J  0x{L1_SEARCH_SITE:08X} is not the native `bl 0x{BSEARCH_FN:08X}` "
                f"(reads {[hex(x) for x in got]}) -- another patch has claimed this site")
            struct.pack_into("<HH", ov, _off(L1_SEARCH_SITE), *want)
            print(f"J  retargeted the provider's L1 lookup `bl` @0x{L1_SEARCH_SITE:08X}: "
                  f"0x{BSEARCH_FN:08X} -> 0x{ov5_cave.CAVE_HANZO_PARAM:08X}")


        def _assert_preconditions(ov: bytearray) -> None:
            """Everything PARTS C/D/E assume about the base image, checked before writing."""
            # the cls1 template really is the record we are cloning
            c1 = _keys(ov, CLS1_BASE, CLS1_COUNT, CLS1_STRIDE, True)
            gf = c1.index(GEARFRAME_CID)
            slots = struct.unpack_from("<6I", ov, _off(CLS1_BASE + gf * CLS1_STRIDE))
            assert slots == (GEARFRAME_CID, ADD_TO_HAND, 0, SLOT3_HAVE_TARGET, SLOT4_GEARFRAME, 0), (
                f"the Machina Gearframe cls1 template drifted: {[hex(x) for x in slots]}")

            # ... and its criteria row is the same shape we are copying, on the same handler
            rows = [(struct.unpack_from("<HHII", ov, _off(CRIT_BASE + i * CRIT_STRIDE)))
                    for i in range(CRIT_COUNT)]
            assert (GEARFRAME_CID, 0x13, DECK_TO_HAND, 0x00000022) in rows, \
                "Machina Gearframe's criteria row drifted -- the aux/handler/word template is stale"
            assert (0x2389, 0x5D, DECK_TO_HAND, CRIT_WORD) in rows, \
                "Karakuri Inashichi's row drifted -- the word 0x0000000E precedent is stale"

            # the donor owns nothing yet, in any of the three tables we touch
            assert DONOR_CID not in c1, f"the donor 0x{DONOR_CID:04X} already has a cls1 record"
            assert all(cid != DONOR_CID for cid, _a, _h, _w in rows), \
                f"the donor 0x{DONOR_CID:04X} already has a criteria row"

            # nothing else claims the set code we are about to use
            assert all(aux != NA_SETCODE for _c, aux, _h, _w in rows), \
                f"aux 0x{NA_SETCODE:02X} is already used by a criteria row -- set code 0x2A is not free"
            print(f"0  preconditions OK: Gearframe cls1[{gf}] + its criteria row match the template, "
                  f"the donor is records-free, aux 0x{NA_SETCODE:02X} is unclaimed")

            # ---- clause 2 -----------------------------------------------------------
            # LIST A: read the count from the instruction that actually bounds the search,
            # never from a remembered constant.
            imm = struct.unpack_from("<H", ov, _off(LIST_A_COUNT_IMM))[0]
            assert imm == (0x2200 | LIST_A_COUNT), (
                f"H  0x{LIST_A_COUNT_IMM:08X} is not `movs r2,#0x{LIST_A_COUNT:02X}` "
                f"(reads 0x{imm:04X}) -- LIST A's size changed")
            la = _keys(ov, LIST_A, LIST_A_COUNT, 2, False)
            assert DONOR_CID not in la, f"H  the donor 0x{DONOR_CID:04X} is already in LIST A"
            assert LIST_A_DROP in la, f"H  0x{LIST_A_DROP:04X} is not in LIST A -- already spent?"
            # the slot we evict must be vestigial: a LIST A member with no criteria row can
            # never exercise the row-offset it grants, so dropping it changes no behaviour.
            assert sum(1 for c, _a, _h, _w in rows if c == LIST_A_DROP) == 0, (
                f"H  0x{LIST_A_DROP:04X} OWNS criteria rows -- dropping it from LIST A would "
                f"change that card's row selection")

            # the two summon-trigger lists
            for base, cnt, drop, name in ((SUMMON_C8_LIST, SUMMON_C8_COUNT, SUMMON_C8_DROP, "code 8"),
                                          (SUMMON_C9_LIST, SUMMON_C9_COUNT, SUMMON_C9_DROP, "code 9")):
                lst = _keys(ov, base, cnt, 2, False)
                assert DONOR_CID not in lst, f"I  the donor is already in the {name} list"
                assert drop in lst, f"I  phantom 0x{drop:04X} is not in the {name} list -- already spent?"

            # PART J's two load-bearing assumptions about the provider
            pro = struct.unpack_from("<H", ov, _off(PARAM_PROVIDER))[0]
            assert pro == PARAM_PROLOGUE, (
                f"J  the param provider's prologue is 0x{pro:04X}, expected 0x{PARAM_PROLOGUE:04X} "
                f"(`push {{r3,r4,r5,r6,r7,lr}}`) -- the stub's `add sp,#4 / pop {{r4-r7,pc}}` "
                f"unwind is sized to exactly that frame")
            site = struct.unpack_from("<HH", ov, _off(L1_SEARCH_SITE))
            assert site == _bl_words(L1_SEARCH_SITE, BSEARCH_FN), (
                f"J  0x{L1_SEARCH_SITE:08X} is not the stock `bl 0x{BSEARCH_FN:08X}` -- "
                f"another patch has claimed the provider's L1 lookup")
            print(f"0  clause 2 preconditions OK: LIST A is {LIST_A_COUNT} long and 0x{LIST_A_DROP:04X} "
                  f"is row-free, both summon lists have their phantom, the provider is unhooked")

        stubs = ((ov5_cave.CAVE_HANZO_PARAM, build_param_stub(ov5_cave.CAVE_HANZO_PARAM), "criteria-row selector"),)

        def install(rom, view):
            apply_effect(view.buf)

        def check_fn(c, rom, view):
            ov = bytearray(view.buf)
            ok = True

            def check(cond: bool, msg: str) -> bool:
                nonlocal ok
                print(f"[{'PASS' if cond else 'FAIL'}] {msg}")
                ok &= bool(cond)
                return bool(cond)

            # -- PART C ---------------------------------------------------------------
            lst = _keys(ov, SUMMON_C7_LIST, SUMMON_C7_COUNT, 2, False)
            check(DONOR_CID in lst, f"C  0x{DONOR_CID:04X} is in the code-7 (Normal Summon) list")
            check(SUMMON_C7_DROP not in lst, f"C  the phantom 0x{SUMMON_C7_DROP:04X} was dropped")
            check(len(lst) == SUMMON_C7_COUNT
                  and all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)),
                  f"C  the code-7 list is still {SUMMON_C7_COUNT} entries and strictly sorted")

            # -- PART D ---------------------------------------------------------------
            c1 = _keys(ov, CLS1_BASE, CLS1_COUNT, CLS1_STRIDE, True)
            if check(DONOR_CID in c1, f"D  cls1 record exists for 0x{DONOR_CID:04X}"):
                rec = struct.unpack_from("<6I", ov, _off(CLS1_BASE + c1.index(DONOR_CID) * CLS1_STRIDE))
                check(rec == CLS1_NEW,
                      f"D  cls1 slots = {{+04 0x{rec[1]:08X}, +08 0x{rec[2]:08X}, +0C 0x{rec[3]:08X}, "
                      f"+10 0x{rec[4]:08X}, +14 0x{rec[5]:08X}}} (Gearframe's, verbatim)")
                gf = c1.index(GEARFRAME_CID)
                gfr = struct.unpack_from("<6I", ov, _off(CLS1_BASE + gf * CLS1_STRIDE))
                check(gfr[1:] == CLS1_NEW[1:],
                      f"D  Machina Gearframe cls1[{gf}] is unregressed and still matches")
            check(CLS1_DROP not in c1, f"D  the phantom 0x{CLS1_DROP:04X} was dropped")
            check(len(c1) == CLS1_COUNT and all(c1[i] <= c1[i + 1] for i in range(len(c1) - 1)),
                  f"D  cls1 is still {CLS1_COUNT} records and sorted")

            # -- PART E ---------------------------------------------------------------
            rows = [struct.unpack_from("<HHII", ov, _off(CRIT_BASE + i * CRIT_STRIDE))
                    for i in range(CRIT_COUNT)]
            check(CRIT_NEW in rows,
                  f"E  criteria row {{0x{DONOR_CID:04X}, aux 0x{NA_SETCODE:04X}, "
                  f"0x{DECK_TO_HAND:08X}, 0x{CRIT_WORD:08X}}} present")
            check(sum(1 for r in rows if r[0] == DONOR_CID) == 2,
                  "E  the donor owns exactly TWO criteria rows (clause 1 + clause 2)")
            check(all(r[0] != CRIT_DROP for r in rows), f"E  the phantom 0x{CRIT_DROP:04X} was dropped")
            keys = [r[0] for r in rows]
            check(len(keys) == CRIT_COUNT and all(keys[i] <= keys[i + 1] for i in range(len(keys) - 1)),
                  f"E  the criteria table is still {CRIT_COUNT} rows and sorted")
            check(keys[CRIT_GUARD_ROW] == CRIT_GUARD_CID
                  and keys[CRIT_SENTINEL_ROW] == CRIT_SENTINEL_CID,
                  "E  the 0xFFFE guard and 0xFFFF sentinel rows are intact")
            check((GEARFRAME_CID, 0x13, DECK_TO_HAND, 0x00000022) in rows,
                  "E  Machina Gearframe's own criteria row is unregressed")

            # -- PART G: clause 2's row, and the ORDER that makes it row 1 -------------
            drows = _donor_rows(ov)
            if check(len(drows) == 2, f"G  the donor owns exactly 2 criteria rows (got {len(drows)})"):
                (i0, r0), (i1, r1) = drows
                check(i1 == i0 + 1, f"G  the two rows are adjacent (index {i0}, {i1})")
                check(r0 == CRIT_NEW,
                      f"G  ROW 0 = aux 0x{r0[1]:04X} word 0x{r0[3]:08X} -- clause 1 (Ninjitsu Art)")
                check(r1 == CRIT_NEW_C2,
                      f"G  ROW 1 = aux 0x{r1[1]:04X} word 0x{r1[3]:08X} -- clause 2 (Ninja, except self)")
                check(bool(r1[3] & 0x20),
                      "G  clause 2's word carries bit 5 (0x20) = \"except this card\"")
            check(all(r[0] != CRIT_DROP_C2 for r in rows),
                  f"G  the phantom 0x{CRIT_DROP_C2:04X} was dropped")

            # -- PART H: LIST A --------------------------------------------------------
            la = _keys(ov, LIST_A, LIST_A_COUNT, 2, False)
            check(DONOR_CID in la, f"H  0x{DONOR_CID:04X} is in LIST A (so row = leftmost + r4)")
            check(LIST_A_DROP not in la, f"H  the vestigial member 0x{LIST_A_DROP:04X} was dropped")
            check(len(la) == LIST_A_COUNT and all(la[i] < la[i + 1] for i in range(len(la) - 1)),
                  f"H  LIST A is still {LIST_A_COUNT} entries and strictly sorted")
            check(struct.unpack_from("<H", ov, _off(LIST_A_COUNT_IMM))[0] == (0x2200 | LIST_A_COUNT),
                  f"H  0x{LIST_A_COUNT_IMM:08X} still reads `movs r2,#0x{LIST_A_COUNT:02X}`")

            # -- PART I: the Flip / Special triggers -----------------------------------
            for base, cnt, drop, name in ((SUMMON_C8_LIST, SUMMON_C8_COUNT, SUMMON_C8_DROP, "8 (Flip)"),
                                          (SUMMON_C9_LIST, SUMMON_C9_COUNT, SUMMON_C9_DROP, "9 (Special)")):
                lst = _keys(ov, base, cnt, 2, False)
                check(DONOR_CID in lst, f"I  0x{DONOR_CID:04X} is in the code-{name} summon list")
                check(drop not in lst, f"I  the phantom 0x{drop:04X} was dropped from code-{name}")
                check(len(lst) == cnt and all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)),
                      f"I  the code-{name} list is still {cnt} entries and strictly sorted")
            c7 = _keys(ov, SUMMON_C7_LIST, SUMMON_C7_COUNT, 2, False)
            check(DONOR_CID in c7, "I  the code-7 (Normal) list still holds the donor -- clause 1 intact")

            # -- PART J: the hook and the stub -----------------------------------------
            check(struct.unpack_from("<H", ov, _off(PARAM_PROVIDER))[0] == PARAM_PROLOGUE,
                  f"J  the provider's frame is still `push {{r3,r4,r5,r6,r7,lr}}` "
                  f"(the stub's unwind is sized to it)")
            check(struct.unpack_from("<HH", ov, _off(L1_SEARCH_SITE))
                  == _bl_words(L1_SEARCH_SITE, ov5_cave.CAVE_HANZO_PARAM),
                  f"J  the provider's L1 lookup @0x{L1_SEARCH_SITE:08X} calls the stub")
            # gates_of_dark_world owns the L2 lookup -- prove we did not disturb it
            check(struct.unpack_from("<HH", ov, _off(0x02234E96))
                  != _bl_words(0x02234E96, ov5_cave.CAVE_HANZO_PARAM),
                  "J  the L2 lookup @0x02234E96 (gates_of_dark_world's site) is untouched by us")
            want_blob = build_param_stub(ov5_cave.CAVE_HANZO_PARAM)   # re-asserts Thumb-1 only
            got_blob = ov5_cave.read_cave(rom, ov5_cave.CAVE_HANZO_PARAM, len(want_blob))
            check(got_blob == want_blob,
                  f"J  the {len(want_blob)} B param stub is installed at "
                  f"0x{ov5_cave.CAVE_HANZO_PARAM:08X}")

            # -- PARTS A/B (ARM9) -----------------------------------------------------
            rom2 = rom
            _mc, _sec, d = _arm9_section(rom2)
            d = bytes(d)

            try:
                na = _read_setcode_table(d, NA_THUNK, NA_COUNT_IMM, NA_LIST_POOL, NA_LIST,
                                         "A  set code 0x2A")
                # NOT an exact-equality check.  Clause 1 searches "Ninjitsu Art" cards, so
                # a LATER patch adding a member to this list is a feature, not a
                # regression -- ninjitsu_art_super_transformation spends the phantom
                # 0x1C55 to join it.  What Hanzo actually requires is that its own two
                # members survive and the table stays a valid sorted set-code list.
                check(NA_TRANSFORMATION in na and NA_DECOY in na
                      and len(na) == NA_COUNT
                      and all(na[i] < na[i + 1] for i in range(len(na) - 1)),
                      f"A  set code 0x{NA_SETCODE:02X} = {[hex(x) for x in na]} "
                      f"(Transformation + Decoy present, sorted, {len(na)} entries)")
            except AssertionError as exc:
                check(False, f"A  {exc}")

            try:
                nj = _read_setcode_table(d, NINJA_THUNK, NINJA_COUNT_IMM, NINJA_LIST_POOL, NINJA_LIST,
                                         "B  set code 0x06")
                check(DONOR_CID in nj, f"B  0x{DONOR_CID:04X} is a member of the Ninja set code")
                check(NINJA_DROP not in nj, f"B  Armed Ninja 0x{NINJA_DROP:04X} was displaced")
                check(len(nj) == NINJA_COUNT, f"B  the Ninja list is still {NINJA_COUNT} entries")
            except AssertionError as exc:
                check(False, f"B  {exc}")

            # the aux -> thunk plumbing the criteria row depends on
            ptr = struct.unpack_from("<I", d, SETCODE_PTR_TABLE + NA_SETCODE * 4 - ARM9_BASE)[0]
            check(ptr == (NA_THUNK | 1),
                  f"A  has_set_code[0x{NA_SETCODE:02X}] still points at 0x{NA_THUNK | 1:08X}")
            # `cmp r1,#0x70` = 0x2970 (CMP Rn,#imm8 is 0x2800 | Rn<<8 | imm8).  This is the
            # bound that makes aux 0x2A a legal set code at all, so it is worth pinning.
            check(struct.unpack_from("<H", d, HAS_SET_CODE + 2 - ARM9_BASE)[0] == 0x2970,
                  f"A  has_set_code 0x{HAS_SET_CODE:08X} still bounds-checks `cmp r1,#0x70`")
            c.ok(ok, "Hanzo: summon lists, cls1, criteria rows and their order, LIST A, provider hook, set codes")

        return Compiled(stubs, installs=(install,), posts=(apply_arm9_setcodes,), checks=(check_fn,))


hanzo_effects = normal_summon_add_ninjitsu_art_flip_or_special_summon_add_ninja_from_deck

SPEC = card(0x13E7, hanzo_effects())

PROPS = card_props("DARK", "Warrior", level=4, atk=1800, defense=1000)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_hanzo.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
