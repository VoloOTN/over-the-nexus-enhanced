# CPU-vs-CPU battery (otn_enhanced/tools/cpu_battery) — findings

## Confirmed (2026-11-03, this session)

- **Mailbox rig works on rom_all_patches.nds:** 2 duels played back to back in one melonDS boot. Both reached
  `state 3` and `seq` advanced 0→1→2. Results are in `build/cpu_battery/results*.jsonl`.
- **The card prop / intid tables are loaded on demand, not at boot.** The rig's first build aborted:
  - savestate `build/cpu_battery/w0/battery.ml1` showed CPSR 0x97 (abort mode);
  - `R6` was `rig`; banked LR 0x02029ED1 was the caller of `card_index` 0x02029E1C;
  - `[0x02121A6C]` (the DB struct) was 0x027E33F0, but `[+0x3C]` (the intid table) was 0.
  - The game itself brackets uses with check/load/free: `0x0202BB14` / `0x0202BAC8` (+0x38 prop) and
    `0x0202BB78` / `0x0202BB2C` (+0x3C intid). See the pattern at 0x0202DA4A and 0x0202DCCE.
  - Calling the loaders in `launch()` fixed it.
- **The duel-exit callback literal is ov3 `0x02146518`** (stock 0x02019359). Pointing it at `rig_boot` returns
  control to the rig after the spectator duel. No result-screen hook is needed: View Mode's `vm_result_panel`
  skips the panel.
- **Outcomes are deterministic for a given seed:** identical LP and winner on the 8-pass build and on the
  32-pass + busy-break + skip-anim build:
  - `default_jf` vs `rpg001_0_syoki`: LP 5600 / 0
  - reverse seating: LP 0 / 3550
- **Wall time per duel, 1 worker, JIT off:**

  | Build | default_jf vs rpg001_0_syoki | reverse |
  |---|---|---|
  | 8 passes | 165 s | 337 s |
  | 32 passes + busy-break NOP @0x021460E8 + 5 skip_animations cases | 126 s | 298 s |

  These are one sample each, with three variables changed at once. They do NOT show which change helped.

### JIT path (2026-11-03)

- **GDB + JIT does not work in melonDS 1.1.** With `[JIT] Enable = true` the host connected to the stub, but the
  emulator stayed stopped after halt/continue and showed a white screen. User savestate
  `w0/battery.ml1` @10:55: `booted=1`, `state=0`, so the host never armed it. Ruled out as a channel.
- **The game reformats a save with no valid ID at boot.** It writes its header `wcs201100002…` plus default data
  from offset 0, so a blank 0xFF save loses anything written there.
  - In a formatted save, 0x0684–0x8500, 0x8504–0xB838 and 0xB83C–0xEF5C are 0xFF.
  - `body_save` writes its two 0x3338 B bodies at 0x8500 / 0xB838 (CardWorkshop labels).
- **The save-file channel works with the JIT on.**
  - The host writes ≤48 pairings at save 0x1000 into a copy of a game-formatted save
    (`build/cpu_battery/formatted.sav`) and boots melonDS.
  - The rig reads each pairing with `backup_read` 0x0202BBD0 (offset, dst, size) and writes each result back with
    `backup_write` 0x0202BB90 (offset, src, size).
  - melonDS flushes `battery.sav` to disk and the host polls the file.
  - Smoke result: the same two duels gave identical results to the GDB builds (LP 5600 / 0 and 0 / 3550),
    in **58 s / 114 s**, against 126 s / 298 s for JIT off with the same ROM patches.

### Turbo vs regular (2026-11-03)

- **Turbo Duel config, from savestates `rom_ov5_canary.ml1` (normal) and `.ml2` / `.ml4` (turbo / tag-turbo):**
  `[0x020B8808]` = 4 and `[0x020B880C]` = 3 in a Turbo Duel, against 0 / 0 in normal and tag duels.
  Menu id `[0x020B8F3C]` is 0x2002 for turbo and 0x2001 for normal.
  `duel_mode_reset(arg0, arg1)` at 0x02018E6C writes arg0 → 0x020B8808, 0 → 0x020B880C and arg1 → 0x020B8838.
- **The rig launches turbo pairings with `duel_mode_reset(4, 1)`, `[0x020B880C]=3` and menu id 0x2002.**
  - At duel end both turbo games read 4 / 3, and the regular pair reads 0 / 0. The regular results were unchanged
    (deterministic).
  - **User confirmed in this session (2026-11-03) that the turbo pair played as Turbo Duels:** "Just to confirm
    that those duels WERE turbo duels".
- **Turbo deck = a deck with any "Speed Spell" in its Main Deck:** 84 of 305. All `*_rd`, `rtlr*` and
  `wrd*` decks qualify; the `_rd` / `rtlr` name pattern alone misses the 40 `wrd*` decks.
  Same-kind pairing gives 221·220 + 84·83 = 55,592 duels.
- **Speed World 2 (cid 3400) is not a card in any zone of the turbo savestate.** Turbo is engine state, so a
  field-zone check can't detect it. Zone 12 in story.c's zone numbering is not the field zone.

### Duel command opcodes (probe 2026-11-03)

How it was measured:
- The rig replaced the head of `0x021C3BC8` (KB `event.animation_command_queue`) with a C copy that does the same
  append and logs every call. The head patch is CardWorkshop's `bx pc ; nop ; ldr pc,=fn` over `CMD_PUSH_HEAD`.
- One duel was logged (rpg001_0_syoki vs default_jf), with turn, phase, side, deck and hand counts per entry.
  Refs were mapped to cids through both player structs dumped at duel end.
- 1,203 entries, none dropped. Duel results were identical to every non-probe build, so the replacement is
  behaviour-neutral. Saves: `build/cpu_battery/probe_rpg001_vs_default_jf.sav`, `probe2.sav`.

Op bit 15 = side. Ref = `((word & 0x7FFFFFFF) >> 23) * 2 + ((word >> 14) & 1)`, as in story.c.

| op | meaning | card | evidence |
|---|---|---|---|
| 0x56 | draw, b = count (opening hand: a = 0xFFFF, b = 5) | **not in the entry; it is `deck[0..b-1]` at push time** | deck count drops after it 49/49; newest hand card == pre-draw `deck[0]` in 47/47 single draws (probe2) |
| 0x2B | Normal Summon face-up (incl. Tribute) | a = cid | Armored Bee, Alien Shocktrooper, Zaborg, Gale… |
| 0x2C | Special Summon | b = ref | Black Rose / Magical Android / Gaia Knight / Brionac Synchros; Quickdraw Synchron; Gravekeeper's Spy from Deck; Quillbolt Hedgehog from GY |
| 0x2D | effect activation (Spell / Trap / monster) | b = cid, c = ref | MST, Mind Control, Bottomless, Shield Crush, Call of the Haunted, Armored Bee, Gravekeeper's Spy |
| 0x50 | monster from hand to a monster zone; b: 0x8000 set, 0x4000 face-up, low bits = zone | a = cid | Giant Rat set, Armored Bee summon |
| 0x51 | Spell/Trap from hand; b: 0x4000 activated face-up, else Set | a = cid | |
| 0x52 | card added from Deck to hand by an effect (search, not a draw) | a = ref | deck −1 / hand +1 twice |
| 0x4E / 0x4C / 0x4D | Synchro Summon / its materials | a = cid | 6 Synchros |

**Flip Summon (mapped 2026-11-03, probes `probe_flip_rpg021_7_seria_vs_wcs021_zakka.sav` / `…_wcs077_gallis.sav`,
FLIP-heavy decks):**
- **A Flip Summon is 0x2B with c = 1; a Normal Summon is 0x2B with c = 0.** Over 3 logged duels: 19 × c=0, each
  right after a 0x50 (from hand); 10 × c=1, each right after `0x33 (a = zone, b = 1, c = 1)` (position change),
  all in Main Phase 1 by the turn player, each preceded by `0x61 … c = 4` (likely the action-menu choice).
- 7 of the 10 cards had been Set from hand (0x50 with 0x8000). Dark Grepher was Set by The Shallow Grave.
  Brionac and Caius had been turned face-down by Book of Eclipse.
- **Battle flips are not summons and emit no 0x2B:** `0x62 (a = cid, b = 1)` in the battle phase.
  `0x62 b = 0` follows a Flip Summon only for monsters with a FLIP effect, then 0x2D for that effect.
- So the SUMMONED counter (0x2B + 0x2C) already includes Flip Summons, and excludes battle and effect flips.
  No rig change was needed.

KB: `event.cmd_queue_draw_summon_activate_opcodes` (ANCHORED). Its proof re-reads `probe2.sav` and passes.

### Per-card counters (2026-11-03)

- The production rig always replaces `0x021C3BC8` with the C copy, and in a duel it tallies per side, per deck
  slot: drawn (0x56 → `deck[0..b-1]`), summoned (0x2B cid + 0x2C ref→cid) and activated (0x2D cid).
  Counts are u8, saturating.
  - Ref→cid scans that player's struct for a card word whose ref matches.
  - A cid not in that side's deck (e.g. a Mind-Controlled monster) is not counted.
- `battery.py report` writes `build/cpu_battery/card_stats.csv` (deck, card, cid, duels, drawn, summoned,
  activated).
- Batch is now 24 pairings: result records are 608 B and the save range is 0x1000–0x5DD0.
- Sanity check on 4 duels: drawn ≤ (Main Deck size − cards left) on every side. The gap is searches and mills;
  Quickdraw Synchron was summoned 2× and drawn 0×, being searched by Tuning.
- Results stayed identical to every earlier build.
- **Bug fixed along the way:** the builder wrote `story_config` at a hard-coded struct offset. When the result
  struct grew, launch called garbage and aborted (user savestate 11:37, CPSR 0x97, LR inside `rig_boot` after
  `blx [rig+0x408]`). It is now its own symbol, `rig_story_config`, patched by name.

### Throughput levers (2026-11-03)

- **Full run, 6 workers, JIT on, software 3D renderer: ~160–170 duels/hour** (45 duels, all `done`). Hardware:
  i7-7700HQ, 4 cores / 8 threads, 32 GB. Each melonDS worker keeps ~1 thread busy (790 CPU-s in ~14 min) and uses
  ~315 MB.
- **`--gl` (OpenGL 3D renderer) is SLOWER: ~45–50% more wall time per duel** at 2 workers
  (60→86, 54→90, 76→114, 122→180 s), with identical results. Not used. Possibly the Intel iGPU via Optimus;
  not investigated.
- The JIT is already at melonDS's maximum (`MaxBlockSize = 32`, literal/branch optimisations, FastMemory).
  `LimitFPS = false`, so `TargetFPS` has no effect.
- **Turns = `duel[16] + 1`.** Word 16 of the captured block is 0x0229DD54, the 0-based index of the current turn.
  In 3 probe duels it ended at 45 / 8 / 15, with 46 / 9 / 16 turn-start ops (0x02) logged. It counts both
  players' turns.

### Tournaments (2026-11-03)

- **`tournament.py`:**
  - Swiss with best-of-5 matches; the first player alternates (odd games put the higher-ranked deck on side 0).
  - Rounds default to ⌈log₂ N⌉: 8 for 221 regular decks, 7 for 84 turbo decks.
  - Single-elimination top cut (`--cut`, default 32) seeded 1 v N.
  - Scoring 3/1/0. Tiebreaks: OMW% (floor 1/3), then GW%, then a seeded hash.
- **History lives in tracked `data/cpu_tournaments/<id>/`:** `meta.json` (settings, deck list, source + battery ROM
  sha256), `games.jsonl` (every game with stats and turns), `standings.md`, `bracket.md`, `card_stats.csv`,
  `card_stats_by_deck.csv` and `summary.json`. Each finished tournament also appends one line to
  `data/cpu_tournaments/history.jsonl`.
- **Resuming:** state is a pure function of `games.jsonl`, so a re-run resumes. A run refuses to continue if
  `battery.nds` changed.
- **Checks:**
  - `tournament selftest`: full fake tournaments at 221/84/9 decks.
  - A 4-deck emulator test, 2 rounds + Top 2: 21 games, all `done`.
- **`card_stats.csv`** is per card across decks (duels, drawn, summoned, activated), sorted by summoned then
  activated. The per-deck version is `card_stats_by_deck.csv`.
- **Match length (2026-11-03, user request): Swiss best of 3, top cut best of 5** for new tournaments.
  - `meta.json` records `swiss_best_of` / `cut_best_of`; flags `--swiss-bo` / `--cut-bo`.
  - Tournaments started earlier recorded one `best_of`, used for both stages, so `2026-11-03_regular` /
    `_turbo` replay and finish as Bo5 throughout. Their logs were checked through the new code: read as {5}.
  - Verified by the selftest and an end-to-end fake-worker run: Swiss matches 2–3 games, cut 3–5.
- **Scheduling (2026-11-03, user request): one worker plays one Bo5 match at a time.**
  - Before: each stage was played in waves of pre-assigned batches of up to 24 games per worker (`battery.play`).
    The user saw only 4 of 6 workers busy at the end of waves.
  - Now `tournament.play_matches` queues matches. A worker plays what its match needs in one boot, re-checks it,
    plays game 4/5 if needed, then takes the next match.
  - The only barrier left is the end of each Swiss/bracket round, since pairings need every result.
  - Selftest: a fake-worker tournament completes in exactly one pass per stage, with no game played twice.
  - The game log and ROM are unchanged, so the restart resumed from the log.
- **Crash fixed 2026-11-03:** writing `card_stats.csv` raised UnicodeEncodeError, because Windows' default cp1252
  can't encode `\x90`. The game's text uses byte 0x90 for "∞" in the Meklord Emperor names (Wisel / Granel /
  Skiel ∞). CSVs are now written as `utf-8-sig` and 0x90 is mapped to ∞.
  - The regular run had died after round 1's first wave of 330 games, and the script went on to turbo (49 games).
  - Restarting the script resumed both with no games lost.
- **Started 2026-11-03 12:47:** `build/cpu_battery/run_tournaments.ps1` runs `2026-11-03_regular`, then
  `2026-11-03_turbo`.
- The round-robin is paused at 65 duels in `build/cpu_battery/results.jsonl`; `battery run` resumes it.

### Ratings (2026-11-03)

- **`tournament ratings`** writes `data/cpu_tournaments/ratings/<build12>_<pool>.md` / `.csv`.
  - One table per ROM build (the battery sha256 recorded in each tournament's `meta.json`) and per pool.
  - **Built from tournament games only** (user decision 2026-11-03). Round-robin results are not rated.
- **Model:** Bradley–Terry, P(side 0 wins) = σ(s_a − s_b + h), fitted to all games at once (no order effects).
  - Newton MAP with a weak Gaussian prior (precision 0.1) so undefeated decks stay finite; ±95% from the inverse
    Hessian.
  - Elo scale: 1500 mean, 400/ln 10 points per logit.
  - Undecided games score 0.5; hangs and crashes are dropped.
- **Selftest** (synthetic 40 decks, 4,000 games): rank correlation 0.973 with the true strengths, h 0.35 against a
  true 0.30.
- A tournament refreshes the ratings when it finishes. The regular run already in progress runs the old code, so
  its ratings refresh comes when the turbo run finishes.

### Where duel time goes (experiment 2026-11-03)

How it was measured:
- Experiment build `battery build --frames --out build/cpu_battery_exp/…`.
- `rig_frame` replaces the per-frame pad read at 0x020162E6 / 0x0201634C (w11speed h_pad) and counts frames.
- 6 logged tournament games were replayed with 1 extra worker in its own folders.
- The control build is byte-identical to the tournament ROM (`388cdff3…`).

Results:
- **Duels are presentation-bound:** 6/6 games came out identical, and **88% of frames had a duel command queued or
  running** (`[0x0229A368]` / `[0x0229DE28]`). Workers ran at ~30 fps beside the 6 tournament workers.
- **Frames by current command op** (`[0x02299B60] & 0xFFF`): 0x16 battle 22%, 0x31 15%, 0x55 shuffle 13%,
  0x4E Synchro 10.5%, 0x30 destroy/send-to-GY 10%, 0x32 banish 5%.
- **Mechanism, from the shuffle handler 0x021C0BB4:**
  - Step 0 does the state change: the shuffle, via View Mode's wrapper at 0x023DEDD4.
  - It then starts presentation code 0x15 with `0x0219C99C`.
  - Step 1 polls **`0x0214B490(code)`**, which returns 1 while that code is still playing. It then posts 0x16 and
    clears the in-progress word `[0x0229A360+0xC]`.
- **The drain** (0x021C3C3C, called from the state machine at 0x021C3FB8 on `[0x02298E58+0x44]`) stays busy
  while `[0x0229A360+0xC]` != 0. Jump table: target = 0x021C3C60 + s16 at 0x021C3C5E + 2·op.
  - Handlers: 0x16 → 0x021BB6A0, 0x31 → 0x021BEEC8, 0x4E → 0x021C2914, 0x30 → 0x021BE83C.
- **`0x0214B490`:** 97 callers, all ov3. A 0x4E-case switch per code when `[0x020B7C8C+0xF54]` == 0; the
  fast-forward path otherwise.
- **STRIKE 1: making `0x0214B490` always return 0 (`--no-wait`) HANGS duels.**
  - The first 2 games finished within ~40 s of boot (baseline 38 + 50 s), with 1–3 frames per command op.
  - Game 3 (`s1/rtl011/rpg023_4_rossi/g1`) stalled with the emulator running at 59 fps. The relaunched batch
    also made no progress.
  - Outcome identity of the 2 fast games is unknown: the relaunch overwrote the save.
  - So at least one caller needs the real answer.

- **STRIKE 2: skipping only the shuffle handler's wait also HANGS.**
  - Build: `--skip-wait 55`, which points the 0x0214B490 poll at 0x021C0C3A (inside 0x021C0BB4) to a rig stub
    returning 0.
  - 4 of the 6 replayed games were identical to the log, but **2 hung**: `s1/wcs012_winda/rpg054_6_hana/g1` and
    `s1/sd05_soldier/wcs071_ka2/g1`.
  - The user watched one freeze during a shuffle (2026-11-03): "See savestate - it froze during a shuffle".
  - The finished games were not faster (34/58/64/112 s against 38/58/66/124 s).
  - Unproven guess: posting 0x16 while presentation code 0x15 is still on screen leaves something waiting on a
    screen state that never comes.
- **Per the two-strike rule, stop patching presentation waits.** The next step is measurement: what the stuck
  duel waits on, from the user's savestate.
- `--skip-wait` / `--no-wait` / `--frames` are experiment-only flags; the default build stays byte-identical to
  `388cdff3…`.
- **8 vs 32 duel-loop passes makes no wall-time difference (measured 2026-11-03).**
  - Same 6 games, frame-counting builds, 1 worker beside the 6 tournament workers.
  - CardWorkshop-style 8 passes with the busy break kept (`--no-anim 8 --keep-busy-break`): 6/6 identical, 488 s,
    20,127 frames at ~41 fps.
  - Ours (32 passes, busy break NOPed): 6/6 identical, 483 s, 14,308 frames at ~30 fps.
  - More passes give fewer but proportionally heavier frames. Per-game times differ by a few seconds either way.
  - **Conclusion:** a duel costs roughly a fixed amount of emulated ARM9 work, however it is spread over frames.
    That also fits the shuffle-skip games not getting faster.
  - The levers are less emulated work per duel or more host cores, not frame pacing.
  - The battery stays at 32: the tournament ROM `388cdff3…` uses it, and changing it buys nothing.

### Removing animations at the interpreter (2026-11-03)

- **The frozen shuffle-skip duel was a CRASH, not a wait.** Savestate `build/cpu_battery_exp/w0/battery.ml1`
  14:02:57: rig code matched the `sw55` build, CPSR 0x97 (abort), LR_abt 0x0216662C (ARM user mode).
  - The fault is around 0x02166624/28, in a presentation routine indexing a table by (`ip − 0xC`) and calling
    0x02152280.
  - R6 = R9 = 0x022956C4, the 3rd frame-loop presentation context (pool 0x0214620C), whose first 12 words were
    all 0.
  - Letting logic run past an unfinished sequence corrupts the presentation state.
- **Busy polls of 0x0214B490 per presentation code** (`--frames` build: all 96 Thumb poll sites routed through
  `rig_present_poll`; 6/6 identical; 384,092 busy polls): 0x0D 22.9%, 0x20 15.4%, 0x15 13.5%, 0x3A 10.8%,
  0x1F 10.1%, 0x21 5.1%, 0x3C 5.1%, 0x05 4.1%.
  - These match the command-op shares one-to-one: 0x16 battle → 0x0D, 0x31 → 0x20, 0x55 shuffle → 0x15,
    0x4E Synchro → 0x3A, 0x30 → 0x1F.
  - The codes `skip_animations` already removes (0x1E, 0x22, 0x2C, 0x38, 0x39) show **0** busy polls, consistent
    with interpreter case N = presentation code N.
- **H3 WORKS: route interpreter cases 0x0D, 0x20, 0x15, 0x3A, 0x1F to the epilogue 0x02148C50**
  (`--skip-codes 0d,20,15,3a,1f`, the `skip_animations` precedent: the sequence never starts, so nothing waits).
  - **6/6 identical, 0 hangs.**
  - Frames per 6 games 14,301 → 5,299 (−63%).
  - **Head-to-head with baseline, same 6 games side by side under equal load: 557 s → 459 s (−18%).**
- **Why only 18%:** the remaining frames got ~2.5× heavier (26 → 12 fps). Most of a duel's emulated ARM9 work is
  duel logic + CPU AI thinking, not animation. Even removing every animation would likely stay well under 2×.
- **Not yet adopted:** validated on 6 games only. The tournament ROM `388cdff3…` is unchanged.
- **Timing caveat:** single-run wall times swing ~2× with tournament load (the same 6 games took 265 s, 447 s and
  557 s on different runs). Only side-by-side runs are comparable.

- **Gauntlet (2026-11-04):** `uv run python -m otn_enhanced.tools.cpu_battery.gauntlet run DECK [--duels N]`
  plays one deck against its pool, in rounds (each round meets every opponent once, in a shuffled order; the
  seat alternates per opponent, so two rounds give one duel each seat). It writes to
  data/cpu_gauntlets/<date>_<deck>/, and it resumes; a larger --duels extends the run. Reports: win % vs the field, a percentile from a
  Bradley-Terry fit over the gauntlet plus the tournament games on the same battery ROM sha and pool (none
  -> no percentile), first/second split, by-opponent table, and card_stats.csv for the deck's cards only
  (card_stats(only=)). Fake-worker e2e passed (resume/extend without duplicates, seat balance).

## Open Questions

- Where the wall time goes. User observation 2026-11-03: "animations like banish, tribute, synchro are still
  slow and i think some summon animations still play". Those animations are not among the 5 skip_animations
  commands, and they evidently are not stepped per sub-pass.
- Emulated speed: how many rendered frames per second melonDS reaches here with JIT off.

## Next Experiment

- Measure before patching further: frames per duel and emulated FPS. Get them by reading a frame counter at
  duel start and end in the rig, and by PC-sampling during a banish/synchro animation (the method in
  notes/battle-speed-ar-findings.md "Next Experiment").
