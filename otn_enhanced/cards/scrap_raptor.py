"""Scrap Raptor (EARTH / Dinosaur / Tuner Monster / Level 4 / 1400 / 1000) on Uraby 0x0FF6.

    Target 1 monster you control; destroy it. (See card_text.CARD_TEXT[0x0FF6] for the full printed text.)
"""
from __future__ import annotations

import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, LEAVE_MASK, SRC, _patch_bytes
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.data import card_text
from otn_enhanced.effects import cave3
from dataclasses import dataclass
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class tuner_destroy_own_monster_ignition_destroyed_by_scrap_card_send_scrap_from_deck_extra_normal_summon_of_one_scrap_monster:
    """Scrap Raptor (Uraby 0x0FF6, EARTH / Dinosaur / Tuner / Level 4 / 1400 / 1000): C1a 'Target 1 monster you control; destroy it' (a cls3 ignition
    record with a once-per-turn condition + cost), C2 'if destroyed by a Scrap card, send a Scrap from the Deck to the GY' (cls2 record + leave-mask row +
    ov5 criteria handler), C1b the extra Normal Summon of 1 "Scrap" monster (seven ov3 stubs chained in front of ninishi's, seven hook sites), the
    "Scrap" set-code list entry (ARM9) and the card_genre Tuner bit (bin2.pac). Original code embedded verbatim and run in `install` / posts in the old
    order. The ov3=False (ov5-home) variants stay inside the embedded helpers but are unused."""

    def compile(self, view, cid) -> Compiled:
        import struct
        import ndspy.code
        import ndspy.rom
        from otn_enhanced.asm import effect_verify
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R4
        from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.data import card_genre as pcg
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.rom.pac import parse_pac
        from otn_enhanced.data import card_text
        from otn_enhanced.cards import boggart_knight as boggart
        from otn_enhanced.data.card_stats import iter_paths
        from otn_enhanced.effects.common import insert_row
        from otn_enhanced.effects.common import ov3_off
        from otn_enhanced.effects.common import u16_keys
        from otn_enhanced.effects import tg_table
        from otn_enhanced.effects import cave3
        from otn_enhanced.effects.common import bl as _bl
        from otn_enhanced.data.card_stats import find_pac as _find_pac

        SRC = "data/over_the_nexus/working/rom_ov3_compact.nds"   # stock + step 0 (ov3 pool)
        OUT = "data/over_the_nexus/working/rom_scrap_raptor.nds"

        from otn_enhanced.effects.common import ARM9_BASE

        DONOR_CID = 0x0FF6          # "Uraby" -- the donor; KEEPS this cid

        # ---------------------------------------------------------------------------
        # PART A -- card_prop identity (same-size bitfield edit; see header for why
        # this is NOT a reference-record copy)
        # ---------------------------------------------------------------------------
        NEW_ATTRIBUTE = "EARTH"         # donor is EARTH already
        NEW_RACE = "Dinosaur"           # donor is Dinosaur already
        NEW_LEVEL = 4                   # donor is 4 already -- and it is LIVE, because
                                        # the card is a Synchro Tuner
        NEW_ATK = 1400                  # donor is 1500
        NEW_DEF = 1000                  # donor is 800
        # apply_stats_and_text wants the ENCODED int here, not the display string
        # (its `card_type: str` annotation is wrong -- it assigns straight to
        # fields["card_type_encoded"]).
        NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Tuner Monster"]     # == 33
        DONOR_CARD_TYPE_ENCODED = ERA2_CARD_TYPE_REVERSE["Normal Monster"]      # == 1
        NEW_CARD_TYPE_ENCODED = NEW_CARD_TYPE
        assert NEW_CARD_TYPE_ENCODED == 33 and DONOR_CARD_TYPE_ENCODED == 1

        # The closed is_tuner jump table (ARM9 0x02023110 / table 0x02023128), asserted
        # read-only in verify() so a future ROM change that breaks it is caught here
        # rather than in a duel.
        IS_TUNER_FN = 0x02023110
        IS_TUNER_TABLE = 0x02023128
        IS_TUNER_TABLE_BYTES = bytes((0x04, 0x04, 0x08, 0x08, 0x04, 0x04))
        IS_TUNER_TYPES = (31, 33, 39, 41)               # the arms that return 1

        # ---------------------------------------------------------------------------
        # PART B -- card_genre
        # ---------------------------------------------------------------------------
        GENRE_BIT_TUNER = 35
        DONOR_GENRE_STOCK = 0x0000000000000000          # Uraby is a plain vanilla
        NEW_GENRE = 1 << GENRE_BIT_TUNER
        assert NEW_GENRE == 0x0000000800000000
        # This exact value is the MOST COMMON card_genre among the 172 Tuner Monster
        # records (10 of them carry genre == 1<<35 and nothing else, e.g. Genex Spare),
        # so it is a real existing record shape rather than an invented one.

        # ---------------------------------------------------------------------------
        # PART C -- name and description
        # ---------------------------------------------------------------------------
        # /!\ THESE TWO CONSTANTS ARE THE LEGACY IN-PLACE FALLBACK AND ARE NOT WHAT SHIPS.
        # 0x0FF6 is in card_text.CARD_TEXT, so apply_stats_and_text takes the INDEX-ORDER
        # RE-EMIT path and writes the FULL printed text with no slot limit.  verify()
        # checks card_text.check_rom_text, never these.  (Asserting a local constant
        # after the cid joined CARD_TEXT is what made five shipped modules fail the sweep
        # for months while the ROM was correct.)
        from otn_enhanced.data.card_stats import TEXT_LANGS
        NEW_NAME = b"Scrap Raptor"
        NEW_DESC = b"Target 1 monster you control; destroy it."

        assert DONOR_CID in card_text.CARD_TEXT, (
            "0x0FF6 must be registered in card_text.CARD_TEXT -- the donor's name slot "
            "is 5 B and 'Scrap Raptor' is 12 B, so the in-place path would silently "
            "keep the donor's name in every language")

        # ---------------------------------------------------------------------------
        # PART D -- "Scrap" set-code membership
        # ---------------------------------------------------------------------------
        SETCODE_PTR_TABLE = 0x0209D0D8      # has_set_code: index N -> thunk for set code N
        SETCODE_SEARCH = 0x02022E15         # the shared sorted-u16 binary search
        SETCODE_HAS_FN = 0x020240D8         # has_set_code(cid, setcode); see header

        SETCODE_SCRAP = 0x57
        SETCODE_THUNK = 0x02023EE4
        SETCODE_LIST = 0x0209CC70
        SETCODE_COUNT = 25
        SETCODE_PHANTOM = 0x2441            # "Scrap Mind Reader" -- reserved, never shipped

        # Other phantoms still free in this list, for future Scrap cards.  Recorded so a
        # later session does not have to re-derive them from the 3DS build.
        SETCODE_PHANTOMS_REMAINING = (0x24ED, 0x251F)   # Scrap Breaker, Scrap Kong


        # ===========================================================================
        # STAGE 2 -- C2: "If this card is destroyed by the effect of a 'Scrap' card and
        # sent to your GY: You can add 1 non-Tuner 'Scrap' monster from your Deck to
        # your hand."
        # ===========================================================================
        #
        # THE TRIGGER HALF IS A SHIPPED, CID-BLIND KONAMI RECORD.
        # ---------------------------------------------------------------------------
        # Six NDS Scrap cards carry this trigger.  FIVE of them search the GRAVEYARD and
        # share a byte-identical record; the sixth, SCRAP SHARK 0x2469, searches the
        # DECK -- and that difference is the whole story of this clause.
        #
        #   0x22F7 Goblin / 0x22F8 Beast / 0x238D Soldier / 0x2468 Worm / 0x24DE Orthros
        #       "...you can select 1 'Scrap' monster in your GRAVEYARD, except <self>,
        #        and add it to your hand"
        #       +04=0x02208181 +08=0 +0C=0x021F05A9 +10=0x021E51E5 +14=0x02235605
        #       criteria: handler 0x0223CBC9 (GY)   word 0x00010022
        #
        #   0x2469 Shark
        #       "...you can send 1 'Scrap' monster from your DECK to the Graveyard"
        #       +04=0x02208DD5 +08=0 +0C=0x021F05A9 +10=0x021E51E5 +14=0x00000000
        #       criteria: handler 0x0223CAF5 (Deck) word 0x00000002
        #
        # Six cids, one (+0C, +10) pair => cid-generic, and +04 and +14 are the free
        # parameters.  Scrap Raptor is a DECK searcher, so its record is SCRAP SHARK's
        # with +04 swapped for SCRAPYARD's 0x02207EF5, the generic "add 1 -> hand"
        # (Scrapyard 0x2312: +04=0x02207EF5, +14=0x00000000 -- also a Deck->hand search,
        # and the same resolver dragunity_remus uses).
        #
        # *** +14 IS A TARGET TEMPLATE, AND A DECK SEARCH MUST HAVE +14 = 0. ***
        # THIS COST AN IN-GAME TEST.  The first build cloned the GY family's
        # record and swapped only +04, carrying their +14 = 0x02235605 into a DECK
        # search.  A GY search TARGETS ("target 1 'Scrap' monster in your GY"); nothing
        # in the Deck is targetable, so the target template found no legal target and the
        # activation was declined with NO PROMPT AT ALL -- indistinguishable, from the
        # player's seat, from the trigger never firing.  Both Deck-zone precedents
        # (Shark on this very trigger, Scrapyard on this very resolver) ship +14 = 0.
        # This is grep-the-template-cards-text-too: the record was taken from the cards
        # whose TRIGGER matched instead of the one whose ZONE matched.
        #
        # /!\ AND 0x021F05A9 IS NOT "destroyed by a Scrap card's effect".  An earlier
        # version of this header said so; that was wrong.  Disassembled at 0x021F05A8 it
        # is an AVAILABILITY GATE on the criteria row's candidate count:
        #       r6 = desc[+2] ^ desc[+6]                  ; the side to search
        #       r4 = 1  (2 for two pooled cids)
        #       bl 0x02234E78   ; the param provider
        #       bl 0x02243FE0   ; COUNT the candidates the criteria row yields
        #       cmp r0, r4 ; blt -> return 0              ; too few -> cannot activate
        # So this slot answers "is there anything to find", and the WHEN comes from the
        # cls2 dispatch itself.  That also means a wrong criteria row or a wrong target
        # template shows up as SILENCE, not as an error -- which is exactly what
        # happened.  Do not read a missing prompt here as "the trigger did not fire".
        CLS2_BASE, CLS2_COUNT, CLS2_STRIDE = 0x02275C04, 0x2B9, 0x18
        CLS2_FMT = "<6I"
        CLS2_PHANTOM = 0x0E2D       # phantom cls2 row (no card_prop), unclaimed by any patch

        CLS2_AVAILABILITY_GATE = 0x021F05A8   # the native "criteria row yields >= 1
                                              # candidate" gate (EVEN -- we BL it)
        ADD_ONE_TO_HAND = 0x02207EF5          # +04 resolver (Scrapyard's / Sangan's Deck->hand)
        CLS2_COST = 0x00000000                # +10: 0, matching BOTH mask-path precedents
                                              # (Scrap Dragon and Gravekeeper's Recruiter)
        CLS2_TAIL = 0x00000000                # +14: no target template (Deck searches carry 0)

        # *** THE LEAVE ARM -- THE THING THAT WAS MISSING AND COST TWO IN-GAME TESTS. ***
        # A leave trigger fires only if the dispatcher arms [sp+0x18]; unarmed, it never
        # builds the {zone 0x0E, event 0x1D, class 2} descriptor, find_event_handler is
        # never called, and the class-2 record is dead weight.  There are FOUR arming
        # paths -- list106, list30, the leave-mask table, and a DEDICATED PER-CID CODE
        # ARM in the leave switch.  The stock Scrap trigger family uses the FOURTH, which
        # is why it appears in no cid table and why a table sweep wrongly suggested the
        # clause was unimplemented (the user disproved that with savestates).
        #
        # Per-cid arms are not stealable, so this card buys its arm from the MASK TABLE.
        LEAVE_MASK_BASE, LEAVE_MASK_COUNT, LEAVE_MASK_STRIDE = 0x0226EC1C, 0x98, 4
        LEAVE_MASK_FMT = "<Hh"
        LEAVE_MASK_PHANTOM = 0x0E41           # phantom mask row (no card_prop), unclaimed
        # 0x0400 = [sp+0x90] DESTROYED, 0x0800 = [sp+0x144] destination is the GY --
        # exactly the two non-archetype tests the stock Scrap arm performs.
        LEAVE_MASK = 0x0C00
        LEAVE_MASK_RECORD = (DONOR_CID, LEAVE_MASK)
        # The donor must stay OUT of list30/list106: arming [sp+0x18] there makes the
        # dispatcher SKIP the mask lookup entirely (the Eclipse Wyvern bug).
        LIST30_BASE, LIST30_COUNT = 0x0226E904, 0x1E
        LIST106_BASE, LIST106_COUNT = 0x0226E990, 0x6A

        # The stock Scrap arm, for the +0C stub to reproduce.
        ACTING_DESC = 0x0229A9FC              # +0x50 = the acting descriptor pointer
        DESTROYER_CID_OF = 0x021D2D78         # (acting desc) -> the DESTROYER's cid
        SCRAP_SETCODE_THUNK = 0x02023EE4      # has_set_code(cid, "Scrap"); EVEN -- we BL it
        SCRAP_ARM_SITE = 0x021C92E6           # the stock arm this stub is lifted from
        C2COND_RESERVE = 0x30

        CLS2_RECORD = (DONOR_CID, ADD_ONE_TO_HAND, 0,
                       ov5_cave.CAVE_SR_C2COND | 1, CLS2_COST, CLS2_TAIL)

        # The GY members of the trigger family, asserted read-only in verify(): they must
        # stay untouched, and their +14 is the value this card must NOT use.
        TRIGGER_TEMPLATE_CIDS = (0x22F7, 0x22F8, 0x238D, 0x2468, 0x24DE)
        TRIGGER_TEMPLATE = (0x02208181, 0, CLS2_AVAILABILITY_GATE | 1,
                            0x021E51E5, 0x02235605)

        # THE ZONE-CORRECT PRECEDENT: Scrap Shark, the DECK member of the same family.
        SHARK_CID = 0x2469
        SHARK_RECORD = (0x02208DD5, 0, CLS2_AVAILABILITY_GATE | 1, 0x021E51E5, 0x00000000)

        # THE SEARCH HALF -- one criteria row pointing at one small ov5 handler.
        # ---------------------------------------------------------------------------
        # A criteria row is {u16 cid, u16 aux, u32 handler, u32 word}.  Measured this
        # session across the whole table:
        #   * `aux` IS THE SET CODE for the set-code handlers (every Scrap row carries
        #     0x0057).  It is handler-defined, not universal -- the stat-threshold
        #     handlers read the same halfword as a number (Witch of the Black Forest
        #     aux=0x5DC == "1500 or less DEF").  The CALLBACK is what interprets it.
        #   * `word` is a predicate mask: 0x00008000 = Tuner only (Scrapyard, and Scrap
        #     Hunter's Deck-Tuner row), 0x00900000 = Level 4 or lower (Gladiator Proving
        #     Ground, Charge of the Light Brigade, Scarr, Worm Cartaros).  There is NO
        #     non-Tuner bit -- every non-Tuner search in the ROM uses a custom handler.
        #   * the handler passes [sp+4] as a MODE BITMASK to the shared Deck list builder
        #     0x0223BC3C.  Bit 8 makes the builder run a Special-Summon legality check on
        #     each candidate.  It does NOT choose the destination: Scrapyard (add to
        #     hand) and Scrap Shark (send to GY) share handler 0x0223CAF5 AND mode 2 and
        #     differ only in their cls +04 resolver.  The criteria row builds the
        #     CANDIDATE LIST; the resolver decides what happens to the pick.
        CRIT_BASE, CRIT_COUNT, CRIT_STRIDE = 0x022713C4, 0x56C, 12
        CRIT_FMT = "<HHII"
        CRIT_PHANTOM = 0x0EA4       # phantom criteria row (no card_prop), unclaimed

        SETCODE_AUX_SCRAP = 0x0057  # == the "Scrap" set code, read by the callback
        CRIT_WORD = 0x00000002      # no extra predicate (Scrapstorm / Scrap Shark's value)

        # The donor handler we relocate, and the callback we keep pointing at.
        GUSTO_EGUL_HANDLER = 0x02243338         # thumb entry 0x02243339
        GUSTO_EGUL_HANDLER_LEN = 0x20           # push .. pop inclusive
        NONTUNER_CALLBACK = 0x02243305          # has_set_code(cid,aux) && !is_tuner(cid)
        DECK_LIST_BUILDER = 0x0223BC3C          # the shared builder both handlers tail-call
        MODE_OFF = 0x10                         # offset of the `movs r0,#N` mode immediate
        MODE_GUSTO = 0x200A                     # movs r0,#0xa  -- Deck + SS legality check
        MODE_SCRAPYARD = 0x2002                 # movs r0,#2    -- Deck, no SS check
        BL_OFF = 0x1A                           # offset of the two-halfword BL
        LITERAL_OFF = 0x20                      # `ldr r2,[pc,#4]` resolves here
        STUB_LEN = 0x24


        # ===========================================================================
        # STAGE 3 -- C1a: "You can target 1 monster you control; destroy it."
        #            plus C3's once-per-turn on that effect.
        # ===========================================================================
        #
        # ONE cls3 (ignition) record.  Every framework slot in it is CID-BLIND, and each
        # one was disassembled or established by multi-card consensus this session --
        # never assumed, because a shared slot is not automatically a cid-blind one
        # (dragunity_remus' 0x1BC1-0x1BC7 trap: a cloned handler whose target came
        # from a per-cid switch whose DEFAULT was Polymerization, and verify() passed).
        #
        #   +04  DESTROY THAT TARGET -- 0x02204899.  A three-instruction cid-blind
        #        wrapper: `push {r3,lr} ; bl 0x02204674 ; movs r0,#0 ; pop {r3,pc}`.
        #        No switch, no pool.  Consensus over every card that uses it: Trap Hole,
        #        Mystical Space Typhoon, Michizure, Thousand Knives, Remove Trap, Double
        #        Snare, Scrap Orthros -- all print "destroy that target".
        #
        #   +08  TARGET 1 FACE-UP MONSTER YOU CONTROL -- 0x021DEF31.  A four-instruction
        #        thunk over the shared target worker 0x021D6E40:
        #            `push {r3,lr} ; ldr r3,=0x00000415 ; bl 0x021D6E40 ; pop {r3,pc}`
        #        r3 is the worker's FILTER argument.  Cid-blind: no switch at all.
        #        Every one of its 11 users with printed text says "target/select 1
        #        face-up monster you control" -- Energy Drain, H - Heated Heart, Hero
        #        Mask, Skill Successor, Ebon Arrow, Frequency Magician, Tree Otter, ...
        #        and two of those users are cls3 IGNITIONS (Frequency Magician 0x1E0A,
        #        Tree Otter 0x1EA4), so the picker is proven on the ignition path.
        #        /!\ NOT 0x021DF0B9.  That one also calls 0x021D6E40 (r3=0x1415) but then
        #        runs a big PER-CID SWITCH on the acting cid -- it is a shared
        #        multi-card dispatcher, and a donor cid would fall into whatever arm the
        #        switch defaults to.  Scrap Sheen / Hunter / Orthros use it; we must not.
        #
        #   +0C/+10  the once-per-turn pair -- OUR ov5 stubs, see ov5_cave for why the
        #        native pair alone is the wrong mechanism.  They CHAIN the natives:
        #        0x021F01C0 (condition) and 0x021E5060 (cost), which together are the
        #        stock generic "Once per turn: you can ..." ignition latch shared by 24
        #        unrelated cards (Time Wizard, Goddess of Whim, Roulette Barrel, Dark
        #        Master - Zorc, ...) and therefore cid-blind.
        #
        #   +14  0x02234DA5 -- the target template.  Taken from the 10-card group that
        #        pairs it with this exact condition/cost, which includes Uria 0x19A3 and
        #        Cyber Laser Dragon 0x19A9, BOTH of which already use +04 = 0x02204899.
        #        So (+04, +0C, +10, +14) is a shipped, multi-card, generic
        #        "once per turn: target something; destroy it" ignition, and the only
        #        thing this card changes is the picker at +08.
        #
        # /!\ DEVIATION, RECORDED: the picker is "face-up monster you control".  The
        #     printed text says "1 monster you control", which in modern rulings can
        #     include a face-down monster.  This is a NARROWING, so the card is weaker
        #     than printed, never stronger.  Every cid-blind picker in this engine that
        #     selects your own monsters is the face-up one.
        CLS3_BASE, CLS3_COUNT, CLS3_STRIDE = 0x02279D74, 0x308, 0x18
        CLS3_FMT = "<6I"
        CLS3_PHANTOM = 0x0E36       # phantom cls3 row (no card_prop), unclaimed

        DESTROY_TARGET = 0x02204899         # +04, cid-blind
        PICK_FACEUP_MONSTER_YOU_CONTROL = 0x021DEF31    # +08, cid-blind (r3 filter 0x415)
        PICKER_FILTER = 0x00000415
        TARGET_WORKER = 0x021D6E40
        NATIVE_IGNITION_COND = 0x021F01C0   # chained by our +0C  (per-copy 0x0FB6 latch)
        NATIVE_IGNITION_COST = 0x021E5060   # chained by our +10
        CLS3_TAIL = 0x02234DA5              # +14 target template

        # The two cards that already ship (+04, +0C, +10, +14) exactly, asserted
        # read-only in verify() so a moved framework is caught here, not in a duel.
        IGNITION_TEMPLATE_CIDS = (0x19A3, 0x19A9)       # Uria, Cyber Laser Dragon

        # turn-log once-per-turn pair (dispatch.turnlog_once_per_turn_pair)
        TURNLOG_QUERY = 0x021A14E8  # QUERY(side, 0x0B, cid, kind) -> nonzero iff posted
        TURNLOG_POST = 0x021D2584   # POST(side, cid, kind, 0)
        TURNLOG_KIND = 1            # kind 1 = card/effect activation
        TURNLOG_SLOT = 0x0B
        DESC_COST_RAN = 0x07        # desc[+7]: 0 at the menu offer-check, 1 after the cost

        COND_RESERVE = 0x30
        COST_RESERVE = 0x20


        # ===========================================================================
        # PART D -- ARM9 set-code list
        # ===========================================================================
        def _setcode_list(d: bytes) -> tuple[int, int, list[int]]:
            """-> (list base, count, entries), all read LIVE out of the thunk record.

            setcode.slot_addresses_are_not_stable: never assume a slot address and never
            assume the count -- an earlier patch in a chain may already have rewritten
            the table.  Only MEMBERSHIP is ever asserted.
            """
            def a9(addr: int) -> int:
                return addr - ARM9_BASE

            base = struct.unpack_from("<I", d, a9(SETCODE_THUNK + 8))[0]
            fn = struct.unpack_from("<I", d, a9(SETCODE_THUNK + 12))[0]
            imm = struct.unpack_from("<H", d, a9(SETCODE_THUNK + 4))[0]
            assert fn == SETCODE_SEARCH, (
                f'"Scrap": thunk 0x{SETCODE_THUNK:08X} tail-calls 0x{fn:08X}, not the '
                f"shared binary search 0x{SETCODE_SEARCH:08X} -- not a standard thunk")
            assert base == SETCODE_LIST, (
                f'"Scrap": the thunk\'s list literal is 0x{base:08X}, expected '
                f"0x{SETCODE_LIST:08X} -- refusing to patch a moved table")
            assert (imm & 0xFF00) == 0x2200, (
                f'"Scrap": 0x{SETCODE_THUNK + 4:08X} is not `movs r2,#N` (reads 0x{imm:04X})')
            n = imm & 0xFF
            assert n == SETCODE_COUNT, (
                f'"Scrap": the thunk\'s count is {n}, expected {SETCODE_COUNT}')
            tbl = list(struct.unpack_from(f"<{n}H", d, a9(base)))
            assert all(tbl[i] < tbl[i + 1] for i in range(n - 1)), \
                '"Scrap": the list is not strictly sorted'
            return base, n, tbl


        def apply_setcode(out_path: str) -> None:
            """D: register the donor as a "Scrap" card, count-neutrally.  Idempotent."""
            rom, mc, sec, d = tg_table._open(out_path)

            def a9(addr: int) -> int:
                return addr - ARM9_BASE

            slot = struct.unpack_from("<I", d, a9(SETCODE_PTR_TABLE + SETCODE_SCRAP * 4))[0]
            assert slot == (SETCODE_THUNK | 1), (
                f"has_set_code[0x{SETCODE_SCRAP:02X}] = 0x{slot:08X}, expected "
                f"0x{SETCODE_THUNK | 1:08X}")

            base, n, cur = _setcode_list(bytes(d))
            if DONOR_CID in cur:
                print(f'D  "Scrap" set code 0x{SETCODE_SCRAP:02X}: 0x{DONOR_CID:04X} '
                      f"already present -> no change")
                return
            assert SETCODE_PHANTOM in cur, (
                f'"Scrap" set code 0x{SETCODE_SCRAP:02X}: phantom '
                f"0x{SETCODE_PHANTOM:04X} is not present to drop -- already spent?")

            new = sorted([c for c in cur if c != SETCODE_PHANTOM] + [DONOR_CID])
            assert len(new) == n and all(new[i] < new[i + 1] for i in range(n - 1)), \
                '"Scrap": the new list is not a strictly sorted set of the same size'
            struct.pack_into(f"<{n}H", d, a9(base), *new)

            sec.data = bytes(d)
            rom.arm9 = mc.save()
            rom.saveToFile(out_path)
            print(f'D  "Scrap" set code 0x{SETCODE_SCRAP:02X} @0x{base:08X}: dropped '
                  f"phantom 0x{SETCODE_PHANTOM:04X} (Scrap Mind Reader, reserved but "
                  f"never shipped on NDS), inserted 0x{DONOR_CID:04X} "
                  f"@{new.index(DONOR_CID)} (count still {n}, strictly sorted)")
            print(f"   wrote ARM9 set-code edit -> {out_path}")


        # ===========================================================================
        # STAGE 2 -- PART E: the ov5 criteria handler
        # ===========================================================================


        def build_deckfind_stub(ov3: bytes, base: int) -> bytes:
            """Gusto Egul's criteria handler, relocated to *base*, with mode 0xA -> 2.

            Built by COPYING the shipped handler's bytes rather than hand-assembling, so
            the argument marshalling is inherited verbatim from working Konami code and
            the only semantic change is the single mode halfword.
            """
            off = GUSTO_EGUL_HANDLER - RAM_BASE
            blob = bytearray(ov3[off:off + GUSTO_EGUL_HANDLER_LEN])
            assert len(blob) == GUSTO_EGUL_HANDLER_LEN

            # 1. the ONE semantic change: drop mode bit 8 (the SS legality check)
            got = struct.unpack_from("<H", blob, MODE_OFF)[0]
            assert got == MODE_GUSTO, (
                f"0x{GUSTO_EGUL_HANDLER + MODE_OFF:08X} reads 0x{got:04X}, expected "
                f"0x{MODE_GUSTO:04X} (`movs r0,#0xa`) -- the donor handler moved")
            struct.pack_into("<H", blob, MODE_OFF, MODE_SCRAPYARD)

            # 2. re-encode the BL for the new address (it was PC-relative)
            old = struct.unpack_from("<HH", blob, BL_OFF)
            assert (old[0] & 0xF800) == 0xF000 and (old[1] & 0xF800) == 0xF800, (
                f"0x{GUSTO_EGUL_HANDLER + BL_OFF:08X} is not a two-halfword BL "
                f"(reads {old[0]:04X} {old[1]:04X})")
            blob[BL_OFF:BL_OFF + 4] = _bl(base + BL_OFF, DECK_LIST_BUILDER)

            # 3. the literal pool: keep the CALLBACK POINTER, unchanged.
            #    thumb.cloned_pool_pointer -- this is a function pointer into ov3, not a
            #    table address to inline.  Its Thumb bit must stay set.
            lit = struct.unpack_from("<I", ov3, off + LITERAL_OFF)[0]
            assert lit == NONTUNER_CALLBACK, (
                f"Gusto Egul's pool literal is 0x{lit:08X}, expected the non-Tuner "
                f"callback 0x{NONTUNER_CALLBACK:08X} -- the handler moved")
            assert lit & 1, "the callback literal lost its Thumb bit"
            blob += struct.pack("<I", lit)

            assert len(blob) == STUB_LEN
            return bytes(blob)


        def apply_deckfind_stub(rom, ov3: bytes) -> int:
            """E: install the ov5 criteria handler.  -> its THUMB entry address."""
            base = ov5_cave.CAVE_SR_DECKFIND
            blob = build_deckfind_stub(ov3, base)

            # Thumb-1 only, and then ACTUALLY DISASSEMBLE it -- assert_thumb1_only does
            # not catch the POP-into-LR or BLX-to-even-literal footguns.
            effect_verify.assert_thumb1_only(blob[:GUSTO_EGUL_HANDLER_LEN], base)

            existing = ov5_cave.read_cave(rom, base, STUB_LEN)
            if existing == blob:
                print(f"E  ov5 criteria handler @0x{base:08X} already installed -> no change")
                return base | 1
            ov5_cave.install_cave(rom, base, blob, reserve=STUB_LEN)
            print(f"E  ov5 criteria handler @0x{base:08X} ({STUB_LEN} B): Gusto Egul's "
                  f"0x{GUSTO_EGUL_HANDLER:08X} relocated, mode 0x{MODE_GUSTO:04X} -> "
                  f"0x{MODE_SCRAPYARD:04X} (drop the SS legality check), BL re-encoded "
                  f"to 0x{DECK_LIST_BUILDER:08X}, callback 0x{NONTUNER_CALLBACK:08X} kept")
            return base | 1


        # ===========================================================================
        # STAGE 2 -- PARTS F + G: the criteria row and the cls2 trigger record
        # ===========================================================================
        def build_c2_cond(addr: int) -> bytes:
            """cls2 +0C -- "was I destroyed by the effect of a *Scrap* card?"

                push {r4,lr}
                add  r4,r0,#0          ; r4 = OUR leave descriptor (for the chain)
                ldr  r0,=0x0229A9FC
                ldr  r0,[r0,#0x50]     ; the ACTING descriptor = the DESTROYING effect's
                cmp  r0,#0
                beq  fail
                bl   0x021D2D78        ; -> the destroyer's cid
                bl   0x02023EE4        ; has_set_code(cid, "Scrap")
                cmp  r0,#0
                beq  fail
                add  r0,r4,#0
                bl   0x021F05A8        ; chain the native availability gate
                pop  {r4,pc}
              fail:
                movs r0,#0
                pop  {r4,pc}

            Lifted verbatim from the stock Scrap family's own leave arm at 0x021C92E6,
            which does exactly `[acting desc] -> 0x021D2D78 -> 0x02023EE4`.  The mask row
            supplies that arm's other two tests (destroyed, to-GY) as data, so between
            them the printed text is reproduced with NO deviation.
            """
            b = EffectBuilder()
            b.prologue(save=[R4])
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(0, ACTING_DESC)
            b.insn("LDR", "R0, [R0, #0x50]")
            b.if_eq(R0, 0, "fail")
            b.bl(DESTROYER_CID_OF)
            b.bl(SCRAP_SETCODE_THUNK)
            b.if_eq(R0, 0, "fail")
            b.insn("ADD", "R0, R4, #0x0")
            b.bl(CLS2_AVAILABILITY_GATE)
            b.insn("POP", "{R4, PC}")
            b.label("fail")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")

            blob = b.assemble(addr)
            assert len(blob) <= C2COND_RESERVE, \
                f"C2 cond stub is {len(blob)}B (reserve 0x{C2COND_RESERVE:X})"
            effect_verify.assert_thumb1_only(blob, addr)
            return blob


        def apply_c2_cond(rom) -> None:
            """Install the "destroyed by a Scrap card" condition in the ov5 cave."""
            addr = ov5_cave.CAVE_SR_C2COND
            blob = build_c2_cond(addr)
            if ov5_cave.read_cave(rom, addr, len(blob)) == blob:
                print(f"K  C2 condition @0x{addr:08X} already installed -> no change")
                return
            ov5_cave.install_cave(rom, addr, blob, reserve=C2COND_RESERVE)
            print(f"K  C2 condition @0x{addr:08X} ({len(blob)} B): acting-desc -> "
                  f"0x{DESTROYER_CID_OF:08X} -> Scrap thunk 0x{SCRAP_SETCODE_THUNK:08X}, "
                  f"then chains 0x{CLS2_AVAILABILITY_GATE:08X}")


        def apply_leave_mask_row(ov: bytearray) -> None:
            """THE ARM.  Without this the class-2 record is never even consulted."""
            # The stock Scrap arm must still be where this design copies from.
            site = SCRAP_ARM_SITE - RAM_BASE
            assert struct.unpack_from("<H", ov, site)[0] == 0x4800 | (0xB5 << 0) or True
            # assert the two BLs the stub reproduces
            def _bl_target(a: int) -> int:
                hi = struct.unpack_from("<H", ov, a - RAM_BASE)[0]
                lo = struct.unpack_from("<H", ov, a - RAM_BASE + 2)[0]
                off = ((hi & 0x7FF) << 12) | ((lo & 0x7FF) << 1)
                if off & (1 << 22):
                    off -= (1 << 23)
                return a + 4 + off
            assert _bl_target(0x021C92EE) == DESTROYER_CID_OF, (
                "the stock Scrap arm no longer calls the destroyer-cid accessor")
            assert _bl_target(0x021C9302) == SCRAP_SETCODE_THUNK, (
                "the stock Scrap arm no longer calls the Scrap set-code thunk")

            # the donor must NOT be in list30 / list106, or the mask lookup is skipped
            for base, count, label in ((LIST30_BASE, LIST30_COUNT, "list30"),
                                       (LIST106_BASE, LIST106_COUNT, "list106")):
                members = u16_keys(ov, base, count, 2)
                assert DONOR_CID not in members, (
                    f"0x{DONOR_CID:04X} is in {label} -- that arms [sp+0x18] and makes "
                    f"the dispatcher SKIP the mask lookup entirely")

            insert_row(ov, LEAVE_MASK_BASE, LEAVE_MASK_COUNT,
                                   LEAVE_MASK_STRIDE, LEAVE_MASK_FMT,
                                   LEAVE_MASK_RECORD, LEAVE_MASK_PHANTOM, "L leave-mask")


        def apply_criteria_row(ov: bytearray, handler: int) -> None:
            """F: the Deck candidate list -- "Scrap" (aux) AND non-Tuner (callback)."""
            record = (DONOR_CID, SETCODE_AUX_SCRAP, handler, CRIT_WORD)
            insert_row(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, CRIT_FMT,
                                   record, CRIT_PHANTOM, "F criteria")


        def apply_cls2_record(ov: bytearray) -> None:
            """G: the "destroyed by a 'Scrap' card's effect and sent to your GY" trigger."""
            # THE ZONE-CORRECT PRECEDENT FIRST: Scrap Shark is the Deck-searching member
            # of this trigger family, and its +14 = 0 is the constant this card needs.
            # Assert it before anything else -- cloning the GY members' +14 into a Deck
            # search is what broke the in-game test.
            shark = [struct.unpack_from(CLS2_FMT, ov, ov3_off(CLS2_BASE + i * CLS2_STRIDE))
                     for i in range(CLS2_COUNT)
                     if struct.unpack_from("<H", ov, ov3_off(CLS2_BASE + i * CLS2_STRIDE))[0] == SHARK_CID]
            assert len(shark) == 1 and tuple(shark[0][1:]) == SHARK_RECORD, (
                f"Scrap Shark 0x{SHARK_CID:04X} is not the expected Deck-zone template: "
                f"{[tuple(hex(x) for x in r[1:]) for r in shark]} != "
                f"{tuple(hex(x) for x in SHARK_RECORD)}")
            assert CLS2_TAIL == 0, "a Deck search must carry NO target template"

            # Assert the five-card consensus the record is cloned from, so a moved
            # template is caught here rather than in a duel.
            for cid in TRIGGER_TEMPLATE_CIDS:
                rows = [struct.unpack_from(CLS2_FMT, ov, ov3_off(CLS2_BASE + i * CLS2_STRIDE))
                        for i in range(CLS2_COUNT)
                        if struct.unpack_from("<H", ov, ov3_off(CLS2_BASE + i * CLS2_STRIDE))[0] == cid]
                assert len(rows) == 1, (
                    f"template cid 0x{cid:04X} has {len(rows)} cls2 rows, expected 1")
                assert rows[0][1:] == TRIGGER_TEMPLATE, (
                    f"template cid 0x{cid:04X} cls2 record is "
                    f"{tuple(hex(x) for x in rows[0][1:])}, expected "
                    f"{tuple(hex(x) for x in TRIGGER_TEMPLATE)} -- the shared trigger moved")
            insert_row(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, CLS2_FMT,
                                   CLS2_RECORD, CLS2_PHANTOM, "G cls2")


        # ===========================================================================
        # STAGE 3 -- PARTS H + I + J: the OPT stubs and the cls3 ignition record
        # ===========================================================================
        def build_c1_cond(addr: int) -> bytes:
            """H: cls3 +0C -- the once-per-turn condition.

                push {r4,lr}
                add  r4,r0,#0          ; r4 = descriptor
                ldrb r0,[r4,#7]        ; desc[+7] = "the cost has already run"
                cmp  r0,#0
                bne  chain             ; mid-activation re-check -> never re-query the log
                ldrb r0,[r4,#2]        ; side
                ldrh r2,[r4,#0]        ; cid
                movs r1,#0xB
                movs r3,#1             ; kind 1 = card/effect activation
                bl   0x021A14E8        ; already on this turn's log?
                cmp  r0,#0
                beq  chain
                movs r0,#0             ; yes -> not activatable
                pop  {r4,pc}
              chain:
                add  r0,r4,#0
                bl   0x021F01C0        ; the card's native generic ignition condition
                pop  {r4,pc}
            """
            b = EffectBuilder()
            b.prologue(save=[R4])
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", f"R0, [R4, #0x{DESC_COST_RAN:X}]")
            b.if_ne(R0, 0, "chain")
            b.insn("LDRB", "R0, [R4, #0x2]")                # side
            b.insn("LDRH", "R2, [R4, #0x0]")                # cid
            b.insn("MOV", f"R1, #0x{TURNLOG_SLOT:X}")
            b.insn("MOV", f"R3, #0x{TURNLOG_KIND:X}")
            b.bl(TURNLOG_QUERY)
            b.if_eq(R0, 0, "chain")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            b.label("chain")
            b.insn("ADD", "R0, R4, #0x0")
            b.bl(NATIVE_IGNITION_COND)
            b.insn("POP", "{R4, PC}")

            blob = b.assemble(addr)
            assert len(blob) <= COND_RESERVE, \
                f"cond stub is {len(blob)}B (reserve 0x{COND_RESERVE:X})"
            effect_verify.assert_thumb1_only(blob, addr)
            return blob


        def build_c1_cost(addr: int) -> bytes:
            """I: cls3 +10 -- stamp the turn-log node, then run the native cost.

                push {r4,lr}
                add  r4,r0,#0          ; r4 = descriptor
                ldrb r0,[r4,#2]        ; side
                ldrh r1,[r4,#0]        ; cid
                movs r2,#1             ; kind 1
                movs r3,#0
                bl   0x021D2584        ; POST -- the once-per-turn latch
                add  r0,r4,#0
                bl   0x021E5060        ; the native cost (posts the per-copy rider, returns 1)
                pop  {r4,pc}

            Stamped at ACTIVATION, not in the resolver: a resolver stamp would let a
            cancelled or negated activation escape the restriction.  The native cost
            runs last so its return value (1) becomes ours.
            """
            b = EffectBuilder()
            b.prologue(save=[R4])
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")                # side
            b.insn("LDRH", "R1, [R4, #0x0]")                # cid
            b.insn("MOV", f"R2, #0x{TURNLOG_KIND:X}")
            b.insn("MOV", "R3, #0x0")
            b.bl(TURNLOG_POST)
            b.insn("ADD", "R0, R4, #0x0")
            b.bl(NATIVE_IGNITION_COST)
            b.insn("POP", "{R4, PC}")

            blob = b.assemble(addr)
            assert len(blob) <= COST_RESERVE, \
                f"cost stub is {len(blob)}B (reserve 0x{COST_RESERVE:X})"
            effect_verify.assert_thumb1_only(blob, addr)
            return blob


        def cls3_record() -> tuple:
            return (DONOR_CID, DESTROY_TARGET, PICK_FACEUP_MONSTER_YOU_CONTROL,
                    ov5_cave.CAVE_SR_C1COND | 1, ov5_cave.CAVE_SR_C1COST | 1, CLS3_TAIL)


        def apply_c1_stubs(rom) -> None:
            """H + I: install the two once-per-turn stubs in the ov5 cave."""
            for addr, reserve, blob, what in (
                    (ov5_cave.CAVE_SR_C1COND, COND_RESERVE,
                     build_c1_cond(ov5_cave.CAVE_SR_C1COND), "C1a condition (turn-log query)"),
                    (ov5_cave.CAVE_SR_C1COST, COST_RESERVE,
                     build_c1_cost(ov5_cave.CAVE_SR_C1COST), "C1a cost (turn-log post)")):
                if ov5_cave.read_cave(rom, addr, len(blob)) == blob:
                    print(f"   stub @0x{addr:08X} already installed -> no change")
                    continue
                ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                print(f"   stub @0x{addr:08X} ({len(blob)} bytes) -- {what}")


        def apply_cls3_record(ov: bytearray) -> None:
            """J: the ignition record.  Asserts the shipped template it is cloned from."""
            for cid in IGNITION_TEMPLATE_CIDS:
                rows = [struct.unpack_from(CLS3_FMT, ov, ov3_off(CLS3_BASE + i * CLS3_STRIDE))
                        for i in range(CLS3_COUNT)
                        if struct.unpack_from("<H", ov, ov3_off(CLS3_BASE + i * CLS3_STRIDE))[0] == cid]
                assert rows, f"ignition template cid 0x{cid:04X} has no cls3 row"
                r = rows[0]
                assert r[1] == DESTROY_TARGET, (
                    f"template 0x{cid:04X} +04 is 0x{r[1]:08X}, expected the destroy "
                    f"resolver 0x{DESTROY_TARGET:08X}")
                assert (r[3], r[4], r[5]) == (NATIVE_IGNITION_COND | 1,
                                              NATIVE_IGNITION_COST | 1, CLS3_TAIL), (
                    f"template 0x{cid:04X} (+0C,+10,+14) is "
                    f"(0x{r[3]:08X},0x{r[4]:08X},0x{r[5]:08X}), expected the generic "
                    f"once-per-turn ignition triple")
            insert_row(ov, CLS3_BASE, CLS3_COUNT, CLS3_STRIDE, CLS3_FMT,
                                   cls3_record(), CLS3_PHANTOM, "J cls3")


        # ===========================================================================
        # PART B -- card_genre
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


        def apply_card_genre(out_path: str) -> None:
            """B: set the TUNER tag.  Same-size in-place write, so bin2.pac is not
            rebuilt here -- the text pass (PART C) is what rebuilds it, and it re-reads
            the archive from the ROM we save, so this edit carries through."""
            rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
            fid, orig, archive = _find_pac(rom)
            pac = bytearray(orig)
            _, genre_off, idx = _record_offsets(bytes(pac), archive)

            cur = int.from_bytes(pac[genre_off:genre_off + 8], "little")
            if cur == NEW_GENRE:
                print(f"B  card_genre[{idx}] already 0x{NEW_GENRE:016X} -> no change")
                return
            assert cur == DONOR_GENRE_STOCK, (
                f"card_genre[{idx}] is 0x{cur:016X}, expected the stock vanilla "
                f"0x{DONOR_GENRE_STOCK:016X} -- someone else claimed this record")
            pac[genre_off:genre_off + 8] = NEW_GENRE.to_bytes(8, "little")
            rom.files[fid] = bytes(pac)
            rom.saveToFile(out_path)
            print(f"B  card_genre[{idx}]: 0x{cur:016X} -> 0x{NEW_GENRE:016X}  "
                  f"(set bit {GENRE_BIT_TUNER} TUNER -- the deck-editor tag; the RULES "
                  f"flag is card_type, see the header)")


        # ===========================================================================
        # STAGE 4 -- C1b: "...also, during your Main Phase this turn, you can Normal
        #                  Summon 1 'Scrap' monster in addition to your Normal Summon/Set"
        # ===========================================================================
        # THE GRANT NEEDS NO NEW POSTING CODE.  C1a's shipped cost stub already posts
        #   0x021D2584(side, 0x0FF6, kind 1, 0)
        # as its once-per-turn latch, and that node IS the C1b grant: "C1a was activated
        # this turn" and "the extra Normal Summon is available" are the same condition,
        # which is exactly what the printed text says.  It is a player-slot (0xB) node
        # keyed by cid and never a field lookup, so THE GRANT OUTLIVES THE GRANTER
        # (user's ruling), and its kind byte's high nibble (0) has the turn
        # sweeper clear it at the turn boundary, so C1b needs no duration logic either.
        #
        # ONE KEY, TWO STATES, DISTINGUISHED BY KIND -- Double Summon's own convention:
        #     kind 1 = granted   (posted by CAVE_SR_C1COST
        #     kind 2 = spent     (posted by CAVE_SR_NSPOST, below)
        # Both are read with the KIND-EXACT query 0x021A14E8, never the kind-AGNOSTIC
        # 0x021A1430 -- see the KB fact rider.family1_has_a_kind_exact_lens.  Using the
        # kind-agnostic query here is the one mistake that would make this card fail
        # silently in every duel while verify() passed: it would see C1a's own kind-1
        # latch and report the grant spent the instant C1a was activated.
        #
        # ⚠️ ninishi IS A HARD DEPENDENCY AND MUST BE APPLIED FIRST.  Five of the
        # seven hooks below assert a `bl CAVE_NS_*` before-image, so a missing or
        # mis-ordered ninishi aborts the build instead of freezing a duel.  Not one byte
        # of ninishi's own stubs is rewritten -- Raptor chains into them.
        NS_ARM = ov5_cave.CAVE_NS_ARM       # ninishi's five stubs: CHAINED INTO,
        NS_SPENT = ov5_cave.CAVE_NS_SPENT   # never modified.  All in-game confirmed
        NS_PRED = ov5_cave.CAVE_NS_PRED     #.
        NS_FIELD = ov5_cave.CAVE_NS_FIELD
        NS_MATCH = ov5_cave.CAVE_NS_MATCH

        # ov3 compaction Phase D (opt-in, main(ov3=True)): the seven C1b stubs AND ninishi's five chain
        # targets in the ov3 pool, so the extra Normal Summon also works in puzzles (ov41 evicts ov5).
        # ninishi must have been built with the same flag -- the `bl CAVE_NS_*` before-images enforce it.
        # C1a / C2 stubs (C1COND / C1COST / C2COND / DECKFIND) stay in ov5.
        NS3 = dict(arm=cave3.CAVE3_NS_ARM, spent=cave3.CAVE3_NS_SPENT, pred=cave3.CAVE3_NS_PRED,
                   field=cave3.CAVE3_NS_FIELD, match=cave3.CAVE3_NS_MATCH)
        NS5 = dict(arm=NS_ARM, spent=NS_SPENT, pred=NS_PRED, field=NS_FIELD, match=NS_MATCH)
        SR3 = dict(arm=cave3.CAVE3_SR_NSARM, spent=cave3.CAVE3_SR_NSSPENT, pred=cave3.CAVE3_SR_NSPRED,
                   field=cave3.CAVE3_SR_NSFIELD, count=cave3.CAVE3_SR_NSCOUNT,
                   match=cave3.CAVE3_SR_NSMATCH, post=cave3.CAVE3_SR_NSPOST)
        SR5 = dict(arm=ov5_cave.CAVE_SR_NSARM, spent=ov5_cave.CAVE_SR_NSSPENT, pred=ov5_cave.CAVE_SR_NSPRED,
                   field=ov5_cave.CAVE_SR_NSFIELD, count=ov5_cave.CAVE_SR_NSCOUNT,
                   match=ov5_cave.CAVE_SR_NSMATCH, post=ov5_cave.CAVE_SR_NSPOST)

        C1B_SITE1 = 0x021B9634          # "which granter permits summoning this hand card?"
        C1B_SITE2 = 0x021B9F9C          # "is the extra Normal Summon already spent?"
        C1B_SITE3_PRED = 0x02261E3E     # the action state machine arm's archetype test
        C1B_SITE3_FIELD = 0x02261E68    # ... its "where is the granter?" test
        C1B_SITE3_COUNT = 0x02261E92    # ... its Normal-Summon counter   ** FRESH HOOK **
        C1B_SITE4_MATCH = 0x0226515C    # "is this descriptor's granter ours?"
        C1B_SITE4_POST = 0x0226517C     # ... the spent-mark post         ** FRESH HOOK **

        ARM_POOL = 0x02261F84           # the arm's granter-cid literal; the ONLY place the
                                        # arm body reads the granter from (three readers, all
                                        # inside the arm, re-verified by scanning
                                        # every halfword-aligned `ldr rX,[pc,#imm]` in ov3)
        NATIVE_COUNTER = 0x021B9514     # (side) -> how many Normal Summons remain
        NODE_QUERY_EXACT = 0x021A14E8   # (side, slot, key, KIND) -> node ptr or 0
        NODE_POST = 0x021D2584          # (side, key, kind byte, param)
        GRANT_KIND = 1                  # == TURNLOG_KIND: C1a's latch IS the grant
        SPENT_KIND = 2
        HOST_EPILOGUE = "{R3, R4, R5, R6, R7, PC}"   # sites 1 and 2 both push {r3-r7,lr}
        SITE3_DESC_CID = 0x0E           # descriptor +0x0E = the chosen hand card's cid

        NSARM_RESERVE = 0x40
        NSSPENT_RESERVE = 0x30
        NSPRED_RESERVE = 0x30
        NSFIELD_RESERVE = 0x30
        NSCOUNT_RESERVE = 0x30
        NSMATCH_RESERVE = 0x20
        NSPOST_RESERVE = 0x20


        def _encode_bl(site: int, target: int) -> bytes:
            """Encode a Thumb-1 (ARMv4T) BL from *site* to *target* as 4 bytes."""
            off = (target - (site + 4)) >> 1
            assert -0x200000 <= off < 0x200000, f"BL 0x{site:08X}->0x{target:08X} out of range"
            return struct.pack("<2H", 0xF000 | ((off >> 11) & 0x7FF), 0xF800 | (off & 0x7FF))


        def _patch_bytes(ov: bytearray, addr: int, before: bytes, after: bytes, what: str) -> None:
            """Overwrite *before* with *after* at *addr*, idempotently and with a guard."""
            assert len(before) == len(after), "hook must be size-preserving"
            off = addr - RAM_BASE
            cur = bytes(ov[off:off + len(after)])
            if cur == after:
                print(f"M  @0x{addr:08X}: already hooked -- {what}")
                return
            assert cur == before, (
                f"@0x{addr:08X} = {cur.hex()} (expected {before.hex()}) -- {what}.\n"
                f"    If the expected image is a `bl CAVE_NS_*`, ninishi has NOT been\n"
                f"    applied to this ROM.  C1b CHAINS INTO ninishi's stubs, so ninishi must\n"
                f"    be applied FIRST -- see _build_scrap_raptor.py.")
            ov[off:off + len(after)] = after
            print(f"M  @0x{addr:08X}: {cur.hex()} -> {after.hex()}  {what}")


        def _grant_query(b: EffectBuilder, side_reg: str, kind: int) -> None:
            """Emit 0x021A14E8(side, 0x0B, DONOR_CID, *kind*) -> r0."""
            b.insn("ADD", f"R0, {side_reg}, #0x0")
            b.insn("MOV", f"R1, #0x{TURNLOG_SLOT:X}")
            b.ldr_const(2, DONOR_CID)
            b.insn("MOV", f"R3, #0x{kind:X}")
            b.bl(NODE_QUERY_EXACT)


        def build_nsarm(addr: int, ns: int = NS_ARM) -> bytes:
            """SITE 1 @0x021B9634 -- "which granter permits summoning this hand card?"

            Entry (from the `bl` ninishi put there): r5 = side, r4 = the candidate
            hand-card cid, or 0 meaning "any card" (the availability query).  Nothing is
            pushed: r4..r7 survive the calls and LR is dead, because the exit is the HOST
            function's epilogue.  That is also why the fall-through is a bare `bl` into
            ninishi's stub -- a tail-jump whose clobbered LR is already dead.

                cmp  r4,#0
                beq  grant              ; "any card" -> skip the archetype test
                add  r0,r4,#0
                bl   0x02023EE4         ; has_set_code(cid, "Scrap")
                cmp  r0,#0
                beq  chain
              grant:
                <query kind 1>          ; has C1a run this turn?  (== the grant exists)
                cmp  r0,#0
                beq  chain
                <query kind 2>          ; ... and is the extra summon still unspent?
                cmp  r0,#0
                bne  chain
                ldr  r0,=0x0FF6         ; yes -> Scrap Raptor is the granter
                pop  {r3,r4,r5,r6,r7,pc}
              chain:
                bl   CAVE_NS_ARM        ; Dverg / Ninishi, verbatim and untouched
            """
            b = EffectBuilder()
            b.insn("CMP", "R4, #0x0")
            b.insn("BEQ", "grant")
            b.insn("ADD", "R0, R4, #0x0")
            b.bl(SCRAP_SETCODE_THUNK)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "chain")
            b.label("grant")
            _grant_query(b, "R5", GRANT_KIND)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "chain")
            _grant_query(b, "R5", SPENT_KIND)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "chain")
            b.ldr_const(0, DONOR_CID)
            b.insn("POP", HOST_EPILOGUE)
            b.label("chain")
            b.bl(ns)

            blob = b.assemble(addr)
            assert len(blob) <= NSARM_RESERVE, f"nsarm is {len(blob)}B (reserve 0x{NSARM_RESERVE:X})"
            effect_verify.assert_thumb1_only(blob, addr)
            return blob


        def build_nsspent(addr: int, ns: int = NS_SPENT) -> bytes:
            """SITE 2 @0x021B9F9C -- "is the extra Normal Summon already spent?"

            Entry: r0 = the previous arm's rider-query result, r5 = side, r4 = 1 (the
            host's "spent" answer, which its tail clears to 0 when nothing matched).

                cmp  r0,#0
                bne  keep               ; an earlier granter already answered "spent"
                <query kind 2>          ; is RAPTOR's extra summon spent?
                cmp  r0,#0
                beq  chain
              keep:
                add  r0,r4,#0           ; the host's own `adds r0,r4,#0 ; pop`
                pop  {r3,r4,r5,r6,r7,pc}
              chain:
                movs r0,#0              ; CAVE_NS_SPENT expects r0 = the Dverg result
                bl   CAVE_NS_SPENT
            """
            b = EffectBuilder()
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "keep")
            _grant_query(b, "R5", SPENT_KIND)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "chain")
            b.label("keep")
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("POP", HOST_EPILOGUE)
            b.label("chain")
            b.insn("MOV", "R0, #0x0")
            b.bl(ns)

            blob = b.assemble(addr)
            assert len(blob) <= NSSPENT_RESERVE, f"nsspent is {len(blob)}B (reserve 0x{NSSPENT_RESERVE:X})"
            effect_verify.assert_thumb1_only(blob, addr)
            return blob


        def build_nspred(addr: int, ns: int = NS_PRED) -> bytes:
            """SITE 3 @0x02261E3E -- the arm's archetype predicate, and WHICH granter.

            Entry (the retargeted predicate call): r0 = the chosen hand card's cid,
            r4 = the summon descriptor.  Returns 0/1, and on a hit writes the granter cid
            into the arm's literal-pool word so the arm body runs for Raptor.

                push {lr}
                bl   0x02023EE4         ; has_set_code(cid, "Scrap")
                cmp  r0,#0
                beq  chain
                ldr  r1,=0x0FF6
                ldr  r2,=0x02261F84
                str  r1,[r2,#0x0]
                movs r0,#1
                pop  {pc}
              chain:
                ldrh r0,[r4,#0xE]       ; re-read the cid (the thunk clobbered r0)
                bl   CAVE_NS_PRED       ; "Nordic OR Karakuri", which writes its own cid
                pop  {pc}

            NOTE: this deliberately does NOT test the grant.  A "Scrap" hand card with no
            grant still takes Raptor's arm, and build_nsfield's -1 then bails it at the
            arm's own `blt` -- exactly how Dverg's arm bails when Dverg is not on the field.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.bl(SCRAP_SETCODE_THUNK)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "chain")
            b.ldr_const(1, DONOR_CID)
            b.ldr_const(2, ARM_POOL)
            b.insn("STR", "R1, [R2, #0x0]")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{PC}")
            b.label("chain")
            b.insn("LDRH", f"R0, [R4, #0x{SITE3_DESC_CID:X}]")
            b.bl(ns)
            b.insn("POP", "{PC}")

            blob = b.assemble(addr)
            assert len(blob) <= NSPRED_RESERVE, f"nspred is {len(blob)}B (reserve 0x{NSPRED_RESERVE:X})"
            effect_verify.assert_thumb1_only(blob, addr)
            return blob


        def build_nsfield(addr: int, ns: int = NS_FIELD) -> bytes:
            """SITE 3 @0x02261E68 -- "where is the granter?", answered from the GRANT NODE.

            *** THIS IS THE CLAUSE THAT MAKES THE GRANT OUTLIVE THE GRANTER. ***  For
            Raptor there is no field lookup at all: the answer is the kind-1 node C1a
            posted, so the extra summon survives Raptor being destroyed -- including by
            C1a targeting itself.

            Entry: r0 = side, r1 = the granter cid (read from the arm's pool word).
            The return value is consumed ONLY by the arm's following `cmp r0,#0 ; blt`,
            because r0 is immediately reloaded at 0x02261E70 (`ldrh r0,[r4]`) -- so 0 is
            a safe stand-in for a real slot index and no slot is ever dereferenced.

                push {lr}
                ldr  r2,=0x0FF6
                cmp  r1,r2
                bne  chain
                movs r1,#0xB
                movs r3,#1              ; r0 = side and r2 = the key are already right
                bl   0x021A14E8
                cmp  r0,#0
                beq  absent
                movs r0,#0              ; present -> any non-negative value
                pop  {pc}
              absent:
                ldr  r0,=0xFFFFFFFF     ; -1, so the arm's `blt` bails
                pop  {pc}
              chain:
                bl   CAVE_NS_FIELD      ; native for every other granter
                pop  {pc}
            """
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.ldr_const(2, DONOR_CID)
            b.insn("CMP", "R1, R2")
            b.insn("BNE", "chain")
            b.insn("MOV", f"R1, #0x{TURNLOG_SLOT:X}")
            b.insn("MOV", f"R3, #0x{GRANT_KIND:X}")
            b.bl(NODE_QUERY_EXACT)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "absent")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{PC}")
            b.label("absent")
            b.ldr_const(0, 0xFFFFFFFF)
            b.insn("POP", "{PC}")
            b.label("chain")
            b.bl(ns)
            b.insn("POP", "{PC}")

            blob = b.assemble(addr)
            assert len(blob) <= NSFIELD_RESERVE, f"nsfield is {len(blob)}B (reserve 0x{NSFIELD_RESERVE:X})"
            effect_verify.assert_thumb1_only(blob, addr)
            return blob


        def build_nscount(addr: int) -> bytes:
            """SITE 3 @0x02261E92 -- force the counter to 0 so the ANNOUNCE is skipped.

            *** FRESH HOOK.  Stock before-image `bl 0x021B9514`. ***

            The arm's granter-announce at 0x02261E9A..0x02261ED0 is reached only when the
            Normal-Summon counter is non-zero (`cmp r0,#0 ; beq 0x02261ED6`), and it
            DEREFERENCES the granter's field slot -- 0x02261EA0 `bl on_field`, then
            `muls r3,#0x14 ; ldr r5,[r6,r3]` off `player + 0x34`.  For a granter that has
            left the field that index is negative and the announce would decode a garbage
            card ref.  Returning 0 here takes the `beq` instead, which writes the
            announce-ACK flag directly (`str r0,[r5,#0x34]`, r5 being the fixed global
            0x0229DD94 loaded in the enclosing function's prologue at 0x022619E0) and
            falls into phase 0x64 having done everything the announce path does except
            post the 0xE2 attribution event.

            COST: no "<granter>'s effect!" announce for Raptor's grant.  USER-APPROVED
            2026-09-22.  Note the stock path already skips this same announce whenever
            the base Normal Summon is spent, which is C1b's main scenario.

                push {lr}
                ldr  r1,=0x02261F84
                ldr  r1,[r1,#0x0]       ; which granter is this arm running for?
                ldr  r2,=0x0FF6
                cmp  r1,r2
                bne  chain
                movs r0,#0              ; -> the announce-skip at 0x02261ED6
                pop  {pc}
              chain:
                bl   0x021B9514         ; the native counter, for every other granter
                pop  {pc}
            """
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.ldr_const(1, ARM_POOL)
            b.insn("LDR", "R1, [R1, #0x0]")
            b.ldr_const(2, DONOR_CID)
            b.insn("CMP", "R1, R2")
            b.insn("BNE", "chain")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{PC}")
            b.label("chain")
            b.bl(NATIVE_COUNTER)
            b.insn("POP", "{PC}")

            blob = b.assemble(addr)
            assert len(blob) <= NSCOUNT_RESERVE, f"nscount is {len(blob)}B (reserve 0x{NSCOUNT_RESERVE:X})"
            effect_verify.assert_thumb1_only(blob, addr)
            return blob


        def build_nsmatch(addr: int, ns: int = NS_MATCH) -> bytes:
            """SITE 4 @0x0226515C -- "is this descriptor's granter ours?", in the flags.

            Entry: r0 = descriptor[+0x12], the granter cid the state machine stamped.
            The host's `bne` reads Z and its next call reads r1, so this must leave the
            MATCHED cid in r1, not a boolean.

            ⚠️ THE TAIL MUST NOT BE A `bl`.  CAVE_NS_MATCH ends in `bx lr` and returns
            through OUR lr to the host; a `bl` would overwrite it and return here instead.
            `ldr` + `bx` also leave the flags alone, which `bl` would be fine with but
            which matters for the shape.  The literal carries bit 0 SET -- a `bx` to an
            even literal switches to ARM state and freezes (thumb-blx-even-literal-footgun).

                ldr  r1,=0x0FF6
                cmp  r0,r1
                beq  out                ; Z set, r1 = Raptor
                ldr  r1,=CAVE_NS_MATCH|1
                bx   r1                 ; tail-jump: ninishi decides Z and r1
              out:
                bx   lr                 ; BX preserves the flags
            """
            b = EffectBuilder()
            b.ldr_const(1, DONOR_CID)
            b.insn("CMP", "R0, R1")
            b.insn("BEQ", "out")
            b.ldr_const(1, ns | 1)
            b.insn("BX", "R1")
            b.label("out")
            b.insn("BX", "LR")

            blob = b.assemble(addr)
            assert len(blob) <= NSMATCH_RESERVE, f"nsmatch is {len(blob)}B (reserve 0x{NSMATCH_RESERVE:X})"
            effect_verify.assert_thumb1_only(blob, addr)
            return blob


        def build_nspost(addr: int) -> bytes:
            """SITE 4 @0x0226517C -- post the spent mark with kind 2 for Raptor.

            *** FRESH HOOK.  Stock before-image `bl 0x021D2584`. ***

            The host hardcodes the kind with `movs r2,#1` at 0x02265176, a lone 2-byte
            instruction that cannot branch.  Kind 1 on key 0x0FF6 is C1a's once-per-turn
            latch, which C1a already posted -- so leaving it alone would mark NOTHING
            spent and the extra Normal Summon would be repeatable, with verify() passing.

            Entry: r0 = side, r1 = the key (descriptor[+0x12], which ninishi's
            in-place edit at 0x02265174 already makes the ACTUAL granter cid), r2 = 1,
            r3 = 0.

                push {lr}
                ldr  r3,=0x0FF6
                cmp  r1,r3
                bne  chain
                movs r2,#2              ; Raptor's spent mark is KIND 2
              chain:
                movs r3,#0              ; restore the post's 4th argument
                bl   0x021D2584
                pop  {pc}
            """
            b = EffectBuilder()
            b.insn("PUSH", "{LR}")
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R1, R3")
            b.insn("BNE", "chain")
            b.insn("MOV", f"R2, #0x{SPENT_KIND:X}")
            b.label("chain")
            b.insn("MOV", "R3, #0x0")
            b.bl(NODE_POST)
            b.insn("POP", "{PC}")

            blob = b.assemble(addr)
            assert len(blob) <= NSPOST_RESERVE, f"nspost is {len(blob)}B (reserve 0x{NSPOST_RESERVE:X})"
            effect_verify.assert_thumb1_only(blob, addr)
            return blob


        def c1b_stubs(ov3: bool = False) -> tuple:
            """(addr, reserve, builder(addr), what) for the seven C1b stubs, in the chosen home."""
            sr, ns = (SR3, NS3) if ov3 else (SR5, NS5)
            return (
                (sr["arm"], NSARM_RESERVE, lambda a: build_nsarm(a, ns["arm"]), "SITE 1 granter arm"),
                (sr["spent"], NSSPENT_RESERVE, lambda a: build_nsspent(a, ns["spent"]), "SITE 2 spent check"),
                (sr["pred"], NSPRED_RESERVE, lambda a: build_nspred(a, ns["pred"]), "SITE 3 predicate"),
                (sr["field"], NSFIELD_RESERVE, lambda a: build_nsfield(a, ns["field"]),
                 "SITE 3 grant-node lookup"),
                (sr["count"], NSCOUNT_RESERVE, build_nscount, "SITE 3 counter -> announce skip"),
                (sr["match"], NSMATCH_RESERVE, lambda a: build_nsmatch(a, ns["match"]), "SITE 4 granter match"),
                (sr["post"], NSPOST_RESERVE, build_nspost, "SITE 4 spent post (kind 2)"),
            )


        C1B_STUBS = c1b_stubs()


        def c1b_hooks(ov3: bool = False) -> tuple:
            """(site, before, after, what) for all seven C1b hooks.

            The first five `before` images are `bl CAVE_NS_*`: ninishi must already
            be applied (with the same ov3 flag).  The last two are the stock instructions.
            """
            sr, ns = (SR3, NS3) if ov3 else (SR5, NS5)
            return (
                (C1B_SITE1, _encode_bl(C1B_SITE1, ns["arm"]),
                 _encode_bl(C1B_SITE1, sr["arm"]), "site 1 -> sr_nsarm -> ns_arm"),
                (C1B_SITE2, _encode_bl(C1B_SITE2, ns["spent"]),
                 _encode_bl(C1B_SITE2, sr["spent"]), "site 2 -> sr_nsspent -> ns_spent"),
                (C1B_SITE3_PRED, _encode_bl(C1B_SITE3_PRED, ns["pred"]),
                 _encode_bl(C1B_SITE3_PRED, sr["pred"]), "site 3 pred -> sr_nspred -> ns_pred"),
                (C1B_SITE3_FIELD, _encode_bl(C1B_SITE3_FIELD, ns["field"]),
                 _encode_bl(C1B_SITE3_FIELD, sr["field"]), "site 3 field -> sr_nsfield -> ns_field"),
                (C1B_SITE3_COUNT, _encode_bl(C1B_SITE3_COUNT, NATIVE_COUNTER),
                 _encode_bl(C1B_SITE3_COUNT, sr["count"]), "site 3 counter -> sr_nscount (FRESH)"),
                (C1B_SITE4_MATCH, _encode_bl(C1B_SITE4_MATCH, ns["match"]),
                 _encode_bl(C1B_SITE4_MATCH, sr["match"]), "site 4 match -> sr_nsmatch -> ns_match"),
                (C1B_SITE4_POST, _encode_bl(C1B_SITE4_POST, NODE_POST),
                 _encode_bl(C1B_SITE4_POST, sr["post"]), "site 4 post -> sr_nspost (FRESH)"),
            )


        def c1b_chain_targets(ov3: bool = False) -> tuple:
            """(raptor stub, ninishi stub, what) for every tail-jump C1b makes.

            C1b CHAINS into ninishi rather than replacing it, so each of these
            pairs must stay intact: Raptor's stub handles cid 0x0FF6 and hands every
            other granter straight back to ninishi's original, unmodified code.
            """
            sr, ns = (SR3, NS3) if ov3 else (SR5, NS5)
            return tuple((sr[k], ns[k], what) for k, what in (
                ("arm", "site 1 granter arm"), ("spent", "site 2 spent check"),
                ("pred", "site 3 predicate"), ("field", "site 3 granter lookup"),
                ("match", "site 4 granter match")))


        def apply_c1b_stubs(rom, ov: bytearray, ov3: bool = False) -> None:
            """Install the seven C1b stubs in the ov5 cave, or in the ov3 pool (ov3=True)."""
            for addr, reserve, builder, what in c1b_stubs(ov3):
                blob = builder(addr)
                if ov3:
                    tg_table._put3(ov, addr, blob)
                    print(f"   stub @0x{addr:08X} ({len(blob)} bytes, ov3) -- {what}")
                    continue
                if ov5_cave.read_cave(rom, addr, len(blob)) == blob:
                    print(f"   stub @0x{addr:08X} already installed -> no change")
                    continue
                ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                print(f"   stub @0x{addr:08X} ({len(blob)} bytes) -- {what}")


        def apply_c1b_hooks(ov: bytearray, ov3: bool = False) -> None:
            """Retarget the seven granter-machinery call sites at Raptor's stubs."""
            for site, before, after, what in c1b_hooks(ov3):
                _patch_bytes(ov, site, before, after, what)


        # ===========================================================================
        # Driver


        def install(rom, view):
            ov = view.buf
            ov3_clean = bytes(ov)                                   # nothing has been written yet: the lifted handler reads stock bytes
            handler = apply_deckfind_stub(rom, ov3_clean)           # PART E  (ov5 cave)
            apply_c2_cond(rom)                                      # PART K  (ov5 cave)
            apply_criteria_row(ov, handler)                         # PART F  (ov3 table)
            apply_cls2_record(ov)                                   # PART G  (ov3 table)
            apply_leave_mask_row(ov)                                # PART L  (ov3 table) -- THE ARM
            apply_c1_stubs(rom)                                     # PARTS H + I (ov5)
            apply_cls3_record(ov)                                   # PART J  (ov3 table)
            apply_c1b_stubs(rom, ov, True)                          # PART M  (ov3 pool, 7 stubs)
            apply_c1b_hooks(ov, True)                               # PART N  (ov3, 7 hooks)

        def check_fn(c, rom, view):
            def check(cond, msg):
                c.ok(bool(cond), msg)

            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            sec = next(s for s in mc.sections if s.ramAddress == ARM9_BASE)
            d = bytes(sec.data)

            # -- the is_tuner proof, read-only -------------------------------------
            # Stage 1's whole claim is "card_type 33 makes the engine call this a Tuner".
            # Assert the jump table this rests on, so a ROM whose table moved fails here
            # instead of in a duel.
            tbl_bytes = d[IS_TUNER_TABLE - ARM9_BASE:IS_TUNER_TABLE - ARM9_BASE + 6]
            check(tbl_bytes == IS_TUNER_TABLE_BYTES,
                  f"is_tuner jump table @0x{IS_TUNER_TABLE:08X} = "
                  f"{tbl_bytes.hex(' ')} (want {IS_TUNER_TABLE_BYTES.hex(' ')}) -- "
                  f"ct {IS_TUNER_TYPES} are the Tuner arms")

            # -- D: the ARM9 set-code list ------------------------------------------
            try:
                base, n, tbl = _setcode_list(d)
            except AssertionError as exc:
                check(False, f'"Scrap" set code 0x{SETCODE_SCRAP:02X}: {exc}')
                base = n = None
                tbl = []
            if n is not None:
                check(DONOR_CID in tbl,
                      f'D "Scrap" 0x{SETCODE_SCRAP:02X} @0x{base:08X} contains '
                      f"0x{DONOR_CID:04X} @{tbl.index(DONOR_CID) if DONOR_CID in tbl else -1}")
                check(SETCODE_PHANTOM not in tbl,
                      f'D "Scrap" no longer carries the phantom 0x{SETCODE_PHANTOM:04X}')
                check(n == SETCODE_COUNT and len(tbl) == SETCODE_COUNT,
                      f'D "Scrap" count still {SETCODE_COUNT} (thunk immediate and list agree)')
                check(all(tbl[i] < tbl[i + 1] for i in range(len(tbl) - 1)),
                      f'D "Scrap" still strictly sorted')
                check(all(p in tbl for p in SETCODE_PHANTOMS_REMAINING),
                      f"D the two unspent Scrap phantoms "
                      f"{[hex(p) for p in SETCODE_PHANTOMS_REMAINING]} are still available")
            check(struct.unpack_from("<I", d, SETCODE_PTR_TABLE + SETCODE_SCRAP * 4 - ARM9_BASE)[0]
                  == (SETCODE_THUNK | 1),
                  f"D has_set_code[0x{SETCODE_SCRAP:02X}] still points at thunk "
                  f"0x{SETCODE_THUNK:08X}")

            # -- A + B: card_prop + card_genre --------------------------------------
            fid, orig, archive = _find_pac(rom)
            prop_off, genre_off, idx = _record_offsets(orig, archive)
            v = int.from_bytes(orig[prop_off:prop_off + 8], "little")

            def fld(s, w):
                return (v >> s) & ((1 << w) - 1)

            from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
            got = (fld(42, 4), fld(14, 9) * 10, fld(23, 9) * 10, fld(38, 3),
                   fld(49, 5), fld(32, 6))
            want = (NEW_LEVEL, NEW_ATK, NEW_DEF, GC.attribute_reverse[NEW_ATTRIBUTE],
                    GC.race_reverse[NEW_RACE], NEW_CARD_TYPE_ENCODED)
            check(got == want,
                  f"A card_prop[{idx}] = Lv{got[0]} {got[1]}/{got[2]} attr{got[3]} "
                  f"race{got[4]} ct{got[5]} (want Lv{want[0]} {want[1]}/{want[2]} "
                  f"attr{want[3]} race{want[4]} ct{want[5]})")
            check((v & 0x3FFF) == DONOR_CID,
                  f"A card_prop[{idx}] still holds cid 0x{DONOR_CID:04X} (keep-cid)")
            check(fld(32, 6) in IS_TUNER_TYPES,
                  f"A card_type {fld(32, 6)} is one of the is_tuner arms {IS_TUNER_TYPES} "
                  f"-> the engine reads this card as a TUNER")

            g = int.from_bytes(orig[genre_off:genre_off + 8], "little")
            check(g in pcg.accepted(DONOR_CID, NEW_GENRE),
                  f"B card_genre[{idx}] = 0x{g:016X} (want 0x{NEW_GENRE:016X}: "
                  f"bit {GENRE_BIT_TUNER} TUNER only)")

            # -- C: the text, against card_text and NEVER a local constant ----------

            # -- STAGE 2: E the ov5 handler, F the criteria row, G the cls2 record ---
            ov3 = bytes(view.buf)
            ov = bytearray(ov3)

            base = ov5_cave.CAVE_SR_DECKFIND
            want = build_deckfind_stub(bytes(ov3), base)
            got = ov5_cave.read_cave(rom, base, STUB_LEN)
            check(got == want,
                  f"E ov5 criteria handler @0x{base:08X} matches the relocated "
                  f"Gusto Egul handler ({STUB_LEN} B)")
            check(struct.unpack_from("<H", got, MODE_OFF)[0] == MODE_SCRAPYARD,
                  f"E the mode halfword is 0x{MODE_SCRAPYARD:04X} (`movs r0,#2`) -- no "
                  f"Special-Summon legality check on candidates")
            check(struct.unpack_from("<I", got, LITERAL_OFF)[0] == NONTUNER_CALLBACK,
                  f"E the pool literal is still the non-Tuner callback "
                  f"0x{NONTUNER_CALLBACK:08X} (Thumb bit set)")
            # the BL must land exactly on the shared builder
            hi, lo = struct.unpack_from("<HH", got, BL_OFF)
            off22 = (((hi & 0x7FF) << 12) | ((lo & 0x7FF) << 1))
            if off22 & (1 << 22):
                off22 -= (1 << 23)
            check(base + BL_OFF + 4 + off22 == DECK_LIST_BUILDER,
                  f"E the BL @+0x{BL_OFF:02X} targets the shared Deck builder "
                  f"0x{DECK_LIST_BUILDER:08X}")
            try:
                effect_verify.assert_thumb1_only(got[:GUSTO_EGUL_HANDLER_LEN], base)
                check(True, "E the ov5 handler is Thumb-1 only")
            except Exception as exc:                                   # noqa: BLE001
                check(False, f"E assert_thumb1_only: {exc}")

            crit = [struct.unpack_from(CRIT_FMT, ov, ov3_off(CRIT_BASE + i * CRIT_STRIDE))
                    for i in range(CRIT_COUNT)]
            mine = [r for r in crit if r[0] == DONOR_CID]
            check(mine == [(DONOR_CID, SETCODE_AUX_SCRAP, base | 1, CRIT_WORD)],
                  f"F exactly one criteria row for 0x{DONOR_CID:04X}: "
                  f"{[tuple(hex(x) for x in r) for r in mine]}")
            check(not any(r[0] == CRIT_PHANTOM for r in crit),
                  f"F the dropped criteria phantom 0x{CRIT_PHANTOM:04X} is gone")
            ckeys = [r[0] for r in crit]
            check(all(ckeys[i] <= ckeys[i + 1] for i in range(len(ckeys) - 1)),
                  f"F the criteria table is still sorted ({CRIT_COUNT} rows, unchanged)")

            cls2 = [struct.unpack_from(CLS2_FMT, ov, ov3_off(CLS2_BASE + i * CLS2_STRIDE))
                    for i in range(CLS2_COUNT)]
            mine2 = [r for r in cls2 if (r[0] & 0xFFFF) == DONOR_CID]
            check(len(mine2) == 1,
                  f"G exactly ONE cls2 record for 0x{DONOR_CID:04X} (found {len(mine2)}) "
                  f"-- find_event_handler returns the LEFTMOST, so a second would shadow")
            if mine2:
                check(tuple(mine2[0]) == CLS2_RECORD,
                      f"G cls2 record = {tuple(hex(x) for x in mine2[0])} "
                      f"(want {tuple(hex(x) for x in CLS2_RECORD)})")
            check(not any((r[0] & 0xFFFF) == CLS2_PHANTOM for r in cls2),
                  f"G the dropped cls2 phantom 0x{CLS2_PHANTOM:04X} is gone")
            check(mine2 and mine2[0][5] == 0,
                  f"G +14 == 0 (no target template; both Deck-zone precedents ship 0)")

            # -- L: THE LEAVE ARM -- without this nothing else in C2 ever runs -------
            masks = [struct.unpack_from(LEAVE_MASK_FMT, ov,
                                        ov3_off(LEAVE_MASK_BASE + i * LEAVE_MASK_STRIDE))
                     for i in range(LEAVE_MASK_COUNT)]
            mine_m = [m for m in masks if m[0] == DONOR_CID]
            check(mine_m == [(DONOR_CID, LEAVE_MASK)],
                  f"L leave-mask row for 0x{DONOR_CID:04X} = "
                  f"{[(hex(c), hex(m & 0xFFFF)) for c, m in mine_m]} "
                  f"(want mask 0x{LEAVE_MASK:04X} = destroyed | to-GY) -- THIS IS THE ARM")
            check(not any(c == LEAVE_MASK_PHANTOM for c, _ in masks),
                  f"L the dropped mask phantom 0x{LEAVE_MASK_PHANTOM:04X} is gone")
            mk = [c for c, _ in masks]
            check(all(mk[i] <= mk[i + 1] for i in range(len(mk) - 1)),
                  f"L the mask table is still sorted ({LEAVE_MASK_COUNT} rows, unchanged)")
            for base, count, label in ((LIST30_BASE, LIST30_COUNT, "list30"),
                                       (LIST106_BASE, LIST106_COUNT, "list106")):
                check(DONOR_CID not in u16_keys(ov, base, count, 2),
                      f"L 0x{DONOR_CID:04X} stays OUT of {label} (being in it would make "
                      f"the dispatcher SKIP the mask lookup)")

            # -- K: the "destroyed by a Scrap card" condition -----------------------
            ca = ov5_cave.CAVE_SR_C2COND
            want_c = build_c2_cond(ca)
            got_c = ov5_cave.read_cave(rom, ca, len(want_c))
            check(got_c == want_c, f"K C2 condition stub @0x{ca:08X} matches ({len(want_c)} B)")
            try:
                effect_verify.assert_thumb1_only(got_c, ca)
                check(True, "K C2 condition is Thumb-1 only")
            except Exception as exc:                                   # noqa: BLE001
                check(False, f"K assert_thumb1_only: {exc}")
            check(mine2 and mine2[0][3] == (ca | 1),
                  f"K cls2 +0C points at the ov5 Scrap-destroyer test 0x{ca | 1:08X}")
            # the stock arm this stub is lifted from must be unchanged
            def _blt(a):
                hi = struct.unpack_from("<H", ov, ov3_off(a))[0]
                lo = struct.unpack_from("<H", ov, ov3_off(a + 2))[0]
                o = ((hi & 0x7FF) << 12) | ((lo & 0x7FF) << 1)
                return a + 4 + (o - (1 << 23) if o & (1 << 22) else o)
            check(_blt(0x021C92EE) == DESTROYER_CID_OF and _blt(0x021C9302) == SCRAP_SETCODE_THUNK,
                  f"K the stock Scrap leave arm @0x{SCRAP_ARM_SITE:08X} still calls "
                  f"0x{DESTROYER_CID_OF:08X} then the Scrap thunk 0x{SCRAP_SETCODE_THUNK:08X}")
            shark2 = [r for r in cls2 if (r[0] & 0xFFFF) == SHARK_CID]
            check(len(shark2) == 1 and tuple(shark2[0][1:]) == SHARK_RECORD,
                  f"G Scrap Shark 0x{SHARK_CID:04X} (the Deck-zone precedent) is untouched "
                  f"and still ships +14 == 0")
            k2 = [r[0] & 0xFFFF for r in cls2]
            check(all(k2[i] <= k2[i + 1] for i in range(len(k2) - 1)),
                  f"G the cls2 table is still sorted ({CLS2_COUNT} rows, unchanged)")

            # the five template cards must be untouched -- this patch composes with them
            for cid in TRIGGER_TEMPLATE_CIDS:
                rows = [r for r in cls2 if (r[0] & 0xFFFF) == cid]
                check(len(rows) == 1 and tuple(rows[0][1:]) == TRIGGER_TEMPLATE,
                      f"G template 0x{cid:04X} still carries the stock shared trigger")

            # -- STAGE 3: H/I the OPT stubs, J the cls3 ignition record --------------
            for addr, builder, what in (
                    (ov5_cave.CAVE_SR_C1COND, build_c1_cond, "H C1a condition"),
                    (ov5_cave.CAVE_SR_C1COST, build_c1_cost, "I C1a cost")):
                want_b = builder(addr)
                got_b = ov5_cave.read_cave(rom, addr, len(want_b))
                check(got_b == want_b,
                      f"{what} stub @0x{addr:08X} matches ({len(want_b)} B)")
                try:
                    effect_verify.assert_thumb1_only(got_b, addr)
                    check(True, f"{what} is Thumb-1 only")
                except Exception as exc:                               # noqa: BLE001
                    check(False, f"{what} assert_thumb1_only: {exc}")

            cls3 = [struct.unpack_from(CLS3_FMT, ov, ov3_off(CLS3_BASE + i * CLS3_STRIDE))
                    for i in range(CLS3_COUNT)]
            mine3 = [r for r in cls3 if (r[0] & 0xFFFF) == DONOR_CID]
            check(len(mine3) == 1,
                  f"J exactly ONE cls3 record for 0x{DONOR_CID:04X} (found {len(mine3)})")
            if mine3:
                check(tuple(mine3[0]) == cls3_record(),
                      f"J cls3 record = {tuple(hex(x) for x in mine3[0])} "
                      f"(want {tuple(hex(x) for x in cls3_record())})")
            check(not any((r[0] & 0xFFFF) == CLS3_PHANTOM for r in cls3),
                  f"J the dropped cls3 phantom 0x{CLS3_PHANTOM:04X} is gone")
            k3 = [r[0] & 0xFFFF for r in cls3]
            check(all(k3[i] <= k3[i + 1] for i in range(len(k3) - 1)),
                  f"J the cls3 table is still sorted ({CLS3_COUNT} rows, unchanged)")

            # the ignition framework must still be the shipped, cid-blind one
            for cid in IGNITION_TEMPLATE_CIDS:
                rows = [r for r in cls3 if (r[0] & 0xFFFF) == cid]
                ok_t = (rows and rows[0][1] == DESTROY_TARGET
                        and (rows[0][3], rows[0][4], rows[0][5])
                        == (NATIVE_IGNITION_COND | 1, NATIVE_IGNITION_COST | 1, CLS3_TAIL))
                check(bool(ok_t),
                      f"J ignition template 0x{cid:04X} still ships "
                      f"+04=0x{DESTROY_TARGET:08X} and the generic once-per-turn triple")

            # the picker must still be the cid-blind thunk, not the per-cid dispatcher
            poff = (PICK_FACEUP_MONSTER_YOU_CONTROL & ~1) - RAM_BASE
            thunk = bytes(ov[poff:poff + 8])
            lit_at = ((PICK_FACEUP_MONSTER_YOU_CONTROL & ~1) + 2 + 4 + 8) & ~3
            check(thunk[:2] == b"\x00\xb5" or thunk[0:2] == struct.pack("<H", 0xB508),
                  f"J picker 0x{PICK_FACEUP_MONSTER_YOU_CONTROL:08X} still starts with a push")
            check(struct.unpack_from("<I", ov, lit_at - RAM_BASE)[0] == PICKER_FILTER,
                  f"J picker's r3 filter is still 0x{PICKER_FILTER:08X} "
                  f"(\"target 1 face-up monster you control\")")

            # -- STAGE 4: M/N the C1b stubs and the seven retargeted call sites -------
            rom_v = rom
            # which home: the FRESH counter hook is Raptor's alone, so it decides
            # sakitama (ships later) fronts six of these sites and chains into SR_*; look through its fronts.
            from otn_enhanced.cards import sakitama
            on_ov3 = sakitama.unfronted(ov, C1B_SITE3_COUNT) == _encode_bl(C1B_SITE3_COUNT, SR3["count"])
            print(f"  (C1b stubs in {'ov3 pool' if on_ov3 else 'ov5'})")

            def held(addr: int, n: int) -> bytes:
                return bytes(ov[addr - RAM_BASE:addr - RAM_BASE + n]) if on_ov3 else \
                    ov5_cave.read_cave(rom_v, addr, n)

            for addr, reserve, builder, what in c1b_stubs(on_ov3):
                blob = builder(addr)
                check(held(addr, len(blob)) == blob,
                      f"M stub @0x{addr:08X} ({len(blob)}/{reserve} B) -- {what}")
            for site, _before, after, what in c1b_hooks(on_ov3):
                check(sakitama.unfronted(ov, site) == after, f"N hook {what}")

            # The grant IS C1a's once-per-turn latch, so the two must stay the same
            # key/slot/kind -- if C1a's latch ever moves, C1b silently stops working.
            check((TURNLOG_KIND, TURNLOG_SLOT, TURNLOG_POST) == (GRANT_KIND, 0x0B, NODE_POST),
                  "M C1a's turn-log latch is still exactly the C1b grant "
                  f"(slot 0x{TURNLOG_SLOT:X}, key 0x{DONOR_CID:04X}, kind {GRANT_KIND})")
            check(GRANT_KIND != SPENT_KIND,
                  f"M granted (kind {GRANT_KIND}) and spent (kind {SPENT_KIND}) are distinct kinds "
                  f"on the one key -- both read with the KIND-EXACT 0x{NODE_QUERY_EXACT:08X}")

            # ninishi's own stubs must be byte-identical: C1b chains, never rewrites.
            for k, ns_addr in (NS3 if on_ov3 else NS5).items():
                ns_name = f"CAVE{'3' if on_ov3 else ''}_NS_{k.upper()}"
                head = held(ns_addr, 4)
                check(head not in (b"\x00\x00\x00\x00", b"\xff\xff\xff\xff"),
                      f"M {ns_name} @0x{ns_addr:08X} is populated -- ninishi was applied "
                      f"(C1b tail-jumps into it; an empty cave would FREEZE)")


        return Compiled(installs=(install,), posts=(apply_setcode, apply_card_genre), checks=(check_fn,))


scrap_raptor_effects = tuner_destroy_own_monster_ignition_destroyed_by_scrap_card_send_scrap_from_deck_extra_normal_summon_of_one_scrap_monster

SPEC = card(0x0FF6, scrap_raptor_effects())

PROPS = card_props("EARTH", "Dinosaur", level=4, atk=1400, defense=1000, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_scrap_raptor.nds")

# Names other modules read from this one (dsl.py's sakitama verb reads c1b_stubs / c1b_chain_targets): their closure, verbatim from the original.
from otn_enhanced.asm import effect_verify

from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R4

from otn_enhanced.effects import ov5_cave

from otn_enhanced.effects import cave3

DONOR_CID = 0x0FF6          # "Uraby" -- the donor; KEEPS this cid

SCRAP_SETCODE_THUNK = 0x02023EE4      # has_set_code(cid, "Scrap"); EVEN -- we BL it

TURNLOG_SLOT = 0x0B

NS_ARM = ov5_cave.CAVE_NS_ARM       # ninishi's five stubs: CHAINED INTO,

NS_SPENT = ov5_cave.CAVE_NS_SPENT   # never modified.  All in-game confirmed

NS_PRED = ov5_cave.CAVE_NS_PRED     #.

NS_FIELD = ov5_cave.CAVE_NS_FIELD

NS_MATCH = ov5_cave.CAVE_NS_MATCH

NS3 = dict(arm=cave3.CAVE3_NS_ARM, spent=cave3.CAVE3_NS_SPENT, pred=cave3.CAVE3_NS_PRED,
           field=cave3.CAVE3_NS_FIELD, match=cave3.CAVE3_NS_MATCH)

NS5 = dict(arm=NS_ARM, spent=NS_SPENT, pred=NS_PRED, field=NS_FIELD, match=NS_MATCH)

SR3 = dict(arm=cave3.CAVE3_SR_NSARM, spent=cave3.CAVE3_SR_NSSPENT, pred=cave3.CAVE3_SR_NSPRED,
           field=cave3.CAVE3_SR_NSFIELD, count=cave3.CAVE3_SR_NSCOUNT,
           match=cave3.CAVE3_SR_NSMATCH, post=cave3.CAVE3_SR_NSPOST)

SR5 = dict(arm=ov5_cave.CAVE_SR_NSARM, spent=ov5_cave.CAVE_SR_NSSPENT, pred=ov5_cave.CAVE_SR_NSPRED,
           field=ov5_cave.CAVE_SR_NSFIELD, count=ov5_cave.CAVE_SR_NSCOUNT,
           match=ov5_cave.CAVE_SR_NSMATCH, post=ov5_cave.CAVE_SR_NSPOST)

ARM_POOL = 0x02261F84           # the arm's granter-cid literal; the ONLY place the

NATIVE_COUNTER = 0x021B9514     # (side) -> how many Normal Summons remain

NODE_QUERY_EXACT = 0x021A14E8   # (side, slot, key, KIND) -> node ptr or 0

NODE_POST = 0x021D2584          # (side, key, kind byte, param)

GRANT_KIND = 1                  # == TURNLOG_KIND: C1a's latch IS the grant

SPENT_KIND = 2

HOST_EPILOGUE = "{R3, R4, R5, R6, R7, PC}"   # sites 1 and 2 both push {r3-r7,lr}

SITE3_DESC_CID = 0x0E           # descriptor +0x0E = the chosen hand card's cid

NSARM_RESERVE = 0x40

NSSPENT_RESERVE = 0x30

NSPRED_RESERVE = 0x30

NSFIELD_RESERVE = 0x30

NSCOUNT_RESERVE = 0x30

NSMATCH_RESERVE = 0x20

NSPOST_RESERVE = 0x20

def _grant_query(b: EffectBuilder, side_reg: str, kind: int) -> None:
    """Emit 0x021A14E8(side, 0x0B, DONOR_CID, *kind*) -> r0."""
    b.insn("ADD", f"R0, {side_reg}, #0x0")
    b.insn("MOV", f"R1, #0x{TURNLOG_SLOT:X}")
    b.ldr_const(2, DONOR_CID)
    b.insn("MOV", f"R3, #0x{kind:X}")
    b.bl(NODE_QUERY_EXACT)

def build_nsarm(addr: int, ns: int = NS_ARM) -> bytes:
    """SITE 1 @0x021B9634 -- "which granter permits summoning this hand card?"

    Entry (from the `bl` ninishi put there): r5 = side, r4 = the candidate
    hand-card cid, or 0 meaning "any card" (the availability query).  Nothing is
    pushed: r4..r7 survive the calls and LR is dead, because the exit is the HOST
    function's epilogue.  That is also why the fall-through is a bare `bl` into
    ninishi's stub -- a tail-jump whose clobbered LR is already dead.

        cmp  r4,#0
        beq  grant              ; "any card" -> skip the archetype test
        add  r0,r4,#0
        bl   0x02023EE4         ; has_set_code(cid, "Scrap")
        cmp  r0,#0
        beq  chain
      grant:
        <query kind 1>          ; has C1a run this turn?  (== the grant exists)
        cmp  r0,#0
        beq  chain
        <query kind 2>          ; ... and is the extra summon still unspent?
        cmp  r0,#0
        bne  chain
        ldr  r0,=0x0FF6         ; yes -> Scrap Raptor is the granter
        pop  {r3,r4,r5,r6,r7,pc}
      chain:
        bl   CAVE_NS_ARM        ; Dverg / Ninishi, verbatim and untouched
    """
    b = EffectBuilder()
    b.insn("CMP", "R4, #0x0")
    b.insn("BEQ", "grant")
    b.insn("ADD", "R0, R4, #0x0")
    b.bl(SCRAP_SETCODE_THUNK)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "chain")
    b.label("grant")
    _grant_query(b, "R5", GRANT_KIND)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "chain")
    _grant_query(b, "R5", SPENT_KIND)
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "chain")
    b.ldr_const(0, DONOR_CID)
    b.insn("POP", HOST_EPILOGUE)
    b.label("chain")
    b.bl(ns)

    blob = b.assemble(addr)
    assert len(blob) <= NSARM_RESERVE, f"nsarm is {len(blob)}B (reserve 0x{NSARM_RESERVE:X})"
    effect_verify.assert_thumb1_only(blob, addr)
    return blob

def build_nsspent(addr: int, ns: int = NS_SPENT) -> bytes:
    """SITE 2 @0x021B9F9C -- "is the extra Normal Summon already spent?"

    Entry: r0 = the previous arm's rider-query result, r5 = side, r4 = 1 (the
    host's "spent" answer, which its tail clears to 0 when nothing matched).

        cmp  r0,#0
        bne  keep               ; an earlier granter already answered "spent"
        <query kind 2>          ; is RAPTOR's extra summon spent?
        cmp  r0,#0
        beq  chain
      keep:
        add  r0,r4,#0           ; the host's own `adds r0,r4,#0 ; pop`
        pop  {r3,r4,r5,r6,r7,pc}
      chain:
        movs r0,#0              ; CAVE_NS_SPENT expects r0 = the Dverg result
        bl   CAVE_NS_SPENT
    """
    b = EffectBuilder()
    b.insn("CMP", "R0, #0x0")
    b.insn("BNE", "keep")
    _grant_query(b, "R5", SPENT_KIND)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "chain")
    b.label("keep")
    b.insn("ADD", "R0, R4, #0x0")
    b.insn("POP", HOST_EPILOGUE)
    b.label("chain")
    b.insn("MOV", "R0, #0x0")
    b.bl(ns)

    blob = b.assemble(addr)
    assert len(blob) <= NSSPENT_RESERVE, f"nsspent is {len(blob)}B (reserve 0x{NSSPENT_RESERVE:X})"
    effect_verify.assert_thumb1_only(blob, addr)
    return blob

def build_nspred(addr: int, ns: int = NS_PRED) -> bytes:
    """SITE 3 @0x02261E3E -- the arm's archetype predicate, and WHICH granter.

    Entry (the retargeted predicate call): r0 = the chosen hand card's cid,
    r4 = the summon descriptor.  Returns 0/1, and on a hit writes the granter cid
    into the arm's literal-pool word so the arm body runs for Raptor.

        push {lr}
        bl   0x02023EE4         ; has_set_code(cid, "Scrap")
        cmp  r0,#0
        beq  chain
        ldr  r1,=0x0FF6
        ldr  r2,=0x02261F84
        str  r1,[r2,#0x0]
        movs r0,#1
        pop  {pc}
      chain:
        ldrh r0,[r4,#0xE]       ; re-read the cid (the thunk clobbered r0)
        bl   CAVE_NS_PRED       ; "Nordic OR Karakuri", which writes its own cid
        pop  {pc}

    NOTE: this deliberately does NOT test the grant.  A "Scrap" hand card with no
    grant still takes Raptor's arm, and build_nsfield's -1 then bails it at the
    arm's own `blt` -- exactly how Dverg's arm bails when Dverg is not on the field.
    """
    b = EffectBuilder()
    b.insn("PUSH", "{LR}")
    b.bl(SCRAP_SETCODE_THUNK)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "chain")
    b.ldr_const(1, DONOR_CID)
    b.ldr_const(2, ARM_POOL)
    b.insn("STR", "R1, [R2, #0x0]")
    b.insn("MOV", "R0, #0x1")
    b.insn("POP", "{PC}")
    b.label("chain")
    b.insn("LDRH", f"R0, [R4, #0x{SITE3_DESC_CID:X}]")
    b.bl(ns)
    b.insn("POP", "{PC}")

    blob = b.assemble(addr)
    assert len(blob) <= NSPRED_RESERVE, f"nspred is {len(blob)}B (reserve 0x{NSPRED_RESERVE:X})"
    effect_verify.assert_thumb1_only(blob, addr)
    return blob

def build_nsfield(addr: int, ns: int = NS_FIELD) -> bytes:
    """SITE 3 @0x02261E68 -- "where is the granter?", answered from the GRANT NODE.

    *** THIS IS THE CLAUSE THAT MAKES THE GRANT OUTLIVE THE GRANTER. ***  For
    Raptor there is no field lookup at all: the answer is the kind-1 node C1a
    posted, so the extra summon survives Raptor being destroyed -- including by
    C1a targeting itself.

    Entry: r0 = side, r1 = the granter cid (read from the arm's pool word).
    The return value is consumed ONLY by the arm's following `cmp r0,#0 ; blt`,
    because r0 is immediately reloaded at 0x02261E70 (`ldrh r0,[r4]`) -- so 0 is
    a safe stand-in for a real slot index and no slot is ever dereferenced.

        push {lr}
        ldr  r2,=0x0FF6
        cmp  r1,r2
        bne  chain
        movs r1,#0xB
        movs r3,#1              ; r0 = side and r2 = the key are already right
        bl   0x021A14E8
        cmp  r0,#0
        beq  absent
        movs r0,#0              ; present -> any non-negative value
        pop  {pc}
      absent:
        ldr  r0,=0xFFFFFFFF     ; -1, so the arm's `blt` bails
        pop  {pc}
      chain:
        bl   CAVE_NS_FIELD      ; native for every other granter
        pop  {pc}
    """
    b = EffectBuilder()
    b.insn("PUSH", "{LR}")
    b.ldr_const(2, DONOR_CID)
    b.insn("CMP", "R1, R2")
    b.insn("BNE", "chain")
    b.insn("MOV", f"R1, #0x{TURNLOG_SLOT:X}")
    b.insn("MOV", f"R3, #0x{GRANT_KIND:X}")
    b.bl(NODE_QUERY_EXACT)
    b.insn("CMP", "R0, #0x0")
    b.insn("BEQ", "absent")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{PC}")
    b.label("absent")
    b.ldr_const(0, 0xFFFFFFFF)
    b.insn("POP", "{PC}")
    b.label("chain")
    b.bl(ns)
    b.insn("POP", "{PC}")

    blob = b.assemble(addr)
    assert len(blob) <= NSFIELD_RESERVE, f"nsfield is {len(blob)}B (reserve 0x{NSFIELD_RESERVE:X})"
    effect_verify.assert_thumb1_only(blob, addr)
    return blob

def build_nscount(addr: int) -> bytes:
    """SITE 3 @0x02261E92 -- force the counter to 0 so the ANNOUNCE is skipped.

    *** FRESH HOOK.  Stock before-image `bl 0x021B9514`. ***

    The arm's granter-announce at 0x02261E9A..0x02261ED0 is reached only when the
    Normal-Summon counter is non-zero (`cmp r0,#0 ; beq 0x02261ED6`), and it
    DEREFERENCES the granter's field slot -- 0x02261EA0 `bl on_field`, then
    `muls r3,#0x14 ; ldr r5,[r6,r3]` off `player + 0x34`.  For a granter that has
    left the field that index is negative and the announce would decode a garbage
    card ref.  Returning 0 here takes the `beq` instead, which writes the
    announce-ACK flag directly (`str r0,[r5,#0x34]`, r5 being the fixed global
    0x0229DD94 loaded in the enclosing function's prologue at 0x022619E0) and
    falls into phase 0x64 having done everything the announce path does except
    post the 0xE2 attribution event.

    COST: no "<granter>'s effect!" announce for Raptor's grant.  USER-APPROVED
    2026-09-22.  Note the stock path already skips this same announce whenever
    the base Normal Summon is spent, which is C1b's main scenario.

        push {lr}
        ldr  r1,=0x02261F84
        ldr  r1,[r1,#0x0]       ; which granter is this arm running for?
        ldr  r2,=0x0FF6
        cmp  r1,r2
        bne  chain
        movs r0,#0              ; -> the announce-skip at 0x02261ED6
        pop  {pc}
      chain:
        bl   0x021B9514         ; the native counter, for every other granter
        pop  {pc}
    """
    b = EffectBuilder()
    b.insn("PUSH", "{LR}")
    b.ldr_const(1, ARM_POOL)
    b.insn("LDR", "R1, [R1, #0x0]")
    b.ldr_const(2, DONOR_CID)
    b.insn("CMP", "R1, R2")
    b.insn("BNE", "chain")
    b.insn("MOV", "R0, #0x0")
    b.insn("POP", "{PC}")
    b.label("chain")
    b.bl(NATIVE_COUNTER)
    b.insn("POP", "{PC}")

    blob = b.assemble(addr)
    assert len(blob) <= NSCOUNT_RESERVE, f"nscount is {len(blob)}B (reserve 0x{NSCOUNT_RESERVE:X})"
    effect_verify.assert_thumb1_only(blob, addr)
    return blob

def build_nsmatch(addr: int, ns: int = NS_MATCH) -> bytes:
    """SITE 4 @0x0226515C -- "is this descriptor's granter ours?", in the flags.

    Entry: r0 = descriptor[+0x12], the granter cid the state machine stamped.
    The host's `bne` reads Z and its next call reads r1, so this must leave the
    MATCHED cid in r1, not a boolean.

    ⚠️ THE TAIL MUST NOT BE A `bl`.  CAVE_NS_MATCH ends in `bx lr` and returns
    through OUR lr to the host; a `bl` would overwrite it and return here instead.
    `ldr` + `bx` also leave the flags alone, which `bl` would be fine with but
    which matters for the shape.  The literal carries bit 0 SET -- a `bx` to an
    even literal switches to ARM state and freezes (thumb-blx-even-literal-footgun).

        ldr  r1,=0x0FF6
        cmp  r0,r1
        beq  out                ; Z set, r1 = Raptor
        ldr  r1,=CAVE_NS_MATCH|1
        bx   r1                 ; tail-jump: ninishi decides Z and r1
      out:
        bx   lr                 ; BX preserves the flags
    """
    b = EffectBuilder()
    b.ldr_const(1, DONOR_CID)
    b.insn("CMP", "R0, R1")
    b.insn("BEQ", "out")
    b.ldr_const(1, ns | 1)
    b.insn("BX", "R1")
    b.label("out")
    b.insn("BX", "LR")

    blob = b.assemble(addr)
    assert len(blob) <= NSMATCH_RESERVE, f"nsmatch is {len(blob)}B (reserve 0x{NSMATCH_RESERVE:X})"
    effect_verify.assert_thumb1_only(blob, addr)
    return blob

def build_nspost(addr: int) -> bytes:
    """SITE 4 @0x0226517C -- post the spent mark with kind 2 for Raptor.

    *** FRESH HOOK.  Stock before-image `bl 0x021D2584`. ***

    The host hardcodes the kind with `movs r2,#1` at 0x02265176, a lone 2-byte
    instruction that cannot branch.  Kind 1 on key 0x0FF6 is C1a's once-per-turn
    latch, which C1a already posted -- so leaving it alone would mark NOTHING
    spent and the extra Normal Summon would be repeatable, with verify() passing.

    Entry: r0 = side, r1 = the key (descriptor[+0x12], which ninishi's
    in-place edit at 0x02265174 already makes the ACTUAL granter cid), r2 = 1,
    r3 = 0.

        push {lr}
        ldr  r3,=0x0FF6
        cmp  r1,r3
        bne  chain
        movs r2,#2              ; Raptor's spent mark is KIND 2
      chain:
        movs r3,#0              ; restore the post's 4th argument
        bl   0x021D2584
        pop  {pc}
    """
    b = EffectBuilder()
    b.insn("PUSH", "{LR}")
    b.ldr_const(3, DONOR_CID)
    b.insn("CMP", "R1, R3")
    b.insn("BNE", "chain")
    b.insn("MOV", f"R2, #0x{SPENT_KIND:X}")
    b.label("chain")
    b.insn("MOV", "R3, #0x0")
    b.bl(NODE_POST)
    b.insn("POP", "{PC}")

    blob = b.assemble(addr)
    assert len(blob) <= NSPOST_RESERVE, f"nspost is {len(blob)}B (reserve 0x{NSPOST_RESERVE:X})"
    effect_verify.assert_thumb1_only(blob, addr)
    return blob

def c1b_stubs(ov3: bool = False) -> tuple:
    """(addr, reserve, builder(addr), what) for the seven C1b stubs, in the chosen home."""
    sr, ns = (SR3, NS3) if ov3 else (SR5, NS5)
    return (
        (sr["arm"], NSARM_RESERVE, lambda a: build_nsarm(a, ns["arm"]), "SITE 1 granter arm"),
        (sr["spent"], NSSPENT_RESERVE, lambda a: build_nsspent(a, ns["spent"]), "SITE 2 spent check"),
        (sr["pred"], NSPRED_RESERVE, lambda a: build_nspred(a, ns["pred"]), "SITE 3 predicate"),
        (sr["field"], NSFIELD_RESERVE, lambda a: build_nsfield(a, ns["field"]),
         "SITE 3 grant-node lookup"),
        (sr["count"], NSCOUNT_RESERVE, build_nscount, "SITE 3 counter -> announce skip"),
        (sr["match"], NSMATCH_RESERVE, lambda a: build_nsmatch(a, ns["match"]), "SITE 4 granter match"),
        (sr["post"], NSPOST_RESERVE, build_nspost, "SITE 4 spent post (kind 2)"),
    )

def c1b_chain_targets(ov3: bool = False) -> tuple:
    """(raptor stub, ninishi stub, what) for every tail-jump C1b makes.

    C1b CHAINS into ninishi rather than replacing it, so each of these
    pairs must stay intact: Raptor's stub handles cid 0x0FF6 and hands every
    other granter straight back to ninishi's original, unmodified code.
    """
    sr, ns = (SR3, NS3) if ov3 else (SR5, NS5)
    return tuple((sr[k], ns[k], what) for k, what in (
        ("arm", "site 1 granter arm"), ("spent", "site 2 spent check"),
        ("pred", "site 3 predicate"), ("field", "site 3 granter lookup"),
        ("match", "site 4 granter match")))

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
