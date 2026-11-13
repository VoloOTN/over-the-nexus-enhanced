"""Jet Warrior (FIRE / Warrior / Synchro Effect Monster / Level 5 / 2100 / 1200) on Ignition Beast Volcannon 0x23EB.

    "Jet Synchron" + 1 or more non-Tuner monsters
    If this card is Synchro Summoned: You can target 1 card your opponent controls; return it to the hand. If this card is in your GY: You can
    Tribute 1 Level 2 or lower monster; Special Summon this card in Defense Position, but banish it when it leaves the field. Each effect once per
    turn. (See card_text.CARD_TEXT[0x23EB] for the full printed text.)
"""
import sys

from otn_enhanced.effects.common import code_reaches
from otn_enhanced import dsl
from otn_enhanced.dsl import card, card_props, Compiled
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
from otn_enhanced.asm.effect_builder import EffectBuilder
from otn_enhanced.asm.effect_builder import R0
from otn_enhanced.asm.effect_builder import R1
from otn_enhanced.asm.effect_builder import R2
from otn_enhanced.asm.effect_builder import R4
from otn_enhanced.asm.effect_builder import R5
from otn_enhanced.asm.effect_builder import R6
from otn_enhanced.asm.effect_builder import R7
from dataclasses import dataclass
from otn_enhanced.effects.common import keys
import ndspy.rom
from otn_enhanced.effects import ov5_cave
from otn_enhanced.effects.common import rows
import struct


@dataclass(frozen=True)
class synchro_jet_synchron_and_non_tuners_return_opponent_card_to_hand_in_graveyard_tribute_level_2_or_lower_special_summon_defense_banish_on_leave:
    """Jet Warrior (Ignition Beast Volcannon 0x23EB, a vanilla Fusion monster made a Synchro Effect Monster from Laval Twin Slayer's card_prop
    template): '"Jet Synchron" + 1 or more non-Tuner monsters. If this card is Synchro Summoned: You can target 1 card your opponent controls; return
    it to the hand. If this card is in your GY: You can Tribute 1 Level 2 or lower monster; Special Summon this card in Defense Position, but banish it
    when it leaves the field. Each effect once per turn.' Fusion recipe killed, the named-material row (Jet Synchron) over a phantom, the donor's cls1
    record rewritten in place, a GY-action registry row, the cls2 record for clauses 2 + 3, the Defense Position hook, the shared timing-class and
    summon-rider hooks and the ov5 stubs; the card_prop template copy and card_genre tags are a post. Original code embedded verbatim (the legacy
    per-language description ladder is dropped: the card is in CARD_TEXT so the re-emit path ignores slots)."""

    def compile(self, view, cid) -> Compiled:
        import struct
        import ndspy.rom
        from otn_enhanced.asm import effect_verify
        from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE
        from otn_enhanced.rom.overlay_io import RAM_BASE
        from otn_enhanced.rom.pac import parse_pac
        from otn_enhanced.effects import ov5_cave
        from otn_enhanced.cards import boggart_knight as boggart
        from otn_enhanced.data.card_stats import iter_paths
        from otn_enhanced.effects import timing_class_hook as timinghook
        from otn_enhanced.effects import summon_rider_hook as riderhook
        from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R1, R2, R4, R5, R6, R7
        from otn_enhanced.effects.common import ov3_off as _off
        from otn_enhanced.data.card_stats import find_pac as _find_pac
        from otn_enhanced.effects.common import bl as _bl

        DONOR_CID = 0x23EB          # "Ignition Beast Volcannon" -- KEEPS this cid
        JET_SYNCHRON_CID = 0x224C   # jet_synchron's donor -- the NAMED material

        # ---------------------------------------------------------------------------
        # PARTS A + B -- identity
        # ---------------------------------------------------------------------------
        # Laval Twin Slayer is Lv5 / FIRE / Warrior / Synchro Effect Monster -- every
        # identity field except the stats is already Jet Warrior's.
        REFERENCE_SYNCHRO_CID = 0x23FE

        NEW_ATTRIBUTE = "FIRE"          # donor is EARTH
        NEW_RACE = "Warrior"            # donor is Machine
        NEW_LEVEL = 5                   # donor is 6 -- and the Level is now LIVE, because
                                        # can_synchro_summon 0x02249540 reads it via
                                        # 0x0202ABD8 to size the material search.
        NEW_ATK = 2100                  # donor is 2300
        NEW_DEF = 1200                  # donor is 1600
        NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Synchro Effect Monster"]        # 37

        GENRE_BIT_NOMI    = 21      # "Special Summon only"; already set on the donor
        GENRE_BIT_FUSION  = 29      # must be CLEARED
        GENRE_BIT_SYNCHRO = 36      # must be SET
        # NB: NO bit 35 (TUNER) -- Jet Warrior is a non-Tuner.  Accel Synchron needed it.

        DONOR_GENRE_STOCK = 0x0000000420200402      # bits {1, 10, 21, 29, 34}
        NEW_GENRE = ((DONOR_GENRE_STOCK & ~(1 << GENRE_BIT_FUSION))
                     | (1 << GENRE_BIT_SYNCHRO))
        assert DONOR_GENRE_STOCK >> GENRE_BIT_NOMI & 1, "donor should already be nomi-tagged"
        assert NEW_GENRE == 0x0000001400200402, f"genre target drifted: 0x{NEW_GENRE:016X}"


        # ---------------------------------------------------------------------------
        # PART D -- kill the donor's fusion recipe (for the UNGATED CPU AI planner)
        # ---------------------------------------------------------------------------
        # fusion.table_a: 161 rows of 8 bytes, {u16 result_cid, u16 m1, u16 m2, u16 m3},
        # sorted by result_cid and binary-searched with the count hardcoded as 161.  We
        # touch ONLY the material columns, so the cid column, the sort order and the row
        # count are all untouched.
        #
        # After the card_type flip the row is already dead on the PLAYER's path
        # (can_fusion_summon 0x0223298C hard-rejects at its first is_fusion check), but
        # the CPU AI special-summon planner at 0x022112B2 / 0x0221132E calls
        # is_extra_deck then fusion_material_count WITHOUT an is_fusion gate.
        #
        # /!\ Volcannon's materials are CATEGORY CODES, not cids: its printed recipe is
        # "1 Machine-Type monster + 1 Pyro-Type monster" and the row holds (7, 4).
        # fusion.code_classes: a slot >= 0x33 is read as a literal CID (the `cmp r0,#0x33`
        # at 0x02232146), and the max real cid is 0x24E8 -- so 0x3FFF can never match a
        # card, and being >= 0x33 it never enters that proof's category census either.
        FUSION_TABLE_A   = 0x02270B94
        FUSION_ROW_COUNT = 161
        FUSION_ROW       = 155
        FUSION_ROW_ADDR  = FUSION_TABLE_A + FUSION_ROW * 8          # 0x0227106C
        FUSION_STOCK_M1  = 0x0007       # category code: Machine
        FUSION_STOCK_M2  = 0x0004       # category code: Pyro
        FUSION_DEAD_MATERIAL = 0x3FFF

        # ---------------------------------------------------------------------------
        # PART E -- the named material: '"Jet Synchron" + ...'
        # ---------------------------------------------------------------------------
        # *** THE NAMED-MATERIAL RULE IS A 4-BYTE DATA ROW, NOT CODE. ***
        #
        # 0x02275B04: 23 rows x 4 B, {u16 synchro_cid, u16 named_material_cid}, strictly
        # ascending, BINARY-SEARCHED.  Read from OUTER 0x022485B4:
        #
        #   0x02248608  ldr  r1,=0x02275B04
        #   0x0224860A  adds r0,r5,#0        ; r0 = the SYNCHRO's cid
        #   0x0224860C  movs r2,#0x17        ; count = 23
        #   0x0224860E  movs r3,#4           ; stride = 4
        #   0x02248610  bl   0x02022E44      ; binary search -> row ptr, or 0
        #   0x02248618  beq  0x02248660      ; MISS -> the generic per-Synchro cid switch
        #   0x02248636  ldr  r0,=0x000020F7  ; HIT: is the material QUICKDRAW SYNCHRON?
        #   0x0224863E  ldrsh r0,[row,#2] ; bl 0x02023E1C   ; ...and the named cid a "Synchron"?
        #   0x0224864E  ldrsh r0,[row,#2] ; cmp r4,r0       ; ACCEPT iff material == named
        #   0x0224865C  movs r0,#0 ; pop                    ; else REJECT
        #
        # Junk Warrior 0x1E10 is row 1 = {0x1E10, 0x1E07} and prints the IDENTICAL count
        # clause ('"Junk Synchron" + 1 or more non-Tuner monsters') -- that row is its
        # entire material rule.  Jet Warrior is the same shape with a different name.
        #
        # FREE BONUS, and the correct real-world ruling: 0x224C is a stock member of the
        # "Synchron" set-code table 0x0209C968, so the arm at 0x02248636 makes QUICKDRAW
        # SYNCHRON a legal substitute Tuner automatically.
        NAMEDMAT_BASE    = 0x02275B04
        NAMEDMAT_COUNT   = 23
        NAMEDMAT_STRIDE  = 4
        NAMEDMAT_PHANTOM = 0x2524       # "Junk Berserker" -- not a card in this ROM
        NAMEDMAT_ROW     = (DONOR_CID, JET_SYNCHRON_CID)

        # Read-only cross-checks the printed summon procedure needs (verify()).  All
        # three are OPT-IN EXCEPTION LISTS and the donor must be ABSENT from every one.
        LIST_A          = 0x02275AB8    # 16 x u16 -- membership = "EXACT, extras forbidden"
        LIST_A_COUNT    = 16            # /!\ adding the donor here would BREAK "1 or more"
        MIN3_LIST       = 0x02275AD8    # 21 x u16 -- membership = 3 materials minimum
        MIN3_COUNT      = 21
        TWO_TUNER_CIDS  = (0x239F, 0x24B2)      # literal compares at 0x02248294/0x02248298

        # ---------------------------------------------------------------------------
        # PART F -- clause 1, "If this card is Synchro Summoned: ... return it to the hand"
        # ---------------------------------------------------------------------------
        # The trigger is INHERITED (the donor is row 30 of 0x0228F6C0); only the action
        # slots of its existing cls1 record change.  Transplant source is NIGHTMARE
        # PENGUIN cls1[325] @0x02287F4C, whose 5-tuple is shared verbatim by Gem-Knight
        # Aquamarine (cls2[579]) and Lavalval Dragon (cls3[696]) -- three records, three
        # printed "target 1 card your opponent controls; return it to the hand" texts.
        #
        #   +04 0x02204911  the BOUNCE resolver.  21 sharers, all bounce (Compulsory
        #                   Evacuation Device 0x171A, Hane-Hane, Abyss Soldier, ...).
        #   +08 0x021DED49  "1 CARD your opponent controls".  EXACTLY 6 sharers and 6/6
        #                   are printed "...your opponent controls".
        #                   /!\ NOT 0x021D8CF5 (Compulsory Evacuation Device's) -- that
        #                   one is "1 MONSTER on the field": both sides, monsters only.
        #   +0C 0x0224A115  'movs r0,#2; bx lr' -- activatable unconditionally.
        #   +10 0x021E51E5  UNCHANGED.  Timing class 2 = the optional "You can" tag, and
        #                   Jet Warrior also prints "You can target".  This matters:
        #                   timing.class_is_the_slot4_literal (VERIFIED) says the
        #                   classifier 0x0224AF7C reads +0x10 as a RAW LITERAL and never
        #                   calls it, so a wrong value here is the silent-drop failure
        #                   that cost lightpulsar a withdraw-and-restore.  Nothing
        #                   moves, so nothing is at risk.
        #   +14 0x02234DCD  'movs r2,#0x57 ; b 0x02234CA5' -- the single-target
        #                   declaration thunk.  Prompt code 0x57 is carried by 31
        #                   records, ALL worded "return that target to the hand".
        #
        # NO CRITERIA-REGISTRY ROW IS NEEDED: Nightmare Penguin, Mist Wurm and Gem-Knight
        # Aquamarine each have ZERO rows in 0x022713C4.  A bounce of an ON-FIELD card
        # never touches the off-field selection engine.
        CLS1_BASE   = 0x022860D4
        CLS1_COUNT  = 0x535
        CLS1_STRIDE = 0x18
        CLS1_INDEX  = 1279                                          # STOCK index only
        CLS1_ADDR   = CLS1_BASE + CLS1_INDEX * CLS1_STRIDE          # 0x0228D8BC, STOCK only


        def cls1_addr(ov) -> int:
            """The donor's cls1 row, located BY CID rather than by row index.

            ⚠️ CLS1_INDEX/CLS1_ADDR are the STOCK position and are WRONG in the combined
            build: an earlier chain step deletes a cls1 row above ours, so on the chained
            image the donor sits at 1278, not 1279, and anchoring on the index aborts the
            whole 52-step run at step 48 with "holds cid 0x23FD ... refusing to patch a
            moved table" (measured).  otn-chain-build-verify-artifact:
            ANCHOR CHAIN PRECONDITIONS ON A CID, NEVER A ROW INDEX.

            Keep-cid means +00 stays the donor before AND after the transplant, so this
            is stable and idempotent.
            """
            hits = [i for i in range(CLS1_COUNT)
                    if struct.unpack_from("<I", ov, _off(CLS1_BASE + i * CLS1_STRIDE))[0] == DONOR_CID]
            assert len(hits) == 1, (
                f"expected exactly one cls1 row for the donor 0x{DONOR_CID:04X}, found {hits}")
            return CLS1_BASE + hits[0] * CLS1_STRIDE

        # Volcannon's stock slots -- the guard that we are patching the right record.
        CLS1_BEFORE = (0x02230C7D, 0x021D882D, 0x02203C5D, 0x021E51E5, 0x02234DA5)
        CLS1_AFTER  = (0x02204911, 0x021DED49, 0x0224A115, 0x021E51E5, 0x02234DCD)

        # Inherited, NOT edited -- pinned so a table move is caught.
        SS_TRIGGER_LIST  = 0x0228F6C0
        SS_TRIGGER_COUNT = 0x24
        SS_TRIGGER_ROW   = 30
        SS_TRIGGER_ADDR  = SS_TRIGGER_LIST + SS_TRIGGER_ROW * 2     # 0x0228F6FC

        # The one unexplained binding (see the module docstring).  Pinned, not edited.
        UNKNOWN_LIST_ENTRY = 0x0226D974


        # ===========================================================================
        # helpers
        # ===========================================================================


        def _find_one(ov: bytes, base: int, count: int, stride: int, cid: int,
                      width: str) -> int:
            hits = [i for i in range(count)
                    if struct.unpack_from(width, ov, _off(base) + i * stride)[0] == cid]
            if len(hits) != 1:
                raise SystemExit(f"expected exactly 1 row for {cid:#06x} at {base:#010x}, "
                                 f"found {hits}")
            return hits[0]


        def _count_neutral_insert(ov: bytearray, base: int, count: int, stride: int,
                                  width: str, phantom: int, row: bytes, cid: int,
                                  label: str, strict: bool = True) -> None:
            """Drop *phantom*'s row and re-insert *row* at its sorted position.

            The array is binary-searched, so the COUNT and the SORTEDNESS are the
            invariants that matter -- neither changes here.  Idempotent.

            *strict* is the ordering the table actually guarantees.  The named-material
            table 0x02275B04 is STRICTLY ascending (one row per Synchro).  cls2 is only
            NON-DECREASING: a cid may legitimately own two records (Doppelwarrior 0x244D
            and King of the Beasts 0x20B9 both do), so asserting strictness there is
            wrong and rejects a correct insert.
            """
            def key(i: int) -> int:
                return struct.unpack_from(width, ov, _off(base) + i * stride)[0]

            if any(key(i) == cid for i in range(count)):
                print(f"  {label}: {cid:#06x} already present -- skipped (idempotent)")
                return
            src = _find_one(bytes(ov), base, count, stride, phantom, width)
            dst = sum(1 for i in range(count) if i != src and key(i) < cid)
            off = _off(base)
            rows = [bytes(ov[off + i * stride: off + (i + 1) * stride]) for i in range(count)]
            rows.pop(src)
            rows.insert(dst, row)
            assert len(rows) == count, "count-neutral insert changed the row count"
            ov[off: off + count * stride] = b"".join(rows)
            keys = [struct.unpack_from(width, ov, off + i * stride)[0] for i in range(count)]
            bad = (any(keys[i] >= keys[i + 1] for i in range(count - 1)) if strict
                   else any(keys[i] > keys[i + 1] for i in range(count - 1)))
            assert not bad, (
                f"{label}: array is no longer "
                f"{'STRICTLY ascending' if strict else 'sorted'} after the insert")
            print(f"  {label}: dropped phantom {phantom:#06x} at [{src}], "
                  f"inserted {cid:#06x} at [{dst}] -- {count} rows, still sorted")


        # ===========================================================================
        # PART D -- fusion recipe
        # ===========================================================================
        def apply_fusion_recipe_kill(ov: bytearray) -> None:
            """Blank the donor's fusion recipe materials.  Count-neutral, idempotent."""
            off = _off(FUSION_ROW_ADDR)
            result, m1, m2, m3 = struct.unpack_from("<4H", ov, off)
            assert result == DONOR_CID, (
                f"fusion table A row {FUSION_ROW} @0x{FUSION_ROW_ADDR:08X} holds result "
                f"0x{result:04X}, expected the donor 0x{DONOR_CID:04X} -- refusing to "
                f"patch a moved table")
            if (m1, m2) == (FUSION_DEAD_MATERIAL, FUSION_DEAD_MATERIAL):
                print(f"D  fusion recipe row {FUSION_ROW} already neutralised -> no change")
                return
            assert (m1, m2, m3) == (FUSION_STOCK_M1, FUSION_STOCK_M2, 0), (
                f"fusion row {FUSION_ROW} materials are (0x{m1:04X}, 0x{m2:04X}, 0x{m3:04X}), "
                f"expected the stock category codes (0x{FUSION_STOCK_M1:04X}, "
                f"0x{FUSION_STOCK_M2:04X}, 0) -- someone else claimed this row")
            struct.pack_into("<2H", ov, off + 2, FUSION_DEAD_MATERIAL, FUSION_DEAD_MATERIAL)
            print(f"D  fusion recipe A[{FUSION_ROW}] @0x{FUSION_ROW_ADDR:08X}: materials "
                  f"0x{m1:04X}/0x{m2:04X} -> 0x{FUSION_DEAD_MATERIAL:04X}/"
                  f"0x{FUSION_DEAD_MATERIAL:04X}  => the row can never be satisfied, so the "
                  f"ungated AI planner 0x022112B2 cannot Fusion Summon the converted card")


        # ===========================================================================
        # PART E -- the named material
        # ===========================================================================
        def apply_named_material(ov: bytearray) -> None:
            """Give the donor a row in the named-material table 0x02275B04."""
            # Guard the table before touching it: Junk Warrior's row is the anchor.
            jw = struct.unpack_from("<2H", ov, _off(NAMEDMAT_BASE) + 1 * NAMEDMAT_STRIDE)
            assert jw == (0x1E10, 0x1E07), (
                f"named-material row 1 is {jw}, expected Junk Warrior's "
                f"(0x1E10, 0x1E07) -- the table moved or is not what this patch assumes")
            row = struct.pack("<2H", *NAMEDMAT_ROW)
            assert len(row) == NAMEDMAT_STRIDE
            _count_neutral_insert(ov, NAMEDMAT_BASE, NAMEDMAT_COUNT, NAMEDMAT_STRIDE, "<H",
                                  NAMEDMAT_PHANTOM, row, DONOR_CID, "E named-material")


        # ===========================================================================
        # PART F -- clause 1
        # ===========================================================================
        def apply_clause1(ov: bytearray) -> None:
            """Transplant Nightmare Penguin's action slots onto cls1[1279], in place."""
            addr = cls1_addr(ov)
            off = _off(addr)
            cid = struct.unpack_from("<I", ov, off)[0]
            assert cid == DONOR_CID, (
                f"the donor's cls1 row @0x{addr:08X} holds cid 0x{cid:04X}, expected "
                f"the donor 0x{DONOR_CID:04X} -- refusing to patch a moved table")
            cur = struct.unpack_from("<5I", ov, off + 4)
            if cur == CLS1_AFTER:
                print(f"F  cls1 @0x{addr:08X} 0x{DONOR_CID:04X}: already transplanted "
                      f"(idempotent)")
                return
            assert cur == CLS1_BEFORE, (
                f"F  cls1 @0x{addr:08X} for 0x{DONOR_CID:04X} is "
                f"{[f'0x{v:08X}' for v in cur]}, expected Volcannon's stock slots "
                f"{[f'0x{v:08X}' for v in CLS1_BEFORE]} -- someone else claimed this record")
            struct.pack_into("<5I", ov, off + 4, *CLS1_AFTER)
            print(f"F  cls1 0x{DONOR_CID:04X} @0x{addr:08X}: "
                  + " ".join(f"0x{a:08X}->0x{b:08X}" for a, b in zip(cur, CLS1_AFTER)))


        # ===========================================================================
        # PARTS A + B -- bin2.pac, both records written IN PLACE (same size, no rebuild)
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


        def apply_card_prop_and_genre(out_path: str) -> None:
            """A: copy Laval Twin Slayer's whole card_prop record (cid swapped).
            B: clear the card_genre FUSION tag and set the SYNCHRO tag.

            Both are same-size in-place writes, so bin2.pac is NOT rebuilt here -- the
            text pass (PART C) is what rebuilds it, and it re-reads the archive from the
            ROM we save, so these edits carry through.
            """
            rom = ndspy.rom.NintendoDSRom.fromFile(out_path)
            fid, orig, archive = _find_pac(rom)
            pac = bytearray(orig)

            prop_off, genre_off, idx = _record_offsets(bytes(pac), archive)

            # -- A: the reference-record copy --------------------------------------
            cpf = next(f for f in archive.files
                       if f.get_clean_name().lower() == "card_prop.bin")
            ref_off = None
            for i in range((cpf.size - 8) // 8):
                o = cpf.address + 8 + i * 8
                if (int.from_bytes(pac[o:o + 8], "little") & 0x3FFF) == REFERENCE_SYNCHRO_CID:
                    ref_off = o
                    break
            if ref_off is None:
                raise RuntimeError(
                    f"reference cid 0x{REFERENCE_SYNCHRO_CID:04X} (Laval Twin Slayer) "
                    f"not found in card_prop.bin")
            ref = int.from_bytes(pac[ref_off:ref_off + 8], "little")
            ref_type = (ref >> 32) & 0x3F
            assert ref_type == NEW_CARD_TYPE, (
                f"reference card 0x{REFERENCE_SYNCHRO_CID:04X} has card_type {ref_type}, "
                f"expected {NEW_CARD_TYPE} (Synchro Effect Monster)")

            cur = int.from_bytes(pac[prop_off:prop_off + 8], "little")
            want = (ref & ~0x3FFF) | DONOR_CID
            if ((cur >> 32) & 0x3F) == NEW_CARD_TYPE:
                print(f"A  card_prop[0x{DONOR_CID:04X}] already card_type {NEW_CARD_TYPE} "
                      f"-> no template copy")
            else:
                pac[prop_off:prop_off + 8] = want.to_bytes(8, "little")
                print(f"A  card_prop[0x{DONOR_CID:04X}] idx {idx}: 0x{cur:016X} -> "
                      f"0x{want:016X}  (Laval Twin Slayer 0x{REFERENCE_SYNCHRO_CID:04X} "
                      f"template, cid swapped; the stat fields follow in PART C)")

            # -- B: the genre category tags ----------------------------------------
            g_cur = int.from_bytes(pac[genre_off:genre_off + 8], "little")
            if g_cur == NEW_GENRE:
                print(f"B  card_genre[{idx}] already 0x{NEW_GENRE:016X} -> no change")
            else:
                assert g_cur in (DONOR_GENRE_STOCK, NEW_GENRE), (
                    f"card_genre[{idx}] is 0x{g_cur:016X}, expected the stock donor value "
                    f"0x{DONOR_GENRE_STOCK:016X} -- someone else claimed it")
                pac[genre_off:genre_off + 8] = NEW_GENRE.to_bytes(8, "little")
                print(f"B  card_genre[{idx}]: 0x{g_cur:016X} -> 0x{NEW_GENRE:016X}  "
                      f"(clear bit {GENRE_BIT_FUSION} FUSION, set bit {GENRE_BIT_SYNCHRO} "
                      f"SYNCHRO, keep bit {GENRE_BIT_NOMI} nomi and the donor's "
                      f"effect-category tags)")

            assert len(pac) == len(orig), "bin2.pac changed size -- these edits must be in place"
            rom.files[fid] = bytes(pac)
            rom.saveToFile(out_path)


        # ===========================================================================
        # CLAUSES 2 + 3 -- the Graveyard revive, and the two once-per-turn latches
        # ===========================================================================
        # CLAUSE 2: "If this card is in your Graveyard: You can Tribute 1 Level 2 or
        #            lower monster; Special Summon this card in Defense Position, but
        #            banish it when it leaves the field."
        # CLAUSE 3: "You can only use each effect of 'Jet Warrior' once per turn."
        #
        # *** THE GY OFFER PATH IS SAFE FOR AN EXTRA-DECK cid -- MEASURED, NOT ASSUMED.
        # The zone scanner 0x0224C88E walks the ZONE ARRAY (0x0219CE2C count,
        # 0x0219CAE4 cid-by-index) and matches on CID ALONE; 0x0224C591 fills the
        # descriptor (desc[+3] = 0x0E, desc[+5] = 2 = CLASS 2) and calls 0x021EC740,
        # whose card_type-reading branch is ON-FIELD ONLY (`ldrb r4,[r5,#3] ; cmp r4,#0xA
        # ; bls`) -- a GY descriptor takes `b 0x021EC892`, which SETS the cls2 selector.
        # NOTHING on the path reads card_type / is_extra_deck / card_category.  The one
        # per-cid gate, `bl 0x021A897C` @0x021ECD32, is guarded by
        # `ldr r0,[0x0229C294+0x78] ; tst r0,#1` -- and that flag is 0x00000000 in every
        # duel savestate measured (rom.ml1/ml2/ml3, ov3 resident 3/3), so it never runs.
        # See scratch/jw_gyoffer_probe.py and notes/jet-warrior-findings.md C11 + C12.
        #
        # *** CLAUSE 3 MUST BE STAMPED IN SLOT +10, NOT IN THE RESOLVER. ***
        # dispatch.once_per_turn_must_stamp_at_activation (VERIFIED, measured in-game on
        # card.maiden_clause1): with the post in slot1, BOTH activations run the slot3
        # query before either resolves, so the card can be activated TWICE IN ONE CHAIN.
        # The stamp therefore wraps the activation procedure and fires only on the
        # "player accepted" return, so DECLINING THE PROMPT DOES NOT BURN THE LATCH.
        #
        # ⚠️ AND THAT FORCES A TIMING-HOOK ARM.  timing.class_is_the_slot4_literal: the
        # WHEN-vs-IF classifier 0x0224AF7C reads +0x10 RAW and never calls it, so a cave
        # pointer there leaves the card in NO timing class -- the failure that cost
        # lightpulsar a withdraw-and-restore.  0x0224AF7C returns 0 at once for
        # descriptor selectors 0 and 3, so a cls0/cls3 record escapes this; OURS ARE cls1
        # AND cls2, so cid 0x23EB is registered on the SHARED timing-class hook.  One arm
        # covers both records -- both clauses are class 2 ("You can").
        # ---------------------------------------------------------------------------
        TURNLOG_QUERY = 0x021A14E9   # (side, 0x0B, key, kind) -> nonzero iff already logged
        TURNLOG_POST  = 0x021D2585   # (side, key, kind, 0) -> log it
        TURNLOG_SLOT  = 0x0B

        # THE TWO INDEPENDENT LATCHES.  dispatch.turnlog_once_per_duel_is_kind_5 carries
        # the closed proof of the kind semantics: the node search 0x021A1268 matches
        # node[+2] & 0xF under `cmp r7,#6 ; bhs`, so kinds run 0..5, and the end-of-turn
        # sweeper 0x0219F9E0's jump table sends kinds 1 AND 2 to the countdown-or-remove
        # block (0/4/5 persist).  So both are per-TURN.  The query matches key AND kind,
        # and no native code posts key 0x23EB, so these two cannot collide -- with each
        # other or with anything else.  That is what the printed "EACH effect" needs.
        LATCH_KEY = DONOR_CID
        C1_KIND = 1                  # clause 1, the Synchro-Summoned bounce
        C2_KIND = 2                  # clause 2, the GY Tribute revive

        TAG_BODY = 0x021E50DD        # the costless "You can" BODY (|1), NOT the 0x021E51E5
                                     #   thunk.  Returns 1 exactly when the player said yes.
        C2_COST = 0x021E7C89         # the shared Tribute machine.  Phase 0 opens the picker
                                     #   and returns 0; phase 1 returns 0 AND REWINDS the
                                     #   phase on a cancel (0x021E8144), or falls through to
                                     #   the send-to-GY 0x021CF68C and returns 1.  So 1 means
                                     #   "the Tribute was actually paid".
                                     #   ⚠️ Its per-cid switch is NOT a filter selector -- it
                                     #   maps a cid to a NAMED tribute cid used only as a UI
                                     #   prompt parameter, and an unlisted cid gets 0 = "no
                                     #   card named", which is right for a Level filter.
                                     #   The FILTERING is done by slot2.  See
                                     #   dispatch.tribute_cost_filter_lives_in_slot2.
        C2_RESOLVER = 0x0220731D     # the GY self-Special-Summon resolver, shared by 68 cls2
                                     #   records.  Used VERBATIM: the Defense Position comes
                                     #   from the CAVE_JW_C2_POS hook below, not from here.
        C2_CONDITION = 0x021FF06D    # Plaguespreader Zombie's own GY-revive gate

        ZONE_PRED = 0x021D6E41       # (desc, side, zone, MASK) -> 1 accept / 0 reject
        TRIBUTE_MASK = 0x00008011    # SWAP FROG 0x2115's mask, whose printed cost is
                                     #   "return 1 monster you control to the hand" -- exactly
                                     #   the population to filter by Level.  Fields:
                                     #     bits 0-1 = 01  SIDE SELECTOR, "same side as the
                                     #                    source" (see the WRONG-MASK note)
                                     #     bits 4-6 = 0x10  zone class, "zone < 5" = a monster
                                     #                    zone
                                     #     bit 15   = the TRIBUTABILITY checks: the arm at
                                     #                0x021D714E requires 0x021B088C(side,zone)
                                     #                and 0x021BAF30(side, 1<<(zone+side*16))
                                     #                to be non-zero, else reject.  Those are
                                     #                what stop you tributing a monster that
                                     #                cannot be tributed, so a Tribute cost
                                     #                WANTS them.
                                     #
                                     # ⚠️⚠️ THIS WAS 0x00020013 AND IT BROKE THE CARD IN GAME
                                     # the effect was offered with no legal
                                     # target and summoned WITHOUT EVER TRIBUTING.  BITS 0-1
                                     # ARE A 2-BIT SELECTOR, NOT TWO FLAGS -- 0x021D6E48 does
                                     # `movs r0,#3 ; ands r0,r4` and switches: 1 = same side,
                                     # 2 = opponent's side, 3 = a THIRD mode gated on
                                     # 0x021AE130, 0 = no side test.  Setting bits 0 AND 1
                                     # selected mode 3, which rejected the one legal candidate
                                     # (Level Eater).  With NO candidate, the cost machine's
                                     # `bl 0x0224AB38` returned 0 and it took the
                                     # `b 0x021E7C98` = RETURN 1 path -- the engine's "there is
                                     # nothing to pay, so the cost is satisfied" convention --
                                     # so the summon proceeded for free.  0x00020013 came from
                                     # a sweep of the 168 thin mask wrappers whose owners print
                                     # "Tribute" (wrapper 0x021DFD0D: Raviel, Hand of Nephthys,
                                     # ...), but those cards TRIBUTE FOR A SUMMON and use side
                                     # mode 3 deliberately.  Matching on the word "Tribute" was
                                     # the wrong join; match on the PRINTED POPULATION.
                                     #
                                     # ⚠️ There is NO Level field in the mask, so the level
                                     #   test below must be written -- no stock slot2 pointer
                                     #   means "Level 2 or lower monster you control".
        LEVEL_GETTER = 0x021B807D    # (side, zone, 0) -> the card's LIVE Level (honours Level
                                     #   modifiers), the getter dispatch.level_rider_is_kind_3
                                     #   names and scratch/accel_level_probe.py measured on a
                                     #   real board.  NOT 0x0202ABD8, which is the printed one.
        MAX_TRIBUTE_LEVEL = 2

        # --- the candidate count the ACTIVATION CONDITION has to do for itself ------
        # dispatch.cls_slot_roles says slot3's code 1 means "activatable but slot2 must
        # find at least one legal target", and 0x0224AD94 is what implements that.  THE
        # GY-ACTION OFFER PATH DOES NOT GO THROUGH 0x0224AD94 -- measured in game: with
        # the condition returning 1, the effect was still offered on a board with no
        # Level 2 or lower monster, and then summoned for free.  So the condition counts
        # the candidates ITSELF, using the SAME sweeper the Tribute machine uses at
        # 0x021E7D40, which guarantees the gate and the cost can never disagree about
        # what counts as a legal Tribute.
        CANDIDATE_COUNT = 0x0224AB39     # (desc, filter) -> number of legal candidates
        SLOT2_INVOKER = 0x0224A8C1       # "run the record's own +08 on this candidate"

        # *** EVERY `blx` TARGET MUST CARRY THE THUMB BIT. ***
        # This assertion exists because omitting it FROZE THE GAME on the first in-game
        # test of clauses 2+3 (user: "I hit a freeze when jet warrior is
        # summoned ... before I believe it worked so this is a regression").  `blx rX`
        # with bit 0 CLEAR switches the CPU to ARM state, so the ARM9 -- which is running
        # Thumb here -- starts decoding Thumb halfwords as ARM words: instant garbage.
        # All four of these are Thumb functions (each begins `push {...}`), and all four
        # had been written from their even disassembly addresses.  Nothing catches it:
        # assert_thumb1_only checks the STUB's encoding, not its literal pool, and a
        # capstone disasm of the stub shows only `ldr rX,[pc,#imm]`.
        # The one that froze was TURNLOG_QUERY inside CAVE_JW_C1_COND -- cls1's +0C,
        # which the engine evaluates while enumerating the summon trigger, i.e. exactly
        # "at the moment of summoning".
        for _n, _v in (("TURNLOG_QUERY", TURNLOG_QUERY), ("TURNLOG_POST", TURNLOG_POST),
                       ("TAG_BODY", TAG_BODY), ("C2_COST", C2_COST),
                       ("C2_CONDITION", C2_CONDITION), ("C2_RESOLVER", C2_RESOLVER),
                       ("CANDIDATE_COUNT", CANDIDATE_COUNT),
                       ("ZONE_PRED", ZONE_PRED), ("LEVEL_GETTER", LEVEL_GETTER)):
            assert _v & 1, (
                f"{_n} = 0x{_v:08X} has bit 0 CLEAR; every one of these is reached by "
                f"`blx`, and an even target switches the core to ARM state -> freeze")

        # --- the SS commit's position argument ------------------------------------
        # 0x0226925C(r0 = side, r1 = locator, r2 = face_up, r3 = POSITION), [sp] = cid<<16.
        # The token fact fixes the encoding: 1 = Defense, 0 = Attack, 2 = player's choice.
        # C2_RESOLVER's per-cid switch 0x02207424 gives any unlisted cid the DEFAULT
        # r4 = 2, so Jet Warrior would otherwise let the player choose.  These are the two
        # instructions that load two of the four arguments, and they are exactly 4 bytes.
        POS_SITE = 0x022074E6
        # ldrb r0,[r5,#2] = 0x78A8 (01111 00010 101 000) ; adds r3,r4,#0 = 0x1C23
        # (0001110 000 100 011).  Little-endian: A8 78 23 1C.
        POS_SITE_NATIVE = bytes.fromhex("a878231c")
        POS_DEFENSE = 1

        # --- the GY-action registry row (PART G) ----------------------------------
        # 0x0228DDF8, 60 rows x 0x10 B {u32 cid, u32 zone, u32 chk, u32 post}, UNSORTED and
        # LINEAR-SCANNED, so a cid rewrite is count-neutral by construction.
        # ⚠️ FAMILY C's PHANTOMS ARE EXHAUSTED (row 15 -> grapha, 47 -> lightpulsar,
        # 48 -> jet_synchron) and the table cannot grow: it ends at 0x0228E1B8 with a
        # pointer table immediately after.  Family B's three phantoms are a TRAP -- that
        # family builds no class descriptor and gates on the HAND.
        # So this patch spends a REAL card's row, by explicit user decision.
        GYREG_BASE = 0x0228DDF8
        GYREG_COUNT = 0x3C
        GYREG_STRIDE = 0x10
        GYREG_ROW = 33
        GYREG_ROW_ADDR = GYREG_BASE + GYREG_ROW * GYREG_STRIDE      # 0x0228E008
        GYREG_STOCK_CID = 0x209D     # "Sword of Sparkles"
        GYREG_ZONE_GY = 0x0E
        GYREG_CHECK = 0x0224C591
        GYREG_POST = 0x0224C6C1
        # WHAT SPENDING IT COSTS, measured: it kills exactly Sword of Sparkles' THIRD
        # sentence ("You can Tribute 1 monster you control to return this card from your
        # Graveyard to the top of your Deck"), whose action is cls2[475] @0x0227888C.  Its
        # equip + battle-destruction clause lives in cls1[1042] @0x0228C284 and is reached
        # by the battle/equip path, so it stays fully live.  It has no criteria row and no
        # leave-mask row.  The card loses one of three sentences; it is not bricked.

        # --- the new cls2 record (PART H) -----------------------------------------
        CLS2_BASE = 0x02275C04
        CLS2_COUNT = 0x2B9
        CLS2_STRIDE = 0x18
        # 0x1655 has no card_prop record and EXACTLY ONE aligned-u16 mention in all of
        # overlay 3 -- its own cls2 record -- which is the fewest of any unclaimed cls2
        # phantom.  Cross-checked against PHANTOM_CLAIMS.
        CLS2_PHANTOM = 0x1655
        CLS2_SLOTS = (C2_RESOLVER,
                      ov5_cave.CAVE_JW_TRIBFILT | 1,
                      ov5_cave.CAVE_JW_C2_COND | 1,
                      ov5_cave.CAVE_JW_C2_SLOT4 | 1,
                      0x00000000)

        # Clause 1's two slots move for clause 3.  +04 and +08 and +14 do NOT move, so the
        # in-game-confirmed bounce itself is untouched.
        CLS1_AFTER_C3 = (0x02204911, 0x021DED49,
                         ov5_cave.CAVE_JW_C1_COND | 1,
                         ov5_cave.CAVE_JW_C1_SLOT4 | 1,
                         0x02234DCD)

        C23_RESERVES = {
            "CAVE_JW_C1_COND": 0x30,
            "CAVE_JW_C1_SLOT4": 0x40,
            "CAVE_JW_C2_COND": 0x60,
            "CAVE_JW_C2_SLOT4": 0x40,
            "CAVE_JW_TRIBFILT": 0x40,
            "CAVE_JW_C2_POS": 0x20,
        }




        # ---------------------------------------------------------------------------
        # The six ov5 stubs
        # ---------------------------------------------------------------------------
        def _stub_c1_cond(base: int) -> bytes:
            """cls1 +0C -- clause 3 for clause 1.  (desc, arg) -> activation code.

            Returns 2 ("activatable unconditionally", what the stock 0x0224A115 returned)
            unless the kind-1 node is already on this turn's log, in which case 0.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call("turnlog_query", R0, TURNLOG_SLOT, LATCH_KEY, C1_KIND, via=R5)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "used")
            b.insn("MOV", "R0, #0x2")
            b.insn("POP", "{R4, R5, PC}")
            b.label("used")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, PC}")
            return b.assemble(base, pad="nop")


        def _stub_c1_slot4(base: int) -> bytes:
            """cls1 +10 -- clause 1's activation procedure, plus clause 3's STAMP.

            Wraps the costless "You can" BODY 0x021E50DC and posts the kind-1 node only
            when it returns 1 = "the player said yes".  Declining does not burn the latch.
            `blx` clobbers lr, which is safe because lr is already on the stack.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(TAG_BODY, via=R2)
            b.insn("CMP", "R0, #0x1")
            b.insn("BNE", "out")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_post(R0, LATCH_KEY, C1_KIND, via=R4)
            b.insn("ADD", "R0, R5, #0x0")
            b.label("out")
            b.insn("POP", "{R4, R5, PC}")
            return b.assemble(base, pad="nop")


        def _stub_c2_cond(base: int) -> bytes:
            """cls2 +0C -- clause 3 for clause 2, the GY-revive gate, and "a Tribute exists".

            The turn-log query is FIRST so a spent latch costs nothing else, then
            Plaguespreader Zombie's own 0x021FF06D decides whether the revive is legal.

            *** IT RETURNS 1, NOT 2, AND THAT IS THE WHOLE POINT. ***
            dispatch.cls_slot_roles: slot3's return is a CODE -- 0 = cannot activate,
            1 = activatable BUT slot2 must find at least one legal target, >= 2 =
            activatable unconditionally.  Returning 2 (what the stock 0x0224A115 does)
            is why the first build offered this effect with NO Level 2 or lower monster
            on the field.  And offering it was not harmless: with no candidate, the cost
            machine's `bl 0x0224AB38` @0x021E7D40 returns 0 and it takes
            `b 0x021E7C98` = RETURN 1 -- the engine's "there is nothing to pay, so the
            cost is satisfied" convention -- so the card SUMMONED ITSELF FOR FREE.
            Returning 1 makes the engine run our slot2 over the board first and refuse
            the activation when nothing passes, which is the printed behaviour.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.call("turnlog_query", R0, TURNLOG_SLOT, LATCH_KEY, C2_KIND, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BNE", "used")
            b.call_addr(C2_CONDITION, R4, R5, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "used")
            b.call_addr(CANDIDATE_COUNT, R4, SLOT2_INVOKER, via=R6)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "used")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, PC}")
            b.label("used")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, PC}")
            return b.assemble(base, pad="nop")


        def _stub_c2_slot4(base: int) -> bytes:
            """cls2 +10 -- the Tribute cost, plus clause 3's STAMP.

            Chains the shared Tribute machine and posts the kind-2 node only on a return
            of 1 = "the Tribute was actually paid" (phase 1 returns 0 and rewinds the
            phase on a cancel), so cancelling does not burn the latch.
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.call_addr(C2_COST, via=R2)
            b.insn("CMP", "R0, #0x1")
            b.insn("BNE", "out")
            b.insn("ADD", "R5, R0, #0x0")
            b.insn("LDRB", "R0, [R4, #0x2]")
            b.turnlog_post(R0, LATCH_KEY, C2_KIND, via=R4)
            b.insn("ADD", "R0, R5, #0x0")
            b.label("out")
            b.insn("POP", "{R4, R5, PC}")
            return b.assemble(base, pad="nop")


        def _stub_tribfilt(base: int) -> bytes:
            """cls2 +08 -- "1 Level 2 or lower monster".  (desc, side, zone) -> 1 / 0.

            dispatch.tribute_cost_filter_lives_in_slot2: the Tribute machine enumerates
            its candidates through the record's own slot2, so this IS the restriction.
            The zone predicate supplies "a monster you control" from the engine's own
            Tribute mask; the Level test has to be written, because the mask has no Level
            field and no stock slot2 pointer means "Level 2 or lower monster you control".
            """
            b = EffectBuilder()
            b.insn("PUSH", "{R4, R5, R6, R7, LR}")
            b.insn("ADD", "R4, R0, #0x0")
            b.insn("ADD", "R5, R1, #0x0")
            b.insn("ADD", "R6, R2, #0x0")
            b.call_addr(ZONE_PRED, R0, R1, R2, TRIBUTE_MASK, via=R7)
            b.insn("CMP", "R0, #0x0")
            b.insn("BEQ", "reject")
            b.call_addr(LEVEL_GETTER, R5, R6, 0, via=R7)
            b.insn("CMP", f"R0, #0x{MAX_TRIBUTE_LEVEL:X}")
            b.insn("BGT", "reject")
            b.insn("MOV", "R0, #0x1")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            b.label("reject")
            b.insn("MOV", "R0, #0x0")
            b.insn("POP", "{R4, R5, R6, R7, PC}")
            return b.assemble(base, pad="nop")


        def _stub_c2_pos(base: int) -> bytes:
            """Force DEFENSE POSITION for our cid only.  Displaces 4 bytes at POS_SITE.

            Native:  ldrb r0,[r5,#2]  (side)  ;  adds r3,r4,#0  (position)
            -- two of the four arguments of the SS commit 0x0226925C, loaded immediately
            before the call at 0x022074EA.

            ⚠️ 68 cls2 records share this resolver, so the equivalence must be exact.  It
            is, BY CONSTRUCTION: this stub writes ONLY r0 and r3 -- precisely the two
            registers the displaced pair writes -- and leaves r1, r2, r4 and r5 alone
            (r1 = the locator and r2 = face_up were loaded at 0x022074DE/E0 and are live).
            For every cid but ours it performs the identical two writes in the opposite
            order, which is unobservable.  No harness needed.

            O15 (2026-09-07): IT ALSO ARMS THE BANISH RIDER.  "...but banish it when it
            leaves the field" belongs to clause 2's revive ONLY -- a Synchro Summoned Jet
            Warrior prints no rider -- so summon_rider_hook needs a one-shot byte that
            only this summon sets.  THIS is the tightest possible setter: it is already
            cid-scoped AND it sits at 0x022074E6 inside the GY self-SS resolver
            0x0220731D, four bytes before the SS commit `bl 0x0226925C` at 0x022074EA.
            Clause 1 uses a different resolver and the Synchro Summon never enters
            0x0220731D at all, so no other path can arm it.  (Jet Synchron arms from its
            resolver instead, which is looser.)

            ⚠️ The byte is NOT cleared here -- only the consumer may clear it, because the
            commit 0x0226925C can finish after this returns
            (rider.banish_marker_attach_site's timing warning; the window that killed
            card.upstart_golden_ninja's first STAGE latch).

            ⚠️ THE REGISTER INVARIANT SURVIVES: the two extra instructions use r0 and r3,
            which are exactly the registers this branch already clobbers, so the stub
            still writes ONLY r0 and r3 and the by-construction equivalence above is
            untouched.
            """
            b = EffectBuilder()
            b.insn("LDRH", "R0, [R5, #0x0]")
            b.ldr_const(3, DONOR_CID)
            b.insn("CMP", "R0, R3")
            b.insn("BNE", "native")
            b.ldr_const(0, ov5_cave.CAVE_JW_ARM)
            b.insn("MOV", "R3, #0x1")
            b.insn("STRB", "R3, [R0, #0x0]")
            b.insn("MOV", f"R3, #0x{POS_DEFENSE:X}")
            b.insn("B", "setside")
            b.label("native")
            b.insn("ADD", "R3, R4, #0x0")
            b.label("setside")
            b.insn("LDRB", "R0, [R5, #0x2]")
            b.insn("BX", "LR")
            return b.assemble(base, pad="nop")


        _C23_STUBS = (
            ("CAVE_JW_C1_COND", ov5_cave.CAVE_JW_C1_COND, _stub_c1_cond,
             "cls1 +0C: clause 3's query for clause 1"),
            ("CAVE_JW_C1_SLOT4", ov5_cave.CAVE_JW_C1_SLOT4, _stub_c1_slot4,
             "cls1 +10: the 'you can' body + clause 3's stamp"),
            ("CAVE_JW_C2_COND", ov5_cave.CAVE_JW_C2_COND, _stub_c2_cond,
             "cls2 +0C: clause 3's query + the GY-revive gate"),
            ("CAVE_JW_C2_SLOT4", ov5_cave.CAVE_JW_C2_SLOT4, _stub_c2_slot4,
             "cls2 +10: the Tribute cost + clause 3's stamp"),
            ("CAVE_JW_TRIBFILT", ov5_cave.CAVE_JW_TRIBFILT, _stub_tribfilt,
             "cls2 +08: '1 Level 2 or lower monster'"),
            ("CAVE_JW_C2_POS", ov5_cave.CAVE_JW_C2_POS, _stub_c2_pos,
             "force Defense Position at the SS commit"),
        )


        # ---------------------------------------------------------------------------
        # PART G -- the GY-action registry row
        # ---------------------------------------------------------------------------
        def apply_gy_registry(ov: bytearray) -> None:
            """Take over Sword of Sparkles' family-C row.  Count-neutral, idempotent."""
            off = _off(GYREG_ROW_ADDR)
            cid, zone, chk, post = struct.unpack_from("<4I", ov, off)
            if cid == DONOR_CID:
                print(f"G  GY-action row {GYREG_ROW} already the donor -> no change")
                return
            assert (cid, zone, chk, post) == (GYREG_STOCK_CID, GYREG_ZONE_GY,
                                              GYREG_CHECK, GYREG_POST), (
                f"GY-action row {GYREG_ROW} @0x{GYREG_ROW_ADDR:08X} is "
                f"(0x{cid:04X}, 0x{zone:X}, 0x{chk:08X}, 0x{post:08X}), expected Sword of "
                f"Sparkles' stock family-C row -- someone else claimed it")
            struct.pack_into("<I", ov, off, DONOR_CID)
            print(f"G  GY-action row {GYREG_ROW} @0x{GYREG_ROW_ADDR:08X}: cid "
                  f"0x{GYREG_STOCK_CID:04X} (Sword of Sparkles) -> 0x{DONOR_CID:04X}  "
                  f"[zone 0x{zone:X}, chk 0x{chk:08X}, post 0x{post:08X} unchanged]")


        # ---------------------------------------------------------------------------
        # PART H -- the cls2 record, and clause 1's two moved slots
        # ---------------------------------------------------------------------------
        def apply_clause23_records(ov: bytearray) -> None:
            rec = struct.pack("<I", DONOR_CID) + struct.pack("<5I", *CLS2_SLOTS)
            assert len(rec) == CLS2_STRIDE
            _count_neutral_insert(ov, CLS2_BASE, CLS2_COUNT, CLS2_STRIDE, "<H",
                                  CLS2_PHANTOM, rec, DONOR_CID, "H cls2", strict=False)

            addr = cls1_addr(ov)
            off = _off(addr)
            cur = struct.unpack_from("<5I", ov, off + 4)
            if cur == CLS1_AFTER_C3:
                print(f"H  cls1 @0x{addr:08X}: clause 3 slots already installed (idempotent)")
                return
            assert cur == CLS1_AFTER, (
                f"H  cls1 @0x{addr:08X} is {[f'0x{v:08X}' for v in cur]}, expected the "
                f"clause-1 tuple {[f'0x{v:08X}' for v in CLS1_AFTER]} -- run apply_clause1 first")
            struct.pack_into("<5I", ov, off + 4, *CLS1_AFTER_C3)
            print(f"H  cls1 @0x{addr:08X} +0C 0x{CLS1_AFTER[2]:08X}->0x{CLS1_AFTER_C3[2]:08X}, "
                  f"+10 0x{CLS1_AFTER[3]:08X}->0x{CLS1_AFTER_C3[3]:08X}  (clause 3; "
                  f"+04/+08/+14 UNTOUCHED, so the confirmed bounce itself does not move)")


        # ---------------------------------------------------------------------------
        # PART I -- the Defense-Position hook
        # ---------------------------------------------------------------------------
        def apply_position_hook(ov: bytearray) -> None:
            off = _off(POS_SITE)
            cur = bytes(ov[off:off + 4])
            want = _bl(POS_SITE, ov5_cave.CAVE_JW_C2_POS)
            if cur == want:
                print(f"I  position hook @0x{POS_SITE:08X}: already installed (idempotent)")
                return
            assert cur == POS_SITE_NATIVE, (
                f"I  0x{POS_SITE:08X} holds {cur.hex()}, expected the native "
                f"{POS_SITE_NATIVE.hex()} (ldrb r0,[r5,#2] ; adds r3,r4,#0) -- someone "
                f"else hooked the SS commit's argument load")
            ov[off:off + 4] = want
            print(f"I  position hook @0x{POS_SITE:08X}: {cur.hex()} -> bl "
                  f"0x{ov5_cave.CAVE_JW_C2_POS:08X}  (Defense Position, our cid only)")


        # ---------------------------------------------------------------------------
        # PART J -- install the ov5 stubs and the shared timing-class arm
        # ---------------------------------------------------------------------------
        def install_clause23(rom) -> None:
            """Write every ov5 blob clauses 2 + 3 need.  Read-back-and-skip = idempotent."""
            for name, addr, fn, doc in _C23_STUBS:
                blob = fn(addr)
                effect_verify.assert_thumb1_only(blob, addr)     # ARMv5TE = Thumb-1 ONLY
                reserve = C23_RESERVES[name]
                assert len(blob) <= reserve, \
                    f"J  {name} is {len(blob)} B > its {reserve:#x} reserve"
                if ov5_cave.read_cave(rom, addr, len(blob)) == blob:
                    print(f"J  {name} @0x{addr:08X}: already installed (idempotent)")
                    continue
                ov5_cave.install_cave(rom, addr, blob, reserve=reserve)
                print(f"J  {name} -> ov5 0x{addr:08X} ({len(blob)} B): {doc}")
            timinghook.install(rom)      # the shared timing-class hook (ARM_JW is ours)
            riderhook.install(rom)       # O15: the shared summon-rider hook (arm 0x23EB is
                                         #      ours; it also writes CAVE_JW_ARM, CLEAR)



        def install(rom, view):
            ov = view.buf
            apply_fusion_recipe_kill(ov)                    # PART D
            print("  E: the named material --")
            apply_named_material(ov)                        # PART E  (clause 0)
            apply_clause1(ov)                               # PART F  (clause 1)
            apply_gy_registry(ov)                           # PART G  (clause 2)
            print("  H: the cls2 record + clause 3's two slots --")
            apply_clause23_records(ov)                      # PART H  (clauses 2 + 3)
            apply_position_hook(ov)                         # PART I  (Defense Position)
            print("  T: shared timing-class hook --")
            timinghook.apply(ov)                            # its 4-byte site
            install_clause23(rom)                           # PART J  (ov5, before the save)


        def check_fn(c, rom, view):
            ov = view.buf

            def check(cond: bool, msg: str) -> bool:
                """Returns the verdict -- timing_class_hook.verify() folds it with &=."""
                c.ok(bool(cond), msg)
                return bool(cond)

            def u16(a: int) -> int:
                return struct.unpack_from("<H", ov, _off(a))[0]

            def u32(a: int) -> int:
                return struct.unpack_from("<I", ov, _off(a))[0]


            # -- PART D ------------------------------------------------------------
            r = struct.unpack_from("<4H", ov, _off(FUSION_ROW_ADDR))
            check(r[0] == DONOR_CID,
                  f"fusion A[{FUSION_ROW}] result is still the donor 0x{r[0]:04X}")
            check(r[1] == r[2] == FUSION_DEAD_MATERIAL,
                  f"fusion A[{FUSION_ROW}] materials blanked "
                  f"(0x{r[1]:04X}, 0x{r[2]:04X})")
            results = [u16(FUSION_TABLE_A + i * 8) for i in range(FUSION_ROW_COUNT)]
            check(all(results[i] <= results[i + 1] for i in range(FUSION_ROW_COUNT - 1)),
                  "fusion table A is still sorted by result cid")

            # -- PART E ------------------------------------------------------------
            keys = [u16(NAMEDMAT_BASE + i * NAMEDMAT_STRIDE) for i in range(NAMEDMAT_COUNT)]
            check(all(keys[i] < keys[i + 1] for i in range(NAMEDMAT_COUNT - 1)),
                  "named-material table is still strictly ascending (binary-searched)")
            check(NAMEDMAT_PHANTOM not in keys,
                  f"named-material phantom 0x{NAMEDMAT_PHANTOM:04X} was dropped")
            hits = [i for i, k in enumerate(keys) if k == DONOR_CID]
            check(len(hits) == 1, f"exactly one named-material row for the donor: {hits}")
            if hits:
                named = u16(NAMEDMAT_BASE + hits[0] * NAMEDMAT_STRIDE + 2)
                check(named == JET_SYNCHRON_CID,
                      f'named material is Jet Synchron 0x{named:04X} '
                      f'(row {hits[0]} @0x{NAMEDMAT_BASE + hits[0] * NAMEDMAT_STRIDE:08X})')
            check(u16(NAMEDMAT_BASE + 4) == 0x1E10,
                  "Junk Warrior's row 1 key is untouched")

            # The OUTER predicate must still read the table the way this patch assumes.
            # Without these three, a table move would leave the row we wrote unread and
            # the material rule would silently fall through to the generic cid switch.
            # Decode OUTER's `ldr r1,[pc,#imm]` at 0x02248608 rather than scanning a
            # window: this pins the exact literal the predicate reads.
            enc = u16(0x02248608)
            check(enc >> 11 == 0b01001, f"0x02248608 is still an LDR literal (0x{enc:04X})")
            pool_addr = ((0x02248608 + 4) & ~3) + (enc & 0xFF) * 4
            check(u32(pool_addr) == NAMEDMAT_BASE,
                  f"OUTER 0x022485B4 still loads the table base 0x{NAMEDMAT_BASE:08X} "
                  f"from its pool @0x{pool_addr:08X}")
            check(u16(0x0224860C) == 0x2217,
                  "OUTER still loads count 0x17 (movs r2,#0x17) @0x0224860C")
            check(u16(0x0224860E) == 0x2304,
                  "OUTER still loads stride 4 (movs r3,#4) @0x0224860E")

            # -- the three exception lists: the donor must be ABSENT from all --------
            la = [u16(LIST_A + i * 2) for i in range(LIST_A_COUNT)]
            m3 = [u16(MIN3_LIST + i * 2) for i in range(MIN3_COUNT)]
            check(DONOR_CID not in la,
                  "donor is ABSENT from LIST_A (membership would break '1 or more')")
            check(DONOR_CID not in m3,
                  "donor is ABSENT from the min-3-materials list")
            check(DONOR_CID not in TWO_TUNER_CIDS,
                  "donor is ABSENT from the 2-leading-Tuners pair")

            # -- PART F ------------------------------------------------------------
            _c1 = cls1_addr(ov)
            check(u32(_c1) == DONOR_CID,
                  f"the donor's cls1 row @0x{_c1:08X} still holds the donor cid")
            slots = struct.unpack_from("<5I", ov, _off(_c1) + 4)
            # +0C and +10 belong to clause 3 and are checked with it below; the three
            # slots that CARRY the in-game-confirmed bounce must never move.
            check((slots[0], slots[1], slots[4]) == (CLS1_AFTER[0], CLS1_AFTER[1], CLS1_AFTER[4]),
                  "cls1 +04/+08/+14 are still Nightmare Penguin's bounce tuple: "
                  + " ".join(f"0x{v:08X}" for v in (slots[0], slots[1], slots[4])))
            cls1_cids = [u32(CLS1_BASE + i * CLS1_STRIDE) for i in range(CLS1_COUNT)]
            check(all(cls1_cids[i] <= cls1_cids[i + 1] for i in range(CLS1_COUNT - 1)),
                  "cls1 is still sorted (binary-searched)")
            check(cls1_cids.count(DONOR_CID) == 1,
                  "the donor owns exactly ONE cls1 record (no leftmost-record shadow)")

            # -- inherited, must NOT have moved ------------------------------------
            check(u16(SS_TRIGGER_ADDR) == DONOR_CID,
                  f"donor is still row {SS_TRIGGER_ROW} of the proper-Summon trigger list "
                  f"@0x{SS_TRIGGER_ADDR:08X} (this is what makes clause 1 fire)")
            trig = [u16(SS_TRIGGER_LIST + i * 2) for i in range(SS_TRIGGER_COUNT)]
            check(all(trig[i] < trig[i + 1] for i in range(SS_TRIGGER_COUNT - 1)),
                  "the trigger list is still strictly ascending (binary-searched)")
            check(u16(UNKNOWN_LIST_ENTRY) == DONOR_CID,
                  f"the UNIDENTIFIED cid list @0x{UNKNOWN_LIST_ENTRY:08X} still names the "
                  f"donor -- inherited, but its only consumer on the GY path is the "
                  f"DORMANT gate 0x021A897C (see the module docstring)")

            # -- PART G: the GY-action registry row --------------------------------
            g = struct.unpack_from("<4I", ov, _off(GYREG_ROW_ADDR))
            check(g[0] == DONOR_CID,
                  f"GY-action row {GYREG_ROW} @0x{GYREG_ROW_ADDR:08X} is the donor "
                  f"(was Sword of Sparkles 0x{GYREG_STOCK_CID:04X})")
            check((g[1], g[2], g[3]) == (GYREG_ZONE_GY, GYREG_CHECK, GYREG_POST),
                  "the row is still family C: zone 0x0E, chk 0x0224C591, post 0x0224C6C1")
            gy_cids = [u32(GYREG_BASE + i * GYREG_STRIDE) for i in range(GYREG_COUNT)]
            check(gy_cids.count(DONOR_CID) == 1,
                  "the donor owns exactly ONE GY-action row")
            check(GYREG_STOCK_CID not in gy_cids,
                  "Sword of Sparkles no longer has a GY-action row (its equip/battle "
                  "clause in cls1[1042] is untouched and still live)")
            # Sword of Sparkles' OTHER record must be intact -- the regression oracle.
            sos = [i for i in range(CLS1_COUNT)
                   if u32(CLS1_BASE + i * CLS1_STRIDE) == GYREG_STOCK_CID]
            check(len(sos) == 1 and u32(CLS1_BASE + sos[0] * CLS1_STRIDE + 4) == 0x02204899,
                  "Sword of Sparkles' cls1 equip/battle record is untouched")

            # -- PART H: the cls2 record, and clause 3's two slots -----------------
            cls2_cids = [u16(CLS2_BASE + i * CLS2_STRIDE) for i in range(CLS2_COUNT)]
            check(all(cls2_cids[i] <= cls2_cids[i + 1] for i in range(CLS2_COUNT - 1)),
                  "cls2 is still sorted (binary-searched)")
            check(CLS2_PHANTOM not in cls2_cids,
                  f"cls2 phantom 0x{CLS2_PHANTOM:04X} was dropped")
            check(cls2_cids.count(DONOR_CID) == 1,
                  "the donor owns exactly ONE cls2 record")
            if DONOR_CID in cls2_cids:
                a = CLS2_BASE + cls2_cids.index(DONOR_CID) * CLS2_STRIDE
                s = struct.unpack_from("<5I", ov, _off(a) + 4)
                check(s == CLS2_SLOTS,
                      "cls2 slots: " + " ".join(f"0x{v:08X}" for v in s))
            # one cls1 + one cls2 under one cid is NOT the Warwolf shadow: that bug was
            # two records of the SAME class, where find_event_handler returns the leftmost.
            check(cls1_cids.count(DONOR_CID) == 1 and cls2_cids.count(DONOR_CID) == 1,
                  "one cls1 AND one cls2 record -- different classes, different "
                  "enumerators, so no find_event_handler leftmost shadow")
            slots = struct.unpack_from("<5I", ov, _off(cls1_addr(ov)) + 4)
            check(slots == CLS1_AFTER_C3,
                  "cls1 carries clause 3's +0C/+10 with the confirmed +04/+08/+14 intact")

            # -- PART I: the Defense-Position hook ---------------------------------
            check(code_reaches(rom, POS_SITE, ov5_cave.CAVE_JW_C2_POS),
                  f"the SS-commit argument load @0x{POS_SITE:08X} reaches CAVE_JW_C2_POS")
            check(struct.unpack_from("<H", ov, _off(0x022074E4))[0] == 0x9000,
                  "the commit's `str r0,[sp]` @0x022074E4 is unmoved (cid<<16)")

            # -- PART J: the ov5 stubs and the shared timing arm -------------------
            if rom is not None:
                for name, addr, fn, _doc in _C23_STUBS:
                    blob = fn(addr)
                    check(ov5_cave.read_cave(rom, addr, len(blob)) == blob,
                          f"{name} is present in ov5 @0x{addr:08X} ({len(blob)} B)")
            check(any(cid == DONOR_CID for cid, *_ in timinghook.ARMS),
                  "the donor is a registered arm on the SHARED timing-class hook "
                  "(without it, a cave pointer in +0x10 leaves the card unclassified)")
            timinghook.verify(ov, check, rom=rom)
            riderhook.verify(rom, ov, check)     # O15: the shared summon-rider hook
            check(any(cid == DONOR_CID for cid, *_ in riderhook.ARMS),
                  f"R 0x{DONOR_CID:04X} is a registered arm on the shared summon-rider hook "
                  f"(without it the GY revive would never banish itself)")


        return Compiled(installs=(install,), posts=(apply_card_prop_and_genre,), checks=(check_fn,))


jet_warrior_effects = synchro_jet_synchron_and_non_tuners_return_opponent_card_to_hand_in_graveyard_tribute_level_2_or_lower_special_summon_defense_banish_on_leave

SPEC = card(0x23EB, jet_warrior_effects())

PROPS = card_props("FIRE", "Warrior", level=5, atk=2100, defense=1200, card_type="Synchro Effect Monster")

main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_jet_warrior.nds")

# Names the KB proofs read from this module (verbatim).
from otn_enhanced.rom.game_constants import ERA2_CARD_TYPE_REVERSE

DONOR_CID = 0x23EB          # "Ignition Beast Volcannon" -- KEEPS this cid
JET_SYNCHRON_CID = 0x224C   # jet_synchron's donor -- the NAMED material
REFERENCE_SYNCHRO_CID = 0x23FE
NEW_CARD_TYPE = ERA2_CARD_TYPE_REVERSE["Synchro Effect Monster"]        # 37
GENRE_BIT_FUSION  = 29      # must be CLEARED
GENRE_BIT_SYNCHRO = 36      # must be SET
DONOR_GENRE_STOCK = 0x0000000420200402      # bits {1, 10, 21, 29, 34}
NEW_GENRE = ((DONOR_GENRE_STOCK & ~(1 << GENRE_BIT_FUSION))
             | (1 << GENRE_BIT_SYNCHRO))
FUSION_TABLE_A   = 0x02270B94
FUSION_ROW       = 155
FUSION_ROW_ADDR  = FUSION_TABLE_A + FUSION_ROW * 8          # 0x0227106C
FUSION_STOCK_M1  = 0x0007       # category code: Machine
FUSION_STOCK_M2  = 0x0004       # category code: Pyro
FUSION_DEAD_MATERIAL = 0x3FFF
NAMEDMAT_BASE    = 0x02275B04
NAMEDMAT_COUNT   = 23
NAMEDMAT_PHANTOM = 0x2524       # "Junk Berserker" -- not a card in this ROM
NAMEDMAT_ROW     = (DONOR_CID, JET_SYNCHRON_CID)
TWO_TUNER_CIDS  = (0x239F, 0x24B2)      # literal compares at 0x02248294/0x02248298
CLS1_BASE   = 0x022860D4
CLS1_STRIDE = 0x18
CLS1_INDEX  = 1279                                          # STOCK index only
CLS1_ADDR   = CLS1_BASE + CLS1_INDEX * CLS1_STRIDE          # 0x0228D8BC, STOCK only
CLS1_BEFORE = (0x02230C7D, 0x021D882D, 0x02203C5D, 0x021E51E5, 0x02234DA5)
CLS1_AFTER  = (0x02204911, 0x021DED49, 0x0224A115, 0x021E51E5, 0x02234DCD)

if __name__ == "__main__":
    verify() if "--verify" in sys.argv else main(write_text="--text" in sys.argv)
