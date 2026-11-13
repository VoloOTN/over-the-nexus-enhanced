# Over the Nexus randomiser

A randomiser for **Yu-Gi-Oh! WC2011: Over the Nexus** (NDS, EU `BYYP`).

This folder is UI and config only (`gui.py`, `cli.py`, `paths.py`, `deck_seeds.json`).
The engine lives in `otn_enhanced/randomise/` (stages, card_prop layout, driver,
selftest), with `rom/pac_inplace.py`, `rom/ydc_codec.decode_ydc_ids` and
`otn_enhanced/deckgen/` underneath.

```
uv run python -m otn_enhanced.randomiser            # GUI
uv run python -m otn_enhanced.randomiser --help     # CLI
```

Installing, the deck-stage data, and rebuilding the `.exe`: see [INSTALL.md](INSTALL.md).

## What it randomises

| Option | Effect |
|---|---|
| Attribute | DARK / LIGHT / WIND / EARTH / FIRE / WATER. DIVINE cards keep DIVINE. |
| Type / Race | Dragon … Psychic. Divine-Beast cards keep Divine-Beast. |
| Level | 1–12 for ordinary monsters. |
| …including Synchros | Synchro monsters get 2–12 (a Synchro needs a Tuner plus a non-Tuner, so 2 is the floor). Off by default, because a Synchro's level is what its materials have to sum to. |
| ATK / DEF | 0–5000 in steps of 50. |
| Balanced mode | Caps ATK and DEF by level band. Defaults: Lv1–4 → 2000, Lv5–6 → 3000, Lv7–8 → 3500, Lv9–10 → 4000, Lv11–12 → 5000. Editable. |

Spells, Traps, Tokens and the four level-0 rows are never touched, and the 47 cards
with `?` ATK/DEF keep the `?`.

## Other stages

- **Booster packs** — three-way choice: leave as shipped, unlock all 60 from the
  start, or unlock only pack 60 and lock 1–59.
- **Duel puzzles** — sets the opponent's life points in `2011_tume01` … `tume10`
  so none of the ten can soft-lock. Defaults to 0; the value is editable because
  whether the engine's win check accepts a zero at duel *start* has not been
  confirmed in-game, and 1 is the fallback.
- **Decks** — regenerates every `.ydc` from `deck_seeds.json`. Needs the repo
  checkout, see below.
- **CPU duelists** — placeholder. Not solved; see
  `notes/cpu-duelist-unlock-findings.md`.

## Seeds

The master seed can be any text. **Omit it and a fresh random one is generated and
reported**, both on screen and in the report header, so a result you like stays
reproducible — pass it back with `--seed` to rebuild the same ROM. (The GUI
pre-fills the box with a new seed each time it opens; overwrite it to reuse one.)

Each property gets its own RNG stream derived from the seed, and every eligible card
draws from every stream whether or not that property is enabled — so **toggling the
ATK checkbox will not reshuffle races**, and a given seed always means the same thing.

## What you need to supply

Only the **ROM**. Properties, packs and puzzles need nothing else — no seed, no seed
list — and produce a finished ROM.

The one exception is deck regeneration, which needs `deck_seeds.json` to hold at
least one usable recipe. Without it that single stage skips and says so; every other
stage still runs and you still get a ROM.

## Deck regeneration

`deck_seeds.json` holds a flat **seed pile**. There is no filename → seed mapping:
each of the 305 decks in `deck.pac` draws an entry from the pile at random,
deterministically from the master seed, so the pile can be extended without
renaming or reordering anything. See the comment block in that file for the
per-entry keys.

Entries with no usable card name (`"seed": [""]`) are skipped rather than built
from nothing. If the file is not valid JSON — a trailing comma after the last entry
is the usual culprit — the deck stage reports the line and column and skips; the
property, pack and puzzle stages still run and still produce a ROM.

### Turbo (Riding) duel decks

84 of the 305 decks are Turbo Duel decks, and those may only run **Speed Spells** —
never ordinary Spells. Monsters and Traps are unrestricted, and Speed World is not
a deck card. Measured across all 305 stock decks: the 84 turbo decks contain zero
ordinary Spells.

Two things this tool gets right that are easy to get wrong:

- **Turbo decks are detected by contents, not by filename.** Only 29 are named
  `*_rd.ydc`; the other 55 are in the `rtlr*`, `wrd*` and `rpg*` families. A
  `_rd` suffix test misses two thirds of them.
- **deckgen cannot pick Speed Spells at all.** Its `namematch` marks every
  `Speed Spell - *` card `excluded` ("turbo duel only") and `Card.playable` is
  `False` for them, so they are absent from its pool and unscored. So after
  deckgen returns a deck for a turbo slot, this tool rewrites the spells: each
  ordinary Spell becomes its `Speed Spell - <name>` counterpart where one exists
  (111 of the 148 Speed Spells have one), and anything with no counterpart is
  replaced by an unused Speed Spell. Monsters, Traps, deck size and copy limits
  are left exactly as deckgen chose them.

In practice translation covers nearly everything, because deckgen picks staples and
staples are precisely the cards with Speed versions — a sample turbo build had
10 of 10 spells translated, coming out as Speed Spell versions of Monster Reborn,
Heavy Storm, Mystical Space Typhoon and Allure of Darkness.

The one caveat: those spells are chosen by name substitution, not by deckgen's
scoring, since it has no model for them. Getting deckgen to build turbo decks
natively would mean bringing the 148 Speed Spells into its pool with parsed text
and scores — a change to deckgen, not to this tool.

### Decks are generated at run time, never cached

Deck generation runs **after** the properties are randomised, against the stats this
run just wrote, and nothing is reused between runs. That is not a performance
oversight — it is the only correct order. deckgen's card pool is keyed by **cid** and
stores each card's Attribute, Type, Level, ATK and DEF, so a deck computed before the
properties moved is a deck built around cards that no longer exist. deckgen has its
own name for the hazard, `cardpool.is_randomised`.

So the stage does this:

1. writes the in-progress ROM to a temp file,
2. points deckgen at it (`resources.set_rom_path`), which changes the pool's cache
   key and forces a rebuild from the randomised `card_prop.bin`,
3. logs `deckgen sees this ROM as randomised: True` so you can see it took,
4. generates every deck in parallel across all cores.

You can watch it work. With a `Shining Angel` / LIGHT-only recipe on a randomised
ROM, the finished deck is 18 of 18 non-seed monsters LIGHT **by the randomised
properties** — where those same cids are only 6 of 21 LIGHT in stock. The three
remaining cards are the seed's own copies, because deckgen's rule is that `--seed`
always wins even when it is off-filter (Shining Angel had randomised to DARK).

### Cost

Two parts, both on the critical path:

Measured end to end on 8 cores — all 305 decks plus every other stage:

| | measured |
|---|---|
| rebuilding the pool from the randomised ROM | **26 s**, once per run |
| generating all 305 decks | **230 s** (0.8 s per deck, 0 failures) |
| whole run, ROM in to ROM out | **258 s — 4.3 minutes** |

Sequentially the deck phase alone would be ~20 minutes, so parallelism is worth
about **4.9×** here. Peak memory is roughly 900 MB (8 workers holding a pool each
plus the parent), worth knowing if you run it beside an emulator.

Profiling says the per-deck cost is 8,775 calls to `deckscore.score`, of which only
6.1% are redundant — the search genuinely evaluates 8,242 distinct deck states, so
there is no cache to add. `-j N` limits the worker count.

`--deck-limit N` builds only the first N (name-sorted) if you want a quick look.

### Where it runs

Everywhere, including the bundled `.exe`. The bundle carries deckgen's pool-build
*inputs* (36 MB raw, ~4 MB compressed) rather than its caches, which is the only thing
that works: a randomised ROM invalidates the whole cache chain, so shipping caches
would ship 5 MB that is discarded on first use.

The pool is cached under `%LOCALAPPDATA%\OTN-Randomiser\deckgen-cache` when frozen,
keyed on the content of the randomised ROM — so a repeat run with the same seed and
settings skips the rebuild entirely (30 s → 1 s).

The inputs are not in the repo; `python -m otn_enhanced.tools.fetch_deckgen_inputs --rom <rom>`
makes them. If they are absent, the deck stage refuses outright rather than falling
back on a pre-built pool: that pool describes the stock stats and would silently
mis-build all 305 decks. Every other stage still runs and still produces a ROM.

### Evidence mode

There is nothing to configure. `load_scored()` auto-detects via
`cardpool.is_randomised()`, so on a randomised ROM the per-cid tournament evidence
channel switches itself **off** and the `randomised` profile takes over — that is the
`deckgen sees this ROM as randomised: True` line. The per-**tag** play rates it falls
back to still come from the mined tournament corpus, which is worth keeping: deckgen
measures rank correlation at +0.6302 per-cid, **+0.4988 per-tag**, and +0.2973 with no
mining at all.

## Checking a build

```
uv run python -m otn_enhanced.randomiser --selftest --rom path/to/rom.nds
```

Round-trips every structure the tool writes and reports each check. It also
cross-checks the `card_prop` bitfield layout and the PAC reader against
`otn_enhanced.rom.game_constants` and `otn_enhanced.rom.pac`, which is what stops
the duplicated copies drifting from the validated originals.

It also **validates the seed pile**, which is the cheap way to catch a typo before
committing several minutes to a deck run:

- the file is valid JSON (reporting the line and column if not);
- every seed card resolves to a real card — against deckgen's pool when it is
  importable, which suggests near-matches (`no card named 'Rekindlng'. did you
  mean: ['Rekindling']`), otherwise against the ROM's own name table;
- `allowed_types` / `allowed_attributes` values are real Types and Attributes;
- `size` is 40–60 and `banlist` is one of the ROM's six lists (or `none`);
- no unknown keys — `allowed_type` for `allowed_types` would otherwise be
  ignored in silence and quietly produce an unconstrained deck.

Point it at a pile elsewhere with `--seed-pile PATH`. The same validation runs at
the start of the deck stage, before any deck is built, so a bad recipe stops the
stage immediately instead of after the decks preceding it have been rebuilt.

## The report file

Every run writes `<output ROM stem>_report.txt` next to the ROM it produced — so
`rom_randomised.nds` gets `rom_randomised_report.txt`. It opens with the settings
that produced the ROM, which is what lets you trace a build back to its seed
months later:

```
========================================================================
Over the Nexus randomiser report
========================================================================
  input ROM   : data/over_the_nexus/working/rom.nds
  output ROM  : data/over_the_nexus/working/rom_randomised.nds
  seed        : 20111
  randomised  : Attribute, Type/Race, Level 1-12, ATK, DEF
  balanced    : Lv1-4<=2000, Lv5-6<=3000, Lv7-8<=3500, Lv9-10<=4000, Lv11-12<=5000
  packs       : all 60 unlocked
  puzzles     : tume01-10 opponent LP -> 0
========================================================================
```

Then every change, one card per line:

```
157 - Blue-Eyes White Dragon [Normal Monster]: Attribute LIGHT -> WIND;
      Race Dragon -> Beast-Warrior; Level 8 -> 9; ATK 3000 -> 3950; DEF 2500 -> 0
```

and, for every regenerated deck, its **full contents** grouped by copy count:

```
  (wrd012_dashguy.ydc: seed ['Shining Angel'] rng 2060698020 -> 40+15 (124 bytes)
                       [turbo: 7 translated, 4 substituted]
      MAIN (40):
        3x Master Hyperion
        3x Shining Angel
        3x Speed Spell - Heavy Storm
        ...
      EXTRA (15):
        1x Odin, Father of the Aesir
        ...
```

The GUI shows a progress bar and a stage label throughout — per-card while
properties are randomised, per-deck while decks are generated, and a marching bar
during the pool rebuild, whose length the tool genuinely cannot know in advance.

The report always holds the full detail. `-v` additionally echoes it to the
console as it goes, which is off by default because 305 decklists is several
thousand lines. `--log FILE` puts the report somewhere else, `--no-report`
suppresses it, and a `--dry-run` writes nothing at all unless you pass `--log`.

## Notes and limits

- The input ROM is never modified, and the tool refuses to write over it.
- Card data decodes for any era-2 game, but the **pack addresses are EU `BYYP`
  only**. The tool checks overlay 1's load address and refuses anything else
  rather than writing to the wrong offsets.
- Every stage except decks is a byte-for-byte in-place patch: no PAC is repacked
  and no file address moves. The deck stage grows an entry inside its own
  512-byte block and updates just its size word, so no address moves there either.
- If chained with `apply_all_patches`, run the randomiser **first** — the shipped
  card patches assert against stock stats.

## Why not `ygo_tools/tools/randomiser.py`

The older in-repo randomiser addresses `card_prop.bin` **by byte index**, but each
entry is a 64-bit bitfield whose fields straddle byte boundaries: ATK is bits
14–22 and DEF is 23–31, so byte 2 is half of each and randomising "ATK" corrupts
both. Writing `level * 4` as the whole of byte 5 also zeroes **bit 41**, the
monster/spell-trap discriminator. This tool goes through the bitfield, starting
from the original u64 so bit 41, the spell/trap subtype and the reserved bits all
survive untouched.
