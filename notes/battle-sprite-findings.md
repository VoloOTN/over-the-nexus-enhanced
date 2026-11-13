# 2D battle (attack) sprite — why the June splice failed

Investigated 2026-11-04. No ROM built, nothing tested in-game. Status of any future
splice: **AWAITING IN-GAME TEST**.

The sprite in question = the monster cut-out shown when it attacks:
`Data_arc_pac/duel2d/BattleMonster{1,2,3}.pac`, one LZ11 NTBG file per id.
(NOT `BustupL/R.pac` — those are duelist portraits.)

## Confirmed

* **Loader = ov3 ARM fn 0x0218C448** (KB `battle_sprite.path_loader`, ANCHORED). Format
  strings at 0x02293A64 / 0x02293A88 / 0x02293AB0 / 0x02293AD0, each referenced once from its
  literal pool (0x0218C568..0x0218C57C). Disassembly (capstone ARM, stock rom.nds):
  `cmp r6,#0x1F40 -> movge r4,#3 ; mov r4,#2 ; cmp r6,#0x1900 -> movlt r4,#1` = pac select.
  Try order: `%d_%s` (suffix 'L'/'R' from ptr table 0x02293794) -> plain `%d.LZ5bg`
  (returns 1 = mirror when side r5 == 0) -> `BattleMonster1/0000_%s.LZ5bg` placeholder.
  Existence check 0x02016C00 between each. The id comes from 0x0218C38C (cid unless remapped;
  falls back to 0x1362 = 4962 when 0x02029E60(id) == 0 and a flag bit is clear).
* **Old donors have only the plain file**: 5588 (0x15D4, BM1), 7398 (0x1CE6, BM2),
  8325 (0x2085, BM3), 6587 (0x19BB, BM2) each = exactly `<cid>.lz5bg`, no `_l`/`_r`.
  So the plain file IS what the game reads for them — the side-file shadowing idea is dead
  for these four (see Ruled Out).
* **ROOT CAUSE: `otn_enhanced/rom/extract_card_images.py::parse_graphics_pac` is off by one.**
  It drops the first offset-table entry, so name i is paired with entry i+1's data.
  Checked against CardWorkshop's `tools/pac.py::parse` (exact format: name records
  `{u8 len, u8 xor-hash, name}` in 0x200 blocks, then 63-entry chunks `{u16 0, u16 cnt|0xFFFF,
  u32 0}` + `{u32 rel_off, u32 size}`, data 0x200-aligned):
  BM1 ours 1022 entries vs 1023 names, **1022/1022 mismatched**; BM2 854/855; BM3 961/962.
  First three: ours `5425_l @0x7000 0xc31` vs true `5425_l @0x5600 0x190a`, and true `3972 @0x7000 0xc31`.
* **What the June splice (git `e3c1f1b^` patch_card_art.py `_patch_battle_sprite`) actually did**,
  replayed offline on stock rom.nds with the same parser (unchanged since, 1-line import diff):
  | donor | data written into | size field written into | donor file |
  |---|---|---|---|
  | 5588 | `6123.lz5bg` | slot of `4368_l.lz5bg` (0x1110 Grandsoil!) | untouched |
  | 7398 | `6420_r.lz5bg` | slot of `6420_r.lz5bg` | untouched |
  | 8325 | `8163.lz5bg` | slot of `8163.lz5bg` | untouched |
  | 6587 | `7959.lz5bg` | slot of `7959.lz5bg` | untouched |
  => in-game the donors kept their stock sprite, and four other monsters got a wrong/corrupt one.
  That fully explains "did not work in-game". The *encoder* was never actually exercised.
* **Stock format survey (all 2840 files)**: 100% LZ11 (0x11); all 32x12 tiles = 256x96;
  2541 x 4bpp (BGDT flags 0xFF00) with blocks PALT+BGDT+DFPL, 299 x 8bpp (flags 0xFF01)
  with PALT+BGDT only. Tilemap palette banks 0..15 ALL used (bank 15: 28233 tiles) —
  no reserved row 15 here, unlike the 64x64 zoom art.
* Our encoder output (`card_art_codec.encode_battle_sprite_256x96`) for the four PNGs has the
  stock shape (PALT/BGDT/DFPL, flags 0xFF00, 32x12, 256 colours), and LZ11 round-trips; all
  four fit the true entry's 0x200 slack. (Shape only — not shown to render correctly.)

* **Parser FIXED 2026-11-04**: `parse_graphics_pac` now wraps a new exact
  `graphics_pac_layout(data) -> [(name, abs_off, size, slot)]`. Check: for all three pacs it
  equals CardWorkshop `pac.parse` entry for entry (1023/855/962), every chunk header is
  `{0, cnt, 0}`, and all 2840 entries LZ-decode to `NTBG`.
* `rom_all_patches.nds` (built 2026-11-04 09:54): all three BattleMonster pacs byte-identical to
  stock rom.nds — the June mis-splice never shipped.
* **Current donors** (all BM1, plain file only, 4bpp PALT/BGDT/DFPL): 0x13A5 Boggart Knight `5029`,
  0x1463 Reborn Tengu `5219`, 0x13B8 Mystic Piper `5048`, 0x0FB4 GK Recruiter `4020`,
  0x1783 Darksoul `6019`. New LZ11 sizes vs slot: 5029 0x1221/0x2000, 5219 0xdd0/0x1600,
  5048 0x98f/0x1000, 4020 0xc51/0x1800 (fit); **6019 0x1554/0x1200 does NOT fit** -> needs a repack.
* **BUILT `_build_battle_sprite.py` -> `rom_battle_sprite.nds`** (base rom_all_patches.nds),
  sha256 `4da490ae34e8756e73660254084321dc108fcc4263f4104fe17af606ba304a03`. In-place splice of the
  four fitting donors (own slot + own size field). `verify()`: every other ROM file identical, every
  other pac entry identical (size + bytes), offsets/slots unmoved, the four entries = fresh encode.
  Decoded with CardWorkshop's independent `bgdt_image`: all four render as clean cut-outs with
  transparency. **AWAITING IN-GAME TEST.**

* **Cut-out softening (2026-11-04, preview only, nothing written to card_arts/)**: the old
  `make_card_art` rembg call (alpha matting, erode 3, fg 240, post_process_mask) eats thin parts.
  Softer recipe that the user was shown: raw `isnet-general-use` mask run directly in onnxruntime
  (rembg preprocessing: 1024² LANCZOS, mean (0.485,0.456,0.406), std 1, min-max output) ->
  MaxFilter grow 0.8% of min side -> cutoff 48/255 -> `make_character_256x96` -> drop 8-connected
  blobs < max(40 px, 2% of opaque) on the 256x96. rembg itself would not install under uv
  (numba wheel file-lock, os error 32 twice); onnxruntime alone works via `uv run --with onnxruntime`.
  Known bad cut-outs even with this: grandsoil, grapha, aratama, accel_synchro, gates,
  infernoble_knight_captain_roland / _captain_oliver, scrap_archfiend, upstart_ninja.
* **Soft cut-out is now the `make_card_art` default** (user approved 2026-11-04): onnxruntime-only
  (`bgremove` extra no longer lists rembg). Check: re-running the new `_remove_background` +
  `make_character_256x96` on all 123 `artwork_full` PNGs is pixel-identical to the approved preview
  (123/123). **User 2026-11-04: "Do not wire this in, the arts are still not perfect"** — so no
  character PNGs written to card_arts/, card_art.py and the chain untouched, rom_battle_sprite.nds
  still carries the OLD cut-outs.

* **Tolerance candidates (2026-11-12, preview only)**: `scratch/battle_sprite_candidates.py` wrote 10
  variants for each of the 104 monster entries in `card_art.CARDS` (type read from rom_all_patches.nds card_prop)
  to `data/over_the_nexus/card_arts/battle_sprite_candidates/<folder>/t01..t10_keep<P>pct_cut<C>.png`
  (1040 PNGs). The user deletes all but the best one per folder; nothing is wired in.
  **Ruled out: a fixed cutoff range across cards.** First attempt used fixed cutoffs 16..224 and on Aratama every
  cutoff >= 64 left slivers, because isnet mask strength varies per art. Fix: the per-card cutoff is the mask
  quantile that keeps 80/70/62/55/48/42/36/30/24/18% of the art (mask grown 0.8%, as in make_card_art).

* **Wired into the build 2026-11-13** (user: "Done wire it in"): `otn_enhanced/data/battle_sprites.py`, two
  steps in `steps.py` right after each "Card art" step (vanilla+ cids / REST_ART). The user picked one cut-out per
  card; the picks were copied to each card's `<base>_character_256x96.png` (119 cards). **AWAITING IN-GAME TEST.**
  - **Side files PROVEN (ov3 disasm 0x0218C49C..0x0218C4A0 + table 0x02293794 = ["L","R"])**: suffix = table[r5],
    and the plain file is mirrored when r5 == 0. So `R` = plain orientation and `L` = its mirror. Stock `_l`/`_r`
    pairs are mirror images (e.g. 6093: mean abs diff vs mirror 0.5). Five cids have side files: 0x0FD0 Uni-Zombie,
    0x1110 Grandsoil, 0x1145 Blaster, 0x17CD Redox, 0x181C Unknown Synchron. Both files are written.
  - **Repack rule PROVEN**: all three stock pacs store entries in table order, each 0x200-aligned and packed, with
    the file end 0x200-aligned. Re-laying the data that way reproduces each stock pac byte-for-byte (asserted on
    every run). So size growth (Darksoul) is no longer a problem.
  - **Name hash** in the name records = XOR of the name bytes (checked on the first six BM1 records).
  - Skipped: 0x14CF The Prime Monarch has no sprite file in BM1 (stock Trap). Adding a name entry is unproven
    (lookup 0x02016C00 not read). Thestalos the Shadowfire Monarch has no cid (not in CARDS).
  - verify(): each replaced entry decodes back to the pick's opaque mask (>= 97%); every other entry is
    byte-identical to stock rom.nds. Standalone: 123 entries replaced, OK.
  - **Test ROM 2026-11-13**: `rom_battle_sprite.nds` = rom_all_patches.nds (2026-11-12 16:01) + this step. Only the three
    BattleMonster pacs differ, arm9 and all overlays are identical. sha256
    `649e1b34c93ba14e9a7031b984fd98e36c39691cf8c4a26d478b3fbb1d26388e`. The full `otn_enhanced.build` aborted
    BEFORE any step on the deck preflight (`wcs089_soulogre.ydc`, the user's uncommitted ydc_decks.py WIP), so the
    combined ROM was not rebuilt with this step.

## Ruled Out

* "A `<cid>_l/_r` file shadows the plain file we edited" — false for all four donors
  (only the plain file exists). It IS a real rule for cids that have side files
  (e.g. 4048 has `4048_l`/`4048_r`): those two must be replaced, not a plain file.
* "LZ type mismatch" — stock is LZ11 too.

## Open Questions

* Does the encoder output render correctly on hardware (index 0 transparent, DFPL meaning)?
  Unknown until a correctly-spliced ROM is tested.
* `extract_card_images.py` battle_monsters PNG export uses the same parser, so its PNG
  names are off by one as well; anything chosen from those PNGs may be mislabelled.
* New cids (e.g. Reborn Tengu 0x25E3 = 9699 -> BM3) have no file; adding a name entry needs a
  full pac rebuild (CardWorkshop-style `build`) — not tried.

## Next Experiment

1. ~~Fix the parser~~ done. ~~Build a test ROM~~ done (`rom_battle_sprite.nds`).
2. User test: attack with XX-Saber Boggart Knight / Reborn Tengu / Mystic Piper /
   Gravekeeper's Recruiter, as the player AND as the CPU (the CPU side uses the mirrored path).
   Expected: the new cut-out each time, the right way round, no holes or colour blocks.
3. If it works: Darksoul needs a full BattleMonster1 repack (offsets recomputed, size grows);
   then decide whether to fold the step into card_art.py / the chain (needs user approval).
