# Frost Blast of the Monarchs (Normal Spell) on Double Snare 0x14C3 -- live findings (2026-11-11)

Text: "If you control a monster with 2400 or more ATK and 1000 DEF: Target 1 Set card on the field; destroy it. You can banish this card and 1 "Monarch" Spell/Trap Card from your Graveyard, then target 1 Set card on the field; destroy it."
Clauses: C1 condition: control a 2400+ ATK / 1000 DEF monster; C2 target 1 Set card; destroy it; C3 (GY): banish this card + 1 other Monarch S/T from the GY (cost), then target 1 Set card; destroy it.
Donor Double Snare 0x14C3 chosen by me (unused, not in decks; stock cls0 {0x14C3, 0x02204899, 0x021DE2B1, 0, 0, 0x02234DA5}); the user said "implement frost blast next" and did not name a donor.

## Built -- AWAITING IN-GAME TEST (cards/frost_blast.py + cards/c/frostblast.c)
- cls0 {0x14C3, 0x02204899 (native destroy target 0), 0x021DFD1D (Granmarg the Rock Monarch's Set-card filter), COND, 0, 0x02234DA5 (single-target selector)} in place; COND = a face-up monster of yours with PRINTED ATK >= 2400 and DEF == 1000 (cid getters 0x0202AC49 / 0x0202AC29). KNOWN GAP: printed, not current, ATK/DEF (a buffed / debuffed monster is judged on its printed stats).
- C3: cls2 {0x14C3, 0, 0x02204899, 0x021DFD1D, COND2, COST2, 0x02234DA5} over cls2 phantom 0x0EBE; 18th virtual GY row (gy_vrow_hook MONARCH_ARMS + layout GYV2, now also relocating the POST stub: CAVE_GYV2_POST 0xD0); virtual GY row 0xFFB0 {0x14C3, set 0x6D, 0x0223CA2D, word 0x2C}; COND2 = another Monarch S/T in the GY (menu); COST2 = native banish cost 0x021E5319 then native self-banish 0x021E5709. "Monarch" list (tenacity.py MONARCH) is now FULL (8 u16 in 0x10 bytes): future Monarch S/T need CAVE_TN_MON widened.
- ov5 RESERVE 0x17400 (chain rebuilt: rom_chain_17400.nds sha256 0b152e7c082455b99d251fb4d8dd41882286fcf8cc31db47298a58e20eee11db, 129/129 steps, committed ydc_decks.py). CAVE_FREE 0x023B12B0.
- Combined ROM data/over_the_nexus/working/rom_monarch_all.nds sha256 ffbe745c974a91bc6c9d864bc515aaccab98a6154df18e2983a5365c97575dd9 (scratch/_monarch_session.py, 47 s). frost_blast.verify() / pantheism.verify() run in the background build.

## Confirmed by CPU (emulator, NOT user-confirmed; scratch/frostblast_gdb.py, build/cpu_battery/gdb_fb1/rs_1..5.json)
- Mirror (8 duels, Zaborg/Mobius/March/Tenacity/Mirror Force/Trap Hole): Frost Blast drawn 10, activations counted 11, 0 hangs.
- C1 (seed 3): Mobius 0x17E2 (2400/1000) face-up, Frost Blast activated from the hand; the native destroy resolver 0x02204898 ran for cid 0x14C3 and the Set card 0x1317 (face-down S/T) reached the GY with Frost Blast.
- C3 (seed 1): GY [March 0x15EC, ..., Frost Blast 0x14C3]; COST2 entered 3 times (cost step 0 -> 1 -> 2); at the destroy resolver the GY had lost March and Frost Blast and the banished list held [0x15EC, 0x14C3]; the Set targets (a Set monster and a Set S/T) were on the field.
- NOT SHOWN: which card was destroyed in C3 (the snapshot is at the resolver's entry), the human targeting prompt, Set MONSTERS as C1 targets, refusal when no Set card exists, refusal of C3 with no other Monarch S/T in the GY, the text.
- In-game steps: C1: control Zaborg / Mobius / any 2400+ ATK / 1000 DEF monster; with a Set card on the field the Spell is activatable and asks for a Set card (yours or theirs, S/T or monster); it is destroyed. No such monster: not activatable. C3: with Frost Blast and another Monarch S/T in your GY, the GY effect is offered (monster not required); it banishes both and destroys the Set card you target.
