# Life Stream Dragon — findings

Donor: **Steam Gyroid 0x18FA** (effectless Lv6 Fusion, recipe A[81] @ ov3 0x02270E1C) — user-chosen 2026-09-29.
Scope: all clauses (user, 2026-09-29). Status: **AWAITING IN-GAME TEST** (nothing built yet).

Text (ygoprodeck 25165047): 1 Tuner + "Power Tool Dragon". When this card is Synchro Summoned:
You can make your LP become 4000. You take no effect damage. If this face-up card on the field
would be destroyed, you can banish 1 Equip Spell Card from your Graveyard instead.
Synchro Tuner, Lv8 EARTH Dragon 2900/2400. Real Konami cid 0x2525 (3DS), absent from NDS pool.

## Confirmed
- `verify_knowledge` 2026-09-29: 595 facts, 529 PASS / 0 FAIL / 66 UNVERIFIED.
- donor_scan 0x18FA: only binding occurrence = fusion recipe A[81]; one ARM9 u16 at 0x0209CD20.
- 0x0209CD20 = entry [9] of the **"roid" set-code list**: thunk slot 0x15 of 0x0209D0D8, base 0x0209CD0E,
  count 28 (walked with scratchpad setwalk.py over reference arm9.bin). Must be removed or Life Stream
  counts as a "roid". Count-neutral fix: overwrite [9] with 0x18F5 (duplicate of [8]) — order kept.

- Proven by disasm 2026-09-29 and banked in author_facts (self-check 533 PASS / 0 FAIL):
  `lp.set_lp_primitive` (0x021CF8F4), `damage.effect_damage_immunity_gate` (0x021BAC34, Wombat arm
  0x021BACCC), `synchro.life_stream_named_nontuner_leaf` (tree entry 0x02248AB8 -> leaf 0x02249478),
  `setcode.roid_list_holds_steam_gyroid`.
- Hook sites byte-identical stock vs current chain ROM (scratchpad sitecheck.py): 0x02248AB8 (4 B,
  `ldr r0,=0x219D; str r0,[sp,#0xC]`), 0x021BACCC arm, recipe A[81]. 0x02248AAC is Azure Eyes's (expected).
- cls1 table 0x022860D4 x0x535 (24 B): 0x18FA has no record. Native optional-trigger shape = Karakuri
  0x23A0 {+04 res, +08 0, +0C 0x021F0419, +10 0x021E51E5, +14 0}. Unclaimed phantom rows exist (e.g.
  0x0E59 idx 14, single row).
- Trigger resolver protocol (template HANDSS_RES 0x02206ABC): phase word [0x0229AAFC+0x70]; act at 0x80
  -> return 0x7F; 0x7F / other -> return 0.

## C1 design
cls1 {0x18FA, 0, CAVE_LSD_RES|1, 0, 0x021F0419, 0x021E51E5, 0} over phantom 0x0E59; resolver = phase
0x80: set_lp(desc[+2], 0xFA0) -> 0x7F. summon_trigger_hook.ARMS += 0x18FA.

## C2 design
0x021BACCC `movs r2,#0 ; ldr r1,=0x18C4` -> `bl CAVE_LSD_DMG`; stub: 0x021AC0C8(r5, 0x18FA, -1) != 0 ->
bx 0x021BACDD (movs r0,#0; pop = immune) else re-issue r2=0, r1=0x18C4, bx lr (native Wombat arm).

## Build 1 (C0+C1+C2) -- 2026-09-29, AWAITING IN-GAME TEST
`_build_life_stream_dragon.py` layered on rom_all_patches.nds (fresh: no module newer except this session's
edits). Output rom_life_stream_dragon.nds sha256 04345ade654c2f14302a4af22d9bc02929dbd0c8a75bdcac903f4170ea677d45.
Verify PASS: life_stream_dragon + ASSD, Junk Speeder, Azure Eyes, Accel Synchron, Revolution Synchron,
Shooting Quasar, Boggart Knight, Scrap Archfiend. cls1 inserted @477 over 0x0E59 @14.
summon_trigger_hook.install now clears + rewrites its own slot when ARMS grew (chained ROM).
Caves: CAVE_LSD_MAT 0x023A33F0, CAVE_LSD_RES 0x023A3410, CAVE_LSD_DMG 0x023A3440; CAVE_FREE 0x023A3470.

## In-game test of build 1 (user, 2026-10-01)
Items 1 (card in Extra Deck), 2 (summons with Tuner + Power Tool), 4 (burn = 0 while face-up),
5 (burn hurts again when gone): **in-game confirmed by user 2026-10-01**. C1: "No prompt appeared"
on a Synchro Summon with Power Tool Dragon (savestates rom_life_stream_dragon.ml2 before / .ml3 after).
The negative material test (non-Power-Tool Lv7) was not reported.
ROOT CAUSE (static, KB dispatch.cls1_cond_0x021F0419_needs_criteria_row): cls1 +0C 0x021F0419 requires
a criteria-row candidate count; 0x18FA has no row -> condition 0 -> never offered. Savestates not
needed for this one.

## Build 2 -- 2026-10-01 (C1 fix)
User 2026-10-01: "Prompt Appears, if yes, LP goes to 4000. All good." -> C1 Yes path **in-game confirmed
by user 2026-10-01**. Not reported: the No path, the non-Power-Tool negative material test, and the
Junk Speeder / ASSD trigger regression.
cls1 +0C 0x021F0419 -> 0x021F0385 (Ljosalf of the Nordic Alfar 0x2459's row-less optional shape).
rom_life_stream_dragon.nds sha256 10fb7913d08b8940e79f063cd4c986b7a05da64c0c51def1f8997e911b6bd161;
same 9 verifies PASS.

## C3 RE (in progress)
- Step 5 0x0225C2B8 (step table 0x0228EF84) is the PICK-A-SUBSTITUTE UI step, keyed on r4 = the card
  being destroyed (0x021A36EC). Power Tool: [sp] = 0x1FC9 -> picker filter 0x0225C289 (else 0x0225C25D),
  message 0xE2 (else 0x14D), picker 0x0224B9F0(side, r4, 0, filter).
- Banked as `dispatch.destroy_substitute_is_field_only` (VERIFIED, 534 PASS): UI starter 0x0225BD40,
  step-5 wrapper 0x0225BE0C, called by the destroy engine at 0x021CE4F4 (+0x021CEBE6, 0x0225037A) after the
  gate 0x021A3858 / 0x021A32B4 and a ZONE-mask build via 0x021A3930 (S/T 5..9 for 0x1FC9/0x1FFC, else
  monster 0..4). Filters 0x0225C25D / 0x0225C289 read that mask. **No GY candidate path exists.**
- 3DS: real Life Stream takes the DEFAULT arm of the step-5 twin 0x00513B18; its GY-cost substitute lives
  in a separate 3DS step (0x5113F4, with Clear Vice / Gravekeeper's Visionary / Gachi Gachi) that has no
  NDS counterpart. 3DS 0x1E1684 / 0x1EB964 / 0x284F74 are AI heuristics; 0x242308 posts a hint.
- 0x021A3858 is a per-cid switch (0x1DF3, 0x1F0D.., 0x1F50, 0x1FC9, 0x1FFC, 0x2073, 0x207C, 0x219B) after a
  generic 0x02023A50 test -- NOT yet decoded semantically.

- Static trace 2026-10-01 (disasm only, UNVERIFIED on the live path):
  * Destroy state machine = [0x0229DE14+0x18] state / +0x1C index; a UI post sets state += 0x64
    (0x021CEF58) and the next pass reads the UI answer [0x0229DE54+0x24] (0x021CF28A).
  * 0x021CF25E..0x021CF2CE (state 0x65 loop over index 0..9): clears the card's bit in the
    pending-destroy mask [0x0229C314+0] (`bics` @0x021CF26C), calls 0x021CC290(side, zone, answer,
    card word), then sets bits in [0x0229C314+0x14/+0x18] from its result.
  * 0x021CC290 = per-card destroy EXECUTOR (recursive). Its answer decode @0x021CC66C: high byte =
    chosen zone; >=5 -> S/T path (Power Tool 0x1FC9 special-cased @0x021CC68A) -> recursive
    0x021CC290(chosen side, zone, 0xE, mode) destroys the substitute and clears bit [0x0229C314+4]
    for the original; <5 -> 0x021CC028 then the recursive destroy.
  * 0x021CC64A..0x021CC66A: cids 0x215A / 0x21BE / 0x22D3 take a 'survive' branch that only clears
    bit [0x0229C314+4] and exits (0x021CC8D8) -- a native "not destroyed" leaf, no substitute card.
    It is reached @0x021CC626 only when the card's bit in [0x0229C314+4] (SUBSTITUTE PENDING) is set;
    the substitute choice is read from the destroyed card's field entry 0x0229ACD4+side*0xB3C+zone*0x14
    (= card +0x40).
  * ANSWER CONSUMER 0x021CED62 (state loop, index -> side/zone by /5): if [0x0229DE54+0x26] != 0 it sets
    the card's bit in [0x0229C314+4] (str @0x021CED94), then 0x021CF7D4(side) ... (answer +0x24 in r5).
    Second setter 0x021CEFDE.. (index /0xB) also branches on 0x215A / 0x1C8B cids.
  => static chain: gate 0x021CE34E -> mask -> 0x0225BE0C (UI step 5) -> state+0x64 -> consumer
     0x021CED62 (bit +4) -> executor 0x021CC290 @0x021CC626 (survive leaf or recursive destroy).

## C3 design candidate (UNPROVEN -- needs the GDB trace below)
  H1 gate: at the 0x021CE3B2 cid compare, for 0x18FA: own GY holds an Equip Spell -> post step 5 with
     a dummy mask = Life Stream's own zone bit (keeps the AI path, which answers a mask bit).
  H2 step 5 (0x0225C2C4 r4 switch): 0x18FA -> Yes/No + a GY picker of Equip Spells; answer carries the
     GY index (human). AI: answer = mask bit -> executor auto-picks the first Equip Spell.
  H3 executor survive leaf (0x021CC64A chain): + 0x18FA -> banish the chosen GY Equip Spell
     (0x021C7118) and clear bit [+4] like 0x215A.

## Ruled Out
- C3 via the native step-5 picker alone: it can only offer field zones (mask bits 0..9). A GY Equip
  Spell cannot be a candidate without a new picker.

## Open Questions
- Research leads (UNVERIFIED until re-proven): set-LP 0x021CF8F4(side,val); damage gate 0x021BAC34 w/
  Des Wombat arm 0x021BACCC; THIRD leaf for 0x2525 @0x02248EF2 -> 0x02249478 (material == 0x1FC9);
  destroy-substitute step 5 0x0225C2B8 (Power Tool arms 0x0225C300/0x0225C364/0x0225C418).

## C3 -- Laval the Greater precedent (2026-10-01) -- IN-GAME CONFIRMED BY USER 2026-10-01
Build 3 items 9 (offer -> GY Equip Spell pick -> banished, Life Stream stays), 10 (No -> destroyed),
11 (no Equip Spell in GY -> no offer) and 12 (Laval the Greater regression) all confirmed by the user.
User asked to solve it without a trace. The NDS non-field substitute chain (KB dispatch.nonfield_substitute_laval,
VERIFIED) is Clear Vice / Visionary / Laval the Greater 0x22D3 -- and Laval's printed clause is
"banish 1 'Laval' monster from your GY instead", i.e. Life Stream's clause with a different GY filter; the
mover 0x021C7104 is the KB GY->banished applier. The field-only Power Tool path above is NOT used.
Build 3: criteria {0x18FA,0xFFFF,0x0223CA11,0x204} over 0x0E93; detours 0x021CE89C (decide) / 0x021CF00E
(consumer) -> Laval arms, 0x0225CAC8 / 0x0225CAF2 (step 9) flag-OR, 0x021CC656 (executor) survive.
FIRST TRY picked 0x021CE8A6 / 0x021CF018 (the 0x1FC7 compares) -- WRONG: both switches are binary trees
and 0x18FA < 0x1C8B branches away first; caught before build. Route proof by execution
(scratch/lsd_c3_route_proof.py on the built image): ALL ROUTES AS DESIGNED.
rom_life_stream_dragon.nds sha256 9c2cdc4dc0230c133f694d1c09d5c46d6507ec52c237a9790d14fa0f046aa25c, 9 verifies PASS.
ASSUMED (not executed): word 0x204 on the GY handler = Equip Spells (Power Tool's Deck row + the 3DS row).
The GDB trace script scratch/gdb_life_stream_c3_trace.py is no longer needed.

## SHIPPED 2026-10-01
User confirmed the remaining items 2026-10-01: 3 (non-Power-Tool material -> not offered), 4 (No -> LP
unchanged), 7 (Junk Speeder / ASSD triggers), 8 (Azure-Eyes, Des Wombat). User: "Ship it".
steps.STEPS (after Overtex Qoatlus) + _verify_all_patches.SHIPPED. EE build 87/87, sha256
9c2cdc4dc0230c133f694d1c09d5c46d6507ec52c237a9790d14fa0f046aa25c -- byte-identical to the in-game-tested
build 3. Verify sweep: 73 passed, 0 failed. Pre-ship chain ROM kept as rom_all_patches.pre_life_stream.nds.

## Next Experiment
None -- card complete.
