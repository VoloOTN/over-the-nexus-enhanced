# Setup

Everything needed to build the Over the Nexus ROM hack (`otn_enhanced`) and the randomiser from a
fresh machine. Each pinned item below changes the bytes of the built ROM if it changes, so the build
checks the pins itself and stops with a message pointing back here if one is wrong.

All commands run from the repo root.

## Pinned versions

| What | Pinned to | Checked by |
|---|---|---|
| Python | 3.14 (`.python-version`) | uv |
| Python packages | `pyproject.toml` + `uv.lock` (ndspy 4.2.0, capstone 5.0.9, …) | `uv sync` |
| Arm GNU Toolchain | **14.2.Rel1** (`arm-none-eabi-gcc` 14.2.1 20241119) | `otn_enhanced/asm/cc.py` `GCC_VERSION` |
| CardWorkshop | **`3934f5cc3a54986666ababffc929ad083a82275c`** ([BlueKitkallos/CardWorkshop](https://github.com/BlueKitkallos/CardWorkshop), MIT) | `otn_enhanced/system/cardworkshop_speed_view.py` `CW_COMMIT` |
| Base ROMs | EU `BYYP`: clean dump + anti-piracy-fixed copy (step 4) | not checked: compare sha1 by hand |

armips is **not** needed: it is only used by CardWorkshop's card/text/duel fixes, which this build
leaves out.

## 1. uv and Python

Install [uv](https://docs.astral.sh/uv/getting-started/installation/):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then:

```bash
uv sync
```

This installs Python 3.14 if you don't have it, creates `.venv`, and installs exactly the versions in
`uv.lock` (ndspy, capstone, pillow, numpy, pandas, pyyaml, pyinstaller). Run everything through
`uv run python …`; there is nothing to activate. If you install Python yourself from python.org, keep
the "tcl/tk" option on: the randomiser's window needs Tkinter.

`uv sync --extra bgremove` adds onnxruntime, used only by `make_card_art --character`
([HOWTO 5](howto/5-card-art.md)).

## 2. Arm GNU Toolchain 14.2.Rel1

Used to compile the C effect stubs and CardWorkshop's speed-up / View Mode code. Download the
**14.2.Rel1** `arm-none-eabi` build for your host from Arm's
[download page](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads):

| Host | Archive |
|---|---|
| Windows | `arm-gnu-toolchain-14.2.rel1-mingw-w64-i686-arm-none-eabi.zip` |
| Linux x86_64 | `arm-gnu-toolchain-14.2.rel1-x86_64-arm-none-eabi.tar.xz` |
| macOS (Apple silicon) | `arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi.tar.xz` |

Extract it so the compiler is at `~/tools/arm-gnu-toolchain/bin/arm-none-eabi-gcc` (on Windows,
`%USERPROFILE%\tools\arm-gnu-toolchain\bin\arm-none-eabi-gcc.exe`). To keep it elsewhere, set
`ARM_TOOLCHAIN` to its `bin` folder. Check it:

```bash
uv run python -m otn_enhanced.asm.cc
```

A different version is refused (`arm-none-eabi-gcc is not 14.2.Rel1`), because it would change the
ROM bytes and with them every baseline hash.

## 3. CardWorkshop

The build's first step applies CardWorkshop's CPU speed-up and View Mode, imported from a checkout
next to this repo (it is not copied in here). Clone it into the folder that contains this repo, so the
two sit side by side, and check out the pin:

```bash
git clone https://github.com/BlueKitkallos/CardWorkshop.git ../CardWorkshop
```

```bash
git -C ../CardWorkshop checkout 3934f5cc3a54986666ababffc929ad083a82275c
```

To keep it elsewhere, set `CARDWORKSHOP` to its folder. The step refuses a checkout at any other
commit, or one with modified tracked files.

## 4. Base ROMs

Use your own dump of *Yu-Gi-Oh! 5D's World Championship 2011: Over the Nexus* (Europe, game code
`BYYP`). The US (`BYYE`) and Japanese builds are not address-compatible. Three copies are needed:

| Path | What | sha1 |
|---|---|---|
| `data/over_the_nexus/backup/unpatched/eu.nds` | the **clean** dump; distributable patches are made against it | `7617788d197ffd45d2ab2bb6deadbf0f9874e2fa` |
| `data/over_the_nexus/backup/eu_apfix.nds` | anti-piracy fixed; what the build starts from (`build.CLEAN_SRC`) | `a90f3d0cc51f29bd58738fa0fec9ee1ba765ab2f` |
| `data/over_the_nexus/working/rom.nds` | the same anti-piracy-fixed ROM; the knowledge checks and step 5 read it | `a90f3d0cc51f29bd58738fa0fec9ee1ba765ab2f` |

## 5. Single-card base ROM

Every card module can be built on its own (`uv run python -m otn_enhanced.cards.<card>`). Those
standalone builds start from `rom_ov3_compact.nds` (the stock ROM plus step 0, which frees dead
overlay-3 code for injected stubs). Make it once:

```bash
uv run python -m otn_enhanced.system.ov3_compact
```

It writes `data/over_the_nexus/working/rom_ov3_compact.nds`. A few cards' `verify()` and several
knowledge checks read it too.

## 6. Deck-generator data (randomiser decks)

The randomiser's deck regeneration, its `.exe`, and a few knowledge checks need data that is not in
the repo: the YGOPRODeck card database, the ROM's card names, formatlibrary.com decklists and Fandom
wiki categories. Download it once (about 1½ hours, nearly all of it the decklists: the requests are paced on purpose; if it stops,
run it again and it resumes):

```bash
uv run python -m otn_enhanced.tools.fetch_deckgen_inputs --rom data/over_the_nexus/working/rom.nds
```

It writes `scratch/ygoprodeck_cache.json`, `scratch/cid_to_name.json`,
`scratch/formatlibrary_decks.json` and `data/deckgen/wiki_categories.json`. Without them everything
else still works; the randomiser just skips the deck stage. More:
[otn_enhanced/randomiser/INSTALL.md](../otn_enhanced/randomiser/INSTALL.md).

## 7. Check the setup

```bash
uv run python -m otn_enhanced.knowledge.verify_knowledge
```

With steps 4–6 done this reports no failures.

```bash
uv run python -m otn_enhanced.build
```

The full (Enhanced) build takes **10–16 minutes**; `--vanilla-plus` takes about 3. It writes
`data/over_the_nexus/working/rom_all_patches.nds` and prints its sha256: compare it with
[notes/CURRENT-BASELINE.md](../notes/CURRENT-BASELINE.md). Then check every card:

```bash
uv run python -m otn_enhanced.verify data/over_the_nexus/working/rom_all_patches.nds
```

This takes about 30 minutes and should end with `0 failed`. Building and verifying in detail:
[docs/tutorials/building-and-verifying/HOWTO.md](tutorials/building-and-verifying/HOWTO.md).

For in-game testing, use melonDS (GDB stub on port 3333): see
[debugging-in-game](tutorials/debugging-in-game/HOWTO.md).


To check the randomiser itself:

```bash
uv run python -m otn_enhanced.randomiser --selftest --rom data/over_the_nexus/working/rom.nds
```

Run the self-test against the **stock** EU ROM. It is the input the randomiser is made for, and the
self-test's card counts are the stock game's, so pointed at the Enhanced ROM it reports `BAD` on the
Speed Spell and seed-pile checks.

## Changing a pin

1. Change the pin in the file listed in the table above (`CW_COMMIT`, `GCC_VERSION`, `.python-version`
   or `uv lock --upgrade-package <name>`).
2. Rebuild, and expect a different sha256: re-record the baseline in
   [notes/CURRENT-BASELINE.md](../notes/CURRENT-BASELINE.md).
3. Update the table in this file.
