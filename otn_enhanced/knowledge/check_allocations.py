"""Patch-slot allocation registry + collision guard.

Two card patches must never claim the same ov5 cave slot, phantom cid, or effect
registry row.  Before this module the only guard in the tree was one hand-copied
``assert`` list in ``shooting_quasar.py`` (which silently rots as patches
are added), and the ov5 cave map was a flat list of ``CAVE_*`` constants whose
only overlap check was ``install_cave``'s "is this exact slot zero?" — it cannot
see two slots that are adjacent-but-too-tight.

This module is the single ledger.  It:

  * derives the ov5-slot table by parsing ``ov5_cave.py``'s ``CAVE_*`` constants
    (address, size, owner, retired/legacy/diagnostic flags from the comments);
  * holds the phantom-cid / registry-row claims (:data:`PHANTOM_CLAIMS`) — the
    part that is NOT in ``ov5_cave.py``;
  * emits ``docs/engine/allocations.yaml`` (the committed ledger);
  * CHECKS: overlapping ov5 ranges (live slots only), any cid claimed by >1 owner
    within a pool, and drift between the committed ledger and the live
    ``ov5_cave.py``.

``main()`` returns non-zero on any violation and is wired into the build
(``apply_all_patches`` / ``_build_tg3``) so a duplicate allocation fails the
build before any ROM is written.

    uv run python -m otn_enhanced.knowledge.check_allocations
    uv run python -m otn_enhanced.knowledge.check_allocations --emit   # regenerate ledger
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
OV5_CAVE_PY = _ROOT / "otn_enhanced" / "effects" / "ov5_cave.py"
LEDGER = _ROOT / "otn_enhanced" / "docs" / "engine" / "allocations.yaml"

OV5_RAM_BASE = 0x022C5900
# The cave CEILING is derived from ov5_cave.py's RESERVE, never duplicated here:
# a stale second copy stops this guard flagging out-of-region slots.  See
# env._ov5_reserve and the KB fact mem.ov5_cave_can_grow.
from otn_enhanced.knowledge.env import OV5_END

# ---------------------------------------------------------------------------
# Phantom-cid / registry-row claims (the part not encoded in ov5_cave.py).
# Keyed by (pool, cid) -> owner; a duplicate (pool, cid) is a collision.
# Pools are distinct address spaces, so the SAME cid may legitimately appear in
# two different pools (e.g. 0x2347 is the X-Saber phantom AND a registry row).
# Seeded from the exploration of tg_table.py / xsaber_table.py / the patch
# modules; extend this when a new patch claims a phantom.
# ---------------------------------------------------------------------------
PHANTOM_CLAIMS: list[tuple[str, int, str]] = [
    # ARM9 T.G. set-code table @0x0209CB48 (count-neutral phantom drops)
    ("tg_setcode_table", 0x2510, "tg_striker"),
    ("tg_setcode_table", 0x2513, "tg_warwolf"),
    ("tg_setcode_table", 0x2514, "tg_rush_rhino"),
    ("tg_setcode_table", 0x2552, "hyper_librarian"),
    # ARM9 "Junk" set-code table @0x0209C842 (set code 0x50, sorted 13 x u16,
    # count hardcoded `movs r2,#0x0D` in thunk 0x02023E5C).  It shipped with two
    # phantoms, 0x2500 and 0x2524, which are Junk Servant's and Junk Berserker's
    # real Konami IDs (3DS CARD_Indx_E records 4532 / 4568).  junk_servant
    # spends 0x2500 on its own donor; 0x2524 is still free.
    ("junk_setcode_table", 0x2500, "junk_servant"),
    # ... and junk_speeder spends 0x2524.  This claim was MISSING until
    # (the comment above still said "0x2524 is still free" while the
    # shipped Junk Speeder build had been spending it).
    ("junk_setcode_table", 0x2524, "junk_speeder"),
    # ARM9 "Synchron" set-code table @0x0209C968 (set code 0x4C, sorted 15 x u16,
    # count hardcoded `movs r2,#0x0F` in thunk 0x02023E1C, ONE consumer).  It
    # shipped with a single phantom, 0x2501 -- a Konami-reserved Synchron id with
    # no card_prop record.  unknown_synchron spends it on its own donor.
    # This is the table `Tuning` 0x23A2 searches: its criteria row 1269
    # @0x02274F40 carries aux 0x004C == this set code.
    ("synchron_setcode_table", 0x2501, "unknown_synchron"),
    # ... and the table's LAST spare slot is not a phantom at all: entry 0 is
    # 0x0D6B "Speed Spell - Deceased Synchron", a real card with its own cls0
    # record[3], criteria rows 1-3 and effect-registry entry -- all untouched by
    # the drop.  Because it is a SPELL it was never reachable by any
    # monster-filtered "Synchron" search (Tuning's criteria row filters card type
    # MONSTER), so its membership was inert.  accel_synchron spends it.
    # Dropping it costs only "0x0D6B counts as a Synchron CARD".
    ("synchron_setcode_table", 0x0D6B, "accel_synchron"),
    # 0x1E4E Synchro Deflector -- a NORMAL TRAP, so inert for the same reason as 0x0D6B.
    # Spent by assault_synchron (add_synchron_member(out, 0x13AE, 0x1E4E)).
    # After this the list has NO inert slot.
    ("synchron_setcode_table", 0x1E4E, "assault_synchron"),
    # Assault Synchron's donor: Shapesnatch 0x13AE, records-free vanilla (donor_scan CLEAN;
    # its one u16 hit ov3:0x0217EAA0 is half of an ARM blx, not a cid).
    ("donor_cid", 0x13AE, "assault_synchron"),
    # Assault Synchron C2: count-neutral drops, each a no-card_prop cid owning exactly
    # one row and no other table rows in BOTH rom.nds and rom_all_patches.nds
    # (scratch/assault_pick_phantoms.py). 0x0EAD is also a dead effect-registry cid
    # (notes/shiens-dojo-findings.md) -- only its criteria row is touched.
    ("cls2_table", 0x0E19, "assault_synchron"),
    ("populate_table", 0x0EAD, "assault_synchron"),
    # 0x2414 Bri Synchron -- a REAL Tuner Synchron, spent by user decision for
    # revolution_synchron (the list had no inert slot left). Bri loses Tuning reach.
    ("synchron_setcode_table", 0x2414, "revolution_synchron"),
    # Revolution Synchron's donor: Acrobat Monkey 0x1649, records-free vanilla (donor_scan CLEAN;
    # its one chained ov3 u16 hit is the pointer 0x021F1649 in a cls0 record, not a cid).
    ("donor_cid", 0x1649, "revolution_synchron"),
    # Revolution Synchron C2: cls2 phantom 0x164F sits exactly at 0x1649's sorted index
    # (in-place cid rewrite, zero shift); ignition-condition registry phantom 0x1748 (released by
    # eclipse_wyvern, still present in rom_all_patches.nds). The GY-action row is VIRTUAL
    # (CAVE_REVSYN_VROW + four ov3 hooks), so no gy_action_registry row is claimed.
    ("cls2_table", 0x164F, "revolution_synchron"),
    ("ignition_cond_registry", 0x1748, "revolution_synchron"),
    # /!\ THIS GUARD CANNOT SEE THE REAL HAZARD HERE, so it is written down instead.
    # Four claims on 0x0209C968, all DIFFERENT slots -- 0x2501 (unknown_synchron),
    # 0x229E (steam_synchron), 0x0D6B (accel_synchron), 0x1E4E (assault_synchron) --
    # so this check passes.  But a "nothing else was lost" survival tuple that NAMES
    # another patch's slot aborts that patch's main() with no ledger warning.
    # steam_synchron.SYNCHRON_CORE was cleared of 0x0D6B and 0x1E4E for exactly
    # this reason.  A survival assertion is not a claim, so no ledger can catch it.
    # accel_synchron CLAUSE 1 -- the donor 0x11A3 is records-free, so the
    # cls3 record and the criteria row are both COUNT-NEUTRAL inserts that each drop a
    # phantom cid (no card_prop row) and shift, keeping count and sortedness exact.
    # Both phantoms were checked against PHANTOM_CLAIMS *and* against the CHAINED image
    # rom_all_patches.nds -- still present there, i.e. unspent (otn-register-phantom-
    # same-edit: a single-card ROM cannot see a phantom that a chained patch already
    # took).
    ("cls3_table", 0x0E13, "accel_synchron"),        # cls3[6],  dropped for the record
    ("populate_table", 0x0E17, "accel_synchron"),    # crit[15], dropped for the row
    # accel_synchron CLAUSE 3.  The donor cannot take a SECOND cls3
    # record -- find_event_handler returns the leftmost -- so clause 3 shares clause
    # 1's record through three ov5 turn splitters, and needs only its own criteria
    # row plus ARM9 spell-speed-2 membership.  Both phantoms re-checked against the
    # CHAINED image rom_all_patches.nds this session: still present, i.e. unspent.
    ("populate_table", 0x0E2A, "accel_synchron"),    # the SECOND criteria row (row 1)
    ("quickeffect_list", 0x0E5B, "accel_synchron"),  # ARM9 spell-speed-2 list 0x0209C118
    # XX-Saber Boggart Knight, RE-HOMED off Vampire Orchis 0x15D4 (a real
    # Effect Monster, borrowed only for her native "when Normal Summoned" cls1 record)
    # onto the records-free vanilla Molten Behemoth 0x13A5. The trigger is now built
    # from three DATA rows -- summon.trigger_is_a_membership_list, the in-game-confirmed
    # Hanzo clause-1 recipe -- so each costs one count-neutral phantom drop. All three
    # phantoms were checked against this ledger AND against the CHAINED image
    # rom_all_patches.nds (still present there, i.e. unspent) before being claimed.
    ("donor_cid", 0x13A5, "boggart_knight"),
    # Mystic Piper, RE-HOMED off Ancient Gear Cannon 0x19BB (a real Effect
    # Monster, borrowed only for its native TARGETLESS ignition framework) onto the
    # records-free vanilla Flame Dancer 0x13B8.  The migration note filed this card as
    # Tier C "donor-locked" behind an "ignition-offer gate"; there is no such gate --
    # upstart_golden_ninja already ships an ignition on a vanilla, and the three
    # framework slots this card uses (+0C 0x021F06E8, +10 0x021E50CC, +08/+14 NULL) are
    # CID-BLIND by disassembly.  So the card is ONE count-neutral cls3 insert.
    # 0x1436 was checked against this ledger AND against the CHAINED image
    # rom_all_patches.nds (still at cls3[67] there, i.e. unspent) before being claimed.
    ("donor_cid", 0x13B8, "mystic_piper"),
    # Psi-Reflector C1 (2026-09-15. Donor Clown Zombie 0x1008: all 12 donor_scan
    # occurrences classified non-cid (notes/psi-reflector-findings.md). Phantoms: no card_prop, unclaimed,
    # same row count in rom.nds AND rom_all_patches.nds. Set code 0x6E ("Meklord Army", 4 phantoms, no
    # consumer) is claimed whole: its thunk literal is repointed to CAVE_PSI_GROUP.
    ("donor_cid", 0x1008, "psi_reflector"),
    ("summon_list_c7", 0x0E7F, "psi_reflector"),
    ("summon_list_c9", 0x167C, "psi_reflector"),
    ("cls1", 0x0E38, "psi_reflector"),
    ("populate_table", 0x0E75, "psi_reflector"),
    ("setcode_index", 0x6E, "psi_reflector"),
    # Psi-Reflector C2 (2026-09-15. 0x0E40 is a whole phantom (one cls3 + one
    # criteria row, both retired); 0x0E3A owns one criteria row (its orphan cls2 record is untouched).
    ("cls3_table", 0x0E40, "psi_reflector"),
    ("populate_table", 0x0E40, "psi_reflector"),
    ("populate_table", 0x0E3A, "psi_reflector"),
    ("cls3_table", 0x1436, "mystic_piper"),         # phantom dropped for the ignition record
    # Cardcar D clause 2, the Mystic Piper recipe on records-free vanilla
    # Mushroom Man 0x0FAE (donor_scan CLEAN).  0x0EC8 has no card_prop row and was
    # checked against this ledger AND rom_baseline.nds (still at cls3[40]) before claiming.
    ("donor_cid", 0x0FAE, "cardcar_d"),
    # Metal Armored Bug (stats + text only) spends Basic Insect 0x0FD8; claimed
    # after donor_scan --free re-offered it.
    ("donor_cid", 0x0FD8, "metal_armored_bug"),
    ("cls3_table", 0x0EC8, "cardcar_d"),            # phantom dropped for the ignition record
    # Cardcar D clause 1: ARM9 "Cannot be Special Summoned" list 0x0209BD6C (48 x u16,
    # read by 0x02023398 on the SS gate 0x021BA69C) -- the NDS twin of the 3DS list that
    # holds Cardcar D. 0x193B is one of its three phantoms (no card_prop row).
    ("cannot_ss_list", 0x193B, "cardcar_d"),
    # Kuribandit (on records-free vanilla Torike 0x0FD5
    # (donor_scan CLEAN).  All three phantoms have no card_prop row and were checked against
    # this ledger AND rom_baseline.nds: cls1 0x1441 (one row), criteria 0x0E34 (one row),
    # End-Phase registry row 188 {0x02253F89, 0x1A1F} (only the cid halfword is rewritten).
    ("donor_cid", 0x0FD5, "kuribandit"),
    ("cls1_table", 0x1441, "kuribandit"),
    ("populate_table", 0x0E34, "kuribandit"),
    ("registry_row", 0x1A1F, "kuribandit"),
    # Soul Charge (on Breath of Light
    # 0x123D: its cls0 row is
    # rewritten in place, and one criteria row {0x123D, 0xFFFF, 0x0223C9D1, 0x00010002}
    # is inserted count-neutrally by dropping phantom 0x12D6's only row. 0x12D6 has no
    # card_prop row, no tsv name, is not in list A, and was checked against this ledger
    # AND rom_all_patches.nds (still one row there) before being claimed.
    ("donor_cid", 0x123D, "soul_charge"),
    ("populate_table", 0x123D, "soul_charge"),
    ("populate_table", 0x12D6, "soul_charge"),       # phantom row dropped
    # Clause 3 posts the turn node of 0x0EBD (no card_prop; a non-collectible BP-lock card)
    # because the Battle Phase gate 0x0224CD84 checks a fixed cid chain. Registered so a
    # second patch borrowing the same node shows up as a double claim.
    ("bp_lock_node_borrow", 0x0EBD, "soul_charge"),
    ("summon_list_c7", 0x0E74, "boggart_knight"),   # code-7 Normal-Summon membership list
    ("cls1", 0x0E11, "boggart_knight"),             # the cls1 record (Boggart 0x2346's, verbatim)
    ("populate_table", 0x0E20, "boggart_knight"),   # the criteria row ("Level<=4 X-Saber", from HAND)
    # ARM9 X-Saber set-code table @0x0209CB6E
    ("xsaber_setcode_table", 0x2347, "boggart_knight"),
    ("xsaber_setcode_table", 0x2346, "darksoul"),
    # ARM9 Karakuri set-code table @0x0209CC16 (22 entries, count hardcoded in the
    # consumer thunk).  It shipped with exactly TWO phantoms and both are now spent.
    ("karakuri_setcode_table", 0x1140, "ninishi"),
    ("karakuri_setcode_table", 0x2445, "karakuri_haipa"),
    # cls1 dispatch table @0x022860D4 (count-neutral phantom drop)
    # ⚠️ THIS ONE TABLE IS CLAIMED UNDER TWO POOL NAMES -- "cls1" here and
    # "cls1_table" further down (maiden_eyes_of_blue 0x1DB6, azure_eyes 0x1C27).
    # All four cids were confirmed to be rows of the SAME physical
    # table 0x022860D4, so the split means a cross-name duplicate would NOT be
    # caught by the (pool, cid) check.  Until they are unified, check BOTH lists
    # by hand before claiming a cls1 phantom.
    ("cls1", 0x0ECC, "karakuri_haipa"),
    ("cls1", 0x1048, "orient_dragon"),
    # cls2 / populate binary-searched tables (count-neutral phantom drops)
    ("cls2_table", 0x1175, "shooting_quasar"),
    ("cls2_table", 0x0E66, "hyper_librarian_chain"),
    ("cls2_table", 0x2511, "tg_warwolf"),
    ("populate_table", 0x2511, "tg_warwolf"),           # NOT dropped: E2's Deck search reads 0x2511's own row (Joyeuse ate it once)
    ("cls2_table", 0x234E, "tg_rush_rhino"),
    ("populate_table", 0x2346, "tg_rush_rhino"),
    # ⚠️ CORRECTED: this line used to read ("populate_table", 0x2347,
    # "tg_striker"), which is wrong -- tg_striker drops 0x2347 from CLS2
    # (its CLS2_PHANTOM) and 0x234E from populate (its POP_PHANTOM). The mislabel
    # mattered the moment wattcobra registered its REAL populate claim on
    # 0x2347 (below): the guard would have reported a phantom collision that does
    # not exist, and hidden the fact that the cls2 claim was unregistered.
    ("cls2_table", 0x2347, "tg_striker"),
    ("populate_table", 0x234E, "tg_striker"),
    # retargeted code literals (a live literal repointed at a non-existent cid so a
    # native sub-effect can never match; the cid must stay unused by every patch)
    ("lp_literal", 0x2617, "safe_zone"),
    # The Gates of Dark World: the donor Colosseum - Cage of the Gladiator Beasts
    # 0x1C8B natively accrues counters ("place 1 Counter each time a monster is
    # Special Summoned from either player's Deck"). Killed twice over, each by
    # repointing a plain equality test at a cid with no card_prop record:
    #   * the arm-call literal @0x022666AC (bl 0x02244418 @0x0226638E), and
    #   * the continuous-trigger registry row 117 @0x022758BC (0x02275510+117*8).
    # Both are equality tests, not ordered chains, so no sort-interval constraint
    # applies. NB cid 0 in the trigger registry means UNCONDITIONAL -- never use it.
    ("lp_literal", 0x2500, "gates_of_dark_world"),
    ("counter_trigger_registry", 0x2500, "gates_of_dark_world"),
    # The Gates of Dark World CLAUSE 2 -- "Once per turn: banish 1 Fiend from your
    # GY; discard 1 Fiend, then draw 1". Four count-neutral sorted inserts plus a
    # 28 B ov3 stub (see OV3_CLAIMS). The donor needs TWO criteria rows in two
    # different zones, which needs LIST B membership (row = param & 0x10000000)
    # AND the param provider 0x02234E78 to return that bit -- see the KB fact
    # dispatch.two_row_criteria_is_list_b_plus_l2.
    ("populate_table", 0x178C, "gates_of_dark_world"),   # phantom dropped (row 287)
    ("populate_table", 0x1795, "gates_of_dark_world"),   # phantom dropped (row 288)
    ("populate_table", 0x1C8B, "gates_of_dark_world"),   # the donor's TWO rows
    # ⚠️ NEW POOL. LIST B @0x02271314 (27 x u16, sorted, count immediate
    # `movs r2,#0x1b` @0x02243C06) is the "this cid owns a two-row criteria pair"
    # list. It cannot grow -- 0x0227134C immediately begins LIST A -- so a new
    # member must displace one. 0x234F is the only phantom in it.
    # NB 0x234F is ALSO claimed by sea_lancer, but in the populate_table pool (it
    # drops 0x234F's second criteria row). Different resource, no conflict: a
    # phantom with one row left has no business in a two-row list anyway.
    ("membership_list_b", 0x234F, "gates_of_dark_world"),  # phantom evicted
    ("membership_list_b", 0x1C8B, "gates_of_dark_world"),  # the donor
    ("cls3_table", 0x1AF0, "gates_of_dark_world"),       # phantom dropped (owns TWO records)
    ("cls3_table", 0x1C8B, "gates_of_dark_world"),       # the donor's cls3 record
    # ⚠️ NEW POOL. The "draw N cards" count table @0x022704A4 ({u16 cid, s16 n},
    # 189 rows, stride 4, sorted; count immediate `movs r2,#0xbd` @0x02206324),
    # binary-searched by 0x02206304 for the slot1 resolver 0x022065B9.
    ("draw_count_table", 0x1B1A, "gates_of_dark_world"),  # phantom dropped (row 70)
    ("draw_count_table", 0x1C8B, "gates_of_dark_world"),  # the donor, n = 1
    # (WITHDRAWN after in-game test #3: the 0x0228EF48 "my HAND selection is
    #  filtered by my criteria row" insert did NOTHING for the effect discard --
    #  0x0225A3F0 keys that lookup on [0x0229DE94+0x0A], which the request-driven
    #  discard never sets to the acting cid (measured 0x0004; that field holds the
    #  PICKED HAND INDEX, written by 0x02259EE0). The list and its 2 B alignment
    #  pad at 0x0228EF86 are RESTORED to stock. The Fiend restriction is now done
    #  by the ov5 filter CAVE_GDW_FILT, which wraps the discard window's legality
    #  callback -- see ov5_cave.py.)
    # Shien's Dojo: the donor Ancient Gear Castle's NATIVE counter accrual
    # (0x02265F96, "place 1 type-1 counter each Normal Summon") is killed by
    # repointing its cid literal @0x02265FF8 at a cid with no card_prop record.
    # A plain equality test, so no sort-interval constraint applies here.
    ("lp_literal", 0x1A50, "shiens_dojo"),
    # Escuridao retires two of Darkbright's native sub-effects by overwriting the
    # cid with an unused one. The "defense-flip" family is an ORDERED comparison
    # chain over {0x14D6, 0x1993, 0x1C08, 0x1DA6, 0x237F}, so 0x1994 was chosen to
    # sit exactly where 0x1C08 did (between 0x1993 and 0x1DA6) -- a phantom outside
    # that interval would mis-route the other four cards' lookups.
    ("lp_literal", 0x1994, "escuridao"),
    # battle-attribute piercing list @0x0226D764 (49 sorted entries, hard-coded
    # count): 0x1B8E keeps the sort order between 0x1B86 and 0x1C54.
    ("pierce_list", 0x1B8E, "escuridao"),
    # Maiden with Eyes of Blue CLAUSE 2 (records-free Tuner donor Comrade Swordsman
    # of Landstar 0x1ED7). Two count-neutral sorted inserts, each dropping a phantom
    # that has no card_prop record and owns exactly one row, plus two ov5 slots
    # (CAVE_MAIDEN_COND / CAVE_MAIDEN_RES, declared in ov5_cave.py).
    ("cls1_table", 0x1DB6, "maiden_eyes_of_blue"),      # phantom dropped for the donor's cls1 record
    ("populate_table", 0x1BBE, "maiden_eyes_of_blue"),  # phantom dropped for the donor's criteria row
    # CLAUSE 1: one more count-neutral insert, into cls3. The phantom
    # 0x1C80 has no card_prop record, owns exactly one cls3 row, and its cid appears
    # exactly ONCE as an aligned u32 anywhere in overlay 3 -- in that very row.
    # ⚠️ IT WAS ALSO CHOSEN FOR ITS ROW INDEX. shiens_dojo (cls3 rows 223/233)
    # and sea_lancer (cls3 row 527) both anchor into this table BY INDEX. A
    # count-neutral swap leaves every index above max(drop, insert) untouched, and
    # 233 < 334 < 451 < 527, so neither of those anchors moves. Any future cls3
    # insert must re-check that arithmetic before picking its phantom.
    ("cls3_table", 0x1C80, "maiden_eyes_of_blue"),      # phantom dropped for the donor's cls3 record
    # Clause 1 is a QUICK EFFECT, and the engine enforces spell speed: 0x021EDA4C
    # refuses a responder whose speed is below the activation's, and a monster only
    # gets speed 2 by being in the sorted 118-entry ARM9 list at 0x0209C118 (the
    # list that already holds Blue-Eyes Shining Dragon 0x17C2, D.D. Crow, Kuriboh,
    # Doomcaliber Knight...). Count-neutral insert over phantom 0x1A86 -- the count
    # is a hard-coded `movs r2,#0x76` at 0x02023490 and the list is BINARY-searched,
    # so it must stay the same length and sorted.
    ("quickeffect_list", 0x1A86, "maiden_eyes_of_blue"),
    # The donor cid itself, so a future patch cannot pick 0x1ED7 as "records-free"
    # (it no longer is) and so clause 1's future cls3 record is filed against the
    # same owner rather than looking like a second card.
    ("donor_cid", 0x1ED7, "maiden_eyes_of_blue"),
    # ---------------------------------------------------------------------
    # Azure-Eyes Silver Dragon, clause 3 only. Donor Ally of Justice
    # Light Gazer 0x1E9C -- records-free in all four cls tables, no criteria row,
    # no registry row, absent from the Fusion tables and LIST_A.
    # ---------------------------------------------------------------------
    ("donor_cid", 0x1E9C, "azure_eyes"),
    # cls1: count-neutral insert of the donor's Standby-Phase record. Phantom
    # 0x1C27 has no card_prop record, owns exactly ONE cls1 row, and appears
    # exactly once as an aligned u32 in overlay 3 -- in that very row. It sits at
    # cls1[668]; no shipped patch anchors cls1 BY INDEX (sea_lancer and
    # shooting_quasar both search by cid, armory_arm scopes by a cid literal), so
    # the shift is safe. Re-check that if a future patch starts index-anchoring.
    ("cls1_table", 0x1C27, "azure_eyes"),
    # criteria/populate registry: count-neutral insert of the "1 Normal Monster in
    # your GY" row. Phantom 0x1ABE, no card_prop, owns exactly one row.
    ("populate_table", 0x1ABE, "azure_eyes"),
    # Effect registry 0x0228E1E0 row 341, inside the Standby-Phase section
    # (base 0x0228EB08, count 0x88). The row already carried the generic Standby
    # resolver 0x02256F7D with the INERT phantom cid 0x16FE; only the cid field is
    # rewritten, so the section keeps its hard-coded length. The section is walked
    # linearly and is NOT sorted, so no ordering constraint applies. Six further
    # phantom rows on the same resolver remain free: 0x1338, 0x18F8, 0x1147,
    # 0x11CF, 0x11EA, 0x0E9B.
    ("registry_row", 0x16FE, "azure_eyes"),
    # ARM9 "Ally of Justice" set-code table 0x0209CB96 (21 entries, hard-coded
    # `movs r2,#0x15`, one consumer at 0x02023B70). The donor is removed by shifting
    # the tail left and refilling the vacated LAST slot with the sentinel cid 0x2700
    # (a phantom above every real cid -- max is 0x24E8), leaving the count immediate
    # untouched. There is no phantom anywhere in 0x1E94..0x1E9F to substitute in
    # place, and BOTH simpler removals collide with elder_six_samurai PART E,
    # which edits this same table: it asserts STRICT sortedness (so a duplicated
    # neighbour trips it) and hardcodes 21 as the count it expects (so decrementing
    # trips it). The sentinel keeps the array the same length AND strictly sorted, so
    # the two patches compose in either order -- both verified.
    ("aoj_setcode_table", 0x1E9C, "azure_eyes"),
    # ⚠️ The "populate_table" pool IS the table at 0x022713C4 -- boggart_knight calls it
    # POP_BASE, notes/sea-lancer-findings.md calls it the criteria registry. Same 1388 x 12 sorted
    # array, binary-searched by 0x02243B9C. Sea Lancer's E1 row for cid 0x1FFC is a count-neutral
    # insert into it; 0x234F is a phantom cid that owned TWO identical-cid rows, so dropping the
    # second cannot orphan a real card. It MUST be claimed in this pool and not a new one --
    # filing it under a separate name would hide it from the duplicate check.
    ("populate_table", 0x234F, "sea_lancer"),
    # Shien's Dojo clause 2. The criteria-registry row 409 was ITSELF a phantom
    # (cid 0x19B5, no card_prop) sitting between 0x19B1 and 0x19B6, so the donor's
    # row overwrites it in place -- no shifting, sort order preserved.
    ("populate_table", 0x19B5, "shiens_dojo"),   # phantom row consumed
    ("populate_table", 0x19B2, "shiens_dojo"),   # the donor's criteria row
    # cls3 record for the donor: count-neutral insert that drops phantom 0x1941.
    ("cls3_table", 0x1941, "shiens_dojo"),       # phantom dropped to make room
    # Eclipse Wyvern clause 1. Naturia Cliff 0x2034 is edited ENTIRELY IN PLACE --
    # no phantom is consumed and nothing is inserted or shifted, because the donor
    # already owns exactly one criteria row and one cls2 record. The claims below
    # exist so a future patch cannot silently reuse the same donor's slots.
    # Eclipse Wyvern clause 1 (records-free Normal Monster donor 0x1859, no real card
    # consumed). Two count-neutral sorted inserts, each dropping a phantom that has no
    # card_prop record, plus an ov3 dead-code stub (see OV3_CLAIMS below).
    ("cls2_table", 0x194A, "eclipse_wyvern"),       # phantom dropped for the donor's cls2 record
    ("populate_table", 0x18F8, "eclipse_wyvern"),   # phantom dropped for the donor's criteria row
    # ⚠️ The trigger is the donor's NATIVE membership in the any-means sent-to-GY
    # dispatcher list30 @0x0226E904 (index 20). Nothing is written there -- the patch
    # DEPENDS on it and asserts it. list30 is FULL (30/30 real cards, no phantom) and
    # cannot grow (0x0226E940 begins another sorted list), so any future card wanting
    # this trigger must likewise pick a donor that is already a member.
    # Eclipse Wyvern's TRIGGER: a row in the LEAVE-MASK table 0x0226EC1C ({u16 cid,
    # s16 mask}, 152 rows, stride 4, sorted), count-neutral over phantom 0x16F5.
    # Mask 0x0800 = "sent to the Graveyard", ANY source zone -- the Dandylion family.
    # ⚠️ Eclipse Wyvern must NOT be added to list30 (0x0226E904): that table's arm is
    # gated on "left the FIELD", and setting its flag makes the dispatcher SKIP this
    # mask table entirely (0x021C80FE). An earlier build did exactly that and the
    # effect only fired on a field->GY leave, never on a discard or a mill.
    ("leave_mask_table", 0x16F5, "eclipse_wyvern"),   # phantom dropped to make room
    # ---------------------------------------------------------------------
    # Snoww, Unlight of Dark World, CLAUSE 1. Donor Renge,
    # Gatekeeper of Dark World 0x1C18 -- a records-free vanilla Normal Monster
    # that is ALREADY DARK / Fiend / Level 4 and ALREADY a member of the ARM9
    # "Dark World" set-code list @0x0209CA22, so no set-code table is touched.
    # Two count-neutral inserts plus the ov3 trigger stub in OV3_CLAIMS below.
    # ---------------------------------------------------------------------
    ("donor_cid", 0x1C18, "snoww"),
    # ⚠️ NEW POOL, added after an IN-GAME finding. The ARM9 "Dark World"
    # set-code table @0x0209CA06 (16 x u16, sorted, BINARY-SEARCHED, count immediate
    # `movs r2,#0x10` @0x020238B8, consumer thunk 0x020238B5 = has_set_code index
    # 0x0F). Snoww's search filters on aux 0x000F = membership of THIS list, and
    # the user found in-game that "The Gates of Dark World" could not be fetched --
    # its donor Colosseum 0x1C8B was in no set-code table at all after that patch's
    # PART E dropped it from Gladiator Beast. gates_of_dark_world PART E2 now
    # joins it here, count-neutral over the phantom 0x0EC9 (no card_prop, so its
    # membership was inert). ⚠️ 0x0EC9 is ALSO one of the seven cids in the
    # effect-discard arm 0x021D185C (event.dark_world_discard_arm) -- a DIFFERENT
    # table, unaffected, and a cid with no card_prop can never reach either.
    ("dw_setcode_table", 0x0EC9, "gates_of_dark_world"),   # phantom dropped
    ("dw_setcode_table", 0x1C8B, "gates_of_dark_world"),   # the donor joins
    # cls2: {+04 0x02207EF5 add-to-hand, rest 0} = the Sangan/Scarr MANDATORY
    # shape. Phantom 0x1B45 has no card_prop record, owns exactly ONE cls2 row
    # (index 245), and its cid appears exactly once as an aligned u32 anywhere in
    # overlay 3 -- in that very row -- and never in ARM9.
    ("cls2_table", 0x1B45, "snoww"),
    # criteria registry: {aux 0x000F = the Dark World set code, fn 0x0223CAF5 =
    # search the DECK, word 0x0000000E = any CARD type} -- the 3DS's own Snoww
    # row 0 (cid 0x25F1, handler 0x004B1C1C), with the handler mapped by Scarr
    # 0x196A, which owns a byte-identical row in BOTH builds. Phantom 0x14E7 has
    # no card_prop, owns exactly one row (index 165) and is in neither membership
    # list, so dropping it cannot change any cid's block size. It sits BELOW the
    # donor's insert point (554), and dragon_shrine's index-anchored
    # crit[157] is below that window, so nothing index-anchored moves.
    ("populate_table", 0x14E7, "snoww"),
    # ---------------------------------------------------------------------
    # Snoww CLAUSE 2 -- "if it was an OPPONENT's card effect, you
    # can target 1 monster in your opponent's GY; ... Special Summon it in
    # face-up Defense Position". Cloned structurally from GOLDD, WU-LORD OF
    # DARK WORLD 0x1969, whose printed text is identical in shape.
    # ---------------------------------------------------------------------
    # the donor's SECOND criteria row (opponent's GY), adjacent to row 0.
    # Phantom 0x14EF: no card_prop, exactly one row (index 168), in neither
    # membership list, 3 u16 occurrences build-wide.
    ("populate_table", 0x14EF, "snoww"),
    # ⚠️ NEW POOL. LIST A @0x0227134C (59 x u16, STRICTLY sorted, binary-searched,
    # count immediate `movs r2,#0x3b` @0x02243BF0) is the OTHER "this cid owns a
    # two-row criteria pair" list; its rule is `row = (param != 0) ? 1 : 0`
    # (`cmp r4,#0` @0x02243BFA), which any nonzero param satisfies -- so unlike
    # LIST B it needs NO L2 membership. Chosen precisely because LIST B is full
    # and gates_of_dark_world owns both its phantom 0x234F and the L2 lookup stub
    # CAVE_GDW_L2; using LIST A keeps the two cards completely disjoint.
    # 0x0D7A (Speed Spell - Preparation of Rites) is one of the only TWO LIST A
    # members owning ZERO criteria rows, so its membership was inert
    # (dispatch.list_a_has_two_inert_members). 0x0D81 remains as the last spare.
    ("membership_list_a", 0x0D7A, "snoww"),   # inert member evicted
    ("membership_list_a", 0x1C18, "snoww"),   # the donor
    # ---------------------------------------------------------------------
    # Grapha, Dragon Lord of Dark World CLAUSE 1 -- "You can Special
    # Summon this card (from your Graveyard) by returning 1 'Dark World' monster
    # you control to the hand, except 'Grapha'". Donor Zure, Knight of Dark World
    # 0x1961: a records-free vanilla Normal Monster, already DARK / Fiend, and
    # ALREADY entry 0 of the ARM9 Dark World set-code list @0x0209CA06 -- so this
    # patch claims NOTHING in dw_setcode_table, which matters because
    # gates_of_dark_world spent that list's last phantom.
    # Template: Blackwing - Zephyrus the Elite 0x241C (same sentence, different
    # archetype), whose +04 resolver and +10 bounce-cost machine are reused as-is.
    # ---------------------------------------------------------------------
    ("donor_cid", 0x1961, "grapha"),
    # cls2: {+04 0x02230EBD Zephyrus's resolver, +08 CAVE_GRAPHA_FILT,
    # +0C CAVE_GRAPHA_GATE, +10 0x021EB1B1 the shared bounce-cost machine, +14 0}.
    # Phantom 0x1A86 has no card_prop record, owns exactly ONE cls2 row (index
    # 219) and that row is its ONLY aligned occurrence in overlay 3; it is the
    # nearest unclaimed phantom above the donor's insert point, so the sorted
    # insert shifts the fewest rows. (0x194A, which is nearer, is eclipse_wyvern's
    # -- the check_allocations guard caught that collision before the build.)
    ("cls2_table", 0x1A86, "grapha"),
    # ⚠️ NEW POOL. The GY-ACTION registry @0x0228DDF8 (60 x 0x10 B,
    # {u32 cid, u32 zone, u32 check_fn, u32 post_fn}, zone 0x0E = Graveyard) is
    # the gate that decides whether a card's Graveyard effect is ever offered
    # (dispatch.gy_action_registry). It is UNSORTED and LINEAR-scanned with a
    # hard-coded `cmp rX,#0x3C`, so a row is claimed IN PLACE -- no shifting, and
    # count-neutral by construction. Row 15 already carried exactly the shape
    # needed ({zone 0x0E, chk 0x0224C591, post 0x0224C6C1} -- the 45-row
    # GY-EFFECT family that Plaguespreader Zombie, Glow-Up Bulb and Zephyrus
    # himself belong to) under the phantom cid 0x0EB2, whose membership was inert
    # because no card_prop record can ever reach it. FIVE phantom rows remain
    # (0x1449, 0x144C, 0x1452, 0x0E3E, 0x0E64) but only 0x0E3E / 0x0E64 are in
    # this family; 0x1449 / 0x144C / 0x1452 carry chk 0x0224C55D.
    ("gy_action_registry", 0x0EB2, "grapha"),   # phantom row 15 reclaimed
    ("gy_action_registry", 0x1961, "grapha"),   # the donor takes it
    # ⚠️ CLAUSE 2, WHEN IT LANDS, will need a SECOND criteria row on 0x1C18 plus
    # membership of the two-row list. LIST B @0x02271314 is FULL and its only
    # phantom (0x234F) is spent by gates_of_dark_world -- but LIST A @0x0227134C
    # (59 entries, count immediate `movs r2,#0x3b` @0x02243BF0, rule
    # row = (param != 0) ? 1 : 0) has TWO members that own ZERO criteria rows,
    # 0x0D7A and 0x0D81 (both Speed Spells), so their membership is vestigial and
    # one can be dropped count-neutrally. Claim it as pool "membership_list_a"
    # then, NOT as a LIST B claim.
    # (RELEASED: PART F's condition-table row for 0x1748 is WITHDRAWN.
    #  Setting cls2 +0C to the native condition 0x021F0BDD stopped the trigger firing
    #  from the HAND and the DECK while it still fired from the field -- its act half
    #  0x021F6565 = 0x021BABE8(side) does not hold while a discard/mill resolves, so
    #  the event was refused at admission. The empty-deck guard now lives in the
    #  PART H ov5 wrapper, which runs only AFTER the event is admitted.)
    ("cls3_table", 0x19B2, "shiens_dojo"),       # the donor's cls3 record
    # continuous-trigger registry rows @0x02275510 (181 x 8 B, {handler, cid};
    # both walkers 0x02248154 / 0x022481C0 hard-code CMP #0xB5, and the table
    # butts against synchro LIST_A @0x02275AB8 with ZERO spare bytes -- so a new
    # row must overwrite one of the 16 rows whose cid has no card_prop record.
    # NOTE: this is a DIFFERENT table from the "registry_row" pool below, which
    # is the effect registry @0x0228E1E0.
    ("counter_trigger_row", 0x2349, "shiens_dojo"),   # the dead row consumed (row 137)
    ("counter_trigger_row", 0x19B2, "shiens_dojo"),   # the donor cid now in it
    # effect-registry rows @0x0228E1E0 (End-Phase-trigger phantom rows stolen)
    ("registry_row", 0x1A9F, "tg_striker"),
    ("registry_row", 0x2347, "tg_warwolf"),
    # ⚠️ REGISTERED, LATE, AFTER IT COST A 25-MINUTE CHAIN BUILD.
    # tg_warwolf.POP_PHANTOM has always been 0x234A and its criteria row has
    # always been the one this patch drops -- but the claim was never entered here,
    # so check_allocations reported "no phantom double-claims" while jet_synchron
    # was independently written to drop the SAME row. The single-card build could
    # not see it (Warwolf is not applied there); the chain build died at step 48
    # with "phantom 0x234A owns 0 row(s)". THE LEDGER IS ONLY A BACKSTOP IF THE
    # CLAIM IS IN IT -- when a patch consumes a phantom, register it in the SAME
    # edit that consumes it.
    ("populate_table", 0x234A, "tg_warwolf"),

    # XX-Saber Darksoul, RE-HOMED off Deep Diver 0x1CE6 (a real Effect
    # Monster) onto the records-free vanilla Gigobyte 0x1783, using the donor-free
    # End-Phase deck-search recipe already in-game confirmed on tg_striker/tg_warwolf.
    # The old build ALSO stole Manticore of Darkness 0x16F9's End-Phase registry row
    # @0x0228E478; it now repurposes phantom row 119 @0x0228E598 instead, so both real
    # cards are handed back (darksoul._assert_donors_untouched pins them).
    # The stale ("registry_row", 0x1CDE) claim below was never the row this patch took --
    # 0x1CDE was the cls2 phantom the old build rewrote for byte-fidelity with a
    # reference ROM that verify_against_proven no longer compares against. Removed.
    # All three phantoms were checked against this ledger AND against the CHAINED image
    # rom_all_patches.nds (still present there, i.e. unspent) before being claimed.
    ("donor_cid", 0x1783, "darksoul"),
    ("registry_row", 0x0E6C, "darksoul"),      # phantom row 119, resolver+cid both rewritten
    ("cls2_table", 0x0E15, "darksoul"),        # phantom dropped for the donor's cls2 record
    ("populate_table", 0x0E21, "darksoul"),    # phantom dropped for the donor's criteria row
    # Lightpulsar Dragon clause 1 (records-free Normal Monster donor 0x0FB1, Sword Arm
    # of Dragon). "SS from hand by banishing 1 LIGHT + 1 DARK from GY" needs a PAIR of
    # criteria rows -- param is the row index within the cid's block -- so the insert
    # drops BOTH rows of phantom 0x0E79, chosen because it owns exactly two rows and is
    # in neither membership list nor the disambiguation switch (dropping it whole
    # therefore cannot orphan a cid or change any other card's block size).
    ("populate_table", 0x0E79, "lightpulsar"),   # phantom, both rows dropped
    ("populate_table", 0x0FB1, "lightpulsar"),   # the donor's LIGHT+DARK row pair
    # ⚠️ 2-ROW BLOCKS ARE ONLY ADDRESSABLE VIA A MEMBERSHIP LIST. 0x02243B9C returns
    # the LEFTMOST row for a cid plus r4, and r4 = 1 only for cids in list A
    # @0x0227134C (59) or list B @0x02271314 (27); 3-4 row blocks instead need a case
    # in the compiled switch @0x02243C1C. Without the list-A entry the donor's param-1
    # pass re-reads the LIGHT row and the DARK half of the cost silently vanishes.
    ("membership_list_a", 0x0E6B, "lightpulsar"),  # phantom dropped to make room
    ("membership_list_a", 0x0FB1, "lightpulsar"),  # the donor
    # ⚠️ IN-PLACE ov3 CODE EDITS (no cave, so clause 1 works in puzzles too):
    #   * the DEAD dispatch arm 0x0225E6E0/0x0225E6E6 -- its only reaching cids were
    #     phantoms 0x0E1F / 0x0ECA.
    #   * the required-count branch 0x0225CF5E -> the return-1 leaf.
    # ⚠️ CORRECTED: the note here used to say "THREE other dead arms remain
    # unclaimed for future cards". They are NOT interchangeable. An arm can only be
    # re-aimed at a cid that BOTH reaches its guard AND is within base +/- imm8 of it,
    # and measured over the whole cid space the windows of 0x0225E67C (0x0DA6..0x0E1E)
    # and 0x0225E692 (0x0E20..0x0E3F) contain NO MONSTER AT ALL -- only Speed Spells
    # and phantoms. 0x0225E88E (window 0x15C7..0x164C) was the last usable one and
    # Darkflare took it. A further banish-cost card needs a different mechanism.
    ("handss_dead_arm", 0x0225E6E6, "lightpulsar"),
    ("handss_count_branch", 0x0225CF5E, "lightpulsar"),
    # ⚠️⚠️ THE ROW THAT ACTUALLY MAKES A COST-SUMMON COST ANYTHING. The SUMMON-PROCEDURE
    # REGISTRY @0x0228F158 ({u32 cid, u32 handler}, stride 8, 133 rows, strictly sorted,
    # binary-searched by 0x02022E44 from BOTH 0x02264DAE and 0x022651C0, row count a
    # hard-coded imm8 `movs r2,#0x85` in BOTH). The hand-SS tree only sets a BITMASK bit
    # meaning "can be Special Summoned from hand" -- WHICH cost to pay comes from here.
    # A cid with no row takes the searcher's not-found branch (beq 0x02264DC2) and the
    # card summons for FREE: that was in-game failure #1 AND #2 of this card. Handler
    # 0x0226292D is the banish-cost payment state machine shared with the Chaos family.
    ("summon_procedure_table", 0x0ECA, "lightpulsar"),   # phantom row dropped
    ("summon_procedure_table", 0x0FB1, "lightpulsar"),   # the donor's procedure row
    # ------------------------------------------------------------------
    # Darkflare Dragon CLAUSE 1 -- Lightpulsar's clause 1 word for word, on donor
    # Battle Footballer 0x1646. Same five structures, different slots in each; the
    # PAYMENT side is not listed per-card because it is genuinely SHARED (see
    # finished_patches/handss_banish_cost.py -- one BL hook per dispatch, so the
    # stubs carry a donor REGISTER rather than one cid).
    # ⚠️ The criteria phantom and the list-A phantom are deliberately THE SAME cid:
    # list-A membership means "this cid owns a 2-row block", so a phantom whose two
    # rows are dropped must leave list A with them or it would claim a block it no
    # longer has. (Lightpulsar could use two different phantoms only because its
    # criteria phantom 0x0E79 was in neither list.) 0x0EA8 is the last spare of this
    # shape; after it, a further card needs a phantom pair found some other way.
    ("populate_table", 0x0E32, "darkflare"),     # phantom, both rows dropped
    ("populate_table", 0x1646, "darkflare"),     # the donor's LIGHT+DARK row pair
    ("membership_list_a", 0x0E32, "darkflare"),  # the same phantom leaves list A
    ("membership_list_a", 0x1646, "darkflare"),  # the donor
    ("handss_dead_arm", 0x0225E88E, "darkflare"),      # the LAST usable dead arm
    ("handss_count_branch", 0x0225CF8C, "darkflare"),  # NOT Lightpulsar's 0x0225CF5E:
    #   the donor is 0x1646, above the 0x1466 pivot, so it takes a different branch.
    #   Blast radius measured: 601 cids share it, none has a nonzero count and none
    #   reaches a banish-cost leaf, so only the donor can observe the change.
    ("summon_procedure_table", 0x176C, "darkflare"),   # phantom row dropped
    ("summon_procedure_table", 0x1646, "darkflare"),

    # --- Darkflare CLAUSE 2 -------------------------------------
    # Three criteria rows at RELATIVE 2/3/4 on the same donor, so they get their
    # own pool name -- the base `populate_table` claim above is clause 1's rel 0/1
    # pair, exactly the split lightpulsar uses (populate_table_r23 / _r4).
    ("populate_table_r234", 0x1646, "darkflare"),   # hand / deck / either-GY rows
    ("populate_table", 0x0E6B, "darkflare"),        # phantom, BOTH rows dropped.
                                                    #   Already out of list A --
                                                    #   lightpulsar removed it there,
                                                    #   so no list bookkeeping follows.
    ("populate_table", 0x164A, "darkflare"),        # phantom, its 1 row dropped
    ("cls3_table", 0x1646, "darkflare"),            # Card Ejector's record shape
    ("cls3_table", 0x164B, "darkflare"),            # phantom cls3 row dropped   # the donor's procedure row
    # Lightpulsar CLAUSE 2 ("SS from GY by sending 1 LIGHT + 1 DARK from hand").
    # ⚠️ THE ZONE OF A CRITERIA ROW IS ITS HANDLER, NOT ITS WORD
    # (dispatch.criteria_zone_is_the_handler, proved by Dark Simorgh 0x1E5A paying the
    # same two attributes from either zone with pairwise-IDENTICAL words). So clause 2's
    # rows are clause 1's words with handler 0x0223CA11 -> 0x0223CB19 (GY -> HAND), and
    # they MUST sit at relative indices 2/3: clause 1 is shipped and in-game confirmed
    # and its leaf 0x0225FA46 passes param 0/1 as bare immediates.
    # ⚠️⚠️ REVISED: 0x1303 is not dropped, it is REPURPOSED AS A PROXY CID.
    # cid 0x0FB1 can never address a criteria row past index 1 -- 0x02243B9C gives a
    # list-A cid `r4 = (param==0)?0:1` and gives a listless one `movs r4,#0`
    # (0x02243EEC, reached via the BST at 0x02243C1C) -- so the donor's own block is
    # capped at two rows and clause 2 cannot have rows of its own on that cid.
    # 0x1303 is the ideal stand-in: a phantom that ALREADY owns exactly two adjacent
    # criteria rows (94/95) AND is ALREADY in membership list A. Its two rows are
    # rewritten IN PLACE to the hand-select LIGHT/DARK pair (handler 0x0223CB19), so
    # the registry keeps its size, its sort and its membership lists untouched, and
    # lightpulsar's PART L trampoline swaps desc[+0] to this cid for the
    # duration of the probe. Claimed here so no other patch reuses either row.
    # SIMORGH_STYLE: clause 2's two rows sit on the DONOR at
    # relative indices 2/3 -- Dark Simorgh's exact layout -- reachable because
    # CAVE_LP_ROWHOOK supplies the `r4 = 2 + desc[+0x12]` arm that the compiled
    # switch 0x02243B9C has hardcoded for 0x1E5A and cannot have for us. Phantom
    # 0x1303's two rows are dropped to keep the insert count-neutral.
    ("populate_table", 0x1303, "lightpulsar"),   # phantom, both rows dropped
    ("populate_table_r23", 0x0FB1, "lightpulsar"),  # the donor's HAND pair at rel 2/3
    # cls2 record cloned verbatim from Dark Simorgh cls2[375] -- the GY-summon half of
    # its two records (+04 0x0220731D self-SS-from-GY resolver, +10 0x021EC57D hand cost).
    ("cls2_table", 0x0E10, "lightpulsar"),       # phantom dropped to stay count-neutral
    # The PROXY 0x1303 needs a cls2 record of its own or clause 2's cost DEADLOCKS:
    # the activation machine re-enters the cost through find_event_handler(desc),
    # which binary-searches cls2 by desc[+0] -- and the cost swaps desc[+0] to the
    # proxy so the candidate enumeration uses the proxy's hand-select rows. Measured
    # without this record desc[+0] stuck at 0x1303 across all savestates,
    # the state machine reset, nothing was sent and nothing summoned. +0C is NULL by
    # design (the condition is only used when OFFERING, always via the donor record).
    # (RELEASED when SIMORGH_STYLE shipped: the proxy cls2 record and its
    #  phantom 0x1435 are no longer needed. The cost no longer swaps desc[+0], so
    #  re-entry finds the DONOR's own record and the proxy needs no record of its own.
    #  0x1435 is free for the next patch.)
    # ⚠️⚠️ AND THE ROW THAT MAKES A GY EFFECT REACHABLE AT ALL. The GY-ACTION REGISTRY
    # @0x0228DDF8 ({u32 cid, u32 zone, u32 check_fn, u32 post_fn}, stride 0x10, 60 rows,
    # UNSORTED and LINEAR-SCANNED by four scanners each bounded by a hard-coded
    # `cmp rX,#0x3C`: 0x0224C88E by zone, 0x0224CD14 by cid, 0x0224CBD8 / 0x0224CD42 by
    # post_fn). Its check_fn 0x0224C591 is the ONLY thing that builds the zone-0x0E /
    # class-2 descriptor which reaches the cls2 condition -- 0x0224C590 and 0x0224C6C0
    # have ZERO BL callers and exist solely as this table's function pointers. A cid with
    # no row here has its Graveyard effect silently never offered, with every other
    # structure correct and resident: that was the clause-2 dead end.
    # Every ignition-style GY summoner is in it (Simorgh 0x1E5A, Plaguespreader 0x1EA9,
    # Quillbolt 0x1E15, Soulkius 0x202C, Spore 0x225B, Glow-Up Bulb 0x2387, Ronintoadin
    # 0x2269). ⚠️ Treeborn Frog 0x19CB is NOT -- it is a Standby-Phase trigger wired
    # through 0x0228EB24 / 0x0226D384, which is exactly why it is a misleading control.
    # Unsorted + imm8 bounds => the insert is an in-place rewrite of a phantom's cid word.
    # Two phantoms remain free in the same family/zone for future cards: 0x0EB2 (row 15,
    # but embedded in the 0x0224C55D block) and 0x0E64 (row 48).
    ("gy_action_registry", 0x0E3E, "lightpulsar"),   # phantom row 47 consumed in place
    ("gy_action_registry", 0x0FB1, "lightpulsar"),   # the donor's GY-action row
    # ---- Lightpulsar CLAUSE 3 -------------------------------------
    # "When this card is sent from the field to the GY: you can target 1 Lv5+ DARK
    # Dragon in your GY; Special Summon that target."
    #
    # TRIGGER: a second row in the LEAVE-MASK table 0x0226EC1C, alongside Eclipse
    # Wyvern's. Mask 0x0800 = "sent to the Graveyard". It is FIELD-ONLY here because
    # the whole leave dispatcher is (event.leave_mask_is_field_only: read at exactly
    # one site, 0x021C8104, never on a discard) -- which is precisely what clause 3
    # wants, and precisely why this patch must NOT also hook the any-location cid
    # switch 0x021D1392 the way Eclipse Wyvern's PART E does.
    # ⚠️ list30 0x0226E904 is the semantically exact "sent from the FIELD to the GY"
    # register (Botanical Girl, Sangan, Witch of the Black Forest, the equip spells)
    # but it is FULL -- 30/30 real cards -- and cannot grow. 21 phantom mask rows
    # remain for future cards.
    # Lightpulsar clause 3's TRIGGER: a second row in the leave-mask table, alongside
    # Eclipse Wyvern's. Mask 0x0800 = "destination is the Graveyard" (bit 11), and it
    # sets [sp+0x18] -- the flag the leave switch's GENERIC arm needs. The control is
    # Sangan 0x0FD6: it reaches the SAME switch arm as our donor 0x0FB1 (both fall in
    # the interval (0x0EBF, 0x1174) -> `bl 0x021C93D0` @0x021C827A) and its any-means
    # sent-to-GY trigger works natively purely on list30 membership. So the arm is
    # generic and only the flag matters. list30 itself is FULL (30/30 real cards) and
    # cannot grow, which is why a donor that is not natively a member uses the mask
    # table instead -- same flag, and field-only either way because the whole
    # dispatcher is (event.leave_mask_is_field_only).
    ("leave_mask_table", 0x0E80, "lightpulsar"),   # phantom dropped to make room
    ("leave_mask_table", 0x0FB1, "lightpulsar"),   # the donor's sent-to-GY row
    # TARGET FILTER: a 5th criteria row on the donor, at relative index 4, carrying
    # the row the 3DS ships for the real Lightpulsar Dragon (cid 0x26E3):
    # {fn 0x0223C9D1, word 0x0A550002}. Reachable only via CAVE_LP_ROWHOOK's third
    # arm, which returns r4 = 4 when the acting descriptor's event code is 0x1E.
    # Count-neutral over single-row phantom 0x1138 (in neither membership list nor
    # the disambiguation switch, so dropping it orphans nothing).
    ("populate_table", 0x1138, "lightpulsar"),      # phantom, its single row dropped
    ("populate_table_r4", 0x0FB1, "lightpulsar"),   # the donor's revive row at rel 4
    # ---------------------------------------------------------------------
    # Reborn Tengu, re-homed from the REAL Effect Monster
    # Minefieldriller 0x2085 onto the records-free Normal Monster The Portrait's
    # Secret 0x1463 (reborn_tengu, superseding patch_minefield_driller).
    # 0x2085 is now touched by nothing and is a working card again -- do NOT
    # treat it as an available donor: its native rows are what the patch asserts.
    # The donor's cid has ZERO aligned u16/u32 occurrences in overlay 3 + arm9.
    # ---------------------------------------------------------------------
    ("donor_cid", 0x1463, "reborn_tengu"),
    # TRIGGER: leave-mask row {0x1463, 0x000C} = face-up + left the field -- the
    # value Konami's own 3DS build gives its shipped Reborn Tengu (cid 0x25E3).
    # Phantom 0x14E9 owned this row AND cls2[100], its only two appearances in the
    # whole build, so the two drops below retire the cid entirely. Its mask row was
    # already at the donor's sorted index, so PART B shifts nothing.
    ("leave_mask_table", 0x14E9, "reborn_tengu"),  # phantom dropped to make room
    ("leave_mask_table", 0x1463, "reborn_tengu"),  # the donor's leave row
    ("cls2_table", 0x14E9, "reborn_tengu"),        # same phantom, its other row
    # CRITERIA: {a=b=0x1463, h=CAVE_MINEFIELD|1, fl=0x00000802}. Phantom 0x1452 owns
    # exactly one criteria row (132) and is in neither membership list, so dropping
    # it cannot change any cid's block size. Only the row originally at 133 moves;
    # dragon_shrine's index-anchored crit[157] is above that window.
    ("populate_table", 0x1452, "reborn_tengu"),    # phantom dropped to make room
    ("populate_table", 0x1463, "reborn_tengu"),    # the donor's deck self-SS row
    # ---------------------------------------------------------------------
    # NINJA GRANDMASTER HANZO -- clause 1 ("When this card is Normal Summoned:
    # You can add 1 'Ninjitsu Art' card from your Deck to your hand"), on donor
    # MELCHID THE FOUR-FACE BEAST 0x13E7: a records-free vanilla Normal Monster,
    # already DARK and already Level 4, with ZERO aligned u16/u32 occurrences
    # anywhere in overlay 3 + arm9. Pure data -- NO ov5 cave slot is claimed.
    # ---------------------------------------------------------------------
    ("donor_cid", 0x13E7, "ninja_grandmaster_hanzo"),

    # --- Ninjitsu Art of Super-Transformation (donor Goblin Fan 0x1255) -------
    ("donor_cid", 0x1255, "ninjitsu_art_super_transformation"),
    ("ninjitsu_art_setcode_table", 0x1C55, "ninjitsu_art_super_transformation"),  # phantom dropped
    ("ninjitsu_art_setcode_table", 0x1255, "ninjitsu_art_super_transformation"),  # the donor joins
    ("cls0", 0x0E1A, "ninjitsu_art_super_transformation"),          # phantom dropped
    ("cls0", 0x1255, "ninjitsu_art_super_transformation"),
    ("populate_table", 0x0E12, "ninjitsu_art_super_transformation"),  # phantom dropped
    ("populate_table", 0x1255, "ninjitsu_art_super_transformation"),
    ("leave_cleanup_list", 0x0E42, "ninjitsu_art_super_transformation"),  # phantom dropped
    ("leave_cleanup_list", 0x1255, "ninjitsu_art_super_transformation"),
    # ARM9 set code 0x2A @0x0209C5D2 (thunk 0x02023B10, `movs r2,#4`) is REPURPOSED
    # as "Ninjitsu Art". All FOUR of its stock members are phantoms with no
    # card_prop record, no criteria row carries aux 0x2A, and the only aligned
    # pointer to its thunk in arm9+ov3 is the has_set_code table slot itself -- so
    # the archetype was inert and nothing can regress. Entries 0/1 become the two
    # real Ninjitsu Art cards; 0x1C55/0x1C5F are kept as sorted padding so the
    # hardcoded count stays 4.
    ("ninjitsu_art_setcode_table", 0x0EA1, "ninja_grandmaster_hanzo"),  # phantom dropped
    ("ninjitsu_art_setcode_table", 0x0EA2, "ninja_grandmaster_hanzo"),  # phantom dropped
    # ARM9 Ninja set code 0x06 @0x0209C722 (thunk 0x020237D8, `movs r2,#9`) has NO
    # phantom -- every entry is a real card -- so membership costs a real Ninja.
    # ARMED NINJA 0x117B is displaced (user's choice). Nothing in the
    # stock ROM consumes set code 0x06, and both Ninjitsu Art cards test "Ninja"
    # through their own per-cid switch predicates (0x021DA1C8 / 0x021E0680), not
    # this table, so the cost is confined to Hanzo's own future clause-2 search
    # and the deck-editor archetype filter.
    ("ninja_setcode_table", 0x117B, "ninja_grandmaster_hanzo"),   # Armed Ninja displaced
    ("ninja_setcode_table", 0x13E7, "ninja_grandmaster_hanzo"),   # the donor joins

    # ---------------------------------------------------------------------
    # WHITE DRAGON NINJA -- identity + clause 2 ("Spells/Traps you control
    # cannot be destroyed by card effects"), on donor DUNAMES DARK WITCH
    # 0x12B2: a records-free Normal Monster, already LIGHT, with ZERO ARM9
    # data-region occurrences (the cleanest report in the whole donor pool).
    # Clause 1 ("Cannot be Special Summoned, except with a 'Ninjitsu Art'
    # card's effect") is NOT built -- see notes/white-dragon-ninja-findings.md.
    #
    # It claims NO cls record, NO criteria row and NO effect-registry row: the
    # card is reachable purely because NAST's ov5 criteria handler whitelists
    # races {1 Dragon, 9 Dinosaur, 5 Sea Serpent} and this card's card_prop
    # race becomes 1. Only the ov5 cave slot and the two set-code cids below.
    # ---------------------------------------------------------------------
    ("donor_cid", 0x12B2, "white_dragon_ninja"),
    # The same 9-entry, phantom-free Ninja list Hanzo already paid into. The
    # displaced card is KARAKURI NINJA mdl 339 "Sazank" 0x238B (user's choice,
    #), verified still a member of the KARAKURI set-code list
    # 0x0209CC16[4] -- so it keeps every Karakuri interaction and loses only
    # "Ninja" status. This is what lets White Dragon Ninja be chosen as the
    # "Ninja you control" that Super-Transformation sends; it is NOT what makes
    # it summonable (that is card_prop race, PART A).
    ("ninja_setcode_table", 0x238B, "white_dragon_ninja"),   # Karakuri Ninja "Sazank" displaced
    ("ninja_setcode_table", 0x12B2, "white_dragon_ninja"),   # the donor joins
    # TRIGGER: the "when this card is Normal Summoned" membership list 0x0228F7AC
    # (summon.trigger_is_a_membership_list, code 7). Phantom 0x14CC has no
    # card_prop record; it sits three slots above the donor's sorted index, so the
    # insert shifts only rows 5..7.
    ("summon_list_c7", 0x14CC, "ninja_grandmaster_hanzo"),   # phantom dropped
    ("summon_list_c7", 0x13E7, "ninja_grandmaster_hanzo"),   # the donor's Normal-Summon trigger
    # cls1: Machina Gearframe 0x21F5's record verbatim -- {+04 0x02207EF5
    # add-to-hand, +08 0, +0C 0x021F0821 "a candidate exists", +10 0x021E51E5,
    # +14 0}. Phantom 0x143E owns exactly one cls1 row.
    ("cls1", 0x143E, "ninja_grandmaster_hanzo"),
    # CRITERIA: {0x13E7, aux 0x002A = the Ninjitsu Art set code above, fn
    # 0x0223CAF5 = select from the DECK -> hand, word 0x0000000E}. The word is the
    # 3DS Hanzo clause-1 row's verbatim (3DS 0x004B1C1C == NDS 0x0223CAF5), and
    # admits non-monster card types -- both Ninjitsu Art cards are Traps.
    ("populate_table", 0x143D, "ninja_grandmaster_hanzo"),   # phantom dropped
    ("populate_table", 0x13E7, "ninja_grandmaster_hanzo"),   # the donor's deck-search row
    # ---- CLAUSE 2 ----------------------------------------------------------
    # A records-free donor gets ONE cls1 record (the second-record path needs a
    # Spirit Monster -- dispatch.second_cls1_record_is_spirit_only), so clause 2
    # cannot have its own. It is a SECOND CRITERIA ROW on the same record,
    # selected by 0x02243B9C's `leftmost_row_for_cid + r4`.
    # {0x13E7, aux 0x0006 = the Ninja set code, 0x0223CAF5, word 0x00000022} --
    # Konami's own row (3DS registry 0x686CBC row 1541) and byte-identical to
    # Machina Gearframe's. Bit 5 = "except this card". Phantom 0x0E14 owns
    # exactly one row and was unclaimed in every pool.
    ("populate_table", 0x0E14, "ninja_grandmaster_hanzo"),   # phantom dropped for row 1
    # LIST A membership is what grants the row offset at all. 0x0D81 "Speed Spell
    # - Stardust Shimmer" is a member owning ZERO criteria rows, so its
    # membership is vestigial and dropping it changes no behaviour. It and 0x0D7A
    # were the only two such members, and 0x0D7A is already spent by snoww.
    ("membership_list_a", 0x0D81, "ninja_grandmaster_hanzo"),  # vestigial member evicted
    ("membership_list_a", 0x13E7, "ninja_grandmaster_hanzo"),  # the donor
    # ⚠️ NEW POOLS. The Flip (code 8) and Special (code 9) summon-trigger lists,
    # same data-only route clause 1 proved in-game.
    # 0x0228F580 x 0x0C has exactly ONE phantom, 0x1A9F -- the scarcest slot in
    # the whole subsystem. (0x1A9F is also claimed by tg_striker, but in the
    # `registry_row` pool: a different resource, no conflict.)
    ("summon_list_c8", 0x1A9F, "ninja_grandmaster_hanzo"),   # its only phantom
    ("summon_list_c8", 0x13E7, "ninja_grandmaster_hanzo"),   # Flip-Summon trigger
    # 0x0228F63A x 0x1F has five phantoms; 0x0E12 was unclaimed in every pool.
    ("summon_list_c9", 0x0E12, "ninja_grandmaster_hanzo"),   # phantom dropped
    ("summon_list_c9", 0x13E7, "ninja_grandmaster_hanzo"),   # Special-Summon trigger
    # ---------------------------------------------------------------------
    # Upstart Golden Ninja -- "Once per turn: You can send 1 Trap
    # from your hand to the GY; Special Summon 1 Level 4 or lower 'Ninja'
    # monster from your Deck...".  Donor The Gross Ghost of Fled Dreams 0x1464,
    # a records-free vanilla Normal Monster (donor_scan: CLEAN; its single ARM9
    # u16 "hit" @0x020A15F4 is a monotonic numeric ramp, i.e. a curve table, not
    # a cid list).  Level 4 and DEF 1800 already match the printed card.
    # ---------------------------------------------------------------------
    ("donor_cid", 0x1464, "upstart_golden_ninja"),
    # ⚠️ THE THIRD PATCH TO PAY INTO THE 9-ENTRY, PHANTOM-FREE Ninja list
    # @0x0209C722 (hanzo drops 0x117B, white_dragon_ninja drops 0x238B).  The
    # displaced card here is CRIMSON NINJA 0x16B8 -- Level 1, 400/700, the
    # weakest member -- and it is chosen because it is the ONLY sort-neutral
    # slot in EVERY chain order: 0x1464 lands between 0x117B/0x13E7/0x12B2 and
    # 0x16B9 whichever of the three patches has already run, so the list stays
    # strictly sorted at 9 entries and the hardcoded `movs r2,#9` stays valid.
    ("ninja_setcode_table", 0x16B8, "upstart_golden_ninja"),   # Crimson Ninja displaced
    ("ninja_setcode_table", 0x1464, "upstart_golden_ninja"),   # the donor joins
    # TWO criteria rows, and the ORDER IS LOAD-BEARING: rel 0 is the cost
    # {0xFFFF, 0x0223CB65 hand-send, 0x08 = Trap} and rel 1 is the effect
    # {0x0006 Ninja, 0x0223CAB5 deck-SS, 0x00900002 = Lv<=4 monster}.  Both
    # consumers pass param 0, so the rows are separated by an arm on the SHARED
    # criteria_row_hook keyed on desc[+7] ("the cost has already run"), NOT by
    # membership list A -- which is why this patch claims no list-A slot.
    # Phantoms 0x1449 (crit[130]) and 0x144C (crit[131]) are adjacent and were
    # unclaimed in every pool.
    ("populate_table", 0x1449, "upstart_golden_ninja"),
    ("populate_table", 0x144C, "upstart_golden_ninja"),
    # cls3 {+04 0x02206CAD deck-SS resolver, +08 0, +0C CAVE_UGN_COND,
    # +10 CAVE_UGN_COST, +14 0} = Gem-Knight Alexandrite's record with Naturia
    # Landoise's cost slot.  Dropping 0x144C here as well retires that phantom
    # from the build entirely (the Reborn Tengu pattern).
    ("cls3_table", 0x144C, "upstart_golden_ninja"),
    # ⚠️ NEW POOL, and the thing in-game test 1 died on. The IGNITION-CONDITION
    # REGISTRY @0x0226FAFC (146 x {u16 cid, u16 aux, u32 f1, u32 f2}, sorted,
    # binary-searched by 0x021F0BDD via 0x02022E44) decides whether an on-field
    # ignition effect is OFFERED AT ALL: a cid with no row makes 0x021F0BDD return
    # 0 at 0x021F0BF0 and the activate prompt never appears. The row is Beast
    # Striker 0x20B8's {f1 0x021F024D, f2 0x021F0419} -- the native card with this
    # card's exact shape -- and BOTH pointers were checked for cid gates before
    # reuse. Phantom 0x1446 (row 11) is already AT the donor's sorted index
    # (0x1446 < 0x1464 < 0x14A7 Rope of Life), so the insert shifts zero rows.
    # The table's other six phantoms are 0x0E3E 0x0E7D 0x0E86 0x0EA9 0x0EAE 0x1748.
    ("ignition_cond_registry", 0x1446, "upstart_golden_ninja"),
    ("ignition_cond_registry", 0x1464, "upstart_golden_ninja"),
    # ---------------------------------------------------------------------
    # Jet Synchron, CLAUSE 1 ONLY. Donor Changer Synchron 0x224C:
    # already Level 1 / Machine / Tuner, already a member of the ARM9 "Synchron"
    # set-code list @0x0209C968 (so Tuning and Junk Speeder reach it with NO table
    # edit and NO phantom spend), and already carrying the sent-to-GY trigger
    # clause 1 needs. It is named by exactly ONE structure, cls2[555], which this
    # patch rewrites IN PLACE -- no cls2 phantom is consumed.
    # ⚠️ NOT in apply_all_patches: awaiting its first in-game test.
    # ---------------------------------------------------------------------
    ("donor_cid", 0x224C, "jet_synchron"),
    # criteria/populate registry: count-neutral insert of the donor's
    # {aux 0x0050 = the Junk set code, handler 0x0223CAF5 = search the DECK,
    # flags 0x0002 = Monster, extra 0 = no level bound} row. Phantom 0x234A has no
    # card_prop record and owns exactly ONE criteria row (1237); it also owns a
    # cls3 record, which is left alone and is unreachable anyway for a cid with no
    # obtainable card -- the same standard as azure_eyes 0x1ABE, eclipse_wyvern
    # 0x18F8 and maiden_eyes_of_blue 0x1BBE, each of which is named by MORE
    # structures than this one.
    ("populate_table", 0x0EAF, "jet_synchron"),
    # --- clause 2 ---------------------------------------------
    # The COST's "any 1 card in your hand" row, inserted IMMEDIATELY AFTER the
    # clause-1 Deck row so the donor owns rel 0 = Deck and rel 1 = Hand (the order
    # is load-bearing: dispatch.offer_check_probes_rel0_only). Count-neutral over
    # 0x0E4A -- no card_prop, exactly one criteria row (33) in the stock image, and
    # the fewest aligned-u16 mentions of any unclaimed single-row phantom. Its other
    # two structures (a leave-mask row @0x0226EC38 and a cls2 record @0x02275DB4)
    # are LEFT ALONE and are unreachable, because a cid with no card_prop can never
    # be an obtainable card -- the same argument clause 1's 0x234A rests on.
    ("populate_table", 0x0E4A, "jet_synchron"),
    # ⚠️ THIS WAS THE LAST FREE PHANTOM IN THE GY-ACTION REGISTRY'S GRAPHA FAMILY.
    # Row 48. The sibling family {chk 0x0224C55D, post 0x0224C669} still has three
    # spare rows (0x1449, 0x144C, 0x1452) but CANNOT host a GY self-Special-Summon:
    # it builds no class descriptor at all, so there are no +04/+0C/+10 slots to
    # hang an effect on, and both of its halves gate on the card being in the HAND.
    # A future GY-effect card must therefore overwrite a REAL card's row, costing
    # that card its GY effect (the darksoul precedent took Manticore's
    # End-Phase slot outright).
    ("gy_action_registry", 0x0E64, "jet_synchron"),   # phantom row 48 consumed in place
    ("gy_action_registry", 0x224C, "jet_synchron"),   # the donor's GY-action row   # phantom dropped
    ("populate_table", 0x224C, "jet_synchron"),   # the donor's criteria row
    # ---------------------------------------------------------------------
    # Steam Synchron. Donor Cyber-Tech Alligator 0x12B6 -- a records-free
    # vanilla Normal Monster, already a Machine. The card is a TRANSPLANT of Formula
    # Synchron 0x239E's opponent's-turn Synchro clause: cls3 slots (+04 resolver
    # 0x02249EC1, shared with Urgent Tuning 0x1EF0; +0C condition 0x021F1491) plus a
    # criteria row plus spell-speed-2 membership. NO injected code, NO ov5 slot, so
    # unlike an ov5-hosted card it works in puzzles and turbo duels too.
    # ---------------------------------------------------------------------
    ("donor_cid", 0x12B6, "steam_synchron"),
    # cls3: count-neutral insert. 0x1528 is the IDEAL phantom -- no card_prop record and
    # its own cls3 row is its ONLY binding occurrence anywhere in the ROM. Also chosen
    # for its INDEX: dropping row 96 to insert at row 58 moves only indices [58, 96],
    # which is below every cls3 row a shipped patch anchors BY INDEX
    # (shiens_dojo 223/233, maiden_eyes_of_blue 334, sea_lancer 527).
    # Any future cls3 insert must redo that arithmetic before picking its phantom.
    ("cls3_table", 0x1528, "steam_synchron"),
    # criteria/populate: count-neutral insert. 0x0E6E has no card_prop and owns exactly
    # ONE criteria row (it also owns a cls0 record, which is left untouched and is
    # unreachable for want of a card_prop record).
    ("populate_table", 0x0E6E, "steam_synchron"),
    # spell-speed-2 list 0x0209C118 -- the QUICK EFFECT gate
    # (dispatch.responder_spell_speed_gate). 0x1774 was picked over the other nine free
    # phantoms because its only structure is a cls2 record: 0x0E6B/0x0E6C are T.G.
    # set-code members and 0x0E63/0x0E64 Infernity members, and spending one of those
    # would put this patch next to tables other modules assert.
    ("quickeffect_list", 0x1774, "steam_synchron"),
    # ⚠️ "Synchron" set-code list 0x0209C968 -- A REAL CID IS SPENT HERE, not a phantom,
    # and that needs justifying. The list is FULL (15 real members; its only phantom
    # 0x2501 went to unknown_synchron) and CANNOT GROW: the Lightsworn list ends at
    # 0x0209C966 and the Gravekeeper's list begins at 0x0209C986. The neighbour's
    # trailing phantom 0x2442 is unavailable too -- gravekeepers_recruiter spent
    # it and asserts that list's base and both count immediates.
    # WHAT MAKES 0x229E FREE IS THAT IT IS STALE, NOT THAT IT IS UNUSED: it is
    # tour_guide's donor, so in any chained build it is Tour Guide From the
    # Underworld -- not a Synchron -- and its criteria row already carries aux 0x000E
    # with an ov5 handler, i.e. it does not use set code 0x4C at all. Only the list
    # membership outlived the card. Dropping it is a correction; it also stops Tour
    # Guide showing under a "Synchron" deck-editor filter.
    # NB set code 0x4C is provably MONSTER-ONLY (its three consumers -- criteria rows
    # for Necro Linker 0x237A, Tuning 0x23A2 and 0x24B3 -> Junk Speeder -- all carry low
    # half 0x0002 plus bit 15), which is the general rule to apply before spending any
    # set-code tag: read every aux consumer's card-type bits first.
    # This patch and unknown_synchron use DIFFERENT slots (stale 0x229E vs phantom
    # 0x2501), so they compose in either order.
    ("synchron_setcode_table", 0x229E, "steam_synchron"),
    # ---------------------------------------------------------------------
    # Jet Warrior, CLAUSES 0 + 1 ONLY. Donor Ignition Beast
    # Volcannon 0x23EB, an EFFECT Fusion -- deliberately not the effectless
    # Fusion the card was scoped with. The proper-Summon trigger list
    # 0x0228F6C0 (36 x u16, hard count 0x24) is the ONLY one of the nine
    # summon-trigger lists with ZERO phantoms, so an "If this card is Synchro
    # Summoned:" donor must ALREADY be in it; 0x23EB is row 30. Its single cls1
    # record is rewritten IN PLACE, so no cls record phantom is spent either.
    # ⚠️ NOT in apply_all_patches: awaiting its first in-game test.
    # ---------------------------------------------------------------------
    ("donor_cid", 0x23EB, "jet_warrior"),
    # NEW POOL. The named-material table @0x02275B04 -- 23 rows x 4 B,
    # {u16 synchro_cid, u16 named_material_cid}, strictly ascending and
    # BINARY-SEARCHED by 0x02022E44 from OUTER 0x022485B4 @0x02248610 (count
    # 0x17 @0x0224860C, stride 4 @0x0224860E). One row is a complete
    # '"<name>" + 1 or more non-Tuner monsters' material rule: Junk Warrior
    # 0x1E10 is row 1 = {0x1E10, 0x1E07} and prints exactly that. The table
    # shipped with a SINGLE phantom, row 22 = {0x2524, 0x1E07} -- 0x2524 is Junk
    # Berserker's real Konami id and has no card_prop record here. jet_warrior
    # spends it on a count-neutral sorted insert of {0x23EB, 0x224C}.
    # NB 0x2524 also appears in junk_setcode_table, where it is still FREE --
    # these claims are pool-scoped and the two edits are independent.
    ("named_material_table", 0x2524, "jet_warrior"),
    # --- clauses 2 + 3 ----------------------------------------
    # cls2: the donor has no cls2 record, so clause 2 needs a count-neutral
    # sorted insert.  0x1655 has no card_prop record and EXACTLY ONE aligned-u16
    # mention in all of overlay 3 -- its own cls2 record -- which is the fewest
    # of any unclaimed cls2 phantom.  ⚠️ cls2 is only NON-DECREASING, not
    # strictly ascending: a cid may legitimately own two records (Doppelwarrior
    # 0x244D, King of the Beasts 0x20B9), so an insert must not assert strictness.
    ("cls2_table", 0x1655, "jet_warrior"),
    # ⚠️ NOT A PHANTOM.  Clause 2 spends a REAL card's GY-action row -- row 33
    # @0x0228E008, Sword of Sparkles 0x209D -- because family C's three phantoms
    # are all gone (15 grapha, 47 lightpulsar, 48 jet_synchron) and the table
    # cannot grow (it ends at 0x0228E1B8 with a pointer table immediately after).
    # Family B's three spare rows CANNOT host a GY self-SS: that family builds no
    # class descriptor and gates on the HAND.  By explicit user decision.
    # COST, measured: Sword of Sparkles loses ONLY its third sentence (the GY
    # self-recycle, cls2[475] @0x0227888C); its equip + battle-destruction clause
    # is cls1[1042] @0x0228C284, reached by the battle/equip path, and stays live.
    ("gy_action_registry_row", 0x209D, "jet_warrior"),
    # ---------------------------------------------------------------------
    # Scrap Archfiend.  Donor Humanoid Worm Drake 0x13C6, an
    # effectless FUSION monster converted to an effectless SYNCHRO (the
    # accel_synchron recipe).  Pure data: no cls record, no criteria row,
    # no ov5 cave slot -- the only shared resources are the two ARM9 set-code
    # lists.
    #
    # ⚠️ TWO NEW POOLS, and they drop the SAME cid on purpose.
    #   "Scrap"     set code 0x57, list @0x0209CC70, 25 x u16, thunk 0x02023EE5
    #   "Archfiend" set code 0x01, list @0x0209CF90, 42 x u16, thunk 0x02023761
    # 0x23F2 is a phantom in BOTH and in no other list -- it is Scrap Archfiend's
    # OWN Konami cid (3DS CARD_Prop record 4339, setcode.numbering_shared_with_3ds),
    # reserved on NDS for a card that never shipped.  It has no card_prop record,
    # so its membership was inert in both.  The pools are distinct address spaces,
    # so claiming 0x23F2 in each is not a collision -- but a future patch must not
    # spend it in EITHER.
    ("scrap_setcode_table", 0x23F2, "scrap_archfiend"),        # phantom dropped
    ("scrap_setcode_table", 0x13C6, "scrap_archfiend"),        # the donor joins
    ("archfiend_setcode_table", 0x23F2, "scrap_archfiend"),    # phantom dropped
    ("archfiend_setcode_table", 0x13C6, "scrap_archfiend"),    # the donor joins
    # The donor itself, so no later patch reuses this Extra-Deck slot.
    ("donor_cid", 0x13C6, "scrap_archfiend"),
    # ⚠️ NEW POOL. fusion recipe table A @0x02270B94 -- the patch blanks row 57's
    # MATERIAL columns only (0x13C5/0x13C4 -> 0x3FFF/0x3FFF) so the ungated CPU AI
    # planner 0x022112B2 cannot Fusion Summon the converted card.  The result cid,
    # the sort order and the 161-row count are untouched.
    ("fusion_table_a_row", 0x13C6, "scrap_archfiend"),
    # ---------------------------------------------------------------------
    # Scrap Raptor, on the records-free vanilla Normal Monster
    # URABY 0x0FF6 (donor_scan VERDICT CLEAN; already Lv4 EARTH Dinosaur).
    # -- Stage 1 (the chassis) only.
    #
    # Same "Scrap" pool as scrap_archfiend above, so this is the second
    # count-neutral drop from list @0x0209CC70.  The phantom spent here is
    # 0x2441 == SCRAP MIND READER (3DS CARD_Prop, setcode.numbering_shared_with_3ds),
    # a cid Konami reserved and never shipped on NDS; it has no card_prop record
    # so its membership was inert.  Scrap Raptor has NO reserved cid of its own --
    # it is a 2019 card and is absent from the NDS *and* the 3DS build -- which is
    # why an unrelated phantom has to be spent.
    # ⚠️ TWO Scrap phantoms remain for future Scrap cards and must not be spent
    #    without registering them here: 0x24ED Scrap Breaker, 0x251F Scrap Kong.
    ("scrap_setcode_table", 0x2441, "scrap_raptor"),           # phantom dropped
    ("scrap_setcode_table", 0x0FF6, "scrap_raptor"),           # the donor joins
    # The donor itself, so no later patch reuses this Main-Deck slot.
    ("donor_cid", 0x0FF6, "scrap_raptor"),
    # Stage 2 (C2).  The cls2 record is the trigger "destroyed by the effect of a
    # 'Scrap' card and sent to your GY" -- Scrap Goblin's cid-blind record with
    # +04 swapped for Scrapyard's "add 1 -> hand" resolver 0x02207EF5.  The
    # criteria row builds the candidate list, keyed aux=0x0057 ("Scrap") and
    # filtered non-Tuner by the ov5 handler's callback.
    ("cls2_table", 0x0E2D, "scrap_raptor"),          # phantom dropped for the trigger
    ("criteria_table", 0x0EA4, "scrap_raptor"),      # phantom dropped for the search
    # Stage 3 (C1a).  The cls3 ignition "target 1 face-up monster you control;
    # destroy it", with the once-per-turn latch on it.
    ("cls3_table", 0x0E36, "scrap_raptor"),          # phantom dropped for the ignition
    # THE LEAVE ARM.  A leave trigger only fires if the dispatcher
    # arms [sp+0x18]; the stock Scrap family uses a per-cid CODE arm, which a
    # donor cannot have, so this card buys its arm from the mask table.
    # mask 0x0C00 = 0x0400 destroyed | 0x0800 to-GY, exactly the two
    # non-archetype tests the stock arm at 0x021C92E6 performs; the archetype
    # test is supplied by the ov5 cls2 +0C stub CAVE_SR_C2COND.
    ("leave_mask_table", 0x0E41, "scrap_raptor"),    # phantom dropped
    ("leave_mask_table", 0x0FF6, "scrap_raptor"),    # the donor's leave row
    # ---------------------------------------------------------------------
    # Miscellaneousaurus C2 (2026-09-22 on records-free Normal
    # Monster Krokodilus 0x0FF2.  All phantoms checked unclaimed AND still present in the
    # chained rom_all_patches.nds before being claimed (notes/miscellaneousaurus-findings.md).
    ("donor_cid", 0x0FF2, "miscellaneousaurus"),
    ("gy_action_registry", 0x144C, "miscellaneousaurus"),   # sibling-family row 12 converted
    ("cls2_table", 0x0EBF, "miscellaneousaurus"),            # phantom dropped for the GY effect
    ("populate_table", 0x0EA8, "miscellaneousaurus"),        # its 2 rows -> Deck + GY rows
    ("membership_list_a", 0x0EA8, "miscellaneousaurus"),     # the LAST spare list-A pair
    ("membership_list_a", 0x0FF2, "miscellaneousaurus"),     # the donor
    ("endphase_destroy_list", 0x0E2E, "miscellaneousaurus"), # list 0x0228F708, in-place swap
    ("endphase_destroy_list", 0x0FF2, "miscellaneousaurus"),
    ("registry_row", 0x0E43, "miscellaneousaurus"),          # End-Phase row 254 -> 0x02254E95
    # C1 (2026-09-22: Effect Veiler's shape. ⚠️ NEW POOL for the ARM9 hand
    # QUICK-effect list 0x0209BC8C (36, sorted) -- distinct from "handfx_list" (0x0209BC4E) and
    # from "quickeffect_list" (the speed-2 list 0x0209C118). 0x0E63 was spent by koaki_meiru_wall
    # in the speed-2 list only; its list-B membership was still free.
    ("handfx_quick_list", 0x0E63, "miscellaneousaurus"),     # phantom dropped
    ("handfx_quick_list", 0x0FF2, "miscellaneousaurus"),
    ("quickeffect_list", 0x1534, "miscellaneousaurus"),      # phantom dropped (speed 2)
    ("quickeffect_list", 0x0FF2, "miscellaneousaurus"),
    # ---------------------------------------------------------------------
    # Souleating Oviraptor C1 on records-free Normal
    # Monster Two-Headed King Rex 0x0FC6.  Phantoms unclaimed in every pool and present in
    # BOTH stock rom.nds and chained rom_all_patches.nds (notes/souleating-oviraptor-findings.md).
    ("donor_cid", 0x0FC6, "souleating_oviraptor"),
    ("summon_list_c7", 0x19C0, "souleating_oviraptor"),
    ("summon_list_c9", 0x1ABF, "souleating_oviraptor"),
    ("cls1", 0x0E47, "souleating_oviraptor"),
    ("populate_table", 0x0E67, "souleating_oviraptor"),
    # C2 (2026-09-25: ignition cls3 + the GY Dinosaur criteria row (rel 1).
    ("cls3_table", 0x0E3F, "souleating_oviraptor"),
    ("populate_table", 0x0E69, "souleating_oviraptor"),
    # ---------------------------------------------------------------------
    # Elemental HERO Shadow Mist (2026-09-28 on records-free Normal Monster
    # Ryu-Kishin Powered 0x111F (donor_scan CLEAN).  Phantoms: no card_prop, exactly one row, present in
    # BOTH stock rom.nds and chained rom_all_patches.nds, unclaimed under any pool name
    # (notes/shadow-mist-findings.md).
    ("donor_cid", 0x111F, "shadow_mist"),
    ("summon_list_c9", 0x176C, "shadow_mist"),       # C1 Special Summon trigger list
    ("cls1", 0x1190, "shadow_mist"),                 # C1 record
    ("cls2_table", 0x0EBA, "shadow_mist"),           # C2 record
    ("populate_table", 0x0EB7, "shadow_mist"),       # rel 0: Mask Change from the Deck
    ("populate_table", 0x0EB5, "shadow_mist"),       # rel 1: "HERO" monster from the Deck, not itself
    ("leave_mask_table", 0x0EBA, "shadow_mist"),     # {0x111F, 0x0800} sent-to-GY mask row
    # sent-to-GY cid chain 0x021D1392: the terminal node 0x021D13CC re-keyed in place from phantom
    # 0x1175 (no card_prop) to the donor, routed to the native accept 0x021D13FC.
    ("gy_switch_node", 0x1175, "shadow_mist"),
    ("ehero_setcode_table", 0x1A6F, "shadow_mist"),  # Elemental Hero Flare Neos displaced (user decision)
    ("ehero_setcode_table", 0x111F, "shadow_mist"),  # the donor joins list 0x0209CFE4 (also "HERO" via the composite)
    # ---------------------------------------------------------------------
    # Masked HERO Dark Law C1 (2026-09-28 on effectless Fusion Aqua Dragon
    # 0x1160 (donor_scan: only binding = its own fusion recipe A[28]).  All ARM9 data/code, no ov5.
    # Masked HERO list moved back one slot to 0x0209C570 = [0x1160, Goka, Vapor]; that slot was the
    # 1-entry "Nitro" list [0x1E35], whose thunk 0x02023BD8 now compares directly (no member lost).
    # Fusion restriction class 3 (list 0x0209BA18, all phantom) is retagged class 5 (Goka's class).
    ("donor_cid", 0x1160, "masked_hero_dark_law"),
    ("fusion_class3_list", 0x1C55, "masked_hero_dark_law"),   # phantom dropped
    ("fusion_class3_list", 0x1160, "masked_hero_dark_law"),   # the donor joins (class 3 -> 5)
    ("masked_hero_setcode_table", 0x1160, "masked_hero_dark_law"),
    ("nitro_setcode_slot", 0x1E35, "masked_hero_dark_law"),   # list storage reused; thunk compares directly
    ("gy_banish_scan_bit4", 0x1444, "masked_hero_dark_law"),  # phantom arm of scan 0x021BA82C (C2)
    ("cls1_table", 0x1AC7, "masked_hero_dark_law"),           # C3: phantom's dead cls1[598] dropped
    ("draw_poster_slot", 0x1AC7, "masked_hero_dark_law"),     # C3: draw handler lit 0x021D12EC -> 0x1160
    # ---------------------------------------------------------------------
    # Elder Entity Norden on effectless Fusion Bickuribox
    # 0x1127 (donor_scan: only binding = its own fusion recipe A[23]).  Fusion material code 46's
    # jump-table entry 0x02231B82 is re-pointed at the plain is_synchro tail 0x02231DCC ("any Synchro
    # Monster"); code 46's only other user is phantom 0x1C5F's recipe row.
    ("donor_cid", 0x1127, "elder_entity_norden"),
    ("fusion_material_code", 46, "elder_entity_norden"),
    # C1a/C1b: Junk Synchron's cls1 + criteria row, cid swapped.
    ("summon_list_c9", 0x1ABE, "elder_entity_norden"),      # the code-9 list's LAST phantom
    ("summon_list_c9", 0x1127, "elder_entity_norden"),
    ("cls1_table", 0x0E4F, "elder_entity_norden"),
    ("populate_table", 0x0E7D, "elder_entity_norden"),
    # ---------------------------------------------------------------------
    # Double Evolution Pill on Normal Spell Share the Pain 0x1319:
    # cls0[199] rewritten in place; ONE criteria row (mode-switching ov5 handler) count-neutral over
    # phantom 0x16FD: no card_prop, one row, not in list A/B, nobody's aux, identical in stock ov3 and
    # rom_all_patches.nds (notes/double-evolution-pill-findings.md).
    ("donor_cid", 0x1319, "double_evolution_pill"),
    ("populate_table", 0x16FD, "double_evolution_pill"),
    # ---------------------------------------------------------------------
    # Ultimate Conductor Tyranno on Normal Monster Sengenjin 0x1265 (C1/C3/C4 built; notes/ultimate-conductor-tyranno-findings.md). Phantom 0x1758: no card_prop, unclaimed,
    # present in stock ov3 AND rom_all_patches.nds (9b82f8a1...) in the criteria table (1 row), the
    # summon-procedure registry (-> 0x02261F8D) and the ARM9 nomi class-2 list 0x0209BE9C. cls1 phantom 0x0E54
    # (1 row), likewise present in both images.
    ("donor_cid", 0x1265, "ultimate_conductor_tyranno"),
    ("populate_table", 0x1758, "ultimate_conductor_tyranno"),
    ("summon_procedure_table", 0x1758, "ultimate_conductor_tyranno"),
    ("summon_procedure_table", 0x1265, "ultimate_conductor_tyranno"),
    ("nomi_class2_list", 0x1758, "ultimate_conductor_tyranno"),
    ("cls1_table", 0x0E54, "ultimate_conductor_tyranno"),
    # C2 (built: Junk Defender-shaped cls3 over 0x0E46; speed-2 list 0x0209C118
    # over 0x1529 -- the LAST unclaimed phantom in that list (checked vs PHANTOM_CLAIMS + the chain ROM).
    ("cls3_table", 0x0E46, "ultimate_conductor_tyranno"),
    ("quickeffect_list", 0x1529, "ultimate_conductor_tyranno"),
    ("quickeffect_list", 0x1265, "ultimate_conductor_tyranno"),
    # ---------------------------------------------------------------------
    # Overtex Qoatlus on Normal Monster Prevent Rat 0x10A5 (notes/overtex-qoatlus-findings.md). Phantoms have no card_prop and were unclaimed in their pools in
    # rom_all_patches.nds: criteria 0x0E92 (1 row, claimed nowhere); 0x18B9 = registry row (-> 0x02261F8D)
    # AND ARM9 nomi class-2 list 0x0209BE9C (claimed nowhere).
    ("donor_cid", 0x10A5, "overtex_qoatlus"),
    ("populate_table", 0x0E92, "overtex_qoatlus"),
    ("summon_procedure_table", 0x18B9, "overtex_qoatlus"),
    ("summon_procedure_table", 0x10A5, "overtex_qoatlus"),
    ("nomi_class2_list", 0x18B9, "overtex_qoatlus"),
    # C3 (built: leave mask over 0x174E, cls2 over 0x14DD -- no card_prop,
    # one row, claimed nowhere, present in stock and the chain ROM. (C3 reuses criteria row 0, mode-switched.)
    ("leave_mask_table", 0x174E, "overtex_qoatlus"),
    ("cls2_table", 0x14DD, "overtex_qoatlus"),
    # C2 (built: cls3 over 0x0E4C (no card_prop, one row, claimed nowhere).
    ("cls3_table", 0x0E4C, "overtex_qoatlus"),
    # ---------------------------------------------------------------------
    # Life Stream Dragon on effectless Fusion Steam Gyroid 0x18FA (2026-09-29
    # notes/life-stream-dragon-findings.md). cls1 over 0x0E59 (no card_prop, one row, claimed nowhere, in stock
    # and the chain ROM). The ARM9 "roid" set-code list slot 0x15 gets phantom 0x18F8 in place of the donor.
    ("donor_cid", 0x18FA, "life_stream_dragon"),
    ("cls1_table", 0x0E59, "life_stream_dragon"),
    ("roid_setcode_list", 0x18F8, "life_stream_dragon"),
    # C3: criteria row {0x18FA, 0xFFFF, 0x0223CA11 GY, 0x204 Equip Spell} over 0x0E93 (no card_prop,
    # one row, claimed nowhere, in stock and the chain ROM).
    ("populate_table", 0x0E93, "life_stream_dragon"),
    # Ojamassimilation on Normal Spell Gryphon's Feather Duster 0x170F (C1+C2;
    # notes/ojamassimilation-findings.md). cls0 rewritten in place; ONE criteria row over 0x0EA9 (no card_prop,
    # one row, not in list A/B, no row's aux, same row in stock and the chain ROM; Double Evolution Pill's
    # vetting, then un-claimed). Its ignition_cond_registry phantom row is a different table, untouched.
    ("donor_cid", 0x170F, "ojamassimilation"),
    ("populate_table", 0x0EA9, "ojamassimilation"),
    # C3 (2026-10-01: phantom 0x1452's cls2 record (unclaimed; stock cls2[89]) dropped for
    # 0x170F's GY-effect record, and its sibling-family GY-action row 13 converted to the Grapha family for 0x170F
    # (dragunity_remus method). 0x1452's populate_table row stays reborn_tengu's -- a different pool.
    ("cls2_table", 0x1452, "ojamassimilation"),
    ("gy_action_registry", 0x1452, "ojamassimilation"),   # sibling row 13 converted
    ("gy_action_registry", 0x170F, "ojamassimilation"),   # the donor's GY-action row
    # Ojama set code 0x0D (ARM9 list 0x0209C9E6, 16 entries): phantom 0x0EB0 (no card_prop, in no other set
    # list) swapped for the donor in place so Ojama Blue's Deck search (row aux 0x0D) finds it.
    ("ojama_setcode_table", 0x0EB0, "ojamassimilation"),
    # Obedience Schooled on Normal Spell Abyssal Designator 0x17F4 (notes/obedience-schooled-findings.md). cls0[554] and criteria row 312 are the donor's own, rewritten in
    # place (no phantom). Its LP-cost table row 0x0226F254 {0x17F4, 1000} is zeroed in place.
    ("donor_cid", 0x17F4, "obedience_schooled"),
    ("lp_cost_table", 0x17F4, "obedience_schooled"),
    # C3b: End-Phase registry row 249 {0x02253EC9, phantom 0x0E8C} -> {0x02254E95, 0x17F4} (0x0E8C: no card_prop,
    # unclaimed in every pool, stock == chain).
    ("registry_row", 0x0E8C, "obedience_schooled"),
    # ---------------------------------------------------------------------
    # Gravekeeper's Recruiter, RE-HOMED onto the records-free Normal
    # Monster Battle Steer 0x0FB4 (donor_scan VERDICT CLEAN).  The old build
    # cannibalised Botanical Girl 0x1ED4, a real Effect Monster, and DEPENDED on
    # her native records: it overwrote her cls2 record and her populate row in
    # place and reused her membership in list30 (the sent-to-GY leave list).  A
    # records-free donor has none of those, so both records are now count-neutral
    # sorted inserts and the list30 membership is bought with an ov5 shim
    # (CAVE_GK_ARMTRAMP) rather than a table edit -- list30 has NO phantom to drop
    # and cannot be grown in place.  Botanical Girl is handed back whole.
    ("cls2_table", 0x0E16, "gravekeepers_recruiter"),       # phantom dropped for the donor's cls2 record
    ("populate_table", 0x0E2B, "gravekeepers_recruiter"),   # phantom dropped for the donor's criteria row
    ("donor_cid", 0x0FB4, "gravekeepers_recruiter"),
    # ARM9 "Gravekeeper's" set-code list @0x0209C986 (16 x u16, count hardcoded
    # `movs r2,#0x10` in TWO thunks).  This claim was never registered when the
    # card first shipped -- steam_synchron's comment above already records it in
    # prose ("gravekeepers_recruiter spent it"), so write it down properly.
    ("gk_setcode_table", 0x2442, "gravekeepers_recruiter"),  # phantom dropped
    ("gk_setcode_table", 0x0FB4, "gravekeepers_recruiter"),  # the donor joins
    # Leave-mask table @0x0226EC1C -- the TRIGGER registration. A records-free donor
    # cannot join list30 (the path Botanical Girl was native to): all 30 entries are
    # real cards, 0x0226E940 abuts it so it cannot grow up, and growing DOWN into the
    # 2 B pad at 0x0226E902 needs a cid < 0x0D7C, where all 52 real cids are Speed
    # Spells, not monsters. The mask table is the engine's own answer for exactly
    # this (event.leave_dispatcher_three_registers), and mask 0x0800 is field-only
    # anyway (event.leave_mask_is_field_only) -- which is what "this card YOU CONTROL
    # is sent to your GY" means. Same recipe as lightpulsar PART M, whose donor
    # 0x0FB1 is one cid away and shares this donor's generic switch arm.
    ("leave_mask_table", 0x0E49, "gravekeepers_recruiter"),   # phantom dropped (mask 0x0600)
    # ---------------------------------------------------------------------
    # Thunder Sea Horse, RE-HOMED from Thunder Dragon 0x114F onto the
    # records-free vanilla Fiend Kraken 0x0FEC (donor_scan CLEAN).  The old build
    # repointed Thunder Dragon's cls2 record + criteria row in place; both are now
    # count-neutral sorted inserts on the donor and Thunder Dragon is handed back.
    ("cls2_table", 0x0E9E, "thunder_sea_horse"),        # phantom dropped for the donor's cls2 record
    ("populate_table", 0x0EB0, "thunder_sea_horse"),    # phantom dropped for the donor's criteria row
    ("donor_cid", 0x0FEC, "thunder_sea_horse"),
    # ⚠️ NEW POOL. ARM9 hand-effect cid list @0x0209BC4E (30 x u16, sorted, count
    # `movs r2,#0x1E` @0x02023550). The hand menu 0x0224BC40 consults a card's cls2
    # record only if 0x0202354C(cid) = this list || the quick-effect list 0x0209BC8C.
    # Members: Kuriboh, D.D. Crow, Thunder Dragon, Captain Gold, Zeradias... Phantoms
    # 0x0EB2 and 0x1B42; 0x1B42 is spent here, 0x0EB2 remains (inert: grapha rekeyed
    # its GY row, not this list).
    ("handfx_list", 0x1B42, "thunder_sea_horse"),       # phantom dropped
    ("handfx_list", 0x0FEC, "thunder_sea_horse"),       # the donor joins
    # ---------------------------------------------------------------------
    # Tour Guide From the Underworld, RE-HOMED from the real Effect
    # Monster Synchron Explorer 0x229E onto the records-free vanilla Rock Ogre
    # Grotto #1 0x0FC2 (donor_scan: VERDICT CLEAN).  A records-free donor has no
    # cls1 record, no criteria row and no summon-trigger membership, so the
    # "when this card is Normal Summoned" trigger is built from three
    # count-neutral inserts -- the Hanzo / Boggart recipe.  All three phantoms
    # were checked against this list AND against the chained image
    # rom_all_patches.nds (still present there, i.e. unspent).
    ("summon_list_c7", 0x0E7E, "tour_guide"),   # code-7 Normal-Summon membership
    ("cls1_table",     0x0E1B, "tour_guide"),   # the cls1 record the event dispatches to
    ("populate_table", 0x0E2E, "tour_guide"),   # the Lv3-Fiend hand+Deck criteria row
    # ADDED after in-game test 1: the summon worked but NO rider node
    # was attached, so neither the negate nor the Synchro-Material embargo fired.
    # Two more lists gate that, and a records-free donor is in neither.
    #   0x0228F750 x 0x2E -- the WRITE side.  0x0226806E binary-searches this list
    #     on the summoning card's cid and, only on a hit, attaches the node
    #     {key = that cid (read generically), kind = 3} to the summoned monster.
    #     No membership => no node => both riders silently absent.
    #   0x0226FAB4 x 0x23 -- the READ side for the negate half.  0x021EE402 walks
    #     the node pool 0x0229D33C, accepts kind < 6, and honours the node ONLY if
    #     its key is in this list (same shape as
    #     dispatch.level_rider_key_is_a_selector).
    # Each list has exactly ONE phantom and this patch takes it.  The embargo half
    # needs no list: deny key 5 of the Synchro-material predicate already points
    # at the donor.
    ("rider_attach_list_k3", 0x0E4B, "tour_guide"),
    ("negate_reader_keys",   0x0E57, "tour_guide"),
    # ⚠️ NOT A PHANTOM CLAIM, but the ledger is where it will be looked for: the
    # embargo spends deny key 5 of the Synchro-material predicate -- pool word
    # 0x022485B0, natively 0x24B5 Vylon Element -- plus a 2 B BNE->NOP at
    # 0x022485A6 that drops key 5's "except for a 'Vylon' Synchro" exception.
    # Keys 1-4 (0x225E Cherry Inmato, 0x2273 Chaos Goddess, 0x237A Necro Linker,
    # 0x231F Wiseman's Chalice) stay NATIVE and tour_guide.verify() pins
    # them, so a second patch reaching for that predicate will trip.  Key 5 is
    # the only one of the five with no arithmetic successor, which is why a
    # Normal-Monster donor has to take it -- see notes/tour-guide-findings.md.
    ("donor_cid", 0x0FC2, "tour_guide"),
    # ---------------------------------------------------------------------
    # Wattcobra, RE-HOMED off Blackwing - Fane the Steel Chain 0x2069
    # (a real Effect Monster, borrowed only for its two NATIVE data grants) onto
    # the records-free vanilla WATTKID 0x0FD3.  The migration note filed this card
    # as Tier B behind "is the battle-damage trigger dispatched to any cls1 record,
    # or gated by a membership list?" -- it IS a membership list, mapped this
    # session at 0x021D020A (notes/wattcobra-normal-donor-findings.md), so the
    # whole trigger is DATA and each half costs one count-neutral phantom drop.
    # Every phantom below was checked against this ledger AND against the CHAINED
    # image rom_all_patches.nds (still present there, i.e. unspent).
    # NOTE the donor needs NO set-code claim: Wattkid is already entry 0 of the
    # ARM9 "Watt" table 0x0209CBEA, which is why it is the right donor at all.
    ("donor_cid", 0x0FD3, "wattcobra"),
    # ⚠️ NEW POOL. The direct-attack GRANT list 0x0226D730 (25 x u16, sorted,
    # count immediate `movs r2,#0x19` @0x021A6BDC, one literal ref @0x021A6D98) --
    # "This card can attack your opponent directly" is exactly membership here.
    # Six phantoms shipped in it; this patch takes the first.
    # ⚠️ shooting_quasar PART O edits the ABUTTING double-attack list
    # 0x0226D712 and its verify() used to byte-compare this whole region against
    # clean; that tripwire was narrowed (sorted-25 + piercing-region
    # compare) so the two compose.  Keep it narrow, not deleted.
    ("direct_attack_list", 0x0EB3, "wattcobra"),
    # ⚠️ NEW POOL. The "inflicts Battle Damage BY A DIRECT ATTACK" trigger list
    # 0x0226EE7C (19 x u16, sorted, count immediate `movs r2,#0x13` @0x021D021A,
    # one literal ref @0x021D03FC).  A miss means the cls1 event is never posted.
    # Its ungated sibling LIST B 0x0226EEA4 x 0x33 ("inflicts Battle Damage", any
    # attack) is a SEPARATE pool and is deliberately NOT joined -- that is what
    # keeps the trigger direct-attack-only.  Four phantoms shipped in list A.
    ("da_damage_trigger_list", 0x0EC0, "wattcobra"),
    # cls1: the handler row, cloned from Fane's slot-for-slot with only the +04
    # resolver swapped to the shared add-to-hand 0x02207EF5.  0x0E14 has no
    # card_prop record and owns exactly one cls1 row.  ⚠️ the cls1 pool is split
    # across the names "cls1" and "cls1_table" in this file -- BOTH were checked.
    ("cls1", 0x0E14, "wattcobra"),
    # populate: the candidate-list row the add-to-hand resolver reads.  This claim
    # is not new behaviour (the Fane build already dropped 0x2347 here) but it was
    # never registered; see the tg_striker correction above.
    ("populate_table", 0x2347, "wattcobra"),
    # MATHEMATICIAN (donor Boneheimer 0x13B6), pure data. Every phantom has no
    # card_prop, is unclaimed under every pool name (cls1 AND cls1_table checked)
    # and was still present in rom_all_patches.nds.
    ("donor_cid", 0x13B6, "mathematician"),
    # ACCEL SYNCHRO STARDUST DRAGON (donor Meteor B. Dragon 0x126F, effectless Fusion ->
    # Synchro). Approved by the user. donor_scan: only binding hit is its own
    # fusion recipe A[52] result row, 0 advisory, 0 CPU decks. Claimed ahead of the build
    # so no other session picks it; the patch module does not exist yet.
    ("donor_cid", 0x126F, "accel_synchro_stardust_dragon"),
    # C1. Both phantoms: no card_prop, exactly ONE row in their table in
    # BOTH the stock ov3 and rom_baseline.nds, unclaimed under every pool name ("cls1"
    # AND "cls1_table" checked). 0x1280's only structure is its cls1 record; 0x14BA also
    # owns an unreachable cls2 record (no card_prop), left untouched.
    ("cls1_table", 0x1280, "accel_synchro_stardust_dragon"),
    ("populate_table", 0x14BA, "accel_synchro_stardust_dragon"),
    # C2. cls3 0x14B9: no card_prop, its cls3 row is its only structure, and
    # the drop/insert span is rows 53..85 stock / 53..86 chained -- above accel_synchron's
    # cls3[50] and below every BY-INDEX anchor (223/233 shiens_dojo, 334 maiden, 527
    # sea_lancer). Criteria 0x1445: no card_prop, one row (its cls0/cls2 records are
    # unreachable). 0x0E82: spell-speed-2 list phantom, present in stock AND chained,
    # claimed in no pool (0x0EB2 rejected -- grapha spends it elsewhere).
    ("cls3_table", 0x14B9, "accel_synchro_stardust_dragon"),
    ("populate_table", 0x1445, "accel_synchro_stardust_dragon"),
    ("quickeffect_list", 0x0E82, "accel_synchro_stardust_dragon"),
    # C3. Criteria 0x0EBE: no card_prop, exactly one row in stock AND
    # rom_baseline.nds, its only other structure an unreachable cls2 record. (0x14D7/0x1507/
    # 0x1508 are fusion-recipe cids, 0x14DD/0x0EB9 list106 members, 0x1529's row is another
    # phantom's aux -- all passed over.)
    ("populate_table", 0x0EBE, "accel_synchro_stardust_dragon"),
    ("summon_list_c7", 0x15D0, "mathematician"),
    ("cls1_table", 0x0E1F, "mathematician"),
    ("populate_table", 0x0E3C, "mathematician"),
    ("cls2_table", 0x0E1C, "mathematician"),
    ("draw_count_table", 0x16C1, "mathematician"),
    # ⚠️ NEW POOL. list106 @0x0226E990 (0x6A x u16, sorted, count immediate
    # `movs r2,#0x6A` @0x021C80D2, ONE literal ref @0x021C831C) = "destroyed by
    # battle and sent to the GY" (leave dispatcher 0x021C80BC).
    ("list106", 0x1B46, "mathematician"),
    # Koa'ki Meiru Wall on Dark Rabbit 0x1126 (. Phantoms have no
    # card_prop, own exactly one row, and are present in BOTH stock rom.nds and rom_all_patches.nds.
    ("koaki_setcode_table", 0x2444, "koaki_meiru_wall"),   # set code 0x46 -- Wall's own 3DS cid
    ("populate_table", 0x0E39, "koaki_meiru_wall"),        # the donor's Rock criteria row
    ("cls3_table", 0x0E22, "koaki_meiru_wall"),            # the donor's Spell-negate record
    ("quickeffect_list", 0x0E63, "koaki_meiru_wall"),
    # ⚠️ NEW POOL, GROWN not swapped: hand-criteria list 0x0228EF48 (31 real cids, no phantom)
    # takes a 32nd entry in its u16 alignment pad 0x0228EF86; count `movs r2,#0x1F` @0x0225A418.
    ("hand_criteria_list", 0x1126, "koaki_meiru_wall"),
    # Naturia Pineapple on Headless Knight 0x1465. Phantoms have no card_prop, own
    # exactly one row, and are present in BOTH stock rom.nds and rom_all_patches.nds (probe).
    ("donor_cid", 0x1465, "naturia_pineapple"),
    ("registry_row", 0x1338, "naturia_pineapple"),        # Standby row 316 -> {0x022573DD, 0x1465}
    ("cls2_table", 0x1435, "naturia_pineapple"),
    ("naturia_setcode_table", 0x23F4, "naturia_pineapple"),  # set code 0x3C -- Pineapple's own 3DS cid
    # Elder of the Six Samurai RE-DONORED from AoJ Cosmic Gateway 0x1F1D
    # (an effect monster whose native hand-SS dispatch-tree node was retargeted) onto
    # Flame Cerebrus 0x11B7, a records-free Normal Monster (donor_scan CLEAN). The
    # dispatch-tree retarget only works for a donor that already owns a tree node, so
    # the effect is now the shared hand-SS trampoline (CAVE_ELDER_SSCOND, ov5_cave.py)
    # instead -- same condition, same primitives, per tg_striker's precedent.
    # PART E (removing the old donor from the AoJ set-code table) no longer applies:
    # Flame Cerebrus was never an AoJ member. azure_eyes already tolerates this
    # (its AOJ_COUNT_NATIVE branch), so the table now simply keeps its native 21 entries.
    ("donor_cid", 0x11B7, "elder_six_samurai"),
    ("sixsam_setcode_table", 0x251B, "elder_six_samurai"),  # phantom dropped (Elder's own real Konami ID)
    # Crimson Blader on Crimson Sunbird 0x1179, a LEVEL 6 effectless Fusion (user: Lv6+ only).
    # donor_scan: ONE binding occurrence, its own fusion recipe A[31] @0x02270C8C, result
    # column only; 0 ambiguous ARM9 hits, 0 code-region hits, 0 CPU decks.  Blanking that
    # recipe costs nothing -- its material 0x1178 has no card_prop record, so the fusion was
    # already unperformable.  Both phantoms own exactly one row and carry no card_prop record,
    # and both were checked in rom.nds AND rom_all_patches.nds.
    ("donor_cid", 0x1179, "crimson_blader"),
    # NEW POOL: the attacker-side battle-destruction trigger table 0x0226EA64
    # ({u16 cid, u16 mask}, 110 rows, count `movs r2,#0x6E` @0x021CAAF4, sole LDR @0x021CAAF2).
    # It ships with FOUR phantoms at its head -- 0x0E12, 0x0E8A, 0x0E9C, 0x0EA7 -- so three
    # remain after this one.  mask 0x000F == "destroys an OPPONENT's monster by battle and sends
    # it to the GY" (Goyo Guardian 0x1E38, Hydro Genex 0x1E9A, Jurrac Spinos 0x2031 ...).
    ("battle_destroy_flags", 0x0E9C, "crimson_blader"),
    ("cls1_table", 0x1197, "crimson_blader"),
    # ---------------------------------------------------------------------
    # DRAGUNITY REMUS, CLAUSE 2 ONLY. Donor Petit Dragon 0x106E: a vanilla
    # Normal Monster that is ALREADY WIND / Dragon / Level 2 (Remus's own attribute, race
    # and level), records-free in all FOUR cls tables, owns no criteria row and no row in
    # the ignition-cond registry 0x0226FAFC, is a member of NO set-code list and of neither
    # hand list. Literal scan: exactly one u16 hit in arm9 (0x02022E4E, inside
    # the bsearch function's CODE -- an instruction encoding, not a cid) and one in ov3
    # (0x02270C00, a fusion-recipe row, left untouched). Pure data: no ov5 cave, no Thumb.
    ("donor_cid", 0x106E, "dragunity_remus"),
    # The ARM9 hand-effect cid list 0x0209BC4E (dispatch.hand_effect_offer_list) -- without
    # membership the cls2 record is never consulted and the effect is never offered from
    # hand (Thunder Sea Horse in-game test 1).
    # ⚠️ 0x0EB2 IS THE LAST FREE PHANTOM IN THIS LIST. 0x1B42 went to thunder_sea_horse, and
    # after this claim the list can only grow by displacing a real card. 0x0EB2 is claimed by
    # grapha in the gy_action_registry pool -- a DIFFERENT pool, hence legal, and this list's
    # own block comment already records that its membership here is inert.
    ("handfx_list", 0x0EB2, "dragunity_remus"),          # phantom dropped
    ("handfx_list", 0x106E, "dragunity_remus"),          # the donor joins
    # Both phantoms: no card_prop, exactly ONE row in their table, claimed under no pool name.
    ("cls2_table", 0x0E1D, "dragunity_remus"),           # the donor's hand-ignition record
    ("populate_table", 0x0E3D, "dragunity_remus"),       # the donor's "named card in my Deck" row
    # ⚠️ NEW POOL, DISPLACEMENT not insert: the "Dragunity" set-code list 0x0209CBC0 (set code
    # 0x4A, thunk 0x02023DFD, count `movs r2,#0x15` @0x02023E00, pool literal @0x02023E04) holds
    # 21 REAL cards with NO phantom, so a new member COSTS an old one -- the
    # white_dragon_ninja / Sazank precedent. Base and count are left untouched and the
    # array stays strictly sorted; only the membership set changes.
    # EVERY alternative was eliminated first: the region has no slack -- the lists
    # are packed and every apparent gap is another cid list on a differently-shaped thunk, the
    # largest all-zero run being 2 B, and the 128 B at 0x0209D058 between the last list and the
    # pointer table is a live {u16 cid, u16 group} table read via thunk 0x02023804. Shifting a
    # neighbour is out because ELEVEN shipped modules hardcode the neighbouring bases (forward:
    # Watt 0x0209CBEA in wattcobra + ee/patches/wattcobra, Karakuri 0x0209CC16 in
    # ninishi + ee/patches/ninishi + karakuri_haipa; backward: AoJ 0x0209CB96 in
    # azure_eyes, X-Saber 0x0209CB6E in xsaber_table, T.G. 0x0209CB48 in tg_table +
    # hyper_librarian + ee/arm9.py + ee/test_utils.py). Relocating the list to ov5 is WRONG
    # -- all 12 BL callers of the thunk are in ov3, resident in every duel mode, while ov5 is
    # evicted by ov41 in a puzzle, so the bsearch would read overlay-41 data and return silent
    # wrong answers. ov3 is the right host but has only 38 B free, fragmented into 8..12 B blocks.
    # And the appended ARM9 cave is FALSIFIED, not merely unproven: its canary was RUN
    # and FREEZES on entering a duel.
    # DISPLACED: Dragunity Knight - Trident 0x2180 (USER'S CHOICE). A Level 10
    # Extra-Deck Synchro that no "Dragunity" test can reach -- not searchable from the Deck, not
    # equippable, and every GY-targeting Dragunity effect filters "Level 3 or lower Dragon". It
    # keeps its effect, its Synchro materials and its Extra-Deck presence; it loses only its
    # contribution to Dux's "gains 200 ATK for each 'Dragunity' card you control".
    ("dragunity_setcode_table", 0x2180, "dragunity_remus"),   # Trident displaced
    ("dragunity_setcode_table", 0x106E, "dragunity_remus"),   # the donor joins

    # --- wattuna -- Wattuna on Spirit of the Harp 0x1050 ---
    # Every phantom below was proven absent from card_prop via donor_scan.cards()
    # and present in BOTH the stock ROM and rom_all_patches.nds; each owns exactly
    # one row in its table.  scratch/cid_to_name.json was NOT used (partial dump).
    ("donor_cid", 0x1050, "wattuna"),
    ("direct_attack_list", 0x1129, "wattuna"),      # U1: phantom dropped from 0x0226D730
    ("direct_attack_list", 0x1050, "wattuna"),      # U1: the donor joins
    ("da_damage_trigger_list", 0x1DB6, "wattuna"),  # U4: phantom dropped from LIST A 0x0226EE7C.
                                                    #   ⚠️ 0x1DB6 is ALSO claimed as ("cls1_table",
                                                    #   …, "maiden_eyes_of_blue") -- a DIFFERENT pool
                                                    #   and a different resource; that cls1 row is
                                                    #   already spent, so the LIST A entry was its
                                                    #   last surviving occurrence.
    ("da_damage_trigger_list", 0x1050, "wattuna"),  # U4: the donor joins
    ("cls1", 0x1147, "wattuna"),                    # U4: the Synchro-summon resolver row
                                                    #   (⚠️ the cls1 pool is split across "cls1" and
                                                    #   "cls1_table" -- see the note at the top of
                                                    #   this list; 0x1147 is free under BOTH)
    ("cls2_table", 0x0EC3, "wattuna"),              # U3: the hand self-SS record
    ("populate_table", 0x0EB9, "wattuna"),          # U4: the "Watt Synchro" criteria row
    # The battle-time hand-responder list 0x0209BD20 (38 entries, thunk 0x02023574,
    # count imm @0x02023578).  A THIRD ARM9 hand list, distinct from
    # dispatch.hand_effect_offer_list's 0x0209BC4E / 0x0209BC8C -- found.
    ("handresp_list", 0x0E68, "wattuna"),           # U3: phantom dropped (index 0)
    ("handresp_list", 0x1050, "wattuna"),           # U3: the donor joins
    # The hand-material Synchro gate's dead literal @0x02249534 (synchro.
    # native_hand_material_mode).  0x0E66 has no card_prop; it is claimed elsewhere
    # only under "cls2_table" by hyper_librarian_chain -- a different pool.
    # REASSIGNED to Mara of the Nordic Alfar (user: "Take the literal");
    # Wattuna's U4 hand material needs a new design (notes/wattuna-findings.md).
    ("hand_material_gate", 0x0E66, "mara"),
    # Mara of the Nordic Alfar (2026-10-05 on records-free Happy Lover 0x106C;
    # Nordic subtype table 0x0209CEF8 (18 x {cid, subtype}) drops phantom 0x24F0 (3DS The Nordic Lights).
    ("donor_cid", 0x106C, "mara"),
    ("nordic_subtype_table", 0x24F0, "mara"),
    # PART F -- "Watt" set code 0x58, ARM9 list 0x0209CBEA.  A count-neutral
    # DISPLACEMENT, not an insert: the list is boxed in between the Dragunity 0x4A
    # and Karakuri 0x5D lists with zero slack, so it cannot grow in place.  The user
    # nominated Wattkey / Wattcannon / Wattcine / Wattcastle as expendable
    #; all four are Watt Spell/Traps whose own membership nothing reads.
    # NOT optional: Wattchimera and Watthydra are each "1 *Watt* Tuner + 1+ non-Tuner
    # Thunder monsters", enforced by has_set_code(material, 0x58) at 0x02248A42, so
    # without this the Synchro material picker refuses every cell (in-game failure 2).
    ("watt_setcode_table", 0x2481, "wattuna"),      # Wattkey displaced
    ("watt_setcode_table", 0x1050, "wattuna"),      # the donor joins
    ("ov3_dead_arm", 0x1433, "wattuna"),            # U4 E2: gate-tail stub in this phantom's leaf 0x021BB288
    ("battle_damage_poster", 0x0EC4, "wattuna"),    # U3 printed timing: dead phantom arm @0x021D07C4
    #   repurposed as a HAND post of 0x1050 for the attacker (PART H)
    ("mover_handss_chain", 0x1050, "wattuna"),      # U3 Watapon-style: 0x021C73AE chain rewrite (PART G)
    # Wattkyuki (2026-10-05 on effectless Fusion St. Joan 0x1458 -> Synchro.
    # C0 is two private ov3 detours (0x02248660 / 0x02248AFA -> CAVE_WK_OUTER / CAVE_WK_THIRD).
    ("donor_cid", 0x1458, "wattkyuki"),
    ("direct_attack_list", 0x1133, "wattkyuki"),    # C1: phantom dropped from 0x0226D730
    ("direct_attack_list", 0x1458, "wattkyuki"),    # C1: the donor joins
    ("watt_setcode_table", 0x232A, "wattkyuki"),    # Wattcannon displaced (user decision)
    ("watt_setcode_table", 0x1458, "wattkyuki"),    # the donor joins
    ("da_damage_trigger_list", 0x1A1F, "wattkyuki"),  # C2: phantom dropped from LIST A 0x0226EE7C
                                                      #   (0x1A1F's registry_row belongs to kuribandit -- other pool)
    ("da_damage_trigger_list", 0x1458, "wattkyuki"),  # C2: the donor joins
    ("cls1", 0x0E9B, "wattkyuki"),                    # C2: the trigger row (phantom's only cls1 row)
    ("populate_table", 0x0E9B, "wattkyuki"),          # C2: the phase-keyed criteria row (its only criteria row)
    # NOTE: wattuna claims NO ov5 cave slot.  Build 1's CAVE_WU_ED was
    # retired before shipping -- the criteria row now points at
    # Blackwing Aurora's STOCK handler 0x022430A1, so the module injects no code.
    # JUNK SPEEDER RE-DONOR (user-approved): Daigusto Sphreeze 0x24B3 ->
    # Twin-Headed Thunder Dragon 0x120B, an EFFECTLESS Level 7 Fusion monster.  The old
    # donor was rewritten in place and claimed nothing here; the vanilla donor owns
    # neither record, so both are count-neutral inserts.  donor_scan: 0x120B's only
    # binding occurrence in ov3 + ARM9 is its own fusion recipe A[47], which the patch
    # blanks.  Sphreeze is left completely untouched and goes back to being itself.
    ("donor_cid", 0x120B, "junk_speeder"),
    # Both phantoms own EXACTLY ONE row in their table and are unclaimed under every
    # pool name.  0x12A9's cls1 record[113] is its ONLY binding structure anywhere;
    # 0x16C2's criteria row[247] leaves behind only an unreachable cls1 record[332]
    # (no card_prop, never dispatched), which is the least of any unclaimed criteria
    # phantom -- every other carries three or more.
    ("cls1_table", 0x12A9, "junk_speeder"),
    ("criteria_table", 0x16C2, "junk_speeder"),
    # Petiteranodon C1+C2+C3 (on records-free Normal Mammoth
    # Graveyard 0x0FE1.  Phantom 0x0E6A owns exactly one cls2, one criteria and one leave-mask row
    # in BOTH rom.nds and rom_all_patches.nds and nothing else; all three rows are dropped.
    ("donor_cid", 0x0FE1, "petiteranodon"),
    ("cls2_table", 0x0E6A, "petiteranodon"),
    ("populate_table", 0x0E6A, "petiteranodon"),
    ("leave_mask_table", 0x0E6A, "petiteranodon"),
    ("leave_mask_table", 0x0FE1, "petiteranodon"),   # the donor's leave row
    # PART F: sent-to-GY chain node 0x021D13C2 re-keyed in place from PHANTOM 0x0EC9 to the
    # donor, routed to Babycerasaurus's arm 0x021D18D2 (off-field "destroyed by effect -> GY").
    ("gy_switch_node", 0x0EC9, "petiteranodon"),
    # BRILLIANT FUSION C1 + C4 (brilliant_fusion) on Temple of the Sun 0x21D5 (donor_scan CLEAN, zero records). One cls0 insert and
    # two criteria rows, each count-neutral over a phantom with no card_prop row that is present in
    # BOTH rom.nds and rom_all_patches.nds (0x1507 / 0x1508 own exactly one criteria row each).
    ("donor_cid", 0x21D5, "brilliant_fusion"),
    ("cls0", 0x143B, "brilliant_fusion"),               # phantom dropped
    ("cls0", 0x21D5, "brilliant_fusion"),
    ("cls0", 0x234C, "seal_of_orichalcos"),             # phantom dropped (C4/C6 activation record)
    ("cls0", 0x10F5, "seal_of_orichalcos"),
    ("criteria_table", 0x1507, "brilliant_fusion"),     # phantom dropped
    ("criteria_table", 0x1508, "brilliant_fusion"),     # phantom dropped
    # build 3: criteria row-offset LIST A 0x0227134C, so param != 0 selects row 1 (the material pool) --
    # as for Future Fusion / Polymerization. 0x1303 has no card_prop row and is still in list A in
    # both rom.nds and rom_all_patches.nds (its other claim is populate_table, a different pool).
    ("membership_list_a", 0x1303, "brilliant_fusion"),  # phantom dropped
    ("membership_list_a", 0x21D5, "brilliant_fusion"),
    # build 4 (C2): leave-cleanup list 0x0226E940 -- 0x0E48 is its LAST phantom in rom_all_patches.nds
    # (NAST spent 0x0E42). No card_prop row.
    ("leave_cleanup_list", 0x0E48, "brilliant_fusion"),  # phantom dropped
    ("leave_cleanup_list", 0x21D5, "brilliant_fusion"),
    # build 5 (C3): cls3 ignition record. 0x234B = cls3[711] in BOTH rom.nds and
    # rom_all_patches.nds, no card_prop row, its only other binding a code literal (ov3:0x021B34E8).
    # The donor lands at [645]: the shift range 645..711 is above every by-index cls3 anchor (527).
    ("cls3_table", 0x234B, "brilliant_fusion"),          # phantom dropped
    ("cls3_table", 0x21D5, "brilliant_fusion"),
    # RAIDEN, HAND OF THE LIGHTSWORN (raiden) on Rogue Doll 0x0FD2 (donor_scan CLEAN). Phantoms picked by
    # scratch/raiden_pick_phantoms.py, present in BOTH rom.nds and rom_all_patches.nds, no card_prop
    # row: 0x0ECB is a whole phantom End-Phase card (one cls1 row + End-Phase registry row 100 on
    # Jain's poster 0x02253EC9) and both are consumed; 0x0EBC owns one cls3 row (shift range
    # 34..38, below every by-index cls3 anchor).
    ("donor_cid", 0x0FD2, "raiden"),
    ("cls1_table", 0x0ECB, "raiden"),                  # phantom dropped
    ("cls1_table", 0x0FD2, "raiden"),
    ("registry_row", 0x0ECB, "raiden"),                # row 100, cid rewritten to 0x0FD2
    ("cls3_table", 0x0EBC, "raiden"),                  # phantom dropped
    ("cls3_table", 0x0FD2, "raiden"),
    # ANIMADORNED ARCHOSAUR (animadorned_archosaur
    #) on Swordsman of Landstar 0x1297 (donor_scan CLEAN). Phantoms from
    # scratch/archosaur_pick_phantoms.py, present in BOTH rom.nds and rom_all_patches.nds, no card_prop:
    # 0x0E77 = the NS-OR-SS trigger list 0x0228F60A (code 7 or 9; 0x1297 takes its exact slot, zero
    # shift); 0x12A6 = one cls1 row (shift window 105..112, no by-index cls1 anchor); 0x0EAE = one
    # criteria row (+ an orphan cls0 record, untouched; not in lists A/B; window 61..83 crosses no
    # address anchor -- dragon_shrine crit[157] and shiens_dojo's 0x19B5 row are outside it).
    ("donor_cid", 0x1297, "animadorned_archosaur"),
    ("summon_list_c79", 0x0E77, "animadorned_archosaur"),
    ("cls1_table", 0x12A6, "animadorned_archosaur"),   # phantom dropped
    ("cls1_table", 0x1297, "animadorned_archosaur"),
    ("populate_table", 0x0EAE, "animadorned_archosaur"),  # phantom dropped
    ("populate_table", 0x1297, "animadorned_archosaur"),
    # eva (Aitsu 0x160A -> Eva Phantoms own exactly one row of the
    # table in BOTH rom.nds and rom_all_patches.nds, have no card_prop, and are unclaimed in that table.
    ("donor_cid", 0x160A, "eva"),
    ("cls2_table", 0x1775, "eva"),                      # phantom dropped
    ("cls2_table", 0x160A, "eva"),
    ("leave_mask_table", 0x0E4A, "eva"),                # phantom dropped
    ("leave_mask_table", 0x160A, "eva"),                # {0x160A, 0x0800} sent-to-GY mask row
    ("populate_table", 0x15D0, "eva"),                  # phantom dropped (criteria row)
    ("populate_table", 0x160A, "eva"),
    # grandsoil (Millennium Shield 0x1110 -> Grandsoil the Elemental Lord). C1 nomi: phantom 0x0E63 is in the chained class-2 list and unclaimed in that pool.
    ("donor_cid", 0x1110, "grandsoil"),
    ("nomi_class2_list", 0x0E63, "grandsoil"),          # phantom dropped
    ("nomi_class2_list", 0x1110, "grandsoil"),
    # Stage B (C3/C4): phantoms one row in BOTH stock and chain, unclaimed in every pool.
    ("summon_list_c79", 0x1B6B, "grandsoil"),           # phantom dropped (N-or-SS list 0x0228F60A)
    ("summon_list_c79", 0x1110, "grandsoil"),
    ("cls1_table", 0x0E5D, "grandsoil"),                # phantom dropped
    ("cls1_table", 0x1110, "grandsoil"),
    ("criteria_table", 0x0E94, "grandsoil"),            # phantom dropped
    ("criteria_table", 0x1110, "grandsoil"),
    # Stage C (C5): node key of the skip-BP predicate 0x0224CF90 (phantom 0x1502), and the dead
    # cls0 resolver body of phantom 0x0EAB that hosts the ov3 leave stub.
    ("bp_lock_node_borrow", 0x1502, "grandsoil"),
    ("ov3_dead_arm", 0x0EAB, "grandsoil"),
    # moulinglacia (Venom Cobra 0x1C1A -> Moulinglacia the Elemental Lord). C1 nomi: phantom 0x0EB3 is in the chained class-2 list and unclaimed in that pool.
    ("donor_cid", 0x1C1A, "moulinglacia"),
    ("nomi_class2_list", 0x0EB3, "moulinglacia"),       # phantom dropped
    ("nomi_class2_list", 0x1C1A, "moulinglacia"),
    # Stage B (C3/C4): phantoms one row in BOTH stock and chain, no card_prop, unclaimed in their pool
    # (scratchpad ml_phantoms.py). 0x0E17's only other claim is populate_table (a different table).
    ("summon_list_c79", 0x0E17, "moulinglacia"),        # phantom dropped (N-or-SS list 0x0228F60A)
    ("summon_list_c79", 0x1C1A, "moulinglacia"),
    ("cls1_table", 0x1C5F, "moulinglacia"),             # phantom dropped
    ("cls1_table", 0x1C1A, "moulinglacia"),
    # pyrorex (Harpie Girl 0x181F -> Pyrorex the Elemental Lord).
    # Phantoms present in BOTH stock and chain, no card_prop, unclaimed in their pool (scratchpad pyro_phantoms.py).
    # 0x176C / 0x164A are the LAST free phantoms of the nomi class-2 / N-or-SS lists.
    ("donor_cid", 0x181F, "pyrorex"),
    ("nomi_class2_list", 0x176C, "pyrorex"),            # phantom dropped
    ("nomi_class2_list", 0x181F, "pyrorex"),
    ("summon_list_c79", 0x164A, "pyrorex"),             # phantom dropped (N-or-SS list 0x0228F60A)
    ("summon_list_c79", 0x181F, "pyrorex"),
    ("cls1_table", 0x17E0, "pyrorex"),                  # phantom dropped
    ("cls1_table", 0x181F, "pyrorex"),
    ("harpie_setcode_table", 0x181F, "pyrorex"),        # REMOVED from set code 0x14 (list 0x0209C8C4)
    ("harpie_setcode_table", 0x181E, "pyrorex"),        # non-card filler written in its place (keeps the list sorted)
    # windrose (Soitsu 0x190B -> Windrose the Elemental Lord).
    # nomi class 2 and the N-or-SS list are FULL: class-4 list 0x0209BC14 + c79_trigger_hook instead.
    ("donor_cid", 0x190B, "windrose"),
    ("nomi_class4_list", 0x19A8, "windrose"),           # phantom dropped (list 0x0209BC14)
    ("nomi_class4_list", 0x190B, "windrose"),
    ("nomi_class4_list", 0x0E22, "block_dragon"),
    ("registry_row", 0x0FDE, "cpu_hand_ss"),
    ("leave_mask_table", 0x0E12, "block_dragon"),   # C3 leave-mask row {0x0FDD, 0x0800}
    ("registry_row", 0x0E5C, "cpu_hand_ss"),   # -> 0x17CD Redox (CPU payment row)
    ("registry_row", 0x0E60, "cpu_hand_ss"),   # -> 0x115F Tidal
    ("registry_row", 0x112E, "cpu_hand_ss"),   # -> 0x1145 Blaster
    ("registry_row", 0x128C, "cpu_hand_ss"),   # -> 0x1125 Tempest   # summon-procedure registry 0x0228F158 row 0x0FDE (handler 0x02261F8D) -> re-keyed to 0x0FDD, CAVE_BD_PAY        # phantom dropped (list 0x0209BC14); Normal Summon/Set block, class 4 like Windrose
    ("c79_trigger_hook_arms", 0x190B, "windrose"),      # shared N-or-SS trigger stub, site 0x02265C44
    ("cls1_table", 0x18E5, "windrose"),                 # phantom dropped
    ("cls1_table", 0x190B, "windrose"),
    # uni_zombie (Illusionist Faceless Mage 0x0FD0 -> Uni-Zombie
    # Stubs in the ov3 pool (cave3.CAVE3_UZ_*); turn-log lock key 0x4FD0 (0x4000 | cid).
    ("donor_cid", 0x0FD0, "uni_zombie"),
    ("cls3_table", 0x0E39, "uni_zombie"),               # phantom dropped
    ("cls3_table", 0x0FD0, "uni_zombie"),
    ("criteria_table", 0x0E41, "uni_zombie"),           # phantom dropped
    ("criteria_table", 0x0FD0, "uni_zombie"),
    # aratama (Souleater 0x13AC vanilla+).
    # All three phantoms: no card_prop, unclaimed in every pool, present in stock + chained images.
    ("donor_cid", 0x13AC, "aratama"),
    ("summon_list_c78", 0x12B4, "aratama"),             # code-7-or-8 list 0x0228F598
    ("summon_list_c78", 0x13AC, "aratama"),
    ("cls1", 0x1506, "aratama"),                        # BOTH rows of phantom Spirit Fushi No Tori
    ("cls1", 0x13AC, "aratama"),                        # [return, search] pair
    ("criteria_table", 0x0E9D, "aratama"),              # phantom dropped
    ("criteria_table", 0x13AC, "aratama"),
    ("flipped_faceup_list", 0x1527, "aratama"),          # ARM9 0x0209BB5C, battle-flip fix
    ("flipped_faceup_list", 0x13AC, "aratama"),
    # sakitama (Grand Tiki Elder 0x13E5, donor_scan CLEAN;
    # Phantoms (scratchpad phantoms.py): no card_prop, row counts identical in rom.nds + rom_all_patches.nds.
    # 0x1774's only other claim is the SPEED-2 list (steam_synchron) -- its cls2 row and its hand-effect
    # LIST B 0x0209BC8C slot were unclaimed. 0x1446's other claim is the ignition-condition registry, not
    # the criteria table (window stock rows 123..129, below crit[157]). Granter key K = 0x3E50 is a
    # turn-log key, not a table slot.
    ("donor_cid", 0x13E5, "sakitama"),
    ("cls1", 0x1500, "sakitama"),                       # phantom's single return-shaped row dropped
    ("cls1", 0x13E5, "sakitama"),                       # return-only (Asura Priest shape)
    ("cls2_table", 0x1774, "sakitama"),                 # phantom dropped
    ("cls2_table", 0x13E5, "sakitama"),                 # ONE record, C3/C4 mode-switched on desc[+3]
    ("criteria_table", 0x1446, "sakitama"),             # phantom dropped
    ("criteria_table", 0x13E5, "sakitama"),
    ("handfx_quick_list", 0x1774, "sakitama"),          # ARM9 hand-effect LIST B 0x0209BC8C, phantom dropped
    ("handfx_quick_list", 0x13E5, "sakitama"),
    ("flipped_faceup_list", 0x1535, "sakitama"),        # ARM9 0x0209BB5C, Aratama parity
    ("flipped_faceup_list", 0x13E5, "sakitama"),
    # nikitama (Wolf 0x0FE3, donor_scan CLEAN; Phantoms checked
    # (scratchpad phant.py) against card_prop and PHANTOM_CLAIMS in rom.nds AND rom_all_patches.nds: 0x0E2F
    # (2 cls1 rows), 0x1B18, 0x120E, 0x0E86 unclaimed everywhere; 0x1534's only other claim is quickeffect_list
    # (its flip-list slot was the LAST free one); 0x0E1C's only other claim is cls2_table (mathematician).
    # Keys G = 0x3E52 / K = 0x3E51 are turn-log keys, not table slots. The sent-to-GY node 0x021D13C2 is
    # FRONTED (literal untouched -- Petiteranodon keeps 0x0FE1).
    ("donor_cid", 0x0FE3, "nikitama"),
    ("cls1", 0x0E2F, "nikitama"),                       # BOTH phantom rows dropped
    ("cls1", 0x0FE3, "nikitama"),                       # [return, gain] pair
    ("cls2_table", 0x1B18, "nikitama"),                 # phantom dropped
    ("cls2_table", 0x0FE3, "nikitama"),                 # C4 sent-to-GY draw
    ("summon_list_c78", 0x120E, "nikitama"),            # code-7-or-8 list 0x0228F598, phantom dropped
    ("summon_list_c78", 0x0FE3, "nikitama"),
    ("flipped_faceup_list", 0x1534, "nikitama"),        # ARM9 0x0209BB5C, last phantom
    ("flipped_faceup_list", 0x0FE3, "nikitama"),
    ("draw_count_table", 0x0E86, "nikitama"),           # phantom dropped
    ("draw_count_table", 0x0FE3, "nikitama"),           # n = 1
    ("leave_mask_table", 0x0E1C, "nikitama"),           # phantom dropped
    ("leave_mask_table", 0x0FE3, "nikitama"),           # 0x0800 any-leave-to-GY
    ("gy_switch_node", 0x0FE3, "nikitama"),             # front over node 0x021D13C2 (CAVE3_NK_GYNODE)
    # Neo Space Connector (2026-10-14 Donor Kanan the Swordmistress 0x1106 (donor_scan CLEAN;
    # base+-imm scan 0 real hits). Phantoms by scratchpad phantom_scan.py (stock AND chain, no card_prop, unclaimed).
    ("donor_cid", 0x1106, "neo_space_connector"),
    # NEXT on Normal Trap Return Soul 0x1B22 (2026-10-15 notes/next-findings.md). cls0[779] and
    # criteria row 489 are the donor's own, rewritten in place (no phantom).
    ("donor_cid", 0x1B22, "next"),
    # Dragon Rulers (dragon_rulers notes/dragon-rulers-findings.md).
    # No cls/criteria phantom: the rulers' records and rows are VIRTUAL (cave3 CAVE3_RUL_* hooks). Donors approved
    # by the user; only Redox is built so far. End-Phase registry row 154 (phantom 0x19C0, resolver
    # 0x02253F89 in stock AND chain) is re-pointed at CAVE3_RUL_H5.
    ("donor_cid", 0x17CD, "dragon_rulers"),             # Charcoal Inpachi -> Redox
    ("donor_cid", 0x115F, "dragon_rulers"),             # Mech Bass -> Tidal
    ("donor_cid", 0x1145, "dragon_rulers"),             # Mechanicalchaser -> Blaster
    ("donor_cid", 0x1125, "dragon_rulers"),             # Parrot Dragon -> Tempest
    ("donor_cid", 0x0FF4, "dragon_rulers"),             # Axe Raider -> Reactan
    ("donor_cid", 0x115E, "dragon_rulers"),             # 7 Colored Fish -> Stream
    ("donor_cid", 0x0FEA, "dragon_rulers"),             # Garoozis -> Burner
    ("donor_cid", 0x1CC6, "dragon_rulers"),             # Atlantean Pikeman -> Lightning
    ("registry_row", 0x19C0, "dragon_rulers"),          # row 154 @0x0228E6B0, resolver -> CAVE3_RUL_H5
    ("summon_list_c7", 0x19D3, "neo_space_connector"),  # NS list 0x0228F7AC -- taken from parked Magician's Rod (user)
    ("summon_list_c7", 0x1106, "neo_space_connector"),
    ("cls1", 0x11EA, "neo_space_connector"),            # C1 cls1 {RES, 0, COND, SLOT4, 0}, phantom dropped
    ("cls1", 0x1106, "neo_space_connector"),
    ("populate_table", 0x14D7, "neo_space_connector"),  # the ONE criteria row (mode-switching handler), phantom dropped
    ("populate_table", 0x1106, "neo_space_connector"),
    ("cls3_table", 0x14D7, "neo_space_connector"),      # C2 cls3 {RES, 0, COND, COST, 0x02235605}; same dead card as the row
    ("cls3_table", 0x1106, "neo_space_connector"),
    # Denko Sekka on Kojikocy 0x0FE8 (denko_sekka notes/denko-sekka-findings.md).
    # donor_scan CLEAN (its ARM9 u16 hits are a sin/cos table). C1 = ARM9 Cannot-SS list 0x0209BD6C over phantom 0x19A8
    # (in stock AND chain; 0x19A8 is claimed only in OTHER pools). C2 = cave3 CAVE3_DENKO_* fronts, no table rows.
    ("donor_cid", 0x0FE8, "denko_sekka"),
    ("cannot_ss_list", 0x19A8, "denko_sekka"),
    # Sekka's Light on Stop Defense 0x10E6 (sekkas_light
    # notes/sekkas-light-findings.md). cls0[103] rewritten in place. C4 cls2 {GYRES,0,GYCOND,GYCOST,0} over
    # phantom 0x1B47 (in the cls2 table of stock AND chain, not a real card, unclaimed). Its GY offer is
    # the 6th Dragon Rulers virtual GY row (ov5 CAVE_RUL_GYROWS), not a 0x0228DDF8 row.
    ("donor_cid", 0x10E6, "sekkas_light"),
    ("cls2_table", 0x1B47, "sekkas_light"),
    # Fire Formation - Tenki on Marshmallon Glasses 0x1777 (fire_formation_tenki,
    # SHIPPED; notes/fire-formation-tenki-findings.md). C1 cls0 {RES, 0, COND, COST, 0} over phantom 0x1765 (stock AND
    # chain, no card_prop, unclaimed). Its Deck row is VIRTUAL (cave3 CAVE3_TENKI_H2 + ov5 CAVE_TENKI_ROW). Phantom
    # 0x0E2C: its S/T-stat-switch arm leaf hosts C2 and Marshmallon's attack-target literal 0x021A6644 now names it.
    ("donor_cid", 0x1777, "fire_formation_tenki"),
    ("cls0", 0x1765, "fire_formation_tenki"),
    ("stat_switch_arm", 0x0E2C, "fire_formation_tenki"),
    # Sacred Sword of Seven Stars on Block Attack 0x130A (sacred_sword_seven_stars;
    # notes/sacred-sword-of-seven-stars-findings.md). Block Attack's OWN cls0 record is rewritten in place (no
    # phantom). Its criteria row is VIRTUAL (cave3 CAVE3_SSS_H2 ahead of Tenki's front + ov5 CAVE_SSS_ROW, k = 31).
    ("donor_cid", 0x130A, "sacred_sword_seven_stars"),
    # Infernoble Knight Ogier on Robotic Knight 0x13A3 (infernoble
    # notes/infernoble-ogier-findings.md). Phantoms present in the stock AND chain tables, no card name, unclaimed in
    # their pool (scratch/infernoble/free_phantoms.py + donor_scan). 0x1370 owns TWO cls1 rows; one is
    # dropped. GY offer = gy_vrow_hook's virtual row (ov5 CAVE_GYV_ROWS), not a 0x0228DDF8 row.
    ("donor_cid", 0x13A3, "infernoble"),
    ("cls2_table", 0x1B48, "infernoble"),               # phantom dropped (C3 equip-from-GY record)
    ("cls2_table", 0x13A3, "infernoble"),
    ("ignition_cond_registry", 0x0E86, "infernoble"),   # phantom dropped (C3 ignition row)
    ("ignition_cond_registry", 0x13A3, "infernoble"),
    ("cls1_table", 0x1370, "infernoble"),               # one of its two rows dropped (C2 Armageddon record)
    ("cls1_table", 0x13A3, "infernoble"),
    ("populate_table", 0x0E7E, "infernoble"),           # phantom row 48 dropped (C2 FIRE Warrior Deck row)
    ("populate_table", 0x13A3, "infernoble"),
    # Infernoble Knight Maugis on Wolf Axwielder 0x139A (infernoble
    # notes/infernoble-maugis-findings.md). Phantoms present in stock AND chain, no card name, unclaimed in their pool.
    # ONE cls2 record serves C2 (sent-to-GY trigger) and C3 (GY ignition), switched on desc[+3]/desc[+4].
    ("donor_cid", 0x139A, "infernoble"),
    ("cls2_table", 0x1B49, "infernoble"),               # phantom dropped (C2+C3 record)
    ("cls2_table", 0x139A, "infernoble"),
    ("ignition_cond_registry", 0x0E7D, "infernoble"),   # phantom dropped (C3 ignition row)
    ("ignition_cond_registry", 0x139A, "infernoble"),
    ("populate_table", 0x0E7F, "infernoble"),           # phantom dropped (C2 FIRE Warrior GY+banished row)
    ("populate_table", 0x139A, "infernoble"),
    ("leave_mask_table", 0x0E1D, "infernoble"),         # phantom dropped (C2 sent-to-GY mask 0x0800)
    ("leave_mask_table", 0x139A, "infernoble"),
    ("draw_count_table", 0x0E19, "infernoble"),         # phantom dropped (C2 draw 1)
    ("draw_count_table", 0x139A, "infernoble"),
    # Infernoble Knight Oliver on Tune Warrior 0x1E04 (infernoble
    # notes/infernoble-oliver-findings.md). ONE cls2 record: C2 hand ignition (desc[+3] == 0x0B) + C3 GY equip.
    # hand_effect_list_b = ARM9 LIST B 0x0209BC8C (x0x24), the hand-effect offer list (KB @0x0202354C) -- NOT the
    # speed-2 list 0x0209C118 that "quickeffect_list" claims below/above name; 0x1A86 is a phantom in BOTH lists and
    # Maiden spent it only in 0x0209C118 (maiden_eyes_of_blue.py:338-341).
    ("donor_cid", 0x1E04, "infernoble"),
    ("cls2_table", 0x1B4A, "infernoble"),               # phantom dropped (C2+C3 record)
    ("cls2_table", 0x1E04, "infernoble"),
    ("ignition_cond_registry", 0x0EA9, "infernoble"),   # phantom dropped (C3 ignition row)
    ("ignition_cond_registry", 0x1E04, "infernoble"),
    ("populate_table", 0x0ECA, "infernoble"),           # phantom dropped (C2 hand-cost row, word 0 + callback)
    ("populate_table", 0x1E04, "infernoble"),
    ("hand_effect_list_b", 0x1A86, "infernoble"),       # phantom dropped
    ("hand_effect_list_b", 0x1E04, "infernoble"),
    # Infernoble Knight Turpin on Beaver Warrior 0x0FC1 (infernoble
    # notes/infernoble-turpin-findings.md). ONE cls2 record (hand C2 / GY "Use which effect?" C2 vs C3). Hand offer via a
    # front on Dragon Rulers' ARM9 H4 site (no list slot spent); GY offer via gy_vrow_hook; no criteria/ignition rows.
    ("donor_cid", 0x0FC1, "infernoble"),
    ("cls2_table", 0x1A8A, "infernoble"),               # phantom dropped
    ("cls2_table", 0x0FC1, "infernoble"),
    # Infernoble Knight - Renaud on Water Spirit 0x1E05 (infernoble
    # notes/infernoble-renaud-findings.md). C1 via tg_table's hand-SS registry + ss_commit_hook row (data rows, no
    # list slot); C3 via the new shared c9_trigger_hook (plain-SS list 0x0228F63A is full in the chain).
    ("donor_cid", 0x1E05, "infernoble"),
    ("cls1_table", 0x0E5F, "infernoble"),               # phantom dropped (C3 record)
    ("cls1_table", 0x1E05, "infernoble"),
    ("populate_table", 0x0E68, "infernoble"),           # phantom dropped (C3 GY+banished row)
    ("populate_table", 0x1E05, "infernoble"),
    # Infernoble Knight Ricciardetto on Tiger Axe 0x0FE6 (infernoble;
    # notes/infernoble-ricciardetto-findings.md). Two criteria rows (rel 0 hand / rel 1 GY) via a criteria_row_hook arm.
    ("donor_cid", 0x0FE6, "infernoble"),
    ("cls2_table", 0x1B8F, "infernoble"),               # phantom dropped (C1 record)
    ("cls2_table", 0x0FE6, "infernoble"),
    ("cls1_table", 0x0E61, "infernoble"),               # phantom dropped (C2 record)
    ("cls1_table", 0x0FE6, "infernoble"),
    ("populate_table", 0x0E42, "infernoble"),           # phantom dropped (C1 hand row, rel 0)
    ("populate_table", 0x0E4B, "infernoble"),           # phantom dropped (C2 GY row, rel 1)
    ("populate_table", 0x0FE6, "infernoble"),
    # Infernoble Knight - Roland on Killer Needle 0x0FDB (infernoble;
    # notes/infernoble-roland-findings.md). End-Phase row 133 rewritten {0x022540F5, 0x0E8B} -> {0x02254221, 0x0FDB}.
    ("donor_cid", 0x0FDB, "infernoble"),
    ("cls2_table", 0x0E34, "infernoble"),               # phantom dropped (C1 hand / C2 GY record)
    ("cls2_table", 0x0FDB, "infernoble"),
    ("populate_table", 0x0E48, "infernoble"),           # phantom dropped (C2 Deck row)
    ("populate_table", 0x0FDB, "infernoble"),
    ("leave_mask_table", 0x0E66, "infernoble"),         # phantom dropped (sent-to-GY mask 0x0800)
    ("leave_mask_table", 0x0FDB, "infernoble"),
    ("equip_grant_table", 0x15D1, "infernoble"),        # phantom dropped (+500/+500 row 0x0226DFB0)
    ("equip_grant_table", 0x0FDB, "infernoble"),        # {0x0FDB, +500, 0}
    ("registry_row", 0x0E8B, "infernoble"),             # End-Phase row 133 -> {0x02254221, 0x0FDB}
    # Infernoble Knight Astolfo on Griffore 0x0FD4 (infernoble;
    # notes/infernoble-astolfo-findings.md). Standby row 294 rewritten {0x022573DD, 0x1775} -> {0x02257739, 0x0FD4}.
    ("donor_cid", 0x0FD4, "infernoble"),
    ("cls2_table", 0x0E3A, "infernoble"),               # phantom dropped (C1 hand / C2 GY / C2 banished record)
    ("cls2_table", 0x0FD4, "infernoble"),
    ("populate_table", 0x0E49, "infernoble"),           # phantom dropped (cost pick + C2 follow-up pick)
    ("populate_table", 0x0FD4, "infernoble"),
    ("registry_row", 0x1775, "infernoble"),             # Standby row 294 -> Drill Warrior's walker for 0x0FD4
    # Courageous Crimson Chevalier Bradamante on Sonic Duck 0x160B (infernoble;
    # notes/infernoble-bradamante-findings.md).
    ("donor_cid", 0x160B, "infernoble"),
    ("cls2_table", 0x0E3E, "infernoble"),               # phantom dropped (C1 hand / C2 GY record)
    ("cls2_table", 0x160B, "infernoble"),
    ("populate_table", 0x1529, "infernoble"),           # phantom dropped (C1 Deck Equip Spell row)
    ("populate_table", 0x160B, "infernoble"),
    ("list106", 0x1B18, "infernoble"),                  # phantom dropped (C2 battle-destroyed-to-GY trigger)
    ("list106", 0x160B, "infernoble"),
    # Infernoble Knight Captain Roland on Thousand Dragon 0x0FEB (infernoble
    # notes/infernoble-captain-roland-findings.md). End-Phase row 99 cid 0x0EC3 -> 0x0FEB (rider thunk 0x0225432D kept).
    ("donor_cid", 0x0FEB, "infernoble"),
    ("cls1_table", 0x0E65, "infernoble"),               # phantom dropped (C1 Synchro trigger)
    ("cls1_table", 0x0FEB, "infernoble"),
    ("cls2_table", 0x0E41, "infernoble"),               # phantom dropped (C1 End-Phase action)
    ("cls2_table", 0x0FEB, "infernoble"),
    ("populate_table", 0x0E6C, "infernoble"),           # phantom dropped (C1 Deck rows)
    ("populate_table", 0x0FEB, "infernoble"),
    ("registry_row", 0x0EC3, "infernoble"),             # End-Phase row 99 -> 0x0FEB
    ("equip_grant_table", 0x0E6D, "infernoble"),        # phantom dropped (-500/-500 row)
    ("equip_grant_table", 0x0FEB, "infernoble"),        # {0x0FEB, +500, 0} (C2)
    # Infernoble Knight Captain Oliver on Labyrinth Tank 0x1118 (infernoble
    # notes/infernoble-captain-oliver-findings.md).
    ("donor_cid", 0x1118, "infernoble"),
    ("cls1_table", 0x0E6D, "infernoble"),               # phantom dropped (C1 attack-declared trigger)
    ("cls1_table", 0x1118, "infernoble"),
    ("cls2_table", 0x0E4A, "infernoble"),               # phantom dropped (C2 GY)
    ("cls2_table", 0x1118, "infernoble"),
    ("attack_declare_list", 0x0E11, "infernoble"),      # list 0x0226E740 x0x11, phantom dropped
    ("attack_declare_list", 0x1118, "infernoble"),
    # Infernoble Knight Emperor Charles on Master of Oz 0x17EF (infernoble
    # notes/infernoble-emperor-charles-findings.md).  End-Phase row 198 cid 0x1337 -> 0x17EF.
    ("donor_cid", 0x17EF, "infernoble"),
    ("cls1_table", 0x1337, "infernoble"),               # phantom dropped (C1 equip + C2 End Phase)
    ("cls1_table", 0x17EF, "infernoble"),
    ("populate_table", 0x0E9C, "infernoble"),           # phantom dropped (C2 hand/GY/Deck rows)
    ("populate_table", 0x17EF, "infernoble"),
    ("registry_row", 0x1337, "infernoble"),             # End-Phase row 198 -> {0x02253F89, 0x17EF}
    # Angelica, Princess of Noble Arms on Rabid Horseman 0x1002 (re-donored from Barox) (infernoble
    # notes/infernoble-angelica-findings.md).  End-Phase row 152 {0x02253EC9, 0x0EA0} -> {0x022546FD, 0x1002};
    # attack-target cid tree pool literal 0x021C68C0 0x0E65 -> 0x1002 (execution-proven).
    ("donor_cid", 0x1002, "infernoble"),
    ("cls1_table", 0x0EA0, "infernoble"),               # phantom dropped (C1 SS + C2 attack target)
    ("cls1_table", 0x1002, "infernoble"),
    ("cls3_table", 0x0E51, "infernoble"),               # phantom dropped (C2 targeted by an activation)
    ("cls3_table", 0x1002, "infernoble"),
    ("cls2_table", 0x0E67, "infernoble"),               # phantom dropped (End-Phase return)
    ("cls2_table", 0x1002, "infernoble"),
    ("populate_table", 0x16C1, "infernoble"),           # phantom dropped (search / FIRE Warrior / Roland pools)
    ("populate_table", 0x1002, "infernoble"),
    ("registry_row", 0x0EA0, "infernoble"),             # End-Phase row 152 -> {0x022546FD, 0x1002}
    ("attack_target_tree", 0x0E65, "infernoble"),       # pool literal 0x021C68C0 re-keyed
    ("attack_target_tree", 0x1002, "infernoble"),
    # Horn of Olifant on Simultaneous Loss 0x1976 (infernoble
    # notes/infernoble-horn-of-olifant-findings.md).  cls0 record re-pointed in place; negate lists 0x0228F708 /
    # 0x0226FAB4 joined virtually (NEXT-style prechecks), no phantom.
    ("donor_cid", 0x1976, "infernoble"),
    ("populate_table", 0x1748, "infernoble"),           # phantom dropped (A / destroy / Roland / Deck pools)
    ("populate_table", 0x1976, "infernoble"),
    # Infernoble Arms - Joyeuse on Demotion 0x15E3 (infernoble
    # notes/infernoble-arms-findings.md).  Level-recompute cid slots 0x021B845C / 0x021B8464 -> 0x1601.
    ("donor_cid", 0x15E3, "infernoble"),
    ("cls3_table", 0x0E56, "infernoble"),               # phantom dropped (E1)
    ("cls3_table", 0x15E3, "infernoble"),
    ("cls2_table", 0x0E69, "infernoble"),               # phantom dropped (E2 leave trigger)
    ("cls2_table", 0x15E3, "infernoble"),
    ("populate_table", 0x1534, "infernoble"),           # phantom dropped (rel 0 hand)
    ("populate_table", 0x167D, "infernoble"),           # phantom dropped (rel 1 GY)
    ("populate_table", 0x15E3, "infernoble"),
    # Infernoble Arms - Durendal on Rod of the Mind's Eye 0x1663 (infernoble
    # Rod's per-cid code retired: battle-damage stack slot 0x02199C44 -> 0x1677.
    ("donor_cid", 0x1663, "infernoble"),
    ("cls3_table", 0x0E5E, "infernoble"),               # phantom dropped (E1)
    ("cls3_table", 0x1663, "infernoble"),
    ("cls2_table", 0x0E6B, "infernoble"),               # phantom dropped (E2 leave trigger)
    ("cls2_table", 0x1663, "infernoble"),
    ("populate_table", 0x0E66, "infernoble"),           # phantom dropped (rel 0 Deck)
    ("populate_table", 0x14DD, "infernoble"),           # phantom dropped (rel 1 GY)
    ("populate_table", 0x1663, "infernoble"),
    # Infernoble Arms - Almace on Broken Bamboo Sword 0x1C39 (infernoble
    # Bamboo's per-cid code retired: stack cid slot 0x021C42A6 -> 0x1CEA.
    ("donor_cid", 0x1C39, "infernoble"),
    ("cls3_table", 0x0E62, "infernoble"),               # phantom dropped (E1)
    ("cls3_table", 0x1C39, "infernoble"),
    ("cls2_table", 0x0E49, "infernoble"),               # phantom dropped (E2 leave trigger)
    ("cls2_table", 0x1C39, "infernoble"),
    ("populate_table", 0x19C0, "infernoble"),           # phantom dropped (modes 0 / 1 / 2)
    ("populate_table", 0x1C39, "infernoble"),
    # Infernoble Arms - Hauteclere on Psychic Sword 0x1F71 (infernoble
    ("donor_cid", 0x1F71, "infernoble"),
    ("cls3_table", 0x0E70, "infernoble"),               # phantom dropped (E1)
    ("cls3_table", 0x1F71, "infernoble"),
    ("cls2_table", 0x0E4B, "infernoble"),               # phantom dropped (E2 leave trigger)
    ("cls2_table", 0x1F71, "infernoble"),
    # Noble Arms Museum on Molten Destruction 0x1346 (infernoble
    ("donor_cid", 0x1346, "infernoble"),
    ("cls3_table", 0x14B8, "infernoble"),               # phantom dropped (C2/C3)
    ("cls3_table", 0x1346, "infernoble"),
    # The Continuing Epic of Charles on Big Burn 0x16DB (infernoble
    ("donor_cid", 0x16DB, "infernoble"),
    ("cls2_table", 0x0E63, "infernoble"),               # phantom dropped (E2, GY)
    ("cls2_table", 0x16DB, "infernoble"),
    # Disguise, the Copycat Hero on Monster Tamer 0x111E + Cursed Copycat Noble Arms on Cyber Shield 0x10E3
    # (disguise_copycat; single-card TEST ROM, not shipped)
    ("donor_cid", 0x111E, "disguise_copycat"),
    ("donor_cid", 0x10E3, "disguise_copycat"),
    ("cls3_table", 0x0E88, "disguise_copycat"),         # phantom dropped (Disguise C3 ignition)
    ("cls2_table", 0x1B19, "disguise_copycat"),         # phantom dropped (Disguise C1 hand SS) -- the LAST cls2 phantom
    ("cls1_table", 0x0E9F, "disguise_copycat"),         # phantom dropped (Disguise C2 NS/SS search)
    ("cls3_table", 0x14C5, "disguise_copycat"),         # phantom dropped (Noble Arms N2 ignition)
    # Noble Knight Medraut on Armored Lizard 0x0FD9 (noble_knight_medraut; single-card TEST ROM, not shipped)
    ("donor_cid", 0x0FD9, "noble_knight_medraut"),
    ("cls3_table", 0x0E73, "noble_knight_medraut"),     # phantom dropped (Medraut ignition)
    # Immortal Phoenix Gearfried on Judge Man 0x0FC7 (immortal_phoenix_gearfried; single-card TEST ROM, not shipped).
    # C1 hand cls2 record is VIRTUAL (find_event_handler front) and its criteria row is VIRTUAL (index 0xFF20): no cls2 / criteria phantom spent.
    ("donor_cid", 0x0FC7, "immortal_phoenix_gearfried"),
    ("cls1_table", 0x0E39, "immortal_phoenix_gearfried"),     # phantom dropped (C2 Damage-Step equip trigger)
    ("cls1_table", 0x17EA, "phoenix_gearblade"),              # phantom dropped (C3 End-of-Damage-Step trigger); sole ov3/ARM9 hit = its cls1 row
    ("cls2_table", 0x14E7, "phoenix_gearblade"),              # phantom dropped (C4 'add this card to your hand'); other hits are populate / criteria / list106 rows of the same dead cid
    ("cls3_table", 0x0E47, "immortal_phoenix_gearfried"),     # phantom dropped (C3 quick negate)
    ("quickeffect_list", 0x0EB2, "immortal_phoenix_gearfried"),   # ARM9 spell-speed-2 list 0x0209C118: phantom dropped for the donor
    ("ds_negator_list", 0x0E5B, "immortal_phoenix_gearfried"),    # ov3 Damage-Step offer list 0x0226D8B0: phantom dropped for the donor
    # Return of the Monarchs on Vengeful Bog Spirit 0x14A1 (return_monarchs; single-card TEST ROM, not shipped). cls0 phantom 0x0E2A and cls1 phantom 0x130F: one row each in stock AND chain, no card, unclaimed (checked 2026-11-10).
    ("donor_cid", 0x14A1, "return_monarchs"),
    ("cls0_table", 0x0E2A, "return_monarchs"),
    ("cls1_table", 0x130F, "return_monarchs"),
    # Tenacity of the Monarchs on De-Spell 0x12EB (tenacity; single-card TEST ROM, not shipped). Set code 0x6D ("Monarch", list repointed to CAVE_TN_MON)
    # and 0x6C (Vision HERO, ATK/DEF reveal list, repointed to CAVE_TN_REV; 0x35 is taken by masked_hero_dark_law): both have no criteria row and no pool reference to the thunk except the pointer-table slot (checked 2026-11-10 on the chain ROM).
    ("donor_cid", 0x12EB, "tenacity"),
    ("setcode_index", 0x6D, "tenacity"),
    ("setcode_index", 0x6C, "tenacity"),
    # Restoration of the Monarchs on Burning Spear 0x12EE (restoration; single-card TEST ROM, not shipped). cls0 phantom 0x0E2B; set code 0x6C is shared with tenacity (same list).
    ("donor_cid", 0x12EE, "restoration"),
    ("cls0_table", 0x0E2B, "restoration"),
    # The Monarchs Awaken on Disarmament 0x1633 (monarchs_awaken; single-card TEST ROM, not shipped): cls0 rewritten in place, no phantom.
    ("donor_cid", 0x1633, "monarchs_awaken"),
    # Pantheism of the Monarchs on Des Croaking 0x1923 (pantheism; test ROM, not shipped): cls0 rewritten in place, no phantom; "Monarch" set code 0x6D list shared with tenacity.
    ("donor_cid", 0x1923, "pantheism"),
    # Frost Blast of the Monarchs on Double Snare 0x14C3 (frost_blast; test ROM, not shipped): cls0 rewritten in place, cls2 phantom 0x0EBE dropped (C2 GY ignition).
    ("donor_cid", 0x14C3, "frost_blast"),
    ("cls2_table", 0x0EBE, "frost_blast"),
    # The Monarchs Revolt on Short Circuit 0x1DCD (revolt; test ROM, not shipped): cls0 rewritten in place, cls2 phantom 0x16F5 dropped (C4 GY ignition).
    ("donor_cid", 0x1DCD, "revolt"),
    ("cls2_table", 0x16F5, "revolt"),
    # Edea the Heavenly Squire on Gokibore 0x0FDC (edea; test ROM, not shipped): cls1 phantom 0x0E8A (N-or-SS trigger), cls2 phantom 0x0E64 (sent-to-GY target), leave phantom 0x0E2D.
    ("donor_cid", 0x0FDC, "edea"),
    ("cls1_table", 0x0E8A, "edea"),
    ("cls2_table", 0x0E64, "edea"),
    ("leave_mask_table", 0x0E2D, "edea"),
    # Eidos the Underworld Squire on Great White 0x0FE2 (eidos_squire; test ROM, not shipped): cls1 phantom 0x0E8F (N-or-SS trigger), cls2 phantom 0x0E12 (GY ignition).
    ("donor_cid", 0x0FE2, "eidos_squire"),
    ("cls1_table", 0x0E8F, "eidos_squire"),
    ("cls2_table", 0x0E12, "eidos_squire"),
    # Tessera the Primal Squire on Toon Alligator 0x1123 (tessera; test ROM, not shipped; T1 hand ignition NOT built): cls3 phantom 0x0E20 (T2), cls2 phantom 0x0EC9 + leave phantom 0x0E4B (T3).
    ("donor_cid", 0x1123, "tessera"),
    ("cls3_table", 0x0E20, "tessera"),
    ("cls2_table", 0x0EC9, "tessera"),
    ("leave_mask_table", 0x0E4B, "tessera"),
    # Eidos the Underworld Monarch on Whiptail Crow 0x1230 (eidos_monarch; test ROM; E1 deck half only): cls1 phantom 0x0EA7.
    ("donor_cid", 0x1230, "eidos_monarch"),
    ("cls1_table", 0x0EA7, "eidos_monarch"),
    # Erebus the Underworld Monarch on Man-Eating Treasure Chest 0x1313 (erebus; test ROM, E1 partly): cls1 phantom 0x0EB1.
    ("donor_cid", 0x1313, "erebus"),
    ("cls1_table", 0x0EB1, "erebus"),
    # Ehther the Heavenly Monarch on Baron of the Fiend Sword 0x1312 (erebus.py): cls1 phantom 0x0EB8, End-Phase registry row 144 (phantom cid 0x11CF) -> return-to-hand body.
    ("donor_cid", 0x1312, "ehther"),
    # Escalation of the Monarchs on Enervating Mist 0x1800 (escalation; test ROM): cls0 phantom 0x0E71, cls3 phantom 0x152C.
    ("donor_cid", 0x1800, "escalation"),
    # The Prime Monarch on The A. Forces 0x14CF (erebus.py; test ROM): cls0 phantom 0x0E72, cls3 phantom 0x152D.
    ("donor_cid", 0x14CF, "prime_monarch"),
    # The First Monarch on Tiki Soul 0x249B (first_monarch.py; test ROM): a native Trap Monster donor, no table rows; its 3 effect-arm literals go to the dead phantom 0x1449.
    ("donor_cid", 0x249B, "first_monarch"),
    ("cls1_table", 0x0EC5, "first_monarch"),
    ("cls0_table", 0x0E72, "prime_monarch"),
    ("cls3_table", 0x152D, "prime_monarch"),
    ("cls0_table", 0x0E71, "escalation"),
    ("cls3_table", 0x152C, "escalation"),
    ("cls1_table", 0x0EB8, "ehther"),
    ("registry_row", 0x11CF, "ehther"),
    # Monarchic Perfection on Call of the Grave 0x12F6 (erebus.py + c/perfection.c; test ROM 2026-11-12): its own cls0 record rewritten in place, cls1 trigger over phantom 0x0EC4.
    ("donor_cid", 0x12F6, "monarchic_perfection"),
    ("cls1_table", 0x0EC4, "monarchic_perfection"),
    # The Monarchs Masterplan on Speed Spell - Faustian Bargain 0x0D6A (masterplan; test ROM, clause 1 only): cls0 phantom 0x0E30.
    ("donor_cid", 0x0D6A, "masterplan"),
    ("cls0_table", 0x0E30, "masterplan"),
    ("cls2_table", 0x0EB9, "pantheism"),               # phantom dropped (C3 Graveyard ignition record; single row)
    # Predaplant Darlingtonia Cobra on Jellyfish 0x0FED + Predaplant Ophrys Scorpio on Skull Dog Marron 0x17CF (predaplant; single-card TEST ROM, not shipped).
    ("donor_cid", 0x0FED, "predaplant"),
    ("donor_cid", 0x17CF, "predaplant"),
    ("predaplant_setcode_table", 0x1433, "predaplant"),    # set code 0x28 list @0x0209C582 (2 entries, both phantoms): phantom dropped for Ophrys
    ("predaplant_setcode_table", 0x1434, "predaplant"),    # ... and for Darlingtonia
    ("cls1_table", 0x0E17, "predaplant"),                  # phantom dropped (Darlingtonia 'You can' search)
    ("cls1_table", 0x0E20, "predaplant"),                  # phantom dropped (Ophrys 'You can' Deck summon)
    # Granmarg the Mega Monarch on Big Insect 0x0FD7 (mega_monarch; single-card TEST ROM, not shipped). cls1 phantom 0x0E21: one row in stock AND chain, no card, unclaimed (checked 2026-11-10).
    ("donor_cid", 0x0FD7, "mega_monarch"),
    ("cls1_table", 0x0E21, "mega_monarch"),                # phantom dropped (E1 Tribute-Summon trigger record)
    # Mobius the Mega Monarch on Grappler 0x0FF3 (mega_monarch; test ROM). cls1 phantom 0x0E3D: one row stock+chain, no card, unclaimed in cls1 (checked 2026-11-10).
    ("donor_cid", 0x0FF3, "mega_monarch"),
    ("cls1_table", 0x0E3D, "mega_monarch"),
    # Zaborg the Mega Monarch on The Illusory Gentleman 0x139B (mega_monarch; test ROM). cls1 phantom 0x0E41: one row stock+chain, no card, unclaimed in cls1 (checked 2026-11-10).
    ("donor_cid", 0x139B, "mega_monarch"),
    ("cls1_table", 0x0E41, "mega_monarch"),
    # Raiza the Mega Monarch on Mist Valley Watcher 0x1E87 (mega_monarch; test ROM). cls1 phantom 0x0E48 (checked 2026-11-10).
    ("donor_cid", 0x1E87, "mega_monarch"),
    ("cls1_table", 0x0E48, "mega_monarch"),
    # Caius the Mega Monarch on Koumori Dragon 0x0FC5 (mega_monarch; test ROM). cls1 phantom 0x0E74 (checked 2026-11-10).
    ("donor_cid", 0x14D8, "mega_monarch"),               # Angmarl the Fiendish Monarch on The Dragon Dwelling in the Cave (a non-Mega Monarch in the same module)
    ("cls1_table", 0x0E7E, "mega_monarch"),              # phantom dropped (Angmarl trigger record)
    ("donor_cid", 0x127B, "mega_monarch"),               # Thestalos the Mega Monarch on Red Archery Girl
    ("cls1_table", 0x0E77, "mega_monarch"),              # phantom dropped (Thestalos E1 trigger record; single row stock+chain)
    ("donor_cid", 0x0FC5, "mega_monarch"),
    ("cls1_table", 0x0E74, "mega_monarch"),
    # March of the Monarchs on Kishido Spirit 0x15EC (march; single-card TEST ROM; Spell Absorption 0x15FE was dropped 2026-11-10: it is in ROM deck wcs075_bigbang, so renaming it aborts the deck preflight). cls0 phantom 0x0E1E: one row stock+chain, no card, unclaimed in cls0 (checked 2026-11-10).
    ("donor_cid", 0x15EC, "march"),
    ("cls0_table", 0x0E1E, "march"),
    # The Monarchs Erupt on Respect Play 0x135E (erupt; single-card TEST ROM). cls0 phantom 0x0E3B: free per scratch/_phantoms_all.py on rom_chain_18C00 (2026-11-11).
    ("donor_cid", 0x135E, "erupt"),
    ("cls0_table", 0x0E3B, "erupt"),
    # Strike of the Monarchs on Speed Spell - Offerings to the Doomed 0x0DE4 (strike; test ROM). cls0 phantom 0x0E6F: free per scratch/_phantoms_all.py (2026-11-11).
    ("donor_cid", 0x0DE4, "strike"),
    ("cls0_table", 0x0E6F, "strike"),
    # Domain of the True Monarchs on Sogen 0x10F3 (domain; test ROM). cls3 phantom 0x14DC: free per scratch/_phantoms_all.py (2026-11-11).
    ("donor_cid", 0x10F3, "domain"),
    ("cls3_table", 0x14DC, "domain"),
    # The Monarchs Stormforth on Tailor of the Fickle 0x1328 (stormforth; single-card TEST ROM). Rewrites the donor's own cls0 record in place (dsl.Edit): no phantom.
    ("donor_cid", 0x1328, "stormforth"),
    # Coral Dragon on B. Skull Dragon 0x107F (coral_dragon; whole card, shipped 2026-11-09). Each phantom is free IN ITS OWN table (checked 2026-11-09
    # against PHANTOM_CLAIMS + the stock ov3 rows): cls2 0x1B46 (0x234D was already spent in the CHAIN image by tg_warwolf), draw-count 0x1AE9, leave-mask 0x194A. Archfiend list idx 3 gets a sorted dup of its neighbour phantom 0x10AB (not a spent phantom).
    ("donor_cid", 0x107F, "coral_dragon"),
    ("cls2_table", 0x1B46, "coral_dragon"),
    ("draw_count_table", 0x1AE9, "coral_dragon"),
    ("leave_mask_table", 0x194A, "coral_dragon"),
    ("cls3_table", 0x1BCE, "coral_dragon"),                # C1 ignition record (phantom free in cls3, checked 2026-11-09)
    # criteria rows are VIRTUAL (indices 0xFF30..0xFF32 in CAVE_PD_ROWS via H2/H3 fronts): no criteria phantom spent (the 4 spare ones are second copies of phantoms tg_striker / tg_warwolf / sea_lancer / ninjitsu already count on).
]


# ---------------------------------------------------------------------------
# OVERLAY-3 DEAD-CODE POOL (stat.phantom_arm_scratch).
#
# The continuous stat engine 0x021B44C0 has 182 `cmp r2,<cid>` arms, and 16 of
# them name cids that do not exist in the ROM's card_prop (4305 records), so
# their leaves can never execute. That makes them free ov3 code space -- and
# unlike the ov5 cave, ov3 is resident in EVERY duel mode including puzzles
# (mem.ov3_resident_all_modes), with no overlay resize and no canary needed.
#
# SUPPLY: (leaf address, contiguous free bytes, the phantom cid whose arm guards
# it). Extents stop at the first branch target or literal-pool word, measured by
# a CFG walk over the function -- do NOT widen one without re-measuring.
# ⚠️ Only the leaf BODY is free. A phantom arm's SLOT cannot be re-keyed: each
# sits at a fixed point of a sorted binary chain, so giving it an out-of-interval
# cid mis-routes every card in that interval.
# ---------------------------------------------------------------------------
OV3_DEAD_BLOCKS: list[tuple[int, int, int]] = [
    (0x021B54E0, 44, 0x0EC1),
    (0x021B582A, 30, 0x1827),
    (0x021B58E6, 30, 0x194C),
    (0x021B591E, 28, 0x19BE),
    (0x021B57EE, 22, 0x1789),
    (0x021B56B8, 16, 0x133D),
    (0x021B58D0, 12, 0x190F),
    (0x021B5AAA, 10, 0x1BCF),
    # 0x1AC7 (no card_prop) cls1[598]'s resolver 0x02223450 + its pool, up to the next function 0x02223504.
    # No bl/b/ldr-literal from ARM9/ov3/ov5 lands inside (scan); its only pointer was the cls1
    # record, which masked_hero_dark_law drops. DEAD ONLY WITH THAT RECORD GONE.
    (0x02223450, 180, 0x1AC7),
    # Abyssal Designator 0x17F4's native selector (cls0[554] +14) 0x02237D8C..0x02237E53, up to the next fn
    # 0x02237E54 (ptr @0x02281C00). Its ONLY reference was cls0[554] (ptr @0x02281A50; no bl, no ARM9 ptr, no
    # external b/bcc lands inside; scan). DEAD ONLY WITH obedience_schooled's cls0 rewrite.
    (0x02237D8C, 200, 0x17F4),
    # Return Soul 0x1B22's native cond 0x021FBC94 (cls0[779] +0C, 0x18 B) and criteria handler 0x0223F8E4 (row 489,
    # 0x20 B): each one's ONLY reference is that slot; no bl, no other u32, no b/bcc lands inside, both preceded by
    # `pop {..pc}` (scan). DEAD ONLY WITH next_card's cls0/criteria rewrite.
    (0x021FBC94, 0x18, 0x1B22),
    (0x0223F8E4, 0x20, 0x1B22),
    (0x021B594A, 8, 0x19D1),
    (0x021B5952, 8, 0x19D3),
    # ⚠️ A SECOND, LARGER SUPPLY -- NOT from the stat engine. Two adjacent leaves of
    # the HAND-SS DISPATCH (0x0225F240..0x0225F26C, 46 B, reached only from the dead
    # arm 0x0225E88E / phantom 0x164C; and 0x0225F26E..0x0225F2BC, 80 B, reached only
    # from the dead arm 0x0225E692 / phantom 0x0E3F) form ONE 126-BYTE CONTIGUOUS
    # RUN -- by far the largest always-resident block known, and the only one big
    # enough for a multi-stub payload.
    #
    # Proved dead by three scans over the ARM9 **and all 50 overlays**:
    # BL/BLX into the range = exactly the two dead arms above and nothing else;
    # inbound B/Bcond from outside = 0; pointer words (raw or Thumb-bit) = 0.
    # ⚠️ THE TWO ARMS MUST BE NEUTRALISED by whoever claims this block (point them
    # at the reject leaf 0x0225FF96) -- lightpulsar does exactly that. Until
    # they are, a phantom cid in hand would jump into whatever code lives here.
    # ⚠️ The literal pool at 0x0225F510+ is SHARED with live code -- the dead range
    # loaded from it. Never touch the pool; stubs must carry their own literals.
    # Unlike the ov3_cave.py BSS windows (canary-dead: the engine clears ov3 BSS
    # over its ORIGINAL extent), this is part of ov3's FILE IMAGE, so it survives.
    (0x0225F240, 126, 0x164C),
    # phantom cls3 0x0E46's private cond (dead once ultimate_conductor_tyranno J drops 0x0E46; its only
    # reference was that record -- no BL / pointer in stock, the chain or the Tyranno ROM).
    (0x021F065C, 64, 0x0E46),
    # ⚠️⚠️ NOT NATIVELY DEAD -- dead only BECAUSE gates_of_dark_world is
    # applied. This is the tail of Colosseum 0x1C8B's field-spell arm
    # (0x021B2A3E..0x021B2A69, 44 B): clause 1 PART A overwrites the first 14 B
    # with the Fiend +300/+300 block, which ends in `b PLUS300_TAIL`, so the
    # remaining 30 B become unreachable. The third field is the DONOR cid, not a
    # phantom -- in a build WITHOUT this patch these bytes are live engine code.
    # All 30 B are claimed by gates_of_dark_world below precisely so no other
    # patch can be handed the remainder and then break if this card is dropped
    # from the chain.
    (0x021B2A4C, 30, 0x1C8B),
    # Phantom 0x2348's FIELD-SPELL arm 0x021B2B10..0x021B2B33 (field.arm_map): 0x2348 has no card_prop
    # record, so the field-spell engine can never dispatch to it. NATIVELY dead (no patch dependency).
    (0x021B2B10, 36, 0x2348),
    # Phantom 0x0E82's arm leaf 0x022212E4..0x0222133F in cls3 resolver 0x02221298: entered only through
    # the arm `ldrh r3,[r5] ; cmp r3,=0x0E82 ; bne` @0x022212E2 (no other branch/BL/pointer/pool word lands inside;
    # 0x0E82 has no card_prop in stock or chain). seal_of_orichalcos also seals that arm (bne -> b).
    (0x022212E4, 92, 0x0E82),
    # Phantom 0x1433's arm leaf 0x021BB288..0x021BB2C7: entered only by falling through
    # `ldr r0,=0x1433; cmp r4,r0; bne 0x021BB2C8` @0x021BB282..86 (scratch/ov3_leaf_check.py:
    # no inbound branch/BL/pointer word in stock or chain; 0x1433 has no card_prop). wattuna seals
    # that arm (bne -> b).  ⚠️ 0x02228F4A (0x0E8F) is NOT dead: Arcana Force VII 0x1DA2 falls through into it.
    (0x021BB288, 64, 0x1433),
    # Phantom 0x0EAB's cls0[86] resolver body 0x0220A158..0x0220A1BF: its ONLY reference is that record's +04
    # literal (stock 0x0227EE60 / chain 0x0227EE48); no BL/B/Bcc in ov3 targets the range; preceded by a
    # literal pool (no fall-through). scratchpad dead_fn_scan.py, both ROMs.
    (0x0220A158, 104, 0x0EAB),
    # Phantom 0x0E2C's arm leaf 0x021B32E4..0x021B32FF in the S/T-card stat switch (fn 0x021B2B7C): entered only by
    # `beq` @0x021B3274 (scan of ov3: no other branch/BL lands inside); preceded by `b 0x021B355E`, ends in
    # `b 0x021B333C` (no fall-through either way); 0x0E2C has no card_prop. fire_formation_tenki seals the beq.
    (0x021B32E4, 28, 0x0E2C),
]

# DEMAND: (address, bytes used, owner). Must lie inside a declared dead block.
OV3_CLAIMS: list[tuple[int, int, str]] = [
    # Ninjitsu Art of Super-Transformation clause 4 PART H: the leave-cleanup
    # DESTINATION stub. Reached from the 4-byte BL that replaces the default
    # `movs r0,#0x0E ; str r0,[sp,#0xA8]` at 0x021CB48C, and writes 0x0F
    # (banished) for cid 0x1255 and 0x0E (Graveyard) for every other member of
    # the 40-entry leave list. 20 B of the 22 B still free in this block.
    # ⚠️ IT IS IN OV3, NOT THE OV5 CAVE, ON PURPOSE: 0x021CB48C is a SHARED site
    # that all 40 leave-list cards run through, and a puzzle loads overlay 41
    # over overlay 5, so a bl into ov5 here would freeze Premature Burial, Call
    # of the Haunted and friends in every puzzle.
    (0x0225F2A8, 20, "ninjitsu_art_super_transformation"),
    # Escuridao clause 3: "gains 100 ATK for each E-HERO monster in your GY".
    # 28 B = the cid test + Goka's x100 leaf + a 2-word literal pool.
    (0x021B54E0, 28, "escuridao"),
    # Battle speed multiplier PART B: the 16-byte ARM throttle stub that gates the
    # frame body's `bl 0x02159F1C` to sub-pass 0. Takes the last 16 B of the
    # escuridao block (0x021B54FC..0x021B550C) with ZERO slack -- it is the only
    # 16-byte contiguous hole in the whole ov3 dead pool, and it has to be ov3 and
    # not ov5 because the duel per-frame tick runs in puzzles too.
    (0x021B54FC, 16, "battle_speed"),
    # The Gates of Dark World clause 2 PART I: the L2-membership stub, reached
    # from the retargeted `bl 0x02022E14` @0x02234E96 (the param provider's L2
    # lookup, and nothing else). Reports "found" for the donor so 0x02234E78
    # returns 1 << 28, which is what makes slot4 read criteria ROW 1 (the GY row)
    # while slot5's own `movs r2,#0` keeps it on ROW 0 (the hand row).
    # 28 B used of the 30 B block; all 30 are claimed -- see the block comment.
    (0x021B2A4C, 30, "gates_of_dark_world"),
    # Shien's Dojo clause 1: the arm stub reached from the retargeted third
    # Bushido arm call (BL @0x02266BDC). Performs the displaced
    # 0x02244418(0x247E) then 0x02244418(0x19B2). 20 B = 5 insns + 1 pool word,
    # based at 0x021B582C (2 B into the block: the assembler needs a 4-aligned
    # base for its literal pool), so 22 B of the 30 B block are consumed.
    (0x021B582A, 22, "shiens_dojo"),
    # Shien's Dojo PART E: the type-6 (Bushido) counter CAPACITY stub, reached
    # from the displaced head of the capacity chain at 0x021A2F9E. Gives the donor
    # capacity 0xFF; without it 0x021C7D80 refuses to place any Bushido counter.
    # 24 B based at 0x021B58E8 (2 B in, for the assembler's 4-aligned literal pool).
    (0x021B58E6, 26, "shiens_dojo"),
    # Grapha CLAUSE 2 PART H: the switch-node stub that admits the donor 0x1961 to
    # the Dark World effect-discard arm 0x021D185C, reached from the 4-byte BL that
    # replaces 0x021D14E2 (the stock "subs r1,#0x23 ; cmp r5,r1"). It reproduces it for
    # every other cid -- including Ojamagic 0x1946, whose arm is the fall-through --
    # and long-branches ours. ⚠️ MUST BE ov3, NOT ov5: this is a SHARED path (every
    # effect discard of every card runs it) and a puzzle evicts the ov5 cave.
    # 16 B spanning the TWO ADJACENT 8-byte dead blocks 0x021B594A (phantom 0x19D1)
    # and 0x021B5952 (phantom 0x19D3); both were wholly unclaimed, and their only
    # inbound branches come from those phantoms own dead arms.
    (0x021B594A, 8, "grapha"),
    (0x021B5952, 8, "grapha"),
    # (RELEASED: Eclipse Wyvern's 22 B list30-membership override at
    #  0x021B591E is GONE. Forcing the donor onto list30's path made the effect
    #  fire only on a field->GY leave AND suppressed the leave-mask table, which is
    #  the correct any-location path. Replaced by a pure data row -- see the
    #  leave_mask_table claim in PHANTOM_CLAIMS. Block 0x021B591E is free again.)
    #
    # RE-CLAIMED for a DIFFERENT and now GDB-proven purpose: the
    # sent-to-GY EVENT GATE. "This card is sent to the Graveyard" is not data --
    # 0x021D1300 routes GY-bound cards into a hardcoded per-cid chain at 0x021D1392
    # that admits exactly 16 cids (event.sent_to_gy_cid_switch). Measured: cid
    # 0x19FE -> [sp+0x14]=1 posts, cid 0x1859 -> 0 skips. Exactly one of the 16,
    # 0x16F5, is a phantom -- but its ARM cannot be re-keyed (a sorted binary search
    # never routes 0x1859 there; that first attempt was inert in-game). Instead we
    # hook the TERMINAL NODE of the donor's own interval, 0x021D14D2, displacing
    # `ADD R2,#0x95 ; CMP R5,R2` into this stub. 24 B based at 0x021B5920 (2 B into
    # the block, for a 4-aligned literal pool), so 26 B of the 28 B block are used.
    # ⚠️ ov3, NOT ov5: 0x021D1300 is shared engine code that runs in puzzles too.
    (0x021B591E, 26, "eclipse_wyvern"),
    # Eclipse Wyvern PART I -- clause 2's prerequisite: the BANISH-FROM-GY event gate.
    # ⚠️ This REPLACES PART G, which claimed this same block plus 0x021B56B8 (16 B, now
    # RELEASED). PART G hooked 0x021D1C44, the banish leaf of the relocation
    # applier 0x021D1300 -- and a GY -> banished move PROVABLY never enters it: that
    # transition has its own mover, 0x021C7118, which hardcodes source 0x0E / dest 0x0F
    # and posts by calling the register-prim 0x021D3168 DIRECTLY (event 0x20, zone 0x0F).
    # Measured: PART G's instrumented gate recorded dest 0x0E and never 0x0F across a
    # real GY -> banished move (rom_eclipse_wyvern.ml2 -> .ml3).
    # PART I hooks the gate inside that mover instead: displace
    # `LDR R1,=0x1CF6 ; CMP R0,R1` @0x021C71C8 into a stub returning Z set for Cyber
    # Ouroboros OR the donor, handing the flags to the caller's own BNE @0x021C71CC.
    # 20 B based at 0x021B57F0 (2 B into the block, for a 4-aligned literal pool).
    # ⚠️ ov3, NOT ov5: 0x021C7118 is shared engine code that runs in puzzles too.
    (0x021B57EE, 22, "eclipse_wyvern"),
    # Lightpulsar clause 1, PARTS E/F: the two COST-PAYMENT routing stubs, in the
    # 126 B hand-SS dead run. The summon pipeline dispatches on cid THREE times --
    # legality (0x0225E622, handled by a dead-arm repoint), then "how many cards to
    # select" (root 0x02262962) and the TWO-PASS DRIVER (root 0x02262C24). The last
    # two have no dead arm reachable from the donor's cid, so they get real stubs,
    # hooked at their roots with 4-byte BLs. ⚠️ ov3, NOT ov5: this is the shared
    # summon path and it runs in puzzles.
    # THE SHARED BANISH-COST PAYMENT STUBS (finished_patches/handss_banish_cost.py).
    # 56 B pay-1 (Dark Necrofear + every registered donor -> its arm) + 48 B pay-2
    # (donor -> the two-pass driver, else replay the displaced ldr/cmp and resume).
    # Each payment dispatch has exactly ONE 4-byte BL hook, so these stubs cannot be
    # per-card: they carry the donor REGISTER (0x0FB1 Lightpulsar, 0x1646 Darkflare)
    # and grow ~10 B per additional card. Owner is the shared module, not one patch.
    # ⚠️ ov3, NOT ov5 -- this is a summon path that also runs in puzzles, where ov41
    # evicts ov5 and a BL into the ov5 cave would execute overlay-41 data.
    # (An earlier layout also hosted a 36 B PART L here; clause 2 owns its cost
    #  outright now, so that block is free again -- hence 104 B, not 116 B.)
    (0x0225F240, 104, "handss_banish_cost"),
    # Snoww, Unlight of Dark World clause 1: the "discarded to the GY by a card
    # effect" TRIGGER GATE. That trigger is not data -- it is the hardcoded per-cid
    # chain at 0x021D1392 inside the relocation applier 0x021D1300, whose arm
    # 0x021D185C (source zone == the hand, event 0x1F, relocation kind 0) is reached
    # by exactly seven cids: phantom 0x0EC9 plus Beiige/Broww/Sillva/Goldd/Kahkki/
    # Gren. The donor Renge 0x1C18 is admitted by displacing the terminal node of its
    # own interval (`ADD R0,#0x60 ; CMP R5,R0` @0x021D15EE) into this stub, exactly as
    # eclipse_wyvern does at 0x021D14D2 -- re-keying the phantom 0x0EC9 node
    # CANNOT work, because the chain is a sorted binary search and 0x1C18 > 0x0EC9.
    # 16 B, the whole block, and it needs no literal pool: both cids are reachable
    # from the subtree pivot 0x1B8B that r0 already holds (0x1B8B + 0x8D = the donor,
    # then - 0x2D = Lich Lord 0x1BEB, whose arm 0x021D1902 must keep working).
    # ⚠️ ov3, NOT ov5: 0x021D1300 is shared engine code that runs in puzzles, where
    # overlay 41 evicts ov5.
    (0x021B56B8, 16, "snoww"),
    # Elemental HERO Shadow Mist: NEVER-MISS-THE-TIMING admission. 0x111F's node in the miss-timing
    # test's IF-card cid tree (0x021EE10C, Sinister Sprocket 0x1E1B -- real, kept) is displaced into
    # these two blocks: A replays the Sprocket test and branches to B, which tests 0x111F. ov3 because
    # 0x021EE0E0 runs in puzzles too.
    (0x021B58D0, 10, "shadow_mist"),
    (0x021B5AAA, 10, "shadow_mist"),
    # Masked HERO Dark Law C3: the draw / Deck->hand posters (S_DRAW + S_ADD). ov3 because the draw
    # handler and the Deck->hand mover 0x021C72CC run in puzzles, where ov41 evicts ov5.
    (0x02223450, 0x40, "masked_hero_dark_law"),
    # Elder Entity Norden C1b: the negate-list stub ("0x1127 ? 1 : bsearch"), reached from the
    # retargeted bls @0x02268074 (write list 0x0228F750), @0x021EE418 (reader list 0x0226FAB4) and
    # @0x021CB3BC (leave-cleanup list 0x0226E940, C1c); then C1c's destination stub @0x022234A8,
    # reached from the bl replacing the shared tail `movs r0,#2 ; str r0,[sp,#0xAC]` @0x021CB514.
    (0x02223490, 48, "elder_entity_norden"),
    # Ultimate Conductor Tyranno C1 + C3: PAY1 (dispatch-1 root 0x02262962 -> `bx r1` via literal 0x02262BBC;
    # 0x1265 -> r7=2, Necrofear race arm 0x02262A52) + AT (attack-all lookup: thunk literal 0x021A3FEC and
    # bl @0x021A4252/0x021A58D0/0x021A67AC). ov3 because both are hit by every cid, puzzles included.
    (0x022234C0, 64, "ultimate_conductor_tyranno"),
    # Tyranno C4 fix M: start-of-Damage-Step poster root 0x0224F588 -> stub (0x1265 posts event 0x15).
    (0x021F065C, 36, "ultimate_conductor_tyranno"),
    # Overtex Qoatlus C3 H: the sent-to-GY chain stub, BL'd from Shadow Mist's node 0x021D13CC (tests 0x111F
    # unconditionally, 0x10A5 iff off-field source and cause > 0). Rest of the dead 0x0E46 body. ov3: the chain
    # runs in puzzles too.
    (0x021F0680, 28, "overtex_qoatlus"),
    # Overtex Qoatlus C3 J: never-miss block C (0x10A5), reached by `b` from Shadow Mist's block B 0x021B5AAA
    # (which this card rewrites in place: its `bx lr` -> `b C`). Dead tail of phantom 0x1827's block.
    (0x021B5840, 8, "overtex_qoatlus"),
    # Obedience Schooled C3/C4, in the donor's own dead selector body. bls retargeted:
    # @0x021EE418 (negate reader list 0x0226FAB4) -> NEGR -> Norden's NEG_STUB; @0x02268090 (summon kind-2
    # list 0x0228F708) -> EPL -> Petiteranodon's CAVE_PTER_NOATK; @0x021BA368 (SS gate 0x021BA258's
    # bl 0x021BA1E8) -> LOCK. COST = cls0[554] +10.
    (0x02237D8C, 0x18, "obedience_schooled"),   # NEGR
    (0x02237DA4, 0x18, "obedience_schooled"),   # EPL
    (0x02237DBC, 0x40, "obedience_schooled"),   # LOCK
    (0x02237DFC, 0x20, "obedience_schooled"),   # COST
    # NEXT C2: bl @0x021EE418 (negate reader list 0x0226FAB4) -> NEGR -> previous target;
    # bl @0x02268090 (summon kind-2 poster list 0x0228F708) -> EPL -> previous target.
    (0x021FBC94, 0x18, "next"),   # NEGR
    (0x0223F8E4, 0x18, "next"),   # EPL
    # The Seal of Orichalcos C2 PART C: the 28 B gate stub reached from the BL at 0x021CC264 (default
    # exit of the destroy-survive check 0x021CC028). ov3 on purpose: that exit runs for every card-effect
    # destroy, in puzzles too, so a bl into ov5 there would freeze puzzles.
    (0x021B2B10, 0x1C, "seal_of_orichalcos"),
    # (RELEASED: The Seal's C3 stub used to live at 0x02237E1C, 0x1C B, in obedience_schooled's
    # zero-filled tail; it moved to the ov3 pool slot cave3.CAVE3_SEAL_C3 so the Seal no longer depends on
    # that patch. The 28 B stay zero -- free dead space again.)
    # The Seal of Orichalcos C5 PART F: stub A (SYNCHRO wrapper literal 0x021B9EF8) + stub B (cid-aware SS gate
    # bl @0x021BA35A, location 0x0C = Extra Deck). Shared gates that run in puzzles -> ov3.
    (0x022212E4, 0x44, "seal_of_orichalcos"),
    # Eva PART G: the sent-to-GY chain node 0x021D1436 (Neko Mane King 0x15DB's test) -> this stub, which
    # keeps Neko and long-branches 0x160A to the any-location accept 0x021D199E. The last 18 of the 24 B left
    # in phantom 0x0E82's leaf after the Seal. ov3: 0x021D1300 runs in puzzles too.
    (0x02221328, 18, "eva"),
    # Eva PART J: front stub BL'd from Shadow Mist's miss-timing node 0x021EE10C: 0x160A -> Z (never miss),
    # every other cid -> Shadow Mist's block A. The zero-filled tail of Abyssal Designator's block after the
    # Seal's 0x02237E1C stub; needs obedience_schooled + shadow_mist first.
    (0x02237E38, 20, "eva"),
    # Infernoble Knight - Roland (infernoble): the 28 B The Seal released (its C3 moved to cave3)
    # -> sent-to-GY node 0x021D13C2 front: 0x0FDB -> accept 0x021D1938, else Nikitama's CAVE3_NK_GYNODE.
    (0x02237E1C, 28, "infernoble"),
    # Wattuna PART E2: tail of the hand-material gate 0x022494EC (`ldr r0,[0x0224953C] ; bx r0` @0x02249516):
    # Parallel Gear 0x2353 as stock, 0x1050 only while the forced-material slot 0x0229AC7C != 0 (U4 summon)
    # or the ov5 probe flag CAVE_WU_PROBE != 0 (U4 Extra-Deck offer, E3).
    # ov3: the gate runs for every Synchro material check, puzzles included.
    (0x021BB288, 52, "wattuna"),
    (0x0220A158, 100, "grandsoil"),
    # Fire Formation - Tenki C2: "Beast-Warriors you control +100 ATK" arm, reached from the retargeted `bgt` @0x021B3284.
    (0x021B32E4, 28, "fire_formation_tenki"),          # C5 leave stub (BL from 0x021C8078); 72 -> 80 B (+ Moulinglacia 0x1C1A); -> 92 B (+ Pyrorex 0x181F); -> 100 B (+ Windrose 0x190B)
]


# ---------------------------------------------------------------------------
# Parse ov5_cave.py's CAVE_* constants into slot records.
# ---------------------------------------------------------------------------
_CONST_RE = re.compile(r"^CAVE_(\w+)\s*=\s*(0x[0-9A-Fa-f]+)\s*(?:#(.*))?$")
_SIZE_RE = re.compile(r"\(?\s*(?:==|<=|>=)?\s*(0x[0-9A-Fa-f]+)\s*bytes", re.I)


def _owner_of(name: str) -> str:
    n = name.upper()
    prefixes = {
        "QSR": "shooting_quasar", "TGS": "tg_striker", "TGW": "tg_warwolf",
        "TGR": "tg_rush_rhino", "TG_SS": "tg_shared", "TG_ARM": "tg_shared",
        "TG_REG": "tg_shared", "TG_": "tg_shared", "LIB": "hyper_librarian",
        "TSH": "thunder_sea_horse", "WNM": "w_nebula_meteorite", "WW": "wonder_wand",
        "WATT": "wattcobra", "GK": "gravekeepers_recruiter", "MYSTIC": "mystic_piper", "CARDCAR": "cardcar_d",
        "BOGGART": "boggart_knight", "MINEFIELD": "reborn_tengu",
        "ARMORY": "armory_arm", "SL_": "sea_lancer", "SZ_": "safe_zone",
        "SC_": "soul_charge", "KURIBANDIT": "kuribandit",
        "ASSAULT": "assault_synchron", "SSCOMMIT": "ss_commit_hook",
        "SM_": "shadow_mist", "UCT_": "ultimate_conductor_tyranno",
        "ARCH_": "animadorned_archosaur", "EVA_": "eva", "GS_": "grandsoil",
    }
    for p, owner in prefixes.items():
        if n.startswith(p):
            return owner
    return name.lower()


def parse_ov5_slots() -> list[dict]:
    slots: list[dict] = []
    for line in OV5_CAVE_PY.read_text(encoding="utf-8").splitlines():
        m = _CONST_RE.match(line.strip())
        if not m:
            continue
        name, addr_s, comment = m.group(1), m.group(2), (m.group(3) or "")
        if name in ("FREE",):                       # the free-space sentinel, not a slot
            continue
        addr = int(addr_s, 16)
        if not (OV5_RAM_BASE <= addr < OV5_END):     # geometry consts (OV5_*) etc.
            continue
        sm = _SIZE_RE.search(comment)
        size = int(sm.group(1), 16) if sm else None
        cu = comment.upper()
        flags = []
        if "RETIRED" in cu or "RETIRED" in name.upper():
            flags.append("retired")
        if "LEGACY" in cu:
            flags.append("legacy")
        if "DIAGNOSTIC" in cu:
            flags.append("diagnostic")
        slots.append({
            "name": f"CAVE_{name}", "addr": addr, "size": size,
            "owner": _owner_of(name), "flags": flags,
            "note": comment.strip(),
        })
    slots.sort(key=lambda s: s["addr"])
    return slots


# ---------------------------------------------------------------------------
# Collision checks
# ---------------------------------------------------------------------------
def _live(slot: dict) -> bool:
    """A slot that participates in overlap checks (excludes retired/legacy/diag)."""
    return not (set(slot["flags"]) & {"retired", "legacy", "diagnostic"})


def check_ov5_overlaps(slots: list[dict]) -> list[str]:
    violations = []
    live = [s for s in slots if _live(s) and s["size"]]
    live.sort(key=lambda s: s["addr"])
    for a, b in zip(live, live[1:]):
        a_end = a["addr"] + a["size"]
        if a_end > b["addr"]:
            violations.append(
                f"ov5 overlap: {a['name']} [0x{a['addr']:08X}+0x{a['size']:X}) "
                f"overruns {b['name']} @0x{b['addr']:08X} "
                f"(owners {a['owner']} / {b['owner']})")
    for s in live:
        if s["addr"] + (s["size"] or 0) > OV5_END:
            violations.append(f"ov5 out of region: {s['name']} exceeds 0x{OV5_END:08X}")
    return violations


def check_ov3_claims() -> list[str]:
    """Every ov3 dead-code claim must fit a declared block and not overlap another."""
    violations = []
    for addr, size, owner in OV3_CLAIMS:
        host = next(((b, n, cid) for b, n, cid in OV3_DEAD_BLOCKS
                     if b <= addr and addr + size <= b + n), None)
        if host is None:
            violations.append(
                f"ov3 claim '{owner}' @0x{addr:08X}+{size} is outside every declared "
                f"dead block — it may be live engine code")
    ordered = sorted(OV3_CLAIMS)
    for a, b in zip(ordered, ordered[1:]):
        if a[0] + a[1] > b[0]:
            violations.append(
                f"ov3 overlap: '{a[2]}' @0x{a[0]:08X}+{a[1]} runs into "
                f"'{b[2]}' @0x{b[0]:08X}")
    return violations


# ---------------------------------------------------------------------------
# ov3 COMPACTION POOL (mem.ov3_compaction_pool): step 0 zero-fills pool_blocks.FREE_RUNS;
# slots in it are the CAVE3_* constants of ov3_compaction/cave3.py (same comment format as
# ov5_cave.py). FREE_RUNS is disjoint from OV3_DEAD_BLOCKS (checked below).
# ---------------------------------------------------------------------------
CAVE3_PY = _ROOT / "otn_enhanced" / "effects" / "cave3.py"
_CONST3_RE = re.compile(r"^CAVE3_(\w+)\s*=\s*(0x[0-9A-Fa-f]+)\s*(?:#(.*))?$")


def parse_cave3_slots() -> list[dict]:
    slots = []
    for line in CAVE3_PY.read_text(encoding="utf-8").splitlines():
        m = _CONST3_RE.match(line.strip())
        if m:
            sm = _SIZE_RE.search(m.group(3) or "")
            slots.append({"name": f"CAVE3_{m.group(1)}", "addr": int(m.group(2), 16),
                          "size": int(sm.group(1), 16) if sm else None, "note": (m.group(3) or "").strip()})
    return sorted(slots, key=lambda s: s["addr"])


def check_cave3() -> list[str]:
    from otn_enhanced.effects.pool_blocks import FREE_RUNS
    v = [f"ov3 pool run 0x{s:08X} overlaps dead block 0x{b:08X}"
         for s, e, _ in FREE_RUNS for b, n, _ in OV3_DEAD_BLOCKS if s < b + n and b < e]
    slots = parse_cave3_slots()
    for s in slots:
        if not s["size"]:
            v.append(f"{s['name']} has no `(0xNN bytes)` size in its comment")
        elif not any(a <= s["addr"] and s["addr"] + s["size"] <= e for a, e, _ in FREE_RUNS):
            v.append(f"{s['name']} @0x{s['addr']:08X}+0x{s['size']:X} is outside every freed ov3 run")
    for a, b in zip(slots, slots[1:]):
        if a["addr"] + (a["size"] or 0) > b["addr"]:
            v.append(f"ov3 pool overlap: {a['name']} runs into {b['name']} @0x{b['addr']:08X}")
    return v


def check_phantom_dupes(claims: list[tuple[str, int, str]]) -> list[str]:
    seen: dict[tuple[str, int], str] = {}
    violations = []
    for pool, cid, owner in claims:
        key = (pool, cid)
        if key in seen and seen[key] != owner:
            violations.append(
                f"phantom collision: cid 0x{cid:04X} in pool '{pool}' claimed by "
                f"both '{seen[key]}' and '{owner}'")
        seen[key] = owner
    return violations


# ---------------------------------------------------------------------------
# Ledger emission + drift check
# ---------------------------------------------------------------------------
def emit_ledger() -> None:
    slots = parse_ov5_slots()
    lines = [
        "# allocations.yaml — patch-slot allocation ledger (generated by check_allocations.py --emit).",
        "# The build (apply_all_patches / _build_tg3) runs check_allocations and FAILS on any collision.",
        "# ov5 slots are derived from ov5_cave.py's CAVE_* constants; phantom_cids from PHANTOM_CLAIMS.",
        "",
        "ov5_slots:",
    ]
    for s in slots:
        size = f"0x{s['size']:X}" if s["size"] else "null"
        flags = "[" + ", ".join(s["flags"]) + "]"
        lines.append(f"  - name: {s['name']}")
        lines.append(f"    addr: 0x{s['addr']:08X}")
        lines.append(f"    size: {size}")
        lines.append(f"    owner: {s['owner']}")
        lines.append(f"    flags: {flags}")
    lines.append("")
    lines.append("phantom_cids:")
    for pool, cid, owner in PHANTOM_CLAIMS:
        lines.append(f"  - {{pool: {pool}, cid: 0x{cid:04X}, owner: {owner}}}")
    lines.append("")
    lines.append("# Provably-dead overlay-3 code (stat.phantom_arm_scratch): the leaves of stat-engine")
    lines.append("# arms whose cid is not a card. Resident in every duel mode; no cave, no canary.")
    lines.append("ov3_dead_blocks:")
    claimed = {c[0]: c for c in OV3_CLAIMS}
    for addr, size, cid in OV3_DEAD_BLOCKS:
        used = sum(n for a, n, _ in OV3_CLAIMS if addr <= a < addr + size)
        owners = sorted({o for a, _, o in OV3_CLAIMS if addr <= a < addr + size})
        lines.append(f"  - addr: 0x{addr:08X}")
        lines.append(f"    size: {size}")
        lines.append(f"    phantom_cid: 0x{cid:04X}")
        lines.append(f"    used: {used}")
        lines.append(f"    owners: [{', '.join(owners)}]")
    lines.append("")
    from otn_enhanced.effects.pool_blocks import FREE_RUNS
    cave3 = parse_cave3_slots()
    lines.append("# ov3 compaction pool (step 0 frees pool_blocks.FREE_RUNS); slots = cave3.py CAVE3_*.")
    lines.append(f"ov3_pool: {{runs: {len(FREE_RUNS)}, bytes: {sum(e - s for s, e, _ in FREE_RUNS)}, "
                 f"used: {sum(s['size'] or 0 for s in cave3)}}}")
    lines.append("ov3_pool_slots:")
    for s in cave3:
        lines.append(f"  - {{name: {s['name']}, addr: 0x{s['addr']:08X}, size: 0x{s['size'] or 0:X}}}")
    lines.append("")
    LEDGER.write_text("\n".join(lines), encoding="utf-8")
    free = sum(n for a, n, _ in OV3_DEAD_BLOCKS) - sum(n for _, n, _ in OV3_CLAIMS)
    print(f"wrote {LEDGER.relative_to(_ROOT)}  ({len(slots)} ov5 slots, "
          f"{len(PHANTOM_CLAIMS)} phantom claims, {len(OV3_DEAD_BLOCKS)} ov3 dead blocks, "
          f"{free} B ov3 still free)")


def check_ledger_drift() -> list[str]:
    """The committed ledger's ov5 addresses must match the live ov5_cave.py."""
    if not LEDGER.exists():
        return [f"ledger missing: run `check_allocations --emit` to create {LEDGER.name}"]
    ledger_addrs = set()
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*addr:\s*(0x[0-9A-Fa-f]+)", line)
        if m:
            ledger_addrs.add(int(m.group(1), 16))
    live_addrs = {s["addr"] for s in parse_ov5_slots()}
    drift = []
    for a in live_addrs - ledger_addrs:
        drift.append(f"ov5 slot @0x{a:08X} in ov5_cave.py but NOT in the ledger — run --emit")
    for a in ledger_addrs - live_addrs:
        drift.append(f"ledger slot @0x{a:08X} no longer in ov5_cave.py — run --emit")
    return drift


# ---------------------------------------------------------------------------
def run_checks() -> list[str]:
    slots = parse_ov5_slots()
    return (check_ov5_overlaps(slots)
            + check_phantom_dupes(PHANTOM_CLAIMS)
            + check_ov3_claims()
            + check_cave3()
            + check_ledger_drift())


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--emit" in argv:
        emit_ledger()
        return 0
    violations = run_checks()
    slots = parse_ov5_slots()
    live = sum(1 for s in slots if _live(s))
    ov3_free = sum(n for _, n, _ in OV3_DEAD_BLOCKS) - sum(n for _, n, _ in OV3_CLAIMS)
    print(f"allocation check: {len(slots)} ov5 slots ({live} live), "
          f"{len(PHANTOM_CLAIMS)} phantom claims, {len(OV3_CLAIMS)} ov3 dead-code claims "
          f"({ov3_free} B free), {len(parse_cave3_slots())} ov3 pool slots")
    if violations:
        print(f"\n{len(violations)} COLLISION(S):")
        for v in violations:
            print(f"  [X] {v}")
        return 1
    print("  [OK] no ov5 overlaps, no phantom double-claims, no ov3 overlaps, ledger in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
