# Edea the Heavenly Squire (0x0FDC, donor Gokibore) -- findings

Status 2026-11-11: BUILT as a test ROM (`_build_edea.py` -> `data/over_the_nexus/working/rom_edea.nds`, verify 54/54), in the combined Monarch ROM via `scratch/_monarch_session.py`.
AWAITING IN-GAME TEST. Nothing below is in-game confirmed.

Printed text (scratch/ygoprodeck_cache.json, id 95457011): "If this card is Normal or Special Summoned: You can Special Summon 1 monster with 800 ATK and 1000 DEF from your Deck in
Defense Position, except "Edea the Heavenly Squire", also you cannot Special Summon monsters from the Extra Deck for the rest of this turn. If this card is sent to the Graveyard:
You can target 1 of your banished "Monarch" Spell/Trap Cards; add it to your hand. You can only use each effect of "Edea the Heavenly Squire" once per turn."
Stats LIGHT / Warrior / Lv1 / 800 / 1000.  Clauses: C1 N-or-SS trigger "You can"; C2 Deck SS 800/1000 in Defense Position, not Edea; C3 Extra Deck SS lock this turn;
C4 sent-to-GY trigger "You can", target banished "Monarch" Spell/Trap -> hand; C5 each effect once per turn.

## Confirmed (this session, static)
- Donor Gokibore 0x0FDC: `donor_scan` VERDICT CLEAN (no data structure names it); Normal Lv4 1200/1400 (rule 2026-11-11: Lv<=8, ATK<=2000, no Lv4 >=1800).  Not in LIST_30 / LIST_106 (build asserts).
- Native Deck-SS machine 0x02206CAC (disassembled this session): default arm for an unlisted cid = gates 0x021AD870/0x021B9ECC/0x021B9ED8(side) -> param 0x02234E78(desc) ->
  count 0x02243FA8(side,cid,param) (0: msg 0x0D, phase 0x7B) -> phase 0x7F msg 0x30 -> 0x7E picker 0x0219C430(side,6,cid,param) -> 0x7C 0x0226925C(side, 0x0219C510(), 1,
  position r7, (cid<<16)|r6) -> 0x78 shuffle 0x021D269C -> 0x64.  r7 default = 2 (player chooses); only cids in the switch get r7 = 1 -> a replay in C is needed for Defense.
- Banished-zone criteria handler = thunk 0x0223FBA0 (type 0xC = SS) / 0x0223DB24 (type 8 = add/return) -> off-field picker 0x0223C6AC -> banished walker 0x0223C52C (player+0x7B4).
  Edea's banished row = a copy of 0x0223FBA0 with type 8 and aux = Monarch set code 0x6D (callback 0x0223C825 = has_set_code).
- Laval Lancelord 0x24E2 is the native shape of C4: cls2 {0, 0x02208181, 0, 0x021F05A9, 0x021E51E5, 0x02235605} + leave-mask row mask 0x0C04.  Edea uses mask 0x0800 (Gravekeeper's Recruiter).
- Free phantoms (ledger-checked): cls1 0x0E8A, cls2 0x0E64, leave 0x0E2D.  Virtual rows 0xFFD0 (Deck) / 0xFFD1 (banished).  ov5 slots CAVE_ED_* (RESERVE bumped to 0x18C00; chain rebuilt as rom_chain_18C00.nds, 129/129).
- The C79 hook stub has exactly 6 arms in its 0x50 slot (80 B): `c79_trigger_hook.register_extra` adds Edea at compile time (the shipped chain never sees it).
- The Extra Deck lock reuses Revolt's kind-1 key 0x5DCD (edlock.c already tests it).

## CPU evidence (emulator CPU, NOT user-confirmed) -- 2026-11-11
- Combined ROM rom_monarch_all.nds sha256 f4d06a17...db743 (11 modules incl. Edea), rig rebuilt, `scratch/edea_gdb.py` (stall detector, one GDB connection per seed).
- Seed 1: ED_COND2 (the sent-to-GY cond, mask 0x0800 row) was hit ONCE with Edea (0x0FDC) in the GY and a second/third Edea in hand -> the cls2 leave record + leave-mask row are reachable
  (the Edea reached the GY without a C79 event, so most likely a hand discard: mask 0x0800 appears to cover hand -> GY too; UNVERIFIED source).  COND2's return value and the picker were not logged.
- cardtest mirror 0x0FDC (kit Desert Protector x3), 8 duels: Edea drawn 12 / summoned 0 / activated 0.  With --fodder none (decks of Edea + Desert Protector only): drawn 48 / summoned 0 / activated 0 and
  Desert Protector (also 800/1000) summoned 0 as well -> the CPU never Normal Summons these 800-ATK monsters (it Sets / holds them): the C79 trigger path (C1) is NOT exercised by the CPU.
  This is not a defect signal; it means C1 needs the user's duel (Normal Summon Edea with an 800/1000 monster in the Deck).
- Ruled out: "CPU hit on C79 stub for 0x0FDC" never happened in 2 seeds (no summon at all).

## Open Questions (UNPROVEN until traced / tested)
- Position argument 1 = Defense (inferred from the native switch: cids 0x1E2C/0x136A/... with r7 = 1); [sp+4] = 1 kept as in the default arm.
- Whether the cls1 "You can" shape (Ophrys) is enough timing for an N-or-SS trigger on a Normal donor in this ROM (expected yes: Ophrys is shipped).
- Whether leave-mask 0x0800 fires for hand/Deck -> GY (event.leave_mask_is_field_only says field only: documented gap).
- Whether MODE (DATA+0) is always correct for the native criteria consumers of C4 (cond / picker / resolver are all wrapped).
- Printed (not current) ATK/DEF in the predicate: KNOWN GAP.

## Next Experiment
- User test: Normal Summon Edea with Desert Protector (800/1000) in the Deck: expect the "You can" prompt, the pick, the monster in DEFENSE; then Special Summon from the Extra Deck must be refused this turn.  Sent to the GY (field / hand discard): prompt to add a banished Monarch S/T.
- Optional CPU/GDB follow-up: a puzzle or a forced-summon trace to hit ED_COND/ED_RES (the CPU will not summon it).
