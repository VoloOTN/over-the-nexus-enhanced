# Eidos the Underworld Squire (0x0FE2, donor Great White) -- findings

Status 2026-11-11: BUILT as a test ROM (`_build_eidos_squire.py` -> rom_eidos_squire.nds, verify 43/43) and in the combined Monarch ROM (`scratch/_monarch_session.py`, 12 modules).
AWAITING IN-GAME TEST.  Nothing here is user-confirmed.

Printed text (scratch/ygoprodeck_cache.json): "If this card is Normal or Special Summoned: During your Main Phase this turn, you can Tribute Summon 1 monster, in addition to your Normal
Summon/Set. (You can only gain this effect once per turn.) You can banish this card from your Graveyard, then target 1 monster with 800 ATK and 1000 DEF in your Graveyard, except
"Eidos the Underworld Squire"; Special Summon it in Defense Position, also you cannot Special Summon monsters from the Extra Deck for the rest of this turn. You can only use this effect
of "Eidos the Underworld Squire" once per turn."  DARK / Spellcaster / Lv2 / 800 / 1000.
Clauses: E1 N-or-SS trigger, gain one extra Tribute Summon this turn (once per turn); E2 (GY) banish self, target an 800/1000 monster in the GY (not Eidos), SS it in Defense; E3 Extra Deck
SS lock for the rest of the turn; E4 E2 once per turn.

## KNOWN DEVIATION (a bug until the user says otherwise)
- E1 posts the kind-1 node of DOUBLE SUMMON (0x1C33): ns_counter 0x021B9514 (read this session, @0x021B959A) adds one Normal Summon when node 0x1C33 exists and no kind-2 (spent) node does.
  So the extra summon is a plain extra Normal Summon/Set (not Tribute-Summon-only) and it is not "immediate".  Restricting it needs a per-hand-card eligibility arm (Scrap Raptor / Ninishi chain).

## Confirmed (static, this session)
- Donor Great White 0x0FE2: donor_scan VERDICT CLEAN; Normal Lv4 1600/800; not in LIST_30 / LIST_106 (build asserts).
- Double Summon 0x1C33's cls0 resolver 0x02208C51 = "post the kind-1 node keyed by the resolving cid" (disassembled), the same resolver Swap Frog's cls3 uses.
- Premature Burial family resolver 0x02207529 (cls0 of PB 0x1366 / Call of the Haunted 0x137D / Soul Resurrection 0x17B7) does the GY Special Summon; position r2 = 1 = Defense (Restoration's front, proven there).
- GY Special Summon plain handler = 0x0223C9D0 (flags 8, pred 0), set-code variant 0x0223C9EC; PB's criteria row = {0xFFFF, 0x0223C9D1, 0x00010002}.
- c79 N-or-SS stub: 7th arm does not fit the 0x50 slot -> `c79_trigger_hook.where()` moves the stub to CAVE_ES_C79BIG (0x80 B) and re-points the 4-byte site; verified in the combined ROM (site -> 0x023B2050, 88 B, byte-exact).

## CPU evidence (emulator CPU, NOT user-confirmed) -- combined ROM sha 4acdb299...bb5
- cardtest mirror 0x0FE2 (kit Desert Protector x3 + Dark Hole x2), 8 duels: Eidos drawn 10 / summoned 0 / activated 12 (the CPU does not summon it: the E1 trigger is untraced; it ACTIVATES the GY effect).
- scratch/eidos_gdb.py seed 2 (one GDB connection, stall detector): ED_COND2 x8, ED_COST2 x1, ED_RES2 phases 0x80 -> 0x7F -> 0x64.  After the cost the banished list reads ['0xfe2'] (self-banish worked);
  at phase 0x7F zone 4 of the controller holds 0x1F5D (Desert Protector, an 800/1000 monster) with zone record +6 == 1 (Defense; Attack monsters read 0) -> the Defense front + the custom GY
  predicate + the PB resolver all ran.  No hang / freeze.  Not observed: the Extra Deck lock being tested, the target-pick UI (the CPU picks itself).

## Ruled Out
- (none)

## Open Questions (UNPROVEN)
- E1: the c79 trigger path for 0x0FE2 (the CPU never summons an 800-ATK monster); whether the mandatory cls1 {RES, 0, COND, 0, 0} shape fires for a Normal donor.
- E1: whether Double Summon's node is consumed correctly (extra summon offered, spent after use) -- UNTESTED.
- E2 from a human player: the target-selection prompt (0x02235605 picker over the virtual row 0xFFD2) and that the cost's self-banish happens before the target choice.
- Printed (not current) ATK/DEF in the predicate: KNOWN GAP.

## Next Experiment
- User test: Normal Summon Eidos -> a second Normal Summon (any monster) should be offered this turn.  Put Eidos in the GY with an 800/1000 monster (Desert Protector 0x1F5D, Edea) there: banish it,
  pick the target, expect the monster in DEFENSE and no Extra Deck Special Summon this turn.
