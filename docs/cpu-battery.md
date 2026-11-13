# CPU battery: tournaments and gauntlets

The CPU plays itself in melonDS, on a copy of `rom_all_patches.nds` with a small rig added. There are two ways
to use it:

- **Tournament** (`tournament.py`): the whole pool plays a Swiss tournament with a top-cut bracket. This gives
  standings, a champion and ratings for every deck.
- **Gauntlet** (`gauntlet.py`): one deck plays the rest of its pool. This gives its win %, its percentile
  against the other decks, its matchups and how often each of its cards was drawn, summoned and activated.

All the decks are the 305 in the ROM's `deck.pac`. They split into two pools that never meet:

- **turbo:** 84 decks, the ones holding a Speed Spell. They play Turbo Duels.
- **regular:** the other 221 decks.

Everything below runs from the repo root, in PowerShell.

> These are emulator results, not in-game confirmation of any card.

## Setup (once)

You need:

- `uv sync` done (see [docs/SETUP.md](SETUP.md)).
- CardWorkshop checked out next to this repo (`..\CardWorkshop`), or its path in `$env:CARDWORKSHOP`.
- `melonDS.exe` and `melonDS.toml` at the repo root. Each worker gets its own copy under
  `build\cpu_battery\w<k>\`, set up for speed: JIT on, no frame limit, sound off, software renderer.
- `data\over_the_nexus\working\rom_all_patches.nds` built.

Then build the battery ROM:

```
uv run python -m otn_enhanced.tools.cpu_battery.battery build
```

This writes `build\cpu_battery\battery.nds` and prints its sha256.

**Rebuild it whenever `rom_all_patches.nds` changes.** A tournament or gauntlet records the battery ROM's
sha256, and refuses to resume on a different one, so start a new run (a new `--id`) after a rebuild.

The first run boots one emulator to let the game format a save (`build\cpu_battery\formatted.sav`) and keeps
that save. Leave it there.

## Tournaments

```
uv run python -m otn_enhanced.tools.cpu_battery.tournament run --pool regular
uv run python -m otn_enhanced.tools.cpu_battery.tournament run --pool turbo
```

| option | default | meaning |
|---|---|---|
| `--pool regular\|turbo` | required for a new tournament | which pool plays |
| `--rounds N` | ceil(log2(decks)): 8 regular, 7 turbo | Swiss rounds |
| `--cut N` | 32 | single-elimination top cut (a power of two) |
| `--swiss-bo N` | 3 | Swiss matches are best of N |
| `--cut-bo N` | 5 | top-cut matches are best of N |
| `--id ID` | `<date>_<pool>` | folder name; an existing id resumes |
| `--jobs N` | 6 | emulators at once |
| `--timeout S` | 900 | seconds without a result before a game counts as a hang |
| `--decks PATTERNS` | all | comma-separated fnmatch patterns: a smaller pool, for tests |

Within a match the first player alternates. **Swiss rounds:**

- Pairing: equal scores meet, avoiding rematches.
- Scoring: 3 points for a match win, 1 for a draw.
- Tiebreaks: opponents' match-win %, then game-win %.
- Bye: an odd deck out gets a bye.

**Top cut:** seeded by the Swiss standings. A drawn bracket match goes to the higher seed.

`build\cpu_battery\run_tournaments.ps1` runs the regular tournament and then the turbo one. Edit its `--id`s
before starting a new pair.

To leave it running unattended, start it in its own PowerShell window. The Terminal panel's tool can
interrupt Python while it is still loading the card database. To start it in a window:

```
Start-Process powershell -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File','.\build\cpu_battery\run_tournaments.ps1'
```

### Stopping and resuming

To stop, close the window, or press Ctrl-C and then close any `melonDS.exe` left behind. To resume, run the
same command again: with `--id`, the id alone is enough.

A tournament's state is worked out from its `games.jsonl` every time, so a resume plays only what is
missing. At worst it replays the game each emulator was in the middle of.

Settings recorded in `meta.json` win over the command line on resume. A tournament keeps the format it
started with.

### What you get: `data\cpu_tournaments\<id>\`

| file | contents |
|---|---|
| `meta.json` | settings, deck list, sha256 of the source and battery ROMs |
| `games.jsonl` | one line per game: decks, seats, seed, result, LP, turns, per-card stats |
| `standings.md` | Swiss standings and tiebreaks (updated as it plays) |
| `bracket.md` | the top cut |
| `card_stats.csv` | per card: duels, drawn, summoned, activated; sorted by summoned, then activated |
| `card_stats_by_deck.csv` | the same, per deck |
| `summary.json` | champion and placements (once finished) |

A finished tournament also appends one line to `data\cpu_tournaments\history.jsonl`. That file is the
cross-tournament record, kept for compiling results later.

### Ratings

```
uv run python -m otn_enhanced.tools.cpu_battery.tournament ratings
```

This runs automatically at the end of every tournament. It writes
`data\cpu_tournaments\ratings\<build>_<pool>.md/.csv`, one table per battery ROM build and pool, using
tournament games only.

- **The fit:** a Bradley-Terry fit on an Elo scale, where 1500 is average and +200 means 76% expected. It also
  estimates the first-player advantage.
- **±95:** the 95% range. Decks whose ranges overlap are not really apart.

Offline check of the pairing, bracket and rating logic (no emulator):

```
uv run python -m otn_enhanced.tools.cpu_battery.tournament selftest
```

## Gauntlets

```
uv run python -m otn_enhanced.tools.cpu_battery.gauntlet run wcs049_gaiza
uv run python -m otn_enhanced.tools.cpu_battery.gauntlet run wcs049_gaiza --duels 100
```

The deck name is the `deck.pac` name without `deck/` or `.ydc`. A misspelt name lists the closest matches.

| option | default | meaning |
|---|---|---|
| `--duels N` | every opponent twice | duels to play |
| `--id ID` | `<date>_<deck>` | folder name; an existing id resumes, and a larger `--duels` extends it |
| `--jobs N` | 6 | emulators at once |
| `--timeout S` | 900 | seconds before a duel counts as a hang |

Duels go out in rounds:

- Each round meets every opponent once, in a shuffled order. A short `--duels` is therefore a fair sample of
  the field, not the first decks alphabetically.
- The seat alternates per opponent, so two rounds give each opponent one duel going first and one going
  second.

### What you get: `data\cpu_gauntlets\<id>\`

| file | contents |
|---|---|
| `report.md` | see below |
| `card_stats.csv` | the deck's own cards: drawn, summoned, activated over its duels |
| `summary.json` | the headline numbers |
| `games.jsonl`, `meta.json` | as for tournaments |

`report.md` holds:

- the W-L-D record and win % against the field (an average deck scores 50%);
- the percentile;
- the record going first and going second;
- average turns;
- a table of every opponent, worst matchups first.

**Percentile:** the share of the pool's other decks rated below this one.

- **How it is rated:** the gauntlet's games are fitted together with every tournament game played on the same
  battery ROM and pool. The tournaments supply the opponents' strength.
- **No tournament on the current build and pool:** the report gives only the win % until one is played.
- **Read the ± first:** a handful of duels gives a very wide range. Four duels came out at ±387.

## Practical notes

- **Throughput:** about 200 games/hour at 6 jobs (measured 2026-11-03). Duels are limited by the emulated CPU
  (game logic and AI), not by drawing. The GPU renderer (`--gl` on `battery run`) measured slower.
- **Jobs:** one emulator per CPU thread is the ceiling. Above that they only share the time. On a 4-core /
  8-thread machine, 7 jobs leaves room for the rest of the system.
- **Windows:** each emulator opens at a fixed spot in a grid (`tile_geometry` in `battery.py`), so the
  windows don't overlap. Six fit in one row on a 1920-wide screen.
- **Hangs and crashes** are recorded with their game (`status` = `hang` / `crash`) and count as no result. A
  tournament, it uses up one game of the match with no winner, like a drawn game. In a gauntlet, it is
  listed in the opponent table and left out of the record. Neither replays it.
- **Older round-robin battery:** `battery.py run` / `report` is the original every-pair-twice battery, writing
  to `build\cpu_battery\results.jsonl`. The tournament and gauntlet replace it for normal use.
- **Implementation details and measurements:** see `notes/cpu-battery-findings.md`.
