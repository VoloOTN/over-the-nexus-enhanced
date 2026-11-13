# Card stats, name, description, genre and archetype

## Goal

Make the card look like the new card: ATK/DEF/Level/Type/Attribute, name, description, deck-editor search tags
and archetype membership.

## Before you start

A card's data is spread over several files inside `bin2.pac`. All are keyed by the **cid**, or by the card's
record index in `card_prop.bin`.

| What | File (inside `bin2.pac`) | Format |
|---|---|---|
| ATK, DEF, Level, Attribute, Type, Race | `card_prop.bin` | 8-byte bitfield per card, low 14 bits = cid |
| Name | `card_name_<L>.bin` | NUL-terminated strings |
| Description | `card_desc_<L>.bin` | NUL-terminated strings |
| Name/description offsets | `card_indx_<L>.bin` | `[name_off u32][desc_off u32]` per card |
| Is a summonable monster | `card_intid.bin` | u16 per card, indexed by `cid - 0xD48`; bit 15 = summonable |
| Deck-editor search filters | `card_genre.bin` | bitmap per card |
| Pack and rarity | `card_pack.bin` | 8 bytes per card |

Language suffixes: `e f g i s j k r`. `r` is **Japanese with ruby markup, not Russian**; `k` is Korean.

Text must come from `scratch/ygoprodeck_cache.json`. The ROM's own English descriptions are mistranslated and are
not a source.

## Steps

### 1. Stats (card_prop)

Do not hand-roll the bits. Use the codec:

```python
from otn_enhanced.rom.game_constants import DEFAULT_CONSTANTS as GC
fields = GC.decode_entry(record8)
fields["attribute_encoded"] = GC.attribute_reverse["WIND"]
fields["race"] = "Beast-Warrior"
fields["level"] = 4
fields["atk_encoded"] = 1700 // GC.layout.atk_divisor
record8 = GC.encode_entry(fields)
```

Layout (ERA2): cid `[0:14]`, ATK÷10 `[14:23]`, DEF÷10 `[23:32]`, type `[32:38]`, attribute `[38:41]`,
level `[42:46]`, race `[49:54]`.

### 2. One call for stats and text

`data/card_stats.apply_stats_and_text` finds the record by cid, rewrites the stats (a same-size edit) and, when
`write_text` is true, the name and description:

```python
from otn_enhanced.data.card_stats import apply_stats_and_text
apply_stats_and_text(out, cid=DONOR_CID, attribute="LIGHT", race="Spellcaster", level=1, atk=0, defense=0,
                     card_type=ERA2_CARD_TYPE_REVERSE["Effect Monster"],
                     name=b"Mystic Piper", desc=b"...", langs="efgisjkr", write_text=write_text)
```

For a cid that is in `data/card_text.CARD_TEXT` the full printed text is written by `card_text.apply_to_rom`
and the `name`/`desc` arguments only satisfy the legacy fallback.

### 3. Printed text: `data/card_text.py`

`CARD_TEXT[cid]` holds `{lang: (name, description) | bytes | None}`. `None` means use English. Add the English
text verbatim and fill other languages when you have them.

The module re-emits the **whole** name and description blobs in index order, so text is not limited by the
donor's slot length. Rules it enforces:

- **Never append a string past the end of a blob.** The deck editor reads a description's length from the gap to
  the *next* index entry; an appended string makes that gap negative and hard-freezes the console.
- A name or description written the old in-place way must fit the donor's slot; skip a language rather than
  growing it.

Assert text in `verify()` with `card_text.check_rom_text(rom, cid, langs)`. It compares against the same source
the writer uses, so it cannot drift. Do not assert against a local constant: five modules once did, and the
sweep reported them failing for months while the ROM was correct.

### 4. Trap or Spell becoming a monster (or the reverse)

Three edits are needed, not one:

1. `card_prop` card type = Effect Monster.
2. `card_genre.bin`: clear the Spell/Trap flag bits.
3. `card_intid.bin`: set bit 15 (summonable), otherwise ATK/DEF/Level render blank and there is no Normal
   Summon option.

`data/bulk_card_props.py` converts cards in bulk (and Field Spells; those also need a background, see
[art-tweaks](../art-tweaks/HOWTO.md)).

### 5. Deck-editor search tags

`data/card_genre.py` holds each re-donored card's tags. A donor keeps its own tags, so without an entry it shows
under the donor's filters. Add the cid and its tag value. The step is name-guarded: it writes a row only when the
ROM's English name for that cid already equals the new name, so it must run **after** the step that renames the
card. It runs at the end of Vanilla+, after the main card set, and again after the Monarch set. If you add cards in
a new step after those, add another `data.card_genre` step after them in `steps.py`, or their tags are silently
skipped.

### 6. Archetype membership

Archetypes are sorted u16 cid tables in ARM9, binary-searched, with the count baked into the code. They cannot be
relocated (no safe cave), so they are edited in place and count-neutral: drop a phantom cid, insert yours.
Look at the helpers in `effects/xsaber_table.py` and `effects/tg_table.py`
(`add_xsaber_member`, `add_tg_member`). Edit ARM9 only through `ndspy.code.MainCodeFile` (the
`effects.common.arm9_edit` context manager does this).

## Worked example

`cards/mystic_piper.py`: `NEW_ATTRIBUTE`, `NEW_RACE`, `NEW_LEVEL` and the call at the end of `main()` set the
stats; its text lives in `card_text.CARD_TEXT[0x13B8]`. Its `verify()` checks the overlay edits only; add a
`card_text.check_rom_text(...)` call if you want the text asserted too.

## Check it

- Open the built ROM in the deck editor: ATK/DEF/Level show and the description reads correctly in each
  language you filled.
- Search the card by the filters you set in `card_genre`.
- `check_rom_text` returns `(True, ...)` for every language.

## Pitfalls

- **Descriptions and names never grow.** Fixed-size buffers overflow into blank text and freezes.
- A name that is correct in `CARD_TEXT` but fails `check_rom_text` usually means a later step re-wrote the
  card. `text_guard.py` names the step that clobbers finished text the moment it happens during a build.
- "Cannot be Normal Summoned" (nomi) has no known data switch. Choose a donor that already has the summon type.
- The era wording is modern ("GY", "banishing"). Edit `CARD_TEXT` if era-accurate wording is wanted.
