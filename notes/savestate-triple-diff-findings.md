# duel_one / duel_two / duel_three savestate triple-diff — findings

Session 2026-09-20. Files: `data/over_the_nexus/working/duel_{one,two,three}.mln`
(19,301,495 B each, melonDS, main RAM at file offset **0x24** in all three).
Tooling: ad-hoc scripts in the session scratchpad; structure map from
`otn_enhanced/docs/engine/ram_layout.yaml` + `duel.phase_and_turn_player`.

## Confirmed (measured this session)

### Overlays resident
All three: **overlay 3** (0x02141700, 0x152CE0 + 0x31520 bss) and **overlay 5**
(0x022C5900, 0xE4820) are resident, and both match
`data/over_the_nexus/working/rom_all_patches.nds` **byte-for-byte** (ov3 image
1,387,744 B: 0 diff bytes vs the ROM; ov5 image 935,968 B: 0 diff bytes).
Against stock `rom.nds` ov3 is 98.5% / ov5 is a different length, so all three
states are from the **combined-build ROM**, in a **normal duel** (overlay 41 is
not loaded, so ov5 is resident and the cave is live).

### Identical across all three
- LP: `player+0x00` = 8000 for both sides in all three.
- Turn player `[0x0229DD14+0x34]` = **1** (opponent), turn counter `[+0x40]` = **0**
  in all three → all three are turn 1 of the duel.
- Both fields empty: 0 monsters, 0 S/T, GY count 0, banished count 0, both sides.
- Hand sizes 5 (side 0) / 6 (side 1) in all three.
- **The player's (side 0) deck is the same 40-card main deck and the same
  12-card Extra Deck in all three** — identical multisets; only the shuffle
  order of `player+0x304` differs.
- The **ov5 cave** (0x0239A120–0x0239FDD0, 23,728 B): **0 differing bytes**. No
  patched-card runtime state in any of the three.
- ov3 code/data image: the ONLY differing byte inside it is 0x0228FA60 (below).

### Differences that are NOT "different hands / different opponent deck"

1. **duel_three is at the opponent's MAIN PHASE 1, not the Standby Phase.**
   `[0x0229DD14+0x48]` (KB `duel.phase_and_turn_player`, 2=Main1 / 3=Battle /
   4=Main2 / 5=End) reads **1, 1, 2**. The phase-handler table 0x0226D2B0 has
   9 live entries (0..8, index 2 = NULL because Main1 is interactive), so
   phase 0/1 are Draw/Standby; the opponent has already drawn (6 cards) in all
   three, so phase 1 = Standby. **duel_one and duel_two are at Standby; duel_three
   has already advanced into Main Phase 1.**

2. **A cluster of "one == two != three" state variables** corroborates (1):
   | address | one | two | three | note |
   |---|---|---|---|---|
   | `0x0229DD14+0x74` | 2 | 2 | 3 | duel-state |
   | `0x0229DD14+0x7C` | 0 | 0 | 2 | duel-state |
   | `0x0229DD14+0x80` | 0 | 0 | 0x0A | duel-state |
   | `0x0229DD14+0xD8` | 1 | 1 | 0 | duel-state |
   | `0x0228FA60` | 8 | 8 | 5 | ov3 .data **scene/sub-mode byte** (label from `ygo_tools/tools/ai_trace.py:48`); ROM image value is 9 |
   | `0x02299B60` | 0x800B | 0x800B | 0x800C | animation/replay queue opcode (`event.animation_command_queue`) |
   | `0x022C4154` | 2 | 2 | 4 | ov3 .bss |
   | `0x0229ABA8` / `0x0229ABB4` | 6 / 1 | 6 / 1 | 8 / 2 | ov3 .bss counters |

3. **The opponent's EXTRA DECK differs too** (15 cards each, `player+0x4E4`),
   not just the main deck — three completely disjoint lists.

4. **Three different opponents; two are stock CPU decks, one is not.**
   Matching the side-1 40+15 multiset against the 305 decks in
   `Data_arc_pac/deck.pac` of `rom_all_patches.nds`:
   - duel_one  → `wcs003_hyupuno.ydc`, **55/55 exact** (Sunlight Unicorn /
     Hypnocorn / Closed Forest / Koa'ki Meiru Urnight).
   - duel_two  → `wcs057_redame.ydc`, **55/55 exact** (Red-Eyes Darkness Metal
     Dragon / Masked Dragon / Blizzard Dragon).
   - duel_three → **no match at all** (best score 19/55). It is a
     Quickdraw/Junk Synchron deck whose Extra Deck holds Shooting Star Dragon,
     Red Nova Dragon, Formula Synchron, Majestic Star Dragon, Daigusto Sphreeze,
     Ignition Beast Volcannon, **Scarred Warrior 0x2338** (Hyper Librarian's
     donor) and **Meteor B. Dragon 0x126F** (Accel Synchro Stardust's donor);
     its main deck holds **Shapesnatch 0x13AE** (Assault Synchron's donor),
     **Boneheimer 0x13B6** (Mathematician's donor) and **Breath of Light 0x123D**
     (Soul Charge's donor). So duel_three's opponent is running a
     **save-file / patched-donor test deck, not a ROM CPU deck**.

5. **duel_one and duel_two were launched from the identical game context;
   duel_three was not.** The 2D-resource cache at ~0x02112000 holds a set of
   asset names: duel_one and duel_two hold the **same 842 names, byte-identical**
   (0.00% differing bytes over 32,762 B); duel_three holds **963** names — a
   superset containing 121 extra entries that are **player-avatar assets**
   (`f_hair01_l.lznclr`, `m_hair08_l.lznanr`, … 0..9 prefixed variants) plus
   `card_5bg64x64.bin` / `card_5bg24x32.bin` / `card_5bg24x32_idx.bin`.
   The duel stage/field assets are the same set in all three.
   Same story in the 246,936 B heap block at 0x020C7254 (a **sound heap**: the
   first record carries an `SSEQ` magic): duel_one vs duel_two = **0.06%**
   differing bytes, but duel_three differs from both by **98%** and its record
   length differs (0x40A0 vs 0x1FE0).

6. **RNG state differs in all three** (expected, but worth recording):
   `[0x0229DD14+0x24]` = 0x25B16345 / 0x9E92E6F4 / 0x68F3FF19, and an ARM9
   global at 0x020AEFD8 = 0xC44B19AC / 0x7E802864 / 0xD48ECD80.

### Diff budget
371,945 bytes (8.868% of main RAM) differ three-way, in 82 regions (gap 256).
Accounting: ~280 KB is the audio heap + resource cache from (5); ~12 KB at
0x020BD600 is an audio/PCM working buffer (≈99.4% differing between *every*
pair); ~1.4 KB at 0x022945F4 is the ov3 BSS sprite/tile allocation table; the
card-instance heap 0x022967C8–0x02297030 and the sorted deck-list mirrors at
0x02299204 and 0x0229C364 are byte-for-byte re-expressions of the hand/deck
contents; the player structs contribute only their hand (`+0x124`), deck
(`+0x304`) and Extra-Deck (`+0x4E4`) arrays.

## Ruled Out
- Different ROM / different build between the states — ov3 and ov5 images are
  identical to each other and to `rom_all_patches.nds`.
- Different LP, field state, GY, banished zone, turn number, or turn player.
- The player's own deck or Extra Deck differing — same 40 + same 12 in all three.
- Any patched-card cave state differing — the ov5 cave is byte-identical.
- Puzzle mode — ov5 is resident, so overlay 41 is not loaded in any of them.

## Open Questions
- What exactly distinguishes duel_three's launch context (which menu / duel mode
  loads the avatar-hair assets and a save-file opponent deck)? Only the user can
  say what they did differently.
- `0x0228FA60` is labelled "scene/sub-mode byte" in `ai_trace.py` but its value
  space (ROM 9 → runtime 8 / 8 / 5) has never been enumerated.
- `0x02299114` = 0x0C7D / 0x0B4C / 0x073A (the most-referenced ov3 global,
  `DUEL_CTX` in `ai_trace.py`): varies in all three; meaning of the low word
  unknown.

## Next Experiment
If the launch-context question matters: capture two savestates from *known*
different entry points (e.g. Free Duel vs. Story/World duel) at the same phase
and diff `0x0228FA60`, the resource-cache name set, and whether the avatar-hair
assets are present. That pins the scene-mode byte's value space in one pass.
