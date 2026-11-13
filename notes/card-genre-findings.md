# card_genre (deck-editor search filter) — findings

Started 2026-10-09. Goal: give every re-donored card the right search-filter tags.
Nothing written to any ROM yet.

## Confirmed (this session)

- **Bit map** (keyword-lift census vs `scratch/ygoprodeck_cache.json`, `scratch/genre_census.py` +
  `scratch/genre_check2.py`): 0 Recover LP, 1 Reduce LP, 2 Draw, 3 Special Summon, 4 Cancel out
  Effect (negate 0.98 vs 0.07 base), 5 Search Deck, 6 Recover from GY, 7 ATK/DEF, 8 Change position
  (0.97), 9 Change control (1.00), 10 Destroy monster, 11 Destroy S/T, 12 Hand destruction, 13 Deck
  destruction, 14 Remove from play (banish 0.93), 15 Return (0.61 vs 0.03), 16 Pierce, 17 Direct, 18
  Multiple Attack, 19 Cannot be Destroyed, 20 Restrict Attack, 21 nomi, 22 Flip, 23 Toon, 24 Spirit,
  25 Union, 26 Gemini, 27 LV, 28 Speed Spell, 29 Fusion, 30 Token, 31 Counter, 32 Gamble (1.00), 33
  mentions-an-Attribute, 34 Type, 35 Tuner, 36 Synchro, 37 Graveyard-bound, 38 Normal Monster (0.99),
  39-44 LIGHT/DARK/EARTH/WATER/FIRE/WIND (keyword tags, 1.00 — NOT the card's own attribute).
- **3DS CARD_Genre.bin is the same bitfield**: no header, parallel to CARD_Prop (record 0 = dummy).
  3DS bit k == NDS bit k for k<30, 3DS bit k+1 == NDS bit k for 30..44 (>=3886/3918 agreement per
  bit). KB: `carddata.card_genre_bitmap_and_3ds_source` (VERIFIED, passes `--check`).
- NDS `card_indx_e` has no header: prop record i -> indx entry i+1 (first audit run was off by one).
- `scratch/genre_audit.py` (stock vs rom_all_patches): 85 renamed cards; 50 have a 3DS genre that
  differs from the ROM, 3 already match (Metal Armored Bug, Crimson Blader, Scrap Archfiend), 32 are
  not in the 3DS and need hand tags.

## Built 2026-10-09 — AWAITING IN-GAME TEST

- `finished_patches/patch_card_genre.py`: 47 3DS-sourced rows, NAME-GUARDED (writes a cid only when
  the ROM's English name already equals the new card's). User approved wiring it in; it is in
  steps.STEPS twice: before "Extra banlists" (inside vanilla+) and after "Field backgrounds --
  remaining". Added to `_verify_all_patches.SHIPPED`.
- vanilla+ build 968f5598... : audit shows only Orient / Hyper Librarian / Life Stream still differ
  (deliberately excluded). Full build 107/107, b79496b9...: 50 ok, same 3 excluded; EE verify sweep
  88 passed, 0 failed.

## Built 2026-10-09 (round 2) -- AWAITING IN-GAME TEST

- User approved the 32 hand tags (scratch/genre_hand_draft.py) and adding the 10 own-genre modules.
  patch_card_genre.GENRE now = 52 3DS rows + 32 hand rows = 84. No longer imports any patch module
  (orient imports it); exposes accepted(cid, own).
- 9 modules' verify() now use `in pcg.accepted(DONOR_CID, NEW_GENRE)` (accel_synchron, ASSD,
  hyper_librarian, junk_speeder, life_stream_dragon, orient_dragon, raiden, scrap_raptor, wattkyuki);
  jet_warrior's verify never checked genre. Their main() still write their own NEW_GENRE first.
- vanilla+ af10e71d...: 27/84 present, all correct. Full 107/107 62fc84a5...: 84/84 present and
  correct; EE verify sweep 88 passed, 0 failed.
- Caveat: those modules' main() assert the CURRENT genre is donor-or-NEW_GENRE, so re-applying one
  of them on top of an already-chained ROM would abort. Builds from stock are unaffected.

## Round 3 2026-11-13 -- user approved, in card_genre.GENRE (162 rows) -- AWAITING IN-GAME TEST

- Audit of __ee_session__.nds (2026-11-13) vs stock: 40 renamed cards still carry the donor genre
  (Infernobles, Dragon Rulers, Gearfried, Uni-Zombie, ...); 5 Synchros (Captain Roland, Angelica,
  Coral Dragon, Captain Oliver, Emperor Charles) carry only the module-written (nomi)+Synchro(+Tuner);
  30 Monarch-set cids have no GENRE row. 77 CARD_TEXT cids lack a row; Armory Arm / Vylon Element
  keep their stock names so stock tags stand -> 75 to draft.
- 3ds_extract/ is NOT on disk any more: all 75 are hand tags. Draft: scratch/genre_hand_draft2.py
  (conventions in its docstring). User approved; rows pasted into card_genre.GENRE (87 -> 162).
- Proof: card_genre.main on a copy of __ee_session__.nds -> 132/162 present and tagged (the 30
  Monarch cids are not renamed in that build, so the name guard skips them), verify() True, and the
  stock-vs-patched scan finds 0 renamed cards outside GENRE. No full build run.
- scratch/genre_audit.py imports ygo_tools.tools.pac (gone; use otn_enhanced.rom.pac) and needs the
  3DS extract; it cannot run as-is.

## Next Experiment

- After a write: open the deck editor, filter by e.g. "Search Deck" and confirm T.G. Striker shows.
