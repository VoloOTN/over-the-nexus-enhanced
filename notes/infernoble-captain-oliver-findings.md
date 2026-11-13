# Infernoble Knight Captain Oliver — findings

Family card 11 (Synchro). User 2026-10-22: "Work on the next card while I test" (Captain Roland C2 in test).
Clause split + donor Labyrinth Tank 0x1118 confirmed by user 2026-10-22 ("Confirm"): C1 no OPT, OPT on C2 only, C2 not the turn sent to the GY.

## Printed text (scratch/ygoprodeck_cache.json): Synchro, Warrior, FIRE, L5, 2000/500
1 Tuner + 1+ non-Tuner monsters
- C1 When this card declares an attack while equipped: You can target 1 face-up card on the field; destroy it.
- C2 During your Main Phase, except the turn this card was sent to the GY: You can target 1 Warrior monster you
  control; Special Summon this card from your GY as a Tuner, and if you do, equip that monster you control to this
  card as an Equip Spell that gives it 500 ATK. Once per turn (C2 only: "this effect").

## Donor scan (2026-10-22) -- effectless Fusions whose ONLY reference is their own fusion recipe row
- Barox 0x0FFC (Lv5 DARK Fiend 1380/1530, recipe A[9]) -- RECOMMENDED (obscure, weak)
- Kaminari Attack 0x1170 (Lv5 WIND Thunder 1900/1400, A[29]); Marine Beast 0x120F (Lv5 WATER Fish 1700/1600, A[48]);
  Mavelus 0x10B6 (Lv4 WIND Winged Beast 1300/900, A[19]); Kamionwizard 0x1019 (Lv4 DARK Spellcaster 1300/1100, A[11]).
- Labyrinth Tank 0x1118 (Lv7 DARK Machine 2400/2400, recipe A[21] @0x02270C3C) -- user asked 2026-10-22. Its three
  extra donor_scan hits are FALSE POSITIVES (checked 2026-10-22): arm9 0x0205846A / 0x020587D8 load 0x1118 as a STRUCT
  OFFSET (`ldr r1,[r0,r7]` / `ldr r5,[r0,r6]` into the UI struct at [0x02130860+4], beside sibling offset 0x1114);
  ov3 0x0229113C is the low half of the pointer 0x02291118. => effectively clean (recipe only).
- Not offered: Pragtical 0x1188 (two unclassified ARM9 literals), Rare Fish 0x108C (2 bindings), Master of Oz
  (unchecked ARM9 ref), and the iconic ones (Flame Swordsman, Blue-Eyes Ultimate, Gem-Knights).

## Reuse candidates (to confirm in research)
- Identity: Captain Roland's recipe (card_prop from a real Synchro Effect Monster, genre, recipe kill, material walk).
- C1: attack-declaration trigger "while equipped" + destroy target (search precedent).
- C2: "except the turn sent to the GY" + SS from GY as a Tuner (0x1E40 latch, Renaud/Ricciardetto) + equip a monster
  you control to this card (Allure / Relinquished resolver 0x0220BFFD, Bradamante's desc re-point lesson).

## Confirmed (2026-10-22, static)
- Attack-declaration trigger list 0x0226E740 x0x11 (sorted u16, read @0x021C637A: bsearch of the attacker's cid ->
  event 0x13 to its cls1); members incl. Gravekeeper's Assailant 0x158D, Turbo Synchron, Vylon Soldier / Sigma, Dark
  Diviner; phantoms 0x0E11 / 0x18E5 (unclaimed in this pool).
- Target-1-face-up-card-and-destroy = The Fabled Catsith 0x216B cls2 {0x02204899 (-> 0x02204674), +08 0x021E3BD5 =
  zone predicate mask 0x1474, +0C 2, +10 0, +14 0x02234DA5} -- cid-free.
- "Except the turn this card was sent to the GY" natively = Skill Successor 0x20A1: +0C 0x02200908 queries
  0x021A14B4(side, 0xB, cid, ref); the {cid, kind 1, ref} node is posted by the sent-to-GY accept chain leaf
  0x021D178A (0x021C479C(side, 0xB, cid, 1, [sp+0x38] ref)); 0x20A1's node 0x021D157A -> leaf 0x021D17A2 -> b there.
  Captain Oliver (Extra Deck, field-only GY route) uses a leave-switch front marker {0x7118, kind 1} instead.
- Stat recompute 0x021B44C0 frame: [sp+0xC] holder side, [sp+0x10] holder zone, [sp+0xB0]/[sp+0xAC] equip ATK/DEF
  accumulators (zeroed at entry); @0x021B703E r5 = CARD_CID_AT(equip link location) -- monster equips included (the
  same path that gives Roland his +500 from the grant table) -> @0x021B7088 grant-table bsearch by r5.
- Labyrinth Tank material rule: absent from LIST_A / min-3; INNER_PRED walk 0x1118 -> 0x02023138 (generic, = 0x120B).

## Build design (BUILD 17)
- cls1 {Catsith resolver, Catsith filter, CO_C1COND (an Equip Card equipped to this card), You-can, 0x02234DA5} over
  0x0E6D + attack-list member over 0x0E11. cls2 {CO_C2RES (Bradamante's sequence + latch byte), CO_C2FILT (face-up
  Warrior you control), CO_C2COND (own MP, OPT 0x3118, no marker 0x7118, room), 0, 0x02234D99} over 0x0E4A; GY row.
- Fronts: rider site -> CO_LATCH -> RC_LATCH -> ...; leave switch -> CO_LEAVE -> BR_LEAVE -> T.G.; stat 0x021B7088.

## BUILD 17 (2026-10-22) -- AWAITING IN-GAME TEST
- rom_infernoble.nds sha256 a239d17c76993c00fdf91a52552ee2906951d63601ec0344c113c78948e29eed; verify PASS; regression =
  BUILD 16's set.
- ASSUMED (not executed): the stat front's +500 path; [sp+0x144]/[sp+0x98] at the leave switch (Bradamante proved
  [sp+0x44]/[sp+0x90]/[sp+0x98]/[sp+0xA0] in-game); Allure's equip of a monster YOU control (Bradamante equipped the
  OPPONENT's).

## IN-GAME RESULT
- in-game confirmed by user 2026-10-22 on BUILD 17 (rom sha256 a239d17c...9eed): "All of captain roland and captain oliver is confirmed". Not shipped.

## Ruled Out
## Open Questions
- "+500 from any monster equipped to it" vs only the one C2 equipped -- implemented as ANY monster equip (rare edge).

## Next Experiment
- In-game CO1-CO8.
