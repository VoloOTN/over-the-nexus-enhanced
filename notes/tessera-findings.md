# Tessera the Primal Squire (0x1123, donor Toon Alligator) -- findings

Status 2026-11-11: T2 + T3 BUILT as a test ROM (`_build_tessera.py` -> rom_tessera.nds, verify 41/41) and in the combined Monarch ROM (13 modules).
**T1 (hand ignition) BUILT 2026-11-11 (cards/tessera_hand.py + effects/prefind_hook.py), CPU-evidence for the offer only.**  AWAITING IN-GAME TEST.  Nothing here is user-confirmed.

Printed text (scratch/ygoprodeck_cache.json): "You can reveal 1 "Monarch" Spell/Trap in your hand; Special Summon this card from your hand. During your Main Phase, you can: Immediately
after this effect resolves, Tribute Summon 1 monster. If this card is sent to the GY: You can Special Summon 1 monster with 800 ATK/1000 DEF from your Deck, also you cannot Special Summon
from the Extra Deck for the rest of this turn. You can only use each effect of "Tessera the Primal Squire" once per turn."  LIGHT / Warrior / Lv1 / 800 / 1000.
Clauses: T1 hand reveal -> self SS; T2 Main Phase ignition "Tribute Summon 1 monster immediately after it resolves"; T3 sent to the GY -> SS an 800/1000 monster from the Deck + Extra Deck lock;
T4 each effect once per turn.

## KNOWN GAPS / DEVIATIONS (bugs until the user says otherwise)
- T1 missing (see Next Experiment for the recipe).  Without it Tessera can only be Normal Summoned / Set (Lv1).
- T2: grant = Double Summon's kind-1 node 0x1C33 (ns_counter 0x021B9514): an extra Normal Summon/Set, not Tribute-only, not "immediate".  Assumed to be a FIELD ignition (the printed text does not say).
- ATK / DEF tests use PRINTED values (cid getters).
- T3 trigger origin: leave-mask 0x0800 (Gravekeeper's Recruiter's recipe).  For Edea the CPU trace showed the mask row answering for a card that reached the GY from the hand -> probably any source.

## Confirmed (static, this session)
- Donor Toon Alligator 0x1123: donor_scan VERDICT CLEAN; Normal Lv4 800/1600; not in LIST_30 / LIST_106.
- cls3 ignition record shape (cid, RES, 0, COND, COST, 0) (dsl.py line 167); Mystic Piper's COND/COST pair = `!cost_ran && OPT -> 0 ; can_take_ignition 0x021F06E8` / `post OPT ; ...`.
- cls2 table holds ONE record per cid for dispatch (Warwolf's leftmost-record lesson), so T1 (hand) cannot be a second real cls2 record next to T3's: it needs a VIRTUAL cls2 hand record
  (Gearfried C1's find_event_handler front 0x0224A86A) + the ARM9 hand-offer front 0x02023566; both ARM9 hand-effect lists (0x0209BC4E x30, 0x0209BC8C x36) have no phantom left.
- Free phantoms used (ledger-checked): cls3 0x0E20, cls2 0x0EC9, leave 0x0E4B; virtual criteria row 0xFFD3.

## CPU evidence (emulator CPU, NOT user-confirmed) -- combined ROM sha dc09a714...ee9b
- cardtest mirror 0x1123 (kit Desert Protector x3 + Dark Hole x3), 8 duels: Tessera drawn 16 / summoned 2 / activated 5; no hang.
- scratch/tessera_gdb.py seed 2: T3 ran through the native Deck Special Summon machine: ED_COND, then RES phases 0x80 -> 0x7F -> 0x7E -> 0x7C -> 0x78 -> 0x64; COUNT(side 1, 0x1123, 0) > 0 at 0x80,
  PICK(1, 6, 0x1123, 0) at 0x7E, SS(1, loc 0x2299458, 1, position 2 = the player chooses, 0x11230000) at 0x7C from LR 0x2206EE5 (the native machine).  NOT proven from this trace: which monster
  arrived (my zone dump read the TURN player's side, but the effect side was the other one) and that the Extra Deck lock key was honoured.

## Ruled Out
- (none)

## Open Questions
- Does the SS'd monster land (zone dump of the controller's side)?  The trace needs `side_dump(c, regs side)` at the RES events.
- T2 untested (the CPU summoned Tessera twice but did not use the ignition in the traced seed).

## Next Experiment
- T1: copy Immortal Phoenix Gearfried's C1 infrastructure (cards/immortal_phoenix_gearfried.py: h1_front / h4_front / VREC / hand row + C1 cond/res shape; gearfried.c) with COST = the native reveal
  cost 0x021EAAA1 over a hand row {Monarch set code 0x6D, Spell|Trap word 0xC} (Tenacity / Psi-Reflector C2 show the UI path), RES = native handss_res 0x02206ABD.  Needs its own ov5 slots + two shared-front chains.
- User test: Normal Summon Tessera, use the Main Phase ignition (a second Normal Summon should be offered); send Tessera to the GY (e.g. Dark Hole) with an 800/1000 monster in the Deck: prompt, summon.


## T1 session (2026-11-11) -- PRE-DISPATCH hook
- find_event_handler 0x0224A118: desc[+5] (class) selects the table (class 0: cls2 table 0x02275C04 unless desc[+4]==0x25 -> cls0 0x0227E64C; 1: cls1 0x022860D4; 2/3 ...); it returns the LEFTMOST record of the cid, so
  Tessera's real cls2 T3 record shadows any hand-effect lookup.  Gearfried's miss-tail front (0x0224A86A) only fires on a MISS.  New hook `effects/prefind_hook.py`: 4-byte BL at 0x0224A124
  (`cmp r0,#3 ; bhi 0x0224A174`, bytes 032825d8 verified) -> ov5 stub (CAVE_PF_STUB, 0x90 B, entries (cid, class, zone, vrec)); on a hit it `pop {r1-r7,pc}` with r0 = the virtual record, else replays the cmp/bhi.
  Reusable for any card needing a second record in a table it already uses (Eidos Monarch E3).
- T1 = virtual cls2 hand record {RES 0x23b25b0, 0, COND 0x23b2500, COST 0x23b2580, +14 = movs r0,#1 ; bx lr}, hand row 0xFFD5 {0x6D, 0x0223CB39, 0xC} chosen by the T1_H2 front while the cost machine runs,
  ARM9 H4 hand-offer front (chains Block Dragon's CAVE_BD_H4, the site's current owner), COST = native reveal 0x021EAAA1, RES = OPT stamp + native handss_res.
- CPU evidence (emulator, not user-confirmed; scratch/t1_gdb.py): ED_COND is invoked for 0x1123 with desc[+3]=0xB, [+4]=0, [+5]=2 (so the pre-dispatch hit works) and returns 2 whenever a Monarch Spell/Trap (Tenacity 0x12EB)
  is in the hand, 0 otherwise.  The CPU never ACTIVATES it (no ED_COST / ED_RES in 9 seeds; its AI does not pick the effect), so the reveal UI path and the self-SS are UNPROVEN until the user plays it.
- Combined ROM sha 3936a0a0...df6f (15 modules).  Mirror 0x1123 (Monarch Spell kit): drawn 17 / summoned 11 / activated 7, no hang.
