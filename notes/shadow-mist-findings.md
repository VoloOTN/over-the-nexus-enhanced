# Elemental HERO Shadow Mist — findings

Status: build 3 (sha256 6b7f38bf...e17b75) IN-GAME CONFIRMED BY USER 2026-09-28 -- retest items 1-7
(Fusion / Synchro material, Tribute, destroy/mill/discard, decline-then-material, shared lock, Sinister
Sprocket regression) all "Confirmed"; user: "Ship it". Mask Change targeting still deferred (no DARK
Masked HERO). Started 2026-09-28.

Printed text (scratch/ygoprodeck_cache.json): "If this card is Special Summoned: You can add 1
"Change" Quick-Play Spell Card from your Deck to your hand. If this card is sent to the GY: You can
add 1 "HERO" monster from your Deck to your hand, except "Elemental HERO Shadow Mist". You can only
use 1 "Elemental HERO Shadow Mist" effect per turn, and only once that turn."
DARK / Warrior / Lv4 / 1000 / 1500.

User decisions 2026-09-28: all 3 clauses in scope; donor Ryu-Kishin Powered 0x111F; Shadow Mist
becomes a "HERO" by replacing Hero's Bond 0x1A81 in HERO list 0x0209C56C; C2 fires from ANY
location (Eclipse Wyvern PART E style).

## Confirmed
- Not in the NDS ROM; not in the 3DS build (3ds_extract/partition0/romfs/duel/card/CARD_Name_E.bin
  names ending " Change": Weapon/Synchro/Mask/Heraldry Change only).
- Only "Change" Quick-Play Spell in OTN = Mask Change (enhanced_card_data.json idx 4021; cid 0x236A).
  Form Change / Geargia Change absent (grep of enhanced_card_data.json).
- HERO set-code composite thunk 0x02023974 (disasm of rom_all_patches.nds ARM9) checks 6 lists via
  0x02022E14; last list 0x0209C56C count 1 = [0x1A81 Hero's Bond]. Only ARM9 literal referencing
  0x0209C56C is 0x020239F4 (byte search). E-HERO list 0x0209CFE4 count 0x3A=58, refs 0x02023824 /
  0x020239E0, no phantom.

- Donor 0x111F Ryu-Kishin Powered: `donor_scan 0x111F` -> "VERDICT: CLEAN - no data structure
  names this cid"; no finished_patches/steps reference (grep).
- Native any-location "sent to GY: You can add from Deck" template = Cross Porter 0x1D97 (stock rom.nds):
  cls2[335] {0x02207EF5, 0, +0C 0x021F0821, +10 0x021E51E5, 0}; mask row {0x1D97, 0x0800};
  crit rows {0x17, 0x0223CA71, 2} and {0x17, 0x0223CAF5, 2}. Stratos crit {0x1A80, 0x1B, 0x0223CAF5, 2}
  = HERO Deck search. Hero's Bond 0x1A81 has crit {0x8, 0x0223CA71, 0x900002} (E-HERO) -- unaffected
  by the list swap (the list only changes whether Hero's Bond itself counts as "HERO").
- PART E terminal node for 0x111F in sent-to-GY chain 0x021D1392 (scratch trace via
  patch_snoww._switch_leaf, identical on rom.nds and rom_all_patches.nds):
  `0x021D13BC bgt 0x021D13CC` (only inbound) ->
  `0x021D13CC subs r1,#0x10 (r1 = lit 0x1185 -> 0x1175) ; 0x021D13CE cmp r5,r1 ;
   0x021D13D0 beq 0x021D13E2 ; 0x021D13D2 b 0x021D19C0 (reject)`. Stock verdict: reject.
  - 0x1175 = PHANTOM (donor_scan: no card_prop row). Its arm 0x021D13E2 -> 0x021D1872 is a
    conditional hand-discard arm (src zone 0x0B, [sp+0x18], [sp+0x20], r4==r7) -- NOT wanted.
  - 0x021D13FC = native `b 0x021D1938` -> `b 0x021D199E` -> `movs r0,#1 ; str r0,[sp,#0x14]` = ACCEPT.
  - No branch anywhere in ov3 targets 0x021D13CE/D0/D2 (full-overlay B/Bcc/BL scan).
  - r0 dead on all exits (reject 0x021D19C0 `ldr r0,[sp,#0x2c]`; accept `movs r0,#1`; occupant arm
    `ldr r0,[sp,#0x34]`). r1 reloaded at 0x021D19CC before use on the accept tail.
  => PLAN: in-place re-key, NO stub: 0x021D13CC `subs r1,#0x66` (0x3966) and 0x021D13D0
     `beq 0x021D13FC` (0xD014). Only 0x1175 (phantom) loses its arm; 0x111F becomes ACCEPT.
     0x1175 is also Shooting Quasar's dropped cls2 phantom -- different pool, no clash.

- BUILT 2026-09-28: `_build_shadow_mist.py` -> data/over_the_nexus/working/rom_shadow_mist.nds,
  sha256 d5c8fc982e04fad6e0def128149d8ef0b63a97ba064c4aad66bd047d56e72d41; check_allocations clean;
  patch_shadow_mist.verify() 35/35 PASS (static). NOT in steps.STEPS.
  - Phantoms: SS list 0x176C, cls1 0x1190, cls2 0x0EBA, criteria 0x0EB7 (rel 0) / 0x0EB5 (rel 1),
    leave-mask 0x0EBA; all: no card_prop, one row, present in stock AND rom_all_patches, unclaimed.
  - ov5: CAVE_SM_COND 0x023A1FE8 (48 B), CAVE_SM_SLOT4 0x023A2018 (44 B); CAVE_FREE -> 0x023A2048.
    Disassembled: every BLX literal odd (0x021A14E9, 0x021F0821, 0x021E51E5, 0x021D2585); POP {..,PC}.
  - Shared hooks proven by EXECUTION (scratch/sm_equiv.py, thumbemu): stub with vs without ARM_SM --
    row hook 80640 inputs, timing hook 171360 inputs, ONLY 0x111F differs. 0x111F: row cls2 -> tail
    r4=1, every other class native (rel 0); timing cls1/cls2 -> 0x021E51E5 (class 2).
  - GATE: simulated chain on the built ROM: 0x111F -> accept store 0x021D19BE; whole 0..0x26FF walk
    vs stock: only 0x111F and 0x1175 moved.

- IN-GAME (user, 2026-09-28, build 1): "1. Confirmed" -- card face item 1 in-game confirmed by user
  2026-09-28. User also reported: "Cards like Stratos, E-Call, A Hero Lives cannot search shadow-mist".
  E-Call / A Hero Lives read "Elemental HERO" (set 0x08) -- build 1 only made it "HERO" (0x1B) via the
  Hero's Bond list, so that part is explained. Stratos (0x1B) failing is UNRESOLVED -- awaiting the user's
  answer on whether the search opened without it or nothing happened.
- BUILD 2 2026-09-28: Hero's Bond list back to STOCK; E-HERO list 0x0209CFE4 drops Flare Neos 0x1A6F
  (user's pick), 0x111F inserted at index 0 (Darkbright/Escuridao entry at index 42 unmoved).
  rom_shadow_mist.nds sha256 e7d1f880e3d26ae13984fe0a5f2ba608536b59f6537df8ae0125662c9e4f8fba,
  verify() PASS, ledger emitted.

- IN-GAME (user, 2026-09-28, build 2 sha256 e7d1f880...): in-game confirmed by user 2026-09-28 --
  item 2 (E-Call / A Hero Lives / Stratos find it), 3 (SS -> Mask Change), 4 (shared lock),
  6 (C2 from field / hand / Deck, itself not offered), 8 (NS no C1), 9 (Cross Porter / Dandylion),
  10 (Flare Neos no longer an E-HERO). Item 7 (Mask Change target) DEFERRED: no DARK Masked HERO yet.
- ⛔ BUG (user, verbatim 2026-09-28): "When sent to the GY for a fusion, Shadow mist misses timing
  (which should not happen as it is an IF effect)"; "It said missed timing"; "It would happen if
  shadow mist is tribute summoned, or used as a synchro material. If it gets destroyed/milled/
  discarded then it does not miss timing. It needs to behave EXACTLY like eclipse Wyvern and
  Dandlyion". Decline-C1-then-C2 works (the miss-timing notice proves C2 was eligible).
  => C2 is being classified as a WHEN (misses timing when the send is not the last thing to happen:
  Fusion material, Tribute Summon, Synchro material). Must be an IF: never misses timing.

- ROOT CAUSE (disassembly, 2026-09-28): C2's +10 calls "You can" 0x021E51E5 -> body 0x021E50DC,
  whose phase 0 calls the miss-timing test 0x021EE0E0(desc) (bl @0x021E510A). Dandylion / Wyvern have
  +10 = 0 (mandatory) and never reach it. 0x021EE0E0's head is a cid tree of hard-coded IF cards ->
  0x021EE27E `movs r0,#0` (never miss); 0x111F falls to the event-code log walk and misses when the
  send is not the last thing to happen (material / Tribute).
  0x111F's tree node: 0x021EE10C `subs r2,#0x13` (r2 = 0x1E2E -> 0x1E1B Sinister Sprocket, REAL)
  `; cmp r3,r2 ; beq 0x021EE176 (never) ; b 0x021EE296`. No inbound to 0x021EE10E..12.
- FIX (build 3, PART J): node's first 4 B -> BL ov3 dead block A 0x021B58D0 (replay Sprocket test,
  else b B) + B 0x021B5AAA (r3 == 0x89<<5 - 1 = 0x111F); Z back to the caller's beq. Both blocks
  have exactly one inbound each (their phantom arms 0x021B4F50 / 0x021B50FE).
  EXECUTION PROOF: scratch/sm_misstiming_exec.py runs 0x021EE0E0 stock vs patched for cids
  0..0x26FF (event 0x1E, word low bits 5, empty log): changed == [(0x111F, 1 -> 0)] only; Sprocket 0/0.
  Build 3: rom_shadow_mist.nds sha256 6b7f38bfc9e132e48278049be75c861f5c44fdee94ec327da75288a2c3e17b75,
  verify() PASS. Covers BOTH clauses (C1 SS trigger also can no longer miss timing) -- both are "If".
  C2 stays OPTIONAL (prompt kept); only the miss-timing test is bypassed. AWAITING IN-GAME TEST.

- SHIPPED 2026-09-28: steps.STEPS step 77/80 + _verify_all_patches.SHIPPED. EE fast build 80/80,
  rom_all_patches.nds sha256 ef97d96d7fbfa10ac9588b28b15920c4a8303ed8f6b4ea2df67baa3da01a7777
  (previous combined ROM kept as rom_all_patches.pre_shadow_mist.nds). Sweep: 65 passed, 1 failed --
  patch_ninishi, PRE-EXISTING: identical 5 FAILs on the pre-Shadow-Mist ROM; its sites
  0x021B9634/0x021B9F9C/0x02261E3E/0x0226515C/0x02261E68 now BL Scrap Raptor's CAVE_SR_NS* chain stubs
  (by design), so ninishi's verify() asserts stale targets. patch_shadow_mist PASS.

## Pre-build risk checklist (status)
1. per-cid gates on 0x111F: PROVEN none (donor_scan CLEAN).
2. zones: C1 handler 0x0223D075 = Remus/Fusion Sage named Deck search (in-game confirmed on Remus);
   C2 handler 0x0223CAF5 = Deck (Stratos native, Hanzo/Snoww confirmed). ASSUMED-by-precedent, not
   re-disassembled this session.
3. text: card_text re-emit, check_rom_text PASS all 8 langs. PROVEN.
4. HOPT stamp: +10 CAVE_SM_SLOT4 after "Yes" (activation). Jet Synchron precedent (cls2 query in +0C,
   no desc[+7] guard) confirmed in-game 2026-09-02/03.
UNPROVEN until in-game: row hook sees the cls2 acting descriptor during C2's +0C probe and resolution
(Lightpulsar C3 cls2 precedent); bit 0x20 excludes Shadow Mist on a set-code (not named) row.

## Ruled Out
- summon_trigger_hook (0x02265900) for C1: only proper Synchro/Fusion/Ritual summons (per precedent
  survey; UNVERIFIED this session beyond the module comments).

## Open Questions
- Does bit 0x20 ("except this card") exclude Shadow Mist on a SET-CODE row? (Hanzo proves it on 0x0223CAF5.)
- Hand discard: Eclipse Wyvern's gate proof covered a discard; Snoww showed the EFFECT-discard arm is
  kind-gated -- our accept is unconditional, so cost/UI discards should also trigger (printed-correct).

## Next Experiment
- User in-game run of the 10-item oracle in _build_shadow_mist.py on rom_shadow_mist.nds (sha256 d5c8fc98...).
- If C2 fires but offers nothing / wrong cards: savestate at the picker -> check row hook chose rel 1.
- If C2 never fires from hand/Deck but fires from field: the gate node (GDB bp 0x021D13CC, r5 = cid).
- KB: setcode.hero_composite_lists + dispatch.sent_to_gy_node_0x111f added VERIFIED; card.shadow_mist UNVERIFIED.
