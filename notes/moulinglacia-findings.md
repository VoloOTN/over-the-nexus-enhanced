# Moulinglacia the Elemental Lord — findings

Status (2026-10-06): WHOLE CARD in-game confirmed by user; SHIPPED 2026-10-06 (steps.STEPS 98 steps, after
patch_grandsoil; SHIPPED list; 0x1C1A moved into patch_grandsoil.C5_CIDS, ledger claim 72 -> 80 B). EE chain
rom_all_patches.nds sha256 8c8c666b...80df66a0 == the in-game-tested rom_moulinglacia.nds byte for byte; sweep
84 passed / 0 failed; ledger OK; KB 657 / 583 PASS (+ card.random_discard_opponent_hand,
card.mandatory_summon_trigger_cond_gate). Pre-ship chain kept as rom_all_patches.pre_moulinglacia.nds.
Earlier: plan approved (~\.claude\plans\moulinglacia-the-elemental-lord-zesty-sutherland.md).
Scope: whole card, staged A (C1+C2) -> B (C3+C4) -> C (C5), user-chosen 2026-10-06. Nothing built yet.
Donor: Venom Cobra 0x1C1A (user-chosen 2026-10-06). Empty-opp-hand ruling (user): activates, discards 0,
HOPT spent.

Text (scratch/ygoprodeck_cache.json id 13959634): Lv8 WATER Sea Serpent 2800/2200.
C1 nomi / C2 exactly 5 WATER in GY, from hand / C3 If SS: discard 2 random from opp hand (all if < 2) /
C4 HOPT on C3 / C5 face-up leaves field -> skip BP of your next turn.

## Confirmed
- donor_scan --free 2026-10-06: 0x1C1A Venom Cobra Lv4 EARTH Reptile 100/2000 = clean (zero aligned
  u16/u32 occurrences in ov3 + arm9).
- WATER = 3 in the 0x021B1810 numbering: KB gy.count_by_attribute (VERIFIED, otn_enhanced/docs/engine/donor_card_technique.yaml:84).
- 3DS (agent byte reads 2026-10-06): Moulinglacia 3DS cid 0x2811; event-trigger row @0x6C5594
  {0x2811, res 0x4134BC, 0, +0C 0x49C570 (HOPT check), +10 0x400EF0 (HOPT post), 0}; hand-SS procedure
  row {0x2811, 0x4B5F64} (same handler as Grandsoil); in SS-trigger list 0x6AD4D0 (twin of NDS 0x0228F63A)
  and class-2 nomi list 0x685E8E; NO criteria row. Resolver case: 0x3D9764(1-desc[2], r1, 2) unclamped.
- NDS random-discard primitive 0x022599C8(side, opp_flag, count) -> 0x0225985C(side, 3, opp_flag, count)
  (agent bytes). Fuh-Rin-Ka-Zan @0x0221D5FC: r0 = 1 - desc[2], r1 = 1, r2 = 2. Thestalos cls1[431]
  {0x182E, 0x0221D151, 0,0,0,0} = mandatory summon trigger, +0x10 == 0.
- timing_class_hook.py:9-15: +0x10 == 0 -> class 0 (no timing arm needed).
- Reuse map (agent, 2026-10-06): CAVE_FREE 0x023A5120, ceiling 0x023AA120; hand-SS table 8/15 rows;
  nomi phantoms 0x0EB3 / 0x176C free; c79 phantoms 0x0E17 / 0x164A free; C5 ov3 host 0x0220A158 72/104 B,
  a 2-cid stub assembles to 80 B.

- Set-code: donor_scan's zero aligned u16 hits in arm9 covers the set-code thunk lists -> 0x1C1A is in none.
- patch_grandsoil.sscond_stub now takes (attr, count) with defaults EARTH/5; its output == the chain's
  installed CAVE_GS_SSCOND bytes (56 B, script 2026-10-06) -> Grandsoil unchanged.
- STAGE A BUILT 2026-10-06: data/over_the_nexus/working/rom_moulinglacia.nds sha256
  c887a750...fc849ee3, layered on rom_all_patches.nds (newer than every patch module). --verify 6/6 PASS.
  CAVE_ML_SSCOND 0x023A5120 disasm: 0x021B9ECD free zone, 0x021AD871 canSS, 0x021B1811(side, #3) cmp #5.
  Nomi 0x0EB3 -> 0x1C1A. check_allocations [OK]. Sweep on the test ROM: 83 passed, 0 failed.
  C1 + C2 in-game confirmed by user 2026-10-06 on sha256 c887a750...fc849ee3. User's report, verbatim:
  "All confirmed, move on to Stage B" (5-step test: 4/5/6 WATER, no NS/Set, Grandsoil/Striker/Elder).
  NOT shipped.

### Stage B (C3 + C4), 2026-10-06
- +0C IS CONSULTED FOR A CLASS-0 SUMMON TRIGGER -- proven by native precedent, not traced: scan of stock cls1
  rows in the summon lists with +10 == 0: Fortune Lady Water 0x20FD ("If this card is SS while you control a
  'Fortune Lady'...: Draw 2", mandatory) = {0x22065B9, 0, 0x2200F39, 0, 0} -- its gating condition lives in +0C.
  Also Karakuri Nishipachi 0x238A {.., +0C 0x21F4D4D, 0, 0}. Thestalos 0x182E = all-zero mandatory shape.
- Discard call, disasm this session: Don Zaloog res 0x022152DC arm desc[+0x18]==1: r0 = 1 - desc[2], r1 = 1,
  r2 = 1, bl 0x022599C8, return 0. Fuh-Rin-Ka-Zan 0x0221D5FC same with r2 = 2. Primitive 0x022599C8 ->
  0x0225985C: [0x..+0x70] = side, +0x74 = 3, +0x3C/+0x3E = r1/count, bl 0x0225981C (posts a request).
- Wiraqocha 0x0222D39E: hand count = WORD [0x0229ACA0 + ((1 - desc[2]) & 1) * 0xB3C]; clamp then same call.
- cls1 phantom scan (scratchpad ml_phantoms.py): one row in stock AND chain, no card_prop, unclaimed: 57 cids;
  picked 0x1C5F (nearest 0x1C1A, 13 rows shift). c79 0x0E17 present in both; only other claim = populate_table.
- thumb_asm has no muls / bls (only beq/bne/bge/blt/bgt/ble) -> branch on opp 0/1, signed ble on hand count.
- STAGE B BUILT 2026-10-06: rom_moulinglacia.nds sha256 d8cbf546...5be99e3e (layered on rom_all_patches.nds).
  --verify 12/12 PASS; sweep 83/0; ledger [OK]. CAVE_ML_RES 0x023A5160 (80 B): post 0x021D2585(side,0x1C1A,1,0);
  opp = (1 - desc[2]) & 1; n = min(2, [0x0229ACA0 + opp*0xB3C]); n -> 0x022599C9(opp, 1, n); return 0.
  CAVE_ML_COND 0x023A51B0 (36 B): 0x021A14E9(side, 0xB, 0x1C1A, 1) ? 0 : 2. cls1 {0x1C1A, 0, RES|1, 0, COND|1, 0, 0}.
  N-or-SS 0x0E17 -> 0x1C1A. C3 + C4 in-game confirmed by user 2026-10-06 on sha256 d8cbf546...5be99e3e.
  User's report, verbatim: "All confirmed, move on to Stage C" (6-step test: opp hand 3+/1/0, 2nd SS same turn
  no discard, next turn discards again, regressions). Class-0 +0C consultation therefore settled in-game.
  NOT shipped.
### Stage C (C5), 2026-10-06
- patch_grandsoil.c5_stub(base, cids=(0x1110,)): default output == chain's installed 72 B (script 2026-10-06).
  2-cid (0x1110, 0x1C1A) = 80 B <= 104 B host, Thumb-1 clean.
- EXECUTION PROOF scratch/c5_two_cid_equiv.py (thumbemu, 160 inputs: cid x left x face-up x owner x TP; the
  installed 104 B host vs the 2-cid stub): every cid except 0x1C1A identical (post args, [sp+0x18], sp, r1-r4);
  0x1C1A == 0x1110 (posted 4/4 when left && face-up). [OK].
- STAGE C BUILT 2026-10-06: rom_moulinglacia.nds sha256 8c8c666b...80df66a0. --verify 13/13 PASS. Installed
  stub disasm: cmp 0x1110 beq go / cmp 0x1C1A bne out / ... post 0x021D2585(owner, 0x1502, 0x21|0x11, 0).
  Sweep 82 / 1 FAIL = patch_grandsoil's ONLY "C5 stub == 1-cid" check (2nd cid local until ship; expected,
  same pattern as Grandsoil's local timing arm). C5 in-game confirmed by user 2026-10-06 on sha256
  8c8c666b...80df66a0, verbatim "All confirmed, ship it" (6-step C5 test + regressions). WHOLE CARD
  CONFIRMED; user approved shipping 2026-10-06.
- SHIP TODO: move 0x1C1A into patch_grandsoil c5_stub default (or a C5_CIDS there), claim 72 -> 80 B at
  check_allocations.py (0x0220A158 grandsoil row), steps.STEPS after patch_grandsoil, SHIPPED, donor pool note.
- Known deviation vs 3DS: HOPT stamped at RESOLUTION (3DS stamps at activation via +10); +10 must stay 0 for
  class 0. Matters only if the trigger is negated (then HOPT is not spent).

## Ruled Out

## Open Questions
- Does a class-0 cls1 summon trigger consult +0x0C (cond)? Prove before Stage B code.
- Venom Cobra set-code membership (thunk table 0x0209D0D8).
- cls1 phantom for Stage B (one row in BOTH rom.nds and chain).

## Next Experiment
- USER IN-GAME TEST of rom_moulinglacia.nds (normal duel), Stage A 5-step test (see session report).
- Stage B static: prove a class-0 cls1 summon trigger consults +0x0C; scan for a cls1 phantom.
