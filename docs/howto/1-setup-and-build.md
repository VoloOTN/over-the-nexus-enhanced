# HOWTO 1: Set up the dev environment and build the patched ROM

Full detail and the reasons behind each pin: [docs/SETUP.md](../SETUP.md).
All commands run from the repo root.

## Once

1. **Install uv** (PowerShell):
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
2. **Install Python + packages** (Python 3.14 and the exact versions in `uv.lock`):
   ```bash
   uv sync
   ```
3. **Arm GNU Toolchain 14.2.Rel1**: download `arm-gnu-toolchain-14.2.rel1-mingw-w64-i686-arm-none-eabi.zip`
   from Arm and extract it so this exists:
   `%USERPROFILE%\tools\arm-gnu-toolchain\bin\arm-none-eabi-gcc.exe`
   (or set `ARM_TOOLCHAIN` to its `bin` folder). Check:
   ```bash
   uv run python -m otn_enhanced.asm.cc
   ```
4. **CardWorkshop** in the folder that contains this repo (side by side), at the pinned commit:
   ```bash
   git clone https://github.com/BlueKitkallos/CardWorkshop.git ../CardWorkshop
   ```
   ```bash
   git -C ../CardWorkshop checkout 3934f5cc3a54986666ababffc929ad083a82275c
   ```
5. **Base ROMs**: your own EU (`BYYP`) dump, in three places (sha1s in [SETUP](../SETUP.md) step 4):
   - `data/over_the_nexus/backup/unpatched/eu.nds`: the **clean** dump (patches are made against it)
   - `data/over_the_nexus/backup/eu_apfix.nds`: anti-piracy fixed (the full build starts here)
   - `data/over_the_nexus/working/rom.nds`: the same anti-piracy-fixed ROM

   US / JP ROMs are **not** address-compatible.

6. **Single-card base ROM** (stock + step 0; standalone card builds start here):
   ```bash
   uv run python -m otn_enhanced.system.ov3_compact
   ```
7. **Deck-generator data** (randomiser decks and `.exe`; about 1½ hours, resumable):
   ```bash
   uv run python -m otn_enhanced.tools.fetch_deckgen_inputs --rom data/over_the_nexus/working/rom.nds
   ```
8. **Check the knowledge base proofs pass** (no failures once 5–7 are done):
   ```bash
   uv run python -m otn_enhanced.knowledge.verify_knowledge
   ```

## Build the patched ROM

```bash
uv run python -m otn_enhanced.build
```

Takes 10–16 minutes (`--vanilla-plus`: about 3). Output: `data/over_the_nexus/working/rom_all_patches.nds`,
with its sha256 printed; compare it with [notes/CURRENT-BASELINE.md](../../notes/CURRENT-BASELINE.md).
It aborts before writing anything if two patches claim the same slot.

Useful flags:

| flag | does |
|---|---|
| `--vanilla-plus` | stop after the Vanilla+ steps → `rom_vanilla_plus.nds` |
| `--patch xdelta` / `--patch bps` | also emit distributable patches (needs `xdelta3` / `flips` on PATH or in repo root) |
| `--only <module>`, `--start N`, `--upto N` | run part of the chain |
| `-v` | show each step's own output |

## Check it

```bash
uv run python -m otn_enhanced.verify data/over_the_nexus/working/rom_all_patches.nds
```

About 30 minutes; it should end with `0 failed`. Then load the ROM in melonDS.
A passing `verify()` is **not** in-game confirmation.

## Common failures

| message | fix |
|---|---|
| `arm-none-eabi-gcc is not 14.2.Rel1` | wrong toolchain version; install 14.2.Rel1 |
| CardWorkshop commit / modified files refused | `git -C ../CardWorkshop checkout <pin>` and discard local edits |
| allocation guard failed | two patches claim the same cave/cid; see [caves-and-allocation](../tutorials/caves-and-allocation/HOWTO.md) |

Deeper: [building-and-verifying](../tutorials/building-and-verifying/HOWTO.md).
