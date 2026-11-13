# T.G. Striker (0x1F18, donor Ally Mind) — claims moved out of the old module on DSL conversion 2026-10-29

All **UNVERIFIED (inherited, not re-proven this session)**. The old `tg_striker.py` is recoverable from git history;
`finished_patches/tg_striker.py` is the oracle and also keeps the GDB trace that pinned E1's register facts.

## Confirmed (this session)
- Byte-identity only: DSL build == original build, sha256 `71884afa…d1245` (full `cmp`). Nothing run in-game.

## Inherited, UNVERIFIED
- E1: the hand-SS OFFER is decided by dispatch `0x0225E51C` alone (bit 0x4 consulted at `0x0224C026`, `BL 0x0225E51C; ORR R5,R0`).
  Retargeting the dispatch-tree node or editing the donor's cls/populate/registry records was "proven in-game" NOT to work, hence the
  shared trampoline. Encoded in the verb's docstring (`special_summon_self_from_hand`), not re-proven.
- E2 needs all four pieces together (arming trampoline, registry row cid repoint keeping resolver `0x02254221`, cls2 insert,
  populate insert); any one alone fires nothing. Encoded in `add_from_deck_end_phase` docstring.
- Arming trampoline gates on `[sp+0x90]` DESTROYED so Tribute / Synchro Material do not arm. Lives in `tg_table.py` (untouched).
- Name: the donor's English name run is 12 B, "T.G. Striker" needs 13 B; old module used "TG Striker" via `force_name_in_place`.
  That path is skipped for cids in `card_text.CARD_TEXT` (0x1F18 is), so the full printed name ships; the DSL file just uses `CARD_TEXT`.
- Stock populate holds phantom `0x234E` at rows 1238 AND 1239; the insert spends one (`Row(stock_copies=2)`).
- Populate table is counted PAST the `0xFFFF` sentinel (1391, not 0x56C): `dsl.CRITERIA_PAST_SENTINEL`.
- Phantoms: cls2 `0x2347`, populate `0x234E`, T.G. table `0x2510` (Striker's real Konami ID); registry row phantom `0x1A9F`.
- `finished_patches/tg_striker._insert_sorted` is imported by darksoul, gravekeepers_recruiter, shooting_quasar, tg_warwolf,
  tg_rush_rhino, test_tables — that is the **finished_patches** original, not this module; unaffected.

## Dropped (not encoded anywhere)
- `ENABLE_E2` switch and the ov5 placement (`ov3=False`) of the old module: ov3 was the default and the only path the chain uses.
- Import-time cave-collision asserts against Warwolf's ov5 block (ov3 slots now; `check_allocations` covers them).
- Module-level `SLOTS5`/`apply_effect`/`_build_*` exports: nothing imports them (grep 2026-10-29).
