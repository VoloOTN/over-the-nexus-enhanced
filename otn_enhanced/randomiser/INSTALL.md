# Installing the Over the Nexus randomiser

Two ways to run it, easiest first. Pick one.

---

## 1. Just run the executable (no Python needed)

Grab `OTN-Randomiser.exe` and put it in a folder of your own — anywhere is fine.
Double-click it. The window opens; point it at your ROM and go.

That is the whole installation. Nothing is written to your system, there is no
uninstall, and the input ROM is never modified — you always get a new file.

**If Windows SmartScreen warns you** ("Windows protected your PC"), that is because
the executable is unsigned, which is normal for a one-off tool like this. Click
**More info → Run anyway**. If you would rather not, use method 2 instead.

Your antivirus may also flag it. PyInstaller bundles a Python interpreter inside
the `.exe`, and some scanners treat that pattern as suspicious on sight. If that is
a problem, method 2 avoids the bundle entirely.

**Decks work here too.** The bundle carries the 36 MB of source data deckgen needs to
rebuild its card pool from *your* randomised ROM, so deck regeneration runs in the
`.exe` with nothing else installed. Budget ~30 s for the pool on a first run, then
~1-2 s per deck across your cores. The pool is cached under
`%LOCALAPPDATA%\OTN-Randomiser\deckgen-cache`, so a repeat run with the same seed and
settings skips the rebuild (30 s → 1 s).

---

## 2. Run it from the repo

Same features as the `.exe`, and what you want if you are changing the code. Measured
on 8 cores: 26 s for the pool, 230 s for all 305 decks, **4.3 minutes** for the whole
run. `-j N` limits the worker count.

Needs **Python 3.12 or newer** and [uv](https://docs.astral.sh/uv/). If you install
Python from [python.org](https://www.python.org/downloads/), leave the default
"tcl/tk and IDLE" option on — that is Tkinter, which draws the window.

Install the dependencies once, from the repo root:

```
uv sync
```

Then run it from the repo root:

```
uv run python -m otn_enhanced.randomiser            # opens the window
uv run python -m otn_enhanced.randomiser --help     # command-line options
```

### Deck-stage data (one-off)

The deck stage needs four data files that are **not included in the repo**: the
YGOPRODeck card database, the ROM's card names, tournament decklists from
formatlibrary.com, and card categories from the Yu-Gi-Oh! Fandom wiki. Make them once
with:

```
uv run python -m otn_enhanced.tools.fetch_deckgen_inputs --rom path/to/your_eu_rom.nds
```

Expect about an hour and a half, nearly all of it the formatlibrary.com decklists: the downloads are paced so they don't
hammer either site. If it stops partway, run the same command again and it carries
on where it left off. `--force` rebuilds everything from scratch.

Without these files the deck stage is skipped, and every other stage still runs.

---

## Check it works before trusting a build

```
uv run python -m otn_enhanced.randomiser --selftest --rom path/to/rom.nds
```

Point it at the **stock** EU ROM, the randomiser's intended input. Its expected card counts are the
stock game's, so against the Vanilla+/Enhanced ROM the Speed Spell and seed-pile checks say BAD.

This writes nothing. It round-trips every structure the tool touches — all 4305
card records, all 305 decks, all three archives, the overlay-1 pack table — and
prints OK or BAD per check. If anything says BAD, stop and report it rather than
using the output ROM.

---

## First run, step by step

1. **Input ROM** → Browse to your Over the Nexus ROM.
   It must be the **EU** release, game code `BYYP`. The tool prints the game code
   and warns if it is something else; the pack options in particular are EU-only.
2. **Output ROM** → fills in automatically as `<name>_randomised.nds`. Change it if
   you like. It refuses to overwrite the input.
3. **Seed** → pre-filled with a fresh random value. The same seed and the same
   checkboxes always produce the same ROM, so keep it if you like the result. It is
   recorded at the top of the report either way.
4. Tick what you want randomised.
5. **Randomise**. The progress bar and stage label track the run; the log fills the
   bottom pane. Tick *Show every card below* first if you want the per-card list on
   screen (the report file always has it).
6. Play the output `.nds` in an emulator (melonDS) or on a flashcart.

Tick **Dry run** to see everything that would change without producing a ROM.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `No module named ndspy` | Run `uv sync` in the repo root, then start it with `uv run` (method 2). |
| `No module named tkinter` | Python installed without tcl/tk. Re-run the installer and enable it; on Linux `sudo apt install python3-tk`. |
| `error: input ROM not found` | Check the path; quote it if it contains spaces. |
| `WARNING: expected BYYP` | Not the EU ROM. Card randomisation still works; the pack options are EU-only and will refuse. |
| `overlay 1 loads at 0x…, expected 0x02141700` | Not the EU ROM — the tool stopped rather than writing to the wrong addresses. This is the guard working. |
| `deck stage skipped: the card pool has to be rebuilt …` | The deck-stage data is missing. Run `fetch_deckgen_inputs` (method 2, *Deck-stage data*). |
| `deck stage skipped: … seed pile … has no usable entries` | `deck_seeds.json` has no entries yet. |
| `deck_seeds.json is not valid JSON … trailing comma` | A comma after the last entry in the list. The other stages still run. |
| SmartScreen / antivirus warning | Unsigned PyInstaller bundle. Use method 2 to avoid it. |
