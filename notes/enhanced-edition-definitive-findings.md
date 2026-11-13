# Enhanced Edition Definitive — findings (2026-09-10 / live)

Refactor of the `apply_all_patches` stack into `otn_enhanced/`.
Goal: byte-identical ROM, ~30 min -> ~1 min, shared utils instead of ~250 copy-pasted helpers.
`finished_patches/` is **never modified** — it is the oracle.

## Confirmed (this session)

**The 30 minutes is 136 pure-Python LZ compressions, not I/O.** Measured on this machine
against `data/over_the_nexus/working/rom.nds`:

| Operation | Time |
|---|---|
| `NintendoDSRom.fromFile` | 0.13 s |
| `rom.save()` (129,321,096 B out) | 0.33 s |
| `loadArm9Overlays([3])` (decompress) | 0.74 s |
| **`ov3.save(compress=True)`** (1,387,744 B) | **12.67 s** |
| **`ov5.save(compress=True)`** (870,432 B) | **8.57 s** |
| `MainCodeFile(arm9)` / `mc.save()` | 0.38 s / 0.00 s |

AST call-count over the 55 active steps: **88 `ov5_cave.install_cave`** (1 ov5 recompress
each) and **48 `save_overlay3`** (1 ov3 recompress each) = 88x8.6 + 48x12.7 ~= **23 of the
~30 minutes** in `ndspy._lzCommon.compress`. There is no C extension; it is a per-position
binary search over `bytes.rfind`.
Worst single modules: `patch_shooting_quasar` 9 `install_cave`, `patch_sea_lancer` 8,
`patch_thunder_sea_horse` / `patch_tg_warwolf` 6.
`patch_wifi_timers` changes **one u32** and pays a full 12.7 s ov3 recompression for it.

**The whole compression surface is ONE method.** All 13 sites in the repo are
`ov.save(compress=ov.compressed)` on an `ndspy.code.Overlay`: `overlay_io.py:63`,
`ov5_cave.py:1623`, `ov3_cave.py:121`, `pack_unlock_conditions.py:339`, `tg_table.py:235,491`,
`patch_wifi_timers.py:135`, `patch_unlock_all_packs.py:132`, `patch_bulk_memory.py:114`,
`overlay5_expand.py:187,217`, `app/nds_dash.py:1480`. Each is followed by the **identical**
overlay-table writeback (ramSize @+0x08, `(flags<<24)|csz` @+0x1C), so one finalize routine
reproduces all of them.

**`loadArm9Overlays` re-parses and re-decompresses on every call** — confirmed by
`inspect.getsource`: it calls `code.loadOverlayTable(...)` fresh each time and
`Overlay.__init__` decompresses eagerly. That is why caching the `Overlay` objects is the
hook that makes deferral safe.

## *** FULL-CHAIN BYTE-IDENTITY PROVEN (2026-09-11) ***

```
original chain (apply_all_patches, 55/55)   129,622,664 B
new engine     (build.py, 55/55, 234 s)     129,622,664 B
both sha256    0f7f9c1aa16712f6073f3a0c8c7be4cd2f32923fb6fb91a54fafcb81e0708f06
```

Original chain log shows 55 step lines and `ALL 55 PATCHES APPLIED`. **30 min -> 234 s (7.7x),
same bytes.** This is the whole correctness claim for the refactor: no card behaviour can have
changed, because no byte did.

### Where the 234 s actually goes (compression is no longer the bottleneck)

| Step | Time |
|---|---|
| 46 `patch_field_backgrounds` | **105.0 s** |
| 42 `patch_card_art` | 24.3 s |
| 30 `patch_snoww` | 13.1 s |
| finalize (1 ov3 + 1 ov5 compress + save) | ~21 s |
| the other 52 steps | ~1.2 s each |

Three steps are ~60% of the build. The 136 compressions are gone; what remains is image
encoding and pac rebuilds. 105 s for field backgrounds is unexplained and worth a look.

### TWO BUGS THE IN-MEMORY BUILD EXPOSED (both real, both pre-existing)

**1. `rom.files` entries must be `bytearray`, and ~20 modules make them `bytes`.**
`fromFile` produces 127 **bytearrays**, but modules assign immutable `bytes` back
(`rom2.files[fid] = bytes(pac_data)` in reborn_tengu:535, ceruli:551, grapha:1459,
gates_of_dark_world:1131, jet_warrior:644, orient_dragon:416, accel_synchron:1038, ...).
The old chain never noticed because **every step re-read the ROM from disk, which laundered
the types back**. `patch_bulk_card_props.py:209` is the ONLY in-place `rom.files` mutation in
the repo:

```python
old_rom.files[old_rom.filenames.idOf(pac_path)][addr:addr + len(data)] = data
```

-> `TypeError: 'bytes' object does not support item assignment` at step 45 on the first full
run. Fixed by `Session.normalise()`, which restores exactly the types a fresh `fromFile`
guarantees. **Types only, never bytes** -- proven by the matching hash above.

**2. `patch_bulk_card_props.py:204-207` does raw file I/O that bypasses every hook**
(`open(src,'rb').read()` then `open(out,'wb').write(...)`), so the work path must exist as a
real file. It had been silently succeeding off a LEFTOVER file from an earlier run. The
session now materialises the work path deliberately and unlinks it on exit. Its content is
never read back -- the module takes all real data from the ROM object -- so seeding it with
the clean ROM is safe.

**3. `apply_all_patches.main()` is not callable as a library function.** It raises
`NameError: name 'MAKE_PATCH' is not defined` at line 2227, because `MAKE_PATCH` (and
`WRITE_TEXT`) are assigned only inside `if __name__ == "__main__"`. The 55 patches had all
been applied by then, so the ROM was intact -- but any harness that does `chain.main()` eats a
traceback at the end. `build.py` has no such split.

---

**BYTE-IDENTITY PROVEN FOR STEPS 1-2** (2026-09-10, superseded by the full-chain result above).
Same sha256 from both paths:

```
642166d68ac3ddef8e0086831569669a42ca3e74d58a45d00cd3594237b405ec   129,524,872 B
```
* old file-based path: `scratchpad/oracle_slice.py 2` (calls the same two `main()`s with real
  file I/O, exactly as `apply_all_patches` does)
* new in-memory path: `build.py --upto 2`

This slice is not trivial — it covers an **ov5 cave install** (reborn_tengu's selector blob),
the **ov5 growth + arm9 arena-lo raise**, an **ov3 edit**, three count-neutral data inserts,
and a **bin2.pac rebuild** (+2,048 B). Full 55-step confirmation pending the baseline run.

**Measured new-build speed:** 2 steps in 24.3 s, of which ~21 s is the one-time finalize
(12.7 ov3 + 8.6 ov5). Per-step cost is ~1-3 s (reborn_tengu 2.9 s, boggart 1.2 s), dominated
by `bin2.pac` parse/rebuild, not compression. Projected full build **~75-90 s**, not the 40 s
originally estimated.

**The duplication census** (AST over 80 modules, 1,049 functions under 550 distinct names):
`_off`x28 + `off`x12, `_bl`x14 + `_thumb_bl`x5, `verify`x62 (3 shapes, 2 return contracts),
`check`x28 (2 shapes), `apply_effect`x36, `_insert_sorted`x9, `_keys`x7, `_crit_rows`x6,
`_orig`x8, `_iter_paths`x6, `_build_filter`x8, `_build_wrapper`x7. Nine `_bl` bodies are
**byte-identical**. `_insert_sorted` exists in **three incompatible argument orders** —
`patch_tg_striker.py:340` swaps `stride`/`count` against every other copy.

**All 60 `_apply_*` wrappers in `apply_all_patches.py` have a one-call body** (AST-verified),
i.e. 1,900 of its 2,239 lines are docstring + boilerplate around 60 calls.

**The two shipped `_insert_sorted` algorithms ARE byte-equivalent — and one has a latent bug.**
Differential test (`test_tables.py`) on the real criteria registry from `rom.nds`
(0x022713C4, 1388 x 12 B, sorted by the u16 cid at +0), phantom 0x1DBD @ index 694, across
five insert positions — far before / just before / just after / far after the phantom, and
smallest-in-table:

| Position | cid | Result |
|---|---|---|
| far before phantom | 0x1888 -> idx 347 | all three identical |
| just before phantom | 0x1DBC -> idx 694 | all three identical |
| just after phantom | 0x1DBE -> idx 694 | all three identical |
| far after phantom | 0x214D -> idx 1041 | all three identical |
| smallest in table | 0x0D47 -> idx 0 | all three identical |
| **largest in table** | 0xFFFF -> idx 1387 | **variant B raises `StopIteration`** |

Variant A = `patch_grapha.py:456` (in-place memmove; also snoww, reborn_tengu, hanzo, nast,
eclipse_wyvern, boggart_knight). Variant B = `patch_tg_striker.py:340` (unpack-all/repack;
darksoul and gravekeepers_recruiter import it) — **and B takes `stride` and `count` in the
opposite order to A**, which is a live footgun, not just duplication.

B's insert position is `next(i for i, r in enumerate(recs) if r[0] > cid)`, which has no
fallback when the new cid is larger than every remaining key: it raises `StopIteration`
instead of appending. Not hit by any shipped card (all inserted cids are mid-table), so it has
never fired — but the next card with a high cid on a B-derived table would have hit it.
`tables.insert_sorted` uses `sum(1 for r in recs if r[0] <= cid)` and appends correctly.

**The util equivalence checks pass** (`test_utils.py`, 5/5): `thumb.bl` reproduces
`criteria_row_hook._bl`, `patch_darkflare._bl` and `patch_boggart_knight._thumb_bl` on four
real hook sites; `b`/`bcond`/`ldr_pc` match `patch_darkflare._b` and
`patch_white_dragon_ninja._bcond`/`_ldr_pc`; `Ov.keys` agrees with `patch_grapha._keys` on the
full 1388-row registry.

## Ruled Out

* **"Deferring compression will break an idempotency guard."** No. Every guard in the stack
  reads `ov.data`, never the overlay table or `ov.compressed`: `tg_table.py:212,219,360,368,517,526`,
  `ov5_cave.install_cave:1665`. Grep for a *branch* on `.compressedSize` / `arm9OverlayTable`
  returns nothing but `pack_into` writebacks. `session.assert_no_table_readers()` now re-checks
  this on every build so the assumption cannot rot silently.
* **`ov3_cave.geometry()` (`ov3_cave.py:208`) reads the table** — but it is called only by
  `_build_ov3_canary.py`, never in the chain, and no active patch uses `ov3_cave` at all.
* **"ndspy's `rom.save()` rebuild is the bottleneck."** No — it re-concatenates all 127 files
  and regenerates FNT/FAT every time, but that is 0.33 s. Ignore it.
* **`patch_bulk_ydcs.py` (16,788 lines) costs build time.** No — its step is commented out
  (`apply_all_patches.py:2123`). It is 304 hand-written decklists, pure data.
* **tqdm is doing anything useful.** `apply_all_patches.py:2214` wraps the loop but four
  `print()`s inside the body destroy the bar. Zero runtime effect. (`from time import time`
  at line 59 is imported and never used.)

## Open Questions

* Does the full 55-step chain hash match? (baseline running, ~30 min)
* Does the per-step `bin2.pac` parse dominate the new build enough to be worth caching? At
  ~1 s/step it is now the largest remaining cost, ahead of the two compressions.

## Next Experiment

**Step 0 — both ROMs on disk are STALE.** After the proof was taken, the user modified four
patch modules (2026-09-11): `patch_boggart_knight.py` (+3), `patch_card_art.py`,
`patch_shiens_dojo.py` (+71/-16), `patch_tour_guide.py` (+3). `rom_all_patches.nds` and
`rom_ee_definitive.nds` were both built from the PRE-EDIT code. User instruction, verbatim:
*"please do not make comparisons just yet."* Rebuild **both** sides before any `--compare`;
a mismatch against a stale baseline means nothing.

⚠️ Run the oracle as a **script** (`python -m ...apply_all_patches`), never `chain.main()` —
see the `MAKE_PATCH` NameError above.

**Step 1 — why is `patch_field_backgrounds` 105 s?** 573 lines, a pac rebuild, not a
compression; nothing in the measured cost table explains two minutes. Measure it in isolation
first:

```
.venv-1/Scripts/python.exe -m otn_enhanced.build \
    --only patch_field_backgrounds -v --out data/over_the_nexus/working/rom_fieldbg_probe.nds
```

Still ~105 s ⇒ inherent to the module (profile it, fix in the rewrite). Fast in isolation ⇒
the cost depends on accumulated session state, which is a finding about `session.py` and must
be understood before Phase 3.

**Step 2 — Phase 3**, cheapest batch first, each module gated by
`equiv.py <module>` ⇒ `[IDENTICAL]`, then a full `--compare` per batch (a per-module diff
cannot see cross-patch interaction). Order and full detail:
`PROMPT_enhanced_edition_definitive_phase3.md`.

## STATUS

**FULL-CHAIN BYTE-IDENTITY CONFIRMED 2026-09-11** — both builds 55/55, sha256
`0f7f9c1aa16712f6073f3a0c8c7be4cd2f32923fb6fb91a54fafcb81e0708f06`, 129,622,664 B.

Nothing here is in-game confirmed and nothing needs to be: the ROM is byte-for-byte the one
the old chain produces, so no card behaviour can have changed. `steps.MIGRATED` is still
empty — every step runs the original `finished_patches` module, and `finished_patches/` has
not been modified.
