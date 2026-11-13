# Petiteranodon — findings

Printed text (scratch/ygoprodeck_cache.json, id 82946847; EARTH Dinosaur L2 500/500 Effect):
> If this card is destroyed by a card effect and sent to the Graveyard: Special Summon 1 Level 4 or
> higher Dinosaur-Type monster from your Deck, but it cannot attack this turn.

Template: Babycerasaurus 0x1A8F (id 36042004, same stats), text identical except "Level 4 or lower"
and no "cannot attack this turn" rider.

User instruction 2026-09-25: Petiteranodon is not in the 3DS or NDS — do not look.

## Confirmed
- Criteria level byte encoding (KB `dispatch.criteria_word_level_field`, VERIFIED, 177/177 rows):
  byte bits23:16 = [op:2][level:4][flag:2]; op1 = "or higher", op2 = "or lower".
  Babycerasaurus row = {0x1A8F, 0xFFFF, 0x0223CA99 (Deck), 0x48900002} -> 0x90 = op2 L4.
  Petiteranodon needs 0x50 = op1 L4 -> word **0x48500002**. (Read from KB claim this session.)
- **Babycerasaurus is exactly THREE data records, nothing else** (donor_scan 0x1A8F, stock ov3, 2026-09-25):
  - cls2[222] @0x022770D4 = {0x1A8F, +04 0x02206CAD deck-SS, +08 0, +0C 0x0224A115, +10 0 (mandatory), +14 0}
  - criteria[462] @0x0227296C = {0x1A8F, 0xFFFF, 0x0223CA99 Deck, 0x48900002}
  - leave-mask[51] @0x0226ECE8 = {0x1A8F, 0x0E00} = 0x0800 to-GY + 0x0400 destroyed + 0x0200 by card effect
    (bits per KB leave.mask_bit_semantics) — exactly the printed trigger.
- **0x1A8F takes the DEFAULT path through 0x02206CAD** (capstone of 0x02206CAC..0x02206F40, 2026-09-25):
  phase-0x80 per-cid switch @0x02206D54 cids = {0x0D4C (0x1A98>>1), 0x136A, 0x140B (0x136A+0xA1), 0x1612,
  0x1A98, 0x1BA1, 0x1E2C, 0x21F8, 0x2233 (0x21F8+0x3B)}; phase-0x7C switch @0x02206E7C = {0x1E2C, 0x136A,
  0x1232, 0x1612, 0x2233, 0x1F7A, 0x2361, +1 more @0x02206EB8}. 0x1A8F in none. Lists 0x0227020C/0x022701EC
  covered by donor_scan (no hit). => a donor cid NOT in those sets reproduces Babycerasaurus with pure data.
- **0x0223CA99 is DECK** (KB counter_engine container fact, VERIFIED, 30/30). Its body (capstone 2026-09-25):
  `[sp]=row.word, [sp+4]=0xA, r0=side, r1=row.cid, r2=0, r3=0, bl 0x0223BC3C` — byte-identical to 0x0223CAD9
  except the flags literal (0xA vs 2). No stock CA99 row uses op1, BUT op1 through the same builder is native:
  Summoner's Art 0x1C34 crit[565] {0x0223CAD9, 0x00540402} (L5 or higher) and Gusto Skwirl 0x24A6 crit[1360]
  {0x0223CAB5 (flags 0xA, same builder), 0x00540002}. => the word's level op is decoded by 0x0223BC3C, not by
  the handler; 0x48500002 on CA99 is expected to filter Level>=4. (Structural, not yet executed.)
- **Phantom 0x0E6A** owns exactly one cls2, one criteria and one leave-mask row in BOTH rom.nds and
  rom_all_patches.nds, no card_prop, no PHANTOM_CLAIMS entry in any pool (scratch picker 2026-09-25).
  One phantom covers all three drops.
- **Donor candidate Mammoth Graveyard 0x0FE1** (Normal, L3 EARTH Dinosaur 1200/800): donor_scan --free CLEAN
  (zero aligned u16/u32 hits in ov3+arm9), zero rows in any cls/criteria/mask table in both ROMs, not in
  PHANTOM_CLAIMS, not in either 0x02206CAD per-cid switch. Min name slot 13 B (= len "Petiteranodon").
  Other clean unused Dinosaurs: Megazowler 0x0FF5, Kabazauls 0x1583, Frostosaurus 0x1B31.
- Plan = Mathematician/GK-Recruiter shape: 3 count-neutral inserts (cls2, criteria w/ 0x48500002, leave-mask
  0x0E00) over phantoms + card_prop -> Effect Monster EARTH Dinosaur L2 500/500 + card_text. No Thumb, no cave.

- **BUILT 2026-09-25** (user approved donor Mammoth Graveyard 0x0FE1): patch_petiteranodon.py +
  _build_petiteranodon.py -> rom_petiteranodon.nds sha256 219cd3647d27347028e0e5c98c4f8465dc685c8aac66e25ca09799e97dd411a9.
  verify(): A cls2 / B criteria / C leave-mask / D text all PASS; test_card_text OK. Claims registered in
  check_allocations (donor 0x0FE1, phantom 0x0E6A x3 pools), ledger emitted. NOT in steps.STEPS.
  **C1+C2 in-game confirmed by user 2026-09-25** -- all 5 oracle items (card/text; effect-destroy SSes
  Lv>=4 Dinosaur only, no prompt; battle negative; Tribute/Synchro negative; Babycerasaurus regression).
  This also closes the op1-on-0x0223CA99 assumption: 0x48500002 filters Level>=4 in-game.

## Clause 3 ("but it cannot attack this turn") -- started 2026-09-25
- Precedents in NDS: Summoner Monk 0x1900 (Deck SS via the SAME criteria handler 0x0223CA99, row 368, "cannot
  attack this turn"), Tribute Doll 0x15ED, Puppet Master 0x156A (ygoprodeck text grep 2026-09-25).
- Both Monk and Doll sit in TWO lists (donor_scan "unclassified" hits, dumped from stock ov3):
  - list @0x0226D6F8, sorted u16: 0x0D59 0x0DBE 0x0E03 0x14F7 0x156A 0x15ED 0x16C9 0x1900 0x1944 0x1A7B 0x1AF4
    0x1AF5 0x20CD -- nearly all printed "cannot attack" (Instant Fusion, Level Modulation, Fake Hero, Jurrac
    Guaiba, Chaos Sorcerer, Silent Doom). Sits between the attack-all list 0x0226D6E4 (10) and double-attack
    0x0226D712. Hypothesis: "a monster carrying a rider keyed by one of these cannot attack". UNPROVEN.
  - list 0x0228F708 (0x24): summon-event opcode 0x14 -> 0x021C479C(side, zone, key=source cid, kind 2, 0)
    (KB continuous_riders line 467, Rescue Cat mechanism). Monk/Doll/Puppet/Level Mod/Fake Hero/Guaiba all in it.
- **PROVEN (static, stock ov3, 2026-09-25): 'cannot attack this turn' = membership in BOTH lists, no code.**
  - Attack check 0x021A4A9A..0x021A4B36: walks the monster's node chain (head [0x0229ACD2+..], node =
    0x0229D33C + i*10: +0 key, +2 kind low nibble, +8 next); for every node with kind < 6:
    ldrh r0,[node]; ldr r1,=0x0226D6F8 (lit @0x021A4CE0, sole ref); movs r2,#0xD; bl 0x02022E14
    @0x021A4AC0..C6; hit -> bl 0x021A577E (cannot attack).
  - The node comes from list 0x0228F708 (lit @0x02268118, sole ref): summon event attaches a kind-2 rider keyed
    by [r4+0x12] = SOURCE effect cid (KB continuous_riders 'destroy during End Phase is pure data').
  - **Summoner Monk 0x1900 is the exact precedent**: cls3[214] = {0x02206CAD, 0, 0x021F0BDD, 0x021E8FD5, 0} (the
    SAME Deck-SS resolver as Petiteranodon), criteria on 0x0223CA99, no per-cid arm in 0x02206CAD, no End-Phase
    registry row; its only 'cannot attack' wiring is the two list memberships. So C3 = add 0x0FE1 to both lists.
    Rider expiry at end of turn is inferred from Monk (no registry row), NOT traced.
- **BLOCKER: both lists are full of real cards with no phantom**; each has ONE reader (count immediates
  0x021A4AC4 movs r2,#0xD ; 0x0226808E movs r2,#0x24) and is packed flush against its neighbours.
  Both sites run for EVERY card (attack check / summon event) -> an ov5 hook or an ov5-relocated list is an
  engine-wide puzzle hazard (prefer-ov5-cave exception). ov3 dead-block free space (2026-09-25):
  largest gap 12 B @0x021B58D0, then 10 B @0x021B5AAA, 8 B @0x021B5840 -- a 'cid==0x0FE1 ? 1 : bsearch'
  stub is ~22 B, does not fit. ov3_cave.py windows not canary-confirmed (do not claim).
  Both lists share SS - Summon Speeder 0x0DBE (Speed Spell) as a common member.

- **C3 BUILT 2026-09-25 (build 2)**: rom_petiteranodon.nds sha256
  49523cb573082a7f69fda2d67a590ec75da330328667fc9cb82f741fd5fb0e97. PART E = CAVE_PTER_NOATK 0x023A1B9C (24 B):
  `ldr r3,=0xFE1; cmp r0,r3; bne miss; movs r0,#1; bx lr; miss: ldr r3,=0x02022E15; bx r3` (disassembled
  from the built ROM; literals @0x023A1BAC / 0x023A1BB0 resolve correctly; 0x02022E14 is Thumb
  `push {r3-r5,lr}` binary search that itself clobbers r3). Both sites now `bl 0x023A1B9C`.
  verify 7/7 PASS. **C3 in-game confirmed by user 2026-09-25** (items 6-10: can't attack that turn, CAN
  attack next turn -> rider expiry confirmed; other monsters + Summoner Monk unaffected). Normal duel only.
- **SHIPPED 2026-09-25** (user: "Ship it"): steps.STEPS [74/77] + _verify_all_patches.SHIPPED; donor moved
  to "Used" in notes/donor-pool-normal-and-effectless-fusion.md + scratch/donor_resource.json.
  EE build 77/77 -> rom_all_patches.nds sha256 bd5fce0dc9bf915fdd9d2118833722b5397af8e78c6c7d4a9c891769eeb7b85c
  (hash re-read from the file). Sweep: 62 passed, 1 failed = patch_ninishi, PRE-EXISTING: identical 5 hook
  FAILs on the pre-Petiteranodon chain ROM; none of its sites are ours. Spun off as a separate task.

## Hand-destroy report (2026-09-28)
- User (verbatim): "Petiteranodon needs to trigger when it is destroyed from hand. EXACTLY how babycerasaurus
  does it" / "I watched it happen when testing Ultimate Conductor Tyranno." => Petiteranodon destroyed IN HAND
  by UCT C2 did NOT trigger. Test ROM = rom_ultimate_conductor_tyranno_fix3.nds (built on rom_all_patches.nds,
  which contains patch_petiteranodon). Savestates fix3.ml1 / .ml2 exist (19:32 / 19:34) -- contents unknown.
- UCT's hand destroy is CUSTOM (its findings: "Hand-destroy: no precedent"): 0x021D2478(side, idx, slot, cid,
  [sp]=0) -> 0x021D2314(side, 0xB, idx, loc, ...) -> 0x021D1300(0x20, &word, 0, kind) + 0x022391CC(0x20, word).
- **Babycerasaurus has NO code arm anywhere in ov3** (register-constant scanner over all ov3, 2026-09-28,
  $TEMP/scan_const.py; positive control finds the known 0x1CF9 compare @0x021D235C and 0x1900 @0x021AD9E4):
  0x1A8F appears in no cmp. Its ONLY records are cls2 / criteria / leave-mask, which Petiteranodon copies 1:1
  (only the criteria level byte differs). => statically, the two cards MUST behave identically on a hand
  destroy. UNVERIFIED: whether Babycerasaurus actually triggered in the UCT test (asked user).
- If neither triggers, the defect is UCT's custom hand-destroy (e.g. the "by card effect" reason bit 0x0200 /
  the leave path not being reached), NOT Petiteranodon.

- User 2026-09-28: "I saw babycerasaurus trigger" (hand destroy by UCT). Records identical in fix3 ROM
  (verify PASS). Ruled out: no Lv>=4 Dino in Deck (fix*.ml2 decks have plenty); miss-timing (both +10=0,
  never reach 0x021EE0E0); genre bits (no correlation with destroyed-to-GY text).
- **LEAD (not yet walked):** KB event.* @0x021D1392 -- "sent to the GY" from any location is a HARDCODED
  sorted binary-search cid chain in relocator 0x021D1300 (dest 0x0E); only admitted cids get [sp+0x14]=1.
  My register scanner can't see it (literal in parent node, cmp in child). Next: patch_snoww._switch_leaf
  (ov, 0x1A8F) vs (ov, 0x0FE1) on fix3 ov3 -- if 0x1A8F reaches an accept and 0x0FE1 doesn't, that's the bug;
  fix = admit 0x0FE1 at its own interval's terminal node (Shadow Mist / Eclipse Wyvern pattern, ov3).
  User is making savestates -- wait for them.
- **ROOT CAUSE FOUND (2026-09-28, patch_snoww._switch_leaf on stock rom.nds AND fix3):** in the sent-to-GY
  chain 0x021D1392, 0x1A8F -> its own arm **0x021D18D2**; 0x0FE1 -> default REJECT 0x021D19C0 (same as neg ctrl
  0x1859; Dandylion ctrl 0x19FE -> 0x021D19BE). Arm 0x021D18D2: `ldr r0,[sp,#0x2c]; cmp #0; beq reject;
  ldr r0,[sp,#0x1c]; cmp #0; beq reject; b 0x021D199E` (ACCEPT: movs r0,#1 -> [sp+0x14]). So the hand-destroy
  trigger is this hardcoded arm, NOT the leave-mask row (which is field-only; that's why Dark Hole worked).
  User savestates: fix3.ml3 = Babycerasaurus destroyed, fix3.ml4 = Petiteranodon destroyed.
- Arm 0x021D18D2 family (walk of all cids, stock): 0x1A8F Babycerasaurus, 0x24A6 Gusto Skwirl, 0x24E5 Necro Fleur.
- 0x0FE1's terminal node (traced): 0x021D13C2 `ldr r0,[pc,#0x1e0] (=0x0EC9 PHANTOM @0x021D15A4, sole reader)
  ; cmp r5,r0 ; bne 0x021D19CA(reject) ; b 0x021D185C (DW discard arm)`. Identical in stock / fix3 / chain.
- **FIX = PART F (2026-09-28)**: literal 0x0EC9 -> 0x0FE1, branch @0x021D13C8 -> b 0x021D18D2. 0x2700-cid walk:
  only 0x0FE1 (REJECT -> 0x021D18D2) and 0x0EC9 (DW arm -> REJECT) moved. Registered with
  patch_snoww.register_switch_stub; ledger ("gy_switch_node", 0x0EC9). patch_ceruli.DW_ARM_CIDS dropped the
  phantom 0x0EC9 (it asserted the phantom still reached the DW arm).
  Single-card rom_petiteranodon.nds verify 10/10. TEST ROM rom_petiteranodon_handfix.nds = fix3 + PART F only
  (3 ov3 bytes differ), sha256 57ec9ba12be803c5b8941d5f0508587d7841a4b5489cd37dadab827bad50b3bc.
  **PART F in-game confirmed by user 2026-09-28** on rom_petiteranodon_handfix.nds (fresh duel): hand destroy
  by UCT triggers + SSes Lv>=4; Babycerasaurus unchanged; Dark Hole on field triggers ONCE; battle = nothing.
  Chain NOT rebuilt yet (module is in STEPS; rebuild + sweep after the user confirms).
- 2026-09-29: user saw "Petit when destroyed from hand doesnt trigger" on an Archosaur test ROM
  layered on rom_all_patches.nds of 2026-09-28 19:43 -- built BEFORE PART F landed (module mtime 19:55),
  so PART F was never in the chain (its two "sent-to-GY chain" verify checks failed there). Chain
  rebuilt 2026-09-29: EE build 84/84 sha256 f34ac729e778b70af68a017790b90296a773eb0626c789a0453986c69f096169,
  sweep 70/0, Petit verify PASS. Hand-destroy on the chain **in-game confirmed by user 2026-09-29** ("I destroy petit from hand and it worked") on rom_all_patches.nds sha256 9e07501f...7c179789.

## Ruled Out

## Open Questions
- None open for the card. (Rider expiry closed by item 7, 2026-09-25.)
- C3 host decision (closed): **user chose option 3 (ov5 hook) 2026-09-25**, accepting the puzzle hazard: both
  `bl 0x02022E14` sites (0x021A4AC6 attack check, 0x02268090 summon event) -> one ov5 stub
  "key==0x0FE1 ? 1 : tail-call 0x02022E14". Both sites: r0 = key (ldrh), result only zero-tested (disasm).

## Next Experiment
- None -- card DONE and shipped 2026-09-25.
