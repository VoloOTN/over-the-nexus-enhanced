# Thestalos the Mega Monarch (0x127B, donor Red Archery Girl) -- live findings (2026-11-11)

Text: "You can Tribute Summon this card by Tributing 1 Tribute Summoned monster. If this card is Tribute Summoned: Look at your opponent's hand and discard 1 card from their hand, then, if it was a Monster Card, inflict damage to your opponent equal to its original Level x 200. If this card was Tribute Summoned by Tributing a FIRE monster, add this additional effect. * Also, inflict 1000 damage to your opponent after that."  Lv8 FIRE Pyro 2800/1000.
Clauses: M0 alt Tribute (shared Mega front); E1 trigger on Tribute Summon (shared TRIG front); E1a look at opponent's hand + discard 1; E1b Monster -> Level x 200 damage; E2 FIRE Tribute -> +1000 damage after.
Donor Red Archery Girl 0x127B approved by user 2026-11-10 ("Approve donors"); donor_scan CLEAN; Normal Monster 1400/1500.

## Built (static; NOT in-game; NOT traced)
- cards/c/thestalos.c = a clone of vanilla Thestalos the Firestorm Monarch's cls1 resolver 0x0221D150 (disassembled this session: phase 0x80 -> if the opponent has cards, 0x022599C8(opp, 1, 1) = look at hand + pick a discard, return 0x7F; phase 0x7F -> cid of the discarded card from table 0x0229C33C[ [0x0229DE94+6] ], 0x02029E60 monster test, 0x0202ABD8 Level, 0x021CFBC8(desc, opp, Level x 100) damage) with Level x 200, plus the FIRE latch (CAVE_MM_FLAG bit 4, set by the Tribute-payment capture front) -> 1000 more damage.
- Wired into mega_monarch.py: THESTALOS in MEGAS (M0 / TRIG / CAP fronts pick it up), cls1 phantom 0x0E77, card_props FIRE/Pyro/Lv8/2800/1000, slot CAVE_MM_REST 0x023B08D8 (0xA0). M0 relocated to 0x023B0978 (0x80) and TRIG to 0x023B09F8 (0x50) because they outgrew their slots; RESERVE raised to 0x16C00 (chain rebuilt, 129/129 steps, rom_chain_16C00.nds sha256 f70a1dda347bf95a4d81dcc30e58e670c5a89c6fb5c8e2abb17187ebae4f9ed9, built with the COMMITTED ydc_decks.py because the working-tree copy failed the deck preflight).
- Combined ROM data/over_the_nexus/working/rom_monarch_all.nds sha256 6a08165a6db8ce9c94a0fd93fe2bda04caf3f74dbba14c08446684539185723b (Megas x6, March, Stormforth, Tenacity, Return, Restoration, Awaken). The sequential build and the in-memory session build (scratch/_monarch_session.py, 181 s) gave BYTE-IDENTICAL ROMs.

## Trace
- scratch/thestalos_gdb.py, 6 seeds, build/cpu_battery/gdb_th1: the resolver (CAVE_MM_REST) was NEVER entered. Cause not established (the CPU may not summon the Mega); mirror running.

## UNPROVEN
Everything: the 0x022599C8 arguments for the human path, the damage amount, the FIRE latch, the CPU path, text.

## Session 26b: mirror (2026-11-11; emulator CPU; rom_monarch_all.nds; NOT user-confirmed)
- cardtest mirror 0x127B (12 duels, Monarchs x3 each + Dark Hole x2): drawn 21 / summoned 0 / activated 0. The CPU never Tribute Summons the Lv8 Mega (no CPU path for the alternate 1-Tribute cost), so neither the resolver (CAVE_MM_REST never entered in 6 GDB seeds) nor the damage could be exercised. Same pattern as the other Megas: the human path is the test.
- In-game steps for the user: Tribute Summon a Level 5-6 monster, then Tribute Summon Thestalos by Tributing it (M0): (1) a prompt to look at the opponent's hand and discard 1; (2) if the discarded card is a monster, the opponent takes its original Level x 200 damage; (3) Tributing a FIRE Tribute Summoned monster adds 1000 damage afterwards; (4) with the opponent's hand empty nothing happens; (5) the text reads correctly (bullet before the FIRE clause).
