# Restoration of the Monarchs (Equip Spell) on Burning Spear 0x12EE -- live findings (2026-11-11)

Text (scratch/ygoprodeck_cache.json): "Activate this card by targeting 1 monster in your GY with 2400 ATK/1000 DEF, or 2800 ATK/1000 DEF; Special Summon it in Defense Position, but negate its effects, also equip it with this card. When this card leaves the field, destroy that monster. The equipped monster can be treated as 2 Tributes for a Tribute Summon. You can only activate 1 "Restoration of the Monarchs" per turn."
Clauses: C1 target a GY monster 2400/1000 or 2800/1000; C2 SS it in DEFENSE, effects negated; C3 equip it with this card; C4 this card leaves -> destroy that monster; C5 equipped monster = 2 Tributes; C6 OPT.
Donor Burning Spear 0x12EE approved by user 2026-11-10 ("Approve revised donors"); not in any ROM deck (Session 19).

## Confirmed (static, this session; NOT in-game)
- 0x02207528 (Premature Burial family resolver) is cls0 +04 of PB 0x1366: cls0[242] = {0x1366, 0x02207529, 0, 0x021F03B5 (cond), 0x021E4D81 (cost: LP), 0x02235605}. Disassembled this session: phase 0x80 switch picks r4 (0 Attack, 1 Defense = Soul Resurrection 0x17B7, default 2 = player chooses) then `bl 0x02204730(desc,1,r4)` @0x022075D2; phase 0x7F: for card_prop type 3 (Equip) it calls 0x021C4A5C = the EQUIP LINK, so an Equip donor equips the summoned monster (KB fusion_material).
- GY "Special Summon" criteria thunk with a SET-CODE predicate = 0x0223C9ED (flags 8, predicate 0x0223C825, aux = row+2 -> [sp+8]); plain = 0x0223C9D1 (PB row {0x1366,0xFFFF,0x0223C9D1,0x00010002}). Set code 0x6C = Tenacity's reveal list (22 cids printed 2400/1000 or 2800/1000) -> reuse as the GY filter.
- Negate = KB summon.negate_is_kind2_node_plus_reader_list (VERIFIED): source cid in list 0x0228F708 (bl @0x02268090) posts a kind-2 node; reader list 0x0226FAB4 (bl @0x021EE418) negates. Chain ROM heads now: 0x021EE418 -> 0x023AAC30, 0x02268090 -> 0x023AAC50 (ov5 prechecks of later cards): add a front ahead (Obedience precheck shape: cid == 0x12EE ? 1 : tail).
- Leave list 0x0226E940 is FULL (KB, Norden notes): no phantom left -> needs a front on its search bl @0x021CB3BC (precheck shape) -- UNVERIFIED current chain head, check.
- Burning Spear's only code reference = equip ATK/DEF row[31] @0x0226E06A -> its stat bonus must be zeroed.

## Ruled Out
(nothing yet)

## Open Questions
- Does 0x02204730 pass the SOURCE cid so the 0x02268090 prologue posts the negate node for 0x12EE? (UNPROVEN; Obedience/Level Modulation precedent says the source is the Spell cid.)
- Chain head of 0x021CB3BC; double-Tribute site 0x021AE148 front (Mega Monarch M0?) and how to key it on the equip link.

## Next Experiment
Build rom_restoration.nds on the chain + Tenacity's 0x6C list; trace with GDB: resolver 0x02207528 phase 0x80 r4, negate node posted, link made, leave-destroy.

## Session 25 update (2026-11-11) -- BUILT as a test ROM, AWAITING IN-GAME TEST, NOT YET TRACED
- Findings corrected: Burning Spear owns NO cls0 record (only equip stat row[32] @0x0226E070 = (0x12EE, +400, -200)); cls0 row inserted over free cls0 phantom 0x0E2B. Chain heads: leave search bl @0x021CB3BC and kind-3 summon poster bl @0x02268074 both -> 0x02223490 (Norden's shared stub); negate reader bl @0x021EE418 -> 0x023AAC30.
- NEGATE DURATION: kind-2 nodes (summon poster 0x02268090) are freed at the END OF THE TURN (rider.turn_sweeper); kind-3 nodes survive every sweep (freed only for keys 0x18D9 / 0x1F6A) and the reader honours any node of kind < 6 keyed in 0x0226FAB4 -> Restoration uses the kind-3 poster (0x02268074), NOT 0x02268090 (Obedience's end-of-turn recipe).
- Built: cards/restoration.py + cards/c/restoration.c + _build_restoration.py; data/over_the_nexus/working/rom_restoration.nds sha256 343395f38e77b861cd39557e72399436c82524dcacf904ed98b68e6e326a906d, verify 38/38 static. Slots CAVE_RS_* (CAVE_FREE 0x023B08D8), TRIB leaf in the hole 0x023B0380. Ledger: donor 0x12EE, cls0 phantom 0x0E2B. Built stubs disassembled (POS, PREA, H2, TRIBW) -- Thumb-1, correct.
- UNPROVEN (needs trace): resolver phase-0x80 reaches POS with desc cid 0x12EE and r2 = 1; the summon prologue's [r4+0x12] is the Spell cid so the kind-3 node posts; negation takes (zone flag bit 6); equip link made; leave-destroy fires; TRIB hit for the equipped monster; H2/H3 virtual row returns GY candidates; CPU plays the card (cardtest rows/mirror not run yet).
- Composition notes: front chains for H2/H3 (ahead of Block Dragon's, like Tenacity/Return), 0x021AE14A (Mega Monarch M0 site), PREA/PREB chain heads are chain-ROM-specific; a combined ROM with other Monarch cards needs them chained. Set code 0x6C shared with Tenacity (same group object).

## Session 25b: CPU evidence (2026-11-11; emulator, one emulator; NOT user-confirmed)
- cardtest rows 0x12EE: no ov5 CPU row. Same for Premature Burial 0x1366 and Soul Resurrection 0x17B7 (the equip-style GY revive class has no CPU row), so the CPU never offers it: mirror (12 duels, Monarchs x3 each + Dark Hole x3 + filler) drawn 20 / summoned 0 / activated 0, and the GDB trace (scratch/restoration_gdb.py, build/cpu_battery/gdb_rs1/rs_1..6.json, 6 seeds) never entered COND, COST or the resolver. This is the card class, NOT shown to be a patch defect; it also means NO CPU trace of C1-C4 is possible without adding an ov5 CPU row (not done).
- What the trace DID show: the TRIBW double-Tribute front (0x023B08A8) was entered 8-20x per seed during CPU Tribute Summons with r0 = player, r2 = side, no freeze/crash, and the duels completed. The leaf's TRUE branch (equipped monster) was NOT exercised (no Restoration ever on the field).
- Everything in "UNPROVEN" above still stands. Next experiment = the user's in-game test (below), or give the CPU a row (one 8 B row, evaluator 0x023107C1) to trace.
- In-game steps (user is the oracle): Deck: Restoration x3, 2400/1000 or 2800/1000 monsters (Zaborg, Mobius, Caius, Raiza...), a way to fill the GY (Foolish Burial-style / Dark Hole), a Level 5-6 and a Level 7+ monster. Checks: (1) activatable only with a legal monster in your GY; prompt lists only 2400/1000 or 2800/1000 monsters; (2) it comes up in DEFENSE Position, effects negated (try a flip/trigger effect); (3) it is equipped with Restoration, ATK/DEF unchanged (no +400/-200); (4) destroy/remove Restoration -> the monster is destroyed; (5) the equipped monster pays 2 Tributes for a Level 7+ Tribute Summon; (6) a second Restoration the same turn is refused; (7) Burning Spear's old equip effect is gone; (8) the negation persists past the End Phase.

## Session 25c: CPU row added + trace #2 (2026-11-11; emulator CPU, ONE emulator; build/cpu_battery/gdb_rs2/rs_1..6.json; NOT user-confirmed)
- CPU row: ov5 phantom row 0x0239292C (cid 0x1695, card-less) repurposed to {0x3D2EE, 0x023107C1} in restoration.py (_patch_ai_row, Grass recipe). rom_restoration.nds sha256 1cac05963db9915bb6b1fbc2c50066c31026315996afc8fb75c2bdb6932529ed, verify() 38/38 + the row check. Mirror (12 duels, Monarchs x3 each + Dark Hole x3): drawn 19 / summoned 0 / activated 13 -> the CPU plays it.
- CONFIRMED by CPU trace, 5 of 6 seeds (side 0 and side 1 both): COND (menu) -> COST -> PB resolver 0x02207528 phases 0x80 -> 0x7F -> 0x64 for cid 0x12EE.
  * Defense front: the breakpoint after the POS stub's `movs r2,#1` saw r2 == 1 on every activation.
  * Kind-3 summon poster precheck (PREA @0x02268074, LR 0x02268079) entered with r0 = 0x12EE (r2 = 0x2E count) between phase 0x80 and 0x7F.
  * The SS'd monster (cids 0x1D5C Caius, 0x174D Zaborg, 0x1BCD Raiza, 0x17E2 Mobius) carries a node {key 0x12EE, kind 3, dur 0, param 0} that SURVIVES the whole resolution = the negate node (reader keyed by PREB not yet shown to act).
  * At phase 0x64 the monster's zone gains a node {key 0x700/0x701/0x800, kind 10 (0xA)}: key = locator of Restoration's own S/T zone (side 0 zone 7 = 0x700, side 1 zone 7 = 0x701, side 0 zone 8 = 0x800) = the EQUIP LINK. Restoration stays face-up in S/T.
- STILL UNPROVEN: the monster is actually in DEFENSE Position; its effects are actually negated (reader PREB result / zone flag bit 6); leave-destroy fires (PREA at the leave bl 0x021CB3BC was entered twice after RES_END with r0 = 0x12EE, outcome not recorded); TRIB leaf TRUE branch; OPT second-use refusal; negation persists past the End Phase.

## Session 25d: trace #3 + #4 (2026-11-11; emulator CPU, one emulator; build/cpu_battery/gdb_rs3, gdb_rs4; NOT user-confirmed)
- CONFIRMED by CPU trace (raw zone records, 6 + 8 seeds): the Special Summoned monster's zone record has +6 (position, ram.zone_record layout in ram_layout.yaml) = 1 while Attack-Position monsters read 0 -> DEFENSE; its +0x10 flag word goes 0x...10 -> 0x...50 (bit 6) after the PREB negate-reader polls (cw label `negate_test`: negation rebuild 0x021EF808 sets slot flag bit 6; third-party label, so STRONG not conclusive); kind-3 node {0x12EE} present throughout. The equip link (kind 10, key = Restoration's zone locator) appears at phase 0x64 as before.
- NOT EXERCISED in 8 more seeds (deck + Mystical Space Typhoon x3, Heavy Storm x2, Dark Magician x3): leave-destroy (the leave-list precheck fired only right after the resolver, monster still on the field), the TRIB leaf TRUE branch (no TRIB_HIT), OPT refusal. The CPU never removed Restoration nor Tribute Summoned with the equipped monster in these windows.
- Remaining checks are the user's in-game steps (list in Session 25b); the unproven ones are leave-destroy, counts-as-2, OPT refusal, negation persisting past the End Phase, and the human-facing prompt.
