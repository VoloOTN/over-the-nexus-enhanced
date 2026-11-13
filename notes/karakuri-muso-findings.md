# Karakuri Muso mdl 818 "Haipa" — findings

Session 2026-08-25. **SHIPPED — IN-GAME CONFIRMED ON THE FIRST TEST.**
Single-card ROM: `data/over_the_nexus/working/rom_karakuri_haipa.nds` (`_build_haipa.py`).
Registered in `apply_all_patches.py` directly below Maiden (its dependency).

Printed text (`scratch/ygoprodeck_cache.json`, passcode 24150026):
> This card must attack if able. When this face-up Attack Position card is selected
> as an attack target, change it to Defense Position. If this card attacks, it is
> changed to Defense Position at the end of the Battle Phase.

1. This card must attack if able.
2. When this face-up Attack Position card is selected as an attack target, change it to Defense Position.
3. If this card attacks, it is changed to Defense Position at the end of the Battle Phase.

All three are implemented. **None needed new effect machinery** — the engine
already implements all three for other cards; the whole patch is new *membership*.

## Confirmed (this session)

- **KB healthy**: `verify_knowledge` 300 facts, **268 PASS / 0 FAIL / 32 UNVERIFIED**
  (was 298/266/32 before this session's 4 new facts, all now VERIFIED; the generated `otn_enhanced/docs/engine/`
  is untracked and was already 2 facts stale against `author_facts.py`, which the
  mandated regeneration resynced — `git diff` on the source is +167 / **-0**).
- **Muso is absent from the ROM.** 15 Karakuri cids present; Muso, Ninishi,
  Barrel, Gama, Bonze, Nanashick, Super Shogun, Spider are not.
- **Clause 3 = the end-of-Battle-Phase sweep `0x02252EC0`**, effect-registry
  row 1 (`0x0228E1E8` = {resolver `0x02252EC1`, cid `0x0000`} — a generic phase
  handler, and **no BL anywhere in ov3 targets it**; the registry pointer is its
  only inbound reference). Five per-zone gates, all cid-independent, then
  `r5 = 0x021A36EC(side,zone)` @`0x02252F96` feeds an ordered compare tree with
  **three** arms:
  | Arm | Address | Behaviour | Members |
  |---|---|---|---|
  | A | `0x02253040` | flip **+ position LOCK** (`0x021C479C`, key `0x1419`, kind `0x22`) | 0x1419, 0x1566, 0x15D2, 0x1912, 0x1C7F, 0x1CAB, 0x1DA6, 0x1ECB, phantoms 0x1915/0x1DB6 |
  | **B** | **`0x02253078`** | **flip, NO lock** (`b 0x02253068` skips the attach) | 0x1A61 Dasher, 0x21FC Transforming Sphere, 0x22D0 Gem-Knight Aquamarine |
  | C | `0x02253094` | flip **face-down** (`0x021C5894`) | 0x1FB4 Worm Rakuyeh |
  Arm B's three members are exactly the ROM's three printed "flip to DEF at end of
  Battle Phase" cards **with no lock** — the membership self-validates.
  Now KB fact `battle.end_of_bp_flip_sweep` (VERIFIED).
- **`0x2092` is the "declared an attack" rider, NOT Ancient Forest.** It is
  Ancient Forest's cid and the compiler pools constants by value, which made the
  sweep's gate look Ancient-Forest-conditional. The marker is attached
  unconditionally in the attack-declaration path at `0x021C6104..0x021C611E`;
  `0x021A1430` walks the family-1 rider list at `0x0229D33C` via `0x021A1238`.
  This is what makes the sweep's gate cid-independent.
  Now KB fact `battle.attacked_marker_rider` (VERIFIED).
- **Clause 1 = two ordered chains, `0x0224D250` and `0x0224D530`**, both fed by
  the same getter `bl 0x021A36EC` (`0x0224D254` / `0x0224D534`). Population is
  exactly `{0x16BF, 0x2388..0x238C, 0x2466, 0x2467}` — the eight ROM monsters
  that print the clause. Chain 1 builds its comparands from one pool word
  `0x2388` (`[sp+0xC]`=0x238C pivot, `[sp+0x10]`=`[sp+0x14]`=0x2466,
  `[sp+0x18]`=0x2467) and dispatches `0x2388..0x238C` through a five-entry
  PC-relative jump table at `0x0224D270` (all entries `0x0054` → the single
  accept leaf `0x0224D2C6`). Chain 2 has the same shape (pivot `r7+0xA0`, table
  base `r7+0x9C`, r7 = 0x22EC). Now KB fact `battle.must_attack_chains` (VERIFIED).
- **Clause 2** is the stock position-change cls1 record
  `{+04 0x0220C6B1, +0C 0x021F4D4D}` (`battle.change_own_position_resolver`),
  cloned from Black Stego `0x1A78`. The record alone is inert: the code-0x13
  event reaches only 26 hard-coded cids, so the donor also joins maiden's
  **shared** admit list.
- **Donor: Saggi the Dark Clown `0x0FC8`** — Level 3 DARK Spellcaster 600/1500
  Normal Monster, obtainable (pack1 = 2). Records-free in all four cls tables,
  the effect registry and the criteria registry, with **zero aligned u16/u32
  occurrences anywhere in ov3 + arm9**. Name floor 18 / description floor 58
  across all eight languages, so "Karakuri Haipa" (14 B) and the condensed text
  (53 B) both land **in all eight, in place**.

## Ruled Out

- **A Karakuri donor** (clauses 1+2 free, zero new records) — rejected on the
  user's instruction to keep every Karakuri playable. Worth recording anyway:
  of the six, **only Nisamu `0x2388` carries the position-change record as its
  LEFTMOST cls1 row**. On 0x2389/0x238A/0x238B/0x238C it is the *second* cls1
  record, which `dispatch.second_cls1_record_is_spirit_only` says is unreachable
  through `find_event_handler` for a non-Spirit.
- **The full 29-byte name.** Only four records-free cards in the ROM have a
  29 B English name slot; three are Speed Spells and the fourth (`0x1ED7`) is
  already Maiden's donor. Growing the name blob is forbidden
  (`donor.name_slot_floor`). User chose "Karakuri Haipa"; archetype membership is
  the set-code table, not the name, so nothing mechanical is lost.
- **Extending either clause-1 chain by data.** `[sp+0x10]`/`[sp+0x14]` look
  redundant but both are load-bearing (pivot vs equality test) — re-aiming either
  drops Saizan; the jump table is only indexed for `0x2388 <= cid <= 0x238C`.
- **Extending the clause-3 tree by data.** The `>0x21FC` leaf `0x02253024` is the
  only one-member leaf and its `[sp+0x44]` is `0x21FC + 0xD4` (imm8), so no
  immediate reaches a low cid; the 0x6C frame is fully allocated.
- **Hosting the stubs in ov3 (puzzle-safe).** The always-resident ov3 dead-code
  supply is down to a **22 B contiguous maximum** — `check_allocations.OV3_CLAIMS`
  shows escuridao, shiens_dojo ×2, eclipse_wyvern ×2 and handss_banish_cost hold
  the rest (106 B free, fragmented). Two stubs of 24 B + 28 B do not fit.
  ⚠️ I initially built into `0x021B582A` / `0x021B58E6` **without checking
  OV3_CLAIMS** and silently collided with both shiens_dojo claims. The KB fact
  `stat.phantom_arm_scratch` only names escuridao's claim — **the ledger, not the
  fact, is authoritative for what is free.**
- **The ov3 BSS cave** (`ov3_cave.py`) — canary round 2 proved the engine clears
  ov3's BSS; both windows come back wiped in all five modes.

## In-game result (2026-08-25, first test — all six checks passed)

| # | Check | Result |
|---|---|---|
| 1 | attacks -> flips to DEF at end of Battle Phase (clause 3) | **changes position** |
| 2 | freely repositionable on the FOLLOWING turn | **can change position — proves ARM B, not Arm A** |
| 3 | attacked in face-up ATK -> flips to DEF (clause 2) | **changes position** |
| 4 | forced to attack when able (clause 1) | **must attack** |
| 5 | regressions: Aquamarine flip, Berserk Gorilla / Saizan / Kuick forced attack | **no regressions** |
| 6 | Karakuri searchers offer it (PART G set-code row) | **Cash Cache offers it, and so do the other Karakuri search cards** |

Check 2 is the one that mattered: Arm A and Arm B are indistinguishable for a
single turn, and only diverge when you try to reposition the card next turn. A
lock there would have meant the divert landed on Arm A.

## Open Questions

- None for this card. Untested by design: puzzle mode (ov5 stubs are inert there,
  and clause 2 already depended on maiden's ov5 gate regardless).

## What shipped

`otn_enhanced/cards/karakuri_haipa.py`, seven parts:

| Part | What | Where |
|---|---|---|
| A/B | Level 4 EARTH Machine 2100/1100 Effect Monster; name + text, all 8 languages | bin2.pac |
| C | clause-2 cls1 record, count-neutral over phantom `0x0ECC` | cls1[56] |
| D | donor joins maiden's SHARED attack-target admit list | `patch_maiden_eyes_of_blue.ATKTGT_ADMIT` |
| E | clause 1: cid remap → `0x2388`, hooked at both getters | `0x0224D254`, `0x0224D534` → ov5 `CAVE_HAIPA_MUSTATK` |
| F | clause 3: divert donor to Arm B | `0x02252F9A` → ov5 `CAVE_HAIPA_BPFLIP` |
| G | Karakuri set-code row, count-neutral over phantom `0x2445` | arm9 `0x0209CC16` |

⚠️ **Normal duels only** — both stubs are ov5-hosted (a puzzle loads ov41 over
ov5). This costs the card nothing extra: clause 2 already requires maiden's
ov5-hosted `CAVE_ATKTGT_GATE`, so it is a normal-duel card either way.

⚠️ **Depends on `patch_maiden_eyes_of_blue`** (PART D). `main()` asserts the donor
is in `ATKTGT_ADMIT` and `verify()` asserts the gate is hooked, so the dependency
fails the build rather than going quiet.

Registered in `apply_all_patches.py` as `_apply_karakuri_haipa`, placed **directly
below the Maiden step** — that ordering is load-bearing, not cosmetic: clause 2's
record is inert without maiden's shared attack-target gate.

## Next Experiment (the in-game oracle)

Normal duel, `rom_karakuri_haipa.nds`. "Karakuri Haipa" occupies Saggi the Dark
Clown's slot (Level 4, 2100/1100).

1. Attack with it → at the **end of the Battle Phase** it must flip to **face-up
   Defense Position**.
2. **On your next turn it must be freely changeable back to Attack Position.**
   A lock here means the stub landed on Arm A, not Arm B — the single most
   important observation in this test.
3. Opponent declares an attack on it while face-up Attack Position → it flips to
   Defense (clause 2).
4. It must be forced to attack when able (clause 1).
5. Regression: **Gem-Knight Aquamarine 0x22D0** must still flip at end of Battle
   Phase; **Berserk Gorilla 0x16BF / Saizan 0x2466 / Kuick 0x2467** must still be
   forced to attack.
6. Regression: a Karakuri search (**Karakuri Cash Cache**) must offer it — proves
   the PART G set-code row.
