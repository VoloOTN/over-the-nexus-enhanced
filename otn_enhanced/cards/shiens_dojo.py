"""Shien's Dojo (Field Spell) on Ancient Gear Castle 0x19B2.

See notes/shiens-dojo-findings.md and card_text.CARD_TEXT[0x19B2] for the printed text: each Normal/Special Summon of a
"Six Samurai" monster places a Bushido Counter on this card; send it to the GY to Special Summon a "Six Samurai" or "Shien"
Effect Monster from the Deck by Level.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, Compiled, NATIVE_COND, REG_ROW_ADDR
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import cave3
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
import struct


@dataclass(frozen=True)
class each_six_samurai_summon_place_bushido_counter_send_to_graveyard_special_summon_six_samurai_or_shien_level_4_or_lower_from_deck:
    """Shien's Dojo (Ancient Gear Castle 0x19B2, a Field Spell kept as a Spell): 'Each time a "Six Samurai" monster(s) is Normal or Special Summoned,
    place 1 Bushido Counter on this card. You can send this card to the GY; Special Summon 1 "Six Samurai" or "Shien" Effect Monster from your Deck whose
    Level is up to the number of Bushido Counters (max 4 per the cap).' Bushido-arming registry row over 0x2349, the arm hook on the third Bushido arm call,
    the donor's native accrual and own effects retired, an uncapped Bushido capacity, the cls3 deck-SS record over 0x1941 and a criteria row over 0x19B5 whose
    handler ORs the two set codes, with three ov3-pool stubs (the Level-bound writer finds the row by cid at runtime). The legacy in-place name/description
    write for f/g/i/s is kept as a post. Original code embedded verbatim."""

    def compile(self, view, cid) -> Compiled:
        import struct
        import ndspy.rom
        from otn_enhanced.asm.effect_verify import assert_thumb1_only
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.rom.pac import parse_pac
        from otn_enhanced.effects.ov5_cave import CAVE_DOJO_CB, CAVE_DOJO_CRIT, CAVE_DOJO_LVL, install_cave
        from otn_enhanced.data.card_stats import iter_paths, read_cstr, rebuild_v1_pac
        from otn_enhanced.effects import cave3
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R3
        from otn_enhanced.effects.common import ov3_off as _off

        DONOR_CID = 0x19B2          # Ancient Gear Castle (keep-cid rule)

        # ---------------------------------------------------------------------------
        # PART D -- neutralising the donor's native counter accrual
        # ---------------------------------------------------------------------------
        # Ancient Gear Castle natively does "Each time a monster is Normal Summoned/Set,
        # place 1 counter on this card" at 0x02265F96:
        #     loop zone 5..9: if 0x021ABFA8(side, zone, 0x19B2) then
        #                     0x021C7D80(side, zone, type=1, amount=1)
        # That is counter TYPE 1, a different type from Bushido (6), so leaving it in
        # would put two counter stacks on one card and corrupt the clause-1 oracle.
        # The test is a plain equality lookup (not an ordered comparison chain), so the
        # cid literal can be repointed at any cid with no card_prop record and the match
        # simply never succeeds -- the same "retargeted code literal" technique
        # safe_zone and escuridao already use (the lp_literal pool).
        ACCRUAL_POOL = 0x02265FF8       # the literal read by the LDR at 0x02265F96
        DEAD_CID = 0x1A50               # no card_prop record; unclaimed by any patch

        # ---------------------------------------------------------------------------
        # PART E -- the counter CAPACITY gate  (this is what made round 1 accrue nothing)
        # ---------------------------------------------------------------------------
        # 0x021C7D80 does not place a counter blindly.  It calls
        #     0x021A2F10(side, zone, type) -> "how many counters of this TYPE may the
        #                                      card at this zone hold?"
        # and bails (returns 0, places nothing) when that is 0 or already reached.
        # 0x021A2F10 switches on the counter type; the TYPE 6 (Bushido) arm is a
        # hard-coded per-cid chain at 0x021A2F9E:
        #     0x1D22 Six Samurai United  -> 2      <- the real "(max. 2)" of that card
        #     0x219A Gateway of the Six  -> 0xFF
        #     0x247E Temple of the Six   -> 0xFF
        #     ...anything else           -> 0      (falls through to 0x021A3014)
        # R0 there is the cid of the card in the zone (from 0x021A36F8).  A donor with no
        # entry therefore has Bushido capacity 0 and can never receive a counter, no
        # matter how correctly it is armed or registered.  Shien's Dojo is uncapped, so
        # the donor is given 0xFF like Gateway/Temple.
        #
        # The chain's first arm is displaced into a stub: LR is free to clobber because
        # the enclosing function pushed it at 0x021A2F10 (PUSH {R3,R4,R5,LR}).
        CAP_LEAF = 0x021A2F9E           # the type-6 arm's first instruction
        CAP_LEAF_ORIG = bytes.fromhex("2649" "8842")   # LDR R1,[PC,#0x98] ; CMP R0,R1
        CAP_LEAF_RESUME = 0x021A2FA2    # the BNE that follows the displaced pair
        CAP_FIRST_CID = 0x1D22          # the value the displaced LDR loaded
        DOJO_CAPACITY = 0xFF            # uncapped, like Gateway of the Six / Temple

        CAP_BLOCK = 0x021B58E8          # dead leaf of phantom arm 0x194C (block 0x021B58E6)
        CAP_BLOCK_FREE = 28             # 30 B block - 2 B alignment slack
        CAP_PHANTOM_CID = 0x194C
        # ---------------------------------------------------------------------------
        # PART F -- retiring the rest of Ancient Gear Castle
        # ---------------------------------------------------------------------------
        # Five sites take the donor cid either as a plain equality test or as a call
        # argument, so repointing their literal at a cid with no card_prop record makes
        # them dead without touching any code:
        #   0x0225D274  0x021ACC10(side, cid, n)          Tribute-substitution helper
        #   0x0225E4F8  CMP R0,cid / BNE                  Tribute-substitution dispatch
        #   0x022613AC  0x021ABFA8(side, zone, cid)       "is this zone the Castle"
        #   0x02261CE4  call argument (four LDR users)    Tribute-substitution
        #   0x02267A5C  LDRH [R4,#0x12]; CMP; BEQ         Tribute-substitution flag
        RESIDUAL_POOLS = (0x0225D274, 0x0225E4F8, 0x022613AC, 0x02261CE4, 0x02267A5C)

        # ---------------------------------------------------------------------------
        # PART G -- CLAUSE 2 (Six Samurai only; see the deviation note below)
        # ---------------------------------------------------------------------------
        # "You can send this card to the GY; Special Summon 1 'Six Samurai' or 'Shien'
        #  Effect Monster from your Main Deck, whose Level is <= the number of Bushido
        #  Counters on this card."
        #
        # Two count-neutral inserts, no new code:
        #
        # (G1) A cls3 record for the donor, cloned from **Six Samurai United's**
        #      cls3[370] -- which is already exactly this card's activation shape
        #      ("You can send this card to the GY; <payload>"):
        #          +04 resolution   0x022065B9  draw N        -> 0x02206CAD  SS from Deck
        #          +08 0
        #          +0C condition    0x021FD489  "do I hold >=1 counter of type R2?"
        #                           Its per-cid R2 DEFAULTS TO 6 (Bushido) -- only
        #                           0x1F78 (R2=0) and 0x23A5 (R2=0x17) are special-cased
        #                           -- so the donor inherits the Bushido test for free.
        #                           It reads the count with 0x021A3054(side, zone, 6),
        #                           the same accessor PART E's capacity gate uses.
        #          +10 cost/timing  0x021E6FF5  (send-self-to-GY cost tag)
        #      cls3 is sorted by cid with a hard count (0x308 = 776 rows x 24 B), so the
        #      insert drops the phantom row 223 (cid 0x1941, no card_prop) and shifts
        #      rows 224..233 down one, landing the donor at index 233 between 0x19A9 and
        #      0x19BB.
        #
        # (G2) A criteria-registry row (counter.criteria_registry_layout). Row **409**
        #      is ITSELF a phantom (cid 0x19B5, no card_prop) and sits between 0x19B1 and
        #      0x19B6 -- so the donor's row is written straight over it with NO shifting
        #      and the sort order still holds. Contents mirror Shien's Footsoldier:
        #          +0x02 filter 0x001E   the Six Samurai set code
        #          +0x04 handler 0x0223CAB5  the "SS from Deck" criteria handler
        #          +0x08 flags   0x0002
        #          +0x0A extra   0x0090  = 0x80 | (4 << 2) -> Level <= 4
        #
        # ⚠️ TWO DELIBERATE, DOCUMENTED DEVIATIONS FROM THE PRINTED CARD:
        #   1. **Six Samurai only.** The row filters by ONE set code. "Six Samurai" is
        #      0x1E; "Shien" is not a set code anywhere in this engine, so Great Shogun
        #      Shien / Footsoldier / Enishi / Squire are not valid targets yet. Adding
        #      them needs a hook in the criteria handler 0x0223CAB5.
        #   2. **The Level bound is STATIC (<= 4), not "<= the Bushido Counters".**
        #      +0x0A is a static field. Making it dynamic means writing
        #      `0x80 | (min(N,12) << 2)` into it at activation time from a stub -- ~44 B,
        #      but the largest contiguous free ov3 dead block left is 28 B. It cannot go
        #      in ov5 (a puzzle evicts ov5 and the record's slot would jump into dead
        #      memory). Blocked on ov3 cave space; see notes/shiens-dojo-findings.md.
        CLS3_BASE, CLS3_COUNT, CLS3_STRIDE = 0x02279D74, 0x308, 24
        CLS3_DROP_ROW = 223             # phantom cid 0x1941 (no card_prop record)
        CLS3_DROP_CID = 0x1941
        CLS3_INSERT_ROW = 233           # lands between 0x19A9 and 0x19BB
        DECK_SS_RESOLVER = 0x02206CAD   # counter.deck_ss_resolver
        UNITED_CLS3_ROW = 370           # the record we clone the wrapper slots from

        CRIT_BASE, CRIT_COUNT, CRIT_STRIDE = 0x022713C4, 1388, 12
        CRIT_ROW = 409                  # where the phantom sits in the STOCK table (see crit_row())
        CRIT_ROW_ORIG_CID = 0x19B5      # ... and the phantom cid, which is the REAL anchor
        SIX_SAMURAI_SETCODE = 0x001E
        CRIT_HANDLER_NATIVE = 0x0223CAB5   # Shien's Footsoldier's "SS from Deck" handler
        CRIT_HANDLER = CAVE_DOJO_CRIT | 1  # PART I: our clone, which ORs the two set codes
        # ov3 compaction (main(ov3=True) default: the three PART H/I stubs in the ov3 pool.
        # LVL = cls3 +0C (find_event_handler), CRIT = criteria h (0x02243F74), CB = builder blx r4 -- all ov3.
        LVL3, CB3, CRIT3 = cave3.CAVE3_DOJO_LVL, cave3.CAVE3_DOJO_CB, cave3.CAVE3_DOJO_CRIT


        def _addrs(ov3: bool) -> tuple[int, int, int]:
            """(LVL, CB, CRIT) stub addresses for the ov5 or the ov3 placement."""
            return (LVL3, CB3, CRIT3) if ov3 else (CAVE_DOJO_LVL, CAVE_DOJO_CB, CAVE_DOJO_CRIT)
        CRIT_FLAGS = 0x0002
        CRIT_LEVEL_CAP = 4
        CRIT_EXTRA = 0x80 | (CRIT_LEVEL_CAP << 2)   # 0x90 -> Level <= 4 (the seed value)
        CRIT_EXTRA_ADDR = CRIT_BASE + CRIT_ROW * CRIT_STRIDE + 0x0A   # STOCK-table address; see crit_row()


        def crit_row(ov: bytearray) -> int:
            """Index of this card's criteria row in *ov*, LOCATED BY CID.

            ⚠️ NEVER index this table by a hardcoded row number. The criteria registry is
            shared and count-neutral inserts by other patches move every row between their
            dropped phantom and their inserted cid: a patch that drops a phantom above
            0x19B5 and inserts below it pushes this row DOWN one, and
            gates_of_dark_world (which drops two phantoms below and inserts higher)
            pulls it UP two. Both happen in the combined chain, and their sum is whatever
            today's patch list happens to be.

            That is not a theoretical hazard: on 2026-09-10 the chain died here at step
            24/55 with "criteria row 409 is 0x19B1, expected phantom 0x19B5" -- the guard
            below firing because a step before this one had shifted the table by one. The
            guard is also load-bearing at RUNTIME, because build_level_stub() bakes this
            row's bound-byte ADDRESS into an ov5 stub as a literal: an unnoticed shift
            would have had that stub writing into a NEIGHBOURING card's row every time the
            effect was activated.

            Returns the donor's own row when it is already claimed (idempotent re-apply),
            else the phantom's.
            """
            keys = [struct.unpack_from("<H", ov, _off(CRIT_BASE + i * CRIT_STRIDE))[0]
                    for i in range(CRIT_COUNT)]
            for cid, what in ((DONOR_CID, "donor (already claimed)"),
                              (CRIT_ROW_ORIG_CID, "phantom")):
                hits = [i for i, k in enumerate(keys) if k == cid]
                if len(hits) == 1:
                    return hits[0]
                if len(hits) > 1:
                    raise RuntimeError(
                        f"criteria registry has {len(hits)} rows for the {what} cid "
                        f"0x{cid:04X} ({hits}); expected exactly one")
            raise RuntimeError(
                f"criteria registry holds neither the donor 0x{DONOR_CID:04X} nor the "
                f"phantom 0x{CRIT_ROW_ORIG_CID:04X} -- another patch consumed this row")

        # ---------------------------------------------------------------------------
        # PART H -- the counter-derived Level bound (clause 2, the real thing)
        # ---------------------------------------------------------------------------
        # IN-GAME CONFIRMED (user): with the row's bound byte = 0x90 the card summons
        # Level <= 4 Six Samurai and REFUSES Level 5+. So row +0x0A IS the Level bound,
        # encoded 0x80 | (L << 2) -- the earlier doubt (none of the three thin criteria
        # handlers reads +0x0A) was inconclusive, not decisive: the field is consumed
        # downstream, by the worker 0x0223BC3C / its callback, which is what actually
        # walks the Deck.
        #
        # That makes the dynamic bound cheap: the bound is plain data, so it just has to
        # be REWRITTEN from the live counter count before each search. The stub is
        # installed as the donor's OWN cls3 +0C slot -- the activation condition, which
        # the engine evaluates before offering/resolving the effect, and which is ours
        # alone (no shared-function surgery). It recomputes N with the engine's own
        # accessor, clamps to the maximum Level, writes the byte, then tail-calls the
        # native condition and returns its verdict unchanged.
        #
        # ov5 hosting is safe here (and was the user's call): a cls-record slot is
        # CID-KEYED -- dereferenced only when this card is involved -- not a shared
        # always-executing path like the PART B/E hooks. ov5 cave deck-search stubs are
        # in-game proven (see the ov5_cave.py note on Reborn Tengu / Gravekeeper's
        # Recruiter). Cost: normal duels only, which is this project's documented norm.
        NATIVE_COND = 0x021FD489        # the condition slot we wrap ("do I hold >=1 type-6 counter?")
        COUNTER_COUNT = 0x021A3054      # 0x021A3054(side, zone, type) -> current count
        MAX_LEVEL = 12

        # ---------------------------------------------------------------------------
        # PART I -- "Six Samurai OR Shien" (the last deviation)
        # ---------------------------------------------------------------------------
        # A criteria row holds ONE set code, but the card needs two. All 112 set codes
        # were enumerated via the ARM9 thunk table 0x0209D0D8: 0x1E = Six Samurai,
        # 0x4F = the "Shien" name group (0x0209C664: Great Shogun Shien, Footsoldier,
        # Enishi, Shien's Squire + 2 phantoms). There is no combined code.
        #
        # The fix is small because the search is callback-driven. The generic criteria
        # handler 0x0223CAB4 hands the worker 0x0223BC3C a per-candidate predicate
        # 0x0223C825, which does:
        #     r0 = [[sp+0]] & 0x3FFF          (the candidate's cid, 14 bits)
        #     r1 = [[sp+4]]                   (the filter = the row's set code)
        #     tail-call 0x020240D9(cid, setcode)
        # and 0x020240D8 is simply `if setcode < 0x70: thunk = 0x0209D0D8[setcode]; return
        # thunk(cid)`. So ORing two codes = replacing that one predicate.
        #
        #   CAVE_DOJO_CB   the OR predicate: has_set_code(cid, 0x1E) || (cid, 0x4F).
        #                  It reads the candidate from [sp+0] exactly as the original
        #                  does (BEFORE pushing, so SP is still the caller's), and
        #                  ignores the row's filter word entirely.
        #   CAVE_DOJO_CRIT a faithful clone of 0x0223CAB4 with the baked-in callback
        #                  literal swapped for CAVE_DOJO_CB. The row's +0x02 stays
        #                  0x001E so anything else reading the filter is unchanged.
        HAS_SET_CODE = 0x020240D9       # has_set_code(cid, setcode) -> 0/1
        CRIT_WORKER = 0x0223BC3C        # the search worker the handler tail-calls
        SETCODE_SIX_SAMURAI = 0x1E
        SETCODE_SHIEN = 0x4F

        # The sixth -- "All Ancient Gear monsters gain 300 ATK" -- is an arm of an
        # ORDERED comparison chain in the continuous stat engine:
        #     0x021B3290  LDR R0,[PC,#0x244]   (= 0x19B2)
        #     0x021B3292  CMP R4,R0
        #     0x021B3294  BEQ 0x021B336A       <- the +300 ATK leaf
        #     0x021B3296  B   0x021B355E       <- the shared "no entry" exit
        # Repointing its literal would move a node of a sorted binary chain and mis-route
        # every cid in that interval (the escuridao footgun). Instead the LEAF DISPATCH
        # is removed: NOP the BEQ so a match falls through to the very same
        # `B 0x021B355E` that the non-match path -- and the neighbouring arm -- already
        # take. The comparison and the chain's shape are untouched, so no sort-interval
        # reasoning is needed at all.
        ATK_ARM_BEQ = 0x021B3294
        ATK_ARM_BEQ_ORIG = 0xD069       # BEQ 0x021B336A
        THUMB_NOP = 0x46C0              # MOV R8, R8 -- the ARMv4T canonical NOP

        CAP_BLOCK_ORIG = bytes.fromhex(
            "0121" "081a" "f7f73cfb" "c821" "4143" "0398" "6418" "f7f736fb"
            "411e" "7d20"
        )                                                 # the 24 B we overwrite

        # ---------------------------------------------------------------------------
        # PART A -- the continuous-trigger registry
        # ---------------------------------------------------------------------------
        REG_BASE = 0x02275510           # 181 rows x 8 B: {+0x00 handler, +0x04 cid}
        REG_COUNT = 0xB5                # the count immediate both walkers hard-code
        REG_ROW = 137                   # the dead row we claim
        REG_ROW_ADDR = REG_BASE + REG_ROW * 8            # 0x02275958
        REG_ROW_ORIG = (0x02244431, 0x2349)              # handler, phantom cid (no card_prop)
        BUSHIDO_THUNK = 0x022473C5      # {MOV R1,#6 (Bushido); MOV R2,#1} -> 0x02247304

        # Rows 76/77/78 are Six Samurai United / Temple of the Six / Gateway of the Six.
        UNITED_ROW = 76                 # (0x02275770 - REG_BASE) // 8

        # The two registry walkers, only for the verify() guard that the count is intact.
        WALKER_A_COUNT_IMM = 0x02248196     # CMP R4, #0xB5
        WALKER_B_COUNT_IMM = 0x0224821C     # CMP R5, #0xB5

        # ---------------------------------------------------------------------------
        # PART B -- the arm site and the ov3 dead-code host
        # ---------------------------------------------------------------------------
        ARM_PRIM = 0x02244418           # 0x02244418(cid) -> arms that card on both sides
        ARM_BL_SITE = 0x02266BDC        # the third arm call (Temple of the Six, R0=0x247E)
        TEMPLE_CID = 0x247E             # what R0 already holds when the BL is taken

        # The declared dead block starts at 0x021B582A, but the assembler needs a
        # 4-aligned base for its PC-relative literal pool, so the stub starts 2 B in.
        # Those 2 leading bytes are left as they were: they are inside the same dead
        # leaf and are only ever reached from the phantom arm that can never match.
        DOJO_BLOCK = 0x021B582C         # dead leaf of stat-engine phantom arm cid 0x1827
        DOJO_BLOCK_FREE = 28            # 30 B block - 2 B alignment slack
        DOJO_PHANTOM_CID = 0x1827       # the non-existent card whose dead leaf this was
        DOJO_BLOCK_ORIG = bytes.fromhex(
            "0421" "0425" "f7f7befa" "0028" "08d1" "0398" "0121"
            "081a" "291c" "f7f7b6fa" "0028" "00d1"
        )                                                 # the 28 B we overwrite

        # ---------------------------------------------------------------------------
        # PART C -- card face (card_prop untouched; the donor is already Continuous)
        # ---------------------------------------------------------------------------
        NEW_NAME = b"Shien's Dojo"      # 12 B
        NEW_DESC = (                    # 299 B -- fits the donor's 304 B English slot
            b'Each time a "Six Samurai" monster(s) is Normal or Special Summoned, '
            b'place 1 Bushido Counter on this card. You can send this card to the GY; '
            b'Special Summon 1 "Six Samurai" or "Shien" Effect Monster from your Main '
            b'Deck, whose Level is less than or equal to the number of Bushido '
            b'Counters on this card.'
        )
        LANGS = "efgis"                 # English/French/German/Italian/Spanish


        # ===========================================================================
        # Helpers
        # ===========================================================================


        def _thumb_bl_bytes(site: int, target: int) -> bytes:
            """Encode the two-halfword ARMv4T ``BL`` at *site* branching to *target*."""
            off = target - (site + 4)
            if not -(1 << 22) <= off < (1 << 22):
                raise ValueError(f"BL 0x{site:08X} -> 0x{target:08X} out of range")
            off &= (1 << 23) - 1
            hi = 0xF000 | (off >> 12)
            lo = 0xF800 | ((off >> 1) & 0x7FF)
            return struct.pack("<HH", hi, lo)


        def build_arm_stub(base: int) -> bytes:
            """The 20 B stub that arms Temple of the Six *and* the donor.

            Entered by the retargeted ``BL`` at :data:`ARM_BL_SITE`, where R0 already
            holds 0x247E (loaded by the ``LDR`` at 0x02266BDA).  The first call is
            therefore byte-for-byte the behaviour that was displaced, so Temple of the
            Six is unaffected.

            Thumb-1 note: the return is ``PUSH {LR}`` / ``POP {PC}``.  Thumb-1 cannot
            ``POP`` into LR -- ``POP {..., LR}`` silently miscodes to ``POP {..., PC}``
            (see the thumb.pop_into_lr footgun).
            """
            a = EffectBuilder()
            (a
             .insn("PUSH", "{LR}")                 # R0 = 0x247E on entry
             .bl(ARM_PRIM)                         # the displaced original: arm Temple
             .ldr_const(0, DONOR_CID)              # r0 = 0x1F75
             .bl(ARM_PRIM)                         # arm Shien's Dojo
             .insn("POP", "{PC}"))
            blob = a.assemble(base)
            assert_thumb1_only(blob, base)         # never trust a bare capstone disasm
            if len(blob) > DOJO_BLOCK_FREE:
                raise RuntimeError(
                    f"arm stub is {len(blob)} B, only {DOJO_BLOCK_FREE} B are free "
                    f"at 0x{base:08X}")
            return blob


        # ===========================================================================
        # PART A
        # ===========================================================================
        def apply_registry_row(ov: bytearray) -> None:
            """Claim the dead registry row for the donor (count-neutral, 8 bytes)."""
            cur = struct.unpack_from("<II", ov, _off(REG_ROW_ADDR))
            if cur == (BUSHIDO_THUNK, DONOR_CID):
                print(f"  PART A: registry row {REG_ROW} already claimed -- skipping")
                return
            if cur != REG_ROW_ORIG:
                raise RuntimeError(
                    f"registry row {REG_ROW} @0x{REG_ROW_ADDR:08X} is "
                    f"(0x{cur[0]:08X}, 0x{cur[1]:04X}), expected "
                    f"(0x{REG_ROW_ORIG[0]:08X}, 0x{REG_ROW_ORIG[1]:04X}) -- "
                    f"another patch may have claimed it")
            struct.pack_into("<II", ov, _off(REG_ROW_ADDR), BUSHIDO_THUNK, DONOR_CID)
            print(f"  PART A: registry row {REG_ROW} @0x{REG_ROW_ADDR:08X}  "
                  f"(0x{REG_ROW_ORIG[0]:08X}, 0x{REG_ROW_ORIG[1]:04X}) -> "
                  f"(0x{BUSHIDO_THUNK:08X}, 0x{DONOR_CID:04X})")


        # ===========================================================================
        # PART B
        # ===========================================================================
        def apply_arm_hook(ov: bytearray) -> None:
            """Retarget the third arm call into the dead-code stub."""
            have = bytes(ov[_off(DOJO_BLOCK):_off(DOJO_BLOCK) + len(DOJO_BLOCK_ORIG)])
            stub = build_arm_stub(DOJO_BLOCK)
            if have.startswith(stub):
                print(f"  PART B: stub already present at 0x{DOJO_BLOCK:08X} -- skipping")
            else:
                if have != DOJO_BLOCK_ORIG:
                    raise RuntimeError(
                        f"dead block 0x{DOJO_BLOCK:08X} does not hold its expected "
                        f"original bytes -- another patch may have claimed it")
                ov[_off(DOJO_BLOCK):_off(DOJO_BLOCK) + len(stub)] = stub
                print(f"  PART B: {len(stub)} B arm stub -> 0x{DOJO_BLOCK:08X} "
                      f"(dead leaf of phantom cid 0x{DOJO_PHANTOM_CID:04X})")

            new_bl = _thumb_bl_bytes(ARM_BL_SITE, DOJO_BLOCK)
            old_bl = _thumb_bl_bytes(ARM_BL_SITE, ARM_PRIM)
            cur = bytes(ov[_off(ARM_BL_SITE):_off(ARM_BL_SITE) + 4])
            if cur == new_bl:
                print(f"  PART B: arm BL @0x{ARM_BL_SITE:08X} already retargeted")
                return
            if cur != old_bl:
                raise RuntimeError(
                    f"BL @0x{ARM_BL_SITE:08X} is {cur.hex()}, expected {old_bl.hex()} "
                    f"(-> 0x{ARM_PRIM:08X})")
            ov[_off(ARM_BL_SITE):_off(ARM_BL_SITE) + 4] = new_bl
            print(f"  PART B: BL @0x{ARM_BL_SITE:08X}  0x{ARM_PRIM:08X} -> "
                  f"0x{DOJO_BLOCK:08X}")


        def build_capacity_stub(base: int) -> bytes:
            """Give the donor an uncapped type-6 (Bushido) counter capacity.

            Entered by ``BL`` from the head of the type-6 arm, with R0 = the cid of the
            card in the zone.  Two exits:

              * donor  -> R0 = 0xFF and the *enclosing function's* epilogue is run here
                          (``POP {R3,R4,R5,PC}``); the stack still holds 0x021A2F10's
                          frame because a BL pushes nothing.
              * other  -> re-execute the displaced ``LDR R1,=0x1D22`` / ``CMP R0,R1`` and
                          ``BX LR`` back to the BNE at 0x021A2FA2, which consumes the
                          flags this CMP just set (BX does not disturb them).

            Clobbering LR is safe: 0x021A2F10 opens with ``PUSH {R3,R4,R5,LR}``.
            """
            a = EffectBuilder()
            (a
             .ldr_const(1, DONOR_CID)                 # r1 = 0x19B2
             .insn("CMP", "R0, R1")
             .insn("BNE", "not_us")
             .insn("MOV", f"R0, #0x{DOJO_CAPACITY:X}")
             .insn("POP", "{R3, R4, R5, PC}")         # return capacity from 0x021A2F10
             .label("not_us")
             .ldr_const(1, CAP_FIRST_CID)             # the displaced LDR's value
             .insn("CMP", "R0, R1")                   # the displaced CMP
             .insn("BX", "LR"))                       # -> 0x021A2FA2 (the BNE)
            blob = a.assemble(base)
            assert_thumb1_only(blob, base)
            if len(blob) > CAP_BLOCK_FREE:
                raise RuntimeError(
                    f"capacity stub is {len(blob)} B, only {CAP_BLOCK_FREE} B are free "
                    f"at 0x{base:08X}")
            return blob


        # ===========================================================================
        # PART E
        # ===========================================================================
        def apply_capacity_hook(ov: bytearray) -> None:
            """Displace the type-6 chain head into the capacity stub."""
            stub = build_capacity_stub(CAP_BLOCK)
            have = bytes(ov[_off(CAP_BLOCK):_off(CAP_BLOCK) + len(stub)])
            if have == stub:
                print(f"  PART E: capacity stub already present at 0x{CAP_BLOCK:08X}")
            else:
                cur = bytes(ov[_off(CAP_BLOCK):_off(CAP_BLOCK) + len(CAP_BLOCK_ORIG)])
                if cur != CAP_BLOCK_ORIG:
                    raise RuntimeError(
                        f"dead block 0x{CAP_BLOCK:08X} does not hold its expected "
                        f"original bytes -- another patch may have claimed it")
                ov[_off(CAP_BLOCK):_off(CAP_BLOCK) + len(stub)] = stub
                print(f"  PART E: {len(stub)} B capacity stub -> 0x{CAP_BLOCK:08X} "
                      f"(dead leaf of phantom cid 0x{CAP_PHANTOM_CID:04X})")

            new_bl = _thumb_bl_bytes(CAP_LEAF, CAP_BLOCK)
            cur = bytes(ov[_off(CAP_LEAF):_off(CAP_LEAF) + 4])
            if cur == new_bl:
                print(f"  PART E: capacity hook @0x{CAP_LEAF:08X} already installed")
                return
            if cur != CAP_LEAF_ORIG:
                raise RuntimeError(
                    f"type-6 capacity chain head @0x{CAP_LEAF:08X} is {cur.hex()}, "
                    f"expected {CAP_LEAF_ORIG.hex()}")
            ov[_off(CAP_LEAF):_off(CAP_LEAF) + 4] = new_bl
            print(f"  PART E: BL @0x{CAP_LEAF:08X} -> 0x{CAP_BLOCK:08X} "
                  f"(donor Bushido capacity = 0x{DOJO_CAPACITY:02X})")


        # ===========================================================================
        # PART D
        # ===========================================================================
        def apply_kill_native_accrual(ov: bytearray) -> None:
            """Repoint the native counter-accrual cid literal at a dead cid."""
            cur = struct.unpack_from("<I", ov, _off(ACCRUAL_POOL))[0]
            if cur == DEAD_CID:
                print(f"  PART D: accrual literal already neutralised -- skipping")
                return
            if cur != DONOR_CID:
                raise RuntimeError(
                    f"accrual literal @0x{ACCRUAL_POOL:08X} is 0x{cur:04X}, "
                    f"expected the donor cid 0x{DONOR_CID:04X}")
            struct.pack_into("<I", ov, _off(ACCRUAL_POOL), DEAD_CID)
            print(f"  PART D: accrual literal @0x{ACCRUAL_POOL:08X}  "
                  f"0x{DONOR_CID:04X} -> 0x{DEAD_CID:04X} (native type-1 counter killed)")


        # ===========================================================================
        # PART F
        # ===========================================================================
        def apply_retire_donor_effects(ov: bytearray) -> None:
            """Retire the donor's remaining Ancient Gear Castle behaviour."""
            for pool in RESIDUAL_POOLS:
                cur = struct.unpack_from("<I", ov, _off(pool))[0]
                if cur == DEAD_CID:
                    continue
                if cur != DONOR_CID:
                    raise RuntimeError(
                        f"residual literal @0x{pool:08X} is 0x{cur:04X}, expected the "
                        f"donor cid 0x{DONOR_CID:04X}")
                struct.pack_into("<I", ov, _off(pool), DEAD_CID)
            print(f"  PART F: {len(RESIDUAL_POOLS)} residual literals -> 0x{DEAD_CID:04X} "
                  f"(Tribute-substitution retired)")

            cur = struct.unpack_from("<H", ov, _off(ATK_ARM_BEQ))[0]
            if cur == THUMB_NOP:
                print(f"  PART F: +300 ATK leaf dispatch already NOP'd")
                return
            if cur != ATK_ARM_BEQ_ORIG:
                raise RuntimeError(
                    f"stat-engine arm @0x{ATK_ARM_BEQ:08X} is 0x{cur:04X}, expected "
                    f"0x{ATK_ARM_BEQ_ORIG:04X} (BEQ)")
            struct.pack_into("<H", ov, _off(ATK_ARM_BEQ), THUMB_NOP)
            print(f"  PART F: BEQ @0x{ATK_ARM_BEQ:08X} -> NOP "
                  f"(+300 ATK to Ancient Gear monsters retired; chain shape intact)")


        def build_setcode_or_stub(base: int) -> bytes:
            """Per-candidate predicate: set code 0x1E (Six Samurai) OR 0x4F (Shien).

            Drop-in for the engine's 0x0223C825.  It must read its argument from
            ``[sp,#0]`` **before** pushing anything, because that slot belongs to the
            worker's frame and any push would shift SP out from under it.
            """
            a = EffectBuilder()
            (a
             .insn("LDR", "R0, [SP, #0x0]")          # -> the candidate record
             .insn("LDR", "R0, [R0, #0x0]")
             .insn("LSL", "R0, R0, #18")             # keep the low 14 bits = the cid
             .insn("LSR", "R0, R0, #18")
             .insn("PUSH", "{R4, LR}")
             .insn("ADD", "R4, R0, #0x0")            # r4 = cid
             .insn("MOV", f"R1, #0x{SETCODE_SIX_SAMURAI:X}")
             .ldr_const(3, HAS_SET_CODE)
             .insn("BLX", "R3")
             .insn("CMP", "R0, #0x0")
             .insn("BNE", "yes")                     # already a Six Samurai
             .insn("ADD", "R0, R4, #0x0")
             .insn("MOV", f"R1, #0x{SETCODE_SHIEN:X}")
             .ldr_const(3, HAS_SET_CODE)
             .insn("BLX", "R3")
             .label("yes")
             .insn("POP", "{R4, PC}"))
            blob = a.assemble(base)
            assert_thumb1_only(blob, base)
            if len(blob) > 0x40:
                raise RuntimeError(f"set-code OR stub is {len(blob)} B, reserve is 0x40")
            return blob


        def build_criteria_handler(base: int, callback: int) -> bytes:
            """Clone of the generic criteria handler 0x0223CAB4, using *callback*.

            Identical stack shape: PUSH {R1,R2,R3,LR} reserves the three outgoing stack
            words, which are then filled with {flags, 0xA, filter} while R3 points at the
            filter slot.  The row's +0x02 is non-negative here (0x001E), so a plain LDRH
            is equivalent to the original's register-offset LDSH.
            """
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R1, R2, R3, LR}")
             .insn("ADD", "R2, R0, #0x0")            # r2 = the criteria row
             .insn("LDRH", "R0, [R2, #0x2]")         # filter (set code)
             .insn("ADD", "R3, SP, #0x8")
             .insn("STR", "R0, [SP, #0x8]")
             .insn("LDR", "R0, [R2, #0x8]")          # flags
             .insn("STR", "R0, [SP, #0x0]")
             .insn("MOV", "R0, #0xA")
             .insn("STR", "R0, [SP, #0x4]")
             .insn("ADD", "R0, R1, #0x0")            # r0 = ctx
             .insn("LDRH", "R1, [R2, #0x0]")         # r1 = cid
             .ldr_const(2, callback | 1)             # r2 = OUR predicate
             .bl(CRIT_WORKER)
             .insn("POP", "{R1, R2, R3, PC}"))
            blob = a.assemble(base)
            assert_thumb1_only(blob, base)
            if len(blob) > 0x40:
                raise RuntimeError(f"criteria handler is {len(blob)} B, reserve is 0x40")
            return blob


        def build_level_stub(base: int, extra_addr: int = CRIT_EXTRA_ADDR) -> bytes:
            """Write `0x80 | (min(N,12) << 2)` into the criteria row's Level-bound byte.

            Entered as the donor's cls3 ``+0C`` activation condition with R0 = the effect
            descriptor (``+2`` = side, ``+3`` = zone, exactly as the native condition
            0x021FD488 reads it).  Returns whatever the native condition returns, so the
            "do I hold at least one Bushido Counter?" gate is preserved verbatim.
            """
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, LR}")
             .insn("ADD", "R4, R0, #0x0")            # r4 = descriptor
             .insn("LDRB", "R0, [R4, #0x2]")         # side
             .insn("LDRB", "R1, [R4, #0x3]")         # zone
             .insn("MOV", "R2, #0x6")                # Bushido
             .bl(COUNTER_COUNT)                      # r0 = N
             .insn("CMP", f"R0, #0x{MAX_LEVEL:X}")
             .insn("BLE", "clamped")
             .insn("MOV", f"R0, #0x{MAX_LEVEL:X}")
             .label("clamped")
             .insn("LSL", "R0, R0, #2")              # N << 2
             .insn("ADD", "R0, #0x80")               # 0x80 | (N << 2)
             .ldr_const(1, extra_addr)               # the RESOLVED row's bound byte -- crit_row(),
                                                     # never the stock index: a shifted table would
                                                     # make this write into a neighbouring card's row
             .insn("STRB", "R0, [R1, #0x0]")         # patch the row's bound byte
             .insn("ADD", "R0, R4, #0x0")            # r0 = descriptor again
             .ldr_const(3, NATIVE_COND)
             .insn("BLX", "R3")                      # tail-call the native condition
             .insn("POP", "{R4, PC}"))
            blob = a.assemble(base)
            assert_thumb1_only(blob, base)
            if len(blob) > 0x40:
                raise RuntimeError(f"level stub is {len(blob)} B, reserve is 0x40")
            return blob


        # ===========================================================================
        # PART G
        # ===========================================================================
        def _cls3_cids(ov: bytes) -> list[int]:
            return [struct.unpack_from("<I", ov, _off(CLS3_BASE + i * CLS3_STRIDE))[0]
                    for i in range(CLS3_COUNT)]


        def apply_clause2(ov: bytearray, ov3: bool = False) -> None:
            """Clause 2: the cls3 record + the criteria-registry row."""
            lvl, _, crit = _addrs(ov3)
            # ---- G1: the cls3 record (count-neutral: drop a phantom, shift, insert) --
            cids = _cls3_cids(ov)
            if DONOR_CID in cids:
                print(f"  PART G1: cls3 record for 0x{DONOR_CID:04X} already present")
            else:
                if cids[CLS3_DROP_ROW] != CLS3_DROP_CID:
                    raise RuntimeError(
                        f"cls3 row {CLS3_DROP_ROW} is 0x{cids[CLS3_DROP_ROW]:04X}, "
                        f"expected phantom 0x{CLS3_DROP_CID:04X}")
                united = bytes(ov[_off(CLS3_BASE + UNITED_CLS3_ROW * CLS3_STRIDE):
                                  _off(CLS3_BASE + UNITED_CLS3_ROW * CLS3_STRIDE) + CLS3_STRIDE])
                if struct.unpack_from("<I", united, 0)[0] != 0x1D22:
                    raise RuntimeError("Six Samurai United is not at cls3[370]")
                # clone United's wrapper, swap cid and the resolution slot
                row = bytearray(united)
                struct.pack_into("<I", row, 0x00, DONOR_CID)
                struct.pack_into("<I", row, 0x04, DECK_SS_RESOLVER)
                # PART H: +0C = our Level-bound writer, which tail-calls NATIVE_COND
                struct.pack_into("<I", row, 0x0C, lvl | 1)

                lo = _off(CLS3_BASE + (CLS3_DROP_ROW + 1) * CLS3_STRIDE)
                hi = _off(CLS3_BASE + (CLS3_INSERT_ROW + 1) * CLS3_STRIDE)
                block = bytes(ov[lo:hi])                       # rows 224..233
                ov[lo - CLS3_STRIDE:hi - CLS3_STRIDE] = block   # shift down one slot
                at = _off(CLS3_BASE + CLS3_INSERT_ROW * CLS3_STRIDE)
                ov[at:at + CLS3_STRIDE] = bytes(row)

                after = _cls3_cids(ov)
                if not all(after[i] <= after[i + 1] for i in range(CLS3_COUNT - 1)):
                    raise RuntimeError("cls3 is no longer sorted after the insert")
                print(f"  PART G1: cls3[{CLS3_INSERT_ROW}] = 0x{DONOR_CID:04X} "
                      f"(dropped phantom 0x{CLS3_DROP_CID:04X} @row {CLS3_DROP_ROW}; "
                      f"count stays {CLS3_COUNT})")

            # ---- G2: the criteria-registry row (straight over a phantom) ------------
            row = crit_row(ov)                      # BY CID -- other patches shift this table
            base = _off(CRIT_BASE + row * CRIT_STRIDE)
            cur = struct.unpack_from("<H", ov, base)[0]
            if cur == DONOR_CID:
                print(f"  PART G2: criteria row {row} already claimed")
                return
            if row != CRIT_ROW:
                print(f"  PART G2: criteria row moved {CRIT_ROW} -> {row} by an earlier "
                      f"patch's count-neutral insert (located by phantom cid, not index)")
            struct.pack_into("<H", ov, base + 0x00, DONOR_CID)
            struct.pack_into("<H", ov, base + 0x02, SIX_SAMURAI_SETCODE)
            struct.pack_into("<I", ov, base + 0x04, crit | 1)
            struct.pack_into("<H", ov, base + 0x08, CRIT_FLAGS)
            struct.pack_into("<H", ov, base + 0x0A, CRIT_EXTRA)

            keys = [struct.unpack_from("<H", ov, _off(CRIT_BASE + i * CRIT_STRIDE))[0]
                    for i in range(CRIT_COUNT)]
            if not all(keys[i] <= keys[i + 1] for i in range(CRIT_COUNT - 1)):
                raise RuntimeError("criteria registry is no longer sorted")
            print(f"  PART G2: criteria row {row} = "
                  f"{{0x{DONOR_CID:04X}, setcode 0x{SIX_SAMURAI_SETCODE:04X}, "
                  f"0x{crit | 1:08X}, 0x{CRIT_FLAGS:04X}, "
                  f"0x{CRIT_EXTRA:04X} = Level <= {CRIT_LEVEL_CAP}}}")


        # ===========================================================================
        # PART C
        # ===========================================================================
        def apply_text(out_path: str) -> None:
            """Write the name/description in place (card_prop is left untouched)."""
            rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
            pac_path = next((p for p in iter_paths(rom.filenames)
                             if p.lower().endswith("bin2.pac")), None)
            if pac_path is None:
                raise RuntimeError("bin2.pac not found in ROM")
            fid = rom.filenames.idOf(pac_path)
            orig_pac = bytes(rom.files[fid])
            archive = parse_pac(orig_pac, pac_path)

            def _orig(f) -> bytes:
                return orig_pac[f.address:f.address + f.size]

            cpf = next(f for f in archive.files
                       if f.get_clean_name().lower() == "card_prop.bin")
            cp = _orig(cpf)
            entry_count = (cpf.size - 8) // 8
            card_index = None
            for i in range(entry_count):
                val = int.from_bytes(cp[8 + i * 8:16 + i * 8], "little")
                if (val & ((1 << 14) - 1)) == DONOR_CID:
                    card_index = i
                    break
            if card_index is None:
                raise RuntimeError(f"card_id 0x{DONOR_CID:04X} not found in card_prop.bin")

            modified: dict = {}
            for L in LANGS:
                idxf = next((f for f in archive.files
                             if f.get_clean_name().lower() == f"card_indx_{L}.bin"), None)
                namef = next((f for f in archive.files
                              if f.get_clean_name().lower() == f"card_name_{L}.bin"), None)
                descf = next((f for f in archive.files
                              if f.get_clean_name().lower() == f"card_desc_{L}.bin"), None)
                if not (idxf and namef and descf):
                    print(f"  [{L}] missing name/desc/index file -> skipped")
                    continue

                name_blob = bytearray(modified.get(namef.address, _orig(namef)))
                desc_blob = bytearray(modified.get(descf.address, _orig(descf)))
                idx_buf = bytes(modified.get(idxf.address, _orig(idxf)))

                rec = 8 + card_index * 8
                name_off, desc_off = struct.unpack_from("<II", idx_buf, rec)
                old_name = read_cstr(bytes(name_blob), name_off)
                old_desc = read_cstr(bytes(desc_blob), desc_off)

                if len(NEW_NAME) <= len(old_name):
                    name_blob[name_off:name_off + len(NEW_NAME)] = NEW_NAME
                    name_blob[name_off + len(NEW_NAME)] = 0
                    nnote = f"in-place ({len(NEW_NAME)}/{len(old_name)}B)"
                else:
                    nnote = f"SKIPPED (need {len(NEW_NAME)}B > {len(old_name)}B)"

                if len(NEW_DESC) <= len(old_desc):
                    desc_blob[desc_off:desc_off + len(NEW_DESC)] = NEW_DESC
                    desc_blob[desc_off + len(NEW_DESC)] = 0
                    dnote = f"in-place ({len(NEW_DESC)}/{len(old_desc)}B)"
                else:
                    dnote = f"SKIPPED (need {len(NEW_DESC)}B > {len(old_desc)}B)"

                modified[namef.address] = bytes(name_blob)
                modified[descf.address] = bytes(desc_blob)
                print(f"  [{L}] name {nnote}; desc {dnote}")

            rom.files[fid] = rebuild_v1_pac(orig_pac, archive, modified)
            rom.saveToFile(out_path)
            print(f"  PART C: wrote name/desc -> {out_path}")

        def build_level_stub3(base: int) -> bytes:
            """build_level_stub, but the donor's criteria row is FOUND BY CID AT RUNTIME (ov3 placement).

            The ov5 stub bakes crit_row()'s bound-byte address at Dojo's chain step; later steps' count-neutral
            criteria inserts move the row (chain f1c24d39: baked 0x02272706 = row 410 = cid 0x19DC, donor row is
            402), so the shipped chain writes the bound into 0x19DC's row. A cid scan cannot go stale.

            It also no longer tail-calls NATIVE_COND: that is Six Samurai United's condition, which ends in the
            can-draw-N check 0x021BAE30(side, N) -- Dojo was hidden whenever counters > cards in Deck (proven
            on rom_elder_dojo_pineapple_heirloom_ov3.ml2, 2026-10-08). Kept: N >= 1 and United's other gate
            0x021B0BC4(side, zone)."""
            src = f"""
                push    {{r4, r5, lr}}
                adds    r4, r0, #0
                ldrb    r0, [r4, #2]
                ldrb    r1, [r4, #3]
                movs    r2, #6
                ldr     r3, ={COUNTER_COUNT | 1:#x}
                blx     r3
                cmp     r0, #0
                beq     fail                ; no Bushido Counter: not offered
                cmp     r0, #{MAX_LEVEL}
                ble     clamped
                movs    r0, #{MAX_LEVEL}
              clamped:
                lsls    r0, r0, #2
                adds    r0, #0x80
                ldr     r1, ={CRIT_BASE:#x}
                ldr     r2, ={DONOR_CID:#x}
                ldr     r3, ={CRIT_BASE + CRIT_COUNT * CRIT_STRIDE:#x}
              find:
                cmp     r1, r3
                bge     native              ; past the table: cid absent, write nothing
                ldrh    r5, [r1, #0]
                cmp     r5, r2
                beq     hit
                adds    r1, #{CRIT_STRIDE}
                b       find
              hit:
                strb    r0, [r1, #0xA]
              native:
                ldrb    r0, [r4, #2]
                ldrb    r1, [r4, #3]
                ldr     r3, ={UNITED_GATE2:#x}
                blx     r3
                cmp     r0, #0
                beq     fail
                movs    r0, #1
                pop     {{r4, r5, pc}}
              fail:
                movs    r0, #0
                pop     {{r4, r5, pc}}
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x3]")
            b.call_addr(COUNTER_COUNT, R0, R1, 6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "fail")
            b.insn("CMP", f"R0, #0x{MAX_LEVEL:X}")
            b.insn("BLE", "clamped")
            b.insn("MOV", f"R0, #0x{MAX_LEVEL:X}")
            b.label("clamped")
            b.insn("LSL", "R0, R0, #0x2")
            b.insn("ADD", "R0, #0x80")
            b.ldr_const(1, CRIT_BASE)
            b.ldr_const(2, DONOR_CID)
            b.ldr_const(3, CRIT_BASE + CRIT_COUNT * CRIT_STRIDE)
            b.label("find")
            b.insn("CMP", "R1, R3")
            b.insn("BGE", "native")
            b.insn("LDRH", "R5, [R1, #0x0]")
            b.insn("CMP", "R5, R2")
            b.insn("BEQ", "hit")
            b.insn("ADD", f"R1, #0x{CRIT_STRIDE:X}")
            b.insn("B", "find")
            b.label("hit")
            b.insn("STRB", "R0, [R1, #0xA]")
            b.label("native")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.insn("LDRB", "R1, [R4, #0x3]")
            b.call_addr(UNITED_GATE2, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "fail")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, PC}")
            b.label("fail")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return cave3._checked(base, 0x60, b.assemble(base, pad="nop"), src)


        UNITED_GATE2 = 0x021B0BC5   # 0x021B0BC4(side, zone): United's cond's 2nd gate (thunk, r2 = 0xE)


        def _stub_blobs(extra_addr: int, ov3: bool) -> list[tuple[int, bytes]]:
            """[(addr, blob)] of the PART H/I stubs for the ov5 or ov3 placement."""
            lvl, cb, crit = _addrs(ov3)
            return [(lvl, build_level_stub3(lvl) if ov3 else build_level_stub(lvl, extra_addr)),
                    (cb, build_setcode_or_stub(cb)), (crit, build_criteria_handler(crit, cb))]

        def install(rom, view):
            ov = view.buf
            apply_registry_row(ov)          # PART A
            apply_arm_hook(ov)              # PART B
            apply_kill_native_accrual(ov)   # PART D
            apply_capacity_hook(ov)         # PART E
            apply_retire_donor_effects(ov)  # PART F
            apply_clause2(ov, True)         # PART G
            # The row the stub will write to at activation time -- resolved from the ROM just built, NOT the stock index.
            extra_addr = CRIT_BASE + crit_row(ov) * CRIT_STRIDE + 0x0A
            for addr, blob in _stub_blobs(extra_addr, True):     # PARTS H + I in the ov3 pool
                cave3.put(ov, addr, blob)
                print(f"  PART H/I: {len(blob)} B stub -> ov3 pool 0x{addr:08X}")

        def check_fn(c, rom, view):
            _rom, ov = rom, view.buf

            def print(*a):      # the original verify prints PASS/FAIL lines; route them into the checker
                s = " ".join(str(x) for x in a)
                if s.startswith("PASS"):
                    c.ok(True, s)
                elif s.startswith("FAIL"):
                    c.ok(False, s)

            # --- PART A: the claimed registry row -----------------------------------
            row = struct.unpack_from("<II", ov, _off(REG_ROW_ADDR))
            if row == (BUSHIDO_THUNK, DONOR_CID):
                print(f"PASS registry row {REG_ROW} = (0x{row[0]:08X}, 0x{row[1]:04X})")
            else:
                print(f"FAIL registry row {REG_ROW} = (0x{row[0]:08X}, 0x{row[1]:08X})")
                ok = False

            # the row must use the SAME thunk Six Samurai United's row uses
            united = struct.unpack_from("<II", ov, _off(REG_BASE + UNITED_ROW * 8))
            if united[1] == 0x1D22 and united[0] == BUSHIDO_THUNK:
                print(f"PASS United's row {UNITED_ROW} intact -> same thunk "
                      f"0x{BUSHIDO_THUNK:08X}")
            else:
                print(f"FAIL United's row {UNITED_ROW} = "
                      f"(0x{united[0]:08X}, 0x{united[1]:04X})")
                ok = False

            # count-neutrality: the two walkers' hard-coded counts must still be 0xB5
            for name, addr in (("A", WALKER_A_COUNT_IMM), ("B", WALKER_B_COUNT_IMM)):
                hw = struct.unpack_from("<H", ov, _off(addr))[0]
                if hw & 0xFF == REG_COUNT and (hw >> 11) == 0b00101:
                    print(f"PASS walker {name} count immediate still #{REG_COUNT:#x}")
                else:
                    print(f"FAIL walker {name} @0x{addr:08X} = 0x{hw:04X}")
                    ok = False

            # no other row may claim the donor cid (single-claim guard)
            dupes = [i for i in range(REG_COUNT)
                     if struct.unpack_from("<I", ov, _off(REG_BASE + i * 8 + 4))[0] == DONOR_CID]
            if dupes == [REG_ROW]:
                print(f"PASS donor cid 0x{DONOR_CID:04X} claims exactly one row")
            else:
                print(f"FAIL donor cid claimed by rows {dupes}")
                ok = False

            # --- PART B: the stub and the retargeted BL -----------------------------
            stub = build_arm_stub(DOJO_BLOCK)
            have = bytes(ov[_off(DOJO_BLOCK):_off(DOJO_BLOCK) + len(stub)])
            if have == stub:
                print(f"PASS arm stub ({len(stub)} B) present at 0x{DOJO_BLOCK:08X}")
            else:
                print(f"FAIL arm stub mismatch at 0x{DOJO_BLOCK:08X}: {have.hex()}")
                ok = False

            want_bl = _thumb_bl_bytes(ARM_BL_SITE, DOJO_BLOCK)
            have_bl = bytes(ov[_off(ARM_BL_SITE):_off(ARM_BL_SITE) + 4])
            if have_bl == want_bl:
                print(f"PASS arm BL @0x{ARM_BL_SITE:08X} -> 0x{DOJO_BLOCK:08X}")
            else:
                print(f"FAIL arm BL @0x{ARM_BL_SITE:08X} = {have_bl.hex()}")
                ok = False

            # the first two arm calls (United, Gateway) must be untouched
            for label, site, cid in (("United", 0x02266BD0, 0x1D22),
                                     ("Gateway", 0x02266BD6, 0x219A)):
                have = bytes(ov[_off(site):_off(site) + 4])
                if have == _thumb_bl_bytes(site, ARM_PRIM):
                    print(f"PASS {label} arm BL @0x{site:08X} untouched")
                else:
                    print(f"FAIL {label} arm BL @0x{site:08X} = {have.hex()}")
                    ok = False

            # --- PART D: the native accrual is dead ---------------------------------
            lit = struct.unpack_from("<I", ov, _off(ACCRUAL_POOL))[0]
            if lit == DEAD_CID:
                print(f"PASS native accrual literal @0x{ACCRUAL_POOL:08X} = "
                      f"0x{DEAD_CID:04X} (dead)")
            else:
                print(f"FAIL native accrual literal @0x{ACCRUAL_POOL:08X} = 0x{lit:04X}")
                ok = False

            # --- PART E: the capacity hook ------------------------------------------
            cstub = build_capacity_stub(CAP_BLOCK)
            have = bytes(ov[_off(CAP_BLOCK):_off(CAP_BLOCK) + len(cstub)])
            if have == cstub:
                print(f"PASS capacity stub ({len(cstub)} B) present at 0x{CAP_BLOCK:08X}")
            else:
                print(f"FAIL capacity stub mismatch at 0x{CAP_BLOCK:08X}: {have.hex()}")
                ok = False

            want = _thumb_bl_bytes(CAP_LEAF, CAP_BLOCK)
            have = bytes(ov[_off(CAP_LEAF):_off(CAP_LEAF) + 4])
            if have == want:
                print(f"PASS capacity hook @0x{CAP_LEAF:08X} -> 0x{CAP_BLOCK:08X}")
            else:
                print(f"FAIL capacity hook @0x{CAP_LEAF:08X} = {have.hex()}")
                ok = False

            # the other three Bushido capacities must be untouched
            for label, addr, want_imm in (("United", 0x021A2FA4, 0x02),
                                          ("Gateway", 0x021A2FAE, 0xFF),
                                          ("Temple", 0x021A2FB8, 0xFF)):
                hw = struct.unpack_from("<H", ov, _off(addr))[0]
                if (hw >> 11) == 0b00100 and ((hw >> 8) & 7) == 0 and (hw & 0xFF) == want_imm:
                    print(f"PASS {label} Bushido capacity still #{want_imm:#04x}")
                else:
                    print(f"FAIL {label} capacity @0x{addr:08X} = 0x{hw:04X}")
                    ok = False

            # --- PART F: the donor's own effects are retired ------------------------
            live = [p for p in RESIDUAL_POOLS
                    if struct.unpack_from("<I", ov, _off(p))[0] != DEAD_CID]
            if not live:
                print(f"PASS all {len(RESIDUAL_POOLS)} residual literals retired")
            else:
                print(f"FAIL residual literals still live: "
                      f"{[f'0x{p:08X}' for p in live]}")
                ok = False

            hw = struct.unpack_from("<H", ov, _off(ATK_ARM_BEQ))[0]
            if hw == THUMB_NOP:
                print(f"PASS +300 ATK leaf dispatch NOP'd @0x{ATK_ARM_BEQ:08X}")
            else:
                print(f"FAIL stat-engine arm @0x{ATK_ARM_BEQ:08X} = 0x{hw:04X}")
                ok = False

            # the ordered chain itself must be untouched: the cid literal and the
            # surrounding compare/exit must still be exactly as shipped
            if (struct.unpack_from("<I", ov, _off(0x021B34D8))[0] == DONOR_CID
                    and struct.unpack_from("<H", ov, _off(0x021B3292))[0] == 0x4284
                    and struct.unpack_from("<H", ov, _off(0x021B3296))[0] == 0xE162):
                print("PASS stat-engine sorted chain shape intact (literal + CMP + exit)")
            else:
                print("FAIL stat-engine chain shape disturbed")
                ok = False

            # --- PART G: clause 2 ----------------------------------------------------
            cids = _cls3_cids(bytes(ov))
            hits = [i for i, c in enumerate(cids) if c == DONOR_CID]
            if len(hits) == 1:           # row index shifts when later count-neutral inserts drop phantoms before it
                b = _off(CLS3_BASE + hits[0] * CLS3_STRIDE)
                slots = struct.unpack_from("<5I", ov, b + 4)
                on3 = slots[2] == LVL3 | 1          # which placement this ROM was built with
                want = (DECK_SS_RESOLVER, 0, _addrs(on3)[0] | 1, 0x021E6FF5, 0)
                if slots == want:
                    print(f"PASS cls3[{CLS3_INSERT_ROW}] = 0x{DONOR_CID:04X} with the "
                          f"deck-SS wrapper")
                else:
                    print(f"FAIL cls3 slots = {[hex(x) for x in slots]}")
                    ok = False
            else:
                print(f"FAIL donor cls3 rows = {hits}")
                ok = False

            if len(cids) == CLS3_COUNT and all(cids[i] <= cids[i + 1]
                                               for i in range(len(cids) - 1)):
                print(f"PASS cls3 still {CLS3_COUNT} rows and sorted (count-neutral)")
            else:
                print("FAIL cls3 count/sort broken")
                ok = False
            if CLS3_DROP_CID in cids:
                print(f"FAIL dropped phantom 0x{CLS3_DROP_CID:04X} still present")
                ok = False

            # ⚠️ LOCATE BY CID, NEVER BY CRIT_ROW. The criteria registry is shared and a
            # LATER patch in the combined chain can shift this row: gates_of_dark_world
            # drops two phantom rows below it and inserts higher up, moving this record from
            # 409 to 407. The row CONTENT is what matters, and it is checked in full below.
            # (PART G2's apply may still index by CRIT_ROW -- it asserts the phantom cid
            # first, so a shift there aborts loudly instead of corrupting.)
            _cids = [struct.unpack_from("<H", ov, _off(CRIT_BASE) + i * CRIT_STRIDE)[0]
                     for i in range(CRIT_COUNT)]
            _hits = [i for i, c in enumerate(_cids) if c == DONOR_CID]
            if len(_hits) != 1:
                print(f"FAIL criteria rows for 0x{DONOR_CID:04X}: {_hits} (expected exactly 1)")
                ok = False
            else:
                _at = _hits[0]
                b = _off(CRIT_BASE + _at * CRIT_STRIDE)
                row = (struct.unpack_from("<H", ov, b)[0],
                       struct.unpack_from("<H", ov, b + 2)[0],
                       struct.unpack_from("<I", ov, b + 4)[0],
                       struct.unpack_from("<H", ov, b + 8)[0],
                       struct.unpack_from("<H", ov, b + 10)[0])
                on3 = row[2] == CRIT3 | 1
                if row == (DONOR_CID, SIX_SAMURAI_SETCODE, _addrs(on3)[2] | 1, CRIT_FLAGS, CRIT_EXTRA):
                    print(f"PASS criteria row {_at} = set code 0x1E, "
                          f"Level <= {CRIT_LEVEL_CAP}"
                          f"{'' if _at == CRIT_ROW else f' [base-ROM index was {CRIT_ROW}]'}")
                else:
                    print(f"FAIL criteria row = {[hex(x) for x in row]}")
                    ok = False
                # PARTS H + I: the three stubs, at the home the live pointers name (ov5 or ov3)
                for addr, blob in _stub_blobs(CRIT_BASE + _at * CRIT_STRIDE + 0x0A, on3):
                    if cave3.read_code(_rom, ov, addr, len(blob)) == blob:
                        print(f"PASS {'ov3' if on3 else 'ov5'} stub @0x{addr:08X} ({len(blob)} B)")
                    else:
                        print(f"FAIL stub bytes @0x{addr:08X}")
                        ok = False

            keys = [struct.unpack_from("<H", ov, _off(CRIT_BASE + i * CRIT_STRIDE))[0]
                    for i in range(CRIT_COUNT)]
            if all(keys[i] <= keys[i + 1] for i in range(len(keys) - 1)):
                print("PASS criteria registry still sorted (count-neutral)")
            else:
                print("FAIL criteria registry sort broken")
                ok = False

            # Footsoldier's row is our structural template -- it must be untouched
            fi = keys.index(0x1B3A)
            fb = _off(CRIT_BASE + fi * CRIT_STRIDE)
            if (struct.unpack_from("<H", ov, fb + 2)[0] == 0x001E
                    and struct.unpack_from("<H", ov, fb + 10)[0] == 0x008C):
                print("PASS Shien's Footsoldier criteria row intact")
            else:
                print("FAIL Footsoldier criteria row disturbed")
                ok = False


        return Compiled(installs=(install,), posts=(apply_text,), checks=(check_fn,))


dojo_effects = each_six_samurai_summon_place_bushido_counter_send_to_graveyard_special_summon_six_samurai_or_shien_level_4_or_lower_from_deck

SPEC = card(0x19B2, dojo_effects())

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_shiens_dojo.nds")

# Name other modules read.
DONOR_CID = 0x19B2          # Ancient Gear Castle
CLS3_DROP_ROW = 223             # phantom cid 0x1941 dropped from cls3 (read by KB dispatch.cls3_rows_anchored_by_index)
CLS3_INSERT_ROW = 233           # lands between 0x19A9 and 0x19BB
UNITED_CLS3_ROW = 370           # the record the wrapper slots are cloned from

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
