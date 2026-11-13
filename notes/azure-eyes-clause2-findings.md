# Azure-Eyes Silver Dragon — CLAUSE 2 findings (session 2026-08-24b)

Scope this session: **clause 2 only** — the on-Special-Summon targeting /
destruction protection. Clauses 3 (Standby revive) and 1 (Normal-Monster
materials) are **shipped and in-game confirmed** and must not regress.

Text re-read from `scratch/ygoprodeck_cache.json` id 40908371 **this session**
(not from the prompt, not from recall):

> 1 Tuner + 1+ non-Tuner Normal Monsters
> If this card is Special Summoned: Until the end of the next turn, neither
> player can target Dragon monsters you currently control with card effects,
> also they cannot be destroyed by card effects. Once per turn, during your
> Standby Phase: You can target 1 Normal Monster in your GY; Special Summon it.

Clause numbering (unchanged): **1** = materials, **2** = on-SS protection,
**3** = Standby-Phase revive.

OTN-era (3DS) printing of the clause being built:

> When this card is Special Summoned: Dragon-Type monsters you currently control
> cannot be targeted or destroyed by card effects until the end of the next turn.

Four sub-problems: (a) the trigger, (b) the "Dragons you currently control"
snapshot, (c) the protection (target **and** destroy, **both** players),
(d) the duration (until the end of the *next* turn).

`verify_knowledge` at session start: **287 facts, 256 PASS, 0 FAIL, 31
UNVERIFIED**. (The handoff prompt's "282 / 251" predates the clause-1 session;
287/256 is what the runner prints and what the clause-1 findings record.)

---

## Confirmed (this session, by disassembly of the clean `rom.nds`)

### `0x0224A115` is NOT "was I just Synchro Summoned" — it is the always-on stub

The handoff named `0x0224A115` as the prime candidate for the trigger, recurring
as `+0C` on three of the five native "when this card is Synchro Summoned" cards.
It is **`0x0224A114 | 1`**, and `0x0224A114` is `movs r0,#2 ; bx lr` — the
ubiquitous **activation-condition slot3 stub** already documented in
`dispatch.cls_slot_roles` ("318 cls1 + 112 cls2 records" share it), meaning
"activatable unconditionally". It says nothing about how the card was summoned.

So the trigger for those five cards is **not in the record at all** — it is in
the EVENT that reaches the record.

### The summon trigger is a DATA table: `0x02265768`, the summon-trigger evaluator

`0x02265768(r0 = event code)` runs after every summon, with `r4 = 0x02298A28`
(the global summon record: `+0x02` side, `+0x04` zone, `+0x0E` cid,
`+0x10` flags, `+0x12` a second cid). Three callers, three codes:

| caller | `movs r0,#N` | meaning |
|---|---|---|
| `0x02267A38` | 7 | Normal Summon |
| `0x02268B7C` | 8 | Flip Summon |
| `0x0226878A` | **9** | **Special Summon** |

The body computes a single flag `r5` and, at `0x02265C70`, posts a **selector-1**
event when it is non-zero:

```
02265C74  ldrh r0,[r4,#4]      ; zone   -> bits 16..20
02265C76  ldrh r2,[r4,#2]      ; side   -> bit 31
02265C88  lsls r6,r6,#0x19     ; event code (r6) -> bits 25..30
02265C8E  movs r6,#2 ; lsls r6,#0x14   ; = 0x00200000 -> SELECTOR 1  (cls1)
02265C90  ldrh r1,[r4,#0xe]    ; cid    -> bits 0..15
02265CA8  bl   0x021D3168      ; the register-prim
```

i.e. exactly `event.packed_word_layout`. **The event always carries selector 1,
so a summon trigger can only ever be dispatched to a cls1 record — cls3 is
unreachable for it.**

`r5` is decided by **nine sorted cid membership lists** searched with the generic
binary search `0x02022E14(value, table, count)`, plus one per-cid switch:

| list | count | gate | contents (spot-checked by name) |
|---|---|---|---|
| `0x0228F7AC` | 0x67 | code 7 | Normal-Summon triggers |
| `0x0228F5B8` | 0x12 | code 7 + tribute | the Monarchs |
| `0x0228F580` | 0x0C | code 8 | Flip-Summon triggers |
| **`0x0228F63A`** | **0x1F** | **code 9, no further gate** | **plain "when this card is Special Summoned"** |
| `0x0228F5DC` | 0x17 | code 9 + `[+0x12]==cid` | Gorz / Kristya / the Aesir … |
| `0x0228F6C0` | 0x24 | code 9 + `[0x02298A28+0x10] & 1` | **the "when Synchro/Fusion/Ritual Summoned" set** |
| `0x0228F598` | 0x10 | code 7 or 8 | |
| `0x0228F60A` | 0x18 | code 7 or 9 | |
| `0x0228F678` | 0x23 | any | |

`0x0228F6C0` holds all four cards the handoff table named (Mist Wurm `0x1D7D`,
Locomotion R-Genex `0x2045`, Trishula `0x221C`, Vylon Alpha `0x24B1`) plus
Junk Warrior, Black Rose Dragon, Trident Dragion, Formula Synchron, Karakuri
Burei, the Vylons, the "when Fusion Summoned" HEROes and two Rituals — so
`[0x02298A28+0x10] & 1` is the **"this Special Summon was a proper
Fusion/Ritual/Synchro Summon"** flag.

### The deliberate second-cls1-record path is closed for this donor

`find_event_handler`'s `leftmost + offset` offset is computed at
`0x0224A7E6` — the **default arm** of a per-cid switch — as

```
0224A7E6  adds r0,r1,#0        ; r1 = the cid
0224A7E8  bl   0x020230D4      ; == (0x0202ABF8(cid) == 7)  ->  card_type>>1 == 7
0224A7EC  cmp  r0,#0 ; beq offset 0
0224A7F0  ldrb r0,[r4,#5] ; cmp r0,#1 ; bne offset 0      ; selector must be cls1
0224A7F6  ldrb r0,[r4,#4] ; cmp r0,#6 ; beq offset 0      ; event code must not be 6
0224A7FC  movs r0,#1
```

`card_type >> 1 == 7` means `card_type ∈ {14,15}` = **Spirit Monster**. So the
second cls1 record exists for **Spirits only** (they need one record for the
summon effect and one for the End-Phase return). Walked concretely for our donor:
`0x1E9C` routes `0x0224A1F2 → 0x0224A45A → 0x0224A464 → 0x0224A46E →
0x0224A4A2 → 0x0224A4B8 → 0x0224A4C6 → 0x0224A7E6` (the default arm), and its
`card_type_encoded` is 37 → `>>1 = 18 ≠ 7`. **The offset is always 0.**

Combined with the selector-1 fact above, **all three of the handoff's options are
dead**: cls3 is never reached by a summon event; the second cls1 record is
Spirit-only; and folding clause 2 into the shipped cls1 record would entangle the
in-game-confirmed clause 3.

### The chosen host: hook the list search, not the record

`0x022658B8` is the `bl 0x02022E14` that searches `0x0228F63A` inside the
`cmp r6,#9` block (entered at `0x022658AE`). Replacing it with a call into an ov5
stub gives us a place to run arbitrary code **on any Special Summon**, with the
cid live, and to return the engine's own verdict unchanged — so **no event is
posted for our donor and the shipped clause-3 cls1 record is never consulted.**

Verified `r5` stays 0 for `0x1E9C` all the way to `0x02265C70`: it is in none of
the code-9 lists, its cid reaches the switch **default** (`0x02265910`: `0x1E9C >
0x1D08` → `0x02265990`; `< 0x204E`; `> 0x1E2A` → `0x022659A8`; `< 0x1F93`;
`≠ 0x1F93` → `b 0x02265C1C`), and the tail lists (`0x0228F598` code 7/8 — skipped
for code 9 — `0x0228F60A`, `0x0228F678`) do not contain it.

**Reachability is structural, not assumed.** `0x022658B8` and `0x022658FC` (the
`0x0228F6C0` search that the four native "when Synchro Summoned" cards
demonstrably use) are in the **same straight-line block** — every instruction
between them is a fall-through or a forward `beq` that rejoins. Reaching the
second requires having executed the first.

### (b) The snapshot is free: rider nodes are per-ZONE

Node pool `0x0229D33C`, stride 10, chain head
`0x0229ACD2 + side*0xB3C + slot*0x14`. Writer
**`0x0219F190(r0 = side, r1 = slot, r2 = kind BYTE, r3 = key, [sp+0] = param)`**:

```
0219F1DC  strh <idx>,[chain tail]        ; append
0219F1DE..0219F208                        ; [node+2] low nibble = kind & 0xF
                                          ; [node+2] bits 4..7  = (kind & 0xF0) >> 4
0219F20C  strh r7,[r1]                    ; [node+0] = key
0219F20E  strh r2,[r1,#4]                 ; [node+4] = param
0219F214  strh <[0x0229DD14+0x2C]>,[r1,#6]
0219F218  strh #0,[r1,#8]                 ; next
```

Attaching one node per Dragon-occupied monster zone at resolution time IS the
snapshot: a Dragon summoned later has no node, and a protected Dragon that leaves
the field loses its node when the zone chain is cleared (`0x0219F2BC`).

### (d) "Until the end of the next turn" is a kind nibble, and needs NO code edit

The **turn-boundary node sweeper is `0x0219F9E0`**, called from exactly one site
(`0x021C1358`), inside the handler for animation opcode **3**
(`0x021C3D3C → 0x021C12F0`). Opcode 3 is queued by the **phase-8 handler**
`0x02258C3C` at its step 0; phase 8 is the last entry of the phase-handler table
`0x0226D2B0` (`0x0219D4C0`: `ldr r0,[0x0226D2B0 + phase*4] ; blx r0`), and the
very next step of that same handler queues opcode 4 → `0x021C102C`, which is the
**sole** site that does

```
021C1042  ldr r1,=0x0229DD14
          ldr r2,[r1,#0x34] ; eors r2,#1 ; str r2,[r1,#0x34]   ; toggle turn player
          ldr r2,[r1,#0x40] ; adds r2,#1 ; str r2,[r1,#0x40]   ; TURN COUNTER += 1
```

So the sweep runs **exactly once per turn, immediately before the turn flips**.

The sweeper dispatches on the node's kind nibble (jump table at `0x0219FA2C`,
`add pc` base `0x0219FA2E`):

| kind | arm | behaviour |
|---|---|---|
| 0, 4, 5 | `0x0219FAEE` | keep forever |
| **1, 2** | **`0x0219FA3E`** | **`n = [node+2]>>4`; if n == 0 free the node, else `n -= 1`** |
| 3 | `0x0219FA5C` | free only if key ∈ {`0x18D9`, `0x1F6A`} |
| 6, 7, 8 | `0x0219FA6C` | family 2: resolve the SOURCE locator to a cid, then a per-cid switch — `0x175D` (**Weapon Change**, "until the End Phase of your opponent's next turn") takes `0x0219FACE`, which frees when `[0x0229DD14+0x40] > [node+4]` |

The kind-1/2 arm is **unconditional — it never looks at the key** — so a node
created with duration nibble **1** survives the sweep at the end of the summoning
turn (1 → 0) and is freed by the sweep at the end of the following turn.
That is "until the end of the next turn" exactly, with **zero engine edits**.

Corroboration that this is the engine's own "next turn" idiom: `0x0221B18A`
attaches a family-2 kind-7 node whose param is `[0x0229DD14+0x40]` (the current
turn) against the Weapon Change arm above — the same duration expressed the other
way. That path is unusable here only because its arm is cid-gated on `0x175D`.

### (c) The protection host, and why it beats Safe Zone's divergence

`0x021B021C` is the general "may this card effect affect this monster" predicate.
Its "protected" exit is `0x021B0296` (`ldr r0,[sp,#0x58]` = the caller's supplied
default) and its "affectable" exit is `0x021B081E` (`movs r0,#1`).

Inside it, at `0x021B058C`, is a **family-1** rider link:

```
021B058C  ldr r2,=0x1A5C          ; Vehicroid Connection Zone
021B058E  adds r0,r6,#0           ; r6 = the TARGET's side
021B0590  adds r1,r5,#0           ; r5 = the TARGET's slot
021B0592  bl 0x021A1430           ; family-1 query (kind < 6, key@+0 IS a cid)
021B0596  cmp r0,#0 ; beq 0x021B059C
021B059A  b 0x021B0296            ; PROTECTED
```

Three things make this the right link:

1. **It is OUTSIDE the `targets` block.** The `targets` flag is read 0x2C bytes
   later (`0x021B05BE ldr r0,[sp] ; cmp r0,#0 ; beq 0x021B05EC`), and Heart of
   Clear Water's link — the one `patch_safe_zone` PART D borrowed — sits inside
   it. That is the entire origin of Safe Zone's documented DIVERGENCE.
   **This clause does not inherit it.**
2. **A non-targeting destruction really does pass through here.** Caller
   `0x02245B7A` builds a descriptor, calls the wrapper `0x021B0848` with
   `[sp+4] = 0` (i.e. `targets = 0`), and on a non-zero result calls
   `0x021CF35C → 0x021CF31C → 0x021CDD4C(desc, mask, r2 = 0x0E, r3 = 2)` —
   destination zone `0x0E` = the **Graveyard**, i.e. it destroys the monster.
   `0x021B0848` passes **0** as the predicate's `[sp+0x58]`, so "protected"
   returns 0 and the destroy is skipped (`0x02245B86 cmp r0,#0 ; beq`).
3. **It is on the live path, proven by a shipped in-game result.**
   `patch_safe_zone` PART D's hook at `0x021B05CC` is IN-GAME CONFIRMED
   (2026-07-21), and control can only reach `0x021B05CC` by first executing
   `0x021B0592` (`0x021B0596 → 0x021B059C → 0x021B05A2 → … → 0x021B05BE →
   0x021B05C6`, all fall-through or forward branches that rejoin).

Both players: neither `0x021B058C` (VCZ) nor `0x021B05FA` (Dreadmaster) applies a
controller test at this point, so simply **omitting** Safe Zone's opponent check
(`r7+2`) yields "neither player", which is what this clause wants.

### The key `0x1E9C` is inert to every other node consumer

Family-1 query `0x021A1430(side, slot, key)` → walker `0x021A1238`: accepts any
kind nibble < 6 and matches `[node+0] == key`; it never filters by kind. So a
`{key = 0x1E9C, kind = 2}` node is visible only to a query that names `0x1E9C`,
and the donor's cid has no other live reference in the build (PART D1 retargeted
its ov3 arm, PART D2 removed its arm9 table entry).

Checked against the two generic kind dispatchers:

* the sweeper `0x0219F9E0` — its kind-1/2 arm never reads the key;
* `0x0219FE0C` — its kind-1/2 arm switches on the key: `0x1E9C` compares
  `> 0x197D → 0x0219FF64`, `< 0x2223`, `< 0x1EEF`, then `≠ [sp+0x28]`. `[sp+0x28]`
  is built at `0x0219FE66..0x0219FE6C` as `0x1EEF - 0xE7 = 0x1E08 ≠ 0x1E9C`, so it
  falls to the **default arm `0x021A0076`**. (This is the ungreppable
  stack-held-base switch — the base was read out of the prologue, not guessed.)

### Attach API

`0x021C479C(r0 = side, r1 = slot, r2 = key, r3 = kind BYTE, [sp+0] = param)`
packs animation command `0x35 | (side ? 0x8000 : 0)` with
`arg1 = slot | kind<<8`, `arg2 = key`, `arg3 = param`, and queues it via
`0x021C3BC8`. The op-0x35 handler is `0x021C3E68 → 0x021BE044`, which unpacks it
and calls `0x0219F190(side, slot, kind, key, [sp]=param)` — the full kind BYTE
survives, so `kind | duration<<4` passes through. **`0x02265768` already makes
this exact call natively at `0x02265C6C`** (for cid `0x1A1F`, kind 2), so it is
legal from the function we are hooking.

### Helper primitives used

* `0x021A36EC(side, slot)` → the cid in that zone (0 when empty) —
  `[0x0229AC94 + side*0xB3C + slot*0x14 + 0x34]`, masked to 14 bits.
* `0x0202ABB8(cid)` → race (`[record+4] << 0xA >> 0x1B`); **Dragon = 1**.
* `0x02022E14(value, table, count)` → 1/0, binary search over sorted s16.

## Ruled Out

- **`0x0224A115` as the trigger predicate** — it is `movs r0,#2 ; bx lr`.
- **A cls3 record for the trigger** (the handoff's option 1) — the summon event
  word hard-codes selector 1 at `0x02265C8E`; cls3 is unreachable from it.
- **The deliberate `leftmost + 1` cls1 record** (option 2) — gated on
  `0x0202ABF8(cid) == 7` = Spirit Monster; our donor is card_type 37.
- **Folding clause 2 into the shipped cls1 record** (option 3) — unnecessary once
  the trigger is taken at the list search, and it would put an unproven clause
  inside an in-game-confirmed one.
- **Borrowing Heart of Clear Water's link at `0x021B05CC`** — already claimed by
  `patch_safe_zone` PART D, and it is inside the `targets` block, which is exactly
  the divergence this clause must avoid.
- **Re-using key `0x1A5C` (Vehicroid Connection Zone) so no new link is needed** —
  tempting (zero ov3 edits) but `0x1A5C` has a second consumer, `0x021AB90C`,
  which reads the **acting** card's own locator; a protected Dragon activating an
  effect could then be suppressed. Rejected in favour of a private key.
- **The Weapon Change turn-compare arm `0x0219FACE`** — reachable only when the
  node's source locator resolves to cid `0x175D`, and that switch is the
  ungreppable base±imm kind; the kind-1/2 countdown gives the same duration with
  no code edit.
- **The SS-commit hook `0x022692E6`** — not needed; `0x02265768` is downstream of
  it, already has the cid/side/zone in one struct, and is Special-Summon-scoped.

## Open Questions

- **How wide is `0x021B021C`'s destruction coverage?** One non-targeting
  destruction site (`0x02245B7A`) is proven to consult it. Whether *every*
  destruction-by-effect route in the engine does is not established — battle
  destruction certainly does not (that is `0x02197E90`, and it should not: the
  card only protects from card effects). In-game oracle 2 below is what settles it.
- **Puzzles.** Both stubs live in the ov5 cave, so in a puzzle (overlay 41 evicts
  overlay 5) the two hook `bl`s land in non-ov5 memory. This is the repo's
  standing accepted limitation and is **pre-existing at this very function**:
  `patch_safe_zone` PART D already hooks `0x021B05CC` inside `0x021B021C` into ov5
  and ships in `apply_all_patches`. No new class of risk; noted, not solved.
- Face-down Dragons: the loop attaches by static race, so a set (face-down)
  Dragon you control is protected too. Modern rulings agree, but it is untested.

## Deliberate divergences (documented, not accidental)

1. **Control change.** The node lives on the zone, so a protected Dragon that
   changes controller does not carry its protection across; the real card's
   protection is a one-shot application that follows the monster.
2. The protection is expressed as "this monster is not affectable by a card
   effect" (the `0x021B021C` exit), which is **broader** than "cannot be targeted
   or destroyed": any other question routed through that predicate is also
   answered "protected". That is the same over-approximation Vehicroid Connection
   Zone itself gets, on the same link.

## Next Experiment

In-game, **normal duel** (not a puzzle). Build the test ROM with
`.venv-1/Scripts/python.exe _build_azure_testbench.py` ->
`data/over_the_nexus/working/rom_azure_test.nds`, which is `rom_azure.nds` plus
`patch_testbench_decks`: **every CPU opponent deck becomes 20x Dark Hole + 20x
Smashing Ground**, both non-targeting destruction, so oracle 2 below fires every
turn instead of once a duel. Smashing Ground destroys the highest-DEF monster you
control and Azure-Eyes has DEF 3000, so it aims itself at the card under test.
(The 21 `sd*` structure decks, `rpg001_0_syoki.ydc` and `default_jf.ydc` are left
alone so you still have a board to play.) `rom_azure.nds` alone works too, just
much more slowly.

⚠️ **The testbench cannot produce oracles 1 and 3** — they need a TARGETING
effect, and neither the CPU decks nor the starting player deck's removal
(Fissure, Hammer Shot) targets. Put a targeting effect in your own deck, or edit
`DECK_CARDS` in `patch_testbench_decks`.

Oracles:

1. Synchro Summon Azure-Eyes while controlling another Dragon → target that
   Dragon with an opponent's **targeting** effect → **refused**.
2. Same board, hit it with a **non-targeting** destruction (Dark Hole / Torrential
   Tribute) → the Dragons **survive** (this is the question Safe Zone could not
   answer; if they die, `0x021B021C` is narrower than the `0x02245B7A` caller
   suggests and the finding above needs correcting).
3. Target one of your own Dragons with **your own** effect → also refused
   (both players).
4. A **non-Dragon** you control is **not** protected.
5. A Dragon summoned **after** the resolution is **not** protected (the snapshot).
6. Protection is still up during the opponent's next turn and **gone** from the
   turn after that.
7. **Regression:** clause 3 still offers in the Standby Phase and still lists only
   Normal Monsters; clause 1 still refuses a non-Tuner Effect Monster as material.

---

## BUILT (2026-08-24) — statically verified, NOT yet played

`patch_azure_eyes.py` **PART G**, build `_build_azure.py` ->
`data/over_the_nexus/working/rom_azure.nds`. The card is still deliberately held
out of `apply_all_patches` (its `PatchStep` stays commented out) until clause 2
has an in-game result.

**The edit is 8 bytes of overlay 3 plus two ov5 stubs (80 B + 32 B).**

| | G1 — trigger + snapshot | G2 — the protection |
|---|---|---|
| hook | `0x022658B8`, native `bdf5acfa` (`bl 0x02022E14`) | `0x021B0592`, native `f0f74dff` (`bl 0x021A1430`) |
| stub | `CAVE_AZURE_SSPROT = 0x0239D030`, 80 B in a 0x60 reserve | `CAVE_AZURE_PROT = 0x0239D090`, 32 B in a 0x30 reserve |
| what it does | replays the list search, returns its verdict **unchanged**, and for cid `0x1E9C` attaches `{key 0x1E9C, kind byte 0x12}` to every Dragon in the summoner's monster zones | replays Vehicroid Connection Zone's query, and only on a miss asks the same question about key `0x1E9C` |

`CAVE_FREE` bumped `0x0239D030 -> 0x0239D0C0`.

Stubs, disassembled **out of the built ROM**:

```
0239D030  push  {r3,r4,r5,r6,r7,lr}
0239D032  sub   sp, #8                ; scratch for 0x021C479C's [sp] param
0239D034  bl    0x02022E14            ; the native search, args untouched
0239D038  movs  r7, r0                ; its verdict -- returned verbatim
0239D03A  ldr   r4, =0x02298A28       ; the summon record
0239D03C  ldrh  r0, [r4, #0xe]        ; the summoned card's cid
0239D03E  ldr   r1, =0x00001E9C
0239D040  cmp   r0, r1
0239D042  bne   0x0239D072            ; any other card -> replay only
0239D044  ldrh  r6, [r4, #2]          ; side = its controller
0239D046  movs  r5, #0                ; zone
0239D048  movs  r0, r6 / r1, r5
0239D04C  bl    0x021A36EC            ; -> cid in that zone (0 = empty)
0239D050  cmp   r0, #0 ; beq next
0239D054  bl    0x0202ABB8            ; -> race
0239D058  cmp   r0, #1 ; bne next     ; Dragon == 1
0239D05C  movs  r0, #0 ; str r0,[sp]  ; param = 0, as the native call at 0x02265C6C
0239D060  movs  r0, r6 / r1, r5
0239D064  ldr   r2, =0x00001E9C       ; key
0239D066  movs  r3, #0x12             ; kind 2 | duration 1 << 4
0239D068  bl    0x021C479C            ; attach
0239D06C  adds  r5, #1 ; cmp r5,#5 ; blt loop
0239D072  movs  r0, r7
0239D074  add   sp, #8
0239D076  pop   {r3,r4,r5,r6,r7,pc}

0239D090  push  {r3,r4,r5,r6,r7,lr}
0239D092  movs  r4, r0 / r5, r1       ; side / slot
0239D096  bl    0x021A1430            ; VCZ's own query, args untouched
0239D09A  cmp   r0, #0
0239D09C  bne   0x0239D0A8            ; VCZ matched -> hand back its answer
0239D09E  movs  r0, r4 / r1, r5
0239D0A2  ldr   r2, =0x00001E9C
0239D0A4  bl    0x021A1430            ; our rider -> 1 = protected
0239D0A8  pop   {r3,r4,r5,r6,r7,pc}
```

Details that would each have been a silent bug:

- **`POP {..,PC}`, never `POP {..,LR}`** (`thumb-pop-into-lr-footgun`).
- **`ADD R5, #1` is the two-operand imm8 form.** The 3-operand Format-2
  `ADD Rd,Rs,#imm` caps its immediate at 7 and miscodes silently above that
  (`thumb-add-sub-imm3-footgun`).
- **`MOV Rd, Rs` on low registers is `LSL Rd,Rs,#0` and sets flags**, so no `MOV`
  sits between a `CMP` and the branch that reads it.
- **Six-register push + `SUB SP,#8`** keeps the stack 8-aligned across the
  scratch slot, matching the engine's own idiom in this function.
- **G2 needs no frame surgery.** The native `cmp r0,#0 ; beq ; b 0x021B0296`
  already routes a non-zero return to the protected exit — unlike Safe Zone's
  insert, which had to drop the saved LR and jump to `0x021B0296` itself.

**Register contracts checked, not assumed.** Every callee preserves `r4-r7`:
`0x02022E14` and `0x021A1430` push `{r3,r4,r5,lr}`; `0x021A36EC`'s body
`0x021A36F8` pushes and pops `{r1-r7}`; `0x0202ABB8 -> 0x0202A084` and
`0x021C479C` push only `r4` and were scanned instruction-by-instruction for
writes to `r5/r6/r7` (none); `0x021C3BC8` pushes `{r4,r5,r6}` and never writes
`r7`.

### Composition — measured

A **whole-overlay-3 diff of the built ROM against clean** finds 1377 changed runs
and **every one lands inside a region this module claims** (the cls1 and criteria
tables, the effect registry row, PART D1's arm, and PARTs F/G's 12 bytes). Zero
unclaimed bytes. Explicitly byte-identical to clean: `0x022482B2` (Boggart),
`0x022482B6` / `0x02248778` / `0x02248CAA` / `0x02249D26` (Quasar),
**`0x021B05CC` (Safe Zone PART D, in the same function as G2)**, LIST_A
`0x02275AB8`, and both Special-Summon trigger lists `0x0228F63A` / `0x0228F6C0`.

`verify()` = **PASS, 47 checks** (16 new for PART G, including that both caves
hold their stubs byte-for-byte, that `assert_thumb1_only` accepts them, that the
donor is absent from BOTH Special-Summon trigger lists — so no cls1 event is
posted and clause 3's record stays out of this path — that the reachability
anchor `0x022658FC` is still the sibling search and still finds all four native
"when Synchro Summoned" cards, and that Safe Zone's link is untouched).
`check_allocations` clean, ledger refreshed.

### KB

`verify_knowledge`: **292 facts, 260 PASS, 0 FAIL, 32 UNVERIFIED** (was 287 /
256 / 0 / 31). Four new VERIFIED facts, one correction, no regressions:

- `summon.trigger_is_a_membership_list` — the whole `0x02265768` mechanism, the
  nine lists, the three event codes, and the hard-coded selector 1. **This is the
  reusable one**: it is how any "when this card is Summoned" clause gets built,
  and it is what kills the cls3 option.
- `dispatch.second_cls1_record_is_spirit_only` — **corrects**
  `dispatch.find_event_handler_second_record`, which quoted only half the gate and
  is what made the handoff's option 2 look viable. The old fact is kept as
  UNVERIFIED with `corrected_by:` pointing here.
- `rider.node_writer_and_kind_byte` — `0x0219F190`, the node layout, and the
  duration nibble hiding in the kind argument.
- `rider.turn_sweeper` — `0x0219F9E0`, proven to run exactly once per turn, with
  the per-kind arms and the Weapon Change turn-compare.
- `rider.affect_predicate_protection_link` — `0x021B0592`, why it beats Safe
  Zone's link, and the destruction caller that proves it covers non-targeting
  destruction.

`card.azure_eyes_silver_dragon` updated: clause 2 recorded as **built and
statically verified, NOT yet in-game confirmed**, with its divergences.

---

## IN-GAME (2026-08-24) — the two hardest oracles PASSED on the first test

Reported by the user against `rom_azure_test.nds` (the card plus
`patch_testbench_decks`, whose CPU decks were 20x Dark Hole + 20x Smashing Ground
at the time — **both non-targeting destruction**):

> on the turn i summoned azure eyes it was immune to destruction and then the turn
> afterwards it could be destroyed

and, when asked, that **the duration is correct**.

| oracle | result |
|---|---|
| 2. NON-targeting destruction (Dark Hole / Smashing Ground) vs. a protected Dragon | **PASSED** |
| 6. protection up through the intended window, gone after it | **PASSED** |

**What that pair actually proves — this is the load-bearing part:**

1. **The trigger fires.** The G1 hook at `0x022658B8` is reached on the live
   Special-Summon path, and the summon-trigger evaluator `0x02265768` is what runs
   after a Synchro Summon. `summon.trigger_is_a_membership_list` moves from a
   structural argument to behaviour.
2. **The snapshot is attached and the query finds it.** A `{key 0x1E9C, kind 2}`
   rider really is written to the zone chain by `0x021C479C`, and the G2 link at
   `0x021B0592` really does read it back.
3. **⭐ `0x021B021C` GOVERNS NON-TARGETING DESTRUCTION.** This was the session's
   biggest open question and the one `patch_safe_zone` explicitly could not
   answer. The static argument (caller `0x02245B7A` passes `targets = 0` and then
   calls the send-to-GY primitive only if the predicate says affectable) is now
   backed by a duel. **Clause 2 does NOT inherit Safe Zone's divergence**, and
   `rider.affect_predicate_protection_link` is confirmed behaviour, not inference.
4. **The duration mechanism is right.** Kind byte `0x12` — kind 2 in the low
   nibble, countdown 1 in the high nibble — expires exactly when intended, so the
   turn-boundary sweeper `rider.turn_sweeper` runs once per turn as read.

⚠️ **I initially misread the report as an off-by-one and started re-deriving the
sweeper. It was not.** The user counts their own turns: summon on your turn T
(immune), opponent's turn T+1 (immune), your turn T+2 = "the turn afterwards"
(destructible). That is "until the end of the next turn" exactly. Do not "fix"
the duration nibble.

### ALL ORACLES CONFIRMED (2026-08-24) — clause 2 is DONE

Oracle 1 was untestable with the first harness (nothing in it targeted), so
`patch_testbench_decks` was re-armed with **Dark Hole + Offerings to the Doomed**
("Target 1 face-up monster on the field; destroy that target, also skip your next
Draw Phase") — a matched non-targeting / targeting pair, and Offerings being
Quick-Play lets the CPU fire it from a Set card during your turn too.

The user then confirmed **all remaining oracles**:

| oracle | result |
|---|---|
| 1. an opponent's **targeting** effect on your Dragon | **refused** |
| 2. **non-targeting** destruction (Dark Hole) | **survives** |
| 3. your **own** effect targeting your own Dragon | **refused** (both players) |
| 4. a **non-Dragon** you control | **not** protected |
| 5. a Dragon summoned **after** the resolution | **not** protected (the snapshot) |
| 6. duration — up through the next turn, gone after | **correct** |
| 7. regression — clauses 1 and 3 | **unaffected** |

So every design decision in PART G is now backed by behaviour:

* the trigger really is the summon-trigger evaluator `0x02265768`
  (`summon.trigger_is_a_membership_list`);
* **per-zone rider attachment really is the "Dragons you CURRENTLY control"
  snapshot** — oracles 4 and 5 are what prove that, and they are what would have
  failed had the design used a live "is a Dragon you control" predicate instead;
* `0x021B021C` governs **both** targeting and non-targeting effects, so clause 2
  does not inherit `patch_safe_zone`'s divergence
  (`rider.affect_predicate_protection_link`);
* omitting Safe Zone's opponent check really does give "neither player" (oracle 3);
* the kind byte's high nibble really is a per-turn countdown
  (`rider.turn_sweeper`).

---

## SHIPPED (2026-08-24) — wired into `apply_all_patches`

`PatchStep("AoJ Light Gazer -> Azure-Eyes Silver Dragon (clauses 3 + 1 + 2)")` is
live. Full chain: **36/36 patches applied** -> `rom_all_patches.nds`.

**The composition sweep the single-card ROM could never run.** New tool
`_verify_all_patches.py` runs `verify()` for every shipped card module against the
combined ROM, which is what CLAUDE.md's Patch Composition Rules require and which
`apply_all_patches` does not do by itself:

    PASS 25   FAIL 0   SKIP 3
    (skipped: minefield_driller, boggart_knight, darksoul -- no verify() of their own)

The four checks that only exist in the chain, all green:

| shared resource | check |
|---|---|
| ARM9 "Ally of Justice" table `0x0209CB96` (with Elder of the Six Samurai) | azure reads the count immediate LIVE: `count immediate is 20 (21 clean / 20 after elder)`, tail shifted, sentinel `0x2700` in slot 19 |
| Synchro-material predicates (with Shooting Quasar + Boggart Knight) | `0x022482B2` is boggart's BL, `0x022482B6` is quasar's BL, `0x02248AAC` is ours — and Quasar's own verify passes, so **the regression that was untestable on the single-card ROM is clean** |
| affect predicate `0x021B021C` (with Safe Zone) | `0x021B05CC` is safe_zone's BL, `0x021B0592` is ours — two links, one function, neither stolen |
| LIST_A `0x02275AB8` | donor still absent, so "1 OR MORE non-Tuner" survives Quasar's edits to the same list |

⚠️ **Row indices drift in the chain and that is normal**: the cls1 insert lands at
row **888** here vs 890 in the single-card build, and the criteria row at **758**
vs 759, because earlier patches already added and dropped rows. Everything is
count-neutral and sorted, which is what `verify()` actually asserts — never assert
an absolute row index.

⚠️ **`_verify_all_patches.py` had a bug worth remembering.** Its first run reported
**17 failures**. All 17 were `TypeError: verify() got an unexpected keyword
argument 'out'`: the ROM path is the FIRST POSITIONAL parameter of every `verify()`
in the repo but is named `out` in some modules and `out_path` in others. Calling it
positionally fixes all of them. A sweep that calls it by keyword looks exactly like
17 regressions — check the failure *text* before believing a red result.

The card is **not** puzzle-safe (PARTS F and G are ov5), which is the repo's
standing accepted limitation and is now stated in `_apply_azure_eyes`.
