# Eidos the Underworld Monarch E1 GY half + E3, The Monarchs Masterplan C2, Monarch never-miss-timing -- 2026-11-12 session 2 (user: "build the other effects of Eidos", "make sure none of these effects can miss timing", "also do the last Masterplan effect")

Status: BUILT. Chain rom_chain_1B400.nds (129/129, sha256 8dc0158e79bd07123e76d806bbe0ea188c4c78769aa588c0894a2a889e0d8664, RESERVE 0x1B400). Combined ROM rom_monarch_eidos.nds sha256 fa81552f02221af9225357b2618eccf622d4f039efe743dac10d43d5139ba6cc (22 modules). Nothing in-game tested.
- Sweep vs the Perfection ROM: only new lines = "prefind stub byte-exact" on eidos_monarch / masterplan (the known class tessera_hand / strike already show: each module recomputes the shared stub from the entries registered so far; erebus, which registers last, PASSES the full stub).
- Build bug caught by the installer (not the ledger): escalation's predicate front grew to 0x40 B but its LEDGER comment said 0x30, so it overlapped CAVE_EB_H4 @0x023B3B50; "ov5 cave 0x023B3B20 is not free". Relocated CAVE_EC_FRONT to 0x023B54E0 (0x40). LESSON: when a stub grows, update its "(0xNN bytes)" ledger comment, not just the module's RESERVE dict -- check_allocations only reads the comment. CAVE_FREE is now the ceiling (0 B left at RESERVE 0x1B400).

## Printed text (scratch/ygoprodeck_cache.json)
- Eidos: "If this card is Normal or Special Summoned: You can add 1 "Monarch" Spell/Trap or 1 monster with 2800 ATK/1000 DEF from your Deck or GY to your hand. You can declare 1 Attribute; make 1 face-up monster on the field become that Attribute. If you Tribute Summon a monster with 2400 or more ATK and 1000 DEF, while this card is in your GY: You can add this card to your hand or Special Summon it. You can only use each effect of "Eidos the Underworld Monarch" once per turn."
- Masterplan C2: "If this card is banished: You can target 1 face-up monster your opponent controls; add 1 monster with the same Attribute that has 2400 ATK/1000 DEF, from your Deck or GY to your hand, then you can apply this effect. * Immediately after this effect resolves, Normal Summon 1 [Zaborg 0x174D / Mobius the Frost 0x17E2 / Thestalos the Firestorm 0x182E / Granmarg the Rock 0x185F / Raiza 0x1BCD / Caius 0x1D5C]. You can only use this effect once per turn."

## Missed timing (audit of the 30 cids' trigger records in rom_monarch_perfection.nds)
- Optional triggers whose +0x10 tag runs the "You can" body 0x021E50DC (which asks the miss-timing test 0x021EE0E0): Edea (cls1 + cls2), Mobius (+0x10 = 0x021E50DD itself), Eidos Monarch, Perfection, Ehther, Erebus, Return of the Monarchs, Angmarl, The First Monarch, Tessera (cls2); +0x10 = 0 never reaches the test (Caius / Granmarg / Zaborg / Thestalos / Raiza Mega, Eidos Squire cls1).
- Printed "When ... : You can" (the only ones the printed text allows to miss): Mobius the Mega Monarch, Angmarl, Return of the Monarchs -- made never-miss anyway on the user's instruction.
- FIX: CAVE_MON_NOMISS = front on `bl 0x021EE0E0` @0x021E510A (KB timing.miss_timing_test_two_callers), table of all 30 cids -> 0, else the Dragon Rulers' cave3 head 0x0221AC08. (cards/erebus.py NEVER_MISS.)

## Eidos (cards/eidos_monarch.py + c/eidos_monarch.c)
- E1 GY half: row 0xFFD4 handler = CAVE_EM_GYH (Deck walker 0x0223BC3D + GY walker 0x0223C4E9, same predicate); cls1 +04 = CAVE_EM_RES1 (list picker; GY -> hand 0x021C7038 on the matching GY entry, Deck -> hand 0x021C72CC = the native search's own mover (KB), shuffle).
- E3: front CAVE_EM_TRIGF over `bl 0x022391CC` @0x02265D2A (head of the summon dispatch 0x02265CF8; every event; r6 = event, r7 = ctx); event 7 -> CAVE_EM_POST: own Tribute Summon (zone flag bit 3) of a printed 2400+/1000 monster -> 0x021D3648(side, 0x1230, 7, ctx) (Assault Synchron's GY poster). Virtual cls2 GY record CAVE_EM_VREC3 via prefind_hook (zone 0xE) {RES3G, COND3G, "You can" tag}; RES3G = menu (new dlg ids 603 "Add it to your hand." / 604 "Special Summon it.") -> GY -> hand or the native GY self-SS 0x0220731D (player chooses position). OPT key 0x9230.
- UNPROVEN: that a Tribute Summon is event 7 at the dispatch head and that zone flag bit 3 is already set there; that the GY poster's event reaches a cls2 record for zone 0xE.

## Masterplan C2 (cards/masterplan.py + c/masterplan.c)
- Banish detection: fronts on the Dragon Rulers' gates -- CAVE_MP_H6F @0x021C71C8 (GY -> banished, 0x0D6A -> Z=1) and CAVE_MP_H7F @0x021D1B98 (other zones, dest 0xF -> banish leaf 0x021D1D3E). Field banish (H8) NOT covered (a Normal Spell is not on the field).
- Virtual cls2 record for the banished zone 0xF via prefind_hook (the Rulers' C4 is class 2 / zone 0xF). Rows 0xFFD6 (C1) / 0xFFD7 (targets, MODE 8) / 0xFFD8 (adds, MODE 9) in CAVE_MP_ROWS (relocated, 0x30) with the relocated MODE-aware CAVE_MP_H2.
- Resolver: stamp OPT 0x8D6A; picker over the opponent's face-up monsters that have a same-Attribute 2400/1000 add; picker over Deck + GY adds; move; if a named Monarch in hand can be Summoned: menu (dlg 605 "Normal Summon a Monarch." / 0x1AC "Do not activate effect.") -> yes = delegate to Cry Havoc!'s machine 0x0220D80D (escalation's predicate front now routes 0x0D6A to CAVE_MP_NSPRED = the six named cids).
- KNOWN DEVIATION: the opponent's monster is chosen at resolution, not targeted at activation.
- Prefind stub relocated again: CAVE_PF_STUB 0x023B4CE0 (0x100) for 7 entries.

## CPU trace 1 (ROM fa81552f, 4 seeds, build/cpu_battery/gdb_em/em_0..3.json; CPU duels, NOT user-confirmed)
- Eidos E1 (new CAVE_EM_RES1): 4 activations, each 0x80 picker (mode 7, cid 0x1230) -> 0x7F DECK2HAND 0x021C72CC(side, &pick) -> 0x64 shuffle -> 0. GY picks never chosen (GY branch UNEXERCISED).
- Eidos E3: CONFIRMED (CPU, seed 3): Tribute Summon of Eidos itself (summon record cid 0x1230, flag bit 3) -> CAVE_EM_POST -> GYPOST 0x021D3648(0, 0x1230, 7, ctx) -> EM_COND3G returned 2 -> EM_RES3G 0x80 MENU(desc, 0x103, 0x25B, 0x25C) (= the new dlg ids 603 / 604) -> answer 0 -> GY2HAND 0x021C7038 -> 0. The Special Summon branch (answer 1) not chosen. EM_POST also ran for non-Tribute summons and posted nothing (correct).
- Never-miss front: hit for 0x1230 (seed 2: 1, seed 3: 7 entries logged), no stall.
- Masterplan C2: NOT exercised -- Masterplan was never banished (MP_H6 / MP_H7 fronts only saw other cids).

## CPU traces 2 + 3 (same ROM, 8 seeds, Masterplan-heavy decks; logs gdb_em_run2/ and gdb_em/)
- Eidos E3 fired again (seeds 0 / 1 of trace 2: EM_COND3 -> EM_RES3 -> menu -> GY2HAND); Eidos E1 again Deck-only picks.
- Masterplan went to the GY in every duel (Erebus' cost / C1), but the CPU NEVER banished it -- not even with The Prime Monarch's GY effect available and Masterplan the only other Monarch S/T in the GY (the CPU did not use Prime's GY effect). The MP_H7 hits with r5 = 0x0D6A were moves to the GY (not dest 0xF). So Masterplan C2 (banish gates -> virtual cls2 -> resolver -> optional Normal Summon) is COMPLETELY UNEXERCISED; it needs the user's in-game test.

## Chain rebuild note
- scratch/_build_chain_headdecks.py now appends the STOCK card names as a fallback for name -> cid resolution: CARD_TEXT renames Tiki Soul (The First Monarch's donor) and the stock CPU deck wcs006_statue lists 'Tiki Soul' x3, which failed the deck preflight. (So that CPU deck plays The First Monarch in any ROM that includes first_monarch -- donor-in-a-deck, a donor rule the earlier session broke.)
