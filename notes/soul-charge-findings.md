# Soul Charge — findings

Status (2026-09-14): all four clauses IN-GAME CONFIRMED by user; SHIPPED into apply_all_patches /
steps.STEPS. Donor Breath of Light 0x123D (user-approved 2026-09-13). Superseded lines below (this
section is UNVERIFIED as of 2026-09-14 and kept only for provenance -- see the "Round 2 build" and
"Clauses 3+4 in-game confirmed" sections for current state):
Single-card ROM `data/over_the_nexus/working/rom_soul_charge.nds`, sha256
`732C6D1338822093462A6DD1589BFAE9C4A72725BD700F129B26D721EDD18C2B`
(`python -m otn_enhanced.cards.soul_charge`, then `--verify` = 7/7 PASS).
NOT wired into apply_all_patches / steps.STEPS. check_allocations [OK]; verify_knowledge 426 PASS / 0 FAIL.
Module: `otn_enhanced/cards/soul_charge.py`. ov5: CAVE_SC_SELECT 0x0239EE90 (18 B),
CAVE_SC_RES 0x0239EEB0 (76 B); CAVE_FREE -> 0x0239EF00. cls0 @0x0227F21C.
Build gotcha caught by the stock-bytes guard: Breath of Light's cls0 +08 is 0x021D8DB9 (the survey print skipped +08);
it is set to 0, as on every native record of resolver 0x0221B4E0.

Printed text (scratch/ygoprodeck_cache.json, id 54447022, Normal Spell):
> Target any number of monsters in your GY; Special Summon them, and if you do, you lose 1000 LP
> for each monster Special Summoned by this effect. You cannot conduct your Battle Phase the turn
> you activate this card. You can only activate 1 "Soul Charge" per turn.

1. Target any number of monsters in your GY; SS them. (in scope)
2. Lose 1000 LP per monster SS'd. (in scope)
3. No Battle Phase the turn you activate. (NOT implemented — out of scope)
4. Once per turn activation. (NOT implemented — out of scope)

## Clauses 3 + 4 (user request 2026-09-13: "Do clause 3 and 4 now") — BUILT, AWAITING IN-GAME TEST
rom_soul_charge.nds sha256 `4998EF8247491CF77239B0F4548884642A2749401D1F25A20FF3DD901F314076`; verify 9/9 PASS;
check_allocations [OK]. CAVE_SC_COND 0x0239EF00 (48 B), CAVE_SC_COST 0x0239EF40 (44 B), CAVE_FREE 0x0239EF70.
cls0 +0C/+10 now CAVE_SC_COND|1 / CAVE_SC_COST|1. KB fact dispatch.activation_turn_locks.
Tests: (6) activate in MP1 -> the Battle Phase cannot be entered that turn; next turn BP works. (7) second Soul Charge
same turn -> not activatable; next turn activatable. (8) MP2 (after BP) -> not activatable. (9) clause 1+2 tests 2-4 again.
(10) a native BP-lock card (e.g. Soul Exchange) and Pot of Duality still behave.
Clause 3: "You cannot conduct your Battle Phase the turn you activate this card."
Clause 4: "You can only activate 1 "Soul Charge" per turn."
Must not regress: clauses 1+2 (in-game confirmed). Native OTN Normal-Spell precedents (ygoprodeck text, cid in card_prop):
- BP lock: Makiu 0x1475, Soul Exchange 0x13EB, ZERO-MAX 0x2276 (+ traps Reinforce Truth 0x20A2, Synchro Material 0x2419).
- 1/turn activation: Pot of Duality 0x2321, Instant Fusion 0x1AF5, Ritual Foregone 0x1AF4, Pot of Benevolence 0x21E0,
  Spell Power Grasp 0x1FC8, Cards for Black Feathers 0x2275.

### Proven (static, stock ov3)
- **Activation-lock tags are cid-keyed turn nodes.** cls0 +0x10 tag 0x021E8181 (Soul Exchange / Reinforce Truth /
  ZERO-MAX / Synchro Material / Stray Lambs) = unless 0x021D2B88(desc): `0x021D2584(desc[+2], cid, 1, desc[+0xC])`,
  return 1. Tag 0x021E8E75 (Pot of Duality / Pot of Benevolence / Spell Power Grasp) is the same with r3 = 0.
- **1/turn check = 0x021F6DD8(desc)**: returns 1 if 0x021D2B88(desc), else 1 iff `0x021A1430(desc[+2], 0xB, cid) == 0`.
  **Pot of Benevolence 0x21E0 is the exact precedent**: multi-select template 0x02235701 + tag 0x021E8E75 + cond
  0x02201C7C, which skips 0x021F6DD8 when desc[+7] != 0 (the template re-checks the condition after the cost).
- **Battle Phase gate = 0x0224CD84(side)**: after a state precheck it returns 0 if `0x021A1430(side, 0xB, X)` finds a node
  for any of 16 cids: 0x0EB7, 0x0EBD, 0x0DDE Speed Spell - Soul Exchange, 0x13EB Soul Exchange, 0x1475 Makiu,
  0x15F0 Thunder of Ruler, 0x173F Saturn, 0x1F9A Ancient Fairy Dragon, 0x204D Skull Flame, 0x20A2 Reinforce Truth,
  0x211C Silverwind, 0x2276 ZERO-MAX, 0x23A6 Scrap Lube, 0x2419 Synchro Material, 0x244A Cards from the Sky,
  0x24B6 Forbidden Arts of the Gishki (literal + base±imm resolved by register tracking). No u16/u32 cid list exists
  (searched arm9 + ov3).
- **Borrowed BP cid = 0x0EBD**: no card_prop, no tsv name, cls0[93] with the BP tag 0x021E8181 (a non-collectible BP-lock
  card). Register tracking of every 0x021A1430 / 0x021A14E8 / 0x021A0950 call in arm9 + ov3 finds only the BP gate
  (0x0224CDB6) keyed on it. Its other literal sites (0x021A90E6, 0x0225B004, 0x0225B2BA) are per-cid `cmp` switches on
  the processed card's cid, not node reads. (Same technique as Cardcar D borrowing Pot of Duality's node — in-game
  confirmed there.)
- **Native BP-lock spells are MP1-only**: Soul Exchange cond 0x021F462C and Makiu cond 0x021F4EDC require
  `[0x0229DD14+0x48] == 2` (phase 2 = MP1, per patch_cardcar_d DUEL_STATE, in-game proven).

### Design
- +0C CAVE_SC_COND: if desc[+7] == 0 { phase == 2 (clause 3) && 0x021F6DD8(desc) (clause 4) }; then native 0x021F03B4.
- +10 CAVE_SC_COST: unless 0x021D2B88(desc): node(side, 0x123D, 1, 0) [clause 4] + node(side, 0x0EBD, 1, desc[+0xC])
  [clause 3]; return 1.

## In-game results (user, 2026-09-13, rom_soul_charge.nds)
User's words: "1. Confirmed 2. Confirmed 3. It did not let me choose more than 3 see .ml3 4. It did not let me
choose more than 3 see .ml3 5. All work." Board for tests 3/4: 6 monsters in GY, 1 monster on the field.
- Test 1 (empty GY -> not activatable): in-game confirmed by user 2026-09-13.
- Test 2 (pick 1 -> 1 summoned, position choice, LP -1000): in-game confirmed by user 2026-09-13.
- Test 5 (Portable Battery Pack / Monster Reborn / Premature Burial regression): in-game confirmed by user 2026-09-13.
- **BUG, tests 3/4: the picker refuses a 4th pick.** GY 6, 4 free Monster Zones, cap 3. Expected "any number"
  (at most 4 here). Tests 3/4 as written (all targets / zone-limited LP) were therefore NOT exercised.

## Confirmed (2026-09-13, static read of the stock ov3 oracle via knowledge.env.load_env)

- **Soul Charge is not in the NDS build** — no row in `otn_enhanced/rom/konami_id_to_card_name.py.tsv`.
- **Soul Charge is not in the 3DS build** — UTF-16 search of
  `3ds_extract/partition0/romfs/duel/card/CARD_Name_E.bin` finds nothing. No reference handler.
- **Native "any number from your GY -> Special Summon" resolver = 0x0221B4E1.** A scan of cls0/cls1/cls2/cls3
  for records with +0x14 == 0x02235701 (the multi-select template) grouped by +0x04 gives 0x0221B4E1 for
  Portable Battery Pack 0x1DDF, Gottoms' Emergency Call 0x205A, Double-Edged Sword Technique 0x1C9B,
  Spirit of the Pharaoh 0x1788, Infernity Launcher 0x2277, Infernity Mirage 0x2254, Doomkaiser/AM 0x1F51.
- **Resolver 0x0221B4E0 phase map.** `ldr r6,=0x0229AAFC ; ldr r2,[r6,#0x70] ; sub r2,#0x78`, jump table at
  0x0221B4FC, `add pc` base 0x0221B4FE:
  - 0x80 -> 0x0221B50E: activation; zeroes [st+0x74]/[st+0x78]; 0x021F0384 check; opens 0x021D28A4; returns 0x7F
  - 0x7F -> 0x0221B56E: SS loop, `i=[st+0x74] < desc[+0x12]` (desc[+0x12] = number of picks);
    pick 0x02234964(desc,i) -> GY index 0x021A2510 -> can-SS 0x021B1E08(side,..) -> summon 0x0226925C
    with r3=2 (r3=0 = forced, only for DEST 0x1C9B and PBP 0x1DDF); a failed pick increments i, returns 0x7F
  - 0x7E -> 0x0221B5F0: post walk; 0x021A241C(pick) `bmi` = not on field; per-cid arms only
  - 0x78 -> 0x0221B660: 0x021D2964 close; returns 0
- **Per-cid arms in 0x0221B4E0** (pool 0x0221B688..0x0221B6B0): 0x205A, 0x2277, 0x1C9B, 0x1DDF, 0x0D77,
  0x1F72, 0x1F51. Any other cid runs the plain "SS each pick, player picks position" path.
- **LP damage call shape** (0x02206138 disassembly): `mov r0,desc ; r1=side ; r2=positive amount ; bl 0x021CFBC8`,
  where side = desc[+2] for the controller and 1-desc[+2] for the opponent. Bracketed by 0x021D28A4 ... 0x021D2964.
- **LP-change table 0x02270798's per-count codes count FIELD monsters** — Just Desserts 0x1301 (k1, -500, code 4),
  Gift of the Mystical Elf 0x137A (k0, +300, code 2). Nothing counts "monsters just summoned" -> clause 2
  needs a stub.

- **KB fact `dispatch.gy_multi_summon_resolver` added** (author_facts.py, VERIFIED; regen self-check 425 PASS / 0 FAIL).
- **Criteria row for "any monster in your GY, Special Summon" = `{cid, 0xFFFF, 0x0223C9D1, 0x00010002}`**, copied
  verbatim from Premature Burial 0x1366 row 115 and Call of the Haunted 0x137D row 119. The handler thunk pushes
  flags `mov r0,#8` (bit 3 SS, own side); Monster Reborn's 0x0223D6E1 is the same thunk with `#0xA` (both GYs).
- **Activation condition = native 0x021F03B5** (no new code): `0x021F0384(desc)` (= 0x021F0114(desc, side) &&
  0x021B9EC0(side, cid)), then `0x02234E78` param + `0x02243FE0(desc[+2]^desc[+6], cid, param) != 0`. It is
  Telekinetic Power Well 0x1F72's condition on this same resolver, and Monster Reborn's 0x021F2BAD tail-calls it.
  Ruled out: 0x021F5E39 (PBP/DEST) needs >= 2 free zones and >= 2 candidates; 0x021F4F8D needs >= 2 candidates.
- **Multi-select without the 0x360-byte clone.** Native prologue 0x02235700 = `push {r3-r7,lr} ; adds r5,r0,#0 ;
  str r1,[sp]`, then the per-cid switch; the tail 0x02235912 starts `ldr r7,[pc,#0x78]` and needs only r4, r5 = desc,
  r6 and [sp]. So an ov5 prologue `push {r3-r7,lr}; adds r5,r0,#0; str r1,[sp]; movs r4,#0x29; <r6 = 0x11D>;
  bl 0x02235912` is enough. LR is already saved, so the BL is a plain jump, and the tail's `pop {..,pc}` returns
  to the real caller. Pair (0x29, 0x11D) = Infernity Launcher's concretely-measured pair (KB) = "SS from GY",
  min 1 / max 35. (Sea Lancer's ov5_cave comment still says prompt 0x4C; the KB and patch constants say Barcha's 0x139.)
- **0x021CFBC8 is DAMAGE, not LP loss**: 0x021CFBC8 computes `target != desc[+2]^desc[+6]` and, when desc[+0xF] != 0,
  runs a per-source-cid modifier switch (0x021D2D40). None of the 120 LP-change-table cards prints "lose ... LP".
- **Donor candidate: Breath of Light 0x123D** (Normal Spell: "Destroy all face-up Rock monsters"). cls0 = 1 record
  {+04 0x022048FD, +08 0, +0C 0, +10 0, +14 0}, no cls1/2/3, 0 criteria rows, **exactly 1 raw u16 hit for 0x123D
  across arm9 + ov3 + ov5** (its own cls0 row). No finished_patches reference except patch_bulk_card_pack's rarity row.
  Runner-up: Raimei 0x12E9 (2 hits).
- **Unclaimed phantom criteria cids** (in the table, not in card_prop, not in PHANTOM_CLAIMS; stock image): 0x12D6,
  0x1445, 0x14BA, 0x14D7, 0x0E34.. (full list from the session), 0x0EA8 x2. Only the stock image was checked; the
  chained image still needs checking.

- **User decisions 2026-09-13:** donor = Breath of Light 0x123D; clause 2 = "do what Premature Burial does".
- **Premature Burial's LP payment = 0x021CF924(side, amount)** (KB `dispatch.lp_pay_primitive`, VERIFIED).
  PB cls0[241] +0x10 = 0x021E4D81 -> amount 0x021E48D4(desc) -> default tail 0x021E4E5A
  `adds r0,r5(side = desc[+2]^desc[+6]) ; adds r1,r6(amount) ; bl 0x021CF924`. The primitive skips amount 0, clamps,
  and posts duel command 0x24 through 0x021C3BC8 — no damage-modifier switch. Clause 2 calls it with 1000 x n.
  (This closes the "lose LP" open question; the damage routine 0x021CFBC8 is NOT used.)

- **Phantom criteria row to drop = 0x12D6** (stock row 86 / chained row 85: {0x12D6, 0xFFFF, 0x0223C9D1, 0x90010002}).
  No tsv name, no card_prop, NOT in list A (u16 region 0x0227134C..0x022713C4) in stock or chained ov3, single row.
  0x123D would insert at bisect index 81 (after 0x1232), so rows 81..85 shift by one.
- **0x021A241C(ref) = field-only locator**: loops side 0..1 and slot 0..10 over `player+0x34` (stride 0x14), matches
  the packed ref, returns `side | slot<<8`, else `mvns r0,#0` = -1. So a pick still in the GY reads negative, and
  "count picks with 0x021A241C >= 0" = monsters that actually landed.
- Card text writer for a Spell donor = `card_text.apply_to_rom(out, cid)` + a CARD_TEXT entry (Shien's Dojo / GDW
  precedent), not `apply_stats_and_text` (that one needs monster stats).

- **Savestate rom_soul_charge.ml3 (RAM offset 0x24, validated by finding resolver 0x0221B4E0's bytes at file 0x21B504):**
  the ov5 SELECT stub is resident; picker state 0x0229944C = {h+2 mode 0x29, h+6 candidates 6}; [0x0229AB7C] substep 2.
- **CPU auto-select max getter 0x0219C4B0** (sole BL caller 0x0226C1B6, which pre-selects picks 0..max-1 via
  0x0219C504 / 0x0219C88C): mode <= 5 -> 0; mode 0x26 / 0x47 / 0x48 -> all candidates (<= 0x80); 6 < mode < 0x26 ->
  mode-6; 0x27 < mode < 0x47 -> mode-0x27; result clamped to candidates [state+6]. Consistent with the printed counts:
  Psychic Path / Infernity Launcher 0x29 "up to 2", Burial from DD / Backup Soldier 0x2A "up to 3", Barcha 0x47 "any number".

## Ruled Out
- **KB `dispatch.multiselect_target_template` "max picks = r4 - 6" (hence 0x29 = max 35)**: falsified in-game
  (the user was capped at 3). The template does queue r4-6 through 0x0219A7F8, but that is not what limits the picks.
- **"The human pick cap is 0x0219C4B0"**: falsified by measurement. It gives 2 for mode 0x29, the user got 3, and its
  only caller is the CPU auto-select path. The HUMAN picker's cap mechanism is UNMAPPED (strike 2 -> stop, use precedent).
- **Finding a plain "lose LP" primitive via the cost path (2 probes).** Krebons' cost tag 0x021E780C hands off to
  the cost state machine (0x021E50DC / 0x021E4D80); nothing pays inline. Delinquent Duo 0x1325's resolver 0x0220E108
  never touches LP (its "Pay 1000" is also a cost tag). Stopped here per the two-strike rule; the decision goes to the user.
- Reusing an LP-change table row for clause 2 (the codes count the wrong thing — see above).
- Portable Battery Pack / Gottoms' Emergency Call / the other five arm cids as donors: all are per-cid
  special-cased inside 0x0221B4E0.

## Open Questions
- The picker max is 35, not the free-zone count; excess picks aren't summoned (the resolver loop checks free zones
  via 0x021AD870) and aren't charged LP. Real Soul Charge can't target more monsters than there are free zones.
- Is the phantom criteria row (e.g. 0x12D6) still present in the CHAINED image, and is it outside list A?

## Round 2 build (user approved 0x47, 2026-09-13) — TESTS 3+4 PASS
User's words: "Okay, both those tests pass now. And are as described". Test 3 (4+ picks, 4 summoned, LP -4000)
and test 4 (more picks than free zones -> extras not summoned, not charged): in-game confirmed by user 2026-09-13.
=> Clauses 1+2 in-game confirmed by user 2026-09-13 (tests 1-5 all pass on sha256 259D2095...9239).
Clauses 3 (no Battle Phase) and 4 (once per turn) are NOT implemented. Not wired into the chain (needs user approval to ship).
COUNT_CODE 0x29 -> 0x47 (the only change). verify 7/7 PASS. rom_soul_charge.nds sha256
`259D2095F184CADD4BE2D03855A0C569431BEF86A085B42EB4268E2849ED9239`. Old round-1 savestates (.ml1-.ml3) are from the 0x29 build.
Re-run tests 3 and 4: GY 6, 1 monster on field -> can 4+ be picked? Pick 4 -> 4 summoned, LP -4000. With fewer free
zones than picks -> extras not summoned and not charged.

## Proposed fix (approved — see Round 2 build)
Use Dragunity Knight - Barcha 0x221B's native count code **0x47** (its printed text is "any number"; cls1[1166] runs
the same template 0x02235701). patch_sea_lancer already ships 0x47 (MULTI_COUNT_CODE) for its "any number" equip.
Change COUNT_CODE 0x29 -> 0x47 and keep prompt 0x11D. Unexplained: why 0x29 gave 3 rather than 2 for a human.
Caveat: Sea Lancer's own in-game notes only show 2 picks, so >3 picks under 0x47 is not yet proven in-game either.

## Clauses 3+4 in-game confirmed (user, 2026-09-14, rom_soul_charge.nds sha256 4998EF82...314076)
User's words: "6. Confirmed 7. Confirmed 8. Confirmed 9. Confirmed 10. Confirmed. Update the
knowledge base and ship it!" -- confirmed against the test list this same findings doc specifies
(Round 2 build section, tests 6-10):
- Test 6 (activate in MP1 -> Battle Phase locked that turn; next turn BP works): in-game confirmed.
- Test 7 (second Soul Charge same turn refused; next turn activatable): in-game confirmed.
- Test 8 (MP2 after a Battle Phase -> not activatable): in-game confirmed.
- Test 9 (re-run clause 1+2 tests 2-4: 1 target / 4+ targets / more targets than free zones,
  no regression from clauses 3+4): in-game confirmed.
- Test 10 (native BP-lock card Soul Exchange and Pot of Duality still behave normally,
  i.e. clause 3's borrowed node 0x0EBD and clause 4's tag reuse don't interfere): in-game confirmed.

=> All four printed clauses in-game confirmed by user. SHIPPED 2026-09-14: wired into
apply_all_patches.PATCHES and otn_enhanced.steps.STEPS (patch_soul_charge, no
MIGRATED entry -- runs the original module in both chains).

## Next Experiment (in-game, user)
Normal duel (ov5 must be resident; not a puzzle), rom_soul_charge.nds, "Soul Charge" in hand:
1. Empty GY -> Soul Charge must NOT be activatable.
2. 3 monsters in GY, empty field -> activate, pick 1 -> 1 summoned, position choice offered, LP -1000.
3. Same, pick 3 -> 3 summoned, LP -3000.
4. Only 2 free Monster Zones, pick 3 -> expect 2 summoned and LP -2000 (known gap: the picker allows more targets
   than free zones).
5. Regression: Portable Battery Pack / Monster Reborn / Premature Burial still work.
If anything misbehaves, a savestate at the moment is the fastest diagnosis.
