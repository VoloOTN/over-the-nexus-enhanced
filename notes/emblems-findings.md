# Emblem unlock conditions — findings (EU BYYP)

## Confirmed
- The user's AR code (0x0212422A..0x02124230) is a **US** address. The US save/global struct base literal is 0x02124150 and EU's is 0x0212406C
  (the same literal shows up at the same call sites in both, so the shift is +0xE4). AR range = struct+0xDA..+0xE0 -> EU 0x02124146..0x0212414C.
- Emblem bits = struct **+0xDD (row 1), +0xDE (row 2), +0xDF (row 3), +0xE0 (row 4)**, one byte per row, bit n = column n+1.
  Proof: ov1 0x02146088 does `ldrb [base,#0xe0]; orr #2; strb` (row 4 col 2 = Blackbird) and `#0xdf |= 0x10 / 0x40`, then calls 0x0202FEAC (notify).
  EU savestate rom.ml1: +0xDD..+0xE0 = 87 06 30 08.
- ov1 0x02146088 = emblem-check function (field/story overlay).

## Open Questions
- What +0xDA..+0xDC hold (the AR code also writes them).

## Confirmed (cont.) — award sites, all 32 located (EU, static disassembly 2026-10-09)
Every award = `byte[0x0212406C+0xDD+idx/8] |= 1<<(idx%8)` then notify `0x0202FEAC(0x13E+idx)` (Thumb).
ov18 0x02153DA8 draws the grid from bitfield 0x02124149 (32 bits). NB arm9 is BLZ-compressed: scan via ndspy.code.MainCodeFile.
| idx | id | site |
| 0 | 13E | ov31 0x02164BF8 (event id ==0x27E0) |
| 1 | 13F | ov3 0x0214416C ([base+0x29A2] >=20) |
| 2,3 | 140,141 | ov3 0x02144128 ([stats+0xA6] >=100 / >=300) |
| 4 | 142 | arm9 0x02015DBC (pred 0x02015CC8) |
| 5,6 | 143,144 | ov18 0x0214D73C / 0x0214D760 (preds 0x0215B6B4 / 0x0215B798) |
| 7,8 | 145,146 | arm9 0x0202DB80 / 0x0202DC8A ([base+4]/216000 >=100 / >=300 h, + gate 0x0202FBE8()==0x3FF) |
| 9,10 | 147,148 | arm9 0x0202DDEC / 0x0202DE64 (card-list % >=70 / >=100) |
| 11,12 | 149,14A | ov3 0x02181FD4 (duel-bonus ratio >=0.7 / all) |
| 13-15 | 14B-14D | ov3 0x02144588 ([stats+0xCE] >=50/150/300) |
| 16,17 | 14E,14F | ov3 0x02183114 (byte counter base+0xDC >=5 / >=10) |
| 18 | 150 | ov31 0x02164C3C (0x0201B36C(0x2E) >= 22) |
| 19,20,22,25 | 151,152,154,157 | ov1 0x02146088 |
| 21 | 153 | ov38 0x0214E620 (17 shop items) |
| 23,24,31 | 155,156,15D | ov34 0x02160BC0 (preds 0x0215D50C/51C/52C) |
| 26 | 158 | ov42 0x0215EF74 (counter base+0x28B0 hits 100) |
| 27 | 159 | ov7 0x021509A8 ([r4+0x9CC] < 120) |
| 28 | 15A | ov6 0x02197770 (counter >=20) |
| 29 | 15B | ov6 0x02198E34 |
| 30 | 15C | ov3 0x02144198 (bitmask base+0x280C full) |

## Confirmed (cont.) — predicate details (static disassembly 2026-10-09)
- stats block r5 = 0x0212426C = base+0x200 in ov3 0x02143A34 (duel-end bookkeeping). Wins = u16 base+0x2A6, Wi-Fi duels = u16 base+0x2CE.
- DMG: sl=1 (0x02143A3C) -> mask base+0x280C must equal 0x7FFF (15 Structure Decks); bit index = [0x020B7C8C+0xBC4].
- Per-duelist byte table: base+0x2EC+4*id (nonzero = cleared). Average Duel Disk = ids 2..0x70 (skip 0x48,0x6F) + 0x13A..0x14C.
  Championship Cup = ids 0x71..0xAC, 0xD5..0xE8, 0x11C..0x139. Typical Duel Disk = bitset base+0x2818 bits 0x71..0xAC, 0xD5..0xE8 + bitset base+0x2848 bits 0..29.
- Riding records: 3 difficulty blocks base+0x271C/0x276C/0x27BC. Time race = byte +0xC+16*course (4 courses) ==1; Battle race = +0xD+16*course; Highway = +0x4D ==1 (0x0215D44C).
- Blackbird: 7 runner-part categories, sizes {17,8,8,15,13,13,16} (ov1 0x0214B070), bitsets base+0x38+4*cat all set (cats 0-2 skip part 0).
- Duel time = u32 base+4 in frames (/60/60/60). 100 h / 300 h emblem gated by 0x0202FBE8(3 bytes from 0x02126C6C/0x02126C8C) == 0x3FF (meaning UNVERIFIED).
- EU equivalent of the user's AR code (UNTESTED, AWAITING IN-GAME TEST): 94000130 FCFF0000 / 22124149 000000FF / 1212414A 0000FFFF / 2212414C 000000FF / D2000000 00000000

## Open Questions
- What [0x0229DC94+0xD0]==1 means for the Simple/Prestigious counter (+0xDC). User (2026-10-09): these medals measure Wi-Fi rank; code thresholds are +0xDC >=5 / >=10.
- 0x0202FBE8==0x3FF duel-time gate: user not interested, left alone.

## Confirmed (cont.) — +0xD8..+0xDB are NOT emblems (2026-10-09)
- ARM strb/ldrb scan over all overlays: +0xD9/+0xDA are only ever written 0, together with +0xD8, in ov6 0x021A59BC / 0x021A6F9C / 0x021A73B8
  (Wi-Fi penalty/reset paths: [base+0x28] -= 0x63, u16 [base+0xD6] -= 1). +0xD8 is read in ov3 0x02180EDC, ov15 0x021508DC, ov18 0x021527CC.
  +0xDB: no ARM-mode access found. The emblem grid reads only 0x02124149..0x0212414C. The US AR code's writes to +0xDA..+0xDC are side effects.

## Patch: patch_wifi_emblems.py (built 2026-10-09, AWAITING IN-GAME TEST)
- User chose per-row piggyback. ov3 0x02182028 orr #0x10->#0xF0 (Thrifty Goblin -> +Bronze/Silver/Gold);
  ov1 0x0214625C orr #0x08->#0x0B (Treasure Chest -> +Simple/Prestigious); ov3 0x021441C0 orr #0x40->#0x70 (DMG -> +Guard Robot/?).
- Words are stock in both rom.nds and rom_all_patches.nds; no shipped patch references them. Single-card ROM rom_wifi_emblems.nds
  sha256 ef2d3b874723422b6d7d39819c124ed072e2b82ace03a2d8cb1b02bbc7770132. NOT in steps.STEPS.
- Caveat: Treasure Chest site skips if its own bit is already set (ov1 0x021461F8), so an existing save with Treasure Chest won't get row-3 medals.

## Shipped 2026-10-12 (user: "Ship it. In the vanilla+ section") — still AWAITING IN-GAME TEST
- steps.STEPS step 5/108, right after "Banlist menu ... No Banlist" (vanilla+ block 1); added to _verify_all_patches.SHIPPED.
- Full build 108/108 sha256 4d174b3eeb85db9d3e80126d4c6abbf083932262297800198f526f9eeecbfbc5; sweep 89 passed / 0 failed.
- Vanilla+ build 40/108 sha256 c4c31fcfab487c2a8a361cd5ff3263f328b5e79ae2dc9c567151fa45b54678fa; patch_wifi_emblems.verify PASS
  (the full sweep is not meaningful on the vanilla+ ROM: it checks block-2 cards too).
