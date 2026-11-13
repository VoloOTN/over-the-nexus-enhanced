# Escalation of the Monarchs (donor Enervating Mist 0x1800) — findings (2026-11-12, user away, autonomous)

Status: BUILT as a test ROM (`rom_monarch_erebus.nds` sha256 ce5b82868653049cce32d4e274137a62e6505a4392d1affba229b826a48bb845, 22 modules). NOT shipped, NOT traced, nothing user-confirmed. **AWAITING IN-GAME TEST.**

Text (scratch/ygoprodeck_cache.json): "Once per turn, during your opponent's Main Phase or your opponent's Battle Phase, you can: Immediately after this effect resolves, Tribute Summon 1 monster." Continuous Trap.

## Confirmed (static, this session)
- Cry Havoc! 0x1D35 is a Continuous Trap whose cls3 record {+04 0x0220D80D, +0C 0x021FD73D, +10 0x021E5319 (GY banish)} resolves with a native "Normal Summon from the hand as an effect" machine: phases 0x80 (gates 0x021B9E6C / 0x021B9DAC, candidate count, prompt 0x27) -> 0x7E/0x7F (hand picker 0x0224B9C8(desc, predicate)) -> the standard summon state machine (0x02261444 / 0x0224B1FC), which owns the Tribute selection.
- The resolver asks `0x0220D7B4(acting cid)` (call at 0x0220D81C) for a per-cid hand predicate r7(side, zone, idx) -> mask; a candidate counts when `0x0225D6D4(side, ref) & mask` != 0 (0x0225D6D4 returns 0x10 = can be Summoned, tributes included). With r7 = 0 every legal Normal Summon/Set counts. The zone loop calls r7(side, 0..4, 0): returning 0 there restricts the choice to the hand.
- In the chain ROM the site 0x0220D81C already calls a cave3 front at 0x021F0FD8 (Sakitama's), not the native function; the other two callers (0x02200BF2, 0x02222488) are untouched natives and serve other cards' paths. Escalation fronts ONLY 0x0220D81C, tail = 0x021F0FD8.
- Phase numbering from this session's CPU traces: Main = 2, End = 5 (Battle 3, Main 2 = 4 inferred).
- cls0/cls3 phantoms were free (0x0E71 / 0x152C); donor_scan(0x1800) CLEAN (records-free Continuous Trap); 0x1800 joins tenacity.MONARCH (13 of 24 slots).

## Built
- cls0 {RES tiny, 0, ALWAYS, COST tiny, 0} over phantom 0x0E71 (Erupt's shape); cls3 {0x0220D80D, 0, ES_COND, ES_COST, 0} over phantom 0x152C; ES_PRED (hand monster Level >= 5 -> 0x10); ES_COND (opponent's turn, phase 2..4, OPT unused, a hand Level 5+ monster with 0x0225D6D5(side, ref) & 0x10); ES_COST stamps the OPT node; slots CAVE_EC_* 0x023B3990..0x023B3B50 (0x1D0 B free after).
- Sweep: escalation PASS; known-fail set unchanged.

## Open Questions / UNPROVEN
1. Does the cls3 effect of a Continuous Trap get OFFERED in the opponent's Main/Battle Phase (spell speed of a cls3 record on a Trap; the offer path for cls3 on the opponent's turn)? Cry Havoc!'s own offer path is cond 0x021FD73D.
2. Does the summon legality (0x0225D6D4 / 0x0225D73C and the gates 0x021B9E6C / 0x021B9DAC) allow a Summon on the opponent's turn? No turn-player test was found in 0x0225D73C, but the 0x021B9709 gate chain was not read to the end.
3. Whether the effect-summon consumes anything it shouldn't, and whether the Tribute selection UI runs on the opponent's turn.
4. Phase numbers 3 (Battle) and 4 (Main 2).
## Ruled Out
(none)
## Next Experiment
- User test: Set Escalation, Set/hold a Level 5+ monster with enough Tributes, pass to the opponent's Main Phase / Battle Phase: the effect should be offered once per turn; on activation choose the monster and Tributes. If it is never offered, trace 0x0220D80D / ES_COND with GDB in a puzzle or duel.
- Ehther's E2 (Quick Effect from hand) could reuse ES_PRED's mechanism with the predicate keyed on cid 0x1312 (needs hand list B / speed-2 list slots: both lists have no free phantom left).

## CPU TRACE (2026-11-12; build/cpu_battery/gdb_eb/eb_*.json from scratch/erebus_gdb.py with EB_CID=0x1800; 12 cardtest seeds, kit Caius/Raiza/Zaborg/Granmarg x3 + March x2; ROM ce5b8286...; emulator CPU, NOT user-confirmed)
- cardtest mirror: Escalation drawn 23 / summoned 0 / activated 39 in 12 duels, no hang. The stock CPU row for 0x1800 (id 0x3D800, always-true evaluator 0x023107C1) already existed, so the CPU Sets/activates it and also USES the cls3 effect.
- CONFIRMED (CPU): in 10 of 12 seeds the cls3 effect was activated on the OPPONENT's turn: ECOST (our cost) with controller != turn player, at phase 2 (Main 1) and phase 3 (Battle) (seed 0: tp 0 ph 2 ctrl 1; tp 1 ph 3 ctrl 0 twice; seed 4: tp 0 ph 2 and ph 3 ctrl 1). Cry Havoc!'s resolver 0x0220D80C then ran phases 0x80 -> 0x7F -> 0x7E -> 0x7D and the engine paid Tributes through 0x021CF68C (TRIBPAY player = controller, e.g. mask 0x40000/0x80000/0x4/0x8) and the controller's hand lost a Level 5+ monster (seed 0: Zaborg 0x174D left the hand, the Tributed monster went to the GY: GY 0 -> 1). So the offer path, the summon legality and the Tribute Summon all work on the opponent's turn for the CPU, and ES_PRED/ES_COND ran thousands of times without a fault.
- Once per turn: ECOST hit 1-3 times per duel, never twice in one turn in the logs read (seed 0: three ECOSTs on three different turn-phases).
- Phase numbers: 2 = Main 1, 3 = Battle confirmed by the activations (COND only allows 2..4). Main 2 (4) not seen.
- STILL UNPROVEN: the human UI path (hand picker + Tribute selection UI on the opponent's turn); that the monster is only ever Tribute Summoned (CPU masks show Tributes were paid; Level < 5 candidates are excluded by ES_PRED); Main Phase 2.
