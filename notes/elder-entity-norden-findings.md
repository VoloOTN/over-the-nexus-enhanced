# Elder Entity Norden — findings

Donor: **Bickuribox 0x1127** (effectless Fusion), approved by user 2026-09-28 (replaced Metal Dragon 0x113F, which is not in the pool).
Scope: all clauses (user 2026-09-28), staged C0 -> C1a+C1b -> C1c, each ending in an
in-game test. Materials changed by the user to **1 Synchro Monster + 1 Synchro Monster**.

Printed text (scratch/ygoprodeck_cache.json id 17412721), Fusion / Lv4 / WATER / Fairy / 2000 / 2200:
- C0 "1 Synchro or Xyz Monster + 1 Synchro or Xyz Monster" -> user: 1 Synchro + 1 Synchro
- C1a "When this card is Special Summoned: You can target 1 Level 4 or lower monster in your
  Graveyard; Special Summon it"
- C1b "but its effects are negated"
- C1c "also banish it when this card leaves the field" (NORDEN leaving -> banish the revived
  monster; NOT the 0x1E15 self-leave marker)

Not in the NDS pool; not in the 3DS build (`threeds_lookup "Elder Entity Norden"` -> no match).

## Confirmed (2026-09-28, read-only on the committed stock ov3/arm9 oracles)
- Fusion predicate 0x02231A74 jump table 0x02231B54 (codes 23..50), target = 0x02231B56 + s16
  entry. Leaves:
  - 47 @0x02231D82: `(1<<race) & 0x2` AND is_synchro 0x02023050 — Draco-Equiste 0x2309 {47,15}
  - 48 @0x02231D96: race bit 21 AND is_synchro — Ultimate Axon Kicker 0x230A {48,21}
  - 49 @0x02231DAC: race bit 18 AND is_synchro — Supreme Arcanite Magician 0x239B {49,18}
  - 50 @0x02231DC2: `0x02023008(cid)==0` AND is_synchro — Gaia Drake 0x239C {0x1E11,50}
  - r6 = 1 << race (prologue 0x02231AE8..0x02231AF0 / 0x02231AD8..0x02231ADE)
  - **0x02231DCC..0x02231DD6 = `adds r0,r5,#0 ; bl 0x02023050 ; cmp r0,#0 ; beq 0x02231DD8 ;
    b 0x02231DF4 (accept)` — a plain is_synchro test**, reachable as its own leaf.
  - No native code = "any Synchro Monster".
- Codes 43..46 are used only by phantom rows 0x0EA1 {6,43} @0x02270B9C, 0x0EA2 {6,44}
  @0x02270BA4, 0x1C55 {6,45} @0x02270F4C, 0x1C5F {6,46} @0x02270F6C. Code 37 is Escuridao's.
  No finished_patches module writes 0x02231B54..0x02231B8B.
- Predicate callers (BL scan, ov3 only, none in arm9): 0x0223210A 0x0223D3DE 0x0223D458
  0x0223EAB6 0x022401E4. Table A/B base literals only at 0x02231E54/58, 0x02231EC4/C8,
  0x02231F48/4C.
- Metal Dragon 0x113F: 0 aligned hits in arm9, 1 in ov3 (its table-A row); 0 refs in
  finished_patches + check_allocations.
- Criteria word level byte = op<<6 | lvl<<2 | low2 (KB dispatch.criteria_word_level_field);
  Accel Synchro Stardust's "Lv2 or lower, GY" = 0x89 -> "Lv4 or lower" = 0x91.

- donor_scan 2026-09-28 over the effectless-Fusion candidates: NOT in the pool (no card_prop):
  Metal Dragon 0x113F, Skelgon 0x11C7, Skullbird 0x11AF, Mystical Sand 0x11B9, Punished Eagle
  0x1177, Rose Spectre 0x11F8, Soul Hunter 0x117D, Great Mammoth 0x11DA, Kaiser Dragon 0x1151,
  Warrior of Tradition 0x1210. IN the pool: Bickuribox 0x1127 (only occurrence = its recipe
  A[23] @0x02270C4C {0x1005 Crass Clown, 0x101E Dream Clown}; Lv7 DARK Fiend 2300/2000;
  name slot floor 9, desc floor 29), Steam Gyroid 0x18FA (+1 ambiguous arm9 hit 0x0209CD20),
  St. Joan 0x1458 (+unclassified ov3 u32 0x021E2488), Master of Oz, Thousand Dragon, Labyrinth
  Tank. Bickuribox 0x1127 APPROVED by user 2026-09-28.

- Preflight on rom_all_patches.nds (sha c52716a2...16c1): A[23] @0x02270C4C = {0x1127, 0x1005,
  0x101E, 0}; jump entry 46 @0x02231B82 = 0x0214; 0x02231DCC bytes = 281cf1f53ff9002800d00de0;
  code 46's only user = 0x1C5F. Code-compare scan 0x02231000..0x02234600: the only code
  interpretation outside the predicate is the `< 0x33` cid/code split @0x02232134/46/4C (the
  cmp #0x32 hits are resolver phases).
- KB: fusion.synchro_codes_and_plain_synchro_tail VERIFIED (verify_knowledge 515 PASS 0 FAIL).
- C0 BUILT 2026-09-28: patch_elder_entity_norden.py + _build_elder_entity_norden.py on the chain
  ROM -> rom_norden.nds sha256 03e6c7c99a30c909a9c66138e4f62bb2bed5b9ed170acbe8390b8257bbde5e75,
  verify 9/9 PASS (static). check_allocations clean. **C0 IN-GAME CONFIRMED BY USER 2026-09-28 (all 7 oracle items: identity, Synchro+Synchro, Synchro Tuner accepted, Synchro+non-Synchro and Synchro+Fusion rejected, other Fusions unaffected, deck editor OK).**

- STAGE 2 (C1a+C1b) evidence, 2026-09-28, on rom_all_patches.nds:
  - Junk Synchron 0x1E07 (native "Lv2 or lower in GY; SS, effects negated") = the template.
    cls1[838] = {0x1E07, 0, 0x02207191 revive resolver, 0, 0x021F03B5 GY cond, 0x021E51E5 "You can"
    tag, 0x02235605 target-declare} -- ALL NATIVE literals (no OPT, no ov5). Criteria row[721]
    {fn 0x0223C9D1, word 0x00890002} (3DS main_effect identical, aux 0xFFFF) -> Norden word
    0x00910002 (op 2 "or lower", lvl 4, low2 1).
  - Trigger: code-9 list 0x0228F63A (plain "when Special Summoned", KB
    summon.trigger_is_a_membership_list). Stock phantoms 0xE12 hanzo / 0x167C psi / 0x176C
    shadow_mist / 0x1ABF oviraptor are claimed; **0x1ABE is the LAST free one** (present, no
    card_prop, unclaimed in summon_list_c9). Fusion Summons post code 9 (native "when Fusion
    Summoned" HEROes sit in the code-9 proper list 0x0228F6C0 on the same evaluator).
  - NEGATE LISTS ARE FULL: write list 0x0228F750 (x0x2E, sole literal 0x02268114, search bl
    @0x02268074 with r0 = [r4+0x12] the SOURCE cid) and reader 0x0226FAB4 (x0x23, sole literal
    0x021EE4C8, bl @0x021EE418 with r0 = node key). Every entry is a live card (dumped); their one
    phantom each (0x0E4B / 0x0E57) is tour_guide's. bsearch 0x02022E14 returns exactly 1/0.
    -> fix: ONE shared ov3 stub "r0 == 0x1127 ? 1 : tail-call 0x02022E15", both bls retargeted.
    No patch hooks either bl (grep). Host: Dark Law's reclaimed 0x1AC7 body, free 0x02223490..
    0x02223504 (dead only with Dark Law applied -- it is in the chain base).
  - Revival list 0x0226DBBC (x0x82, sole literal 0x021AAE5C, read at 0x021AAC08 by 0x021AABC8, an
    early `return 1` before a per-cid switch): meaning unproven; Accel Synchro's GY revive is
    in-game confirmed WITHOUT membership, so Norden stays out of it.
  - Free phantoms (no card_prop, single row, unclaimed anywhere): cls1 0x0E4F, criteria 0x0E7D.

- C1a+C1b BUILT 2026-09-28 (parts D-G of patch_elder_entity_norden): rom_norden.nds sha256
  8f2d68965f7487aa5e6e48ba10cfec7feffb0fc93c4e13edee4a79ce7bc7486e, verify 20/20 static PASS,
  check_allocations clean (110 B ov3 free left). Built stub disassembled: ldr r3,=0x1127 ; cmp ;
  beq ; ldr r3,=0x02022E15 ; bx r3 ; movs r0,#1 ; bx lr (pool 0x022234A0/A4 correct). Both bls
  (0x02268074, 0x021EE418) -> 0x02223490. **C1a+C1b IN-GAME CONFIRMED BY USER 2026-09-28 (C1-1..C1-9 all pass; position = player choice)** (oracle in the
  build script).

- STAGE 3 (C1c) evidence, 2026-09-28 (stock oracle disasm + rom_norden.nds reads):
  - Leave-cleanup list 0x0226E940 (40, sole search bl @0x021CB3BC, r0 = r4 = the LEAVING cid,
    r1 = list literal, r2 = 0x28) has MONSTER members: Alien Mother 0x1A95, Doom Shaman 0x1C22,
    Il Blud 0x1CAC, GB Darius 0x1D08, Kinka-byo 0x1E30 (a BANISH-arm cid), Doomkaiser Dragon 0x1EA8
    (Extra Deck Synchro). => the cleanup runs for monster sources, incl. Extra Deck. List is FULL
    (all 40 entries have card_prop; phantoms spent by NAST 0x0E42 / Brilliant Fusion 0x0E48).
  - Doomkaiser Dragon cls1[895] = {0x1EA8, 0, 0x02207529, 0, 0x021F03B5, 0x021E51E5, 0x02235605}:
    Norden's C1 record with ONLY +04 different. 0x02207528 is the shared "SS from GY + link"
    resolver (pool: Limit Reverse, Autonomous Action Unit, Premature Burial, Birthright, Soul
    Resurrection, Psychic Tuning, Core Reinforcement, Amazoness Willpower + Doomkaiser).
    Phase 0x80: per-cid mode switch -> r4 (0 attack: Doomkaiser/Graceful Revival/..., 1 = Soul
    Resurrection 0x17B7, 2 = every unlisted cid incl. 0x1127 -- hand-traced) then
    0x02204730(desc, 1, r4) -- IDENTICAL to 0x02207191's generic leaf 0x022072DA
    `0x02204730(desc, 1, 2)`, which gave "player chooses the position" in C1-3.
    Phase 0x7F: 0x021A241C -> summoned card's (side, slot); if slot < 5 and 0x0202ABE8(cid) != 3
    and 0x021D2CB8(desc): 0x021C479C(side, slot, key = desc[2] | desc[3] << 8, kind 0x17, 0)
    (the NAST link node). 0x0202ABE8 = card_prop word1 bits 14..16 (3-bit subtype); Norden's word1
    0x002210C7 -> 0 (same decode gives level bits 10..13 = 4, matches) -> monster path, not 3 (equip).
  - Destination: tree 0x021CB490..0x021CB512 compares r4 (leaving cid); every miss branches to the
    shared tail 0x021CB514 `movs r0,#2 ; str r0,[sp,#0xAC]`, then 0x021CB518 reloads r0 from
    [sp,#0xA8]. NAST's PART H hooks 0x021CB48C (bl 93f00cff -> 0x0225F2A8, 20 B, compares r4 with
    0x1255, host full). NAST pins 0x021CB514 only in _assert_preconditions (apply time; NAST runs
    before Norden in the chain), not in verify(); the KB proof reads the stock oracle.
  - PLAN C1c: H cls1 +04 -> 0x02207529 (Doomkaiser's record verbatim); I bl @0x021CB3BC -> the
    existing membership stub 0x02223490 (generic over r1/r2); J bl @0x021CB514 -> new ov3 stub
    "replay tail; r4 == 0x1127 -> [sp,#0xA8] = 0x0F".

- C1c BUILT 2026-09-28 (parts H/I/J): rom_norden.nds sha256
  30e0c10930c00321037e20a12cb198ab05d8edef61d1cb2991107a1c1036d04c, verify 24/24 static PASS,
  check_allocations clean (86 B ov3 free left). Built disasm: 0x021CB3BC / 0x02268074 / 0x021EE418
  bl 0x02223490; 0x021CB514 bl 0x022234A8 = movs r0,#2 ; str [sp,#0xAC] ; ldr r0,=0x1127 (pool
  0x022234B8) ; cmp r4,r0 ; bne ; movs r0,#0xF ; str [sp,#0xA8] ; bx lr. **C1c IN-GAME CONFIRMED BY USER 2026-09-28 -- WHOLE CARD CONFIRMED
  (L1-L5 + regression R1-R3 all pass).**

- **SHIPPED 2026-09-28 (user: "Ship it")**: steps.STEPS step 79/82 (right after Dark Law, which it
  depends on) + _verify_all_patches.SHIPPED. EE build 82/82 -> rom_all_patches.nds sha256
  30e0c10930c00321037e20a12cb198ab05d8edef61d1cb2991107a1c1036d04c == the in-game-tested
  rom_norden.nds byte for byte. Pre-ship chain backed up as rom_all_patches.pre_norden.nds
  (c52716a2...16c1). Verify sweep: 67 passed, 1 failed -- patch_ninishi, which fails IDENTICALLY
  (6 FAIL lines, original and migrated module) on the pre-Norden ROM, so it is pre-existing.
  verify() made self-contained (no base diffs) so the sweep's stock-base call is valid.

## Ruled Out
- **Metal Dragon 0x113F as donor**: `donor_scan 0x113F` -> "<no card_prop row>" (2026-09-28).
  Its table-A row A[25] @0x02270C5C is a recipe for a card NOT in the NDS pool. The ov3/arm9
  cid-occurrence screen alone does not prove pool membership — always donor_scan.
- Reusing code 37 (DARK): claimed by patch_escuridao (MAT_DARK = 37).
- Native code 50 for "Synchro": it rejects Synchro Tuners (extra 0x02023008 test).
- summon_rider_hook 0x1E15 marker for C1c: that banishes the monster when IT leaves, not
  when Norden leaves.

## Open Questions
- 0x113F card_prop/intid presence -> donor_scan.
- C1a trigger: is the plain Special-Summon list 0x0228F63A read for an Extra-Deck donor, and
  does it have a phantom?
- C1b: what does the revival list 0x0226DBBC gate? (Norden left out; Accel precedent.)
- C1c: does the leave-cleanup list 0x0226E940 scan run when a MONSTER source leaves?

## Next Experiment
User in-game C1 oracle (C1-1..C1-9 in _build_elder_entity_norden.py). Then Stage 3 C1c: prove the
leave-cleanup list 0x0226E940 scan runs for a MONSTER source leaving (trace from 0x021C8216).
NAST attaches the kind-0x17 link at resolver phase 1 -- Norden uses native resolver 0x02207191.
