# Azure-Eyes Silver Dragon — findings (2026-08-20)

Scope this session: **clause 3 only** (the Standby-Phase Normal-Monster revive).
Clauses 1 (Normal-Monster materials) and 2 (on-SS targeting/destruction
protection) are deliberately out of scope; nothing is shipped for this card yet,
so no clause can regress.

Card text, from `scratch/ygoprodeck_cache.json` id 40908371 (NOT from recall) —
LIGHT / Dragon / Synchro / Level 9 / 2500 / 3000:

> 1 Tuner + 1+ non-Tuner Normal Monsters
> If this card is Special Summoned: Until the end of the next turn, neither player
> can target Dragon monsters you currently control with card effects, also they
> cannot be destroyed by card effects. Once per turn, during your Standby Phase:
> You can target 1 Normal Monster in your GY; Special Summon it.

3DS cross-check (`CARD_Indx_E` record 5631, `CARD_Prop` cid `0x2961`), OTN-era
printing of the same three clauses:

> 1 Tuner + 1 or more non-Tuner Normal Monsters / When this card is Special
> Summoned: Dragon-Type monsters you currently control cannot be targeted or
> destroyed by card effects until the end of the next turn. / Once per turn,
> during your Standby Phase: You can target 1 Normal Monster in your Graveyard;
> Special Summon that target.

Clause numbering used below: **1** = materials, **2** = on-SS protection,
**3** = Standby-Phase revive.

---

## Confirmed (this session, against the committed oracles)

`verify_knowledge` baseline at session start: **246 PASS / 0 FAIL / 31 UNVERIFIED**.

### Azure-Eyes is not in the NDS
No `card_prop` record carries cid `0x2961`. Full donor conversion required.

### The 3DS ships the card — checked BEFORE any NDS disassembly
- `CARD_Prop` record 5631, first u16 `0xA961`, masked `0x3FFF` -> cid **`0x2961`**.
- 3DS criteria registry (`0x686CBC`, 2100 rows) row 1953:
  `{cid 0x2961, aux 0xFFFF, handler 0x4B1B74, word 0x00010402}`.
  Handler-sharers with the same word are exactly the Normal-Monster revivers:
  Silent Doom `0x14F7`, Soul Resurrection `0x17B7`, Birthright `0x1B65`,
  Swing of Memories `0x1C58` — all four exist in OTN.
- 3DS on-summon trigger registry (`0x6C335C`, 489 rows) has TWO rows for `0x2961`:
  row 458 `{router 0x45AF54, 0x3F033C, 0x404260}` and
  row 459 `{router 0x45E8A0, 0x49D508, 0x400004, 0x477CC0}`. Row 459's router is
  shared by ~25 "target 1 X in your GY; Special Summon it" cards, so row 459 is
  clause 3 and row 458 is clause 2. (Recorded for the clause-2 session; 3DS
  addresses deliberately kept out of the NDS namespace.)

### The Standby-Phase offer is a registry-row + generic-resolver pair
- Effect registry `0x0228E1E0`, stride 8, `[resolver u32][cid u16][pad u16]`.
- The section based at **`0x0228EB08`** (row 293) has count **`0x88` = 136** — the
  immediate at `0x02258378` — so it spans rows 293..428 and ends exactly at the
  next section base `0x0228EF48` (row 429).
- Walker at `0x02258358`:
  `ldr r2,[base + i*8] ; ldr r1,[base + i*8 + 4] ; adds r0,r4 ; blx r2` —
  the row's resolver is called with **r1 = the row's cid**.
- Every legible member of that section is a Standby-Phase card: Vampire Lord
  `0x1522`, Sacred Phoenix of Nephthys `0x185C`, Treeborn Frog `0x19CB`, Destiny
  Hero – Fear Monger `0x1A64` / Departed `0x1CF9` / Double Dude `0x1A62` /
  Captain Tenacious `0x1A03`, E-HERO Woodsman `0x1A48`, E-HERO Ocean `0x1A4D`,
  Drill Warrior `0x21CC`, Goka `0x1B08`, Arcana Force XVIII `0x1DA4`.

### `0x02256F7C` = the generic "once per turn, during your Standby Phase: you can …"
Disassembled this session. r5 = side/context (r0 in), r7 = r1 = **the registry
row's cid**. Turn-player gate, then `for zone in 0..4`:
`0x021AC004 / 0x021ABFA8 (side, zone, cid)` locates the card, bit 27 of
`[zone_struct + 0x44]` is the once-per-turn latch, then the offer is posted via
`0x021D3230(side, zone, 2, 0)` and `0x021D2A40(side, zone, 0x1B, 1)`.
**Fully data-driven — nothing about the cid is hardcoded.**
Riders: Goka `0x1B08` (reg 409), Mosaic Manticore `0x1B98` (411), E-HERO Woodsman
(416), E-HERO Ocean (417), **Captain Tenacious `0x1A03` (422)**, Arcana Force
XVIII (424), plus 7 inert phantom rows.

### Captain Tenacious `0x1A03` is the structural template for clause 3
Printed: "Once per turn, during your Standby Phase: You can target 1 'Destiny
HERO' monster in your Graveyard …; Special Summon that target."
- `cls1[533]` = `{+04 0x02207191, +08 0, +0C 0x021F03B5, +10 0x021E50DD,
  +14 0x02235605}`.
  `+0C` = the generic "is there a legal candidate in a list zone" predicate (the
  same one Release from Stone's slot3 uses); `+14` = the off-field list-zone
  target template; `+10` = the three-step "you can" confirm slot (state machine on
  `[r6+0x7C]`, calls the cls2 invoker `0x0224AD94` at step 0).
- criteria row 421 `{0x1A03, 0xFFFF, 0x0223F3E1, word 0x0}` — its bespoke handler
  is where "destroyed by battle since your last Standby Phase" lives. We replace
  the handler+word wholesale, so that restriction does not come along.

### "1 Normal Monster in your GY" is ONE criteria row: `{0x0223DE05, 0x00010002}`
In `0x022713C4`, handler `0x0223DE05` has exactly 6 rows; the 4 carrying word
`0x00010002` are Silent Doom `0x14F7`, Soul Resurrection `0x17B7`, Birthright
`0x1B65`, Swing of Memories `0x1C58` — i.e. 4/4 are printed "Special Summon 1
Normal Monster from your Graveyard". (The other two are Supervise `0x20F3`, same
word, whose GY effect is the same verb, and Knight of the Red Lotus `0x2113` with
a different word.) The handler forwards to `0x0223C4E8` with `r1 = row cid`,
`[sp] = row flags`, `[sp+4] = 0x1008`. **Two independent builds agree** (see the
3DS row above).

### `0x02207190`'s default arm is the right summon-position mode
`0x02207190` is a per-cid compare tree ending in `bl 0x02204730(desc, r4, r5)`;
r4 defaults to 1 and r5 to 2, and the per-cid arms only ever override r4/r5.
A symbolic walk (written this session; **no `[sp]`-held bases appear in the
routing path**, so the stack-switch footgun does not apply) routes:

| cid | card | r4 | r5 | printed position |
|---|---|---|---|---|
| `0x14F7` | Silent Doom | 1 | **1** | "in face-up **Defense** Position" |
| `0x1C58` | Swing of Memories | 1 | 2 | (unspecified) |
| `0x1A03` | Captain Tenacious | 1 | 2 | (unspecified) |
| `0x20F3` | Supervise | 1 | 2 | (unspecified) |
| **`0x1E9C`** | **the donor** | **1** | **2** | — |

The simulator reproduces the one card of the four whose printing specifies a
position, which is what makes r5 = position mode credible. The donor takes the
default, r5 = 2 = free choice — exactly what "Special Summon it" wants.

### Donor: Ally of Justice Light Gazer `0x1E9C`
Lv8 / DARK / Machine / 2400 / 1600, `card_type_encoded 37` (Synchro Effect
Monster — already correct), materials "1 Tuner + 1 or more non-Tuner monsters"
(the **generic** rule, so no named-material arm to unwind).

Vetted against the whole `donor_card_technique` checklist:
- zero records in cls0 / cls1 / cls2 / cls3
- no criteria-registry row, no effect-registry row
- absent from the Fusion recipe tables `0x02270B94` / `0x02270B58`
- absent from LIST_A `0x02275AB8` (so the "1 or more non-Tuner" form stays legal)
- claimed by no shipped patch
- **exactly one** u16-aligned occurrence in overlay 3 (`0x021B53A8`) and one in
  arm9 (`0x0209CBA2`) — both handled, see below
- English name slot **27 B** >= `len("Azure-Eyes Silver Dragon")` = 24

Rejected alternatives:
- **Naturia Leodrake `0x1FB7`** — cleaner still (ZERO ov3 occurrences, native
  Level 9, vanilla Synchro) but its English name slot is **16 B**: the name write
  would be silently skipped and the card would ship called "Naturia Leodrake".
- **Gaia Knight `0x1E11`** — 31 B name slot, but it is a Fusion material
  (table A row 154) and is named in the Synchro-material predicate region
  (`0x02249EBC`).
- No OTN Level-9 Synchro has a native Standby-Phase revive (checked: Field
  Marshal, Mist Wurm, Trishula, Gottoms, Scrap Twin, Locomotion, Hyper Psychic
  Blaster, Vylon Alpha — all different effects).

### The donor's two entanglements — both mapped by execution, not by reading

**D1 — the continuous ATK gain (ov3).** ⚠️ **CORRECTED mid-session.** The word
`0x1E9C` at `0x021B53A8` is NOT a droppable leaf reference: it is the **pivot of
an ordered binary-search tree**, and the arms below it are `base ± imm` off that
same register, so repointing it would mis-route every card in the subtree. The
consumer, found by scanning for the LDR-literal encoding directly (linear
disassembly desyncs on the interleaved pools):

```
021B516E  ldr r0,=0x1E9C
021B5170  cmp r2, r0
021B5172  bgt 0x021B51EA      ; upper subtree
021B5174  blt 0x021B517A      ; lower subtree, and r0 is ITS base (r0-0xB0, r0-0xEC, ...)
021B5176  bl  0x021B5B8C      ; cid == 0x1E9C  ->  Light Gazer's private bonus leaf
```

The tree's root is `0x021B4C38` (`movs r1,#2 ; ldrsh r2,[r7,r1]` — **r2 = the cid,
signed halfword from `[r7+2]`**), entry `0x021B4C3C`, extent
`0x021B4C00..0x021B5C00`. Executed concretely for every cid `1..0x26FF`:

- **default terminal = `bl 0x021B5E6E`** ("no continuous bonus"), reached by
  9857 / 9975 cids;
- **126 cids reach a non-default leaf, 110 of them real cards** — and every one is
  a printed "gains ATK for each X" card (Swamp/Lava Battleguard, Maha Vailo, Muka
  Muka, Insect Queen, Buster Blader, Dark Paladin, Amazoness Tiger, Batteryman AA,
  Mythical Beast Cerberus, Uria, Blue-Eyes Shining Dragon, …). That semantic
  agreement is what validates the simulator;
- **Goka `0x236B` → `bl 0x021B5DC4`**, its own private leaf — independently
  confirms the KB's "Goka is this engine's template";
- **`0x1E9C` → `bl 0x021B5B8C`, and it is the ONLY cid that reaches that leaf.**

So the donor's ATK gain is live and exclusively his. **Fix: retarget the 4 bytes
at `0x021B5176` from `bl 0x021B5B8C` to `bl 0x021B5E6E`** (`00f009fd` ->
`00f07afe`). Only cid `0x1E9C` can execute that instruction — it is the `==` arm
of the pivot compare. Proved closed by re-running the whole sweep on the patched
image: **exactly one cid changes terminal, `0x1E9C`, onto the default.**

**D2 — the archetype membership (arm9).** `0x1E9C` is entry 6 of the strictly
sorted 21-entry "Ally of Justice" set-code table at **`0x0209CB96`**, consulted
from **exactly one** site — the thunk at `0x02023B70`
(`ldr r1,=0x0209CB96 ; movs r2,#0x15 ; ldr r3,=0x02022E15 ; bx r3`), so the count
`0x15` is a hard-coded immediate and the table is packed against the Dragunity
table with a 0-byte gap. There is **no phantom cid anywhere in `0x1E94..0x1E9F`**
(every one is a real card), so the entry cannot be replaced by an inert cid in
place.

⚠️ **This is a composition problem, and both obvious removals abort the chain.**
`patch_elder_six_samurai` PART E **already edits this same table** — it removes
cid `0x1F1D` by shifting the tail left and decrementing the count immediate
`0x15 -> 0x14`, while *asserting the result is STRICTLY sorted* and *hardcoding 21*
as the count it expects to find. So:

| candidate fix | fails when |
|---|---|
| overwrite our slot with a duplicate neighbour `0x1E93` | Elder runs **after** us — its strict-sortedness assert trips |
| shift left + decrement the count to `0x14` | Elder runs **after** us — it hardcodes `0x15` |

Both were built and both tripped. **The fix that composes either way: shift the
tail left past the donor and refill the vacated LAST slot with a SENTINEL cid above
every real card — `0x2700` (the maximum real cid is `0x24E8`) — leaving the count
immediate untouched.** Same length, still strictly sorted, and the sentinel can
never match a card because no card carries that cid. Confirmed by building both
orders and running **both** patches' `verify()` on each: all four pass.

### Donor text slots (measured from the ROM's `bin2.pac`, card_prop index 2956)

| lang | e | f | g | i | s | j | k | r |
|---|---|---|---|---|---|---|---|---|
| name slot | 27 | 45 | 42 | 44 | 34 | 28 | **21** | 60 |
| desc slot | **116** | 152 | 130 | 119 | 137 | 138 | 120 | 242 |

`"Azure-Eyes Silver Dragon"` is 24 B, so the name lands in **7 of 8 languages** and
is **skipped in Korean** (21 B slot) — the helper keeps the donor's Korean name and
prints a note. The description budget is the **English 116 B**; the full
three-clause printing is ~200 B, so it ships truncated (115 B, all three clauses
named).

---

## Ruled Out

- **Implementing clause 3 on a Level-9 Synchro that already has the effect** —
  no such card exists in OTN (see the Level-9 Synchro sweep above).
- **Naturia Leodrake as donor** — 16-byte name slot (above).
- **Gaia Knight as donor** — Fusion material + material-predicate reference.
- **Inheriting Captain Tenacious's criteria handler `0x0223F3E1`** — it is the
  bespoke "destroyed by battle since your last Standby Phase" filter, not a
  generic one. Replaced wholesale by `{0x0223DE05, 0x00010002}`.
- **A cls2 record for the trigger** — not needed, and cls2 dispatch is known not
  to reach an Extra-Deck donor. The Standby offer is a zone scan driven from the
  effect registry, which is why an Extra-Deck monster is reachable at all.
- **Repointing the `0x021B53A8` literal** (the approach the plan called for) — it
  is the compare tree's pivot, not a leaf reference. Killed by reading its actual
  consumer at `0x021B516E`; replaced by the 4-byte `bl` retarget above.
- **Dropping `0x1E9C` from the Ally of Justice table by substituting a phantom** —
  no phantom exists in the required sort interval `0x1E94..0x1E9F`.
- **Duplicating the neighbouring member `0x1E93`** in its place, and separately
  **shifting left + decrementing the count** — each breaks a different assertion in
  `patch_elder_six_samurai` PART E, which edits the same table. Replaced by the
  shift-left + `0x2700` tail sentinel described above.

---

## Open Questions

- None. Clause 3 is in-game confirmed; the two static-only inferences below were
  settled by the test (see the Shipped section).
- Original note kept for provenance: none blocking the build. Everything the plan deferred to implementation time has
  been measured: text slots, the AoJ table geometry, and the stat-engine arm.
- Korean keeps the donor's name (21 B slot < 24 B). Accepted.
- The description ships truncated to 115 B of a ~200 B printing. The proper fix
  (append to `card_desc_<L>.bin` + repoint `desc_off`) is recorded in
  `patch_maiden_eyes_of_blue.py` as a standalone task and is NOT attempted here.

---

## Next Experiment

**In-game, normal duel (not a puzzle).** Synchro Summon the card with >= 1 Normal
Monster in the Graveyard, pass to your next Standby Phase, and observe:

1. the effect is offered at the start of **your** Standby Phase;
2. accepting opens a Graveyard picker listing **only Normal Monsters**;
3. the pick is Special Summoned and the **battle position is chosen by the player**
   (proves the r5 = 2 default arm);
4. it is offered at most **once** per Standby Phase (the `[zone+0x44]` bit-27 latch);
5. with no Normal Monster in the GY it is not offered at all;
6. the card's ATK reads a flat **2500** with LIGHT monsters in the opponent's
   Graveyard (proves the `0x021B53A8` repoint landed).

The two things only the emulator can settle are (a) that the `0x0228EB08` section
is walked specifically in the Standby Phase — inferred from 30/30 semantic
agreement across its members, not measured — and (b) that the resolver's
monster-zone scan admits an Extra-Deck-summoned monster.


---

## Shipped and IN-GAME CONFIRMED (2026-08-21)

Module `otn_enhanced/cards/azure_eyes.py`, build script
`_build_azure.py` -> `data/over_the_nexus/working/rom_azure.nds`.
**IN-GAME CONFIRMED on the first test (2026-08-21)** — all six oracle checks
passed:

1. offered at the start of the owner's Standby Phase;
2. the Graveyard picker lists **only Normal Monsters**;
3. the pick is Special Summoned with the **battle position chosen by the player**
   — which independently confirms the `r5 = 2` default arm read off statically;
4. offered at most **once** per Standby Phase (the `[zone+0x44]` bit-27 latch);
5. **not offered** with no Normal Monster in the Graveyard;
6. ATK reads a flat **2500** with LIGHT monsters in the opponent's Graveyard —
   the D1 arm retarget landed.

Checks 1 and 3 settle the two things static analysis could not: the
`0x0228EB08` section **is** walked in the Standby Phase, and the resolver's
monster-zone scan **does** admit an Extra-Deck-summoned monster.

Now wired into `apply_all_patches.PATCHES`, immediately after Maiden and
**below Elder of the Six Samurai** (they share the ARM9 Ally of Justice table).

| part | edit |
|---|---|
| A | effect registry `reg[341]` cid `0x16FE` -> `0x1E9C` (resolver `0x02256F7D` kept) |
| B | cls1 insert of Captain Tenacious's slots, count-neutral over phantom `0x1C27` (row 668 -> the donor lands at row 890) |
| C | criteria insert `{0xFFFF, 0x0223DE05, 0x0002, 0x0001}`, count-neutral over phantom `0x1ABE` (row 474 -> row 759) |
| D1 | `0x021B5176` `bl 0x021B5B8C` -> `bl 0x021B5E6E` |
| D2 | AoJ table: donor removed, tail shifted left, slot 20 = sentinel `0x2700` |
| E | card_prop LIGHT / Dragon / Lv9 / 2500 / 3000; name in 7 of 8 languages; 115 B description |

`verify()` = **PASS** (22 checks). `check_allocations` = clean.
`verify_knowledge` = **282 facts, 251 PASS, 0 FAIL** (was 246 PASS at session
start; the five new facts are all VERIFIED).

KB facts contributed: `timing.standby_phase_section`,
`timing.standby_offer_resolver`, `counter.normal_monster_gy_row`,
`dispatch.ss_from_list_position_mode`, `card.azure_eyes_silver_dragon`.

---
---

# CLAUSE 1 — "1 Tuner + 1+ non-Tuner Normal Monsters" (session 2026-08-24)

Scope this session: **clause 1 only** (the material restriction). Clause 3 (the
Standby-Phase revive) is shipped and in-game confirmed and **must not regress**;
clause 2 is a separate session (`PROMPT_azure_eyes_clause2.md`).

Text re-read from `scratch/ygoprodeck_cache.json` id 40908371 this session (not
from the prompt, not from recall):

> 1 Tuner + 1+ non-Tuner Normal Monsters
> If this card is Special Summoned: Until the end of the next turn, neither player
> can target Dragon monsters you currently control with card effects, also they
> cannot be destroyed by card effects. Once per turn, during your Standby Phase:
> You can target 1 Normal Monster in your GY; Special Summon it.

Clause 1 has two halves. Only the second is missing:

| half | status |
|---|---|
| "1 Tuner + 1 **or more** non-Tuner" (the count form) | **already correct** — the donor is absent from LIST_A `0x02275AB8`, and absence is what unlocks "N or more". LIST_A is NOT touched this session. |
| the non-Tuners must be **Normal Monsters** | **this session** |

`verify_knowledge` at session start: **282 facts, 251 PASS, 0 FAIL, 31 UNVERIFIED**
— matches the handoff exactly.

## Confirmed (this session, by disassembly of the clean `rom.nds`)

### The material subsystem has exactly three predicates, with two callers each

BL-scan over the whole overlay-3 image:

| predicate | called from |
|---|---|
| INNER `0x0224829C` | `0x022485D8` (inside OUTER) and `0x02248AAC` (inside THIRD) — nowhere else |
| OUTER `0x022485B4` | `0x02249CC8`, `0x02249D12` — both in the driver |
| THIRD `0x02248A88` | `0x02249C98`, `0x02249D96` — both in the driver |

The whole subsystem is closed over one driver function, and every path into the
inner predicate goes through either the outer or the third. That closure is what
makes the next fact a proof rather than a sample.

### THE OPEN QUESTION IS ANSWERED, STRUCTURALLY: the THIRD predicate never sees the Tuner

The driver (`0x02249C60`..`0x02249DA0`) splits on `0x02023068(synchro_cid)`, and the
material index lives at `[0x0229ABFC + 0x7C]`:

* **branch FALSE** (`0x02249CD4`) — `N = 0x02248280(synchro_cid)` (2 for `0x239F`
  and `0x24B2`, else **1**):
  * index `< N` → `0x021A1C7C(side, idx)` must be **non-zero** (IS a Tuner) →
    OUTER `0x022485B4`;
  * index `>= N` → per-Synchro switch `0x02249D1C` → for our donor the **generic**
    rule `0x02249D66`, which requires `0x021A1C7C == 0` / `0x02023110(cid) == 0`
    (**NOT** a Tuner) → THIRD `0x02248A88`.
* **branch TRUE** (`0x02249C78`) — index `0` requires `0x021A1C7C == 0` (not a
  Tuner) → THIRD; index `1` requires `0x02023138(cid) != 0` → OUTER; any other
  index is rejected outright.

**In BOTH branches the third predicate is entered only after the engine has already
proved the material is not a Tuner.** The only paths into `bl 0x02248A88` that skip
the Tuner check are the four hardcoded per-Synchro shortcuts at `0x02249D2C`
(cid `0x208E`), `0x02249D3C` (`0x21CB`), `0x02249D4C`/`0x02249D50` (`0x239D` /
`0x239F`) and `0x02249D56` (`0x211B`/`0x21CB`, `cmp r7,#2 ; blo`) — **none of them
is our donor `0x1E9C`**.

So a gate installed inside the third predicate is **non-Tuner-only by construction**.
No register archaeology at `0x022482B6`, no LR sniffing, and **no GDB session
needed** — the prompt's fallback ("accept the material if it is a Tuner *or* a
Normal Monster", which over-admits a second Tuner) is not required.

### Which branch our donor takes (settled, though it turns out not to matter)

`0x02023068(cid)` is `0x02022D70(cid) == 0xB`, and `0x02022D70` is a jump table on
`0x0202ABF8(cid)` (card_type >> 1) returning a category. Evaluated from the table
at `0x02022D88`: card_type `17`/`18`/`19` (every Synchro) → **category `0xA`**, and
only card_type `21` reaches category `0xB`. The donor's `card_type_encoded` is 37,
i.e. `>>1 = 18` → category `0xA` != `0xB` → **branch FALSE**, the ordinary
"Tuner first, then non-Tuners" path.

### `0x02023110(cid)` = "is this cid a Tuner", decoded

`t = 0x0202ABF8(cid)` (card_type >> 1); `t -= 15`; `t > 5` → return 0; else a
byte jump table at `0x02023128` (`04 04 08 08 04 04`) over `pc = 0x0202312A`:
`card_type>>1 ∈ {15,16,19,20}` → `0x0202312E` (**return 1**), `∈ {17,18}` →
`0x02023132` (return 0). So Normal Tuner / Tuner / Synchro Tuner are Tuners and
plain Synchros are not. `0x021A1C7C(side, idx)` wraps it: it reads the material's
cid from `0x0229AC94 + 0xB3C*(side&1) + 0x14*idx + 0x34`, tries `0x02023110`, and
falls back to the kind<6 rider walker `0x021A1430(side, idx, 0x1E40)` — i.e. "is a
Tuner, statically **or** by an attached rider".

### `0x0219CAE4(arg1, arg2, arg3)` returns the material's cid and is PURE

It is what the inner predicate uses to derive `r4`: at `0x022482AC` the inner calls
it with (arg1, arg2, arg3) and takes the result as the material cid. Disassembled
end to end (`0x0219CAE4`..`0x0219CBA2`): `r1 - 0xB <= 4` selects a 5-arm jump table,
otherwise the default arm at `0x0219CB82`. **Every arm is a single masked table read**
— `0x0229AC94 + 0xB3C*(side&1) + <zone offset> + idx*4` (zone offsets `0x124`,
`0x304`, `0x4E4` = the Extra Deck, `0x55C`, `0x7B4`) or `+ 0x14*idx + 0x34` — then
`lsls #0x12 / lsrs #0x12` and `pop {r4,pc}`. **There is not one store in the whole
function**, so calling it a second time with the same arguments is free and returns
exactly what the inner computed.

### The hook site is reached on the target path — already GDB-measured

`patch_shooting_quasar.py` records a live GDB trace of this very predicate during a
material-selection sweep:

> verdict of `0x02248A88` = 0 (REJECT) x364 hits, while **its INNER call returns 1**

That is `0x02248AAC` — the exact instruction this patch replaces — executing 364
times on the non-Tuner candidate path. Combined with `ov5_cave.py`'s note that
`0x022482B6` is GDB-confirmed to run for every material with the non-Tuners
arriving "via the third predicate `0x02248A88`", the reachability requirement in
CLAUDE.md is satisfied from recorded measurement; no new duel was burned.

### The hook site is FREE

`0x022482B6` is owned by Shooting Quasar (`CAVE_QSR_PRED`) and `0x022482B2` by
XX-Saber Boggart Knight, and the two chain — confirmed by reading both modules.
**This patch touches neither.** `0x02248AAC` is claimed by nobody: a repo-wide grep
returns zero hits, and the only Quasar edit *inside* the third predicate is PART E's
2-byte branch retarget at `0x02248CAA`, 0x1FE bytes away.

## Ruled Out

- **Chaining a third link onto `0x022482B6`** — the site already carries two hooks
  (Boggart `0x022482B2` → Quasar `0x022482B6` → `0x022482BC`), the only remaining
  4 bytes are the switch head itself, and a gate there would run for **every**
  material of **every** Synchro: the largest possible blast radius, across two
  shipped in-game-confirmed cards.
- **Distinguishing the Tuner at `0x022482B6` by the pushed LR at `[sp+0x1C]`** — it
  would have worked (the inner pushes `{r1-r7,lr}`, so the caller's return address
  is `0x022485DD` for the Tuner and `0x02248AB1` for a non-Tuner), but it is
  strictly worse than hooking the non-Tuner caller directly and it still needs a
  slot in the crowded site above.
- **Testing Tunerness on `r4` and admitting "Tuner or Normal Monster"** (the
  prompt's fallback) — unnecessary, and it would have over-admitted a second Tuner
  used as a non-Tuner material.
- **Adding the donor to LIST_A `0x02275AB8`** — that imposes "EXACTLY 1 non-Tuner"
  and would break the "1 **or more**" half that is already correct.

## Open Questions

- **Tokens.** `0x0202ABF8` gives a Token a card_type `>>1` of **10**, not 0, so the
  gate refuses Tokens as materials. By strict modern rulings a Token *is* a Normal
  Monster; this ships as a **deliberate, documented deviation** (see the module
  docstring). It needs a Level-9-total Synchro built out of Tokens to be observable.
- Whether the third predicate's own per-Synchro switch (base `0x219D` kept in
  `[sp,#0xc]` — the ungreppable stack-switch footgun) routes `0x1E9C` anywhere
  other than its generic accept. **Not simulated on purpose**; the in-game evidence
  is stronger: the card already Synchro Summons today with ordinary non-Tuners
  (2026-08-21 test), so that switch currently accepts them, and this patch only
  ever tightens.
- **Puzzles.** The gate is an ov5 stub, so it is inert (worse: the `bl` would land
  in evicted memory) in a puzzle, where overlay 41 replaces overlay 5. This is the
  repo's standing, accepted ov5 limitation and is *pre-existing* at this exact
  predicate — Quasar's `0x022482B6` and Boggart's `0x022482B2` hooks already carry
  it. No new class of risk; noted, not solved.

## Next Experiment

In-game, **normal duel** (ov5 stubs are not resident in a puzzle), ROM
`data/over_the_nexus/working/rom_azure.nds`:

1. 1 Tuner + Normal Monster non-Tuners totalling Level 9 → **summons**.
2. 1 Tuner + a non-Tuner **Effect** Monster totalling Level 9 → **refused** (the
   Effect Monster should not be selectable as the second material).
3. An ordinary **non-Normal Tuner** + Normal non-Tuners → **summons**. This is the
   case the structural proof above is about; if that proof were wrong, this is
   what would break.
4. **Two or more** Normal non-Tuners (e.g. Lv1 Tuner + 2 Lv4 Normals) → still
   summons — proves LIST_A was not touched.
5. **Regression:** clause 3 still offers in the Standby Phase; Shooting Quasar and
   XX-Saber Boggart Knight still Synchro Summon with their correct materials.

---

## BUILT (2026-08-24) — and IN-GAME CONFIRMED the same day (see the final section)

`patch_azure_eyes.py` **PART F**, build `_build_azure.py` ->
`data/over_the_nexus/working/rom_azure.nds`. The card is still deliberately held
out of `apply_all_patches` (its `PatchStep` stays commented out).

**The edit is 4 bytes of overlay 3 plus a 68-byte ov5 stub.**

| | |
|---|---|
| hook | `0x02248AAC` — the `bl 0x0224829C` the THIRD (non-Tuner) predicate makes into the inner one. Native bytes `fff7f6fb`. |
| stub | `CAVE_AZURE_NORMALMAT = 0x0239CFE0`, 68 B in a 0x50 reserve. `CAVE_FREE` bumped to `0x0239D030`. |
| test | `0x0202ABF8(material_cid) in {0, 15}` — Normal Monster / Normal Tuner. |
| scope | only when the Synchro's cid is `0x1E9C`; every other Synchro gets the inner predicate's own verdict, byte for byte. |

Stub, disassembled **out of the built ROM** (not from the assembler):

```
0239CFE0  f0b5  push   {r4,r5,r6,r7,lr}
0239CFE2  0c00  movs   r4, r1          ; arg1 side/context
0239CFE4  1500  movs   r5, r2          ; arg2 zone selector
0239CFE6  1e00  movs   r6, r3          ; arg3 index
0239CFE8  0700  movs   r7, r0          ; arg0 the SYNCHRO's cid
0239CFEA  bl    0x0224829C             ; the native verdict
0239CFEE  cmp   r0, #0
0239CFF0  beq   0x0239D01C             ; already rejected -> keep it
0239CFF2  ldr   r3, =0x00001E9C
0239CFF4  cmp   r7, r3
0239CFF6  bne   0x0239D016             ; other Synchro -> native verdict, r3 fixed
0239CFF8  movs  r7, r0                 ; stash the native verdict
0239CFFA  movs  r0, r4 / r1, r5 / r2, r6
0239D000  bl    0x0219CAE4             ; -> the material's cid (pure)
0239D004  bl    0x0202ABF8             ; -> card_type >> 1
0239D008  cmp   r0, #0     ; beq keep  ; 0  = Normal Monster
0239D00C  cmp   r0, #0xF   ; beq keep  ; 15 = Normal Tuner
0239D010  movs  r0, #0                 ; else REJECT
0239D012  b     0x0239D016
0239D014  movs  r0, r7                 ; keep: the engine's own verdict
0239D016  movs  r1, r4 / r2, r5 / r3, r6   ; the inner predicate's r1/r2/r3 contract
0239D01C  f0bd  pop    {r4,r5,r6,r7,pc}
```

Three details that would each have been a silent bug:

- **`POP {..,PC}`, never `POP {..,LR}`** (`thumb-pop-into-lr-footgun`). The pushed
  LR is what lands in PC.
- **r1/r2/r3 are re-established on every exit.** The inner predicate restores them
  from its own `push {r1-r7,lr}`, so the third predicate may rely on it; the donor
  path clobbers them via the two extra calls. This is why arg1/arg2/arg3 are saved
  before the call even though only the donor path reads them back.
- **`MOV Rd, Rs` on low registers is `LSL Rd, Rs, #0`** and sets flags — every
  `CMP` in the stub is placed so no `MOV` sits between it and its branch.

### Composition — measured, not asserted

A **whole-overlay-3 diff of the built ROM against clean** finds 154 changed runs
and **every single one lands inside a region this module claims** (cls1, criteria,
effect registry, the PART D1 arm, and PART F's 4 bytes). Zero unclaimed bytes.
Explicitly byte-identical to clean: `0x022482B2` (Boggart), `0x022482B6` (Quasar
PART I), `0x02248778` (Quasar PART D), `0x02248CAA` (Quasar PART E), `0x02249D26`
(Quasar PART F) and LIST_A `0x02275AB8`.

`verify()` = **PASS, 31 checks** (9 new for PART F, including that the cave holds
the stub byte-for-byte, that `assert_thumb1_only` accepts it, that both neighbour
hook sites are still native-or-their-owner's, and that the donor is still absent
from LIST_A). `check_allocations` clean, ledger refreshed.

### KB

`verify_knowledge`: **287 facts, 256 PASS, 0 FAIL, 31 UNVERIFIED** (was 282 / 251 /
0 / 31). Five new VERIFIED facts, no regressions:

- `synchro.third_pred_is_the_nontuner_caller` — the closure proof above, with the
  BL-scan and both driver Tuner-gates as its executable proof. **This is the
  reusable one**: it is how any "N non-Tuner *\<type\>* Monsters" clause gets built.
- `synchro.nontuner_gate_hook` — `0x02248AAC`, its register contract, and why not
  `0x022482B6`.
- `synchro.is_tuner_predicate` — `0x02023110` decoded, jump table and all, plus the
  runtime wrapper `0x021A1C7C`.
- `synchro.material_cid_lookup_is_pure` — `0x0219CAE4`, with purity proved by
  scanning its whole extent for store opcodes (there are none).
- `synchro.required_leading_material_count` — `0x02248280`.

`card.azure_eyes_silver_dragon` updated: clause 3 still marked in-game confirmed,
clause 1 marked **built and statically verified, NOT yet in-game confirmed**.

### One doc bug fixed on the way

`apply_all_patches._apply_azure_eyes` said the step was "Pure DATA — no injected
code and no ov5 cave slot, so it is puzzle-safe". PART F makes that **false**, so
it now says so explicitly.

---

## IN-GAME CONFIRMED (2026-08-24) — clause 1 shipped, on the FIRST test

Reported by the user against `rom_azure.nds`:

| oracle | result |
|---|---|
| 1. 1 Tuner + 1 non-Tuner **Normal** Monster | **summons** ✅ |
| 2. 1 Tuner + 1 non-Tuner **Effect** Monster | **refused** ✅ |

Those two together are the pair that matters: the gate **fires** (oracle 2 — a
material the engine used to accept is now rejected) and it **discriminates**
(oracle 1 — the tightening is not blanket). PART F is correct on the live path,
so `synchro.third_pred_is_the_nontuner_caller` is now backed by behaviour and not
only by the static closure proof.

Clause 3 was likewise confirmed on its first test (2026-08-21). Both shipped
clauses landed first-time — the mapped subsystem is what paid, exactly as with
Darkflare after Lightpulsar.

### What is confirmed vs. inferred — do not blur these

**Confirmed:** oracles 1 and 2 above.

**Inferred, not measured:** oracle 3 (an ordinary **non-Normal Tuner** + Normal
non-Tuners). The Tuner used in oracle 1 was not recorded. Only **5 cards in the
game are Normal Tuners** (`card_type >> 1 == 15`), so the successful summon
almost certainly ran with an ordinary Effect Tuner — which is precisely the case
the design hinges on, since a naive "every material must be Normal" gate would
have refused it. Very likely already proven in passing; worth one line of
confirmation rather than an assumption.

**Untested, low risk:** oracle 4 (two or more Normal non-Tuners, i.e. the "1 OR
MORE" form). `verify()` asserts statically that the donor is still absent from
LIST_A, which is the mechanism that grants it.

**NOT TESTABLE ON THIS ROM:** oracle 5's Shooting Quasar / Boggart Knight
regression. `rom_azure.nds` is a single-card build from clean `rom.nds` and
contains **neither** of those patches. For now that composition is covered by the
whole-overlay diff (PART F changes exactly 4 bytes; both cards' hook sites are
byte-identical to clean). It becomes a real in-game check only when the card is
wired into `apply_all_patches` — which is deliberately still deferred until
clause 2 lands.

### State after this session

- `patch_azure_eyes.py` — clauses 3 + 1, `verify()` PASS (31 checks).
- Still **held out of `apply_all_patches`** on purpose, so the clause-2 session
  keeps iterating on the cheap single-card ROM.
- KB: **287 facts, 256 PASS, 0 FAIL, 31 UNVERIFIED**.
  `card.azure_eyes_silver_dragon` now records clause 1 as in-game confirmed, with
  the confirmed/inferred split above stated explicitly.
