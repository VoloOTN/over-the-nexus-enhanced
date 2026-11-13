# Block Dragon - findings

Card: Lv8 EARTH Rock/Effect 2500/3000 (scratch/ygoprodeck_cache.json, id 94689206).

## Clauses (user confirmed scope = WHOLE CARD, 2026-11-08)
1. Cannot be Normal Summoned/Set. Must be Special Summoned (from hand or GY) by banishing 3 EARTH monsters from hand and/or GY.
2. Rock monsters you control cannot be destroyed, except by battle.
3. If sent from the field to the GY: you can add up to 3 Rock monsters from Deck to hand, total Levels = 8. Once per turn (this effect).

## User rulings
- NDS: card absent. 3DS: card absent too (user, 2026-11-08) -> no Konami handler to copy.
- C3: any 1-3 Rocks whose Levels sum to exactly 8 (user "Yes", 2026-11-08).

## Confirmed (this session)
- No existing Block Dragon patch/notes in repo (grep otn_enhanced + notes).
- donor_scan --free (run 2026-11-08): clean weak EARTH Normal donors, ATK<=1500: Big Insect 0x0FD7, Gokibore 0x0FDC, Giant Flea 0x0FDD (all Lv4 1200-1500).
  Lv8 clean donors are all beaters (BEWD, Tri-Horned...). Only clean Rock Normal = Gem-Knight Crystal 0x249C (2450 ATK, too strong).
  Donor Level/race/attr are overwritten by stats patch; NOT yet checked: per-cid gates, blob lengths (moot if cid joins card_text.CARD_TEXT).

## Donor: Giant Flea 0x0FDD (user pick 2026-11-08)
- donor_scan 0x0FDD: VERDICT CLEAN. Not in steps.py / donor-pool "Used". Lv4 EARTH Insect 1500/1200. desc floor 54 B, name floor 8 B
  (moot if cid joins card_text.CARD_TEXT). 4 ambiguous ARM9 data u16 hits (0x0209D6BE, 0x0209E414, 0x0209E6BC, 0x020A1416) +
  3 code-region hits (ov3 0x02265458, arm9 0x020080F0, 0x020534F2): NOT YET READ BY HAND. Stack-based-switch blind spot unchecked.

## Precedent map (read this session from repo code/notes; UNVERIFIED until executed)
- C1 NS block + hand SS: Grandsoil (otn_enhanced/cards/grandsoil.py, dsl.hand_special_summon_by_gy_attribute): costless hand-SS via the SHARED
  tg_table trampoline (hook 0x0224C026) + ov5 cond stub (free zone 0x021B9ECC && canSS 0x021AD870 && ...); "Cannot be NS/Set" via LIST_NS_OR_SS.
  Grandsoil is NOT in-game confirmed shipped? (its note line 10 says "NOT shipped, not in STEPS" - stale?) -> check before relying.
  tg_table was FULL and relocated 2026-10-05 to 0x023A4E00 (15 rows): need a free row.
  COST (banish 3 EARTH, hand and/or GY): nearest = Gearfried C1 (virtual cls2 hand record + virtual criteria row 0xFF20 picker, banish mover split
  GY/field, Ojamassimilation machine). NEW: hand+GY pick set, 3 picks, exclude self. GY-origin SS: Lightpulsar GY resolver / Revolution virtual GY-action row.
- C2: white_dragon_ninja.py hooks 0x021B07F4 ("may this card effect affect this target" predicate) -- covers ALL card effects (not only opp), exactly
  matches "cannot be destroyed except by battle" semantically (battle destruction is not a card effect). BUT it protects S/T slots 5..0xA; MONSTER
  slots 0..4 go via Safe Zone / Dreadmaster leaf 0x021B05FE (slot split 0x021B059C). Needs a Rock-filter variant for slots 0..4. UNPROVEN.
  Also verify: does it cover destroy-by-effect only, and does "destroyed as cost/tribute" stay legal.
- C3: leave-to-GY any-leave: Darksoul (TREE 2) / GK Recruiter (leave-MASK row, Normal donor). Level-sum Deck picker: nearest = Mara/Wattuna
  level_sum 0x0224966C (Synchro-material machinery, hand/field) -- Deck search with Rock filter + sum==8 is NEW.

## Confirmed 2026-11-08 (second pass)
- Giant Flea residual hits READ BY HAND (otn_enhanced/reference_files arm9.bin / nds_overlay_3.bin, capstone/u16 dump): the 4 ARM9 data hits
  (0x0209D6BE, 0x0209E414, 0x0209E6BC, 0x020A1416) sit in monotonic numeric tables (0xFE0,0xFDF,0xFDE,0xFDD,0xFDC... paired with 0x208..0x227 /
  0xFDFE..0xFDDF) = geometry/trig tables, NOT cids. Code hits arm9 0x020080F0 and 0x020534F2 are inside instruction streams
  (0x0FDD == `lsrs r5,r3,#0x1f` encoding), not literals. ov3 0x02265458 is the low half of a 0x0226xxxx pointer table. => no per-cid gate found.
  STILL UNCHECKED: stack-based-switch blind spot (thumb.stack_based_switch).
- Grandsoil IS in steps.STEPS (otn_enhanced/steps.py:196) -> earlier "not shipped" note was stale; usable precedent.
- Shared hand-SS table (CAVE3_TGSH_SSTABLE 0x021DF390, 0x80 B = 15 rows + terminator): in data/.../rom_all_patches.nds (mtime 2026-11-06) rows 0..11 used
  (0x11B7,0x1F18,0x17CE,0x181C,0x13AE,0x1265,0x10A5,0x1110,0x1C1A,0x181F,0x190B,0x1E05), terminator at 12 => 3 free rows. Chain ROM may predate
  Gearfried/Predaplant single-card work (not in chain by rule) - re-read from a fresh build before claiming.
- ov5_cave.CAVE_FREE currently 0x023ADCF0 (read from ov5_cave.py:2518); ledger not yet re-quoted for a claim.

## Ruled Out
- Giant Flea per-cid data gates via the 7 residual donor_scan hits (see above).

## Open Questions / precedents (UNVERIFIED, read from notes only)
- C1 hand-SS + banish cost: Lightpulsar/Darkflare handss_banish_cost.py is FULL (no dead arms left; notes say a 3rd card needs a new mechanism).
  Newer route: Gearfried C1 = virtual cls2 hand record + virtual criteria row picker (otn_enhanced/cards/immortal_phoenix_gearfried.py).
  GY-SS half: Lightpulsar GY resolver (handss.self_ss_from_gy_resolver) / Revolution Synchron virtual GY-action row.
  NEW unknown: one picker spanning hand AND GY (3 picks, EARTH, excluding self).
- "Cannot be Normal Summoned/Set" for a Lv8 donor: need precedent (Chaos Sorcerer-family / Dragon Rulers).
- C2: no shipped "all my Rocks indestructible except battle" - check Gravekeeper/Koa'ki Wall-style leave-mask & destroy-prevent precedents.
- C3: Level-sum deck search with up-to-3 picks is new; Dragunity Remus named-search/Miscellaneousaurus pick-count are nearest.

## Next Experiment
- Pick donor with user; run Donor checklist (per-cid gates); find precedents for C1 mixed-zone cost, cannot-NS, C2, C3 before any code.

## C1 cost research (2026-11-08, static reading of KB YAML only; NOTHING executed, NOTHING built) - all UNVERIFIED until re-run
- NATIVE PAYMENT MACHINE ALREADY DOES MIXED ZONES: handss.banish_payment_state_layout (handss_dispatch.yaml:309): handler 0x0226292D, state 2 @0x02262B7E
  commits each picker pick by trying GY (0x021A2510 -> 0x021C7104) THEN hand (0x021A25A0 -> 0x021C6E98) THEN field. State 1 opens picker
  0x0219C430(side, min(count,0x20)+6, cid, pass) = exactly n picks. => the COMMIT for "3 EARTH from hand and/or GY" needs no new mover.
- event.hand_index_and_hand_banish (event_queue.yaml:756): mixed commit recipe h=0x021A25A0(side,ref); h>=0 ? 0x021C6E98(side,h) : 0x021C7104(side,0x021A25E8(ref),0).
- Candidate enumeration spanning hand+GY with a filter: Double Evolution Pill (cards.yaml:79, IN-GAME CONFIRMED by user 2026-09-28, SHIPPED) = ONE criteria row whose
  ov5 handler builds a hand+GY candidate set with banish flag 0x10000; Sacred Sword (hand builder + banish flags) same idea. => C1's candidate list = a handler of that shape
  filtered to EARTH monsters, excluding self.
- Count per row: 0x0225CF28(cid) = number demanded PER ROW; unnamed-cid default 0 => VACUOUS PASS (free summon). Lightpulsar retargets 0x0225CF5E to return-1 leaf (count 1).
  Block Dragon needs 3 => a NEW per-cid arm returning 3 (Dark Necrofear 0x1466 = 3, Rainbow Dark Dragon = 7 prove the count mechanism). NOT yet read: how to add an arm.
- Registry row required or the summon is FREE (handss.summon_procedure_registry, 0x0228F158, {cid,handler}, stride 8, 133 rows, count hard-coded imm8 0x85 in BOTH
  searchers; 16 phantom rows carry 0x02261F8D = drop candidates). Block Dragon row {0x0FDD -> 0x0226292D} over a dropped phantom, count-neutral.
- State 0 per-cid arm sets prompt text / race-attr; donor cid not named -> DEFAULT arm: UNVERIFIED what the default prompt says / whether it filters.
- Dark Simorgh 0x1E5A pays from EITHER zone natively with separate hand/GY rows (effect_dispatch_tables.yaml:1021) = proof a GY-origin summon procedure exists natively.
- Hand-SS routing for a NEW cid: dead arms are GONE (handss_banish_cost note). Candidate: the shared tg_table trampoline hook 0x0224C026 (Grandsoil, 3 free rows) gives
  ELIGIBILITY only; whether the trampoline path then reaches the registry/payment machine (instead of a free summon) is UNPROVEN - this is THE open question for C1.
- Shared payment stubs in finished_patches/handss_banish_cost.py (DONOR_CIDS register 0x0FB1, 0x1646) hook the two payment dispatch roots; Block Dragon's cid would have to join that register.

## Next Experiment (C1)
1. Read handss.banish_cost_payment_dispatches + handss_banish_cost.py: can a cid routed in via the tg_table trampoline reach 0x0226292D, or must it go through the hand-SS tree leaf 0x0225FA46?
2. Savestate/thumbemu (scratch/thumbemu.py): run the 0x0225CF28 count switch for cid 0x0FDD; list free arm slots.
3. Only then write a single-card _build_block_dragon.py for C1 alone.

## C1 routing (2026-11-08, static; capstone over otn_enhanced/reference_files/nds_overlay_3.bin + KB yaml; NOTHING executed)
- Count: hand-simulated 0x0225CF28(0x0FDD) from the stock bytes (pool: 0x1C2B, 0x16CB, 0x1466, 0x16C7; cf28..cf5e): 0x0FDD < 0x1466 -> `bne 0x225CF5E` -> `b 0x225D09C` (return 0).
  Every cid < 0x1466 shares that branch; Lightpulsar's shipped edit retargets 0x0225CF5E to the return-1 leaf 0x0225D06A, so in the CHAIN ROM 0x0FDD would count 1, in stock 0.
  Return-3 leaf already exists: 0x0225D062 (`movs r0,#3; bx lr`, Dark Necrofear's, reached from 0x0225CF5C `beq`). Block Dragon needs 3 => a tiny cid-testing leaf
  at 0x0225CF5E's target (r0 == cid ? 3 : 1), hosted in the 126 B ov3 dead run (0x0225F240, 104 B used, 22 B free per handss_banish_cost.py docstring - UNVERIFIED in current ROM).
  Hand-simulation is register-only; the path touches no stack (same caveat Lightpulsar's note records), but run it through scratch/thumbemu.py before relying on it.
- Payment dispatch 1 (root 0x02262962) default arm 0x02262AAE sets up NO selection; the Necrofear arm 0x02262A52 calls get_race(0x0202ABB8) for the prompt; the Gigantes-family
  single-attribute arm is what gives an EARTH prompt. Block Dragon must join the shared stub register (handss_banish_cost.DONOR_CIDS) routed to an EARTH-prompt arm; dispatch 2 default
  (one pass) is CORRECT for a single-row cost. Which arm exactly = UNPROVEN (read 0x02262962..0x02262AAE arms against Gigantes 0x16C7).
- Registry row {0x0FDD -> 0x0226292D} over a dropped phantom, count-neutral (0x0228F158, imm8 0x85 in both searchers). Required: miss = FREE summon (confirmed in-game on Lightpulsar twice).
- Trampoline question (does the tg_table path reach the payment machine?): the trampoline hook 0x0225E51C replay only decides the "may SS from hand" bit (success leaf 0x0225F216 = set bit 2, handss_dispatch.yaml:107);
  the COST is chosen later by the registry lookup in the generic summon path (0x02264DAE / 0x022651C0), independent of how the bit was set. Grandsoil has no registry row => free summon = consistent.
  => STRONG INFERENCE that a trampoline-offered card WITH a registry row pays via 0x0226292D. NOT proven in the emulator. Experiment: single-card ROM with trampoline cond stub + registry row + count leaf,
  GDB/savestate watch that state 0..3 of [0x02298A28+0x24] run for cid 0x0FDD.
- LEGALITY: our own trampoline cond stub counts EARTH monsters in hand+GY excluding self (>=3), free zone 0x021B9ECC, canSS 0x021AD870 (Grandsoil's stub shape). The payment's picker candidates come from the
  criteria row (handler = a Double-Evolution-Pill-style hand+GY builder, EARTH filter, exclude self) - the row's param/pass wiring for a trampoline cid is UNVERIFIED (the criteria resolver for a cid with no
  hand-SS-tree leaf: Gearfried's virtual row 0xFF20 is the nearest precedent).
- GY-origin SS (second half of C1) NOT yet researched beyond "Dark Simorgh does it natively and Lightpulsar's GY resolver handss.self_ss_from_gy_resolver exists". Separate routing question.

## C1 GY half research (2026-11-08, static KB/code reading; NOTHING executed) - UNVERIFIED until run
- GY self-SS = ONE shared cls2 slot1 resolver 0x0220731D (handss.self_ss_from_gy_resolver, VERIFIED in KB, 69 records); an unnamed cid runs the default mode-0 common body 0x022073E8.
  Per-card parts are the record's slot3 (+0C condition) / slot4 (+10 cost). Ojamassimilation C3 shape: cls2 {GYRES, 0, GYCOND, cost, GYSEL}.
- A GY effect is invisible without a GY-ACTION registry row (0x0228DDF8, dispatch.gy_action_registry_consumers, VERIFIED). Registry is 60 rows, no free phantom in the Grapha family.
  Existing facility: Rulers' virtual GY rows 60.. (CAVE_RUL_GYROWS, 0x60 B = 6 rows max, shared stubs gyfetch/gyexit/gypost/gyhas parameterised by _gy_rows()):
  Revolution Synchron (1) + 4 big Rulers + Sekka's Light (appended via EXTRA_GY_ROWS) = 6 => LIKELY FULL; Block Dragon needs the reserve grown (ov5 cave claim + ledger) - NOT yet checked.
  Alternative from KB (Remus): convert a wrong-family phantom row by rewriting its check/post words to {0x0224C591,0x0224C6C1}; rows 11/12/13 are taken (Remus/Misc/Ojam); other phantom rows UNSURVEYED.
- ARCHITECTURE OPTION B (recommended, supersedes the registry+payment-machine route for BOTH origins): Gearfried C1 (in-game confirmed whole card 2026-11-04, NOT shipped) already gives a HAND self-SS
  with a REAL banish cost through a virtual cls2 hand record (find_event_handler miss-tail front, desc[+5]==2,[+3]==0xB,[+4]==0), a virtual criteria row (0xFF20) over hand/GY/field candidates and a
  picker cost on the [RES_STATE+0x7C] phase protocol. A Block Dragon cost function = that, with (a) hand+GY EARTH monsters excluding self, (b) picker code n+6 = 9 for exactly 3 and a 3-pick commit
  loop using the mixed-zone recipe (event.hand_index_and_hand_banish; payment machine state 2 is the native model), (c) the SAME cost/legality reused by a GY-origin cls2 record (resolver 0x0220731D + GY row).
  Wins: no registry row, no 0x0225CF28 count leaf, no shared-payment-stub contention. Costs: new multi-pick loop asm; shared find_event_handler miss-tail front chain (Gearfried not in chain => no conflict today,
  but both cards would front the same site); the GY row capacity; "Cannot be NS/Set" still via Grandsoil's LIST_NS_OR_SS membership.
- NEW OPEN QUESTION: "Must be Special Summoned" also implies it cannot be Special Summoned by other effects (Monster Reborn, Call of the Haunted). Not in Grapha/Lightpulsar/Grandsoil precedents
  (white_dragon_ninja.py notes 'no summon-restriction route exists'). Needs a user ruling: ship without that restriction (as Grandsoil does)?

## User ruling 2026-11-08
- "Must be Special Summoned": ship WITHOUT blocking other-effect Special Summons, same as Grandsoil (user: "Yes, same as Grandsoil"). Only NS/Set is blocked.

## C2 / C3 research (2026-11-08, static KB/code reading; NOTHING executed) - UNVERIFIED until run
### C2 "Rock monsters you control cannot be destroyed, except by battle"
- REJECTED hook: the affect-predicate 0x021B021C / link 0x021B058C (Azure-Eyes C2, in-game confirmed) is "may this card effect affect this monster" - it blocks targeting AND every
  non-destroy effect too (bounce, control change...), and Azure attaches per-zone rider nodes ONCE on summon ("Dragons you currently control"), not a live class. Wrong semantics for
  "cannot be destroyed" and for Rocks summoned later.
- BEST HOOK: destroy.survive_check_0x021CC028 (field_spell_engine.yaml:143, VERIFIED): "would be destroyed -> survives?" r0 side(r5)/r1 zone(r4), [sp+8] = cid of the card, returns 1 = survives; commit==0 is a pure
  query. Default exit 0x021CC264 (`movs r0,#0 ; pop {r1-r7,pc}`) is ALREADY hooked by Seal of Orichalcos C2 (stub 0x021B2B10, cid 0x10F5, in-game confirmed 2026-10-02): Block Dragon must CHAIN in
  front of / behind that stub (its `no:` path returns 0), not replace it. Stub idea: zone <= 4, face-up (0x021A32B4), race(cid at [sp+8]) == Rock (0x0202ABB8), AND own side holds a face-up Block Dragon
  (0x021A36EC + 0x021A32B4 scan of zones 0..4 like white_dragon_ninja's leaf; bit26 / global slot mask tests) -> return 1, no state spent.
- UNPROVEN, decisive: does BATTLE destruction go through executor 0x021CC290 / this survive check? Executor is gated on mode bit 1 ([sp+0x14]), source arg [sp+0xF0] != 0, per-card halfword (NOT decoded - Seal notes).
  If battle destroys also pass it, "except by battle" would be violated (Rocks would never die in battle). Battle-destroy predicate is separate (0x02197E90, battle_attributes.yaml:359) - suggests battle takes
  its own path, but MEASURE: thumbemu / GDB breakpoint on 0x021CC028 during a battle destroy and an MST destroy.
- Also UNPROVEN: Rock race code value from 0x0202ABB8 (Dragon = 1 per azure-eyes note); whether tribute/cost/Synchro-material "sent to GY" counts (it is not destruction; survive check should not be called).
### C3 "If sent from the field to the GY: add up to 3 Rocks from Deck, total Levels = 8. Once per turn."
- TRIGGER: GK Recruiter on Normal donor Battle Steer (in-game confirmed 2026-09-10, ov3 move confirmed 2026-10-06 incl. puzzle): leave-MASK row {cid, 0x0800} @0x0226EC1C over a phantom + cls2 + populate row;
  fires on battle, effect destruction, Tribute, Synchro Material, field-only (event.leave_dispatcher_three_registers). Cost: 3 phantom drops in that card (cls2, populate, mask) - Block Dragon needs its own 3 phantoms
  (and the Level-8-total search resolver is NEW). Darksoul = "any leave" alternative (TREE 2).
- SEARCH: Recruiter's search = custom filter + cloned Botanical wrapper (CAVE3_GK_FILTER/WRAPPER). Needed: Rock-in-Deck filter + SUM constraint. The native picker 0x0219C430 only knows count codes (n+6 exactly n, 0x47 any
  number) - NO level-sum validator; Mara/Wattuna level_sum 0x0224966C is Synchro-material hand/field machinery, not reusable for Deck. Plan: step-wise picker, each step re-builds candidates with remaining sum r and picks-left k
  (candidate Level <= r; feasibility: k==1 -> Level == r, k==2 -> a second Rock exists summing to r - L, ...), stop when r == 0. Valid partitions of 8 into 1-3 parts: {8},{1,7},{2,6},{3,5},{4,4},{1,1,6},{1,2,5},{1,3,4},{2,2,4},{2,3,3}.
  RULING NEEDED: if the Deck cannot form a total of exactly 8, may the effect be activated (and do nothing)? Cannot stop early with a partial total (printed text).
- Tooling: C effect stubs exist (asm/cc.py + engine.h, memory otn-c-effect-stubs; Mystic Piper pilot confirmed 2026-11-03) - candidate for writing the stepwise search in C.
- Once-per-turn flag: UNPLACED (Recruiter-style HOPT: turn log / cls2 key 'You can' shape; Souleating Oviraptor's HOPT shape is the confirmed template).

## User ruling 2026-11-08 (C3)
- C3 may only be activated when the Deck holds a legal selection (1-3 Rocks, total Level exactly 8). The activation CONDITION must scan the Deck for a feasible subset; no activate-and-fizzle.

## C2 battle-path check (2026-11-08)
- Static: executor 0x021CC290 is the GENERAL relocation core (34 BL callers in ov3). Survive check call @0x021CC604 requires [sp+0x14] (= mode bit 1, r3&2), [sp+0xF0] (stacked source arg) != 0 and a
  per-card halfword != 0 (0x021CC5D4 pool). Effect-destroy wrappers pass mode 2 (0x021CF31C/0x021CF35C `movs r3,#2`), others pass 0/8/0xA/0x1000/0x10000/...; the battle path's mode is NOT decoded.
  => battle reaching the check is DECIDED BY MODE+SOURCE ARG, unresolved statically.
- Experiment written (NOT run; needs the user's melonDS + active duel): scratch/gdb_block_dragon_destroy_path.py - one connection, breakpoints E 0x021CC290 (log dest/mode/source for zone<=4 -> GY/banish)
  and S 0x021CC604 (survive check actually called). Do: (1) destroy by battle, (2) destroy by effect, (3) tribute, (4) lose a monster to battle. Expected if the hook is safe: S after (2), none after (1)/(4).
  Preflight compares both sites to the reference image. Output scratch/gdb_block_dragon_destroy_path.txt.

## Build attempt 2026-11-08 - BLOCKERS FOUND BEFORE ANY CODE (static; chain ROM rom_all_patches.nds 2026-11-06)
- NOT BUILT. The user asked for build + self-test; reading the build infrastructure first turned up capacity blockers, banked here instead of hacking around them.
- "Cannot be Normal Summoned/Set" membership list (NOMI class-2, ARM9 0x0209BE9C, 57 entries, count imm8 0x39 @ thunk 0x020231E0): in the chain ROM it holds NO phantom - all 57 are real
  cards/donors (read this session: 0x10A5 .. 0x2432 incl. 0x1110, 0x181F, 0x1C1A). Both reference-image phantoms (0x0E63 grandsoil, 0x0EB3 moulinglacia) are claimed (check_allocations.py:1599/1614).
  => Block Dragon cannot join it count-neutrally. Needs: list relocation + count bump (bsearch count imm8 + pool literal), or another NS/Set-block route. UNINVESTIGATED how Windrose/Pyrorex got in.
- GY-action virtual rows (CAVE_RUL_GYROWS 6 rows) likely full (see GY half section).
- Hand-offer / criteria / find_event_handler front sites H1..H4 are an ORDERED CHAIN (ov5_cave.dc_next, Predaplant ahead of Gearfried ahead of Medraut/Disguise/Rulers); a new owner must be registered in
  that chain AND in CAVE_* ledger constants (CAVE_BD_*), as Gearfried did with CAVE_GF_*. Gearfried's constants are claimed in ov5_cave.py (0x023ACF10..) and CAVE_FREE = 0x023ADCF0.
- NEW ASM still unwritten: hand+GY EARTH candidate handler, 3-pick commit loop, GY-origin cls2 record, Rock destroy-survive stub (+ battle-path measurement), Level-sum Deck search with feasibility scan.
- Autonomy limit: the CPU mirror harness (cardtest) reports only drawn/summoned/activated counts; it cannot prove "banished exactly 3 EARTH", C2 protection, or the Level-8 search. Those need GDB/savestate
  evidence from a live duel (melonDS GDB one-shot) - the C2 battle-path probe is already written (scratch/gdb_block_dragon_destroy_path.py).

## Stage 1 capacity (2026-11-08, static; chain ROM rom_all_patches.nds 2026-11-06 read this session)
### NS/Set block - SOLVED on paper (class 4)
- Classifier 0x020231C8 has FOUR lists (cards.yaml:622, VERIFIED KB; re-read here): class1 0x0209BE2C (0x37) Spirits/Toons/Chaos-family - NOT NS-forbidden; class2 0x0209BE9C (0x39) full nomi; class3 0x0209BA12 (3)
  "SS only with one named card" - NOT NS-forbidden; class4 0x0209BC14 (0x1D) semi-nomi. Caller 0x020233F4 returns 0 ("cannot be Normal Summoned/Set") for classes 2 and 4 ONLY (disassembled this session).
- Class 2 in chain: 57 entries, ZERO phantoms (printed this session). Class 4 in chain: 29 entries incl. Windrose 0x190B (replaced phantom 0x19A8) and STILL-FREE phantoms 0x0E22 and 0x167C
  (allocations.yaml nomi_class4_list claims only 0x19A8/0x190B -> 0x0E22 / 0x167C unclaimed; re-quote the ledger before claiming).
- Membership in ANY class also removes the cid from every Deck/hand SS-search candidate list (cards.yaml:622, 0x021BA69C) = consistent with "Must be Special Summoned"; does NOT block effect SS from GY (user ruling 2026-11-08: same as Grandsoil).
- Class 4 costs one thing: the CPU AI planner (ov5 0x0236A1BA) SKIPS class 3/4/5 cards (notes/windrose-findings.md step 0). Windrose solved it with an ov5 stub returning 2 for 0x190B else the native class
  (`bl 0x020231C8` @0x0236A1BA -> stub). Block Dragon = extend that stub to a cid list {0x190B, 0x0FDD}. Small, ov5 only (puzzle-safe).
- Plan: archetype_member(NOMI_CLASS_4_TABLE, phantom=0x0E22) (table const lives in windrose.py:23: SetCodeTable("nomi class 4", 0x0209BC14, 0x1D, (0x02023224,), (0x02023206,))) + Windrose AI-stub list extension.
### GY-action row capacity - REAL BLOCKER, needs a shared edit
- Chain ROM CAVE_RUL_GYROWS 0x023A6DF0 (0x60 B): ALL SIX rows used (read this session): 0x1649 (Revolution), 0x17CD, 0x115F, 0x1145, 0x1125 (Rulers), 0x10E6 (Sekka). 7th row has nowhere to go:
  the next slot CAVE_RUL_GYFETCH starts at 0x023A6E50 = exactly +0x60. Registry 0x0228DDF8 itself has no free phantom (virtual-row memory note).
- Fix = RELOCATE the row blob to a 0x80 B (8-row) region: change ov5_cave.CAVE_RUL_GYROWS (retire the old 0x60 slot as CAVE_RUL_GYROWS_OLD, same pattern as CAVE_TG_SSTABLE_OLD2), bump CAVE_FREE, raise
  dragon_rulers._extra_gy_rows bound `range(base, 6)` -> 8, refresh the ledger. Rulers' gyfetch stub takes the rows address from the constant, so the stubs regenerate. BLAST RADIUS: changes shipped bytes of
  Dragon Rulers / Revolution Synchron / Sekka's Light rows => frozen-baseline compare breaks (re-baseline through the apply_all_patches oracle, ~30 min) and the user should re-test those three in-game.
  NOT DONE - needs the user's go-ahead because it edits shipped, user-confirmed cards' bytes.

## CORRECTION 2026-11-08 - GY-row capacity is NOT a blocker; relocation NOT needed (supersedes the "REAL BLOCKER" section above)
- My Stage 1 conclusion read only the Rulers' LEGACY table CAVE_RUL_GYROWS (6 rows, left in place, dead once the sites move). The live table is the SHARED module otn_enhanced/effects/gy_vrow_hook.py:
  CAVE_GYV_ROWS 0x023A7600 (0x100 B = MAX_ROWS 16), base rows read live from the Rulers' table + the ARMS register. In the chain ROM (rom_all_patches.nds 2026-11-06) rows 0..14 are filled
  (Revolution 0x1649, Rulers 0x17CD/0x115F/0x1145/0x1125, Sekka 0x10E6, Infernoble 0x13A3/0x139A/0x1E04/0x0FC1/0x0FE6/0x0FD4/0x0FEB/0x1118, Charles 0x16DB) and row 15 is ZERO = ONE FREE ROW (read this session).
- Block Dragon takes row 15: gy_vrow_hook.install(rom, ov, arms=ARMS + ((0x0FDD, "Giant Flea -> Block Dragon GY SS"),)) - install() takes `arms` as a parameter, so a single-card test build does NOT edit the shared ARMS tuple
  (editing ARMS would wire it into the chain builds; per rule it waits for the user's approval). After Block Dragon the GYV table is FULL (16/16): the next GY-ignition card needs MAX_ROWS raised (RESERVES[ROWS] 0x100 -> larger + ledger).
- No shipped bytes are touched. The relocation the user approved was therefore NOT performed (not needed). Lesson (same as the Gearfried 'not shipped' mistake): read the LIVE ROM table, not the first module that names it.

## Stage 2 build (2026-11-08) - C1 HAND HALF BUILT, static + CPU evidence only; AWAITING IN-GAME TEST
- CORRECTION: Gearfried, Gearblade and Predaplant ARE in steps.STEPS and in the chain ROM (the earlier "Gearfried not in chain" was wrong): chain heads read this session
  H1 0x0224A86A -> CAVE_GF_H1, H2 0x02243F24 -> CAVE_PD_H2, H3 0x02243F62 -> CAVE_PD_H3, ARM9 H4 0x02023566 -> CAVE_GF_H4.
- Built: otn_enhanced/cards/block_dragon.py + cards/c/block_dragon.c + _build_block_dragon.py -> data/over_the_nexus/working/rom_block_dragon.nds sha256 c5bdd6a5...158891, verify 27/27 (static).
  Claims: ov5 CAVE_BD_* 0x023ADCF0..0x023AE070 (11 slots, CAVE_FREE -> 0x023AE070; only 0xB0 B left before the ov5 ceiling 0x023AE120), ledger refreshed (+55 lines, additions only),
  dc_next fronts registered (BD_H1..H4 AHEAD of GF_H1 / PD_H2 / PD_H3 / GF_H4), virtual criteria index 0xFF40, card_text entry 0x0FDD (English only, NOT shipped). No phantom/cls2/cls1 rows claimed.
- Design as built: virtual cls2 hand record {BD,0,RES=0x02206ABD native,0,COND,COST,S5}; COND (C) = hand zone, free zone 0x021AD870, (EARTH monsters in hand+GY incl. self) >= 4;
  COST = Double Evolution Pill's 0..3 phase protocol extended to 3 picks, refs in desc[+0x14+2i], count desc[+0x12]; handler = DEP hand+GY builders (flags 0x10000) + EARTH filter excluding desc[+0xC] (own ref,
  ASSUMED valid for a hand descriptor) and already-picked refs (needed: DEP's two picks had different filters, three identical picks could repeat).
- ASSUMED / UNPROVEN: desc[+0xC] holds the hand card's ref at cost time; desc[+0x14..+0x19] free scratch; engine attribute numbering EARTH == 5 via 0x0202ABC8 (fusion_material.yaml numbering);
  picker re-opens cleanly for picks 2 and 3 (DEP proved 2); a picked-twice guard works; 0x02206ABD summons without a once-per-turn wrapper.
- CPU evidence (emulator, NOT user-confirmed): cardtest rig + mirror, rom_block_dragon.nds, kit Big Insect:14 / Gokibore:14 / Neo Bug:10, 8 duels, 3 jobs: ALL 8 duels finished (no hang / freeze);
  Block Dragon drawn 17 / summoned 2 / activated 0; kit drawn 190 / summoned 67 / activated 0. "summoned 2" is AMBIGUOUS: the Normal Summon/Set block is NOT built, so the CPU may have Tribute Summoned it (Lv8, 2 tributes).
  activated 0 = no evidence the CPU used the hand-SS route (the CPU may not plan virtual hand records at all; the class-4 AI stub is not built either). `cardtest rows`: no ov5 CPU row (monster donor).
- NEXT EXPERIMENT (needs the human or a scripted duel): a live duel with Block Dragon + >= 3 other EARTH monsters in the hand/GY: is the SS offered, does it prompt 3 times, banish exactly those 3 (hand and/or GY,
  never itself, never the same card twice), and summon? GDB probe candidates: bp 0x023ADDF0 (cost) logging [0x0229AAFC+0x7C] phases + desc[+0xC]/[+0x12]/[+0x14..].

## NS/Set block built (2026-11-08) - AWAITING IN-GAME TEST
- Added to block_dragon.py: archetype_member(NOMI_CLASS_4_TABLE, phantom 0x0E22) (nomi class 4 list 0x0209BC14: 0x0FDD in, 0x0E22 out, sorted) + `cpu_planner_reads_class_2_ahead_of_windrose` = CAVE_BD_AI 0x023AE070 (0x20 B)
  chained ahead of Windrose's CAVE_WR_AICLASS at ov5 site 0x0236A1BA (0x0FDD -> class 2; else tail to Windrose's). CAVE_FREE -> 0x023AE090 (0x90 B left before the ov5 ceiling 0x023AE120).
  PHANTOM_CLAIMS += ("nomi_class4_list", 0x0E22, "block_dragon"); ledger refreshed (additions only).
- rom_block_dragon.nds sha256 77eed423...738e0c, verify 30/30 (static). The install ASSERTS Windrose's re-point is present, so this front needs Windrose in the chain (it is).
- Verify sweep of the UNCHANGED chain ROM after my shared edits (ov5_cave.py, card_text.py, check_allocations.py, ledger): 116 passed, 0 failed, 5 without verify() (this session, otn_enhanced.verify rom_all_patches.nds).
  => the shared-file edits did not break a shipped module's verify(). (The chain ROM itself was not rebuilt.)
- Static reachability (this session, depth-4 BL walk from 0x02206ABC over ov3, 92 functions): the native hand self-SS resolver does NOT reach the classifier 0x020232AC / 0x021BA684 / 0x021BA69C, so a
  class-4 membership should not reject Block Dragon's own hand summon. NOT executed; depth-limited; UNPROVEN until the emulator shows the summon happening.
- Follow-up before shipping: windrose.verify() must accept Block Dragon's front ahead of its AI stub (it asserts the site calls its own stub) - handle via an ik_walk/dc_next-style skip like the other chains.

## CPU mirror on the NS-block ROM (2026-11-08; emulator CPU, NOT user-confirmed)
- rom_block_dragon.nds sha256 77eed423...738e0c, kit Big Insect:14 / Gokibore:14 / Neo Bug:10, 12 duels, 3 jobs, rig rebuilt from this ROM: ALL 12 duels finished (no hang/freeze).
  Block Dragon drawn 26 / summoned 0 / activated 0; kit drawn 328 / summoned 109 / activated 0.
- READING: the earlier "summoned 2" (no NS block) were Tribute Summons - with the block they are gone. The CPU never Special Summoned Block Dragon from the hand in 26 draws.
  That is consistent with (a) the CPU planner not offering a virtual hand cls2 record / the class-view front not taking effect, OR (b) the hand-SS route itself being broken (COND never true, offer not shown).
  The mirror cannot tell (a) from (b). It does show the NS/Set block stops the Tribute Summon path and that nothing crashes.
- NEXT: a human or scripted live duel (or GDB breakpoint on CAVE_BD_C1_COND 0x023ADD40 in a CPU duel: does COND ever run / return 2 when >= 4 EARTH cards are in hand+GY?) to separate (a) from (b).


## HANDOFF 2026-11-08
- Continuation prompt written: PROMPT_block_dragon_c1.md (status: C1 hand half + NS block BUILT - AWAITING IN-GAME TEST; GY half, C2, C3 not built). The prompt and this file agree; this file is the log.
- KB not updated this session: facts proven here (live GYV row 15 free, class-4 phantoms 0x0E22/0x167C, chain front heads, 0x0225CF28(0x0FDD)=0) are only in this file and the prompt - add them to author_facts.py with proofs next session.
- verify_knowledge 2026-11-08: TOTAL 1075 facts: 893 PASS 7 FAIL 175 UNVERIFIED (7 FAIL = missing 3DS extract + tool.rom_files_entries_must_be_bytearray, not from this work).

## CPU no-summon diagnosis 2026-11-09 (GDB, one CPU-vs-CPU mirror duel on rom_block_dragon.nds; scratch/gdb_bd_cpu.py; NOT user-confirmed)
- PROVEN (this session, GDB breakpoints, 81 s duel, Block Dragon drawn): CAVE_BD_C1_COND 0x023ADD40 / COST 0x023ADDF0 / my class-view front CAVE_BD_AI 0x023AE070 / planner site 0x0236A1BA
  were NEVER hit. The CPU does not use the 0x0236A1BA planner for hand SS.
- PROVEN: the CPU's hand-card loop is ov5 0x02340EEC..0x02340F76 (hand list at player+0x124, per card: 0x02029E60(cid) -> BL 0x0225E51C(player, ref) legality -> 0x0233FCB4 evaluator).
  cid 0x0FDD reached 0x0225E51C 49 times and it returned 0 every time. Cause: BD's offer is a virtual cls2 record (human menu path); 0x0225E51C (hand-SS legality, tg_table trampoline) has no row for 0x0FDD.
- Ruled out: stale rig (rig ov5 bytes at 0x0236A1BA/0x023AE070/0x023ADD40 == rom_block_dragon.nds).
- Next: give 0x0225E51C a BD arm (shared trampoline table CAVE3_TGSH_SSTABLE, 3 free rows) whose cond = BD COND, then re-run; also see what 0x0233FCB4 does after legality passes.

## CPU path fixed to OFFER, but the summon is FREE (2026-11-09, GDB, CPU-vs-CPU; NOT user-confirmed)
- Built: CAVE_BD_CPU 0x023AE090 (0x40 B; CAVE_FREE -> 0x023AE0D0, ledger refreshed) = front over ov5 `bl 0x0225E51C` @0x02340F16 (CPU hand-card loop; r6 = cid live across the call):
  cid 0x0FDD -> COND on a faked 8-byte descriptor (side<<16 | 0x0B<<24), else native. rom_block_dragon.nds sha256 c0d2be1c...c3227, verify 32/32 (static).
  (Footgun: EffectBuilder "STRB R0,[SP,#n]" silently assembles to STR -- no SP-based byte store in Thumb-1; compose the word in a register.)
- PROVEN (GDB, one 224 s duel, rig rebuilt from this ROM): COND hit 3x, returned 2 each; legality at 0x02340F1A returned 1 for 0x0FDD 3x (0 for all other cards); evaluator 0x0233FCB4 returned 1 (=> command 0x3E8) 3x.
  Result stats BD drawn 3 / summoned 3 / activated 0.
- PROVEN (same run): NO call to CAVE_BD_C1_COST 0x023ADDF0, and NO call to the banish movers 0x021C6E98 (hand) / 0x021C7104 (GY) -- so the CPU's 3 summons were FREE (no banish cost).
  Reading: the CPU runs the generic hand-SS path (legality bit -> registry miss), not the virtual cls2 record, same as Grandsoil/"registry miss = free summon". OPEN BUG, not an accepted deviation.
- Open: make the CPU's summon pay. Options: (a) CPU front returns 0 unless... (denies the CPU the card entirely, safe but no play); (b) registry row {0x0FDD -> 0x0226292D} + count leaf + EARTH prompt arm (the REJECTED payment-machine route in the prompt, now the only way the CPU path pays); (c) hook the CPU's executor to run the cost. Needs a user decision.
- Reproduce: uv run python scratch/gdb_bd_cpu.py 0 400   (cardtest rig must be rebuilt from the ROM first).

## CPU hand-SS across shipped cards (2026-11-09, GDB CPU-vs-CPU mirror, per-card kits; scratch/gdb_cpu_cards.py; NOT user-confirmed)
- Chain ROM rom_all_patches.nds (results scratch/gdb_cpu_cards.txt; 2 duels/card): Lightpulsar 0x0FB1 legality 4 (pass) + evaluator 1 + summoned 4/4 -> CPU plays it natively; Darkflare 0x1646 legality 4 once, summoned -> plays natively.
  Grandsoil/Moulinglacia/Pyrorex/Windrose: legality ALWAYS 0 (20-100 checks/duel), never summoned. Tidal 0x115F, Tempest 0x1125: legality 0, never summoned; Redox/Blaster: few/no hits.
- CAUSE (A/B proven): the CPU's hand loop (ov5 0x02340F16 `bl 0x0225E51C`) bypasses the shared hand-SS trampoline (ov3 0x021F1398, hooked only at the human site 0x0224C026). The trampoline's contract (r0 = side, r6 = cid) is identical at the CPU site.
  FIX (test ROM rom_block_dragon.nds sha 46797a9b, front CAVE_BD_CPU tails to 0x021F1398 for non-BD cards): same decks now -> Grandsoil 2/2 duels legality 4, summoned 1+1; Moulinglacia 1/2; Pyrorex 2/2 (summoned 1, 2); Windrose 1/2 (the other duel never met the GY condition).
  Each also activated its on-summon effect. => ANY tg_table card (Striker, Junk Servant, Unknown Synchron, Grandsoil family ...) is CPU-playable with ONE 4-byte BL at ov5 0x02340F16 -> 0x021F1398 (no cave: BL range ok). Not yet a standalone module / not in the chain.
- Block Dragon after the fix: 2/2 duels legality 1, summoned 1 each, still FREE (no cost run).
- Still open: Dragon Rulers (not in tg_table; need their own CPU legality + cost), Block Dragon CPU cost.

## CPU payment handler (2026-11-09) -- BUILT IN SOURCE, NOT BUILT INTO A ROM (blocked, see bottom)
- PROVEN (GDB probe scratch/gdb_bd_pay.py, probe ROM with registry handler stub = `movs r0,#1; bx lr`): the summon-procedure registry handler for 0x0FDD IS called when the CPU summons it (lr 0x02264DC1 = the `blx r0` at 0x02264DBC), once per summon.
  Summon record 0x02298A28 at that moment: +2 side, +0xC = the SUMMONED CARD'S ref (hand word -> (w>>23&0xFF)*2 + (w>>14&1): 0x03000FDD -> 0xC, 0x04000FDD -> 0x10, 0x04004FDD -> 0x11), +0xE cid 0x0FDD, +0x24 state = 0 at entry. The summoned card is STILL IN THE HAND (hand_count includes it).
  is_cpu flag [0x02299114+8+side*4] = 1 for both seats in the CPU-vs-CPU rig (human = 0 in a real duel).
- Registry row: phantom 0x0FDE (handler 0x02261F8D, between 0x0FB1 and 0x0FDF) re-keyed to 0x0FDD in place -> sorted, count-neutral. Claimed in check_allocations.PHANTOM_CLAIMS ("registry_row", 0x0FDE).
- Handler design (cards/c/block_dragon.c STUB=PAY): human seat -> return 1 (already paid via the cls2 COST); CPU seat -> one banish per call (native payment machine pacing), GY first then hand, EARTH only, skip the summoned card (index = 0x021A25A0(side, ref)), descending index; gy mover 0x021C7104(side,&GYword,0), hand mover 0x021C6E98(side,index). 3 picks then state 3 / return 1. Syms added to asm/c/engine_syms.txt (+engine.h decls).
- SIZE: C handler = 0x104 B; the Block Dragon cave region had 0x50 B left. => RESERVE raised 0x14000 -> 0x14400 in ov5_cave.py, CAVE_BD_PAY (0x140) / CAVE_FREE 0x023AE210, ledger refreshed. (CAVE_TIMINGHOOK_OLD is marked "Never reuse"; not touched.)
- BLOCKER: the chain ROM's ov5 is the OLD length (0xE8820); install_cave refuses a layered build until the chain is rebuilt at 0xE8C20. `uv run python -m otn_enhanced.build` ABORTS in the deck preflight: rpg059_8_aki.ydc 'Chimeratech Fortress DragonScrap Archfiend' (a missing comma in the user's uncommitted otn_enhanced/data/ydc_decks.py). NOT my edit; not touched. Backup of the current chain ROM: data/over_the_nexus/working/rom_all_patches.PRE_reserve400.nds.
- Also proven earlier this session: Elemental Lords gain CPU legality when the CPU loop site goes through the shared trampoline (see above).

## CPU payment handler BUILT + MEASURED (2026-11-09; GDB CPU-vs-CPU; NOT user-confirmed)
- Fixed the user-approved typo in otn_enhanced/data/ydc_decks.py (rpg059_8_aki: missing comma after 'Chimeratech Fortress Dragon'); fast chain build then ran 126/126 steps at RESERVE 0x14400:
  rom_all_patches.nds sha256 2e38f06e...df8569a (129825928 B). Block Dragon layered on it: rom_block_dragon.nds sha256 bea64723...c48fa5, verify 36/36.
- PROVEN (one 81 s duel, rig rebuilt): COND returned 2 twice (side 0 and 1); each summon was followed by EXACTLY 3 banish-mover calls -- side 0: hand movers idx 5,4,3; side 1: GY mover 1x then hand movers idx 4,3.
  PAY handler called 10x = 2 summons x (init + 3 picks + finish). Summons 2 (drawn 1+1). So the CPU's Block Dragon summon is no longer free. Not checked in this run: that every banished card was EARTH (the filter is in the C; deck was all EARTH) and the human seat (needs the user: handler returns done at once for a human).
- Reproduce: uv run python scratch/gdb_bd_cpu.py 0 500

## CPU hand-SS for the big Dragon Rulers + Block Dragon (2026-11-09; GDB CPU-vs-CPU, rom_block_dragon.nds sha 68e253ab...ac01, 45/45 static; NOT user-confirmed)
- Built: CAVE_BD_CPUL 0x023AE270 (C legality, rule table: BD 3 EARTH; Redox/Tidal/Blaster/Tempest 2 of attribute-or-Dragon; need+1 counting the card itself; -1 = not ours) behind the CAVE_BD_CPU front (-> else shared trampoline 0x021F1398);
  CAVE_BD_PAY 0x023AE0D0 (0x1A0, same rule table; human seat returns done, CPU banishes one per call). Registry rows via insert_row_by_stride: 0x0FDD<-0x0FDE, 0x17CD<-0x0E5C, 0x115F<-0x0E60, 0x1145<-0x112E, 0x1125<-0x128C (all claimed in PHANTOM_CLAIMS). CAVE_FREE 0x023AE3B0.
- Results (scratch/gdb_cpu_cards_rulers.txt, 2 duels/card): Block Dragon legality 1 once per duel, summoned 1, banish movers exactly 3 per duel. Tempest legality 1 x2/duel, 2 summons, 4 movers (= 2 per summon). Tidal 10-12 legal, 14-15 summons (returns each End Phase), 28 movers.
  Redox duel1: 3 legal, 10 movers, 5 summons. Blaster: drawn 0 in both duels -> INCONCLUSIVE. Not checked: attribute correctness of every banished card; the human seat (needs the user); the Rulers' once-per-turn flag is NOT stamped by the CPU path (deviation).
- Blaster re-run (scratch/gdb_cpu_cards_blaster.txt, 5 duels): duel2 legality 1 x2, 6 summons, 12 movers; duel3 legality 1 x6, 9 summons, 18 movers; duels 0/1/4 had no legality hits (card not in hand when it could be offered / drawn 0). => Blaster is CPU-playable and pays like the others. (Movers include the Rulers' discard-effect banishes only if any; ratio 2 per legal summon holds: 4/12, 6/18 -> 3 per legal hit incl. other banish effects.)

## C2 hook PROVEN (2026-11-09; GDB CPU-vs-CPU rig, scratch/gdb_c2_path.py -> scratch/gdb_c2_path.json; deck = Dark Hole/Raigeki/Smashing Ground x3 + vanilla monsters; NOT user-confirmed)
- 58 events, ONE private-port GDB session (port 3340). Executor E 0x021CC290 (zone<=4 -> GY/banished):
  * BATTLE destruction: phase 3, mode 0x7, stacked source 0 -> 16 hits, NEVER followed by a survive-check hit.
  * EFFECT destruction (Dark Hole 0x10F6 / Raigeki-type 0x1711 / 0x10F7): phase 2, mode 0x10003, source = the card cid -> 20 hits, EVERY one followed by S 0x021CC604 (survive check called).
  * Tribute/other (mode 0x11000, source 0): 2 hits, no S.
  => the survive check 0x021CC028 sees exactly the card-effect destructions and not battle: the right hook for "cannot be destroyed, except by battle".
- INCIDENT: the user's own melonDS (~\RH\melonDS.exe) was running with the GDB stub on 3333 (repo melonDS.toml has Gdb Enabled), and two of my runs connected to IT by mistake (add_breakpoint timed out; breakpoints at 0x021CC290/0x021CC604 may be left armed in the user's emulator). Fixed: grass_gdb.worker now moves my private worker to ARM9 port 3340 / ARM7 3341 and all scratch/gdb_*.py use grass_gdb.PORT.

## C2 BUILT + MEASURED (2026-11-09; rom_block_dragon.nds sha 438fd55e..3cc3, 48/48 static; GDB CPU-vs-CPU; NOT user-confirmed)
- Built: CAVE_BD_C2W 0x023AE3B0 (asm front over the `bl` at ov3 0x021CC264, the survive check's default exit; tail -> Seal's stub 0x021B2B10) + CAVE_BD_C2 0x023AE3E0 (C: zone<=4, face-up, get_race(cid)==6 [Rock], own face-up Block Dragon in zones 0..4 -> 1). CAVE_FREE 0x023AE460.
  Needs seal_of_orichalcos in the chain (asserted; the chain has it).
- PROVEN (scratch/gdb_c2_path.py with C2_BD=1, seeds 1-5, Dark Hole/Raigeki/Smashing Ground deck): every survive check on a Block Dragon (cid 0x0FDD) returned 1 (14 hits, repeated Dark Hole attempts left it standing); a non-Rock (0x129F) returned 0; other non-protected cids 0.
  Battle destruction (phase 3, mode 0x7) never reaches the check so Rocks still die in battle (E hits 4-20 per duel in phase 3). NOT yet exercised: a NON-Block-Dragon Rock being protected (only BD itself appeared at the check); get_race==6 is the Rock code per game_constants.ERA2_RACE_MAP -- proven only via BD (race set by card_props "Rock").

## C3 DESIGN + PRE-BUILD RISK CHECKLIST (2026-11-09; static reading, NOTHING built for C3)
Text: "If this card is sent from the field to the GY: You can add up to 3 Rock monsters from your Deck to your hand, whose total Levels equal 8. You can only use this effect of 'Block Dragon' once per turn."
User rulings: any 1-3 Rocks summing to exactly 8; activation only when the Deck holds a legal selection (no activate-and-fizzle).
PRIMITIVES READ THIS SESSION (static, native add-to-hand resolver 0x02207EF4 disassembly; UNVERIFIED by execution):
- single pick: r1 = 0x0219C510() (picker readback word*), then 0x021C72CC(side, word*) = hand-add mover; multi-pick: loop i=1..[0x0229DD94+0x34]: r1 = 0x0219C94C(i), 0x021C72CC(side, r1). Picker open = 0x0219C430(side, count code n+6, cid, row-param) (phase 0x7D); 0x021D28A4 / 0x021D2964 open/close the pick session.
- desc[+0x18] is free scratch for a donor in the deck resolvers (effect_dispatch_tables.yaml ~2937). Deck criteria handler 0x0223CAD9 + Deck walker 0x0223BC3C / 0x0223DB24 (Qoatlus crit stub = precedent for a custom Deck predicate row).
- Trigger precedent: Gravekeeper's Recruiter (cls2 record with CLS2_SEARCH_RESOLVER + criteria row 1389 + leave-mask row {cid, 0x0800}) -- needs 3 phantoms (cls2, populate, mask); its native resolver adds exactly ONE card, so BD needs its OWN resolver.
- Step protocol precedent: BD's own C1 cost (c1_cost/c1_handler/c1_filt, DEP-derived 0..3 pick loop) -- NOT yet user-tested, so its protocol is itself unproven.
PLAN: virtual cls2 record (like C1) with COND = Deck holds a feasible set + once-per-turn (Souleating-Oviraptor-style HOPT), and a custom RES that loops: open picker over a dynamic candidate set (Rock, in Deck, not already picked, Level <= remaining r, and a completion exists with the picks left) -> 0x021C72CC mover -> r -= Level; stop when r == 0.
  Feasibility(r, k): r==0 -> true; k==0 -> false; exists Rock card (distinct) with Level l <= r and feasible(r-l, k-1). Valid partitions of 8: {8},{1,7},{2,6},{3,5},{4,4},{1,1,6},{1,2,5},{1,3,4},{2,2,4},{2,3,3}. Write in C (asm/cc.py).
UNPROVEN (each must be PROVEN before code, CLAUDE.md pre-build checklist): (1) 0x021C72CC arg shape (side, word*) from a custom caller; (2) the picker can be re-opened for picks 2 and 3 inside a RES phase machine with a dynamic callback filter (DEP proved it for a COST, not a RES); (3) a leave-mask trigger for a Level-8 donor (Recruiter is Lv3 Normal donor; Block Dragon donor Giant Flea 0x0FDD is a Normal monster); (4) 3 free phantoms (cls2, populate, mask) + a virtual criteria row; (5) the zone the Deck candidates are read from + the Deck-walk callback signature; (6) HOPT stamp site; (7) ov5 space: ~0x170 B left (CAVE_FREE 0x023AE460, ceiling 0x023AE520): C3 needs far more -> another RESERVE raise + a chain rebuild (6 min fast build).
NEXT EXPERIMENT (cheapest discriminator for (1)/(2)): a probe RES that, via GDB in the CPU rig, runs a 2-step pick over the Deck and logs [0x0229DD94+0x34], 0x0219C510 and the hand count before/after 0x021C72CC.

## C3 probe RESULT (2026-11-09; GDB CPU-vs-CPU on rom_c3_probe.nds [throwaway: rom_block_dragon + a probe stub in the CPU hand loop]; scratch/_build_c3_probe.py, otn_enhanced/cards/c/c3_probe.c, scratch/gdb_c3_probe.py; NOT user-confirmed)
- Static read: 0x021C72CC(side, word*) is `movs r2,#1 ; bx -> 0x021C72D8`, a function that derives the card ref from [word*] ((w>>23&0xFF)*2 + (w>>14&1)) and scans the player's Deck array (player+0x304) for it.
- PROVEN (1 sample, seed 0): calling 0x021C72CC(side 0, &DeckTopWord = 0x0229AF98) from a custom stub returned 1; the Deck-top card (word 0x0B800FDC = Gokibore) was NOT in the hand 2 visits later (hand 6, deck 34, unchanged) and WAS in the hand 55 visits later (card matched on cid + ref bits, deck 32). => the mover is DEFERRED (queued), not synchronous, and works from a custom caller with a pointer to a Deck array word. Caveat: only the cid+ref match was checked, one duel.
- STILL UNPROVEN for C3: (2) re-opening the picker 0x0219C430 for picks 2 and 3 inside a RES phase machine with a dynamic callback filter -- the CPU seat never opens a picker (human UI only), so this needs a HUMAN duel or a savestate; (3) leave-mask trigger on this donor; (4) phantoms (cls2/populate/mask) + virtual criteria row; (5) Deck walk callback signature; (6) HOPT stamp; (7) ov5 space (~0x170 B left, C3 needs a RESERVE raise + chain rebuild).
- Because the mover is deferred, an ADD loop may call it once per pick without waiting; but the picker-for-pick-2 filter must treat already-picked cards as excluded by ref (they are still in the Deck array until the queue drains).

## USER REPORT 2026-11-09 (in-game, rom_block_dragon.nds with C1 hand + CPU + C2)
- User's words, verbatim: "I have tested C2 and the hand summon, they work for me, just left with C3... test in CPU duel?"
- in-game confirmed by user 2026-11-09: C2 (Rocks cannot be destroyed except by battle) and the C1 HAND special summon. The exact checks they ran were not stated (so NOT claimed: human GY-origin summon [unbuilt], C3 [unbuilt], once-vs-twice payment detail beyond "work").

## USER REPORT 2026-11-09 (in-game): C3
- User's words, verbatim: "i have tested it and can confirm it works"
- MY INTERPRETATION: they ran C3 on data/over_the_nexus/working/rom_block_dragon.nds (sha256 8e7a853d...0b664: C1 hand + CPU + C2 + C3, built on the 2026-11-09 11:46 chain, RESERVE 0x14C00) and the effect did what the printed text says. The individual checks they ran (once per turn, 1-3 Rocks totalling Level 8, no-fizzle activation, never missing timing, human picker) were NOT listed.
- in-game confirmed by user 2026-11-09: C3 "works" -- scope exactly as worded above; the itemised behaviours are not separately confirmed.
- Not run to completion: the 5-seed CPU trace (scratch/gdb_c3_cpu.py) was stopped when the user's result arrived; seed 0 showed no Block Dragon leave. So there is NO CPU-duel evidence for C3, and the descriptor shape of the leave-trigger lookup was never sampled (the virtual-record split in the H1 front rests on the user's in-game pass).
- Still unbuilt: C1's GY-origin summon ("Special Summoned from your hand or GY"). Not in the chain / steps.STEPS (shipping not approved).

## C3 CPU evidence + descriptor shapes (2026-11-09; rom_bd_noc2.nds = Block Dragon WITHOUT C2 [BD_NO_C2 probe toggle in block_dragon.py], CPU-vs-CPU rig, Dark Hole/Raigeki deck; scratch/gdb_c3_cpu.py, results scratch/gdb_c3_cpu_noc2_seed{1,2,3}.json; NOT user-confirmed)
- Seed 2: COND ret 1 once, COST once, RES phases 0x80 x1, 0x7F x3, 0x7E x2, 0x7D x2, 0x64 x1; hand-add mover called twice: Beta The Magnet Warrior (Lv4 Rock) + Gamma The Magnet Warrior (Lv4 Rock) = Level 8, 2 cards.
  Seed 3: Beta + Beta (two copies, Lv4 + Lv4 = 8): the second pick was a different copy (refs deduped). Seed 1: Block Dragon never left the field. => the stepwise picker (picker re-opened for pick 2), the Level-sum filter and the loop end (third 0x7F sees total 0 -> 0x64) work for a CPU seat. (User separately confirmed C3 in-game.)
- DESCRIPTOR SHAPES at the find_event_handler miss tail for cid 0x0FDD (desc bytes +2..+5 = side, +3 zone, +4 type, +5 table): leave trigger = [+3]=0x0E, [+4]=0x1D, [+5]=0x02; (other samples: cls1 lookups [+5]=1, cls3 lookups [+5]=3). Dragon Rulers' H1 (read) serves GY ignition lookups as [+5]==2, [+3]==0xE, [+4] <= 6 (hand: [+3]==0xB, [+4]==0). => leave trigger ([+4]=0x1D) and GY ignition ([+4] <= 6) are DISTINGUISHABLE.

## USER REPORTS 2026-11-09 (in-game, rom_block_dragon.nds with the GY half, sha 34683289...7ab4)
- GY summon, user's words verbatim: "I tested the GY summon - with block dragon in the GY, i activated its effect, banished 3 rocks but it did not summon". Reading confirmed by user ("Yes, that's it"): GY effect offered + activated, 3-pick cost paid (3 Rocks banished), Block Dragon NOT summoned. => BUG, not an accepted deviation. Open: which silent exit of the shared GY resolver 0x0220731C returned 0 (canSS 0x02207330, zone gate 0x022073F6, ref/zone/2-bit mismatch 0x022074F4, ptr 0x022074B4, gates 0x021BA440 @0x022074C6 / 0x021BA258 @0x022074DA, success call 0x0226925C @0x022074EA). CPU rig never activates the GY SS (seed 1-2: no GYRES hit) -> needs a user savestate right after the failure, to replay the resolver offline.
- C3 on discard, user's words verbatim: "C3 was not offered to me when I discard it." => in a human duel C3 is NOT offered when Block Dragon is discarded from the hand (no over-trigger there). The CPU-rig sample [+4]=0x17 lookup that ran C3 (gdb_c3_cpu seed 1) is therefore not a hand discard; its cause is unidentified (candidates: a field-leave variant such as battle destruction). The H1 front still serves C3 for every non-hand, non-GY-ignition cls2 lookup of the cid: narrowing it to [+4] in the proven leave values is an open hardening item.

## GY summon FAILURE DIAGNOSED from the user's savestate (2026-11-09; data/over_the_nexus/working/rom_block_dragon.ml2, replayed with scratch/_gy_replay.py over scratch/thumbemu.py)
- Board in the state: side 0 no monsters; hand Into the Void / Graceful Charity / Morphing Jar; GY Block Dragon x2 (words 0x01800FDD ref 6, 0x01000FDD ref 4), Graceful Charity; banished Legendary Jujitsu Master, Neo-Spacian Grand Mole, Block Dragon. Descriptor (0x0229A7FC): cid 0x0FDD, side 0, zone [+3]=0x0E, type [+4]=0, table [+5]=2, cost_ran [+7]=1, desc[+0xC]=ref 4 (the Block Dragon in the GY at index 2), [+0xE]=0.
- Replay of the shared GY resolver 0x0220731C over that memory (ITCM veneers/literals of the speed patch restored to stock for the emulator; ev 0/1/2/0x80 all identical): canSS passes, free-zone gate 0x021B9EC0 passes, zone compare (locator -> 0x0E) passes, 2-bit compare passes (desc[+0xE]=0 = table bits), then `0x021A2618(&word)` returns 0 -> `return 0` at 0x022074B2 with NO summon.
- 0x021A2618(word*) = `0x020232AC(cid) ? ((word << 16) >> 31) : 1`: a card WITH A SUMMON RESTRICTION (classifier 0x020231C8 class > 0; Block Dragon is nomi class 4) may be Special Summoned from the GY only if bit 15 of its card word ("properly Special Summoned") is set. The two Block Dragons in the user's GY were DISCARDED (never summoned) so bit 15 = 0. (Independent corroboration: another session's coral_dragon note, ov5_cave CAVE_CORAL_C2COND: "GY card's word bit 15 (properly summoned)".)
- OFFLINE PROOF OF THE FIX: setting bit 15 on the GY word (0x01000FDD -> 0x01008FDD at 0x0229B1F8) makes the same replay pass 0x021A2618 and BOTH legality gates (0x021BA440 / 0x021BA258) and reach the summon call 0x0226925C @0x022074EA.
- FIX BUILT: CAVE_BD_GYRES 0x023AEB60 (0x30): GY record +04 = wrapper that sets bit 15 on the card word found by desc[+0xC] (0x021A25E9) then tail-calls 0x0220731D. rom_block_dragon.nds sha256 ebb1ab89...b11ea, 88/88 static. AWAITING IN-GAME RETEST (the same setup: Block Dragon discarded to the GY, 3 other EARTH across hand/GY, free zone).
- Note: another session is claiming ov5 slots right after mine (CAVE_CORAL_* 0x023AEA70..0x023AEB60); CAVE_FREE moved to 0x023AEB90 after my claim.

## USER REPORT 2026-11-09: GY summon fixed + SHIP APPROVAL
- User's words, verbatim: "Okay that works, Is that everything? if so ship"
- in-game confirmed by user 2026-11-09: the C1 GY-origin Special Summon works (rom_block_dragon.nds sha256 ebb1ab89...b11ea, with the bit-15 wrapper). Together with the earlier confirmations (C1 hand summon + C2 "they work for me"; C3 "i have tested it and can confirm it works") every printed clause is now user-confirmed. Not separately reported by the user: the "Cannot be Normal Summoned/Set" block, and a human test of the CPU-side pieces (Elemental Lords / Dragon Rulers CPU play) that ride in this module.
- Ship approval = the user's explicit "ship" (2026-11-09) for Block Dragon.

## SHIPPED 2026-11-09 (user: "Ship it, but also split out the Elemental Lords and Dragon Ruler work out of the block dragon module.")
- steps.STEPS: "Block Dragon" (cards.block_dragon) then "CPU hand Special Summons (Elemental Lords, Dragon Rulers, Block Dragon)" (cards.cpu_hand_ss, a card-less module: CPU hand-loop front at ov5 0x02340F16 -> CPUL / shared hand-SS trampoline, PAY registry handler, 5 registry rows on phantoms 0x0FDE/0x0E5C/0x0E60/0x112E/0x128C). gy_vrow_hook.ARMS carries Block Dragon's row (table now FULL 16/16).
- Chain build: 128/128 steps, rom_all_patches.nds sha256 ebb1ab8990ae0b2be12fadad3c2095476bf8f9745bc658f35253bca2af7b11ea (129,831,048 B), asserted from the build's own output. This hash is IDENTICAL to the user-tested single-card Block Dragon ROM (the one with the GY fix that the user confirmed), i.e. the module split moved code without changing one byte.
- First two ship builds died: (1) bulk_card_pack.py still keyed the donor as "Giant Flea" -> renamed to "Block Dragon" (same pack slot 53); (2) the second error was only the build's stdout cp1252 crash printing a Japanese character (run with PYTHONIOENCODING=utf-8). A concurrent chain build by another session (coral_dragon) shares the working dir; do not run two chain builds at once.
- Verify sweep: Block Dragon and cpu_hand_ss PASS. Eight older modules asserted "my front owns the shared site": seal_of_orichalcos (C hook BL), shadow_mist (miss node hop limit 6 -> 12), windrose (CPU planner site), dragon_rulers (ARM9 H4), immortal_phoenix_gearfried + disguise_copycat (ARM9 H4), infernoble (2 ARM9 H4 checks), predaplant / phoenix_gearblade (miss node: dc_next entries added). Fix = ov5_cave.dc_next += {BD_C3MISS: PD_MISS, BD_C2W: 0x021B2B10, BD_AI: WR_AICLASS} and a new ov5_cave.dc_ahead_of(owner) helper the verify()s use. data.bulk_ydcs (":wcs084_formula ... does not match CHANGES") fails before and after, from the user's uncommitted deck edits -- not touched.
- Not separately user-reported: the "Cannot be Normal Summoned/Set" block; a human test of the CPU-side pieces (Elemental Lords / Dragon Rulers CPU play), which are CPU-vs-CPU evidence only.

## CARD ART registered 2026-11-09 (user: "Ship the predaplant art too"; "they are both in implemented")
- data/card_art.py: CardArt(0x0FDD 'block_dragon'), CardArt(0x0FED 'predaplant_darlingtonia_cobra'), CardArt(0x17CF 'predaplant_ophrys_scorpio'); PNGs in data/over_the_nexus/card_arts/implemented/<folder>/ (32x32 + 64x64 RGBA + artwork_full). I first looked in card_arts/ (not implemented/) and wrongly told the user there was no Block Dragon art.
- Chain rebuild: 128/128 steps, exit 0, rom_all_patches.nds sha256 522873acbd81cea1070a569a5a4a29ea7cb65c1aa69061048e50238b34a1b9fe (129,831,048 B; was ebb1ab89... before the art). The art step has no verify(); the art is NOT checked in-game -- AWAITING the user's look in the deck editor / duel.
