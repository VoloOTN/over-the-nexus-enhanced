# Wonder Wand — findings (session 2026-08-03)

Target card text (authoritative, `scratch/ygoprodeck_cache.json`, id 67775894):

> Equip only to a Spellcaster monster. It gains 500 ATK. If you control the
> equipped monster and this card: You can send both to the GY; draw 2 cards.

Clauses:
1. Equip only to a Spellcaster monster.  *(equip-target gate)*
2. It gains 500 ATK.  *(continuous grant)*
3. If you control the equipped monster and this card: You can send both to the
   GY; draw 2 cards.  *(field ignition — cost = send both, effect = draw 2)*

**Scope this session: clause 2 — DONE and IN-GAME CONFIRMED. Clause 1 is
`unproven` and deliberately not implemented. Clause 3 left exactly as it was.**

## Confirmed (verified THIS session)

- ⭐ **CLAUSE 2 IS IN-GAME CONFIRMED** (user, 2026-08-03, on
  `rom_wonder_wand.nds`): the equipped monster's ATK rises by the patched amount.
  This proves more than the static cross-check did — **`0x0226DFB0` is the LIVE
  source of an equip's stat bonus**, not merely a data mirror that happens to
  agree with the card text. Editing the `atk`/`def` i16 in a record changes the
  bonus the engine actually applies. Consequence: any "+N ATK" equip clause is a
  **2-byte data edit**, with no shim, no cave slot, and no cls record — the
  custom-grant-shim approach in the older notes is unnecessary for this case.

- **KB is healthy.** `verify_knowledge`: **116 PASS / 0 FAIL / 24 UNVERIFIED**
  (140 facts after this session's additions); oracles arm9+ov3+ov5+savestate.
- **cid resolution method**: `card_prop.bin` record *i* (8-byte header, 8-byte
  records) has the engine **cid in its low 14 bits**; the same *i* indexes
  `card_indx_<lang>.bin` (8-byte header, `[name_off u32][desc_off u32]`) into
  `card_name_<lang>.bin`.
  - Axe of Despair `0x10D6`, Black Pendant `0x10DD`,
    **Book of Secret Arts `0x10E9`**, Magic Formula `0x1467`,
    **Trial of the Princesses `0x19D8`** (matches the module).
- **The donor grants +800, not +500.** Trial of the Princesses is *"Equip only to
  'White Magician Pikeru' or 'Ebon Magician Curran'; it gains **800** ATK. During
  a turn that the equipped monster **destroyed a Level 5 or higher monster by
  battle**, you can Tribute the equipped monster and this card to Special Summon
  ..."* The module declared `WW_ATK_GAIN = 500` and **never used it**, so the ATK
  was simply never patched. Its ignition is also **battle-destruction gated**,
  which is *not* Wonder Wand's condition — relevant to clause 3.
- **THE EQUIP ATK/DEF GRANT TABLE — `0x0226DFB0`, stride 6, 94 records,
  `[cid u16][atk i16][def i16]`**, sorted, spanning `0x0226DFB0 .. 0x0226E1E4`.
  Every record cross-checks against the printed card — a closed structural proof:

  | addr | cid | ATK | DEF | card |
  |---|---|---|---|---|
  | 0x0226DFB6 | 0x10D3 | +300 | +300 | Legendary Sword |
  | 0x0226DFBC | 0x10D4 | +400 | −200 | Sword of Dark Destruction |
  | 0x0226DFC8 | 0x10D6 | +1000 | 0 | Axe of Despair |
  | 0x0226DFF2 | 0x10DD | +500 | 0 | Black Pendant |
  | 0x0226DFFE | 0x10DF | 0 | +800 | Horn of Light |
  | 0x0226E004 | 0x10E0 | +700 | +700 | Horn of the Unicorn |
  | 0x0226E02E | 0x10E9 | +300 | +300 | Book of Secret Arts |
  | 0x0226E09A | 0x1467 | +700 | 0 | Magic Formula |
  | **0x0226E13C** | **0x19D8** | **+800 → +500** | **0** | **Trial (donor)** |

  A second run of the same shape begins at `0x0226E1E4` (Speed Spell equips,
  `0x0Dxx`). **Clause 2 = a 2-byte in-place edit**; count-neutral, no re-sort.
  Now a KB fact: `equip.grant_table` (VERIFIED).
- **`0x02022E44` = generic sorted-table binary search**, `find(key r0, base r1,
  count r2, stride r3)` → record pointer or 0; key is the **i16 at `+0`**, and
  count/stride are hardcoded immediates per call site. Any table it searches must
  stay sorted by `+0` and count-neutral. KB fact `dispatch.sorted_table_search`.
- **`0x0226F628` is a real per-cid hook table, but not the equip-target gate.**
  `0x021E5200` binary-searches it with `count=0x61`, `stride=0xC` (immediates read
  out of the function; literal `@0x021E5274` = `0x0226F628`), calls `+4` as a
  predicate (`r0 != 0` ACCEPTS) and `+8` as an applier, driving a counter at
  `[0x0229AAFC+0x7C]` — an FSM/chain handler, **not** a target enumerator. Its 97
  rows are mostly monsters / sent-to-GY hooks; **no** race-locked equip has a row
  (`0x10E9`, `0x1467`, `0x19D8` all absent). KB: `equip.percid_hook_table`, with
  the old `equip.target_table` demoted to UNVERIFIED + `corrected_by`.
- **The real dispatch geometry — four cls tables, no "master table".**
  `find_event_handler` `0x0224A118` switches on `descriptor[+5]` through a
  4-entry jump table at `0x0224A134` and selects, all stride 24 with **cid as a
  u16 at `+0x00`** and five Thumb slots at `+04..+14`:

  | class | base | rows |
  |---|---|---|
  | cls2 | 0x02275C04 | 697 (0x2B9) |
  | cls3 | 0x02279D74 | 776 (0x308) |
  | cls0 | 0x0227E64C | 1306 (0x51A) |
  | cls1 | 0x022860D4 | 1333 (0x535) |

  All sorted ascending. This **already existed** in the KB as
  `dispatch.cls_tables`, which even warns *"ALWAYS search all FOUR tables."*
- **The donor has exactly ONE record across all four tables**: `cls3[237]`
  `@0x0227B3AC` — `+00`=0x19D8, `+04`=0x02206F41 res, `+0C`=0x021FA685 cond,
  `+10`=0x021E7C3D timing. So the module's A1 (write `+04` res) is **correct**.
- **The module's real bug was A2, and it corrupted a bystander.**
  `_find_master_row` used a **fictitious** grid (`MASTER_BASE = 0x02275C08`,
  4116 rows, cid at `+0x14`). That grid starts 4 bytes into cls2 and reads its
  "cid" out of the *next* record, so every row it returned was the previous
  record's tail. A2 wrote `0x0227B3A4` = **`cls3[236]` field `+0x10`**, and
  `cls3[236]` is **cid `0x19D5` "Demise, King of Armageddon"** — it zeroed a
  bystander's timing slot and never touched the donor. **A2 is deleted**;
  `verify()` asserts Demise's record is byte-identical to the base ROM.

- ⭐ **THE SPELLCASTER RACE LOCK IS ENFORCED NATIVELY AND IS cid-KEYED**
  (user, in-game, 2026-08-03): **Book of Secret Arts (`0x10E9`) REFUSES to target
  a non-Spellcaster.** So the engine does have a per-card equip-target race gate;
  it is simply not in any table found so far. Two consequences:
  1. `0x10E9` is a free Spellcaster gate if used as the donor (keep-cid).
  2. There is now a **live, reproducible rejection** to trace with GDB — the
     cleanest possible handle on Open Question 1.
- **Book of Secret Arts IS obtainable — donor-viable.** `card_prop` ✓, name ✓,
  `card_pack.bin` row 399 = **pack 46, Common** ✓ (Trial is pack 11; Axe is pack
  1/35 Rare). Decisive: the user activated it in a duel this session.
  ⚠️ **Retraction:** I briefly claimed `card_intid = 0` made it unobtainable.
  That was a bad read — `card_intid.bin` is 12098 B (~6049 u16) for 4305 cards,
  so it is **not row-indexed** and `intid[row]` is meaningless. Axe of Despair
  and Black Pendant also read 0 there while sitting in pack 1 at Rare. Use
  `card_pack.bin` for obtainability, not `card_intid`.
- **Book of Secret Arts has ZERO cls records** (searched all four tables) — which
  is the clause-3 problem: no native ignition to inherit.

- **GDB session #2 (noise-filtered) — the race accessor is NOT the gate.** 723
  hits, 709 noise-filtered, 14 clean records. During a live Book of Secret Arts
  activation the legal Spellcaster (Pikeru `0x1757`) and the illegal
  non-Spellcaster (7 Colored Fish `0x115E`) were queried by the **same** callers
  and treated identically. Captured activation-path callers, all ARM mode:
  `0x0214ACE8` (activation), `0x0214C810` (completion), `0x0217323C` (per-hovered
  target) — each is `blx 0x0202ABB8` followed by **`cmp r0,#0x17`**.
- **RACE/TYPE CODE 23 (0x17) == SPELL.** Pinned by those three sites plus
  card_prop decoding every Spell as "Unknown(23)". KB: `equip.race_code_accessor`.
- **"Spellcaster == 18" is unsupported.** Of **101** call sites to `0x0202ABB8`
  across ov3+arm9, **none** compares the result against 18. The old
  `RACE_SPELLCASTER = 18` in `patch_wonder_wand.py` came from the same module
  that got everything else wrong — do not build a gate on it.
- **Method that works**: filter known-noise callers *without recording them* so
  the record budget survives to the interesting event. Noise set for this
  breakpoint: `0x021B8965` (field display walker), `0x02021F37`, `0x0224BFAB`,
  `0x02023465` (hand hover). Without filtering, a 60-record budget is consumed in
  1.5 s of hand-scrolling.
- **Gotcha that cost a round: LR parity selects the instruction set.** ov3 holds
  both ARM and Thumb. Odd LR = Thumb, **even LR = ARM**. Decoding an even LR as
  Thumb produces plausible garbage (`udf`, stray `movs`) instead of failing.
  KB: `tool.lr_parity_selects_mode`.

- **GDB session #3 (table probe) — INCONCLUSIVE, failed mechanically.**
  Breakpoint on the generic binary search `0x02022E44`. Two defects, both in the
  harness, not the hypothesis:
  1. ⚠️ **A stale breakpoint from session #2 was still armed.** The stub died with
     `RspError` before the `finally:` cleanup ran, so `0x0202ABB8` persisted into
     the next session and its hits were mis-parsed as table lookups (the
     "novel bases" `0x00008000`, `0x00001757`, `0x000018AB`… with absurd strides
     — their LRs are the session-#2 caller set). **A stub death leaves
     breakpoints armed; the next session MUST delete known breakpoints before
     arming anything.**
  2. The 150-record cap filled in **~50 ms** on unrelated traffic, so the window
     never reached the activation. The only genuine `0x02022E44` hits were three
     ARM9 tables — `0x0209BBDC` (count 14, stride 4), `0x0209BF10` (31, 4),
     `0x0209BDCC` (24, 4) — all called with **key = 0** from one function
     (`lr` = `0x020234B9` / `0x020234D7` / `0x02023509`). Not equip-related.
  **No conclusion may be drawn about which tables the equip gate consults** —
  the activation was never captured.

- **GDB session #4 (corrected table probe) — CLEAN RUN, and it settles the
  question.** 40,756 hits, 40,455 noise-filtered, **0 strays** (the stale-BP fix
  worked), 301 records spanning a real Book of Secret Arts activation. Every
  table consulted through the generic binary search during the activation:

  | base | geometry | what it is |
  |---|---|---|
  | 0x0226F1A8 | 97 × 4 | **LP activation-cost table** (NEW — `cost.lp_activation_table`) |
  | 0x0209BF8C | 46 × 4 | ARM9 cid→u16 map, queried constantly (unidentified) |
  | 0x0226DFB0 | 94 × 6 | equip ATK/DEF grant (known) |
  | 0x0228EFE8 | 46 × 8 | monster-only, 2 hits (unidentified) |
  | 0x0209CEF8 | 18 × 4 | monster-only, 2 hits (unidentified) |

  `0x0226F1A8` was the promising one — queried with key `0x10E9` at the instant
  of activation — but its contents are **LP costs**, not races (Cyber-Stein 5000,
  Gale Dogra 3000, Premature Burial 800, Solemn Warning 2000). Book of Secret
  Arts is **absent** from it: the activation path asks "does this cost LP?",
  misses, and continues.
- ⇒ **NO race/target table is consulted during an equip activation.** Combined
  with the session-#2 result (the race accessor treats legal and illegal targets
  identically), the gate is almost certainly **code, not data** — most plausibly
  a leaf of the big per-cid switch in the `0x021B7xxx`–`0x021B9xxx` region, which
  is exactly the construct `thumb-stack-based-switch-footgun` says cannot be
  resolved by static simulation.

## Ruled Out

- **`0x0226F628` as the equip-target gate** — real table, wrong role; no
  race-locked equip has a row, and its consumer is an FSM handler.
- **Magic Formula as a Spellcaster race-gate donor** — current text is *"Equip
  only to 'Dark Magician' or 'Dark Magician Girl'"*, a named-card gate.
- **A cid-keyed race table for equips** — Book of Secret Arts (`0x10E9`) occurs
  **exactly once** in all of ov3 data (`0x0226E02E`, the grant table). Clustering
  every race-locked equip cid across ov3 + ARM9 found no shared window other than
  the grant table itself.
- **`romfs/script/bin` in the 3DS build as an effect-script source** — it is
  scene/story script (`SC_C000_S*`), not card logic. The 3DS game also hardcodes
  effects in ARM11 `exefs/code_dec.bin`.
- **MY OWN earlier claim that A1 corrupts "Great Spirit" (`0x19F1`)** — **FALSE.**
  It came from trusting the module's fictitious master grid instead of the KB.
  `0x19F1` is `cls3[238]`, a different record that A1 never touches. Retracted
  and corrected in the module docstring.

## Open Questions

1. **Where is equip-target legality decided?** Not the grant table (no race
   field), not `0x0226F628`, not a per-card race row, and **not** the big per-cid
   switch containing `0x021B7110` — that one's grant-table use at `0x021B7088`
   binary-searches `0x0226DFB0` and merely **accumulates** ATK/DEF into
   `[sp+0xB0]` / `[sp+0xAC]`, so it is the **stat-recalc walker**. The gate is
   still unlocated, but it is now known to exist and be cid-keyed.
2. **Does OTN actually enforce Book of Secret Arts' Spellcaster lock?**
   Undetermined statically. This single fact decides the donor.
3. Clause 3: Trial's native cond `0x021FA685` is battle-destruction gated, which
   is the wrong condition for Wonder Wand — swapping it is unaddressed. `WW_RES`'s
   FSM protocol is **UNVERIFIED** and was partly inferred from the bad grid.

## Next Experiment

**Probe the TABLES consulted during the activation, not the race accessor.**
`0x02022E44` is the engine's generic sorted-table binary search
(`find(key r0, base r1, count r2, stride r3)`, KB `dispatch.sorted_table_search`).
Any data-driven equip-target gate **must** look its table up through it.

> ONE-SHOT session (per `tool.gdb_one_shot_session`): breakpoint `0x02022E44`,
> and on each hit record `r0` (key), `r1` (**table base**), `r2` (count),
> `r3` (stride) plus `lr`. Filter out the bases we already know —
> `0x0226DFB0` (equip grant), `0x0226F628` (per-cid hook), and the four cls
> tables `0x02275C04` / `0x02279D74` / `0x0227E64C` / `0x022860D4` — and record
> only **novel** bases. Then activate Book of Secret Arts and hover both a
> Spellcaster and a non-Spellcaster.
>
> Any base that appears with `key == 0x10E9` is a candidate gate table; dump it
> statically afterwards and check for a race field.

If no novel table appears, the gate is **code**, not data — in which case the
next probe is to bracket the accept/reject divergence directly: breakpoint the
activation entry `0x0214ACE8` and single-step/branch-trace the two candidate
hovers, comparing the paths.

Reusable harness: `scratchpad/probe_gate2.py` already implements the one-shot +
noise-filter + incremental-JSON pattern; change `BP` and the filter set.
⚠️ Its `race_samples` step-loop is **broken** — it single-steps and falls into
the `bl 0x0202A084` call, so it never reaches the return. Use a temporary
breakpoint at the function's `pop` instead of stepping.

## Lesson for the next session

Read `otn_enhanced/docs/engine/*.yaml` **before** reasoning from constants in a patch module.
`dispatch.cls_tables` had the correct four-table geometry the whole time; taking
`patch_wonder_wand.py`'s `MASTER_BASE`/`MASTER_COUNT` at face value produced a
confident, wrong "this patch corrupts Great Spirit" conclusion that cost a round
trip. The YAML wins.
