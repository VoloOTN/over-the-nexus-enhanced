# Upstart Golden Ninja — findings (session 2026-09-01)

Printed text (`scratch/ygoprodeck_cache.json`, id 58911105) — LIGHT / Warrior /
Level 4 / 500 / 1800. Byte-identical to the 3DS build's own `CARD_Desc_E`:

> Once per turn: You can send 1 Trap from your hand to the GY; Special Summon 1
> Level 4 or lower "Ninja" monster from your Deck in face-up Defense Position or
> face-down Defense Position.

Clauses (one ignition effect — cost + action, cannot ship apart):

1. **C1 (cost)** — *Once per turn:* send 1 **Trap** from your **hand** to the GY.
2. **C2 (effect)** — Special Summon 1 **Level 4 or lower "Ninja"** from the
   **Deck**, face-up DEF **or** face-down DEF.

**STATUS: BUILD 4 — BOTH PRINTED CLAUSES IN-GAME CONFIRMED BY THE USER
2026-09-01.** One deliberate deviation remains (PART F, the face-down Defense
option). `verify()` = **37/37 PASS (static only)**.

    .venv-1/Scripts/python.exe _build_upstart.py
    -> data/over_the_nexus/working/rom_upstart.nds
    sha256 51aa382b104ce5ea6e87b0d7945aac718a5e1c916205c34bfb0411d56d060f22

✅ **IN-GAME CONFIRMED BY THE USER 2026-09-01 — TEST 4**, their words:
*"I can confirm all 4 points behave as expected"*, against this checklist:

1. **No Trap in hand -> the effect is NOT offered** (the soft-lock is gone).
2. **A Trap that is NOT the first card in hand -> offered, and it works** — the
   case the scan loop exists for.
3. **Empty hand -> not offered.**
4. **No regression** in the Trap-only cost or the per-copy once-per-turn.

✅ **IN-GAME CONFIRMED BY THE USER 2026-09-01 — TEST 3** (their words: *"That
fixed two of the bugs"*), on top of what test 2 already showed working:

* the effect is **offered**, **activates**, the cost is **paid**, and a Level 4
  or lower Ninja is **Special Summoned** from the Deck in the chosen position;
* **the cost is now Trap-only** — the `[0x0229AAFC+0x7C]` discriminator fixed the
  "discard any card" bug;
* **once per turn is PER COPY** — a second Upstart Special Summoned by the first
  can use its own effect; the `0x021E5060` / `0x0FB6` rider fixed the
  "second copy has no effect entry" bug. (This is the fix that could NOT be
  verified offline, so the in-game result is the only evidence for it — and it
  passed.)

✅ **The soft-lock test 3 found is FIXED and confirmed** — see *IN-GAME TEST 3*
below for the mechanism.

### KNOWN DEVIATION (recorded on the user's instruction, 2026-09-01)

**The printed "in face-up Defense Position or face-down Defense Position" is NOT
implemented.** The card summons through the engine's stock battle-position
chooser, which offers **face-up Attack or face-up Defense**. User-approved as a
known deviation when the card was shipped.

* **Why it is not built rather than not attempted:** the option set is the summon
  UI screen, not a parameter. `position == 2` is resolved in state 1 of the
  summon-execution machine (`0x02266E66`) by reading the player's answer out of
  the generic UI slot `[0x0229DD94+0x34]`, which the input decoder writes. There
  is no value meaning "offer face-down as a choice".
* **What blocks the achievable version** (remapping the two existing answers for
  this cid only): the remap must sit at `0x02266E66`, which **every** Normal and
  Special Summon in the game runs. An ov5 stub there crashes every summon in a
  puzzle, and ov3's dead-code supply is exhausted — largest free run 16 B, the
  126 B run at `0x0225F240` is 124/126 claimed — while `ov3_cave.py`'s BSS
  windows are off-limits until their canary passes.
* **The unblock:** run the ov3-cave canary (`notes/ov3-cave-findings.md`). After
  that PART F is a 22-byte ov3 splice to a ~48-byte stub keyed on
  `[0x02298A28+0x12] == 0x1464`, mapping answer 0 → `position=1, faceUp=1` and
  answer 1 → `position=1, faceUp=0`. Nothing else about the card changes.
* **The card's in-game text does not claim it.** The description is trimmed to
  *"Once/turn: send 1 Trap from your hand to the GY; SS 1 Lv4 or lower Ninja from
  your Deck."* — the same handling `patch_white_dragon_ninja` gives its own
  unenforced clause. 8 bytes remain against the 96 B floor if PART F lands.

Recorded in three places so it cannot be lost: this file, the module docstring,
the `apply_all_patches` step docstring, and the `card.upstart_golden_ninja` KB
fact.

### What else is NOT confirmed

* **PART F** — the printed *face-down* Defense Position option is not
  implemented; the engine's stock chooser offers face-up ATK / face-up DEF.
  Deliberate, user-acknowledged, blocked on an ov3 host (see below).
* **The Deck-side filter as a NEGATIVE control.** The summon works and returns a
  Level 4 or lower Ninja, but no test explicitly confirmed that a **non-Ninja**
  or a **Level 5+** monster is refused from the picker. The filter is
  `{aux 0x06, 0x0223CAB5, 0x00900002}`, whose meaning is well attested, and the
  offline probe counted exactly 5 legal candidates on a real board — but the
  in-game negative control was never run. One duel would close it.
* **NOT wired into `apply_all_patches`** — single-card ROM only until the user
  approves shipping.

## IN-GAME TEST 3 (2026-09-01) — the soft-lock

User's exact words:

> "There is another bug where the effect can be activated even when there isn't a
> proper target for discarding. Which will cause a soft-lock if the players
> activate the effect."

and on the clarifying questions:

> "1. No traps in the hand, 4 other spells/monsters"
> "2. I am trapped in the 'choose a card to discard' but cannot select a card to
> discard."

MY INTERPRETATION, confirmed before investigating: with a Ninja in the Deck but
**no Trap in hand**, the effect is still OFFERED; activating it opens the discard
picker with zero legal candidates and no way out. Item 1's filter is working
correctly — it rejects all four cards — there is simply nothing to pick.

### The cause: NOTHING checked the hand before the effect was offered

The offer-check chain is slot3 -> `0x021F0BDD` -> f2 `0x021F0419`, and f2 probes
**rel 0**, which is deliberately the **Deck** row ("is there a Ninja to
summon?"). No step consults the Hand row. This was written down as a risk when
the row order was chosen — *"the MENU does not pre-check the Deck"*, inverted —
but the predicted consequence was a harmless fizzle. It is a soft-lock.

`rom_upstart.ml3` (18:53) is the stuck state: `cost_state = 2` (picker open),
acting descriptor set, hand `132D 2321 17F4` with **no Trap**, three Upstarts on
the field.

### The fix: PART E gains a hand-scanning condition (`CAVE_UGN_COND`, 96 B)

`cls3 +0C` is a stub again. It walks the hand and only chains `0x021F0BDD` if a
legal cost exists:

* side = `desc[+2] ^ desc[+6]`; hand count = `player + side*0xB3C + 0x0C`;
* for `k` in `0 .. count-1`: set `CAVE_UGN_PROBE`, call
  `0x02243FE0(side, cid, k)`, clear it; stop on the first hit;
* no hit -> return 0 (never offered). Hit -> chain `0x021F0BDD`.

⚠️ **THE SCAN MUST LOOP.** Measured on `.ml3`: `0x02243FE0` **and**
`0x02243FA8` both test only hand slot `param` — `[filler, Trap]` returns 0 at
param 0 and 1 at param 1; `[filler, filler, Trap]` returns 1 only at param 2.
Neither primitive enumerates the hand. A single param-0 probe is precisely the
mistake that made in-game test 1 fail.

⚠️ **A LATCH IS CORRECT HERE, and was wrong for the cost.** `CAVE_UGN_PROBE`
wraps `0x02243FE0`, a **synchronous** count that has already returned before the
byte is cleared. The STAGE byte test 2 killed wrapped `0x021E7245`, which only
**arms** an asynchronous picker and returns. The arm now selects rel 1 when
either the probe flag is set OR the cost machine is running.

### Verified offline on the failing state (rider-free zone, so f1 does not mask it)

| hand | slot3 |
|---|---|
| no Trap, 3 cards (**the soft-lock**) | **0 — not offered** |
| no Trap, 4 cards | 0 — not offered |
| empty hand | 0 — not offered |
| Trap at index 0 / 1 / **2** | **1 — offered** (all three) |
| Trap only | 1 — offered |

⚠️ First run of that matrix returned 0 for EVERY case, which looked like a broken
scan. Tracing showed the opposite: the loop found the Trap at index 1 and reached
`found`, and the 0 came from the chained condition, because the descriptor's zone
already carried the `0x0FB6` rider. Re-running on a rider-free zone gave the
table above. **Trace before concluding.**

### BONUS: item 3 is corroborated from the user's own duel

Querying `0x021A1430(0, zone, 0x0FB6)` across `.ml3`'s zones gives
`{0: 0, 1: 1, 2: 1, 3: 1, 4: 0}` — the three zones holding Upstarts that used
their effects carry the rider, the two empty zones do not. That is live evidence
for the per-copy once-per-turn fix that could not be verified in the emulator.

    .venv-1/Scripts/python.exe _build_upstart.py
    -> data/over_the_nexus/working/rom_upstart.nds
    sha256 5e05009b749ef873383d08ff20539b13d80eba4e6d8aa4a622d6765438782133

**What test 2 established as WORKING (user-observed, not inferred):** the effect
is offered, activates, the cost is paid, the Ninja is Special Summoned, and the
position prompt behaves. Only the cost FILTER and the per-copy OPT were wrong.

Offline re-checks for each build are recorded under their own headings below
(BUILD 3 is the current one).

⚠️ **NOT wired into `apply_all_patches`** — single-card ROM only until the user
approves shipping.

Module: `otn_enhanced/cards/upstart_golden_ninja.py`.
Parts A (Ninja set code), B (two criteria rows, **DECK row at rel 0**),
C (shared row-hook arm, keyed on **the cost machine's state word
`[0x0229AAFC+0x7C]`**), D (cls3 record, `+0C` = the stock `0x021F0BDD`),
E (**one** ov5 cost stub, 44 B), **H (the ignition-condition registry row —
added after test 1)** and G (card_prop + text) are **built**.
**PART F (the printed battle position) is NOT built** — see the negative result
below; it is blocked on an ov3 host, not on understanding.

User decisions this session: donor **`0x1464`**; the donor **joins** the Ninja
set code (displacing Crimson Ninja `0x16B8`); position **remap the two answers**
(after the "build the prompt" choice was re-put once the UI finding landed).

Plan: `~\.claude\plans\upstart-golden-ninja-modular-rabbit.md`

---

## Confirmed (proven THIS session)

Preflight: `verify_knowledge` **377 facts / 341 PASS / 0 FAIL / 35 UNVERIFIED**.
`check_allocations` OK, ledger in sync, 130 phantom claims, **54 B free ov3 dead code**.

### The 3DS ships the card

`3ds_extract/partition0/romfs/duel/card/CARD_Indx_E.bin` (5888 × `{u32 name_off,
u32 desc_off}`) + `CARD_Prop.bin` record *i* masked `0x3FFF` →
**Upstart Golden Ninja = cid `0x26B1`**, name index 4952.

Its two rows in the 3DS main-effect registry `0x686CBC` (stride `0x0C`,
`{u16 cid, u16 aux, u32 handler, u32 param}`), found by direct scan:

| row | VA | cid | aux | handler | param |
|---|---|---|---|---|---|
| 1542 | `0x68B504` | `0x26B1` | `0xFFFF` | `0x004B1C5C` | `0x00000008` |
| 1543 | `0x68B510` | `0x26B1` | `0x0006` | `0x004B0358` | `0x00900002` |

Handler `0x004B1C5C` has **41 mates**, every one a hand-cost card (Spirit Ryu,
Spell Reproduction, Abyss Soldier, Lady Ninja Yae, **Darkflare Dragon `0x26E4`**,
Herald of Purple Light…). Handler `0x004B0358` has **exactly 1 mate — itself**,
so the SS half is bespoke on the 3DS too (it is the position choice that makes it
so).

### Criteria-word decode (both halves)

* **Low byte = card-type bitmask: `2` Monster / `4` Spell / `8` Trap.**
  Proof = printed text over the whole NDS criteria registry `0x022713C4`: every
  `…04` row is a Spell reader (Magician of Faith "Target 1 **Spell** in your GY",
  Spell Reproduction "Send 2 **Spells** from your hand", Fusion Sage, Iron
  Blacksmith Kotetsu, Naturia Landoise, Synchro Fusionist); every `…08` row a
  Trap reader (Mask of Darkness "Target 1 **Trap** in your GY", A Cat of Ill Omen
  "Choose 1 **Trap** from your Deck", Loki). Hanzo's `0x0E` = 2|4|8 = any type is
  the same encoding, and it matches Konami's 3DS param `0x08` exactly.
* **`0x00900002` = "Level 4 or lower monster"**; the field is
  **`(0x80 | level<<2) << 16`**. Confirmed at three distinct levels by printed
  text on handler `0x0223CAB5`:
  * `0x0090` Lv≤4 — A Hero Lives, Test Ape, Naturia Cliff, XX-Saber Emmersblade,
    Steelswarm Caller, Karakuri Nisamu, Queen's Pawn, Dragon Ravine
  * `0x008C` Lv≤3 — Shien's Footsoldier, Naturia Antjaw
  * `0x0088` Lv≤2 — Gusto Gulldo

  Independently corroborated by the in-game-confirmed NAST build, which computes
  the same field at runtime as `(0x80 | (sum << 2)) << 16`.

### NDS handlers (both already in the ROM)

* **`0x0223CB65` = send/discard from HAND** (KB-VERIFIED,
  `dispatch.criteria_hand_vs_deck_handlers`). **Naturia Landoise `0x2182`
  crit[1058] = `{0xFFFF, 0x0223CB65, 0x00000004}`** = "send 1 Spell Card from
  your hand to the GY" — our C1 row is that row with one nibble changed, `4`→`8`.
* **`0x0223CAB5` = Special Summon a set-code-filtered monster from the DECK.**
  All 32 of its rows are printed "Special Summon 1 &lt;archetype&gt; monster from
  your Deck" — Shien's Footsoldier (aux `0x1E` Six Samurai), Gravekeeper's Spy,
  Substitoad, A Hero Lives, Gem-Knight Alexandrite, XX-Saber Emmersblade,
  Steelswarm Caller, Karakuri Burei… Zero counter-examples.

### Record shape — a splice of three native cards (all dumped this session)

| cid | card | record |
|---|---|---|
| `0x20B8` | Beast Striker — "**Once per turn**, you can **discard 1 card** to SS 1 'Moja' **from your Deck**" | `cls3[562] {+04 0x02206CAD, +08 0, +0C 0x021F0BDD, +10 0x021E4ECD, +14 0}`; crit[974] `{0x20B7, 0x0223D075, 0x00000802}` |
| `0x22C0` | Gem-Knight Alexandrite — "Tribute this card; SS 1 '**Gem-Knight**' Normal Monster **from your Deck**" | `cls3[692] {+04 0x02206CAD, +08 0, +0C 0x021F0BDD, +10 0x021E50CD, +14 0}`; crit[1188] `{0x0054, 0x0223CAB5, 0x00000402}` |
| `0x2182` | Naturia Landoise — "**send 1 Spell Card from your hand** to the GY" | `cls3[622] {+04 0x0221C63D, +08 0, +0C 0x021F89A9, +10 0x021E7245, +14 0}`; crit[1058] `{0xFFFF, 0x0223CB65, 0x00000004}` |

Target record = **Alexandrite's, with Landoise's cost slot**:
`{+04 0x02206CAD, +08 0, +0C 0x021F0BDD, +10 ⟨OPT shim⟩, +14 0}`.

⚠️ **THIS NEXT LINE IS THE MISTAKE THAT COST IN-GAME TEST 1 — kept, struck
through, so it is not re-derived:** ~~`+0C 0x021F0BDD` is shared by Beast Striker
**and** Alexandrite, so it is the generic ignition activation condition, not
card-specific.~~ It is **NOT** generic: it binary-searches the per-cid registry
`0x0226FAFC` and returns 0 for any cid without a row. Two native cards sharing a
slot says nothing about whether that slot is cid-blind — the correct test is to
disassemble the slot itself, which is what PART H below finally did.

**`+10 0x021E7245` disassembled** (`0x021E7244`): `push {r3-r7,lr}` /
`ldrh r2,[r4]` (cid) / one pool-literal compare / `movs r7,#1` default,
`movs r7,#2` for that single cid — then a 4-state machine on `[r5+0x7C]`.
So **r7 is the send COUNT and an arbitrary donor sends exactly 1**. No code needed.

### Summon position is a REGISTER in deck-SS phase 0x7C — fully decoded

Phase `0x7C` body `0x02206E62..0x02206EE6` disassembled. It ends in

```
0226925C(r0 = side, r1 = &locator, r2 = faceUp, r3 = position, [sp] = (cid<<16)|flag)
```

with prologue defaults `str 1,[sp,#4]` → **faceUp = 1**, `movs r7,#2` →
**position = 2**, `movs r6,#0` → flag = 0. Three overrides:

| override | mechanism | cards | printed text |
|---|---|---|---|
| `position := 0` (`adds r7,r6,#0` @`0x02206E78`) | **16-entry sorted list @`0x022701EC`** searched by `bl 0x02022E14` with `movs r2,#0x10` | Giant Rat, UFO Turtle, Shining Angel, Mother Grizzly, Flying Kamakiri #1, Mystic Tomato, UFOroid, Warrior Lady of the Wasteland, Damage Condenser, Reverse of Neos, Mind Master, Genex Searcher, Assault Mode Activate, Naturia Cliff, Karakuri Nisamu | all "in **(face-up) Attack** Position" |
| `position := 1` (`movs r7,#1` @`0x02206EC8`) | per-cid compare tree | Phantom Magician `0x2361`, Tanngnjostr `0x2458` | both "in **face-up Defense** Position" |
| `faceUp := 0` (`movs r0,#0 ; str r0,[sp,#4]` @`0x02206EC2`) | per-cid compare tree | Bubonic Vermin `0x136A`, Apprentice Magician `0x1612`, Mecha Bunny `0x1E2C`, Super-Nimble Mega Hamster `0x2233` | **4/4** "in **face-down Defense** Position" |
| `flag := 1` (`movs r6,#1` @`0x02206EBE`) | per-cid compare tree | Magical Labyrinth `0x1232`, Assault Mode Activate `0x1F7A` | (low half of the word, not position) |
| *(defaults 1 / 2)* | — | Shien's Footsoldier, Six Scrolls, Alexandrite | no position printed = **player chooses** |

⇒ **position 0 = forced face-up ATK, 1 = forced DEF, 2 = player chooses**;
`faceUp = 0` = face-down DEF.

Corroborated independently by `dispatch.ss_from_list_position_mode`: a *different*
resolver `0x02207191` whose `r5` uses the same encoding (Silent Doom → 1 =
Defense, three others → 2 = player-chooses), in-game confirmed on Azure-Eyes.

Phase-0x7C literal pool (read this session): `0x02206F2C = 0x022701EC` (the
position list), `0x02206F24 = 0x0227020C` (the phase-0x7F auto-pick list, 18
entries), `0x02206F30/34/38/3C = 0x1232 / 0x2233 / 0x1F7A / 0x2361`.

### Donor `0x1464` — The Gross Ghost of Fled Dreams

`donor_scan 0x1464` → **VERDICT: CLEAN — no data structure names this cid.**
Lv4 DARK Fiend 1300/**1800** (DEF already matches the printed card).
* name slots `e30 f27 g37 i31 j10 k11 r30 s38`; "Upstart Golden Ninja" = 20 B
  fits six of eight, **j/k skipped** (`skip_name_if_too_long`).
* desc slots floor **96** (`e96 f106 g115 i114 j104 k107 r216 s103`) → one
  compact description ≤96 B fits all eight.

⚠️ **OPEN:** one ambiguous ARM9 data-region u16 hit at **`0x020A15F4`** — must be
explained before building (donor_scan warns ARM9 data holds numeric tables too).

Chosen over `0x16F2` (e31/e146) and `0x14D8` (e31/e140) by the user.

### Ninja roster — every Ninja is a legal target

Ninja set code `0x06`, thunk `0x020237D8`, list `@0x0209C722`, **9 entries, all
Level 4 or lower**: Armed Ninja `0x117B`(1), Crimson Ninja `0x16B8`(1), Strike
Ninja `0x16B9`(4), Lady Ninja Yae `0x1754`(3), Ninja Grandmaster Sasuke
`0x17DF`(4), White Ninja `0x18BE`(4), Goe Goe `0x1BCB`(4), Karakuri Sazank
`0x238B`(3), Karakuri Kuick `0x2467`(4). The two Ninjitsu Art **Traps**
(`0x1768`, `0x17FF`) are natural cost fodder.

Displacing **entry[1] Crimson Ninja `0x16B8`** with the donor `0x1464` keeps the
list strictly sorted **both with and without Hanzo**:
`{0x117B, 0x1464, 0x16B9, …}` and `{0x13E7, 0x1464, 0x16B9, …}`.

### Free slots for count-neutral inserts (cross-checked vs `PHANTOM_CLAIMS`)

* criteria phantoms **crit[130] `0x1449`** and **crit[131] `0x144C`** — adjacent,
  both unclaimed (`0x1452` is reborn_tengu's, `0x143D` is hanzo's — avoided)
* cls3 phantom **cls3[71] `0x144C`** — unclaimed
* membership **list A `0x0227134C`** (59 entries, sorted) has five phantom slots:
  `0x0E32, 0x0E6B, 0x0EA8, 0x1303, 0x234E`. List B `0x02271314` (27) has one:
  `0x234F`.

### Once per turn

`dispatch.turnlog_once_per_turn_pair` (VERIFIED; shipped in-game by Quasar PART
K): POST `0x021D2584(side, cid, 1, 0)`, QUERY `0x021A14E8(side, 0x0B, cid, 1)`.
Cid-generic. ⚠️ `0x021E7245` posts the latch only from a per-cid switch arm and a
donor's default arm posts **nothing** (measured for Darkflare), so the cost slot
must be a shim that posts the latch and then tail-calls `0x021E7245`.

---

## IN-GAME TEST 1 (2026-09-01) — FAILED, cause FOUND

User's exact words:

> "2. The effect is not offered. See .ml2"

and, on the clarifying question:

> "I selected upstart and there was no activate effect prompt."

MY INTERPRETATION, confirmed by the user before anything was investigated: the
donor is selectable on the field but **no activate-effect entry appears in its
menu**. Steps 3-9 were never reached.

### The savestate cleared the patch completely

`data/over_the_nexus/working/rom_upstart.ml2`, RAM0 @ file offset 0x24. Every
piece of the patch is LIVE, so this is the right ROM and the tables are right:

* `crit[132] {0x1464, 0xFFFF, 0x0223CB65, 0x00000008}` and
  `crit[133] {0x1464, 0x0006, 0x0223CAB5, 0x00900002}` — present, **in the right
  order** (cost at rel 0).
* `cls3[74] {+04 0x02206CAD, +08 0, +0C 0x0239DE01, +10 0x0239DE41, +14 0}`.
* Row hook installed at `0x02243BEC` (`58f1dcfc`); all three ov5 stubs resident
  with real bytes (COND `30b5041c...`, COST `70b5041c...`, ROWHOOK `184b1b6d...`).
* Board: the donor is face-up on **side 0 zone 2** (`word 05001464`).
* Hand holds **Ninjitsu Art of Decoy `0x17FF`** (a Trap — the cost is payable).
* Deck holds **Goe Goe `0x1BCB` x3** (Level 4 Ninjas — the effect has targets).

So the preconditions were all satisfied and the effect was still not offered.

### ⚠️ THE CAUSE: `0x021F0BDD` IS A PER-CID REGISTRY LOOKUP, NOT A GENERIC CONDITION

```
021F0BE0  ldrh r0,[r5]         ; the cid
021F0BE4  ldr  r1,=0x0226FAFC  ; a 146-row table
021F0BE6  movs r2,#0x92        ; 146 entries
021F0BE8  movs r3,#0xC         ; stride 12
021F0BEA  bl   0x02022E44      ; binary search BY CID
021F0BEE  adds r4,r0,#0
021F0BF0  beq  0x021F0C0C      ; NOT FOUND -> movs r0,#0 ; return   <<<< THE GATE
021F0BF2  ldr  r2,[r4,#4]      ; row +4 = f1, a precondition
021F0BF8  blx  r2              ; 0 -> return 0
021F0BFE  ldr  r2,[r4,#8]      ; row +8 = f2, the candidate check
021F0C04  blx  r2              ; ITS return value is slot3's
```

The donor has no row in `0x0226FAFC`, so slot3 returns 0 and the engine never
offers the effect. **This is a per-cid gate on the donor cid — CLAUDE.md's
pre-build checklist item (c) — and it was missed because the slot was reasoned
about as "generic" on the grounds that Beast Striker AND Gem-Knight Alexandrite
share it.** Sharing a slot between two cards is not the same as being cid-blind;
this is exactly `grep-the-template-cards-text-too`'s "no cid compare" != 
"card-agnostic", one level further in.

### THE TABLE, and the fix

`0x0226FAFC`, **146 rows x 12 B, `{u16 cid, u16 aux, u32 f1, u32 f2}`, sorted by
cid**, every row's aux = 0. It has **7 phantom rows** (0x0E3E, 0x0E7D, 0x0E86,
0x0EA9, 0x0EAE, **0x1446**, 0x1748), and **`0x1446` at row 11 sits exactly at the
donor's sorted position** (0x1446 < 0x1464 < 0x14A7 Rope of Life), so a
count-neutral insert there shifts **zero rows**.

Template rows:

| cid | card | f1 | f2 |
|---|---|---|---|
| `0x20B8` | Beast Striker — "Once per turn, you can discard 1 card to SS 1 'Moja' from your Deck" | `0x021F024D` | `0x021F0419` |
| `0x22C0` | Gem-Knight Alexandrite | `0x021F06E9` | `0x021F7979` |

**Beast Striker's pair is the right one** (hand cost + deck SS), and BOTH halves
were checked for cid gates this time rather than assumed:

* **f1 `0x021F024D` is cid-generic** — `ldrb r0,[r5,#2] ; ldrb r1,[r5,#3] ;
  ldr r2,=0x0FB6 ; bl 0x021A1430` is the attached-node walker
  (`otn-attached-effect-rider`, kind < 6 family) querying the **0x0FB6
  once-per-turn rider**; not-yet-used -> chain `0x021F0220`. No cid compare.
* **f2 `0x021F0419` is cid-generic** — `side = desc[+2]^desc[+6]`, a gate
  `0x021F0384`, then `param = 0x02234E78(desc)` and
  `0x02243FE0(side, desc[+0], param)` = the candidate count. No cid compare.
  At the menu `desc[+7] == 0`, so this probes rel 0 = the Trap-in-hand row, and
  the hand does hold `0x17FF`.

NOTE: f1 already enforces once-per-turn via the **0x0FB6 rider**, which this
patch never posts, so f1 always passes and the card's own turn-log latch
(CAVE_UGN_COST / CAVE_UGN_COND) remains the thing that enforces OPT. The two
mechanisms do not conflict; the native one is simply inert here.

### SECOND CAUSE, found by OFFLINE A/B on the failing state (no duel spent)

PART H alone is **necessary but not sufficient**. Driving `0x021F0BDD` under the
savestate Thumb emulator (`scratch/thumbemu.py`) showed the registry row makes
the lookup succeed and f1 pass, but **f2 `0x021F0419` still returns 0**, and the
trace pinned it to `0x02243FE0` returning **0 candidates**.

**Harness validated first** (against native cards on the same state, so the tool
is not the thing being measured): Pot of Duality -> 34 with param 0 (deck size is
34) and 1 with param 1; Naturia Landoise `{0xFFFF, 0x0223CB65, 0x04}` -> **1**
(the one Spell in hand); Foolish Burial `{0xFFFF, 0x0223CAD9, 0x02}` -> **11**
(monsters in a 34-card deck); Shien's Footsoldier and Gem-Knight Alexandrite ->
**0** (no Six Samurai / Gem-Knight). All correct.

#### The card-type encoding IS right — confirmed by isolation

Forcing the hand to a single card and probing handler `0x0223CB65`:

| hand forced to | `00` | `02` | `04` | `08` | `0C` | `0E` |
|---|---|---|---|---|---|---|
| **Trap** `0x17FF` (card_type 14) | 1 | 0 | 0 | **1** | 1 | 1 |
| **Spell** `0x2321` (card_type 13) | 1 | 0 | **1** | 0 | 1 | 1 |
| **Monster** `0x21F5` (card_type 8) | 1 | **1** | 0 | 0 | 0 | 1 |

So **2 = Monster, 4 = Spell, 8 = Trap is CORRECT** and
`dispatch.criteria_word_card_type_mask` stands. The word `0x00000008` is right.

#### ⚠️ THE REAL CAUSE: THE HAND PROBE IS POSITIONAL

With the full 5-card hand the same probe returns 0 for `0x08`, but moving the
Trap to hand index 0 returns 1:

```
original hand order (Trap at index 4), word 08 -> 0
Trap moved to index 0,                 word 08 -> 1
Trap + any 1/2/3 others, Trap first,   word 08 -> 1
original order, word 04 -> 1   (index 0 IS a Spell)
original order, word 02 -> 0   (index 0 is not a monster)
```

Every result is explained by **the probe testing ONLY hand slot `param`**. This
is the memory note `otn-gates-of-dark-world-shipped` verbatim — *"0x02243FE0's
param is a row selector for GY but a candidate INDEX for HAND"* — a fact already
in the KB that I did not apply. `0x02234E78` returns 0 for the donor, so the
offer-check probes hand index 0 and the card is offered only when the Trap
happens to be the first card in hand.

#### THE FIX, measured rather than guessed

Put the **DECK row at rel 0** so the offer-check counts Ninjas in the Deck (a
proper count, not an index probe). Measured on the failing state:

```
rel0 = cost(hand)  -> 0x02243FE0 param0=0 param1=0 ; slot3 0x021F0BDD -> 0
rel0 = effect(deck)-> 0x02243FE0 param0=5 param1=5 ; slot3 0x021F0BDD -> 1  <-- OFFERED
```

(5 = the Level 4-or-lower Ninjas in that Deck: 3x Goe Goe plus copies of the
donor, which is itself a Ninja after PART A.)

**But desc[+7] can no longer be the discriminator**: the cost runs BEFORE
`0x02217FB4` sets the flag, so the menu check and the cost BOTH see
`desc[+7] == 0` and they need different rows. The replacement is the **STAGE
byte**, which is exactly Darkflare's precedent in this same shared module:

* `CAVE_UGN_STAGE == 0` -> rel 0, the Deck/Ninja row (menu offer-check, and the
  deck-SS resolver)
* `CAVE_UGN_STAGE == 1` -> rel 1, the Hand/Trap row (only while the cost runs)

with the cost stub setting STAGE around its delegation to `0x021E7245`.

⚠️ **Also confirmed by measurement:** `[0x0229A9FC+0x50]` is **0** in this
savestate, so the shared row-hook stub took its `cmp r3,#0 ; beq native` exit and
**my arm never fired in any of these runs** — every probe used the native
param path with `r4 = 0` (the donor is not in list A). That is why param 0 and
param 1 gave identical answers, and it means the measurements above are clean
reads of "rel 0", which is what makes the row-order conclusion sound.

## IN-GAME TEST 2 (2026-09-01) — the effect now FIRES; two bugs left, both found

User's exact words:

> "It lets me discard any card see .ml3
>
> I am given two choices, SS ATK and SS DEF, the SS Face-up DEF is fine. But
> there is no SS in face-down def position. The chosen card is special summoned
> though.
>
> If I special summon another upstart golden ninja, I cannot the summoned upstart
> golden ninjas effect. See .ml4"

and on the clarifying questions:

> "The second copy's effect was absent from the menu."
> "For item 1, the card was sent and the ninja is summoned."

**PART H + the row reorder WORKED**: the effect is offered, activates, the cost is
paid, and the Ninja is Special Summoned in the chosen position. Item 2 (no
face-down option) is the KNOWN, accepted PART F deviation, not a regression.

### ITEM 1 — the cost accepts ANY card. Cause: the STAGE latch is a timing window

`rom_upstart.ml3`, captured with the hand picker open:

```
CAVE_UGN_STAGE @0239DEA0   = 0        <-- MY LATCH IS ALREADY CLEAR
sel mode  [0x0229DD94+0x4C] = 8       <-- the mode-8 HAND selection IS live
cost state[0x0229AAFC+0x7C] = 2       <-- the cost machine is mid-run
acting desc 0x0229A7FC: cid 1464 +3=02 +5=03 +7=00
```

The cost stub sets STAGE, calls `0x021E7245` — which only **arms** the selection
and returns — then clears STAGE. The candidate filtering happens LATER, when the
picker runs, by which time STAGE is 0, so the arm hands back rel 0 (the Deck row)
and the hand picker ends up unfiltered. A latch around a call that merely sets up
an asynchronous UI cannot work.

**FIX: drop the latch and key the arm on `[0x0229AAFC+0x7C] != 0`** — the cost
machine's own state word. Measured across all three savestates, it is exactly the
discriminator wanted:

| moment | cost state | row wanted | savestate |
|---|---|---|---|
| menu offer-check | **0** | rel 0 Deck | `.ml2`, `.ml4` |
| cost / hand picker | **2** | rel 1 Hand | `.ml3` |
| deck-SS resolver | **0** | rel 0 Deck | zeroed at `0x02217FBA` |

and the reset is proven, not assumed: the activation machine does
`movs r1,#0 ; str r1,[r4,#0x7c]` at `0x02217FB6`/`0x02217FBA` (r4 = `0x0229AAFC`)
in the same breath as `strb r0,[r5,#7]`, so by the time the resolver runs the
word is back to 0. No latch, no window, one global read.

### ITEM 2 — expected

Two options offered (face-up ATK / face-up DEF), face-up DEF correct, no
face-down. This is PART F, never built. Unchanged.

### ITEM 3 — the second copy is refused. Cause: the OPT latch is CID-keyed

`rom_upstart.ml4` shows **two donors on the field** (zone 2 `04801464`, zone 3
`05801464`) and `desc[+7] = 1`. My `CAVE_UGN_COND` queries
`dispatch.turnlog_once_per_turn_pair`'s log, which is keyed on the **cid** — so
the first copy's use locks every copy for the turn. The printed text is once per
turn PER COPY. This is the deviation flagged when the card was planned, now
observed.

**FIX: use the engine's own per-copy rider instead.** PART H's registry row
already routes through f1 `0x021F024D`, which queries
`0x021A1430(desc[+2], desc[+3], 0x0FB6)` — **side + SLOT**, i.e. per copy. The
matching POST is the shared "you can" tag **`0x021E5060`**, disassembled this
session:

```
021E5070  ldrb r0,[r4,#2]   ; side
021E5072  ldrb r1,[r4,#3]   ; SLOT  <-- per copy, not per cid
021E5074  ldr  r2,=0x0FB6
021E5076  movs r3,#2
021E5078  bl   0x021C479C   ; attach the node
```

So the cost stub should post `0x021E5060` and NOT the cid-keyed turn log — and
then **`CAVE_UGN_COND` can be deleted entirely**, with `+0C` going back to the
native `0x021F0BDD`, because f1 already performs the once-per-turn check. The
card shrinks to ONE ov5 stub.

⚠️ Watch `dispatch.slot3_reevaluated_after_cost`: a condition the cost consumes
can make an effect activate and then fizzle. It says the single-pick template
does NOT re-check and only multi-select effects are bitten; this card's `+14` is
0, so there is no target template at all. Flagged, not assumed.

### BUILD 3 (2026-09-01) — both fixes in, and the card got SIMPLER

sha256 `5e05009b749ef873383d08ff20539b13d80eba4e6d8aa4a622d6765438782133`,
`verify()` **35/35**. The card is now **ONE 44-byte ov5 stub** — the condition
stub and the STAGE byte are both gone, because the engine's own machinery does
their jobs once the registry row exists:

* `cls3 +0C` is back to the stock `0x021F0BDD` (PART H routes it through f1,
  which already queries the per-copy rider).
* `CAVE_UGN_COND` and `CAVE_UGN_STAGE` deleted; `CAVE_UGN_COST` moved to
  `0x0239DE00`, `CAVE_FREE` back to `0x0239DE60`.

**Offline verification of ITEM 1 — PASSES**, on the three real states:

| state | cost state | `0x02243FE0` | reading |
|---|---|---|---|
| `.ml3` (picker open) | 2 | **1** | rel 1, the Hand/Trap row — filtered |
| `.ml4` (idle) | 0 | 3 | rel 0, the Deck row |
| `.ml2` (menu) | 0 | 4 | rel 0, the Deck row |

**ITEM 3 is NOT verifiable offline — same harness limit, with a control.**
Posting the rider via `0x021E5060` reaches the attach (`0x021C479C` called once,
traced) and the function returns 1, but the subsequent
`0x021A1430(side, slot, 0x0FB6)` query still reads 0. `0x021C479C` is the SAME
writer `0x021D2584` tail-calls, and that post was already shown invisible in a
static run with Pot of Duality as a native control — the emulator does not
process the event queue. So item 3's fix rests on construction, not measurement:
the tag is keyed `side + SLOT` (disassembled) and f1 queries exactly that key
(disassembled). **It must be confirmed in-game.**

## Ruled Out

* **`0x021E4ECD`** (Beast Striker's cost) — it is the *unfiltered* "discard 1
  card". The Trap filter has to come from a criteria row, which forces the
  hand-send cost `0x021E7245` (Landoise / Darkflare) instead.
* **cls1 / cls2 record** — this is an on-field ignition, so cls3. Every native
  card of this shape (Beast Striker, Alexandrite, Substitoad, Mind Master) is
  cls3.
* **Cloning Ninjitsu Art of Transformation's resolver `0x0221B2FD`** for the
  position. Two reasons: NAST froze three times pointing cls0 +04 at it, and —
  measured this session — **it hardcodes face-up**.

### ⚠️ THE NDS DOES NOT IMPLEMENT TRANSFORMATION'S FACE-DOWN OPTION

Ninjitsu Art of Transformation `0x1768` (`cls0[524] {+04 0x0221B2FD, +08
0x021DA1C9, +0C 0x021F7D05, +10 0x021E7C89, +14 0}`) is printed "…in face-up
Attack Position **or face-down Defense Position**". Its resolver calls the same
commit `bl 0x0226925C` @`0x0221B5D8`, and immediately before it:

```
0221B5A8  ldrh r1,[r4]        ; cid
0221B5AC  movs r3,#2          ; position = 2 (player chooses)
0221B5AE..B5B6                ; two pool compares
0221B5B8  movs r3,#0          ;   -> forced face-up ATK for those two cids
0221B5D6  movs r2,#1          ; faceUp = 1   <-- HARDCODED
0221B5D8  bl   0x0226925c
```

So **no card in the ROM ever asks the player face-up-or-face-down.** There is no
template for the printed position choice; PART F is genuine RE.

---

## STEP 0 RESULTS — the row-addressing question is CLOSED (and the answer was "no")

### ⚠️ BOTH CONSUMERS PASS param = 0 — a two-row donor's clauses WOULD COLLAPSE

This kills the "pure data" plan. Measured statically this session:

* **The deck-SS side passes 0.** `0x02234E78` (the param provider) is five
  membership-list tests followed by a per-cid ordered compare tree. The donor
  `0x1464` is in **none** of the five lists (dumped in full):
  `0x022710E2`×0x11 → `[r5+0xC]`, `0x02271104`×0x1C → `0x10000000`,
  `0x022710B2`×0x0C → `[r5+0x14]`, `0x0227109C`×0x0B → `[r5+0x16]`,
  `0x022710CA`×0x0C → `[r5+0x18]`. The tree's **default leaf `0x022355F0` is
  `movs r0,#0 ; pop`** — param **0**.
* **The cost side also passes 0.** `0x021E7245` state 1 @`0x021E7298`:
  `ldr r0,[r5,#0x74]` (pass counter, zeroed by state 0) / `movs r2,#1` /
  `cmp r0,#0 ; bne` / `movs r2,#0` / `rsbs r2,r2,#0` / `bl 0x0224B9F0`.
  And `0x0224B9F0` @`0x0224B9F8` is **`str r2,[r4,#0x50]` = THE PARAM**.
  Our card sends exactly 1, so only the first pass runs ⇒ **param = 0**.

⇒ `0x02243B9C` yields `r4 = 0` on both paths ⇒ both read **relative row 0** ⇒ the
Trap cost and the Ninja search would be the same row. Exactly the silent swap
`otn-param-provider-internal-hook` warns about.

**Consequences for the plan:**
* **PART C (membership list A) is DROPPED** — list A only distinguishes
  `param == 0` from `param != 0`, and both are 0. It buys nothing. The phantom
  `0x1303` is *not* claimed after all.
* **A third arm on the shared `criteria_row_hook.py` is REQUIRED**, not a
  fallback. The arm writes `r4` directly and jumps to the tail `0x02243EEE`,
  short-circuiting the list-A logic entirely.

### THE DISCRIMINATOR IS `desc[+7]`, and it is proven

Darkflare's arm keys on `desc[+5] == 3`, but that cannot work here: both of our
steps run from **one activation of one cls3 cid**, so `desc[+0]` and `desc[+5]`
are identical for both. What differs is **`desc[+7]` = "the cost has already
run"**. Activation state machine `0x02217F80`, disassembled this session:

```
02217F8C  str  r5,[r0,#0x50]   ; [0x0229A9FC+0x50] = the acting descriptor
02217F8E  ldrb r0,[r5,#7]      ; desc[+7]
02217F92  bne  0x02217FB2      ; already run -> skip the cost
02217FA2  bl   0x0224AE50      ; RUN THE COST (slot4)
02217FB4  strb r0,[r5,#7]      ; desc[+7] := 1, AFTER the cost
02217FBE  movs r0,#0x76        ; yield -> resolution follows
```

So `desc[+7] == 0` while the cost selects, `== 1` by the time the deck-SS
resolver runs. The arm is therefore:

* `desc[+0] == 0x1464` and `desc[+7] == 0` → `r4 = 0` → **row 0 = Trap from hand**
* `desc[+0] == 0x1464` and `desc[+7] != 0` → `r4 = 1` → **row 1 = Ninja from Deck**

Line `0x02217F8C` also confirms the hook's descriptor pointer
(`[0x0229A9FC+0x50]`) is populated on exactly this path.

### Side effect to watch in-game

`dispatch.slot3_reevaluated_after_cost`: slot3 (`+0C 0x021F0BDD`,
"activatable iff a candidate exists") is evaluated **twice** — at the menu
(`desc[+7] == 0`, so it probes row 0 = "have I a Trap?") and again
mid-activation (`desc[+7] == 1`, so it probes row 1 = "is there a Ninja in my
Deck?"). Fortuitously both are real conditions, but the menu will **not**
pre-check the Deck. **Add an in-game test: activate with a Trap in hand and NO
Ninja in the Deck** — expect it to be offered and then fizzle. That is a
deviation to report, not to hide.

## Open Questions

1. ~~Do the two criteria rows get addressed separately?~~ **CLOSED — no. See
   STEP 0 RESULTS above; the shared row hook is required.**
2. ~~Is there a position code that offers a player choice including face-down?~~
   **CLOSED — no evidence of one. See STEP 0 / PART F below.**
3. ~~What is the ARM9 hit at `0x020A15F4`?~~ **CLOSED — not a cid structure.**
   The words around it are a monotonically increasing numeric ramp
   (`…13A6 13E6 1425 1464 14A2 14E0 151E 155B…`, deltas shrinking 0x45→0x3E) —
   a curve/math lookup table in which `0x1464` merely occurs as a value. Exactly
   the "ARM9 data holds numeric tables too" case `donor_scan` warns about.
   **The donor `0x1464` is entanglement-free.**

### STEP 0 / PART F — the position codes (NEGATIVE RESULT)

Readers of the summon request block `0x02298A28` located by literal-anchored
scan. `+8` (position) is read at `0x022614F6, 0x02261566, 0x022619FA,
0x02262340, 0x02262CCE, 0x02262E0A, 0x02263A32, 0x022646EE, 0x02265102,
0x022654A8, 0x02266E66`; `+6` (faceUp) at `0x0226006A, 0x02260182, 0x02262E92,
0x0226321A, 0x022634A6, 0x02264930, 0x0226548E, 0x02265700, 0x02268862,
0x02269154, 0x0226B4CE`. All in the summon-execution region.

The two decoded consumers treat position as a **battle-position bitmask
selector**, not a UI mode:

```
02261566  ldrh r0,[r4,#8] ; movs r6,#0x40 ; cmp r0,#0 ; bne ; movs r6,#0x10
022614F6  ldrh r0,[r0,#8] ; cmp r0,#0     ; bne      ; movs r5,#0x10
```

i.e. **position 0 → mask 0x10 (Attack), position ≠ 0 → mask 0x40 (Defense)**.
`faceUp` is carried as a **separate boolean** at `+6` throughout.

⇒ **No code in this field means "let the player choose, including face-down".**
The enum only distinguishes Attack / Defense / (default 2, which the *separate*
resolver-side fact `dispatch.ss_from_list_position_mode` shows the player picks
between the two face-**up** positions). Nothing anywhere couples the face-down
boolean to a player choice.

⚠️ **Correction to my own scan:** `0x0219AFB6` (`ldr r1,[r0,#8] ; cmp r1,#2`)
initially looked like a "position == 2 ⇒ ask the player" site. It is **not** —
its `r0` is reloaded from `0x02299114`, a different block. Discarded.

**Consequence:** the printed "face-up DEF **or** face-down DEF" cannot be bought
with a constant.

### THE NATIVE BATTLE-POSITION CHOOSER — found, and it is a UI-layer screen

User reaffirmed "build the prompt" after the negative result above, so the
chooser was tracked down. **`position == 2` is resolved in the summon-execution
state machine**, table `0x02266E34` / add-pc `0x02266E36`, 23 arms; **state 1**
is its body:

```
02266E62  adds r0,r0,#1 ; strh r0,[r4,#0x24]   ; state 0: advance, fall through
02266E66  ldrh r0,[r4,#8]   ; position
02266E68  cmp  r0,#2 ; bne 0x02266E7C
02266E6C  ldr  r0,=0x0229DD94                  ; the generic UI-answer block
02266E6E  ldr  r0,[r0,#0x34]                   ; THE PLAYER'S ANSWER
02266E70  strh r0,[r4,#8]                      ; position := answer
02266E74  cmp  r0,#0 ; bne
02266E78  movs r0,#1 ; strh r0,[r4,#6]         ; answer 0 -> faceUp := 1
```

So the native mapping is **answer 0 → position 0 (Attack) + faceUp 1**, and
**answer 1 → position 1 (Defense)**. A real 2-option chooser exists.

⚠️ **But `[0x0229DD94+0x34]` is the GENERIC UI-answer slot, fed by the input
layer, not by an effect-table parameter.** Its writers are the input/replay
command decoder (`0x0219E878`, `0x0219E89C`, `0x0219E8BC`, `0x0219E8E0`,
`0x0219E8F4` — all inside a packet decode using `blx 0x0214C05C` on `[r5+0xC/D/E]`),
plus per-effect writers. There is **no parameter that says which options to
show**: the option set is the summon UI screen itself.

⇒ **Adding a genuine third "face-down" button is a SUMMON-UI change, shared by
every summon in the game — not an effect-table change.** That is a different and
much riskier class of edit than anything shipped in this repo.

**The achievable version** (correct mechanics, wrong label): hook state 1 for our
donor's summon only and remap the existing two answers —
`answer 0 → position 1, faceUp 1` (face-up DEF), `answer 1 → position 1,
faceUp 0` (face-down DEF). The player gets a true 2-way choice with exactly the
printed game effect, but the buttons still read **Attack / Defense**.
**Escalated to the user 2026-09-01; awaiting their call.**

## Next Experiment

**Step 0 (static, no duel, no build):**

1. Disassemble `0x02234E78` to its **default return** for a cid in none of its
   membership lists, and read `0x021E7245`'s param immediates. Answers Q1 and
   decides whether the card is pure data or needs a third arm on the shared
   `criteria_row_hook.py` (keyed `desc[+5] == 3`, Darkflare's arm J precedent).
2. Read `0x020A15F4` in context (± 0x40, plus whatever table it sits in) to
   settle Q3.
3. Find the readers of `[0x02298A28+8]` and enumerate the legal position codes to
   settle Q2.

Do **not** write PART B or PART F until 1 and 3 respectively are settled.

---

## PART F — blocked on a HOST, not on understanding

The user chose "remap the two existing answers" (Attack button -> face-up DEF,
Defense button -> face-down DEF: correct mechanics, wrong labels). **It could not
be built this session, and the blocker is hosting, not knowledge:**

* The remap must sit at **state 1 of the summon-execution machine (`0x02266E66`)**
  — the only place the player's answer is turned into a position. That site is
  the **shared summon path**: every Normal and Special Summon in the game runs
  it.
* An ov5 stub there would crash **every summon** in a puzzle (overlay 41 evicts
  ov5), which is a far wider blast radius than Hanzo's accepted deck-search cost.
* A self-guarding ov3 splice does not fit: the native block is 22 B and a cid
  guard plus the native replay needs ~32 B, with no adjacent slack (the 23-arm
  jump table ends exactly at `0x02206E62`).
* **ov3's dead-code supply is exhausted:** largest fully-free run is **16 B**
  (the tail of escuridao's block); the 126 B run at `0x0225F240` is **124/126**
  claimed by handss_banish_cost + NAST. The stub needs ~48 B.
* `ov3_cave.py`'s BSS windows are the natural host but are explicitly off-limits:
  *"Do not claim a CAVE3_* slot until the canary passes."*

**Next experiment for PART F:** run the ov3-cave canary (`notes/ov3-cave-findings.md`)
so a `CAVE3_*` slot becomes claimable; then PART F is a 22-byte ov3 splice to a
~48-byte universal-cave stub keyed on `[0x02298A28 + 0x12] == 0x1464`, mapping
answer 0 -> `position=1, faceUp=1` and answer 1 -> `position=1, faceUp=0`.
Nothing else about the card changes.

## Composition note — the shared row hook

Adding the third arm changes the SHARED stub's bytes (108 B -> 132 B), so
**`rom_all_patches.nds` as built before 2026-09-01 now FAILS** the row-hook
byte check (measured: 6/7 pass, the stub-presence check fails). That is a
**rebuild requirement, not a behaviour change** — verified structurally: the
guard order is preserved (`0x0FB1`, `0x1646`, then `0x1464`) so Lightpulsar and
Darkflare match their own arms before ever reaching the new guard, and the
`native` / `tail` epilogues are identical in both stubs (LIST_A literal
`0x0227134C`, resume `0x02243BF1`, tail `0x02243EEF`), so every other cid still
falls through to the same place. Rebuild the chain when this card ships.

⚠️ The Ninja set-code list is now contended by **three** patches: hanzo drops
Armed Ninja `0x117B`, white_dragon_ninja drops Karakuri Sazank `0x238B`, and this
drops Crimson Ninja `0x16B8`. All three inserts are sort-neutral in any order,
but the archetype loses three real members if all three ship.

## KB contributions — DONE this session

`author_facts.py` regenerated: **383 facts, 346 PASS, 0 FAIL, 37 UNVERIFIED**
(was 377 / 341 / 0 / 36). All five new engine facts carry passing proofs.

* **`counter.deck_ss_phase_arms` CORRECTED in place** — its "tweaks those three
  defaults and NOTHING else" now carries a ⚠️ CORRECTED 2026-09-01 note naming
  the missed fourth override (the 16-entry list `@0x022701EC`) and pointing at
  the new fact.
* **`counter.deck_ss_position_encoding`** (VERIFIED, new) — the full four-way
  position/faceUp decode, the state-1 UI resolution, `[0x02298A28+0x12]` = the
  summoned cid, the "option set is the UI screen" warning, and Transformation's
  hardcoded face-up.
* **`dispatch.criteria_word_card_type_mask`** (VERIFIED, new) — 2/4/8, with
  Vampire Lord `0x1522` (owns both a 4 row and an 8 row) as the internal control.
* **`dispatch.criteria_word_level_cap`** (VERIFIED, new) — `(0x80|lvl<<2)<<16`,
  proven at Lv2/Lv3/Lv4.
* **`dispatch.criteria_deck_ss_setcode_handler`** (VERIFIED, new) — `0x0223CAB5`,
  including the structural tell that no row on it carries aux `0xFFFF`.
* **`dispatch.cost_flag_desc7_separates_two_rows`** (VERIFIED, new) — both
  consumers pass param 0; `desc[+7]` is the discriminator.
* **`card.upstart_golden_ninja`** (new) — the build record, explicitly
  AWAITING IN-GAME TEST, with both known deviations written down.
