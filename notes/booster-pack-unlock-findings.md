# Booster-pack unlock — US AR code reversed, EU equivalent derived

Session: 2026-08-03. Goal: understand the US "unlock all booster packs" AR code
and port it to EU (`BYYP`, `data/over_the_nexus/working/rom.nds`).

Source AR code (US, `BYYE`):

```
52159ED0 02158DE4      ; if [0x02159ED0] == 0x02158DE4
02159E9C FFFFFFFF      ;   [0x02159E9C] = 0xFFFFFFFF
02159EA0 FFFFFFFF      ;   [0x02159EA0] = 0xFFFFFFFF
D2000000 00000000      ; endif / flush
```

## Confirmed (this session)

**Everything below was derived from the ROM images, not from memory.**
US oracle: `data/over_the_nexus/backup/unpatched/us.nds`.
EU oracle: `data/over_the_nexus/working/rom.nds` (ov10 image is byte-identical to
`backup/unpatched/eu.nds` — checked).

### The addresses live in overlay 10, which is the card shop

- ov10 US: ram `0x0214C920`, size `0xBF40`, bss `0xE500` (bss = `0x02158860` ..
  `0x02166D60`). All four AR addresses are in that **BSS**, so they are runtime
  data, not overlay code. Verified: no overlay's code image contains
  `0x02158DE4` at `0x02159ED0`.
- ov10 is the **"Getpack" (booster-pack shop) screen** — string table at
  `0x02158384`+: `Getpack/rare.LZNCLR`, `Getpack/pack_bottan.*`,
  `/pack/pack%02d.LZ5bg`, `/pack/l_pack%02d.LZ5bg`, `/pack/s_pack%02d.LZ5bg`.

### The shop object and the unlock bitfield

- The shop's C++ singleton is at **US `0x02158DF0` / EU `0x02158D10`**.
  Proof: ctor-registration thunk at US `0x02158230` / EU `0x02158150`
  (`ldr r4,=<obj>; bl <ctor>; ldr r1,=<dtor>; ldr r2,=<node>; blx <atexit>`).
- Layout inside the object (offsets confirmed by code, not guessed):
  - `+0x0000` array of pack entries, stride **0x34** (`mov r0,#0x34; mla r1,r6,r0,sl`)
  - `+0x10A4` u16 — number of packs currently in the list (`strh r6,[r2,#0xa4]`
    US `0x0214E504` / EU `0x0214E424`, r6 = count of *unlocked* packs)
  - `+0x10A8` u32 — selected pack price (US `0x02155830`: `DP -= price`)
  - **`+0x10AC` u32[3] — the pack-unlock BITFIELD** (bit *i* = pack index *i*)
- Bit-test idiom (signed `i/32`, `i%32`), both sites identical in US and EU:

```
asr  r0, i, #4                 ; \
add  r0, i, r0, lsr #27        ;  } r0 = i / 32   (signed)
asr  r0, r0, #5                ; /
add  r0, sl, r0, lsl #2        ; obj + (i/32)*4
add  r0, r0, #0x1000
ldr  r2, [r0, #0xac]           ; word (i/32) of bitfield at obj+0x10AC
rsb  r0, r1, i, lsl #27        ; \  r0 = i % 32
add  r0, r1, r0, ror #27       ; /
tst  r2, fp, lsl r0            ; test bit i
beq  <skip pack i>
```

Only **two** consumers exist; `+0x10AC` is **never written** inside ov10:

| consumer | US | EU | loop bound | role |
|---|---|---|---|---|
| loop A | `0x0214DB30` | `0x0214DA50` | `cmp r6,#0x51` → i = 0..80 | syncs per-pack records into master state |
| loop B | `0x0214E000` | `0x0214DF20` | `cmp sb,#0x3c` → i = 0..59 | builds the visible shop list; `r6` counts hits → `+0x10A4` |

Pack index *i* maps to pack ID *i+1* (`add r0,sb,#1; strh r0,[r5]`).
`scratch/bin2/card_pack.bin` has 80 distinct pack IDs spanning **1..81**
(ID 60 unused) — consistent with loop A's 81 iterations.

### The AR condition is an "is the shop loaded" guard

`0x02158DE4` and `0x02159ED0` are **static-destructor list nodes**, not data
pointers. The ctor thunks register them in order:

- US `0x02158230`: obj `0x02158DF0`, dtor `0x0214D8D0`, node `0x02158DE4`
- US `0x02158260`: obj `0x02159EF8`, dtor `0x0214EF7C`, node `0x02159ED0`

The second node's `next` field (`+0x00`) points at the first node. So
`[0x02159ED0] == 0x02158DE4` is exactly *"ov10's static ctors have run"* — it
stops the writes from corrupting whatever else occupies that RAM when the shop
overlay is not resident. (Several overlays share this address range.)

### US → EU mapping

EU ov10 is the **same size** (`0xBF40`) and loads **0xE0 lower**
(`0x0214C840` vs `0x0214C920`). Word-level diff of the two decompressed images:
213 differing words are exactly `-0xE0` relocations into ov10, the rest are
`BL`/`B` displacements into ARM9 static (EU arm9 is `0xA0` smaller). **No
structural difference.** Every site below was re-read from the EU image and the
instruction encodings match US byte-for-byte.

| item | US | EU |
|---|---|---|
| ov10 load base | `0x0214C920` | `0x0214C840` |
| shop object | `0x02158DF0` | `0x02158D10` |
| unlock word 0 (packs 1–32) | `0x02159E9C` | **`0x02159DBC`** |
| unlock word 1 (packs 33–64) | `0x02159EA0` | **`0x02159DC0`** |
| unlock word 2 (packs 65–81) | `0x02159EA4` | **`0x02159DC4`** |
| guard address | `0x02159ED0` | **`0x02159DF0`** |
| guard expected value | `0x02158DE4` | **`0x02158D04`** |
| pack count u16 (`+0x10A4`) | `0x02159E94` | `0x02159DB4` |
| pack price (`+0x10A8`) | `0x02159E98` | `0x02159DB8` |
| loop A bit-test `ldr` | `0x0214DB30` | `0x0214DA50` (`ac 20 90 e5`) |
| loop B bit-test `ldr` | `0x0214E000` | `0x0214DF20` (`ac 20 92 e5`) |

**EU AR code (faithful port of the US one):**

```
52159DF0 02158D04
02159DBC FFFFFFFF
02159DC0 FFFFFFFF
D2000000 00000000
```

### Who writes the bitfield — and why it is NOT in the save

**The mask is derived, not stored.** It is recomputed from scratch every time the
shop list is built, by a function in **overlay 1** (ov1 is resident *under* ov10:
ov1 ends at EU `0x0214C840`, exactly ov10's load address). ov10 calls it twice
(EU `0x0214DEA8`, `0x0214DEE4`); both pass `r1 = [obj+0x10D8]`, but only the
**second** passes `r0 = obj+0x10AC` — the first writes the mask into a separate
scratch buffer (`r7`, zeroed just above the call), presumably to diff against the
live mask for "new since last visit". Both go through the same jump table.

`unlock_mask(u32 *bits, int)` — US `0x021451D8` / **EU `0x021450F8`**:

```
r7 = 0                                   ; pack index
loop:
  r0 = r7 + 1                            ; pack ID
  cmp  r0, #0x3c
  addls pc, pc, r0, lsl #2               ; jump table, one arm per pack ID 1..60
  <arm: this pack's unlock condition>
     fail -> b <loop tail>               ; bit left clear
     pass -> b <set-bit tail>            ; sets bit, then notifies "new pack"
  add r7,r7,#1 ; cmp r7,#0x3c ; blt loop
```

Condition kinds observed in the arms (EU addresses):

| kind | code | meaning |
|---|---|---|
| unconditional | `b 0x02145218` (packs 1–4) | always available |
| story/event flag | `ldr r0,=0x4E40; blx 0x0201B36C; cmp r0,#0` | flag IDs 0x4E40, 0x4E41, … sequential |
| progress counter | `mov r0,#1; blx 0x0202F6EC; cmp r0,#0x32` | ≥ 50, another arm ≥ 100 |
| duelist wins | `ldr r0,=<list>; mov r1,#7; mov r2,#3; bl 0x02144F08` | beat each of N duelists ≥ 3 times |

`0x02144F08` is `all_of(u32 *ids, int n, int min_wins)` over the per-duelist byte
array at `master[0x0212406C + id*4 + 0x2EC]`.

⚠️ **Corrected 2026-08-03:** that third argument was first written up here as a
"rank". It is a **win count** — user-reported in-game ("defeat some duelists a
certain number of times") and confirmed by measurement: the bytes read out as
`0x3A=0, 0x31=1, 0x30=2, 0x66=10` in `rom_all_patches.ml2`. A rank does not reach
10. Each duelist has a 4-byte record; **three** counters live in it
(`+0x2EC/+0x2ED/+0x2EE`), presumably per mode — `0x02144F08` only tests `+0x2EC`,
while `0x02144FA0` returns true if *any* of the three is non-zero. A parallel
duelist array exists at `master + id*4 + 0x75C..0x75E` (helper `0x02144FD0`).

Set-bit tails (both just `OR (1 << i%32)` into `bits[i/32]`):
- EU `0x02145218` — plain, used by the unconditional arms
- EU `0x02145BC0` → `0x02145D80` — same store **plus** `blx` a notifier with
  `r0 = r7 + 0x7F` ("new pack unlocked!"), used by the conditional arms

**Consequence:** there is no "pack unlocked" field in the `.sav` to edit. The
save holds the *inputs* (event flags, counters, per-duelist ranks); the mask is
re-derived on every shop entry. That is also why the AR code has to be a
per-frame write — it is overwriting a value the game recomputes.

Master game-state block: US `0x02124150` / **EU `0x0212406C`** (ARM9 BSS,
survives overlay swaps). `+0x28` = Duel Points, `+0x2EC + id*4` = per-duelist
rank byte, `+0x2000 + packid*4 + 0x260..0x263` = per-pack records written by
ov10 loop A. Note the ARM9-side shift US→EU is **0xB0/0xE4**, *not* the 0xE0 that
applies to ov1/ov10 — read ARM9 addresses from the EU image, never extrapolate.

### Full unlock-condition map (all 60 packs)

Jump-table slot for pack ID *n* is at **`0x02145124 + n*4`**. Pack numbering is
**1:1 with the in-game pack number** — confirmed by pack 25 matching the user's
report ("defeat some duelists a number of times") against its decoded arm.

Labels for IDs 39, 47–55 and 60 were supplied by the user from in-game
observation and then **confirmed against the disassembly** (each is noted below
with the instruction that implements it).

⚠️ **An earlier version of this table was wrong** — the arm walker ran past each
arm's end into the next one, so packs 32–34 were reported as duelist checks
(they are ALWAYS), several "×1" thresholds were really ×3 (a `mov r2, r1` the
walker didn't propagate), and every TAG clause was missed. An arm ends at its
**first unconditional `B`**; truncate there. Regenerate with
`scratchpad/clauses.py` logic, not a fixed-size window.

Conditions are **AND**-chained: a pack may carry several clauses.

| ID | condition |
|---|---|
| 1–4, 32, 33, 34 | always unlocked (32–34 via trampoline `0x021454D4` → `b 0x02145218`) |
| 5,7,9,11,13,15,17,19,21,22,23,24,26,27,29 | story flag `0x4E40`–`0x4E4E` (sequential) |
| 43,44,45,57,58,59 | story flag `0x4E4F`–`0x4E54` |
| 41 | story flag `0x4E55` |
| 56 | story flag `0x27E0` |
| 6 / 10 / 14 | duels won ≥ 50 / 100 / 200 |
| 39 | beat **every** story duelist (solo) AND every duelist (tag) |
| 47–55 | count of unlocked CPU duelists in a mode ≥ threshold (see below) |
| 60 | own ≥ 95 % of all cards |

Duelist-gated packs — solo list is one u32 duelist id per entry; **tag list is one
u32 per entry holding a PAIR of u16 ids**:

Regenerate with `scratchpad/packnames.py` (kept in the session scratchpad).
Pack 8 verified against user-supplied in-game ground truth, exact and in order.

| ID | requirement (all ×3 wins) |
|---|---|
| 8  | Bronson, Minegishi, Jemma, Virgil, Seluga, Clint, Scotch |
| 12 | Reimi, Lilie, Hayakawa, Masaki, Gordon, Kuroe |
| 16 | Rossi, Kazuhiro, Honda, Yagiura, Helio, Angie, Nelson, Figaro, Corse |
| 18 | Randsborg, Hunter Pace, Lenny, Larry, Lug |
| 20 | Lazar, Sherry LeBlanc, Elsworth |
| 25 | Torunka, Regulus |
| 28 | Nico, West, Kalin Kessler, Sergio, Barbara |
| 30 | Yusei Fudo ×2, Jack Atlas ×2, Crow Hogan ×2 · tag: (Jack+Yusei) ×2 |
| 31 | Harald, Dragan, Brave · tag: Harald+Dragan |
| 35 | Carly Carmine, Mina Simington, Stephanie · tag: Carly+Stephanie |
| 36 | Hermann, Nicolas, Hans · tag: Nicolas+Hermann |
| 37 | Tetsu Trudge, Akiza Izinski ×2, Luna, Leo · tag: Akiza+Trudge, Leo+Luna · story flag `0x27E0` |
| 38 | Facility Chief, Syd, Lawton, Ramon, Malcolm |
| 40 | Narumi, Salida Noula, Grammy, Alina Noula, Iranami, Globe, Lagoon Noula, Oscar, Kalisse Noula |
| 42 | Klaus, Toru ×2, Misaki ×2 · tag: (Toru+Misaki) ×2 |
| 46 | the **first 6 CPU-duel opponents**: Moja, Cherry Inmato, Hypnocorn, Naturia Cherries, Wattmole, Tiki Soul (ids 0x71–0x76) |

**ids ≥ 0x71 are the CPU-duel roster, named after monsters** (user-supplied,
in-game). This closes packs 47/48 too: they count set bits over ids 0x71–0xAC —
exactly 60 CPU-duel opponents — so "36 / 48 CPU duelists unlocked". Packs 49–51
(ids 0x00–0x13) and 54/55 (0x14–0x1D) count over the story roster; 52/53 count
over ids 0xD5–0xE8, a third roster.

The CPU-duel name table is **not** found yet. Ruled out this session: it is not
the `0x020AA7D4` array (that ends at 0x70 — values past it exceed
`game_indx_e.bin`'s 8137 entries and are unrelated adjacent data), and it is not
an array of card *text* indices (searched arm9 + all 50 overlays + `bin.pac` /
`bin2.pac` / `cpuduel.pac` for the u16/u32 sequence `6902, 7644, 7882, 8110,
8420, 8516` = the six names' `card_indx_e` indices — zero hits). Next thing to
try: the same search using engine **cids** rather than text indices — note
**card text index ≠ cid** (verified: `card_indx_e[0x1CE6]` = "Garlandolf", not
Deep Diver), so the cids must come via `card_intid.bin` / the konami-id TSV
first.

Duplicate names (Yusei ×2 in pack 30, Toru ×2 in 42, Akiza ×2 in 37) are distinct
duelist ids sharing a name — the same character as separate story/WRGP opponents.

Helpers (all take `(u32 *ids, int n, int min_wins)`):

| fn | array | note |
|---|---|---|
| `0x02144F08` | `master + id*4 + 0x2EC` | solo win count |
| `0x02144F4C` | `master + f(pair)*4 + 0x75C` | tag; maps the u16 pair via `blx 0x02017784` |
| `0x02144FA0` | `+0x2EC/+0x2ED/+0x2EE` | true if **any** of the three ≠ 0 (beaten once, solo) |
| `0x02144FD0` | `+0x75C/+0x75D/+0x75E` | same for tag |

### Duelist id → name (SOLVED)

Two hops, **not** a direct index:

```
duelist id --u16--> game-text index --u32 offset--> ASCII string
            ^ arm9 0x020AA7D4         ^ bin2/game_indx_e.bin -> bin2/game_text_e.bin
```

`name(id) = game_text[ u16 @ (0x020AA7D4 + id*2) ]`.

Roster is **ids 0x00–0x70** (113). The table's u16s go out of range (> 8137) from
0x71 on, and pack 39's loop bound is `cmp r4,#0x71` — both say the roster ends at
0x70. ids 0x00 and 0x01 both read **"You"** (the player), which is exactly why
pack 39 skips `{0, 1}`. ids ≥ 0x71 belong to a *separate* roster (Turbo Duel /
WRGP, used by packs 46–48 and 52–53) whose names live in a different table —
**not yet mapped**.

⚠️ **Two earlier attempts at this mapping were wrong** and must not be reused:
a direct `1401 + id` and a direct `4801 + id` into `game_text`. Both are real
character-name blocks and they align with each other for ids 0x06–0x62, which is
what made the false mapping look convincing — but neither is keyed by duelist id.
The give-away was user-supplied ground truth for pack 8 (Bronson, Minegishi,
Jemma, Virgil, Seluga, Clint, Scotch) not matching. **Verify a name mapping
against a known-good in-game list before trusting it**; a plausible-looking
roster is not evidence.

**Counter index 1 = duels won.** `counter_get` (`0x0202F6EC`) case 1 computes
`u16[0x021242EC+0x24] − u16[+0x2C] − u16[+0x2E] − u16[+0x30]`; indices 2/3/4
return those three subtrahends. Measured in `rom_all_patches.ml2`:
`183 − 12 − 31 − 0 = 140`. So packs 6 and 10 unlocked, pack 14 (needs 200) not.

**ID 39** — arm `0x021455A0`. Loops duelist id 0..0x70 skipping `{0, 1, 0x48,
0x6F}`, requiring `0x02144FA0(id)` (any of the three `+0x2EC` counters non-zero)
for **every** one; then a second clause over the `+0x75C` array from id 0x1E via
`0x02144FD0`. = "beat every story duelist at least once".

**IDs 47–55** — each counts set bits in a duelist-unlocked bitfield and compares
to a threshold. Three different bitfields / id ranges = the different duel modes:

| ID | arm | bitfield | duelist ids | needs | threshold instruction |
|---|---|---|---|---|---|
| 47 | `0x021456D0` | `master+0x2818` | 0x71..0xAC (60) | 36 | `cmp r0,#0x24` @ `0x02145714` |
| 48 | `0x02145748` | `master+0x2818` | 0x71..0xAC (60) | 48 | `cmp r0,#0x30` @ `0x0214578C` |
| 49 | `0x02145798` | `master+0x2848` | 0x00..0x13 (20) | 7  | `cmp r0,#0x07` @ `0x021457DC` |
| 50 | `0x021457E8` | `master+0x2848` | 0x00..0x13 (20) | 12 | `cmp r0,#0x0C` @ `0x0214582C` |
| 51 | `0x02145838` | `master+0x2848` | 0x00..0x13 (20) | 16 | `cmp r0,#0x10` @ `0x0214587C` |
| 52 | `0x02145888` | `master+0x2818` | 0xD5..0xE8 (20) | 12 | `cmp r0,#0x0C` @ `0x021458CC` |
| 53 | `0x021458D8` | `master+0x2818` | 0xD5..0xE8 (20) | 16 | `cmp r0,#0x10` @ `0x0214591C` |
| 54 | `0x02145928` | `master+0x2848` | 0x14..0x1D (10) | 8  | `cmp r0,#0x08` @ `0x0214596C` |
| 55 | `0x02145978` | `master+0x2848` | 0x14..0x1D (10) | 9  | `cmp r0,#0x09` @ `0x021459BC` |

Note 47–55 inline their own set-bit tail (branching to `0x02145D88`) instead of
using the shared `0x02145BC0`.

**ID 60** — arm `0x02145BE4`. Requires the incoming `r1` arg == 0, then walks all
`0x10D2` (4306) card slots, skipping ~13 excluded ids, counting owned (`blx
0x0202B058`) vs eligible, then `pct = owned*100/eligible` and
**`cmp r0, #0x5f`** (95) at **`0x02145D58`**. = "own ≥ 95% of all cards".

## Ruled Out (continued)

- *"Set a third bitfield word `0001FFFF` for packs 65–81"* (proposed earlier this
  session) — **wrong, drop it.** `unlock_mask` only ever writes bits 0..59
  (loop bound `0x3c`) and the shop-list loop only reads 0..59. Bits 60..80 are
  never set by the stock game and setting them cannot add shop entries; they
  would only feed ov10 loop A's master-record sync. Pack IDs 61–81 exist in
  `card_pack.bin` but are not shop-purchasable.

## Shipped: editable condition table

`otn_enhanced/system/pack_unlock_conditions.py` — reads all 60 arms
into `{pack_id: Condition}`, applies a modified dict back to the ROM. Follows the
`patch_bulk_ydcs.py` house pattern: a module-level **`CHANGES`** dict with every
pack listed (commented out, showing its stock rule and the duelist names), a
`validate()` on each condition type, and `main(src, out)`.

```
python -m ...pack_unlock_conditions              # apply CHANGES
python -m ...pack_unlock_conditions show         # print the stock table
python -m ...pack_unlock_conditions dump  p.json # or edit as JSON, then
python -m ...pack_unlock_conditions apply p.json
```

`Condition` is intentionally *not* a dataclass: keeping `sites` (patch-site
bookkeeping) out of the field list is what lets subclasses take positional args
(`StoryFlag(0x4E40)`) and keeps it out of `__eq__`, so an untouched round-trip
compares equal and writes nothing.

Edits are **size-neutral only** (arms are packed back-to-back): `Always`/`Never`/
`SameAs` rewrite the jump-table slot; thresholds (`DuelsWon.wins`,
`CountUnlocked.need`, `CardPercent.percent`, `BeatDuelists.wins`) rewrite an
immediate; `StoryFlag.flag_id` rewrites the literal-pool word; `BeatDuelists.ids`
rewrites the id array in place at **same length or shorter** and updates
`mov r1,#n`. A structural swap (e.g. story-flag → duels-won) is refused.

Guards that fire (all tested): shared arm (packs 1–4, 32–34), shared duelist
list, list longer than its array, non-encodable ARM immediate, compound clause
list resized. Unchanged packs are skipped, so a full round-trip writes nothing.

⚠️ Two parser traps found while building it, both **silent**:
1. `arm_body` needs a window ≥ ~0x1A4 bytes — pack 60's arm is that long, and a
   short window truncated it before its threshold `cmp`, reading as `percent=0`.
2. An arm ends at its first unconditional `B` **or** on reaching a shared tail
   (`SET_TAIL`/`SET_TAIL2`/`LOOP_TAIL`). Pack 60 has no terminating `B` — it
   falls through into `SET_TAIL2` — so a bounds-only fix ran past into another
   function and read as a story flag. Both bounds are required.

## Shipped

`otn_enhanced/system/unlock_all_packs.py` — one instruction in
overlay 1:

```
EU 0x0214511C:  00 F1 8F 90  (addls pc, pc, r0, lsl #2)
             -> 3D 00 00 EA  (b 0x02145218)
```

Every pack ID 1..60 now takes the unconditional set-bit arm. Retargeting to
`0x02145218` rather than the conditional tail `0x02145BC0` is deliberate — the
latter also fires the "new pack unlocked" notifier, which would trigger 60× per
shop entry.

Built + verified: `data/over_the_nexus/working/rom_all_packs.nds`; diff vs
`rom.nds` is **4 bytes in ov1**, with ov0/ov3/ov5/ov10 and arm9 byte-identical.
Module is idempotent and guards on four byte signatures around the site.

**Not yet confirmed in-game** — that is the remaining step: load
`rom_all_packs.nds` in melonDS, open the card shop, and check all 60 packs list
and are purchasable.

## Next Experiment

In-game check of `rom_all_packs.nds` (above). If the list is right but purchases
misbehave, the suspect is ov10 `+0x10A4` (pack count) vs the entry array built by
loop B — both derive from the same mask, so they should stay consistent, but the
price field at `+0x10A8` and the DP debit at EU `0x02155750` are the things to
watch.

## Ruled Out

- *"The AR addresses are overlay code / a data table"* — no overlay image holds
  `0x02158DE4` at `0x02159ED0`; they are BSS.
- *"`+0xAC`/`+0xB0` in the `0x02152D90` function is the bitfield"* — that is a
  BG-scroll routine writing `0x04000018`/`0x0400001C` (BG2/BG3 offset regs) on an
  unrelated struct. False positive from offset-only matching.
- *"`0x02158DE4` is a struct base the object hangs off"* — it is a static
  destructor-list node (see above).
