# Dueling AI — findings

## ROUND 14 (2026-09-20) — seat controller, per-cid AI knowledge lists, recipe duels

Static only (ov3 image of `rom_all_patches.nds` + five savestates: `duel_one`,
`duel_two`, `duel_three`, `moja_opp_turn`, `gyzarus_opp_turn`, plus `moja`,
`gyzarus`, `gyzarus_my_turn`, `normal_duel`, `puzzle` for the seat-mode read).
No GDB was used and none was needed.

### Confirmed — `0x021D6D34` is a 6-way priority cascade (re-verified byte for byte)

```
A = 0x0229AAFC (action ctx)          B = 0x0229A9FC (queue ctx)
C = 0x0229DD94                       D = 0x0229ABFC (AI phase ctx)

0x021D6D34  if [A+0x6C] != 0            -> return 0            ; busy/blocked
            if [A+0x5C] != 0            -> 0x021D3E78()        ; sub-dispatcher
            if [A+0x64] != 0            -> 0x021D49D4()        ; EXECUTOR
            if 0x022481C0() != 0        -> return 1            ; REACTIVE rule scan
            if [B+0x54] != 0            -> 0x021D6B44()        ; queue compactor
            [C+0x20] = 0
            if [D+0x60] != 0            -> 0x0223A1C4()        ; PHASE SCHEDULER
            return
```

So the reactive 181-rule table (`0x022481C0` -> `0x02275510`) is tried **before**
the proactive phase scheduler every frame, and both are below the executor.

### Confirmed — `0x0223A1C4` is a 4-state phase machine, and the worker is `0x02239EF0`

State variable `[0x0229ABFC+0x5C]`, bounded `cmp r0,#3 ; bhi`, PC-relative
halfword jump table at **`0x0223A1DA`** (base `0x0223A1DC`, offsets
`0x0006 / 0x0056 / 0x007A / 0x0084`):

| state | arm | body |
|---|---|---|
| 0 | `0x0223A1E2` | `0x0219D198()` busy-check; `0x021A1430(0,0xB,0x1401)`; then `[0x0229AB9C+0x18]` in {3,5,0x18} -> state = 2, else state++ and fall into the worker |
| 1 | `0x0223A232` | `0x02239EF0(0, [0x0229DD14+0x34])`  — the **turn player** |
| 2 | `0x0223A256` | state++ ; `0x02239EF0(0, 1 - [0x0229DD14+0x34])` — the **opponent** |
| 3 | `0x0223A260` | same as 2 |

⚠️ **Correction to round 8/13:** the generator reached from the scheduler is
**`0x02239EF0`**, not `0x0224B094`. `0x0224B094` has only two BL callers
(`0x0219DC0C`, `0x0223A186`) and its body indexes zone records
(`0x0229ACD0 + side*0xB3C + zone*0x14`, i.e. player+0x3C) and special-cases
Speed World 2 `0x0D48` — it is an activation/marking helper, not the move
generator. `0x02239EF0`'s five callers are `0x021D494A`, `0x021D497A`,
`0x0223A23A`, `0x0223A26C`, `0x0223A2C8` — the executor and the scheduler.

`0x02239EF0(r0 = descriptor-or-0, r1 = side)` is itself a state machine on
`[0x0229ABFC+0x58]` (jump table at `0x02239F18` for 0..0xB, plus explicit arms
for 0x14, 0x15, 0x1E, 0x1F).

### Confirmed — THE SEAT CONTROLLER MODE: `0x02299114 + 8 + side*4`

`0x02299114` is the duel context (298 ov3 literal refs, round 3). At `+8` begins
a **per-seat controller-mode array, stride 4**. Read at `0x02239F72`:

```
02239F72  ldr r0,[pc]   ; = 0x0229911C        (= ctx + 8)
02239F74  lsls r1,r6,#2 ; r6 = side
02239F76  ldr r0,[r0,r1]
02239F78  cmp r0,#1 ; bne -> ...              ; 1 = CPU  -> 0x0219E59C(8,side,1,0), state = 0x0A, return 0
02239F90  cmp r0,#2 ; bne -> ...              ; 2        -> state = 0x14
        (else, 0)                             ; 0 = HUMAN -> falls through to the prompt path
```

**Measured, all ten savestates: `[0x0229911C] = 0` (seat 0 = human) and
`[0x02299120] = 1` (seat 1 = CPU) — with NO exception, including the recipe
duel `duel_three` and the puzzle.** The same array is the "`0x0229911C` jump
table" gate already noted in `0x021D2FC4` and `0x022481C0` (round 9).

This is the `is_cpu` flag round 4 went looking for in the player struct and did
not find. Value 3 ("COM" in the tag-duel AR code) belongs to the *tag* control
context `0x02299414+8`, which is all zeros in every single-player state.

### Confirmed — the AI's PER-CID KNOWLEDGE LISTS (`0x0227113C` family)

Four sorted `u16` cid lists, each read from exactly ONE site, each through the
binary search `0x02022E14 contains_sorted_s16(r0=cid, r1=list, r2=count)` — the
routine PC sampling saw hot **only** on the AI's turn (round 2: 15 samples vs 0
at baseline). All four live inside **`0x022393CC`**, the per-cid AI switch:

| list | count | read at | what it is |
|---|---|---|---|
| `0x0227113C` | 0x13 = 19 | `0x022395BA` | cards the CPU knows to use on the **opponent's turn** (Threatening Roar, Effect Veiler, Formula Synchron, Red Screen, Array of Revealing Light, …) |
| `0x02271162` | 0x15 = 21 | `0x02239738` | **destruction responses** (Michizure, Chthonian Blast, Snake Whistle, Starlight Road, …) |
| `0x0227118C` | 0x16 = 22 | `0x0223989E` | **chain-related** (Chain Strike, Accumulated Fortune, Spell/Trap Reclamation, …) — inside the leaf `0x02239898`, callers `0x02239B9E` / `0x02239C3E` |
| `0x022711B8` | 0x30 = 48 | `0x0223961E` | **summon responses** (Trap Hole, Torrential Tribute, Bottomless Trap Hole, Needle Ceiling, Chain Disappearance, …) |

`0x022393CC(r0 = side, r1 = cid, …)` immediately forms `0x02299114 + side*4`
(the seat-mode pointer) and then runs a long per-cid compare chain plus these
four membership tests. **Five callers:** `0x0223983E`, `0x02239922`,
`0x022399AC`, `0x0224C8BE`, `0x0226A722`.

⚠️ The adjacent lists `0x0227109C` / `0x022710B2` / `0x022710CA` / `0x022710E2`
/ `0x02271104` are read at `0x02234EBA` / `0x02234EA6` / `0x02234ECE` /
`0x02234E7E` / `0x02234E92` — i.e. inside **`0x02234E78`, the shared card-effect
PARAM PROVIDER** (`otn-param-provider-internal-hook`), *not* the AI. Do not
confuse the two families; they sit in one contiguous data block.
(Note `0x02234E7E`'s lookup now BLs `0x0239D900` — this repo's own ov5 hook.)

**Consequence for this repo:** a patched/new card is in none of these four lists
(and in none of the 164 cids of the 181-rule table `0x02275510`), so the CPU has
no special-case knowledge of it. Adding a cid to a list is a **count-neutral
problem** — the count is an immediate (`movs r2,#0x13`) and the lists are packed
back-to-back, so growing one shifts the next. Editing an existing entry is free.

### Confirmed — the opponent's DUELIST IDENTITY never reaches the duel engine

The per-duelist profile block in the arm9 heap (~`0x020B6D00`, mirrored at
`0x020B8880`) holds, per seat:

| field | seat 0 (you) | CPU seat 1 |
|---|---|---|
| `0x020B6F04` | `0x2536B489` (your profile id) | — |
| `0x020B6F08` | — | `0x8000012F` Hypnocorn / `0x80000165` Dr. RED / `0x8000012D` Moja / `0x8000015D` Gyzarus — **bit31 set = CPU** |
| `0x020B6DDE` | — | duelist name string |
| `0x020B7019/23` | — | deck display name |
| `0x020B6F40` (28 B) | — | the **duelist roster id repeated 28x**: Moja `0x2F`, Gyzarus `0xA7`, Hypnocorn `0xAD`, Dr. RED `0xA0` |

**A 4-way constrained byte search over all 4 MB (one=0xAD, two=0xA0,
moja=0x2F, gyzarus=0xA7) returns exactly TWO runs: `0x020B6F40` and
`0x020B8B54` — both the 28-byte profile field.** The duelist id therefore exists
nowhere in ov3 `.bss`, the duel context, or the player structs. The duel
engine never learns *who* it is playing. This closes round 3's open question
"is there any AI parameter at all": **measured, there is none keyed on duelist
identity.** Per-opponent behaviour comes from the decklist and the board.

### Confirmed — what a RECIPE duel changes (and what it does not)

`duel_three` is a recipe duel. Compared with the two ordinary CPU duels:

- **Seat controller mode is IDENTICAL** — `[0x02299120] = 1` (CPU). Same AI.
- Seat 1's profile id is the **player's own** `0x2536B489`, not `0x800001xx`:
  the CPU bit31 is clear and there is no duelist roster id — `0x020B6F40` holds
  a user-ID string (`"…GKOYJMTY"`) instead of a repeated id byte.
- The per-seat scalars that are zero for a CPU seat are **populated for seat 1**:
  `0x020B6F14` halfword `0xDC`, `0x020B6F1C` halfword `0x421F`, and
  `0x020B6F94/98/9C` bytes `0x0E / 0x1F / 0x03` — all mirroring seat 0.
- The opponent's 40+15 deck matches **no deck in `Data_arc_pac/deck.pac`**
  (best 19/55), whereas `duel_one` = `wcs003_hyupuno.ydc` 55/55 and
  `duel_two` = `wcs057_redame.ydc` 55/55.
- Its heap still holds player-avatar assets (`*_hair*.lznclr/.lznanr`) that
  neither CPU duel loaded.

**=> A recipe duel runs the same AI through the same seat-controller path.**
Nothing measured in the AI's inputs differs except the decklist and the board.

### Confirmed (round 14g) — a SECOND family of per-cid lists lives in OVERLAY 5

Found by scanning arm9 (all sections) + all 50 overlays for one cid
(`scratch/cid_mention_scan.py`, aligned u16/u32 only). For Mirror Force 0x1317
on stock `rom.nds`: **ov3 x1** (its own effect record 0x0227F8DC), **ov5 x7**,
**ov7 x2** (both inside ARM instruction words -- incidental, not references),
arm9 **none aligned**, every other overlay none.

**THE ov5 LIST FAMILY.** `0x02347DD4(r0=cid, r1=list, r2=BYTE length, r3=flag)`
is ov5's own wrapper around the ARM9 binary search: `r4 = r2 >> 1` (so **r2 is a
BYTE count, not an entry count** -- read it that way or you double the list),
optionally `bl 0x022DBF2C` on r0 when r3 != 0 (a cid normalise / "treated as"
step the ov3 AI lists do NOT do), then `bl 0x02022E14 contains_sorted_s16`.
**133 call sites in ov5.**

Thin per-list wrappers sit in a block, e.g. around 0x0235AA28:

| wrapper | list | bytes | entries |
|---|---|---|---|
| 0x0235AA28 | 0x02397A50 | 68 | 34 |
| 0x0235AA50 | 0x0239705E | 12 | 6 |
| **0x0235AA64** | **0x02397602** | **46** | **23** <- holds Mirror Force |

The 23-entry list @0x02397602, sorted: Sangan 0FD6, Dark Hole 10F6, Raigeki
10F7, Swords of Revealing Light 1102, Cockroach Knight 1185, Witch of the Black
Forest 11E4, Harpie's Feather Duster 1246, Relinquished 1281, Toon World 12BE,
Monster Reborn 12EA, Pot of Greed 12EC, Change of Heart 12FC, Magic Jammer 12FE,
Seven Tools of the Bandit 12FF, **Mirror Force 1317**, Heavy Storm 131B, Destiny
Board 1468, Exchange of the Spirit 14F0, Van'Dalgyon 190A, Voltanis 1A28,
Felgrand Dragon 1C4C, Phantom of Chaos 1CB7, Genex Ally Reliever 2208.
A SECOND, SEPARATE sorted list starts at 0x02397630 and is 23 Dragon-themed
cards (Dragon Seeker, Lord of D., Buster Blader, Stamping Destruction, King
Dragun, REDMD, Trident Dragion, ...) -- so this region is a TABLE OF CATEGORY
LISTS, not one big list.

⚠️ **THE SEMANTICS ARE UNIDENTIFIED.** The membership is not the Forbidden list
(Magic Jammer, Seven Tools, Swords, Destiny Board, Van'Dalgyon, Voltanis,
Felgrand, Phantom of Chaos, Genex Ally Reliever and Cockroach Knight are not
banned) and it is not an archetype. Do not guess it. The sole caller of the
0x02397602 wrapper is **0x022D4428**, reached with r0 = a cid and r1 = 1, and a
HIT branches to 0x022D4386 while a miss falls through -- so identifying it is
one disassembly of what those two paths do.

⚠️ Note ov5 executes only ~0.5% of AI-turn PC samples (round 2), so this family
is NOT the AI's hot path, whatever it is.

### Confirmed (round 14f) — THE ORDER: the card-agnostic path is four nested machines

Decoded statically from stock `rom.nds` (`scratch/ai_worker_states.py`).

**LAYER 1 - per-frame priority cascade `0x021D6D34`** (ai.turn_controller_cascade):
blocked -> sub-dispatcher -> EXECUTOR -> reactive rule scan -> queue compactor ->
proactive scheduler. First arm that fires owns the frame.

**LAYER 2 - scheduler `0x0223A1C4`, state `[0x0229ABFC+0x5C]`, 4 arms** via the
halfword table at `0x0223A1DA`: state 0 pre-checks (`0x0219D198` busy,
`0x021A1430(0,0xB,0x1401)`, `[0x0229AB9C+0x18]` in {3,5,0x18} -> jump to state 2);
state 1 runs the worker for the TURN PLAYER; states 2 and 3 run it for the
OPPONENT. So both seats are walked, in that order.

**LAYER 3 - worker `0x02239EF0`, state `[0x0229ABFC+0x58]`** — THIS IS THE TURN'S
ACTION ORDER. Bounded `cmp r0,#0x15 / #0xB`, halfword jump table at
`0x02239F18` (add-pc base `0x02239F1A`) for 0..0xB, plus explicit arms for
0x14/0x15/0x1E/0x1F. **LIVE STATES: 0x00, 0x01, 0x02, 0x05, 0x0A, 0x0B, 0x14,
0x15, 0x1E, 0x1F. States 3, 4, 6, 7, 8, 9 and everything else fall to the common
return `0x0223A1A2` and do nothing.**

| state | arm | calls | writes next state |
|---|---|---|---|
| 0x00 | 0x02239F4A | `state += 1`, then falls straight into 0x01's body | 0x0A, 0x02 |
| 0x01 | 0x02239F4E | `0x022398C8`, `0x0219E59C` (CPU-seat post), `0x02239A30`, four UI posts, `0x02029E60` is_monster, `0x02239CCC` | 0x0A, 0x02 |
| 0x02 | 0x0223A006 | **`0x0226A75C` -> `0x022393CC` THE PER-CID AI SWITCH**, `0x0224B970`, `0x0219C430` | 0x0A, 0x01, 0x05, 0x1E, 0x00 |
| 0x05 | 0x02239F4E | identical body to 0x01 | 0x0A, 0x02 |
| 0x0A | 0x0223A01A | same 0x0226A75C / 0x0224B970 family + `0x0219EA68`, `0x02239270` | 0x01, 0x05, 0x1E, 0x00 |
| 0x0B | 0x0223A070 | `0x0219C430`, `0x0219EA68`, `0x02239270` | 0x05, 0x1E, 0x00 |
| 0x14 | 0x0223A0B2 | `0x021C3BC8` (animation/command queue), `0x0224B184` | 0x1E, 0x01 |
| 0x15 | 0x0223A0E0 | **`0x0224B094` / `0x0224B184` / `0x0224B224` / `0x0224B380`** | 0x1E, 0x01 |
| 0x1E | 0x0223A0FE | same 0x0224Bxxx family | 0x01, 0x05 |
| 0x1F | 0x0223A13A | same family + `0x0219D198` busy check | 0x05 |

⚠️ The per-state LABELS (what each one is "for") are NOT proven -- only the
call targets and the next-state writes are measured. The `0x0224Bxxx` family is
where round 11's live stack ran `0x0224B158 -> 0x021D32A0 -> 0x021D2FC4`, so
states 0x14/0x15/0x1E/0x1F are the ones that PROPOSE; state 0x02/0x0A reach the
per-cid switch.

**LAYER 4 - executor `0x021D49D4`**, opcode `[0x0229AAFC+0x68]`: explicit arms
0x67/0x66/0x65/0x64, `>7` -> default `0x021D6B00`, else the halfword table at
`0x021D4A20` (base 0x021D4A22) -> op0 0x021D4A94, op1 0x021D4BBA, op2 0x021D4BE0,
op3 0x021D4C04, op4 0x021D4DB0, op5 0x021D5A0E, op6 0x021D5AA2, op7 0x021D5AB8.

**MEASURED LIVE** in rom_ai_tables.ml4/.ml5/.ml6: worker state `[+0x58]` = 2 and
scheduler state `[+0x5C]` = 3 in all three, i.e. parked at the per-cid-switch
state on the opponent pass; the cascade gate `[+0x60]` goes 1 -> 0 as the chain
starts, so the scheduler stops being invoked while the chain resolves.
Executor opcode `[0x0229AAFC+0x68]` = 104 (0x68) throughout.

### Confirmed (round 14e) — the PROACTIVE path names 141 cids, 3.28% of the game

Census over the proactive chain only (`scratch/ai_proactive_census.py`, run
against STOCK `rom.nds` so no patch noise). A pool literal counts as "named"
only if it is loaded and then CMP'd within six halfwords, which rules out engine
constants that merely look like cids.

| site | cids named inline |
|---|---|
| `0x022393CC` per-cid AI switch + leaves | **17** — Curse of Fiend 131E, Embodiment of Apophis 1472, Non Aggression Area 15AD, Mind Crush 1803, D.D. Trap Hole 192E, Trap of Darkness 1935, Royal Writ of Taxation 1A9D, Volcanic Eruption 1AA8, Rainbow Dragon 1C03, Tour of Doom 1DD9, Battle Mania 1EEE, Metaphysical Regeneration 1F88, Fake Feather 201E, Majestic Star Dragon 211B, Seal of Wickedness 2142, **Effect Veiler 22E5**, Odin's Eye 2493 |
| `0x02239898` chain leaf | 1 — Gandora 17BC |
| `0x022398C8`-`0x02239EF0` helpers | 2 — Miraculous Rebirth 1AF9, Accumulated Fortune 1B04 |
| `0x021D2FC4` move validator | 1 — Seven Swords Warrior 23EA |
| `0x02239EF0` worker, `0x0223A1C4` scheduler, `0x021D32A0` packer, `0x021D6D34` cascade | **0** |

Plus the five membership lists it queries (19 + 48 + 21 + 22 + 29 entries;
125 of those are real cards). **UNION = 141 distinct cids = 3.28% of 4305.**

**THE REST OF THE GAME -- 96.7% OF CARDS -- IS PLAYED BY CARD-AGNOSTIC CODE.**
Cross-checking the ten cards the proactive path has been OBSERVED playing (round
13's live enqueue capture plus the .ml5/.ml6 chain), NINE are named nowhere in
that union: Elemental Hero Prisma 1D43, GB Gyzarus 1DC1, Offerings to the Doomed
145E, Book of Moon 1538, Magical Mallet 198D, Cup of Ace 1DC7, MST 132D, GB
Equeste 1E2A and **Ninjitsu Art of Transformation 1768**. Only Bottomless Trap
Hole 1518 appears, and only in the summon-response list.

⚠️ **THIS WEAKENS THE CASE THAT THE `chain_related` ADDITION CAUSED THE .ml6
ACTIVATION.** Being named in a proactive structure is demonstrably NOT a
precondition for the AI playing a card. The negative control (rebuild with
`ADD_CHAIN_RELATED` emptied, same Moja deck) is still the only thing that
settles it, and it has NOT been run.

Note `Effect Veiler 0x22E5` is BOTH an inline literal in the per-cid switch AND
a member of `opponent_turn_usable` -- the engine special-cases it twice.

### Confirmed (round 14d, 2026-09-20) — a live chain read from three savestates

`rom_ai_tables.ml4/.ml5/.ml6`, user-reported sequence: side 0 activates Effect
Veiler -> side 1 chains Book of Moon -> side 1 activates Ninjitsu Art of
Transformation.  All three are turn 3, turn player 1, phase 2 (Main 1).

**THE CHAIN / ACTIVATION LOG IS THE 0x24-BYTE DESCRIPTOR ARRAY AT 0x0229A7FC,
count `[0x0229A9FC+0x40]` (mirrored by `[+0x44]` in all three states).** It
accumulates what has actually been ACTIVATED this turn, by BOTH seats:

| state | count | entries (cid, +02 side, +05 kind, +0C code, +0E) |
|---|---|---|
| .ml4 | 0 | -- |
| .ml5 | 2 | `22E5` Effect Veiler side 0 kind 2 code 0x0046 ; `1538` Book of Moon side 1 kind 0 code 0x0023 flag 1 |
| .ml6 | 3 | + `1768` Ninjitsu Art of Transformation side 1 kind 0 code 0x0027 flag 1 |

`+0x02` is the CONTROLLING SIDE and it matches the report exactly (Veiler = 0 =
the human, the other two = 1 = the CPU).  ⚠️ Rounds 12/13 called 0x0229A7FC
"QUEUE-B, the full enumerated legal-move list"; here it is plainly an
accumulating record of activations, not a candidate list.  Not resolved — but
the round-12/13 reading should not be trusted without re-measuring.

**ZONE-RECORD `+0x04` IS THE POSITION / FACE STATE, NOT BIT 22 OF THE CARD WORD.**
The card word `+0x00` is unchanged across the whole chain for both S/T cards, so
decoding face-down from it (bit 22, which is the MONSTER-zone rule) is WRONG for
a Spell/Trap zone. Measured on side-1 records (base 0x0229B7D0 + 0x34 + z*0x14):

| zone | card | +0x04 | meaning |
|---|---|---|---|
| z8 | Ninjitsu Art of Transformation | **0x0C** in .ml3/.ml4/.ml5 -> **0x11** in .ml6 | SET face-down -> activated face-up Continuous Trap |
| z6 | Book of Moon | absent -> **0x10** in .ml5 | activated Quick-Play Spell |
| z2 | Ninja Grandmaster Hanzo | **0x07** throughout, record fully ZEROED in .ml6 | face-up ATK monster -> tributed |

`+0x08` is 0 while Set and 1 once face-up. `+0x10` = 0x00000102 for the face-up
Trap, 0x10000102 for the Spell (bit 28 differs), 0x00000100 for the monster.
So the user's original "it was Set and never flipped" was exactly right, and
0x0C -> 0x11 at `+0x04` is the activation.

**THE TRIBUTE WAS PAID WITH MELCHID 0x13E7**, whose zone record is zeroed in
.ml6 and which appears in side 1's GY (count 2 -> 3).

⚠️ **CORRECTION to a claim made earlier this session.** I read .ml3 and said the
opponent's deck contained NO Ninja monster, because none of the nine stock cids
in `setcode.ninja_table` were present. That was WRONG, and the reason is a trap
worth remembering: **cid 0x13E7 "Melchid the Four-Face Beast" is the DONOR for
`patch_ninja_grandmaster_hanzo`**, so in a chained ROM it IS Ninja Grandmaster
Hanzo and the patch rewrites the Ninja set-code list to contain it. Measured on
`rom_ai_tables.nds`, list 0x0209C722 count 9 =
`12B2, 13E7, 1464, 16B9, 1754, 17DF, 18BE, 1BCB, 2467` -- Armed Ninja 0x117B,
Crimson Ninja 0x16B8 and Sazank 0x238B have been displaced by three donors
(0x12B2 Dunames Dark Witch, 0x13E7 Melchid, 0x1464 The Gross Ghost of Fled
Dreams). **`scratch/cid_to_name.json` is the STOCK name map; on a chained ROM it
shows the donor's OLD name.** Never read a patched ROM's board through it
without checking the donor list first.

**AI context across the three:** action ctx `[0x0229AAFC+0x68]` = 104 (0x68) in
all three; `+0x5C` 0 -> 1 at the chain; `+0x60` 15 -> 12. AI phase ctx
`[0x0229ABFC+0x58]` = 2, `+0x5C` = 3 throughout, `+0x60` 1 -> 0. The reactive
rule-scan request `[0x0229DD94+0x18]` is **0 in all three**, so the 181-rule
table did NOT run for any of these activations. Animation opcode
`[0x02299B60]` 0x800C -> 0x8010 -> 0x8010.

**The relocated list is live:** 23 entries at 0x023A03D0 with 0x1768 present,
the reader's pool word 0x022398C0 -> 0x023A03D0, count immediate 23, read out of
running RAM in .ml3. Whether the addition CAUSED the activation is still
unproven -- the negative control (rebuild with `ADD_CHAIN_RELATED` emptied) has
not been run.

### Tooling (round 14c) — `ygo_tools/tools/ai_tables.py`

Lists and EXTENDS all six AI card tables.  **All 320 entries are written out
inline in the module itself** as editable `NATIVE_*` / `ADD_*` constants, one
cid per line with its card name in a comment -- appending to an `ADD_*` list and
rebuilding is the whole workflow.  `NATIVE_*` is asserted against the ROM before
anything is written, so a wrong base ROM or a drifted address aborts the build.
(notes/ai-card-tables.md is the same data as a flat report.)

```
python -m ygo_tools.tools.ai_tables --list --src <rom>
python -m ygo_tools.tools.ai_tables --extend --src <rom> --out <rom> \
    --add summon_response=0x2330 --add opponent_turn_usable=0x2321
python -m ygo_tools.tools.ai_tables --verify <rom>
```

**None of the six can grow in place.** The five u16 lists are packed back to
back with their neighbours (`0x0227109C`..`0x02271218`, and `0x0226EF2E` sits in
its own packed arena), and the rule table ends at `0x02275AB8` == the Synchro
LIST_A base. A survey of ov3's whole FILE IMAGE finds **zero** runs of >=128
zero bytes in both the stock and chained ROMs, and ov3's BSS cave is dead
(`mem.ov3_bss_is_cleared`), so there is no ov3 host either. Extension = RELOCATION
into the ov5 cave, three edits per table:

| edit | list | rule table |
|---|---|---|
| base pointer | the read site's literal-pool word | **TWO** pool words, `0x022481A8` and `0x02248244` |
| count | `movs r2,#imm8` at the read site | **TWO** `cmp rN,#imm8`, `0x02248196` and `0x0224821C` |
| entries | u16 cids, **must stay sorted** (binary search) | 8-byte {fn, arg} rows |

Both counts are 8-bit immediates, so **255 entries is the hard ceiling** for
every table. Cave slots claimed (ledger refreshed, `check_allocations` OK):
`CAVE_AI_L_OPPTURN` / `_SUMMON` / `_DESTROY` / `_CHAIN` / `_DEDUP` (0x200 each)
and `CAVE_AI_RULETABLE` (0x800); `CAVE_FREE` 0x0239FDD0 -> 0x023A0FD0.

⚠️ **The rule table relocates too, ON by default (`--no-rules` opts out) —
user's call, 2026-09-20.** Its entries are FUNCTION POINTERS and the scan does
`blx r1`; the ov5 cave is normal-duel-only (in `puzzle.mln` the cave region
holds unrelated ARM code), so **a ROM built this way must be treated as
NORMAL-DUEL ONLY until a puzzle has been tested on it** — that test is
outstanding. The five data lists degrade benignly in a puzzle: a binary search
over garbage returns a wrong bool. The mode-safe route, if the puzzle test
fails, is to relocate the rule table's neighbour (Synchro LIST_A, pure data) and
let the rule table grow in place in ov3 — NOT implemented.

**Extending the lists is meaningful** because a hit is a pure boolean verdict:
every list lookup that succeeds branches to `0x022397D2` = `movs r0,#1 ;
b 0x02239854`, with no per-card follow-up code.

**Native bug found AND FIXED:** `proposal_dedup` `0x0226EF2E` ships UNSORTED —
index 27 is `0x24B5`, index 28 is `0x2486` — so its last entry could never be
reached by the binary search. The relocated copy is sorted, so Divine Wind of
Mist Valley `0x2486` is reachable for the first time. The tool prints a `[fix]`
line and returns the repaired cids in its report, so the behaviour change is
never silent.

**Status: BUILT, verified, NOT in-game tested.**
`data/over_the_nexus/working/rom_ai_tables.nds`, built 2026-09-20 from
`rom_all_patches.nds` (source sha256 `ee8f588e…`), all six tables relocated,
**no cids added yet** — the build is the capacity change only.
  * sha256 `b27572d956bcee5474604797ca0f8a21142ce1ac7325ebdd11791a5259f70f17`, 129,605,256 B
  * every relocated copy is byte-identical to its native ov3 original
    (rule table 1448 B, all four lists) — only the dedup list's ORDER changed
  * exactly **21 ov3 bytes** differ from the source: the seven relocated base
    pool words. The two rule-table count immediates still read 181, and both
    rule pools (`0x022481A8`, `0x02248244`) now hold `0x023A07D0`
  * shipped-patch sweep: **57 passed, 0 failed**
  * capacity now 255 per table (the 8-bit count immediates), up from 19/48/21/22/29/181
  * NOT wired into `steps.STEPS`

### Confirmed (round 14b) — the GENERIC main-phase path is NOT a card list

Census of every per-card structure the CPU owns, against the 4305 cids in
`card_prop.bin` (`scratch/_ai_known_cids.json`, written by the census script):

| structure | entries |
|---|---|
| reactive rule table `0x02275510` args | 167 cid rows, **164 distinct** (148 exist in card_prop) |
| list `0x0227113C` opponent's-turn usable | 19 |
| list `0x02271162` destruction response | 21 |
| list `0x0227118C` chain-related | 22 |
| list `0x022711B8` summon response | 48 |
| proposal dedup table `0x0226EF2E` | 29 |
| **hard union (tables only)** | **275 distinct cids = 6.4% of 4305** |
| + cid-shaped literals in the AI code regions | <= 432 (10.0%) — an UPPER BOUND, the literal-pool scan cannot tell a cid from an engine constant of the same value |

**The decisive measurement:** cross the nine cards round 13 caught the proposal
loop *actually enqueueing live* against that union —

| cid | card | named anywhere in the AI's per-card structures? |
|---|---|---|
| 0x1D43 | Elemental Hero Prisma | **no** |
| 0x1DC1 | Gladiator Beast Gyzarus | **no** |
| 0x145E | Offerings to the Doomed | **no** |
| 0x1538 | Book of Moon | **no** |
| 0x198D | Magical Mallet | **no** |
| 0x1DC7 | Cup of Ace | **no** |
| 0x132D | Mystical Space Typhoon | **no** |
| 0x1E2A | Gladiator Beast Equeste | **no** |
| 0x1518 | Bottomless Trap Hole | yes — but only in the *summon-response* list, i.e. the REACTIVE path |

Eight of nine are named nowhere. **So the generic main-phase path is keyed on
action legality and instance state, not on card identity.** Corroborated by the
packer `0x021D32A0`, which is purely data-driven: it unpacks a 32-bit MOVE WORD
(`cid` bits 0-15, `field` bits 16-20, `kind` bits 21-23, `flag` bit 30) into the
0x24-byte descriptor and takes descriptor `+0x0E` from bits 19-20 of the
per-instance property word at **`0x0229C33C + packed_ref*8`** (`packed_ref =
(instance_index << 1) | side`, so stride 0x10 per instance with the two seats
interleaved) — there is no cid compare anywhere in it.

**Consequence for donor patches:** a newly authored card IS proposable by the
generic path (normal summon / set / activate) the moment the engine reports the
action legal. What it does not get is reactive play and any special-case plan —
those need membership of the four lists or a row in `0x02275510`.

## Ruled Out (round 14)

- **A per-duelist AI parameter.** The duelist id is confined to two arm9-heap
  copies of one profile string field; no code path in the duel engine can read it.
- **`0x0224B094` as the move generator.** Two callers, zone-record body,
  Speed World 2 special case — it is an activation helper.
- **Seat-mode value 3 in a normal duel.** `[0x0229DD14+0x54] = 0` in all ten
  states; 3 is a tag-duel control mode (`0x02299414+8`).

## Open Questions (round 14)

- `0x022393CC`'s per-cid compare chain (0x1EE bytes of stack
  initialisation and `cmp`/`beq` before the first list lookup; it seeds ~10
  stack slots `sp+0x08..sp+0x2C` with cid constants, each written twice as
  `base` then `base+delta` so only the second store survives) — are those pairs "card A wants card B" combo hints?
- Which of `0x02239EF0`'s 0..0xB states actually proposes a card, and where the
  *choice among several legal plays* is made (round 13 showed there is no scored
  candidate list — it is a proposal/validation loop).
- Does the AI's card-play breadth depend on anything other than the decklist?
  Round 14 found no parameter; the honest remaining explanation for "the recipe
  opponent plays more" is deck composition (its Synchron deck has far more
  legal main-phase plays than a Unicorn/Koa'ki beatdown list). **Unproven** —
  the test is to run the same recipe deck as an ordinary CPU duelist's deck and
  compare.

## Next Experiment (round 14)

Cheapest decisive modification test, no cave and no trampoline: in the ov3 image
at `0x0227113C` (file offset `0x12FA3C`) swap one cid of the 19-entry
opponent's-turn list for a card the AI holds but never uses, keep the list
sorted, rebuild a single-card test ROM, and watch whether the CPU starts
activating it. That exercises list membership in isolation with a count-neutral,
fully reversible edit.

## THE MAIN MOVE PATH (round 8) — planner + executor, NOT the rule table

The `0x02275510` rule table is the **reactive** path (see below). The AI's
*main* turn logic is a **queued-plan executor**, and it lives here:

| what | address | evidence |
|---|---|---|
| AI turn controller | **`0x021D6D34`** | live chain probe: busy on AI turn, idle on human turn (human frames are owned by `0x0219DAA4`) |
| **move queue** | **`0x0229A37C`** | literal @`0x021D6C98`, indexed `r6 + n*0x24` |
| queue count | **`0x0229A9FC+0x54`** | decremented by the compactor |
| queue index | `0x0229A9FC+0x40` | zeroed on entry to `0x021D6B44` |
| current action descriptor | **`0x0229AAFC`** | **736** ov3 literal refs — the busiest AI structure |
| current opcode | **`[0x0229AAFC+0x68]`** | observed live = **104 (0x68)** in `moja_opp_turn` |
| queue compactor | **`0x021D6B44`** | see below |
| **main opcode dispatcher** | **`0x021D49D4`** | switch on `[0x0229AAFC+0x68]` |
| secondary dispatcher | `0x021D3E78` | switch on `[ctx+0x60]`, range 0..0xE |

**Move descriptors are 0x24 bytes.** Every one of these functions indexes with
`movs r0,#0x24; muls`.

**`0x021D6B44` = queue compactor** (fully decoded):

```
[ctxA+0x40] = 0                       ; reset index
for r4 in queue:
    r0 = queue + r4*0x24
    bl 0x021ECDA4(entry,0,0)          ; validity predicate
    if r0 == 0: r4++                  ; keep
    else:                             ; drop: shift the tail down
        for r5 = r4 .. count-2:
            blx 0x0214C1E8(queue+r5*0x24, queue+(r5+1)*0x24, 0x24)   ; memcpy
        [ctxA+0x54] = count-1
```

**`0x021D49D4` = the executor.** Range-checks then dispatches:

```
r0 = [0x0229AAFC+0x68]
r0 == 0x67 -> 0x021D6AEA        r0 == 0x66 -> 0x021D64F2
r0 == 0x65 -> 0x021D64C4        r0 == 0x64 -> 0x021D6474
r0 >  7    -> 0x021D6B00 (default)
r0 <= 7    -> PC-relative halfword jump table @0x021D4A20 (base 0x021D4A22):
   op0 0x021D4A94   op1 0x021D4BBA   op2 0x021D4BE0   op3 0x021D4C04
   op4 0x021D4DB0   op5 0x021D5A0E   op6 0x021D5AA2   op7 0x021D5AB8
```

Opcode space runs to at least 0x68 (104 observed live), so this is a
**~104-instruction action repertoire**, not a handful of hardcoded moves.

### So the shape of the AI is

1. Something **generates candidate moves** and enqueues 0x24-byte descriptors.
2. Each tick `0x021D6B44` **prunes** descriptors that are no longer legal.
3. `0x021D49D4` **executes** the current descriptor by opcode.
4. Separately, `0x022481C0` runs the 181-entry **reactive** rule scan when a
   decision request is posted.

### THE ENQUEUE — `0x021D2FC4` (round 9, static)

Found by scanning ov3 for `ldr rX,[pc]` resolving to the queue contexts, then a
store to `[rX,#0x54]`/`[rX,#0x40]` in the same function.

```
0x021D2FC4  push {r4-r7,lr}          ; register_action(...)
  ...gate: [ctx+0x64] and the 0x0229911C jump table == 2   (same gate as 0x022481C0)
  build a packed descriptor on the stack from r4/r5/r6/[sp]:
     strh r5,[sp+0x10]      strh r4,[+2]     strh r4>>16,[+4]
     strh [sp],[+6]         strh [sp]>>16,[+8]   strh r6,[+0xA]
  ; r4 is a PACKED MOVE WORD, unpacked into fields:
     (r4 & 0x00E00000) >> 21    -> 3-bit kind   -> descriptor +0x05
     (r4 & 0x7E000000) >> 25    -> 6-bit field
     (r4 >> 31) & 1             -> flag
  ; DEDUP: linear scan of queue 0x0229A37C, stride 0x24, matching
     [e+0x0C]==r6 && [e+0x00]==id && [e+0x05]==kind
     plus bl 0x02023574 and the sorted-s16 binary search 0x02022E14
     over a 29-entry cid table at 0x0226EF2E
  ; APPEND (0x021D302E):
     r1 = 0x0229A9FC ; r3 = 0x0229A7FC
     r2 = [r1+0x40] ; r5 = r3 + r2*0x24 ; [r1+0x40] = r2+1     <<< queue[idx++]
```

**Five callers** (found by BL scan):

| bl site | enclosing function |
|---|---|
| `0x0219ED3C` | `0x0219EB08` — itself called from the turn controller at `0x0219D486` |
| `0x021D3222` | **`0x021D3168`** |
| `0x021D3402` | `0x021D32A0` |
| `0x021D3430` | `0x021D3424` |
| `0x021D3E0E` | `0x021D3BB0` |

⚠️ **`0x021D3168` is already in the KB** — `otn-warwolf-e1-native-responder-path`
records it as the "register-prim" through which Doppelwarrior offers a hand
Special Summon (`register-prim 0x021D3168 -> COMMIT 0x021EDA08`).

**This reframes the whole subsystem.** The 0x24-byte queue is not an AI-private
plan — it is the **shared LEGAL-ACTION list**. The engine enumerates legal
actions into it for whoever holds the turn; the human picks one through the UI,
the AI picks one programmatically. That is why `0x021D6B44` re-validates entries
every tick, and why the same machinery already showed up while chasing a
*player-facing* hand-SS prompt.

The 29-entry cid table at **`0x0226EF2E`** is searched during dedup:
`0E2F 118A 11C9 1403 16CD 1C9A 1D25 1D40 1D88 1DC5 1E8F 1EEB 1F3E 1F3F 1FA4
2077 2084 20C9 20D2 2101 2103 2179 2258 227B 2316 234D 23EA 24B5 2486`
(sorted except the last pair — treat the count as 28+terminator until proven).

### Round 10 — opcode writers, and a FALSE LEAD

Writers of `[0x0229AAFC+0x68]` (the executor's opcode), found statically:

| write site | function | note |
|---|---|---|
| `0x021D49A0` | `0x021D3E78` | secondary dispatcher |
| `0x021D53FE` | `0x021D49D4` | executor self-sequencing |
| `0x021D6AE6` | `0x021D49D4` | executor self-sequencing |
| `0x0223AAAE` | `0x0223A9B8` | refs only actx/ctxD |
| `0x0223B82C` | `0x0223B6EC` | refs only actx/ctxD |
| `0x02249630` | `0x02249540` | refs only actx/ctxD |

⚠️ **FALSE LEAD — `0x0223AC0C` is NOT the selector.** It looked ideal: the only
function referencing QUEUE-A (x6), qctx (x9) and the opcode (x12), 2168 bytes,
big switch on `[0x0229ABFC+0x70]` (situation codes 0x61-0x64, 0x78, 0x7B, 0x7C,
9..12), and 0 direct BL callers. But its Thumb pointer `0x0223AC0D` appears at
**`0x0226DCD0`, inside a RESOLVER pointer table**, two slots from
`0x02206ABD` (HANDSS_RES, `otn-hyper-librarian-chain-protocol`) and
`0x02206F41` (leave-trigger cls2, `otn-leave-trigger-cls2`). It is a
**card-effect resolver** that offers choices into the shared action queue — not
the AI's move chooser. The "touches all the globals" heuristic was wrong.

Useful by-product: **`0x0226DCC0`+ is a resolver function-pointer table** whose
membership is partly already in the KB.

### Round 11 — enqueue caught LIVE (the shared-list model is CONFIRMED)

`bp 0x021D2FC4 --hits 5` during the AI's turn. All 5 hits root at the AI turn
controller (`0x0219D4C8` scene tick -> `0x0219D3xx` duel-tick chain), and the
**enqueued cids are the AI's OWN cards** (low 16 bits of r1): `0x1D43`,
`0x1DC1` (Gladiator Beast Gyzarus), `0x1E2A` — all side-1 Gladiator Beast cards.

**Two distinct generator paths, both proven by stack:**

1. **Turn-controller main path** (hit 1, cid 0x1D43):
   `0x0219D4C8 -> 0x021D6D86 -> 0x0223A23E -> 0x0223A18A -> 0x0224B158
    -> 0x021D32A0 -> 0x021D2FC4`.
   `0x021D6D86` is the pop after `0x021D6D34`'s LAST branch (`bl 0x0223A1C4`,
   gated by `[0x0229ABFC+0x60]`). So `0x0223A1C4` is the AI's main-phase legal-
   move enumerator.

2. **Per-card effect enumeration** (hits 2-5, cids 0x1DC1 / 0x1E2A):
   `... -> 0x02256BAE -> 0x02253846 -> 0x0225379A -> 0x02252C70 -> 0x021D3296
    -> 0x021D3168 -> 0x021D2FC4`. The `0x0225xxxx` functions are the
   `0x0226D2B0` handler-table family; `0x021D3168` is the KB register-prim.

**Descriptor build (from the enqueue + live regs):** r1 low16 = cid; r6/r2 =
an action/situation code (0x41, 0x43, 0x59 observed); r4 = a packed field word
whose bits 21-23 are the "kind". This **confirms the queue is the shared
legal-action list**, not an AI plan: multiple enumerators (main phase +
per-card effects) post the turn-holder's legal moves; the human picks via UI,
the AI picks programmatically.

**So fill -> compact -> execute is fully proven. Only SELECTION remains.**
Working hypothesis: selection may be encoded IN the descriptor (a score/priority
field written at enqueue time), given the dedup pass and the 29-cid special
table `0x0226EF2E`. `ai_trace bp --queue` now decodes the 0x24-byte descriptors
to expose any such field.

### Round 12 — TWO arrays, and QUEUE-A is a size-1 slot

`bp 0x021D6B44 --hits 3 --queue` (compactor, reached via `0x021D6D34`'s
`[B+0x54]` branch `bl 0x021D6B44` @0x021D6D6E). At every hit **QUEUE-A count = 1**
and the single 0x24-byte entry CHANGES across hits:

| hit | cid | +0x04 | kind +0x05 | code +0x0C |
|---|---|---|---|---|
| 1 | 0x1DC1 (Gyzarus) | 0x09 | 1 | 0x59 |
| 2 | 0x1DC1 (Gyzarus) | 0x18 | 1 | 0x59 |
| 3 | 0x147D | 0x17 | 1 | 0x18 |

Descriptor layout confirmed: `+0x00` u16 cid, `+0x02`=0x02, `+0x04` u8 (varies),
`+0x05` u8 kind, `+0x0C` u16 action code (0x59 monster / 0x18 other — same family
as the enqueue's r2/r6). Trailing bytes past +0x14 are stale stack, ignore.

**Critical structural correction — there are TWO arrays, not one:**
- **QUEUE-B `0x0229A7FC`**, index `[QCTX+0x40]`: the enqueue `0x021D2FC4`
  APPENDS here. This is the full enumerated legal-move list.
- **QUEUE-A `0x0229A37C`**, count `[QCTX+0x54]`: the compactor operates here;
  observed to hold exactly ONE entry = the current chosen action.

Rounds 8-11 conflated them (dumped QUEUE-A while reasoning about the enqueue's
QUEUE-B target). At the compactor, `[QCTX+0x40]` (QUEUE-B index) had already been
reset to 0, so QUEUE-B was empty by then — enumeration/selection was complete.

**This narrows the selector precisely:** it is whatever reads full QUEUE-B and
writes the single winner into QUEUE-A (`[QCTX+0x54]` count-write with a copy).
`ai_trace bp --queue` now dumps BOTH arrays, so breaking at the enqueue will show
QUEUE-B accumulating; breaking after enumeration will show which entry survived
into QUEUE-A.

### Round 13 — the move path is a PROPOSAL LOOP (not a scored list)

`bp 0x021D2FC4 --hits 12 --queue` on the AI turn. Decoded (cid = r1 low16):

| # | cid | card | code r2 | proposer | driver |
|---|---|---|---|---|---|
| 1 | 0x1D43 | Elemental Hero Prisma | 0x41 | 0x021D32A0 | 0x0223A1C4 main-phase |
| 2,3,11 | 0x1DC1 | Gladiator Beast Gyzarus | 0x59 | 0x021D3168 | effect/summon (0x02256BAE/0x02268FF0) |
| 4 | 0x145E | Offerings to the Doomed | 0x12 | 0x021D32A0 | 0x0219DBF8 |
| 5,7 | 0x1538 | Book of Moon | 0x13/0x1E | 0x021D32A0 | executor 0x021D494E |
| 6 | 0x1518 | Bottomless Trap Hole | 0x0F | 0x021D32A0 | 0x0223A1C4 main-phase |
| 8 | 0x198D | Magical Mallet | 0x30 | 0x021D32A0 | 0x0219DBF8 |
| 9 | 0x1DC7 | Cup of Ace | 0x38 | 0x021D32A0 | 0x0219DBF8 |
| 10 | 0x132D | Mystical Space Typhoon | 0x0B | 0x021D32A0 | 0x0219DBF8 |
| 12 | 0x1E2A | Gladiator Beast Equeste | 0x43 | 0x021D3168 | 0x02256BAE effect |

All cids are the AI's own deck cards. **QUEUE-B index stayed 0 (twice 1); QUEUE-A
count stayed 0 the whole time.** So there is **no accumulated candidate list and
no scoring pass** — each call is one *proposal*, validated and cleared. The move
path is a **proposal/validation loop**, not enumerate-then-select.

**`0x021D32A0` = the descriptor packer.** Unpacks a 32-bit MOVE WORD (r5):
`+00 cid = bits0-15 | +03 field = bits16-20 | +05 kind = bits21-23 |
 +02 flag = bit30 | +0C target ref = arg2 | +0E 2 bits from a per-card prop table`.
Then `bl 0x021D2FC4` to validate/commit. It does not decide — it formats.

## THE MAIN MOVE PATH — complete map

```
0x0219D320   duel tick (subsystem chain)
  0x021D6D34   AI turn controller  (runs only when the AI holds the turn)
    0x0223A1C4   PHASE SCHEDULER   (state [ctx+0x5C]=0..3, walks the sub-phases)
      0x0224B094   MOVE GENERATOR  (+ siblings 0x0219DB04, executor 0x021D49D4)
        0x021D32A0   packer   -> {cid,field,kind} into a 0x24-byte descriptor
          0x021D2FC4   validate/dedup (29-cid table 0x0226EF2E) -> QUEUE-B
    0x021D6B44   compactor   -> revalidates the chosen action in QUEUE-A (size 1)
    0x021D49D4   executor    -> performs QUEUE-A's action (opcode VM, ~104 ops)
  reactive branch: 0x022481C0 -> 181-entry rule table 0x02275510 (on request only)
```

**The judgement — "which card, which play" — lives in the generators**
(`0x0224B094` and siblings), which iterate the AI's cards and decide what to
propose. Everything below them (packer, validator, queue, executor) is shared
mechanism, common to the human's UI path. `0x0224B094` is the next disassembly
target for the actual heuristics.

### Modification levers (updated)

- **Reactive special-cases:** reorder / retarget the `0x02275510` rule table
  (static ov3 patch, offset 0x133E10). 3.81% card coverage; exception list.
- **Proactive move choice:** the generators `0x0224B094` / `0x0219DB04`. Not yet
  disassembled; this is where "play aggressively / defensively / this combo"
  would live.
- **Move validity:** `0x021D2FC4` + the 29-cid table `0x0226EF2E` gate what is
  even proposable.
- ov5 trampolines work on any of these (AI runs in normal duels only = ov5 OK).

### STILL OPEN — the per-card heuristics

What remains unfound is the code that **picks an index** out of the populated
legal-action queue on the AI's behalf. Generation is shared with the human path,
so the AI-specific "judgement" is the selection step, somewhere between
`0x021D6D34` and `0x021D49D4`.

**Next (static):** the executor reads its opcode from `[0x0229AAFC+0x68]`. Find
what writes it — same technique: ov3 `ldr rX,[pc]` -> `0x0229AAFC`, then
`str rY,[rX,#0x68]` (imm5 = 0x1A, encoding 0x6680..0x669F). That writer is the
selector.

### SUPERSEDED — the generator/scorer

Steps 2-4 are mapped; **step 1 is not**. The code that fills the queue and picks
the opcode is the actual "decision" logic and has not been located. It is
somewhere in the 234 refs to `0x0229A9FC` / 736 refs to `0x0229AAFC`
(range `0x0219C87C`-`0x0226BFFC`, ov3 only).

**Next experiment (static):** find the *enqueue* — scan ov3 for `ldr rX,[pc,#imm]`
whose pool word is `0x0229A9FC`, then look ahead in the same function for a
`str rY,[rX,#0x54]` (count write) or a `+0x24`-strided store into `0x0229A37C`.
That site is the move generator. No emulator needed.

## FOUND — the dueling AI (round 6)

**The AI is a priority-ordered rule table at `0x02275510`: 181 (`0xB5`) records
of `{u32 fn, u32 arg}`, stride 8, spanning `0x02275510`–`0x02275AB8`.**

Call path, every step live-verified this session:

```
0x0219D4C6  blx r0            per-frame duel scene tick (handler[0] of 0x0226D2B0)
  -> 0x0219D320               duel tick: cooperative subsystem chain
    -> 0x021D6D34             busy ONLY on the AI's turn (chain probe, both turns)
      -> 0x022481C0           AI move selection
        -> 0x0224820C         the rule loop
```

The loop (`0x0224820C`–`0x0224821E`):

```
r5 = 0
loop: r1 = r5 << 3            ; stride 8
      r0 = [r4 + r1 + 4]      ; arg
      r1 = [r4 + r1]          ; fn
      blx r1                  ; run the rule
      cmp r0, #0
      bne 0x0224822E          ; nonzero => this move is CHOSEN, stop scanning
      r5 += 1
      cmp r5, #0xB5           ; 181 rules   <- count immediate at 0x0224821C
      blo loop
0x02248220  (no rule fired)  bl 0x021D2964; [ctx+0x18]=0; [ctx+0x1C]=0; return 0
0x0224822E  (rule fired)     bl 0x021D2964; return 1
```

`return 1` at `0x02248232` is literally the `r0=1` the chain probe measured on
the AI's turn — the path is confirmed end to end, not inferred.

**Table contents:** 67 distinct rule functions, all in ov3 `0x02244xxx`–
`0x02247xxx`. `arg` is a **cid** (`0x1D08`, `0x1FEE`, `0x15F6`, `0x1C7B`, …), so
the table is largely *per-card* AI knowledge. `arg = 0` entries are generic rules
and sit at the top (highest priority): index 0 = `0x02244191`, then `0x02247F41`,
`0x02246AE9`, `0x02245265`. Most-used handlers:

| fn | count | | fn | count |
|---|---|---|---|---|
| `0x02244431` | 37 | | `0x022443B1` | 7 |
| `0x02245C49` | 36 | | `0x02246D91` | 6 |
| `0x0224660D` | 12 | | `0x022475B9` | 5 |

Rule functions take the `arg` cid in r0. Sampled `0x02244430`: calls the
card-property bitfield test `0x02029E60`/`0x02029E80`, selects a zone range
(`r6`/`r7` = 4/0, 0xA/0xA, or 5/9) and scans.

⚠️ **`0x02244431` is an AI RULE HANDLER**, not the "level-BAND checker" claimed
in `otn-hyper-librarian` (already flagged wrong by
`otn-synchro-material-machinery`). This is its actual role.

### Round 7 — STATIC resolution of the gate chain (no emulator)

Done purely from savestate RAM + overlay images. Literals re-resolved carefully
(Thumb `PC = (addr+4) & ~3`); two of the round-6 literals were wrong — G2's base
is `0x0229DD14` (not `0x0229911C`, which is the G3 jump table).

- **`0x021EF7FC` is NOT a stub.** It is `ldr r3,[pc,#4]; movs r0,#0; bx r3` —
  a thunk that tail-calls **`0x021EF808(0)`**, a real board scan (iterates zones
  at stride 0x14, reads `[r1+0x34]`, extracts cid via `<<18 >>18`, reads
  `[r1+0x3C]`).

- **`[0x0229DD94+0x18]` is a PENDING-REQUEST flag, not a per-frame condition.**
  The no-fire exit at `0x02248224` does `[0x0229DD94+0x18] = 0` and `[+0x1C] = 0`
  — it *consumes* the request. So the 181-rule scan is an **on-demand decision
  scan**, which is exactly why 3.81% card coverage is coherent: it only runs when
  something asks for a special-case decision.

- **Branch of `0x021D6D34` taken, evaluated statically per savestate**
  (A=`0x0229AAFC`, B=`0x0229A9FC`, C=`0x0229DD94`, D=`0x0229ABFC`):

  | state | turn | req `[C+0x18]` | path |
  |---|---|---|---|
  | moja | start | 0 | return 0 |
  | moja_opp_turn | **AI** | 0 | **return 0 — nothing to do** |
  | gyzarus | start | 1 | -> `0x022481C0` |
  | gyzarus_my_turn | human | 0 | return 0 |
  | gyzarus_opp_turn | **AI** | 1 | -> `0x022481C0` |

  Note `moja_opp_turn` is an AI turn yet returns 0, and `gyzarus.mln` is a duel
  *start* yet has the request set. **The request flag is not turn-correlated** —
  it is transient. This weakens the round-5 phrasing "`0x021D6D34` is busy ONLY
  on the AI's turn": the live probe saw 6/6 vs 6/6 in the gyzarus duel, but that
  is a property of when the flag happened to be set, not of the turn as such.

- **The table is the sole entry point for 62 of 67 rule functions.** Scanning
  ov3 + ov5 + arm9 for each fn pointer as a 32-bit word and subtracting the
  table's own multiplicity: only 5 fns have any external reference (1 each), and
  **every** occurrence is in ov3 (none in ov5 or arm9). So these functions exist
  *for* this table — patching table records really does change behaviour.

### What static analysis CANNOT settle here

Whether `0x021EF808(0)` returns nonzero — which decides rule-loop vs
short-circuit — is a data-dependent board scan with loops. Hand-simulating it is
precisely the failure mode recorded in `thumb-stack-based-switch-footgun`
(a register-only simulator reported the WRONG leaf; GDB disagreed x364).
**Do not infer this one; measure it.** Single test, with a known precondition:

```
# must be run while [0x0229DD94+0x18] != 0, else 0x022481C0 exits at G1
uv run python -m ygo_tools.tools.ai_trace bp 0x02248214 --hits 5
```

Hit => the rule loop genuinely runs (r1 = rule fn, r0 = its arg cid).
No hit => the table is dormant and `0x021EF808` is the real decision path.

### ⚠️ SCOPE CORRECTION — the rule table is not "the whole AI"

Two things walked back from the round-6 write-up above:

1. **Coverage is 3.81%.** 181 entries = 13 generic (`arg=0`, at idx 0/13/14/16/
   55/62/63/89/91/92/106/167/168), 1 sentinel (idx 88, `0xFFFFFFFF`), and 167
   cid-specific records holding only **164 distinct cids out of 4305 cards**.
   Card-type mix tracks the game's overall mix (Effect 40.9% vs 39.2%, Spell
   23.2% vs 23.8%, Trap 21.3% vs 17.0%), i.e. it is NOT a complete card
   database — it is a **special-case exception list**. The generic play logic
   (normal summon / attack declaration / set) has NOT been located.

2. **We have not proven the rule loop executes.** `0x022481C0` has an earlier
   short-circuit that also returns 1 without ever reaching the loop:

```
022481FA  bl 0x021D290C
022481FE  bl 0x021EF7FC
02248202  cmp r0,#0
02248204  bne 0x0224822E     ; -> returns 1, SKIPPING the rule loop entirely
02248206  movs r5,#0         ; rule loop starts here
```

   The chain probe measured `r0=1` out of `0x021D6D34`, which is equally
   consistent with `0x021EF7FC` firing. **Unproven** that the 181-rule scan ran
   at all. Entry gate `[0x0229DD94+0x18]` was 1 in the savestate, so the loop is
   at least reachable.

   **Next experiment:** `bp 0x02248214` (the `blx r1` inside the loop) during the
   AI's turn. If it hits, the loop genuinely runs and r1/r0 give the firing rule.
   If it never hits, the table is dormant in normal play and the real decision
   path is `0x021EF7FC`.

### Q: do all CPU opponents share this AI? — YES

The 1448-byte table is **byte-identical across all five savestates**, covering
two different duelists (Moja deck, Gladiator Beast deck). It lives in ov3
code+data, the region proven earlier to have exactly ONE state-dependent byte in
its whole 1.39 MB (`0x0228FA60`, the scene mode) — and that byte is not in the
table. There is one shared AI; per-opponent variation comes from the decklist,
not from the rule set.

### Q: is the table ROM-patchable? — YES, no trampoline needed to re-order

It sits at **ov3 image offset 0x133E10**, and `ov3_image[0x133E10:] == live RAM`.
So reordering records or changing an `arg` cid is a plain static overlay patch —
no hook, no cave, count-neutral. A trampoline is only needed to add *new
behaviour* (see below).

### cid -> card name (reusable)

`card_prop.bin` rows are sorted by `card_id` (= cid); the row index addresses
`card_name_e.bin`, **plus a skew of 2** (that file has two leading entries).
Solved by sweep: k=+2 gives 3170/3174 against the decompiled filenames, every
other k gives 0. Spot-checked 0x1DC1 Gyzarus / 0x20B7 Moja / 0x1C76 Laquari /
0x2338 Scarred Warrior against independent sources. `card_intid.bin` is NOT this
mapping, and the `iNNNN` field in decompiled filenames is NOT the card_prop row.

### How to modify the AI

- **Reprioritise:** swap 8-byte records. Earlier = higher priority; the first
  rule to return nonzero wins and the rest are never evaluated.
- **Retarget a rule:** change a record's `arg` cid.
- **Replace behaviour:** point `fn` at an ov5 cave stub (normal duels only —
  which is fine, the AI only runs there).
- **Disable a rule:** point it at a stub returning 0.
- ⚠️ **The table CANNOT grow in place.** It ends at `0x02275AB8`, which is
  exactly the Synchro `LIST_A` address in the KB — the next structure starts
  immediately. Extending means relocating the table and patching both the base
  literal at `0x02248244` and the count immediate `0xB5` at `0x0224821C`.
  Register any such claim in the allocation ledger before building.



Savestates (all melonDS, RAM0 file offset **0x24**, all in
`data/over_the_nexus/working/`):

| label | file | state |
|---|---|---|
| M     | `moja.mln`             | duel start vs Moja deck |
| G     | `gyzarus.mln`          | duel start vs Gladiator Beast deck |
| G:MY  | `gyzarus_my_turn.mln`  | my turn, AI has Laquari `0x1C76` on field |
| M:OPP | `moja_opp_turn.mln`    | AI's turn, it summoned `0x1EA4` |
| G:OPP | `gyzarus_opp_turn.mln` | AI's turn, it summoned Laquari `0x1C76` |

Player 0 is the human (same deck in all five). Player 1 is the AI.

## Confirmed (this session)

- **No per-opponent or per-turn code anywhere.** Over all five states, byte-diff
  of every executable region is **zero**: arm9 code `0x02000000–0x0209E000`,
  overlay 3 `0x02141700–0x022943E0`, overlay 5 `0x022C5900–0x0239A120`. One
  shared AI; no AI overlay swap; nothing self-modifying except the single byte
  below.

- **The AI leaves almost no persistent RAM footprint.** Whole-RAM liveness
  matrix at 64-byte granularity across all five states: memory nonzero in *both*
  AI-turn captures and zero in *all three* others totals **512 bytes**
  (`0x02110F00–0x02111000`, `0x0213DEC0–0x0213DF80`, `0x022AEE00–0x022AEE40`).
  Symmetrically only 704 B is freed during the AI's turn.
  **=> The AI's decision is computed transiently (stack / reused scratch) and is
  gone by the time a savestate lands on a stable frame. Savestate diffing cannot
  localise the AI, on any axis.** This kills the plan from the previous round.

- **Overlay-3 `.bss` holds no AI workspace.** 3156 blocks of 64 B over
  `0x022943E0–0x022C5900`: 2685 blocks (167 K) are zero in *all five* states,
  including both AI-turn captures. Only 218 blocks (13 K) come alive after duel
  start, and those are live on my turn too.

- **Exactly one byte of ov3 `.data` is state-dependent: `0x0228FA60`.**
  ROM ships `0x09`; four states hold `0x05`; G:OPP holds `0x08`. It is a **scene
  / sub-mode variable**, not an AI flag — proven by disassembly: the function at
  **`0x0214656C`** loads it into r7 (literal at `0x021466C8`) and gates
  transitions among modes 4,5,7,8 (`cmp r0,#4 / #5 / #7 / #8`, `str r6,[r7]`).
  M:OPP also holds `0x05`, so it does not track "AI is acting".

- **⚠️ The early part of overlay 3 is ARM code, not Thumb.** `0x02141700`
  onward (at least through `0x0214_6xxx`) disassembles correctly only in ARM
  mode — e.g. `0x02146574 ldr r1,[pc,#0x148]`, `0x021465F4 pop {r4..r8,pc}`.
  Capstone in Thumb mode produces plausible-looking garbage here. The effect
  engine proper (`0x0219…`–`0x0226…`) is Thumb as documented; this ARM region is
  the overlay's framework/scene layer. Anyone disassembling low ov3 addresses
  must pass ARM mode.

- **Opponent deck record: `0x02299200` (ov3 `.bss`, static address).**
  Layout, confirmed against both opponents:
  - `+0x00` u32 = **main-deck count** (0x28 = 40 for both)
  - `+0x08` u32 = **extra-deck count** (0 for Moja, 6 for Gyzarus)
  - `+0x0C` = **sorted u16 cid array**, main deck then extra
  Cross-checks: the array matches the player-1 deck decoded from
  `player+0x304`/`+0x4E4`, and the Gyzarus extra count 6 matches its
  `0x1C87`x3 + `0x1DC1`x3. Mirrored in the arm9 heap at `0x020B8CE0` with the
  same shape.

- **ov3 duel-context global `0x02299114`** — **298** literal references from ov3
  (nothing from arm9 or ov5), by far the most-referenced address found. The deck
  record above sits at context `+0xEC`.

- **Per-opponent duelist profile block in the arm9 heap (~`0x020B6DD0`).**
  Decoded strings, invariant per opponent across time:
  - `0x020B6DDE` duelist name — `"Moja"` / `"Gladiator Beast Gyzarus"`
    (duplicate copy at `0x020B88C2`)
  - `0x020B7019` deck name — `"Dingy Daredevil"` / `"Gladiator Gradation"`
    (length-prefixed: `\x03` / `\x02`)
  - `0x020B6F40` **28 bytes of a single repeated per-duelist byte**:
    `0x2F` (Moja) vs `0xA7` (Gyzarus). Duplicate at `0x020B8B54`.
    Purpose unknown — the only compact per-opponent scalar found.
  These are heap addresses, so they are not statically xref-able and may move
  between runs.

- **Overlay 5 is duel-aware code, not a data blob.** Literal refs to the player
  struct `0x0229AC94` / stride `0xB3C` / summon descriptor `0x02298A28`:
  arm9 = 0/0/0, ov3 = 1394/1925/140, **ov5 = 914/1168/35**. ov5 is 870432 B of
  code that indexes duel state.

- **No debug symbols.** arm9 + ov0/1/3/5/6/41 scanned for `*.c`/`*.cpp` strings:
  only `_wmapi.c` (arm9), `ds_flash.cpp` / `ds_flash_texture.cpp` (ov0).

## Confirmed — live GDB, PC sampling (round 2)

Tool: `ygo_tools/tools/ai_trace.py` (built this session, on `gdb_rsp.py`).
Preflight PASSED against the live Gyzarus duel: ov3 + ov5 resident, LP 8000/8000,
side1 zone 2 = Laquari `0x1C76`, deck record `0x02299200` main=40 extra=6.

- **Baseline (human turn, idle), 200 samples:** 100% arm9 code; 197/200 at a
  single idle loop **`0x02053250`**.

- **AI turn, 400 samples:** idle loop falls to 205/400 (51%). New activity:

  | PC | samples | identified |
  |---|---|---|
  | `0x0207FF80–0x0207FF9E` | ~73 (18%) | HW FIFO drain loop — **not AI** |
  | `0x02022E1C–0x02022E3E` | 15 | **sorted-s16 binary search** |
  | `0x02089FA4–0x02089FAC` | 7 | unidentified |
  | ov3 MAIN (Thumb) | 22 (5.5%) | — |
  | **ov5 NATIVE** | **2 (0.5%)** | **noise** |

  LR by region: arm9 82.2%, **ov3 MAIN 11.5%**, ov5 0.8%. So ov3 Thumb code is
  the caller of the hot arm9 leaves.

- **`0x02022E14` = `bool contains_sorted_s16(r0=key, r1=array, r2=count)`.**
  Disassembled from savestate RAM:
  `push {r3,r4,r5,lr}; lo=0; hi=count-1;` loop `mid=(lo+hi)>>1;
  r3=ldrsh[r1+mid*2]; cmp r3,r0; bge hi=mid else lo=mid+1;` exit
  `return arr[lo]==key`. 15 samples on the AI turn vs **0** at baseline. The
  deck record at `0x02299200` is a sorted u16 cid array, so this is the likely
  "do I hold / can I play card X" probe. Generic library routine — its *callers*
  are what matter.

- **`0x0207FF80` is a hardware FIFO drain**, not AI: `r0 = 0x00800000` status
  mask, poll `[r1]`, copy up to 0x80 words into `r4[]`, `bne` back. Consistent
  with the summon animation. Discount the 18%.

- **⚠️ `ndspy`'s `rom.arm9` is BLZ-compressed** — ROM file offsets do NOT map
  linearly to arm9 RAM addresses, and disassembling it yields plausible-looking
  garbage (it decoded ASCII string data as Thumb). ndspy DOES decompress
  overlays, so `ovs[3].data` / `ovs[5].data` are fine. **Disassemble arm9 from a
  savestate**, not from the ROM (`scratchpad/disasm_ss.py`).

## Confirmed — PC sampling round 3 (600 samples, AI turn)

Region split: arm9 88.7%, **ov3 MAIN 7.7%**, ITCM/DTCM 2.5%, ov5 0.8%,
ov3 LOW 0.3%. LR: arm9 79.7%, **ov3 MAIN 12.2%**, ov5 1.7%. ov5 stays noise.

Hottest ov3 LRs (the call sites, at LR-4):

| LR | hits | call site |
|---|---|---|
| `0x021A3788` | 24 | `bl 0x02023B00` @ `0x021A3784` |
| `0x021A3728` | 16 | `bl 0x02023640` @ `0x021A3724` |
| `0x021AC168` | 5 | |
| `0x021A144C` | 4 | inside the known `0x021A1430` walker family |

All the hot ov3 PCs (`0x021A36F8/3702/3704/371A/371E/3782/379E/37E6`) fall in one
function.

- **`0x021A36F8` = `get_effective_cid(r0=side, r1=zone, r2=apply_overrides)`.**
  Disassembled from savestate RAM:
  `r6 = zone*0x14; r3 = player_base + (side&1)*0xB3C;
  r2 = [r3+r6+0x34]; r4 = (r2<<18)>>18` (= `word & 0x3FFF`, the cid). Then for
  `zone <= 4` it calls `0x02023640(cid)` (card-property fetch — a 4-instruction
  thunk `r2=9; bx r3`) and walks the **stride-0xA attached-node list**
  (`ldrh [r5,#8]` = next index, `+2` low nibble = kind, kinds 2/3 matched,
  `+0` = key, `+4` = replacement cid, gated by the bitfield test `0x02029E60`),
  overriding the cid on a hit. If `r2` was set it then calls `0x02023B00(cid)`
  and `0x021A1584(side, zone, ...)` for a further override. Returns r4.
  This is the **name-override / "treated as" resolver**, and it corroborates the
  `ram.relationship_pool` stride-0xA claim (currently UNVERIFIED in the KB).
- **`0x021A37D8`** is a thin wrapper: `get_effective_cid(side, zone, 1)`, then
  one more `0x021A1584` fixup.

- **The sampler has bottomed out in leaf utilities.** LR reaches exactly one
  frame up, and everything hot is a shared board-scanning helper that *any*
  caller (AI, UI, effect engine, renderer) would hit. PC sampling cannot go
  deeper — the next instrument must be the **stack walk**.

## Ruled Out

- **Per-duelist AI code / an AI overlay.** Killed by the zero-byte code diff
  across all five states.
- **A persistent AI evaluation workspace in ov3 `.bss`.** Killed by the liveness
  matrix — 167 K of that `.bss` is dead even mid-AI-turn.
- **Locating the AI by savestate diff at all.** Killed by the 512-byte
  AI-exclusive result on the correct (temporal, same-duel) axis.
- **A per-player `is_cpu` flag in the player struct.** Scanned all 0xB3C bytes
  for an offset that is constant-per-side across all five states and differs
  between sides: **zero hits**. Side 1 is not marked as CPU in the player struct.
- **`0x0228FA60` as an AI indicator.** It is a scene mode; M:OPP and G:OPP
  disagree on its value.
- **"The AI lives in overlay 5."** Killed by PC sampling: 2 of 400 samples
  (0.5%) during the AI's whole turn, with LR in ov5 at 0.8%. ov5's 914
  player-struct literal refs did NOT predict execution — it is duel-aware code
  that barely runs. **The static ref-count heuristic was misleading; the
  sampler is the arbiter.** Remaining candidate: ov3 MAIN (Thumb).

## Open Questions

- Is the AI in ov3's Thumb region or in ov5? ov5's 914 player-struct refs make
  it the prime suspect, but "indexes duel state" ≠ "is the AI".
- What is the `0x020B6F40` per-duelist byte (`0x2F` / `0xA7`)? Duelist ID,
  portrait/voice ID, or an AI tier? Heap-resident, so it needs a live watch.
- Is there any AI *parameter* at all, or is opponent behaviour purely a function
  of the decklist plus one shared routine?

## Confirmed — the tag-duel AR code (round 4)

User-supplied Action Replay code "grants control over the AI in a tag duel".
Decoded (NDS AR types): `5` = guard, `E` = block copy, `0` = 32-bit write,
`D2000000` = end.

```
5219D4A8 D1052800   ; guard: only apply if [0x0219D4A8] == 0xD1052800
E219D498 00000010   ; copy 16 bytes to 0x0219D498
491DD10E 009B23C6   ;   payload
68181AF3 68586088   ;   payload
0219D4A8 200060C8   ; write [0x0219D4A8] = 0x200060C8
D2000000 00000000
```

- **The guard MATCHES our EU ROM**: bytes at `0x0219D4A8` are `00 28 05 D1`.
  So this code is address-compatible with `data/over_the_nexus/working/rom.nds`
  and `0x0219D4A8` is a valid EU ov3 address. (Verified by reading savestate RAM.)

- **The patched function (`0x0219D478`–`0x0219D4C6`) is the turn/action
  controller**, disassembled from savestate RAM:

```
0219D478  ldr r1,[pc,#0x90]  -> 0x0226D2B0     ; handler table
0219D47A  ldr r1,[r1,r2]
0219D47E  beq 0x219D4DA
0219D486  bl  0x0219EB08
0219D492  bl  0x021C4028
0219D498  bne 0x219D4A8
0219D49A  ldr r1,[pc,#0x74]  -> 0x02299414     ; TAG control context
0219D49C  ldr r1,[r1,#8]                       ; control MODE
0219D49E  cmp r1,#3                            ; <-- AR neutralises this
0219D4A2  bl  0x0219D31C
0219D4AC  ldr r1,[pc,#0x58]  -> 0x0229DD14     ; action/control context
0219D4AE  ldr r1,[r1,#0x54]                    ; control MODE
0219D4B0  cmp r1,#3
0219D4B4  blx 0x0214C1C8
0219D4BC  ldr r4,[pc,#0x48]  -> 0x0229DD14
0219D4BE  ldr r0,[r4,#0x70]                    ; STATE INDEX
0219D4C0  lsls r1,r0,#2
0219D4C2  ldr r0,[pc,#0x48]  -> 0x0226D2B0
0219D4C4  ldr r0,[r0,r1]
0219D4C6  blx r0                               ; <<< STATE DISPATCH
```

- **The AR patch's effect:** it replaces the `[0x02299414+8] == 3` test with
  `r1 = 0x02299414; r3 = r6 - 0x318; [r1+8] = [r3]; [r1+0xC] = [r3+4]; r0 = 0`
  — i.e. it stamps another seat's control descriptor onto the AI seat.
  **=> control mode lives at `ctx+8`/`ctx+0xC`, and value 3 means "this seat is
  COM/AI".** This is the `is_cpu` flag I failed to find in the player struct: it
  is NOT per-player, it is in a separate control context.

- **Handler table `0x0226D2B0`** (read from savestate, all Thumb pointers, ov3):

  | idx | handler | | idx | handler |
  |---|---|---|---|---|
  | 0 | `0x0219D320` | | 5 | `0x022580CC` |
  | 1 | `0x0219D230` | | 6 | `0x0225694C` |
  | 2 | `0` | | 7 | `0x022564EC` |
  | 3 | `0x022567A8` | | 8 | `0x02258C3C` |
  | 4 | `0x02253A04` | | 9 | `0` |

- **`0x0229DD14` is the live action/command descriptor.** In
  `gyzarus_opp_turn` (AI mid-action) `0x0229DDFC` holds cid `0x1C76` (Laquari)
  and `0x23` — the exact packed ref from the summon descriptor `0x02298A28`.
  Whatever fills this during the AI's turn IS the AI.

- **Its owning subsystem is `~0x02198000–0x0219E000` in ov3.** Literal refs into
  `0x0229DD14–0x0229DE40`: **ov3 1203, arm9 0, ov5 0**, clustered in
  `0x02198xxx–0x0219Dxxx`. That narrows the AI search space from ov3's 1.39 MB
  to about 24 KB — and is a third independent confirmation that ov5 is not
  involved.

- **`0x02299414` (tag control ctx) is all zeros in every single-player
  savestate**, as expected for a non-tag duel. The normal-duel path uses the
  `0x0229DD14+0x54` test instead.

## Confirmed — dispatch breakpoint (round 5)

`bp 0x0219D4C6`, 6 hits on the human turn and 6 on the AI turn: **identical**.
Every hit `r0=0x0219D321`, `r4=0x0229DD14`, `sp=0x027E3728`, stack
`0x021460D0` -> `0x0214653C` (the ov3 ARM scene loop).

- **`0x0219D4C6` is the per-frame duel scene tick, not a control fork.** The
  state index `[0x0229DD14+0x70]` stays 0, so it always dispatches handler[0] =
  **`0x0219D320`**. Ruled out as a discriminator.

- **`0x0219D320` is the duel tick and it is a cooperative subsystem chain**
  (disassembled from savestate RAM):

```
0219D34C  bl 0x0219C964
0219D350  bl 0x0219AF00
0219D354  cmp r0,#0 ; bne 0219D35C
0219D358  bl 0x0219DAA4
0219D35C  cmp r0,#0 ; bne 0219D364
0219D360  bl 0x0225CD44
0219D364  cmp r0,#0 ; bne 0219D36C
0219D368  bl 0x021CDE54
0219D370  bl 0x0225965C
0219D378  bl 0x02268918
0219D380  bl 0x0219DB04
0219D388  bl 0x021D6D34
0219D394  str r1,[r4,#0x6c]      ; r1 = (r0 == 0)
0219D39E  bl 0x0219D198
```

  Each `bl` returns "am I busy" and the first nonzero owns the frame. Note the
  `bne` targets are the *next* `cmp`, so a nonzero **cascades** — every cmp site
  is still executed. That is what makes the site-by-site r0 read a valid probe.

## Next Experiment (current)

The chain probe RESOLVED the search (see "FOUND" at the top of this file):

| turn | first BUSY site | subsystem |
|---|---|---|
| human | `0x0219D35C` | `0x0219DAA4` (human input owns the frame) |
| AI | `0x0219D38C` | `0x021D6D34` -> `0x022481C0` -> the rule table |

Remaining work, in priority order:

1. **Identify the rule handlers.** 67 functions in `0x02244xxx`–`0x02247xxx`.
   Start with the four generic (`arg = 0`) entries at the top of the table —
   `0x02244191`, `0x02247F41`, `0x02246AE9`, `0x02245265` — since they gate
   everything else.
2. **Confirm rule selection live.** `bp 0x02248214` (the `blx r1`) during the
   AI's turn and log r1/r0 to see which rule index actually fires for a given
   board. A `--log` mode over N hits would give the firing histogram.
3. **First modification experiment.** Retarget one `arg` cid (cheapest,
   fully reversible) and confirm the AI's play changes in-game.
4. **Promote to the KB.** These are strong VERIFIED-grade facts with closed
   structural proofs: rule table base/stride/count, the `0x0219D320` chain, the
   `0x0226D2B0` handler table, `0x0229DD14` action ctx, control mode == 3.
   Also fix `otn-hyper-librarian`'s `0x02244431` claim.

## Superseded Experiment

Savestate diffing is exhausted — the remaining work is **live**, via the melonDS
GDB stub. Preflight per CLAUDE.md: stub on port **3333**, an active *normal*
duel (not a puzzle), ov3 + ov5 resident.

1. During the AI's turn, break on a commit primitive the AI must route through —
   SS-commit **`0x022692E6`**, or the summon-event dispatch — and walk LR / the
   stack upward. Frames above the effect engine are AI code; whether they land in
   `0x02141700+` (ov3) or `0x022C5900+` (ov5) settles the ov3-vs-ov5 question in
   a single capture. This is the decisive experiment.
2. Cheap corroboration: breakpoint on any write to the deck record region around
   `0x02299200` / context `0x02299114` during the AI's turn. (melonDS
   write-*watchpoints* do not fire — use breakpoints, per
   `otn-hyper-librarian`.)
3. Once an AI frame address is known, feed it back through
   `scratchpad/xref_addr.py` to pull the surrounding call graph out of the ROM
   statically.

**Caveat for later:** if the AI turns out to live in ov5, re-verify
`otn_enhanced/docs/engine/allocations.yaml` before touching ov5 natively. Cave claims sit at
`0x0239A120+`, past ov5's native end, so they *should* not overlap AI code — but
that has not been checked against actual ov5 function extents.

## Tooling written this session

In the session scratchpad (not yet promoted to `ygo_tools/tools/`):
`ss_survey.py` (page-density diff), `ss_runs.py` (coalesced diff runs by
region), `ss_state.py` (decode duel state), `ss_peek.py` (side-by-side hex),
`bss_matrix.py` / `live_matrix.py` (N-state liveness matrix),
`opp_profile.py` (invariant-per-opponent word isolation),
`xref_addr.py` (literal-pool xref), `disasm_win.py` (ARM/Thumb window disasm).
