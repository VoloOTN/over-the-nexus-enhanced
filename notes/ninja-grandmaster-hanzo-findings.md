# Ninja Grandmaster Hanzo — findings (session 2026-08-30)

Printed text (`scratch/ygoprodeck_cache.json`, id 95027497) — DARK / Warrior /
Level 4 / 1800 / 1000:

> When this card is Normal Summoned: You can add 1 "Ninjitsu Art" card from your
> Deck to your hand. When this card is Flip or Special Summoned: You can add 1
> "Ninja" monster from your Deck to your hand, except "Ninja Grandmaster Hanzo".

Clauses:

1. **C1 — IN-GAME CONFIRMED by the user 2026-08-30.** *Normal* Summoned → add 1
   "Ninjitsu Art" **card** (any card type) from Deck to hand.
2. **C2 — IN-GAME CONFIRMED by the user 2026-08-30, and SHIPPED.** *Flip or
   Special* Summoned → add 1 "Ninja" **monster** from Deck to hand, **except
   this card**.

**STATUS: ✅ C1 DONE — IN-GAME CONFIRMED BY USER 2026-08-30, on the FIRST test,
all five checklist items.** Their exact words:

> 1. Works as described, effect activate, prompt and only ninjitsu art cards
>    proposed.
> 2. Works as described
> 3. Nothing happens
> 4. No regressions
> 5. Archetype filter works

— reading confirmed by the user before it was acted on. So: the prompt fires on
Normal Summon and offers ONLY the two Ninjitsu Art cards; no prompt when the Deck
holds none; nothing on Flip/Special Summon (correct, C2 is not built); Machina
Gearframe unregressed; and the deck-editor archetype filter is fine after the
set-code `0x2A` repurpose and the Armed Ninja displacement.

**NOT shipped** — still not wired into `apply_all_patches`, pending the user's
say-so.

## BUILT (clause 1) — `otn_enhanced/cards/ninja_grandmaster_hanzo.py`

Five table edits, **none of them code** — no Thumb emitted, no ov5 cave slot, so
the card is NOT normal-duel-only.

| part | where | edit |
|---|---|---|
| A | ARM9 `0x0209C5D2` | set code `0x2A` (inert, 4 phantoms) becomes "Ninjitsu Art": entries 0/1 → `0x1768` / `0x17FF`. 4 bytes, still sorted, `movs r2,#4` untouched |
| B | ARM9 `0x0209C722` | Ninja set code `0x06`: Armed Ninja `0x117B` → the donor `0x13E7` @0. 2 bytes, still 9 and sorted |
| C | ov3 `0x0228F7AC` | code-7 (Normal Summon) list: insert `0x13E7` @5, drop phantom `0x14CC` @8 |
| D | ov3 cls1 | insert @155 `{0x13E7, 0x02207EF5, 0, 0x021F0821, 0x021E51E5, 0}` (Gearframe verbatim), drop phantom `0x143E` @165 |
| E | ov3 crit | insert @123 `{0x13E7, 0x002A, 0x0223CAF5, 0x0000000E}`, drop phantom `0x143D` @127 |
| F | bin2.pac | Effect Monster / DARK / Warrior / Lv4 / 1800 / 1000; name in place in 6/8 languages, appended in j/k; desc in place in all 8 |

Build: `.venv-1/Scripts/python.exe _build_hanzo.py --text`
ROM: `data/over_the_nexus/working/rom_hanzo.nds`
sha256 `ec7d75a2f0b06f8f866354d24823853c257a6c64979488b7d78a0d8964b9e148`
(deterministic — two clean builds from `rom.nds` produced the same digest).

`verify()`: **25/25 PASS** (static only). `check_allocations`: OK, ledger in
sync, 111 phantom claims. `verify_knowledge` at session end: **362 facts,
327 PASS, 0 FAIL, 35 UNVERIFIED**.

⚠️ **NOT wired into `apply_all_patches`** — single-card ROM only until the user
approves shipping.

⚠️ One `verify()` FAIL during the build was **my own assertion constant**, not
the ROM: I wrote `cmp r1,#0x70` as `0x2870`; the real Thumb encoding is `0x2970`
(`0x2800 | Rn<<8 | imm8`). Fixed; the ROM bytes never changed.

Donor: **Melchid the Four-Face Beast `0x13E7`** (user-chosen).
Ninja set-code membership bought by dropping **Armed Ninja `0x117B`**
(user-chosen).

---

## Confirmed (proven this session)

### The 3DS ships Hanzo, and gives Konami's own record for C1

* **Hanzo = cid `0x26AF`** on the 3DS. Found via
  `3ds_extract/partition0/romfs/duel/card/CARD_Indx_E.bin` (5888 × `{u32 name_off,
  u32 desc_off}`) + `CARD_Prop.bin` record *i* masked `0x3FFF`. Name index 4950.
* Its rows in the 3DS main-effect registry `0x686CBC` (stride `0x0C`,
  `{u16 cid, u16 aux, u32 handler, u32 word}`):

  | row | cid | aux | handler | word | = clause |
  |---|---|---|---|---|---|
  | 1540 | `0x26AF` | `0x7B` | `0x004B1C1C` | `0x0000000E` | C1 (Ninjitsu Art) |
  | 1541 | `0x26AF` | `0x06` | `0x004B1C1C` | `0x00000022` | C2 (Ninja, except self) |

* On-summon registry `0x6C335C`[281] = `{0x26AF, router 0x4604B4, 0, 0x49CC14,
  0x4001F4, 0}` — the same router Wattcobra uses.
* **3DS `0x004B1C1C` == NDS `0x0223CAF5`** is already a VERIFIED KB fact
  (`dispatch.threeds_deck_handler_equivalence`, pinned by Dragon Ravine's row
  pair). So both Hanzo rows carry straight across; only `aux` needs remapping.

### `aux` in a criteria row IS the has_set_code index (disassembled)

`0x0223CAF4` = the Deck-search criteria handler `(r0 = row, r1 = side)`:

```
0223CAF6  adds  r3,r0,#0      ; r3 = row
0223CAFA  ldrsh r2,[r3,#2]    ; aux, SIGNED  (0xFFFF = -1 = no set-code filter)
0223CAFC  str   r2,[sp,#8]
0223CAFE  ldr   r2,[r3,#8]    ; the criteria word
0223CB00  str   r2,[sp]
0223CB02  str   r0,[sp,#4]    ; type 2
0223CB06  ldrh  r1,[r3]       ; the row's cid
0223CB08  ldr   r2,=0x0223C825    ; the set-code predicate
0223CB0A  add   r3,sp,#8          ; -> the one-element aux list
0223CB0C  bl    0x0223BC3C
```

`0x0223C824` masks the candidate to 14 bits (`lsls #0x12 / lsrs #0x12`) and
tail-calls **`0x020240D8`**:

```
020240D8  push {r3,lr}
020240DA  cmp  r1,#0x70 ; blt   ; else return 0
020240E2  lsls r2,r1,#2
020240E4  ldr  r1,=0x0209D0D8   ; the has_set_code pointer table
020240E6  ldr  r1,[r1,r2]
020240E8  blx  r1
```

So a criteria row's `aux` is literally `has_set_code(candidate, aux)`, bounded to
`< 0x70` (112 entries).

### The NDS "Ninja" set code is `0x06`

`0x0209D0D8[0x06]` → thunk `0x020237D8`:
`ldr r1,=0x0209C722 ; ldr r3,=0x02022E15 ; movs r2,#9 ; bx r3`
(count immediate at **`0x020237DC`**, list-base pool at `0x020237E0`).

Sorted 9-entry list @ **`0x0209C722`**:
`0x117B` Armed Ninja, `0x16B8` Crimson Ninja, `0x16B9` Strike Ninja,
`0x1754` Lady Ninja Yae, `0x17DF` Ninja Grandmaster Sasuke, `0x18BE` White Ninja,
`0x1BCB` Goe Goe the Gallant Ninja, `0x238B` Karakuri Ninja "Sazank",
`0x2467` Karakuri Ninja "Kuick".

* **No phantom** — every entry is an obtainable card, so an insert must drop a
  real Ninja.
* **Zero consumers in the stock ROM**: no criteria row carries `aux 0x06`, and
  the only aligned pointer to the thunk anywhere in arm9+ov3 is the table slot
  `0x0209D0F0` itself.

### There is NO "Ninjitsu Art" set code on the NDS

`0x1768` (Ninjitsu Art of Transformation) occurs exactly once in ARM9
(`0x0206C37C`, not a set-code list); `0x17FF` (Ninjitsu Art of Decoy) occurs
zero times. The 3DS's `aux 0x7B` has no NDS counterpart.

### Set code `0x2A` is completely inert — the free slot

Thunk `0x02023B10`:
`ldr r1,=0x0209C5D2 ; ldr r3,=0x02022E15 ; movs r2,#4 ; bx r3`
(count immediate at **`0x02023B14`**, list-base pool at `0x02023B18`).
List @ **`0x0209C5D2`** = `{0xEA1, 0xEA2, 0x1C55, 0x1C5F}` — **all four are
phantoms with no `card_prop` record**. No criteria row carries `aux 0x2A`; no
extra aligned pointer to the thunk. Repurposing it costs 4 bytes and no code.

### The summon trigger is a data table (re-read live this session)

`summon.trigger_is_a_membership_list` re-verified: nine sorted lists, all
strictly sorted, phantom availability measured —

| list | base | count | gate | free phantoms |
|---|---|---|---|---|
| code 7 Normal | `0x0228F7AC` | 0x67 | 7 | 0xE74, 0xE7E, 0xE7F, **0x14CC**, 0x15D0, 0x19C0, 0x19D3, 0x1B1A, 0x2346 |
| code 7 + tribute | `0x0228F5B8` | 0x12 | Monarchs | 0x172D, 0x1737, 0x1A0A |
| code 8 Flip | `0x0228F580` | 0x0C | 8 | 0x1A9F |
| code 9 Special | `0x0228F63A` | 0x1F | 9 | 0xE12, 0x167C, 0x176C, 0x1ABE, 0x1ABF |
| code 9 + `[+0x12]==cid` | `0x0228F5DC` | 0x17 | | 0xEC9, 0x1B8F |
| code 9 + proper | `0x0228F6C0` | 0x24 | | (none) |
| code 7 or 8 | `0x0228F598` | 0x10 | | 0x120E, 0x12B4, 0x16FD, 0x19C6 |
| code 7 or 9 | `0x0228F60A` | 0x18 | | 0xE17, 0xE77, 0x164A, 0x1B6B |
| any code | `0x0228F678` | 0x23 | | 0xE1B, 0xE8C, 0xE8F, 0x14BB, 0x19C2, 0x1CB1 |

### Native NDS precedents for the exact clause shape

| card | cid | cls1 `{+04,+08,+0C,+10,+14}` | criteria row | list |
|---|---|---|---|---|
| **Machina Gearframe** | `0x21F5` | cls1[1147] `{0x02207EF5, 0, 0x021F0821, 0x021E51E5, 0}` | crit[1109] `{0x21F5, 0x13, 0x0223CAF5, 0x00000022}` | c7 |
| Genex Blastfan | `0x1FA8` | cls1[967] — same five slots | crit[852] `{0x1FA8, 0x36, 0x0223CAF5, 0x02000002}` | c9 |
| Karakuri Inashichi | `0x2389` | cls1[1238] `{0x02207EF5, 0, 0x0224A115, 0, 0}` | crit[1256] `{0x2389, 0x5D, 0x0223CAF5, 0x0000000E}` | c7 |
| Gem-Armadillo | `0x22C1` | cls1[1191] — same as Gearframe | crit[1189] `{0x22C1, 0x54, 0x0223CAF5, 0x00000002}` | c7 |
| Fabled Grimro | `0x1F9D` | — | crit[847] `{0x1F9D, 0x41, 0x0223CAF5, 0x00000022}` | — |

Set code `0x13` = "Machina" (list `0x0209C734`, 9 entries, all nine Machina
cards) — which is what makes Gearframe's row the direct analogue.

### Both per-cid switches this patch rides DEFAULT for an unlisted cid

* **slot3 `0x021F0820`** (Gearframe `+0C`): side = `desc[+2] ^ desc[+6]`;
  `bl 0x021BAD70(side)`; a per-cid switch on `ldrh r1,[r5]` sets `r4` = 3 for
  `0x1FC9`, 2 for `0x2049`, 3 for `0x2410`, **default `r4 = 1`**; then
  `0x02234E78(desc)` → param, `0x02243FE0(side, cid, param)` → candidate count,
  and `return count >= r4`. For an unlisted donor that is exactly
  *"activatable iff at least one legal candidate exists"* = "You can add".
* **resolver `0x02207EF4`** (`+04`): opens with the same
  `desc[+2] ^ desc[+6]`, `movs r4,#1`, then a per-cid switch whose default is
  `b 0x02207FCC`. An unlisted donor keeps `r4 = 1`.

### NEW ENGINE FACT — criteria-word bit 5 (`0x20`) = "except this card"

Scanned all `0x56C` rows of `0x022713C4`: **53 carry bit 5, and 51 of them belong
to cards printed with "except"** (Machina Gearframe, Fabled Grimro, every
Gladiator Beast, Batteryman Charger, Scrap Goblin/Beast/Soldier/Worm/Orthros,
Koa'ki Meiru Urnight, The Agent of Mystery - Earth, …). The two that do not are
Destiny Hero - Fear Monger and Test Tiger. This bit is **absent from
`dispatch.criteria_word_fully_decoded`'s documented mask list** (which covers
bits 1, 10, 13, 14, 15, 16) — a genuine gap in the KB.

### Donor vetting — Melchid the Four-Face Beast `0x13E7`

`donor_scan 0x13E7`: *"CLEAN — no data structure names this cid"*, **zero**
ARM9 data-region hits, **zero** ov3 hits. Normal Monster, DARK / Fiend / Lv4 /
1500 / 1200, booster pack 1.
Name slots: e 27, f 34, g 35, i 31, j 14, k 13, r 30, s 37 —
`"Ninja Grandmaster Hanzo"` is 24 B with the NUL, so in place in 6 of 8
languages, appended + repointed in j/k.
Desc slots: e 65, f 73, g 84, i 77, j 58, k 48, r 118, s 78 — the compact
description is sized to fit the 48 B floor in place everywhere.

Insert positions computed live: c7 index 5, cls1 index 155, criteria index 123.
Melchid is present in none of the three tables beforehand.

---

## Ruled Out

* **"Add the donor to the Ninja list without cost."** Impossible — the 9-entry
  list `0x0209C722` has no phantom, so membership must displace a real Ninja.
* **A native "Ninjitsu Art" set code.** Does not exist (see above); the 3DS's
  `0x7B` has no NDS twin, so C1 needs either a repurposed inert set-code list
  (chosen) or an ov5 custom filter (the Wattcobra recipe, rejected because it
  would make the card normal-duel-only for no benefit).
* **A second cls1 record for the donor.** `dispatch.second_cls1_record_is_spirit_only`:
  the `leftmost + offset` path requires `card_type >> 1 == 7` (Spirit Monster).
  Melchid will be card_type 3. So C1 and C2 must share one cls1 record, which is
  why C2 needs a criteria row-selector rather than a second record.
* **`aux 0x06` is consumed by the Ninjitsu Art cards.** It is not — both test
  "Ninja" through their own per-cid switch predicates (Transformation's slot2
  `0x021DA1C8`, Decoy's `0x021E0680`), which switch on the ACTING card's cid at
  `ldrh r0,[r6]`. So dropping Armed Ninja from set code `0x06` does **not**
  stop Ninjitsu Art of Transformation/Decoy from using it.

---

## Settled by the in-game test (2026-08-30)

* **THE ONE LIVE-PATH ASSUMPTION IS NOW PROVEN, AND IT IS THE MOST REUSABLE
  THING THIS SESSION PRODUCED.** Inserting a **records-free donor** into a
  summon-trigger membership list and giving it a fresh cls1 record **does fire**.
  Before this card that route was documented by
  `summon.trigger_is_a_membership_list` but had never been exercised by a shipped
  patch — `card.azure_eyes` hooked the search at `0x022658B8` instead, and only
  because *its* donor already owned a cls1 record, which made the list route look
  harder than it is. It is not: for a records-free donor a "when this card is
  Summoned" trigger costs **one u16 in a sorted list plus one cls1 row, and zero
  code**. Checklist item 1 fired on the first test.
* **The activation condition gates on candidate existence, as read.** Item 2
  (no Ninjitsu Art left in the Deck → no prompt) confirms slot3 `0x021F0820`
  takes its default arm `r4 = 1` for an unlisted donor and returns
  `0x02243FE0(...) >= 1`. The per-cid-switch-defaults reading was right.
* **`aux` really is the has_set_code index, end to end.** Item 1 offered *only*
  the two Ninjitsu Art cards, i.e. the repurposed set code `0x2A` filtered
  correctly through `0x0223CAF4 → 0x0223C824 → 0x020240D8 → 0x0209D0D8[0x2A]`.
* **Repurposing an inert set code is safe and invisible.** Item 5: the deck
  editor's archetype filter is fine, so the ARM9 UI readers (`0x0202A358`,
  `0x0202A3F0`) tolerate a rewritten member list.
* **The shared Gearframe template is not damaged by cloning it.** Item 4: Machina
  Gearframe still searches a "Machina" monster on its own Normal Summon.

## Open Questions

* slot4 `0x021E51E5` is still not decoded; taken verbatim from Gearframe and
  Genex Blastfan. It demonstrably does no harm here, but that is not a decode.
* Armed Ninja `0x117B` is out of the Ninja set-code list. Nothing consumes set
  code `0x06` today, so the only live cost is that **C2's search will not be able
  to fetch Armed Ninja** — accepted by the user 2026-08-30.

---

## SESSION 2026-08-30b — C2 IN-GAME CONFIRMED AND SHIPPED

**Status: clause 2 IN-GAME CONFIRMED BY THE USER 2026-08-30 on the first test,
and SHIPPED into `apply_all_patches` on their "Ship it!".**

Their exact words:

> 1. When hanzo is flipped summoned, he behaves correctly, prompts me to add a
>    ninja, and the ninja gets added to hand
> 2. When Hanzo is normal summoned I can add a ninjitsu art, as per, no
>    regressions
> 3. No regressions on machina gearframe either.
> 4. When hanzo is special summoned, he behaves correctly, prompts me to add a
>    ninja and the ninja gets added.

and, asked specifically about the except-self bit:

> Hanzo did not search itself so the exclusion held.

So all four load-bearing claims are confirmed: both trigger inserts fire (code 8
AND code 9), the row selector picks row 1 on Flip/Special and **still row 0 on
Normal** (not inverted), the resolver delivers to hand, and criteria-word bit 5
excludes the searcher itself.

⚠️ **NOT observed either way:** Flip/Special Summon with **no other Ninja left in
the Deck** (expected: no prompt). Clause 1's identical negative control passed
and both clauses share the slot3 activation condition, so it is very likely
fine — but it is untested. Worth one glance next time a duel happens.

`verify()` 48/48, `check_allocations` OK.

### Chain build (2026-09-01)

Rebuilt after the card-text fix, with the old ROM moved aside first so the
artifact could not be confused with a stale one (`otn-chain-build-verify-artifact`
— exit 0 has lied twice here):

* **44/44 patches applied**, WiFi timers last, 0 tracebacks, 25m16s.
* `data/over_the_nexus/working/rom_all_patches.nds`, sha256
  `d4c34abd54bf293c0cc8518e0465a4c64880698f1506f61a979fe0d92c01e36a`
  (written 13:13; the stale 12:36 file was moved to `.PREV.nds`).
* `_verify_all_patches.py`: **33 PASS / 0 FAIL / 2 SKIP** (boggart_knight and
  darksoul have no `verify()` of their own).
* Hanzo's own checks all pass against the combined ROM — note the two criteria
  rows land at **118/119** there, not 122/123, because other patches also insert
  into the criteria table. Adjacency and clause order both hold, which is the
  property that matters.
* Composition with the later Ninja cards is clean: the sweep confirms
  `0x13E7 is still a Ninja (no regression)` after `0x12B2` joined set code `0x06`
  by displacing Karakuri Ninja "Sazank" `0x238B`.

ROM `data/over_the_nexus/working/rom_hanzo.nds`, sha256
`e33e6b9bfd80c092af5c9d399eab94d2eae40087ad175394c0d835a988fc2e74`.

⚠️ **The build the user tested was `d50d5591…`.** The only change since is the
**card text**: the printed description still described clause 1 alone
(`"Normal Summon: add 1 Ninjitsu Art from Deck."`). **The user caught that, not
`verify()`** — which checked the NAME in all 8 languages but never the
DESCRIPTION. No table, stub or hook byte differs, so the in-game result carries.
`verify()` now checks the description in all 8 languages *and* that it mentions
both clauses.

New text: `"Normal: 1 Ninjitsu Art. Flip/SS: 1 other Ninja."` (47 B).
⚠️ The budget is **48 B, not the 52 B blob slot** — `apply_stats_and_text`'s fit
test is `len(desc) <= len(OLD desc)` and Melchid's shortest existing string is
Korean at 48 B. Exceed it and Korean silently keeps "a monster with four masks".
`DESC_MAX_B` in the module now pins this.
Build: `.venv-1/Scripts/python.exe _build_hanzo.py --text`; the in-game
checklist is at the top of `_build_hanzo.py`.

Five parts, all in `patch_ninja_grandmaster_hanzo.py`:

| part | where | edit |
|---|---|---|
| G | ov3 crit @123 | `{0x13E7, aux 0x0006, 0x0223CAF5, 0x00000022}` inserted **after** C1's row (index 122/123); drop phantom `0x0E14` |
| H | ov3 `0x0227134C` | LIST A: insert `0x13E7`, drop the row-free member `0x0D81` |
| I | ov3 `0x0228F580` / `0x0228F63A` | code-8 insert (drop `0x1A9F`), code-9 insert (drop `0x0E12`) |
| J | ov3 `0x02234E84` → ov5 `0x0239D900` | retargeted L1 search `bl`; 0x24 B row-selector stub |

⚠️ **The card is no longer puzzle-safe, deliberately.** PART J's hook is inside
the shared param provider, and ov5 is evicted in puzzles — so a puzzle now
crashes on the first deck-search by *any* card. Explained to and accepted by the
user 2026-08-30. Reversing it = relocating PART J's stub alone into 26 B of ov3.

The stub as it sits in the built ROM (read back, not assumed):

```
0239d900: ldr  r3,[pc,#0x18]      ; = 0x000013E7
0239d902: cmp  r0,r3
0239d904: bne  0x239d916
0239d906: ldrb r3,[r5,#4]         ; event code
0239d908: cmp  r3,#8
0239d90a: blt  0x239d916
0239d90c: cmp  r3,#9
0239d90e: bgt  0x239d916
0239d910: movs r0,#1
0239d912: add  sp,#4
0239d914: pop  {r4,r5,r6,r7,pc}
0239d916: ldr  r3,[pc,#8]         ; = 0x02022E15
0239d918: bx   r3
```

New KB facts: `dispatch.param_provider_internal_hook`,
`card.ninja_grandmaster_hanzo_clause2`; `dispatch.row_param_provider_call_sites`
**corrected** (two sites → three) with a proof that now pins the whole call-site
set so it cannot be undercounted again.

---

## SESSION 2026-08-30b — C2 design CORRECTED (read this before the section below)

The section *"Next Experiment — C2, and it is fully designed"* below is the
2026-08-30a handoff. **Two of its claims are wrong**; both were falsified by
disassembly this session. It is kept for provenance — the corrections here win.

### ⚠️ CORRECTION 1 — there are THREE provider sites on this card's path, not two

Of the 60 `bl 0x02234E78` sites in ov3, **three** lie on the live path (scanned
programmatically over the whole ov3 image, not by eye):

| site | in | feeds | role |
|---|---|---|---|
| `0x021F0858` | slot3 `0x021F0820` | `0x02243FE0` | activation condition |
| `0x02208028` | resolver `0x02207EF4` | `0x02243FA8` | **guard only** — `cmp r0,r4 ; blt` → bail code `0x78` |
| **`0x022080D6`** | resolver `0x02207EF4` | **`0x0219C430`** | **THE PROMPT** |

`0x022080D6` is the one the handoff missed, and it is the one that matters:

```
022080D4  adds r0,r5,#0
022080D6  bl   0x02234E78      ; <- param
022080DA  adds r3,r0,#0        ; r3 = param   (4th arg)
022080DC  ldrh r2,[r5]         ; r2 = cid     (3rd arg)
022080DE  adds r0,r6,#0        ; r0 = side
022080E0  adds r1,r4,#0
022080E2  bl   0x0219C430      ; the card-selection UI
```

`0x0219C430` stashes them (`str r2,[sp] ; str r3,[sp,#4]`) and re-reads them at
`0x0219C47C: bl 0x02243FA8` — **that call builds the picker list**. So
`0x02208028` only decides whether the resolver errors out; `0x022080D6` decides
what the player is actually offered. Hooking the handoff's two sites would have
shipped a card that offers **Ninjitsu Art** on a Flip Summon *and passes
`verify()` while doing it*.

### ⚠️ CORRECTION 2 — hook INSIDE the provider; one site, not three

`patch_gates_of_dark_world.py:290` already ships this technique:
`L2_SEARCH_SITE = 0x02234E96` retargets a `bl 0x02022E14` *inside* the provider,
so every call site gets the right param at once. Its sibling **`0x02234E84`**
(the L1 lookup) is **unclaimed**, and `r5` still holds the descriptor there
(`0x02234E7A: adds r5,r0,#0`) — so the event code is `[r5,#4]`.

One hook replaces three and covers any call site I failed to enumerate. Given
that this session found a site the last one missed, that robustness is the point.

### Confirmed — the row rule (re-derived, agrees with the handoff)

`0x02243B9C(r0=cid, r1=param)` returns a criteria ROW INDEX =
`leftmost_row_for_cid + r4`:

```
02243BEC  ldr r1,=LIST_A ; adds r0,r5,#0 ; movs r2,#0x3b ; bl 0x02022E14
02243BF6  cmp r0,#0   ; beq  <LIST B test @0x02243C02>
02243BFA  cmp r4,#0   ; beq  0x02243C00 -> 0x02243EEC (movs r4,#0)
02243BFE              b     0x02243EC6 -> movs r4,#1
02243EEC..0x02243F0A  walk back while rows[r6-1].cid == cid ; r2 = r6 + r4
```

Exactly **3 callers** ROM-wide: `0x02243FB6` (inside `0x02243FA8`),
`0x02243FEE` (inside `0x02243FE0`), `0x02244080`.

### Confirmed — a DATA-ONLY fix is impossible

`0x02234E78` is five membership-list arms then a per-cid switch defaulting to 0:

| arm | list | n | returns |
|---|---|---|---|
| L1 | `0x022710E2` | 17 | `desc[+0x0C]` |
| L2 | `0x02271104` | 28 | `1 << 0x1C` (**hooked by gates_of_dark_world**) |
| L3 | `0x022710B2` | 12 | `desc[+0x14]` |
| L4 | `0x0227109C` | 11 | `desc[+0x16]` |
| L5 | `0x022710CA` | 12 | `desc[+0x18]` |

**No arm returns the event code**, and **every member of all five lists is a real
card — 0 phantoms in 80 entries** (checked against `card_prop.bin`, 4305 cids).
So no list can be repurposed the way set code `0x2A` was for C1, and no
descriptor field substitutes for the event code. Code is required. (This also
explains *why* GDW hooked the L2 search instead of inserting a row: same
constraint.)

### Confirmed — data slots, re-verified directly rather than inherited

* LIST A `0x0227134C` (59): the ONLY members owning zero criteria rows are
  `0x0D7A` (spent by snoww) and **`0x0D81`** (free). `0x13E7` is in neither
  LIST A nor the criteria table.
* c8 `0x0228F580` (0x0C) contains phantom `0x1A9F`; c9 `0x0228F63A` (0x1F)
  contains `0x0E12 0x167C 0x176C 0x1ABE 0x1ABF`.

### Ruled out — hosting the stub in ov3

Stub floors at ~26 B. Free ov3 dead-code runs, computed from
`OV3_DEAD_BLOCKS` vs `OV3_CLAIMS` (74 B total, all fragments):

| run | free |
|---|---|
| `0x0225F2A8` | 22 |
| `0x021B54FC` | 16 |
| `0x021B58D0` | 12 |
| `0x021B5AAA` | 10 |
| `0x021B5840` | 8 |
| `0x021B5900` | 4 |
| `0x021B5938` | 2 |

**No run holds 26 B**, and no reusable literal word (`0x02022E14/15`, `0x13E7`,
`0x02234E79`) exists in the PC-relative window of any of the four largest runs —
scanned, zero hits. Splitting across `0x021B54FC`+`0x021B58D0` fits with exactly
0 B slack.

**USER DECISION 2026-08-30: host in ov5, accept that puzzles break.** The cost is
specific and worth restating: because the hook is inside the shared provider, a
puzzle will **crash on the first search by any card**, not merely lose Hanzo.
`mem.ov3_resident_all_modes` measured ov5 100% resident in normal/turbo/tag/
tag-turbo and only evicted in the puzzle, so the blast radius is puzzles alone.
Reversing it later = relocating this one stub into 26 B of ov3, nothing else.

### The stub (PART J)

Hooked at `0x02234E84`. Entry: `r0`=cid, `r1`=L1 base, `r2`=0x11, `r5`=desc,
`lr`=`0x02234E89`.

```
    ldr  r3,=0x13E7
    cmp  r0,r3
    bne  native            ; not ours -> stock behaviour byte for byte
    ldrb r3,[r5,#4]        ; event code: 7 Normal / 8 Flip / 9 Special
    cmp  r3,#8
    blt  native            ; 7 and below -> row 0 = C1
    cmp  r3,#9
    bgt  native            ; above 9 -> row 0, fail safe
    movs r0,#1             ; Flip/Special: param != 0 -> row 1 = C2
    add  sp,#4             ; unwind the provider's push {r3,r4,r5,r6,r7,lr}
    pop  {r4,r5,r6,r7,pc}  ; return 1 to the provider's CALLER
native:
    ldr  r3,=0x02022E15
    bx   r3
```

Taking `native` for event 7 is correct *and* free: `0x13E7` is in none of the
five provider lists, so the search misses, the switch defaults, and the provider
returns 0 → row 0 → C1. The unwind is needed because L1's "found" arm returns
`desc[+0x0C]`, which we do not want. ⚠️ `desc[+0x0C]` is a packed ref
`(inst_idx<<1)|side` and CAN be 0, so the tempting "just report found" shortcut
would silently fall back to row 0 for one board position — do not use it.

---

## Next Experiment — C2 (2026-08-30a handoff — SUPERSEDED, see corrections above)

Continuation prompt: **`PROMPT_hanzo_clause2.md`**. Nothing is built for C2.

The trigger half is de-risked (same list-insert route, into `0x0228F580` code 8
and `0x0228F63A` code 9). The remaining problem was row selection, and it is now
solved on paper — every address below was **PROVEN by disassembly this session**:

* **The row rule.** `dispatch.two_row_criteria_is_list_b_plus_l2` +
  `dispatch.list_a_free_slots_and_list_b_none`: LIST A `0x0227134C`
  (59 entries, count immediate `movs r2,#0x3B` @`0x02243BF0`) gives
  `row = (param != 0) ? 1 : 0`, and the offset is applied as
  **leftmost-row-for-this-cid + r4**, so C2's row must sit **immediately after**
  C1's.
* **LIST A still has exactly one free slot: `0x0D81` "Speed Spell - Stardust
  Shimmer"** — a member owning **zero** criteria rows, so its membership is
  vestigial and it can be dropped count-neutrally. Verified this session: it is
  in the list, `rows.count(0x0D81) == 0`, and it is **unclaimed in
  `otn_enhanced/docs/engine/allocations.yaml`**. ⚠️ The other free slot `0x0D7A` is **already
  spent by `snoww`** (ledger line 796) — do not plan on it.
* **`param` comes from the provider `0x02234E78`, and BOTH steps this card uses
  call it with the descriptor live in `r5`:**
  * resolver `0x02207EF4` @**`0x02208028`**:
    `adds r0,r5,#0 ; bl 0x02234E78 ; adds r2,r0,#0 ; ldrh r1,[r5]`
  * slot3 `0x021F0820` @**`0x021F0858`**: byte-for-byte the same shape.
  Both are **unclaimed** (Snoww hijacked a different one of the 60 sites,
  `0x02235610`).
* **The event code is readable there.** `dispatch.cls_table_selector`: the
  descriptor is `{+0x00 u16 cid, +0x04 u8 event code, +0x05 u8 selector, ...}`,
  and `r5` IS the descriptor at both sites — so `ldrb rX,[r5,#4]` yields 7
  (Normal) / 8 (Flip) / 9 (Special).

**So the C2 stub is: `return (cid == 0x13E7) ? (desc[+4] != 7) : provider(desc)`**
— which routes Normal Summon to row 0 (Ninjitsu Art, C1) and Flip/Special to
row 1 (Ninja, C2), off one shared stub hooked at both call sites.

⚠️⚠️ **HOST THE STUB IN THE ov3 CAVE, NOT ov5.** `0x02208028` and `0x021F0858`
are shared fall-throughs on paths every searcher card takes. `stat.ov3_dead_arm_pool`
warns explicitly: never bl-hijack a shared fall-through into ov5, because a
puzzle loads overlay 41 over ov5 and the branch lands in ov41's data → freeze.
`check_allocations` reports **74 B still free** in the ov3 dead-code pool, which
is ample for this stub. It also keeps the card puzzle-safe, which C1 currently is.

## Next session — C2

C2's row is `{0x13E7, aux 0x0006, 0x0223CAF5, word 0x00000022}` — the 3DS row and
Machina Gearframe's row agree byte-for-byte. Trigger: insert `0x13E7` into the
code-8 list `0x0228F580` (phantom `0x1A9F`) and the code-9 list `0x0228F63A`
(five phantoms). **The hard part is row selection**: one cid gets one cls1 record
and the resolver reads criteria row 0 by default, so C2 needs a second row
reached by the row-offset mechanism (`otn-criteria-row-offset-mechanism`, the
Dark Simorgh hook at `0x02243BEC`) or the LIST B route Gates of Dark World used,
discriminating on the event code (7 vs 8/9) in the descriptor.
