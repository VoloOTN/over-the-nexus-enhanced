# The 5 verify() sweep failures — diagnosed 2026-09-11

## Confirmed

**All five are STALE VERIFICATIONS, not broken cards. The ROM is correct.**

`patch_grapha`, `patch_ceruli`, `patch_ninja_grandmaster_hanzo`, `patch_white_dragon_ninja` and
`patch_accel_synchron` have failed the sweep since before the fast build existed. Measured on
`rom_all_patches.nds` (`7196d23e…dc414c`), and identically on the oracle's own artifact, so they
never were a regression from anything recent.

**Every failing check is about card NAME or DESCRIPTION. Not one is about an effect.**

### The evidence

Read the English name/desc straight out of `bin2.pac` for each donor cid and compared three ways:

| module | cid | ROM name | module `NEW_NAME` | ROM == `card_text` |
|---|---|---|---|---|
| grapha | 0x1961 | `Grapha, Dragon Lord of Dark World` | `Grapha, Dark World Lord` | **name + desc: True** |
| ceruli | 0x1B3E | `Ceruli, Guru of Dark World` | `Ceruli, Guru of Dark World` | **name + desc: True** |
| ninja_grandmaster_hanzo | 0x13E7 | `Ninja Grandmaster Hanzo` | `Ninja Grandmaster Hanzo` | **name + desc: True** |
| white_dragon_ninja | 0x12B2 | `White Dragon Ninja` | `White Drgn Ninja` | **name + desc: True** |
| accel_synchron | 0x11A3 | `Accel Synchron` | `Accel Synchron` | **name + desc: True** |

All five cids ARE in `card_text.CARD_TEXT`, and in all five the ROM's name AND description match
`card_text.resolve(cid, 'e')` byte for byte.

### The cause

`apply_stats_and_text` has two paths. For a cid carried by `card_text.CARD_TEXT` it takes the
**index-order re-emit**, which writes the card's FULL printed text and is not limited by the
donor's original slot length. Only for a cid it does NOT carry does it fall back to the legacy
**strictly in-place** write, which is why those modules define abbreviated constants.

These five modules were written before, or across, that change. Their `verify()` still asserts
the **legacy abbreviations** — the strings the in-place path would have produced — while the ROM
correctly carries the full printed text the re-emit path wrote. So the assertions test a
mechanism the cards no longer use.

`patch_accel_synchron` states it most clearly:

```
FAIL C [e] desc == the longest ladder entry its 44 B slot holds (42 B)
           b'1 Tuner + 1+ non-Tuners. Lv +/-. Quick SS.'
           (got b'1 Tuner + 1+ non-Tuner monsters Once...')
FAIL C [e] desc is 463 B, within the 44 B in-place slot
```

The 463 B string IS the real printed text, and the 44 B "in-place slot" ceiling stopped applying
the moment the cid joined `CARD_TEXT`. The check is asserting the old constraint.

## Why this is safe to fix

`verify()` is **never called by `main()`**, by `apply_all_patches`, or by the fast build. Fixing
these assertions changes **no ROM bytes**, so it needs no re-baseline — only a `--compare` to
prove exactly that.

## Ruled out

* **Not a regression from the fast build.** Identical failures on the oracle's own artifact.
* **Not a regression from Phase 3.** None of the five is a migrated module.
* **Not a broken effect.** Every failing assertion is a text-blob string comparison.
* **Not a card_text bug.** The ROM matches `card_text.resolve()` exactly for all five.

## The fix — DONE 2026-09-11

`card_text.check_rom_text(rom_path, cid, langs)` -> `(ok, summary)` asserts the ROM's name and
desc equal `card_text.resolve(cid, lang)` for every language. That is the same source the writer
uses, so it cannot drift the way a hand-copied constant did. A cid absent from `CARD_TEXT`
returns `(True, "not carried")`, so it is safe to call unconditionally.

Each of the five modules' bespoke text block was replaced with one call. Two of them needed the
`card_text` import added (`patch_white_dragon_ninja`, `patch_ninja_grandmaster_hanzo`,
`patch_accel_synchron`).

```
BEFORE: 41 passed, 5 failed, 0 without verify()
AFTER:  46 passed, 0 failed, 0 without verify()
```

Two checks were preserved rather than dropped, because they tested something real:

* **hanzo** also asserted its description covers BOTH clauses, not just clause 1 — now run
  against `card_text.resolve(cid, "e")` instead of the dead constant.
* **hanzo / white_dragon_ninja** looped per language specifically to catch a language being
  silently skipped. `check_rom_text` checks all eight by construction, so that guarantee is
  kept, not lost.

### Dead machinery this exposed

`patch_accel_synchron` carries a whole `DESC_LADDER` / `DESC_SLOTS` / `_desc_for(L)` apparatus —
a per-language ladder of progressively shorter descriptions, picking the longest that fits each
donor slot. **It is dead for this card.** It existed only for the in-place writer's slot limit,
which stopped applying the moment the cid joined `CARD_TEXT`. Its verify half is gone; the
constants are left in place (they are harmless and `main` still references them), but nothing
should be built on them.

## Proof this changed no ROM bytes

`verify()` is not called by `main()`, `apply_all_patches`, or the fast build, so the ROM must be
untouched — confirmed by a full `--compare` against the frozen baseline after the edits.

⚠️ NONE OF THIS IS IN-GAME CONFIRMATION. It proves the ROM says what `card_text` says it should.
The five cards' EFFECTS were never in question here — not one failing assertion was about an
effect — and nothing about them has been re-tested.
