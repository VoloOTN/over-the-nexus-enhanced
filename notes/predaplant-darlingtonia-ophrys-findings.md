# Predaplant Darlingtonia Cobra + Ophrys Scorpio — findings

## Confirmed
- Printed text (scratch/ygoprodeck_cache.json, this session):
  - Darlingtonia Cobra (Lv3 DARK Plant 1000/1500): "If this card is Special Summoned by the effect of a "Predaplant" monster: You can add 1 "Polymerization" Spell Card or "Fusion" Spell Card from your Deck to your hand. ... once per Duel."
  - Ophrys Scorpio (Lv3 DARK Plant 1200/800): "If this card is Normal or Special Summoned: You can send 1 monster from your hand to the GY; Special Summon 1 "Predaplant" monster from your Deck, except "Predaplant Ophrys Scorpio". ... once per turn."
- User (2026-11-06): the 3DS does not ship either card; there is NO Predaplant set code. No repo code/notes mention Predaplant (grep this session).
- User confirmed clause split D1-D3 / O1-O3, all in scope.

## Ruled Out
- 3DS second-source lookup: user says cards absent from 3DS -> no Konami handler to clone.

## Open Questions
- New set code "Predaplant": candidates per archetype_setcode_tables.yaml (UNVERIFIED this session, read from YAML only): 0x28 (2 phantoms, all-phantom, no aux rows per YAML note), 0x2A taken (Ninjitsu Art/Hanzo), 0x6E taken (Psi-Reflector, ov5 list). Need ledger re-read + thunk walk.
- Only two Predaplants exist -> Ophrys' Deck target = Darlingtonia only (except itself); needs Darlingtonia in Deck.
- "Special Summoned by the effect of a Predaplant monster": need a summon-source discriminator; Darlingtonia has no own summon procedure, so a plain "Special Summoned" gate would also fire from Monster Reborn etc. (deviation -> user decision).
- Fusion Spell search: "Polymerization or Fusion Spell" — set code for "Fusion"? Existing criteria lists (brilliant-fusion-findings.md: list A contains Polymerization 0x12E5, Fusion 0x1A7E) may serve.
- Donors (Normal, ATK<=1500, records-free): not yet chosen.

## Next Experiment
- Re-read allocations ledger for set code 0x28; walk thunk table; pick 2 donors from notes/donor-pool-normal-and-effectless-fusion.md candidates; run full pre-build risk checklist.

## Session 2026-11-06 update (user: "Exact Ophrys-only gate")
### Confirmed (this session, committed arm9 oracle)
- has_set_code[0x28] = thunk 0x02023AF1, standard shape; list @0x0209C582, count 2: [0x1433, 0x1434]. No stock criteria row has aux 0x28 (scanned ov3 table 0x022713C4, 1451 rows). card_prop status of 0x1433/0x1434 NOT yet checked (YAML claims phantoms) -> UNVERIFIED.
- donor_scan --free (66 clean Normals). ATK<=1500 shortlist: Toon Alligator 0x1123 (800/1600), Grappler 0x0FF3 (1300/1200), Gokibore 0x0FDC (1200/1400), Big Insect 0x0FD7 (1200/1500), Jellyfish 0x0FED (1200/1500), Skull Dog Marron 0x17CF (1350/2000), Dragon Dwelling 0x14D8 (1300/2000), Chamberlain 0x1C6C (200/2000). Not in steps/cards (grep otn_enhanced). Giant Flea 0x0FDD / Koumori 0x0FC5 / Red Archery Girl 0x127B / Illusory Gentleman 0x139B excluded: referenced in KB or shipped modules.
- Precedents to read next (UNVERIFIED reuse): Noble Knight Medraut / Infernoble Ogier+Oliver (Deck SS native 0x02206CAC, Deck-pick callback), Gates of Dark World / Lightpulsar (hand cost).
### Open
- Exact Ophrys-only gate for Darlingtonia D1: needs a summon-source flag stamped by Ophrys resolver; mechanism UNPROVEN.
- Set-code grows: Predaplant list only 2 slots -> exactly Darlingtonia+Ophrys donors. OK.

## Donors (user pick 2026-11-06): Darlingtonia = Jellyfish 0x0FED, Ophrys = Skull Dog Marron 0x17CF
- donor_scan this session: both "VERDICT: CLEAN - no data structure names this cid". 0x0FED has 9 ARM9 data-region + 12 ov3 code-region u16 hits (ambiguous/instruction encodings, NOT yet dumped); 0x17CF has none. Name floors 6 B / 10 B, irrelevant once in CARD_TEXT.
- Per-cid gate check beyond data tables (stack-switch blind spot) and the 0x0FED hits: UNVERIFIED.

## Precedents identified (module headers read this session; implementation reuse UNVERIFIED)
- Darlingtonia D1-D3: cards/shadow_mist.py C1 ("If SS: add 1 named Spell from Deck", "You can" trigger, once-per-X lock, criteria via LIST_CODE9) + cards/brilliant_fusion_findings (list A holds Polymerization 0x12E5, Fusion 0x1A7E; 'Fusion' Spell family may need a 2-entry criteria list).
- Ophrys O1/O3: cards/souleating_oviraptor.py ("Normal or Special Summoned" cls1 trigger, once per turn, Deck pick).
- Ophrys O2 Deck SS of archetype minus self: Noble Knight Medraut / Infernoble Ogier+Oliver (native Deck SS 0x02206CAC).
- Ophrys hand-discard cost: cards/dragunity_remus.py C4 / cards/gates_of_dark_world.py (cost-vs-effect discard) / raiden_cost.c.
- Cards are now written in otn_enhanced/dsl.py (card, CLS1, SetCodeTable, ...), so the patch should be a DSL module, not hand Thumb.

## Pre-build risk checklist status
1. Per-cid gates on donors: data tables PROVEN clean (donor_scan); stack-switch blind spot + 0x0FED's 9 ARM9 / 12 ov3 hits ASSUMED harmless.
2. Zone: Ophrys Deck-SS and hand-cost zones ASSUMED from precedent; disassembly not yet read.
3. Blob lengths: moot via CARD_TEXT re-emit (ASSUMED until cids added).
4. OPT flag stamp (Ophrys per-turn, Darlingtonia per-Duel): ASSUMED; per-Duel needs a flag that survives turns -- no precedent found yet.
5. Ophrys-only SS-source flag: UNPROVEN.

## Proof pass 1 (2026-11-06)
### Confirmed (read from repo sources this session; engine facts themselves NOT re-executed)
- Once-per-Duel: turn-log kind 5 (never swept) = per Duel; same turn-log pair as once-per-turn (kind 1). Used by infernoble.py (C3 keys 0x4FD4/0x2FD4), junk_speeder, unknown_synchron (in-game corroborated per author_facts ~2532), revolution_synchron cls2 +10 stamp. -> Darlingtonia D3 has a precedent; stamp kind 5 on its cid.
- Precedent for "SS by the effect of a <archetype> card": notes/ceruli-findings.md CLAUSE 2 -- user proposed INLINING the follow-on into the summoning clause's own resolver; it is then reachable only from that summon (cannot fire on Monster Reborn). Exactly the Ophrys-only gate, no latch, no summon-source flag needed.
### Design (proposal, unproven): Ophrys resolver, after the Deck SS of Darlingtonia, runs Darlingtonia's search inline (per-Duel check kind 5 on Darlingtonia cid, optional Yes/No prompt precedent: otn-warwolf-e1-proactive-prompt, then add Polymerization/Fusion Spell from Deck to hand).
- Exact for the current archetype (Ophrys is the only Predaplant that Special Summons). Add a 2nd Predaplant summoner later => the inline path must be extended.
- Side effect to confirm: Darlingtonia's search is then NOT a separate cls1 trigger, so it wouldn't fire if Darlingtonia were SS'd by some other Predaplant effect (none exist in this ROM).
### Still unproven
- Hand-cost zone + Deck-SS zone disassembly; optional Yes/No prompt inside a resolver; Polymerization/Fusion criteria list; set-code 0x28 phantoms' card_prop status.

## Proof pass 2 (2026-11-06; user approved inlining Darlingtonia's search into Ophrys's resolver)
### Confirmed
- Set-code 0x28 list [0x1433, 0x1434]: BOTH ABSENT from card_prop (donor_scan.cards() keyed by cid: `0x1433 in cards() == False`, same for 0x1434; 0xFED and 0x17CF present). => phantoms, free to overwrite count-neutrally (YAML claim now backed by this session's check; still need ledger/PHANTOM_CLAIMS entry when claimed).
### From KB YAML (counter_engine.yaml, NOT re-executed this session) -> UNVERIFIED until proof run
- Ophrys O2 template: native Deck-SS resolver 0x02206CAC (counter.deck_ss_resolver; Shien's Footsoldier 0x1B3A cls2 slot +04) + criteria handler 0x0223CAB5 with aux = has_set_code index (=0x28) = "SS set-code-filtered monster from your Deck". Exclusion of Ophrys itself: trivial here (Ophrys is the one that would need excluding but is also a member; check handler or lock).
- Ceruli resolver shape (cards/ceruli.py): phase 0x80 first entry, return 0x7F to get a later phase for the follow-on; inline follow-on reachable only from the summon.
### Still open (build-blocking)
1. Optional ("You can") Yes/No for Darlingtonia's inline search: Ceruli's follow-on is mandatory. Prompt-in-resolver precedent: otn-warwolf-e1-proactive-prompt (hook path unproven here).
2. Fusion-Spell Deck-search criteria row: Polymerization 0x12E5 + Fusion 0x1A7E (brilliant-fusion list A) + other "Fusion" Spells (Future Fusion, Miracle Fusion, ... must define list).
3. Hand-discard COST + Ophrys's own once-per-turn (turnlog kind 1) in the activation path of a Normal-or-Special-Summoned cls1 trigger (Oviraptor C1, Gates of Dark World cost shapes).
4. Darlingtonia must have an own record? If its search is only inline, Darlingtonia needs no cls1 record; but the donor Normal still must become an Effect-typed card? Effect type optional (no own effect) -- decide.

## Search list decision (user, 2026-11-06): "Poly + every 'Fusion' Spell"
- CORRECTION: earlier notes call 0x1A7E "Fusion"; it is FUTURE FUSION. No card is named exactly "Fusion" (checked donor_scan.cards() names + ygoprodeck cache).
- Confirmed (arm9 oracle walk of all standard has_set_code thunks, this session): set code **0x59** list @0x0209CDB8, 29 entries, already IS the Polymerization/"Fusion" family: Polymerization 0x12E5, Fusion Sage, De-Fusion, Fusion Gate, Fusion Sword Murasame Blade, Dimension Fusion, Fusion Weapon, Re-Fusion, Fusion Recovery, Miracle Fusion, Future Fusion, Overload Fusion, Instant Fusion, Dark Fusion, Revoke Fusion, Super Polymerization, Parallel World Fusion, Gem-Knight Fusion, Miracle Synchro Fusion, Pyroxene Fusion (a Trap -> filtered by card-type bits), + Speed Spell variants and 4 phantoms (0xEA4, 0xEAB, 0x1303 [claimed list-A phantom], ...).
- => Darlingtonia's search = ONE criteria row {handler 0x0223CAF5-style search, aux 0x59, word = Spell type}; no new list. Needs: which word value selects Spell cards (precedent: Remus/Dragon Ravine, Shadow Mist "Change" search) -> UNVERIFIED.
- Super Polymerization / De-Fusion / Re-Fusion / Revoke Fusion are in the list (name contains Fusion / Polymerization); printed text says "Fusion" Spell Card, so these count -- flag in the final report as natural behaviour of the native list, not a deviation.

## Proof pass 3 (2026-11-06) -- prompt + cost shapes (read from memory notes/source; nothing executed)
- The engine has NO free-standing Yes/No popup call to inline: the optional prompt is the cls1/cls2 record's +10 "You can" tag (0x021E51E5; body 0x021E50DC), per Shadow Mist (cards/shadow_mist.py) and Oviraptor (cost stub entry -> fn_021E5060 "You can" rider). Warwolf note: the "proactive popup" pivot was a red herring on the 3DS. => An INLINE follow-on (Ceruli) is necessarily MANDATORY. It cannot be the optional "You can" the printed text has.
- OPTIONS for D1 optionality: (A) inline mandatory search = declared deviation (rejected by CLAUDE.md "bug until user says otherwise"); (B) Darlingtonia gets its own cls1 SS-trigger "You can" record (Shadow Mist C1 shape: code-9 list 0x0228F63A membership + never-miss cid-tree admission 0x021EE0E0) whose CONDITION stub tests an Ophrys-written turn-log stamp (Ophrys resolver stamps just before the Deck SS commit) => still Ophrys-only, optional, once-per-Duel kind 5.
- Risks for (B): needs a stamp kind that survives until Darlingtonia's trigger is polled but not beyond the turn; code-9 list has phantoms (Ceruli note: list has 5 phantoms, UNVERIFIED now); "You can" miss-timing tree admission mandatory (Shadow Mist lesson).
- Ophrys cost: criteria handler for "select from HAND" 0x0223CB19 (== 3DS 0x004ABE08 per CLAUDE.md); cost stubs in cards/c/*_cost.c log turnlog (side,cid,kind 1 = once per turn) -- pattern ds_cost.c/raiden_cost.c. Monster-only filter via the row word's card-type bits (UNVERIFIED which value). Printed "send to GY" is NOT "discard": no Dark-World-style discard trigger must fire -> use the send-to-GY mover, not the effect-discard post 0x022598A0 (UNVERIFIED mover address).

## Proof pass 4 (2026-11-06) -- user chose "Own trigger + stamp" for Darlingtonia D1
- Template: cards/shadow_mist.py clause 1 (special_summoned_..._search_shared_lock): code-9 list row + cls1 {add_to_hand 0x02207EF5, 0, +0C cond, +10 slot4 "You can" 0x021E51E5, 0} + criteria rel 0 (named/set-code search) + never_miss_timing node 0x021EE10C front stub (Eva note: every donor ends at that node; add a FRONT STUB tail-jumping to block A, `_miss_node_reaches_a` tolerates it). Cond stub = turn-log query (side, cid, kind) -> have_target 0x021F0821. For Darlingtonia the cond must query the Ophrys STAMP instead of the used-lock; +10 stamps kind 5 (per Duel).
- BLOCKER FOUND: the code-9 ("when Special Summoned") list 0x0228F63A (31 entries, ov3 oracle, count read this session) has NO free phantom. Its 5 stock phantoms 0x0E12, 0x167C, 0x176C, 0x1ABE, 0x1ABF are ALL claimed (allocations.yaml: Hanzo, Psi-Reflector, Shadow Mist, Norden, Oviraptor). All other 26 entries are real cards (Hero Kid, Gladiator Beast Spartacus, ... Scrap Searcher). The list is binary-searched with a hard-coded count => a new member must displace a real card (cost = that card loses its SS trigger) or use another route.
- Routes (UNPROVEN): (1) displace a real code-9 member whose trigger is dead/irrelevant (needs per-member audit: which are Extra-Deck/inert); (2) SS-commit hook (otn-summon-event-dispatch-tg) -- Ophrys's own resolver already runs at the exact commit; (3) fall back to mandatory inline (declared deviation).
- NOTE: the "shared summon-trigger hook" (summon_trigger_hook.py, list 0x0228F6C0) is for Synchro/Fusion/Ritual Summons only -- NOT this list.

## Proof pass 5 (2026-11-06) -- SS-commit/c9 route: SOLVED by an existing shared hook
- FOUND (source read + executed this session): otn_enhanced/effects/c9_trigger_hook.py = the shared plain-Special-Summon trigger hook for the FULL code-9 list. Site 0x022658BC (`cmp r0,#0 ; beq`, 4 B), stub CAVE_C9TRIG 0x023A85B0, ARMS register of cids, RESERVE 0x30. A donor joins by adding ONE ARMS entry -- no list slot needed. Currently 2 arms (Water Spirit 0x1E05 -> Renaud C3, in-game confirmed 2026-10-20 per module; Rabid Horseman 0x1002 -> Angelica).
- MEASURED: c9.stub() is 40 B with 2 arms, 48 B with a 3rd (Jellyfish 0x0FED) == RESERVE 0x30 exactly -> Darlingtonia fits as the 3rd arm, a 4th arm would need the stub re-homed (c79 precedent: 0x30 -> 0x40).
- Closest precedent for D1: infernoble.py card 5 / Renaud C3 ("If SS: You can ... add it to your hand", OPT): c9 arm + cls1 {R_RES add resolver, 0, R_COND, "You can" 0x021E51E5, target step}. Darlingtonia swaps: resolver = add-to-hand 0x02207EF5 (Shadow Mist C1), criteria row aux 0x59 Spell, cond = Ophrys stamp && per-Duel kind 5 unused.
- Still needed: never-miss node admission (0x021EE10C front stub) for 0x0FED; Ophrys stamp kind/lifetime; cls1 phantom + criteria phantom (count-neutral) claimed in ledger.

## Proof pass 6 (2026-11-06) -- Ophrys trigger path
- Ophrys "Normal or Special Summoned" = c79_trigger_hook.py ARMS (site 0x02265C44, code-7-or-9 list verdict). MEASURED: c79.stub() is 60 B with the 4 current arms (Windrose 0x190B, Ogier 0x13A3, Ricciardetto 0x0FE6, Disguise 0x111E), 68 B with Skull Dog Marron 0x17CF as a 5th, RESERVE is 0x40 (64) => **5th arm OVERFLOWS**. Needs a re-home of CAVE_C79TRIG to a 0x50 slot at CAVE_FREE (now 0x023ADA40; current slot 0x023AC970 (0x40)); precedent: re-homed 0x023A53F0 -> 0x023AC970 on 2026-11-04 (CAVE_C79TRIG_OLD retired). Touches the shared slot of 4 SHIPPED cards -> every one must be re-verified after.
- Hand cost: Darkflare Dragon C2 (cards.yaml card.darkflare..., in-game confirmed 2026-08-18) = criteria HAND row handler 0x0223CB65 (word 0x08000002 = Dragon-filtered; monster-any would be 0x...0002 low bits), native hand cost 0x021E7245 owns slot4 steps 0..3; LESSON (2): the DEFAULT arm of 0x021E7245 posts NO once-per-turn latch -> wrapper must call 0x021E5060 itself. Eva note: for an optional trigger with a cost put the cost in +14 and stamp OPT there ("You can" native +10 0x021E51E5). Both UNVERIFIED for a cls1 SS trigger.
- Deck SS of set-code 0x28: handler 0x0223CAB5 aux 0x28 (Shien's Footsoldier shape, counter.deck_ss_resolver 0x02206CAC). Exclude-self: unresolved -- Ophrys is itself a member (donor 0x17CF in the list). Options: bit 0x20 "except this card" in the row word as Shadow Mist's HERO row (0x22 = monster + except self) -- plausible, UNVERIFIED for 0x0223CAB5.
- Darlingtonia SS'd by Ophrys while Ophrys' stamp: stamp lifetime still open.

## Proof pass 7 (2026-11-06) -- user approved re-homing the c79 stub ("Yes, re-home it")
- Re-home plan (NOT yet executed): new CAVE_C79TRIG slot 0x50 B at CAVE_FREE (0x023ADA40 as read), retire the current 0x023AC970 (0x40) as CAVE_C79TRIG_OLD2 in ov5_cave.py + ledger, bump CAVE_FREE, RESERVE = 0x50 in c79_trigger_hook.py, then --emit allocations and re-verify Windrose, Ogier, Ricciardetto, Disguise. To be done together with the module (a lone re-home proves nothing).
- Disassembled this session (ov3 oracle, capstone, Thumb): 0x0223CAB4 is a thin wrapper -> shared Deck scanner 0x0223BC3C(side, cid, pool_lit, &out, [sp]=row desc+8, [sp+4]=0x0A mode, [sp+8]=row word/aux). The scanner tests row-word bits 0x01 (flip side), 0x02, 0x04 (0x021BAD70 check), 0x08/0x10 (0x021BA69C zone placement, 0xD = Deck), 0x20 (calls 0x02023008 on the CANDIDATE cid), 0x40, and 0xFE000000 (count cap). => bit 0x20 is a candidate-cid predicate, NOT proven to be "except this card". Shadow Mist's "except self" claim for word 0x22 is UNVERIFIED by this read.
- Exclude-self for Ophrys is therefore UNPROVEN. Note Ophrys itself is on the field when the effect resolves, so it only matters for OTHER copies of Ophrys in the Deck (3 allowed). Candidate designs: (a) a candidate-filter front on 0x0223BC3C keyed on the acting cid; (b) accept search = set-code 0x28 incl. other Ophrys copies (declared deviation, needs user ruling).

## Proof pass 8 (2026-11-06) -- exclude-self: NO FRONT NEEDED (supersedes the "UNPROVEN" verdict of pass 7)
- CORRECTION: pass 7's reading of bit 0x20 (scanner branch calling 0x02023008) mis-attributed the row-word bit; KB fact dispatch.criteria_word_bit5_is_except_self (VERIFIED, text-correlated 51/53 rows, 3DS Hanzo agrees) says criteria-word bit 5 (0x20) IS "except this card".
- Executed this session: listed every criteria row whose handler is 0x0223CAB4/5 (the set-code Deck-SS handler) from the ov3 oracle: THREE rows already carry bit 5 for printed "Special Summon ... from your Deck, except <self>": Batteryman Micro-Cell 0x1DB5 {aux 0x0E, word 0x900022} ("Special Summon 1 Level 4 or lower Batteryman monster from your Deck, except Batteryman Micro-Cell" -- printed text checked in ygoprodeck_cache), Koa'ki Meiru Urnight 0x21BC {aux 0x46, word 0x900022} (same, with a hand "reveal" cost + once per turn: the closest cost-shaped precedent), Tanngnjostr 0x2458 {aux 0x64, 0x22}.
- => Ophrys criteria row = {cid 0x17CF, aux 0x28, handler 0x0223CAB5, word 0x00000022} (monster + except-self; the 0x90xxxx high bits in the others are the "Level 4 or lower" cap Ophrys doesn't have). Also shows the handler is used by ignition (Urnight) and flip (Micro-Cell) cards, so a cls1 summon trigger is a new caller shape -> still UNPROVEN end-to-end.
- Exclude-self proof status: PROVEN by KB + row census; Ophrys-specific behaviour UNVERIFIED until in-game.

## BUILD PLAN (2026-11-06, user: "Yes, write it") -- module NOT yet written; this is the checkpoint
Template modules read this session: cards/disguise_copycat.py (layered-on-chain single-card ROM; stubs via `compile_c`/EffectBuilder; Row(CLSn, rec, phantom); fronts via dc_next), cards/shadow_mist.py (SS-trigger + You-can + never-miss), cards/infernoble.py card 5 Renaud C3 (c9 arm + cls1), cards/c/*.c with engine.h (turnlog_post/query, opt_used).
Layering decision: base = data/over_the_nexus/working/rom_all_patches.nds (chain incl. Disguise + Gearblade). Module stays OUT of steps.STEPS/SHIPPED until the user approves. Shared-hook arms (c79, c9, timing, criteria_row_hook) must NOT be added to the module-level ARMS tuples (Windrose's c79 install() would then ship an arm for a cid with no cls1 row): the module's install() writes `stub(base, ARMS + mine)` via effects.common.rewrite_shared, as Dark Law/Overtex do.
Data:
 1. set code 0x28 list 0x0209C582 (count 2 imm @0x02023AF0..): [0x1433,0x1434] -> sorted [0x0FED, 0x17CF]; PHANTOM_CLAIMS entries for both phantoms.
 2. Darlingtonia 0x0FED: cls1 {add_to_hand 0x02207EF5, 0, COND, SLOT4(You-can via dsl._hopt_you_can_stub-like, kind-5 per-Duel stamp), 0}; criteria row {0x0FED, aux 0x59, 0x0223CAF5, word = Spell}; c9 arm (3rd arm: 48 B == RESERVE); never-miss front AHEAD of Gearblade's (CAVE_PG_MISS -> CAVE_DC_MISS chain); COND = per-Duel unused AND Ophrys stamp this turn AND [0x02298A28+0xA]==0x0D (summoned from Deck) AND have_target 0x021F0821.
 3. Ophrys 0x17CF: cls1 {SS resolver wrapper (stamps Darlingtonia-arm key then native 0x02206CAD), 0, COND (OPT clear, hand monster, Deck member of 0x28 other than self), SLOT4 You-can, +14 cost (send 1 hand monster to GY; OPT stamp)}; criteria rel0 {0x17CF, 0x28, 0x0223CAB5, 0x22}; rel1 hand cost row {0x17CF, 0xFFFF, 0x0223CB65, monster word} via criteria_row_hook arm; c79 arm 5th -> RE-HOME stub to 0x50 B at CAVE_FREE (retire 0x023AC970 as CAVE_C79TRIG_OLD2); timing_class_hook arm; never-miss entry for 0x17CF.
 4. card_props: Darlingtonia Lv3 DARK Plant 1000/1500 Effect; Ophrys Lv3 DARK Plant 1200/800 Effect; card_text.CARD_TEXT entries for both (full printed text).
Unproven (must be proven or tested): send-to-GY mover address for the cost; cost-in-+14 on a cls1 summon trigger (Eva: cls2 GY trigger only); [SUMMON_DESC+0xA]==0xD at poll time; stamp lifetime/turn-log key semantics; rel1 hand row addressing for a cls1 record.
Ledger/housekeeping at build: ov5_cave CAVE_PD_* constants + CAVE_FREE bump, check_allocations PHANTOM_CLAIMS, `--emit`, donor-pool note move (0x0FED Jellyfish, 0x17CF Skull Dog Marron) -- ONLY when added to steps.py.

## BUILD 1 (2026-11-06) -- AWAITING IN-GAME TEST (nothing here is user-confirmed)
- ROM: data/over_the_nexus/working/rom_predaplant.nds, sha256 d4f988d25dafeeea951c23a026d4166d5c19b90b2164758f1bec7067d37159d8, layered on rom_all_patches.nds (single-card test ROM; module NOT in steps.STEPS / SHIPPED; no chain build run).
- Module: otn_enhanced/cards/predaplant.py (+ cards/c/predaplant.c, card_text entries 0x0FED/0x17CF, ov5_cave CAVE_PD_* + CAVE_C79TRIG re-homed to 0x023ADA40 (0x50 B), c79_trigger_hook.RESERVE 0x50, allocations ledger regenerated: no overlaps, no phantom double-claims).
- Own verify(): 0x0FED 25/25, 0x17CF 15/15 (emulator-independent static checks only).
- Design change on the way: criteria rows could NOT be inserted -- the criteria table's 4 spare phantoms (0xE12, 0x234E, 0x234F, 0x2511) are second stock copies that tg_striker / tg_warwolf / sea_lancer assert they keep (first attempt made 3 of them FAIL, reverted). Rows are therefore VIRTUAL (0xFF30/31/32 in CAVE_PD_ROWS 0x023ADC40) via H2/H3 fronts ahead of Gearfried's (Medraut's proven pattern). A criteria_row_hook arm would also have overflowed a Thumb cond-branch; not needed now (criteria_row_hook.py untouched).
- Sweep on rom_predaplant.nds: 110 passed / 6 failed. data.bulk_ydcs = pre-existing (user's ydc_decks.py). The other 5 are caused by the LAYERING, not regressions: windrose/infernoble/disguise assert the shared c79/c9 stubs equal their module ARMS (ours adds arms at install time on purpose, so Windrose's chain install can't ship an arm for an unbuilt cid); immortal_phoenix_gearfried / phoenix_gearblade assert their H2/H3/miss BL targets DIRECTLY and do not step over fronts placed ahead of theirs. Shipping would need: arms added to c79/c9 ARMS tuples, and those two checks made dc_skip-aware (small edits to shipped modules -- user decision).
- NOT run: step 5b CPU mirror duels (cardtest rig/mirror) -- not done, so no emulator evidence either.
### Still ASSUMED / unproven in-game
1. cost in cls1 +14 (native 0x021E7245 on a summon trigger); 2. [0x02298A28+0xA] == 0x0D at Darlingtonia's poll; 3. KEY_ARM stamp visible to Darlingtonia's cond (turnlog kind 1, slot 0x0B); 4. virtual-row selection by PROBE/cost-state in the H2 front for a cls1 trigger; 5. word 0x04 = Spell with the set-code 0x59 search; 6. hand-scan probe via 0x02243FE0 with a virtual row; 7. c79 re-home (4 shipped arms still work from the new stub).

## Step 5b CPU check (2026-11-06) -- emulator CPU evidence, NOT user-confirmed
- Rig: build/cpu_battery/cardtest/rig_rom_predaplant.nds from rom_predaplant.nds (sha256 d4f988d2...37159d8).
- cardtest rows 0x0FED 0x17CF: no ov5 CPU row for either (monster cids: expected, nothing to fix).
- Mirror 0x17CF (Ophrys x3 + Darlingtonia x3, Polymerization x3, Future Fusion x2, Fusion Gate x2 + Lightsworn filler; 8 duels, 4 jobs): Ophrys drawn 17 / summoned 8 / activated 8; kit total 150 / 67 / 106 (aggregates the filler too, not separable).
- Mirror 0x0FED (Darlingtonia x3 + Ophrys x3 + same Spells; 8 duels): Darlingtonia drawn 13 / summoned 4 / activated 3.
- Reading: the CPU draws, summons and activates both cards without a hang or freeze in 16 duels, so both trigger paths (c79 arm incl. the re-homed stub, c9 arm, cls1 records, virtual rows, cost) are reachable and run. It does NOT show: that Darlingtonia fires ONLY after Ophrys (3 activations vs 4 summons suggests at least one summon by another route did not activate -- plausibly a hand/Normal-Summon route correctly refused, UNVERIFIED), that the right card was sent/searched, or that the other copies of Ophrys are excluded. 'activated' counts come from the battery's instrumentation and were not cross-checked against the savestate.

## SHIPPED 2026-11-06 on user approval ("Ship without the art. I'll provide it later") -- IN-GAME TEST NOT REPORTED, AWAITING IN-GAME TEST
- steps.STEPS entry "Predaplant Darlingtonia Cobra + Ophrys Scorpio" after Phoenix Gearblade (the verify sweep reads STEPS directly; there is no separate SHIPPED list any more). Arms registered in c79_trigger_hook.ARMS (0x17CF) and c9_trigger_hook.ARMS (0x0FED); installs are idempotent for both a fresh chain and a ROM built before the card.
- Shared-code edits: ov5_cave (CAVE_C79TRIG re-homed to 0x023ADA40/0x50 B, CAVE_PD_* slots, CAVE_FREE 0x023ADCF0, dc_next +PD_H2/H3/MISS), c79 RESERVE 0x50, Gearfried + Gearblade checks now step over fronts ahead of theirs (dc_next walk), bulk_card_pack keys renamed Jellyfish/Skull Dog Marron -> the new names (the Card Pack step aborted the first chain build on the old key), donor-pool note updated.
- Chain: `-m otn_enhanced.build` 126/126 steps, 342.6 s, rom_all_patches.nds sha256 3f2c17a96eb21d0346fc5c0e9d62be3f080c7b055a81bc0faf9dae1503ebf671. Allocation check clean. Sweep: 116 passed / 1 failed (data.bulk_ydcs wcs084_formula deck, from the user's uncommitted ydc_decks.py, not this card). --compare against rom_baseline.nds NOT run (retired per memory ship-to-steps-only).
- NO custom card art yet (cards keep the donors' Jellyfish / Skull Dog Marron pictures): user will supply it; then add CardArt rows in data/card_art.py.
