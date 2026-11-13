# Infernoble Knight Maugis — findings

Family card 2 (roadmap ~\.claude\plans\add-all-the-infernoble-merry-rainbow.md). Started 2026-10-20
while the user tests Ogier (user: "Start building Maugis while I test Ogier"). Status: AWAITING CLAUSE + DONOR
CONFIRMATION — no ROM code yet. Builds ON TOP of Ogier's patch_infernoble (C3 reuse), so an Ogier C3 failure
must be fixed first.

## Printed text (scratch/ygoprodeck_cache.json, Effect, Warrior, FIRE, L4, 1500/1000)
- C1 While this card is an Equip Card, the equipped monster cannot be destroyed by battle.
- C2 (OPT) If this card is sent to the GY: You can shuffle into the Deck, 3 of your other FIRE Warrior monsters
  and/or "Noble Arms" cards that are banished or in your GY; draw 1 card.
- C3 (OPT) If this card is in your GY: You can target 1 Warrior monster you control; equip this card to that monster.

## Confirmed (static, this session)
- C1 model: Mist Body 0x1992 has NO record; its battle check is in the battle predicate at 0x021984C0:
  `ldr r2,=0x1992 ; adds r0,r5 ; adds r1,r4 ; bl 0x021A0950 ; cmp r0,#0 ; beq ; b 0x02197F16` (indestructible exit).
  0x021A0950 = attached-node walker (kind 6..0xB, "equipped with cid X"). Hook = chain at the BL 0x021984C8.
- C2 model: shared "shuffle N from GY, draw" resolver 0x0221FB95 (Pot of Avarice 0x196F cls0[658], Gladiator's
  Return 0x1C90 cls0[869], Royal Firestorm Guards 0x1D3F cls1[759], Psychic Overload 0x1E6D cls0[984]); slot5
  0x02235701. Count = desc[+0x12] (targets chosen at activation). Phase 0x80 requires each target IN THE GY
  (0x021A2510) -> banished targets would abort. 0x7F shuffles each via 0x021C6A0C(desc, side, ref, 1).
  Draw: cid switch @0x0221FC56 (0x203D / 0x23DF / 0x23E2 special), default 0x022065B8(desc) (draws 1 for
  Gladiator's Return, 2 for Pot -> per-cid inside, NOT YET READ). Royal Firestorm crit {0xFFFF, 0x0223CBB1,
  0x20010002 Pyro}; Gladiator's Return crit {aux 0x24 set, 0x0223CBC9, 0x0001000E}.
- Donor candidates (donor_scan CLEAN + near_lits no hits): Wolf Axwielder 0x139A (L4 EARTH Beast-Warrior
  1650/1000), Beaver Warrior 0x0FC1 (1200/1500), Tiger Axe 0x0FE6 (1300/1100).

## IN-GAME RESULT — in-game confirmed by user 2026-10-20 (BUILD 3, rom_infernoble.nds dc1e1293...486d)
User's words: "Maugis works perfectly now. Add it to confirmed."
- CONFIRMED: C1 (equipped monster not destroyed by battle), C2 (sent to GY from any location -> shuffle 3 other FIRE
  Warriors from GY/banished into the Deck, draw 1; once per turn; resolution-time OPT stamp), C3 (GY equip, once per turn).
- NOT BUILT / NOT TESTED: C2's "Noble Arms" half (joins with the Infernoble Arms).
- NOT SEPARATELY REPORTED: regression items 12-14. NOT shipped (not in steps.STEPS).

## BUILD 2 (Ogier + Maugis, 2026-10-20)
- User confirmed clause split, C2 option "a" (targets on activation, banished allowed), donor Wolf Axwielder 2026-10-20.
- rom_infernoble.nds sha256 d047fa39272b4b6e0e2e44dc632d3a4e3e867332976e8d71d3afaeb6185a6c1e (on rom_all_patches.nds).
- ONE cls2 record over phantom 0x1B49, slots switched on desc[+3]==0xE && desc[+4]>6 (Jet Synchron's discriminator).
  C2: own resolver CAVE_IK_M_C2RES (0x0221FB94 phases, GY 0x021A2510/0x021C6A0C OR banished 0x021A2558/0x021C6A9C),
  slot5 replay r4=9 (3 targets), cond = OPT 0x539A + 0x02243FE0 >= 3 -> 2, slot4 = "You can" + post, criteria row
  {0xFFFF, C2H, 0x7C010002} over 0x0E7F (C2H = GY worker + banished worker, Ogier's exclude-cid callback),
  leave-mask {0x139A, 0x0800} over 0x0E1D, draw-count {0x139A, 1} over 0x0E19, timing arm ARM_IKM PREPENDED (appending
  overflowed an early arm's conditional range), ov3 chain front @0x021D13F6 (Gilfer node), ov3 miss front @0x021EE10C.
  C3: Vylon resolver/filter/slot5, igncond {0, 0x021F8049, M_C3F2} over 0x0E7D, gy_vrow_hook row, EQFILT +Maugis cid.
  C1: CAVE_IK_M_BATTLE fronts Mist Body's query BL @0x021984C8 (native query first, then Ogier-style S/T scan).
- PROOFS this session: chain_walk_diff.py (all 0x2700 cids, every stub registered): only 0x139A changes leaf -> accept.
  miss_diff.py: only 0x139A's miss verdict changes, 1 -> 0. patch_infernoble.verify PASS.
- Verify sweep on the build: 84 passed / 16 failed; EVERY failure is (a) the shared timing / c79 stub carrying our
  LOCAL arms or (b) Snoww/Eva whole-chain walk without patch_infernoble registered -- the chain ROM alone is 100/0.
  Tolerances added (verify only, no shipped bytes): patch_safe_zone (Mist Body link), patch_white_dragon_ninja
  (0x021B059C split -- Ogier's PROT), patch_eva + patch_shadow_mist (miss-node fronts chain).
- Ruled out: node 0x021D13EE (Sword of Deep-Seated compare) is NOT on 0x139A's path (it takes bgt 0x021D13F6) --
  first build put the front there; execution trace caught it before any in-game test.
- ASSUMED: the banished worker's callback gets [sp] = &card word like the GY one (native GY callback 0x0223C825 proves
  the GY side only).

## IN-GAME TEST 1 (BUILD 2, d047fa39...) — C2 FAILED
User: "See .ml3, Maugis's "pot of avarice" effect activated but did not resolve." Reading confirmed by user: (b) the
effect went on the chain, NO 3-card picker appeared, nothing moved. Maugis was sent FROM THE DECK; all candidates in the GY.
- Savestate rom_infernoble.ml3 (2026-10-20 10:26, ROM identity OK: every ov5 stub in RAM == build). Board: side 0 GY 13
  cards incl. 0x139A + 0x13A3, nothing banished. Executed over the state (scratch/infernoble/maugis_ss.py):
  0x02243FE0(0, 0x139A, param 0) = 3 candidates -> the picker HAD 3 legal cards. Our +0C now returns 0 (OPT stamped).
- Maugis descriptors in RAM @0x0229A37C / 0x0229A7FC: {0x139A, side 0, zone 0x0E, event 0x1E (relocation), class 2,
  +0xC ref 0x2C, **+0x12 target count = 0**} -> resolver phase 0x80 `n == 0 -> return 0` = nothing happened.
- ROOT CAUSE (disasm 0x02235994..0x022359A6): slot5's shared tail phase 0 RE-RUNS the record's +0C via
  `bl 0x0224AD94(desc, [sp])` and returns 1 (no picker) when it says 0. Our +10 stamped the C2 OPT on "Yes" BEFORE
  slot5 ran, so the re-check saw "used" -> no picker. = the dispatch.slot3_reevaluated_after_cost hazard Jet
  Synchron's docstring warns about. Ogier's C2 (cls1, +14 = 0) has no slot5 re-check -> unaffected (confirmed).
- FIX (BUILD 3): C2's +10 = the plain "You can" tag (no stamp); the C2 OPT is checked-and-stamped at resolver
  phase 0x80 (already stamped -> resolve as nothing). Declining still burns nothing. Residual: two Maugis sent in the
  SAME chain could both activate; only the first resolves.
- BUILD 3 built 2026-10-20: rom_infernoble.nds sha256 dc1e12938e159db4da01990dea4bc2f1072b1297cbea550c0d34f39a3818486d.
  M_C2RES grew to 288 B (slot 0x120; C2H/C3F2/BATTLE shifted +0x20, CAVE_FREE 0x023A7D60). patch_infernoble.verify
  PASS; chain_walk_diff PASS (only 0x139A); miss_diff PASS (only 0x139A 1->0); gyv_equiv ALL PASS. RE-TEST PASSED (user 2026-10-20).

## Open Questions
- C2 banished zone: native resolver is GY-only; needs a zone-extended handler + resolver phase-0x80 tolerance.
- C2 is NON-targeting in print ("shuffle ... 3"); native shape targets at activation.
- "other" = excluding Maugis itself (the just-sent copy).

## Next Experiment
- Read 0x022065B8's draw-count switch; find a criteria handler covering GY+banished.

## "Noble Arms" half (2026-10-22) -- BUILD 27 AWAITING IN-GAME TEST
- rom_infernoble.nds sha256 9acdb6fa935264b7bd69025297cfd8004619c12f009956e203269750ecc6ade1; verify PASS; regression FAIL
  set identical to BUILD 26.
- Row words made type-only (Ogier 0x00000006 Deck; Maugis 0x00010006 GY+banished); new shared callback AR_NACB (ov5
  0x023AB770): cid != excluded AND (one of the four Infernoble Arms OR Warrior + FIRE). Ogier's old C2CB is kept (Charles
  and Angelica use it with FIRE-Warrior words).
- EXECUTION-PROVEN: scratch/infernoble/nacb_check.py -- AR_NACB matches a Python oracle on 8,610 (card, excluded) cases;
  all four Arms kept, the excluded card never kept.
