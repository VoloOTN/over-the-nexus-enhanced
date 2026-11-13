# Elder of the Six Samurai — re-donor to Flame Cerebrus (2026-09-17)

Task: swap this already-shipped card's donor from AoJ Cosmic Gateway (0x1F1D,
an effect monster) to Flame Cerebrus (0x11B7, a Normal Monster), per user
request and the established "donor-swap old effect-monster patches onto Normal
Monster donors" pattern (T.G. Striker / Warwolf precedent).

## Confirmed (this session)

- `donor_scan 0x11B7` (Flame Cerebrus): **CLEAN** — zero aligned u16/u32
  occurrences anywhere in ov3/arm9. Records-free Normal Monster, safe donor.
  Lv6 FIRE Pyro 2100/1800, pack1=52.
- Flame Cerebrus's native name/desc slots are too small for Elder's printed
  text (name floor 14B vs 24B needed; desc floor 50B vs 115B needed) — solved
  by adding cid 0x11B7 to `card_text.CARD_TEXT` (index-order re-emit, no slot
  limit), not the legacy in-place path.
- The old donor's PART A (dispatch-tree node retarget @0x0225EDFE) only works
  because AoJ Cosmic Gateway already owned a leaf in the hand-SS dispatch
  tree. A Normal Monster donor owns no leaf, so the effect is now installed
  via the SHARED multi-cid hand-SS trampoline (`tg_table.register_tg_handss`
  over `BL 0x0225E51C` @0x0224C026) — same architecture as T.G. Striker /
  Warwolf / Junk Servant / Assault Synchron. Condition stub logic is
  byte-identical to Striker's: canSS(side) && monster_count(side)==0 &&
  monster_count(1-side)!=0 (== gate 0x0225F33A's logic).
- PART E (removing the old donor from the Ally of Justice set-code table
  0x0209CB96) no longer applies — Flame Cerebrus was never an AoJ member.
  `patch_azure_eyes` already tolerates the AoJ table staying at its native
  21-entry count (its `AOJ_COUNT_NATIVE` branch), confirmed by the verify
  sweep still passing after removing PART E.
- New ov5 slot claimed: `CAVE_ELDER_SSCOND` @0x0239FDA0 (0x30 B); `CAVE_FREE`
  bumped to 0x0239FDD0. Registered in `check_allocations.PHANTOM_CLAIMS`:
  `("donor_cid", 0x11B7, "elder_six_samurai")` and
  `("sixsam_setcode_table", 0x251B, "elder_six_samurai")`.
- `check_allocations` (--emit + check): no collisions.
- Standalone build (`patch_elder_six_samurai --text`) + its own `verify()`:
  ALL PASS (hand-SS hook + condition stub BLs + Six Samurai table + card_text
  match in all 8 languages).
- EE fast build (`otn_enhanced.build`): 69/69 steps, wrote
  `rom_all_patches.nds`, sha256
  `a03448aca4f5f86ad90e51583975a84ce99b5eb54482cc066013021933c3f19e`.
- `otn_enhanced.verify rom_all_patches.nds`: **57 passed, 0
  failed** — including `patch_elder_six_samurai`, `patch_azure_eyes` (AoJ
  table), and `patch_tg_striker`/`patch_tg_warwolf`/`patch_tg_rush_rhino`
  (share the same hand-SS trampoline table), so no regression in any card
  that touches the same shared structures.

## Ruled Out

- Retargeting a dispatch-tree node for the new donor — Flame Cerebrus has no
  existing node in the compiled tree (0x0225E622-0x0225F20C) to retarget;
  inserting a new leaf is not a count-neutral table edit like the tree's
  fixed leaf structure assumes.

## Open Questions

- None outstanding for this donor swap; the mechanism is a direct application
  of the already in-game-confirmed T.G. Striker trampoline.

## In-game test result (donor-swap build, PRE card_type fix)

**IN-GAME CONFIRMED by user 2026-09-17.** Tested in melonDS: "All good, no
regressions." Covers the hand-SS offer on the re-donored card and the absence
of regressions elsewhere in the build, on the ROM as it stood before the
card_type fix below.

## Follow-up fix: card_type was never flipped (2026-09-17, same day)

Bug found by the user after the in-game confirmation above: the printed card
"Elder of the Six Samurai" is an **Effect Monster**
(`scratch/ygoprodeck_cache.json`: type="Effect Monster"), but the donor Flame
Cerebrus is a Normal Monster, and `apply_stats_and_text` was never told to
change `card_type` — it stayed "Normal Monster" in card_prop.bin. Fixed by
passing `card_type=ERA2_CARD_TYPE_REVERSE["Effect Monster"]` (value 3) into
`apply_stats_and_text`. Added a `verify()` check that decodes card_prop's
record for 0x11B7 and asserts `card_type == "Effect Monster"` so this can't
silently regress again.

Re-ran after the fix: standalone `verify()` ALL PASS (including the new
card_type check); EE fast build 69/71->71/71 steps (unrelated steps were added
elsewhere in the same session), sha256
`af19971be9ac14deec945edeb52eaf0c4178594ef39c2158bf1a636ad714e85e`; full sweep
**57 passed, 0 failed**.

**AWAITING IN-GAME TEST for this specific fix.** The card_type field change is
cosmetic/categorical (affects the in-duel Monster/Effect display and any
Normal-Monster-only support interaction) and was not covered by the prior
in-game confirmation, which predates it.
