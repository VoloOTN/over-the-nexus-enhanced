# Lightpulsar Dragon — findings

> ## Session 2026-08-13 (implementation) — appended below at
> ## [§ Session 2026-08-13](#session-2026-08-13--implementation)
> The 2026-08-05 recon body follows first and is **still valid** (re-verified this
> session), with ONE correction and one new blocker — see the 08-13 section.

Session 2026-08-05. Scope chosen by the user: **RECON ONLY — map all three clauses,
build nothing.** No ROM code written, nothing built, no slot claimed in the ledger.

Outcome: **all three clauses have native in-ROM machinery**, and two of the three are
mostly *data*, not code. Six new engine facts contributed to the KB (all PASS).

## Card text (authoritative source)

From `scratch/ygoprodeck_cache.json`, id **99365553**, name "Lightpulsar Dragon":

> You can Special Summon this card (from your hand) by banishing 1 LIGHT and 1 DARK
> monster from your GY. You can Special Summon this card (from your GY) by sending 1
> LIGHT and 1 DARK monster from your hand to the GY. When this card is sent from the
> field to the GY: You can target 1 Level 5 or higher DARK Dragon monster in your GY;
> Special Summon that target.

Stats: **Effect Monster, LIGHT, Dragon, Level 6, ATK 2500 / DEF 1500.**
Not a Nomi card — it can still be Normal Summoned by tributing 1.

### Clauses

1. **(alt summon procedure, from hand)** SS this card from your hand by banishing 1
   LIGHT and 1 DARK monster from your GY.
2. **(alt summon procedure, from GY)** SS this card from your GY by sending 1 LIGHT
   and 1 DARK monster from your hand to the GY.
3. **(optional trigger, leave-field)** When this card is sent from the field to the
   GY: You can target 1 Level 5 or higher DARK Dragon monster in your GY; Special
   Summon that target.

Nothing is implemented yet, so there is no intra-card regression surface.

---

## Confirmed (this session — closed structural proofs against the ov3 oracle)

### KB health

`verify_knowledge` = 196 facts (190 before this session). Against the default
savestate two RAM facts FAIL; against the savestate they were *derived* from,
`data/over_the_nexus/working/sealancer_recon.ml3`, the run is
**167 PASS / 0 FAIL / 29 UNVERIFIED** (all 29 narrative). The two FAILs are an
oracle-selection artefact, not KB rot.

```
.venv-1/Scripts/python.exe -m otn_enhanced.knowledge.verify_knowledge \
    --savestate data/over_the_nexus/working/sealancer_recon.ml3
```

### Lightpulsar Dragon is absent from the ROM

`scratch/cid_to_name.json` (4305 cids) has zero hits for "pulsar". Donor conversion
+ `card_prop` retune required.

### All three clauses have native analogues already in the ROM

| Clause | Native analogue(s) in ROM |
|---|---|
| 1 | Chaos Sorcerer `0x16C9`, BLS - Envoy of the Beginning `0x16CB`, Chaos Emperor Dragon `0x16E4` — cost is *literally* "banish 1 LIGHT and 1 DARK monster from your GY" |
| 2 | Plaguespreader Zombie `0x1EA9`, Treeborn Frog `0x19CB`, Spore `0x225B`, Glow-Up Bulb `0x2387` |
| 3 | Decoy Dragon `0x1C4F` ("Lv7+ Dragon in GY; SS it"), Chaos Goddess `0x2273` ("Lv5+ **DARK** monster in GY; SS it") |

### Clause 3 — the criteria word is DATA, and it is nearly free

New fact `dispatch.criteria_word_level_field` (VERIFIED). The off-field criteria
registry word (`0x022713C4`, stride 12, row+0x08) has a LEVEL filter in bits 23:16:

```
[op:2 @7:6][level:4 @5:2][flag:2 @1:0]     op 0 = exactly, 1 = or higher, 2 = or lower
```

Decoded by cross-checking **every** registry row against its ygoprodeck text:
**177 level-bearing rows agree, 0 disagree**, spanning op 0 (levels 1,2,3,4,5,7,8),
op 1 (4,5,7) and op 2 (2,3,4,5,6,7). Combined with the already-VERIFIED top byte
(`race<<3 | attribute`, `dispatch.criteria_word_race_attribute`), the whole word is
now readable.

New fact `dispatch.criteria_gy_revive_handler` (VERIFIED). Criteria handler
**`0x0223C9D1`** is the "target 1 filtered monster in your **GY**; Special Summon it"
enumerator — family includes Premature Burial, Call of the Haunted, Decoy Dragon,
Dark Horus, Kinka-byo, Graceful Revival, Junk Synchron, Chaos Goddess. It pairs with:

- **slot1 `0x02207529`** — the shared revive resolver (slot1 of 27 records). Its
  per-cid switch only picks a MODE in `r4` and **defaults to 2 for an unnamed cid**
  (`movs r4,#2` @`0x0220754A`, leaves set 0/1 @`0x022075C2`/`0x022075C6`, all rejoin
  the common body @`0x022075C8`). So a donor cid the switch doesn't name still works.
- **slot5 `0x02235605`** — the off-field (list-zone) target picker template.

So clause 3's action needs **no new resolver code**. Target word:

| field | value | source |
|---|---|---|
| race Dragon(1) `<<3` \| attr DARK(2) | `0x0A` | proven byte split |
| op 1 (or higher), level 5 | `0x55` | copied verbatim from Chaos Goddess |
| low half | `0x0002` | whole family |
| **criteria word** | **`0x0A550002`** | |

Chaos Goddess `0x2273` is `0x02550002` = the same thing *minus* the Dragon race.
Clause 3's word is Chaos Goddess's word with the race nibble filled in.

### Clause 1 — the multi-card summon cost is DATA too

New fact `dispatch.multi_attribute_summon_cost_is_multiple_rows` (VERIFIED). A summon
procedure demanding **several different cards** is encoded as **multiple criteria rows
on the same cid**, selected by the `param` argument of `0x02243FE0`/`0x02243FA8` —
`param` IS the row index among that cid's rows:

- Chaos Sorcerer `0x16C9`, BLS-Envoy `0x16CB`, Chaos Emperor Dragon `0x16E4` each own
  **exactly two** adjacent rows: `0x01000002` (LIGHT) + `0x02000002` (DARK), handler
  `0x0223CA11`.
- The single-attribute members own **exactly one**: Inferno `0x16C5` FIRE, Fenrir
  `0x16C6` WATER, Gigantes `0x16C7` EARTH, Silpheed `0x16C8` WIND.

New fact `handss.banish_cost_leaf` (VERIFIED). The consumer is the hand-SS cid tree:
the banish-summon family is a contiguous cluster at `0x0225E88x–0x0225E8DE` with the
compare base in `R7 = 0x16C6` (Fenrir), splitting into exactly two leaves:

- **`0x0225FA36`** — single attribute (Inferno / Fenrir / Gigantes / Silpheed)
- **`0x0225FA46`** — LIGHT + DARK (Chaos Sorcerer / BLS-Envoy / CED) ← **clause 1**

`0x0225FA46` is **generic in the cid** — it holds no cid-specific constant. It runs
two identical passes: `strh 0,[g+0x28]` → `0x02243FE0(side, cid, 0)`, then
`strh 1,[g+0x28]` → `0x02243FE0(side, cid, 1)`, each comparing the criteria hit count
against the required count from `0x0225CF28(cid)`.

**Consequence:** clause 1 = two criteria rows on the donor cid + reaching
`0x0225FA46` in the tree. The only *code* change is the tree branch.

### Clause 2 — one shared resolver, per-card cost/condition

New fact `handss.self_ss_from_gy_resolver` (VERIFIED). "SS this card from your GY by
\<cost\>" is a **single shared cls2 slot1 resolver, `0x0220731D`**, used by **69 cls2
records** (Treeborn Frog, Plaguespreader, Spore, Quillbolt Hedgehog, Wulf, Fabled
Lurrie, Ronintoadin, Stardust Dragon, Vampire Lord, the three Aesir lords, …). Like
the revive resolver, it is cid-switched only to pick a mode in `r4`
(`movs r4,#0` @`0x02207324`) and every unmatched compare reaches the **common body at
`0x022073E8`** — an unnamed donor cid runs the default path.

The per-card cost and condition are **not** in the resolver; they are the record's
slot3/slot4:

| card | slot3 (+0x0C, condition) | slot4 (+0x10, cost) |
|---|---|---|
| Plaguespreader `0x1EA9` | `0x021FF06D` | `0x021E9039` |
| Treeborn Frog `0x19CB` | `0x021FA585` | `0x021E7969` |
| Spore `0x225B` | `0x021F0BDD` | `0x021E5319` |

So clause 2 reuses `0x0220731D` wholesale; the work is a slot3 ("are there 1 LIGHT +
1 DARK in hand?") and a slot4 (send them). **This was my pre-session estimate's biggest
error — I had called clause 2 the expensive one; it is structurally the same shape as
the others.**

### cls3 is the on-field IGNITION table, not summon procedures

Chaos Sorcerer's only cls record is `cls3[152]`, and its slot3 `0x021F7425` / slot4
`0x021E91B9` are **shared with Volcanic Slicer, Sky Scourge Enrise, Venom Snake, Venom
Boa, Super Conductor Tyranno, Enishi** — i.e. generic on-field ignition condition/cost.
That record is Chaos Sorcerer's *once-per-turn banish* effect, **not** its summon
procedure (which lives in the hand-SS tree). BLS-Envoy has both: `cls1[335]` (ignition)
and `cls3[153]`. This refines `dispatch.cls_table_selector`.

### Donor selection — records-free Normal Monsters

User decision (2026-08-05): **Summoned Skull is excluded**, any other Normal Monster
is acceptable.

Six filters, strictest first:

1. ygoprodeck type == "Normal Monster" (authoritative — **not** the ROM decoder, whose
   race/attribute columns are known-unreliable, see Open Question 6)
2. ROM `card_prop` also Normal, Level 6
3. no record in cls0/cls1/cls2/cls3
4. no row in the off-field criteria registry `0x022713C4`
5. **cid never appears as a compare constant in the hand-SS / summon-restriction region
   `0x0225E51C..0x02260400`** — missed on the first pass; it disqualified Ushi Oni
   `0x1137` and Firewing Pegasus `0x1270`
6. **not used as a fusion material** in recipe table A `0x02270B94` / table B
   `0x02270B58` — it disqualified **Meteor Dragon `0x126E`**, which is the material for
   Meteor B. Dragon (this one nearly slipped through: `0x126E` is Dragon-race and
   already Level 6, so it looked like the ideal pick)

**CHOSEN (user decision, 2026-08-05): Armored Lizard `0x0FD9`** — Reptile / EARTH,
Level 4, 1500/1200.

Vetted against all six filters — **CLEAN on every one**: no cls0/cls1/cls2/cls3 record,
no criteria-registry row, absent from the summon-restriction tree, not a fusion
material, not a fusion result.

`card_prop` retune needed (larger than a Level-6 Dragon donor, but routine):

| field | from | to |
|---|---|---|
| level | 4 | 6 |
| race | Reptile | Dragon |
| attribute | EARTH | LIGHT |
| ATK / DEF | 1500 / 1200 | 2500 / 1500 |

Writing all four is an **established shipped path** — `patch_bulk_card_props.py`
already sets `race` (Molten Zombie `0x16F7`), `attribute_encoded` (Gazelle `0x1291`)
and `level` for ~10 cards. The card_prop caution in Open Question 6 is about *decoding*
that file for filtering, **not** about writing it.

Other candidates considered, all CLEAN on every filter (Level 6, so a smaller retune):

| cid | name | ATK/DEF | race/attr | note |
|---|---|---|---|---|
| `0x14E5` | Luster Dragon #2 | 2400/1400 | **Dragon**/WIND | already Dragon + Level 6 = smallest retune |
| `0x17CE` | Neo Aqua Madoor | 1200/3000 | Spellcaster/WATER | most obscure |
| `0x1285` | Steel Ogre Grotto #2 | 1900/2200 | Machine/EARTH | |
| `0x112A` | Pendulum Machine | 1750/2000 | Machine/DARK | |
| `0x13E4` | Gadget Soldier | 1800/2000 | Machine/FIRE | |
| `0x1B31` | Frostosaurus | 2600/1700 | Dinosaur/WATER | closest raw stats |
| `0x0FB1` | Sword Arm of Dragon | 1750/2030 | Dinosaur/EARTH | |
| `0x0FC7` | Judge Man | 2200/1500 | Warrior/EARTH | |
| `0x0FF5` | Megazowler | 1800/2000 | Dinosaur/EARTH | |
| `0x1120` | Swordstalker | 2000/1600 | Warrior/DARK | |
| `0x11B7` | Flame Cerebrus | 2100/1800 | Pyro/FIRE | |
| `0x13CA` | Amphibian Beast | 2400/2000 | Fish/WATER | |
| `0x1D74` | Ally of Justice Clausolas | 2300/1200 | Machine/DARK | |

---

## Ruled Out

- **"Clause 2 has no mapped machinery" (my own pre-session estimate).** Wrong — it is
  the best-shared path of the three (69 cards on one resolver).
- **"Chaos Sorcerer's summon procedure is in its cls record."** Wrong — `cls3[152]`
  is its on-field ignition effect; the summon procedure is in the hand-SS cid tree.
- **A bespoke criteria handler (Unicorn Beacon style) is needed for clause 3.** Not
  needed: clause 3 wants ONE race + ONE attribute + one level op, all of which fit a
  plain row. (Sea Lancer needed a bespoke handler only because it wanted *three* races.)

---

## Open Questions

1. **The constructed criteria word `0x0A550002` is unattested for Dragon.** All 35
   Dragon-race rows in the ROM have attribute 0 — no row anywhere combines Dragon with
   an attribute. The byte split itself is VERIFIED (Agent of Miracles - Jupiter `0x2449`
   = `0x89` = Fairy|LIGHT), so `0x0A` is well-formed by construction, but the
   combination has never been exercised in this engine. **Verify at runtime before
   trusting it.**
2. **`0x0225CF28`'s fall-through** (new fact `handss.banish_cost_count_default`,
   UNVERIFIED). It returns the required banish count per cid and is a per-cid compare
   tree, not a table. If the unnamed-cid default is 0 the cost check passes vacuously
   (free summon); if it is 1 the donor needs no edit. Gates whether clause 1 is pure
   data or needs a tree edit.
3. **Can a cls2 leave-trigger row carry slot1 `0x02207529` + slot5 `0x02235605`?**
   The revive resolver's native family is cls0/cls1/cls3 (spells/traps). Clause 3 needs
   it on a cls2 *trigger* row. Plausible from `dispatch.cls_slot_roles` but **inference,
   not proven.**
4. **Clause 3's trigger scope.** "Sent from the field to the GY" must include
   destroyed-by-battle and destroyed-by-effect. Per `leave.gate` `0x021CA640` the gate
   *omits* DESTROYED, and `leave.descriptor_slots` (UNVERIFIED) puts DESTROYED at
   `[sp+0x90]` and to-GY at `[sp+0x144]` at hook `0x021C8216`; native mask table
   `0x0226EC1C` has `0x0C04` = destroyed + to-GY. Needs confirming.
5. **Clause 2's slot3/slot4 bodies** (`0x021FF06D` / `0x021E9039` etc.) were not
   disassembled — the *shape* is proven, the *contents* are not.
6. **`card_prop` race/attribute decode is unreliable** via
   `scratch/bin2/card_prop.bin` + `card_prop_codec`: the same card name appears with
   contradictory races (Dark Magician as Insect / Psychic / Fiend / Aqua across its
   alternate arts). Level and ATK/DEF decode correctly. Do **not** build a donor filter
   on the race/attribute columns from that path.

---

## Next Experiment

In dependency order; **1 and 2 are offline** (no emulator needed), so do them first.

1. **Resolve `0x0225CF28`'s fall-through (offline first, then GDB).** Disassemble to
   the arm every unmatched compare branches to and read the returned immediate. Because
   this is a stack-based switch, a register-only simulation can report the WRONG leaf
   (`thumb.stack_switch`) — confirm with GDB: breakpoint `0x0225CF28`, read `r0` at
   return, for a records-free cid.
2. **Prove the criteria-row insert is count-neutral.** The registry is sorted,
   binary-searched, and its count literal `0x56C` lives at `0x02243DF8`. Clause 1 needs
   **2** new rows and clause 3 needs **1**, all on the donor cid — so 3 phantom rows
   must be dropped to stay count-neutral. Identify the phantoms before writing anything.
3. **Runtime-check the `0x0A` race+attribute byte (GDB, one shot).** Give the donor a
   single criteria row `0x0A550002` + handler `0x0223C9D1`, breakpoint the enumerator
   `0x02243FA8`, and confirm it counts exactly the Lv5+ DARK Dragons in the GY (seed the
   GY with one DARK Dragon Lv6, one DARK Dragon Lv4, one LIGHT Dragon Lv6, one DARK
   non-Dragon Lv6 — only the first should match). This single experiment settles Open
   Question 1 and de-risks the whole of clause 3.
4. **Then** decide clause order. Recommended: **clause 3 first** (most data-driven,
   independent of the summon-procedure subsystem), then clause 1, then clause 2.

⚠️ Per CLAUDE.md the melonDS GDB stub is **one-shot**: plan the entire experiment
offline, connect **once**, arm every breakpoint, collect in a single wait window, and
write results to a file.

---

## Slots this work would claim (NOT claimed yet — recon only)

Listed so the next session can check collisions before writing:

- donor cid `0x0FD9` (Armored Lizard) — records-free in all four cls tables, absent
  from the criteria registry, absent from the summon-restriction tree, neither a fusion
  material nor a fusion result, not in `PHANTOM_CLAIMS`.
- `card_prop` row for `0x0FD9` (level / race / attribute / ATK / DEF).
- 3 new criteria-registry rows on `0x0F0A` (2 for clause 1, 1 for clause 3) + 3 phantom
  rows dropped to stay count-neutral.
- 1 cls2 record for clause 3's trigger; 1 cls2 record for clause 2.
- hand-SS cid-tree branch reaching `0x0225FA46` for clause 1.
- ov5 cave: **none needed so far** — every clause currently maps to native code + data.

---

## KB contributions this session

Added to `otn_enhanced/knowledge/author_facts.py` and regenerated
(`--check` = 164 PASS / 2 pre-existing savestate FAILs / 30 UNVERIFIED; full
`verify_knowledge` on the right savestate = **196 facts, 167 PASS, 0 FAIL**):

| id | grade |
|---|---|
| `dispatch.criteria_word_level_field` | VERIFIED |
| `dispatch.criteria_gy_revive_handler` | VERIFIED |
| `dispatch.multi_attribute_summon_cost_is_multiple_rows` | VERIFIED |
| `handss.banish_cost_leaf` | VERIFIED |
| `handss.self_ss_from_gy_resolver` | VERIFIED |
| `handss.banish_cost_count_default` | UNVERIFIED (+ `next_experiment`) |

---

# Session 2026-08-13 — implementation

Scope: user said "continue with the implementation". Recon body above re-verified
against the current KB before anything else. **No ROM bytes written yet** at the
time of writing; awaiting clause-scope confirmation.

## Confirmed (this session)

### Inherited state re-verified — all green
- `verify_knowledge --savestate data/over_the_nexus/working/sealancer_recon.ml3`
  = **219 facts, 189 PASS, 0 FAIL, 30 UNVERIFIED**. KB grew 196 -> 219 since the
  recon session (Escuridao et al. shipped in between); **no Lightpulsar fact
  rotted**. All six recon facts PASS: `dispatch.criteria_word_level_field`,
  `dispatch.criteria_gy_revive_handler`,
  `dispatch.multi_attribute_summon_cost_is_multiple_rows`,
  `handss.banish_cost_leaf`, `handss.self_ss_from_gy_resolver`
  (+ `handss.banish_cost_count_default` still UNVERIFIED, as filed).
- **Donor Armored Lizard `0x0FD9` is STILL CLEAN** — re-proved this session, not
  inherited: `donor.vetting_beyond_cls_records` PASSES and its proof body asserts
  `0x0FD9` has no cls0/cls1/cls2/cls3 record, no criteria row, is not a fusion
  material and not a fusion result.
- Allocation ledger clean: **87 ov5 slots (78 live), 29 phantom claims, 5 ov3
  dead-code claims (84 B free), no overlaps, ledger in sync.**
  `ov5_cave.CAVE_FREE = 0x0239C1A8` (moved from the recon session's `0x0239C014`).
- Card text re-read from `scratch/ygoprodeck_cache.json` id 99365553 — **identical**
  to the text quoted in the recon body. Not from recall.
- Criteria registry still 1388 rows, count literal `0x56C` @`0x02243DF8`, **sorted
  by cid** (verified this session).

### ✅ CORRECTION to the recon body — clause 2 needs NO criteria rows
The recon's "slots this work would claim" implies registry rows for all clauses.
Measured this session: the self-SS-from-GY family mostly owns **zero** rows —
Treeborn Frog `0x19CB`, Quillbolt Hedgehog `0x1E15`, Wulf `0x1DAC`, Stardust
Dragon `0x1E36` all have **0 criteria rows**. (Plaguespreader `0x1EA9` and Spore
`0x225B` own one each, but under unrelated handlers `0x0223CB19` / `0x0223FE41`,
not the self-SS path.) So **clause 2's cost lives entirely in the cls2 record's
slot3/slot4** — it consumes no registry rows and cannot perturb the row block.
Registry budget is therefore **3 rows, not 5**.

### ⚠️ NEW BLOCKER — `param` is the RELATIVE row index, so clause 1 and clause 3 fight over it
`dispatch.criteria_registry_lookup_default` (VERIFIED) says the lookup walks back
to the **leftmost row for the cid**, and
`dispatch.multi_attribute_summon_cost_is_multiple_rows` (VERIFIED) says `param`
**is the row index among that cid's rows**. Both clauses put rows on the SAME cid
(`0x0FD9`), so their relative order is load-bearing:

- clause 1's leaf `0x0225FA46` hardcodes two passes, `param = 0` then `param = 1`
  (`strh 0,[g+0x28]` @`0x0225FA6A`, `strh 1,[g+0x28]` @`0x0225FA8A`) — so clause 1
  **must** own relative rows 0 and 1.
- clause 3's revive row would then be forced to relative row **2**.

Measured distribution of the revive handler `0x0223C9D1`'s relative index across
all 45 rows that carry it: **`{rel 0: 42, rel 1: 3}` — rel 2 is UNATTESTED.**
The three rel-1 cases are The Dark Creator `0x1CFB`, Lava Dragon `0x1FFD` and
**Chaos Goddess `0x2273`**.

**Chaos Goddess is the exact structural template Lightpulsar needs** and it is the
very card the recon proposed copying the criteria word from:

| rel | cid `0x2273` block | handler | word | meaning |
|---|---|---|---|---|
| 0 | row 1159 | `0x0223CB65` | `0x01000002` | its summon-cost row (LIGHT) |
| 1 | row 1160 | `0x0223C9D1` | `0x02550002` | GY-revive target, DARK Lv5+ |

Lightpulsar's clause-3 word `0x0A550002` is literally row 1160's word with the
Dragon race nibble filled in — and it sits at a **non-zero relative index there**,
which is the proof that the revive consumer is not hardwired to `param = 0`.

**Also measured: NO cid in the ROM owns both a revive row (`0x0223C9D1`) and a
banish-cost row (`0x0223CA11`).** The combination clause 1 + clause 3 needs is
**unattested in the engine** — this is the single biggest risk in the card.

### Registry facts measured this session
- 118 cids own >1 criteria row; **max block size is 4**.
- **106 cids** own multiple rows under **different handlers**, so a mixed-handler
  block is ordinary (e.g. Book of Life `0x1536` = revive row + `0x0223D6FD` row).
- **100 rows are phantoms** (cid absent from `scratch/cid_to_name.json`) — an ample
  pool of count-neutral drop candidates for the 3 rows this card needs.

### ✅ RESOLVED — Open Question 1: how the engine addresses a cid's Nth criteria row

The `param`/relative-row question is **fully answered offline this session**. The
disambiguation stage returns `leftmost_row_index + r4`, and what sets `r4` is a
**three-tier mechanism keyed purely by block size**:

| block size | how it is addressed | population |
|---|---|---|
| **1 row** | default leaf `0x02243EEC`, `r4 = 0` | **1141 cids** |
| **2 rows** | cid must appear in **membership list A `0x0227134C` (59)** or **B `0x02271314` (27)** -> `r4 = 1` leaf `0x02243EC6` | **108 cids** |
| **3-4 rows** | cid must be a case in the **compiled switch @`0x02243C1C`** | **10 cids** |

Block-size histogram over the whole registry: **`{1: 1141, 2: 108, 3: 9, 4: 1}`**.

Proof of the 2-row tier: **every cid in membership list A or B owns exactly 2 rows**
(the only exceptions are two Speed Spells with 0 rows). The lists are literally a
"this cid owns a two-row block" register. Both are **sorted** (binary-searched,
hard-coded counts `0x3B` / `0x1B`).

This is exactly how the two families Lightpulsar copies work:
- clause 1's Chaos family `0x16C9` / `0x16CB` / `0x16E4` are **all in list A** — that
  is how their `param = 1` pass reaches their DARK row.
- clause 3's template Chaos Goddess `0x2273` is **in list B** — that is how its
  revive row at rel 1 is reachable.

Proof of the 3-row tier: of the 10 cids owning 3+ rows, **8 are in the 22-case
compiled switch** (`0x0D6B`, `0x0E12`, `0x1522` Vampire Lord, `0x1746` Vampire Lady,
`0x1E5A` Dark Simorgh (4 rows), `0x210E`, `0x22D6`, `0x24AD`). Caveat: `0x21BC`
Koa'ki Meiru Urnight and `0x2449` Agent of Miracles - Jupiter own 3 rows and are in
**neither** the lists nor the switch-case list inherited from
`dispatch.criteria_registry_lookup_default` — so either that fact's 22-case
enumeration is incomplete, or those cards' 3rd row is vestigial. **Not resolved.**

### ⚠️⚠️ THE REAL BLOCKER, restated precisely

Lightpulsar wants **3 rows on one cid** (clause 1 = rel 0 + rel 1, clause 3 = rel 2).
That lands in the **3-row tier**, which is a **compiled-switch CODE edit at
`0x02243C1C`** — not a data edit. Clause 2 is free (no rows).

Both single-clause orderings are cheap; only the COMBINATION is expensive:

| plan | registry cost | attested? |
|---|---|---|
| clause 3 alone | 1 row, rel 0 | yes — the 1141-cid default tier |
| clause 1 alone | 2 rows rel 0/1 + donor into **list A** (count-neutral; list A has 5 phantom entries `0x0E32` `0x0E6B` `0x0EA8` `0x1303` `0x234E`, list B has `0x234F`) | yes — literally the Chaos family |
| clauses 1 **and** 3 | 3-row block + a new case in the compiled switch | **no — 3-row blocks are all native, none ever added** |

**Escape hatch worth considering:** clause 3 does not *have* to use a criteria row.
Its target selection could live in an **ov5 cave stub** hung off the leave-hook
trampoline `0x021C8216` (the Quasar / Reborn Tengu route, and our donor is a
main-deck monster so a cls2 leave row is available to it too). That keeps the
registry block at 2 rows, so clause 1 stays pure data and no switch edit is needed.

### ✅ CLAUSE 1 FULLY MAPPED — and it needs NO code cave at all

The recon assumed clause 1's only code change was "the tree branch". Measured
this session, the picture is sharper and *cheaper*:

**1. The hand-SS dispatch is a cid-ordered BST rooted at `0x0225E622`.**
`0x0225E51C` is the entry (`r6 = side`, `r4 = cid` from the packed word's low 14
bits). Simulated over the whole cid space, the tree reproduces every known fact:
Chaos Sorcerer / BLS-Envoy / CED -> leaf `0x0225FA46`; Fenrir -> `0x0225FA36`.

**2. The donor must be *routed*, and the routing is FREE — four arms are DEAD.**
An arm is dead when every cid reaching it is a phantom (not a real card):

| BL site | leaf | reaching cids | status |
|---|---|---|---|
| `0x0225E67C` | `0x0225F33A` | `0x0E18`, `0x0EA5` | dead |
| `0x0225E692` | `0x0225F26E` | `0x0E3F` | dead |
| **`0x0225E6E6`** | `0x0225F7EC` | `0x0E1F`, `0x0ECA` | **dead — the one we use** |
| `0x0225E88E` | `0x0225F240` | `0x164C` | dead |

The chosen node:
```
0x0225E6E0  adds r0, #0x17     ; r0 = 0x0EB3 + 0x17 = 0x0ECA   <- imm8 is the compared cid
0x0225E6E2  cmp  r4, r0
0x0225E6E4  bne  0x0225E6EA
0x0225E6E6  bl   0x0225F7EC    ; DEAD
0x0225E6EA  bl   0x0225FF96    ; reject
```
Repointing it costs **3 bytes** and no cave: change the imm8 to select the donor,
and retarget the BL to `0x0225FA46`. **Because it is pure in-place ov3, clause 1
works in PUZZLES too** — unlike anything hosted in the ov5 cave.

**⚠️ CONSTRAINT this imposes:** `adds r0,#imm8` caps the compared cid at
`0x0EB3 + 0xFF = 0x0FB2`, so the donor must lie in **`0x0EB4..0x0FB2`**.
**The recon's chosen donor Armored Lizard `0x0FD9` is OUT OF RANGE.**

**3. Donor changed to Sword Arm of Dragon `0x0FB1`** (imm8 = `0xFE`). Swept the
whole repointable window against all six vetting filters — 8 cids pass, and
`0x0FB1` is the best: **already Level 6** (smallest retune of any candidate),
Normal Monster, no cls0/1/2/3 record, no criteria row, absent from the
summon-restriction region, neither fusion material nor result. (Summoned Skull
`0x0F0A` also passes but the user excluded it on 2026-08-05; the rest are
Blue-Eyes / Dark Magician alternate arts, Hitotsu-Me Giant, Mushroom Man.)

**4. `handss.banish_cost_count_default` = 0 — ANSWERED (was UNVERIFIED).**
`0x0225CF28(cid)` returns the required per-row banish count. Simulated across the
cid space: the unnamed-cid fall-through is leaf `0x0225D09C` = `movs r0,#0; bx lr`
-> **0**, shared by 6110 of 6144 cids. The simulation validates itself against the
card texts: **Fenrir `0x16C6` -> 2** ("banishing **2** WATER monsters"), the whole
Chaos family -> 1, Inferno/Gigantes/Silpheed -> 1, Dark Necrofear -> 3, Rainbow
Dark Dragon -> 7. **This also answers Darkflare for free.**

**Consequence: a count of 0 makes the cost check pass VACUOUSLY** — the leaf tests
`found >= required` twice, so with required = 0 the donor could Special Summon
itself from hand banishing nothing, even from an empty GY. Clause 1 therefore
needs a third code edit.

**5. The count edit and its blast radius.** Donor `0x0FB1` reaches
`0x0225CF5E: b 0x0225D09C` (return 0); retargeting that to `0x0225D06A`
(`movs r0,#1`) gives the donor its required 1. That branch is shared by every cid
`< 0x1466`, so the blast radius was measured rather than assumed:
- **Every cid with a legitimately nonzero count is `>= 0x1466`** (lowest is Dark
  Necrofear `0x1466`); and
- **no cid `< 0x1483` reaches a banish-cost leaf** (`0x0225FA36`/`0x0225FA46`) —
  from the whole-cid-space tree simulation; and
- all four other callers of `0x0225CF28` (`0x0225D0D8`, `0x0225F678`,
  `0x0226295A`, `0x02264814`) are summon-cost machinery that reads the cid out of
  the live summon record (`ldrh r0,[r4,#0xe]`), i.e. only runs for a card actually
  performing this summon.
So the only cid whose observable count changes is the donor. `verify()` re-checks
this invariant so a future patch that routes another low cid there trips the guard.

### Clause 1 — the complete change set (3 code bytes + 2 data inserts + card_prop)

| # | where | from | to | kind |
|---|---|---|---|---|
| 1 | `0x0225E6E0` | `adds r0,#0x17` | `adds r0,#0xFE` | ov3 code (1 byte) |
| 2 | `0x0225E6E6` | `bl 0x0225F7EC` | `bl 0x0225FA46` | ov3 code (2 bytes) |
| 3 | `0x0225CF5E` | `b 0x0225D09C` | `b 0x0225D06A` | ov3 code (2 bytes) |
| 4 | criteria registry `0x022713C4` | — | 2 rows on `0x0FB1`: `{aux 0xFFFF, fn 0x0223CA11, 0x01000002}` then `{…, 0x02000002}` at index 69 | data, count-neutral (drop both rows of phantom `0x0E79`) |
| 5 | membership list A `0x0227134C` | — | insert `0x0FB1` | data, count-neutral (drop phantom `0x0E6B`) |
| 6 | `card_prop` row `0x0FB1` | Dinosaur / EARTH / 1750 / 2030 | Dragon / LIGHT / 2500 / 1500 | data (Level already 6) |

Row aux/handler/word copied verbatim from the Chaos family (all six of their rows
are `aux=0xFFFF, fn=0x0223CA11`). Insert index 69 sits between `0x0ECA` and
`0x0FB6`, preserving the sort. Membership list A is what makes `param = 1` (the
DARK pass) reachable — **without step 5 only the LIGHT row would ever be read.**

## Ruled Out (this session)
- **"Clause 2 costs registry rows."** No — 4 of 7 sampled family members own zero
  rows; the cost is slot3/slot4 only.
- **"The GY-revive consumer always reads relative row 0."** No — 3 of 45 revive
  rows sit at relative index 1 (Chaos Goddess, Lava Dragon, The Dark Creator).
- **The ov3 BSS cave (`ov3_cave.py` WINDOW_PRIMARY/SECONDARY).** Unusable —
  `notes/ov3-cave-findings.md` canary round 2 proved the engine clears ov3's BSS
  over its ORIGINAL extent, wiping both windows in all five modes. Not a
  "shrink and retry" failure. The only puzzle-safe ov3 space is the 180 B
  dead-code pool, whose 84 B free is **fragmented** (largest contiguous block
  16 B) — too small for a router, which is why the dead-ARM repoint above
  (needing no space at all) is the right answer.
- **Hosting the routing stub in the ov5 cave.** Rejected on safety: the hand-SS
  dispatch is a SHARED path, and in a puzzle ov41 evicts ov5, so a BL from the
  tree into the cave would execute ov41 data and freeze.

## Open Questions
1. ~~What supplies `param` to the GY-revive consumer?~~ **ANSWERED above** —
   membership list B. The live question it becomes: **do we pay the compiled-switch
   edit to get a 3-row block, or route clause 3 through an ov5 stub instead?**
   (User decision — see Next Experiment.)
1b. Are `0x21BC` and `0x2449` evidence that the inherited 22-case switch
   enumeration is incomplete? Affects only the 3-row plan.
2. Recon Open Question 1 still stands: **`0x0A550002` (Dragon + an attribute) is
   unattested** — all 35 Dragon-race rows have attribute 0.
3. Recon Open Question 2 still stands: `0x0225CF28`'s fall-through
   (`handss.banish_cost_count_default`, UNVERIFIED). Answers Darkflare too.
4. Recon Open Questions 3, 4, 5 unchanged.

## Next Experiment
1. ~~Find the `param` source for the revive path.~~ **DONE — answered above.**
2. **(offline) Pick the phantom rows to drop** for count-neutrality, respecting
   sort order (a dropped phantom must sit in an interval that keeps the array
   sorted around `0x0FD9`).
3. Then the recon's experiments 1 and 3 (both GDB, foldable into ONE stub session).

## BUILT — clause 1 (2026-08-13)

`otn_enhanced/cards/lightpulsar.py`, registered in
`apply_all_patches.PATCHES` after Eclipse Wyvern. Single-card ROM:
`data/over_the_nexus/working/rom_lightpulsar.nds`. **`verify()` = 18/18 PASS.**

card_prop retune confirmed by the builder's own before/after dump:
```
BEFORE: lvl=6 attr=EARTH race=Dinosaur atk=1750 def=2030 type=Normal Monster
AFTER : lvl=6 attr=LIGHT race=Dragon    atk=2500 def=1500 type=Effect Monster
```

### Structural end-to-end proof (offline, against the PATCHED overlay)

Re-ran both simulators on the patched image and diffed against the clean one:

1. donor `0x0FB1`: dispatch leaf `0x0225FF96` (reject) -> **`0x0225FA46`** (LIGHT+DARK cost) ✅
2. `0x0225CF28(0x0FB1)`: **0 -> 1** ✅
3. cids whose dispatch leaf changed: **2, both phantoms** — `0x0E1F`
   (`0x0225F7EC` -> `0x0225FA46`) and `0x0ECA` (`0x0225F7EC` -> reject). Neither has
   a card_prop record, so neither can be in a deck, hand, field or GY.
   **Zero real cards changed leaf.**
4. cids whose *count* changed: 1894 (every cid `< 0x1466`), of which the ones that
   can ever OBSERVE it — i.e. that reach a banish-cost leaf — are exactly
   `0x0E1F` (phantom) and `0x0FB1` (the donor). **Zero real cards affected.**

⚠️ `0x0E1F` reaching the LIGHT+DARK leaf was NOT predicted by the dead-arm
analysis alone (it enters the node through a different branch than `0x0ECA`). It
is harmless — a phantom cannot be held — but it is why the post-patch differential
was worth running, and the same check should be re-run for Darkflare's arm.

### Slots claimed (registered in `check_allocations.PHANTOM_CLAIMS`, ledger refreshed)

| pool | cid / addr | note |
|---|---|---|
| `populate_table` | `0x0E79` | phantom, **both** rows dropped |
| `populate_table` | `0x0FB1` | the donor's LIGHT+DARK row pair |
| `membership_list_a` | `0x0E6B` | phantom dropped |
| `membership_list_a` | `0x0FB1` | the donor |
| `handss_dead_arm` | `0x0225E6E6` | 3 dead arms remain free |
| `handss_count_branch` | `0x0225CF5E` | |

**No ov5 cave slot, no ov3 dead-code slot** — `CAVE_FREE` is untouched at
`0x0239C1A8` and the ov3 pool still has its 84 B.

### KB contributions

`verify_knowledge` 219 -> **221 facts, 191 PASS, 0 FAIL, 30 UNVERIFIED**.

| id | grade | note |
|---|---|---|
| `handss.banish_cost_count_default` | UNVERIFIED -> **VERIFIED** | fall-through = 0; answers Darkflare too |
| `handss.dispatch_dead_arms` | **VERIFIED** (new) | the 4 dead arms + the 3-byte repoint recipe |
| `dispatch.criteria_block_size_tiers` | **VERIFIED** (new) | the 1 / 2 / 3-4 row addressing tiers |

## ⛔ IN-GAME TEST 1 — FAILED (2026-08-13, user-reported)

**Observed: the card Special Summoned itself from the hand WITHOUT banishing a
LIGHT and a DARK monster from the GY.**

So clause 1 is NOT working. The condition/legality half may or may not be right,
but the COST IS NOT BEING PAID. What this rules in and out is under Ruled Out /
Open Questions below; the leading hypothesis is that **the cost PAYMENT is a
separate per-cid-dispatched routine that my change set never touched** —
`0x0226295A` calls `0x0225CF28` for the count and then immediately switches on the
cid (`ldrh r0,[r4,#0xe]` / `cmp r0,=0x1C81` / `bgt` / `blt`), which for an unnamed
donor cid would take a default arm that banishes nothing.

⚠️ This also means my "3 code bytes + 2 data inserts" change set was INCOMPLETE,
not wrong: routing + legality + count are necessary but not sufficient. Do not
re-derive the parts above — they verify and the differential proved them
side-effect-free — but treat "clause 1 is data-only" as **DISPROVEN**.

### ✅ ROOT CAUSE OF THE FAILED TEST — a SECOND per-cid dispatch: the cost PAYMENT

The summon pipeline has (at least) two independent per-cid dispatches, and I only
patched the first. Legality and payment are separate:

  * **legality** — the hand-SS BST -> leaf `0x0225FA46`, which only computes a
    yes/no in r7. PATCHED, works.
  * **payment** — a different BST, rooted at the cid compare `0x02262962` (reached
    from the `0x0225CF28` caller at `0x0226295A`), which selects **`r5` = how many
    cards the player must pick and banish**. NOT patched. Our donor lands on the
    DEFAULT arm, which sets up no selection at all — hence a free summon.

Enumerated the whole payment dispatch by cid:

| arm | meaning | n | cids |
|---|---|---|---|
| `0x02262A52` | computed r5 via `0x0202ABB8` | 6 | `0x1466` `0x18B4` `0x19CA` `0x1D86` `0x1D91` `0x234F` |
| **`0x02262A5A`** | **`movs r5,#2` — the LIGHT+DARK two-card select** | **5** | `0x16C9` `0x16CB` `0x16E4` `0x1BC8` `0x1BC9` |
| `0x02262A66` | r5 = 4/3 | 1 | `0x1C2A` |
| `0x02262A72` | r5 = 5/6 | 1 | `0x1C2B` |
| `0x02262A82` | r5 unset, posts 0x56 | 7 | `0x1BB5` `0x1C81` `0x1DB4` `0x1DBD` `0x1E31` `0x204C` `0x2113` |
| `0x02262AAE` | **DEFAULT — no selection** | **6378** | ...including our donor `0x0FB1` |

**All 5 cids on the 2-card arm are REAL CARDS**, and the dispatch's ONLY dead
decision site (`0x02262A46` -> `0x02262A52`, phantom `0x234F`) leads to the *wrong*
arm — and sits at cid ~`0x234F`, unreachable from a donor at `0x0FB1` anyway.

**So the dead-arm trick does NOT generalise across the pipeline.** Each per-cid
dispatch needs its own dead arm within `base + imm8` of the SAME donor cid, and
those windows do not intersect.

### ⛔ "Clause 1 is data-only with a Normal-Monster donor" — DISPROVEN
It needs the donor injected into every per-cid dispatch in the summon pipeline. The
payment dispatch has no usable dead arm, so that means real stub code on a SHARED
summon path — where ov5 is unsafe (ov41 evicts it in puzzles) and the ov3 dead-code
pool has only 84 B, fragmented, largest contiguous block **16 B**. Not feasible as
things stand.

### The five cards already wired end-to-end for this exact cost

| cid | name | stats | cls records to strip | criteria words |
|---|---|---|---|---|
| **`0x16C9`** | **Chaos Sorcerer** | **Lv6** DARK/Spellcaster 2300/2000 | **`cls3[152]`only** | **`0x01000002` / `0x02000002` — already EXACTLY Lightpulsar's cost** |
| `0x16CB` | BLS - Envoy of the Beginning | Lv8 LIGHT/Warrior 3000/2500 | `cls1[335]` + `cls3[153]` | same |
| `0x16E4` | Chaos Emperor Dragon | Lv8 DARK/Dragon 3000/2500 | `cls3[154]` | same |
| `0x1BC8` | Sky Scourge Enrise | Lv8 LIGHT/Fairy 2400/1500 | `cls3[294]` | `0x89000002`/`0x1A000002` (race-constrained, would need rewriting) |
| `0x1BC9` | Sky Scourge Norleras | Lv8 DARK/Fiend 2400/1500 | `cls3[295]` | same |

**Chaos Sorcerer `0x16C9` is the standout**: already Level 6 (Lightpulsar's level),
its two criteria words are ALREADY plain LIGHT + plain DARK, it is in membership
list A, its count is already 1, it routes natively to `0x0225FA46` and to the
2-card payment arm — and it carries only ONE extra cls record. Clause 1 with that
donor is **card_prop + text + strip one cls3 record**, and ZERO of the pipeline
edits.

⚠️ KNOWN COST of any of the five: they are **Nomi** ("Cannot be Normal
Summoned/Set. Must first be Special Summoned..."), while Lightpulsar is NOT — it
can be Normal Summoned by tributing 1. Per `donor.vetting_beyond_cls_records` the
Nomi wiring lives in the same `0x0225E51C..0x02260400` region, so removing it is
bounded but unproven work. And it consumes a real card, against this project's
Normal-Monster-donor preference.

### ✅ NEW CAVE SPACE — 126 B of contiguous, puzzle-safe, provably-dead OV3 code

User decision 2026-08-13: **keep the Normal-Monster donor**, which means stub code
on the shared summon path, which means always-resident (ov3) space. The ov3
dead-code pool was too fragmented (84 B free, 16 B largest run). Found a much
better block **inside the hand-SS region itself**:

| range | size | what it was |
|---|---|---|
| `0x0225F240..0x0225F26C` | 46 B | leaf reached ONLY from dead arm `0x0225E88E` (phantom `0x164C`) |
| `0x0225F26E..0x0225F2BC` | 80 B | leaf reached ONLY from dead arm `0x0225E692` (phantom `0x0E3F`) |
| **`0x0225F240..0x0225F2BE`** | **126 B contiguous** | |

Proved dead by three independent scans over the ARM9 **and all 50 overlays**:
1. **BL/BLX into the range: exactly 2** — `0x0225E692` -> `0x0225F26E` and
   `0x0225E88E` -> `0x0225F240`, i.e. *only the two dead arms*, whose sole reaching
   cids are phantoms. Neutralise those two arms (point them at the reject leaf
   `0x0225FF96`) and the range becomes unreachable.
2. **Inbound B/Bcond from outside the range: 0.**
3. **Pointer words (raw or Thumb-bit) anywhere in arm9 + 50 overlays: 0.**

⚠️ The literal pool at `0x0225F510+` (`0x0B3C`, `0x0229ACA0`, `0x132C`, `0x1DF4`,
`0x0229AC94`) is SHARED with live code — the dead range's own code loaded from it.
**Do not touch the pool**; stubs must carry their own literals inside the 126 B.

⚠️ This is a code range, not BSS — it is part of ov3's file image, so unlike the
`ov3_cave.py` BSS windows it is NOT wiped by the engine's BSS clear. That is why
this works where the BSS cave failed.

### ✅ THE COST-PAYMENT PIPELINE — mapped, and it is only TWO more dispatches

Bounded the problem instead of guessing: scanned ov3 for every literal word holding
a banish-cost family cid (`0x16C5`-`0x16E4`, `0x1BC8`, `0x1BC9`) and then every
PC-relative load of those literals — 28 sites, of which only **three** lie in the
summon/payment region and only **four** in the hand-SS region:

| site | what it is | donor status |
|---|---|---|
| `0x0225CF32` / `0x0225CF7E` | the required-count tree | PART B ✅ |
| `0x0225E7A4` | the hand-SS BST family cluster | PART A ✅ (bypassed via a dead arm) |
| `0x0225EAA6` | the Sky Scourge cluster (separate leaf) | not ours |
| **`0x02262974`** | **payment dispatch 1 — how many cards to select** | PART E/F ✅ |
| **`0x02262C26`** | **payment dispatch 2 — the two-pass driver** | PART E/F ✅ |
| `0x02262C2E` | same dispatch, second literal | same stub |

The other two `0x0225CF28` callers turned out to be **cid-generic**, so they needed
nothing: `0x0225F678` is a single-pass count check, and `0x02264814` is the
"how many must you banish" PROMPT, driven by a state machine on `[rec+0x24]` — it
just consumes whatever `0x0225CF28` returns, which PART B already fixed.

**Dispatch 2 is the important discovery.** Its family arm `0x02262C8C` does
`[rec+0x28] += 1` and, if the OLD index was 0, sets `[rec+0x24] = 4` — *go round
again*. That is the ONLY thing that makes the DARK pass happen. `[rec+0x28]` is the
same pass index the legality leaf mirrors into the criteria-row `param`, and
`rec == 0x02298A28`, which ties the whole scheme together.

**⚠️ TRAP AVOIDED:** the obvious hook for dispatch 2 is its shared completion arm
`0x02262CA4` — but `0x02262C8C`'s own "both passes done" path branches THERE, so a
cid test at `0x02262CA4` sends the donor back to `0x02262C8C` **forever**. Both
hooks must sit at the dispatch ROOTS. An earlier draft had exactly that bug.

Register discipline: the stubs clobber **only r2**, which is a scratch compare
register in both dispatches (never an argument) — except on dispatch 2's `bgt`
path, where `0x02262C5E` does `adds r1,r2,#0` and needs `r2 == 0x1BC8`. Stub 2
therefore replays the displaced `ldr`/`cmp` and returns via `push {r2}` / `pop {pc}`,
preserving both the flags and r2. (`pop {pc}` is intended here — cf.
`thumb.pop_into_lr`: Thumb-1 POP can load PC but never LR.)

**Why no differential was needed this round:** unlike PART A (a shared *tree node*,
whose reachability had to be computed — and where the differential caught phantom
`0x0E1F`), both stubs are total functions of the cid whose default path replays the
original instructions verbatim. Only `0x0FB1` can change behaviour, by construction.
`verify()` additionally pins the first instructions of all three jump targets.

### Change set, final — 5 in-place edits + 2 stubs + 2 data inserts

| # | where | change |
|---|---|---|
| A | `0x0225E6E0` / `0x0225E6E6` | dead arm -> donor cid, BL -> legality leaf `0x0225FA46` |
| B | `0x0225CF5E` | required count 0 -> 1 |
| C1 | criteria registry | 2 rows on `0x0FB1` (LIGHT then DARK), phantom `0x0E79` dropped |
| C2 | membership list A | `0x0FB1` in, phantom `0x0E6B` out |
| D | `0x0225E692` / `0x0225E88E` | the two dead arms -> reject leaf (makes the cave unreachable) |
| E | `0x0225F240` | pay-1 stub 44 B + pay-2 stub 36 B (80/126 B) |
| F | `0x0226298C` / `0x02262C26` | 4-byte BLs hooking both payment dispatch roots |
| — | `card_prop` `0x0FB1` | Dragon / LIGHT / 2500 / 1500 (Level already 6) |

`verify()` = **29/29 PASS**. Still ov3-only, so still puzzle-capable.
Ledger: 11 ov3 dead blocks, 6 claims, 130 B free. No ov5 slot used.

### Chain rebuild (2026-08-13, after the payment fix)

`ALL 32 PATCHES APPLIED -> data/over_the_nexus/working/rom_all_patches.nds`,
Lightpulsar at step **[26/32]**; allocation guard OK before the first write.
`patch_lightpulsar.verify()` against the **combined** ROM = **29/29 PASS**.

Chain-wide regression sweep (`verify()` for every patch module against the combined
ROM): **22 PASS, 12 modules expose no verify(), 4 not-PASS — none of them in the
applied chain**, so none is a regression from this work:

| module | result | why it is not a regression |
|---|---|---|
| `patch_wonder_wand` | `AssertionError: grant row is +800/+0` | its PatchStep is **commented out**; not applied |
| `patch_bulk_ydcs` | IMPORT-FAIL `ValueError` (a 15-card deck) | no PatchStep at all; pre-existing data issue |
| `patch_unlock_all_packs` | `TypeError: verify() takes 0 args` | no PatchStep; harness passed an arg its verify doesn't take |
| `patch_zeta_reticulant` | `SystemExit: 1` | no PatchStep; not applied |

Every applied module that exposes `verify()` passes, including all 25 shipped
effect cards.

## ⛔ IN-GAME TEST 2 — FAILED, but the failure MOVED (2026-08-13)

Observed: the Special Summon option now appears **only when a LIGHT and a DARK are
in the GY** — so PARTS A/B/C (routing + criteria rows + membership + count) ARE
WORKING. But the summon still paid nothing: no prompts, nothing banished.

### ✅ Savestate evidence (`rom_all_patches.ml2` before / `.ml3` after)

1. **The patched ov3 IS resident** — the pay stubs at `0x0225F240`, both hooks, the
   routing compare/BL and the count branch are all **byte-identical to the built
   image** in both states. So the code was there; it simply never ran.
2. **The summon record `0x02298A28` after the summon:** `+0x0E (cid) = 0x0FB1` —
   our donor's summon really was in flight — but **`+0x28` (pass index) = 0** and
   `+0x24` = `0x17`. The payment state machine `0x0226292C` only handles states
   0..4, so **it never executed**.

### ✅ ROOT CAUSE — the SUMMON-PROCEDURE REGISTRY, a table I had not found

The hand-SS tree does NOT select a cost. Its success leaf `0x0225F216` is literally
`movs r0,#4 ; orrs r5,r0` — it just sets **bit 2 of a bitmask** meaning "this card
can be Special Summoned from the hand". (Both of the dead leaves I reused ended by
branching there, which is consistent.) That bitmask is why the option correctly
appeared once the GY had a LIGHT and a DARK.

**Which cost to pay is a separate per-cid lookup:**

```
0x02264DAE  ldr  r1, =0x0228F158   ; {u32 cid, u32 handler}, stride 8, STRICTLY sorted
0x02264DB0  movs r2, #0x85         ; 133 rows -- hard-coded imm8...
0x02264DB2  movs r3, #8            ; ...and duplicated at 0x022651C2
0x02264DB4  bl   0x02022E44        ; generic binary search on the cid
0x02264DB8  cmp  r0, #0
0x02264DBA  beq  0x02264DC2        ; NOT FOUND -> generic summon, NO COST
0x02264DBC  ldr  r0, [r0, #4]
0x02264DBE  blx  r0                ; else CALL the procedure handler
```

Table base **`0x0228F158`**, 133 rows, ending `0x0228F580`. The whole banish-cost
family maps to handler **`0x0226292D`** — exactly the payment state machine PARTS
E/F patch. **Our donor had no row**, so the search missed, the engine took the
not-found branch, and the card summoned for nothing. PARTS E/F were correct but
UNREACHABLE. `0x02261F8D` is the registry's "no special procedure" handler (the
second searcher at `0x022651D4` tests for it explicitly); all 16 phantom rows use it.

⚠️ Note the region holds **two** sorted `{cid, handler}` tables back to back —
`0x0228EFE8..0x0228F158` (44 rows) and ours `0x0228F158..0x0228F580` (133). There is
exactly one descent between them, at `0x0228F158`. Do not treat them as one array.

### PART G — the fix

Count-neutral insert of `{0x0FB1 -> 0x0226292D}` at index 11, dropping phantom row
`0x0ECA` (index 10, handler `0x02261F8D`) — pleasingly the same phantom whose dead
arm PART A repurposed. Both searchers' `movs r2,#0x85` immediates are asserted
unchanged. `verify()` = **36/36 PASS**.

### Lesson for the next card (and for Darkflare)

**"The card can be summoned" and "the summon costs something" are two different
tables.** A donor needs BOTH: the hand-SS bitmask route (PART A) *and* a row in the
summon-procedure registry `0x0228F158` (PART G). Getting only the first produces a
card that summons itself for free while LOOKING correctly gated — which is exactly
what both failed in-game tests showed, and what no static `verify()` caught.

## ✅ IN-GAME TEST 3 — PASSED. CLAUSE 1 IS DONE (2026-08-13)

User-reported on `rom_lightpulsar.nds`: **the card summons correctly, offers a LIGHT
then a DARK to be banished, and banishes them.** That is the full clause-1 loop —
legality gate, both selection passes, and the actual cost — working on the live path.

This also retroactively validates PARTS E/F, which had never executed before PART G
made them reachable: the two-pass driver, the `pop {pc}` resume path and the r2
discipline are all correct in practice, not just on paper.

**What it took, in the order the three in-game tests forced it out:**

| test | symptom | what was missing |
|---|---|---|
| 1 | summons for free, no gate | the whole payment side (PARTS D/E/F) |
| 2 | correctly gated on GY contents, still free | the SUMMON-PROCEDURE REGISTRY row (PART G) — without it the payment machine is never even called |
| 3 | **correct** | — |

The through-line: **static `verify()` proves the code I wrote is correct, never that
the engine reaches it.** Both failures were reachability, and only the emulator could
see them. CLAUDE.md's "ground truth is the emulator, not the compiler" earned its
place twice in one card.

## Next Experiment
1. **IN-GAME TEST 2 of clause 1** — the arbiter. Test 1 failed (free summon) and led
   to the payment-dispatch discovery; this round adds PARTS D/E/F. The specific
   regression to re-check is **the empty/partial-GY refusal**, plus that BOTH prompts
   appear and BOTH picks end up banished. Also worth a puzzle, since this patch is
   ov3-only and should work there.
2. Then clause 2 or clause 3. **Read `dispatch.criteria_block_size_tiers` first**:
   clause 3 needs a 3rd row on this cid, which is a compiled-switch edit at
   `0x02243C1C`, OR route clause 3's targeting via an ov5 stub off the leave-hook
   trampoline `0x021C8216` and keep the block at 2 rows.
3. Darkflare Dragon is now cheap: take one of the 3 remaining dead arms
   (`0x0225E67C`, `0x0225E692`, `0x0225E88E`), mind each one's own
   `base + imm8` donor window, and re-run the post-patch differential.


---

# Clauses 2 and 3 — mapped 2026-08-13 (scope: user asked to build both)

**Clause 1 must not regress.** It is in-game confirmed; its rows sit at criteria
relative index 0 (LIGHT) and 1 (DARK) and its leaf passes param 0/1 as BARE
IMMEDIATES, so anything added must not renumber those two.

## New tool: the per-cid structure profiler

`scratchpad/cid_profile.py` (worth promoting into `ygo_tools/`) answers **"which
per-cid structures does this cid appear in?"** over 18 named tables plus a raw ov3
data sweep. Built because clause 1 needed SEVEN insertions and each missing one was
found only by a failed duel. **Profile a working card first, then give the donor the
same set** — do not discover them one in-game test at a time.

## ✅ Clause 2 is SMALL — one cls2 record, nothing else

Profiled the whole self-SS-from-GY family:

| card | structures it appears in |
|---|---|
| **Treeborn Frog `0x19CB`** | **cls2[199] and NOTHING ELSE** |
| Quillbolt Hedgehog `0x1E15` | cls2[359] only |
| Plaguespreader `0x1EA9` | cls2[385] + a criteria row (for its *other* effect) |
| Spore `0x225B` | cls2[561] + criteria row + param-provider list (its level-up effect) |

Treeborn Frog is the proof: a pure "Special Summon this card from your GY by
\<cost\>" card needs **only a cls2 record**. Record shape:

```
+04 = 0x0220731D   the shared self-SS-from-GY resolver (handss.self_ss_from_gy_resolver)
+0C = <condition>  Treeborn 0x021FA585 / Plaguespreader 0x021FF06D / Spore 0x021F0BDD
+10 = <cost>       Treeborn 0x021E7969 / Plaguespreader 0x021E9039 / Spore 0x021E5319
```

**Crucially it needs NO summon-procedure-registry row** — that gate (which cost
clause 1 two failed tests) applies to the hand-SS path, not this one. Confirmed:
Treeborn/Quillbolt/Plaguespreader are absent from `0x0228F158`.

**Remaining work for clause 2:** a slot3 condition ("is there 1 LIGHT + 1 DARK in
hand?") and a slot4 cost ("send them to the GY"). Neither exists natively in the
right shape, so both are new Thumb-1 stubs — hostable in the ~46 B still free in the
126 B ov3 dead run, if they fit; otherwise the ov5 cave is acceptable here **only if**
clause 2 is allowed to be normal-duel-only. **Next step: disassemble the three known
slot3/slot4 pairs above to learn the ABI before writing anything.**

## ⚠️ Clause 3 has ONE specific unsolved blocker

Template (`Decoy Dragon 0x1C4F`, the cleanest — "target 1 Lv7+ Dragon in your GY;
Special Summon it"):

| structure | value |
|---|---|
| cls1[676] | +04 = `0x02225CB1` resolver, +14 = `0x02235605` off-field picker |
| criteria registry[571] | handler `0x0223C9D1`, word `0x085D0002` |

That is all Decoy Dragon needs — because it owns exactly ONE criteria row, so the
default leaf's forced param 0 lands on it.

**Our donor already owns two rows (clause 1's), so clause 3's revive row lands at
relative index 2, and the revive path must ASK for param 2.** Record-driven paths do
not pass param as an immediate; they get it from the per-cid provider **`0x02234E78`**
— itself a large BST over cid whose leaves return descriptor fields (`[desc+0x0C]`,
`[desc+0x14]`) or flag words (`0x10000000`), with membership lists at `0x022710E2`
(17), `0x02271104` (28), `0x022710B2` (12). An unlisted cid takes the default, which
we have NOT yet read.

Chaos Goddess `0x2273` is the existence proof that this is solvable — it owns 2 rows,
its revive row is at index 1, and it is in **membership list B** *and* **param
provider list 2**. So the mechanism is: add the donor to the right provider structure
so the revive path requests the right index.

**⚠️ Clause 1 is NOT at risk from this**: its leaf `0x0225FA46` passes param 0/1 as
bare immediates and never consults `0x02234E78`, so changing the provider's answer for
our cid cannot renumber clause 1's rows.

**✅ BLOCKER RESOLVED (2026-08-13):** `0x02234E78` returns **0** for our donor —
traced to the fall-through leaf `0x022355F0` (`movs r0,#0 ; pop`), and `0x0FB1` is in
**none** of the three provider lists (`0x022710E2` 17, `0x02271104` 28, `0x022710B2`
12). So the revive path would ask for row 0 and get clause 1's LIGHT row. Confirmed,
not assumed.

**The fix: hook `0x02234E78` with a cid test returning 2 for the donor** — the same
pattern as the payment stubs, ~24 B in the 46 B still free in the ov3 dead run.
Reordering the rows instead does NOT work: clause 1 needs LIGHT at row 0 and clause 3
would also want row 0, a direct conflict. **Safe for clause 1** because its leaf
passes param as bare immediates and never consults the provider; and safe generally
because the donor's only record-driven criteria consumer is clause 3 itself.

**Remaining clause-3 steps:**
3. Only then choose the trigger: a cls2 leave-trigger row (Reborn Tengu blueprint,
   `otn-leave-trigger-cls2`) with slot5 = `0x02235605`, resolver `0x02207529`
   (`dispatch.criteria_gy_revive_handler`).
4. Criteria word is already derived: **`0x0A550002`** = Chaos Goddess's `0x02550002`
   with the Dragon race nibble filled in. ⚠️ STILL UNATTESTED — no row in the ROM
   combines Dragon race with an attribute (all 35 Dragon rows have attribute 0), so
   verify it enumerates correctly before trusting it.

## Slots clauses 2/3 will need (NOT claimed yet)
- cls2 record for clause 2 (+ a phantom to drop, count-neutral).
- cls2 record for clause 3's leave trigger (+ a phantom).
- 1 criteria row on `0x0FB1` at relative index 2 (+ a phantom).
- possibly a param-provider list entry for `0x0FB1`.
- ov3 dead run `0x0225F240`: 46 B free after clause 1's 80 B.


## Clause 2 — RE done 2026-08-13, one design decision outstanding

**The near-exact native template is Fabled Soulkius `0x202C`**: "If this card is in
your GY: You can send 2 cards from your hand to the GY; Special Summon this card."
Same shape as clause 2; only the FILTER differs (Soulkius: any 2 cards).

Its cls2 record: `+04 = 0x0220731D` (shared resolver), `+0C = 0x022002B1` (condition),
`+10 = 0x021E7245` (cost).

**COST `0x021E7245` decoded** — entry `0x021E7244`:
```
r4 = desc ; r2 = [r4] = cid
r7 = 1 ; if cid == 0x202C then r7 = 2      <-- r7 IS THE NUMBER OF CARDS TO SEND
r5 = 0x0229AAFC ; r0 = [r5+0x7C]           <-- a 4-step state machine (jump table)
```
So the count is a per-cid test defaulting to **1**, and only Soulkius gets 2. It sends
**any** cards from the hand — there is no attribute filter in it.

**CONDITION `0x022002B1`**: `0x0224401C(desc) >= 2` AND `0x021F04FC(...)` (in-GY test).
`0x0224401C` reads `[desc]`=cid, `[desc+2]`=side, `[desc+6]`, and tail-calls
`0x02244030`, which indexes the per-side player struct (`0x0229AC94 + side*0x0B3C`)
— i.e. a zone-count helper that receives the cid (r7), so it is plausibly
criteria-row-filtered, but that was NOT run down.

### The decision

**(a) FAITHFUL — "1 LIGHT and 1 DARK monster from the hand".** Needs a filtered
two-pass selection over the HAND: two more criteria rows on `0x0FB1` (hand-zone LIGHT
/ hand-zone DARK) at relative indices 2 and 3, which runs into **the same param
blocker as clause 3** — record-driven paths take param from `0x02234E78`, which
returns 0 for our cid. So it needs the provider hook (shared with clause 3) plus new
condition/cost stubs. Bigger, correct, and shares work with clause 3.

**(b) DEVIATION — "send any 2 cards from your hand to the GY".** Reuse `0x021E7245`
verbatim and make its `r7 = 2` test match our cid as well as Soulkius (a one-cid-test
hook, ~20 B in the 46 B still free in the ov3 dead run), plus a cls2 record cloning
Soulkius's. Small, native machinery, no criteria rows, no param blocker. Deviation is
LOOSER than the printed card (any 2 cards rather than specifically 1 LIGHT + 1 DARK
monster), i.e. easier for the player — precedent exists (Eclipse Wyvern shipped two
documented deviations).

⚠️ Either way the record is one count-neutral cls2 insert (a phantom must be dropped),
and `handss.self_ss_from_gy_resolver`'s mode defaults to 0 for an unnamed cid, which
is the Treeborn/Soulkius path — no resolver edit needed.

⚠️ Clause 2 needs NO summon-procedure-registry row (Treeborn/Quillbolt/Plaguespreader
are all absent from `0x0228F158`) — clause 1's expensive gate does not apply here.


### Clause 2 progress 2026-08-13 — user chose the FAITHFUL cost (1 LIGHT + 1 DARK)

Needs hand-zone criteria rows on `0x0FB1` at relative indices 2 and 3, plus the
`0x02234E78` param-provider hook (shared with clause 3), plus a cls2 record cloning
Fabled Soulkius's shape.

**❌ RULED OUT — "low half `0x0802` = the HAND zone".** Tempting and WRONG. Armed
Dragon LV5 `0x17DA` ("send 1 monster from your hand to the GY") does carry
`0x00000802`, and `0x0802` is the 2nd-commonest low half (148 rows) — but only **71
of those 148** have "from your hand" anywhere in their text, and the counter-examples
are decisive: Time Wizard `0x0FB6`, Cyber-Stein `0x114A`, Magical Labyrinth `0x1232`,
Chimera `0x1294`, Dark Magic Curtain `0x12DE`, Giant Germ `0x1339`. **The low half is
NOT a zone field**; it encodes some criteria/selection TYPE not yet decoded. Do not
synthesise it.

Observed low-half frequencies (for whoever decodes it): `0x0002` x833, `0x0802` x148,
`0x000E` x142, `0x0000` x54, `0x0004` x38, `0x0022` x35, `0x8002` x27, `0x2002` x21,
`0x0204` x19, `0x0822` x16.

**NEXT EXPERIMENT (clause 2), in order:**
1. **Decode the low half properly.** The honest route is the one that worked for the
   level field (`dispatch.criteria_word_level_field`): cross-check EVERY row's low
   half against its ygoprodeck text and find the split that agrees on all of them.
   Until then clause 2's rows cannot be written.
2. Then the `0x02234E78` provider hook so the record-driven path asks for rows 2/3
   (its default for `0x0FB1` is 0 — already confirmed).
3. Then the cls2 record: `+04 = 0x0220731D`, `+0C`/`+10` cloned from Soulkius
   (`0x022002B1` / `0x021E7245`) or bespoke; count-neutral, drop a phantom.
4. ⚠️ `0x021E7245` hardcodes the send-count in `r7` (1 by default, 2 only for
   Soulkius `0x202C`) — a faithful clause 2 needs 2, so that test needs our cid too.

**Nothing was written to the ROM for clause 2.** No slot claimed, no ledger entry.
Clause 1 remains shipped, in-game confirmed, and unaffected.


### ✅ CLAUSE 2 ENCODING UNBLOCKED — copy Fabled Soulkius's row, don't decode the field

The low half never needed decoding. `dispatch.criteria_word_level_field` says to
**copy the low bits from a same-zone donor row**, and Soulkius IS that row — it is
consumed by the very cost function clause 2 reuses:

| card | criteria row | meaning |
|---|---|---|
| **Fabled Soulkius `0x202C`** | row 910, handler **`0x0223CB65`**, word **`0x0000002E`** | "any card in your HAND" (its text: send 2 cards from your hand) |

Top byte is `race<<3 \| attribute` (VERIFIED, `dispatch.criteria_word_race_attribute`),
and Soulkius's is 0 = no filter, matching "any card". So clause 2's rows are Soulkius's
word with the attribute nibble filled in — the SAME construction that produced
clause 1's working rows (Chaos word + attribute) :

| row | word | handler |
|---|---|---|
| LIGHT monster in hand | **`0x0100002E`** | `0x0223CB65` |
| DARK monster in hand | **`0x0200002E`** | `0x0223CB65` |

⚠️ Note the handler is `0x0223CB65` (Soulkius / hand-select), **not** clause 1's
`0x0223CA11` (banish-from-GY select). Do not reuse clause 1's handler.

This supersedes the "decode the low half" next-experiment — that is no longer on the
critical path for clause 2. (It would still be a good KB contribution on its own.)

### Clause 2 — the remaining build, fully specified

1. **Criteria rows** — 2 new rows on `0x0FB1` at relative indices **2 and 3**
   (LIGHT `0x0100002E` then DARK `0x0200002E`, handler `0x0223CB65`, aux `0xFFFF`),
   count-neutral: drop 2 phantom rows. ⚠️ MUST go AFTER clause 1's rows 0/1 — clause 1's
   leaf passes param 0/1 as bare immediates and renumbering them breaks a shipped,
   in-game-confirmed clause.
2. **Param-provider hook** at `0x02234E78` so the record-driven path asks for rows 2/3
   (its default for `0x0FB1` is **0** — confirmed by tracing to leaf `0x022355F0`).
   ~24 B; 46 B remain free in the ov3 dead run `0x0225F240`. Shared with clause 3.
3. **cls2 record** for `0x0FB1`: `+04 = 0x0220731D`, `+0C = 0x022002B1`,
   `+10 = 0x021E7245` (cloned from Soulkius cls2[449]); count-neutral, drop a phantom.
4. **Send-count**: `0x021E7245` sets `r7 = 1` by default and `2` only for cid `0x202C`
   — clause 2 needs 2, so that test must match `0x0FB1` too (a small hook, or fold it
   into the same stub as step 2).
5. Build, `verify()` the whole chain, then IN-GAME test — and per this card's history,
   assume nothing works until the duel says so.


## ✅✅ CLAUSE 2 — THE TEMPLATE IS DARK SIMORGH `0x1E5A` (user's lead, 2026-08-13)

Two corrections to my own earlier work, both from this one card:

**1. THE ZONE IS THE HANDLER, NOT THE WORD** (now VERIFIED as
`dispatch.criteria_zone_is_the_handler`). Dark Simorgh pays the same two attributes
from EITHER zone and owns four rows whose words are pairwise identical:

```
row 741  fn 0x0223CA11  word 0x02000002   DARK, from the GRAVEYARD
row 742  fn 0x0223CA11  word 0x06000002   WIND, from the GRAVEYARD
row 743  fn 0x0223CB19  word 0x02000002   DARK, from the HAND
row 744  fn 0x0223CB19  word 0x06000002   WIND, from the HAND
```

One cid, one text, everything controlled for. **`0x0223CA11` = select from GY;
`0x0223CB19` = select from HAND.** My "low half 0x0802 = hand" theory was wrong and
is filed under Ruled Out; the low half is an undecoded selection-TYPE code and never
needed decoding.

**So clause 2's rows are clause 1's words UNCHANGED with the handler swapped:**

| row | rel index | handler | word |
|---|---|---|---|
| LIGHT monster in hand | 2 | `0x0223CB19` | `0x01000002` |
| DARK monster in hand | 3 | `0x0223CB19` | `0x02000002` |

**2. DARK SIMORGH IS A STRUCTURAL TWIN OF THE WHOLE CARD.** It owns TWO cls2 records,
one per summon direction, and a FOUR-row criteria block laid out exactly as Lightpulsar
needs — GY-pair at rel 0/1, HAND-pair at rel 2/3:

| record | +04 resolver | +0C condition | +10 cost | direction |
|---|---|---|---|---|
| cls2[374] | `0x02206ABD` | `0x021FEBA9` | `0x021EB7AD` | SS from HAND, paying from GY |
| **cls2[375]** | **`0x0220731D`** | `0x021FEBA9` | **`0x021EC57D`** | **SS from GY, paying from HAND** |

**cls2[375] is clause 2 exactly** — the shared self-SS-from-GY resolver plus a cost
that takes two filtered monsters from the hand. Clone it.

### Clause 2 — remaining build (short and fully specified)
1. 2 criteria rows on `0x0FB1` at rel **2 and 3** (table above), count-neutral, drop
   2 phantoms. ⚠️ MUST follow clause 1's rows 0/1 — clause 1 is shipped and
   in-game-confirmed and its leaf passes param 0/1 as bare immediates.
2. cls2 record cloning **cls2[375]**, count-neutral (drop a phantom).
3. **The one open question:** how the cost `0x021EC57D` obtains its row index. Either
   it passes param 2/3 as immediates (like clause 1's leaf — then this is pure data and
   NOTHING else is needed), or it reads the per-cid provider `0x02234E78` (whose
   default for `0x0FB1` is 0 — confirmed), in which case add the provider hook.
   **Disassemble `0x021EC57D` for `movs r2,#2` / `movs r2,#3` FIRST** — it decides
   whether clause 2 is data-only.
4. Check `0x021FEBA9` (the condition) is not Simorgh-specific before cloning it.
5. Dark Simorgh is one of the 22 cids in the disambiguation switch `0x02243C1C`; if
   step 3 shows the provider path is used, our donor likely needs equivalent handling.


## Clause 2 — still NOT activating; three hypotheses falsified in-game

Built and in RAM (savestate-confirmed on `rom_lightpulsar.ml2`): the ov5 condition
stub at `0x0239C1A8` AND `cls2[39] = {0x0FB1, 0x0220731D, 0, <cond>, 0x021EC57D, 0}`.
So the wiring is present; the effect is simply never offered from the GY.

### ❌ Ruled out (each cost an in-game test)
1. **Simorgh's `[desc+3] == 0xB` gate.** Removed it (it selects between Simorgh's TWO
   records; we have one). Still not offered.
2. **Wrong zone on the probe.** Hypothesised the enumerator reads criteria row rel 0
   (the GY row) because `param`'s high attribute bits overflow `leftmost + param`.
   Predicted that adding a DARK monster to the GY would make it activate.
   **It did not** — so the condition is not gated on GY contents, and this is wrong.
3. **A missing subscription/registry row.** Treeborn Frog's two extra structures
   (registry `0x0228EB24` x7 -> handler `0x022573DD`, and the sorted list at
   `0x0226D384` x52) are **Treeborn-SPECIFIC** — Plaguespreader, Spore, Quillbolt,
   Ronintoadin, Soulkius and Simorgh are absent from both, yet all work. Likewise the
   effect-registry region `0x0228E000..0x0228F160` contains Spore and Ronintoadin but
   NOT Plaguespreader, Quillbolt, Soulkius or Simorgh. **No shared gate exists there.**

So our donor structurally matches a working card (cls2 record only) and still fails.

### ⏭ NEXT: the diagnostic that splits the search space
`DIAG_C2_ALWAYS_TRUE = True` in `patch_lightpulsar.py` replaces the condition with
`movs r0,#1 ; bx lr`. **This must not ship.**
- offered  -> record/dispatch fine; fault is INSIDE the condition.
- not offered -> condition irrelevant; nothing upstream reaches the record.

### ⚠️ WE DID NOT ACTUALLY COPY DARK SIMORGH (user's instruction, still outstanding)
Simorgh owns **TWO cls2 records** (374 from-hand + 375 from-GY), **FOUR criteria rows**
(GY pair rel 0/1, HAND pair rel 2/3) and **is a case in the disambiguation switch
`0x02243C1C`**. We gave the donor ONE record and are not in that switch. Any of those
three differences could be the blocker. Aligning all of them is the next build.

### 3DS reference (user's other lead) — where to look
`3ds_extract/partition0/exefs/code_dec.bin`, BLZ-decompressed ARM11,
**VA = 0x00100000 + file_offset, ARM/ARMv6**. Engine is table-driven: registries of
fixed-stride records **sorted by Konami ID** with the handler at **`+0x04`**, many
handlers shared templates parameterised by a `param` word
(see `CARDS_ZEXAL_3DS_ASM.md` §0). ⚠️ That doc maps only 12 cards and **Lightpulsar
and Dark Simorgh are NOT among them** — the binary itself must be searched by Konami
ID (Lightpulsar = 99365553).


## ⛔⛔ THE REAL BLOCKER: TWO INCOMPATIBLE SUMMON ARCHITECTURES ON ONE CID

**Diagnostic result (decisive):** with clause 2's condition replaced by
`movs r0,#1 ; bx lr`, the GY effect is STILL not offered. So the condition is
irrelevant and **nothing upstream ever reaches the cls2 record**. Stop editing the
condition/cost -- three earlier fixes there were all beside the point.

**Why.** There are TWO different architectures for an alternative summon:

| architecture | wiring | example |
|---|---|---|
| **A -- Chaos / banish-cost** | hand-SS BST leaf `0x0225FA46` + a row in the SUMMON-PROCEDURE REGISTRY `0x0228F158` -> payment machine `0x0226292D` | Chaos Sorcerer `0x16C9` (and CLAUSE 1 as built) |
| **B -- cls2 record** | one cls2 record per direction, resolver `0x0220731D` (from GY) / `0x02206ABD` (from hand); **NO registry row** | Dark Simorgh `0x1E5A`, Treeborn, Plaguespreader, Soulkius, Spore, Quillbolt |

**Measured: NOT ONE architecture-B card is in the procedure registry** -- Simorgh,
Treeborn, Plaguespreader, Soulkius, Spore and Quillbolt are all ABSENT from
`0x0228F158`; only the architecture-A family is in it.

**Clause 1 (shipped, in-game confirmed) is architecture A**, so its PART G registry
row sends EVERY summon of `0x0FB1` into the from-hand banish-cost handler
`0x0226292D`. That handler has no from-GY case, so the cls2 record added for clause 2
is never reached. The two architectures appear to be **mutually exclusive on one cid**.

**Dark Simorgh proves architecture B does BOTH directions**: cls2[374] from hand
(banish from GY) + cls2[375] from GY (banish from hand), four criteria rows
(GY pair rel 0/1, HAND pair rel 2/3), a case in the disambiguation switch
`0x02243C1C`, and NO procedure-registry row.

### The decision this forces (USER CALL -- clause 1 is shipped and confirmed)
- **(i) REBUILD CLAUSE 1 THE SIMORGH WAY.** Drop PART G's registry row and PARTS
  A/D/E/F, and express BOTH clauses as two cls2 records + a 4-row criteria block +
  a switch case, exactly mirroring `0x1E5A`. This is what "copy Dark Simorgh" means
  and it is the only configuration proven to support both directions. ⚠️ It means
  reworking a clause that currently works in-game, and it gives up clause 1's
  ov3-only/puzzle-capable property (Simorgh's condition/cost need our attributes).
- **(ii) KEEP CLAUSE 1 AS IS AND DROP CLAUSE 2** (ship clauses 1 + 3 only).
- **(iii) Prove the exclusivity first** before spending the rework: give the donor
  BOTH the registry row and the cls2 record (current state) and single-step
  `0x02264DAE`'s search under GDB during a GY-summon attempt to confirm the handler
  is entered and swallows the GY case. One measurement; settles it.

⚠️ `DIAG_C2_ALWAYS_TRUE = True` IS STILL SET in `patch_lightpulsar.py`. It must be
reverted before anything ships -- clause 2's condition currently returns 1 always.


## ✅ GDB CONTROL (Dark Simorgh, 2026-08-13) — the dispatcher, and what [desc+3] IS

Armed `0x021FEBA8` (Simorgh's cls2 condition) and just played. It fired TWICE per
evaluation, once per cls2 record:

```
call #1  LR=0x0224AE13  desc@0x027E3280: 5a1e 00 0e 0002 ... 0a00 ...   [+3]=0x0E
call #2  LR=0x0224AE13  desc@0x027E3620: 5a1e 00 0b 0002 ... 0400 ...   [+3]=0x0B
```

**1. THE cls2 CONDITION DISPATCHER IS `0x0224AE13`** (the call site; LR at entry).
This is the routine that enumerates a card's cls2 effects and asks each one "are you
usable?" -- the thing our record is never reached by.

**2. `[desc+3]` IS THE EFFECT/RECORD SELECTOR, NOT A SIMORGH QUIRK.** Its two records
are dispatched with **0x0E** and **0x0B**, and the condition's `cmp [desc+3],#0xB`
picks its from-GY half. **So removing that test was a mistake of understanding** --
it is not Simorgh-specific scaffolding, it is how a multi-effect card tells which of
its effects is being interrogated. (Harmless in our build only because our card has
one record; but the byte's MEANING is now known.) `[desc+0x0C]` also differs per
record (0x0A vs 0x04).

**3. THE REAL BLOCKER IS NOW PRECISELY LOCATED.** Our condition never fires at all,
while the native card's fires twice on the same screen. So the fault is NOT in our
condition, cost, criteria rows or the procedure-registry clash -- it is that
**`0x0224AE13`'s enumerator never offers our cid's cls2 record**.

### NEXT EXPERIMENT (narrow and concrete)
Disassemble around the call site `0x0224AE13` (i.e. the function containing it) and
find what it iterates and what gates a cid out. Candidates in priority order:
(a) it walks a per-cid list/registry of "cards with usable GY effects" that our donor
    is absent from -- the exact shape of the clause-1 trap;
(b) it filters on a card_prop bit (our donor is a converted NORMAL MONSTER -- check
    the Effect-Monster/type bits actually written);
(c) it requires the record's `+08` slot (Quillbolt has one, Treeborn/Simorgh do not).
With the dispatcher known, a second GDB run can breakpoint INSIDE it and watch it
accept Simorgh and skip `0x0FB1` in the same pass -- that would name the gate outright.


---

# Session 2026-08-14 — CLAUSE 2 ROOT CAUSE FOUND (offline, no emulator)

Scope: continue clause 2. The handoff's next step was "disassemble the function
containing `0x0224AE13`, find what it iterates and what filters a cid out."
**Done, and the answer is candidate (a): a per-cid registry our donor is absent
from.** Everything below was measured this session against the CLEAN image plus
the KB; nothing is inherited.

KB health: `verify_knowledge --savestate data/over_the_nexus/working/sealancer_recon.ml3`
= **226 facts, 197 PASS, 0 FAIL, 29 UNVERIFIED.**

## Confirmed (this session)

### ✅✅ ROOT CAUSE — the GY-ACTION REGISTRY `0x0228DDF8`

A table of **60 rows x 0x10 B** at **`0x0228DDF8`**:

```
+0x00  u32  cid
+0x04  u32  zone         0x0E = Graveyard (52 rows), 0x0D = Deck (8 rows)
+0x08  u32  check_fn
+0x0C  u32  post_fn
```

**NOT sorted — linear-scanned.** Four scanners, each bounded by a hard-coded
`cmp rX,#0x3C` (60):

| scanner | keyed on |
|---|---|
| `0x0224C88E` | `[row+4]` zone (`ldr r1,=0x0228DDF8 ; lsls r0,r6,#4 ; adds r0,r1,r0`) |
| `0x0224CD14` | `[row+0]` cid, then `blx [row+0xC]` |
| `0x0224CBD8` | index, tests `[row+0xC] == 0x0224C669` |
| `0x0224CD42` | cid, tests `[row+0xC] == 0x0224C7C1` |

Three check/post families: `0x0224C591`/`0x0224C6C1` x45 (**the GY-effect
family**), `0x0224C63D`/`0x0224C7C1` x9, `0x0224C55D`/`0x0224C669` x6.

**Membership — measured:**

| cid | card | in table? |
|---|---|---|
| `0x1E5A` | Dark Simorgh | **IN** |
| `0x1EA9` | Plaguespreader Zombie | **IN** |
| `0x1E15` | Quillbolt Hedgehog | **IN** |
| `0x202C` | Fabled Soulkius | **IN** |
| `0x225B` | Spore | **IN** |
| `0x2387` | Glow-Up Bulb | **IN** |
| `0x2269` | Ronintoadin | **IN** |
| **`0x0FB1`** | **our donor** | **ABSENT** |
| `0x19CB` | Treeborn Frog | absent — see the warning below |

### ✅ The offer path, closed end to end

```
registry 0x0228DDF8 row {cid, zone 0x0E, 0x0224C591, 0x0224C6C1}
  -> 0x0224C590(side, cid, ref)   builds a 0x24-B descriptor: zone 0x0E, class 2,
                                   event code read from the queue 0x0229A37C
  -> 0x021EC740(desc, other)
  -> 0x021EDA14                   the COMMIT body (0x021EDA08 is a thunk into it)
  -> 0x0224AD94(desc, arg)        <- LR 0x0224AE13 is INSIDE THIS FUNCTION
  -> find_event_handler 0x0224A118
  -> record[+0x0C]                the activation condition
```

`0x0224C590` / `0x0224C6C0` have **zero BL callers in ov3** — they are reachable
only as the function pointers in that registry (45 rows each). No row -> no
descriptor -> the condition is never called. That is exactly the symptom.

### ⚠️⚠️ TREEBORN FROG IS NOT A VALID CONTROL — it misled two sessions

The earlier conclusion "a pure SS-this-card-from-GY card needs ONLY a cls2 record"
was derived from Treeborn Frog owning `cls2[199]` and nothing else. Treeborn is a
**Standby-Phase trigger**, registered through its own two structures
(`0x0228EB24`, `0x0226D384`) — the very structures that session dismissed as
"Treeborn-specific". It is the ONE card in the family absent from `0x0228DDF8`.
Every *ignition-style* GY summoner is in the registry. Profile Plaguespreader or
Soulkius instead.

### ⚠️ Why the registry was wrongly ruled out before

The "missing subscription/registry row" hypothesis was tested over
`0x0228E000..0x0228F160`. That window starts **inside** this table and misses its
first 32 rows — which is where Simorgh, Plaguespreader, Quillbolt and Soulkius
all live. From the true base `0x0228DDF8` the pattern is unambiguous.

## ❌ Ruled Out / CORRECTED (this session)

1. **"`[desc+3]` is the effect selector."** WRONG — it is the **ZONE**.
   KB-VERIFIED (`event.register_prim_descriptor_layout`:
   `desc[+3] = (word >> 16) & 0x1F`, `strb` @`0x021D31A8`). The GDB control's two
   Simorgh hits were **two different card instances** — `[desc+0xC]` (the packed
   ref) was `0x000A` vs `0x0004` — one Simorgh in the GY (zone `0x0E`) and one in
   the hand (zone `0x0B`). NOT "one call per cls2 record".
2. **"`0x0224AE13`'s enumerator never offers our record."** There is no enumerator
   there. `0x0224AD94` is a **single-descriptor query**: `find_event_handler`,
   then `blx [record+0x0C]` if non-zero. With NO record found it returns
   **1 = ACCEPT** (`event.admission_accepts_recordless`), so a missing record
   could never suppress an offer. The gate had to be upstream, and it is.
3. **"There is a shared per-cid list of GY-effect cards as a contiguous u16
   array."** No — swept ov3 and arm9 for a window containing all six family cids
   as u16; zero hits. The registry stores cids as **u32 at stride 0x10**, which is
   why the u16 sweep missed it.
4. **The per-card capability enumerator `0x0224BC40` is NOT the offer path for a
   GY effect.** It dispatches on zone through a 16-entry jump table at
   `0x0224BCD2` (zone 0x0B hand -> `0x0224BEFC`, which is where the hand-SS BST
   `0x0225E51C` is consulted at `0x0224C026`; zones 0x0C..0x0F -> `0x0224C0E6`).
   The 0x0C..0x0F arm is four instructions of cid-blind work (`0x0224B7CC` +
   `0x0224B838`). A GY effect is **event-driven**, not a capability bit.
5. **COMMIT `0x021EDA08` has only two callers** — the register-prim admission
   `0x021D31CC` and `0x02263A76` (which builds a class-**1**, zone-**0**
   descriptor). Neither is the GY offer path; `0x021EC740` calls the COMMIT
   **body** `0x021EDA14` directly.

## ⚠️ SEPARATE BUG FOUND IN PART J (not the blocker)

Simorgh's condition `0x021FEBA8` branches on the zone:

```
0x021FEBAC  ldrb r2,[r4,#3]   ; zone
0x021FEBB0  cmp  r2,#0xB      ; card in HAND?
0x021FEBB2  bne  0x021FEBFE   ; -> the from-GY arm
   ; HAND arm: probe DARK 0x20000000 then WIND 0x60000000 via 0x02243FE0,
   ;           then 0x021F0384 / 0x021BA440        <- cls2[374], SS from HAND
0x021FEBFE ; GY arm: 0x021F04FC, 0x021BABE8(side), 0x0224401C(desc), ...
   ;                                               <- cls2[375], SS from GY
```

PART J cloned the **HAND arm** and tail-jumps into that arm's epilogue
(`0x021FEBDC`). Clause 2's card sits in the **GY**, so it is the wrong half — it
probes clause 1's GY criteria rows instead of clause 2's hand rows. It did not
cause the current failure (the condition provably never runs), but it is why the
earlier note "a donor cloning a multi-record card's condition must drop any such
record-selector test" was reasoning from a wrong premise: the test is a ZONE test,
and dropping it made the condition zone-blind rather than record-agnostic.

## Clause 3 — two structural constraints, now measured

- **No criteria row is available.** Clause 1 owns rel 0/1 and clause 2 owns rel
  2/3; a revive row would be rel 4 = a 5-row block. Max native block is 4
  (`dispatch.criteria_block_size_tiers`).
- **No second cls2 record either.** `find_event_handler` returns
  `leftmost + r0`, `r0` in {0,1} (`movs r0,#1` @`0x0224A7FC`, `movs r0,#0`
  @`0x0224A802`, common tail @`0x0224A804` which walks back to the leftmost row,
  adds r0, bounds-checks and returns `base + idx*0x18`). `r0` becomes 1 only via
  the data lists `0x02275B60` (x19, tests `[desc+4]==2`), `0x02275B86` (x25,
  `[desc+4]==6`), `0x02275BB8` (x38, `[desc+0x18]`) — or the per-cid BST at
  `0x0224A1F2`, which is where Dark Simorgh (2 cls2 records, in NONE of the three
  lists) is handled. None of the three lists separates clause 2's descriptor from
  clause 3's (sent-to-GY = event code `0x1F`), so a second record needs a code
  edit or it is shadowed — the Warwolf E1/E2 trap.

=> Clause 3 shares the SINGLE cls2 record and branches on `[desc+4]` (the event
code), per `event.optional_trigger_is_record_shape`'s composition note.

## Next Experiment

**PART K**: claim a phantom row in `0x0228DDF8` for the donor. Phantoms already in
the correct family (`0x0224C591`/`0x0224C6C1`) and zone (`0x0E`):

| row | address | phantom cid |
|---|---|---|
| 15 | `0x0228DEE8` | `0x0EB2` |
| **47** | **`0x0228E0E8`** | **`0x0E3E`**  <- taken |
| 48 | `0x0228E0F8` | `0x0E64` |

Unsorted + linear-scanned => overwriting the cid word is a **4-byte in-place
edit**, count-neutral by construction, no sort to maintain, both `cmp #0x3C`
bounds untouched.

User decision 2026-08-14: **PART K alone in this build; PART J's zone stays
untouched** so the in-game test changes exactly one variable. If the effect is
offered at all, PART K is proven; the wrong-zone condition then shows up as the
wrong cards being offered to send, which is itself diagnostic.

## ⛔ IN-GAME TEST (PART K alone) — STILL NOT OFFERED (2026-08-14)

User-reported on `rom_lightpulsar.nds`; savestate `rom_lightpulsar.ml3`.

### Savestate evidence — the setup and the patch were both correct
Parsed with the version-independent RAM auto-detect (RAM0 file offset **0x24**):

- **PART K IS RESIDENT.** Registry row **[47] @0x0228E0E8 = {cid 0x0FB1, zone 0x0E,
  check 0x0224C591, post 0x0224C6C1}** — byte-identical in shape to Dark Simorgh's
  row [7]. Phantom `0x0E3E` is gone.
- cls2 record, all four criteria rows and the ov5 condition stub: all resident.
- **The card really was in the Graveyard.** The GY array is **player + 0x55C**
  (count at player+0x14 = 3): `Reload 0x16D9`, `Upstart Goblin 0x131F`,
  **`0x0FB1`**. Hand count (player+0x0C) = 3; deck (player+0x304) = 33, holding two
  more copies of `0x0FB1`; Extra (player+0x4E4) = 5.

**So PART K was NECESSARY BUT NOT SUFFICIENT.** The row is right, the card is in
the right zone, and the effect is still not offered.

### ✅ The enumerator's own filters — both cleared, so the scan DOES reach us
The registry scanner is `0x0224C820(r0 = side, r1, r2 = packed)`, where
`[sp+0x18] = r2 & 0xFF` is the ZONE to sweep. Its two per-cid filters:

1. `0x0202345C(cid) >= 2`, but **only when `[sp+4]`** (mode 2, or some pending
   event byte > 6). `0x0202345C` returns a SPELL-SPEED class: spell (type 0x17) ->
   2 if subtype 5 else 1; trap (0x18) -> 3 if subtype 1 else 2; **monster ->
   binary-searches the 118-entry sorted list `0x0209C118`, 2 if found else 1.**
   That list is the QUICK-EFFECT register (Kuriboh `0x0FE0` is in it) and **NONE**
   of Simorgh / Plaguespreader / Quillbolt / Soulkius / Spore / Glow-Up Bulb /
   Ronintoadin is in it — the whole family relies on the bypass at `0x0224C8D0`
   (`[0x0229DD14+0x34] == side && [0x0229DD14+0x48] in {2,4}` = **your own Main
   Phase**), which skips the speed test entirely. **RULED OUT as our gate.**
2. `0x022393CC(...)`, gated on `[sp+8]` (mode 1 only).

Then `0x0224C900` counts the zone (`0x0219CE2C(side, zone)`), walks it backwards,
matches the cid with `0x0219CAE4(side, zone, idx)`, takes the ref from
`0x0219CBB8(...)` and calls **`[row+8]` = check_fn `0x0224C591`** with
`(side, cid, ref)`. So the remaining gate is **inside `0x0224C590` ->
`0x021EC740` -> COMMIT `0x021EDA14` -> our condition**.

### ✅✅ AND THE CONDITION IS DEMONSTRABLY WRONG — PART J fixed this round
`0x021F04FC`, the FIRST check of Simorgh's from-GY arm, does:

```
0x021F0506  bl 0x021A2510(side, [desc+0xC])   ; resolve the packed ref
0x021F0516  ldr r1,=0x0229AC94 ; muls r2,r3,#0xB3C
0x021F0522  ldr r1,=0x0000055C ; adds r1,r2,r1   <-- player + 0x55C = THE GRAVEYARD
0x021F0528  bl 0x021A2618                        ; validate the card there
```

That is **the exact array the savestate shows our card sitting in**. Our condition
never ran it: it tail-jumped to `0x021FEBDC`, the from-HAND arm's epilogue
(`0x021F0384` -> `0x021F0114(side)` + `0x021B9EC0(side, cid)`; then `0x021BA440`).

**FIX (built): retarget the tail from `0x021FEBDC` to `0x021FEBFE`** — Simorgh's
from-GY arm — restoring `r0 = desc`, `r1 = the original arg`, which is exactly the
register state Simorgh's own `bne 0x021FEBFE` arrives with. Frame-compatible: that
arm returns through the same `pop {r3,r4,r5,pc}` our prologue pushed. Stub is 60 B
of 64 reserved, disassembled and Thumb-1 clean.

### ⏭ NEXT: two ROMs, one sitting
| ROM | condition | reads |
|---|---|---|
| `rom_lightpulsar.nds` | the real, GY-arm condition | offered -> **clause 2 works** |
| `rom_lightpulsar_diag.nds` | `DIAG_C2_ALWAYS_TRUE` (`movs r0,#1 ; bx lr`) | test only if the real one fails: offered -> the path is live and the fault is still inside the condition; NOT offered -> a gate remains inside COMMIT `0x021EDA14` |

⚠️ `DIAG_C2_ALWAYS_TRUE` is **False** in the module on disk; the diagnostic ROM was
produced by setting it at runtime only. It must never ship.
⚠️ Normal duel only (the condition is in the ov5 cave). Re-check clause 1 too.

## ⛔ IN-GAME TEST (PART K + the GY-arm condition) — STILL NOT OFFERED (2026-08-14)

Savestate `rom_lightpulsar.ml3`, RAM0 file offset 0x24. **The build and the setup
were both correct**, so this is a real negative, not a mis-test:

- ov5 stub head `38b5041c0d1ca078` = the **REAL** 60 B condition (not the DIAG one).
- PART K row [47] = `{0x0FB1, 0x0E, 0x0224C591, 0x0224C6C1}` — resident.
- **GY (player+0x55C, count player+0x14 = 5):** Upstart Goblin, Into the Void,
  Magical Mallet, Soul Release, **`0x0FB1`**. ✅ the card is in the Graveyard.
- **HAND (player+0x124, count player+0x0C = 3):** Red-Eyes Darkness Metal Dragon
  `0x1D85` (**DARK** monster), **`0x0FB1`** (our own card — retuned to **LIGHT**),
  Dark Hole `0x10F6`. ✅ a LIGHT and a DARK monster really were in hand.

**Player-struct map, measured here (worth keeping):** hand `+0x124` (count
`+0x0C`), deck `+0x304` (count `+0x10`), Extra `+0x4E4` (count `+0x18`),
**GY `+0x55C` (count `+0x14`)**.

### ✅ The whole offer path is now disassembled — and it is CID-BLIND

```
0x0224C820(side, _, packed)   registry sweep; [sp+0x18] = zone
  |  filter 1: 0x0202345C(cid) >= 2, ONLY when [sp+4] -- and BYPASSED entirely at
  |            0x0224C8D0 during your own Main Phase
  |            ([0x0229DD14+0x34]==side && [0x0229DD14+0x48] in {2,4})
  |  filter 2: 0x022393CC(...), only when [sp+8] (mode 1)
  |  then walks the zone (0x0219CE2C count, 0x0219CAE4 cid, 0x0219CBB8 ref)
  -> check_fn 0x0224C590(side, cid, ref)   builds desc{zone 0x0E, class 2,
                                            event code from queue 0x0229A37C}
  -> 0x021EC740
       zone <= 0x0A  -> ON-FIELD branch: desc[+5]=3, gate 0x0224A874
                        (⚠️ that gate asks "does this cid own a CLASS-3 record?";
                         42 of the 45 GY-family cids own none -- it is NOT on our
                         path, because GY zone 0x0E > 0x0A)
       zone >  0x0A  -> OFF-FIELD branch @0x021EC892: desc[+5] = 2 (cls2), then
                        gate 0x021ECC6C, then COMMIT 0x021EDA14
  -> 0x0224AD94 -> find_event_handler -> record[+0x0C]
```

`0x021ECC6C`, with no pending event: `0x021A87BC(desc) >= 2` passes outright,
else a 5-cid whitelist (`0x131E`, `0x14D7`, `0x154C`, `0x1E08`, `0x2272`), else
**`0x021ECC28(desc)`**, which is:

```
own turn ([0x0229DD14+0x34] == desc[+2]^desc[+6])  and  phase [+0x48] in {2,4}
and ( desc[+4] <= 6                      -> 1
      or (desc[+3] <= 4 and desc[+4] in {7,8,9}) -> 1 )
else 0
```

i.e. for an **off-field** card (zone 0x0E > 4) the event code `desc[+4]` must be
**<= 6**. `desc[+4]` comes from the pending-event queue byte
(`0x0229A37C + 0x838 + i`), and `0x021EC740` re-writes it per queued event at
`0x021EC8CE`.

**But `0x021A87BC` is not a discriminator.** Simulated over cids 0x0D00..0x24FF:
**Dark Simorgh `0x1E5A`, Plaguespreader `0x1EA9`, Treeborn `0x19CB` AND our donor
`0x0FB1` all reach the SAME leaf `0x021A894C`** (the 4149-cid default bucket).
And `0x021ECC28` reads only `desc[+2]/[+3]/[+4]/[+6]` — no cid at all.

**So every gate from the registry sweep down to COMMIT treats our donor exactly
like the working cards.** Static analysis cannot separate them any further; the
difference must be inside COMMIT `0x021EDA14`, in `find_event_handler`'s record
selection, or in the condition's return value.

### ❌ Also ruled out this round
- **The quick-effect / speed-2 list `0x0209C118`** (118 sorted u16, searched by
  `0x0202345C` for monsters). Kuriboh `0x0FE0` is in it; **none** of the GY family
  is. Not our gate.
- **A missing CLASS-3 record** (`0x0224A874`). Real gate, but only on the
  **on-field** branch (`zone <= 0x0A`); the GY path never reaches it.
- **`0x02234E78`'s param-provider lists** — Simorgh is in none of them either
  (lists `0x022710E2` x17, `0x02271104` x28, `0x022710B2` x12, `0x0227109C` x11,
  `0x022710CA` x11), so they are not how its from-GY direction addresses rows.

### ⏭ NEXT — the measurement, not another fix
Run **`rom_lightpulsar_diag.nds`** (`DIAG_C2_ALWAYS_TRUE`, condition = `movs r0,#1
; bx lr`). It splits what static analysis no longer can:
- **offered** -> the path is live and the fault is inside the condition (most
  likely `0x0224401C`'s pass/row addressing, since Simorgh's from-GY arm drives
  its two passes through `desc[+0x12]` = 0 then 1, and `0x02244030` loops
  `0x02243FE0(side, cid, i)` for `i < hand_count`);
- **not offered** -> a gate remains inside COMMIT `0x021EDA14`, and the next step
  is the ONE-SHOT GDB run with breakpoints at `0x0224C590`, `0x021ECC6C` and
  `0x021EDA14`, Simorgh and Lightpulsar both in the GY.

## ✅✅ DIAG RESULT — THE OFFER PATH IS LIVE. PART K IS PROVEN. (2026-08-14)

User-reported on `rom_lightpulsar_diag.nds`: **the effect IS activatable from the
GY**, and the selection appears — but **only the leftmost card in the hand can be
picked.**

So everything upstream is CORRECT and IN-GAME CONFIRMED: the GY-action registry
row (PART K), the cls2 record, `0x0224C590`, `0x021EC740`, `0x021ECC6C`, COMMIT
`0x021EDA14`, `find_event_handler`. **The remaining fault is entirely inside the
condition/cost pair.** No further GDB run is needed.

### ✅ Why only one card is selectable — the mechanism, end to end

The cost `0x021EC57D` is a 4-state machine on `[0x0229AAFC+0x7C]`:

| state | address | what it does |
|---|---|---|
| 0 | `0x021EC59C` | `desc[+0x12] = 0` (**the PASS INDEX**), prompt `0x0219A818(side, 0x15D)` |
| 1 | `0x021EC5B0` | `0x0224B9F0(side, cid, r2 = 0, callback 0x022065F9)` — **`movs r2,#0` is a HARDCODED IMMEDIATE, on BOTH passes** |
| 2 | `0x021EC5BE` | take the pick, store it at `desc[+0x14 + pass*2]`, `desc[+0x12]++`, loop to state 1 while `< 2` |
| 3 | `0x021EC60E` | actually send both picks (`0x021C6E98`) |

`0x0224B9F0` is pure setup: `[0x0229DD94+0x4C] = 8` (mode), **`[+0x50] = param`**,
`[0x0229DE14+0x0C] = callback`, `[+0x74] = side`, `[+0x60] = cid`.

The per-candidate filter is the callback **`0x022065F9`**:
```
r0 = candidate side, r1 = candidate ZONE, r2 = param
desc = [0x0229A9FC+0x50]                  ; the acting descriptor
if side != desc[+2]^desc[+6]  -> 0
*** if r1 != 0x0B -> 0                    ; THE CANDIDATE MUST BE IN THE HAND ***
r1 = desc[+0] (the acting cid; a small BST redirects 0x183E/0x1935/0x201E/0x219E)
bl 0x02243FE0(side, cid, param)           ; THE CRITERIA PROBE
return (hit ? 0x800 : 0)
```

**⚠️ CORRECTION to `dispatch.criteria_zone_is_the_handler`: on THIS path the ZONE
is enforced by the CALLBACK (`cmp r1,#0xB`), not by the row's handler.** The row
supplies only the attribute/race/level filter.

And the row index comes from `0x02243B9C(cid, param)`, whose disambiguation for a
cid **in membership list A `0x0227134C`** is (read at `0x02243BEC`-`0x02243C00`):

```
if cid in list A:  r4 = (param == 0) ? 0 : 1      ; a pure 0/1 FLAG
```

Our donor is in list A (clause 1 needs it). So:
- **clause 1** passes param 0 then 1 as bare immediates -> rows 0 (LIGHT) and 1
  (DARK). ✅ exactly the in-game behaviour.
- **clause 2's cost** passes param **0 on both passes** -> r4 = 0 -> **row 0 =
  LIGHT** every time. The only LIGHT monster in the test hand was our own second
  copy of `0x0FB1`, so exactly ONE card was selectable — the reported symptom —
  and pass 2 would ask for LIGHT again and find nothing.

### ✅ The consequence: clause 2 needs NO new criteria rows at all

Because the callback already pins the zone to the hand, **clause 1's existing rows
0/1 (LIGHT, DARK) are exactly what clause 2 wants** — "send 1 LIGHT and 1 DARK
monster from your hand". The HAND-handler rows at rel 2/3 (PART H) are
unreachable under the list-A 0/1 clamp and are now redundant (harmless; left in
place for now).

**THE WHOLE FIX IS ONE VALUE: the cost must pass `param = desc[+0x12]` (the pass
index) instead of the hardcoded 0.**

### ⏭ NEXT: a bespoke clause-2 cost (PART L)
`0x021EC57D` is Dark Simorgh's shared cost, so it cannot be edited in place.
Clone its state machine into the ov5 cave (clause 2 is already normal-duel-only)
with `movs r2,#0` replaced by `ldrh r2,[r4,#0x12]`, and point the cls2 record's
`+10` at it. Write the four states with explicit compares rather than copying the
PC-relative `add pc, r0` jump table. ~0x70 B.
## BUILT — PART L + a simplified PART J (2026-08-14)

Rather than clone Simorgh's whole state machine, **PART L repoints the CALLBACK
POINTER** the cost loads and overrides `param` there, cid-scoped:

- literal slot `0x021EC644` (stock `0x022065F9`) has **exactly one loader**,
  `ldr r3,[pc,#0x8c]` @`0x021EC5B4` — resolved every PC-relative LDR in ov3 to
  confirm. The callback address appears in 27 other pools; none is touched.
- the trampoline (44 B) tests `desc[+0]` against `0x0FB1` and, only then, replaces
  `param` with `desc[+0x12]` before tail-calling the native filter. **Dark Simorgh
  reaches `0x022065F9` with its own param unchanged.**
- ⚠️ **ov3 dead code at `0x0225F290`, never the ov5 cave** — `0x021EC57D` is shared
  with Simorgh and runs in puzzles, where ov41 evicts ov5. The block is now
  **124/126 B** used (pay-1 44 + pay-2 36 + callback 44).

**PART J simplified to an 8 B thunk.** The two attribute probes were cloned from
Simorgh's from-HAND arm, where the attribute rides in `param`'s top nibble — an
idiom that cannot work for a **list-A** cid, whose row is clamped to
`param == 0 ? 0 : 1`, so both probes resolved to row 1 (DARK) and the pair was a
spurious double-DARK test. Simorgh's from-GY arm already does the correct check
and is entirely cid-generic (`0x021F04FC` in-GY, `0x021BABE8` may-SS, then
`0x0224401C` twice with `desc[+0x12]` = 0/1). The stub is now just
`ldr r3,=0x021FEBFF ; bx r3` and exists only to host `DIAG_C2_ALWAYS_TRUE`.

**Once clause 2 is in-game confirmed: point the cls2 record's `+0C` straight at
`0x021FEBA9` and drop the ov5 slot** — that makes clause 2 ov3-only and therefore
puzzle-safe like clause 1, and removes the current risk that the record's ov5
condition is evaluated in a puzzle (where it would jump into overlay-41 data).

`verify()` = **60/60 PASS**. KB = **230 facts, 201 PASS, 0 FAIL**, with the new
`dispatch.selection_param_and_zone` recording the cost state machine, the
callback's hardcoded hand gate, and the list-A param clamp.

### Expected in-game behaviour
Pass 1 offers the **LIGHT** monsters in hand (criteria row 0), pass 2 the **DARK**
ones (row 1); both are sent by Simorgh's state 3.
⚠️ **KNOWN DEVIATION, not yet fixed:** Simorgh's state 3 calls `0x021C6E98`, which
**banishes** — Lightpulsar's clause 2 should *send to the Graveyard*. If the two
picks end up banished rather than in the GY, that is this, and the fix is a
send-to-GY primitive in a bespoke state 3 (`0x021C6CA8`, hand 0x0B -> GY 0x0E).

## ⛔ FREEZE — and the rule that caused it (2026-08-14)

**Reported: the game freezes the moment Lightpulsar reaches the Graveyard.**
Savestate `rom_lightpulsar.ml2` confirms the culprit was resident: the ov5 slot
held `004b 1847` = the 8-byte thunk `ldr r3,=0x021FEBFF ; bx r3`.

**Cause — my error, introduced when the attribute probes were removed.** Dropping
the probes also dropped the PROLOGUE. `0x021FEBFE` is the from-GY **arm** of
Simorgh's condition, not an entry point:

- it reads the descriptor out of **`r4`**, and
- it returns through **`pop {r3,r4,r5,pc}`** @`0x021FEC3E`.

A bare thunk pushes nothing, so that `pop` takes four words that were never
pushed and returns to garbage — and `r4` was never the descriptor either. The
earlier 60 B stub happened to be correct only because it opened with Simorgh's
own `push {r3,r4,r5,lr} ; adds r4,r0,#0 ; adds r5,r1,#0`.

**Fix — point `+0C` at the NATIVE entry `0x021FEBA9`.** It performs its own
prologue, tests `desc[+3]` itself, and routes a GY card into the very same arm
with a correct frame. Strictly less code than any thunk, and two bonuses:

- **clause 2 is now ov3-only, hence PUZZLE-SAFE like clause 1**, and
- **the ov5 cave slot is released** (ledger: 88 slots, **79 live**, was 80).

The ov5 stub now exists ONLY for `DIAG_C2_ALWAYS_TRUE`; `_stub_c2_cond` raises if
called with DIAG off, and `main()` installs nothing in ov5 for a shipped build.

New KB fact **`dispatch.midfunction_tail_needs_prologue_frame`** (VERIFIED)
records the rule: *a cls-record slot may point at a whole function, never at a
mid-function arm, unless you reproduce that function's prologue exactly.*

`verify()` = **61/61 PASS** (a new check pins `+0C` to the native address).
KB = **231 facts, 202 PASS, 0 FAIL**. Allocation guard: no overlaps, ledger in
sync.

## ⛔ SELECTION BUGS — and the hard engine limit behind them (2026-08-14)

**No freeze now.** The effect activates from the GY and the selection opens. Two
faults reported: **(a) every card in the hand is selectable, not just LIGHT/DARK
monsters** (`rom_lightpulsar.ml3`), and **(b) after picking one card the game
hangs** (`rom_lightpulsar.ml4`). Both savestates confirm the intended build:
`+0C = 0x021FEBA9`, callback literal `0x021EC644 = 0x0225F291`, the four criteria
rows resident, donor in list A.

### ❌ MY "the zone is the callback" CORRECTION OVER-REACHED
`0x022065F9`'s `cmp r1,#0xB` restricts which ZONE THE CURSOR may sit in, but the
actual per-candidate matching is the criteria probe `0x02243FE0`, whose
enumeration zone comes from **the row's handler** after all. PART L makes the cost
address rows 0/1 — whose handler is `0x0223CA11`, the **GY** enumerator. It
therefore counts LIGHT/DARK monsters *in the Graveyard* (our own copy is one), is
non-zero regardless of which hand card the cursor is on, and so filters nothing.
That is symptom (a) exactly, and (b) is almost certainly its consequence.
`dispatch.criteria_zone_is_the_handler` stands; my refinement was wrong.

### ⛔⛔ THE HARD LIMIT: cid `0x0FB1` CAN ONLY EVER ADDRESS ROWS 0 AND 1
The fix "make the cost address rows 2/3 (handler `0x0223CB19`, hand-select)" is
**impossible for this cid**. Traced `0x02243B9C`'s disambiguation for `0x0FB1`:

| donor's list membership | resulting r4 | reachable rows |
|---|---|---|
| **in membership list A** | `param == 0 ? 0 : 1` (`0x02243BFA`) | **{0, 1}** |
| in neither list | BST `0x02243C1C`: `0x208A`> , `0x1895`> , `0x0E79`< -> `0x02243C56`, `0x1686`> -> `0x02243C60`, `!= 0x1522` -> **`0x02243EEC` = `movs r4,#0`** | **{0}** |

So leaving list A makes it strictly worse (row 0 only, which would also break
clause 1's DARK pass). **Rows 2 and 3 are unreachable either way — the PART H
insert can never be read.** The four-row block is a dead end.

### ⏭ THE DESIGN THAT GETS ROUND IT: probe with a PROXY CID
The native callback already supports probing under a *different* cid — its own
BST redirects `0x183E`/`0x1935`/`0x201E`/`0x219E` to a cid fetched from elsewhere
(`0x02206634`). So PART L should, for our donor only, run the probe against a
**proxy phantom cid whose rows 0/1 are the HAND pair** (handler `0x0223CB19`,
words `0x01000002` / `0x02000002`) and which is itself in membership list A so
param 1 reaches its row 1.

Cheapest implementation: keep delegating to the native filter, but have the
trampoline temporarily swap `desc[+0]` to the proxy cid across the call and
restore it afterwards (~46 B, vs 44 B today).

**⚠️ SPACE IS THE BLOCKER.** The ov3 dead run `0x0225F240` is at **124/126 B**;
every other dead block is fragmented (largest contiguous free run **16 B**). The
trampoline cannot grow more than 2 B where it is, and it must stay in ov3 — the
cost `0x021EC57D` is shared with Dark Simorgh and runs in puzzles, where ov41
evicts the ov5 cave. So this needs either a tighter stub or a new proven-dead ov3
block (the 126 B run was found by proving two dead dispatch arms unreachable; the
same technique should yield more).

**Slots this would need:** the proxy phantom cid (2 criteria rows, moved off
`0x0FB1` from rel 2/3 — so PART H is repurposed, not added to) plus one more
list-A phantom drop (list A has phantoms `0x0E32`, `0x0EA8`, `0x1303`, `0x234E`
besides the `0x0E6B` we already took).

## ✅ BUILT — the proxy cid, and the space problem DISSOLVED (2026-08-14)

User asked to move code into ov5 to free ov3 space. **That turned out to be
unnecessary**, and it would have been actively harmful: both stub sites are on
paths shared with NATIVE cards (the payment dispatch with the Chaos family, the
selection callback with Dark Simorgh), and an ov5 target on a shared path does not
go inert in a puzzle — ov41 evicts ov5, so the engine executes overlay-41 data and
**freezes those cards too**.

**The proxy needed no new space at all.** Phantom **`0x1303`** is the ideal
stand-in and was already sitting there:

- it is a phantom (no `card_prop`), so no real card is touched;
- it **already owns exactly two adjacent criteria rows** (94/95);
- it is **already in membership list A**, so its `param 1` genuinely reaches its
  row 1.

So its two rows are **rewritten in place** to the hand-select pair
(`fn 0x0223CB19`, words `0x01000002` / `0x02000002`): registry size, sort order
and every membership list are structurally untouched. And the **donor drops back
to two rows**, restoring the "in list A => exactly two rows" invariant that the
4-row block had violated.

PART L's trampoline (still 44 B, still in ov3 at `0x0225F290`, 124/126 B used)
now, for our cid only:

```
r5 = [0x0229A9FC+0x50]        ; the acting descriptor
r4 = desc[+0]                 ; save the real cid
if r4 == 0x0FB1:
    r2 = desc[+0x12]          ; param  = the PASS INDEX (0 then 1)
    desc[+0] = 0x1303         ; probe under the PROXY
bl 0x022065F9                 ; the native filter, unchanged
desc[+0] = r4                 ; restore (a no-op for every other cid)
```

Dark Simorgh reaches the native filter with its own cid and its own param, exactly
as before.

**Expected:** pass 0 enumerates LIGHT monsters **in the hand** (proxy row 0,
hand-select handler), pass 1 the DARK ones (proxy row 1).

`verify()` = **61/61 PASS** (the H checks now assert the donor owns exactly two
rows and the proxy carries the hand pair while sitting in list A).
KB = **231 facts, 202 PASS, 0 FAIL.** Allocation guard clean; ledger records
`0x1303` as REPURPOSED rather than dropped.

⚠️ Still outstanding: Simorgh's state 3 calls `0x021C6E98`, which **banishes**.
If the two picks are banished rather than sent to the GY, that is the remaining
deviation and the fix is a send-to-GY primitive (`0x021C6CA8`, hand -> GY).

## ⛔ IN-GAME: proxy swap on the CALLBACK changed nothing (2026-08-14)

Reported: the GY summon is offered; **all hand cards are still selectable (an EARTH
monster among them)**; **the same card can be picked for both halves**; the picks
are banished (expected).

### ❌ I HOOKED THE WRONG FUNCTION
`0x022065F9` is **not a per-candidate filter**. Its only caller-of-record is the
loop at `0x0224C3EC`:

```
for side r4 in 0..1:
    for r5 in 0..0x0A:                       ; a mapped zone index
        r1 = zonetab[...] (via 0x0228DDE4)   ; r0 = side, r2 = 0  <- HARDCODED @0x0224C41A
        blx [0x0229DE14+0xC]                 ; THE CALLBACK
        if r0 != 0: 0x0224C28C(side, zone, 0, 0xB) ; open the picker HERE
```

It receives **(side, zone, 0)** and never sees a candidate — it is a **ZONE-LEVEL
gate** answering "is anything selectable over here?". Overriding its `param`, or
swapping `desc[+0]` around it, therefore cannot filter individual cards. That is
precisely what the duel showed.

### ✅ THE RIGHT HOOK: the cost's `bl 0x0224B9F0`
`0x0224B9F0(side, cid, param, callback)` is the **only** place the cid and param
the selection is armed with are supplied — it stores them at `[0x0229DD94+0x60]`
and `[+0x50]` (measured: `+0x50` has exactly **one** reader, `0x0224C3C6`, and
`+0x60` two). So a donor substitutes there.

**PART L relocated** to the cost's own call site `0x021EC5B8` (a 4-byte BL). For
our cid it arms the selection as if the PROXY were paying — `r1 = 0x1303`,
`r2 = desc[+0x12]` (the pass index) — and replays `movs r2,#0` verbatim for every
other cid, so Dark Simorgh is untouched. The callback literal `0x021EC644` is
**restored to native**.

Stub is 36 B (was 44), so the ov3 dead run drops to **116/126 B** with 10 B spare.
⚠️ r4 is the descriptor at that call site and is also our scratch for the indirect
call, so it is pushed/popped, and `ldrh r2,[r4,#0x12]` runs BEFORE r4 is reloaded.

**Bug 2 should disappear with bug 1**: a card cannot be both LIGHT and DARK, so a
working attribute filter makes picking the same card twice impossible. If it
survives, the fix is to exclude `desc[+0x14]` from the second pass.

`verify()` = **59/59 PASS**. KB **231 facts, 202 PASS, 0 FAIL**. Ledger clean
(94 B ov3 free).

---

# 3DS CROSS-CHECK — the byte-for-byte comparison (2026-08-14)

User: *"Do a byte for byte comparison with the 3DS code instead of guessing."*
Correct call. **The 3DS build ships Lightpulsar Dragon natively**, so it is an
authoritative reference rather than a reconstruction.

## How to line the two builds up (reusable)
- `3ds_extract/partition0/exefs/code_dec.bin`, **VA = 0x00100000 + file_offset**.
- Card identity: `romfs/duel/card/CARD_Indx_E.bin` is **5888 x {u32 name_off,
  u32 desc_off}** into `CARD_Name_E.bin` (a flat run of NUL-terminated UTF-16LE
  strings). Record *i* of `CARD_Prop.bin` (5887 x 8 B) is that same card, and its
  first u16 masked with `0x3FFF` is **the cid — the SAME cid space as the NDS**.
  Verified: Dark Simorgh `0x1E5A`, Plaguespreader `0x1EA9`, Soulkius `0x202C`,
  Chaos Sorcerer `0x16C9` all match the NDS exactly.
  **Lightpulsar Dragon = `0x26E3`**, Darkflare Dragon = `0x26E4`.
  ⚠️ The CARD_Name index is NOT the cid (Lightpulsar is name-index 7500).

## ✅ The criteria registry is THE SAME TABLE in both builds
3DS `main_effect` **`0x686CBC`**, stride `0x0C`, 2100 rows — identical record
shape to the NDS criteria registry `0x022713C4` (`{u16 cid, u16 aux, u32 handler,
u32 word}`), and **the word values are byte-identical**:

| card | NDS `0x022713C4` | 3DS `0x686CBC` |
|---|---|---|
| Chaos Sorcerer `0x16C9` | `0x0223CA11` w `0x01000002` + `0x0223CA11` w `0x02000002` | `0x004B1A90` w `0x01000002` + `0x004B1A90` w `0x02000002` |
| Dark Simorgh `0x1E5A` | `0x0223CA11` w `0x02000002`/`0x06000002`, then `0x0223CB19` w `0x02000002`/`0x06000002` | `0x004B1A90` w `0x02000002`/`0x06000002`, then `0x004ABE08` w `0x02000002`/`0x06000002` |

**=> handler equivalence, independently confirmed:
`0x004B1A90` == `0x0223CA11` (select from GY) and
`0x004ABE08` == `0x0223CB19` (select from HAND).**
So `dispatch.criteria_zone_is_the_handler` is RIGHT, and my mid-session
"the zone is enforced by the callback" claim is definitively dead. Two shipping
builds agree.

## ✅✅ NATIVE LIGHTPULSAR HAS EXACTLY **ONE** CRITERIA ROW

```
3DS main_effect[1568]  cid 0x26E3  aux 0xFFFF  fn 0x004B1B74  word 0x0A550002
```

**`0x0A550002` is precisely the word the 2026-08-05 recon derived for CLAUSE 3**
(race Dragon(1)<<3 | attribute DARK(2) = `0x0A`; op 1 "or higher", level 5 =
`0x55`; low half `0x0002`). It is now **attested in a shipping Konami build**,
which closes recon Open Question 1 ("no row anywhere combines Dragon with an
attribute — verify before trusting it"). Clause 3's word is correct as derived.

**And Lightpulsar has NO criteria rows for clause 1 or clause 2.** Their LIGHT +
DARK costs are not expressed as criteria rows at all in that engine.

## ✅✅ THE ARCHITECTURE: both summon clauses are ONE summon-condition entry

3DS `hand_ss_cond` **`0x6AC2D4`** (262 rows, stride `0x10`,
`{u16 cid, u16 flag, u32 handler, u32 aux, u32 aux2}`):

| card | flag | handler | +8 | +0xC |
|---|---|---|---|---|
| Chaos Sorcerer `0x16C9` | 1 | `0x004B509C` | `0` | `0x004B86D8` |
| **Darkflare `0x26E4`** | 1 | `0x004B509C` | `0` | `0x004B86D8` |
| **Lightpulsar `0x26E3`** | 1 | **`0x004B5AE4`** | **`0x004CBCB4`** | `0x004BB350` |

Darkflare — hand-only, "banish 1 LIGHT and 1 DARK from your GY" — shares Chaos
Sorcerer's handler **exactly**. Lightpulsar, the only one of the three that can
ALSO summon itself from the Graveyard, gets **its own handler plus a non-zero
`+8`**. So in the 3DS the from-hand and from-GY summons are **one mechanism, keyed
on the summon-condition registry** — not a cls2 record borrowing another card's
cost.

**The NDS analogue of `0x6AC2D4` is the summon-procedure registry `0x0228F158`**,
which clause 1 already uses (PART G, handler `0x0226292D`). The 3DS says clause 2
belongs *there*, as a different handler — which is exactly the "two incompatible
architectures on one cid" wall this card hit earlier, now resolved in favour of
architecture A.

## ❌ Also killed by this pass
- **"Simorgh reaches rows 2/3 via the disambiguation switch `0x02243C1C`."** No —
  the switch names only `0D6B 0E79 1522 1686 1757 1895 19D8 1CD6 1F06 208A 21BC
  231C 2449`; Simorgh is absent, and so is our donor. Simorgh is also in neither
  membership list. Its 4-row block must therefore be addressed by a
  param-preserving BST leaf, i.e. purely by which cid-interval it falls in —
  something a donor cannot choose without changing its cid.

## ⏭ What this means for the build
Clause 2 as currently built (cls2 record + Dark Simorgh's cost `0x021EC57D`) is
**the wrong architecture for this engine**, which is why every fix has moved the
symptom rather than removing it. The 3DS-faithful design is a **second
summon-procedure handler for `0x0FB1`** that handles the from-GY direction,
alongside the from-hand one clause 1 already has — not a borrowed cost whose row
addressing the donor's cid can never satisfy.

## ✅ The 3DS handler diff — the blueprint, in four instructions

`0x004B5AE4` (Lightpulsar) vs `0x004B509C` (Chaos Sorcerer *and* Darkflare):

```arm
0x4B5B08  bl   0x3CDD64          ; resolve the summon source
0x4B5B10  bge  0x4B5B2C          ; it's the GRAVEYARD -> the GY path
0x4B5B20  bl   0x4B509C          ; else TAIL-CALL THE SHARED HAND HANDLER, VERBATIM
0x4B5B28  pop  {...}
```

**Lightpulsar is its own handler that branches on zone and reuses the hand one
untouched.** That is the whole architecture, and it ports directly: give the card
its OWN cost, and leave clause 1's native path alone.

# ✅ BUILT — clause 2 gets its own cost (2026-08-14)

**`otn_enhanced/tools/threeds_lookup.py.py`** now exists: one command dumps a card's
rows across every 3DS registry beside the NDS ones
(`... -m otn_enhanced.tools.threeds_lookup "Lightpulsar Dragon"`). The lookup being
hand-rolled each time is a large part of why it kept losing to "I'll just
disassemble the NDS". CLAUDE.md now carries the rule and the recipe.

## What changed
- **PART L is GONE.** Nothing hooks Dark Simorgh's cost, its callback literal, or
  its arming call any more; all three are restored to native. The ov3 dead run
  drops back to **80/126 B**.
- **New `CAVE_LP_C2COST` (ov5, 236 B of a 0x100 reserve)** — our own clone of the
  selection state machine, pointed at by the cls2 record's `+10`. Two deliberate
  differences from `0x021EC57D`, everything else copied instruction for
  instruction because that half demonstrably works:
  1. **arms with `(side, PROXY 0x1303, desc[+0x12], native callback)`** instead of
     `(side, donor, 0, …)`. Simorgh's `movs r2,#0` @`0x021EC5B6` is why both passes
     asked for the same row, and the donor's cid can never address rows 2/3.
  2. **state 3 calls `0x021C6E74` (hand `0x0B` -> GY `0x0E`) instead of
     `0x021C6E98` (hand -> banished `0x0F`)** — so the cost SENDS rather than
     banishes, as printed. The two wrappers are sibling thin calls into the
     relocation core `0x021C6B00` with the same `(side, &cardword)` signature;
     they differ only in the `r3` immediate.
- **ov5 is safe here**, unlike every earlier hook: this stub is reached only via
  our own cls2 record's `+10`, so no native card can jump into it when ov41 evicts
  ov5. Clause 2 stays normal-duel-only; clause 1 remains pure ov3.

`verify()` = **56/56 PASS**; allocation guard clean (89 ov5 slots, 94 B ov3 free);
KB **231 facts, 202 PASS, 0 FAIL**. Stub disassembled and `assert_thumb1_only`
clean; `player+0x124` is precomputed as `0x0229ADB8`.

**Expected in-game:** pass 1 offers only LIGHT monsters in the hand, pass 2 only
DARK ones, and both picks land in the **Graveyard**, not the banished zone.

## ⛔ IN-GAME — still only the DARK card, twice. THE STUB IS EXONERATED.

`rom_lightpulsar.ml2` is mid-selection and settles what our code did. Read
straight out of RAM:

| global | value | meaning |
|---|---|---|
| ov5 `0x0239C1E8` | `70b5041c2b4de86f` | our cost stub is resident |
| cls2 `+10` | `0x0239C1E9` | the engine called OUR cost |
| `[0x0229DD94+0x4C]` | `8` | selection mode, as armed |
| **`[0x0229DD94+0x60]`** | **`0x1303`** | **armed with the PROXY cid — the stub ran** |
| `[0x0229DD94+0x50]` | `0` | param = pass index 0 |
| `[0x0229DE14+0x0C]` | `0x022065F9` | native callback, untouched |
| hand | `0x1D85` REDMD (DARK), `0x2278` Into the Void (Spell), `0x0FB1` (LIGHT) | |

**So the arming is exactly as designed and the fault is downstream.** And the
behaviour CONTRADICTS the static reading: param 0 on a list-A cid should resolve
to the proxy's **row 0 = LIGHT-from-hand**, which matches only `0x0FB1` -- yet the
only selectable card was REDMD, which is **DARK**. Into the Void was correctly
excluded, so something IS filtering; it is simply not the row I believe it is.

Also measured and eliminated: the eligible-card list does NOT come from the
callback (`0x0224C3EC` calls it per (side, zone) with `r2 = 0` hardcoded), and
`[0x0229DD94+0x50]` has exactly one reader, `0x0224C3C6`, which only tests it
`>= 0`. `0x0224B838` calls the enumerate-and-reset variant `0x02243FA8` with
**cid `0xFFFE`** and a packed `(kind<<8)|zone` param, so that third argument is
NOT always a row index -- which is very likely where my model is wrong.

## ⏭ BUILT — the INSTRUMENTED ROM (`rom_lightpulsar_diag.nds`)

Enough hypotheses; measure. `DIAG_C2_INSTRUMENT` makes clause 2's cost, in state 1
just before it arms the picker, ask `0x02243B9C` the one contested question and
park the answers in **`CAVE_LP_DIAG` = `0x0239C368`** (0x40 B, untouched by the
shipped build, so a nonzero magic proves the probe ran):

| offset | contents |
|---|---|
| `+0x00` | magic `0x4C504431` |
| `+0x04` | `0x02243B9C(proxy 0x1303, param 0)` |
| `+0x08` | `0x02243B9C(proxy 0x1303, param 1)` |
| `+0x0C` | `0x02243B9C(donor 0x0FB1, param 0)` |
| `+0x10` | `0x02243B9C(donor 0x0FB1, param 1)` |
| `+0x14` | `desc[+0x12]`, the live pass index |
| `+0x18` | handler of the row `+0x04` resolved to |
| `+0x1C` | word of the row `+0x04` resolved to |

`0x02243B9C` is a pure lookup (binary search + disambiguation, no writes), so the
probe cannot perturb the selection it is measuring. The row read is guarded to
indices `< 0x1000` so a pointer-style return cannot cause a wild access.

Stub: 348 B of a 0x180 reserve, Thumb-1 clean. **Both DIAG flags are `False` on
disk**; the diagnostic ROM is produced by setting `DIAG_C2_INSTRUMENT` at runtime.
Shipped `verify()` = **56/56 PASS**.

**What each outcome means:**
- `+0x04` resolves to the proxy's **DARK** row -> the disambiguation is not the
  `param == 0 ? 0 : 1` clamp I read at `0x02243BFA`; fix the row selection.
- `+0x04` resolves to the **LIGHT** row -> the row is right and the enumerator is
  not using it; the filter lives somewhere else entirely and the next target is
  whatever consumes `[0x0229DD94+0x60]`.
- magic absent -> state 1 never ran, and the whole cost model is wrong.

## ✅✅ INSTRUMENTATION RESULT — the answer, in one savestate (2026-08-14)

`rom_lightpulsar_diag.ml2` (before activation): scratch all zero -> the magic is
meaningful. `rom_lightpulsar_diag.ml3` (during selection):

| slot | value | reading |
|---|---|---|
| `+0x00` | `0x4C504431` | the probe ran |
| `+0x04` | **94** | `0x02243B9C(proxy 0x1303, 0)` -> the proxy's row 0 |
| `+0x08` | **95** | `0x02243B9C(proxy 0x1303, 1)` -> the proxy's row 1 |
| `+0x0C` / `+0x10` | 67 / 68 | the donor's rows 0/1 |
| `+0x14` | 0 | live pass index |
| `+0x18` | **`0x0223CB19`** | HAND-select ✅ |
| `+0x1C` | **`0x01000002`** | **LIGHT** ✅ |

**So row resolution, the param clamp, the proxy and the arming were all correct.**
Outcome 2 of the three: the row is right and the enumerator is not using it.

### THE CAUSE — the enumerator keys off `desc[+0]`, not the armed global
Read straight from the same savestate:

```
[0x0229A9FC+0x50] -> 0x0229A7FC
  b10f 00 0e 00 02 ...   cid 0x0FB1, side 0, zone 0x0E (GY), class 2, pass 0
[0x0229DD94+0x60] = 0x1303      (what we armed)
[0x0229944C+6]   = 1            (candidates -- the one selectable card)
```

The acting descriptor still carried the **DONOR** cid, so the engine enumerated
`0x0FB1`'s row 0 -- handler `0x0223CA11`, a **GY-select** row -- against a HAND
selection. Hence no usable attribute filter, and hence the same card twice.
`[0x0229DD94+0x60]` is written by `0x0224B9F0` but is not what the enumeration
reads.

### THE FIX (built)
Swap the **acting descriptor's** cid, not just the armed global: `strh PROXY,
[desc]` at the top of state 1, and restore `DONOR` at state 3 (before the moves,
so the resolver `0x0220731D` summons the right card) and on the cancel path (so a
cancelled selection cannot leave the descriptor holding a phantom cid). Three
`strh r0,[r4]` sites, verified in the disassembly at `0x0239C212` / `0x0239C268` /
`0x0239C29C`.

Cost stub 252 B of a 0x180 reserve, Thumb-1 clean. `verify()` = **56/56 PASS**;
allocation guard OK (90 ov5 slots, 81 live, 94 B ov3 free); KB **231 facts,
202 PASS, 0 FAIL**. Both DIAG flags `False` on disk.

**This is the first clause-2 change of the session backed by a direct measurement
rather than a reading of the disassembly.**

## ⛔ AND THE SWAP DEADLOCKED THE COST — measured, fixed (2026-08-14)

In-game: only one card selectable (the wrong one), and post-selection **nothing
was sent and Lightpulsar was not summoned**. The savestates name the cause without
ambiguity:

| | ml2 (pre) | ml3 (selecting) | ml4 (post) |
|---|---|---|---|
| `desc[+0]` | **0x1303** | **0x1303** | **0x1303** |
| cost state | 0 | 2 | **0** |
| picks `desc[+0x14]/[+0x16]` | 0/0 | 0/0 | **0/0** |
| candidates | 0 | 1 | 0 |

**`desc[+0]` is the proxy in ALL THREE states, so NEITHER restore ever ran.** It
could not: the activation machine re-enters the cost through
`find_event_handler(desc)`, which binary-searches cls2 by `desc[+0]` — and
`0x1303` owned no record. State 1 armed the picker, swapped the cid, and the cost
was never called again; the state machine fell back to 0 with nothing banked.

*The swap that fixes enumeration also blocks re-entry* — a deadlock of my own
making, and the restores I placed in state 3 / the cancel path are unreachable by
construction.

### FIX — give the proxy its own cls2 record
`cls2[59] = {0x1303, 0x0220731D, 0, **0**, our cost, 0}`, count-neutral over
unclaimed phantom `0x1435`. Now re-entry lands somewhere while the descriptor
carries the proxy cid, and the state-3 / cancel restores become reachable.

`+0C` is **NULL by design**: the condition is only consulted when OFFERING an
effect, which always goes through the donor's own record, and pointing it at
Simorgh's `0x021FEBA9` would make that condition validate a GY slot holding cid
`0x0FB1` against `desc[+0] = 0x1303`. A null `+0C` is a legal, common shape (155
of 697 native cls2 records). `0x1303` is a phantom with no `card_prop`, so it can
never sit in a zone and can never be offered on its own.

Built: `cls2[39]` donor `{0x0220731D, cond 0x021FEBA9, cost 0x0239C1E9}`,
`cls2[59]` proxy `{0x0220731D, cond 0, cost 0x0239C1E9}`; table still 697 rows and
sorted. `verify()` = **59/59 PASS**; ledger OK (43 phantom claims); KB
**231 facts, 202 PASS, 0 FAIL**.

## ⛔ NOTHING SELECTABLE — and the handler was wrong all along (2026-08-14)

The deadlock fix worked mechanically (the cost is re-entered, `desc[+0]` swaps and
restores), but the picker offered nothing. `rom_lightpulsar.ml3`: state 2, mode 8,
armed `0x1303`, `desc[+0] = 0x1303`, zone `0x0E`, and the hand held a LIGHT
(Divine Dragon Ragnarok `0x1859`) that should have matched.

### ❌❌ `0x0223CB19` IS THE **BANISH**-FROM-HAND HANDLER, NOT SEND-FROM-HAND
The two handlers are **not a symmetric pair**. They call different enumerators
with different argument layouts:

```
0x0223CA11 -> 0x0223C4E8    word at [sp],  1<<16 at [sp+4],  r2 = 0, r3 = 0
0x0223CB19 -> 0x0223BFD4    0 at [sp],     word  at [sp+4],  0x10  at [sp+8]
```

So "same word, different handler = different zone"
(`dispatch.criteria_zone_is_the_handler` as I applied it) was never true at the
code level. It came from Dark Simorgh's 2+2 row block, and the 3DS's
`0x004B1A90` / `0x004ABE08` pair appeared to confirm it — but I mapped those onto
the NDS handlers **by position**, which reproduced Simorgh's semantics. And
**Dark Simorgh BANISHES from the hand**; it does not send.

**The only card whose cost SENDS from the hand is Fabled Soulkius `0x202C`**, and
its row is:

```
[910]  fn 0x0223CB65   word 0x0000002E
```

Handler populations: `0x0223CA11` 78 rows, `0x0223CB65` 25, `0x0223CB19` only 11.

### FIX — the proxy rows are SOULKIUS's, not Simorgh's
```
[94]  0x1303  fn 0x0223CB65  word 0x0100002E   LIGHT, send from hand
[95]  0x1303  fn 0x0223CB65  word 0x0200002E   DARK,  send from hand
```
i.e. Soulkius's word with the attribute nibble filled in — **exactly what the
2026-08-13 recon derived** under "CLAUSE 2 ENCODING UNBLOCKED — copy Fabled
Soulkius's row" before the Dark Simorgh lead displaced it. Clause 1's rows are
untouched (`0x0223CA11`, banish from GY).

`verify()` = **59/59 PASS**; guards clean; KB **231 facts, 0 FAIL**.

⚠️ **Lesson for the KB**: Dark Simorgh was the wrong template for clause 2 all
along. Its from-GY summon *banishes* from the hand; Lightpulsar *sends*. Match the
template on the COST VERB, not just on the summon direction.

## ✅✅ THE ENCODING IS NOW ATTESTED, NOT CONSTRUCTED — Chaos Goddess (2026-08-14)

Cross-checked **every** row carrying handler `0x0223CB65` against its ygoprodeck
text (the method that proved `dispatch.criteria_word_level_field`). All 25:

| row | card | word | attr | printed text |
|---|---|---|---|---|
| 273 | Abyss Soldier | `0x03000002` | WATER | "discard 1 **WATER** monster" ✓ |
| 280 | Lady Ninja Yae | `0x06000002` | WIND | "discarding 1 **WIND** monster from your hand" ✓ |
| 631 | Dark Crusader | `0x02000002` | DARK | "send 1 **DARK** monster from your hand to the GY" ✓ |
| 675 | Darklord Zerato | `0x02000002` | DARK | "send 1 **DARK** monster from your hand" ✓ |
| **1159** | **Chaos Goddess `0x2273`** | **`0x01000002`** | **LIGHT** | **"send 1 LIGHT monster from your hand to the GY…"** ✓ |

**Five for five on the attribute nibble, zero disagreements.** Race-only rows
(Herald family `0x88` Fairy, Genesis Dragon `0x08` Dragon, Koalo-Koala `0x58`
Beast) agree too.

**And the LOW HALF is `0x0002`, not Soulkius' `0x002E`** — 20 of the 25 rows use
`0x0002`, including every attribute-filtered one. Soulkius is the outlier
precisely because its cost is "any **2 cards**". Copying its low half was my
error.

### The final rows — clause 2's first pass is a NATIVE ROW, byte for byte
```
proxy [ 94]  0x1303  fn 0x0223CB65  word 0x01000002   == Chaos Goddess row 1159
proxy [ 95]  0x1303  fn 0x0223CB65  word 0x02000002
donor [ 67]  0x0FB1  fn 0x0223CA11  word 0x01000002   (clause 1, unchanged)
donor [ 68]  0x0FB1  fn 0x0223CA11  word 0x02000002
```

**Chaos Goddess `0x2273` is the correct template for this whole card**, not Dark
Simorgh — and it always was: its row 1160 is `fn 0x0223C9D1 word 0x02550002`,
"target 1 Level 5 or higher DARK monster in your GY; Special Summon it", which is
**clause 3 minus the Dragon race nibble** and independently corroborates both the
recon's `0x0A550002` and the 3DS's shipping row for cid `0x26E3`.

`verify()` = **59/59 PASS**; guards clean; KB **231 facts, 202 PASS, 0 FAIL**.

## ⚠️ IN-GAME: the filter WORKS — two gating defects left (2026-08-14)

**Only LIGHTs and DARKs were offered, and the summon completed.** So the proxy
row, the handler, the word, the pass machinery and the send-to-GY all work. The
savestates confirm the pass loop is sound:

| | ml3 | ml4 | ml5 |
|---|---|---|---|
| `desc[+0x12]` pass | 0 | 1 | 2 |
| armed param | 0 | 1 | — |
| picks `+0x14`/`+0x16` | 0 / 0 | **0x0020** / 0 | **0x0020 / 0x0020** |

Two defects, both about GATING rather than selection:

### 1. Activatable with only ONE DARK in hand
The condition was the native `0x021FEBA9`. Its GY arm resolves rows through
`0x0224401C`, which reads `desc[+0]` — still the **DONOR** at condition time,
because the proxy swap happens in the COST. So it was checking the donor's rows
0/1, the **GY-select** pair: it asked about the GRAVEYARD, not the hand.

**FIX:** our own condition (ov5 `CAVE_LP_C2COND`, 60 B) probes the PROXY's hand
rows 0 and 1 with `0x02243FA8(side, 0x1303, param)` — the RESET variant, so each
probe returns the count for that row alone — requires BOTH non-zero, then calls
the native `0x021FEBA9` as a proper function for the zone / in-GY / can-SS checks.
(A call, not a jump: `dispatch.midfunction_tail_needs_prologue_frame`.)

### 2. The same card could be picked for both halves
`ml5` shows both picks as ref `0x0020` and only ONE card moved to the GY.

**FIX:** in the cost's state 2, when banking pass 1's pick, compare it with
`desc[+0x14]`; if equal, refuse it and re-arm the same pass (`state = 1`) instead
of advancing. Cancelling still works (`0x0224BBB0` returns 0 -> the reset path
restores `desc[+0]`), so this cannot hard-lock.

Built: `cls2[39]` donor `{0x0220731D, cond 0x0239C1A9, cost 0x0239C1E9}`,
`cls2[59]` proxy `{…, cond 0, cost 0x0239C1E9}`. Condition 60 B / 0x40 reserve,
cost 268 B / 0x180 reserve, both Thumb-1 clean. `verify()` = **60/60 PASS**;
guards clean; KB **231 facts, 0 FAIL**.

## ⛔⛔ THE CRITERIA ROW DOES NOT FILTER BY ATTRIBUTE ON THIS PATH (2026-08-14)

In-game, with a hand of **Mind Master (DARK)** and **Krebons (DARK)** and NO LIGHT
at all, pass 0 still accepted a pick and pass 1 still offered DARKs
(`ml4`: pass 1, `picks[0]=0x0034`; `ml5`: pass 1, `picks[0]=0x0036`). Earlier the
Spell in hand WAS excluded. So the row filters **monster vs spell** but **ignores
the attribute nibble** on the selection path — even though the row is byte-identical
to Chaos Goddess's, and even though the attribute nibble is provably honoured
elsewhere (177 level-field rows, 5/5 attribute rows agree with their printed text).

**So the attribute must be enforced by us, not by the row.** That also matches the
user's instinct to make the two halves strictly linear.

### FIX — check each pick's attribute with the ENGINE's own accessor
`0x0202ABE8(cid)` returns the attribute: `0x0202A084` resolves the 8-byte
card_prop record, then bits 16:14 of `[rec+4]`. In the cost's state 2 the picked
hand word is already in hand, so the gate is local:

```
cid = word & 0x3FFF ; attr = 0x0202ABE8(cid)
pass 0 -> require attr == 1 (LIGHT) ; pass 1 -> require attr == 2 (DARK)
mismatch -> state = 1, re-arm the SAME pass (do not bank, do not advance)
```
then the existing duplicate check, then bank. Verified in the disassembly at
`0x0239C250..0x0239C286`.

### ✅✅ CORRECTION — `card_prop_codec` IS RIGHT; I was reading it wrong
User: *"Mind master is a Light Psychic, Krebons is a Dark Psychic, you are looking
at the wrong bit"* and *"there is the card_prop codec that properly decodes
card_prop.bin"*. Both correct.

Decoding **the ROM's own** `card_prop.bin` (via `parse_pac` + `DEFAULT_CONSTANTS`,
the ERA2 constants — my earlier snippet had picked up **ERA1** by grabbing the
first module object with a `.layout`):

```
Mind Master 0x1E22 LIGHT  Krebons 0x1E24 DARK   Psychic Commander 0x1E26 EARTH
Ragnarok    0x1859 LIGHT  REDMD   0x1D85 DARK   Chaos Sorcerer    0x16C9 DARK
Sword Arm   0x0FB1 EARTH  Dragunity Arma Leyvaten 0x2356 WIND        -- 8/8 correct
```

So `attribute = BitField(38, 3)` decodes perfectly and the recon's "race/attribute
decode is unreliable" caveat does **not** apply when the ERA2 constants are used.

**And the hand in ml4/ml5 DID hold one of each** — Mind Master is LIGHT, Krebons
is DARK. So the CONDITION was right to allow activation; the only real defect was
that pass 1 did not require DARK.

### ⚠️⚠️ AND THE ACCESSOR I PICKED WAS THE WRONG ONE
attribute = record bits 40:38 = **`[rec+4]` bits 8:6**, and record bit 41
(`[rec+4]` bit 9) is the monster/spell-trap flag. So:

| accessor | `[rec+4]` bits | what it is |
|---|---|---|
| **`0x0202ABC8`** | **9:6** | **flag<<3 \| ATTRIBUTE — the one we need** |
| `0x0202ABE8` | 16:14 | `spell_trap_subtype` — **0 for every monster** |

I had used `0x0202ABE8`, which returns 0 for every monster, so the gate would have
rejected **every** pick. Corrected to `0x0202ABC8`: for a monster it returns the
attribute unchanged (1 LIGHT … 7 DIVINE); for a spell it returns >= 8, which fails
both tests and rejects spells for free.

`verify()` = **60/60 PASS**; guards clean.

## ⛔ NOT OFFERED — the CONDITION was still row-based (2026-08-14)

`ml2`/`ml3`: Lightpulsar in the GY, hand = **Dark Armed Dragon (DARK)** +
**Divine Dragon Ragnarok (LIGHT)** — one of each — and everything resident
(cond `0x0239C1A9`, cost `0x0239C1E9`, GY-action row, both cls2 records). Still no
offer. So the CONDITION returned 0.

It was still probing `0x02243FA8(side, 0x1303, param)` — the criteria rows — which
is precisely the mechanism already shown not to filter by attribute on this path.
The cost had been fixed to check attributes itself; the condition had not.

### FIX — the condition is now self-contained too (`CAVE_LP_C2COND2`, 124 B)
```
hand   = player + 0x124        (0x0229ADB8 for side 0)
count  = player + 0x0C         (0x0229ACA0)
for i in 0..count-1:
    attr = 0x0202ABC8(hand[i] & 0x3FFF)
    if attr == 1: seen |= LIGHT      ; if attr == 2: seen |= DARK
require seen == both, then CALL the native condition 0x021FEBA9
```
No criteria rows anywhere in clause 2's gating any more — both halves use the
engine's own attribute accessor. Index and flags are packed into `r7` (index in
the low byte, flags at bits 8/9) because the assembler has no `sub sp,#imm` and
r4/r5/r6 were already taken; the `arg` parameter is parked with `push {{r1}}`.

Slot: a NEW `CAVE_LP_C2COND2` (0x100 reserve) — the old `CAVE_LP_C2COND` is 0x40
and could not grow in place, since `CAVE_LP_C2COST` sits immediately after it.

`verify()` = **60/60 PASS**; ledger 91 ov5 slots, no overlaps; KB **231 facts,
202 PASS, 0 FAIL**.

## ⛔ OFFERED, but NOTHING SELECTABLE — the handler matrix, settled empirically

`ml3`: the condition now passes (the offer appears) and the cost arms correctly —
mode 8, cid `0x1303`, param 0, pass 0, `desc[+0] = 0x1303` — with a hand of REDMD
(DARK), Ragnarok (LIGHT), Mind Master (LIGHT), Dragon Ravine (Spell). Yet no card
could be picked.

**Three handler/word combinations have now been tried in-game, and the result is
unambiguous:**

| proxy row | in-game |
|---|---|
| `0x0223CB65` + `0x0100002E` (Soulkius verbatim) | picker opens, **nothing selectable** |
| `0x0223CB65` + `0x01000002` (Soulkius handler, common low half) | picker opens, **nothing selectable** |
| **`0x0223CB19` + `0x01000002`** (Simorgh's handler) | **picker opens with the hand's MONSTERS selectable** |

So the "match the template on the cost VERB" rule I derived — which sent me from
Simorgh's handler to Soulkius's — was the wrong lesson. **The handler selects
which list the picker opens; it is not what makes the cost a send or a banish.**
That distinction lives entirely in the COST's state 3: `0x021C6E74` (hand `0x0B` ->
GY `0x0E`) versus Simorgh's `0x021C6E98` (hand -> banished `0x0F`), which is
already what our stub calls.

**FIX:** proxy rows back to `0x0223CB19` + `0x01000002`/`0x02000002` — the
combination that empirically opens the hand — and let clause 2's own code enforce
the semantics. It already does, in both halves, via `0x0202ABC8`:
the CONDITION requires a LIGHT and a DARK in hand before offering, and the COST
requires LIGHT on pass 0, DARK on pass 1, and refuses a repeat of the first pick.

The criteria row is now doing nothing but opening the hand list. Everything the
card actually promises is enforced by our stubs against the engine's own
attribute accessor.

`verify()` = **60/60 PASS**; guards clean.

## ⚠️ "I can select Krebons but nothing happens" — the gate, working silently

`ml4`: the picker offers the hand's monsters, but clicking Krebons did nothing.
**Krebons is DARK and pass 0 demanded LIGHT**, so our gate refused the pick and
re-armed the same pass — correct behaviour, invisible feedback. That build DOES
complete if the LIGHT is chosen first.

But a fixed LIGHT-then-DARK order is not in the printed text ("by sending 1 LIGHT
and 1 DARK monster from your hand"), and the picker cannot be made to hide the
wrong-attribute cards (the row only opens the list; it does not filter — see the
handler matrix above). So the ORDER requirement is removed instead:

```
pass 0: accept ANY LIGHT or DARK monster; remember its attribute at
        CAVE_LP_DIAG+0x20 (0x0239C388, scratch, unused by the shipped build)
pass 1: accept a LIGHT or DARK whose attribute DIFFERS from pass 0's,
        and which is not the same card (the existing ref check)
```

Now either card can be picked first and only the second pick is constrained — and
by then the constraint is forced by the rules rather than by our implementation.
The residual UX wart is unavoidable without control of the picker's list: choosing
a second card of the same attribute silently re-asks.

Verified in the disassembly at `0x0239C250..0x0239C294`.
`verify()` = **60/60 PASS**; guards clean.

## ✅✅ THE ROW **DOES** FILTER BY ATTRIBUTE — my earlier conclusion was wrong

The order-free build produced "I cannot select REDMD or anything", and the
savestates finally explain the whole picture:

| state | pass | param | `[0x0229944C+6]` | hand |
|---|---|---|---|---|
| `ml4` (fresh) | 0 | 0 | **1** | one LIGHT (Ragnarok), one DARK (Krebons), Reload, Horus (FIRE) |
| `ml3` | 1 | 1 | **1** | one LIGHT (Ragnarok), one DARK (REDMD), Mallet, White Night (WATER) |

Pass 0 with param 0 yields exactly the number of **LIGHT** monsters in hand; pass
1 with param 1 exactly the number of **DARK**. **The criteria row filters by
attribute per pass, correctly.**

⚠️ **And this explains "I can select X but nothing happens": the picker DRAWS the
whole hand, so a non-candidate looks clickable and is silently ignored by the
ENGINE.** That was never our gate. My "the row ignores the attribute nibble"
conclusion came from the ml4/ml5 hand I had mis-read (Mind Master is LIGHT, not
DARK) — the user corrected it, and with the right attributes every observation
lines up.

**FIX:** drop the order-free logic and the `CAVE_LP_DIAG+0x20` scratch; our
per-pick check goes back to matching the row exactly — **LIGHT on pass 0, DARK on
pass 1** — so our gate agrees with the engine instead of fighting it. The
order-free version let a DARK through pass 0 and left pass 1 with only the
already-taken card, which is exactly what `ml3` shows (`picks[0]=0x002C`,
scratch=2=DARK, pass 1 offering only the DARK it already had).

Net: the engine filters, our gate double-checks the same rule, and the duplicate
check remains as a belt-and-braces guard.
⚠️ Consequence for the player: **the LIGHT must be sent first.** A minor deviation
from the printed text's ordering, forced by the engine's per-pass row.

`verify()` = **60/60 PASS**; guards clean.

# ✅✅✅ CLAUSE 2 WORKS — IN-GAME CONFIRMED (2026-08-14)

User-reported: *"selecting the light and then the dark does work and summons the
card properly."* The full loop runs — the effect is offered from the Graveyard
only when a LIGHT and a DARK are in hand, the LIGHT is sent, then the DARK, both
to the **Graveyard**, and Lightpulsar Special Summons itself.

## The final architecture (what actually made it work)

| part | what it does |
|---|---|
| **K** | row in the GY-action registry `0x0228DDF8` (phantom `0x0E3E`) — without it the effect is never offered at all |
| **I** | cls2 record on the donor: `+04 0x0220731D`, `+0C` our condition, `+10` our cost |
| **I2** | cls2 record on the PROXY `0x1303` (phantom `0x1435` dropped), `+0C` NULL — exists so the cost can be RE-ENTERED while `desc[+0]` carries the proxy |
| **H** | proxy's two criteria rows rewritten in place: `fn 0x0223CB19`, words `0x01000002` / `0x02000002` — the row the picker filters on |
| **J** | condition (ov5 `CAVE_LP_C2COND2`, 124 B): walks the hand via `0x0202ABC8`, requires a LIGHT **and** a DARK, then defers to native `0x021FEBA9` |
| **L** | cost (ov5 `CAVE_LP_C2COST`, ~270 B): 4-state clone of Simorgh's machine that arms with the **proxy cid + real pass index**, swaps `desc[+0]` for the selection, re-checks each pick's attribute, refuses a repeat, and **sends to the GY** via `0x021C6E74` |

**The two insights that unlocked it**, both from savestates rather than reading:
1. the enumerator keys off **`desc[+0]`**, not the armed global — hence the proxy swap;
2. swapping `desc[+0]` breaks re-entry unless the proxy also owns a cls2 record.

## ⚠️ KNOWN REMAINING DEFECT — a second copy of the card cannot pay for itself

With a hand of REDMD (DARK), Emergency Teleport (Spell), Dark Armed Dragon (DARK)
and **`0x0FB1` (LIGHT — a second copy of Lightpulsar)**, pass 0 reported
`candidates = 1` (correctly counting the LIGHT) but that card could not be picked.

**This is a real bug, not intended behaviour**: a different copy in the hand is a
different card and the rules allow it as the cost. The exclusion is NOT ours —
our gate accepts it (`0x0202ABC8(0x0FB1)` = 1 = LIGHT, pass 0 wants LIGHT) and the
duplicate check only compares refs on pass 1. It is also not `desc[+0]`-based,
because `desc[+0]` is the PROXY `0x1303` throughout the selection.

### ✅ CAUSE FOUND — the row's LOW HALF over-filters by monster sub-kind
A later hand made it unambiguous: **two** LIGHT monsters in hand,

```
[0] 0x1859 Divine Dragon Ragnarok  LIGHT  *Normal* Monster
[1] 0x1E22 Mind Master             LIGHT  *Tuner*  Monster
[3] 0x1D85 REDMD                   DARK   Effect  Monster
```
and `[0x0229944C+6] == 1` — only ONE of the two LIGHTs was a candidate. So the
word `0x01000002` filters on more than the attribute: its **low half** (the
undecoded selection/sub-kind field; `0x0002` is the commonest of ten values)
discriminates Normal / Tuner / Effect. The same over-filtering is what excluded a
second copy of `0x0FB1` from paying its own cost.

**FIX:** the proxy's rows become **`word 0x00000002`** — attribute nibble 0, i.e.
**any monster in the hand** — on both passes. Clause 2 already enforces everything
itself (condition: a LIGHT *and* a DARK present; cost: LIGHT on pass 0, DARK on
pass 1, no repeat; all via `0x0202ABC8`), so the row's only remaining job is to
open the widest correct list. This shape is attested natively: Ape Magician
`0x218B` is `{fn 0x0223CB65, word 0x00000002}` = "send 1 monster from your hand to
the GY".

This should fix BOTH reported defects at once — every LIGHT in hand becomes
selectable, and a second copy of the card can pay for itself.

## ✅✅✅ DEEP STATIC PASS — THE CRITERIA WORD IS FULLY DECODED, AND THE WIDENING WAS WRONG

User: *"I am not comfortable with this behaving like this ... it would be confusing
for users if the selection process is not behaving in a way that is intuitive"* —
correct, and the fix is not a trade-off. Read straight off the matcher
**`0x0223BA24(side, zone, &cardword, WORD)`**:

```
bits 31:27  RACE       vs 0x0202ABB8(cid)    [0x021B1EE8 when zone == 0x0E]
bits 26:24  ATTRIBUTE  vs 0x0202ABC8(cid)    [0x021B1F7C when zone == 0x0E]
bits 21:18  LEVEL      vs 0x0202ABD8(cid);  bit 22 => ">=", bit 23 => "<=", else "=="
```

*** AND THE LOW 16 BITS ARE A **BITMASK OF PREDICATES**, NOT AN ENUM *** — which is
why the ten observed low halves never decoded as an enumeration, and why `0x0002`
is the commonest (it is the single "is a real card" bit):

| bit | test |
|---|---|
| 1 `0x0002` | `0x02029E60(cid) != 0` — the basic real-card test |
| 10 `0x0400` | zone 0x0B ? `0x021B2094` : `0x02022FF0` |
| **13 `0x2000`** | **`0x0202AC48(cid) <= 0x5DC` — ATK <= 1500** |
| 14 `0x4000` | `0x02023188(cid) == 1` |
| 15 `0x8000` | `0x02023110(cid) == 1` |
| 16 `0x10000` | `0x021B1E68(side, cid) != 0` |

Cross-check: Giant Rat / UFO Turtle / Shining Angel / Mother Grizzly / Flying
Kamakiri #1 / Mystic Tomato all carry low half `0x2002` and all read "Special
Summon 1 \<ATTRIBUTE\> monster with **1500 or less ATK**" — attribute nibble plus
bit 13, exactly. Filed as `dispatch.criteria_word_fully_decoded` (VERIFIED).

### CONSEQUENCE — the widening was a workaround for a limit that does not exist
`0x01000002` imposes **no** constraint on race, level, Normal/Tuner/Effect kind,
or on the acting card's own cid. The only other gate is
`0x021B945C(side, cid, 0)` (reached because our handler sets flag `0x10`), which
with flags 0 is a two-cid blocklist `{0x12EA, 0x1D16}` and otherwise falls through
to `movs r0,#1`.

So **nothing in the engine excludes a Tuner, a Normal Monster, or a second copy of
the donor**, and `word 0x00000002` ("any monster") was the wrong answer: it made
every monster clickable and pushed the filtering into our silent re-ask — worse UX
for no correctness gain.

**Rows restored to `0x01000002` / `0x02000002`.** The engine now offers ONLY valid
cards per pass, which is the intuitive behaviour; our own attribute gate stays as
a harmless backstop.

⚠️ **STILL UNEXPLAINED BY THE CODE:** the report that only one of two LIGHTs
(Ragnarok `0x1859` Normal, Mind Master `0x1E22` Tuner) was selectable. Nothing in
the matcher accounts for it. Most likely `[0x0229944C+6]` is a RUNNING counter
rather than a candidate count — which would also invalidate several "cands=N"
readings in this file — or the prompt observed was the DARK pass. **Decisive
check: on the FIRST prompt, are both Ragnarok and Mind Master selectable?** If not,
instrument the matcher rather than guessing.

`verify()` = **60/60 PASS**; KB **232 facts, 203 PASS, 0 FAIL**.

# ✅ ANSWERED — HOW DARK SIMORGH REACHES ROWS 2/3 (2026-08-14)

It is **a hand-written arm in the compiled disambiguation switch** inside
`0x02243B9C`, at **`0x02243DEA`**, and nothing else — not a membership list
(`0x1E5A` is in neither) and not the param provider `0x02234E78` (it is in none of
its lists):

```
param >= 0x10000000   (caller passed an attribute FLAG word)
    r4 = ((param >> 28) == 6 /*WIND*/) ? 1 : 0        -> rows 0/1, its GY pair
param <  0x10000000   (what its own cost passes: `movs r2,#0` @0x021EC5B6)
    r0 = [0x0229A9FC+0x50]                 ; the ACTING DESCRIPTOR
    r1 = (r0 && desc[+0x12] != 0) ? 1 : 0  ; THE PASS INDEX
    r4 = r1 + 2                            ; ROWS 2 AND 3
```

So the `+2` is hardcoded in Simorgh's own arm and the pass index is read out of
the descriptor — which is exactly why its cost can pass a constant 0 on both
passes and still alternate rows. A donor gets one of two clamps instead: list A =>
`param == 0 ? 0 : 1` (`0x02243BFA`), neither list => forced `movs r4,#0`
(`0x02243EEC`). Filed as `dispatch.simorgh_row_offset_is_a_bespoke_switch_arm`.

## ✅✅✅ SHIPPED — `SIMORGH_STYLE = True` IS NOW THE DEFAULT (in-game confirmed)

User, 2026-08-14: *"that simorgh version works perfectly! Ship that"*. The variant
below is now the shipped design; `SIMORGH_STYLE` defaults to **True** and
`apply_all_patches` builds it. `verify()` branches on the flag and is **62/62 PASS**.

**Released by shipping it:** the proxy's cls2 record and its phantom `0x1435`
(the cost no longer swaps `desc[+0]`, so re-entry finds the DONOR's own record).
`0x1435` is free for the next patch. `0x1303` is still consumed — its two rows are
dropped to keep the donor's rel-2/3 insert count-neutral.

⚠️ **THE ONE COST OF SHIPPING THIS:** the hook is on `0x02243B9C`, the SHARED row
resolver that every card selecting anything passes through, and its stub is in
ov5. In a PUZZLE (ov41 evicts ov5) that would freeze **any** such card, not just
ours — a strictly wider blast radius than before, when only this card's clause 2
was duel-only. Accepted by explicit user decision. **To make it puzzle-safe the
stub must move to ov3 dead code (~60 B); the largest contiguous free run is
currently 46 B, so it needs either a shrink or a newly proven-dead block.**

## THE VARIANT, AS BUILT (`SIMORGH_STYLE`)

User decision 2026-08-14: build the Simorgh-style approach as a **separate ROM**,
ov5 accepted. `CAVE_LP_ROWHOOK` (68 B) supplies our donor the arm the switch has
for `0x1E5A`, hooked over `ldr r1,=0x0227134C ; adds r0,r5,#0` at `0x02243BEC`:

```
desc = [0x0229A9FC+0x50]
if desc && desc[+0] == 0x0FB1 && desc[+3] == 0x0E:   r4 = 2 + (desc[+0x12] != 0)
                                                     -> jump to the tail 0x02243EEE
else:  replay the two displaced instructions, resume at 0x02243BF0
```

The discriminator is the descriptor's own cid+zone, which is why this variant must
NOT swap `desc[+0]`. Clause 1 is unaffected: it runs while the card is in the
hand, so the zone is never `0x0E`.

**What it removes:** the proxy cid `0x1303`, the proxy's cls2 record, and the
`desc[+0]` swap with its restores (the source of the re-entry deadlock). The cost
now arms exactly like Simorgh's — real cid, `param = 0`.

Built layout, confirmed in the ROM:

| | main `rom_lightpulsar.nds` | variant `rom_lightpulsar_simorgh.nds` |
|---|---|---|
| donor `0x0FB1` rows | 2 (GY pair) | **4** — GY at rel 0/1, HAND at rel 2/3 (Simorgh's exact layout) |
| proxy `0x1303` rows | 2 | 0 |
| cls2 records | donor[39] + proxy[59] | donor[39] only |
| `0x02243BEC` | native `8449281c` | `58f15cfc` (BL to ov5) |

⚠️⚠️ **`0x02243B9C` is the SHARED row resolver** — every card that selects
anything passes through it, so an ov5 target there freezes all of them in a
puzzle. Duel-only, by explicit user decision, and it never enters the main build
(`SIMORGH_STYLE` is `False` on disk and `apply_all_patches` uses the default).

## CHAIN REBUILT + REGRESSION SWEEP — CLEAN
`ALL 32 PATCHES APPLIED -> rom_all_patches.nds`. `patch_lightpulsar.verify()`
against the **combined** ROM = **60/60 PASS**. Sweep of every module's `verify()`:
**22 PASS, 0 FAIL**, 12 expose no `verify()`, and the same 4 known non-applied
modules error as in the historical baseline (`patch_wonder_wand` commented out,
`patch_bulk_ydcs` / `patch_zeta_reticulant` have no PatchStep,
`patch_unlock_all_packs` has a zero-arg `verify()`).
⚠️ The sweep must catch **BaseException**, not `Exception` — `patch_zeta_reticulant`
raises `SystemExit` on import and silently kills a sweep that only catches
`Exception`.

Ledger: 92 ov5 slots, 43 phantom claims, 94 B ov3 free, no overlaps.
KB: **233 facts, 204 PASS, 0 FAIL.**

⚠️ Known remaining looseness: the CONDITION still probes via the criteria rows, so
the effect may be **offered** when it cannot actually be paid (e.g. no LIGHT in
hand). The cost can no longer be completed wrongly — the worst case is an offer
the player must cancel. Tightening the condition means walking the hand and
calling `0x0202ABE8` per card, the same way the cost now does; it needs a bigger
cave slot than the 0x40 the condition currently has.

`verify()` = **60/60 PASS**; guards clean; cost stub 300 B of 0x180... (see build).


---

# Session 2026-08-17 — CLAUSE 3 (scope: build it)

Clauses 1 and 2 are shipped and in-game confirmed; **neither may regress**.
Everything below was measured THIS session against the clean image, the 3DS
build and existing savestates. Anything inherited from the sections above is
marked UNVERIFIED until re-confirmed here.

Card text re-read from `scratch/ygoprodeck_cache.json` id 99365553 — unchanged.
Clause 3: *"When this card is sent from the field to the GY: You can target 1
Level 5 or higher DARK Dragon monster in your GY; Special Summon that target."*

KB health at session start:
`verify_knowledge --savestate data/over_the_nexus/working/sealancer_recon.ml3`
= **233 facts, 204 PASS, 0 FAIL, 29 UNVERIFIED.** Allocation guard clean
(92 ov5 slots / 83 live, 42 phantom claims, 94 B ov3 free).

## Confirmed (this session)

### 3DS FIRST — the criteria row, settled before any NDS disassembly
`... -m otn_enhanced.tools.threeds_lookup "Lightpulsar Dragon"`:

```
main_effect [1568]  FFFF26E3  004B1B74  0A550002        <- the whole of clause 3
summon_cond [ 192]  000126E3  004B5AE4 004CBCB4 004BB350
```

**Handler equivalence `0x004B1B74` == NDS `0x0223C9D1`, proven on FOUR
independent cards** (a much stronger check than the positional mapping that
misled the 2026-08-14 session):

| card | 3DS main_effect | NDS criteria registry |
|---|---|---|
| Chaos Goddess `0x2273` | `004B1B74` w `02560002` | `0x0223C9D1` w `0x02550002` |
| Lord Poison `0x156D` | `004B1B74` w `68010022` | `0x0223C9D1` w `0x68010022` |
| Call of the Haunted `0x137D` | `004B1B74` w `00010002` | `0x0223C9D1` w `0x00010002` |
| Decoy Dragon `0x1C4F` | `004B1B74` w `085D0002` | `0x0223C9D1` w `0x085D0002` |

So clause 3's row is `{0x0FB1, 0xFFFF, 0x0223C9D1, 0x0A550002}` — **attested in a
shipping Konami build, not constructed.** Recon Open Question 1 stays closed.

### THE TRIGGER — the leave dispatcher has THREE registration paths, and they are semantically distinct

Disassembled `0x021C80BC..0x021C8114` this session:

```
0x021C80BC  if [sp+0x44] && [sp+0x90] && [sp+0x144]        ; battle && DESTROYED && to-GY
              && bsearch(list106 0x0226E990, 0x6A, cid):  [sp+0x18] = 1
0x021C80E0  if [sp+0x2C] && [sp+0x144]                     ; left the FIELD && to-GY
              && bsearch(list30  0x0226E904, 0x1E, cid):  [sp+0x18] = 1
0x021C80FE  if [sp+0x18] == 0:                             ; ONLY THEN
              bsearch(mask table 0x0226EC1C, 0x98, stride 4, cid)
```

**Membership proves the semantics outright** (dumped and joined to
`scratch/cid_to_name.json`):

- **list30 (30 entries) = "sent from the FIELD to the GY"** — Botanical Girl
  `0x1ED4`, Sangan `0x0FD6`, Witch of the Black Forest `0x11E4`, Goblin Zombie,
  Dupe Frog, Naturia Cliff, Naturia Eggplant, Gusto Gulldo, Gem-Knight
  Aquamarine, Junk Gardna, Masked Beast Des Gardius, Emissary of the Afterlife,
  Deepsea Macrotrema, E-Hero The Shining — **plus the equip spells** (Axe of
  Despair, Black Pendant, Horn of Light, Horn of the Unicorn, Malevolent
  Nuzzler, Magic Formula, Crystal Release, Cursed Armaments), whose text is
  literally "When this card is sent from the field to the Graveyard...".
  Every single member is worded that way. **ALL 30 ARE REAL CARDS — no phantom.**
- **list106 = "destroyed by battle and sent to the GY"** — Colossal Fighter
  `0x1E12`, Lord Poison `0x156D`, Sun Dragon Inti `0x21CD`.
- **mask table = "sent to the Graveyard"** — the Dandylion `0x19FE` family
  (15 real cards, all so worded), and it is consulted ONLY when neither list
  armed `[sp+0x18]`. **22 phantom rows**, of which 21 unclaimed (Eclipse Wyvern
  owns `0x16F5`).

⚠️ **CORRECTION to the continuation prompt.** It offered only two candidates —
the sent-to-GY cid switch `0x021D1392` and "the leave-mask table plus a cls2
record ... the field-only path". The cid switch is the **any-location widener**
(Eclipse Wyvern needed it precisely to fire from a hand discard and a deck mill)
and is therefore WRONG for clause 3. The mask table is field-only not because of
its mask value but because **the whole dispatcher is field-only**
(`event.leave_mask_is_field_only`, VERIFIED: read at exactly one site, never
reached on a discard). list30 is the semantically exact register but **cannot be
used** — no phantom, and it cannot grow (the attached-destroy list
`leave.attached_card_destroy_list` abuts it at `0x0226E940`).

**=> Clause 3's trigger = a mask row `{0x0FB1, 0x0800}` and NO cid-switch hook.**
That is Eclipse Wyvern's shipped PART A minus its PART E, which is exactly the
configuration EW measured as field-only before PART E existed.

### THE EVENT CODE — measured from savestates, not assumed

Parsed the acting descriptor `[0x0229A9FC+0x50]` out of every existing savestate
(RAM0 auto-detected = 0x24):

| savestate | descriptor | what it is |
|---|---|---|
| `rom_eclipse_wyvern.ml2` | cid `0x1859` zone `0x0E` **event `0x1E`** cls 2 | a sent-to-GY trigger |
| `rom_all_patches.ml3` | cid `0x1859` zone `0x0E` **event `0x1E`** cls 2 | same, in the chain build |
| `rom_eclipse_wyvern.ml3` | cid `0x1859` zone `0x0F` event `0x20` cls 2 | EW clause 2 (banished) — matches `event.gy_to_banished_mover` |
| `rom_lightpulsar.ml3/4/5` | cid `0x1303` zone `0x0E` **event `0x00`** cls 2 | Lightpulsar CLAUSE 2 |

So **`desc[+4]` separates clause 2 (`0x00`) from clause 3 (`0x1E`)**, and the
zone does NOT (both `0x0E`). Independently, `0x021ECC28` caps clause 2's
off-field event code at `<= 6`, so the two ranges are provably disjoint.

### THE ACTION — Colossal Fighter `0x1E12` is the record template

Its OTN effect is clause 3's shape verbatim. `cls2[357]`:

```
+04 0x02207191   +08 0   +0C 0x021F03B5   +10 0x021E51E5   +14 0x02235605
```

- **`0x02207191` is the cls2 GY-revive resolver** — ~40 native cls2 records use
  it with `+14 = 0x02235605` (Lord Poison, Sun Dragon Inti, Moon Dragon Quilla,
  Lightning Tricorn, Dragunity Arma Leyvaten, the /Assault Mode family...).
  ⚠️ **CORRECTION to the continuation prompt**, which named `0x02207529`: that
  one is the **cls0 SPELL** revive resolver (Premature Burial, Call of the
  Haunted, Monster Reborn family) and has no cls2 member.
- Its per-cid switch only picks modes (`r4=1, r5=2` defaults set at
  `0x02207198`/`0x0220719A`); **the unnamed-cid fall-through is `0x022072DA` =
  `0x02204730(desc, r4, r5)`**, the generic body. So the donor's records-free cid
  works, by the same argument already proven for `0x0220731D` and `0x02207529`.
- `+0C 0x021F03B5` = `0x021F0384(side)` (may you SS?) then
  `0x02234E78(desc)` -> param then `0x02243FE0(side, desc[+0], param)` -> return 1
  iff a legal target exists. Cid-generic.
- `+10 0x021E51E5` is the **"You can" tag** — the same slot4 value Botanical
  Girl carries (`event.optional_trigger_is_record_shape`).
- `+14 0x02235605` is the off-field picker; it calls `0x02234E78` for param
  (`0x02235610`) then `0x02243FA8(side, desc[+0], param)` (`0x0223562E`).

Handler note: Colossal Fighter's own criteria handler is `0x0223D6E1`
(3DS `0x004A713C`), a *different* revive handler. We take **Lightpulsar's own**
`0x0223C9D1`, as the 3DS ships it — Lord Poison is the cls2 precedent for that
handler.

### "SLOT ABSENT" == RETURN 1

`0x0224AE5E` (slot4) and `0x0224AE84` (slot5) both fall to `movs r0,#1 ; pop`
when the record's `+0x10` / `+0x14` is zero. So a `+14` dispatcher can reproduce
clause 2's current `+14 == 0` behaviour exactly by returning 1 — no need to
emulate the target-declaration sub-machine.

### ONE RECORD, FOUR BRANCHING SLOTS

`dispatch.find_event_handler_second_record` (VERIFIED): the `+1` record offset
applies **only** when `desc[+5] == 1` (cls1). Relocation events are always
class 2 (`event.register_prim_descriptor_layout`), so a second cls2 record on the
donor is unreachable — the Warwolf E1/E2 shadow. Clause 3 therefore shares
`cls2[39]` and every slot branches on `desc[+4]`.

### THE ROW HOOK CAN GROW IN PLACE

`_stub_row_hook` is **68 B in a 0x60 (96 B) reserve = 28 B headroom**, and
`CAVE_LP_ROWHOOK 0x0239C4A8` is the LAST slot before `CAVE_FREE 0x0239C508`, so
its reserve can be bumped with no re-homing. ⚠️ CORRECTION to the continuation
prompt's "it will need a larger slot, so re-home it rather than growing it".
Current stub headroom elsewhere: `CAVE_LP_C2COND2` 124/0x100 (132 B free),
`CAVE_LP_C2COST` 296/0x180 (88 B free).

### THE DONOR'S CURRENT ROWS (read from the built `rom_lightpulsar.nds`)

```
[67] 0xFFFF 0x0223CA11 0x01000002   clause 1 LIGHT, banish from GY   (rel 0)
[68] 0xFFFF 0x0223CA11 0x02000002   clause 1 DARK                    (rel 1)
[69] 0xFFFF 0x0223CB19 0x01000002   clause 2 LIGHT, from hand        (rel 2)
[70] 0xFFFF 0x0223CB19 0x02000002   clause 2 DARK                    (rel 3)
```

Clause 3's row goes at **index 71 = rel 4**. 96 phantom criteria rows remain;
nearest above the donor is `[76] cid 0x1138` (unclaimed) — the smallest memmove.

## Ruled Out (this session)

- **"Use the sent-to-GY cid switch `0x021D1392`."** It is the any-location path;
  clause 3 says "from the field". Using it would make the effect fire on a hand
  discard and a deck mill.
- **"Register in list30."** Semantically perfect, structurally impossible — 30/30
  entries are real cards and the array cannot grow.
- **"A second cls2 record, discriminated by the `[desc+4]` lists at
  `0x02275B60`/`0x02275B86`."** The older note in this file describing those
  lists is superseded by the VERIFIED
  `dispatch.find_event_handler_second_record`: the offset is 1 only for cls1.
- **"`0x02207529` is the resolver."** cls0/spell only; see above.

## Open Questions

1. **Is the acting descriptor the row hook reads (`[0x0229A9FC+0x50]`) the same
   descriptor the condition/picker are handed in `r0` during clause 3?** The row
   hook keys off the global. PART Q instruments both.
2. **Is our trigger's `desc[+4]` really `0x1E`?** Measured for Eclipse Wyvern,
   inherited for us. PART Q measures it directly.
3. **A 5-row criteria block is unattested.** The leftmost walk-back is
   block-size agnostic and the tail bounds `leftmost + r4 < 0x56C`, so it should
   be safe — but no native cid owns more than 4.

## Next Experiment

ONE in-game test (user decision 2026-08-17): the full clause 3, with the `+0C`
stub always dumping the descriptor and the resolved row index into the unused
`CAVE_LP_DIAG` scratch. If it works, done; if not, the savestate already answers
Open Questions 1-3 without spending a second duel.


## ⛔ IN-GAME TEST 1 (clause 3) — NOT ACTIVATED (2026-08-17)

User-reported on `rom_lightpulsar.nds`; savestates `.ml2` (before Lightpulsar is
destroyed on the field) and `.ml3` (after). Lightpulsar reached the Graveyard and
nothing was offered.

### ✅ The setup and the build were both correct — this is a real negative
Read out of the savestates (RAM0 auto-detected = 0x24):

- **`.ml3` GY (player+0x55C, count player+0x14 = 7):** Upstart Goblin, Dragunity
  Arma Leyvaten `0x2356`, `0x0FB1`, REDMD `0x1D85`, Krebons, **`0x0FB1` (a SECOND
  copy — the destroyed one)**, Dark Hole `0x10F6`. So the card really did go from
  the field to the GY, and the live acting descriptor in `.ml3` is
  `cid 0x10F6 zone 0x07 cls 0` = **Dark Hole resolving**, i.e. destruction by a
  card effect.
- A legal clause-3 target was present the whole time: **Dragunity Arma Leyvaten
  `0x2356` is a Level 8 WIND Dragon** — wrong attribute, so actually NOT legal;
  REDMD `0x1D85` (Red-Eyes Darkness Metal Dragon) IS Level 10 DARK Dragon and was
  in the GY in both states. ✅ a legal target existed.

### ✅ PART Q EARNED ITS KEEP — the probe ran
`CAVE_LP_DIAG` held magic `0x4C503343` in BOTH states, so our `+0C` stub is being
called. Every recorded call:

| slot | `.ml2` | `.ml3` |
|---|---|---|
| desc[+0] cid | `0x0FB1` | `0x0FB1` |
| side / zone / **EVENT** / cls | 0 / `0x0E` / **`0x00`** / 2 | 0 / `0x0E` / **`0x00`** / 2 |
| GLOBAL acting desc | `0x027E3368` | `0x027E3280` |
| desc handed in r0 | `0x027E3368` | `0x027E3280` |
| resolved criteria row | **69** | **69** |

Three things fall out of this:

1. **✅ OPEN QUESTION 1 ANSWERED: the two descriptors are the SAME pointer.**
   `[0x0229A9FC+0x50]` == the `r0` the slot was handed, in both states. So the row
   hook keying off the global is sound.
2. **✅ The clause-2 path is healthy** — row 69 is rel 2, the hand LIGHT row, which
   is exactly what the clause-2 arm asks for.
3. **⛔ NO event-`0x1E` call was ever captured.** Every call carries event `0x00`,
   i.e. a clause-2 GY-action poll.

⚠️ **INSTRUMENTATION FLAW (mine):** `CAVE_LP_DIAG` is a single slot that every call
overwrites, and clause 2's GY-action poll runs constantly. So "no `0x1E` recorded"
is strong evidence but **not proof** — a `0x1E` call could have been overwritten by
a later poll. The next build must LATCH the first non-zero event code in a slot
nothing else touches, plus a per-event-code counter.

### ⛔⛔ ROOT CAUSE — PART M's premise was wrong. A LEAVE-MASK ROW ONLY SETS A FLAG.

Disassembled `0x021C8110..0x021C81F0` this session. After the mask lookup succeeds,
the mask value is used as a **REQUIREMENT BITMASK**: each set bit adds a
precondition, and failing any of them clears `r5`:

```
bit 2  (0x0004)  requires [sp+0x2C]    (left the FIELD)
bit 7  (0x0080)  requires [sp+0x44]    (battle)
bit 10 (0x0400)  requires [sp+0x90]    (DESTROYED)
bit 11 (0x0800)  requires [sp+0x144]   (destination is the GY)   <- ours
...
0x021C81EA  cmp r5,#0 ; beq -> skip ; movs r0,#1 ; str r0,[sp,#0x18]
```

So mask `0x0800` really does mean "sent to the Graveyard" — but **all it does is set
`[sp+0x18]`**. And `[sp+0x18]` is then read at **12 sites, every one of them INSIDE
the per-cid switch that begins at `0x021C8216`** (`leave.hook`): 0x021C87D8,
0x021C8818, 0x021C883E, 0x021C89B2, 0x021C8AA6, 0x021C8C2C, 0x021C8C5E, 0x021C8D0C,
0x021C8DDC, 0x021C8ED0, 0x021C9000. The region posts an event at only four places
(register-prim `0x021D3168` from 0x021C93B8 / 0x021C94FC / 0x021C979A, and the cls1
poster `0x021D3230` from 0x021C7E80) — all deep inside specific per-cid arms.

**=> A leave-mask row is a PRECONDITION for a card that already has an arm in the
`0x021C8216` cid switch. It cannot, by itself, make an event happen. Our donor has
no arm, so PART M is inert.**

That also corrects how I read Eclipse Wyvern. `event.leave_mask_is_field_only`
(VERIFIED) proves the mask table is only *read* on a field leave — true, and still
true — but I took that to mean a mask row alone *posts* a field-only sent-to-GY
event. It does not. EW's trigger actually comes from its **PART E**, the hook on the
relocation applier's cid switch `0x021D1392`, which is the ANY-LOCATION path; and
the "field-only, before PART E" line in EW's own STATUS block refers to the earlier
**list30**-based build, not to a mask-only one. No native card has a 0x0800 mask row
without also being in the 0x021D1392 switch — the two sets are identical, which is
exactly the shape of "both are required".

### The two remaining routes for clause 3's trigger

| route | mechanism | scope | cost |
|---|---|---|---|
| **A** | hook the relocation-applier cid switch `0x021D1392` at the terminal node of `0x0FB1`'s interval — Eclipse Wyvern's PART E, **in-game confirmed** | **ANY location**: field, hand discard AND deck mill. Wider than printed. | ~24 B ov3 dead code + a search simulation to prove the donor reaches the node |
| **B** | register the donor on the shared any-leave trampoline at `0x021C8216` (`tg_table.arm_tg_leave_trigger`, already installed in the chain by the T.G./Quasar patches, cid list has room) and post the class-2 event ourselves from a new arm | **exactly "sent from the field to the GY"** — `[sp+0x2C]` and `[sp+0x144]` are both live at that hook | a new arm + an event post (`0x021D3168`, packed word `cid \| 0x0E<<16 \| 2<<21 \| 0x1E<<25 \| side<<31`) |

⚠️ Route B is NOT "run the effect in the stub" — Eclipse Wyvern already ruled that
out, and correctly: the leave path is synchronous and cannot yield, so a
self-contained stub there could only auto-select, and clause 3 must PROMPT. B posts
the event and lets our existing cls2 record + native picker do the work.

⚠️ Route B's trampoline lives in ov5 (`CAVE_TG_ARMTRAMP`) on shared engine code, so
it is duel-only — which this card already is, via the row hook.

### Unchanged and still good
PARTS N (the criteria row at rel 4), O (the row-hook arm), P (the four slot
dispatchers) and the description fix are all built, verified and untouched by this
finding — they are downstream of a trigger that never fired. `verify()` = 85/85
PASS; chain rebuilt (32 patches) and the sweep is 22 PASS / 0 FAIL with the same
4 known non-applied modules erroring as in the baseline. KB 236 facts, 207 PASS,
0 FAIL.

### Next Experiment
Pick route A or B (user call — it is a fidelity-vs-cost trade), and in the SAME
build fix the instrumentation: latch the first non-zero `desc[+4]` into a slot the
clause-2 poll never overwrites, and count calls per event code. That way one duel
settles both "did the trigger arrive" and "with which event code".

### ✅✅ CORRECTION TO THE ROOT CAUSE ABOVE — IT WAS THE EVENT CODE, NOT THE TRIGGER

The section immediately above concluded "the mask row is inert, so no event was
posted, so clause 3 needs a trigger mechanism". **The first half is right and the
second half is wrong**, and the control that settles it is a card already shipped
in this repo.

**REBORN TENGU (Minefieldriller `0x2085`) IS THE DECISIVE CONTROL.** It is a
shipped, in-game-working *field-leave* trigger on a records-free donor, and it is
registered **nowhere**:

| cid | list30 | list106 | leave mask |
|---|---|---|---|
| `0x2085` Reborn Tengu (works in-game) | no | no | **no row at all** |
| `0x1859` Eclipse Wyvern donor | no | no | 0x0800 (added by its PART A) |
| `0x1ED4` Botanical Girl (native) | **yes** | no | no |

…yet `rom_all_patches.ml4/ml5` show its descriptor as
**`{cid 0x2085, zone 0x0E, event 0x1D, cls 2}`**.

**=> The leave dispatcher posts an event for ANY card leaving the field. The three
tables only gate specific NATIVE per-cid arms. Clause 3 needs NO trigger
registration whatsoever.**

**THE ACTUAL BUG WAS ONE CONSTANT.** The leave-field dispatcher picks its own event
code at `0x021C809C`:

```
0x021C809C  ldr  r0,[sp,#0x44]      ; destroyed BY BATTLE?
0x021C809E  cmp  r0,#0
0x021C80A0  beq  0x021C80A6
0x021C80A2  movs r0,#0x17           ; battle destruction
0x021C80A4  b    0x021C80A8
0x021C80A6  movs r0,#0x1D           ; every other field leave
0x021C80A8  str  r0,[sp,#0x1c]
```

and every native arm ORs `[sp+0x1C] << 0x19` into the packed word
(`0x021C9396..0x021C93A2`). So a field leave carries **0x17 or 0x1D**.
**0x1E is the RELOCATION APPLIER's code** (`0x021D1300`), which is how Eclipse
Wyvern's *any-location* trigger arrives — and 0x1E is what build 1 tested for.

So on the test duel the trigger **did** arrive, carrying `0x1D` (Dark Hole is an
effect destruction, not battle), all four slot dispatchers saw `0x1D != 0x1E`,
routed it to **clause 2's** arm, clause 2's condition demanded a LIGHT *and* a DARK
in hand (the hand held only REDMD), returned 0, and nothing was offered. Every
observation lines up.

### The stack slots at the leave hook, read off a native post (`0x021C9380..0x021C93B8`)
```
[sp+0x1C]  event code (0x17 / 0x1D)      [sp+0x98]  side  -> word bit 31
[sp+0x9C]  the packed ref (& 0xFFFF)     [sp+0xB8]  the cid
r0 = zone<<16 (masked 0x001F0000) | side<<31 | event<<25 | 1<<22 (cls 2) | cid
bl 0x021D3168
```

### What changed for build 2
1. **The discriminator is now a RANGE, not a constant:**
   `desc[+3] == 0x0E && desc[+4] > 6` selects clause 3. That covers `0x17`, `0x1D`
   **and** `0x1E` without enumerating them, and it can never catch clause 2, whose
   off-field gate `0x021ECC28` provably caps `desc[+4]` at 6 (measured: 0x00).
   Applied to all five sites — the row hook and the four record slots.
   The **zone** test is what keeps clause 3 to *sent to the GRAVEYARD* rather than
   any field leave: the descriptor's zone is the DESTINATION, so a bounce to the
   hand or a banish carries a different one.
2. **PART M is unwired and now raises if called**, with the whole wrong-premise
   argument kept in its docstring (cf. `synchro.material_pool_wrong`). Phantom
   `0x0E80` is released back to the pool; the mask table is asserted UNTOUCHED.
3. **PART Q gained a write-once LATCH** at `CAVE_LP_DIAG+0x1C`
   (`0x10000 | zone<<8 | event`, first `desc[+4] > 6` only) plus a counter at
   `+0x20`. Slots `+0x00..+0x18` are overwritten by clause 2's constant polling,
   which is exactly why build 1's reading was evidence rather than proof.
4. Cave re-home: the condition stub grew past its 0x100 reserve, so
   `CAVE_LP_C2COND2` is now 0x120 and `CAVE_LP_ROWHOOK` / `CAVE_LP_RESDISP` /
   `CAVE_LP_TGTDISP` moved up 0x20 (`0x0239C4C8` / `0x0239C528` / `0x0239C548`);
   `CAVE_FREE = 0x0239C568`.

`verify()` = **83/83 PASS**; allocation guard clean (94 ov5 slots, 44 phantom
claims, 94 B ov3 free); KB **236 facts, 207 PASS, 0 FAIL**.

### Lesson worth keeping
Two different subsystems post a "this card went to the Graveyard" class-2 event
with **different event codes**, and which one you get depends on HOW the card got
there. Never pin a descriptor discriminator to a single code measured from another
card's path — take the range, or measure the code on your own path first.

### BUILD 2 SHIPPED — ready for IN-GAME TEST 2 (2026-08-17)

`rom_lightpulsar.nds` and `rom_all_patches.nds` both rebuilt.

- single-card `verify()` = **83/83 PASS**; against the **combined** ROM = **PASS**
- chain: **ALL 32 PATCHES APPLIED**
- regression sweep (catching `BaseException`): **22 PASS, 0 FAIL, no regressions**;
  12 modules expose no `verify()`, and the same 4 known non-applied modules error
  as in the historical baseline (`patch_wonder_wand` commented out,
  `patch_bulk_ydcs` / `patch_zeta_reticulant` have no PatchStep,
  `patch_unlock_all_packs` has a zero-arg `verify()`)
- all four ov5 stubs read back **byte-identical** out of BOTH ROMs, and
  `CAVE_LP_DIAG` is **all zero in the image**, so a nonzero magic in a savestate is
  meaningful
- allocation guard clean (94 ov5 slots / 85 live, 44 phantom claims, 94 B ov3 free)
- KB **237 facts, 208 PASS, 0 FAIL** (new: `event.leave_field_event_codes`;
  `event.leave_dispatcher_three_registers` corrected in place rather than deleted)

**What to do in the duel:** get Lightpulsar onto the field with a **Level 5 or
higher DARK Dragon in your Graveyard** (REDMD `0x1D85` is ideal — Level 10 DARK
Dragon), then send Lightpulsar from the field to the GY. Battle destruction
(event `0x17`) and effect destruction (event `0x1D`) should both work; a tribute or
a Synchro Material use should too. Expect a *You can* prompt, then a picker showing
**only** Lv5+ DARK Dragons in your GY.

⚠️ Re-check clauses 1 and 2 in the same duel — the record's `+04` and `+14` are now
dispatchers rather than plain values, so clause 2 exercises new code even though its
behaviour should be bit-identical.

**If it fails, take a savestate and read `CAVE_LP_DIAG` (`0x0239C368`):**

| offset | meaning |
|---|---|
| `+0x00` | magic `0x4C503343` — the condition stub ran at all |
| `+0x04`..`+0x18` | the LAST call's cid / side+zone+event+cls / pass / global desc / r0 desc / resolved row |
| **`+0x1C`** | **write-once latch: the FIRST `desc[+4] > 6` seen, as `0x10000 \| zone<<8 \| event`** |
| **`+0x20`** | how many such calls happened |

`+0x1C` is the one that matters. **0** there means no leave event ever reached our
record, and the trigger really is missing. Non-zero means it arrived, and the low
byte names the event code and the next byte the zone — which then says whether the
fault is the discriminator, the row index, or the action.

## ⛔ IN-GAME TEST 2 — NOT OFFERED, AND THE LATCH SAID WHY (2026-08-17)

`rom_lightpulsar.ml2` / `.ml3`. Setup correct (Lightpulsar destroyed on the field
by Dark Hole; REDMD `0x1D85`, a Level 10 DARK Dragon, in the GY the whole time).

`CAVE_LP_DIAG`: magic present (the stub runs), last call `{cid 0x0FB1, zone 0x0E,
event 0x00, cls 2, row 69}` = a clause-2 poll, and

**`+0x1C` (the write-once latch) = 0, `+0x20` (the counter) = 0.**

So NO descriptor with `desc[+4] > 6` ever reached the record. Proof this time, not
inference — which is exactly what the latch was added for.

## ⛔⛔ THE CAUSE WAS MINE: I REMOVED PART M, THE THING THAT WAS WORKING

**User, 2026-08-17: "There are lots of any-leaves, We implemented a fresh one on GK
recruiter..."** — correct, and it is the control that settles this.

`patch_gravekeepers_recruiter` (donor **Botanical Girl `0x1ED4`**) implements the
same trigger and its PART A3 says the registration IS the list30 membership, and
that "the dispatcher routes by cid RANGE through a **generic** event-type gate (not
tied to any card's native effect)". Checking that against the switch:

**SANGAN `0x0FD6` AND OUR DONOR `0x0FB1` REACH THE SAME ARM.** Both fall in the
interval `(0x0EBF, 0x1174)`, so both walk
`0x021C8240 (vs 0x13A1, blt) -> 0x021C824C (vs 0x0EBF, bgt) -> 0x021C8272
(vs 0x1174, neither) -> 0x021C827A: bl 0x021C93D0`.
Sangan's any-means sent-to-GY trigger works natively. Ours does not. **The arm is
therefore generic and is not what distinguishes them** — and `0x021C93D0` is not a
do-nothing leaf either (it is a long generic tail: `0x021D3438`, `0x02244280`, …).

What distinguishes them is **`[sp+0x18]`**, and the only three things that set it
are list106, list30 and the leave-mask table — i.e. exactly PART M.

### Reconstructing both failures
| test | mask row (PART M) | discriminator | what happened |
|---|---|---|---|
| 1 | **present** | `== 0x1E` (wrong; the leave path posts `0x17`/`0x1D`) | the trigger DID fire; every dispatcher routed it to clause 2's arm; clause 2's condition wanted a LIGHT and a DARK in hand (only REDMD was there) -> 0 -> no offer |
| 2 | **removed by me** | fixed (`> 6`) | no event at all -> latch 0 |

**Two separate bugs, one per build, and the second hid the first.** Build 3 has the
mask row AND the range discriminator.

### PART S — written, then withdrawn
Between the two I built a 96 B ov5 stub to post the event by hand, hooked over
`0x021C827A`. It is **unnecessary and is not installed**; the applier raises and the
hook site is asserted STOCK in `verify()`. It would have hooked a site shared by
**692 cids / 316 real cards** (Blue-Eyes, Dark Magician, …) to fix a problem that
did not exist. The switch trace it produced is kept, because it is real and shows
there is no dead arm on this cid's path (the only equality test `0x0FB1` reaches is
against `0x1174`, which is also the binary-search pivot).

### Lesson
The engine's leave switch dispatches a whole cid RANGE to one generic arm; a card
triggers because of the `[sp+0x18]` registration, not because it has a bespoke arm.
Before inventing a mechanism, grep the repo for a shipped card with the same printed
wording — `patch_gravekeepers_recruiter` had this exact trigger working, and
`event.optional_trigger_is_record_shape` even cites it.

## BUILD 3 (2026-08-17)
- **PART M restored** (mask row `{0x0FB1, 0x0800}`, count-neutral over phantom
  `0x0E80`) — the trigger.
- **PART O/P discriminator** stays the corrected range: `desc[+3] == 0x0E &&
  desc[+4] > 6`, covering `0x17` (battle) and `0x1D` (every other field leave).
- **PART S unwired**; `CAVE_LP_LEAVE` marked retired, 0 B used.
- `verify()` = **87/87 PASS**, including a check that Sangan keeps its list30 row
  (the control) and that the PART S site is stock.
- Ledger: 95 ov5 slots, 46 phantom claims, 94 B ov3 free.
- KB **237 facts, 208 PASS, 0 FAIL**; `event.leave_dispatcher_three_registers`
  corrected a second time — a registration IS required, and the three tables are
  interchangeable as far as the switch is concerned.

## ⚠️ IN-GAME TEST 3 — "MISSED THE TIMING" (2026-08-17). THE TRIGGER WORKS.

User-reported: Lightpulsar was used as **Synchro Material**, and the game said it
**missed the timing**. That is a timing-CLASS verdict, which means the engine
recognised our effect -- so PART M (the mask row), the range discriminator and all
four record-slot dispatchers are working. Only the classification was wrong.

### ✅ THE CLASSIFIER READS THE +0x10 LITERAL AND NEVER CALLS THE SLOT
`timing.classifier` 0x0224AF7C, disassembled this session:

```
0x0224AF80  ldrb r1,[desc,#5]      ; selector 0 or 3 -> return 0 immediately
0x0224AF8E  bl   find_event_handler
0x0224AF96  ldr  r0,[rec,#0x10]    ; *** the RAW tag value ***
0x0224AF98  cmp  r0,#0
0x0224AF9A  bne  ...               ; +0x10 == 0        -> CLASS 0
0x0224AFA0  cmp  r0,=0x021E51E5    ; the "You can" tag -> class 2
0x0224AFAA  cmp  r0,=0x021E50DD                        -> class 1
            ... 0x021E5201, 0x021E780D, 0x021E88F5, 0x021E91DD, 0x021E9A21,
                0x021E986D, 0x021EAD71, 0x021E7969, 0x021E9215 ... -> class 1
```

**Class 0 is the one that cannot miss the timing**, and it is reached only by
`+0x10 == 0` -- literally Sangan 0x0FD6's shape, which is why
`patch_gravekeepers_recruiter` adopts that pairing and claims its trigger fires on
"battle destruction, effect destruction, Tribute AND Synchro Material".

**Our +0x10 is `CAVE_LP_C2COST`** -- clause 2 needs a real cost function there --
so it matches none of the cases and the card could never be filed as mandatory.

⚠️ **A DONOR SHARING ONE RECORD BETWEEN TWO CLAUSES CANNOT CHOOSE ITS TIMING CLASS
WITH A DISPATCHER STUB**, because the classifier reads the literal and never
executes it. Filed as `timing.class_is_the_slot4_literal` (VERIFIED).

### PART T -- the fix (32 B, ov5 `CAVE_LP_TIMING`)
Displace the classifier's own `ldr r0,[r0,#0x10] ; cmp r0,#0` at 0x0224AF96 into a
stub that performs the same load and then, **for our cid on a leave event only**,
substitutes 0 -- so the classifier sees Sangan's shape. It replays the `cmp` so the
caller's `bne` at 0x0224AF9A gets the right flags; every other card reaches the tag
chain with its real value.

⚠️ `+0C` is deliberately LEFT at 0x021F03B5. Matching Sangan exactly would mean
nulling it too, but that is the "does a legal target exist" gate, and removing an
equivalent gate is what gave Eclipse Wyvern an empty-deck FREEZE. One variable per
test: this build changes the timing class and nothing else.

`verify()` = **91/91 PASS**; all four ov5 stubs resident and byte-identical in
`rom_lightpulsar.nds`; the withdrawn PART S slot is still zero. Ledger clean
(96 ov5 slots). KB **238 facts, 209 PASS, 0 FAIL**.

⚠️ `rom_all_patches.nds` is ONE BUILD BEHIND (it has PART M + the range
discriminator but not PART T) -- rebuild it once clause 3 is confirmed.

### Next Experiment
Send Lightpulsar from the field to the GY as **Synchro Material** (the case that
failed) and by **destruction**. Expect the prompt and a picker of Lv5+ DARK Dragons
in the GY. If it still misses the timing, the class verdict is coming from
somewhere other than 0x0224AF7C and the next step is to breakpoint that function
rather than guess.

# ✅✅✅ CLAUSE 3 WORKS — IN-GAME CONFIRMED (2026-08-17). LIGHTPULSAR IS COMPLETE.

User-reported: *"Perfect, ship it"* after the PART T build. All three clauses are
now live on donor Sword Arm of Dragon `0x0FB1`:

1. SS from hand, banishing 1 LIGHT + 1 DARK from the GY  (confirmed 2026-08-13)
2. SS from the GY, sending 1 LIGHT + 1 DARK from the hand (confirmed 2026-08-14)
3. Sent from the field to the GY: target 1 Lv5+ DARK Dragon in the GY and SS it
   (confirmed 2026-08-17)

## The final architecture of clause 3

| part | what it does |
|---|---|
| **M** | leave-mask row `{0x0FB1, 0x0800}` (phantom `0x0E80` dropped) — sets `[sp+0x18]`, which is what the leave switch's GENERIC arm needs. Sangan `0x0FD6` reaches the very same arm and triggers purely on its list30 membership. |
| **N** | criteria row at rel 4: `{0xFFFF, 0x0223C9D1, 0x0A550002}` — the 3DS's own row for the real Lightpulsar `0x26E3`, handler mapped by a four-card join |
| **O** | `CAVE_LP_ROWHOOK` third arm: `desc[+3] == 0x0E && desc[+4] > 6` -> `r4 = 4` |
| **P** | the single cls2 record's four slots, each branching on the same zone+event test: `+04` -> `0x02207191`, `+0C` -> `0x021F03B5`, `+10` -> `0x021E51E5`, `+14` -> `0x02235605` |
| **T** | the timing class — the classifier reads `+0x10` as a LITERAL, so a shared record cannot pick its class; the stub makes it see Sangan's `+10 == 0` for our cid on a leave event |
| **Q** | instrumentation (magic, last call, write-once latch, counter) in the otherwise-unused `CAVE_LP_DIAG` |

## What it took, and the three things that actually cost the time

| test | symptom | cause |
|---|---|---|
| 1 | nothing offered | discriminator pinned to event `0x1E` (the RELOCATION applier's code) when the leave path posts `0x17`/`0x1D` |
| 2 | nothing offered, latch = 0 | I removed PART M on a misreading — the one piece that was working |
| 3 | "missed the timing" on Synchro Material | the WHEN-vs-IF classifier reads the `+0x10` LITERAL, and ours is clause 2's cost stub |

**The through-line, and it is not a new lesson:** every one of the three was
settled by a control that already existed — Reborn Tengu's savestate for the event
code, Sangan and `patch_gravekeepers_recruiter` for the registration, Sangan again
for the timing class. Two of the three were things I had already read past. **Grep
the repo for a shipped card with the same printed wording BEFORE reading
disassembly.** `event.optional_trigger_is_record_shape` even names
`patch_gravekeepers_recruiter` in its own claim text.

## Also fixed this session
The card's in-game description had been **108 B against a 98 B English slot**, so
it was SKIPPED in every language and the card had been showing Sword Arm of
Dragon's flavour text since clause 1 shipped. The new 88 B text covers all three
clauses and lands in e/f/g/i/s/r (j/k slots are 48/57 B and keep the original).

## Withdrawn, kept unwired for the record
**PART S** — a 96 B hand-rolled event poster hooked over `0x021C827A`. Unnecessary:
that arm is generic, not a dead leaf. It would have hooked a site shared by 692
cids / 316 real cards. `CAVE_LP_LEAVE` is reserved but never written, and
`verify()` asserts the site is stock.

## KB contributions
| id | grade |
|---|---|
| `event.leave_dispatcher_three_registers` | VERIFIED (new) |
| `event.leave_field_event_codes` | VERIFIED (new) |
| `dispatch.cls2_gy_revive_resolver` | VERIFIED (new) |
| `dispatch.absent_cls_slot_returns_one` | VERIFIED (new) |
| `timing.class_is_the_slot4_literal` | VERIFIED (new) |

## ✅ CORRECTION — PART T WITHDRAWN. THE "MISSED THE TIMING" REPORT WAS CORRECT BEHAVIOUR.

User, 2026-08-17: *"I was actually mistaken, because the effect actually can miss
timing (that is my bad) but the fix you implemented did not make it a mandatory
optional so the behaviour is correct."*

Clause 3 is a **WHEN**-you-can effect -- "**When** this card is sent from the field
to the GY: You can target..." -- so losing it when the Synchro Summon is the last
thing to happen is **correct Yu-Gi-Oh behaviour**, not a bug. PART T was built to
solve a non-problem, and it made the card strictly MORE generous than the printed
text while hooking `0x0224AF7C`, a function every triggered card passes through.

**Dropped (user decision).** The applier raises, the stub is never installed,
`CAVE_LP_TIMING` is reserved-but-zero, and `verify()` now asserts the classifier
site is STOCK (`00690028`).

### ⚠️ AND A HONEST CORRECTION TO MY OWN KB ENTRY
`timing.class_is_the_slot4_literal` remains VERIFIED for the part that was
measured -- the classifier reads `[rec+0x10]` as a LITERAL, never calls the slot,
and maps `+0x10 == 0 -> class 0`, `0x021E51E5 -> class 2`, a dozen other tags
`-> class 1`. That mapping is real and still useful.

**What was NEVER measured is what the classes MEAN.** "Class 0 cannot miss the
timing" came from `patch_gravekeepers_recruiter`'s docstring prose, not from an
observation, and I presented an inference as if it were the finding. Now filed
separately as **`timing.class_semantics` (UNVERIFIED)** with the experiment that
would settle it: re-install the withdrawn PART T hook for a cid whose trigger is
known to miss the timing, use it as Synchro Material, and see whether it fires.

### Final shipped state of clause 3
PARTS **M** (leave-mask row), **N** (criteria row at rel 4), **O** (row-hook third
arm), **P** (four record slots branching on `desc[+3] == 0x0E && desc[+4] > 6`),
**Q** (instrumentation). PARTS **S** and **T** are both withdrawn and unwired,
each with its analysis kept in the applier's docstring.

`verify()` = **91/91 PASS** (it now pins BOTH withdrawn hook sites as stock).
Ledger: 96 ov5 slots, 46 phantom claims, 94 B ov3 free.
KB: **239 facts, 207 PASS, 0 FAIL, 32 UNVERIFIED.**

## ✅ SHIPPED + CLEANED UP (2026-08-17)

### Cleanup -- proven byte-neutral
`patch_lightpulsar.py` **3052 -> 2830 lines**, and the rebuilt overlays hash
IDENTICAL to the pre-cleanup build (sha256 of ov3 and ov5 both unchanged), with
`verify()` still **91/91 PASS**. Nothing shipped changed; only dead code went.

Removed: `_stub_leave` + `_stub_timing`; the unreachable bodies under both
withdrawn appliers; `apply_proxy_rows` / `apply_proxy_cls2` / `h_bl`; 9 unused
constants; **the `SIMORGH_STYLE` flag and every branch on it** (permanently True
since 2026-08-14, so `apply_effect`, `main()`, both cost-stub helpers and three
`verify()` blocks each carried a dead alternative); and the two never-written cave
slots `CAVE_LP_LEAVE` / `CAVE_LP_TIMING`, reclaiming `CAVE_FREE` to `0x0239C568`.

Kept on purpose: `apply_leave_hook` and `apply_timing` as RAISING stubs carrying
their full analysis -- they are the record of why each was withdrawn, and
`verify()` still asserts BOTH sites are stock so a future patch cannot hook them
by accident. Also `PROXY_CID` (its two criteria rows are still the count-neutral
drop for the rel-2/3 insert) and the `DIAG_C2_*` scaffolding.

### Final verification
| check | result |
|---|---|
| `patch_lightpulsar.verify()` single-card | **91/91 PASS** |
| `verify()` vs the COMBINED ROM | **PASS** |
| chain | **ALL 32 PATCHES APPLIED** |
| regression sweep (catching `BaseException`) | **22 PASS, 0 FAIL, no regressions** -- 12 modules expose no `verify()`, and the same 4 known non-applied modules error as in the historical baseline |
| allocation guard | 94 ov5 slots, 46 phantom claims, 94 B ov3 free, ledger in sync |
| KB | **239 facts, 209 PASS, 0 FAIL** |

### Outstanding (deliberately not done)
`C3_DIAG` is still `True`, so the +0C stub records to `CAVE_LP_DIAG` on every call
and pays one `0x02243B9C` lookup per clause-2 poll. It only records, but stripping
it changes emitted bytes and would invalidate the in-game confirmation, so it wants
its own one-variable change rather than riding along in a cleanup.

## ✅✅✅ FINAL — PART T RESTORED, AND THE CLASS SEMANTICS ARE THE OPPOSITE OF MY GUESS

User, 2026-08-17: *"When the card is being sent for a synchro summon, it is now not
saying it misses timing. I want that behaviour back"* -- then, after the rebuild,
*"okay perfect!"*

**THE A/B IS DECISIVE, AND IT INVERTS THE READING I DROPPED PART T OVER:**

| what the classifier 0x0224AF7C sees at `+0x10` | in-game, card used as Synchro Material |
|---|---|
| `CAVE_LP_C2COST` -- an UNRECOGNISED pointer, so NO class | **nothing happens, no message** |
| `0` via PART T -- **class 0** | **"MISSED THE TIMING", correctly** |

So **class 0 is not a "cannot miss the timing" class.** It means the effect is a
PROPERLY CLASSIFIED TRIGGER, and the engine then applies the miss-timing rule to it
correctly. An unclassified trigger is silently dropped.

**=> PART T IS REQUIRED FOR CORRECT BEHAVIOUR, not a generosity hack.** I withdrew
it as a "fidelity regression" on an inference taken from
patch_gravekeepers_recruiter's prose -- and I put that inference into a question to
the user as the recommended option, which is how a correct part came out of a
shipped card. The measurement was available the whole time.

⚠️ Lesson, and it is the same one three times on this card: **an A/B I could have
run beats a sentence of prose in another patch's docstring.** Filed as
`timing.class_semantics` (ANCHORED, with the in-game A/B in the claim) and folded
into `timing.class_is_the_slot4_literal`.

`CAVE_LP_TIMING` now lives at `0x0239C568` (the cleanup had reclaimed its old
`0x0239C5E8`); `CAVE_FREE = 0x0239C5A8`.

# LIGHTPULSAR DRAGON -- COMPLETE

| clause | mechanism | confirmed |
|---|---|---|
| 1 | hand-SS dead-arm route + count edit + 2 criteria rows + list A + summon-procedure row + the 2 payment stubs | 2026-08-13 |
| 2 | GY-action registry row + shared cls2 record + hand pair at rel 2/3 + row hook + ov5 condition & cost | 2026-08-14 |
| 3 | leave-mask row (M) + revive row at rel 4 (N) + row-hook arm (O) + four slot dispatchers (P) + timing class (T) | 2026-08-17 |

Plus the description fix -- the card had been showing Sword Arm of Dragon's flavour
text in every language since clause 1 shipped, because the text was 108 B against a
98 B slot and the writer silently skips an over-long description.

---

# ⚠️ 2026-08-17 — THE PAYMENT STUBS MOVED OUT OF THIS MODULE (Darkflare)

Darkflare Dragon's clause 1 is this card's clause 1 word for word, and it needs the
SAME two payment dispatches. Each of those has exactly **one** 4-byte BL hook, so
PARTS E/F could not stay single-cid. They now live in
**`otn_enhanced/effects/handss_banish_cost.py`**, which owns:

* `DONOR_CIDS = (0x0FB1, 0x1646)` -- the register the stubs test against;
* the stub builders, the 126 B ov3 dead run and its layout;
* the D-arm sealing and the E/F hooks, as one idempotent `apply(ov)`;
* a `verify(ov, check)` both card modules call.

**What changed for Lightpulsar, precisely:**

1. **Its emitted stub bytes are different** -- 44 + 36 B became 56 + 48 B (104 of
   126 B used). Lightpulsar's own path through them is unchanged: pay-1 still
   tests Dark Necrofear first and routes `0x0FB1` to `0x02262A5A`, pay-2 still
   routes it to `0x02262C8C` and still replays `ldr r2,=0x1BC8 ; cmp r0,r2` with
   `push {r2}` / `pop {pc}` on the native path.
2. **PART D's assertion was relaxed** from "both dead arms point at the reject
   leaf" to the invariant that actually matters: *no arm branches INTO the cave*.
   Darkflare re-aims `0x0225E88E` at the real leaf `0x0225FA46`, which seals the
   cave exactly as well. The old wording would have flagged that as a collision
   when it is not one.
3. Nothing else. `verify()` = **91 PASS / 0 FAIL** on the rebuilt
   `rom_lightpulsar.nds`, and the whole-cid-space differential on the composed
   `rom_ew_lp_df.nds` shows the only real cards changing hand-SS leaf are the two
   donors.

⚠️ **This has NOT been re-confirmed in a duel.** The stub bytes under Lightpulsar
changed, so the next in-game session should re-test THIS card as well as Darkflare
(step 3 of the test in notes/darkflare-dragon-findings.md).

⚠️ **There are no dead hand-SS arms left that a monster can reach** -- see the new
KB fact `handss.dead_arm_donor_windows`. The two remaining arms
(`0x0225E67C`, `0x0225E692`) can only ever be aimed at Speed Spells. A third
banish-cost card needs a different routing mechanism.

## ✅ NO REGRESSION FROM THE SHARED-STUB REFACTOR — IN-GAME CONFIRMED (2026-08-17)

User-reported alongside Darkflare's first-test pass: *"No regressions in
lightpulsar."* The payment stubs under this card were rewritten from single-cid to
a two-donor register (44 + 36 B -> 56 + 48 B) and its PART-D guard relaxed to "no
arm branches into the cave"; both are confirmed harmless on the live path, not
merely on paper. Nothing further is owed on this card.
