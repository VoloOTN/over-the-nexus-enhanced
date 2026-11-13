# Psi-Reflector — findings

Printed text (scratch/ygoprodeck_cache.json): Tuner, Lv1, DARK Psychic, 400/300.
> If this card is Normal or Special Summoned: You can add 1 "Assault Mode Activate", or 1 card that specifically lists "Assault Mode Activate" in its text, from your Deck to your hand, except "Psi-Reflector". You can reveal 1 "Assault Mode Activate" in your hand, then target 1 monster in your GY that specifically lists "Assault Mode Activate" in its text, except "Psi-Reflector"; Special Summon it, and if you do, increase its Level by 1 to 4. You can only use each effect of "Psi-Reflector" once per turn.

**Clauses:**
- **C1:** search on Normal or Special Summon (HOPT). **This session's scope.**
- **C2:** GY revive plus a Level increase. User ruling 2026-09-15: the player picks +1 to +4.
- **C3:** each effect once per turn.

**Donor:** Clown Zombie 0x1008 (user's choice 2026-09-15). Plan: `~\.claude\plans\psi-reflector-parallel-ladybug.md`.

## Confirmed (2026-09-15, read-only scans of base EU ROM)
- **No 3DS reference.** The 3DS build does not ship Psi-Reflector: a CARD_Name_E scan finds no "Psi-Reflector".
- **The AMA group.** 12 NDS cids, from the ygoprodeck desc containing "Assault Mode Activate", plus AMA itself:
  - AMA 0x1F7A
  - Assault Mode monsters 0x1F47, 0x1F51, 0x1F52, 0x1F53, 0x1F9B, 0x1FCA
  - Arcane Apprentice 0x1F54, Assault Mercenary 0x1F55, Assault Beast 0x1F56, Night Wing Sorceress 0x1F57
  - Assault Revival 0x1F70
- **Set-code walk** (0x0209D0D8, standard 16 B thunks, `donor_scan.cards()` as the real-card set):
  - 0x40 = the 6 /Assault Mode monsters.
  - All-phantom lists: 0x28 (2 entries), 0x2A (4, Hanzo), 0x4B (6, has criteria rows aux 0x4B), 0x5C (19, T.G.), 0x6E (4 @0x0209C5CA, thunk-shape standard).
  - 0x6E and 0x28 have **no** criteria rows with that aux.
- **Stock criteria rows for AMA cards:**
  - Arcane Apprentice `{0x1F54, 0x1F7A, 0x0223D075, 0x0E}`
  - Assault Mercenary `{0x1F55, 0x1F7A, 0x02240F9D, 0x0E}`
  - Assault Teleport `{0x1F6F, 0x40, 0x0223CB39, 0x02}`
  - Assault Revival `{0x1F70, 0x1F7A, 0x0224102D, 0x0E}` and `{0x1F70, 0x40, 0x0223EF09, 0x10802}`
- **Donor data.** `donor_scan 0x1008` says Clown Zombie is Normal / Lv2 / DARK / Zombie / 1350/0, pack 46, verdict ENTANGLED with 10 binding occurrences (classification below).
- **0x1008 HAS NO PER-CID GATE.** All 12 occurrences were classified by disassembling each use site. The script is `scratchpad/classify_1008.py`: find every PC-relative ldr that loads the literal, then disassemble around it. It also found no mapped-struct key hits (`structs: []`).
  - **ov3 0x0228F994 (u16):** the low half of ARM instruction `e59f1008` = `ldr r1,[pc,#8]`. An instruction encoding, not a cid.
  - **ov3 0x0223DE20, 0x0223E7DC, 0x0223F4A4 (u32):** three sibling criteria-handler bodies, e.g. 0x0223DE04: `ldr r0,[row,#8] ; str r0,[sp] ; ldr r0,=0x1008 ; str r0,[sp,#4] ; ldrh r1,[row] ; bl 0x0223C4E8`.
    - 0x1008 is the 6th argument to the shared counter 0x0223C4E8, a zone/location mask.
    - 0x0223DE05 is the "Normal Monster in GY" handler used by Azure-Eyes clause 3 (`counter.normal_monster_gy_row`). Not a cid.
  - **arm9 0x02056788, 0x02056958, 0x02056C10, 0x02056D14, 0x02056E88, 0x02057CC8 (u32):** all used as a struct OFFSET, e.g. `ldr r0,=0x1008 ; str r2,[r1,r0]` (0x02056C3C) and `ldr r0,[r5,r0]` (0x02057C54). A state-machine field in a non-card subsystem. Not a cid.
  - **arm9 0x020A175C, 0x020A1894 (u16, advisory):** halves of `0x100A1008` (data) and `0x04001008` (the DS sub-engine BG0CNT MMIO address in an I/O register table). Not a cid.

- **Set code 0x6E = "Meklord Army".** Slot 0x0209D290 holds thunk 0x02024089.
  - The thunk at 0x02024088 is standard: `ldr r1,=0x0209C5CA ; ldr r3,=0x02022E15 ; movs r2,#4 ; bx r3`. The list-base literal is @0x02024090 and the count immediate @0x0202408C.
  - Members {0x250B, 0x250C, 0x250D, 0x2532} = 3DS Meklord Army of Wisel/Skiel/Granel and The Resolute Meklord Army. No card_prop record for any of them in the NDS.
  - It is identical in rom.nds and the chained rom_all_patches.nds, so no shipped patch touched it.
  - No criteria row has aux 0x6E, and no ov3 pointer references the thunk or list.
  - The only aligned pointer to the thunk is its own table slot.
  - Zero `movs r1,#0x6E` within 16 B of `bl has_set_code` in arm9 or ov3. (Scan: scratchpad/psi_checks.py.)
- **Set code 0x6F shares 0x6E's list.** Its thunk is at 0x02024098 (non-standard, `push {r4,lr}`, multi-list). Its OWN literal @0x020240D0 also = 0x0209C5CA, count 3 @0x020240C2.
  - So repointing ONLY the 0x6E literal @0x02024090 leaves 0x6F reading the untouched stock list.
  - Do NOT move or overwrite the list bytes at 0x0209C5CA.
- **The "You can" tag 0x021E51E5 wraps 0x021E50DD.** Disassembled 0x021E51E4: `push {r3,lr}; ldr r3,=0x021E50DD; ldr r2,=0x021E51E5; cmp r3,r2; bne -> bl 0x021E50DC; pop {r3,pc}`. The literals differ, so it always calls 0x021E50DC and returns its r0.
  - Its return value equals Accel Stardust C1's TAG_BODY 0x021E50DD, where 1 == yes (in-game confirmed 2026-09-14).
  - So the HOPT +10 stub can call 0x021E51E5 and stamp on r0 == 1.
- **Count-neutral drop phantoms.** Each is absent from card_prop, unclaimed in every PHANTOM_CLAIMS pool, and present with the same row count in BOTH rom.nds and rom_all_patches.nds (scratchpad/psi_checks.py and psi_checks2.py):
  - **code-7 list 0x0228F7AC:** 0x0E7F. Free alternatives 0x19C0, 0x19D3. Tour_guide took 0x0E7E, boggart 0x0E74, hanzo 0x14CC, mathematician 0x15D0.
  - **code-9 list 0x0228F63A:** 0x167C (3DS = Dark Magician Knight). Free alternative 0x1ABF. Hanzo took 0x0E12.
  - **cls1:** 0x0E38. One cls1 row, no row in any other table.
  - **criteria:** 0x0E75. One row `{0x0E75, 0xFFFF, 0x0223CA11, 0x38000002}`; its only other row is one cls0 record, which is untouched. The strict "no other-table rows" filter found NO criteria candidate, so this relaxes it.
- **Tuner identity precedent.** Assault Synchron / T.G. Striker / Unknown Synchron (Normal donors) set `card_type=ERA2_CARD_TYPE_REVERSE["Tuner Monster"]` (33) via `apply_stats_and_text` with no card_genre edit.

## Ruled Out
- **0x5C: the T.G. set code**, consumed by tg_striker/warwolf/rush_rhino/hyper_librarian. Not reusable.
- **0x2A: claimed** by ninja_grandmaster_hanzo PART A.
- **Writing the 12-cid group in place.** No inert list is 12 or longer. The list must be relocated, via a thunk repoint to ov5.
- **A Hanzo C2-style row selector.** Not needed: Normal and Special Summon use the same row.

## C2 (started 2026-09-15): reveal AMA in hand, target a group monster in GY, SS it, Level +1..4 (player picks)
**Sub-parts:**
- **C2a:** ignition, HOPT, a separate counter from C1.
- **C2b:** cost = reveal AMA 0x1F7A from hand.
- **C2c:** GY target in the group.
- **C2d:** Special Summon it.
- **C2e:** Level +N, N in 1..4 chosen by the player.

**Precedents found by grepping ygoprodeck text x the NDS cid list** (records dumped from base-ROM ov3):
- **Koa'ki Meiru Urnight 0x21BC** — "Once per turn, you can reveal 1 'Iron Core of Koa'ki Meiru' in your hand to Special Summon 1 Level 4 or lower 'Koa'ki Meiru' monster from your Deck". Ignition + reveal-by-name cost + SS.
  - cls3[637] = {0x02206CAD, 0, 0x021F0BDD, 0x021EAAA1, 0}.
  - Criteria rows 1085 {0xFFFF, 0x02241471, 0x60000002}, 1086 {0x46, 0x0223CAB5, 0x00900022}, 1087 {0x200F, 0x02241769, 0x0E}.
- **Assault Revival 0x1F70** — "Special Summon 1 '/Assault Mode' monster from your Graveyard, ignoring its Summoning conditions".
  - cls0[1020] = {0x0222B4E5, 0x021D86B9, 0x021FFC25, 0x021E5319, 0x02235605}.
  - Row 818 {0x1F7A, 0x0224102D, 0x0E} (banish AMA from GY); row 819 {aux 0x40, 0x0223EF09, 0x00010802}.
  - **Lead:** 0x0223EF09 is a GY selector keyed by set-code aux; aux 0x6E would give our group. UNVERIFIED: word bit meanings (0x10000 = ignore summoning conditions?) not yet proven.
- **Spore 0x225B** — SS itself from GY and increase its Level. cls2[561] = {0x0220731D, 0, 0x021F0BDD, 0x021E5319, 0}, row 1148 {0xFFFF, 0x0223FE41, 0x68000002}. The Level-increase code lives in resolver 0x0220731C (UNVERIFIED).
- **Reasoning 0x159A** — "Your opponent declares a monster Level from 1 to 12". A number-declare UI exists. cls0[392] = {0x02216375, 0, 0x021F64F1, 0, 0}.
- **Delta Flyer 0x22F3** — increase a Level by 1. cls3[700] = {0x022087B5, 0x021DCD49, 0x021F01C1, 0x021E5061, 0x02234D8D}.

**Proven this session by disassembly** (scratchpad/thumbdis.py over the committed ov3 oracle):
- **Reveal cost 0x021EAAA0 (Koa'ki family).** A state machine on [0x0229AAFC+0x7C].
  - Entry cid switch sets r4 = 1 ("auto-pick, no UI") ONLY for 0x2021 Reckoned Power, 0x2022 Automatic Laser, 0x2096 Core Compression, 0x20AC Iron Core Luster, 0x21BC Urnight, 0x23AD Koa'ki Ring.
  - **Any other cid, e.g. our donor, takes the UI path.** State 0: prompt 0x0219A818(side, 0x155), then 0x0224B9F0(side, cid, param 0 @0x021EAB56, callback 0x022065F9); state++. State 1: 0x0224BBB0 wait → state 2 or back. State 2: ref = hand[[0x0229DE14]] → desc[+0x14]; **0x021D2598(side, ref) = the reveal**. Then cid 0x202B → 0x021CF658, cid 0x21BC → 0x021E5060(desc, r7), **any other cid → return 1**.
  - So for 0x1008 it is "player picks 1 hand card passing the row, it is revealed". Native, no stub.
- **Target declare +14 0x02235604 uses its OWN state word 0x0229AB7C, not +0x7C.** The activation machine zeroes BOTH ([0x0229AAFC+0x7C] @0x02217FBA, [0x0229AB7C] @0x02217FBC) right after the cost, so an arm keyed "cls3 && [0x0229AAFC+0x7C] != 0" is the hand/reveal row, and "cls3 && == 0" is the GY row (offer check, target declare, resolver). This is Upstart Golden Ninja's in-game-confirmed discriminator (`dispatch.cost_machine_state_is_the_row_discriminator`).
- **cls3 +0C 0x021F0BDD** is a cid-keyed table lookup (0x0226FAFC x 0x92, stride 12, two fn ptrs) and returns 0 for an unlisted cid. So the donor needs its own cave condition (HOPT + AMA-in-hand + GY-candidate count), as UGN / Mystic Piper did.
- **The option prompt 0x0219ABB4 is a FOUR-option menu, not two.** Labels = r2, r3, caller [sp], caller [sp+4]. The mask is caller [sp+8], bits 0..3, and a 0 label clears its bit. It loops `cmp r3,#4` @0x0219AC60 writing 4 entries into 0x02299458. The CPU path goes via 0x0226ABF8. The answer is at [0x0229DD94+0x34], 0-based.
  - Accel Synchron clause 2 (in-game confirmed 2026-09-03) calls it with [sp] = 0x01AC as a THIRD option label, not a title.
  - So "+1/+2/+3/+4" is one native prompt IF four label text IDs reading 1..4 exist. **UNFOUND**: the label strings are not plain latin-1/UTF-16 in any ROM file.
- **Level delta** = rider `0x021C479C(side, zone, key 0x22EB, kind 3, [sp] = value)` — `dispatch.level_rider_key_is_a_selector`, VERIFIED, in-game via Accel Synchron C2. Any other key is silently ignored.
- **Number-declare family 0x0225985C(side, type, cid, 0)** has 20 type wrappers 0x022598A0..0x02259C34. Reasoning uses 0x02259C1C (type 0x13) and reads the answer at [0x0229DE94+6] in phase 0x7F. Range control is UNKNOWN, so this is not the preferred route.

- **GY target row handler 0x0223C9ED** = "target 1 <set code> monster in your GY; Special Summon it".
  - Thunk: 0x0223C4E8(side, cid, predicate 0x0223C825 has_set_code(aux), [sp] word, flags 8 = action SS per `dispatch.criteria_handler_flags_word`).
  - 50 rows, e.g. Rite of Spirit 0x15AC {aux 0x02, 0x10002} "Target 1 Gravekeeper's monster in your GY; Special Summon that target"; Lumina 0x1DAA {aux 0x33, 0x910002}.
  - The word histogram is dominated by 0x10002 (27 rows).
  - **C2 row:** {0x1008, aux 0x6E, 0x0223C9ED, 0x00010002}.
- **Template cls3 = Lumina, Lightsworn Summoner 0x1DAA** ("Once per turn: You can discard 1 card, then target 1 ... in your GY; Special Summon that target").
  - cls3[397] = {0x02207191 GY revive, 0, 0x021F0BDD, 0x021E4ECD discard cost, 0x02235605 target declare}.
  - Jurrac Aeolo / Iron Chain Repairman share it with other costs at +10.
  - 0x02207190's unnamed-cid leaf is `resolver.gy_revive_default_leaf` (VERIFIED).
  - **C2 cls3:** {0x02207191, 0, CAVE cond, CAVE cost → 0x021EAAA1, 0x02235605}.
- **Reveal row = Urnight's Iron Core row with aux → AMA:** {0x1008, aux 0x1F7A, 0x02241769, 0x0E}.
  - 0x02241768 calls the HAND worker 0x0223BFD4(side, cid, param = HAND INDEX, [sp] &aux, word, flags 0x20) with name predicate 0x0223C6F1.
  - 0x0223BFD4 indexes player+0x124 + param*4, so param is a candidate index, consistent with the UGN KB fact.
  - The send-from-hand sibling 0x0223CB64 uses flags 0x11 and no predicate.
- **Hand scan offsets for a cave condition:** count = player+0x0C (0x021EAB40); cards = player+0x124 + i*4, cid = word & 0x3FFF (0x021EAB92..9E).
- **Cost return protocol:** 0x021EAAA0 returns 0 while pending and 1 when revealed (state-2 tail). The activation machine at 0x02217FA6 treats 0 as "pending", >0 as "done", <0 as "abort". So a HOPT cost stub posts the turn log only when the native returns 1.

**PROPOSED ROWS for 0x1008:**
- rel 0: C1 deck search (shipped). Read when desc[+5] != 3.
- rel 1: C2 GY target. Read when desc[+5] == 3 and [0x0229AAFC+0x7C] == 0 (menu offer, target declare, resolver).
- rel 2: C2 reveal. Read when desc[+5] == 3 and [0x0229AAFC+0x7C] != 0 (the reveal picker).

This needs a criteria_row_hook.ARMS entry in the Upstart Golden Ninja / Accel Stardust style.

- **Post-summon follow-up = Call of the Haunted / Premature Burial resolver 0x02207528** (`summon.ss_placed_before_next_resolver_phase`, VERIFIED).
  - Phase 0x80: 0x021D28A4 (chain push, no args), 0x02204730(desc, 1, pos); nonzero → return 0x7F, else 0x021D2964 (pop) and 0.
  - Phase 0x7F: ref = 0x02234964(desc, 0); loc = 0x021A241C(ref) → (slot<<8)|side, or -1 (0x021A2470 `movs r0,#0; mvns`). It acts only if slot byte < 5, then returns 0x64.
  - Phase 0x64: 0x021D2964, return 0.
- **Number picker = the native "decrease Level by N" resolver 0x0222C270.**
  - Phase 0x80: `0x0219AE10(desc[+2], desc cid, title 0x16A, item 0x11B '%d', [sp] min 1, [sp+4] max 2)`, return 0x7F.
  - Phase 0x7F: `0x021C479C(side, zone, key, 3, [0x0229DD94+0x34])`, so the answer slot holds the chosen NUMBER.
  - 0x0219AE10 stores side at [0x0229DD94+0x30] and passes min/max through to 0x0219AE30.
  - The counter picker 0x021EB9B4 uses the same call with title 0x13D / item 0x13E.
- **dlg_text_e.bin** (bin2.pac, dlg_indx_e = u32 offsets) decoded:
  - 0x16E "Increase the Level of the @3monster@0." — our title
  - 0x11B "%d" — our item label
  - 0x155 "Select the @3card(s)@0 to show your opponent." — the reveal prompt 0x021EAAA0 uses
  - 0x103 "Use which effect?"
  - **No new text needed.**

## C2 PRE-BUILD CHECKLIST (2026-09-15)
1. **Per-cid gates on 0x1008: PROVEN none** (C1 classification). The reveal cost switch 0x021EAAA0, target declare 0x02235604 and resolver 0x02207190 cid trees do not list 0x1008, so the default arms are taken. For 0x02207190 / 0x02235604 this is by the KB default-leaf facts plus the listed literals.
2. **Zones: PROVEN.**
   - Reveal: hand, enforced by callback 0x022065F9 `cmp r1,#0xB` (`dispatch.selection_param_and_zone`).
   - Target: GY, handler 0x0223C9ED with flags 8.
   - Summon: 0x02204730 generic revive.
3. **Text: PROVEN.** CARD_TEXT[0x1008] already carries the full printed C2 text.
4. **HOPT stamp: PROVEN site.** The cost stub posts turn log (desc[+2], 0x1008, kind 2, 0) only when 0x021EAAA0 returns 1. The cond stub queries kind 2. Kind 1 = C1 (separate counter, as printed).
5. **Row discrimination: PROVEN by precedent.** Arm keyed desc[+5]==3 and [0x0229AAFC+0x7C] (UGN / Jet Synchron, in-game confirmed). The target declare's own state word is 0x0229AB7C, zeroed with +0x7C @0x02217FBA/0x02217FBC.
6. **Phantoms** (unclaimed, same counts in rom.nds and rom_all_patches.nds):
   - cls3 0x0E40 (whole phantom: its criteria row is dropped too)
   - criteria 0x0E40 and 0x0E3A (0x0E3A's orphan cls2 record untouched)

**PLAN — slots claimed:**
- **Criteria rows,** appended AFTER C1's row:
  - rel 1: {0x1008, aux 0x6E, 0x0223C9ED, 0x00010002}
  - rel 2: {0x1008, aux 0x1F7A, 0x02241769, 0x0000000E}
- **cls3:** {0x1008, 0, CAVE_PSI_C2RES, 0, CAVE_PSI_C2COND, CAVE_PSI_C2COST, 0x02235605} over 0x0E40.
- **criteria_row_hook.ARMS:** 0x1008 (guard r5 == 0x1008): desc[+5]==3 → (+0x7C != 0 ? rel 2 : rel 1), else native.
- **ov5 stubs:**
  - C2COND = turn-log kind 2 clear, AMA 0x1F7A in hand (direct scan of player+0x124 x [+0x0C]), tail 0x021F03B5 (Rite of Spirit / Accel C1 GY-candidate condition).
  - C2COST = 0x021EAAA1; on r0 == 1 post turn log.
  - C2RES = CotH phases 0x80 / 0x7F (picker 1..4) / 0x7E (rider 0x22EB kind 3 on loc) / 0x64.

**Row-hook re-home (2026-09-15):**
- **Why:** the first C2 build aborted on `R row hook is 284 B > the 0x100 reserve`. Without the Psi arm the stub is 244 B; a trimmed arm still made 276 B. CAVE_DF_STAGE sits at old + 0x100, so it can't grow in place.
- **Done:** re-homed CAVE_ROWHOOK 0x0239C5A8 → 0x0239F6F8 (reserve 0x180, criteria_row_hook.RESERVE); the old slot is CAVE_ROWHOOK_OLD, RETIRED. Same precedent as the 2026-08-18 lift from CAVE_LP_ROWHOOK.
- **Proven by execution:** `python -m scratch.rowhook_equiv` runs the OLD 6-arm stub @old address against the NEW 7-arm stub @new address.
  - 80,640 inputs (cid x zone x event x class x pass x DF stage x UGN probe x cost state x ASSD stage).
  - Only 0x1008 differs. Shipped arms 0x0FB1, 0x1646, 0x1464, 0x224C, 0x11A3, 0x126F are unchanged (exit + r4).
  - 0x1008: cls3 → rel 1 at cost-state 0, rel 2 while the cost runs; other classes native.

**User decisions 2026-09-15:**
- /Assault Mode (nomi) monsters are revivable **only if properly summoned**: use the engine's normal legality, word 0x00010002 (Rite of Spirit shape), NOT Assault Revival's 0x10802.
- **All of C2 in ONE build.** Level +1..4 research (label IDs, post-summon hook) comes before any code.

## C2 IN-GAME CONFIRMED BY USER 2026-09-15, AND THE CARD IS SHIPPED
- **Confirmation:** the user's words, in reply to oracle items 11-18 on build 8216a0c6: "Perfect, Ship it".
- **Wired in:** `otn_enhanced/steps.py` STEPS (after Assault Synchron, before WiFi timers) and `_verify_all_patches.SHIPPED`. Not in apply_all_patches, per the 2026-09-14 rule.
- **EE build:** 65/65 steps, `rom_all_patches.nds` sha256 `b3fe4305fe2339a9aafab219b379ad1aa7558abb3f6e0ed85da2ae3a412983c1`.
- **Verify sweep:** 53 passed, 0 failed (patch_psi_reflector PASS).
- ⚠️ **`equiv --all`: [DIFFERS] patch_bulk_ydcs** (deck.pac file 61 @+0x180C).
  - Not caused by this card: neither implementation imports anything edited this session.
  - The last commit 16711f4 added a 'Moja' deck to patch_bulk_ydcs.CHANGES; that is the likely source.
  - **NOT INVESTIGATED** (one card per session). Open follow-up for the user.

## C2 BUILD (2026-09-15)
- **Output:** `rom_psi_reflector.nds`, sha256 `8216a0c6d041905b28143a754b0194cd7b44881b429bd19310278578bb4fa9fa`.
  - BUILD_EXIT 0; verify() PASS for hanzo, accel_synchro_stardust_dragon and psi_reflector.
  - check_allocations OK; author_facts 458 PASS / 0 FAIL.
- **Installed stubs disassembled from the built ROM:**
  - Frames balanced (C2RES `push {r2,r3,r4-r7,lr}` / `pop {r2,r3,r4-r7,pc}`, where r2/r3 only reserve [sp] and [sp+4]).
  - Every BLX literal odd.
  - The picker's stack args line up with 0x0219AE10's `[sp+0x18]` / `[sp+0x1C]`.
- **In-game checklist:** items 11-18 in `_build_psi_reflector.py`.
- **KB added:**
  - `dispatch.option_prompt_is_four_way`
  - `dispatch.number_picker_0219ae10`
  - `dispatch.reveal_cost_ui_path`
  - `dispatch.gy_setcode_ss_handler_0223c9ed`
  - `card.psi_reflector_clause2` (UNVERIFIED)
- ⚠️ **Shared-byte changes that affect the next chain build:**
  - The row-hook stub moved to 0x0239F6F8 and gained the psi arm.
  - The timing stub has the psi arm (from C1).
  - Until rom_all_patches.nds is rebuilt, the sweep's R/T "shared stub present" checks will fail on the OLD artifact.
- **If C2 fails in-game, suspect in this order:**
  1. **No effect offered:** cond stub. Savestate at the menu; read CAVE_PSI_C2COND's inputs: turn log, hand words @player+0x124, GY row count.
  2. **Reveal picker lists wrong cards:** row hook rel 2 / callback param.
  3. **Target picker wrong:** rel 1.
  4. **No number prompt:** the 0x7F locate slot >= 5.

## C1 IN-GAME CONFIRMED BY USER 2026-09-15: all 8 oracles, first test
The user reported "1. Confirmed" through "8. Confirmed" against the in-game test checklist, on sha256 `3877f236…c5c02`:
1. Normal Summon → prompt; only group cards; the pick reaches the hand; Assault Teleport absent.
2. Special Summon → same prompt.
3. Second use in the same turn → refused.
4. Declined → still available that turn.
5. Next turn → offered again.
6. No group card in the Deck → no prompt.
7. Card identity: Psi-Reflector, Lv1 DARK Psychic Tuner, 400/300.
8. Hanzo, Gearframe and Accel Stardust C1 are unregressed.

This also proves:
- A set-code group can be grown past its stock count by repointing the thunk literal into ov5 (`setcode.inert_6e_meklord_army`).
- Gearframe's +10 can be wrapped with 0x021E51E5 plus ARM_JW.

**NOT SHIPPED.** Wiring into steps.STEPS / SHIPPED waits for the user's explicit ship decision.

## Build (2026-09-15)
- **Code:**
  - `otn_enhanced/cards/psi_reflector.py`
  - `_build_psi_reflector.py`, which applies Hanzo + Accel Stardust + Psi-Reflector onto the clean ROM
- **Output:** `rom_psi_reflector.nds`, sha256 `3877f2362ddc198442f68393d333696ec945236b017e56aaf34a0c79d47c5c02`.
  - BUILD_EXIT 0; verify() PASS for all three modules.
  - check_allocations OK; author_facts self-check 454 PASS / 0 FAIL.
- **Installed stubs, disassembled from the built ROM:**
  - `pop {r4,r5,pc}` (no POP-into-LR miscode).
  - Every BLX literal is odd: 0x021A14E9, 0x021F0821, 0x021E51E5, 0x021D2585.
  - The group list is the 12 sorted cids.
  - The 0x6E thunk = `ldr r1,=0x0239F510 ; ldr r3,=0x02022E15 ; movs r2,#12 ; bx r3`.
  - The 0x6F literal is still 0x0209C5CA.
- **Shared-file edits** (not wired into STEPS/SHIPPED):
  - `timing_class_hook.ARMS` gets the appended arm `(0x1008, ARM_JW)`. The shared stub is now 132 B.
    - ⚠️ The next EE chain build's bytes will differ from the frozen baseline because of this arm. The arm is inert without Psi-Reflector's records.
    - The sweep's `T the shared stub is present` check on the OLD rom_all_patches.nds will fail until it is rebuilt.
  - The `card_text.CARD_TEXT[0x1008]` entry is written only by this module. No chain step iterates CARD_TEXT (checked steps.py / build.py).
  - `ov5_cave.py`: CAVE_PSI_GROUP / CAVE_PSI_COND / CAVE_PSI_SLOT4; CAVE_FREE moves to 0x0239F588.
  - `check_allocations.PHANTOM_CLAIMS`: donor, c7 0x0E7F, c9 0x167C, cls1 0x0E38, criteria 0x0E75, setcode_index 0x6E.
- **KB facts added:**
  - `setcode.inert_6e_meklord_army` (VERIFIED)
  - `dispatch.you_can_tag_wraps_50dd` (VERIFIED)
  - `donor.clown_zombie_1008_no_cid_gate` (VERIFIED)
  - `card.psi_reflector_clause1` (UNVERIFIED)

## Open Questions
- Using it as Synchro Tuner material was not in the test list. Card_type 33 is precedent only for Tuner behaviour.
- **C2 (GY revive, Level +1 to +4, the player picks):** the next session's clause.

## Next Experiment
- User decision: ship C1 (steps.STEPS + SHIPPED + the EE build/sweep), or start C2 first.
