# Elemental HERO Escuridao — findings

**Session start: 2026-08-03.** Donor: **Elemental HERO Darkbright `0x1C08`**.
Target card text (source `scratch/ygoprodeck_cache.json`, id 33574806 — NOT recalled):

> 1 "Elemental HERO" monster + 1 DARK monster
> Must be Fusion Summoned and cannot be Special Summoned by other ways. This card
> gains 100 ATK for each "Elemental HERO" monster in your Graveyard.
> Fusion / Level 8 / DARK / Warrior / 2500 / 2000

Clauses: **(1)** materials = 1 E-HERO + 1 DARK · **(2)** must be Fusion Summoned ·
**(3)** +100 ATK per E-HERO in your GY.

**Status:** clauses **1 and 2 are implemented and `verify()`-clean**
(`otn_enhanced/cards/escuridao.py`, registered in
`apply_all_patches.PATCHES` above the WiFi-timers step). Clause **3 is
`unproven`** — the engine is mapped but the per-card amount is not yet located,
and no GDB session was run, so nothing was built for it. Not yet tested in-game.

Escuridao is **not** in the OTN pool (0 hits over 4305 cards in
`scratch/cid_to_name.json`). It is the missing DARK member of the attribute-HERO
Fusion cycle; the other five are present.

---

## Confirmed (proved THIS session, static, on the committed oracles)

The engine KB had **no fusion facts at all** before this session.

### The fusion recipe tables

- **Table A** = `0x02270B94`, **161 rows × 8 bytes**, `{u16 result_cid, u16 m1,
  u16 m2, u16 m3}`, sorted ascending by `result_cid`, ends exactly at
  `0x0227109C`.
  *Proof:* the count and stride are literal immediates in the consumer —
  `movs r2,#0xa1; movs r3,#8` @ `0x02231E92` — and
  `0x02270B94 + 161*8 == 0x0227109C`; the cid column is strictly ascending.
- **Table B** = `0x02270B58`, **5 rows × 12 bytes** (up to 5 materials), ends
  exactly at table A's base. *Proof:* `movs r2,#5; movs r3,#0xc` @ `0x02231EAE`.
  Members: Five-Headed Dragon `{1,1,1,1,1}` (= 5 Dragon-Type), E-HERO Electrum,
  Super Vehicroid - Stealth Union, E-HERO Divine Neos, Barbaroid.
- Both tables are binary-searched by the shared ARM9 helper **`0x02022E44`**
  `(key, base, count, stride)`.

### The fusion table API (all in ov3)

| Function | Signature | Behaviour |
|---|---|---|
| `0x02231E08` | `(cid)` | material COUNT → `0` / `2` / `3` / `4` / `5` (reads `row+6` / `row+0xA`, adds 2 / 4) |
| `0x02231E8C` | `(cid, i)` | material slot `i` → signed halfword `row[2*(i+1)]` |
| `0x02231ECC` | `(out, material)` | reverse lookup: every fusion whose recipe names `material` |
| `0x02231F50` | `(...)` | loads the current fusion's requirement codes into the array at **`0x0229AC80`** (`0x0229A37C + 0x904`), count = `[0x0229ABFC + 0x70]` clamped to 5 |
| `0x02231A74` | `(code, card)` | **the material-code predicate** — called from the fusion match loop @ `0x0223210A` |

`0x0229ABFC` is the fusion-UI state struct: `+0x68` = target fusion cid,
`+0x70` = material count, `+0x78`/`+0x7C` counters.

### The material-code space

- **1 – 22** → Type/race. Test is `(1 << code) & (1 << get_race(cid))`
  @ `0x02231B2C`, gated by `cmp r0,#0x16` @ `0x02231B1E`.
  Observed: 1 = Dragon (Five-Headed Dragon), 3 = Fiend + 6 = Rock (Evil HERO
  Dark Gaia), 7 = Machine (Chimeratech Fortress Dragon).
- **23 – 50** → a 28-entry PC-relative halfword jump table at `0x02231B54`
  (`subs #0x17; cmp #0x1B; bls` @ `0x02231B40`; targets = `0x02231B56 + off`).
  The observed code histogram over all 166 recipes maxes at exactly **50**.
- **≥ 51 (`0x33`)** → a literal card cid. *Proof:* `cmp r0,#0x33` @ `0x02232146`
  and `cmp r7,#0x33` @ `0x0223214C`.

### Decoded leaves that matter here

- **Codes 36–41 all share ONE leaf, `0x02231CF2`**, which is parametric:
  ```
  ldr r0,[sp]        ; the requirement code
  subs r0,#0x23      ; - 35
  movs r1,#1 ; lsls r1,r0
  ldr r0,[sp,#0xc]   ; = 1 << get_attribute(cid)
  ands r0,r1
  ```
  i.e. **`match ⟺ attribute == code − 35`**.
- Engine attribute numbering (`ERA2_ATTRIBUTE_MAP`): LIGHT 1, DARK 2, WATER 3,
  FIRE 4, EARTH 5, WIND 6, DIVINE 7. Cross-checked against every sibling row:

  | card | recipe row | code | ⇒ attr | real |
  |---|---|---|---|---|
  | The Shining `0x2161` | `0x0227100C` | 36 | 1 | LIGHT ✓ |
  | Absolute Zero `0x1FC1` | `0x02270FFC` | 38 | 3 | WATER ✓ |
  | Nova Master `0x24DF` | `0x02271094` | 39 | 4 | FIRE ✓ |
  | Gaia `0x1FBA` | `0x02270FF4` | 40 | 5 | EARTH ✓ |
  | Great Tornado `0x2190` | `0x02271014` | 41 | 6 | WIND ✓ |

  **⇒ DARK = attribute 2 = material code 37**, the one unused slot in the block.
- **Code 30 = "HERO"** (leaf `0x02231C58` → set-code thunk `0x02023974`).
  Users: Vision HERO Adoration `{30,30}`, Vision HERO Trinity `{30,30,30}`,
  and (ROM divergence) Absolute Zero.
- **Code 31 = "Elemental HERO"** (leaf `0x02231C74` → set-code thunk
  **`0x0202381C`**, ptr-table `0x0209D0D8` index 8). Users: Gaia, The Shining,
  Great Tornado, Nova Master.

### Set-code list + card record getters

- **"Elemental HERO" cid list** = `0x0209CFE4 … 0x0209D058`, **58 sorted u16**.
  Every entry is an *Elemental Hero* card; preceded by the Archfiend list
  (`0x0209CF94`, 40 entries). **Darkbright is already a member** (`0x0209D038`)
  — no set-code insert needed, so no count-neutrality problem there.
- `get_race` `0x0202ABB8` = `(w4>>17)&0x1F`; `get_attribute` `0x0202ABC8` =
  `(w4>>6)&0xF`; `get_level` `0x0202ABD8` = `(w4>>10)&0xF`, where `w4` is the
  second u32 of the 8-byte card record.

### The continuous ATK/DEF modifier engine (clause 3's machinery — found, not yet wired)

- **TWO per-cid delta tables**, both stride 6 `{u16 cid, s16 atk_delta, s16 def_delta}`,
  sorted, binary-searched by the same ARM9 helper `0x02022E44`:

  | table | base | count | ends |
  |---|---|---|---|
  | delta table 1 | `0x0226E1E4` | `0x6F` = 111 | `0x0226E43A` |
  | delta table 2 | `0x0226E4BC` | 103 | `0x0226E726` |

  Table 1's geometry is the literal immediates `movs r2,#0x6f; movs r3,#6`
  @`0x0226E1E4`'s call site `0x021B610C`; table 2 was walked (ascending cid,
  ends where the next structure starts). Which table applies is selected by
  `cmp r6,#1` @`0x021B6104`.
- **A stored delta of ±1 is a SENTINEL meaning "variable — multiply by the
  runtime amount in `[sp+0x80]`".** The idiom appears four times (once per
  ATK/DEF field per table), e.g. @`0x021B6118`:
  ```
  movs r3,#2 ; ldrsh r2,[r0,r3]     ; row+2 = ATK delta
  movs r1,#1 ; cmp r2,#1  ; beq keep
  subs r3,r3,#3 ; cmp r2,r3 ; beq keep   ; r3 = -1
  movs r1,#0
  keep: cmp r1,#0 ; beq add
        ldr r1,[sp,#0x80] ; muls r2,r1,r2   ; <-- variable amount
  add:  ldr r1,[sp,#0xa8] ; adds r1,r1,r2 ; str r1,[sp,#0xa8]
  ```
  `[sp+0xA8]` / `[sp+0xA4]` are the running ATK / DEF totals.
- **45 of table 2's 103 rows carry the ±1 sentinel**, and reading their real card
  text confirms the family: Bazoo the Soul-Eater, **Chaosrider Gustaph**,
  Necroface, Gandora, Gaia Soul, White-Horned Dragon, Card Trooper, Rallis,
  Etoile Cyber, Elemental Hero Terra Firma — all "gains N ATK for each / equal
  to X". Fixed-delta cards store the literal amount instead (Zombyra −200,
  Exarion Universe −400, Legendary Fiend +700, Exodia Necross +500,
  Insect Princess +500, Berserk Dragon −500) — each matching its real text.
- **`Chaosrider Gustaph` (`0x16C4`, table 2 row 12, atk = 1) is the structural
  twin of Escuridao's clause 3**: "gains 100 ATK for each Equip Spell Card in
  your Graveyard" = 100 × count-in-own-GY, the exact shape needed.

### ⚠️ CORRECTION — `[sp+0x80]` is a RIDER-NODE FIELD, not a per-cid switch

An earlier version of this note said the variable amount was computed by "a
per-cid switch in `0x021B4A00`–`0x021B6600`". **That was a guess and it is
wrong.** Measured: in the whole region there is **exactly one** write,
`str r0,[sp,#0x80]` @ `0x021B5FD0`, and it is a plain struct load:

```
ldr  r1,[sp,#0x28]        ; node index
movs r2,#0xa              ; stride 0xA
ldr  r0,=0x0229D33C       ; the RELATIONSHIP-NODE POOL (ram.relationship_pool)
muls r2,r1,r2
adds r1,r0,r2             ; node = pool + idx*0xA
ldrh r5,[r0,r2]           ; node+0 = the granting cid  -> the delta-table key
ldrh r0,[r1,#2]           ; node+2 = kind
ldrh r0,[r1,#4]
str  r0,[sp,#0x80]        ; node+4 = THE AMOUNT
```

So the real model is: **the whole function is the continuous-rider walker.** For
each rider node attached to a monster it takes `node+0` (the *granting* card's
cid), looks that up in the delta tables, and applies the delta — multiplied by
`node+4` when the delta is the ±1 sentinel. The amount is baked into the node at
**attach** time; the delta table only supplies the sign.

### The shared "count × multiplier" attach tail — `0x02219AE0 … 0x02219B0E`

Chaosrider Gustaph's cid pool word `0x02219B2C` sits in the function that owns
this tail, a switch of per-card multiplier arms feeding one attach call:

```
0x02219AFC   ldr  r1,[r5,#0x34]   ; r1 = THE COUNT (computed upstream, per card)
0x02219AFE   movs r0,#0xc8        ;   x 200
0x02219B00   muls r0,r1,r0
0x02219B02   movs r3,#3           ; kind = 3
0x02219B04   lsls/lsrs r0,#0x10   ; truncate to u16
0x02219B08   str  r0,[sp]         ; param  -> becomes node+4 -> [sp+0x80]
0x02219B0A   ldrb r0,[r4,#2] ; ldrb r1,[r4,#3]    ; side, slot
0x02219B0E   bl   0x021C479C      ; riders.attach_api
```

Sibling arms supply other multipliers: `0x02219AEA` → `0x19<<4` = **400**,
`0x02219AF4` → `0x7D<<2` = **500**, `0x02219AE0` → `r0<<2` with kind `0x12`.
`riders.attach_api` `0x021C479C(r0=side, r1=slot, r2=key cid, r3=kind,
[sp]=param)` is already in the KB.

**So clause 3 is: attach a node keyed `0x1C08`, kind 3, param = 100 × (E-HEROes
in your own GY), and give `0x1C08` a `+1` row in a delta table.** Absolute Zero
attaches with the same API (`bl 0x021C479C` @ `0x02250DD4`, `movs r3,#4`,
param 0), which is why its ATK gain has no cls record.

### ✅ THE TEMPLATE: Miracle Kids' leaf (the whole clause-3 recipe)

`Miracle Kids 0x19B4` ("that target loses **400** ATK for each **'Hero Kid'** in
your Graveyard") is routed by the cid switch at `0x02219C70…0x02219CDE`
(`r4` = cid; the `0x19B4` arm at `0x02219CAA` falls through to `b 0x02219DCA`).
Its leaf is six instructions and contains every piece clause 3 needs:

```
02219DCA  ldrb r0,[r5,#2]     ; side
02219DCC  subs r1,#0xd        ; r1 = 0x19B4 - 0xD = 0x19A7 "Hero Kid"  <- counted cid
02219DCE  bl   0x021B13E0     ; COUNT cid r1 in side r0's GRAVEYARD
02219DD2  movs r1,#0x19
02219DD4  lsls r1,r1,#4       ; r1 = 0x190 = 400                       <- multiplier
02219DD6  b    0x02219D24     ; -> shared "count x multiplier -> attach" tail
```

**Full chain, now end-to-end known:**
`cid switch → leaf (count-in-GY × multiplier) → shared tail 0x02219AE0-0x02219B0E
→ riders.attach_api 0x021C479C (node+4 = the amount) → the rider walker
0x021B5FD0 reads node+4 into [sp+0x80] → delta-table ±1 sentinel multiplies it in.`

⚠️ The counted cid is encoded `base − 0xD`, the documented `base ± imm` switch
footgun — which is exactly why no byte scan for "Hero Kid" ever found this site.

**The one mismatch:** `0x021B13E0` counts ONE specific cid. Escuridao needs "any
*Elemental HERO*" — a set-code predicate. `Raging Mad Plants 0x212F` counts by
**Type** and `Deal of Phantom 0x1492` counts **any monster**, so their leaves must
call a *predicate-taking* counter. Read those two leaves to get it, then feed it
the E-HERO set-code thunk `0x0202381C`.

### The two delta tables are SELF vs OTHER

Reading each table's members against their real text:

- **Table 1 `0x0226E1E4` = cards that grant ATK to ANOTHER monster** — it is full
  of Spells/Traps: Deal of Phantom, Energy Drain, Ojamuscle, Synchro Strike,
  Beast Rage, Factory of 100 Machines, Raging Mad Plants, Miracle Kids (−1).
- **Table 2 `0x0226E4BC` = cards that grant ATK to THEMSELVES** — Zombyra,
  Chaosrider Gustaph, Terra Firma, Card Trooper, Insect Princess.

That is what the `cmp r6,#1` selector @ `0x021B6104` chooses between.
**Escuridao's row belongs in TABLE 2.**

### ⚠️ Two probe-card corrections (both were my own recall, not the cache)

1. **Chaosrider Gustaph is NOT "100 ATK per Equip Spell in your GY".** Real text
   (ygoprodeck 0x16C4): *"Once per turn, you can remove from play up to 2 Spell
   Cards from your Graveyard. This card gains 300 ATK for each card removed,
   until the end of your opponent's next turn."* It is an **activated, temporary**
   gain — the wrong shape for Escuridao and a poor probe. Everything above that
   called it "the structural twin" is wrong.
2. **Absolute Zero `0x1FC1` and The Shining `0x2161` are in NEITHER delta table.**
   So their continuous ATK gains appear to be **unimplemented in OTN**. Do not
   use them as templates.

**The right probe is `Elemental Hero Terra Firma 0x1A4B`** — table 2, sentinel
`atk=+1`, and its gain is genuinely **continuous** ("gains ATK equal to the
combined original ATK of the other face-up 'Elemental HERO' monsters you
control"), so it recomputes as monsters enter and leave. It is also an E-HERO,
so it exercises the same set-code path Escuridao needs. Its "equal to combined
ATK" shape (rather than N × count) also settles the units question directly:
whatever `[r5+0x34]` holds for it must be an ATK total, with a ×1 arm.

### Donor facts

- Darkbright recipe row @ **`0x02270F2C`** =
  `{0x1C08, 0x18A9 Sparkman, 0x197F Necroshade, 0x0000}`.
  Target rewrite: `{0x1C08, 31, 37, 0x0000}` — result cid unchanged, so the table
  stays sorted and the row count stays 161. **Inherently count-neutral.**
- ⚠️ **Darkbright's stock text is FOUR clauses, and only one of them is a cls
  record.** Retiring the cls2 record alone left piercing and the Defense-Position
  flip live in-game (user-reported, 2026-08-03 — my first pass shipped that bug):

  | # | stock clause | where it lives | action |
  |---|---|---|---|
  | 1 | cannot be SS'd except by Fusion Summon | `card_type` = Fusion Effect Monster | **KEEP** — this *is* clause 2 |
  | 2 | piercing battle damage | membership of the piercing list `0x0226D764` (49 sorted u16, index 23 @ `0x0226D792`) | dropped → phantom `0x1B8E` |
  | 3 | changes to Defense Position after attacking | **code**, not data: two literal pools | dropped → phantom `0x1994` |
  | 4 | if destroyed, destroy 1 opponent monster | cls2[274] `0x022775B4` | retired (slot3 = never-activate) |

  **Finding the code sites needed a u32 scan, not a u16 one:** `0x1C08` is also
  the Thumb encoding of `adds r0,r1,#0`, so a halfword scan returns 900+ false
  positives. Scanning for the *word* `0x00001C08` gives exactly three sites —
  `0x021C62DC`, `0x022526D8` (both literal pools) and `0x022775B4` (the cls2 row).
- **The "switches to Defense Position after attacking" family** is a cid-comparison
  chain over `{0x14D6 Spear Dragon, 0x1993 Axe Dragonute, 0x1C08 Darkbright,
  0x1DA6 Arcana Force EX - The Dark Ruler, 0x237F Power Breaker}` — every member a
  card with that behaviour. It is evaluated in two functions, loading the cids
  from the pools above (loaded by the `ldr` at `0x021C6150` and `0x02252542`).
  The chain is an **ordered** binary search (`bgt`/`bge`/`beq`), so the phantom
  must occupy the same slot in the ordering: `0x1994` sits strictly between
  `0x1993` and `0x1DA6` and belongs to no card, so the other four still route
  correctly. Both edits are count-neutral by construction (overwrite, not delete).
- `0x0226ED14` is Darkbright's row in the stride-4 **leave-trigger mask** table
  (`0x0226EC20`, 151 rows, `{u16 cid, u16 mask}`; mask `0x0400`), the partner of
  the cls2 record. **Left alone deliberately** — the cls2 slot3 never-activate
  stub is the engine's own documented "cannot activate" contract, so zeroing the
  mask as well would be an extra unproven edit for no gain.
- `0x0226C0D0` / `0x0226C136` are `adds r0,r1,#0` false positives inside code.
- Darkbright has **exactly one** record across all four cls tables:
  **cls2[274] @ `0x022775B4`** =
  `{cid 0x1C08, +04 0x02204899, +08 0x021D882D, +0C 0x0224A115, +10 0, +14 0x02234DA5}`.
  (`0x0224A115` is the ubiquitous `movs r0,#2; bx lr` activation stub.)
- Darkbright is already `card_type = Fusion Effect Monster` ⇒ **clause 2 is free**
  (its stock description even says "cannot be Special Summoned except by Fusion
  Summon").
- Card face before → after: Level 6 → **8**, ATK 2000 → **2500**, DEF 1000 →
  **2000**; DARK / Warrior unchanged. Name "Elemental Hero Escuridao" is 24 B and
  fits every language's name slot in place (the tightest is German at 24 B); the
  190 B description fits every desc slot (382–740 B) in place. `bin2.pac` stays
  byte-identical in size (+0 B).
- The cls2 record is **retired, not deleted**: slots are zeroed and slot3 (the
  activation condition) is pointed at the engine's own never-activate stub
  `0x0224A110` (`movs r0,#0; bx lr`). The cid stays, so cls2 remains sorted at
  697 records — the count is a hard-coded immediate, so a row cannot be removed.

### card_prop geometry

- `nds_card_prop.bin` = 8-byte header + 4305 records × 8 bytes, indexed by the
  **rank of the cid** in the sorted cid list (not by cid value).
  *Proof:* the level field (raw bits 42–45, matching the `get_level` getter)
  reproduces ygoprodeck for **2435 / 2438** name-matched monsters.

---

## Chain verification (2026-08-03)

Combined build: **all 28 patches applied**, exit 0 →
`data/over_the_nexus/working/rom_all_patches.nds`.
`verify()` on every shipped module against that ROM: **17 PASS, 1 no-verify()
(darksoul), 2 FAIL — both pre-existing and NOT caused by this patch.**

**Escuridao's total overlay-3 footprint is 17 bytes**, measured by diffing
`rom_escuridao.nds` against the clean ROM:

```
0x02270F2E..0x02270F31   4B   the two fusion material halfwords
0x022775B8..0x022775C0   9B   cls2 slots 1-3
0x022775C8..0x022775CB   4B   cls2 slot 5
```

`bin2.pac` stays exactly the same size (+0 B) — every name/desc write is in-place.

### FAIL 1 — `patch_sea_lancer`: Cyberdark cls1[588..590]
Sea Lancer clones the Cyberdark equip resolver and guards that its **clone source
rows are untouched**. In the combined ROM those rows have **shifted down by one**:

| row | clean | combined |
|---|---|---|
| 588 `0x022897F4` | cid 0x1AAE | cid **0x1AAF** |
| 589 `0x0228980C` | cid 0x1AAF | cid **0x1AB0** |
| 590 `0x02289824` | cid 0x1AB0, res 0x022186E5 | cid 0x1AB0, res **0x02206139** |

So some **other** patch in the chain does a cls1 **insert**, and Sea Lancer's
hard-coded row indices 588/589/590 drift. A real composition bug worth fixing —
Sea Lancer should look its rows up **by cid**, not by index — but unrelated to
Escuridao: in `rom_escuridao.nds` all three rows still hold the clean values.

### FAIL 2 — `patch_shooting_quasar`: blast-radius + PART I
Quasar's `verify()` diffs against the **clean** ROM and whitelists only its own
regions, so it necessarily fails on any combined build. The bytes it flags —
`0x021984EC` and `0x021A69CC` — are **Safe Zone's** documented PART C / PART E
detour sites, and `0x022482B2` is Boggart's; both patches run in the same chain.
Structural and by design, not a regression.

## Ruled Out

- **"Clone The Shining's ATK gain"** is not a shortcut. Its two `0x2161` byte
  hits (`0x021B632A`, `0x021DA37E`) both disassemble to
  `movs r1,#0x61; lsls r1,r1,#6` (= 0x1840) — byte-pattern false positives.
  Its only per-card records are cls2[504] `0x02278B44` (leave-field trigger) and
  the off-field-selection registry row `0x022744F0` (its banish-recovery clause).
- Absolute Zero's `0x02250DAE` / `0x02250E4C` hits are likewise false positives
  (`subs r1,r0,#7` against the literal `0x13B4`).
- **Absolute Zero's cls2 record is NOT its ATK gain.** Disassembled this session:
  cls2[432] `0x02278484` slot1 `0x022048FD` is six instructions —
  `bl 0x0224AA20; bl 0x021CF310` — i.e. its *leave-field board wipe*; slot2
  `0x021D886D` is just a zone-mask query `0x021D6E40(…, 0x1012)`. So neither
  Absolute Zero nor The Shining carries its continuous ATK gain in a cls record;
  the mechanic is the delta-table engine described above.
- The **variable-ATK engine** (function ending `0x021B4B2C`, literal pool
  `0x021B4B30`) is the **wrong family** for clause 3: its pool is exactly the
  "ATK *becomes* N × count" cards — Chaos Necromancer `0x16C3`, Helios Trice
  Megistus, The Wicked Eraser, Fortune Lady Wind, Gradius' Option, Winged Kuriboh
  LV9, Arsenal Bug, Stronghold, Option Token. Escuridao "*gains* N for each" is a
  delta, not a replacement. (Still worth reading as a counter-example.)
- Chaos Necromancer / Gren Maju Da Eiza / Megarock Dragon / The Calculator have
  **no cls records at all**, confirming the dynamic-ATK mechanic lives outside
  the cls dispatch.

### ⚠️ A wrong claim I made and then killed — `ygo_tools/reference_files/nds_card_prop.bin` is STALE

Mid-session I concluded "`card_prop.bin` contains no attribute or race field;
`ERA2_LAYOUT` is wrong". **That was wrong**, and it is recorded here so the
correction survives.

- Cause: I analysed `ygo_tools/reference_files/nds_card_prop.bin`, which
  **differs from the ROM's real `bin2.pac/card_prop.bin` in 4368 of 34448 bytes**
  (first divergence at record 157). It is stale. Same length and a valid
  8-byte-header / rank-of-cid framing, so every structural self-check still
  passed — which is exactly why it fooled me.
- A second, independent error compounded it: I hand-wrote a race table in
  Konami sort order (1 = Warrior …) instead of using the repo's
  `ERA2_RACE_MAP` (1 = Dragon, …, 15 = Warrior).
- **Ground truth, measured against the ROM's own card_prop over the 2438
  name-matched monsters: `ERA2_LAYOUT` attribute (bits 38–40) = 99.96%, race
  (bits 49–53) = 99.96%, level (42–45) = 99.96%.** `ERA2_ATTRIBUTE_MAP` and
  `ERA2_RACE_MAP` are both correct. Bit 54 is a separate flag (race values
  reappear as 32 + race).
- So `patch_bulk_card_props.py`'s `attribute_encoded` / `race` edits are **fine**
  — the earlier "suspect" warning is withdrawn.
- The other two oracles are clean: `reference_files/nds_overlay_3.bin` is
  **byte-identical** to the ROM's overlay 3 (checked this session), so every
  fusion-engine fact above stands. `arm9.bin` is the decompressed main section
  and is validated by the KB's 119 passing proofs.
- **Rule for the next session: read `card_prop` out of the ROM's `bin2.pac`, not
  from `reference_files/`.** The stale file should be regenerated or deleted.

---

# SESSION 2 — 2026-08-03 (clause 3): the delta-table route is the WRONG FAMILY

Everything above about the rider/delta-table engine is still true as *description*,
but it is **not where clause 3 belongs**, and three claims above are now corrected.

## Confirmed (proved THIS session, static, on the committed ov3 oracle)

### ⚠️ CORRECTION 1 — delta table 2 is `0x0226E480`, **113** rows (not `0x0226E4BC`/103)

The consumer's own immediates are `movs r2,#0x71` @`0x021B60BA` and `movs r3,#6`
@`0x021B60BC`, with the base literal at `0x021B6184` = **`0x0226E480`**.
`0x0226E480 + 113*6 = 0x0226E726`, and it abuts table 1's end `0x0226E47E`
exactly. The old base was **10 rows too high**; the walk that produced it started
mid-array. `fusion.atk_delta_tables` still PASSes only because a subrange of a
sorted array is still sorted — the proof must be tightened to pin the base to the
consumer's literal.

### ⚠️ CORRECTION 2 — no delta-table card has a *continuous* "for each" gain

I read the printed text (ygoprodeck cache) of **all 51 `±1`-sentinel rows** of
table 2. Every one is **activated or event-driven**: "Once per turn: … gains N ATK
for each", "during the Damage Step only", "gains N ATK for each card banished this
way". **Not one** is "gains N ATK for each X currently in your GY".

That is structural, not incidental: the amount is `node+4`, written once at
`riders.attach_api` time and only *read* by the walker at `0x021B5FD0`. Routing
Escuridao through it would freeze its ATK at whatever the GY held when the node
was attached. **The delta-table/rider route is rejected for clause 3.**

### ⚠️ CORRECTION 3 — "The Shining / Shining Flare Wingman are unimplemented" is WRONG

The Ruled Out section above concluded they are unimplemented because they are in
neither delta table. They are **fully implemented** — continuous per-card stat
effects simply do not live in those tables:

| card | cid | arm | leaf | what the leaf does |
|---|---|---|---|---|
| E-HERO Shining Flare Wingman | `0x1943` | `0x021B4F40` | — | E-HERO count ×300 |
| E-HERO Shining Phoenix Enforcer | `0x1A00` | `0x021B502E` | `0x021B58DC` | `0x021B18E0(side, 0x0202381D)` ×300 |
| E-HERO The Shining | `0x2161` | `0x021B534C` | `0x021B5CFE` | `0x021B1950(side, 0x0202381D)` over the **banished** array ×300 |
| Masked HERO Goka | `0x236B` | `0x021B535A` | `0x021B5DC4` | `0x021B18E0(side, 0x02023975)` ×**100** |

### THE REAL HOME: the continuous stat engine `0x021B44C0`

`0x021B44C0(r0=side, r1=zone, r2=out_struct, r3=flag)` recomputes one card's live
stats into a 0x28-byte out struct. Called by 11 sites including the ATK getters
`0x021B8014` (reads `out+0x10`) and `0x021B803C` (reads `out+0x14`); `0x021B3CE8`
is its sibling. Because it is re-run on every stat query, anything routed through
it is continuous **by construction**.

* frame: `[sp+0x0C]` = side, `[sp+0x30]` = side×0xB3C, `[sp+0x50]` = zone×0x14
* live regs in the cid chains: **`r2` = the cid**, **`r4` = the running bonus**,
  `r7` = the out struct (`+0x02` cid, `+0x10`/`+0x14` the two stat accumulators,
  clamped to ≥0 at `0x021B79DE`, epilogue `0x021B79F2`)
* continuation `0x021B5E6E`, reached by the ARMv4T **`bl`-as-long-branch** idiom
  from 72 sites (it never returns)
* multiplier tails, all ending `muls r1,r0,r1 ; adds r4,r4,r1 ; bl 0x021B5E6E`:
  **`0x021B557E` = ×100**, `0x021B575E` = ×300, `0x021B5552` = ×500
* counters: **`0x021B18E0(side, thunk)`** = monsters in own **GY** matching a
  set-code thunk (`0x021B18EC` is the body; `0x02029E60` gates to monsters, then
  `blx thunk`); `0x021B1950` = same over the **banished** array with a
  distinct-names pass; `0x021ACFE8(side, thunk, exclude_zone, faceup)` = on-field
  zones 0..0xA; `0x021A3054(side, idx, code)` = player counters
* generic `has_set_code(cid, idx)` = **`0x020240D8`** (ptr table `0x0209D0D8`,
  `idx >= 0x70` rejected). The "Elemental HERO" thunk `0x0202381C` tail-calls the
  u16 binary search `0x02022E14(cid, 0x0209CFE4, 58)`.

**Method:** the chains encode cids as `base ± imm` with the base in a register
(`thumb.stack_based_switch`), so they were mapped with a **CFG walk + constant
propagation**, not by grepping. 182 `cmp r2,<const>` arm sites recovered.

### 16 of the 182 arms are PHANTOM — provably dead ov3 code

Checked every arm cid against the ROM's own `bin2.pac/card_prop.bin` (4305
records, 4305 distinct cids, max `0x24E8`). These arm cids **do not exist as
cards**, so their `cmp r2,<cid>` can never match and their leaves are unreachable:

`0x0E4C 0x0E51 0x0E56 0x0EC1 0x1091 0x133D 0x1789 0x1827 0x1860 0x190F 0x194C
0x19BE 0x19D1 0x19D3 0x1B6B 0x1BCF`

Free code bytes per leaf (stopping at the first branch target or literal-pool
word): `0x0EC1`→**44 B @0x021B54E0**, `0x1827`→30 B, `0x194C`→30 B, `0x19BE`→28 B,
`0x1789`→22 B, `0x133D`→16 B, `0x190F`→12 B, `0x1BCF`→10 B @`0x021B5AAA`.
This is a reusable, all-duel-modes ov3 scratch pool that needs **no cave and no
canary** — the cids simply are not in the game.

### The routing site for `0x1C08`

CFG walk with `r2 = 0x1C08` lands on **`0x021B512C`**, the `bl 0x021B5E6E`
fall-through of the `0x1C09` (E-HERO Magma Neos) equality node:

```
021B5122  subs r0,#0x59      ; r0 = 0x1C62 - 0x59 = 0x1C09
021B5124  cmp  r2,r0
021B5126  bne  0x021B512C
021B5128  bl   0x021B5ADE    ; Magma Neos leaf
021B512C  bl   0x021B5E6E    ; <-- 0x1C08 exits here
```

`0x021B512C` has **exactly one predecessor** (`bne` @`0x021B5126`), and
`0x021B54E0` has exactly one (the dead `bl` @`0x021B4CC4`). Verified by a
predecessor scan over the whole function.

## Ruled Out (this session)

* **Sacrificing a live card's arm.** All 166 non-phantom arms belong to real
  cards; the only ordering-safe neighbours of `0x1C08` are `0x1BE7` Botanical Lion
  and `0x1C09` E-HERO Magma Neos. Unnecessary — the phantom blocks are free.
* **Retuning the `0x1BCF` phantom arm's cid to `0x1C08`.** Its node only ever sees
  the interval `(0x1B6B, 0x1BE7)`; `0x1C08` is routed away by `bgt` @`0x021B5090`
  and would never reach it. Its *leaf* is still usable as scratch — its *slot* is not.
* **A generic `bl 0x021B5E6E` hijack into the ov5 cave.** ov5 is evicted by
  overlay 41 in a puzzle, so the branch would land in ov41 data — a **freeze**,
  not an inert effect. Any ov5 host here would need a native ov3 cid gate anyway.
* **The ov3 BSS cave** (`ov3_cave.py`) — already dead, see
  `notes/ov3-cave-findings.md` canary round 2 (the engine wipes ov3's BSS over its
  original extent). Not re-attempted.

## Shipped (2026-08-03) — PART E of `patch_escuridao.py`

Two edits, **30 bytes**, both overlay 3, no cave / cls record / delta row / phantom:

| # | site | change |
|---|---|---|
| E1 | `0x021B512C` | `BL 0x021B5E6E` → `BL 0x021B54E0` (4 B; only the low halfword differs) |
| E2 | `0x021B54E0` | 28 B of Thumb-1 over the dead phantom-`0x0EC1` leaf (44 B free) |

```
021B54E0  ldr  r0,=0x00001C08
021B54E2  cmp  r2,r0
021B54E4  bne  0x021B54F0
021B54E6  ldr  r0,[sp,#0xc]        ; side
021B54E8  ldr  r1,=0x0202381D      ; "Elemental HERO" thunk
021B54EA  bl   0x021B18E0          ; count E-HERO monsters in own GY
021B54EE  b    0x021B557E          ; x100 -> r4 -> continuation
021B54F0  bl   0x021B5E6E          ; the displaced original
021B54F4  .word 0x00001C08 / 0x0202381D
```

Every path ends in a call that never returns, so the block needs no epilogue, and
the **non-match path performs exactly the `BL` it displaced** — so every other cid
is bit-identical, including on the block's other (dead) inbound edge `0x021B4CC4`.

Measured blast radius, `rom_escuridao.nds` vs the clean ROM: **8 runs, 53 bytes**
(`0x021B512E` 2 B + `0x021B54E0` 28 B are clause 3; the rest are clauses 1+2 as
before). `bin2.pac` +0 B.

**Verification status:**
* `patch_escuridao.verify()` — **14/14 PASS** on both the single-card ROM and the
  combined build. It re-proves each build that cid `0x0EC1` is absent from all
  4305 `card_prop` records, i.e. that the host really was dead code.
* Combined chain (all 28 patches, exit 0): **19 PASS, 0 FAIL** after fixing the two
  long-standing verify() bugs below. `patch_wonder_wand` still ERRORs but is
  **commented out of `PATCHES`** (apply_all_patches.py:730), so it verifies an
  unapplied patch; `patch_bulk_ydcs` fails at *import* ("Main deck must have between
  40 and 60 cards, got 15") — neither is a chain result.
  `patch_hyper_librarian` / `patch_mystic_piper` / `patch_tour_guide` used to print
  "VERIFY OK" and then `return None`, so any harness treating a falsy return as
  failure invented three phantom FAILs (it cost a round here). All three now
  `return True` and are annotated `-> bool`; failure still raises AssertionError,
  and their `--verify` CLI paths ignore the return, so nothing else changed.

### The two pre-existing verify() FAILs — diagnosed and FIXED (2026-08-03)

**`patch_sea_lancer`: a real by-index bug.** Its guard read the Cyberdark clone
sources at hard-coded cls1 rows 588/589/590. Measured against the clean ROM, the
whole cls1 array is shifted **up by one** in a combined build: `combined[N] ==
clean[N+1]`, first divergence at row 71, because **`patch_ninishi` count-neutrally
DELETES the phantom record `0x1140`**. The Cyberdark rows themselves were never
touched — same cids, same slot1 `0x022186E5`, now at 587/588/589. Fixed by looking
them up **by cid**, matching on the `(cid, resolver)` PAIR because cid `0x1AB0`
owns two cls1 rows (the second has resolver `0x02206139`). Also note the old code
read the cid as `<H`; cls records are cid-first **u32** (`dispatch.cls_tables`).

**`patch_shooting_quasar`: two wrong invariants, both standalone-only.**
1. *PART I* asserted Boggart's site `0x022482B2` equals the CLEAN ROM. But Boggart
   legitimately owns that site and writes `BL -> CAVE_BOGGART 0x0239A160` there in
   any chained build (measured). The invariant Quasar actually needs is "**I** did
   not clobber it", so it now accepts pristine-or-Boggart's-own-BL and fails only
   on an unrecognised value — which is what a genuine detour collision looks like.
2. *Blast radius* diffs all of overlay 3 against the clean ROM and whitelists only
   Quasar's own sites, so every other patch's bytes are "stray" (22404 of them).
   It cannot attribute strays in a chained build, so it now reports **SKIP** there
   instead of FAIL, detecting a chained build from populated non-Quasar ov5 cave
   slots (minefield / boggart / mystic_piper). On a standalone
   `rom_shooting_quasar.nds` those slots are zero and the check runs unchanged.
* KB: 165 facts, **140 PASS / 0 FAIL**; allocation ledger in sync (180 B of the
  ov3 dead-code pool still free).

⚠️ **Do not edit build inputs while `apply_all_patches` is running.** A first
chain build produced a ROM in which Escuridao's own rows read as *native* — a
partial artifact that looks like a real regression. Always let a build finish, and
capture its stdout (`python -u ... > log 2>&1`) so an abort is visible.

## ✅ CLAUSE 3 IS IN-GAME CONFIRMED (user, 2026-08-03)

**Elemental HERO Escuridao is COMPLETE — all three clauses shipped and confirmed.**
The static case (the CFG walk, the single-predecessor proof at `0x021B512C`, and
the 90 shipped cards that depend on the same engine) is now backed by live play.

That also confirms, on the live path, the design decision this session turned on:
routing a continuous "for each" gain through **`0x021B44C0`** rather than the
ATK/DEF delta tables. The delta-table route would have snapshotted the count.

The one-shot probe `scratch/gdb_escuridao_clause3.py` was written but is not
needed for this card; keep it as the template for the **next** stat-engine effect
(it breaks at the block, checks `r2 == 0x1C08`, and cross-checks the GY sweep's
return against a count it computes independently from RAM).

---

## Open Questions

*(none blocking — the clause-3 mechanism is resolved; see SESSION 2 above.)*

---

## Next Experiment

**E0 (housekeeping).** Regenerate or delete
`ygo_tools/reference_files/nds_card_prop.bin` — it is stale (see the Ruled Out
section) and silently corrupts any analysis built on it. The runtime accessor is
`0x0202A084(cid)` = `[[0x02121A5C]+0x10]+0x38 + rank*8`, rank from `0x02029E1C`;
its record layout is exactly `ERA2_LAYOUT`.

Clause 3 stands at: **engine found, per-card amount not yet located.** Two things
are still needed, in this order.

**E1 — find the ROUTING and the COUNT.** *(static, do first.)* Two sub-questions,
both inside the function that owns the pool word `0x02219B2C`:
1. **What routes a cid to a multiplier arm?** Find the `ldr` that loads
   `0x02219B2C` and read the switch above `0x02219AE0`. ⚠️ Per
   `[[thumb-stack-based-switch-footgun]]` these switches encode cids as
   `base ± imm` with the base in `[sp,#n]`, so a register-only reading reports the
   WRONG arm — confirm with GDB, do not infer.
2. **Where does `[r5+0x34]` (the count) get filled?** That is the per-card
   "count Equip Spells in your GY" step; the E-HERO equivalent is a GY sweep
   applying the set-code thunk `0x0202381C`.
Also check whether **100** already exists as a multiplier arm (Gustaph's own text
is 100/Equip, yet the arms found so far are 200/400/500 — so either an unseen arm
supplies 100, or `[r5+0x34]` is not a raw count and the units differ). Resolve
that before assuming a multiplier.

**E2 — GDB (only after E1).** One-shot session, port **3333**, **active normal
duel** (not a puzzle — overlay 41 evicts ov5), overlays 3 and 5 resident. Break at
the attach tail `0x02219B0E` and at the delta lookup `0x021B610C` with Chaosrider
Gustaph face-up and Equip Spells accumulating in the GY. **Expected:** at
`0x02219B0E`, `r2` = `0x16C4`, `[sp]` = 100 × (equips in GY); at `0x021B6118`,
`r5` = `0x16C4` and `[sp+0x80]` = that same amount. This settles the units
question and proves the node is re-attached as the GY changes (a *continuous*
gain must be refreshed — if the node is written once at summon time, the value
would freeze and a different hook is needed). Connect **once**, arm everything,
collect in a single wait window, write to a file. Never probe, never reconnect.

**Then implement** (two parts, both count-neutral):
1. **A delta row for `0x1C08`** with `atk = +1`. Both tables are sorted with
   **hard-coded counts** (`0x6F` / 103), so this must be a count-neutral insert —
   drop a phantom cid to make room and keep the array sorted, exactly as
   `tg_table.py` / `xsaber_table.py` do. Register the phantom in `PHANTOM_CLAIMS`
   (Escuridao already owns `0x1994` and `0x1B8E` there).
2. **An attach for cid `0x1C08`, kind 3, param = 100 × (E-HEROes in own GY)** via
   `riders.attach_api` `0x021C479C`. Preferred: an in-place arm retune if E1 finds
   a spare one; otherwise an ov5 cave stub. Take the next address from the **live**
   `CAVE_FREE` in `ov5_cave.py` (never hardcode), add the `CAVE_*` constant, run
   `... knowledge.check_allocations --emit`, Thumb-1 only
   (`effect_verify.assert_thumb1_only`). ⚠️ An ov5 stub is **normal duels only**,
   so the ATK gain would be inert in puzzles while clauses 1+2 keep working
   everywhere — an in-place ov3 edit avoids that and is worth the extra RE.

**Also pending:** the card description currently prints all three clauses,
including the unimplemented ATK gain. If clause 3 is abandoned, trim the last
sentence so the printed text matches behaviour (the house rule — see
`patch_vylon_element`). Card art is still Darkbright's.
