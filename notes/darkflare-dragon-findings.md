# Darkflare Dragon — findings

Session 2026-08-05. Card: **Darkflare Dragon** (YGOPRODeck id 25460258).
User directive: **map all clauses; Normal-Monster donor; trampoline the effects on.**

> ## ▶ STATUS 2026-08-17: UNPARKED. Lightpulsar is COMPLETE (all 3 clauses in-game
> ## confirmed), so Darkflare is unblocked. See
> ## [§ Session 2026-08-17](#session-2026-08-17--clause-1-planning) at the bottom —
> ## the donor and every clause-1 edit are now measured, and the 2026-08-05 body
> ## below is superseded on TWO points (the donor, and "take any remaining dead arm").

> ## ⏸ STATUS: PARKED — do Lightpulsar Dragon FIRST
>
> Decided by the user 2026-08-05. **This card is sequenced AFTER Lightpulsar
> Dragon** (`notes/lightpulsar-findings.md`); the plan below is complete and is to
> be enacted once Lightpulsar lands. Nothing is built and **nothing is claimed in
> the allocation ledger** — deliberately, so Lightpulsar can claim first.
>
> **Why the order matters (not just preference):** Lightpulsar's clause 1 is
> Darkflare's C1 *word for word* — "You can Special Summon this card (from your
> hand) by banishing 1 LIGHT and 1 DARK monster from your GY." Both cards need:
> - the same two criteria rows (`0x01000002` LIGHT + `0x02000002` DARK, handler `0x0223CA11`),
> - the same effect-registry handler `0x0226292D`,
> - and the **same routing edit** at the hand-SS tree compare `0x0225E8DA` -> leaf `0x0225FA46`.
>
> **So when Lightpulsar is built, build the routing stub to take a LIST of cids,
> not one.** A stub that hardcodes a single donor cid will have to be rewritten
> for Darkflare; a 2-3 entry cid list costs nothing extra and makes Darkflare a
> data-only follow-up. Same for the GDB work: **`0x0225CF28(cid)`'s fall-through
> value (Next Experiment #1) answers both cards at once** — measure it during the
> Lightpulsar session and Darkflare inherits the answer for free.
>
> **On resuming Darkflare:** re-read this file's Confirmed section against the
> then-current `otn_enhanced/docs/engine/*.yaml` (the YAML wins on any disagreement), re-run
> `check_allocations` to see what Lightpulsar claimed, and re-pick the donor only
> if Lightpulsar took `0x16EF`.

Authoritative text (`scratch/ygoprodeck_cache.json`, NOT recall):

> You can Special Summon this card (from your hand) by banishing 1 LIGHT and 1
> DARK monster from your GY. Once per turn: You can send 1 Dragon monster from
> your hand and 1 Dragon monster from your Deck to the GY, then target 1 card in
> either GY; banish that target.

Level 5, DARK, Dragon, Effect Monster, ATK 2400 / DEF 1200.

## Clause split

- **C1** — optional hand SS by banishing 1 LIGHT + 1 DARK monster from your GY.
  Not a nomi (may still be Tribute Summoned).
- **C2** — OPT ignition COST: send 1 Dragon from **hand** + 1 Dragon from **Deck** to GY.
- **C3** — payload: target 1 card in **either** GY; banish that target.

## Confirmed (this session)

### Card / KB status
- **Darkflare is absent from the ROM** (0 name hits / 4305 cids) and has no prior
  work in the repo (grep: only the card DBs mention it). Full donor build.
- **KB is healthy.** `verify_knowledge` default run = 159 PASS / **2 FAIL** / 29 UNVER;
  the 2 FAILs (`ram.graveyard_and_banished_arrays`, `ram.card_instance_record`) are
  both `oracle: savestate` and PASS against
  `--savestate data/over_the_nexus/working/sealancer_recon.ml3` (**162 PASS / 0 FAIL**).
  The default savestate `rom_all_patches.ml2` is a bad input for them, **not** KB rot.
- Allocation ledger clean: 85 ov5 slots (76 live), 29 phantoms, no overlaps.
  `ov5_cave.CAVE_FREE = 0x0239C014`.

### C1 — the "Special Summon by banishing from your GY" procedure is FULLY TABLE-DRIVEN
Found by intersecting refs to the 3 chaos cids (0x16C9 Chaos Sorcerer, 0x16CB
BLS-Envoy, 0x16E4 CED-Envoy) across ov3+arm9. Two structures, **no per-card code**:

1. **Effect-registry row** `{u32 cid, u32 handler}` @ `0x0228E1E0` stride 8.
   Handler **`0x0226292D` = the SS-by-banishing-from-GY procedure**. Exactly
   **32 cids** share it and every one of their texts is "Special Summon this card
   by banishing/removing N <filter> from your Graveyard" — incl. the OPTIONAL
   (non-nomi) ones: Master Hyperion 0x2447, Spell Striker 0x1BB5, Gaia Plate
   0x1D86, Knight of the Red Lotus 0x2113, Dragunity Arma Leyvaten 0x2356.
2. **Criteria-registry rows**, ONE PER MATERIAL GROUP, in `dispatch.criteria_registry`
   @ `0x022713C4` stride 12, layout `{+0 u16 cid, +2 u16 aux, +4 Thumb handler, +8 u32 criteria}`:
   | card | rows |
   |---|---|
   | CED 0x16E4 | crit[261] `0x01000002` (LIGHT) + crit[262] `0x02000002` (DARK), handler `0x0223CA11` |
   | Chaos Sorcerer 0x16C9 | crit[253] `0x01000002` + crit[254] `0x02000002` |
   | BLS 0x16CB | crit[255] `0x01000002` + crit[256] `0x02000002` |
   | Frost & Flame 0x1C2A | `0x03000002` (WATER) + `0x04000002` (FIRE) |
   | Spell Striker 0x1BB5 | ONE row `0x00000004` (a Spell, not a monster) |
   Criteria top byte = `race<<3 | attr` (KB `dispatch.criteria_word_race_attribute`):
   attr 1=LIGHT, 2=DARK. So **CED's two rows ARE C1 verbatim.**

- **DECISIVE — no cls record is needed for C1.** Spell Striker 0x1BB5 has a reg row
  + exactly ONE criteria row and **no cls0/1/2/3 record at all**, and its only
  printed effect is the SS procedure. The cls3 records that CED / Frost & Flame /
  Master Hyperion carry belong to their *other* (once-per-turn) effects.
  => **C1 = 1 reg row + 2 criteria rows. Pattern A, no ov5, no Thumb, puzzle-safe.**

### C2 / C3 — every piece exists natively
Criteria handlers decoded by their users (all `dispatch.criteria_registry` rows):
| handler | meaning | witness |
|---|---|---|
| `0x0223CA11` | GY monster as SS material | the chaos cards |
| `0x0223CB65` | **send 1 Dragon from HAND to GY** | Vanguard of the Dragon 0x1FFE crit[885] `0x08000002` (race 1 = Dragon); Genesis Dragon 0x1F2A crit[792] same |
| `0x0223CAD9` | **send from DECK to GY** | Foolish Burial 0x1474 crit[138] `0x00000002` (any monster); Dragunity Tribus 0x20C6 crit[978] `0x088C0002` (Lv<=3 Dragon) |
| `0x0223D6E1` | **target a monster in EITHER GY** | Zombie Master 0x1C2F crit[561] `0x10910002` (race 2 = Zombie) |
| `0x0223D6FD` | **banish 1 CARD from a GY** | Disappear 0x1515 crit[174] `0x0001000E` (opponent's GY) |

- **Zombie Master 0x1C2F is the structural twin of C2+C3**: "Once per turn: You can
  send 1 monster from your hand to the GY, then target 1 <filter> monster in either
  GY; **Special Summon** that target." Its cls3[321] @0227BB8C =
  `slot1=02207191 slot2=0 slot3=021FC99D slot4=021EAC0D slot5=02235605`.
  slot5 `0x02235605` is the KB's off-field (list-zone) target template
  (`dispatch.offfield_picker_sequence` 0x02235604) — the one that CAN read GY.
  Deltas vs Darkflare: send filter any->Dragon; add the 2nd (Deck) send; target
  filter Lv<=4 Zombie monster -> any CARD; action Special Summon -> banish.
- **D.D. Crow 0x1B44 IS in the ROM** — the exact C3 wording ("target 1 card in
  either GY; banish that target"). Not yet dumped; the prime C3 donor of slots.
- Criteria byte1 is a Level cap (`0x8C` = Lv<=3, `0x90/0x91` = Lv<=4, per KB
  Coelacanth/Deep Sea Diva anchors); low byte 0x02 = monster, 0x04 = Spell,
  0x0E = any card (Disappear).

### Structure geometry (for count-neutral inserts)
- criteria registry: base `0x022713C4`, count `0x56C` (1388), stride 12, sorted by cid,
  binary-searched by `0x02243B9C`.
- cls tables: cls0 `0x0227E64C`/0x51A, cls1 `0x022860D4`/0x535,
  cls2 `0x02275C04`/0x2B9, cls3 `0x02279D74`/0x308, stride 24, cid-first.
- effect registry: base `0x0228E1E0`, stride 8.

### C1 routing — the hand-SS cid TREE (corrects the "pure data" reading above)
The KB gained `handss.banish_cost_leaf` (VERIFIED, source `lightpulsar-findings`)
mid-session, and it corrects my earlier conclusion. Disassembled and **independently
re-confirmed this session** at 0x0225E8A0..0x0225E8E4 (base `r7 = 0x16C6` Fenrir):

```
0225E8A0  adds r1,r7,#0 ; adds r1,#0x92   ; = 0x1758  upper guard
0225E8A6  bgt  0225E8E8                    ;  cid > 0x1758 -> other subtree
0225E8B0  adds r0,r7,#3 ; cmp r4,r0        ; = 0x16C9 Chaos Sorcerer
0225E8B4  bgt  0225E8CE ; bge 0225E8E0     ;  == -> LEAF
0225E8CE  adds r0,r7,#5 ; cmp r4,r0        ; = 0x16CB BLS-Envoy
0225E8D2  bgt  0225E8DA ; beq 0225E8E0     ;  == -> LEAF
0225E8DA  adds r7,#0x1e ; cmp r4,r7        ; = 0x16E4 CED-Envoy
0225E8DE  bne  0225E8E4                    ;  != -> bl 0225FF96 (REJECT)
0225E8E0  bl   0225FA46                    ; <== the LIGHT+DARK leaf
```
- Leaf `0x0225FA46` is **generic in the cid** — it loops param 0 then 1 through
  `0x02243FE0(side, cid, param)` (the criteria registry) and compares each hit
  count against `0x0225CF28(cid)`. So the per-card data is entirely the criteria rows.
- **=> C1 is NOT pure data.** The donor cid must be ROUTED to `0x0225E8E0`.
  A records-free Normal Monster is never named in this tree, so it hits the `bne`
  reject at `0x0225E8DE`. This is exactly where the user's trampoline belongs.

### Donor selection
- **220 fully records-free Normal Monsters** (absent from all four cls tables AND
  the criteria registry AND the effect registry — per `dispatch.cls_tables`, all four
  must be searched).
- **Best stats match: Curse of Dragon `0x0FCD`** — DARK / Dragon / **Level 5**,
  2000/1500. Attribute, race and Level already correct for Darkflare; only ATK/DEF
  + name need `card_prop` edits. Unclaimed by any shipped patch.
  ⚠️ **But cid 0x0FCD is far below the tree window** (0x16C6..0x1758), so it enters a
  different subtree entirely — routing it needs a full trampoline.
- **Better for C1: an IN-WINDOW donor.** Records-free Normal Monsters with cid in
  `(0x16CB, 0x1758]` — these already fall through to the `0x0225E8DA` compare, so
  routing is a **local 2-compare edit** instead of a trampoline:
  | cid | name | stats |
  |---|---|---|
  | **0x16EF** | **Giga Gagagigo** | WATER Reptile **Lv5** 2450/1500 |
  | 0x16F0 | Mad Dog of Darkness | **DARK** Beast Lv4 1900/1400 |
  | 0x16F2 | Sea Serpent Warrior of Darkness | WATER Sea Serpent Lv4 1800/1500 |
  | 0x173A | Gogiga Gagagigo | WATER Reptile Lv8 2950/2800 |
  | +0x16F1, 0x16F4, 0x173D | | |
  **0x16EF Giga Gagagigo is the pick**: already Level 5, cid only 0x0B above CED's
  0x16E4, so the routing edit is `beq leaf / adds r7,#0x0b / cmp / bne reject`.
  That does not fit in the 4 halfwords available in place, so it wants a small
  **ov3-cave stub** (132 B free per `check_allocations`) — and ov3 is resident in
  puzzles (`mem.ov3_resident_all_modes`), so this stays puzzle-safe where ov5 would not.

### C3 template — D.D. Crow 0x1B44 is the exact wording
"(Quick Effect): You can discard this card to the GY, then target 1 card in your
opponent's GY; **banish that target**."
- crit[495] `{0x1B44, 0xFFFF, handler 0x0223D6FD, criteria 0x0001000E}`
- cls2[244] `slot1=02208D19 slot2=0 slot3=021FBDF5 slot4=021E6FD9 slot5=02235A4D`
- **slot1 `0x02208D19` = the BANISH-the-target resolver** — shared by D.D. Crow,
  Kycoo 0x1480 and Disappear 0x1515. That is C3's action, free.
- **slot5 `0x02235A4D` = the GY target-declaration step** (same three cards).
- criteria `0x0001000E`: low byte `0x0E` = ANY CARD (vs `0x02` monster-only, which
  is what Kycoo's `0x00010002` uses); byte2 `0x01` = opponent's side.
  "Either GY" needs that side field widened — Zombie Master 0x1C2F proves either-GY
  is expressible (handler 0x0223D6E1, `0x10910002`).

## Ruled Out

- **Using a chaos card (0x16E4/0x16C9/0x16CB) as donor** — user directed a Normal
  Monster instead; also each is a marquee card that would be consumed.
- **"C1 needs no code at all"** — MY OWN EARLIER READING, now WRONG. Spell Striker's
  minimal footprint (reg row + 1 criteria row, no cls record) is real, but it only
  shows the *data* is minimal; the cid still has to reach the tree leaf. Kept here so
  the correction survives.
- **The 59-cid ov3 u16 list @0x0227134C is NOT the nomi list** — it mixes Fusion
  spells (Polymerization, Power Bond, Super Poly), Gladiator Beasts and Assault
  Mode monsters with the chaos cards. Purpose unknown; not needed for C1.

## Open Questions

- **What enforces nomi?** The arm9 sorted u16 list @`0x0209BE2C` (55 entries,
  zero-terminated) is 50/55 nomi-by-text and contains all 3 chaos cards, while
  every OPTIONAL "you can SS by banishing" card (0x2447, 0x1BB5, 0x1D86, 0x2113,
  0x2356) is **absent** — but **Frost & Flame 0x1C2A is nomi by text and also
  absent**, so this list is not a complete nomi registry. UNRESOLVED.
  *Not blocking*: we want NON-nomi and we only ever ADD rows, so we inherit nothing.

  WARNING — **RESOLVED 2026-09-01. See the KB fact
  `dispatch.summon_restriction_classifier` (`otn_enhanced/docs/engine/cards.yaml`) and
  `notes/white-dragon-ninja-findings.md`.** `0x0209BE2C` is one of **four**
  sorted lists read by the classifier `0x020231C8(cid)`, which returns a class
  code 1..4: `0x0209BE2C` (55), `0x0209BE9C` (57), `0x0209BA12` (3),
  `0x0209BC14` (29). The "false negatives" above are simply members of the other
  lists — **Frost & Flame `0x1C2A` is a class-2 member**. The classifier is
  reached from `0x020232AC`, which `0x021BA6DC` calls inside the Special-Summon
  legality chain `0x021BA69C`. Class 3 (`0x0209BA12` = Harpie Lady Sisters, Wall
  Shadow, phantom `0x1534`) is the "Special Summon ONLY with one specific named
  card" class and has a free slot. Still open: whether class membership also
  blocks an *effect-driven* summon.
- Where is the material **count** encoded? Frost & Flame's "1 FIRE and 2 WATER"
  has two criteria words identical in shape to CED's 1+1. Not blocking (C1 needs 1+1
  = CED exactly), but unknown.
- Does the criteria byte1 bit 0 mean "both sides" (Zombie Master `0x91` either-GY vs
  Coelacanth `0x90` own-Deck)? Needed for C3's "either GY". UNVERIFIED.
- Is the effect-registry (0x0228E1E0) count hardcoded anywhere (does adding a row
  need a count bump / phantom drop)? Not yet checked.

- **Criteria-row INDEX collision across clauses.** `dispatch.multi_attribute_summon_cost_is_multiple_rows`
  proves a cid's criteria rows are selected by `param` = **the row index among that
  cid's rows**. C1's leaf hardcodes param 0 and 1. So C1's LIGHT/DARK rows must be
  rows 0 and 1, and C2's two send-rows plus C3's target-row must sit at 2/3/4 and be
  indexed by their own slot4/slot5 code (which gets param from `0x02234E78(desc)`).
  Whether those consumers can be pointed at a nonzero param is **UNVERIFIED** and is
  the main cross-clause risk on this card.
- ⚠️ **Parallel session on Lightpulsar Dragon** (`notes/lightpulsar-findings.md`)
  shares C1 **verbatim** ("banishing 1 LIGHT and 1 DARK monster from your GY") and is
  also pre-build. Both cards would claim criteria rows, a reg row, phantom cids, and
  the same tree-routing edit at 0x0225E8DA. **Coordinate before either builds** — the
  routing stub should be written once and shared (two cids -> one leaf), not twice.

## Next Experiment

The two blockers are both about `0x0225CF28` and the routing; neither is buildable yet.

1. **`0x0225CF28(cid)` fall-through value — the gating unknown.** It is the
   required-count function the leaf compares against. Disassembly shows it is a
   compare tree ending in a **PC-relative jump table** at 0x0225CF60..0x0225CF72
   (`adds r1,#0x1d; subs r1,r0,r1; cmp r1,#4; bhi; add r1,r1,r1; add r1,pc;
   ldrh r1,[r1,#6]; add pc,r1`). Per `thumb.stack_switch` a register-only simulation
   of this shape reports the WRONG leaf — **measure it with GDB**, do not infer:
   breakpoint at `0x0225CF28`, force r0 = the donor cid (0x16EF), continue to return,
   read r0. If it returns **1**, C1 needs no edit here at all; if **0**, the cost
   check passes vacuously (free summon) and the tree needs a count arm added.
2. **Prove the routing.** Breakpoint `0x0225E8DA` and `0x0225E8E0` with the donor in
   hand during a normal duel; confirm the donor cid reaches the compare and currently
   takes the `bne` reject. That is the evidence CLAUDE.md requires before any build.
3. Only then: claim an ov3-cave slot for the 2-compare routing stub, add the criteria
   rows count-neutrally (drop phantoms), add the reg row, and edit `card_prop`.

**Nothing has been built and nothing is claimed in the ledger.** Per CLAUDE.md
(*No Blind Build-Test Cycles*) items 1 and 2 are `unproven` and must be settled on the
emulator first — both fit in ONE GDB session (the stub is one-shot; plan the whole
experiment offline, arm both breakpoints, collect in a single wait window).

---

# Session 2026-08-17 — clause 1 planning

Scope as given: *"continue implementing Darkflare Dragon"* + *"produce modified
versions of the ROM which include Eclipse Wyvern and Lightpulsar Dragon"*.
**No ROM bytes written for Darkflare yet** — clause scope awaiting confirmation.

## Confirmed (this session)

### Inherited state re-verified
- KB healthy: `verify_knowledge --savestate .../sealancer_recon.ml3` =
  **239 facts, 210 PASS, 0 FAIL, 29 UNVERIFIED**.
- Allocation ledger clean: 95 ov5 slots (86 live), 46 phantom claims, 6 ov3
  dead-code claims (94 B free), no overlaps, ledger in sync.
- Card text re-read from `scratch/ygoprodeck_cache.json` id 25460258 — **identical**
  to the 2026-08-05 quote. DARK / Dragon / Level 5 / 2400 / 1200.

### 3DS FIRST (the second source of truth), before any NDS disassembly
`... -m otn_enhanced.tools.threeds_lookup "Darkflare Dragon"` -> 3DS index 5003,
**cid `0x26E4`** (same cid space as the NDS):

| registry | rows |
|---|---|
| `main_effect` (== NDS criteria registry) | `[1569] FFFF 26E4 004B1C5C 08000002` · `[1570] FFFF 26E4 004B1BE8 08000002` · `[1571] FFFF 26E4 004A71E4 0001000E` |
| `summon_cond` (~ NDS summon-procedure registry `0x0228F158`) | `[193] cid 26E4 flag 1 handler 004B509C +8=0 +C=004B86D8` |

Two consequences, both decisive:

1. **Darkflare's summon-condition row is byte-identical to Chaos Sorcerer's**
   (`0x004B509C`, `+8 = 0`) — the row Lightpulsar needed its OWN handler for. So
   clause 1 is the *plain* banish-cost procedure, i.e. NDS handler `0x0226292D`,
   exactly the one `patch_lightpulsar` PART G installs.
2. Clause 1 owns **no criteria row** in the 3DS either (same as Lightpulsar); the
   three rows are clause 2/3 (two Dragon send-rows `0x08000002`, one
   any-card-in-a-GY row `0x0001000E` — the Disappear / D.D. Crow word).

### CORRECTION to the 2026-08-05 plan: "take one of the 3 remaining dead arms" is WRONG
`handss.dispatch_dead_arms` lists four dead arms and says three remain. Measured
this session with a full **Thumb interpreter for the BST** (models the stack AND
the compiled jump tables, per `thumb.stack_switch`; it reproduces every published
fact — Chaos family -> `0x0225FA46`, Fenrir -> `0x0225FA36`, each dead arm's exact
phantom set), the three are **not interchangeable**, because an arm can only be
retargeted at cids that (a) actually REACH its guard and (b) lie within
`base +/- imm8` of that guard:

| arm (BL) | guard | cids reaching the guard | usable window | clean Normal-Monster donors in it |
|---|---|---|---|---|
| `0x0225E67C` | `subs r0,#0x8d` @`0x0225E676` | `0x0001..0x0E1E` | `0x0DA6..0x0E1E` | **0** — the window is entirely Speed Spells + phantoms |
| `0x0225E692` | `subs r0,#0x66` @`0x0225E68C` | `0x0E20..0x0E3F` | same | **0** |
| `0x0225E88E` | `subs r0,#0x7a` @`0x0225E888` | `0x1579..0x164C` | `0x15C7..0x164C` | **6** |

So there is exactly **ONE** usable arm left for a monster donor: **`0x0225E88E`**,
guard `0x0225E888`, base `r7 = 0x16C6` (Fenrir).

### AND THAT ARM IS ALREADY WRITTEN BY `patch_lightpulsar` (PART D)
Lightpulsar neutralises `0x0225E692` and `0x0225E88E` -> the reject leaf
`0x0225FF96`, so that its 126 B ov3 cave at `0x0225F240..0x0225F2BE` is
unreachable; `patch_lightpulsar.verify()` asserts exactly that.
**Substantively this is not a conflict** — repointing `0x0225E88E` at the cost leaf
`0x0225FA46` leaves the cave just as unreachable (nothing branches to
`0x0225F240` either way). It is the *guard wording* that must be relaxed, from
"points at the reject leaf" to the invariant that actually matters, "does not
point into the cave".

### The six candidate donors (all six vetting filters + every cid-keyed table)
Records-free Normal Monsters that reach the REJECT leaf, own no cls0-3 record, no
criteria row, no summon-procedure row, are in neither membership list, are neither
fusion material nor fusion result, and are unclaimed in the ledger. Additionally
checked clean against the effect registry `0x0228E1E0`, the equip ATK/DEF table
`0x0226DFB0`, the three battle-attribute lists, the leave-mask table `0x0226EC1C`,
list30, the ARM9 nomi list `0x0209BE2C`, the GY-action registry `0x0228DDF8` and
Synchro LIST_A:

| cid | name | printed | note |
|---|---|---|---|
| `0x1609` | Great Angus | FIRE Beast Lv4 1800/600 | |
| `0x160A` | Aitsu | FIRE Fairy Lv5 100/100 | **AVOID** — Koitsu `0x1620` and Doitsu `0x1917` both ship, and both are "equip only to 'Aitsu'"; that restriction's mechanism is unlocated, so converting Aitsu risks two other cards |
| `0x160B` | Sonic Duck | WIND Winged Beast Lv3 1700/700 | least-referenced of all (3 raw occurrences ROM-wide) |
| **`0x160C`** | **Luster Dragon** | **WIND Dragon Lv4 1900/1600** | **RECOMMENDED** — already Dragon race, so the retune is attribute + level + ATK/DEF only |
| `0x1646` | Battle Footballer | FIRE Machine Lv4 1000/2100 | |
| `0x1649` | Acrobat Monkey | EARTH Machine Lv3 1000/1800 | |

### PART B must move — Lightpulsar's count edit does NOT cover this donor
`0x0225CF28(cid)` simulated across the cid space (self-validating: Fenrir -> 2,
Chaos family -> 1, Dark Necrofear -> 3, all matching the printed texts):

- donor `0x160C` currently returns **0**, via the branch **`0x0225CF8C`**
  (`b 0x0225D09C`) — a DIFFERENT site from Lightpulsar's `0x0225CF5E`, so the two
  cards do not collide here.
- Retarget `0x0225CF8C` -> `0x0225D06A` (`movs r0,#1 ; bx lr`). Blast radius,
  **measured not assumed**: 601 cids take that branch (454 real cards, range
  `0x1467..0x16C4`); **0 of them have a nonzero count today**, and **0 of them
  reach a banish-cost leaf**, so none can observe the change. After PART A the
  only cid in that set that reaches one is the donor.
- 4 cids (`0x1BC8` `0x1BC9` `0x1C2A` `0x1C2B`) the count simulator could not
  decide; all lie above `0x16C4`, i.e. outside this branch, so they do not affect
  the conclusion. Noted rather than glossed.

## Ruled Out (this session)
- **Curse of Dragon `0x0FCD`** (the 2026-08-05 recommendation). It is outside every
  remaining arm's window — the same class of error that disqualified Armored Lizard
  for Lightpulsar.
- **Arms `0x0225E67C` / `0x0225E692`.** Their windows contain no monster at all.
- **Aitsu `0x160A`** as donor — Koitsu and Doitsu both name it.

## Open Questions
1. **The payment stubs are single-cid.** `patch_lightpulsar`'s PARTS E/F stubs in
   the ov3 dead run test `r0 == 0x0FB1`. Darkflare needs the same two dispatches to
   accept its donor too, and there is only ONE BL hook at each dispatch root. The
   2026-08-05 note anticipated this: *"build the routing stub to take a LIST of
   cids"*. 46 B of the 126 B run are free — enough for a second cid on both stubs
   (~20 B) — but it means **re-emitting code that a shipped, in-game-confirmed card
   owns**. Design decision, not yet made.
2. Clause 2/3's three criteria rows need the rowhook mechanism
   (`CAVE_LP_ROWHOOK` is Lightpulsar's, in ov5) or an equivalent — unexamined this
   session.

## Next Experiment
Clause 1 is fully mapped and needs **no emulator work before building**: every
part is either measured here or a verbatim replay of Lightpulsar's shipped,
in-game-confirmed recipe. The in-game test IS the experiment:

1. hold the donor in hand with a LIGHT and a DARK monster in your GY -> the SS
   option must appear;
2. with an EMPTY GY -> it must NOT appear (this is what failed twice on Lightpulsar);
3. take the summon -> it must prompt for a LIGHT, then a DARK, and BANISH BOTH
   (test 2 on Lightpulsar looked correctly gated yet paid nothing — that is the
   symptom that means PART G is missing).

## Also this session (unrelated to Darkflare)
`_build_ew_lp.py` -> `data/over_the_nexus/working/rom_ew_lp.nds`: Eclipse Wyvern +
Lightpulsar Dragon chained onto the clean ROM, both `verify()` clean against the
final image. It auto-chains Darkflare too once `patch_darkflare.py` exists.

---

# ✅ BUILT — CLAUSE 1 (2026-08-17)

`otn_enhanced/cards/darkflare.py`, registered in
`apply_all_patches.PATCHES` immediately after Lightpulsar.
Single-card ROM: `data/over_the_nexus/working/rom_darkflare.nds`.
**`verify()` = 36/36 PASS.**

Donor **Battle Footballer `0x1646`** (user decision). card_prop retune, from the
builder's own before/after dump:

```
BEFORE: lvl=4 attr=FIRE race=Machine atk=1000 def=2100 type=Normal Monster
AFTER : lvl=5 attr=DARK race=Dragon  atk=2400 def=1200 type=Effect Monster
```

Name and description landed **in place in every language** (desc 64 B against the
smallest slot, Korean's 76 B) -- so unlike Lightpulsar's first month, the card is
not silently wearing the donor's flavour text.

## The change set

| # | where | change |
|---|---|---|
| A | `0x0225E888` / `0x0225E88E` | `subs r0,#0x7a` -> `#0x80` (0x16C6 - 0x80 = 0x1646); BL -> the LIGHT+DARK cost leaf `0x0225FA46` |
| B | `0x0225CF8C` | `b 0x0225D09C` (return 0) -> `b 0x0225D06A` (return 1) |
| C1 | criteria registry `0x022713C4` | 2 rows on `0x1646`, LIGHT then DARK, `{0xFFFF, 0x0223CA11, ...}`, at [225]/[226]; both rows of phantom `0x0E32` dropped |
| C2 | membership list A `0x0227134C` | `0x1646` in at [9], phantom `0x0E32` out |
| D/E/F | shared | `handss_banish_cost.py` -- see below |
| G | summon-procedure registry `0x0228F158` | `{0x1646 -> 0x0226292D}` at [27], phantom `0x176C` dropped |
| — | `card_prop` `0x1646` | DARK / Dragon / Lv5 / 2400 / 1200, Normal -> Effect |

**No ov5 cave slot, no ov3 dead-code slot of its own, no cls record.** Entirely
overlay-3, so clause 1 should work in puzzles too.

## The one shipped-card change: the payment stubs became SHARED

Each payment dispatch has exactly ONE 4-byte BL hook, so a stub that hardcodes one
donor cid can only serve one card. The stubs, the ov3 dead run that hosts them and
the donor list therefore moved out of `patch_lightpulsar` into a new
**`otn_enhanced/effects/handss_banish_cost.py`**, which both cards
call. `DONOR_CIDS = (0x0FB1, 0x1646)`; adding a third card is one line there.

Two consequences worth stating plainly:

1. **Lightpulsar's emitted stub bytes changed** (44 + 36 B -> 56 + 48 B, still
   inside the 126 B run at 104 B). Its own route through the stubs is unchanged,
   and `patch_lightpulsar.verify()` = **91 PASS / 0 FAIL** after the refactor.
2. **PART D's assertion was relaxed to the invariant that actually matters.** It
   used to require the two dead arms to point at the reject leaf; Darkflare ROUTES
   one of them at a real leaf, which seals the cave just as effectively. Both the
   applier and `verify()` now check *"no arm branches INTO `[CAVE, CAVE+126)`"*.

The install is idempotent and order-independent, so a single-card ROM and the full
chain emit identical bytes.

## ✅ POST-PATCH DIFFERENTIAL (the check Lightpulsar's 0x0E1F surprise made mandatory)

Both whole-cid-space simulators re-run against the patched overlay and diffed
against the clean one.

**Darkflare alone** (`rom.nds` -> `rom_darkflare.nds`):

| cid | hand-SS leaf | what it is |
|---|---|---|
| `0x0E3F` | `0x0225F26E` -> reject | phantom (the shared cave-sealing) |
| `0x164C` | `0x0225F240` -> reject | phantom (the arm's old occupant) |
| **`0x1646`** | reject -> **`0x0225FA46`** | **the donor** |

**REAL cards that changed leaf: 1 — the donor.**
Required count: 601 cids changed, of which **exactly one can observe it** (reach a
banish-cost leaf): the donor, 0 -> 1. **Zero other real cards.**

**Composed** (`rom_ew_lp_df.nds`, Eclipse Wyvern + Lightpulsar + Darkflare): 6 cids
changed leaf, of which the only real cards are the two donors `0x0FB1` and
`0x1646`; the three count-observers are the two donors plus phantom `0x0E1F`
(a pre-existing, documented Lightpulsar side effect). **Nothing new was disturbed.**

## Test ROMs

`_build_ew_lp.py` builds two, verifying EVERY patch against each FINAL image:

| ROM | contents |
|---|---|
| `data/over_the_nexus/working/rom_ew_lp.nds` | Eclipse Wyvern + Lightpulsar |
| `data/over_the_nexus/working/rom_ew_lp_df.nds` | + Darkflare Dragon |

Both clean. `rom_darkflare.nds` is the isolated single-card build.

## Slots claimed (registered in `check_allocations.PHANTOM_CLAIMS`, ledger refreshed)

| pool | cid / addr | note |
|---|---|---|
| `populate_table` | `0x0E32` | phantom, **both** rows dropped |
| `populate_table` | `0x1646` | the donor's LIGHT+DARK pair |
| `membership_list_a` | `0x0E32` | the same phantom leaves list A with its rows |
| `membership_list_a` | `0x1646` | the donor |
| `handss_dead_arm` | `0x0225E88E` | **the last usable one** |
| `handss_count_branch` | `0x0225CF8C` | not Lightpulsar's `0x0225CF5E` |
| `summon_procedure_table` | `0x176C` | phantom row dropped |
| `summon_procedure_table` | `0x1646` | the donor's procedure row |
| ov3 dead run | `0x0225F240`, 104 B | owner is now `handss_banish_cost`, not one card |

`check_allocations` = 95 ov5 slots (86 live), 54 phantom claims, 6 ov3 dead-code
claims, 106 B free, no overlaps, ledger in sync.

⚠️ **`0x0EA8` is the last unclaimed phantom with a 2-row criteria block**, and there
are now **no dead hand-SS arms left that a monster can reach**. A fifth
banish-cost card needs a different routing mechanism entirely.

## KB contributions

`verify_knowledge --savestate .../sealancer_recon.ml3` 239 -> **241 facts,
211 PASS, 0 FAIL, 30 UNVERIFIED.**

| id | grade | note |
|---|---|---|
| `handss.dead_arm_donor_windows` | **VERIFIED** (new) | the reachability windows; why only one arm was usable |
| `handss.dispatch_dead_arms` | claim CORRECTED | its "three arms remain, take one" guidance was misleading |
| `card.darkflare_clause1` | **UNVERIFIED** (new) | built, not yet duelled; carries the exact in-game test |

## ⏳ Next Experiment — the in-game test IS the arbiter

Static `verify()` proves the written bytes are correct and says NOTHING about
whether the engine reaches them. Both of Lightpulsar's failures were reachability.
On `rom_ew_lp_df.nds`:

1. donor in hand, a LIGHT and a DARK monster in your GY -> the SS option must APPEAR;
2. with an EMPTY GY -> it must NOT appear;
3. take the summon -> it must prompt for a LIGHT, then a DARK, and **BANISH BOTH**.

Step 3 is the decisive one: Lightpulsar's test 2 looked correctly gated and still
paid nothing, which is the signature of a missing summon-procedure row (part G).

**Also re-test Lightpulsar on the same ROM** -- the shared payment stubs were
rewritten to cover both cids, and only the emulator can confirm that.

## Chain rebuild + regression sweep (2026-08-17)

`ALL 33 PATCHES APPLIED -> data/over_the_nexus/working/rom_all_patches.nds`,
Darkflare at step **[27/33]**, immediately after Lightpulsar; the allocation guard
passed before the first write.

Chain-wide sweep (`verify()` for every patch module against the **combined** ROM):
**23 PASS, 12 modules expose no verify(), 4 not-PASS — none of them in the applied
chain**, i.e. none is a regression from this work:

| module | result | why it is not a regression |
|---|---|---|
| `patch_wonder_wand` | `AssertionError: grant row is +800/+0` | its PatchStep is **commented out**; not applied |
| `patch_bulk_ydcs` | IMPORT-FAIL `ValueError` (a 15-card deck) | no PatchStep at all; pre-existing data issue |
| `patch_unlock_all_packs` | returns False | no PatchStep; not applied |
| `patch_zeta_reticulant` | `SystemExit: 1` | no PatchStep; not applied |

Identical to the list the 2026-08-13 Lightpulsar sweep recorded. Every applied
module that exposes `verify()` passes, including all 26 shipped effect cards and
Darkflare's 36 checks.

⚠️ A harness note, because it wasted a pass: the sweep script must call
`verify()` **positionally** unless the module's first parameter is literally named
`out` — the modules disagree (`out`, `rom_path`, `path`, bare positional), and
forcing `out=` reports 20 false `TypeError` ERRORs that look exactly like
regressions. Two modules also `sys.exit()` at import, so the harness has to catch
`BaseException`, not `Exception`, or it dies silently with no output at all.

---

# ✅✅✅ CLAUSE 1 WORKS — IN-GAME CONFIRMED ON THE FIRST TEST (2026-08-17)

User-reported: *"Darkflare dragon can be SSed correctly. No regressions in
lightpulsar."*

Both halves matter. The card works, **and** Lightpulsar — whose shared payment
stubs were rewritten from single-cid to a donor register in this session — is
unaffected on the same ROM. That was the one live risk in the refactor and only
the emulator could close it.

## Why this one passed first time and Lightpulsar took three

| card | in-game tests | what each failure was |
|---|---|---|
| Lightpulsar clause 1 | 3 | (1) no payment side at all; (2) correctly GATED yet still FREE — the missing summon-procedure row; (3) pass |
| **Darkflare clause 1** | **1** | — |

Not luck, and not a better guess. The pipeline had already been mapped end to
end, so this build could **start** from the summon-procedure row (part G) that
Lightpulsar only found after two duels. The generalisable point:

> A fully-mapped subsystem turns a multi-duel debugging loop into a single
> confirmation. That is the return on writing the KB entry the first time —
> and it only pays out if the next card actually reads it before building.

The second thing that paid off was checking the **3DS first**, as CLAUDE.md's order
of authority requires: `summon_cond[193]` for Darkflare being byte-identical to
Chaos Sorcerer's row settled "plain banish-cost procedure, handler 0x0226292D, no
bespoke handler" in one lookup, before a single instruction was disassembled.

## Final shipped state of clause 1

Donor **Battle Footballer `0x1646`** -> Darkflare Dragon, DARK / Dragon / Lv5 /
2400 / 1200. Five in-place overlay-3 edits (A routing, B count, C1 criteria pair,
C2 membership list A, G summon-procedure row) + the shared ov3 payment stubs.
**No ov5 cave, no cls record, no ov3 slot of its own.**

* `patch_darkflare.verify()` = **36/36 PASS**
* `patch_lightpulsar.verify()` = **91 PASS / 0 FAIL** after the shared-stub refactor
* full chain = **33/33 applied**; sweep = 23 PASS, 4 not-PASS (all pre-existing,
  none in the applied chain)
* KB = **249 facts, 218 PASS, 0 FAIL**; `card.darkflare_clause1` promoted
  UNVERIFIED -> **VERIFIED**

## Open for a future session

* **Clauses 2 and 3** ("Once per turn: send 1 Dragon from your hand and 1 Dragon
  from your Deck to the GY, then target 1 card in either GY; banish that target").
  The 3DS shows them as three criteria rows on one cid — rows 0/1 here are already
  clause 1's, so C2/C3 need relative rows 2/3/4, which a donor cannot address by
  data alone (`dispatch.criteria_block_size_tiers`). It needs a row-offset hook;
  Lightpulsar's `CAVE_LP_ROWHOOK` is in ov5 and is keyed to its own cid, so
  Darkflare needs either its own arm on a shared hook or its own stub.
  3DS handlers to map first: `0x004B1C5C` and `0x004B1BE8` (the two Dragon send
  rows, word `0x08000002`) and `0x004A71E4` (the banish-from-a-GY row, word
  `0x0001000E` — the same word D.D. Crow and Disappear carry on the NDS).
* **Puzzle behaviour is untested.** Clause 1 is entirely ov3, so it *should* work
  where ov5-hosted cards cannot; nobody has actually run it in a puzzle.
* ⚠️ **The routing mechanism is now exhausted.** No dead hand-SS arm remains whose
  window contains a monster (`handss.dead_arm_donor_windows`), and `0x0EA8` is the
  last unclaimed phantom with a 2-row criteria block. A third
  banish-cost card needs a different approach — most likely a small ov3 stub
  hooked into the BST, since 22 B of the dead run and 106 B of the ov3 dead-code
  pool are still free.

## Handoff prompt for clause 2

`PROMPT_darkflare_clause2.md` (repo root).

It carries the **3DS→NDS handler join measured 2026-08-17**, which both confirms and
corrects the 2026-08-05 table above. Method: for each 3DS handler, take every cid
carrying it, look those cids up in the NDS criteria registry, and keep the rows whose
WORD also matches.

| 3DS handler | NDS | concurring rows | verdict |
|---|---|---|---|
| `0x004B1C5C` | `0x0223CB65` | **24** | settled — send from HAND (witness Vanguard of the Dragon `0x1FFE` [885], word `0x08000002`, literally Darkflare's row) |
| `0x004B1BE8` | `0x0223CAD9` | **60** | settled — send from DECK (witness Foolish Burial `0x1474` [138]) |
| `0x004A71E4` | ? | 2 / 1 / 1 split | **OPEN** |

⚠️ **The 2026-08-05 guess `0x0223D6FD` for the third row is NOT supported** — that
handler never appears in the join. The candidate is **`0x0223D741`**, on two
independent lines: Soul Release `0x12F9` matches on the 3DS handler, the NDS handler
AND the word `0x0001000E` simultaneously; and every opponent-only card (D.D. Crow,
Disappear, Kycoo) sits on `0x0223D6FD` while Soul Release ("either player's GY") sits
on `0x0223D741` with the SAME word — i.e. the SIDE looks like it lives in the handler,
per `dispatch.criteria_zone_is_the_handler`. Darkflare needs "either GY", so picking
`0x0223D6FD` would silently narrow the card. **Settle this before building.**

The prompt also names the two blockers:

1. the criteria row-index hook `0x02243BEC` is a **single 4-byte BL already owned by
   Lightpulsar** (`CAVE_LP_ROWHOOK`) — add an arm to the shared stub, never re-point
   the hook; the same lesson the payment stubs taught this session;
2. the **hand + deck double send has no native precedent**. Nearest twin is Zombie
   Master `0x1C2F` cls3[321] `+04 02207191 +0C 021FC99D +10 021EAC0D +14 02235605` —
   read its cost `0x021EAC0D` first to see whether a second pass is data or code.

Action side is nearly free and now measured: the banish-the-target resolver is
`0x02208D19` and the GY target-declaration step is `0x02235A4D`, shared by D.D. Crow
`0x1B44` cls2[244], Disappear `0x1515` cls0[358] and Kycoo `0x1480` cls1[177].

---

# Session 2026-08-18 — CLAUSE 2 (the whole second sentence)

Scope: *"Once per turn: You can send 1 Dragon monster from your hand and 1 Dragon
monster from your Deck to the GY, then target 1 card in either GY; banish that
target."* Text re-read verbatim from `scratch/ygoprodeck_cache.json` id 25460258 —
identical to both earlier quotes. **Clause 1 is shipped and in-game confirmed and
must not regress; neither may Lightpulsar, which shares the row hook.**

User decisions this session: **two staged builds, one duel each**; **re-home** the
shared row hook rather than chaining a continuation stub; **no fallback** on the
Deck send — the cost is faithful (both sends before targeting) or the work is
reported blocked.

## Confirmed (this session)

### Inherited state re-verified
- KB `verify_knowledge --savestate .../sealancer_recon.ml3` = **249 facts,
  218 PASS, 0 FAIL, 31 UNVERIFIED**.
- `check_allocations` = 95 ov5 slots (86 live), 54 phantom claims, 6 ov3 dead-code
  claims (106 B free), no overlaps, ledger in sync.

### THE ACTION HALF IS A NATIVE CARD, SHIPPING AS PURE DATA — Card Ejector `0x1D44`
*"Once per turn: You can target 1 card in your opponent's Graveyard; banish that
target."* An on-field ignition monster, and its ENTIRE implementation is one cls3
record plus one criteria row:

```
cls3[375] cid 1D44  +04 02208D19  +08 00000000  +0C 021F05E9  +10 021E5061  +14 02235A4D
crit[659] 1D44 aux FFFF handler 0223D6FD word 0001000E
```

Every slot is generic in the cid — disassembled this session:

- **`+0C 0x021F05E9`** — the once-per-turn gate AND the offer test, with **no per-cid
  switch**:
  ```
  if 0x021A1430(desc[+2] side, desc[+3] zone, 0x0FB6) != 0:  return 0   ; used this turn
  tail -> 0x021F05A8:  side = desc[+2]^desc[+6] ; param = 0x02234E78(desc)
                       return 0x02243FE0(side, desc[+0], param) ? 1 : 0
  ```
  Key `0x0FB6` is the per-SLOT "effect used this turn" latch (memory note
  `otn-attached-effect-rider`), queried by the key-only walker `0x021A1430`.
- **`+10 0x021E5061`** — the shared "You can" cost tag (236 records). It selects
  nothing; it **posts the latch**: `0x021C479C(desc[+2], desc[+3], 0x0FB6, 2)`. So
  the once-per-turn write and read are both native and already paired.
- **`+04 0x02208D19`** — the banish resolver. Target-list driven, cid-blind: reads
  `desc[+0x12]` = number of declared picks, walks them with `0x02234964(desc,i)`,
  requires each pick's container kind `== 0x0E` (GY), then banishes with
  `0x021C7098`, bracketed by `0x021D28A4` / `0x021D2964`.
- **`+14 0x02235A4D`** — the GY target-declaration step. `MOVS R1,#1` then a per-cid
  count switch; **a cid with no case keeps 1** = "target 1 card". 3-step machine on
  `[0x0229AB7C]`: `0x02243FE0(side, cid, param=0 HARDCODED)`, prompt `0x56`,
  `0x0219C430(side, 0x27+n, cid, 0)`, then a recorder loop with **`MOVS R7,#0x0E`** —
  the GY container kind, hardcoded. No side flip (unlike `0x02235605`, which does
  `desc[+2] ^ desc[+6]`).

**=> Darkflare's action half = Card Ejector's record with the criteria row's
HANDLER swapped for the either-GY one.** No cave, no Thumb.

### THE EITHER-GY HANDLER — SETTLED, and the handler's flags word is DECODED
`0x0223D6FC` and `0x0223D740` are **byte-identical 14-byte thunks differing in one
pooled word**, which they pass as arg6 to the shared worker `0x0223C4E8`:

```
0x0223D6FC  push{r1,r2,r3,lr}; r2=row; r0=[r2+8] (criteria word); r3=0; [sp]=r0;
            r0=<POOLED FLAGS>; [sp+4]=r0; r0=player; r1=[r2] (cid); r2=0;
            bl 0x0223C4E8; pop{r1,r2,r3,pc}        .word 0x00010001
0x0223D740  ... identical ...                       .word 0x00010003
```

The flags word is a bitfield, read off its two consumers:

| bit | meaning | site |
|---|---|---|
| 0 `0x1` | scan the **opponent's** side, not the controller's | `TST r1,#1 ; EOR r5,#1` @`0x0223BC76` |
| 1 `0x2` | scan **both** sides: pass 1 with bit 1 cleared, then `flags ^= 1`, pass 2 | `0x0223C4FA`..`0x0223C510` |
| 3 `0x8` | action = Special Summon | `0x0223D6E1` flags `0x0A` |
| 16 `0x10000` | action = **banish** | 106 rows, all "banish" |

- **All 24 rows on `0x0223D6FD` (flags `0x10001`) print "your opponent's GY" — zero
  exceptions.** The apparent counterexample D.D. Guide `0x19C0` is the strongest
  confirmation the bit is *relative*: the card gives itself to the opponent, so its
  "this card's controller's GY" IS the relative opponent's.
- The single `0x0223D741` row (flags `0x10003`) is **Soul Release `0x12F9`** —
  *"Target up to 5 cards in any GY(s); banish them"* — word `0x0001000E`, i.e. the
  exact (word, flags) pair the 3DS assigns Darkflare.

**Row 3 = `{0xFFFF, 0x0223D741, 0x0001000E}`.** Rivals enumerated and rejected:
`0x0223E461` / `0x02240835` / `0x02242DB1` are either-GY banish but only ever
attested with monster-only words (`...0002`); `0x0223FB39` is either-GY/any-card but
lacks bit 16, so it **shuffles into the Deck**. Cross-check `0x0224265D` (Power
Pickaxe, flags `0x10001`) — 25/25 for the opponent-only class.

WARNING: **the 2026-08-05 guess `0x0223D6FD` is WRONG for this card** and would have
silently narrowed it to the opponent's GY. Kept in Ruled Out below.

### HAND vs DECK — confirmed, not reversed
Internal control: **Dark Grepher `0x1D89` owns two adjacent rows differing only in
handler** — `[673] {0x0223CB19, 0x02000002}` ("You can discard 1 DARK monster") and
`[674] {0x0223CAD9, 0x02000002}` ("send 1 DARK monster **from your Deck** to the
GY"). Table-wide: all 25 `0x0223CB65` rows are hand cards, all 66 `0x0223CAD9` rows
are Deck cards, zero crossovers.

**Dragon Ravine `0x2359` already ships Darkflare's Deck row verbatim**:
`crit[1249] {0xFFFF, 0x0223CAD9, 0x08000002}` = "send 1 Dragon monster from your
Deck to the GY". And **Vanguard of the Dragon `0x1FFE` `crit[885]` /
Genesis Dragon `0x1F2A` `crit[792]`** are the hand row `{0x0223CB65, 0x08000002}` —
literally the row the 3DS assigns Darkflare.

### THE HAND SEND, AND WHY THE DECK SEND CANNOT USE THE SAME PATH
- `0x021E7245` (Soulkius / Genesis Dragon / Vanguard, 30 records) is the "send N from
  hand" cost: a 4-state machine on `[0x0229AAFC+0x7C]`, `r7` = count (**1 for every
  cid except Soulkius `0x202C`**), arming `0x0224B9F0(side, 0xD, param, 0x022065F9)`
  with **param 0 on pass 0**.
- WARNING: **the zone on that path is enforced by the CALLBACK, not by the row
  handler.** `0x022065F9` hardcodes `CMP R1,#0x0B` (hand) @`0x0220660C` before
  probing `0x02243FE0`. There is **exactly one** `0x02243FE0` caller in
  `0x02205000..0x02208000` and its only zone compare is that `#0x0B`, so **there is
  no native Deck-pinning sibling callback** — a Deck selection cannot be armed
  through `0x0224B9F0`.
- Every native Deck read instead runs the **list-zone path**: `0x02208DD5`
  (Foolish Burial / Dragunity Tribus / Dark Grepher / Dragon Ravine) does
  `param = 0x02234E78(desc)` then `0x02243FA8(side, cid, param)` to count and fill,
  prompt `0x0219A818(side, 0xD)` on shortfall, then `0x0219C430` to pick. On THAT
  path the row's handler IS the zone, dispatched through the stride-12 table at
  `0x022713C4`.

### A NATIVE TWO-ZONE IGNITION COST EXISTS — Transcendent Wings `0x1907`
Scanned all 161 distinct slot4 values for routines invoking two different pickers.
Exactly one is genuinely two-zone: `cls0[626] +10 = 0x021EA055`, a 3-state machine on
`[0x0229AAFC+0x7C]` that picks **on the FIELD** (`0x0224BA34` with the slot2 invoker
`0x0224A8C1` as the legality callback) in states 0/1 and then arms a **HAND** send of
N cards (`0x021E4CCC` -> `0x02259968`) in state 2. **Two zones, two stages, one
slot4, staged by the same counter our cost would use.** That is the structural
precedent the handoff prompt said did not exist.

Dark Simorgh `0x1E5A` `+10 0x021EC57D` is the two-PASS precedent (pass index at
`desc[+0x12]`, picks banked at `desc[+0x14 + pass*2]`, `state := 1` to go round
again), and its sibling `0x021EB7AD` proves a **per-pass, code-computed filter** is
native (`pass ? WIND : DARK`, handed to `0x0219C430` as `attr << 28`).

### AN ON-FIELD IGNITION NEEDS NO REGISTRY ROW
The capability enumerator `0x0224BC40` dispatches zones 0..4 to `0x0224BCF2`, which
builds a descriptor at `sp+0x1C` (zeroed by `0x0209A080`) and writes
`desc[+0] = cid`, `desc[+2] = side`, **`desc[+3] = zone`** (`strb r6,[r0,#3]`
@`0x0224BD62`, loop bounded `cmp r6,#4`), `desc[+4] = index`, **`desc[+5] = 3`**
(the record class) and `desc[+6] = 1`. It gates only on `0x02029E60` /
`0x02023584` and the zone record — **no per-cid table anywhere on the path**.
Corroborated by profiling: Zombie Master `0x1C2F`, Genesis Dragon `0x1F2A`, Vanguard
`0x1FFE` and Card Ejector `0x1D44` each own a cls3 record and **nothing** in the
effect registry, the GY-action registry or the summon-procedure registry.

**=> `desc[+5] == 3` is the row hook's discriminator**: clause 1 runs from the hand
through a different path and never produces a cls3 descriptor, so its membership-
list-A `param == 0 ? 0 : 1` clamp is untouched.

### THE ROW HOOK MUST BE RE-HOMED, NOT GROWN
- `patch_lightpulsar._stub_row_hook` emits **76 B (0x4C)** into `reserve=0x60`, and
  `CAVE_LP_RESDISP = 0x0239C528` sits at exactly `CAVE_LP_ROWHOOK + 0x60` — **20 B
  of headroom**, less than a second card's arm needs.
- `ov5_cave.install_cave()` **asserts the destination is all-zero**, so it cannot be
  called twice at one address in a chained ROM. A shared module needs a
  read-back-and-skip wrapper to stay order-independent.
- WARNING: `check_allocations.parse_ov5_slots` scrapes the size from the trailing
  comment **on the assignment line only**; every `CAVE_LP_*` size comment sits on a
  continuation line, so the ledger records `CAVE_LP_ROWHOOK` with `size: null` and
  **it participates in NO overlap check today**.
- `patch_lightpulsar.verify()` never loads ov5 — only the 4-byte BL is checked — and
  its row-hook tail assertion at `:2676` is `... or True`, i.e. permanently PASS.

### PHANTOM CENSUS (against the FULL CHAIN `rom_all_patches.nds`)
Only three phantoms with >=2 criteria rows survive the chain:

| phantom | rows | list A? | note |
|---|---|---|---|
| `0x0E12` | **3** | neither list | one of the 22 equality cases in the switch `0x02243C1C` |
| `0x0E6B` | 2 | **already out** (Lightpulsar dropped it) | unclaimed in `populate_table` |
| `0x0EA8` | 2 | yes | the last spare list-A pair |

`0x234E` is **NOT** available despite reading as unclaimed: `patch_tg_striker.py:158`
`POP_PHANTOM = 0x234E` consumes one of its two rows, and the ledger records that
claim under the wrong cid `0x2347` (which is striker's *cls2* phantom).

## Ruled Out (this session)

- **`0x0223D6FD` as clause 2's target handler** (the 2026-08-05 guess). It is the
  opponent-GY-only handler — 24/24 by printed text — and would silently narrow the
  card. Superseded by `0x0223D741`.
- **"The hand+Deck double send is unattested and is the real research."** Two native
  precedents were found: Transcendent Wings `0x1907` (two zones, two stages, one
  slot4) and Dark Simorgh `0x1E5A` (two passes with a per-pass computed filter).
- **Arming the Deck pass through `0x0224B9F0`.** Impossible: the only callback is
  `0x022065F9` and it hardcodes the hand. Deck selection must use the list-zone path.
- **Zombie Master `0x1C2F` as the twin.** Its cost `0x021EAC0D` hardcodes ONE pass
  and never touches a criteria row index at all — the only data-driven part is a
  scalar count from the 27-row table `0x0226F04C` `{u16 cid, s16 count}`. Genesis
  Dragon `0x1F2A` (cost) and Card Ejector `0x1D44` (action) are the real templates.
- **The `[rec+0x28]` / `0x02262C8C` two-pass driver as a reusable mechanism.** Traced:
  `0x02262C8C`, `0x02262C24` and `0x0226292C` have **zero BL callers**; `0x0226292D`
  appears only in the summon-procedure registry's handler column, and no cls slot
  value lies in `0x02262000..0x02263000`. Its state lives in the summon record
  `0x02298A28`, which an ignition never populates. **Summon-path exclusive.**

## Open Questions

1. Does `0x02235A4D`'s default count of 1 mean "exactly 1" or "up to 1" at runtime?
   The picker mode is `0x27 + n` into `0x0219C430`, undecoded. Not blocking — either
   reading is acceptable for "target 1 card".
2. Can `0x02208DD5`'s Deck stage be re-entered from inside a slot4 cost stub, or must
   the Deck states be cloned? Untested; decided by build 2's disassembly.
3. Is the acting descriptor the row hook reads (`[0x0229A9FC+0x50]`) the same cls3
   descriptor at the moment each consumer runs? Lightpulsar relies on the identical
   assumption and works in-game, but it was measured there. **UNVERIFIED here.**

## Next Experiment

**BUILD 1 — the action half, then one duel.** It is almost pure data: Card Ejector's
cls3 record on our cid, three criteria rows at rel 2/3/4, and one new arm on the
shared (re-homed) row hook so the target step reaches rel 4.

---

# ✅ BUILT — CLAUSE 2, BUILD 1 (2026-08-18)

Build 1 is the **action half plus the hand send**, shipped as the user's staged
plan requires: one duel decides the row hook, the either-GY row and the whole
banish pipeline before the Deck send (the only genuinely new state machine) is
written. **Build 1 is a test vehicle, not the finished clause** — the card is not
done until build 2 lands.

Test ROM: `data/over_the_nexus/working/rom_ew_lp_df.nds` (Eclipse Wyvern +
Lightpulsar + Darkflare), **248 PASS / 0 FAIL** across all three cards verified
against the FINAL image.

## The change set

| # | where | change |
|---|---|---|
| H | criteria registry `0x022713C4` | **3 rows on `0x1646` at rel 2/3/4**; phantoms `0x0E6B` (2 rows) + `0x164A` (1 row) dropped |
| I | cls3 `0x02279D74` | Card Ejector's record on `0x1646`; phantom `0x164B` dropped |
| J | `0x02243BEC` | the SHARED row hook — an arm keyed on `desc[+5] == 3` |
| — | `card_prop` desc | rewritten to cover both clauses within the 76 B ceiling |

```
rel 0  {0xFFFF, 0x0223CA11, 0x01000002}   clause 1 LIGHT   (SHIPPED, unmoved)
rel 1  {0xFFFF, 0x0223CA11, 0x02000002}   clause 1 DARK    (SHIPPED, unmoved)
rel 2  {0xFFFF, 0x0223CB65, 0x08000002}   1 Dragon, from the HAND
rel 3  {0xFFFF, 0x0223CAD9, 0x08000002}   1 Dragon, from the DECK   (build 2 uses it)
rel 4  {0xFFFF, 0x0223D741, 0x0001000E}   1 card, in EITHER GY

cls3  {0x1646, 0x02208D19, 0, 0x021F05E9, 0x021E5061, 0x02235A4D}
```

All three rows go in now, even though build 2 is the only consumer of rel 3, so
that build 2 adds **no rows at all** and cannot renumber anything.

## The shared row hook — `otn_enhanced/effects/criteria_row_hook.py`

`0x02243BEC` has exactly ONE 4-byte BL and `patch_lightpulsar` owned it. Lifted
into a shared module on the `handss_banish_cost.py` pattern: the site, the stub
builder and an `ARMS` register of `(cid, tag, arm source, doc)`. Both card modules
call its idempotent `apply(ov)` / `install(rom)` and its `verify(ov, check, rom=)`.

**RE-HOMED, not grown** (user decision). The stub was 76 B in a `reserve=0x60`
whose next slot `CAVE_LP_RESDISP` sits at exactly `+0x60` — 20 B of headroom, less
than a second arm needs. It now lives at **`CAVE_ROWHOOK = 0x0239C5A8`, 108 B in a
0x100 reserve**, with `CAVE_LP_ROWHOOK` marked RETIRED. `CAVE_DF_STAGE =
0x0239C6A8` holds the stage byte; `CAVE_FREE = 0x0239C6AC`.

Three defects in the old arrangement were fixed in passing, all of them things
that had been silently unguarded:

1. `ov5_cave.install_cave()` **asserts its destination is all-zero**, so a shared
   stub could not be installed by whichever card patch ran first. Added
   `ov5_cave.read_cave()` and a read-back-and-skip wrapper, so the install is
   idempotent and order-independent.
2. `check_allocations.parse_ov5_slots` scrapes a slot's size from the trailing
   comment **on the assignment line only**; every `CAVE_LP_*` size comment sits on
   a continuation line, so the ledger recorded `CAVE_LP_ROWHOOK` with `size: null`
   and it was in **no overlap check at all**. The new constants carry their size
   inline and the guard now covers them.
3. **`patch_lightpulsar.verify()` never loaded ov5** — only the 4-byte BL was ever
   checked — and its row-hook tail assertion was `... or True`, a permanent PASS.
   Both card modules now pass the ROM into `rowhook.verify(..., rom=)`, which pins
   the 108-byte blob and the STAGE byte byte-for-byte.

### Darkflare's arm, and why clause 1 is safe

```
if desc[+0] == 0x1646 and desc[+5] == 3:      # our cid, a cls3 (on-field) descriptor
    r4 = 2 + STAGE                            # STAGE 0/1/2 -> rel 2/3/4
    goto 0x02243EEE
```

`desc[+5] == 3` is measured, not assumed: the on-field capability enumerator
`0x0224BCF2` writes `desc[+3] = zone` (`strb r6,[r0,#3]` @`0x0224BD62`),
`desc[+4] = index` and **`desc[+5] = 3`** (`movs r1,#3 ; strb r1,[r0,#5]`
@`0x0224BD66`). Clause 1 runs from the hand through the hand-SS dispatch and never
produces a cls3 descriptor.

**✅ AND THE STALE-DESCRIPTOR HAZARD IS CLOSED, measured this session.** The obvious
worry is that clause 2 leaves its cls3 descriptor behind and clause 1's later
lookups get hijacked. It cannot happen: `[0x0229A9FC+0x50]` is **scoped, not global
state**. The slot dispatcher saves the old value, writes its own
(`str r5,[r0,#0x50]` @`0x0224AE20`) and **restores it** (`str r7,[r0,#0x50]`
@`0x0224AE3C`) around every slot invocation, and the activation state machine sets
it once per activation (`str r5,[r0,#0x50]` @`0x02217F8C`). The descriptor an arm
sees always belongs to the activation actually running. (There are 15 writers of
that slot in ov3 and 94 readers, enumerated by resolving every PC-relative load of
the `0x0229A9FC` literal.)

### Lightpulsar's arm is unchanged — proven, not asserted

The pre-refactor stub was rebuilt verbatim at the new address and disassembled
against the new one. The Lightpulsar arm is **instruction-for-instruction
identical** except for two branch targets that must differ: its cid-test `bne` now
falls to Darkflare's arm instead of `native`, and its `setOff` path ends with an
explicit `b tail` where it used to fall through into `tail`. Every other
instruction, in order, is the same. `patch_lightpulsar.verify()` = **95 PASS /
0 FAIL** (was 91; the shared module contributed the extra checks).

Each arm now re-reads the cid (`ldrh r0,[r3,#0x0]`) and exits to `native` on its
own sub-condition, so no arm can be broken by what an earlier one left in `r0` —
the first draft chained the arms and would have compared Lightpulsar's zone byte
against Darkflare's cid.

## ✅ POST-PATCH DIFFERENTIAL

`rom_ew_lp.nds` -> `rom_ew_lp_df.nds`, whole criteria registry and whole cls3
table, block by block:

| cid | | rows |
|---|---|---|
| `0x0E32` | phantom | 2 -> 0 (clause 1's drop) |
| `0x0E6B` | phantom | 2 -> 0 |
| `0x164A` | phantom | 1 -> 0 |
| **`0x1646`** | **the donor** | **0 -> 5** |

**REAL cards whose criteria block changed: 1 — the donor.** Every other cid's block
is **byte-identical in content AND order**. cls3: only `0x1646` (gained) and
`0x164B` (phantom, dropped).

## Slots claimed (ledger refreshed)

| pool | cid / addr |
|---|---|
| `populate_table_r234` | `0x1646` — the rel 2/3/4 block, its own pool per the `populate_table_r23` precedent |
| `populate_table` | `0x0E6B` (2 rows), `0x164A` (1 row) |
| `cls3_table` | `0x1646`, phantom `0x164B` |
| ov5 | `CAVE_ROWHOOK` 0x0239C5A8 (0x100), `CAVE_DF_STAGE` 0x0239C6A8 (0x4) |

`check_allocations` = 97 ov5 slots (87 live), 59 phantom claims, 106 B ov3 free,
no overlaps, ledger in sync.

⚠️ `0x0EA8` remains the last unclaimed phantom with a 2-row criteria block, kept
deliberately for the next card. `0x0E12` (3 rows) is available but is one of the 22
equality cases in the disambiguation switch `0x02243C1C`.
⚠️ **Ledger bug found, not yet fixed:** `check_allocations` records tg_striker's
populate phantom as `0x2347`, but `patch_tg_striker.py:158` sets
`POP_PHANTOM = 0x234E` (`0x2347` is its *cls2* phantom). So `0x234E` reads as
unclaimed while one of its two rows is actually consumed.

## KB contributions

`verify_knowledge --savestate .../sealancer_recon.ml3` 249 -> **252 facts,
221 PASS, 0 FAIL, 31 UNVERIFIED.**

| id | grade | note |
|---|---|---|
| `dispatch.criteria_handler_flags_word` | **VERIFIED** (new) | a criteria handler is a 14-byte thunk whose only per-handler datum is a pooled FLAGS word; bit 0 = opponent's side, bit 1 = both sides, bit 3 = SS, bit 16 = banish. **A missing side/action combination can be synthesised as a 14-byte clone with one word changed.** |
| `dispatch.criteria_hand_vs_deck_handlers` | **VERIFIED** (new) | `0x0223CB65` = hand, `0x0223CAD9` = Deck; control = Dark Grepher `0x1D89` rows [673]/[674] |
| `dispatch.onfield_ignition_is_a_cls3_record_only` | **VERIFIED** (new) | a cls3 record is the whole registration; `desc[+5] = 3` is written at `0x0224BD66` |

## ⏳ IN-GAME TEST — BUILD 1 (the arbiter)

On `data/over_the_nexus/working/rom_ew_lp_df.nds`. Static `verify()` proves the
bytes and says NOTHING about reachability.

1. Darkflare on the field, **≥1 Dragon in your hand**, cards in both GYs → the
   effect must be **offerable**.
2. Activate → it must prompt for a Dragon **from the hand** and send it to the GY.
3. → it must let you target **1 card in EITHER GY** — **test your own GY
   explicitly**, that is exactly what the `0x0223D741` choice decides — and
   **banish** it.
4. It must be **once per turn**, and not offerable with no Dragon in hand.
5. **Regression, mandatory:** clause 1 still summons and still banishes a LIGHT and
   a DARK; and **Lightpulsar's clauses 1/2/3 all still work** — the row hook is
   shared and was re-homed.

What each failure would mean, so the duel is decisive either way:

- **not offerable at all** → the cls3 record is not being enumerated (the
  `dispatch.onfield_ignition_is_a_cls3_record_only` premise), or `0x021F05E9`'s
  candidate probe returned 0 because the row hook did not fire.
- **offerable, but the target prompt shows the wrong cards** → the row hook fired
  but STAGE/offset is wrong: it is reading rel 0 (clause 1's LIGHT row) instead of
  rel 4.
- **targets only the opponent's GY** → `0x0223D741` is not the either-GY handler
  after all, and `dispatch.criteria_handler_flags_word` needs correcting.
- **no hand prompt** → `0x021E5061` really is only a tag, and the hand send needs
  the `0x021E7245` cost (Genesis Dragon's) instead — a one-constant change.

---

# ✅ IN-GAME TEST — BUILD 1 PASSED (2026-08-18)

User-reported on `rom_ew_lp_df.nds`: *"Dark Flare still summons and can activate its
effect to banish a card from the GY but there is no send Hand -> GY and Deck -> GY
cost yet"*, and separately that **Lightpulsar's three clauses are all still fine**.

Build 1 passed on every question it was built to answer:

| what the duel proves | how |
|---|---|
| clause 1 does not regress | the card still Special Summons from the hand |
| **the shared row hook survived being RE-HOMED** | Lightpulsar's clauses 1/2/3 all still work on the same ROM — the one live risk in the lift |
| **a cls3 record IS the whole registration** | the effect was OFFERABLE with no registry row anywhere (`dispatch.onfield_ignition_is_a_cls3_record_only`) |
| **the row hook fires and resolves rel 4** | the target prompt offered GY cards to banish. Had the hook not fired, `0x02235A4D`'s hardcoded `param = 0` would have read rel 0 — clause 1's LIGHT row, a summon-material filter — and the prompt would have been wrong or empty |
| the action half works | `0x021F05E9` gated it, `0x02235A4D` declared the target, `0x02208D19` banished it |

**The missing cost is the predicted outcome, not a surprise.** This file's build-1
test section listed it in advance: *"no hand prompt -> `0x021E5061` really is only a
tag, and the hand send needs the `0x021E7245` cost (Genesis Dragon's) instead"*.
`0x021E5061` selects nothing; it only posts the once-per-turn latch.

⚠️ **Still unchecked: whether the target prompt offers YOUR OWN GY as well as the
opponent's.** That is the single question the `0x0223D741` handler choice decides,
and it folds into build 2's duel at no extra cost.

## Chain + sweep after build 1 — clean

`ALL 33 PATCHES APPLIED -> rom_all_patches.nds`. Sweep (`verify()` for every module
against the COMBINED ROM, called positionally, catching `BaseException`):
**23 PASS, 12 expose no verify(), 4 not-PASS** — `patch_wonder_wand`,
`patch_bulk_ydcs`, `patch_unlock_all_packs`, `patch_zeta_reticulant`, all
pre-existing and **none in the applied chain**. Identical to the historical baseline.

---

# BUILD 2 — the two-zone cost. RE COMPLETE, every primitive measured.

## The hand half is native, with ONE trap

`0x021E7245` (Soulkius / Genesis Dragon / Vanguard, 30 records) is a 4-state machine
on `[0x0229AAFC+0x7C]` with the pass counter at `[+0x74]`:

```
state 0  r7 = 1 (2 only for Soulkius 0x202C); prompt 0x3A via 0x0219A818; state++
state 1  0x0224B9F0(side, 0xD, param, 0x022065F9)   ; param 0 on pass 0, -1 after
state 2  0x0224BBB0() -> picked?; read player[side].hand[[0x0229DE14]];
         *** 0x021C6E74(side, &cardword) == THE SEND, hand 0x0B -> GY 0x0E ***
         [+0x74]++ ; if [+0x74] >= r7 then state++ else state-- (re-arm)
state 3  a per-cid switch, then `movs r0,#1 ; pop`
```

⚠️⚠️ **THE TRAP: THE ONCE-PER-TURN LATCH IS IN STATE 3'S PER-CID SWITCH, NOT IN THE
SHARED TAIL.** Only the cids with a case reach `0x021E744E`, which is
`adds r0,r4,#0 ; bl 0x021E5060` — the latch post. **The DEFAULT arm branches
straight to `0x021E745C` (`movs r0,#1 ; pop`) and posts NOTHING.** So swapping our
`+10` from `0x021E5061` to `0x021E7245` would buy the hand send and *silently lose
the once-per-turn*, which build 1 has already confirmed working. The wrapper must
call `0x021E5060(desc)` itself.

## The Deck half — Foolish Burial's exact recipe, in the slot4 protocol

The Deck pass CANNOT use the mode-8 path: its only callback `0x022065F9` hardcodes
`cmp r1,#0x0B` (hand). Every native Deck read uses the list-zone path, and
`0x02208DD4` (Foolish Burial 0x1474 / Dragunity Tribus 0x20C6 / Dark Grepher 0x1D89
/ Dragon Ravine 0x2359) is the worked example. Disassembled in full this session:

```
count+fill   0x02243FA8(side, cid, param)         ; param from 0x02234E78, ours -> 0
                                                   ; the ROW HOOK supplies rel 3
shortfall    0x0219A818(side, 0xD)                ; the deck prompt
open picker  r6 = min(count, 0x20) + 6            ; mode = count + 6, so 7 for one card
             0x0219C430(side, mode, cid, param)
read picks   n = [0x0229DD94 + 0x34]              ; number of picks made
             for i in n..1:
                 ptr = 0x0219C94C(i) ; w = [ptr]
                 ref = ((w << 1) >> 24) << 1 | ((w << 17) >> 31)
                 *** 0x021D21B0(side, ref, cid, 0) == THE MOVE, deck -> GY ***
```

`0x021D21B0` is the Deck-to-GY relocation — the counterpart of `0x021C6E74`
(hand->GY) and `0x021C6E98` (hand->banished). ⚠️ `0x02208DD4` is a RESOLVER: it runs
on `[0x0229AAFC+0x70]` and returns PHASE CODES (0x78..0x80), not the slot4
yield/done protocol, so its states have to be re-expressed rather than copied.

## The shape build 2 installs

`+10` becomes an ov5 wrapper that owns states 0..3 for the hand (by delegating to
`0x021E7245` unchanged) and states 4..6 for the Deck:

```
STAGE = 0                                  ; -> rel 2, the hand-Dragon row
if [0x0229AAFC+0x7C] <= 3:
    r0 = 0x021E7245(desc)
    if r0 == 0: return 0                   ; still selecting the hand card
    [0x0229AAFC+0x7C] = 4 ; [+0x74] = 0    ; hand done -> start the Deck half
    return 0
STAGE = 1                                  ; -> rel 3, the deck-Dragon row
state 4: count = 0x02243FA8(side, cid, 0); if 0 -> finish; prompt 0xD; state++; ret 0
state 5: 0x0219C430(side, 7, cid, 0); state++; ret 0
state 6: pull pick 1, 0x021D21B0(side, ref, cid, 0)
         STAGE = 2                         ; -> rel 4, so the TARGET step is correct
         0x021E5060(desc)                  ; the once-per-turn latch, which
                                           ;   0x021E7245's default arm never posts
         return 1
```

`STAGE` is the byte at `CAVE_DF_STAGE`; the row hook returns `r4 = 2 + STAGE`. It is
restored to 2 by the cost's own final state, so the target step and the activation
condition both read the either-GY row whether or not the cost ran.

---

# ✅ BUILT — CLAUSE 2, BUILD 2 (2026-08-18): THE TWO-ZONE COST

`patch_darkflare.verify()` = **74 PASS / 0 FAIL**; the 3-card test ROM
`rom_ew_lp_df.nds` = **264 PASS / 0 FAIL** across all three cards against the FINAL
image. `BUILD2_COST = True` gates the whole thing — setting it False re-ships
build 1's tag-only cost byte-for-byte.

## The record, before and after

```
build 1  cls3 {0x1646, 0x02208D19, 0, 0x021F05E9,   0x021E5061,   0x02235A4D}
build 2  cls3 {0x1646, 0x02208D19, 0, CAVE_DF_COND, CAVE_DF_COST, 0x02235A4D}
                                      0x0239C7AD    0x0239C6AD
```

Only `+0C` and `+10` change. The resolver, the target step and all five criteria
rows are exactly what the build-1 duel confirmed working.

## `+10` — CAVE_DF_COST, 200 B in a 0x100 reserve

Two zones need two machines, and that is forced rather than chosen: the mode-8
path's only callback `0x022065F9` hardcodes `cmp r1,#0x0B`, so it can never read a
Deck. The stub therefore delegates the hand half and re-expresses the Deck half:

```
STAGE = 0                                   ; -> rel 2, the hand-Dragon row
if [0x0229AAFC+0x7C] <= 3:                  ; steps 0..3 belong to the native cost
    r0 = 0x021E7245(desc)                   ; Genesis Dragon's "send 1 from hand"
    if r0 == 0: return 0                    ; still selecting
    [+0x7C] = 4 ; [+0x74] = 0               ; hand done -> hand over to the Deck half
    return 0
STAGE = 1                                   ; -> rel 3, the deck-Dragon row
step 4: n = 0x02243FA8(side, cid, 0); if n == 0 -> done
        0x0219A818(side, 0x0D)              ; the Deck prompt; step++, return 0
step 5: 0x0219C430(side, 7, cid, 0)         ; mode 6+1 == exactly one; step++, return 0
step 6: if [0x0229DD94+0x34] <= 0 -> done
        ptr = 0x0219C94C(1) ; w = [ptr]
        ref = ((w << 1) >> 24) << 1 | ((w << 17) >> 31)
        0x021D21B0(side, ref, cid, 0)       ; THE MOVE, deck -> GY
done:   STAGE = 2 ; 0x021E5060(desc) ; return 1
```

The staging on the engine's own slot4 step counter is the shape **Transcendent
Wings `0x1907`** uses natively (`cls0[626] +10 = 0x021EA055` picks on the FIELD in
steps 0/1, then arms a HAND send in step 2) — a two-zone ignition cost is not a new
mechanism, it is an attested one.

⚠️ **`0x021E5060` is called explicitly, and that is not belt-and-braces.**
`0x021E7245` posts the once-per-turn latch only from a per-cid switch arm in its
state 3; the DEFAULT arm our donor takes branches straight to `movs r0,#1 ; pop`
and posts nothing. Swapping `+10` to `0x021E7245` directly would have bought the
hand send and **silently lost the once-per-turn that build 1 confirmed working**.

## `+0C` — CAVE_DF_COND, 80 B in a 0x80 reserve

Found while writing the cost, and it is a real correctness bug rather than polish:
Card Ejector's native gate `0x021F05E9` probes exactly ONE criteria row, and with
STAGE at rest that row is the either-GY target. So a player with a Dragon in hand
but none in the Deck could activate, lose the hand Dragon, find nothing to send
from the Deck, and still resolve — a half-paid cost.

```
STAGE = 0 ; if 0x02243FE0(side, cid, 0) == 0 -> return 0     ; no Dragon in hand
STAGE = 1 ; if 0x02243FE0(side, cid, 0) == 0 -> return 0     ; no Dragon in Deck
STAGE = 2 ; tail -> 0x021F05E9(desc, event)                  ; once-per-turn + a GY card
```

⚠️ `r1` (the EVENT) is preserved across both probes — `otn-shooting-quasar`'s trap,
which this project has already paid for once. And STAGE is restored to 2 on **every**
exit including the rejections, so a refused activation cannot leave the target step
or the next condition poll reading the wrong row.

## Why an ov5 `+10` is safe here (it was not for Lightpulsar)

`timing.class_is_the_slot4_literal`: the classifier reads `+0x10` as a LITERAL and
an unrecognised pointer leaves the effect UNCLASSIFIED — which for Lightpulsar's
clause 3 meant the engine said nothing when the trigger was lost, and needed PART T.
That applies to TRIGGER effects. This is an IGNITION: the player activates it from
the field, so there is no timing to miss. The three native ignition monsters
profiled for this card all carry non-tag `+10` values and work — Zombie Master
`0x021EAC0D`, Genesis Dragon and Vanguard `0x021E7245`.

## Differential — clean

`rom_ew_lp.nds` -> `rom_ew_lp_df.nds`, whole cls3 table: **only `0x1646` (gains the
record) and phantom `0x164B` (dropped)**. Every other cid's cls3 block is
byte-identical. The criteria registry is unchanged from build 1 — all five rows went
in during build 1 precisely so build 2 could not renumber anything.

## Slots

| slot | addr | size |
|---|---|---|
| `CAVE_ROWHOOK` | `0x0239C5A8` | 108 / 0x100 |
| `CAVE_DF_STAGE` | `0x0239C6A8` | 4 / 0x4 |
| `CAVE_DF_COST` | `0x0239C6AC` | 200 / 0x100 |
| `CAVE_DF_COND` | `0x0239C7AC` | 80 / 0x80 |
| `CAVE_FREE` | `0x0239C82C` | ~0x18F4 left |

`check_allocations` = 99 ov5 slots, 59 phantom claims, 106 B ov3 free, no overlaps.

## ⏳ IN-GAME TEST — BUILD 2

On `data/over_the_nexus/working/rom_ew_lp_df.nds`:

1. Darkflare on the field, **≥1 Dragon in hand AND ≥1 Dragon in Deck**, cards in
   both GYs → offerable.
2. Activate → prompt for a Dragon **from the hand**, then a Dragon **from the
   Deck**, and **both** go to the GY — **before** the target prompt.
3. → target 1 card in **EITHER GY** — ⚠️ **test your OWN GY explicitly**, the one
   question build 1 left open and the only thing that validates `0x0223D741` — and
   banish it.
4. **Once per turn** (this is the check most at risk: the latch moved from the
   native tag into our stub).
5. **Not offerable** with no Dragon in hand, and **not offerable** with no Dragon in
   the Deck — the `+0C` gate.
6. Regression: clause 1 still summons and banishes a LIGHT + a DARK; Lightpulsar's
   three clauses still work.

Failure readings, so the duel is decisive either way:
- **hand prompt then nothing** → the Deck half's step 4 found 0 candidates, i.e. the
  row hook is not returning rel 3 for STAGE 1, or `0x02243FA8` does not honour the
  deck handler on this path.
- **both prompts, but the Deck card is not sent** → `0x021D21B0`'s argument order or
  the ref unpack is wrong (it is copied from `0x02208DD4`, so compare against a live
  Foolish Burial activation).
- **works but is repeatable in a turn** → `0x021E5060` is not the latch write for an
  ignition, and the once-per-turn needs `0x021D2584` directly.

---

# ⛔ IN-GAME TEST — BUILD 2 NOT ACTIVATABLE (2026-08-18). THE GATE IS WITHDRAWN.

User-reported: *"I am now unable to activate Dark Flare"*, with savestate
`data/over_the_nexus/working/rom_ew_lp_df.ml2`.

Only two things changed between the activatable build 1 and build 2 — the cls3
record's `+0C` and `+10`. `+10` (the cost) runs only AFTER activation, so the
regression can only be `+0C`, the new `_stub_c2_cond` gate.

## ✅ What the savestate PROVES (parsed, not inferred)

Main RAM at file offset **0x24** (auto-detected via the `0x021A25A0` anchor —
`melonds-savestate-ram-offset`).

| check | value | verdict |
|---|---|---|
| ov5 resident? `[0x0239C5A8]` | `4B13 6D1B` = `ldr r3,[pc,#0x4C] ; ldr r3,[r3,#0x50]` | ✅ the row hook is in RAM |
| `[0x0239C6AC]` (cost) | `B5F0 1C04` = `push {r4-r7,lr} ; adds r4,r0,#0` | ✅ installed |
| `[0x0239C7AC]` (gate) | `B570 1C04` = `push {r4,r5,r6,lr} ; adds r4,r0,#0` | ✅ installed |
| STAGE `[0x0239C6A8]` | **2** | ✅ at its resting value — no stub left it dirty |
| hook site `[0x02243BEC]` | `58f1dcfc` — a BL | ✅ hooked |
| player Deck (`player+0x304`, count `player+0x10` = 25) | **6 Dragon monsters**: Malefic Stardust Dragon x2, Divine Dragon Ragnarok, **Battle Footballer 0x1646 x2 (Darkflare itself)**, Sword Arm of Dragon 0x0FB1 (Lightpulsar) | ✅ the Deck requirement was MET |
| player hand (`player+0x124`) | Bottomless Trap Hole, D.D.R., Solemn Warning, Mirror Force, Bottomless Trap Hole, **Sword Arm of Dragon 0x0FB1 — a Dragon MONSTER in this ROM** | ✅ the hand requirement was MET |

**So the gate refused an activation whose cost was payable.** At least one of its two
`0x02243FE0` probes returns 0 while the candidates demonstrably exist.

## ❌ Hypotheses falsified while diagnosing

- **"`0x02243FE0` is not a counter."** It is: it calls `0x02243B9C(cid, param)`,
  saves the candidate count `[0x0229944C+6]`, runs the walker `0x02243F38`, and
  returns the DELTA (restoring the count). A negative row index short-circuits to 0.
- **"The hand row's handler is not countable."** All three handlers are the same
  `(row, player)` thunk shape, and all three walkers reach the candidate recorder
  `0x02243B2C` (`0x0223BFD4` hand ✅, `0x0223BC3C` deck ✅, `0x0223C4E8` GY via
  `0x0223C1C4` ✅).
- **"The stubs are not resident / ov5 is evicted."** Disproven by the savestate above.
- **"STAGE was left dirty by a rejected poll."** It reads 2, the resting value.

## ⚠️ The one asymmetry noticed but NOT yet tested

The HAND handler `0x0223CB65` is the only one of the three that does **not set `r2`
itself** (`0x0223CAD9` and `0x0223D741` both do `movs r2,#0`); it inherits whatever
its caller left there, and passes a third stack argument `[sp+8] = 0x11` that the
other two do not. So a hand row may only be countable from the caller that natively
uses it — the mode-8 per-candidate callback `0x022065F9` — and not from a bare
`0x02243FE0` probe. **Unproven.**

## What shipped instead

`BUILD2_GATE = False`. The record's `+0C` goes back to the native `0x021F05E9`,
which build 1 proved activatable; `+10` keeps the two-zone cost. Both stubs are
still built and installed, so the bytes and the analysis survive — only the record
stops pointing at the gate. `verify()` asserts which of the two is wired.

**Consequence, stated plainly:** the card is once again activatable and should now
pay both sends, but it is NOT yet gated on the cost being payable — activating with
no Dragon in hand or none in the Deck will do whatever the cost does when it finds
nothing, which is untested.

## ⏳ NEXT EXPERIMENT — and this duel answers TWO questions at once

Rebuild is done: `rom_ew_lp_df.nds`, **264 PASS / 0 FAIL**.

1. Activate Darkflare's effect. **What does the FIRST prompt offer?**
   - Dragon monsters **from your hand** -> the row hook fires and resolves rel 2.
     That clears the row hook of blame and pins the gate's failure on the probe
     contract (the `r2` asymmetry above).
   - LIGHT monsters **in your GY** -> the row hook is NOT firing during the cost, so
     everything is resolving to rel 0, clause 1's row. That would also mean build 1's
     apparent success proved less than it looked: "banish a card from the GY" is
     equally consistent with rel 0, since clause 1's row is itself a GY selection.
   - nothing at all -> the cost's step 0 is not reached.
2. Then: does a **Deck** prompt follow, and do both cards reach the GY?
3. And the still-open build-1 question: when targeting, **is your own GY offered**?

⚠️ Do NOT re-enable `BUILD2_GATE` until (1) is answered. Per `otn-escalate-to-
measurement`, two failed hypotheses on one subsystem means instrument rather than
patch: if (1) shows the hook firing, the next step is a write-once latch in the cave
recording each `0x02243FE0` probe's return, not another guess.

## Data point (2026-08-18, user): OWN GY WAS OFFERED in build 1

*"i can answer that my own GY was offered previously."*

⚠️ **This rules out one thing and settles less than it appears to.**

- ✅ **RULED OUT: `0x0223D6FD` (opponent-GY only) being in effect.** That handler
  could never have offered the player's own Graveyard.
- ❌ **NOT settled: whether the row hook fires.** Clause 1's rel-0 row is *itself*
  an own-GY selection — handler `0x0223CA11`, word `0x01000002` = a LIGHT MONSTER
  in YOUR GY. So "my own GY was offered" is equally consistent with rel 4 (the
  intended either-GY any-card row) and with rel 0 (the hook silently not firing and
  every lookup falling back to clause 1's row).

The two observations that DO discriminate, both available in the next duel:

| observation | rel 4 (hook fires) | rel 0 (hook does not) |
|---|---|---|
| a **Spell or Trap** in a GY is selectable | yes — word `0x0001000E` is ANY CARD | no — `0x01000002` is monster-only |
| the **opponent's** GY is offered | yes — flags bit 1, both sides | no — `0x0223CA11` is own-side |
| the first cost prompt shows **Dragons in hand** | yes — rel 2 | no — it would show GY LIGHT monsters |

This matters beyond the target step: if the hook is not firing, that is also the
most likely explanation for the withdrawn `+0C` gate's failure, since both of its
probes would then have been reading rel 0 (a LIGHT monster in the GY) rather than
the hand and Deck rows — and an empty-of-LIGHT Graveyard would refuse the
activation exactly as observed.

## ✅✅ CORRECTION + THE ROW HOOK IS CONFIRMED FIRING (2026-08-18)

User clarification: *"I meant that I was able to activate the effect WITHOUT the 1
LIGHT in the GY, there were still 4 cards in the GY."*

**That is the discriminator, and it settles the open question.**

| row the lookup could resolve to | candidates on that board | verdict |
|---|---|---|
| rel 0 — clause 1's LIGHT MONSTER in your GY | **0** (no LIGHT in the GY) | would have REFUSED |
| rel 4 — ANY CARD in either GY | **4** | activatable — what was observed |

=> **The row hook FIRES and resolves rel 4.** `dispatch.criteria_handler_flags_word`
holds, `0x0223D741` is the correct either-GY handler, and the whole rel-2/3/4 block
is reachable. The earlier "own GY was offered" report is now explained properly: it
was rel 4, not clause 1's row.

⚠️ **My previous entry's STAGE-leak hypothesis is FALSIFIED** — it was written
against "activatable with an EMPTY GY", which was a misreading of the report. The GY
was never empty. Keeping the correction visible rather than deleting it, because the
lesson is the one this project keeps re-learning: I built a mechanism-level theory on
a second-hand summary of a board state instead of the board state itself.

### The withdrawn `+0C` gate — root cause, now concrete and testable

With the hook proven to work, the gate's failure has a specific candidate:

1. **THE SIDE ARGUMENT.** The native `0x021F05A8` computes
   `side = desc[+2] ^ desc[+6]` before calling `0x02243FE0` — and the on-field
   enumerator `0x0224BCF2` sets **`desc[+6] = 1`**, so the effective side is the
   OPPOSITE of `desc[+2]`. `_stub_c2_cond` passed `desc[+2]` raw.
2. **AND THE HAND HANDLER FLIPS AGAIN.** `0x0223CB65` passes `[sp+8] = 0x11` to its
   walker `0x0223BFD4`; per `dispatch.criteria_handler_flags_word` **bit 0 = scan the
   OPPONENT's side**. So the hand probe lands on the opponent's hand — which in the
   duel held no Dragons -> count 0 -> refuse, exactly the symptom.
3. **WHY THE GY ROW SURVIVED THIS.** `0x0223D741`'s flags are `0x00010003`: bit 1 =
   scan BOTH sides, so the side argument barely matters for rel 4. That is why the
   native condition works while the two new probes did not.

**Next experiment (one constant each, then ONE duel):** pass
`desc[+2] ^ desc[+6]` as the side in `_stub_c2_cond`, and account for
`0x0223CB65`'s bit-0 flip on the hand probe. Do NOT re-enable `BUILD2_GATE` before
the diagnostic latch confirms the side actually reaching the walker.

### STILL UNANSWERED, and it is now the only thing build 2 needs
Does the activation prompt for a Dragon **from the hand** and then one **from the
Deck**, and do both reach the Graveyard? Every report so far has been about
ACTIVATION, not about the cost being paid.

## ✅✅✅ THE COST WORKS IN-GAME (2026-08-18)

User: *"when it is activated with a dragon in hand and dragon in deck, the effect
works perfectly, so it is literally just that that is stopping the card from being
shipped."*

**Build 2's whole point is confirmed**: the activation prompts for a Dragon from the
HAND, then a Dragon from the DECK, sends both to the Graveyard, then targets and
banishes a card in either GY. The two-zone cost -- the piece the handoff prompt
called "unattested, the real research" -- is done, and it is the shape Transcendent
Wings 0x1907 uses natively: two zones, two machines, staged on the engine's own
slot4 step counter.

Confirmed working end to end: the shared row hook (re-homed), rel 2 / rel 3 / rel 4,
`0x0223CB65` hand + `0x0223CAD9` deck + `0x0223D741` either-GY, `0x021E7245` for the
hand send, the cloned list-zone Deck states with `0x021D21B0`, `0x02235A4D` target,
`0x02208D19` banish -- and clause 1 and Lightpulsar both unregressed throughout.

## THE LAST BLOCKER, AND ITS FIX — the side argument

Remaining defect: activatable with no Dragon in hand or Deck, i.e. the `+0C` gate.
Root cause, diagnosed from the confirmed behaviour rather than guessed:

**The criteria walkers want `side = desc[+2] ^ desc[+6]`, not `desc[+2]`.** The
native gate `0x021F05A8` computes exactly that (`ldrb r1,[r5,#2] ; ldrb r0,[r5,#6] ;
eor r6,r0`) before calling `0x02243FE0`, and the on-field enumerator `0x0224BCF2`
sets **`desc[+6] = 1`** -- so the raw `desc[+2]` the first draft passed addressed the
**OPPONENT**. That is why the gate refused an activation whose cost was payable: it
was counting Dragons in the opponent's hand and Deck.

⚠️ And why the GY probe never showed the bug: `0x0223D741`'s flags are `0x00010003`
and **bit 1 = scan BOTH sides**, so for rel 4 the side argument barely matters. Only
the hand and deck probes were exposed. A side bug that is invisible on two thirds of
your call sites is exactly the kind this project keeps paying for.

`BUILD2_GATE = True` again with `eors r0, r1` on both probes. Rebuilt:
`rom_ew_lp_df.nds`, **264 PASS / 0 FAIL**.

### The one duel that ships the card
1. Dragon in hand + Dragon in Deck + a card in a GY -> activates and works (already
   confirmed; this is the no-regression check).
2. **No Dragon in hand** -> must NOT be offerable.
3. **No Dragon in Deck** -> must NOT be offerable.
4. Once per turn still holds.

---

# ✅✅✅ DARKFLARE DRAGON IS COMPLETE — IN-GAME CONFIRMED (2026-08-18)

User: *"Perfect! Ship it!"* — after the side fix, the effect is gated correctly and
the whole card works.

| clause | mechanism | confirmed |
|---|---|---|
| 1 — SS from hand by banishing 1 LIGHT + 1 DARK from your GY | 5 in-place ov3 edits + the shared payment stubs; **no cave, puzzle-safe** | 2026-08-17, first test |
| 2 — OPT: send 1 Dragon from hand AND 1 from Deck to the GY, then target 1 card in either GY and banish it | 3 criteria rows at rel 2/3/4, a Card Ejector cls3 record, an arm on the shared row hook, a 200 B two-zone cost and an 88 B gate | 2026-08-18 |

Donor **Battle Footballer `0x1646`** -> Darkflare Dragon, DARK / Dragon / Lv5 /
2400 / 1200. Clause 2 is **duel-only** (ov5); clause 1 stays pure ov3.

## What it took, and the three things that actually cost the time

1. **The either-GY handler.** Settled offline by decoding the handler's pooled FLAGS
   word rather than guessing from words — and the 2026-08-05 note's guess
   (`0x0223D6FD`) would have silently narrowed the card to the opponent's Graveyard.
2. **The two-zone cost.** The handoff prompt called it "unattested — the real
   research". It was attested twice over: Transcendent Wings `0x1907` stages two
   zones in one slot4, and Dark Simorgh `0x1E5A` runs a two-pass cost with a
   per-pass computed filter. Finding those turned a research problem into a compose.
3. **`side = desc[+2] ^ desc[+6]`.** The only genuine bug, and it cost two duels
   because it is invisible on any row whose flags set bit 1 (scan both sides). The
   GY probe worked; the hand and Deck probes silently addressed the OPPONENT.

## The generalisable lessons, worth more than the card

- **Check the native card first.** Card Ejector `0x1D44` ships "once per turn: target
  1 card in a GY; banish it" as PURE DATA, and Genesis Dragon `0x1F2A` ships the
  send-from-hand ignition skeleton. Between them they supplied every slot; the only
  new code was the Deck half and the row-offset arm.
- **A shared hook wants a shared MODULE.** `criteria_row_hook.py` is the second
  instance of the pattern (after `handss_banish_cost.py`), and lifting it exposed
  three latent defects nobody would have found otherwise: `install_cave` cannot be
  re-run at one address, `check_allocations` silently recorded `size: null` for every
  `CAVE_LP_*` slot (so they were in NO overlap check), and `verify()` never loaded
  ov5 at all.
- **A board summary is not a board.** I built a mechanism-level theory (a STAGE leak)
  on a second-hand reading of "no cards in the GY", and it was wrong; the savestate
  had the answer both times. Parse the state, do not paraphrase it.

## KB

**254 facts, 222 PASS, 0 FAIL, 32 UNVERIFIED.** New this session:
`dispatch.criteria_handler_flags_word`, `dispatch.criteria_hand_vs_deck_handlers`,
`dispatch.onfield_ignition_is_a_cls3_record_only`,
`dispatch.criteria_probe_side_is_xor_desc6`, `card.darkflare_clause2`.

## Remaining, deliberately not done

- `0x0EA8` is the last unclaimed phantom with a 2-row criteria block.
- ⚠️ `check_allocations` records tg_striker's populate phantom as `0x2347`; the code
  uses `0x234E` (`patch_tg_striker.py:158`). `0x234E` therefore reads as unclaimed
  while one of its two rows is consumed. Not this card's bug; worth a one-line fix.
- Puzzle behaviour of clause 1 is still untested.

## Chain + sweep, final (2026-08-18)

`ALL 33 PATCHES APPLIED -> data/over_the_nexus/working/rom_all_patches.nds`.
Chain-wide sweep against the COMBINED ROM (positional `verify()`, catching
`BaseException`): **23 PASS, 12 expose no verify(), 4 not-PASS** — `patch_wonder_wand`,
`patch_bulk_ydcs`, `patch_unlock_all_packs`, `patch_zeta_reticulant`, all pre-existing
and **none in the applied chain**. Identical to the baseline every prior session
recorded. `patch_darkflare` and `patch_lightpulsar` both PASS against the combined
image. Ledger: 100 ov5 slots, 59 phantom claims, 106 B ov3 free, no overlaps, in sync.
