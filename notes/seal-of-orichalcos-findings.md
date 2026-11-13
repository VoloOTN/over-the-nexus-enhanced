# The Seal of Orichalcos — findings (donor Yami 0x10F5)

Printed text (`scratch/ygoprodeck_cache.json`, id 48179391, Spell Card):
> All monsters you control gain 500 ATK. Once per turn, this card cannot be destroyed
> by card effects. While you control 2 or more face-up Attack Position monsters, your
> opponent cannot target your monster(s) with the lowest ATK for an attack. If this
> card is activated: Destroy all Special Summoned monsters you control. You cannot
> Special Summon monsters from the Extra Deck. You can only activate "The Seal of
> Orichalcos" once per Duel.

Clauses: C1 +500 ATK (you control) · C2 OPT not destroyed by card effects ·
C3 lowest-ATK attack-target protection · C4 on activation destroy own SS'd monsters ·
C5 no Extra Deck SS · C6 once per Duel.
**Session 2026-10-02 scope: C1 only.** User chose donor Yami 0x10F5 (keep cid).

## SHIPPED 2026-10-02
User: "All confirmed. Ship it" (C3 items 13-18 confirmed) -> WHOLE CARD in-game confirmed by user
2026-10-02. steps.STEPS step 88/91 (right after Obedience Schooled -- must stay after it) +
_verify_all_patches.SHIPPED. EE build 91/91, sha256 69562b52b357aad99d6a5d8d4a3551fa332bbf2d180bb0e1526a1c8a659ef355
== byte-identical to the tested single-card ROM. Verify sweep 77 passed / 0 failed; allocation guard
clean. Not added to apply_all_patches (oracle retired). Donor-pool note not touched (Field Spell).

## Status (2026-10-02, before ship)
C1, C2, C4, C5, C6: **in-game confirmed by user 2026-10-02** (items 1-5, 7-12, 19-29 "Confirmed";
item 25 settles the UNPROVEN Polymerization path below -- Fusion IS blocked). C3 (items 13-18):
AWAITING IN-GAME TEST -- not yet reported. Build tested: sha256 69562b52...8a659ef355.
Not in STEPS / SHIPPED; ships only on user approval, and must come AFTER obedience_schooled.

## Status (history)
C1: **in-game confirmed by user 2026-10-02** (checklist items 1-5 "Confirmed"; item 6, the
AI activating it, not reported). C2: **in-game confirmed by user 2026-10-02** for items 7-10
and 12 (MST survives once, second MST destroys, resets next turn, Heavy Storm survives once,
Kingshark / Realm of Light regression OK). Item 11 user reply verbatim: "The seal should be
destroyed" -- ruling = a Field Spell swap must destroy the Seal; follow-up reply "No change
needed" = it WAS destroyed in the test (swap does not hit the protection). C2 complete.
Build details (PART C;
rom_seal_of_orichalcos.nds sha256 9c384d52b9ae5933cf5192156294042e279946036d5587343bcc6889c83df244,
verify 7/7, stub + hook disassembled from the output ROM; ledger claim (0x021B2B10, 0x1C);
KB destroy.survive_check_0x021CC028 VERIFIED, 552 PASS / 0 FAIL). Open ruling (user: "find out
in test"): does a Field Spell swap consume / get blocked by the protection? [resolved above]
C3: BUILT 2026-10-02, AWAITING IN-GAME TEST (PART D: BL @0x021A65E2 -> ov3 stub 0x02237E1C
"Pixie Ring OR Seal"; needs patch_obedience_schooled applied first -- its zero-filled tail is the
host; rom sha256 df3fc99ef8683f01fb0078268909594b8e1707648f722a4c4e55d61430884f75, verify 10/10,
stub disassembled from the output; ledger claim (0x02237E1C, 0x1C); KB
battle.pixie_ring_lowest_atk_block VERIFIED, 553 PASS / 0 FAIL). AI caveat: ov5 0x02317ED8 is
the AI's Pixie Ring mirror; the AI planner may not know the Seal restricts targets (the game still
enforces it). C4..C6 not implemented.
- `patch_seal_of_orichalcos.py` + `_build_seal_of_orichalcos.py` -> rom_seal_of_orichalcos.nds
  (on rom_all_patches.nds of 2026-10-01 18:39, staleness-checked), sha256
  f0c3bc0114a9efe2436c910771df76518a2d18e3f7b2132dc6405b8d7da05aa2; verify() 4/4 PASS.
- Output arm disassembled from the ROM: `0098 8742 40d1 7d20 8000 2418 4ce1`
  (ldr r0,[sp]; cmp r7,r0; bne 0x2928; movs r0,#0x7D; lsls r0,#2; adds r4,r4,r0; b 0x2B48).
- KB: `field.arm_side_registers` VERIFIED (551 PASS / 0 FAIL / 69 UNVERIFIED).
- NOT in STEPS / SHIPPED; donor-pool note not yet updated (only on ship).

## Confirmed (2026-10-02, disassembly of base EU ROM ov3)
- 3DS ships the card: CARD_Indx index 5368, **cid 0x2857**. 3DS code refs to 0x2857
  (undecoded, for later clauses): 0x38FD58, 0x391C24, 0x392920, 0x6A8388, 0x6BB570.
- Field-spell stat engine `0x021B26F4` prologue:
  `push {r3-r7,lr}; sub sp,#0x10; adds r6,r0,#0; ... str r1,[sp]` (=> **[sp] = field-spell side**),
  `adds r7,r3,#0` (=> **r7 = monster side**), r4/r5 zeroed = running ATK/DEF bonus.
  At 0x021B2718: `cmp r7,[sp]` already used natively to pick a per-side bit of [r6+0x20].
- Common exit `0x021B2B48` stores r4 -> [sp+0x2C], r5 -> [sp+0x30], returns changed flag.
- `0x021B2928` = `b 0x021B2B48` (no-change exit), in bne range from Yami's arm.
- Yami arm `0x021B28A0..0x021B28B5` (22 B), stock bytes:
  `b168 4e48 0842 01d0 c834 c835 0220 0004 0842 39d0 f1e7`
  (ldr r1,[r6,#8]; ldr r0,=mask; tst; beq; +200/+200; Fairy test; beq 0x2928; b 0x289A).
- u32-aligned literal 0x000010F5 occurrences: ov3 `0x021B29AC` (switch pool), ov5
  `0x022C971C`, ov5 `0x02331E94`. Wasteland/Mountain/Sogen: none.

- **Gate census for 0x10F5 (2026-10-02)**: cls0/cls1/cls2/cls3 = no record; criteria
  registry 0x022713C4 = no row (scanned all rows by cid). `scratch/cid_mention_scan.py 0x10F5`
  over ARM9 sections + all 50 overlays: 7 aligned hits = ov3 0x021B29AC (the engine switch's
  OWN pivot literal, loaded @0x021B274C; must stay), ov5 0x022C971C, ov5 0x02331E94,
  ov31 0x0217E3B0 (inside an ARM instruction word, incidental). **ARM9: none.**
- ov5 0x022C971C = pivot of a switch @0x022C9506 over 0x10F0..0x10F5; Yami arm
  0x022C9694 compares race CODE [sp+0xD0] vs 3/0x11/0x12 (Fiend/Fairy/Spellcaster) and
  applies -200 for Fairy (0x022C96A4) -- an ov5 MIRROR of the field-spell stat buff.
- ov5 0x02331E94 = pivot of a switch @0x02331DA2; Yami arm 0x02331F52 stores race MASK
  0x40008 (pool) and 0x20000 (`lsls r2,r1,#0xe`) into a stack array -- another mirror
  (race masks per field spell). Both are READERS (evaluation), not activation/target gates.
  Semantics unidentified (likely AI evaluation; ov5 per-cid lists are AI per
  dueling-ai-findings). Leaving them means that evaluator still thinks the card is Yami.

### C2 research (2026-10-02, static disassembly of base ROM, NOT yet built)
- Only native NDS card with OPT card-effect destruction immunity: **Abyssal Kingshark 0x1CA8**
  ("Once per turn, if this card would be destroyed by an effect that does not target it, it is
  not destroyed"). Its real literals: ov3 0x021B04CC (affect-predicate pool, arm 0x021B042E) and
  ov3 **0x021CC288** (pool of the survive function below); ov5 0x02352D00 = AI mirror.
- **0x021CC028(r0 side, r1 zone, r2 COMMIT, r3 TARGETED) = "would be destroyed -> survives?"**,
  returns 1 = survives. r5=side, r4=zone, r6=commit, [sp+4]=targeted, [sp+8]=cid
  (0x021A36EC), r7 = 0x0229C314 (literal 0x021CC268). Per-cid arms: 0x1B6A @0x021CC12E,
  Kingshark @0x021CC194, Realm of Light 0x1DCA @0x021CC21C (**requires zone == 0x0A = Field
  zone** -> Field Spells DO reach this function), default `movs r0,#0 ; pop {r1-r7,pc}` @0x021CC264.
- Kingshark arm = the OPT template: zone<=4, face-up 0x021A32B4, not [card word]>>26 bit,
  `0x021A1430(side, zone, 0x1CA8) == 0` (no marker yet), targeted == 0; if COMMIT: unless
  [r7+0x14] bit (side*16+zone) set, [r7+8] |= that bit, 0x021CF7D4(side, zone), then
  **0x021C479C(side, zone, key 0x1CA8, kind 2, param 0)** = per-turn marker; return 1.
  Kind 2 / duration nibble 0 is freed by the turn sweeper at the end of THIS turn
  (KB rider.turn_sweeper) => once per turn.
- Callers: executor 0x021CC290 @0x021CC604 (zone = own r6, commit = [sp+0x44], targeted =
  mode bit 28; gated on mode bit 1 ([sp+0x14]), [sp+0xF0] (stacked source arg) != 0 and a
  per-card halfword), plus @0x021CC6BA / @0x021CC7CA (commit 1, targeted 0, substitute paths).
- Executor 0x021CC290(side, zone, dest, mode, [stack] source): mode bit 2 -> early out,
  bit 1 -> survive check enabled, bit 28 -> targeted. Commit = 1 iff [state+0x18] != 2 and < 0x64.

### C2 design (2026-10-02, not built)
- Hook: 0x021CC264 (`movs r0,#0 ; pop {r1-r7,pc}` = 0020 febd, default exit of 0x021CC028;
  inbound branches land ONLY on 0x021CC264 -- from 0x021CC222/226/234 -- never on 0x021CC266)
  -> 4-byte BL to stub at **0x021B2B10** (phantom 0x2348 field arm, 36 B, natively dead per KB
  field.arm_map; stock bytes in base AND chain ROM; not in the ov3 dead-block ledger yet).
- Stub: `ldr r0,[sp,#8] ; ldr r1,=0x10F5 ; cmp ; bne no ; movs r0,#0 ; str r0,[sp,#4]
  (targeted := 0) ; str r0,[sp,#8] (cid := 0, loop breaker) ; bl 0x021CC1CA ; no: movs r0,#0 ;
  pop {r1-r7,pc}` + literal. 0x021CC1CA = Kingshark's marker query (key 0x1CA8 on the
  Seal's own zone chain) + commit tail (bit bookkeeping, 0x021CF7D4 flash, kind-2 marker,
  return 1). Marker already present -> bne 0x021CC21C (Realm arm) -> [sp+8]=0 != 0x1DCA ->
  0x021CC264 -> stub -> cid 0 -> return 0 (destroyed). [sp+4]/[sp+8] are the saved-r2/r3
  slots of `push {r1-r7,lr}`, restored into caller-scratch r2/r3 only.
- 0x021CF7D4(side, zone) = queues animation opcode 0x2D with 0x021A36EC(side,zone) -- generic.
- Both sites byte-identical in rom.nds and rom_all_patches.nds; no finished_patches module
  references 0x021CC028..0x021CC267 or 0x021B2B10.
- Pre-build checklist: per-cid gates PROVEN (census above); zone PROVEN only by precedent
  (Realm of Light 0x1DCA's zone==0x0A arm in this very function); which executor path a
  Field-zone card-effect destroy takes = ASSUMED (0x021CC604 gates [sp+0x14]/[sp+0xF0]/halfword
  not decoded); OPT stamp = the kind-2 marker attached in Kingshark's commit tail.

### C3 research (2026-10-02, static disassembly of base ROM)
- **Pixie Ring 0x20A3** (Continuous Trap) prints C3 VERBATIM ("While you control 2 or more face-up
  Attack Position monsters, your opponent cannot target your monster(s) with the lowest ATK for an
  attack."). Its only ov3 literal is 0x021A664C, loaded @0x021A65DC; ov5 0x02317ED8 = AI mirror.
- Its block is the tail of an attack-target restriction function (pool also holds Belial 0x1B9C,
  Marshmallon Glasses 0x1777, 0x21A8, 0x1AD2, 0x2117, 0x14D4): r5 = target side, r6 = target zone.
  0x021A65C2: target halfword [sp+0x7C][[sp+0x2C]] != 0; 0x021A65D4 `0x021AD2CC(r5,1,1) >= 2`;
  **0x021A65DC: `ldr r1,=0x20A3 ; adds r0,r5,#0 ; subs r2,r4,#2 (=-1) ; bl 0x021AC0C8 @0x021A65E2 ;
  cmp r0,#0 ; beq 0x021A662E`**; r7 = 0x021B8014(r5,r6) (target ATK); loop zones 0..4 != r6,
  occupied + [+0x3C] != 0, ATK < r7 -> break; no lower found -> `bl 0x021A5836` (mark untargetable).
  Ties: only STRICTLY lower breaks, so tied-lowest monsters are all protected ("monster(s)").
- **0x021AC0C8(side, cid, r2) = count of face-up active copies of cid on side**: monster cid ->
  zones 0..4; Field Spell (0x02029E80) -> **zone 0x0A only** (0x021AC1AC: 0x021A36EC(side,0xA) ==
  cid, face-up 0x021A32B4, not [word]>>26 bit, not disabled-mask bit side*16+0xA); else S/T.
  => `0x021AC0C8(r5, 0x10F5, -1)` = "the target's controller has the Seal active".
- Design: retarget the BL @0x021A65E2 to an ov3 stub: Pixie Ring check, else Seal check.
  Must be ov3 (attack selection runs in puzzles). Only space left: 0x02237E1C (56 B tail of the
  Abyssal Designator dead block, dead ONLY with patch_obedience_schooled's cls0 rewrite).

### User rulings 2026-10-02 (C4-C6)
- C5 lock lasts only WHILE THE SEAL IS FACE-UP; it blocks only Special Summons FROM THE EXTRA DECK
  (reviving a Synchro/Fusion from GY/banished is allowed).
- C6 counts only if the activation RESOLVES (a negated activation does not use it up).

### C4 / C6 research (2026-10-02, static)
- Field Spells with an on-activation effect use a **cls0** record (Array of Revealing Light 0x14D1
  cls0[333], Ancient Forest 0x2092 cls0[1079]); Yami has none (census above).
- C4 precedents: Special Hurricane 0x179E cls0[531] {0x022048FD, 0x021DD6CD, 0x021F0221,
  0x021E4EA5, 0}; Koa'ki Meiru Tornado 0x2078 cls3[547] slot2 0x021E32E5 (mask 0x1012).
  0x021DD6CC = `push {r3,r4,r5,lr} ; ldr r3,=0x1010 ; adds r5,r1 ; adds r4,r2 ; bl 0x021D6E40 ;
  ... SS bit = card word >> 4 & 1 ; pop {r3,r4,r5,pc}`. Mask bits 0-1 = side mode (1 = same side
  as source, KB dispatch.zone_predicate bits fact) -> own side = 0x1011.
  => C4 slot2 = 16 B stub replaying that prologue with 0x1011 and `bl 0x021DD6D4`.
- Slot3 0x0224A115 = `movs r0,#2` = activatable unconditionally (needed: C4 has no target
  requirement). C6 slot3 = kind-5 turn-log query 0x021A14E8(side, 0x0B, cid, 5) -> 0 / 2;
  post 0x021D2584(side, cid, 5, 0) (KB dispatch.turnlog_once_per_duel_is_kind_5).

### C4 + C6 BUILT 2026-10-02, AWAITING IN-GAME TEST (PART E)
- cls0 insert {0x10F5, RES 0x023A4231, FILT 0x023A41F1, COND 0x023A4211, 0, 0} at row 103,
  phantom 0x234C dropped from row 1225 (count 0x51A unchanged, sorted). 0x234C mention scan:
  own cls0 record + ov5 AI list 0x02397068 + ARM-noise u16 only.
- ov5: CAVE_SEAL_FILT 0x023A41F0 (16 B, joins 0x021DD6D4 with mask 0x1011), CAVE_SEAL_COND
  0x023A4210 (26 B, kind-5 query -> 0/2), CAVE_SEAL_RES 0x023A4230 (24 B, post kind 5 then
  0x022048FC, which is single-phase: returns 0). All disassembled from the output ROM.
- rom sha256 6fd0def0af02df89321121ea9d1e24fe4a4b4bd8a1719bedf4f49555637b17d5, verify 14/14;
  read-only verify sweep on this test ROM: 76 passed, 0 failed (the cls0 row shift broke no
  shipped verify). Ledger: cls0 0x234C + 0x10F5 claims, 3 ov5 slots.

### C5 research (2026-10-02, static) -- BLOCKED ON ov3 SPACE
- Zone code **0x0C = Extra Deck** (KB ram.container_for_zone_code).
- Fusion/effect SS from the Extra Deck: cid-aware gate 0x021BA258(side r7, cid r5, ref r4, LOCATION
  r6) -- callers pass r3 = 0xC at 0x0221DA36, 0x02233CF0, 0x0223D38C, 0x0223EA20 (via wrapper
  0x021BA410); Obedience Schooled already hooks its `bl 0x021BA1E8` @0x021BA368 (r6/r7 live there)
  -> chain: deny if r6 == 0xC && 0x021AC0C8(r7, 0x10F5, -1).
- Synchro Summon: mega-gate 0x021B9708 mode bit 4; the SYNCHRO wrapper 0x021B9EF0 = `ldr r3,[pc,#4] ;
  movs r1,#0x18 ; movs r2,#0 ; bx r3 ; .word 0x021B9709` -- retarget its LITERAL to a stub
  (no code bytes change) that denies when the Seal is active for r0. No synchro-range caller of
  0x021BA258/0x021BA410/0x021BA440 exists, so the Synchro path needs this second check.
- BOTH run in puzzles (shared gates) -> must be ov3. Need ~70 B; free ov3 ~50 B in fragments
  (0x02237E38 28 B, 0x021B2B2C 8 B, Yami tail 0x021B28AE 8 B, scraps). ov3 BSS cave is
  canary-unproven (ov3_cave.py says do not claim). Phantom 0x234C's handlers are SHARED
  (0x022062F9: 62 ptrs, 0x021F5F95: 18 ptrs) -> no space freed by its drop.
- A scan of ov3 for `ldr =<phantom cid> ; cmp ; bcc` found 322 sites ($TEMP/phantom_arms.txt,
  regenerate with the one-liner in this session) -- candidate dead arms, none proven exclusive yet.

### C5 BUILT 2026-10-02, AWAITING IN-GAME TEST (PART F) -- space unblocked by a dead phantom leaf
- User suggestion: reclaim ov3 code of a card that doesn't exist (e.g. Akz, the Pumer = 3DS cid
  0x234F, phantom in NDS). Akz itself frees only ~18 B (its summon-procedure arm 0x02262A52 is a
  SHARED leaf; its record handlers are shared). Generalised: scratchpad phantom_leaf_scan.py
  (all `ldr =phantom ; cmp ; beq/bne` arms, exclusive extent = no inbound branch/BL/ptr/pool word).
  Top hits: 92 B 0x022212E4 (0x0E82), 86 B 0x02228F4A (0x0E8F), 68 B 0x02208322 (0x0E3F), ...
- Host: 0x022212E4 (92 B) in cls3 resolver 0x02221298, phantom 0x0E82 (no card_prop in stock or
  chain; its other claim is accel_synchro's quickeffect_list drop). Arm sealed `bne`->`b` @0x022212E2.
- Stub A 0x022212E4: SYNCHRO wrapper 0x021B9EF0's literal 0x021B9EF8 -> A; deny if Seal active.
- Stub B 0x02221300: `bl 0x021BA20C` @0x021BA35A -> B; deny if r6 == 0x0C && Seal active for r7.
  (Not 0x021BA368: obedience_schooled's verify pins that exact BL.)
- rom sha256 69562b52b357aad99d6a5d8d4a3551fa332bbf2d180bb0e1526a1c8a659ef355, verify 18/18, stubs
  disassembled from the output, read-only sweep 76/0, ledger 17 ov3 dead blocks, KB
  summon.extra_deck_lock_seats VERIFIED (554 PASS / 0 FAIL).
- UNPROVEN: whether Fusion Summon via Polymerization reaches 0x021BA258 with location 0x0C
  (statically: the 0x0C callers are criteria handlers 0x0223D38C / 0x0223EA20 and 0x0221DA36 /
  0x02233CF0, not traced to Polymerization). Test item 25 is the oracle.

## Ruled Out
- C2 via the affect predicate 0x021B021C S/T tail (White Dragon Ninja's site): it is a QUERY
  ("may this effect affect the card"), called with no commit flag, so it cannot spend a
  once-per-turn marker; it also covers non-destroy effects.
- Halfword-aligned u16 grep is useless as a gate census for 0x10F5 (19 arm9 hits,
  instruction-encoding noise).

## Open Questions
- What are ov5 0x022C971C and 0x02331E94? (gate census, blocks the build)
- Inherited from gates-of-dark-world notes, UNVERIFIED: "Yami has no cls0-3 record and
  no criteria-registry row".

## Next Experiment
- User in-game test of C1 (checklist in `_build_seal_of_orichalcos.py` docstring).
- Later clauses: decode 3DS rows for cid 0x2857 (0x38FD58, 0x391C24, 0x392920, 0x6A8388,
  0x6BB570) first.


## 2026-10-08 -- Field Spell replacement vs the opponent's face-up Seal (ov3 test ROM 31aef920, PUZZLE)
User verbatim: "Seal of Orichalchos doesn't destroy the opponents face-up seal when played see .ml2"; then
"1. Puzzle 2. My seal stayed on the field 3. No it had not but this shouldn't matter 4. The opponents field spells
should go to the GY because the last played field spells takes precedent 5. Yes every field spells would destroy the
other field spells when played. It is a game mechanic".
RULING (user): activating a Field Spell sends the OTHER face-up Field Spell (either side) to the GY; Seal C2
(OPT not destroyed by card effects) must NOT stop it. Status: BUG, open.

### Confirmed (savestate rom_seal_of_orichalcos_ov3.ml2, 18:22, RAM off 0x24; scratch/seal_swap_probe.py, thumbemu)
- 0x021A36EC(side, 0x0A): side 0 = 0x10F5, side 1 = 0x10F5 -> BOTH Field zones hold a Seal after the activation.
- 0x021A1430(side, 0x0A, 0x1CA8) (Kingshark marker = C2 protection spent this turn): side 0 -> 1, side 1 -> 0.
- 0x021A14E8(side, 0x0B, 0x10F5, 5) (C6 once-per-Duel log, posted by the activator in RES): side 0 -> 1, side 1 -> 0.
- Rider nodes @0x0229D33C: node 2 {key 0x10F5, kind 5}, node 3 {key 0x1CA8, kind 2}.
=> the activating side (0) carries the C2 marker; the other side's Seal carries none.

### Open Questions
- Is side 0 the user in this puzzle? (Then the marker is on the user's OWN new Seal, not the opponent's.)
- Did anything try to destroy the user's own Seal earlier that turn (would explain the marker innocently)?
- Where is the engine's Field-Spell replacement (activation -> destroy the other zone-0x0A card)? Not in the KB.
  Does it run the survive check 0x021CC028, on which side/zone, and why is side 1's Seal untouched?

### Next Experiment
- Static: find the replacement path (callers of the destroy executor 0x021CC290 / sends of zone 0x0A on Field Spell
  activation) and whether it is gated by a per-cid / per-type test the Seal (Yami donor) fails.
- Control: stock pairing (two DIFFERENT stock Field Spells) on this ROM, to confirm the mechanic works natively here.

- USER 2026-10-08: "I was side 0, I summoned some monsters and then played seal. Destroying my own cyber dragon to test one
  of seals effects" -> side 0 = the user; nothing targeted the user's Seal; the 0x1CA8 marker on (0, 0x0A) is UNEXPLAINED.

### ROOT CAUSE (static, base rom.nds) -- the opponent's Field Spell is removed by the RESOLVER, which ours skipped
- Every placement-time path (0x02217EC6, 0x0224B246, 0x0220FED8, 0x0222072C, 0x02224A28) destroys only the ACTIVATOR's own
  zone 0x0A; 0x021CF35C(side, zone, ..) builds ONE mask bit (side*16+zone) -- no cross-side logic there.
- 0x02204C7C = stock Field/Continuous activation resolver (pool [0x0229AAFC], phase [+0x70]): phase 0x80 -> opp = 1-desc[+2];
  if opp's +0xFC occupied: cid -> [state+0x74]; if Field Barrier 0x1BD7 face-up (0x021AC204) -> desc[+0xB]=1, return 0;
  else 0x021CF35C(opp, 0x0A, 0, 0), return 0x7F. Phase 0x7F -> (cid != [+0x74] -> 0x021C7F5C), return 0.
- Census of stock Field Spell cls records: Ancient Forest 0x2092 cls0 +04 0x0222C9B1 = phase != 0x78 ? (r = 0x02204C7C(desc); r ? r : 0x78)
  : (desc[+0xB] ? skip : own effect 0x022077B4); Array of Revealing Light cls0 +04 = 0x02204C7D itself.
- The Seal's RES (ov5 CAVE_SEAL_RES / round-2 ov3) went straight to post + destroy 0x022048FC and NEVER called 0x02204C7C.
  0x022048FC is single-shot (mask 0x0224AA20 -> 0x021CF310, return 0), phase-independent.
- FIX (ov3 path only, opt-in): build_res3 = Ancient Forest's shape; phase 0x78 posts kind 5 + destroys unless desc[+0xB].
  56 B -> CAVE3_SEAL_RES moved to 0x021F19B0 (148-run best fit; old 24-B slot released, zero in the ROM).
  ov5 default UNCHANGED (still byte-identical to HEAD) -> the SHIPPED CHAIN HAS THE SAME BUG until ov3 becomes the default.
- TEST ROM round 3: rom_seal_of_orichalcos_ov3.nds sha256 c8be1d12f2dceff9995fdc360e71f12cc92f39ec068c4308e84215b7514a309b
  (stock + step 0 + Seal only). arm9 + ov5 identical to base; ov3 diff = Seal sites + cls0 row shift; RES read back from the
  ROM matches the source (bl 0x02204C7C / 0x021D2584 / 0x022048FC, literal 0x0229AAFC). AWAITING IN-GAME TEST.
- Open: the user's OWN Seal got the C2 marker during its activation (who ran a commit survive-check on (0, 0x0A)?). If real,
  a later card-effect destroy the same turn would wrongly destroy it -> oracle item.
