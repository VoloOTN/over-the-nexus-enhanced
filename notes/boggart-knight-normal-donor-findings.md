# XX-Saber Boggart Knight — re-home onto a Normal-Monster donor (2026-09-08)

Task: `patch_boggart_knight` cannibalised **Vampire Orchis 0x15D4**, a real Effect
Monster. Moved to a records-free vanilla per the Tier-A row in
`notes/normal-donor-migration-findings.md`:

> `patch_boggart_knight` | Vampire Orchis 0x15D4 | native "when Normal Summoned"
> cls1 trigger | `summon.trigger_is_a_membership_list`: add the donor to list
> 0x0228F7AC (code 7) + a cls1 record + populate row

**Status: ✅ DONE — IN-GAME CONFIRMED BY USER 2026-09-08, first test, ALL FIVE
oracles.** `verify()` 19/19 PASS, allocation guard clean, and no regression from
the later chain steps (proved by a 3-step mini-chain, below).
`data/over_the_nexus/working/rom_boggart_knight_hand_v2.nds`

The five oracles the user confirmed in a duel:
1. the card reads **XX-Saber Boggart Knight**, EARTH / Beast-Warrior / Lv4 /
   1900 / 1000, with the full printed text;
2. Normal Summoning it with a Lv<=4 "X-Saber" in hand offers the prompt and
   Special Summons that monster from the hand;
3. it counts as an "X-Saber" for other cards (Faultroll on-field count,
   Gardestrike GY count);
4. it is refused as Synchro Material for a non-"X-Saber" Synchro Summon;
5. **Vampire Orchis 0x15D4 is a real card again** — her own name, art, stats and
   her own "Special Summon 1 Des Dendle" effect.

## Confirmed (this session, read out of stock `data/over_the_nexus/working/rom.nds`)

* **What the old patch borrowed from Orchis was exactly one thing: her cls1
  record.** Orchis cls1 row **278** =
  `{cid 0x15D4, +04 0x0220667D, +08 0, +0C 0, +10 0x021E9A21, +14 0}`.
  Boggart 0x2346's cls1 row **1227** is **byte-identical apart from the cid**.
  The donor's record is a verbatim copy with the cid swapped — no new shape, no
  new handler. Asserted at build time against the live ROM, not hardcoded blind.
* **Boggart's criteria row 1235** = `{a 0x2346, b 0x0048, h 0x0223CA71,
  fl 0x00900002}` — exactly the `BOGGART_B / BOGGART_H / BOGGART_FL` constants the
  old PART A copied onto Orchis. Still present in stock; also asserted at build.
* **Code-7 (Normal Summon) membership list 0x0228F7AC**: 103 entries (`0x67`),
  strictly sorted, and it contains both 0x15D4 and 0x2346. Dumped in full.
* **Donor: `0x13A5` Molten Behemoth** — Normal Monster, `donor_scan` VERDICT
  **CLEAN**, zero aligned u16/u32 occurrences in ov3 + ARM9 (its single ov3 u16
  hit at 0x021707F0 is an instruction encoding, below the per-cid data block).
  Its short text slots (name floor 10 B, desc floor 55 B) **do not matter** —
  `card_text.py` re-emits the blobs in index order, so strings may exceed the
  donor's original slot. Confirmed in the build log: the FULL name
  "XX-Saber Boggart Knight" (23 B) and the full 211-B printed text landed in
  **all eight** languages.
* **Three count-neutral inserts, all phantoms checked against PHANTOM_CLAIMS AND
  the chained image `rom_all_patches.nds`** (still present there, i.e. unspent):
  | insert | table | phantom dropped | measured effect |
  |---|---|---|---|
  | A1 c7 membership | 0x0228F7AC ×0x67 | `0x0E74` | donor @4, 103 entries, sorted |
  | A2 cls1 record | 0x022860D4 ×0x535 | `0x0E11` | donor @143, 140 rows shifted, 1333 unchanged |
  | A3 criteria row | 0x022713C4 stride 12 | `0x0E20` | donor @122, 106 rows shifted, 1389 unchanged |
* **Criteria table bound**: 1388 real rows + the `0xFFFF` sentinel = **1389**.
  (`patch_ninja_grandmaster_hanzo`'s `CRIT_COUNT = 1391` reaches two rows PAST the
  sentinel; this module counts to the sentinel instead so an insert can never step
  over it.)
* **PART D and PART E needed no new mechanism** — the X-Saber set-code insert is
  the same `add_xsaber_member` call with a different cid (dropped 0x2347, table
  still 20 sorted entries), and the Synchro-material restriction is the existing
  `CAVE_BOGGART` stub with one literal changed (`0x15D4` → `0x13A5`). Hook
  0x022482B2 → 0x0239A160 unchanged; predicate pivot literal still 0x2346.
* **Vampire Orchis 0x15D4 is a real card again** — touched nowhere.
  `_assert_orchis_untouched` pins her native criteria row
  `{0x15D5, 0x0223DAA5, 0x00000802}`, her single cls1 record, and her code-7
  membership, at build time AND in `verify()`. A future patch reaching for her as
  "records-free" trips it.

## Ruled Out

* **Dropping 0x2346's own cls1 / criteria rows** as the count-neutral victims.
  Tempting (Boggart's reserved cid) but its criteria row is already claimed by
  `tg_rush_rhino` in `populate_table`, and its cls1 row is the template we clone.
  Anonymous 0x0Exx phantoms cost nothing and keep the template readable.
* **Rejecting Molten Behemoth on text slots.** That was the initial reading and it
  is obsolete: the in-place slot limit died with `card_text.py`'s index-order
  re-emit (user, 2026-09-08). Gene-Warped Warwolf 0x1B30 was the alternative and
  is no longer needed.

## Open Questions

1. `patch_darksoul` and `patch_tg_rush_rhino` both legitimately spend 0x2346
   phantoms **after** this step in the chain. Two `verify()` checks were therefore
   downgraded to informational notes; the ORDER DEPENDENCY (boggart must run
   before rhino, because it clones 0x2346's criteria row) is now documented in
   `_apply_boggart`'s docstring but is **not** enforced by a guard.
2. Should the effect text keep modern wording ("GY")? It is quoted verbatim from
   ygoprodeck; the ROM era says "Graveyard".

## Next Experiment

None — the card is done. The only thing left open is Open Question 1: nothing
guards the boggart-before-rhino ordering in `PATCHES`. If that list is ever
reshuffled, boggart's build aborts loudly at `find_pop(0x2346)` rather than
emitting a bad ROM, so it fails safe.

## Inherited from the pre-DSL module docstring (UNVERIFIED, not re-proven; moved 2026-10-29 during DSL conversion)
- Order dependency: boggart must run before tg_rush_rhino (Rhino spends criteria phantom 0x2346, which this card clones). Unguarded; the DSL `_template` assert fails loudly if reordered.
- "When Normal Summoned" is a membership list (evaluator 0x02265768, code 7), not a flag; the three rows are why it works on a records-free donor and stays puzzle-safe.
- Synchro restriction: the shared predicate computes r4 = cid and r4 is scratch (reassigned before the property lookup), so remapping r4 0x13A5 -> 0x2346 at 0x022482B2 is side-effect free.
- Removed tripwire: build/verify asserted Vampire Orchis 0x15D4 untouched (criteria row b=0x15D5 h=0x0223DAA5 fl=0x802, one cls1 record, still in the code-7 list). No longer checked.
- Removed ov5 variant of the Synchro stub (CAVE_BOGGART 0x0239A160); only the ov3 home is built now.
- Old module also exported find_pop/_rebuild_v1_pac/_iter_paths helpers via finished_patches; those live in finished_patches (the oracle), not here.
