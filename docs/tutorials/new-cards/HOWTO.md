# Adding a card at a brand-new cid

## Goal

Add a card that does not consume a donor: it gets a new cid beyond the game's current maximum.

## Status

**Shelved.** This was proven on one card and then set aside; nothing in the build uses it. The reference
implementation is `cards/new_cid_reborn_tengu.py` (Reborn Tengu at Konami cid `0x25E3`) with
`cards/new_card_save.py`. It is **not** a step in `steps.py` and collides with the shipped `cards/reborn_tengu.py`
(same phantoms): shipping it would replace that card.

Prefer a donor ([donor-cards](../donor-cards/HOWTO.md)) unless you specifically need a card that adds to the
collection.

## Before you start

- Understand why donors exist: every per-card table is keyed by cid and sized for the stock set.
- Read the ceiling first: **two** new cards. An overlay-8 fixed buffer (`0x021FD1F0`) has only 2 spare bytes
  of padding. More needs that buffer moved and the save arrays expanded. The deck-editor trunk list (4306 slots)
  overflows above about 75 new cards on a ~100% collection.

## Recipe (from the proven card)

1. **ARM9:** raise the `cid_to_intid` upper-bound literal at `0x02029E44` (`0x24E9` to new max + 1). It is the
   only cid-range bound in code.
2. **ARM9:** add 1 to the global card count at `[0x0209D474]` (deck editor and lists) and to the pack-list loop
   literal at `0x0202A75C` (packs).
3. **`bin2.pac`:** append one record to **all 64** per-card files, re-emitting the blobs in index order
   (`card_text.rebuild_blobs` / `rebuild_sort`); grow `card_intid` to cover the cid (bit 15 = monster, plus the
   record index).
4. **`card.pac`:** append the thumbnail, its index entry and the 64×64 art tile.
5. **Leave the save accessors' `0x10D2` literals alone.** A record at index 4306 or above reads as "owned ×9"
   and writes nothing.
6. **Save storage:** `cards/new_card_save.py` keeps the count and flags in unused bits 6 and 7 of the flag
   bytes (128-card capacity) by rewriting the ARM9 accessors in place. Reusing Token slots was rejected because
   duel code can write them.

## Check it

- Deck editor lists the card; pack opening can award it; a normal duel, a puzzle and every leave route work.
- The save round-trips: add the card, save, reload, confirm the count.

## Pitfalls

- Only the card-data half was confirmed in-game on the original card. The save-storage layer
  (`new_card_save.py`) was emulator-proven and still needs an in-game test.
- A new cid needs its own effect rows too (phantom drops, caves). Register every claim.
- Do not wire it into `steps.py` without the owner's approval.
