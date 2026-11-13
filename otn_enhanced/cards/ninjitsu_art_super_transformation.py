"""Ninjitsu Art of Super-Transformation (Continuous Trap) on Goblin Fan 0x1255.

See notes/ninjitsu-art-super-transformation-findings.md and card_text.CARD_TEXT[0x1255] for the printed text: target 1 "Ninja"
you control and 1 face-up opponent monster, send them to the GY, Special Summon a Dragon / Dinosaur / Sea Serpent from the Deck
by combined Level; banish it when this card leaves the field. Also searchable by Hanzo (set code 0x2A).
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, Compiled, RES_RESERVE, RIDER_ATTACH
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R3
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
from otn_enhanced.effects import ov5_cave
import struct


@dataclass(frozen=True)
class continuous_trap_target_ninja_and_opponent_monster_send_to_graveyard_special_summon_dragon_dinosaur_or_sea_serpent_from_deck_by_combined_level_banish_on_leave:
    """Ninjitsu Art of Super-Transformation (Goblin Fan 0x1255, already a Continuous Trap): 'Activate this card by targeting 1 "Ninja" monster
    you control and 1 face-up monster your opponent controls; send them to the GY, then Special Summon 1 Dragon, Dinosaur, or Sea Serpent monster
    from your Deck whose Level is less than or equal to the combined original Levels of the sent monster(s). When this card leaves the field, banish
    that monster.' cls0 record over 0x0E1A (Bubble Shuffle slots + an ov5 resolver and candidate predicate), criteria row over 0x0E12 (ov5 handler),
    leave-cleanup list insert over 0x0E42, the banish-destination hook, Goblin Fan's flip-destroy retired, and the donor added to the repurposed
    "Ninjitsu Art" ARM9 set code 0x2A over phantom 0x1C55 (a post). Original code embedded verbatim (the records=False bisect build and the
    in-place text guard are dropped; the card keeps its stats, so props=None)."""

    def compile(self, view, cid) -> Compiled:
        import struct
        import ndspy.code
        import ndspy.rom
        from otn_enhanced.asm.effect_verify import assert_thumb1_only
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R3, R4, R5, R6, R7
        from otn_enhanced.effects.common import ov3_off as _off

        DONOR_CID = 0x1255                      # Goblin Fan -- already a Continuous Trap

        # ---------------------------------------------------------------------------
        # PART A -- the "Ninjitsu Art" set code 0x2A (repurposed by patch_ninja_
        # grandmaster_hanzo; on a clean ROM its four entries are all phantoms).
        # ---------------------------------------------------------------------------
        SETCODE_THUNK = 0x02023B10
        SETCODE_COUNT_IMM = 0x02023B14          # movs r2,#4
        SETCODE_LIST = 0x0209C5D2
        SETCODE_N = 4
        SETCODE_DROP = 0x1C55                   # phantom padding left by the Hanzo patch

        # ---------------------------------------------------------------------------
        # PART B -- retire the donor's own printed effect.
        # 0x02268C48 is a literal-pool word read by 0x02268B04 (`ldr r6,[pc,#0x140]`) and
        # 0x02268B38.  The block it gates is Goblin Fan's text, "When a Level 2 or lower
        # monster is Flip Summoned, destroy it" -- the `cmp r0,#2 / bgt` right above the
        # load is that Level test.  The block only runs when 0x021AC204(cid) says the cid
        # is face-up on the field, so repointing the word at a phantom kills it forever.
        # ---------------------------------------------------------------------------
        GOBLIN_FAN_LITERAL = 0x02268C48
        RETIRED_CID = 0x0BB8                    # the ROM's own filler phantom (cls0[0..2])

        # ---------------------------------------------------------------------------
        # PART C -- the cls0 record
        # ---------------------------------------------------------------------------
        CLS0_BASE, CLS0_COUNT, CLS0_STRIDE = 0x0227E64C, 0x51A, 24
        CLS0_DROP = 0x0E1A                      # phantom at index 44

        # Bubble Shuffle's resolver is the CLONE SOURCE, not the runtime target -- it
        # hard-codes 0x18F9 (see build_res_stub).  cls0 +04 points at CAVE_NAST_RES.
        BUBBLE_SHUFFLE_RESOLVER = 0x0221EBBD
        PHASE_BLOCK = 0x0229AAFC                # [+0x70] = the resolver phase
        TARGET_FETCH = 0x022349B0               # (desc, i, 0) -> is declared target i present
        TARGET_UNPACK = 0x02234904              # (desc, i)    -> packed side/zone
        TARGET_STILL_LEGAL = 0x0224A924         # (desc, side, zone)
        AFFECT_GUARD = 0x021AFCBC               # (desc, side, zone) nonzero -> skip
        TARGET_GUARD = 0x021AE124                # (acting_side, side, zone) zero -> skip
        SEND_TO_GY = 0x021CF6B8                 # (desc, side, zone) -> destination 0x0E = GY
        SUMMON_STEP = 0x02206F40                # Transformation's tribute -> SS-from-DECK engine
        TRANSFORMATION_RESOLVER = 0x0221B2FD    # (round 10; superseded)
        DECK_SS_RESOLVER = 0x02206CAD           # counter.deck_ss_resolver: the SHARED
                                                # 'Special Summon 1 <filtered> monster from
                                                # your Deck' resolver -- slot +04 of Shien's
                                                # Footsoldier 0x1B3A and Six Scrolls 0x1F76,
                                                # i.e. the two cards whose printed summon
                                                # clause is exactly ours.  Phase window
                                                # 0x78..0x80, nine-way table @0x02206CC6.
        SS_LEGAL_PRED = 0x021B9ECC              # DEBUG probe: 0x021B9708(side, mask 8, 0)
        FREE_ZONE_COUNT = 0x021AD870            # DEBUG probe: free monster zones (returns 5, not 1)

        # --- the deck-SS chassis 0x02206CAC, decoded halfword-by-halfword.
        # build_resolver_stub reimplements its DEFAULT-ARM path; these are every native
        # call that path makes, in phase order.  (The phase table itself is at
        # 0x02206CD2, add-pc base 0x02206CD4 -- NOT the addresses in the old handoff.)
        SS_FREE_ZONE = 0x021AD870               # 0x80 gate 1 (side) -> 0 = cannot Special Summon
        SS_LEGAL_A = 0x021B9ECC                 # 0x80 gate 2 (side)
        SS_LEGAL_B = 0x021B9ED8                 # 0x80 gate 3 (side)
        PARAM_PROVIDER = 0x02234E78             # (desc) -> the criteria `param`
        CRIT_CANDIDATE_COUNT = 0x02243FA8       # (side, cid, param) -> n; CALLS OUR ROW HANDLER
        MESSAGE = 0x0219A818                    # (side, code) -- 0x0D "none", 0x30 "choose"
        LIST_PICKER = 0x0219C430                # (side, mode=6, cid, param) opens the picker
        PICK_READBACK = 0x0219C510              # () -> &0x02299458[[0x0229944C+4]] (a POINTER)
        SS_COMMIT = 0x0226925C                  # (side, &locator, face-up, position, [sp]=cid<<16)
        LEVEL_OF = 0x0202ABD8                   # ARM9, Thumb: (cid) -> the card's ORIGINAL Level.
                                                # Same accessor family as the VERIFIED race reader
                                                # 0x0202ABB8 (card_data_files): `bl 0x0202A084` for the
                                                # card_prop record, then `ldr r0,[r0,#4] ; lsls #0x12 ;
                                                # lsrs #0x1C` = the 4-bit level field at bit 42.
                                                # Cross-checked against card_prop.bin via the savestate
                                                # emulator: 0x13E7 -> 4, 0x16FF -> 6, 0x1255 -> 0, all
                                                # matching game_constants' decode.
        RIDER_ATTACH = 0x021C479C               # rider.node_writer_and_kind_byte, QUEUED route:
                                                # (side, slot, key, kind byte, [caller sp+0] = param)
        SUMMON_BLOCK = 0x02298A28               # +0x04 = the slot the monster was placed in
        RIDER_KIND = 0x17                       # what Transformation passes at its phase 1
        NO_CANDIDATE_CLEANUP = 0x0225BF30       # phase 0x7B (1 - side)
        RESOLUTION_TEARDOWN = 0x021D269C        # phase 0x78 (side) -> then return 0x64
        STEP_COUNTER = 0x0229AB7C               # DEBUG probe: [+0x1C] rejects the mask-8 arm
        MISC_GLOBAL = 0x02299414                # DEBUG probe: [+0x2C] == 5 rejects it too
        _SUMMON_STEP_OLD = 0x0220667C                # the tail step Bubble Shuffle defers to
        ACT_COND = 0x021F8549                   # the 3DS-mapped "send then SS" condition
        TARGET_DECL = 0x02235C75                # the two-target declaration template

        # ---------------------------------------------------------------------------
        # PART D -- the criteria row
        # ---------------------------------------------------------------------------
        CRIT_BASE, CRIT_COUNT, CRIT_STRIDE = 0x022713C4, 0x56C, 12
        CRIT_DROP = 0x0E12                      # phantom at index 11
        CRIT_AUX = 0xFFFF                       # -1 = no set-code filter (as the 3DS row)
        CRIT_WORD = 0x00000002                  # card-type mask: MONSTER

        # ---------------------------------------------------------------------------
        # PART E -- the leave-cleanup membership list
        # ---------------------------------------------------------------------------
        LEAVE_LIST, LEAVE_N = 0x0226E940, 40
        LEAVE_DROP = 0x0E42                     # phantom at index 0

        # ---------------------------------------------------------------------------
        # PART F -- ov5
        # ---------------------------------------------------------------------------
        # claimed slots -- read from the ledger, never hardcoded and never derived from
        # the live CAVE_FREE sentinel (which moves as later patches claim space)
        CAVE_NAST_RES = ov5_cave.CAVE_NAST_RES2         # 0x0239DB80 -- cls0 +04, THE RESOLVER
        CAVE_NAST_DIAG = ov5_cave.CAVE_NAST_DIAG        # 0x0239D990 -- DEBUG, strip before ship
        CAVE_NAST_PRED = ov5_cave.CAVE_NAST_PRED        # 0x0239D940, 0x48 B of 0x50
        CAVE_NAST_CRIT = ov5_cave.CAVE_NAST_CRIT        # 0x0239DB20, 0x5C B of 0x60
        PRED_RESERVE, CRIT_RESERVE, RES_RESERVE = 0x50, 0x60, 0x200
        DIAG_RESERVE = 0x50

        # ov5_cave.CAVE_NAST_RES (0x0239D9E0, 0x140) held the round-10/11 wrapper.  It is
        # too small for the purpose-written resolver and is boxed in by CAVE_NAST_CRIT at
        # 0x0239DB20, so the stub moved to CAVE_NAST_RES2.  The old slot stays RESERVED to
        # this card (see the ledger note) rather than being freed mid-debug.

        # DIAG block (DEBUG ONLY -- read by scratch/nast_state.py):
        #   +0x00  times CAVE_NAST_CRIT was entered   (the Deck-search success signal)
        #   +0x04  the Deck walker's last return value
        #   +0x08  total resolver entries
        #   +0x0C  declared targets actually sent to the GY
        #   +0x10  the declared-target count phase 0x80 saw
        #   +0x14  ROLLING PHASE TRACE -- last four phases, newest in the low byte
        #   +0x18  the candidate count 0x02243FA8 returned

        ZONE_PRED = 0x021D6E40                  # dispatch.zone_predicate_masks
        CID_AT_ZONE = 0x021A36EC                # (side, zone) -> cid
        NINJA_THUNK = 0x020237D8                # has_set_code 6 ("Ninja"); ARM9, Thumb
        DECK_WALKER = 0x0223BC3C                # the Deck container walker
        RACE_PREDICATE = 0x0223C791             # "candidate's race is in this list"

        # masks for 0x021D6E40.  Bits 0-1 are the side selector (01 = same side as the
        # source, 10 = the other side); bits 4-6 are the zone class (1 = a monster zone).
        # 0x0C15 is the own-side face-up monster filter shared by every "select 1 monster
        # on YOUR side" continuous card -- INCLUDING Ninjitsu Art of Decoy 0x17FF
        # (continuous_riders: the 0x021E0680 family).  0x0C16 is the same filter with the
        # side selector flipped, exactly the 0x...95 -> 0x...96 step Bubble Shuffle makes.
        MASK_MINE = 0x00000C15
        MASK_THEIRS = 0x00000C16

        ZONE_DECK = 0x0A                        # the container index the Deck walker takes

        # The level field, bits 23:16 of the criteria word, encoded 0x80 | (L << 2)
        # (counter.criteria_registry_layout).  Transformation's handler ORs this in from
        # its `param`; ours has no param source, so it hardcodes the clamp maximum L=12
        # -- "Level <= 12", i.e. effectively unrestricted, which is what the first build
        # tried to get by omitting the field ENTIRELY.  Omitting it is NOT the same
        # thing: this handler family always writes the field, and a zero there may well
        # read as "Level <= 0".  That is unproven either way and it is exactly why the
        # first build's Deck search may have come back empty.
        LEVEL_BITS = (0x80 | (12 << 2)) << 16   # 0x00B00000 -- the BUILD-TIME default only
        # *** THE LEVEL CAP IS NOW COMPUTED AT RUNTIME, AND THE HANDOFF IS THE CRIT STUB'S
        # OWN LITERAL. *** build_crit_stub keeps `ldr r1,=LEVEL_BITS ; orrs r0,r1` exactly as
        # it was; the resolver simply OVERWRITES that pool word at phase 0x80 with
        # (0x80 | (sum << 2)) << 16 before the Deck search runs.  Nothing about the criteria
        # handler changes, so it does not have to grow past its full 0x60 reserve, and the
        # static byte-compare in verify() still passes because the built ROM carries the
        # default.  0x80 = op 2 = "Level N or lower" (dispatch.criteria_word_level_field).


        # ---------------------------------------------------------------------------
        # helpers (ported verbatim from ninja_grandmaster_hanzo)
        # ---------------------------------------------------------------------------


        def _u16(ov: bytes, addr: int) -> int:
            return struct.unpack_from("<H", ov, _off(addr))[0]


        def _u32(ov: bytes, addr: int) -> int:
            return struct.unpack_from("<I", ov, _off(addr))[0]


        # ---------------------------------------------------------------------------
        # PART H -- C4's DESTINATION: banish, not destroy
        # ---------------------------------------------------------------------------
        # The leave-cleanup body 0x021CB2xx.. walks the leaving card's zones and picks a
        # DESTINATION ZONE CODE into [sp+0xA8] before calling 0x021CC290:
        #
        #     0x021CB48C  movs r0,#0x0E ; str r0,[sp,#0xA8]     <- the DEFAULT: Graveyard
        #     <per-cid switch>
        #     0x021CB50A  movs r0,#0x0F ; str r0,[sp,#0xA8]     <- 0x1D2F Escape: BANISHED
        #     0x021CB504  movs r0,#0x0D                          <- one other arm
        #     0x021CB514  movs r0,#2    ; str r0,[sp,#0xAC]      <- the shared tail
        #
        # So destroy-vs-banish IS encoded, and it is neither the leave list nor the rider
        # kind byte (the two places earlier rounds looked): it is this switch.  All five
        # cids that reach an 0x0F arm -- 0x1625, 0x1880, 0x1881, 0x1D2F, 0x1E30 -- are
        # live members of the list, so there is no dead compare to repoint for free.
        #
        # We therefore REPLACE THE DEFAULT ASSIGNMENT (4 bytes, `movs r0,#0x0E ; str
        # r0,[sp,#0xA8]`) with a BL to a stub that writes 0x0F for our cid and 0x0E for
        # every other.  Safe because, between the call at 0x021CB47C and the reload at
        # 0x021CB4DC, ONLY r0 and r4 are read -- r1/r2/r3 are dead scratch -- and the stub
        # runs at the host's own SP, so [sp,#0xA8] addresses the same slot.  Our cid then
        # falls through the switch to 0x021CB514, taking [sp+0xAC]=2 exactly as Escape
        # from the Dark Dimension does: same destination, same reason code.
        #
        # ⚠️ THE STUB LIVES IN OV3 DEAD CODE, NOT THE OV5 CAVE, and that is deliberate.
        # 0x021CB48C is a SHARED site every one of the 40 leave-list cards runs through.
        # A puzzle loads overlay 41 over overlay 5, so a bl into ov5 here would freeze
        # Premature Burial, Call of the Haunted and friends in every puzzle
        # (otn-continuous-stat-engine: "never bl-hijack a shared fall-through into ov5").
        BANISH_HOOK = 0x021CB48C                # movs r0,#0x0E ; str r0,[sp,#0xA8]
        BANISH_HOOK_ORIG = b"\x0e\x20\x2a\x90"  # `movs r0,#0x0E ; str r0,[sp,#0xA8]`
        DEST_GY, DEST_BANISHED = 0x0E, 0x0F
        CAVE_NAST_DEST = 0x0225F2A8             # the 22 B still free in the 0x0225F240 ov3
                                                # dead block (host cid 0x164C); stub is 20 B
        DEST_RESERVE = 22


        def build_dest_stub(base: int) -> bytes:
            """`[sp,#0xA8] = 0x0F` for our donor, `0x0E` for everyone else, then BX LR.

            Deliberately POOL-FREE: 0x1255 is built with `movs/lsls/adds` so the stub
            needs no 4-aligned literal and fits an 18 B hole.  It runs at the host's own
            SP (no push), so [sp,#0xA8] is the host's slot -- do not add a push.
            """
            b = EffectBuilder()
            b.insn("MOV", f"R0, #0x{DEST_GY:X}")
            b.insn("MOV", f"R1, #0x{DONOR_CID >> 8:X}")
            b.insn("LSL", "R1, R1, #0x8")
            b.insn("ADD", f"R1, #0x{DONOR_CID & 0xFF:X}")
            b.insn("CMP", "R4, R1")
            b.insn("BNE", "keep")
            b.insn("MOV", f"R0, #0x{DEST_BANISHED:X}")
            b.label("keep")
            b.insn("STR", "R0, [SP, #0xA8]")
            b.insn("BX", "LR")
            blob = b.assemble(base, pad="nop")
            assert len(blob) <= DEST_RESERVE, f"dest stub {len(blob)} B > {DEST_RESERVE} B hole"
            assert_thumb1_only(blob, base)
            return blob


        def _thumb_bl(at: int, target: int) -> bytes:
            """Encode the ARMv4T two-halfword BL at *at* to *target*."""
            off = target - (at + 4)
            assert -0x400000 <= off < 0x400000, "BL out of range"
            hi = 0xF000 | ((off >> 12) & 0x7FF)
            lo = 0xF800 | ((off >> 1) & 0x7FF)
            return struct.pack("<HH", hi, lo)



        def _bl_target(ov: bytes, addr: int) -> int:
            """Resolve the ARMv4T two-halfword ``BL`` at *addr* to its target address."""
            hi, lo = _u16(ov, addr), _u16(ov, addr + 2)
            assert (hi & 0xF800) == 0xF000 and (lo & 0xF800) == 0xF800, \
                f"0x{addr:08X} is not a Thumb BL ({hi:#06x} {lo:#06x})"
            off = ((hi & 0x7FF) << 12) | ((lo & 0x7FF) << 1)
            if off & 0x400000:
                off -= 0x800000
            return addr + 4 + off


        def _keys(ov: bytes, base: int, count: int, stride: int, wide: bool) -> list[int]:
            fmt = "<I" if wide else "<H"
            return [struct.unpack_from(fmt, ov, _off(base + i * stride))[0] for i in range(count)]


        def _insert_sorted(ov: bytearray, base: int, count: int, stride: int, fmt: str,
                           record: tuple, drop_cid: int, label: str, wide: bool) -> int:
            """Count-neutral insert of *record* into a cid-sorted array."""
            keys = _keys(ov, base, count, stride, wide)
            new_cid = record[0]
            if new_cid in keys:                                  # idempotent re-run
                pos = keys.index(new_cid)
                cur = struct.unpack_from(fmt, ov, _off(base + pos * stride))
                assert tuple(cur) == tuple(record), f"{label}: cid present with a different record"
                return pos
            assert drop_cid in keys, f"{label}: drop cid 0x{drop_cid:04X} is not in the table"
            dst = keys.index(drop_cid)
            pos = sum(1 for k in keys if k < new_cid)
            if dst < pos:
                pos -= 1
                lo, hi = _off(base + dst * stride), _off(base + pos * stride)
                ov[lo:hi] = ov[lo + stride:hi + stride]
            else:
                lo, hi = _off(base + pos * stride), _off(base + dst * stride)
                ov[lo + stride:hi + stride] = ov[lo:hi]
            struct.pack_into(fmt, ov, _off(base + pos * stride), *record)
            after = _keys(ov, base, count, stride, wide)
            assert all(after[i] <= after[i + 1] for i in range(count - 1)), f"{label}: sort broken"
            assert len(after) == count, f"{label}: count changed"
            return pos


        def _list_insert(ov: bytearray, base: int, count: int, new_cid: int,
                         drop_cid: int, label: str) -> None:
            cur = [_u16(ov, base + 2 * i) for i in range(count)]
            if new_cid in cur:
                return
            assert drop_cid in cur, f"{label}: drop cid 0x{drop_cid:04X} absent"
            new = sorted([c for c in cur if c != drop_cid] + [new_cid])
            assert len(new) == count, f"{label}: length changed"
            assert all(new[i] < new[i + 1] for i in range(count - 1)), f"{label}: not strictly sorted"
            for i, v in enumerate(new):
                struct.pack_into("<H", ov, _off(base + 2 * i), v)


        def _ldr_pc(at: int, reg: int, target: int) -> int:
            imm = target - ((at + 4) & ~3)
            assert 0 <= imm <= 0x3FC and imm % 4 == 0, f"ldr [pc,#{imm}] out of range at 0x{at:08X}"
            return 0x4800 | (reg << 8) | (imm // 4)


        def _bcond(at: int, target: int, cond: int) -> int:
            off = (target - (at + 4)) // 2
            assert -0x80 <= off < 0x80, "conditional branch out of imm8 range"
            return 0xD000 | (cond << 8) | (off & 0xFF)


        # ---------------------------------------------------------------------------
        # PART F1 -- the two-side candidate predicate
        # ---------------------------------------------------------------------------
        def build_pred_stub(base: int) -> bytes:
            """cls0 +08: (r0 = source descriptor, r1 = candidate side, r2 = candidate zone)
            -> 0 reject / nonzero accept.

            A near-verbatim clone of Bubble Shuffle's 0x021E00D8, which is the ROM's own
            "1 of mine AND 1 of theirs" predicate: ONE function serves both targets and
            branches on whether the candidate is on the acting side.  The only change is
            the my-side extra test -- Bubble Shuffle compares the candidate against a
            single cid (0x021A3800), we ask whether it is a "Ninja" (set code 6).

                push {r4,r5,r6,lr}
                adds r5,r1,#0          ; keep side
                adds r4,r2,#0          ; keep zone
                ldrb r3,[r0,#2]        ; the ACTING side
                cmp  r1,r3
                bne  theirs
                ldr  r3,=0x0C15        ; my side: face-up monster I control
                ldr  r6,=ZONE_PRED|1
                blx  r6
                cmp  r0,#0
                beq  reject
                adds r0,r5,#0
                adds r1,r4,#0
                ldr  r6,=CID_AT_ZONE|1
                blx  r6                ; -> the candidate's cid
                ldr  r6,=NINJA_THUNK|1
                blx  r6                ; -> nonzero iff it is a "Ninja"
                pop  {r4,r5,r6,pc}
            reject:
                movs r0,#0
                pop  {r4,r5,r6,pc}
            theirs:
                ldr  r3,=0x0C16        ; their side: any face-up monster
                ldr  r6,=ZONE_PRED|1
                blx  r6
                pop  {r4,r5,r6,pc}
            """
            assert base % 4 == 0, f"stub base 0x{base:08X} must be 4-aligned"
            reject = base + 0x24
            theirs = base + 0x28
            body_len = 0x34                                # 26 halfwords, pool 4-aligned
            pool = base + body_len
            lit_mask_mine, lit_zone_pred, lit_cid_at, lit_ninja, lit_mask_theirs = (
                pool, pool + 4, pool + 8, pool + 12, pool + 16)
            w = [
                0xB570,                                    # 0x00 push {r4,r5,r6,lr}
                0x1C0D,                                    # 0x02 adds r5,r1,#0
                0x1C14,                                    # 0x04 adds r4,r2,#0
                0x7883,                                    # 0x06 ldrb r3,[r0,#2]
                0x4299,                                    # 0x08 cmp  r1,r3
                _bcond(base + 0x0A, theirs, 0x1),          # 0x0A bne  theirs
                _ldr_pc(base + 0x0C, 3, lit_mask_mine),    # 0x0C ldr  r3,=0x0C15
                _ldr_pc(base + 0x0E, 6, lit_zone_pred),    # 0x0E ldr  r6,=ZONE_PRED|1
                0x47B0,                                    # 0x10 blx  r6
                0x2800,                                    # 0x12 cmp  r0,#0
                _bcond(base + 0x14, reject, 0x0),          # 0x14 beq  reject
                0x1C28,                                    # 0x16 adds r0,r5,#0
                0x1C21,                                    # 0x18 adds r1,r4,#0
                _ldr_pc(base + 0x1A, 6, lit_cid_at),       # 0x1A ldr  r6,=CID_AT_ZONE|1
                0x47B0,                                    # 0x1C blx  r6
                _ldr_pc(base + 0x1E, 6, lit_ninja),        # 0x1E ldr  r6,=NINJA_THUNK|1
                0x47B0,                                    # 0x20 blx  r6
                0xBD70,                                    # 0x22 pop  {r4,r5,r6,pc}
                0x2000,                                    # 0x24 reject: movs r0,#0
                0xBD70,                                    # 0x26 pop  {r4,r5,r6,pc}
                _ldr_pc(base + 0x28, 3, lit_mask_theirs),  # 0x28 theirs: ldr r3,=0x0C16
                _ldr_pc(base + 0x2A, 6, lit_zone_pred),    # 0x2A ldr  r6,=ZONE_PRED|1
                0x47B0,                                    # 0x2C blx  r6
                0xBD70,                                    # 0x2E pop  {r4,r5,r6,pc}
                0x0000,                                    # 0x30 pad
                0x0000,                                    # 0x32 pad
            ]
            blob = b"".join(struct.pack("<H", x) for x in w)
            assert len(blob) == body_len, f"pred body {len(blob):#x} != {body_len:#x}"
            blob += struct.pack("<IIIII", MASK_MINE, ZONE_PRED | 1, CID_AT_ZONE | 1,
                                NINJA_THUNK | 1, MASK_THEIRS)
            assert_thumb1_only(blob[:body_len], base)
            assert len(blob) <= PRED_RESERVE, f"pred stub {len(blob):#x} > reserve"
            return blob


        # ---------------------------------------------------------------------------
        # PART F3 -- THE RESOLVER (round 12: purpose-written, delegates to nothing)
        # ---------------------------------------------------------------------------
        def build_resolver_stub(base: int) -> bytes:
            """cls0 +04: OUR OWN phase machine.  (r0 = descriptor) -> the next phase.

            *** WHY THIS IS NOT A WRAPPER.  Three rounds delegated to a native resolver
            -- Bubble Shuffle 0x0221EBBD, Transformation 0x0221B2FD, the shared deck-SS
            0x02206CAD -- and all three froze the game in-game.  The user has ruled
            delegation out.  This stub owns every phase itself. ***

            IT IS NOT INVENTED, EITHER.  It is a byte-level reimplementation of the
            DEFAULT-ARM path of 0x02206CAC (`counter.deck_ss_resolver`, slot +04 of
            Shien's Footsoldier 0x1B3A and Six Scrolls of the Samurai 0x1F76 -- the two
            stock cards whose printed summon clause is exactly ours), with this card's
            one extra verb prepended to phase 0x80.  Every address below was read out of
            ov3 this session; see notes/ninjitsu-art-super-transformation-findings.md.

            ⚠️ The phase table in PROMPT_nast_resolver.md was MIS-DECODED -- it read the
            dispatch prologue's own instruction halfwords as table entries against the
            wrong add-pc base, which is where its "picker arm 0x022080D0" and "the summon
            is 0x02269314" both came from.  Neither address is on this path.  The real
            table is at 0x02206CD2 with add-pc base 0x02206CD4:

                0x80 -> 0x02206CE4   0x7F -> 0x02206E2A   0x7E -> 0x02206E4E
                0x7C -> 0x02206E62   0x7B -> 0x02206EE8   0x78 -> 0x02206EF4
                0x79 / 0x7A / 0x7D -> 0x02206EFE, which is ALSO the out-of-window
                target of the `b` at 0x02206CC4 -- i.e. the unused slots, which is the
                structural check that this decode is the right one.

            THE MACHINE (return value = the next phase; 0 = stop):

              0x80  send every declared target to the GY   <- OUR verb, the loop already
                    proven in-game in rounds 3..8; then the chassis's own three
                    Special-Summon legality gates and the candidate count
                    0x02243FA8(side, cid, param), which is what finally calls
                    CAVE_NAST_CRIT.  0 candidates -> message 0x0D, go to 0x7B.
              0x7F  message 0x30 ("choose a card"), go to 0x7E.
              0x7E  0x0219C430(side, 6, cid, param) opens the list picker.  The `6` is a
                    LITERAL in the chassis, not an unpinned register.
              0x7C  0x0219C510() returns &LOCATOR[picked index] (0x02299458, stride 4),
                    handed straight to the summon commit
                    0x0226925C(side, &locator, face-up=1, position=2,
                               [sp] = acting_cid << 16).
                    That fifth argument's HIGH half lands at [0x02298A28 + 0x12] -- the
                    "which card summoned this" attribution field, which is what PART E's
                    leave-cleanup list needs.
              0x7B  0x0225BF30(1 - side) -- the no-candidate cleanup.
              0x78  0x021D269C(side) -- teardown.  *** RETURNS 1, NOT THE CHASSIS'S 0x64. ***
                    That one immediate is clause 4.  The driver at 0x02218042 stores any
                    NONZERO return as the next phase and re-enters, so returning 1 drives
                    PHASE 1 -- and phase 1 is where a continuous card attaches its
                    "when I leave, the monster leaves with me" link.  The deck-SS chassis
                    returns 0x64 (stop) because Shien's Footsoldier and Six Scrolls have
                    no attached monster to clean up; the NAMED-SS chassis 0x02206F40 that
                    Transformation rides returns 1 from its own teardown arm 0x02207116,
                    which calls the SAME 0x021D269C.  Copying the deck-SS 0x64 faithfully
                    is exactly why C4 did nothing in-game 2026-08-31.
              0x01  attach that link: 0x021C479C(side, [0x02298A28+4], locator, 0x17,
                    [sp] = 0), where locator = (desc[+3] << 8) | desc[+2] -- this card's
                    own (zone, side).  Savestate-checked: desc[+2]=0 / desc[+3]=6 with the
                    card in S/T zone 6, and [summon block + 4] = 2 with the summoned
                    monster in monster zone 2.
                    ⚠️ Transformation's own phase-1 body reads the descriptor out of R3,
                    which the invoker 0x0224AEB8 does NOT set (its bl 0x021A1430 clobbers
                    r0-r3 before the blx r2).  We rebuild the arguments from R5 instead.

            Phase order in the emitted code is deliberate: the five SHORT arms sit
            directly after the dispatch so their `beq`s stay inside Thumb-1's imm8
            branch range, and the long 0x80 arm goes last.

            r1 (the event) is not used -- unlike a wrapper, this stub calls no 2-arg
            native, so there is nothing to preserve it for.

            ⚠️ DIAG writes are DEBUG ONLY and must be stripped before shipping.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R6, [R5, #0x2]")
            b.insn("LDRB", "R0, [R5, #0x6]")
            b.insn("EOR", "R6, R0")
            b.ldr_const(4, PHASE_BLOCK)
            b.insn("LDR", "R4, [R4, #0x70]")
            b.ldr_const(7, CAVE_NAST_DIAG)
            b.insn("LDR", "R0, [R7, #0x8]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R7, #0x8]")
            b.insn("LDR", "R0, [R7, #0x14]")
            b.insn("LSL", "R0, R0, #0x8")
            b.insn("ORR", "R0, R4")
            b.insn("STR", "R0, [R7, #0x14]")
            b.insn("CMP", "R4, #0x80")
            b.insn("BEQ", "ph80")
            b.insn("CMP", "R4, #0x7F")
            b.insn("BEQ", "ph7f")
            b.insn("CMP", "R4, #0x7E")
            b.insn("BEQ", "ph7e")
            b.insn("CMP", "R4, #0x7C")
            b.insn("BEQ", "ph7c")
            b.insn("CMP", "R4, #0x7B")
            b.insn("BEQ", "ph7b")
            b.insn("CMP", "R4, #0x78")
            b.insn("BEQ", "ph78")
            b.insn("CMP", "R4, #0x1")
            b.insn("BEQ", "ph1")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("ph1")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("LDRB", "R2, [R5, #0x3]")
            b.insn("LSL", "R2, R2, #0x8")
            b.insn("ORR", "R2, R0")
            b.insn("LSL", "R2, R2, #0x10")
            b.insn("LSR", "R2, R2, #0x10")
            b.ldr_const(1, SUMMON_BLOCK)
            b.insn("LDRH", "R1, [R1, #0x4]")
            b.insn("MOV", f"R3, #0x{RIDER_KIND:X}")
            b.insn("MOV", "R4, #0x0")
            b.insn("STR", "R4, [SP, #0x0]")
            b.call_addr(RIDER_ATTACH, via=R7)
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("ph7f")
            b.call_addr(MESSAGE, R6, 0x30, via=R3)
            b.insn("MOV", "R0, #0x7E")
            b.insn("B", "ret")
            b.label("ph7e")
            b.call_addr(PARAM_PROVIDER, R5, via=R7)
            b.insn("ADD", "R3, R0, #0x0")
            b.insn("LDRH", "R2, [R5, #0x0]")
            b.insn("MOV", "R1, #0x6")
            b.call_addr(LIST_PICKER, R6, via=R7)
            b.insn("MOV", "R0, #0x7C")
            b.insn("B", "ret")
            b.label("ph7c")
            b.call_addr(PICK_READBACK, via=R7)
            b.insn("ADD", "R1, R0, #0x0")
            b.insn("LDRH", "R0, [R5, #0x0]")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("STR", "R0, [SP, #0x0]")
            b.call_addr(SS_COMMIT, R6, R1, 1, 2, via=R7)
            b.insn("MOV", "R0, #0x78")
            b.insn("B", "ret")
            b.label("ph7b")
            b.insn("MOV", "R0, #0x1")
            b.insn("SUB", "R0, R0, R6")
            b.call_addr(NO_CANDIDATE_CLEANUP, via=R3)
            b.insn("MOV", "R0, #0x78")
            b.insn("B", "ret")
            b.label("ph78")
            b.call_addr(RESOLUTION_TEARDOWN, R6, via=R3)
            b.insn("MOV", "R0, #0x1")
            b.insn("B", "ret")
            b.label("ph80")
            b.insn("LDRH", "R0, [R5, #0x12]")
            b.insn("STR", "R0, [R7, #0x10]")
            b.insn("SUB", "R4, R0, #0x1")
            b.insn("MOV", "R6, #0x0")
            b.insn("B", "lvlchk")
            b.label("lvlbody")
            b.call_addr(TARGET_UNPACK, R5, R4, via=R3)
            b.insn("LSL", "R1, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("LSR", "R0, R0, #0x10")
            b.insn("ASR", "R0, R0, #0x8")
            b.insn("LSL", "R0, R0, #0x18")
            b.insn("LSR", "R7, R0, #0x18")
            b.insn("LSR", "R0, R1, #0x18")
            b.call_addr(CID_AT_ZONE, R0, R7, via=R3)
            b.call("cid_level", via=R3)
            b.insn("ADD", "R6, R6, R0")
            b.insn("SUB", "R4, R4, #0x1")
            b.label("lvlchk")
            b.insn("CMP", "R4, #0x0")
            b.insn("BGE", "lvlbody")
            b.insn("CMP", "R6, #0xF")
            b.insn("BLE", "lvlok")
            b.insn("MOV", "R6, #0xF")
            b.label("lvlok")
            b.insn("LSL", "R6, R6, #0x2")
            b.insn("ADD", "R6, #0x80")
            b.insn("LSL", "R6, R6, #0x10")
            b.ldr_const(3, CAVE_NAST_CRIT + 0x50)
            b.insn("STR", "R6, [R3, #0x0]")
            b.insn("LDRH", "R0, [R5, #0x12]")
            b.insn("SUB", "R4, R0, #0x1")
            b.insn("B", "gychk")
            b.label("gybody")
            b.call_addr(TARGET_UNPACK, R5, R4, via=R3)
            b.insn("LSL", "R1, R0, #0x18")
            b.insn("LSL", "R0, R0, #0x10")
            b.insn("LSR", "R0, R0, #0x10")
            b.insn("ASR", "R0, R0, #0x8")
            b.insn("LSL", "R0, R0, #0x18")
            b.insn("LSR", "R7, R0, #0x18")
            b.insn("LSR", "R6, R1, #0x18")
            b.call_addr(AFFECT_GUARD, R5, R6, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "gyskip")
            b.call_addr(TARGET_GUARD, R6, R6, R7, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "gyskip")
            b.call_addr(SEND_TO_GY, R5, R6, R7, via=R3)
            b.ldr_const(3, CAVE_NAST_DIAG)
            b.insn("LDR", "R0, [R3, #0xC]")
            b.insn("ADD", "R0, #0x1")
            b.insn("STR", "R0, [R3, #0xC]")
            b.label("gyskip")
            b.insn("SUB", "R4, R4, #0x1")
            b.label("gychk")
            b.insn("CMP", "R4, #0x0")
            b.insn("BGE", "gybody")
            b.insn("LDRB", "R6, [R5, #0x2]")
            b.insn("LDRB", "R0, [R5, #0x6]")
            b.insn("EOR", "R6, R0")
            b.call_addr(SS_FREE_ZONE, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "p80stop")
            b.call_addr(SS_LEGAL_A, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "p80stop")
            b.call_addr(SS_LEGAL_B, R6, via=R3)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "p80count")
            b.label("p80stop")
            b.insn("MOV", "R0, #0x0")
            b.insn("B", "ret")
            b.label("p80count")
            b.call_addr(PARAM_PROVIDER, R5, via=R3)
            b.insn("ADD", "R2, R0, #0x0")
            b.insn("LDRH", "R1, [R5, #0x0]")
            b.call_addr(CRIT_CANDIDATE_COUNT, R6, via=R3)
            b.ldr_const(3, CAVE_NAST_DIAG)
            b.insn("STR", "R0, [R3, #0x18]")
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "p80ok")
            b.call_addr(MESSAGE, R6, 0xD, via=R3)
            b.insn("MOV", "R0, #0x7B")
            b.insn("B", "ret")
            b.label("p80ok")
            b.insn("MOV", "R0, #0x7F")
            b.label("ret")
            b.insn("POP", "{R3, R4, R5, R6, R7, PC}")
            blob = b.assemble(base, pad="nop")
            assert len(blob) <= RES_RESERVE, f"resolver {len(blob):#x} > reserve {RES_RESERVE:#x}"
            assert_thumb1_only(blob, base)
            return blob


        # The round-10/11 DELEGATING WRAPPER that used to live here is deleted, not
        # commented out: it intercepted phase 0x80, sent the declared targets to the GY,
        # and tail-called a native resolver for every phase.  Shipped over 0x0221B2FD
        # (round 10) and 0x02206CAD (round 11); BOTH FROZE in-game.  build_resolver_stub
        # above records what replaced it and why.

        # ---------------------------------------------------------------------------
        # PART F2 -- the Dragon / Dinosaur / Sea Serpent Deck criteria handler
        # ---------------------------------------------------------------------------
        def build_crit_stub(base: int) -> bytes:
            """criteria-row handler: (r0 = row, r1 = side, r2 = param) -> candidate count.

            A clone of Ninjitsu Art of Transformation's 0x0223E768 with TWO changes:

              * the 4-word race whitelist is {1, 9, 5, 0} = Dragon, Dinosaur, Sea Serpent
                instead of Transformation's 0x02271304 = {11, 16, 10} = Beast, Winged
                Beast, Insect.  No {1,9,5,0} exists anywhere in ov3 -- every 4-word window
                was scanned -- which is why this needs a stub at all.
              * only the DECK container is searched.  Transformation calls 0x0223C16C with
                zone 2 (HAND) and then 0x0223BC3C with zone 0xA (DECK); the printed text
                here says "from your Deck", so the hand call is dropped.

            The level bits the original ORs in from r2 are also dropped -- see the
            DEVIATIONS note in the module docstring.
            """
            assert base % 4 == 0, f"stub base 0x{base:08X} must be 4-aligned"
            body_len = 0x3C                                # 30 halfwords, pool 4-aligned
            pool = base + body_len
            lit_list = pool                                # the FOUR RACE WORDS themselves
            lit_diag = pool + 0x10
            lit_level = pool + 0x14
            lit_race_pred = pool + 0x18
            lit_walker = pool + 0x1C
            # *** THE ROUND-12 BUG, AND WHY THIS WORD EXISTS. ***
            # `ldm r4!` needs r4 to be the ADDRESS of the race list.  Transformation's
            # original loads a POINTER (`ldr r4,[pc,#0x48]` = 0x02271304, a list that
            # lives in ov3).  Ours carries its own list, and rounds 10-12 pointed the
            # `ldr` straight AT that list -- so r4 loaded the first race CODE, 1, and the
            # `ldm r4!` read from address 0x00000001.  The handler never got as far as
            # its own DIAG counter, which is exactly why "criteria handler entered" read
            # 0 in every savestate.  The list needs a pointer word of its own.
            lit_list_ptr = pool + 0x20

            w = [
                0xB5F8,                                    # 0x00 push {r3,r4,r5,r6,r7,lr}
                0xB086,                                    # 0x02 sub  sp,#0x18
                0x1C05,                                    # 0x04 adds r5,r0,#0   (row)
                0x1C0E,                                    # 0x06 adds r6,r1,#0   (side)
                _ldr_pc(base + 0x08, 4, lit_list_ptr),     # 0x08 ldr  r4,=&RACE_LIST
                0xCC03,                                    # 0x0A ldm  r4!,{r0,r1}
                0xAB02,                                    # 0x0C add  r3,sp,#8
                0xC303,                                    # 0x0E stm  r3!,{r0,r1}
                0xCC03,                                    # 0x10 ldm  r4!,{r0,r1}
                0xC303,                                    # 0x12 stm  r3!,{r0,r1}
                # --- DIAGNOSTIC: count entries.  r4 is callee-saved, so it survives the
                # --- walker call below and is reused at 0x34 to bank the return value.
                _ldr_pc(base + 0x14, 4, lit_diag),         # 0x14 ldr  r4,=DIAG
                0x6820,                                    # 0x16 ldr  r0,[r4]
                0x3001,                                    # 0x18 adds r0,#1
                0x6020,                                    # 0x1A str  r0,[r4]
                0x68A8,                                    # 0x1C ldr  r0,[r5,#8]   (criteria word)
                _ldr_pc(base + 0x1E, 1, lit_level),        # 0x1E ldr  r1,=LEVEL_BITS
                0x4308,                                    # 0x20 orrs r0,r1
                0x9000,                                    # 0x22 str  r0,[sp]      (word)
                0x200A,                                    # 0x24 movs r0,#0x0A
                0x9001,                                    # 0x26 str  r0,[sp,#4]   (type)
                0x8829,                                    # 0x28 ldrh r1,[r5]      (cid)
                _ldr_pc(base + 0x2A, 2, lit_race_pred),    # 0x2A ldr  r2,=RACE_PREDICATE
                0x1C30,                                    # 0x2C adds r0,r6,#0     (side)
                0xAB02,                                    # 0x2E add  r3,sp,#8     (list)
                _ldr_pc(base + 0x30, 7, lit_walker),       # 0x30 ldr  r7,=DECK_WALKER|1
                0x47B8,                                    # 0x32 blx  r7
                0x6060,                                    # 0x34 str  r0,[r4,#4]   DIAG: return
                0xB006,                                    # 0x36 add  sp,#0x18
                0xBDF8,                                    # 0x38 pop  {r3,r4,r5,r6,r7,pc}
                0x0000,                                    # 0x3A pad -> 4-align the pool
            ]
            blob = b"".join(struct.pack("<H", x) for x in w)
            assert len(blob) == body_len, f"crit body {len(blob):#x} != {body_len:#x}"
            blob += struct.pack("<IIII", 1, 9, 5, 0)       # the race whitelist, AT lit_list
            blob += struct.pack("<I", CAVE_NAST_DIAG)
            blob += struct.pack("<I", LEVEL_BITS)
            blob += struct.pack("<II", RACE_PREDICATE, DECK_WALKER | 1)
            blob += struct.pack("<I", lit_list)            # -> r4 for the `ldm r4!` pair
            assert struct.unpack_from("<I", blob, lit_list_ptr - base)[0] == lit_list, \
                "the race-list POINTER word is not where the `ldr r4,=&RACE_LIST` reads"
            assert struct.unpack_from("<I", blob, lit_list - base)[0] == 1, \
                "the race list no longer starts at lit_list"
            # THE LEVEL LITERAL IS A RUNTIME HANDOFF, NOT A CONSTANT: the resolver
            # overwrites this exact word at phase 0x80 with (0x80 | (sum << 2)) << 16, and
            # it hardcodes CAVE_NAST_CRIT + 0x50 to do it.  Keep the two in step.
            assert lit_level - base == 0x50, \
                f"the level literal moved to +0x{lit_level - base:02X}; the resolver writes +0x50"
            assert struct.unpack_from("<I", blob, lit_level - base)[0] == LEVEL_BITS, \
                "the level literal is not the build-time default"
            assert_thumb1_only(blob[:body_len], base)
            assert len(blob) <= CRIT_RESERVE, f"crit stub {len(blob):#x} > reserve"
            return blob


        # ---------------------------------------------------------------------------
        # overlay-3 parts
        # ---------------------------------------------------------------------------
        def _assert_preconditions(ov: bytes) -> None:
            """Every base-image assumption, checked BEFORE a byte is written."""
            # PART B -- the donor's stock-effect block is where we think it is
            assert _u32(ov, GOBLIN_FAN_LITERAL) in (DONOR_CID, RETIRED_CID), \
                "Goblin Fan literal already holds something unexpected"
            assert _u16(ov, 0x02268B00) == 0x2802, \
                "the `cmp r0,#2` Level gate above the donor block moved"
            # PART C -- the templates we clone are intact
            cls0 = _keys(ov, CLS0_BASE, CLS0_COUNT, CLS0_STRIDE, True)
            bs = cls0.index(0x1908)
            assert _u32(ov, CLS0_BASE + bs * CLS0_STRIDE + 4) == BUBBLE_SHUFFLE_RESOLVER, \
                "Bubble Shuffle's resolver moved"
            assert _u32(ov, CLS0_BASE + bs * CLS0_STRIDE + 0x14) == TARGET_DECL, \
                "Bubble Shuffle's target declaration moved"
            # the two-target switch default still lives where it was decoded
            assert _u16(ov, 0x02235C80) == 0x2701 and _u16(ov, 0x02235C82) == 0x2502, \
                "the 0x02235C74 defaults (movs r7,#1 / movs r5,#2) moved"
            # PART D -- Transformation's criteria handler, our clone source
            crit = _keys(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, False)
            t = crit.index(0x1768)
            assert _u32(ov, CRIT_BASE + t * CRIT_STRIDE + 4) == 0x0223E769, \
                "Transformation's criteria handler moved"
            assert _u32(ov, 0x02271304) == 11 and _u32(ov, 0x02271308) == 16 \
                and _u32(ov, 0x0227130C) == 10 and _u32(ov, 0x02271310) == 0, \
                "Transformation's race whitelist moved"
            # -- PART F3: the chassis build_resolver_stub REIMPLEMENTS.  We no longer
            # call 0x02206CAC, but every native address the stub calls was read out of
            # it, so it stays the anchor: if the chassis drifts, our copy is stale.
            # (counter.deck_ss_resolver anchors the function itself on this record.)
            # ⚠️ FIND SHIEN'S FOOTSOLDIER BY CID, NEVER BY ROW INDEX. The first attempt
            # asserted cls2[237], which is where it sits in a CLEAN ROM -- and the chain
            # build aborted here at step 36 of 43, because count-neutral inserts by the
            # 35 patches ahead of us shift every row after their insertion point. A row
            # index is a fact about one image, not about the table.
            cls2 = _keys(ov, 0x02275C04, 0x2B9, 24, wide=True)
            assert 0x1B3A in cls2, "Shien's Footsoldier 0x1B3A is not in cls2 at all"
            assert _u32(ov, 0x02275C04 + cls2.index(0x1B3A) * 24 + 4) == DECK_SS_RESOLVER, \
                "Shien's Footsoldier no longer routes to the shared deck-SS resolver"
            assert _u16(ov, 0x02206CBE) == 0x3978 and _u16(ov, 0x02206CC0) == 0x2908, \
                "the deck-SS resolver's 0x78..0x80 phase window moved"
            # the nine-way jump table itself: halfwords at 0x02206CD2, add-pc base
            # 0x02206CD4.  ⚠️ PROMPT_nast_resolver.md decoded this from 0x02206CC6 with
            # base 0x02206CC8 and got the PROLOGUE'S OWN INSTRUCTIONS back as "arms".
            arms = []
            for k in range(9):
                hw = _u16(ov, 0x02206CD2 + 2 * k)
                arms.append(0x02206CD4 + (hw - 0x10000 if hw & 0x8000 else hw))
            assert arms == [0x02206EF4, 0x02206EFE, 0x02206EFE, 0x02206EE8, 0x02206E62,
                            0x02206EFE, 0x02206E4E, 0x02206E2A, 0x02206CE4], \
                f"the deck-SS phase table moved: {[hex(a) for a in arms]}"
            # phase 0x80's DEFAULT arm: param provider then the candidate count
            assert _u16(ov, 0x02206E06) == 0x1C20 and _u16(ov, 0x02206E0E) == 0x8821, \
                "phase 0x80's default arm no longer loads the descriptor / cid"
            for site, fn in ((0x02206E08, PARAM_PROVIDER), (0x02206E12, CRIT_CANDIDATE_COUNT),
                             (0x02206E1E, MESSAGE)):
                assert _bl_target(ov, site) == fn, \
                    f"phase 0x80's call at 0x{site:08X} is no longer 0x{fn:08X}"
            # phase 0x7E: the picker, and the mode really is the literal 6
            assert _u16(ov, 0x02206E58) == 0x2106, "the list-picker mode is no longer `movs r1,#6`"
            assert _bl_target(ov, 0x02206E4E) == PARAM_PROVIDER \
                and _bl_target(ov, 0x02206E5A) == LIST_PICKER, \
                "phase 0x7E's param / picker calls moved"
            # phase 0x7C: read the pick back, then commit the summon
            assert _bl_target(ov, 0x02206ECA) == PICK_READBACK \
                and _bl_target(ov, 0x02206EE0) == SS_COMMIT, \
                "phase 0x7C's read-back / summon calls moved"
            # the read-back really returns a POINTER into the candidate locator array
            assert _u32(ov, 0x0219C520) == 0x0229944C and _u32(ov, 0x0219C524) == 0x02299458, \
                "0x0219C510's picker-control / locator-array literals moved"
            assert _u16(ov, 0x0219C518) == 0x0080 and _u16(ov, 0x0219C51A) == 0x1810, \
                "0x0219C510 no longer computes &LOCATORS[index]"
            # phases 0x7B / 0x78 teardown
            assert _bl_target(ov, 0x02206EEC) == NO_CANDIDATE_CLEANUP \
                and _bl_target(ov, 0x02206EF6) == RESOLUTION_TEARDOWN, \
                "the 0x7B / 0x78 teardown calls moved"
            # the criteria fill still invokes the row's own handler from row+4
            assert _u32(ov, 0x02243FA0) == CRIT_BASE and _u32(ov, 0x02243FA4) == CRIT_BASE + 4, \
                "0x02243F38's registry base / handler-slot literals moved"
            assert _u16(ov, 0x02243F74) == 0x4798, \
                "0x02243F38 no longer `blx r3`s the criteria row's own handler"

            # PART H -- the leave-cleanup DESTINATION switch, and the dead ov3 hole
            _hook_now = bytes(ov[_off(BANISH_HOOK):_off(BANISH_HOOK) + 4])
            assert _hook_now in (BANISH_HOOK_ORIG,
                                 _thumb_bl(BANISH_HOOK, CAVE_NAST_DEST)),         (f"0x{BANISH_HOOK:08X} holds {_hook_now.hex()}, which is neither the stock "
                 "`movs r0,#0x0E ; str r0,[sp,#0xA8]` nor our own BL (idempotent re-run)")
            assert _u16(ov, 0x021CB50A) == 0x200F and _u16(ov, 0x021CB50C) == 0x902A,         "Escape from the Dark Dimension's BANISH arm (dest 0x0F) moved"
            assert _u16(ov, 0x021CB514) == 0x2002 and _u16(ov, 0x021CB516) == 0x902B,         "the shared tail's `movs r0,#2 ; str r0,[sp,#0xAC]` moved -- and note it reuses r0, which is why the stub's r0 output does not need to survive it"
            assert _u16(ov, 0x021CB536) == 0x9A2A,         "0x021CC290 no longer takes the destination from [sp,#0xA8]"

            # PART E -- the leave list is the 40-entry sorted array we measured
            leave = [_u16(ov, LEAVE_LIST + 2 * i) for i in range(LEAVE_N)]
            assert all(leave[i] < leave[i + 1] for i in range(LEAVE_N - 1)), \
                "leave-cleanup list is not strictly sorted"
            assert 0x1768 in leave and 0x1F75 in leave and 0x1D2F in leave, \
                "the leave-cleanup list lost a known member"
            # the donor must be genuinely records-free
            assert DONOR_CID not in cls0, "the donor already owns a cls0 record"


        def apply_effect(ov: bytearray, records: bool = True) -> None:
            """*records=False* is the BISECT build: the card still exists, is named and
            is Hanzo-searchable (PARTS A/B/E/G), but gets NO cls0 record and NO criteria
            row -- so it has no effect and, crucially, no `+08` candidate predicate.
            dispatch.cls2_plus08_is_the_per_card_candidate_filter says a card with no
            `+08` ACCEPTS every candidate, so this isolates 'the new records' from
            'the new card identity' in a single duel."""
            # -- PART B ------------------------------------------------------------
            struct.pack_into("<I", ov, _off(GOBLIN_FAN_LITERAL), RETIRED_CID)

            if not records:
                _list_insert(ov, LEAVE_LIST, LEAVE_N, DONOR_CID, LEAVE_DROP, "leave-cleanup")
                return

            # -- PART C ------------------------------------------------------------
            _insert_sorted(
                ov, CLS0_BASE, CLS0_COUNT, CLS0_STRIDE, "<6I",
                (DONOR_CID, CAVE_NAST_RES | 1, CAVE_NAST_PRED | 1, ACT_COND, 0, TARGET_DECL),
                CLS0_DROP, "cls0", wide=True)

            # -- PART D ------------------------------------------------------------
            _insert_sorted(
                ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, "<HHII",
                (DONOR_CID, CRIT_AUX, CAVE_NAST_CRIT | 1, CRIT_WORD),
                CRIT_DROP, "criteria", wide=False)

            # -- PART E ------------------------------------------------------------
            _list_insert(ov, LEAVE_LIST, LEAVE_N, DONOR_CID, LEAVE_DROP, "leave-cleanup")

            # -- PART H ------------------------------------------------------------
            blob = build_dest_stub(CAVE_NAST_DEST)
            ov[_off(CAVE_NAST_DEST):_off(CAVE_NAST_DEST) + len(blob)] = blob
            ov[_off(BANISH_HOOK):_off(BANISH_HOOK) + 4] = _thumb_bl(BANISH_HOOK, CAVE_NAST_DEST)


        # ---------------------------------------------------------------------------
        # PART A -- ARM9
        # ---------------------------------------------------------------------------
        def _arm9_section(rom: "ndspy.rom.NintendoDSRom"):
            mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
            for sec in mc.sections:
                if sec.ramAddress == 0x02000000:
                    return mc, sec
            raise AssertionError("ARM9 0x02000000 section not found")


        def apply_arm9_setcode(out_path: str) -> None:
            rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
            mc, sec = _arm9_section(rom)
            d = bytearray(sec.data)

            def off(a: int) -> int:
                return a - 0x02000000

            # take the count and the list base from the thunk itself, never on faith
            count_imm = struct.unpack_from("<H", d, off(SETCODE_COUNT_IMM))[0]
            assert (count_imm & 0xFF00) == 0x2200, \
                f"set-code 0x2A count immediate is not `movs r2,#N`: {count_imm:#06x}"
            n = count_imm & 0xFF
            assert n == SETCODE_N, f"set code 0x2A holds {n} entries, expected {SETCODE_N}"

            cur = [struct.unpack_from("<H", d, off(SETCODE_LIST + 2 * i))[0] for i in range(n)]
            if DONOR_CID not in cur:
                assert SETCODE_DROP in cur, \
                    f"set code 0x2A has no phantom 0x{SETCODE_DROP:04X} to spend: {cur}"
                new = sorted([c for c in cur if c != SETCODE_DROP] + [DONOR_CID])
                assert len(new) == n and all(new[i] < new[i + 1] for i in range(n - 1)), \
                    f"set code 0x2A would not stay strictly sorted: {new}"
                for i, v in enumerate(new):
                    struct.pack_into("<H", d, off(SETCODE_LIST + 2 * i), v)

            sec.data = bytes(d)
            rom.arm9 = mc.save()
            rom.saveToFile(out_path)


        def install(rom, view):
            ov = view.buf
            _assert_preconditions(ov)
            apply_effect(ov, records=True)
            for addr, blob, reserve, label in (
                    (CAVE_NAST_PRED, build_pred_stub(CAVE_NAST_PRED), PRED_RESERVE, "pred"),
                    (CAVE_NAST_CRIT, build_crit_stub(CAVE_NAST_CRIT), CRIT_RESERVE, "crit"),
                    (CAVE_NAST_RES, build_resolver_stub(CAVE_NAST_RES), RES_RESERVE, "resolver"),
                    (CAVE_NAST_DIAG, bytes(0x40), DIAG_RESERVE, "diag (DEBUG)")):
                cur = ov5_cave.read_cave(rom, addr, len(blob))
                if cur != blob:
                    ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                print(f"  ov5 {label} stub @0x{addr:08X}  {len(blob)} B")

        def check_fn(c, rom, view):
            ov = bytes(view.buf)

            def check(cond: bool, msg: str) -> None:
                c.ok(bool(cond), msg)

            # PART B
            check(_u32(ov, GOBLIN_FAN_LITERAL) == RETIRED_CID,
                  "PART B: Goblin Fan's stock flip-destroy effect is retired")

            # PART C
            cls0 = _keys(ov, CLS0_BASE, CLS0_COUNT, CLS0_STRIDE, True)
            check(len(cls0) == CLS0_COUNT, "PART C: cls0 count unchanged")
            check(all(cls0[i] <= cls0[i + 1] for i in range(CLS0_COUNT - 1)), "PART C: cls0 sorted")
            check(DONOR_CID in cls0, "PART C: donor owns a cls0 record")
            check(CLS0_DROP not in cls0, "PART C: phantom 0x0E1A spent")
            if DONOR_CID in cls0:
                i = cls0.index(DONOR_CID)
                slots = [_u32(ov, CLS0_BASE + i * CLS0_STRIDE + k) for k in (4, 8, 0xC, 0x10, 0x14)]
                check(slots == [CAVE_NAST_RES | 1, CAVE_NAST_PRED | 1, ACT_COND, 0, TARGET_DECL],
                      f"PART C: cls0 slots are the Bubble Shuffle template ({[hex(s) for s in slots]})")
            # the template card must not regress
            bs = cls0.index(0x1908)
            check(_u32(ov, CLS0_BASE + bs * CLS0_STRIDE + 4) == BUBBLE_SHUFFLE_RESOLVER
                  and _u32(ov, CLS0_BASE + bs * CLS0_STRIDE + 0x14) == TARGET_DECL,
                  "PART C: Bubble Shuffle 0x1908 unregressed")

            # PART D
            crit = _keys(ov, CRIT_BASE, CRIT_COUNT, CRIT_STRIDE, False)
            check(len(crit) == CRIT_COUNT, "PART D: criteria count unchanged")
            check(all(crit[i] <= crit[i + 1] for i in range(CRIT_COUNT - 1)), "PART D: criteria sorted")
            check(DONOR_CID in crit, "PART D: donor owns a criteria row")
            if DONOR_CID in crit:
                i = crit.index(DONOR_CID)
                row = (_u16(ov, CRIT_BASE + i * CRIT_STRIDE + 2),
                       _u32(ov, CRIT_BASE + i * CRIT_STRIDE + 4),
                       _u32(ov, CRIT_BASE + i * CRIT_STRIDE + 8))
                check(row == (CRIT_AUX, CAVE_NAST_CRIT | 1, CRIT_WORD),
                      f"PART D: criteria row is {[hex(x) for x in row]}")
            t = crit.index(0x1768)
            check(_u32(ov, CRIT_BASE + t * CRIT_STRIDE + 4) == 0x0223E769,
                  "PART D: Ninjitsu Art of Transformation's own row unregressed")

            # PART E
            leave = [_u16(ov, LEAVE_LIST + 2 * i) for i in range(LEAVE_N)]
            check(DONOR_CID in leave, "PART E: donor is in the leave-cleanup list")
            check(LEAVE_DROP not in leave, "PART E: phantom 0x0E42 spent")
            check(all(leave[i] < leave[i + 1] for i in range(LEAVE_N - 1)),
                  "PART E: leave-cleanup list still strictly sorted")
            check(0x1768 in leave and 0x1F75 in leave and 0x1D2F in leave,
                  "PART E: known leave-cleanup members unregressed")

            # PART H
            dest = build_dest_stub(CAVE_NAST_DEST)
            check(bytes(ov[_off(CAVE_NAST_DEST):_off(CAVE_NAST_DEST) + len(dest)]) == dest,
                  "PART H: the ov3 destination stub matches the rebuilt blob")
            check(bytes(ov[_off(BANISH_HOOK):_off(BANISH_HOOK) + 4])
                  == _thumb_bl(BANISH_HOOK, CAVE_NAST_DEST),
                  "PART H: 0x021CB48C calls it")
            check(_u16(ov, 0x021CB50A) == 0x200F,
                  "PART H: Escape from the Dark Dimension's own banish arm unregressed")

            # PART F -- re-derive the stubs so assert_thumb1_only runs again
            for addr, blob, label in ((CAVE_NAST_PRED, build_pred_stub(CAVE_NAST_PRED), "pred"),
                                     (CAVE_NAST_CRIT, build_crit_stub(CAVE_NAST_CRIT), "crit"),
                                     (CAVE_NAST_RES, build_resolver_stub(CAVE_NAST_RES), "resolver")):
                check(ov5_cave.read_cave(rom, addr, len(blob)) == blob,
                      f"PART F: ov5 {label} stub matches the rebuilt blob")

            # PART A
            mc, sec = _arm9_section(rom)
            d = bytes(sec.data)
            base = SETCODE_LIST - 0x02000000
            lst = [struct.unpack_from("<H", d, base + 2 * i)[0] for i in range(SETCODE_N)]
            check(DONOR_CID in lst, f"PART A: donor is in set code 0x2A -> Hanzo can search it ({[hex(x) for x in lst]})")
            check(SETCODE_DROP not in lst, "PART A: phantom 0x1C55 spent")
            check(all(lst[i] < lst[i + 1] for i in range(SETCODE_N - 1)),
                  "PART A: set code 0x2A still strictly sorted")
            cnt = struct.unpack_from("<H", d, SETCODE_COUNT_IMM - 0x02000000)[0]
            check(cnt == 0x2200 | SETCODE_N, "PART A: count immediate untouched")

        return Compiled(installs=(install,), posts=(apply_arm9_setcode,), checks=(check_fn,))


nast_effects = continuous_trap_target_ninja_and_opponent_monster_send_to_graveyard_special_summon_dragon_dinosaur_or_sea_serpent_from_deck_by_combined_level_banish_on_leave

SPEC = card(0x1255, nast_effects())

main, verify = dsl.make(SPEC, None, out="data/over_the_nexus/working/rom_nast.nds")

DONOR_CID = 0x1255          # Goblin Fan

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
