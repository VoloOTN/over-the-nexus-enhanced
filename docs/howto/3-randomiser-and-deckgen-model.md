# HOWTO 3: Run the randomiser and tune / train the deck model

Two parts: the **randomiser** (`otn_enhanced/randomiser` UI + `otn_enhanced/randomise` engine) and **deckgen**
(`otn_enhanced/deckgen`), the model the randomiser uses to rebuild all 305 CPU decks.
Full references: [randomiser README](../../otn_enhanced/randomiser/README.md),
[deckgen README](../../otn_enhanced/deckgen/README.md).

## Setup

Only [HOWTO 1](1-setup-and-build.md) steps 1, 2 and 5 (uv, `uv sync`, an EU `BYYP` ROM). No toolchain or
CardWorkshop needed.

> `INSTALL.md` in the randomiser folder still describes the old single-file / `.exe` layout; ignore its
> paths and use the commands below.

## Run the randomiser

GUI:
```bash
uv run python -m otn_enhanced.randomiser
```

CLI (example: everything, balanced stats, all packs, new decks):
```bash
uv run python -m otn_enhanced.randomiser --rom data/over_the_nexus/working/rom.nds --out data/over_the_nexus/working/rom_randomised.nds --seed myseed --attribute --race --level --atk --def --balanced --unlock-all-packs --decks
```

| option | does |
|---|---|
| `--seed TEXT` | same seed + same flags = same ROM. Omit for a random one (printed in the report) |
| `--attribute --race --level --atk --def` | which monster properties to shuffle |
| `--synchro-level` | also Synchro levels (off by default; breaks material maths) |
| `--balanced [--caps ...]` | cap ATK/DEF by level band |
| `--unlock-all-packs` / `--only-pack-60` | pack unlocks (default: stock) |
| `--decks` | regenerate every CPU deck with deckgen (~4 min on 8 cores) |
| `--deck-limit N` | only the first N decks, for a quick look |
| `--dry-run` | report changes, write nothing |
| `--selftest --rom <rom>` | round-trip every structure + validate the seed pile; writes nothing |

Output: the new ROM plus `<out>_report.txt` (seed, settings, every change, every deck list).
The input ROM is never modified.

**Order with the card patches:** randomise the **clean** ROM first, then apply card patches on top —
the patches assert against stock stats.

## Change what decks get built: the seed pile

`otn_enhanced/randomiser/deck_seeds.json` → `seed_pile` is a flat list. Each of the 305 decks draws one entry
at random (deterministic per seed). Add entries freely:

```json
{ "seed": ["Shining Angel"], "allowed_attributes": ["LIGHT"], "size": 40, "banlist": "none" }
```

Keys: `seed` (required), `size`, `banlist`, `allowed_types`, `allowed_attributes`, `beam`, `candidates`, `lam`.
Run `--selftest` after editing: it catches typos in card names (with suggestions), bad keys and trailing commas.

Try a single recipe directly:
```bash
uv run python -m otn_enhanced.deckgen.cli gen --seed "Rekindling" -v
```

## Tune the model by hand

Every coefficient lives in `otn_enhanced/deckgen/data/params.toml`. Other knobs:

| file | for |
|---|---|
| `data/bundles.toml` | "A is dead without B" pairs the card text doesn't state |
| `data/aliases.toml` | name fixes the auto-matcher misses (Spells/Traps) |
| `data/golden.toml` | ground-truth economy assertions; must stay green |

Inspect what the model thinks:
```bash
uv run python -m otn_enhanced.deckgen.cli explain "Mystical Space Typhoon"
```
Also `partners "<card>"`, `top --monsters`, `seeds`.

After **any** edit, both must pass:
```bash
uv run python -m otn_enhanced.deckgen.cli golden
```
```bash
uv run python -m otn_enhanced.deckgen.cli validate
```

## Train the model

Two fits, each owning a disjoint set of `params.toml` keys:

| command | fits | against |
|---|---|---|
| `train` | per-card quality (tag weights, gains) | tournament play rate (formatlibrary decklists) |
| `train-deck` | how card scores add up into a deck (impact balance, `deck.*`) | AUC: tournament deck vs ROM AI deck |

Dry run first (prints fitted vs current, writes nothing):
```bash
uv run python -m otn_enhanced.deckgen.cli train
```
Then write it:
```bash
uv run python -m otn_enhanced.deckgen.cli train --apply
```
Same for `train-deck`. Useful flags: `--fetch` (refresh the decklist cache first), `--seeds 1 2 3 4 5`
+ `--min-seeds 3` (how many runs must agree before a value is written), `--all-formats` (all ~100 formats
instead of the 2011 era), `train --no-evidence` (judge the model's own reasoning, not the play-rate lookup).

Fits use one half of the corpus and report the held-out half: quote the held-out number. Re-run
`golden` and `validate` after `--apply`.
