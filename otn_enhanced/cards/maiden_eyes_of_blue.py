"""Maiden with Eyes of Blue (LIGHT / Spellcaster / Tuner Monster / Level 1 / 0 / 0) on Comrade Swordsman of Landstar 0x1ED7.

    When a card or effect is activated that targets this card (Quick Effect): You can Special Summon 1 "Blue-Eyes White Dragon" from your hand,
    Deck, or GY. When this card is targeted for an attack: You can negate the attack, and if you do, change the battle position of this card, then
    you can Special Summon 1 "Blue-Eyes White Dragon" from your hand, Deck, or GY. You can only use 1 "Maiden with Eyes of Blue" effect per turn,
    and only once that turn. (See card_text.CARD_TEXT[0x1ED7] for the full printed text.)
"""
from __future__ import annotations

import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, SRC
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.effects import cave3
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class quick_effect_targeted_by_card_or_attacked_negate_attack_change_position_special_summon_blue_eyes_white_dragon_once_per_turn:
    """Maiden with Eyes of Blue (Comrade Swordsman of Landstar 0x1ED7, LIGHT / Spellcaster / Tuner / Level 1 / 0 / 0): 'When a card or effect is
    activated that targets this card (Quick Effect): You can Special Summon 1 "Blue-Eyes White Dragon" from your hand, Deck, or GY. When this card is
    targeted for an attack: You can negate the attack, and if you do, change the battle position of this card, then you can Special Summon 1
    "Blue-Eyes White Dragon" from your hand, Deck, or GY. You can only use 1 "Maiden with Eyes of Blue" effect per turn, and only once that turn.'
    Clause 2 = a cls1 record (phantom 0x1DB6) + the shared attack-target gate; clause 1 = a cls3 record (phantom 0x1C80) with a once-per-turn
    stamping cost; the one shared criteria row (phantom 0x1BBE); the donor in the ARM9 Spell-Speed-2 list (phantom 0x1A86); five ov5 stubs. Original
    shipped-path code embedded verbatim (the ov5-gate variant is kept inside apply_effect; the diagnostic-build stubs are dropped)."""

    def compile(self, view, cid) -> Compiled:
        import struct
        from otn_enhanced.asm import effect_verify
        from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.effects import cave3
        from otn_enhanced.effects import atktgt_gate
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R4, R5, R6, R7
        from otn_enhanced.effects.common import ov3_off as _off

        SRC = "data/over_the_nexus/working/rom_ov3_compact.nds"   # stock + step 0 (ov3 pool)
        OUT = "data/over_the_nexus/working/rom_maiden.nds"

        DONOR_CID = 0x1ED7          # Comrade Swordsman of Landstar
        BEWD_CID = 0x0FA7           # Blue-Eyes White Dragon -- the only obtainable art

        # ---------------------------------------------------------------------------
        # PART A1 -- cls1 (dispatcher event-class table 1)
        # ---------------------------------------------------------------------------
        CLS1_BASE = 0x022860D4
        CLS1_COUNT = 0x535          # 1333 records, stride 24
        CLS1_STRIDE = 24
        # Phantom dropped to keep the count. 0x1DB6 has NO card_prop record (so it can
        # never be instantiated and its record can never be dispatched), owns exactly ONE
        # cls1 record, and is claimed by no other patch.
        CLS1_DROP_PHANTOM = 0x1DB6
        CLS1_PHANTOM_BEFORE = (0x1DB6, 0x022288C5, 0x00000000, 0x021F2BD9, 0x021E51E5, 0x00000000)

        # ---------------------------------------------------------------------------
        # PART A2 -- criteria / populate registry
        # ---------------------------------------------------------------------------
        CRIT_BASE = 0x022713C4
        CRIT_COUNT = 1388
        CRIT_STRIDE = 12
        CRIT_FMT = "<HHIHH"         # {cid, aux, handler, flags, extra}
        CRIT_DROP_PHANTOM = 0x1BBE  # no card_prop; owns exactly one row; unclaimed
        CRIT_PHANTOM_BEFORE = (0x1BBE, 0x0020, 0x0223CAF5, 0x0002, 0x0000)
        CRIT_NEW = (DONOR_CID, BEWD_CID, 0x0223E2C9, 0x0802, 0x0000)

        # ---------------------------------------------------------------------------
        # PART A3 -- the attack-target event GATE (added after in-game test 1 failed)
        # ---------------------------------------------------------------------------
        # The code-0x13 "targeted for an attack" post at 0x021C6798 is guarded by
        # `cmp r6,#0 ; beq` at 0x021C678A, and r6 comes from a PER-CID SWITCH at
        # 0x021C6620 that defaults to 0. Concretely executing that switch over the whole
        # cid space accepts exactly 26 cids -- the negate-attack family, the
        # position-change family and Decoy Dragon -- and the donor is not among them, so
        # no event was ever posted and the (correct, live) cls1 record was never reached.
        # See notes/maiden-with-eyes-of-blue-findings.md.
        #
        # The switch is an ORDERED compare tree, so it cannot be extended by data: every
        # single-word edit to its literal pool was tried and re-simulated, and each one
        # either admitted extra cids or removed a real card. The fix therefore retargets
        # the ONE `bl 0x021A37D8` that feeds the switch its cid.
        ATKTGT_BL_SITE = 0x021C6624         # the `bl 0x021A37D8` inside 0x021C6620
        ATKTGT_HELPER = 0x021A37D8          # cid_at(side, slot) -- the original callee
        ATKTGT_ACCEPTED = 0x1CB1            # a PHANTOM cid the native switch already accepts
        # Cids admitted to the attack-target event (zero-terminated in the cave). This list
        # is SHARED, not Maiden's private property -- any donor needing the code-0x13
        # "targeted for an attack" event goes here.
        #   0x0FFD  Dark Chimera -> Karakuri Komachi Ninishi (ninishi PART A5). Its
        #           grafted "when this face-up card is selected as an attack target, change
        #           its battle position" record is inert without this remap, like every
        #           donor's. Added as Dverg 0x245B; re-keyed to 0x0FFD on
        # when ninishi moved to a Normal-Monster donor and gave
        #           Dverg back (Dverg has no such printed clause, so it must NOT be listed).
        #   0x1ED7  Comrade Swordsman of Landstar -> Maiden with Eyes of Blue (this patch).
        #   0x0FC8  Saggi the Dark Clown -> Karakuri Muso mdl 818 "Haipa"
        #           (karakuri_haipa PART D).  Its clause 2, "when this face-up Attack
        #           Position card is selected as an attack target, change it to Defense
        #           Position", is the stock 0x0220C6B1 / 0x021F4D4D cls1 record, which is
        #           inert without this remap.  Added.
        ATKTGT_ADMIT = (0x0FFD, DONOR_CID, 0x0FC8)

        # ---------------------------------------------------------------------------
        # PART E -- CLAUSE 1: the cls3 record ("a card or effect is activated that
        #          targets this card")
        # ---------------------------------------------------------------------------
        # cls3 is the fourth dispatch table (descriptor[+5] == 3) -- the ON-FIELD responder
        # table, reached by a ZONE SWEEP rather than by a posted event, which is exactly why
        # clause 1 needs no gate surgery of the kind clause 2's code-0x13 post required.
        CLS3_BASE = 0x02279D74
        CLS3_COUNT = 0x308          # 776 records, stride 24
        CLS3_STRIDE = 24
        # Phantom dropped to keep the count. 0x1C80 has NO card_prop record (so no instance
        # can ever carry the cid and the record is unreachable), owns exactly ONE cls3 record,
        # and is claimed by no other patch -- its cid appears exactly once as an aligned u32
        # anywhere in overlay 3, namely in its own record.
        #
        # WHY THIS PHANTOM AND NOT ONE OF THE OTHER 76 CANDIDATES: it sits at cls3[334], which
        # is ABOVE shiens_dojo's index-anchored rows (it drops 223 and inserts at 233)
        # and BELOW sea_lancer's (DONOR_CLS3_ROW = 527). A count-neutral swap leaves every
        # index above max(drop, insert) untouched, so with 233 < 334 < 451 neither of those two
        # patches' by-index anchors moves. (Anchoring into a shared table by row index is a bug
        # -- see verify() below -- but it is a bug those two modules already ship, and this
        # patch is not going to be the one that detonates it.)
        CLS3_DROP_PHANTOM = 0x1C80
        CLS3_PHANTOM_BEFORE = (0x1C80, 0x02226175, 0x00000000, 0x021F01C1, 0x021E5061, 0x00000000)

        # ---------------------------------------------------------------------------
        # PART F -- CLAUSE 1 IS A *QUICK EFFECT*, AND THE ENGINE ENFORCES SPELL SPEED
        # ---------------------------------------------------------------------------
        # Measured, not guessed (rom_maiden_diag.ml2/.ml4/.ml5). The clause-1
        # condition WAS dispatched -- the diagnostic read the invoker's return address
        # straight off the stack and it is 0x021EDC91, i.e. the responder 0x021EDA14 arm C,
        # exactly the mapped path. But every call arrived with r1 == 0 and the chain empty,
        # because 0x021EDA14 bails BEFORE reaching slot3:
        #
        #   021EDA38  ldr r0,[sp] ; cmp r0,#0 ; beq 0x021EDA76   <- chain empty: skip the test
        #   021EDA3E  bl 0x021A87BC(my desc)   -> r4 = MY spell speed
        #   021EDA46  bl 0x021A87BC(the act)   -> r0 = the ACTIVATION's spell speed
        #   021EDA4C  cmp r4,r0 ; bge ; b 0x021EDC9E              <- my speed < theirs: RETURN
        #
        # So the two entries we saw were the chain-empty ignition sweeps (where the test is
        # skipped), and every real response window died at the spell-speed comparison.
        #
        # 0x021A87BC(desc) is a per-cid switch whose DEFAULT leaf 0x021A894C tail-calls
        # 0x0202345C(cid), and that function gives a MONSTER speed 2 only if its cid is in a
        # sorted 118-entry list at 0x0209C118 (ARM9), else 1. The list self-identifies: it
        # holds Kuriboh 0x0FE0, Injection Fairy Lily 0x13A7, Doomcaliber Knight 0x1771,
        # D.D. Crow 0x1B44, Herald of Purple/Green Light 0x1A24/0x1A25, Winged Kuriboh LV10
        # 0x1906 -- and BLUE-EYES SHINING DRAGON 0x17C2, the very card whose cls3 condition
        # this patch transcribes. That is why the native card's clause works and ours did not.
        #
        # THE FIX IS DATA: a count-neutral insert of the donor into that list. It is an ARM9
        # table, so unlike the ov5 stubs it is resident in EVERY duel mode, puzzles included.
        QUICKEFFECT_LIST = 0x0209C118       # sorted u16 cid list, binary-searched by 0x02022E14
        QUICKEFFECT_COUNT = 0x76            # 118 -- a HARD-CODED immediate (`movs r2,#0x76`
                                            # at 0x02023490), so the insert must be count-neutral
        QUICKEFFECT_DROP = 0x1A86           # phantom: no card_prop record, unclaimed, and the
                                            # highest phantom below the donor so the fewest
                                            # entries move

        # ---------------------------------------------------------------------------
        # PART B -- ov5 cave stub sizes
        # ---------------------------------------------------------------------------
        COND_LEN = 0x40
        RES_LEN = 0x80
        GATE_LEN = 0x40
        LIST_LEN = 0x10
        C1_COND_LEN = 0x60
        C1_RES_LEN = 0x40

        # ---------------------------------------------------------------------------
        # PART C / D -- visible stats and text
        # ---------------------------------------------------------------------------
        NEW_ATTRIBUTE = "LIGHT"                                     # donor is EARTH
        NEW_RACE = "Spellcaster"                                    # donor is Warrior
        NEW_LEVEL = 1                                               # donor is Level 3
        NEW_ATK = 0                                                 # donor is 500
        NEW_DEF = 0                                                 # donor is 1200
        NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Tuner Monster"]     # 33 -- donor ALREADY is

        NEW_NAME = b"Maiden with Eyes of Blue"
        # The donor's SMALLEST name slot across e/f/g/i/s/j/k/r is exactly 24 bytes
        # (Korean), so the real name lands in every language with nothing to spare.
        NAME_SLOT_MIN = 24
        assert len(NEW_NAME) <= NAME_SLOT_MIN, (
            f"name is {len(NEW_NAME)} B > the {NAME_SLOT_MIN} B floor -- growing the name "
            f"blob is forbidden (fixed-size engine buffer), so it would ship as the donor's")

        # The description is written STRICTLY IN PLACE and any language whose slot is
        # smaller is SKIPPED (the original donor text is kept -- a printed note, not an
        # error, which is how Lightpulsar shipped for a month with its donor's flavour
        # text). MEASURED for 0x1ED7: e 51, f 79, g 69, i 66, s 65, j 138, k 124, r 276.
        # 51 (English) is therefore the budget that covers EVERY language.
        DESC_SLOT_MIN = 51
        # Covers BOTH triggers. The previous string ("1/turn, if attacked: negate, flip, SS
        # Blue-Eyes.") was written when only clause 2 existed and never mentioned clause 1 at
        # all. 51 bytes is the donor's own English string and text is written STRICTLY IN
        # PLACE, so that is the whole budget -- "negate, flip" is what had to go.
        #
        # NOTE FOR A FUTURE SESSION: 51 B is NOT an engine limit. The English desc blob already
        # carries a 657-byte description (Manga Ryu-Ran), and other languages exceed 1000. The
        # proper fix is to APPEND a longer string to card_desc_<L>.bin and repoint this card's
        # desc_off in card_indx_<L>.bin -- both are u32 offsets, and pac.build_modified_pac
        # already repacks a v1 archive when an inner file changes size. It is untested here
        # (bin2.pac has only ever been edited at +0 B) and boggart_knight records that
        # growing the NAME blob correlated with in-game trouble, so it wants its own task and
        # its own test. Every card in this repo has been shipping truncated text.
        NEW_DESC = b"1/turn: if targeted or attacked, SS Blue-Eyes."
        assert len(NEW_DESC) <= DESC_SLOT_MIN, (
            f"description is {len(NEW_DESC)} B > the {DESC_SLOT_MIN} B slot -- it would be "
            f"SKIPPED and the card would keep the donor's flavour text")
        from otn_enhanced.data.card_stats import TEXT_LANGS

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


        def _cls3_records(ov: bytearray) -> list[tuple[int, ...]]:
            """Read cls3 as (cid, slot1..slot5) tuples; the pad halfword must be zero."""
            out = []
            for i in range(CLS3_COUNT):
                o = _off(CLS3_BASE + i * CLS3_STRIDE)
                cid, pad = struct.unpack_from("<HH", ov, o)
                assert pad == 0, f"cls3[{i}] has nonzero pad 0x{pad:04X}"
                out.append((cid,) + struct.unpack_from("<5I", ov, o + 4))
            return out


        def _write_cls3(ov: bytearray, recs: list[tuple[int, ...]]) -> None:
            for i, r in enumerate(recs):
                struct.pack_into("<HH5I", ov, _off(CLS3_BASE + i * CLS3_STRIDE), r[0], 0, *r[1:])


        def _crit_rows(ov: bytearray) -> list[tuple[int, ...]]:
            return [struct.unpack_from(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE))
                    for i in range(CRIT_COUNT)]


        def _write_crit(ov: bytearray, rows: list[tuple[int, ...]]) -> None:
            for i, r in enumerate(rows):
                struct.pack_into(CRIT_FMT, ov, _off(CRIT_BASE + i * CRIT_STRIDE), *r)


        def _bl(src: int, dst: int) -> bytes:
            """ARMv4T two-halfword BL (Thumb-1 long branch-with-link)."""
            off = dst - (src + 4)
            assert -(1 << 22) <= off < (1 << 22), f"BL 0x{src:08X}->0x{dst:08X} out of range: {off:#x}"
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
            generic table editors miss -- that no cid which owned SEVERAL adjacent rows
            ends up split by the edit. That matters for cls1 specifically: find_event_handler
            reaches a cid's SECOND record via `leftmost + 1`
            (dispatch.find_event_handler_second_record), so wedging a foreign record between
            a pair would silently make the second one unreachable.
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

            print(f"A  {label}: dropped phantom 0x{drop[0]:04X} (row {hits[0]}), inserted "
                  f"0x{insert[0]:04X} at row {pos} -- count {len(out)}, sorted, "
                  f"{len(after_groups)} multi-row cids all still contiguous")
            return out

        def _cond_stub(base: int) -> bytes:
            """slot3: the clause-2 ACTIVATION CONDITION -> 2 (activate) or 0 (cannot).

            Called as slot3(desc, event) by 0x0224AD94 (`ldr r2,[r4,#0xC] ; ldr r1,[sp] ;
            adds r0,r5,#0 ; blx r2` at 0x0224AE06), which treats any code > 0 as
            "activatable" and only consults slot2 when the code is exactly 1 -- so
            returning 2 means "activatable unconditionally, no board target needed".

            Gate 1 is Krebons' event-code test, transcribed from 0x0221F9E4:
            `(desc[+4] + 0xED) & 0xFF <= 1` accepts codes {0x13, 0x14} and nothing else.
            0x13 is "targeted for an attack"; 0x14 is its unproven sibling, and the KB is
            explicit that BOTH must be accepted rather than pinning one (pinning a
            discriminator measured on another card's path is what cost Lightpulsar clause
            3 an in-game test). Strictly this record can only ever receive the attack-
            target event -- it is the donor's only cls1 record -- but the test costs six
            halfwords and makes the record inert for anything else.

            Gate 2 is CLAUSE 3, the once-per-turn. Pot of Duality's exact query,
            0x021A14E8(side, 0x0B, cid, 1) -> nonzero iff this cid already logged a
            kind-1 (card/effect activation) node this turn. The key is the CID, so when
            clause 1 is built it shares this restriction for free.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x4]")
            b.insn("ADD", "R0, #0xED")
            b.insn("LSL", "R0, R0, #0x18")
            b.insn("LSR", "R0, R0, #0x18")
            b.insn("CMP", "R0, #0x1")
            b.insn("BGT", "reject")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", "R1, #0xB")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call("turnlog_query", R0, R1, R2, 1, via=R4)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "reject")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, PC}")
            b.label("reject")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, PC}")
            return b.assemble(base, pad="nop")

        def _res_stub(base: int) -> bytes:
            """slot1: the clause-2 RESOLVER -- negate, then flip, then chain the summon.

            The resolver is re-entered once per resolution phase, with the phase word at
            [0x0229AAFC + 0x70] and the return value naming the NEXT phase. The entry
            phase is 0x80, so the two verbs that are Maiden's own run there, and every
            phase (0x80 included) then tail-calls the shared "Special Summon 1 card
            matching my criteria row" machine 0x02206F41, whose own arms cover 0x80
            (count + prompt), 0x7F (open the picker), 0x7E (summon) and the teardown.
            0x02206F41's prologue switch has no arm for this donor, and a concrete trace
            shows ten of its eleven native users take that same DEFAULT arm -- the default
            is the beaten path, not an exception.

            *** THE NEGATE'S RETURN VALUE IS THE CARD'S "and if you do". ***
            0x0221F944 is self-driven and completely cid-generic: it takes side and slot
            from the battle context 0x02298AD8 (not from the descriptor, not from a pick
            array), runs five gates, enqueues command opcode 0x1F via 0x021C3BC8, and
            returns 1 only if it actually negated. So `cmp r0,#0 / bne` IS the printed
            "and if you do" -- no state, no latch.

            THE POSITION CHANGE IS A TOGGLE. 0x021C5324(desc, side, zone, 0, [sp]=1) has
            no target-position argument. The 16 native cards on 0x0220C6B1 hardcode
            "change to Defense" and guard it with a comparison against the live position;
            Maiden's text says "change the battle position", so the guard is dropped and
            the primitive called outright. 0x021D2C1C is the still-on-the-field gate and
            0x021D2D18 re-syncs desc[+2]/desc[+3] from the locator desc[+0xC] -- both
            taken verbatim from 0x0220C6B0's prologue, because the negate that just ran
            can have moved things.

            STACK NOTE: `push {r3, ...}` is not saving r3, it RESERVES the outgoing 5th-
            argument word at [sp] for 0x021C5324 -- Thumb PUSH stores the lowest-numbered
            register at the lowest address, and 0x021C5324 reads that word as [sp,#0x20]
            after its own 8-register push. 0x0220C6B0 uses the identical trick.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R3, R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.ldr_const(6, 0x0229AAFC)
            b.insn("LDR", "R6, [R6, #0x70]")
            b.insn("CMP", "R6, #0x80")
            b.insn("BNE", "delegate")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, 1, via=R6)
            b.call_addr(0x0221F944, R4, R5, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "negated")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R3, R4, R5, R6, PC}")
            b.label("negated")
            b.call_addr(0x021D2C1C, R4, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "delegate")
            b.call_addr(0x021D2D18, R4, via=R6)
            b.insn("ADD", "R0, R4, #0x0")
            b.insn("LDRB", "R1, [R4, #0x2]")
            b.insn("LDRB", "R2, [R4, #0x3]")
            b.insn("MOV", "R3, #0x0")
            b.insn("MOV", "R6, #0x1")
            b.insn("STR", "R6, [SP, #0x0]")
            b.call_addr(0x021C5324, via=R6)
            b.label("delegate")
            b.call_addr(0x02206F40, R4, R5, via=R6)
            b.insn("POP", "{R3, R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")

        def _c1_cond_stub(base: int) -> bytes:
            """CLAUSE 1 slot3: "a card or effect is activated that TARGETS this card".

            Called as slot3(r0 = MY descriptor, r1 = THE ACTIVATION'S descriptor). That
            second argument is the whole mechanism, and pinning it took a session: 0x0224AD94
            parks its own r1 at [sp] (`push {r3,...}` + `str r1,[sp]` @0x0224AD98) and hands
            it to slot3 as r1 @0x0224AE06. The descriptor itself comes from the CHAIN ARRAY --
            0x0229A7FC, stride 0x24, depth [0x0229A9FC + 0x44] -- via

                0x0224B8B0(side, container, zone)            container 0..0xA => field arm
                  -> 0x021EC654(viewpoint, side, zone, act)  builds MY desc FROM THE ZONE
                    -> 0x021EC740(mine, act)                 zone <= 0xA => desc[+5] = 3 (cls3)
                      -> 0x021EDA14(mine, act, 0)            selector != 0 => jump to 0x021EDC70
                        -> 0x0224AD94(mine, act)             -> find_event_handler -> here

            So clause 1's trigger is a ZONE SWEEP OF THE FIELD, not a posted event. There is no
            cid-gated post to defeat, which is the whole reason this clause is cheap where
            clause 2 needed the 26-cid gate remap. (0x021EDA08 is only a `movs r2,#0 ;
            bx 0x021EDA15` THUNK -- which is why "both callers of COMMIT pass r1 = 0" was a
            true statement that pointed at the wrong branch for two sessions.)

            Every gate between the sweep and this stub was audited for cid dependence:
            0x0224AF7C returns 0 immediately for selector 3 (so the class-2 short circuit at
            0x021EDC76 cannot fire); 0x021D3788's per-cid tree was executed over the whole cid
            space 0x0D48..0x24E8 and only 10 cids leave its reject leaf, every one of them
            additionally requiring desc[+5] to be 1 or 2 -- so NO cid can take that
            slot3-bypassing shortcut on a cls3 descriptor; 0x02023584's 7-cid list
            {0x0E47, 0x0E88, 0x1232, 0x149C, 0x1517, 0x1A67, 0x209B} is applied only when
            desc[+6] != 0, i.e. when enumerating the OTHER player's cards; and 0x0224A874 is
            self-satisfying ("does this cid own a cls3 record").

            The body is Blue-Eyes Shining Dragon's 0x021F8134 transcribed -- its printed text is
            clause 1's trigger verbatim -- with the clause-3 turn-log query folded in front:

              * r1 == 0 (nothing is being activated) -> 0.
              * CLAUSE 3: 0x021A14E8(side, 0x0B, cid, 1) nonzero -> 0. The key is the CID, so
                this is the SAME node clause 2 posts; "1 Maiden effect per turn" spans both
                clauses with no extra state and no second latch.
              * 0x021AB90C(act, 0) must return ZERO. Note the polarity -- BESD bails when it
                returns NONZERO (`cmp r0,#0 ; beq <loop bound>` @0x021F814A, the fall-through
                returning r4 which is still 0). It is the "this activation is immune to
                responses" test.
              * then for i in range(act[+0x10]): 0x02234904(act, i) returns a packed
                `side | (zone << 8)`; compare it against MY (desc[+3] << 8) | desc[+2].
                A hit means the activation declared THIS card as one of its targets.

            Returns 2, not BESD's 1: per dispatch.cls_slot_roles a 1 makes 0x0224AD94 consult
            slot2 for a board target, and >= 2 means "activatable unconditionally". With +08 = 0
            the two are equivalent (0x0224AE1A skips an absent slot2), but 2 states the intent
            and matches clause 2's condition.

            NO opponent-only filter -- deliberate. Naturia White Oak's 0x02201FDD splits the
            halfword and demands the activator be the opponent, matching ITS printed "an
            opponent's card effect". Maiden's text says "a card or effect", so BESD's unfiltered
            form is the faithful one and she answers your own targeting too.

            r4-r7 are used across the BLXs because AAPCS makes them callee-saved, and BESD's own
            loop relies on exactly that (it keeps its counter in r4 across `bl 0x02234904`).
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("CMP", "R5, #0x0")
            b.insn("BEQ", "reject")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("MOV", "R1, #0xB")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.call("turnlog_query", R0, R1, R2, 1, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "reject")
            b.call_addr(0x021AB90C, R5, 0, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "reject")
            b.insn("MOV", "R6, #0x0")
            b.label("loop")
            b.insn("LDRB", "R0, [R5, #0x10]")
            b.insn("CMP", "R6, R0")
            b.insn("BGE", "reject")
            b.call_addr(0x02234904, R5, R6, via=R7)
            b.insn("LDRB", "R1, [R4, #0x3]")
            b.insn("LSL", "R1, R1, #0x8")
            b.insn("LDRB", "R2, [R4, #0x2]")
            b.insn("ORR", "R1, R2")
            b.insn("LSL", "R1, R1, #0x10")
            b.insn("LSR", "R1, R1, #0x10")
            b.insn("CMP", "R1, R0")
            b.insn("BEQ", "accept")
            b.insn("ADD", "R6, #0x1")
            b.insn("B", "loop")
            b.label("accept")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("reject")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")

        def _c1_res_stub(base: int) -> bytes:
            """CLAUSE 1 slot1: stamp the turn log, then hand over to the shared SS machine.

            Clause 1's payload is EXACTLY clause 2's -- "Special Summon 1 Blue-Eyes White
            Dragon from your hand, Deck, or GY" -- and that payload is the ONE criteria row
            PART A2 already ships, in-game confirmed to summon from all three zones. So this
            resolver owns no verbs of its own; it exists only to POST the once-per-turn node
            before delegating, because 0x02206F41's phase-0x80 arm turn-logs per-cid only for
            the cards its prologue switch names and a records-free donor takes the default arm.

            resolver.phase_protocol (VERIFIED): a resolver is re-entered once per resolution
            phase, the phase lives at [0x0229AAFC + 0x70], the entry phase is 0x80 and the
            return value NAMES THE NEXT PHASE. So the post is gated on phase == 0x80 and EVERY
            phase -- 0x80 included -- tail-calls 0x02206F41, whose own arms cover 0x80 (count
            candidates + prompt), 0x7F (open the picker), 0x7E (summon) and the teardown.
            r1 = the event must be preserved: 0x02206F40 parks it with `str r1,[sp]` @0x02206F48
            and re-reads it for the 0x021F0384 gate.

            Same shape as CAVE_MAIDEN_RES, minus the negate and the position toggle.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, 1, via=R6)
            b.call_addr(0x02206F40, R4, R5, via=R6)
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")

        def _c1_cost_stub(base: int, diag: bool = False) -> bytes:
            """CLAUSE 1 slot4: the costless "you can", PLUS the once-per-turn stamp.

            *** THE ONCE-PER-TURN HAS TO BE STAMPED AT ACTIVATION, NOT AT RESOLUTION. ***
            Measured in-game: with the stamp in the resolver, Maiden could be
            activated TWICE IN THE SAME CHAIN -- both activations query the turn log before
            either of them resolves, so both see it clear. The engine's own activation log is
            written late for the same reason, which is why the cross-turn cases all behaved
            correctly while the same-chain case did not.

            So the stamp moves into the activation procedure. This wrapper calls the shared
            body 0x021E50DC (NOT the thunk 0x021E51E5) and posts only when it returns 1.
            Reading 0x021E50DC: it runs on its own phase counter [0x0229AAFC + 0x7C] --
            ⚠️ NOT the resolver's [+0x70] -- with phase 0 = run slot3 then open the Yes/No
            dialog, phase 1 = read the answer, phase 2 = finish. Phase 1 is
            `ldr r1,[0x0229DD94 + 0x34] ; cmp r1,#0 ; bne 0x021E51AE`, and the non-zero arm
            (the player said YES) is the only one that returns 1; the zero arm advances the
            phase and returns 0 to abort. **Declining the prompt therefore does NOT burn the
            once-per-turn**, which is the correct reading of "you can".

            SAFE ONLY BECAUSE CLAUSE 1 IS cls3. timing.class_is_the_slot4_literal: the
            WHEN-vs-IF classifier 0x0224AF7C reads this slot's literal RAW and never calls it,
            so an unrecognised value would put the card in NO timing class -- but it returns 0
            at once for descriptor selectors 0 and 3, so a cls3 record's +0x10 is never read.
            Clause 2 is cls1 and MUST keep the bare 0x021E51E5 literal.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.ldr_const(6, 0x021E50DD)
            b.insn("BLX", "R6")
            b.insn("CMP", "R0, #0x1")
            b.insn("BNE", "out")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.turnlog_post(R0, R1, 1, via=R6)
            if diag:
                b.ldr_const(5, ov5_cave.CAVE_MD_DIAG3)
                b.insn("LDR", "R6, [R5, #0x18]")
                b.insn("ADD", "R6, #0x1")
                b.insn("STR", "R6, [R5, #0x18]")
            b.insn("MOV", "R0, #0x1")
            b.label("out")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")

        def _atktgt_list() -> bytes:
            """The zero-terminated u16 cid list CAVE_ATKTGT_GATE scans."""
            blob = struct.pack(f"<{len(ATKTGT_ADMIT)}H", *ATKTGT_ADMIT) + b"\x00\x00"
            assert len(blob) <= LIST_LEN, "admit-list overflows its cave slot"
            return blob + bytes(LIST_LEN - len(blob))


        LIST3_LEN = 0x08                    # the ov3 home (CAVE3_ATKTGT_LIST): 3 cids + terminator, FULL


        def _atktgt_gate(base: int, lst: int = ov5_cave.CAVE_ATKTGT_LIST) -> bytes:
            """Replaces `bl 0x021A37D8` at 0x021C6624; same ABI, returns the cid in r0.

            Calls the original (r0/r1/r2/r3 are untouched by the prologue, so the callee
            sees its real arguments), then remaps any cid in CAVE_ATKTGT_LIST to
            ATKTGT_ACCEPTED so the native per-cid switch below sets r6 = 1 and the
            code-0x13 post at 0x021C6798 fires.

            The remap is safe because the cid register is DEAD after the switch: the very
            next thing the caller does is `ldr r2,=0x02298AD8` at 0x021C6788, and the post
            itself takes only the side (r4) and the slot ([0x02298AD8 + 0xA]). The remap
            target is a PHANTOM (no card_prop record), so even if some path did read it,
            no real card's identity is borrowed.
            """
            return atktgt_gate.gate_code(base, lst)      # one copy of the gate, shared


        def _gate_slots(ov3: bool) -> tuple[int, int]:
            """(gate, list) addresses: the ov3 pool (puzzle-safe) or the old ov5 cave."""
            if ov3:
                return cave3.CAVE3_ATKTGT_GATE, cave3.CAVE3_ATKTGT_LIST
            return ov5_cave.CAVE_ATKTGT_GATE, ov5_cave.CAVE_ATKTGT_LIST

        def _quickeffect_list(sec_data: bytes) -> list[int]:
            off = QUICKEFFECT_LIST - 0x02000000
            return list(struct.unpack_from(f"<{QUICKEFFECT_COUNT}H", sec_data, off))


        def apply_quickeffect(rom) -> None:
            """Insert the donor into the ARM9 Spell-Speed-2 monster list, count-neutrally."""
            mc, sec = ov5_cave._arm9_main(rom)
            d = bytearray(sec.data)
            off = QUICKEFFECT_LIST - 0x02000000

            # anchors: the searched list and its hard-coded count must not have drifted
            lit = struct.unpack_from("<H", d, 0x0202348C - 0x02000000)[0]
            pool = ((0x0202348C + 4) & ~3) + (lit & 0xFF) * 4
            assert lit & 0xF800 == 0x4800 and \
                struct.unpack_from("<I", d, pool - 0x02000000)[0] == QUICKEFFECT_LIST, \
                "0x0202348C no longer loads the Spell-Speed-2 list base"
            assert struct.unpack_from("<H", d, 0x02023490 - 0x02000000)[0] == 0x2276, \
                "the list count immediate `movs r2,#0x76` at 0x02023490 drifted"

            lst = _quickeffect_list(bytes(d))
            if DONOR_CID in lst:
                print(f"F  Spell-Speed-2 list: 0x{DONOR_CID:04X} already present")
                return
            assert all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)), \
                "the Spell-Speed-2 list is not sorted before the edit"
            assert 0x17C2 in lst, \
                "Blue-Eyes Shining Dragon 0x17C2 is missing -- wrong list or wrong base ROM"
            assert lst.count(QUICKEFFECT_DROP) == 1, \
                f"phantom 0x{QUICKEFFECT_DROP:04X} appears {lst.count(QUICKEFFECT_DROP)}x"

            out = [c for c in lst if c != QUICKEFFECT_DROP]
            pos = next((i for i, c in enumerate(out) if c > DONOR_CID), len(out))
            out.insert(pos, DONOR_CID)
            assert len(out) == QUICKEFFECT_COUNT, "count changed"
            assert all(out[i] < out[i + 1] for i in range(len(out) - 1)), "lost its sort"

            struct.pack_into(f"<{QUICKEFFECT_COUNT}H", d, off, *out)
            sec.data = bytes(d)
            rom.arm9 = mc.save()
            print(f"F  Spell-Speed-2 list @0x{QUICKEFFECT_LIST:08X}: dropped phantom "
                  f"0x{QUICKEFFECT_DROP:04X}, inserted 0x{DONOR_CID:04X} at index {pos} "
                  f"-- count {QUICKEFFECT_COUNT}, sorted (clause 1 is a QUICK EFFECT)")

        def apply_effect(ov: bytearray, diag: bool = False, ov3: bool = False) -> None:
            res = ov5_cave.CAVE_MD_RES if diag else ov5_cave.CAVE_MAIDEN_RES
            cond = ov5_cave.CAVE_MD_COND if diag else ov5_cave.CAVE_MAIDEN_COND
            gate = ov5_cave.CAVE_MD_GATE if diag else _gate_slots(ov3)[0]
            c1res = ov5_cave.CAVE_MD_C1RES if diag else ov5_cave.CAVE_MAIDEN_C1_RES
            c1cond = ov5_cave.CAVE_MD_C1COND if diag else ov5_cave.CAVE_MAIDEN_C1_COND
            cls1_new = (DONOR_CID, res | 1, 0x00000000, cond | 1, 0x021E51E5, 0x00000000)
            c1cost = ov5_cave.CAVE_MD_C1COST if diag else ov5_cave.CAVE_MAIDEN_C1_COST
            cls3_new = (DONOR_CID, c1res | 1, 0x00000000, c1cond | 1, c1cost | 1, 0x00000000)

            recs = _cls1_records(ov)
            recs = _count_neutral_swap(recs, CLS1_PHANTOM_BEFORE, cls1_new,
                                       "cls1 (clause-2 attack-target trigger)")
            _write_cls1(ov, recs)

            # --- E: CLAUSE 1. A different table from clause 2's, so the leftmost-record
            # rule (which is per-table) cannot make either clause shadow the other. ---
            recs3 = _cls3_records(ov)
            recs3 = _count_neutral_swap(recs3, CLS3_PHANTOM_BEFORE, cls3_new,
                                       "cls3 (clause-1 targeted-by-a-card-or-effect trigger)")
            _write_cls3(ov, recs3)

            rows = _crit_rows(ov)
            rows = _count_neutral_swap(rows, CRIT_PHANTOM_BEFORE, CRIT_NEW,
                                       "criteria (SS 1 Blue-Eyes from hand/Deck/GY)")
            _write_crit(ov, rows)

            # --- A3: admit the donor to the attack-target event (see PART A3 above) ---
            if ov3 and not diag:            # the shared ov3 gate: Ninishi / Haipa may have installed it already
                atktgt_gate.install(ov, DONOR_CID)
                return
            cur = bytes(ov[_off(ATKTGT_BL_SITE):_off(ATKTGT_BL_SITE) + 4])
            want = _bl(ATKTGT_BL_SITE, gate)
            if cur == want:
                print(f"A  attack-target gate @0x{ATKTGT_BL_SITE:08X}: already hooked")
            else:
                assert cur == _bl(ATKTGT_BL_SITE, ATKTGT_HELPER), (
                    f"0x{ATKTGT_BL_SITE:08X} is not the stock `bl 0x{ATKTGT_HELPER:08X}` "
                    f"(found {cur.hex()}) -- the gate moved, re-run the switch simulation")
                ov[_off(ATKTGT_BL_SITE):_off(ATKTGT_BL_SITE) + 4] = want
                print(f"A  attack-target gate @0x{ATKTGT_BL_SITE:08X}: "
                      f"bl 0x{ATKTGT_HELPER:08X} -> gate 0x{gate:08X} "
                      f"(admits {[hex(c) for c in ATKTGT_ADMIT]} -> 0x{ATKTGT_ACCEPTED:04X})")


        # Every ov5 slot this patch owns: (name, address, builder, reserve, is_code).
        # main() installs them and verify() reads them back out of the built ROM.
        CAVE_SLOTS = (
            ("clause-2 condition", ov5_cave.CAVE_MAIDEN_COND, _cond_stub, COND_LEN, True),
            ("clause-2 resolver", ov5_cave.CAVE_MAIDEN_RES, _res_stub, RES_LEN, True),
            ("attack-target admit list", ov5_cave.CAVE_ATKTGT_LIST,
             lambda _a: _atktgt_list(), LIST_LEN, False),
            ("attack-target gate hook", ov5_cave.CAVE_ATKTGT_GATE, _atktgt_gate, GATE_LEN, True),
            ("clause-1 condition", ov5_cave.CAVE_MAIDEN_C1_COND, _c1_cond_stub, C1_COND_LEN, True),
            ("clause-1 resolver", ov5_cave.CAVE_MAIDEN_C1_RES, _c1_res_stub, C1_RES_LEN, True),
            ("clause-1 cost (once-per-turn stamp)", ov5_cave.CAVE_MAIDEN_C1_COST,
             _c1_cost_stub, 0x40, True),
        )


        stubs = []
        for name, addr, builder, reserve, is_code in CAVE_SLOTS:
            if addr in (ov5_cave.CAVE_ATKTGT_GATE, ov5_cave.CAVE_ATKTGT_LIST):    # shared gate + admit list live in the ov3 pool
                continue
            blob = builder(addr)
            if is_code:
                effect_verify.assert_thumb1_only(blob, addr)
            assert len(blob) <= reserve, f"{name}: {len(blob)} B exceeds the {reserve} B reservation"
            stubs.append((addr, blob, name))

        def install(rom, view):
            apply_effect(view.buf, diag=False, ov3=True)
            apply_quickeffect(rom)

        def check_fn(c, rom, view):
            def check(cond, msg):
                c.ok(bool(cond), msg)
                return bool(cond)

            ov = view.buf
            recs = _cls1_records(ov)
            cids = [r[0] for r in recs]
            check(cids.count(DONOR_CID) == 1, f"expected exactly 1 cls1 record for the donor, got {cids.count(DONOR_CID)}")
            check(CLS1_DROP_PHANTOM not in cids, "cls1 phantom dropped")
            check(len(recs) == CLS1_COUNT, "cls1 count unchanged")
            check(all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)), "cls1 sorted")
            rec = recs[cids.index(DONOR_CID)]
            expect = (DONOR_CID, ov5_cave.CAVE_MAIDEN_RES | 1, 0x00000000, ov5_cave.CAVE_MAIDEN_COND | 1, 0x021E51E5, 0x00000000)
            check(rec == expect, f"cls1 record {[hex(x) for x in rec]}")
            check(all(idxs == list(range(idxs[0], idxs[0] + len(idxs))) for idxs in _dup_groups(cids).values()),
                  "cls1: every multi-record cid is still contiguous")

            recs3 = _cls3_records(ov)
            cids3 = [r[0] for r in recs3]
            check(cids3.count(DONOR_CID) == 1, f"expected exactly 1 cls3 record for the donor, got {cids3.count(DONOR_CID)}")
            check(CLS3_DROP_PHANTOM not in cids3, "cls3 phantom dropped")
            check(len(recs3) == CLS3_COUNT, "cls3 count unchanged")
            check(all(cids3[i] <= cids3[i + 1] for i in range(len(cids3) - 1)), "cls3 sorted")
            rec3 = recs3[cids3.index(DONOR_CID)]
            expect3 = (DONOR_CID, ov5_cave.CAVE_MAIDEN_C1_RES | 1, 0x00000000, ov5_cave.CAVE_MAIDEN_C1_COND | 1,
                       ov5_cave.CAVE_MAIDEN_C1_COST | 1, 0x00000000)
            check(rec3 == expect3, f"cls3 record {[hex(x) for x in rec3]}")
            check(all(idxs == list(range(idxs[0], idxs[0] + len(idxs))) for idxs in _dup_groups(cids3).values()),
                  "cls3: every multi-record cid is still contiguous")
            check(rec3[0] == rec[0] and CLS3_BASE != CLS1_BASE, "the two clauses are in different tables")
            check(rec3[1] != rec[1] and rec3[3] != rec[3], "the two clauses' records point at different stubs")
            check(rec[4] == 0x021E51E5, "clause 2 keeps its class-2 timing tag at +0x10")
            check(rec3[4] == ov5_cave.CAVE_MAIDEN_C1_COST | 1, "clause 1's +0x10 is the once-per-turn stamp wrapper")

            besd = [r for r in recs3 if r[0] == 0x17C2]
            check(besd and besd[0][3] == 0x021F8135, "Blue-Eyes Shining Dragon 0x17C2 still has its targeted-by-an-effect condition")
            check(struct.unpack_from("<H", ov, _off(0x021F813A))[0] & 0xFF00 == 0xD100, "0x021F813A is still the `r1 == 0` BNE bail")
            check(struct.unpack_from("<H", ov, _off(0x021F8170))[0] == 0x7C28, "0x021F8170 still reads the pick COUNT act[+0x10]")
            check(struct.unpack_from("<H", ov, _off(0x0224AD98))[0] == 0x9100, "0x0224AD98 still parks the invoker's r1 at [sp]")
            check(struct.unpack_from("<H", ov, _off(0x0224AE0C))[0] == 0x9900, "0x0224AE0C still reloads [sp] as slot3's r1")
            check(struct.unpack_from("<H", ov, _off(0x0224A16E))[0] == 0x4D90 and struct.unpack_from("<I", ov, _off(0x0224A3B0))[0] == CLS3_BASE,
                  "find_event_handler's selector-3 arm still loads the cls3 base")

            rows = _crit_rows(ov)
            ccids = [r[0] for r in rows]
            check(ccids.count(DONOR_CID) == 1, f"expected exactly 1 criteria row for the donor, got {ccids.count(DONOR_CID)}")
            check(CRIT_DROP_PHANTOM not in ccids, "criteria phantom dropped")
            check(len(rows) == CRIT_COUNT, "criteria count unchanged")
            check(all(ccids[i] <= ccids[i + 1] for i in range(len(ccids) - 1)), "criteria registry sorted")
            row = rows[ccids.index(DONOR_CID)]
            check(row == CRIT_NEW, f"criteria row {[hex(x) for x in row]}")
            check(row[1] == BEWD_CID, "the row names Blue-Eyes White Dragon")

            check(struct.unpack_from("<H", ov, _off(0x0221F9E4))[0] == 0x7928, "Krebons' event-code gate 0x0221F9E4 intact")
            stego = [r for r in recs if r[0] == 0x1A78]
            check(stego and any(r[1] == 0x0220C6B1 for r in stego), "Black Stego 0x1A78 keeps its position-change record")

            site = bytes(ov[_off(ATKTGT_BL_SITE):_off(ATKTGT_BL_SITE) + 4])
            gate_a, list_a = _gate_slots(True)
            check(site == _bl(ATKTGT_BL_SITE, gate_a), f"0x{ATKTGT_BL_SITE:08X} is hooked to CAVE3_ATKTGT_GATE")
            check(struct.unpack_from("<H", ov, _off(0x021C678A))[0] == 0x2E00, "the attack-target post guard @0x021C678A is still `cmp r6,#0`")
            check(struct.unpack_from("<H", ov, _off(0x021C6794))[0] == 0x2213, "the guarded post @0x021C6794 still loads event code 0x13")
            check(bytes(ov[_off(0x021C6798):_off(0x021C6798) + 4]) == _bl(0x021C6798, 0x021D3230),
                  "the guarded post still calls the cls1 event poster 0x021D3230")

            _mc, sec = ov5_cave._arm9_main(rom)
            qlst = _quickeffect_list(bytes(sec.data))
            check(len(qlst) == QUICKEFFECT_COUNT, "Spell-Speed-2 list count unchanged")
            check(all(qlst[i] < qlst[i + 1] for i in range(len(qlst) - 1)), "Spell-Speed-2 list sorted (binary-searched)")
            check(DONOR_CID in qlst, "the donor is in the Spell-Speed-2 list")
            check(QUICKEFFECT_DROP not in qlst, "Spell-Speed-2 phantom dropped")
            check(0x17C2 in qlst, "Blue-Eyes Shining Dragon 0x17C2 still in the list")
            for name, addr, builder, _reserve, is_code in CAVE_SLOTS:
                if addr in (ov5_cave.CAVE_ATKTGT_GATE, ov5_cave.CAVE_ATKTGT_LIST):
                    continue
                want = builder(addr)
                got = ov5_cave.read_cave(rom, addr, len(want))
                check(got == want, f"ov5 {name} bytes at 0x{addr:08X}")
                if is_code:
                    effect_verify.assert_thumb1_only(got, addr)
            want = _atktgt_gate(gate_a, list_a)
            check(bytes(ov[_off(gate_a):_off(gate_a) + len(want)]) == want, f"ov3 attack-target gate bytes at 0x{gate_a:08X}")
            effect_verify.assert_thumb1_only(want, gate_a)

            lst = bytes(ov[_off(list_a):_off(list_a) + LIST3_LEN])
            admitted = []
            for i in range(0, LIST3_LEN, 2):
                cc = struct.unpack_from("<H", lst, i)[0]
                if cc == 0:
                    break
                admitted.append(cc)
            check(sorted(admitted) == sorted(ATKTGT_ADMIT),
                  f"attack-target admit list is {[hex(x) for x in admitted]}, expected {[hex(x) for x in ATKTGT_ADMIT]}")
            check(0x0FFD in admitted, "Ninishi 0x0FFD is admitted")

        return Compiled(stubs=tuple(stubs), installs=(install,), checks=(check_fn,))


maiden_effects = quick_effect_targeted_by_card_or_attacked_negate_attack_change_position_special_summon_blue_eyes_white_dragon_once_per_turn

SPEC = card(0x1ED7, maiden_effects())

PROPS = card_props("LIGHT", "Spellcaster", level=1, atk=0, defense=0, card_type="Tuner Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_maiden.nds")

# Names other modules read from this one (dsl.py's criteria-row verb imports CRIT_*); verbatim from the original.
DONOR_CID = 0x1ED7          # Comrade Swordsman of Landstar
BEWD_CID = 0x0FA7           # Blue-Eyes White Dragon -- the only obtainable art

# ---------------------------------------------------------------------------
# PART A1 -- cls1 (dispatcher event-class table 1)
# ---------------------------------------------------------------------------
CLS1_BASE = 0x022860D4
CLS1_COUNT = 0x535          # 1333 records, stride 24
CLS1_STRIDE = 24
# Phantom dropped to keep the count. 0x1DB6 has NO card_prop record (so it can
# never be instantiated and its record can never be dispatched), owns exactly ONE
# cls1 record, and is claimed by no other patch.
CLS1_DROP_PHANTOM = 0x1DB6
CLS1_PHANTOM_BEFORE = (0x1DB6, 0x022288C5, 0x00000000, 0x021F2BD9, 0x021E51E5, 0x00000000)

# ---------------------------------------------------------------------------
# PART A2 -- criteria / populate registry
# ---------------------------------------------------------------------------
CRIT_BASE = 0x022713C4
CRIT_COUNT = 1388
CRIT_STRIDE = 12
CRIT_FMT = "<HHIHH"         # {cid, aux, handler, flags, extra}
CRIT_DROP_PHANTOM = 0x1BBE  # no card_prop; owns exactly one row; unclaimed
CRIT_PHANTOM_BEFORE = (0x1BBE, 0x0020, 0x0223CAF5, 0x0002, 0x0000)
CRIT_NEW = (DONOR_CID, BEWD_CID, 0x0223E2C9, 0x0802, 0x0000)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
