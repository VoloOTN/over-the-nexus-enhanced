# CPU candidate-row audit (2026-11-04)

Trigger: That Grass Looks Greener was drawn 60x and activated 0x because the donor Sparks' ov5 CPU row
{0x0003D0FD, evaluator 0x0231111D} points at the generic LP-effect evaluator 0x02311084, which returns 0 for any cid
without an LP-table entry (see notes/that-grass-looks-greener-findings.md, "ROOT CAUSE + FIX").
Row format (ov5 static data, 8 B): { id | loc<<14 | param<<18 , evaluator fn }; id word usually 0x3Dxxx / 0x7Dxxx / 0xBExxx.

## What was checked (all from STOCK rom.nds ov5 rows + the 2026-11-03 tournaments and 2026-11-04 gauntlets)
- 128 cids have patched text (card_text.CARD_TEXT). Only 27 of them have an ov5 CPU row (Spell/Trap donors; monster donors have none).
- The LP evaluator family (thunks 0x0231111D / 0x02311129 / 0x02311135) is used by Sparks ONLY among those 27. => Grass is the
  only patched card with that specific defect.

## Rows inherited by patched cards, with measured CPU play (drawn / summoned / activated, tournaments + gauntlets)
Played fine (activated > 0): Sekka's Light 0x10E6 14/0/8, Double Evolution Pill 0x1319 7/0/3, Noble Arms Museum 0x1346 6/0/6,
Dragon Shrine 0x14C1 5/0/2, Infernoble Joyeuse 0x15E3 2/0/4, Continuing Epic 0x16DB 1/0/1, Horn of Olifant 0x1976 6/0/5,
Shien's Dojo 0x19B2 1/0/4, Gates of Dark World 0x1C8B 8/0/8, Infernity Barrier 0x1DDD 4/0/1, Armory Arm 0x1F33, Sea Lancer
0x1FFC 22/8/4, Brilliant Fusion 0x21D5 9/0/13.
NOT YET TESTABLE (no tested deck draws them): 0x10F5 Seal of Orichalcos, 0x123D Soul Charge, 0x1255, 0x130A Sacred Sword,
0x1315, 0x16A2, 0x170F Ojamassimilation, 0x1777 Fire Formation - Tenki, 0x17F4 Obedience Schooled, 0x1B22 NEXT, 0x211B
Majestic Star Dragon, 0x2124 Amazoness Heirloom, 0x24B5 Vylon Element. Their evaluators: generic/shared for 0x10F5 (0x23140d5),
0x1255 (0x2310a39), 0x130A (0x2310c81), 0x1777 (0x2310a25), 0x1B22 (0x2310905), 0x2124 (0x2311331); donor-unique for 0x1315
(0x231b789), 0x16A2 (0x23220c5), 0x170F (0x2322879), 0x17F4 (0x2323d21), 0x123D (0x231a1fd), 0x211B (0x232bd89/0x2310cd1),
0x24B5 (0x2329969). A unique evaluator is NOT proof of a defect (Dragon Shrine's unique 0x231e6cd plays fine) -- they need a deck.

## Other suspects seen in the same stats (not CPU-row defects, unproven cause)
- Monsters never summoned although drawn: Grandsoil 0x1110 (22 drawn), Pyrorex 0x181F (19), Moulinglacia 0x1C1A (10),
  Ceruli 0x1B3E (9). These have no ov5 row; their summon conditions may simply be unmet in those decks. UNVERIFIED.
- ~50 patched cids were never drawn in any run at all.

## Next
- Build a test deck (or gauntlet-able deck) per not-yet-testable Spell above and read card_stats.csv; fix any with the same
  one-word row change (target evaluator 0x023107C1 `movs r0,#1; bx lr`, shared by 145 stock rows).

## Result of the 12-card screen (2026-11-04, scratch/test_deck_gauntlet.py, 60 duels, fixed rig, 24 Spells + 16 Lightsworn fodder)
drawn / activated: Seal of Orichalcos 33/33, Fire Formation - Tenki 30/30, Ninjitsu Art of Super-Transformation 33/28 -> CPU plays them.
Soul Charge 33/1, W Nebula Meteorite 27/2 -> rarely.
0 activations: Sacred Sword of Seven Stars 29, Safe Zone 31, Ojamassimilation 33, Obedience Schooled 30, NEXT 36,
Amazoness Heirloom 29, Vylon Element 27.
CAVEAT: the deck had no setup (no Amazoness / Vylon / Ojama / Spirit / Neos targets), so a zero is NOT yet a defect.
Next: per-card mirror decks (card x3 + its targets + filler vs a copy of itself) for the 9 low/zero cards.

## Mirror-deck results (2026-11-04, otn_enhanced/tools/cpu_battery/cardtest.py mirror, combined ROM with the Grass row fix; emulator CPU, NOT user-confirmed)
16 duels each, card x3 + kit vs an identical copy, both seats summed. drawn / summoned / activated:
Soul Charge 22/0/3 (plays, rarely) | Safe Zone 27/0/0 (ZERO with 196 kit summons -> candidate defect) |
W Nebula Meteorite 27/0/1 | Sacred Sword of Seven Stars 23/0/9 (earlier 0/29 was a missing-L7 setup) |
Ojamassimilation 29/0/34 (works; earlier 0/33 was a missing-setup zero) | Obedience Schooled 24/0/0 (needs NO monsters; the
kit kept the board non-empty -> not yet a defect) | NEXT, Amazoness Heirloom, Vylon Element: still running.
Cardcar D 0x0FAE: Lightsworn-filler deck 29/1/0; spells+traps-only deck (the only monster in the deck, 8 duels) 45/21/0 -> the CPU
Normal Summons it 21 times and NEVER uses the Tribute-to-draw effect. Comparable shipped monster effects the CPU DOES use
(tournament/gauntlet stats, drawn/summoned/activated): Raiden 75/52/27, Tour Guide 27/22/12, Wattuna 16/13/4, Sakitama 5/4/2,
Aratama 4/2/11. Cardcar D is the odd one out (no ov5 CPU row exists for monster cids). Cause unknown.
Bug fixed on the way: the 40-card filler loop in cardtest looped forever on a small kit (cap 3 per card); the cap now rises.
Vanilla-monster Cardcar D deck (13 vanilla x3): 2 of the first 3 duels HUNG at 900 s -- being re-run with a 240 s timeout.

## Cardcar D vanilla-monster deck: HANGS (2026-11-04, cardtest mirror 0x0FAE, 8 duels, 240 s timeout, own work folder)
Deck = Cardcar D x3 + Alligator's Sword, Alpha The Magnet Warrior, Amazon of the Seas, Archfiend Marmot of Nefariousness,
Armored Zombie, Baby Dragon, Battle Warrior, Big Insect, Blackland Fire Dragon, Blade Skater, Celtic Guardian, Chamberlain of
the Six Samurai, Cloudian - Smoke Ball (x3 each), mirrored. 7 of 8 duels hung (duels 4,0,1,5,2,7,3); 1 finished (Cardcar D
drawn 1, summoned 0). An earlier run of the same deck hung 2 of its first 3 duels at the 900 s timeout. The spells+traps-only
Cardcar D deck (same load) had 0 hangs in 8 duels. Machine was heavily loaded (other cardtest runs), so NOT conclusive.
Suspects: Cardcar D used often (effect ends the turn) or one of the 13 vanilla monsters. Next: bisect the kit on a quiet machine.
NOTE: results CSV is per card id; the later run overwrote build/cpu_battery/cardtest/mirror_0x0fae.csv (the 45/21/0 numbers
for the spells+traps deck are recorded above).
