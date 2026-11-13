# Shared hooks and step order

## Goal

Add behaviour at an engine site that other cards already use, without breaking them, and put a new step in the
right place in `steps.py`.

## Before you start

Many useful interception points are a **single 4-byte `BL`**. One stub can only serve one owner, so the sites are
owned by **shared modules** in `effects/`, each holding one stub and a **register of cids** (`ARMS`). Re-pointing
a site to your own stub silently breaks every card already on it.

| Module | Site it owns (what it intercepts) |
|---|---|
| `criteria_row_hook.py` | criteria-row offset inside the row resolver (`0x02243BEC`) |
| `timing_class_hook.py` | the "When" vs "If" timing classifier (`0x0224AF96`) |
| `summon_rider_hook.py` | default leaf of the summon-event per-cid switch (`0x02268666`): attaches "banish when it leaves" |
| `summon_trigger_hook.py` | proper-Summon trigger list |
| `c79_trigger_hook.py` | "If Normal or Special Summoned" trigger list (code 7 or 9) |
| `c9_trigger_hook.py` | "If Special Summoned" trigger list (code 9) |
| `ss_commit_hook.py` | stamp when a card is Special Summoned from the hand |
| `deck_send_follow_hook.py` | deck-send phase `0x7C` follow-up |
| `gy_vrow_hook.py` | virtual GY-action rows (one 16-row table) |
| `handss_banish_cost.py` | Special Summon by banishing from the GY: shared cost half |
| `atktgt_gate.py` | the "selected as an attack target" gate |
| `tg_table.py`, `xsaber_table.py` | archetype tables and the T.G. trampolines |

Ask first: **does the site already have an owner?** Grep its address across `cards/` and `effects/`.

## Steps: add an arm

1. Open the owner module. Its `ARMS` tuple has one entry per cid, for example in `timing_class_hook.py`:

   ```python
   (LP_CID, "lp", ARM_LP, "Lightpulsar: zone GY, event > 6 -> tag 0 (class 0, a real WHEN trigger)"),
   ```

2. Add your entry. Decide where it goes: a cid-keyed arm answers for **every clause of that card**, not only the
   one you wrote it for. Scope it (zone, event class) so it does not capture a sibling clause.
3. The module's `install(rom)` / `apply(ov)` regenerates the stub from the whole register. Your card's `main()`
   calls it, and `verify()` calls the module's `verify`.
4. **Prove the arms already there are unchanged by executing both stubs**, not by arguing: run the old and
   new stub on the same inputs and compare.
5. For a default-leaf hook, prove your cid actually reaches the site. A cid with its own dedicated arm never
   arrives, and the hook is silently dead for it. Check the path with a cid whose leaf you already know.

If no shared module fits, see [trampolines](../trampolines/HOWTO.md) for creating one, and
[caves-and-allocation](../caves-and-allocation/HOWTO.md) for where its stub lives.

## Steps: place a new step in `steps.py`

`steps.STEPS` is data. Order is load-bearing and is not alphabetical.

1. Vanilla+ steps come first (ov3 compaction, WiFi timers, pack unlocks, banlist menu, then the Vanilla+ cards,
   their art and genre). `VANILLA_PLUS_END` is the row named "Card Pack Changes (unobtainable cards only)".
2. Then the remaining cards, art, banlist, bulk property conversions.
3. Then full card-pack changes, decks, rewards, deck names and duelist unlocks.
4. A card that composes with another goes **after** it. The existing constraints are written as `MUST stay
   after ...` comments above the rows. Examples: Boggart Knight before T.G. Rush Rhino (Boggart clones criteria
   phantom `0x2346`, Rush Rhino later spends it); Scrap Raptor after Ninishi (it chains into Ninishi's stubs);
   Sakitama after Scrap Raptor and Assault Synchron (it fronts their stubs and asserts the before-images);
   Dragon Rulers after Revolution Synchron; Sekka's Light, Fire Formation, Sacred Sword after Dragon Rulers.
5. Add a `Step(name, "cards.my_card")` row. Call shapes: `text=FLAG` follows `--no-text`; `ALWAYS` forces
   `write_text=True`; `None` omits the argument. A positional or non-`main` entry uses the extra fields.
6. Write the constraint as a comment on the row. Today these live only in comments, which is the main fragility
   of the build.

## Check it

- A full build with the new row passes the allocation guard and `verify` passes for the new card **and** every
  card in the register you touched.
- Moving the row earlier breaks the build loudly for assert-guarded cards. If it does not break, the guard is
  missing: add a before-image assert.

## Pitfalls

- A shared hook with an arm per card costs a compare per cid at every dispatch; keep arms narrow.
- "Virtual" rows (the Dragon Rulers family) have **no table rows at all**: hooks on the miss tails answer for a
  cid list. They compose through the same registers; do not also add real rows for those cids.
- Shared-hook modules must not import card modules that import them (`card_genre` documents this for orient
  dragon).
