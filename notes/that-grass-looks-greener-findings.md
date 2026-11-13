# That Grass Looks Greener — findings

Text (scratch/ygoprodeck_cache.json id 11110587, Normal Spell):
"If you have more cards in your Deck than your opponent does: Send cards from the top of your
Deck to the Graveyard so you have the same number of cards in the Deck as your opponent."

- C1 condition: my Deck > opp Deck. C2: mill (mine - theirs). User ruling 2026-10-01: recheck at
  resolution, diff <= 0 -> mill 0. Scope C1+C2 together. Donor (user choice): Sparks 0x10FD.
- Status: whole card in-game confirmed by user 2026-10-01 (items 1-5); SHIPPED 2026-10-01
  (steps 86/89, chain sha256 7ab4355c...694ea65fe == tested ROM, sweep 75/0).

## Confirmed (2026-10-01, disassembly of committed ov3/arm9)
- 3DS build does not ship the card (`"Grass Looks"` absent from CARD_Name_E.bin).
- Template Needlebug Nest 0x1E59: cls0[983] @0x02284274 = {0x1E59, 0x0222983D, 0, 0x021FEB75, 0, 0}.
  Resolver 0x0222983C: `ldrb r1,[r0,#2]; movs r2,#5; bl 0x021D2148; movs r0,#0; pop`.
  Condition 0x021FEB74: `bl 0x021BA9AC(desc[2])` (Dimension Fortress Weapon 0x1F5C gate), then
  `ldr r1,=0x0229ACA4; ldr r1,[r1,(side&1)*0xB3C]; cmp r1,#5; bhs ok`.
- Deck count = player+0x10 = 0x0229ACA4 + (side&1)*0xB3C: decremented in Deck-remove 0x021A7C94,
  incremented (cap 0x78) in 0x021A7A90, and 0x021D2094 clamps the mill N to it
  (`ldr r1,[0x0229ACA4+..]; cmp r0,r1; blo`). => a negative N (unsigned huge) mills the WHOLE Deck.
- Sparks 0x10FD cls0[111] @0x0227F0B4 = {0x10FD, 0x02206139, 0, 0, 0, 0} (shared LP resolver).
- u16 sweep for 0x10FD: arm9 0 hits; ov3 8 hits:
  - 0x0227F0B4 own cls0 record.
  - 0x022702B0 row {0x10FD, -200} of the fixed-LP-amount table 0x02270260; the table's ONLY literal
    reader is 0x02204D38 (inside LP-change resolver 0x02204D08) -> dead once cls0 +04 is retargeted.
  - 0x021804B0 literal used at 0x0217FB28: ARM switch fn 0x0217F53C (~0xC4 cases; also tests
    Obelisk/Uria/Dreadroot/Avatar/Skull Servant) `ldr r1,[r5,#0xD8]; cmp r1,0x10FD; moveq r0,sb` —
    read-only predicate, looks like a duel-record/bonus condition. ASSUMED harmless (user approved plan).
  - 0x0218C4F4 ARM code bytes; 0x02279E70/88, 0x0227EAA8/C0 are pointer words 0x021F10FD. Coincidental.

## Built (2026-10-01) — in-game confirmed by user 2026-10-01
- patch_that_grass_looks_greener: cls0[111] -> {0x10FD, 0x023A3F71, 0, 0x023A3F31, 0, 0};
  CAVE_TGLG_COND 0x023A3F30 (60 B), CAVE_TGLG_RES 0x023A3F70 (56 B); stubs disassembled, pool literals
  0x021BA9AD / 0x021D2149 odd (both callees reached by Thumb BL natively), POP {r4,pc}.
  thumb_asm has no unsigned branches -> signed `ble` (counts 0..0x78, exact).
- _build_that_grass_looks_greener.py on rom_all_patches.nds (e55b608f...efef973da): BUILD_EXIT=0,
  verify 3/3 PASS, out sha256 7ab4355cf9aea685f0e93cd64ab26d927b859fd4dc52407aab1c016694ea65fe.
- KB: ram.deck_count_player_0x10, cards.needlebug_nest_self_mill_template,
  lp.fixed_amount_table_0x02270260 (VERIFIED), card.that_grass_looks_greener (UNVERIFIED). 545/0/68.

## Ruled Out
- Criteria registry 0x022713C4 / cost / registry rows: Needlebug ships with none; not needed.

## Open Questions
- Purpose of switch fn 0x0217F53C (bonus/record evaluator?) — not needed for this card.

## 2026-11-04 report: "not getting played at all" by the AI (UNVERIFIED, nothing proven yet)
- Shipped patch (cards/that_grass_looks_greener.py) only retargets the donor's cls0 record
  {RES, 0, COND}; no AI-side registration was added. Leads not yet read: per-cid AI switch
  0x022393CC and AI list block ending 0x02271218 (effect_dispatch_tables.yaml ~L3739-3764),
  docs/cpu-battery.md, CardWorkshop SDK AI hints (docs/SETUP.md references it).
- Next: find how a comparable self-mill/draw Spell is made AI-playable (grep shipped patches for
  the AI list), then check whether Sparks 0x10FD sits in an AI list with the OLD (burn) behaviour.

- Read this session (from notes/dueling-ai-findings.md, rounds 14b/14e): the main-phase AI is keyed on
  action LEGALITY, not card identity (8 of 9 observed live plays are in no AI list). So a donor card
  with a working COND is normally proposable by the generic path. AI lists (0x0227113C/62/8C/B8,
  rule table 0x02275510) cover only reactive/chain play; ai_tables.py relocates/extends them
  (NOT wired into STEPS, not in-game tested).
- CardWorkshop hints (tools/engine/labels_wc2011.txt L124-125,185-187): ov5 has a SEPARATE CPU row
  list: ai_row_count 0x023358AC / ai_row_at 0x023359C0 (row = u32 id|loc<<14|param<<18, eval) and
  ai_try_row 0x02346F2C -- stock chain/no-link driver 0x0233BFEC. Its role for MAIN-phase Spells is
  UNPROVEN. Its docs (GUIDE/DEVELOPMENT) have no AI-card guidance.
- CPU battery 2026-11-03: card_stats(.by_deck).csv has NO row for That Grass Looks Greener (cid 4349
  decimal) although it is listed in ydc_decks.py (rpg046_8_glaton ...) -- the Glaton deck's 36 rows
  omit it. Likely the battery ROM/deck.pac predates the deck edit (ydc_decks.py is uncommitted), so
  "never played" may just be "never in a tested deck". UNVERIFIED -- check meta.json ROM sha/mtime.

## 2026-11-04 gauntlet evidence (user report: "The card was definetly drawn in 100 duels")
- data/cpu_gauntlets/2026-11-04_rpg046_8_glaton (battery sha 388cdff3..., source rom_all_patches d661dce5...):
  That Grass Looks Greener cid 4349: duels 99, drawn 60, summoned 0, activated 0. CONFIRMED from card_stats.csv.
- Ruled out: "stats don't count Spells" -- same run: Gold Sarcophagus drawn 61/activated 62, Solar Recharge 54/41,
  Reinforcement of the Army 23/23, Monster Reborn 21/14. Deck-based no-target Normal Spells ARE activated.
- Ruled out: "never in a tested deck" (my earlier guess, wrong).
- games.jsonl deck_left (END of game, not at the Main Phase): Glaton side had more cards than the opponent in
  53/99 games, so COND was plausibly true at times. NOT proof -- the instant of the AI's Main Phase is unmeasured.
- Open: (A) COND never true at the AI's Main Phase (e.g. turn-player draw makes own < opp), or (B) COND true but
  the AI never proposes it (its COND runs in an AI-only context where desc[2] / side differs).
- Distinguishing experiment (one-shot GDB or savestate+scratch/thumbemu.py): savestate at the AI's Main Phase with
  Grass in hand and AI deck > opp deck; run COND 0x023A3F31 on it. True -> (B), break 0x021D2FC4 for cid 0x10FD.

## 2026-11-04 GDB session (scratch/grass_gdb.py; battery.nds sha 388cdff3, melonDS interpreter+GDB, Glaton vs rpg020_4_kazuhiro)
- Seeds #1, #2: Grass not drawn, 0 COND calls. Seed #3 (build/cpu_battery/gdb/grass_rpg020_4_kazuhiro_3.json):
  Grass drawn 1, activated 0. MEASURED: cls0 record for 0x10FD is {0x10FD, RES 0x023A3F71, 0, COND 0x023A3F31, 0, 0}
  (read from battery.nds ov3 0x0227F0B4). COND 0x023A3F30 called 31 times, ALL from lr 0x0224AE13,
  desc[2]=0 (Glaton's seat), Deck counts [54,35]..[36,30] (Glaton larger every time), phases 2 and 4,
  EVERY return = 1. ENQUEUE 0x021D2FC4 with r1&0xFFFF==0x10FD: ZERO hits.
- => Hypothesis (A) "COND false on the AI's turn" is RULED OUT for this duel; it is (B'): the engine's legality
  check passes (so the card is legal) and the AI still never proposes/enqueues it. (Caveat: the enqueue filter
  assumed cid = r1 low16 per dueling-ai-findings round 11; it was not validated against another card this run.)
- 0x0224AE12 is `blx r2` of record+0xC (COND) inside a generic cls0 condition wrapper (0x0224ADA0.., r5=desc,
  r4=record); on r6==1 it then tests record+8 (=0 for us) and returns 1. Which loop calls this wrapper (human
  menu scan vs AI proposer) is UNPROVEN.

## 2026-11-04 GDB session 2 (scratch/grass_gdb2.py, same seed #3; build/cpu_battery/gdb/grass2_rpg020_4_kazuhiro_3.json)
- Breakpoints: 0x0224AE10 (before `blx r2` = record COND in the generic cond wrapper) and enqueue 0x021D2FC4,
  each logged with a stack-derived call chain. MEASURED:
  - Every card that WAS enqueued shows its cond called on TWO paths: (1) the SCAN path
    ['0x21edc0b','0x21ecb83'] (also 0x21edc91/0x21edc65 variants) and (2) the PROPOSE path
    ['0x21d33a9','0x224b321','0x219dbf9','0x219d385',...] = packer 0x021D32A0 (cond call at 0x021D33A4) <-
    0x0224B2F6..0x0224B31C (calls 0x021D32A0 with the move word built from [ctx+0x64]=cid,[ctx+0x68]) <- 0x0219DBF8.
    Gold Sarcophagus 0x1811: scan 1x + propose 1x, enqueued (r1=0x00071811). 0x1dc9 and 0x142a likewise.
  - Grass 0x10FD: scan path 31x (all return 1, see session 1), propose path 0x. Never reached the proposer.
- => The legality SCAN works and says "legal". The break is the CHOOSER that picks which scanned candidate is
  stored into the proposer's input (AI ctx 0x0229ABFC+0x64 per the move-word build at 0x0224B2FA) -- Grass is
  never picked. Stores `str rX,[rY,#0x64]` in the AI region: 0x02239250, 0x0223A0D4, 0x0223A190, 0x0223A22A,
  0x0223A25A, 0x0224B0EC (static scan, base register NOT checked -> candidates only, UNVERIFIED).
- Not yet known: what makes the chooser accept 0x1811/0x1dc9/0x142a and skip 0x10FD (candidate scoring? a
  per-card "wants" list? the cid appearing in a gauntlet-eligible class?). 0x1811 = Gold Sarcophagus cls0 cond
  is 0x021F0BDD (same family as Dimensional/other no-target Spells); Grass cond is the ov5 stub.

## 2026-11-04 session 3 -- INCONCLUSIVE (scratch/grass_gdb3.py, grass3_*.json)
- Logged AI ctx 0x0229ABFC fields at 0x0219DB04 (entry) and 0x0224B2F6 (pack step). 0x0219DB04 is a command-kind
  switch on [ctx+0x6C] (jump table, kinds 0..0xA) calling 0x0224B1D8/0x0224B1FC/0x0224B224/0x0224B184/0x0224B380/
  0x02261444/0x0224B094/0x0224B590; it runs thousands of times (3136 hits) with [ctx+0x64]==0 almost always, so it
  is the per-frame command EXECUTOR, not the chooser. My field decoding of that dump was off; discard its columns.
- 0x0219EB08 (the 0x0219ED3C enqueue caller) is a duel-command-stream replay switch (opcode via [..]),
  not the chooser either. 0x0224B094 = zone-record activation helper (stores Speed World cid into ctx+0x64).
- The chooser is still NOT found. Scan-path callers 0x021ECB82 / 0x021EDC0A (call chain of Grass's 31 COND calls)
  are the next thing to read: what do they do with COND==1 (build a candidate list? filter by record+8
  criteria / a class?) -- Gold Sarcophagus gets through, Grass does not.

- RULED OUT (record shape): Gold Sarcophagus cls0 @0x02281BA4 = {0x1811, RES 0x0221CD29, 0, COND 0x021F0BDD, 0, 0}
  -- the same {RES, 0, COND, 0, 0} shape as Grass @0x0227F0B4 {0x10FD, 0x023A3F71, 0, 0x023A3F31, 0, 0}.
  (0x1811 also has a second record @0x0228EAFC; 0x1dc9 has +0x10 set, 0x142a has +8 set.) So the missing
  field is not in the cls0 record.
- RULED OUT (cave RES/COND blocks the AI): tournament 2026-11-03 card_stats show shipped Normal Spells with
  cave code ARE activated by the AI: Brilliant Fusion drawn 9/activated 13, Sekka's Light 8/4, Double Evolution
  Pill 7/3. => ov5 residency of RES/COND is not the blocker.
- RULED OUT ("AI never mills"): tournament card_stats: Needlebug Nest (the self-mill template, stock, cond =
  DFW gate + Deck>=5) drawn 12 / activated 13 over 24 duels. The AI does play a self-mill Spell with the same record
  shape. So the gate is specific to what Grass's COND/RES do or to a per-cid/class list Needlebug is in.
- Remaining differences to test: Grass is a SELF-MILL with no target, deck-size condition -- the scan consumer may
  rank/filter candidates (cheapest: compare against Needlebug Nest 0x1E59, the template, is it ever activated?).

## 2026-11-04 LIVE-PATCH BISECT (scratch/grass_gdb4.py variant both; grass4_both_*.json)
- Over GDB write_mem on the first stop of seed #3: Grass's cls0 record COND (+0xC) := Needlebug's 0x021FEB75 AND
  RES (+4) := Needlebug's 0x0222983D. Logged cond fn for 0x10FD confirms 0x021FEB75 (patch applied).
  RESULT: grass enqueues = 0, cond calls = 31, hits 534 / 76 / 12 keys -- identical to the unpatched run.
  => the missing play is NOT caused by Grass's COND or RES code. RULED OUT.
- cid-literal scan of arm9 + every ov (aligned u16 0x10FD): only ov3 {0x021804B0, 0x0218C4F4, 0x022702B0,
  0x02279E40/58, 0x0227EA90/A8, 0x0227F0B4} and ov5 0x0234E7B4. ov5 0x0234E7B4 is a literal 0x10FD ORed into a
  word inside the attack-AI function around 0x0234E5xx (a constant, not a cid test) -- UNVERIFIED as incidental.
  The ov3 0x02279E40/58 and 0x0227EA90/A8 are 0x021F10FD pointer words (incidental, as noted 2026-10-01).
- card_prop (carddb): Grass frame 13 attr 8 race 23 genre 1<<37 -- identical to played Normal Spell Solar Recharge
  (genre 1<<37|4). genre/frame do not separate Grass from played Spells either.
- 0x021ED..0x021EDCA2 (scan path 0x021EDC0B) is the generic activation-legality check with temporary zone
  mutations (0x224AD94 = wrapper); not the chooser.
- STILL OPEN: what separates cid 0x10FD from played no-target Spells. Not the cls0 record, not COND/RES, not a
  cid-keyed ov3/arm9 table, not frame/genre. Remaining: ov5 AI (0x0234E5xx..., ai_row lists 0x023358AC) and the
  per-card selection step; or the card never reaches the AI's hand-scan because the proposer only walks cards
  whose [zone record] flags/ATK-DEF fields ... (guess, UNVERIFIED).

## 2026-11-04 more live-patch bisects (scratch/grass_gdb4.py variants; seed #3 replays identically, 534 hits each)
All with Grass drawn on seed #3; result each time: grass enqueues = 0, cond calls = 31. RULED OUT as the cause:
- `sparks`: zeroed 0x021804B0 (cid literal in 0x0217F53C) and the LP-table row cid @0x022702B0 (Sparks leftovers).
- `lists`: inserted 0x10FD (sorted, in place) into the six ov5 cid lists that contain played cards (0x02397602 x23,
  0x02397A50 x34, 0x02397B78 x41, 0x02398680 x125, 0x02398878 x248, 0x02398B54 x22). NOTE: write success not
  separately verified -- treat as WEAKLY ruled out.
- `row`: ov5 CPU row table. FOUND: u32 rows {id|loc<<14|param<<18, handler} where the id word is 0x3D000+cid&0x3FFF
  style: Grass keeps Sparks' row @0x02392A6C = {0x0003D0FD, handler 0x0231111D} (same handler as the preceding row
  0x3D2E9); Gold 0x23946DC {0x3D811, 0x02310889}, Dark Hole 0x2391F04/0x239294C {0x3D0F6, 0x02319A7D}, Solar
  0x2394BAC {0x3DDC9, 0x0232B7B1}, Needlebug 0x2393E04 {0x3DE59, 0x0232C479}, Charge 0x23968C4 {0x3DEE4,
  0x02311331}, 0x142A 0x23928E4 {0x3D42A, 0x0231D849}. Live-wrote Grass's handler := 0x0232C479 -> no change.
  These rows are for the answer-window/chain driver (CardWorkshop ai_row_*), so this is not the main-phase chooser.
- MEASURED: legality (0x021EDC0A result) = 1 for Grass 31x; Gold/Solar/0x1dc9 get packed on their first legal
  evaluation (r0=1 once), 0x10F6 Dark Hole after 5. Main-phase selection is posted as commands via 0x0224C28C(side,
  zone,index,mode) from the cursor walker (callers 0x02269664, 0x0224B986/B9B6, 0x0219E78E/ECFC/ED7E ...).
- STILL UNKNOWN: the main-phase chooser. No hook exists yet; the AI does not play Grass.

## 2026-11-04 sessions 8-11 (grass_gdb8..11.py, seed #3)
- HAND WALK MEASURED (grass8_*.json): each AI main phase makes a few 0x0224C28C calls (side,11,slot,mode) and the
  card landed on is then packed/enqueued: Gold (slot5,mode3), Dark Hole (slot0,mode3), Solar (slot4,mode3),
  0x142a (slot3,mode3). Mode 3 = the "activate Spell" selection. Grass (3 copies in the deck) is NEVER landed on.
- The mode-3 selections all share the ov5 call chain 0x0234681D,0x0234687B,0x023468DB,0x02346B4D,0x02346D1F,
  0x02346EEB,0x02346F99 (the last is inside the function at 0x02346F78, right after ai_try_row 0x02346F2C), then
  outer ov5 frames 0x02343 2CB / 0x02342379 (Gold) or 0x023422CF (Dark Hole): an ov5 AI state machine
  ([ctx+0x2A] state). So the CPU picks main-phase Spells in OVERLAY 5, not in the ov3 code I was reading.
- ai_try_row 0x02346F2C itself is only called ~116x/duel on answer-window rows (handler 0x02336125 for most);
  none of the played cards' rows pass through it.
- ai_row_at 0x023359C0 returns (grass11_*.json 'seen'): the big list (arg 0x23958DC-ish, 1417 distinct rows) offers
  Grass's row {0x3D0FD, 0x0231111D} 47 times -- the same as Gold {0x3D811,0x02310889} (47), Solar (46),
  Charge (44), Dark Hole (48), 0x142A (47). => Grass IS offered as a candidate as often as the played cards.
- Grass's evaluator 0x0231111D is a 3-instruction thunk `ldr r3,=0x02311085; movs r1,#0; bx r3`, i.e. generic
  eval 0x02311084(desc, 0) (uses 0x02310FF0, 0x021AC0C8, 0x021AE5C8, 0x02352A8C deck count...); not Sparks-specific.
  Live-writing the handler to Needlebug's 0x0232C479 and to the default 0x02336125 changed nothing (weakly: the
  write was to the static row at 0x02392A70; whether the evaluated row is that copy is UNPROVEN).
- NOT FOUND: why the ov5 state machine never picks Grass. Next: break INSIDE the evaluation (the eval fn that the
  row list calls: log the return value of the handler for Grass's row vs Gold's), starting from
  0x02346F78's caller chain; or log the arguments/return of 0x02311084 for desc cid 0x10FD.

## 2026-11-04 ROOT CAUSE + FIX (session 12/13) -- AWAITING IN-GAME TEST
- MEASURED (grass12_*.json): the generic evaluator 0x02311084 (Grass's row evaluator thunk 0x0231111C -> 0x02311084(desc,0))
  returned 0 on ALL 31 of Grass's evaluations; Gold's evaluator 0x02310888, Dark Hole's 0x02319A7C and Solar's 0x0232B7B0
  returned 1 on the evaluation that preceded their play.
- WHY (disassembly): 0x02311084 -> 0x02310FF0 -> 0x02310F18 -> 0x0234AD94(side, cid): an LP-effect-table lookup keyed by
  cid. Not found -> returns 0 -> 0x02310FF0 sees r0>=0 and the evaluator returns 0 ("do not play"). Grass inherited
  Sparks' ov5 CPU row {0x0003D0FD, 0x0231111D} at 0x02392A6C (a burn/LP evaluator); no LP entry => never played.
- FIX: ov5 data word 0x02392A70 := 0x023107C1 (`movs r0,#1 ; bx lr`, already the evaluator of 4 stock rows). Live-patched
  over GDB on seed #3 (grass4_row3_*.json): Grass ENQUEUED for the first time (enqueues=1; baseline 0).
  (Earlier row/row2 tests used 0x0232C479 / 0x02336125 and did not work: those evaluators reject Grass too.)
- Module: otn_enhanced/cards/that_grass_looks_greener.py now patches the row after the DSL build (_patch_ai_row) and
  verify() checks it (single-card build 4/4 + row PASS). NOT wired into the chain / steps; the shipped chain ROM
  does NOT contain the fix until the user approves.
- Caveat: the evaluator is now unconditional, so the CPU will activate whenever the card's own COND passes
  (Deck > opponent's). Whether it activates at sensible times, and whether it RESOLVES in the CPU duel, is untested.
- E2E on a BUILT ROM, no live patch (scratch/grass_fix_e2e.py: rom_all_patches copy + _patch_ai_row -> rig
  battery_grassfix.nds sha dc831b86...a8b827): seed #3 Grass enqueued 1x (706 hits).
- GAUNTLET on the fixed rig (scratch/grass_fix_gauntlet.py -> data/cpu_gauntlets/grassfix_glaton, 40 duels, emulator CPU):
  That Grass Looks Greener drawn 24 / summoned 0 / activated 22 (before the fix: drawn 60 / activated 0).
  Glaton went 31-8 (79.5%); the 40-duel sample is too small to compare with the earlier 100-duel 66.7%.
- Status: user said "I can confirm grass works" on 2026-11-04 after testing the fix (scope presumed: the CPU now plays the
  card; exact ROM and whether the mill amount was checked NOT stated -- confirmed by user 2026-11-04, scope to be
  confirmed). Not wired into the chain / steps.STEPS: shipping has not been approved.
  (earlier line, superseded:) AWAITING IN-GAME TEST (emulator CPU stats are not user confirmation). Whether the CPU's activations RESOLVE
  correctly (mill own-minus-opp) is not checked; the evaluator is unconditional so timing is the card COND only.
- Fixed ROM copy: data/over_the_nexus/working/rom_all_patches_grassfix.nds (experiment copy; NOT the baseline).

## Next Experiment
- Log, per candidate row, the return value of its handler (bp at the handler entry + lr) for Grass vs Gold.
- Trace the AI's HAND walk (DONE, see above): bp 0x0224C28C with zone==hand, log (index, hand contents via 0x0229B7D0 area) per AI
  turn on seed #3 and see which hand slots the AI walks to and whether Grass's slot is ever selected / skipped.
- Check activation counts of Needlebug Nest 0x1E59 / other "send top N" Spells in the batteries; if also 0, the
  AI evaluates milling Spells as useless (a benefit gate) and the hook goes there.
- Disassemble 0x021ECB82 and 0x021EDBxx (scan path) and the consumer of its candidate list; log, for Grass vs
  0x1811, the values compared right after COND returns (record +8 criteria word, +0x10 flags) -- see if record
  fields beyond {RES, COND} that Gold has (cls0 0x1811 record) and ours lacks gate the candidate.
- Find the chooser: disassemble the writers of [0x0229ABFC+0x64] (candidate list above, confirm base reg), then
  re-run grass_gdb2 with bps on those writers logging the cid they store -> see whether Grass is ever stored and
  what the stores for 0x1811 test first (guess to test: a cid/set-code/effect-type class check on the record).
- Earlier plan (done in part by session 2): enqueue log for ALL cids (validate the filter; do Gold Sarcophagus 0x? appear?) and the
  wrapper's caller chain (sp walk) for the Grass COND call vs a Gold Sarcophagus COND call. The difference in
  who calls / what gate precedes the enqueue is the missing hook.
- Rebuild battery ROM, run `gauntlet run <deck holding Grass>`, read card_stats.csv for the card; if
  drawn>0 and activated=0, disassemble why COND fails for the AI (0x021BA9AD gate / deck-count read).
- In-game: Deck 35 vs 30 -> activate -> 5 milled, Deck 30. Equal / smaller -> not activatable.
