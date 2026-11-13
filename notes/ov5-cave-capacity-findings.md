# ov5 cave capacity — can the cave be made larger?

Session 2026-09-02. Asked while Junk Speeder clause 2 was under in-game test,
because that patch consumed the last 0x150 bytes of the cave.

**ANSWER: yes, comfortably — it is one constant, and the duel heap it borrows
from is enormously over-provisioned.** Nothing below has been in-game tested;
the structural claims are closed against the committed oracles, the usage
figures are savestate measurements.

## Confirmed — the mechanism (re-read this session, ov5_cave.py:42-57)

- ov5 loads at `0x022C5900`, native length `0xD4820`, so it natively ends at
  **`0x0239A120`** — and that address **is** the duel heap base ("arena-lo").
- The cave = append `RESERVE` zero bytes to ov5, and raise the arena-lo literal
  by the same amount so the heap starts above the grown overlay.
- `RESERVE = 0x4000` (16 KB) today. `OV5_NEW_LEN` and `ARENA_LO_NEW` both derive
  from it, so **the size is a single constant**.

## Confirmed — the arena bounds

Literal pool at `0x02051ED8` (arm9 main section) holds the region table:

```
0x02051ED8 = 0x0239A120   <- duel arena LO   (== ov5 native end)
0x02051EDC = 0x0212EA38
0x02051EE0 = 0x023E0000   <- duel arena HI
0x02051EE4 = 0x01FFF520
0x02051EE8 = 0x027E0140
0x02051EEC = 0x02FFF000
0x02051EF0 = 0x037F8000
```

⇒ duel arena = `[0x0239A120, 0x023E0000)` = **0x45EE0 = 279.7 KB**, of which the
cave currently takes 16 KB, leaving the heap 263.7 KB.

## *** Confirmed — 0x0239A120 OCCURS EXACTLY ONCE IN THE WHOLE ROM ***

Scanned every aligned u32 of the ARM9 main section **and all 50 overlays**:
the only occurrence is `arm9 sec0 @0x02051ED8`, the literal `ov5_cave.py`
already raises. So the arena-lo really is a single source of truth — there is
no second hardcoded copy that would silently hand the heap back the bytes the
cave took. **This is what makes enlarging safe at any size**, not just at 16 KB.

## Confirmed — no overlay collision

Only two overlays load at ov5's base `0x022C5900`:

| overlay | size | reaches |
|---|---|---|
| ov5 | 0xD4820 (850 KB) | 0x0239A120 |
| ov41 (puzzle) | 0x161E0 (88.5 KB) | 0x022DBAE0 |

ov41 — the one that evicts ov5 in a puzzle — is **an order of magnitude
smaller** and ends 1041 KB below arena-hi, so it imposes no limit on RESERVE.
(ov47/48/49 load at 0x022DC640+ and are tiny; all sit far below the cave.)
⚠️ Unchanged by any of this: ov5 is not resident in a puzzle, so cave stubs stay
normal-duel-only regardless of size.

## Measured — how much duel heap is actually used

The duel arena is a NitroSDK **ExpHeap**. Header fields, established from three
states and then cross-checked on all of them:

```
+0x00  signature   (u32 0x45585048, bytes spell 'HPXE')
+0x18  heapStart   (== arena_lo + 0x38)
+0x1C  heapEnd     (== 0x023E0000 in every state)
+0x24  free-list HEAD      +0x28  free-list TAIL
+0x2C  used-list HEAD      +0x30  used-list TAIL
```

Scanned **every savestate in data/over_the_nexus/working/** (the arena_lo was
discovered per state by probing for the signature, not assumed):

- **153 states** carried a readable duel heap.
- Two distinct arena_lo values appear — `0x0239A120` (pre-cave ROMs) and
  `0x0239E120` (cave ROMs) — confirming the raise works and that the heap in a
  cave ROM genuinely starts above the cave.
- heapEnd is `0x023E0000` in **all 153**.
- Free-list head == tail in **all 153** ⇒ a single free block running to
  heapEnd, so `free_head - heapStart` is a conservative "used" figure (it counts
  fragmentation as used).

| | |
|---|---|
| minimum used | **33.1 KB** |
| **peak used across all 153 states** | **37.3 KB** (`rom_tg_test.ml5`) |
| duel arena total | 279.7 KB |
| headroom above peak | **242.4 KB** |

What various RESERVE values would leave:

| RESERVE | cave | heap | spare above the measured peak |
|---|---|---|---|
| 0x4000 (today) | 16 KB | 263.7 KB | 226.4 KB |
| 0x8000 | 32 KB | 247.7 KB | 210.4 KB |
| 0x10000 | 64 KB | 215.7 KB | 178.4 KB |
| 0x20000 | 128 KB | 151.7 KB | 114.4 KB |

## Open Questions / limits of this measurement

- The 153 states are the ones this project happened to capture — overwhelmingly
  normal duels, mid-turn. **37.3 KB is a measured lower bound on the true peak,
  not a proof of it.** Duel load, tag / turbo duels, and heavy animation
  sequences are not necessarily represented. The margin (6x the observed peak
  even at RESERVE 0x10000) is what carries the risk, not the sample.
- Not measured: whether any allocation path uses a *different* heap that also
  lives below 0x023E0000.

## What a change would touch

1. `ov5_cave.RESERVE` — the actual change (`OV5_NEW_LEN`, `ARENA_LO_NEW` derive).
2. `otn_enhanced/knowledge/env.py:36` `OV5_END` — **hardcoded 0x0239E120**.
3. `otn_enhanced/knowledge/check_allocations.py:39` `OV5_END` — **hardcoded**.

⚠️ 2 and 3 are hardcoded copies of a derived value; they are exactly the drift
that already produced the stale "464 bytes free" comment. Worth deriving rather
than re-hardcoding.

**Existing cave slots do NOT move.** The appended region still starts at
`0x0239A120`; only its ceiling rises. So no shipped stub changes address and no
patch needs editing — the change is purely additive.

But it IS shared state: every ROM's ov5 length and arm9 arena-lo literal change,
so it needs a full `apply_all_patches` + `_verify_all_patches` sweep and at least
one in-game duel to confirm the smaller heap is still sufficient.

---

# DECISION (user, 2026-09-02): grow to 64 KB, AFTER the Junk Speeder in-game test

`RESERVE 0x4000 -> 0x10000`. Deliberately NOT done yet: the user is mid-test on
`rom_junk_speeder.nds`, and landing a heap change under an in-flight test would
make a failure ambiguous. **Nothing in the repo has been changed for this.**

New geometry once it lands:
- `ARENA_LO_NEW` = 0x0239A120 + 0x10000 = **0x023AA120**
- cave region = `[0x0239A120, 0x023AA120)` = 64 KB
- `CAVE_FREE` stays **0x0239E120** (it is the first free address, not the
  ceiling) -> free tail becomes 0x023AA120 - 0x0239E120 = **0xC000 = 48 KB**
- duel heap = `[0x023AA120, 0x023E0000)` = 0x35EE0 = **215.7 KB**, vs the 37.3 KB
  measured peak

## The exact edit list

1. `ov5_cave.py:48` `RESERVE = 0x4000` -> `0x10000`. Everything else in that
   module derives (`OV5_NEW_LEN`, `ARENA_LO_NEW`) — do not touch them.
2. `ov5_cave.py:1134-1145` — the CAVE_FREE comment block currently reads "THE
   CAVE IS FULL". Rewrite: ceiling is now 0x023AA120, free tail 0xC000.
3. `otn_enhanced/knowledge/env.py:36` `OV5_END = 0x0239E120` -> `0x023AA120`.
   ⚠️ **Must land in the same edit** — this is the KB oracle's address-range
   test, so without it every ov5 proof above 0x0239E120 reports "outside every
   known oracle" instead of reading the image.
4. `otn_enhanced/knowledge/check_allocations.py:39` `OV5_END` -> `0x023AA120`.
   It already reads `ov5_cave.py` as text (`OV5_CAVE_PY.read_text`), so the
   better fix is to parse `RESERVE` from it rather than re-hardcode — these two
   copies are the same drift class that produced the stale "464 bytes free"
   comment.

## Then, in order (do NOT skip — this is shared state)

5. `check_allocations --emit`, then `check_allocations` (expect no overlaps).
6. `verify_knowledge` (expect 0 FAIL; `mem.ov5_cave_can_grow`'s proof asserts
   the DERIVATION, not the value 0x4000, so it survives the change by design).
7. Full chain: `-m ygo_tools.tools.finished_patches.apply_all_patches` (~25 min).
   ⚠️ `otn-chain-build-verify-artifact`: move the old ROM aside first and assert
   the BUILT ROM's final patch count **and** sha256 — exit code 0 has lied twice.
8. `_verify_all_patches.py` sweep (call `verify()` POSITIONALLY).
9. **One in-game duel** to confirm the smaller heap is still sufficient. That is
   the only thing that can confirm this; steps 5-8 cannot.

⚠️ If step 9 ever shows instability, the suspect is the heap, and the revert is
a one-constant rollback (plus items 2-4) — no patch needs editing, because
growing RESERVE moves only the ceiling and no CAVE_* slot changes address.

---

# LANDED 2026-09-02 — RESERVE 0x4000 -> 0x10000 (64 KB)

Applied exactly as planned, plus one improvement:

1. `ov5_cave.RESERVE` = **0x10000**. `OV5_NEW_LEN` and `ARENA_LO_NEW` derive.
2. `env.py` and `check_allocations.py` no longer HARDCODE the ceiling.
   `env._ov5_reserve()` parses `RESERVE` out of ov5_cave.py and
   `check_allocations` imports `env.OV5_END`, so the ceiling now has ONE source.
   (This is the duplication that produced the stale byte-count comment twice.)
3. The `CAVE_FREE` comment block was rewritten to say "never trust a byte count
   written here; compute `ceiling - CAVE_FREE`" and to record that `CAVE_FREE`
   is the first free ADDRESS, not the ceiling, so it does not move with RESERVE.

Measured geometry after the change:
```
RESERVE         0x10000 (64 KB)      ARENA_LO_NEW   0x023AA120
ceiling         0x023AA120           CAVE_FREE      0x0239E260
free tail       0xBEC0 (48832 B)     duel heap      215.7 KB
env.OV5_END == check_allocations.OV5_END == 0x023AA120   (both derived, agree)
```

## Validation

- `check_allocations`: 164 ov5 slots, **no overlaps, ledger in sync**.
- `verify_knowledge`: **398 facts, 361 PASS, 0 FAIL**. `mem.ov5_cave_can_grow`
  still passes because its proof asserts the DERIVATION, not the value 0x4000 —
  which is why it was written that way.
- Full chain rebuild: **ALL 47 PATCHES APPLIED**, WiFi timers last,
  `rom_all_patches.nds` 129,535,624 B,
  sha256 `015c688e0224f1546ee0ce063732b8039ed175a524d0f45d7a55b8e9783c118e`.
  (The old 16 KB-cave ROM was moved aside to `rom_all_patches.PREV-16KB-CAVE.nds`
  before building, per otn-chain-build-verify-artifact — exit code 0 has lied
  twice, so the artifact was asserted, not trusted.)
- `_verify_all_patches.py` against that ROM: **PASS 36, FAIL 0, SKIP 2**
  (patch_boggart_knight and patch_darksoul have no verify() of their own).

## STILL NOT CONFIRMED
**No duel has been played on the 64 KB-cave ROM.** Static validation cannot
confirm the smaller heap; only an in-game test can. The rollback remains one
constant (`RESERVE`) plus the ledger refresh — no CAVE_* slot moves, because
growing RESERVE moves only the ceiling.


## ov41 extent + whole-cave canary (2026-10-08)

- **Confirmed (read from EU rom.nds overlay table via ndspy this session):** ov41 = ram 0x022C5900,
  data 0x161E0 + bss 0xB60 = 0x16D40 B, ends **0x022DC640**. The ov5 cave [0x0239A120, 0x023AA120)
  is 0xBDAE0 above it, so ov41 never overlaps the cave; in a puzzle the cave holds stale or never-loaded RAM.
- Canary ROM data/over_the_nexus/working/rom_ov5_canary.nds (clean base, ov5 grown by RESERVE filled 0xA5, arena-lo raised to
  0x023AA120), sha256 d6cb9645442872abc9a16cbf5d0073c5ecbf983c720ee8d646b3fbfe03f54b55.
  Static checks pass. **AWAITING IN-GAME TEST.**
- Next experiment: save states as rom_ov5_canary.ml* in normal/turbo/tag/tag-turbo duels plus puzzles,
  then run: python -m otn_enhanced.tools.ov5_cave_check

- **Canary result 2026-10-08 (savestates rom_ov5_canary.ml1-ml6, read by ov5_cave_check this session):**
  ml1 normal, ml2 turbo, ml3 tag, ml4 tag-turbo: ov5 resident, all 0x10000 cave bytes still 0xA5 -> the
  whole cave survives live play in all four duel modes.
  ml5 puzzle editor, ml6 puzzle: ov41 resident, whole cave region overwritten (only 2 bytes coincidentally
  0xA5); ml5/ml6 contents identical; ~39.6 KB zeros, rest contains ARM code (B/BL 0xEA/0xEB words),
  e.g. @0x023A2120: 48fcffeb4b0100ea... -> something else is loaded/allocated over 0x0239A120+ in puzzle mode.
  Open: were ml5/ml6 entered after a duel in the same boot (i.e. canary was present and got overwritten)?
- User 2026-10-08: ml5/ml6 were the same boot as ml1-ml4 (so the canary WAS in RAM before them).
- **ml7 (user: "another puzzle without going through the puzzle editor"), read this session:** ov5 resident
  (first 1 KB at 0x022C5900 == ov5 image), whole cave 0xA5 intact. Contradicts the KB claim that a puzzle
  loads ov41 (mem.ov5_ov41_share_base). Open: is ov41 the PUZZLE EDITOR overlay, and was ml6 a puzzle
  launched from inside the editor? If so, ordinary puzzles keep ov5 and cave stubs work there.
- User 2026-10-08 confirmed: ov41 is the PUZZLE EDITOR's overlay (ml6 was played from the editor). Ordinary
  puzzles keep ov5 + the cave (ml7). KB: mem.ov5_ov41_share_base corrected, mem.ov5_cave_canary_all_modes added.
- User 2026-10-08 confirmed: ov41 is the PUZZLE EDITOR's overlay (ml6 was played from the editor). Ordinary
  puzzles keep ov5 + the cave (ml7). KB: mem.ov5_ov41_share_base corrected, mem.ov5_cave_canary_all_modes added.
- User 2026-10-08, verbatim: ".ml6 was reached through the puzzle editor mode, while ml7 was triggered
  through a puzzle mechanic in the game" -- consistent with the KB entries above, no change needed.

---

# DECISION (user, 2026-10-22: "Increase the cave"): RESERVE 0x10000 -> 0x14000

- Fresh scan (scratchpad heap_scan.py, every *.ml* in data/over_the_nexus/working with a duel arena = 62 states):
  61 states use 33.1..35.6 KB; the outlier rom_ov5_canary.ml1 = 109.2 KB. Heap at 0x14000 = 199.7 KB = 1.8x the outlier.
- env.OV5_END / check_allocations derive from RESERVE now (no hardcoded copies to edit).
- check_allocations OK; verify_knowledge 731 PASS 0 FAIL; EE fast build 119/119 sha256
  f13eb229bca665dd481f4ea4c5aae43f0224125c37e2039b671cb394b1e9ae07 (ov5 len 0xE8820, arena-lo 0x023AE120);
  verify sweep 100 passed 0 failed. Old chain ROM kept in the session scratchpad (sha f7a2b160...8d4c).
- Side fix needed for the build: patch_bulk_ydcs named three UNSHIPPED Infernoble donors (Sonic Duck x7, Tune Warrior,
  Water Spirit), which no longer resolve once card_text renames them -> written as their cids (same deck bytes).
- STILL NEEDED: one in-game duel on a ROM with the new heap base (the next Infernoble test ROM covers it).
