# Infernoble Arms (Durendal / Joyeuse / Almace / Hauteclere) — findings

Session 2026-10-20. User scope: "Make the plan for noble arms but focus on the 4 infernoble equips
for this session". Ogier is parked (notes/infernoble-ogier-findings.md). Family roadmap:
~\.claude\plans\add-all-the-infernoble-merry-rainbow.md

## Shared clause shapes (all 4 cards)
- E1: "While this card is equipped to a monster: You can <X>, then destroy this card." (ignition on a face-up Equip Spell)
- E2: "If this card is sent to the GY because the equipped monster is sent to the GY: You can <Y>." (optional trigger)
- HOPT: "You can only use 1 <card> effect per turn, and only once that turn." (E1 and E2 share one OPT)

## Confirmed (static disassembly this session, ov3 image)
- Leave dispatcher 0x021C7FD0's r3 ([sp+0xC]) = the reason word passed by the move function
  (caller 0x021CD2AC loads r3 from its own [sp+0xC] = its r3 arg).
- **Equip-card reason word built by the attached-card cleanup 0x021CB354 at 0x021CBBEC..0x021CBC1E**
  (r4 then flows into the per-attached-card loop at 0x021CBC52 that walks 0x0229D33C nodes):
    r4 = 0x02000000                         (always: lost its equip target)
    | 0x00080000 if leaving monster's reason & 2   ([sp+0x1C])
    | 0x00100000 if leaving monster's reason & 4   ([sp+0x18])
    | 0x00400000 if leaving monster's DEST == 0x0E (GY)   ([sp+0x14] = ([sp+8]==0xE) @0x021CB396)
    | 0x00200000 if leaving monster's reason & 0x1000 (Tributed)  (0x1000 << 9)
  Disasm excerpt:
    021CBBEE movs r4,#2 ; lsls r4,#0x18           -> 0x2000000
    021CBC06 ldr r0,[sp,#0x14] ; cbz ; movs r0,#1 ; lsls r0,#0x16 ; orrs r4,r0  -> 0x400000
    021CBC14 ldr r0,[sp,#0xc] ; tst 0x1000 ; lsls r0,r1,#9 ; orrs r4  -> 0x200000
- Stock per-cid leave arms that consume these bits (TREE 1 root 0x021C8216, scratch/leave_tree_leaf.py):
    Sword of Dark Rites 0x1BF0 -> 0x021C90F4: [sp+0x144] to-GY && [sp+0xC] & 0x200000 -> arm 0x021C9334
    Core Blaster 0x2097 -> 0x021C922E: [sp+0x144] && [sp+0xC] & 0x2000000
    GB Battle Archfiend Shield 0x1D23 / Battle Gladius 0x1C8D -> 0x021C9150: [sp+0x144] && & 0x800000
    Necklace of Command 0x1841 -> 0x021C8DA4: [sp+0x20] && [sp+0x144] && side checks
    Telekinetic Charging Cell 0x1EBB -> 0x021C8E98: [sp+0x24] && [sp+0x144]
- **0x400000 consumers (all-cid TREE 1 scan, scratch/infernoble/leaf_scan.py):** Nitro Unit 0x18D1 and
  Iron Chain Snake 0x1ECE -> arm 0x021C919E: `[sp+0x20] && [sp+0xC] & 0x400000` — both printed
  "equipped monster is destroyed by battle and SENT TO THE GRAVEYARD". Corroborates 0x400000 = equipped
  monster's destination GY. Also: Sword of Kusanagi / Orb of Yasaka 0x1E00/0x1E01 -> 0x021C9164 test
  0x1000000 ("returned to the hand"); Spirit Burner 0x2094 -> 0x021C918A same bit; GB Halberd/Gladius/
  Manica/Archfiend Shield 0x1C8C/D/E/0x1D23 test 0x800000 ("returned to the Deck").
- => Infernoble Arms E2 condition = [sp+0x144] (this card to GY) && [sp+0xC] & 0x400000 — same shape
  as Sword of Dark Rites with a different bit. STATIC ONLY: not yet traced live.

- E1 precedent: Spark Blaster 0x1909 (equip spell, Main-Phase ignition "target 1 face-up monster") owns
  cls3 record[216] @0x0227B1B4 (donor_scan this session) -> ignition on a face-up Equip Spell is a cls3 record.
- Donor scan (donor_scan this session, Equip Spells in NDS pool, list scratch/infernoble/nds_equips.txt):
  CLEAN: Demotion 0x15E3, Rod of the Mind's Eye 0x1663, Broken Bamboo Sword 0x1C39 (but Golden Bamboo
  Sword may test it via base±imm — unchecked). 1 unclassified hit: Raregold Armor 0x15EA (0x021A5DFC),
  Phalanx Pike 0x1C36 (0x021B7174). Synchro Boost 0x1E0B = equip ATK row[79] + 1 hit.
  Heavier: Stim-Pack, Grarl, Deep-Seated (cls2+leave-mask), Vicious Claw (cls1+token row).

## User decisions (2026-10-22, "confirmed")
- Donors: Joyeuse = Demotion 0x15E3 (first), Durendal = Rod of the Mind's Eye 0x1663, Almace = Broken Bamboo Sword
  0x1C39, Hauteclere = Psychic Sword 0x1F71. Equip to ANY monster, no ATK change (cache text has neither).
- Cache texts (ids 90861137 / 37478723 / 98319530 / 64867422); names arrive wrapped in stray quotes -> strip.

## Joyeuse (2026-10-22) -- BUILD 22 AWAITING IN-GAME TEST
- Demotion 0x15E3 per-cid code: Level recompute 0x021B807C builds a stack cid table; [sp+0xCC]/[sp+0xD0] =
  0x15C7 + 0x1C @0x021B845C / 0x021B8464 (scratch/infernoble/baseimm_scan.py). Plan: imm 0x1C -> 0x3A (= 0x1601,
  no card, no structure) so Joyeuse inherits no Level change. Other donors' base+-imm hits: Rod 0x02199C44 /
  0x021F076E / 0x0221A296; Bamboo 0x021C42A6 / 0x02234C30; Psychic Sword none.
- E2 = leave arm: Sword of Dark Rites' accept arm 0x021C9334 (`movs r0,#1` -> tail 0x021C93CE stores the post flag
  [sp+0x18]); plan: JO_LEAVE front ahead of CO_LEAVE @0x021C8216: cid 0x15E3 && [sp+0x144] && [sp+0xC] & 0x400000
  -> b 0x021C9334, else tail CO_LEAVE. cls2 needs no leave-mask row (Sword has none).
- E1 = cls3 (Spark Blaster shape) {own res: add-target 0x02208181 then destroy self 0x0224A925/0x021CF389, 0,
  cond, 0, 0x02235605}; E2 = cls2 {hand SS 0x0220667D after OPT, 0, cond, You-can, 0}.
- Criteria: rel 0 {0x15E3, 0xFFFF, 0x0223CA51 hand, 0x7C000002}, rel 1 {0x0223CA11 GY, 0x7C000002}; row pick via a
  JO_ROW front ahead of Ricciardetto's RC_ROW @0x02243BEC (acting desc cid 0x15E3 && desc[+5] == 3 -> rel 1).
- Phantom picks: cls3 0x0E56 (unclaimed), cls2 0x0E69 (claimed only as populate by souleating_oviraptor).

- BUILD 22: rom_infernoble.nds sha256 eaad9a39c20c00c9b5efd3f67b786e205fe389dbb98dc26f6a9c353584137500; verify PASS
  (9 JO checks + text); regression FAIL set identical to BUILD 21. ov5 CAVE_IK_JO_* 0x023AAC70..0x023AAE70.
- E2's reason bit: the leave switch's [sp+0xC] carries the equip reason word -- shown by NATIVE consumers in the
  same switch (Nitro Unit / Iron Chain Snake test [sp+0xC] & 0x400000, Sword of Dark Rites & 0x200000), not by a
  live trace of Joyeuse itself.
- ASSUMED (not executed): Demotion has no OTHER per-cid code (scan only covers literal / base+-imm); the hand-SS
  resolver 0x0220667D runs from a GY-zone cls2 desc (Ricciardetto ran it from the hand); the row front's cls3 test.

## Durendal (2026-10-22) -- BUILD 23 AWAITING IN-GAME TEST
- rom_infernoble.nds sha256 563aebfc9a84198d40a941e8551cd3f6e2226afd532558929543d3fe81adef53; verify PASS (10 DU
  checks + text); regression FAIL set identical to BUILD 22. ov5 CAVE_IK_DU_* 0x023AAE70..0x023AB080.
- Rod's battle-damage stack slot 0x02199C44 `subs r0,#0x40` -> `#0x2C` (0x1677, no card). 0x021F076E left stock.
- E1 cls3 over 0x0E5E: Deck add 0x02207EF5 (rel 0 0x0223CAD9, word 0x7C940002 = FIRE Warrior Lv<=5) then destroy self.
  E2 cls2 over 0x0E6B: leave arm via DU_LEAVE ahead of JO_LEAVE; target via 0x02235605 (rel 1 0x0223CA11) -> Junk
  Synchron's revive 0x02207191; Warrior lock = Ricciardetto's node {0x4FE6, kind 1}. Row front DU_ROW (cls2 -> rel 1).
- ASSUMED: Rod has no other per-cid code; Junk Synchron's revive summons a GY target from an Equip Spell's cls2 desc.

## Almace (2026-10-22) -- BUILD 24 AWAITING IN-GAME TEST
- rom_infernoble.nds sha256 ce7158871bbdc6056cbecef6fddf4be3c558a0815481e1a35c2ef079b557f11e; verify PASS (8 AL checks
  + text); regression FAIL set identical to BUILD 23. ov5 CAVE_IK_AL_* 0x023AB080..0x023AB4D0.
- Bamboo's stack cid slot 0x021C42A6 (straight-line `ldr =0x1D01; str; subs #0xC8; str [sp+0x58]`) -> 0x1CEA.
  0x02234C30 = false positive (`adds r2, r5, #0` replaces the 0x1C25 literal first).
- ONE criteria row over 0x19C0, modes by param (0 E2 GY+banished FIRE Warriors / 1 E1 Arms in Deck+GY / 2 your
  face-up monsters); Deck worker records zone 0xD (0x0223BD52..), so the move's source = the pick's list-meta zone.
- E1 own machine (pick Arms, pick monster, zone UI, move, link 0xA, destroy self); E2 template 0x02235605 -> Renaud's
  add-target. LEAVE_FRONTS tuple now used by every verify that checks the leave switch.
- ASSUMED: Bamboo has no other per-cid code; E1 needs Joyeuse / Durendal / Hauteclere in Deck or GY to be offered.

## In-game results (user, 2026-10-22, BUILD 23/24)
- Joyeuse + Durendal E1: confirmed ("The C1 effect for both worked").
- Joyeuse + Durendal E2: confirmed when the equipped monster is destroyed by a card effect and by battle.
- BUG (user): "Joyeuse and Durendal should not miss timing when the equip is sent to the GY if the monster is used
  as a synchro material" -- E2 not offered on that path (user confirmed the reading: worked for effect/battle).

## Synchro-Material miss-timing fix (2026-10-22) -- BUILD 25 AWAITING IN-GAME TEST
- Cause: E2 is "You can" -> the body runs the miss-timing test 0x021EE0E0; a Synchro Summon's material send is not the
  last thing that happened, so a non-IF cid misses (memory otn-shadow-mist-shipped). Battle/effect worked = last event.
- Fix: AR_MISS (ov5 0x023AB4D0) fronts the test's node 0x021EE10C ahead of Maugis's ov3 front: Arms cid -> Z set.
- EXECUTION-PROVEN (scratch/infernoble/arms_misstiming_exec.py, BUILD 24 vs 25, all 0x2700 cids): only 0x15E3, 0x1663,
  0x1C39 change, each 1 (misses) -> 0 (never misses).  0x1F71 (Hauteclere) is 1 before AND after: its cid leaves the
  test's tree on a different branch and never reaches node 0x021EE10C -> needs its own node when Hauteclere is built.
- Verify-only tolerances: patch_shadow_mist._miss_node_reaches_a / patch_eva J walk the front chain into ov5
  (6 hops). Chain sweep after the edit: 100 passed, 0 failed. BUILD 25 sha256
  cfbf23b7af1366654198cbd5c722f3deb121921e599c0e8b364f19dd0790609e, FAIL set identical to BUILD 24.

## Hauteclere (2026-10-22) -- BUILD 26 AWAITING IN-GAME TEST
- rom_infernoble.nds sha256 8372026552dca17b81dc8ceb5bf3aea24998b3342cb9b61190f6e851c5926739; verify PASS (6 HA checks
  + text); regression FAIL set identical to BUILD 25. ov5 CAVE_IK_HA_* 0x023AB510..0x023AB770.
- Psychic Sword per-cid code: none found (literal, base+-imm up to +-0x600 / 14 instrs, movs+lsls/adds chains;
  catalogue hit = instruction encoding) -> its Psychic-only restriction + ATK-difference: ASSUMED gone (HA1/HA2).
- E1 = Wonder Clover 0x2009's own code (desc[0] = 0x2009 around 0x021E8180 player node + 0x02208849 default arm ->
  kind-2 rider {0x2009}); battle: "others cannot attack" @0x021A52AE (player node vs monster rider value),
  second attack = rider-key list @0x021A3E48.. (0x2009 = 0x203F - 0x36 @0x021A3F00). Target step 0x02234D8D.
- E2 = Catsith destroy 0x02204899 (+14 0x02234DA5), face-up monster on the field filter.
- Never miss: 0x1F71 leaves the miss-timing tree via 0x021EE114 -> 0x021EE124 -> pair @0x021EE12A (`subs r1,r2,#3 ;
  cmp r3,r1`, then blt miss / beq never) -> HA_MISS front: 0x1F71 -> `cmp r3,r3`. EXECUTION-PROVEN with
  arms_misstiming_exec (BUILD 24 vs 26): only the four Arms change, each 1 -> 0.

## In-game result (user, 2026-10-22, BUILD 25/26)
- "All 3 existing equips work perfectly" -> Joyeuse, Durendal, Almace whole cards in-game confirmed by user
  2026-10-22 (incl. the Synchro-Material never-miss fix). Hauteclere: not yet tested.

## Hauteclere equip-target bug (user 2026-10-27: "I cannot equip Hauteclare to a valid target", no valid target offered)
- CONFIRMED by execution over rom_all_patches.ml2 (chain 3e85b233): the equip-legality check 0x021D7348(desc, side,
  zone) returns 0 for u16[desc] = 0x1F71 on both own face-up monsters (Captain Roland z2, Renaud z3) while 0x15E3 /
  0x1663 return 1. Divergence: switch @0x021D78EC `subs r3,#0x9c` (r3 = 0x200D) = 0x1F71 -> `b 0x021D7F2A` = accept
  only if [sp+0x10] bit 21 (Psychic race) -- Psychic Sword's "Psychic only". A base+-imm compare, missed by the
  earlier scans (the 'NO findable per-cid code' claim was WRONG).
- FIX: halfword 0x021D78EC 0x3B9C -> 0x3BA2 (target 0x1F6B < the 0x1F6C lower bound of this subtree = unreachable).
  A/B executed: 0x1F71 0 -> 1; 0x1F6D..0x1F70 unchanged.
  APPLIED (PSY_GATE in apply_hauteclere): chain sha256 ac564953a147f7ff7a44632896ea5e93d46ba3e25f418704b19d7ecce71623c9,
  120/120, sweep 101/0. AWAITING IN-GAME TEST (HA1..HA6).

## Ruled Out
- 2026-10-22: "Rod of the Mind's Eye 0x1663 is in the Equip-Spell activation tree @0x021F076E" -- FALSE. The arm
  is entered by `bgt` from 0x021F075E with r0 = 0x1EFA, so `subs r0,r0,#7` builds 0x1EF3. baseimm_scan tracks
  registers in a STRAIGHT LINE and ignores branch targets: any hit whose instruction is a branch target must be
  re-read by hand. (Caught before any test; BUILD 23 was rebuilt with the site stock.) Demotion's 0x021B845C/64 and
  Rod's 0x02199C44 are straight-line stores (ldr; str; adds/subs; str) -> genuine.
(none yet)

## Open Questions
- Does r4 actually reach the equip card's leave dispatcher call as r3? (loop body after 0x021CBC52 not traced)
- Which stock cid (if any) already tests 0x400000 (arm 0x021C919E tests [sp+0x20] && 0x400000)?
- E1 shape: precedent for an ignition on a face-up equip spell (Spark Blaster 0x1909).
- "Noble Arms"/"Infernoble Arms" set code: NDS has no such cards; 3DS index to check.

## Next Experiment
- Scan all cids through TREE 1 to find the owner of arm 0x021C919E (0x400000 consumer).

## Hauteclere E1 does not destroy itself (user 2026-10-27: "does not destroy itself when it activates its effect";
attack part worked)
- CONFIRMED by execution over rom_all_patches.ml4 (Hauteclere in S/T zone 7): VALID_AT 0x0224A925(desc, 0, 7) = 0
  for cls3 desc 0x1F71, = 1 for 0x1663. VALID_AT runs the record's +08 filter on the zone; HA E1FILT only admits face-up
  monsters in zones 0..4, so the self-destroy was always skipped. Durendal/Joyeuse have +08 = 0.
- FIX: E1RES destroys after LOCATE (found, zone 5..9) without VALID_AT.
  APPLIED: chain sha256 1d350c1536a033d8d39d7ad978d773bbb8468beca3af31ec634e46c5936be1b6, 120/120, sweep 101/0 -- AWAITING IN-GAME TEST.

## Hauteclere: in-game confirmed by user 2026-10-27 on chain d432355a ("All three confirmed, ship").
