# Gravekeeper's Recruiter — re-home onto a Normal-Monster donor (2026-09-10)

Task: `patch_gravekeepers_recruiter` currently cannibalises **Botanical Girl
0x1ED4**, a real Effect Monster, and *depends on her native records* (her cls2
record, her populate row, and her membership in the sent-to-GY leave list).
Move it to a records-free vanilla the way `patch_boggart_knight` (2026-09-08) and
`patch_darksoul` (2026-09-08) were moved.

**Status: DONE — IN-GAME CONFIRMED BY USER 2026-09-10.** Every oracle passed on the
FIRST test. `verify()` 13/13 PASS, allocation guard clean, KB 411 PASS / 0 FAIL.
ROM: `data/over_the_nexus/working/rom_gravekeepers_recruiter.nds`.

Their words, verbatim, against the six-item oracle list in the hand-off message:
*"1. Confirmed / 2. Confirmed / 3. Confirmed / 4. Confirmed / 5. Confirmed /
6. Confirmed"*, and then *"Yes that is correct"* to the read-back below — which
explicitly enumerated effect destruction, Tribute **and** Synchro Material under
oracle 3, so all three means are confirmed, not a subset.

**Chain build + verify sweep: NOT YET RUN.** Deliberately deferred — see Open
Questions.

## Printed text (`scratch/ygoprodeck_cache.json` — authoritative, read this session)

> **Gravekeeper's Recruiter** — DARK / Spellcaster / Lv3 / 1200 / 1500, Effect Monster
> "If this card you control is sent to your GY: Add 1 "Gravekeeper's" monster with
> 1500 or less DEF from your Deck to your hand."

Single clause, mandatory, any-means send-to-GY. The current patch's stats already
match. Nothing to re-implement — only to re-key onto a new donor.

## Confirmed (this session, measured out of stock `data/over_the_nexus/working/rom.nds`)

### What the current patch costs: one real card, Botanical Girl 0x1ED4

* cls2 record overwritten in place (`+0C 0x021F0821 -> 0`, `+10 0x021E51E5 -> 0`).
* populate row overwritten in place (`b 0x03E8 -> 0x05DC`, `h 0x0223D675 -> cave
  wrapper`, `fl 0x68000002 -> 0x00000002`).
* Its list30 membership is *reused as-is* (the patch only asserts it).
* card_prop / name / desc / art all rewritten.

### THE ARMING MECHANISM — fully mapped this session (static disassembly, stock ov3)

`patch_gravekeepers_recruiter`'s comments call list30 a "per-cid RANGE" dispatch.
**That is wrong.** Measured at `0x021C8054..0x021C8104`, inside the single leave
dispatcher `0x021C7FD0`, there are exactly **two flat sorted cid lists**, both
feeding the same arm flag `[sp+0x18]`:

| list | addr | count | consumer | preconditions |
|---|---|---|---|---|
| A "destroyed by battle" | `0x0226E990` | `0x6A` | `bl 0x02022E14` @`0x021C80D4` | `[sp+0x44]` BATTLE && `[sp+0x90]` DESTROYED && `[sp+0x144]` to-GY |
| B "list30" (any-means) | `0x0226E904` | `0x1E` | `bl 0x02022E14` @`0x021C80F2` | `[sp+0x2c]` (desc bit 23 clear) && `[sp+0x144]` to-GY |

```
021C80E0  ldr r0,[sp,#0x2c] ; cmp r0,#0 ; beq skip     <- bit 23 clear
021C80E6  ldr r0,[sp,#0x144]; cmp r0,#0 ; beq skip     <- destination == GY
021C80EC  ldr r1,[pc,#0x230]                           <- 0x0226E904 (list30)
021C80EE  adds r0,r4,#0                                <- r4 = departing cid
021C80F0  movs r2,#0x1e                                <- count 30
021C80F2  bl 0x02022E14                                <- bsearch_u16(key,tbl,cnt)->bool
021C80F6  cmp r0,#0 ; beq skip
021C80FA  movs r0,#1 ; str r0,[sp,#0x18]               <- ARM FLAG
021C80FE  ldr r0,[sp,#0x18]; cmp r0,#0; bne 0x021C81F2 <- armed -> resolve
```

`0x02022E14` disassembled and confirmed to be a plain
`bsearch_u16(r0=key, r1=table, r2=count) -> r0 bool` (`push {r3-r5,lr}` … `movs r0,#1`
/ `movs r0,#0` … `pop {r3-r5,pc}`). **PROVEN.**

These two lists are BEFORE tree 1's root `0x021C8216` (the shared T.G. hook) and
tree 2's root `0x021C9F1C` (Darksoul's hook) — they are a *third*, data-driven
arming route in the same function, and the two conditions list30 requires are
exactly two of the three that gate `0x021CA640` demands. `PROVEN`.

* Literal `0x0226E904` occurs **exactly once** in ov3 (@`0x021C8320`), and the
  count immediate `movs r2,#0x1e` exactly once (@`0x021C80F0`). One consumer.
* Hook-site bytes @`0x021C80F2` = `5A F6 8F FE` (the BL). Unclaimed by any patch.

### list30 has NO phantom to drop — a count-neutral insert is impossible

All 30 entries resolve to real cards (dumped this session):
`0x0D7C 0x0FD6 0x10D6 0x10DD 0x10DF 0x10E0 0x10E7 0x11E4 0x13E9 0x1467 0x15B9
0x16CC 0x1796 0x17A5 0x1CDE 0x1D8C 0x1E6C 0x1E96 0x1ED4 0x1F2A 0x2034 0x204C
0x2161 0x2282 0x22C7 0x22D0 0x231E 0x2355 0x23CC 0x24E0`.
`donor_scan` independently names the table ("list30 (sent-to-GY leave list)") and
reports each of the sampled entries as a real, ENTANGLED card.
And the table cannot be **grown in place** in EITHER direction:

* **Up:** `0x0226E940`, immediately after the 30th entry, is already the start of
  another sorted u16 table (`0x0E42 0x0E48 0x12D3 ...`).
* **Down:** `0x0226E902` genuinely IS free — a 2-byte alignment pad reading `0x0000`
  between the preceding sorted list (last entry `0x2469` @`0x0226E900`) and list30's
  first entry — and the table has exactly ONE base literal (@`0x021C8320`) and ONE
  count immediate (@`0x021C80F0`), so re-basing to `0x0226E902` with count `0x1F` is
  a 6-byte data edit. **But a prepended entry must sort below `0x0D7C`, and all 52
  real cids below `0x0D7C` are Speed World / Speed Spell cards — not one monster.**
  `PROVEN`.

⇒ **No monster donor can ever be given list30 membership by a data edit.** Banked in
the KB (`event.leave_dispatcher_three_registers`, proof extended this session).
⇒ The trigger must come from the dispatcher's THIRD registration path, the leave-mask
table — which is also pure data. See *What was built*.

### Donor: Battle Steer 0x0FB4 (user's suggestion) — CLEAN

`.venv-1/Scripts/python.exe -m otn_enhanced.tools.donor_scan 0x0FB4`:

* Normal Monster, EARTH / Beast-Warrior / Lv5 / 1800 / 1300, pack1=2.
* **VERDICT: CLEAN — no data structure names this cid.** No cls2 record, no
  populate row, no list30/listA membership, no set-code table, no per-cid gate.
* The 4 "ambiguous ARM9 data-region u16 hits" (`0x0209D762`, `0x0209E370`,
  `0x0209E760`, `0x020A1372`) were dumped with context this session and are
  **numeric lookup tables**, not cid tables — each hit sits in a monotone
  interleaved pair sequence (`0FB6 030D 0FB5 0313 0FB4 0319 0FB3 031F 0FB1`).
  Not a gate. `PROVEN`.
* Text slot floors are irrelevant — `apply_stats_and_text` routes any cid present
  in `card_text.CARD_TEXT` through `card_text.rebuild_blobs` (boggart_knight /
  darksoul precedent, in-game confirmed 2026-09-08).

### Free, unclaimed, unspent phantoms for the two count-neutral inserts

Cross-checked against `PHANTOM_CLAIMS` **and** against the chained image
`rom_all_patches.nds` (cid still present there ⇒ nobody has spent it):
cls2 has **37** candidates, populate has **52**.
Proposed: cls2 **0x0E16**, populate **0x0E2B**.

### ov5 cave

`ov5_cave.CAVE_FREE = 0x0239EBF0` (read this session, quoted from
`otn_enhanced/effects/ov5_cave.py:1502`). The card already owns
`CAVE_GK_WRAPPER = 0x0239A1E0` and `CAVE_GK_FILTER = 0x0239A220`.

## What was built (2026-09-10) — IN-GAME CONFIRMED

ROM: `data/over_the_nexus/working/rom_gravekeepers_recruiter.nds` (single-card).

| # | piece | landed |
|---|---|---|
| A1 | cls2 `{0x0FB4, 0, 0x02207EF5, 0, 0, 0, 0}` (= Sangan's, read at build time) | idx 39 @0x02275FAC, dropped phantom 0x0E16, 697 records, sorted |
| A2 | populate `{0x0FB4, 0x05DC, 0x0239A1E1, 0x00000002}` | idx 68 @0x022716F4, dropped phantom 0x0E2B, 1389 rows, sorted |
| A3 | leave-mask row `{0x0FB4, mask 0x0800}` | idx 17 @0x0226EC60, dropped phantom 0x0E49, 152 rows, sorted |
| D | Gravekeeper's set-code table @0x0209C986 | dropped 0x2442, inserted 0x0FB4; 16 sorted |
| B | card_prop | `lvl 5 EARTH Beast-Warrior 1800/1300 Normal` → `lvl 3 DARK Spellcaster 1200/1500 Effect` |
| C | name + text | full `Gravekeeper's Recruiter` (23 B) + 125 B printed text in **all eight** languages, via `card_text.rebuild_blobs` |
| E | art | 0x0FB4 idx 257 → Gravekeepers_Recruiter (32x32 + 64x64) |

The ov5 filter + cloned wrapper (`CAVE_GK_FILTER` / `CAVE_GK_WRAPPER`) are byte-identical
to the shipped build — untouched by the re-home.

**Zero injected code was added.** The final architecture costs three phantom drops
and nothing else: no new ov5 cave slot (`CAVE_FREE` is back at its original
0x0239EBF0), no ov3 dead-code block (54 B still free, unchanged).

Also re-keyed 0x1ED4 → 0x0FB4 (would otherwise have silently mis-targeted):
`card_text.CARD_TEXT` and `patch_card_art.CardArt` — the art row would have painted
Recruiter's art onto Botanical Girl.

## THE ARCHITECTURE CHANGED TWICE — both dead ends are worth carrying forward

**Dead end 1: an ov5 shim over list30's bsearch call (BUILT, verified, then REVERTED).**
A 24 B stub at `CAVE_GK_ARMTRAMP` hooked over the `BL 0x02022E14` @0x021C80F2,
answering "member" for the donor and tail-calling the real bsearch otherwise. It
built and passed verify() — and it was **wrong**, for a reason `verify()` can never
see: that BL is on the leave path for **every card in the game**, and a puzzle loads
overlay 41 over overlay 5, so it would have frozen the engine the first time anything
went to the GY in a puzzle. Not "this card doesn't work in puzzles" — the whole mode.
`patch_eclipse_wyvern` documented this trap **at this very site** in a previous build.
⇒ Caught by grepping the hook address across `finished_patches/` before shipping.
The allocation guard cannot see a hook-site collision; only the manual grep can.

**Dead end 2: the same stub hosted in ov3 dead code (BUILT, verified, then REVERTED).**
Puzzle-safe, and it fit: 12 B of code at 0x021B58D0 with its 8 B literal pool SPLIT
into 0x021B5AAC (both `ldr [pc,#472]` reads in range), returning the cid itself as the
non-zero "found" value to save the `movs r0,#1` there was no room for. Disassembled
clean. But it burned the **last two free ov3 dead blocks** to buy something the engine
already offers as a data row.

**What was actually right was already in the KB, in a VERIFIED fact, naming this
patch.** `event.leave_dispatcher_three_registers` says in as many words: a donor that
is not natively in list30 "takes the MASK TABLE with mask 0x0800 ... That is
patch_lightpulsar PART M and patch_gravekeepers_recruiter PART A3 (whose donor
Botanical Girl 0x1ED4 is a native list30 member)". The KB had already answered the
question this session spent two builds re-deriving.
⇒ **Read the KB fact for the subsystem before designing, not after the first build.**

## Ruled Out

* **Inserting the donor into list30 count-neutrally.** No phantom exists in it
  (all 30 are real cards) and the table is packed against its neighbour at
  `0x0226E940`, so it cannot be grown in place either.
* **The "per-cid RANGE dispatch" story in the current module's comments.** list30
  is a flat sorted bsearch table with two stack-flag preconditions; there is no
  range routing. Corrected above.
* **Joining the shared T.G. arming trampoline (hook `0x021C8216`).** It applies a
  `[sp+0x90]` DESTROYED filter — the exact bug that broke Darksoul's
  Synchro-Material case (2026-09-08). Recruiter is any-means.
* **Joining Darksoul's tree-2 trampoline (hook `0x021C9F1C`).** Right semantics
  (no DESTROYED filter) but `patch_darksoul` *owns* that 4-byte site; a second
  patch cannot install a second BL there, and turning it into a shared cid-list
  trampoline re-creates exactly the cross-card coupling that produced the T.G.
  regression. It also enters a *different* gate than the one Recruiter natively
  used.

* **An ov5 shim over the list30 bsearch call** — built and verified, then reverted.
  0x021C80F2 is on the leave path for every card and ov41 evicts ov5 in a puzzle:
  engine-wide freeze, not a card-level no-op. See *dead end 1* above.
* **The same shim in ov3 dead code** — built and verified, then reverted. Correct
  and puzzle-safe, but it spends the last two free ov3 dead blocks on something the
  leave-mask table provides as a data row. See *dead end 2* above.

## IN-GAME TEST — 2026-09-10 (user), ALL PASS ON THE FIRST TEST

Numbering below is the six-item list from the hand-off message. (The eight-item list
drafted earlier in this file was superseded by it; items 3 and 8 there map onto 3 and
6 here, and the two DEF-boundary/archetype checks were folded into 2 and 5.)

| # | oracle | result |
|---|---|---|
| 1 | Reads Gravekeeper's Recruiter, DARK / Spellcaster / Lv3 / 1200 / 1500, full text + art | **PASS** |
| 2 | Destroyed by battle → mandatory Deck→hand add of a Gravekeeper's with DEF ≤ 1500 | **PASS** |
| 3 | Same via effect destruction, Tribute **and** Synchro Material (all three) | **PASS** |
| 4 | Discarded from hand / milled from Deck → nothing fires (field-only) | **PASS** |
| 5 | Botanical Girl 0x1ED4 is her own card again, with her own Plant search | **PASS** |
| 6 | Puzzle mode still plays normally | **PASS** |

**What #2 + #3 + #4 together prove, and it is the load-bearing result of this
session:** the leave-MASK row `{cid, 0x0800}` is a drop-in replacement for list30
membership for a "sent from the field to the GY by any means" trigger. It fires on
every departure means list30 does, including Synchro Material — the case that broke
Darksoul on the shared T.G. trampoline — and it stays field-only, so a discard or a
mill does not trigger it. Paired with Sangan's cls2 (+0C=0 / +10=0). `PROVEN in-game`.

**What #6 proves:** the puzzle-mode concern that killed both earlier architectures was
real to worry about and is fully avoided by the data-row approach — there is no
injected code anywhere on the leave path.

**What #5 proves:** the re-home achieved its purpose. Botanical Girl was a real Effect
Monster being consumed by this patch; she is now intact and playable.

## Open Questions

1. **Chain build + `_verify_all_patches` sweep — NOT YET RUN.** The single-card ROM is
   confirmed; the chained one has not been rebuilt since the re-home. Two things it
   needs to establish:
   * `_assert_botanical_untouched` also runs against the chained ROM in the sweep.
     Nothing later in `PATCHES` is known to touch 0x1ED4, but that is not demonstrated.
   * The three phantoms this patch now spends (cls2 `0x0E16`, populate `0x0E2B`,
     leave-mask `0x0E49`) were each checked free in both the stock image and the
     PREVIOUS `rom_all_patches.nds` — but that image predates this change.
   ⚠️ Per `otn-chain-build-verify-artifact`: move the old ROM aside first and assert
   the BUILT artifact's patch count and sha256, not the exit code.

## Next Experiment

None for this card — it is done. The only remaining work is the chain build + verify
sweep (Open Question 1), which is a build step, not a measurement.
