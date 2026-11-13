# Dragon Rulers — field-banish gap (C4 search) — findings

Status: **FIXED + SHIPPED** -- in-game confirmed by user 2026-10-19 ("All good that fixes things. Thanks. Ship it"), SHIPPED, on rom_rulers_field_banish.nds 2218e291...afba9 (H8, below). Patch: `otn_enhanced/cards/dragon_rulers.py`
(SHIPPED 2026-10-16). Found 2026-10-19 while testing Sacred Sword of Seven Stars
(notes/sacred-sword-of-seven-stars-findings.md).

## Confirmed (2026-10-19)
- USER REPORT 1 (verbatim): "Banishing a dragon ruler with its effect from field does not trigger the search effect see .ml2"
  -> confirmed reading: Redox 0x17CD face-up on field, banished as Sacred Sword's cost; NO prompt, no activation.
- USER REPORT 2 (verbatim): "1. Tidal 2. Dark Core 3. No activate prompt 4. See .ml3 (before) and .ml4 (after)"
  -> confirmed reading: NATIVE Dark Core banished face-up Tidal 0x115F from the field; no activate prompt.
- USER (verbatim, confirmed): a ruler banished FROM HAND by Sacred Sword DID trigger its search ("Yes that worked").
- Rulers' own oracle (_build_dragon_rulers.py item 6) only ever tested C4 "from hand AND from GY" -> field never tested.
- Savestates data/over_the_nexus/working/rom_sacred_sword.ml3 / .ml4 (ROM rom_sacred_sword.nds sha 66249a77...b0ef =
  chain + Sacred Sword; ov3 image match 1.0000 for both): ml3 side0 field zone 2 = 0x115F face-up, hand [0x130A, 0x14E2],
  GY [0x115E, 0x1145, 0x15A1], banished []; ml4 field empty, GY + 0x15E9 (Dark Core), banished [0x115F]. ml3 = Dark Core
  on the chain, before resolution (proven by the delta; read with knowledge.env.SaveState).
- Dark Core 0x15E9 cls0 @0x02280D4C (stock) = {0x02219B3D, 0x021DED59, 0x021F0221, 0x021E4EA5, 0x02234E11}; resolver
  0x02219B3C: 0x022349B0 target -> 0x0224A924 revalidate -> bl 0x021CF43C(desc, side, zone, kind=0).
- 0x021CF43C = mask 1<<(side*16+zone) -> 0x021CDD4C(desc, mask, 0x0F, kind): QUEUES a relocation
  (KB engine.relocation_request_core_0x021CDD4C, VERIFIED). Sacred Sword's mover 0x021CF40C is the same with a zeroed desc.
- Rulers' C4 detection (patch doc): H6 = cave3 0x021F105C on the banish worker's cid gate 0x021C71C8 (in 0x021C7118);
  H7 = cave3 0x021F1A0C on 0x021D1300's per-cid switch 0x021D1B98 (banish leaf 0x021D1D3E); H1 = cave3 0x021F1008 on
  find_event_handler miss tail 0x0224A86A, returning the BAN virtual record only when desc[+5] == 2 && desc[+3] == 0x0F;
  BAN +0C = ov5 CAVE_RUL_CONDB 0x023A6550 (OPT 0x021F6DD9 when desc[+7]==0, then Deck-candidate cond).
- 0x021D1300 has exactly 3 BL callers (stock ov3 raw scan): 0x021C6CB8 (core 0x021C6B00, hand/GY movers),
  0x021D1F06 (Deck mover), 0x021D2450 (in 0x021D2314, location-destroy core).
- Queue-consumer region 0x021CE0C0..0x021CF300 calls 0x021C7104(side, 0x021A25E8(ref), 0) at 0x021CECD0, 0x021CEFB8,
  0x021CF09E; 0x021C7104 = `r2 = (r2 != 0)` then bl 0x021C7118 (the banish worker holding H6). So a queued FIELD
  banish MAY reach H6 -- which arm Dark Core takes is NOT proven.
- Native "if banished" monsters in the NDS: Necroface 0x17BB (literals in the worker 0x021C724C AND in the
  0x021D1300 switch 0x021D1D9C), Cyber Ouroboros 0x1CF6 (worker gate 0x021C71C4/C8), D.D. Survivor 0x18BC
  (field-only wording; NO leave-mask row at 0x0226EC1C, NOT in the 0x021D1300 switch list; cls2[172], EP-registry
  row 0x0228E5FC, unexplained sorted list hit 0x0226D3A8).

- (2026-10-19 session 2, KB leave.descriptor_slots VERIFIED, measured 2026-09-14) a Dark Core FIELD banish DOES pass
  through the leave dispatcher 0x021C7FD0: dest 0xF, [sp+0x144]=0, [sp+0x28]=0, [sp+8]=0x15E9.
- (session 2, stock ov3 disasm 0x021C8054..0x021C8216) the dispatcher's arming before TREE 1: lists 0x0226E990 (battle+
  destroyed+GY, 0x6A) and 0x0226E904 (left field + GY, 0x1E) set [sp+0x18]=1; else the MASK TABLE bsearch
  `bl 0x02022E44(cid=r4, 0x0226EC1C, 0x98, 4)` @0x021C810C -> row ptr [sp+0x80]; mask = ldrsh [row,#2]; r5 = 1 unless
  dest==Deck; each mask bit may clear r5; r5 -> [sp+0x18] = 1. No mask bit expresses dest == 0xF (banished).
- (session 2) D.D. Survivor 0x18BC: NOT a leave-dispatcher card. cls2 record @0x02276C24 = {0x18BC, res 0x0221991D, 0,
  cond 0x021F9261, tag 0x021E9021, 0}; its cond requires locator zone (0x021A220C(desc[+0xC]) >> 8) == 0xF. EP row
  0x0228E5F8 = {0x0225498D, 0x18BC}. List 0x0226D384 (contains 0x18BC) is read only by 0x0219F69A (rider-node
  keep list, bl 0x02022E14 n=0x3C) -- unrelated to banish detection. LEAD CLOSED.
- (session 2, stock disasm) THE LEAVE TAIL POSTS THE SAME EVENT WORD AS H7's LEAF. Consumer 0x021CA980 switches on
  [sp+0x18]; variant 1 (0x021CA990) builds cid | ((w>>19)&0xF)<<16 | 1<<22 | ([sp+0x88]&0x3F)<<25 | side<<31 and
  `bl 0x021D3168` @0x021CAA48 (r1 = ref [sp+0x9C], r2 = [sp+0xA4]). H7's leaf 0x021D1D5C..0x021D1D92 builds
  cid | ([sp+0x30]&0x1F)<<16 | 1<<22 | ([sp+4]&0x3F)<<25 | side<<31 -> same bl 0x021D3168. So a ruler armed in the
  dispatcher with dest 0xF posts exactly the event H1's BAN branch already answers for hand banishes (only the
  6-bit code differs: 0x1D/0x17 vs 0x021D1300's [sp+4]; H1 BAN does not read desc[+4]).
- (session 2) no branch leaves 0x021C93D0..0x021CA980 except into 0x021CA980 itself (scripted scan); the only
  [sp+0x18] clear in that stretch is 0x021C943C (rider key 0x19AE present on the zone) -- not a dest test.
- (session 2) chain ROM rom_all_patches.nds: 0x021C810C is STOCK `5af69afe` (bl 0x02022E44) -- no patch owns it.
  (0x021C8216 / 0x021C9F1C / 0x021C93D0 are hooked by T.G. / Darksoul / Assault Synchron.)
- (session 2, stock disasm 0x021C7118..0x021C71A2) the banish worker (H6's host) looks the card up in the GY
  (0x021A2510) and returns 0 if absent -> H6 can NEVER post for a field card; no double post from H6.
- (session 2) Necroface 0x17BB's remaining list hit 0x0226E800 is inside the 159-key list 0x0226E7C4 walked by
  0x021C79A2 (rider-node cleanup 0x021C48DC on leave) -- not a trigger route. No native field-banish trigger
  precedent exists besides the leave dispatcher's arming (lists / mask rows).
- (session 2) cave3 free runs >= 0x10 re-measured from pool_blocks.FREE_RUNS - cave3 slots: 0x021F1A34 (0x10),
  0x021F5A96 (0x12), 0x021FAE44 (0x12), 0x02209A7C (0x12), 0x02220BCC (0x16). The prompt's 0x021F1994 (0x1A) is GONE.
- (session 2) [sp+0x80] (the mask row ptr) is read only at 0x021C8120 / 0x021C814A (ldrsh [row,#2]) -> a virtual
  row needs only its +2 halfword.

## Ruled Out
- "D.D. Survivor is a template for field-banish detection" -- its list hit 0x0226D384 is a rider keep-list; it has no
  leave-mask row. Not a precedent for the event post.
- "Sacred Sword's field mover is the bug" -- killed by report 2: native Dark Core fails the same way.

## Fix design (session 2, static -- AWAITING IN-GAME TEST)
- H8 = BL @0x021C810C (stock bl 0x02022E44, the leave-mask bsearch; r4 = cid) -> cave3 front split over
  0x02220BCC + 0x021F1A34: push {r0-r3,lr}; FINDK(cid); non-ruler -> pop args, native bsearch; ruler -> ov5 body:
  dest = ([caller sp+0x200] >> 19) & 0xF; dest == 0xF -> virtual mask row {_, 0x0004 "left the field"} else 0.
  -> [sp+0x18] = 1 -> tail posts cid | 0xF<<16 | ... -> H1 BAN (same word as H7's leaf).
- Residual risk: a field banish that ALSO reaches 0x021D1300 (H7) would post twice. Dark Core's evidently does not
  (no prompt in report 2), but not proven for every route.

## Build (session 2, 2026-10-19) -- in-game confirmed by user 2026-10-19 ("All good that fixes things. Thanks. Ship it"), SHIPPED
- `_build_rulers_field_banish.py`: H8 delta only, on rom_sacred_sword.nds (chain + SSS) ->
  data/over_the_nexus/working/rom_rulers_field_banish.nds sha256 2218e2916235bc8e1e803b940681087b78cd225cb6c42796745dd8bb808afba9.
- Slots: cave3 CAVE3_RUL_H8A 0x02220BCC (0x14), CAVE3_RUL_H8B 0x021F1A34 (0x08); ov5 CAVE_RUL_LEAVE 0x023A75A0 (0x20),
  CAVE_RUL_LVROW 0x023A75C0 (0x10); CAVE_FREE -> 0x023A75D0. check_allocations --emit: OK, ledger in sync.
- verify(): patch_dragon_rulers PASS (incl. new `bl @0x21c810c`, both H8 fragments, ov5 body/row, "no ruler owns a native
  leave-mask row"), patch_eclipse_wyvern PASS, patch_fire_formation_tenki PASS, patch_sacred_sword_seven_stars PASS.
- Built stubs disassembled from the ROM: 0x021C810C bl 0x02220BCC; H8A push{r0-r3,lr} / bl FINDK / bmi / bl 0x023A75A0 /
  add sp,#0x10 / pop{pc} / bl H8B; H8B pop{r0-r3} / bl 0x02022E44 / pop{pc}; body literal = 0x023A75C0, row +2 = 0x0004.
  0x02022E44 is register-only (no stack arg) -> the extra stacked LR in the native path is harmless.
- KB: leave.tail_post_word_matches_banish_leaf + leave.banish_worker_gy_only (VERIFIED), card.dragon_rulers_field_banish_gap
  updated (UNVERIFIED, next = in-game). author_facts --check: 804 facts, 718 PASS, 0 FAIL, 86 UNVERIFIED.
- NOT run (per brief): steps.STEPS wiring, chain build, sweep.

## Open Questions
- Does Dark Core's queued banish of Tidal reach 0x021C7118 / H6 (0x021F105C)? Does it reach 0x021D1300 / H7?
- If H6 fires: is an event posted, and does H1 (0x021F1008) get asked for 0x115F? With which desc[+3]/[+4]/[+5]?
  (a field-origin banish event may carry a different zone/selector than the hand/GY ones H1 accepts).
- If H1 returns BAN: does CONDB 0x023A6550 return 0 (OPT / Deck-candidate)?
- How does D.D. Survivor 0x18BC detect "banished while face-up on your side of the field" natively? (EP registry poster
  + some per-turn flag?) -- possible native template for the fix.

## Next Experiment
- IN-GAME (user): rom_rulers_field_banish.nds, the 6-item list in _build_rulers_field_banish.py. Watch for TWO prompts
  (would mean some field-banish route also reaches 0x021D1300 / H7).
- Only if it fails: ONE-SHOT GDB on the FIX ROM in a fresh normal duel (the old .ml3 carries the OLD ov3 in RAM, so
  it cannot test H8): break 0x02220BCC (H8A; log r4, [sp+0x200]), 0x023A75A0 (body; r0 after), 0x021CAA48 (post; r0),
  0x021F1008 (H1; [r4+0..7], [sp]), 0x023A6550 (CONDB; return), then Dark Core a face-up Tidal.
