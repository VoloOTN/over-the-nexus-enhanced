# Mara of the Nordic Alfar — findings (live)

Status: **WHOLE CARD IN-GAME CONFIRMED by user 2026-10-05 (build 2, sha256 95e50b93...a8dca2e); SHIPPING approved** (was: BUILT, AWAITING IN-GAME TEST) — rom_mara.nds sha256 7eaca55a…6e8ecc, verify 12/12, offline proof ALL PASS. NOT in steps.STEPS. Session 1 = 2026-10-05.

## Printed text (scratch/ygoprodeck_cache.json, id 73417207)
Level 2 DARK Spellcaster **Tuner**, ATK 1000 / DEF 500, archetype Nordic.
> When using this card as Synchro Material, the other Synchro Materials must be 2 "Nordic" monsters in your hand.

- C0 identity: stats, Tuner, text, Nordic set list (is_nordic 0x02023FC4). **IN SCOPE**
- C1 material rule: Mara (field) + exactly 2 Nordic monsters from the hand; no field partners. **IN SCOPE**

## User decisions (2026-10-05, verbatim answers)
- Scope: "C0 + C1 (Recommended)"
- Ruling (Mara from hand?): "Field only (match 3DS)"
- Donor: "Basic Insect is already used - Use happy lover. But make a note that Basic Insect shouldnt be offered."
  → donor **Happy Lover 0x106C**. **Basic Insect 0x0FD8 is SPENT** even though `donor_scan --free --level 2` lists it CLEAN.

## Confirmed (this session)
- Not in the NDS card set: scratch/cid_to_name.json has Nordic cids 0x2455-0x245E (9301-9310) + relics, no Mara.
- 3DS: `threeds_lookup "Mara of the Nordic Alfar"` → 3DS index 4750, **cid 0x25E5**, no registry rows (hard-coded, like Eccentric Boy 0x2184).
- **3DS 0x3d8a68 = hand-material-mode gate** (NDS 0x022494EC equivalent). Disassembled: returns 0 if pick count [G+0xcc8] == 0; else switches on FIRST pick cid (u16 at list [+0xa9c]+0x80 &0x7F) with pivot 0x250F (literal @0x3d8b8c):
  - `sub r1,#0x2000; subs #0x184` (Ecc 0x2184) / `subsne #0xcf` past that (0x2353 Parallel Gear) → return 1
  - pivot+0xD6 = **0x25E5 Mara → return 1**
  - 0x250F T.G. Cyber Magician / pivot+0x473 = 0x2982 → conditional return 2
  Callers (BL scan): 0x3d7048 (level_sum: on >0 loops hand idx, `bl 0x3d53d0(side, 0xB, i)`), 0x35e550, 0x4cf6e4, 0x4cf78c.
- **3DS validator 0x3d5e14**: r6 = (kind == 0xB). cid 0x25E5 (literal @0x3d6408, pivot of the cid switch) → 0x3d60b8: `if r6 → reject; if [G+0xcc8] != 0 → reject; else generic`. ⇒ **Mara is legal only as the FIRST pick, from the field.** Matches the user's ruling.
- 3DS 0x446c64: for Synchro cid 0x1EF0 (Urgent Tuning context) rejects if materials contain any of {0x2184, 0x2353, 0x250F, 0x25E5} (literal pool 0x446e90) — confirms Mara is in the hand-material family.
- ⇒ Architecture: **add the donor cid to the NDS hand-material mode** (gate 0x022494EC), with a Nordic filter (like Parallel Gear's Malefic filter) and count 2 instead of 1.
- Where 3DS enforces "exactly 2" / the Nordic filter: NOT FOUND yet (no other 0x25E5 literal / split-immediate in the binary). Probably generic data; NDS side must implement it.

- **Basic Insect root cause (fixed 2026-10-05):** patch_metal_armored_bug spends 0x0FD8 (steps.py:59, card_text 0x0FD8) but had no `donor_cid` claim, and `donor_scan --free` scans only the STOCK image. Fix: donor_scan --free now skips cids in card_text.CARD_TEXT or claimed `donor_cid`; added ("donor_cid", 0x0FD8, "metal_armored_bug") to PHANTOM_CLAIMS (ledger emitted, OK); donor-pool note + scratch/donor_resource.json updated. `--free --level 2` now lists only Happy Lover / Harpie Girl / Atlantean Pikeman.
- **Donor Happy Lover 0x106C** (Normal Lv2 LIGHT Fairy 800/500, pack1 55): donor_scan VERDICT CLEAN on stock. Name floor 9 B / desc floor 56 B → needs card_text.CARD_TEXT (re-emit path). Not in CARD_TEXT, no PHANTOM_CLAIMS.
  - stock arm9 0x0209B2F0 (ambiguous u16): context `18C4 188D 0FC0 0070 0050 3416 2408 8C00 | 106C 108D 0FC0 0090 0048 3422 ...` = repeated 8-u16 records with paired xx6C/xx8D values, not a cid table (ASSUMED non-cid).
  - chained rom_all_patches.nds: ov3 20 hits stock == chain (no new); ov5 0 hits; arm9 3 new hits at 0x020B2F00/18/28 are inside the grown ARM9 tail and decode as ARM `str/ldr rX,[rY,#0x6C]` (E580 106C etc.) — not cids.

- **Nordic set membership is a SUBTYPE TABLE, not a plain set list** (arm9 disasm, stock):
  - `0x02023FA4(cid)` = `bsearch 0x02022E44(cid, table 0x0209CEF8, 0x12 rows, 4 B)` → returns s16 row[+2] or 0.
  - is_nordic `0x02023FC4` = value > 0. Siblings: `0x02023FD8` (== 1, Beasts), `0x02023FEC` (== 2, **Alfar**), `0x02024000` (== 3, Ascendant), `0x02024014` (== 5, Relic). No predicate tests 4 or 6 alone.
  - Table 0x0209CEF8 (18 rows `{u16 cid, s16 subtype}`), stock == chain:
    - 0x0F85 = 1 (token)
    - 0x2455-0x2458 = 1
    - 0x2459-0x245B = 2
    - 0x245C-0x245D = 3
    - 0x245E = 4
    - 0x2478 / 0x248F-0x2491 = 5
    - phantoms **0x24EA = 3 (3DS: Vanadis)**, **0x24F0 = 6 (3DS: The Nordic Lights)**, **0x24F1 = 5 (3DS: Megingjord)**
  - No phantom is Mara's own 0x25E5. None of the three is in PHANTOM_CLAIMS / allocations.yaml.
  - ⇒ C0 plan: count-neutral insert {0x106C, 2} at index 1 (sorted after 0x0F85), drop **0x24F0** (subtype 6 has no dedicated predicate). Register ("nordic_subtype_table", 0x24F0, "mara").

- **NDS C1 mechanism, re-disassembled THIS SESSION on stock ov3 (capstone, scratchpad nds_synchro.txt):**
  - Gate 0x022494EC (leaf, `bx lr`): count [0x0229ABFC+0x7C] != 0, then the first-pick cid (u16 list via [+0x58], instance table [ref*8] & 0x3FFF) is compared with THREE POOL LITERALS:
    - 0x0E66 @0x02249534 (ldr @0x0224950A)
    - 0x2184 @0x02249538 (ldr @0x02249510)
    - 0x2353 @0x0224953C (ldr @0x02249516)
    → 1. **The cheapest gate edit is to repoint the 0x0E66 literal (no card_prop) to the donor cid. No code.**
  - Validator 0x02249AFC: `bl gate` @0x02249B12 (Revolution H1 site) → [sp+0x14]. The hand branch is @0x02249BE0:
    - side == [+0x6C]&1
    - r6 == 0xB
    - **@0x02249BEE `ldr r0,[r7,#0x7C]; cmp r0,#1; beq`** — count must be exactly 1 (r7 = 0x0229ABFC)
    - 0x021AEA7C(cid, -1) == 0
    - Par filter @0x02249C54 (first == 0x2353 → 0x02023E7C)
  - Validator Tuner order: @0x02249CD4 r7 = count and r0 = 0x02248280(synchro) (= Tuner count?). If count < r0, the pick must pass is_tuner_slot 0x021A1C7C and then OUTER. Otherwise the non-Tuner path 0x02249D1C runs a per-Synchro cid switch, then @0x02249D66: in hand mode the partner is rejected if `0x02023110(cid)` != 0 (Tuner?), else (field) it is rejected if is_tuner_slot. Then THIRD 0x02248A88.
    - ⇒ for ordinary 1-Tuner Synchros **the Tuner is always the first pick**, so Mara (a Tuner) is naturally first.
  - Validator field path: field cid @0x02249B8C → `bl 0x02029E60(cid)` @0x02249B92.
  - Validator tail 0x02249DE0: hand level via 0x021B20AC, then 0x02249A0C, then level_sum(side, kind, idx, lvl).
  - level_sum 0x0224966C:
    - pushes the pick (remaining [0x0229AAFC+0x74] -= lvl, count++, list append)
    - remaining != 0 → 0x02249924 (`bl gate`: hand loop vs field loop)
    - remaining == 0 → **completion @0x02249714 `ldr r1,[r6,#0x70]; ldr r0,[r6,#0x7C]; cmp r0,r1; bhs`**: count must be >= [+0x70] (the required material count), and if count > [+0x70] then 0x02248264(synchro) must hold.
    - ⇒ **Mara + 1 hand Nordic that closes the level would PASS natively** (count 2 >= 2). "Exactly 2" needs the completion minimum raised to 3 in Mara mode.
- **C1 hook plan (no code written yet):**
  - G = literal 0x02249534: 0x0E66 → 0x106C
  - V @0x02249BEE (count ∈ {1,2} + is_nordic for Mara mode)
  - C @0x02249714 (r1 = max([+0x70], 3) in Mara mode)
  - M = retarget the BL @0x02249B92 (field cid == donor at count != 0 → reject 0x02249B21)
  - No can_synchro hook is expected: Mara is a FIELD first pick, so the native can_synchro → validator → level_sum → gate → hand loop path covers it (Revolution needed H2 only because its first pick was in the hand).

- **COLLISION CAUGHT: the gate literal 0x02249534 (0x0E66) is CLAIMED by wattuna** (check_allocations `("hand_material_gate", 0x0E66, "wattuna")`). Wattuna is unshipped (build 1 failed in-game 2026-09-21) but still owns it. ⇒ Mara must NOT retarget the literal. Use caller-side hooks instead.
- Gate pool (stock): 0x02249524 = 0x0229ABFC, 0x02249528 = 0x0229A9FC, 0x0224952C = 0x0229AA58, 0x02249530 = 0x0229C33C, then 0x0E66 / 0x2184 / 0x2353.
- Hook sites, stock == chained (rom_all_patches.nds), and NO ov3 branch lands on site+2:
  - G1 0x02249924 `fff7e2fd` (bl gate, level_sum)
  - G2 0x02249B16 `05900028` (str r0,[sp,#0x14]; cmp r0,#0 — right after Revolution's H1 BL returns)
  - C 0x02249714 `316ff06f`
  - M 0x02249B92 `e0f565f9` (bl 0x02029E60)
  - V 0x02249BEE `f86f0128`
  Grep of finished_patches / KB / build scripts: only comments mention them (shooting_quasar docs 0x02249714; the KB proof asserts bl_target(0x02249924) on STOCK ov3, unaffected).
- From patch_shooting_quasar docstring: min_material_count 0x02248249 (LIST_B 0x02275AD8 → 3, else 2) = [+0x70]; rule_class 0x02248265 (LIST_A = exact count); required_tuner_count 0x02248281 = 2 only for 0x239F / 0x24B2.
  - ⇒ C stub: in Mara mode, if count < 3, force r1 = 3 (below required). Otherwise leave native r1, so LIST_A "exact 2" Synchros still reject 3 materials.
- Validator hand-cid read (native @0x02249BF6): player 0x0229AC94 + side*0xB3C (lits @0x02249DB4 / 0x02249DB0) + 0x124 + 4*idx → w; inst = ((w>>23)&0xFF)*2 + ((w>>14)&1); cid = [0x0229C33C + inst*8] & 0x3FFF.

- **Nordic table closed scan (stock):** u32 0x0209CEF8 appears ONLY at arm9 0x02023FC0 (no ov3 hit). BL callers of the reader 0x02023FA4 are exactly the 5 wrappers 0x02023FC6/FDA/FEE/02024002/16. Count = `movs r2,#0x12` @0x02023FA8. ⇒ the count-neutral row swap is closed.
- **GAP FOUND: the native hand branch has NO duplicate-pick check.** The field path's ref-vs-pick-list loop @0x02249BB6-0x02249BDC is skipped by the hand branch, and Ecc/Par only ever take ONE hand card. With 2 hand picks the same hand card could be picked twice. ⇒ the Mara stub must reject a hand ref equal to pick-list[1]. The list holds the same ((w>>23&0xFF)<<1)+(w>>14&1) ref space, which the field loop compares directly.
- Register liveness after the gate call @0x02249B16 (disasm): r1/r2/r3 are dead on every path (r1 set @0x02249B2C/0x02249BF6, r2 @0x02249B4E/0x02249BF8, r3 @0x02249BC6/0x02249D8E before any read). r7 = 0x0229ABFC is unchanged from 0x02249B00. ⇒ the stub may clobber r0-r3 and may jump to 0x02249BF7 (past the native `count == 1` check) with native state.

## Pre-build risk checklist (2026-10-05)
1. Per-cid gates on donor 0x106C — **PROVEN** clean (stock donor_scan + chained u16 scan, above).
2. Zone — **PROVEN**: hand partners are read from player+0x124 hand words (kind 0xB), the native read @0x02249BF6. Mara is a field first pick (Tuner-first rule @0x02249CD4).
3. Blob lengths — **PROVEN**: name floor 9 B < "Mara of the Nordic Alfar" → card_text.CARD_TEXT re-emit path (Revolution precedent).
4. Once-per-turn — N/A (no OPT on the card).
5. Hook sites stock in the chain, no mid-site branch targets, not claimed by any module — **PROVEN**.
6. Gate literal 0x0E66 — **CLAIMED by wattuna → not used**.
7. **ASSUMED (A2):** the procedure's hand-send step (0x0226395C, re-entered until no hand pick remains) sends BOTH hand picks. Static read only (inherited); in-game Revolution / Ecc only ever had one hand pick.
8. **ASSUMED (A4):** can_synchro (Extra Deck command) reaches hand mode through validator → level_sum → gate → hand loop when Mara is the field first pick. This is the native Eccentric Boy route (Ecc is a stock card), now through G1/G2.

- **User decisions 2026-10-05 (verbatim answers):**
  - Collision: "Take the literal" → Mara takes the gate literal 0x02249534 (0x0E66 → 0x106C). Wattuna's claim is transferred to mara, and Wattuna's U4 hand-material design must change (noted in wattuna-findings).
  - Assumptions: "Approve both (Recommended)" → A2 / A4 approved. The in-game test settles them.
  - ⇒ The gate is pure data, so no G1/G2 hooks. Hooks: V @0x02249BEE, C @0x02249714, M @0x02249B92.

- **BUILT 2026-10-05** `_build_mara.py` → data/over_the_nexus/working/rom_mara.nds. verify **12/12 PASS**. sha256 **7eaca55aad7bd33ea3cfc5a30ead6745568ff05d1fcf87616dc193f4066e8ecc**. **AWAITING IN-GAME TEST.**
  - Slots: CAVE_MARA_VALID 0x023A4690 (160 B / 0xB0), CAVE_MARA_COUNT 0x023A4740 (60 B / 0x40), CAVE_MARA_FIRST 0x023A4780 (40 B / 0x30); CAVE_FREE → 0x023A47B0.
  - Claims: donor_cid 0x106C, nordic_subtype_table 0x24F0, hand_material_gate 0x0E66 (moved from wattuna). check_allocations OK.
  - The built ov3 differs from stock ONLY at 0x02249534 (2 B), 0x02249714 / 0x02249B92 / 0x02249BEE (4 B each). ARM9 differs only in the Nordic table plus the arena-lo word 0x02051ED8 and the 0x02000B9C header word that every cave install moves.
  - All 3 stubs disassembled by hand: literals OK, validator [sp] at +0xC after push {r4,r6,lr}, no POP-into-LR, BL targets 0x02023FC4 / 0x02029E60 are Thumb.

- **OFFLINE EXECUTION PROOF — ALL PASS** (`scratch/mara_offline_proof.py`, thumbemu over rom.ml1 with ONLY the 3 stubs + Nordic rows overlaid; is_nordic / is_monster run for real):
  - is_nordic: 0x106C → 1, Dverg / Tanngrisnir / Guldfaxe → 1, **Relic 0x2478 → 1** (⇒ the is_monster filter is REQUIRED), Ecc / BEWD → 0.
  - V accepts: count 1 + Dverg; count 2 + Tanngrisnir.
  - V rejects: the same Dverg twice, count 3, BEWD, the Relic.
  - V non-Mara (Ecc first) returns the native count with native flags. r4/r6/sp are restored.
  - C: Mara + 1 → required 3; Mara + 2 → native 2; LIST_B → 3; Ecc + 1 → 2.
  - M: Mara at count 0 → is_monster; at count 1 → REJECT 0x02249B20; any other cid → is_monster.
  - Note: a Nordic TUNER in hand (Guldfaxe) passes V by design; the native hand-partner Tuner reject `0x02023110` @0x02249D66 handles it downstream (not executed here).
- **Composition** (Mara applied to a copy of rom_all_patches.nds, scratchpad chain_plus_mara.nds): verify() OK for revolution_synchron, unknown/steam/accel/assault/jet synchron, shooting_quasar, ninishi, junk_speeder, accel_synchro_stardust_dragon. Mara's own checks all PASS except the text, which is expected (applied with write_text=False).

- KB contributed 2026-10-05 (author_facts --check: 565 PASS / 0 FAIL / 71 UNVERIFIED; all 4 new facts PASS): `setcode.nordic_subtype_table`, `synchro.threeds_mara_is_hand_material_mode`, `synchro.level_sum_completion_min_count`, `synchro.hand_branch_has_no_duplicate_check`.

- **IN-GAME TEST 1 (user, 2026-10-05, rom_mara.nds sha256 7eaca55a…6e8ecc)**, verbatim: "See .ml3, 4, 5, when i performed a synchro summon only 1 of the materials selected from the hand went to the GY, as you can confirm from the GY. 1. Confirmed … 10. Confirmed" (all ten listed as Confirmed). Follow-up answers: "1. Still in my hand" / "2. That is correct" (ml3 = before the summon, ml4 = during material selection, ml5 = after; taken on rom_mara.nds).
  - ⇒ items 1, 3-10 in-game confirmed by user 2026-10-05. Item 2 is a **BUG**: the Synchro summons, but only ONE of the 2 hand Nordics goes to the GY; **the other stays in the hand**. **Assumption A2 is FALSIFIED** (the procedure's hand-send does not send both).

- **ROOT CAUSE of test-1 item 2 (static, stock ov3, this session):** procedure 0x02263494 step table (i16 @0x022634AE, base 0x022634B0) = {0 0x022634C4, 1 0x02263500, 2 0x0226350E, 3 0x0226362C, 4 0x022636C6, **5 0x0226395C**, 6 0x022639BA, 7-9 0x022639F8, 10 0x02263606}.
  - Step 5 FIRST writes `step = r1+1` (`adds r0,r1,#1; strh r0,[r4,#0x24]` @0x0226395C, r4 = 0x02298A28). It then loops r5 < [0x0229ABFC+0x70]; for the first pick with `0x021A25A0(side=[r4+2], ref) >= 0` (still in hand) it runs anim 0x4D (0x021C3BC8), sends `0x021C6E74(side, hand idx)` @0x022639AA, and RETURNS (`b 0x022635EC` → 0x022634FC, r0 = 0).
  - The next call runs step 6 (anim 0x4E, then step++). ⇒ **step 5 sends EXACTLY ONE hand card per Summon.** That is enough for Ecc/Par/Revolution (one hand card) and is why Mara's second Nordic stayed in the hand.
  - The +0x70 bound is NOT the problem: step 3 @0x022636BC copies the pick count into +0x70 when the level closes, so it is 3 here.
  - **CORRECTION:** revolution-synchron-findings' "re-entered each frame until no hand pick remains" is WRONG.

- **SAVESTATE-MEASURED (rom_mara.ml3/4/5, this session):**
  - Synchro 0x1D7C, side 0. ml4 (selection): picks [Mara ref 2, Dverg ref 68, Tanngrisnir ref 42], count 2.
  - ml5 (after): count 3, +0x70 = 3, picks unchanged; the hand lost **Dverg (pick 1)**, but **Tanngrisnir (pick 2) is still in the hand at idx 0**.
  - ⇒ this exactly matches the "step 5 sends one hand card" mechanism (pick 1 sent, pick 2 never visited).
- **FIX DESIGN (S hook):** 0x0226395C `adds r0,r1,#1; strh r0,[r4,#0x24]` (`481ca084`, stock in the chain, no branch to +2, unclaimed) → BL CAVE_MARA_SEND.
  - Replay the step write. In Mara mode (pick 0 == donor), for picks i = 2 .. +0x70-1: idx = 0x021A25A0(side = [r4+2], ref); if idx >= 0 → anim 0x021C3BC8(0x4D | (side ? 0x8000 : 0), 0xB, ref, 0), then 0x021C6E74(side, idx). The native loop then sends pick 1.
  - No card is handled twice. Each idx is re-resolved by ref right before its send, so it is correct whether 0x021C6B00 moves the card immediately or queues it. (Repeating step 5 instead was rejected: if the move were queued, it would re-send the same card forever.)

- **BUILD 2 (2026-10-05)**: S hook added. `_build_mara.py` verify **15/15 PASS**. sha256 **95e50b937724496db4aefeef484355f08f82b84ad36bced6eb1563ab7a8dca2e** (build 1 copied to scratchpad). **AWAITING IN-GAME TEST.**
  - Slot: CAVE_MARA_SEND 0x023A47B0 (136 B / 0x90); CAVE_FREE → 0x023A4840; ledger OK (376 slots).
  - Offline proof **17/17 PASS**, incl. S over the REAL rom_mara.ml5. It sends exactly anim(0x4D, 0xB, ref 42, 0) + send(side 0, idx 0) = Tanngrisnir, writes step 6, and restores r4/sp. Negative control (pick 0 not the donor) sends nothing.

- **IN-GAME TEST 2 (user, 2026-10-05, build 2 sha256 95e50b93...a8dca2e)**, verbatim: "All confirmed, Ship it". ⇒ whole card in-game confirmed by user 2026-10-05 (incl. item 2: both hand Nordics to the GY). Shipping approved.

- **SHIPPED 2026-10-05:** step 90/95 "Happy Lover -> Mara of the Nordic Alfar (whole card)" after Eva in steps.STEPS, plus _verify_all_patches.SHIPPED; donor pool updated. EE build **95/95**, exit 0, 442.7 s, rom_all_patches.nds sha256 **8bd8c08554b2ea326706cd1353d1f9dd9aaa6317e30b27da9ca051eefbf49f64** (previous chain ROM copied to the scratchpad first).
  - Verify sweep: **80 passed, 1 failed**. patch_mara PASS. The FAIL is patch_no_banlist_mode "name id changed": that assertion is not in the on-disk module, which is untracked and was modified at 12:23 DURING the sweep (not by this session). Re-running its on-disk verify() on the same ROM PASSES. Not a Mara regression.

## Inherited, UNVERIFIED until re-read this session (notes/revolution-synchron-findings.md)
- 0x022494EC leaf: count 0x0229ABFC+0x7C != 0 AND first pick cid ∈ {0x0E66, 0x2184, 0x2353}; callers 0x02249924 (level_sum) and 0x02249B12 (validator; HOOKED by Revolution H1).
- Validator hand branch requires count == 1; Par's partner must pass 0x02023E7C (Malefic).
- Procedure 0x02263494 sends hand picks to GY at 0x022639AA (HOOKED by Revolution H3).

## Ruled Out
- (none yet)

## Open Questions
- Who spent Basic Insect 0x0FD8, and why does donor_scan/ledger not know?
- NDS: how is Eccentric Boy kept out of non-first picks? How is "exactly 1 hand partner" enforced (count==1 only, or level closure)?
- Does native can_synchro explore hand mode, or is a Revolution-H2-style pass needed?
- Nordic set list capacity (stock + chain).

## Next Experiment
- **User re-runs item 2 (+ regression items 3, 6, 9) on build 2, rom_mara.nds sha256 95e50b93...a8dca2e, in a NORMAL duel.** Both hand Nordics must reach the GY. Report protocol: quote verbatim → MY INTERPRETATION → wait.
  - Synchro not offered at all → A4 (can_synchro) is wrong; check with a savestate.
  - A Nordic stays in the hand after the Summon → A2 (hand-send loop) is wrong.
- DONE: shipped 2026-10-05 (see Confirmed).
