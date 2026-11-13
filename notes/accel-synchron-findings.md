# Accel Synchron — findings (live)

Session 2026-09-03. **Phase 1 = the Synchro chassis only.** Clauses 1–3 are out of
scope this session (user-agreed).

## *** PHASE 1 IN-GAME CONFIRMED BY THE USER 2026-09-03, ALL EIGHT ORACLES ***

On `rom_accel.nds` sha256 `7225bc51e3b5c751f3976f263ec63355b3083e385b57eaeb94922e1bada9cb8e`.
Checks 1–6 and 8 answered "Confirmed" verbatim. Check 7 as originally written was
**an invalid test of mine** — Tuning adds a "Synchron" from your **Deck**, and an
Extra Deck monster is never in the Deck, so it could never have reached this card
whatever its set code. The user's words: *"It is in the extradeck, so it cannot be
searched by tuning"*, and then, on the substitute oracle: *"The deck editor filter
worked, it appeared under related cards in the tuning related cards. So it IS a
synchron card."*

**So an effectless FUSION monster really does convert into a fully working SYNCHRO
monster**, by data alone — no injected code, no ov5 cave slot. What that measured,
clause by clause:

| # | Oracle | Result |
|---|---|---|
| 1 | Deck editor: Accel Synchron, Lv5 DARK Machine Synchro **Tuner** 500/2100, Synchro frame, in the **Extra Deck** | **CONFIRMED** — and this was the genuinely unverified one, since the BL sweep covered ARM9 + ov3 only |
| 2 | Polymerization does **not** offer it for a Fusion Summon | **CONFIRMED** |
| 3 | Synchro Summons with 1 Tuner + non-Tuners totalling Level 5 | **CONFIRMED** (positive control) |
| 4 | Also summons with 1 Tuner + **two** non-Tuners totalling 5 | **CONFIRMED** — this is what proves LIST_A **absence** gave the printed "1+ non-Tuner" form rather than "exactly 1" |
| 5 | Materials not totalling Level 5 are refused | **CONFIRMED** (negative control) |
| 6 | The summoned card is itself usable as the **Tuner** for another Synchro Summon | **CONFIRMED** — card_type 39 really is read as a Tuner |
| 7 | "Synchron" set-code membership | **CONFIRMED via the deck-editor archetype filter** — it appears under Tuning's *related cards*. That is `has_set_code` reader `0x0202A358`/`0x0202A3F0` per `archetype.setcode_4c_is_monster_only`, the ONLY consumer of set code 0x4C that can reach an Extra Deck monster |
| 8 | No effects fire (clauses 1–3 unimplemented) | **CONFIRMED** |

⚠️ **What check 7 does and does not prove.** It proves the set-code table edit took
and that the engine reads this cid as a "Synchron". It does **not** exercise a
duel-time consumer, because none exists for an Extra Deck monster: all three
criteria-row consumers of aux 0x4C search the Deck or GY. Recorded so a later
session does not mistake this for a duel-path confirmation.

Everything below is the supporting evidence, gathered before the test.

Printed text (from `scratch/ygoprodeck_cache.json`, grepped this session — NOT recall):

```
Accel Synchron   Synchro Tuner Monster / DARK / Machine / Level 5 / 500 / 2100
1 Tuner + 1+ non-Tuner monsters
Once per turn: You can send 1 "Synchron" monster from your Deck to the GY, then
activate 1 of these effects;
* Increase this card's Level by the Level of the sent monster.
* Reduce this card's Level by the Level of the sent monster.
During your opponent's Main Phase, you can (Quick Effect): Immediately after this
effect resolves, Synchro Summon using this card you control. You can only Synchro
Summon "Accel Synchron" once per turn.
```

| # | Clause | This session |
|---|--------|--------------|
| 0 | `1 Tuner + 1+ non-Tuner monsters` + identity + "Synchron" membership | **DONE — in-game confirmed 2026-09-03** |
| 1 | Once/turn: send 1 "Synchron" monster from Deck to GY | later |
| 2 | …then raise **or** lower this card's Level by the sent monster's Level | later |
| 3 | Opponent's Main Phase Quick Effect: Synchro Summon using this card; hard once/turn | later |

Clause 0 is now shipped and in-game confirmed; clauses 1-3 remain unimplemented,
so a future session must not regress the chassis above.

---

## Confirmed

### KB health (this session)
`verify_knowledge` at session start → **410 facts, 373 PASS, 0 FAIL, 37 UNVERIFIED**.
After contributing this session's five facts → **421 facts, 384 PASS, 0 FAIL,
37 UNVERIFIED**. Oracles arm9=yes ov3=yes ov5=yes savestate=rom_all_patches.ml2.

**Facts contributed** (all VERIFIED with closed proofs, all passing):
`carddata.card_genre_type_tags`, `carddata.fusion_to_synchro_conversion`,
`dispatch.card_category_hub`, `dispatch.extra_deck_enumerator`,
`synchro.no_cid_whitelist`.

### C1. `card_type` is bits [32:38] of the 8-byte `card_prop` record
Fusion(no effect) = **5**, Fusion Effect = 7, Synchro = 35, Synchro Effect = 37,
**Synchro Tuner Effect = 39**. `0x0202ABF8(cid)` returns `card_type >> 1`.
Verified by decoding all 4305 records out of `bin2.pac`/`card_prop.bin` this
session (`carddata.card_prop_era2_bitfield` also passes).

**There is exactly ONE card_type-39 card in the game: Formula Synchron 0x239E**
(card_prop idx 4065, raw `0x00CE08674B05239E`). It is therefore the reference
record for the conversion.

### C2. ⚠️ THE FIND: `card_genre.bin` carries the Fusion/Synchro/Tuner tags
`card_genre.bin` is a 4305 × 8-byte u64 array in `bin2.pac`, indexed **parallel to
`card_prop.bin`** (same index, verified: both report 4305 entries). Whole-table
census this session:

| bit | meaning | evidence |
|---|---|---|
| 21 | "Special Summon only / nomi" | set on all 147 Fusions and all 140 Synchros |
| **29** | **Fusion** tag | set on **all 147** card_type-5 and -7 records; **0** Synchros |
| **36** | **Synchro** tag | **139 of 140** Synchros (2/2 type-35, 136/137 type-37, 1/1 type-39); **0** effectless Fusions |
| **35** | **Tuner** tag | **all 178** Tuner-typed cards (types 31/33/39) carry it |

The tags also land on cards whose *text* mentions the keyword (221 records carry
bit 35 against 178 actual Tuners), so they are **genre/keyword tags**, not the
summon classifier — the classifier is `card_category` (C3).

Measured records: Formula Synchron 0x239E `0x0000001800200004` (bits 2,21,35,36);
Gaia Knight 0x1E11 (effectless Synchro) `0x0000001000200000` (bits 21,36);
every effectless Fusion checked (0x1225, 0x11DB, 0x0FB5) `0x0000000020200000`
(bits 21,29).

⇒ Target genre for our card = **`0x0000001800200000`** (bits 21, 35, 36) =
Formula's record with bit 2 cleared (bit 2 is Formula's own effect keyword).

**Why this matters:** `patch_w_nebula_meteorite` already proved that a one-field
`card_type` flip is not enough (Spell→Trap "renders a glitched card frame and
freezes when the card is selected"). This is the Fusion→Synchro equivalent, and a
naive `card_type` edit would have left the card tagged Fusion in the genre file.

### C3. The duel path: one category hub, two gates
BL/jump-table sweep of `arm9.bin` + `nds_overlay_3.bin` this session.
**Fusion-vs-Synchro is never decided at `0x0202ABF8`** — none of its 19 callers
compares the result against 2/3 or 17/18/19. It routes through:

- **`0x02022D70 card_category(cid)`** — `bl 0x0202ABF8`, `cmp r0,#0x15`, then a
  22-entry halfword jump table at **`0x02022D88`** (targets relative to
  `0x02022D8A`). **Fusion (`ct>>1` 2, 3) → 3. Synchro (17, 18, 19) → 0xA.**
  Token → 9, Ritual → 2, Spell → 7, Trap → 8, Dark Synchro (`ct>>1` 21) → 0xB.
- **`0x0202303C is_fusion`** = `card_category == 3` (`cmp r0,#3`) → **1 → 0**.
- **`0x02023050 is_synchro`** = `card_category ∈ {0xA, 0xB}` → **0 → 1**.
- **`0x0202307C is_extra_deck`** tests `#3` / `#0xA` / `#0xB` → **UNCHANGED**.
  This is why the conversion does not disturb Extra-Deck residency, deck legality
  or zone placement.
- `0x02023110 is_tuner` → **0 → 1** (39>>1 = 19 is in its accept set
  {15,16,19,20}); `has_effect` (entry `0x02023008`) → **0 → 1**.

### C4. The Extra-Deck enumerator and the two summon gates
**`0x0223BE40`** (ov3) is the Extra-Deck walker, pinned by its own literal pool at
0x0223BFC4–0x0223BFD0: per-player stride `0xB3C`, count at `player+0x18`, array at
`player+0x4E4`, downstream zone id `0xC`. Matches `otn-extra-deck-array`.
Filter-flag bits it applies:

| flag | check | site |
|---|---|---|
| 0x02 | `is_fusion` 0x0202303C | 0x0223BF16 |
| 0x04 | `is_synchro` 0x02023050 | 0x0223BF26 |
| 0x10 | `can_fusion_summon` **0x0223298C** | 0x0223BF60 |
| 0x20 | `can_synchro_summon` **0x02249540** | 0x0223BF76 |

- **`0x0223298C can_fusion_summon`** hard-rejects at its FIRST check
  (`bl 0x0202303C; cmp r0,#0; bne; movs r0,#0`) — before it reaches
  `bl 0x02231E08` at 0x02232A32. **So after the type flip the fusion recipe row
  is dead on the player's Fusion-Summon path.**
- **`0x02249540 can_synchro_summon`** gates on `is_synchro`, then calls
  `0x02248248` (minimum materials) and **reads the card's LEVEL via `0x0202ABD8`**
  before looping the field with the per-slot validator `0x02249AFC`.
  ⚠️ **The donor's Level field becomes live and was not before.**

### C5. There is NO Synchro cid whitelist
- Per-Synchro switch `0x02249D1C` names only 0x208E / 0x211B / 0x21CB / 0x239D /
  0x239F. **Every other cid falls to the default arm `0x02249D66`, which is an
  ACCEPT path** — it only rejects a Tuner sitting in a non-Tuner slot.
- The big material-rule switch `0x02248A88` has **20** fallthrough sites branching
  to the accept leaf `0x022494C4` (`movs r0,#1`) against **1** reject site.
- The three per-cid tables are all **opt-in exception lists**:

| table | role | donor 0x11A3 (4515) |
|---|---|---|
| `0x02275AD8` (21 × u16) | min 3 materials | absent → **min 2** |
| LIST_A `0x02275AB8` (16 × u16) | "exact, extras forbidden" | absent → **"N or more"** |
| `0x02248280` | 2 leading Tuners (0x239F, 0x24B2 only) | absent → **1 Tuner** |

⇒ a cid in none of them gets *2 materials minimum, 1 Tuner, generic material
rules* = **exactly the printed "1 Tuner + 1+ non-Tuner monsters"**, with nothing
to insert anywhere. LIST_A absence is REQUIRED for the "1+" form
(`synchro.list_a`) — **never add the donor to LIST_A.**

### C6. The one reason the fusion recipe row still has to die: the CPU AI
The AI special-summon planner at **`0x022112B2` / `0x0221132E`** calls
`is_extra_deck` (0x02211298) and then `fusion_material_count` (0x02231E08)
**without** an `is_fusion` gate, so it would visit the converted card and read a
stale material count of 2. Blanking the material slots makes its follow-up check
(`0x02232AF0`) fail — the benign outcome.
The only OTHER table-A iterator, the reverse lookup `0x02231ECC`, has **zero** BL
callers and zero literal references in either image — dead code.

### C7. "Synchron" set-code table and the slot the user named
`setcode.synchron_table` (VERIFIED, re-run this session): set code **0x4C**, thunk
`0x02023E1D`, sorted **15**-entry u16 array @ **0x0209C968**, count hardcoded
`movs r2,#0x0F` @ 0x02023E20, pool word @ 0x02023E24, **one** consumer.

Stock contents dumped this session:
```
[ 0] 0x0D6B Speed Spell - Deceased Synchron   <- the slot the user assigned
[ 1] 0x1E07 Junk Synchron        [ 2] 0x1E14 Nitro Synchron
[ 3] 0x1E4E Synchro Deflector    [ 4] 0x1EA1 Road Synchron
[ 5] 0x1EBE Turbo Synchron       [ 6] 0x1F46 Hyper Synchron
[ 7] 0x20F7 Quickdraw Synchron   [ 8] 0x21A7 Drill Synchron
[ 9] 0x224C Changer Synchron     [10] 0x229E Synchron Explorer
[11] 0x239E Formula Synchron     [12] 0x23EE Fleur Synchron
[13] 0x2414 Bri Synchron         [14] 0x2501 PHANTOM (spent by unknown_synchron)
```
Dropping 0x0D6B and inserting 0x11A3 keeps it a sorted 15-entry set (0x11A3 lands
at index 0). Reusable helper exists:
`patch_unknown_synchron.add_synchron_member(out, insert_cid, phantom_cid)` — it
asserts the pool word, the count immediate and strict sortedness before writing,
and is idempotent.

**Cost of the drop:** 0x0D6B stops counting as a "Synchron" *card*. Its own effect
is untouched (it keeps cls0 record[3], criteria rows 1–3, its registry entry). It
is a **Spell**, so no monster-filtered Synchron search — `Tuning` 0x23A2, criteria
row 1269 @0x02274F40, aux 0x004C — could ever have found it.

`patch_unknown_synchron.verify()` checks membership + count + sortedness, never a
slot address (`setcode.slot_addresses_are_not_stable`), so it survives this edit.
It drops 0x2501, we drop 0x0D6B — different targets, order-independent.

⚠️ **The KB had already reached this conclusion independently** and I only found it
after choosing the slot. `archetype.setcode_4c_is_monster_only` (VERIFIED) says set
code 0x4C has exactly three consumers, all criteria rows, and every one carries low
half `0x0002` = MONSTER — so *"a 'Synchron' SPELL or TRAP can never be fetched by
anything, so the list's two non-monster members — **Speed Spell - Deceased Synchron
0x0D6B** and Synchro Deflector 0x1E4E — are **INERT and are the drops of last resort
for a future Synchron**."* The user picked exactly the slot the KB nominated.

That fact also pins the **precise** residual cost, which is narrower than I first
wrote: the only non-criteria consumers of `has_set_code` are the **deck-editor
archetype filters `0x0202A358` / `0x0202A3F0`**, so dropping an inert member is
*"cosmetic and confined to the deck editor"* — i.e. 0x0D6B will no longer appear
under a "Synchron" filter when browsing cards. Nothing in a duel changes.

### C8. The donor: Bracchio-raidus 0x11A3
All 39 effectless Fusion monsters (card_type 5) were decoded and their **real**
in-place name/desc budgets measured with `donor_scan`'s method (current string
length — what the shared writer enforces, NOT the gap to the next index entry).
Filtered to **Level 6+** (user's instruction) and name budget ≥ 14 B
("Accel Synchron"):

| cid | card | lvl | name E/floor | desc E/floor | CPU decks | binding hits |
|---|---|---|---|---|---|---|
| **0x11A3** | **Bracchio-raidus** | 6 | **15 / 15** | **44 / 37** | **0** | **1** |
| 0x126F | Meteor B. Dragon | 8 | 16 / 16 | 38 / 34 | 0 | 1 |
| 0x107F | B. Skull Dragon | 9 | 15 / 15 | 39 / 30 | 0 | 1 + 22 ambiguous |
| 0x13C6 | Humanoid Worm Drake | 7 | 19 / 19 | 29 / 29 | 0 | 1 + 1 |
| 0x1002 | Rabid Horseman | 6 | 14 / 14 | 31 / 29 | 0 | 3 + 214 |

**Chosen: Bracchio-raidus 0x11A3** — Lv6 WATER Dinosaur 2200/2000, pack 52.
- card_prop / card_genre index **489**; prop raw `0x001218C5643711A3`,
  genre raw `0x0000000020200000`.
- `donor_scan` finds **exactly one binding occurrence in all of ov3 + ARM9** — its
  own fusion recipe row — and **zero** ambiguous ARM9-data or code-region hits.
  The cleanest donor in the whole survey.
- **Not** a material of any other fusion (tables A and B both swept: 0 hits).
- Name floor **15 ≥ 14**, so "Accel Synchron" writes in **all eight languages**.
- In **zero** CPU decks (`deck.json` swept over main/extra/side).

Fusion recipe **row 38 @ `0x02270CC4`** = `{result 0x11A3, m1 0x0FC6, m2 0x0FF7,
m3 0x0000}`; m1 slot at **0x02270CC6**, m2 slot at **0x02270CC8**.

### C9. Target values (round-tripped through `GC.encode_entry` this session)

| field | value |
|---|---|
| `card_prop` raw | `0x00CE14A7690C91A3` → cid 4515 (0x11A3), Lv5, DARK, Machine, 500/2100, Synchro Tuner Effect Monster |
| `card_genre` raw | `0x0000001800200000` (bits 21, 35, 36) |
| recipe m1 @0x02270CC6, m2 @0x02270CC8 | both `0x3FFF` |
| Synchron table | `[0x11A3, 0x181C, 0x1E07, …]`, 15 entries, strictly sorted |

`0x3FFF` is chosen because `fusion.code_classes` says a material slot ≥ 0x33 is
read as a literal **cid**, not a category code, and the max real cid is 0x24E8 —
so it can never match a card, and it never enters that proof's `0 < v < 0x33`
category census.

### C10. Precedent banked for the LATER clauses (not built this session)
**Formula Synchron 0x239E** — the game's only other Synchro Tuner — already ships
a native NDS implementation of Accel Synchron's clause 3: *"Once per Chain, during
your opponent's Main Phase, you can (Quick Effect): Immediately after this effect
resolves, Synchro Summon using this card you control."* Its records (from
`donor_scan 0x239E`): **cls3[730]** `ov3:0x0227E1E4`, **cls1[1253]**
`ov3:0x0228D64C`, **criteria row[1266]** `ov3:0x02274F1C`, plus a row in the
proper-SS trigger list `0x0228F6C0[27]` (`ov3:0x0228F6F6`).

**The KB already has this fully decoded** — do not re-derive it:
`synchro.opponent_turn_summon_is_formulas_cls3` (VERIFIED) states the clause is
*three data rows, not code*: cls3 record `{+04 resolver 0x02249EC1, +0C condition
0x021F1491, rest 0}`, criteria row 1266 `{aux 0xFFFF, handler 0x0223D21D, word
0x00000802}`, and membership of the ARM9 spell-speed-2 list `0x0209C118`. The
condition `0x021F1490` IS the printed timing (turn-log once-per-turn scan → must be
the OPPONENT's turn → Main Phase 1 or 2), and both the resolver and the criteria
handler are **cid-agnostic**. Its cls1 record + `0x0228F6C0` membership are a
*different* clause (Formula's draw) and **must not be copied**.
⚠️ It also warns: Formula's cls1/trigger-list rows belong to the draw, so clause 3
needs neither. Already used by `card.steam_synchron`.

### C11. Built and statically verified (2026-09-03) — NOT in-game confirmed

`.venv-1/Scripts/python.exe _build_accel_synchron.py --text`

- **Stage 1**, single-card ROM `data/over_the_nexus/working/rom_accel.nds`,
  129,515,656 B, **sha256 `7225bc51e3b5c751f3976f263ec63355b3083e385b57eaeb94922e1bada9cb8e`**
  — `patch_accel_synchron.verify()` **PASS**, all 41 checks.
- **Stage 2**, composition against `patch_unknown_synchron` (the only shipped card
  that touches a shared resource with this patch, the Synchron set-code table),
  `rom_accel_compose.nds`, **sha256 `6e7d18729eb51d6d0065748225d2cdf12f90dd6e08c3010a416ea9a6bd1b533e`**
  — both modules' `verify()` PASS, and the combined table is
  `0x11A3, 0x181C, 0x1E07, 0x1E14, 0x1E4E, 0x1EA1, 0x1EBE, 0x1F46, 0x20F7, 0x21A7,
  0x224C, 0x229E, 0x239E, 0x23EE, 0x2414` — a sorted 15-entry set holding **both**
  donors with **both** drops gone.
- `check_allocations` **PASS** (174 ov5 slots, 153 phantom claims, ledger in sync);
  the new claim `{pool: synchron_setcode_table, cid: 0x0D6B, owner: accel_synchron}`
  is registered in `otn_enhanced/docs/engine/allocations.yaml:884`.
- **No ov5 cave slot claimed, no injected Thumb anywhere** — `CAVE_FREE` is still
  `0x0239E700`, untouched.

⚠️ **NOT wired into `apply_all_patches` or `_verify_all_patches.SHIPPED`** — the
card has never been tested in a duel, so per CLAUDE.md it stays out of the chain
until the user approves shipping.

---

## Ruled Out

- **"The Level-change mechanic has no precedent in this engine."** MY OWN CLAIM,
  written into an earlier draft of this file and **killed the same session, before
  any code was written.** I had checked for a KB *fact*, found none, and concluded
  the mechanic did not exist — without searching the card pool. A scan of all 4305
  OTN cards against `scratch/ygoprodeck_cache.json` finds **45 cards whose printed
  text changes a Level**, several structurally identical to clause 2 (see
  `## Next Experiment`). **THE RULE: absence of a KB fact is not absence of a
  mechanic.** Before declaring anything unprecedented, grep the printed-text cache,
  intersect with `scratch/cid_to_name.json` to keep only cards that exist in this
  ROM, then `donor_scan` the survivors. Two minutes.
- **Testing the "Synchron" tag with Tuning.** Cannot work at all: Tuning adds a
  "Synchron" from your **Deck**, and this is an **Extra Deck** monster. Killed by
  the user in-game: *"It is in the extradeck, so it cannot be searched by tuning"*.
  The working oracle is the deck-editor archetype filter (C7). Do not retry.
- **The 3DS build as a source for this card.** Killed by measurement this session:
  Accel Synchron is **not in the 3DS build** (`CARD_Name_E.bin` has no "Accel
  Synchron"; the only "Formula Synchron" is idx 4260, prop cid 0x239E). CLAUDE.md
  ranks the 3DS second in Reference Sources, but for THIS card it has nothing.
  Do not spend a lookup on it.

- **"A `card_type` flip alone converts a Fusion to a Synchro."** Killed by C2: the
  parallel `card_genre.bin` record carries an independent Fusion tag (bit 29) that
  a `card_prop` edit does not touch, plus a Tuner tag (bit 35) the card needs.
- **"A new Synchro cid must be inserted into some Synchro table."** Killed by C5:
  all three per-cid tables are opt-in exception lists and the generic arms accept.
  Inserting into LIST_A would actively *break* the printed "1+ non-Tuner" form.
- **"Fusion members are unusable as a Synchro donor"**
  (`notes/junk-speeder-findings.md:143`). That was a statement about which members
  of the **on-Synchro-Summon trigger list `0x0228F6C0`** could be repurposed — an
  assumption about the conversion, not a measurement of it. C3/C4/C5 measure it.
  Marked here so the next session does not inherit it as a blocker.
- **Man-eating Black Shark 0x11DB / Amphibious Bugroth 0x1225** as donors — both
  clean, but the user asked for Level 6+, and 0x11DB's name floor is 12 (< 14) so
  Japanese and Korean would keep the donor name.

---

## Open Questions

- **Are the `card_prop` reserved bits [54:58] meaningful?** Histogram by card_type
  shows values {0,2,3,4} across **every** type including both Fusions and Synchros,
  so they are **not** category-coupled — unlike the Spell/Trap case. The
  reference-record copy sidesteps the question, so this stays open but harmless.
- **No duel-time consumer exercises the "Synchron" tag for this card.** Confirmed
  at the `has_set_code` level only (C7). If a later clause or card is meant to see
  Accel Synchron as a Synchron *during a duel*, that path is still unproven.

## Closed this session

- ~~Deck-editor / card-list UI was never swept (may live in another overlay).~~
  **Closed by oracle 1**: the card renders correctly with the Synchro frame and
  sits in the Extra Deck, so whatever the menus read, the three-file conversion
  satisfies them.
- ~~`card_category` 3 → 0xA changes the bucket at 14 call sites that switch on the
  raw category (icon / sort / menu ordering) — unverified visually.~~
  **Closed by oracles 1 and 7**: the frame, the Extra-Deck placement and the
  archetype-filter listing all render correctly.

---

## Composition — READ BEFORE SHIPPING

⚠️ **A hazard no ledger can catch.** Three modules now edit the "Synchron" list
`0x0209C968`, and each claims a **different** slot — `patch_unknown_synchron`
0x2501, `patch_steam_synchron` 0x229E, this patch 0x0D6B — so
`check_allocations` passes cleanly. **But `patch_steam_synchron.SYNCHRON_CORE` is
a "nothing else was lost" survival tuple that NAMES 0x0D6B**, and its `main()`
aborts on a missing core member.

✅ **RESOLVED 2026-09-03, later the same day.** Steam Synchron was in-game
confirmed (all eight oracles) and **shipped into `apply_all_patches`**, and
`0x0D6B` **was removed from `patch_steam_synchron.SYNCHRON_CORE` in that same
change**, specifically so this card can still take that slot. The two now compose
in either order. Steam's survival check is now purely dynamic — "nothing but *my
own* stale `0x229E` left the list during *my* edit" — plus a 12-cid core that no
longer names any slot another patch may spend.

**Still re-check the tuple before shipping accel**, and take the general lesson
with you: *keep a survival assertion to the cids YOU depend on, never to the whole
table.* A tuple naming a neighbour's spendable slot silently constrains every
future patch that shares the table, and no ledger can see it — the same class as
`otn-register-phantom-same-edit`. Recorded in `check_allocations.py` at the claim,
in both patch docstrings, and in `card.accel_synchron_phase1`.

**Also upgraded by that session:** clause 3's chassis
(`synchro.opponent_turn_summon_is_formulas_cls3`) is no longer merely *decoded* —
Steam Synchron shipped that exact clause and the user confirmed it in-game on the
first test, **including in a puzzle**. Two differences in Accel's favour: Accel
**prints** the once-per-turn, so Formula's inherited turn-log gate is *correct*
here rather than the deviation it is for Steam Synchron; and Accel is an Extra
Deck Synchro, which cls3 does reach (Formula is itself an Extra Deck Synchro
running off exactly this record) — though that last point is **inferred from the
retail card working, not measured by us**, and is what an Accel clause-3 in-game
test should watch. See `card.accel_synchron_phase1` for the full note.

Otherwise composition is clean: stage 2 of the build applies
`patch_unknown_synchron` on top and both modules' `verify()` pass, with the
combined table a sorted 15-entry set holding both donors.

---

## Next Experiment

Phase 1 (clause 0) is done and in-game confirmed. **The user chose CLAUSES 1 + 2
as the next session's target** (2026-09-03) and chose **NOT** to ship into
`apply_all_patches` yet. Full continuation prompt:
**`PROMPT_accel_synchron_clause1.md`**.

### ⚠️ CORRECTION to what this file said earlier in the session

An earlier draft of this section said *"the Level-change half has no known
precedent and needs its own reverse-engineering."* **That was wrong**, and it was
written from the absence of a KB *fact* rather than from a search of the card
pool. A scan of all 4305 OTN cards against `scratch/ygoprodeck_cache.json` finds
**45 cards whose printed text changes a Level**, several of them structurally
identical to this clause. Corrected 2026-09-03, same session, before any code was
written. **Do not re-derive the "no precedent" conclusion.**

### Clause 1 (send a "Synchron" from Deck to GY) — a SOLVED chassis

This needs **zero new machinery**. `patch_dragon_shrine` is the worked example
already shipped in this repo: *"Send 1 Dragon monster from your Deck to the GY"*,
whose own docstring says *"Clause 1 needs ZERO new machinery, because the
engine's deck-send pipeline is [complete]"*.

| KB fact | address | what it gives you |
|---|---|---|
| `dispatch.deck_send_phase_machine` | `0x02208DD4` | the SHARED deck-send resolver, a 9-phase state machine |
| `dispatch.deck_send_count_switch` | `0x0220906C` | per-cid send COUNT (register-based switch) |
| `dispatch.criteria_hand_vs_deck_handlers` | `0x0223CAD9` | selects from the **DECK** (`0x0223CB65` is the HAND — do not swap them) |
| `archetype.setcode_4c_is_monster_only` | — | the three existing aux-`0x4C` criteria rows to copy |

The filter row wants aux **`0x4C`** with low half `0x0002` (MONSTER). Synchron
Explorer 0x229E's word `0x00010002` is the closer template than Tuning's
`0x00008002`, because bit 15 = Tuner and the printed text says any "Synchron"
**monster**, not only Tuners.

### Clause 2 (raise OR lower this card's Level by the sent monster's Level)

**The hook already exists.** `dispatch.post_send_followup_phase` (`0x02208F42`):
*"PHASE 0x7C OF THE DECK-SEND RESOLVER IS A GENERIC POST-SEND FOLLOW-UP HOOK --
the place to hang"* work that must happen after the send. That is exactly where
the Level change belongs, and it is why clauses 1 and 2 are **one** effect and
should be built together rather than split across sessions.

**Native precedents for the Level change itself** (all in this ROM, cids verified
against `cid_to_name.json` this session; records from `donor_scan`):

| cid | card | printed text | records |
|---|---|---|---|
| **0x225B** | **Spore** | *"...Special Summon this card from your Graveyard and **increase its Level by the Level of that banished monster**"* | **cls2[561]** `ov3:0x0227909C`, **criteria row[1148]** `ov3:0x02274994` |
| 0x1F34 | Give and Take | *"increase the Level of 1 monster you control **by the Level of** the Special Summoned monster"* | cls0[1013] `ov3:0x02284544`, criteria row[795] `ov3:0x02273908` |
| 0x1EC1 | Copy Plant | *"this card's Level **becomes** that monster's current Level"* | cls3[438] `ov3:0x0227C684` |
| 0x201D | Level Retuner | *"Reduce the Level of 1 face-up monster you control **by up to 2**"* | cls0[1066] `ov3:0x02284A3C` |
| 0x1E33 / 0x1E32 | Noisy Gnat / Silent Strider | increase / reduce a Level by 1 | — |
| 0x1EA1 | Road Synchron | *"**reduce this card's Level** by 2"* — a self-Level-reduce, on a Synchron | — |

**Spore 0x225B is the primary template.** Its clause is the same shape as ours:
a variable Level increase, read from *another card's* Level, applied to *this*
card. Both directions (increase and reduce) and the "by the Level of another
card" variable all exist natively, so **neither half of clause 2 is new
machinery** — it is a transplant, pending the disassembly that confirms it.

### The three things to prove BEFORE writing any code

1. **PROVEN** that phase `0x7C` is reached on the deck-send path
   (`dispatch.post_send_followup_phase`) — but **HYPOTHESIS** that it is reached
   for a *new* cid with no existing per-cid arm. Check
   `dispatch.deck_send_count_switch` `0x0220906C` for whether a cid absent from
   the switch still gets phase 0x7C.
2. **HYPOTHESIS**: Spore's Level-increase leaf is cid-agnostic and can be reached
   from our resolver. Disassemble `cls2[561]` `ov3:0x0227909C` and follow its
   slots before assuming anything.
3. **OPEN**: how the *player choice* between "increase" and "reduce" is expressed.
   No precedent found for a two-way branch on one effect — `0x201D` Level Retuner's
   *"by up to 2"* is the closest thing to a player-chosen Level amount and is
   worth disassembling for its picker.

### ⚠️ The 3DS shortcut is NOT available for this card

**MEASURED this session, so do not spend a lookup on it:** Accel Synchron is
**not in the 3DS build**. `CARD_Name_E.bin` contains only `Linear Accelerator
Cannon`, `Blaze Accelerator`, `Tri-Blaze Accelerator`, `Morphtronic
Accelerator`, `R-Genex Accelerator` and `Accellight` for "Accel"; the only
"Formula Synchron" record is idx 4260, prop cid `0x239E`. CLAUDE.md's
*Reference Sources* rule puts the 3DS second, but for THIS card it has nothing —
go straight to the NDS precedents above.

### Regression guard

The chassis is confirmed working. Re-run the eight oracles in
`_build_accel_synchron.py`'s docstring after any change — especially **oracle 4**
(1 Tuner + two non-Tuners) and **oracle 6** (usable as a Tuner), because a clause
that changes Level is exactly what could silently break them: `can_synchro_summon`
`0x02249540` reads the card's Level via `0x0202ABD8` to size its material search
(`dispatch.extra_deck_enumerator`).

⚠️ This card currently has **no cls0-cls3 record, no criteria row, no
effect-registry row and no ov5 slot** — the first clause to land claims all of
them. Take `CAVE_FREE` **live** from `ov5_cave.py`; it was `0x0239E700` at the
end of this session. Never hardcode it.


---

# SESSION 2026-09-03b — CLAUSES 1 + 2 (recon)

Status: **RECONNAISSANCE ONLY. No code written, nothing built.**

## Confirmed (this session)

### S2-C1. KB health at session start
`verify_knowledge` -> **TOTAL 422 facts: 385 PASS 0 FAIL 37 UNVERIFIED**,
oracles arm9=yes ov3=yes ov5=yes savestate=rom_all_patches.ml2. Matches the
handoff's expected figure exactly. No rot.

### S2-C2. ⚠️ THE PHASE-0x7C GATE IS ALREADY OWNED BY A SHIPPED PATCH
The handoff proposed hanging clause 2 on `dispatch.post_send_followup_phase`
(`0x02208F42`). **That site is not free.** `patch_dragon_shrine` PART E already
overwrites its first 8 bytes with `ldr r0,[pc,#4] ; bx r0 ; nop ; .word
CAVE_DS_FOLLOW|1` and re-dispatches from an ov5 stub:

    if cid in (0x0DBF, 0x1C15, 0x1DC2): goto 0x02208F56   ; native body
    if cid != 0x14C1:                   goto 0x02209046   ; nothing to do
    ... Dragon Shrine clause 2 ...

Evidence, read this session from
`otn_enhanced/cards/dragon_shrine.py`:
- `GATE_ADDR = 0x02208F42`, `GATE_STOCK` asserted before the overwrite
  (`apply_gate`, idempotent), `CAVE_DS_FOLLOW` stub `_build_follow`.
- **Dragon Shrine IS SHIPPED**: `apply_all_patches.py:91` imports it,
  `apply_all_patches.py:1638` runs `_apply_dragon_shrine`, and
  `_verify_all_patches.py:52` lists `patch_dragon_shrine` in SHIPPED.

**Consequence.** Accel Synchron clause 2 cannot rewrite `0x02208F42`
independently — in the chain, Dragon Shrine's `GATE_STOCK` assert would abort the
build (or, if ordered the other way, Accel's assert would). The gate must become a
**shared module with a cid-dispatch arm per owner**, in the established shape of
`criteria_row_hook.py` / `timing_class_hook.py`
(`otn-shared-hook-lift-prove-by-execution`), and the lift must be proved by
EXECUTION — i.e. assert no shipped cid's behaviour changes.

⚠️ A single-card `rom_accel.nds` built from stock `rom.nds` **cannot see this
class of bug** — only the chain can. Same lesson as
`otn-register-phantom-same-edit`.

### S2-C3. Clause 1's per-cid default is already PROVEN by Dragon Shrine
The handoff listed as a HYPOTHESIS: "does a cid with no arm in the deck-send count
switch `0x0220906C` still reach phase 0x7C?" `patch_dragon_shrine`'s docstring
answers both halves from disassembly already banked in the KB:
- resolver `0x02208DD4` presets count = 1 at `0x02208E1A`
  (`movs r0,#1 ; str r0,[r5,#0x74]`, mode 0 at `[r5+0x78]`) and only THEN runs the
  per-cid tree; the tree is REGISTER-based against PC-relative literals (not the
  stack-based-switch footgun), so a static read is sound. Literals
  `0x0220906C..0x0220907C` = `0x1BFE`->4, `0x1D3E`->2, `0x228E`->desc[+0x18],
  `0x22C3`->2, `0x1FCA`->mode 2. **Every other cid falls through with count = 1.**
- Phase 0x7C is entered generically; `0x02208F42` is the in-phase cid FILTER, whose
  stock default arm is `0x02209046` = "nothing to do". So a new cid reaches phase
  0x7C and is then filtered out — which is exactly why an arm has to be added.

## Open Questions (this session)

- **Which cls table does a MONSTER ignition effect live in?** Dragon Shrine's donor
  is a Normal SPELL and uses **cls0** with condition `0x021F0B19` (Foolish Burial's
  Spell activation condition). Accel Synchron is a monster; cls0 + a Spell
  activation condition is almost certainly wrong. Needs the `dispatch.cls_tables`
  geometry and a MONSTER precedent that sends from Deck to GY on an ignition.
- **Donor 0x11A3 is records-free**, so clause 1 needs a count-neutral INSERT into
  both the cls table and the criteria registry (phantom cid drop), not an in-place
  rewrite. Dragon Shrine paid neither cost.

### S2-C4. ⚠️⚠️ THE HANDOFF'S CLAUSE-1 ROW WAS WRONG — handler `0x0223CAD9` IGNORES aux

The handoff (and `dispatch.criteria_hand_vs_deck_handlers`) said to build clause 1's
criteria row on **`0x0223CAD9`** = "select from the DECK", with aux `0x004C` supplying
the "Synchron" filter. **That row would have silently dropped the archetype filter.**

Disassembled this session from the committed ov3 oracle:

```
0x0223cad8  push  {r1,r2,r3,lr}
0x0223cada  adds  r2, r0, #0      ; r2 = the registry row
0x0223cadc  ldr   r0, [r2, #8]    ; the criteria WORD
0x0223cade  movs  r3, #0          ; <-- r3 = 0   : NO value list
0x0223cae0  str   r0, [sp]
0x0223cae2  movs  r0, #2
0x0223cae4  str   r0, [sp, #4]    ; type 2
0x0223cae6  adds  r0, r1, #0      ; side
0x0223cae8  ldrh  r1, [r2]        ; row[+0] = the CID
0x0223caea  movs  r2, #0          ; <-- r2 = 0   : NO extra predicate
0x0223caec  bl    0x0223bc3c
```

**It never touches `row[+2]`.** The aux is not read, so `aux = 0x004C` on a
`0x0223CAD9` row is dead data.

The aux-aware sibling immediately below it does read it, via exactly the
(r2 = extra predicate, r3 = &value list) mechanism of
`dispatch.criteria_word_race_attribute`:

```
0x0223caf4  push  {r1,r2,r3,lr}
0x0223caf6  adds  r3, r0, #0
0x0223caf8  movs  r0, #2
0x0223cafa  ldrsh r2, [r3, r0]    ; <-- r2 = (s16) row[+2] = THE AUX
0x0223cafc  str   r2, [sp, #8]    ; the aux becomes the value list
0x0223cafe  ldr   r2, [r3, #8]    ; word
0x0223cb00  str   r2, [sp]
0x0223cb02  str   r0, [sp, #4]    ; type 2  (IDENTICAL to 0x0223CAD9)
0x0223cb04  adds  r0, r1, #0      ; side
0x0223cb06  ldrh  r1, [r3]        ; cid
0x0223cb08  ldr   r2, [pc, #8]    ; r2 = 0x0223C825  = the SET-CODE predicate
0x0223cb0a  add   r3, sp, #8      ; r3 = &aux
0x0223cb0c  bl    0x0223bc3c      ; same callee, same type
```

Literal at `0x0223CB14` = **`0x0223C825`** (the set-code candidate predicate).
The two handlers are otherwise instruction-for-instruction identical — same
callee `0x0223BC3C`, same type 2, same word, same cid. **So the difference between
`0x0223CAD9` and `0x0223CAF5` is EXACTLY the set-code filter, nothing else** —
in particular NOT the destination (GY vs hand), which is the resolver's business.

⚠️ This is precisely the handoff's own predicted failure row *"Picker appears but
lists non-Synchrons"*. It would have cost a duel.

### S2-C5. ⭐ THE CLAUSE-1 ROW, taken from SEVEN native cards that already do it

Cross-referenced this session: cids owning a criteria row on `0x0223CAF5` with a
non-`0xFFFF` aux **and** a cls record whose resolver is `0x02208DD5` (the shared
deck-send) — i.e. cards that natively print *"send 1 <archetype> monster from your
Deck to the GY"*:

| row | cid | card | aux | word |
|---|---|---|---|---|
| 698 | 0x1DC2 | Hero Mask | 0x0008 | 0x00000002 |
| 989 | 0x20DB | Worm Xex | 0x0032 ("Worm") | 0xA0000002 (+ Reptile) |
| **1120** | **0x2209** | **The Fabled Peggulsus** | **0x0041 ("Fabled")** | **0x00000002** |
| 1190 | 0x22C3 | Laval Miller | 0x0055 ("Laval") | 0x00000002 |
| 1248 | 0x2359 | Dragon Ravine | 0x004A | 0x00900002 |
| **1334** | **0x2469** | **Scrap Shark** | **0x0057 ("Scrap")** | **0x00000002** |
| 1356 | 0x249D | Tender of the Laval Volcano | 0x0055 | 0x00000002 |

Peggulsus prints *"send 1 'Fabled' monster from your Deck to the GY"* and Scrap
Shark *"send 1 'Scrap' monster from your Deck to the Graveyard"* — our sentence
with a different archetype, and both carry the bare word `0x00000002`.

⇒ **CLAUSE 1'S CRITERIA ROW = `{cid 0x11A3, aux 0x004C, 0x0223CAF5, 0x00000002}`**
— Peggulsus's / Scrap Shark's row with only the aux swapped to the "Synchron" set
code. Konami's own value, not a reconstruction. No bit 15 (the printed text says
any "Synchron" **monster**, not only Tuners — `dispatch.criteria_word_bit15_is_tuner`);
level byte 0 because Deck-reading rows carry a clear low-2-bit zone flag
(`dispatch.criteria_word_level_field`), which every Deck row above confirms.

### S2-C6. ⭐ THE CLAUSE-1 cls RECORD: Darklord Asmodeus 0x205F, verbatim

`Darklord Asmodeus 0x205F` prints *"Once per turn: You can send 1 Fairy-Type
monster from your Deck to the Graveyard"* — clause 1's exact shape on a MONSTER
(the handoff's template, Dragon Shrine, is a Normal SPELL and uses cls0 with a
Spell activation condition, which is the wrong class here).

Records dumped this session from the ov3 oracle:

| cid | record | +04 | +08 | +0C | +10 | +14 |
|---|---|---|---|---|---|---|
| **0x205F Darklord Asmodeus** | **cls3[543]** @0x0227D05C | **0x02208DD5** | 0 | **0x021F0B71** | **0x021E5061** | 0 |
| 0x22F9 Scrap Hunter | cls3[701] @0x0227DF2C | 0x0222F95D | 0x021DF0B9 | **0x021F0B71** | **0x021E5061** | 0x02234DA5 |
| 0x1D89 Dark Grepher | cls3[385] @0x0227C18C | 0x02208DD5 | 0 | 0x021F0BDD | 0x021E4EED | 0 |
| 0x1474 Foolish Burial | cls0[305] @0x022802E4 | 0x02208DD5 | 0 | 0x021F0B19 | 0 | 0 |

- **A monster ignition effect lives in cls3** (`dispatch.cls_table_selector`: sel 3
  -> 0x02279D74 count 0x308). Asmodeus, Scrap Hunter and Dark Grepher are all cls3.
- The pair **`+0C 0x021F0B71` / `+10 0x021E5061`** appears on both Asmodeus and Scrap
  Hunter, whose only shared printed property is *"Once per turn:"* + an ignition —
  so that pair is the generic **monster once-per-turn ignition** condition/cost.
- `0x021E5060` is the "once while face-up" cost node that `patch_dragon_shrine`'s
  docstring records as ABANDONED for Dragon Shrine because *"it hangs off a MONSTER
  ZONE RECORD, which a Normal Spell does not have"*. **Accel Synchron IS a monster,
  so the node Dragon Shrine could not use is exactly the right one here** — and it
  sits in slot 4 (the COST slot), i.e. stamped at ACTIVATION, which is what
  `dispatch.once_per_turn_must_stamp_at_activation` requires. Clause 1's
  once-per-turn therefore costs zero new machinery.

⇒ **CLAUSE 1'S cls3 RECORD = `{0x11A3, 0x02208DD5, 0, 0x021F0B71, 0x021E5061, 0}`**
— Darklord Asmodeus's record verbatim with the cid swapped.

**Cost:** donor 0x11A3 is records-free, so BOTH rows are count-neutral INSERTS
(a phantom cid dropped from cls3 and one from the criteria registry), not the
in-place rewrites Dragon Shrine paid for. Phantoms not yet chosen.

## Ruled Out (this session)

- **`0x0223CAD9` + aux `0x004C` as clause 1's criteria row** (the handoff's design).
  Killed by disassembly, S2-C4: the handler never reads `row[+2]`. Use `0x0223CAF5`.
- **`patch_dragon_shrine`'s cls0 + `0x021F0B19` as clause 1's chassis.** That is a
  Normal SPELL's activation condition in the Spell/Trap table. A monster ignition is
  cls3 with `0x021F0B71` (S2-C6).

### S2-C7. The clause-1 callbacks are cid-agnostic (`grep-the-template-cards-text-too` check)

Disassembled this session; neither compares a cid, so neither can smuggle
Asmodeus's or Scrap Hunter's own printed clauses into our card:

**slot3 `0x021F0B70`** — the once-per-turn ignition condition:
```
r5=desc, r4=arg1
ldrb r0,[r5,#2]        ; side
ldrb r1,[r5,#3]        ; ZONE
ldr  r2,=0x00000FB6    ; the once-per-turn node KEY
bl   0x021A1430        ; the kind<6 attached-node WALKER (otn-attached-effect-rider)
if r0 != 0 -> return 0          ; already used this turn -> cannot activate
else       -> tail 0x021F0B18   ; == FOOLISH BURIAL's own activation condition
```
So it is exactly *"not yet used this turn, AND a legal candidate exists"*. Keyed on
**(side, zone)**, i.e. per monster-zone instance — so it cannot clash with Asmodeus
or Scrap Hunter sharing key 0x0FB6, since they occupy different zones.

**slot4 `0x021E5060`** — the stamp:
```
bl 0x021D2C1C ; if 0 -> just return 1
[sp]=0 ; r0=desc[+2] side ; r1=desc[+3] zone ; r2=0x0FB6 ; r3=2
bl 0x021C479C        ; the attached-node WRITER, kind 2
return 1
```
Query and stamp use the same key and the same (side, zone). **The stamp is in
slot 4 = the COST slot = at ACTIVATION**, satisfying
`dispatch.once_per_turn_must_stamp_at_activation` with no shim.

### S2-C8. Clause 2's mechanism located: a Level change is an ATTACHED RIDER

`0x02208499` is a SHARED Level-change resolver, owned by **Copy Plant 0x1EC1**
(cls3[438], *"this card's Level becomes that monster's current Level"*) and
**Road Synchron 0x1EA1** (cls1[894], `{+04 0x02208499, rest 0}`). Its per-cid tree
is register-based against PC-relative literals with base±imm arms (ungreppable,
`thumb.stack_based_switch` family) and its default arm is `0x0220873E`.
`0x02208849` is a second, smaller Level resolver (Noisy Gnat 0x1E33 / Silent
Strider 0x1E32, "+/- 1 Level").

BL census over both resolvers gives the primitive family:

| addr | role |
|---|---|
| `0x021B8050` | **READ Level**: `(side, zone)` -> `0x021B3CE8` recompute, returns `[sp+0x20]` |
| `0x021B8028` | read a sibling stat, `0x021B3CE8` -> `[sp+0x1C]` |
| `0x021B8014` | read a stat via `0x021B44C0` (`otn-continuous-stat-engine`) -> `[sp+0x14]` |
| **`0x021C479C`** | **WRITE**: the attached-node writer (`otn-attached-effect-rider`) |

The WRITE shape, read at `0x02208716`:
```
str  r7, [sp]        ; arg4 = the VALUE
ldrb r0, [r5, #2]    ; side
ldrb r1, [r5, #3]    ; zone
adds r2, #0xFB       ; r2 = the node KEY  (base+-imm: UNGREPPABLE)
movs r3, #2          ; kind = 2
bl   0x021C479C
```
and at `0x022086C2` the same call builds `r3 = 2 | ((r7 & 0xF) << 4)` — the kind
BYTE's HIGH nibble being the per-turn countdown of `otn-attached-effect-rider`
(`0x2` = permanent, `0x12` = until the end of the next turn).

⇒ **A Level change is a kind-2 attached rider on (side, zone), not a card_prop or
stat-table write.** That is good news for the clause-0 regression risk: it goes
through the same recompute path `can_synchro_summon` reads.

## Open Questions (clause 2)

1. **The exact node KEY for a Level rider.** The value is formed by `adds r2,#0xFB`
   off a switch base, so it is UNGREPPABLE and must be read out of the specific
   leaf that belongs to Copy Plant or Road Synchron. Not yet done.
2. **The player's up/down choice.** Still no precedent found. Level Retuner 0x201D
   (cls0[1066] `{0x0222C259, 0x021DCD49, 0, 0, 0x02234D8D}`, *"by up to 2"*) is the
   nearest thing and has NOT been disassembled yet.
3. **⚠️ BLOCKER — phase 0x7C is owned by a SHIPPED patch** (S2-C2). Clause 2 cannot
   take `0x02208F42` for itself; the gate must be lifted into a shared cid-dispatch
   module and the lift proved by EXECUTION per
   `otn-shared-hook-lift-prove-by-execution`.

## Next Experiment

Pending the user's scope decision (clause 1 alone vs 1+2 together). If 1+2:
read the Copy Plant / Road Synchron leaves of `0x02208499` for the Level rider KEY,
then disassemble Level Retuner's `0x0222C259` for a two-way chooser.

### S2-C9. ⭐⭐ THE TWO-WAY CHOOSER, found via a USER TIP: Egotistical Ape 0x22EB

**The user named the card** (2026-09-03, mid-session): *"Egotistical Ape has an
effect that increases or decrease level based on the card used"*. It closes the
question this file had marked GENUINELY OPEN.

Printed text (`scratch/ygoprodeck_cache.json`, cid confirmed 0x22EB via
`cid_to_name.json` — Tuner Monster / EARTH / Beast / Lv5 / 1200 / 1200):

> This card cannot be Normal Summoned or Set. This card can only be Special
> Summoned by sending 1 Beast-Type monster from your hand to the Graveyard.
> **When this card is Special Summoned this way, you can activate 1 of these
> effects: * Increase the Level of this card by the Level of the Beast-Type
> monster. * Decrease the Level of this card by the Level of the Beast-Type
> monster.**

That is clause 2's sentence with a different source zone. Records:

```
cls1[1198] @0x0228D124  {+04 0x022082A5, +08 0, +0C 0, +10 0x021E88F5, +14 0}
```
(no criteria row; its cid literal sits at ov3:0x02208480, inside resolver
`0x022082A4`'s pool — which is how the resolver was identified.)

**`0x022082A5` is a SECOND shared stat/level resolver**, same shape as
`0x02208499`: a register-based per-cid compare tree over `ldrh r0,[r5]` with a
shared write tail (here `0x0220844E`). Egotistical Ape's arm is selected at
`0x02208310` (`ldr r1,=0x000022EB ; cmp r0,r1 ; beq 0x022083DC`) — an exact
literal, so this one IS greppable.

**ITS LEAF @0x022083DC IS THE TWO-WAY BRANCH:**
```
0x022083dc  ldrb r1, [r5, #2]      ; side
0x022083e0  ldr  r3, =0x0229ACD4   ; zone-record base
0x022083e2  ands r1, #1
0x022083e6  ldrb r1, [r5, #3]      ; zone
0x022083e8  ldr  r0, =0x00000B3C   ; per-player stride
0x022083ea  muls r4, r0, r4        ; side * 0xB3C
0x022083ec  movs r0, #0x14         ; zone-record stride
0x022083f0  muls r2, r0, r2        ; zone * 0x14
0x022083f4  ldr  r4, [r2, r0]      ; r4 = the AMOUNT
0x022083f6  ldrh r0, [r5, #0x18]   ; *** desc[+0x18] = THE PLAYER'S CHOICE ***
0x022083f8  cmp  r0, #2
0x022083fa  bne  0x0220844e        ; choice != 2 -> use r4 as-is  (INCREASE)
0x022083fc  rsbs r0, r4, #0        ; choice == 2 -> NEGATE        (DECREASE)
```

⇒ **"Activate 1 of these effects" is expressed as ONE resolver leaf that branches
on `desc[+0x18]`, negating the amount for option 2.** The sibling leaf at
`0x022083BA` (cid 0x1FDC) is the same load with NO negate — i.e. the plain
increase-only form, which controls for everything but the branch.

`desc[+0x18]` is a general effect-parameter field, not bespoke: the OTHER level
resolver reads it too — `0x02208684` (`ldrh r4,[r5,#0x18]`) and `0x02208732`
(`ldrh r0,[r5,#0x18] ; cmp r0,#1`).

### S2-C10. The rider write tail of `0x02208499`, fully decoded

Entry (`0x0220849E`): `ldrh r1,[r5]` (cid), `movs r7,#0` (duration), **`str r1,[sp,#8]`**,
`movs r4,#0` (value). Shared tail:
```
0x0220873e  ldr  r0, =0xFFFF
0x02208784  cmp  r4, r0 ; ble ; adds r4, r0, #0     ; value = min(r4, 0xFFFF)
0x0220878a  movs r3, #0xF ; ands r3, r7             ; duration nibble
0x0220878c  lsls r0, r4, #0x10 ; lsrs r0, r0, #0x10
0x02208792  str  r0, [sp]                           ; arg5 = VALUE (u16)
0x02208796  ldr  r2, [sp, #8]                       ; arg3 = KEY
0x02208798  lsrs r4, r3, #0x14
0x0220879a  movs r3, #2 ; orrs r3, r4               ; arg4 = KIND = 2 | (dur << 4)
0x0220879e  lsls r2, r2, #0x10 ; lsrs r2, r2, #0x10 ; key &= 0xFFFF
0x022087a2  ldrb r0, [r5, #2] ; ldrb r1, [r5, #3]   ; side, zone
0x022087aa  bl   0x021C479C
0x022087ae  movs r0, #0 ; add sp,#0x10 ; pop
```
⇒ `0x021C479C(side, zone, key, kind, value)`; **the KEY defaults to the effect
source's own cid** (`[sp+8]` set from `desc[+0]` at entry) and a leaf may override
it (`0x0220873A: ldr r0,=0x1295 ; str r0,[sp,#8]`). Kind low nibble 2, high nibble
= the per-turn countdown of `otn-attached-effect-rider`. Value is capped to u16.

Traced by hand through the compare tree: **Copy Plant 0x1EC1 -> leaf 0x02208602**
(via `r2 = 0x1F0E - 0x4D = 0x1EC1` at 0x02208532). **Road Synchron 0x1EA1 falls to
the shared tail with r4 = 0**, i.e. its cls1 record's level clause is NOT in this
resolver.

## Open Questions (updated)

1. ~~The player's up/down choice~~ — **CLOSED by S2-C9**: `desc[+0x18]`, `cmp #2`.
   Still open: **where `desc[+0x18]` is SET** (the prompt that offers the two
   options). Next: disassemble Egotistical Ape's slot4 `0x021E88F4`.
2. **What exactly `[0x0229ACD4 + side*0xB3C + zone*0x14]` holds** — it is read as
   the AMOUNT by both 0x022083BA and 0x022083DC. Needs confirming it is the
   remembered Level of the consumed card and not a zone-record card word.
3. **⚠️ BLOCKER unchanged** — phase 0x7C (`0x02208F42`) is owned by shipped
   `patch_dragon_shrine` (S2-C2); the gate needs a shared-hook lift.

### S2-C11. ⭐ THE "ACTIVATE 1 OF THESE EFFECTS" MACHINERY, END TO END

Egotistical Ape's slot4 `0x021E88F4` is a SHARED activation sub-machine driven by
the phase counter `[0x0229AAFC + 0x7C]` (exactly the slot4 protocol of
`dispatch.cls_slot_roles`). Ape's arm is selected at `0x021E8980`
(`ldr r0,=0x000022EB ; cmp r1,r0 ; beq 0x021E8ACC`) — an exact literal, greppable.

**Phase 0** (Ape arm `0x021E8ACC`) builds a legality BITMASK in r5
(`movs r5,#4` seed; bit 0 = option 1 legal, bit 1 = option 2 legal), then:
```
0x021e8b40  cmp  r5, #4          ; neither option legal?
0x021e8b42  bne  0x021e8b4a
0x021e8b44  movs r0,#0 ; mvns r0,r0 ; return -1     ; ABORT the activation
0x021e8b4a  ldrh r0,[r4]     ; cid
0x021e8b4c  movs r1,#0
0x021e8b50  bl   0x021E5748  ; -> r6 = LABEL for option 0
0x021e8b56  ldrh r0,[r4] ; movs r1,#1
0x021e8b5a  bl   0x021E5748  ; -> r0 = LABEL for option 1
0x021e8b5e  r1 = 0x6B<<2 = 0x1AC ; str r1,[sp]      ; the default/title label
0x021e8b64  r3 = option-1 label ; r2 = option-0 label ; r0 = desc
0x021e8b6a  subs r1,#0xA9 -> 0x0103                 ; prompt id
0x021e8b6e  str  r5,[sp,#8]                         ; the legality mask
0x021e8b70  bl   0x0219ABB4                         ; *** THE TWO-OPTION PROMPT ***
            [0x0229AAFC+0x7C] += 1 ; return 0
```
**Phase 1** (`0x021E8B80`):
```
r0 = [0x0229DD94 + 0x34]   ; the player's SELECTED option index
r0 = r0 + 1
strh r0, [r4, #0x18]       ; *** desc[+0x18] = selected_index + 1 ***
... bl 0x021C3BC8 (announce the chosen effect) ; [+0x7C] += 1 ; return 0
```
**Phase 2** (`0x021E8BAC`): `ldrh r1,[r4,#0x18] ; cmp r1,#3 ; beq <abort>` then
`bl 0x021CF834`; `[+0x7C] += 1`.

⇒ option 1 -> `desc[+0x18] = 1`, option 2 -> `desc[+0x18] = 2`, which is exactly
what the resolver leaf `0x022083F8` (`cmp r0,#2`) branches on. **The chooser and the
branch are now closed end to end.**

### S2-C12. ⭐ THE OPTION LABELS ARE A DATA TABLE — and Ape's two rows are OUR two rows

`0x021E5748(cid, option_index) -> label` is pure data:
```
0x021e574a  r7 = 0x0226F32C     ; TABLE BASE
0x021e5750  r2 = 0xBF (191)     ; COUNT immediate
0x021e5752  r3 = 4              ; record stride
0x021e5758  bl 0x02022E44       ; binary search by cid -> record ptr, 0 if absent
0x021e5760  default label = 0xBF + 0xED = 0x01AC
0x021e576c  r0 -= 4 ; walk BACK while record[-1].cid == cid   ; LEFTMOST-equal walk
0x021e5778  r1 = option_index * 4
0x021e577c  ldrsh r1,[r0,r1]    ; the cid of record[leftmost + index]
0x021e577e  cmp r5,r1 ; bne -> return 0x01AC     ; fewer rows than the index
0x021e5788  ldrsh r0,[r0, index*4 + 2]           ; THE LABEL
```
**Table `0x0226F32C`, 191 x 4-byte `{s16 cid, s16 label}` rows, strictly sorted by
cid** (verified over the whole table this session), 84 distinct cids, rows-per-cid
histogram `{2: 64, 3: 18, 4: 1, 5: 1}`. It ends at `0x0226F628`. Each card
contributes N CONSECUTIVE rows, one per menu option.

**Egotistical Ape's rows, dumped this session:**
```
[163] @0x0226F5B8  cid 0x22EB  label 0x016E     ; "Increase the Level ..."
[164] @0x0226F5BC  cid 0x22EB  label 0x016F     ; "Decrease the Level ..."
```
⇒ **clause 2 can reuse label ids `0x016E` / `0x016F` verbatim** — the strings
already exist and already say the right thing. No new text, no blob growth.
Insert point for cid `0x11A3` is index **7** (between 0x10F8 and 0x1231).
⚠️ The count is a hardcoded `movs r2,#0xBF`, so the insert must be COUNT-NEUTRAL
(drop two phantom rows elsewhere, memmove, keep 191 rows sorted) unless the
immediate is bumped and the bytes after 0x0226F628 are proved free. Phantom
candidates not yet vetted: rows at indices 78 (0x1916), 80 (0x19D3), 91 (0x1AF0),
165 (0x234F) resolve to no name in `cid_to_name.json` — MUST be checked against
card_prop before dropping any of them.

### S2-C13. The clause-2 architecture that follows from all of the above

Mirror Egotistical Ape, split across the two moments the card needs:

| piece | where | what |
|---|---|---|
| the two-option prompt | **slot 4** of our cls3 record | must ALSO keep the once-per-turn stamp `0x021E5060` that clause 1 needs -> a combined ov5 stub, not a slot swap |
| the choice | `desc[+0x18]` | written by the prompt's phase 1 |
| the amount | **phase 0x7C** of the deck-send resolver | the sent monster's Level is only known AFTER the send, so it is read at follow-up time (the GY-top read `patch_dragon_shrine` already does) |
| the write | `0x021C479C(side, zone, key=0x11A3, kind=2, value)` | negate the value when `desc[+0x18] == 2` |
| the labels | table `0x0226F32C` | two rows, labels 0x016E / 0x016F |

⚠️ **A NEW CID HAS NO ARM in `0x021E88F4`'s per-cid switch** — it would fall through
to `0x021E8B40` with r5 = 4, hit `cmp r5,#4`, and **return -1, aborting the
activation**. So the prompt cannot be reached by data alone; it needs either an arm
in that shared switch or a self-contained ov5 clone in slot 4. Same for the level
resolvers `0x02208499` / `0x022082A5`: an unlisted cid reaches only the shared tail
with value 0.

## Ruled Out (added)

- **"Clause 2 can hang on phase 0x7C by data alone."** No: the gate is owned by
  shipped Dragon Shrine (S2-C2) AND the chooser needs a slot-4 stub (S2-C13).

## Next Experiment

1. Confirm what `[0x0229ACD4 + side*0xB3C + zone*0x14]` holds (the AMOUNT source in
   both `0x022083BA` and `0x022083DC`) — is it the remembered Level of the consumed
   card, or a zone-record word? This decides whether clause 2 reads the amount there
   or from the GY top like Dragon Shrine.
2. Vet the four unnamed option-label rows (0x1916, 0x19D3, 0x1AF0, 0x234F) against
   `card_prop` for phantom status, to pick the two count-neutral drops.
3. Design the shared phase-0x7C lift (Dragon Shrine + Accel Synchron) and prove it
   by EXECUTION per `otn-shared-hook-lift-prove-by-execution`.

### S2-C14. `0x0202ABD8(cid)` IS the Level reader — so clause 2's amount needs no zone field

```
0x0202abd8  push {r3,lr}
0x0202abda  bl   0x0202A084      ; card_prop record lookup
0x0202abde  ldr  r0, [r0, #4]    ; word 1
0x0202abe0  lsls r0, r0, #0x12
0x0202abe2  lsrs r0, r0, #0x1c   ; bits [13:10], 4 bits = LEVEL
0x0202abe4  pop  {r3,pc}
```
Confirmed against its two neighbours (`0x0202ABE8` = a 3-bit field, `0x0202ABF8` =
the known `card_type >> 1`, bits [5:0]) — same lookup, different bitfield. **ARM9,
so always resident, puzzle included.**

⇒ clause 2's amount = `0x0202ABD8(gy_top_word & 0x3FFF)`, read at phase 0x7C from
the GY top exactly as `patch_dragon_shrine`'s `_build_follow` already reads it.
**We do NOT need `[0x0229ACD4 + side*0xB3C + zone*0x14]`** — that field is Egotistical
Ape's own summon-procedure scratch (its phase-0 arm requires it nonzero at
`0x021E8B14` and uses it at `0x021E8B38` to forbid "decrease" when
`current_level <= amount`). Open question 2 is therefore CLOSED as not-needed,
though the legality idea is worth copying: **"decrease" should be refused when it
would take the Level to 0 or below.**

### S2-C15. The option-label count-neutral drop: phantom 0x1916

`donor_scan` this session: **0x1916, 0x19D3, 0x1AF0 and 0x234F all report
`<no card_prop row>`** — all four are phantom cids, so their option-label rows are
dead data (no menu can ever ask for a non-card's labels).

Ledger check (`check_allocations.py` / `otn_enhanced/docs/engine/allocations.yaml`, quoted):
- `0x234F` — claimed twice already: `{pool: membership_list_b, owner: gates_of_dark_world}`
  and `{pool: populate_table, owner: sea_lancer}`
- `0x1AF0` — `{pool: cls3_table, owner: gates_of_dark_world}`
- `0x19D3` — ov3 dead-code claim (`check_allocations.py:840`, `allocations.yaml:1082`)
- **`0x1916` — UNCLAIMED in every pool.**

`0x1916` owns **exactly two** consecutive rows, indices 78-79 @0x0226F450:
`{0x1916, 0x01C5}` and `{0x1916, 0x01CC}` — exactly the two clause 2 needs.

⇒ **Drop `0x1916`'s two rows; insert `{0x11A3, 0x016E}` / `{0x11A3, 0x016F}` at
index 7** (between 0x10F8 and 0x1231). Count stays 191 (the hardcoded `movs r2,#0xBF`
is untouched), the table stays strictly sorted, total size unchanged. Register the
claim as `{pool: option_label_table, cid: 0x1916, owner: accel_synchron}` in the SAME
edit (`otn-register-phantom-same-edit`). Claiming a phantom already claimed in a
DIFFERENT pool is explicitly allowed by the ledger's own precedent
(`check_allocations.py:129`), but 0x1916 avoids the question entirely.

### S2-C16. ⭐ cls3 DOES reach Extra-Deck monsters (the fear from `otn-leave-trigger-cls2` does NOT apply)

`otn-leave-trigger-cls2` warns: *"cls2 dispatch NEVER reaches an EXTRA-DECK
(Synchro) donor -- proven by A/B vs a Tengu control across 3 row shapes"*. That
would be fatal to clause 1 if it generalised. **It does not.** Census this session
over all four cls tables, cids classified by their ygoprodeck `type`:

| table | Synchro records | Fusion records |
|---|---|---|
| **cls3** | **79** | **43** |
| cls2 | 24 | 11 |
| cls1 | 75 | 41 |
| cls0 | 0 | 0 |

cls3 Synchro owners include Stardust Dragon 0x1E36, Black Rose Dragon 0x1EDA,
Brionac 0x1D7C, Dark End Dragon 0x1CCB and **Armory Arm 0x1F33 — a card this repo
has already shipped a patch against**. So an on-field ignition effect on an
Extra-Deck monster is completely ordinary; the cls2 finding was specific to the
LEAVE-FIELD trigger enumeration, not to cls dispatch in general.

⇒ **Clause 1's cls3 record is architecturally sound for this Extra-Deck donor.**

### Phantom survey for the clause-1 count-neutral inserts (candidates, not yet fixed)

Both arrays must stay sorted; donor cid is 0x11A3.
- **cls3** (base 0x02279D74, count 0x308): 84 phantom rows exist. Many sit BELOW
  0x11A3 (cls3[5..47] are 0x0Exx / 0x1138), so a drop-below + shift-down insert is
  available. Candidates with no mention anywhere in `check_allocations.py`:
  cls3[6] 0x0E13, cls3[8] 0x0E21, cls3[12] 0x0E36, cls3[59] 0x1337.
- **criteria registry** (base 0x022713C4, count 0x56C): candidates
  crit[15] 0x0E17, crit[86] 0x12D6, crit[128] 0x1445, crit[156] 0x14BA.
⚠️ The "no mention" test above is a crude grep over every 4-hex literal in
`check_allocations.py` and is an OVER-approximation. Before fixing a choice, read
`PHANTOM_CLAIMS` properly AND confirm the phantom is free in the CHAINED image too,
not just stock (`otn-register-phantom-same-edit`).

### S2-C17. ⭐⭐ PROVEN: THE DECK-SEND RESOLVER'S RETURN VALUE **IS** THE NEXT PHASE

This was the load-bearing unknown for clause 2, and it also closes an open question
`patch_dragon_shrine` has carried since 2026-08-18 (*"NOT PROVEN: that returning
0x7F from phase 0x7C re-enters selection cleanly ... this has never been
exercised"*).

**The phase is state, not an argument.** Resolver head:
```
0x02208dd6  ldr r5, =0x0229AAFC
0x02208dda  ldr r0, [r5, #0x70]     ; *** THE PHASE ***
0x02208ddc  cmp r0, #0x64 ; bgt ... ; ==0x64 -> 0x02209058 ; <0x64 -> 0x02209062
0x02208de6  subs r0,#0x78 ; cmp r0,#8 ; bhi -> 0x02209062
0x02208df8  add pc, r0              ; halfword jump table @0x02208DFA
```
Jump table decoded (targets relative to 0x02208DFC):
`0x78->0x0220904A  0x79/0x7A/0x7B->0x02209062  0x7C->0x02208F42  0x7D->0x02208EEE
 0x7E->0x02208EE4  0x7F->0x02208EB4  0x80->0x02208E0C`
— confirming **phase 0x7C == the gate at 0x02208F42**.

**The driving loop @0x02218032** (inside the activation state machine 0x02217F80,
r4 = 0x0229AAFC):
```
0x02218034  ldrh r1, [r4, #0x18]    ; the SAVED phase
0x02218038  str  r1, [r0, #0x70]    ; -> the phase word the resolver reads
0x0221803a  adds r0, r5, #0         ; the descriptor
0x0221803e  bl   0x0224AEB8         ; invoke slot 1 (the resolver)
0x02218042  strh r0, [r4, #0x18]    ; *** SAVE r0 AS THE NEXT PHASE ***
0x02218046  cmp  r0, #0 ; beq -> return 0xA (done)
0x0221804a  movs r0, #0x64          ; nonzero -> "call me again"
```
and the machine seeds it at `0x0221802C` with `movs r0,#0x80 ; strh r0,[r4,#0x18]`
— matching the documented `0x80 activate` entry phase.

⇒ **A resolver returns the phase it wants to run next.** Therefore:
- returning **0x7C from phase 0x7C RE-ENTERS phase 0x7C** — a two-pass follow-up is
  legal and needs no new machinery;
- returning **0x7F re-enters selection** — `patch_dragon_shrine`'s clause-2
  assumption is now PROVEN, not assumed. Its docstring's "NOT PROVEN" item 1 should
  be downgraded;
- returning 0 ends the resolution loop; returning 0x64 hits the resolver head's
  `cmp r0,#0x64` and runs the finalise arm 0x02209058.

**CONSEQUENCE — the clause-2 architecture simplifies substantially.** The
S2-C13 plan put the two-option prompt in slot 4 (Egotistical Ape's own home) and
worried about cloning Ape's `[0x0229AAFC+0x7C]` sub-machine. **That is no longer
needed.** The prompt goes in phase 0x7C itself, two passes, latched:

    pass 1: raise the prompt (0x0219ABB4), latch the descriptor, return 0x7C
    pass 2: read the choice, compute the amount, write the rider, clear the latch,
            return 0x64

This is BETTER than the slot-4 design on the merits, not just simpler: slot 4 runs
BEFORE the send, so a slot-4 chooser would have made the player pick the direction
before knowing which "Synchron" was sent. Phase 0x7C runs AFTER the send, which is
the printed order ("send ... THEN activate 1 of these effects").

⇒ **Clause 1's cls3 record stays EXACTLY Darklord Asmodeus's, unchanged**, with
slot 4 = the plain native once-per-turn stamp `0x021E5061`. Clause 2 adds no slot.

**The prompt ABI** (from Ape's `0x021E8B4A` block):
```
r0 = desc ; r1 = 0x0103 (prompt id) ; r2 = label(option0) ; r3 = label(option1)
[sp+0] = 0x01AC (title/default) ; [sp+4] = 0 ; [sp+8] = legality mask (seed 4,
                                   bit0 = option 1 legal, bit1 = option 2 legal)
bl 0x0219ABB4
```
answer read on the NEXT pass from **`[0x0229DD94 + 0x34]`** (selected index), and
Ape stores `selected + 1` into `desc[+0x18]`, which the resolver leaf tests with
`cmp #2`.

## Open Questions (updated 2)

- ~~how the player's up/down choice is expressed~~ CLOSED (S2-C9)
- ~~whether phase 0x7C can be re-entered~~ **CLOSED (S2-C17)**
- ~~whether a slot-4 clone is needed~~ **CLOSED — it is not (S2-C17)**
- Remaining: whether `0x0219ABB4` is asynchronous (Ape's phase split implies yes).
  The two-pass design is correct EITHER WAY, so this is not a blocker.

### S2-C18. ⚠️ CORRECTION TO S2-C10: the Level-DELTA rider is **kind 3**, not kind 2

S2-C10 decoded the write tail of resolver `0x02208499` and reported `kind = 2`.
That tail is real, but it is **the wrong resolver to copy for this clause.**
Egotistical Ape's resolver `0x022082A5` — whose printed clause IS ours — has its
own tail at `0x0220844E`:

```
0x0220844e  lsls r0, r4, #0x10
0x02208450  lsrs r0, r0, #0x10     ; value truncated to u16 (a NEGATIVE stays two's complement)
0x02208452  str  r0, [sp]          ; arg5 = VALUE
0x02208454  ldrb r0, [r5, #2]      ; side  (RAW desc[+2], not the ^desc[+6] form)
0x02208456  ldrb r1, [r5, #3]      ; zone
0x02208458  ldrh r2, [r5]          ; KEY = desc[+0] = the source card's own cid
0x0220845a  movs r3, #3            ; *** KIND = 3 ***
0x0220845c  bl   0x021C479C
0x02208460  movs r0, #0
```
and the negate path immediately before it:
```
0x022083fc  rsbs r0, r4, #0
0x022083fe  lsls r0, r0, #0x10
0x02208400  asrs r4, r0, #0x10     ; sign-extended negative delta
```

**Reading**: `0x02208499`'s tail (kind 2) serves Copy Plant, whose text is *"this
card's Level BECOMES that monster's current Level"* — a SET. `0x022082A5`'s tail
(kind 3) serves Egotistical Ape, whose text is *"INCREASE / DECREASE the Level BY
the Level of ..."* — a DELTA. Accel Synchron clause 2 is *"Increase / Reduce this
card's Level BY the Level of the sent monster"* = **a DELTA = kind 3.**

⚠️ I had the kind-2 tail in hand and was about to use it. The two resolvers look
alike and their tails differ by one immediate. **Mirror the card whose PRINTED
CLAUSE matches, not the resolver you disassembled first** — the same lesson as
`grep-the-template-cards-text-too`.

**DECISION: clause 2 mirrors Egotistical Ape's write EXACTLY**, changing only the
cid: `0x021C479C(side=desc[+2], zone=desc[+3], key=0x11A3, kind=3, value=delta_u16)`.

**ASSUMED (the one item for the in-game test):** that the Level recompute sums
kind-3 riders by KIND rather than looking up a specific cid KEY. Evidence for: the
native tail reads the key generically with `ldrh r2,[r5]` (no cid literal), and
`otn-attached-effect-rider` records that for kind<6 the key at +0 is simply the
source card's cid. If this is wrong the symptom is precise and unmistakable: the
effect resolves, the prompt appears, and the Level does not move.

### S2-C19. Design change: NO option-label table edit after all

S2-C12 planned two rows in the label table `0x0226F32C` over phantom 0x1916.
**Dropped.** The labels are only ever *arguments* to the prompt — Ape looks them up
with `0x021E5748(cid, index)` because its native code has no other way to name
them, but our ov5 stub can pass the ids `0x016E` / `0x016F` directly. Nothing else
reads the table for our cid.

⇒ **no phantom claim, no sorted insert, no shared-table edit.** Strictly less
regression surface. The only cosmetic cost is that we also skip Ape's phase-1 call
to `0x021C3BC8` (the chain announcement), so the chain display may name the chosen
branch generically. Recorded as a deliberate, reversible simplification: if the
in-game test shows a bad display, add the two rows then.

### S2-C20. BUILT AND STATICALLY VERIFIED (2026-09-04) -- **NOT IN-GAME CONFIRMED**

`.venv-1/Scripts/python.exe _build_accel_synchron.py --text`

| artifact | sha256 |
|---|---|
| `data/over_the_nexus/working/rom_accel.nds` | `1cb64ef968d14db1ab92aefdc56dbea0bf6cb53444b109ce77714f92f06cec98` |
| `rom_accel_compose.nds` (stage 2, vs patch_unknown_synchron) | `b87963baefa7a0e4a702325bee6c7d955bdabf66c8dc94d02ba10bf56ba41dc5` |
| `rom_dragon_shrine.nds` (rebuilt after the lift) | `66363888daf75766a5e461aac827409b8870efc9fcc9e480a0d0ed7c92e674b6` |

- `patch_accel_synchron.verify()` **PASS** including the eight new clause-1/2 checks
  (cls3 exactly one record, phantom dropped, 776 rows still sorted, slots ==
  Asmodeus's; criteria exactly one row, phantom dropped, 1388 rows still sorted,
  row == `{0x11A3, 0x4C, 0x0223CAF5, 0x2}`, and an explicit assert that the handler
  is **not** `0x0223CAD9`).
- **`patch_dragon_shrine.verify()` PASS after the lift** — rebuilt from scratch,
  all 12 checks including the new shared-dispatcher check.
- `scratch/followhook_equiv.py` **PASS** — 131 cids executed through both the old
  inline-dispatch stub and the new shared dispatcher; **only 0x11A3 changes
  (exit -> as)**; 0x14C1 and the three native cids (0x0DBF/0x1C15/0x1DC2) keep
  their destinations.
- `check_allocations` **PASS**: 177 ov5 slots (161 live), 155 phantom claims,
  ledger in sync.

**Slots claimed this session** (all registered in the same edit):
```
ov5:  CAVE_FOLLOWHOOK 0x0239E700 (0x80)   shared, owner deck_send_follow_hook
      CAVE_AS_FOLLOW  0x0239E780 (0x100)  accel_synchron clause 2, 200 B used
      CAVE_AS_LATCH   0x0239E880 (0x8)    accel_synchron clause 2
      CAVE_FREE       0x0239E700 -> 0x0239E890
phantoms: {pool: cls3_table,     cid: 0x0E13, owner: accel_synchron}
          {pool: populate_table, cid: 0x0E17, owner: accel_synchron}
```

**Landing indices** (for a continuation session): cls3[50], criteria row[78].

⚠️ **STATUS: BUILT -- AWAITING IN-GAME TEST.** A passing `verify()` is not
confirmation (CLAUDE.md). Still **NOT** wired into `apply_all_patches`.

⚠️ **The card is now NORMAL-DUEL-ONLY for clauses 1+2** (accepted by the user
2026-09-04). Clause 0's chassis is still pure data and still works in every mode;
clause 1 is also pure data, but clause 2's stub is in the ov5 cave, which overlay
41 evicts in a puzzle. Because the shared dispatcher now owns the phase-0x7C gate,
**Dragon Shrine's clause 2 has the same property it already had** (it was ov5 from
the start) -- but note the three NATIVE phase-0x7C cards (Power Baton, Venom Shot,
Hero Mask) now also route through ov5, so their follow-ups are normal-duel-only
too. That was already true of the shipped Dragon Shrine build; the lift does not
change it.

### S2-C21. THE ONE ASSUMED ITEM, and exactly how the in-game test falsifies it

Everything in the pre-build checklist is PROVEN except one thing:

**ASSUMED: the Level recompute sums kind-3 riders by KIND, not by a specific cid
KEY.** Evidence for: Egotistical Ape's native write tail reads the key generically
(`ldrh r2,[r5]` = desc[+0], no cid literal), and `otn-attached-effect-rider`
records that for kind<6 the key at +0 is simply the source card's cid.

**Falsification is unambiguous and costs one duel:** if it is wrong, the prompt
appears, an option is chosen, the effect finishes — and the Level does not move.
That symptom cannot be confused with any other failure in the table below.

### S2-C22. KB contributions (all VERIFIED with closed, passing proofs)

`verify_knowledge`: **422 -> 427 facts, 385 -> 390 PASS, 0 FAIL, 37 UNVERIFIED.**

| fact | what it pins |
|---|---|
| `dispatch.criteria_deck_handler_aux_aware` | `0x0223CAD9` ignores the aux; `0x0223CAF5` is the aux-aware twin. Proof asserts both encodings, that they share callee `0x0223BC3C`, and that the seven native archetype-deck-send cards still exist |
| `dispatch.resolver_return_is_next_phase` | the resolver's return value IS the next phase; asserts the phase read, the 9-entry jump table (incl. 0x7C -> 0x02208F42), and the driving loop's `strh r0,[r4,#0x18]` |
| `dispatch.two_option_effect_choice` | the whole "activate 1 of these effects" chain: legality mask, prompt `0x0219ABB4`, `[0x0229DD94+0x34]` -> `desc[+0x18]`, the `cmp #2` negate, and the 191-row label table |
| `dispatch.level_rider_is_kind_3` | DELTA = kind 3 (Ape) vs SET = kind 2 (Copy Plant); also pins `0x0202ABD8` as the Level bitfield reader |
| `dispatch.cls3_reaches_extra_deck_monsters` | corrects the over-reading of `otn-leave-trigger-cls2`; cls3 holds 79 Synchro records incl. Armory Arm |

⚠️ One proof failed on first run (`0x0223CAF5`'s `ldrsh r2,[r3,r0]` is `0x5E1A`,
not `0x5F1A`) and was corrected against the oracle — the self-check did its job.

## Next Experiment — THE IN-GAME TEST

Build: `.venv-1/Scripts/python.exe _build_accel_synchron.py --text`
Test **`data/over_the_nexus/working/rom_accel.nds`**
(sha256 `1cb64ef9...f06cec98`), **NORMAL DUEL ONLY** (clause 2 is an ov5 stub; a
puzzle loads overlay 41 over the cave and the stub is inert).

**Deck:** Accel Synchron in the Extra Deck. Main Deck: Junk Synchron (Lv3 Tuner),
at least two other "Synchron" monsters of DIFFERENT Levels (Nitro Synchron Lv2,
Road Synchron Lv4) so the arithmetic is distinguishable, several low-Level
non-Tuners, and **at least one non-Synchron Tuner as the negative control**.

| # | Step | Expected |
|---|---|---|
| 1 | Synchro Summon Accel Synchron (1 Tuner + non-Tuners totalling 5) | works — **clause 0 regression check** |
| 2 | Activate its effect | a picker listing **ONLY "Synchron" monsters from your Deck** |
| 3 | Confirm the non-Synchron Tuner is **NOT** offered | the negative control — this is what proves aux `0x004C` + handler `0x0223CAF5`, not merely that a picker appeared |
| 4 | Send a Level 2 "Synchron" | a **two-option prompt: increase / reduce** |
| 5 | Choose **increase** | Accel Synchron's Level reads **7** |
| 6 | Reset, repeat, choose **reduce** | Level reads **3** |
| 7 | Try to activate a second time the same turn | refused (once-per-turn) |
| 8 | After a Level change, use it as Synchro material at its NEW Level; re-run clause-0 oracles 4 (1 Tuner + TWO non-Tuners) and 6 (usable as a Tuner) | all still work |

**Distinguishable failures:**

| symptom | cause |
|---|---|
| no effect offered at all | the cls3 record is not reached |
| picker lists non-Synchrons | the aux/handler pair is wrong (should be impossible — `verify()` asserts the handler is not `0x0223CAD9`) |
| picker lists only Tuners | bit 15 crept into the word |
| card sent, **no prompt** | the phase-0x7C arm is not reached, or `0x0219ABB4`'s ABI differs |
| prompt appears, choice taken, **Level does not move** | **the one ASSUMED item (S2-C21): the recompute keys kind-3 riders by cid rather than by kind** |
| Level moves by the wrong amount | the GY-top read is not the card just sent |
| "reduce" offered when it would go to 0 | the legality mask (`current > amount`) is wrong |
| usable twice in one turn | `0x021E5061` is not stamping at activation |
| **Dragon Shrine regresses** | the shared-hook lift — but `followhook_equiv` says otherwise, and its ROM rebuilt and verified clean |

---

# SESSION 2026-09-04 -- IN-GAME TEST 1: clause 2 diagnosed and fixed

## The user's report, verbatim

> "Okay. I can still summon accel synchron. When I activate his effect, it lets me
> choose a synchron to send to the GY, and then prompts me to either increase or
> decrease the level. However, choosing either option does not change the level of
> accel synchron. See: .ml3 (after sending a monster, before choosing increase
> decrease), .ml4 (increase), .ml5 (decrease)"

Confirmed reading: clauses 0 and 1 work, clause 2's PROMPT works, only the Level
write fails. Exactly the falsification predicted in S2-C21.

## S3-C1. What the savestates proved WORKS (so it must not be touched)

`scratch/accel_diag.py` over `rom_accel.ml3/ml4/ml5` (RAM at file offset 0x24;
ROM identity checked by asserting CAVE_AS_FOLLOW holds this build's stub):

- **Pass 1 ran and computed correctly.** `CAVE_AS_LATCH[+4] = 2` -- the Level of the
  sent monster (GY top = Bri Synchron `0x23EE`). So the GY-top read and
  `0x0202ABD8` both work.
- **Pass 2 ran.** `CAVE_AS_LATCH[+0]` = the descriptor `0x0229A7FC` in ml3, and
  **cleared to 0** in ml4/ml5.
- **The rider was written AND linked.** Accel Synchron sat at side 0, zone 2. Node
  array `0x0229D33C`, **stride 10**, `{u16 key, u16 kind, u16 value, u16 flags,
  u16 next}`, list head in `zone_record[+0x0A]`. Chain for (0,2):
  `ml3: [2, 10]` -> `ml4/ml5: [2, 10, 11]`, and node 11 is
  `{key 0x11A3, kind 3, value +2 (ml4) / -2 = 0xFFFE (ml5)}`.

**So every byte my stub wrote was correct.** The bug was entirely on the READ side.

## S3-C2. ⭐ ROOT CAUSE: the Level getter honours only a HARDCODED SET of rider KEYS

`0x021B807C(side, zone, 0)` is the Level getter (the one Copy Plant's leaf and
Egotistical Ape's legality check both call, via thunk `0x021B8064`). Its final
formula, at `0x021B88B4`:

```
level = [sp+0xC] (base) + r4 + [sp+0x24]      then clamped to >= 1
```

Its kind<6 rider walk starts at `0x021B81E8` and, having accepted the kind,
**dispatches on the node's KEY**:

```
0x021b8204  ldrh r0, [r0]          ; node[+0] = THE KEY
0x021b8206  cmp  r0, #0x18D9  ; beq -> SET arm  ([sp+0xC] = node[+4])
0x021b820c  cmp  r0, #0x1F6A  ; beq -> DELTA arm (r4 -= (s16)node[+4])
0x021b8210  b    <IGNORED>
```
and further arms compare against a **stack-built table of cids** at
`0x021B82D6..0x021B8320+`, encoded base+-imm in the `thumb.stack_based_switch`
style (`0x2334 - 0x49 = 0x22EB`, `0x1DD0 + 0x62 = 0x1E32`, `0x206E - 0x51 = 0x201D`
...). **UNGREPPABLE, which is why no PC-relative load of these keys exists in ov3.**

⇒ **A rider keyed by an arbitrary donor cid can never be read.** The key is not
"the source card", it is a SEMANTIC SELECTOR drawn from a fixed set -- the same
idiom as the once-per-turn key `0x0FB6` (Time Wizard's cid) and the `0x1295`
override in the other stat resolver. My ASSUMED item (S2-C21) is FALSIFIED.

## S3-C3. ⭐ THE FIX, measured not inferred: key = `0x22EB`

`scratch/accel_level_probe.py` runs the real getter over the real board with
`scratch/thumbemu` and A/Bs the key on node 11 (ml4, base Level 5):

| key | card | v=+2 | v=-2 | v=+7 | v=-7 |
|---|---|---|---|---|---|
| **0x22EB** | **Egotistical Ape** | **7** | **3** | **12** | **1** |
| 0x1EC1 | Copy Plant | 2 | 65534 | 7 | 65529 |
| 0x1F6A | Star Blast | 3 | 1 | 1 | 1 |
| 0x201D | Level Retuner | 3 | 1 | 1 | 1 |
| 0x1E33 | Noisy Gnat | 6 | 6 | 6 | 6 |
| 0x1EA1 | Road Synchron | 6 | 6 | 6 | 6 |
| 0x18D9 | Level Conversion Lab | 5 | 5 | 5 | 5 |
| **0x11A3** | **our donor (as built)** | **5** | **5** | **5** | **5** |

**`0x22EB` ADDS the value to the base Level** -- positive = increase, negative =
reduce, clamped at 1. That is exactly clause 2's printed text AND exactly the sign
convention already in the stub, so **the fix is one constant.**

Why this key is safe: the node list is per-(side, zone), so an Egotistical Ape
elsewhere on the field owns a different list and cannot clash. Reusing a card's cid
as a semantic sentinel is the engine's own idiom here.

⚠️ Note 0x1EC1 (Copy Plant) yields 65534 for -2 -- an unclamped u16 underflow. It is
a SET-style arm and is the wrong shape for this clause; do not use it.

## S3-C4. Tool note

`scratch/accel_level_probe.py` and `scratch/accel_diag.py` are reusable: they run
the engine's own getter over a savestate and A/B a value offline. This diagnosis
cost ZERO extra duels (`otn-savestate-thumb-emulator`, `otn-escalate-to-measurement`).

## S3-C5. REBUILT WITH THE FIX (2026-09-04) -- **AWAITING IN-GAME TEST 2**

One-constant change in `patch_accel_synchron.py`:
`RIDER_KEY = 0x22EB` replaces `DONOR_CID` in the clause-2 stub's rider write.
**Nothing else changed** -- the sign convention the stub already emitted (positive =
increase, negative = reduce) is exactly what key 0x22EB consumes.

`data/over_the_nexus/working/rom_accel.nds`
sha256 **`7f5702cdda19ad3a0f42a79e399f58e4896b0309cc3bd1d26378f2e890d03347`**
(was `1cb64ef9...f06cec98`).

Two NEW regression guards in `verify()`, so this exact bug cannot come back:
- the clause-2 stub's literal pool **must** contain `0x22EB`;
- it **must not** contain the donor cid `0x11A3` as a rider key.

All guards green: `patch_accel_synchron.verify()` PASS; `check_allocations` PASS
(177 ov5 slots, 155 phantom claims, ledger in sync); `scratch/followhook_equiv.py`
PASS (only 0x11A3 changes destination); `verify_knowledge` **428 facts, 391 PASS,
0 FAIL**.

**KB contributed:** `dispatch.level_rider_key_is_a_selector` (VERIFIED, closed
proof), and `dispatch.level_rider_is_kind_3` amended in place with an explicit
"DO NOT read this as 'any cid works as the key'" warning pointing at it -- the
misreading of that fact is what cost the test.

## Next Experiment -- IN-GAME TEST 2

Test `rom_accel.nds` sha256 `7f5702cd...d03347`, **normal duel**. The earlier steps
1-3 (summon, Synchron-only picker, negative control) are already CONFIRMED by test
1 and only need a glance; the new information is entirely in steps 4-8.

| # | Step | Expected |
|---|---|---|
| 4 | Send a Level 2 "Synchron", choose **increase** | Accel Synchron reads **Level 7** |
| 5 | Reset, choose **reduce** | **Level 3** |
| 6 | Second activation the same turn | refused |
| 7 | Use it as Synchro material at its NEW Level | works at 7 (or 3) |
| 8 | Re-run clause-0 oracles 4 and 6 on a fresh copy | unregressed |

⚠️ Predicted from the measurement, worth confirming: reducing below Level 1 is
**clamped to 1** by the engine, and the stub additionally refuses to offer "reduce"
when `current <= amount`, so a Level 2 send on a Level 5 body always offers both.

---

# SESSION 2026-09-04b -- CLAUSE 3 (opponent's-Main-Phase Quick Effect)

## *** CLAUSES 1 + 2 IN-GAME CONFIRMED BY THE USER 2026-09-04 ***

On `rom_accel.nds` sha256
`7f5702cdda19ad3a0f42a79e399f58e4896b0309cc3bd1d26378f2e890d03347`.
Their exact words: **"Cool that works now. All that is left to add is the formula
synchron main-phase synchro effect."**

**What that confirms**: the picker offers a "Synchron" from the Deck, it is sent to
the GY, the two-option prompt appears, and **choosing either option now changes
Accel Synchron's Level** -- i.e. oracles 1-5 of the test plan, and the S3-C3 fix.

⚠️ **What it does NOT confirm** -- recorded so no later session mistakes silence for
a pass. The user did not report on:
- oracle 6, a second activation in the same turn being refused;
- oracle 7, using the card as Synchro material AT ITS NEW LEVEL (the card's point);
- oracle 8, clause-0 oracles 4 and 6 still unregressed.
These stay **UNTESTED**, not "passed".

## Clause 4 is DELIBERATELY OUT OF SCOPE (user ruling, 2026-09-04)

*"You can only Synchro Summon 'Accel Synchron' once per turn."* The user's decision,
verbatim: **"Do clause 3 only there isn't a precedence in the NDS game to only
summon a monster once a turn."** So the restriction has no engine precedent and the
card will ship without it -- a deliberate deviation, not an oversight. Do not
re-litigate it or "discover" it as a bug later.

## Clause 3 -- the printed text

> During your opponent's Main Phase, you can (Quick Effect): Immediately after this
> effect resolves, Synchro Summon using this card you control.

## Inherited, VERIFIED, re-checked this session

`synchro.opponent_turn_summon_is_formulas_cls3` **PASSES** (VERIFIED, 0x02249EC0).
Formula Synchron 0x239E ships this clause natively as THREE DATA ROWS, not code:
- cls3 record `{+04 resolver 0x02249EC1, +0C condition 0x021F1491, rest 0}`
- criteria row `{aux 0xFFFF, handler 0x0223D21D, word 0x00000802}`
- membership of the ARM9 spell-speed-2 list `0x0209C118`
  (`dispatch.responder_spell_speed_gate`, also PASSES)

Both the resolver and the criteria handler are **cid-agnostic**, and the condition
`0x021F1490` IS the printed timing (turn-log once-per-turn scan -> must be the
OPPONENT's turn -> Main Phase 1 or 2).
⚠️ Formula's cls1 record and its row in the proper-SS trigger list `0x0228F6C0`
belong to its DRAW effect and **must not be copied**.

## ⚠️ The problem clause 3 must solve first

**Our donor already owns a cls3 record** -- clause 1's ignition, at cls3[50]
`{0x02208DD5, 0, 0x021F0B71, 0x021E5061, 0}`. Clause 3 wants a SECOND cls3 record on
the same cid, and `find_event_handler` 0x0224A118 returns the **LEFTMOST** record for
a cid (`dispatch.cls_table_selector`), so a second record would be shadowed --
exactly the bug that made Warwolf E1 shadow E2
(`otn-warwolf-e1-native-responder-path`). **Resolve this before writing anything.**

Candidate routes, in the order they should be checked:
1. One cls3 record whose slots serve both clauses, discriminated by the event
   descriptor (the `criteria_row_hook` idiom: desc[+4] event code / desc[+5] class).
2. A SECOND CRITERIA ROW selected by event code on the one record -- the shape
   `card.ninja_grandmaster_hanzo_clause2` already ships
   (`otn-param-provider-internal-hook`: insert the 2nd row AFTER the 1st or the
   clauses swap silently).
3. Put clause 3 on a different cls table if its event reaches one.

## S4-C1. Clause 3's blocker is REAL, and the architecture that follows

**Two cls3 records on one cid cannot both be reached.** `dispatch.cls_table_selector`
(VERIFIED): `find_event_handler` 0x0224A118 binary-searches the table and does a
**leftmost-equal walk-back** @0x0224A808, returning ONE record. The Warwolf
precedent (`otn-warwolf-e1-native-responder-path`) is the same bug already paid for
once. So clause 3 CANNOT be a second cls3 record; it must share cls3[50] with
clause 1.

**The slots collide**, which is why a merge needs code:

| slot | clause 1 (shipped) | clause 3 (Formula) |
|---|---|---|
| +04 resolver | `0x02208DD5` deck-send | `0x02249EC1` synchro-summon |
| +0C condition | `0x021F0B71` once/turn ignition | `0x021F1491` opponent-MP quick effect |
| +10 cost | `0x021E5061` the once/turn stamp | 0 (must NOT stamp, or clause 3 eats clause 1's once-per-turn) |

**The discriminator is whose turn it is**, and it is free: Formula's own condition
already computes it (`[0x0229DD14+0x34] == 1 - desc[+2]`, per
`synchro.opponent_turn_summon_is_formulas_cls3`). So
`opponent's turn <=> [0x0229DD14+0x34] != desc[+2]` -- a four-instruction test.
Clause 1 is an ignition (your Main Phase); clause 3 is printed "During your
OPPONENT's Main Phase". The split is exactly the printed text.

⇒ three small ov5 dispatch stubs in slots +04 / +0C / +10.

**S4-C2. The criteria row is the second, subtler blocker.** Clause 3 needs its own
row `{aux 0xFFFF, 0x0223D21D, 0x0802, 0x0000}` while clause 1 keeps
`{aux 0x004C, 0x0223CAF5, 0x0002, 0x0000}`. But `criteria_row_hook`'s module
docstring records the ceiling verbatim: the row resolver 0x02243B9C walks to the
LEFTMOST row for the cid and adds r4, and **"for a cid in neither list it forces
r4 = 0"** -- so our donor can only ever address ROW 0. Both clauses would read
clause 1's row.

⇒ clause 3 needs **an arm in the shared `criteria_row_hook`** (the established
module, 4 cards registered) to hand it row 1, discriminated on the descriptor. That
means running `scratch/rowhook_equiv.py` and asserting no shipped arm moves --
`otn-shared-hook-lift-prove-by-execution`, the same discipline the phase-0x7C lift
used.

**S4-C3. The ARM9 spell-speed-2 list is clean.** `0x0209C118`, count immediate
`movs r2,#0x76` @0x02023490 = **118 entries, strictly sorted**, verified this
session against the stock ROM. `0x11A3` is NOT a member; its sorted position is 11.
**11 phantoms are present**, of which these are unclaimed in `PHANTOM_CLAIMS`:
`0x0E5B, 0x0E63, 0x0E6C, 0x0E82, 0x1529, 0x1534`. A count-neutral insert is
available (drop one below 0x11A3, e.g. **0x0E5B**, shift, count untouched).
⚠️ Re-check the chosen phantom against the CHAINED image before fixing it
(`otn-register-phantom-same-edit`).

## S4-C4. Clause 3 -- what was built (2026-09-04)

**PART J -- cls3[50] slots become three ov5 TURN SPLITTERS.** A second cls3 record is
impossible, so clause 3 shares clause 1's record and the three contended slots are
split on `[0x0229DD14+0x34] != desc[+2]`:

| slot | our turn (clause 1) | opponent's turn (clause 3) |
|---|---|---|
| +04 `CAVE_AS_RES` 0x0239E890 (32 B) | `0x02208DD4` deck-send | `0x02249EC0` Synchro Summon |
| +0C `CAVE_AS_COND` 0x0239E8D0 (32 B) | `0x021F0B70` ignition | `0x021F1490` opponent-MP timing |
| +10 `CAVE_AS_COST` 0x0239E910 (28 B) | `0x021E5060` stamp | return 1, **stamp nothing** |

Each is a pure TAIL-JUMP -- same (r0 = desc, r1 = arg) ABI on both sides, so LR is
never saved and only r2/r3 (scratch) are borrowed. r0 and r1 arrive at the native
callback untouched.

⚠️ **The cost splitter is a correctness requirement, not tidiness.** Slot 4
`0x021E5061` stamps key `0x0FB6` on (side, zone) -- the exact key clause 1's
condition queries. Unguarded, activating clause 3 on the opponent's turn would
silently eat clause 1's once-per-turn for the following turn. Formula's own record
carries slot 4 = 0.

**PART K -- the SECOND criteria row**, `{0x11A3, 0xFFFF, 0x0223D21D, 0x0802}`
(Formula's, verbatim), inserted **immediately after** clause 1's row over phantom
`0x0E2A`. Adjacency is asserted in `verify()`: the row resolver walks to the
LEFTMOST row for the cid and adds an offset, so a gap would make row 1 unreachable.

**PART N -- an arm in the shared `criteria_row_hook`.** Without it the row resolver
forces `r4 = 0` for a cid in neither membership list and clause 3 could never
address its own row. The arm uses the SAME turn test, so it cannot disagree with the
slot splitters. **Proved by execution**: `scratch/rowhook_equiv.py`, updated so
Jet Synchron counts as SHIPPED and Accel as ADDED, executed **23,040 inputs**
through the 4-arm and 5-arm stubs -- only `0x11A3` differs; `0x0FB1`, `0x1646`,
`0x1464` and `0x224C` are unchanged. Stub 180 B -> 216 B, within its 0x100 reserve.

**PART L -- ARM9 spell-speed-2 list `0x0209C118`.** Without membership the
opponent's-turn responder never polls slot 3 at all
(`dispatch.responder_spell_speed_gate`), so clause 3 would simply never be offered.
Count-neutral over phantom `0x0E5B`; base and count read from the CODE via
`patch_steam_synchron._read_thunk_list`, never hardcoded
(`setcode.slot_addresses_are_not_stable`). The list self-identifies (Blue-Eyes
Shining Dragon / Kuriboh / D.D. Crow must be members) before any write.

**Phantoms claimed**, both re-checked against the CHAINED image this session and
still unspent there: `{populate_table, 0x0E2A}` and `{quickeffect_list, 0x0E5B}`.
Ledger now 180 ov5 slots, 157 phantom claims.

## S4-C5. BUILT (2026-09-04) -- **AWAITING IN-GAME TEST**

`data/over_the_nexus/working/rom_accel.nds`
sha256 **`2f20d4e0153fc016b4605881eb9ab885b7e20c38acae5f851da9df72cb309718`**

All guards green:
- `patch_accel_synchron.verify()` **PASS** -- 28 clause-1/2/3 checks, including
  "exactly TWO criteria rows and they are ADJACENT", "still exactly ONE cls3 record",
  and the three splitters' our-turn targets still being Asmodeus's callbacks.
- `scratch/rowhook_equiv.py` **PASS** -- 23,040 inputs, only 0x11A3 differs.
- `scratch/followhook_equiv.py` **PASS** -- only 0x11A3 differs.
- `check_allocations` **PASS** -- 180 ov5 slots (164 live), 157 phantom claims,
  ledger in sync.
- `verify_knowledge` **428 facts, 391 PASS, 0 FAIL**.

Landing indices this build: cls3[50], criteria rows [77] (clause 1) and [78]
(clause 3), spell-speed-2 list index 10.

## Next Experiment -- IN-GAME TEST 3

Test **`rom_accel.nds` sha256 `2f20d4e0...cb309718`**, **NORMAL DUEL ONLY**.

**Deck**: as before, plus at least one Synchro monster in the Extra Deck that Accel
Synchron could actually make (it is a Tuner, so e.g. a Level 7/8 Synchro reachable
from Accel + a non-Tuner already on the field).

| # | Step | Expected |
|---|---|---|
| 1 | On YOUR turn, activate the effect | picker + increase/reduce prompt, exactly as before -- **clause 1/2 regression check** |
| 2 | End your turn with Accel Synchron on the field | -- |
| 3 | During your OPPONENT's Main Phase | you are offered the Quick Effect |
| 4 | Take it | you Synchro Summon using Accel Synchron, on the opponent's turn |
| 5 | Try it a SECOND time the same turn | refused (Formula's turn-log gate) |
| 6 | ⚠️ **The splitter's whole point**: on YOUR next turn, is clause 1 still available? | **YES** -- if clause 3 had stamped 0x0FB6, clause 1 would be dead |
| 7 | Untested from last round: use Accel Synchron as material AT ITS CHANGED Level | works |
| 8 | Clause-0 oracles 4 and 6 on a fresh copy | unregressed |

**Distinguishable failures:**

| symptom | cause |
|---|---|
| no offer at all on the opponent's turn | the ARM9 spell-speed-2 insert did not take, or slot 3 is not polled |
| offered on YOUR turn instead | the turn test is inverted |
| offered, but the picker is the DECK "Synchron" list | the criteria_row_hook arm is handing clause 3 row 0 |
| the summon is offered but does nothing | Formula's resolver did not get its row / param |
| clause 1 dead on the following turn | the COST splitter is not suppressing the 0x0FB6 stamp |
| clause 1 or 2 regressed | the cls3 merge broke the our-turn path |

## *** S4-C6. CLAUSES 0-3 IN-GAME CONFIRMED BY THE USER 2026-09-04 ***

On `rom_accel.nds` sha256
`2f20d4e0153fc016b4605881eb9ab885b7e20c38acae5f851da9df72cb309718`.
Their exact words:

> "Ship it! the opponents main phase synchro fired. and the level changes landed
> and persisted for the next synchro summon. all implemented clauses of the card
> are in game confirmed. Don't forget to update the card text!"

**What that measures:**
- **Clause 3 works** -- the Quick Effect is offered and taken during the OPPONENT's
  Main Phase and the Synchro Summon happens. So the cls3 turn-splitters, the second
  criteria row, the `criteria_row_hook` arm and the ARM9 spell-speed-2 insert are
  all live on the real path.
- **Clause 2 persists** -- "the level changes landed and persisted for the next
  synchro summon" closes **oracle 7**, the item left UNTESTED after test 2: the
  changed Level is what the summon machinery actually reads. That is the whole point
  of the card and it had never been exercised.
- Clauses 0 and 1 unregressed by the cls3 merge ("all implemented clauses").

⚠️ Still not separately reported, and therefore still UNTESTED rather than passed:
the clause-1 once-per-turn refusal (step 6 of test 2) and the clause-3 second-use
refusal (step 5 of test 3). Both are inherited native gates, not new code.

**User instruction carried into this session: "Don't forget to update the card text!"**

## S5-C1. ⚠️ CORRECTION: the "steam_synchron SYNCHRON_CORE names 0x0D6B" hazard is FALSE

Both the phase-1 findings and `card.accel_synchron_phase1` record a composition
hazard: *"patch_steam_synchron.SYNCHRON_CORE is a survival tuple that NAMES 0x0D6B
and its main() aborts on a missing core member ... if it is ever shipped alongside
this card, drop 0x0D6B from that tuple FIRST."*

**Read from the source this session, that is wrong.** `SYNCHRON_CORE` is
```
(0x1E07, 0x1E14, 0x1E4E, 0x1EA1, 0x1EBE, 0x1F46,
 0x20F7, 0x21A7, 0x224C, 0x239E, 0x23EE, 0x2414)
```
— twelve cids, and **0x0D6B is not among them**. So Accel dropping 0x0D6B cannot
trip Steam's `assert not missing`. No edit to that tuple is needed.

Also stale: the phase-1 note said steam_synchron "is not in apply_all_patches today
(verified: 0 hits)". **It is now** — `apply_all_patches.py:1784` and
`_verify_all_patches.py:103`. The three Synchron-list patches spend three DIFFERENT
slots (unknown_synchron the phantom 0x2501, steam_synchron the stale 0x229E, accel
the inert 0x0D6B), so the list stays a sorted 15 with all three donors in it.
The chain build is the arbiter and is what actually settles this.

## S5-C2. Card text -- why it is a LADDER and not the printed text

The user's instruction was "Don't forget to update the card text!".  The printed
text is ~350 B.  **It cannot ship, and that is measured, not assumed:**

- per-language IN-PLACE budgets for card_prop index 489 (the length of the card's
  CURRENT string, which is what the shared writer enforces):
  `k 37, e 44, g 44, f 45, j 46, s 47, i 55, r 94`;
- **every `card_desc_<L>.bin` is packed solid** -- measured this session across all
  eight languages: trailing slack is **0-3 B** and the largest interior gap is
  **3 B** (alignment padding);
- **there is no phantom desc slot to steal**: all 4305 `card_prop` entries map to
  real cards, so no index entry points at a never-displayed string;
- growing the blob is recorded by `patch_steam_synchron` as overflowing "a
  fixed-size buffer" and freezing text rendering.

The shared writer takes ONE description and SKIPS any language it does not fit --
which would leave that language showing **Bracchio-raidus's Fusion flavour text**.
So the card now ships a `DESC_LADDER` and `main()` drives the writer once per
(description, languages) group, giving every language the longest entry its own
slot holds:

| bytes | languages | text |
|---|---|---|
| 94 | r | `1 Tuner + 1+ non-Tuners. Once/turn: send 1 Synchron from Deck to GY, then Level +/-. Quick SS.` |
| 53 | i | `1 Tuner + 1+ non-Tuners. 1/turn: Level +/-. Quick SS.` |
| 45 | f j s | `1 Tuner + 1+ non-Tuners. Level +/-. Quick SS.` |
| 42 | e g | `1 Tuner + 1+ non-Tuners. Lv +/-. Quick SS.` |
| 32 | k | `1 Tuner + 1+ non-Tuners. Lv +/-.` |

A module-level assert proves all eight languages are covered, and `verify()` now
checks each language against `_desc_for(L)` rather than one global string.

⚠️ **The standing open task is unchanged and now has evidence attached**: shipping
the full card text needs a card_desc blob APPEND plus a `desc_off` repoint in
card_indx, and the blobs have no slack, so it means growing a packed file that the
engine may read into a fixed-size buffer. Not attempted here.

## S5-C3. Single-card rebuild with the text ladder (2026-09-04)

`rom_accel.nds` sha256
**`e3898ac87226358defc787c6d05a602d93d5051132b6db4ca88ab1bc0c369a21`**
(was `2f20d4e0...cb309718` before the text change).
`patch_accel_synchron.verify()` **PASS, 0 failures**, and every one of the eight
languages now carries the longest ladder entry its slot holds -- r and f and j fill
their slots exactly (94/45/45 of 94/45/46), none falls back to the donor's text.

⚠️ Only the DESCRIPTION changed between `2f20d4e0` (the in-game-confirmed build) and
`e3898ac8`. No overlay-3, ov5 or ARM9 byte differs, so the user's clause 0-3
confirmation carries over -- but that is an inference from the diff, not a retest.

## *** S5-C4. SHIPPED 2026-09-04 ***

Wired into `apply_all_patches` as **step 50 of 51** (immediately after Steam
Synchron; WiFi timers remain last), and added to `_verify_all_patches.SHIPPED` in
the same edit (`otn-chain-build-verify-artifact`).

| artifact | sha256 |
|---|---|
| `rom_accel.nds` (single-card) | `e3898ac87226358defc787c6d05a602d93d5051132b6db4ca88ab1bc0c369a21` |
| `rom_all_patches.nds` (**51/51**) | `f1c61ce2e909958c7e83f7015c58952a3b6bf108b60b6268ce4022410c682c17` |

The old chain ROM was MOVED ASIDE to `rom_all_patches.PREV.nds` before the build,
so the artifact asserted below cannot be a stale file that a silently-dead build
left in place (`otn-chain-build-verify-artifact`: exit 0 has lied twice).

**Asserted on the BUILT chained ROM, not on the exit code:**
- `ALL 51 PATCHES APPLIED`, log reached `51/51`, file rewritten at build time.
- **`_verify_all_patches.py`: PASS 40, FAIL 0, SKIP 2** (the two skips are
  `patch_boggart_knight` and `patch_darksoul`, which have no `verify()` of their
  own -- pre-existing, not caused by this change).
- Direct composition read of the chained ROM:
  - **exactly ONE** cls3 record for 0x11A3, slots
    `0x0239E891 / 0 / 0x0239E8D1 / 0x0239E911 / 0` (the three turn splitters);
  - **two ADJACENT** criteria rows at **[70, 71]** -- row 0 `{aux 0x004C,
    0x0223CAF5, 0x00000002}` (clause 1), row 1 `{aux 0xFFFF, 0x0223D21D,
    0x00000802}` (clause 3).  ⚠️ They sat at [77, 78] in the single-card build:
    other patches consume rows, which is exactly why `verify()` anchors on the CID
    and never on an index;
  - ARM9 spell-speed-2 list: 118 entries, strictly sorted, holding BOTH
    0x11A3 (accel) and 0x12B6 (steam), phantom 0x0E5B gone;
  - "Synchron" set-code list: 15 entries, strictly sorted, holding ALL THREE
    donors 0x11A3 / 0x12B6 / 0x181C with all three drops gone.
- `check_allocations` PASS, ledger in sync.
- `verify_knowledge` **429 facts, 392 PASS, 0 FAIL**.

**KB**: `card.accel_synchron_clauses123` added (VERIFIED, closed proof), carrying
the user's sign-off and the correction to `card.accel_synchron_phase1`'s false
SYNCHRON_CORE hazard.

**Remaining known gaps, deliberate and recorded:** clause 4 is not implemented (user
ruling: no NDS precedent for a once-per-turn SUMMON restriction); the printed text
cannot ship in full (packed, ungrowable desc blobs) so a per-language ladder is used;
and clauses 1-3 are normal-duel-only because their stubs live in the ov5 cave.
