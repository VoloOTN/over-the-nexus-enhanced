# Choosing a donor card

## Goal

Pick the existing card that will become your new card, and gather the evidence that it is safe to overwrite
before any patch code is written.

## Before you start

The technique: **keep the donor's cid** and overwrite the effect tables for that cid with the new card's
effect. Changing a cid breaks the deck editor and menu lookups (the card vanishes or freezes on select).

## Steps

### 1. Pick a candidate

Donors are **vanilla Normal Monsters that are not competitively playable**. Prefer weak filler (low ATK).
Powerful vanilla cards that people play are off the table. A Normal Monster with no effect records is
collision-free by default.

Scan for candidates:

```
uv run python -m otn_enhanced.tools.donor_scan 0x13B8                      # audit one cid
uv run python -m otn_enhanced.tools.donor_scan --free --level 1 --min-desc 200   # list candidates
uv run python -m otn_enhanced.tools.donor_scan --help                      # --race, --attribute, --min-name
```

`donor_scan` looks for the cid as an aligned u16/u32 anywhere in overlay 3 and ARM9. A cid with no occurrence
is entangled in nothing. It cannot see switches that encode cids as `base ± imm`, so a clean report means "no
data structure names this cid".

### 2. Gather four pieces of evidence

Mark each `PROVEN` (with address or byte evidence) or `ASSUMED`. Do not write code until every line is proven
or you have decided to accept the assumption.

| # | Evidence | How |
|---|---|---|
| a | The donor is a Normal Monster with no existing effect records | `donor_scan`; check cls0 to cls3, criteria and registry |
| b | Name and description blob lengths are at least the new strings | read `card_name_*` / `card_desc_*` slots; a donor was abandoned mid-patch for short blobs |
| c | **No per-cid gate** on the donor cid in ov3 or ov5 | attack-target gate, summon-procedure row, criteria-registry row, Bushido counter capacity... Unnoticed gates broke two patches in-game |
| d | Level, type and attribute do not fight the effect | Extra Deck donors are never reached by cls2 dispatch; use a leave-hook trampoline instead |

### 3. Name the zone the effect searches

State the exact zone (Deck, hand, GY, banished) and show the disassembly proving the primitive reads that zone.
A patch once searched the Deck instead of the banished zone and passed every static check.

### 4. Name the once-per-turn stamp

Say where the once-per-turn flag is written. It belongs in the **cost**, not the resolver, so a cancelled or
negated activation cannot escape the restriction.

### 5. Show the evidence and wait for approval

Present the table to whoever owns the card before writing the module.

## Worked example: Mystic Piper

Donor Flame Dancer `0x13B8`, a records-free vanilla. It replaced an earlier choice (Ancient Gear Cannon
`0x19BB`), which was restored to a real card. `cards/mystic_piper.py` asserts the old donor is untouched
(`_assert_agc_untouched`) so a later edit cannot reach for it again.

## Check it

- `verify()` asserts the donor's cid appears in exactly the rows you wrote.
- `check_allocations` passes: you did not claim a phantom someone else holds.

## Pitfalls

- Two failure modes cause most patches that pass `verify()` and then fail in-game: a missed per-cid gate, and a
  wrong zone.
- A donor that natively has the timing you want (an End-Phase GY trigger, say) saves a slot-steal. Pick for
  the native shape when a table row is unavoidable.
- A donor whose Level or Type contradicts the printed card produces blank ATK/DEF or no Normal Summon option.
- Re-using a retired donor: check the ledger line in `otn_enhanced/docs/engine/allocations.yaml` before relying on a phantom
  being free.
