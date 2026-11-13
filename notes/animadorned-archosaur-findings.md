# Animadorned Archosaur — findings

Donor: Swordsman of Landstar 0x1297 (user-chosen 2026-09-29). Whole card in scope.
Plan: ~\.claude\plans\animadorned-archosaur-it-isn-t-buzzing-pearl.md

Printed text (scratch/ygoprodeck_cache.json): L1 LIGHT Dinosaur Effect 0/0.
"If this card is Normal or Special Summoned: You can destroy 1 Dinosaur monster in your hand or
face-up field, except "Animadorned Archosaur", then add 1 Reptile, Sea Serpent, or Winged Beast
monster with the same original Level as that destroyed monster, OR 1 "Evolution Pill" Spell, from
your Deck to your hand. You can only use this effect of "Animadorned Archosaur" once per turn."

User rulings (2026-09-29): prompt offered iff a destroyable Dinosaur exists (no search-target
requirement). Evolution Pill list = {0x1AA3 Big, 0x1715 Ultra, 0x1319 Double (patched)}.
Not in NDS or 3DS — do not look there (user).

## Confirmed
- `donor_scan 0x1297` -> CLEAN (2026-09-29). Hits: ARM9 data u16 0x020A9F68 (ambiguous),
  code u16 0x0203D588. 0x1297 unused by any patch (Maiden donor is Comrade ... 0x1ED7).
- KB verify_knowledge: 521 PASS / 0 FAIL / 64 UNVERIFIED (2026-09-29).
- Evolution Pill cids in ROM: Ultra 0x1715, Big 0x1AA3, Double 0x1319 (patched). No set code.

- DECK WALKER 0x0223BC3C (disassembled 2026-09-29, scratch.dis 0x0223BC3C 0x220):
  args (r0 side, r1 row cid, r2 predicate|0, r3 pred list ptr, [sp] criteria word, [sp+4] type).
  Per candidate: keep = monster-branch 0x0223BA24 (word bit 0x2) OR spell-branch 0x0223BBCC
  (word bit 0x4, is_spell 0x02022FC8, spell subtype bits 7..9, 0 = any) OR trap 0x0223BC04 (bit 0x8).
  Then predicate at 0x0223BDFA: pred(r0 side, r1 0xD, r2 idx, r3 ROW cid, [sp] &cardword,
  [sp+4] list ptr) -> 0 rejects. Then record 0x02243B2C(side,0xD,idx) unless type bit 0.
- MONSTER BRANCH 0x0223BA24: is_monster 0x02029E60 first; race (bits 27..31), attribute (24..26),
  level (bits 18..21 value; bit 22 = >=, bit 23 = <=, neither = EXACT) only checked if non-zero.
  Level source for zone != 0xB is printed level 0x0202ABD8(cid) = ORIGINAL Level.
  => criteria word 0x00000006 = "any monster OR any Spell"; runtime-writing row+0xA = N<<2 gives
  "monster of original Level exactly N" and leaves Spells untouched (spell branch ignores bits 18..23).
- ADD_TO_HAND 0x02207EF5 phases (disassembled): 0x80 deck>0, count 0x02243FA8 (<1 -> msg 0x15 ->
  0x78), else msg 0x33 -> 0x7E picker 0x0219C430 -> 0x7D add 0x021C72CC -> 0x64 teardown 0x021D269C.
  No chain-depth bracket for a single pick. 0x1297 hits the default arm of both per-cid switches.
- 0x021D28A4 / 0x021D2964 = chain-depth push/pop (KB cards.yaml:561/564). Tyranno C2 brackets with them.
- Face-up flag: u16 at 0x0229ACD0 + side*0xB3C + zone*0x14 (= FIELD_CID 0x0229ACC8 entry +8) != 0
  (patch_miscellaneousaurus.py:121, patch_hyper_librarian.py:582).

- Phantom census 2026-09-29 (scratch/archosaur_pick_phantoms.py, stock rom.nds + chained
  rom_all_patches.nds of 2026-09-28): cls1 free nearest 0x12A6 / 0x120E / 0x12B4; code-7 NS list
  0x0228F7AC only 0x19D3 left; code-9 SS list 0x0228F63A NONE left; criteria (strict: one row, no
  other-table rows) NONE (0xFFFE is not a phantom). BLOCKERS for C1-SS and for the search row.
- CAVE_FREE = 0x023A2980 (ov5_cave.py:2049) at session start.
- RESOLVED the SS blocker: list 0x0228F60A (x0x18) is the "code 7 OR 9" = Normal-or-Special-Summoned
  trigger list (KB summon.trigger_is_a_membership_list, VERIFIED; consumed at 0x02265C3C..0x02265C48,
  `movs r5,#1` on hit, r5 only OR'd afterwards). Stock free phantoms 0x0E77, 0x1B6B (no card_prop,
  unclaimed, identical in chain). 0x1297 sorts exactly into 0x0E77's slot -> zero-shift rewrite.
  => ONE list insert gives both halves of C1; no c7/c9 insert, no shared-hook change.
- Also on that path (for completeness): 0x0228F598 = code 7 or 8, 0x0228F678 = any code.
- Criteria phantom: 0x0EAE (stock row 61; chain row 30). No card_prop, unclaimed, 1 criteria row +
  1 dead cls0 record[88]; NOT in lists A 0x0227134C / B 0x02271314 (stock + chain), not a
  0x02243C1C switch case. Donor sorts to stock row 83 -> shift window 61..83, which contains no
  ADDRESS anchor (only address anchors: dragon_shrine crit[157] in place, shiens_dojo baked 0x19B5
  row -- both outside). 0x167D (row 235) REJECTED: its window would cross crit[157].
  Psi-Reflector precedent: 0x0E3A's criteria row taken, orphan cls record left.
- Runtime row lookup (no baked row address): idx = 0x02243B9D(cid, 0), row = 0x022713C4 + idx*12
  (patch_miscellaneousaurus _ROW0_PTR, in-game confirmed).
- cls1 phantom: 0x12A6 (nearest to donor's sort index, d7).

## Ruled Out
- Donors Mokey Mokey 0x1782 (fusion recipe A[76], criteria row[329], stat tree),
  Crawling Dragon #2 0x0FF7 (fusion recipe A[38]), Sabersaurus 0x1A8C (ARM9 u32 0x0205355C).
- Kabazauls 0x1583: clean but rejected by user (too strong).

- BUILT 2026-09-29: _build_animadorned_archosaur.py -> rom_animadorned_archosaur.nds
  sha256 56b7279d85b4dd18d85f7245108b6a1e0920fdab826d5dc35cb3706b94e7dde9, verify 20/20 PASS,
  card_prop decoded = Effect Monster / LIGHT / Dinosaur / Lv1 / 0 / 0. check_allocations OK.
  Caves: COND 0x023A2980, SLOT4 0x023A29E0, HELP 0x023A2A10, PRED 0x023A2AF0, CRIT 0x023A2B50,
  RES 0x023A2B80; CAVE_FREE -> 0x023A2E00. Timing arm passed LOCALLY (tch.ARMS untouched).
  Chain untouched: summon_trigger_hook edit was reverted (git diff empty); card_text entry is inert
  until apply_stats_and_text runs for 0x1297.
- CHAIN TEST BUILD 2026-09-29: `_build_animadorned_archosaur.py --chain` layers onto
  rom_all_patches.nds (sha b85c3441..., current: built 4 min after steps.py's last edit) ->
  rom_animadorned_archosaur_chain.nds sha256 ddba109a65fc096f8f2aa96d750a34e3f2f48d245fa9695b60b55cf2afcb51e0.
  The shared timing stub is overwritten only if it equals tch.stub(ARMS) + zero tail.
  verify: archosaur PASS, miscellaneousaurus PASS, double_evolution_pill PASS, tyranno PASS.
  oviraptor + psi_reflector: ONE FAIL each = "shared stub == tch.ARMS stub" -- expected, the stub
  carries the local 0x1297 arm. petiteranodon: 2 FAILs "sent-to-GY chain 0x0FE1/0x0EC9" --
  PRE-EXISTING, identical on the untouched rom_all_patches.nds.
- **IN-GAME CONFIRMED BY USER 2026-09-29**, all 9 items of the test list given in chat (= docstring
  items 1-9: NS prompt + Dinosaur-only picker without Archosaur; Level-matched Reptile/Sea Serpent/
  Winged Beast + Pills only; OPT; decline re-offers; no Dinosaur -> no prompt; face-down excluded;
  SS half; field Dinosaur of another Level; no-match -> no crash) on rom_animadorned_archosaur_chain.nds
  sha256 ddba109a65fc096f8f2aa96d750a34e3f2f48d245fa9695b60b55cf2afcb51e0 (ROM inferred as the one
  delivered in the previous turn). Item 10 (card text/stats) in-game confirmed by user 2026-09-29 on the shipped chain (sha 9e07501f...7c179789).
- Side finding in that test: Petiteranodon destroyed FROM HAND gave no prompt. Cause: the chain ROM
  (19:43 2026-09-28) predated patch_petiteranodon PART F (19:55), so the in-game-confirmed hand fix
  was never in it. Chain rebuilt 2026-09-29 (EE build 84/84, sha256 f34ac729...c096169; old ROM kept
  as rom_all_patches.PRE_petit_partF.nds); sweep 70 passed / 0 failed; Petit verify PASS.
  Archosaur chain test ROM rebuilt on it: sha256 9e07501f1fb64a0e70851e47524deb5cf206a7d12cfe1cc0df085d637c179789
  Petit hand-destroy in-game confirmed by user 2026-09-29 on the shipped chain (sha 9e07501f...7c179789).
- **SHIPPED 2026-09-29** on user instruction ("All good, ship it"): steps.STEPS [82/85] after Tyranno,
  _verify_all_patches.SHIPPED, timing arm moved into tch.ARMS (module now uses tch.install/verify),
  donor pool note updated. EE build 85/85 sha256 9e07501f1fb64a0e70851e47524deb5cf206a7d12cfe1cc0df085d637c179789
  (pre-ship chain kept as rom_all_patches.PRE_archosaur.nds); sweep 71 passed / 0 failed; check_allocations OK.
- KB: dispatch.deck_walker_word_is_a_type_union VERIFIED; card.animadorned_archosaur UNVERIFIED.
- STATUS: AWAITING IN-GAME TEST (static verify is not confirmation).

## Open Questions
- PICK_WORDS 0x02299458[i] is only used for HAND picks (Tyranno proof); field picks read the zone's
  card word directly -- consistent with Tyranno, not independently measured.
- AI path (CTRL_TYPE 1/4) skips the picker UI and takes index 0 -- inherited from Tyranno, unmeasured.

## Next Experiment
- User runs the 10-item oracle in _build_animadorned_archosaur.py (normal duel, not a puzzle).
  If a clause fails, ask for a savestate at the failing prompt.
