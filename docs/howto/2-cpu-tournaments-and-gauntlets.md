# HOWTO 2: Run CPU tournaments and gauntlets

The CPU plays itself in melonDS on a copy of the patched ROM. Full reference: [docs/cpu-battery.md](../cpu-battery.md).
All commands run from the repo root in PowerShell.

> Battery results are emulator evidence, **not** in-game confirmation of any card.

## Once

1. Finish [HOWTO 1](1-setup-and-build.md) and build `rom_all_patches.nds`.
2. Put `melonDS.exe` and `melonDS.toml` in the repo root. (Each worker gets its own tuned copy under
   `build\cpu_battery\w<k>\`.)
3. Build the battery ROM:
   ```bash
   uv run python -m otn_enhanced.tools.cpu_battery.battery build
   ```
   → `build\cpu_battery\battery.nds`.

**Rebuild the battery ROM every time `rom_all_patches.nds` changes**, and start runs with a new `--id` after.
The first run formats a save (`build\cpu_battery\formatted.sav`); leave that file alone.

## Tournament (whole pool, Swiss + top cut)

Two pools that never meet: `regular` (221 decks) and `turbo` (84 Speed Spell decks).

```bash
uv run python -m otn_enhanced.tools.cpu_battery.tournament run --pool regular
```
```bash
uv run python -m otn_enhanced.tools.cpu_battery.tournament run --pool turbo
```

Main options: `--id ID` (folder name; reusing it **resumes**), `--jobs N` (emulators at once, default 6;
max one per CPU thread), `--rounds`, `--cut`, `--swiss-bo`, `--cut-bo`, `--decks "pat*,..."` (small test pool).

Unattended (both pools back to back; edit the `--id`s in the script first):
```powershell
Start-Process powershell -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File','.\build\cpu_battery\run_tournaments.ps1'
```

**Stop:** close the window (or Ctrl-C, then close leftover melonDS windows). **Resume:** run the same command again.

**Results:** `data\cpu_tournaments\<id>\` → `standings.md`, `bracket.md`, `card_stats.csv`, `summary.json`.
Ratings (Elo-scale, auto-run at the end) → `data\cpu_tournaments\ratings\`. Re-run manually with
`... tournament ratings`.

## Gauntlet (one deck vs the rest of its pool)

```bash
uv run python -m otn_enhanced.tools.cpu_battery.gauntlet run wcs049_gaiza --duels 100
```

Deck name = the `deck.pac` name without `deck/` or `.ydc` (a typo lists close matches).
Default `--duels` = every opponent twice. Same `--id` / `--jobs` / resume behaviour as tournaments;
a larger `--duels` on an existing id extends it.

**Results:** `data\cpu_gauntlets\<id>\report.md` — win %, percentile, first/second split, worst matchups.
The percentile needs a tournament already played on the same battery ROM and pool; read the `±` before
trusting it.

## Testing one new card with the CPU

```bash
uv run python -m otn_enhanced.tools.cpu_battery.cardtest mirror data/over_the_nexus/working/rom_<card>.nds 0x1234 --duels 16 --jobs 4
```

A mirror deck of 3× the card plus filler plays itself; `activated > 0` means the CPU can play it.
`cardtest rows <rom> <cid>` checks statically for the CPU-row problem that stops donor Spells being played.

## Tips

- ~200 games/hour at 6 jobs.
- Offline logic check, no emulator: `... tournament selftest`.
- Hangs/crashes are recorded as no-result and never replayed.
