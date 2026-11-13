# Obedience Schooled — findings

Printed (scratch/ygoprodeck_cache.json 72537897, Normal Spell):
"If you control no monsters: Special Summon 3 Level 2 or lower Beast-Type Effect Monsters with
different names from your Deck. Their effects are negated, and they are destroyed during the End
Phase. If you activate this card, you cannot Special Summon for the rest of this turn, except
Beast-Type monsters."

Clauses: C1 control no monsters | C2 SS 3 Lv<=2 Beast Effect, different names, Deck | C3a negated |
C3b End-Phase destroy | C4 Beast-only SS lock.
Session 1 scope (user 2026-10-01): C1 + C2. User rulings 2026-10-01: donor = Abyssal Designator
0x17F4; activation needs >= 3 distinct-name candidates in the Deck, summon is always exactly 3.
Status: C1+C2 in-game confirmed by user 2026-10-01 (oracle items 1-7). NOT shipped (not in steps.STEPS).

## Confirmed (2026-10-01, stock ygo_tools/reference_files images, ov3 base 0x02141700)
- Not in the 3DS build: CARD_Name_E.bin has no "Obedience" (UTF-16 find = -1; "Dark Simorgh" found
  as a sanity check). Not in the NDS build either (no decompiled card file).
- Donor 0x17F4 Abyssal Designator (`donor_scan 0x17F4`: ENTANGLED, 3 bindings):
  - cls0[554] (base 0x0227E64C, stride 24) = {0x17F4, 0, 0x0221C955, 0, 0x021F8515, 0x021E4D81, 0x02237D8D}.
  - criteria row 312 (base 0x022713C4) = {0x17F4, 0xFFFF, 0x0223E821, 0x00000002}.
  - LP-cost table row at 0x0226F254 = {0x17F4, 1000}. Table 0x0226F1A8..0x0226F328, 97 rows
    {u16 cid, s16 LP}, sorted. Sole literal ref @0x021E4B50, loaded by `ldr r1` @0x021E492A in
    getter 0x021E48D4(desc): `movs r2,#0x61; movs r3,#4; bl 0x02022E44` -> hit ? ldrsh [r0+2] : cid switch.
  - Getter's 10 BL callers (all inside per-card fns): 0x021E4D8C (fn 0x021E4D80 = Abyssal's COST,
    also used by cls rows for 0x17C9/0x18EC/0x1E23/0x1E8F/0x208D/0x2352), 0x021E781A, 0x021EDADE,
    0x021F81BE, 0x021F9556, 0x021FE626, 0x021FED82, 0x021FF2CA, 0x021FFBE8, 0x022043F8.
  - Other u16 hits are code: ov3 0x02168D84 / ARM9 0x02038254 are ARM `ldr r1,[pc,#0x7F4]`
    (0xE59F17F4); ARM9 0x0208BF02 is Thumb `asrs r4,r6,#0x1f` in a run of arithmetic.
- Rescue Cat 0x1876: criteria row 340 = {0x1876, 0xFFFF, 0x0223CA99, 0x588C0002} (Beast Lv<=3, Deck).
  Its cls record is at 0x0227AFEC: {0x1876, 0, 0x0221DA95, 0, 0x021F8EC5, 0x021E6FF5}.
- Shared native "SS N from Deck" resolver 0x0221DA94 (disasm): it starts with a cid switch on desc[+0].
  - Default arm: r5 = 2 (count), r7 = 1 (exactly N), r6 = 1.
  - Arm literals: 0x207F, 0x17B2, 0x1BF2, 0x225E, 0x24B5.
  - Users: 13 cls records with fn 0x0221DA95. Cids 0x207F, 0x225A, 0x225E, 0x1876, 0x1F90, 0x1FF4, 0x2213,
    0x1BF2, 0x17B2, 0x1C79, 0x1C86, 0x1DC1, 0x24B5.
  - Phase 0x80 checks: 0x021B9ECC, then 0x021AD870, then 0x02243FA8(side, cid, 0) >= r5 (r5 forced to 1 when r7 == 0).
  - The picker call is 0x0219C430(side, r5+6 or r5+0x27, cid, 0).
- Criteria word for Beast Lv<=2 monster = 0x58880002. It is derived from Rescue Cat's 0x588C0002, with the level
  byte 0x8C (<=3) -> 0x88 (<=2). KB counter_engine.yaml lists 0x88 = Lv<=2.

- 0x021E780C = a generic "pay LP cost" COST fn. It calls the getter, then pays.
  - It is reached only through a record COST field: pointers sit in the cls tables (0x0227604C…) and in the COST-fn list at 0x0224B030.
  - New cls0 COST = 0, so this path is closed for 0x17F4.
- 0x021EDA14(desc, r1) calls the getter on the evaluated desc @0x021EDADE.
  - It is reached by BL from generic code: 0x021EC740 <- 0x021EC654 <- 0x022398C8 / 0x02239A30 / 0x0224B8B0 / 0x0226A75C, and 0x021EDCE0 <- 0x0224B644.
  - So it may run cid-blind, and the 1000 LP row could leak into an affordability check.
  - **Decision:** zero the row value: {0x17F4, 1000} -> {0x17F4, 0} at 0x0226F256. This is count-neutral and keeps the table sorted; the getter returns ldrsh [hit+2] = 0.

- 0x17F4 is in neither row-offset list (A 0x0227134C/0x3B, B 0x02271314/0x1B; both sorted).
  Emulating the stock cid compare tree from 0x02243C1C (scratchpad rowwalk.py, scratch/thumbemu.py over
  the ov3+arm9 images, r5 = cid, r4 = param, r6 = 312) returns row index 0x138 = 312 at 0x02243F22 for
  param 0 AND param 0x159D234. Path length 45, the same exit as 0x170F (Ojamassimilation, in-game
  confirmed). So every packed-exclusion param lands on row 312.
- Native Deck handler 0x0223CA98 (disasm): builder 0x0223BC3C(side, cid, pred 0, ctx 0, [sp] = row word, [sp+4] = 0xA).
- COUNT 0x02243FA8 (disasm): row lookup 0x02243B9C(cid, param), then resets [0x0229944C+6], then calls 0x02243F38 (handler, r2 = param), then returns ldrsh [0x0229944C+6].

## Ruled Out
- Basing C2 on the native resolver 0x0221DA94. It has no "different names" handling, and count 3 would
  need a new arm in the ov3 cid switch.

## Build 1 (2026-10-01) -- C1+C2 in-game confirmed by user 2026-10-01 (oracle items 1-7)
- patch_obedience_schooled.py + _build_obedience_schooled.py. Base rom_all_patches.nds sha256 7ab4355c...94ea65fe.
  Only patch_card_art is newer (art entries, cosmetic).
- Output rom_obedience_schooled.nds sha256 6ce389ac74cb040b23075aaf63a0556f1bc9becf9f758ad99c212781c265ba17.
  verify 6/6 PASS, exit 0.
- verify() also PASSes on the built ROM for the sibling Deck-SS modules: ojamassimilation, double_evolution_pill,
  petiteranodon, soul_charge, miscellaneousaurus.
- Tables:
  - cls0[554] -> {0x17F4, RES|1, 0, COND|1, 0, 0}.
  - crit[312] -> {0x17F4, 0xFFFF, HANDLER|1, 0x58880002}.
  - LP row 0x0226F254 -> {0x17F4, 0}.
- ov5 slots: CAVE_OS_PRED 0x023A3FB0 (0x48/0x60), HANDLER 0x023A4010 (0x28/0x40), COND 0x023A4050 (0x68/0x80),
  RES 0x023A40D0 (0x104/0x120); CAVE_FREE -> 0x023A41F0. check_allocations --emit OK (363 slots).
- Claims: donor_cid 0x17F4, lp_cost_table 0x17F4.
- Stub check: every BLX literal is odd (21) and there is no pop {..lr}. PRED reads the entry [sp] / [sp+4] at
  [sp+0x10] / [sp+0x14] after a 4-reg push.
- Deck builder pred call (disasm 0x0223BDE2..0x0223BE0C): pred(side, 0xD, idx, r3, [sp] = &card word,
  [sp+4] = ctx); survivors are recorded by 0x02243B2C into 0x02299458 (KB-verified recorder).
- Test deck: there is NO Lv<=2 Beast Normal Monster in the NDS, so the Normal-Monster filter cannot be tested
  in-game. 28 Lv<=2 Beast Effect monsters exist (Nimble Momonga, Tree Otter, Playful Possum, Sea Koala, ...).
- KB: cost.lp_cost_table_0x0226F1A8 + dispatch.shared_deck_multi_ss_resolver_0x0221DA94 (VERIFIED);
  card.obedience_schooled (UNVERIFIED).


## Session 2 (2026-10-01): C3a + C3b + C4 in scope (user: "Continue with C3 and C4")
### Confirmed (disassembly / table dumps, chain ROM rom_all_patches.nds 7ab4355c unless "stock")
- Summon-event prologue (chain): `ldrh r0,[r4,#0x12]` (SOURCE cid), then two INDEPENDENT list searches, no else:
  - 0x02268074: list 0x0228F750/0x2E -> kind-3 node (0x02268086). The bl goes to Norden's NEG_STUB 0x02223490.
  - 0x02268090: list 0x0228F708/0x24 -> kind-2 node (0x022680A4). The bl goes to Petiteranodon's ov5
    CAVE_PTER_NOATK 0x023A1B9C, which also serves the attack check 0x021A4AC6.
- Negate reader 0x021EE402..0x021EE422: walks node pool 0x0229D33C; a node of kind < 6 whose key [node+0] is in
  0x0226FAB4/0x23 means negated (the bl at 0x021EE418 goes to NEG_STUB; a hit returns 1).
- **NATIVE RECIPE.** Level Modulation 0x1944 and Fire Ant Ascator 0x21B7 are in F708 (kind 2) AND in FAB4
  (reader), but NOT in F750. So a kind-2 "summoned by X" node plus reader membership = negated. C3a needs the
  READ list only. The kind-2 node + End-Phase row 0x02254E95 = destroyed (Rescue Cat). Level Modulation has no
  End-Phase row, so the two riders are independent.
- No phantoms are left: F708 is all real in the chain (0x0E2E -> Misc), and FAB4 is all real (0x0E57 -> Tour Guide;
  0x0D65 / 0x2184 / 0x2414 are real cards).
- ov3 free fragments (ledger) are all 2-4 B, so there is no room for a stub there. NEG_STUB (16 B code + 2 literals)
  is packed against Norden's DEST_STUB @0x022234A8.
- **Fresh dead ov3 body:** the donor's native fns 0x0221C954 (RES), 0x021F8514 (COND) and 0x02237D8C (SEL) are
  each referenced ONLY by cls0[554] (pointers @0x02281A40 / 48 / 50; no BL; no ARM9 pointer), so they are dead
  after the rewrite.
  - SEL body = 0x02237D8C..0x02237E53 (0xC8 B). The next fn 0x02237E54 is referenced @0x02281C00. No external
    b/bcc lands inside it, and the chain bytes are stock.
- End-Phase registry 0x0228E1E0 (8-B rows {fn, cid}), End-Phase section rows 63..287.
  - Phantom rows unclaimed in every ledger pool: 133 (0x0E8B), 152 (0x0EA0), 198 (0x1337), 249 (0x0E8C).
  - Chosen: row 249 @0x0228E9A8 {0x02253EC9, 0x0E8C} -> {0x02254E95, 0x17F4}.

### Design C3 (puzzle-safe, ov3)
- ov3 stubs in the dead SEL body:
  - NEGR at 0x021EE418: r0 == 0x17F4 ? 1 : tail-call NEG_STUB.
  - EPL at 0x02268090: r0 == 0x17F4 ? 1 : tail-call CAVE_PTER_NOATK.
- Leave-cleanup 0x021CB3BC, attack check 0x021A4AC6 and write site 0x02268074 stay untouched.
- Row 249 is converted.

### C4 research (2026-10-01)
- No NDS template exists: Remus C3c and Assault Synchron's lock were never built.
- NDS 0x021B9FC0(side, cid, r2 = SOURCE ZONE) is "may cid be placed in side's Monster Zone".
  - It computes r7 = race 0x0202ABB8(cid) and [sp+4] = attribute 0x0202ABC8(cid).
  - Rivalry of Warlords 0x15F6 (race mask) and Gozen Match 0x1EFE (attribute mask) deny inside it via
    0x021AC204(cid on field) -> deny leaf 0x021BA028.
  - It has 9 BL callers: 0x021AF080, 0x021B1D6E, 0x021BA41C, 0x021BA44A, 0x021BA800 (in 0x021BA69C),
    0x021F07FE, 0x02207CDA, 0x0225D81C, 0x0225E5D6.
  - The Normal Summon path 0x0225D81C passes r2 = 0xB (hand) right after 0x021B9E6C, so r2 does NOT tell NS
    from SS. An arm INSIDE 0x021B9FC0 would also block Normal Summons.
- **3DS architecture (code_dec.bin):** the Baby Raccoon Ponpoko 0x29F9 text "cannot Special Summon ... the turn
  you activate this effect, except Beast-Type monsters" is enforced at 0x3922F8, with r6 = side and
  r8 = race:
  - `if race != 0xB && 0x3BCF20(side, 0xB, 0x29F9, 1) -> deny`.
  - Kidmodo 0x28DB has the same shape for race 1 (Dragon) @0x3922AC.
  - Archfiend Emperor 0x298A has an on-field variant @0x3922D4.
  - The lock = a turn-log node (pseudo-zone 0xB, key = card cid, kind 1), posted at activation
    (0x37BB58/0x37BBC8: bl 0x3A1C28(side, 0xB, 2, key)).
  - The same pair appears in 4 functions: 0x340890/0x34098C, 0x37BB64/0x37BBCC, 0x3922AC/0x3922F8,
    0x392AC8/0x392B10.
  - Beast race code = 0xB (matches the criteria word).

- **NDS SS-only, cid-aware gate = 0x021BA258(side r7, cid r5, ref r4, zone r6)** (disasm, stock).
  - It holds Heat Wave 0x23B3's SS arm (key-only 0x021A1430(0, 0xB, 0x23B3) @0x021BA380). That arm is SKIPPED
    when [sp] != 0, which marks non-Effect monsters etc., so it is the wrong seat.
  - The unconditional `bl 0x021BA1E8` (Worm Bait's SS-level check) @0x021BA368 has r5 = cid and r7 = side
    still live (r5 is not rewritten until 0x021BA3B0). That is the hook seat.
  - Normal Summon checks live separately in 0x021AF0A8 (Worm Bait + Heat Wave NS arms), so a hook in
    0x021BA258 cannot block a Normal Summon.
  - Callers of 0x021BA258:
    - the per-candidate SS chain 0x021BA69C;
    - the criteria matcher 0x0223BA24;
    - the hand-SS dispatch 0x0225E51C;
    - 0x021B1BE8, 0x021F072C, 0x02200D50, 0x0220731C, 0x02207A08;
    - wrapper 0x021BA410 (17 caller fns, incl. the Fusion area 0x02233980 and the SS-from-GY resolver 0x02204730);
    - wrapper 0x021BA440 (15 caller fns).
    - Synchro Summon and Token paths are NOT proven to pass through it.
- **Race getter 0x0202ABB8 returns 11 for Beast.**
  - The criteria matcher 0x0223BAEC does `bl 0x0202ABB8 ; cmp word>>27, r0`, so the criteria race field IS that getter.
  - C2 (word race 11) is in-game confirmed to offer only Beasts.
- Lock post = Dragon Shrine / Pot of Duality's cost slot, run once per activation: 0x021D2584(desc[+2], desc[+0] = 0x17F4, 1, 0); return 1.
- Lock query = key-only 0x021A1430(side, 0xB, 0x17F4) (summon.pot_of_duality_ss_lock shape).

### Design C4 (ov3, dead SEL body)
- cls0 +10 COST stub = the post.
- LOCK stub at bl 0x021BA368: r0 = native 0x021BA1E8(r0, r1); if r0 != 0 and 0x021A1430(r7, 0xB, 0x17F4) != 0
  and 0x0202ABB8(r5) != 11 -> 0.

## Build 2 (2026-10-01) -- C3a + C3b + C4 in-game confirmed by user 2026-10-01 (build 2, items 8-16). WHOLE CARD CONFIRMED.
- rom_obedience_schooled.nds sha256 d26dc2e6d4b1d343685887a3cbf578ae23b3a5587d94cef60ab9e47021ab6be8 (same base
  7ab4355c). BUILD_EXIT 0, verify 9/9.
- ov3 stubs in the dead selector body:
  - NEGR 0x02237D8C (0x18): bl @0x021EE418 -> NEGR -> NEG_STUB.
  - EPL 0x02237DA4 (0x18): bl @0x02268090 -> EPL -> CAVE_PTER_NOATK.
  - LOCK 0x02237DBC (0x3C/0x40): bl @0x021BA368 -> LOCK.
  - COST 0x02237DFC (0x18/0x20) = cls0 +10.
- End-Phase row 249 -> {0x02254E95, 0x17F4}.
- Ledger: OV3_DEAD_BLOCKS (0x02237D8C, 200, 0x17F4), 4 OV3_CLAIMS, registry_row 0x0E8C. Emit OK.
- All stubs: odd BLX literals, no pop {..lr}.
- **Lift proven by execution** (scratchpad liftexec.py, thumbemu over the built ROM's ov3 + ov5 + ARM9):
  - NEGR == NEG_STUB for every cid 0..0x27FF (36 old hits) except 0x17F4 -> 1.
  - EPL == CAVE_PTER_NOATK (37 hits) except 0x17F4 -> 1.
- Neighbour verify() on build 2: tour_guide, miscellaneousaurus, ojamassimilation, double_evolution_pill,
  soul_charge, masked_hero_dark_law, ultimate_conductor_tyranno, naturia_pineapple, kuribandit, thunder_sea_horse,
  cardcar_d, dragon_shrine and raiden all PASS.
  - **elder_entity_norden FAILs** "G bl @0x21ee418 -> stub" and **petiteranodon FAILs** "E summon-rider list bl
    @0x02268090 -> stub". Both are exact-target asserts, now fronted by the pre-checks, and the behaviour is proven
    identical above. Their verify() must learn to follow a pre-check before shipping (cross-patch edit -> user's
    call).
- KB VERIFIED: summon.ss_gate_0x021BA258_cid_aware, summon.negate_is_kind2_node_plus_reader_list,
  carddata.race_getter_is_criteria_race.
- UNPROVEN: whether Synchro Summons and Token summons pass through 0x021BA258 (oracle item 11/12 records it).
  LOCK's native callee 0x021BA1E8 is state-dependent, so it was not executed offline.

## Shipped
- SHIPPED 2026-10-01 (steps.STEPS step 87/90 + SHIPPED; EE build 90/90 sha256 78f71a95...489b04cc, ov3+ov5 byte-identical to the tested build 2; sweep 76/0).
- Norden / Petiteranodon verify() now use effect_verify.bl_reaches (direct OR via one exact-shape pre-check whose
  tail literal is the stub). It PASSes on the chain and on build 2; negative controls (wrong stub, non-pre-check
  target) are rejected.

## Open Questions
- ASSUMED (not measured): the candidate buffer slot 0x02299458[0] holds the FIRST survivor right after COUNT
  returns (COND's greedy distinct count relies on it). If COND wrongly refuses activation, this is the first
  suspect -> dump 0x0229944C / 0x02299458 from a savestate.

## Next Experiment
- DONE: items 1-7 in-game confirmed by user 2026-10-01 (oracle items 1-7). The 0x02299458[0] assumption therefore held in practice (items 3 + 6).
- DONE: build 2 items 8-16 in-game confirmed by user 2026-10-01 (build 2, items 8-16) ("All confirmed, ship it"). Shipping to steps.STEPS.
- Then C3a / C3b / C4, one per session.

## CPU never plays it (2026-11-06) -- user report: "the CPU drew and held it but never played it" (Regurus gauntlet)
Measured: data/cpu_gauntlets/2026-11-06_rpg053_8_regurus/card_stats.csv: Obedience Schooled 6132 (=0x17F4) 50 duels, drawn 26, activated 0.
Same deck: Gazelle summoned 51, Berfomet 31, Fabled Ganashia 23 -> the CPU fields monsters almost every turn (card needs NO own monsters).
### Confirmed (this session)
- `cardtest rows` (stock rom.nds AND rom_all_patches.nds, identical): ov5 CPU row 0x02395EEC id 0x3D7F4, evaluator 0x02323D21, shared by 1 row. Unlike Grass (0x0231111D LP evaluator) it was NOT swapped.
- Evaluator 0x02323D20 (Abyssal Designator's own, disassembled from ov5; ctx r0: [+0] u16 cid, [+2] u8 side, [+3] u8 type):
  returns 1 iff  A(ctx)!=0  OR  ( oppMonsters(1-side) != 0  AND  ai[side] >= 0 ).
  - A = 0x023435A4: ctx[+3]==0xE && 0x02022FC8(cid) && 0x0202ABE8(cid)==0 (card-property test, not field state).
  - oppMonsters = 0x021ACF68(p): over 5 slots of base 0x0229AC94 + (p&1)*0xB3C, stride 0x14, counts slots with ([+0x34]&0x3FFF)!=0 and bit21 of [+0x44]==0.
  - ai[side] = 0x023511FC(side) = ldrsh [0x0229DEAC + side*0x1A0 + 0x25F24]; 0x023525D0(v,0) returns 1 iff v<0.
### Ruled Out / not established
- NOT proven a defect: the evaluator can return 1 (opp has a monster, ai>=0). The measured 0 may simply be the card's own cond (control no monsters) never being true, since the CPU deck summons constantly.
- games.jsonl stores per-card counts only; it cannot say whether the CPU's field was ever empty while holding the card.
### Open Questions
- Does the evaluator ever run for this row, and what does it return, at a moment the CPU's own monster zones are empty with the card in hand? (a=empty field never occurred / b=evaluator returned 0 / c=evaluator 1 but cond or cost gate rejects)
### TRACE RESULT (2026-11-06, scratch/obed_trace.py, private melonDS on port 3433 -- user's own instance holds 3333, untouched)
Replayed 5 exact gauntlet duels (seeds from games.jsonl, rig sha fd363748... == the gauntlet's battery_sha256, interpreter + GDB), breakpoint at the evaluator 0x02323D20 + LR return + enqueue 0x021D2FC4 (cid 0x17F4).
Columns: cid, side, type, ownMon, oppMon, ai[side], turnPlayer, phase, RET, count. Outputs: build/cpu_battery/gdb/obed_<opp>_<seed>.json
- wcs063_maji  (side0): ['0x17f4',0,11, own0, opp0, ai 0,     tp0, ph2, RET 0] x2        -> opp has no monster -> 0
- wcs001_moja  (side0): evaluator never called
- wcs090_demise(side1): own0 opp1 ai -1900 RET 0 | own0 opp1 ai -2400 RET 0 x2 | own0 opp2 ai -2400 RET 0 x2
- rtl012       (side1): own0 opp1/2/3, ai -2400/-2800/-1800 -> RET 0 on all 7 calls
- wcs074_o7    (side1): own0 opp1/2, ai -1600/-2500 -> RET 0; own0 opp0 ai0 -> RET 0
- Enqueues of 0x17F4: ZERO in all 5 duels. Evaluator returned 1: NEVER (0 of ~20 calls).
### Confirmed (proof = the trace above)
- The CPU's own field WAS empty (ownMon=0) when the evaluator ran, i.e. the card's "control no monsters" cond is satisfiable in these duels.
- The donor evaluator returns 0 in exactly those states: with oppMon>=1 the ai[side] term is NEGATIVE (-1600..-2800) so `ai>=0` fails; with oppMon=0 the opp-monster term fails. => candidate cause (a)/(c) of the open question is ruled out; the evaluator IS a blocker (b).
- ai[side] = ldrsh [0x0229DEAC+side*0x1A0+0x25F24]: what it measures is UNVERIFIED (negative whenever the CPU has no monsters and the opp has some, so plausibly an AI board/threat score).
### Fix A/B (2026-11-06, scratch/obed_fix_e2e.py; scratch copy rom_all_patches_obedfix.nds, NO module/chain edit)
- Row 0x02395EEC evaluator word 0x02323D21 -> 0x023107C1, rig sha256 98a240c2..., replay of the SAME duel wcs090_demise seed 3881114246 side1:
  baseline = 0 enqueues of 0x17F4; fixed = 1 enqueue (r1=0x800717f4, lr=0x21d3407). Evaluator no longer called (as expected).
- Side effects: the duel diverges after the first play (lp [0,7900] vs the baseline), as it must. NOT measured: activated count over a gauntlet, resolution success.
- APPLIED 2026-11-06 in otn_enhanced/cards/obedience_schooled.py (_patch_ai_row + verify); combined ROM rom_obed_cpufix.nds sha256 08bf8380...c07c, sweep 115/1 (the 1 = data.bulk_ydcs wcs084_formula, fails identically on the old rom_all_patches.nds).
- CPU-play fix in-game confirmed by user 2026-11-06 ("okay it works now, thanks"; scope: the CPU now plays the card in the test the user ran; exact test not stated).
### Was "Not yet shown" (now answered above)
- That swapping the row's evaluator to 0x023107C1 (Grass fix) makes the CPU enqueue the card: after the evaluator, the card's own cond/cost gates still run. Next: scratch copy of rom_all_patches.nds with the word at 0x02395EF0 changed, rig, replay wcs090_demise -> expect enqueues of 0x17F4 (same pattern as scratch/grass_fix_e2e.py). No module/chain edit until the user approves.
