# Wiring an effect into the engine's tables

## Goal

Make the engine find and run your stub for the donor's cid, by adding or editing rows in overlay 3's
cid-keyed tables, without growing any table.

## Before you start

- You have a stub ([effect-writing](../effect-writing/HOWTO.md)) and a donor ([donor-cards](../donor-cards/HOWTO.md)).
- Overlay 3 cannot grow: its RAM slot is exactly full. Every insert must be **count-neutral**: drop a
  *phantom* cid (an engine id with no card behind it) to make room.
- Tables are binary-searched with the row count baked into the code as an immediate. A table that is unsorted
  or the wrong length makes the search read garbage.

## The tables

Overlay 3 RAM base `0x02141700`; file offset = RAM address − `0x02141700`.

| Table | Base | Count | Stride | What a row does |
|---|---|---|---|---|
| cls0 | `0x0227E64C` | `0x51A` | 24 | continuous / on-field |
| cls1 | `0x022860D4` | `0x535` | 24 | continuous / on-field |
| cls2 | `0x02275C04` | `0x2B9` | 24 | leave-field and sent-to-GY triggers |
| cls3 | `0x02279D74` | `0x308` | 24 | ignition and activated-from-field |
| criteria / populate | `0x022713C4` | live (use `crit_count`) | 12 | search and Special Summon candidates |
| effect registry | about `0x0228E1E0` | sectioned | 8 | timing subscription; **position is timing** |
| delayed-trigger list | `0x0226D384` | 52 | 2 | sorted u16 cids for End-Phase triggers |

A cls row, sorted ascending by cid:

```
+00 cid   +04 resolver   +08 aux   +0C condition   +10 timing tag / cost   +14 tail
```

`find_event_handler` (`0x0224A118`) picks the table by event class and binary-searches it. If two rows share a
cid it returns the **leftmost**, so a second row for a cid can be unreachable.

## Steps

### 1. Describe the table once

```python
from otn_enhanced.effects.common import Ov, Table, insert_sorted, keys, rows

CLS3 = Table(base=0x02279D74, count=0x308, stride=24, fmt="<IIIIII", wide=True,
             label="cls3 ignition record")
CLS3_DROP = 0x1436        # a phantom cid currently in the table
```

`wide=True` means the key is a u32 (cls3 here) rather than a u16.

### 2. Open overlay 3 as a RAM-addressed view

```python
from otn_enhanced.rom.overlay_io import load_overlay3, save_overlay3
rom, ovb = load_overlay3(src)
view = Ov(bytearray(ovb))
```

`Ov` offers `u8/u16/u32`, `blob`, `unpack`, `write`, `pack`, `rows`, `keys`, addressed in RAM terms.
`write` refuses to change the buffer length.

### 3. Insert the row

```python
record = (DONOR_CID, stub_addr | 1, 0, cond_addr | 1, cost_addr | 1, 0)
insert_sorted(view, CLS3, record, drop=CLS3_DROP)
```

`insert_sorted` removes the phantom, shifts the rows between, writes the record at its sorted position and
asserts the table is still sorted. Run twice it does nothing the second time.

`swap_key(view, t, old_cid, new_cid)` re-points an existing row to another cid.

### 4. Save

```python
save_overlay3(rom, bytes(view.buf), out)
```

### 5. Register what you used

Add the phantom to `PHANTOM_CLAIMS` in `knowledge/check_allocations.py` and any new cave constant to
`effects/ov5_cave.py` / `effects/cave3.py`, then `check_allocations --emit`. The build aborts on a double claim.

## Worked example: Mystic Piper (`cards/mystic_piper.py`)

A records-free Normal Monster becomes an ignition effect with **one** cls3 row:

```
{cid 0x13B8, +04 resolver|1, +08 0, +0C condition|1, +10 cost|1, +14 0}
```

- `+04` is the action, `+0C` the offer test, `+10` the cost.
- `+0C` and `+10` borrow generic routines (`0x021F06E8`, `0x021E50CC`) that do not look at the cid. Disassemble a
  borrowed slot before trusting it: cloning another card's condition fails because those binary-search a
  per-cid registry and return 0 for an unlisted cid.
- `+08 = +14 = 0` means no target framework can abort the activation.
- The card must also become an Effect Monster in `card_prop` ([card-text-and-stats](../card-text-and-stats/HOWTO.md)).

## Choosing the record shape

| Wanted behaviour | Start from |
|---|---|
| Manually activated ("you can Tribute this card to...") | one cls3 row |
| Trigger when it leaves the field or goes to the GY | cls2 row, plus a leave-mask row; cls2 is never reached by Extra Deck donors |
| Search or Special Summon a chosen card | a criteria row (the `b` field is a fixed cid or a criteria code) |
| End-Phase trigger | registry slot in the End-Phase section **and** the delayed-trigger list |
| "When ... you can" vs "If ... you can" | the timing tag in `+10`: `0x021E51E5` can miss timing, `0x021E50DD` never misses, `0` is mandatory |

Rows past index 1 of a criteria entry need a switch arm; see `docs/engine/` (`criteria` facts) before adding one.

## Check it

`verify()` in a card module re-opens the built ROM and asserts the edit landed. Use the helpers:

```python
c = Checker("My Card")
table_intact(c, view, CLS3, expect=DONOR_CID, phantom=CLS3_DROP)   # sorted, right length, phantom spent, cid present
c.eq([r for r in rows(view, CLS3) if r[0] == DONOR_CID], [record], "exactly one row, exact")
return c.result()                                                 # always a bool
```

Then build a single-card ROM and test in a normal duel. For a puzzle, host the stubs in the ov3 pool.

## Pitfalls

- **Position equals timing in the registry.** Overwriting a resolver in place keeps the old timing. Steal a slot
  in the right section.
- **The engine is cid-switch coded.** Pointing a row at a foreign handler often does nothing, because the
  handler falls through to a default for cids it does not know. Choose a donor whose native shape matches.
- **Do not claim a phantom someone else holds.** Re-read the ledger line first; do not trust memory.
- **Counts.** The cls table counts are fixed immediates inside `find_event_handler`, and inserts are
  count-neutral, so they do not move. The criteria table is the exception: earlier steps insert rows, so read
  its live length with `crit_count(ov)` instead of copying a number from a note.
