# Steam Synchron — findings

Live file. Everything below was verified **this session (2026-09-03)** unless
marked UNVERIFIED.

Card: **Steam Synchron**, Konami id 83295594. WATER / Machine / Tuner / Effect,
Level 3, ATK 600 / DEF 800. Archetype "Synchron".

Printed text (`scratch/ygoprodeck_cache.json`, verbatim — NOT from recall):

> During your opponent's Main Phase, you can: Immediately after this effect
> resolves, Synchro Summon using this card you control (this is a Quick Effect).

Clauses:

1. *(the whole card)* Quick Effect during the opponent's Main Phase: Synchro
   Summon using this card you control as material. **In scope, built.**
2. *(a property)* "Synchron" archetype membership. **In scope, built.**

## STATUS: DONE — IN-GAME CONFIRMED 2026-09-03, SHIPPED

**In-game confirmed by user 2026-09-03**, all eight oracles, on the first test.
Their words: *"1. Confirmed 2. Confirmed 3. Confirmed 4. Confirmed 5. Confirmed
6. Confirmed 7. Confirmed 8. Confirmed"* then *"ship it!"*.

Donor: **Cyber-Tech Alligator `0x12B6`** (user-approved).
Tested ROM: `data/over_the_nexus/working/rom_steam_synchron.nds`,
sha256 `a3bd7debcc4d37020a01a5e7350a06347ade675e7cd67f59cb7e1844fc937268`.

What the eight oracles actually measured:

1. The Synchro Summon **is** offered during the opponent's Main Phase 1 and
   resolves onto your field on their turn. *(The open question below — whether
   cls3 slot3 is polled with an empty chain — is now answered: yes.)*
2–4. Negative controls all held: not offered on your own turn, not in the
   opponent's Battle/End Phase, not with no legal Synchro.
5. Stats, name and full official text correct.
6–7. Tuning and Junk Speeder reach it; every other Synchron still does.
8. **It works in PUZZLE MODE** — the measured payoff of the data-only build.
   An ov5-hosted clause would be inert there (overlay 41 evicts ov5).

Wired into `apply_all_patches` (`PatchStep` + `_verify_all_patches.SHIPPED` in the
same edit) on 2026-09-03.

⚠️ **One cross-patch fix made at ship time.** `patch_accel_synchron` spends
`0x0D6B` from the same Synchron list, and this module's `SYNCHRON_CORE` survival
tuple named it — which would have aborted whichever of the two built second, with
`check_allocations` passing cleanly because *a survival assertion is not a claim*.
`0x0D6B` was removed from the tuple. General lesson: **keep a survival assertion
to the cids you depend on, never to the whole table.**

---

## Confirmed

### The engine already ships this effect — Formula Synchron `0x239E`

Formula prints "Once per turn, during your opponent's Main Phase, you can Synchro
Summon using this face-up card you control as a Synchro Material Monster." Its
**complete** per-cid footprint (`donor_scan 0x239E` finds every aligned u16/u32
occurrence in ov3 + ARM9, so this is closed, not sampled):

| structure | address | content |
|---|---|---|
| cls3 record[730] | `0x0227E1E4` | cid `239E`, aux 0, **+04 `0x02249EC1`**, +08 0, **+0C `0x021F1491`**, +10 0, +14 0 |
| criteria row | `0x02274F1C` (stock row 1266, **chained row 1265**) | `{aux FFFF, handler 0x0223D21D, word 0x00000802}` |
| ARM9 spell-speed-2 list | `0x0209C118` | 118 × u16 sorted; count `movs r2,#0x76` @ `0x02023490` |
| ARM9 "Synchron" set-code list | `0x0209C968` | 15 × u16 sorted; count `movs r2,#0x0F` @ `0x02023E20`, pool `0x02023E24` |
| cls1[1253] + summon list `0x0228F6C0`[27] | | Formula's OTHER clause (the draw) — **not transplanted** |

⚠️ **Read the criteria row live, never by index** — it is 1266 in the stock ROM
and 1265 in `rom_all_patches.nds`. Shipped patches shift it.

### Condition `0x021F1490` (cls3 +0C) IS Steam Synchron's condition

Disassembled this session. In order:

1. turn-log scan (`0x0229A37C` + i·0x24, field `+0x48C`, count
   `[0x0229A9FC+0x44]`) for `desc[+0xC]` → if found return 0. *(Formula's
   once-per-turn; see Open Questions.)*
2. `[0x0229DD14+0x34] == 1 - desc[+2]` → **must be the opponent's turn**
   (`ldr r5,[r1,#0x34]` = `0x6B4D` @ `0x021F14C2`).
3. `[0x0229DD14+0x48] ∈ {2, 4}` → **Main Phase 1 or 2**
   (`cmp r0,#2` = `0x2802` @ `0x021F14D0`; `cmp r0,#4` = `0x2804` @ `0x021F14D4`).
4. `0x021F97F4(desc, event)` ≠ 0 → the Synchro Summon must be legal.
5. return 1.

### Resolver `0x02249EC0` (cls3 +04) is card-agnostic

Phase machine on `[0x0229AAFC+0x70]` (arms `0x64`, `0x6E`, `0x7D..0x80`), walks
the on-field zone records itself (`[player+0x34 + zone*0x14]` loop from
`0x02249F46`), calls the shared param provider `0x02234E78` @ `0x0224A02A`. Its
**only** per-cid arm is `cmp cid,#0x1EF0` (literal @ `0x0224A0D8`) — **Urgent
Tuning, a Trap**. A resolver shared between a monster and a Trap carries no
Formula-specific assumption.

### Criteria handler `0x0223D21C` is cid-agnostic

Reads the cid from the descriptor (`ldrh r1,[r2]` = `0x8811` @ `0x0223D22E`) and
forwards to `0x0223BE40`. No compare anywhere. Only two rows use it: `0x0E6B`
(a phantom) and `0x239E`.

### Set code `0x4C` is MONSTER-ONLY, and `0x229E`'s tag is STALE

Stock consumers — three criteria rows, all low half `0x0002` = MONSTER
(`dispatch.criteria_low_bits_are_card_type`, VERIFIED):

- row 1183 `0x229E` word `0x00010002`  ← Synchron Explorer's own native row
- row 1253 Necro Linker `0x237A` word `0x00018002` (+ bit15 Tuner)
- row 1269 Tuning `0x23A2` word `0x00008002` (+ bit15 Tuner)

In the **chained** ROM: rows 1252 / 1268 / **1368 `0x24B3` → Junk Speeder**
(handler `0x0239DFC1` == `CAVE_JSP_CRIT`), and `0x229E`'s row has moved to
**aux `0x000E`** — `patch_tour_guide` rewrote it. `has_set_code` slot 76 (`0x4C`)
→ thunk `0x02023E1D`; the only non-criteria consumers are the deck-editor filters
`0x0202A358` / `0x0202A3F0`.

⇒ `0x229E` (patch_tour_guide's donor → **Tour Guide From the Underworld**) keeps
a Synchron list slot it no longer uses. Spending it is a **correction**, and it
stops Tour Guide showing under a "Synchron" deck-editor filter.

⇒ Steam Synchron becomes reachable by **Tuning, Necro Linker and Junk Speeder**
(all three demand bit15 = Tuner, which it now is).

### Donor Cyber-Tech Alligator `0x12B6`

`donor_scan` → **VERDICT: CLEAN**, zero aligned u16/u32 occurrences in ov3 +
ARM9. Native: Normal Monster, Lv5 WIND **Machine** 2500/1600, pack 48.

Its **one** raw ARM9 halfword hit, `0x020A2A84`, was chased down and is a
**coincidence**: `0x020A2000..0x020A3400` is a byte ramp read as u16 — the
neighbouring "cids" decode as `1413 1414 1414 1515 1515 1616 1616 1717 1817…`,
i.e. consecutive bytes, and the stride histogram is 0x24 with stride-2 runs. The
one "pointer" into the region (`ov3:0x022173D0`) is Thumb **jump-table data**
(`add pc, r1`), not a pointer.

English blobs: name **20 B** (need 14) / desc **182 B** (need 152 — the **full
official text** fits, no paraphrase). Desc also fits f/g/i/s; j (82) / k (85) /
r (144) are too small and keep donor text. Name fits all 8.

### Phantoms spent — and the vetting standard, stated correctly

What licenses dropping a phantom's row: **(a)** no `card_prop` record, so no
instance can carry the cid and none of its rows is reachable; **(b)** it owns
**exactly one** row in the pool being edited. A phantom also appearing in *other*
tables is **not** a blocker — those rows are untouched. (My first pre-build
script conflated the two and reported four spurious FAILs.)

| pool | spent | footprint |
|---|---|---|
| cls3 `0x02279D74` | `0x1528` | **ideal** — its own cls3 row is its ONLY binding occurrence anywhere in the ROM |
| criteria `0x022713C4` | `0x0E6E` | cls0 record + exactly one criteria row |
| spell-speed-2 `0x0209C118` | `0x1774` | cls2 record only — deliberately not `0x0E6B`/`0x0E6C` (T.G. set-code members) or `0x0E63`/`0x0E64` (Infernity), so no shipped patch's set-code asserts are perturbed |
| Synchron `0x0209C968` | `0x229E` | **stale, not phantom** — see above |

All four unclaimed by any shipped patch before this one.

### ⚠️ NEW: cls3 row 370 is a by-index anchor, and it is NOT in the ledger

`patch_shiens_dojo` clones its wrapper slots from **`cls3[370]`**
(`UNITED_CLS3_ROW`, "Six Samurai United") and raises
`RuntimeError("Six Samurai United is not at cls3[370]")` if that row moves. The
full by-index anchor set is **{223, 233, 334, 370, 527}**; `check_allocations`'
comment only mentioned 223/233/334/527.

**And those modules are not order-independent among themselves**: running
`maiden` before `shiens_dojo` shifts row 370 and detonates that RuntimeError.
A composition check must use `apply_all_patches`' own order —
tour_guide #8 → sea_lancer #24 → shiens_dojo #27 → maiden #37 →
unknown_synchron #45. My first stage-2 order hit this; it is a **pre-existing
constraint between two shipped cards, not a Steam Synchron regression.**

Steam Synchron's own cls3 window is rows **[58, 97]**, below every anchor.

### Build results

- cls3: dropped `0x1528` (row 96), inserted `0x12B6` at row 58 — count 776,
  sorted, 33 multi-row cids all still contiguous.
- criteria: dropped `0x0E6E` (row 43), inserted at row 84 — count 1388, sorted,
  118 multi-row cids all still contiguous.
- spell-speed-2: dropped `0x1774`, inserted at index 11 — count 118, strictly
  sorted.
- Synchron: dropped stale `0x229E`, inserted at index 1 — count 15, strictly
  sorted, all 13 core Synchrons preserved.
- card_prop: `0x000E1581503E92B6` → `0x000E0CE1280F12B6` (Lv3 WATER Machine
  600/800 Tuner Monster).
- Composition (shipped order, steam applied first): `steam_synchron=PASS
  tour_guide=PASS sea_lancer=PASS shiens_dojo=PASS maiden_eyes_of_blue=PASS
  unknown_synchron=PASS`. Composed Synchron list holds **both** `0x12B6` (Steam)
  and `0x181C` (Unknown), 15 entries, strictly sorted — the two patches spend
  different slots (stale `0x229E` vs phantom `0x2501`) so they compose either way.

---

## Ruled Out

- **`0x0227113C` (19 × u16, read at `0x022395BA`) is a CPU-AI list, NOT the
  quick-effect gate.** Contents: The Regulation of Tribe, Embodiment of Apophis,
  Array of Revealing Light, A Feint Plan, Frozen Soul, Taunt, Threatening Roar,
  Elemental Absorber, Cyber Shadow Gardna, Morphtronic Bind, Grave of the Super
  Ancient Organism, Pixie Ring, Effect Veiler, Formula Synchron, Red Screen
  (+4 unnamed). Siblings read from the same per-cid switch at `0x022395xx`:
  `0x022711B8` ×0x30 (summon-response traps), `0x02271162` (destruction-response),
  `0x0227118C` (chain-related). It *looks* like the gate because Formula and
  Effect Veiler are in it. The real gate is `0x0209C118`.
- **The unsorted ARM9 blocks at `0x020AA952` / `0x020AA998`** (which also name
  `0x239E`) are AI hint tables — unsorted ⇒ not binary-searched gates, and no
  aligned u32 points at them.
- **Stealing the Gravekeeper neighbour's trailing phantom `0x2442` is BLOCKED.**
  `patch_gravekeepers_recruiter` (shipped, chain #7) spent it on Botanical Girl
  `0x1ED4` and asserts both consumer pool words (`0x02023778`, `0x020237A4`) and
  both `movs r2,#0x10` immediates (`0x02023774`, `0x02023792`). Live Gravekeeper
  list = 16/16 full.
- **The Synchron list cannot grow in place**: Lightsworn ends `0x0209C966`,
  Gravekeeper's begins `0x0209C986`. Its only phantom `0x2501` went to
  `patch_unknown_synchron`.
- **Relocating the Synchron list was designed and then made unnecessary** by the
  stale-`0x229E` find. Recorded because the reasoning stands if a *second* new
  Synchron is ever added: one consumer ⇒ 3 writes (pool word `0x02023E24`, count
  `0x02023E20`, data), but it would need a proven-dead always-resident ARM9 home
  and an edit to `patch_unknown_synchron`'s hardcoded base/count.
- **`_build_arm9_canary.py`'s appended cave `[0x020AF120, 0x020B7120)` is not an
  option** — built 2026-07-27 and **never played**
  (`notes/gladiator-beast-essedarii-findings.md`), so it is unproven.
- **`0x0D6B` / `0x1E4E` were the fallback drops and were NOT spent.** Both are
  inert (set code `0x4C` is monster-only) and `0x0D6B` has `pack1=0` so it is
  unobtainable. Kept in reserve for a future Synchron.

---

## Open Questions

- **Where is the once-per-turn stamped?** The condition only *reads* the turn
  log. ASSUMED to be a generic activation log, so the donor inherits an
  unintended once-per-turn (user-accepted deviation). Not proven either way.
  Candidates to check: the resolver's `0x0225BE7C` / `0x0225BF3C` calls at
  `0x0224A0C0` / `0x0224A0CA`.
- ~~**Is cls3 slot3 actually polled during the opponent's Main Phase with an empty
  chain?**~~ **ANSWERED YES by oracle 1, in-game 2026-09-03.** This was the one
  genuinely unproven step — the responder `0x021EDA14` does reach slot3 for a
  free, untriggered offer, not just for a triggered one like Maiden's clause 1.
  A cls3 record + spell-speed-2 membership is therefore sufficient for a
  *spontaneous* opponent's-turn Quick Effect, which is a reusable result.
- ARM9 static-module zero runs (`0x0209D4B5` 147 B, `0x020A1E94` 122 B,
  `0x020AC074` 72 B, `0x020AD8D9` 159 B — holds `arm9_cave_check`'s probe —
  `0x020AE940` 212 B). Not needed any more; UNVERIFIED as dead space, would need
  the savestate all-zero check. Worth banking as a future resource.

---

## Next Experiment

**The in-game test.** `rom_steam_synchron.nds`. Checklist is in
`_build_steam_synchron.py`'s docstring; the decisive one is check 1 (does the
prompt appear at all during the opponent's Main Phase 1), which settles the open
question above. Checks 2–4 are the negative controls; check 7 is the Synchron
list regression; check 8 tests the puzzle-mode claim (this patch has no ov5
dependency, so it should work there too — unlike every ov5-hosted card).

If check 1 fails with no prompt at all, the next move is **not** another build:
capture a savestate mid-opponent-Main-Phase and use `scratch/thumbemu.py` to run
`0x021F1490` against it, to see which of the four gates rejected.
