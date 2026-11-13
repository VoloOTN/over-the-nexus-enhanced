# Where injected code lives, and how to claim space

## Goal

Choose a home for a stub, claim the space without colliding with another card, and register the claim so the
build guard keeps it that way.

## Before you start

Overlay 3 (the effect engine) **cannot grow**: its RAM slot is full up to `0x022C5900`, and growing it
black-screens at boot. There are two places to put new code instead.

| Home | File | Runs in | Use for |
|---|---|---|---|
| **ov3 pool** | `effects/cave3.py` (`CAVE3_*`) | every duel mode, including puzzles | default for new work |
| **ov5 cave** | `effects/ov5_cave.py` (`CAVE_*`) | normal duels only | older stubs; ov5 is evicted when a puzzle is started from the puzzle editor (overlay 41 loads at the same address) |

The project direction is to move everything into the ov3 pool. Do not invent a third home (a new overlay, an
ARM9 BSS raise, unused ov3 zero-runs) without asking first.

## ov3 pool

Step 0 of the build (`system/ov3_compact.py`) frees dead and duplicate code in overlay 3. The freed runs
(`effects/pool_blocks.py`) are the pool. `effects/cave3.py` assigns each slot a constant:

```python
CAVE3_PIPER_RES = 0x....  # (0xNN bytes) mystic_piper
```

- One constant per slot, with its size in the trailing comment; a stub split across runs gets one constant per
  fragment (`cave3.asm_split`).
- **Step 0 must run before any card that uses the pool.** Cards assert the slot is zero:
  `cards/mystic_piper.py` refuses to write if it is not.
- `cave3.put(ov, addr, blob, src)` writes and checks the slot; `cave3._checked(addr, size, blob, src)` checks
  only.
- ThumbAssembler stubs need a 4-aligned base.
- ⚠ `pool_blocks.py` is **frozen** from its first claim. Regenerating it (`tools/ov3_compaction/gen_pool.py`)
  renumbers and moves runs and invalidates every `CAVE3_*` constant. Do not regenerate it casually.
- Addresses are stock-EU ov3. ov3 code never moves in the chain; only table rows shift.

To claim a slot: pick a free run big enough (`tools/ov3_compaction/census.py` reports supply and demand), add
a `CAVE3_<CARD>_<ROLE>` constant, and use it.

## ov5 cave

Overlay 5 is co-resident with overlay 3 in a normal duel and ends exactly at the duel heap base. The code
appends a region there and raises one ARM9 literal (the duel arena-lo) to make room.

```python
from otn_enhanced.effects import ov5_cave
ov5_cave.install_cave(rom, ov5_cave.CAVE_MYSTIC, blob, reserve=0x60)   # asserts the slot is free and blob fits
# then point a table field at  ov5_cave.CAVE_MYSTIC | 1
```

`install_cave` grows overlay 5 once (idempotent), edits ARM9 through `ndspy.code.MainCodeFile`, and writes the
blob. Add a `CAVE_<NAME>` constant for every new slot and bump `CAVE_FREE`. **Never hardcode a cave address**:
read `CAVE_FREE` from `ov5_cave.py` and check it against the ledger.

ARM9 must always be edited through `MainCodeFile`. A raw decompress and recompress flattens its sections and
white-screens.

## The ledger

`otn_enhanced/docs/engine/allocations.yaml` is the live record of every claimed ov5 slot, ov3 pool slot and
phantom cid. It is generated from the code.

```
uv run python -m otn_enhanced.knowledge.check_allocations          # check
uv run python -m otn_enhanced.knowledge.check_allocations --emit   # rewrite after a claim
```

Every build runs the check first and **aborts on any overlap or double-claimed phantom cid**, before writing a
ROM.

When you claim something:

1. Add the `CAVE_*` or `CAVE3_*` constant (and bump `CAVE_FREE` for ov5).
2. Add any phantom cid you drop to `PHANTOM_CLAIMS` in `knowledge/check_allocations.py`.
3. Run `--emit`.

Before saying a region is free or already reserved, re-read the ledger and quote the exact line. Do not rely on
memory or an older note.

## Worked example: Mystic Piper's three stubs

`cards/mystic_piper.py` has both homes behind one flag:

```python
SLOTS5 = (STUB_ADDR, COND_ADDR, COST_ADDR)                       # ov5_cave.CAVE_MYSTIC, CAVE_PIPER_COND, CAVE_PIPER_COST
SLOTS3 = (cave3.CAVE3_PIPER_RES, cave3.CAVE3_PIPER_COND, cave3.CAVE3_PIPER_COST)
```

`main(ov3=True)` is the default. `verify()` works out which home was used by looking at where the table row
points, then checks the stub bytes at that address.

## Check it

- `check_allocations` exits 0.
- `verify()` reads the stub back from the built ROM (`cave_holds`) and compares it with a fresh build.
- Test in a **normal duel and a puzzle** if the stub is in the ov3 pool. Test in a normal duel if it is in ov5.

## Pitfalls

- A stub placed in ov5 and tested in an editor-launched puzzle "does nothing" or freezes. That is residency, not
  your logic. Confirm the route the puzzle was started from.
- Developing in ov3 first isolates logic bugs from residency bugs; port to a final slot once it works.
- Do not park code in "obviously free" ARM9 zero runs: every one examined so far was a live buffer or a sparse
  jump table.
- Some ov3 tail zero-runs are runtime-clobbered. Only use runs the pool allocator hands out.
- Savestates can hold **old** ov5 code. Byte-check a savestate's stubs against the current build before
  diagnosing from it.
