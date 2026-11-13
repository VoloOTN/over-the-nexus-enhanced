# C effect stubs: findings

## Confirmed (2026-11-03)
- Toolchain: Arm GNU Toolchain 14.2.Rel1 at `~\tools\arm-gnu-toolchain` (override with `ARM_TOOLCHAIN`).
  The zip's sha256 `6facb152…94e1` matches Arm's published `.sha256asc`.
- `python -m otn_enhanced.asm.cc` self-check passes: a C call to `draw` compiles to one direct `BL 0x021D12F4`,
  there is no Thumb-2, and a mutable global is rejected by the linker `ASSERT`.
- Engine symbols come in through `.thumb_set` (asm/c/engine_syms.txt), so every call is a Thumb `BL`. The
  idea comes from CardWorkshop tools/inject.py (BlueKitkallos, MIT).
- Mystic Piper C resolver (`otn_enhanced/cards/c/mystic_piper.c`): 72 B, exactly the 0x48 `CAVE3_PIPER_RES` slot.
  Its disassembly calls `reveal_top 0x021D2624`, then the Deck-top read (`0x0229AF98 + side*0xB3C`, masked to 14
  bits), then `draw 0x021D12F4`, `is_monster 0x02029E60` and `cid_level 0x0202ABD8`; if the level is 1 it draws
  again, and it returns 0. `_build_mystic_piper_c.py` verify: 9/9.
- KB: added `engine.reveal_top_0x021D2624` (ANCHORED; it has a `push {r4, lr}` prologue) so engine_syms can cite it.

- Phase 0 step 1 done: `compile_c` takes one file or a list, `.c` and `.S` mixed, same linker script. Self-check
  proves a `.S` entry assembles to exact bytes (`10b5 0248 ...`, pool via `.ltorg` at +12, `bl draw` -> 0x021D12F4)
  and that a `.S` entry can call a C helper. Piper C build still 72 B, verify 9/9.

- Phase 0 step 2 done: `python -m otn_enhanced.tools.c_corpus [ROM]` -> `scratch/c_corpus.json`. It reuses
  check_allocations' own parsers (ov5 CAVE_*, CAVE3_*, OV3_CLAIMS), so it can't drift from the ledger. Run against
  `rom_all_patches.nds` (Nov 3 09:10): ov3_dead 34 slots / 1128 B, ov3_pool 156 / 7192 B (4 empty = latch/scratch),
  ov5 633 live / 66568 B (153 empty, 122 unsized -> bounded by the next slot, capped 0x100). The empty ov5 slots are
  latches/scratch/diag or cards already moved to the ov3 pool (tg_shared, boggart, piper...): nothing to convert.

- Phase 0 step 3 done: `otn_enhanced/tools/c_equiv.py` `equiv(old, new, base, args, ss=None)`. Self-check: Piper's
  ROM bytes (CAVE3_PIPER_RES from rom_all_patches) vs `mystic_piper.c` equal over 469 swept paths (returns 0/1/2/-1
  per call, hash-filled memory); a 1->2 draw-count mutation, a frame read and a dropped store are all caught.
- Comparing all of r0-r3 at an engine call is WRONG: Piper's first run differed only in r2 at `draw` (2 args): dead
  scratch. Args are now compared up to the callee's arity from the engine.h prototypes; undeclared callees compare
  all four. After each call r1-r3 are poisoned identically (the real callee clobbers them).
- `scratch/dis.py` shadows the stdlib `dis`: anything that puts scratch/ FIRST on sys.path breaks dataclasses.

- Phase 0 step 4 done: `otn_enhanced/tools/c_callee_audit.py [ROM]` -> `scratch/c_callee_audit.json`. Static walk of
  every branch from the callee (tail `b` followed with the sp delta carried): FAIL on any sp access at/above entry
  sp or a read of r4-r12 before it's written; UNKNOWN on indirect bx, sp/pc hi-reg ops, ARM code. Self-check: 4
  synthetic cases (own-frame read PASS; stack arg, bare r4 read, push-then-r4 read all FAIL).
  Over rom_all_patches: 209 fronts -> 161 distinct targets: 23 PASS (40 fronts, plain C OK, e.g. is_monster
  0x02029E60), 42 FAIL (66 fronts, front shim), 9 UNKNOWN (human look: jump tables, indirect bx), 87 INTERNAL
  (jumps into our own slots: shared tails, not native callees).
- The FAILs are mostly mid-function resume points (reads r4-r7 at entry, or returns with sp delta 24/56): the
  front hands back into the middle of an engine function, so they need the front shim by construction.
- Deviation from the plan: per-callee KB facts are NOT written yet (161 of them). The JSON is the record; a
  callee gets its KB fact when the first front that relies on it converts.

- Phase 0 step 5 done: `otn_enhanced/asm/c/shim.S` has TWO macros, not three: SPLICE_SHIM (C gets `Regs *r` = live
  r0-r7, writable, plus `u32 *frame` = engine sp at the hook) and FRONT_SHIM (same interface; return 0 -> back to the
  engine with r->r[], nonzero -> tail-jump to native with r->r[], lr, sp intact, scratch reg = native). The frame
  shim is SPLICE's `frame` argument. Proof `python -m otn_enhanced.tools.c_shim_proof` (sources in asm/c/proofs/):
  CAVE3_SL_ATKRESET (writes live r4 + engine frame [sp+0xB0]) and CAVE3_SK_NSMATCH (front, both exits) are
  trace-equal to their ROM bytes comparing all r0-r7 on return; a mutated old stub (r4=1 / K+1) fails each proof.
- The first FRONT design (C gets plain r0-r3 args, scratch zeroed on return) was WRONG for SK_NSMATCH: its return
  path hands r1 = K back to the engine. C must be able to set return-path registers, hence the Regs interface.
- Shim cost vs tiny slots: SL_ATKRESET C+shim 36 B vs 16 B slot, SK_NSMATCH 56 B vs 20 B. Both proof hooks would be
  .S fallbacks (Phase 4). C+shim only pays off where the slot has room (ov5, bigger stubs). Measure per stub.
- c_equiv gained `all_regs=True` (compare r0-r7 on return) for splice/front returns.

- Phase 0 step 6 done: `python -m otn_enhanced.tools.c_classify [ROM]` -> `scratch/c_classify.json` (needs c_corpus +
  c_callee_audit first). It runs the callee-audit walker inside each slot in a new facts mode (exits, frame access,
  hidden r4-r12 reads, unpushed r4-r7 writes). Over rom_all_patches, 666 non-empty stubs: C 398, C+splice 130
  (7 tight), C+front 119 (61 tight = slot < shim + 8 B: likely .S), .S 16 (tiny, or the exact addr_reaches
  list-search shape), REVIEW 3 (CAVE_RUL_ROWS / CAVE_TENKI_ROW / CAVE_SSS_ROW are data rows, not code).
  Spot checks: PIPER_RES/PIPER_COND -> C, SL_ATKRESET -> C+splice (clobber r4, frame sp+0xB0), SK_NSMATCH ->
  C+front, BOGGART -> C+splice (reads r4, clobbers r4/r5, frame sp+0).
- Walker bug fixed: `blx rN` was treated as an exit (UNKNOWN). It is a call; the first classifier run had 336 REVIEW
  from it. The callee-audit verdicts didn't change (23/42/9).
- c_corpus now fills the owner of ov3-pool slots from the cave3.py comment.

- Phase 0 step 7 (KB gate) done for 265/287: `python -m otn_enhanced.tools.c_engine_syms [ROM]` -> scratch/c_engine_syms.json.
  The stubs call 287 distinct engine routines (BL targets + `ldr rN,=X; blx rN` literals outside every slot). 150 already
  had a VERIFIED/ANCHORED fact at exactly that address; 137 did not (the plan's estimate, exactly). 115 of those start
  with `push {.., lr}` and now have `engine.c_entry_0x<addr>` ANCHORED facts (author_facts.py, one data-driven loop after
  reveal_top; all 115 captured ANCHORED, none downgraded). Claim is ONLY "Thumb function entry called by these stubs".
  author_facts --check: 858 PASS / 7 FAIL / 172 UNVERIFIED; the 7 FAILs are pre-existing (3DS extract absent, stale
  tool.rom_files_entries_must_be_bytearray), none are c_entry facts.
- engine_syms.txt / engine.h entries are still added per card as it converts: a name and an arity are a claim the
  anchors don't make. c_equiv reads arity from engine.h, so an undeclared callee is compared on all of r0-r3.

- Phase 0 step 7 KB gate COMPLETE: 287/287 called routines have a VERIFIED/ANCHORED fact. The last 22 (no push
  prologue) were read one by one (disassembly with 6 B of context + the walker in facts mode): 18 are callable
  entries -- 8 set-code thunks at 0x020235F0..0x02023F44 (`ldr r1,=table; ldr r3,=fn; movs r2,#N; bx r3`), 5 other
  arg-setting tail thunks, 5 leaf functions -- all with no hidden register input, no stack access, sp balanced. They
  are `engine.c_entry_0x...` like the rest. 4 are MID-FUNCTION points (`engine.c_midfn_0x...`): 0x021B5E6E,
  0x021CC1CA, 0x021D199E, 0x021DD6D4 -- they read live r5/r7, touch the enclosing frame and return with sp off by
  16..80. cc.py now refuses to put a c_midfn fact in engine_syms.txt.
- CAVE3_SEAL_FILT BLs INTO the middle of a function (0x021DD6D4) and returns through that function's epilogue: a
  hidden frame contract. It must stay .S (or get its own proof) whatever the classifier says.

- Phase 0 step 8 done: `otn_enhanced/c_forms.py` FORMS = {slot: Form(sources, gate, args, all_regs, frame_ok)}.
  `build --c` appends one step (121/120) that, for each form, compiles it, re-proves it against the slot's bytes AS
  BUILT (c_equiv, or byte-identity for .S), checks it fits, then overwrites the slot; any failure aborts. Default out
  `rom_all_patches_c.nds`. `python -m otn_enhanced.c_forms --status` writes notes/c-migration-status.md (one row per
  stub: proposed form, converted form, gate result, size vs slot); currently 1/666 (CAVE3_PIPER_RES).
  First run 2026-11-03: exit 0, 121/120 steps in 372 s, sha256 63bcf2eb677eb683bdf5443f7e11b997fa4271a26d1f324355f91d197a4aaf20.
  Diff vs rom_all_patches.nds: ov3 30 bytes, all inside 0x02220BE4..0x02220C22 (the Piper slot), slot == C blob;
  ov5 and arm9 identical; the only differing file is ov3's. The deck preflight did NOT abort this time.
  AWAITING IN-GAME TEST (only the old single-card Piper C ROM was confirmed, not this chain ROM).
- PHASE 0 COMPLETE 2026-11-03.

- Phase 1 batch 1 (2026-11-03): CAVE3_SEKKA_LOCK (sekkas_light_lock.c, 60/64 B, 18 paths / 2 runs), CAVE_RAIDEN_COST
  (raiden_cost.c, 20/28 B, 5 paths), OV3_DEAD_021B2A4C Gates of Dark World (gates_of_dark_world.c, 24/30 B, 6 paths /
  2 runs) + the Piper pilot: all PASS in c_forms. Wrong-constant mutants (0x10E7 / 0x1C8C) are caught. `build --c`:
  exit 0, 121/120, 377 s, sha256 8457757eaa407b1e9a122665a785e61c5bb74c3b8d610610129e074f61a2fd1f; ov3/ov5 differ from
  rom_all_patches.nds in exactly those 4 slots, arm9 identical. AWAITING IN-GAME TEST (final retest).
- Callee ARITY must be measured, not read off the caller: `c_callee_audit.arg_regs(img, addr)` = r0-r3 the callee may
  read before writing, following nested BLs; an indirect call/tail-jump, an ARM veneer, a cycle or a walker give-up
  counts as all four (upper bound). It agrees with every earlier engine.h prototype (draw 2, reveal/is_monster/
  cid_level 1, turnlog 4). New: activation_prohibited 0x021ECDA4 = 4 (upper bound, walk UNKNOWN; Sekka passes its
  incoming r1-r3 through), fn_02022E14 = r0-r2.
- c_equiv now takes planted memory (`ss={addr: byte}`) and c_forms.Form takes `runs`: a branch on an INPUT or a MEMORY
  value is not swept by the return-value sweep. Gates first passed over 1 path (only cid==0x1C8B ran) -- vacuous for
  the other branch. Any stub with an input/memory compare needs a run per side.

- Phase 1 batch 2 (2026-11-03): CAVE3_OD_TRIG Orient Dragon (24/28 B), CAVE_SEKKA_RES + CAVE_SSS_RES (one shared
  draw2_resolver.c, 20/32 B), CAVE_NK_GAINRES Nikitama (24/32), CAVE_SR_C1COST Scrap Raptor (24/32), CAVE3_ELDER_SSCOND
  (40/42; entry r0 is a SIDE; runs side 0 and 1): all PASS. New callees, arity measured: 0x021E5060 r0,
  0x021AD870 r0+r2 (Elder forwards its incoming r2), 0x021ACF68 r0. `build --c`: exit 0, 377.6 s, sha256
  4c1bbbc4f6270007690e29d073b6312f45dc0a949fc0640e0f4d172e22bd1597; exactly the 10 converted slots differ from
  rom_all_patches.nds, arm9 identical. 10/666 converted. AWAITING IN-GAME TEST (final retest).

- Phase 1 batch 3 (2026-11-03): CAVE3_WNM_SUB_ACT (12/12 B) and CAVE3_SZ_FILTER (16/16) = zone_predicate 0x021D6E40
  with mask 0x118 / 0xC94 in r3; CAVE3_TG_NEGATE (12/14) = fn_02235604(r0); return 1. All PASS. `build --c`: exit 0,
  383.9 s, sha256 3cc1d1c52d8806be02afc459ab1542d9c2eb4341dc7fc2f9fb9d82a82ef3b0ea; exactly the 13 FORMS slots differ,
  arm9 identical. 13/666. AWAITING IN-GAME TEST (final retest).
- Classifier was calling flag-contract stubs C. Added: a conditional branch before anything sets the flags (consumes
  the CALLER's flags, e.g. OV3_DEAD_021B5840), a compare immediately before a return (result IS the flags, e.g.
  CAVE3_HEIRLOOM_POST), and an unbalanced sp at an exit (pops the caller's pushes, e.g. CAVE3_RUL_H8B) -> .S.
  .S 16 -> 75, C 398 -> 385. c_equiv does NOT compare flags at a return, so this classifier check is the only guard.

- Phase 1 batch 4 (2026-11-03): CAVE3_TGW_E1COND (latch planted 0 / nonzero), CAVE3_SR_NSPOST (cid 0xFF6 / other),
  CAVE3_PIPER_COST, CAVE3_SEAL_COND, CAVE3_SR_NSCOUNT (0x02261F84 planted 0xFF6 / other): all PASS. `build --c`:
  exit 0, 409 s, sha256 3cf82ac5a99846147c99c0a21463e2cc6613f7248b1f43aa4f9b14d089ce6d82; exactly the 18 FORMS slots
  differ, arm9 identical. 18/666. AWAITING IN-GAME TEST (final retest).
- CAVE3_SEAL_C3 does NOT fit as C: 32 B vs a 28 B slot (the old stub reuses its own pushed r0-r2 as the second
  call's args). -> .S fallback (Phase 4).
- CAVE3_SL_ATK is NOT a plain function: it returns its bonus in r1 and leaves r0, r2, r3 as the caller passed them.
  A `u64` return reproduces r0:r1, but the C clobbers r2/r3 (0x400064be / 0x021ba0f4 vs 0x22 / 0x33) and whether
  the caller reads them is unproven. -> splice/.S. The classifier still calls such stubs C: a non-r0 result is
  invisible to it.

- Phase 1 batch 5 (2026-11-03): OV3_DEAD_02237DFC Obedience Schooled cost (reuses raiden_cost.c, identical code),
  CAVE_CARDCAR_COST, CAVE_UCT_C4COND, CAVE_WR_AICLASS (cid 0x190B / other), CAVE_NSC_C2RES: all PASS. `build --c`:
  exit 0, 362.6 s, sha256 a65826df5ddc1fbe8390e76d65180020bcbbc153db6179f78a3e2594b0a8c547; exactly the 23 FORMS
  slots differ, arm9 identical. 23/666. AWAITING IN-GAME TEST (final retest).
- Classifier: a return right after a write to r1-r3 (pops skipped) = "returns a value in rN" -> .S. Catches
  CAVE3_SL_ATK and 7 more (e.g. CAVE3_MARA_COUNT, CAVE3_QSR_LEAVE). Needed because the default gate compares only r0
  at a return: an r1-returning stub would otherwise pass falsely. Now C 379 / C+splice 98 / C+front 90 / .S 96.
- Checked 2026-11-03: no c_engine_syms target lies in the ov3 compaction pool (pool_blocks.FREE_RUNS entries are
  (start, END, crc), not (start, size)), so the step-7 c_entry facts are not our own code.

- Slot symbols (2026-11-03): cc.py emits `.thumb_set slot_<NAME>` for every live ledger slot
  (c_corpus.slot_symbols(), the same parsers as the allocation guard). A stub declares the callee in engine.h's slot
  section with the callee stub's measured arity; c_equiv maps slot_* prototypes to addresses for arg comparison.
  Converted with it: CAVE3_SK_NSCOUNT / CAVE3_NK_NSCOUNT (the NS-count chain; node planted 0x3E50 / 0x3E51 and not),
  CAVE3_DENKO_SET (-> slot_CAVE3_DENKO_LOCK, 0 args), CAVE3_RUL_H4 (-> slot_CAVE3_RUL_FINDK, -1 = not found): all PASS.
- cc.py now links 2-ALIGNED slots: base%4==2 links at base-2 behind a SHORT(0) pad that is stripped, so pools keep
  absolute 4-alignment; trailing pad aligns the END address. CAVE3_RUL_H4 (0x021F4C1A) was the first such slot.
- `build --c`: exit 0, 357.5 s, sha256 06349e7efb5bc49ac48c0a6532ababd3caaad7cd25fb9281ac55eb0138c67a27; exactly the
  27 FORMS slots differ, arm9 identical. 27/666. AWAITING IN-GAME TEST (final retest).

- Phase 1 batch 6 (2026-11-03): CAVE_RUL_ATTR (-> slot_CAVE_RUL_KBASE), CAVE_IK_C3COST (Ogier), CAVE_IK_CR_COND2
  (Captain Roland; raw bytes +3 zone / +4 event, 3 planted runs), CAVE3_HAIPA_MUSTATK (sweep adds returns 0xFC8/0xFFD),
  CAVE3_QSR_RES: all PASS. `build --c`: exit 0, 475 s, sha256
  6f24597559e537ad57245e5ed6a0cccb28088dfd8be48165d551527e71c49ba5; exactly the 32 FORMS slots differ, arm9 identical.
  32/666. AWAITING IN-GAME TEST (final retest).
- c_equiv/c_forms gained `returns=`: extra engine-call return values to sweep. A stub that compares a call's RESULT to a
  constant (Haipa: zone cid == 0xFC8 / 0xFFD) never takes that branch under the 0/1/2/-1 sweep.

- c_equiv now compares STACK ARGS and FRAME POINTEES (2026-11-03): engine.h arity is no longer capped at 4; at a call
  the 5th+ args are read as words at sp, and any arg inside the stub's own frame [SP0-0x1000, SP0) is compared as
  ("&frame", pointee word) since the two frame layouts differ. Proven on the real CAVE3_WNM_WRAPPER (deck walker
  0x0223BC3C, 6 args, r3 = &local): the C port is trace-equal over 5 paths; a stack-arg mutant (2 -> 3) and a pointee
  mutant (key + 1) are both caught. Self-check asserts _call_args on a synthetic frame.
- The three deck-walker wrappers (WNM / TGW / TGR) compile to 40 B for 36 B slots -> .S fallbacks (Phase 4); their C
  was removed again. FORMS unchanged at 32, so the last build --c (6f245975...) stands.

- Phase 1 batch 7 (2026-11-03): CAVE3_PIPER_COND (cost_ran planted 0 / 1), CAVE3_NIN_POSRES (5-arg position toggle,
  stack arg compared), CAVE3_SL_CRIT (6-arg criteria registrar), CAVE3_LSD_RES (phase word planted 0x80 / 0x7F),
  CAVE3_RUL_H5 (planted 2-entry list / empty list), CAVE3_ATKTGT_GATE (planted list; returns 0x1234/0x5678 swept):
  all PASS. `build --c`: exit 0, 378 s, sha256 e123f44d5d159dfb2de34045fe54ce00365d20199a5f96cc3fac16e5f71abd86;
  exactly the 38 FORMS slots differ, arm9 identical. 38/666. AWAITING IN-GAME TEST (final retest).
- cc.py no longer pads the blob's end to 4: the pad is not needed (pools are aligned inside the link) and it made two
  38 B ports "40 B" for 38 B slots. Bytes past the code now stay as the old slot bytes.
- c_forms.Form gained `mem` (planted bytes for the DEFAULT run): a loop over a RAM list must have a bounded list in
  every run, or hash memory + nonzero scripted returns run it past MAX_CALLS.
- CAVE3_PINE_RES (Naturia Pineapple) NOT convertible as plain C: it hands 0x0220731C the r2 that 0x021AE4AC left behind
  (callee junk), and 0x0220731C's r2 read is only an upper bound. Needs proof 0x0220731C ignores r2, or .S.
- The 9 deck-walker wrappers (*_WRAPPER, CAVE_SR_DECKFIND, CAVE3_DOJO_CRIT) are all 36 B slots that C makes 40 B:
  all .S fallbacks.

- Phase 1 batch 8 (2026-11-03): CAVE3_WNM_CHECK (returns 0x14 swept), CAVE_OVI_C2COST, CAVE3_TGS_COND (reuses
  elder_six_samurai_sscond.c: same shape), CAVE3_SR_NSFIELD, CAVE3_QSR_EXSEL (6-arg Extra Deck enumerator, key from
  desc+2 if > 0 else cid: 3 planted runs), CAVE3_JS_SSCOND: all PASS -> 44/666. `build --c`: exit 0, 707 s (slow
  run), sha256 c807a7f0714800868157c7015bb938a61b2f1d7c9d0661a75f7e7e47d744da12; exactly the 44 FORMS slots differ,
  arm9 identical. AWAITING IN-GAME TEST (final retest).
- CAVE3_SR_NSFIELD: the old stub's `ldr r2,=0xFF6; cmp r1,r2` LEAVES 0xFF6 IN r2, so both of its calls get 0xFF6 as
  arg 3 (I first wrote a2 there; the trace check caught it on both paths). Watch for compare constants loaded into
  argument registers: they become arguments.
- CAVE3_QSR_COND: C is 46 B for a 44 B slot -> .S fallback.

- Phase 1 batch 9 (2026-11-03): CAVE3_NK_NSFIELD -> slot_CAVE3_SK_NSFIELD -> slot_CAVE3_SR_NSFIELD (the NS-field
  chain; node cid and other), CAVE3_TGW_ARMHOOK (watched cid planted / 0; levels 4 and 5 swept), CAVE_TSH_SSGATE,
  CAVE_AZURE_PROT (Azure-Eyes C2), CAVE_JW_C1_COND, CAVE_SC_COST (Soul Charge): all PASS -> 51/666. `build --c`:
  exit 0, 482 s, sha256 9b67f2bec06707bc4cdc09296142fe8112b4819b9822ff29ca39973ad5829a7e; exactly the 51 FORMS slots
  differ, arm9 identical. AWAITING IN-GAME TEST (final retest).

- Phase 1 batch 10 (2026-11-03): CAVE_ASSD_C1_COND, CAVE_PSI_COND, CAVE_ASSD_C1_SLOT4, CAVE_PSI_SLOT4,
  CAVE_ASSD_C2_COST, CAVE_ASSAULT_C2COST: all PASS -> 57/666. `build --c`: exit 0, 514 s, sha256
  3d9faa790b5bbec754c7300f9f82725cc962ca8bcf030d422d90903a066a4643; exactly the 57 FORMS slots differ, arm9
  identical. AWAITING IN-GAME TEST (final retest).

- Phase 1 batch 11 (2026-11-03): CAVE_CB_LOCK (Crimson Blader; turn-player word planted = / != side),
  CAVE_DR_C3_MAIN (Dragunity Remus C3a splitter; desc+3 planted 0xE / other), CAVE_SR_C1COND (cost_ran 0/1),
  CAVE_SR_C2COND (watched word planted / 0), CAVE_OVI_COND, CAVE_OVI_SLOT4, CAVE_BF_COND (Brilliant Fusion; cost_ran
  0/1): all PASS -> 64/666. `build --c`: exit 0, 382.5 s, sha256
  eceff38d272e8281098b20bdece039ce51283f4554e3639fc6d49623cf428df6; exactly the 64 FORMS slots differ, arm9 identical.
  AWAITING IN-GAME TEST (final retest).
- CAVE_REVSYN_C2COST skipped: after its turn-log post it calls the 4-arg cost 0x021EBA34 with r1-r3 = whatever the post
  left (callee junk), like CAVE3_PINE_RES.

- Phase 1 batch 12 (2026-11-03): CAVE_BF_COST, CAVE_BF_C3COND (-> slot_CAVE_BF_C3FIND, < 0 = none), CAVE_SM_COND,
  CAVE_SM_SLOT4 (Shadow Mist), CAVE_DL_SLOT4 (Dark Law), CAVE_UCT_C2COND (phase 2/4/3 x cost_ran 0/1, 4 runs),
  CAVE_ARCH_SLOT4, CAVE_ARCH_CRIT (deck walker with r3 = NULL: no frame pointer, fits 32/48 B): all PASS -> 72/666.
  `build --c`: exit 0, 710 s, sha256 68889c1b481064a0cfa03612a81819e3f8d17edaa4b8780577a10652c384c3d7; exactly the
  72 FORMS slots differ, arm9 identical. AWAITING IN-GAME TEST (final retest).
- CAVE_BF_COST: `movs r1,#0; strb r1,[r0]` (clearing the latch) leaves r1 = 0, so 0x021D2B88 gets 0 as arg 1, not a1.
  Second instance of a scratch register becoming an argument (after CAVE3_SR_NSFIELD); caught by the trace check.

- Phase 1 batch 13 (2026-11-03): SHARED TEMPLATES. compile_c(defines=) passes -D, c_forms.Form(defines=) sets them per
  slot. cards/c/tpl_opt_cond.c (LOG_CID, KIND, NEXT), tpl_tag_post.c (TAG, LOG_CID, KIND), tpl_settled_post.c (KIND).
  Converted with them: CAVE_OQ_C3COND / CAVE_OQ_C3SLOT4 (Overtex Qoatlus), CAVE_WU_U3COND / U3COST / U4COND / U4COST
  (Wattuna), CAVE_WK_COST (Wattkyuki), CAVE_GS_COND (Grandsoil); plus CAVE_PSI_C2COST: all PASS -> 81/666.
  `build --c`: exit 0, 748 s, sha256 ae19727c53f62c7dc62742538b564d79cf5d2264cc2564fcf0868b219c68ec6d; exactly the 81
  FORMS slots differ, arm9 identical. AWAITING IN-GAME TEST. A template parameter named CID collides with engine.h's CID() macro: use LOG_CID.
- "Callee's own address" junk IS reproducible: `ldr rN,=fn|1; blx rN` leaves fn|1 in rN, and in C (u32)fn evaluates to
  exactly that (the .thumb_set symbol carries the Thumb bit). tpl_settled_post passes (u32)cost_settled as r3 (the
  0x021D2BC8 nest reaches the unboundable ITCM routine 0x0202ABF8); psi_c2cost passes (u32)reveal_cost as r2. Equal by
  construction, whether or not the callee reads it. NOT applicable to junk a previous CALLEE left (Pineapple, Revsyn).
- c_forms --status now reports a compile error as a FAIL row instead of crashing.

- Phase 1 batch 14 (2026-11-03): new template tpl_opt_const.c (LOG_CID, KIND, RET: logged ? 0 : RET). Converted:
  CAVE_GS_SLOT4, CAVE_PX_SLOT4 (tpl_tag_post); CAVE_ML_COND, CAVE_PX_COND, CAVE_WR_COND (tpl_opt_const); CAVE_UZ_COND
  (-> slot_CAVE_UZ_MASK; cost_ran 0/1), CAVE_SK_COST (desc+3 planted 0xB / 4), CAVE_NK_GAINCOND (cost_ran 0/1),
  CAVE_NK_DRAWCOND: all PASS -> 90/666. `build --c`: exit 0, 506 s, sha256
  ee3c2c062beead962b1bb4c2f0e7a7618ae3216dab60d9d46651c4c7b07f3ec2; exactly the 90 FORMS slots differ, arm9 identical.
  AWAITING IN-GAME TEST (final retest).
- CAVE_WR_RES skipped: callee junk again (the 4-arg destroy filter 0x022048FC gets r1-r3 left by the turn-log post).

- Phase 1 batch 15 (2026-11-03): new template tpl_post_then.c (LOG_CID, KIND, THEN). Converted: CAVE_NK_DRAWRES,
  CAVE_NSC_SLOT4, CAVE_NSC_C2COST, CAVE_NEXT_COST (own-address r3 trick), CAVE_IK_O_HANDH (Oliver; 7-arg 0x0223BFD4,
  3 stack args compared), CAVE_IK_C2COND, CAVE_IK_C2SLOT4: all PASS -> 97/666. `build --c`: exit 0, 867 s, sha256
  3dcc0112e208bfeb4642bae8c91149a67e510af446ee6fab2dd3223c220d3d3d; exactly the 97 FORMS slots differ, arm9 identical.
  AWAITING IN-GAME TEST (final retest).
- WRONG and caught: I assumed the three Infernoble C3F2 conditions (Ogier/Maugis/Oliver) hand 0x022043F4 "r2 = the
  queried cid, r3 = 1" left over from the query's arg setup. Registers set up FOR a call are gone after it: r2/r3 at
  the second call are what turnlog_query left (callee junk). Skipped, like Pineapple. The setup-constant trick only
  works when the constant is loaded AFTER the last call (SR_NSFIELD, BF_COST).

## Ruled Out
- (none yet)

## Open Questions
- `build --compare` against rom_baseline was not run: deck preflight aborts on `rpg015_8_jill.ydc` (39 main-deck
  cards), from the `otn_enhanced/data/ydc_decks.py` edit already in the working tree. The shipped path is
  untouched by this work: `cards/mystic_piper.py` is unchanged, and `dsl._resolver` only branches on `c_source`.

- `data/over_the_nexus/working/rom_baseline.nds` does NOT exist on disk (checked 2026-11-03), though the plan and
  build.py both name it. The corpus was read from `rom_all_patches.nds` instead. Re-run against the real baseline
  once it exists (the deck preflight abort blocks rebuilding it).
- The 0x100 cap on unsized slots over-reads the last slot before a gap; the trace harness bounds a stub by
  execution, so it only matters for the byte-identical gate. Give those slots real sizes in ov5_cave.py if needed.

- c_equiv limits: stack args (5th+) are not compared; savestate-driven runs not yet exercised (only hash memory).

- The frame READ path of SPLICE is not exercised by a real hook yet (SL_ATKRESET only writes the frame); prove it on a
  leave-hook reader ([sp+0x90]) when Phase 3 starts.
- SL_ATKRESET's C copies the old stub's incidental r3 = &flag; whether r3 is dead at return site 0x021B44F0 is unproven.

- Matching is by fact address only; a fact AT the address may not claim a function entry (e.g. mem.ov3_anchor at
  0x021A25A0). cc.py gates on fact id + grade, so cite a fact that actually claims the routine.

- rom_all_patches.nds (09:10) and rom_all_patches_c.nds came from the same tree only as far as ROM inputs go; the
  diff above is the evidence they agree outside the converted slot.

- Koa'ki Meiru Wall (CAVE3_KMW_COND) PARKED for Phase 1: it calls 0x02022FC8 (-> BL 0x0202ABF8, a `bx pc` veneer to an
  ITCM ARM routine via `ldr pc`) with junk in r1-r3; arity can't be bounded statically, so a natural C port can't be
  proven equal. Needs the ITCM routine read (arm9 autoload image) or a savestate run.


- c_equiv frame-pointer args are compared by ONE pointee word (ponytail ceiling): widen if a callee takes a pointer to
  a bigger local struct.

- Next-batch helper: `python -m otn_enhanced.tools.c_next [N]` lists the next unconverted C-classified stubs (skips
  FORMS, the parked SKIP set, and deck-walker wrappers). Next up: CAVE_IK_T_COND.

## Next Experiment
- The pilot is done: `rom_mystic_piper_c.nds` was in-game confirmed by the user on 2026-11-03 ("I can confirm
  mystic piper's C implementation works"). The next step is Phase 0 of `notes/c-migration-plan.md`.
- Phase 1 (plain functions -> C): pick the first module from c_classify.json rows with form C and owner among the
  confirmed, all-plain modules (Koa'ki Meiru Wall, Raiden, Sekka's Light, That Grass Looks Greener). Per stub: write
  the .c, declare any new callee in engine.h + engine_syms.txt citing its c_entry/KB fact, add a FORMS row, run
  `c_forms --status` (gate must PASS), then one `build --c` per batch.

- Phase 1 batch 16 (2026-11-03): CAVE_IK_T_COND, CAVE_IK_RC_C2CND (tpl_opt_cond), CAVE_RAIDEN_EP: PASS -> 100/666 (status run; build --c NOT yet run for this batch). AWAITING IN-GAME TEST.
- CAVE3_SL_COND skipped: trace calls differ; criteria_count 0x02243FE0 gets r3 left as callee junk by the param provider 0x02234E78. Parked like Pineapple.

- Phase 1 batch 17 (2026-11-03): CAVE3_WNM_SUB_RIDER PASS (56/60) -> 101/666; build --c not yet run for batches 16-17. AWAITING IN-GAME TEST.
- CAVE3_WNM_COND: C is 100 B for a 64 B slot (2x5 row scan) -> .S fallback.

- Phase 1 batch 18 (2026-11-03): CAVE_DS_COND, CAVE_DS_COST, CAVE_MAIDEN_COND, CAVE_TSH_RES (new sym fn_021E6FD8): all PASS -> 105/666. AWAITING IN-GAME TEST.
- Batches 16-18 `build --c`: exit 0, 1067 s, sha256 f1fadbb7ecf9b86f04b32854697c1f4a90b997fe5631c8c2fa6234b7711dd4e9 (105 FORMS slots; per-slot diff vs rom_all_patches.nds not re-checked this run). AWAITING IN-GAME TEST (final retest).

- Phase 4 start (2026-11-03): tools/c_s_gen.py generates a byte-identical .S from a corpus slot (cards/c/s/<SLOT>.S, auto-registered in c_forms). 111 .S fallbacks (all classified .S stubs + the parked callee-junk ones) -> 216/666 gated, 0 FAIL. build --c: exit 0, 1379 s, sha256 f1fadbb7ecf9b86f04b32854697c1f4a90b997fe5631c8c2fa6234b7711dd4e9 -- IDENTICAL to the pre-.S build, as byte-identity predicts. AWAITING IN-GAME TEST (final retest).
- c_s_gen gotchas: unified-syntax flag `s` picked from the raw halfword; gas rewrites `adds rN,rN,#imm3` to the imm8 form (emit .hword); sub sp prints "#-0x10"; slots with base%4==2 cannot use gas pools (emit ldr as .hword).
- User decision 2026-11-03: stop the exercise here, little more to gain. Remaining: 450 stubs (259 C, 98 C+splice, 90 C+front, 3 REVIEW); Phase 2/3 shims unused.
