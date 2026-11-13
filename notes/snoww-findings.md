# Snoww, Unlight of Dark World — findings (session 2026-08-26)

Printed text (`scratch/ygoprodeck_cache.json`, id 60228941) — DARK / Fiend /
Level 4 / 1700 / 0:

> If this card is discarded to the Graveyard by a card effect: If it was
> discarded from your hand to your Graveyard by an opponent's card effect, you
> can target 1 monster in your opponent's Graveyard; add 1 "Dark World" card
> from your Deck to your hand, then Special Summon that target (if any) in
> face-up Defense Position.

Clauses:

1. **C1 (base, mandatory)** — discarded to the GY by a card effect → add 1
   "Dark World" **card** (any type) from your Deck to your hand.
2. **C2 (bonus, optional)** — if it was discarded **from your hand** by an
   **opponent's** card effect → you can also target 1 monster in your
   **opponent's** GY and Special Summon it in **face-up Defense Position**.

**STATUS: ✅ DONE. BOTH CLAUSES IN-GAME CONFIRMED BY THE USER 2026-08-27 —
clause 1 on the FIRST test, clause 2 after two rounds ("Perfect! Ship it!").
SHIPPED into `apply_all_patches` 2026-08-27 as step 29, immediately after
The Gates of Dark World.**

⚠️ **ORDERING IS LOAD-BEARING.** Snoww must be applied AFTER
`patch_gates_of_dark_world`: that patch's PART E2 is what puts its own donor into
the ARM9 Dark World set-code table, and without it Snoww's archetype search
cannot find "The Gates of Dark World" (found in-game, see below).

⚠️ **NEITHER CLAUSE-2 FAILURE WAS WHAT IT LOOKED LIKE.** Round 1 ("no prompt")
was the TEST HARNESS — 20/40 Card Destruction left the AI's Graveyard with no
monster. Round 2 ("target selected, nothing summoned") was a real bug: the
declared-pick count is `desc[+0x10]`, not `[0x0229AAFC+0x74]`. Both are written
up in full below; the second is the one worth carrying to the next card.

## CLAUSE 2 — BUILT (awaiting in-game test)

Structural clone of **Goldd, Wu-Lord of Dark World `0x1969`**. Six edits:

| part | what | where |
|---|---|---|
| E | criteria **row 1** `{0x1C18, 0xFFFF, 0x0223E1D1, 0x00010002}`, adjacent to and after row 0, count-neutral over phantom `0x14EF` | crit[551] |
| F | **LIST A** membership, count-neutral over the inert `0x0D7A` | `0x0227134C` |
| G | cid-scoped trampoline on slot5's own `bl 0x02234E78` | `0x02235610` -> `CAVE_SNOWW_ROW` |
| H | cls2 `{+04 resolver, +08 0, +0C 0x0224A115, +10 0, +14 target-decl}` | cls2[278] |
| I | three ov5 stubs, 44 + 36 + 28 B | `0x0239D1C0` / `0x0239D200` / `0x0239D230` |

**The resolver** is Goldd's two-phase skeleton with clause 1 grafted in — phase
`0x7F` -> `0x02204730(desc, 1, 1)` = Special Summon the recorded pick in
**face-up Defense**; otherwise delegate to `0x02207EF4` and, when it returns 0
with `[0x0229AAFC+0x74] != 0`, return `0x7F`.
Two things make the graft provably safe: phase `0x7F` is **unused** by the
add-to-hand resolver, and `0x02207EF4` **never touches `[0x0229AAFC+0x74]`**
(scanned over its whole extent).

⚠️ **The jump table reads from `0x02207FEE` but branches from `0x02207FF0`** —
`ADD PC,R0` adds 4, not 2. Getting that wrong points every arm one halfword
early; it cost one build here and the patch now asserts the corrected arm.

**The target declaration** is Goldd's step-0 gate then a *tail-call* to the
native picker `0x02235604` — stateless, so it consumes no step of
`[0x0229AB7C]`. The empty-Graveyard guard is **structural, not synthesised**:
`0x02235632 CMP R0,#0 ; BNE` routes a zero-candidate enumeration to
`movs r0,#1 ; pop` = skip.

**Row selection**: LIST A's rule is `row = (param != 0)`, so the trampoline
returns 1 for the donor and slot5 reads row 1, while the add-to-hand resolver's
*separate* provider call at `0x02208028` still returns 0 = row 0. This
deliberately avoids L2, which `gates_of_dark_world` has already hijacked.

**Test ROMs** (both `verify()`-green for Gates AND Snoww):
* `rom_snoww_test.nds` — sha256 `5a427e0c7bcb2c007d2103fb1cdfb976d55198ccc588e4568bbccb23449236d2`
* `rom_snoww_test_carddestruction.nds` — the same, plus every one of the 305 AI
  decks stacked with 20 Card Destruction (`_stack_opponent_decks.py`), so the
  opponent reliably discards your hand. `deck.pac` is rewritten in place at the
  same size; nothing the effect engine reads is touched.

---

(clause 1 status below)

**CLAUSE 1 IS IN-GAME CONFIRMED BY THE USER 2026-08-27, on the FIRST
test.** Discarding Snoww with The Gates of Dark World's effect runs the Deck
search and adds a "Dark World" card to the hand; the cost-discard negative
control correctly does nothing; no regressions. C2 is mapped (see the bottom
section) but NOT built and NOT tested.

The user's exact words: *"1. This works. However the only exception is i cannot
search gates of dark world because that itself isnt in the dark world archtype
table yet. 2. Nothing happens 3. No regressions"* — reading confirmed by the
user before it was acted on.

### ⚠️ ONE GAP FOUND IN-GAME, AND IT IS NOT SNOWW'S — FIX BUILT, AWAITING RETEST
**Fixed 2026-08-27 in `patch_gates_of_dark_world` PART E2** (a count-neutral
swap in the ARM9 Dark World set-code list, folded into the same ROM round-trip
as PART E). Dropped the phantom `0x0EC9`, inserted `0x1C8B` at index 14 between
Renge `0x1C18` and Dark World Grimoire `0x1D25`; count immediate
`MOV R2,#0x10` @`0x020238B8` untouched, list still strictly sorted.
New ROM: `rom_snoww_test.nds`, sha256
`7ae4a4282871def210c98c265e6571e484c5bbe887f122700bdac429bcd44440`.
Both patches `verify()` green against it. **NOT retested in-game yet.**
Registered as the new allocation pool `dw_setcode_table`.

Original finding:

**"The Gates of Dark World" cannot be fetched by the search**, because the Gates
donor **Colosseum 0x1C8B is not a member of the ARM9 Dark World set-code list**
`0x0209CA06` (setcode.dark_world_table). Snoww's row filters on `aux 0x000F`, so
a card that is not in that list is not a "Dark World" card as far as the engine
is concerned. This is a DATA gap in `patch_gates_of_dark_world`, not a defect in
Snoww's clause 1 — the search mechanism itself is confirmed working, including
its acceptance of non-monster card types. The fix belongs in the Gates module.

## BUILT (clause 1) — `otn_enhanced/cards/snoww.py`

Four edits, one of them code:

| part | what | where |
|---|---|---|
| A | 4 B `BL` hook + a 16 B ov3 stub that admits the donor to the effect-discard arm | `0x021D15EE` -> `0x021B56B8` -> `0x021D185C` |
| B | cls2 record `{0x1C18, +04 0x02207EF5, rest 0}` (Sangan/Scarr = MANDATORY), count-neutral over phantom `0x1B45` | cls2[278] |
| C | criteria row `{0x1C18, 0x000F, 0x0223CAF5, 0x0000000E}`, count-neutral over phantom `0x14E7` | crit[553] |
| D | card_prop -> Effect Monster 1700/0; name + description | card_prop[2393] |

The stub (16 B, no literal pool — both cids come off the pivot `0x1B8B` already
in r0):

```
021B56B8  adds r0,#0x8D     ; 0x1B8B + 0x8D = 0x1C18   (the donor)
021B56BA  cmp  r5,r0
021B56BC  beq  0x021B56C4
021B56BE  subs r0,#0x2D     ; 0x1C18 - 0x2D = 0x1BEB   (Lich Lord)
021B56C0  cmp  r5,r0
021B56C2  bx   lr           ; caller's BNE routes Lich Lord / reject
021B56C4  bl   0x021D185C   ; the Dark World effect-discard arm; never returns
```

Build: `.venv-1/Scripts/python.exe _build_snoww.py --text` — chains
`patch_gates_of_dark_world` then `patch_snoww` onto the clean ROM and runs BOTH
`verify()`s against the final image.
Result: **`rom_snoww_test.nds`, 129517704 B, sha256
`10802431ea15e43f5b2d139e2aee2c5712b9b11154df45a6ced920108e1c51e1`, 0 FAIL,
exit 0** (Gates' own 40-odd checks all PASS in the same ROM).

The strongest check is not the bytes but the walk: `patch_snoww` simulates the
whole `0x021D1392` chain for **all 0x2700 cids** against the committed ov3 oracle
and asserts **exactly one leaf changed** — `0x1C18`: reject -> `0x021D185C` —
with Lich Lord and all six native Dark World monsters keeping theirs.

KB: `verify_knowledge` = **325 facts, 291 PASS, 0 FAIL, 34 UNVERIFIED** (was
314/281/0/33). Six facts added: `event.dark_world_discard_arm`,
`dispatch.opponent_effect_discard_test`,
`dispatch.criteria_low_bits_are_card_type`,
`dispatch.criteria_opponent_gy_revive_handler`,
`dispatch.list_a_has_two_inert_members`, `setcode.dark_world_table` (all
VERIFIED + PASS) and `card.snoww_unlight_of_dark_world` (UNVERIFIED, awaiting
the in-game test).
Allocations registered: `donor_cid 0x1C18`, `cls2_table 0x1B45`,
`populate_table 0x14E7`, ov3 claim `(0x021B56B8, 16, "snoww")`.

Donor: **Renge, Gatekeeper of Dark World `0x1C18`** (user-approved).
Test ROM must include **The Gates of Dark World** (user requirement) — its
clause-2 effect discard is the trigger source.

---

## Confirmed (this session, with the proof)

### KB baseline
`verify_knowledge` on arrival: **314 facts, 281 PASS, 0 FAIL, 33 UNVERIFIED**
(oracles arm9 / ov3 / ov5 present, savestate `rom_all_patches.ml2`).

### Snoww is not in the NDS ROM
`scratch/cid_to_name.json` (4305 names) has no "Snoww" → donor required.

### The 3DS ships Snoww: cid 0x25F1, and it hands over BOTH criteria rows
`otn_enhanced.tools.threeds_lookup "Snoww"` → 3DS index 4762, cid `0x25F1`,
main-effect registry `0x686CBC`:

```
[1460] 000F25F1 004B1C1C 0000000E     <- C1
[1461] FFFF25F1 004A7F4C 00010002     <- C2
```

Row shape `{u16 cid, u16 aux, u32 handler, u32 word}`.

### Handler equivalence 3DS 0x004B1C1C == NDS 0x0223CAF5 (DECK search)
Proven by a card present in **both** builds — Scarr, Scout of Dark World:

```
3DS  crit[ 323] cid=196A aux=000F fn=004B1C1C word=00900002
NDS  crit[ 390] cid=196A aux=000F fn=0223CAF5 word=00900002
```

Same card, same aux, same word, exactly one row each.

### Handler equivalence 3DS 0x004A7F4C == NDS 0x0223E1D1 (opponent's-GY revive)
cid-set correlation over both registries: 3DS `0x004A7F4C` owns 9 cids, NDS
`0x0223E1D1` owns 6, **6 shared, Jaccard 0.667**; the 3 unshared are 3DS-only
cards (`0x25F1` Snoww, `0x2781`, `0x2A21`). The shared family is textually
unambiguous — every member prints "target 1 monster in your opponent's
Graveyard; Special Summon":

```
15E6 Autonomous Action Unit   cls0[ 413] 02207529 0 021F03B5 021E4D81 02235605  crit[ 211] w=00010002
1EA8 Doomkaiser Dragon        cls1[ 896] 02207529 0 021F03B5 021E51E5 02235605  crit[ 765] w=10010002
1F8C Victoria                 cls3[ 492] 02207191 0 021F03E9 021E5061 02235605  crit[ 833] w=08010002
2025 Bone Temple Block        cls0[1073] 0222C2F1 0 02200231 0        022366A9  crit[ 907] w=00910002
231F Wiseman's Chalice        cls0[1207] 02207191 0 02203229 0        02235605  crit[1227] w=00010002
24E6 Sorciere de Fleur                                                          crit[1384] w=00010002
```

**Victoria `0x1F8C` is the C2 template** ("Once per turn: You can target 1
Dragon-Type monster in your opponent's Graveyard; Special Summon that target").
Autonomous Action Unit and Wiseman's Chalice carry **word `0x00010002`
verbatim** — the same word the 3DS gives Snoww.

### aux 0x000F = the "Dark World" set code, and Renge is already in the list
ARM9 set-code thunk table `0x0209D0D8`, index `0x0F` → `0x020238B5`. That
function's only literal is `0x0209CA06`; the next thunk's list base is
`0x0209CA26`. So the Dark World cid list is **`0x0209CA06..0x0209CA24`, 16
sorted entries**:

```
0EC9(phantom) 1961 Zure   1965 Beiige 1966 Broww 1967 Brron 1968 Sillva
1969 Goldd    196A Scarr  1970 DW Lightning 1973 Gateway 1B3D Reign-Beaux
1B3E Kahkki   1B3F Gren   1B5A DW Dealings  1C18 Renge   1D25 DW Grimoire
```

`0x020238B4` has **zero** direct BL callers in arm9+ov3 (one literal reference
to the table, `0x020240EC`) — it is reachable only through the thunk table.
**Renge `0x1C18` @0x0209CA22 is already a member**, so Snoww stays a real
"Dark World" card with no table edit.

### The criteria word's LOW HALF is a card-TYPE bitmask (bits 1/2/3)
This closes the two bits `dispatch.criteria_word_fully_decoded` left undecoded.

* **bit 1 (0x0002) = MONSTER**, **bit 2 (0x0004) = SPELL**, **bit 3 (0x0008) = TRAP**.
* Anchors: Magician of Faith `0x1152` low `0x0004` — "Target 1 **Spell** in your
  GY"; Mask of Darkness `0x100C` low `0x0008` — "Target 1 **Trap** in your GY";
  and decisively **Vampire Lord `0x1522`, which owns one `0x0004` row AND one
  `0x0008` row** and prints "Declare 1 type of card (Monster, Spell, or Trap)".
* ⇒ `0x000E` = bits 1|2|3 = **"card", any type** — exactly C1's wording.

In-ROM structural twins of C1's row (same handler `0x0223CAF5`, same word
`0x0000000E`, aux = an archetype set code), both on slot1 `0x02207EF5`:

```
crit[ 188] cid=1562 aux=0000 Toon Table of Contents "Add 1 'Toon' card from your Deck to your hand."
crit[ 227] cid=1647 aux=0003 Arsenal Summoner       "FLIP: Add 1 'Guardian' card from your Deck to your hand."
```

### ⭐ The "discarded to the GY by a card effect" trigger is ONE switch arm
Simulated the hardcoded per-cid chain at `0x021D1392` inside the relocation
applier `0x021D1300` over every cid (`scratch/sim_gy_cid_switch.py`, unmodified):

```
arm 0x021D185C   7 cids  0EC9 1965 1966 1968 1969 1B3E 1B3F
                          (phantom, Beiige, Broww, Sillva, Goldd, Kahkki, Gren)
arm 0x021D1850   1 cid   1B3D  Reign-Beaux (opponent's-effect-only variant)
arm 0x021D19BE  16 cids  the known "sent to the GY by any means" family
arm 0x021D19C0  9906     reject (default)
```

Disassembled:

```
021D185C  LDR R0,[SP,#0x34] ; CMP R0,#0x0B ; BNE 0x021D1870   ; SOURCE zone == 0x0B = HAND
021D1862  LDR R0,[SP,#0x18] ; CMP R0,#0    ; BEQ 0x021D1870   ; (event code == 0x1F)
021D1868  LDR R0,[SP,#0x10] ; CMP R0,#0    ; BLE 0x021D1870   ; r3 of 0x021D1300
021D186E  B   0x021D199E                                      ; ACCEPT -> [sp+0x14]=1
021D1870  B   0x021D19BC                                      ; reject
```

**This closes `dispatch.three_hand_to_gy_movers` structurally.** The caller
`0x021C6B00` computes `r3 = 1 - kind` (`SUB R3,R6,R3` @`0x021C6CB6` with
`r6 = 1` set at `0x021C6CB0`), so the arm's `kind > 0` test means:

| mover | kind | r3 = 1-kind | verdict |
|---|---|---|---|
| `0x021C6D58` **effect discard** | 0 | **1** | **ACCEPT** |
| `0x021C6DB4` cost discard | 1 | 0 | reject |
| `0x021C6D90` UI discard | 2 | -1 | reject |

— exactly the three in-game results already recorded in the KB. It also shows
OTN implements the trigger as **hand-only**, matching the ROM's own wording on
Beiige / Broww / Kahkki / Gren ("discarded **from the hand** to the Graveyard by
a card effect").

### ⭐ The "opponent's card effect" test at RESOLVE time (Sillva's own resolver)
Sillva `0x1968` prints Snoww's two-tier shape. Its resolver `0x0221FA5C` gates
tier 2 with a **pure descriptor read** — no globals, no state:

```
0221FAA0  LDR  R0,[R4,#0x20]              ; r4 = descriptor; desc[+0x20] = packed card word
0221FAA2  LDRB R2,[R4,#0x2]               ; desc[+2] = the ACTING side
0221FAA4  LSL R1,R0,#13 ; LSR R1,R1,#31   ; bit 18 of the word
0221FAA8  CMP R2,R1 ; BEQ  skip-tier-2
0221FAAC  LSL R0,R0,#22 ; LSR R0,R0,#31   ; bit  9 of the word
0221FAB0  CMP R2,R0 ; BNE  skip-tier-2
0221FAB4  ... Sillva's own "opponent has >= 2 cards" check ...
0221FAC8  MOV R0,#0x7F                    ; advance to the tier-2 phase
```

Cross-check: `0x021D1300`'s prologue extracts **the same two bits** (`LSL #22 /
LSR #31` -> r7, and `LSL #13 / LSR #31` compared against it @`0x021D1344`) to
form `[sp+0x20]`, which is exactly the extra flag **Reign-Beaux's** arm
`0x021D1850` tests (`[sp+0x20] != 0 && r4 == r7`). Two independent sites, same
bit pair.

### ⭐ LIST A has TWO INERT MEMBERS — the two-row slot exists
LIST A `0x0227134C`, **59** entries, count immediate `MOV R2,#0x3B`
@`0x02243BF0`, rule `row = (param != 0) ? 1 : 0` @`0x02243BFA`. Two members own
**zero** criteria rows, so their membership is vestigial:

```
0x0D7A  Speed Spell - Preparation of Rites
0x0D81  Speed Spell - Stardust Shimmer
```

LIST B `0x02271314` (27 entries) has **no** member with a row-count != 2 — it is
genuinely full, and Gates of Dark World already spent its only phantom
(`0x234F`). So C2 uses **LIST A**, count-neutral over `0x0D7A`, sorted insert of
`0x1C18` between `0x1BC9` and `0x1C2A`. LIST B stays untouched.

### ⭐ Which step reads which criteria row — the crux
Both of Snoww's steps would otherwise read the **same** row:

* C1's add-to-hand resolver common body calls the param provider itself —
  `0x02208028 BL 0x02234E78`, result passed as `r2` to the criteria enumerator
  (`LDRH R1,[R5,#0]` @`0x0220802E` proves r5 is the descriptor there).
* slot5's off-field template does the same — `0x02235610 BL 0x02234E78`.

**Fix:** keep the donor out of every L-list (provider returns 0 → C1 reads
**row 0**, the Deck row) and **cid-scope slot5's provider call** so it returns
nonzero for the donor only (→ **row 1**, the opponent's-GY row). This
deliberately avoids **L2**, which `patch_gates_of_dark_world` has already
hijacked (`CAVE_GDW_L2`, retargeted `bl 0x02022E14` @`0x02234E96`).

### The donor: Renge, Gatekeeper of Dark World 0x1C18
| check | result |
|---|---|
| type | **Normal Monster**, vanilla flavour text, non-competitive |
| card_prop | idx **2393**, DARK / Fiend / **Level 4** / 100 / 2100 |
| Dark World set code | **yes**, `0x0209CA22` |
| cls0 / cls1 / cls2 / cls3 | **no records** (all four tables swept) |
| criteria registry | **no row** |
| name blob (E) | **31 B** >= `"Snoww, Unlight of Dark World"` (28 B) — in place |
| desc blob (E) | **173 B** — the new description fits in place |

Zure `0x1961` is the only other Normal-Monster Dark World card; its E name blob
is **26 B < 28 B** → rejected. Phantom `0x0EC9` — already in BOTH the set-code
list and the trigger arm — has **no card_prop record** → cannot be a donor.

### The hook site for admitting the donor to the trigger
`0x1C18` currently falls to the reject leaf `0x021D19C0`. Traced terminal node:

```
021D15EE  ADD R0,#0x60   ; r0 = 0x1B8B (literal @0x021D1590) + 0x60 = 0x1BEB
021D15F0  CMP R5,R0
021D15F2  BNE 0x021D15F6
021D15F4  B   0x021D1902 ; Lich Lord 0x1BEB — LIVE
021D15F6  B   0x021D19C0 ; reject
```

Interval `(0x1BB4, 0x1C38)`, entered only from `BGT 0x021D15EE` @`0x021D15D8`.
Branch scan over `0x021D1300..0x021D1E00`: the ONLY inbound branches near it are
`0x021D15D8 -> 0x021D15EE`, `0x021D15E8 -> 0x021D15EC`, `0x021D15F2 ->
0x021D15F6`, `0x021D15C8 -> 0x021D15F8`. **Nothing branches to `0x021D15F0` or
`0x021D15F2`**, so the first two halfwords can be replaced by a 4-byte `BL`.
`0x1C18 = 0x1B8B + 0x8D` and `0x1BEB = 0x1C18 - 0x2D` ⇒ the stub needs **no
literal pool**.

### Free ov3 dead block for the stub
`OV3_DEAD_BLOCKS` free (unclaimed) blocks: `0x021B56B8` (16 B, phantom `0x133D`,
**owners: []**), `0x021B58D0` (12), `0x021B5AAA` (10), `0x021B594A` (8),
`0x021B5952` (8), plus the 16 B tail of `0x021B54E0` and the 22 B tail of
`0x0225F240`. The stub is **exactly 16 B** → `0x021B56B8` is an exact fit, and
unlike `0x0225F240` it needs no arm neutralisation.

### Count-neutral drop candidates (rigorous scan)
* **cls2**: phantom **`0x1B45` (cls2[245])** — no card_prop, owns exactly one
  cls2 row, appears **exactly once** as an aligned u32 anywhere in ov3 (that
  row) and **never** in ARM9. Insert index for `0x1C18` is **279**.
* **criteria registry**: insert index for `0x1C18` is **554**. Best phantoms by
  fewest u16 occurrences anywhere (ov3+arm9): `0x14E7` crit[165] (3),
  `0x14EF` crit[168] (3), `0x0E4A` crit[33] (3). For calibration the phantoms
  already used by shipped patches score 8-13.

### The add-to-hand resolver 0x02207EF5 defaults to "add exactly 1"
`0x02207EF4` opens `PUSH ... ; MOV R4,#1` and runs a per-cid switch whose arms
only **override r4 (the count)** before `B 0x02207FCC` (the common body). 105
cls records use it, incl. Scarr, Toon Table of Contents, Arsenal Summoner,
Terraforming, Reinforcement of the Army, E-HERO Stratos.

---

## ⚠️ CLAUSE 2 FAILED ITS FIRST IN-GAME TEST (2026-08-27) — STRIKE 1

User's exact words: *"1. Clause 2 does not let me SS from the opponents GY
2. Negative control passes 3. Couldnt verify 4. No regressions"*, then, on being
asked to disambiguate: **no target prompt at all**, and **clause 1's "Dark World"
Deck search DID still happen** on the opponent's discard.

### What that rules IN (all confirmed working on the opponent's-discard path)
* the trigger arm `0x021D185C` fires for an OPPONENT-initiated effect discard;
* `find_event_handler` returns our cls2 record;
* the activation state machine reaches slot1 and clause 1 resolves.

### What that rules OUT
* **It is NOT the row selector, the criteria row, LIST A, or the resolver.**
  None of those can suppress the *prompt* — a prompt failure is upstream of them.
* **slot5 IS invoked.** Read off the activation state machine at `0x02217FC2`:
  `LDRB R0,[R5,#8]` (the "slot5 already done" flag) -> `BL 0x0224AEA4` (the
  getter: `find_event_handler` then `[rec+0x14]`, nonzero for us) -> `BL 0x0224AE84`
  (the call). A return **> 0 marks it done and advances**, which is exactly the
  skip convention the stub implements. So the block was entered and our stub ran.
* **The slot5 ABI is right**: `0x0224AE92` calls it with `r0 = r5 = the
  descriptor`, `r1 = r4` — the same registers Goldd's slot5 reads.
* **The gate's arithmetic is not the bug.** Instruction-for-instruction it is
  Goldd's, only with the operand registers renamed and the word re-loaded instead
  of kept in a second register:

```
Goldd  LDR R2,[R4,#0x20] ; LDRB R1,[R4,#2] ; LSL R3,R2,#13 ; LSR R3,R3,#31
       CMP R1,R3 ; BEQ skip ; LSL R2,R2,#22 ; LSR R2,R2,#31 ; CMP R1,R2 ; BNE skip
ours   LDRB R3,[R0,#2] ; LDR R2,[R0,#0x20] ; LSL R2,R2,#13 ; LSR R2,R2,#31
       CMP R3,R2 ; BEQ SKIP ; LDR R2,[R0,#0x20] ; LSL R2,R2,#22 ; LSR R2,R2,#31
       CMP R3,R2 ; BNE SKIP
```

### CONTROL RESULT (2026-08-27): *"Broww draws 2 and Goldd offers"*
So the opponent-effect FLAG is populated on the Card Destruction path (Broww's
bonus draw is a binary probe of exactly that), and the NATIVE slot5 template does
prompt. `desc[+0x20]` / `desc[+2]` are therefore fine and the gate arithmetic is
exonerated. That kills the "surviving hypothesis" below.

### ⭐ THE LIKELIEST CAUSE IS THE TEST HARNESS, NOT THE PATCH
The native picker's zero-candidate exit produces EXACTLY "no prompt at all":

```
0223562E  BL  0x02243FA8      ; enumerate candidates for the selected criteria row
02235632  CMP R0,#0
02235634  BNE 0x0223563A
02235636  MOV R0,#1           ; ZERO candidates -> return 1 = SKIP, no prompt
02235638  POP {R3,R4,R5,R6,R7,PC}
```

Row 1's word `0x00010002` has low half bit 1 = **MONSTER**, so Spells and Traps
in the opponent's Graveyard do not count. `_stack_opponent_decks.py` was run at
**20 of 40** copies, so the AI's hand when it fires Card Destruction is mostly
SPELLS -- its own discard therefore fills its Graveyard with Spells and leaves
**no monster for Snoww to target**.

Two independent corroborations, so this is evidence rather than a bare guess:
1. **Goldd offering fits it.** Goldd targets cards your opponent CONTROLS (the
   field, populated); Snoww targets their GRAVEYARD. Only the Graveyard one was
   plausibly empty.
2. **It also proves the ROW SELECTOR works.** Had the trampoline failed and slot5
   read ROW 0 (Deck / any "Dark World" card), the enumeration would have found
   something -- clause 1 had just searched that row successfully -- and a WRONG
   prompt would have appeared. Getting NO prompt means slot5 selected a row whose
   candidate list was genuinely empty, i.e. row 1 behaving correctly.

**Harness fixed**: rebuilt at `--copies 8`, so the AI keeps 32 real cards and its
discarded hand should contain monsters.
⚠️ RETEST BEFORE CHANGING ANY CODE. If the prompt appears with a monster
actually in the opponent's Graveyard, there was never a patch bug.

### The (now killed) surviving hypothesis — kept for the reasoning
`desc[+0x20]` and/or `desc[+2]` are not what Goldd expects **on this descriptor**.
Note that with `desc[+0x20] == 0` the gate skips for EITHER side (bit18 = bit9 = 0
makes one of the two compares fail whatever `desc[+2]` is) — which matches the
observed "no prompt in both the opponent case AND the negative control".
⚠️ That also means **the negative control passing is NOT evidence the gate works**;
it is equally consistent with the gate always skipping. Do not count it.

### NEXT EXPERIMENT — one duel, three native controls, NO rebuild
All three cards are already in the ROM and Card Destruction discards the WHOLE
hand, so holding them together tests everything at once:

| card | what it proves |
|---|---|
| **Broww 0x1966** | binary probe of the opponent-effect FLAG with no targeting UI: "Draw 1 card, plus another if discarded from your hand by an opponent's card effect". **Draw 2 = the flag is populated. Draw 1 = it is not**, and that is the root cause. |
| **Goldd 0x1969** | the slot5 template itself: does the NATIVE card offer "destroy up to 2 cards your opponent controls"? |
| **Sillva 0x1968** | the same flag read from a RESOLVER instead of slot5 ("opponent returns exactly 2 cards from their hand"). |

Outcomes and what each means:
* Broww draws 2 **and** Goldd offers -> the native slot5 path works; diff our
  record/stub against Goldd's field by field.
* Broww draws 2, Goldd silent -> the flag is fine but slot5 is the wrong home;
  move the gate into the RESOLVER (Sillva's shape) and drop the slot5 gating.
* Broww draws 1 -> the opponent-effect flag is not populated on the Card
  Destruction path at all; the discriminator must be re-derived, and OTN's own
  Goldd/Broww/Sillva tier-2 effects are themselves dead here.

## ⭐⭐ CLAUSE 2 BUG #2, FOUND AND FIXED (2026-08-27) — THE PICK COUNT IS desc[+0x10]

After the harness fix the user reported: *"Okay it let me select a card: see .ml3
but nothing happend afterwards .ml4"*, clarified as **"I targeted a monster but
that monster did not get special summoned to my board"**, with clause 1 fine.
Savestates `rom_snoww_test_carddestruction.ml3` / `.ml4`.

That isolated the fault to the resolver's phase-`0x7F` arm and exonerated the
target declaration, the criteria rows, LIST A and the row selector.

**ROOT CAUSE.** The stub gated on `[0x0229AAFC+0x74] != 0`, copied from Goldd.
**Nothing on the shared-picker path ever writes that word** — scanned every
`STR Rn,[Rm,#0x74]` in ov3: there is not one inside Goldd's slot5
(`0x0223847C..0x02238560`) nor inside the off-field picker
(`0x02235604..0x02235800`). `+0x74` is Goldd's own bespoke slot5 machinery.

**THE REAL COUNTER IS THE BYTE `desc[+0x10]`**, and this was already a VERIFIED
KB fact (`dispatch.pick_record_and_resolver_readback`) that I failed to apply:

* the off-field picker's sub-step 2 at `0x0223569E` reads the pick's zone code
  (`bl 0x0219C534`) and branches `CMP R0,#0xA ; BGT` -> board recorder
  `0x022347B0` for zone <= 0x0A, else the list recorder `0x02234880`.
  **A Graveyard pick is zone 0x0E, so it takes the LIST recorder.**
* both recorders bump the same byte: `STRB R0,[R4,#0x10]` @`0x0223480E` and
  `STRB R0,[R5,#0x10]` @`0x022348B8`.

So phase `0x7F` was never entered and `0x02204730` never ran. Exactly the
symptom.

**FIX** (`res_stub`, 44 B -> 48 B): keep the DESCRIPTOR in r6 at entry (r0 is the
return value after the clause-1 delegation) and gate on
`LDRB R5,[R6,#0x10] ; CMP R5,#0` instead of `LDR R5,[R4,#0x74]`.

**LESSON WORTH CARRYING**: cloning a native card is only safe field-by-field.
Goldd's *skeleton* was right, but one of its reads was private to its own
bespoke slot5 — and the shared picker it was swapped for keeps its state
somewhere else entirely. When you swap a component, re-derive every value the
surrounding code reads; do not inherit them.

**Rebuilt** `rom_snoww_test.nds` sha256
`976be61646807e4954d76bbbd738e6fc0bc2121161ee42147550417ac151623c`, and the
Card Destruction harness on top of it (8 copies). Both patches verify green.
**AWAITING RETEST.**

## Ruled Out (hypothesis + the evidence that killed it)

* **Re-key the phantom `0x0EC9` node so `0x1C18` reaches arm `0x021D185C`.**
  The chain is a **sorted binary search**; `0x1C18 > 0x0EC9` never visits that
  node. This is the documented Eclipse Wyvern failure
  (`event.sent_to_gy_cid_switch`: bytes correct, stub disassembled perfectly,
  did nothing in-game).
* **Steal Lich Lord's arm** by changing `ADD R0,#0x60` to `#0x8D`. `0x021D1902`
  is live and load-bearing: Lich Lord, King of the Underworld reads "If this
  card is Tributed by a card effect and sent to the GY: Add this card from your
  GY to your hand."
* **A pure-data trigger via the leave-mask table `0x0226EC1C`.**
  `event.leave_mask_is_field_only`: read at exactly one site, the field-leave
  dispatcher, **never** on a hand discard.
* **Host the switch stub in the ov5 cave.** `0x021D1300` is shared engine code
  that runs in puzzles, where overlay 41 evicts ov5. The stub must be **ov3**.
* **Use L2 membership to give slot5 row 1.** `patch_gates_of_dark_world` has
  already hijacked the L2 lookup (`CAVE_GDW_L2`). Avoided entirely by
  trampolining slot5's own provider call instead.
* **`data/over_the_nexus/decompiled/cards/*.py` for the Dark World cards.**
  Confirms `dispatch.decompiled_cards_off_by_one` first-hand: the file named
  `c06502_...Broww...py` lifts RAM `0x0220731C`, which is **Beiige's** slot1.
  The directory is off by one record; do not use it.

---

## Open Questions (must be closed before the code they gate)

* ~~**U0 (C1, blocking)**~~ — **CLOSED this session.** `0x021268EC` has **exactly
  one** reference in the entire build (the literal at `0x0202E4DC`), and nothing
  ever reads back through it; the `0x1C18` there is a constant being *written*,
  never compared against a card's cid. No per-cid gate. Original note below.
* ~~**U1 (C1, blocking)**~~ — **CLOSED this session.** The add-to-hand resolver's
  per-cid switch (`0x02207EF4`, pivots `0x220C` / `0x200B` / `0x23E4`; named arms
  Dragunity Corsesca, Black Whirlwind, Ojama Blue, Vylon Delta, Gishki Erial,
  Gem-Turtle) routes `0x1C18` to the **default body `0x02207FCC` with r4 = 1** —
  the same arm as Scarr, Toon Table of Contents, Arsenal Summoner and Stratos.
  The patch asserts this at build time and in `verify()`.

* **U0 (original note, now closed).** `donor_scan 0x1C18` reports ENTANGLED on one hit:
  `arm9:0x0202E4D8`, a literal-pool word `0x00001C18` whose **only** consumer is
  `0x0202E4B2 LDR R1,[PC,#0x24]` -> `STRH R1,[R0,#0x2C]` with `r0 = 0x021268EC`,
  immediately followed by `MOV R1,#8 ; STRH R1,[R0,#0x2E]`. It is an
  **unconditional store of a constant**, not a cid comparison, so it is almost
  certainly a numeric field — but classify the struct at `0x021268EC+0x2C`
  before building. (Calibration: the shipped Eclipse Wyvern donor `0x1859` is
  also reported ENTANGLED, on a fusion recipe.)
### ⭐ CLAUSE 2's TEMPLATE IS GOLDD, WU-LORD OF DARK WORLD 0x1969 (2026-08-27)
Goldd's PRINTED TEXT is structurally identical to Snoww's — same trigger, same
opponent gate, same "target ...; \<base action\>, then \<targeted action\> (if any)":

> If this card is discarded to the Graveyard by a card effect: If it was
> discarded from your hand to your Graveyard by an opponent's card effect, you
> can target up to 2 cards your opponent controls; Special Summon this card from
> the Graveyard, then destroy those targets (if any).

`cls2[192] = {+04 0x0221FB51, +08 0x021DE7C9, +0C 0x0224A115, +10 0, +14 0x0223847D}`

**Its resolver `0x0221FB50` is a 2-phase machine** — the exact skeleton Snoww needs:

```
phase [0x0229AAFC+0x70] == 0x80 -> BL 0x021F0384 (can-I-SS); if 0 return 0
                                   BL 0x0220731C   <- the BASE action
                                   if [0x0229AAFC+0x74] != 0 -> return 0x7F else 0
phase                     0x7F  -> BL 0x022048A4   <- the TARGETED action
                                   return 0
```

`[0x0229AAFC+0x74]` is the "were any targets declared" counter = the printed
"(if any)".

**Its slot5 `0x0223847C` step 0 IS the opponent gate + the optional prompt** — see
the disassembly in the session log: bit 18 vs `desc[+2]`, bit 9 vs `desc[+2]`,
then a candidate count (`0x0224AA94`), then the prompt `0x0219A9B4`; it returns
**0 = stay in the step machine** and **1 = SKIP**.

## Open Questions — U2..U5 ALL CLOSED 2026-08-27

* ~~**U2**~~ — **CLOSED.** `0x02235610` is stock: it appears in the BL-caller
  census of the param provider `0x02234E78` (59 callers), so nothing has
  retargeted it. Because it is shared, the trampoline **must be cid-scoped**;
  the descriptor is in `r5` (`LDRH R1,[R5]` @`0x02235628`).
* ~~**U3**~~ — **CLOSED.** `0x02204730(r0 = desc, r1 = count/mode, r2 = POSITION)`,
  read off `0x02207191`'s tail (`ADD R0,R6 ; ADD R1,R4 ; ADD R2,R5 ; BL 0x02204730`).
  The position argument is stashed at `[sp+8]`; the `r5` inside `0x02204730` is
  an unrelated local (it is re-derived from a per-cid compare at `0x02204752`),
  so passing `r2 = 1` really does select **face-up Defense Position**
  (`dispatch.ss_from_list_position_mode`). Five callers total.
* ~~**U4**~~ — **CLOSED, and it CORRECTS my earlier reading of
  `event.optional_trigger_is_record_shape`.** The "you can" for a HALF-optional
  card is not in slot3/slot4 at all: Goldd's slot3 is the generic
  `0x0224A115` (`movs r0,#2`) and its slot4 is 0. The optionality lives in
  **slot5 step 0**, which prompts with `0x0219A9B4` and is skipped wholesale when
  the gate fails. So ONE cls2 record CAN be half-optional.
* ~~**U5**~~ — **CLOSED.** slot5 returning **1** ends the step machine without
  requesting a target, which is exactly "no prompt on your own discard".

### ⚠️ NEW RISK FOUND WHILE CLOSING U5 — EMPTY CANDIDATE LIST FREEZES
`card.gates_of_dark_world_clause2` records that the engine **FROZE** when its
selection ran with an empty candidate list. Goldd guards this with the count call
`0x0224AA94` before prompting. Goldd's candidates are ON THE FIELD, so that
sweeper is right for it; **Snoww's are in the opponent's GRAVEYARD**, so the
count must instead come from the criteria row — `0x02243FE0(side, cid, param)`,
the counting sibling of the enumerator, with a NONZERO param (LIST A rule) to
select row 1, and the probe side from `dispatch.criteria_probe_side_is_xor_desc6`
(`desc[+2] ^ desc[+6]`). **Snoww's slot5 wrapper MUST make this check before
delegating**, or an opponent with an empty Graveyard will hang the duel.

### Superseded U-list (kept for the reasoning)
* **U2 (C2).** Confirm nothing else already retargets
  `0x02235610 BL 0x02234E78`, and that the descriptor really is `r5` there.
* **U3 (C2).** The exact ABI of `0x02204730(desc, r4, r5)` and how it reads the
  slot5-recorded pick. (`dispatch.ss_from_list_position_mode`: r5 = 1 is
  Defense, r5 = 2 is player-chooses; every path of `0x02207191` ends there.)
* **U4 (C2).** The slot3/slot4 pair that makes **only** the C2 half optional —
  `event.optional_trigger_is_record_shape` warns a record cannot be
  half-optional, so both must be descriptor-branching stubs.
* **U5 (C2).** Whether `0x02235605` can be suppressed cleanly when the Sillva
  test fails, so no target prompt appears on your own discard.
* **U6 (cosmetic).** Japanese/Korean name slots are 20 B < 28 B; their desc
  slots are 110 / 118 B. Those languages will relocate or print "KEPT: no room".

---

## Next Experiment

**1. THE IN-GAME TEST OF CLAUSE 1 — this is the only thing that can advance the
card.** Load `data/over_the_nexus/working/rom_snoww_test.nds` in melonDS, in a
**normal duel**. Deck: Snoww (the ex-Renge card), The Gates of Dark World, at
least one other Fiend, at least one other "Dark World" card left in the Deck.

* Activate Gates' once-per-turn effect: banish 1 Fiend from your GY, then
  **discard Snoww** (it is a Fiend, so it is a legal discard).
  -> expect a **Deck search for a "Dark World" card of ANY type** (monster,
  Spell or Trap) added to your hand, and Gates' own "then draw 1" still
  resolving.
* NEGATIVE CONTROL: discard Snoww as a **cost** (e.g. Fabled Valkyrus).
  -> expect **nothing** (relocation kind 1 is rejected by the arm).
* REGRESSION: discard **Beiige** with Gates -> it must still Special Summon
  itself. And Gates clause 1 must still give every Fiend +300 ATK/DEF.

If the search does not appear, ask for a savestate pair (before / after the
discard) rather than reasoning from prose.

**2. Then clause 2** — close U2..U5 first, then build PARTs E-I as mapped in
the section below. Do **not** write clause-2 code while any of U2..U5 is open.

**3. Do NOT wire `patch_snoww` into `apply_all_patches`** until the user
explicitly approves shipping.
