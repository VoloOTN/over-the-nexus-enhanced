# Puzzle editor: rom_infernoble works, rom_all_patches does not

## Confirmed (2026-10-23, ndspy byte diff of the two ROMs)
- ARM9 (747384 B) and EVERY overlay are byte-identical. Header/overlay table identical. Not a code difference.
- Only 2 of 127 files differ: Data_arc_pac/card.pac and Data_arc_pac/deck.pac.
- card.pac: 18 thumb/64x64 art slots differ (card_prop idx -> cid): fc1 fd4 fdb fe6 feb 1002 1118 139a 13a3 15e3 160b 1663 17ef 1976 1c39 1e04 1e05 1f71. File1 shrinks 3144222 -> 3144102 (both < stock 3144957), so no size growth.
- deck.pac: ~33 opponent .ydc differ (ported decks; bulk_ydcs); most grew to 124 B.

## Open Questions
- Exact symptom of the puzzle-editor failure (not reported yet).
- Which of card.pac / deck.pac triggers it.

## Next Experiment
Load rom_bisect_card_from_infernoble.nds and rom_bisect_deck_from_infernoble.nds (all_patches with ONE file swapped back); whichever fixes the editor is the culprit.
