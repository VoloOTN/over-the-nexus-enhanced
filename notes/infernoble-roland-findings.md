# Infernoble Knight - Roland — findings

Family card 7. User 2026-10-20: "All confirmed. Build Roland". Clause split + donor Killer Needle 0x0FDB (L4 WIND Insect Normal 1200/1000) confirmed by user 2026-10-20 ("Confirmed, Killer Needle — proceed"). donor_scan CLEAN.

## Printed text (scratch/ygoprodeck_cache.json): Effect, Warrior, FIRE, L1, 500/500
- C1 (Quick Effect, from the hand) target 1 face-up monster you control; equip this card from your hand to it as
  an Equip Spell that gives it 500 ATK. (once per turn)
- C2 End Phase, if this card is in the GY because it was sent there this turn: add 1 FIRE Warrior except Roland,
  or 1 Equip Spell, from your Deck to your hand. (once per turn)
- C3 each effect once per turn (separate locks).

## Confirmed (this session, static)
- C1 equip-from-hand: Vylon's equip-THIS-card resolver 0x02210960 is zone-agnostic: phase 0x80 requires the card's
  CURRENT zone (0x021A220C(desc[+0xC]) >> 8) == desc[+3]; phase 0x7F moves it with 0x021C7484(side, SRC ZONE = that
  current zone, ref, side, [sp] S/T idx, 1, 0); a native caller (0x02212AC4) passes r1 = 0x0B (hand).
  Vylon f1 0x021F8048: GY check ONLY if desc[+3] == 0xE, then free S/T zone 0x021AE644 > 0. f2 0x022043F4: LP cost
  0x021E48D4 (no row = 0) then legal-+08 count 0x0224AA94 > 0.
- Cocoon of Evolution 0x0FEE (native "equip this card from your hand") is NOT reusable: cls0 + 10 hard-coded cid
  sites (0x021A2774, 0x021B70DC, 0x021C2204, 0x021D3950, 0x021D3B56, 0x021EC990, 0x021EDEF4, 0x0224B18C, 0x022560E6,
  0x02260616), ignition speed. RULED OUT.
- Hand Quick Effect = cls2 hand record + LIST A/B membership: Effect Veiler 0x22E5 and Honest 0x1D96 are LIST B;
  Veiler +0C 0x02202EEC = opponent's turn [0x0229DD14+0x34] && phase [+0x48] in {2,4} && 0x021BA8EC(ref) -> 1. All
  five callers of the membership test 0x0202354C (0x021EC982, 0x02239656, 0x0224B082, 0x0224C052, 0x0224C0C4) go
  through the ARM9 H4 site's LIST B bsearch -> Turpin's H4 front (grown to Turpin/Ricciardetto/Roland, new slot).
  Damage Step: KB battle.damage_step_offer_flag -- non-DS-legal cids are not offered in the Damage Step.
- +500 ATK: equip grant table 0x0226DFB0 (94 x {cid, atk, def}, sorted); phantom rows 0x0E6D (-500/-500), 0x15D1
  (+500/+500), both unclaimed -> 0x15D1 -> {0x0FDB, 500, 0}. ASSUMED: the grant is applied to a MONSTER card used as
  an Equip (table is cid-keyed) -> in-game item.
- C2 End-Phase "sent this turn": Fox Fire 0x1836 = End-Phase registry row 114 {0x02254221, cid} + cls2 GY record.
  0x02254220 = `r2 = 0xE ; bx 0x02254121`. Walker 0x02254120 walks the per-player turn-log list (head u16
  player+0x11A, 10-B records at 0x0229D33C {key, flags(low4 kind), ref, ?, next}) for key == cid, kind 1/2, flags
  bits 4..7 == 0, ref != 0, and the ref's CURRENT zone == 0xE; then posts 0x021D3168(word, ref, 0) with word =
  side<<31 | 0x0C400000 | (zone & 0x1F)<<16 | cid and removes the node (0x021C4974).
- 0x021D3168 descriptor decode: desc[+0] = word & 0xFFFF, [+2] = bit 31, [+3] = bits 16..20, [+4] = bits 25..30,
  [+5] = bits 21..23, [+6] = bit 24, [+0xC] = ref => the walker's event has desc[+4] = 6, desc[+5] = 2 (cls2).
  The sent-to-GY trigger has desc[+4] > 6 (Maugis _trig) -> one GY record separates the two.
- Savestates .ml3/.ml4: the turn log holds ONLY effect-specific nodes (OPT keys, Into the Void ...) -- the engine
  logs no generic "sent to the GY" node => Roland posts its own: TURNLOG_POST 0x021D2584(side, key, kind, param)
  -> 0x021C479C(side, 0xB, key, kind, [sp] = param) (param = the record's ref).
- Sent-to-GY accept chain: stock walk 0x0FDB ends at node 0x021D13C2 (`ldr r0,=0x0EC9 ; cmp r5,r0`); in the chain
  that node BLs Nikitama's ov3 front CAVE3_NK_GYNODE 0x0220A5C4 (0x0FE3 -> bx 0x021D1939 accept; else replay). Roland
  front chained ahead in the 28 B The Seal RELEASED at 0x02237E1C (zero in rom_all_patches / rom_infernoble).
- Add-to-hand resolver 0x02207EF5: 0x0FDB reaches dispatch 0x02207FCC like T.G. Striker 0x1F18 (in-game confirmed
  End-Phase Deck search through its default path).
- OPT keys 0x4FDB (C1) / 0x2FDB (C2): NOT 0x0FDB, which is the walker's node key (the walker needs ref != 0; our
  OPT posts use ref 0, but a query on key 0x0FDB would see the sent node).

## Ruled Out
- Cocoon of Evolution's hand-equip path (above).

## Build design (BUILD 9)
- ONE cls2 {RO_RES, RO_FILT, RO_COND, RO_COST, RO_SLOT5} over phantom 0x0E34; criteria {RO_C2H} over 0x0E48;
  leave-mask {0x0FDB, 0x0800} over 0x0E66; equip grant over 0x15D1; End-Phase row 133 (phantom 0x0E8B) rewritten;
  ov3 GY front 0x02237E1C at node 0x021D13C2; timing arm ARM_RO PREPENDED (zone GY -> "You can"); EQFILT Roland arm
  (any monster you control); ARM9 H4 -> CAVE_IK_RO_H4.

## IN-GAME RESULT BUILD 9 (user 2026-10-20)
User's words: "1. Confirmed 2. Confirmed 3. Confirmed 4. Confirmed 5. Roland does not 'activate' in the GY when it is
sent there... (see ml2 after send and ml3 in mainphase) 6. Confirmed 7. Confirmed"; reading (a) confirmed by user (the
End Phase came, no prompt). Follow-up: "In the save states it was sent by foolish burial/painful choice, but when i sent
it from field to GY no effect occured".
- PASSED (in-game confirmed by user 2026-10-20): RO1, RO2 (hand equip + 500 ATK), RO3 (Quick timing, no Damage Step,
  face-up only), RO4, RO6, RO7.
- FAILED: RO5 -- End-Phase search never offered (Deck route in the savestates; field route too).

## RO5 DIAGNOSIS (savestates rom_infernoble.ml2 / .ml3, ROM identity: RO_ stubs byte-equal in RAM)
- .ml2 (phase 2, after Foolish Burial / Painful Choice): turn log side 0 holds {0x0FDB, kind 1, ref 0x0C}; GY ref 0x0C
  = 0x0FDB => the sent-to-GY post WORKS (Deck route).
- .ml3 (phase 5 = End Phase, same turn): that record is consumed (key 0, ref 0) => the walker found it and posted.
- Executed over .ml3 (divide helper 0x020989A4 modelled): RO_COND(event 6) = 1 (OPT clear, 13 Deck candidates);
  miss-timing test 0x021EE0E0(event 6) = 0 (not missed; same as Fox Fire / Striker); post gate 0x021EDA08 = 1.
- ROOT CAUSE (KB dispatch.cls_slot_roles + disassembly 0x0224AE14..0x0224AE2E): +0C returning EXACTLY 1 makes the
  activation check 0x0224AD94 run the +08 sweep 0x0224A988, and RO_FILT returns 0 outside the hand -> not activatable.
  0x0224AD94 over .ml3: BUILD 9 stub -> 0 (reproduces the in-game failure); event-6 branch returning 2 -> 1.
- Ruled out this session (each by execution): turn-log post missing; walker not reaching the node; C2 condition
  false; miss-timing at the End Phase; post gate 0x021EDA08.
- FIX (BUILD 10): RO_COND event-6 branch returns 2 (Striker's 0x0224A114 value). Field route (RO5a) shares the
  activation path; if it still fails after BUILD 10, take a savestate right after the field send.

## IN-GAME RESULT BUILD 10 -- WHOLE CARD in-game confirmed by user 2026-10-21
User's words: "Roland now works as expected when foolished and sent to the GY by other means -and performs the
search" -> RO5 passes (with RO1-4, RO6, RO7 from BUILD 9). NOT shipped.

## BUILD 10 (2026-10-20)
- rom_infernoble.nds sha256 8da51312e1a03698d3d1f42035820c94f3f92ece39990e6a69c175678606fd9f.
- patch_infernoble.verify PASS; Dragon Rulers + Nikitama PASS; remaining regression lines = BUILD 8's known
  local-arm / unregistered-walk category only (Eva / Shadow Mist chain walk, timing stub, row-hook front).

## BUILD 9 (2026-10-20)
- rom_infernoble.nds sha256 f2b25ddad452a209838463f8b3753c926701314602673083fcf75fb479dac4c1 (all seven Knights).
- patch_infernoble.verify PASS. Regression = BUILD 8's list; two new lines fixed by VERIFY-ONLY tolerance (no shipped
  bytes): patch_dragon_rulers accepts the H4 site -> CAVE_IK_RO_H4; patch_nikitama accepts its GY node -> 0x02237E1C
  (both PASS afterwards, nikitama with patch_infernoble's switch stub registered, as in the build).
- scratch/infernoble/chain_walk_diff.py PASS: whole sent-to-GY chain vs rom_all_patches -> only 0x0FDB and 0x139A
  change leaf, both to the accept leaf.
- OFFLINE EXECUTION scratch/infernoble/roland_ss.py over .ml3 (BUILD 9 stubs + tables in memory; side-0 GY card #9
  relabelled 0x0FDB in BOTH the GY array player+0x55C and the instance table 0x0229C33C + ref*8, ref 0x3E):
  RO_COND(event 7) -> 0 and queues attach (0x35, 0x10B = kind 1 | slot 0xB, key 0x0FDB, param 0x3E = the ref);
  with that node in the list, walker 0x02254121 posts word 0x0C4E0FDB ref 0x3E = event 6, zone 0xE, cls2, 0x0FDB.
  (The attach is QUEUED via 0x021C3BC8, so it is applied later in-game -- same path as every OPT stamp.)
  NOT executed: RO_COND(event 6) -- thumbemu stops at an ARM BLX (0x02029BA2 -> 0x020989A4) inside the row count;
  that branch is Renaud's in-game-confirmed r_cond shape (OPT + 0x02234E79 / 0x02243FE1).

## Open Questions
- Does the +500 grant apply? Does the C2 node post land with the right ref (walker accepts)? -> in-game / savestate.

## Next Experiment
- BUILD 9 in-game test.
