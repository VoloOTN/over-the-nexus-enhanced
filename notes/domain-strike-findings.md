# Domain of the True Monarchs + Strike of the Monarchs — findings (live)

Card text: see PROMPT_monarch_erupt_domain_strike.md (quoted from scratch/ygoprodeck_cache.json).
Status 2026-11-11: research only, NOTHING BUILT.  Donors proposed, NOT approved.

## Confirmed (2026-11-11, this session)
- Donor scan (scratch/_spell_donors.py "Spell Card" Quick-Play / Field: clean, undecked, unclaimed):
  Quick-Play = only Speed Spells 0x0DE4 Offerings to the Doomed, 0x0DF0 Reload, 0x0DFF Tornado.
  Field = Wasteland 0x10F1, Sogen 0x10F3, Umiiruka 0x1345, Mystic Plasma Zone 0x1349, Acidic Downpour 0x1D21.
- Halfword scan of the stock ROM (scratchpad cidhits.py): 0x0DE4 = 3 arm9 / 1 ov3 / 0 ov5 halfwords, ZERO u32 literals (cleanest Quick-Play);
  0x10F3 Sogen = 4 arm9 / 0 ov3 / 0 ov5, zero literals.
- Field Spells' stat boosts are NOT found by cid scans: they are arms of the stack-based switch in the field-spell stat engine
  0x021B26F4..0x021B2B6E (KB field.stat_engine / field.arm_map).  Sogen -> arm 0x021B287C via the halfword jump table @0x021B2764 (entry 3).
  So a Field donor brings its boost; Sogen's is neutralised by repointing its jump-table entry (Seal of Orichalcos rewrote Yami's entry-5 arm the same way).
- Masterplan is already on a Speed Spell donor (Faustian Bargain 0x0D6A), AWAITING IN-GAME TEST: whether a Speed Spell donor can be put in a
  non-Turbo deck / activated in a normal duel is UNPROVEN.
- D2 precedent: Skyscraper 0x18FF's battle bonus is a cid check in the damage-calculation code: 0x02197782 `ldr r0,=0x18FF ; bl 0x021AC494`
  (with 0x021AF7A4(side, [r7+8]) as r2) sets r5 = 1; Skyscraper 2 0x1A66 the same @0x021977AC; 0x2319 @0x021977DC via 0x021AC0C8.
  Where r5 is consumed (the +1000) is NOT yet read.
- D3 precedent: Cost Down 0x15C7 (cls0 0x02280CD4 {0x15C7, res 0x02208C51, 0, cond 0x021F0221, cost 0x021E4EA5, 0}) — its key is read by the
  level getter around 0x021B8458 / 0x021B8460 / 0x021B8506 (pool 0x021B86AC; a stack-based switch on node keys at 0x021B85F0) and at
  0x021B2162, 0x021C1EE6.., 0x021C31FC..  Cost Down lowers ALL hand monsters; Domain lowers ONE chosen card -> needs a per-card mark.  UNREAD.

## Strike S1-S3 BUILT 2026-11-11 (user: "Approve, Strike first"; donor 0x0DE4 approved) — AWAITING IN-GAME TEST
- Chain rebuilt for RESERVE 0x19C00: rom_chain_19C00.nds 129/129 steps, sha256 d014efb32744b6c78c0f0d65fc2e5422f465afa35f0c8429dbbfaa2a88743002
  (ov5 len 0xEE420 == OV5_NEW_LEN).  All CHAIN constants (edea, eidos_monarch, eidos_squire, erupt, revolt, tessera, _monarch_session, _phantoms_all,
  _lists_free, _build_erupt) now point at it.  Ceiling 0x023B3D20.
- Precedent found: Gemini Spark 0x212A cls0 @0x02284E5C = {0x022297FD, +08 0x021DE309, COND 0x021F069D, COST 0x021E7C89, SEL 0x02234DA5} — the shared
  "Tribute 1 X, then target" shape (Miyabi 0x192A, Icarus Attack 0x1A35, Gem-Enhancement 0x22D9 share COST 0x021E7C89).
  * 0x021E7C88 (cost): `0x0224AB38(desc, 0x0224A8C1)` candidate check, then `0x0224BB98(side, cid, 0, 0x0224A8C1)` picker; no 0x212A literal in its pool.
  * 0x0224A8C0(desc, side, zone) = find_event_handler(desc) -> record +08 filter (skipped when zone flag bit 21 set).
  * 0x021DE308 (the shared +08): cid switch picks r4 = per-card TARGET filter; desc[+7] != 0 -> r4(desc, side, zone); desc[+7] == 0 -> 0x021D9188
    (Tribute test) && 0x0224AB44(desc, r4, zone<<8|side) >= [sp] (targets left after the Tribute).  Disassembled 0x021DE308..0x021DE4C6.
  * Zone-predicate masks from the rosetta (dispatch.zone_predicate_mask_rosetta) paired with printed text: Saber Slash 0x209C 0x21874 = "face-up cards on
    the field"; Wild Tornado 0x229B 0x21454 = "face-up card in the Spell & Trap Zone".
- Pre-build checklist: (1) per-cid gates on 0x0DE4: PROVEN none — the only ov3 halfword hit 0x02143B68 is inside ARM code (neighbours 0xE1A0/0xE59F),
  no u32 literal anywhere; (2) zones: cost = own monster zones 0..4 (mask 0x0C15 + zone <= 4), target = any face-up card (0x21874); (3) text via card_text
  re-emit; (4) no once-per-turn.
- Build: cards/strike.py + cards/c/strike.c; CAVE_ST_FILT/TGT/RES/PREB 0x023B2A10..0x023B2B40; cls0 phantom 0x0E6F; card_text 0x0DE4; tenacity.MONARCH
  + 0x0DE4 (11 entries); rom_strike.nds sha256 a314d8d1c609ade86422827c264c0ca5b82af84ee21fbc265359bdecf8fa0f51 (15/15).
- CPU row: donor had none.  ov5 CPU row table 0x02391820..0x02396C94 (2498 rows) is UNSORTED (checked: neither id nor cid order) -> phantom 0x0E1E's row
  @0x02395414 {0x3CE1E, always-true 0x023107C1} re-keyed to 0x3CDE4 (unclaimed: no repo reference).
- Combined: 'strike' after 'erupt' in ORDER -> rom_monarch_all.nds sha256 3c732fe30f95bfcbe565f9e9cbc793c60e24727637ac88e0c7987a50b0a0e41e; strike 15/15
  + CPU row, erupt 19/19.  Full sweep (scratch/_monarch_verify.py): the same pre-existing chain-head FAILs as before (mega_monarch 3, restoration 2,
  edea 1, eidos_squire 1) plus monarchs_awaken "negate-reader list search -> PREB (got 0x023B2B20)" = Strike's precheck now sits ahead of Awaken's
  and tails into it (expected, same category as Restoration's line).
- Trace tool: scratch/strike_gdb.py -> build/cpu_battery/gdb_st/st_N.json (COST 0x021E7C88 for 0x0DE4, FILT, RES, PREB key hits, TRIBPAY 0x021CF68C, RESNEG).
- BUG FOUND BY TRACE (st_1..3.json on 3c732fe3…, superseded): 3 duels, Strike's FILT called 0 times, COST never for 0x0DE4 (Tribute Summons did happen).
  Cause, disassembled: Gemini Spark's COND 0x021F069C = `n = 0x02206304(desc)`; n == 0 -> 0; else 0x021BAE30(desc[2]^desc[6], n).  0x02206304
  binary-searches the draw-count table 0x022704A4 (0xBD rows, stride 4, `bl 0x02022E44`) — 0x0DE4 is not in it -> COND always 0 -> never offered.
  FIX: own COND CAVE_ST_COND 0x023B2B40 (0x20 B) = 0x021BAE30(desc[2]^desc[6], 1).  rom_strike.nds now sha256
  1a008565c477538aa8d1bac12d14f590ee505358e8a70a94d4ce3b9d58698b8a.  LESSON: a borrowed native COND can be cid-keyed through a DATA table.
- Re-trace after the COND fix (rom_monarch_all 87b1fef2…): event counts IDENTICAL to before (PREB 12650/30855/13052), COND 0x023B2B40 never hit.
  Hand/GY dump (seed 2): Strike never in a hand at any snapshot; one copy MILLED into side 1's GY by t=129 s.  The Lightsworn filler mills the Deck ->
  not evidence of a Speed Spell gate.  (Masterplan's "drawn 14 / activated 0" on a Speed Spell donor is still unexplained and is the other candidate.)
  Trace filler switched to Normal Monsters (Vorse Raider, Gene-Warped Warwolf, ...).
- Normal-filler re-trace: duels are short (~10 draws per side) and Strike was never drawn in any of the 6 hands (deck still held all 3) -> no
  activation evidence either way.  scratch/strike_gdb.py now FORCES the case: at the first Tribute payment it rewrites one filler card in the Tributing
  player's hand to 0x0DE4 (hand word cid bits + acting-instance entry 0x0229C33C + ref*8, ref = idx<<1 | side).  That run crashed (my variable `w`
  shadowed the worker) and left build/cpu_battery/gdb_st/melonDS.exe running (PID 16512); stopping it was denied -> trace NOT yet run.
- Forced-hand trace RUN (st_1..3.json, user closed the stale emulator): the rewrite happened at the first Tribute payment in all 3 seeds (e.g. seed 1
  player 0 hand[1] 0x09001682 -> cid 0x0DE4, instance 0x0229C45C 0x1682 -> 0x0DE4), but the card later appears in the GY as its ORIGINAL cid
  (0x1682 / 0x11BA / 0x16F0), and COND / FILT / COST never fired.  => card identity is held somewhere else as well (a card-instance master copy):
  the rewrite is NOT a valid way to give the CPU a card.  RULED OUT as an experiment design.  Two attempts have now failed to get a CPU activation
  attempt of Strike; per the two-strike rule, stop instrumenting the CPU and ask for the in-game test (it also answers the Speed Spell question).
### S4 BUILT 2026-11-11 (user: "Build S4 first") — AWAITING IN-GAME TEST, no trace
- PROVEN (KB + read this session): GY-action descriptor builder 0x0224C590 writes desc[+5] = 2 (@0x0224C5E6), desc[+3] = 0x0E (@0x0224C5EA), desc[+4] =
  byte [0x0229A37C + r5 + 0x838] (state, NOT a constant) -> prefind_hook gained `any_sub` (skip the desc[+4] == 0 test; default False keeps Tessera's bytes).
- PROVEN: Genex's poster 0x02207908(desc, kind, param, x): per target, revalidate 0x0224A924, for kind < 6 and x == 0 skip if 0x021AFCBC(desc, side, zone)
  (unaffected), then 0x021C479C rider_attach(side, zone, desc cid, kind, param).  rider_attach = 0x021C3BC8(0x35 | side<<15, kind<<8 | zone, key, value).
- PROVEN: DNA Transplant 0x171F cls0 0x02281604 = {0, 0, 0, 0, SEL 0x022378E5}; its selector phase [0x0229AB7C]: 0 -> 0x02259A9C(side, cid, 1, 0xFF);
  1 -> value [0x0229DE94+8] -> 0x022345F4(desc, value) (append: count u16 +0x12, values u16 +0x14 + 2i) + 0x021C3BC8(8 | side<<15, 4, value, 0); else 1.
- Build: CAVE_ST_COND2 / SEL2 / RES2 / VREC 0x023B2B60..0x023B2C90; VREC {0x0DE4, 0, RES2, 0, COND2 (code 2), 0x021E5709, SEL2}; gy_vrow_hook.MONARCH_ARMS
  + 0x0DE4 (21 of 24 GYV2 rows); rom_strike.nds sha256 c4680bc735bcb7e6f4de0074e727a092ae23986a97fb3928c61dfe10cbd241ca (28/28).
- ASSUMED: [0x0229AB7C] is reset to 0 before a +14 selector runs (DNA's selector relies on it); the declared value's encoding is what cur_attribute's
  0x2167 arm expects (Eidos Monarch E2 is the same untested assumption); the GY enumerator restricts a GY ignition to your Main Phase (Frost Blast /
  Pantheism have no own timing test either).
- Combined: rom_monarch_all.nds sha256 dac01d366f4a92324b70e3dbc8b3bbd693c98b32570ad48e001acff6b538b283.  Sweep: strike PASS (incl. prefind stub byte-exact
  with entries [Tessera 0x1123, Strike 0x0DE4] and the 0x0DE4 GY row); pantheism / frost_blast / revolt PASS on the 21-row table; tessera_hand FAIL only
  "prefind stub byte-exact (entries ['0x1123'])" (predicted below); the other FAILs are the pre-existing chain-head lines.
- Expected sweep line: tessera_hand's prefind stub check FAILs in a separate-process sweep (its ENTRIES lack Strike's, the ROM's stub has both); the
  session build itself carries both entries.
- ASSUMED: flag bit 4 clear == "Normal Summoned/Set" (Flip Summons unmeasured); 0x021E7C89's default arms Tribute the picked monster for a cid not in its
  switch (Gemini Spark takes the default path).
- S4 plan (not built): no cls2 phantom left (_phantoms_all: cls2 0) -> virtual cls2 record via effects/prefind_hook.register(0x0DE4, vrec, cls=2, zone=GY
  code) + gy_vrow_hook MONARCH_ARMS row; cost self-banish 0x021E5709; selector = DNA Transplant 0x171F's declare step re-written without its on-field
  check: phase [0x0229AB7C] 0 -> 0x02259A9C(side, cid, 1, 0xFF), 1 -> 0x022345F4(desc, [0x0229DE94+8]) (appends to desc +0x12 count / +0x14 values);
  RES = rider_attach(s, z, 0x2167 Genex Ally Changer key, kind 2, attr) on every face-up monster (cur_attribute 0x021B8E48 honours key 0x2167; Eidos
  Monarch E2 is the untested precedent).

## Domain research 2026-11-11 (user: "Start Domain"; donor Sogen 0x10F3 approved with Strike's)
- D2 precedent read: Skyscraper 0x18FF's "+1000 during damage calculation" lives in 0x02196A28 (push {r4-r7,lr}; sub sp,#0x144).  0x02197782:
  r5 = 1 if 0x021AC494(0x18FF, r6, 0x021AF7A4(r6, [0x02298AD8+8])) (Skyscraper active for the attacker side r6?).  0x02197A14: `ldr r7,=0x02298AD8 ;
  cmp r5,#0 ; beq 0x02197A5A`; if [sp+0x10C+r4] < [sp+0x10C+[sp+0x30]]: r1 = 0x3E8, scaled by [sp+0xF4] (<< for negative, (x+1)>>1 per positive step),
  added to [sp+0x10C+r4].  => the native "+N ATK during damage calculation" slot.
- Callers of 0x02196A28: ov3 0x0226BAEA only (inside 0x0226B9FC, itself called from 0x0226A3D2; it first fills the battle struct 0x02298AD8: +0 side,
  +1 other side, +8 zone, +0xA zone) + ov5 0x022E1DD0 / 0x022EED58 / 0x0234A666 (CPU).  Literal 0x02196A29 @0x02197D10.
- Other Skyscraper sites are NOT the boost: 0x0220DD2E = the Field Spell activation resolver's cid -> field id switch (0x021A7BC4); 0x02245596 = Field
  Spell activation legality (0x021AC9DC).
- PLAN (unproven): 4-byte front @0x02197A14 -> stub: push {r0-r3,lr}; C(host sp, r4, r6) adds 800 (same scaling) when the attacker is a Tribute
  Summoned monster of a face-up Domain's controller attacking a monster; pop {r0-r3}; ldr r7,=0x02298AD8; cmp r5,#0; pop {pc} (flags survive).
  NEEDS a GDB trace first: r4 / r6 / [sp+0x30] roles and that real battles (call window 0x0226BAEA..0x0226BAEE) reach 0x02197A14.

- RULED OUT (D2 strike 1, trace build/cpu_battery/gdb_d2/d2_1/2.json, rom_monarch_all dac01d36…): 0x02197A14 hit ~720x per duel, the real-battle
  call window 0x0226BAEA..0x0226BAEE NEVER entered; between hits the CPU swaps hypothetical monsters into zone 2 (0x160C, 0x16F1, 0x16F0, ...).
  => 0x02196A28 is the CPU's battle PREDICTOR in practice; a bonus there changes AI estimates, not damage.  Logged regs there: r4 = 0 / 36 and
  [sp+0x30] = 36 / 0 (byte offsets of the two sides' ATK entries in [sp+0x10C]), r6 = side (0 / 1), [sp+0xF4] = 0.  Where the REAL damage
  calculation reads ATK (and where Skyscraper's real +1000 lives) is UNKNOWN: Skyscraper's 4 aligned literals are the predictor, the field
  activation resolver, and field legality — so its real boost is either ungreppable (a stack-based switch) or the card is unimplemented.

- CORRECTION to the line above (same day): the "CPU predictor only" reading was a MIS-MEASUREMENT, not a falsified mechanism.  0x02196A28(r0, mode)
  writes the battle results [0x02298B30] itself (@0x02197D26); the real battle reaches it through the THUNK 0x02197D08 = `ldr r3,=0x02196A29 ; movs
  r1,#0 ; bx r3` (mode 0), whose BL callers are 0x021BB6EC, 0x021BC032, 0x021BC25A, 0x021C16B0, 0x0222A720, 0x0224F550, 0x0224F8B0, 0x0224FB9A,
  0x022500D2, 0x022501BA (battle step machine).  The predictor path 0x0226BAEA passes mode 1.  The damage handler 0x021D00A0 (only caller 0x0225136C)
  applies [0x02298B30 + 8*i].  My d2 trace labelled hits "real" only inside 0x0226BAEA..EE, so every real (mode 0) hit was mislabelled "cpu".
  Re-trace with ENTRY 0x02196A28 r1 = mode: build/cpu_battery/gdb_d2/d2_1/2.json — PROVEN: every real attack reaches 0x02197A14 in MODE 0, 7 times
  (one per thunk caller, LR 0x0224F555 / 0x0224F8B5 / 0x0224FB9F / 0x022500D7 / 0x021BC037 / 0x022501BF / 0x021BB6F1), 21 / 28 mode-0 hits vs ~690
  mode-1 (predictor) hits per duel.  In the real hits r6 = attacker side (= battle struct +0), r4 = attacker entry offset (0 side 0 / 36 side 1),
  [sp+0x30] = defender offset, [sp+0x10C + r4] = attacker ATK (2400 for Tribute Summoned Zaborg 0x1D5C / Caius 0x1BCD with flags 0x0801C042 / bit 3),
  [sp+0x10C + r4 + 4] = its DEF (1000), [sp+0xF4] = 0.  => D2 = a front at 0x02197A14, Skyscraper's own real bonus site.
  Site check: stock halfwords 0x4F48 (`ldr r7,[pc,#0x120]` = 0x02298AD8) 0x2D00 (`cmp r5,#0`); no b/bcond inside 0x02196A28..0x02197D08 targets
  0x02197A14 or 0x02197A16.  D2 stub: push {r0-r3,lr}; C(host sp = sp+20, r4, r6): if battle struct +2 == 0 (not direct), side r6 has a face-up
  Domain in zone 10, and the attacker (r6, zone [0x02298AD8+8]) has flag bit 3 -> host[0x10C + r4] += 800 scaled like Skyscraper by host[0xF4];
  pop {r0-r3}; ldr r7,=0x02298AD8; cmp r5,#0; pop {pc}.  Applies in mode 1 too, so the CPU predictor sees it (consistent).
- Battle struct 0x02298AD8 from the CPU hits: +0 attacker side, +1 other side, +2 direct-attack flag, +8 attacker zone (s16), +0xA defender zone.
  At 0x02197A14: r6 = attacker side, r4 = attacker entry offset into [sp+0x10C] (0 / 36), [sp+0x30] = defender entry offset.

### Domain BUILD 2026-11-11 (user: "Yes, build Domain") — AWAITING IN-GAME TEST
- cards/domain.py + cards/c/domain.c; cls3 over phantom 0x14DC; slots CAVE_DM_FRONT/BONUS/COND3/COST3/RES3/PRED 0x023B2DD0..0x023B30F0; CAVE_MA_LOCK RELOCATED
  0x023B0020 (0x90) -> 0x023B2C90 (0x140) because edlock.c + D1 = 0x120 B (old range is a hole; March's RESERVES LOCK 0x140).  Sogen has NO cls0 record
  (scan of cls0 0x0227E64C x0x51A, 2026-11-11): Field Spell activation is generic.  Sogen arm patch 0x021B2884 0xD050 -> 0xE050 (stock read).
  D2 site stock bytes 484f002d (read).  card_text 0x10F3; tenacity.MONARCH + 0x10F3; ORDER + 'domain'; _build_domain.py = Session(chain, march, domain).
- rom_domain.nds (chain + march + domain) sha256 1103f4f8f120850f84b5f5f06803c293af68024cb41d8e3d92b4845646083084: domain 20/20, march 28/28.
  Combined rom_monarch_all.nds sha256 8a2c7b73aa5e1551eba3f087d0b6e3f9b0db60b9d682e6844d6da7354116e690: domain PASS, march / stormforth / return / revolt PASS
  with the relocated lock; the other FAIL lines are the known chain-head ones.  D2 front disassembled from the built ROM: push {r0-r3,lr}; add r0,sp,#0x14;
  r1 = r4; r2 = r6; blx =0x023B2DF1; pop {r0-r3}; ldr r7,=0x02298AD8; cmp r5,#0; pop {pc}.
- D2 TRACED (CPU, NOT in-game) build/cpu_battery/gdb_d2/d2_1/2.json on 8a2c7b73…, deck 3 x Domain (the CPU played it in both duels): seed 1 t=56.6 — Domain
  face-up in side 0's zone 10, side 0's Tribute Summoned Monarch (2400) attacks a monster (battle struct +2 = 0), mode 0: [host sp+0x10C+r4] AFTER the front
  = 3200 (the copy at +8 still 2400).  Seed 2 t=42.9 — Domain on side 1 (the defender's side), attacker side 0: 2400 unchanged (negative control).  No Domain:
  values unchanged; every real battle passed the front (DM_FRONT = A14 count) and both duels finished, no stall.
- ASSUMED: Star Blast's phase protocol (0x80 -> 0x7F, PICK_DONE == 0 -> 0x80) behaves the same under a cls3 descriptor; can_take_ignition 0x021F06E8 accepts
  a Field-zone (desc[+3] = 10) ignition; the CPU will not use D3 (no AI work done).

### D3 PROVEN pieces (disassembly 2026-11-11)
- Hand Level reader 0x021B20AC(side, ref): printed Level (0x0202ABD8 of [0x0229C33C + ref*8] & 0x3FFF), then walks the INSTANCE rider chain
  head u16 [0x0229C340 + ref*8] (node pool 0x0229D33C, stride 10, kind < 6): key 0x18D9 (Level Conversion Lab) = SET node[+4]; key 0x1F6A
  (Star Blast) = Level -= (s16)node[+4], min 1; then A Legendary Ocean 0x150B -1; then Cost Down 0x15C7 turn-log count * 2.
- The FIELD Level getter 0x021B807C walks the SAME instance chain: @0x021B81CC..0x021B81E4 it rebuilds ref = (word bit 14) + 2*((word >> 23) & 0xFF)
  from the zone's card word and loads [0x0229C340 + ref*8] — so an instance rider attached in the hand is read after the Summon ("even after they are
  Summoned/Set").
- Star Blast 0x1F6A cls0 0x0228458C = {0x0222B3E5, 0x021DBB75, 0x021FFBE5, 0x021EBFF9, 0}; resolver: 0x80 -> picker 0x0224B9F0(side, cid, 0, pred
  0x0222B399) + msg 0x0219A818(side, 0x6F) -> 0x7F; 0x7F: 0x0224BBB0() == 0 -> 0x80; zone [0x0229DD94+0x7C], side [+0x78], index [0x0229DE14];
  hand (zone 0xB): ref from hand word (player+0x124+4*idx), reveal 0x021D2598(side, ref), 0x021C4814(ref, 0x1F6A, 3, desc[+0x18]); field:
  0x021AFCBC unaffected check, rider_attach(side, zone, 0x1F6A, 3, value).  Picker predicate pred(side, zone, index) -> 0x800 = selectable
  (current desc at [0x0229A9FC+0x50]).
- 0x021C4814(ref, key, kind, value) = engine command 0x35 with (ref>>1, kind) / 0x8000|key — the INSTANCE-chain attach.
- Field Spell ignitions live in the cls3 table: Dragon Ravine 0x2359 rows 0x0227E094 / 0x0227E0AC, Valhalla 0x0227C21C, Fusion Gate 0x0227A50C.

### Domain activation / D1
- Sogen's stat arm 0x021B287C: Warrior|Beast-Warrior test, `beq 0x021B2928` / `b 0x021B2860` (+200/+200 tail) -> neutralise by turning the beq
  @0x021B2884 into `b 0x021B2928` (exit still to be confirmed as the no-change path).  Sogen's own cls0 activation record (field id) kept.
- D1 = edlock.c gains: side's opponent controls a face-up Domain (zone 10), has an empty Extra Deck and a face-up Tribute Summoned monster, and side has
  none -> locked.  Needs March's lock stack (combined ROM has it).

## Ruled Out (do not retry)
- Gemini Spark's COND 0x021F069D for a cid that is not in the draw-count table 0x022704A4: always 0 (never offered).  Strike has its own COND.
- Rewriting a hand card's cid (hand word + acting-instance entry 0x0229C33C) via GDB to hand the CPU a card: the card's identity is held elsewhere too; it
  reappeared in the GY under its original cid and no Strike code ran.  Not a valid experiment.
- Lightsworn filler for a trace that needs a specific card drawn: it mills the card away (st_2, Strike in the GY by t=129 s).
- D2 at the predictor-only window 0x0226BAEA..0x0226BAEE: that call is mode 1 (CPU predictor).  Label real battles by the calculator's MODE (r1 at
  0x02196A28 entry), never by that window.
- A D3 Level change through the zone rider chain alone: hand cards have no zone; the instance chain [0x0229C340 + ref*8] is what both readers walk.

## Open Questions
- Speed Spell donors outside Turbo Duels: can Strike (and Masterplan) be put in a normal deck and activated?  Only the in-game test answers it.
- Strike S1 "Normal Summoned/Set" = zone flag bit 4 clear (HYPOTHESIS for Flip-Summoned monsters: unmeasured).
- Strike S2 on a Spell/Trap target: resolution-time negation goes through 0x021EE3DC; continuous Spell/Trap effects may not consult it (HYPOTHESIS).
- Strike S4: [0x0229AB7C] reset before the +14 selector; declared-value encoding vs cur_attribute's 0x2167 arm; GY ignition restricted to your Main Phase
  (all HYPOTHESIS, the same assumptions Eidos Monarch E2 / Frost Blast rest on).
- Domain D3: Star Blast's phase protocol under a cls3 descriptor and can_take_ignition 0x021F06E8 for a Field-zone ignition (HYPOTHESIS); the CPU has no
  AI for D3.  Domain D1: not traced.

## Next Experiment
- THE USER'S IN-GAME TEST of rom_monarch_all.nds sha256 8a2c7b73aa5e1551eba3f087d0b6e3f9b0db60b9d682e6844d6da7354116e690 (Erupt, Strike, Domain).
- If Strike is never offered at all: look for a Speed-Spell activation gate (card_prop type / genre 28) before anything else; Masterplan shares the symptom.
