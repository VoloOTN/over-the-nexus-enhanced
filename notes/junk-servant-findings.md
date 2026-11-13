# Junk Servant — findings (session 2026-09-01)

Card: **Junk Servant**, ygoprodeck id 78922939, EARTH / Lv4 / Warrior / Effect /
1500 ATK / 1000 DEF.

> "If you control a \"Junk\" monster, you can Special Summon this card (from your
> hand)."

One clause, the whole card: a **continuous** condition on the hand-Special-Summon
eligibility offer. Free — no cost, no tribute, no once-per-turn. No shipped card
to regress.

STATUS: **IN-GAME CONFIRMED BY USER 2026-09-01 — SHIPPED.**

All five test points passed in a single round. The user's exact words:

> "1. Confirmed
> 2. Confirmed
> 3. Confirmed
> 4. Confirmed
> 5. Confirmed.
>
> Ship it"

Against the numbered list in `_build_junk_servant.py` that is:

1. No Junk monster on the field → the Special Summon is **not** offered.
2. Face-up Junk monster on the field → offered, resolves **for free**, and the
   card arrives as a Level 4 EARTH Warrior 1500/1000.
3. Face-down-only Junk board → **not** offered. *This is the deliberate,
   user-approved deviation* (`faceup_only = 1`; the printed text omits
   "face-up"). Confirmed as intended behaviour, not a bug.
4. Second copy the same turn → offered again (no once-per-turn).
5. A Junk **Spell** alone (Junk Barrage / Junk Box) → **not** offered, as
   predicted by `0x021ACFE8` walking monster zones 0..4 only.

Wired into the chain on the user's "Ship it": `PatchStep` in
`apply_all_patches.py` (index 39 of 46, WiFi timers still last) and
`patch_junk_servant` in `_verify_all_patches.SHIPPED` — both in the same commit,
per `otn-chain-build-verify-artifact`.

---

## Confirmed (this session)

### The "Junk" archetype IS already in the ROM — set code 0x50

* `has_set_code` pointer table `0x0209D0D8`, index **0x50** → thunk `0x02023E5D`
  (`ldr r1,=0x0209C842 ; ldr r3,=0x02022E15 ; movs r2,#0x0D ; bx r3`, bytes
  `0149 024b 0d22 1847 | 42c80902 152e0202`).
* List `0x0209C842`, **sorted, 13 × u16**:

  | cid | card |
  |---|---|
  | 0x1E07 | Junk Synchron |
  | 0x1E10 | Junk Warrior |
  | 0x1E3D | Junk Barrage (Spell) |
  | 0x200C | Junk Box (Spell) |
  | 0x2185 | Junk Archer |
  | 0x219E | Junk Collector |
  | 0x221F | Junk Blader |
  | 0x229C | Junk Destroyer |
  | 0x2335 | Junk Forward |
  | 0x2355 | Junk Gardna |
  | 0x23FF | Junk Defender |
  | 0x2500 | *** PHANTOM *** |
  | 0x2524 | *** PHANTOM *** |

  Proven by walking all 103 parseable `has_set_code` thunks off `0x0209D0D8`
  (decoding each `ldr r1,[pc,#imm]` pool word + `movs r2,#N`) and intersecting
  each list against the 11 Junk cids in `scratch/cid_to_name.json`. Only index
  0x50 holds all eleven. Phantom status = absent from `cid_to_name.json` (4305
  named cids), i.e. no card_prop record.

* **0x2500 IS Junk Servant's own reserved Konami ID.** 3DS
  `romfs/duel/card/CARD_Indx_E.bin` record **4532** → name "Junk Servant";
  `CARD_Prop.bin[4532] & 0x3FFF` = **0x2500**. (0x2524 = record 4568 = "Junk
  Berserker".) So the count-neutral drop is the slot Konami reserved for this
  exact card.

* The 3DS agrees the set code is 0x50: `{u32 cid, u32 setcode}` pair table at
  3DS VA **0x0069E074** reads `… {0x24ED,0x57} {0x24F5,0x40000040} {0x2500,0x50}
  {0x250B,0x6F} …`. Extends `setcode.numbering_shared_with_3ds` (proven on Dark
  World 0x0F) to Junk 0x50.

* **Exactly one stock consumer** of set code 0x50: criteria row 1136 =
  `{0x221F Junk Blader, aux 0x50, handler 0x0223CA2D, word 0x00000002}` — Junk
  Blader's "banish 1 'Junk' monster from your Graveyard". Scanned all 0x56C rows
  at `0x022713C4` for `aux == 0x50`.

* No shipped patch writes `0x0209C842` (grep over `finished_patches/`).

### The engine's own template for this clause shape: `0x0225F7A0`

Disassembled; it is the **Six Samurai** hand-SS gate ("If you control a face-up
'Six Samurai' monster, you can Special Summon this card (from your hand)"):

```
0225F7A0  adds r0, r6, #0        ; r6 = side
0225F7A2  bl   0x021AD870        ; canSS(side)
0225F7A6  cmp  r0, #0
0225F7A8  beq  0x0225F836        ; reject
0225F7AA  ldr  r1, [pc,#0xc4]    ; [0x0225F870] = 0x02023A19  <- set-code 0x1E thunk
0225F7AC  adds r0, r6, #0        ; side
0225F7AE  adds r2, r7, #0        ; exclude
0225F7B0  movs r3, #1            ; faceup_only = 1
0225F7B2  bl   0x021ACFE8
0225F7B6  cmp  r0, #0
0225F7B8  beq  0x0225F836        ; reject
0225F7BA  b    0x0225F216        ; SUCCESS  (movs r0,#4 ; orrs r5,r0)
```

`0x02023A19` is `has_set_code[0x1E]` = Six Samurai (18 entries @ `0x0209CA8C`,
the table `patch_elder_six_samurai` PART D edits). Reached by a single `b`
@`0x0225F152` — no BL callers.

### `0x021ACFE8` argument contract (full disassembly)

`0x021ACFE8(r0 = side, r1 = set_code_thunk, r2 = exclude, r3 = faceup_only)
-> count`

* Loop is `r4 = 0..4` (`cmp r4,#4 ; ble`) — **monster zones only**. So the two
  Spells in the Junk list (Junk Barrage, Junk Box) can never satisfy the
  condition and no is-monster gate is needed.
* Zone → cid via `0x021A3320(side, zone)`; skipped when 0.
* `r2` is overloaded: if `0 <= r2 <= 0xA` it is an **exclude-ZONE** (stored to
  `[sp+0xC]`, cid-exclusion disabled); otherwise it is an **exclude-CID**. So
  `r2 = -1` means "exclude nothing".
* Two flag rejects on `[rec+0x44]` (bit 1, bit 0x15); `faceup_only != 0`
  additionally requires `[rec+0x3C] != 0`.
* Candidate cid goes to `r0` and the thunk is called with `blx r1`; nonzero
  return increments the count, which is the return value.

Sibling on-field callers in the hand-SS leaf region: `0x0225F59A`, `0x0225F714`,
`0x0225F7B2`. GY variant is `0x021B18E0` (`stat.gy_setcode_counter`).

### Routing

The donor cannot be routed through the hand-SS dispatch BST: per
`handss.dead_arm_donor_windows` all four dead arms are spent or Speed-Spell-only
(`0x0225E6E6` = Lightpulsar, `0x0225E88E` = Darkflare, the last monster-reachable
one). The ov3 dead run `0x0225F240` is 124/126 B used (`allocations.yaml`).
⇒ the **shared ov5 hand-SS trampoline** over `BL 0x0225E51C @0x0224C026`
(`handss.hook_site`, in-game confirmed for T.G. Striker) is the route.
`tg_table.register_tg_handss` is idempotent and multi-cid; its table
`CAVE_TG_SSTABLE` @`0x0239B1A8` (4 slots) has **one** occupant, 0x1F18
(T.G. Striker is the only caller in the tree — T.G. Warwolf hooks
`0x022692E8`/`0x02269396` instead).

### Donor: Neo Aqua Madoor `0x17CE` (user's pick)

Normal Monster, Lv6 WATER Spellcaster 1200/3000, pack1=5.
`donor_scan 0x17CE` → **VERDICT: CLEAN — no data structure names this cid**, with
*zero* hits of any kind (not even ambiguous ARM9-data or code-region ones).
Text budgets (smallest slot across all eight languages): name **15 B** (need 13),
desc **94 B** (need 84) — both fit in place in every language.

Rejected candidate: Mist Valley Watcher `0x1E87` looked ideal (1500 ATK already)
but its ARM9 data hit `0x0209C7D2` resolves to **entry 3 of set-code 0x37's
11-entry list @0x0209C7CC** — a real archetype membership, which would have
needed an Elder-of-the-Six-Samurai-style removal pass.

### Baseline health

* `verify_knowledge`: 386 facts, **349 PASS, 0 FAIL**, 37 UNVERIFIED (narrative).
* `check_allocations`: 157 ov5 slots (142 live), 138 phantom claims, 11 ov3
  dead-code claims — **no overlaps, no double-claims, ledger in sync**.
* Live `CAVE_FREE` = `0x0239DEF0`; 0x230 B remain to `0x0239E120`.

---

### Built (static verification only — NOT an in-game confirmation)

`_build_junk_servant.py --text` → `data/over_the_nexus/working/rom_junk_servant.nds`
(129,517,704 B, sha256
`74cd15cbecbe373891a46bb7a424d93949e4d8761a26a532af08d0a879b74214`).

* Condition stub: **44 B** at `CAVE_JS_SSCOND` = `0x0239DEF0` (0x30 B reserve),
  `assert_thumb1_only` clean. Disassembled back out of the built ROM:

  ```
  0239DEF0  push {r4, lr}
  0239DEF2  adds r4, r0, #0        ; side, callee-saved across both BLs
  0239DEF4  bl   0x021AD870        ; canSS(side)
  0239DEF8  cmp  r0, #0 ; beq no
  0239DEFC  adds r0, r4, #0
  0239DEFE  ldr  r1, [pc, #0x18]   ; [0x0239DF18] = 0x02023E5D  ("Junk" thunk)
  0239DF00  movs r2, #0
  0239DF02  mvns r2, r2            ; exclude = -1
  0239DF04  movs r3, #1            ; faceup_only
  0239DF06  bl   0x021ACFE8
  0239DF0A  cmp  r0, #0 ; beq no
  0239DF0E  movs r0, #1 ; pop {r4, pc}
  0239DF12  no: movs r0, #0 ; pop {r4, pc}
  ```
* `verify()` on the test ROM: **ALL CHECKS PASSED** (stub byte-exact + Thumb-1;
  hook installed at `0x0224C026` with `0x17CE` in the shared dispatch table; Junk
  list still 13 entries, strictly sorted, `0x17CE` in / `0x2500` out, four native
  Junk cards still members; donor has **no** summon-procedure row at
  `0x0228F158`, so the summon is free).
* Junk list read back from the built ROM: `0x17CE, 0x1E07, 0x1E10, 0x1E3D,
  0x200C, 0x2185, 0x219E, 0x221F, 0x229C, 0x2335, 0x2355, 0x23FF, 0x2524`.
* `card_prop[1570]` decodes as cid 0x17CE, **Effect Monster, EARTH, Level 4,
  Warrior, 1500 / 1000**. Name and description landed in place in every language
  checked (e/f/g/s), byte-length unchanged.
* Composition: applying **T.G. Striker on top** (`rom_junk_servant_compose.nds`,
  a static-check artifact, *not* the duel ROM) leaves both cards registered on
  the shared trampoline — `junk_servant=PASS tg_striker=PASS`.
* `check_allocations`: 158 ov5 slots (143 live), 139 phantom claims — no
  overlaps, no double-claims, ledger in sync.
* `verify_knowledge`: **389 facts, 352 PASS, 0 FAIL**, including the three new
  ones (`setcode.junk_table`, `setcode.junk_numbering_matches_3ds`,
  `handss.archetype_control_leaf`).

None of the above is in-game evidence. The card is **AWAITING IN-GAME TEST**.

### Shipped into the chain 2026-09-01

`apply_all_patches` ran to completion: **ALL 46 PATCHES APPLIED**, Junk Servant at
step **40/46**, WiFi timers still 46/46. The previous chain ROM was moved to
`rom_all_patches.PREV.nds` FIRST so a silent mid-chain death could not leave a
plausible-looking artifact (`otn-chain-build-verify-artifact`).

* Built artifact: `data/over_the_nexus/working/rom_all_patches.nds`,
  **129,529,992 B**, sha256
  `6fde114b6f37292a9c1699b5bc0f36b84d50a80434ef5c4e987e60f4a00ef165`
  (confirmed different from PREV).
* Name/desc landed in place in **all eight languages** (`e f g i s j k r`),
  12/15..20 B name and 83/94..228 B desc — no blob grew.
* `_verify_all_patches.py` over the built ROM: **PASS 35, FAIL 0, SKIP 2**
  (the two skips are `patch_boggart_knight` and `patch_darksoul`, which have no
  `verify()` of their own).
* The shared-trampoline composition held in the real chain: `patch_junk_servant`
  reports `T.G. Striker 0x1F18 also registered: True`, and `patch_tg_striker`
  passes its own three checks against the same ROM.

### ⚠️ Ledger drift introduced by a CONCURRENT edit (not this card)

While the chain was building, `ov5_cave.py` gained a slot that is not this
session's work: `CAVE_UNKSYN_SSCOND = 0x0239DF20` (0x30 B), for an *Unknown
Synchron* on donor Woodborg Inpachi 0x181C. No `patch_unknown_synchron.py` exists
yet, so nothing references it and the built ROM is unaffected.

* **No overlap with this card.** `CAVE_JS_SSCOND` is 0x0239DEF0 + 0x30 and its
  stub occupies 44 B (ends 0x0239DF1C); the new slot starts exactly at
  0x0239DF20. Adjacent, disjoint.
* **But `check_allocations` now fails**, because that slot was never emitted to
  the ledger: `[X] ov5 slot @0x0239DF20 in ov5_cave.py but NOT in the ledger`.
  Both `apply_all_patches` and every `_build_*.py` abort on a non-zero guard, so
  **no build will run until it is regenerated**:
  `.venv-1/Scripts/python.exe -m otn_enhanced.knowledge.check_allocations --emit`
  It was left for whoever owns that slot rather than folded into the committed
  ledger from here.
* That edit also corrected the cave-headroom comment: the old "0x1790 == 6032
  bytes still free" was wrong; the live figure is `0x0239E120 - CAVE_FREE`, now
  **464 B**. The ov5 cave is nearly exhausted — a large new stub needs a plan.

## Ruled Out

* **Routing via a dead hand-SS arm** — none reachable by a monster cid remains
  (`handss.dead_arm_donor_windows`, VERIFIED). Not re-tested; inherited and
  re-read this session.
* **Hosting the condition stub in the ov3 dead run `0x0225F240`** (which would
  have made the card puzzle-safe) — 124 of its 126 bytes are already claimed by
  `handss_banish_cost` + `ninjitsu_art_super_transformation`.
* **A summon-procedure registry row @`0x0228F158`** — deliberately NOT added.
  Per `handss.summon_procedure_registry`, a miss on that table means the card is
  summoned by the generic path *for free*, which is exactly Junk Servant's
  (costless) summon. This is the one card where the Lightpulsar/Darkflare trap is
  the desired behaviour.
* **Donor Mist Valley Watcher `0x1E87`** — see above, it is a set-code 0x37 member.

## Open Questions

* `r7` at `0x0225F7AE` (the native leaf's `exclude` argument) was not traced;
  `r7` is set by `lsrs r7, r0, #0x18` @`0x0225E594` early in `0x0225E51C`, so it
  is a flags/zone byte, not obviously a cid. Our stub sidesteps this by passing
  `-1` (exclude nothing), which is the faithful reading of the printed text.
  Only matters if in-game shows a miscount.
* Whether the deck editor surfaces the donor under a "Junk" archetype label once
  it joins list 0x50 (cosmetic; `setcode.inert_2a_table` notes the editor reads
  these tables).

## Next Experiment

Build `rom_junk_servant.nds` via `_build_junk_servant.py`, then in melonDS
(normal duel, NOT a puzzle — ov5 is evicted by ov41):

1. Junk Servant in hand, **no** Junk monster on your field → the Special Summon
   must **not** be offered.
2. Normal Summon a Junk monster face-up (Junk Synchron / Gardna / Forward), then
   select Junk Servant in hand → offer appears, resolves **for free**, card
   arrives as Lv4 EARTH Warrior 1500/1000.
3. Only a **face-down** Junk monster → **not** offered (`faceup_only = 1`, the
   user's decision 2026-09-01; the printed text omits "face-up", so this is a
   deliberate, user-approved deviation).
4. Second copy in the same turn → offered again (no once-per-turn).
5. Regression: T.G. Striker's own hand-SS offer still works (shared trampoline).

## Inherited from the pre-DSL module docstring (UNVERIFIED, not re-proven; old file in git history)
- Junk set code 0x50: thunk 0x02023E5D -> sorted 13-entry list 0x0209C842, phantoms 0x2500 (spent) and 0x2524 (junk_speeder).
- 0x021ACFE8 walks MONSTER zones only (so Junk Spells never satisfy it); r2 outside 0..0xA = exclude-CID, -1 excludes nothing.
- Deliberate user-approved deviation: faceup_only = 1 although the printed text omits "face-up".
- NO summon-procedure registry row (0x0228F158) on purpose: a miss summons for free, which is the printed card. Do not add one. The DSL no longer asserts this; byte-identity covers it today.
- Hand-SS offer rides the shared trampoline (hook 0x0224C026; slot 2 of 4, Striker slot 1). Dispatch-tree route had no dead arm left.
