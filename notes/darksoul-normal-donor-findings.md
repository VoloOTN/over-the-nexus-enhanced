# XX-Saber Darksoul — re-home onto a Normal-Monster donor (2026-09-08)

Task: `patch_darksoul` cannibalises **Deep Diver 0x1CE6** (a real Effect Monster)
*and* **steals Manticore of Darkness 0x16F9's** native End-Phase registry row.
Move it to a records-free vanilla, the way `patch_boggart_knight` was moved on
2026-09-08, using the already-shipped T.G. Striker / Warwolf E2 recipe.

**Status: ✅ DONE — IN-GAME CONFIRMED BY USER 2026-09-08.** Their words on the
build-2 re-test, verbatim: *"No Regreesions now. Thanks!"* — i.e. the
Synchro-Material regression from test 1 is gone and nothing else broke.
`verify()` 11/11 PASS, allocation guard clean, KB 410 PASS / 0 FAIL.
ROM: `data/over_the_nexus/working/rom_darksoul.nds`.

**Chain build + verify sweep: DONE 2026-09-08.** `ALL 55 PATCHES APPLIED`,
`BUILD_EXIT=0`, artifact asserted (not the exit code): the old ROM was moved to
`rom_all_patches.PREV.nds` first and the target confirmed absent, so the built file
cannot be stale. `rom_all_patches.nds` sha256
`830cafc72e647b5f8db9662258e75703741ea8749f8f4c88d4ce0c10d7d7a2e6`
(PREV was `c92dcafb...`).

Sweep, measured against a PREV-ROM baseline rather than read cold:

| | PREV baseline | after this work |
|---|---|---|
| `patch_boggart_knight`, `patch_darksoul` | FAIL | **PASS** |
| `patch_lightpulsar` | PASS | FAIL → **root-caused and fixed, now PASS** |
| grapha, ceruli, hanzo, white_dragon_ninja, accel_synchron | FAIL | FAIL (**pre-existing, untouched**) |
| totals | 39 PASS / 7 FAIL | **41 PASS / 5 FAIL** |

**The one real regression, and its root cause.** `patch_lightpulsar.verify` read
Sangan's cls2 record by **hardcoded row index 40** (`0x02275C04 + 40*24 + 0x10`).
The cls2 table is a shared count-neutral resource: this patch drops phantom 0x0E15
(row 7) and inserts the donor at row 143, so every row between shifts down one and
**Sangan moved from row 40 to row 39**. Measured in both ROMs: Sangan 0x0FD6's
record is intact with `+10 == 0` in each — the ROM was always correct, the
assertion was stale. Fixed by looking Sangan up **by cid**, which is exactly what
`otn-chain-build-verify-artifact` already says ("anchor chain preconditions on a
CID never a row index"); re-tested green against BOTH the new and the PREV ROM.

⚠️ **The 5 remaining failures are NOT from this work** and were failing before it.
All five are stale TEXT assertions: each verify still asserts a truncated
"ladder" string that fits the donor's original in-place slot, while `card_text.py`'s
index-order re-emit (user, 2026-09-08) now writes the FULL printed text. e.g.
accel_synchron asserts a 44 B English desc and the ROM holds the correct 463 B one.
The ROMs are right and the assertions are obsolete. **Out of scope this session
(one patch per session); worth a dedicated pass.**

## Printed text (scratch/ygoprodeck_cache.json — authoritative)

> **XX-Saber Darksoul** — EARTH / Beast / Lv3 / 100 / 100, Effect Monster
> "During the End Phase, if this card was sent from your side of the field to
> your Graveyard this turn: You can add 1 "X-Saber" monster from your Deck to
> your hand."

Single clause. `card_text.CARD_TEXT[0x1CE6]` already carries this verbatim, and
the current patch's stats (EARTH/Beast/Lv3/100/100) already match — nothing to
correct there, only to re-key onto the new donor.

## Confirmed (this session, read out of stock `data/over_the_nexus/working/rom.nds`)

* **What the current patch costs, exactly two real cards:**
  * Deep Diver 0x1CE6 — its cls2 record, its populate row and its leave-switch
    leaf at 0x021CA0AA/AC are all overwritten (`patch_darksoul` A1/A3/A5).
  * **Manticore of Darkness 0x16F9 — loses its native End-Phase registry row.**
    Confirmed in the chained image: `rom_all_patches.nds` row @0x0228E478 reads
    `res 0x02254221, cid 0x1CE6` where stock reads `cid 0x16F9`.
  * Plus A2, a rewrite of phantom 0x1CDE's cls2 record kept only for byte-fidelity
    with a stale reference ROM (`rom_all_patches_anyleave.nds`) that
    `verify_against_proven` no longer compares against. Dead weight.

* **Phantom 0x2347 (Darksoul's real reserved cid) carries the complete native
  record set** — this is the shape to clone:
  | table | row | value |
  |---|---|---|
  | cls2 @0x02275C04 | 603 | `{0x2347, 0, +04 0x02207EF5, 0, +0C 0x021F0821, +10 0x021E50DD, 0}` |
  | populate @0x022713C4 | 1236 | `{a 0x2347, b 0x0048, h 0x0223CAF5, fl 0x00000002}` |
  | registry @0x0228E1E0 | 84 (@0x0228E480) | `res 0x02254221, cid 0x2347` |
  All three are **already spent** by other shipped patches (cls2 + populate by
  `tg_striker`, the registry row by `tg_warwolf` — chained image confirms
  @0x0228E480 now reads cid 0x0FA9). So the migration must clone the *shape* onto
  fresh count-neutral phantom drops, not reuse 0x2347's own rows.

* **THE EFFECT REGISTRY IS NOT PARTITIONED BY RESOLVER — it is partitioned by
  SECTION, and rows 63..287 are one section** (`timing_classifier.yaml`, section
  bases rows 1/48/63/288/293/429). Dumped @0x0228E3E0–0x0228E640: rows carrying
  six different resolvers are freely interleaved, and `tg_striker`'s stolen
  0x02254221 row at **row 132** (@0x0228E600) sits amid 0x022546FD / 0x0225474D /
  0x02254865 / 0x022548B9 / 0x0225498D rows — and is **in-game confirmed**.
  ⇒ Any phantom row inside rows 63..287 can be repurposed by rewriting BOTH its
  resolver and its cid, and the End-Phase timing is preserved. `PROVEN`.

* **A free phantom registry row exists in that section: row 119 @0x0228E598**,
  stock `res 0x02254321, cid 0x0E6C`. 0x0E6C has **no card_prop record** (absent
  from `scratch/cid_to_name.json`), the row is **unchanged in the chained image**
  `rom_all_patches.nds` (i.e. unspent), and `("registry_row", 0x0E6C, ...)` is
  **not in `PHANTOM_CLAIMS`** (only 0x16FE azure_eyes, 0x1A9F tg_striker,
  0x2347 tg_warwolf, 0x1CDE darksoul are claimed there).
  ⇒ Rewriting it to `res 0x02254221, cid <donor>` **gives Manticore its row back**.

* **Donor: `0x1783` Gigobyte** (the user's suggestion) — Normal Monster, WATER /
  Reptile / Lv1 / 350 / 300. `donor_scan` VERDICT **CLEAN** (zero aligned
  u16/u32 occurrences in ov3 + ARM9). No cls2 record, no populate row.
  Text slot floors (name 8 B, desc 78 B) **do not matter** — `apply_stats_and_text`
  routes any cid present in `card_text.CARD_TEXT` through `card_text.rebuild_blobs`,
  which re-emits both blobs in index order (boggart_knight, in-game confirmed
  2026-09-08, landed a 23 B name and 211 B text in all eight languages).

* **Free, unclaimed, unspent phantoms for the two count-neutral inserts**
  (cross-checked against `PHANTOM_CLAIMS` *and* against the chained image
  `rom_all_patches.nds`, still present there): cls2 has 59 candidates, populate
  has 63. Proposed: cls2 **0x0E15**, populate **0x0E21**.

* **X-Saber set-code membership** (PART D) is unchanged in mechanism —
  `add_xsaber_member` still drops phantom 0x2346 (`("xsaber_setcode_table",
  0x2346, "darksoul")` in the ledger), only the inserted cid changes.

## Ruled Out

* **Reusing 0x2347's own three native rows.** All three are already spent by
  `tg_striker` / `tg_warwolf` in the chained image. A single-card ROM would not
  have shown this (`otn-register-phantom-same-edit`).
* **The shared End-Phase registry-invoke trampoline `invoke_tg_endphase`
  (`CAVE_TG_REGLIST`)** as the invoker instead of a registry row. It would cost
  zero phantoms, but its only consumer is `patch_tg_rush_rhino`, which the
  changelog still lists as `[ ]` (never in-game confirmed). The registry-row
  steal is the in-game-confirmed path (Striker + Warwolf). Not worth putting an
  unproven mechanism under a card that currently works.
* **Keeping the A5 ov3 leave-switch leaf retarget (0x021CA0AA/AC).** It only
  exists because Deep Diver *had* a native leaf to retarget; a records-free donor
  has none, and Deep Diver must keep its leaf now that it is a real card again.
  ⚠️ Build 1 replaced it with `tg_table.arm_tg_leave_trigger` (hook 0x021C8216);
  that was WRONG — see ROOT CAUSE. Build 2 arms from an equivalent position in
  TREE 2, which is where A5 armed from.
* **Keeping A2 (phantom 0x1CDE cls2 rewrite).** Byte-fidelity ballast for a
  reference ROM `verify_against_proven` no longer compares against.

## What was built (all measured out of the build log / verify, 2026-09-08)

| # | piece | landed |
|---|---|---|
| A1 | ~~shared T.G. trampoline, hook 0x021C8216~~ **superseded in build 2** — see ROOT CAUSE: that stub gates on `[sp+0x90]` DESTROYED. Now a dedicated any-leave stub `CAVE_DS_ARMTRAMP` @0x0239EB70 (28 B) hooked at TREE 2's root 0x021C9F1C → gate 0x021CA640 |
| A2 | registry row 119 @0x0228E598 | `res 0x02254321 cid 0x0E6C` → `res 0x02254221 cid 0x1783` |
| A3 | cls2 record `{0x1783, 0, 0x02207EF5, 0, 0x021F0821, 0x021E50DD, 0}` | idx 143 @0x0227696C, dropped phantom 0x0E15, 697 records, sorted |
| A4 | populate row `{0x1783, 0x0048, 0x0223CAF5, 0x00000002}` | idx 284 @0x02272114, dropped phantom 0x0E21, 1389 rows, sorted |
| D | X-Saber set-code table @0x0209CB6E | dropped 0x2346, inserted 0x1783; 20 sorted entries |
| B | card_prop | `lvl 1 WATER Reptile 350/300 Normal` → `lvl 3 EARTH Beast 100/100 Effect` |
| C | name + text | full `XX-Saber Darksoul` (17 B) + 161 B printed text in **all eight** languages, via `card_text.rebuild_blobs` |

`add_xsaber_member` is pinned to `drop_cids=(0x2346,)` so the single-card ROM and
the chained ROM drop the same slot (boggart_knight owns 0x2347).

**Deleted from the old build:** A2 (the phantom-0x1CDE cls2 rewrite, byte-fidelity
ballast) and A5 (the ov3 leave-switch leaf retarget at 0x021CA0AA/AC — a
records-free donor has no leaf, and deleting it restores Deep Diver's).
`verify_against_proven` is gone; the module now has a real `verify()`, which
`_verify_all_patches` can actually call (it was in `SHIPPED` but skipped, because
the old module exposed no `verify`).

**Also re-keyed 0x1CE6 → 0x1783 (would otherwise have silently mis-targeted):**
`card_text.CARD_TEXT`, and **`patch_card_art.CardArt`** — the art row would have
painted Darksoul's art onto Deep Diver.

**New KB fact** `timing.registry_row_repurpose_within_section` (VERIFIED, closed
structural proof against stock ov3): a phantom registry row anywhere in the right
section can be repurposed by rewriting resolver AND cid together — the walker does
`ldr r2,[r5,r2] ; blx r2`, i.e. reads each row's own resolver, and the 63..287
section holds ≥20 distinct resolvers. This is the general answer to "where do I get
an End-Phase registry row without breaking a real card", now that 0x02254221's only
two phantom rows are spent by tg_striker and tg_warwolf.

## IN-GAME TEST 1 — 2026-09-08 (user)

User's exact words: *"1) If I use darksoul as a synchro material, he does not trigger
in the end-phase, see .ml3 (after synchro) and .ml4 (in end-phase) … Destroy by battle
showed no regressions."* Follow-up: *"No prompt appeared in the end-phase. There was
only one regression."*

* **PASS** — destroyed by battle → the End-Phase X-Saber pick menu appears.
  This proves A2 (registry row 119), A3 (cls2), A4 (populate) and the whole
  native resolution path are correct. Oracle 3's other means are untested.
* **FAIL** — used as Synchro Material → **no prompt at all** at the End Phase.
  The fault is isolated to the ARM half (A1).
* Oracles 1, 4–8 not yet reported on.

## Confirmed — the arming path, measured this session (static, stock ov3)

Scripts: `scratch/leave_tree_callers.py`, `leave_tree_select.py`,
`leave_fn_callers.py`, `leave_gate_flags.py`, `darksoul_arm_probe.py`.

1. **Both per-cid leave trees live in ONE function.** TREE 1 (root 0x021C8216,
   where the shared trampoline hooks) and TREE 2 (root 0x021C9F1C, whose leaf the
   OLD Deep Diver build retargeted) share the prologue **0x021C7FD0**
   (`push {r3-r7,lr} ; sub sp,#0x1e8`), as does the gate 0x021CA640. So they share
   one stack frame — the cross-tree branch the trampoline makes is frame-safe.
2. **TREE 1's root is straight-line fall-through from the prologue.** Every branch
   in 0x021C7FD0..0x021C8214 lands *on* 0x021C8216 (predecessors 0x021C81F6 /
   0x021C8206 / 0x021C8210). ⇒ **"the Synchro path took the other tree" is RULED
   OUT** — if the function runs, our trampoline runs.
3. **The function has exactly ONE caller: `BL 0x021C7FD0` @0x021CD2AC**, and that
   call is GUARDED:
   `[sp+0x4c] == 0` **AND** (`[sp+0x14] != 0` **OR** `r4 > 0xA`).
   (`0x021CD28A..0x021CD29A`; `bne 0x021CD2C6` skips the call.)
4. **The descriptor unpack** (measured 0x021C7FD0..0x021C8054), arg 5 at [sp+0x200]:
   `[sp+0x144]` = 1 iff dest zone field == 0x0E (to GY); `[sp+0x28]` = dest == 0x0D;
   `[sp+0x90]` = bit 15 (DESTROYED); `[sp+0x44]` = bit 16 (BATTLE);
   `[sp+0x2c]` = 1 iff **bit 23 is CLEAR**; `[sp+0x30]` = the two side fields differ.
5. **The arming gate 0x021CA640 requires exactly three things** to reach its
   trigger-build call `bl 0x021D2584` @0x021CA686:
   `[sp+0x2c] != 0` (bit 23 clear) **AND** `r6 == [sp+0x98]` (controller)
   **AND** `[sp+0x144] != 0` (destination is the GY).
   It does **NOT** require DESTROYED or BATTLE. A Synchro Material does go to the
   GY, so of the three only **descriptor bit 23** can be rejecting it.

⇒ The failure is at exactly one of two single-bit places: **(A)** the guarded call
@0x021CD2AC is skipped on the Synchro-Material path, or **(B)** the call happens and
descriptor **bit 23 is SET**, so `[sp+0x2c]` is 0 and gate 0x021CA640 bails to the
generic leaf 0x021CA68A. Nothing else in the chain can reject.

## Ruled Out (this session)

* **"Battle and Synchro Material use different leave dispatch trees, and I hooked
  the wrong one."** Falsified by (1)+(2): one function, one caller, and tree 1 is
  unconditional fall-through.
* **"The gate rejects because it demands DESTROYED."** Falsified by (5): the gate
  reads `[sp+0x90]` only on the *other* arm (0x021CA654..), not the one we enter.
* **A rider-pool node keyed with our cid** as the "left the field this turn" mark —
  `darksoul_arm_probe` finds **no** node keyed 0x1783 in ml2/ml3/ml4. (Consistent
  with the two-walker-families trap: the key may be a locator, not a cid, so this
  is not evidence either way about arming.)
* Savestate census: the card sits at player[0]+0x05C (monster zone 2) in ml2 and
  moves to player[0]+0x55C in ml3/ml4 — i.e. the engine did relocate it normally.

## ROOT CAUSE — FOUND 2026-09-08, and it was written in the code all along

`tg_table._shared_arm_trampoline` — the shared TREE 1 trampoline I registered the
donor on — **adds its own `[sp+0x90]` DESTROYED test** before branching to the gate.
Its own comment says why:

> *"this trampoline was originally cloned from patch_darksoul.py, where firing on
> ANY leave is correct for that card. The T.G. cards need 'destroyed on the field
> and sent to the GY', so the [sp+0x90] DESTROYED test below is REQUIRED — **without
> it Tribute Summon fodder and Synchro Material also armed the search** (both send
> to the GY, so the gate's own [sp+0x144] test passes)."*

Battle destruction sets `[sp+0x90]`; a Synchro Material does not. That is the entire
bug, and it matches both observations exactly. The gate 0x021CA640 itself is an
ANY-LEAVE-to-GY gate (measured above: it never reads `[sp+0x90]` on the arm we
enter) — the filter is the trampoline's, not the engine's.

⚠️ The irony worth carrying forward: that trampoline was **cloned from this very
card**, then tightened for the T.G. cards, and re-homing Darksoul onto it silently
re-applied a filter Darksoul must not have. A shared arming trampoline is not
card-agnostic just because it takes a cid list.

## THE FIX (built 2026-09-08) — A1 moved to its own TREE 2 trampoline

* New ov5 stub **`CAVE_DS_ARMTRAMP` = 0x0239EB70** (28 B), hooked over **TREE 2's
  root 0x021C9F1C** (native `LDR R0,[PC,#0x9C] ; CMP R4,R0` = `4827 4284`,
  literal `0x00001A64` @0x021C9FBC). For `r4 == 0x1783` it `BX`es into the
  any-leave gate 0x021CA640 with **no DESTROYED test**; every other cid gets
  `r0 = 0x1A64` and `CMP R4,R0` replayed, then `BX LR`.
* ⚠️ **Replay order is load-bearing:** the replayed `CMP` must be the LAST
  instruction before `BX LR` — 0x021C9F20 is a `BLE` that consumes those flags.
  Verified in the emitted stub.
* The donor is **removed from the shared T.G. trampoline**, so Striker, Warwolf,
  Rush Rhino and Quasar keep their DESTROYED filter and their stub is byte-untouched.
  `verify()` asserts the donor is NOT on it, so a future session cannot re-introduce
  this bug silently.
* This is the position the OLD Deep Diver build armed from (a tree-2 leaf), which
  the user confirms worked on Synchro Material.
* Emitted stub disassembled and checked: three literals `0x00001783`,
  **`0x021CA641` (ODD — no ARM-state freeze)**, `0x00001A64`; no POP, no BLX-to-even.
* `verify()` **11/11 PASS**; allocation guard clean; KB 410 PASS / 0 FAIL.
* New KB fact `leave.two_trees_one_function_pick_by_timing` (VERIFIED) records the
  one-function/two-tree geometry, the descriptor slot map, the gate's three terms,
  and this trap.

**Status: IN-GAME CONFIRMED by user 2026-09-08** (*"No Regreesions now"*).

## Superseded context — was "an untested corner"; the user corrected this

Every shipped user of the shared arming trampoline triggers on **destruction**:
T.G. Striker and T.G. Warwolf E2 are printed *"because it was destroyed on the field
and sent there this turn"*, and Quasar's is destruction-based too. **No shipped
patch has ever exercised hook 0x021C8216 for a non-destruction departure**, so the
trampoline was never shown to arm on Synchro Material.

✅ **RESOLVED by the user 2026-09-08:** *"yes the old deep diver worked when used as
synchro material this was documented."* So it IS a regression, the tree-2 arming
position is proven to work for Synchro Material, and the DESTROYED filter above is
the difference. The guard @0x021CD2AC is therefore NOT what blocks the Synchro path.

## Open Questions

1. `verify()`'s `_assert_donors_untouched` also runs against the CHAINED ROM in
   the `_verify_all_patches` sweep. Nothing later in `PATCHES` is known to touch
   0x1CE6 or 0x16F9, but that has not been demonstrated — it needs a chain build,
   which is deliberately deferred until the card is in-game confirmed.

## Next Experiment (supersedes the oracle list below, which still stands for the rest)

The chain is narrowed to two single-bit possibilities (A) and (B) above. Cheapest
first, in order:

1. **FREE — ask the user** whether the OLD Deep Diver build ever actually fired on
   Synchro Material. If it never did, this is not a regression and the clause has
   always been battle-only; that changes what "fixed" means.
2. **ONE GDB session, one breakpoint** (`tool.gdb_one_shot_session` — connect once,
   arm everything, collect in a single window, write to a file):
   * bp **0x021CD28A** — read `[sp+0x4c]`, `[sp+0x14]` and `r4` to see whether the
     guard even lets the call through on a Synchro Summon. Distinguishes (A) from (B).
   * bp **0x021C8216** — if it hits, (A) is dead; then read `[sp+0x2c]`,
     `[sp+0x144]`, `[sp+0x98]`, `r6` and `r4` to see which gate term fails.
   Run both in the SAME session: Synchro-Summon using Darksoul as material.
   Control arm in the same session: a battle destruction, which must hit both.
3. Only then choose the fix. If (A): the arming has to be hooked upstream of
   0x021CD28A, on whatever path sends a Synchro Material to the GY. If (B): the
   trampoline must build the trigger itself rather than delegating to 0x021CA640
   — i.e. call `0x021D2584([sp+0x98], cid, 1, [sp+0x9c])` directly once its own
   conditions hold, bypassing the bit-23 term.

Do **not** write a fix before that measurement — the mechanism hypothesis has been
narrowed by measurement twice now and the remaining split is exactly what a
breakpoint reads in one duel.

## Original oracle list (items 1, 4-8 still unreported)
1. The card reads **XX-Saber Darksoul**, EARTH / Beast / Lv3 / 100 / 100, with the
   full printed text and Darksoul's art.
2. On the field, **destroyed by battle** → at your End Phase, a pick menu offers
   "X-Saber" monsters from your Deck; the chosen one goes to hand.
3. Same, but sent to the GY by **effect destruction / Tribute / Synchro Material** —
   the any-leave trampoline is what makes these fire, and it is the piece the old
   ov3-leaf build had to hand-write.
4. Sitting **in hand** at either player's End Phase → nothing fires, no freeze.
5. On the field and **NOT sent to the GY** → nothing fires.
6. It counts as an "X-Saber" for other cards (Faultroll's on-field count).
7. **Deep Diver 0x1CE6 is a real card again** — own name, art, stats and its own
   flip effect.
8. **Manticore of Darkness 0x16F9 is a real card again** — its own End-Phase
   "discard 3 Beast/Beast-Warrior/Winged Beast; Special Summon this" trigger.

Oracles 7 and 8 are the whole point of the re-home; 3 is the clause most likely to
regress.

## Inherited from the pre-DSL darksoul.py (UNVERIFIED -- not re-proven in the DSL conversion, 2026-10-29)
- Never move arming onto the shared T.G. trampoline 0x021C8216: it gates on [sp+0x90] DESTROYED; this card is "sent to GY" by any means. Measured in-game earlier: battle destruction armed, Synchro Material did not. (Still asserted by the DSL `check`.)
- `CMP R4,R0` must be the last insn before `BX LR` (0x021C9F20 is a BLE consuming the flags). (Encoded in the verb.)
- Registry row 119 @0x0228E598 is safe: timing is positional; it sits in the 63..287 section with Manticore's row 83 and tg_striker's row 132.
- Old build re-homed off Deep Diver 0x1CE6 and stole Manticore 0x16F9's row 0x0228E478. The old file pinned both (Deep Diver cls2 tail 0x02216191,0,0x0224A115,0,0, populate 0x0223CAD9; Manticore row = 0x02254221/0x16F9) and re-read the clone source phantom 0x2347's cls2/populate shapes. The DSL does NOT assert these any more; recover from git history if needed.
- X-Saber table drop order: Boggart drops 0x2347 first; Darksoul drops 0x2346.
