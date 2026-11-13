# The Gates of Dark World — findings (session 2026-08-25)

Printed text (`scratch/ygoprodeck_cache.json`, id 33017655) — **Field Spell**:

> All Fiend-Type monsters gain 300 ATK and DEF. Once per turn: You can banish 1
> Fiend-Type monster from your Graveyard; discard 1 Fiend-Type monster, then
> draw 1 card.

Clauses:
1. **Continuous**: all Fiend-Type monsters (BOTH players, on the field) gain
   300 ATK and 300 DEF.
2. **Once per turn ignition**: cost = banish 1 Fiend-Type monster from YOUR GY;
   effect = discard 1 Fiend-Type monster, then draw 1 card.

**STATUS: ✅ DONE. BOTH CLAUSES SHIPPED AND IN-GAME CONFIRMED BY THE USER --
clause 1 on 2026-08-25, clause 2 on 2026-08-26 ("Perfect! Ship it!").**

## ⚠️ PART E2 ADDED 2026-08-27 — the card was not a "Dark World" card
**Found in-game while testing Snoww, Unlight of Dark World** (whose clause 1 adds
1 "Dark World" card from the Deck): the user reported *"i cannot search gates of
dark world because that itself isnt in the dark world archtype table yet"*.

**Cause.** "Is a Dark World card" means membership of the ARM9 set-code list
`0x0209CA06` (set code 0x0F, thunk `0x020238B5`, `setcode.dark_world_table`) --
a donor does NOT inherit it from the new card's NAME. After PART E dropped the
donor Colosseum `0x1C8B` from Gladiator Beast, it was in **no set-code table at
all**, so no archetype effect could ever see it.

**Fix — PART E2**, folded into PART E's existing ROM round-trip (a 129 MB save;
do it once). Count-neutral swap over the phantom `0x0EC9` (no card_prop, so its
membership was inert), inserting `0x1C8B` at index 14, between Renge `0x1C18` and
Dark World Grimoire `0x1D25`:

```
before: 0EC9 1961 1965 1966 1967 1968 1969 196A 1970 1973 1B3D 1B3E 1B3F 1B5A 1C18 1D25
after : 1961 1965 1966 1967 1968 1969 196A 1970 1973 1B3D 1B3E 1B3F 1B5A 1C18 1C8B 1D25
```

The list is **binary-searched** with a hardcoded count (`MOV R2,#0x10`
@`0x020238B8`), so the edit preserves both the length and STRICT sort order --
both asserted before writing and re-checked in `verify()` (six new E2 checks,
including that the six native Dark World monsters are still members).
A Spell in this list is normal (Grimoire, Dealings, Lightning, Gateway are all
members) and cannot make the card findable by Scarr, whose criteria row filters
card type MONSTER.

Allocation pool `dw_setcode_table` registered in `check_allocations.py`.
⚠️ `0x0EC9` is ALSO one of the seven cids in the effect-discard arm `0x021D185C`
(`event.dark_world_discard_arm`) -- a different table, unaffected.

**IN-GAME CONFIRMED BY THE USER 2026-08-27** ("all good!", against the three-item
retest: the card is now fetchable by Snoww's "Dark World" search, Gates itself
still activates with its banish -> discard -> draw, and Fiends still get +300).

⚠️ THE LIST NOW HAS NO PHANTOM LEFT. A future card wanting Dark World membership
must displace a REAL card. Registered as pool `dw_setcode_table`.

> **Reading order note.** The `## Confirmed` section below is the log in the
> order it was discovered, so it still contains the FIRST design, which used
> **Yami 0x10F5** as the donor. That design was **superseded** once the card-face
> constraint was measured (see `## CARD-FACE CONSTRAINT`). The shipped donor is
> **Colosseum 0x1C8B**; the shipped addresses are in `## SHIPPED (2026-08-25)`.
> The Yami analysis is kept because it is still the best Field Spell donor in the
> ROM for any card with a short name.

## Confirmed (this session)
- KB proofs green at session end: **305 facts, 272 PASS / 0 FAIL /
  33 UNVERIFIED** (was 300/268/0/32 on arrival, before this card's 5 new facts).
- "The Gates of Dark World" is **not** in the ROM (`scratch/cid_to_name.json`,
  4305 names) => donor required.
- **`0x021B26F4` is THE FIELD-SPELL STAT ENGINE.** Bounds `0x021B26F4` (push
  {r3-r7,lr}; sub sp,#0x10) .. `0x021B2B6E` (pop {r3-r7,pc}). Every one of the
  12 cid literals in its pool `0x021B29A4..0x021B29D0` is a Field Spell (Neo
  Space, Rising Air Current, Yami, Chorus of Sanctuary, A Legendary Ocean,
  Harpies' Hunting Ground, Wetlands, Colosseum, Closed Forest, Morphtronic Map,
  phantom 0x2348, Temple of the Six). Signature:
  `(r0=affected monster record, r1=field-spell side, r2=field-spell zone,
    r3=monster side, [sp+0x28]=monster zone, [sp+0x2C]=out ATK, [sp+0x30]=out DEF)`;
  r4 = running ATK bonus, r5 = running DEF bonus, returns 1 iff it changed
  anything. Switch key = `0x021A36EC(side, zone)` = the field spell's cid.
- **It is called from the live stat recompute**: the only two BL callers are
  `0x021B5F84` and `0x021B7BD2`, and `0x021B5F84` lies inside
  `stat.recompute` 0x021B44C0..0x021B79F2. So anything routed through it is
  **continuous by construction** (same argument as Escuridao).
- **`[r6+0x08]` is a RACE bitmask = `1 << ERA2_race_code`** (game_constants
  `ERA2_RACE_MAP`), and `[r6+0x0C]` is the ATTRIBUTE bitmask. Proven by a closed
  cross-check: all six classic field-spell arms decode bit-exactly onto their
  printed race sets —
  Forest `0x3C00` = Insect|Beast|Beast-Warrior|Plant; Wasteland `0x244` =
  Zombie|Rock|Dinosaur; Mountain `0x90002` = Dragon|Winged Beast|Thunder;
  Sogen `0x9000` = Beast-Warrior|Warrior; Umi `0x84120` =
  Sea Serpent|Fish|Aqua|Thunder with `0x90` = Pyro|Machine at -200;
  **Yami `0x40008` = Fiend(bit 3)|Spellcaster(bit 18)** with `0x20000` =
  Fairy(bit 17) at -200.  ==> **Fiend = bit 3 = `0x00000008`.**
- **Jurassic World `0x1AA7` is clause 1 verbatim with a different race**
  ("All Dinosaur-Type monsters gain 300 ATK and DEF"). Its arm `0x021B28C2`
  tests race bit 9 (Dinosaur) then falls into a **+300/+300 tail at
  `0x021B28CC`**: `adds r0,r1,#0 ; subs r0,#0xd4 ; subs r1,#0xd4 ;
  adds r4,r4,r0 ; adds r5,r5,r1 ; b 0x021B2B48` — requires `r1 = 0x200` on
  entry (300 = 0x200 - 0xD4; the compiler reused the race-mask constant as the
  amount source).
- ⚠️ **SUPERSEDED (donor changed to Colosseum 0x1C8B — see CARD-FACE CONSTRAINT).
  Still true and still useful: Yami is the best Field Spell donor in the ROM for
  any card whose name fits 4 bytes.** Across the whole
  ARM9 + overlay-3 image, cid 0x10F5 has **exactly one** aligned occurrence: the
  literal-pool word at `0x021B29AC` that drives its own field-spell arm. It has
  no cls0 / cls1 / cls2 / cls3 record and no criteria-registry row (swept all
  four tables per `dispatch.cls_table_selector`). It is already the correct card
  type (Field Spell), so activation / field-zone / deck-editor handling is native.
- **Yami's switch arm is `0x021B28A0`**, reached only via the 6-entry jump table
  at `0x021B2764` (entry 5, offset 0x13A). The arm occupies
  `0x021B28A0..0x021B28B5` (11 halfwords / 22 bytes) and the **only** branch
  landing anywhere in it is its own `beq 0x021B28AC` at `0x021B28A6` — so the
  whole block is exclusively Yami's and free to rewrite. Nothing else targets
  the `0x021B28CC` tail either.
- Full field-spell arm map (cid -> arm): Forest 0x10F0->0x021B2856,
  Wasteland 0x10F1->0x021B2866, Mountain 0x10F2->0x021B2872,
  Sogen 0x10F3->0x021B287C, Umi 0x10F4->0x021B2888, **Yami 0x10F5->0x021B28A0**,
  Chorus of Sanctuary 0x1323->0x021B294C, Gaia Power 0x1344->0x021B28D8,
  Umiiruka 0x1345->0x021B28EE, Molten Destruction 0x1346->0x021B28FA,
  Rising Air Current 0x1347->0x021B2906, Luminous Spark 0x1348->0x021B2912,
  Mystic Plasma Zone 0x1349->0x021B291E, A Legendary Ocean 0x150B->0x021B292C,
  Necrovalley 0x159D->0x021B296C, Harpies' Hunting Ground 0x183F->0x021B28B6,
  Neo Space 0x1A77->0x021B2986, **Jurassic World 0x1AA7->0x021B28C2**,
  Venom Swamp 0x1BFC->0x021B2A1E, Colosseum 0x1C8B->0x021B2A3E,
  Acidic Downpour 0x1D21->0x021B2938, Realm of Light 0x1DCA->0x021B2A6A,
  Wetlands 0x1DCB->0x021B2A8C, Morphtronic Map 0x1F6D->0x021B2AAE,
  Ojama Country 0x204A->0x021B2ACE, Closed Forest 0x2189->0x021B2AE4,
  Amazoness Village 0x2318->0x021B2AFC, phantom 0x2348->0x021B2B10,
  Temple of the Six 0x247E->0x021B2B34.

## ⚠️ SUPERSEDED first design (donor Yami) — NOT what shipped
This is the block as it would have gone into **Yami's** arm. It was never
applied: the donor changed to Colosseum for the name slot. Kept because the
shape is identical and it documents Yami's arm geometry. **The shipped bytes and
addresses are in `## SHIPPED (2026-08-25)` below.**

```
021B28A0  b168   ldr  r1,[r6,#8]      ; race bitmask     (unchanged)
021B28A2  2008   movs r0,#8           ; Fiend = bit 3
021B28A4  0842   tst  r0,r1           ;                  (unchanged)
021B28A6  d03f   beq  0x021B2928      ; not a Fiend -> no change
021B28A8  2102   movs r1,#2
021B28AA  0209   lsls r1,r1,#8        ; r1 = 0x200
021B28AC  e00e   b    0x021B28CC      ; -> shared +300/+300 tail
```
`0x021B28AE..0x021B28B5` become unreachable dead bytes (left as-is).
All seven halfwords are Thumb-1. No cave slot, no phantom cid, no cls record,
no registry row, no shared table => **cannot collide with any shipped patch**,
and being overlay-3 it also works in puzzles.

## Ruled Out
- Field spells are **not** keyed by a cid table: scanning ARM9 + ov3 for u16
  occurrences of the 12 classic field-spell cids finds no cluster (Sogen and
  Umiiruka have zero occurrences anywhere). The dispatch is the ungreppable
  stack-based switch in `0x021B26F4`.
- Field spells are **not** in the ATK/DEF delta tables `0x0226E1E4` (111 rows) /
  `0x0226E480` (113 rows) — no field-spell cid appears in either.
- **Dark World Grimoire 0x1D25 is NOT a template for clause 2.** Recalled text
  said "banish 1 Fiend from GY to discard then draw"; the printed text is
  "During your End Phase, if you discard a monster(s) because you had more cards
  than your hand size limit: target 1 of those; Special Summon it." Checked
  against ygoprodeck_cache before acting on it.

## CLAUSE 2 SESSION (2026-08-25b) — 3DS FIRST

### CONFIRMED: the 3DS ships The Gates of Dark World, cid 0x25F3
`3ds_extract/partition0/romfs/duel/card/CARD_Indx_E.bin` record **4764**,
`CARD_Prop.bin[4764] & 0x3FFF = 0x25F3`, name `The Gates of Dark World`,
description **verbatim** the printed text:

> All Fiend-Type monsters gain 300 ATK and DEF. Once per turn: You can banish 1
> Fiend-Type monster from your Graveyard; discard 1 Fiend-Type monster, then
> draw 1 card.

So there is an **authoritative Konami implementation of clause 2 in the same cid
space**. Checked FIRST, per CLAUDE.md, before any further NDS RE.

### CONFIRMED: cls3 slot roles for the NDS templates (record dump, this session)
cls3 rows are 24 B at `0x02279D74`: `+00 u32 cid`, then the five slots of
`dispatch.cls_slot_roles` (+04 resolver, +08 on-field predicate, +0C activation
condition, +10 cost, +14 target declaration).

```
cls3[508] cid=1FB5 Fabled Valkyrus  +04 022065B9  +08 0  +0C 021F0BDD  +10 021E4EED  +14 0
cls3[538] cid=204A Ojama Country    +04 02207191  +08 0  +0C 021F0BDD  +10 021E7245  +14 02235605
```

So for Valkyrus ("Once per turn: You can discard 1 Fiend monster; draw 1 card")
the **discard is the COST (slot4 0x021E4EED)** and the **draw is the RESOLVER
(slot1 0x022065B9)**. Its single criteria row (handler 0x0223CB19 = HAND) serves
the cost.

### CONFIRMED: `0x021F0BDD` is NOT a once-per-turn gate — it is a per-cid slot3 dispatcher
Disassembled from the ov3 oracle:

```
021f0bdc  push {r4,r5,r6,lr}
021f0bde  adds r5,r0,#0          ; r5 = descriptor
021f0be0  ldrh r0,[r5]           ; r0 = key at desc[+0] (the cid)
021f0be2  adds r6,r1,#0
021f0be4  ldr  r1,[pc,#0x28]     ; = 0x0226FAFC
021f0be6  movs r2,#0x92          ; 146 rows
021f0be8  movs r3,#0xc           ; 12 B stride
021f0bea  bl   0x02022e44        ; generic binary search
021f0bee  adds r4,r0,#0
021f0bf0  beq  0x021f0c0c        ; no row -> return 0
021f0bf2  ldr  r2,[r4,#4] ; blx  ; cond(desc, r6)
021f0bfa  cmp  r0,#0 ; beq       ; 0 -> return 0
021f0bfe  ldr  r2,[r4,#8] ; blx  ; act(desc, r6)  -> its return value
```

**Secondary per-cid table `0x0226FAFC`, 146 rows x 12 B, sorted by cid**, row =
`{u16 cid, u16 pad, u32 cond_fn, u32 act_fn}`. 58 of the 776 cls3 records use
`0x021F0BDD` as slot3. Rows for the templates:

```
sec[67] cid=1FB5 cond=0x021F0355 act=0x021F069D
sec[75] cid=204A cond=0x021F0355 act=0x021F03B5
```

`0x1C8B` (Colosseum, our donor) is **NOT** in that table -> with slot3 =
0x021F0BDD the donor's activation condition would return 0 (never activatable).
So the hypothesis in the previous handoff ("+0C is the shared once-per-turn
slot") is **REFUTED as stated**: +0C is the activation-condition slot generally
(that part is `dispatch.cls_slot_roles`), and 0x021F0BDD specifically is a
cid-keyed indirection the donor cannot use without a row in 0x0226FAFC.

### ⭐ CONFIRMED: the 3DS's two criteria rows for 0x25F3, and both handler identities
3DS main criteria registry `0x686CBC` (2100 x 12, `{u16 cid, u16 filt, u32 handler,
u32 word}`) — cid 0x25F3 owns **exactly two consecutive rows**:

```
[1462] {0x25F3, 0xFFFF, handler 0x004A9EFC, word 0x18000002}   <- row index 0
[1463] {0x25F3, 0xFFFF, handler 0x004B1A90, word 0x18000002}   <- row index 1
```

`word 0x18000002` = NDS `{flags 0x0002, extra 0x1800}` = the Fiend race filter,
identical to Dark Necrofear / Fabled Valkyrus. Handler identities:

- `0x004B1A90` == NDS `0x0223CA11` = **select from GY** (CLAUDE.md line 247;
  re-measured this session: 96 3DS cids vs 70 NDS cids, **66 shared**, Jaccard
  0.660 — the residue is 3DS-only cards).
- `0x004A9EFC` == NDS **`0x0223CE65`** = **select from HAND** — a NEW equivalence,
  established this session by cid-set correlation (8 of the 9 NDS rows shared;
  next-best NDS candidate scores 0.040). Both member lists read as hand
  selection: Allure of Darkness, Common Charity, Cards from the Sky, Moray of
  Greed, Lighten the Load, Fabled Raven, Tri-Blaze Accelerator, Star Blast, and
  on the 3DS side also Dark Smog and Trance Archfiend — both `word 0x18000002`,
  both printed "discard 1 Fiend-Type monster".
  ⚠️ NOT `0x0223CB19` (which CLAUDE.md line 247 maps to 3DS `0x004ABE08`); that
  is a *different* hand selector. Measured: `0x004ABE08` vs `0x0223CB19` share
  only 1 cid (Jaccard 0.077), so **that line of CLAUDE.md is at best weak** —
  see Ruled Out.

**So the authoritative Konami implementation is: row 0 = HAND/Fiend, row 1 =
GY/Fiend.** Two rows, in that order.

### ⭐⭐ CONFIRMED: LIST B IS THE TWO-ROW GROUP, and its selector is `param & 0x10000000`
This is the mechanism that `dispatch.simorgh_row_offset_is_a_bespoke_switch_arm`
said a donor could not have. It was only ever half the story: the fact documents
**list A** and the fall-through leaf, and never decoded **list B**.

Disassembled from the ov3 oracle inside `0x02243B9C`:

```
02243c02  ldr  r1,[pc,#0x200]    ; = 0x02271314  (LIST B)
02243c04  adds r0,r5,#0          ; r5 = cid
02243c06  movs r2,#0x1b          ; 27 entries
02243c08  bl   0x02022e14        ; generic binary search
02243c0c  cmp  r0,#0
02243c0e  beq  0x02243c1c        ; not in list B -> the big per-cid switch
02243c10  movs r0,#1
02243c12  lsls r0,r0,#0x1c       ; r0 = 0x10000000
02243c14  tst  r0,r4             ; r4 = param
02243c16  beq  0x02243c1a
02243c18  b    0x02243ec6        ; -> movs r4,#1   ROW 1
02243c1a  b    0x02243eec        ; -> movs r4,#0   ROW 0
```

Leaf semantics confirmed by disassembly: `0x02243EC6 = movs r4,#1`,
`0x02243EEC = movs r4,#0`; then at `0x02243EEE..0x02243F06` the code walks r6
**back to the leftmost row with the same cid** and forms `r2 = leftmost + r4`.
So `r4` is a genuine ROW OFFSET off the leftmost record.

**LIST B RULE: row = (param & 0x10000000) ? 1 : 0.**
(LIST A rule, already in the KB: row = (param != 0) ? 1 : 0, at 0x02243BFA.)

### ⭐ CONFIRMED: lists A and B are exactly "the cids with a two-row criteria pair"
Dumped both lists against a row-count census of the registry:

- LIST B `0x02271314`, 27 entries — **every one has exactly 2 rows.**
- LIST A `0x0227134C`, 59 entries — every one has exactly 2 rows **except** the
  two Speed Spells `0x0D7A`/`0x0D81`, which have 0.
- Registry-wide: 118 of 1259 distinct cids have >1 row (108 x2, 9 x3, 1 x4).

**Every NDS card that owns one HAND-family row AND one GY-family row is in list
B**, with the HAND row FIRST — the same order as the 3DS's Gates rows:

```
1F2A Genesis Dragon    HAND 0223CB65 / GY 0223CBB1
1FFD Lava Dragon       HAND 0223CA51 / GY 0223C9D1
2076 Koa'ki Crusader   HAND 02241471 / GY 0223CBC9
210F Koa'ki Rooklord   HAND 02241471 / GY 0223CA2D
2273 Chaos Goddess     HAND 0223CB65 / GY 0223C9D1
234F (PHANTOM)         HAND 0223CB19 / GY 0223CA11   extra 0x6000 on both
23E1 Ceremonial Mirror HAND 02241471 / GY 0223CBC9
204A Ojama Country     <- in list B, 2 rows, and a FIELD SPELL
```
(the exceptions — Dark Simorgh 0x1E5A x4, Koa'ki War Arms, Sea Panther,
Ghoulungulate, Jupiter — are in neither list and use bespoke switch arms.)

### ⭐ THE TEMPLATE IS OJAMA COUNTRY 0x204A
It is a **Field Spell**, **in list B**, with **2 criteria rows**, and a
**once-per-turn ignition whose cost selects from one zone and whose effect
selects from the other** — structurally clause 2 with the two zones swapped.
cls3[538] `{+04 0x02207191, +08 0, +0C 0x021F0BDD, +10 0x021E7245,
+14 0x02235605}`.

### ⭐⭐⭐ CONFIRMED: THE COMPLETE TWO-ZONE RECIPE — it is PURE DATA, no code
The remaining half of the mechanism: **who passes a param with bit 28 set.**

`0x02243B9C` has exactly **three** callers (BL scan over arm9+ov3):
`0x02243FB6`, `0x02243FEE`, `0x02244080`. The first two
(`0x02243FA8(side, cid, param)` = the list-zone enumerator, `0x02243FE0` = its
counting sibling) forward their own `param` argument untouched. The third,
`0x0224406C`, **derives** it: `bl 0x02234E78` then passes the result.

`0x02234E78(desc)` is the PARAM PROVIDER, and it is a chain of five sorted cid
lists (disassembled from the ov3 oracle):

| list | base | count | returns |
|---|---|---|---|
| L1 | `0x022710E2` | 17 | `desc[+0x0C]` |
| **L2** | **`0x02271104`** | **28** | **`0x10000000`** (`movs r0,#1 ; lsls r0,r0,#0x1c` @0x02234E9E) |
| L3 | `0x022710B2` | 12 | `desc[+0x14]` |
| L4 | `0x0227109C` | 11 | `desc[+0x16]` |
| L5 | `0x022710CA` | 12 | `desc[+0x18]` |

**L2 `0x02271104` is the ROW-1 LIST.** `0x10000000` is precisely the bit list B
tests. Its 28 members are Dark Grepher, Genesis Dragon, Tragoedia, Ancient Fairy
Dragon, Lava Dragon, Vanguard of the Dragon, One for One, Morphtronic Repair
Unit, Fake Feather, **Ojama Country 0x204A**, Supersonic Skull Flame, Skull
Flame, the Koa'ki Meirus, Gae Dearg, Knight of the Red Lotus, Black Brutdrago,
Iron Core Specimen Lab, The Fabled Peggulsus, Chaos Goddess, Infernity Launcher,
Ceremonial Mirror Meditation, Dark Flattop, Master Hyperion + Speed Spell - One
for One. **22 of the 27 list-B cids are also in L2.**

And the off-field slot5 template consumes it — disassembled at `0x02235604`:

```
02235604  push {r3-r7,lr}
02235606  adds r5,r0,#0          ; r5 = descriptor
02235608  ldrb r2,[r5,#2]        ; side
0223560a  ldrb r1,[r5,#6]
0223560c  adds r4,r2,#0 ; eors r4,r1
02235610  bl   0x02234e78        ; <-- THE PARAM PROVIDER
02235616  adds r3,r0,#0
  ...
02235628  ldrh r1,[r5]           ; cid
0223562a  adds r0,r4,#0          ; side
0223562c  adds r2,r3,#0          ; param  <-- 0x10000000 for an L2 cid
0223562e  bl   0x02243fa8        ; the list-zone enumerator
```

#### THE RECIPE (all four items are count-neutral data edits)
To give a donor a once-per-turn ignition that selects from TWO different zones:

1. **Two consecutive criteria rows** in `0x022713C4`
   (row 0 = the zone the COST selects from, row 1 = the zone SLOT5 selects from).
2. **cid in LIST B `0x02271314`** (27 entries, count immediate `movs r2,#0x1b`
   @`0x02243C06`) => row = `(param & 0x10000000) ? 1 : 0`.
3. **cid in L2 `0x02271104`** (28 entries, count immediate `movs r2,#0x1c`
   @`0x02234E94`) => slot5's enumerator call resolves to **row 1**.
4. A **cls3 record** with `+14 = 0x02235605` (the off-field target template),
   `+10` = a cost step, `+04` = the resolver, `+0C` = an activation condition.

Ojama Country 0x204A satisfies all four and is the working reference:
criteria rows **[924]** `{filt 0x000D, hnd 0x0223CB85, flags 0x000E, extra 0x0000}`
(hand, "Ojama" set code 0x0D) and **[925]** `{filt 0x000D, hnd 0x0223C9ED,
flags 0x0002, extra 0x0001}` (GY). Its cost `0x021E7244` passes
`r2 = -(1 if [0x0229AAFC+0x74] else 0)` to `0x0224B9F0` — i.e. **0 => row 0** on
the pass that matters, so the COST reads row 0 and SLOT5 reads row 1.

**=> Clause 2 needs NO new Thumb for the selection machinery.** The only code
question left is the resolver (discard + draw) and the once-per-turn gate.

### THE FOUR UNKNOWNS -- ALL RESOLVED (2026-08-25b, static, from the ov3 oracle)

#### (2) SLOT5's off-field template is ZONE-AGNOSTIC -- but no shipped card pairs it with HAND
`0x02235604` never names a container. Sub-step 2 at `0x0223569E` calls
`0x0219C534` to read the PICK's zone code at runtime and branches on it:
`<= 0x0A` -> the board recorder `0x022347B0(desc, side, zone)`, else the list
recorder `0x02234880`. The container is decided entirely by the criteria row's
HANDLER, loaded at `0x02243F64..0x02243F6E` (`r3 = [0x022713C8 + idx*12]`) and
called by `0x02243F38`. Its prompt is fixed: `0x0219A818(side, 0x5E)`; its picker
is `0x0219C430(side, 6, cid)`.

⚠️ **CENSUS CAVEAT.** 315 cls records use `+14 = 0x02235605`. Classifying each by
its cid's criteria-row handler families: 146 GY-only, 129 unclassified, and
**11 with a HAND row -- but in every one of those 11 the HAND row is row 0 (read
by the COST) and the GY row is row 1 (read by slot5).** So the engine has never
been observed driving slot5 at the HAND container. Zone-agnostic by disassembly;
unexercised in practice.

#### (1) THE GY-BANISH COST IS `0x021E56E9`, AND IT DEFAULTS TO EXACTLY 1
Found by correlating every slot4 pointer against the owning card's PRINTED text:
`0x021E56E9` has 17 named users and **16 of them are "banish ... from your
Graveyard"**, 14 with a GY criteria row. All 18 records are cls3. It is a thin
wrapper:

```
021e56e8  push {r3,r4,r5,lr}
021e56ee  bl 0x021e5318      ; the SELECT machine
021e56f2  cmp r0,#0 ; beq -> return 0   (abort the activation)
021e56fa  bl 0x021e5060      ; the BANISH action
021e56fe  movs r0,#1         ; cost paid
```

`0x021E5318` opens with `movs r4,#1 ; movs r6,#1` and then runs an ungreppable
per-cid switch **whose every arm only overrides r4 = the NUMBER of cards to
banish** (2, 5, 3, 0x20, or a computed count) and sets r6 = 0. **A cid with no
switch arm keeps r4 = 1** -- "banish exactly 1". Our donor has no arm, so the
native cost banishes exactly one card with no code at all.

Reference shape: **Psychic Lifetrancer 0x1EDC**, cls3[454]
`{+04 0x02206139, +08 0, +0C 0x021F09E1, +10 0x021E56E9, +14 0}`, criteria row
[779] `{0xFFFF, 0x0223CA11, 0x0002, 0xA800}` -- extra high byte 0xA8 >> 3 = 21 =
Psychic, printed "Once per turn, you can remove from play 1 Psychic-Type monster
from your Graveyard to gain 1200 Life Points." **Swap 0xA8 for 0x18 (Fiend) and
that row IS clause 2's cost.**

#### ⭐ THE CRUX: WHICH STEPS CAN READ DIFFERENT ROWS
`0x021E5318` state 1 (`0x021E5486`) calls **`0x02234E78` (the param provider)**
and hands the result to the picker `0x0219C430(side, count+6, cid)` -- so the
native GY-banish cost reads **the same row slot5 would**. Two steps can only
land on different rows when one of them passes **its own** param:

| slot4 family | param | row |
|---|---|---|
| `0x021E56E9` GY banish | **provider** `0x02234E78` | same as slot5 |
| `0x021E7245` Ojama Country | own, `-(1 if [0x0229AAFC+0x74] else 0)` -> 0 | row 0 |
| `0x021E4EED` Fabled Valkyrus discard | own, **`movs r2,#0` @0x021E4F40** | row 0 |

That is exactly how Ojama Country works: its cost hardcodes param 0 (row 0 =
hand) while slot5 takes 0x10000000 from the provider (row 1 = GY).

#### (4) THE DRAW PRIMITIVE IS CONFIRMED -- `0x021D12F4(side, count)`
Was UNVERIFIED and inherited from memory. Now proven from a shipped resolver:
Fabled Valkyrus's slot1 `0x022065B8` ends

```
022065e4  cmp r5,#0 ; ble -> skip
022065e8  adds r0,r4,#0      ; side  = desc[+2] ^ desc[+6], flipped by 0x021D2D40
022065ea  adds r1,r5,#0      ; count
022065ec  bl 0x021d12f4      ; THE DRAW
```

`0x022065B9` is therefore a **generic "draw N" resolver**, with N from
`0x02206304(desc)` -- a binary search (`0x02022E44`) over a **189-row x 4 B
per-cid table** returning the s16 at `[row+2]`. A donor needs a row there (or the
0x02206336 fallback) to draw 1.

#### (3) THE ONCE-PER-TURN SLOT3 IS `0x021F09E1` (candidate, needs one more check)
Shared by 12 of the 18 `0x021E56E9` users, including every "Once per turn: you
can banish ..." one. It reads `(side, desc[+3])` and calls the **attached-effect
node walker `0x021A1430`** -- the kind<6 family from `otn-attached-effect-rider`
-- returning 1 only when the walker finds NOTHING, then chains `0x021F0948`.
i.e. "no used-this-turn rider is attached". ⚠️ NOT yet confirmed: the literal
handed to the walker as r2, and where the rider is stamped after use.

#### THE L2 PROBLEM AND ITS ANSWER
Getting a second row therefore needs the donor to look like an L2 member. L2
`0x02271104` has **no phantom to evict** (all 28 are real cards) and **cannot
grow in place** -- the bytes at `0x0227113C` are the next sorted cid list, packed
solid. Two clean ways out:

- **RELOCATE L2.** Its base has **exactly ONE aligned reference in the whole
  arm9+ov3 image: the pool word at `0x02235104`.** So a 29-entry copy in 58 B of
  free ov3 + repoint that word + bump `movs r2,#0x1c` @`0x02234E94` to `#0x1d`.
- **HOOK THE L2 SEARCH (preferred).** Retarget the single `bl 0x02022E14` at
  `0x02234E96` -- the L2 lookup and nothing else -- to a cid-scoped ov3 stub that
  reports "found" for `0x1C8B` and otherwise tail-calls the native search. This
  is the shipped Azure-Eyes PART G pattern, ~20 B, and it lands in the **30 B of
  dead space this card already owns** in its own field arm
  (`0x021B2A4C..0x021B2A69`). ov3, so it works in puzzles too.

### ⭐ THE ONCE-PER-TURN MACHINERY IS `0x0FB6`, AND THE BANISH COST STAMPS IT ITSELF

Found by correlating every slot3 pointer against printed text, then scanning the
slot3 pool for calls to the attached-effect node walker `0x021A1430`:

- **84 of the 1004 distinct slot3 functions call `0x021A1430`, covering 665 of
  the 3107 cls records**, and **30 of them pass the same r2 literal
  `0x00000FB6`** -- the top six alone (`0x021F01C1` x115, `0x021F03B5` x112,
  `0x021F0419` x62, `0x021F05A9` x62, `0x021F069D` x37, `0x021F0221` x27) are all
  100%-once-per-turn families. So **`0x0FB6` is the "already used this turn"
  rider key** (its numeric collision with Time Wizard's cid is a coincidence --
  it is a sentinel in the rider key space).
- The **stamp** is `0x021C479C(side, zone, key, kind, extra)`: 24 sites load
  `0x0FB6` and immediately call it.
- ⭐ **One of those 24 sites is inside the banish cost's own tail.**
  `0x021E5060`, the function `0x021E56E9` calls after a successful selection, is
  *only* a stamp:

```
021e5060  push {r2,r3,r4,lr}
021e5064  bl   0x021d2c1c        ; guard
021e506a  beq  0x021e507c
021e506c  movs r0,#0 ; str r0,[sp]   ; 5th arg = 0
021e5070  ldrb r0,[r4,#2]        ; side
021e5072  ldrb r1,[r4,#3]        ; zone
021e5074  ldr  r2,[pc,#8]        ; = 0x00000FB6   (pool 0x021E5080)
021e5076  movs r3,#2             ; kind 2  -> the 0x021A1430 walker family
021e5078  bl   0x021c479c        ; ATTACH the rider
021e507c  movs r0,#1
```

**So slot4 = `0x021E56E9` gives the pick, the banish, the count of 1, AND the
once-per-turn stamp -- all native, all free.**

### ⭐⭐ CONFIRMED: SLOT4 AND SLOT5 HAVE THE IDENTICAL ABI, AND THE SUB-STEP COUNTER IS RESET BETWEEN THEM
This is what makes the design work without chaining two state machines by hand.

The two invokers are byte-identical apart from the record offset --
`0x0224AE5E: ldr r2,[r0,#0x10]` vs `0x0224AE92: ldr r2,[r0,#0x14]` -- both
`push {r3,r4,r5,lr}; bl 0x0224A118; ldr r2,[rec,#slot]; blx r2` with
`(r0 = desc, r1 = event)` and "absent slot => return 1".

And in the activation state machine `0x02217F80` the slot4 block
(`0x02217F8E..0x02217FC0`, gated on `desc[+7]`, getter `0x0224AE70`, invoker
`0x0224AE50`) and the slot5 block (`0x02217FC4..0x02217FFA`, gated on `desc[+8]`,
getter `0x0224AEA4`, invoker `0x0224AE84`) are the same shape, and **each one
ends with `str r1,[r4,#0x7c]` with r1 = 0 -- i.e. `[0x0229AAFC+0x7C]`, the
sub-step counter, IS RESET TO ZERO before the machine advances.** Return protocol
read off the same code: **0 = yield (call me again), > 0 = finished, < 0 = ABORT
the activation.**

=> **A slot4-family cost machine dropped into slot5 starts cleanly at state 0.**
The stock image never does this (the five slot pointer pools are pairwise
disjoint, per `dispatch.cls_slot_roles`) -- that is an observation about Konami's
codegen, not a constraint. **This is the one genuinely novel step in the build
and the thing most worth watching in the first in-game test.**

### ✅ THE SETTLED CLAUSE 2 DESIGN (2026-08-25b)

Row order **row 0 = HAND, row 1 = GY** -- the order the 3DS ships for `0x25F3`.

| slot | value | which row it reads | what it does |
|---|---|---|---|
| +04 slot1 | `0x022065B9` | draw-count table `0x02206304` | **draw 1** |
| +08 slot2 | `0` | -- | -- |
| +0C slot3 | a `0x0FB6` reader (`0x021F01C1` candidate) | -- | **once per turn** |
| +10 slot4 | `0x021E56E9` | provider -> **row 1 = GY** | **banish 1 Fiend from GY** + stamp `0x0FB6` |
| +14 slot5 | `0x021E4EED` | own param `movs r2,#0` -> **row 0 = HAND** | **discard 1 Fiend** |

Both criteria rows are **byte-identical copies of rows already shipped and
working in this ROM**:

```
row 0  {0xFFFF, 0x0223CB19, 0x0002, 0x1800}   == Fabled Valkyrus 0x1FB5's row
row 1  {0xFFFF, 0x0223CA11, 0x0002, 0x1800}   == Dark Necrofear  0x1466's row
```

⚠️ Row 0 deliberately uses **`0x0223CB19`, not the `0x0223CE65` the 3DS names**:
we are reusing Valkyrus's exact cost function `0x021E4EED`, so we reuse the
handler that function is shipped paired with. Matching the working NDS pairing
beats matching the 3DS's handler choice, because the 3DS's effect script is
different code.

**Parts:**

- **G** two count-neutral criteria-row inserts for `0x1C8B` into `0x022713C4`
  (drop 2 phantom rows -- **NOT** `0x234F`'s pair, `patch_sea_lancer` draws on it).
- **H** LIST B `0x02271314`: evict phantom `0x234F`, insert `0x1C8B` sorted
  (rotate, count immediate untouched).
- **I** L2 semantics for `0x1C8B`: retarget the single `bl 0x02022E14` at
  `0x02234E96` (the L2 lookup and nothing else) to a cid-scoped ov3 stub -- the
  Azure-Eyes PART G pattern, ~20 B, into the **30 B of dead space this card
  already owns** at `0x021B2A4C..0x021B2A69`. ov3, so puzzles are fine.
- **J** cls3 record for `0x1C8B`, count-neutral (drop a phantom cls3 row).
- **K** a draw-count entry so `0x02206304` yields 1 (or prove the fallback does).

**Total new Thumb: the ~20 B L2 stub. Everything else is data.**

### ✅ SLOT3 SETTLED: `0x021F01C1` IS THE BARE ONCE-PER-TURN GATE
115 records, six instructions, no other condition:

```
021f01c0  push {r3,lr}
021f01c2  adds r1,r0,#0
021f01c4  ldrb r0,[r1,#2]      ; side
021f01c6  ldrb r1,[r1,#3]      ; zone
021f01c8  ldr  r2,[pc,#0x10]   ; = 0x00000FB6   (pool 0x021F01DC)
021f01ca  bl   0x021a1430      ; the rider walker
021f01ce  cmp  r0,#0 ; bne 0x021f01d6
021f01d2  movs r0,#1 ; pop     ; no rider -> ACTIVATABLE
021f01d6  movs r0,#0 ; pop     ; rider present -> CANNOT ACTIVATE
```

It returns **1**, which per `dispatch.cls_slot_roles` means "activatable but
slot2 must find a target" -- and our slot2 is 0. **28 of its 115 users already
have slot2 == 0**, so that pairing is well precedented and needs no slot2.

### ✅ DRAW COUNT SETTLED: table `0x022704A4`, 189 x 4, `{u16 cid, s16 count}`
Sorted-unique. **Fabled Valkyrus 0x1FB5 -> 1.** Value histogram: 1 x112,
2 x58, 3 x8, -1 x7, -2 x3, -3 x1 (negatives = the opponent draws, via the side
flip at `0x022065DE`). The donor `0x1C8B` is **absent**, and a miss falls through
to a long per-cid switch at `0x02206336` rather than a default of 1, so **an
entry is required**.

### ✅ PROVEN: THE DONOR TAKES THE DEFAULT ARM OF THE BANISH-COUNT SWITCH
The `0x021E5318` switch is **register-only** -- scanned `0x021E5318..0x021E5428`
for stack access and found **zero** `[sp]` references (only the function's own
push/pop), so `thumb-stack-based-switch-footgun` does not apply and the switch is
safely simulable. Simulated every cid `0x0D00..0x24FF` with the same
raise-on-unmodelled discipline as `patch_reborn_tengu._res_switch_leaf`:

| leaf | meaning | cids |
|---|---|---|
| `0x021E53BA` | r4 = a zone-record field | 1 (0x18F8) |
| `0x021E53D4` | **r4 = 2** | 9 |
| `0x021E53D8` | **r4 = 5** | 1 (The Beginning of the End) |
| `0x021E53DC` | **r4 = 3** | 1 (Bazoo the Soul-Eater) |
| `0x021E53E0` | r4 = board count | 1 (Infernal Flame Emperor) |
| `0x021E53F0` | **r4 = 0x20** | 1 (Survival Instinct) |
| `0x021E53F4` | stamp-now leaf | 1 (Splendid Rose) |
| `0x021E5418` | r4 = `0x021AD870()` | 1 (Searing Fire Wall) |
| `0x021E5422` | **DEFAULT, r4 = 1** | 6128 |

**The simulator validates 6-for-6 against printed text** -- Bazoo "up to 3" -> 3,
Freed "2 LIGHT" -> 2, Enishi "2 Six Samurai" -> 2, Beginning of the End "5 DARK"
-> 5, Survival Instinct "any number" -> 0x20, and Lifetrancer / Jurrac Titano /
Laval Judgment Lord / Hundred Eyes / Master Hyperion "banish 1" -> 1.

⭐ **`0x1C8B` -> `0x021E5422`, the DEFAULT leaf, r4 = 1.** Clause 2's cost banishes
exactly one card with no code.

### ✅ THE FOUR COUNT-NEUTRAL SLOTS, ALL UNCLAIMED
Phantom = no `card_prop` record (checked against the real 4305 cids read from
`bin2.pac`), cross-checked against every claim in `check_allocations.py`:

| table | insert index for 0x1C8B | drop | note |
|---|---|---|---|
| criteria `0x022713C4` (1388 x 12) | **592** | rows **287 `0x178C`** and **288 `0x1795`** | adjacent, both unclaimed -> ONE memmove of 289..591 down by 2 |
| cls3 `0x02279D74` (776 x 24) | **340** | record **267 or 268, cid `0x1AF0`** | `0x1AF0` owns TWO records, so dropping one cannot orphan a card (same argument sea_lancer used for 0x234F) |
| draw-count `0x022704A4` (189 x 4) | **91** | row **70 `0x1B1A`** | unclaimed phantom |
| LIST B `0x02271314` (27 x 2) | **2** | phantom **`0x234F`** (index 24) | rotate 2..23 right by one; count immediate untouched |

Registry-wide there are **100 phantom criteria rows**, **82 phantom cls3
records** and **14 phantom draw-count rows**, so none of these is a scarce slot.

⚠️ `0x234F` is claimed by `sea_lancer` in the **`populate_table`** pool (it drops
0x234F's second criteria row). LIST B membership is a **different resource** and
needs a **new `membership_list_b` pool** in `check_allocations.py`. The two do not
conflict -- and removing a phantom from list B that no longer has two rows is
strictly *more* consistent than leaving it.

### PRE-BUILD RISK CHECKLIST (CLAUDE.md)
1. **Per-cid gates referencing the donor** -- `PROVEN`. Clause 1 enumerated all
   10 aligned occurrences of `0x1C8B` and retired the four live ones (PARTS B-E).
   New for clause 2: the donor takes the **DEFAULT** arm of the banish-count
   switch `0x021E5318` (above), and the draw-count switch `0x02206336` is never
   reached because the table hit returns early at `0x02206334`.
   ⚠️ `ASSUMED`: the per-cid prompt switch inside `0x021E4EEC`
   (`0x021E4F12..0x021E4F34`) -- the donor is none of its three literals, so it
   shows the default prompt string `0x29`. Cosmetic only; not yet read.
2. **The zone each step searches** -- `PROVEN`. The criteria row's HANDLER selects
   the container (`counter.criteria_handler_selects_container`), and both rows are
   **byte-identical copies of shipped working rows**: Valkyrus's HAND row and
   Dark Necrofear's GY row.
3. **Donor name / description blob lengths** -- `PROVEN`, and already shipped:
   clause 1 PART F wrote the name and description in all 8 languages into
   Colosseum's 40/36/40/39/40-byte slots.
4. **Where the once-per-turn flag is stamped** -- `PROVEN`. `0x021E5060`, the tail
   of the banish cost, calls `0x021C479C(side, zone, 0x0FB6, kind 2, 0)` at
   `0x021E5078`; slot3 `0x021F01C1` reads it back through `0x021A1430`.

**Remaining `ASSUMED` / unexercised, both to watch in the first duel:**
- a slot4-family function (`0x021E4EED`) placed in **slot5** -- ABI proven
  identical and the sub-step counter proven reset between the blocks, but the
  stock image never does it;
- the prompt string shown by the discard step (cosmetic).

### 🔨 CLAUSE 2 BUILT (2026-08-25b) -- **AWAITING IN-GAME TEST**

`.venv-1/Scripts/python.exe -m otn_enhanced.cards.gates_of_dark_world`
-> `data/over_the_nexus/working/rom_gates_dark_world.nds`
sha256 `587cc5caf0e9d2dbbd0466905accca136d7defed5b373d00aee3aac3eff268e7`
**verify() 39/39 PASS**, KB `311 facts: 278 PASS 0 FAIL 33 UNVERIFIED`,
`check_allocations` `[OK] no ov5 overlaps, no phantom double-claims, no ov3
overlaps, ledger in sync`.

**IDEMPOTENT, byte-for-byte:** re-applying the module on top of its own output
produces the identical sha256 and all five clause-2 parts report "already
present". That is what `apply_all_patches` will do, so the chain step is safe.

Parts as built:

| part | edit | result |
|---|---|---|
| **G** | criteria registry `0x022713C4` | dropped phantoms `0x178C` (287) + `0x1795` (288), inserted the donor's pair at **590/591**; still 1388 sorted |
| **H** | LIST B `0x02271314` | evicted phantom `0x234F`, inserted `0x1C8B` at index **2**; still 27 strictly sorted, count imm untouched |
| **I** | L2 membership | 28 B stub @`0x021B2A4C`, `bl` @`0x02234E96` retargeted `0x02022E14` -> stub |
| **J** | cls3 `0x02279D74` | dropped one of phantom `0x1AF0`'s two records (267), inserted at **339**; still 776 sorted |
| **K** | draw-count `0x022704A4` | dropped phantom `0x1B1A` (70), inserted `{0x1C8B, 1}` at **90**; still 189 sorted |
| **F** | card face | description updated to the full printed text, all 8 languages, in place |

The cls3 record, read back from the built ROM:

```
cls3[339] cid=1C8B  +04 022065B9  +08 00000000  +0C 021F01C1
                    +10 021E56E9  +14 021E4EED
```

The PART I stub, disassembled **from the output ROM** (never the assembler):

```
021b2a4c  00b5   push {lr}
021b2a4e  044b   ldr  r3,[pc,#0x10]   ; 0x021B2A60 = 0x00001C8B
021b2a50  9842   cmp  r0,r3
021b2a52  01d1   bne  0x021b2a58
021b2a54  081c   adds r0,r1,#0        ; "found": r1 = the list base, non-NULL
021b2a56  00bd   pop  {pc}
021b2a58  024b   ldr  r3,[pc,#8]      ; 0x021B2A64 = 0x02022E15
021b2a5a  9847   blx  r3              ; tail-call the engine's own search
021b2a5c  00bd   pop  {pc}
021b2a5e  0000   (pad)
021b2a60  .word 0x00001C8B
021b2a64  .word 0x02022E15
02234e96  7df7d9fd  bl 0x021b2a4c     ; the retargeted L2 lookup
```

All Thumb-1 (`assert_thumb1_only`), 28 B of the 30 B clause 1 left dead, and
clause 1's block above it is untouched (`b 0x021b28cc` still the last
instruction at `0x021B2A4A`).

#### ⚠️ COMPOSITION: cls3 IS ANCHORED BY ROW INDEX BY TWO OTHER PATCHES
`patch_shiens_dojo` drops row 223 / inserts at 233; `patch_sea_lancer`
hard-asserts the donor cid at `cls3[527]`. A count-neutral swap shifts only the
rows strictly between the drop index and the insert position, here **268..339**:

- 223, 233 -- below the span, `patch_shiens_dojo` unaffected
- 527 -- above the span, `patch_sea_lancer` unaffected
- 334 -- **inside** the span: `patch_maiden_eyes_of_blue`'s phantom `0x1C80`
  moves to 333. **Harmless** -- that module finds it by full RECORD CONTENT
  (`_count_neutral_swap`'s `r == drop`) and verifies by cid, never by index.

Dropping a phantom ABOVE the insert instead (the next are 710/711/712) would
shift 340..709 upward and move sea_lancer's hard-coded 527 -- strictly worse.
`_drop_and_insert` also now asserts that **no cid's multi-row group is split** by
an edit (`find_event_handler` reaches a second record via `leftmost + 1`).

### 🎮 IN-GAME TEST #1 OF CLAUSE 2 -- 2026-08-25, reported by the user

**User's exact words:**

> "Okay I was able to use the effect to banish a Dark World card, and discard 1
> and draw 1.
>
> However 2 bugs:
> 1) I can activate the card without a darkworld in the GY (which causes a
> freeze) due to no targets
> 2) When I discard a card with gates of the dark world, it is still discard for
> cost and not for effect because it should be triggering my dark world
> monsters. Use the same subroutine that cards like Darkworld Lightning uses to
> discard cards. See .ml2 and .ml3 (the silva should have special summoned from
> being discarded but it did not!)
>
> I can confirm that the remaining regression controls had no regressions so
> clause 1 is fine."

Clarified by the user afterwards: at the freeze the Graveyard held **no
Fiend-Type monster at all** (the card filters on Fiend, not on the "Dark World"
archetype -- every Dark World monster is a Fiend but not conversely, and this
was the plain no-candidate case).

#### ✅ CONFIRMED WORKING (in-game, user-confirmed 2026-08-25)
- The whole happy path: activate -> banish 1 Fiend from the GY -> discard 1
  Fiend from the hand -> draw 1.
- ⭐ **The one unexercised step WORKS.** A slot4-family cost machine
  (`0x021E4EED`) placed in **slot5** ran correctly and produced its prompt. The
  ABI/counter-reset reasoning in
  `dispatch.slot4_and_slot5_are_interchangeable_machines` is confirmed on the
  live path -- upgrade that fact's caveat.
- PART I works: slot4 read criteria **row 1** (GY) while slot5 read **row 0**
  (hand), i.e. the cid-scoped L2-membership stub does make the param provider
  return `1 << 28` for the donor and nothing else changed.
- PART K works: exactly 1 card drawn.
- **CLAUSE 1 IS REGRESSION-FREE**, including the two controls that had never been
  run: Yami `0x10F5` and Jurassic World `0x1AA7`.

#### 🐞 BUG 1 -- activatable with no legal banish candidate, then FREEZE
slot3 `0x021F01C1` is the BARE once-per-turn gate: it tests only the `0x0FB6`
rider and nothing else. Nothing anywhere checks that the GY holds a Fiend, so the
effect is offered, the cost's selection machine opens on an empty candidate list,
and the game hangs.

⚠️ Note this is exactly the `dispatch.cls_slot_roles` return-code semantics biting:
`0x021F01C1` returns **1** = "activatable but SLOT2 must find at least one legal
target" -- and **our slot2 is 0**. The 28 native records that pair
`slot3 = 0x021F01C1` with `slot2 == 0` evidently never need a candidate test.
FIX DIRECTION: give slot3 a candidate-existence test as well (the counting
sibling `0x02243FE0` is what Release from Stone's slot3 uses for exactly this),
or supply a slot2 predicate.

#### 🐞 BUG 2 -- the discard is a COST, so Dark World monsters do not trigger
`0x021E4EED` is Fabled Valkyrus's **cost** step, and a cost discard does not post
the event that "If this card is discarded to the Graveyard by a card effect"
monsters listen for. Sillva, Warlord of Dark World was discarded and did **not**
Special Summon itself.

This is a REAL BUG, not an acceptable deviation: the printed text puts the
discard AFTER the semicolon, so it is part of the EFFECT and must trigger.

FIX DIRECTION (the user's instruction): use the discard subroutine that **Dark
World Lightning** uses ("Target 1 Set card on the field; destroy that target,
then discard 1 card" -- its discard is post-semicolon, i.e. an effect discard).
Savestates `.ml2` / `.ml3` were supplied.

### ⭐⭐ THE EFFECT-DISCARD PATH, AND WHY THE COST PATH CANNOT TRIGGER (2026-08-25c)

⚠️ **RULES NOTE, corrected by the user:** a **cost** discard does **NOT** trigger
Dark World. The cards that do -- Dark World Dealings, Dark World Lightning,
Dragged Down into the Grave, Graceful Charity, Card Destruction -- all discard as
an **effect**. Hand Destruction does **not**, because it *sends* from the hand
rather than discarding. So the engine's two paths are not an implementation
detail to paper over: they are the rules distinction, and clause 2's discard is
post-semicolon, i.e. an EFFECT.

**The two paths, both disassembled this session:**

| | cost discard (what we shipped) | effect discard (what we need) |
|---|---|---|
| entry | slot4/slot5 `0x021E4EED` | `0x022598A0(side, count, f2, f3)` |
| mechanism | picks, then MOVES the card directly: `0x021C6DB4(side, hand_idx)` -> `0x0219CA28(side, 0x0B, idx)` -> `0x021C6B00(..., dest 0x0E)` | fills a REQUEST struct (`0x0225985C`: side -> `[0x0229DE14+0x70]`, kind 1 -> `+0x74`, count -> `[0x0229DE54+0x3C]`, flags -> `+0x3E`) and posts it via `0x0225981C`; the discard subsystem fulfils it |
| who calls it | slot4 (a cost step) | **slot1 (a RESOLVER) in all 24 attributed call sites** |

That census is the proof of the user's model: `0x022598A0` is only ever reached
from a resolver. Dark World Lightning `0x1970` is cls0[659], `+04 = 0x0221FCB9`,
a two-phase resolver -- phase `0x80` destroys the target and returns `0x7F`;
phase `0x7F` calls `0x022598A0(side, 1, 0, 0)`.

**Its flag arguments, recovered from all 26 call sites:** `r2 = 1` appears on
exactly ONE caller -- **The Cheerful Coffin `0x12FA`, "Discard up to 3 Monster
Cards"** -- so `r2` is a *monsters-only* flag. There is **no race field**, which
is why using `0x022598A0` naively would discard any card and lose "1
**Fiend-Type** monster".

### ⭐⭐⭐ THE FIX FOR BOTH BUGS IS THE SAME LIST: `0x0228EF48`
The effect-discard's per-candidate legality test is `0x0225A3F0(side, zone, idx)`:

```
0225a3f0  push {r3-r7,lr} ; sub sp,#0x10
0225a3f4  adds r6,r0,#0          ; side
0225a3f8  str  r2,[sp]           ; the HAND INDEX
0225a400  cmp  r1,#0xb           ; zone must be 0x0B = HAND
0225a40a  ldrh r4,[r0,#0xa]      ; r4 = THE ACTING CARD'S CID
0225a438  adds r0,r4,#0
0225a43a  bl   0x02022e14        ; search 0x0228EF48, count 0x1F = 31
0225a43e  cmp  r0,#0 ; beq -> skip the filter entirely
0225a442  ldr  r2,[sp]           ; param = the hand index
0225a446  adds r1,r4,#0          ; the acting cid
0225a448  bl   0x02243fe0        ; THE CRITERIA COUNT/LEGALITY CALL
0225a44c  cmp  r0,#0 ; bgt -> legal ; else movs r5,#0 (reject)
```

**`0x0228EF48` is a 31-entry sorted cid list of "my hand selection is filtered by
my criteria row"** -- and its membership reads exactly like that: Allure of
Darkness `0x1D92` ("banish 1 DARK monster from your hand"), Common Charity
`0x1C3C` ("banish 1 Normal Monster from your hand"), Familiar Knight, Relieve
Monster, Drastic Drop Off, Wild Tornado, and the whole Koa'ki Meiru family
(their reveal-a-type maintenance cost).

⭐ **And the param it passes is the HAND INDEX, a small integer** -- so bit 28 is
never set, and for a LIST B cid `0x02243B9C` resolves to **ROW 0**. Our row 0 is
already **HAND / Fiend**. So adding `0x1C8B` to `0x0228EF48` filters the *effect*
discard to Fiends **using the row we already shipped**, with no new data.

The layout that results is exactly the one already built:

| row | zone | read by | via |
|---|---|---|---|
| **0** | HAND / Fiend | the effect-discard candidate filter | `0x02243FE0`, param = hand index (no bit 28) |
| **1** | GY / Fiend | slot4's banish cost | the provider, forced to `1 << 28` by the PART I stub |

### THE FIX PLAN (both bugs)

- **PART L -- `0x0228EF48` membership.** Add `0x1C8B` (31 entries, count immediate
  `movs r2,#0x1f` @`0x0225A418`). ⚠️ Needs a count-neutral slot or a relocation --
  the list's geometry has NOT been checked yet.
- **PART M -- move the discard from slot5 to slot1.** slot5 -> 0. slot1 -> a stub
  that phase-`0x80` posts `0x022598A0(side, 1, 0, 0)` and returns `0x7F`, then
  phase `0x7F` draws via `0x021D12F4(side, 1)`.
  ⚠️ **OPEN:** whether the engine fulfils the discard REQUEST before re-entering
  the resolver for the next phase. Dark World Lightning posts its discard last
  and never needs to know. This is the one thing to prove before building.
- **PART N -- bug 1, the activation gate.** slot3 -> a stub that keeps the
  `0x0FB6` once-per-turn check (`0x021A1430(side, zone, 0x0FB6)`, the
  `0x021F01C1` body) AND requires `0x02243FE0(side, 0x1C8B, param|1<<28) > 0`,
  i.e. at least one Fiend in the GY. Returns 0 when either fails.

Both stubs are card-specific, so the ov5 cave is the right home (the donor's own
ov3 dead space has only 2 B left after PART I).

### RESOLVED: THE RESOLVER PHASE PROTOCOL -- Bone Temple Block is the precedent
`0x2025` "Discard 1 card. Special Summon 1 Level 4 or lower monster from your
Graveyard" -- cls0[1073], slot1 `0x0222C2F1`. Disassembled:

```
0222c2f0  push {r4,lr}
0222c2f4  ldr  r3,[r2,#0x70]     ; r2 = 0x0229AAFC, r3 = the PHASE CODE
0222c2f6  cmp  r3,#0x80
0222c2f8  bne  0x0222c320        ; -> the follow-up stage
  ; ---- phase 0x80: the discard ----
0222c2fa  ldrb r0,[r0,#2]        ; side
0222c2fc  movs r1,#1             ; count
0222c30c  cmp  r2,#0 ; bne       ; GUARD: nothing to discard ...
0222c310  movs r0,#0 ; pop       ;   ... -> return 0, do not post
0222c314  movs r2,#0 ; movs r3,#0
0222c318  bl   0x022598a0        ; POST the effect-discard request
0222c31c  movs r0,#0x7f          ; RETURN 0x7F -> advance
0222c31e  pop  {r4,pc}
  ; ---- any later phase: the follow-up ----
0222c320  adds r3,r3,#1 ; str r3,[r2,#0x70]
0222c324  bl   0x0220f57c        ; the Special Summon -- runs AFTER the discard
```

⭐ **So the engine DOES fulfil the discard request before re-entering the
resolver**: post in phase `0x80`, `return 0x7F`, do the follow-up next phase.
That is exactly clause 2's "discard 1 Fiend, THEN draw 1", and it is a shipped
working card. The open question in the fix plan is closed.

⚠️ Note its **guard**: if there is nothing to discard it returns 0 without
posting. Clause 2 needs the same, because the symmetric freeze exists -- a Fiend
in the GY but none in the hand.

### 🔨 BOTH BUGS FIXED AND BUILT (2026-08-25c) -- **AWAITING IN-GAME TEST #2**

`rom_gates_dark_world.nds` sha256
`56f7c4cad6b5ca970d5facadc718d0f5f71d72c9c8aa805fb64fa60cfebb9e99`,
**verify() ALL PASS**, KB `311 / 278 PASS / 0 FAIL`, allocations `[OK] ... ledger
in sync`, and **idempotent byte-for-byte** on re-application.

| part | edit |
|---|---|
| **J (changed)** | cls3[339] is now `{+04 CAVE_GDW_RES\|1, +08 0, +0C CAVE_GDW_COND\|1, +10 0x021E56E9, +14 0}` -- **slot5 is NULL**, the discard is no longer a cost |
| **L (new)** | `0x1C8B` inserted at index 7 of the effect-discard filter list `0x0228EF48`; count immediate `movs r2,#0x1f` -> `#0x20`, grown into the 2 B alignment pad at `0x0228EF86` (the pointer table at `0x0228EF88` verified untouched) |
| **M (new)** | 52 B ov5 resolver `CAVE_GDW_RES = 0x0239D120` |
| **N (new)** | 68 B ov5 gate `CAVE_GDW_COND = 0x0239D160` |

Both stubs disassembled **out of the built ROM**:

```
; PART M -- slot1: discard 1 Fiend as an EFFECT, then draw 1
0239d120  push {r4,lr} ; adds r4,r0,#0
0239d124  ldr  r2,[pc,#0x28]      ; 0x0229AAFC
0239d126  ldr  r3,[r2,#0x70]      ; the phase code
0239d128  cmp  r3,#0x80 ; bne 0x0239d13c
0239d12c  ldrb r0,[r4,#2] ; movs r1,#1 ; movs r2,#0 ; movs r3,#0
0239d134  bl   0x022598a0         ; POST the effect-discard request
0239d138  movs r0,#0x7f ; pop {r4,pc}      ; yield; it resolves before we return
0239d13c  adds r3,r3,#1 ; str r3,[r2,#0x70]
0239d140  adds r0,r4,#0 ; movs r1,#0
0239d144  bl   0x022065b8         ; the native draw-N resolver (PART K's row)
0239d148  movs r0,#0 ; pop {r4,pc}

; PART N -- slot3: once per turn AND a Fiend in BOTH zones
0239d160  push {r4,lr} ; adds r4,r0,#0
0239d164  ldrb r0,[r4,#2] ; ldrb r1,[r4,#3] ; ldr r2,[pc,#0x2c]  ; 0x0FB6
0239d16a  bl   0x021a1430 ; cmp r0,#0 ; bne reject   ; already used this turn?
0239d172  ldrb r0,[r4,#2] ; ldr r1,=0x1C8B ; ldr r2,=0x10000000
0239d178  bl   0x02243fe0 ; cmp r0,#0 ; ble reject   ; Fiends in the GY   (ROW 1)
0239d180  ldrb r0,[r4,#2] ; ldr r1,=0x1C8B ; movs r2,#0
0239d186  bl   0x02243fe0 ; cmp r0,#0 ; ble reject   ; Fiends in the hand (ROW 0)
0239d18e  movs r0,#1 ; pop {r4,pc}
0239d192  reject: movs r0,#0 ; pop {r4,pc}
```

⚠️ **DELIBERATE, STATED DEVIATION (needs the user's blessing).** PART N also
refuses activation when there is **no Fiend in the HAND**. The printed text makes
only the banish a cost, so strictly you could activate with an empty hand and
simply fail to discard. It is gated because the symmetric freeze is real -- the
empty-candidate hang of bug 1 exists on the hand side too -- and an activation
that cannot complete its own mandatory effect is not worth offering. Easy to
relax: drop the third test from `build_gdw_condition`.

⚠️ **ov5, so normal duels only.** PARTS M/N are cave stubs, inert in a puzzle
(overlay 41 evicts ov5). Clause 1 is overlay-3 and unaffected; PART I is ov3 too.

### 🎮 IN-GAME TEST #2 -- 2026-08-25: activation lost entirely (MY regression)

**User:** *"See .ml2 I cannot activate gates even though there is a target in the
GY AND in my hand"*, clarified as **no activation option appears at all**.

`rom_gates_dark_world.ml2` parsed (RAM0 file offset 0x24), side 0:

```
HAND  count=4  [0]2321 Pot of Duality  [1]1474 Foolish Burial
               [2]1966 Broww (FIEND)   [3]2321 Pot of Duality
GY    count=8  ... [1]1966 Broww (FIEND) ...
FIELD zone 10  1C8B  <- Gates
```

So the user is exactly right: a Fiend in both zones, and the card refused.

#### What was RULED OUT first (each measured, not argued)
- **Not a stale once-per-turn rider.** Walked the attached-effect node lists for
  every zone of both sides (`head u16 @0x0229ACD2 + side*0x0B3C + zone*0x14`,
  nodes `0x0229D33C + idx*0x0A`, exactly as `0x021A1430`/`0x021A1238` do):
  **no nodes attached anywhere.**
- **Not a missing/!resident patch.** All three stubs verified byte-identical in
  the SAVESTATE's live RAM (`CAVE_GDW_RES`, `CAVE_GDW_COND`, the ov3 L2 stub),
  and live `cls3[339] = {1C8B, 0239D121, 0, 0239D161, 021E56E9, 0}`.
- **Not slot5 = 0.** Censused every Field Spell's cls record: **Amazoness
  Village 0x2318** is cls1[1217] `{+04 0x02206CAD, +08 0, +0C 0x021F01C1,
  +10 0x021E5201, +14 0}` -- a Field Spell ignition with slot2 = 0, slot5 = 0 and
  the very slot3 we replaced. (Only ONE Field Spell in the ROM has a cls3 record
  at all: Ojama Country.)

#### ⭐⭐⭐ ROOT CAUSE: `0x02243FE0`'s `param` MEANS DIFFERENT THINGS PER HANDLER FAMILY
The shared slot3 **`0x021F02E4`** -- used by 12 cards, every one of which owns a
HAND-family criteria row -- is the precedent that settles it:

```
021f02f0  movs r4,#0            ; r4 = the HAND INDEX
021f02f8..0316                  ; read hand word player+0x124 + r4*4, unpack
021f0318  ldrh r1,[r5,#0xc] ; cmp ; beq next    ; skip the acting card itself
021f031e  ldrh r1,[r5]          ; cid = desc[+0]
021f0320  adds r2,r4,#0         ; *** param = THE HAND INDEX ***
021f0322  bl   0x02243fe0
021f0328  beq  next             ; 0 -> try the NEXT hand slot
021f032a  movs r0,#1 ; pop      ; a legal candidate -> ACTIVATABLE
021f0330  ldrb r0,[r5,#2] ... ldr r1,[player+0x0C]   ; the HAND COUNT
021f0340  blo  loop
```

- **HAND-family row:** `param` is the **CANDIDATE INDEX**; `0x02243FE0` answers
  "is hand slot `param` legal?" and the caller MUST ITERATE over `player+0x0C`.
  (`0x0225A3F0`, the effect-discard filter of PART L, passes the hand index for
  the same reason -- that is consistent, not a coincidence.)
- **GY-family row:** `param` is a **ROW SELECTOR**; the handler enumerates the
  whole zone and returns a total. Book of Life 0x1536's slot3 passes `0` then
  `1` (its LIST A row pair), never an index.

**So PART N's third test, `0x02243FE0(side, 0x1C8B, 0)`, asked only "is hand slot
ZERO a Fiend?" In the savestate hand slot 0 is Pot of Duality (Broww is at slot
2), so it returned 0 and the gate rejected.** The GY test above it was fine.

#### THE FIX (built)
**Removed the hand test.** It was an addition of mine, already flagged as a
deliberate deviation, and it is not what bug 1 needed. The gate is now: no
`0x0FB6` rider, AND at least one Fiend in the GY (row 1, param `1 << 28`) --
the half that follows the GY convention and is correct as written.

`CAVE_GDW_COND` is now **52 B** (was 68). Read back from the built ROM:

```
0239d160  push {r4,lr} ; adds r4,r0,#0
0239d164  ldrb r0,[r4,#2] ; ldrb r1,[r4,#3] ; ldr r2,=0x0FB6
0239d16a  bl   0x021a1430 ; cmp r0,#0 ; bne reject
0239d172  ldrb r0,[r4,#2] ; ldr r1,=0x1C8B ; ldr r2,=0x10000000
0239d178  bl   0x02243fe0 ; cmp r0,#0 ; ble reject
0239d180  movs r0,#1 ; pop {r4,pc}
0239d184  reject: movs r0,#0 ; pop {r4,pc}
```

⚠️ **Consequence to watch:** nothing now blocks activation when the GY has a
Fiend but the HAND does not. If that hangs at the discard, the fix is to iterate
the hand properly in slot3 (clone `0x021F02E4`'s loop), NOT to pass a bare index.

`rom_gates_dark_world.nds` sha256
`3713edb57f9b74a4d50d19789a8bbe35cbccffc354ae5602f31c6025d974e379`,
verify() 51/51 PASS.

### 🎮 IN-GAME TEST #3 -- 2026-08-25: effect discard WORKS, filter does not

**User:** *"Thats better. One last thing, when i am asked to discard it lets me
discard any card, not just a fiend. See .ml3 while I am in the discard window"*
-- and, asked directly, confirmed **the Dark World trigger DID fire** this time.

So activation, the GY banish, the effect discard (Sillva/Broww trigger) and the
draw are all working. **Only the Fiend restriction on the discard is missing.**

#### MEASURED from rom_gates_dark_world.ml3 (taken inside the discard window)
```
[0x0229DE94+0x0A] = 0004        <- NOT 0x1C8B
[0x0229DE14+0x70] = 0  (side)   [0x0229DE14+0x74] = 1 (kind)
[0x0229DE54+0x3C] = 1  (count)  [0x0229DE54+0x3E] = 0000 (flags)
```

#### ⚠️ TWO WRONG READINGS OF THIS MECHANISM -- do not make a third
1. I read `[0x0229DE94+0x0A]` as "the acting card's cid". **It is not** -- at
   `0x02259ECA..0x02259EF4` the pick-completion code writes the **PICKED HAND
   INDEX** there and the picked card's packed ref to `+0x0C`.
2. I read `0x0225A3F0` as "the per-candidate legality test for the discard
   request", giving it the signature `(side, zone, hand_idx)`. **`0x0225A3F0`
   has NO BL callers anywhere in arm9+ov3** -- it is a step in a table-driven
   state machine, reached indirectly. Its role is unestablished.

**Consequence: PART L (membership in `0x0228EF48`) does nothing for this path.**
It should be considered unproven, not merely ineffective.

#### ⭐ THE ENGINE LIMIT (this part IS well evidenced)
Recovered the arguments and printed text of all 26 callers of the effect-discard
`0x022598A0(side, count, monsters_only, f3)`:

- every caller's text is "discard 1 card" / "2 cards" / "up to 2 cards" with **no
  type restriction** -- Dark World Lightning, Dark World Dealings, Bone Temple
  Block, Infernity Inferno, Depth Amulet, Drill Warrior, Clear World, Fine, ...
- **exactly one** passes `monsters_only = 1`: **The Cheerful Coffin 0x12FA**, and
  it is the only one printed *"Discard up to 3 **Monster Cards**"*.

So the request struct carries **one boolean filter and no race field**. There is
**no native race-filtered EFFECT discard in this ROM to copy**. (n = 1 for the
flag's meaning; the 1:1 correlation over 26 callers is the evidence, and the flag
is not consumed by any card-type accessor inside 0x02258F00..0x0225B800 -- the
only accessor there is `0x02029E60` is-real-card, x4. Treat "monsters_only" as
STRONGLY INDICATED, not proven.)

#### THE CHOICE (for the user)
- **(a) "discard 1 monster"** -- pass `monsters_only = 1`. One-word change to
  PART M. Keeps the Dark World trigger. Deviation: any monster, not only Fiend.
- **(b) custom filter** -- hook the discard UI's real candidate-legality site to
  add a Fiend test for the donor. Needs that site identified properly first
  (twice mis-identified above), most likely with a GDB session breakpointing the
  window rather than more static reading.
- **(c) revert to the cost discard** -- Fiend-filtered but NO trigger. Already
  rejected by the user, recorded for completeness.

### 🔨 THE FIEND FILTER, BUILT IN ov5 (2026-08-25d) -- AWAITING IN-GAME TEST #4

`rom_gates_dark_world.nds` sha256
`316bc9afabd31afb6e5bf3ac12b428836d0b2c278a766833c0faa3335dab6c05`,
verify() ALL PASS, KB 312/279/0, allocations `[OK] ... ledger in sync`,
**idempotent byte-for-byte**.

#### The 3DS answer, and why it does not port directly
Gates 0x25F3's HAND handler on the 3DS is `0x004A9EFC`, and it is four lines:

```
004a9efc  str  lr,[sp,#-4]!
004a9f00  ldr  r3,[r0,#8]        ; r3 = the row's CRITERIA WORD (0x18000002)
004a9f08  mov  ip,r1
004a9f10  stm  sp,{r1,r3}        ; [sp]=0, [sp+4]=THE WORD
004a9f18  ldrh r1,[r0]           ; the row's cid
004a9f24  bl   0x004b16b4        ; register the effect component WITH the word
```

So on the 3DS the criteria word travels **with the registered component**, and the
selection machinery filters on it. **The NDS effect-discard request has no such
field** -- `0x0225985C` stores only side, kind, count and flags -- so there is
nothing to port. The filter has to be supplied by us.

#### PART O -- the narrowing wrapper (`CAVE_GDW_FILT = 0x0239D1C0`, 96 B)
Hook point, established statically: the discard window's per-candidate legality
**callback** is `0x0225A3F1`. It is loaded from the pool word at **`0x0225A7DC`**
and passed as the `r3` argument of `bl 0x0224B9F0` @`0x0225A7C8` -- which is why
nothing in the image BLs to it, and why `0x0225A7DC` is its ONLY reference.
Repointing that one word swaps the callback for every discard in the game, so the
stub is a WRAPPER, not a replacement:

```
0239d1c0  push {r4,r5,r6,r7,lr} ; adds r4,r0 / r5,r1 / r6,r2   ; side, zone, index
0239d1c8  bl   0x0225a3f0        ; THE NATIVE VERDICT
0239d1cc  adds r7,r0,#0 ; cmp r0,#0 ; beq out    ; already illegal -> unchanged
0239d1d2  ldr  r0,=FLAG ; ldr r0,[r0] ; cmp r0,#0 ; beq out   ; not our discard
0239d1da  cmp  r5,#0xb ; bne out                 ; hand only
0239d1de  ldr  r0,=0x0229ADB8                    ; player[0] hand array
0239d1e0  movs r1,#1 ; ands r1,r4 ; cmp r1,#0 ; beq side0
0239d1e8  ldr  r1,=0x0B3C ; adds r0,r0,r1
0239d1ec  side0: lsls r1,r6,#2 ; ldr r0,[r0,r1]  ; the hand word
0239d1f0  ldr  r1,=0x3FFF ; ands r0,r1           ; -> cid
0239d1f4  ldr  r1,=0x0202ABB9 ; blx r1           ; -> race
0239d1f8  cmp  r0,#3 ; bne reject                ; FIEND
0239d1fc  out:    adds r0,r7,#0 ; pop
0239d200  reject: movs r0,#0    ; pop
```

Native verdicts are **0x800 legal / 0 illegal** (`0x0225A52C`), passed through
untouched for every other card. `FLAG` is the word at `CAVE_GDW_FILT+0x5C`
(`0x0239D21C`): **set** by the resolver before it posts the request, **cleared**
when it draws, and **cleared again by the slot3 gate on every activation poll**,
so a cancelled discard cannot leave the filter armed.

⭐ `0x0202ABB8(cid)` decoded and cross-validated: it is
`((card_prop[cid].word1 << 10) & 0xFFFFFFFF) >> 27`. Evaluated over the real
card_prop, every Dark World monster returns **3**, Gemini Elf 18 (Spellcaster),
and Psychic Lifetrancer 21 -- which independently matches its own criteria row's
`0xA8 >> 3 = 21`. 264 cards in the ROM return 3.

#### PART L WITHDRAWN
The `0x0228EF48` insert is reverted and the list + its 2 B alignment pad are back
to stock (verified in the built ROM), and the ledger claim is removed. It did
nothing here: `0x0225A3F0` keys that lookup on `[0x0229DE94+0x0A]`, which the
request-driven discard never sets to the acting cid -- the savestate read
**0x0004**, and that field is written with the PICKED HAND INDEX by `0x02259EE0`.

#### Cave layout now
```
CAVE_GDW_RES  0x0239D120  68 B / 0x50   slot1 resolver (+ arms the flag)
CAVE_GDW_COND 0x0239D170  64 B / 0x50   slot3 gate     (+ disarms the flag)
CAVE_GDW_FILT 0x0239D1C0  96 B / 0x60   the Fiend filter, flag at +0x5C
CAVE_FREE     0x0239D220
```

⚠️ ov5, so normal duels only -- in a puzzle the filter is inert **and so is the
whole of clause 2** (its resolver and gate are cave stubs too). Clause 1 is ov3
and unaffected.

### 🎮 IN-GAME TEST #4 -- filter inert; ROOT CAUSE: WRONG WINDOW (2026-08-25e)

**User:** *"See .ml3 all cards are still offered"*, on the new build.

#### Measured from the savestate -- everything I had suspected was WRONG
```
CAVE_GDW_RES / COND  live RAM  MATCHES the build
CAVE_GDW_FILT        live RAM  matches EXCEPT +0x5C, which is the runtime flag
FLAG @0239D21C = 00000001      ARMED           <- slot3 was NOT clearing it
[0x0225A7DC]   = 0239D1C1      retargeted OK
request: side 0  kind 1  count 1  flags 0000
```
So the stub was installed, armed and hooked -- and still nothing filtered. My
"slot3 clears the flag on every poll" theory was **falsified by measurement**.

#### ⭐ ROOT CAUSE
The callback ABI was right all along -- `0x0224B9F0(side, cid, param, callback)`
stores the callback at `[0x0229DE14+0x0C]` (0x0224B9FA) and it is invoked as
**(side, zone, index)**, proven at 0x0224C136:
`ldr r3,[r0,#0xc] ; adds r0,r4 ; adds r1,r5 ; adds r2,r7`. And the mechanism does
gate the display -- in-game test #1 the COST discard used this same picker and
correctly offered only Fiends.

**The mistake was hooking only ONE of the discard UI's FOUR pickers:**

```
0x02259EBE -> callback 0x02259C4D   pool 0x02259F9C
0x0225A354 -> callback 0x0225A239   pool 0x0225A3E8
0x0225A7C8 -> callback 0x0225A3F1   pool 0x0225A7DC   <- the only one test #3 hooked
0x0225B434 -> r3 not from a pc-literal              (not hookable this way)
```

A request-driven discard opens one of the other two. (0x02259EBE is a good
candidate: it passes `param = 0xFFFFFFFF` via `mvns r2,r2`.)

#### THE FIX (built)
PART O is now **three 8-byte thunks plus one shared flag-gated body**, and all
three literal pool words are retargeted. Hooking extras is safe precisely because
the body is flag-gated: it calls the native callback first and returns that
verdict untouched unless our own discard is live.

```
0239d1c0  ldr r3,[pc,#0] ; b 0x239d1d8 ; .word 0225A/02259C4D   thunk 0
0239d1c8  ldr r3,[pc,#0] ; b 0x239d1d8 ; .word 0225A239         thunk 1
0239d1d0  ldr r3,[pc,#0] ; b 0x239d1d8 ; .word 0225A3F1         thunk 2
0239d1d8  push {r4,r5,r6,r7,lr} ; adds r4,r0 / r5,r1 / r6,r2
0239d1e0  blx  r3                        ; THE NATIVE VERDICT
0239d1e2  adds r7,r0,#0 ; cmp r0,#0 ; beq out
0239d1e8  ldr  r0,=FLAG ; ldr r0,[r0] ; cmp r0,#0 ; beq out
0239d1f0  cmp  r5,#0xb ; bne out
0239d1f4  ...hand word -> cid...
0239d20a  ldr  r1,=0x0202ABB9 ; blx r1 ; cmp r0,#3 ; bne reject
0239d212  out: adds r0,r7,#0 ; pop      reject: movs r0,#0 ; pop
```

112 B at `CAVE_GDW_FILT = 0x0239D1C0` (0x80 held), flag now at **+0x6C =
0x0239D22C**, `CAVE_FREE = 0x0239D240`.

`rom_gates_dark_world.nds` sha256
`668c218f2338b77770620675599aabd992e4c490b17b7d9bb23f2befe5633dd3`,
verify() ALL PASS, KB 312/279/0, ledger in sync, idempotent byte-for-byte.

⚠️ If test #5 still shows every card, the remaining suspect is the fourth picker
`0x0225B434`, whose callback is not a pc-literal and so needs a different hook
(or the window is not a 0x0224B9F0 picker at all). At that point the honest move
is a diagnostic build that records (zone, index, cid, race) into spare cave bytes
and ONE savestate, rather than another blind hook.

### 🎮 TEST #5 FROZE -- and the 3DS comparison found the real answer (2026-08-25f)

**User:** *"When I open the discard window the game freezes."* Then: *"do a deep
RE on the 3DS rom and see where you deviate."*

The freeze was mine: PART O hooked THREE picker callbacks whose role I had not
established, on the reasoning that flag-gating made it safe. Flag-gating makes
the VERDICT safe; it does nothing about control flow or about a window that ends
up with zero legal candidates. `0x0219DA5C` is a candidate COUNTER -- it loops the
callback over `player[+0x0C]` and tallies the legal ones -- so a filter that
rejects everything yields a window with nothing selectable.

#### ⭐⭐⭐ THE DEVIATION FROM THE 3DS
3DS Gates 0x25F3 registers a **criteria-carrying component for BOTH zones** (hand
handler `0x004A9EFC` lifts the row's word `0x18000002` and passes it to the
registrar `0x004B16B4`). It never uses an unfiltered discard request. My build
used the criteria registry for the GY (matching) but the **request-based discard**
for the hand (deviating) -- and the NDS request carries no race field, which is
what sent me hunting for a filter hook at all.

#### ⭐ AND THE COST/EFFECT DISTINCTION IS *ONE ARGUMENT*
`0x021C6D90` and `0x021C6DB4` are the same function twice, byte-identical except:

```
0x021C6DB4  movs r0,#1 ; str r0,[sp] ; str r0,[sp,#4]     ; kind 1  COST
0x021C6D90  movs r0,#1 ; str r0,[sp] ;
            movs r0,#2 ; str r0,[sp,#4]                   ; kind 2  EFFECT
```

Both then `bl 0x021C6B00(side, slot, 0, dest 0x0E)` from source zone 0x0B, where
that word arrives as `[sp,#0x4C]` and is handed to
`0x021D1300(reason, &desc, r2, KIND)` at `0x021C6CB8` -- the relocation event that
"if this card is discarded to the Graveyard by a card effect" listens for.
`0x021C6D90` has exactly ONE native caller, `0x02259F42`, inside the discard UI's
request fulfilment, chosen over `0x021C6DB4` by a flag at `0x02259F3C`.

**So the request subsystem was never the point.** Its only relevance was that it
happens to call the kind-2 mover. Keep the criteria-FILTERED picker -- slot5
`0x021E4EED`, which in-game test #1 proved offers only Fiends via criteria ROW 0
-- and change its mover.

#### THE BUILD (PARTS M and O withdrawn, PART P added)
- cls3[339] is back to the **test-#1 shape** with our own gate:
  `{+04 0x022065B9 draw, +08 0, +0C CAVE_GDW_COND|1, +10 0x021E56E9 banish,
  +14 0x021E4EED Fiend discard}`.
- **PART P**, 36 B at `CAVE_GDW_MOVER = 0x0239D120`: retarget the single
  `bl 0x021C6DB4` at `0x021E4F66` (inside the shared discard cost) to a
  **cid-scoped** trampoline. r5 still holds the descriptor there -- confirmed by
  the very next instruction, `ldrh r1,[r5]` at 0x021E4F6A -- so it reads the acting
  cid from `[r5]` and picks the mover:

```
0239d120  push {lr}
0239d122  ldrh r2,[r5]        ; the acting card's cid
0239d124  ldr  r3,=0x1C8B ; cmp r2,r3 ; bne native
0239d12a  ldr  r3,=0x021C6D91 ; blx r3 ; pop {pc}    ; EFFECT (kind 2)
0239d130  native: ldr r3,=0x021C6DB5 ; blx r3 ; pop {pc}   ; COST, byte-for-byte
```

- All three PART O callback hooks are **reverted to native** (verified in the
  built ROM), `CAVE_GDW_RES` / `CAVE_GDW_FILT` are retired, `CAVE_FREE` back to
  `0x0239D1C0`.

`rom_gates_dark_world.nds` sha256
`b48d7a5ee62b9f3db9a7ff9a1d86fc72e363d99a6879bb115a299f8862ae4f0e`,
verify() 48/48 PASS, KB 312/279/0, ledger in sync, idempotent byte-for-byte.

**Why this should hold:** every piece is now a configuration that has already been
observed working in game -- the banish, the Fiend-filtered discard prompt and the
draw are exactly test #1, which passed on all three. The only new thing is one
argument on the relocation.

### 🎮 TEST #6: filter WORKS, trigger still absent -> THE THIRD MOVER (2026-08-26)

**User:** *"It now only lets me discard fiends but the effects of darkworlds are
not firing when I do so it is treating the discard as a cost and not an effect
discard."* Savestates `.ml2` (before) / `.ml3` (after) supplied.

#### Measured from the pair -- the whole effect resolves correctly
```
.ml2  HAND: Beiige, Goldd, GATES, Goldd, Pot of Duality, Gemini Elf   GY: ... Broww
.ml3  HAND: Goldd, Goldd, Pot of Duality, Gemini Elf, SILLVA (drawn)
      GY:   ... Beiige (discarded)      BANISHED: Broww      FIELD z10: Gates
```
Banish ✓, Fiend-only discard ✓, draw ✓. **Beiige sits in the GY instead of
Special Summoning itself** -> no trigger. Exactly as reported.

#### ⭐⭐⭐ THERE ARE THREE HAND->GY MOVERS, NOT TWO
`0x02259F3C`..`0x02259F58` in the discard UI chooses between **three**:

| mover | `[sp+4]` (relocation KIND) | who calls it |
|---|---|---|
| `0x021C6DB4` | **1** | the COST discards -- Valkyrus, Trade-In, Allure of Darkness, ... (8 callers) |
| `0x021C6D90` | **2** | only `0x02259F42` |
| **`0x021C6D58`** | **0** | **THE EFFECT DISCARD** (29 callers) |

`0x021C6D58`'s callers settle it, because they are the user's own list of cards
that trigger Dark World: **Card Destruction `0x12D5`**, **Dragged Down into the
Grave `0x14E8`**, Morphing Jar `0x11F5`, Royal Tribute `0x15A4`, Beckoning Light
`0x1769`, Confiscation `0x1324`, Mind Crush `0x1803`, Into the Void `0x2278`,
The Fabled Chawa `0x216A`.

⚠️ **PART P had picked kind 2 and that was wrong** -- inferred from `0x021C6D90`
being the request path's mover, when the request path actually picks among all
three. Tried in game 2026-08-26: the discard resolved, Dark World still silent.

⚠️ `0x021C6D58(side, index, flag)` takes **THREE** arguments where the other two
take two (its `flag` becomes `0x021C6B00`'s r2). The trampoline zeroes r2.

#### THE BUILD
PART P now routes the donor to `0x021C6D58`:

```
0239d120  push {lr}
0239d122  ldrh r2,[r5]          ; the acting cid (r5 = descriptor, still live --
0239d124  ldr  r3,=0x1C8B       ;  confirmed by `ldrh r1,[r5]` at 0x021E4F6A)
0239d126  cmp  r2,r3 ; bne native
0239d12a  movs r2,#0            ; the third argument
0239d12c  ldr  r3,=0x021C6D59 ; blx r3 ; pop {pc}    ; EFFECT (kind 0)
0239d132  native: ldr r3,=0x021C6DB5 ; blx r3 ; pop {pc}   ; COST, byte-for-byte
```

`rom_gates_dark_world.nds` sha256
`5747b116ee13d18150c9893228a4ab03306cd8bac8218325ea55202a9de7a03e`,
verify() ALL PASS, KB 312/279/0, ledger in sync, idempotent byte-for-byte.

### ✅ SHIPPED -- clause 2 in-game confirmed 2026-08-26

User, on the kind-0 mover build: **"Perfect! Ship it!"** -- banish, Fiend-only
discard, Dark World trigger, draw and the once-per-turn gate all correct, with
clause 1 regression-free.

Single-card ROM `rom_gates_dark_world.nds` sha256
`5747b116ee13d18150c9893228a4ab03306cd8bac8218325ea55202a9de7a03e`.

Banked this session (KB now **314 facts / 281 PASS / 0 FAIL**):

| fact | what it cost to learn |
|---|---|
| `dispatch.three_hand_to_gy_movers` | 3 in-game tests -- cost vs effect discard is ONE argument; `0x021C6DB4` kind 1 = cost, **`0x021C6D58` kind 0 = effect**, `0x021C6D90` kind 2 = neither |
| `dispatch.two_row_criteria_is_list_b_plus_l2` | the "donor gets row 0 at best" pessimism was only half the story -- LIST B selects by `param & 0x10000000` |
| `dispatch.candidate_count_param_is_family_dependent` | 1 in-game test -- `0x02243FE0`'s param is a ROW SELECTOR for a GY row, a CANDIDATE INDEX for a HAND row |
| `timing.once_per_turn_is_the_0fb6_rider` | the `0x0FB6` rider, and that the GY-banish cost stamps it for free |
| `resolver.draw_n_is_a_per_cid_table` | upgrades `equip.draw` from ANCHORED to a closed ABI |
| `dispatch.gy_banish_cost_and_row_param_sources` | the banish cost defaults to exactly 1 for a cid with no switch arm |
| `dispatch.slot4_and_slot5_are_interchangeable_machines` | now in-game proven, not just static |
| `card.gates_of_dark_world_clause2` | the shipped record + every anchor it stands on |

**THE LESSON, recorded because it held six times out of six:** every wrong turn
was a static inference about *which subsystem does X*; every correct step came
from correlating a function against the **printed text of its callers**
(0x021E56E9's banish cards, 0x022598A0's discard cards, 0x021C6D58's Dark World
cards, 0x021F02E4's hand cards) or from a user savestate. When a hypothesis about
this engine is falsified twice, the census beats the disassembly.

### THE IN-GAME TEST FOR CLAUSE 2
Deck: The Gates of Dark World, **>= 2 Fiends** you can get into the GY, **>= 1
Fiend in hand**, cards left to draw.

1. Activate Gates. Get a Fiend into your GY.
2. Activate the once-per-turn effect. It must prompt to **banish 1 Fiend from
   your GY** -- Fiend-only, and not activatable with no Fiend in the GY.
3. Then it must prompt to **discard 1 Fiend from your hand** -- Fiend-only.
4. Then you **draw exactly 1**.
5. **Once per turn:** the option is gone on a second attempt the same turn, back
   next turn.
6. **Clause 1 regression (mandatory):** Fiends still +300/+300; Spellcasters and
   Fairies unaffected; **Yami `0x10F5` still gives Fiend/Spellcaster +200 and
   Fairy -200**; **Jurassic World `0x1AA7` still gives Dinosaurs +300** (it owns
   the tail clause 1 branches into). Items 5-6 of the clause-1 test were never
   run -- fold them in.

**Distinguishable failures**

| symptom | most likely cause |
|---|---|
| no activation option at all | the cls3 record is not being reached, or slot3 `0x021F01C1` refuses |
| the GY prompt offers non-Fiends, or the wrong zone | PART I is not taking effect -- slot4 read ROW 0 (hand) instead of ROW 1 (GY) |
| **the banish prompt appears but the discard prompt never does** | ⚠️ **the one unexercised step**: a slot4-family function (`0x021E4EED`) in slot5 |
| the discard prompt offers non-Fiends | row 0's `extra` is wrong |
| you draw 0, or 2 | the PART K draw-count row |
| it fires twice in a turn | the `0x0FB6` rider is not being stamped or not read |

### STILL OPEN
1. Which `0x0FB6` reader to use for slot3 -- `0x021F01C1` (115 records) is the
   most generic candidate but has NOT been disassembled yet; it may carry an
   extra condition.
2. The draw count: does a cid absent from the 189-row table at `0x02206304` fall
   through to something that yields 1, or is an entry required?
3. Which two phantom criteria rows to consume (G), and which phantom cls3 row (J).
4. ⚠️ Unexercised in the stock image: a slot4-family function in slot5 (above).

### PROPOSED CLAUSE 2 DESIGN (2026-08-25b) -- awaiting user confirmation

The recipe above needs the donor in TWO membership lists. **List B has a phantom
to evict (0x234F); L2 `0x02271104` does NOT** -- all 28 of its members are real
cards (Master Hyperion, Tragoedia, Dark Grepher, the Koa'ki Meirus, ...), so
joining L2 would break a shipped card.

**So invert the row assignment and drop the L2 requirement entirely.** L2 only
matters because SLOT5's param comes from the provider; a COST passes *its own*
param, and we are writing the cost stub. Therefore:

| row | zone | who reads it | how |
|---|---|---|---|
| **0** | **HAND** (Fiend) | SLOT5 off-field template `0x02235604` | provider returns 0 for a non-L2 cid -> `param & 0x10000000 == 0` -> row 0 |
| **1** | **GY** (Fiend) | our SLOT4 cost stub | the stub passes a param with **bit 28 set** -> row 1 |

Only **LIST B membership** is then required. And this ordering -- row 0 = HAND,
row 1 = GY -- is **exactly the order the 3DS ships for cid 0x25F3**, which is an
independent corroboration that was not used to derive it.

Parts, provisional:

- **G** criteria rows: 2 consecutive rows for `0x1C8B`
  `{0xFFFF, <HAND handler>, 0x0002, 0x1800}` and
  `{0xFFFF, 0x0223CA11, 0x0002, 0x1800}`, count-neutral (drop 2 phantom rows --
  NOT 0x234F's pair, which patch_sea_lancer already draws on).
- **H** LIST B `0x02271314`: evict phantom `0x234F`, insert `0x1C8B` in sorted
  position (rotate entries [2..24] right by one; count immediate untouched).
- **I** cls3 record for `0x1C8B`: `+14 = 0x02235605`, count-neutral (drop a
  phantom cls3 row).
- **J** slot3 activation condition + once-per-turn gate. ⚠️ `0x021F0BDD` is
  cid-keyed via `0x0226FAFC` and the donor is not in it -- pick a different
  slot3, or claim a row there.
- **K** slot4 cost stub: select from row 1 (param bit 28) and banish the pick.
- **L** slot1 resolver: discard the slot5 pick from hand, then draw 1.

**Still unproven, in priority order:** (1) which native cost function banishes a
GY pick, and whether it can be reused with a param override rather than
rewritten; (2) whether the off-field slot5 template can address the HAND
container (0x0D) and not just GY/banished; (3) a generic once-per-turn slot3;
(4) the draw primitive (`0x021D12F4(side, count)` is UNVERIFIED, inherited).

### ⚠️ COMPOSITION NOTE: phantom 0x234F is ALREADY CLAIMED
`check_allocations.py:166` — `("populate_table", 0x234F, "sea_lancer")`. Sea
Lancer drops the **second** of 0x234F's two rows to make room for its own insert.
So in the chained ROM 0x234F has ONE row left, while still sitting in list B.
Any plan that reuses 0x234F must be checked against patch_sea_lancer, not just
against the base image.

### CONFIRMED (re-read this session): the criteria row-offset ceiling applies
`dispatch.simorgh_row_offset_is_a_bespoke_switch_arm`: a cid in membership list A
`0x0227134C` (0x3B entries) is clamped to rows 0/1 by `param == 0 ? 0 : 1`
(0x02243BFA); a cid in neither list falls to the forced-`r4=0` leaf 0x02243EEC =
**row 0 only**. Lightpulsar's shipped workaround: put the two rows on a PROXY
phantom cid already in list A and swap `desc[+0]` for the duration.

## Open Questions (clause 2) — see PROMPT_gates_of_dark_world_clause2.md
**Clause 2's payload already ships in this ROM.** PROVEN this session by record
dump: **Fabled Valkyrus 0x1FB5** is printed "Once per turn: You can discard 1
Fiend monster; draw 1 card" — clause 2's payload verbatim — and it is
implemented as `cls3[508] @0x0227CD14 {+04=0x022065B9, +08=0, +0C=0x021F0BDD,
+10=0x021E4EED, +14=0}` plus criteria row [856]
`{0x1FB5, filt 0xFFFF, handler 0x0223CB19, flags 0x0002, extra 0x1800}`.
**Dark Necrofear 0x1466** gives the cost row's shape: criteria row [134]
`{0x1466, 0xFFFF, handler 0x0223CA11, flags 0x0002, extra 0x1800}`.
**Ojama Country 0x204A** (Field Spell, once-per-turn ignition with a cost) is
`cls3[538] @0x0227CFE4 {+04=0x02207191, +08=0, +0C=0x021F0BDD, +10=0x021E7245,
+14=0x02235605}`.

- PROVEN: criteria `extra` HIGH BYTE **0x18 = race 3 = Fiend**, from 10
  concurring rows whose cards all name Fiend-Type monsters (Dark Necrofear,
  Puppet Master, Doom Shaman, Dark Fusion, Gaap, Fabled Valkyrus, Koa'ki Meiru
  Doom, Darkness Neosphere, Stygian Security, Stygian Street Patrol). Matches
  `dispatch.criteria_word_race_attribute`'s `race = high_byte >> 3`.
- HYPOTHESIS (untested): `+0C = 0x021F0BDD` is the shared once-per-turn /
  activation-condition slot — both once-per-turn ignition records carry it.
- OPEN: which cls table does a Field Spell ignition use? Ojama Country and
  Fabled Valkyrus are both **cls3**; the donor's only record is **cls1[706]**
  (now zeroed, cid kept — free to reuse if cls1 is right). Decidable statically
  via `dispatch.cls_table_selector` (descriptor byte +0x05).
- OPEN, likely the real blocker: clause 2 needs **two** criteria rows, and
  `otn-criteria-row-offset-mechanism` records that a donor cannot reach criteria
  rows past index 1 by data alone (Dark Simorgh needs a hardcoded switch arm at
  0x02243DEA; 0x02243BEC is the hook that supplies one). Read that first.
- UNVERIFIED, inherited from memory — re-confirm before use: GY->banished
  applier `0x021C7118`, draw `0x021D12F4(side, count)`.
- The donor owns **no** criteria row and **no** effect-registry row, so clause 2
  needs a count-neutral insert into `0x022713C4` (1388 rows x 12, verified
  sorted this session).

## Unfinished business (carried into the next session)
1. **The combined chain build was never run.** The patch was wired into
   `apply_all_patches.py` (import, `_apply_gates_of_dark_world`, a `PatchStep`
   after Dragon Shrine) and added to `SHIPPED` in `_verify_all_patches.py`, but
   the build was interrupted before executing. **`rom_all_patches.nds` does NOT
   contain this card.** Either run the chain build + full `verify()` sweep, or
   revert those two edits. Composition was checked only STATICALLY: Shien's Dojo
   owns trigger-registry row 137, this card owns 117 (no overlap), and no other
   shipped patch names any of this card's addresses.
2. ~~Two clause-1 regression controls untested~~ — **DONE 2026-08-25**, both
   passed in game (Yami and Jurassic World both still behave correctly). Clause 1
   now has a complete in-game pass; item 1 above is the only loose end.

## Next Experiment
Static, no emulator — answers "which cls table" and "is +0C the once-per-turn
slot":

```
.venv-1/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from otn_enhanced.knowledge.env import load_env; from otn_enhanced.knowledge.helpers import Helpers; env=load_env(); h=Helpers(env); sh=[(i,h.u32(0x02279D74+i*24,'ov3')) for i in range(0x308) if h.u32(0x02279D74+i*24+0xC,'ov3')==0x021F0BDD]; print(len(sh),'cls3 records share +0C=0x021F0BDD'); print(sh[:20])"
```

Then disassemble `0x021F0BDC` (the shared slot-3 callback) and Fabled Valkyrus's
`+10 = 0x021E4EEC` (the likely discard+draw resolver).

## CARD-FACE CONSTRAINT discovered after the donor was chosen (2026-08-25)
Names are written **in place and never grown** (the engine copies these blobs
into fixed-size buffers). Measured on the real ROM (`bin2.pac`):

- `card_name_{E,F,G,I,S}.bin` have only **2-4 bytes of trailing padding**, so
  `_place_string`'s relocate-into-padding path is NOT available for a 24-byte
  string. Verified: name blob is fully packed, **zero unreferenced strings
  >= 23 B**, and the one spare `card_indx` entry (4306 entries vs 4305 cards) is
  a zero-length end sentinel in all five languages.
- "The Gates of Dark World" needs **24 B incl NUL**. Donor name slots:
  Yami **4 B**; Jurassic World 14-16 B; Chorus of Sanctuary 18-24 B;
  A Legendary Ocean 16-21 B; **Harpies' Hunting Ground 23/29/23/29/32 B**;
  **Colosseum - Cage of the Gladiator Beasts 40/36/40/39/40 B**.

=> Only **Harpies' Hunting Ground 0x183F** and **Colosseum 0x1C8B** can carry the
real name in all five languages. With Yami the effect is correct but the card
stays displayed as "Yami" with Yami's description.

Donor footprints (aligned u16 occurrences across ARM9 + ov3):
- **Yami 0x10F5 — 1** (its own field-arm pool word). Ideal, but 4-byte name.
- **Colosseum 0x1C8B — 10** (3 arm9, 7 ov3), cls1[706] has **one** live slot
  (+04 = 0x0221A6ED); its field arm 0x021B2A3E is **44 B** (only inbound branch
  is the switch's own `b` @0x021B27DC), so the 14-byte Fiend block fits in place.
- **Harpies' Hunting Ground 0x183F — 25**, cls1[437] has **four** live slots
  (+04 0x02204899, +08 0x021DFB89, +0C 0x0224A115, +14 0x02234DA5), and its field
  arm 0x021B28B6 is only **12 B** — too small for the 14-byte block. Worst option.

Also confirmed: **cid 0x2348 is a true phantom** (absent from card_prop's 4305
rows) and its field-spell arm `0x021B2B10..0x021B2B33` is **36 B of dead code** —
a free in-function code slot if one is ever needed.


## SHIPPED (2026-08-25) — `patch_gates_of_dark_world.py`, donor Colosseum 0x1C8B
Built `data/over_the_nexus/working/rom_gates_dark_world.nds`; `verify()` 14/14 PASS,
idempotent (re-running `main()` on the output is a no-op and still verifies).

| Part | Address | What |
|------|---------|------|
| A | `0x021B2A3E` | 14 B Fiend +300/+300 block replaces the donor's 44 B field arm (30 B left dead) |
| B | `0x022666AC` | counter-accrual arm literal `0x1C8B` -> phantom `0x2500` |
| C | `0x022758BC` | continuous-trigger registry row 117 cid -> `0x2500` (count still 181) |
| D | `0x0228A304` | cls1[706] slots zeroed, cid kept (cls1 still 1333 sorted) |
| E | `0x0209CDF2` | ARM9 "Gladiator Beast" set-code table: donor shifted out, tail `0xFFFF`, count still 29 |
| F | bin2.pac | name + description in place, all 8 languages |

PART A as built (disassembled from the OUTPUT ROM, not the assembler):
```
021b2a3e  b168  ldr  r1,[r6,#8]     ; race bitmask
021b2a40  0820  movs r0,#8          ; Fiend = bit 3
021b2a42  0842  tst  r0,r1
021b2a44  f2d0  beq  0x021b2a2c     ; -> b 0x021B2B48 (contribute nothing)
021b2a46  0221  movs r1,#2
021b2a48  0902  lsls r1,r1,#8       ; r1 = 0x200
021b2a4a  3fe7  b    0x021b28cc     ; Jurassic World's +300/+300 tail
```
Yami's arm `0x021B28A0` re-disassembled from the output ROM as a control: unchanged.

Slots claimed: NO ov5 cave slot, NO cls insert, NO criteria row, NO phantom drop
from a sorted table. Only `("lp_literal", 0x2500)` and
`("counter_trigger_registry", 0x2500)` in `PHANTOM_CLAIMS`; `check_allocations`
is green (80 phantom claims, no double-claims).

KB contributions (`author_facts.py`, all VERIFIED, `--check` = 272 PASS / 0 FAIL):
`field.stat_engine`, `field.race_and_attribute_bitmasks`, `field.plus300_tail`,
`field.arm_map`, plus UNVERIFIED `donor.name_blob_has_no_slack` amending
`donor.name_slot_floor`.

## Deliberate deviations (clause 1 build)
- **Clause 2 is not implemented** and is deliberately NOT in the card's
  description text — the card reads "All Fiend-Type monsters gain 300 ATK and
  DEF." only.
- The name/description are written in **English in all 8 languages** (the repo's
  existing convention; `_place_string` writes one byte string per language).
- The donor's counter plumbing at `0x021CE8C4` and `0x021CF038` (per-cid arms in
  the counter place/remove paths) is left in place. It is inert because PARTS B
  and C remove every accrual path, so no counter can exist on the card.

## Clause-1 in-game test — RUN 2026-08-25, ALL STEPS PASSED
User's verbatim reports:
- steps 1-4: *"1. Confirm, fiends increase attack / 2/3. Spellcasters/fairies do
  not have increase/decreased attack / 4. No counters are placed"*
- step 5 (regression controls): *"Yami still behaves correctly, Jurassic World
  still behaves correctly."*

Step 2/3 is the load-bearing one: Spellcasters and Fairies being unaffected
proves the mask really is Fiend-only (bit 3) and not Yami's inherited
Fiend|Spellcaster pair, and that the Fairy -200 branch is gone. Step 5 proves
the two shared structures survived — Yami's arm `0x021B28A0` (adjacent, untouched)
and Jurassic World's `0x021B28CC` +300/+300 tail (which clause 1 branches INTO,
so a Dinosaur regression would have meant the tail moved). The test as written:
1. Load `rom_gates_dark_world.nds`, start a **normal duel** (the edit is ov3, so
   a puzzle would work too, but keep it simple).
2. Put "The Gates of Dark World" in the Field Zone.
3. A **Fiend** on either side must read **+300 ATK and +300 DEF** over its
   printed stats. Check an opponent's Fiend too — the arm has no side gate.
4. **Controls that must NOT change**: a Spellcaster and a Fairy (Yami's races,
   proving the mask really is Fiend-only), and any non-Fiend.
5. Regression controls: Yami still gives Fiend/Spellcaster +200 and Fairy -200;
   Jurassic World still gives Dinosaurs +300 (it owns the tail PART A reuses).
6. The card must place **no counters** and have no other effect.
