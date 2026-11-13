# Souleating Oviraptor — findings

Printed text (scratch/ygoprodeck_cache.json, id 44335251, Lv4 DARK Dinosaur 1800/500):
"If this card is Normal or Special Summoned: You can take 1 Dinosaur-Type monster from
your Deck, and either add it to your hand or send it to the Graveyard. You can target 1
other Level 4 or lower Dinosaur-Type monster on the field; destroy it, then Special Summon
1 Dinosaur-Type monster from your Graveyard in Defense Position. You can only use each
effect of "Souleating Oviraptor" once per turn."

- C1 (session 2026-09-25 scope): N/SS trigger, Dinosaur from Deck -> hand OR GY, HOPT.
- C2 (not started): ignition destroy Lv<=4 Dinosaur, then SS Dinosaur from GY in DEF.

User choices 2026-09-25: full hand-or-GY choice (no add-only stage); donor Two-Headed
King Rex (pending checklist).

## Confirmed
- verify_knowledge 2026-09-25: 545 facts, 501 PASS / 0 FAIL / 44 UNVER. Reused facts all VERIFIED
  in docs/engine: summon lists (summon_event_dispatch.yaml:27-59), turnlog_once_per_turn_pair,
  once_per_turn_must_stamp_at_activation, option_prompt_is_four_way, criteria_hand_vs_deck_handlers.
- Donor Two-Headed King Rex = cid 0x0FC6 (scratch/cid_to_name.json key 4038).
- Donor u16 scan (scratchpad scan_cid.py, aligned u16 == 0x0FC6, stock rom.nds + rom_all_patches.nds):
  - ov3 code hits x11 (0x0219D5A2 ... 0x0225646A) all decode `lsrs r6,r0,#0x1f` = instruction, not cid.
  - arm9 (chained) 0x02049C9C = inside ARM code (e58d neighbours); 0x0209D722/0x0209E3B0/0x0209E720/
    0x020A13B2 = monotonic 0xFC5/0xFC6/0xFC7 ramp tables (same as Miscellaneousaurus found). Not cids.
  - ov5 0x02342008: neighbours 0x0488 0x0C80 0x9009 0x0448 -> not a cid table (ASSUMED benign).
  - **REAL per-cid hit: Fusion-material table.** stock 0x02270CBC row = {0x11A2 Cyber Saurus, 0x1147,
    0x0FC6, 0} -> King Rex is a named Cyber Saurus material (still present in chained ROM @0x02270CC0).
    0x02270CC6 (Bracchio-raidus row 38) already rewritten by Accel Synchron in the chained ROM.
  - No cls/criteria/LP record hit -> records-free (a) PROVEN.
- Summon trigger lists, phantoms (card_prop set = cid_to_name, 4305):
  - c7 0x0228F7AC chained free phantoms 0x19C0 0x19D3 0x1B1A 0x2346; **0x19C0 unclaimed in any pool**.
  - c9 0x0228F63A chained free phantoms 0x176C 0x1ABE 0x1ABF; **0x1ABF unclaimed in any pool**.

- User approved donor 0x0FC6 2026-09-25, Cyber Saurus row left alone.
- Template = patch_psi_reflector C1 (in-game confirmed 2026-09-15): c7/c9 lists + Gearframe cls1
  {+04 res, 0, +0C cave cond (turnlog query kind 1 then 0x021F0821), +10 cave slot4 (0x021E51E5, post on 1), 0}
  + timing_class_hook.ARMS ARM_JW for the donor.
- Criteria row: {0x0FC6, 0xFFFF, 0x0223CAD9, 0x48000002}. PROVEN by stock rows sharing handler 0x0223CAD9
  with race word: Fossil Dig 0x20A0 row 965 = 0x48980002 (Dinosaur, hand), Reinforcement 0x14D0 0x78900002
  (hand), Rock Bombardment 0x18DA 0x30000002 (SEND to GY). One handler serves both destinations.
  0x0223CAD8 disasm: reads row+0 cid, row+8 word -> 0x0223BC3C(ctx,cid,0,0,[sp]=word,[sp+4]=2).
- Resolver phase protocol PROVEN (disasm 0x02218032..0x0221804A, stock): [0x0229AAFC+0x70] = saved u16
  phase, seeded 0x80 @0x0221802C; resolver return -> strh phase; loop while nonzero. Invoker 0x0224AEB8
  calls slot1 as (desc, r1=0 passthrough). So a private phase value (0x90) round-trips.
- desc[+0x18] is FREE for the donor in both natives (disasm stock):
  - add-to-hand 0x02207EF4 reads [r5,#0x18] only @0x02207F80, inside the cid-switch arms 0x23CA/0x24E1;
    donor takes default 0x02207FCC (r4=1).
  - deck-send 0x02208DD4 reads [r4,#0x18] only @0x02208E5E, cid 0x228E arm; donor default = count 1,
    [r5+0x78]=0.
- Dialog labels (dlg_text_e, 8-bit, dlg_indx_e u32 offsets): 0x58 'Select the card(s) to add to your hand.',
  0x3A 'Select the card to send to the Graveyard.' (no bare "Add to hand" label exists), 0x103 title.

## Design (C1)
ov5 resolver thunk at cls1 +04: phase 0x80 -> 0x0219ABB4(desc,0x103,0x58,0x3A,0,0,mask 3), return 0x90;
phase 0x90 -> desc[+0x18] = [0x0229DD94+0x34]; [STATE+0x70]=0x80; fall into dispatch; other phases ->
dispatch: desc[+0x18]==0 ? 0x02207EF5 : 0x02208DD5 (desc, r1).
Deviation to disclose: destination is chosen at resolution BEFORE the card pick (same outcomes).

## Build 1 (2026-09-25) -- IN-GAME CONFIRMED BY USER 2026-09-25
- User report verbatim: "1. Confirmed 2. Confirmed 3. Confirmed 4. Confirmed 5. Confirmed 6. Confirmed 7. No Regession"
- _build_souleating_oviraptor.py (Psi-Reflector + Oviraptor onto stock rom.nds) ->
  data/over_the_nexus/working/rom_souleating_oviraptor.nds
  sha256 d9c282413ebc96b5bf94c9440f05438e88b405d4ddddc9d701723cac87c0b732. verify(): both PASS.
- Claims: CAVE_OVI_COND 0x023A18A4 / SLOT4 0x023A18D4 / RES 0x023A1904 (CAVE_FREE -> 0x023A1964);
  phantoms c7 0x19C0, c9 0x1ABF, cls1 0x0E47, criteria 0x0E67. check_allocations: OK.
- timing_class_hook.ARMS += 0x0FC6 (ARM_JW). Lift proven by EXECUTION: stub with vs without the arm,
  244800 inputs over every arm cid +-1 -> only 0x0FC6 differs (Psi 0x1008 etc. identical).
  scratch.timing_hook_equiv (pre-lift baseline) still OK.
- Stubs disassembled: all blx literals odd, pops {..,pc}, no imm3 ADD/SUB.
- KB: dispatch.deck_resolvers_desc18_free_on_default_arm (VERIFIED), card.souleating_oviraptor_c1 (UNVERIFIED).
- ASSUMED: B-cancel on the option menu -> answer != 1 -> hand branch (stub treats only 1 as GY).

## Ruled Out
- summon_trigger_hook.py is NOT the route: it serves Synchro/Fusion/Ritual-Summoned
  (list 0x0228F6C0) only. (memory otn-shared-summon-trigger-hook; UNVERIFIED this session)

## Open Questions
All inherited from an Explore pass, UNVERIFIED this session:
- N-Summon trigger list 0x0228F7AC (code 7), SS list 0x0228F63A (code 9), evaluator
  0x02265768; donor needs a cls1 record (Hanzo precedent patch_ninja_grandmaster_hanzo.py).
- Criteria row {0x0223CAD9 deck-select, 0x48000002 Dinosaur} (Miscellaneousaurus word).
- HOPT: turnlog post 0x021D2584 / query 0x021A14E8, stamped at activation (+10 wrap).
- Choice: prompt 0x0219ABB4 (4-way), answer at [0x0229DD94+0x34]; which resolver hosts
  it (0x02208DD4 phase 0x7C vs 0x02207EF5)? label ids for "hand"/"Graveyard"?

## C2 (session 2026-09-25, started after C1 confirmed)
Scope: C2a ignition, target 1 OTHER Lv<=4 Dinosaur on EITHER field; C2b destroy it; C2c then SS 1 Dinosaur
from own GY in DEF (picked at resolution, not targeted); C2d own OPT (kind 2). Must not regress C1 / Psi C1.
User rulings 2026-09-25: (1) the SS'd monster MAY be the one just destroyed; (2) NO SS unless the destroy
happened; (3) activation requires a legal target AND a Dinosaur already in own GY.
3DS: CARD_Name_E.bin has neither "Oviraptor" nor "Souleating" (2026-09-25) -> no Konami handler.
No NDS card in cid_to_name has "destroy it..., then Special Summon" wording (regex over ygoprodeck cache).

### C2 Confirmed (disasm, stock rom.nds, 2026-09-25)
- Destroy-target body 0x02204674(desc): zero [0x0229C314+0x14/+0x18]; 0x022349B0(desc,0,&ref) -> side=ref&0xFF,
  slot=(ref>>8)&0xFF; re-validate 0x0224A924(desc,side,slot) (slot2 filter, KB); 0x021CF388 -> 0x021CDD4C(desc,
  1<<(side*16+slot), 0xE GY, 0x10000002). 26 callers.
- **Native "destroy, then X" protocol**: resolver 0x0221DEE4: phase 0x80 `bl 0x02204674 ; movs r0,#0x7F`;
  phase 0x7F `ldr r1,=0x0229C314 ; ldr r1,[r1,#0x14] ; cmp r1,#0 ; beq end` -> then-part -> return 0.
  Same 0x80->0x7F + [0x0229C314+0x14] test at 0x02209256, 0x0220FE08, 0x022104A4, 0x022141F2, 0x0221FCC6,
  0x02220F96, 0x02221616. => [0x0229C314+0x14] != 0 == "the destroy happened".
- Uria 0x19A3 cls3[231] = {0x02204899, 0x021DEA35, 0x021F01C1, 0x021E5061, 0x02234DA5}; Cyber Laser Dragon
  0x19A9 cls3[233] = {0x02204899, 0x021D88FD, same...}. +14 0x02234DA4 = `r2=0x119 ; bx 0x02234CA5`; worker
  calls 0x0224AA94/0x02234E3C/0x0219A818/0x02234BDC/0x0224BA34/0x0224BBB0/0x022347B0 -- no criteria row fn.
- Mask-wrapper rosetta scan (thin wrappers over 0x021D6E40, owners' printed text): 0x1410 = "monster on the
  field" (Man-Eater Bug, Zaborg, Kahkki); 0x414 = "face-up monster on the field" (Dark Jeroid, Cold Enchanter);
  **0x1414 wrapper 0x021DB4F9 = Snowman Eater 0x2047 "Target 1 face-up monster on the field; destroy"**,
  also Turbo Cannon. Bit 0x4 = face-up; bit 0x1000 appears on destroy cards (meaning ASSUMED).
- Live race: native filter 0x021D7E76..0x021D7E9E calls 0x021B88F0(cand side, cand zone, r2) with
  r2 = u16[0x0229ACCC + (desc[2]&1)*0xB3C + desc[3]*0x14] (the SOURCE's +0x38 stamp) if desc[3] <= 10 else 0.
- Live Level 0x021B807D(side, zone, 0) (patch_jet_warrior.py:754, patch_revolution_synchron.py:299).
- GY = player+0x55C, count player+0x14, cid = word & 0x3FFF (KB, 0x021A2510).
- criteria_row_hook keys on [0x0229A9FC+0x50]; at resolution it is set @0x02218032 (`str r5,[r0,#0x50]`
  right before bl 0x0224AEB8). At the +0C menu check it may be stale (Misc findings) -> cond must NOT use a
  criteria row; scan the GY directly.

## C2 Build 1 (2026-09-25) -- IN-GAME CONFIRMED BY USER 2026-09-25, SHIPPED
- User report verbatim: "All confirmed - ship it"
- sha256 8db38740d9cc8701c8d31d6762d6bbd6b4bace98d8942a38b45aa6dbbb9741a2 (Psi + Oviraptor C1+C2); verify PASS both.
- Claims: cls3 phantom 0x0E3F, criteria phantom 0x0E69 (GY row rel 1, appended after the Deck row), crh arm ovi,
  CAVE_OVI_C2FILT 0x023A1964 (112 B) / C2COND 0x023A19E4 (112 B) / C2COST 0x023A1A54 (36 B, 0x28) /
  C2RES 0x023A1A7C (256 B); CAVE_FREE -> 0x023A1B9C. check_allocations OK.
- Row-hook lift proven by execution: stub with vs without the ovi arm, 149760 inputs over every arm cid +-1
  -> only 0x0FC6 differs; 0x0FC6: cls3 -> rel 1, else native. scratch.rowhook_equiv also OK.
- ⚠️ Harness bug fixed: scratch/rowhook_equiv emulated the "old" stub at CAVE_ROWHOOK_OLD 0x0239C5A8; at 8 arms
  the stub reaches 0x0239C6B8 and overlapped CAVE_DF_STAGE 0x0239C6A8, which the harness writes -> a clobbered
  literal made cid 0 look misrouted. Moved OLD_BASE to scratch 0x02920000. The LIVE stub is unaffected.
- thumb_asm has no `bhi` and no `mul`: used bgt (zone byte 0..255) and shifts (x0x14 = <<4 + <<2).

## Next Experiment
- None. Whole card shipped 2026-09-25 (steps.STEPS after Miscellaneousaurus + _verify_all_patches.SHIPPED).
- EE build 76/76 -> rom_all_patches.nds sha256 f0f15c4ce8c0f238aa637a181ea0ebcf091ab943509ace4a0c466d4cb99dd7a9.
- Sweep 61 passed / 1 failed: patch_ninishi -- its 5 hook sites BL to CAVE_SR_NS* (Scrap Raptor chains into
  ninishi by design); ninishi verify() is stale, NOT an Oviraptor regression. Spun off as a separate task.
