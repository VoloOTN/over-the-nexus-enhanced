# Ceruli, Guru of Dark World — findings (session 2026-08-30)

Printed text (`scratch/ygoprodeck_cache.json`) — DARK / Fiend / Level 1 / 100 / 300:

> If this card is discarded to the Graveyard by a card effect: Special Summon
> this card from the Graveyard to your opponent's side of the field in face-up
> Defense Position. When this card is Special Summoned by the effect of a
> "Dark World" card: Your opponent must discard 1 card.

Clauses:

1. **C1 — discard trigger.** Discarded to the GY by a card effect → Special
   Summon it from the GY **to the opponent's side of the field**, **face-up
   Defense Position**. Mandatory, not once per turn.
2. **C2 — on-SS trigger.** Special Summoned by the effect of a *"Dark World"*
   card → the opponent discards 1 card. **NOT IN SCOPE this session.**

**SCOPE: clause 1 only.** Donor **Kahkki, Guerilla of Dark World `0x1B3E`**,
chosen by the user 2026-08-30. Kahkki's own printed effect is replaced.

**STATUS: CLAUSE 1 ✅ IN-GAME CONFIRMED BY THE USER 2026-08-30**
("Excellent! Clause 1 works as intended.") on round 2,
sha256 `abca300ef9375bd81824754e6287afbdd5b71adb4df77633ff09d57001dce074`.
Still NOT in `apply_all_patches` — no ship approval yet.
**CLAUSE 2: IN-GAME CONFIRMED BY THE USER 2026-08-30** ("Perfect! Ship it!")
on round 2. **BOTH CLAUSES SHIPPED into `apply_all_patches` the same day.**
ROM `data/over_the_nexus/working/rom_ceruli.nds`,
sha256 `b2762b47066f22407b24566339e52283c15807f376d88d2df1d198ce98a11041`
(round 1 was `f4670487...b900666` — worked, but mis-ordered).

### CLAUSE 2 ROUND 1 IN-GAME RESULT (user, 2026-08-30) — ordering only

> currently the discard prompt appears before ceruli is special summoned.
> but the discard and the summon occur simultaneously.

Preceded by: *"can the discard effect occur after the summon takes place.
Otherwise the effect is good to ship and behaves as intended"* — so both clauses
resolve correctly; only the presentation order was wrong.

**Cause:** the commit and the discard were posted in the **same resolution
phase**. Placing a card is not the same event as presenting it, and two posts in
one phase are shown together.

**Fix — the engine's own idiom, with an exact precedent.** Sillva `0x1968` is on
the *same cls2 table* and the *same discard trigger*, and prints the same two-beat
shape ("Special Summon it from the Graveyard, THEN ... your opponent returns 2
cards"). Its resolver `0x0221FA5C`:

```
0221FA5E  ldr r6,=0x0229AAFC
0221FA62  ldr r2,[r6,#0x70]      ; THE PHASE
0221FA66  subs r2,#0x7a ; cmp r2,#6 ; bhi default
0221FA6C  ... PC-relative halfword jump table, phases 0x7A..0x80
   phase 0x80 -> 0x0221FA84: bl 0x0220731C (the summon), then movs r0,#0x7F
   phase 0x7F -> 0x0221FAD0: the "return 2 cards" post
```
Ceruli now does the same: **phase 1 summons and returns 0x7F; the re-entry posts
the discard.**

This also closes `resolver.phase_protocol`'s scope limit for this dispatch — the
limit was that `+0x70` is not known to hold the phase for *every* resolver (a
cls3 activation read 1 on every entry), and Sillva is a positive instance in the
same table and trigger family.

⚠️ The gate is `phase == 0x7F` with **clause 1 as the fall-through**, deliberately
not `== 0x80` with clause 2 falling through: if the entry phase is ever not 0x80,
this way costs only the ordering, whereas the other way would silently lose the
summon — the exact failure mode `card.maiden_clause1` already paid for.

No chain-depth bracket: Sillva and Delinquent Duo push because their effects span
further phases; a terminal post does not need one.

## CLAUSE 2 — inlined as a follow-on, not a second trigger

> When this card is Special Summoned by the effect of a "Dark World" card:
> Your opponent must discard 1 card.

The **native** route would be a cls1 record plus membership of the code-9
"when Special Summoned" list `0x0228F63A` — `summon.trigger_is_a_membership_list`
hard-codes the selector to 1, so a summon trigger can only ever reach **cls1**
(a different table from clause 1's cls2 record, so there would have been no
shadowing). Affordable: the list has 5 phantoms, cls1 has 161.

**The user proposed inlining it into clause 1's resolver instead**, which costs
neither insert and makes the "by the effect of a Dark World card" condition free
— the code is reachable only from clause 1's own summon, so it cannot fire on a
Monster Reborn revival. It replaced the latch design entirely.

### That shape is legal — measured, not assumed
`0x022598A0` (the effect-discard post) has **26 BL callers** in ov3 and **nine**
post it and return 0 in the same phase, with no `[0x0229AAFC+0x70]` phase
protocol and no chain-depth bracket: `0x0220E0CC`, `0x0220EC4A`, `0x0221AC74`,
`0x0221AC86`, `0x0221FA50`, `0x0221FCDE`, `0x0222914E`, `0x0222DBB2`,
`0x0222EB38`. Delinquent Duo `0x1325` is the misleading example — its three
phases exist because it makes *two* posts in sequence, not because one needs
them.

Three natives even build the identical argument tuple
(`0x0222EB2E`, `0x0223192C`, `0x02211C66`):
```
ldrb r0,[r4,#2] ; movs r1,#1 ; movs r2,#0 ; subs r0,r1,r0 ; movs r3,#1
bl 0x022598A0                       ; (1 - desc[+2], 1, 0, 1)
```

### The target is desc[+2] — the OWNER
The user stated the ruling before any code was read: *"the person who discards
ceruli is the one that has to discard"*. Konami agrees, reaching the same player
the long way round — the 3DS clause-2 handler `0x00444624` runs off the **summon**
descriptor, whose `[+2]` is the **placing** side (`= 1 - owner`), and discards
`1 - that` `= the owner`. Inside clause 1 the owner is already in hand, so no
inversion is needed.

kind 0 = the **effect** discard, so a Dark World monster discarded by Ceruli
still triggers.

### Accepted deviations
* Fires when a **non**-Dark-World card (Card Destruction, Morphing Jar) did the
  discarding — chosen by the user over a full set-code test on the effect source,
  which would have needed unproven RE.
* ⚠️ When the **opponent's** effect discards your Ceruli, owner and discarder are
  different players and Konami targets the **owner**. Not checked against the
  paper ruling.
* Description reworded to cover both clauses (105 B of 106); "Graveyard" is now
  abbreviated "GY", which the clause-1-only wording did not need.

## ROUND 1 IN-GAME RESULT (user, 2026-08-30) — FAILED on the side

> 1. Discarding Ceruli, special summons ceruli on my side of the field see .ml3
> 2. Nothing Happens
> 3. Cannot verify
> 4. No Regressions

Follow-up confirmed by the user: Ceruli arrived **face-up in Defense Position**,
on the wrong side; the summon happened.

So 2 (cost-discard negative control), and 4 (Gren / Beiige / Snoww) PASSED.
3 was not reachable. Only the **side** was wrong.

### THE SAVESTATE SETTLED IT IN ONE READ
`rom_ceruli.ml3` (RAM0 @file 0x24), summon block `0x02298A28`:

```
[+0x00] attribution side = 1     <- the bit-4 flip DID apply
[+0x02] placing side     = 0
[+0x06] face-up          = 1     [+0x08] position = 1 (DEF)
[+0x0A] zone             = 0x0E  [+0x0E] cid = 0x1B3E
[+0x10] word low         = 0x14  == (0x10 | 4), so the 5th argument arrived intact
```
and Ceruli was physically in **side 0's monster zone 2** (`0x0C801B3E`, side
bit = 0), while side 1's zones were empty. Player side 0 = LP 8000 = the user.

**=> `[g+0]` is NOT what places the card. `r0` / `[g+2]` is.** Bit 4 only writes
a separate attribution field that nothing in the placement path reads. This
**falsifies** the round-1 design and the fact it was built on.

Corroboration that was available before the test and should have outranked the
inference: **Ojama Trio** — the one stock card that Special Summons to the
opponent's field — passes `1 - side` in **r0** and leaves the low half **zero**
(`0x02207BAA: movs r0,#1 ; subs r0,r0,r4`). It never touches bit 4.

And re-read with the corrected semantics, **the 3DS agrees**: Ceruli's own
handler passes `r0 = 1 - owner` **and** sets bit 4 — it PLACES on the opponent
while RECORDING `[g+0]` = the owner. Both halves are deliberate.

### ROUND 2 — one instruction
`ldrb r0,[r5,#2]` → `adds r0,r6,#0` in the commit block (r6 = `1 - desc[+2]`
was already computed for gate 3). Bit 4 stays set. Nothing else changed.

* single-card ROM: `data/over_the_nexus/working/rom_ceruli.nds`,
  sha256 `abca300ef9375bd81824754e6287afbdd5b71adb4df77633ff09d57001dce074`
  (round 1 was `fc0c4224…07cb33e6` — the one that landed on the owner's side)
* build: `.venv-1/Scripts/python.exe _build_ceruli.py --text`
* module: `otn_enhanced/cards/ceruli.py`
* NOT wired into `apply_all_patches` (no ship approval yet).

## What was built

**Two edits, no overlay-3 code.**

1. **cls2[239] @`0x0227726C`** (Kahkki's own record) rewritten IN PLACE:
   `{+04 0x0239D841, +08 0, +0C 0, +10 0, +14 0}` -- the Sangan/Beiige
   MANDATORY shape, byte-for-byte the shape of Ceruli's own 3DS row.
   No record inserted => count-neutral by construction, no phantom drop.
2. **`CAVE_CERULI_RES` @`0x0239D840`**, 124 B of a 0x80 reservation
   (`CAVE_FREE` bumped 0x0239D840 -> 0x0239D8C0). The engine's own
   self-SS-from-GY tail with the three 3DS deltas: face-up, DEFENSE, and bit 4
   of the commit's fifth argument.
3. `card_prop[2229]` Lv2/300/500 -> **Lv1/100/300** (DARK / Fiend / Effect
   already correct), plus name + description.

### Deviations from the printed card
* **Description** is a 103 B paraphrase, not the 170 B printed text -- the
  donor's English blob is 106 B and no donatable blob exists.
* **Japanese name** stays Kahkki's (20 B slot, 2 B padding, nothing to relocate
  into). Every other language took both strings.
* **Clause 2 is not implemented.**

## KB contributions (353 facts, 318 PASS / 0 FAIL / 35 UNVERIFIED)
* `summon.commit_r0_places_bit4_only_attributes` -- VERIFIED (the round-1 correction)
* `summon.commit_bit4_flips_destination_side` -- **demoted to UNVERIFIED**,
  `corrected_by` the above; kept so the next session inherits the correction
* `event.discard_desc_side_is_owner` -- VERIFIED
* `tool.threeds_discard_registry_maps_to_cls2` -- VERIFIED
* `card.ceruli_clause1` -- VERIFIED (the *build* is proven; the CARD is
  explicitly marked AWAITING IN-GAME TEST in its claim text)

---

## Confirmed (this session)

### KB baseline on arrival
`verify_knowledge` = **346 facts, 313 PASS / 0 FAIL / 33 UNVERIFIED**
(oracles arm9=yes ov3=yes ov5=yes savestate=rom_all_patches.ml2).

### The donor already owns the trigger
Kahkki `0x1B3E` is one of the **seven** cids the hardcoded Dark World
effect-discard arm `0x021D185C` accepts (`event.dark_world_discard_arm`:
phantom `0x0EC9`, Beiige `0x1965`, Broww `0x1966`, Sillva `0x1968`,
Goldd `0x1969`, Kahkki `0x1B3E`, Gren `0x1B3F`). So clause 1's trigger — "if
this card is discarded to the Graveyard by a card effect" — is **native to the
donor cid** and needs **no ov3 hook at all**, unlike Snoww and Grapha which each
had to buy it with a terminal-node / BL hook.

Kahkki is also already in the ARM9 Dark World set-code table at `0x0209CA1C`
(set code 0x0F, thunk `0x020238B5`), so Ceruli stays a "Dark World" card with no
edit to that list.

### The 3DS ships Ceruli: cid `0x25F2` (adjacent to Snoww 0x25F1, Grapha 0x25F0)
`.venv-1/Scripts/python.exe -m otn_enhanced.tools.threeds_lookup "Ceruli"`

```
discard/event_trigger 0x6C6780 (stride 0x18, 815 rows)
[ 773] 000025F2 00443184 00000000 00000000 00000000 00000000   Ceruli
[ 242] 00001B3E 00458888 003DBCA8 00404260 00000000 00477BB8   Kahkki
on_trigger 0x6C335C
[ 228] 000025F2 00444624 00000000 00404260 00000000 00000000   Ceruli  <- CLAUSE 2
```

Ceruli owns **no** NDS criteria row (the cid is absent from the NDS build).

### The 3DS `discard/event_trigger` registry maps 1:1 onto the NDS cls2 record
Two independent shared-handler pairs survive the port, which pins the mapping:

| card | 3DS resolver | NDS cls2 +04 |
|---|---|---|
| Beiige `0x1965` / Reign-Beaux `0x1B3D` | both `0x0045E090` | both `0x0220731D` |
| Kahkki `0x1B3E` / Gren `0x1B3F` | both `0x00458888` | both `0x02204899` |

Also `3DS +0C 0x00404260` ↔ `NDS +0C 0x0224A115` (Goldd, Kahkki, Gren) and
`3DS +14 0x00477BB8` ↔ `NDS +14 0x02234DA5` (Kahkki, Gren).

Full NDS cls2 rows for the Dark World discard family (stock):

```
cls2[189] 0x1965 Beiige      +04 0220731D  rest 0
cls2[190] 0x1966 Broww       +04 022065B9  rest 0
cls2[191] 0x1968 Sillva      +04 0221FA5D  rest 0
cls2[192] 0x1969 Goldd       +04 0221FB51 +08 021DE7C9 +0C 0224A115 +14 0223847D
cls2[193] 0x196A Scarr       +04 02207EF5  rest 0
cls2[238] 0x1B3D Reign-Beaux +04 0220731D  rest 0
cls2[239] 0x1B3E Kahkki      +04 02204899 +08 021D8CE5 +0C 0224A115 +14 02234DA5
cls2[240] 0x1B3F Gren        +04 02204899 +08 021DB3BD +0C 0224A115 +14 02234DA5
```

Ceruli's 3DS row is the bare `{resolver, 0,0,0,0}` shape = the Sangan/Beiige
**MANDATORY** shape (`event.optional_trigger_is_record_shape`), consistent with
its printed text carrying no "You can".

### ⭐ THE SS COMMIT PRIMITIVE ALREADY IMPLEMENTS "SUMMON TO THE OPPONENT'S SIDE"
`0x0226925C(r0 = acting side, r1 = &locator, r2 = face-up, r3 = position,
[sp] = word)` — **bit 4 (`0x10`) of the 5th argument flips the DESTINATION
side**:

```
0226927A  ldr  r1,[sp,#0x18]     ; the 5th arg  (push{r3-r7,lr} = 0x18)
0226927C  movs r0,#0x10
0226927E  tst  r0,r1             ; BIT 4
02269280  beq  0x02269286
02269282  movs r0,#1
02269286  movs r0,#0
02269288  ldr  r4,[pc,#0x84]
0226928A  eors r0,r5             ; r0 = acting_side ^ bit4
0226928C  strh r0,[r4]           ; [g+0] = DESTINATION side
0226928E  strh r5,[r4,#2]        ; [g+2] = ACTING side
```

The 3DS's own commit `0x003CFDA0` does the identical thing:
```
003CFDF0  and r1, r4, #0x10
003CFDF8  eor r2, r7, r1, lsr #4
003CFE04  strh r2,[sl]           ; destination
003CFE0C  strh r7,[sl,#2]        ; acting
```
No NDS card sets bit 4, but the engine's own **Ojama Trio** proves the placement
half works through this exact primitive (`dispatch.token_table`: its per-cid leaf
`0x02207BAA` does `movs r0,#1 / subs r0,r0,r4` and summons tokens to the
opponent's field via `0x0226925C`).

### 3DS Ceruli's resolver `0x00443184`, decoded
```
r5 = desc[+2] ^ desc[+0xA]
r0 = desc[+0x16] ; bl 0x3CD1A4      == NDS 0x021A220C
cmp desc[+4], r0>>8 ; bne exit                      ; still in the recorded zone
r0 = 1-r5 ; bl 0x3B4588 ; if 0 exit                 ; UNMAPPED
r0 = r5   ; bl 0x391B34 ; if 0 exit                 ; UNMAPPED
[sp]=1 ; r0=r5 ; r1=1-r5 ; r2=ref ; r3=desc[+4]
        bl 0x3B9928 ; if 0 exit    ; TWO-SIDED free-zone check (no NDS twin)
r6 = 2 ; if cid==0x2040 (Worm Ugly) r6=0 ; if cid==0x25F2 (Ceruli) r6=1  ; DEF
[sp] = 0x10 | (cid<<16)
r0 = 1-r5 ; r1 = ref ; r2 = 1 ; r3 = r6 ; bl 0x3CFDA0   ; == NDS 0x0226925C
```
i.e. **face-up (r2=1), Defense (r3=1), destination = the opponent (bit 4)**.

### Primitive equivalence map established this session (3DS → NDS)
Read off 3DS Beiige `0x0045E090` against NDS `0x0220731C` position-for-position:

| 3DS | NDS | role |
|---|---|---|
| `0x003CD1A4` | `0x021A220C` | packed word → zone (`>>8`) |
| `0x003A2EAC` | `0x021A25E8` | ref → `&locator` |
| `0x003BF19C` | `0x021A2618` | proper-summon check on the locator |
| `0x00392BBC` | `0x021B9EC0` | (side, r4) pre-gate |
| `0x00391CD4` | `0x021BA440` | free-zone check, face-up path (takes the descriptor) |
| `0x00392090` | `0x021BA258` | free-zone check (side, cid, ref, zone) |
| `0x003CFDA0` | `0x0226925C` | **the Special Summon commit** |

### `desc[+2]` on the discard path is the OWNER, not the actor
`0x021D3168` builds the descriptor from the event word:
```
021D3182  lsls r2,#0x1e          ; r2 = 0x80000000
021D3186  ands r0,r2
021D318E  lsrs r0,#0x1f
021D3190  strb r0,[r4,#2]        ; desc[+2] = event bit 31
```
and `event.discard_trigger_posts_the_same_0x4E` has `0x021D1D56` building that
bit from `r7 = (w>>9)&1` = **the owner**. So `1 - desc[+2]` is genuinely "the
owner's opponent", which is what the card says.

Same routine: `desc[+3] = (event>>16)&0x1F = KIND`, and the discard arm forces
`KIND = 0x0E`. **`0x0E` is the Graveyard** (corroborated by
`0x021BA258`'s own `cmp r6,#0xE` branch and by patch_armory_arm's
"must still be in GY" gate `cmp r0,#0xE` @`0x02204E5A`). So the native gate
`desc[+3] == zone_of(desc[+0xC])` reads exactly "still in the Graveyard".

### The free-zone check takes the side as a plain parameter
`0x021BA440` is a thin wrapper:
```
021BA444  ldrb r0,[r4,#2] ; ldrh r1,[r4] ; ldrb r2,[r4,#3] ; bl 0x021B9FC0
021BA456  ldrb r0,[r4,#2] ; ldrh r1,[r4] ; ldrh r2,[r4,#0xC] ; ldrb r3,[r4,#3]
          bl 0x021BA258
```
and inside `0x021B9FC0` the side arrives as `r6 = r0` and is used as a side index
(`0x021BA03C  ands r2,r1` with `r2 = r6 & 1`). So **inlining the wrapper with
`1 - desc[+2]` evaluates the OPPONENT's field** — which is what the 3DS spends
its own two-sided `0x003B9928` on.

### Donor safety sweep for `0x1B3E`
Aligned-u16 sweep of the **whole** of overlay 3 and ARM9 → exactly **two** real
references:

* `0x0227726C` — Kahkki's cls2 record (= `0x02275C04 + 239*24`). **Ours.**
* `0x0209CA1C` — the Dark World set-code table. **Kept.**

`0x0214FF58` is a **false positive**: it is the low halfword of the ARM-mode
instruction `E2811B3E = ADD R1,R1,#0xF800`, not a cid.

No criteria-registry row, no summon-procedure row, no cls0/cls1/cls3 record, no
battle-attribute list membership. The discard-arm leaf is ungreppable by design
(`thumb-stack-based-switch-footgun`) and is the trigger we are keeping.

### Donor blob lengths (measured)
`card_prop[2229]` @ pac `0x9677B0` = Lv2 / DARK / Fiend / 300 / 500 /
Effect Monster.

| lang | name | fits 26 B | desc | fits 170 B | name pad | desc pad |
|---|---|---|---|---|---|---|
| e | 30 | yes | 106 | **NO** | 4 | 2 |
| f | 35 | yes | 120 | **NO** | 3 | 1 |
| g | 35 | yes | 127 | **NO** | 2 | 3 |
| i | 37 | yes | 107 | **NO** | 2 | 4 |
| s | 36 | yes | 113 | **NO** | 2 | 3 |
| j | 20 | **NO** | 106 | **NO** | 2 | 2 |
| k | 18 | **NO** | 97 | **NO** | 2067 | 2065 |
| r | 46 | yes | 186 | yes | 2 | 4 |

**There is no donatable blob**: all 4305 `card_prop` records hold a real cid
(0 phantom slots), so no unused description string exists to point at. The
description must be shortened. User chose (2026-08-30) the 103 B form:

> Discarded to the Graveyard by a card effect: Special Summon it to your
> opponent's field in face-up DEF.

Japanese keeps the old name/desc (2 B of padding, nothing to relocate into);
Korean relocates fine (2067 B of padding).

---

## Ruled Out

- **A records-free Normal Monster donor.** The whole value of Kahkki is that the
  discard trigger is hardcoded to seven cids in `0x021D1392`'s switch; any other
  donor needs an ov3 code hook to be admitted (Snoww's terminal-node displacement
  or Grapha's `0x021D14E2` BL). The user's choice is the cheap one.
- **Reusing an existing NDS resolver.** No NDS card Special Summons itself from
  the GY to the opponent's field, so `+04` must be a new stub. Pattern B.
- **A count-neutral phantom drop.** Not needed: `cls2[239]` already exists and is
  rewritten in place, so the table's length and sort order are untouched.

## Open Questions

- 3DS Ceruli's two extra gates `0x003B4588` and `0x00391B34` have no NDS
  counterpart mapped. Omitted from the port; NDS Beiige's path is the precedent
  that the remaining sequence suffices. (`0x003B4588` is probably
  `NDS 0x021AD870`, called at the top of `0x0220731C` — unconfirmed.)
- **Does the engine fully model a card OWNED by one player but sitting in the
  other's monster zone?** Does it go to its owner's GY when destroyed? Can the
  new controller attack with it? The commit clearly separates `[g+0]`
  destination from `[g+2]` acting side, and Ojama Trio exercises the placement
  half — but with **tokens**, which have no owner. An owned card on the
  opponent's field is not exercised anywhere in the stock ROM. **This is the
  main in-game risk.**

## Next Experiment

The in-game test itself (see the build report). If clause 1 fires but the card
lands on the wrong side, the single lever is the commit's side argument: swap
`r0 = desc[+2]` + bit 4 for `r0 = 1 - desc[+2]` + no bit 4 (the Ojama Trio
route) — both produce destination `1 - owner`, and differ only in the recorded
acting side `[g+2]`.

---

## SHIPPED (2026-08-30)

Wired into `apply_all_patches` as a single `PatchStep`, immediately after
Grapha. **No ordering constraint** — the position is for readability only:

* it plants **nothing** on the `0x021D1392` discard-switch chain (unlike Snoww
  and Grapha, which both do and therefore need `register_switch_stub`), because
  its donor Kahkki `0x1B3E` is natively one of the seven cids the arm accepts;
* it **reads but never writes** the ARM9 Dark World set-code table `0x0209CA06`
  (its donor is already a member), so it does not interact with Gates' PART E2;
* its cls2 edit is **in place** on its own record — no insert, no phantom drop,
  no re-sort;
* its one ov5 slot `CAVE_CERULI_RES` is unshared.

### The whole card, for the record

| what | where |
|---|---|
| cls2[239] `{+04 CAVE_CERULI_RES\|1, rest 0}` | `0x0227726C` |
| the two-phase resolver, 184 B of 0xC0 | `CAVE_CERULI_RES` `0x0239D840` |
| `card_prop[2229]` Lv1 / 100 / 300 | pac `0x9677B0` |
| name + description | `card_indx/name/desc_*` record 2229 |

Primitives reused, none new: `0x021A220C` (zone of ref), `0x021A25E8`
(ref -> &locator), `0x021A2618` (proper-summon check), `0x021B9FC0` +
`0x021BA258` (free-zone, called with the OPPONENT's side), `0x0226925C` (the SS
commit), `0x022598A0` (the effect-discard post), `0x0229AAFC+0x70` (the phase).

### KB contributions from this card
* `summon.commit_r0_places_bit4_only_attributes` — VERIFIED (corrects the
  round-1 mistake; the old fact is kept UNVERIFIED with `corrected_by`)
* `event.discard_desc_side_is_owner` — VERIFIED
* `tool.threeds_discard_registry_maps_to_cls2` — VERIFIED
* `dispatch.effect_discard_post_is_fire_and_forget` — VERIFIED
* `card.ceruli_clause1` / `card.ceruli_clause2` — VERIFIED, both carrying the
  user's sign-off date

### What this card cost, so the next one does not repeat it
**Two in-game tests, both avoidable.**

1. **Round 1 of clause 1** landed the card on its owner's side. I inferred from
   `0x0226925C`'s prologue that bit 4 "flips the destination side" and shipped on
   it. **Ojama Trio — the one stock card that Special Summons to the opponent's
   field — was visible the whole time and passes `1 - side` in r0 without ever
   touching bit 4.** A written precedent should have outranked a static
   inference about a field the function merely *writes*.
2. **Round 1 of clause 2** posted the discard in the same phase as the summon.
   **Sillva `0x1968` — same cls2 table, same discard trigger, same printed
   "summon, THEN ..." shape — already solved it with the phase protocol.**

Both misses have the same shape: the answer was in a native card on the same
mechanism, and I reasoned from disassembly instead of looking for it. The
donor-selection habit (find the card that already does this) needs to extend to
*every* primitive, not just the donor.

---

## THE CHAIN BUILD (2026-08-30) — one composition bug, caught by the sweep

**FINAL: `rom_all_patches.nds`, 41/41 steps, 129528456 B,
sha256 `cacb064353599460059c36dec96e10ab8a8a1e3330238e2c38fea6bfbca00393`.
`_verify_all_patches.py` = 30 PASS / 0 FAIL / 2 SKIP (the 2 have no `verify()`).**

### Attempt 1 died at step 32/41 — with exit code 0
The log was buffer-truncated and its last line was the step header, so it looked
like a finished build and left a 129 MB **valid-looking ROM missing nine steps,
including the WiFi timers**. Only the sweep exposed it: `patch_ceruli`,
`patch_maiden_eyes_of_blue` and `patch_azure_eyes` all failed together — the
signature of a chain that *stopped*, not of three unrelated regressions.

**Cause: a hardcoded set-code slot address.** `_assert_arm9_setcode` asserted
`setcode[0x0209CA1C] == 0x1B3E`, which is the donor's slot **in the stock image**.
Gates of Dark World's PART E2 inserts Colosseum `0x1C8B` count-neutrally by
dropping phantom `0x0EC9` off the **front** of the table, shifting every later
entry two bytes earlier — so in the combined ROM `0x0209CA1C` holds Gren `0x1B3F`
and the donor sits at index 10, not 11.

**The single-card build could never catch this**: `_build_ceruli.py` starts from
stock `rom.nds`, where the address is correct.

Fixed to check what the patch actually depends on — `cid in table` plus strict
sortedness — with the count read live from the thunk's own `movs r2,#N`
immediate (`0x020238B8`) rather than assumed. Banked as
`setcode.slot_addresses_are_not_stable`.

### Attempt 2 completed, and exposed a second self-inflicted false alarm
`verify()` diffed cls2 **by index** against stock. Other shipped patches make
their own count-neutral inserts, so in the combined ROM the donor is at index
**240** (not 239), Gren at **241**, and 584 cid slots differ — hundreds of phantom
"regressions" against a ROM that was correct. Same shape of mistake as the
hardcoded slot: an *index* asserted where an *identity* was meant.

Now: the strong per-index diff runs only when the cid columns are index-aligned
with stock (the single-card build, where it still fires and still reports
`[239]`); otherwise it falls back to by-cid checks. Gren is looked up separately
in each image. A new check also asserts the donor cid owns exactly **one** cls2
record, which is the `find_event_handler` leftmost-shadow guard.

### The rule both bugs share
An address is not an identity. In every table that is sorted and inserted into
count-neutrally, a cid's **slot moves** whenever any other patch inserts ahead of
it; only its **membership** is stable. And a guard that runs only in the full
chain is not exercised by any single-card `_build_*.py` — so run
`apply_all_patches` when adding a patch that touches shared state, and **assert
the final patch count and ROM hash, because exit code 0 does not mean the chain
finished.**
