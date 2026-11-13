# Sacred Sword of Seven Stars — findings

Printed text (scratch/ygoprodeck_cache.json id 45725480, Normal Spell):
"Banish 1 Level 7 monster from your hand or face-up from your side of the field; draw 2 cards.
You can only activate 1 "Sacred Sword of Seven Stars" per turn."

- C1 cost: banish 1 Level 7 from hand OR face-up own field.
- C2: draw 2.
- C3: hard OPT (name lock).
Scope (user, 2026-10-19): whole card this session. Status: **AWAITING IN-GAME TEST**. Built 2026-10-19: rom_sacred_sword.nds sha256 66249a77a20cbcb431582cc1696b7e4f6d0a2d82c8f65b9fd5b0fc426c0cb0ef (_build_sacred_sword.py on rom_all_patches.nds 13:37). Static verify PASS: own + Tenki + Dragon Rulers; allocation guard OK; KB 716/0/85.

Donor: **Block Attack 0x130A** (user's choice 2026-10-19; Des Croaking / Short Circuit rejected by user).

## Confirmed (this session, 2026-10-19)
- KB: verify_knowledge 715 PASS / 0 FAIL / 84 UNVERIFIED.
- 3DS: cid 0x2933 (CARD_Name idx 5587, Prop `332900001b023000`); absent on NDS (donor_scan.cards()).
  3DS criteria row @0x68C704 `3329ffff08be4a0002001c00` = {aux 0xFFFF, handler 0x004ABE08, word 0x001C0002}.
  0x001C0002 = Level 7 << 18, exactly-level (no bit 22/23). Only one main-registry row (no separate field row).
  3DS field handling is bespoke (0x47BD3C, 0x3F9500 — single-sharer), no NDS twin.
- NDS Trade-In 0x1C50: criteria row 572 @0x02272E94 {0xFFFF, 0x0223CB19, 0x00200002}; cls0
  {0x022065B9, 0, 0x021F0BDD, 0x021E4EED, 0}.
- Block Attack 0x130A raw u16 hits: arm9 0; ov3 2 = cls0 record[194] @0x0227F87C (own effect,
  RES 0x022076A5, +08 0x021DB1F9) and 0x021A049E (`asrs r2,r1,#0xc` encoding — not a ref).
  Stock ov5 4 hits (all AI): 0x02351B42 code `ldr r2,=0x130A; bl 0x021A1430(side, zone 0..4, key)` =
  AI asks "Block Attack rider on my monster?"; 0x022DEA38 / 0x02370E1C / 0x023990E4 = AI cid lists.
  None is a rules gate. No criteria row, no phantom claim, no finished patch references it.

## Ruled Out
- Donors Des Croaking 0x1923 / Short Circuit 0x1DCD — user rejected.
- Native "draw N" resolver 0x022065B9: needs a 0x022704A4 count row (count-neutral insert hassle). Use 0x021D12F4 direct.

- USER RULING 2026-10-19: field monster qualifies by its CURRENT Level (Level-modified 7 counts). Hand = printed.
- Matcher 0x0223BA24(side, zone, &cardword, word) reads PRINTED Level 0x0202ABD8 for every zone (KB
  dispatch.criteria_word_fully_decoded) -> it cannot serve the field half; need live reader 0x021B20AC.

- LEVEL_OF_ZONE 0x021B8064(side, zone) -> CURRENT Level (thunk to 0x021B807C(a,b,0), KB engine.thunk_0x021B8064;
  used in-game-confirmed by patch_accel_synchron). 0x021B20AC is the HAND-card live-level reader (ref in r1), not field.
- Picker path reaches the virtual row: 0x0219C430 -> bl 0x02243FA8 @0x0219C47C (KB counter proof) -> bl 0x02243B9C
  @0x02243FB6 (disasm this session) -> miss tail 0x02243F24 (H2 front chain) ; invoker 0x02243F38 calls
  handler(r0 row, r1 side, r2 param) via `adds r1,r5 ; adds r2,r7 ; blx r3` @0x02243F70.
- cave3 free gaps >= 0x14 B (FREE_RUNS minus CAVE3_*): 0x021F16CC (0x16), 0x021F1994 (0x1A), 0x02220BCC (0x16).
  Front = 0x14 B -> 0x021F16CC.
- ov5: CAVE_FREE 0x023A73A0; virtual row must sit at CAVE_RUL_ROWS(0x023A6BF0)+k*0x40 -> 0x023A73B0, k=31,
  index 0x5F00 (Rulers k 0..7, Tenki k=27).

## Open Questions
- (resolved statically) COUNT and picker both reach the 0x02243F24 front -- see the picker-path line above. In-game still unproven.

## Built (2026-10-19)
- cls0 Block Attack own record @0x0227F894 (chain) -> {0x130A, RES 0x023A7581, 0, COND 0x023A7441, COST 0x023A74A1, 0}.
- cave3 CAVE3_SSS_H2 0x021F16CC (20 B): 0x130A -> 0x5F00 else bl CAVE3_TENKI_H2; bl @0x02243F24 -> it.
  Tenki + Rulers verify widened to accept this front (composition, not behaviour change).
- ov5: ROW 0x023A73B0, HANDLER 0x023A73C0 (0x74), COND 0x023A7440 (0x54), COST 0x023A74A0 (0xD8), RES 0x023A7580 (0x18);
  hole 0x023A73A0..AF; CAVE_FREE -> 0x023A75A0.
- Pre-build checklist: (1) per-cid gates on 0x130A: none in arm9/ov3 (raw scan), 4 ov5 AI-only hits -- PROVEN.
  (2) zones: hand builder 0x0223C16C (DEP-proven), field FIELD+zone*0x14 +0/+8 (Oja-proven) -- PROVEN by precedent.
  (3) text: CARD_TEXT re-emit, check_rom_text PASS -- PROVEN. (4) OPT stamped in COST phase 0 -- PROVEN (source).
- NOT in steps.STEPS; no chain build / sweep until user confirms in-game.

## In-game report 1 (user, 2026-10-19, rom_sacred_sword.nds)
- Verbatim: "Banishing a dragon ruler with its effect from field does not trigger the search effect see .ml2"
- Confirmed details: Redox (0x17CD) face-up on field, picked as the cost; Redox banished, NO prompt, no activation of its
  banished-search. Sacred Sword drew 2. Hand-banish of a Ruler NOT tested yet.
- => C1 field banish + C2 draw WORK in-game for that case; the bug is the banished Ruler's trigger not firing.

- User follow-up (verbatim): "To confirm it is only the banish from field that is affected, where the rulers do not
  search". CONFIRMED by user 2026-10-19: Sacred Sword banishing a Ruler FROM HAND did trigger its search ("Yes that worked").

## In-game report 2 (user, 2026-10-19) -- native control
- Verbatim: "1. Tidal 2. Dark Core 3. No activate prompt 4. See .ml3 (before) and .ml4 (after)"
- CONFIRMED reading: native Dark Core banished a face-up Tidal from the field -> NO activate prompt for Tidal's search.
- => NOT a Sacred Sword bug. LATENT DRAGON RULERS GAP: a ruler banished FROM THE FIELD (any card) misses C4.
  Follow-up = patch_dragon_rulers, its own session (PROMPT_dragon_rulers_field_banish.md).
- Sacred Sword in-game so far (user 2026-10-19): field Lv7 banished + draw 2 works; hand Lv7 banished + Ruler search
  triggers. Remaining oracle items (OPT, refusals, changed Level, mixed list) NOT yet reported.
- WHOLE CARD IN-GAME CONFIRMED BY USER 2026-10-19, verbatim: "All confirmed all other bits of seven swords, update the
  card art and ship it" (on rom_sacred_sword.nds 66249a77...b0ef). The Ruler field-banish miss is a Dragon Rulers bug
  (separate session), not a Sacred Sword clause. SHIP approved 2026-10-19.
- SHIP WIRING DONE 2026-10-19: steps.STEPS "Sacred Sword of Seven Stars" after Tenki; _verify_all_patches.SHIPPED;
  patch_card_art.CARDS 0x130A (art already in card_arts/implemented/sacred_sword_of_seven_stars/);
  patch_bulk_card_pack row "Block Attack" -> "Sacred Sword of Seven Stars" (build 1 died at step 115 on the old name).
- CHAIN BUILD NOT DONE: build 2 died at step 104 (Dragon Rulers) because the parallel Rulers-fix session was mid-edit
  (CAVE_RUL_LEAVE missing at import). Rulers is in STEPS, so ANY chain build from this checkout now includes its
  UNCONFIRMED H8 fix. rom_all_patches.nds left untouched (== rom_all_patches.pre_sss.nds, sha 7e792694...f157).
- USER DECISION 2026-10-19 (verbatim): "Hold the chain build until the Rulers fix is confirmed in-game, then build once
  with both and run the sweep." -> NEXT: once the user confirms rom_rulers_field_banish.nds in-game, run
  `PYTHONIOENCODING=utf-8 .venv-1/Scripts/python.exe -m otn_enhanced.build`, assert
  N/N + sha256, then `-m otn_enhanced.verify data/over_the_nexus/working/rom_all_patches.nds`.
- SHIPPED 2026-10-19: Rulers fix confirmed by user; the Rulers session ran ONE chain build with both: 119/119
  (step 108 = Sacred Sword), rom_all_patches.nds sha256 7ad072b4ca3d292c7ce5eef12b96cafc5386ffed5447d2300ed8ff4a6c89d6c9,
  sweep "100 passed, 0 failed, 0 without verify()" (scratch/chain_build_rulers_sss.log, scratch/verify_sweep_rulers_sss.log).
  Re-checked here: sha256 recomputed matches; patch_sacred_sword_seven_stars.verify(rom_all_patches.nds) PASS.

## Investigation of report 1 (static, 2026-10-19)
- Field mover 0x021CF40C(side, zone, r2) = mask 1<<(side*16+zone) -> 0x021CDD4C(own zeroed 0x24 desc, mask, 0x0F, r2):
  only QUEUES a relocation (KB engine.relocation_request_core_0x021CDD4C). Disassembled this session.
- Rulers' C4 banish detection = H6 (GY->banished gate 0x021C71C8) + H7 (per-cid switch 0x021D1B98 inside 0x021D1300).
  0x021D1300 has exactly 3 BL callers in stock ov3: 0x021C6CB8 (core 0x021C6B00), 0x021D1F06 (Deck mover),
  0x021D2450 (fn 0x021D2314, location-destroy core). Raw scan this session.
- The queue consumer region 0x021CE0C0..0x021CF300 calls 0x021C7104 (GY banish) x3 and 0x021C6D58 (hand->GY) x1, and
  NO other 0x021C6B00 wrapper; its field-side callees (0x021CF7D4, 0x021C7538, 0x021C7CAC, 0x021C7D80) reach no
  0x021D1300 within a heuristic BL-graph BFS. HEURISTIC (function bounds guessed from push-lr) -- not a closed proof.
- Rulers' own oracle (_build_dragon_rulers.py item 6) tested C4 only "from hand AND from GY" -- a FIELD banish of a
  ruler was never tested. => HYPOTHESIS (UNPROVEN): a Ruler banished FROM THE FIELD by ANY card misses C4, because
  field departures go through the leave-field machinery (cls2 leave / leave-mask rows, leave-hook 0x021C8216), which
  the Rulers' virtual registry does not cover. If true this is a latent DRAGON RULERS gap, not a Sacred Sword bug.

## Ruler field-banish gap -- static findings (2026-10-19) -> carried into notes/dragon-rulers-field-banish-findings.md
- Savestates rom_sacred_sword.ml3 / .ml4 (ov3 image match 1.0000 vs rom_sacred_sword.nds): ml3 side 0 field zone 2 =
  Tidal 0x115F face-up, GY [0x115E, 0x1145, 0x15A1], ban []; ml4 field empty, GY + 0x15E9 (Dark Core), ban [0x115F].
- Dark Core 0x15E9 cls0 @0x02280D4C {0x02219B3D, 0x021DED59, 0x021F0221, 0x021E4EA5, 0x02234E11}; resolver
  0x02219B3C -> 0x021CF43C(desc, side, zone, kind) -> 0x021CDD4C(desc, mask, 0x0F, kind): SAME queued path as
  Sacred Sword's 0x021CF40C. So native and ours fail identically -- not a Sacred Sword bug.
- Queue consumer region 0x021CE0C0..0x021CF300 calls 0x021C7104(side, 0x021A25E8(ref), 0) x3 (0x021CECD0, 0x021CEFB8,
  0x021CF09E) -> banish worker 0x021C7118, which contains the Rulers' H6 gate 0x021C71C8. So a field banish MAY
  reach H6 (unproven which consumer arm Dark Core takes). Necroface 0x17BB (native 'if banished') has literals in
  BOTH the worker (0x021C724C) and the 0x021D1300 switch (0x021D1D9C); D.D. Survivor 0x18BC has no leave-mask row.

## Next Experiment
- User in-game test per _build_sacred_sword.py oracle list (11 items). If the list is empty with a Lv7 in hand, suspect
  the virtual row (front chain) first; if hand works but field not, suspect LEVEL_OF_ZONE / face-up word [+8].
