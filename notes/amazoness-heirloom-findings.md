# Amazoness Heirloom — findings (donor Molting Escape 0x2124)

Status: **all 9 oracles in-game confirmed by user 2026-09-15** ("All confirmed, Ship it!") on
rom_amazoness_heirloom.nds sha256 02007fb2...0326fab0. SHIPPED 2026-09-15 to steps.STEPS (66/67) +
_verify_all_patches.SHIPPED. EE build 67/67 sha256 e98f536ac5487b5f465ea07395eeb26962f8236987326df2d5b13830a6da994e;
verify sweep 55 passed / 0 failed. Plan: ~\.claude\plans\amazoness-heirloom-bright-wave.md

Text (scratch/ygoprodeck_cache.json): "Equip only to an "Amazoness" monster. Once per turn, that
monster cannot be destroyed by battle. After damage calculation, if the equipped monster attacks a
monster: Destroy the attacked monster."
C1 target lock / C2 once-per-turn battle protection / C3 after-dmg-calc destroy attack target.
User put ALL 3 clauses in scope 2026-09-15 and chose donor Molting Escape 0x2124.

## Confirmed (2026-09-15, static reads by research agents this session — re-proven below where marked)
- NDS pool lacks 0x23F9 (Heirloom), 0x23F3, 0x23FA (`read_card_prop` on working/rom.nds).
- 3DS cid 0x23F9 (CARD_Name idx 4346). 3DS impl = shared rows only:
  - C1 equip-target table 0x6A435C {u16 cid,u16 type,u16 val} x165, row @0x6A4614 `F9 23 04 00 05 00`
    (type 4 = has_set_code(cid,val)); reader 0x3F0558.
  - C2 battle-protect switch 0x1BDD28: Heirloom limit 1 with Molting Escape 0x2124; counter key 0xFB6.
  - C3 after-dmg-calc stage 0x1B9FA0 switch 0x1BAE80: Thorn of Malice 0x2007 + Heirloom -> event 0x10
    (attacker only, not direct); trigger row 0x6C3C2C router 0x458A00 filter 0x3E80A8 (case = is attack target).
- NDS set code 0x05 = Amazoness: thunk 0x020237C8, list 0x0209CAB0 n=19 (movs r2,#19 @0x020237CC);
  phantoms 0x143E/0x23F3/0x23F9/0x23FA.
- Molting Escape 0x2124 per-cid refs (symbolic scan): C2 arm 0x02198BEA..C64; Reptile lock 0x021D78A2 ->
  0x021D7F38; End-of-DS walker gate 0x0225223E; cls1[1090] @0x0228C704; +300 stat arm 0x021B71E4;
  attach reset 0x021C4AC6; ov5 AI 0x022D8A02/0x022DFB66/0x022EC682/table 0x0239740E. No grant row.

## Pre-build proofs (2026-09-15, capstone on working/rom.nds AND rom_all_patches.nds — identical)
- P1 PROVEN Fist filter 0x021E1478: `f8b5 push{r3-r7,lr}; ldr r3,=0x1010; adds r7,r0; adds r5,r1;
  adds r6,r2; bl 0x021D6E40; cmp r0,#0; bne; movs r0,#0; pop`. Arm 0x021E1576 uses only r5/r6/r7:
  `bl 0x021A3C78(r5,r6)` (in battle) ; `bl 0x021A0DF8(desc[2],desc[3])` (equipped monster loc) ;
  ret 1 iff loc != (zone<<8|side). All exits `pop {r3-r7,pc}`.
- P2 PROVEN by P1: 0x021D6E40(r0 desc, r1 side, r2 zone, r3 mask) -> r0 bool.
- P3 PROVEN post site 0x022517C6 `2549 8842` (ldr r1,=0x2007 [pool 0x0225185C]; cmp r0,r1; bne 0x022517E0).
  r1 overwritten on every exit (0x022517D6 / loop 0x0225179A / 0x022517EE) before read; LR already
  clobbered by bl 0x021A36EC @0x022517C2. Not-direct check `ldrsb [r6,#2]` follows; then
  0x021D3230(eqSide r5, eqZone r7, 0x10, 0).
- P4 PROVEN cls1 base 0x022860D4 x0x535 stride 24: [594] Fist {1ABC,0,022048FD,021E1479,0,0,0};
  [993] Thorn {2007,0,022089E9,021DA319,0224A115,0,0}; [1090] Molting {2124,0,0222D5FD,0,02201169,0,0};
  [1283] Daredevil / [1312] Tiki both {+04 022048FD, +0C 0}.  => donor row = Fist row with +08 swapped,
  +0C = 0 (CORRECTION to plan, which said Thorn's 0x0224A115).
- P5 PROVEN target check 0x021D7348: r5 = cid from 0x021A3320 @0x021D73A6; Ancient Gear arm
  0x021D7C60 `281c 4bf637fe 88e2` = adds r0,r5 ; bl 0x020238D4 (set 0x11) ; b 0x021D817A (add sp,#0x1c;
  pop{r4-r7,pc}). Molting arm 0x021D7F38 `0498 2105 0842 00d1 0024 7ce5` (12 B), ONLY branch source
  0x021D78A8. Set-code ptr table 0x0209D0D8: [5] = 0x020237C9 `0149 024b 1322 1847` (list 0x0209CAB0,
  n=0x13, search 0x02022E15); [0x11] = 0x020238D5.
- EoDS walker: [sp+0x24] = [sp+0x28] = 0x21D6-0xB2 = 0x2124 (0x022521AE..BC); 0x0225223E `10da`
  bge 0x02252262 -> b 0x02252390 queue (0x021D3230(r7,[sp+0xC],0,0)). `1ada` -> 0x02252276 -> b 0x0225239C skip.
- P6 PROVEN no finished_patches/allocations.yaml reference to any site ±8 B. CAVE_FREE = 0x0239F8D8.

## Ruled Out
- Thorn of Malice / Ancient Gear Fist / Legendary Sword as donors (user chose Molting Escape; reasons in plan).
- Tiki/Stella filter 0x021E32E4 for C3: returns 1 by default for cids 0x2078..0x249A -> would destroy everything.
- Driven Daredevil filter 0x021DB54C for C3: keys on (cid,kind4) tag, which C2 puts on OUR monster.

## Build (2026-09-15) — AWAITING IN-GAME TEST
- `patch_amazoness_heirloom.py` + `_build_amazoness_heirloom.py` (on rom_all_patches.nds).
  Output data/over_the_nexus/working/rom_amazoness_heirloom.nds sha256
  02007fb2f29a68c5dd212edf424da653ea9720547c8e27d2b6d3408a0326fab0; verify() 10/10 PASS.
- Edits: A 0x021D7F38 `281c4bf645fc1ce1` (adds r0,r5; bl 0x020237C8; b 0x021D817A);
  B 0x022517C6 bl CAVE_HEIRLOOM_POST 0x0239F8D8 (0x18); C cls1[1090] {2124,0,022048FD,0239F8F1,0,0,0};
  D 0x0225223E 10da->1ada; ov5 CAVE_HEIRLOOM_FILTER 0x0239F8F0 (0x30). CAVE_FREE -> 0x0239F920.
- card_text CARD_TEXT[0x2124] added (apply_to_rom is per-cid; chain text guards are compare-only,
  so the unwired chain build is unaffected).
- KB: setcode.amazoness_0x05, equip.target_check_switch (corrects equip.target_gate_unlocated),
  battle.after_damage_calc_attacker_equip_post, battle.destroy_step_and_battled_filter,
  battle.molting_escape_wiring — all PASS (464 PASS / 0 FAIL). check_allocations OK.
- NOT wired into steps.STEPS / SHIPPED; no chain build / sweep (card still being tested).

## Open Questions
- None for this card. Answered in-game 2026-09-15: 0x021D7348 IS the equip-target gate (C1); cls1 +0C = 0
  activates correctly off the event-0x10 post (C3).
- Pre-existing `equiv --all` DIFFERS (not caused by this patch) — FIXED 2026-09-15 at the user's request,
  now 14/14 IDENTICAL; shipped ROM unaffected (the build already ran the correct migrated modules):
  - patch_vylon_element: the ORIGINAL was stale — a 2026-06-29 experiment (NATIVE_RES/COND/TAIL + SPY_TAG,
    the in-game "summoned nothing" record) never reverted. Restored the full Spy record (SPY_RES/COND/TAIL).
  - patch_bulk_ydcs: harness artefact. The original does ROM I/O on out+".bak" + a same-path copy back
    that Session swallows, so inside equiv it changed nothing (orig==base proven; migrated changed 35
    decks; built ROM verify(): all 305 decks match CHANGES). equiv.py now runs REAL_IO originals on disk
    and folds changed files back in.

## Next Experiment
- None (shipped).
