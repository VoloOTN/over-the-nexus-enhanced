# Accel Synchro Stardust Dragon — findings (live)

Session 2026-09-14. Recon for C0–C3, then **C0 + C1 built** (single-card ROM, not the chain). Plan:
`~\.claude\plans\accel-synchro-stardust-dragon-immutable-eich.md`.

Printed text (`scratch/ygoprodeck_cache.json` id 30983281, grepped this session):

```
Accel Synchro Stardust Dragon   Synchro / WIND / Dragon / Lv8 / 2500 / 2000
1 Tuner + 1+ non-Tuner monsters
If this card is Synchro Summoned: You can Special Summon 1 Level 2 or lower Tuner
from your GY. During the Main Phase (Quick Effect): You can Tribute this card;
Special Summon 1 "Stardust Dragon" from your Extra Deck (this is treated as a
Synchro Summon), then, immediately after this effect resolves, Synchro Summon 1
Synchro Monster using monsters you control as material. This turn, the monsters
Synchro Summoned by this effect are unaffected by your opponent's activated
effects. You can only use each effect of "Accel Synchro Stardust Dragon" once per turn.
```

| # | Clause | Status |
|---|---|---|
| C0 | 1 Tuner + 1+ non-Tuner (identity) | **in-game confirmed by user 2026-09-14** (oracle 1) |
| C1 | If Synchro Summoned: SS 1 Lv<=2 Tuner from GY, OPT | **in-game confirmed by user 2026-09-14** (oracles 2–7) |
| C2 | Main Phase Quick: Tribute self; SS "Stardust Dragon" 0x1E36 from ED (as Synchro Summon), OPT | **in-game confirmed by user 2026-09-14** (oracles C2-1..C2-8) |
| C3 | then immediately Synchro Summon 1 Synchro using monsters you control | **in-game confirmed by user 2026-09-14** (test 2, build bb2a0929...) |
| C4 | unaffected by opponent's activated effects this turn | **DROPPED by user 2026-09-14** ("Actually just drop the 'activate effects' clause") |

User decisions 2026-09-14: donor = **effectless Fusion**; C3 follow-up Synchro is
**mandatory if able** (no Yes/No prompt).

## Confirmed

### KB health at session start
`verify_knowledge` -> **473 facts: 435 PASS, 0 FAIL, 38 UNVERIFIED**, oracles
arm9/ov3/ov5 yes, savestate rom_all_patches.ml2.

### KB contributions (this session) — `author_facts --check`: 478 facts, 440 PASS, 0 FAIL, 38 UNVERIFIED
- VERIFIED `resolver.synchro_summon_resolver_phases` (0x02249EC0)
- VERIFIED `resolver.cyberstein_extra_deck_summon_flag_zero` (0x0220AF0C)
- VERIFIED `resolver.gy_revive_default_leaf` (0x02207190)
- VERIFIED `resolver.main_phase_either_turn_condition` (0x021F4EC0 vs 0x021F1490)
- VERIFIED `summon.ss_placed_before_next_resolver_phase` (0x02207528) — replaced the
  UNVERIFIED `summon.ss_engine_placement_is_deferred` written earlier this session.

### ⭐ C3 precondition CLOSED WITHOUT GDB — Call of the Haunted relies on it
User prompt (2026-09-14): *"Does Cyber-Stein need the test? Shooting Quasar and
Shooting Stardragon can summon from the Extra Deck, so can Starlight Road."*
- Starlight Road 0x21A1 resolver 0x0222DFFC: SS_FROM_EXTRA at phase 0x7E then
  `movs r0,#0` — **no later phase**, so it could not answer the question.
- **Premature Burial 0x1366 cls0[241] / Call of the Haunted 0x137D cls0[248]** share
  resolver `0x02207528`. Phase 0x80 summons via `0x02204730` (-> SS_ENGINE
  `0x0226925C` @0x0220486A) and returns **0x7F**. Phase 0x7F:
  ```
  0x022075f8 bl 0x02234964 ; 0x022075fc bl 0x021A241C   ; find summoned instance
  r6 = (ret >> 8) & 0xFF                                ; its SLOT
  0x02207610 cmp r0,#5 ; 0x02207614 blo -> link/equip   ; only if in a MONSTER ZONE
  ```
  `0x021A241C` walks both players' slots 0..10 at `0x0229AC94 + side*0xB3C + 0x34 +
  slot*0x14` (literals @0x021A2478/C) and returns `(slot<<8)|side` or -1.
- Call of the Haunted links its target in the retail game, so **the summoned
  monster is on the field when the resolver's next phase runs**. C2's wrapper can
  hand off to 0x02249EC0 in the phase after its summon. **The GDB experiment is
  cancelled.**
- Residual difference: CotH summons from the GY, ours from the Extra Deck; both go
  through the same SS_ENGINE 0x0226925C, so the placement machine is the same.

⚠️ **Tension with `resolver.phase_protocol`'s scope limit** (Maiden measured
`[0x0229AAFC+0x70] == 1` on every cls3 slot1 entry): TWO native cls3 records —
Formula cls3[730] -> 0x02249EC1 and Cyber-Stein cls3[48] -> 0x0220AF0D — dispatch on
+0x70 with 0x80..0x7D arms, and Steam Synchron's in-game confirmation ran through
the first. Unresolved, but it is Konami's own cls3 usage; it will be exercised by
the C2 in-game test.

### Not in the 3DS build
`CARD_Name_E.bin` (UTF-16LE) has no "Accel Synchro Stardust Dragon" (controls
"Junk Synchron", "Dragunity Knight - Barcha" found). NDS is the only source.

### C0 donor survey — all 39 effectless Fusions (card_type "Fusion Monster")
Script `scratchpad/fusion_donor_survey.py` (donor_scan.cards()/scan() over
`reference_files` ov3+arm9; CPU-deck usage by NAME in `working/deck.json` —
positive control "Stardust Dragon" = 149 hits, so the count works).
**Name/desc budget is NOT a constraint**: a cid added to `card_text.CARD_TEXT`
takes the INDEX-ORDER RE-EMIT (card_text.py:874), as Orient Dragon 0x0FCB
(card_text.py:74) and Accel Synchron 0x11A3 (:123) already do.

Cleanest (binding=1 = only its own fusion-recipe-A result row, advisory=0, 0 CPU
decks, no shipped-patch reference except patch_bulk_card_pack name rows):

| cid | card | Lv/Attr/Race | binding | advisory | decks |
|---|---|---|---|---|---|
| **0x126F** | **Meteor B. Dragon** | L8 FIRE Dragon | recipe A[52] | 0 | 0 |
| 0x1127 | Bickuribox | L7 DARK Fiend | recipe A[23] | 0 | 0 |
| 0x120B | Twin-Headed Thunder Dragon | L7 LIGHT Thunder | recipe A[47] | 0 | 0 |
| 0x1160 | Aqua Dragon | L6 WATER Sea Serpent | recipe A[28] | 0 | 0 |
| 0x1179 | Crimson Sunbird | L6 FIRE Winged Beast | recipe A[31] | 0 | 0 |

Spent: 0x11A3 (accel_synchron), 0x0FCB (orient_dragon), 0x13C6 (scrap_archfiend).
Rejected: 0x107F B. Skull Dragon (6 advisory ARM9 hits), 0x0FEB Thousand Dragon (5),
Giltia / Kaminari Attack (in CPU decks). `donor_scan` cannot see base+-imm switches.
**DONOR APPROVED BY USER 2026-09-14: Meteor B. Dragon 0x126F** ("Okay use Meteor B Dragon.").

### C1. Revive resolver 0x02207190: every top donor reaches the GENERIC body
Disassembled this session (`scratchpad/thd.py`, reference ov3). Register-based
per-cid tree over `ldrh r1,[r6]` with r4=1, r5=2 preset; arms set r5=1 (e.g. Junk
Synchron 0x1E07, "in Defense Position"), r5=0, or r4=0; all fall into
```
0x022072da  adds r0,r6,#0 ; adds r1,r4,#0 ; adds r2,r5,#0
0x022072e0  bl   0x02204730          ; generic revive (desc, r4, r5)
```
Path for cid 0x126F (and 0x1127, 0x120B — all < 0x14F7):
```
0x0220719c cmp r1,#0x1F7C  bgt/bge not taken
0x022071a4 cmp r1,#0x1A58  bgt/bge not taken
0x022071ac cmp r1,#0x14F7  bgt/bge not taken
0x022071b4 cmp r1,#0x0DB4  beq not taken -> b 0x022072da   (r4=1, r5=2)
```
Malefic Paradox 0x22A3 (plain "Special Summon it", no position) also reaches the
default (0x22A3 > 0x2147 -> cmp 0x2219 ne -> 0x022072da), so r4=1/r5=2 is the
no-position-clause leaf == our printed text. **No per-cid arm needed.**

### C1. Trigger hook is owned by a SHIPPED card -> must become a shared register
`patch_orient_dragon` is in `otn_enhanced/steps.py` and
`apply_all_patches.py` (grep this session). Its hook `bl 0x02022E14` @0x022658FC is
the ONLY reader of list 0x0228F6C0 (its docstring: sole pool word 0x02265A30), and
its stub `CAVE_OD_TRIG` (patch_orient_dragon.py:190-201) compares ONE cid
(`ldr r3,=0x0FCB; cmp; beq hit; else blx NATIVE_SEARCH|1`). A second cid costs
+10 B and the reserve is 0x20.
**Design:** new `finished_patches/synchro_trigger_hook.py` in the shape of
`summon_rider_hook.py` (hook + stub + `CIDS` register), new ov5 slot, BL retargeted;
patch_orient_dragon delegates to it. **Proof by execution:** run the stub in
`scratch/thumbemu.py` for every one of the 36 list members, both donors, and a
sweep of non-member cids; assert result == native search except donors == 1.

### C2. Cyber-Stein's resolver 0x0220AF0C = a generic 4-phase ED summon; flag built in ONE place
Disassembled this session. Dispatch on `[0x0229AAFC+0x70]` (jump table 0x7D..0x80, 0x64):
```
0x80 @0x0220af36: 0x021B9ECC(side) may-SS ; 0x021AD870(side) zone ; ED count
                  [0x0229ACAC + (side&1)*0xB3C] != 0 ;
                  param=0x02234E78(desc) ; 0x02243FA8(side, cid, param)
                  -> 0: msg 0x122, return 0x64 ; else msg 0x1A, return 0x7F
0x7F @0x0220af94: 0x0219C430(side, 6, cid, 0x02234E78(desc)) picker -> 0x7E
0x7E @0x0220afa8: r6 = pos (2; 1 for 0x0E42, 0 for 0x114A)
                  r1 = 0x0219C510() ; [sp] = cid<<16  (lsls r0,r5,#16 -> FLAG 0)
                  0x0226925C(side, sel, 1, pos)  -> 0x7D
0x7D @0x0220afd8: cid 0x0E42 only: attach rider ; return 0
0x64 @0x0220affe: 0x0225BF3C(1-side) ; return 0
```
The ONLY per-cid code is the two position arms and the 0x0E42 rider; 0x126F gets
pos 2 and no rider. **So C2 = an ov5 wrapper: phase 0x7E replays the 8-instruction
body with `[sp] = (cid<<16)|1`; every other phase tail-calls 0x0220AF0D.** Its
candidate test reads the cid's criteria row -> C2 row = Starlight Road's
`{cid, 0x1E36, 0x022423C9, 0x0802}` (handler not re-disassembled yet).

### C2. Conditions, disassembled this session
- `0x021F4EC0` (Embodiment of Apophis): `[0x0229DD14+0x48]` in {2,4} else 0;
  then `bl 0x021F6EA4`. NO turn test -> either player's Main Phase.
- `0x021F1490` (Formula): turn-log scan for desc[+0xC] -> `[0x0229DD14+0x34] ==
  1-desc[+2]` (OPPONENT'S turn) -> phase {2,4} -> `0x021F97F4`.
- `0x021F90E0` (Kaibaman): `0x021AE130(side,side,zone)` -> `0x021F0114(desc,side)`
  OR `0x021AD488(side,zone)` (the zone the tribute frees) -> `0x021B9ECC(side)` ->
  `0x0224401C(desc) > 0` (criteria-row candidate count). cid-blind.
=> C2 condition stub = phase{2,4} head + desc[+7]-guarded turn-log query + tail
`0x021F90E0`.

### C2. Spell-speed-2 list 0x0209C118 — free phantom = **0x0E82**
`scratchpad/qe_phantoms.py`: count insn @0x02023490 = `0x2276` (movs r2,#0x76);
sorted in stock AND `rom_all_patches.nds`. Ledger claims: 0x0E5B accel_synchron,
0x1A86 maiden, 0x1774 steam. Chained-image phantoms: 0x0E63, 0x0E64 (Infernity set
code), 0x0E6B, 0x0E6C (T.G. set code + rows), **0x0E82 (cls3[32] + fusion recipe
A[0] result only; claimed in NO pool)**, 0x0EB2 (grapha spends it in
gy_action_registry), 0x1529, 0x1534 (cls/criteria rows).

### C3. Synchro resolver 0x02249EC0 — phase map, disassembled this session
```
entry: r6 = desc[+2] ^ desc[+6]
0x80 @0x02249efe: cid 0x1EF0 only: Battle Phase gate
                  0x021B9EF0(side) ; 0x021F05A8(desc, r1) candidate probe
                    (= 0x02243FE0(r6, cid, 0x02234E78(desc)) >= 1)
                  hit  -> 0x0219A818(r6, 0x11D) MESSAGE, return 0x7F
                  miss -> field walk; for non-0x1EF0 checks the SOURCE is still at
                          desc[+3] with instance desc[+0xC]; -> 0 or msg 0x122/0x64
0x7F @0x0224a02a: 0x0219C430(r6, 6, cid, 0x02234E78(desc)) picker -> 0x7E
0x7E @0x0224a03e: summon record 0x02298A28: +2/+0 = r6, +0xE = picked cid,
                  +0xC = instance ; +0x24 = 0 -> 0x7D
0x7D @0x0224a076: r = 0x02263494() ; r>0: 0x02269320(r6, [+0xC], 2, 0), return 0
                  r==0: return 0x7D ; r<0: return 0x80
```
- **0x11D is a message (0x0219A818 is also the 0x122 "no target" call), not a
  Yes/No.** Formula/Urgent Tuning are natively MANDATORY -> matches the user's
  "mandatory if able" with zero extra code.
- **0x7D -> 0x80 re-entry is native** (`blt` at 0x0224a0b0) — a resolver jumping back
  to phase 0x80 is Konami's own pattern, so C2's wrapper can end C2 at its 0x7D by
  setting a STAGE byte and returning 0x80, then route phases 0x80..0x7D to
  0x02249EC1.
- The source-still-on-field check only runs on the no-candidate path; a tributed
  source there just returns 0 / msg 0x122 (fizzle), no crash path seen.
- Formula/Urgent Tuning print "Immediately after this effect resolves" and implement
  it INSIDE the resolver, so doing C3 inside our resolver is Konami's NDS
  realization, not a deviation.

### C2/C3/C1 need THREE criteria rows -> one arm in the shipped criteria_row_hook
`criteria_row_hook.py` docstring: row = leftmost + r4, r4 forced 0 (or 0/1 via LIST A
+ param) — max 2 rows by data. Registered arms key on the ACTING DESCRIPTOR
`[0x0229A9FC+0x50]` (desc[+5] = record class). Proposed arm for the donor:
desc[+5]==1 (cls1, C1) -> row 0 ; desc[+5]==3 -> row 1 + STAGE (C2 row 1, C3 row 2).
Rows inserted in order AFTER each other (param-provider note: a natural sorted
insert swaps same-cid rows).

## UNVERIFIED — inherited from this session's precedent sweeps (re-prove before use)

- C0: Fusion->Synchro Effect conversion = card_prop copy of Laval Twin Slayer 0x23FE
  (type 37) with cid swapped, genre `0x0000001000200000`, recipe m1/m2 = 0x3FFF
  (`patch_orient_dragon.py`, `patch_accel_synchron.py`).
- C1: trigger list `0x0228F6C0` (36 x u16, no phantom, cannot grow), evaluator
  `0x02265768`, cls1-only. Orient Dragon trampoline on `bl 0x02022E14` @0x022658FC,
  28 B stub `CAVE_OD_TRIG 0x0239EB50` in a full 0x20 slot.
- C1 record shape: cls1 `{0x02207191, 0, 0x021F03B5, 0x021E51E5, 0x02235605}`
  (Malefic Paradox 0x22A3) + criteria `{cid, FFFF, 0x0223C9D1, 0x00898002}`
  (Junk Synchron Lv byte 0x89 + Tuner bit 15; combination not native).
- C2: Kaibaman cls3[201] `{0x0220667D, 0, 0x021F90E1, 0x021E50CD, 0}`; tribute
  cost tag `0x021E50CD`; Starlight Road named-ED row `{aux 0x1E36, 0x022423C9, 0x0802}`;
  SS_ENGINE `0x0226925C` writes `[0x02298A28+0x10] = arg|4`, bit 0 = proper summon;
  Quasar PART M `SS_FROM_EXTRA 0x02269314` with `(cid<<16)|1`; spell-speed-2 list
  `0x0209C118`; Apophis phase-only condition `0x021F4EC1`; zone-keyed OPT
  (0x021F0B71/0x021E5061) is USELESS for a self-tribute -> cid turn-log pair
  0x021D2584/0x021A14E8 stamped in cost slot (Mystic Piper).
- C3: resolver `0x02249EC0` phases 0x80 (prompt 0x11D) -> 0x7F (picker) -> 0x7E
  (write summon record) -> 0x7D (commit 0x02269320). Urgent Tuning 0x1EF0 row 786
  `{FFFF, 0x02240EF5, 0x0802}` = "monsters you control"; Formula's `0x0223D21D`
  forces "this card".

## Ruled Out

- **Zone-keyed once-per-turn (0x021F0B71 / 0x021E5061) for C2** — keyed on
  (side, zone); the tribute cost empties the zone at activation, so the stamp dies
  with it. (Sweep reasoning, patch_sea_lancer.py:236-241; not yet re-read.)

## Open Questions

- ~~Is Stardust Dragon on the field when C3's phase 0x80 probe runs?~~ **CLOSED**
  by Call of the Haunted's resolver (see Confirmed). No GDB needed.
- **Does `[0x02298A28+0x10]` bit 0 do anything besides the proper-SS trigger list?**
  KB documents only that consumer (`summon.trigger_is_a_membership_list`). Whether a
  later revive checks "properly summoned" is unmeasured.
- STAGE byte lifecycle: the row arm reads it at condition time too (0x0224401C), so
  it must be 0 outside C3 — clear it on C3's final return AND in C2's cost stub.
- C1 once-per-turn: Junk Speeder / Jet Warrior turn-log cond pair (`CAVE_JW_C1_COND`)
  not yet re-read.
- C2 row handler `0x022423C9` (Starlight Road) not re-disassembled this session.

## Next Experiment

### Offline evidence gathered on the SS-commit timing (this session)
`0x0226925C` writes summon record 0x02298A28 fields +0,+2,+6,+8,+A,+C,+E,
+0x10 (`arg|4`),+0x12,+0x22,+0x2C,+0x2E — **never +4 (zone)** — then `bl 0x02269084`,
which zeroes +0x24..+0x2A, sets **state `+0x1E = 1`** and posts a UI command
`0x0219EA84(0x13, -1, sp, ...)`. So the card is placed by a MULTI-FRAME state
machine, not synchronously. Cyber-Stein's phase 0x7D reads `[0x02298A28+4]`, which
suggests the resolver loop is not re-invoked until that machine has at least
chosen the zone — **suggestive only, not proof that the monster is on the field.**
Also seen: `[sp+0x18] & 0x10` flips the destination controller (`eors r0,r5` ->
+0); so the flag word's bit 4 = "on the opponent's field", bit 0 = proper summon.

### ~~GDB experiment (Cyber-Stein bp 0x0220AFD8)~~ — CANCELLED 2026-09-14
Superseded by the Call of the Haunted proof (`summon.ss_placed_before_next_resolver_phase`).

### C0 + C1 BUILD (2026-09-14) — ALL 7 ORACLES IN-GAME CONFIRMED BY USER 2026-09-14
User's report, verbatim: "1. Confirmed 2. Confirmed 3. Confirmed 4, Confirmed 5. Confirmed
6. Confirmed 7. Confirmed" — on the sha256 below, first test. NOT shipped: not in
steps.STEPS / SHIPPED (user has not approved shipping).
`_build_accel_stardust.py`: clean -> patch_orient_dragon (regression partner) ->
`patch_accel_synchro_stardust_dragon`. Output `data/over_the_nexus/working/rom_accel_stardust.nds`,
129,528,968 B, **sha256 `12cd1e3f63aee8081dd0b9f516678e938b1b867319b951938660dd68eef461c1`**,
BUILD_EXIT 0. Our verify 18/18 PASS, Orient Dragon verify all ok, trigger stub proven BY
EXECUTION (thumbemu over the installed bytes: 12/12 verdict x cid cases, sp/r4 preserved).
Stats decoded from the ROM: Synchro Effect Monster / WIND / Dragon / Lv8 / 2500 / 2000.
Built stubs disassembled: every pop returns via pc, every blx literal odd.

**Design change vs the plan (for the better): NO lift of Orient Dragon's hook.** Our BL
sits on the membership VERDICT `cmp r0,#0 ; beq` @0x02265900, one instruction after
Orient's hook @0x022658FC, so the shipped module is untouched and both compose in either
order (KB `summon.proper_ss_list_verdict_site`, VERIFIED).

Claims: donor 0x126F; cls1 phantom 0x1280; criteria phantom 0x14BA; ov5
CAVE_ASSD_TRIG 0x0239F0A0 / CAVE_ASSD_C1_COND 0x0239F0C0 / CAVE_ASSD_C1_SLOT4
0x0239F0F0 (CAVE_FREE -> 0x0239F120). check_allocations OK.
Records: cls1 `{0x126F, 0, 0x02207191, 0, COND|1, SLOT4|1, 0x02235605}`; criteria
`{0x126F, 0xFFFF, 0x0223C9D1, 0x00898002}` (Junk Synchron Lv<=2 byte | Scrap Chimera
0x22F6's Tuner bit — Scrap Chimera = "SS 1 'Scrap' Tuner from your GY", word
0x00018002 on the set-code sibling 0x0223C9ED).
OPT = Jet Warrior C1 shape (turn-log query in +0C, post in +10 on "yes") + a
desc[+5]==1 timing arm (`tch.ARM_JW`). **ponytail:** the module installs the shared
timing stub with ONLY its own arm; at ship, add the arm to `timing_class_hook.ARMS`.

⚠️ SHIP-TIME TODO: `timing_class_hook.ARMS` entry; STEPS after orient_dragon; SHIPPED list;
re-check criteria-row index anchors of shipped modules (the insert shifts rows between the
donor's slot and 0x14BA's old index 156).

### C2 BUILD (2026-09-14) — ALL 8 ORACLES IN-GAME CONFIRMED BY USER 2026-09-14
User's report, verbatim: "1. Confirmed 2. Confirmed 3. Confirmed 4. Confirmed 5. Confirmed
6. Confirmed 7. Confirmed 8. Confirmed" — on sha256 6f107e44..., first test. Still NOT shipped.
Also closes the `resolver.phase_protocol` cls3 tension for THIS resolver: the wrapper's
`[0x0229AAFC+0x70] == 0x7E` gate fired from a cls3 record (Stardust was summoned).
Same `_build_accel_stardust.py` (clean -> orient_dragon -> this module), same OUT path.
**sha256 `6f107e4490329a3414fa4354633596419bd7f1e91b93b1dfcf4287acec227adf`**, BUILD_EXIT 0.
verify 27/27 PASS; Orient verify ok; trigger stub 12/12 by execution; **row arm 5/5 by
execution** (donor + cls3 -> tail 0x02243EEE r4=1; donor cls1/cls2, other cid, null desc ->
native resume 0x02243BF0 with r0=cid, r1=LIST_A literal, r4 untouched). C2 stubs disassembled,
all pool targets odd.

| part | what | evidence |
|---|---|---|
| H cls3 | `{0x126F, 0, RES|1, 0, COND|1, COST|1, 0}` over phantom 0x14B9 (span 53..85) | `resolver.cyberstein_extra_deck_summon_flag_zero`, Kaibaman cls3[201] |
| RES 0x0239F120 (60 B) | phase != 0x7E -> `bx 0x0220AF0D`; 0x7E -> sel 0x0219C510, `[sp]=(cid<<16)|1`, SS_ENGINE(side, sel, 1, pos 2), return 0x7D | disasm of 0x0220AFA8 this session |
| COND 0x0239F160 (68 B, reserve 0x50) | phase {2,4} -> desc[+7] guard -> turn-log (side,0xB,0x126F,kind 2) -> 0x021F90E0 | `resolver.main_phase_either_turn_condition`, Mystic Piper |
| COST 0x0239F1B0 (36 B) | post (side,0x126F,2,0) -> Tribute tag 0x021E50CC | Mystic Piper (kind 2 so C1's kind-1 latch stays independent, Jet Warrior precedent) |
| I criteria row 1 | `{0x126F, 0x1E36, 0x022423C9, 0x0802}` after C1's row, phantom 0x1445 | Starlight Road row 1075; handler = ED builder 0x0223BE40 flags 8 + named filter 0x0223C6F1 |
| J row arm | acting desc[+5]==3 -> r4=1 | Darkflare's discriminator; Accel Synchron C3 confirms a cls3 picker reads through the hook |
| K QE list | 0x0E82 -> 0x126F | Accel Synchron PART L helpers |

CAVE_FREE -> 0x0239F1E0. ponytail: shared row stub installed with ONLY this arm (as the timing stub).
Oracle: `_build_accel_stardust.py` docstring, C2-1..C2-8.

### C3 BUILD (2026-09-14) — static PASS, AWAITING IN-GAME TEST
**sha256 `4597f109401235d271f486e6e4f4cdb847987e45509a6da9213e796db58f074c`**, BUILD_EXIT 0.
verify all PASS; Orient verify ok; trigger 12/12, **row arm 7/7** (cls3: row 1 + STAGE; cls1/cls2,
other cid, null desc -> native), **C3 dispatcher 8/8** by execution (STAGE 0: 0x80/0x7F/0x7E ->
confirmed C2 stub; 0x7D -> STAGE=1, return 0x80. STAGE 1: resolver called with r0/r1 intact, its
return passed through, STAGE cleared only on 0). Dispatcher disassembled; STAGE ships 0.

- cls3 +04 -> CAVE_ASSD_C3_DISP 0x0239F1F0 (60 B); STAGE data CAVE_ASSD_STAGE 0x0239F1E0 (4 B).
  The in-game-confirmed C2 stubs are byte-identical and at the same addresses.
- criteria row 2 `{0x126F, 0xFFFF, 0x02240EF5, 0x0802}` (Urgent Tuning; handler disassembled this
  session: ED enumerator flags 0x24, r2=r3=0 = NO this-card filter, vs Formula 0x0223D21C which
  passes callback 0x0223D205) over phantom 0x0EBE.
- CAVE_FREE -> 0x0239F230.
- ponytail: STAGE not cleared in C2's cost (stale 1 needs a resolution that never returns 0; ov5
  reloads per duel).

Oracle: `_build_accel_stardust.py` docstring C3-1..C3-6 + one OBSERVE item (does a C3-summoned
Orient Dragon's own trigger fire?).

### ❌ C3 TEST 1 (sha 4597f109...) — FAILED at material selection
User, verbatim: "1. See .ml3, I am unable to select material for my Synchro summon. It let me
choose a monster to Synchro summon see: .ml4 but once I select something it isn't happy."
Clarified: "(a)" = the material cursor won't select any monster.
Board (parsed from rom_accel_stardust.ml3/.ml4, identity: C3 dispatcher bytes in RAM == build):
Stardust Dragon [slot 2], Dragunity Phalanx (Lv2 Dragon Tuner) [slot 3]; pick = Trident Dragion
0x2003 (Lv10, "1 Dragon-Type Tuner + 1+ non-Tuner Dragon-Type") -- a LEGAL Synchro. STAGE=1,
phase 0x7D, acting desc = our cls3 (cid 0x126F, +C instance 0x58).

**ROOT CAUSE (proven):** Synchro resolver phase 0x7D @0x0224A076:
`if 0x02029E60(desc cid) && [0x02298A28+0x24]==1 && [0x0229ABFC+0x7C]==0: [0x0229AC7C] = desc[+0xC]`
= Formula's "using THIS card" FORCED MATERIAL. `0x02029E60(cid)` = bit 0x8000 of
`0x02029E1C(cid)`; true for 0x126F, false for Urgent Tuning (a Trap). Savestate: `[0x0229AC7C] =
0x58` in both states = the TRIBUTED card's instance -> no material is ever legal.
**Measured** (thumbemu over .ml3 + a Python hook for ARM idiv 0x020989A4, scratchpad/c3_validator.py):
validator 0x02249AFC(0,0,slot 3 Phalanx) -> **0 with forced=0x58, 2048 with forced=0**.
`0x0224B9F0` (poll phase 1) only STORES picker config (mode 8, validator at 0x0229DE14+0xC), and
0x0229AC7C is read LIVE by the validators (0x0224967A/0x022496E2/0x0224970A) -> clearing it after
the resolver call, before any filtering, is sound.

**FIX:** C3 dispatcher writes 0 to 0x0229AC7C after every Synchro-resolver call (STAGE==1).
KB `synchro.effect_summon_forced_material_global` (VERIFIED, proof passes; 480 facts / 442 PASS).

### 🚢 SHIPPED 2026-09-14 (user: "All confirmed. Ship!")
- Arms moved into the SHARED registers: `timing_class_hook.ARMS` (0x126F, ARM_JW verbatim) and
  `criteria_row_hook.ARMS` (ARM_ASSD: cls3 -> rel 1 + CAVE_ASSD_STAGE). Module now calls
  `tch.install` / `crh.install` / their `verify`.
- Lift proven BY EXECUTION: `scratch.timing_hook_equiv` 195,840 inputs (only 0x224C/0x23EB/0x126F
  differ vs the pre-lift stub; 0x126F's 2448 == Jet Warrior's identical-arm count) and
  `scratch.rowhook_equiv` 63,360 inputs incl. the new STAGE dimension (only 0x126F differs; LP, DF,
  UGN, JS, Accel Synchron unchanged). Stubs 112 B / 244 B, both <= 0x100.
- `steps.STEPS` step 62/63 (above WiFi) + `_verify_all_patches.SHIPPED`. Not apply_all_patches.
- Single-card rebuild (shared stubs): BUILD_EXIT 0, sha256 e2bf5f0a...1268b1, all exec proofs PASS.
- **EE fast build: 63/63 steps**, `rom_all_patches.nds` sha256
  `5e15090d856f0c9c47a5e67f29d41ded27260204a8136b63e67e2a67b98f7997`, exit 0.
- **Verify sweep: 51 passed, 0 failed** (incl. lightpulsar, darkflare, jet_synchron, jet_warrior,
  accel_synchron, orient_dragon, this card).
- `equiv --all`: `[DIFFERS] patch_bulk_ydcs file 61 @+0x180C` -- PRE-EXISTING, byte-identical to the
  diff notes/kuribandit-findings.md:113 recorded before this session; step 2, neither module
  touched; stops the run. Other migrated modules not re-run individually (none installs the
  shared hooks this ship changed). `equiv --self` crashes in the harness (missing work file) --
  separate, unrelated.
- ⚠️ Still open (not blocking): whether a C3-summoned monster's own "when Synchro Summoned" trigger
  fires was never reported.

### C3 BUILD 2 (2026-09-14) — IN-GAME CONFIRMED BY USER 2026-09-14
User, verbatim: "All confirmed. Ship!" — on sha256 bb2a0929..., the retest checks 1–4.
**The user approved SHIPPING** in the same message.
**sha256 `bb2a09299e4dc9904e903d77537f7b4e842a690e89c1221829896b6196ffc691`**, BUILD_EXIT 0.
Only change: CAVE_ASSD_C3_DISP (now 72 B, reserve 0x50; CAVE_FREE -> 0x0239F240) zeroes
0x0229AC7C after each resolver call. Dispatcher exec proof 8/8 incl. forced-material 0x58 -> 0 on
every STAGE-1 path and untouched on STAGE-0 paths. Everything else byte-identical to build 1.

### In-game oracle (from the build script docstring)
1. Card reads Accel Synchro Stardust Dragon, WIND/Dragon/Lv8/2500/2000, Synchro frame, Extra Deck.
2. Synchro Summon it (1 Tuner + 2 non-Tuners, total 8) -> optional prompt.
3. Picker offers ONLY Lv<=2 TUNERS from your GY (not a Lv3 Tuner, not a Lv2 non-Tuner).
4. Declining summons nothing.
5. Second Synchro Summon of it the same turn -> NO prompt.
6. NEGATIVE: Monster Reborn it -> NO prompt.
7. REGRESSION: Orient Dragon's banish trigger still fires.
