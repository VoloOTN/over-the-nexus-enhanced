# Brilliant Fusion — findings

Status: SHIPPED 2026-09-27. C3 in-game confirmed by user 2026-09-27 on build 5 (sha 1965d2e4...587a91), all six
items ("1. Confirmed ... 6. Confirmed / Ship it!"). C1/C2/C4 in-game confirmed by user 2026-09-25.
Ship: steps.STEPS row "Temple of the Sun -> Brilliant Fusion (the whole card)" + _verify_all_patches.SHIPPED;
summon_rider_hook.LATCH_ARMS now carries the BF arm (chain hook 0x02268666 -> CAVE_RIDERLATCH), so Jet Synchron /
Jet Warrior / Remus now pass through the latch prefix first (miss path -> shared stub; offline-simulated, not re-tested
in-game). EE build 78/78, rom_all_patches.nds sha256 74556a6db5548b69833fc44aacb30a0c0c0acfbddd3f9cce55494b8bd896f1ae.
Sweep 63 passed / 1 failed = patch_ninishi (PRE-EXISTING, Scrap Raptor C1b lifts its hooks). patch_infernity_barrier's
verify compared the donor cls0 row POSITIONALLY against clean and broke on BF's cls0 shift -> fixed to look up by cid
(ROM bytes were correct: +04 0x022062F9 / +0C 0x021F5F95).
Earlier: C1 + C4 IN-GAME CONFIRMED BY USER 2026-09-25 on build 3 (sha a28299d8...fb82e3): Deck-only material
prompts, both picked Deck materials to GY, ATK/DEF 0, no regression in Polymerization / Gem-Knight Fusion / Future
Fusion; 1-per-turn and card text confirmed in test 1. NOT shipped (not in steps.STEPS) -- awaiting user decision.
C2 (leaves field -> destroy) and C3 (discard Spell -> regain ATK/DEF) not built.
History: C1 + C4 in scope (user-approved 2026-09-25). DONOR = Temple of the Sun 0x21D5 (user-approved 2026-09-25;
needs count-neutral cls0 insert + 2 criteria-row inserts). Step 2 (reachability) in progress. No code written.

Printed text (scratch/ygoprodeck_cache.json, race = Continuous Spell):
> When this card is activated: Fusion Summon 1 "Gem-Knight" Fusion Monster from your Extra Deck, using
> monsters from your Deck as Fusion Material, but change its ATK/DEF to 0. If this card leaves the field,
> destroy that monster. Once per turn: You can discard 1 Spell; the monster Special Summoned by this card's
> effect gains ATK/DEF equal to its original ATK/DEF, until the end of your opponent's turn. You can only
> activate 1 "Brilliant Fusion" per turn.

- C1 Deck-material Gem-Knight Fusion Summon, ATK/DEF -> 0   [IN SCOPE]
- C2 leaves field -> destroy that monster                   [later]
- C3 OPT discard Spell -> gains original ATK/DEF             [later]
- C4 hard OPT activation                                     [IN SCOPE]

3DS: Brilliant Fusion is NOT in 3ds CARD_Name_E.bin (checked 2026-09-25; Gem-Knight pool is). No Konami handler.

## Confirmed (static disassembly of ygo_tools/reference_files, 2026-09-25; NOT in-game)
- Fusion-spell cls0 record shared: {+04 resolver 0x02232CFD, +0C cond 0x02232CB1}; Gem-Knight Fusion 0x22D6 = cls0[1195] @0x02285654. (Explore agent read; re-read before relying.)
- Gem-Knight Fusion criteria row 0 = target: fn 0x0223ED09, aux 0x0054, word 0x802 (row @0x02274BE0). Row 1 = material pool fn 0x0223C939 word 0x02 (shared by all Fusion spells).
- Gem-Knight set code index = 0x54: thunk 0x02023EB5, list 0x0209C7F8 (12 cids 0x22BD-C0, 22CF-D1, 22D6, 23FC, 249C, 24AE, 24AF).
- Mode classifier 0x022325B4(cid): compiled cid switch (disassembled this session). Only mode-2 arm = 0x0223264A
  (`movs r0,#2`), reached by `bge` at 0x022325BA when cid == literal [pc+0xb4] (= 0x1A7E Future Fusion per agent).
  => no data retarget; donor needs an ov5 hook returning 2. Default arm 0x02232666 returns 0.
- Zone rule 0x022321D8 (jump table 0x02232248): mode 2 arm @0x022322CC accepts only zone 0xD (Deck). (agent read)
- Material destination 0x02232684(cid): default 0xE (GY) — correct for Brilliant Fusion. (agent read)
- Future Fusion 0x1A7E: Continuous Spell, mode 2, OWN resolver/cond {0x02233981, 0x022338E9} (delayed summon).
- C4 precedent (Soul Charge, confirmed in-game by user 2026-09-14): query 0x021A14E8(desc[+2],0xB,cid,1) in cond slot;
  stamp 0x021D2584(side,cid,1,0) in cost slot +10; guards 0x021D2B88(desc) / desc[+7].

## Donor evidence (donor_scan + static read, 2026-09-25)
Ranked all Continuous Spells by binding cid occurrences (scratchpad rank_spells.py). Neither pick below is in steps.py.
- The Second Sarcophagus 0x17AE (Continuous, pack 4): cls0[543] @0x02281934 = {0x17AE, 0, 0, +0C 0x0224A111, 0, 0}
  — single record, empty resolver slot, overwrite in place. No criteria rows.
  Other binding: u32 literal ov3:0x0221BF78, loaded at 0x0221BDD6 / 0x0221BF16 inside The First Sarcophagus (0x17AF)
  cls1 resolver 0x0221BD69 (its "Second/Third face-up?" check; 0x17AD literal next door). Name slot en 22 B (floor 8 ja),
  desc floor 53 -> needs card_text.CARD_TEXT re-emit. ARM9 advisory u16: 0x020997AC, 0x0209BA4E (unclassified).
- Temple of the Sun 0x21D5 (Continuous, pack 27): CLEAN, zero records/rows -> needs a count-neutral cls0 INSERT.
  Name floor 10, desc floor 88.
- Spell Absorption 0x15FE: CLEAN (2 noise hits); effect presumably in a base±imm switch (not visible to scan).
- Branch! 0x1971: cls1[497] + criteria[392] + 4 code literals (0x021C98C0, 0x021E51D0, 0x0223D990, u16 0x0226DC4E).
- Vehicroid Connection Zone 0x1A5C: Normal Spell, cls0[724] + 2 criteria rows + 6 code literals incl. summon list 0x0228F774.

## Resolver trace (static disasm of 0x02232CFC, ov3 reference image, 2026-09-25)
- cls0 +10 (cost) slot of Gem-Knight Fusion cls0[1195] = 0 -> free for the C4 HOPT stamp. PROVEN (raw read
  {0x22D6,0, 0x02232CFD, 0, 0x02232CB1, 0, 0}).
- 0x022325B4 callers: ov3 only, 10 sites (0x02232E12/E46/E8A resolver phase 1; 0x02233A7E.. Future Fusion;
  0x0223BE56 Extra-Deck gate). Entry hook on the function covers all. PROVEN (BL scan of ov3+arm9).
- Phase 1 (0x02232DE0..): pick stored +0x68, count +0x70, mode = 0x022325B4(cid) -> [0x0229ABFC+0x74].
  Chain Material 0x1D2A check skipped only for mode 6.
- Phase 0x78 material pick: mode 0/7 -> 0x0224B9F0 (filter 0x02232745); ANY OTHER mode (1 Miracle Fusion, 2, ...)
  -> 0x0219C430(side, 6 | 0x48 | n+6, cid, target). So mode 2 would ride Miracle Fusion's picker path.
- Material move loop 0x02233336..0x02233580 (dest = 0x02232684(cid) at 0x022333A8), per material zone r5:
    zone<=0xA / 0xC / ==dest / (0xF && mode!=9) -> skipped here (field mats bulk-sent by 0x021CDD4C(desc,mask,dest,0x20) @0x0223332E)
    0xB hand : dest 0xD -> 0x021C6988 ; 0xE -> 0x021C6E5C ; 0xF -> 0x021C6E4C
    0xE GY   : dest 0xD -> 0x021C6A0C ; 0xF -> 0x021C7098
    0xF ban  : dest 0xD -> 0x021C6A9C
    0xD Deck : dest 0xF -> 0x021D21DC(side, mask, cid, 0x10)   ** dest 0xE (GY) HAS NO ARM -> Deck mats NOT moved **
  => U1 answer: shared resolver + mode 2 + GY dest leaves Deck materials in the Deck. Needs a Deck->GY arm
  (ov5 detour at 0x02233560 `cmp r5,#0xd` block) or a different destination. PROVEN static; not executed.
- Deck-card relocation core 0x021D1DAC(side, r1, ref, flags, [sp]=cid): source r7 = 0xC if 0x0202307C(cid) (Extra) else
  0xD; dest r4 = r1 ? 0xF : 0xE (0x021D1DE2..E8). Wrappers: 0x021D21DC(side,ref,cid,flags) r1=1 BANISH (the Fusion
  Deck arm); 0x021D21B0(side,ref,cid,flag) r1=0 -> GY, flag normalised to 0/1; 0x021D21CC(side,ref) r1=0 cid=0.
  PROVEN static disasm 2026-09-25.
  => FIX DESIGN for the Deck->GY gap: 4-byte `bl` at 0x02233564 (`ldr r0,[sp,#4]` 0x9801 / `cmp r0,#0xf` 0x280F) into
  an ov5 stub: if dest==0xE && [r7]==donor -> 0x021D1DAC(r4 side, 0, [sp+0x10] ref, 0x10, [sp]=cid) mirroring the
  banish arm but r1=0, then return with Z=0 so `bne` goes to 0x02233576 (count++); else re-execute the two displaced
  instructions (flags preserved through bx lr). UNBUILT.
- Summon commit: phase 0x32 -> 0x0223358E: log 0x021C3BC8(0x4E..), then 0x02269314(side, &player[+0x4E4 + i*4], 1, cid<<16|1)
  @0x022335EC (Extra-Deck array entry). Post-commit returns 1 @0x022335F0 -> candidate ATK/DEF-0 hook site.

## U4: ATK/DEF -> 0 mechanism (static + offline switch walk, 2026-09-25)
- Rider walker (continuous stat recompute) @0x021B5FB2..: node = pool 0x0229D33C stride 0xA; key r5 = node+0,
  kind r6 = node+2 low nibble, amount = node+4. Kind jump table @0x021B6092: kinds 1-4 -> key-indexed delta tables
  0x0226E480 / 0x0226E1E4, then a per-GRANTING-cid switch from 0x021B615C. (kinds 6-9 -> 0x021B6CEA, 10-11 -> 0x021B7008,
  12 -> 0x021B740C, 0/5 -> 0x021B7692.)
- Walked every cid 0x0D00..0x25FF through the 0x021B615C switch offline (scratchpad leaf_all.py, thumbemu over the
  reference images). Default leaf 0x021B6296 (482 cids). "Becomes 0" leaves:
    0x021B6920 ATK->0 : 0x2199 Reptilianne Poison, 0x1EDA Black Rose, 0x2107/0x2108 Reptilianne Gorgon/Medusa, 0x1D0D, 0xE36
    0x021B695A DEF->0 : 0x1F7C Descending Lost Star
    0x021B69D0 ATK->0 AND DEF->0 : 0x1F64 Blackwing Armor Master (text: "ATK and DEF ... become 0 until the end of this turn")
      body: ATK -> [sp+0xA0],[r7+0x10],[sp+0xB0]=0 ; DEF -> [r7+0x14],[sp+0x9C],[sp+0xAC],[sp+0x20]=0 (each gated by
      0x021B3C18([sp+0x28], 1|2) == 0).
  => a node with KEY 0x1F64 on the Fusion monster = "ATK/DEF become 0" with no new stat code. PROVEN static; not executed.
- Attach precedent: Reptilianne Poison / Black Rose shared resolver 0x02229F44 -> 0x021C479C(side, slot, key=desc cid,
  kind = 2 if Black Rose else 3, [sp]=0) @0x02229FDC.

- Duration: rider.turn_sweeper (KB, continuous_riders.yaml:35) kind 3 frees only keys 0x18D9/0x1F6A -> {0x1F64, kind 3}
  survives turn sweeps; kind-3 nodes are freed when the card leaves the field (measured for 0x1E15). => permanent.
- WHERE to attach: shared summon-rider hook (finished_patches/summon_rider_hook.py, site 0x02268666, event record
  0x02298A28 {+2 side, +4 slot, +0x12 cid}). Walked the summon-event switch root 0x022680AA offline (scratchpad leaf.py,
  cid in r2): controls 0x1EA9/0x1E15 -> dedicated arm 0x02268544; 0x224C/0x106E -> DEFAULT 0x02268666; ALL Gem-Knight
  cids 0x22BD-C0, 22CF-D1, 23FC, 249C, 24AE, 24AF -> DEFAULT 0x02268666. PROVEN offline.
  ⚠️ scratch/summon_event_sim.py is currently BROKEN: returns (None, 0x022686AC) for every cid incl. the Plaguespreader
  control. Don't trust it until fixed.
- Fusion commit 0x02269314 = `str r3,[sp]; movs r3,#2; bl 0x0226925C` (SS_COMMIT wrapper) -> same commit engine as Jet
  Synchron's confirmed rider path. Opcode 0x14 posting for a FUSION commit = PLAUSIBLE (not traced to the poster).
- The existing stub is keyed on the SUMMONED cid and hardcodes key 0x1E15 -> Brilliant Fusion needs an arm that is
  latch-only (cid-blind) with key 0x1F64. That CHANGES a shipped shared stub (Jet Synchron / Jet Warrior / Remus).
- Latch setter candidate: the Deck->GY stub (runs in phase 0x63, donor-scoped, strictly before commit phase 0x32) ->
  no extra hook needed for the setter.

- Zone rule 0x022321D8 re-read myself: jump table add-pc base 0x0223224A; mode 2 -> 0x022322CC `cmp r6,#0xd ; beq
  accept ; b reject 0x02232228` => Deck-only. PROVEN static.
- Extra-Deck gate 0x0223BE40 classifies ITS r1 (the effect's cid) at 0x0223BE56 -> the H1 wrapper covers activation-time
  candidate checks. PROVEN static.
- Phantoms (unclaimed, present in stock AND rom_all_patches.nds, no card_prop row): cls0 0x143B; criteria 0x1507,
  0x1508 (1 row each). cls0 insert precedent: Ninjitsu Art (phantom 0x0E1A, in-game confirmed).
- Criteria rows to clone: GKF row 1197 {0x22D6, 0x0054, 0x0223ED09, 0x802} + row 1198 {0x22D6, 0xFFFF, 0x0223C939, 0x2}
  (row 1199 is GKF's GY-clause cost row -- NOT cloned).

## Proposed design (C1 + C4) — user approved extending the shared summon_rider_hook 2026-09-25
(condition: prove old arms byte-behaviour-equivalent offline for 0x224C/0x23EB/0x106E + a non-matching cid before build)
Hooks (ov3 4-byte BLs -> ov5): H1 classifier 0x022325B4 is a LEAF (no push lr) -> an entry BL would lose the caller's
lr; instead RETARGET its 10 `bl` sites (0x02232E12/E46/E8A, 0x02233A7E/CD2/FB8, 0x022340D8/41EE/43AA, 0x0223BE56) to an
ov5 wrapper {cid==0x21D5 -> 2; else tail `bx` to 0x022325B5 with lr intact}; H2 Deck->GY arm 0x02233564 (+ set latch);
H3 = extend shared summon_rider_hook with a cid-blind latch arm {key 0x1F64, kind 3}.
Data: cls0 INSERT for 0x21D5 {+04 0x02232CFD, +0C ov5 HOPT-cond, +10 ov5 HOPT-cost}; criteria rows 0/1 cloned from
Gem-Knight Fusion (count-neutral phantom drops); card_text entry.

## Build 1 code (2026-09-25) — offline-proven, NOT in-game tested
- patch_brilliant_fusion.py + summon_rider_hook LATCH prefix (CAVE_RIDERLATCH; LATCH_ARMS default () so the chain is
  unchanged) + ov5 slots CAVE_BF_MODE/DECKGY/COND/COST/ARM (0x023A1BBC..0x023A1CE0) + PHANTOM_CLAIMS + card_text 0x21D5.
- scratch/brilliant_fusion_stub_sim.py (run as module): 23/23 PASS — shared rider stub == bytes shipped in
  rom_all_patches.nds; latch prefix attach(1,3,0x1F64,3,[sp]=0) + replay r0/r6 + regs preserved, clear -> shared,
  mismatch -> shared & byte kept; mode wrapper 0x21D5->2 and native answers for 0x1A7E=2/0x22D6=0/0x1920=1/0x1C31=6/
  0x1D15=7; Deck->GY stub calls 0x021D1DAC(1,0,ref,0x10,[sp]=0x21D5) + latch + Z=0 only for (dest E, donor); cond/cost.

- BUILD 1: _build_brilliant_fusion.py -> data/over_the_nexus/working/rom_brilliant_fusion.nds, BUILD_EXIT=0,
  verify() 27/27 PASS, sha256 69cd80f14dabe6285781475b4bc3dc0d96873977b435105ef89d18d7fed8cfd2 (2026-09-25).
  AWAITING IN-GAME TEST (oracle list in the build script docstring; items 3/4 = assumptions A/B).

## IN-GAME TEST 1 of build 1 (user report 2026-09-25)
- User: items 1, 5, 6 CONFIRMED (name/type/text; 1-per-turn; Poly/GKF regression). Item 4: card stays face-up (not
  linked -- C2 not built; expected). Item 2 FAILED: material prompts (.ml3/.ml4) offer EXTRA DECK cards, not Deck; at
  .ml5 one random Deck Gem-Knight went to GY. Item 3 FAILED: Fusion monster has full ATK.
- Savestates data/over_the_nexus/working/rom_brilliant_fusion.ml2..ml5 (ml1 = no duel loaded). ROM identity PROVEN:
  BL 0x02232E12 -> CAVE_BF_MODE and the CAVE_BF_MODE/DECKGY stub bytes present in RAM. Read by scratch/bf_savestates.py.
  Player side 0 counts (+0x0C hand, +0x10 deck, +0x14 GY, +0x18 extra, +0x1C ban):
    ml2 (target prompt)  phase 0x7E, fusionUI empty;            [5, 34, 0, 15, 0], latch 0
    ml3 (material 1)     phase 0x77, tgt 0x24AF Prism Aura, n=2, MODE=2, picks 0; [5,34,0,15,0], latch 0
    ml4 (material 2)     phase 0x77, same, picks 1;                                   [5,34,0,15,0], latch 0
    ml5 (summoned)       phase 0, picks 2; [5, 33, 1, 14, 0]; GY = [0x22BE Gem-Knight Sapphire]; ED lost only Prism
                         Aura; LATCH = 1 (H2 stub ran for >= 1 material; rider never consumed it)
  => mode 2 IS reaching the resolver (H1 works). The phase-0x77 PICKER (mode != 0/7 path, 0x0219C430) lists the Extra
  Deck, not the Deck; the picked refs then resolve to Deck cards in the move loop (only 1 of 2 moved).
  => STRIKE 1 on "shared resolver + mode 2 = immediate Deck-material Fusion" (falsified). Precedent to diff: Future
  Fusion's own resolver 0x02233980 (its Deck-material pick path).
  => Item 3: latch set but never consumed -> either event 0x14 is not posted/reached for this commit, or the prefix's cid
  compare ([ev+0x12] vs [0x0229ABFC+0x68]) failed. Not yet distinguished.

### Diagnosis of test 1 (savestate ml5 + static, 2026-09-25)
- ITEM 3 ROOT CAUSE (PROVEN by ml5): event record 0x02298A28 after the summon = {+2 side 0, +4 slot 2, +0xE 0x24AF
  (Prism Aura = the SUMMONED card), +0x12 0x21D5 (= the SUMMONING EFFECT's cid), +0x24 opcode 0x17 (last event)}.
  Prism Aura sits in field slot 2. My latch prefix compared [ev+0x12] with the Fusion target 0x24AF -> mismatch ->
  latch left set (ml5 latch = 1, no 0x1F64 node in the pool). KB/summon_rider_hook call +0x12 "the summoned card's
  cid" -- only true for SELF-summons (Jet Synchron/Jet Warrior/Remus). +0x12 = source effect cid; +0xE = summoned cid.
  (Layout observed for opcode 0x17; for 0x14 inferred.) Summon-event switch root 0x022680AA with 0x21D5 -> DEFAULT
  0x02268666 (offline walk), so the hook IS on the path. FIX: latch arm matches [ev+0x12] == 0x21D5 (source).
- ITEM 2 PRECEDENT (Future Fusion resolver 0x02233980, static): FF uses the SAME material picker as the shared resolver
  (phase 0x7C: 0x0219C430(side, 6 | 0x48 | n+6, cid, target)), BUT its phase 0x81, run once between the target read
  (0x7E) and the picker, posts Extra-Deck UI commands: 0x021D2660(side) [cmd 0x59, zone 0xC, only if ED non-empty],
  0x021C7654(side) [cmd 0x28, zone 0xC, the last ED card, 0xFFFE], 0x021D2660(side) again. The shared resolver has no
  such step. Hypothesis (UNPROVEN): without it the ED list view stays open, so the picker SHOWS the Extra Deck while its
  indices map onto the Deck candidates -> the "random" Deck Gem-Knight. FF then moves each pick with
  0x021D21B0(side, ref, cid, 0) (Deck->GY) in its own phase-0x79 loop.
- OPEN: why only 1 of 2 picks moved at ml5 (maybe both indices mapped to one Deck card, or a pick decoded as zone 0xC).

### BUILD 2 (2026-09-25, user chose "Build 2 with FF's UI step") — AWAITING IN-GAME TEST
- Latch arm now keyed on [ev+0x12] == 0x21D5 (summon_rider_hook LATCH_ARMS 5-tuple: tag, byte, key, SOURCE cid, doc).
- cls0 +04 -> CAVE_BF_RES (0x023A1CE0, 72 B of 0x50): on phase 0x78 with [0x0229ABFC+0x7C] == 0, post FF's
  0x021D2660(desc[2]) / 0x021C7654(desc[2]) / 0x021D2660(desc[2]), then native 0x02232CFD(desc, r1).
- stub sim 27/27 PASS (incl. shared stub == shipped chain bytes); build verify 28/28 PASS;
  rom_brilliant_fusion.nds sha256 62e5911de3327bb12b670d40a9bc84ad4d0c7da3971b234231a09a9b9940108c.
- ⚠️ The ml1..ml5 savestates are BUILD 1 RAM (old ov5 stubs): a new test needs a FRESH duel on build 2.
- If item 2 still shows the Extra Deck = STRIKE 2 on the picker mechanism: stop patching, instrument (savestate at
  the material prompt of a STOCK Future Fusion vs ours; diff the UI/picker state).

### IN-GAME TEST 2 of build 2 (user report 2026-09-25)
- User: "the same thing happened as before, however the attack was now set to 0". => rider fix WORKS for ATK
  (user-observed 2026-09-25; DEF not reported). Item 2 unchanged: material picker still shows the Extra Deck, one
  random Deck Gem-Knight to GY. New saves: ml3 = target prompt, ml4 = first material prompt (build 2 RAM).
- User follow-up: "DEF was also 0" => ITEM 3 (ATK/DEF -> 0) IN-GAME CONFIRMED BY USER 2026-09-25 on build 2
  (sha 62e5911d...40108c): latch arm keyed on [ev+0x12] == 0x21D5 + node {0x1F64, kind 3}.
- INSTRUMENTED ml4 (scratch/bf_picker_dump.py, build-2 identity PROVEN): picker header 0x0229944C = {side 0, type 6,
  cursor 0, count 4}; candidate locators 0x02299458 = Gem-Knight Ruby / Topaz / Citrine / Prism Aura (the ED Gem-Knight
  FUSIONS) = criteria ROW 0 (target row) output. The material picker filled from the WRONG ROW; display was faithful.
  Fill chain: 0x0219C430(side, 6, cid, target) -> 0x02243FA8(side, cid, param=target) -> 0x02243B9C(cid, param) = row
  index -> 0x02243F38 calls that row's handler. So the donor's param->row mapping gives 0, not 1.
- ROW SELECTION (memory otn-criteria-row-offset-mechanism + static 0x02243B9C re-read 2026-09-25): leftmost row of cid,
  plus r4: membership LIST A 0x0227134C (0x3B sorted u16, `bl 0x02022E14` @0x02243BF2) -> r4 = (param != 0); else LIST
  B 0x02271314 (0x1B) -> bit28 test; else a compiled BST from 0x02243C1C (default r4 = 0). Stock + chain: Future
  Fusion 0x1A7E and Polymerization 0x12E5 ARE in list A; Gem-Knight Fusion 0x22D6 is NOT (it has a BST arm); 0x21D5 is
  in neither -> param 0x24AF still gave row 0 = the ED target row. ROOT CAUSE OF ITEM 2 (static + ml4 buffer).
- FIX CANDIDATE (precedent: FF/Poly are list-A members; shipped list-A joins: snoww, lightpulsar, darkflare, hanzo,
  miscellaneousaurus): add 0x21D5 to list A count-neutrally over a phantom. Chain list-A phantoms (no card_prop row,
  unclaimed in pool membership_list_a): 0x1303, 0x234E (both claimed only in OTHER pools). Data-only, no code.
- With the right row, CAVE_BF_RES's FF UI step is probably unnecessary (display was faithful) -> remove it.
### BUILD 3 (2026-09-25, user approved) — AWAITING IN-GAME TEST
- 0x21D5 added to list A over phantom 0x1303 (PHANTOM_CLAIMS membership_list_a); CAVE_BF_RES + FF UI step REMOVED
  (CAVE_FREE back to 0x023A1CE0); cls0 +04 = 0x02232CFD again.
- Offline proof (scratch/brilliant_fusion_stub_sim, 28/28): 0x02243B9C over an ov3 carrying this patch's tables ->
  row(0x21D5, 0x24AF) = leftmost+1, row(0x21D5, 0) = leftmost+0; controls FF 0x1A7E / Poly 0x12E5 = leftmost+1.
- rom_brilliant_fusion.nds sha256 a28299d8d534c27e2676e2d9cb9bfa76903c7a13d5587f5efa269ee084fb82e3, BUILD_EXIT 0.
- STILL UNPROVEN: that both picked Deck materials move to GY (only 1 of 2 moved in builds 1-2, but those picks were
  row-0 locators, so that observation is likely an artefact).
- STRIKE 2 on the picker mechanism ("FF's pre-picker ED UI step fixes the display" FALSIFIED). Per CLAUDE.md: no more
  picker patches until instrumented.

## C2 "If this card leaves the field, destroy that monster" (started 2026-09-25, user chose "Build C2 next")
Precedents: Future Fusion (prints the same clause; list member; attaches the link at 0x02233EA8) and Ninjitsu Art of
Super-Transformation (in-game confirmed 2026-08-31: leave list + phase-1 link).
- Leave-cleanup list 0x0226E940 (40 sorted u16): FF 0x1A7E is a member; 0x21D5 is not. Phantoms: stock 0x0E42 +
  0x0E48; chain only 0x0E48 (NAST spent 0x0E42). => insert 0x21D5 over 0x0E48 (both images). PROVEN (read).
- Link node (FF 0x02233EAC..EBE, NAST PART F3): 0x021C479C(side, [0x02298A28+4], key = (desc[+3]<<8)|desc[+2] (THIS
  card's own zone|side), kind byte 0x17, [sp]=0), attached in resolver PHASE 1. PROVEN static (FF bytes).
- The shared Fusion resolver's commit phase 0x32 returns 1 (0x022335F0) -> phase 1 IS driven; phase 1 = 0x022335F4
  `bl 0x021D26CC` (teardown) -> returns 0. So a cls0 +04 wrapper can attach on phase 1, then run the native. Guard on
  [0x02298A28+0x12] == 0x21D5 && [+0xE] == [0x0229ABFC+0x68] (ml5 shows both hold after the summon), because phase 0x32
  also returns 1 when the ED index lookup fails (0x022335C8 blt) = no summon. PROVEN static; ml5 layout observed.
- Destination switch 0x021CB490 (r4 = leaving cid; stack constants stored 0x021CB41A..0x021CB448: c4/c8 0x1881,
  cc 0x1C22, d0 0x1D2F, d4 0x1D2F, d8 0x1D08): 0x21D5 > 0x1CAC -> > [d0] 0x1D2F -> != 0x1E30 -> default, [sp+0xA8]
  stays 0x0E = DESTROY. PROVEN static (stack-based switch values read, not assumed).
- BUILD 4 (user approved 2026-09-25) — C2 IN-GAME CONFIRMED BY USER 2026-09-25 (C2a-d all confirmed): leave list 0x0226E940 += 0x21D5 over 0x0E48;
  cls0 +04 -> CAVE_BF_RES (0x023A1CE0, 96 B / 0x60; CAVE_FREE 0x023A1D40). Sim: phase 1 + source 0x21D5 + summoned ==
  target -> 0x021C479C(0, 2, 0x0600, 0x17, [sp]=0) then native; phase 0x32 / other source / no-summon -> native only.
  sha256 8597da3aacf7069896c261b8fa187df4972fd41882139ead9a4f2b8102ace28b, BUILD_EXIT 0. Oracle C2a-d in the build script.

## C3 session (2026-09-27) — user chose "build C3 first" (ship C1+C2+C4 later, together)
KB baseline this session: TOTAL 558, 500 PASS, 0 FAIL, 58 UNVERIFIED (the +9 UNVER vs handoff = savestate-only facts;
no savestate passed). Stub sim: ALL STUB SIMULATIONS PASS.
### Confirmed (static disasm of reference ov3, this session)
- H(a) SETTLED statically: walker 0x021B5FB2.. walks the zone chain head->tail via node+8 ([sp+0x28]); 0x0219F190
  APPENDS (rider.node_writer_and_kind_byte). The 0x1F64 leaf 0x021B69D0 zeroes only what is accumulated SO FAR:
  ATK [sp+0xA0], base [r7+0x10], [sp+0xB0], r4 (table-1 ATK acc), [sp+0xA8]; DEF [r7+0x14], [sp+0x9C], [sp+0xAC],
  [sp+0x20]. => a gain node attached AFTER the summon-time {0x1F64,kind 3} node is walked after it and SURVIVES.
- Walker working fields: [r7+0x10]/[r7+0x14] = working base ATK/DEF, [r7+0x18]/[r7+0x1C] = ORIGINAL ATK/DEF
  (Speed Warrior leaf 0x021B6A5A: [r7+0x10] = [r7+0x18]*2; arm 0x021B6A76 (0x1C4D) also [r7+0x14] = [r7+0x1C]*2).
- Kind jump table 0x021B6092 (base 0x021B6094): 0,5 -> 0x021B7692 (next node); 1,2,4 -> 0x021B60AC (skip all if
  [sp+0x68]=[sp+0x14]&2); 3 -> 0x021B60B6; 6-9 -> 0x021B6CEA; 10,11 -> 0x021B7008; 12 -> 0x021B740C.
  Kind 1-4: table 1 0x0226E480 (0x71 rows {u16 key, s16 atk, s16 def}, +-1 = x node amount) -> r4/[sp+0x20]; hit => next
  node. Miss: kind 1 -> switch 0x021B615C; else table 2 0x0226E1E4 (0x6F rows) -> [sp+0xA8]/[sp+0xA4]; miss -> switch.
- Power Bond 0x18FE: NOT in either delta table and on the switch catch-all (sim_cid_switch 0x021B615C) -> its gain is
  not a keyed rider. Limiter Removal 0x1409 leaf 0x021B6AD0 SETS [r7+0x10] = amount*10 (and zeroes accs) = a SET, not a gain.
- PRECEDENT for "until end of opponent's turn" + ATK/DEF pair: Weapon Change 0x175D resolver 0x0221B150 (cls rec @0x022883E8
  {0x175D, 0x0221B151, 0x021DCD49,..}): 0x021B44B4(side,slot,&buf) then 0x021C479C(side,slot, key=0x175D, kind 0x12,
  [sp]=u16 value) TWICE (params buf+0x14 then buf+0x10), plus a kind-7 link keyed (desc[3]<<8|desc[2]) with param = turn
  counter [0x0229DD14+0x40]. Kind 0x12 = kind 2, countdown 1 = survives the end of this turn, freed at end of next.
- Paired-node leaf 0x021B6CA0 (The Tyrant Neptune 0x221D, only cid on it): if node.next has the SAME key, r4 (ATK) +=
  this amount, [sp+0x20] (DEF) += next.amount, and skips the pair. => two nodes {0x221D, kind 0x12, origATK},
  {0x221D, kind 0x12, origDEF} = "+origATK/+origDEF until end of next turn" with no new stat code. (static; NOT executed)
- C3 ACTIVATION SHAPE (static, this session): Continuous Spell ignition = a cls3 record (cls3 base 0x02279D74, count 0x308,
  stride 24). Precedents: Core Transport Unit 0x223A cls3[665] @0x0227DBCC {+04 0x02207EF5, +08 0, +0C 0x021F0BDD, +10
  0x021E4ECD, +14 0} (Continuous, "once per turn discard 1 card"); Spell Chronicle 0x1D19 owns BOTH a cls0 (activation)
  and a cls3 (ignition) record = the exact BF shape; Shien's Dojo (shipped) inserted a cls3 row on a Continuous Spell.
- NATIVE "Once per turn: discard 1 Spell" COST = 0x021E8FD4 (5 cls3 users: Chiron 0x16B2, Reshef 0x18C6, Summoner Monk
  0x1900, D.D.M. 0x191E, Endymion 0x1FC4): `bl 0x021E5060` (per-copy OPT: rider {key 0x0FB6, kind 2} on desc[2]/desc[3]
  if 0x021D2C1C(desc)) then 0x0225991C(side, 1, 0, 1). 0x0225991C: r2!=0 -> mode 1, r3!=0 -> mode 7; 0x02259934 maps
  mode 1 -> flag 1, 8 -> 4, 7 -> 8, | 0x10, queues request 0x0225985C(side, 2, n, flags). card_category (0x02022D70):
  7 = Spell, 8 = Trap, 1 = Effect => mode 7 = Spell filter. (CID-BLIND: reads only desc[2].) Not executed.
- Condition slots of those precedents are cid-keyed: 0x021F0BDC = binary search of table 0x0226FAFC (0x92 x {cid, fn1, fn2}),
  then fn1 && fn2 (CTU row: fn1 0x021F024D, fn2 0x021F0821).
- Neptune key 0x221D side-use: only 0x021C7A04 (a per-effect-cid arm of switch ~0x021C78xx) strips ONE 0x221D node via
  0x021C48DC(side, slot, key, 1) along with the 0x9F-key list 0x0226E7C4 -- a single foreign card's effect. Edge only.
- CID-BLIND native cond for "OPT discard 1 Spell": Chiron 0x16B2's cls3 +0C 0x021F7375 (also Summoner Monk's cond-table fn2):
  0x021F0024(desc[2], desc[+0xC] = self ref excluded, 0, 0, [sp]=1 -> mode 7 Spell) = hand holds a Spell other than this
  card; then 0x021F01C0(desc) = 0x021A1430(desc[2], desc[3], 0x0FB6) == 0 (per-copy OPT unused). Reads only desc.
  Chiron cls3 = {0x16B2, 0x02204899, 0x021DB499, +0C 0x021F7375, +10 0x021E8FD5, +14 0x02234DA5}.
- LINK LOOKUP (static): 0x021A0C94(mon_side, mon_slot, src_side, src_zone) -> 0 if the slot is empty, else walks that
  monster's chain and returns the KIND NIBBLE (>= 6) of the first node whose key low byte == src_side and high byte ==
  src_zone, 0 if none. The leave-destroy loop (0x021CB474, after list 0x0226E940) calls it over both sides x slots and
  treats result != 0 && != 0xC as linked. BF's C2 link = key desc[3]<<8|desc[2], kind byte 0x17 -> returns 7.
- Original ATK/DEF getter: 0x021B44B4(side, slot, buf) = recompute 0x021B44C0(side, slot, buf, r3, [sp]=0); buf+0x18 /
  buf+0x1C = original ATK / DEF (init at 0x021B455E via 0x021B3CE8, then copied to +0x10/+0x14; the 0x1F64 leaf never
  writes +0x18/+0x1C). Weapon Change reads buf+0x10/+0x14 (current) the same way.
- 0x221D literal audit (all 5 ov3 pool loads): 0x021AB044, 0x0225E1E0, 0x02267006/0E/1E, 0x022671A4 are compares of a
  CARD's own cid in cid switches (not rider keys); 0x021C7A04 is the only use as a rider KEY (the strip above). So nodes
  keyed 0x221D on a non-Neptune monster are read only by the stat leaf 0x021B6CA0 and that one strip.
- cls3 phantom for C3: 0x234B (cls3[711] in BOTH rom.nds and rom_all_patches.nds, no card_prop row, unclaimed; other
  binding = one u32 code literal ov3:0x021B34E8, a cid compare, unaffected). 0x21D5 inserts at cls3[645] -> rows
  645..710 shift +1; no shipped module anchors cls3 by index/address in that range (grep of finished_patches +
  ygo_tools/tools/enhanced_edition_definitive/patches: only a comment "Lavalval cls3[696]" in patch_jet_warrior). Anchors 223/233/334/527
  untouched. Rejected: 0x234A (criteria row + 3 literals), 0x234D (cls2 row), 0x234F (2 criteria rows + 6 literals).
- Savestates rom_brilliant_fusion.ml1..ml5 are NO LONGER ON DISK (find over repo + user profile, 2026-09-27): no offline
  execution proof of the stat pair is possible without a fresh savestate.
- ov5: ledger last slot CAVE_BF_RES 0x023A1CE0 size 0x60 -> CAVE_FREE 0x023A1D40; ceiling 0x023AA120 (computed).

### BUILD 5 code (C3, 2026-09-27) — offline-proven stubs, NOT in-game tested
- ov5: CAVE_BF_C3FIND 0x023A1D40 (56/0x48 B), CAVE_BF_C3COND 0x023A1D88 (36/0x30), CAVE_BF_C3RES 0x023A1DB8 (92/0x60);
  CAVE_FREE 0x023A1E18. Ledger: cls3_table 0x234B + 0x21D5 claimed; check_allocations [OK] (300 ov5 slots, 324 claims).
- thumb_asm gained `add sp,#` / `sub sp,#` / `add rd, sp, #` (additive; encodings asserted 0xB08B/0xAA01/0xB00B).
- scratch.brilliant_fusion_stub_sim: ALL PASS incl. C3: find = first (side,slot) with lookup != 0/0xC else -1; cond
  gates Chiron's 0x021F7375 on the link; res = 0x021B44B4(1,3,buf,0) then attach(1,3,0x221D,0x12,[sp]=2950) and
  (...,2450), returns 0; monster gone -> no-op; cls3[645] == record, 0x234B gone, row 527 unmoved.
- BUILD 5: _build_brilliant_fusion.py -> rom_brilliant_fusion.nds, BUILD_EXIT=0, verify() 36/36 PASS, sha256
  1965d2e4ffcf1367265da73fac8b8e2941ddf38116effdc190f9c14287587a91 (2026-09-27). AWAITING IN-GAME TEST (oracle C3a-f
  in the build script docstring). Distinguish: C3 not offered = cls3/cond wiring; offered but stays 0/0 = pair leaf or
  walk order (hyp. a/b); permanent = kind nibble; wrong numbers (e.g. ATK=DEF) = pair order.

## Ruled Out
- (strike 2) FF's phase-0x81 UI step (0x021D2660/0x021C7654/0x021D2660) before the shared picker: display unchanged.
- (strike 1) "shared Fusion resolver 0x02232CFC + mode 2 = a working immediate Deck-material Fusion": the phase-0x77
  picker shows the Extra Deck (in-game test 1 + ml3/ml4).
- (bug) latch prefix keyed on [ev+0x12] == Fusion target: +0x12 is the source cid (ml5).
- Normal Monster donor: card must be a Continuous Spell that stays on field.
- Data-only mode-2 retarget of the classifier: the only mode-2 arm is keyed to Future Fusion.

## Open Questions (as of handoff 2026-09-25; the old U1-U4 / C4 / donor questions are all CLOSED above)
- SHIPPING (user decision pending): C1+C2+C4 are in-game confirmed but NOT in steps.STEPS. Shipping needs
  summon_rider_hook.LATCH_ARMS default = patch_brilliant_fusion.LATCH_ARMS (hook 0x02268666 then points at
  CAVE_RIDERLATCH in the chain -> Jet Synchron / Jet Warrior / Remus need an in-game recheck), STEPS + SHIPPED rows,
  donor-pool note, EE build + verify sweep (expect 46+1 passed).
- C3 (not started, NOTHING below is proven): "Once per turn: You can discard 1 Spell; the monster Special Summoned by
  this card's effect gains ATK/DEF equal to its original ATK/DEF, until the end of your opponent's turn."
  HYPOTHESES to test statically first:
  (a) the 0x1F64 leaf 0x021B69D0 ZEROES the accumulators ([sp+0xA0]/[sp+0x9C] etc.) -- a gain applied BEFORE it in the
      walk would be wiped; the order of rider nodes on the zone chain (append order) decides. A grant node attached
      after the 0x1F64 node may or may not survive -- read the walker loop.
  (b) "gains ATK equal to original" candidates: a delta-table row (0x0226E480 / 0x0226E1E4, amount = node+4 param
      when the delta is the +-1 sentinel, fusion.variable_atk_is_rider_param) with param = original ATK.
  (c) "until the end of your opponent's turn" = kind high nibble countdown 1 (rider.node_writer_and_kind_byte).
  (d) cost "discard 1 Spell" and a cls3/ignition record on a Continuous Spell (see otn-vanilla-ignition-recipe,
      Soul Charge's HOPT pair for "once per turn" -- but this is a SOFT OPT on the card, not the hard 1/turn of C4).
  (e) the target = the linked monster: find it via the kind-0x17 link node keyed by this card's zone<<8|side.

## Next Experiment
- IN-GAME TEST OF BUILD 5 (sha 1965d2e4...587a91), normal duel, oracle C3a-f in _build_brilliant_fusion.py. If C3b
  fails (still 0/0 after resolving), ask for a savestate right after resolution and read the monster's zone chain
  (head u16 0x0229ACD2 + side*0xB3C + slot*0x14; pool 0x0229D33C stride 0xA): expect {0x1F64,k3}, link {..,0x17},
  then {0x221D,0x12,origATK},{0x221D,0x12,origDEF} ADJACENT. Then SHIP C1-C4 together (user decision 2026-09-27).
- (2026-09-27) C3 DESIGN APPROVED BY USER 2026-09-27 (offer only while the linked monster exists; build now, no savestate step):
  cls3 insert {0x21D5, +04 CAVE_BF_C3RES|1, +08 0, +0C CAVE_BF_C3COND|1, +10 0x021E8FD5, +14 0} over phantom 0x234B.
  C3COND: linked monster found (both sides x slots 0..4, 0x021A0C94(s, slot, desc[2], desc[3]) not 0/0xC) -> tail 0x021F7375.
  C3RES: find it again; 0x021B44B4(s, slot, buf, r3=0); 0x021C479C(s, slot, 0x221D, 0x12, [sp]=buf+0x18) then
  (..., [sp]=buf+0x1C); return 0. Offline sim of both stubs before build; stat-pair execution needs a fresh savestate.
- Decide ship vs C3 (user). For C3: start with the 3DS lookup (`-m otn_enhanced.tools.threeds_lookup` for any card
  printing "gains ATK equal to its original ATK" -- e.g. Limiter Removal 0x1409 leaf 0x021B6AD0 doubles ATK), then
  read the rider-walker loop 0x021B5FB2.. to settle hypothesis (a) before designing anything.
