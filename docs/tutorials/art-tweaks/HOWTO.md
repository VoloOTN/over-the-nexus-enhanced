# Card art and field backgrounds

## Goal

Replace a card's pictures so they match the card it became, or give a converted Field Spell its duel background.

## Before you start

Each monster has up to three image stores, all located by the card's cid:

| Store | Where | Size | Notes |
|---|---|---|---|
| Card thumbnail | `card.pac` file 1 | 32×32, 8bpp, LZ10 | a full card in miniature |
| Cropped artwork | `card.pac` file 3 | 64×64, 4bpp, fixed 2820-byte stride | the zoom and detail view |
| 2D battle sprite | `duel2d/BattleMonster{1,2,3}.pac` | 256×96 | `<cid>.lz5bg`; splicing it did not work in-game and was removed, so these are left alone |

`data/card_art.py` swaps the first two. The 64×64 art is spliced in place; the 32×32 detail compresses larger
than the stock thumbnail, so `card.pac` file 1, its index table and its header are rebuilt and `card.pac` grows
by one `0x200` block.

Art does not touch effects or text, so it stacks at the end of a build. The build runs it twice (Vanilla+ cards,
then the rest) via `steps.VANILLA_PLUS_ART`.

## Steps

### 1. Make the images

From one card render (a standard portrait card image, for example 813×1185):

```
uv run python -m otn_enhanced.tools.make_card_art <image> --name Mystic_Piper --frame effect --out-dir <folder>
uv run python -m otn_enhanced.tools.make_all_card_arts            # every <password>.jpg in the art folder
uv run python -m otn_enhanced.tools.make_all_card_arts --force --character
```

Output: `<name>_32x32.png` (the real frame template with the art in its window), `<name>_64x64.png` (illustration
only), plus full-resolution and character variants. Frame templates are under
`data/over_the_nexus/card_arts/template_frames/`. Final images go in
`data/over_the_nexus/card_arts/implemented/<folder>/<Name>_<size>.png`.

### 2. Register the card

Add one line to `CARDS` in `data/card_art.py`:

```python
CardArt(0x13B8, "mystic piper", "Mystic_Piper"),     # cid, folder, file basename
```

If the card belongs to Vanilla+, also add its cid to `VANILLA_PLUS_ART` in `steps.py`; otherwise it is applied in
the second art step.

### 3. Field Spells need a background too

A card converted into a Field Spell freezes on activation unless a background file exists for its cid
(`/Duel2D/field/duel_field_magic%04d_P.LZ5bg`). `data/field_backgrounds.py` appends one per entry in its `CARDS`
dict to `duel2d/field.pac`, composed from the card's own 64×64 art.

Add the cid to `CARDS` there after converting it in `data/bulk_card_props.py`. The module enforces three limits
measured from stock backgrounds, because each was a real failure first: the tile budget (397), the stock
luminance envelope, and the duel field's zone grid stamped back on.

### 4. Build and look

```
uv run python -m otn_enhanced.build --only data.card_art --out data/over_the_nexus/working/rom_art.nds
```

## What the 64×64 encoder does, and why

(`rom/card_art_codec.py`, `encode_card_art_64x64`.) Three facts were not obvious and cost time:

1. **Sub-palette row 15 is reserved** by the zoom view for frame/UI colours. Tiles assigned to it render as
   blocky wrong colours in-game only. Quantise into 15 banks.
2. **Palette index 0 of every row is transparent.** Use it and 5 to 17% of pixels become holes. The encoder
   reserves it (15 rows × 15 colours).
3. **Quantise on the BGR555 lattice**, rounding to nearest rather than truncating.

The 32×32 thumbnail is a separate 8bpp path with a shared palette and is inherently grainy for new art.

## Check it

- Deck editor: the thumbnail is correct. Card detail view: the 64×64 art has no holes or blocky tiles.
- Validate encoder output by **dumping what the engine reads** (the tilemap palette bits and a histogram of
  index-0 pixels against stock, which must be 0). Do not round-trip through the project's own decoder: it paints
  index 0 from the palette, so the holes are invisible to it.
- Field Spell: activate it in a duel; it must not hang.

## Pitfalls

- A decoder that agrees with your encoder proves nothing about the console.
- Do not splice the battle sprite; that path is known not to work.
- `card.pac` file 1 is rebuilt, so run the art step after anything else that edits `card.pac`.
