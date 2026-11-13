# Phoenix Gearblade -- findings (live)

Text (user-supplied 2026-11-06; NOT in scratch/ygoprodeck_cache.json, 3DS check waived by user):
> "Equip only to a Warrior or FIRE monster. It gains 300 ATK. At the end of the Damage Step, if the equipped monster
> attacked: You can send this card to the GY; during this Battle Phase, each of your Warrior monsters and FIRE monsters
> can make a second attack. If this card is sent to the GY, or banished, to activate a monster effect: You can add this
> card to your hand. You can only use this effect of "Phoenix Gearblade" once per turn."

Clauses: C1 equip gate Warrior|FIRE; C2 +300 ATK; C3 EoDS optional trigger, cost = send self to GY, grants 2nd attack to all
your Warrior/FIRE monsters this Battle Phase; C4 sent/banished as cost of a monster effect -> add to hand, HOPT.
Scope: whole card (user, 2026-11-06). Status: DONOR NOT YET CHOSEN, no code written.

## Confirmed (this session, static)
- Double-attack grant is a BOOLEAN, chain tail 0x021A3EC0..0x021A3F20 in ov3 = flat `0x021A1430(side,zone,key)` rider tests
  (KB rider.two_walker_families / continuous_riders). A per-monster rider (kind<6, duration nibble 0 = this turn) read by a
  new link in that tail = "second attack". Disassembled this session (tail ends 0x021A3F78).
- Equip-legality arms: Equip Spells with their OWN arm (x1 in equip_tree emulation) and <=2 binding hits (scan 2026-11-06):
  Beast Fangs 0x10DA (arm 0x021D7F06), Steel Shell 0x10DB (0x021D7F6C), Dragon Treasure 0x10E1 (0x021D7EC8),
  Invigoration 0x10EA (0x021D7F64, attribute arm), Mystical Moon 0x10E5 (0x021D7EEE). Burning Spear 0x12EE lands in the
  SHARED FIRE arm 0x021D7F74 (x2): `ldr r1,[sp,#4]; movs r2,#4; b 0x021D7C76` -> helper 0x021B938C(r0=cand,r1,r2=attr bit)
  returns (mask>>r2)&1. A Warrior|FIRE gate needs an own arm; never edit a shared arm.

- DONOR APPROVED by user 2026-11-06: Invigoration 0x10EA; second attack = snapshot riders (user: "snapshot is enough").
- Invigoration vetting (static, this session): donor_scan -> 1 binding hit = equip grant row[22] @0x0226E034 = {0x10EA,+400,-200}
  (edit to +300/0). Own legality arm = 0x021D7F62: `adds r0,r6,#0; ldr r1,[sp,#4]; movs r2,#5; b 0x021D7C76` (EARTH test
  via helper 0x021B938C; attr index FIRE=4 per Burning Spear arm 0x021D7F74). Only 8 bytes before the next arm.
- Race gate shape PROVEN by Pestilence arm 0x021D7F44: `ldr r0,[sp,#0x10]; lsls r1,r4,#N; tst r0,r1; bne accept(0x021D8178)`,
  r4==1 at arm entry, [sp+0x10] = race bitmask from 0x021B8D90 (set @0x021D7382). Warrior = bit 15 (0xF) -- Pestilence's bits
  {0xF,0xC,0x12} = Warrior/Beast-Warrior/Spellcaster. Epilogue 0x021D817A = `add sp,#0x1c; pop {r4-r7,pc}` returns r0.
  PLAN (unbuilt): `bl stub` over 0x021D7F66 (4 B); stub = race-bit-15 test, else helper(r6,[sp+4],4), ends `ldr r1,=0x021D817B; bx r1`.
- EoDS walker 0x02251D08 (disassembled this session): per battle participant r4, walks its attached links of kind 0xA/0xC
  (equip links, node@0x0229D33C), cid r6 = 0x021A36EC(side,zone) of the equip, then a compare tree on r6 (first compare
  `ldr r0,=0x1C8C; cmp r6,r0` @0x02252210, flags consumed by bgt @0x02252214). Arm 0x02252262 -> 0x02252390 =
  `0x021D3230(side=r7, loc=[sp+0xC], 0, 0)` UNGATED post to the equip (Ancient Gear Fist 0x1ABC, Double Tool 0x200D, Rocket
  Pilder 0x21D6, 0x24A1, Molting via slots). Pool words decoded: 0x1C8C, 0x143A, 0x1ABC, 0x200D, 0x21D6, 0x24A1.
  PLAN (unbuilt): BL-front at 0x02252210 -> if r6==0x10EA jump 0x02252262 else displaced ldr/cmp; equip's own cls1/cls2
  record then needs `attacked` test = rider 0x2092 present on equipped monster (KB battle.attacked_marker_rider) -- UNPROVEN.

- C3 TRIGGER SIDE (static, this session): walker 0x02251D08 has exactly 2 callers, @0x02252712 `movs r0,#1; bl` (ATTACKER pass,
  always runs) and @0x02252722 `movs r0,#0; bl` (DEFENDER pass, only if byte [glob+2]==0). Arg is [sp+4]; r3 = battle side
  = [glob+0] when arg!=0 else 1-[glob+0]. Equip arm 0x0225225C = `if [sp+4]==0 skip(0x02252276) else fallthrough 0x02252262
  -> 0x02252390 post 0x021D3230(side, loc, 0, 0)` => routing 0x10EA to 0x0225225C (NOT 0x02252262, which is ungated) posts
  only for an equip on the ATTACKER = "the equipped monster attacked". Still unproven on the live path (no GDB/savestate).
- C4 COST PROVENANCE (static): field->GY primitive 0x021CF658(side,zone) = 0x021CDD4C(..,0xE, kind 0x1000); 14 BL callers:
  cost region 0x021E50D4,6C3A,6CD8,762E,7770,96DA,97DC,9AC6,A704,ABCA (10) + effect/other 0x220A89A,0x224ECBA,0x22589AC,0x2261C12.
  Cost sites are generic dispatch (r5/r4 = effect desc; some = "send THIS card" [desc+2/+3], 0x021E96CC reads a picked-card
  global). The leave dispatcher 0x021C7FCC carries NO cost flag in the packed descriptor ([sp+0x200] bits: 9 side, 10-13 zone,
  15 destroyed, 16 battle, 19-22 dest, 23 hidden; arg3 [sp+0xC] bits 18/20 only).  UNPROVEN: how to know the activator is a
  MONSTER at 0x021CF658 (desc not passed), and which mover is field->banished as cost.

- TRACE A (emulator CPU, not user-confirmed; scratch/gearblade_cost_trace.py, 1 breakpoint @0x021CF658, interpreter+GDB):
  sd19_dragunity vs wcs025_bamboo, duel finished, **0 hits** -> neither deck ever called the field->GY mover. Uninformative
  for C4 (no cost send of a field card happened); NOT a proof the breakpoint is wrong (no positive control run yet).
- Pool check (user suggestions 2026-11-06): Icarus Attack 0x1A35 (Trap: tribute 1 Winged Beast), Offering to the Snake Deity 0x1D34
  (Trap: destroy own Reptile + 2 cards -- a destroy, not a cost), Fortune Lady Dark/Earth/Fire/Light/Water/Wind 0x20FE/20FF/206E/206D/20FD/20FC
  (NONE pays a field send/banish cost; Past/Every/Rewind/Calling are not in the pool). All Spell/Trap or cost-free monsters.

- TRACE B (emulator CPU, not user-confirmed; `gearblade_cost_trace.py mirror`, 4 duels one session, BP 0x021CF658 only; deck =
  Gravekeeper's Descendant/Cannonholder/Curse/Guard/Assailant x3, Panther Warrior x3, Icarus Attack x3 + Lightsworn filler):
  **4 hits, ALL from BL @0x0224ECBA** (LR 0x0224ECBE; side 1, zone 2; sent cids 0x158D x2, 0x1DA7, 0x1DA9; no activator desc in
  r4-r7). 0x0224ECBA is in the "effect/other" group, NOT the cost region 0x021E50D4..0x021EABCA: it sits in an FSM arm
  (`bl 0x0224BBB0; beq; ldr r1,[0x...]; ldr r2,[r6,#0x7C]; ldr r0,[r6,#0x78]; adds r1,r2,r1; bl 0x021CF658`, r6 = FSM scratch).
  Per-card stats (rig save): Descendant drawn 7/summoned 0/activated 0; Cannonholder 9/0/0; Panther Warrior 5/4/0; Icarus Attack
  7/0/0 -> the CPU never summoned Descendant/Cannonholder and never played Icarus, so NO cost-region site was exercised.
  The 4 hits are probably a tribute (Summon or Panther Warrior's tribute-to-attack) -- UNPROVEN which. C4 still unproven.

- C4 RESEARCH 2 (static, this session; user pointed at Gearfried / Medraut / Seven Swords Warrior):
  * Tribute-cost tag +10 0x021E7C89 (Descendant 0x21BF cls3[638], Cannonholder 0x158C cls3[110], Icarus 0x1A35 cls0[718]) calls
    0x021CF68C, NOT 0x021CF658. Both are kind 0x1000 = TRIBUTE reason (KB leave.tributed_reason_bit), blank 0x24-byte desc.
    -> trace A/B watched the wrong mover family for these cards. 0x0224ECBA (trace B's 4 hits) = an FSM tribute arm.
  * Kind-0 field sends come in two flavours around the poster 0x021CDD4C(desc,mask,0xE,0): 0x021CF740 / 0x021CF768 ZERO desc[0]
    (`strh r3,[r5]` before the call, restore after) = NOT-BY-EFFECT (cost/rule) -- 8 + 12 callers, almost all in the cost region
    0x021E71xx..0x021EC2FA; 0x021CF72C / 0x021CF75C keep the cid = BY-EFFECT (15 + 8 callers in the resolver region 0x0220xxxx+).
    Convention matches KB leave.* 'cause 0 = cost, >0 = effect' for hand/deck movers. ASSUMED (not executed) that the leave
    dispatcher's r2 ([sp+8], 'by card effect') comes from that cid -> r2 == 0 for a cost send.
  * Activation step machine 0x02217F80 stores the ACTING descriptor at [0x0229A9FC+0x50] in every step incl. cost (slot4, state 0x77)
    (`ldr r0,=0x0229A9FC ; str r5,[r0,#0x50]` @0x02217F88/8C; KB dispatch.* line 1570 uses the same global). u16[desc] = activator cid,
    so 'activator is a MONSTER' = card_type(cid) via 0x0202ABF8 -- PROVEN as a static read, not executed.
  * Field banish as a cost: KB cards.yaml 1126 (Dragon Rulers H8, in-game confirmed 2026-10-19, Redox banished as Sacred Sword's cost):
    queued field banish passes the leave dispatcher 0x021C7FD0 with dest 0xF; hook = BL 0x021C810C (mask-table bsearch) -> virtual
    mask row 0x0004. GY half = dest 0xE, same dispatcher. => C4's TRIGGER half has a shipped, confirmed precedent.
  * Gearfried (shipped, cid 0xFC7) is the ideal live control: C1 banishes an Equip Spell from the field, C3 sends an Equip Card from the
    field via native field cost machine 0x021E712C -- both are MONSTER-effect costs; Seven Swords Warrior 0x23EA 'send it to the GY' and
    Medraut 'destroy 1 Equip Spell' are effect sends = negative controls.
  * DESIGN (unbuilt): leave-dispatcher front (H8 style) fires when cid==Gearblade && dest in {0xE,0xF} && r2==0 && reason lacks
    0x1000 (not tribute) && acting desc [0x0229A9FC+0x50] -> u16 cid is a monster. Then post the same 'to hand' trigger as Maugis/Roland GY
    nodes.  TRACE (running): scratch/gearblade_leave_trace.py = 1 BP @0x021C7FD0 logging dest,r2,r3,card,actor.

- TRACE C (emulator CPU, not user-confirmed; gearblade_leave_trace.py, BP 0x021C7FD0, 6 mirror duels, deck Gearfried/Medraut/
  Black Pendant/Axe of Despair/Lucky Iron Axe/Axe of Fools x3): 56 leaves, all dest 0xE except 5 dest 0xD. MEASURED:
  * r2 is the ACTING CARD'S CID, not a bool: effect destruction shows r2 = actor cid (0x1DAB / 0x1DA8) with r3 = 0x10010003 /
    0x18010003; battle (r3 = 0x7), equip loss (r3 = 0x2580002 / 0x2480002, the Equip going to GY with its monster) and deck
    returns (r3 = 0x10001, dest 0xD) are r2 = 0 where no card effect did it. Confirms the cost-vs-effect convention for EFFECT
    sends; does NOT yet show a cost send.
  * NO monster-effect cost send occurred: Gearfried drawn 5 / summoned 0 / activated 0, Medraut 8/6/0 -> the positive control is
    still missing. [0x0229A9FC+0x50] (acting desc) gave actor cids on every row, incl. stale ones on battle/equip-loss rows
    (e.g. r3 = 0x7 rows carry an actor cid), so the acting desc is NOT cleared between activations -- it must be combined with
    r2 == 0 AND the cost phase being live ([0x0229AAFC+0x7C] state / cost machine), not used alone. UNPROVEN how to test 'cost live'.

- STAGE 1 BUILT 2026-11-06 (C1 equip gate + C2 +300): otn_enhanced/cards/phoenix_gearblade.py + _build_phoenix_gearblade.py ->
  data/over_the_nexus/working/rom_phoenix_gearblade.nds sha256 a91e997cdf1f7170124b6a8822cb7ef008036baf33c2801de1054ce070ee65eb.
  verify(): Gearfried 59/59, Gearblade 6/6 (static: arm BL @0x021D7F66 -> CAVE_PG_EQ 0x023AD520, 36 B stub, grant row {0x10EA,+300,0},
  text in 8 languages). Stub disassembled: ldr r0,[sp,#0x10]; mov r1,#1; lsl r1,#15; tst; bne yes; add r0,r6; ldr r1,[sp,#4];
  mov r2,#4; bl 0x021B938C; ldr r1,=0x021D817B; bx r1 / yes: mov r0,#1; ... Thumb-1 asserted.  AWAITING IN-GAME TEST -- not executed
  anywhere yet (no emulator run of the arm; assumption r4/r6/[sp+4] frame from static read only).
  Note: the chain ROM already carries Gearfried (steps.STEPS), so the build script does NOT re-apply it (first attempt died on
  'ov5 cave 0x023ACF10 is not free').

- STAGE 2 BUILT 2026-11-06 (C3): rom_phoenix_gearblade.nds sha256 0a27dcbf476c85c7c724475b85473c65a4ffb027e76dbc4de8d9e015fa4a11c5,
  verify Gearblade 23/23 + Gearfried 59/59 (static). cls1 {0x10EA, 0, RES 0x023AD620, 0, COND 0x023AD560, COST 0x023AD5C0, RET2} over
  phantom 0x17EA; fronts: EoDS @0x02252210 -> 0x023AD6C0, double-attack tail @0x021A3F20 -> 0x023AD6F0. engine_syms: send_zeroed_cid.
- TRACE D (emulator CPU, NOT user-confirmed; scratch/gearblade_c3_trace.py, 6 mirror duels, rig_rom_phoenix_gearblade.nds,
  deck Gearblade/Headhuntress/Dark Blade/Celtic Guardian/Blazing Inpachi/Great Angus/Queen's Knight x3): Gearblade drawn 7,
  activated 21 (equip activations). Stub hits: EOD 7 (r6 = 0x10EA every time -> the EoDS front IS reached for an equipped attacker),
  COND 14, COST 14, **RES 0**, DA front ~2900 (normal AI polling). So the trigger reaches the cls1 record and the cost stub runs, but the
  resolver NEVER ran: either the CPU answers No to the 'You can' prompt, or the cost stub does not complete. UNPROVEN which. Trace E
  adds a BP on 0x021CF740 (send mover) and on COST's return address to split the two.

- C4 DESIGN v2 (static, 2026-11-06; user added: 'it can also be sent to the GY from HAND by discard like Tribe-Infecting Virus'
  (0x161C, in pool: 'Discard 1 card from your hand and declare 1 Type...' = a MONSTER effect with a hand-discard cost) and
  'many of the Infernobles should be able to trigger it' -> the detector must be GENERIC (any monster-effect cost), not Gearfried-only).
  Three ENTRY PATHS, all measured/read to exist; none built:
  A. FIELD -> GY / banish as cost: leave dispatcher 0x021C7FD0. Arming = the mask-table bsearch BL @0x021C810C (Dragon Rulers' H8 owns it:
     cave3 CAVE3_RUL_H8A 0x02220BCC -> ov5 CAVE_RUL_LEAVE, virtual mask row {0,0x0004}); a Gearblade front must sit AHEAD of H8A and tail-jump
     to it for every other cid (needs an ov5_cave map entry like dc_next + a tolerance in dragon_rulers' site check, which compares the BL
     target exactly: dragon_rulers.py:1425). At the BL the dispatcher's locals are live: [sp+8] = acting cid (0 = cost/rule), [sp+0xC] = reason
     (0x1000 tribute, 0x2000000 equip-loss), [sp+0x200] = packed word (dest = bit 19..22, 0xE GY / 0xF banish), [sp+0x90] destroyed, [sp+0x44] battle.
  B. HAND -> GY as discard COST: 0x021C6DB4 (kind 1 = COST) -> core 0x021C6B00 -> 0x021D1300 with cause r3 = 1 - kind = 0 (KB
     event.dark_world_discard_arm: kind 0/effect > 0 accepted by Dark World's arm 0x021D185C, kind 1 cost = 0 REJECTED there). The
     per-cid chain in 0x021D1300 (simulate 0x021D1392) is cid-hardcoded; a records-free Spell needs the terminal-node hook of
     card.snoww_unlight_of_dark_world. UNBUILT, UNPROVEN.
  C. HAND/GY -> banished as cost: Rulers' H6/H7 hooks (0x021C71C8 worker gate, 0x021D1B98 switch leaf 0x021D1D3E) are the template.
  Then the GY->hand half: a real cls2 record over a phantom + an offer from the GY (virtual GY row table gy_vrow_hook, 16 rows shared with
  the Rulers/Revolution/Infernoble) + resolver 0x02208181 (add target from GY or banished) + HOPT turn-log stamp.
  'Monster effect' filter: acting desc [0x0229A9FC+0x50] cid -> card type monster (acting desc is STALE between activations: use only with
  [sp+8]==0 AND reason bits clear AND the card being a Spell).
  Controls available in the pool: Gearfried 0xFC7 (field banish / send Equip as cost), Tribe-Infecting Virus 0x161C (hand discard cost),
  Gravekeeper's Descendant 0x21BF / Cannonholder 0x158C (tribute, NOT a send -> must NOT trigger), Medraut / Seven Swords (effect sends -> must NOT trigger).

- TRACE E (emulator CPU, not user-confirmed; gearblade_c3_trace.py with SEND + COST-return BPs, 8 duels): EOD 12, COND 12, COST 24 calls
  (COSTRET r0=0 x12, r0=1 x13), **SEND (0x021CF740) of cid 0x10EA x12** (side0 zone7 x7, side1 zone7 x5), RES 0. => the CPU answered YES
  every time, the cost completed and Gearblade WENT TO THE GY via the zeroed-cid mover, and the resolver still never ran.
  ROOT CAUSE (static, NOT yet executed): 0x021EDE48 ('is the effect still valid', called from 0x02218022 right before the resolver) has
  `spell_type(cid) in {2,3}` -> if desc[+5] != 0 (an on-field effect, not the Spell's own activation) return 0 = ABORT unless cid == the
  single literal 0x1909 (Bubble Shuffle, pool 0x021EE08C). FIX BUILT: front @0x021EDED0 (BL over `ldr r0,=0x1909 ; cmp r1,r0`), sets Z for
  0x10EA too (CAVE_PG_VALID 0x023AD730). The same gate would abort C4's GY trigger, so one front covers both. NEXT: rerun the trace.

- TRACE F (emulator CPU; rebuilt ROM sha 29c221b2... with the validity front, rig rebuilt): EOD 16, COND 32, COST 32, COSTRET r0=0 x16 /
  r0=1 x16, SEND of 0x10EA x16, **RES 0 and VALID 0**. The validity front at 0x021EDED0 was NEVER reached, so my 'Equip branch aborts
  the effect' diagnosis is NOT confirmed (the check may return before that branch, or 0x021EDE48 may not even be called for this
  activation). The hypothesis stays UNPROVEN; the front is harmless but unproven. TRACE G (running) logs 0x021EDE48 entry for cid 0x10EA
  (desc bytes) and its return value.

- TRACE G (emulator CPU; BP on 0x021EDE48 filtered to cid 0x10EA): 24 calls, ALL from 0x021D5A82 (return 0x021D5A86), desc[7] (cost_ran) = 1
  in every one (so they are AFTER the cost, Gearblade already in the GY), returns r0 = 1 x12 and r0 = 0 x12; the FSM caller 0x02218022 was
  NEVER hit for 0x10EA. The 0x021EDED0 front stayed unreached because the walk goes `instance-ref compare @0x021EDFB8 fails` (the source
  card left its zone) -> cid tree @0x021EDFC8 -> DEFAULT arm 0x021EE054: valid iff record +10 == 0x021E6FF5 or desc[+5] == 2, else 0.
  Gearblade's cls1 record (+10 = my COST stub, category 1) therefore fails. REVISED FIX BUILT: the VALID front moved to 0x021EE05A
  (BL over `ldr r1,=0x021E6FF5 ; cmp r0,r1`) and accepts r0 == CAVE_PG_C3_COST|1.  AWAITING TRACE H (rig rebuilt for it).
  Second thought: the 0x021ED5A82 caller may be a chain/offer re-check rather than the pre-resolver one; if RES still does not run,
  the next experiment is BPs on the FSM resolution block (0x02217FFC / 0x02218032 / abort 0x0221804E) filtered to cid 0x10EA.

- TRACE H (emulator CPU, NOT user-confirmed; rom sha 8d0d50e075e32cbb75075f6897c43e8f72981263db0214760b1fb920172b92db, verify Gearblade
  26/26 + Gearfried 59/59; rig rebuilt): **RES ran 13 times** (was 0), VALID front hit 13x with r0 = 0x023AD5C1 (= COST|1), every VCHKRET
  r0 = 1 (26/26, was 12/24).  EOD 13, COND 13, COST 26, SEND 13.  => the 'effect still valid' default arm WAS the blocker and the front
  at 0x021EE05A fixes it (emulator).  NOT yet shown: that the riders attach (TRACE I = BP 0x021C479C key 0x10EA + 0x023AD700 DAHIT) and
  that a monster actually attacks twice.

- USER IN-GAME REPORT 2026-11-06 (verbatim): "See .ml3 and .ml4 (before banish and after banish)" then "I banished gearblade for immortals effect.
  I should be allowed to activate gearblade from my banish pile to add it back to my hand".  Savestates data/over_the_nexus/working/
  rom_phoenix_gearblade.ml3 / .ml4 (read with scratch/gearblade_ml_diff.py): BEFORE side0 field = Disguise 0x111E (monster zone 2) +
  GEARBLADE face-up in S/T zone 7, hand = [0x14D0, 0x1E05, GEARFRIED 0x0FC7, 0x0FC1]; AFTER = Gearfried face-up in monster zone 3,
  Gearblade in the BANISHED list, zone 7 empty, hand lost Gearfried. => Gearfried C1 (hand SS, banish an Equip Spell from the FIELD as
  cost): MEASURED path A banish-from-field-as-cost. No recovery prompt = EXPECTED, C4 is NOT BUILT in rom_phoenix_gearblade.nds (sha 8d0d50e0...).
  The user's expectation is exactly the card text clause C4 ('banished ... to activate a monster effect: add this card to your hand').
- NOTE (process hygiene): the user's own melonDS (~\RH\melonDS.exe, started 09:07) was running while my GDB traces ran; my script
  connects to port 3333 and may have attached to THEIR stub (traces F/G died with 'connection closed by stub'). Never Stop-Process anything
  there; a stale melonDS of mine under build\cpu_battery\gdb\ was left holding battery.nds (auto-mode classifier denied killing it).
- C4 BUILD PLAN (templates found, none built): Infernoble Arms E2 = Joyeuse/Durendal/Almace/Hauteclere in infernoble.py: (1) cls2 record over a
  phantom with +0C OPT cond + +04 res (phase 0x80 OPT check+stamp, then Renaud's add-target 0x02208181 for a GY-or-banished target);
  (2) a leave front at BL 0x021C8216 ahead of the chain (ik_next head = CAVE_IK_HA_LEAVE): cid + dest (GY [sp+0x144] / banish dest 0xF) +
  conditions -> Sword of Dark Rites' accept arm 0x021C9334|1 (movs r0,#1 -> post flag [sp+0x18]); else tail-jump to the previous front (lr intact);
  (3) a criteria row naming 0x10EA with GY+banished workers (Almace's _al_count shape) -- the criteria registry is full, so a VIRTUAL row
  (Gearfried's 0xFF20 H2/H3 chain, Disguise/Medraut ahead of it) is needed; (4) the validity front (CAVE_PG_VALID) already accepts category-2
  records (desc[+5]==2) -- no extra work. Cost filter in the leave front: acting cid [sp+8] == 0, reason [sp+0xC] & 0x2001000 == 0, not destroyed
  [sp+0x90], not battle [sp+0x44], acting desc [0x0229A9FC+0x50] cid is a monster.

- STAGE 3 BUILT 2026-11-06 (C4): rom_phoenix_gearblade.nds sha256 5df5b6af9c932eb9df3d56e453ade0f2ed2f8996210bc7b78c3fd929679aa2f8, verify
  Gearblade 41/41 + Gearfried 59/59 (STATIC). Pieces: leave front CAVE_PG_LEAVE 0x023AD8D0 @BL 0x021C8216 (ahead of the Arms chain head
  CAVE_IK_HA_LEAVE; arms via Sword of Dark Rites' accept arm 0x021C9335 when cid = 0x10EA, dest GY/banish, [sp+8]==0, reason & 0x02001000 == 0,
  not destroyed/battle, acting desc [0x0229A9FC+0x50] cid is a monster); cls2 {0x10EA, RES 0x023AD820, COND 0x023AD750, COST 0x023AD7E0
  (dsl._hopt_you_can_stub, key 0x50EA), RET2} over phantom 0x14E7; resolver = native add-target protocol (phase 0x80: chain_open 0x021D28A4,
  gy_to_hand 0x021C7038 / ban_to_hand 0x021C7068 with a POINTER into the list, return 0x7F; phase 0x7F: chain_close 0x021D2964).
  Sizes measured: C4_COND 0x88, C4_RES 0xA0 (slots 0x90 / 0xB0), first build died on 'C4_COND: 0x88 B > 0x60'.
  KB self-check 7 FAIL, all environmental (missing docs/ov3_catalogue/ov3_index.csv, 3DS extract absent, rom_files bytearray note); my 5 new
  anchors are not among them.  AWAITING IN-GAME TEST (user), sweep of all shipped patches running.

- SWEEP 2026-11-06 (-m otn_enhanced.verify): BASELINE chain rom_all_patches.nds = 113 passed / 2 failed (cards.infernoble because of 'ov5 AR_MISS
  @0x23ab4d0 byte-exact', data.bulk_ydcs because wcs084_formula + rpg049_6_nagisa do not match CHANGES -- the user's uncommitted ydc edits).
  rom_phoenix_gearblade.nds (sha 5df5b6af...) = the IDENTICAL 113 / 2. So both failures are PRE-EXISTING, not caused by Gearblade. Two things
  I did cause and fixed on the way: (1) CAVE_PG_LEAVE belongs in ov5_cave.dc_next(), NOT ik_next() (infernoble.verify KeyError); (2) infernoble's
  Hauteclere check now steps over my front with O5.dc_skip. LEAVE_FRONTS in infernoble.py lists CAVE_PG_LEAVE.

- USER IN-GAME REPORT 2 (2026-11-06 ~10:26, verbatim): "I tested see .ml2 and .ml3 it didnt fire", confirmed reading (user: "yes, no prompt appeared"):
  Gearblade banished from the field as Gearfried's C1 cost again; NO recovery prompt at all.  Savestates rom_phoenix_gearblade.ml2 (before) /
  .ml3 (after): side0 field = Killer Needle 0x0FDB (zone 2) + GEARBLADE (S/T zone 7), hand = [0x1F71, GEARBLADE (second copy), GEARFRIED, 0x1E04];
  AFTER Gearfried in zone 3, one GEARBLADE in the banished list, the other copy still in hand, GY empty.
  scratch/gearblade_ml_stubs.py: EVERY current-build stub (EQ, EOD, DA, VALID, LEAVE, C3_*, C4_COND, C4_RES) MATCHES the build and every hook
  site (EQ/EOD/DA/VALID/LEAVE) points at mine in BOTH states -> the user ran the current code; this is NOT the stale-savestate trap.
  Which link broke is UNKNOWN: arming in the leave front, the posted event, the cls2 lookup, or the cond.  Per the two-failed-tests rule
  (escalate to measurement): DIAGNOSTIC build (DIAG = True in phoenix_gearblade.py) writes raw observations to CAVE_PG_DBG 0x023AD9E0:
  +0 dest(GY 0xE / banish 0xF), +4 acting cid [sp+8], +8 reason [sp+0xC], +0xC destroyed, +0x10 battle, +0x14 acting desc ptr, +0x18 acting
  desc cid, +0x20 leave-front hit count (cid 0x10EA only), +0x24 C4 cond calls, +0x28 last cond verdict, +0x2C C4 resolver calls, +0x30 last phase.
  NEXT: user repeats the banish on the DIAG ROM and saves a state; read the words with SaveState.read(0x023AD9E0, 0x40).
  DIAG ROM BUILT: rom_phoenix_gearblade.nds (rebuilt IN PLACE, same filename) sha256 bf2b775a94c217fe5499ee010d728d677d5d90aa946c58198cf62c85dadce06a,
  verify Gearblade 42/42 + Gearfried 59/59.  The user MUST start a fresh duel on it (an older .mlN restores the OLD ov5 code); check a state with
  scratch/gearblade_ml_stubs.py (it compares against the CURRENT build, DIAG included).  AWAITING the user's state.

- DIAG RESULT (user states .ml2 before / .ml3 after, 2026-11-06 11:09, on the DIAG build; breadcrumbs read with scratch/gearblade_dbg_read.py):
  .ml3: leave-front hits 1, dest 0xF, acting cid [sp+8] 0, reason 0x10000, destroyed 0, battle 0, acting desc cid 0xFC7 (Gearfried),
  C4 cond calls 1, verdict 0, C4 res calls 0.  => MEASURED: the leave front ARMS and the cls2 cond IS REACHED (trigger/lookup chain works);
  the cond REJECTED.  Hypothesis (UNPROVEN): the cond's GY/banished scan ran before the card was in the list (event posted inside the move).
  FIX BUILT: cond now only tests the hard OPT (resolver re-finds the card); extra breadcrumbs +0x1C opt_used, +0x38 GY count, +0x3C banished count.
  ROM rebuilt in place, sha256 3eac0c4ecf10d25ad7a346d8fec3cf5e771dc0959d2e7a11f8da109c497ba183, verify Gearblade 42/42 + Gearfried 59/59. AWAITING user retest.

- USER IN-GAME REPORT 3 (2026-11-06, verbatim): "It said I missed the timing for activation!" (on the relaxed-cond build 3eac0c4e...). So the cond now
  passes and the engine reaches the offer, then drops it at the MISS-TIMING test (KB: 'You can' triggers go through 0x021EE0E0, node 0x021EE10C,
  r3 = cid; known trap, same as Arms E2 / Disguise C2).  FIX BUILT: CAVE_PG_MISS 0x023ADA20 front @0x021EE10C ahead of Disguise's (cid 0x10EA ->
  Z set), dc_next entry PG_MISS -> DC_MISS; infernoble.verify's exact-BL check at the miss site now walks dc_skip.
  ROM rebuilt in place sha256 728ebf42f0485d4aabc5aab078275f05558b67871f5885c4d7780f4483528a34, verify Gearblade 45/45 + Gearfried 59/59,
  sweep 114 passed / 1 failed (only data.bulk_ydcs -- the user's ydc edits; cards.infernoble now PASSES). AWAITING user retest.

- SHIPPED 2026-11-06 on user instruction ("Cool it works now, add the card art and ship it"; the in-game report covered the C4 retest on build
  728ebf42...). In-game confirmed by user 2026-11-06: C4 banish-from-field (Gearfried C1 cost) -> add to hand path only. NOT individually
  reported by the user: equip gate, +300 ATK, Damage-Step second attack (rider attach / double attack never observed even in CPU duels).
  Shipped = steps.STEPS "Phoenix Gearblade" (after Immortal Phoenix Gearfried), CardArt(0x10EA) + art copied to card_arts/implemented/, bulk_card_pack
  key "Invigoration" -> "Phoenix Gearblade", DIAG = False. Chain build 125/125, rom_all_patches.nds sha256 08bf8380d1d5d369af726a79cf235c1732b32b8059f6b3a84db1f59160e6c07c,
  sweep 115 passed / 1 failed (data.bulk_ydcs: wcs084_formula, the user's uncommitted ydc edits). Not covered: hand-discard cost (Tribe-Infecting
  Virus), Infernoble costs, cost-vs-effect negative controls.

- IN-GAME CONFIRMED by user 2026-11-06 (verbatim: "I have tested everything and it works") on the shipped chain (sha 08bf8380...c07c): whole card
  (equip gate, +300 ATK, Damage-Step second attack, banish -> add to hand). Still not covered by any test: hand-discard cost (Tribe-Infecting Virus),
  Infernoble costs, negative controls.

## Ruled Out
- (none yet)

## Open Questions
- C3 trigger site: End-of-Damage-Step equip walker 0x02251D08 (Molting Escape's, donor-only compare) -- optional "You can"
  + cost send-self-to-GY not yet traced. UNPROVEN.
- C4 "sent/banished as COST of a monster effect": needs a cost-vs-effect discriminator on the sent-to-GY / banish path
  (Gates of Dark World precedent: kind argument). Banish half unproven. HOPT stamp site unproven.
- Snapshot (monsters you control at resolution) vs. "each ... can" (also monsters summoned later this BP): decide with user.

## Next Experiment
- After donor approval: emulate 0x021D7348 for the chosen donor, trace 0x02251D08 sub-states, find the GY-cost event kind.
