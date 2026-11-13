# Card art

Card art is **not included** in this repo. Card images belong to Konami and the
frame templates come from the game, so you supply both yourself.

The build works without any of it: any card with no art keeps the donor card's
stock picture, and the build prints a `WARNING: no art PNGs for N card(s)` line
listing them. Follow this page if you want the new cards to show their real art.

All commands run from the repo root.

## 1. Get the card database

The art tool looks cards up in YGOPRODeck's card database. Download it once:

```
mkdir scratch
curl -o scratch/ygoprodeck_cache.json "https://db.ygoprodeck.com/api/v7/cardinfo.php?misc=yes"
```

(The deck generator and the card-text tools read this same file.)

## 2. Extract the frame templates from your ROM

Each 32x32 thumbnail is a stock card frame with the new art pasted into its
picture window. The frames come from your own ROM:

```
uv run python -m otn_enhanced.rom.extract_card_images --rom path/to/your_eu_rom.nds --out scratch/extracted --skip-battle --skip-models
```

From `scratch/extracted/card_art_32x32/`, pick one thumbnail of each frame type
and copy it to `data/over_the_nexus/card_arts/template_frames/` under these names:

| File | Pick any thumbnail of a... |
|---|---|
| `effect_32x32.png` | Effect Monster (orange frame) |
| `fusion_32x32.png` | Fusion Monster (purple) |
| `synchro_32x32.png` | Synchro Monster (white) |
| `ritual_32x32.png` | Ritual Monster (blue) |
| `spell_32x32.png` | Spell (green) |
| `trap_32x32.png` | Trap (pink) |

The picture inside the frame doesn't matter, because it is covered by the new art.

## 3. See which card images you need

```
uv run python -m otn_enhanced.tools.make_all_card_arts --build-set
```

This prints every image the build still needs, as `<password>.jpg  <card name>`.
The password is the card's 8-digit number, which is also its image name on
YGOPRODeck. Get a standard full-card picture for each one (YGOPRODeck's are
813x1185) and save it as `data/over_the_nexus/card_arts/<password>.jpg`.

A card listed under "Not in the ygoprodeck cache" can't be looked up
automatically. Make that one by hand (step 5).

## 4. Generate the art

Run the same command again:

```
uv run python -m otn_enhanced.tools.make_all_card_arts --build-set
```

It crops each image and writes the 32x32 thumbnail and 64x64 artwork to
`data/over_the_nexus/card_arts/implemented/`, where the build reads them.
Cards that already have art are skipped. `--force` regenerates them all.

**Battle sprites (optional).** To also replace the 2D attack sprites, add
`--character`. This removes each picture's background, so it needs the optional
packages (`uv sync --extra bgremove`) and the `isnet-general-use.onnx` model in
`~/.u2net/`. Without it the cards keep their stock sprites.

## 5. Making one card by hand

```
uv run python -m otn_enhanced.tools.make_card_art CARD.jpg --frame effect --out-dir "data/over_the_nexus/card_arts/implemented/<folder>" --name <Base>
```

Take `<folder>` and `<Base>` from that card's line in `CARDS` in
`otn_enhanced/data/card_art.py`.

Then rebuild the ROM.
