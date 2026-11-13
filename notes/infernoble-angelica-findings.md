# Angelica, Princess of Noble Arms — findings

Family card 13 (Synchro). Started 2026-10-22 after the user confirmed Emperor Charles ("All good next card").

## Printed text (scratch/ygoprodeck_cache.json id 36320744): Synchro, FIRE, Warrior, L5, 1200/2400
1 Tuner + 1+ non-Tuner monsters
- C1 If this card is Special Summoned: You can add 1 "Horn of Olifant", or 1 card that mentions "Infernoble Knight
  Emperor Charles", from your Deck to your hand.  (once per turn)
- C2 (Quick Effect) When a card or effect is activated that targets this card on the field, or when this card is
  targeted for an attack: You can send 1 FIRE Warrior monster from your Deck to the GY, and if you do, banish this
  card (until the End Phase), then you can Special Summon 1 "Roland" monster from your Deck or Extra Deck.
  (once per turn)

## Facts (2026-10-22)
- Horn of Olifant / Noble Arms Museum / The Continuing Epic of Charles: NOT in the ROM's card pool (donor_scan cards()).
  Cards that mention Emperor Charles in the cache: Museum, Continuing Epic, Emperor Charles the Great (Link, skipped).
- "Roland" monsters built: Roland 0x0FDB (Main Deck), Captain Roland 0x0FEB (Extra Deck).
- Donor candidate Barox 0x0FFC (Lv5 DARK Fiend Fusion 1380/1530): only binding ref = fusion recipe A[9]
  @0x02270BDC; 16 ARM9 data-region u16 hits flagged ambiguous by donor_scan (numeric tables; 0x0FFC = 4092).
- ov5 cave: CAVE_FREE 0x023AA050, ceiling 0x023AA120 -> 0xD0 B left. RESERVE = 0x10000 (ov5_cave.py: heap
  measured 215.7 KB free vs 37.3 KB peak at 64 KB; growth is one constant, no slot moves).

## Status: user 2026-10-22 "Increase the cave, Build all the extra cards" (Horn of Olifant gets built too; cave
RESERVE -> 0x14000, chain rebuilt 119/119 f13eb229..., sweep 100/0). Donor Barox (no objection). BUILD 19 on Barox: identity + C2 in-game confirmed by user 2026-10-22 (C1 untestable). User 2026-10-22: "Migrate to Rabid Horseman" -> BUILD 20 re-donor 0x0FFC -> 0x1002.

## Confirmed
- Barox ARM9 u16 hits 0x0209D5D6.. / 0x0209E4F0.. = {0x0FFx, small} s16 pair tables (numeric curve data) -> clean.
- Precedents (cache text x NDS records, 2026-10-22):
  - targeted by an activation, Quick: Blue-Eyes Shining Dragon 0x17C2 cls3 {0x02213D05, 0, 0x021F8135, 0, 0};
    Naturia White Oak 0x2213 cls3 {0x0221DA95, 0, 0x02201FDD, 0x021E6FF5, 0}; Arcana Force EX Tails (cls1).
  - targeted for an attack, "You can": Krebons 0x1E24 cls1 {0x0221F9E1, 0, 0, 0x021E780D, 0}; Cyber Valley 0x1CF5
    cls1 {0x022272AD, 0, 0, 0x021E5201, 0}; Rubyruda / X-Saber Galahad same family.
  - banish until the End Phase: Interdimensional Matter Transporter 0x15B8 cls0 {0x02216CE9, 0x021DE7D9, 0, 0,
    0x02234E11} + cls2 {0x02216E21, 0, 0x021F68D9, 0, 0}; Wattpheasant 0x22FD / Uni-Horned Familiar 0x22EC /
    Cybernetic Zone 0x1D1B share 0x02216CE9 / 0x02216E21.
- "targeted for an attack" = per-cid compare tree @0x021C662A on the attack target's cid (attack-declaration
  handler) -> leaf 0x021C6754 r6 = 1 -> 0x021D3230(side, target zone, 0x13, word) = cls1 EVENT 0x13 to the target.
  Members: 0xE65(phantom) 0x1A73 0x1A78 0x1ACA 0x1B8F 0x1C4F 0x1CB1 0x1CCC 0x1CF5 0x1D05 0x1D11 0x1E24 0x1E8E 0x1EBF
  0x20E5 0x2163 0x21CE 0x22EC 0x22FF 0x2388..0x238C 0x2466 0x2467. Phantom arm literal 0x0E65 @pool 0x021C68C0 (ONE
  ldr user 0x021C6642): 0x0E65 -> 0x0FFC changes ONLY 0x0E65 (post->skip) and 0x0FFC (skip->post). PROVEN BY
  EXECUTION over all 0x4000 cids (scratch/infernoble/atktgt_tree.py).
- Banish-until-EP machine: resolver 0x02216CE8 (0x80 banish declared target via 0x021CF450, encode
  ref<<4|side<<3|0x021AF1E8<<2|[0x0229ACCE]<<1|[0x0229ACD0] in [0x74]; 0x7F post node 0x021D2584(side, desc cid,
  1, value) if [0x0229C314+0x14]); EP walker row {0x022546FD, cid} (rows 122 IMT / 124 Cybernetic Zone / 126
  Wattpheasant) -> 0x021A1584 node lookup -> 0x021D3168(cls2 zone 0x10 event 6) -> cls2 {0x02216E21, 0,
  0x021F68D9, 0, 0} returns it from the banished zone.
- SS from the Extra Deck by effect: Wattkyuki = ED builder 0x0223BE41 flags 8 + SS commit 0x0226925D
  (side, &word, 1, 2, [sp] = cid<<16).

## BUILD 19 (2026-10-22) -- in-game confirmed by user 2026-10-22 except C1 ("all effects of Angelica confirmed (except c1)"; C1 has nothing to search yet)
- rom_infernoble.nds sha256 c9a1d6a42a2b014012e9b2d6d223fee23007c6308f746635cf51a017f3e72d39 (base = chain on RESERVE
  0x14000); patch_infernoble verify PASS; regression FAIL set identical to BUILD 18.
- cls1 over 0x0EA0, cls3 over 0x0E51, cls2 over 0x0E67, criteria over 0x16C1, EP row 152, attack-target literal,
  c9_trigger_hook arm, recipe A[9] killed; ov5 CAVE_IK_AN_* 0x023AA050..0x023AA510.
- ASSUMED (not executed): self-banish replicating IMT's 0x80 body on the acting card itself; SS commit 0x0226925D from
  the MAIN DECK (Wattkyuki proved it from the Extra Deck / GY); summon event's desc[+4] != 0x13; C1 search set empty
  until Horn of Olifant / Museum / Continuing Epic are built (AN_SEARCH).

## BUILD 20 (2026-10-22) -- re-donor Barox 0x0FFC -> Rabid Horseman 0x1002 (user: "Migrate to Rabid Horseman") -- AWAITING RE-TEST
- rom_infernoble.nds sha256 d044d77eed72a8f6803e65308b75ba3b42d3c12c4ea599208dd4157382e5a996; verify PASS; regression
  FAIL set identical to BUILD 19. Rabid recipe A[10] killed; Barox recipe A[9] stock again (0x0FFC,0x106F,0x0FAB).
- Attack-target literal re-proven by execution for 0x1002 (atktgt_tree.py 0x1002: only 0x0E65 and 0x1002 change).
- Same stubs, same phantoms; every cid-dependent value derives from ANGELICA.

## In-game result (2026-10-22)
- C1 in-game confirmed by user 2026-10-22 on BUILD 21 (Rabid Horseman): "Angelica C1 also worked" (Horn search).
  With BUILD 19's "all effects of Angelica confirmed (except c1)" on Barox, every clause is now user-confirmed.

## Ruled Out
- CORRECTED 2026-10-22 (re-checked when the user asked): the Rabid Horseman 0x1002 "per-cid code gate" ruling was WRONG.
  ov3 0x021E1E78 is the literal behind `ldr r3,=0x1002 ; bl 0x021D6E40` @0x021E1DD0 = a zone-predicate SELECTOR MASK,
  not a cid; arm9 0x0206A5B8 is `ldr r2,=0x1002` (with r1 = 0xFFFF) into the varargs helper 0x0206A580 -> 0x0206A418,
  not card-effect code (exact meaning unproven). Only binding ref left = its own fusion recipe A[10] -> usable donor.

## Open Questions
- (answered) user: build Horn of Olifant too; C1 targets = Horn + Museum + Continuing Epic as they land (AN_SEARCH).
## Next Experiment
