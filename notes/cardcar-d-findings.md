# Cardcar D — findings

Printed text (scratch/ygoprodeck_cache.json, id 45812361):
> "Cannot be Special Summoned. During your Main Phase 1, if this card was Normal Summoned this turn: You can Tribute this card; draw 2 cards, then it becomes the End Phase. You cannot Special Summon during the turn you activate this effect."

- C1 Cannot be Special Summoned — NOT in scope
- **C2 MP1 + Normal Summoned this turn; Tribute self; draw 2, then End Phase — IN SCOPE (session 2026-09-13)**
- C3 no Special Summon the turn C2 activates — NOT in scope

Status: **ALL THREE CLAUSES IN-GAME CONFIRMED BY USER 2026-09-13**, on Build 2
(`rom_cardcar_d.nds` sha256 `2d36da23236cefb40899029de385632d5e77bb5175677a1d3ca4f17ad0194b94`).
User: *"its perfect all 3 cluases confirmed"* / *"I had confirmed everything and
asked for it to be shipped"* (reported at the start of the next session, after
the testing session itself was lost to a usage limit before it could be
written up here). Earlier in the same day, Build 1 (clause 2 only, sha256
`03662bd3…6aefdc48`) was separately confirmed: *"Clause 2 works perfectly"*.
⚠️ The specific negative controls listed under Next Experiment (Special-Summoned
copy, Set copy, later-turn activation) were NOT individually re-confirmed by
name — the user's report was the three clauses as a whole, not a point-by-point
walkthrough. If any of those matter later, they still need to be asked about
directly rather than assumed.

**SHIPPED 2026-09-13**: wired into `apply_all_patches.PATCHES` and
`otn_enhanced.steps.STEPS` (both as the final card step before
WiFi timers), and into `_verify_all_patches.SHIPPED`. Chain re-baseline is the
remaining step (see *Not yet done*, now updated).

## Build (2026-09-13)
- `patch_cardcar_d.py --text` → `data/over_the_nexus/working/rom_cardcar_d.nds`
  sha256 `03662bd3bf4b64af0cc3863949194316b7964d210720e94d267fcd1f6aefdc48`
- `--verify`: 9/9 PASS (cls3 record exact, single donor record, phantom 0x0EC8 consumed, cls3 0x308 sorted, both stub bytes, BL targets, card text all 8 langs).
- card_prop read back: Effect Monster / EARTH / Machine / Lv2 / 800 / 400.
- Claims: `CAVE_CARDCAR_RES` 0x0239EDB0 (0x50, 76 B used), `CAVE_CARDCAR_COND` 0x0239EE00 (0x50, 80 B used), CAVE_FREE → 0x0239EE50; phantom claims `donor_cid 0x0FAE`, `cls3_table 0x0EC8`. `check_allocations`: OK.
- Stubs disassembled after build; every PC-relative load hits its pool word (0x0229DD14 / 0x801A / 0x800F; 0x0229DD14 / 0xB3C / 0x0229ACD8).
- NOT in the chain, NOT in `_verify_all_patches.SHIPPED` (not approved to ship).
- KB: `zone.bit16_normal_summoned_this_turn`, `duel.phase_and_turn_player`, `phase.becomes_end_phase_neko_body` — all PASS (421 PASS / 0 FAIL).

## Confirmed (2026-09-13, by disassembly this session)

- **Card is absent from the NDS**; 3DS has it: CARD_Indx/Prop record 5075, cid **0x272D** (neighbours Gagaga Gardna 0x272C, Overlay Eater 0x272E).
- **3DS Cardcar D cls3 record @0x6D2934**: `+04 0x404DB0` resolver, `+08 0`, `+0C 0x479828` condition, `+10 0x400794` cost, `+14 0`.
- **3DS resolver 0x404DB0**: `if 0x387B74(desc side, 2) != 0: 0x426AC4(desc, r1)`; returns 0. I.e. draw 2, then End-Phase body.
- **3DS 0x426AC4 = Neko Mane King's 3DS resolver 0x426A38 minus its `[0x7BB690] & 1` branch**: `if [0x7BCFA8+0x13C] != 5: 0x38D9F4(0x1A,1,5,0); 0x38D9F4(0xF | ([+0x128]?0x8000:0),0,0,0)`.
- **NDS Neko Mane King 0x15DB** cls2 record @0x0227672C `+04 0x02217339`. Resolver body @0x02217338:
  - `[0x0229C294+0x78] & 1` → post turn-log 0x021D2584(0,cid,1,0) and return (the branch 3DS omits for Cardcar)
  - else `[0x0229DD14+0x48] == 5` → return
  - else `bl 0x021C3BC8(0x1A | (desc[2]?0x8000:0), 1, 5, 0)`; `bl 0x021C3BC8(0xF | ([0x0229DD14+0x34]?0x8000:0), 0, 0, 0)`; return 0
  - 0x021C3BC8 = command-queue append (KB battle_attributes.yaml:339/367).
- **NDS phase/turn player**: `[0x0229DD14+0x48]` = phase. Formula cond 0x021F14CE..D6 accepts 2 or 4 ("Main Phase"), Neko skips on 5 (End Phase), Speed Warrior 0x021F1596 wants 3 (Battle). `[0x0229DD14+0x34]` = turn player (Formula 0x021F14C2 compares to `1-side` = opponent's turn; 0x021F1588 compares to side).
- **NDS zone word bit 16 == "Normal Summoned this turn"** (zone word = `0x0229ACD8 + (side&1)*0xB3C + slot*0x14`). Structural proof, NDS bit = 3DS `[slot+0x50]` bit + 16 on three independent bits:
  - generic offer gate: NDS 0x021F06E8 rejects bit 26 ↔ 3DS 0x49CD84 rejects bit 10
  - Speed Warrior cond: NDS 0x021FE4EC rejects bit 27 / requires bit 16 ↔ 3DS 0x4917B0 rejects bit 11 / requires bit 0
  - 3DS Cardcar's own NS check 0x492608 = bit 0 (+ slot-cid-still-matches check)
  - NDS Genex Neutron cond 0x021FEDDC ("End Phase of the turn this card was Normal Summoned") also requires bit 16.
- **3DS Cardcar condition 0x479828**: (0x46D328(desc) ≠ 0 OR per-player `[0x7B9FA8 + side*0xB74 + 0x158]` bit 2 clear) AND phase == 2 AND 0x492608 (NS this turn) AND 0x49CD84 (generic gate) AND 0x49C054.
- **NDS DRAW 0x021D12F4** = `push; r2=1; r3=0; bl 0x021D0950; pop` — a queue wrapper, return not proven meaningful.
- No NDS call to the zone-bit setter 0x021D2A40 passes bit 16 (119 callers scanned) — the summon path writes it directly.
- Donor **Mushroom Man 0x0FAE** (Normal, Lv2 EARTH Plant 800/600): `donor_scan` CLEAN; zero hits in finished_patches / otn_enhanced / notes / allocations.yaml / check_allocations.py.
- Phantom **0x0EC8**: no card_prop row, cls3[40], one cls3 row, present in rom.nds AND rom_baseline.nds, not in check_allocations.py.

### Clause 1 — "Cannot be Special Summoned" (2026-09-13, disassembly)
- **3DS list 0x68603C** (52 sorted u16 cids, pool ref @0x1CA9C4): Ra, Doomcaliber, Gandora, AG Golem/Beast, Gilford, … Steelswarm Hercules, 0x255A, 0x2599, 0x270C, **0x272D (Cardcar D)**. Every entry = a Normal-Summonable "Cannot be Special Summoned" card.
- **NDS twin = ARM9 0x0209BD6C, 48 entries** (the same list minus the four post-OTN cids). Phantoms in it: **0x193B, 0x19A8, 0x1B1A** (0x1B1A is claimed by gates_of_dark_world, but in the `draw_count_table` pool).
- Reader **0x02023398(cid)** (ARM9 Thumb): card_type 7 → 0; `0x02022E14(cid, 0x0209BB1A, 15)` hit → 0 (list = Victory Dragon + 14 phantoms); `0x02022E14(cid, 0x0209BD6C, 0x30)` hit → 0 (pool @0x0202340C, count `movs r2,#0x30` @0x020233C8); then the classifier checks; else 1.
- **On the SS path, unconditionally:** 0x021BA69C (dispatch.summon_from_zone_primitive's callee) @0x021BA6D0 `bl 0x02023398 ; cmp r0,#0 ; bne +; b 0x021BA6CA (movs r0,#0 reject)`. Other callers: ov3 0x021B1C0E, 0x0220964A, 0x0220E612, 0x0222021A, 0x0223BF36, 0x0223E9EE, 0x0225ACC6.
- **Ruled out: the class-1 classifier list 0x0209BE2C.** Every member is "cannot be Normal Summoned or Set" + own SS procedure (Card Breaker, Synchro Magnet, Monoceros …) — wrong shape, would risk clause 2's Normal Summon.

### Clause 3 — "You cannot Special Summon during the turn you activate this effect" (2026-09-13, disassembly)
- **Pot of Duality 0x2321** cls0 @0x0228578C: `+0C 0x02203259` cond, `+10 0x021E8E75` activation slot.
  - `0x021E8E74`: `if !0x021D2B88(desc): 0x021D2584(desc side, desc cid, 1, 0)` → posts key 0x2321 on the turn log at ACTIVATION.
  - `0x02203258`: same 0x021D2B88 guard → turn-log query (OPT) → reject if `[0x0229ADB4 + (side&1)*0xB3C]` bit 18 (Special Summoned this turn) → …
- **Can-SS mega-gate 0x021B9708, mode-bit-8 arm**, denies on key-only `0x021A1430(side, 0xB, key)` for keys 0x1F06 (exempt if summoning cid == 0x1F06), 0x0E0A, 0x1A29, 0x2262, 0x0D7F, **0x2321 (@0x021B993C, built as 0x2262+0xBF)**, 0x244A, 0x2275 (kind-2 query), 0x23D3 (exempt if summoning cid == 0x23D3; TSH's hook site 0x021B999A).
- 3DS Cardcar cond's per-player `[+0x158]` bit 2 ↔ NDS turn-flags bit 18 (the +16 map holds a fourth time).
- `0x021D2B88(desc)`: 1 if desc[4] == 0x25; else if desc[3] <= 4 and 0x02022FDC(cid) → reads a per-slot word via desc[0xC]. Not decoded → OMITTED from Cardcar's stubs.
- Chosen: reuse key 0x2321 (no new ov3 hook — a second BL-hijack in the shared mega-gate would branch into ov5 on every SS check and freeze puzzles). Side effect: PoD's OPT latch spent for that player that turn; after C2 it is the End Phase, where a Normal Spell cannot be activated.

## Build 2 (2026-09-13, clauses 1+2+3)
- `rom_cardcar_d.nds` sha256 `2d36da23236cefb40899029de385632d5e77bb5175677a1d3ca4f17ad0194b94`. `--verify` 12/12 PASS.
- Resolver bytes unchanged from the confirmed build. Condition grew to 96 B (bit-18 check); new cost stub 28 B.
- Slots: CAVE_CARDCAR_COND now 0x70 B; CAVE_CARDCAR_COST 0x0239EE70 (0x20); CAVE_FREE 0x0239EE90; claim `cannot_ss_list 0x193B`. check_allocations OK. No other patch touches 0x0209BD6C / 0x02023398.
- **ALL THREE CLAUSES IN-GAME CONFIRMED 2026-09-13** on this exact build (see Status at top).

## Ruled Out
- Wording precedents in OTN for "becomes the End Phase": only Neko Mane King (others in ygoprodeck — Hidden Fangs, Light Wing Shield, Parthian Shot, Photon Timestop, Summon Breaker, Veda — not in cid_to_name.json).

## Open Questions
- 3DS `0x49C054` (0x46A94C(desc) → 0x393A68(side^desc[0xA], r)) — unidentified; maybe a "can draw N" check. Skipped (ponytail): effect activates with <2 cards in Deck.
- 3DS per-player `[+0x158]` bit 2 gate — probably clause 3 ("already Special Summoned this turn"?). Not decoded.
- 3DS gates the End Phase on draw success; NDS draw return unproven, so the NDS stub does not gate.
- NDS `[0x0229C294+0x78] & 1` meaning (Neko's extra branch; also gates Speed Warrior code 0x021ECD24 and the attack-negate resolver) — omitted per 3DS.

## Next Experiment
NONE FOR THIS CARD — in-game confirmed 2026-09-13, all three clauses, and shipped
into both build chains the same day. The negative controls below were never
individually confirmed by name; only worth revisiting if a future report
suggests one of them is wrong:
- MP2 / later-turn activation attempts (should be rejected by the MP1 + NS-this-turn condition)
- Special Summoned copy (should reject the ignition entirely via clause 1's list membership)
- Set copy (same)

Chain re-baseline is the only remaining step — see *Not yet done*.

## Not yet done
`finished_patches/patch_cardcar_d.py` is a brand-new module, so the oracle
chain (`apply_all_patches.PATCHES`) is now stale by definition and needs a
deliberate re-baseline before the fast build (`otn_enhanced`)
can be trusted against it:
1. Copy `rom_all_patches.nds` aside (a killed chain leaves it partial).
2. Run `apply_all_patches` AS A SCRIPT (not `chain.main()`), assert the final
   step count and `ALL ... PATCHES APPLIED` plus the sha256.
3. Copy the result over `rom_baseline.nds`, record the new hash in
   `ygo_tools/tools/enhanced_edition_definitive/notes/CURRENT-BASELINE.md`.
4. `... .build --compare data/over_the_nexus/working/rom_baseline.nds` →
   expect `IDENTICAL <sha256>`.
5. Run the verify sweep (`... -m otn_enhanced.verify`
   or `_verify_all_patches.py`) and confirm N/N pass, N = previous 46 + 1.
