# Sekka's Light — findings (live)

Printed text (scratch/ygoprodeck_cache.json id 24940422, Normal Spell):
"If you have no Spells/Traps in your GY: Draw 2 cards, also, for the rest of this Duel after you
activate this card, you cannot activate Spell/Trap Cards or effects, except "Sekka's Light". You can
banish this card from your GY; reveal 1 monster in your hand, shuffle it into the Deck, then, draw 1
card. You can only use each effect of "Sekka's Light" once per turn."

Clauses: C1 no S/T in own GY (activation condition) | C2 draw 2 | C3 rest-of-Duel lock on own S/T
card/effect activation except Sekka's Light | C4 GY ignition (cost banish self; reveal hand monster,
shuffle into Deck, draw 1) | C5 HOPT per effect.
Scope: WHOLE CARD (user, 2026-10-18). Donor: Stop Defense 0x10E6 (user, 2026-10-18).
Plan: ~\.claude\plans\sekka-s-light-cached-lemur.md

## Confirmed
- Sekka's Light is NOT in the 3DS build (CARD_Name_E UTF-16 scan 2026-10-18). Present there:
  Upstart Goblin 0x131F, Pot of Duality 0x2321, Magical Mallet 0x198D, Reload 0x16D9.
- Nothing in the repo referenced Sekka's Light / 24940422 before this session (grep 2026-10-18).
- KB verify_knowledge 2026-10-18: 728 facts, 644 PASS / 0 FAIL / 84 UNVERIFIED (savestate oracle NO).
- Donor gate census for Stop Defense 0x10E6 (2026-10-18, stock rom.nds; donor_scan + scratchpad
  sekka_donor_sweep.py / sekka_ov5_tables.py, aligned u16/u32 in arm9 (reference_files/arm9.bin),
  ov3, ov5 + base±imm literal idiom in all three):
  - ov3: ONE hit = own cls0 record[103] @0x0227EFF4. No criteria row, no cls1/2/3, no registry row.
    base±imm idiom: 0 hits (ov3/arm9/ov5).
  - ARM9: 0x0202E8EE = instruction `asrs r6, r4, #3` (encoding 0x10E6) in a bit-loop — incidental.
  - ov5 (AI only, readers): T1 = 215 sorted 12-byte recs {u16 cid, u16 flags, u32 fnA, u32 fnB}
    @0x02399520..0x02399F34; Stop Defense rec @0x02399628 {0x10E6, 0xF104, 0x0236D7BD, 0x02370BE5};
    0x02370E18 = a literal in fnB 0x02370BE4's own pool. Pair table around 0x023990E4..0x0239944x:
    {u16 template, u16 sorted key} with template 0x10E6 for ~15 keys (0x1329, 0x1487, 0x148A, ...)
    = other cards reusing Stop Defense's AI handler (inferred, not traced). None of the shipped
    Spell donors (Sparks, Share the Pain, Gryphon, Return Soul, Yami...) are in T1.
    Precedent: Yami/Amazoness left ov5 AI mirrors untouched. Plan: leave them; CPU will still
    "think" 0x10E6 is Stop Defense (AI evaluation only, not a player gate).
  - Old cls0 +08 filter = zone-predicate wrapper with mask bit 0x100 Defense Position
    (safe-zone-findings L880) — disappears with the record rewrite.
  - CPU deck: patch_bulk_ydcs.py L4032-4033 — one Plant deck (Botanical Girl / Lonefire) runs 2x
    Stop Defense -> would become 2x Sekka's Light (duel-long S/T lock on the CPU). Decision for user.
  - Name slots (floor 8) e=12 < "Sekka's Light" (13) -> card_text.CARD_TEXT re-emit (no slot limit).

- DONOR APPROVED by user 2026-10-18 (Stop Defense 0x10E6). Leave ov5 AI tables untouched. Leave the
  Plant CPU deck's 2x Stop Defense as-is (user will sort it later).

### C3 lock site (static proof 2026-10-18; scratchpad sekka_bl_scan.py / sekka_callers.py)
- EXACTLY 3 Thumb BL sites target the predicate 0x021ECDA4 in arm9+ov3+ov5 (stock AND
  rom_all_patches.nds, byte-identical, none hooked yet):
  - 0x021EDA2E `fff7b9f9` in the funnel 0x021EDA14. It's the 1st call, unconditional (prologue: push, sub sp,
    r5=desc, [sp]=r1, ...). r0 = desc, r1 = 0. Non-zero -> `b 0x021EDC9E` (refuse).
  - 0x021D6B5C `16f022f9` in AI cleaner 0x021D6B44 (CPU turn cascade 0x021D6D34).
  - 0x021FC116 `f0f745fe` in 0x021FC104: temporarily sets desc cid = 0x1BA7 (Ancient City - Rainbow
    Ruins, Field Spell), asks the predicate, then restores it. Lock must apply here too (a Spell's effect).
- Funnel 0x021EDA14 BL sites (7): 0x021EC8B0/0x021EC8EA (in 0x021EC740 field), 0x021ECB7E/0x021ECBB8
  (in 0x021EC93C hand), 0x021EDE40 (0x021EDDEC), 0x02217EB2, 0x0223E29E.
- Reach: hand = 0x0224BC40 -> 0x021EDD90 -> 0x021EC93C -> funnel; field/Set S/T = 0x0224BC40/0x0224B644
  -> 0x021EC740 -> funnel; Spell GY row handlers 0x0224C590/0x0224C6C0 (= the GY row ptrs
  0x0224C591/0x0224C6C1) -> 0x021EC740 -> funnel; 0x0224C55C/0x0224C820/0x0224CC88/0x021D3BB0/0x0225186C
  -> 0x021EDDEC -> funnel.
- Activating player = desc[+2] ^ desc[+6]: the funnel deducts the LP cost from
  [0x0229AC94 + ((desc2^desc6)&1)*0xB3C] (catalogue 0x021EDA76..0x021EDAE0; KB line 2113;
  KB dispatch.criteria_probe_side_is_xor_desc6: on-field enumerator sets desc[+6]=1).
- PLACEMENT: all 3 fronts are on code EVERY card passes -> cave3 (ov3), never ov5 (cave3.py L305
  rule, Denko precedent: an ov3 hook into ov5 freezes everything in the puzzle editor).
- Front design: push; r4=desc; bl 0x021ECDA4; if r0 -> return r0; side=(d2^d6)&1;
  if 0x021A14E8(side,0xB,0x10E6,5) && d[0]&0x3FFF != 0x10E6 && !is_monster(d[0]) -> 1 else 0.
  It won't post UI msg 0x14 (the stock prohibited path does; cosmetic).
- RESIDUAL (not runtime-proven): an activation path that bypasses 0x021EDA14 entirely (Denko open
  question: Set Trap in a chain window). Static graph shows none; confirm in-game.

### C4 hand picker — SOLVED statically (2026-10-18; scratchpad sekka_c4_*.py, stock rom.nds ov3)
- NO criteria row needed. 0x0224B9F0(side, cid, param, CALLBACK) is pure setup ([0x0229DD94+0x4C]=8,
  +0x50 param, +0x60 cid, +0x74 side, [0x0229DE14+0xC] = callback). The CALLBACK is the filter:
  cb(r0 = candidate side, r1 = zone, r2 = hand index) -> 0x800 selectable / 0 not.
- ~35 distinct callbacks are passed natively (sekka_c4_cbargs.py: 0x022065F9 x27, 0x02210C15 x3, ...),
  so KB dispatch.selection_param_and_zone's aside "the only callback in the ROM is 0x022065F9" is
  WRONG as a ROM-wide claim (true only for the criteria-probing cost family).
- 0x022065F9 itself probes 0x02243FE0(side, ACTING desc[+0] cid, param) -> a template cid passed to
  0x0224B9F0 would NOT change its filter. RULED OUT: template-cid trick through 0x022065F9.
- TEMPLATE = resolver 0x0220B27C (ptr 0x0220B27D at ov3 0x02286828), phases on [0x0229AAFC+0x70]
  (0x80 prompt 0x0219A818(side,0x1F) / Yes-No 0x0219A9B4(desc,0x1E) -> 0x7F; 0x7F answer
  [0x0229DD94+0x34] -> 0x0224B9F0(desc[2], desc[0], 0, 0x0220B261) -> 0x7E; 0x7E 0x0224BBB0 ->
  0x021C6988(desc[2], [0x0229DE14], 0) hand->DECK, count [0x0229AAFC+0x74]++ -> 0x7D). Callback
  0x0220B260: `side == desc[+2] && zone == 0xB -> 0x800`. Resolution-time own-hand pick + hand->Deck
  is therefore NATIVE.
- Hand-card read idiom (callback 0x0221943C): [0x0229AC94 + (side&1)*0xB3C + 0x124 + idx*4] & 0x3FFF.
- Reveal ref idiom (reveal machine state 2 @0x021EAB82..0x021EABB2): w = hand word; ref =
  bit14(w) + ((w<<1)>>24)*2, stored desc[+0x14], then 0x021D2598(side, ref). Compute BEFORE the mover.
- Mallet resolver 0x02220004 (alt template): kind-7 request 0x02259A38(side,cid,cancel) ->
  0x0225985C(side,7,..); result [0x0229DE94+8] picked / +6 index; 0x7D shuffle 0x021D26CC; 0x7C draw.
- RULED OUT: discard request 0x022598A0 (kind 1 — it discards; KB says hooking its callbacks freezes).
- Template hand rows exist if ever needed: Ape Magician 0x218B row 1059 / Zeman 0x219D row 1072
  {aux 0xFFFF, 0x0223CB65, word 0x2} = "1 monster in hand".
- GYRES plan: 0x80 (no monster in hand -> 0) prompt 0x155 -> 0x7F arm 0x0224B9F0(side, 0x10E6, 0,
  SEKKA_CB) -> 0x7E: not picked -> 0x7F (mandatory); picked -> ref, reveal, mover(side, idx, 0) -> 0x7D
  shuffle 0x021D26CC -> 0x7C draw 0x021D12F4(side,1) -> 0. SEKKA_CB = 0x0220B260 + is_monster(hand cid),
  side compared against desc[2]^desc[6] (0x022065F9 form).
- UNPROVEN (runtime): reveal-then-move in one phase. Fallback: reveal in 0x7E, move in the next phase.

## Inherited from research agents (UNVERIFIED until re-proven this session)
- C3 hook candidate: predicate call 0x021EDA2E inside 0x021EDA14 (before desc[+5] split, so it also
  covers GY effects); AI cleaner 0x021D6B44 is a separate caller of 0x021ECDA4.
- Duel-long node = turn log kind 5: post 0x021D2584(side,key,5,0), query 0x021A14E8(side,0xB,key,5)
  (KB dispatch.turnlog_once_per_duel_is_kind_5).
- HOPT pair 0x021A14E8 / 0x021D2584 kind 1 / kind 2 (Psi-Reflector two-lock precedent).
- Draw-N resolver 0x022065B9 + count table 0x022704A4 {u16 cid, s16 n}; cond 0x021F069D needs row.
- GY offer: Dragon Rulers virtual GY rows — one free row (CAVE_RUL_GYROWS fits 6 exactly).
- Self-banish cost 0x021E5709. Reload resolver 0x02216974: 0x021C6988(side,idx,0) -> 0x021D26CC()
  -> 0x021D12F4(side,n).
- No free criteria phantoms -> hand picker for the reveal is the main open RE item.

### WHOLE CARD IN-GAME CONFIRMED BY USER 2026-10-18 ("All confirmed, ship it!") on BUILD 1 below. SHIPPED.
- Shipped to steps.STEPS (after Denko Sekka) + _verify_all_patches.SHIPPED. Donor renamed in
  patch_bulk_card_pack / patch_bulk_ydcs ("Stop Defense" -> "Sekka's Light", same cid; Plant deck kept as is).
  patch_dragon_rulers: EXTRA_GY_ROWS + _extra_gy_rows(rom) so its verify() accepts the appended 6th GY row.
- The C1 GY check runs on the menu check only (desc[+7]==0); the user's "All confirmed" accepted it as built.
- EE fast build 2026-10-18: 117/117 steps, exit 0, rom_all_patches.nds sha256 3e9041ec...8b65 -- BYTE-IDENTICAL to
  the in-game-tested rom_sekkas_light.nds. Verify sweep: 98 passed, 0 failed (incl. patch_dragon_rulers).

### BUILD 1 (2026-10-18)
- patch_sekkas_light.py + _build_sekkas_light.py, layered on rom_all_patches.nds (sha256 75cb14ea...e0af,
  untouched). Output data/over_the_nexus/working/rom_sekkas_light.nds sha256
  3e9041ec83d5ff08b264c5a46b918c3eee8a1f7b4e09757e4796df932ac38b65. verify() 7/7 PASS (static only).
- Stop Defense stock cls0 = {0x10E6, 0x022076A5, 0x021D883D, 0, 0, 0x02234E01} (stock idx 103, chain 102)
  -> {RES 0x023A7061, 0, COND 0x023A6F81, COST 0x023A7021, 0}.
- cls2: phantom 0x1B47 dropped @246, 0x10E6 inserted @45 (count 697). Only literal pointer into the cls2
  table anywhere (arm9/ov3/ov5, stock+chain) is the base 0x02275C04 @0x0224A398 -> the shift is safe.
- C3 front CAVE3_SEKKA_LOCK 0x0221ABC8 (60 B / 0x40) on 0x021EDA2E / 0x021D6B5C / 0x021FC116.
- ov5 CAVE_SEKKA_* 0x023A6F80..0x023A72A0 (CAVE_FREE now 0x023A72A0). Every stub disassembled after
  assembly: all blx literals odd, no pop {..lr}; assert_thumb1_only on each.
- Dragon Rulers GY rows: table 80 -> 96 B (6 rows, fits 0x60 exactly), exit/post/has regenerated with
  rod generators, Revolution's cid compared LAST. patch_dragon_rulers.verify on this ROM FAILS exactly the 3
  regenerated stubs (0x023A6E70 / 0x023A6E90 / 0x023A6EF0) -- expected; Rulers must learn the extra row at ship.
- check_allocations clean (ledger re-emitted). KB 646 PASS / 0 FAIL (+2 facts this session).
- NOT run (by rule, card not shipped): chain build, all-patches verify sweep.

## Ruled Out

## Open Questions
- RULING (ask user, never assert): C1's "no S/T in GY" is checked on the menu check only (desc[+7]==0),
  not again at resolution. Can-draw-2 is checked always.
- C4 reveal (0x7E) then hand->Deck (0x7D) in separate phases: runtime behaviour unproven.
- C3 runtime: any activation path that bypasses all 3 predicate sites (static graph says none).
- Lock front does not post the stock "prohibited" UI message 0x14 (cosmetic).
- At ship: patch_dragon_rulers must emit the 6th GY row itself (or accept it in verify); steps.py,
  _verify_all_patches.SHIPPED, donor-pool note Candidates -> Used.

## Next Experiment
- User in-game test of rom_sekkas_light.nds, checklist in _build_sekkas_light.py docstring.
