"""Elemental HERO Escuridao (DARK / Warrior / Fusion Effect / Level 8 / 2500 / 2000) on Elemental Hero Darkbright 0x1C08.

    1 "Elemental HERO" monster + 1 DARK monster
    Must be Fusion Summoned and cannot be Special Summoned by other ways. This card gains 100 ATK for each
    "Elemental HERO" monster in your Graveyard.
"""
import sys

from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class fusion_recipe_hero_plus_dark_gains_100_atk_per_elemental_hero_in_graveyard:
    """'1 "Elemental HERO" monster + 1 DARK monster; must be Fusion Summoned; gains 100 ATK for each "Elemental HERO"
    monster in your Graveyard' on a Fusion Effect donor that is already DARK / Warrior. Recipe row retargeted (two
    halfwords); the donor's own cls2 effect record retired in place (activation condition = the never-activate stub);
    its piercing (battle list overwritten with an order-preserving phantom) and Defense-Position flip (two code literal
    pools, ordered binary chain) dropped; the continuous +100 ATK is a 28 B block in the stat-recompute engine, re-run on
    every stat query, hosted in the dead leaf of phantom cid 0x0EC1 and entered by retargeting the one BL that cid 0x1C08
    leaves the chain on (ov3, so it works in puzzles too). Written by `install`, not as a stub: the host is native dead
    code, not a zeroed pool slot."""

    def compile(self, view, cid) -> Compiled:
        from otn_enhanced.rom.overlay_io import RAM_BASE
        DONOR_CID = cid
        FUSION_A_BASE = 0x02270B94  # RAM base of the 8-byte recipe rows
        FUSION_A_COUNT = 0xA1       # 161 -- ``movs r2,#0xa1`` @0x02231E92
        FUSION_A_STRIDE = 8         # ``movs r3,#8``          @0x02231E92
        FUSION_A_END = FUSION_A_BASE + FUSION_A_COUNT * FUSION_A_STRIDE   # == 0x0227109C

        # Material category codes (see the module docstring for the decoded leaves)
        MAT_ELEMENTAL_HERO = 31     # leaf 0x02231C74 -> set-code thunk 0x0202381C
        MAT_DARK = 37               # shared attribute leaf 0x02231CF2: attribute == code - 35

        # ---------------------------------------------------------------------------
        # cls2 dispatch table -- where Darkbright's stock effect record lives
        # ---------------------------------------------------------------------------
        CLS2_BASE = 0x02275C04      # from find_event_handler's selector arm (dispatch.cls_table_selector)
        CLS2_COUNT = 0x2B9          # 697 records
        CLS_STRIDE = 0x18           # 24 bytes, cid-first

        # Darkbright's stock record: "if this card inflicts battle damage, flip it face-down".
        NATIVE_CLS2 = (0x02204899, 0x021D882D, 0x0224A115, 0x00000000, 0x02234DA5)

        # Neutralised record: keep the cid (the table must stay sorted and 697 long -- the
        # count is a hard-coded immediate) and set the ACTIVATION CONDITION to the
        # engine's own "movs r0,#0; bx lr" never-activate stub. Slot3 returning 0 means
        # "cannot activate", so the effect can never be offered or resolved.
        NEVER_ACTIVATE = 0x0224A110  # 'movs r0,#0; bx lr' (dispatch.cls_slot_roles)
        DEAD_CLS2 = (0x00000000, 0x00000000, NEVER_ACTIVATE, 0x00000000, 0x00000000)

        # ---------------------------------------------------------------------------
        # The donor's OTHER two behaviours -- neither lives in a cls record
        # ---------------------------------------------------------------------------
        # Darkbright's stock text is FOUR clauses, and retiring the cls2 record only kills
        # the last one ("if destroyed, destroy 1 monster your opponent controls"):
        #   1. cannot be Special Summoned except by Fusion Summon  -> KEEP (this is clause 2)
        #   2. piercing battle damage                              -> membership of a LIST
        #   3. changes to Defense Position after attacking         -> a cid-comparison CHAIN
        #   4. on-destruction destroy                              -> the cls2 record
        #
        # (2) PIERCING: the battle-attribute piercing cid list (battle.pierce_list) is a
        # sorted u16 array whose length is a hard-coded immediate, so an entry cannot be
        # deleted -- it is OVERWRITTEN with a phantom cid that preserves the sort order.
        PIERCE_LIST = 0x0226D764     # 49 sorted entries
        PIERCE_COUNT = 49
        PIERCE_PHANTOM = 0x1B8E      # unused cid, strictly between the neighbours 0x1B86 and 0x1C54

        # (3) DEFENSE-POSITION FLIP: implemented in code, not data. Two functions compare
        # the acting cid against the family {0x14D6 Spear Dragon, 0x1993 Axe Dragonute,
        # 0x1C08 Darkbright, 0x1DA6 Arcana Force EX - The Dark Ruler, 0x237F Power
        # Breaker} -- every one of them a "switches to Defense Position after attacking"
        # card. Each function loads the cids from its literal pool, so removing Darkbright
        # is a 4-byte edit of the pool word at each site. The comparison is an ORDERED
        # binary chain (bgt / bge / beq), so the replacement must keep the same position
        # in the ordering or the search would mis-route the OTHER four cards: 0x1994 sits
        # strictly between 0x1993 and 0x1DA6 and belongs to no card.
        DEFPOS_LITERALS = (0x021C62DC, 0x022526D8)   # pool words loaded @0x021C6150 / @0x02252542
        DEFPOS_PHANTOM = 0x1994
        DEFPOS_FAMILY = (0x14D6, 0x1993, 0x1C08, 0x1DA6, 0x237F)

        # Darkbright's stock recipe: "Elemental Hero Sparkman" + "Elemental Hero Necroshade"
        NATIVE_MATERIALS = (0x18A9, 0x197F, 0x0000)
        NEW_MATERIALS = (MAT_ELEMENTAL_HERO, MAT_DARK, 0x0000)

        # ---------------------------------------------------------------------------
        # CLAUSE 3 -- "gains 100 ATK for each 'Elemental HERO' monster in your Graveyard"
        # ---------------------------------------------------------------------------
        # NOT the ATK/DEF delta tables. Those carry a rider node whose amount is written
        # once at attach time (node+4, read by the walker at 0x021B5FD0), and the printed
        # text of all 51 of delta-table-2's +-1 sentinel rows is activated or event-driven
        # ("Once per turn: ... gains N ATK for each", "during the Damage Step only") --
        # not one is a continuous "for each X currently in your GY". Routing Escuridao
        # through it would freeze its ATK at whatever the GY held when it fired.
        #
        # Continuous per-card stats live in STAT_RECOMPUTE, which is re-run on every stat
        # query, so anything routed through it is continuous by construction. It carries
        # 182 per-cid arms; the cid is in R2, the running bonus in R4, and the frame slot
        # [SP+0xC] is the side.
        STAT_RECOMPUTE = 0x021B44C0     # (side, zone, out, flag) -> live ATK/DEF into *out*
        GY_SETCODE_COUNT = 0x021B18E0   # (side, thunk) -> # MONSTERS in own GY matching thunk
        EHERO_THUNK = 0x0202381D        # "Elemental HERO" set-code thunk (Thumb bit set)
        MUL100_TAIL = 0x021B557E        # movs r1,#0x64 ; muls r1,r0,r1 ; adds r4,r4,r1 ; -> CHAIN_CONTINUE
        CHAIN_CONTINUE = 0x021B5E6E     # the engine's shared continuation (entered by BL, never returns)

        # Masked HERO Goka 0x236B is the same card shape -- "Gains 100 ATK for each 'HERO'
        # monster in your GY" -- and its leaf 0x021B5DC4 is exactly
        #     ldr r0,[sp,#0xc] ; ldr r1,=0x02023975 ; bl GY_SETCODE_COUNT ; bl MUL100_TAIL
        # Escuridao's leaf is that with the "HERO" thunk swapped for the "Elemental HERO"
        # one. These are the reference sites; the patch must leave them untouched.
        GOKA_CID = 0x236B
        GOKA_ARM = 0x021B535A
        GOKA_LEAF = 0x021B5DC4
        GOKA_LEAF_BYTES = bytes.fromhex("0398" "2349" "fbf78afd" "fff7d7fb")

        # WHERE 0x1C08 LEAVES THE CHAIN. A CFG walk with constant propagation (the arms
        # encode cids as `base +- imm`, so they cannot be grepped -- thumb.stack_based_switch)
        # lands cid 0x1C08 on the fall-through BL of the 0x1C09 (E-HERO Magma Neos) node:
        #
        #   021B5122  subs r0,#0x59      ; r0 = 0x1C62 - 0x59 = 0x1C09
        #   021B5124  cmp  r2,r0
        #   021B5126  bne  0x021B512C
        #   021B5128  bl   0x021B5ADE    ; Magma Neos' own leaf -- untouched
        #   021B512C  bl   CHAIN_CONTINUE  <-- 0x1C08 exits here; retargeted at ESC_BLOCK
        #
        # 0x021B512C has exactly ONE predecessor (the bne above), verified by a
        # predecessor scan of the whole function.
        HOOK_SITE = 0x021B512C
        HOOK_ORIG = bytes.fromhex("00f09ffe")            # bl CHAIN_CONTINUE
        # The routing node, pinned byte-for-byte so any drift in the chain is caught.
        ROUTE_NODE = 0x021B5106
        ROUTE_NODE_BYTES = bytes.fromhex(
            "a748" "8242" "18dc" "01db" "00f0f6fc"        # cmp r2,0x1C62 / bgt / blt / bl
            "011c" "5339" "8a42" "0adc"                   # r1 = 0x1C0F ; cmp ; bgt
            "011c" "5339" "8a42" "09da"                   # r1 = 0x1C0F ; cmp ; bge
            "5938" "8242" "01d1" "00f0d9fc"               # r0 = 0x1C09 ; cmp ; bne ; bl leaf
        )

        # WHERE THE NEW CODE GOES -- no cave, no canary, no card sacrificed.
        # 16 of the engine's 182 arms name cids that do NOT exist in the ROM's own
        # card_prop.bin (4305 records), so their `cmp r2,<cid>` can never match and their
        # leaves are unreachable. The largest such block is the leaf of the phantom arm
        # 0x0EC1 (arm 0x021B4CC0, dead call at 0x021B4CC4): 44 contiguous free bytes,
        # entered from nowhere else and containing no literal-pool word. Being ov3, it is
        # resident in EVERY duel mode including puzzles (mem.ov3_resident_all_modes) --
        # unlike an ov5 stub, which a puzzle's overlay 41 would evict.
        ESC_BLOCK = 0x021B54E0
        ESC_BLOCK_FREE = 44
        ESC_PHANTOM_CID = 0x0EC1        # the non-existent card whose dead leaf this was
        ESC_BLOCK_ORIG = bytes.fromhex(
            "a149" "0c98" "0858" "0028" "40d1" "0398" "f7f71cfd"
            "0128" "3bd1" "0398" "0121" "081a" "1290"
        )                                                 # first 28 B of the dead leaf

        def find_fusion_row(ov: bytes, cid: int) -> int:
            """Return the overlay-3 file offset of *cid*'s recipe row in table A."""
            base = FUSION_A_BASE - RAM_BASE
            for i in range(FUSION_A_COUNT):
                off = base + i * FUSION_A_STRIDE
                if struct.unpack_from("<H", ov, off)[0] == cid:
                    return off
            raise RuntimeError(f"cid 0x{cid:04X} has no fusion recipe row in table A")


        def find_cls2_row(ov: bytes, cid: int) -> int:
            """Return the overlay-3 file offset of *cid*'s cls2 record (or raise)."""
            base = CLS2_BASE - RAM_BASE
            for i in range(CLS2_COUNT):
                off = base + i * CLS_STRIDE
                if struct.unpack_from("<I", ov, off)[0] == cid:
                    return off
            raise RuntimeError(f"cid 0x{cid:04X} not found in cls2")


        def build_esc_block(base: int = ESC_BLOCK) -> bytes:
            """Assemble clause 3's stat-engine block (Thumb-1, 28 bytes incl. its pool).

            Entered by the retargeted ``BL`` at :data:`HOOK_SITE`, so ``SP`` is still
            :data:`STAT_RECOMPUTE`'s own frame and ``[SP+0xC]`` is the side -- exactly as
            the native leaves read it.  ``R0..R3`` are scratch there; ``R4`` (the running
            bonus) and ``R7`` (the out struct) are left alone.

            Every path ends in a call that never returns, so the block needs no epilogue:
            a match tail-calls :data:`MUL100_TAIL` (which multiplies, adds into R4 and
            falls into the engine's continuation), and a non-match performs exactly the
            ``BL CHAIN_CONTINUE`` that was displaced.  That also makes the block harmless
            on its *other* inbound edge -- the dead phantom call at 0x021B4CC4 -- which
            would take the non-match path and so behave identically to the original.
            """
            a = EffectBuilder()
            (a
             .ldr_const(0, DONOR_CID)                 # r0 = 0x1C08
             .insn("CMP", "R2, R0")                   # r2 = the cid being recomputed
             .insn("BNE", "not_us")
             .insn("LDR", "R0, [SP, #0xC]")           # r0 = side (the engine's frame slot)
             .ldr_const(1, EHERO_THUNK)               # r1 = "Elemental HERO" set-code thunk
             .bl(GY_SETCODE_COUNT)                    # r0 = # E-HERO monsters in that GY
             .insn("B", f"0x{MUL100_TAIL:08X}")       # x100 -> r4 -> continuation
             .label("not_us")
             .bl(CHAIN_CONTINUE))                     # the displaced original
            blob = a.assemble(base)
            assert_thumb1_only(blob, base)             # never trust a bare capstone disasm
            if len(blob) > ESC_BLOCK_FREE:
                raise RuntimeError(
                    f"clause-3 block is {len(blob)} B, only {ESC_BLOCK_FREE} B are free "
                    f"at 0x{base:08X}")
            return blob


        def _thumb_bl_bytes(site: int, target: int) -> bytes:
            """Encode the two-halfword ARMv4T ``BL`` at *site* branching to *target*."""
            off = (target - (site + 4)) & 0x7FFFFF
            if not (-(1 << 22) <= target - (site + 4) < (1 << 22)):
                raise ValueError(f"BL 0x{site:08X} -> 0x{target:08X} out of range")
            return struct.pack("<2H", 0xF000 | (off >> 12), 0xF800 | ((off >> 1) & 0x7FF))

        def apply_overlay(ov):
            off = find_fusion_row(ov, DONOR_CID)
            ram = FUSION_A_BASE + (off - (FUSION_A_BASE - RAM_BASE))
            before = struct.unpack_from("<4H", ov, off)
            print(f"fusion recipe row @0x{ram:08X} (table A row {(off - (FUSION_A_BASE - RAM_BASE)) // 8})")
            print("  before: " + " ".join(f"0x{v:04X}" for v in before))

            if before[1:] not in (NATIVE_MATERIALS, NEW_MATERIALS):
                raise RuntimeError(
                    f"Darkbright's recipe is not in the expected native state "
                    f"({' '.join(f'0x{v:04X}' for v in before)}); wrong base ROM?")

            struct.pack_into("<4H", ov, off, DONOR_CID, *NEW_MATERIALS)
            after = struct.unpack_from("<4H", ov, off)
            print("  after : " + " ".join(f"0x{v:04X}" for v in after)
                  + "   (= 1 \"Elemental Hero\" monster + 1 DARK monster)")

            # count-neutrality guard: the table must still be sorted and the same length
            base = FUSION_A_BASE - RAM_BASE
            cids = [struct.unpack_from("<H", ov, base + i * 8)[0] for i in range(FUSION_A_COUNT)]
            assert all(cids[i] < cids[i + 1] for i in range(len(cids) - 1)), \
                "fusion table A is no longer sorted -- binary search would break"
            print(f"  table A still {FUSION_A_COUNT} sorted rows, ends 0x{FUSION_A_END:08X}")

            # -- PART B: retire the donor's own effect (cls2, count-neutral) -----------
            coff = find_cls2_row(ov, DONOR_CID)
            cram = CLS2_BASE + (coff - (CLS2_BASE - RAM_BASE))
            cbefore = struct.unpack_from("<6I", ov, coff)
            print(f"\ndonor cls2 record @0x{cram:08X} (record {(coff - (CLS2_BASE - RAM_BASE)) // CLS_STRIDE})")
            print("  before: " + " ".join(f"+{k * 4:02X}=0x{cbefore[k]:08X}" for k in range(6)))
            if cbefore[1:] not in (NATIVE_CLS2, DEAD_CLS2):
                raise RuntimeError(
                    "Darkbright's cls2 record is not in the expected native state "
                    f"({' '.join(f'0x{v:08X}' for v in cbefore[1:])}); wrong base ROM?")
            struct.pack_into("<6I", ov, coff, DONOR_CID, *DEAD_CLS2)
            cafter = struct.unpack_from("<6I", ov, coff)
            print("  after : " + " ".join(f"+{k * 4:02X}=0x{cafter[k]:08X}" for k in range(6))
                  + "   (slot3 = never-activate stub; cid kept so cls2 stays sorted at 697)")

            cls2_cids = [struct.unpack_from("<I", ov, (CLS2_BASE - RAM_BASE) + i * CLS_STRIDE)[0]
                         for i in range(CLS2_COUNT)]
            assert all(cls2_cids[i] <= cls2_cids[i + 1] for i in range(len(cls2_cids) - 1)), \
                "cls2 is no longer sorted -- find_event_handler's binary search would break"

            # -- PART C: drop the donor's PIERCING (battle-attribute list membership) --
            lst = [struct.unpack_from("<H", ov, (PIERCE_LIST - RAM_BASE) + i * 2)[0]
                   for i in range(PIERCE_COUNT)]
            if DONOR_CID in lst:
                i = lst.index(DONOR_CID)
                struct.pack_into("<H", ov, (PIERCE_LIST - RAM_BASE) + i * 2, PIERCE_PHANTOM)
                print(f"\npiercing list @0x{PIERCE_LIST:08X}[{i}] (0x{PIERCE_LIST + i * 2:08X}): "
                      f"0x{DONOR_CID:04X} -> phantom 0x{PIERCE_PHANTOM:04X}")
            elif PIERCE_PHANTOM in lst:
                print(f"\npiercing already dropped (phantom 0x{PIERCE_PHANTOM:04X} present)")
            else:
                raise RuntimeError(f"neither 0x{DONOR_CID:04X} nor the phantom is in the piercing list")
            lst = [struct.unpack_from("<H", ov, (PIERCE_LIST - RAM_BASE) + i * 2)[0]
                   for i in range(PIERCE_COUNT)]
            assert all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)), \
                "piercing list is no longer sorted -- its binary search would break"
            print(f"  list still {PIERCE_COUNT} sorted entries (count-neutral)")

            # -- PART D: drop the donor's DEFENSE-POSITION FLIP (code literal pools) ---
            for site in DEFPOS_LITERALS:
                cur = struct.unpack_from("<I", ov, site - RAM_BASE)[0]
                if cur == DONOR_CID:
                    struct.pack_into("<I", ov, site - RAM_BASE, DEFPOS_PHANTOM)
                    print(f"defense-flip literal @0x{site:08X}: 0x{DONOR_CID:04X} -> "
                          f"phantom 0x{DEFPOS_PHANTOM:04X}")
                elif cur == DEFPOS_PHANTOM:
                    print(f"defense-flip literal @0x{site:08X}: already dropped")
                else:
                    raise RuntimeError(
                        f"defense-flip pool @0x{site:08X} holds 0x{cur:08X}, expected "
                        f"0x{DONOR_CID:04X}; wrong base ROM?")
            # the chain is an ordered binary search -- the phantom must keep its position
            others = sorted(c for c in DEFPOS_FAMILY if c != DONOR_CID)
            assert all(c < DEFPOS_PHANTOM for c in others if c < DONOR_CID) and \
                   all(c > DEFPOS_PHANTOM for c in others if c > DONOR_CID), \
                "the defense-flip phantom would re-order the comparison chain"
            print(f"  ordering preserved for the remaining family "
                  f"{', '.join(f'0x{c:04X}' for c in others)}")

            # -- PART E: clause 3 -- +100 ATK per E-HERO in your GY (continuous) -------
            blob = build_esc_block()

            # (E1) the routing node must still be the one the CFG walk measured
            node = bytes(ov[ROUTE_NODE - RAM_BASE:ROUTE_NODE - RAM_BASE + len(ROUTE_NODE_BYTES)])
            if node != ROUTE_NODE_BYTES:
                raise RuntimeError(
                    f"stat-engine routing node @0x{ROUTE_NODE:08X} changed "
                    f"({node.hex()}); cid 0x{DONOR_CID:04X} may no longer exit at "
                    f"0x{HOOK_SITE:08X}. Re-run the CFG walk before patching.")

            # (E2) the destination must still be the dead phantom leaf (or already ours)
            cur = bytes(ov[ESC_BLOCK - RAM_BASE:ESC_BLOCK - RAM_BASE + len(ESC_BLOCK_ORIG)])
            if cur == ESC_BLOCK_ORIG:
                ov[ESC_BLOCK - RAM_BASE:ESC_BLOCK - RAM_BASE + len(blob)] = blob
                print(f"\nclause 3 block @0x{ESC_BLOCK:08X}: {len(blob)} B written over the "
                      f"dead leaf of phantom cid 0x{ESC_PHANTOM_CID:04X} "
                      f"({ESC_BLOCK_FREE} B free)")
            elif cur[:len(blob)] == blob:
                print(f"\nclause 3 block @0x{ESC_BLOCK:08X}: already written ({len(blob)} B)")
            else:
                raise RuntimeError(
                    f"clause-3 host @0x{ESC_BLOCK:08X} is neither the phantom leaf nor "
                    f"our block ({cur.hex()}); another patch may have claimed it.")

            # (E3) route cid 0x1C08 into it
            hook = bytes(ov[HOOK_SITE - RAM_BASE:HOOK_SITE - RAM_BASE + 4])
            want = _thumb_bl_bytes(HOOK_SITE, ESC_BLOCK)
            if hook == HOOK_ORIG:
                ov[HOOK_SITE - RAM_BASE:HOOK_SITE - RAM_BASE + 4] = want
                print(f"chain exit @0x{HOOK_SITE:08X}: BL 0x{CHAIN_CONTINUE:08X} -> "
                      f"BL 0x{ESC_BLOCK:08X}")
            elif hook == want:
                print(f"chain exit @0x{HOOK_SITE:08X}: already retargeted")
            else:
                raise RuntimeError(
                    f"chain exit @0x{HOOK_SITE:08X} holds {hook.hex()}, expected "
                    f"BL 0x{CHAIN_CONTINUE:08X}; wrong base ROM?")

            # (E4) the template card must be untouched -- it shares every callee we use
            goka = bytes(ov[GOKA_LEAF - RAM_BASE:GOKA_LEAF - RAM_BASE + len(GOKA_LEAF_BYTES)])
            if goka != GOKA_LEAF_BYTES:
                raise RuntimeError(
                    f"Masked HERO Goka's leaf @0x{GOKA_LEAF:08X} changed ({goka.hex()})")
            print(f"  Masked HERO Goka 0x{GOKA_CID:04X} (the x100 template) unchanged")

        def check_ov(ov):
            ok = True
            # clause 1 -- the recipe row
            off = find_fusion_row(ov, DONOR_CID)
            row = struct.unpack_from("<4H", ov, off)
            if row[1:] == NEW_MATERIALS:
                print(f"PASS fusion recipe 0x{DONOR_CID:04X} = "
                      f"[E-HERO({MAT_ELEMENTAL_HERO}) + DARK({MAT_DARK})]")
            else:
                print(f"FAIL fusion recipe is {' '.join(f'0x{v:04X}' for v in row[1:])}")
                ok = False

            # count-neutrality -- still 161 sorted rows ending where the consumer expects
            base = FUSION_A_BASE - RAM_BASE
            cids = [struct.unpack_from("<H", ov, base + i * 8)[0] for i in range(FUSION_A_COUNT)]
            if all(cids[i] < cids[i + 1] for i in range(len(cids) - 1)):
                print(f"PASS fusion table A still {FUSION_A_COUNT} sorted rows "
                      f"(0x{FUSION_A_BASE:08X}..0x{FUSION_A_END:08X})")
            else:
                print("FAIL fusion table A unsorted -- binary search 0x02022E44 would break")
                ok = False

            # the five sibling attribute-HERO recipes must be untouched
            siblings = {0x1FBA: (31, 40), 0x1FC1: (30, 38), 0x2161: (31, 36),
                        0x2190: (31, 41), 0x24DF: (31, 39)}
            bad = []
            for cid, want in siblings.items():
                r = struct.unpack_from("<4H", ov, find_fusion_row(ov, cid))
                if r[1:3] != want:
                    bad.append(f"0x{cid:04X}")
            if bad:
                print(f"FAIL sibling attribute-HERO recipes changed: {', '.join(bad)}")
                ok = False
            else:
                print("PASS the five sibling attribute-HERO recipes are unchanged")

            # the donor's stock effect is retired, and cls2 is still sorted at 697
            row = struct.unpack_from("<6I", ov, find_cls2_row(ov, DONOR_CID))
            if row[1:] == DEAD_CLS2:
                print("PASS donor cls2 record retired (slot3 = never-activate stub)")
            else:
                print(f"FAIL donor cls2 still live: {' '.join(f'0x{v:08X}' for v in row[1:])}")
                ok = False
            cls2_cids = [struct.unpack_from("<I", ov, (CLS2_BASE - RAM_BASE) + i * CLS_STRIDE)[0]
                         for i in range(CLS2_COUNT)]
            if all(cls2_cids[i] <= cls2_cids[i + 1] for i in range(len(cls2_cids) - 1)):
                print(f"PASS cls2 still {CLS2_COUNT} sorted records")
            else:
                print("FAIL cls2 unsorted -- find_event_handler would break")
                ok = False

            # piercing dropped, list still sorted and the same length
            lst = [struct.unpack_from("<H", ov, (PIERCE_LIST - RAM_BASE) + i * 2)[0]
                   for i in range(PIERCE_COUNT)]
            if DONOR_CID not in lst and PIERCE_PHANTOM in lst and \
                    all(lst[i] < lst[i + 1] for i in range(len(lst) - 1)):
                print(f"PASS piercing dropped; list still {PIERCE_COUNT} sorted entries")
            else:
                print("FAIL piercing list: donor still present or ordering broken")
                ok = False

            # defense-position flip dropped at both code sites
            bad = [hex(s) for s in DEFPOS_LITERALS
                   if struct.unpack_from("<I", ov, s - RAM_BASE)[0] != DEFPOS_PHANTOM]
            if bad:
                print(f"FAIL defense-flip literal(s) not dropped: {', '.join(bad)}")
                ok = False
            else:
                print("PASS defense-position flip dropped at both literal pools")

            # clause 3 -- the stat-engine block, its routing, and its blast radius
            blob = build_esc_block()
            got = bytes(ov[ESC_BLOCK - RAM_BASE:ESC_BLOCK - RAM_BASE + len(blob)])
            if got == blob:
                print(f"PASS clause 3 block @0x{ESC_BLOCK:08X} ({len(blob)} B, Thumb-1)")
            else:
                print(f"FAIL clause 3 block @0x{ESC_BLOCK:08X} is {got.hex()}")
                ok = False

            hook = bytes(ov[HOOK_SITE - RAM_BASE:HOOK_SITE - RAM_BASE + 4])
            if hook == _thumb_bl_bytes(HOOK_SITE, ESC_BLOCK):
                print(f"PASS cid 0x{DONOR_CID:04X} routed from 0x{HOOK_SITE:08X} into the block")
            else:
                print(f"FAIL chain exit @0x{HOOK_SITE:08X} is {hook.hex()}")
                ok = False

            node = bytes(ov[ROUTE_NODE - RAM_BASE:ROUTE_NODE - RAM_BASE + len(ROUTE_NODE_BYTES)])
            if node == ROUTE_NODE_BYTES:
                print(f"PASS stat-engine routing node @0x{ROUTE_NODE:08X} intact "
                      f"(0x{DONOR_CID:04X} still exits at 0x{HOOK_SITE:08X})")
            else:
                print(f"FAIL routing node @0x{ROUTE_NODE:08X} drifted: {node.hex()}")
                ok = False

            # the three shared callees the block tail-calls must still be what we think
            callee_ok = True
            if struct.unpack_from("<H", ov, MUL100_TAIL - RAM_BASE)[0] != 0x2164:
                print(f"FAIL 0x{MUL100_TAIL:08X} is not `movs r1,#0x64` (the x100 tail)")
                callee_ok = ok = False
            goka = bytes(ov[GOKA_LEAF - RAM_BASE:GOKA_LEAF - RAM_BASE + len(GOKA_LEAF_BYTES)])
            if goka != GOKA_LEAF_BYTES:
                print(f"FAIL Masked HERO Goka's template leaf @0x{GOKA_LEAF:08X} changed")
                callee_ok = ok = False
            if callee_ok:
                print(f"PASS x100 tail 0x{MUL100_TAIL:08X} and Goka's template leaf unchanged")
            return ok


        def install(rom, view):
            apply_overlay(view.buf)

        def check(c, rom, view):
            c.ok(check_ov(bytearray(view.buf)), "recipe, cls2, piercing, defense-flip, stat block and its routing")

        return Compiled(installs=(install,), checks=(check,))



SPEC = card(0x1C08, fusion_recipe_hero_plus_dark_gains_100_atk_per_elemental_hero_in_graveyard())

PROPS = card_props("DARK", "Warrior", level=8, atk=2500, defense=2000, card_type="Fusion Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_escuridao.nds")

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--no-text" not in sys.argv)
