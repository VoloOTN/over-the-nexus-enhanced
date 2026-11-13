# Current baseline

The sha256 a correct build produces today. `build --compare data/over_the_nexus/working/rom_baseline.nds`
checks against the frozen copy of the Enhanced ROM (`build.BASELINE`).

| Build | Command | sha256 |
|---|---|---|
| Enhanced (154 steps) | `uv run python -m otn_enhanced.build` | `a4e4e1bd6a06144a446687a49637e15d663d8261cdbf1e203fa5d8a4238c52ee` |
| Vanilla+ (46 steps) | `uv run python -m otn_enhanced.build --vanilla-plus` | `cb9acb1ead276f047885379b0876bbd04edff871f57ebba88d0153f9b2776aea` |

Recorded 2026-11-13 with the pins in [docs/SETUP.md](../docs/SETUP.md) (Arm GNU 14.2.Rel1, CardWorkshop
`3934f5c…`, `uv.lock`) from the EU anti-piracy-fixed ROM (sha1 `a90f3d0c…`).

Verify on that Enhanced ROM: 143 passed, 0 failed, 5 modules without `verify()`.
A passing `verify()` is not in-game confirmation.

## What changed since the previous recorded hashes

- `steps.py`: a `data.card_genre` pass after the Monarch set (every Monarch card shipped its donor's
  search-filter genre before).
- `data/bulk_ydcs.py`: deck-name matching now mirrors `PACFile.get_clean_name()` exactly, so
  `:wcs084_formula.ydc` is replaced (it was silently skipped).

## Re-baselining

Only on purpose (a card, shared data or a pin changed): rebuild, run `verify` to `0 failed`, copy the
result to `rom_baseline.nds`, and update this table and the hashes in
[building-and-verifying](../docs/tutorials/building-and-verifying/HOWTO.md).
