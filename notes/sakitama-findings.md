# Sakitama — findings (started 2026-10-12)

Printed text (scratch/ygoprodeck_cache.json, passcode 67972302, Spirit L4 LIGHT Fairy 400/900):
"Cannot be Special Summoned. Once per turn, during the End Phase, if this card was Normal Summoned or
flipped face-up this turn: Return this card to the hand. You can only use each of the following effects of
"Sakitama" once per turn. You can reveal this card in your hand; immediately after this effect resolves,
Normal Summon 1 Spirit monster from your hand. If this card is Tributed: Target 1 Spirit monster in your GY;
add it to your hand."

C1 cannot be SS / C2 EP return (incl. any flip) / C3 HOPT reveal-in-hand -> NS 1 Spirit from hand /
C4 HOPT if Tributed -> target Spirit in GY -> hand.
Scope: WHOLE CARD (user 2026-10-12). Donor: **Grand Tiki Elder 0x13E5** (user pick 2026-10-12).
C3 ruling (user 2026-10-12): the effect's Normal Summon is ADDITIONAL (does not spend the regular NS).
Not in the 3DS build (CARD_Name_E.bin search for "Sakitama" = -1). Template = patch_aratama.
Status: RE in progress. Nothing built. Nothing in-game tested.

## Confirmed (this session)
- Donor 0x13E5: `donor_scan 0x13E5` -> "VERDICT: CLEAN - no data structure names this cid"; name slots e=16,
  desc e=55 (long text goes through card_text re-emit). No `0x13E5` literal in ygo_tools/tools/*.py except its
  patch_bulk_card_pack row (line 1769).
- RETURN-ONLY Spirit cls1 is a NATIVE shape: stock cls1 scan for {0x0220A901,0,0,0x021E88A9,0} -> Asura Priest
  0x1505 (LIGHT Fairy Lv4 Spirit) and Inaba White Rabbit 0x14FE own exactly 1 cls1 row (the return). KB
  dispatch.second_cls1_record_is_spirit_only (VERIFIED): leftmost+1 holding another cid falls back to leftmost.
  => C2 needs ONE cls1 row, not a pair.
- Phantom 0x1500 (no card_prop row) owns exactly 1 cls1 row, the return record -> natural count-neutral
  drop for C2's row. NOT yet checked against PHANTOM_CLAIMS / chained ROM.
- ARM9 flipped-face-up list 0x0209BB5C (stock == rom_all_patches): Asura Priest 0x1505 and Inaba 0x14FE are NOT
  members. So native return-only Spirits get the EP return without the list -> the list drives flip TRIGGERS
  (Aratama's search), and Sakitama has none. Free list phantom: 0x1535 (0x1534 is in the list but claimed in
  quickeffect_list by miscellaneousaurus -- different pool, re-check). (rom_all_patches.nds is stale: still has
  0x1527, i.e. predates Aratama build 2.)
- LIST B 0x0209BC8C (40 shown, count 0x24=36) contains phantoms 0x1774 and 0x1A86; their existing claims are in
  OTHER pools (quickeffect_list = speed-2 list 0x0209C118; cls2_table). No "handfx_quick_list" claim on either.
- Leave trigger consumer 0x021CA980 switches on [sp+0x18] (1/2/3) and posts via 0x021D3168; Shinai's record is in
  cls2 -> **C4 (tribute trigger) dispatches through cls2**, and so does the hand menu (C3). find_event_handler
  returns the LEFTMOST record for cls2 (KB) => **one cls2 record must serve both C3 and C4** (composition blocker
  for the two-record design).

## Inherited from Explore agents this session — UNVERIFIED until re-proven by me
- Donor 0x13E5: donor_scan CLEAN, 0 advisories, no aligned ov5 hits.
- C3 resolver 0x0220D80C (Ultimate Offering 0x12F3 cls3, Gemini Summoner 0x1CA4 cls1, Cry Havoc 0x1D35,
  Brain Research Lab 0x209B): phases 0x80 legality (0x021B9E6C/0x021B9DAC) + count -> 0x7F picker setup
  0x0224B9C8 -> 0x7E posts turn-log kind 1 on the cid, calls 0x02261444 (summon launch) for hand.
  Filter by cid in 0x0220D7B4; unknown cid -> 0 (any monster). is_spirit = 0x020230D4.
  NS-spent chain 0x021B9EFC / counter 0x021B9514 list special cids.
- Hand activation needs LIST A 0x0209BC4E (full) or LIST B 0x0209BC8C (0x1774 / 0x1A86 maybe free).
- Self-reveal prim 0x021D2598(side, ref). HOPT = turn-log 0x021D2584 post / 0x021A14E8 query, guard desc[+7].
- C4: Tribute bit [sp+0xC]&0x1000 at leave dispatcher (KB leave.tributed_reason_bit). Shinai 0x2462 arm
  0x021C9324. Assault's ov5 stub CAVE_ASSAULT_LEAVEHOOK at 0x021C93D0 already tests the bit.
  Shinai cls2 {0x2462, 0x02208181, 0, 0x0224A115, 0, 0x02235605}, criteria {0x2462,0x1E,0x0223CBC9,0x00010022}.
  Spirit GY->hand handler 0x022409C9 (Izanami 0x1DFD row {7, 0x00010002}).
- Flip parity: ARM9 list 0x0209BB5C (phantom 0x1527 spent by Aratama; 0x1534/0x1535 candidates) + genre bit 22.

### C3 (disassembly of stock ov3 this session, scratch/dis.py)
- Filter selector 0x0220D7B4: 0x1A67 -> 0x0220D63D, 0x1CA4 -> 0x0220D69D, 0x1D35 -> 0x0220D70D,
  0x209B -> 0x0220D749, ANY OTHER cid -> 0 (no filter = every hand monster, mask 0x50). Hookable default exit
  `movs r0,#0 ; bx lr` @0x0220D7EC.
- Filter ABI (r0 side, r1 zone, r2 index) -> mask; hand = zone 0xB, card cid = [0x0229AC94 + (side&1)*0xB3C +
  idx*4 + 0x124] & 0x3FFF; field zones 0..4 = [... + (zone+idx)*0x14 + 0x34]. Gemini Summoner's 0x0220D69C:
  zone<=4 & is_gemini -> 0x10; zone 0xB & is_gemini 0x020230FC -> 0x50; else 0. Spirit filter = same with
  is_spirit 0x020230D4 (hand arm only).
- Resolver 0x0220D80C phases ([0x0229AAFC+0x70]-0x78 jump table):
  0x80: deny unless 0x021B9E6C(side) (NORMAL floodgate gate, mask 1, cid-blind) || 0x021B9DAC(side) (SET);
        count hand cards with filter&0x0225D6D4(side, ...) and field slots 0..4 via filter(side,i,0)&&0x021AF0A8;
        0 -> return 0x78; else prompt 0x0219A818(side, 0x27) -> 0x7F.
  0x7F: 0x0224B9C8(desc, filter) -> 0x7E.  0x7E: [0x0229DD94+0x58]==0 -> back to 0x80; if +0x6C in {4,6}:
        unless 0x021A14E8(side,0xB,?,1) post 0x021D2584(side, desc cid, 1, 0); hand ([+0x7C]==0xB) ->
        0x02261444(+0x6C==4, 0, 0) else 0x0224B1FC(0) -> 0x7D.
  => phase 0x80 does NOT check whether the regular NS is spent; only the per-card filter does
     (Ultimate Offering's 0x0220D63C: 0x021B9514 count>0 -> 0x50, else granter 0x021B95C4).
- NS counter 0x021B9514(side) = remaining NS: +1 if turn-flag word [0x0229ADB4+(side&1)*0xB3C] bit 20 clear
  (regular NS unused); + Double-Summon/Mausoleum (0x1D20 / 0x0E00 / 0x1C33 / 0x23D4) grants. Matches
  notes/scrap-raptor-findings.md:410-425. Bit 18 of the same word = SS this turn (KB PoD fact).
- Consume path 0x0226510C..0x02265182: spends by summon-desc (0x02298A28) +0x12 granter cid (0x21D3 / 0x20D6 /
  0x2115 / 0x245B arms post kind 2 on the granter). "Counter > 0 wins outright" (scrap-raptor findings,
  0x021B9674) => a C3 summon while the regular NS is unused WOULD SPEND THE REGULAR NS unless Sakitama is made a
  granter at the 4 granter sites (ninishi/Raptor CAVE_NS_* chain, steps.py:92/177) and the counter is forced to
  0 for its summon (Raptor's seam).

- Action-machine granter arm (stock 0x02261E3C..0x02261EF4): pred(desc+0xE) -> phase +0x24 (0 / 0x64) ->
  r6 = pool word 0x02261F84 (granter cid K) -> field lookup bl@0x02261E68 (blt bail) -> **0x021A1430(side,0xB,K)
  @0x02261E76, bne bail** -> counter bl@0x02261E92: !=0 -> 0xE2 announce 0x0219AA50 (answer lands in
  [0x0229DD94+0x34]); ==0 -> [+0x34]=1 -> phase 0x64: [+0x34]!=0 -> strh K -> desc+0x12 @0x02261EE8.
  => counter forced 0 for the arm = the grant is ALWAYS spent, never the regular NS (Raptor's seam).
- **0x021A1430 is KIND-AGNOSTIC for kind<6**: -> 0x021A1238 walks 0x0229D33C (stride 0xA), accepts
  ([+2]&0xF) < 6 && [+0]==key. 0x021A14E8 -> 0x021A1268 adds `cmp kind, r2` (kind-exact). Disassembled stock.
  => the native spent check @0x02261E76 treats ANY kind<6 node keyed K as "spent".
  => ⚠️ Scrap Raptor C1b (grant = kind-1 node keyed 0x0FF6, pool K = 0x0FF6) looks like it must bail at
     0x02261E76 by static reading. NOT tested here; out of scope -- flagged to user.
- Chained rom_all_patches.nds (2026-10-12 19:10) sites: 0x021B9634 bl 0x021C74CC (CAVE3_SR_NSARM),
  0x021B9F9C bl 0x0221AE54, 0x02261E3E bl 0x021F10B4, 0x02261E68 bl 0x021F17DC, 0x02261E92 bl 0x021F94C8,
  0x0226515C bl 0x021FAE58, 0x0226517C bl 0x021F10D8; 0x02261E76 still stock bl 0x021A1430;
  0x02265174 = `ldrh r1,[r4,#0x12]` (ninishi in-place: post key = desc+0x12).
- C3 resolver 0x7E post: r2 at 0x0220D942 = desc cid (set by `ldrh r2,[r5]` @0x0220D822, untouched after) ->
  query(side,0xB,cid,1) exists -> skip; else post(side,cid,1,0).

### C3 design (derived, not built)
- Granter key K = a dedicated never-posted key (NOT 0x13E5), because the resolver's native kind-1 post on
  0x13E5 would read as "spent" through 0x021A1430. Grant = kind-1 node on 0x13E5 posted by the C3 COST stub
  (= C3 HOPT; the resolver then skips its own post). Spent = native consume post (side, K, 1, 0).
- Six fronts chaining Raptor's CAVE3_SR_* (all ov3 -- shared NS path, an ov5 stub here crashes puzzles):
  SITE1 arm (is_spirit(r4) && kind1(0x13E5) && !node(K) -> return K), SITE2 spent (node(K)),
  SITE3 pred (is_spirit && grant live -> pool=K, 1), SITE3 field (K -> 0 / -1), SITE3 count (K -> 0),
  SITE4 match (K -> Z, r1=K). No NSPOST hook (native kind 1 on K is right).
- Known edge: C3 activated but no summon happens -> grant (kind1 0x13E5) outlives it for the turn.

- 0x0225D6D4(side, ref) = `0x0225D73C(side, ref, 1, 0)` = UNCOUNTED summonability (tribute/legality).
  The COUNTED one is 0x0225D6E0 (0x021B9514 > 0 || 0x021B95C4 granter). Resolver count (0x0220D8C0) and
  Gemini Summoner's cond 0x021FCDE8 (loop hand: is_gemini && 0x0225D6D4 -> return 1) use the UNCOUNTED one.
  => C3 can be ACTIVATED with the regular NS spent; the grant is what then permits the summon.
- 0x0220D7B4 callers (stock BL scan): 0x02200BF2, 0x0220D81C (the resolver), 0x02222488. Front the
  resolver's own BL @0x0220D81C (shared by UO/Gemini Summoner/Cry Havoc/BRL -> ov3 host).
- C4 arm: stock 0x021C93CC `movs r0,#0 ; str r0,[sp,#0x18]` then 0x021C93D0 (Assault's BL site). Only later
  write of [sp+0x18] before consumer 0x021CA980 is 0x021C943C (zeroes it iff node(side, [sp+0xA0], 0x19AE)) --
  native, applies to Shinai too. => [sp+0x18]=1 set at 0x021C93D0 == Shinai's state. Plan: FRONT the BL at
  0x021C93D0 with an ov5 stub (push {r1,r2}; arm; pop; ldr r0,=CAVE_ASSAULT_LEAVEHOOK|1; bx r0) -- Assault's
  stub untouched, lr preserved. Shared site is already ov5 (Assault), so no new puzzle exposure.
- Criteria "LIST B" 0x02271314 (ov3, two-row selector) != hand-effect LIST B 0x0209BC8C (arm9). No collision.
- Phase/turn (KB duel.phase_and_turn_player VERIFIED): [0x0229DD14+0x48] phase (2 MP1, 4 MP2),
  [0x0229DD14+0x34] turn player. C3 cond checks both (LIST B = hand QUICK list; don't rely on the menu).
- Granter key K: 0x3E50 (> every cid, < 0x4000 so clear of Assault's 0x4000|ref keys, bit 15 clear).

- 0x021B9EFC = "has this side Normal Summoned this turn (any route)": bit 20 -> 1; else any node on
  0x12F3 / 0x1D35 / 0x1CA4 / exact(0x209B,1) / 0x20D6 / exact(0x20D6,2) ... -> 1. 10 callers (0x021B1D1C,
  0x021F4BDA, ...). => Sakitama's spent key K MUST be in this chain (SITE2 link) or a grant-summon would not
  count as "Normal Summoned this turn".
- 0x02261444 callers: 0x0219DB56/76/A8, 0x0220D982 (C3 resolver), 0x022224C2 (Mausoleum), 0x0224C7CE /
  0x0224CCE8 (hand menu). => the C3 summon is the SAME launch as a menu Normal Summon -> same action machine arms.
- 0x021B9674 (can NS?) callers 0x021FAFD0, 0x0224BDAC, 0x0224BFFC. 0x021B95C4 callers 0x021B9688, 0x0220D672,
  0x0225D6FE (all boolean, per Raptor findings).
- desc[+0xC] = u16 ref (0x021E6FDE `ldrh r1,[r4,#0xc]`); 0x021A25A0(side, ref) -> hand idx or -1 (loop over
  [0x0229AC94+(side&1)*0xB3C+0x124+i*4], ref = bit14 | bits23..30 << 1).
- Target record helpers 0x022347B0.. write desc +0x10 (count) / +0x12 / +0x14+2n / +0x1E; 0x02208180 touches no
  desc+0x18. Uni-Zombie stores its mode at desc+0x18 (in-game confirmed) -> Sakitama mode byte = desc+0x18.
- Resolver filter mask: 0x10 = Normal Summon, 0x40 = Set (BRL baseline 0x10; 0x0225D6E0 granter path `ands 0x10`).
  Sakitama filter returns 0x10 (printed text: Normal Summon only).

- Hand-menu probe 0x021EDD90(side, idx, cid): zeroes a 0x24 desc, +0 cid, +2 side, **+3 = 0xB (zone hand)**,
  +0xC ref, +4 event code 0, then 0x021EC93C(desc). => MODE SWITCH = desc[+3] == 0xB (C3) else C4. Stable from
  activation to resolution (chain-link desc) -> no desc+0x18 state needed.
- Phantoms (scratchpad phantoms.py, no card_prop, rows identical stock/chained): cls1 0x1500 (1 row, unclaimed;
  window stock 155..210), cls2 0x1774 (1 row; only claim quickeffect_list = other pool; window 82..142),
  criteria 0x1446 (1 row; only claim ignition_cond_registry = other table; window stock 123..129, below crit[157]),
  hand LIST B 0x0209BC8C: 0x1774 (same phantom), flip list 0x0209BB5C: 0x1535 (unclaimed).
- card_genre: native Spirits 0x14FD 0x1400000, 0x1505 0x1040000, 0x1DFD 0x2001400040 (Recover from GY = 0x40).
  Sakitama = 0x1400040 (Recover from GY, (Flip), (Spirit)) -- hand-assigned (no 3DS row).

### BUILD 1 (2026-10-12) -- AWAITING IN-GAME TEST
- `_build_sakitama.py` on rom_all_patches.nds (19:10, newer than ninishi/raptor/assault modules) ->
  data/over_the_nexus/working/rom_sakitama.nds, sha256
  a762d486747a268354e5e0031eb54b4b8ad74ea7786f7b5ec080d4c7e0e619e1, verify 35/35 PASS (static only).
- check_allocations: OK (415 ov5 slots, 475 phantom claims, 124 ov3 pool slots), ledger emitted.
- EXECUTION PROOF of the 8 shared-site fronts: `python -m scratch.sakitama_equiv` -> identical 17155,
  Sakitama-owned 85, BAD 0. Old = same built bytes with the hook BLs put back. Real host + Raptor/ninishi code
  runs; engine leaves faked (pure queries not compared; fakes clobber r1-r3 = AAPCS caller-saved).
  Owned route checked: grant live + counter 1 -> phase 0: [0x0229DD94+0x34]=1, no 0xE2 announce, ->0x64;
  phase 0x64: desc+0x12 = 0x3E50 (old: 0); consume: POST(side, 0x3E50, 1, 0).
- NOT proven (needs the in-game test): the hand menu offers LIST B member 0x13E5 in Main Phase; reveal cost;
  0x0220D80C resolving from a hand-activated cls2 record; the leave consumer posting 0x13E5's trigger from
  [sp+0x18]=1 for a records-free cid; 0x02208181 + 0x02235605 + criteria 0x022409C9 resolving C4.

### BUILD 2 (2026-10-13) -- ALL-ov3 TEST HOME, AWAITING IN-GAME TEST (duel AND editor puzzle)
- User: "Temporarily move them into ov3 for testing". patch_sakitama.TEST_OV3 = True: COND/COST/RES/TGT/LEAVE
  in cave3 CAVE3_SK_* (cond compacted to 0xCC: player base in r7) + a byte-identical COPY of Assault's leave
  stub (_build_leave_hook @CAVE3_SK_ASSAULT 0x0221AB78); the site 0x021C93D0 now never reaches ov5 (Assault's
  ov5 stub is unchanged, merely unreferenced from the site in this ROM).
- rom_sakitama.nds sha256 1ba1fefa3f53c0b58ec961aad3b469f6fc3ee64a7ee47317b32a780a84ce37bf, verify PASS,
  check_allocations OK (130 ov3 pool slots), scratch.sakitama_equiv 17155 identical / 85 owned / 0 BAD
  (leave: Assault's real ov5 stub vs ov3 front + copy). No word in any Sakitama stub/record points >= 0x022C5900.
- ⚠️ Assault Synchron's OTHER stubs (C2COND/C2COST/C2CRIT/C2PRED, hand-SS cond) are still ov5: Assault's own
  C2 still cannot work in an editor puzzle. Ship decision (ov3 vs ov5 home) is the user's.

### BUILD 3 (2026-10-13) -- PUZZLE TEST BASE, AWAITING IN-GAME TEST
- User: "I still cannot open the puzzle interface, build the test rom off of the base rom/ov3 compact rom?"
- `_build_sakitama.py --compact`: rom_ov3_compact.nds -> EE ninishi (ov3) -> patch_scrap_raptor (ov3) ->
  patch_sakitama -> data/over_the_nexus/working/rom_sakitama_compact.nds, sha256
  e0509aeb1bab5bbdb0defd70043e4cf677f5d4ebccf6ba539a37b1305ec67a7b, BUILD_EXIT 0, verify PASS.
- No Assault on that base: patch_sakitama detects the stock `ldr r0,[sp,#0x44] ; cmp r0,#0` at 0x021C93D0 and
  builds the C4 front in REPLAY mode (leave_stub(chain=False)); no Assault copy installed.
  `python -m scratch.sakitama_leave_replay_equiv`: 44 identical (r0-r7, sp, NZCV, memory at/above sp) +
  4 armed exactly for 0x13E5 && left && 0x1000; 0 BAD.
- Default build (chained ROM) re-run after the refactor reproduced sha256 1ba1fefa... byte-for-byte.
- Ninishi / Raptor still put their OTHER card stubs (Raptor C1a/C2 etc.) in ov5 -- those two cards' own
  effects won't work in an editor puzzle; Sakitama uses only their ov3 granter stubs.

### IN-GAME TEST 1 (build 3, rom_sakitama_compact.nds e0509aeb..., puzzle) -- FAILED item 4
- User verbatim: "if i use Sakitama's effect I get 2 extra normal summons. instead of 1 extra normal summon."
  Clarified: reading A ("A, I hadn't normal summoned yet") = C3 summoned a Spirit, then 2 MORE Normal Summons.
  "all 3 monsters in my hand Can be normal summoned."
- Savestates rom_sakitama_compact.ml1 (after C3 summoned Sakitama itself) / .ml2 (after regular NS of Dark Dust
  Spirit). RAM stub bytes == ROM (CAVE3_SK_NSARM). Side 0 turn flags / slot-0xB nodes (walk 0x0229ACD2 head ->
  0x0229D33C stride 0xA, next @+8):
    ml1: flags 0x01810000 (bit 20 = 0: regular NS UNUSED); nodes (0x13E5,k1) (0x2146,k2); pool 0x02261F84 = 0x3E50
    ml2: flags 0x09810000 (bit 20 STILL 0); nodes + (0x3E50,k1) + (0x13E5,k2)
- PROVEN: the resolver-launched C3 summon consumed NOTHING (no bit 20, no K post) although the granter arm ran
  (pool = K) -> the consume path 0x0226510C.. is NOT reached for a 0x0220D80C-launched summon. The grant stayed
  live, and the REGULAR Normal Summon of a Spirit (Dark Dust) took Sakitama's arm and spent the grant (K posted)
  instead of the regular NS (bit 20 still 0) -> one summon too many.
- UNEXPLAINED: who posted (0x13E5, kind 2) between ml1 and ml2 (C4 cost's OPT key/kind).

- EXPLAINED from the board: ml2 field = Dark Dust Spirit 0x1526 (Lv6), Sakitama gone, hand gained Tsukuyomi
  0x1694 -> Sakitama was the Tribute, C4 fired (its cost posted (0x13E5, k2)) and added Tsukuyomi from the GY.
  ml1 summon desc 0x02298A28: +0xE 0x13E5, +0x12 = 0 (no granter stamped for the C3 summon); ml2 +0x12 = 0x3E50.

### BUILD 4 (2026-10-13) -- fix for test 1, AWAITING IN-GAME TEST
- res_stub (C3): bl 0x0220D80C; on return 0 (resolution over: phase 0x7D returns 0 only once
  [0x02298A28+0x1A] == 0, disassembly 0x0220D992..0x0220D9AA) post (side, 0x3E50, 1, 0) -> grant dead.
  Slot grew 0x18 -> 0x30: CAVE3_SK_RES 0x021F105C (ov5 twin CAVE_SK_RES 0x023A5810, old 0x023A57A0 retired).
  `python -m scratch.sakitama_res_check`: 15/15 (post only on 0, r0 passes through, C4 untouched, r4 kept).
- rom_sakitama_compact.nds sha256 510605d3da130cbc5f788639ff8d5fd52492154d537896d1fdd39d3389aa6a30;
  rom_sakitama.nds (chain) sha256 f8d55f662948b6885a9d1121508a7144a22545c65a6bf1542e828d02806b7db8; both verify PASS.
- Expected now: C3 summons a Spirit, then exactly ONE regular Normal Summon remains (any monster).

### SHIPPED 2026-10-13
- User verbatim: "Confirmed, only one normal summon left now, move to ov5 and ship it!" -> build 4's C3 fix
  in-game confirmed by user 2026-10-13 (puzzle, all-ov3 test home).
- Ship: card-only stubs back to ov5 (CAVE_SK_COND/COST/RES/TGT/LEAVE; test-home cave3 slots + Assault copy
  removed); the 8 shared-path stubs stay ov3. steps.STEPS "Sakitama" after Scrap Raptor (needs Raptor + Assault);
  _verify_all_patches.SHIPPED; patch_card_genre row 0x13E5; bulk_card_pack 'Grand Tiki Elder' -> 'Sakitama';
  donor moved to used (notes + scratch/donor_resource.json).
- patch_sakitama.unfronted(ov, site) lets patch_scrap_raptor / patch_assault_synchron / patch_ninishi verify()
  look through Sakitama's fronts (they asserted the direct BL).
- EE build 111/111 sha256 d7bceb0d76124c2df7574d8ce43c0146c4034301b1324f03c7e36d75506d0559; sweep 92 passed /
  0 failed. Previous chain ROM kept in the session scratchpad (rom_all_patches.before_sakitama.nds).
- Not individually reported in-game: C2 battle-flip return, OPT on a 2nd copy, the negatives, Assault regression.
  OPEN BUG (user-scoped): hand Tributes don't trigger C4.

## Ruled Out
- "Resolver-launched summon spends the grant via the consume path" (design assumption of build 1-3): falsified by
  ml1 (strike 1 on the C3 consumption mechanism).
- Two cls2 records under 0x13E5 (one hand ignition, one tribute trigger): the 2nd is unreachable (leftmost-only
  for cls2; KB dispatch.second_cls1_record_is_spirit_only / Warwolf E1-E2 shadow).
- A cls1 return PAIR for C2: unnecessary, Asura Priest ships return-only.

## Decisions (user, 2026-10-12)
- ONE cls2 record, ov5 slot stubs mode-switch on location: in hand (0x021A25A0(side, ref) >= 0) -> C3, else -> C4.
- Flip parity: add 0x13E5 to flip list 0x0209BB5C (phantom 0x1535 if free) + genre bit 22, like Aratama build 2.
- C4 field Tributes only for this build; hand-Tribute = OPEN BUG (not a deviation).

## Open Questions
- Single cls1 record (return only): does find_event_handler's leftmost+1 Spirit offset land on the next cid?
- Do C3 (hand) and C4 (GY trigger) records live in the same cls table (shadow risk)?
- C4 from hand (no "on the field" in the text) — engine bit only fires on field leaves.

## Next Experiment
- USER IN-GAME TEST of rom_sakitama.nds (sha256 a762d486...e619e1): the 11-item oracle in _build_sakitama.py.
  Report verbatim; quote back + MY INTERPRETATION before touching anything (CLAUDE.md).
- If C3 is not OFFERED from hand: savestate at the hand menu; emulate 0x0224BC40 for the Sakitama slot
  (LIST B membership 0x0202354C -> 0x021EDD90 -> CAVE_SK_COND) with scratch/thumbemu.py, as Thunder Sea Horse did.
- If C4 does not trigger on a Tribute Summon: savestate before tributing; check [sp+0x18] at 0x021CA980 via the
  CAVE_SK_LEAVE front (r4 == 0x13E5? [sp+0x2C]? [sp+0xC]&0x1000?).
- KB written 2026-10-12: dispatch.card_type_gy_to_hand_handler, summon.normal_summon_counter_and_has_summoned,
  summon.granter_arm_counter_decides_grant_vs_regular, dispatch.hand_probe_desc_layout,
  dispatch.ns_resolver_0x0220D80C (VERIFIED, 625 PASS / 0 FAIL); card.sakitama UNVERIFIED.
- SHIP-TIME TODO (only after user approval): steps.STEPS after patch_scrap_raptor + patch_assault_synchron
  (needs both); _verify_all_patches.SHIPPED; patch_card_genre GENRE row 0x13E5 'Sakitama' 0x1400040;
  rename 'Grand Tiki Elder' -> 'Sakitama' in patch_bulk_card_pack CHANGES; teach patch_scrap_raptor.verify()
  and patch_assault_synchron.verify() that their sites are now fronted (they assert the direct BL);
  move Grand Tiki Elder to "Used as donors" in notes/donor-pool-normal-and-effectless-fusion.md.
