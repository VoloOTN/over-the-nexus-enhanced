# Grapha, Dragon Lord of Dark World — findings (session 2026-08-27)

Printed text (`scratch/ygoprodeck_cache.json`) — DARK / Fiend / Level 8 /
2700 / 1800:

> You can Special Summon this card (from your Graveyard) by returning 1
> "Dark World" monster you control to the hand, except "Grapha, Dragon Lord of
> Dark World". If this card is discarded to the Graveyard by a card effect:
> Target 1 card your opponent controls; destroy that target, then, if this card
> was discarded from your hand to your Graveyard by an opponent's card effect,
> look at 1 random card in your opponent's hand, then, if it was a monster, you
> can Special Summon it to your side of the field.

Clauses:

1. **C1 — alternative Special Summon FROM THE GRAVEYARD.** Cost = return 1
   "Dark World" monster you control to the hand, excluding Grapha itself.
   (Not once per turn; no restriction on how it was sent to the GY.)
2. **C2 — discard trigger, base half.** Discarded to the GY by a card effect
   (either player's, from anywhere) → target 1 card your opponent controls,
   destroy it.
3. **C3 — discard trigger, bonus half.** Only if C2's discard was *from your
   hand* *by an opponent's* card effect → look at 1 random card in the
   opponent's hand; if it is a monster you may Special Summon it to YOUR field.

**STATUS: ✅ CLAUSE 1 DONE — IN-GAME CONFIRMED BY THE USER 2026-08-27.**

Round 2 retest, all six checks passed:

| # | check | result |
|---|---|---|
| 1 | offer + pick + bounce + summon at 2700/1800 Lv8 | all good |
| 2 | **no LP lost** (round 1's bug) | no damage taken |
| 3 | a "Dark World" **Spell/Trap** is NOT pickable | all good |
| 4 | still offered on a **full five-monster field** (part F) | confirmed |
| 5 | usable **twice in one duel** — Zephyros's once-per-Duel is NOT inherited | confirmed |
| 6 | no regressions (Zephyros, Snoww, Gates) | no regressions |

**NOT yet wired into `apply_all_patches`** — awaiting explicit ship approval.
Clauses 2 and 3 (the discard trigger) are not implemented.

### ROUND 1 IN-GAME RESULT (user, 2026-08-27)
> "Good attempt. I can activate the effect and bounce a card. However when
> grapha is summoned. I take 400 damage"

Follow-ups confirmed by the user: Grapha **does** end up on the field, the damage
is **exactly 400 every time**, and it lands **after he appears**.

So the offer, the candidate filter and the bounce cost ALL WORKED on the first
test. The only fault was inherited damage — see *THE 400-DAMAGE TRAP* below.
Donor and scope chosen by the user 2026-08-27: Zure `0x1961` with a truncated
name, clause 1 only.

* single-card ROM: `data/over_the_nexus/working/rom_grapha.nds`
* **test ROM (Gates + Snoww + Grapha): `data/over_the_nexus/working/rom_grapha_test.nds`**,
  129518216 B, **round 2** sha256 `9db2a38f6348fd40e7d62b76d930f34625142f1b52e8aa334476219e91444ea2`
  (round 1 was `b542eaaf…d34b176b` — the one that took 400 damage)
  -- all three modules' `verify()` run against that same file and PASS.
* build: `.venv-1/Scripts/python.exe _build_grapha.py --text`

## Confirmed (this session)

### The 3DS ships Grapha: cid `0x25F0` (adjacent to Snoww `0x25F1`)
`.venv-1/Scripts/python.exe -m otn_enhanced.tools.threeds_lookup "Grapha"` →
3DS index 4761, cid `0x25F0`. It owns **exactly one** registry row and it is the
summon-condition registry — **it owns no NDS criteria row** (the cid is absent
from the NDS build entirely):

```
summon_cond 0x6AC2D4 (stride 0x10, 262 rows) [185] 000125F0 004B4CEC 004CBB4C 004BAC30
```

`aux = 0x0001`. Slot layout `{u16 cid, u16 aux, u32 gate, u32 filter, u32 cost}`.

### The three 3DS handlers, and what shares them
Measured by dumping all 262 rows and counting handler occurrences
(`scratchpad/dump_sscond.py`):

| slot | handler | shared with |
|---|---|---|
| gate (+4)   | `0x004B4CEC` | Metalzoa, Red-Eyes Black Metal Dragon (3 rows total) |
| filter (+8) | `0x004CBB4C` | **UNIQUE to Grapha** (1 row) |
| cost (+C)   | `0x004BAC30` | **Mist Condor**, **Fallen Angel of Roses** (3 rows total) |

**The cost slot is the tell.** Mist Condor and Fallen Angel of Roses are the 3DS's
other two "Special Summon this card by RETURNING 1 <archetype/type> monster you
control TO THE HAND" cards. So `0x004BAC30` is the shared
**return-a-monster-you-control-to-the-hand cost machine**, and `0x004CBB4C` is
Grapha's private **candidate filter**. That split — shared cost machine + private
per-card filter — is the architecture to copy.

### `0x004CBB4C` decoded — it IS the printed filter, verbatim
ARM disassembly (`scratchpad/d3b.py 0x4CBB4C 60`). Args `(r0 = side,
r1 + r2 = zone)`; the sum `r4 = r1 + r2` is bounded `cmp r4,#4 / bgt reject`, i.e.
**the five MONSTER ZONES** — the filter searches the FIELD, not the GY:

```
0x4CBB5C  ldrh r0,[r6,#2] ; cmp r0,r5 ; bne reject      ; side must be the controller's
0x4CBB68  cmp  r4,#4      ; bgt reject                  ; monster zones 0..4 only
0x4CBB8C  ldrb r0,[..,#0x43] ; cmp r0,#0 ; beq reject   ; zone occupied?
0x4CBBA0  bl   0x3AE4F4   ; (side,zone) -> cid
0x4CBBA4  ldrh r1,[r6,#0xE] ; cmp r0,r1 ; bne 0x4CBBB8  ; <-- EXCEPT ITSELF
0x4CBBB0  mov  r0,#0      ; pop                         ; same cid  -> reject
0x4CBBB8  ...  bl 0x1CADFC ; beq reject                 ; set-code test ("Dark World")
0x4CBBDC  bl   0x3950C8   ; beq reject                  ; per-zone predicate
0x4CBBF4  bl   0x3B4708   ; bne accept                  ; short-circuit
0x4CBC08  bl   0x3C53E8   ; beq reject
0x4CBC20  mov  r0,#0x800  ; pop                         ; ACCEPT
```

`[r6+0x0E]` (`r6 = 0x007BE19C`, the live "card being resolved" descriptor) is the
**self cid**, and the `cmp r0,r1 / bne` is literally
*except "Grapha, Dragon Lord of Dark World"*. `[r6+0x02]` is the acting side.
Accept returns `0x800`, not 1.

### Zure, Knight of Dark World `0x1961` is a CLEAN donor and ALREADY a Dark World card
`.venv-1/Scripts/python.exe -m otn_enhanced.tools.donor_scan 0x1961`:

```
0x1961  Zure, Knight of Dark World   Normal Monster  Lv4 DARK Fiend 1800/1500
        VERDICT: CLEAN - no data structure names this cid
        1 ARM9 data-region u16 hit: arm9:0x0209CA08
```

That single hit is the **ARM9 Dark World set-code table** (`0x0209CA06`,
`setcode.dark_world_table`) — so a keep-cid donor inherits Dark World membership
for free, which matters because `patch_gates_of_dark_world` PART E2 consumed the
list's last phantom (`notes/gates-of-dark-world-findings.md`: "THE LIST NOW HAS
NO PHANTOM LEFT").

### ⚠️ THE NAME DOES NOT FIT ZURE'S SLOT
`"Grapha, Dragon Lord of Dark World"` = **33 B** (+NUL = 34).
Zure's English name slot is **26 B**; slots are a hard ceiling
(`donor.name_blob_has_no_slack`: no trailing padding, no unreferenced strings,
the one spare `card_indx` entry is a zero-length sentinel).

Full sweep of `donor_scan.cards()` for Normal Monsters with an **English** name
slot >= 33 B — there are only **four in the ROM**:

| cid | name | slot(name/desc, E) | type |
|---|---|---|---|
| `0x0FAD` | Winged Dragon, Guardian of the Fortress #1 | 42 / 115 | Lv4 WIND Dragon |
| `0x1121` | **La Jinn the Mystical Genie of the Lamp** | **38 / 63** | **Lv4 DARK Fiend** |
| `0x1291` | Gazelle the King of Mythical Beasts | 35 / 73 | Lv4 EARTH Beast |
| `0x1070` | Archfiend Marmot of Nefariousness | 33 / 81 | Lv2 EARTH Beast |

So the donor choice is a real trade (see `## Open Questions`).


### THE NDS ALREADY SHIPS CLAUSE 1 — Blackwing - Zephyrus the Elite `0x241C`
> "You can Special Summon this card from your Graveyard by returning 1 face-up
> 'Blackwing' card you control to the hand, except 'Blackwing - Zephyrus the
> Elite'."

Same sentence as Grapha C1 with a different archetype. Its complete wiring, read
out of the EU images this session:

| piece | value | how found |
|---|---|---|
| GY-action registry row 53 | `{0x241C, zone 0x0E, chk 0x0224C591, post 0x0224C6C1}` | dumped all 60 rows of `0x0228DDF8` |
| cls2 record[652] | `{0x241C, 0x02230EBD, 0x021E454D, 0x021F44D9, 0x021EB1B1, 0}` | `donor_scan 0x241C` -> cls2[652] |

Slot roles, each established by who else shares the pointer:

* **`+04 = 0x02230EBC` — the resolver.** Phase machine on `[0x0229AAFC+0x70]`
  (`0x7E`/`0x7F`/`0x80`). Contains **no cid literal and no cid compare**, so it is
  card-agnostic and reusable as-is.
* **`+08 = 0x021E454C` — the CANDIDATE FILTER.** A four-instruction tail-call:
  `push {r3,lr} ; ldr r3,=0x00208075 ; bl 0x021D6E40 ; pop {r3,pc}`.
* **`+0C = 0x021F44D8` — the "can this GY effect be offered" gate.** Calls
  `0x021A14E8(side, 0xB, cid, 5)` then falls into `0x021F04FC`.
* **`+10 = 0x021EB1B0` — THE SHARED "return 1 monster you control to the hand"
  COST MACHINE**, shared with **Genex Ally Birdman `0x2205`** ("You can Special
  Summon this card (from your hand) by returning 1 face-up monster you control to
  the hand") and nothing else. 3-phase on `[0x0229AAFC+0x7C]`; phase 0 registers
  a field selection via `0x0224BA34(side, cid, 0, 0x0224A8C1)`, phase 1 reads the
  pick out of `[0x0229DD94+0x78/+0x7C]` and bounces it with `0x021CF538`.

**The selection filter chain is closed statically:** the cost machine passes
`0x0224A8C1` as the selection callback; `0x0224A8C0` does
`find_event_handler(0x0224A118)` on the source descriptor, reads `[record+8]`,
and `blx`es it with `(source_desc, cand_side, cand_zone)`. So **cls2 `+08` IS the
per-card candidate filter**, and its argument shape matches `0x021D6E40`
(`r7`=source desc: `[r7+0]`=cid, `[r7+2]`=side; `r6`=cand side; `r5`=cand zone).

### `0x021D6E40` is a generic bitmask candidate predicate — and the mask is a Rosetta stone
Scanned overlay 3 for the exact 4-instruction thin-wrapper shape: **168 wrappers**
exist, each a `(mask -> cls-table user)` pair (`scratchpad/masks.py`). The two that
matter:

```
0x021E3E04  mask=0x00008015  cls2[544] +08  Genex Ally Birdman 0x2205
0x021E454C  mask=0x00208075  cls2[652] +08  Blackwing - Zephyrus the Elite 0x241C
```

Decoded arms of `0x021D6E40` (mask in r3 -> r4): bits 0-1 = side selector
(`01` = same side as source); **bits 4-6 are a 3-bit ZONE-CLASS FIELD**, not flags
(`switch` at `0x021D6F32` over `0x00/0x10/0x20/0x30/0x40/0x50`; Birdman's `0x10`
= "zone < 5"; Zephyrus's `0x70` is an unhandled case = no zone test); bit 15
(`0x8000`) at `0x021D714E`; bit 21 (`0x00200000`) at `0x021D72B2`.

**Bit 21 is set by exactly ONE of the 168 wrappers in the whole ROM — Zephyrus's.**
Its arm reads the SOURCE cid, sets a required count (2 iff source cid `0x13FC`,
else 1) and calls `0x021AD870` / `0x021AD488` / `0x021AD79C` — a *"leaves you with
enough monsters"* check. **It is not an archetype test.**

### ⚠️ RULED OUT — and this is the finding that shapes the patch
**The NDS's Zephyrus does NOT check "Blackwing" at all.** Proven three ways this
session:
1. `0x021D6E40`'s whole extent `0x021D6E40..0x021D7308` contains **no literal in
   `0x0209C000..0x020A0000`** (no set-code table pointer) and its 20 BL targets
   are all zone/count/card-type helpers — the two ARM9 ones, `0x02022FDC` and
   `0x0202307C`, are card-type checks via `0x0202ABF8` / `0x02022D70`.
2. Zephyrus's `+08` wrapper is *only* those four instructions — there is nowhere
   else for a test to live.
3. The Blackwing set code is **`0x3F`** (thunk `0x02023D09`, table `0x0209CE2C`,
   31 entries, found by walking the sorted u16 run around the `donor_scan` hit
   `0x0209CE5C` — its only reference is the pool word `arm9:0x02023D10`).
   Overlay 3 contains exactly **four** `movs rX,#0x3F`-then-`BL` sites and none is
   on Zephyrus's path.

So the NDS ships a *simplified* Zephyrus ("return 1 face-up monster you control").
Copying it verbatim would give Grapha the wrong cost.

### The 3DS supplies the missing test, and confirms the set code is shared
3DS `0x004CBB4C` calls `bl 0x001CADFC` on the candidate cid, and that function is:

```
0x1CADFC  mov r1, #0x0F
0x1CAE00  b   0x1C9AC8        ; has_set_code(cid, code)
```

**Set code `0x0F` — byte-identical to the NDS's Dark World set code**
(`setcode.dark_world_table`: thunk `0x020238B5` = `ldr r1,=0x0209CA06 ;
ldr r3,=0x02022E15 ; movs r2,#0x10 ; bx r3`, verified this session). The 3DS and
NDS share the set-code numbering, not just the cid space.

So the NDS-callable Dark World predicate is **`0x020238B5(r0 = cid) -> bool`**.

### ⚠️ `0x021F04FC` has a THREE-CID SPECIAL CASE that Zephyrus depends on
The `+0C` gate falls into `0x021F04FC`, which at `0x021F0546` compares the source
cid against `0x1B20` (Infernal Dragon), `0x20B9` (King of the Beasts) and
`0x241C` (Zephyrus) — those three call `0x021B9ECC(side)` (a free-zone check),
everything else takes the generic `0x021F0384(desc, r4)` branch. A new donor cid
is **not** in that triple, so it would take the wrong branch. This is the
`0x241C` literal that `donor_scan` reports at `ov3:0x021F05A4`.

## SHIPPED-TO-TEST architecture for C1 (built 2026-08-27)

| part | what | where |
|---|---|---|
| A | card_prop: Level 8, ATK 2700, DEF 1800 (DARK/Fiend already correct on both candidate donors) | `card_prop.bin` |
| B | name + description | `bin2.pac` |
| C | GY-action row `{donor, 0x0E, 0x0224C591, 0x0224C6C1}`, count-neutral over one of the SIX phantom rows (11/12/13/15/47/48) | `0x0228DDF8` |
| D | cls2 record `{donor, 0x02230EBD, CAVE_GRAPHA_FILTER, CAVE_GRAPHA_GATE, 0x021EB1B1, 0}`, count-neutral over a phantom cls2 row | `0x02275C04` |
| E | ov5 stub — candidate filter: `cid != donor` AND `0x020238B5(cid)` (Dark World) THEN tail-call `0x021D6E40(desc, side, zone, **0x00208015**)` | `CAVE_GRAPHA_FILT` `0x0239D250`, 68 B of 0x50 |
| G | ov5 stub — resolver: Zephyros's phase machine **minus his 400 LP self-damage** | `CAVE_GRAPHA_RES` `0x0239D350`, 64 B of 0x50 |
| F | ov5 stub — `+0C` gate: Zephyrus's `0x021F44D8` path with the `0x021B9ECC` branch taken unconditionally (works around the three-cid special case) | `CAVE_GRAPHA_GATE` `0x0239D2A0`, 152 B of 0xB0 |

Concrete values as built: GY-action **row 15** claimed in place off the phantom
`0x0EB2`; cls2 record `{0x1961, 0x0239D351, 0x0239D251, 0x0239D2A1, 0x021EB1B1, 0}`
inserted count-neutral over the phantom **`0x1A86`** (the nearer `0x194A` is
eclipse_wyvern's — `check_allocations` caught that collision before any ROM was
written, which is exactly what the guard is for).

⚠️ **All three stubs are ov5, so this card is NORMAL-DUEL ONLY.** A puzzle loads
overlay 41 over the ov5 cave and both stubs become inert.

Parts E and F are what make it *faithful to the 3DS* rather than a copy of the
NDS's simplified Zephyrus.

## ⚠️ THE 400-DAMAGE TRAP (round 1's bug, and the root cause)

**`cid`-agnostic is not effect-agnostic.** I reused Zephyros's `+04` resolver
`0x02230EBC` verbatim, on the reasoning that it contains no cid literal and no
cid compare and must therefore be card-agnostic. That reasoning is wrong: the
absence of cid checks proves the handler is not *dispatched* per-cid, never that
its *body* is generic. Its phase `0x7F` is nothing but

```
0x02230EEC  ldrb r1,[r5,#2]     ; side
0x02230EEE  movs r2,#0x19
0x02230EF0  lsls r2,r2,#4       ; r2 = 0x190 = 400
0x02230EF2  bl   0x021CFBC8     ; the damage primitive (desc, side, amount)
0x02230EF6  movs r0,#0x7e
```

**ROOT CAUSE: I quoted Zephyros's printed text from RECALL instead of grepping
`scratch/ygoprodeck_cache.json`** — precisely what CLAUDE.md's *Card Effect
Sourcing* rule forbids. The real text, quoted:

> **Blackwing - Zephyros the Elite** — "If this card is in your GY: You can
> return 1 face-up **card** you control to the hand; Special Summon this card,
> **and if you do, take 400 damage**. You can only use this effect of "Blackwing
> - Zephyros the Elite" **once per Duel**."

My recalled version had no damage clause, said "Blackwing card", and said "except
this card". All three were wrong, and each one mattered:

| recalled (wrong) | actual | consequence |
|---|---|---|
| no damage clause | "take 400 damage" | **the reported bug** — resolver reused verbatim |
| "1 face-up *Blackwing* card" | "1 face-up card" | my "Konami SIMPLIFIED it" conclusion was wrong; the engine is faithful |
| "except this card" | no self-exclusion | same |
| — | "once per Duel" | untested on Grapha — added to the checklist |

**FIX (part G):** `CAVE_GRAPHA_RES 0x0239D350`, 64 B — Zephyros's phase machine
with phase `0x7F` deleted. Provably equivalent minus the damage: `0x7F` does
nothing else and returns `0x7E` itself, so phase `0x80` returning `0x7E`
unconditionally (instead of branching on `[0x0229AAFC+0x74]`) is the same
machine.

## ⚠️ SECOND BUG, FOUND WHILE FIXING THE FIRST (not yet seen in-game)

Because Zephyros returns **1 face-up CARD** — any zone — his mask's zone-class
field (bits 4-6) is `0x70` = *no zone restriction*, versus Genex Ally Birdman's
`0x10` = *monster zones only*. Grapha's cost is **1 "Dark World" MONSTER**, and
**five of the sixteen** Dark World set-code members are Spells/Traps:

`0x1970` Dark World Lightning, `0x1973` Gateway to Dark World, `0x1B5A` Dark
World Dealings, `0x1C8B` The Gates of Dark World, `0x1D25` Dark World Grimoire

With `0x70` all five were legal picks. **Mask changed `0x00208075` →
`0x00208015`.** Bit 21 is kept — its arm is the candidate-level version of "the
cost frees the zone it needs".

## Ruled Out
- **That the NDS's Zephyrus checks "Blackwing".** It does not — three
  independent proofs, now KB fact `dispatch.zephyrus_has_no_archetype_test`.
- **That cls2 `+0C` could be left as Zephyrus's native `0x021F44D9`.** It routes
  into `0x021F04FC`, whose hard-coded cid triple is the *only* way to skip the
  free-monster-zone precondition, and a new cid cannot join it by data alone
  (`dispatch.gy_offer_free_zone_triple`).
- **Two dead ends on "where is the archetype test", both falsified before any
  code was written**: (1) the `0x021D6E40` mask — bit 21, the one bit unique to
  Zephyrus among all 168 wrappers, turned out to be a "leaves you enough
  monsters" count, not an archetype; (2) a per-cid `{cid, setcode}` data table —
  Zephyrus's three unexplained ARM9 hits (`0x020AA928`, `0x020AA9C8`,
  `0x020AEC88`) are unrelated AI/pointer tables.
- **Growing the name blob.** `_place_string`'s relocate-into-trailing-padding
  fallback is dead: `card_name_{E,F,G,I,S}.bin` carry 2-4 B of padding
  (`donor.name_blob_has_no_slack`, measured 2026-08-25).

## Open Questions
1. **Donor.** "Replace Zure" reads two ways and they produce different ROMs:
   - (A) **Zure IS the donor** (keep cid `0x1961`): Dark World membership is
     free, no archetype-table edit at all, 110 B description budget — but the
     name must be truncated to <= 26 B.
   - (B) **Zure is the archetype-table SACRIFICE**: donor is
     La Jinn `0x1121` (DARK Fiend, 38 B name slot → the full name fits), and the
     Dark World table swaps `0x1961` out for `0x1121`. Costs: Zure stops being a
     Dark World card, and the description budget drops to 63 B.
2. **Which clause is in scope this session** (C1, C2, or C3).

## Open Questions (updated 2026-08-27, after the build)
1. **The one un-measured link.** "cls2 `+08` is the candidate filter" is closed
   *statically* (cost machine -> `0x0224BA34(..., 0x0224A8C1)` ->
   `find_event_handler` -> `blx [record+8]`, with the argument shape corroborated
   by `0x021D6E40`'s own dereferences) but **no GDB trace has shown it firing on
   the live path**. If the summon is offered but the pick list is wrong, this is
   the first suspect.
2. Whether `0x021A14E8(side, 0xB, cid, 5)` — the rider gate transcribed into the
   `+0C` stub — behaves differently for a Fiend than for a Winged Beast. No
   reason to think so; noted because it is transcribed, not reasoned about.

## Next Experiment
Clause 1 is closed. The remaining work on this card is **clauses 2 and 3**, the
discard trigger:

> If this card is discarded to the Graveyard by a card effect: Target 1 card
> your opponent controls; destroy that target, **then**, if this card was
> discarded from your hand to your Graveyard by an **opponent's** card effect,
> look at 1 random card in your opponent's hand, then, if it was a monster, you
> can Special Summon it to your side of the field.

The machinery is already mapped by the two shipped Dark World cards in this ROM:
the effect-discard arm `0x021D185C` (`event.dark_world_discard_arm`, kind 0 via
`0x021C6D58`) that `patch_snoww` PART A hooks, and Goldd's two-phase
resolver skeleton that `patch_snoww`'s clause 2 clones. The donor already owns
its cls2 record from clause 1, so clause 2 needs a criteria row for "1 card your
opponent controls" plus a destroy resolver — and ⚠️ the donor would then own a
SECOND criteria row, which needs LIST A or LIST B membership to be addressable
(`dispatch.criteria_block_size_tiers`); LIST B is full and LIST A's last spare is
`0x0D81`.

⚠️ **Carry the round-1 lesson into it:** grep the printed text of every TEMPLATE
card whose handler gets reused, not just Grapha's own — see the 400-damage trap
above.

# ===========================================================================
# HANDOFF SUMMARY — 2026-08-27.  Continuation prompt: PROMPT_grapha_clause2.md
# The round-by-round log below is kept in discovery order; this section is the
# reconciled state and WINS where the two disagree.
# ===========================================================================

## Confirmed (with how each was proven THIS SESSION)

- **CLAUSE 1 IS DONE — in-game confirmed by user 2026-08-27** (all six checks:
  offer, Dark-World-monsters-only pick list, self excluded, pick returns to hand,
  Grapha arrives 2700/1800 Lv8, no LP lost, still offered on a full field, usable
  twice in one duel, no regressions). Donor Zure `0x1961`, seven parts A–G.
- **`desc[+3]` / `desc[+5]` are the posted EVENT CODE, split** (bits 16..20 and
  21..23) — disassembly of the event-post primitive `0x021D32A0`. NOT a zone and
  a record class. This invalidated three rounds of discriminator work.
- **The event-post primitive has exactly four callers**, and two build their code
  at RUNTIME: `0x0224B1BE` fixed `0x4B`; `0x0224C6EE` fixed `0x4E` (the GY-action
  `post_fn`, i.e. clause 1); `0x0224B31C` dynamic `[r6+4] & 0x1F` (so `desc[+5]`
  is always 0); `0x0224B120` dynamic off the stack.
- **An ABSENT slot4 is reported as 1**, not 0 — wrapper `0x0224AE50`,
  `cmp r2,#0 ; beq` → `movs r0,#1`. Returning 0 means "call me again": measured
  in-game as a hang, slot entered 6,455 times.
- **`r1` (the event arg) is 0 on the GY-action path** — the `0x4E` word never
  reaches the resolver. KB `resolver.event_arg_is_zero_on_gy_action`.
- **3DS↔NDS cls2 correspondence over 662 shared cids** —
  `ygo_tools/tools/threeds_cls2_map.py`. Grapha's clause-2 record should be
  `{0x1961, <own resolver>, 0x021DE7C9, 0x0224A115, 0, 0x02234DA5}`
  (105 cards agree on `+0C`, 16 on `+14`). Still the target.
- **The 3DS discard/event-trigger registry** `0x006C6780`, stride 0x18, 815 rows;
  Grapha is row 771. KB `dispatch.threeds_discard_trigger_registry`.
- **KB state on handoff:** `TOTAL 337 facts: 304 PASS 0 FAIL 33 UNVERIFIED`.
  Allocation guard: `141 ov5 slots (128 live), 101 phantom claims, 10 ov3
  dead-code claims (74 B free)` / `[OK] ... ledger in sync`.

## Ruled Out — do not retry

1. **Re-homing clause 1 to the summon-procedure registry `0x0228F158`** — dumped
   all 133 rows; NO Graveyard self-summon is in it (Zephyros, Plaguespreader,
   Glow-Up Bulb all absent). Hand-SS only.
2. **`0x4E` event code as an `r1` test** — `r1 == 0` measured.
3. **`desc[+3] == 0x0B` (the hand) as the clause-2 signal** — measured `0x0E`.
4. **A latch written by `+0C`** — `+0C` is POLLED (19 calls / 3 activations), so
   the latch is re-armed before the next activation. Consume-once failed too.
5. **`LR == 0x0224AE13` as the clause-2 signal** — that LR is CLAUSE 1's.
6. **`desc[+3] == 0x0E` alone** — the discard path matched it as well.

## Open Questions

1. **Does the discard ever reach the Dark World arm `0x021D185C` for `0x1961`?**
   PART H is proven only STATICALLY (the `verify()` switch walk). The arm only
   sets `[sp+0x14] = 1`; the posting is downstream and evidently does not happen.
2. If it does reach the arm: is the blocker the RECORD SHAPE?
   `event.optional_trigger_is_record_shape` — Snoww's record was the bare Sangan
   shape `{+04, 0, 0, 0, 0}` when its trigger first fired; Grapha's has all five
   slots populated.
3. Is `desc[+5] == 2` (added to the test in the final build) doing anything at
   all? UNTESTED, and probably irrelevant if the discard never arrives.

## Next Experiment

**Instrument PART H's ov3 arm stub with an arrival counter** (~12 B; free ov3
blocks `0x021B58D0` 12 B and `0x021B5AAA` 10 B). ⚠️ MUST be ov3, not ov5 — the
stub is on a shared path that runs in puzzles. Extend
`ygo_tools/tools/grapha_diag.py` to print it; take one savestate immediately
after a Grapha discard.

* counter **0** → PART H is the bug; diff the arm's stack gates against Snoww,
  which fires with the same hook on node `0x021D15EE`.
* counter **> 0** → the posting is the bug; test the record shape by temporarily
  reducing the record to `{+04 = 0x02204899, 0, 0, 0, 0}`.

⚠️ **Do not write another dispatcher before this measurement.** Five were built
and killed in-game; all five were solving a problem that may not exist.

## Latest ROM

`data/over_the_nexus/working/rom_grapha_test.nds` sha256
`69678e81e920a99f413d9d1d0d2fff8506198e7746cb5113ee859e0e5acefaa5`
(gates=PASS snoww=PASS grapha=PASS). **Safe stopping point:** clause 1 works,
clause 2 is inert and harmless because nothing routes to it.

# ===========================================================================
# CLAUSE 2 — "Target 1 card your opponent controls; destroy that target"
# session 2026-08-27, RE only. NO ROM CODE WRITTEN. ONE BLOCKER, see below.
# ===========================================================================

## C2 Confirmed (this session)

### The action is native, twice over — Kahkki and Gren
Printed text grepped from `scratch/ygoprodeck_cache.json` (applying the round-1
lesson: grep every template, never recall):

* **Kahkki, Guerilla of Dark World `0x1B3E`** — "If this card is discarded to the
  Graveyard by a card effect: **Target 1 monster on the field; destroy that target.**"
* **Gren, Tactician of Dark World `0x1B3F`** — "…**Target 1 Spell/Trap Card on the
  field; destroy that target.**"

Grapha C2 is those two merged (any card type) and narrowed to the opponent's
side. Both are already in the effect-discard arm, and their cls2 records are
identical except for the candidate filter:

```
cls2[239] 0x1B3E Kahkki  {02204899, 021D8CE5, 0224A115, 0, 02234DA5}
cls2[240] 0x1B3F Gren    {02204899, 021DB3BD, 0224A115, 0, 02234DA5}
cls2[192] 0x1969 Goldd   {0221FB51, 021DE7C9, 0224A115, 0, 0223847D}
```

* `+04 = 0x02204899` — the DESTROY resolver. A thin wrapper:
  `push {r3,lr} ; bl 0x02204674 ; movs r0,#0 ; pop`. **No phase machine** — it
  acts once and returns 0 (= done).
* `+0C = 0x0224A115` — `movs r0,#2 ; bx lr`, activatable unconditionally.
* `+14 = 0x02234DA5` — the target declaration: `ldr r2,=0x119 ;
  ldr r3,=0x02234CA5 ; bx r3`, i.e. the shared picker with **param `0x119`**.

### The candidate filter for "1 card your opponent controls" is FREE
From the 168-entry mask corpus (`dispatch.zone_predicate_mask_rosetta`):

```
0x021DE7C8  mask=0x00001472  cls2[192] +08  Goldd, Wu-Lord of Dark World
```

Goldd's printed text targets "**up to 2 cards your opponent controls**" — the same
domain as Grapha's "1 card your opponent controls". Decoding `0x00001472`
against the fields established in round 1: bits 0-1 = `0b10` = **opponent's side**
(`cmp r6,r0 / bne continue` arm at `0x021D6E6C`), zone-class field = `0x70` =
**no zone restriction** (so monsters AND Spells/Traps), plus bits 10 and 12 which
Kahkki and Gren also carry. **So `+08 = 0x021DE7C9` is exactly right, verbatim,
no ov5 stub.** (Contrast Kahkki `0x00001410`, zone field `0x10` = monster zones,
side bits 0 = either side; Gren `0x00021440`, zone field `0x40` = Spell/Trap
zones — which is how the field's values decode: `0x10` zone<5, `0x40` 5<=zone<=10,
`0x70` unrestricted.)

### The trigger is Snoww's PART A recipe
The Dark World effect-discard arm `0x021D185C` is a GATE, not a post:

```
0x021D185C  ldr r0,[sp,#0x34] ; cmp r0,#0xB ; bne reject   ; SOURCE ZONE == HAND
0x021D1862  ldr r0,[sp,#0x18] ; cmp r0,#0   ; beq reject   ; it was an EFFECT discard
0x021D1868  ldr r0,[sp,#0x10] ; cmp r0,#0   ; ble reject
0x021D186E  b 0x021D199E -> `movs r0,#1 ; str r0,[sp,#0x14]`   ; set the qualifies flag
```

⚠️ Note the hand gate is CORRECT for Grapha, not a deviation: "discard" is by
definition from the hand. Admitting the donor needs the same switch-node hook
`patch_snoww` PART A used on the `0x021D1392` per-cid chain.

## ⚠️ C2 BLOCKER — clause 1 and clause 2 must share ONE cls2 record

`find_event_handler 0x0224A118` selects its table from **`desc[+5]`, the record
class** (`ldrb r0,[r4,#5] ; cmp r0,#3 ; bhi reject` then a 4-arm jump table:
class 0 -> cls2 `0x02275C04` unless `desc[+4]==0x25`, class 2 -> cls1, class 3 ->
cls3). Both of Grapha's clauses are class 0, so **both resolve to cls2**, and a
second cls2 record on one cid is shadowed by the leftmost-record rule (the
Warwolf E1/E2 failure). So one record, and:

* `+04` must be clause 1's summon **and** clause 2's destroy;
* `+08` must be clause 1's "Dark World monster I control" bounce filter **and**
  clause 2's "card my opponent controls" target filter.

And the phase cannot separate them: `resolver.phase_protocol` (VERIFIED) says the
entry phase is **`0x80` for both**.

### What IS proven about the discriminator
* There is exactly **ONE** resolver invocation site in the build:
  `0x0224AF00 blx r2` inside the invoker `0x0224AEB8(r0 = desc, r1 = event)`,
  reached after `find_event_handler` + `ldr r2,[r0,#4]`. (Of the 18
  `find_event_handler` callers, only `0x0224AEEE` and `0x0224AF3A` touch slot
  `+04`, and the second only COMPARES it against `0x02208DB1` — it never calls.)
* The invoker has **8 call sites**; three pass `r1 = 0` literally
  (`0x0221803E`, `0x02228F92`, `0x0225BCF8`) and the rest pass a live r1. Two of
  them set the phase to `0x80` immediately before (`0x02258ECE` passes a live
  r1, `0x0225BCF8` passes 0).
* **The event-post primitive `0x021D32A0` has exactly FOUR callers in the whole
  build, and their event codes are distinct:**

  | post site | event code |
  |---|---|
  | `0x0224B154` | `0x01` |
  | `0x0224B1BE` | `0x4B` |
  | `0x0224B31C` | `0x1F` |
  | **`0x0224C6EE`** | **`0x4E`** |

  `0x0224C6EE` is the tail of `0x0224C6C0` — **the GY-action registry's own
  `post_fn`, i.e. clause 1's path**, and it is the ONLY site posting `0x4E`. It
  builds the word as `(0x4E << 16) | (r1 & 0xFFFF) | <bit31 flag>`
  (`movs r0,#0x4E ; lsls r0,#0x10 ; orrs r4,r0` @`0x0224C6D4`).

**So the candidate discriminator is `(event >> 16) & 0xFF == 0x4E` = "this is the
GY-action activation (clause 1)", anything else = the discard trigger (clause 2)
— and it is statically unique.**

### The one UNPROVEN link
Whether that packed event word is what arrives at the resolver as **r1**.
`resolver.phase_protocol` states "a 2-arg resolver must still preserve r1 = the
event", and `0x02206F40` parks it with `str r1,[sp]` — but nothing read this
session shows the `0x4E`-tagged word travelling from `0x0224C6EE` to
`0x0224AF00`'s r1. **Do not build on it until it is measured.**

## C2 Next Experiment
ONE melonDS GDB session (the stub is one-shot — connect once, arm everything,
collect in a single window, write to a file; `tool.gdb_one_shot_session`):

* breakpoint `0x0224AF00` (the `blx r2`), in a NORMAL DUEL with the round-2
  Grapha ROM;
* capture **r1** and the first 8 bytes at **r0** (the descriptor: `[+0]` cid,
  `[+2]` side, `[+4]` zone, `[+5]` class) on two triggers:
  1. activating Grapha's clause-1 GY offer, and
  2. discarding Grapha with The Gates of Dark World.
* **Expected if the hypothesis holds:** `(r1 >> 16) & 0xFF == 0x4E` on capture 1
  and something else on capture 2. Any descriptor byte that also differs is a
  second, possibly cheaper discriminator — `desc[+4]` (zone) is the one
  `card.lightpulsar_clause1` uses and `desc[+5]` is `card.darkflare_clause2`'s.

Only after that: build C2 as `+04` = a branching ov5 resolver (clause-1 arm as
today, else tail-call `0x02204898`), `+08` = a branching ov5 filter (clause-1
arm as today, else tail-call `0x021DE7C8`), `+14` = `0x02234DA5`, plus the
switch-node hook admitting `0x1961` to `0x021D185C`.

## C2 — THE 3DS DEEP RE (2026-08-27), and what it settles

### A previously-unknown 3DS registry: the DISCARD/EVENT-TRIGGER table
`threeds_lookup` reported Grapha owning only a `summon_cond` row, because the
registry list in `CARDS_ZEXAL_3DS_ASM.md` does not contain the table its discard
effect lives in. Found by taking the six native Dark World discard monsters,
listing every aligned u16 occurrence of each, and looking for a common lattice:

```
Beiige 0x1965 @0x6C7980   Broww 0x1966 @0x6C7998   Sillva 0x1968 @0x6C79B0
Goldd  0x1969 @0x6C79C8   Kahkki 0x1B3E @0x6C7E30  Gren   0x1B3F @0x6C7E48
GRAPHA 0x25F0 @0x6CAFC8
```

All seven are on one **stride-0x18** lattice. Walking it while `row[0]` stays a
plausible cid gives **base `0x6C6780`, 815 rows** — NOT the doc's `on_trigger`
`0x6C335C` (whose base is not even on this lattice; `delta 0x3424`). Row shape
`{u32 cid, u32 resolver, u32 filter, u32 glue, u32, u32 target_decl}`:

```
[192] Beiige  00001965 0045E090 00000000 00000000 00000000 00000000
[193] Broww   00001966 00459688 00000000 00000000 00000000 00000000
[194] Sillva  00001968 004344AC 00000000 00000000 00000000 00000000
[195] Goldd   00001969 0043464C 003E3E10 00404260 00000000 00476000
[242] Kahkki  00001B3E 00458888 003DBCA8 00404260 00000000 00477BB8
[243] Gren    00001B3F 00458888 003DFB90 00404260 00000000 00477BB8
[771] GRAPHA  000025F0 0045579C 003E3E10 00404260 00000000 00477BB8
```

### ⭐ IT CONFIRMS TWO OF THE THREE NDS SLOT CHOICES, INDEPENDENTLY
* **`+08` filter: Grapha shares `0x003E3E10` with GOLDD.** On the NDS I had
  picked Goldd's `0x021DE7C9` for the same reason (his printed text targets
  "cards your opponent controls"). The 3DS makes the same pairing — the choice is
  no longer an inference.
* **`+14` target declaration: Grapha shares `0x00477BB8` with KAHKKI AND GREN.**
  On the NDS I had picked Kahkki/Gren's `0x02234DA5`. Same pairing again.
* **`+04` resolver: Grapha does NOT share Kahkki/Gren's `0x00458888`** — it has
  its own `0x0045579C`, because its clause has the C3 rider on top of the plain
  destroy. So an ov5 resolver on the NDS is right, not a reuse.

### Grapha's 3DS clause-2 resolver decoded — including the C3 gate
`0x0045579C` is a phase machine over **phases 0x7B..0x80** (six arms):
`ldr r1,[r0,#0xBB4] ; sub r1,r1,#0x7B ; cmp r1,#6 ; ldrlo pc,[pc,r1,lsl #2]`.
One arm does `bl 0x003F1BB4` then returns **0x7F**; the next tests
`[0x007BB6AC]`, then **two BITS of the flags word `[r4+0x30]` against the side
`[r4+2]`** (`lsl r2,r1,#0xC ; cmp r0,r2,lsr#31` and `lsl r1,r1,#0x16 ;
cmp r0,r1,lsr#31`) before returning **0x7E**. Those two bit tests are exactly
C3's condition — *discarded from your hand* AND *by an opponent's card effect* —
so when C3 is built, that flags word is where its gate lives.

### ⚠️ WHAT IT DOES **NOT** SETTLE — and why
**In the 3DS the two clauses are in TWO DIFFERENT REGISTRIES**: clause 1 is
`summon_cond[185]` and clause 2 is `discard_trigger[771]`. They also run on
**different phase counters** — clause 1's slot3 `0x004BAC30` switches on
`[r5+0x26]` with values 0/1/2, clause 2 on `[0x007BE250+0xBB4]` with 0x7B..0x80.
So the 3DS never faces the NDS's problem and cannot answer it.

On the NDS both paths demonstrably reach **cls2 `+04`**: Grapha clause 1 does (it
is in-game confirmed working through `RES_STUB`), and the discard trigger does
(Snoww's shipped cls2 `+04` fires on it, as do Kahkki's and Gren's). So the
shared-record collision is real on the NDS regardless.

**BUT the 3DS raises the odds on the discriminator.** `resolver.phase_protocol`'s
own SCOPE LIMIT already records that the NDS likewise drives different activation
paths from different counters — `card.maiden_clause1` measured
`[0x0229AAFC+0x70] == 1` on every entry, never 0x80, and slot4's procedure uses
`[0x0229AAFC+0x7C]`. Grapha clause 1 provably uses `+0x70` with 0x80. **So
"the discard path presents a different counter or a different value at +0x70" is
now the leading hypothesis, alongside the `0x4E` event code — and both are read
by the same one-shot measurement.**

## C2 — BUILT 2026-08-27 (measurement build), `verify()`-green

**ROM: `data/over_the_nexus/working/rom_grapha_test.nds`**, sha256
`4605a7c23d744f04540360e2dfd000f559e2a4409a9dc2922328c560992e87f8` —
gates=PASS snoww=PASS grapha=PASS against that same file.

| part | what | where |
|---|---|---|
| H | admit the donor to the Dark World effect-discard arm | ov3: `BL` at `0x021D14E2` -> 16 B stub at `0x021B594A` |
| I | cls2 `+14` target declaration | `CAVE_GRAPHA_DECL 0x0239D3E0`, 48 B |
| J | cls2 `+04` resolver dispatcher | `CAVE_GRAPHA_RES2 0x0239D420`, 72 B |
| K | cls2 `+08` filter dispatcher | `CAVE_GRAPHA_FILT2 0x0239D480`, 68 B |
| L | diagnostic block | `CAVE_GRAPHA_DIAG 0x0239D3A0`, 0x40 B |

cls2 is now `{0x1961, 0x0239D421, 0x0239D481, 0x0239D2A1, 0x021EB1B1, 0x0239D3E1}`.
Clause 1's own three stubs are **byte-identical and untouched** — J and K are
dispatchers that call them.

### PART H, the trigger — and why it is ov3
The donor reaches terminal node `0x021D14E2` with `r1 = 0x1969` and falls to the
default leaf. The node is `subs r1,#0x23 ; cmp r5,r1 ; bne default ;
b <Ojamagic> ; b <default>`, and **nothing in overlay 3 branches to `0x021D14E2`
or `0x021D14E4`** (asserted), so those two halfwords become a `BL`. The stub is
exactly 16 bytes:

```
subs r1,#8        ; 0x1969-8    = 0x1961  the donor
cmp  r5,r1
beq  ours
subs r1,#0x1b     ; 0x1961-0x1B = 0x1946  Ojamagic -- the value AND the flags
cmp  r5,r1        ;                        the caller's `bne` expects
bx   lr
ours: BL 0x021D185C                       ; LR is dead (the caller POPs PC)
```

⚠️ **It MUST live in ov3, not ov5**: this is a shared path — every effect discard
of every card runs it — and a puzzle loads overlay 41 over the ov5 cave, so an
ov5 target here would freeze the game. It occupies the two ADJACENT 8-byte dead
blocks `0x021B594A` (phantom `0x19D1`) + `0x021B5952` (phantom `0x19D3`), both
previously unclaimed, giving exactly the 16 bytes needed.

`verify()` walks the whole chain and asserts the donor now reaches
`0x021D185C` while **Ojamagic `0x1946`, Kahkki, Goldd and Beiige all keep their
own arms**.

### ⚠️ A COMPOSITION REGRESSION THE SWEEP CAUGHT, AND IT WAS REAL
The first chain build reported **snoww=FAIL**. Two distinct causes, both worth
recording:

1. `patch_snoww._switch_leaf` stops at any `BL` whose target is not its OWN stub,
   so every cid routed through PART H's node looked like it had changed leaf.
   Fixed by making the tracer walk into any **registered** stub
   (`patch_snoww.register_switch_stub`), so PART H is modelled by its own
   instructions instead of a second hand-written model that could drift.
2. Then it correctly reported that `0x1961` had changed leaf — which it had, on
   purpose. Snoww's regression walk only exempted its own donor. It now takes a
   registry of other patches' donors, and accepts **either** the stock leaf or
   the declared arm, because whether that patch has been applied yet depends on
   chain order.

Net effect of a full-cid diff (`0x0D00..0x2700`): exactly **two** cids changed
leaf, `0x1961` (this patch) and `0x1C18` (Snoww's), both intended.

### THE DISCRIMINATOR IS A MEASUREMENT, NOT A CLAIM
`+04` and `+14` receive the event and test
`(event >> 16) & 0xFF == 0x4E` — clause 1's GY-action post `0x0224C6EE` is the
only one of the four `0x021D32A0` post sites stamping `0x4E`.

⚠️ **`+08` never receives the event** (its args are `(src_desc, cand_side,
cand_zone)`), so it keys on the declared-target counter `[0x0229AAFC+0x74]`:
nonzero -> Goldd's opponent-side filter, **zero -> clause 1's filter**. The zero
case is deliberately the safe default: if the counter is not yet set while the
picker enumerates, clause 2's target list is wrong but **clause 1 — the
in-game-confirmed clause — behaves exactly as it does today**.

All three stubs record what they were handed into `CAVE_GRAPHA_DIAG`. Read it
with:

```
.venv-1/Scripts/python.exe -m ygo_tools.tools.grapha_diag <savestate.ml?>
```

One duel that does both things therefore settles the discriminator whether or not
clause 2 worked. Test checklist (C1..C5) at the top of `_build_grapha.py`.

## C2 ROUND 1 IN-GAME (2026-08-27) — clause 2 inert, CLAUSE 1 REGRESSED, cause MEASURED

User's report, verbatim:
> "1. No prompt occurs, grapha does not activate.
> 2. Cannot verify
> 3. Card gets returned to hand but grapha does not special summon from GY.
> 4. Cannot verify
> 5. All work."

So: clause 2 never fired; **clause 1 regressed** — the offer, the pick and the
bounce cost all still worked, but no summon; and PART H's switch surgery is clean
(every other Dark World card and Ojamagic still behave).

### THE DIAGNOSTIC BLOCK ANSWERED IT IN ONE READ
Savestates `rom_grapha_test.ml2` (before activation), `.ml3` (selecting the card
to return), `.ml4` (after it "resolved"), via
`ygo_tools/tools/grapha_diag.py`:

```
[00] +04 resolver entries              1 -> 1 -> 2
[04] +04 last event (r1)               0x00000000     <-- NOT a packed 0x4E word
[08] +04 last phase [0x0229AAFC+0x70]  0x00000080     <-- entry phase, as documented
[0C] +04 last        [0x0229AAFC+0x74] 0x00000000
[10] +08 filter entries                0x227 -> 0x304 -> 0x372
[18] +14 declaration entries           1 -> 1 -> 2    <-- tracks +04 exactly
[1C] +14 last event (r1)               0x00000000
```

**`r1` is ZERO on the clause-1 path.** The `0x4E` event code that the GY-action
post `0x0224C6EE` stamps into bits 16..23 never reaches the resolver — so
`(0 >> 16) & 0xFF == 0 != 0x4E`, and BOTH `+04` and `+14` took the clause-2 arm:
the declaration called the target picker and the resolver called Kahkki's
destroy instead of the summon. Cost paid, nothing summoned. Exactly the symptom.

That also explains the `+14` counter tracking `+04` in lockstep — both were
running clause 2's path on a clause-1 activation.

⚠️ These three savestates only cover CLAUSE 1 (the GY summon); the discard test
is not captured in them, so why clause 2 was inert is still open.

### FIX (round 2 of clause 2)
Discriminator replaced with the measured one: **clause 1 iff `r1 == 0`**, which is
also the safe direction — if the discard path also passes 0, clause 2 is merely
inert and clause 1 still works. Diagnostics widened so a clause-2 sample can
never be overwritten by clause 1's: `[0x20]/[0x24]` and `[0x28]/[0x2C]` count and
capture entries with a NON-ZERO event, and `[0x30]/[0x34]/[0x38]` record
`desc[+4]` (zone), `desc[+5]` (record class) and `desc[+0]` (cid) — the
discriminators `card.lightpulsar_clause1` and `card.darkflare_clause2` use.

**ROM: sha256 `b4f3c405d01e9cda80ee8c9672f79a53adede23b18c5b324a1e9f5a8337a6bad`**,
gates=PASS snoww=PASS grapha=PASS.

New KB fact: `resolver.event_arg_is_zero_on_gy_action` — including the falsified
0x4E hypothesis, so it is never re-derived.

## C2 ROUND 2 IN-GAME (2026-08-27) — clause 1 RESTORED, clause 2 still inert, cause MEASURED AGAIN

User: *"1. Clause 1 is back. 2. Discarding Grapha does not register a prompt or
activate his effect see .ml2 and .ml3 (after any discard effects resolve)"*

So the measured `r1 == 0` discriminator fixed the regression. Clause 2 remained
completely inert.

### THE SAVESTATES MOVED THE PROBLEM
`rom_grapha_test.ml2` / `.ml3`, taken AFTER a discard fully resolved:

```
[00] +04 resolver entries               4        <-- exactly 2 clause-1 activations
[18] +14 declaration entries            2            at 2 phases each (0x80, 0x7E)
[20] +04 entries with event != 0        0        <-- ***NOTHING FROM THE DISCARD***
[08] +04 last phase                     0x7E
[0C] +04 last [0x0229AAFC+0x74]         1
[34] +04 last desc[+5] record class     2
[38] +04 last desc[+0] cid              0x1961
```

**The resolver was never entered on the discard path at all.** So clause 2 was
not being mis-routed by the discriminator — *it was never offered*.

### WHY — `dispatch.cls_slot_roles`, and a trap the KB had already written down
`+0C` slot3 is the **ACTIVATION CONDITION**, and it returns a CODE where
**0 = cannot activate** (1 = activatable if slot2 finds a target, >=2 =
unconditionally); `+10` slot4 is the **COST / activation-procedure** step. Both
are driven by the activation state machine `0x02217F80`.

Grapha's record carried clause 1's answers in both: `+0C` was clause 1's
GY-offer gate — which *correctly* returns 0 for a discard — and `+10` was the
bounce-cost machine. The gate refused the trigger before the resolver could run.

`event.optional_trigger_is_record_shape` names this exactly:

> "⚠️ COMPOSITION TRAP: one cls record cannot be half-optional. A donor carrying
> two clauses of different optionality … must point +0C/+10 at stubs that branch
> on the descriptor, exactly as its resolver already branches on **desc[+3]**."

I had branched `+04`, `+08` and `+14` and left `+0C`/`+10` on clause 1's — which
is the half of the trap the fact spells out. Kahkki and Gren, the templates, use
`+0C = 0x0224A115` (`movs r0,#2`, activatable unconditionally) and `+10 = 0`.

⚠️ Also corrected: the first diagnostic recorded `desc[+4]` and `desc[+5]` as
"zone" and "class". **`desc[+3]` is the ZONE; `desc[+4]` is the INDEX** — which is
why it read 0. The descriptor is `[+0] cid, [+2] side, [+3] zone, [+4] index,
[+5] record class`.

### ROUND 3 (built) — PARTS M and N
| part | what | where |
|---|---|---|
| M | cls2 `+0C` activation-condition dispatcher | `CAVE_GRAPHA_GATE2 0x0239D510`, 68 B |
| N | cls2 `+10` cost dispatcher | `CAVE_GRAPHA_COST2 0x0239D570`, 44 B |
| L2 | slot3/slot4 diagnostics | `CAVE_GRAPHA_DIAG2 0x0239D4D0`, 0x40 B |

cls2 is now `{0x1961, RES2, FILT2, GATE2, COST2, DECL}`. Both new stubs branch on
**`desc[+3] == 0x0B`** (the hand — the zone the discard arm `0x021D185C` itself
gates on): clause 2 gets `2` from `+0C` and no cost from `+10`; **anything else
falls through to clause 1**, so if the trigger descriptor carries a different
zone, clause 2 stays inert and clause 1 — restored this round — is untouched.

`+0C` records the full descriptor on every call, so if the zone test is wrong the
next read names the right value directly (the reader prints an explicit warning
for that case).

**ROM: sha256 `55d9c374b51ce5ece39128b9c883e73dfbd0d69c73004b317c620e002b14db7d`**,
gates=PASS snoww=PASS grapha=PASS.

## C2 ROUND 3 (2026-08-27) — clause 2 still inert; THE DESCRIPTOR IS IDENTICAL ON BOTH PATHS

User: *"Clause 1 works still. clause 2 still doesn't activate see ml2 before and
ml3."* Plus the steer that made the difference: *"I don't think you are doing a
perfect byte for byte implementation of graphas 3ds effect... look at how Silva
and goldd are implemented in the 3ds version."*

### The measurement (rom_grapha_test.ml3, after the discard)
```
[00] +0C activation-condition entries   2
[04] +0C last desc[+3] ZONE             0x0E    <-- the GRAVEYARD, not the hand
[08] +0C last desc[+5] record class     2
[0C] +0C last desc[+0] cid              0x1961
[18] +0C last arg1 (r1)                 0
[28] +0C last clause-1 gate return code 1
[1C] +10 cost entries                   0
     +04 resolver entries               0
```

`+0C` ran, with the **Graveyard** in `desc[+3]` — Grapha is in the GY on the
discard path too, because he has just been discarded there. So:

**`desc[+0]`, `desc[+2]`, `desc[+3]`, `desc[+5]` and `r1` are ALL IDENTICAL on
the two paths.** There is no descriptor- or argument-based discriminator, and
three rounds of looking for one were three rounds wasted.

And the return code explains the rest: `dispatch.cls_slot_roles` says **1 =
"activatable, but slot2 must find a target"**, so the engine asked `+08`, got
clause 1's filter (your Dark World monsters), found nothing destroyable, and
refused. Resolver never ran, `+10` never called.

### ⭐ THE 3DS ANSWER — a slot-by-slot correspondence over 662 shared cids
Following the user's steer produced a reusable asset:
`ygo_tools/tools/threeds_cls2_map.py`, KB fact
`dispatch.threeds_nds_cls2_correspondence`. Sillva and Goldd are in BOTH builds
with the same printed effect, and their rows line up positionally — as do 660
other cids, which makes the mapping checkable rather than assumed:

```
Beiige 0x1965  3DS 0045E090 00000000 00000000 00000000 00000000
               NDS 0220731D 00000000 00000000 00000000 00000000
Sillva 0x1968  3DS 004344AC 00000000 00000000 00000000 00000000
               NDS 0221FA5D 00000000 00000000 00000000 00000000
Goldd  0x1969  3DS 0043464C 003E3E10 00404260 00000000 00476000
               NDS 0221FB51 021DE7C9 0224A115 00000000 0223847D
Kahkki 0x1B3E  3DS 00458888 003DBCA8 00404260 00000000 00477BB8
               NDS 02204899 021D8CE5 0224A115 00000000 02234DA5
GRAPHA 0x25F0  3DS 0045579C 003E3E10 00404260 00000000 00477BB8
               NDS  <own>   021DE7C9 0224A115 00000000 02234DA5
```

**So Grapha's clause-2 record, byte for byte, is
`{0x1961, <resolver>, 0x021DE7C9, 0x0224A115, 0x00000000, 0x02234DA5}`** — with
105 shared cards agreeing on the `+0C` pairing and 16 on `+14`. `+0C` must return
**2** (activatable unconditionally, slot2 NEVER consulted) and `+10` must be
**0**. Mine returned 1 and carried the bounce machine, which is precisely the
failure.

### ⚠️ THE STRUCTURAL BLOCKER, now provable
Clause 1 needs `+0C` = its own gate and `+10` = the bounce-cost machine.
Clause 2 needs `+0C` = 2 and `+10` = 0. The two cannot coexist in one record, and
the measurement above proves the engine gives us nothing to branch on.

**The 3DS does not have this problem because it puts the two clauses in TWO
REGISTRIES**: clause 1 in `summon_cond[185]` (0x006AC2D4) and clause 2 in
`discard_trigger[771]` (0x006C6780). The NDS counterpart of that separation is
the SUMMON-PROCEDURE REGISTRY **0x0228F158** (`handss.summon_procedure_registry`,
which `threeds_lookup` already labels as summon_cond's NDS equivalent) — the same
table card.lightpulsar_clause1 and card.darkflare_clause1 use for their
alternative summons.

## C2 Next Experiment / decision
Three options, in order of faithfulness:

1. **Re-home clause 1 onto the summon-procedure registry 0x0228F158**, mirroring
   the 3DS split, and give cls2 the byte-for-byte clause-2 record above. Most
   faithful and dissolves the conflict permanently -- but it rebuilds a clause
   that is currently in-game confirmed.
2. **Find a NON-descriptor discriminator: the CALLER.** The clause-1 offer path
   reaches slot3 through the GY-action check 0x0224C590 -> 0x021EC740, while the
   trigger path goes through 0x0224AD94 (whose callers are the event-posting
   range 0x021D333E / 0x021D33A4 / 0x021D3F36). Different wrappers means a
   different **LR** in the stub. Cheap to measure (record LR in +0C) but it is
   another duel, and keying a shipped card on a return address is fragile.
3. **Ship clause 1 alone** and leave clause 2 here, fully mapped.

## C2 ROUND 4 (2026-08-27) — option 1 was NOT BUILDABLE; the caller is the discriminator

### ⚠️ OPTION 1'S PRECONDITION IS FALSE — checked before building
Re-homing clause 1 onto the summon-procedure registry `0x0228F158` (the NDS
counterpart of the 3DS `summon_cond`) cannot be done: **no Graveyard self-Special-
Summon is in that table.** Dumped all 133 rows — Zephyros `0x241C`,
Plaguespreader `0x1EA9` and Glow-Up Bulb `0x2387` are all ABSENT, and so is the
hand-SS Genex Ally Birdman `0x2205`. Its handler family is the banish-cost
payment machine (`0x0226292D` x32, `0x02261F8D` x38 = "no special procedure").
`0x0228F158` is **hand-SS only**; the NDS routes every GY self-summon through the
GY-action registry + cls2, which is what clause 1 already does. There is no
second home to move it to.

### THE ACTUAL DISCRIMINATOR: LR, pinned statically
The trigger path reaches slot3 through `0x0224AD94`:

```
0x0224AE06  ldr r2,[r4,#0xC]     ; slot3
0x0224AE10  blx r2               ; <-- LR == 0x0224AE13 on this path
0x0224AE14  cmp r6,#1
0x0224AE16  bne skip             ; slot2 consulted ONLY if slot3 returned exactly 1
```

Clause 1's offer instead comes via the GY-action check `0x0224C590` ->
`0x021EC740`. So **`+0C` can see which clause is resolving even though the
descriptor cannot** — and `dispatch.threeds_nds_cls2_correspondence` independently
says the trigger path must be told `2` (3DS `0x00404260` -> NDS `0x0224A115`,
105 cards), which is exactly what stops slot2 being consulted with the wrong
filter.

### THE LATCH — what makes `+08` solvable at all
`+0C` is the ONLY slot that can distinguish, so it writes
`CAVE_GRAPHA_LATCH 0x0239D5B0` (1 = the Graveyard summon, 2 = the discard
trigger) and every other slot reads it. The filter is called as
`(src_desc, cand_side, cand_zone)` and could never have worked it out alone.

| slot | clause 1 | clause 2 |
|---|---|---|
| `+04` | `CAVE_GRAPHA_RES` (untouched) | `0x02204899` Kahkki/Gren destroy |
| `+08` | `CAVE_GRAPHA_FILT` (untouched) | `0x021DE7C9` Goldd, opponent's cards |
| `+0C` | `CAVE_GRAPHA_GATE` (untouched) | `2` = activatable unconditionally |
| `+10` | `0x021EB1B1` bounce cost | `0` = no cost |
| `+14` | `1` = skip | `0x02234DA5` Kahkki/Gren picker |

Every clause-2 column is the 3DS row translated through
`ygo_tools/tools/threeds_cls2_map.py`; every clause-1 column is the
in-game-confirmed stub, byte-identical.

**ROM: sha256 `1729f48c3aac2e2d817866f26622b3df2ad967e8adf660a4c8a237c116b38f12`**,
gates=PASS snoww=PASS grapha=PASS.

## C2 ROUND 4 IN-GAME — CLAUSE 2 FIRES. Hang traced to the slot4 RETURN VALUE.

User: *"When grapha is discarded, he activates and then the game hangs... I cannot
select anything to destroy"*.

**The latch design works.** Savestate `rom_grapha_test.ml3`:

```
[08] +0C last LR (caller)                    0x0224AE13   <-- the discriminator fired
[10] +0C CLAUSE-2 entries (LR match)         1
[1C] +10 cost entries                        0x1937 = 6455   <-- THE HANG
[20] +10 last LATCH                          2
[00] +04 resolver entries                    0
[18] +14 declaration entries                 0
```

`+0C` saw `LR == 0x0224AE13`, correctly identified the discard path, and latched
clause 2. The trigger then activated — which is the first time clause 2 has ever
run. The hang is downstream: **slot4 was entered 6,455 times.**

### ⚠️ AN ABSENT SLOT4 IS NOT THE SAME AS A SLOT4 THAT RETURNS 0
The wrapper that drives slot4 is `0x0224AE50`:

```
0x0224AE5E  ldr r2,[r0,#0x10]   ; slot4
0x0224AE60  cmp r2,#0 ; beq 0x0224AE6C     ; absent
0x0224AE68  blx r2
0x0224AE6C  movs r0,#1 ; pop               ; <-- ABSENT YIELDS 1
```

So "there is no cost step" is reported as **1**. Kahkki and Gren have slot4
absent, which is why they work; the most common native slot4 tag `0x021E51E4`
also returns 1 on its early-out. My stub returned **0**, which the activation
state machine reads as "cost not paid, call again" — hence the spin.

**FIX: clause 2's `+10` returns 1.** One value.

**ROM: sha256 `6856bb94c35a52086158703bb1fcc554f236ef8a7533c71a65e25acbc4d0176d`**,
gates=PASS snoww=PASS grapha=PASS.

⚠️ The previous ROM (`1729f48c...`) HANGS on a Grapha discard — do not keep it.

## C2 ROUND 5 IN-GAME — ⭐ CLAUSE 2 WORKS. Clause 1 broken by a STICKY latch.

User: *"1. He does activate and I can target a card and destroy. 2. Clause 1 does
not work anymore. I can activate grapha from GY but I think it is trying to invoke
clause 2 and not clause 1. As when I activated it I could destroy another card."*

**CLAUSE 2 IS FUNCTIONALLY COMPLETE**: it triggers on an effect discard, prompts
for a target on the opponent's field, and destroys it. That is the printed base
half of the clause. (NOT written up as confirmed-and-shipped: clause 1 regressed
in the same build, so the card as a whole is not done.)

### The latch was write-once, and the savestate says why
`rom_grapha_test.ml3`:

```
[00] +0C activation-condition entries        15
[10] +0C CLAUSE-2 entries (LR == 0x0224AE13) 15   <-- ALL of them
[28] +0C clause-1 gate return code            0   <-- the clause-1 branch NEVER RAN
[34] +04 last LATCH                           2
[14] +08 last LATCH                           2
[20] +10 last LATCH                           2
```

**Every single `+0C` call carried the trigger LR, and gate2_stub's clause-1
branch has never executed — so CLAUSE 1'S ACTIVATION DOES NOT CALL slot3 AT
ALL.** Nothing ever wrote the latch back to 1, so after the first discard it was
permanently 2 and every later Graveyard activation ran the destroy.

That also corrects an assumption baked into round 4: `+0C` is not a place both
clauses pass through. It is a clause-2-only slot.

### FIX — the latch is CONSUME-ONCE
Clause 2's resolver writes the latch back to `LATCH_CLAUSE1` immediately after the
destroy, so it reads 2 only inside the window between `gate2_stub` and `res2_stub`.
Clause 1, which touches neither, always sees the default 1.

`+04` and `+10` now also record their LR, because if the latch ever goes stale
again the robust fix is to key EACH slot on its own caller rather than on a
shared word — and that needs clause 1's LRs, which nothing has captured yet.

**ROM: sha256 `3b7853e88b4e2ffc261b83ac12489ad292df86f763c0182416de1717cf705faa`**,
gates=PASS snoww=PASS grapha=PASS.

⚠️ RESIDUAL RISK, stated plainly: if clause 2 ever activates and then aborts
before its resolver runs (e.g. no legal target), the latch stays 2 until the next
clause-2 resolution. The LR capture is there to make the permanent fix possible
in one more pass.

## C2 ROUND 6 — ⭐ THE DISCRIMINATOR, FOUND BY DECODING THE EVENT-POST PRIMITIVE

Round 5 in-game: *"Grapha still destroys..."* — the consume-once latch did not
help, and three savestates showed why:

```
+04 entries        1 -> 2 -> 3      +04 CLAUSE-2 entries 1 -> 2 -> 3   (ALL clause 2)
+04 last LR        0x0224AF03       (one call site, identical for both clauses)
+0C entries        7 -> 12 -> 19    ALL matching LR 0x0224AE13
```

`+0C` is POLLED — 19 calls for 3 activations — so any latch it writes is re-armed
before the next activation. Consume-once cannot survive that.

### THE ACTUAL DECODE — `0x021D32A0` unpacks the posted event word
```
strh r5,[r0]                                     desc[+0] = event & 0xFFFF (cid)
movs r1,#0x1F ; lsls r1,#0x10 ; ands r1,r5
lsrs r1,#0x10 ; strb r1,[r0,#3]                  desc[+3] = (event >> 16) & 0x1F
movs r1,#0xE  ; lsls r1,#0x14 ; ands r1,r5
lsrs r1,#0x15 ; strb r1,[r0,#5]                  desc[+5] = (event >> 21) & 0x07
```

*** ON AN EVENT-POSTED DESCRIPTOR, `desc[+3]` AND `desc[+5]` ARE NOT A ZONE AND A
RECORD CLASS -- THEY ARE THE EVENT CODE, SPLIT (bits 0..4 and 5..7). ***

Three rounds read `desc[+3] == 0x0E` as "the Graveyard" and built discriminators
on it. It is the low half of code **0x4E** -- the GY-action registry's own
post_fn `0x0224C6EE`, i.e. CLAUSE 1. So `LR == 0x0224AE13` was matching clause 1
all along: the gate latched clause 2 for the Graveyard summon, and Grapha
destroyed instead of summoning. Clause 2 "worked" only because both paths ran the
destroy.

The event-post primitive has exactly four call sites, codes `0x01` / `0x4B` /
`0x1F` / `0x4E`, whose low five bits are `0x01` / `0x0B` / `0x1F` / `0x0E` —
**all distinct**. So:

> **`desc[+3] == 0x0E`  <=>  event 0x4E  <=>  CLAUSE 1 (the Graveyard summon)**

a one-byte test available from `r0` in EVERY slot — including the filter, which
receives no event and defeated every previous attempt. The latch, the LR test and
the zone test are all gone.

**ROM: sha256 `2a9e3b8129dd31ab178c51ca28b5aece3cb5e2ca04e01bd7b8a6c8b7db84b25b`**,
gates=PASS snoww=PASS grapha=PASS.

## C2 ROUND 6 IN-GAME — clause 1 BACK, clause 2 inert: the test was HALF right

User: *"Clause 1 is back, Clause 2 doesnt activate anymore."*

So `desc[+3] == 0x0E` does identify clause 1 correctly — that half is confirmed
in-game. But the discard trigger was ALSO matching it and being sent into clause
1's gate, which refuses it (the round-2 failure mode again).

### WHY — two of the four post sites build their code AT RUNTIME
Re-read of the post sites, which my first pass had summarised as four fixed
codes. Only two are fixed:

| site | code | desc[+5] | desc[+3] |
|---|---|---|---|
| `0x0224B120` | `[sp+0xC] << 21`, **dynamic** | dynamic | dynamic |
| `0x0224B1BE` | `movs r1,#0x4B`, fixed | 2 | 0x0B |
| `0x0224B31C` | `[r6+4] & 0x1F`, **dynamic, MASKED TO 5 BITS** | **always 0** | dynamic |
| `0x0224C6EE` | `movs r0,#0x4E`, fixed — the GY-action post | **2** | **0x0E** |

A `desc[+3]`-only test therefore also matches a DYNAMIC post whose low five bits
happen to be `0x0E` — and site `0x0224B31C` masks with `0x1F`, so its `desc[+5]`
is always **0** where clause 1's is **2**.

### FIX — require BOTH halves
Every dispatcher now tests `desc[+3] == 0x0E` **and** `desc[+5] == 2`, which only
the fixed `0x4E` post satisfies. Clause 1 keeps the routing that was just
confirmed working; a dynamic post sharing the low five bits now falls to clause 2
on the `desc[+5]` check.

**ROM: sha256 `69678e81e920a99f413d9d1d0d2fff8506198e7746cb5113ee859e0e5acefaa5`**,
gates=PASS snoww=PASS grapha=PASS.

⚠️ IF THIS STILL LEAVES CLAUSE 2 INERT, the diagnostic now records both halves at
every slot (`+0C` [04]/[08], `+04` [3C]/[34], `+08` [14], `+10` [20], `+14` [1C]),
so ONE savestate taken after a discard names the discard's actual event code and
ends the guessing.

## ⚠️ C2 ROUND 7 — THE DISCARD TRIGGER HAS NEVER FIRED. Round 5 was a misread.

User: *".ml3 Immediately after the discard resolves, grapha didnt activate"*.

```
[00] +0C activation-condition entries   3
[04] +0C last desc[+3] (code low5)      0x0E     <-- CLAUSE 1's code
[08] +0C last desc[+5] (code high3)     2        <-- CLAUSE 1's code
[00] +04 resolver entries               0        <-- resolver NEVER ran
[18] +14 declaration entries            0
[10] +08 filter entries                 0x2C, all code 0x0E
```

**Every descriptor any slot has ever seen carries event code 0x4E**, the
GY-action post. Those three `+0C` calls are the Graveyard OFFER being polled --
Grapha is in the GY once discarded, so the offer is live. Nothing with any other
code has ever arrived at the record.

### THIS RE-INTERPRETS ROUND 5
Round 5's *"He does activate and I can target a card and destroy"* was almost
certainly NOT clause 2. It was the GRAVEYARD OFFER appearing after the discard,
which the round-5 gate answered with clause 2's destroy (it treated code 0x4E as
clause 2). That also explains round 5's other half -- *"Clause 1 does not work
anymore... I could destroy another card"* -- as the SAME event, seen twice.

**So the discard trigger has not fired in any round.** The three "clause 2
discriminator" rounds were all solving a problem that did not exist: there was
never a second path to distinguish.

### WHAT IS ACTUALLY UNKNOWN
PART H is proven only STATICALLY: `verify()` walks the 0x021D1392 chain and shows
`0x1961 -> 0x021D185C`, with Ojamagic/Kahkki/Goldd/Beiige unchanged. But reaching
the arm only sets `[sp+0x14] = 1` inside 0x021D1300; something downstream turns
that flag into a posted event, and for this cid it evidently does not.

Candidate causes, none yet tested:
1. The arm's other two gates fail: `[sp+0x18] != 0` (effect discard) and
   `[sp+0x10] > 0`. Snoww passes both with the same hook, so this would be a
   per-cid difference.
2. The post is made but keyed to a record shape this cid does not have --
   `event.optional_trigger_is_record_shape` shows +0C/+10 turn a record into an
   "activation procedure" card, and Snoww's record was the bare
   `{+04, 0, 0, 0, 0}` Sangan shape when its trigger first fired.
3. The donor needs a leave-mask / list membership row that Snoww's donor has
   natively and Zure does not.

### NEXT EXPERIMENT (do this before writing any more dispatcher code)
**Instrument PART H's ov3 arm stub to count arrivals.** It is the one place that
proves whether the discard reaches the arm AT ALL. Needs ~12 B: a counter word
plus an increment, and 74 B of ov3 dead space remain (0x021B58D0 has 12 B free,
0x021B5AAA has 10 B). A normal-duel-only ov5 counter is NOT acceptable here --
this stub is on a shared path that runs in puzzles.

If the counter stays 0, PART H is the bug and no amount of dispatcher work helps.
If it counts up, the arm is reached and the failure is downstream in the posting,
which is where option 2 above gets tested by giving the donor the Sangan record
shape temporarily.

### CURRENT ROM IS A SAFE STOPPING POINT
`69678e81e920a99f413d9d1d0d2fff8506198e7746cb5113ee859e0e5acefaa5` --
clause 1 works (in-game confirmed on 2a9e3b81 and the tightened test only
NARROWS what matches clause 1, which the measurement above shows it still does),
and clause 2 is inert and harmless because nothing ever routes to it.


# ===========================================================================
# C2 ROUND 8 (2026-08-28) -- ROUND 7'S CONCLUSION IS REFUTED.
# The discard post and clause 1's post are BYTE-IDENTICAL on the two fields
# the diagnostic recorded.  desc[+4] is the discriminator, and it is FREE.
# ===========================================================================

## ⭐ THE FINDING: both paths post event code 0x4E

Round 7 read `desc[+3] = 0x0E, desc[+5] = 2` on all three `+0C` calls and
concluded *"no descriptor with any code other than 0x4E has ever reached the
record, therefore the discard never fired"*.  **That inference does not hold.**
The discard path posts `0x4E` **too** -- it is not a clause-1 fingerprint.

Proven this session by disassembling the whole of `0x021D1300` (the relocation
applier that hosts PART H's switch) down to its posting site.

### The applier's prologue decodes its packed word (`0x021D1300`..`0x021D1392`)

`r1` = a pointer; `w = [r1]`:

```
[sp+0x04] = r0 (arg0)                        [sp+0x08] = r1     [sp+0x0C] = r2
[sp+0x10] = r3 (arg3)                        [sp+0x14] = 0      <- THE RESULT FLAG
[sp+0x38] = w & 0x1FF                 INST   r7 = (w >> 9) & 1        SIDE
[sp+0x34] = (w >> 14) & 0xF           SRC ZONE  (the arm tests == 0x0B)
[sp+0x30] = (w >> 19) & 0xF           KIND
[sp+0x18] = (arg0 == 0x1F) ? 1 : 0
r5 = table[INST] & 0x3FFF             CID   (what the per-cid switch keys on)
```

and the switch is **gated on KIND**:

```
021D1388  LDR R0,[SP,#0x30] ; CMP R0,#0x0E
021D138C  BEQ 0x021D1392        ; -> the per-cid switch PART H hooks
021D138E  BL  0x021D1B98        ; a LONG BRANCH past it (b is out of range)
```

### The arm sets a flag; the flag gates ONE post site

`0x021D185C` accept -> `0x021D199E MOV R0,#1` -> `0x021D19BE STR R0,[SP,#0x14]`.
Every arm converges on the same tail, and the flag is consumed exactly once:

```
021D1D56  LDR  R0,[SP,#0x14] ; CMP R0,#0 ; BEQ 0x021D1D96   ; 0 -> just return
          ... build the event word ...
021D1D92  BL   0x021D3168                                   ; THE POST
021D1D96  ADD  SP,#0x3C ; POP {R4-R7,PC}
```

The word it builds (transcribed instruction by instruction from
`0x021D1D5C`..`0x021D1D92`):

```
event =  (cid & 0xFFFF)
      |  ((KIND & 0x1F) << 16)          ; [sp+0x30]
      |  (1 << 22)                      ; HARDCODED, always set
      |  ((arg0 & 0x3F) << 25)          ; [sp+0x04]
      |  (side << 31)
```

### `0x021D3168` is the register-prim, and it unpacks the SAME way

`0x021D3168(event, inst, w)` zero-fills a 0x24-byte descriptor with
`0x0209A080(ptr,len)` -- **proven a memset-to-zero**, `0209A08A MOVS R2,#0 ;
STRB R2,[R3] ; ...` -- then:

```
desc[+0] = event & 0xFFFF          desc[+2] = event >> 31
desc[+3] = (event >> 16) & 0x1F    desc[+4] = (event >> 25) & 0x3F
desc[+5] = (event >> 21) & 0x07    desc[+6] = (event >> 24) & 1
desc[+C] = inst
... then COMMIT via 0x021EDA08 (the same commit Doppel's offer uses)
```

So on the discard path:

| field | value | why |
|---|---|---|
| `desc[+3]` | **0x0E** | KIND, and KIND==0x0E is REQUIRED to reach the switch at all |
| `desc[+5]` | **2** | bit 22 is hardcoded set; bits 21/23 are always clear |
| `desc[+4]` | **0x1F** | arg0, and the arm's `[sp+0x18] != 0` gate means arg0 == 0x1F exactly |

`0x0E | (2 << 5)` = **`0x4E`** -- the identical event code clause 1 posts.

### ⭐ desc[+4] IS THE DISCRIMINATOR, AND IT IS FREE

Clause 1's post `0x0224C6EE` builds `event = cid | 0x004E0000 | (side << 31)`
(bits 25..30 are all zero) and calls **`0x021D32A0`**, which is a near-twin of
`0x021D3168` -- same zero-fill, same `+0`/`+2`/`+3`/`+5`/`+6` stores -- except
that it **never writes `[+4]` at all** (it writes `+0xE` instead).  The
zero-fill therefore leaves it 0.

```
clause 1 (GY-action offer, 0x0224C6EE -> 0x021D32A0):  desc[+4] = 0x00
clause 2 (discard trigger, 0x021D1D92 -> 0x021D3168):  desc[+4] = 0x1F
```

Nothing else in the current design reads `desc[+4]`.

### WHAT THIS MEANS FOR THE BUILD ON DISK

PART M's `+0C` gate is `if desc[+3]==0x0E && desc[+5]==2 -> clause 1, else
clause 2`.  The discard post satisfies **both** halves, so a discard that
arrived was handed to **clause 1's** activation-condition gate and clause 2 was
never selected.  That is a complete and sufficient explanation of round 7
(`+04 resolver entries = 0`) **without PART H being broken at all**.

⚠️ The round-7 counter experiment (instrument PART H's arm) is therefore **no
longer the right next step** -- it was designed to answer a question that rested
on the refuted inference.  It is still a valid fallback if round 8 fails.

## Ruled Out (round 8)

7. **"The discard trigger has never fired" (round 7's headline).** NOT
   established.  The evidence for it was `desc[+3]==0x0E && desc[+5]==2` on every
   descriptor, which this session proves is exactly what the discard path posts
   too.  Status returns to UNKNOWN, and round 8's diagnostic settles it.
8. **`desc[+3]`/`desc[+5]` in ANY combination as a clause-1/clause-2
   discriminator.** Both paths produce the same `(0x0E, 2)`.  Round 6's "require
   both halves" fix cannot work, and neither can any refinement of it.

## Next Experiment (round 8)

Switch the discriminator to `desc[+4]` and record `desc[+4]` in the diagnostic
at the same time, so ONE duel is conclusive either way:

* clause 2 fires  -> done.
* clause 2 does not fire, but the diag shows a `desc[+4] == 0x1F` descriptor
  reached `+0C` -> the post happens and the failure is downstream (record shape).
* clause 2 does not fire and NO `desc[+4] == 0x1F` descriptor ever arrived ->
  round 7's conclusion was right after all for a different reason, and PART H's
  arrival counter becomes the next measurement.

## C2 ROUND 8 -- BUILT 2026-08-28, `verify()`-green, AWAITING IN-GAME TEST

**ROM:** `data/over_the_nexus/working/rom_grapha_test.nds`, 129518216 B, sha256
`19bacea3c63c3658ee077e65ff995bdf23bd6d7d95c5fac3b939f4afe9df9a33`
(round 7 was `69678e81...`).  `gates=PASS  snoww=PASS  grapha=PASS`, all three
against that same file.  Guards on the way in and out:
`check_allocations` -> `[OK] no ov5 overlaps, no phantom double-claims, no ov3
overlaps, ledger in sync`; `verify_knowledge` -> `TOTAL 340 facts: 307 PASS
0 FAIL 33 UNVERIFIED` (339/306 before -- the one new fact is
`event.discard_trigger_posts_the_same_0x4E`, and it passes its own proof).

**No new slots were claimed.**  Every stub grew inside its existing reservation,
so the ledger is byte-for-byte unchanged:

| stub | slot | before | after | reserve |
|---|---|---|---|---|
| I  decl  (+14) | `CAVE_GRAPHA_DECL`  | 56 | **64** | 64 |
| J  res2  (+04) | `CAVE_GRAPHA_RES2`  | 76 | **84** | 96 |
| K  filt2 (+08) | `CAVE_GRAPHA_FILT2` | 68 | **76** | 80 |
| M  gate2 (+0C) | `CAVE_GRAPHA_GATE2` | 64 | **76** | 96 |
| N  cost2 (+10) | `CAVE_GRAPHA_COST2` | 52 | **60** | 64 |

⚠️ `decl` is now at **64 of 64** -- the next thing added to it needs a bigger
reservation, and `CAVE_GRAPHA_RES2` sits immediately after it at `0x0239D420`.
The dead `CAVE_GRAPHA_LATCH` (`0x0239D5B0`, 0x10 B) is still reserved and still
unused.

### What changed

1. **One shared emitter, `_clause2_test(reg, yes, no)`**, replaces five
   hand-written copies of the test -- they can no longer drift apart, which is
   how round 6 shipped with `+08` testing something different from `+0C`.
2. **The test is now `desc[+4] == 0x1F && desc[+3] == 0x0E && desc[+5] == 2`.**
   Only `desc[+4]` actually separates the paths; the other two are kept so an
   unrelated event whose `arg0` happens to be 0x1F cannot be mistaken for the
   trigger.
3. ⚠️ **THE POLARITY IS INVERTED FROM EVERY PREVIOUS ROUND.** Clause 1 is now the
   FALL-THROUGH and clause 2 the positively-identified branch. Before this, an
   unrecognised descriptor went to *clause 2*; now it goes to clause 1, the
   in-game-confirmed clause. `decl` (+14) was restructured so its clause-1 arm
   (`skip`, return 1 = declare nothing) is the fall-through.
4. **Every slot now records `desc[+4]` instead of `desc[+3]`** in its diagnostic
   word -- `desc[+3]` is 0x0E on both paths and tells us nothing.
5. **`+0C` gained a `desc[+4]` OR-ACCUMULATOR** at `CAVE_GRAPHA_DIAG2+0x0C`
   (previously unused). It ORs together every `desc[+4]` the activation-condition
   slot is ever handed, so it cannot be overwritten by a later poll the way a
   "last value" field can -- and a single 0x1F in it proves the discard
   descriptor reached the record.
6. `grapha_diag.py` relabelled to match, plus a decision table it prints itself.

### The one duel this needs, and what each outcome means

Discard Grapha with Gates' clause 2, take a savestate immediately, run
`.venv-1/Scripts/python.exe -m ygo_tools.tools.grapha_diag <savestate>`.

| `[0C] +0C desc[+4] OR-ACCUMULATOR` | meaning | next |
|---|---|---|
| carries **0x1F** | the discard descriptor DOES reach the record; PART H and dispatch both work | if clause 2 still did not fire, the failure is downstream -- test the record SHAPE (`event.optional_trigger_is_record_shape`), strip `+08/+0C/+10/+14` to the bare Sangan `{+04, 0, 0, 0, 0}` |
| **0** | no discard descriptor has ever reached `+0C`; round 7's conclusion stands after all | instrument PART H's ov3 arm with an arrival counter (12 B free at `0x021B58D0`, 10 B at `0x021B5AAA`) -- ⚠️ ov3 ONLY, that stub runs in puzzles |
| every counter 0 | the duel never exercised the card | re-test |

⚠️ **STATUS: AWAITING IN-GAME TEST.** Nothing about clause 2 is confirmed. Clause
1 remains `in-game confirmed by user 2026-08-27` and this round only NARROWS what
routes away from it, but that has to be re-checked in the same duel (C3).

## ⭐ C2 ROUND 8 IN-GAME (2026-08-28) — CLAUSE 2 WORKS. IN-GAME CONFIRMED BY THE USER.

User, verbatim, answering the three numbered asks of the round-8 test:

> "1. Works
>  2. No Regressions
>  3. No need, proceed to clause 3"

and then, offering the savestate: *"Well .ml3 is a savestate"*.

**Interpretation, stated back and then CORROBORATED MECHANICALLY rather than
taken on prose** — `data/over_the_nexus/working/rom_grapha_test.ml3`
(2026-08-28 09:24, taken on the round-8 ROM `19bacea3...`):

```
[0C] +0C desc[+4] OR-ACCUMULATOR              0x0000001F   <-- carries the discard mark
[10] +0C CLAUSE-2 entries (desc[+4] == 0x1F)  0x00000001
[20] +04 CLAUSE-2 entries (the destroy ran)   0x00000001
[28] +14 CLAUSE-2 entries (target declared)   0x00000002
[00] +04 resolver entries                     0x00000003   (round 7: 0)
[28] +0C last clause-1 gate return code       0x00000001
[00] +0C activation-condition entries         0x00000009
[10] +08 filter entries                       0x0000010C
```

This is the first round in which anything with `desc[+4] == 0x1F` has ever been
seen, and it is decisive on the question rounds 3-7 could not answer:

* **The discard descriptor DOES reach the cls2 record.** PART H's switch hook,
  the Dark World arm, the post at `0x021D1D92` and the cls2 dispatch all work.
  They always did -- rounds 3-7 were mis-routing the descriptor, not missing it.
* **The round-5 illusion is ruled out MECHANICALLY, not by prose.** `+0C
  CLAUSE-2 entries == 1` means the activation-condition slot positively
  identified a discard descriptor exactly once, and `+04 CLAUSE-2 entries == 1`
  means the destroy resolver ran off that identification. A Graveyard offer
  answered with clause 2's destroy -- round 5's failure -- would have shown
  `desc[+4] == 0` and could not have incremented either counter.
* **Clause 1 is not regressed**: its gate still returns 1, and the `+04`/`+08`/
  `+14` "last desc[+4]" fields all read 0x00, i.e. the GY offer is still being
  polled and still routed to clause 1's arm. (This is also exactly why the
  OR-accumulator was needed: every "last value" field was overwritten by a later
  clause-1 poll. A last-value-only diagnostic would have read as a total failure.)

**STATUS: CLAUSE 2 — in-game confirmed by user 2026-08-28.** Clause 1 remains
in-game confirmed (2026-08-27, and retested clean on the combined ROM
2026-08-28). Clause 3 is not implemented.

### Open observation, NOT explained
`+14 CLAUSE-2 entries == 2` while `+04 CLAUSE-2 entries == 1` -- the target
declaration ran twice on clause 2's arm for one destroy. The likely reading is
the ordinary enumerate-then-commit protocol of the `+14` slot, but that is a
GUESS and has not been measured. Behaviour was correct in-game, so it is not
being chased; it is recorded here in case a later clause trips over it.

### Superseded
The round-8 "what each outcome means" decision table is now resolved to its
first row. The **PART H arrival counter is no longer needed** and should not be
built -- the accumulator answered the same question for free, and PART H is
proven good by the 0x1F itself.


# ===========================================================================
# CLAUSE 3 — "look at 1 random card in your opponent's hand, then, if it was a
# monster, you can Special Summon it to your side of the field"
# session 2026-08-28, RECON ONLY. NO ROM CODE WRITTEN.
# ===========================================================================

Printed text (`scratch/ygoprodeck_cache.json` id 34230233), the tail of the
discard trigger:

> ... destroy that target, **then, if this card was discarded from your hand to
> your Graveyard by an opponent's card effect, look at 1 random card in your
> opponent's hand, then, if it was a monster, you can Special Summon it to your
> side of the field.**

Three sequential sub-steps, and they are NOT equally hard:

| step | text | status |
|---|---|---|
| **C3a** | condition: discarded **from your hand** AND **by an OPPONENT's card effect** | half free, half OPEN |
| **C3b** | look at 1 **random** card in your opponent's hand | ⭐ NATIVE PRIMITIVE FOUND |
| **C3c** | if it was a monster, **you can** Special Summon it to YOUR field | strong lead, not proven |

## C3 Confirmed (this session)

### C3a is HALF FREE: "from your hand" is already guaranteed
The Dark World effect-discard arm `0x021D185C` that PART H routes the donor into
opens `LDR R0,[SP,#0x34] ; CMP R0,#0x0B ; BNE reject` — **source zone 0x0B is the
HAND**. Clause 2 therefore cannot fire on a discard from anywhere else, and
"discarded from your hand" needs no new code at all.

### ⚠️ C3a's OTHER HALF IS THE ONE REAL OPEN PROBLEM
"by an **opponent's** card effect" needs the ACTING side compared against the
card's own side. Inside `0x021D1300` both are live — `r7 = (w >> 9) & 1` and
`r4 = INST & 1` — and several sibling arms literally test `CMP R4,R7` (e.g.
`0x021D1884`, `0x021D18AC`, both requiring SAME side). **But the event word built
at `0x021D1D5C` encodes only ONE of them** (bit 31 <- `r4`, which becomes
`desc[+2]`); `r7` is not in the word, and the remaining bits are cid / KIND /
`arg0` / the hardcoded bit 22. So **the acting side does not survive into the
descriptor the resolver receives**, and C3a cannot be decided at resolution time
from `desc` alone.

⚠️ UNVERIFIED: which of `r4`/`r7` is the controller and which is the actor. The
`CMP R4,R7` arms prove only that the two are compared, not their roles.

### ⭐ C3b: THE NDS SHIPS "LOOK AT 1 RANDOM CARD IN YOUR OPPONENT'S HAND"
Found by joining `ygoprodeck_cache.json` to the ROM's own cid space
(`konami_id_to_card_name.tsv` — ⚠️ **it is SPACE-aligned, not tab-separated,
despite the extension**; a naive `split('\t')` parses ZERO rows and silently
reports "no such card exists", which it did here before the join was validated
against Zure/Goldd).

| cid | card | printed text | record |
|---|---|---|---|
| `0x1EED` | Omega Goggles | "Once per turn, you can **look at 1 random card in your opponent's hand**" | cls3[460] |
| `0x1367` | Inspection | "**randomly select 1 card in your opponent's hand**" and look at it | cls1[132] |
| `0x1A9D` | Royal Writ of Taxation | "**Select 1 random card from your opponent's hand and look at it**" | cls0[741] |

**Omega Goggles and Inspection share the SAME `+04` resolver `0x0220F755`** — two
different cards in two different cls tables whose only common printed text is the
random hand-peek. That shared-ness is the evidence the handler is card-agnostic
for this behaviour (cf. `grep-the-template-cards-text-too`: a reused handler CAN
hard-code its own card's clauses, but not one shared by two cards that agree on
nothing else).

Disassembled `0x0220F754` — a standard two-phase resolver on `[0x0229AAFC+0x70]`:

```
0220F756  LDR R1,[pc] ; LDR R1,[R1,#0x70] ; CMP R1,#0x7F ; BEQ 0x0220F788
0220F75E  CMP R1,#0x80 ; BNE return-0
phase 0x80:
0220F762  LDRB R0,[R0,#2]      ; desc[+2] = the side
0220F764  MOVS R1,#1 ; SUBS R0,R1,R0 ; ANDS R2,R1     ; r2 = (1 - side) = THE OPPONENT
0220F76C  ... index the opponent's player struct, load a count
0220F776  CMP R1,#0 ; BEQ -> MOVS R0,#0 ; POP          ; EMPTY OPPONENT HAND -> do nothing
0220F780  BL 0x022599F8 ; MOVS R0,#0x7F ; POP          ; the peek action, then phase 0x7F
phase 0x7F:
0220F788  LDRB R0,[R0,#2] ; ... (1 - side) again ; + 0x124 ; index by a u16
0220F7A8  unpack the card word ; BL 0x021D2598 ; return 0
```

The `(1 - side)` opponent computation and the **empty-hand guard** mirror the
3DS's own C3 arm exactly (see below), which is independent corroboration that
this is the right primitive.

### C3c: strong lead, NOT proven — Conscription `0x192F`
No NDS card Special Summons from the **opponent's hand**. The closest, and
structurally the same shape, is **Conscription `0x192F`, cls0[644], `+04`
`0x0221F1F5`**: *"Excavate the top card of your opponent's Deck, and if it is a
monster that can be Normal Summoned/Set, **Special Summon it to your field**."*
That is C3c's "if it was a monster, Special Summon it to your side of the field"
with a different SOURCE ZONE (opponent's Deck rather than opponent's hand).
⚠️ UNVERIFIED whether its summon primitive takes the source zone as an argument or
hard-codes the Deck — that is the experiment that decides whether C3c is a
retarget or new machinery.

### The 3DS's own C3 gate, RE-VERIFIED THIS SESSION
`0x0045579C` is a six-arm phase machine over 0x7B..0x80
(`ldr r1,[r0,#0xBB4] ; sub r1,r1,#0x7B ; cmp r1,#6 ; ldrlo pc,[pc,r1,lsl #2]`),
jump table at `0x004557C8`. The **phase 0x7F** arm `0x004557F0` is C3's gate:

```
00455800  LDR R1,[R4,#0x30]                  ; the descriptor's FLAGS word
00455804  LDRH R0,[R4,#2]                    ; the side
00455808  LSL R2,R1,#0xC  ; CMP R0,R2,LSR#31 ; BEQ bail   ; flags BIT 19 must != side
00455814  LSL R1,R1,#0x16 ; CMP R0,R1,LSR#31 ; BNE bail   ; flags BIT 9  must == side
00455820  RSB R1,R0,#1 ; AND R1,R1,#1                     ; = the OPPONENT
0045582C  ... index that player, LDR R0,[R0,#0xC] ; CMP R0,#0 ; MOVNE R0,#0x7E
```

Bit positions **19** and **9** are pinned this session (the inherited note gave
the mechanism but not the offsets). The trailing `[+0xC] != 0` on the opponent's
struct is the same empty-hand guard the NDS primitive has.

⚠️ **This does NOT hand us C3a.** The 3DS keeps both facts in a flags word at
`[desc+0x30]`; the NDS descriptor is 0x24 bytes and its event word demonstrably
carries no actor side. The 3DS confirms *what* to test, not *where* to read it.

## C3 Open Questions

1. **Where does the ACTING side live at resolution time on the NDS?** Nothing
   found yet. Options not yet evaluated: stash it from PART H's ov3 arm (which
   runs exactly once per discard, unlike `+0C` which is polled — the reason the
   round-4 latch failed does NOT apply); or read the chain's activating player
   from live engine state.
2. Does `0x0221F1F5` (Conscription) take a source zone, or hard-code the Deck?
3. Where does `0x0220F754`'s randomness come from — `0x022599F8`?
4. `+14 CLAUSE-2 entries == 2` for one destroy (see round 8). Unexplained.

## ⚠️ C3 PRACTICAL REACHABILITY — read before committing to this clause
C3 fires **only when the OPPONENT discards Grapha from YOUR hand with a card
effect.** Against the AI that requires it to play a hand-discard effect on the
player. Every clause-2 test so far discarded Grapha with the player's OWN Gates
of Dark World, which is a SAME-side discard and would leave C3 correctly inert.
So C3 is expensive to *test*, not just to build, and the in-game oracle may be
hard to trigger on demand.

## ⭐⭐ C3c IS A RETARGET, NOT NEW MACHINERY (proven 2026-08-28)

The blocker I expected here dissolved. **`0x021BA684` is a generic
"Special Summon a card from zone Z to your field" primitive that takes the
SOURCE ZONE as an argument in `r3`.** Scanned every `BL` in overlay 3:

```
0x021BA684 -- 20 callers
  r3 = 0x0B (THE HAND)  : 14 callers
  r3 = 0x0D (the Deck)  :  6 callers
```

⚠️ A first pass at this scan reported only 4 callers and missed Conscription's
own call site: the mask on the BL's second halfword was written `0xF800 <= h2 <
0xF900` instead of `(h2 & 0xF800) == 0xF800`. The corrected scan is the one
above. **A BL scanner that silently undercounts looks exactly like a rare
primitive** — check any "only N callers" claim against a known site.

The hand/deck split is not a guess: `ram.zone_code_0x0B_is_the_hand` already has
zone code **0x0B -> `player+0x124`, count `+0x0C`** VERIFIED, and the same KB
proof pins the deck array at `0xC1 << 2 = 0x304`.

### Conscription `0x192F` cls0[644] `+04` = `0x0221F1F4` IS the C3c template
Disassembled in full. It already does every step C3c needs:

```
0221F1F8  LDRB R0,[R5,#2] ; MOVS R6,#1 ; SUBS R0,R6,R0 ; ANDS R2,R6   ; (1 - side) = THE OPPONENT
0221F208  LDR R2,[..]     ; CMP R2,#0 ; BEQ bail                      ; opponent's zone EMPTY -> stop
0221F212  MOVS R1,#0xC1 ; LSLS R1,R1,#2 ; LDR R1,[R2,R1]              ; <-- +0x304 = THE DECK ARRAY
0221F21A  LSLS R1,#0x12 ; LSRS R4,R1,#0x12                            ; r4 = cid & 0x3FFF
0221F21E  MOVS R1,#0xD ; BL 0x0219CD08                                ; <-- zone probe, 0x0D = Deck
0221F22C  BL 0x021D2624                                               ; (reveal, on the probe's 0 path)
0221F254  BL 0x021C7628                                               ; reveal / relocate
0221F25A  BL 0x02029E60(r4)  ; BEQ bail                               ; IS IT A MONSTER?
0221F264  BL 0x020232EC(r4)  ; BEQ bail                               ; can it be Normal Summoned/Set?
0221F28E  MOVS R3,#0xD ; BL 0x021BA684                                ; <-- THE SUMMON, zone in r3
```

`0x02029E60` is the same "is this cid a monster" predicate the relocation
applier's own tail calls at `0x021D1A30` — so C3c's *"if it was a monster"* is
already the template's own gate.

### THE C3c CHANGE, in full
Clone `0x0221F1F4` into ov5 and change **two immediates**:

| what | Conscription | C3c |
|---|---|---|
| the card-word array | `MOVS R1,#0xC1 ; LSLS #2` -> `+0x304` (Deck) | `#0x49` -> **`+0x124`** (Hand) |
| the zone argument | `MOVS R3,#0xD` | **`MOVS R3,#0x0B`** |

plus the zone probe's `MOVS R1,#0xD` at `0x0221F21E` -> `0x0B`.

⚠️ STILL UNPROVEN: whether `0x020232EC` ("can be Normal Summoned/Set") should be
KEPT. Grapha's printed C3c says only *"if it was a monster"* — it does NOT
require the monster be Normal-Summonable, so a faithful build DROPS that gate,
while Conscription's own text requires it. Dropping it is a one-branch edit;
keeping it is a deviation. This is the kind of template-text bleed
`grep-the-template-cards-text-too` exists for.

⚠️ ALSO UNPROVEN: which card word the HAND index selects. Conscription reads a
FIXED slot (the top of the Deck). C3b's peek primitive `0x0220F754` indexes
`+0x124` by a u16 read from elsewhere, i.e. the RANDOM index it chose. C3c must
consume THAT SAME index, not slot 0 — otherwise the card summoned is not the card
that was looked at. **This is now the most important open question for C3.**

## ⚠️ CORRECTION (2026-08-28) — C3a WAS NEVER A BLOCKER, AND THE KB ALREADY SAID SO

The section above headed "C3a's OTHER HALF IS THE ONE REAL OPEN PROBLEM" is
**WRONG**. It concluded, from tracing the event word alone, that the acting side
"does not survive into the descriptor". It does.

**`0x021D3168` stores its THIRD argument — the packed card word `w` itself — at
`desc[+0x20]`** (`ADDS R7,R2,#0` @`0x021D3174`, `STR R7,[SP,#0x20]`
@`0x021D31B6`, the descriptor being `ADD R4,SP,#0`), and the post site hands it
`w` via `LDR R2,[SP,#0x28]`. I traced the event-word packing, stopped at
`desc[+6]`, and never checked what else the primitive wrote.

`dispatch.opponent_effect_discard_test` — **VERIFIED and already in the KB before
this session** — states the test outright, read off Sillva `0x1968`'s resolver
`0x0221FAA0`: `LDR R0,[R4,#0x20]` (the packed word), `LDRB R2,[R4,#0x2]` (the
ACTING side), then **bit 18 must NOT equal r2** and **bit 9 MUST equal r2**.

And **`patch_snoww` already SHIPS it** as its clause-2 `slot5_stub` gate, ten
instructions, for the same printed condition C3a needs. Those are the same two
bits `0x021D1300`'s prologue forms as `r7 = (w >> 9) & 1` and compares against
bit 18 at `0x021D1344`, and the same pair the 3DS tests in its own C3 arm.

**Process lesson, and the repo already documents it:** I derived from disassembly
without consulting `otn_enhanced/docs/engine/*.yaml` first, then reported a conclusion that
contradicted a passing VERIFIED fact. A contradiction with a green KB fact is a
bug in the derivation, not a discovery.

## ⭐ THE C3 ARCHITECTURE IS FULLY DETERMINED — no unknowns left

| step | mechanism | status |
|---|---|---|
| **C3a** | Snoww's `slot5_stub` gate verbatim: `desc[+0x20]` bit 18 != `desc[+2]`, bit 9 == `desc[+2]` | SHIPPED CODE, reuse |
| **C3b** | clone `0x0220F754` phases 0x80/0x7F (hand-count guard, post kind 5, read the index back) | PROVEN |
| **C3c** | extend that phase-0x7F tail: `0x02029E60`(cid) is-a-monster, then `0x021BA684` with **r3 = 0x0B** | PROVEN |

The index-coupling worry is gone: **phase 0x7F of the peek already reads the
randomly-chosen card** out of the opponent's hand array (`player+0x124`) at the
u16 index `0x0229DE94+6`. C3c extends that phase rather than re-deriving a pick.

Delinquent Duo `0x1325` (cls0[207], `+04 0x0220E108`) is the reference for the
random-pick family — a 3-phase machine posting `0x022599C8(opponent, 1, 1)`
(discard 1 RANDOM) then `0x022598A0` (the chosen discard). It confirms the pick
is a UI round-trip, never computed inline.

⚠️ Semantics confirmed by the user 2026-08-28: a random card is chosen; **if it
is a monster, Special Summon it to my side of the field; if it is not a monster,
do nothing.**

### The Conscription harness (user-requested, 2026-08-28)
Turn Conscription `0x192F` (cls0[644]) into a **Spell** whose effect is C3b+C3c
with **no C3a gate**, so the payload can be activated on demand instead of
waiting for the opponent to discard Grapha from hand. Donor checks: `name` floor
6 / `desc` floor 167 (ample); **no per-cid gates** — the single ARM9 hit at
`0x020202CC` is `ADDS R7,R5,R4`, an instruction encoding that reads as `0x192F`,
exactly as `donor_scan` classified it.

## C3 HARNESS BUILT 2026-08-28 — `verify()`-green, AWAITING IN-GAME TEST

**ROM:** `data/over_the_nexus/working/rom_grapha_test.nds`, 129518728 B, sha256
`9d205c1619f42b31f1d5981bd552a07a6e293e4801deb96808fff4f34cf79829`
(clauses-1+2 ROM was `19bacea3...`). Four patches, all four `verify()` against
that same file: `gates=PASS snoww=PASS grapha=PASS conscription=PASS`, zero FAIL
lines. Guards: `check_allocations` `[OK] ... ledger in sync`;
`verify_knowledge` `TOTAL 344 facts: 311 PASS 0 FAIL 33 UNVERIFIED`.

New module **`otn_enhanced/cards/conscription_c3.py`**,
chained as step 4/4 of `_build_grapha.py`. ⚠️ **A TEST CARD, NOT A SHIPPED CARD**
— not in `apply_all_patches`, and Conscription's printed effect is deliberately
destroyed.

### What it is
Conscription `0x192F` becomes a **Normal Spell** whose whole effect is Grapha
clause 3's PAYLOAD (C3b + C3c) with **no C3a condition at all**, so the payload
can be activated on demand instead of waiting for the AI to discard Grapha out
of the player's hand. The resolver lives at **`CAVE_GRAPHA... CAVE_C3_RES
0x0239D5C0`, 196 B of 0xE0**, and **Grapha clause 3 will point at the SAME
address** — the harness cannot drift from the thing it tests.

| # | change | where |
|---|---|---|
| 1 | the shared C3 payload resolver | ov5 `CAVE_C3_RES 0x0239D5C0` |
| 2 | `+04` -> the payload, `+0C` -> `0x021F2BD9` | ov3 `cls0[644]` |
| 3 | card type Trap (29) -> Spell (27), subtype stays Normal | `card_prop[1851]` |
| 4 | description rewritten to state the new effect | `bin2.pac`, 8/8 langs in-place |

The `+0C` swap is load-bearing: Conscription's own condition `0x021F98F4` gates
on the opponent's **DECK** count plus a free zone, which is wrong for a card that
looks at a **HAND**. `0x021F2BD9` is the native condition shared by Confiscation
`0x1324`, Delinquent Duo `0x1325` and The Forceful Sentry `0x132B` = "the
opponent's hand is not empty".

### ⚠️ THE ONE REAL FIND OF THE BUILD: the summon primitive FORCES
`0x021BA684` is not a neutral summon. It stores **1** at `[sp+4]` before calling
`0x021BA69C`, and that 1 is exactly what makes `0x021BA69C` **skip** its
`0x021B9E28` test at `0x021BA6BE`:

```
021BA68C  MOVS R1,#1 ; STR R1,[SP,#4]          ; <-- the FORCE flag
...
021BA6BC  CMP R6,#0 ; BNE 0x021BA6CE            ; r6 == that 1 -> SKIP
021BA6C0  LDR R0,[SP] ; BL 0x021B9E28 ; ...     ; never reached via this entry
```

and `0x021B9E28` is a Special-Summon-**LEGALITY** test anyway (a step-counter
compare plus the kind-`0x0B` rider walker `0x021A1430`), never a zone-capacity
one. **So nothing downstream of the wrapper asks whether the summoning player has
room.** Conscription's own `+0C` had been carrying that check via `0x021B9ECC`,
and this patch swapped that condition out — so the guard had to come back.

It is now in the PAYLOAD, not the condition, and that placement is the printed
text: *"you **can** Special Summon it"* is optional, so a full field must mean
the look-at still happens and the summon simply does not. Right before the
summon:

```
ldrb r0,[r5,#2] ; ldr r3,=0x021B9ECD ; blx r3 ; cmp r0,#0 ; beq done
```

`0x021B9ECD` == `0x021B9708(side, 8, 0)`, the same free-zone test Conscription's
stock condition used.

⚠️ This was caught by reading the primitive BEFORE the duel, not after one. The
first chain build (sha `4663b44a...`, payload 180 B) shipped WITHOUT the guard
and is superseded — do not test it.

### Deliberate deviation from the template, recorded
`0x020232EC` (*"that can be Normal Summoned/Set"*) is **NOT called**. That is
Conscription's own printed clause; Grapha says only *"if it was a monster"*.
`verify()` asserts the gate is absent from the payload's disassembly AND that it
is still present in the template at `0x0221F264`, so "we chose not to call it"
stays a checkable statement rather than a stale comment.

### The in-game test — NORMAL DUEL ONLY (ov5 cave; a puzzle's ov41 evicts it)
Deck needs Conscription plus the existing Grapha/Gates/Snoww cards.

1. Activate Conscription from hand while the opponent holds >= 1 card.
2. -> expect to be shown **1 RANDOM card from the opponent's hand**.
3. If it is a MONSTER -> expect it Special Summoned to **YOUR** field, and gone
   from the opponent's hand.
4. If it is a Spell/Trap -> expect **nothing** after the look.
5. NEGATIVE CONTROL: opponent's hand EMPTY -> the card must not be activatable.
6. FULL FIELD (five monsters yours) + a monster revealed -> the look-at still
   happens, **no summon, no hang**. This is what the new guard exists for.
7. REGRESSION: Omega Goggles `0x1EED`, Inspection `0x1367`, Delinquent Duo
   `0x1325` still work (their primitives are called, their rows untouched —
   `verify()` asserts all three keep their own `+04`).
8. REGRESSION: Grapha clauses 1 and 2 still behave (both in-game confirmed).

**STATUS: AWAITING IN-GAME TEST.** Nothing about clause 3 is confirmed. Grapha
clause 1 carries `in-game confirmed by user 2026-08-27`, clause 2
`in-game confirmed by user 2026-08-28`; the harness carries nothing.

### Still to build once the harness passes
Grapha clause 3 itself: gate `CAVE_C3_RES` behind Snoww's `slot5_stub` C3a test
(`desc[+0x20]` bit 18 != `desc[+2]`, bit 9 == `desc[+2]`) and chain it AFTER
clause 2's destroy — which means clause 2's arm becomes a multi-phase machine
(0x80 destroy -> 0x7F peek -> 0x7E summon) rather than the single-phase
`0x02204899` it is today. That phase chaining is the only unbuilt piece.

## C3 HARNESS ROUND 1 IN-GAME (2026-08-28) — PHASE 0x80 WORKS, PHASE 0x7F DOES NOT

User, verbatim, against the six numbered checks:

> "1. A card is picked, but it is not revealed to me
>  2. When I activated the effect when there was absolutely one monster in the hand it didn't summon
>  3. Nothing happens as expected I gues...
>  4. Didn't verify
>  5. Couldn't verify
>  6. No Regressions"

and, asked how they knew a card had been picked:

> "A card was highlighted with an animation"

### What that pins down
* **Phase 0x80 RAN.** It is the only thing in the payload that posts
  `0x022599F8` (kind 5), and the highlight animation is that post being serviced.
  So: the card activates, `0x021F2BD9` admits it, the resolver is entered with
  `[0x0229AAFC+0x70] == 0x80`, the hand-count guard passes, the request posts, and
  the UI round-trip completes and selects a card.
* **PHASE 0x7F PRODUCED NOTHING.** No reveal (check 1) and no summon (check 2) —
  and check 2 was the unambiguous case: the opponent held **exactly one card and
  it was a monster**, so `0x02029E60` could not legitimately have refused.
* Check 3 is **NOT an independent pass**. With no reveal, "nothing happened" for
  a Spell/Trap is indistinguishable from the whole tail being dead; the user
  flagged this themselves ("I gues...").
* Checks 4 and 5 untested. **No regressions** (check 6): Omega Goggles 0x1EED,
  Inspection 0x1367, Delinquent Duo 0x1325 and Grapha clauses 1+2 all still fine
  — so the patch is not damaging the primitives it borrows.

### TWO COMPETING SINGLE-CAUSE HYPOTHESES — do not guess between them
Both symptoms fall out of ONE fault, and there are exactly two candidates:

1. **Phase 0x7F is never entered.** Phase 0x80 returns 0x7F, but the engine
   either never re-enters the resolver or re-enters it with a phase value the
   stub does not match (`cmp r0,#0x7F` fails, then `cmp r0,#0x80` fails, and it
   falls through to `done` returning 0 — silently). Nothing in the payload would
   run, which is exactly what was observed.
2. **Phase 0x7F IS entered but reads the wrong card.** `0x0229DE94` has 161
   literal references in ov3 — it is a SHARED effect-context block — so `+6` may
   simply not be where THIS requester's chosen index lands. A garbage index gives
   a garbage card word: the reveal does nothing visible, `0x02029E60(garbage)`
   returns 0, and the summon is skipped. Also exactly what was observed.

⚠️ **DO NOT PATCH EITHER ON SPECULATION.** They are indistinguishable from the
prose report and they demand opposite fixes. This is the second failed
hypothesis on this payload (the first being the missing free-zone guard, caught
before the duel), so per CLAUDE.md's two-strike rule the next step is
MEASUREMENT, not code.

### NEXT EXPERIMENT — instrument the payload
The payload shipped with **no diagnostic block at all**, which is why one duel
bought so little. Add one and both hypotheses die in a single savestate:

| record | separates |
|---|---|
| total resolver entries | did it run more than once at all |
| OR of every `[0x0229AAFC+0x70]` value seen | the actual phase values, incl. one the stub ignores |
| count of entries matching NEITHER 0x7F nor 0x80 | hypothesis 1, directly |
| phase-0x7F entry count | hypothesis 1 vs 2 |
| the raw u16 at `0x0229DE94+6` | hypothesis 2 |
| the card word read, and the cid masked out of it | hypothesis 2 |
| the `0x02029E60` result, the `0x021B9ECD` result, summon-reached count | which gate stopped it |

## C3 HARNESS ROUND 2 BUILT 2026-08-28 — INSTRUMENTED, AWAITING ONE SAVESTATE

**ROM:** `data/over_the_nexus/working/rom_grapha_test.nds`, 129518728 B, sha256
`5207faf43d9aceb03e19c9117ba9b3be91a58c29ffcd108aaed233a97cb8d0e5`
(round 1 was `9d205c16...`). `gates=PASS snoww=PASS grapha=PASS
conscription=PASS`, zero FAIL lines; `check_allocations` `[OK] ... ledger in
sync`; KB `344 facts: 311 PASS 0 FAIL`.

**No behaviour was changed.** This build only adds measurement — the two
hypotheses demand opposite fixes and guessing between them would be a blind
build-test cycle.

* payload `CAVE_C3_RES 0x0239D5C0`, now **252 B of 0x140** (was 196 of 0xE0)
* new `CAVE_C3_DIAG 0x0239D700`, 0x40 B, zeroed in the image
* new reader `ygo_tools/tools/conscription_diag.py`

### What it records, and which hypothesis each slot kills

| off | slot | separates |
|---|---|---|
| 00 | resolver entries, ALL phases | did it run at all |
| **04** | **OR of every phase value seen** | **the decisive one** |
| 08 | entries matching NEITHER 0x7F nor 0x80 | a phase the stub ignores |
| 0C | phase 0x80 entries | (known good — the animation proves it) |
| 10 | phase 0x7F entries | **H1 vs H2, directly** |
| 14 | last chosen index, u16 @`0x0229DE94+6` | H2 |
| 18 | last card word read from the opponent's hand | H2 |
| 1C | last cid masked out of that word | H2 |
| 20 | `0x02029E60` is-a-monster result | which gate stopped it |
| 24 | `0x021B9ECD` free-zone result | which gate stopped it |
| 28 | summon reached (`0x021BA684` called) | argument bug vs gate bug |
| 2C | last opponent HAND COUNT seen in phase 0x80 | sanity |
| 30 | last opponent side computed in phase 0x80 | sanity |

`[04]` is decisive because it ORs **every** phase value the resolver is handed,
so a phase the stub silently falls through on cannot hide:

* `0x80` alone -> **H1**: phase 0x7F is never entered; returning 0x7F from phase
  0x80 is not by itself enough to get this card called back.
* `0xFF` (`0x80 | 0x7F`) -> **H2**: the tail ran; `[14]`/`[18]`/`[1C]` say what
  it read.
* anything else -> the engine drives this card on a phase neither the stub nor
  the native peek resolver expects, and `[08]` counts those.

### If it comes back H1, the structural difference to test is already identified
Both native users of `0x0220F754` carry a **non-zero `+10` (cost) slot** --
Omega Goggles `0x1EED` cls3[460] `+10 = 0x021E5061`, Inspection `0x1367`
cls1[132] `+10 = 0x021E780D` -- and so does the other multi-phase cls0 card,
Delinquent Duo `0x1325` cls0[207] `+10 = 0x021E4D81`. **The harness has
`+10 = 0`.** `dispatch.absent_slot4_reports_one` says an absent slot4 is reported
as 1 by the wrapper at `0x0224AE50`, which is "no cost, proceed" -- but whether
the multi-phase RE-ENTRY also depends on that slot has never been measured.
⚠️ UNVERIFIED, and it is a hypothesis, not a finding: do not patch it until
`[04]` says H1.

### The test
Activate Conscription with the opponent holding at least one card — ideally
**exactly one, and a monster**, which is the unambiguous case round 1 already
tried. Save a state immediately after it resolves, then:

```
.venv-1/Scripts/python.exe -m ygo_tools.tools.conscription_diag <savestate>
```

The reader prints the decision itself.

## ⭐⭐ C3 HARNESS ROUND 2 SAVESTATES (2026-08-28) — BOTH HYPOTHESES DEAD, REAL CAUSE FOUND

User supplied `.ml2` (before) and `.ml3` (after), both 2026-08-28 13:28 on ROM
`5207faf4...`.

`.ml2` — every counter zero, i.e. a clean baseline taken before activation.
`.ml3` — after activating Conscription:

```
[00] resolver entries, ALL phases                 2
[04] OR of every phase value seen                 0xFF   = 0x80 | 0x7F
[08] entries matching NEITHER 0x7F nor 0x80       0
[0C] phase 0x80 entries                           1
[10] phase 0x7F entries                           1
[14] last chosen index @0x0229DE94+6              1
[18] last card word from the opponent's hand      0x10005649
[1C] last cid                                     0x1649   = Acrobat Monkey
[20] 0x02029E60 is-a-monster                      1
[24] 0x021B9ECD free-monster-zone                 1
[28] summon reached                               1
[2C] opponent HAND COUNT in phase 0x80            5
[30] opponent side                                1
```

**H1 dead** — the phase machine is perfect: 0x80 once, 0x7F once, nothing
unhandled. **H2 dead** — index 1 gave card word `0x10005649`, a completely valid
card: cid `0x1649` Acrobat Monkey, ref side bit 1 (the opponent, matching `[30]`),
instance 32. `0x0229DE94+6` IS the right slot.

Every gate passed, the call was made, and nothing was summoned.

### ⚠️ THE CAUSE: `0x021BA684` IS A PREDICATE. IT SUMMONS NOTHING.
Reading it to the epilogue — two instructions past where I stopped the first
time — every path returns a constant:

```
021BA80A  MOVS R0,#1 ; ADD SP,#0x14 ; POP {R4-R7,PC}     ; accept
021BA6CA  MOVS R0,#0 ; B 0x021BA80C                       ; every reject
```

and `0x021BA69C` is a chain of legality gates: `0x02023398(cid)`,
`0x020232AC(cid)`, and a per-cid switch that compares the **zone** `r5` against
`0x0B` / `0x0D` / `0x0E` for cards with printed summon restrictions. It answers
*"may this card be Special Summoned from zone Z"* and does nothing else.

The payload called it, threw the boolean away, and returned. That is the whole
bug, and it explains **both** round-1 symptoms at once.

### THE REAL ACTION IS `0x02269314`
Conscription's own resolver, read past the predicate:

```
0221F294  CMP R0,#0 ; BEQ ...            ; <-- it TESTS the predicate
0221F29A  BL 0x021AD870(side)  ; gate
0221F2A4  BL 0x021B9ECC(side)  ; the free-zone gate
0221F2BC  MOVS R1,#0xC1 ; LSLS R1,R1,#2 ; ADDS R1,R2,R1   ; player[opp] + 0x304
0221F2C2  ADDS R2,R6,#0 (=1) ; MOVS R3,#0
0221F2C4  BL 0x02269314                  ; <-- THE SUMMON
```

⚠️ **`0x02269314` takes a POINTER TO THE CARD-WORD SLOT**, not a cid/ref pair —
that is how it removes the card from the source array. 72 callers, all
`r0 = desc[+2]`, `r1 = a pointer`, `r2 = 1`.

For C3c the pointer is `STATE_A + opponent*0xB3C + 0x124 + index*4` — the HAND
slot the payload already computes and currently only dereferences.

### Process note, recorded because it is the reusable part
The caller census (20 callers, 14 hand / 6 deck) proved the **zone is a
parameter** — true, and still the reason hand-sourcing works. But it was allowed
to stand in for reading what the function **does**. A census tells you about an
argument; only the body tells you the role. `dispatch.summon_from_zone_primitive`
is corrected in place with this attached.

## C3 HARNESS ROUND 3 BUILT 2026-08-28 — the predicate is now TESTED and the REAL summon called

**ROM:** `data/over_the_nexus/working/rom_grapha_test.nds`, 129518728 B, sha256
`bbe98a6d1ca1ecaee71d371cd0d139223222946c32b4ab6ba9397c3f2f70e6e9`
(round 2 was `5207faf4...`). `gates=PASS snoww=PASS grapha=PASS
conscription=PASS`, zero FAIL lines; `check_allocations` `[OK]`; KB 344 facts,
311 PASS, 0 FAIL. Payload **292 B of 0x140**.

### The fix
Round 2's payload called `0x021BA684`, threw its boolean away, and stopped.
`0x021BA684` is a PREDICATE. The tail is now the template's own three-gate
sequence followed by the real action:

```
GATE 1  0x021BA684(side, cid, ref, 0x0B)  -> may THIS CARD be SS'd from the HAND
        ⚠️ the answer is TESTED now                      -> DIAG +0x38
GATE 2  0x021AD870(side)                  -> may this player SS right now
                                                         -> DIAG +0x3C
GATE 3  0x021B9ECC(side)                  -> is there a free monster zone
                                                         -> DIAG +0x24
ACTION  0x02269314(side, SLOT POINTER, 1, 0)             -> DIAG +0x28 / +0x34
```

⚠️ **The action takes a POINTER to the card-word slot**, not a cid or a ref —
that is how it removes the card from the opponent's hand. Phase 0x7F now keeps
`STATE_A + opponent*0xB3C + 0x124 + index*4` (stashed at DIAG `+0x34`, which
doubles as the diagnostic) instead of only dereferencing it.

Two register notes, both real footguns avoided:
* `MOVS R3,#0x0B` must be issued **after** the predicate's function pointer is
  loaded, or the `LDR R3,=...` clobbers the zone argument. The pointer goes in
  `r6` instead and the zone is set last.
* `r6` (the card word) is spent as that call register, so the cid is re-read
  from its DIAG copy at `+0x1C` rather than re-derived from `r6`.
* the slot pointer is loaded from `+0x34` **before** `r4` (the DIAG base) is
  reused to hold the summon pointer.

### The test — same as before
Activate Conscription with the opponent holding at least one card; ideally one
that is a **monster**. Then savestate and:

```
.venv-1/Scripts/python.exe -m ygo_tools.tools.conscription_diag <savestate>
```

The reader now names which of the three gates refused, if any, and prints the
slot pointer it handed the summon. Expected on success: `[38] [3C] [24]` all 1,
`[28]` 1, `[34]` a plausible pointer into `0x0229....`, and a monster on your
field that has left the opponent's hand.

⚠️ Reading an OLD savestate with the new reader shows `[38]`/`[3C]`/`[34]` as 0
because those slots did not exist in that build — that is not a result.

**STATUS: AWAITING IN-GAME TEST.** Clause 3 remains unconfirmed. Grapha clauses
1 and 2 are in-game confirmed (2026-08-27 / 2026-08-28) and untouched by all
three harness rounds.

## ⭐⭐ C3 PAYLOAD IN-GAME CONFIRMED BY THE USER 2026-08-28

User: *"Before: ml2, After: ml3. I activated conscription and it summoned a
monster"* — savestates 14:55 / 15:09 on ROM `bbe98a6d...`.

`.ml2` is a clean pre-activation baseline (all counters zero). `.ml3`:

```
[00] resolver entries                 2        [04] OR of phases      0xFF
[0C] phase 0x80 entries               1        [10] phase 0x7F        1
[14] chosen index                     1
[18] card word            0x02804FC0  ->  cid 0x0FC0 = BATTLE OX, ref side 1 (opp), inst 5
[20] 0x02029E60 is-a-monster          1
[38] GATE 1 0x021BA684 may-SS-from-hand   1
[3C] GATE 2 0x021AD870 player-may-SS      5     <-- truthy, NOT a boolean (see below)
[24] GATE 3 0x021B9ECD free zone          1
[28] REAL summon 0x02269314 reached       1
[34] hand SLOT POINTER            0x0229B8F8
[2C] opponent hand count 5             [30] opponent side 1
```

**The slot-pointer arithmetic is exact.**
`STATE_A 0x0229AC94 + opponent(1) * 0xB3C + 0x124 + index(1) * 4 = 0x0229B8F8`,
byte-for-byte what the payload handed `0x02269314`. That is the whole
hand-sourced summon recipe verified against live RAM, not inferred.

### THE WORKING RECIPE — "Special Summon a random card from the opponent's HAND"
This is the reusable result of the whole clause-3 effort:

```
phase 0x80   opponent = (1 - desc[+2]) & 1
             if player[opponent] hand count (STATE_A + opp*0xB3C + 0x0C) == 0: return 0
             0x022599F8(opponent, 0)        ; post the random pick, kind 5 -> UI round-trip
             return 0x7F
phase 0x7F   slot = STATE_A + opp*0xB3C + 0x124 + [0x0229DE94+6] * 4
             w    = *slot                   ; the chosen card word
             ref  = bit14(w) + 2*((w >> 23) & 0xFF)
             0x021D2598(desc[+2], ref)      ; the printed "look at"
             cid  = w & 0x3FFF
             if !0x02029E60(cid):        return 0     ; not a monster -> DO NOTHING
             if !0x021BA684(desc[+2], cid, ref, 0x0B): return 0   ; per-cid SS restriction
             if !0x021AD870(desc[+2]):   return 0     ; may this player SS now
             if !0x021B9ECC(desc[+2]):   return 0     ; free monster zone
             0x02269314(desc[+2], slot, 1, 0)         ; THE SUMMON -- slot POINTER
             return 0
```

⚠️ `0x021AD870` returned **5**, not 1 — it is a truthy count/bitmask, not a
boolean. Test it with `cmp r0,#0 / beq`, never against 1.

### What is confirmed, and what is NOT
CONFIRMED in-game 2026-08-28: the activation, the random pick, the monster test,
all three gates, and the summon of the chosen monster out of the opponent's hand
onto the user's field.

⚠️ **NOT yet verified** — do not write these off as passing:
* the printed **"look at"** being visible to the player. Round 1 reported *"a
  card is picked, but it is not revealed to me"*; this round the user reported
  only the summon and was not asked about the reveal. `0x021D2598` is called
  with the same arguments the native peek uses, but whether the player actually
  SEES the card is untested.
* the **non-monster** case (expect: nothing at all after the look).
* the **full-field** case (expect: look happens, GATE 3 refuses, no summon, no
  hang).
* the **empty-hand** case (expect: not activatable — the 0x021F2BD9 condition).

### Round 2's misdiagnosis, for the record
Round 2's payload reached this same point and summoned nothing because
`0x021BA684` was called as if it were the summon. It is a PREDICATE. The
diagnostic block is what separated "gate refused" from "action never happened",
and the fix was to test its boolean and call `0x02269314` — see
`dispatch.summon_from_zone_primitive`, corrected in place.

## ⭐ GRAPHA CLAUSE 3 BUILT 2026-08-28 — AWAITING IN-GAME TEST

**ROM:** `data/over_the_nexus/working/rom_grapha_test.nds`, sha256
`f4db9a1ce7817850d298950c553ddcb7a15f5cb57b7be5d625cfa4192cac2257`.
**STACKED test ROM (the one to duel with):**
`data/over_the_nexus/working/rom_grapha_test_stacked.nds`, 129518728 B, sha256
`fd6eb164a58994fb835882a720b2a5060e4b822b75211b71d54539675c621ca2`.
`gates=PASS snoww=PASS grapha=PASS conscription=PASS` against **both** files;
`check_allocations` `[OK] ... ledger in sync`; KB 345 facts, 312 PASS, 0 FAIL.

### THE PAYLOAD IS NOT DUPLICATED — that is the whole design
The confirmed payload was split into a thin phase shell plus **two SHARED
halves**, and Grapha drives the very same two addresses the Conscription harness
proved in-game:

| slot | addr | size | role |
|---|---|---|---|
| `CAVE_C3_RES` | `0x0239D5C0` | 80 of 0x60 | Conscription's phase shell (dispatch only) |
| `CAVE_C3_POST` | `0x0239D620` | 80 of 0x60 | **SHARED** half 1: hand-count guard + post the pick |
| `CAVE_C3_FINISH` | `0x0239D680` | 196 of 0xE0 | **SHARED** half 2: look-at, three gates, summon |
| `CAVE_C3_DIAG` | `0x0239D760` | 0x40 | diagnostics (⚠️ MOVED from `0x0239D700`) |
| `CAVE_GRAPHA_C3` | `0x0239D7A0` | 116 of 0xA0 | Grapha's clause-2+3 arm |

Only the phase dispatch moved out of the confirmed code; the halves are the same
logic that summoned Battle Ox. The harness therefore cannot drift from the thing
it certifies.

### Grapha's clause 2 + 3 arm
`CAVE_GRAPHA_RES2`'s clause-2 branch could not hold this (168 B needed vs its
0x60), so it now tail-calls `CAVE_GRAPHA_C3`, and the clause-1 path is untouched
BYTES rather than untouched-by-inspection. The arm is a two-phase machine on the
SAME phase values the shared halves already use, so nothing is translated:

```
phase 0x80  clause 2's destroy 0x02204899        (in-game confirmed)
            then CLAUSE 3's condition:
              r3 = desc[+2]                      the ACTING side
              r2 = desc[+0x20]                   the packed card word
              bit 18 of r2 must DIFFER from r3   -> by an OPPONENT's effect
              bit  9 of r2 must EQUAL  r3        -> from YOUR hand
            if it passes: CAVE_C3_POST, return 0x7F; else return 0 (as before)
phase 0x7F  CAVE_C3_FINISH, return 0
```

⚠️ **The condition is SHIPPED CODE, not a new guess.** It is `patch_snoww`'s
clause-2 `slot5_stub` verbatim — `dispatch.opponent_effect_discard_test`, itself
read off native Sillva `0x1968` — and **Snoww clause 2 is in-game confirmed by
the user 2026-08-27** ("Perfect! Ship it!"), including the opponent's-effect
discard path specifically.

New diagnostics in Grapha's own block: `+0x24` last phase on the discard arm,
`+0x2C` C3a-passed count, `+0x30` finish-half entries.

### The test rig: 20x Delinquent Duo in every AI deck
`_stack_opponent_decks.py` is now parameterised (`--card`, `--copies`); 305 decks
stacked 20/40 with **Delinquent Duo 0x1325**. It is the right trigger: played by
the AI it makes *you* discard **twice** (one random, one chosen), and either
discard is an OPPONENT's card effect hitting YOUR hand — exactly C3a.

⚠️⚠️ **20 COPIES IS A KNOWN HAZARD, AND THE PRECEDENT IS IN THIS REPO.**
`card.snoww_unlight_of_dark_world` records that Snoww clause 2's round-1
"failure" was **the harness, not the patch**: the AI decks had been stacked 20/40
with Card Destruction, so the opponent's zones were nearly all Spells and the
enumeration legitimately found nothing. *"Rebuilding the harness at 8 copies
fixed it."*

The same trap applies here, and harder: clause 3 looks at **1 random card in the
opponent's HAND** and only acts **if it is a monster**. With half the AI's deck
being a Spell, roughly half of all C3 firings will correctly do nothing and look
like a failure. If the trigger fires but nothing is summoned, **re-roll the
harness before suspecting the patch**:

```
.venv-1/Scripts/python.exe _stack_opponent_decks.py --copies 8
```

⚠️ Also UNVERIFIED for any copy count: that the AI will actually *play* the card
it has been handed. Stacking guarantees it is DRAWN, not PLAYED.

### The in-game test
Duel `rom_grapha_test_stacked.nds` in a NORMAL DUEL. Hold Grapha in hand and let
the AI resolve a Delinquent Duo that discards it.

1. Grapha discarded from your hand by the AI's Delinquent Duo -> clause 2 fires
   (target 1 card the opponent controls, destroy it), **then** clause 3: a random
   card from the AI's hand is looked at, and if it is a monster it is Special
   Summoned to YOUR field.
2. NEGATIVE CONTROL: discard Grapha with your OWN Gates of Dark World -> clause 2
   must fire and clause 3 must NOT (same-side discard).
3. REGRESSION: clause 1 (GY summon) and clause 2 alone both still behave.
4. Savestate either way, then BOTH readers:
   `... -m ygo_tools.tools.grapha_diag <state>` (C3a: `+0x2C` nonzero = the
   condition passed) and `... -m ygo_tools.tools.conscription_diag <state>`
   (the payload's own gates).

**STATUS: AWAITING IN-GAME TEST.** Clause 3 is unconfirmed. Clause 1 carries
`in-game confirmed 2026-08-27`, clause 2 `in-game confirmed 2026-08-28`, and the
clause-3 PAYLOAD carries `in-game confirmed 2026-08-28` via the harness — but the
CONDITION and the chaining have never run.

### User-accepted deviation, recorded rather than dropped
The printed "look at 1 random card" produces **no visible reveal** — round 1 of
the harness reported *"a card is picked, but it is not revealed to me"* and the
user ruled on it 2026-08-28: *"I didn't see the picked card, but its not a big
deal."* `0x021D2598` is called with the native peek's exact arguments, so this is
a UI-visibility gap, not a logic one. It is a DEVIATION from the printed text,
accepted by the user, not a passing check.

## ⭐⭐ CLAUSE 3 IN-GAME CONFIRMED 2026-08-28 — GRAPHA IS COMPLETE AND SHIPPED

User: *"I have tested clause 1 and clause 2 and clause 3. they all work. ship
everything"*.

| clause | status |
|---|---|
| C1 SS from the GY by returning a Dark World monster | in-game confirmed 2026-08-27 |
| C2 discarded by a card effect -> destroy 1 card the opponent controls | in-game confirmed 2026-08-28 |
| C3 by an OPPONENT's effect from your hand -> look, then maybe summon | **in-game confirmed 2026-08-28** |

**SHIPPED** into `apply_all_patches` as step 30, immediately after Snoww (29) and
Gates (28); WiFi timers still last. That order is load-bearing: Grapha and Snoww
both plant an ov3 stub on the SAME `0x021D1392` switch chain, and Snoww's
whole-table regression walk only tolerates Grapha's because `patch_grapha`
registers it via `patch_snoww.register_switch_stub` at IMPORT time.

⚠️ **`patch_conscription_c3` is NOT shipped and must never be** — it destroys
Conscription's printed effect on purpose. It stays a `_build_grapha.py`-only card.

### ⚠️ THE SHIPPING BUG THIS ALMOST HAD — the reusable lesson
The two shared C3 halves were **authored in the test harness**, which by design is
never wired into `apply_all_patches`. Shipping `patch_grapha` alone would have left
clause 3 calling an **unwritten ov5 cave** — a freeze, in a card that had just been
confirmed working. Caught while writing the ship step, not in a duel.

> **Code shared between a shipped patch and a test harness must live in the
> SHIPPED module, and the harness must import it — never the other way round.**

Here the reverse was not even possible: `patch_conscription_c3` already imports
`patch_grapha` for its pac helpers, so harness-owned halves were a circular import
waiting to happen as well as a shipping hole.

**The move produced a BYTE-IDENTICAL ROM** — `_build_grapha.py` still emits sha256
`f4db9a1ce7817850d298950c553ddcb7a15f5cb57b7be5d625cfa4192cac2257`, exactly the
pre-refactor hash. That is what proved it was organisational rather than a rewrite
of confirmed code.

### Final clause-3 architecture
```
CAVE_GRAPHA_C3 0x0239D7A0  116 B   clause 2 + 3 arm (Grapha only)
  phase 0x80   destroy 0x02204899, then the C3a condition:
                 desc[+0x20] bit 18 != desc[+2]   an OPPONENT's effect
                 desc[+0x20] bit  9 == desc[+2]   from YOUR hand
               pass -> CAVE_C3_POST, return 0x7F;  fail -> return 0
  phase 0x7F   CAVE_C3_FINISH, return 0
CAVE_C3_POST   0x0239D620   80 B   SHARED, owned by patch_grapha
CAVE_C3_FINISH 0x0239D680  196 B   SHARED, owned by patch_grapha
CAVE_C3_DIAG   0x0239D760  0x40    diagnostics
CAVE_C3_RES    0x0239D5C0   80 B   the HARNESS's phase shell (NOT shipped)
```

### Accepted deviation, carried with the card
The printed "look at 1 random card" produces **no visible reveal** (`0x021D2598`
gets the native peek's exact arguments, so it is a UI-visibility gap, not logic).
User ruling 2026-08-28: *"I didn't see the picked card, but its not a big deal."*
Recorded as a DEVIATION, not a passing check.

## ⚠️ SHIPPING GRAPHA SURFACED A PRE-EXISTING CHAIN BREAKAGE (2026-08-28)

The first `apply_all_patches` run since Snoww shipped **died at step 30**:

```
AssertionError: R cid 0x17C6 changed leaf: 0x021D19C0 -> 0x021B5920
```

⚠️ **Read the log carefully**: `tqdm` writes its progress bar to stderr while the
step banners go to stdout, and with stdout block-buffered the traceback surfaced
at the TOP of the file while the banners flushed at exit. It looks like an early
failure and is not. Re-run with `python -u` to get honest ordering. The bash exit
code is also useless here -- the command was `python ... > log 2>&1; echo; tail`,
so the shell reported the exit status of `tail`.

**NOT caused by Grapha.** `0x021B5920` is `patch_eclipse_wyvern`'s `GATE_STUB`,
planted at step **25**; Snoww is **30**; Grapha is **31** and had not run. Grapha
only ever maps cid `0x1961` and its stub is at `0x021B594A`.

### The mechanism
`patch_snoww._assert_switch_unchanged` walks all 0x2700 cids and compares each
leaf against the committed ov3 oracle. `_switch_leaf` stops at any `BL` it does
not recognise as a **registered** stub — so every cid that merely *passes
through* another patch's stub reads as "changed leaf". Eclipse Wyvern predates
`register_switch_stub` and never called it, so this had been latent in the chain
the whole time. Nobody had run the full build.

### The fix — one import-time line, emitting NO bytes
```python
_snoww.register_switch_stub(GATE_STUB, GATE_STUB_LEN, {DONOR_CID: GATE_STUB + 14})
```
⚠️ **The terminus is not the arm.** `_switch_leaf` follows a **direct BL** (which
is why Grapha's donor registers as the real arm `0x021D185C`) but cannot resolve a
PC-relative literal through a register. Eclipse reaches its arm via
`LDR R0,[PC,#4] ; BX R0`, so the walk terminates at the `BX` itself,
`GATE_STUB + 14`. The literal it loads is `GATE_ACCEPT | 1`, asserted separately
by Eclipse's own `verify()`.

Verified against the partial chain ROM without a rebuild: `0x17C6` and `0x1859`
both pass, and Eclipse's own `verify()` still returns True (the change is
byte-neutral).

### The lesson, and it is about DETECTION
A composition guard that only runs in the FULL chain is **not exercised by any
single-card `_build_*.py`**, so it can stay red for as long as nobody ships. Run
`apply_all_patches` when you add a patch that touches SHARED ov3 code — not only
when you ship.

## ✅ SHIPPED 2026-08-28 — the combined ROM, all 40 patches, sweep green

```
apply_all_patches   PYTHON_EXIT=0   40/40 steps   0 tracebacks
  data/over_the_nexus/working/rom_all_patches.nds
  129528456 bytes
  sha256 4c5cf1544fb39a6ed0950bbd843d0a2bd4087a71b6bf442692ddafb5cd2c0e3f

_verify_all_patches SWEEP_EXIT=0   PASS 29   FAIL 0   SKIP 2
  (skipped: patch_boggart_knight, patch_darksoul -- neither has a verify())

check_allocations   [OK] no ov5 overlaps, no phantom double-claims, no ov3 overlaps
verify_knowledge    347 facts: 314 PASS  0 FAIL  33 UNVERIFIED
```

Grapha is step 31, after Gates (29) and Snoww (30); WiFi timers still last.

### ⚠️ A SECOND import-order bug, same root cause, different harness
After fixing Eclipse Wyvern's missing registration the chain built clean, but the
verify sweep then reported **patch_snoww FAIL** — against a ROM that was correct.
`_verify_all_patches.py` imported each module lazily *inside* its verify loop, and
`patch_snoww` precedes `patch_grapha` in `SHIPPED`, so Snoww verified while
Grapha's stub was still unregistered. The identical walk PASSES as soon as both
modules are imported.

The sweep now imports **every** module first and verifies afterwards.

> **When a module publishes shared state as an import side effect, any harness
> that loads modules one at a time sees a partially-populated world — and the
> symptom is a failure in some OTHER module that looks like a real regression.**

Both bugs this session were the same property biting twice: registration happens
at import, so *what has been imported so far* silently changes the answer.

### Not shipped, deliberately
* `patch_conscription_c3` — the C3 test harness. It destroys Conscription's
  printed effect on purpose and is a `_build_grapha.py`-only card.
* `_stack_opponent_decks.py` — a deck-stacking rig, not a patch; it touches only
  `deck.pac` and produces throwaway duelling ROMs.

## ✅ ECLIPSE WYVERN, FIXED PROPERLY (2026-08-28) — the tracer, not a workaround

The first fix registered Eclipse's donor as `GATE_STUB + 14`, an address **inside
its own stub**, because `patch_snoww._switch_leaf` could not follow
`LDR R0,[PC,#4] ; BX R0`. That unblocked the chain but weakened the guard: it
checked *"the walk stopped where we expected"* rather than *"the donor reaches the
right arm"*, and would not have noticed if Eclipse's literal changed.

**The tracer now follows an indirect tail — but only inside a REGISTERED stub**,
where the register value provably came from a literal load out of the same overlay
image rather than from unmodelled code. The conservatism that makes this guard
trustworthy is therefore intact everywhere else, and no other patch's reported leaf
can move.

Eclipse's donor now traces all the way through `GATE_ACCEPT` to **`0x021D19BE`
`STR R0,[SP,#0x14]`** — the ACCEPT path's flag store. That is a *meaningful*
terminus: reject cids stop two bytes later at `SWITCH_END 0x021D19C0 MOVS R0,#0`,
so the guard now distinguishes accept from reject rather than stub-internal
geography.

```
R  switch walk over 0x2700 cids: only 0x1C18 moved (-> 0x021D185C),
   0x1859 -> 0x021D19BE, 0x1961 -> 0x021D185C; 0x1BEB still -> 0x021D1902
```

Exactly the three intended donors, plus Lich Lord unmoved.

### Proof it changed no ROM
`_switch_leaf` is analysis-only. The shipped combined ROM's sha256 is
**`4c5cf1544fb39a6ed0950bbd843d0a2bd4087a71b6bf442692ddafb5cd2c0e3f`** before and
after, and the sweep is still `PASS 29 FAIL 0` (`SWEEP_EXIT=0`).

## 📋 DEVIATION LOG — clause 3's reveal is invisible (accepted 2026-08-28)

**Printed:** "...**look at 1 random card in your opponent's hand**, then, if it was
a monster, you can Special Summon it to your side of the field."

**Built:** the card is picked (a highlight animation plays over the opponent's
hand) and, if a monster, it is Special Summoned. **The player is never shown the
card.**

**Status:** DEVIATION, accepted by the user — *"I didn't see the picked card, but
its not a big deal."* Recorded as their ruling, **not** as a passing check. The
summon half is in-game confirmed; only the look-at is missing.

**Why it is probably not a logic bug:** `CAVE_C3_FINISH` calls `0x021D2598` with
exactly the arguments the native random-peek resolver `0x0220F754` uses —
`r0 = desc[+2]`, `r1 = bit14(w) + 2*((w >> 23) & 0xFF)`. So it looks like a
UI-visibility gap rather than a wrong call.

⚠️ **Untested assumption:** that the NATIVE users of that primitive display
anything in this build either. If Omega Steel Goggles `0x1EED` and Inspection
`0x1367` are equally silent, the engine's random peek is simply non-visual and
there is nothing to fix.

### NEXT EXPERIMENT (deferred by the user — "save that for later")
Their lead: **The Inexperienced Spy `0x12F0`**, `cls0[170]`, `+04 = 0x0220D575`,
printed *"Select and see 1 card in your opponent's hand"* — a card whose entire
effect is a visible hand reveal.

⚠️ It is a **chosen** reveal, not a random one, so it is not a drop-in for clause
3's selection. What is wanted from it is only its **display** call.

Nice corroboration in passing: its `+0C` is `0x021F2BD9`, the *same*
opponent's-hand-not-empty condition the Conscription harness picked.

1. **Cheapest first:** activate Omega Goggles or Inspection in a duel and see
   whether the native random peek shows anything. If not, close this out.
2. Otherwise disassemble `0x0220D574` and diff its reveal path against
   `0x0220F754`'s `BL 0x021D2598`.
3. If the Spy uses a different primitive (or the same one with a different
   argument form), splice it into `CAVE_C3_FINISH` between the card-word read and
   the is-a-monster test.
