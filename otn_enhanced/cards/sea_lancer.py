"""Sea Lancer (WATER / Beast-Warrior / Effect Monster / Level 5 / 1300 / 1000) on Mermaid Archer 0x1FFC.

    You can target any number of your banished Fish, Sea Serpent, and Aqua-Type monsters; equip them to this card. This effect can only be used once
    while this card is face-up on the field. If this face-up card on the field would be destroyed, you can destroy 1 of those cards, instead. This
    card gains 1000 ATK while equipped with a monster(s) by this effect. (See card_text.CARD_TEXT[0x1FFC] for the full printed text.)
"""
import struct
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled, SRC
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.effects import cave3
from dataclasses import dataclass
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class ignition_equip_any_number_of_banished_fish_sea_serpent_aqua_to_self_once_while_face_up_destroy_equipped_instead_gain_1000_atk:
    """Sea Lancer (Mermaid Archer 0x1FFC, WATER / Beast-Warrior / Level 5 / 1300 / 1000): 'You can target any number of your banished Fish,
    Sea Serpent, and Aqua-Type monsters; equip them to this card. This effect can only be used once while this card is face-up on the field. If this
    face-up card on the field would be destroyed, you can destroy 1 of those cards, instead. This card gains 1000 ATK while equipped with a
    monster(s) by this effect.' E2 (the replacement) is the donor's own, unchanged. Everything lives in the ov3 pool: the E3 flat-grant gate and
    its per-computation reset (two BL hooks), the donor's cls3 record retargeted (multi-select slot 5, NULL slot 2, candidate-gated slot 3,
    the native Cyberdark resolver in slot 1 with four cid-gated detours), and the criteria-registry row. Original ov3-path code embedded verbatim
    (the ov5 clone builders and `apply_e1` are dropped: the card ships in the ov3 pool)."""

    def compile(self, view, cid) -> Compiled:
        import struct

        from otn_enhanced.asm.effect_builder import EffectBuilder
        from otn_enhanced.asm.effect_shim import lift_handler_to_builder
        from otn_enhanced.asm.effect_verify import assert_thumb1_only
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.data.card_stats import apply_stats_and_text
        from otn_enhanced.effects.common import thumb_bl
        from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3, RAM_BASE

        SRC = "data/over_the_nexus/working/rom_ov3_compact.nds"  # stock + step 0 (ov3 stubs need the freed runs)
        OUT = "data/over_the_nexus/working/rom_sea_lancer.nds"

        DONOR_CID = 0x1FFC                      # Mermaid Archer -- keep-cid, per the donor rule

        # --- E3: the ATK-grant leaf -------------------------------------------------
        ATK_LEAF_SITE = 0x021B75F8              # exclusive to cid 0x1FFC
        ATK_LEAF_TWIN = 0x021B7246              # look-alike belonging to another card -- never touch
        ATK_SWITCH_ARM = 0x021B74B0             # ldr r0,=0x1FFC ; cmp r2,r0
        ATK_SWITCH_LIT = 0x021B7700             # the 0x1FFC literal that arm loads
        ATK_ACCUMULATOR = 0x021B7226            # ldr r0,[sp,#0xB0]; adds r0,r0,r1; str r0,[sp,#0xB0]

        # movs r1,#0x32 ; lsls r1,r1,#4  ->  0x32 << 4 = 800   (Mermaid Archer's printed grant)
        ATK_NATIVE = bytes.fromhex("32210901")
        # movs r1,#0x7D ; lsls r1,r1,#3  ->  0x7D << 3 = 1000  (Sea Lancer's printed grant)
        ATK_PATCHED = bytes.fromhex("7D21C900")

        ATK_NATIVE_AMOUNT = 0x32 << 4           # 800
        ATK_PATCHED_AMOUNT = 0x7D << 3          # 1000

        # --- E3 round 2: FLAT +1000, not +1000 PER equipped card -------------------
        # The leaf is reached from 0x021B44C0 by two kinds of pass, both adding r1 to the accumulator
        # [sp+0xB0]: the HOLDER's own pass (once per computation) and one EQUIP-CONTRIBUTION pass per
        # equipped card.  GDB-measured discriminator: the stat block at r7.
        ATK_RESUME = 0x021B75FC                 # the leaf's own `b 0x021B7226`, kept
        ATK_STUB_RESERVE = 0x20
        # 0x021B44C0 zeroes its modifier accumulator here, exactly once per invocation.
        ATK_ACC_ZERO = 0x021B44EC               # `mov r4,#0 ; str r4,[sp,#0xB0]`
        ATK_ACC_ZERO_ORIG = bytes.fromhex("00242c94")
        ATK_ACC_SLOT = 0xB0                     # the accumulator's offset in that frame
        ATK_RESET_RESERVE = 0x20

        # --- E1: the donor's cls3 record ------------------------------------------
        CLS3_BASE = 0x02279D74                  # fourth cls table (descriptor[+5] == 3)
        CLS3_COUNT = 0x308                      # 776 records, stride 24, sorted by cid
        CLS3_STRIDE = 24
        CLS1_BASE = 0x022860D4      # dispatch.cls_tables: cls1, sorted, cid-first
        CLS1_COUNT = 0x535          # 1333 rows (hard-coded immediate in find_event_handler)
        DONOR_CLS3_ROW = 527                    # GDB-confirmed: cls3[527] is Mermaid Archer

        SLOT2_OFF, SLOT3_OFF, SLOT5_OFF = 0x08, 0x0C, 0x14
        SLOT3_NATIVE = 0x021F2461               # the donor's activation condition (once-per-turn etc.)
        CRIT_PROBE = 0x02243FE0                 # (side, cid, param) -> "is there a legal candidate?"
        CRIT_PARAM = 0x02234E78                 # (desc) -> the per-cid criteria parameter
        COND_RESERVE = 0x40
        SLOT2_NATIVE = 0x021E2071               # on-field "face-up Lv<=3 you control" predicate
        SLOT2_PATCHED = 0x00000000              # NULL -> invoker 0x0224A924 returns its default 1
        SLOT5_NATIVE = 0x02234D8D               # board picker thunk, prompt 0x7C (90 records share it)
        SLOT5_SINGLE = 0x02235605               # off-field list template -- records exactly ONE pick

        # --- E1: "any number" -- the MULTI-select target template -------------------
        MULTI_TEMPLATE = 0x02235700             # 0x02235604's multi-select sibling; loops its 3rd sub-step
        # Its prologue is a per-cid switch setting r4 (count code) and r6 (prompt id); the tail computes
        # max picks = r4 - 6 and min required = (r4 - 6 if 6 <= r4 <= 0x26 else 1). cid 0x1FFC has no case,
        # so it would take the default r4 = 8 = "exactly 2" and fizzle on a lone banished target. The clone
        # therefore overwrites three prologue halfwords to jump straight to the tail with fixed values.
        # !! The TRUE extent. detect_function_size stops at the `pop {..,pc}` at 0x02235946 and reports
        # 0x232, which is 0x11A bytes short: the code runs to 0x02235A40 and the trailing pool to
        # 0x02235A4C (0x02235A4C is the next function's `push`). Copying only 0x232 left the tail's
        # `ldr r7,[pc,#0x78]` (literal at +0x28C) reading past the blob -> r7 = 0 -> data abort. _lift's
        # pool-containment guard now enforces this rather than trusting the heuristic.
        MULTI_EXTENT = 0x34C
        MULTI_TAIL_OFF = 0x212                  # the tail (0x02235912) as an offset into the clone
        MULTI_PATCH_OFF = 0x06                  # first prologue halfword we overwrite (0x02235706)
        MULTI_ORIG_PROLOGUE = (0x8829,          # 0x02235706  ldrh r1,[r5,#0]   (the switch operand)
                               0x4892,          # 0x02235708  ldr  r0,[pc,#0x248]
                               0x2408,          # 0x0223570A  mov  r4,#0x8      (the default count code)
                               0x4E92,          # 0x0223570C  ldr  r6,[pc,#0x248] (the default prompt)
                               0x4281)          # 0x0223570E  cmp  r1,r0        (the switch begins)

        # DRAGUNITY KNIGHT - BARCHA 0x221B is the exact analogue and supplies both constants:
        # "you can select ANY NUMBER of Dragon-Type 'Dragunity' monsters in your Graveyard, and EQUIP
        # them to this card" -- an equip-any-number from an off-field list zone. Its cls1[1166] record is
        # +04 = 0x022186E5 (the very resolver we clone), +08 NULL, +14 = 0x02235701 (this template).
        # Its (r4, prompt) pair was obtained by CONCRETELY executing the switch for cid 0x221B -- real
        # numbers, real flags, branch taken or not -- NOT by walking the CFG symbolically. That matters:
        # an earlier symbolic pass followed BGT/BLT edges as if they were equality cases and invented the
        # pair (0x2A, 0x4C); 0x4C is a prompt id NO card uses, and shipping it froze the game. The
        # interpreter is sanity-checked against cards whose text pins the count exactly -- Pot of Avarice
        # 5, Miracle Dig 3, Gladiator's Return 3 -- see thumb-stack-based-switch-footgun.
        MULTI_COUNT_CODE = 0x47                 # Barcha's: max picks 0x47-6 = 65, min required 1
        MULTI_PROMPT = 0x0139                   # Barcha's prompt id (too wide for a MOV imm8, built below)
        MULTI_NEW_PROLOGUE = (0x2000 | (4 << 8) | MULTI_COUNT_CODE,      # mov r4,#0x47
                              0x2000 | (6 << 8) | 0x4E,                  # mov r6,#0x4E
                              0x0000 | (2 << 6) | (6 << 3) | 6,          # lsl r6,r6,#2   -> 0x138
                              0x3000 | (6 << 8) | 0x01,                  # add r6,#1      -> 0x139
                              0xE000 | (((MULTI_TAIL_OFF - (MULTI_PATCH_OFF + 8 + 4)) >> 1) & 0x7FF))
        assert (0x4E << 2) + 1 == MULTI_PROMPT, "the prompt-id construction no longer yields Barcha's id"
        SLOT5_PATCHED = ov5_cave.CAVE_SL_SELECT | 1
        MULTI_RESERVE = 0x360

        # --- E1: the criteria registry --------------------------------------------
        CRIT_BASE = 0x022713C4                  # stride 12, sorted by cid, searched by 0x02243B9C
        CRIT_COUNT = 0x56C                      # 1388 -- the literal at 0x02243DF8; must NOT change
        CRIT_STRIDE = 12
        CRIT_COUNT_LIT = 0x02243DF8             # where the binary search reads that count

        # ⚠️ THIS IS THE SAME TABLE boggart_knight.py calls POP_BASE (the "populate"/evolution
        # table), and several shipped patches ALREADY do count-neutral inserts into it -- the T.G. cards
        # consume 0x2346 / 0x2347 there. So ROW INDICES ARE NOT STABLE ACROSS THE CHAIN: on a clean ROM
        # 0x1FFC sorts to 883, but after the earlier patches it is 884. Everything below therefore
        # LOCATES its rows by cid at apply time instead of hardcoding an index. (Registering the phantom
        # under a new pool name "criteria_registry" also hid it from the collision guard -- it is now
        # claimed in the same "populate_table" pool the other patches use.)
        CRIT_PHANTOM_CID = 0x234F               # non-existent card; owns TWO rows, we drop the second
        CRIT_CLEAN_ROW_INDEX = 883              # documentation only: where 0x1FFC lands on an UNPATCHED rom
        CRIT_WORD = 0x00010002                  # the 3DS build's own param for Sea Lancer
        CRIT_AUX = 0xFFFF

        RACE_LIST = (8, 5, 14, 0)               # Fish, Sea Serpent, Aqua, zero terminator
        REGISTRAR = 0x0223C6AC                  # (side, cid, predicate, &list, criteria, type)
        RACE_PREDICATE = 0x0223C791             # scans a zero-terminated race list (Thumb bit set)
        CRIT_TYPE = 0x8                         # "read the banished zone", own side only, no SS gate
        UNICORN_BEACON_HANDLER = 0x02242E60     # the clone source
        UNICORN_BEACON_LIST = 0x022712DC        # {0x0B, 0x10, 0x00} -- the worked example

        # --- E1: the equip ACTION, cloned from the Cyberdarks ----------------------
        # See the ov5_cave.py comment for why. Round 1 kept the donor's resolver 0x0220BFFC and detoured its
        # pick read-back; the in-game test proved that resolver never moves a card at all, so round 2
        # replaces it outright with the Cyberdarks' 0x022186E4 (equip from an off-field LIST zone).
        SLOT1_OFF = 0x04
        SLOT1_NATIVE = 0x0220BFFD               # donor resolver -- ends on a UI-request post, no card move
        CYBERDARK_RESOLVER = 0x022186E4         # equip-from-Graveyard resolver (cls1[588..590])
        GY_LOCATOR = 0x021A2510                 # (side, ref) -> the ref's index within the Graveyard array

        # The four Graveyard-bound sites, as offsets into the two lifted blobs. An exhaustive scan of both
        # functions for zone-code immediates (0xE/0xF in any MOV/CMP) and container offsets
        # (0x55C/0x7B4/0x4E4/0x304/0x124) found these four and nothing else.
        LOC_COUNT_OFF = 0x10                    # `ldr r4,[r2,#0x14]` @0x021A2520 -- the GY count
        LOC_POOL_OFF = 0x44                     # pool word 0x55C   @0x021A2554
        EQP_ZONE_OFF = 0x172                    # `mov r1,#0xE`     @0x02218856 -- the source zone code
        EQP_POOL_OFF = 0x1E4                    # pool word 0x55C   @0x022188C8

        GY_ARRAY, BANISHED_ARRAY = 0x55C, 0x7B4         # player+... (ram.graveyard_and_banished_arrays)
        GY_COUNT_LDR = 0x6954                           # ldr r4,[r2,#0x14]  (GY count      = player+0x14)
        BANISHED_COUNT_LDR = 0x69D4                     # ldr r4,[r2,#0x1C]  (banished count = player+0x1C)
        GY_ZONE_MOV = 0x210E                            # mov r1,#0xE  (ram.container_for_zone_code: GY)
        BANISHED_ZONE_MOV = 0x210F                      # mov r1,#0xF  (                    : banished)

        # --- E1 round 1, RETIRED: the donor-resolver pick detour -------------------
        # Kept so the retirement is auditable and so verify() can assert the site was RESTORED.
        PICK_DETOUR = 0x0220C05C
        PICK_RESUME = 0x0220C07E
        PICK_DETOUR_LEN = PICK_RESUME - PICK_DETOUR         # 0x22 = 34 bytes
        PICK_REF_ACCESSOR = 0x02234964          # (desc, i) -> the recorded packed card ref
        PICK_ORIG_BLOCK = bytes.fromhex(
            "2649"      # 0220C05C  ldr  r1,[pc,#0x98]   ; 0xB3C
            "2748"      # 0220C05E  ldr  r0,[pc,#0x9c]   ; 0x0229AC94
            "5143"      # 0220C060  mul  r1,r2
            "4318"      # 0220C062  add  r3,r0,r1
            "1420"      # 0220C064  mov  r0,#0x14
            "321c"      # 0220C066  add  r2,r6,#0
            "4243"      # 0220C068  mul  r2,r0
            "3433"      # 0220C06A  add  r3,#0x34
            "9a58"      # 0220C06C  ldr  r2,[r3,r2]
            "a878"      # 0220C06E  ldrb r0,[r5,#0x2]
            "5304"      # 0220C070  lsl  r3,r2,#17
            "5200"      # 0220C072  lsl  r2,r2,#1
            "120e"      # 0220C074  lsr  r2,r2,#24
            "db0f"      # 0220C076  lsr  r3,r3,#31
            "5200"      # 0220C078  lsl  r2,r2,#1
            "011c"      # 0220C07A  add  r1,r0,#0
            "9a18"      # 0220C07C  add  r2,r3,r2
        )
        NOP = 0x46C0                            # `mov r8, r8` -- the canonical Thumb-1 NOP

        CRIT_STUB_RESERVE = 0x40
        RACELIST_RESERVE = 0x10
        LOCATE_RESERVE = 0x60
        EQUIP_RESERVE = 0x200

        # --- reskin -----------------------------------------------------------------
        # Donor's own printed stats, for the assertion in verify(): Level 3 / 1200 / 200.
        NEW_LEVEL = 5
        NEW_ATK = 1300
        NEW_DEF = 1000
        NEW_ATTRIBUTE = "WATER"                 # unchanged from the donor
        NEW_RACE = "Beast-Warrior"              # donor is Sea Serpent

        NEW_NAME = b"Sea Lancer"
        NEW_DESC = (                            # compact -- must fit the donor's smallest desc slot
            b"Equip your banished Fish/Sea Serpent/Aqua monsters to this card, once while "
            b"face-up. If this card would be destroyed, destroy 1 of them instead. "
            b"+1000 ATK while equipped."
        )
        from otn_enhanced.data.card_stats import TEXT_LANGS


        # ===========================================================================
        # E3 -- a FLAT +1000 while equipped (not +1000 per equipped card)
        # ===========================================================================
        def _build_atk_stub(addr: int = ov5_cave.CAVE_SL_ATK, flag: int = ov5_cave.CAVE_SL_ATKFLAG) -> bytes:
            """Set r1 = 1000 once per ATK computation, 0 on the per-equip passes.

            Replaces the leaf's `movs r1,#0x7D ; lsls r1,r1,#3`; the leaf's own
            `b 0x021B7226` (which does `[sp+0xB0] += r1`) is left in place and still runs.

            WHY: the leaf is reached from the ATK-compute function 0x021B44C0 by SEVERAL passes,
            each in its OWN frame (SP differs, so [sp+0xB0] is at a different address) with the
            totals summed upstream -- so a flat `movs r1,#1000` is applied once per pass.  The
            donor never revealed this because Mermaid Archer can only equip one monster; Sea
            Lancer equips any number, and 2 equips read 1300 + 2x1000 = 3300.

            THE PASS STRUCTURE, pinned by measuring ATK at three equip counts (savestates
            ml1/ml2/ml3 = 0/1/2 equips -> 1300 / 2300 / 3300) with an earlier build of this stub
            that granted on `[r7+0x3C] != 0` and produced exactly N x 1000:

                N == 0          NO passes at all -- nothing reaches the leaf when unequipped
                                (independently confirmed by the original donor recon: Mermaid
                                Archer unequipped reads base ATK)
                N >= 1          N + 1 passes:
                                  * N per-equip passes, [r7+0x3C] != 0
                                  * exactly ONE summary pass, [r7+0x3C] == 0

            So granting on `[r7+0x3C] == 0` fires exactly once whenever anything is equipped and
            never when nothing is -- flat for any count, no divide (1000/3 would give 999), no
            cross-frame state.

            !! The first build of this stub had the test INVERTED (it granted on != 0, i.e. on
            the per-equip passes) because a single GDB sample was read as "holder vs equip"
            by the look of the stat-block fields.  The arithmetic across three equip counts is
            what actually settled which side is which -- register semantics guessed from one
            sample are not evidence.

            LR is free here: the leaf branches straight into the accumulator and then the loop,
            and the function returns through its own stacked PC, so a BL never disturbs it.
            """
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R0}")                  # r0 is live in the caller; r1 is the leaf's own output
             .ldr_const(1, flag)
             .insn("LDR", "R0, [R1, #0x0]")
             .insn("CMP", "R0, #0x0")
             .insn("BNE", "none")                   # already granted this computation
             .insn("MOV", "R0, #0x1")
             .insn("STR", "R0, [R1, #0x0]")         # claim it
             .insn("MOV", "R1, #0x7D")
             .insn("LSL", "R1, R1, #0x3")           # 0x7D << 3 = 1000
             .insn("POP", "{R0}")
             .insn("BX", "LR")
             .label("none")
             .insn("MOV", "R1, #0x0")
             .insn("POP", "{R0}")
             .insn("BX", "LR"))
            code = a.assemble(addr)
            assert len(code) <= ATK_STUB_RESERVE, f"atk stub {len(code)}B > 0x{ATK_STUB_RESERVE:X}"
            assert_thumb1_only(code, addr)
            return code


        def _build_atk_reset(addr: int = ov5_cave.CAVE_SL_ATKRESET, flag: int = ov5_cave.CAVE_SL_ATKFLAG) -> bytes:
            """Replay `mov r4,#0 ; str r4,[sp,#0xB0]` and clear the once-per-computation flag.

            Hooked at 0x021B44EC, where 0x021B44C0 zeroes its own modifier accumulator -- so the
            flag is reset exactly once per invocation, which is precisely the scope over which
            the grant must be counted once.  BL does not move SP, so `str r4,[sp,#0xB0]` here
            writes the caller's slot exactly as the original instruction did.

            Register budget at this site: r2/r5/r6/r7 are live (r5,r6 used two instructions
            later, r2 at 0x021B44F6), r4 is being set to 0 anyway, and r3's value is already
            safe on the stack from the function's own `push {r3,...}` -- so r3 is the scratch.
            """
            a = EffectBuilder()
            (a
             .insn("MOV", "R4, #0x0")
             .insn("STR", f"R4, [SP, #0x{ATK_ACC_SLOT:X}]")   # the original store
             .ldr_const(3, flag)
             .insn("STR", "R4, [R3, #0x0]")                   # flag = 0
             .insn("BX", "LR"))
            code = a.assemble(addr)
            assert len(code) <= ATK_RESET_RESERVE, f"atk reset {len(code)}B > 0x{ATK_RESET_RESERVE:X}"
            assert_thumb1_only(code, addr)
            return code


        def _apply_atk_amount(ov: bytearray, atk: int = ov5_cave.CAVE_SL_ATK, reset: int = ov5_cave.CAVE_SL_ATKRESET) -> None:
            """Redirect Mermaid Archer's ATK-grant leaf to the flat-grant stub. Idempotent.

            Round 1 rewrote the leaf in place to +1000 (`7D21C900`); that is still the right
            AMOUNT but it is applied once per equipped card.  The leaf's 4 bytes now become a
            `bl` to CAVE_SL_ATK instead, which decides whether this pass contributes at all.
            """
            off = ATK_LEAF_SITE - RAM_BASE
            cur = bytes(ov[off:off + 4])
            want = thumb_bl(ATK_LEAF_SITE, atk)

            if cur == want:
                print(f"E3 ATK grant @0x{ATK_LEAF_SITE:08X}: already redirected -> no change")
                return
            assert cur in (ATK_NATIVE, ATK_PATCHED), (
                f"E3 ATK leaf @0x{ATK_LEAF_SITE:08X} = {cur.hex()} (expected Mermaid Archer's "
                f"{ATK_NATIVE.hex()} = +800, or round 1's {ATK_PATCHED.hex()} = +1000)")

            # The leaf is only ours because exactly one branch reaches it. Re-check the
            # switch arm before writing, so a drifted overlay can never be silently patched.
            assert struct.unpack_from("<I", ov, ATK_SWITCH_LIT - RAM_BASE)[0] == DONOR_CID, (
                f"switch literal @0x{ATK_SWITCH_LIT:08X} is not cid 0x{DONOR_CID:04X}")
            _assert_equal_arm_reaches_leaf(ov)
            # the leaf's tail must still be the `b` into the shared accumulator -- the stub relies on it
            assert struct.unpack_from("<H", ov, ATK_RESUME - RAM_BASE)[0] & 0xF800 == 0xE000, (
                f"the leaf tail @0x{ATK_RESUME:08X} is no longer a `b` into the accumulator")

            ov[off:off + 4] = want
            print(f"E3 ATK grant @0x{ATK_LEAF_SITE:08X}: -> bl 0x{atk:08X} "
                  f"(flat +{ATK_PATCHED_AMOUNT}, once per computation)")

            # ...and the once-per-computation reset, where the accumulator itself is zeroed
            roff = ATK_ACC_ZERO - RAM_BASE
            rcur = bytes(ov[roff:roff + 4])
            rwant = thumb_bl(ATK_ACC_ZERO, reset)
            if rcur != rwant:
                assert rcur == ATK_ACC_ZERO_ORIG, (
                    f"accumulator-zero site @0x{ATK_ACC_ZERO:08X} = {rcur.hex()} "
                    f"(expected {ATK_ACC_ZERO_ORIG.hex()} = mov r4,#0 / str r4,[sp,#0x{ATK_ACC_SLOT:X}])")
                ov[roff:roff + 4] = rwant
                print(f"E3 accumulator-zero @0x{ATK_ACC_ZERO:08X}: "
                      f"-> bl 0x{reset:08X} (clears the grant flag per computation)")

            # The look-alike four bytes at 0x021B7246 belong to a different card.
            assert bytes(ov[ATK_LEAF_TWIN - RAM_BASE:ATK_LEAF_TWIN - RAM_BASE + 4]) == ATK_NATIVE, (
                f"the twin @0x{ATK_LEAF_TWIN:08X} was modified -- it is NOT Mermaid Archer's")


        def _assert_equal_arm_reaches_leaf(ov: bytearray) -> None:
            """The `b` at 0x021B74B8 (equal arm of `cmp r2,=0x1FFC`) must still target the leaf."""
            site = ATK_SWITCH_ARM + 8                       # 0x021B74B8
            w = struct.unpack_from("<H", ov, site - RAM_BASE)[0]
            assert w & 0xF800 == 0xE000, f"equal arm @0x{site:08X} is not an unconditional B (0x{w:04X})"
            off = (w & 0x7FF) << 1
            off -= 0x1000 if off & 0x800 else 0
            assert site + 4 + off == ATK_LEAF_SITE, (
                f"equal arm @0x{site:08X} targets 0x{site + 4 + off:08X}, not the leaf 0x{ATK_LEAF_SITE:08X}")


        # ===========================================================================
        # E1 -- the ov5 stubs
        # ===========================================================================
        def _build_crit_handler(addr: int = ov5_cave.CAVE_SL_CRIT, racelist: int = ov5_cave.CAVE_SL_RACELIST) -> bytes:
            """Criteria-registry handler for cid 0x1FFC: a clone of Unicorn Beacon's 0x02242E60.

            Called as ``handler(r0 = &row, r1 = side, r2 = param)`` from 0x02243F38's
            ``blx [row+4]``.  It forwards to the generic list-zone registrar

                0x0223C6AC(r0 = side, r1 = cid, r2 = predicate, r3 = &value_list,
                           [sp+0] = criteria word, [sp+4] = type)

            Unicorn Beacon copies its list onto its own stack frame first; that is a
            compiler artifact — the predicate only ever READS the list, so we hand it the
            ov5 constant directly and keep the frame to the two stacked arguments.
            """
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, LR}")
             .insn("SUB", "SP, #0x8")               # room for the two stacked args
             .insn("LDRH", "R4, [R0, #0x0]")        # row.cid  (before r0 is clobbered)
             .insn("LDR", "R2, [R0, #0x8]")         # row.criteria
             .insn("STR", "R2, [SP, #0x0]")         # arg5 = criteria word
             .insn("MOV", "R2, #0x8")
             .insn("STR", "R2, [SP, #0x4]")         # arg6 = type (banished, own side only)
             .ldr_const(3, racelist)                    # arg4 = &{8, 5, 14, 0}
             .ldr_const(2, RACE_PREDICATE)              # arg3 = the race-list predicate
             .insn("ADD", "R0, R1, #0x0")           # arg1 = side
             .insn("ADD", "R1, R4, #0x0")           # arg2 = cid
             .bl(REGISTRAR)
             .insn("ADD", "SP, #0x8")
             .insn("POP", "{R4, PC}"))              # POP into PC, never LR
            code = a.assemble(addr)
            assert len(code) <= CRIT_STUB_RESERVE, f"crit handler {len(code)}B > 0x{CRIT_STUB_RESERVE:X}"
            assert_thumb1_only(code, addr)
            return code


        def _build_race_list() -> bytes:
            """{Fish 8, Sea Serpent 5, Aqua 14, 0} -- zero-terminated, u32 entries.

            The terminator convention is the predicate's ``cmp r1,#0 ; bgt`` loop at
            0x0223C7B8, and the widths match Unicorn Beacon's own list at 0x022712DC.
            """
            return struct.pack("<4I", *RACE_LIST)


        def _lift(ov: bytes, src: int, dest: int, retarget: dict[int, int] | None = None,
                  size: int | None = None) -> bytes:
            """Lift the ov3 function at *src* into a relocated copy for *dest*.

            Two guards, and the second is the one that matters:

            1. ``build(src)`` must equal the original bytes -- proves nothing was mis-decoded.
            2. EVERY ``LDR Rx,[PC,#imm]`` in the copy must resolve INSIDE the copy.

            Guard 1 alone is not enough, and trusting it cost an in-game round.
            ``detect_function_size`` under-reported the multi-select template by 0x11A bytes
            (it stops at an early ``POP {..,PC}`` before an inline literal pool).  A truncated
            lift still round-trips perfectly -- the prefix is genuine code -- so only guard 2
            catches it.  Relocated, the tail's ``ldr r7,[pc,#0x78]`` read past the end of the
            blob, got 0, and ``ldr r1,[r7]`` took a data abort: PC = 0xFFFF0108 with
            LR inside the clone, straight off the freeze savestate's ARM9 register block.

            *retarget* remaps BL destinations (used to point the resolver's locator call at
            our own clone).
            """
            b = lift_handler_to_builder(ov, src, size=size)
            identity = b.build(src)
            assert identity == ov[src - RAM_BASE:src - RAM_BASE + len(identity)], (
                f"lift of 0x{src:08X} is not byte-exact at its own address -- extent/decode drift")
            _assert_pools_contained(identity, src, len(identity))
            for i, (kind, val) in enumerate(b._ops):          # noqa: SLF001 -- no public retarget API
                if kind == "bl" and retarget and val in retarget:
                    b._ops[i] = (kind, retarget[val])
            return b.build(dest)


        def _assert_pools_contained(blob: bytes, base: int, size: int) -> None:
            """Every PC-relative literal load in *blob* must reach a word inside *blob*."""
            from otn_enhanced.asm.thumb_disasm import decode_thumb as _dt
            bad = []
            for ins in _dt(blob, base):
                if ins.mnemonic == "LDR" and "PC" in ins.operands and "#" in ins.operands:
                    imm = int(ins.operands.split("#")[1].rstrip("]"), 16)
                    pool = (((ins.addr + 4) & ~3) + imm) - base
                    if not (0 <= pool + 4 <= size):
                        bad.append((ins.addr - base, pool))
            assert not bad, (
                f"lift of 0x{base:08X} is TRUNCATED: {len(bad)} PC-relative load(s) reach past the "
                f"{size} (0x{size:X}) bytes copied -- e.g. +0x{bad[0][0]:X} wants a literal at "
                f"+0x{bad[0][1]:X}. Pass an explicit `size`; detect_function_size under-reports "
                f"functions with several POP{{..,PC}} returns or an inline pool.")


        def _sub_hw(blob: bytearray, off: int, old: int, new: int, what: str) -> None:
            got = struct.unpack_from("<H", blob, off)[0]
            assert got == old, f"{what}: +0x{off:X} = 0x{got:04X}, expected 0x{old:04X}"
            struct.pack_into("<H", blob, off, new)


        def _sub_word(blob: bytearray, off: int, old: int, new: int, what: str) -> None:
            got = struct.unpack_from("<I", blob, off)[0]
            assert got == old, f"{what}: +0x{off:X} = 0x{got:08X}, expected 0x{old:08X}"
            struct.pack_into("<I", blob, off, new)


        def _build_locator(ov: bytes, dest: int = ov5_cave.CAVE_SL_LOCATE) -> bytes:
            """0x021A2510 (ref -> Graveyard index) re-pointed at the banished array.

            Two substitutions: the count load (player+0x14 -> player+0x1C) and the array
            offset pool word (0x55C -> 0x7B4).  Both containers are packed u32 card words
            with the identical bit layout, so the scan loop itself is unchanged.
            """
            blob = bytearray(_lift(ov, GY_LOCATOR, dest))
            _sub_hw(blob, LOC_COUNT_OFF, GY_COUNT_LDR, BANISHED_COUNT_LDR, "locator count load")
            _sub_word(blob, LOC_POOL_OFF, GY_ARRAY, BANISHED_ARRAY, "locator array offset")
            assert len(blob) <= LOCATE_RESERVE, f"locator {len(blob)}B > 0x{LOCATE_RESERVE:X}"
            assert_thumb1_only(bytes(blob), dest)
            return bytes(blob)


        def _build_cond(addr: int = ov5_cave.CAVE_SL_COND) -> bytes:
            """Activation condition: the donor's, AND at least one legal banished candidate.

            Called as ``slot3(r0 = desc, r1 = arg)`` from 0x0224AD94, which returns
            ``slot3(...) > 0`` (slot2 is NULL for this record, so its branch is skipped) — i.e.
            THIS SHIM ALONE decides activation legality.

            Without the candidate half the effect was activatable with an empty banished pile:
            the target template found nothing, returned "step complete" without recording a
            pick, and the equip resolver then read pick 0 out of an uninitialised descriptor
            and froze.

            !! THE desc[+7] GATE IS LOAD-BEARING, and leaving it out cost an in-game round.
            0x0224AD94 is called TWICE: once by the menu when deciding whether to offer the
            effect, and again BY THE MULTI-SELECT TEMPLATE ITSELF at 0x0223599C (the single
            template 0x02235604 never does this, which is why round 2 did not hit it).
            In between, the activation state machine 0x02217F80 runs the COST (slot4) and then
            sets desc[+7] = 1 at 0x02217FB4.  The donor's condition 0x021F2460 requires
            0x021A10A0(side, slot) == 0xFFFF — an "effect not yet used this turn" marker — and
            the donor's cost 0x021E5060 consumes exactly that.  So the donor's condition is
            TRUE at menu time and FALSE on the re-check, and chaining it unconditionally made
            the template fizzle silently: "nothing happens".
            GDB-confirmed (scratch/gdb_sealancer_e1_trace.py): the `probe` breakpoint inside
            this shim hit ONCE with a candidate count of 2, and `fizzle_legal` then hit with
            r0 = 0 — the second call never reached the probe, so it bailed at the donor branch.
            desc[+7] distinguishes the two call sites exactly: 0 = menu, 1 = mid-activation.
            Skipping the donor's check mid-activation is safe — nothing the condition tests can
            change between the cost and the target step of one activation.
            """
            a = EffectBuilder()
            (a
             .insn("PUSH", "{R4, R5, LR}")
             .insn("ADD", "R4, R0, #0x0")           # r4 = descriptor (survives the calls)
             .insn("MOV", "R5, #0x1")               # default code when the donor check is skipped
             .insn("LDRB", "R0, [R4, #0x7]")        # "cost already run" -> we are mid-activation
             .insn("CMP", "R0, #0x0")
             .insn("BNE", "cand")                   # ...so the donor's HOPT marker is spent; skip it
             .insn("ADD", "R0, R4, #0x0")           # r1 still holds the caller's arg
             .bl(SLOT3_NATIVE & ~1)                 # the donor's condition (desc, arg) -> code
             .insn("CMP", "R0, #0x0")
             .insn("BEQ", "no")                     # already "cannot activate" -> keep that
             .insn("ADD", "R5, R0, #0x0")           # r5 = the donor's code
             .label("cand")
             .insn("ADD", "R0, R4, #0x0")
             .bl(CRIT_PARAM)                        # -> the per-cid criteria parameter
             .insn("ADD", "R2, R0, #0x0")
             .insn("LDRB", "R0, [R4, #0x2]")        # side
             .insn("LDRH", "R1, [R4, #0x0]")        # cid
             .bl(CRIT_PROBE)                        # -> number of legal candidates
             .insn("CMP", "R0, #0x0")
             .insn("BLE", "no")                     # nothing to equip -> not activatable
             .insn("ADD", "R0, R5, #0x0")           # otherwise the donor's code, unchanged
             .insn("POP", "{R4, R5, PC}")
             .label("no")
             .insn("MOV", "R0, #0x0")
             .insn("POP", "{R4, R5, PC}"))
            code = a.assemble(addr)
            assert len(code) <= COND_RESERVE, f"cond shim {len(code)}B > 0x{COND_RESERVE:X}"
            assert_thumb1_only(code, addr)
            return code




        # ===========================================================================
        # E1 -- the overlay-3 edits
        # ===========================================================================
        def _cls3_slot(row: int, slot: int) -> int:
            return CLS3_BASE + row * CLS3_STRIDE + slot


        def _crit_rows(ov: bytearray) -> list[tuple[int, int, int, int]]:
            return [struct.unpack_from("<HHII", ov, CRIT_BASE - RAM_BASE + i * CRIT_STRIDE)
                    for i in range(CRIT_COUNT)]


        def _apply_cls3_slots(ov: bytearray, slot1: int = ov5_cave.CAVE_SL_EQUIP | 1,
                              slot3: int = ov5_cave.CAVE_SL_COND | 1, slot5: int = SLOT5_PATCHED) -> None:
            """Retarget the donor's target-declaration slot and NULL its on-field predicate."""
            base = _cls3_slot(DONOR_CLS3_ROW, 0)
            cid = struct.unpack_from("<H", ov, base - RAM_BASE)[0]
            assert cid == DONOR_CID, (
                f"cls3[{DONOR_CLS3_ROW}] cid = 0x{cid:04X}, expected the donor 0x{DONOR_CID:04X} "
                f"-- the cls3 geometry drifted")

            for slot, native, patched, what in (
                    (SLOT5_OFF, SLOT5_NATIVE, slot5, "slot5 target declaration"),
                    (SLOT2_OFF, SLOT2_NATIVE, SLOT2_PATCHED, "slot2 on-field predicate"),
                    (SLOT1_OFF, SLOT1_NATIVE, slot1, "slot1 resolver -> equip action"),
                    (SLOT3_OFF, SLOT3_NATIVE, slot3, "slot3 cond -> +candidate gate")):
                addr = _cls3_slot(DONOR_CLS3_ROW, slot)
                cur = struct.unpack_from("<I", ov, addr - RAM_BASE)[0]
                if cur == patched:
                    print(f"E1 cls3[{DONOR_CLS3_ROW}] +0x{slot:02X} ({what}): already 0x{patched:08X}")
                    continue
                assert cur == native, (
                    f"cls3[{DONOR_CLS3_ROW}] +0x{slot:02X} = 0x{cur:08X}, expected 0x{native:08X}")
                struct.pack_into("<I", ov, addr - RAM_BASE, patched)
                print(f"E1 cls3[{DONOR_CLS3_ROW}] +0x{slot:02X} ({what}): "
                      f"0x{cur:08X} -> 0x{patched:08X}")


        def _crit_want(handler: int = ov5_cave.CAVE_SL_CRIT) -> tuple[int, int, int, int]:
            return (DONOR_CID, CRIT_AUX, handler | 1, CRIT_WORD)


        def _apply_crit_row(ov: bytearray, handler: int = ov5_cave.CAVE_SL_CRIT) -> None:
            """Count-neutral insert of the criteria row for cid 0x1FFC.

            The table is a FIXED sorted array of 1388 rows that 0x02243B9C binary-searches, so
            a row can only be added by dropping one.  Both the insertion point and the phantom
            row are LOCATED BY CID at apply time, never hardcoded: earlier patches in the chain
            insert into this same table (it is boggart_knight's POP_BASE), which shifts
            every index after their edits.
            """
            import bisect

            rows = _crit_rows(ov)
            want = _crit_want(handler)
            if want in rows:
                print(f"E1 criteria row for 0x{DONOR_CID:04X}: already inserted at "
                      f"[{rows.index(want)}]")
                return

            cids = [r[0] for r in rows]
            assert all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)), (
                "the table is not sorted on entry -- an earlier patch broke the binary-search "
                "precondition")
            assert DONOR_CID not in cids, f"cid 0x{DONOR_CID:04X} already has a row"

            insert_at = bisect.bisect_left(cids, DONOR_CID)
            phantom_rows = [i for i, c in enumerate(cids) if c == CRIT_PHANTOM_CID]
            assert len(phantom_rows) >= 2, (
                f"phantom 0x{CRIT_PHANTOM_CID:04X} has {len(phantom_rows)} row(s), need >= 2 so that "
                f"dropping one cannot orphan a cid -- another patch probably took it")
            drop = phantom_rows[-1]

            if drop > insert_at:
                new = rows[:insert_at] + [want] + rows[insert_at:drop] + rows[drop + 1:]
            else:
                new = rows[:drop] + rows[drop + 1:insert_at] + [want] + rows[insert_at:]
            assert len(new) == CRIT_COUNT, f"insert was not count-neutral ({len(new)} rows)"
            ncids = [r[0] for r in new]
            assert all(ncids[i] <= ncids[i + 1] for i in range(len(ncids) - 1)), \
                "the table lost its sort order"

            for i, r in enumerate(new):
                struct.pack_into("<HHII", ov, CRIT_BASE - RAM_BASE + i * CRIT_STRIDE, *r)
            print(f"E1 criteria row: inserted {{0x{DONOR_CID:04X}, 0x{CRIT_AUX:04X}, "
                  f"0x{want[2]:08X}, 0x{CRIT_WORD:08X}}} at [{insert_at}]"
                  f"{'' if insert_at == CRIT_CLEAN_ROW_INDEX else f' (clean-ROM index would be {CRIT_CLEAN_ROW_INDEX}; earlier patches shifted it)'}"
                  f", dropped phantom 0x{CRIT_PHANTOM_CID:04X} at [{drop}]")

            lit = struct.unpack_from("<I", ov, CRIT_COUNT_LIT - RAM_BASE)[0]
            assert lit == CRIT_COUNT, f"table count literal changed to 0x{lit:X}"


        def _retire_pick_detour(ov: bytearray) -> None:
            """Round 1's detour over 0x0220C05C must be RESTORED, not left installed.

            The clone (CAVE_SL_EQUIP) calls 0x02234964 itself, so the detour is dead code —
            and restoring it takes the 18 cls records that share 0x0220BFFC out of this
            patch's blast radius entirely.
            """
            off = PICK_DETOUR - RAM_BASE
            cur = bytes(ov[off:off + PICK_DETOUR_LEN])
            if cur == PICK_ORIG_BLOCK:
                return                                          # clean ROM, or already restored
            stale = bytearray(thumb_bl(PICK_DETOUR, ov5_cave.CAVE_SL_PICK))
            while len(stale) < PICK_DETOUR_LEN:
                stale += struct.pack("<H", NOP)
            assert cur == bytes(stale), (
                f"resolver block @0x{PICK_DETOUR:08X} = {cur.hex()} is neither the original "
                f"nor round 1's detour -- refusing to guess")
            ov[off:off + PICK_DETOUR_LEN] = PICK_ORIG_BLOCK
            print(f"E1 round-1 pick detour @0x{PICK_DETOUR:08X}: RETIRED (original bytes restored)")



        # ===========================================================================
        # E1 in the ov3 pool (main(ov3=True)) -- 1592 B of ov5 shrunk to ~330 B
        # ===========================================================================
        # ov3 is resident wherever these natives are, so the two big clones are no longer needed:
        #  * SELECT: 0x02235700's prologue replayed + Barcha's (r4, r6) + `bl` straight into the native tail
        #    0x02235912 (soul_charge's in-game-confirmed shape). Every pre-tail path of the template
        #    enters the tail only there, and the tail never branches back into the cid switch.
        #  * EQUIP: slot1 -> the NATIVE Cyberdark resolver 0x022186E5, with cid-gated detours at its four
        #    Graveyard-bound sites (dispatch KB fact @0x022186E4). For any cid but 0x1FFC each detour does
        #    exactly what the native instructions did; for 0x1FFC it picks the banished array / zone 0xF /
        #    banished locator., normal duel AND puzzle ('All good... There rest are good to ship') (default).
        EQP_LOC_SITE = 0x022187A2       # bl 0x021A2510 (GY locator)
        EQP_ARR1_SITE = 0x022187C8      # ldr r0,=0x55C ; ldr r0,[r1,r0]
        EQP_ARR2_SITE = 0x022187FC      # ldr r1,=0x55C ; ldr r1,[r2,r1]
        EQP_ZONE_SITE = 0x02218854      # str r1,[sp,#8] ; movs r1,#0xE
        EQP_NATIVE = {EQP_ARR1_SITE: bytes.fromhex("3f480858"), EQP_ARR2_SITE: bytes.fromhex("32495158"),
                      EQP_ZONE_SITE: bytes.fromhex("02910e21")}
        MULTI_TAIL = MULTI_TEMPLATE + MULTI_TAIL_OFF        # 0x02235912


        def _sl3() -> dict[str, int]:
            from otn_enhanced.effects import cave3 as c
            return dict(crit=c.CAVE3_SL_CRIT, racelist=c.CAVE3_SL_RACELIST, locate=c.CAVE3_SL_LOCATE,
                        locsel=c.CAVE3_SL_LOCSEL, arr1=c.CAVE3_SL_ARR1, arr2=c.CAVE3_SL_ARR2, zone=c.CAVE3_SL_ZONE,
                        select=c.CAVE3_SL_SELECT, cond=c.CAVE3_SL_COND, atk=c.CAVE3_SL_ATK,
                        atkreset=c.CAVE3_SL_ATKRESET, atkflag=c.CAVE3_SL_ATKFLAG)


        def _sel3(base: int) -> bytes:
            b = EffectBuilder()
            b.insn("PUSH", "{R3, R4, R5, R6, R7, LR}")   # 0x02235700's own prologue
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("STR", "R1, [SP, #0x0]")
            b.insn("MOV", f"R4, #{MULTI_COUNT_CODE:#x}")  # Barcha: max 65 / min 1
            b.insn("MOV", "R6, #0x4E")
            b.insn("LSL", "R6, R6, #0x2")
            b.insn("ADD", "R6, #0x1")                     # prompt 0x139 (Barcha)
            b.bl(MULTI_TAIL)                              # LR is pushed: a plain jump; the tail pops pc
            return b.assemble(base, pad="nop")


        def _locsel3(base: int, locate: int) -> bytes:
            # A wrapper, not a tail call: the locator pushes/pops r3, so the CALLER's r3 survives the native
            # call and reaches the next external call -- it must survive this one too (proven by sl_equiv).
            # r2 is free: both locators write it before reading it.
            b = EffectBuilder()
            b.insn("PUSH", "{R3, LR}")
            b.insn("LDRH", "R2, [R4, #0x0]")              # r4 = desc (resolver +0x04)
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R2, R3")
            b.insn("BEQ", "ban")
            b.bl(GY_LOCATOR)                              # any other card: the native GY locator
            b.insn("POP", "{R3, PC}")
            b.label("ban")
            b.bl(locate)                                  # Sea Lancer: the banished locator
            b.insn("POP", "{R3, PC}")
            return b.assemble(base, pad="nop")


        def _arr1(base: int) -> bytes:      # replaces `ldr r0,=0x55C ; ldr r0,[r1,r0]`; every other register preserved
            b = EffectBuilder()
            b.insn("PUSH", "{R2, R3}")
            b.insn("LDRH", "R2, [R4, #0x0]")
            b.ldr_const(3, DONOR_CID)
            b.ldr_const(0, GY_ARRAY)
            b.insn("CMP", "R2, R3")
            b.insn("BNE", "gy")
            b.ldr_const(0, BANISHED_ARRAY)
            b.label("gy")
            b.insn("LDR", "R0, [R1, R0]")
            b.insn("POP", "{R2, R3}")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def _arr2(base: int) -> bytes:      # replaces `ldr r1,=0x55C ; ldr r1,[r2,r1]`; r0 live, r3 kept
            b = EffectBuilder()
            b.insn("PUSH", "{R3}")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R1, R3")
            b.ldr_const(1, GY_ARRAY)
            b.insn("BNE", "gy")
            b.ldr_const(1, BANISHED_ARRAY)
            b.label("gy")
            b.insn("LDR", "R1, [R2, R1]")
            b.insn("POP", "{R3}")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def _zone(base: int) -> bytes:      # replaces `str r1,[sp,#8] ; movs r1,#0xE`; r0/r2/r3 are the mover's args
            b = EffectBuilder()
            b.insn("STR", "R1, [SP, #0x8]")               # BL leaves SP alone: the caller's slot
            b.insn("PUSH", "{R2}")
            b.insn("LDRH", "R1, [R4, #0x0]")
            b.ldr_const(2, DONOR_CID)
            b.insn("CMP", "R1, R2")
            b.insn("BNE", "gy")
            b.insn("MOV", "R1, #0xF")                     # banished
            b.insn("B", "out")
            b.label("gy")
            b.insn("MOV", "R1, #0xE")                     # Graveyard (native)
            b.label("out")
            b.insn("POP", "{R2}")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        def _ov3_blobs(ov_clean: bytes) -> list[tuple[str, int, bytes]]:
            from otn_enhanced.effects import cave3
            A = _sl3()
            for k in ("crit", "racelist", "locate", "cond", "atk", "atkreset", "atkflag"):
                assert A[k] % 4 == 0, f"{k} needs a 4-aligned base (EffectBuilder / lifted pool / data word)"
            out = [("crit", A["crit"], _build_crit_handler(A["crit"], A["racelist"])),
                   ("racelist", A["racelist"], _build_race_list()),
                   ("locate", A["locate"], _build_locator(ov_clean, A["locate"])),
                   ("cond", A["cond"], _build_cond(A["cond"])),
                   ("atk", A["atk"], _build_atk_stub(A["atk"], A["atkflag"])),
                   ("atkreset", A["atkreset"], _build_atk_reset(A["atkreset"], A["atkflag"]))]
            for k, blob in (("select", _sel3(A["select"])), ("locsel", _locsel3(A["locsel"], A["locate"])),
                            ("arr1", _arr1(A["arr1"])), ("arr2", _arr2(A["arr2"])), ("zone", _zone(A["zone"]))):
                out.append((k, A[k], cave3._checked(A[k], 0x40, blob, "")))
            return out


        def _detours3() -> list[tuple[int, bytes, bytes]]:
            """(site, native 4 bytes, patched 4 bytes) for the four resolver detours."""
            A = _sl3()
            nat = dict(EQP_NATIVE)
            nat[EQP_LOC_SITE] = thumb_bl(EQP_LOC_SITE, GY_LOCATOR)
            tgt = {EQP_LOC_SITE: A["locsel"], EQP_ARR1_SITE: A["arr1"], EQP_ARR2_SITE: A["arr2"], EQP_ZONE_SITE: A["zone"]}
            return [(s, nat[s], thumb_bl(s, tgt[s])) for s in (EQP_LOC_SITE, EQP_ARR1_SITE, EQP_ARR2_SITE, EQP_ZONE_SITE)]


        def apply_e1_ov3(ov: bytearray, ov_clean: bytes) -> None:
            from otn_enhanced.effects import cave3
            A = _sl3()
            for name, addr, blob in _ov3_blobs(ov_clean):
                cave3.put(ov, addr, blob)
                print(f"E1 ov3 {name:9s} @0x{addr:08X} ({len(blob)}B)")
            o = A["atkflag"] - RAM_BASE
            assert bytes(ov[o:o + 4]) == bytes(4), "ATK grant flag word is not zero -- step 0 must run first"
            for site, nat, new in _detours3():
                cur = bytes(ov[site - RAM_BASE:site - RAM_BASE + 4])
                if cur != new:
                    assert cur == nat, f"resolver site @0x{site:08X} = {cur.hex()}, not native {nat.hex()} -- another patch owns it"
                    ov[site - RAM_BASE:site - RAM_BASE + 4] = new
                    print(f"E1 resolver detour @0x{site:08X}: {nat.hex()} -> {new.hex()}")
            _apply_crit_row(ov, A["crit"])
            _apply_cls3_slots(ov, slot1=CYBERDARK_RESOLVER | 1, slot3=A["cond"] | 1, slot5=A["select"] | 1)
            _retire_pick_detour(ov)


        # compile() also runs on the BUILT ROM (verify): lift the clone sources from bytes with the four resolver detours restored.
        _clean = bytearray(view.buf)
        for _site, _nat, _new in _detours3():
            _o = _site - RAM_BASE
            if bytes(_clean[_o:_o + 4]) == _new:
                _clean[_o:_o + 4] = _nat
        ov_clean = bytes(_clean)
        A = _sl3()
        blobs = _ov3_blobs(ov_clean)
        stubs = tuple((addr, blob, name) for name, addr, blob in blobs)

        def install(rom, view):
            ov = view.buf
            _apply_atk_amount(ov, A["atk"], A["atkreset"])
            o = A["atkflag"] - RAM_BASE
            assert bytes(ov[o:o + 4]) == bytes(4), "ATK grant flag word is not zero -- step 0 must run first"
            for site, nat, new in _detours3():
                cur = bytes(ov[site - RAM_BASE:site - RAM_BASE + 4])
                if cur != new:
                    assert cur == nat, f"resolver site @0x{site:08X} = {cur.hex()}, not native {nat.hex()} -- another patch owns it"
                    ov[site - RAM_BASE:site - RAM_BASE + 4] = new
            _apply_crit_row(ov, A["crit"])
            _apply_cls3_slots(ov, slot1=CYBERDARK_RESOLVER | 1, slot3=A["cond"] | 1, slot5=A["select"] | 1)
            _retire_pick_detour(ov)

        def check_fn(c, rom, view):
            def check(cond, msg):
                c.ok(bool(cond), msg)
                return bool(cond)

            ov = bytearray(view.buf)
            A3 = A
            ATK_ADDR, RESET_ADDR = A3["atk"], A3["atkreset"]

            leaf = bytes(ov[ATK_LEAF_SITE - RAM_BASE:ATK_LEAF_SITE - RAM_BASE + 4])
            check(leaf == thumb_bl(ATK_LEAF_SITE, ATK_ADDR),
                  f"E3 leaf @0x{ATK_LEAF_SITE:08X} = {leaf.hex()} (want bl -> 0x{ATK_ADDR:08X}, the FLAT +{ATK_PATCHED_AMOUNT} gate)")
            check(struct.unpack_from("<H", ov, ATK_RESUME - RAM_BASE)[0] & 0xF800 == 0xE000,
                  f"the leaf tail @0x{ATK_RESUME:08X} is still the `b` into the accumulator")
            acc = bytes(ov[ATK_ACC_ZERO - RAM_BASE:ATK_ACC_ZERO - RAM_BASE + 4])
            check(acc == thumb_bl(ATK_ACC_ZERO, RESET_ADDR),
                  f"accumulator-zero @0x{ATK_ACC_ZERO:08X} = {acc.hex()} (want bl -> 0x{RESET_ADDR:08X}, the per-computation flag reset)")
            twin = bytes(ov[ATK_LEAF_TWIN - RAM_BASE:ATK_LEAF_TWIN - RAM_BASE + 4])
            check(twin == ATK_NATIVE,
                  f"twin @0x{ATK_LEAF_TWIN:08X} = {twin.hex()} untouched (want {ATK_NATIVE.hex()} -- belongs to another card)")
            lit = struct.unpack_from("<I", ov, ATK_SWITCH_LIT - RAM_BASE)[0]
            check(lit == DONOR_CID, f"switch literal @0x{ATK_SWITCH_LIT:08X} = 0x{lit:04X} (want cid 0x{DONOR_CID:04X})")
            try:
                _assert_equal_arm_reaches_leaf(ov)
                check(True, f"equal arm @0x{ATK_SWITCH_ARM + 8:08X} still branches to the leaf")
            except AssertionError as exc:
                check(False, str(exc))
            acc = bytes(ov[ATK_ACCUMULATOR - RAM_BASE:ATK_ACCUMULATOR - RAM_BASE + 6])
            check(acc == bytes.fromhex("2c9840182c90"), f"accumulator tail @0x{ATK_ACCUMULATOR:08X} = {acc.hex()} intact")
            e2_lit = struct.unpack_from("<I", ov, 0x0225C494 - RAM_BASE)[0]
            check(e2_lit == DONOR_CID, f"E2 switch literal @0x0225C494 = 0x{e2_lit:04X} (want 0x{DONOR_CID:04X}, unmodified)")

            row_base = _cls3_slot(DONOR_CLS3_ROW, 0)
            check(struct.unpack_from("<H", ov, row_base - RAM_BASE)[0] == DONOR_CID,
                  f"cls3[{DONOR_CLS3_ROW}] is still cid 0x{DONOR_CID:04X}")
            for slot, want, what in (
                    (SLOT5_OFF, A3["select"] | 1, "slot5 -> multi-select"),
                    (SLOT2_OFF, SLOT2_PATCHED, "slot2 NULLed"),
                    (SLOT1_OFF, CYBERDARK_RESOLVER | 1, "slot1 -> native resolver + detours"),
                    (SLOT3_OFF, A3["cond"] | 1, "slot3 -> candidate-gated cond")):
                got = struct.unpack_from("<I", ov, _cls3_slot(DONOR_CLS3_ROW, slot) - RAM_BASE)[0]
                check(got == want, f"cls3[{DONOR_CLS3_ROW}] +0x{slot:02X} = 0x{got:08X} (want 0x{want:08X}, {what})")
            for nb, nb_cid in ((DONOR_CLS3_ROW - 1, 0x1FF6), (DONOR_CLS3_ROW + 1, 0x1FFD)):
                got = struct.unpack_from("<H", ov, _cls3_slot(nb, 0) - RAM_BASE)[0]
                check(got == nb_cid, f"cls3[{nb}] cid = 0x{got:04X} (want 0x{nb_cid:04X}, undisturbed)")

            rows = _crit_rows(ov)
            cids = [r[0] for r in rows]
            want = _crit_want(A3["crit"])
            at = rows.index(want) if want in rows else -1
            check(at >= 0, f"criteria row for 0x{DONOR_CID:04X} is present" + (f" at [{at}]" if at >= 0 else " -- NOT FOUND"))
            check(cids.count(DONOR_CID) == 1, f"exactly one criteria row for 0x{DONOR_CID:04X} (found {cids.count(DONOR_CID)})")
            check(all(cids[i] <= cids[i + 1] for i in range(len(cids) - 1)),
                  "criteria table is still sorted by cid (the binary search's precondition)")
            check(len(rows) == CRIT_COUNT and struct.unpack_from("<I", ov, CRIT_COUNT_LIT - RAM_BASE)[0] == CRIT_COUNT,
                  f"criteria table is still {CRIT_COUNT} rows and the count literal agrees")
            check(cids.count(CRIT_PHANTOM_CID) == 1,
                  f"phantom 0x{CRIT_PHANTOM_CID:04X} went 2 rows -> {cids.count(CRIT_PHANTOM_CID)} (paid for the insert)")
            check(at > 0 and rows[at - 1][0] == 0x1FFB and rows[at + 1][0] == 0x1FFD,
                  "the rows bracketing the insert are intact (0x1FFB | 0x1FFD)")
            check(cids.count(0x234E) >= 1, f"neighbouring phantom rows survive (0x234E x{cids.count(0x234E)})")
            ub = next((r for r in rows if r[0] == 0x231A), None)
            check(ub == (0x231A, 0xFFFF, UNICORN_BEACON_HANDLER | 1, 0x00950002),
                  f"Unicorn Beacon's row (the clone source) is untouched: {tuple(hex(x) for x in ub) if ub else None}")
            check(bytes(ov[PICK_DETOUR - RAM_BASE:PICK_DETOUR - RAM_BASE + PICK_DETOUR_LEN]) == PICK_ORIG_BLOCK,
                  f"round-1 pick detour @0x{PICK_DETOUR:08X} is retired (0x0220BFFC back to stock, so the 18 records sharing it are untouched)")

            for site, nat, new in _detours3():
                cur = bytes(ov[site - RAM_BASE:site - RAM_BASE + 4])
                check(cur == new, f"resolver detour @0x{site:08X} = {cur.hex()} (want {new.hex()})")
            ovr = bytearray(ov)
            for site, nat, _new in _detours3():
                ovr[site - RAM_BASE:site - RAM_BASE + 4] = nat
            ovb = bytes(ovr)
            for src, n, what in ((CYBERDARK_RESOLVER, 0x1F4, "Cyberdark equip resolver"),
                                 (GY_LOCATOR, 0x48, "Graveyard locator"),
                                 (MULTI_TEMPLATE, 0x232, "multi-select target template")):
                try:
                    b = lift_handler_to_builder(ovb, src).build(src)
                    check(b == ovb[src - RAM_BASE:src - RAM_BASE + len(b)] and len(b) == n,
                          f"clone source {what} @0x{src:08X} is untouched ({n}B)")
                except Exception as exc:
                    check(False, f"clone source {what} @0x{src:08X}: {exc}")
            cls1_rows = [CLS1_BASE + i * CLS3_STRIDE for i in range(CLS1_COUNT)]
            for cyber in (0x1AAE, 0x1AAF, 0x1AB0):
                found = [a for a in cls1_rows
                         if struct.unpack_from("<I", ov, a - RAM_BASE)[0] == cyber
                         and struct.unpack_from("<I", ov, a - RAM_BASE + SLOT1_OFF)[0] == CYBERDARK_RESOLVER | 1]
                check(len(found) == 1,
                      f"Cyberdark cid 0x{cyber:04X} still has exactly one cls1 row on the native resolver"
                      + (f" (@0x{found[0]:08X})" if len(found) == 1 else f" -- found {len(found)}"))

            from otn_enhanced.effects import cave3
            for name, addr, blob in _ov3_blobs(ovb):
                check(cave3.read_code(rom, ov, addr, len(blob)) == blob, f"ov3 {name} @0x{addr:08X} matches ({len(blob)}B)")
            loc = _build_locator(ovb, A3["locate"])
            check(struct.unpack_from("<H", loc, LOC_COUNT_OFF)[0] == BANISHED_COUNT_LDR
                  and struct.unpack_from("<I", loc, LOC_POOL_OFF)[0] == BANISHED_ARRAY,
                  "ov3 locator reads the BANISHED array (player+0x7B4) and its count (player+0x1C)")

        return Compiled(stubs=stubs, installs=(install,), checks=(check_fn,))


sea_lancer_effects = ignition_equip_any_number_of_banished_fish_sea_serpent_aqua_to_self_once_while_face_up_destroy_equipped_instead_gain_1000_atk

SPEC = card(0x1FFC, sea_lancer_effects())

PROPS = card_props("WATER", "Beast-Warrior", level=5, atk=1300, defense=1000)

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_sea_lancer.nds")

# Names the KB proofs read from this module (verbatim).
from otn_enhanced.asm.effect_verify import assert_thumb1_only  # noqa: E402,F401
from otn_enhanced.rom.overlay_io import RAM_BASE  # noqa: E402,F401

DONOR_CID = 0x1FFC                      # Mermaid Archer -- keep-cid
DONOR_CLS3_ROW = 527                    # GDB-confirmed: cls3[527] is Mermaid Archer


def _assert_pools_contained(blob: bytes, base: int, size: int) -> None:
    """Every PC-relative literal load in *blob* must reach a word inside *blob*."""
    from otn_enhanced.asm.thumb_disasm import decode_thumb as _dt
    bad = []
    for ins in _dt(blob, base):
        if ins.mnemonic == "LDR" and "PC" in ins.operands and "#" in ins.operands:
            imm = int(ins.operands.split("#")[1].rstrip("]"), 16)
            pool = (((ins.addr + 4) & ~3) + imm) - base
            if not (0 <= pool + 4 <= size):
                bad.append((ins.addr - base, pool))
    assert not bad, f"lift of 0x{base:08X} is TRUNCATED: {len(bad)} PC-relative load(s) reach past the {size} bytes copied"


if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
