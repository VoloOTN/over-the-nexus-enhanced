# Infernoble Knight - Renaud — findings

Family card 5. Donor Water Spirit 0x1E05 (L1 WATER Aqua Normal Tuner 400/1200) + clause split confirmed by user
2026-10-20 ("Confirmed, Water Spirit — proceed").

## Printed text (scratch/ygoprodeck_cache.json): Effect, Warrior, FIRE, L1, 500/500
- C1 If you control a FIRE Warrior monster, you can Special Summon this card (from your hand). Once per turn this way.
- C2 If Summoned this way, treat this card as a Tuner.
- C3 (OPT) If this card is Special Summoned: You can target 1 of your FIRE Warrior monsters, or 1 of your Equip Spells,
  that is banished or in your GY, except "Infernoble Knight - Renaud"; add it to your hand.

## Confirmed (static, this session)
- Donor 0x1E05: donor_scan CLEAN, near_lits no hits. Reaches the summon-event DEFAULT leaf 0x02268666 (walk).
- Plain-SS trigger list 0x0228F63A (x0x1F) has NO phantom left in the chain; its search BL 0x022658B8 is owned by
  patch_azure_eyes; the verdict pair `cmp r0,#0 ; beq` @0x022658BC is free (stock == chain) and has the c79 site's
  contract (member 0x022658C0, non-member 0x022658C2) -> new shared c9_trigger_hook.py. List literal @0x02265A20.
- Add-target-to-hand resolver 0x02208181 is shared by GY-target cards (Magical Stone Excavation 0x1638, Monster
  Reincarnation 0x1845: crit 0x0223CBB1) AND banished-target cards (Light of Redemption 0x1DCE, Parallel Selection
  0x2325: crit 0x0223DB25), all with +14 target step 0x02235605 -> one resolver handles both zones.
- Shared summon_rider_hook latch prefix home CAVE_RIDERLATCH (0x50) is too small for a 2nd arm (132 B) -> Renaud's
  latch = its own front CAVE_IK_R_LATCH at the RIDER_SITE BL, tail-jumping to the shared prefix.

## Build design (BUILD 7)
- C1: tg_table.register_tg_handss(0x1E05, R_SSCOND): can SS 0x021B9ECC, free MZ, OPT (side, 0xB, 0x1E05, 1) clear,
  face-up (0x021A32B4) FIRE Warrior (base race/attr getters) in zones 0..4; arms CAVE_IK_R_ARM.
  "Once per turn this way" stamp = ss_commit_hook row {0x1E05, kind 1} (any SS of Renaud from the hand).
- C2: R_LATCH front: byte && event SOURCE cid == 0x1E05 -> attach {0x1E40, kind 3} (Lightwave Tuning's key, read by
  the is-Tuner wrapper 0x021A1C7C). ASSUMED: a procedure summon's source cid [ev+0x12] is the summoned card itself.
- C3: c9_trigger_hook arm + cls1 {R_RES (OPT 0x5E05 at 0x80 -> 0x02208181), 0, R_COND, 0x021E51E5, 0x02235605} over
  phantom 0x0E5F; criteria {0xFFFF, R_C3H (GY + banished workers + Oliver's HANDCB, excl 0x1E05), 0} over 0x0E68.

## IN-GAME RESULT — in-game confirmed by user 2026-10-20 (BUILD 7, rom_infernoble.nds cfa2762c...c521)
User's words: "All confirmed. Proceed onto the next card" (answer to steps R1-R4 + regression 5).
- Whole card confirmed. This also PROVES in-game the assumption that a hand-SS procedure summon's event SOURCE cid
  [0x02298A28+0x12] is the summoned card itself (the 0x1E40 latch fired -> R3 passed). NOT shipped.

## BUILD 7 (all five Knights)
- rom_infernoble.nds sha256 cfa2762cee022243e07d62129309d36d3f4c3bf797107c1212351d270fd8c521.
- patch_infernoble.verify PASS (incl. R hand-SS registered, ss_commit row, C9 hook, cls1/criteria rows, rider site ->
  Renaud front, shared latch prefix unchanged); chain_walk_diff / miss_diff / gyv_equiv PASS.
- R_SSCOND executed over savestate .ml4 with the new stubs: side 0 (Oliver face-up on field) -> 1 + arms the byte;
  side 1 -> 0.
- Sweep 82/18: same modules; the new line "R summon-event default leaf -> latch prefix" (Jet Synchron / Remus / BF)
  is the local-front category (rider site now BLs Renaud's front, which tail-jumps to the shared prefix).

## Open Questions
- Does the rider latch fire for the procedure summon (source cid)? In-game T2 will tell; if not, measure [ev+0x12].
