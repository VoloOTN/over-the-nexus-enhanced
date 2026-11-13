# Masked HERO Dark Law — findings

Started 2026-09-28. Status: C1 IN-GAME CONFIRMED BY USER 2026-09-28 (all 7 oracle items, rom_dark_law.nds sha256 ffe29eee...ede18c).
NOT shipped (not in steps.STEPS) -- awaiting user approval. C2 / C3 not implemented.
Test ROM must also carry Elemental HERO Shadow Mist (user request 2026-09-28) — it already ships in
steps.STEPS (step 77/80), and Dark Law is the DARK Masked HERO its deferred item 7 (Mask Change target)
was waiting on.

Printed text (scratch/ygoprodeck_cache.json, id 58481572): "Must be Special Summoned by "Mask Change".
Any card sent to your opponent's GY is banished instead. Once per turn, if your opponent adds a card(s)
from their Deck to their hand (except during the Draw Phase or the Damage Step): You can banish 1 random
card from your opponent's hand."
DARK / Warrior / Fusion / Lv6 / 2400 / 1800. Archetype HERO.

Clauses:
- C1 summon condition: Must be Special Summoned by "Mask Change".
- C2 continuous: any card sent to your opponent's GY is banished instead.
- C3 trigger (OPT, "You can", "if"): opponent adds card(s) Deck->hand outside Draw Phase / Damage Step
  -> banish 1 random card from opponent's hand.

## Confirmed
- Not in the NDS ROM (konami_id_to_card_name.tsv: only Masked Hero Goka 0x236B, Vapor 0x236D,
  Mask Change 0x236A). Not in the 3DS build either (CARD_Name_E.bin "Masked HERO": Goka, Vapor, Acid,
  Dian only) -> no Konami implementation to transplant; Goka/Vapor are the native Mask Change targets.
- Used effectless Fusion donors (notes/donor-pool...): Bracchio-raidus, Humanoid Worm Drake, Gaia,
  Meteor Black Dragon, Crimson Sunbird (+ Twin-Headed Thunder Dragon, Junk Speeder).

- User 2026-09-28: scope = C1 only.
- (all below: disasm of rom_all_patches.nds, scratchpad dl.py, 2026-09-28)
- Mask Change 0x236A: cls0[1226] {0x02225571, 0x021E1E89, +0C 0x021F8549, 0, +14 0x02234E21}
  (resolver + +08 shared with NEX 0x1BFA). Criteria row [1251] {0x236A, aux 0x6B, 0x02243079, 0x802}.
- 0x02243079 -> walker 0x0223BE40 with per-candidate predicate 0x02243040:
  `bl 0x02024058` (Masked HERO thunk) && attribute(0x0202ABC8(cid)) bit in mask [sp+0xc]. NOTHING per-cid.
- Set code 0x6B "Masked HERO": ptr table 0x0209D0D8[0x6B] = thunk 0x02024059:
  `ldr r1,=0x0209C572 ; ldr r3,=bsearch ; movs r2,#2 (@0x0202405C) ; bx r3`, literal @0x02024060.
  List 0x0209C572 = [0x236B Goka, 0x236D Vapor]. HERO composite 0x020239AC also reads it
  (literal @0x020239EC, `movs r2,#2` @0x020239B0; `movs r4,#2` @0x020239B2 feeds the NEXT list, untouched).
  Only literal refs to 0x0209C572 anywhere (ARM9+ov3+ov5): 0x020239EC, 0x02024060.
- Packed neighbours: 0x0209C56C HERO [0x1A81 Hero's Bond] cnt1 | 0x0209C56E set 0x26 [0x1C39] cnt1 |
  0x0209C570 set 0x35 "Nitro" [0x1E35 Nitro Warrior] cnt1 (thunk 0x02023BD8, only ref = ptr table
  0x0209D1AC) | 0x0209C572 Masked [2] | 0x0209C576 next list. No room to grow in place.
- bsearch 0x02022E14 returns exactly 1/0 (movs r0,#1 / movs r0,#0), ldrsh compare.
- Goka/Vapor per-cid references: class-5 list 0x0209BA2C/2E, Masked list, Goka ATK leaf 0x021B53B0,
  ov5 stock {cid,u16} table 0x023983F8..0x02398610 (134 rows; Goka 0x10, Vapor 0x08; no direct ptr ref).
- Fusion classifier 0x02023228: class 5 list 0x0209BA28 [0x1C06,0x1D11,0x236B,0x236D] (literal 0x020232A0,
  cnt 0x02023252); class 3 list 0x0209BA18 [0x0EA1,0x0EA2,0x1C55,0x1C5F] ALL PHANTOM (literal 0x020232A8,
  only ref), class-3 leaf `movs r0,#3` @0x02023282. Callers: 0x0223BF50 / 0x0223F744 (>1 -> excluded,
  Poly-type fusion), 0x0223FFCE (>2), 0x02240172 (==2), 0x022686F0 (>=4 skip -> 3 and 5 DIFFER),
  0x020233E2 (0/4 ok), 0x02023446 (0 ok), 0x02023354 jump table (0..3 -> 1, 4/5 -> 0 -> 3 and 5 DIFFER).
- Donor candidates in OTN (Lv6 effectless Fusion): Rabid Horseman 0x1002 (extra u32 hits 0x021E1E78 /
  0x0206A5B8), Aqua Dragon 0x1160 (ONLY binding = fusion recipe A[28] @0x02270C74), Steam Gyroid 0x18FA
  (ARM9 hit 0x0209CD20 in set lists). donor_scan 2026-09-28. Warrior of Tradition / Empress Judge etc.
  are not in OTN.

- User approved donor Aqua Dragon 0x1160 + plan 2026-09-28.
- Classifier 0x02023228 arm order (disasm): class1 0x0209BCD4 #0x26 | class4 0x0209BB82 #0x15 |
  class5 0x0209BA28 #4 (also sets r4=4) | class2 0x0209BA50 #6 | class3 0x0209BA18 count r4=4 |
  fallback 0x02023050 -> r4 (4) else 0.
- card_prop: Goka = FIRE (attr enc 4), Vapor = WATER (3), both Fusion Effect / Warrior / Lv6.
  ov5 table 0x023983F8 values are 1<<attr (Goka 0x10, Vapor 0x08) -> a {cid, attribute bit} table.
- BUILT 2026-09-28: patch_masked_hero_dark_law.py via _build_masked_hero_dark_law.py ON TOP OF
  rom_all_patches.nds (sha ef97d96d..., includes Shadow Mist) -> rom_dark_law.nds
  sha256 ffe29eeeae7afc59b9bcf1caaa3f680a5ab56e1f3a97fbd9835bef46d2ede18c. check_allocations clean,
  ledger emitted, verify() 13/13 PASS (static). NOT in steps.STEPS.
  EXECUTION PROOF (scratchpad nitro_exec.py, thumbemu on the built ARM9): Nitro thunk true for
  {0x1E35} only; Masked HERO thunk 0x02024058 true for {0x1160,0x236B,0x236D} only (all 0x4000 cids);
  HERO composite 0x02023974 true for 0x1160; classifier -> 5 for 0x1160 / Goka / Vapor.
  IN-GAME (user, verbatim 2026-09-28): "1. Confirmed 2. Confirmed 3. Confirmed 4. Confirmed 5. Confirmed
  6. Confirmed 7. Confirmed" -- all 7 items in-game confirmed by user 2026-09-28. Also closes Shadow
  Mist's deferred item 7 (Mask Change targets Shadow Mist -> Dark Law).

### C2 (session 2, 2026-09-28 — disasm of rom_all_patches.nds, scratch/dl_dis.py + dl_scan.py)
- User 2026-09-28: scope = C2.
- 3DS: Macro Cosmos has only its Helios-search criteria row (0x004A65EC, 0x802); Dim Fissure / Banisher of
  the Radiance have no registry rows -> the replacement is NOT a record, it is a hardcoded field scan.
- **FIELD SCAN 0x021BA82C** (ov3) returns a mask, player P's half = bits (P*16)..(P*16+15). Per player
  (loop r4=0,1; gated by 0x021BABE8), each arm = 0x021AC0C8(r0=r4, cid, r2=-1) ["cid face-up on r4's
  field", KB summon_event_dispatch 0x021B95E0 probe] or rider 0x021A1430(r4,0xB,key):
  bit 1: Banisher of the Light 0x1332 (lit 0x021BA8E0), Banisher of the Radiance 0x1A27 (lit 0x021BA8DC),
         Macro Cosmos 0x1A1A (= lit-0xD, [sp])
  bit 2: Dimensional Fissure 0x1A33 (= lit+0xC, [sp+4]) — explains why 0x1A33 has no literal anywhere;
         rider kind 0xB key 0x23C2 Different Dimension Ground (lit 0x021BA8E4)
  bit 4: cid 0x1444 (lit 0x021BA8E8, ONLY reader = ldr @0x021BA8B6; bl 0x021AC0C8 @0x021BA8BC).
         0x1444 has NO card_prop row (donor_scan 0x1444) -> PHANTOM; this arm is inert in stock OTN.
  r7 == 1 for the whole loop (0x021BA844..48 set it; loop body never writes r7).
- **REPLACEMENT DECISION 0x021BA94C**(r0=victim side, r1=isMonster 0x02029E60, r2=&out) returns 0 =
  "banish instead" when, for either half P: bit1 set; or bit2 && monster; or **bit4 && P == victim side**.
  *out = (P != victim) (the replacer is the other player).
- Consumers of 0x021BA94C (all four do `if dest==0x0E && !ret: dest=0x0F`): general core 0x021C6B92,
  0x021CCB50, 0x021D1DAC mover @0x021D1E4C, 0x021D236E.
  Core uses out: dest==0x0F && out!=0 -> sets 0x10 in the move word's top byte (@0x021C6BEA..BFC).
- "Can go to GY" check 0x021BA910(side, isMonster): 0 if any half bit1; any bit2 && monster;
  bit (4 << side*16). ~100 callers (costs etc). Also 0x021B0B0E and ov5 AI 0x022EB19A read the mask the
  same way (bit1 either half / 0x4 test).
- => SEMANTICS OF BIT 4 IN HALF P: "P's own cards that would go to the GY are banished".
  C2 = set bit 4 in P's half when P's OPPONENT has Dark Law face-up:
  literal 0x021BA8E8 0x1444 -> 0x1160, and @0x021BA8B8 `adds r0,r4,#0` (20 1C) -> `subs r0,r7,r4`
  (38 1B) = 1 - r4 = opponent. Pure ov3, 6 bytes, no ov5 (puzzle-safe). PROPOSED, NOT BUILT.
- Known gap: out-flag will be 0 (bit4 path compares P == victim) though the replacer is the opponent;
  the 0x10 move-word flag is then not set. Consumer of that flag UNKNOWN.
- User 2026-09-28: approved building C2 ("Find out what reads it while building it"). Question A
  (opponent can't pay send-to-GY costs, same as Macro Cosmos via 0x021BA910) NOT answered yet.
- BUILT 2026-09-28: PART E in patch_masked_hero_dark_law.py; claim ("gy_banish_scan_bit4", 0x1444) in
  PHANTOM_CLAIMS, ledger emitted (346 phantom claims). _build_masked_hero_dark_law.py on rom_all_patches
  (ef97d96d...) -> rom_dark_law.nds sha256 c1739d57259f255cfea13740497bb99b4f077a6f03dd8636e6c1a1523c530199,
  verify 16/16 PASS (static). C2 in-game confirmed by user 2026-09-28 (all 6 items, below).
- Out-flag origin: core 0x021C6B00 initialises [sp+0x2c] = (r5 mover-side != card side [sp+0x24])
  ^ (flags & 1) @0x021C6B36..44 BEFORE the replacement; 0x021BA94C only overwrites it when a
  replacement fires. dest==0x0F && flag -> move word [sp+0x28] |= 0x10000000 (bit 28), then the word
  goes to 0x021D1300 (@0x021C6CB8) and 0x022391CC (@0x021C6CC4). Mover 0x021D1DAC does the same
  (@0x021D1E9E..B0).
- Move word layout (0x021D1300 decode @0x021D1310..42): bits 0-8 index, 9 side, 10-13 src zone, 18 flag,
  19-22 dest zone, 28 = "BANISHED BY OPPONENT" (above), 31 side.
- 0x022391CC appends (code byte, word) to a MOVE LOG: count [0x0229AB7C+0x30] (cap 0x20), codes
  0x0229ABB4+i, words 0x0229ABD4+4i.
- **THE BIT-28 READER = Dimensional Inversion 0x1B01** ("Activate only when a monster(s) you own is removed
  from play by an opponent's effect. Special Summon 1 of those monsters."): criteria row 477 @0x02272A20 in rom_all_patches (stock index 485)
  {0x1B01, 0xFFFF, 0x0223F7F9, 0} (3DS main_effect [421] same shape). Handler 0x0223F7F8 walks the move
  log, codes 0x1D..0x20, dest == 0x0F AND bit 28 (@0x0223F824..32), monster, owner == r5, still banished
  -> 0x02243B2C marks it selectable. Found by pattern scan of ARM9+ov3+ov5 for bit-28 extraction
  (lsl3/lsr31, lsr28/lsl31, lsr24 + #0x10, 1<<28): the only non-writer hit on a move word is
  0x0223F82C. Scan is pattern-based, NOT an exhaustive proof that nothing else reads bit 28.
- CONSEQUENCE of the built patch: 0x021BA94C's bit-4 path writes out = 0, which OVERWRITES the core's
  initial flag. So a Dark-Law-replaced banish never carries bit 28 -- even when Dark Law's controller's
  own effect did the sending (initial flag was 1). Opponent's Dimensional Inversion can't use it.
  Macro Cosmos controlled by the non-owner writes out = 1.
- FIX CANDIDATE (not built): 0x021BA980..0x021BA989 (10 B: movs r6,#4; tst r3,r6; beq 99E; cmp r5,r2;
  bne 99E) -> lsls r6,r3,#29; bpl 0x021BA99E; cmp r5,r2; bne 0x021BA99E; b 0x021BA992 (movs r2,#1;
  str r2,[r4]; [sp]=0). r6 is scratch (reloaded at 0x021BA96A each iteration); all four callers pass a
  non-null out (add r2,sp,#..: 0x021C6B90, 0x021CCB4E, 0x021D1E4A, 0x021D236C). Bit 4 is Dark Law-only
  after PART E, so nothing else changes.
- User 2026-09-28 decisions: (1) Dimensional Inversion bit-28 fix: "No" -> the gap is USER-ACCEPTED, fix
  not built. (2) opponent can't pay send-to-GY costs while Dark Law is face-up: "Yes, that is expected".
- IN-GAME (user, verbatim 2026-09-28, rom_dark_law.nds c1739d57...): "1. Confirmed 2. Confirmed
  3. Confirmed 4. Confirmed" -> C2 oracle items 1-4 (battle / Spell / discard-mill banished; own cards
  still to own GY) in-game confirmed by user 2026-09-28. Then (verbatim) "5. Confimed 6. Confirmed" -> items 5 (Dark Law
  leaves -> GY again) and 6 (C1 regression) in-game confirmed by user 2026-09-28. C2 COMPLETE. NOT shipped.

### C3 (same session, user 2026-09-28: "Go with Clause 3 now") — disasm of rom_all_patches.nds
- Precedents in OTN: trigger Drastic Drop Off 0x1D31 cls0[915] cond 0x021FD659 (code 0x1B|0x1C, event
  word bit 9 side != desc[+2], src zone bits 11-14 == 0x0D Deck); Appropriate 0x1353 cond 0x021F4009
  (code 0x1B, opp side, [0x0229DD14+0x48] != 0 = not Draw Phase). Magic Hand / Harr not in OTN or 3DS.
  Effect: Lightforce Sword 0x12C8 (face-down, cls0 0x0220C8C9) and D.D. Designator 0x16D3 (0x02219E79).
- EVENT CODES: 0x1B = draw (logged only @0x021D0C3A, draw handler), 0x1C = Deck->hand add (logged
  only @0x021C743E inside the Deck->hand mover 0x021C72CC). Enumerated every bl 0x022391CC.
- **Draw/add events reach FIELD monsters only through cid-keyed posters**, not a generic scan:
  0x021D3438(side, cid, code, arg) scans side's field (mzones 0-4 if monster, else 5-10) for face-up cid
  (0x021AC004) and posts a cls1-selector event (bit 21). Draw handler posts code 0x1B to the drawer's
  OPPONENT for 0x1AC7 (lit 0x021D12EC, ldr @0x021D1282, bl @0x021D1288) and Naturia Ragweed 0x2212
  (lit 0x021D12F0) -- Ragweed's cls1[1161] has cond 0 because the poster is the filter. Appropriate:
  0x021D3230 over zones 5-9. Silent Magician LV4 0x1817: rider in the same handler.
  Deck->hand mover posts 0x1C only to Puppet King 0x1A43 in the HAND (0x021D36C0 @0x021C742A) and
  0x021D3438(adder, 0x20D2, 0, 0) @0x021C7436 -> NO field poster for opponent Deck->hand adds.
- 0x1AC7: no card_prop (PHANTOM). cls1[598] {0x1AC7, 0x02223451, 0, 0x021FB691, 0x021E51E5, 0x0223868D}
  (a cut optional draw trigger). 0x02223450 (->0x02223504, 180 B) and 0x0223868C (->0x022386F0, 100 B)
  have NO bl callers and their only pointers are that record (0x022898E8/F8) -> reclaimable ov3 space
  once the record is dropped (branch-into check still TODO).
- Random pick: 0x022599F8(side, 0) -> index at u16[0x0229DE94+6]; face-up banish from hand:
  0x021C6E4C(side, &P(side)+0x124+idx*4, r2=1 "by opponent's effect") (D.D. Designator @0x02219F3A).
- ov3 dead ledger: ~18 B free total -> not enough; 0x1AC7 bodies would be.
- DAMAGE STEP: phase field is 3 for the whole Battle Phase. "During the Damage Step" conds
  (0x021F522D, 0x021FDDDD) key off EVENT codes 0x0E/0x15 + battle record 0x02298AD8 (+2 s8 flag,
  +0 attacker side, +8 zone). No persistent "in Damage Step" flag found yet -> UNPROVEN.
- User 2026-09-28: Q1 draws count ("Yes": a draw by card effect outside the Draw Phase triggers C3).
  Q2 answer "Yes" is AMBIGUOUS (asked (a) savestates vs (b) accept deviation) -> re-asked.
- MISS-TIMING: thumbemu run of 0x021EE0E0 on rom_all_patches: cid 0x1160 ends at node 0x021EE10C
  (Shadow Mist's hooked node) -> 0x021EE296 log walk; controls 0x111F / 0x1E1B -> 0x021EE27E never.
  DECISION: don't touch Shadow Mist's block; post with arg & ~0x1FF instead (Assault Synchron
  precedent, timing.miss_timing_test: low 9 bits 0 -> never miss).
- 0x02223450..0x02223504 (0x1AC7 resolver + pool): branch/BL/ldr-literal scan over ARM9+ov3+ov5 finds NO
  reference from outside -> reclaimable once cls1[598] is dropped. 0x0223868C range is NOT (0x022387B4
  loads a literal at 0x022386E0).
- Face-up banish from opp hand = 0x021C6E4C(opp, &hand[idx], 1) (Lightforce's face-down uses 0x81/0xC1;
  bit 0 = by opponent). Lightforce returns 0 after it. 0x021BABE8 = "banishing allowed" gate.
- Mover 0x021C72CC skips its own posts when [0x0229C294+0x78] bit0 (bne @0x021C73B4).
- Custom cls1 +10 needs a timing_class_hook arm (ARM_JW shape, desc[+5]==1 -> 0x021E51E5); the shared
  stub is already installed in rom_all_patches, so the Dark Law build rewrites it in place (verified
  equal to stub(ARMS) first) and timing_class_hook.py is NOT edited until ship.
- PLAN (building): F cls1 {0x1160,0, RES, 0, COND, SLOT4, 0} dropping 0x1AC7's row; G lit 0x021D12EC ->
  0x1160 + bl @0x021D1288 -> ov3 S_DRAW (clear low 9 bits, bl 0x021D3438); H bl @0x021C743E -> ov3
  S_ADD (log, then unless mode bit post (1-r5, 0x1160, 0x1C, r7 & ~0x1FF)); J ov5 COND/SLOT4/RES;
  timing arm.
- BUILT 2026-09-28: rom_dark_law.nds sha256 c52716a2335b5db387f67d0b5143b24207c51220b7adfc4d2defa865f91916c1
  (on rom_all_patches ef97d96d...), verify 27/27 PASS (static). cls1: 0x1AC7 @598 dropped, 0x1160 @74.
  ov3 S_DRAW 0x02223450 (16 B) / S_ADD 0x02223460 (48 B); ov5 COND 0x023A2048 (76 B), SLOT4 0x023A2098
  (32 B), RES 0x023A20C8 (120 B); CAVE_FREE -> 0x023A2140; shared timing stub rewritten 180 -> 204 B
  (arm local to the patch module). Ledger: 310 ov5 slots, 348 phantom claims, ov3 134 B free.
  Every stub disassembled and matches intent (scratch/dl_c3_disasm.py). NOT executed (no savestate with
  Dark Law). C3 AWAITING IN-GAME TEST (oracle C3-1..8 in _build_masked_hero_dark_law.py).
  NOT IMPLEMENTED: Damage Step exclusion.
- IN-GAME (user, verbatim 2026-09-28, rom_dark_law.nds c52716a2...): "1. Confirmed 2. Confirmed
  3. Confirmed 4. Confirmed 5. Confirmed 6. Confirmed 7. Confirmed 8. Confirmed  Ship it" -> C3 oracle
  C3-1..8 in-game confirmed by user 2026-09-28. Damage Step question (a)/(b) never answered: the
  exclusion remains NOT IMPLEMENTED (open, not user-accepted).
- SHIPPED 2026-09-28 (user: "Ship it"): steps.STEPS step 78/81 + _verify_all_patches.SHIPPED;
  timing arm moved into timing_class_hook.ARMS; Aqua Dragon moved to "Used as donors". EE build 81/81
  -> rom_all_patches.nds sha256 c52716a2335b5db387f67d0b5143b24207c51220b7adfc4d2defa865f91916c1
  (== the confirmed test ROM, byte-identical). Sweep: 66 passed, 1 failed = patch_ninishi, which fails
  identically on the pre-Dark-Law ROM (rom_all_patches_pre_darklaw.nds) -> pre-existing, not this ship.

## Ruled Out
- 0x236C as Dark Law's own phantom: its only hit 0x021787E8 is ARM code.
- Growing Masked / class-5 lists in place (packed) or in an ARM9 cave (none; dragunity-remus findings).

## Open Questions
- ov5 table 0x023983F8 consumer (AI?). Not needed for player-driven Mask Change.

## Plan (C1, proposed 2026-09-28, awaiting approval)
- Donor Aqua Dragon 0x1160 -> card_prop DARK/Warrior/Lv6/2400/1800 Fusion Effect, card_text, recipe A[28] kill (Junk Speeder PART C).
- Masked HERO list -> 0x0209C570 = [0x1160, 0x236B, 0x236D] cnt 3 (both literals + both counts).
- Nitro thunk 0x02023BD8 rewritten as direct compare r0 == 0x1E35 (frees 0x0209C570).
- Fusion class 3 retagged to class 5 (@0x02023282 movs r0,#5); class-3 list drops phantom 0x1C55 for 0x1160.

## Next Experiment
- HANDOFF 2026-09-28: PROMPT_masked_hero_dark_law_clause2_3.md. C2 next: find how native "banished
  instead" cards (Macro Cosmos 0x1A1A, Dimensional Fissure 0x1A33, Banisher of the Radiance 0x1A27 --
  cids from konami_id_to_card_name.tsv, mechanism UNVERIFIED) redirect GY -> banished; C3 candidate
  precedent Thunder King Rai-Oh 0x1CE5 (HYPOTHESIS). Nothing on C2/C3 proven yet.
- User in-game run of the 7-item oracle in _build_masked_hero_dark_law.py on rom_dark_law.nds
  (sha256 ffe29eee...ede18c). If Mask Change does not offer Dark Law on Shadow Mist: savestate at the
  Mask Change prompt; check attribute mask [sp+0xc] and the walker 0x0223BE40 mode.
- KB: setcode.masked_hero_0x6b + dispatch.mask_change_target_predicate VERIFIED; card.masked_hero_dark_law
  UNVERIFIED (verify_knowledge 511 PASS 0 FAIL).
- On ship: steps.STEPS + _verify_all_patches.SHIPPED; verify(base=) must then be the pre-step ROM, not stock
  (its whole-cid diff compares against `base`). Move Aqua Dragon to "Used as donors" in the donor-pool note.
