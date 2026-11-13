# Koa'ki Meiru Wall — findings

Donor: Dark Rabbit 0x1126 (Normal). Template: Koa'ki Meiru Sandman 0x2264. 3DS Wall cid 0x2444.
Scope (user, 2026-09-15): whole card, single-card ROM only, not wired into STEPS.
Status: ALL 8 ORACLES in-game confirmed by user 2026-09-15 ("All confirmed, ship it") on build 1 below.
SHIPPED 2026-09-15: steps.STEPS step 65/66 + _verify_all_patches.SHIPPED. EE build 66/66 -> rom_all_patches.nds
sha256 09743371464489340cb341b3596f917c80c5b7b3e9f120ad6443891202016622; verify sweep 54 passed 0 failed.
patch_card_art: user's meiru_wall entry fixed to cid 0x1126 / basename 'meiru__wall' (was 0xFFFF / 'meiru_wall').
Oracle 6 confirmed => Rock-only reveal picker works with the grown 0x0228EF48 list (which part filters it is still unisolated).
Build 1 (2026-09-15): _build_koaki_wall.py on rom_all_patches.nds ->
rom_koaki_meiru_wall.nds sha256 a67702e31220043e3565c8776410b170355ee095669708eccad94f09968de708.
verify() 12/12 PASS; check_allocations OK; verify_knowledge 459 PASS 0 FAIL.
Installed stub disassembled from the built ROM: literals 0x021AB90D / 0x02022FC9 / 0x021F06E9 (all odd),
both exits POP{..PC}. Hand list imm 0x2022, 32 entries, trailing pointer 0x0225BF49 intact.
KB: dispatch.koaki_negator_spell_trap_switch (VERIFIED).

Printed text (ygoprodeck_cache id 66816282), Lv4 Rock EARTH 1900/1200:
1. During each of your End Phases, destroy this card unless you send 1 "Iron Core of Koa'ki
   Meiru" from your hand to the GY or reveal 1 Rock monster in your hand.
2. When your opponent activates a Spell Card (Quick Effect): You can Tribute this card; negate
   the activation, and if you do, destroy that card.

## Confirmed
- Wall absent from NDS tsv; 3DS CARD_Prop rec 4385 = "Koa'ki Meiru Wall" cid 0x2444 (python lookup this session).
- (scratch kmw1.py, stock rom.nds) cls3 rows: A-Team 0x183A [184], Guardian 0x1FEF [522], Sandman 0x2264 [675]
  all {res 0x022062F9, 0, cond, cost 0x021E50CD, 0}; Sandman/A-Team cond 0x021F2D01. crit[1152]
  {0x2264,0xFFFF,0x02241471,0x30000002}. No 0x1126 rows.
- Cond 0x021F2D00 prologue (disasm): push{r3-r7,lr}; r5=mine r0; r4=act r1 (adds, Z) ; act==0 -> 0;
  act[+3] (zone) > 0xA -> 0; act[+5] != 0 -> 0; bl 0x021AB90C(act,1) != 0 -> 0; then cid switch on [r5].
- Sandman block 0x021F34BE: act[+2]^act[+6] == mine[+2]^mine[+6] -> 0; ldrh r0,[act]; bl 0x02022FDC;
  ==0 -> 0; bl 0x021F06E8(mine, act); pop{r3-r7,pc}.
- arm9 0x02022FC8 = push{r3,lr}; bl 0x0202ABF8; cmp r0,#0xD -> 1/0 (Spell). 0x02022FDC same with #0xE (Trap).
- Cost 0x021E50CC: 0x021CF658(mine[+2], mine[+3]) (Tribute self); return 1. No cid switch.
- Resolver 0x022062F8: r2=1; bl 0x02206230 -> 0x022061A4 (negate) + zone-dispatched destroy
  (0x021CF3E8/0x021CF374/0x021D2478/0x021D24B4). No cid switch anywhere on the path.
- Phantoms, identical in stock + chained rom_all_patches.nds, not in PHANTOM_CLAIMS (kmw3.py):
  cls3 0x0E22 (1 row), crit 0x0E39 (1 row), quick-effect list 0x0E63, KM set 0x2444.
- Hand-criteria list 0x0228EF48: 31 real cids, NO phantom; +0x3E (0x0228EF86) = 0x0000 pad, then
  0x0225BF49. Count = `movs r2,#0x1F` @0x0225A418 (consumer 0x0225A3F0, literal @0x0225A54C).
  Plan: grow to 0x20 into the pad (Gates of Dark World precedent, later withdrawn as ineffective for a discard).

## Inherited from Explore agents this session — UNVERIFIED until re-read in step 1
- Sandman cls3[675] @0x0227DCBC {0x2264, 0x022062F9, 0, 0x021F2D01, 0x021E50CD, 0}; no cls0/1/2.
- Sandman crit[1152] @0x022749C4 {0x2264, 0xFFFF, 0x02241471, 0x30000002}.
- Upkeep = generic walker 0x02255959 (set code 0x46 member, skip list 0F80/2075/2078/2079/2349, own criteria row).
- Cond switch 0x021F2D00 -> Sandman block 0x021F34BE (shared with A-Team 0x183A): opp test, bl 0x02022FDC (Trap) @0x021F34D2, 0x021F06E8. Spell test 0x02022FC8. Unlisted cid -> return 0.
- Lists holding 0x2264: arm9 Quick-Effect 0x0209C118 (0x76), KM set 0x0209CCD8 (27), ov3 0x0228EF48 (0x1F), ov3 0x0226D8B0 (dead gate), ov3 0x0226D978 (Trap list — 3DS excludes Wall).
- KM set code 0x46 thunk 0x02023D94, list 0x0209CCD8, phantoms 0x0F80/0x2349/0x2444. Corepanel 0x213D NOT in it.
- Dark Rabbit 0x1126 donor_scan CLEAN; name slot 11 B / desc 77 B (e) -> CARD_TEXT path.
- 3DS: Wall rows == Sandman rows except cid; cond 0x480C78 Wall case 0x481C54 bl 0x1CAD00 (type==0xD) vs Sandman 0x48157C bl 0x1CBFD8 (type==0xE). Wall not in Trap list 0x6A2558.

## Ruled Out
- Dropping Nega-Ton Corepanel from set code 0x46: it isn't a member.
- Patching block 0x021F34BE in place: shared with A-Team: Trap Disposal Unit.
- Reusing Maryokutai's Spell block 0x021F3446: adds "during opponent's turn" restriction.

## Open Questions
- Is the 0x0228EF48 membership (grown list) what restricts the upkeep reveal picker to Rock? Unproven
  (GDW showed it does nothing for a request-driven discard). Oracle 6 answers it.
- AI (ov5 0x022D3D68) does not know Wall -- deferred.

## Next Experiment
- User in-game test of rom_koaki_meiru_wall.nds, oracles 1-8 in _build_koaki_wall.py docstring.
