# Junk Speeder — re-donor off Daigusto Sphreeze 0x24B3

Session 2026-09-22. Goal (user): move the shipped Junk Speeder patch onto an
**effectless Level 6+ Fusion monster** instead of Daigusto Sphreeze 0x24B3.

Card is SHIPPED (`steps.STEPS` line 95, clauses 1/2/5 in-game confirmed
2026-09-02). Nothing about the *effect* changes; only the carrier cid.

## Confirmed (this session)

- **Printed text** re-read from `scratch/ygoprodeck_cache.json` id 77075360.
  WIND / Warrior / Synchro / Effect, Level 5, 1800 / 1000.
  Clauses: (1) `1 "Synchron" Tuner + 1+ non-Tuner monsters`; (2) if Synchro
  Summoned, mass-SS "Synchron" Tuners of different Levels from Deck in DEF;
  (3) ED lock; (4) double original ATK on attack declaration; (5) hard OPT.
  Shipped today: clauses 1, 2, 5 (+ "Junk" membership). 3 and 4 deferred.

- **The proper-SS trigger list 0x0228F6C0 is 36 entries, sorted, ALL REAL —
  no phantom.** Re-dumped from `reference_files/nds_overlay_3.bin` this
  session; last entry is the current donor 0x24B3. The lists at 0x0228F678
  and 0x0228F708 are packed flush against it, so it **cannot be grown in
  place** either. (Matches `summon.synchro_trigger_list_has_no_phantom`.)
  ⇒ A new donor can only get the "If this card is Synchro Summoned" trigger
  through the **ov5 membership-verdict hook at 0x02265900**.

- **Precedent for the whole shape: `patch_accel_synchro_stardust_dragon`.**
  Accel Synchro Stardust Dragon is a Synchro monster shipped onto the
  **vanilla Level 8 Fusion** Meteor B. Dragon 0x126F, in-game confirmed
  2026-09-14. Its recipe is exactly what a Fusion→Synchro re-donor needs:
  - A `card_prop` ← a reference Synchro's whole record, cid swapped (type 37)
  - B `card_genre` clear FUSION bit 29 / set SYNCHRO bit 36
  - C fusion recipe A row materials → 0x3FFF (the CPU AI planner reads it)
  - F trigger: `bl` over the 4-byte membership verdict `cmp r0,#0 ; beq`
    @0x02265900 → ov5 stub `CAVE_ASSD_TRIG`, member arm 0x02265904,
    non-member arm 0x02265910
  - material rule: **absence** from LIST_A 0x02275AB8 (16) and min-3
    0x02275AD8 (21) is what yields "1 Tuner + 1+ non-Tuner".

- **Candidate donors** — effectless (`card_type == Fusion Monster`) and
  Level ≥ 6, from `donor_scan.cards()` over the working ROM. 0x126F is
  excluded (Accel Synchro Stardust Dragon already owns it). Scanned with
  `donor_scan.occurrences` + `classify`; "clean" = the ONLY binding
  occurrence anywhere in ov3 + ARM9 is the card's own fusion recipe A row,
  which the ASSD recipe kills anyway:

  | cid | Lv | name | binding hits |
  |---|---|---|---|
  | 0x1160 | 6 | Aqua Dragon | fusion recipe A[28] only |
  | 0x1179 | 6 | Crimson Sunbird | fusion recipe A[31] only |
  | 0x11A3 | 6 | Bracchio-raidus | fusion recipe A[38] only |
  | 0x1127 | 7 | Bickuribox | fusion recipe A[23] only |
  | 0x120B | 7 | Twin-Headed Thunder Dragon | fusion recipe A[47] only |
  | 0x13C6 | 7 | Humanoid Worm Drake | fusion recipe A[57] only |

  Rejected for extra binding/advisory hits: 0x1002 Rabid Horseman,
  0x0FCB Gaia the Dragon Champion, 0x1118 Labyrinth Tank, 0x1458 St. Joan,
  0x17EF Master of Oz, 0x1122 Blue-Eyes Ultimate Dragon, 0x107F B. Skull
  Dragon (6 arm9 advisories), 0x0FEB Thousand Dragon (5), 0x18FA Steam
  Gyroid (arm9 0x0209CD20, in the set-code table band).

  All six clean candidates verified **absent** from LIST_A and from the
  min-3 list this session.

- **Why Level 6+ is the right filter** (user's constraint, corroborated):
  Instant Fusion 0x1AF5 special summons a Level 5 or lower Fusion monster
  from the Extra Deck, so Level 6+ vanilla Fusions are the genuinely dead
  ones.

- **Nothing needs "undoing" on Sphreeze.** Every patch applies to a fresh
  base ROM, so deleting the Sphreeze-specific parts restores it outright.

## Confirmed (second pass, 2026-09-22)

- **0x120B card_prop / card_genre, read out of the working ROM this session:**
  `card_prop[513] = 0x00261C456946120B`, card_type field = **5** (Fusion
  Monster); `card_genre[513] = 0x0000000020200000` = {bit 21 nomi, bit 29
  FUSION} — **byte-identical to Meteor B. Dragon 0x126F's genre**, so Accel
  Synchro Stardust Dragon's `NEW_GENRE = 0x0000001000200000` (clear 29, set 36
  SYNCHRO) transfers verbatim.
- **Fusion recipe A[47] @0x02270D0C = {0x120B, 0x114F, 0x114F, 0x0000}**
  (Thunder Dragon x2). Killed to 0x3FFF/0x3FFF exactly like ASSD's A[52].
- **0x120B is absent from LIST_A 0x02275AB8 (16) and the min-3 list
  0x02275AD8 (21)** — the two Synchro material-count exception lists. Absence
  from both is what yields the printed "1 Tuner + 1+ non-Tuner monsters".

- **CLOSED PROOF that no per-cid arm of the Synchro material predicates can
  select 0x120B.** A per-cid compare here keys either on a pool literal equal
  to the cid (which `donor_scan.occurrences` would find — it finds none outside
  the fusion recipe row) or on `base ± imm8` off a pool literal
  (`thumb.stack_based_switch`, which stores no cid). The second form can only
  reach a cid from a literal `L` with `|L - cid| <= 0xFF`. Enumerating every
  word-aligned u32 in the material-predicate span **0x02248280–0x02249600**
  (INNER 0x0224829C, OUTER 0x022485B4, THIRD 0x02248A88 and their leaves):

      0x120B -> 0 literals within +/-0xFF
      0x126F -> 0 literals within +/-0xFF     (the in-game-confirmed ASSD donor)

  So 0x120B reaches the same generic leaves 0x126F does, and PART H of the old
  patch (which opened Daigusto Sphreeze's donor-exclusive "Gusto" non-Tuner
  leaf 0x02249360) has **nothing left to open** — "1+ non-Tuner monsters" is
  the donor's native behaviour. Probe:
  `scratchpad/cid_reach_probe.py`.
  (The one hit in the wider 0x02248000–0x0224A000 window, literal 0x12E5
  Polymerization @0x02249EB0, is in the FUSION-material enumerator that
  precedes the Synchro resolver 0x02249EC0 — outside the predicates, and
  equidistant for both cids.)

  ⚠️ Sphreeze 0x24B3 by contrast has **6** nearby literals in that span (7 in the
  wider 0x02248000–0x0224A000 window), which
  is exactly why the old patch needed PARTs H and I.

- **Phantoms chosen for the two count-neutral inserts** (both unclaimed in
  `check_allocations.PHANTOM_CLAIMS`, verified this session):
  `cls1_table` 0x120E, `criteria_table` 0x14D7. Both are near the donor, so
  `_insert_sorted` shifts few rows.

## What changes in patch_junk_speeder

| old (Sphreeze 0x24B3) | new (Twin-Headed Thunder Dragon 0x120B) |
|---|---|
| A cls1 rewritten IN PLACE | A cls1 **inserted** over phantom 0x120E |
| B criteria rewritten IN PLACE | B criteria **inserted** over phantom 0x14D7 |
| C battle-indestructible list drop | gone — donor is not in that list |
| F battle-damage redirect kill | gone — donor has no such grant |
| G "Gusto" set-code drop | gone — donor is not a "Gusto" card |
| H open the exclusive non-Tuner leaf | gone — donor reaches the generic leaf |
| trigger: donor already in 0x0228F6C0 | trigger: **shared** summon_trigger_hook |
| identity: card_type only | + card_prop template, genre, fusion recipe kill |
| I Tuner gate, J Junk member, K OPT | unchanged apart from the cid |

## Ruled Out

- **Count-neutral insert into 0x0228F6C0** — no phantom in the list (all 36
  cids resolve to real cards).
- **Growing 0x0228F6C0 in place** — the neighbouring membership lists are
  packed flush at 0x0228F6BE and 0x0228F708; there is no slack.
- **Swapping 0x24B3 out of the list for the new donor** — that would leave
  Daigusto Sphreeze without its own printed "When this card is Synchro
  Summoned" trigger, i.e. a regression to a real card, which is the thing
  this re-donor is meant to avoid.

## Decided (user, 2026-09-22)

- **Donor = Twin-Headed Thunder Dragon 0x120B** (Lv7 LIGHT/Thunder, fusion
  recipe A[47] is its only binding occurrence).
- **The 0x02265900 hook is promoted to a shared arms module**, the way
  `criteria_row_hook` / `timing_class_hook` already work;
  `patch_accel_synchro_stardust_dragon` re-registers into it.

## Open Questions

- Nothing blocking. The build is done and static-clean; the only open item is
  the in-game test.

## Built AND IN-GAME CONFIRMED (2026-09-22)

**In-game confirmed by user 2026-09-22.** Their words: *"confirmed all works"*,
against the nine-item round-7 plan in `_build_junk_speeder.py`; the reading was
quoted back and confirmed by the user before being recorded here.

What that covers, beyond the headline (identity / summon / trigger / effect):

- **Daigusto Sphreeze is a normal card again** — the point of the whole change.
- **The trigger fires for a donor OUTSIDE the membership list.** This is the
  load-bearing result: `0x0228F6C0` cannot be inserted into or grown, and the
  shared ov5 stub over the membership verdict `0x02265900` is now *measured*, not
  merely reasoned, as a working trigger path for an arbitrary donor.
- **Accel Synchro Stardust Dragon still triggers off the same stub.** Both arms
  confirmed in one session, so the second arm did not displace the first — the
  measurement `otn-shared-hook-lift-prove-by-execution` asks for.
- **The generic material rule holds in play**, which closes the loop on the
  static proof below: zero nearby literals really did mean "no per-cid arm".
- The blanked fusion recipe A[47] does not upset the CPU planner.

Static results from the same build, for provenance:

- `_build_junk_speeder.py` -> `rom_junk_speeder.nds`: **ALL CHECKS PASSED**
  (45 checks, including the two inserts, the fusion kill, all five ov5 stubs
  byte-exact + Thumb-1, the shared trigger hook, the material-rule scan, the
  Tuner gate, card_prop/card_genre, and card text in all 8 languages).
- `otn_enhanced.build`: **73/73 steps in 234.4 s**,
  `sha256 627fa45c7b6b44c7fd4b559d235ec046d76a45ec335e9e3226a43fc55c96faba`,
  `rom_all_patches.nds`.
- `otn_enhanced.verify rom_all_patches.nds`:
  **59 passed, 0 failed, 0 without verify()**.
- `check_allocations`: 271 ov5 slots (250 live), 288 phantom claims, no
  collisions, ledger in sync.
- `verify_knowledge`: 538 facts, 495 PASS / 0 FAIL / 43 UNVERIFIED.

### Files changed

| file | what |
|---|---|
| `finished_patches/summon_trigger_hook.py` | **NEW.** The shared 0x02265900 hook: one stub, an `ARMS` register (0x126F, 0x120B). |
| `finished_patches/ov5_cave.py` | `CAVE_ASSD_TRIG` retired; `CAVE_SUMMONTRIG = 0x023A1324` (0x60 B); `CAVE_FREE` -> 0x023A1384. |
| `finished_patches/patch_accel_synchro_stardust_dragon.py` | Its one-arm `trig_stub` lifted into the shared module; logic unchanged for 0x126F. |
| `finished_patches/patch_junk_speeder.py` | The re-donor. PARTs C/F/G/H (Sphreeze clean-ups) deleted; A/B became inserts; PARTs C/L/M/N added. |
| `finished_patches/card_text.py` | `0x24B3` -> `0x120B`. |
| `finished_patches/apply_all_patches.py` | Step label + docstring (the retired oracle still calls the module). |
| `otn_enhanced/steps.py` | Step label. |
| `knowledge/check_allocations.py` | `donor_cid` 0x120B, `cls1_table` 0x12A9, `criteria_table` 0x16C2, plus the MISSING `junk_setcode_table` 0x2524 claim the shipped card had been spending unregistered since 2026-09-02. |
| `knowledge/author_facts.py` | `summon.proper_ss_list_verdict_site` amended (site is now shared); new VERIFIED `synchro.no_percid_arm_without_a_nearby_literal`. |
| `scratch/cid_reach_probe.py` | **NEW.** The closed reachability probe. |
| `_build_junk_speeder.py` | Round 7 test plan. |

### Slots this patch claims

- ov5: `CAVE_JSP_DATA / _CRIT / _RES / _TUNER / _USED / _CB / _COND` (unchanged),
  plus a share of the new `CAVE_SUMMONTRIG`.
- ov3: cls1 phantom **0x12A9**, criteria phantom **0x16C2**, fusion recipe A[47].
- ARM9: "Junk" set-code phantom **0x2524**.
- Hook sites: `0x022485D8` (Tuner gate, this patch owns it) and `0x02265900`
  (shared with Accel Synchro Stardust Dragon).

## Next Experiment

None — the card is done and confirmed. Clauses 3 (the Extra-Deck lock) and 4
(double original ATK on attack declaration) remain **deferred by the user**, not
waived; they were never in scope for this session.

If this card is touched again, the round-7 plan in `_build_junk_speeder.py` is
the regression checklist, and item 7 (Accel Synchro Stardust Dragon) must be
re-run whenever `summon_trigger_hook.ARMS` changes.
