# CPU / story deck name findings

Session start: 2026-09-17. See plan: modify CPU/story/tag/turbo deck names,
arbitrary length. Reference: `notes/booster-pack-unlock-findings.md:269-276`
(duelist-name mechanism, deck-name table flagged "not yet mapped").

## Confirmed

- **Deck-name strings live in `Data_arc_pac/bin2.pac` → inner file
  `game_text_e.bin`** (PAC v1, `otn_enhanced/rom/pac.py.py`), paired with offset
  table `game_indx_e.bin`. Verified this session against a **fresh** extract
  of the current `data/over_the_nexus/working/rom.nds`:
  - `bin2.pac` size 10,974,720 B, 99 inner files.
  - `game_indx_e.bin` at PAC-internal offset `0x8f2a00`, size 32548 B (index 71).
  - `game_text_e.bin` at PAC-internal offset `0x912a00`, size 166228 B (index 75).
  - Extraction script:
    ```python
    import ndspy.rom
    from otn_enhanced.rom.pac import parse_pac
    rom = ndspy.rom.NintendoDSRom.fromFile('data/over_the_nexus/working/rom.nds')
    bin2 = rom.files[rom.filenames['Data_arc_pac/bin2.pac']]
    archive = parse_pac(bin2, 'bin2.pac')
    # archive.files[i].address / .size for game_text_e.bin / game_indx_e.bin
    ```
- **⚠️ `scratch/bin2/game_text_e.bin` (166272 B) is STALE** — 44 bytes larger
  than the current live copy (166228 B) and every string offset inside it is
  shifted +28 bytes vs. the current ROM (e.g. "Dingy Daredevil" is at `0x7150`
  in the stale scratch copy but `0x7134` in a fresh extract). **Do not use the
  scratch copy for offsets — always re-extract.** (Likely stale from an
  earlier `card_desc_e_modified.bin` experiment in that same directory that
  resized something upstream in `bin2.pac`, shifting later inner-file
  contents — not confirmed, not important to chase further.)
- **Format** (matches the already-documented duelist-name mechanism):
  null-terminated ASCII strings packed back-to-back in `game_text_e.bin`,
  each padded to the next 4-byte boundary; `game_indx_e.bin` is a flat
  `u32[]`, entry `i` at byte `i*4` = byte offset of string `i` in
  `game_text_e.bin`. Confirmed by hand-walking the first 7 CPU-roster deck
  names and observing every gap round up to a 4-byte boundary.
- **Two deck-name string blocks located** (fresh-extract offsets):
  - `0x6c28` onward: **story-roster** deck names — "Supplied Deck" (`0x6c28`),
    "My Almighty Legend" (`0x6c38`), "Pretty & Prettier", "Wasteland Blokes",
    "Gotham World", "Angel's Bitter Dart", "Bone Destroyer", "Rotten
    Recycler", "My Eyes are Clear", "Electrikiss", "Thanks, Scrap", "Silent
    Swordsman", …
  - `0x7134` onward: **CPU-duel-roster** (ids `0x71-0xAC`, 60 total per
    `notes/cpu-duelist-unlock-findings.md:31`) deck names — "Dingy Daredevil"
    (`0x7134`), "Tomato Alliance" (`0x7144`), "Hip Hypnocorn" (`0x7154`),
    "Organic Cherries", "Watt's Up?", "Ehren There", "Hunk of Junk",
    "Steelswarm Space", "Dragon-Riding Beasts", "X-Soul Successor",
    "Blackwing Elite", "Gladiator Gradation", …
- Each language has its own `game_indx_*.bin`/`game_text_*.bin` pair
  (`_e/_f/_g/_i/_j/_k/_r/_s`) — editing `_e` only does not disturb other
  languages' offset tables.

- **`DECK_NAME_TABLE = 0x020AA5D8`** (arm9 VA) — a `u16[]`, one entry per
  duelist id, same id space as `DUELIST_NAME_TABLE`. `deck_name(id) =
  game_text_e[ game_indx_e.u32[ arm9.u16[ 0x020AA5D8 + id*2 ] ] ]`. Now
  **VERIFIED** in the KB: `otn_enhanced/docs/engine/deck_names.yaml` /
  `deck_names.table_base` (proof re-derives ids `0x71-0x75` and asserts the
  table's end-of-array boundary). Regenerate/re-run with
  `.venv-1/Scripts/python.exe -m otn_enhanced.knowledge.author_facts --check`
  (474 PASS / 0 FAIL as of this session).
- **Found by**: searching `arm9.bin` for the u16 LE encoding of text-id 2325
  ("Dingy Daredevil"'s text-id) on an even (u16-aligned) offset. Exactly one
  hit, at file offset `0xAA6BA`, with the next 4 u16s incrementing
  (2325,2326,2327,2328,2329) — matching "Dingy Daredevil", "Tomato Alliance",
  "Hip Hypnocorn", "Organic Cherries", "Watt's Up?" (the known first 5 of the
  first-6 CPU-duel opponents, `notes/booster-pack-unlock-findings.md:229`).
  `0xAA6BA` is entry `id=0x71` of the table; table base = `0xAA6BA - 0x71*2
  = 0xAA5D8` (file offset) = VA `0x020AA5D8`.
- **The table is much bigger than just the CPU-duel roster.** Dumped ids
  `0x00-0xFC` — every single one resolves to a plausible ASCII deck name (see
  raw dump in this session's transcript if needed; not reproduced here in
  full). Notable landmarks: id `0x55` = "My Almighty Legend" (a boss-sounding
  name, story roster), ids `0x71-0xAC` = the 60-strong CPU-duel roster
  (`notes/cpu-duelist-unlock-findings.md:31`), ids beyond `0xAC` through
  `~0xFC` continue with more unique names ("Aile Be Back", "Dragon Dash",
  "Runway Train", "Mach Quacker", "Wave Runner", "Shark Attack" — Turbo-Duel
  /WRGP-flavoured), i.e. **plausibly the whole single-duel-context deck-name
  space across story + CPU-duel + Turbo-Duel rosters is ONE flat table**, not
  three separate ones.
- **Table end confirmed exactly**: id `0xFD` is the last table entry (text-id
  0, an empty/invalid slot — likely "no deck name" / unused). Ids `0xFE`/
  `0xFF` both resolve to text-id 51 = `"You"`, and reading further (id
  `0x100` onward) decodes cleanly into real DUELIST NAMES ("Lenny", "Tetsu
  Trudge", "Bolt Tanner", "Yusei Fudo", "Jack Atlas", …) — i.e. past id
  `0xFD` this is no longer the deck-name table at all, it's
  `DUELIST_NAME_TABLE` itself, entered 4 bytes into its own start. Confirmed
  algebraically: `0x020AA5D8 + 0xFE*2 == 0x020AA7D4` exactly (`DECK_NAME_TABLE`
  is immediately followed by `DUELIST_NAME_TABLE`, zero gap, zero unrelated
  data between them) — so `DECK_NAME_TABLE` holds **exactly 254 entries**
  (ids `0x00-0xFD`).

## Ruled Out

- A separate deck-name table per game mode (story / CPU-duel / Turbo-Duel) —
  the evidence above points to one flat table covering all of them by id.
  **Not fully confirmed** — see Open Questions below (tag/tag-turbo still
  unchecked).

- **Native resolver function found: `0x020181A0`** (arm9, Thumb). Confirmed by
  raw halfword scan for the exact `LDR r0,[PC,#imm]` targeting the
  `DECK_NAME_TABLE` pool literal (capstone's window-disassembly missed it —
  always confirm a literal-pool xref by computing the exact PC-relative
  target, don't trust a nearby-looking `ldr ... [pc, ...]` in a disasm
  listing). The function takes one param in `r0` and branches four ways:
  - `r0 <= 1`: special-cased (the player, "You") — calls `0x0202F99C`, unrelated to `DECK_NAME_TABLE`.
  - `r0 >= 0x11E` (286): a *different* table, `u32[]` at `0x0209B724`, indexed `(r0-286)*4`.
  - `r0` in `[0x117, 0x11A]` (four ids just below the 286 cutoff): hardcoded
    text-id 2502 ("Prove Your Skill!") for all four — a shared generic name, not per-id.
  - otherwise (our path): `table_index = r0 - 1`; `text_id =
    DECK_NAME_TABLE_u16[table_index]`.
  ⚠️ **This function's own `r0` is NOT the same value as `duelist_id`** — it
  is offset by some caller-side convention (empirically, reading
  `DECK_NAME_TABLE[0x71]` directly — i.e. NOT subtracting 1 — reproduces
  Moja's correct deck name, so whatever calls this native function passes
  `duelist_id + 1`, or "duelist_id" in its own numbering already differs by
  one from the `DUELIST_NAME_TABLE` id space). This is a caller-side
  bookkeeping detail; it does **not** affect the writer, which indexes
  `DECK_NAME_TABLE` directly by the *known* duelist id and has been
  proven correct against ground truth (KB proof `deck_names.table_base`,
  ids `0x71-0x75`).
- **Writer built and mechanically round-tripped**: `otn_enhanced/system/deck_names.py`
  (moved here from `otn_enhanced/system/deck_names.py.py` 2026-09-17 so it can be
  wired into `steps.STEPS` like every other patch module)
  (`deck_name()` reader, `set_deck_names()` writer, both code paths — in-place
  for a same-or-shorter name, append-and-repoint for a longer one — exercised
  in the same test). Test: renamed id `0x71` ("Dingy Daredevil" -> "Short",
  in-place) and id `0x72` ("Tomato Alliance" -> "A Much Longer Deck Name Than
  Tomato Alliance", append path), rebuilt, re-read both back correctly, and
  confirmed neighbouring ids `0x73`/`0x55` were untouched. Bonus: `bin2.pac`'s
  existing inter-file padding absorbed the 48-byte growth from the append, so
  the archive's total size didn't even change in this test. This is a
  **mechanical round-trip only** — no melonDS confirmation yet, per
  `CLAUDE.md` nothing here is "working" until the user loads a real ROM and
  confirms in-game.

## Open Questions

- **Tag and tag-turbo duels**: do they reuse an existing single-duelist id's
  deck name (one or both of the paired duelists), or does the flat table's
  id range `0x00-0xFD` already include distinct entries for specific tag
  pairings? Static reasoning stalls here — this needs either (a) tracing the
  ov3 duel-setup code that decides which id is looked up when a tag/turbo/
  tag-turbo match starts, or (b) a savestate from an actual tag/turbo duel
  (per `CLAUDE.md`'s savestate-over-prose preference) to read back which
  `DECK_NAME_TABLE` id gets used for each of the two CPU decks in that match.
- Exact byte-length budget of each existing name (needed to decide in-place
  vs. append-and-repoint per rename) — computed per-id at edit time, not
  precomputed here.
- Writer not yet built (Phase 2 of the plan).

## Next Experiment

Pick one specific CPU deck to rename first (single-duel, since that mode is
now fully resolved) and build the minimal `set_deck_name(rom, duelist_id,
new_name)` writer per the plan's append-and-repoint design, output to a new
ROM, and have the user confirm in melonDS before generalizing to tag/turbo.
In parallel or after, resolve the tag/turbo open question — ov3 static trace
first, savestate as fallback.
