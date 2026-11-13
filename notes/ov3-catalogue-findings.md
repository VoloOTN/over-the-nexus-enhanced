# ov3 catalogue — findings (live log)

Goal: catalogue every ov3 function (`_func, memory_offset, assembly_code` via
EffectBuilder) with what is known about it, then turn PARTIAL / UNKNOWN into
KNOWN. Started 2026-10-02.

## Confirmed

All proven 2026-10-02 on stock `data/over_the_nexus/working/rom.nds` (EU `BYYP`).

- **The catalogue exists and is exact.** `.venv-1/Scripts/python.exe -m otn_enhanced.tools.ov3_catalogue`
  prints `re-assembly: 5731 identical, 0 differ []`. It also asserts that the
  entry sizes add up to the whole of ov3 (0x152CE0 bytes). Output is in `docs/ov3_catalogue/`.
- **Counts** (`ov3_index.csv`): 5700 functions (4903 Thumb, 797 ARM), 31 gaps,
  2 data regions. Status: KNOWN 213, PARTIAL 913, HANDLER 2466, UNKNOWN 2108 (after the ov10 fix; was 927/2094).
- **Data area:** `0x0226C210`–`0x0228F884` and `0x0228FA28`–end. The
  static-init ARM functions live at `0x0228F884`–`0x0228FA28` (init array `0x0228FA28`–`0x0228FA50`).
- **mwcc BL-as-far-branch.** KB fact `tool.mwcc_bl_is_a_far_branch_inside_big_functions`
  (VERIFIED). The BL at `0x0220502E` jumps to `0x02206106` = `ADD SP,#0x58`, the
  LP resolver's own epilogue (its prologue does `SUB SP,#0x58` at `0x02204D0A`).
  A NOP pad sits at `0x02205032`.
- **mwcc switch idioms** (disassembled this session):
  - Thumb `CMP Rn,#N; BHI dflt; ADD Rx,Rn,Rn; ADD Rx,PC; LDRH Rx,[Rx,#6]; LSL/ASR #16; ADD PC,Rx` at `0x0219A876`. The table follows the `ADD PC`; target = addr(ADD PC)+4+entry.
  - LDRB byte-table variant: `0x021EB7CC`.
  - `BLS ok; B dflt` bound: `0x02206CD0`.
  - Register-bounded (`SUB; BMI`, no `CMP #imm`): `0x021E14A6`.
  - Case bodies not directly after the table (all entries `0x40`): `0x0220806A`.
  - ARM `ADDLS PC,PC,Rn,LSL#2`, one instruction per case from addr+8, default at addr+4 (entries may be `POP {..,PC}`): `0x0218D34C`, `0x0219004C`, `0x02168660`.
- **arm9 "pointers" into ov3 are noise.** Words in arm9 whose value is an odd
  ov3 address: 141 have no PUSH prologue at the target and 1 does. ov41: 2 hits, both
  without a prologue. Only ov3 and ov5 pointers are used as entry evidence.
- **The ov3 address range is shared with other overlays.** Lines in patches and notes such as
  `OV1_BASE = 0x02141700` (pack_unlock_conditions) and "ov10 US: ram 0x0214C920"
  are about other overlays. The generator skips lines that name another overlay or the US ROM.
- **Shape of the remaining work** (PARTIAL + UNKNOWN = 3021):
  - 796 are ARM. 732 ARM functions are UNKNOWN, all in the `0x02141700`–`0x021917xx`
    block, which holds only 1 KNOWN function.
  - 298 have ≥10 callers; 951 have 0 callers; 2145 have no named call or named literal-pool reference.
  - Most-called: `0x021D2964` (271), `0x021A1430` (256), `0x0219A818` (254),
    `0x021D28A4` (234), `0x021A36EC` (219), `0x022349B0` (211), `0x02234904` (198), `0x021A3320` (180).
- **`encode_thumb_line` cannot encode LDSB/LDSH** (2485 sites). The catalogue emits
  those as `b.raw()` with the disassembly as a comment.
- **`ThumbAssembler.assemble` refuses bases ≡ 2 mod 4.** `ov3_catalogue.assemble_native`
  assembles at the real address instead. Shared tooling was left untouched.

- **Breakpoint-capacity test, P0 idle puzzle, stock ROM, 2026-10-02 21:25** (`scratch/ov3cat/bp_capacity.py`,
  result `scratch/ov3cat/bp_capacity_result.json`). One connection.
  - Preflight in the same session: ov3 anchor `38b5012202400e480e4c5043` matched; `0x022C5900`
    held ov41's image, not ov5's (puzzle measured live, consistent with `mem.ov5_ov41_share_base`);
    ARM-block code matched the ROM.
  - **All 200 breakpoints armed with no error** (100 ARM-block, kind 4; 100 KNOWN Thumb, kind 2).
  - The 60 s window ran; cleanup deleted the 181 left over; detach was clean.
  - 19 hits, delete-on-first-hit, **all within t = 0.004–0.023 s, then none for the rest of the
    window**. 17 were ARM-block functions; 2 were KNOWN Thumb: `0x0224CD84`
    (`dispatch.activation_turn_locks`) and `0x021A0714` (`rider.two_walker_families`).
  - **So 17 of the 100 sampled ARM-block functions execute in an idle puzzle.** The ARM block is
    not dead code. Its role is still not established.
  - The user reported (2026-10-02, verbatim): "The game kept animating and responded normally".
    Their confirmed reading: the emulator ran the whole window, so the other 181 functions really
    did not execute while idle. **The melonDS stub holds 200 breakpoints in one session without
    stalling, and the idle-loop functions all fire within ~25 ms of arming.**
- **Catalogue contamination fixed.** `patch_unlock_all_packs.py` and
  `notes/booster-pack-unlock-findings.md` are about ov10 (the card shop) at the same addresses,
  yet their lines were labelling ARM-block ov3 functions (e.g. `0x0214DE00`, `0x0214586C`).
  The generator now skips any source file that names other overlays more often than ov3.
  ov5/41/47–49 don't count as foreign, since they don't overlap ov3. 14 entries went from
  PARTIAL to UNKNOWN; re-assembly is still 5731 identical.
- `patch_battle_speed`, `patch_duel_fastforward` and `patch_skip_animations` really are ov3
  patches that write into the ARM block (their docstrings say "overlay 3 only"). HYPOTHESIS: the ARM
  block includes duel animation/timing code. That fits it running while idle.

- **P1 trace VALIDATED, and it exposed a catalogue bug (2026-10-02 21:41, melonDS pid 1340).**
  The user: "yes i activates pot of greed, the draws happened, i waited and then pressed enter".
  - Trace: 5700 armed in 8.94 s; 142 idle hits, 468 action hits (28 KNOWN, 198 PARTIAL, 241 UNKNOWN, 1 HANDLER).
  - My controls `0x021D88EC` / `0x0220AAA8` did NOT fire, because they were wrong. The real cid-first
    cls0 record for Pot of Greed (cid 0x12EC) is at `0x0227F60C`: `{0x12EC, main 0x022065B9, 0, cond 0x021F069D, 0, 0}`.
    **`0x022065B8` and `0x021F069C` BOTH appear in the action hits** -> the trace caught the activation.
    (`0x021D88EC`/`0x0220AAA8` are slots of the NEIGHBOUR record `0x0227F5F4`, cid 0x12EB.)
  - **Catalogue bug:** the HANDLER status and the "card handler" cards come from
    `effect_extract.HANDLER_TABLE_OFFSET` (cid LAST, one record off). The KB already says that layout is
    WRONG (`effect_dispatch_tables`: real tables are cid FIRST: cls0 0x0227E64C x0x51A, cls2 0x02275C04 x0x2B9, ...).
    All 2466 HANDLER rows and the card names in the docstrings are suspect until rebuilt from the cls tables.
    The 5700 function entries and the byte-exact re-assembly are unaffected.
  - **FIXED 2026-10-02:** `ov3_catalogue.handler_users` now reads the four real cls tables
    (`CLS_TABLES`: cls0 0x0227E64C x0x51A, cls1 0x022860D4 x0x535, cls2 0x02275C04 x0x2B9,
    cls3 0x02279D74 x0x308) and labels each slot with its KB role (resolver / on-field candidate
    predicate / activation condition / cost step / target declaration step). Regenerated:
    5731 entries re-assemble identical; all 2634 distinct slot targets are catalogue entries.
    Counts now KNOWN 213 / PARTIAL 915 / HANDLER 2466 / UNKNOWN 2106.
  - Pot of Greed's real records are now KNOWN: `0x022065B8` (resolver, `resolver.draw_n_is_a_per_cid_table`)
    and `0x021F069C` (condition, `dispatch.draw_condition_needs_the_count_row`).
  - **Corrected controls for the puzzle set** (from the cls records; "shared" = records using it):
    - P1 Pot of Greed 0x12EC: 0x022065B8 (shared 125), 0x021F069C (shared 37). Already seen in the P1 trace.
    - P3 Monster Reborn 0x12EA: 0x0220D530 resolver (UNIQUE), 0x021F2BAC condition (UNIQUE), 0x02235604 target step (shared 313).
    - P5 MST 0x132D: 0x021DB3BC candidate predicate (shared 19), 0x02204898 resolver (shared 184), 0x02234DA4 target step (shared 242).
    - P6 Trap Hole 0x12E4: 0x021DB0A8 predicate (shared 4), 0x021F2B6C condition (shared 3), 0x02234E3C target step (shared 52); resolver is the shared 0x02204898.
    - Celtic Guardian / Mystical Elf are vanilla: no records. P2 and P4 have no card-specific control.
    - **The earlier P3 control 0x02206138, P5's 0x0220E2E0 and P6's 0x021DB06C came from the wrong table; drop them.**
    - The unique ones (Monster Reborn's resolver and condition) are the best controls.

- **P3 trace (Monster Reborn from hand, Celtic Guardian in GY), 2026-10-02 22:07, melonDS pid 8016, fresh session.**
  User ran it and pressed Enter; `scratch/ov3cat/trace_P3.json`. (The user's message was just the results path;
  they were not asked about what they did this time, so the action sequence is as instructed, not user-reported.)
  - 5700 armed in 9.32 s; 167 idle hits, 561 action hits (40 KNOWN, 246 PARTIAL, 272 UNKNOWN, 3 HANDLER); 0 unarmed stops;
    stopped by Enter; 4972 breakpoints left armed and cleaned up.
  - **Controls PASS:** Monster Reborn's UNIQUE resolver `0x0220D530` and condition `0x021F2BAC` and the off-field
    target step `0x02235604` all fired in the action phase; Pot of Greed's draw resolver `0x022065B8` did NOT
    (negative control OK).
  - Differential vs P1 (action phases): 397 shared, 164 only in P3, 71 only in P1.
    P3-only after also removing both idle sets: 158 functions (14 KNOWN, 2 HANDLER, 57 PARTIAL, 85 UNKNOWN).
    The 14 KNOWN are all the Special-Summon / off-field-pick path the KB already describes:
    SS gate `0x021BA258`, generic SS commit `0x0226925C`, summon trigger list `0x02265768`, level restriction
    `0x021BA1E8`, pick halfword accessors `0x02234964`, multi-select count `0x0219C4B0`, pick readback `0x0219C510`,
    rider node writer `0x0219F190`, attach API `0x021C479C`, leave poster `0x021D3648`, criteria word matcher `0x0223BA24`.
  - Idle sets overlap 136 of 142/167 between P1 and P3, so the idle baseline is mostly stable but not identical.
  - **Method works.** Next use of the 85 P3-only UNKNOWN + 57 PARTIAL: they are candidates for
    "Special Summon from GY / pick one card" machinery (HYPOTHESIS: based on co-occurrence with the 14 KNOWN only).

- **P5 trace (Pot of Greed + MST in hand, opp Set Trap Hole), 2026-10-02 22:11, melonDS pid 1208, fresh session.**
  `scratch/ov3cat/trace_P5.json`. The user sent only the results path; what happened in-game was reported
  afterwards, verbatim: "Trap hole was destroyed, I drew 2 cards". So the full action (chain MST onto Pot of Greed,
  destroy the Set Trap Hole, draw 2) completed, and the 542 action hits are that whole sequence.
  - 5700 armed in 8.93 s; 142 idle, 542 action hits (0 unarmed); stopped by Enter; 5016 left armed and cleaned up.
  - **Controls PASS:** Pot of Greed `0x022065B8` + `0x021F069C`; MST predicate `0x021DB3BC` (shared by 19),
    resolver `0x02204898` and target step `0x02234DA4` (both shared) all fired in the action phase.
  - **Prediction that FAILED:** I said Trap Hole's condition `0x021F2B6C` should NOT fire. It DID.
    (`0x021DB0A8`, Trap Hole's predicate, and Monster Reborn's `0x0220D530` did not.) `0x021F2B6C` is shared by
    3 records (Eatgaboon, House of Adhesive Tape, Trap Hole). HYPOTHESIS: the engine polls the opponent's Set
    traps' activation conditions when a chain opens; not tested.
  - Action overlap: 468/542 with P1, 431/542 with P3. **Only in P5** (not in P1/P3 action, not in any idle): 40 functions
    (5 KNOWN, 2 HANDLER, 16 PARTIAL, 17 UNKNOWN). KNOWN ones: `0x021A0C94` link lookup by source zone,
    `0x021D6E40` zone-predicate bitmask candidate predicate, `0x02234CA4` slot5 target picker,
    `0x0224A8C0` per-card candidate filter, `0x0224A924` resolver re-validates its pick.
    HYPOTHESIS: the 33 PARTIAL/UNKNOWN are the on-field Spell/Trap targeting and chain-link machinery.

- **P6 trace (Celtic Guardian in hand, opp Set Trap Hole; Normal Summon, AI responds), 2026-10-02 22:14, melonDS pid 15152.**
  User report, verbatim: "Okay P6 done, trap hole was activated and celtic guardian was destroyed".
  `scratch/ov3cat/trace_P6.json`: 5700 armed in 8.91 s; 139 idle, 562 action hits (0 unarmed); stopped by Enter.
  - **Controls PASS:** Trap Hole predicate `0x021DB0A8`, condition `0x021F2B6C`, target step `0x02234E3C` all fired;
    Pot of Greed's `0x022065B8` and Monster Reborn's `0x0220D530` did not (negative controls OK).
  - Action overlap with P1 / P3 / P5: 433 / 438 / 468 of 562. Only in P6 (vs P1,P3,P5 action and all idles): 40
    (3 KNOWN, 2 HANDLER, 20 PARTIAL, 15 UNKNOWN). KNOWN: `0x021CC028` destroy survive check, `0x021D2584`
    turn-log once-per-turn pair, `0x0225E51C` hand-SS dispatch (fires on a Normal Summon).
  - This also settles P6's earlier open question: the AI did activate Trap Hole.

- **Cross-puzzle analysis (P1, P3, P5, P6), 2026-10-02.** `docs/ov3_catalogue/trace_analysis.md`, generated by
  `scratch/ov3cat/analyse_traces.py`. All four traces: 5700 armed, 0 unarmed stops, every control passed, every
  negative control stayed quiet.
  - **848 of 5700 functions (14.9%) executed** in at least one phase; 4852 never did. Idle in all four: 129.
    Action in all four and never idle: 376 (the generic activation/resolution path: 24 KNOWN, 183 PARTIAL, 168 UNKNOWN, 1 HANDLER).
  - Puzzle-specific (this puzzle's action only): P1 0, P3 78, P5 20, P6 40. P1 is a strict subset of the others'
    generic path, so a draw alone adds nothing beyond it.
  - **The ARM block is live:** 300 of its 720 functions fired (306/797 ARM overall). The "presentation code that
    never runs in effect resolution" hypothesis is dead for at least those 300. Their role is still unknown.
  - Highest-value PARTIAL functions that fired (many KNOWN neighbours): `0x021A1430` (256 callers, idle),
    `0x0219A818` (254, P3/P5), `0x021A36EC` (219, idle), `0x021D2964` (271, all four), `0x021D28A4` (234, all four),
    `0x021A3320` (180, all four), `0x02243FE0` / `0x02243FA8` (call KNOWN `0x02243B9C` / `0x02243F38`).
  - Limits: only four actions; a function that never fired is NOT dead (puzzles evict ov5; AI turn, Synchro/Fusion,
    spells with costs, continuous effects, flips, and the deck editor were not exercised).

- **Plan step 2, first three functions (2026-10-02).** User asked to promote the top PARTIALs and asked "nothing from
  these traces promoted anything to KNOWN, correct?" -- correct: traces alone promote nothing; KNOWN needs a KB fact with a
  passing proof AT the entry. KB now 627 facts, 557 PASS, 0 FAIL, 70 UNVERIFIED.
  - **PROMOTED to KNOWN (by disassembly proof, not by the trace):** `0x021D28A4` (push) and `0x021D2964` (pop) -> facts
    `engine.depth_counter_push_pop_0x021D28A4_0x021D2964` and `engine.depth_counter_pop_0x021D2964` (VERIFIED, proofs
    assert the full decoded body + pool words + the 0x0219EA84 BL). Counter = [0x0229AB7C+0x28]; both no-op if
    [0x0229AB7C+0x34] != 0; first-push init ([+0x30]=0, [0x0229ABFC+0x60]=0, [+0x2C]++) only on the non-mode-2 path.
    The NAME "chain-depth" is inherited from in-game-confirmed patches (Ceruli/Grapha/Sillva/Delinquent Duo), not re-proven.
  - **NOT promoted:** `0x021A3320` -> UNVERIFIED fact `engine.zone_effective_cid_0x021A3320` (hypothesis: effective cid of a
    zone after attached-node substitutions) with next_experiment (thumbemu on a savestate with/without a kind-2/3 node).
  - Catalogue now: KNOWN 215 / PARTIAL 913 / HANDLER 2466 / UNKNOWN 2106 (was 213 / 915 / 2466 / 2106).
  - **Bug I introduced and fixed in the same step:** my fact-insert script left a literal `%%` and `%r` in
    `author_facts.py`, so it had a SyntaxError for one command. Caught by `--check`; repaired by pre-formatting the proof
    strings. Lesson: build proof text in Python before insertion, never rely on `%` inside a generated source block.

## Ruled Out

- **A second GDB connection in the same melonDS session (2026-10-02 21:31).** Do not retry this.
  The capacity test connected, detached cleanly with 'D', and the user loaded P1 without
  restarting melonDS. Then `trace_puzzle.py P1` connected again and `halt()` got no reply within 8 s
  (`TimeoutError: no data from GDB stub`); 0 breakpoints were armed.
  This reproduces `tool.gdb_one_shot_session` (2026-08-03: the second connection's halt timed out),
  and a clean detach does not prevent it.
  **Rule: restart melonDS before every new connection, or keep one connection for the whole
  multi-puzzle run.**
- **NOT ruled out: GDB first-hit tracing of all 5700 entries (2026-10-02 21:32, P1, fresh melonDS).**
  The user briefly said "I think the approach of running GDB traces is not going to work here", then
  withdrew it: "Actually ignore my message about GDB tracing, get better at catching when i reset my
  melon". So the method stays. What the run measured (`scratch/ov3cat/trace_P1.json`):
  - All 5700 breakpoints armed in 9.58 s; preflight OK (ov3 anchor, ov41 resident).
  - 142 hits at t < 1 s, quiet until t ≈ 17 s, then a burst of 468 hits in 3 s, including draw
    `0x021D12F4` at t = 19.30 s.
  - Then `RspError: connection closed by stub` at t = 19.97 s.
  - Pot of Greed's handlers `0x021D88EC` and `0x0220AAA8` were NOT hit. The "READY" signal never
    reached the user (my watcher's start-time filter was wrong), so whether the burst was the action
    is unconfirmed.
  - HYPOTHESIS (from the user's wording, not yet confirmed): the close at 19.97 s was the user
    resetting melonDS, since READY never arrived, not the stub failing under 5700 breakpoints.
  - **Fix (this session):** the script now refuses to connect twice to the same melonDS
    process, reports "melonDS was reset/closed" separately from a stub failure, prints READY
    itself, and takes Enter to stop. It runs in the user's terminal so they see it live.

- **"Every BL target is a function."** Killed by `0x0220502E` → `0x02206106`
  (the function's own epilogue). Do not retry this.
- **arm9 / ov41 values as pointer seeds.** 141/142 had no prologue (see above). Do not retry this.
- **Odd ov3 pointers as entries without a plausibility check.** The word at `0x0218A798`
  holds `0x02205001`, which points mid-function right after a `BLT` (at `0x02204FFE`).
  An entry must not follow a conditional branch or a BL.
- **Sizing a jump table from the `CMP #N` bound alone.** Fails on `BLS;B` and on register-bounded switches.
  **Sizing it as "the table ends at the first case body" alone** fails at `0x0220806A`, where the bodies
  are not adjacent. The tool uses the bound when there is one and the first-body rule otherwise.
- **"Called by ≥2 functions" as entry evidence.** Fragments of one function call each other
  (`0x02204FCE` was "called" from `0x02205000` and `0x022056FC`, all part of `0x02204D08`).
  The tool now requires a BL from a *different span* and a plausible entry, and resolves
  overlapping code by demoting the weaker-evidenced side.
- **Heredocs for code edits** (reconfirmed). A heredoc put literal `\x08` bytes into a regex in
  `ov3_catalogue.py`. It was found and fixed, and both new modules were scanned clean of
  control characters.

## Open Questions

(Updated at handoff, 2026-10-02. Items 1, 2 and 5 of the earlier list are RESOLVED: the ARM block is live, the stub holds 5700
breakpoints, and the user builds puzzles in the in-game editor.)

1. What do the 300 live ARM-block functions (of 720) do? Untouched; 700+ UNKNOWN, no named neighbours.
2. `0x021A3320` needs a savestate with an attached kind-2/3 node to prove or kill the UNVERIFIED fact
   `engine.zone_effective_cid_0x021A3320`. No such savestate is on disk.
3. 19 functions are BOUNDARY UNCERTAIN (CSV `boundary` column); two hit invalid instructions: `0x0220DCC0` (at
   `0x02211F7A`) and `0x02267A6C` (at `0x0226CEB4`).
4. Does the 3DS `code_dec.bin` carry symbols or debug strings that would *name* functions? Unchecked.
5. Untraced actions: P0 baseline, P2 (Normal Summon alone), P4 (attack), AI turn, Synchro/Fusion, costs, continuous effects,
   flips. Never fired != dead (puzzles evict ov5; 153 ov3 functions are referenced from ov5).

## Puzzle set v1 (agreed 2026-10-02; the user builds them in the in-game editor)

Cards checked this session: each is in `KONAMI_ID_TO_CARD_NAME`, its text is from
`scratch/ygoprodeck_cache.json`, and its handlers come from the ov3 handler table.
Celtic Guardian 0x0FCF: vanilla, L4, 1400/1200. Mystical Elf 0x0FA8: vanilla, L4, 800/2000.
Pot of Greed 0x12EC: "Draw 2 cards." Monster Reborn 0x12EA. MST 0x132D. Trap Hole 0x12E4.

**Base board, identical in all seven:**
- LP 8000 / 8000.
- Player: Deck = 5× Mystical Elf; field, hand and GY empty.
- Opponent: Deck = 5× Mystical Elf; field = 1× Mystical Elf face-up ATK; hand and GY empty.

| # | add to base | action | positive control (must be hit) |
|---|---|---|---|
| P0 | nothing | idle | none (baseline) |
| P1 | hand: Pot of Greed | activate | 0x021D88EC, 0x0220AAA8 |
| P2 | hand: Celtic Guardian | Normal Summon, ATK | none (vanilla) |
| P3 | hand: Monster Reborn; GY: Celtic Guardian | activate, target it | 0x02206138 |
| P4 | field: Celtic Guardian face-up ATK | attack opp's Mystical Elf | none |
| P5 | hand: Pot of Greed + MST; opp Set: Trap Hole | Pot of Greed, chain MST on the Set card | P1 controls + 0x0220E2E0 |
| P6 | hand: Celtic Guardian; opp Set: Trap Hole | Normal Summon; AI may respond | 0x021DB06C (Trap Hole only) |

Handler sharing (from the catalogue's HANDLER rows):
- 0x021D88EC: Pot of Greed + Ameba.
- 0x0220AAA8: 5 cards.
- 0x0220E2E0: MST + Worm Bait.
- 0x021DB06C: Trap Hole only.
- 0x02206138 is also listed for Dian Keto and Hinotama, and is KNOWN as the LP-resolver
  caller chain (`lp.burn_invocation_chain`). Why Monster Reborn points there is an
  open question; the P3 trace will show.

Unknowns:
- P4: RESOLVED by the user 2026-10-02: "P4 let's you attack on the first turn as the
  turn counter is 10 in puzzles". Puzzles start with the turn counter at 10, so the
  first-turn no-attack rule never applies. (User-stated; the RAM address of the turn
  counter has not been located.)
- P5: RESOLVED by the user 2026-10-02: "I will be able to chain mst to my own pot of
  greed for p5". The game offers a chain onto your own spell, so P5 runs as written
  (no fallback).
- P6: RESOLVED by the user 2026-10-02: "Ai will activate trap hole for p6". The
  opponent's AI response path will run, and 0x021DB06C (Trap Hole's own handler)
  must show up in the P6 trace.

Getting puzzles into the game: the user builds them in the in-game editor. I don't write
`.ydq` into a `.sav`: no tool exists and the save may carry a checksum. Revisit only if
many puzzles are needed, and only on a copy of the save.

## Next Experiment

No melonDS needed for the next step: continue plan step 2 (promote the most-called fired PARTIALs).
Work list (largest first, from `docs/ov3_catalogue/trace_analysis.md`): `0x0219A818` (254 callers, P3/P5), `0x021A36EC` (219, idle),
`0x021A1430` (256, idle), `0x021D2BC8`, `0x021A32B4`, `0x02243FE0`, `0x02243FA8`, `0x0219C430`.
Method (worked for `0x021D28A4` / `0x021D2964`): disassemble; grep `otn_enhanced/docs/engine/*.yaml` for the address; write a VERIFIED fact whose proof
asserts the decoded body, pool words and BL targets; anything the code alone does not prove goes in as UNVERIFIED with a next_experiment.
Then `author_facts --check`, `verify_knowledge`, regenerate the catalogue, and update the counts in the prompt.

If more traces are wanted (P2, P4): restart melonDS, then `.venv-1/Scripts/python.exe scratch/ov3cat/trace_puzzle.py P2` in the user's terminal
(it enforces one connection per melonDS process, prints READY, takes Enter to stop). See `PROMPT_ov3_catalogue_phase1.md`.

## Session 2026-10-18 (step 2, promotion)

- `0x0219A818` promoted PARTIAL -> KNOWN (KB `engine.ui_event_post_0x0219A818`, VERIFIED): UI-event poster
  `(side, code)`; `[0x0229DD94+0x30]=side`; only if seat mode `[0x0229911C+4*side]==0` (human) sets `[0x0229DD94+0x2C]=1`
  and calls `0x0219C99C(0x36, 0, code, 0)`. Proof = decoded body + pool words + BL target (decode checked against the ROM this session).
  Catalogue regenerated: KNOWN 244, re-assembly 5731 identical.
- Open: what `0x0219C99C` (kind 0x36, 129 callers) does with `code`, and the readers of `[0x0229DD94+0x2C]`.
- Next in the work list: `0x0219C99C` (natural follow-on), then `0x021A36EC`, `0x021A1430`, `0x021D2BC8`, `0x021A32B4`, `0x02243FE0`, `0x02243FA8`, `0x0219C430`.
- Gotcha: `scratch/dis.py` shadows stdlib `dis` when a script lives in `scratch/` (circular `dataclasses` import); run helper scripts from elsewhere with `PYTHONPATH=.`.

- `0x0219C99C` promoted -> KNOWN (KB `engine.ui_event_wrapper_0x0219C99C`, VERIFIED, 2026-10-18): thin wrapper; args forwarded unchanged
  via `blx 0x02148AA0` (0x29E8-byte ARM). Pre-hooks (0x0226B9BC/0x0226B9E0, only if `0x02299114` +8/+0xC == 1) apply to kinds 6, 0x19..0x22,
  0x26 only; kind 0x36 (and 0x37 PICK_UI) = pure passthrough. Readers of `[0x0229DD94+0x2C]`: poll `0x0219AF00` and `0x0219E964`; value 1 does
  nothing there, so the poll clears the flag the poster set. Also added 0x0219AF00 / 0x0219E964 head bodies to the proof (not separately promoted).
- Open: `0x02148AA0` kind dispatch for 0x36 (ARM, not read); the 0x19..0x22 switch targets; meaning of flag values 2..0xB / 0xD..0x14 / >0x14.

- `0x02148AA0` (ARM, 0x29E8 B) kind 0x36 arm proven (KB `engine.ui_event_kind_0x36_arm_0x02148AA0`, VERIFIED, 2026-10-18): dispatch table of `b`s starts at
  0x02148B10 (index = kind; default at 0x02148B0C), 0x36 -> 0x021499E4; for `a != 0xC` it ends `0x02153E70(0x022952E4, a, code, c); return 1`
  (entry gate: if `[0x020B7C8C+0xB80]==9` it first calls 0x02195598 and returns 1 on 0). Only the 0x36 arm is promoted into the fact; the catalogue now labels the whole 0x29E8-byte function KNOWN because a fact is anchored at its address -- read that as "kind 0x36 arm only".
- Open: `0x02153E70` (0x1440 B ARM, UNKNOWN, 13 callers; uses code>>16), the object at 0x022952E4, `[0x020B7C8C+0xB80]` meaning, `0x02195598`.
- Gotcha: capstone ARM-decodes literal pools as nonsense (andeq/eoreq runs) -- read pool words with u32, never trust them as code.

- `0x02153E70` (ARM, 0x1440 B; the UI-window opener) a=0 path proven (KB `engine.ui_dialog_open_0x02153E70`, VERIFIED, 2026-10-18): ctx[0]:=1 active,
  ctx[4]:=a, ctx[8]:=c, `0x02156B90(ctx, code)` draws the text, then table of `b`s at 0x02154394 indexed by ctx[4] (<=0x36); a=0 -> 0x021546B4 -> 0x021545E0 (unread).
  `0x02156B90` does `code>>16 == 0 ? code := 0x0202A970(code) : use as pointer` => the ids patches pass to 0x0219A818 look like TEXT ids (0x0202A970 not decoded: UNPROVEN).
  Correction: the previous fact's "code is packed" aside was wrong; reworded to point here. Catalogue labels the whole function KNOWN; read as "a=0 path only".
- Full chain now documented: `0x0219A818(side,code)` -> `0x0219C99C(0x36,0,code,0)` -> `0x02148AA0` kind 0x36 -> `0x02153E70(0x022952E4,a,code,c)` -> `0x02156B90` text.
- Open: `0x0202A970` (arm9, text-by-id?), `0x021545E0` tail, `0x02155CE0`, and `[0x0229DD94+0x2C]` flag value semantics.

- `0x0202A970` (ARM9, Thumb) decoded (KB `engine.ui_message_id_fetch_0x0202A970`, VERIFIED, 2026-10-18): id 1 = list-built string into buffer 0x02121C94 (arms not decoded);
  every other id -> `0x0202A7C4(id)` = offset-pair string table fetch (index store 0x020AB6C4 slot id*4 -> (start,end); data store 0x020AB6D8 range; buffer 0x02122118).
  `0x0202A814(dst, v)`: v & 0xFFFE0000 == 0 => treated as id. ANSWER to "is the code a text id": YES structurally — it is a MESSAGE-TABLE ID. Not proven: that the stores are the
  localized text archive (contents not in RAM image), 0x02016A48's arg roles, 0x02094BC0.
- Whole chain documented: 0x0219A818(side,id) -> 0x0219C99C -> 0x02148AA0[0x36] -> 0x02153E70(ctx,a,id,c) -> 0x02156B90 -> 0x0202A970(id) -> 0x0202A7C4. Cheap follow-up that would close it:
  read the string for id 0xD / 0x30 from a savestate at 0x02122118 right after a prompt (needs user savestate), or locate the archive in the ROM filesystem.

## Session 2026-10-18 (cont.): 0x021A36EC
- `0x021A36EC(side, zone)` promoted -> KNOWN (KB `engine.zone_cid_at_0x021A36EC`, VERIFIED): thunk to body `0x021A36F8(side, zone, flag=1)`; reads the 14-bit cid at
  `0x0229AC94 + (side&1)*0xB3C + zone*0x14 + 0x34`. Zone>4: only 0x2150 special. Zone<=4: 9-cid ARM9 list 0x0209BA8C -> walk attached nodes (0x0229D33C stride 0xA, kinds 2/3, keys
  0x1A74/0x1E7E/0x221E, last wins, is_monster-gated) and substitute `[node+4]`; else 13-cid list 0x0209C8F8 (flag!=0) -> `0x021A1584(side,zone,0x1DDA)`.
  The body entry `0x021A36F8` is still its own PARTIAL row (the fact is anchored on the thunk); worth promoting by pointing a second fact at it.
- Practical rule for patches: comparing this result to a donor cid is only safe if the donor is in neither list and is not 0x2150.
- Open: names of list A/B cids; what `0x021A1584` returns for them. Work list remaining: `0x021A1430` (256 callers), `0x021D2BC8`, `0x021A32B4`, `0x02243FE0`, `0x02243FA8`, `0x0219C430`.

- `0x021A1430(side, zone, key)` promoted -> KNOWN (KB `engine.attached_key_presence_0x021A1430`, VERIFIED, 2026-10-18; full bodies of it AND walker `0x021A1238` asserted):
  head = u16 `[0x0229ACD2 + (side&1)*0xB3C + zone*0x14]`; walker follows nodes (0x0229D33C + idx*0xA, next = u16 +8), kind(+2 & 0xF) < 6, first u16 == key, FIRST match wins, returns node ptr; 1430 = boolean.
  Contrast with `0x021A36F8` (last-wins substitution walk). Walker `0x021A1238` is anchored via this fact only; it keeps its own PARTIAL row.
- Work list remaining: `0x021D2BC8`, `0x021A32B4`, `0x02243FE0`, `0x02243FA8`, `0x0219C430`.

- `0x021D2BC8(desc)` promoted -> KNOWN (KB `engine.cost_settled_predicate_0x021D2BC8`, VERIFIED, 2026-10-18): 1 iff desc[+4]==0x25, or (desc cid is a Trap [card_type>>1==14 via 0x02022FDC/0x0202ABF8]
  AND acting cid ([0x0229C33C+desc[+0xC]*8]&0x3FFF) in {0x1935,0x201E,0x219E} or list A 0x0209BA8C AND desc cid not in {0x1935,0x201E,0x219E}). Open: names of those cids.

- `0x021A32B4(side, zone)` promoted -> KNOWN (KB `engine.zone_active_presence_0x021A32B4`, VERIFIED, 2026-10-18): occupied u16 `[0x0229ACD0+S+Z]`==0 -> 0; flag u32 `[0x0229ACD8+S+Z]` bits 6/1/21 -> 0;
  zone>4 -> 1; zone<=4: card_type>>1==9 (0x020230FC) -> `0x021A30EC(side,zone)` else 1. Open: `0x021A30EC` (0x1C8 B, UNKNOWN), meaning of bits 1/6/21, card_type 18/19.

- `0x02243FA8(side,cid,param)` + `0x02243FE0` promoted -> KNOWN (KB `engine.criteria_collect_0x02243FA8` / `engine.criteria_count_0x02243FE0`, VERIFIED, 2026-10-18; shared runner `0x02243F38` body asserted too):
  idx = bsearch `0x02243B9C(cid&0xFFFF, param)` in registry 0x022713C4; FA8 zeroes count s16 `[0x0229944C+6]` then runs `0x02243F38` -> `blx [0x022713C8+12*idx]` (row handler) and returns the count (buffer stays filled);
  FE0 does not zero, returns delta, and RESTORES the count (non-destructive "is there a legal candidate"). Seat-mode-1 pre/post hooks 0x0226B6C0/0x0226B914 unproven.
- `0x0219C430` was already KNOWN (dispatch.list_picker_needs_a_criteria_row); nothing to do. Work list from trace_analysis is now exhausted; regenerate the list with the next-most-called fired PARTIALs.

## Batch 2026-10-18 (next-most-called PARTIAL/UNKNOWN thumb functions, small ones)
Promoted, each with its body asserted from the stock bytes (KB `engine.*`): `0x021B9ECC`=`0x021B9708(side,8,0)` thunk; `0x021AD870`=`0x021AD79C(side,0)` thunk; `0x021B8064`=`0x021B807C(a,b,0)` thunk;
`0x0224BBB0` pick-finished predicate ([0x0229DD94+0x58]!=0 && [+0x6C]==0xB); `0x021B8014` = `0x021B44C0(...)` result word +0x10; `0x021B8E30(a,b,n)` = bit n of `0x021B8D90(a,b)`;
`0x021D269C(flag)` posts event `0x55|(flag?0x8000:0)` via `0x021C3BC8`; `0x021D2B38(desc)` Trap/acting-monster gate (sibling of 0x021D2BC8); `0x021A14B4(side,zone,a,b)` boolean over chain walker `0x021A129C`.
INCIDENT: a bad Python string splice (index j<i) duplicated ~12k lines of author_facts.py; restored by deleting the duplicated span (verified: nothing from HEAD lost, every fact present once, `--check` 666 PASS / 0 FAIL, 750 facts).
Lesson: do multi-line text edits with the Edit tool, not `s[:i]+new+s[j:]` with independently-found indices.
Remaining high-fan-in PARTIALs not yet promoted: 0x022349B0, 0x02234904, 0x021A3320 (UNVERIFIED hypothesis fact), 0x0223C4E8, 0x021D2C1C, 0x0224AA94, 0x021A3054, 0x021AC204, 0x021A220C, 0x021CFBC8.
- Also promoted: `0x021A3054(side,zone,type)` counter-count read (type>=0x19 -> `0x021A1690(side,zone,[0x0226D3FC+4*type])`; type 0xE -> `0x021A1690(side,0xB,0xDAC)`; else capacity!=0 ? u32 `[0x0229ACD4+S+Z]` : 0);
  `0x0223C4E8` = sum of one or two `0x0223C1C4` calls (flags bit1 => both halves, bit0 swapped for the 2nd). `0x02234904` left (packed per-slot decode, needs more work).
- Promoted: `0x0224AA94(desc)` board-wide target counter (calls slot-2 predicate `[rec+8]` over side0..1 x zone0..10, skipping zones with `[+0x44]` bit 21; brackets with counter pair `0x0229AB7C+0x10/0x14`);
  `0x021D2C1C(desc)` acting-zone check (loc from `0x021A241C(desc[+0xC])`; zone<=4: flag bit26 clear && desc[+0xE]==2-bit field of acting word && occupied u16 `[0x0229ACD0+S+Z]`; zone 5..10: occupied word);
  `0x021A220C(ref)` packed-ref -> locator (field (zone<<8)|side; lists GY 0xE/banished 0xF/deck 0xD/extra 0xC/hand 0xB with index<<16; not found 0x1000). Body pinned by SHA-256 + return-site constants.

## Subagent batch 2026-10-18 (4 agents, blocks checked in isolation then merged one at a time)
Merged (all VERIFIED, bodies pinned): `0x022349B0` pick validate, `0x02234904` pick accessor, `0x021A3320` zone card resolve (CORRECTS the old hypothesis fact, now `corrected_by`; head = u16 [Z+0x3E], walk keys 0x1A74/0x221E/0x1E7E/0x1F5B + acc keys, substitution tree 0x0EA9/0x19A6/0x19BC/0x1BC7/0x1C1B/0x1E6C/0x2269; zone>4 specials 0x0ECD/0x2150/0x21EF),
`0x021A1584` chain find key, `0x021AC204`/`0x021AC0C8` field cid counts, `0x021A241C` key->field locator, and D: `0x021F0384`, `0x021A2510`, `0x021ABFA8`, `0x021C48DC`, `0x021ACF68`, `0x0224BA34`, `0x021D2D18`.
Skipped as duplicate: agent B's `0x021A32B4` fact (already `engine.zone_active_presence_0x021A32B4`). `0x021B8D90` already had `stat.live_race_mask_0x021B8D90`.
Process note: subagents share one scratchpad and overwrote each other's helper scripts; give each its own subdir next time. Merge via single-index splice (merge_block.py), `--check` after each.

## Probe-card traces 2026-10-18 (static decode, NO in-game claims)
Four agents traced the handler paths of the puzzle probe cards; call trees + narratives: `notes/pot-of-greed-trace.md`, `notes/monster-reborn-trace.md`, `notes/mst-trace.md`, `notes/trap-hole-trace.md`.
23 new VERIFIED facts merged (draw path 8, Monster Reborn 5, MST 7, Trap Hole 3). Fired-function status after this: KNOWN 120, PARTIAL 319, UNKNOWN 408, HANDLER 1 (728 left of 848).
Shared findings: MST and Trap Hole share resolver 0x02204899 -> destroy body 0x02204674 (pick 0, no card constants); they differ only in the +08 predicate and +14 target step. Trap Hole's 1000-ATK arm is in predicate 0x021DB0A8 (via 0x021B8014 result >= 0x3E8; that out+0x10 is ATK is NOT proven).
Open: who posts the selector-0 descriptor to a Set trap on summon (02265768 posts to cls1; candidates 0x021D333E/0x021D33A4/0x021E50FA/0x021E561A/0x021E9262/0x021F0BB2); MST's Spell/Trap filter is a zone test only (flag bit 10 meaning unknown); Pot of Greed mover body beyond its head.
