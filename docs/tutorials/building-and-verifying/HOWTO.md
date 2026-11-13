# Build, compare and verify

## Goal

Produce the Vanilla+ or Enhanced ROM, prove it is the ROM you think it is, and check that every card's edits
landed.

## Before you start

- Clean source ROM: `data/over_the_nexus/backup/eu_apfix.nds` (EU, anti-piracy fixed). `build.CLEAN_SRC`.
- Python: `uv run python` (see [docs/SETUP.md](../../SETUP.md)); `uv sync` installs `ndspy` and `capstone`.
- Run everything from the repo root. Paths like `data/over_the_nexus/working/...` are relative to it.

## Steps

### 1. Build

```
uv run python -m otn_enhanced.build                  # Enhanced: all 120 steps
uv run python -m otn_enhanced.build --vanilla-plus   # stops at steps.VANILLA_PLUS_END (46 steps)
```

| Output | Default path |
|---|---|
| Enhanced | `data/over_the_nexus/working/rom_all_patches.nds` |
| Vanilla+ | `data/over_the_nexus/working/rom_vanilla_plus.nds` |

Vanilla+ takes about 3 minutes and the full build 10–16 minutes. The build prints the step count and a sha256 at
the end. Read both: a build that dies part-way can leave a ROM that looks fine.

Useful switches:

| Switch | Use |
|---|---|
| `--out PATH` | Write somewhere else. Use this for experiments so you never overwrite a ROM you are testing. |
| `--only cards.jet_synchron` | Run one step against the clean ROM. Matches `Step.module` or `Step.name`. |
| `--upto N` / `--start N` | Run a slice. Bisect a divergence with `--upto`. |
| `-v` | Show each module's own output. Quiet by default. |
| `--no-text` | Skip name and description writes. |
| `--strict` | Compress at every step (slow). Tells a deferred-compression bug from a caching bug. |
| `--compare FILE` | Exit non-zero unless the result has the same sha256 as FILE. |

The steps live in `steps.py` as data. Order matters; see [shared-hooks-and-ordering](../shared-hooks-and-ordering/HOWTO.md).

### 2. Prove two builds are the same

`--compare` hashes the result against a ROM you saved earlier. Compare against a **frozen copy**, never the
build's own `--out`: the build refuses that because it would always pass.

```
cp data/over_the_nexus/working/rom_all_patches.nds data/over_the_nexus/working/rom_known_good.nds
# ...change something...
uv run python -m otn_enhanced.build --compare data/over_the_nexus/working/rom_known_good.nds
```

Current reference hashes (also in [notes/CURRENT-BASELINE.md](../../../notes/CURRENT-BASELINE.md), with the frozen
Enhanced ROM at `data/over_the_nexus/working/rom_baseline.nds`; a refactor check, not an in-game result):

```
Enhanced   a4e4e1bd6a06144a446687a49637e15d663d8261cdbf1e203fa5d8a4238c52ee
Vanilla+   cb9acb1ead276f047885379b0876bbd04edff871f57ebba88d0153f9b2776aea
```

They change whenever a card or shared data changes on purpose. Re-record them then.

### 3. Verify every card

```
uv run python -m otn_enhanced.verify data/over_the_nexus/working/rom_all_patches.nds
uv run python -m otn_enhanced.verify <rom> --only cards.mystic_piper
```

`build` applies; it does not verify. This sweep calls each step module's `verify()`.

- It calls `verify()` **positionally**. The ROM path is the first parameter everywhere but is named `out` in
  some modules and `out_path` in others; a keyword call fails on the second kind.
- A `None` return is a **pass**. Only `False` or an exception fails.

### 4. Check one rewritten card against a reference

```
uv run python -m otn_enhanced.equiv cards.mystic_piper            # vs the old-tree original
uv run python -m otn_enhanced.equiv cards.mystic_piper --ref some.module.path
uv run python -m otn_enhanced.equiv cards.mystic_piper --self     # runs the module twice
```

Both versions run on the same in-memory ROM state, so the diff is exactly that card's bytes. It cannot see two
cards fighting over one shared row; follow it with a full build and `--compare`.

### 5. Allocation guard and the knowledge base

```
uv run python -m otn_enhanced.knowledge.check_allocations          # runs inside every build too
uv run python -m otn_enhanced.knowledge.check_allocations --emit   # rewrite the ledger
uv run python -m otn_enhanced.knowledge.author_facts               # regenerate docs/engine/*.yaml
uv run python -m otn_enhanced.knowledge.verify_knowledge           # run every proof
```

The ledger is `otn_enhanced/docs/engine/allocations.yaml`. The build aborts on any overlapping cave slot or
double-claimed phantom cid before it writes a ROM.

### 6. Unit checks

```
uv run python -m otn_enhanced.tests.test_tables
uv run python -m otn_enhanced.tests.test_utils
uv run python -m otn_enhanced.tests.test_lz11
uv run python -m otn_enhanced.tests.test_card_text
uv run python -m otn_enhanced.tests.test_pac_alignment
```

## Worked example: add one card and prove nothing else moved

1. Build a baseline and keep it: `build --out data/over_the_nexus/working/rom_before.nds`.
2. Add the card module and one `Step(...)` row in `steps.py`.
3. Build to a different file, then `verify` it: every old card must still pass, plus the new one.
4. Binary-compare the two ROMs if the change should be additive; any unexpected difference points at a shared
   table you touched.

## Check it

- Step count printed equals the number of rows you expect.
- sha256 is what you expect (or deliberately new).
- `verify` reports `0 failed`.
- `check_allocations` exits 0.

## Pitfalls

- **Do not edit `.py` files while a build runs.** Step modules are imported lazily, so a mid-build edit changes
  what gets built.
- A static pass is not a working card. Only the emulator is ground truth.
- Do not write "confirmed" or "shipped" into notes or the knowledge base unless the in-game test passed.
- `rom.nds` (the stock ROM) and `eu_apfix.nds` (the build source) are different files. A card module's own
  `SRC` default (for example `rom_ov3_compact.nds` in `cards/mystic_piper.py`) is what its standalone
  `main()` reads; the build ignores it and feeds each step the in-memory ROM.
- Build output is large (about 129 MB per ROM). Delete experiment ROMs you no longer need.

## Known rough edges

- `session.py` monkeypatches `ndspy` to defer compression. It is the reason the build takes minutes instead of
  half an hour, and also the most fragile file here. `--strict` is the escape hatch.
- Step-order constraints live only in comments in `steps.py`. A wrong order fails loudly for some cards and
  silently for others.
- `equiv.py` defaults its reference to the pre-refactor tree. Pass `--ref` once that tree is gone.
