# Card pack (unobtainable-only) in vanilla+ — findings

## Confirmed (2026-10-09, by disassembly of rom.nds)
- Booster generator = overlay 10. `0x02155A68(this, out[5], i)` draws 5 cards; each pick is
  `pool[rand % count]` (`bl 0x02098BB0` uidivmod, remainder r1, e.g. @0x02155C00).
- `0x02155934` builds a pool from the pack list at this+0x88BC, filtering by rarity mask:
  jump table @0x021559A0, rarity 0/1 -> 1, 2 (UR) -> 8, 3 (SR) -> 4, 4 (R) -> 2. Returns the count.
  Pools at this+0x22C / this+0x4574 (4306 entries each).
- Pack list = arm9 Thumb `0x0202A608(pack, buf, 0x10D2)`, dynamic, zero-terminated; packs
  0x20..0x2A match on pack_2/rarity_2, the rest on pack_1/rarity_1 (0x0202A5C4 / 0x0202A540).
- => No fixed per-pack rare count exists. Adding rares only dilutes odds. The one hazard is a
  tier that had cards becoming empty (rand % 0).
- KB: `cardpack.generator_pools` (VERIFIED, arm9 anchors; ov10 claims are disassembly-only).

## Change
- `patch_bulk_card_pack.assert_rare_counts_preserved` now fails only if a non-empty tier is emptied
  (was: counts must be identical, which made "add an unobtainable card" impossible).
- `steps.VANILLA_PLUS_END` anchored on "Card Pack Changes (unobtainable cards only)".
- vanilla+ 38/105 sha256 03c294f6...0461: 25 rows changed, all previously pack 0; UR tiers grew
  (pack 56 4->10, 59 4->9, 1 15->20, 32 8->12, 9 4->6, 40/46/47 +1).
- full 105/105 sha256 50ec68a2...6586.
- 2026-10-09 later: the 85 CHANGES keys for donor rows were renamed to the hack's names (row from the clean
  ROM, name from rom_all_patches.nds; each line has a `# was <stock name>` comment). The full step dropped
  names_from. Both builds came out byte-identical (03c294f6... / 50ec68a2...).

## Open Questions
- Pack 56 new cards appearing in vanilla+ (sha 03c294f6...0461): in-game confirmed by user 2026-10-09. Pack 59 not reported.
