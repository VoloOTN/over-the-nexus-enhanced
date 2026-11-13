# Scrap Archfiend — findings (live)

Session 2026-09-07. Card is an **effectless Synchro**: the whole card is the
chassis (identity + summon procedure). No effect clauses exist to implement.

## Confirmed (this session)

- **Printed text** (`scratch/ygoprodeck_cache.json`, grepped — not recall):
  `Scrap Archfiend`, Synchro Monster / EARTH / Fiend / **Level 7** / **2700** /
  **1800**, desc = `1 Tuner + 1 or more non-Tuner monsters` **and nothing else**.
  Cross-checked that the cache is not truncating: Scrap Dragon, T.G. Hyper
  Librarian and Shooting Quasar all carry their full effect paragraphs in the
  same field.
- **The card is NOT in the ROM.** English name-blob sweep of all 4305 card_prop
  records: 25 cards match `scrap`, none is Scrap Archfiend. (The rest of the
  archetype ships: Scrap Dragon 0x230E, Twin Dragon 0x23A1, Atomic 0x2476,
  Chimera 0x22F6, Golem 0x22FA, Beast 0x22F8, Goblin 0x22F7, Orthros 0x24DE, …)
- **KB is healthy**: `verify_knowledge` = 437 facts, 399 PASS, **0 FAIL**,
  38 UNVERIFIED. Oracles arm9/ov3/ov5 all present.
- **Fusion → Synchro conversion is an in-game-confirmed, data-only recipe**
  (`patch_accel_synchron`, user-confirmed 2026-09-03, all eight oracles, first
  test). Three files: card_prop card_type (reference-record copy, never a field
  flip), card_genre category bits, and the donor's fusion recipe row.
- **Reference record for an effectless Synchro (card_type 35)**: only two exist —
  **Gaia Knight, the Force of Earth 0x1E11** (idx 2837, Lv6 2600/800, genre
  `0x0000001000200000` = bits {21, 36}) and Naturia Leodrake 0x1FB7 (genre
  `0x0000021200200000`, carries extra keyword bits). **Gaia Knight is the clean
  reference** — bits 21/36 exactly, nothing else.
- **Donor candidates.** All effectless Fusion monsters (card_type 5) at Level 6+
  whose name slot is >= 15 B (`Scrap Archfiend`) in **all eight** languages:

  | cid | idx | stats | name floor | desc floor | donor_scan |
  |---|---|---|---|---|---|
  | 0x13C6 Humanoid Worm Drake | 830 | Lv7 WATER Aqua 2200/2000 | **19** | 29 | own fusion row A[57] only |
  | 0x126F Meteor B. Dragon | 559 | Lv8 FIRE Dragon 3500/2000 | 16 | 34 | own fusion row A[52] only |
  | 0x107F B. Skull Dragon | 360 | Lv9 DARK Dragon 3200/2500 | 15 | 30 | own row + 6 ambiguous ARM9 hits |
  | 0x11A3 Bracchio-raidus | 489 | Lv6 WATER Dino 2200/2000 | 15 | 37 | **already claimed by patch_accel_synchron** |

- **0x13C6 Humanoid Worm Drake vetted as the donor:**
  - donor_scan VERDICT ENTANGLED by exactly **one** binding occurrence —
    its own **fusion recipe A[57] @ov3:0x02270D5C** (`result 0x13C6,
    m1 0x13C5 Worm Drake, m2 0x13C4 Humanoid Slime, m3 0`). Result column only
    (+0x0), so it is **not a material of any other fusion**.
  - 1 further u16 hit at `ov3:0x0217EAB8`, classified code-region /
    instruction encoding, not a table key.
  - **Zero CPU decks** name it (`data/over_the_nexus/working/deck.json`, 0 hits
    over all decks; same sweep is 0 for the other two candidates).
  - card_genre idx 830 = `0x0000000020200000` = bits **{21, 29}** — textbook
    Fusion tagging, the exact shape the accel recipe rewrites to {21, 36}.
  - Absent from **all three** Synchro per-cid exception lists, so the generic
    "1 Tuner + 1+ non-Tuner" rule applies with nothing to insert:
    - LIST_A "exact" 0x02275AB8 (16 u16) — absent → "N or more"
    - min-3-materials 0x02275AD8 (21 u16) — absent → min 2
    - 2-leading-Tuners 0x02248280 (2 u16 = 0x4904/0x4288) — absent → 1 Tuner
  - Name budget 19 B >= 15 B in every language → the name lands in **all eight**,
    no language left showing the donor's name.

- **Description ladder fits all eight languages** (donor desc floors
  e29 f38 g38 i32 s38 j48 k35 r48):
  - 38 B `1 Tuner + 1 or more non-Tuner monsters` → f g s j r (the printed text)
  - 31 B `1 Tuner + 1+ non-Tuner monsters` → i k
  - 23 B `1 Tuner + 1+ non-Tuners` → e
  So no language keeps the donor's Fusion flavour text.

### Set-code tables located (this session) — the whole thunk table enumerated

The has_set_code pointer table `0x0209D0D8` was walked for all 0x70 indices.
Each standard thunk is a fixed **16-byte** record:

    +0  ldr  r1,[pc,#4]     ; r1 = list base   (u32 literal at +8)
    +2  ldr  r3,[pc,#8]     ; r3 = 0x02022E15  (u32 literal at +12, shared bsearch)
    +4  movs r2,#COUNT
    +6  bx   r3

so base = u32(thunk&~1 + 8), count = the `movs r2,#N` immediate, and any thunk
whose +12 literal is not `0x02022E15` is non-standard (17 of the 112 are).

- **Set code 0x01 = "Archfiend"** — thunk `0x02023761`, list **`0x0209CF90`**,
  **n=42**, sorted-unique. 8 phantoms: 0x10AB, 0x12B5, 0x1441, 0x14B7, 0x168C,
  **0x23F2**, 0x243D, 0x252B.
- **Set code 0x57 = "Scrap"** — thunk `0x02023EE5`, list **`0x0209CC70`**,
  **n=25**, sorted-unique. 5 phantoms: **0x23F2**, 0x2441, 0x24ED, 0x251F.

### *** cid 0x23F2 IS Scrap Archfiend *** (3DS second source of truth)

`0x23F2` is the **only phantom present in BOTH lists** — i.e. Konami reserved a
cid that is simultaneously a "Scrap" and an "Archfiend" card and then never
shipped it on NDS. Confirmed against `3ds_extract`
(`romfs/duel/card/CARD_Prop.bin` record 4339, name via `CARD_Indx_E`/`CARD_Name_E`):

    cid 0x23F2  ->  'Scrap Archfiend'

Same sweep also resolved the other reserved phantoms: 0x2441 Scrap Mind Reader,
0x24ED Scrap Breaker, 0x251F Scrap Kong, 0x243D Archfiend Empress, 0x252B
Overmind Archfiend, 0x10AB Archfiend Mirror, 0x12B5 Beast of Talwar, 0x14B7
Lesser Fiend, 0x168C Vilepawn Archfiend.

**So the count-neutral drop is semantically exact**: 0x23F2 leaves each list and
the donor 0x13C6 takes its place, in both. Neither cid is in `PHANTOM_CLAIMS`
(grep: zero hits for 0x23F2 and 0x13C6 anywhere in `ygo_tools/`, `scratch/*.py`
or `otn_enhanced/docs/engine/*.yaml`).

## Ruled Out

- **0x11A3 Bracchio-raidus** — claimed by `patch_accel_synchron` (unshipped, but
  claimed; do not double-book).
- **0x107F B. Skull Dragon** — 6 ambiguous ARM9 data-region hits and 16
  code-region hits; the other candidates are cleaner, and it is a recognisable
  card the user may play.
- **`cards_text.json` / recalled text** — not consulted; ygoprodeck cache only.

## Open Questions

- **RESOLVED** — the user asked for both tables and they are located above.
  Both memberships are in scope. Per the accel precedent an Extra-Deck monster
  is unreachable by every Deck/GY-searching consumer, so the in-game oracle for
  these two edits is the **deck-editor archetype filter** (has_set_code readers
  0x0202A358 / 0x0202A3F0), not a duel-time search.

## Built (2026-09-07)

`otn_enhanced/cards/scrap_archfiend.py` +
`_build_scrap_archfiend.py`. Pure data patch — no injected Thumb, no ov5 cave
slot, no cls record, no criteria row.

    data/over_the_nexus/working/rom_scrap_archfiend.nds

STAGE 1 `verify()` **PASS** (17/17 checks). STAGE 2 static composition check vs
`patch_accel_synchron` (the other Fusion→Synchro conversion) **PASS** for both
modules on the stacked ROM. `check_allocations` clean.

Parts: **A1** card_prop reference-record copy from Gaia Knight 0x1E11 + stats;
**B** card_genre[830] 0x…20200000 → 0x…10200000; **C** name/desc ladder, all 8
languages; **D** fusion A[57] materials → 0x3FFF/0x3FFF; **E** Scrap 0x57 list;
**F** Archfiend 0x01 list.

## KB contributions (this session)

Five new VERIFIED facts, `author_facts --check` → 442 facts, 404 PASS, 0 FAIL:
`setcode.thunk_record_shape`, `setcode.scrap_table`,
`setcode.archfiend_table`, `setcode.phantom_23f2_is_scrap_archfiend`,
`carddata.effectless_synchro_reference`.

## Next Experiment

None pending — no unproven hook site, because there is no injected code. The
next step is the **in-game oracle** in `_build_scrap_archfiend.py`'s docstring
(8 checks), which only the user can run.

## *** IN-GAME CONFIRMED BY THE USER 2026-09-07, ALL EIGHT ORACLES ***

On `rom_scrap_archfiend.nds` sha256
`f11b9823a13129af9467d8dc2711be40a4d2a5c46e4110a7d1bae13aced14f97`. Every check
in `_build_scrap_archfiend.py`'s oracle list answered **"Confirmed"** verbatim,
followed by **"Ship it"**.

| # | Oracle | Result |
|---|---|---|
| 1 | Deck editor: "Scrap Archfiend", Lv7 EARTH Fiend Synchro 2700/1800, Synchro frame, **Extra Deck** | **CONFIRMED** |
| 2 | Polymerization does not offer it; Worm Drake + Humanoid Slime fuse into nothing | **CONFIRMED** |
| 3 | Synchro Summons on 1 Tuner + non-Tuners totalling Level 7 (positive control) | **CONFIRMED** |
| 4 | Also summons on 1 Tuner + **two** non-Tuners totalling 7 — proves LIST_A absence gave the "1+" form | **CONFIRMED** |
| 5 | Materials not totalling 7 are refused (negative control) | **CONFIRMED** |
| 6 | **Not** usable as a Tuner (genre bit 35 left clear); usable as a non-Tuner material | **CONFIRMED** |
| 7 | Appears under related cards of a "Scrap" card **and** an "Archfiend" card | **CONFIRMED** |
| 8 | No effects fire — the card has none | **CONFIRMED** |

⚠️ **What check 7 does and does not prove.** It proves both set-code table edits
took and that the engine reads this cid as a "Scrap" and an "Archfiend". It does
**not** exercise a duel-time consumer, because none can reach an Extra Deck
monster: every consumer of set codes 0x57 and 0x01 searches the Deck or the GY.
Recorded so a later session does not mistake it for a duel-path confirmation.

**Second confirmation that an effectless FUSION monster converts into a working
SYNCHRO monster by data alone** — after Accel Synchron (2026-09-03), on a
different donor and a different reference record, first test again.

## Status

**SHIPPED 2026-09-07.** Wired into `apply_all_patches.PATCHES` (53 steps, ahead of
the always-last WiFi-timers step) and `_verify_all_patches.SHIPPED` in the same
edit. Chain preconditions re-checked against the previous chained image before
wiring: `0x23F2` still present in **both** set-code lists, fusion A[57] stock,
`card_prop[830]` still the stock effectless Fusion — no collision.

Chain rebuilt 2026-09-07 (old ROM moved to `rom_all_patches.PREV.nds` first).
**ALL 53 PATCHES APPLIED**, and the ARTIFACT itself asserted, not just the exit
code (`otn-chain-build-verify-artifact`):

    data/over_the_nexus/working/rom_all_patches.nds   129,538,184 B
    sha256 d502be892aed32dbcea31f70e8d303b7af2146104c13d0104103576d33d91f19

    Scrap     n=25  0x13C6 @1  0x23F2 gone  sorted
    Archfiend n=42  0x13C6 @8  0x23F2 gone  sorted
    fusion A[57] 0x13C6/0x3FFF/0x3FFF   A[38] 0x11A3/0x3FFF/0x3FFF (accel)
    fusion table A still a sorted 161
    card_prop[830] cid 0x13C6 ct35 Lv7 2700/1800 EARTH Fiend
    card_genre[830] 0x0000001000200000   name b'Scrap Archfiend'

`_verify_all_patches.py` over that ROM: **PASS 42, FAIL 0**, SKIP 2
(`patch_boggart_knight` / `patch_darksoul` have no `verify()` — pre-existing).
