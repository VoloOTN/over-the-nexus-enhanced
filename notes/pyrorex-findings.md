# Pyrorex the Elemental Lord — findings

Status (2026-10-06): plan approved (~\.claude\plans\pyrorex-the-elemental-lord-majestic-codd.md).
Whole card in one build (user request). Donor: Harpie Girl 0x181F (user-chosen 2026-10-06).
Status (2026-10-06): WHOLE CARD in-game confirmed by user; SHIPPED 2026-10-06. User's report on build 2
(faa1dfee...), verbatim: "All confirmed, ship it". steps.STEPS 99 steps (after patch_moulinglacia), SHIPPED list,
timing arm in timing_class_hook.ARMS, 0x181F in patch_grandsoil.C5_CIDS (ledger 0x0220A158 80 -> 92 B). EE chain
rom_all_patches.nds sha256 faa1dfee5aae1b719cb1b450a0ae696c85c0364f9271bbf03f781ec5efb4bec1 == the in-game-tested
rom_pyrorex.nds byte for byte; sweep 85 passed / 0 failed; ledger OK; KB 661 / 587 PASS / 0 FAIL
(+ card.target_step_board_vs_criteria). Pre-ship chain kept as rom_all_patches.pre_pyrorex.nds (8c8c666b...).

Text (scratch/ygoprodeck_cache.json id 35842855): Lv8 FIRE Dinosaur 2800/2200.
C1 nomi / C2 exactly 5 FIRE in GY, from hand / C3 When SS: you can target 1 opp monster; destroy it, and if
you do, both players take damage = half its ORIGINAL ATK / C4 HOPT on C3 / C5 leaves face-up -> skip next BP.

## Confirmed
- 3DS Pyrorex 0x289F (agent byte reads 2026-10-06): event row @0x6C5924 {0x289F, res 0x41B71C, +08 0x3F033C,
  +0C 0x49C570, +10 0x400258, +14 0x477BB8}; NO criteria row (0x289E -> 0x28A5); hand-SS row {0x289F,
  0x4B5F64}; in nomi list 0x685E8E + SS-trigger list 0x6AD4D0. Resolver = shared state machine; amount =
  half card-data ATK (Ancient Gear Explosive arm), damage both (Ring of Destruction arm).
- NDS twin resolver 0x02210311 (disasm this session, stock): phase 0x80 0x022349B0(desc,0,sp+4) target ->
  0x0224A924 revalidate -> amount by cid switch (unknown cid = 1000 / no damage -> can't reuse as-is) ->
  str [0x0229AAFC+0x74] amt, +0x78 side -> bl 0x021D28A4 -> bl 0x02204674(desc) -> return 0x7F.
  Phase 0x7F: [0x0229C314+0x14]==0 -> skip; RoD arm 0x02210560 damage 0x021CFBC8(desc,1-desc[2],amt) then
  0x022105E8 0x021CFBC8(desc, r1, amt); 0x022105EE bl 0x021D2964; return 0. Invalid target -> return 0.
  Edge Hammer arm 0x022103FA: cid = [0x0229AC94+(side&1)*0xB3C+zone*0x14+0x34]&0x3FFF -> bl 0x0202AC08
  (original ATK, '?' -> 0).
- cls +0C consumer 0x0224AE06..0x0224AE30 (disasm this session): r6 = +0C(desc, [sp]); if r6 == 1 AND
  +08 != 0 -> 0x0224A988(desc, +08) target sweep, r6 = found ? 1 : 0. Return 2 skips the sweep.
  Fortune Lady Fire cls1 +0C 0x021F4D4C returns 1 (normal path) with an +08 filter = native twin.
- 0x0224A114 = movs r0,#2 ; bx lr (Dream Clown-style +0C).
- FIRE = 4 (KB gy.count_by_attribute VERIFIED).
- Harpie Girl 0x181F ARM9 u16 hits (chain + stock identical): 0x0204D1A8 (ARM code), 0x0209C8D0 = entry 7 of
  set-code 0x14 list (thunk 0x02023905, list 0x0209C8C4, n 13: 0DCA 0FE4 0FE5 1128 1246 1477 181F 182A 182B
  182C 183F 1A1E 1BC7), 0x020AA964 / 0x020AAA02 unsorted cid runs.
- Slot survey (agent 2026-10-06): CAVE_FREE 0x023A51E0; nomi phantom 0x176C (last); c79 0x164A (last); cls1
  0x17E0; hand-SS 9/15; timing hook 268 -> 292 B / 0x200; C5 stub 3 cids 92 / 104 B.

- Set code 0x14 = HARPIE (names printed 2026-10-06: Harpie Lady / Sisters / Pet Dragon / Feather Duster / Cyber
  Harpie Lady / Harpie Girl / Harpie Lady 1-3 / Hunting Ground / Pet Baby Dragon). Filler 0x181E: no card_prop,
  no ledger mention, sorts between 0x1477 and 0x182A. KB setcode.harpie_0x14 VERIFIED.
- 0x020AA964 / 0x020AAA02: inside an ARM9 table at 0x020AA7D4 (header 0x33,0x33 then 0x05xx ids; nearest
  pointer at 0x02019B58). No ov3 reference -> treated as pack/deck data, cosmetic. ASSUMED (not traced).
- 0x022349B0 reads r0..r2 only (disasm). 0x021D882C = push ; ldr r3,=0x1412 ; bl 0x021D6E40 (disasm).
- EE chain rebuilt 2026-10-06: 98/98, sha256 8c8c666b...80df66a0 == shipped (grandsoil slot4_stub cid param and
  the card_text 0x181F entry are chain-neutral). Pre-build copy: rom_all_patches.pre_pyrorex.nds.
- BUILT 2026-10-06: data/over_the_nexus/working/rom_pyrorex.nds sha256
  bddf5f41510fc15a4a47f9ef0b6b4f2c2d401a7835382a205c2da0cb28e9e8f6 (layered on the chain). --verify 18/18 PASS.
  Stubs: SSCOND 0x023A51E0 56 B, RES 0x023A5220 204 B, COND 0x023A52F0 36 B, SLOT4 0x023A5320 44 B; all Thumb-1.
  cls1 {0x181F, 0, 0x023A5221, 0x021D882D, 0x023A52F1, 0x023A5321, 0x02234DA5} over 0x17E0; N-or-SS 0x164A ->
  0x181F; nomi 0x176C -> 0x181F; Harpie list 0x181F -> 0x181E; C5 stub 92 B (3 cids); timing stub 292 B.
- Sweep on rom_pyrorex.nds: 72 passed / 12 failed = the 11 timing-arm owners' "shared stub == tch.stub(ARMS)"
  checks + grandsoil/moulinglacia "C5 stub == C5_CIDS" checks ONLY (local additions until ship; expected).
- EXECUTION PROOFS 2026-10-06: scratch/pyrorex_equiv.py -> C5 176 inputs, only 0x181F changed and == 0x1110;
  timing 558144 inputs, only 0x181F differs and == 0x1110. scratch/pyrorex_res_exec.py -> resolver 60 cases:
  0x80 amt = ATK/2, push+destroy(desc), 0x7F; invalid target -> 0, no push; 0x7F damage (1-desc[2]) then
  desc[2] only if destroyed; always pop.
- KB 2026-10-06: 660 facts, 586 PASS / 0 FAIL (+ card.cond_return_1_runs_target_sweep,
  card.destroy_then_damage_both_protocol, setcode.harpie_0x14).

### In-game test 1 (rom_pyrorex.nds bddf5f41...), user report 2026-10-06
Verbatim: "1. Confirmed 2. The effect prompted but it did not let me select any monster (see .ml3 before
activation, .ml4 after activation (before choice being made), .ml5 (effect 'resolving', nothing was selected)
3. Could not verify 4. Confirmed 5. Confirmed 6. Confirmed 7. Confirmed 8. Confirmed"; clarified: the prompt was
the Yes/No, no LP change, nothing destroyed. So C1/C2, C4, C5, Harpie removal, regressions: in-game confirmed by
user 2026-10-06 on bddf5f41...; C3 FAILED (no target selection).
- ROOT CAUSE (proven 2026-10-06): patch_pyrorex set +14 = gs.TARGET_STEP = 0x02235605 (Grandsoil's CRITERIA-ROW
  target step: 0x02234E78 param -> 0x02243FA8(side, cid, param) count; 0 -> return 1, no picker). 0x181F has no
  criteria row -> 0 candidates. The plan said 0x02234DA5 (board step: 0x0224AA94 counts via find_event_handler
  record +08 over both fields). Fortune Lady Fire cls1 = {0x02210311, 0x021E18DD, 0x021F4D4D, 0, 0x02234DA5}.
- scratch/pyrorex_ss_exec.py over ml4 RAM: find_event_handler(cls1 desc 0x181F) -> the 0x181F row @0x022888C4;
  0x0224AA94 count = 1; +08(desc, side 1, zone 2) = 1 (opp monster 0x1FCF). ov5 stubs resident in ml3/4/5.
- FIX: TARGET_STEP = 0x02234DA5. REBUILT 2026-10-06 on the same chain (8c8c666b...): rom_pyrorex.nds sha256
  faa1dfee5aae1b719cb1b450a0ae696c85c0364f9271bbf03f781ec5efb4bec1; --verify all PASS; installed cls1
  {0x181F, 0, 0x023A5221, 0x021D882D, 0x023A52F1, 0x023A5321, 0x02234DA5}. Only the cls1 +14 word differs from
  build 1. C3 (and step 3, face-down target) AWAITING IN-GAME TEST.

## Ruled Out
- Board/+08 filter or record lookup as the cause (pyrorex_ss_exec: count 1 with the board step).
- Reusing 0x02210311 unchanged: its cid switch defaults to 1000 dmg / no damage for unknown cids.
- Criteria row: not needed (on-field target via +08, like RoD / Fortune Lady Fire / 3DS).

## Open Questions
- (answered) set code 0x14 = Harpie.
- Native chain-depth push/pop 0x021D28A4/0x021D2964 mirrored; Oviraptor's destroy-then omits them. Effect on a
  destroyed monster's own trigger is untested.

## Next Experiment
- (done) shipped 2026-10-06.
- (done 2026-10-06) SHIP TODO: timing arm into tch.ARMS, 0x181F into gs.C5_CIDS (+ ledger 0x0220A158
  80 -> 92 B), steps.STEPS after patch_moulinglacia, SHIPPED, donor pool note (Harpie Girl -> used).
