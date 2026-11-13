# Pyramid of Light -> Field Spell conversion (0x17BF)

Goal (user request, a deliberate deviation from the printed card): convert
Pyramid of Light -- printed a **Continuous Trap** -- into a **Field Spell**.

Printed text (scratch/ygoprodeck_cache.json, quoted):
> "If this face-up card is removed from your side of the field, destroy
> "Andro Sphinx" and "Sphinx Teleia" on your side of the field and remove them
> from play."  type: Trap Card / race: Continuous

## In-game report (user, 2026-09-07)

Verbatim: "See .ml2, the card goes to the wrong slot, and also freezes when it
activates." + "It goes to an ordinary s/t zone instead of the field zone. I
dont know if the symptoms are the same event"

Savestate: `data/over_the_nexus/working/rom_test.ml2`.

## Confirmed (this session)

- **cid 0x17BF** = Pyramid of Light (scratch/cid_to_name.json).
- **The card_prop edit landed and is LIVE in the duel.** patch_bulk_card_props
  entry `COPY_FROM REFERENCE_FIELD_SPELL_CID` (Forest 0x10F0) writes
  `bf1700001b822e00` against Forest's `f01000001b822e00` -- the upper 4 bytes are
  IDENTICAL, so it is a whole-record template copy, not the one-field flip that
  carddata.card_genre_type_tags / patch_w_nebula_meteorite warn about. Read back
  out of the savestate's **live RAM** at 0x022E70DC: `card_type = Spell Card,
  spell_trap_subtype = Field`.
- **The player's zones are ONE 11-slot array of 0x14-byte records at
  player+0x34** (player base 0x0229AC94, stride 0xB3C):
  - index 0..4  monster     (+0x34 +0x48 +0x5C +0x70 +0x84)
  - index 5..9  spell/trap  (+0x98 +0xAC +0xC0 +0xD4 +0xE8)
  - index 10    **field**   (+0xFC)
  Proved by censusing every `*.ml*` savestate in working/ against card_prop:
  +0xFC held a Field Spell in 23/23 hits; the monster offsets held only
  monsters; the S/T offsets only non-Field Spells/Traps.
- **The symptom reproduces in the savestate**: cid 0x17BF sits at side 0
  **+0xC0 = spell/trap slot 3**, and the field zone +0xFC is empty.
- **ROOT CAUSE FOUND: `card_intid.bin` carries its own copy of the
  classification, and the field-zone placement reads THAT, not card_prop.**
  - `0x02029E1C(cid)` -> u16 from a flat array indexed `(cid - 0xD48)`, table at
    `[[lit+0x10]+0x3C]`. Low 14 bits = the card_prop RECORD INDEX; **bit 15 =
    MONSTER**; **bit 14 = FIELD SPELL**.
  - Censused over all 4305 cards, **zero mismatches both ways**: bit 15 on
    2550/2550 monsters and 0/1755 Spells+Traps; bit 14 on 65/65 Field Spells and
    0/4240 everything else.
  - Readers: `0x02029E60` tests bit 15, **`0x02029E80` tests bit 14**.
  - The spell-activation resolver at **0x02217EBE** calls `0x02029E80`; only on
    TRUE does it destroy whatever holds zone 0xA and set the destination zone to
    0xA. On FALSE it falls through to ordinary S/T placement at 0x02217EF4.
  - PoL's intid was `0x0617` -- **bit 14 clear**. Forest's is `0x4197`, Dragon
    Ravine's `0x4FB1`. That is the whole wrong-zone bug.
- card_prop accessor family (`bl 0x0202A084 ; ldr r0,[r0,#4] ; lsls ; lsrs`):
  0x0202ABB8 race, 0x0202ABC8 attribute, 0x0202ABD8 level, **0x0202ABE8
  spell/trap subtype**, 0x0202ABF8 card_type>>1.
- The engine DOES also gate on card_prop's subtype, but only to VALIDATE an
  already-chosen zone: 0x02255A94 rejects a monster in zone index >= 5 and
  rejects a subtype-2 card in any zone index != 0xA.
- **Pyramid of Light has NO cls0/cls1/cls2/cls3 record** (all four tables
  searched). Whatever drives its printed Continuous-Trap effect is not there.

## Ruled Out

- **card_genre.bin does NOT carry a Field-Spell tag.** Whole-table census: of
  the 65 Field Spells, one has genre `0x0000000000000000`, so no bit can be the
  marker; Chain Energy (an ordinary Continuous Spell) is also 0. Leaving PoL's
  genre at its old 0x4400 is NOT the cause of the wrong zone.

## Fix applied (NOT yet in-game tested)

`patch_bulk_card_props` now derives BOTH intid bits from the post-edit card_prop
fields on every CHANGES entry, so the two files can no longer disagree. On the
current CHANGES set it changes exactly one u16 -- `card_intid[0x17BF]:
0x0617 -> 0x4617` -- confirmed by diffing the built ROM's card_intid.bin against
stock. `rom_test.nds` rebuilt.

## Freeze: DIAGNOSED (2026-09-07, from the freeze savestate)

**It is a data abort in a filename lookup, and the ARM9 abort vector is `B .`.**

- ARM9 CPU state in `rom_test.ml2` (savestate section `ARM9` @file 0x01018D7F):
  **CPSR = 0x40000097 -> mode 0b10111 = ABORT, IRQs masked**, and the saved
  vector words in that block are `0xEAFFFFFE` = ARM `b .` -- a branch to self.
  So the "freeze" is an exception whose handler is an infinite loop.
- The faulting code is the ARM9 C-library **strlen at 0x02016C84**
  (`ldrsb r2,[r0,r1] ; adds r0,#1 ; cmp r2,#0 ; bne`), reached from the
  strcmp-style wrapper at 0x02016C98 (calls 0x02016C84 twice and subtracts).
  A name-table scan that runs past its last entry aborts exactly here.
- **The filename it was looking for is in RAM at the freeze**:
  `duel_field_magic6079_p.lz5bg` and `duel_field_magic6079_P.LZ5bg`
  (0x030241A0 / 0x030243C1). 6079 = 0x17BF = Pyramid of Light.
- **That file does not exist.** `Data_arc_pac/duel2d/field.pac` holds exactly
  **64** background images named `duel_field_magic<cid-in-decimal>_p.lz5bg`.
  Cross-referenced against card_prop: the game has 65 Field Spells, and
  **every one of them has a background except Speed World 0xDAC** (a
  Turbo-Duel card that never reaches this path). Pyramid of Light has none.

### The exact code site (overlay 3, ARM mode)

`0x02170F50(r0, r1 = card number)` builds the background path:

    02170F50  push {r3,r4,r5,lr}
    02170F54  sub  sp,sp,#0x128
    02170F58  movs r2,r1              ; r2 = the number, sets flags
    02170F5C  add  r0,sp,#0x28        ; destination buffer
    02170F60  bne  0x02170F70
    02170F64  ldr  r1,=0x02291EA8     ; "/Duel2D/duel_stage_part2_P.LZ5bg"
    02170F68  blx  0x0208C988         ;   -> plain strcpy: the DEFAULT stage
    02170F6C  b    0x02170F78
    02170F70  ldr  r1,=0x0229207C     ; "/Duel2D/field/duel_field_magic%04d_P.LZ5bg"
    02170F74  bl   0x020508F0         ;   -> sprintf(buf, fmt, cid)
    02170F78  add  r0,sp,#0x28
    02170F7C  mov  r1,#4
    02170F80  mov  r2,#0
    02170F84  blx  0x020168E8         ; open by name  <-- the abort is downstream of here

**`r1 == 0` is a NATIVE, supported path: it loads the default duel stage
instead of a field background.** That is the cheap, non-crashing behaviour for a
converted card with no art of its own.

### field.pac geometry (fully decoded this session)

⚠️ Supersedes an earlier draft of this section that put the file table at 0x810
with absolute addresses -- that was wrong and decoded 63 of 64 files as garbage.

`Data_arc_pac/duel2d/field.pac`, 0x13F600 bytes, is built from **0x200-byte
chunks**:

- **Name chunks, 0x000-0x7FF (four of them).** Each is `00 00 04 <sep>` then 16
  entries of `<u8 name_len><u8 ?><name>`; for these 28-char names that is 30
  bytes each, so 3 + 16*30 = 483 and the last 29 bytes of every chunk are zero.
  4 x 16 = **64 names**, ending at 0x7E3.
- **Table chunks.** 0x800 starts `FF FF 00 00 00 00 00 00` (the 0xFFFF marker on
  a 16-byte boundary), then **(u32 rel_addr, u32 size) pairs from 0x808** --
  63 of them, filling the chunk exactly. A second table chunk at 0xA00 has its
  own 8-byte head (`00 00 02 00 00 00 00 00`) and holds the last 2 pairs
  from 0xA08. So slot(k) = 0x808 + 8k for k < 63, else 0xA08 + 8*(k-63).
- **`rel_addr` is relative to the data base 0xC00**, and files are 0x200-aligned.

**There are 65 files but only 64 names, and `file k carries name k-1` -- file 0
is UNNAMED.** Proven by decoding: file 61 is unmistakably Forest (name 60 =
`duel_field_magic4336_p`, Forest 0x10F0) and file 60 is the Skyscraper 2 - Hero
City cityscape (name 59 = `..._magic7004_p`). Ground truth for the whole table
came from scanning 0x200-aligned offsets for `11 ?? ?? ?? ?? 'NTBG'`, which finds
exactly 65 starts, each equal to its table entry + 0xC00.

Every background is **256x192, LZ11-compressed NTBG** with two sections,
`PALT` (0x20C bytes = one 256-colour palette) and `BGDT` (8bpp tiles). The
rendered image is a set of panels with wide gaps; the gaps are palette **index
0 = (248,0,248)**, the conventional transparent marker.

**RESOLVED -- the second byte of a name entry is the XOR of all the name's
bytes.** A one-byte checksum, matching **65/65** entries. An earlier attempt
scored only 55/64 because the NAME LIST ITSELF was mis-parsed: entry 22 is
`fl_icon.lz5bg`, **13 chars, not 28**, and a fixed 30-byte stride desynchronised
everything after it. Walking with the length byte gives **65 names**, which
matches the 65 files exactly -- so the mapping is **1:1, file k = name k**, and
the earlier "file 0 is unnamed / file k carries name k-1" reading was an
artifact of the same bug. It still lands Forest on file 61 and Skyscraper 2 on
file 60, so the image evidence is unchanged.

So a name entry is `<u8 name_len><u8 xor_of_name_bytes><name>`, and the chunk
head is 3 bytes `00 00 <n>` where n = 4 = the number of name chunks (bin2.pac
has `00 00 04 0d`, Common.pac `00 00 02 0f` -- the 4th byte is just the first
entry's length). For the new entry:

    name = "duel_field_magic6079_p.lz5bg"
    len  = 0x1C
    xor  = 0x34

Adding it needs a 5th name chunk, which pushes the table chunks from
0x800/0xA00 to 0xA00/0xC00 and moves the data base off 0xC00 -- so the archive
gets relaid and every rel_addr recomputed. The chunk-head count must go 4 -> 5.

### The lz5bg encoder: FIXED (index 0)

`encode_lz5bg` is template-based (it takes the original blob for compression
type, section layout, bpp and dimensions) and it now **round-trips
pixel-identically**. It did not before: `_map_to_palette` routed a pixel to
palette index 0 only on `alpha < 128`, but `decode_lz5bg` renders index 0 as its
literal colour on a fully opaque image, so every gap pixel was re-matched
against `palette[1:]`. Measured on Forest: **23808 of 49152 pixels turned
(248,0,248) into (144,96,176), and every other pixel was already exact.**

Fix: map a pixel to index 0 when it is transparent **or** exactly equals
`palette[0]`. Same class of bug as `reserve_index0` in card_art_codec.
Guarded by `tests/tools/test_lz5bg_roundtrip.py` (2 checks, both pass).
⚠️ `.venv-1` has no pytest; the checks were run by importing the module directly.

**Consequence: authoring a real background is now a solved pipeline** -- supply
a 256x192 PNG using (248,0,248) for the gap areas, encode against any existing
background as template, and the bytes are correct.

## field.pac format: FULLY DECODED AND VALIDATED

Validated by re-parsing **every .pac in the ROM** with the same model -- the XOR
checksum holds for every name in 25 archives, and the table heads match the
computed entry counts everywhere:

- **Name area**: N chunks of 0x200, each starting `00 00 <N>` (so byte[2] is the
  NAME-CHUNK COUNT), then entries `<u8 name_len><u8 xor_of_name_bytes><name>`
  packed until the next would not fit.
- **File table**: starts at `N * 0x200`, also 0x200 chunks, 8-byte head then
  `(u32 rel_addr, u32 size)` pairs, **63 per chunk**. A full chunk that
  continues is headed `00 00 FF FF`; **the LAST table chunk is headed
  `00 00 <entry count>`** -- confirmed against tail counts on bin(5), bin2(36),
  CALC2D(21), duel2d(52), DCustom(1), effect(2), MenuCommon(62), pack(54) ...
- **Data base** = the first 0x200 boundary after the table; files are
  0x200-aligned, in index order, and **file k carries name k**.
- field.pac: 65 names / 65 files, 4 name chunks, table at 0x800 (0xFFFF) +
  0xA00 (count 2), data base 0xC00.

## Fixes applied (all NOT yet in-game tested)

1. **Zone** -- `patch_bulk_card_props` syncs the card_intid bits.
   `card_intid[0x17BF]: 0x0617 -> 0x4617`. **IN-GAME CONFIRMED by the user
   2026-09-07**: the card now goes to the field zone.
2. **lz5bg encoder** -- `_map_to_palette` now routes a pixel to index 0 on an
   exact `palette[0]` match as well as on alpha, making decode->encode lossless
   (it was corrupting 23808 of 49152 pixels); and a new `rebuild_palette=True`
   derives a fresh BGR555-lattice palette from the new image instead of reusing
   the template's, because replacement art was otherwise mapped onto the
   template card's colours (Pyramid of Light came back in Forest's greens).
   Guarded by `tests/tools/test_lz5bg_roundtrip.py`.
3. **Background** -- new module `patch_field_backgrounds.py` appends a 66th file
   `duel_field_magic6079_p.lz5bg` (xor 0x34) to field.pac. Artwork is Pyramid of
   Light's own 64x64 card art (card.pac file3 atlas index 1559 -- note that is
   the card_prop record index INCLUDING the 8-byte header, the same number
   card_intid stores) scaled x4 and cropped to 256x192, with Forest's
   transparent mask punched through so the card zones read normally.
   The entry is APPENDED so no existing file's index moves.
   `verify()`: new file at index 65 of 66; all 66 decode at 256x192; all 65
   stock files byte-identical and still at their old index.

`rom_test.nds` = stock + patch_bulk_card_props + patch_field_backgrounds,
129338504 bytes, sha256 c4461a484ad9b10e...
⚠️ NOT wired into apply_all_patches -- single-card test ROM only, per CLAUDE.md.

## Round 2 in-game result (user, 2026-09-07)

Verbatim: "The game didn't crash! however the art-work looks a bit out of whack!"
plus a screenshot: top screen drew the pyramid, bottom screen drew a slice, then
black, then a band of garbage.

- **THE FREEZE IS FIXED -- IN-GAME CONFIRMED BY THE USER 2026-09-07.** Pyramid of
  Light activates as a Field Spell, lands in the field zone, and does not hang.
- **The garbage was a CHARACTER-DATA BUDGET OVERRUN, and it is now fixed.**
  `_build_bgdt_section` documented itself as using "a simple tilemap where each
  map position references a unique tile (no tile de-duplication)", so a 256x192
  background came out as **768 tiles / 49152 bytes**. Every one of the 65 stock
  field backgrounds is between **312 and 397 tiles**, and five sit exactly on
  397 -- so 397 is the cap, and past it the picture drew to the budget and then
  went black and garbage.
  Fix: de-duplicate identical tiles, using the tilemap's H/V flip bits so a
  mirrored block is free too (a flip is its own inverse, so the tile to look up
  under flags (h,v) is the block flipped the same way). Pyramid of Light now
  encodes to **386 tiles / 24704 bytes**, inside the budget, and the decoded
  image is unchanged (de-duplication is lossless). The BGDT tilemap index is
  only 10 bits, so the encoder now also raises above 0x3FF tiles.
  `patch_field_backgrounds` computes the budget from the stock files on every
  build and in `verify()` -- it is never hardcoded.

`rom_test.nds` rebuilt: field.pac 1308160 -> 1324544 bytes, new file 15535 bytes
at index 65 of 66, 386 tiles. verify() passes all four checks.

## Round 3 in-game result (user, 2026-09-07)

Verbatim: "Better but I cannot see the duel field now" + a screenshot showing the
background drawing correctly and completely on both screens (no black, no
garbage), but washing out the play area.

- **The tile-budget fix worked**: the background renders fully.
- **Cause of the washout: the art was brighter than any stock background.**
  Measured over the opaque pixels of all 65 stock backgrounds: mean luminance
  **42..137, median 92**, and **at most 13.9%** of pixels above 200. Pyramid of
  Light's blown-up card art was **mean 159 with 45.8% above 200**. The duel
  field's mat and zone outlines are drawn to read against a mid-dark
  background, so a near-white field hides them.
- **Fix: tone the art into the stock envelope before encoding.**
  ⚠️ It must be a LINEAR scale, not gamma -- the pyramid face is blown out to
  near-white and `255 ** g == 255` for every gamma, so a gamma curve cannot pull
  the highlights down at all; it bottomed out at mean 113 with 27.8% still above
  200 and the build guard rejected it. A linear scale solved by binary search
  against the stock median gives **mean 104, 0.0% above 200**.
- Both the target and the reject threshold are computed from the stock files at
  build time, never hardcoded, and `main()` aborts if the art is brighter than
  the worst stock background.

`rom_test.nds` rebuilt: new file 13373 bytes, 386 tiles, mean luminance 104.
verify() passes all four checks.

## Round 4 (user, 2026-09-07) -- THE ZONE GRID IS PAINTED INTO THE ART

The user diagnosed this one: "I think the issue is that the art for a field
spell have the field zones drawn into it".  Correct, and it is the reason the
duel field vanished.

- **The duel field's zone grid is part of every background's pixel data.** It is
  NOT a separate overlay asset and it is NOT part of the transparent mask, so
  replacing all of a background's opaque pixels with new art deletes the field.
- **It cannot be recovered by intersecting the backgrounds**: each one tints its
  own frame, so only **879** opaque pixels are byte-identical across all 64, and
  they render as a few stray tick marks.
- **The per-pixel SPREAD isolates it cleanly.** The furniture is near-constant
  across backgrounds, the scenery is not, and the split is sharply bimodal:
  5299 pixels at sd<5, rising only to 6474 by sd<30. Anywhere on that plateau
  gives the same mask, and at sd<20 it is **6238 pixels forming exactly the
  5x2 zone grid on both screens**. Colours are the per-pixel median across the
  64 backgrounds.
- `derive_field_furniture()` computes mask and colours from the stock files at
  build time; `compose_background()` tones the art, stamps the grid over it,
  then punches the transparent mask.
- ⚠️ The grid costs tiles: 386 -> **394 of the 397 budget**. That is tight, and
  the build guard is what will catch any future change that pushes it over.
- `fl_icon.lz5bg` (field.pac index 22, 13-char name) is a 64x64 ICON, not a
  frame layer -- checked and ruled out.

`rom_test.nds` rebuilt: new file 12952 bytes, 394 tiles, mean luminance 105,
3.9% above 200. verify() passes all four checks.

## Round 5 -- brightness restored (user asked for it back)

Toning to the stock MEDIAN (92) was a belt-and-braces reaction to the duel field
being invisible; that turned out to be the missing zone grid, not the
brightness, so with the grid restored the art can sit at the top of the stock
range instead of the middle.

Two things the naive fix got wrong, both caught by the build guard, not by a
duel:

1. **Targeting the brightest stock MEAN (137) overshoots to 145**, because the
   zone grid is stamped AFTER toning and is itself mid-bright. The search has to
   run over the FINISHED picture, not the raw art.
2. **The mean is not the binding constraint -- the bright-pixel fraction is.**
   The pyramid face is blown out to near-white, so a scale putting the mean at
   137 still leaves **38.6% of pixels above 200** against a stock worst of
   13.9%. Solving on the fraction makes the mean follow.

`brightest_legal_scale()` now binary-searches the linear scale for the largest
value whose COMPOSED background satisfies both caps. Result: **scale 0.816 ->
mean 128 (brightest stock 137), 12.8% above 200 (stock worst 13.9%)** -- i.e.
brighter than 63 of the 64 stock backgrounds and right up against the cap.

`rom_test.nds` rebuilt: new file 14098 bytes, 388 tiles, verify() passes all four.

## Round 6 -- the lit bezel edges

User: "There are some bezels on the stock frame that are being lost, like appear
to be a little more brighter than the rest of the card".  Correct: every zone has
a LIT edge -- a bright gold/white line along its bottom and left -- and the
variance mask was dropping it.

- **No sd threshold can recover it.** The bezel highlight's colour follows the
  scene (gold in Forest, blue elsewhere), so its spread across the 64
  backgrounds is **51.5 -- HIGHER than the 49.8 of open scenery**. The mask
  curve jumps straight from 6796 pixels at sd<40 to 23615 at sd<60; there is no
  intermediate plateau. Per-background luminance normalisation does not help
  either (~6300 pixels, same mask).
- **What is fixed is the GEOMETRY**, so recover it structurally: grow the frame
  mask by `BEZEL_DILATE` = 2 and keep only the grown pixels whose MEDIAN
  background colour is genuinely bright (`BEZEL_LUMA` > 140).
  Plain dilation without the brightness test also works visually but paints a
  thick grey ring over real scenery (42.6% of the opaque area at r=2, against
  28.9% with the test).
- ⚠️ **BEZEL_LUMA is TUNED BY EYE, not derived** -- and that is worth being
  explicit about, because everything else in this module is computed from the
  stock files. There is no statistic to solve against: the frame's median
  luminance is 72 and the scenery's is 70. 140 is roughly double both; 120 and
  160 look near-identical, so the setting is not delicate.

Result: furniture 6238 -> 7326 pixels, **388 tiles**, mean luminance 129, 12.9%
above 200 -- so the bezels came back at no cost to brightness or budget.

## Generalised (2026-09-07)

`patch_pyramid_field_bg.py` -> **`patch_field_backgrounds.py`**, driven by a
`CARDS` dict. Adding a Field Spell is now two edits: a `COPY_FROM
REFERENCE_FIELD_SPELL_CID` entry in patch_bulk_card_props, and the cid here.
The archive is rebuilt from scratch and grows its own name/table chunks, so
nothing else changes.

- Art index per card is read from **card_intid's low 14 bits** rather than
  recomputed -- that is the atlas index directly, and it is what stops the
  off-by-one that first fetched a completely different card's art.
- Added: **Toon World 0x12BE** and **Vylon Element 0x24B5**, both Continuous
  Spells (ygoprodeck), so the conversion only moves the subtype 4 -> 2.
  `card_intid`: 0x0267 -> 0x4267 and 0x10BC -> 0x50BC.
- Build: 65 -> 68 files, field.pac 1308160 -> 1361920 bytes. Pyramid 388 tiles /
  mean 129; Toon World 397 / 108; Vylon Element 397 / 137. verify() passes.

### ⚠️ CORRECTION: 397 is NOT a measured hardware budget

Earlier rounds of this note (and the code comments) called 397 "a FIXED
character-data budget the game enforces". **That was over-stated.** 397 is a
STRUCTURAL CEILING of the canvas: of the 768 8x8 cells in 256x192, **372 are
entirely transparent** and collapse to one shared tile, leaving **396** that can
differ -- so 396 + 1 = 397 is just what any image needs when every non-gap cell
is unique. That is why five stock backgrounds sit exactly on 397, and why two of
ours now do too; it is not a coincidence and not a cap being hit.

What is actually established: an un-deduplicated **768**-tile encode drew black
and garbage in game, and de-duplicated output at **388..397** works (Pyramid of
Light, user-confirmed). **The real limit is somewhere in 398..768 and has never
been measured.** The build check therefore means "no worse than the busiest
stock background" -- a sound bound to hold to, but not a measured one. Both
code comments have been corrected.

## Framing: plain resize, no crop (user, 2026-09-07)

"Instead of doing a crop and then blow proportions out, just do a resize? the
vylon element art is quite harsh".

`card_canvas` now does a straight `resize((256, 192))` instead of
scale-to-256x256-then-crop, and `crop_top` is gone from `CARDS` (which is back
to a plain cid -> label dict). Cropping preserved the 1:1 aspect but threw away
a quarter of every picture, and on busy art the cut landed mid-subject. The
stretch distorts 4:3 horizontally, which on art this soft is the lesser evil.

Rebuilt: Pyramid 378 tiles / mean 128 / 5.5% above 200 (was 388 / 129 / 12.9% --
the full art includes the darker top, so it needs less toning), Toon World
397 / 101 / 5.2%, Vylon Element 397 / 137 / 6.9%. verify() passes.

## Framing, final: fit the art to the VISIBLE bounding box

User: "Toon World and Vylon element still seem to be cropped?" -- after the crop
had already been removed. They were right, and the cause was placement, not
cropping.

- The 64x64 sources are **complete, not cropped** (checked by eye for all three),
  so nothing is lost upstream.
- **Only about half the 256x192 canvas is ever on screen.** The opaque region is
  **x 40..215, y 16..175**, split into two bands (**y 16..87** and **y 104..175**)
  by a 16-row dead strip -- the gap between the DS's two screens.
- Stretching art across the FULL canvas therefore throws the picture's centre
  into the dead strip and its left/right edges off-screen. Pyramid of Light
  survived that because its subject is a full-width triangle; Toon World's book
  and Vylon Element's orb are centred subjects, so they read as cropped.
- **Fix: fit the art to the opaque bounding box (176x160).** Loses nothing but
  the screen gap, distorts only 1.1:1 from a 64x64 source, and matches what the
  stock backgrounds do -- ONE continuous scene across both screens.
  Geometry is measured from the transparent mask, never hardcoded.
- Rejected alternative: fit the whole art into EACH band (176x72). It shows the
  complete picture on both screens but squashes 2.44:1, and no stock background
  repeats itself that way.

Rebuilt: Pyramid 379 tiles / mean 118, Toon World 397 / 95, Vylon Element
397 / 137. 65 -> 68 files, field.pac 1308160 -> 1364480 bytes. verify() passes.

## SHIPPED into the chain (2026-09-07, user: "Cool ship that patch :)")

- `apply_all_patches`: **54 steps** (was 53). New step
  `PatchStep("Field backgrounds for converted Field Spells")` at index **45**,
  directly BELOW "Bulk Card Changes" (index 44) -- that ordering is
  LOAD-BEARING, since Bulk Card Changes is what makes these cards Field Spells
  and a Field Spell with no background freezes on activation. WiFi timers
  remains last.
- `_verify_all_patches.SHIPPED`: `patch_field_backgrounds` added in the SAME
  edit (tool.register_the_phantom_in_the_same_edit / the chain-build lesson).
  45 modules in the sweep.
- KB: `carddata.field_spell_background_is_mandatory` added to
  otn_enhanced/docs/engine/card_data_files.yaml -- the loader, the abort, the whole field.pac
  format, and the three constraints on a new background. 444 facts, 406 PASS,
  0 FAIL.
- Old chain ROM moved to `rom_all_patches.PRE_FIELDBG.nds` BEFORE building, so
  a silent death cannot leave a plausible-looking stale artifact.

## What is and is NOT confirmed in game

**CONFIRMED by the user 2026-09-07:**
- Pyramid of Light lands in the FIELD ZONE (the card_intid bit-14 fix).
- Pyramid of Light ACTIVATES WITHOUT FREEZING (the background exists).
- The tile-budget fix removed the black/garbage band.

**NOT confirmed in game -- every one of these changed after the last duel:**
- The current framing (fit to the visible bounding box) for ALL THREE cards.
- The brightness restoration (mean 128 rather than 104).
- The lit bezel edges.
- **Toon World 0x12BE and Vylon Element 0x24B5 have NEVER been tested at all** --
  not the conversion, not the background, not their effects.

## The Gates of Dark World: donor background replaced (user request)

The Gates of Dark World's donor is **Colosseum - Cage of the Gladiator Beasts
0x1C8B**, which is itself a STOCK FIELD SPELL -- so it already had a background
(`duel_field_magic7307_p.lz5bg`, file index 40) and it still showed COLOSSEUM's
picture in a duel.

- `patch_card_art` already carries `CardArt(0x1C8B, 'gates', 'gates')`, so the
  donor's 64x64 artwork is swapped for Gates of Dark World's. Regenerating its
  background from card.pac therefore picks the new art up for free -- no new
  art pipeline needed.
- **ORDERING, now load-bearing and written into the code**: this step reads
  card.pac, so it MUST run after "Card art". In the chain that is 41 < 45, which
  was true by luck rather than design until now.
- `patch_field_backgrounds` gained a **replace-in-place** path: a configured cid
  already present in the archive is overwritten and KEEPS ITS NAME AND INDEX
  (nothing that looks a file up positionally moves), while genuinely new cards
  are still appended. Regenerating every configured card on every run is
  idempotent.
- `verify()` split accordingly: the untouched stock files must be byte-identical
  AND each deliberately-replaced one must actually differ, so a silent no-op
  that leaves the donor's background in place FAILS rather than passes.

Measured: Gates 0x1C8B -> scale 0.939, mean 117, 13.9% above 200 (exactly the
stock worst, which is where the solver maximises to), 397 tiles,
20980 -> 20097 bytes, replaced at index 40. verify(): 4 backgrounds present,
64 untouched stock files byte-identical, index 40 confirmed replaced.

⚠️ The chain build started earlier was STOPPED and restarted after this change --
it predated it and would have shipped an already-stale ROM.

## Chain build: DONE and asserted (2026-09-07)

    BUILD_EXIT=0, log ends "ALL 54 PATCHES APPLIED", 54/54 step markers
    rom_all_patches.nds  129593992 bytes
    sha256 6e803b4b57b16b1fb8e13a9d56f397b5055c26d4ab3898e1970aa62d6cf34c71
    allocation guard: 188 ov5 slots (171 live), no overlaps, ledger in sync

Content asserted on the BUILT ROM, not inferred from exit status:
- field.pac holds **68 files**; Pyramid@65, Toon World@66, Vylon Element@67,
  Gates (donor Colosseum)@40.
- card_prop + card_intid: 0x17BF / 0x12BE / 0x24B5 all read
  `Spell Card / Field` with intid **bit 14 set**.

⚠️ A stale `rom_all_patches.nds` was present when the build started -- left by
the earlier build I killed mid-flight. It was harmless: step 1 reads from
`data/over_the_nexus/backup/eu_apfix.nds`, so the chain overwrote it from the
clean base rather than building on it. Checked in the log, not assumed.

`_verify_all_patches.py`: **PASS 43, FAIL 0, SKIP 2** (patch_boggart_knight and
patch_darksoul have no verify() of their own) across the 45 shipped modules.
patch_field_backgrounds passes all 7 of its own checks inside the sweep.

## Open Questions

- **The field.pac name-entry second byte** (see above). Blocks adding a 65th
  name. Next probe: disassemble the archive's name-table walker rather than
  guessing -- the open-by-name entry point is `0x020168E8` (Thumb; it parses the
  path at `0x0201686C`, then `strcmp`s at `0x0201691A`); follow it to the code
  that steps entries and see whether it reads offset +1 at all.
- Source art for the background. 256x192, gaps in (248,0,248). Not something
  this session can fetch.
- PoL's printed Continuous-Trap effect ("if removed from your side of the field,
  destroy Andro Sphinx and Sphinx Teleia and banish them") is unimplemented in
  the cls tables; where it lives, and whether it still fires from the field
  zone, is unexamined.

## Status

- Zone placement: **FIXED and IN-GAME CONFIRMED by the user 2026-09-07** -- the
  card now goes to the field zone.
- Freeze: **diagnosed, not yet fixed.** Cause is the missing background asset.
- lz5bg encoder: **fixed and tested** (lossless round trip).
- field.pac insert: **blocked** on the name-entry byte + source art.

## Next Experiment

Disassemble the name-table walker reached from `0x020168E8` and determine
whether the per-entry byte at offset +1 is read. If it is ignored, a 65th entry
can be written with any plausible value and the remaining work is purely the
archive relayout (5th name chunk, table chunks to 0xA00/0xC00, data base moved,
every rel_addr recomputed) plus encoding the art.
