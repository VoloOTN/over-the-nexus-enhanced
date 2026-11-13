# Orient Dragon — findings

Session 2026-09-07. Scope: **clause 2** (the whole printed effect).
Status: **SHIPPED. IN-GAME CONFIRMED BY USER 2026-09-07, all seven oracles.**

The user's confirmation covered, one by one: deck-editor identity + Extra-Deck
residency; Polymerization refusing it; the Level-6 Synchro Summon; prompt and
**banish** on an opposing Synchro; **no prompt** when the opponent controls only
non-Synchro monsters; a Synchro on the player's own side not offered; and the
regression control that another of the 36 native trigger holders still fires.

Wired into `apply_all_patches` (step 54 of 55, WiFi timers still last) and into
`_verify_all_patches.SHIPPED`, in the same edit.

Chain build: **55/55**, no errors, target path emptied first so a silent death
could not leave a plausible artifact.
`rom_all_patches.nds` sha256 `7e3c8a149789426b1e2ce79e906863051055bca323c2120bdb76971e66822e70`.
Verify sweep: **PASS 44 / FAIL 0 / SKIP 2** (the two skips have no `verify()`).

## ⚠️ It caused one chain-only regression — caught by the sweep, now fixed

`patch_azure_eyes.verify()` FAILED on the first sweep:
`0x022658FC is still the sibling bl 0x02022E14 (the reachability anchor)`.

Azure Eyes hooks the **sibling** call `0x022658B8` in the same evaluator and
asserts `0x022658FC` is stock, as proof its own hook sits on the live
straight-line block. Orient Dragon retargets exactly that instruction.

- **Not a functional regression.** Azure Eyes' own hook, stub and every other
  check passed; only the neighbour assertion tripped. The reachability argument
  itself still holds — `CAVE_OD_TRIG` compares one cid and TAIL-CALLS the same
  `0x02022E14`, so the block and the call are intact.
- **Proven pre-existing-clean:** `patch_azure_eyes.verify()` PASSES on
  `rom_all_patches.PREV.nds` and failed only on the new one, so the cause was
  isolated rather than assumed.
- **Fix:** `_anchor_ok()` in `patch_azure_eyes.py` now accepts the stock BL *or*
  a BL to `ov5_cave.CAVE_OD_TRIG`. Deliberately NOT relaxed to "is it a BL" — the
  anchor must still prove this site calls that specific search. Re-verified
  PASSING on **both** the new and the previous ROM, so it is a widening, not a
  weakening.
- **The lesson worth keeping:** a single-card ROM cannot see this. Two patches
  hooking two `bl`s inside ONE function is invisible to either build; only the
  chain sweep catches it. Same shape as `otn-register-phantom-same-edit`.

## Description text: measured, and there is no more room

Three routes, all measured this session, all closed:

1. **In-place slack** — the gap between the donor's NUL and the next string's
   offset is 0–3 B per language (e 44→47, f 56→56, k 39→39). Not usable, and the
   safe rule is `<= original length` anyway.
2. **Dead space in the desc blob** — ~6.5 KB is unreferenced per language, but it
   is fragmented: the **longest contiguous free run is 8 bytes**. There is no
   region to repoint a `desc_off` into.
3. **Growing the blob** — `card_desc` is read into a FIXED-SIZE buffer; writing
   past a card's original slot overflows it (blank text + corruption -> freeze on
   render), and growing the *name* blob once correlated with an in-game freeze
   (`patch_boggart_knight`'s history note). Known-dangerous, not merely absent.

**But native Synchros DO carry the material line**, `\r\n`-separated — Black Rose
Dragon reads `"1 Tuner + 1 or more non-Tuner monsters\r\nWhen this card is Synchro
Summoned, ..."`. So its absence here is a real faithfulness gap, and it can be
closed for 5 of 8 languages by shrinking the effect half:

| bytes | text | fits |
|---|---|---|
| 44 | `1 Tuner + 1+ non-Tuner\r\nBanish 1 foe Synchro` | e f j r s |
| 47 | `1 Tuner + 1+ non-Tuners\r\nBanish 1 opp. Synchro.` | f r s |
| 38 | `Synchro Summon: banish 1 opp. Synchro.` (current short rung) | all 8 |

g (40), i (41) and k (39) cannot hold both halves and would keep the effect-only
rung. Pending the user's wording call.

ROM: `data/over_the_nexus/working/rom_orient_dragon.nds`
sha256 `6c8d9e4ff034119016f230beea806f2432acbdb11b37feea3ff0c69873cda18d`
(built with `--text`). **NOT wired into `apply_all_patches`** — that waits for
the user's ship approval.

### Offline regression (the one that matters)

The hook is on **every summon's path**, so the trampoline was run against the
native routine over **all 4305 cids** (`scratch/thumbemu.py` over arm9 + ov3 +
the stub blob):

| | result |
|---|---|
| cids tested | 4305 |
| donor `0x0FCB` native / stub | `0` / `1`  (wanted 0 / 1) |
| divergences excluding the donor | **0** |
| native reports member | 36 cids |
| stub reports member | 37 cids = the 36 + the donor |

So the stub changes exactly one card's verdict and leaves the other 4304
byte-identical to stock.

Printed text (`scratch/ygoprodeck_cache.json`, id 68124775):

> 1 Tuner + 1 or more non-Tuner monsters
> If this card is Synchro Summoned: Target 1 Synchro Monster your opponent
> controls; banish that target.

Lv6 / WIND / Dragon / Synchro / 2300 / 1000.

Plan: `~\.claude\plans\dazzling-plotting-moon.md` (approved, then
simplified — see "Design change" below).

---

## Design change made after the plan was approved

**`CAVE_OD_FILTER` is deleted.** Decoding prompt code `0x125` surfaced
**Synchro Ejection `0x2296`** — *"Select 1 face-up Synchro Monster your opponent
controls and remove it from play"* — whose `cls0[1191] +08 = 0x021E3F01` is
**exactly** the candidate filter the stub was going to reimplement. Using the
native address instead.

Consequence: **every slot of the new cls1 record is a native address**, and the
only injected code left in the whole patch is the ~22 B trigger trampoline.

---

## Confirmed

All verified **this session**, statically, against the committed oracles
(`ygo_tools/reference_files/nds_overlay_3.bin`, `arm9.bin`, `3ds_extract/`,
`data/over_the_nexus/working/rom.nds`). Nothing inherited from a note.

1. **Orient Dragon is not in the NDS ROM** (`scratch/cid_to_name.json`). Donor
   conversion, not a fix.

2. **3DS ships it at cid `0x2675`** (`CARD_Prop` record 4894): *"When this card is
   Synchro Summoned: Target 1 face-up Synchro Monster your opponent controls;
   banish that target."* Decoded from `CARD_Indx_E.bin` + `CARD_Name_E.bin` +
   `CARD_Prop.bin`, first u16 masked `0x3FFF`.

3. **`0x0228F6C0` × 0x24 = the "Synchro Summoned" membership list; all 36 real
   cards.** Re-read from the image. Confirms
   `summon.synchro_trigger_list_has_no_phantom`.

4. **`0x0228F6C0` has exactly ONE reference in the whole ROM** — the pool word at
   `0x02265A30`. Scanned every u32-aligned word of ov3 and ARM9. One hook at its
   consumer is therefore total coverage.

5. **The consumer / trampoline site — `0x022658FC`:**

   ```
   0x022658F6  LDRH R0, [R4, #0xE]    ; R0 = summoned card's cid   <- cid LIVE
   0x022658F8  LDR  R1, =0x0228F6C0
   0x022658FA  MOV  R2, #0x24
   0x022658FC  BL   0x02022E14        ; sorted search -> nonzero = member
   0x02265900  CMP  R0, #0x0
   0x02265902  BEQ  0x02265910        ; not a member -> no trigger
   ```
   `R4 = 0x02298A28`, loaded at `0x0226576C`. Inside the evaluator `0x02265768`.

6. **`0x02219B3D` is the field→banished resolver.** Disassembled: reads the
   declared target via `bl 0x022349B0` into `[sp]`, unpacks byte 0 → `r4`,
   byte 1 → `r6`, validates with `bl 0x0224A924(r5,r4,r6)`, then
   `bl 0x021CF43C(r5,r4,r6,0)`. `0x021CF43C` is eight instructions:
   `lsl r1,#4 ; add r2,r2,r1 ; mov r1,#1 ; lsl r1,r2 ; mov r2,#0xF ;
   bl 0x021CDD4C` = `0x021CDD4C(desc, 1 << (side*16 + zone), 0x0F)`.
   Destination `0x0F` = banished (`0x0E` = GY).

7. **A2 CLOSED — prompt `0x125` means "banish that target".** Enumerated every
   cls0–cls3 record whose `+14` thunk loads `0x125` and jumps to the board body
   `0x02234CA5`: **16 records, 16/16 banish effects** (counting the older
   "remove it from play" wording) — Dimensionhole, Interdimensional Matter
   Transporter, Dark Core, Karma Cut, Cybernetic Zone, Synchro Ejection, Caius,
   Wattpheasant, Chaos Sorcerer, BLS-Envoy, VWXYZ-Dragon Catapult Cannon,
   Destiny Hero - Doom Lord, Sky Scourge Enrise, Junk Archer, Forgotten Temple of
   the Deep, Synchro Soldier. Stronger than the KB's own standard for `0x3A` (12),
   `0x4E` (12), `0x57` (31). Control: prompt `0x64` has 65 records, all "target 1
   monster your opponent controls" with *varied* actions = the generic prompt.

8. **`0x021E3F01` = "face-up Synchro Monster your opponent controls"** — Synchro
   Ejection's `+08`:
   ```
   r3 = 0x2416 ; bl 0x021D6E40          ; side sel 2 = opponent, zone class 0x10
   cid = [0x0229AC94 + side*0xB3C + zone*0x14 + 0x34] & 0x3FFF
   bl 0x02023050(cid)                    ; is-Synchro
   ```
   Mask `0x2416` was independently derived earlier this session from the 166-hit
   rosetta scan before this record was found — two routes, same value.

9. **`0x02023050` is the engine's is-Synchro predicate**: `0x02022D70(cid)` and
   accept iff the category is in `{0xA, 0xB}`. Contrast `0x0202307C`
   (`is_extra_deck`) which also accepts Fusion's `3`.

10. **A1 CLOSED — the runtime card category, measured over all 4305 cards.**
    `0x0202ABF8(cid)` = `(u32 at card_prop record +4 >> 1) & 0x1F`. Tabulated
    against decoded `card_type`, the partition is exactly 1:1 with **zero**
    cross-contamination:

    | cat | n | card_type |
    |---|---|---|
    | 2 | 39 | Fusion Monster (the effectless pool) |
    | 3 | 108 | Fusion Effect Monster |
    | 17 | 2 | Synchro Monster |
    | 18 | 137 | Synchro Effect Monster |
    | 19 | 1 | Synchro Tuner Effect Monster |

    So `otn-hyper-librarian`'s `{17,18,19}` = Synchro is **correct**, and
    `cat == card_type >> 1`, so `card_type 5 → 37` lands exactly on cat 18.

11. **A3 CLOSED — the trigger dispatches to the cls1 table `0x022860D4`.**
    `0x02265768` contains no cls lookup at all: at `0x02265C70` it tests `R5` and,
    if nonzero, builds an event word (cid in the low half via `ORR R0,R1` from
    `[R4+0xE]`, event code in bits 25+) and posts it with `bl 0x021D3168`.
    The handler is matched later. Measured instead:
    - **all 36 trigger members own a row in `0x022860D4` — zero missing**
    - the cls1 table is **sorted by cid, zero inversions** (so a sorted insert is
      required and safe)
    - **donor `0x0FCB` currently owns zero cls1 rows** → no `find_event_handler`
      leftmost-record shadow
    - one member (Karakuri Bureido `0x2475`) owns two rows, so >1 is tolerated

12. **A4 CLOSED — `0x02022E14` is a binary search**, `(r0 = key, r1 = i16 table,
    r2 = count) -> 1 hit / 0 miss`, `PUSH {R3,R4,R5,LR}` / `POP {R3,R4,R5,PC}`.
    Clobbers r1–r5. A trampoline that preserves r0/r1/r2 and tail-calls is correct.

13. **A5 CLOSED — no per-cid gate on the donor, proven by equivalence.** The two
    cid binary-search trees on the paths this card traverses were traced with
    `scratch/thumbemu.py` over the code image:

    | tree | 0x0FCB (donor) | 0x11A3 (Accel Synchron) | 0x13C6 (Scrap Archfiend) |
    |---|---|---|---|
    | Synchro material predicates `0x022482C6` | exit `0x02023138` | exit `0x02023138` | exit `0x02023138` |
    | hand-SS / summon-restriction `0x0225E6CC` | exit `0x0225FF96` | exit `0x0225FF96` | exit `0x0225FF96` |

    The donor reaches the **identical leaf** as two donors from the same pool whose
    Synchro conversions are in-game confirmed with negative controls. The fusion
    machinery region has **zero** switch-base candidates within ±0xFF of `0x0FCB`.

14. **Donor `0x0FCB` "Gaia the Dragon Champion"** — effectless Fusion
    (`card_type` 5), Lv7 WIND Dragon 2600/2100. `donor_scan`: **1 binding**, its own
    `fusion recipe A[6] @0x02270BC4` (materials `0x0FCC` + `0x0FCD`).
    Text EN: name 24 B (need 13), desc 44 B, floor 39 across 8 languages.

15. **The whole 39-card effectless-Fusion pool has exactly one binding each** —
    its own fusion recipe row. Measured, not assumed.

16. **`CAVE_FREE = 0x0239EB50`** (`ov5_cave.py:1446`). Free ov3 dead blocks, quoted
    from `otn_enhanced/docs/engine/allocations.yaml`: `addr: 0x021B58D0 / size: 12 / used: 0`
    and `addr: 0x021B5AAA / size: 10 / used: 0` — non-adjacent, 0x1DA apart.

17. **161 phantom rows in the cls1 table**, so the count-neutral insert has choice.

---

## The build (all-native cls1 record)

```
cls1 insert for 0x0FCB, count-neutral over a phantom:
  +04 0x02219B3D   banish the declared target        (Chaos Sorcerer's; NOT
                   Synchro Ejection's 0x0222F8E5, which also draws a card)
  +08 0x021E3F01   opponent's face-up SYNCHRO monsters  (Synchro Ejection's)
  +0C 0x0224A115   standard trigger tail
  +10 0x00000000   MANDATORY -- the clause has no "You can"
  +14 0x02234E11   board target-declaration, prompt 0x125 "banish that target"
```

Plus: card_prop `card_type 5 → 37` + Lv6/WIND/Dragon/2300/1000; card_genre clear
bit 29 / set bit 36 / **not** bit 35 / keep bit 21; blank `fusion recipe A[6]`
material columns to `0x3FFF` (cid column and count 161 untouched); name/desc
ladder; and the one ov5 trampoline at `0x022658FC`.

---

## Ruled Out

- **Growing `0x0228F6C0` by bumping its `movs r2,#0x24` count.** The bytes at
  `0x0228F708` are *another sorted cid list* (`0x0D5D 0x0D62 0x0D6B 0x0DAD …`),
  not padding. Worth checking — it would have been pure data and puzzle-safe.

- **Reptilianne Hydra `0x211D` as donor.** Printed text is
  **`1 "Reptilianne" Tuner + 1 or more non-Tuner monsters`** — a named-material
  restriction. I had asserted "generic materials" from recall earlier in the
  session; reading `ygoprodeck_cache.json` corrected it. Also in **three** set-code
  lists (thunks 32/78/84 of `0x0209D0D8`).

- **Elemental HERO Gaia `0x1FBA` as donor.** Mechanically excellent (its
  `cls1[973]` already has the matching trigger, `+08 = 0x021DEA55` mask `0x0416`,
  and mandatory `+10 = 0`). Rejected by the user in favour of effectless-Fusion +
  trampoline. Also carried a `Must be Fusion Summoned` nomi clause and membership
  in the 58-entry HERO set-code list (thunk[8] `@0x0209CFE4`).

- **Every Lv6 Synchro in the trigger list as donor.** `0x2164`/`0x22D3`/`0x211D`
  named-material; `0x21CF` X-Saber gated; `0x1F95` 11 bindings; `0x24B3` spent by
  Junk Speeder.

- **`summon.synchro_trigger_list_has_no_phantom`'s "Fusion members (card_type 7)
  are unusable as a SYNCHRO donor".** Stale — corrected by
  `carddata.fusion_donor_is_a_synchro_donor` and demonstrated in-game by
  `card.jet_warrior` (2026-09-04). Needs a `corrected_by:` in the KB.

---

## Open Questions

- **Prevention Star `0x1F68` cls2[412] uses the banish resolver `0x02219B3D`** but
  its TCG text does not banish. Either OTN's implementation diverges or the
  resolver is parameterised by something unread. Does not block the build (16/16 on
  the prompt population and 6/7 on the resolver population), but it is the one
  loose thread.

- Whether `+04 = 0x02219B3D` behaves identically in a **cls1** record — it is
  currently used only from cls0/cls2/cls3. Structural precedent is good: E-Hero
  Gaia's `cls1[973]` uses the same slot5-declares → resolver-reads pattern
  (`+14 = 0x02234D99`). To be checked by the in-game oracle.

---

## Next Experiment

Build. All five blocking assumptions are closed; nothing is left to prove
statically. Order:

1. Write `patch_orient_dragon.py` (conversion parts from `patch_accel_synchron.py`,
   cls1 insert + trampoline new).
2. `assert_thumb1_only` + disassemble the built trampoline; the `0x02022E15`
   literal must have **bit 0 set**.
3. `_build_orient_dragon.py` → `rom_orient_dragon.nds`, `verify()`.
4. Offline: trampoline returns 1 for `0x0FCB` and the native verdict for a sample
   of other cids (the regression guard for every other summon in the game).
5. Hand to the user for the in-game oracle list in the plan — including the
   **regression control** that another of the 36 (e.g. Black Rose Dragon) still
   fires its own Synchro-Summon trigger.
