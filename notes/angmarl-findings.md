# Angmarl the Fiendish Monarch (0x14D8, donor The Dragon Dwelling in the Cave) -- live findings (2026-11-11)

Text: "When this card is Tribute Summoned: You can banish 1 Spell Card from your Graveyard; add 1 card with the same name as the banished Spell Card from your Deck to your hand."  Lv6 DARK Fiend 2400/1000.
Clauses: C1 trigger on its own Tribute Summon; C2 optional: banish 1 Spell Card from your GY (cost); C3 add 1 same-name card from the Deck to the hand.
Donor: The Dragon Dwelling in the Cave 0x14D8 (Normal, 1300/2000; donor_scan CLEAN, only arm9 code-region hits; not in any ROM deck; unclaimed). NOTE: chosen by me from the donor criteria; the user said "implement angmarl next" but did not name or approve this donor.

## Built (cards/angmarl.py + cards/c/angmarl.c, installed by cards/mega_monarch.py)
- TRIG front list = MEGAS + Angmarl; cls1 phantom 0x0E7E; cls1 {0x14D8, 0, RES, 0, COND, 0x021E51E5 (native "You can"), COST}; virtual rows 0xFF90 (GY handler 0x0223CA11, word 0x4 = Spell) / 0xFF91 (Deck handler + same-name predicate, word 0xE); H2/H3 fronts ahead of the Mega chain; slots CAVE_AG_* (CAVE_FREE 0x023B0C08); TRIG slot widened to 0x60.
- Combined ROM data/over_the_nexus/working/rom_monarch_all.nds sha256 c97630c4fb151b1684440952e21779f4cff6c1aa067dddb94955e1b238360320 (previous: rom_monarch_all_prev.nds). Built by scratch/_monarch_session.py (139 s). Static verify: mega_monarch 95/98, the 3 failures are expected composition fronts (M0 -> Restoration's front, H2/H3 -> Tenacity's).

## Confirmed by CPU trace (emulator, NOT user-confirmed) -- scratch/angmarl_gdb.py, build/cpu_battery/gdb_ag2/rs_2.json (seed 2)
- Mirror (10 duels, Dark Hole x3 + MST x3 + Heavy Storm x2 + Summoned Skull x3 + Dark Magician x3): drawn 11 / summoned 7 / activated 7.
- Trace: COND with Dark Hole 0x10F6 in the GY -> COST x3 (cost step 0 -> 1 -> 2) -> at RES phase 0x80 the GY LOST 0x10F6 and the banished list GAINED it (exactly 1 banished) -> RES stored DATA = 0x10F6 -> the Deck predicate ran over the Deck (card cids logged) with DATA 0x10F6 -> phases 0x7E / 0x7D (the native Deck picker) -> phase 0x64 the HAND GAINED a second 0x10F6. So the native banish cost, the virtual GY row, the cid capture, the virtual Deck row and the same-name predicate all worked together once.
- NOT SHOWN: a Spell with no copy left in the Deck (the printed text still banishes), the human picker / cancel of the "You can" prompt and of the banish picker, a Spell in the GY that is a Trap-like Continuous Spell, the case of 2+ Spells in the GY (CPU picked 0x10F6), the opponent-side use.

## In-game steps for the user
1. Tribute Summon Angmarl (Level 6, one Tribute) with at least one Spell Card in your GY and a copy of it in your Deck. 2. A Yes/No prompt, then a GY picker listing ONLY Spell Cards; the chosen Spell is banished. 3. The Deck picker lists ONLY cards with that name; the chosen card goes to the hand. 4. Decline at the prompt: nothing is banished. 5. Cancel the banish picker: the effect does not happen. 6. No Spell in the GY: no prompt.
