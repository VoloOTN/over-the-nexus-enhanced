# White Dragon Ninja — findings (session 2026-09-01)

Printed text (`scratch/ygoprodeck_cache.json`, id 99212922) — LIGHT / Level 7 /
Dragon / Effect Monster / ATK 2700 / DEF 1200:

> Cannot be Special Summoned, except with a "Ninjitsu Art" card's effect.
> Spells/Traps you control cannot be destroyed by card effects.

Clause split (confirmed with the user 2026-09-01):

| clause | scope |
|---|---|
| **C0** identity — exists as LIGHT / Lv7 / Dragon / 2700 / 1200, findable by NAST's Deck search | **THIS SESSION** |
| **C1** "Cannot be Special Summoned, except with a Ninjitsu Art card's effect" | **DEFERRED** — no proven route; new lead below |
| **C2** "Spells/Traps you control cannot be destroyed by card effects" | **THIS SESSION** |

**STATUS 2026-09-01: C0 + C2 IN-GAME CONFIRMED BY USER 2026-09-01.**

What the user confirmed, and only this:

* **C0** — activated NA SuperTF and summoned White Drgn Ninja from the Deck
  (*"Activated NA SuperTF, and summoned White Drgn Ninja"*).
* **C2 round 2** — retested in game after the bit-18 fix and the protection
  **held across the turn boundary**, which is the exact case round 1 failed.

* **no over-reach into bouncing** — *"I and my opponent are able to bounce
  spells/traps while White Dragon Ninja is on the field"*. So the grant is
  DESTRUCTION-SCOPED, not "unaffected by card effects", even though `0x021B021C`
  is the general affect predicate. No `targets`-flag gating is needed, and the
  deviation risk flagged at build time is closed.

NOT yet reported back, so still unconfirmed — do not write these up as passing:

* negative control: the OPPONENT's Spells/Traps are still destroyable;
* negative control: YOUR MONSTERS are still destroyable by card effect.

**SHIPPED 2026-09-01** — wired into `apply_all_patches` at index 37 of 44 (after
Super-Transformation, before the card-art step) and added to
`_verify_all_patches.SHIPPED`. Combined ROM
`data/over_the_nexus/working/rom_all_patches.nds`, 129,529,992 bytes, sha256
`481654ed6b6268420b3fc6389da63d1ece5c5efff3a184301cd832cbff1a2ae3`. Sweep:
**33 PASS / 0 FAIL / 2 SKIP** (both skips are modules with no `verify()` of their
own, pre-existing). The always-last WiFi-timers step verifies PASS, which is what
proves the chain ran to completion.

⚠️ Process note worth keeping: the first sweep of this build ran WHILE the build
was still writing and reported 33 PASS on a mid-chain ROM, while `wifi_timers`
(the always-last step) reported FAIL. Same byte length, different sha256. The
final-step verify is the cheap tell — CLAUDE.md's "assert the final patch count
and ROM hash" exists for exactly this.

Round 1 of C2 FAILED in game and the diagnosis is below. Donor **Dunames Dark Witch
`0x12B2`** (user-approved).

Module `otn_enhanced/cards/white_dragon_ninja.py`
Build `.venv-1/Scripts/python.exe _build_wdn.py --text --art`
ROM `data/over_the_nexus/working/rom_wdn.nds`
sha256 `1832ba27cfcc463dcadf2069335f17ec2487179076ee5983131ffbd6faf8ded6`
(129,523,336 bytes; the chain is Hanzo → NAST → this card → card art)

`verify()` against the FINAL ROM: **White Dragon Ninja 21/21 PASS, Hanzo 46/46
PASS, Ninjitsu Art of Super-Transformation 26/26 PASS.** `check_allocations` OK
(154 ov5 slots, 130 phantom claims, no collisions, ledger in sync).
`author_facts --check`: 377 facts / 341 PASS / 0 FAIL / 36 UNVERIFIED.

⚠️ **NOT wired into `apply_all_patches`** and **not added to
`_verify_all_patches.SHIPPED`** — single-card ROM only until the user says ship.

### What was written

| part | where | what |
|---|---|---|
| A | `bin2.pac` `card_prop.bin` + `card_name_*`/`card_desc_*` × 8 | LIGHT / Lv7 / **Dragon** / 2700 / 1200 / Effect Monster; name `"White Drgn Ninja"` (16 B), desc `"Spells/Traps you control cannot be destroyed by card effects."` (61 B) — both in place in all 8 languages |
| B | ARM9 `0x0209C722` | Ninja set code 0x06: dropped Karakuri Ninja "Sazank" `0x238B`, inserted `0x12B2` at index 0. Count immediate `movs r2,#9` untouched, list still strictly sorted |
| C | ov3 `0x021B07F4` (4 B) | the S/T tail's first family-1 link retargeted to `CAVE_WDN_PROT` |
| C | ov5 `0x0239DD80` (124 B of 0x80) | the protection leaf (round 2) |
| D | `patch_card_art.py` | `CardArt(0x12B2, 'dragon_ninja', 'dragon_ninja')` enabled (art was already prepared) |

Nothing else: **no cls0–cls3 record, no criteria row, no effect-registry row, no
summon-list entry, no phantom drop.** The card is reachable by NAST purely
because its `card_prop.race` is now 1.

---

## Confirmed (proven this session)

### KB baseline

`verify_knowledge`: **372 facts / 336 PASS / 0 FAIL / 36 UNVERIFIED**, oracles
arm9+ov3+ov5 present. The KB is healthy; nothing worked around.

### White Dragon Ninja is NOT in the ROM

`scratch/cid_to_name.json` (4305 cids, `0xD48..0x24E8`) has no entry. Donor
required.

### C0 — what NAST's Deck search actually demands of a candidate

NAST's criteria row is `{cid 0x1255, aux 0xFFFF, handler CAVE_NAST_CRIT, word
0x00000002}` — aux `0xFFFF` means **no set-code filter**, and the row's level
field is zero. **All selectivity lives in the ov5 handler `CAVE_NAST_CRIT`**,
which carries the race whitelist `{1, 9, 5, 0}` (Dragon / Dinosaur / Sea
Serpent, `game_constants.ERA2_RACE_MAP`) and searches container `0x0A` = Deck.
The level cap is written into the stub's own pool word at `+0x50` at runtime by
the resolver's phase `0x80` as `(0x80 | (sum << 2)) << 16`, where `sum` is the
two sent monsters' **original** Levels via `0x0202ABD8`.

So a new candidate needs exactly:

1. `card_prop.race == 1` (Dragon)
2. card type MONSTER (row word `0x00000002`)
3. `card_prop.level <= ` the runtime sum, clamped 15
4. to be **in the Deck** (hand and GY are not searched)

**No criteria row, no registry edit, no ov5 change for the new card.** Being a
"Ninja" is irrelevant to this search.

⇒ White Dragon Ninja at Level 7 needs the two sent monsters' original Levels to
sum to ≥ 7. Hanzo is Level 4, so the opponent's monster must be **Level 3+**.

### Donor vetting — `0x12B2` Dunames Dark Witch

`donor_scan 0x12B2` → **CLEAN**, and — the part that matters — **zero ARM9
data-region hits**. The 11 reported hits are all ov3 instruction encodings.

- name slots e18 f30 g21 i21 s20 j24 k17 r24 → **floor 17**
- desc slots e100 f109 g99 i110 s108 j88 k96 r180 → **floor 88**
- Lv4 LIGHT Fairy 1800/1050, pack1 = 71 (obtainable)

`NEW_NAME = b"White Drgn Ninja"` is 16 B ≤ 17 and `NEW_DESC` is 61 B ≤ 88, so
both write **in place in all eight languages** — no append path (the confirmed
in-hand freeze) and no silently-skipped language.

No unclaimed clean Normal-Monster donor in the whole ROM has a name floor ≥ 18,
so the full 18-byte `"White Dragon Ninja"` was never available on any donor.

### ⭐ `donor_scan`'s "CLEAN" verdict does NOT clear an advisory ARM9 hit

`0x1E87` **Mist Valley Watcher** was the best candidate on slot budgets (name 16
/ desc 94) and `donor_scan` printed `VERDICT: CLEAN`. It also printed *"1 ARM9
data-region u16 hit — ambiguous"* at `0x0209C7D2`. Resolved it by walking the
`has_set_code` pointer table `0x0209D0D8`: that address is inside **set-code
list `0x0209C7CC` (index `0x37`, 11 entries) = the "Mist Valley" archetype** —
Thunderbird, Shaman, Soldier, **Watcher**, Windmaster, Baby Roc, Executor,
Falcon, Apex Avian, Thunder Lord, Divine Wind of Mist Valley.

Using it would have made White Dragon Ninja a **"Mist Valley" monster**. This is
exactly CLAUDE.md donor rule (c), and the verdict line alone would have missed
it. **Rejected the donor.**

### C2 — the S/T destruction-protection site (disassembled this session)

`0x021B021C` is the "may this card effect affect this card" predicate
(`rider.affect_predicate_protection_link`, VERIFIED). It **splits by slot**:

```
021B059C  cmp  r5,#4
021B059E  ble  0x021B05A2      ; slots 0..4   = MONSTER zones -> long body
021B05A0  b    0x021B07EA      ; slots 5..0xA = S/T + FIELD   -> short tail
```

⇒ Safe Zone's link `0x021B05CC` and Dreadmaster's `0x021B05FA` are
**monster-zone-only** and unreachable for a Spell/Trap. Azure-Eyes' link
`0x021B0592` sits *before* the split, so it is reached for S/T too — but it is
already claimed.

The S/T tail, verbatim:

```
021B07EA  ldr  r5,[pc,#0x38]   ; r5 = 0x0D6C  (pool word @0x021B0824)
021B07EC  adds r0,r6,#0        ; r0 = the TARGET's controller
021B07EE  movs r1,#0x0B        ; pseudo-slot 0x0B
021B07F0  adds r2,r5,#0
021B07F2  movs r4,#0x0B
021B07F4  bl   0x021A1430      ; family-1 rider lookup   <-- OUR HOOK
021B07F8  cmp  r0,#0
021B07FA  beq  0x021B07FE
021B07FC  b    0x021B0296      ; nonzero => PROTECTED
021B07FE  ldr  r0,[sp,#4]      ; the `targets` flag
021B0800  cmp  r0,#0
021B0802  beq  0x021B081E
021B0804  ldrb r1,[r7,#2]      ; the ACTING card's side
021B0806  movs r0,#1
021B0808  subs r0,r0,r1
021B080A  cmp  r6,r0           ; target side == opponent of acting side?
021B080C  bne  0x021B081E
021B080E  adds r0,r6,#0
021B0810  adds r1,r4,#0
021B0812  adds r2,r5,#2        ; key 0x0D6E
021B0814  bl   0x021A1430
021B0818  cmp  r0,#0
021B081A  beq  0x021B081E
021B081C  b    0x021B0296
021B081E  movs r0,#1           ; AFFECTABLE
021B0820  add  sp,#0x40
021B0822  pop  {r3,r4,r5,r6,r7,pc}
```

**`r6` is the target's controller**, proven by `0x021B0804-0x021B080A`
(`1 - actingSide` compared against `r6`). `r4` and `r5` are live after the call
at `0x021B0810`/`0x021B0812`, so the stub must preserve them.

`0x021B07F4` is chosen over `0x021B0814` because the second link is behind the
opponent-side test, i.e. "your opponent's card effects only"; the printed text
says *all* card effects.

### `0x021AC5A8(r0 = side, r1 = cid) -> count`

Re-derived from its own prologue rather than taken on trust:

```
021AC5A8  push {r1,r2,r3,r4,r5,r6,r7,lr}
021AC5AA  adds r5,r0,#0        ; side
021AC5AC  str  r1,[sp]         ; cid, stashed
021AC5C4  adds r0,r5,#0
021AC5C6  adds r1,r4,#0        ; slot
021AC5C8  bl   0x021A36EC      ; (side, slot) -> cid
021AC5CC  ldr  r1,[sp]
021AC5CE  cmp  r0,r1           ; == the wanted cid?
```

= **side-scoped face-up presence count**. Its native use at `0x021B05FA`
(Dreadmaster `0x1A05`) is the exact call shape our stub clones:
`ldr r1,=<cid> ; adds r0,r6,#0 ; bl 0x021AC5A8 ; cmp r0,#0 ; beq skip ;
b 0x021B0296`.

### ⭐ `0x020231C8` IS A 4-WAY SUMMON-RESTRICTION CLASSIFIER (new)

Found by chasing the only literal reference to `0x0209BE2C` (pool word
`0x02023218`). The function at **`0x020231C8(r0 = cid)`** runs four sorted
cid-list searches through the generic `0x02022E14` and returns a class code:

| class | list | count immediate | n | population |
|---|---|---|---|---|
| 1 | `0x0209BE2C` | `movs r2,#0x37` @`0x020231CC` | 55 | Spirits, Toons, the banish-cost Chaos monsters, Gate Guardian, Backup Warrior, Monoceros, D.D. Unicorn Knight, Scrap Orthros, Card Breaker, Synchro Magnet |
| 2 | `0x0209BE9C` | `movs r2,#0x39` @`0x020231E0` | 57 | full nomi — Judgment Dragon, Dark Armed Dragon, Uria/Hamon/Raviel, the Malefics, the Meklord Emperors, D-HERO Dogma/Plasma, Rainbow Dragon, Faultroll |
| **3** | **`0x0209BA12`** | `movs r2,#3` @`0x020231F2` | **3** | **Harpie Lady Sisters `0x0FE5`, Wall Shadow `0x1117`, phantom `0x1534`** |
| 4 | `0x0209BC14` | `movs r2,#0x1D` @`0x02023206` | 29 | semi-nomi — the LV monsters, the /Assault Mode monsters, Yubel-TI/TUN, Vennominaga, Exodia Necross |
| 0 | — | — | — | no restriction |

**Class 3 is "Special Summon ONLY with one specific named card"** — Harpie Lady
Sisters (Elegant Egotist) and Wall Shadow (Magical Labyrinth). That is *exactly*
White Dragon Ninja's printed shape, **and the list has a free phantom slot
(`0x1534`, no `card_prop` row).**

Callers of `0x020231C8`, both in ARM9:

- **`0x020232DA`**, inside `0x020232AC` — returns 1 iff class > 0 (a jump table
  on `0x02022D70(cid)` handles types ≤ 0xB first).
- **`0x020233F4`** — returns 0 for classes **2 and 4**, 1 otherwise. Consistent
  with 2/4 being the two "Cannot be Normal Summoned/Set" classes.

And **`0x020232AC` is called from `0x021BA6DC`** — inside `0x021BA69C`, the KB's
documented `dispatch.summon_from_zone_primitive` ("may this card be Special
Summoned from zone Z") — plus 15 other ov3 sites including `0x021C22F6`,
`0x021C2472`, `0x021C24B2`.

⇒ **This is the summon-restriction gate.** It supersedes
`notes/darkflare-dragon-findings.md:201`, which saw list `0x0209BE2C` alone,
called it "50/55 nomi-by-text" with unexplained false negatives, and marked it
**UNRESOLVED**. The false negatives are explained: the other three lists.

### Set-code tables have no slack

`0x0209C722` ("Ninja", 9 entries) ends at `0x0209C734`, where the next list
begins (`0x189E 0x189F 0x18A0 …`). `0x0209C5D2` ("Ninjitsu Art", 4) ends at
`0x0209C5DA`, where `0x1ECD …` begins. **Both are packed with no padding**, so
membership is always a count-neutral swap unless the list is relocated.

The "Ninja" list has **no phantom** (Hanzo already spent Armed Ninja `0x117B`),
so joining it costs a real card. Karakuri Ninja "Sazank" `0x238B` was chosen by
the user — verified still present in the **Karakuri** set-code list
`0x0209CC16[4]`, so it keeps all Karakuri support and loses only "Ninja" status.

---

### ⭐ ROUND 1 FAILED IN-GAME, AND WHY — the bit-18 gate

**User report (2026-09-01):** *"See .ml2, the protection effect is active and the
set MST cannot destroy the NA Super TF. In .ml3, the protection effect is gone
and the set MST can destroy NA Super TF."* — i.e. the protection worked and then
**expired at the turn boundary**.

Diagnosed entirely offline from the two savestates; **no duel was spent.**

The two boards are the same board one turn apart. `rom_wdn.ml2` vs `rom_wdn.ml3`,
side 0:

| | ml2 (protected) | ml3 (destroyed) |
|---|---|---|
| monster slot 2 card word | `0x028012B2` | `0x028012B2` |
| monster slot 2 **flags** `[+0x44]` | **`0x00448110`** | **`0x00008110`** |
| `0x021A36EC(0, 2)` | `0x12B2` | `0x12B2` |
| `0x021A32B4(0, 2)` | present | present |
| bit 26 / per-slot mask bit | 0 / 0 | 0 / 0 |
| ov5 stub resident & byte-exact | yes | yes |
| ov3 hook -> `CAVE_WDN_PROT` | yes | yes |

Only **bits 18 and 22** were lost. The opponent's two Set Spell/Traps also lost
bit 20 in the same step, which is what confirms a turn boundary passed.

**Root cause: `0x021AC5A8` carries a flag test its 201-caller sibling
`0x021AC204` does not.**

```
0x021AC5F2  lsrs r1,r0,#0x12     ; >> 18
0x021AC5F4  movs r0,#1
0x021AC5F6  tst  r0,r1
0x021AC5F8  beq  next            ; BIT 18 CLEAR -> this copy is NOT counted
```

`0x021AC204` tests only bit 26 and the per-slot mask. So `0x021AC5A8` is **not**
"does this side control X face-up" — bit 18 is clear on **48 of the 73** face-up
field monsters in the savestate corpus, and it is not stable across turns.
`0x021AC5A8` has only **three** callers (`0x02198530`, `0x02199730`, and
Dreadmaster's leaf `0x021B05FE`), two of them inside the battle chains.

**Fix (round 2):** the stub no longer calls `0x021AC5A8`. It inlines
`0x021AC204`'s own per-slot acceptance test — cid via `0x021A36EC`, then
`0x021A32B4`, then bit 26 of `[slot+0x44]` clear, then the `0x0229C314` per-slot
mask bit clear — over monster slots 0..4 of the **one** side in `r6`. 124 B,
`push {r4,lr}` / `pop {r4,pc}`, so `r5`/`r6`/`r7` are never written and the
caller's second link and its `ldrb r1,[r7,#2]` are untouched.

**A/B, emulated on the failing board itself** (`scratch/thumbemu.py` over
`rom_wdn.ml3`, entry state `r4=0x0B, r5=0x0D6C, r6=side`):

| stub | side 0 (yours) | side 1 (opponent's) |
|---|---|---|
| round 1, `0x021AC5A8` | **0 — not protected** (reproduces the bug) | 0 |
| round 2, inline scan | **1 — PROTECTED** | **0 — destroyable (correct)** |

and `r4`/`r5`/`r6`/`r7` come back as `0x0B` / `0x0D6C` / side / 0 in both cases.

⚠️ `ml2` cannot be emulated end-to-end — `0x021A32B4` on that board reaches an
ARM-mode `BLX` at `0x02029BA2 -> 0x020989A4` that `thumbemu` does not implement.
It is the case that already worked in-game and its bit 18 is set, so both stubs
accept it; the emulator limit is worth knowing for the next session.

### KB facts contributed this session (all VERIFIED, all passing)

- `dispatch.summon_restriction_classifier` (`cards.yaml`) — the four-way
  classifier above. Supersedes `notes/darkflare-dragon-findings.md:201`, which
  now carries a pointer back to it.
- `rider.affect_predicate_zone_split` (`continuous_riders.yaml`) — the
  `cmp r5,#4` split, and which existing hook sites it makes monster-zone-only.
- `rider.st_tail_protection_links` (`continuous_riders.yaml`) — the two S/T-tail
  links, `r6` = the target's controller, and the live-register warning.
- `dispatch.side_scoped_face_up_count` (`effect_dispatch_tables.yaml`) — ⚠️
  **CORRECTED in the same session it was authored**: it now says outright that
  `0x021AC5A8` is NOT the "do you control an X" primitive, documents the
  bit-18 gate and the measured turn-boundary expiry, and points at
  `0x021AC204`'s test plus the geometry needed to clone it per-side.
- `donor.advisory_hits_must_be_resolved` (`donor_card_technique.yaml`) — the
  Mist Valley trap, with the worked resolution.

---

## Ruled Out

### ⭐ CLAUSE 1 VIA THE SUMMON-RESTRICTION CLASSIFIER — RULED OUT (measured 2026-09-01)

The lead was real but it is a dead end, and the reason is worth banking so no
future session pays for it again.

`0x021BA69C` consumes the classifier **unconditionally**:

```
021BA6DA  adds r0,r4,#0        ; r4 = the cid
021BA6DC  bl   0x020232AC      ; -> 1 iff the cid has ANY restriction class
021BA6E0  cmp  r0,#0
021BA6E2  beq  0x021BA6E6      ; class 0 -> carry on
021BA6E4  b    0x021BA6CA      ; class > 0 -> `movs r0,#0` = REJECT
```

There is **no "who is summoning" test at that site**. The `[sp+0x2C]` caller
flag and the `0x021AC204` field check at `0x021BA6B0` bypass only the *separate*
`0x021B9E28` test earlier in the chain — never the classifier.

**And the Deck walker consults it per candidate.** `0x0223BC3C` is the very
function NAST's criteria handler calls (`DECK_WALKER` in
`patch_ninjitsu_art_super_transformation.build_crit_stub`). It has one
`push {r3,r4,r5,r6,r7,lr}` at `0x0223BC3C` and no `pop {...,pc}` before
`0x0223BE20`, so both of these are inside it:

```
0223BD7A  bl   0x021BA69C
0223BD7E  cmp  r0,#0
0223BD80  bne  0x0223BDA8      ; legal -> keep the candidate
0223BDA4  movs r0,#0
0223BDA6  str  r0,[sp,#0x34]   ; ILLEGAL -> mark it unsummonable
```
(and again at `0x0223BD9C`; the HAND walker's neighbourhood does the same at
`0x0223C0D0` / `0x0223C0F4`).

⇒ **Putting `0x12B2` in class 3 would delete it from NAST's own Deck-search
candidate list.** The card's only summon route is that search, so the clause
would make the card unsummonable — clause 1 via this table is self-defeating.
Exactly the risk named as the reason not to build it; now measured, not guessed.

What the class actually is, then: it only ever **subtracts** from the generic
paths. The "allowed summoner" pairing (Harpie Lady Sisters ← Elegant Egotist
`0x10E4`, Wall Shadow ← Magical Labyrinth `0x1232` — both cards ship in this
ROM) lives somewhere else and was not found. Nomi cards reach the field through
the hand-SS tree + summon-procedure registry `0x0228F158`, which never calls
`0x021BA684`.

**Clause 1 is therefore closed as a KNOWN DEVIATION**, with a proven reason
rather than an unknown mechanism. The printed text on the card already omits it,
so nothing in-game claims a restriction that is not enforced.



- **Donor Mist Valley Watcher `0x1E87`** — in the Mist Valley set-code list
  `0x0209C7CC` (see above). Rejected on CLAUDE.md donor rule (c).
- **Donor Gene-Warped Warwolf `0x1B30`** — the only clean unclaimed donor whose
  desc floor (137) fits the *full* 133-byte printed text, but its name floor is
  13, well under any usable abbreviation, and its 2000 ATK makes it the most
  playable vanilla in the pool.
- **Hooking `0x021B05CC` or `0x021B05FA` for C2** — both are on the monster-zone
  side of the `cmp r5,#4` split at `0x021B059C`; a Spell/Trap target never
  reaches them.
- **Hooking `0x021B0592` for C2** — correct zone behaviour, but claimed by
  `patch_azure_eyes` (`CAVE_AZURE_PROT = 0x0239D090`).
- **Growing the "Ninja" set-code list in place** — the list is packed against
  its neighbour at `0x0209C734`.
- **The rider/node system for C2** — HOWTO §7 prohibits blind writes into the
  shared live pool, and riders attach per-zone (one per S/T zone). A static
  predicate leaf is the ROM's own idiom here: Imperial Custom `0x20A5` and Field
  Barrier `0x1BD7` are both implemented *only* as leaves in `0x021B021C`.

---

## Open Questions

1. **Does `0x021B021C` gate more than destruction?** It is the general "may this
   effect affect this card" predicate and takes a `targets` flag. If C2's leaf
   also makes your Spells/Traps immune to bouncing or targeting, that is
   over-reach and a bug until the user says otherwise. Watch for it in the
   in-game test.
2. **C1: does NAST's own Deck Special Summon consult `0x021BA684` /
   `0x020232AC`?** If it does, putting the card in any restriction class would
   block its *only* summon route and C1 is self-defeating. If it does not, a
   2-byte count-neutral insert over phantom `0x1534` in class 3 may be the whole
   clause.
3. What distinguishes class 1 from class 2 functionally? Both hold "cannot be
   Normal Summoned" cards, yet only 2 and 4 are rejected by `0x020233F4`.

---

## Next Experiment

For open question 2, offline and duel-free: run `scratch/thumbemu.py` over a
savestate taken with a NAST activation pending, and trace whether the Deck-search
candidate enumeration (`0x02243FA8` → `CAVE_NAST_CRIT` → `0x0223BC3C`) or the
summon commit reaches `0x021BA684`. Expected deltas:

- **reached** ⇒ class membership would remove the card from NAST's own list ⇒
  C1 via this table is dead; look instead at whether the classifier's caller can
  be scoped to the summoning card's identity.
- **not reached** ⇒ insert `0x12B2` over phantom `0x1534` in `0x0209BA12`
  (2 bytes, count immediate `movs r2,#3` @`0x020231F2` untouched, list stays
  sorted: `0x0FE5, 0x1117, 0x12B2` — note `0x12B2` sorts LAST, replacing
  `0x1534`) and test in-game that Monster Reborn is refused while NAST still
  summons.
