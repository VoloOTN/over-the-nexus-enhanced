# Data patches: packs, decks, banlists, unlocks, rewards

## Goal

Change game data that is not a card effect: booster-pack contents, CPU decks, banlists, pack and duelist unlock
rules, deck names, rewards, timers and emblems.

## Before you start

These modules share one shape: a table named `CHANGES` (or `LISTS`, `BANNED`...) near the top of the file, plus
`main(src=, out=)` and `verify()`. You edit the table, not the logic. Most are same-size, in-place edits.

Run any of them alone with `python -m otn_enhanced.<package>.<module>`, or through the build (they are the last
steps in `steps.py`).

| Job | Module | Edit |
|---|---|---|
| Booster-pack membership and rarity | `data/bulk_card_pack.py` | `CHANGES`, keyed by card name |
| Bulk card property conversions | `data/bulk_card_props.py` | the conversion lists (also Field Spells) |
| CPU and story decks | `data/bulk_ydcs.py` (step) over `data/ydc_decks.py` (the deck data) | `CHANGES` in `ydc_decks.py` |
| Duel rewards ("memory" changes) | `data/bulk_memory.py` | its tables; reward codec in `rom/duel_reward_codec.py` |
| Default banlist | `data/default_banlist.py` | `BANNED`, `LIMITED`, `SEMI_LIMITED` card lists |
| Four extra built-in lists | `data/extra_banlists.py` | `LISTS` (fill in card names) |
| "No Banlist" mode | `system/no_banlist_mode.py` | repurposes the "Treat Ltd as Forb" entry |
| Booster-pack unlock rules | `system/pack_unlock_conditions.py` | `CHANGES`, keyed by pack id |
| CPU duelist unlock rules | `system/duelist_unlock_conditions.py` | `CHANGES`, keyed by duelist id |
| Deck display names | `system/deck_names.py` | `CHANGES = {duelist_id: "New Name"}` |
| Wi-Fi emblems offline | `system/wifi_emblems.py` | piggybacks Wi-Fi emblems on offline ones |
| Wi-Fi turn and match timers | `system/wifi_timers.py` | `--turn`, `--match` values |
| Free overlay-3 space | `system/ov3_compact.py` | step 0; see [caves-and-allocation](../caves-and-allocation/HOWTO.md) |

## Steps

1. Open the module and read its docstring. Each one records where its data lives (which overlay, which table,
   which address) and what is unproven.
2. Edit the table. Card names must match the **rom-hack's** names, not stock (donor rows were renamed).
3. Build only that step against the clean ROM and verify it:

   ```
   uv run python -m otn_enhanced.build --only data.bulk_card_pack --out data/over_the_nexus/working/rom_test.nds
   uv run python -m otn_enhanced.verify data/over_the_nexus/working/rom_test.nds --only data.bulk_card_pack
   ```

4. Run the full build to check it composes with the rest, then test in melonDS.

## Worked example: a pack edit

`data/bulk_card_pack.py` applies `CHANGES` and then enforces an invariant: **no pack may lose the last card of a
rarity tier it had.** The pack generator (ov10, `0x02155934` / `0x02155A68`) pools a pack's cards by rarity and
draws from each pool, so an emptied tier breaks pack opening. Rarity codes: 0 Common, 2 Ultra, 3 Super, 4 Rare.

## Check it

- `verify` passes for the step.
- For packs: open the pack in-game, and open one of each rarity.
- For unlock rules and deck names: the duelist or pack list, on a fresh save and on an existing one.
- For banlists: the Duelist Menu entry shows the right name and limits.

## Pitfalls

- **Same-size or nothing.** Deck names must fit the original name's byte budget unless the module says how it
  grows. Unlock records are fixed 4-byte slots.
- **Order matters.** Card Pack Changes run twice: once for unobtainable cards only (Vanilla+), once in full at the
  end. Decks, rewards, deck names and duelist unlocks run last.
- **Deck data steps use the ROM object, not a path.** `data/bulk_ydcs.py` loads through
  `NintendoDSRom.fromFile(src)` and mutates in place, because the build's session only intercepts that exact
  path. Copying the original `extract_file`/`replace_file` helpers silently edits a disconnected copy.
- **Extra banlists rewrite ARM9 code in place** (`load_list`), because no free ARM9 space is proven. Do not
  grow them.
- The No Banlist mode relies on a flag bit read in exactly one place; do not reuse that bit.
- **Deck checks compare cids, not names.** Names read back from `deck.pac` come from the stock table, so a
  renamed donor reads as its stock name. `data/bulk_ydcs.verify` resolves `CHANGES` through the writer's own
  `_entry_to_konami_id` for that reason.
