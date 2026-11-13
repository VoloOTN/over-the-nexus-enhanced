# ov3 code owned only by phantom cls records — findings (2026-09-27)

Question: how much overlay-3 space do cut cards take (cls0..3 records whose cid has
no card_prop row), and can that space host the stubs now in the ov5 cave?

Tool: `scratch/phantom_ov3_scan.py [rom]` (default `rom_all_patches.nds`), output
`scratch/phantom_ov3_scan_chain.json` (runs, dead fns, phantom records). ~6 s.

## Confirmed (this session, by the scan)

- cls tables read from the selector pool (dispatch.cls_table_selector): 4112 records.
- **Phantom records: 340 in the chained ROM (275 cids)** — cls1 144, cls0 80, cls3 66,
  cls2 50 = **8160 B of records**. Stock rom.nds: 395 records / 322 cids / 9480 B (the
  chain has spent 55 of them as count-neutral insert currency).
- Tokens are NOT phantoms: token cids (0x0F3C..) all have card_prop rows (4305 rows).
- **Code reachable ONLY from phantom records: 103 functions, 7874 B code + 776 B
  private literals = 8650 B in 130 runs** (chain). Stock: 9804 B / 147 runs.
  None of those bytes are written by any shipped patch (patched-vs-stock diff = 0).
- Run sizes (chain): 38 runs 64-127 B, 19 runs 128-326 B, the rest smaller.
  Largest: 0x0220A158 326 B (cls0 slot1 of 0x0EAB/0x0EAC/0x0EAE), 0x02212330 244 B
  (0x143E/0x1445), 0x021F0F9C 240 B (slot3 of 0x0E12), 0x021F1BFC 220 B, 0x0220A570 206 B.
- Hand check of 0x0220A158: starts at `push {r2-r6,lr}` after a pool, ends `pop {pc}` +
  pad at 0x0220A29E, next fn 0x0220A2A0 is live. Clean boundaries.
- "Dead" rule used: every inbound reference to any byte of the function — aligned u32
  (raw or |1) in ARM9 + all 50 overlays incl. the ov5 cave, Thumb BL/BLX anywhere,
  ARM BL/BLX anywhere, B/Bcc in ov3 — must come from a phantom record or other dead
  code. Callees reached only from dead code are added (fixpoint). Bytes a live entry
  can flow into are subtracted. Literals are counted only if every PC-rel load of them
  is dead. Coincidental data matches make the scan conservative, never optimistic.
- The four cls base literals appear exactly once each in ARM9+ov3: the selector pool
  0x0224A398/A0/A8/B0. So compacting the tables (dropping phantom rows, lowering counts)
  would free a contiguous tail per table: up to cls1 3456 B, cls0 1920, cls3 1584, cls2 1200.
- ov5 cave: CAVE_FREE 0x023A1FE8 → 32456 B reserved of 64 KB, **18492 B actually
  non-zero** across 305 slots. First-fit-decreasing into the 130 ov3 runs places
  **176/305 stubs = 8244 B**; the other ~10.2 KB (all the big stubs, max 844 B) do not fit.
- Build methods: of 82 modules calling install_cave, 29 use thumb_asm.asm(base, …)
  (relocatable by changing base), 53 hand-encode (BL offsets / pool words baked for
  the cave address → per-module rework).

## Per-card ranking (2026-09-27, `scratch/phantom_ov3_rank.py`)

- 8238 B of the 8650 B is owned by exactly ONE phantom cid; 412 B is shared by 2+.
- 198 of 275 phantom cids own NO exclusive code (their records point at shared live
  handlers) -- dropping them frees only 24 B per record.
- 108 of 275 phantoms are real cards in the 3DS build (names via CARD_Prop/CARD_Name_E,
  same cid space). Their dead ov3 code is plausibly a Konami implementation of that card
  (UNVERIFIED -- not diffed against the 3DS handler). Top ones: Cyber Esper 0x1AC7 278 B,
  Huge Revolution 0x15EF 234 B, Dark Catapulter 0x18F8 182 B, Disciple of the Forbidden
  Spell 0x19C2 174 B, Divine Dragon - Excelion 0x19D3 146 B, Ambulanceroid 0x1A50 178 B,
  Mutant Mindmaster 0x18E5 168 B, Maximum Six 0x1737 168 B, Kangaroo Champ 0x1866 134 B,
  Desertapir 0x178E 128 B.
- 167 are NOT in the 3DS; the 0x0E00-0x0EFF block dominates the top of the list:
  0x0E64 304 B, 0x0E12 268 B (4 records), 0x0ECE 266 B, 0x0EB7 262 B, 0x0EAB 240 B,
  0x0E3D 224 B, 0x0EAC 188 B, plus 0x1445 264 B, 0x143C 188 B, 0x1C5F 188 B, 0x1AB2 186 B.
- Already referenced by the ledger (cid still used as a sentinel/claim, records untouched):
  0x1A50 (shiens_dojo lp_literal), 0x18F8 (eclipse_wyvern populate row), 0x19D3 (grapha
  stat-engine arm), 0x12D6 (soul_charge populate row).

## ov5 cave footprint (2026-09-27, `scratch/ov5_cave_footprint.py`, run via `python - < file`
## because scratch/dis.py shadows the stdlib `dis`)

- 305 slots, 32456 B reserved, 18492 B non-zero -> 13964 B (43%) slack.
- Code is already tight: 0 identical stubs, only 2 32-byte windows shared by >=3 slots.
  Pointer literals 2160 B total, 1024 B unique (~1.1 KB duplicated, e.g. 0x0229AAFC x29).
- 64 all-zero slots = 8940 B: AI tables (ai_tables.py, not in the chain) 4608 B;
  comment says retired/unused 1248 B (ROWHOOK_OLD 256, NAST_RES 320, LIB_RETIRED 192, ...);
  runtime latches/scratch/DIAG 1268 B (latches+scratch MUST stay; *_DIAG ~560 B are debug);
  1816 B other (unshipped or superseded: MD_* Maiden, WW_* Warwolf, TGS_TRAMP, ...),
  each still needs a per-slot check that nothing BLs to it.
- Remaining ~5 KB is tail padding inside slots that do hold code.

## ov3-only census (2026-09-27, `scratch/phantom_ov3_census.py`, chained ROM)

- 304 phantom cids own >=1 row in a mapped ov3 table (donor_scan.OV3_STRUCTS + draw-count,
  LIST A/B); 275 of them in cls0-3, 29 only in other tables.
- Row bytes: cls 8160 (340 rows), criteria 480 (40), fusion A 192 (24), leave-mask 64,
  token 56, draw-count 48, list106 28, equip 12, summon lists 48, LIST A 2 = 9090 B.
- Plus 8650 B dead code (earlier scan) = 17740 B attributable to phantoms in ov3.
- Unmapped data-block u16 matches: 508 (1016 B) incl. coincidental numbers -- unproven.
- Code-block u32 literals in cid range: 2548 -- mostly plain numeric constants, and
  inline compares are not reclaimable anyway. Ignore.

## Ruled Out

- Nothing falsified yet.

## Open Questions

- The 5 dead functions with `add rX,pc` (jump tables) are sized by CFG walk only; their
  case bodies may be under-counted (safe direction).
- A phantom record re-keyed IN PLACE (Revolution Synchron's 0x164F style) keeps its
  pointers — if its code has been overwritten that card jumps into foreign code. Needs a
  check_allocations guard: no live record may point into a claimed ov3 run.
- Nothing proves the table-compaction idea in game; only the literal count is proven.

## Next Experiment

- Per-block proof before any claim, same bar as OV3_DEAD_BLOCKS (0x0225F240): re-run the
  three scans for that block, register it in OV3_DEAD_BLOCKS, zero the owning phantom
  records' slot pointers (or drop the rows) in the same edit.
- Pilot: move ONE small asm()-built, shared-path (puzzle-unsafe) ov5 stub into one run,
  single-card build, user in-game test in a normal duel AND a puzzle.
