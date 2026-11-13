"""Snoww, Unlight of Dark World (DARK / Fiend / Effect Monster / Level 4 / 1700 / 0) on Renge, Gatekeeper of Dark World 0x1C18.

See notes/snoww-findings.md and card_text.CARD_TEXT[0x1C18] for the printed text: discarded to the GY by a card effect, add 1 "Dark World"
card from the Deck to the hand; a second effect Special Summons a monster from the opponent's GY.

The switch-walk registry below (EXTRA_SWITCH_STUBS / register_switch_stub / _switch_leaf and the bin2.pac helpers) is shared state:
grapha and infernoble register their own ov3 stubs here, gates_of_dark_world reads the pac helpers, and the DSL verbs read the walk.
"""
from __future__ import annotations

import re
import struct
import sys

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
from otn_enhanced.asm import effect_verify
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.rom.pac import parse_pac
from otn_enhanced.effects.common import ov3_off as _off
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.data.card_stats import TEXT_LANGS
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class discarded_from_hand_to_graveyard_by_effect_search_dark_world_card_from_deck_and_in_hand_discard_special_summon_from_opponent_graveyard:
    """Snoww, Unlight of Dark World (Renge, Gatekeeper of Dark World 0x1C18, a Normal Monster made an Effect Monster): 'If this card is discarded to the
    Graveyard by a card effect: add 1 "Dark World" card from your Deck to your hand. [second effect: target 1 monster in your opponent's GY; Special
    Summon it in Defense Position]' The Dark World effect-discard arm admits the donor through a gate stub in the switch chain (the walk registry and
    `_switch_leaf` stay in the card file: grapha and infernoble register their own stubs with it), a cls2 record over 0x1B45 (add-to-hand resolver, then
    the ov5 resolver / target declaration), two criteria rows (Deck Dark World rel 0, opponent GY monster rel 1) over 0x14E7 / 0x14EF, LIST A membership
    over a Speed Spell phantom, and three ov5 stubs (resolver, target declaration, criteria-row selector). The card_prop rewrite and name/description come
    from `dsl.make`. Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        import re
        import struct
        import ndspy.code
        import ndspy.rom
        from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
        from otn_enhanced.asm import effect_verify
        from otn_enhanced.asm.effect_builder import EffectBuilder
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.rom.pac import parse_pac
        from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
        from otn_enhanced.effects.common import ov3_off as _off
        from otn_enhanced.cards import snoww as _sn
        # The switch-walk registry is shared state other cards register into: use the card module's, never a copy.
        EXTRA_SWITCH_STUBS, EXTRA_SWITCH_DONORS = _sn.EXTRA_SWITCH_STUBS, _sn.EXTRA_SWITCH_DONORS
        _in_stub, _switch_leaf = _sn._in_stub, _sn._switch_leaf
        _open_pac, _find_prop = _sn._open_pac, _sn._find_prop

        DONOR_CID = 0x1C18          # Renge, Gatekeeper of Dark World (keep-cid rule)

        from otn_enhanced.effects.common import ARM9_BASE
        # ARM9 "Dark World" set-code list -- ASSERTED, never written.  Set code 0x0F,
        # thunk 0x020238B5 (table 0x0209D0D8 index 0x0F), 16 sorted entries.
        DW_LIST, DW_LIST_COUNT = 0x0209CA06, 16
        DW_THUNK_SLOT = 0x0209D0D8 + 0x0F * 4
        DW_THUNK = 0x020238B5

        # ---------------------------------------------------------------------------
        # PART A -- admit the donor to the "effect discard" switch arm (overlay-3 CODE)
        # ---------------------------------------------------------------------------
        SWITCH_BASE = 0x021D1392            # the per-cid chain inside 0x021D1300
        SWITCH_END = 0x021D19C0             # the default REJECT leaf
        DW_ARM = 0x021D185C                 # the Dark World effect-discard arm
        LICH_CID, LICH_ARM = 0x1BEB, 0x021D1902   # the terminal node's native occupant
        PIVOT_LIT = 0x021D1590              # the subtree's pool literal
        PIVOT_VAL = 0x1B8B                  # = Radiant Jeral; r0 holds this at GATE_ARM

        GATE_ARM = 0x021D15EE               # the terminal node cid 0x1C18 actually reaches
        GATE_ARM_NATIVE = bytes.fromhex("60308542")       # ADD R0,#0x60 ; CMP R5,R0
        # Nothing in ov3 branches to 0x021D15F0 or 0x021D15F2 (asserted below), so those
        # two halfwords may be replaced by a 4-byte BL.  0x021D15F2..0x021D15F7 are KEPT.
        GATE_TAIL_NATIVE = bytes.fromhex("00d185e1e3e1")  # BNE +0 ; B Lich ; B reject

        # ov3 dead-code block 0x021B56B8 (16 B, phantom 0x133D) -- WHOLLY UNCLAIMED in
        # OV3_DEAD_BLOCKS, a stat-engine arm leaf that is resident in every duel mode.
        # Exactly 16 B needed, exactly 16 B available.  Its only inbound reference is the
        # BL at 0x021B4D9A, which belongs to the phantom's own (dead) arm.
        GATE_STUB = 0x021B56B8
        GATE_STUB_LEN = 16

        GATE_STUB_NATIVE = bytes.fromhex("03980121081af7f773fc00282addfa20")

        DONOR_DELTA = DONOR_CID - PIVOT_VAL       # 0x8D
        LICH_DELTA = DONOR_CID - LICH_CID         # 0x2D

        # The kind plumbing this arm depends on -- asserted, never written.
        KIND_MOV_R6 = (0x021C6CB0, 0x2601)        # MOV R6,#1
        KIND_SUB = (0x021C6CB6, 0x1AF3)           # SUB R3,R6,R3   => r3 = 1 - kind
        EFFECT_DISCARD_MOVER = 0x021C6D58

        # ---------------------------------------------------------------------------
        # PART B -- the cls2 record (what the posted event dispatches to)
        # ---------------------------------------------------------------------------
        CLS2_BASE, CLS2_COUNT, CLS2_STRIDE = 0x02275C04, 0x2B9, 0x18
        ADD_TO_HAND = 0x02207EF5     # +04 the shared "add N from a zone to the hand" resolver
                                     #     (105 cls records: Scarr, Toon Table of Contents,
                                     #     Arsenal Summoner, Terraforming, RotA, Stratos ...)
        # +08/+0C/+10/+14 all zero = the SANGAN / SCARR shape = MANDATORY, which is what
        # clause 1 wants (event.optional_trigger_is_record_shape).
        CLS2_NEW = (DONOR_CID, ADD_TO_HAND, 0, 0, 0, 0)
        # Phantom 0x1B45: no card_prop record, owns EXACTLY ONE cls2 row (index 245), and
        # its cid appears exactly once as an aligned u32 anywhere in overlay 3 -- in that
        # very row -- and never in ARM9.
        CLS2_DROP_PHANTOM = 0x1B45

        # 0x02207EF4's per-cid switch only OVERRIDES the count in r4 (default `MOV R4,#1`
        # at 0x02207F04); an unnamed cid falls to the common body with r4 == 1.
        ADDHAND_SWITCH_ENTRY = 0x02207EF6
        ADDHAND_DEFAULT_ARM = 0x02207FCC
        ADDHAND_STOPS = (0x02207FCC, 0x02207F36, 0x02207F42, 0x02207F46, 0x02207F80, 0x02207F8A)

        # ---------------------------------------------------------------------------
        # PART C -- the criteria row (the selector payload), taken from the 3DS
        # ---------------------------------------------------------------------------
        POP_BASE, POP_COUNT, POP_STRIDE = 0x022713C4, 0x56C, 12
        POP_FMT = "<HHII"
        CRIT_AUX = 0x000F            # the "Dark World" set code
        CRIT_HANDLER = 0x0223CAF5    # search the DECK, add to hand (== 3DS 0x004B1C1C)
        CRIT_WORD = 0x0000000E       # any CARD type: Monster|Spell|Trap, no level/race filter
        CRIT_NEW = (DONOR_CID, CRIT_AUX, CRIT_HANDLER, CRIT_WORD)
        # Phantom 0x14E7: no card_prop record, owns exactly one criteria row (index 165),
        # and it is in neither membership list A nor B, so dropping it cannot change any
        # cid's block size.  It sits below the donor's insert point (554), so only rows
        # 166..553 shift down one.  dragon_shrine's index-anchored crit[157] is
        # BELOW that window and is unaffected; shiens_dojo's rows are located by
        # cid, not index.
        POP_DROP_PHANTOM = 0x14E7
        LIST_A, LIST_A_COUNT = 0x0227134C, 59     # asserted untouched by clause 1
        LIST_B, LIST_B_COUNT = 0x02271314, 27     # asserted untouched by clause 1

        # Reference rows this patch's shape is copied from (asserted intact).
        SCARR_CID, SCARR_ROW = 0x196A, (0x196A, 0x000F, 0x0223CAF5, 0x00900002)
        TOON_CID, TOON_ROW = 0x1562, (0x1562, 0x0000, 0x0223CAF5, 0x0000000E)

        # ===========================================================================
        # CLAUSE 2 -- "If it was discarded from your hand to your Graveyard by an
        # OPPONENT's card effect, you can target 1 monster in your opponent's
        # Graveyard; ... then Special Summon that target (if any) in face-up Defense
        # Position."
        #
        # THE TEMPLATE IS GOLDD, WU-LORD OF DARK WORLD 0x1969, whose printed text is
        # structurally IDENTICAL (same trigger, same opponent gate, same
        # "target ...; <base action>, then <targeted action> (if any)"):
        #     cls2[192] = {+04 0x0221FB51, +08 0x021DE7C9, +0C 0x0224A115,
        #                  +10 0, +14 0x0223847D}
        # Its resolver 0x0221FB50 is a 2-phase machine --
        #     phase 0x80 -> <base action>; if [0x0229AAFC+0x74] != 0 return 0x7F else 0
        #     phase 0x7F -> <targeted action>; return 0
        # and [0x0229AAFC+0x74] is the DECLARED-TARGET counter, i.e. the printed
        # "(if any)".  Its slot5 0x0223847C step 0 IS the opponent gate and the "you
        # can" prompt, returning 1 to SKIP -- which is where a half-optional card puts
        # its optionality (NOT slot3/slot4; both of Goldd's are generic).
        # ===========================================================================
        CRIT_AUX2 = 0xFFFF           # no set code -- any monster
        CRIT_HANDLER2 = 0x0223E1D1   # target 1 monster in the OPPONENT'S GY and Special Summon it
                                     # (== 3DS 0x004A7F4C; family = Autonomous Action Unit,
                                     #  Doomkaiser Dragon, Victoria, Bone Temple Block,
                                     #  Wiseman's Chalice, Sorciere de Fleur)
        CRIT_WORD2 = 0x00010002      # 1 monster, GY-zone family flag -- the 3DS's own Snoww row 1,
                                     # and byte-identical to Autonomous Action Unit / Wiseman's
                                     # Chalice, which own the very same row
        CRIT_ROW2 = (DONOR_CID, CRIT_AUX2, CRIT_HANDLER2, CRIT_WORD2)
        # Row 1 must sit IMMEDIATELY AFTER row 0: the row-offset machinery addresses a cid's
        # rows as leftmost + offset, so the pair must be adjacent and in this order.
        POP_DROP_PHANTOM2 = 0x14EF   # no card_prop, owns exactly one criteria row (index 168),
                                     # in neither membership list, 3 u16 occurrences build-wide

        # LIST A @0x0227134C -- "this cid owns a two-row criteria pair", rule
        # `row = (param != 0) ? 1 : 0` (CMP R4,#0 @0x02243BFA).  LIST B is FULL and its only
        # phantom 0x234F is spent by gates_of_dark_world, but LIST A has TWO members
        # that own ZERO criteria rows (dispatch.list_a_has_two_inert_members), so their
        # membership is vestigial and one can be dropped count-neutrally.
        LIST_A_COUNT_IMM = 0x02243BF0        # `movs r2,#0x3B` -- the engine's own bound
        LIST_A_RULE_SITE = 0x02243BFA        # `cmp r4,#0`
        LIST_A_DROP = 0x0D7A                 # Speed Spell - Preparation of Rites: 0 criteria rows
        LIST_A_DROP_ALT = 0x0D81             # Speed Spell - Stardust Shimmer: the other inert one

        # The ov5 stubs (addresses live from the ledger; never hardcoded).
        RES_STUB = ov5_cave.CAVE_SNOWW_RES
        RES_STUB_RESERVE = 0x40
        SLOT5_STUB = ov5_cave.CAVE_SNOWW_SLOT5
        SLOT5_STUB_RESERVE = 0x30
        ROW_STUB = ov5_cave.CAVE_SNOWW_ROW
        ROW_STUB_RESERVE = 0x20

        PHASE_WORD = 0x0229AAFC              # +0x70 = the resolver phase, +0x74 = targets declared
        PHASE_CLAUSE2 = 0x7F                 # UNUSED by 0x02207EF5 (its jump table @0x02207FEE
                                             # sends 0x7F to a bare `movs r0,#0 ; pop`)
        SS_FROM_LIST = 0x02204730            # (desc, count/mode, POSITION); position 1 = face-up
                                             # DEFENSE (dispatch.ss_from_list_position_mode)
        SS_POSITION_DEFENSE = 1
        OFFFIELD_PICKER = 0x02235604         # the native slot5 target-declaration template
        PARAM_PROVIDER = 0x02234E78
        PARAM_CALL_SITE = 0x02235610         # slot5's own `bl 0x02234E78` -- cid-scoped by ROW_STUB
        SLOT3_ALWAYS = 0x0224A115            # `movs r0,#2 ; bx lr` -- activatable unconditionally
                                             # (Goldd's own slot3)
        GOLDD_CID = 0x1969                   # the template; asserted intact
        GOLDD_CLS2 = (0x1969, 0x0221FB51, 0x021DE7C9, 0x0224A115, 0, 0x0223847D)

        # The clause-2 cls2 record.  +08 stays 0: Goldd's slot2 0x021DE7C9 is an ON-FIELD
        # candidate predicate for ITS targets ("cards your opponent controls"); Snoww's
        # candidates are in the opponent's GRAVEYARD and are enumerated from the criteria
        # row by the picker itself, which returns 1 = SKIP when it finds none
        # (`CMP R0,#0 ; BNE` @0x02235632 -> `movs r0,#1 ; pop`).  That is the empty-list
        # guard, and it is structural rather than a count we would have to synthesise.
        CLS2_NEW2 = (DONOR_CID, RES_STUB | 1, 0, SLOT3_ALWAYS, 0, SLOT5_STUB | 1)

        # ---------------------------------------------------------------------------
        # PART D -- the visible card
        # ---------------------------------------------------------------------------
        NEW_ATTRIBUTE = "DARK"       # unchanged from the donor
        NEW_RACE = "Fiend"           # unchanged from the donor
        NEW_ATK = 1700
        NEW_DEF = 0
        NEW_CARD_TYPE = 3            # Effect Monster (the donor is 1 = Normal Monster);
                                     # event.promoted_vanilla_cardprop_is_correct
        NEW_NAME = b"Snoww, Unlight of Dark World"
        NEW_DESC = (b'If this card is discarded from the hand to the Graveyard by a '
                    b'card effect, add 1 "Dark World" card from your Deck to your hand.')
        from otn_enhanced.data.card_stats import TEXT_LANGS


        # ---------------------------------------------------------------------------
        # small helpers (ported verbatim from reborn_tengu / eclipse_wyvern)
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
            return struct.pack("<HH", 0xF000 | ((offset >> 12) & 0x7FF), 0xF800 | ((offset >> 1) & 0x7FF))


        def _insert_sorted_dup(ov: bytearray, base: int, count: int, stride: int, fmt: str,
                               record: tuple, drop_cid: int, label: str) -> None:
            """Count-neutral insert of a SECOND row for a cid that already owns one.

            Like :func:`_insert_sorted` but lands the new row immediately AFTER the
            existing same-cid row, because the row-offset machinery addresses a cid's
            rows as ``leftmost + offset`` -- the pair MUST be adjacent and in order.
            Only the u16-keyed criteria registry needs this.
            """
            keys = _keys(ov, base, count, stride, False)
            new_cid = record[0]
            if keys.count(new_cid) >= 2:
                print(f"{label}: 0x{new_cid:04X} already owns two rows (idempotent) -- skipped")
                return
            assert keys.count(new_cid) == 1, \
                f"{label}: 0x{new_cid:04X} owns {keys.count(new_cid)} rows, expected exactly 1 (clause 1)"
            assert drop_cid in keys, f"{label}: phantom 0x{drop_cid:04X} not found -- table already edited?"
            dst = keys.index(drop_cid)
            pos = sum(1 for k in keys if k <= new_cid)          # AFTER the existing row
            if pos > dst:
                blk = bytes(ov[_off(base + (dst + 1) * stride):_off(base + pos * stride)])
                ov[_off(base + dst * stride):_off(base + (pos - 1) * stride)] = blk
                pos -= 1
            elif pos < dst:
                blk = bytes(ov[_off(base + pos * stride):_off(base + dst * stride)])
                ov[_off(base + (pos + 1) * stride):_off(base + (dst + 1) * stride)] = blk
            struct.pack_into(fmt, ov, _off(base + pos * stride), *record)
            after = _keys(ov, base, count, stride, False)
            assert all(after[i] <= after[i + 1] for i in range(count - 1)), \
                f"{label}: table lost its sort order"
            mine = [i for i, k in enumerate(after) if k == new_cid]
            assert mine == [mine[0], mine[0] + 1], \
                f"{label}: the two rows are not adjacent: {mine}"
            print(f"{label}: dropped phantom 0x{drop_cid:04X} @{dst}, inserted 0x{new_cid:04X} @{pos} "
                  f"(rows {mine[0]}/{mine[1]} adjacent, count {count} unchanged)")


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


        def _read_cstr(buf: bytes, start: int) -> bytes:
            return buf[start:buf.index(b"\x00", start)]


        # ---------------------------------------------------------------------------
        # PART A -- the stub
        # ---------------------------------------------------------------------------
        def gate_stub(base: int = GATE_STUB) -> bytes:
            """Admit the donor; hand Lich Lord's native test back to the caller's BNE.

                +0   ADDS R0,#0x8D    ; r0 = 0x1B8B + 0x8D = 0x1C18   (the donor)
                +2   CMP  R5,R0
                +4   BEQ  +12         ; our cid -> the Dark World arm
                +6   SUBS R0,#0x2D    ; r0 = 0x1C18 - 0x2D = 0x1BEB   (Lich Lord)
                +8   CMP  R5,R0       ; the displaced test: sets Z for the caller's BNE
                +10  BX   LR          ; -> 0x021D15F2 (BX never writes the flags)
                +12  BL   0x021D185C  ; the Dark World effect-discard arm; never returns

            No literal pool: both cids are reachable from the pivot 0x1B8B that r0
            already holds, with 2-operand ADD/SUB imm8 (the thumb.add_sub_imm3 footgun
            only applies to the 3-operand form).

            Register safety on all three exits: the accept path reaches 0x021D199E
            `MOV R0,#1`, the reject path 0x021D19C0 `MOV R0,#0`, and the Dark World arm
            0x021D185C opens `LDR R0,[SP,#0x34]` -- r0 is dead on every one.  LR is free
            because 0x021D1300 pushed it at entry and returns via POP {...,PC}; the arm
            itself never reads LR.
            """
            b = EffectBuilder()
            b.insn("ADD", f"R0, #0x{DONOR_DELTA:X}")
            b.insn("CMP", "R5, R0")
            b.insn("BEQ", "dw")
            b.insn("SUB", f"R0, #0x{LICH_DELTA:X}")
            b.insn("CMP", "R5, R0")
            b.insn("BX", "LR")
            b.label("dw")
            b.bl(DW_ARM)
            blob = b.assemble(base, pad="nop")
            assert len(blob) == GATE_STUB_LEN, len(blob)
            return blob


        # ---------------------------------------------------------------------------
        # CLAUSE 2 -- the three ov5 stubs
        # ---------------------------------------------------------------------------
        def res_stub(base: int = None) -> bytes:
            """cls2 +04.  Goldd 0x0221FB50's two-phase skeleton with clause 1 grafted in.

                +00  PUSH {R4,R5,R6,LR}
                +02  ADDS R6,R0,#0         ; keep the DESCRIPTOR: r0 is the return value later
                +04  LDR  R4,[PC,#..]      ; = 0x0229AAFC                (pool at +0x2C)
                +06  LDR  R5,[R4,#0x70]    ; the resolver phase
                +08  CMP  R5,#0x7F
                +0A  BEQ  +0x1E            ; -> clause 2
                +0C  BL   0x02207EF4       ; CLAUSE 1, byte-identical behaviour
                +10  CMP  R0,#0
                +12  BNE  +0x1C            ; still running -> hand its value straight back
                +14  LDRB R5,[R6,#0x10]    ; THE DECLARED-PICK COUNT = the printed "(if any)"
                +16  CMP  R5,#0
                +18  BEQ  +0x1C            ; no target -> done, clause 1 only (r0 is already 0)
                +1A  MOVS R0,#0x7F         ; advance to clause 2
                +1C  POP  {R4,R5,R6,PC}
                +1E  MOVS R1,#1            ; count / mode
                +20  MOVS R2,#1            ; POSITION = face-up DEFENSE
                +22  BL   0x02204730       ; Special Summon the recorded pick
                +26  MOVS R0,#0
                +28  POP  {R4,R5,R6,PC}
                +2C  .word 0x0229AAFC

            *** THE PICK COUNT IS desc[+0x10], NOT [0x0229AAFC+0x74].  IN-GAME 2026-08-27
            the first build let the player select a monster in the opponent's Graveyard and
            then summoned nothing, because [0x0229AAFC+0x74] -- copied from Goldd, whose
            slot5 is a BESPOKE step machine -- is never written on this path, so phase 0x7F
            was never entered.  The shared off-field picker 0x02235604 records a pick
            through 0x022347B0 (board, zone <= 0x0A) or 0x02234880 (list, zone > 0x0A -- a
            Graveyard pick is zone 0x0E, so it is the list one), and BOTH bump the byte
            desc[+0x10] (`STRB r0,[r4,#0x10]` @0x0223480E, `STRB r0,[r5,#0x10]` @0x022348B8)
            -- dispatch.pick_record_and_resolver_readback.  Scanned: neither Goldd's slot5
            nor 0x02235604 writes any [Rn,#0x74] at all.

            r0 is still the descriptor at +0x1E -- nothing before the BEQ writes it -- and
            0x02207EF4 preserves r4/r6 (it pushes {r3-r7,lr}).  Phase 0x7F is UNUSED by
            0x02207EF5, so this cannot disturb clause 1's own phase chain.
            ⚠️ POP into PC, never into LR (thumb.pop_into_lr).
            """
            base = RES_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R6, R0, #0")
            b.ldr_const(4, PHASE_WORD)
            b.insn("LDR", "R5, [R4, #0x70]")
            b.insn("CMP", f"R5, #0x{PHASE_CLAUSE2:X}")
            b.insn("BEQ", "c2")
            b.bl(ADD_TO_HAND & ~1)
            b.insn("CMP", "R0, #0")
            b.insn("BNE", "ret")
            b.insn("LDRB", "R5, [R6, #0x10]")
            b.insn("CMP", "R5, #0")
            b.insn("BEQ", "ret")
            b.insn("MOV", f"R0, #0x{PHASE_CLAUSE2:X}")
            b.label("ret")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("c2")
            b.insn("MOV", "R1, #1")
            b.insn("MOV", f"R2, #{SS_POSITION_DEFENSE}")
            b.bl(SS_FROM_LIST)
            b.insn("MOV", "R0, #0")
            b.insn("POP", "{R4, R5, R6, PC}")
            blob = b.assemble(base, pad="nop")
            assert len(blob) == 0x30, len(blob)
            return blob


        def slot5_stub(base: int = None) -> bytes:
            """cls2 +14.  Goldd's slot5 step-0 opponent gate, then the native picker.

                +00  LDRB R3,[R0,#0x02]    ; the ACTING side
                +02  LDR  R2,[R0,#0x20]    ; the packed card word
                +04  LSL  R2,R2,#13 ; LSR R2,R2,#31   ; bit 18
                +08  CMP  R3,R2
                +0A  BEQ  SKIP             ; equal -> NOT an opponent's effect
                +0C  LDR  R2,[R0,#0x20]
                +0E  LSL  R2,R2,#22 ; LSR R2,R2,#31   ; bit 9
                +12  CMP  R3,R2
                +14  BNE  SKIP
                +16  LDR  R3,[PC,#..]      ; = 0x02235605                (pool at +0x20)
                +18  BX   R3               ; tail-call the native off-field picker
                +1A  MOVS R0,#1            ; SKIP: end the step machine, ask for nothing
                +1C  BX   LR
                +20  .word 0x02235605

            STATELESS by construction: it never touches the step counter [0x0229AB7C], so
            0x02235604 still sees its own steps 0,1,2...  The tail-call keeps r0 (the
            descriptor), r1 and LR intact, so the picker's own POP returns to OUR caller.
            Returning 1 is the native "skip" convention, read off Goldd's 0x022384CE.
            """
            base = SLOT5_STUB if base is None else base
            b = EffectBuilder()
            b.insn("LDRB", "R3, [R0, #2]")
            b.insn("LDR", "R2, [R0, #0x20]")
            b.insn("LSL", "R2, R2, #13")
            b.insn("LSR", "R2, R2, #31")
            b.insn("CMP", "R3, R2")
            b.insn("BEQ", "skip")
            b.insn("LDR", "R2, [R0, #0x20]")
            b.insn("LSL", "R2, R2, #22")
            b.insn("LSR", "R2, R2, #31")
            b.insn("CMP", "R3, R2")
            b.insn("BNE", "skip")
            b.ldr_const(3, OFFFIELD_PICKER | 1)
            b.insn("BX", "R3")
            b.label("skip")
            b.insn("MOV", "R0, #1")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def row_stub(base: int = None) -> bytes:
            """The criteria-ROW selector: a cid-scoped trampoline on slot5's param provider.

                +00  PUSH {R2}             ; r2's liveness at the call site is NOT established
                +02  LDRH R3,[R5]          ; the descriptor cid (r5 = desc at 0x02235610)
                +04  LDR  R2,[PC,#..]      ; = DONOR_CID                (pool at +0x14)
                +06  CMP  R3,R2
                +08  POP  {R2}             ; LDM does not touch the flags
                +0A  BNE  +0x10
                +0C  MOVS R0,#1            ; nonzero -> LIST A picks criteria ROW 1
                +0E  BX   LR
                +10  LDR  R3,[PC,#..]      ; = 0x02234E79               (pool at +0x18)
                +12  BX   R3               ; every other cid: the native provider, r0 intact
                +14  .word DONOR_CID
                +18  .word 0x02234E79

            r3 is provably dead at the call site (0x02235616 is `ADD R3,R0,#0`), so it is
            the safe scratch; r2 is saved because nothing proves it dead.  r0 (the
            descriptor) and LR are untouched on both paths.
            """
            base = ROW_STUB if base is None else base
            b = EffectBuilder()
            b.insn("PUSH", "{R2}")
            b.insn("LDRH", "R3, [R5, #0]")
            b.ldr_const(2, DONOR_CID)
            b.insn("CMP", "R3, R2")
            b.insn("POP", "{R2}")
            b.insn("BNE", "native")
            b.insn("MOV", "R0, #1")
            b.insn("BX", "LR")
            b.label("native")
            b.ldr_const(3, PARAM_PROVIDER | 1)
            b.insn("BX", "R3")
            return b.assemble(base, pad="nop")


        # ---------------------------------------------------------------------------
        # switch simulation -- the ONLY thing that proves the donor ARRIVES at the arm
        # ---------------------------------------------------------------------------

        def _addhand_leaf(ov: bytes, cid: int, limit: int = 200) -> int:
            """Which arm of the add-to-hand resolver's per-cid switch *cid* reaches."""
            md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
            reg = [0] * 16
            flags = (0, 0)
            pc = ADDHAND_SWITCH_ENTRY
            for _ in range(limit):
                if pc in ADDHAND_STOPS:
                    return pc
                i = next(md.disasm(bytes(ov[_off(pc):_off(pc) + 4]), pc))
                m, ops, nxt = i.mnemonic, i.op_str, pc + i.size
                P = [x.strip() for x in ops.split(",")]

                def rn(t):
                    return int(t[1:]) if t.startswith("r") and t[1:].isdigit() else None

                if m == "b":
                    pc = int(P[0].lstrip("#"), 0)
                    continue
                if m in ("beq", "bne", "bgt", "blt", "bge", "ble"):
                    a, b = flags
                    take = {"beq": a == b, "bne": a != b, "bgt": a > b,
                            "blt": a < b, "bge": a >= b, "ble": a <= b}[m]
                    pc = int(P[0].lstrip("#"), 0) if take else nxt
                    continue
                if m == "ldrh" and "[r5" in ops:
                    reg[rn(P[0])] = cid                     # `LDRH R1,[R5]` = the descriptor cid
                elif m == "ldrb":
                    reg[rn(P[0])] = 0
                elif m == "ldr" and "[pc" in ops:
                    imm = int(re.search(r"#(0x[0-9a-f]+|\d+)\]", ops).group(1), 0)
                    reg[rn(P[0])] = struct.unpack_from("<I", ov, _off(((pc + 4) & ~3) + imm))[0]
                elif m in ("movs", "mov") and P[1].startswith("#"):
                    reg[rn(P[0])] = int(P[1][1:], 0)
                elif m in ("adds", "subs", "add", "sub"):
                    d = rn(P[0])
                    if len(P) == 3:
                        b = int(P[2][1:], 0) if P[2].startswith("#") else reg[rn(P[2])]
                        a = reg[rn(P[1])]
                    else:
                        a, b = reg[d], int(P[1][1:], 0)
                    reg[d] = (a + b if m.startswith("add") else a - b) & 0xFFFFFFFF
                elif m in ("eors", "eor"):
                    reg[rn(P[0])] ^= reg[rn(P[1])]
                elif m == "cmp":
                    r = int(P[1][1:], 0) if P[1].startswith("#") else reg[rn(P[1])]
                    flags = (reg[rn(P[0])], r)
                else:
                    return pc
                pc = nxt
            raise AssertionError(f"add-to-hand walk for 0x{cid:04X} did not terminate")


        # ---------------------------------------------------------------------------
        # static preconditions -- everything this patch DEPENDS on but never writes
        # ---------------------------------------------------------------------------
        def _assert_preconditions(ov: bytearray) -> None:
            def u16(a):
                return struct.unpack_from("<H", ov, _off(a))[0]

            # the terminal node and its subtree pivot
            assert struct.unpack_from("<I", ov, _off(PIVOT_LIT))[0] == PIVOT_VAL, \
                f"A the subtree pivot literal @0x{PIVOT_LIT:08X} is not 0x{PIVOT_VAL:04X}"
            assert bytes(ov[_off(GATE_ARM):_off(GATE_ARM) + 6]) in (
                GATE_ARM_NATIVE + GATE_TAIL_NATIVE[:2],
                _bl(GATE_ARM, GATE_STUB) + GATE_TAIL_NATIVE[:2]), \
                f"A the terminal node @0x{GATE_ARM:08X} is neither stock nor already patched"
            assert bytes(ov[_off(GATE_ARM + 4):_off(GATE_ARM + 4) + 6]) == GATE_TAIL_NATIVE, \
                f"A the kept tail @0x{GATE_ARM + 4:08X} drifted -- Lich Lord/reject would break"

            # the Dark World arm still gates on zone HAND / event 0x1F / kind
            assert u16(DW_ARM) == 0x980D and u16(DW_ARM + 2) == 0x280B, \
                "A the Dark World arm no longer tests SOURCE zone == 0x0B (the hand)"
            assert u16(DW_ARM + 6) == 0x9806, "A the arm's event-code test drifted"
            assert u16(DW_ARM + 12) == 0x9804, "A the arm's relocation-KIND test drifted"
            assert u16(DW_ARM + 14) == 0x2800 and u16(DW_ARM + 16) == 0xDD00, \
                "A the arm's `CMP R0,#0 ; BLE reject` drifted"
            # ... and the caller still hands it r3 = 1 - kind
            for addr, hw in (KIND_MOV_R6, KIND_SUB):
                assert u16(addr) == hw, \
                    f"A 0x{addr:08X} = 0x{u16(addr):04X}, expected 0x{hw:04X} (r3 = 1 - kind)"

            # nothing may branch into the halfwords PART A overwrites, or into the stub
            for lo, hi, what in ((GATE_ARM + 2, GATE_ARM + 4, "the displaced CMP"),
                                 (GATE_STUB, GATE_STUB + GATE_STUB_LEN, "the stub block")):
                for a in range(RAM_BASE, RAM_BASE + len(ov) - 1, 2):
                    w = struct.unpack_from("<H", ov, a - RAM_BASE)[0]
                    t = None
                    if (w & 0xF800) == 0xE000:
                        o = w & 0x7FF
                        t = a + 4 + ((o - 0x800) if o & 0x400 else o) * 2
                    elif (w & 0xF000) == 0xD000 and (w & 0x0F00) < 0x0E00:
                        o = w & 0xFF
                        t = a + 4 + ((o - 0x100) if o & 0x80 else o) * 2
                    assert not (t is not None and lo <= t < hi), \
                        f"A a branch @0x{a:08X} targets {what} -- PART A is unsafe"

            # the stub block is stock (or already ours)
            blk = bytes(ov[_off(GATE_STUB):_off(GATE_STUB) + GATE_STUB_LEN])
            assert blk in (GATE_STUB_NATIVE, gate_stub()), \
                f"A ov3 dead block 0x{GATE_STUB:08X} is neither stock nor ours: {blk.hex()}"

            # the reference rows this patch copies its shape from
            rows = [struct.unpack_from(POP_FMT, ov, _off(POP_BASE + i * POP_STRIDE))
                    for i in range(POP_COUNT)]
            assert SCARR_ROW in rows, "C Scarr's criteria row drifted -- the handler mapping rests on it"
            assert TOON_ROW in rows, "C Toon Table of Contents' criteria row drifted"

            # the donor really is records-free everywhere this patch does not write
            for base, count, stride, name in ((0x0227E64C, 0x51A, 24, "cls0"),
                                              (0x022860D4, 0x535, 24, "cls1"),
                                              (0x02279D74, 0x308, 24, "cls3")):
                assert DONOR_CID not in _keys(ov, base, count, stride, True), \
                    f"the donor gained a {name} record -- it is no longer records-free"

            # LIST B must never hold the donor -- clause 2 deliberately uses LIST A, so that
            # this patch cannot collide with gates_of_dark_world's LIST B / L2 claims.
            assert DONOR_CID not in _keys(ov, LIST_B, LIST_B_COUNT, 2, False), \
                "C the donor is in LIST B; clause 2 must use LIST A (Gates owns LIST B's phantom)"

            # -- clause 2's own preconditions --------------------------------------
            assert h_u16(ov, LIST_A_COUNT_IMM) == (0x2200 | LIST_A_COUNT), \
                f"F the LIST A count immediate @0x{LIST_A_COUNT_IMM:08X} is not movs r2,#0x{LIST_A_COUNT:02X}"
            assert h_u16(ov, LIST_A_RULE_SITE) == 0x2C00, \
                "F LIST A's rule is no longer `cmp r4,#0` -- row = (param != 0) may not hold"
            # the Goldd template must be intact: this patch is a clone of its structure
            g = _keys(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, True)
            assert g.count(GOLDD_CID) == 1, "the Goldd template lost its cls2 record"
            rec = struct.unpack_from("<6I", ov, _off(CLS2_BASE + g.index(GOLDD_CID) * CLS2_STRIDE))
            assert rec == GOLDD_CLS2, \
                f"the Goldd template record drifted: {[hex(x) for x in rec]}"
            # phase 0x7F really is unused by the add-to-hand resolver.  The dispatch is
            # `ADD R0,R0,R0 ; ADD R0,PC ; LDRH R0,[R0,#6] ; ... ; ADD PC,R0` at
            # 0x02207FE2..0x02207FEC, so the TABLE is read from 0x02207FEE but the branch
            # base is `ADD PC` + 4 = 0x02207FF0 -- two bytes apart, and getting that wrong
            # points every arm one halfword early.
            jt, jt_base = 0x02207FEE, 0x02207FF0
            arm7f = jt_base + struct.unpack_from("<h", ov, _off(jt + 7 * 2))[0]
            assert h_u16(ov, arm7f) == 0x2000 and h_u16(ov, arm7f + 2) == 0xBDF8, \
                (f"G phase 0x7F is no longer a bare `movs r0,#0 ; pop` (arm 0x{arm7f:08X}) -- "
                 f"clause 2 would collide with clause 1's phase chain")
            # slot5's param call is still the stock provider call (59 callers; ours is scoped)
            assert _bl_target(ov, PARAM_CALL_SITE) in (PARAM_PROVIDER, ROW_STUB), \
                f"G 0x{PARAM_CALL_SITE:08X} no longer calls the param provider -- another patch took it"
            assert h_u16(ov, 0x02235628) == 0x8829, \
                "G r5 is no longer the live descriptor in the off-field picker"


        def g_index(ov: bytearray, cid: int) -> int:
            """Index of *cid*'s cls2 record."""
            return _keys(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, True).index(cid)


        def h_u16(ov: bytearray, addr: int) -> int:
            return struct.unpack_from("<H", ov, _off(addr))[0]


        def _bl_target(ov: bytearray, site: int) -> int:
            w0, w1 = h_u16(ov, site), h_u16(ov, site + 2)
            assert (w0 & 0xF800) == 0xF000 and (w1 & 0xF800) == 0xF800, f"0x{site:08X} is not a BL"
            hi = w0 & 0x7FF
            if hi & 0x400:
                hi -= 0x800
            return (site + 4) + (hi << 12) + ((w1 & 0x7FF) << 1)


        def _assert_arm9_setcode(rom) -> list[int]:
            """The donor must already be a 'Dark World' card.  Read-only."""
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
            d = bytes(sec.data)
            thunk = struct.unpack_from("<I", d, DW_THUNK_SLOT - ARM9_BASE)[0]
            assert thunk == DW_THUNK, \
                f"the set-code 0x0F thunk is 0x{thunk:08X}, expected 0x{DW_THUNK:08X}"
            lst = list(struct.unpack_from(f"<{DW_LIST_COUNT}H", d, DW_LIST - ARM9_BASE))
            assert DONOR_CID in lst, \
                f"the donor 0x{DONOR_CID:04X} is not in the Dark World set-code list"
            assert all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)), \
                "the Dark World set-code list is not sorted"
            return lst


        # ---------------------------------------------------------------------------
        # overlay-3 half
        # ---------------------------------------------------------------------------
        def apply_effect(ov: bytearray) -> None:
            """PARTS A/B/C."""
            _assert_preconditions(ov)

            # -- PART A: the trigger ---------------------------------------------------
            stub = gate_stub()
            effect_verify.assert_thumb1_only(stub, GATE_STUB)
            ov[_off(GATE_STUB):_off(GATE_STUB) + GATE_STUB_LEN] = stub
            hook = _bl(GATE_ARM, GATE_STUB)
            effect_verify.assert_thumb1_only(hook, GATE_ARM)
            ov[_off(GATE_ARM):_off(GATE_ARM) + 4] = hook
            print(f"A  gate: 0x{GATE_ARM:08X} BL -> stub 0x{GATE_STUB:08X} ({GATE_STUB_LEN} B); "
                  f"0x{DONOR_CID:04X} -> arm 0x{DW_ARM:08X}, 0x{LICH_CID:04X} -> 0x{LICH_ARM:08X}")
            md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
            for ins in md.disasm(stub, GATE_STUB):
                print(f"     0x{ins.address:08X}: {ins.mnemonic:8s} {ins.op_str}")

            # -- PART B: the cls2 record ----------------------------------------------
            leaf = _addhand_leaf(bytes(ov), DONOR_CID)
            assert leaf == ADDHAND_DEFAULT_ARM, (
                f"B the donor reaches add-to-hand arm 0x{leaf:08X}, not the default "
                f"0x{ADDHAND_DEFAULT_ARM:08X} -- it would run a NAMED card's count override")
            _insert_sorted(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, "<6I",
                           CLS2_NEW, CLS2_DROP_PHANTOM,
                           f"B  cls2 (+04 0x{ADD_TO_HAND:08X}, rest 0 = MANDATORY)", wide=True)

            # -- PART C: the criteria row ---------------------------------------------
            _insert_sorted(ov, POP_BASE, POP_COUNT, POP_STRIDE, POP_FMT,
                           CRIT_NEW, POP_DROP_PHANTOM,
                           f"C  criteria (aux 0x{CRIT_AUX:04X} = Dark World, DECK, any card type)",
                           wide=False)

            # ==== CLAUSE 2 ==========================================================
            # -- PART E: the second criteria row (opponent's GY), adjacent to row 0 ----
            _insert_sorted_dup(ov, POP_BASE, POP_COUNT, POP_STRIDE, POP_FMT,
                               CRIT_ROW2, POP_DROP_PHANTOM2,
                               f"E  criteria row 1 (fn 0x{CRIT_HANDLER2:08X} = opponent's GY)")

            # -- PART F: LIST A membership => row = (param != 0) ? 1 : 0 --------------
            _list_insert(ov, LIST_A, LIST_A_COUNT, DONOR_CID, LIST_A_DROP,
                         "F  LIST A (two-row criteria pair)")

            # -- PART G: cid-scope slot5's param provider so IT reads row 1 -----------
            # The add-to-hand resolver's own provider call @0x02208028 is untouched, so
            # clause 1 keeps reading row 0 (the Deck row).
            if _bl_target(ov, PARAM_CALL_SITE) != ROW_STUB:
                ov[_off(PARAM_CALL_SITE):_off(PARAM_CALL_SITE) + 4] = _bl(PARAM_CALL_SITE, ROW_STUB)
            print(f"G  slot5 param provider: 0x{PARAM_CALL_SITE:08X} BL -> 0x{ROW_STUB:08X} "
                  f"(cid-scoped; every other cid still reaches 0x{PARAM_PROVIDER:08X})")

            # -- PART H: the cls2 record grows the clause-2 slots ---------------------
            c2 = _keys(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, True)
            rec_off = _off(CLS2_BASE + c2.index(DONOR_CID) * CLS2_STRIDE)
            struct.pack_into("<6I", ov, rec_off, *CLS2_NEW2)
            print(f"H  cls2 = {{+04 0x{RES_STUB | 1:08X} resolver, +08 0, "
                  f"+0C 0x{SLOT3_ALWAYS:08X}, +10 0, +14 0x{SLOT5_STUB | 1:08X} target}}")

            # -- the whole-table proof: only the donor's routing changed ---------------
            _assert_switch_unchanged(bytes(ov))


        def _assert_switch_unchanged(ov: bytes, stock: bytes | None = None) -> None:
            """Every cid but the donor keeps its stock leaf; the donor gains the DW arm."""
            if stock is None:
                # the stock overlay 3, read from the base ROM
                from otn_enhanced.rom import stock as _stock
                stock = _stock.ov3()
            for cid in range(0, 0x2700):
                now = _switch_leaf(ov, cid)
                was = _switch_leaf(stock, cid)
                if cid == DONOR_CID:
                    assert was == SWITCH_END and now == DW_ARM, (
                        f"R donor 0x{cid:04X}: stock leaf 0x{was:08X}, patched 0x{now:08X} "
                        f"(expected 0x{SWITCH_END:08X} -> 0x{DW_ARM:08X})")
                elif cid in EXTRA_SWITCH_DONORS:
                    # Either state is legitimate: whether that patch has been applied
                    # yet depends on chain order (this module runs BEFORE grapha).
                    # What must never happen is the cid landing on some THIRD arm.
                    want = EXTRA_SWITCH_DONORS[cid]
                    assert now in (was, want), (
                        f"R cid 0x{cid:04X} is registered as another patch donor bound for "
                        f"0x{want:08X}, but reaches 0x{now:08X} (stock 0x{was:08X})")
                else:
                    assert now == was, (
                        f"R cid 0x{cid:04X} changed leaf: 0x{was:08X} -> 0x{now:08X}")
            extra = "".join(f", 0x{c:04X} -> 0x{a:08X}" for c, a in sorted(EXTRA_SWITCH_DONORS.items()))
            print(f"R  switch walk over 0x2700 cids: only 0x{DONOR_CID:04X} moved "
                  f"(-> 0x{DW_ARM:08X}){extra}; 0x{LICH_CID:04X} still -> 0x{LICH_ARM:08X}")



        def install(rom, view):
            ov = view.buf
            lst = _assert_arm9_setcode(rom)
            print(f"0  ARM9 Dark World set code 0x0F (thunk 0x{DW_THUNK:08X}, list 0x{DW_LIST:08X}, "
                  f"{len(lst)} entries) already contains the donor 0x{DONOR_CID:04X}")

            apply_effect(ov)

            # -- CLAUSE 2's ov5 stubs -------------------------------------------------
            md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
            for blob, addr, reserve, label in (
                    (res_stub(), RES_STUB, RES_STUB_RESERVE, "I  resolver (cls2 +04)"),
                    (slot5_stub(), SLOT5_STUB, SLOT5_STUB_RESERVE, "I  target declaration (cls2 +14)"),
                    (row_stub(), ROW_STUB, ROW_STUB_RESERVE, "I  criteria-row selector")):
                effect_verify.assert_thumb1_only(blob, addr)
                ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                print(f"{label} @0x{addr:08X} ({len(blob)} B of 0x{reserve:X})")
                for ins in md.disasm(blob, addr):
                    print(f"     0x{ins.address:08X}: {ins.mnemonic:8s} {ins.op_str}")


        def check_fn(c, rom, view):
            ov = bytearray(view.buf)

            def check(cond: bool, msg: str) -> bool:
                c.ok(bool(cond), msg)
                return bool(cond)

            # -- PART A: the hook and the stub -----------------------------------------
            check(bytes(ov[_off(GATE_ARM):_off(GATE_ARM) + 4]) == _bl(GATE_ARM, GATE_STUB),
                  f"A  0x{GATE_ARM:08X} is a BL to the stub 0x{GATE_STUB:08X}")
            check(bytes(ov[_off(GATE_ARM + 4):_off(GATE_ARM + 4) + 6]) == GATE_TAIL_NATIVE,
                  f"A  the kept tail (BNE / B 0x{LICH_ARM:08X} / B 0x{SWITCH_END:08X}) is native")
            stub = bytes(ov[_off(GATE_STUB):_off(GATE_STUB) + GATE_STUB_LEN])
            check(stub == gate_stub(), f"A  stub intact @0x{GATE_STUB:08X} ({GATE_STUB_LEN} B)")
            thumb1 = True
            try:
                effect_verify.assert_thumb1_only(stub, GATE_STUB)
            except Exception:
                thumb1 = False
            check(thumb1, "A  stub is Thumb-1 only (assert_thumb1_only)")

            # -- REACHABILITY: the walk, not the bytes ---------------------------------
            moved = None
            try:
                _assert_switch_unchanged(bytes(ov))
                moved = True
            except AssertionError as e:
                print(f"       {e}")
                moved = False
            check(moved, f"R  0x{DONOR_CID:04X} reaches the Dark World arm 0x{DW_ARM:08X} and "
                         f"NO other cid's leaf changed (walk over 0x2700 cids)")
            check(_switch_leaf(bytes(ov), LICH_CID) == LICH_ARM,
                  f"R  Lich Lord 0x{LICH_CID:04X} still reaches its own arm 0x{LICH_ARM:08X}")
            for cid, name in ((0x1965, "Beiige"), (0x1966, "Broww"), (0x1968, "Sillva"),
                              (0x1969, "Goldd"), (0x1B3E, "Kahkki"), (0x1B3F, "Gren")):
                check(_switch_leaf(bytes(ov), cid) == DW_ARM,
                      f"R  native {name} 0x{cid:04X} still reaches 0x{DW_ARM:08X}")

            # -- the arm's own gate, and the kind plumbing behind it -------------------
            u16 = lambda a: struct.unpack_from("<H", ov, _off(a))[0]
            check(u16(DW_ARM) == 0x980D and u16(DW_ARM + 2) == 0x280B,
                  "A  the arm still gates on SOURCE zone == 0x0B (the hand)")
            check(u16(KIND_MOV_R6[0]) == KIND_MOV_R6[1] and u16(KIND_SUB[0]) == KIND_SUB[1],
                  f"A  0x{EFFECT_DISCARD_MOVER:08X} (kind 0) still reaches the arm as r3 = 1 - kind")

            # -- PART B: the cls2 record ----------------------------------------------
            c2 = _keys(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, True)
            check(c2.count(DONOR_CID) == 1,
                  f"B  exactly one cls2 record for 0x{DONOR_CID:04X} (a second would shadow it "
                  f"via find_event_handler's leftmost-record rule)")
            if DONOR_CID in c2:
                rec = struct.unpack_from("<6I", ov, _off(CLS2_BASE + c2.index(DONOR_CID) * CLS2_STRIDE))
                check(rec == CLS2_NEW2,
                      f"B  cls2 = {{+04 0x{RES_STUB | 1:08X} resolver, +08 0, +0C 0x{SLOT3_ALWAYS:08X}, "
                      f"+10 0, +14 0x{SLOT5_STUB | 1:08X} target declaration}}")
            check(CLS2_DROP_PHANTOM not in c2,
                  f"B  phantom 0x{CLS2_DROP_PHANTOM:04X} dropped from cls2 (count-neutral)")
            check(all(c2[i] <= c2[i + 1] for i in range(CLS2_COUNT - 1)), "B  cls2 sorted")
            check(_addhand_leaf(bytes(ov), DONOR_CID) == ADDHAND_DEFAULT_ARM,
                  f"B  the donor takes the add-to-hand resolver's DEFAULT arm "
                  f"0x{ADDHAND_DEFAULT_ARM:08X} (count r4 = 1), same as Scarr / Toon Table")

            # -- PART C: the criteria row ---------------------------------------------
            rows = [struct.unpack_from(POP_FMT, ov, _off(POP_BASE + i * POP_STRIDE))
                    for i in range(POP_COUNT)]
            pcids = [r[0] for r in rows]
            mine = [i for i, c in enumerate(pcids) if c == DONOR_CID]
            check(len(mine) == 2 and mine[1] == mine[0] + 1,
                  f"C  the donor owns exactly TWO ADJACENT criteria rows {mine} "
                  f"(the row-offset machinery addresses them as leftmost + offset)")
            if len(mine) == 2:
                check(rows[mine[0]] == CRIT_NEW,
                      f"C  ROW 0 = {{aux 0x{CRIT_AUX:04X} Dark World, fn 0x{CRIT_HANDLER:08X} DECK, "
                      f"word 0x{CRIT_WORD:08X} any card type}} -- the 3DS's own Snoww row 0")
                check(rows[mine[1]] == CRIT_ROW2,
                      f"E  ROW 1 = {{aux 0x{CRIT_AUX2:04X}, fn 0x{CRIT_HANDLER2:08X} OPPONENT'S GY, "
                      f"word 0x{CRIT_WORD2:08X} 1 monster}} -- the 3DS's own Snoww row 1")
            check(POP_DROP_PHANTOM not in pcids and POP_DROP_PHANTOM2 not in pcids,
                  f"C  phantoms 0x{POP_DROP_PHANTOM:04X} and 0x{POP_DROP_PHANTOM2:04X} dropped "
                  f"(both inserts count-neutral)")
            check(all(pcids[i] <= pcids[i + 1] for i in range(POP_COUNT - 1)), "C  criteria sorted")
            check(SCARR_ROW in rows and TOON_ROW in rows,
                  "C  Scarr 0x196A and Toon Table of Contents 0x1562 keep their native rows")

            # -- PART F: LIST A membership --------------------------------------------
            la = _keys(ov, LIST_A, LIST_A_COUNT, 2, False)
            check(DONOR_CID in la, "F  the donor is in LIST A (row = (param != 0) ? 1 : 0)")
            check(LIST_A_DROP not in la,
                  f"F  the inert Speed Spell 0x{LIST_A_DROP:04X} dropped (it owned ZERO criteria rows)")
            check(len(la) == LIST_A_COUNT and all(la[i] < la[i + 1] for i in range(len(la) - 1)),
                  f"F  LIST A still {LIST_A_COUNT} STRICTLY sorted entries (it is binary-searched)")
            check(struct.unpack_from("<H", ov, _off(LIST_A_COUNT_IMM))[0] == (0x2200 | LIST_A_COUNT),
                  f"F  LIST A count immediate still movs r2,#0x{LIST_A_COUNT:02X}")
            check(DONOR_CID not in _keys(ov, LIST_B, LIST_B_COUNT, 2, False),
                  "F  the donor is NOT in LIST B -- no collision with gates_of_dark_world")

            # -- PARTS G/I: the row selector and the two other ov5 stubs --------------
            check(_bl_target(ov, PARAM_CALL_SITE) == ROW_STUB,
                  f"G  slot5's param provider call 0x{PARAM_CALL_SITE:08X} reaches the cid-scoped stub")
            check(_bl_target(ov, 0x02208028) == PARAM_PROVIDER,
                  "G  the ADD-TO-HAND resolver's own provider call is UNTOUCHED, so clause 1 "
                  "still reads criteria ROW 0 (the Deck row)")
            ov5 = rom.loadArm9Overlays([ov5_cave.OV5_ID])[ov5_cave.OV5_ID]
            for blob, addr, label in ((res_stub(), RES_STUB, "I  resolver"),
                                      (slot5_stub(), SLOT5_STUB, "I  target declaration"),
                                      (row_stub(), ROW_STUB, "I  criteria-row selector")):
                lo = addr - ov5_cave.OV5_RAM_BASE
                ok_blob = bytes(ov5.data[lo:lo + len(blob)]) == blob
                t1 = True
                try:
                    effect_verify.assert_thumb1_only(blob, addr)
                except Exception:
                    t1 = False
                check(ok_blob and t1, f"{label} intact @0x{addr:08X} ({len(blob)} B, Thumb-1 only)")
            check(struct.unpack_from("<6I", ov, _off(CLS2_BASE + g_index(ov, GOLDD_CID) * CLS2_STRIDE))
                  == GOLDD_CLS2,
                  f"X  the Goldd template 0x{GOLDD_CID:04X} is untouched (this patch clones it)")

            # -- the donor stays records-free where this patch does not write ----------
            check(all(DONOR_CID not in _keys(ov, b, c, 24, True)
                      for b, c in ((0x0227E64C, 0x51A), (0x022860D4, 0x535), (0x02279D74, 0x308))),
                  "X  donor still has no cls0 / cls1 / cls3 record")

            # -- PART D: the visible card ---------------------------------------------
            rom2 = rom
            _, pac_data, archive = _open_pac(rom2)
            off, idx = _find_prop(bytes(pac_data), archive, DONOR_CID)
            f = GC.decode_entry(pac_data[off:off + 8])
            check(f["attribute"] == NEW_ATTRIBUTE and f["race"] == NEW_RACE
                  and f["real_atk"] == NEW_ATK and f["real_def"] == NEW_DEF
                  and f["level"] == 4 and f["card_type_encoded"] == NEW_CARD_TYPE,
                  f"D  card_prop = DARK / Fiend / Lv4 / {NEW_ATK} / {NEW_DEF} / Effect Monster "
                  f"(got {f['attribute']}/{f['race']}/Lv{f['level']}/{f['real_atk']}/"
                  f"{f['real_def']}/{f['card_type']})")

            names = []
            for L in TEXT_LANGS:
                idxf = next((x for x in archive.files
                             if x.get_clean_name().lower() == f"card_indx_{L}.bin"), None)
                namef = next((x for x in archive.files
                              if x.get_clean_name().lower() == f"card_name_{L}.bin"), None)
                if not (idxf and namef):
                    continue
                no = struct.unpack_from("<I", pac_data, idxf.address + 8 + idx * 8)[0]
                names.append((L, _read_cstr(pac_data, namef.address + no) == NEW_NAME))
            good = [L for L, v in names if v]
            check(len(good) >= 6,
                  f"D  name reads \"{NEW_NAME.decode()}\" in {len(good)}/{len(names)} languages "
                  f"({''.join(good)}; j/k name slots are 20 B < 28 B)")

            # -- the ARM9 set code (read-only dependency) ------------------------------
            lst = _assert_arm9_setcode(rom2)
            check(DONOR_CID in lst,
                  f"X  the donor is still in the ARM9 Dark World set-code list "
                  f"(0x{DW_LIST:08X}, {len(lst)} entries) -- Snoww IS a 'Dark World' card")


        return Compiled(installs=(install,), checks=(check_fn,))


snoww_effects = discarded_from_hand_to_graveyard_by_effect_search_dark_world_card_from_deck_and_in_hand_discard_special_summon_from_opponent_graveyard

SPEC = card(0x1C18, snoww_effects())

PROPS = card_props("DARK", "Fiend", level=4, atk=1700, defense=0, card_type="Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_snoww.nds")

DONOR_CID = 0x1C18          # Renge, Gatekeeper of Dark World (keep-cid rule)

SWITCH_BASE = 0x021D1392            # the per-cid chain inside 0x021D1300
SWITCH_END = 0x021D19C0             # the default REJECT leaf
DW_ARM = 0x021D185C                 # the Dark World effect-discard arm

GATE_STUB = 0x021B56B8
GATE_STUB_LEN = 16

# Other patches may hook the SAME 0x021D1392 chain with their own ov3 stubs (the
# first is grapha PART H, which admits its donor to the very same Dark World
# arm).  _switch_leaf must WALK THROUGH those stubs, or every cid routed via a
# hooked node looks like it changed leaf and this module's whole-table regression
# check fails on a patch that changed nothing.  Registered as (base, length).
EXTRA_SWITCH_STUBS: list[tuple[int, int]] = []


# cid -> the arm another patch DELIBERATELY moves it to.  The regression walk
# below asserts that nothing but this module's donor changed leaf; a second patch
# admitting its own donor to the same chain is a legitimate change, not a
# regression, and has to say so rather than be silently tolerated.
EXTRA_SWITCH_DONORS: dict[int, int] = {}


def register_switch_stub(base: int, length: int, donors: dict[int, int] | None = None) -> None:
    """Declare another patch's ov3 stub so _switch_leaf walks into it.

    *donors* maps each cid that patch intentionally re-routes to the arm it
    should now reach.
    """
    if (base, length) not in EXTRA_SWITCH_STUBS:
        EXTRA_SWITCH_STUBS.append((base, length))
    if donors:
        EXTRA_SWITCH_DONORS.update(donors)


def _in_stub(pc: int) -> bool:
    if GATE_STUB <= pc < GATE_STUB + GATE_STUB_LEN:
        return True
    return any(b <= pc < b + n for b, n in EXTRA_SWITCH_STUBS)


def _read_cstr(buf: bytes, start: int) -> bytes:
    return buf[start:buf.index(b"\x00", start)]


def _switch_leaf(ov: bytes, cid: int, limit: int = 800) -> int:
    """Which leaf of the 0x021D1392 chain *cid* reaches, following PART A's stub.

    Models only ldr-literal / movs / adds / subs / cmp / b / bcc / bl / bx lr;
    anything else STOPS and is reported as the leaf, so the walk can never
    silently guess a wrong arm.  Sound here because every base in the routing
    path is a pc-relative literal, never an [sp,#n] slot -- the condition
    thumb.stack_based_switch_footgun demands be checked before trusting a
    register-only simulator.
    """
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    reg = [0] * 16
    reg[5] = cid
    lr = 0
    flags = (0, 0)
    pc = SWITCH_BASE
    for _ in range(limit):
        if not (SWITCH_BASE <= pc < SWITCH_END or _in_stub(pc)):
            return pc
        try:
            i = next(md.disasm(bytes(ov[_off(pc):_off(pc) + 4]), pc))
        except StopIteration:
            return pc
        m, ops, nxt = i.mnemonic, i.op_str, pc + i.size
        P = [x.strip() for x in ops.split(",")]

        def rn(t):
            return int(t[1:]) if t.startswith("r") and t[1:].isdigit() else None

        if m == "b":
            pc = int(P[0].lstrip("#"), 0)
            continue
        if m in ("beq", "bne", "bgt", "blt", "bge", "ble"):
            a, b = flags
            take = {"beq": a == b, "bne": a != b, "bgt": a > b,
                    "blt": a < b, "bge": a >= b, "ble": a <= b}[m]
            pc = int(P[0].lstrip("#"), 0) if take else nxt
            continue
        if m == "bl":
            tgt = int(P[0].lstrip("#"), 0)
            if _in_stub(tgt):
                lr, pc = nxt | 1, tgt
                continue
            return tgt                              # a long-branch exit == the leaf
        if m == "bx":
            if P[0] == "lr":
                pc = lr & ~1
                continue
            # An INDIRECT tail (`LDR Rd,[PC,#imm] ; BX Rd`) is followed ONLY inside a
            # registered stub, where the value provably came from a literal load out
            # of this same image rather than from unmodelled code.  Eclipse Wyvern's
            # gate stub ends this way; grapha's uses a direct BL instead.
            d = rn(P[0])
            if d is not None and _in_stub(pc) and reg[d]:
                pc = reg[d] & ~1
                continue
            return pc
        if m == "ldr" and "[pc" in ops:
            imm = int(re.search(r"#(0x[0-9a-f]+|\d+)\]", ops).group(1), 0)
            d = rn(P[0])
            if d is None:
                return pc
            reg[d] = struct.unpack_from("<I", ov, _off(((pc + 4) & ~3) + imm))[0]
        elif m in ("movs", "mov") and P[1].startswith("#"):
            reg[rn(P[0])] = int(P[1][1:], 0)
        elif m in ("adds", "subs", "add", "sub"):
            d = rn(P[0])
            if d is None:
                return pc
            if len(P) == 3:
                s = rn(P[1])
                if s is None:
                    return pc
                b = int(P[2][1:], 0) if P[2].startswith("#") else (
                    reg[rn(P[2])] if rn(P[2]) is not None else None)
                if b is None:
                    return pc
                a = reg[s]
            else:
                a = reg[d]
                if not P[1].startswith("#"):
                    return pc
                b = int(P[1][1:], 0)
            reg[d] = (a + b if m.startswith("add") else a - b) & 0xFFFFFFFF
        elif m == "cmp":
            l = rn(P[0])
            if l is None:
                return pc
            r = int(P[1][1:], 0) if P[1].startswith("#") else (
                reg[rn(P[1])] if rn(P[1]) is not None else None)
            if r is None:
                return pc
            flags = (reg[l], r)
        else:
            return pc
        pc = nxt
    raise AssertionError(f"switch walk for 0x{cid:04X} did not terminate")


def _iter_paths(folder, prefix=""):
    for f in getattr(folder, "files", []) or []:
        yield f"{prefix}{f}"
    folders = getattr(folder, "folders", []) or []
    items = folders.items() if isinstance(folders, dict) else folders
    for item in items:
        if isinstance(item, tuple) and len(item) >= 2:
            yield from _iter_paths(item[1], prefix=f"{prefix}{item[0]}/")


def _open_pac(rom):
    pac_path = next((p for p in _iter_paths(rom.filenames)
                     if p.lower().endswith("bin2.pac")), None)
    if pac_path is None:
        raise RuntimeError("bin2.pac not found in ROM")
    fid = rom.filenames.idOf(pac_path)
    data = bytearray(rom.files[fid])
    return fid, data, parse_pac(bytes(data), pac_path)


def _find_prop(pac_data: bytes, archive, cid: int) -> tuple[int, int]:
    cpf = next((f for f in archive.files
                if f.get_clean_name().lower() == "card_prop.bin"), None)
    if cpf is None:
        raise RuntimeError("card_prop.bin not found in bin2.pac")
    body_start = cpf.address + 8
    for i in range((cpf.size - 8) // 8):
        o = body_start + i * 8
        if int.from_bytes(pac_data[o:o + 8], "little") & 0x3FFF == cid:
            return o, i
    raise RuntimeError(f"card_id 0x{cid:04X} not found in card_prop.bin")


# Names the KB proofs (card.snoww_unlight_of_dark_world) read from this module, verbatim.
DW_LIST, DW_LIST_COUNT = 0x0209CA06, 16
LICH_CID, LICH_ARM = 0x1BEB, 0x021D1902   # the terminal node's native occupant
PIVOT_LIT = 0x021D1590              # the subtree's pool literal
PIVOT_VAL = 0x1B8B                  # = Radiant Jeral; r0 holds this at GATE_ARM
GATE_ARM = 0x021D15EE               # the terminal node cid 0x1C18 actually reaches
GATE_ARM_NATIVE = bytes.fromhex("60308542")       # ADD R0,#0x60 ; CMP R5,R0
GATE_TAIL_NATIVE = bytes.fromhex("00d185e1e3e1")  # BNE +0 ; B Lich ; B reject
GATE_STUB_NATIVE = bytes.fromhex("03980121081af7f773fc00282addfa20")
DONOR_DELTA = DONOR_CID - PIVOT_VAL       # 0x8D
LICH_DELTA = DONOR_CID - LICH_CID         # 0x2D
CLS2_DROP_PHANTOM = 0x1B45
ADDHAND_DEFAULT_ARM = 0x02207FCC
CRIT_HANDLER = 0x0223CAF5    # search the DECK, add to hand (== 3DS 0x004B1C1C)
POP_DROP_PHANTOM = 0x14E7
def _bl(site: int, target: int) -> bytes:
    """Encode a 32-bit ARMv4T Thumb BL from *site* to *target*."""
    offset = (target - (site + 4)) & 0x7FFFFF
    return struct.pack("<HH", 0xF000 | ((offset >> 12) & 0x7FF), 0xF800 | ((offset >> 1) & 0x7FF))
def gate_stub(base: int = GATE_STUB) -> bytes:
    """Admit the donor; hand Lich Lord's native test back to the caller's BNE.

        +0   ADDS R0,#0x8D    ; r0 = 0x1B8B + 0x8D = 0x1C18   (the donor)
        +2   CMP  R5,R0
        +4   BEQ  +12         ; our cid -> the Dark World arm
        +6   SUBS R0,#0x2D    ; r0 = 0x1C18 - 0x2D = 0x1BEB   (Lich Lord)
        +8   CMP  R5,R0       ; the displaced test: sets Z for the caller's BNE
        +10  BX   LR          ; -> 0x021D15F2 (BX never writes the flags)
        +12  BL   0x021D185C  ; the Dark World effect-discard arm; never returns

    No literal pool: both cids are reachable from the pivot 0x1B8B that r0
    already holds, with 2-operand ADD/SUB imm8 (the thumb.add_sub_imm3 footgun
    only applies to the 3-operand form).

    Register safety on all three exits: the accept path reaches 0x021D199E
    `MOV R0,#1`, the reject path 0x021D19C0 `MOV R0,#0`, and the Dark World arm
    0x021D185C opens `LDR R0,[SP,#0x34]` -- r0 is dead on every one.  LR is free
    because 0x021D1300 pushed it at entry and returns via POP {...,PC}; the arm
    itself never reads LR.
    """
    b = EffectBuilder()
    b.insn("ADD", f"R0, #0x{DONOR_DELTA:X}")
    b.insn("CMP", "R5, R0")
    b.insn("BEQ", "dw")
    b.insn("SUB", f"R0, #0x{LICH_DELTA:X}")
    b.insn("CMP", "R5, R0")
    b.insn("BX", "LR")
    b.label("dw")
    b.bl(DW_ARM)
    blob = b.assemble(base, pad="nop")
    assert len(blob) == GATE_STUB_LEN, len(blob)
    return blob
def _addhand_leaf(ov: bytes, cid: int, limit: int = 200) -> int:
    """Which arm of the add-to-hand resolver's per-cid switch *cid* reaches."""
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    reg = [0] * 16
    flags = (0, 0)
    pc = ADDHAND_SWITCH_ENTRY
    for _ in range(limit):
        if pc in ADDHAND_STOPS:
            return pc
        i = next(md.disasm(bytes(ov[_off(pc):_off(pc) + 4]), pc))
        m, ops, nxt = i.mnemonic, i.op_str, pc + i.size
        P = [x.strip() for x in ops.split(",")]

        def rn(t):
            return int(t[1:]) if t.startswith("r") and t[1:].isdigit() else None

        if m == "b":
            pc = int(P[0].lstrip("#"), 0)
            continue
        if m in ("beq", "bne", "bgt", "blt", "bge", "ble"):
            a, b = flags
            take = {"beq": a == b, "bne": a != b, "bgt": a > b,
                    "blt": a < b, "bge": a >= b, "ble": a <= b}[m]
            pc = int(P[0].lstrip("#"), 0) if take else nxt
            continue
        if m == "ldrh" and "[r5" in ops:
            reg[rn(P[0])] = cid                     # `LDRH R1,[R5]` = the descriptor cid
        elif m == "ldrb":
            reg[rn(P[0])] = 0
        elif m == "ldr" and "[pc" in ops:
            imm = int(re.search(r"#(0x[0-9a-f]+|\d+)\]", ops).group(1), 0)
            reg[rn(P[0])] = struct.unpack_from("<I", ov, _off(((pc + 4) & ~3) + imm))[0]
        elif m in ("movs", "mov") and P[1].startswith("#"):
            reg[rn(P[0])] = int(P[1][1:], 0)
        elif m in ("adds", "subs", "add", "sub"):
            d = rn(P[0])
            if len(P) == 3:
                b = int(P[2][1:], 0) if P[2].startswith("#") else reg[rn(P[2])]
                a = reg[rn(P[1])]
            else:
                a, b = reg[d], int(P[1][1:], 0)
            reg[d] = (a + b if m.startswith("add") else a - b) & 0xFFFFFFFF
        elif m in ("eors", "eor"):
            reg[rn(P[0])] ^= reg[rn(P[1])]
        elif m == "cmp":
            r = int(P[1][1:], 0) if P[1].startswith("#") else reg[rn(P[1])]
            flags = (reg[rn(P[0])], r)
        else:
            return pc
        pc = nxt
    raise AssertionError(f"add-to-hand walk for 0x{cid:04X} did not terminate")


# Names the KB proofs (card.snoww_unlight_of_dark_world) read from this module, verbatim.
ADDHAND_SWITCH_ENTRY = 0x02207EF6
ADDHAND_STOPS = (0x02207FCC, 0x02207F36, 0x02207F42, 0x02207F46, 0x02207F80, 0x02207F8A)


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
