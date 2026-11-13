# Magician's Rod — findings (live)

⚠️ 2026-10-14: Rod's code-7 phantom **0x19D3 was REASSIGNED to Neo Space Connector** by user decision (Rod C2 parked;
the NS list 0x0228F7AC has no other free phantom). Rod's build no longer applies as-is: before rebuilding, give Rod a
new NS-trigger route -- e.g. a shared hook at the code-7 verdict 0x022657A6 (KB summon.c7_verdict_site, a twin of
c79_trigger_hook) -- and drop its `_list_insert` of 0x19D3. See notes/neo-space-connector-findings.md.

Status: **AWAITING IN-GAME TEST** (nothing built yet). Plan: ~\.claude\plans\magicians-rod-soft-dongarra.md

Printed text (scratch/ygoprodeck_cache.json id 7084129, Lv3 DARK Spellcaster 1600/100):
- C1 When NS'd: you can add 1 S/T from Deck that specifically lists "Dark Magician".
- C2 Opp's turn, if you activate a S/T Card or effect while this is in your GY (not Damage Step): you can Tribute 1 Spellcaster; add this card to hand.
- C3 each effect HOPT by name.

## Confirmed (this session, 2026-10-13)
- 3DS build does NOT ship Magician's Rod (`CARD_Name_E.bin` has no UTF-16LE match) -> no Konami reference.
- Donor chosen by user constraint "<1500 ATK": Aqua Madoor 0x107B (Normal Lv4 WATER Spellcaster 1200/2000), reported clean by `python -m otn_enhanced.tools.donor_scan --free` (zero aligned u16/u32 in ov3+arm9).
- In-ROM S/Ts whose printed text names "Dark Magician" (cache desc x ROM name match, explore agent): 0x12DE Dark Magic Curtain, 0x142E Thousand Knives, 0x1467 Magic Formula, 0x1631 Miracle Restoring, 0x167E Sage's Stone, 0x1713 Dedication through Light and Darkness, 0x17A9 Dark Magic Attack.

- **C2-Q3 ANSWERED (static): `[0x0229C294+0x78]` bit0 IS the engine's Damage-Step gate.**
  Set by duel command opcode 0x1B handler 0x021BC160 (`orrs #1` @0x021BC17C), cleared by
  opcodes 0x15/0x1C (0x021BC10A, 0x021BC1CE) — opcode->arm mapped by scratchpad cmd_table.py
  over dispatcher 0x021C3C3C. Offer gate 0x021ECC6C @0x021ECD24: when bit0 set, the effect is
  offered only if 0x021A897C(cid, desc[+4]) != 0, and 0x021A897C passes only (a) 0x0202ABE8==1,
  (b) list 0x0226D8B0 x0x30 = negators (Null and Void, Stardust Dragon, Herald of ... Light),
  (c) list 0x0226DB0C x0x57 = ATK/DEF modifiers (Rush Recklessly, Shrink, Limiter Removal,
  Metalmorph...). That membership is exactly the Damage-Step-legal set => bit0 = Damage Step.
  CONSEQUENCE: "except during the Damage Step" is FREE for C2 as long as the donor cid is NOT
  added to either list.
- **C2-Q2 ANSWERED (static + prior measurement):** GY check 0x0224C590 passes
  r1 = &0x0229A7FC[[0x0229A9FC+0x44]-1] (0x0224C5BC..0x0224C5D4), 0 when +0x44 == 0, into
  0x021EC740. The identical expression in 0x0224B8B0 was MEASURED to be the chain top
  (maiden-with-eyes-of-blue-findings.md:1523, ml3 savestate, top = Book of Moon).
- **C2-Q1 ANSWERED (prior in-game evidence):** OTN DOES offer responders to the activating
  player's own activation, but only if the player FORCES the response window
  (maiden-with-eyes-of-blue-findings.md "RESOLVED (2026-08-20)", user quote: "I can activate
  maiden in response to my own card, but I wasn't forcing the window."). In-game test steps
  must tell the user to force the window.
- Offer gate 0x021ECC6C with a pending link (r1 != 0): needs speed(mine) >= speed(link) AND
  speed(mine) >= 2; skips the own-turn/MP check 0x021ECC28 (disasm this session). With NO chain
  (r1 == 0) speed >= 2 passes outright => C2's +0C condition MUST return 0 when act == NULL.
- **Native GY Quick-Effect chassis exists:** GY-action registry 0x0228DDF8 rows 20 Necro Gardna
  0x1C0A, 25 Shield Warrior 0x1E17, 45 Damage Eater 0x22E7 (family chk 0x0224C591 / post
  0x0224C6C1), and all three are in the ARM9 speed-2 list 0x0209C118 (stock image, this session).
  Speed getter 0x021A87BC = per-cid switch, default leaf 0x021A894C -> 0x0202345C (list).
  Free GY-family phantom rows (stock): 15 (0x0EB2), 48 (0x0E64); 47 taken by lightpulsar — check
  the ledger, other patches may have spent 15/48.

- Native GY quick-effect cls2 records (cls2 base 0x02275C04 x0x2B9, stride 0x18, this session):
  Necro Gardna [276] {0x0221F9E1, 0, 0x021F0BDD, 0x021E5709, 0}; Shield Warrior [361]
  {0x022134A1, 0, 0x021FE559, 0x021E5709, 0}; Damage Eater [583] {0x0221FCF1, 0, 0x02202F55,
  0x021E5709, 0}. Damage Eater cond 0x02202F54 = TEMPLATE for C2's +0C: checks
  [0x0229DD14+0x34] == 1 - desc[+2] (OPPONENT'S TURN), then passes (desc, r1=act) on to
  0x021F0A10 => class-2 +0C DOES receive act in r1.
- Self GY->hand resolver 0x02208211 (disasm this session): locate desc[+0xC] via 0x021A220C,
  require still in zone desc[+3] (0x0E GY / 0x0F banished) and same instance (+0xE vs
  0x0229C33C), then 0x021C7038 / 0x021C7068 -> 0x021C6EE0 (to hand, or Extra Deck for
  Extra monsters). Single-shot, returns 0. => C2 resolver is pure data.
- GY-action row: NO phantom/sibling rows left (ledger: grapha 0x0EB2, lightpulsar 0x0E3E,
  jet_synchron 0x0E64, remus 0x1449, misc 0x144C, oja 0x1452; jet_warrior spent real row 33).
  Only route without breaking a real card = extend Revolution Synchron's virtual-row hooks
  (CAVE_REVSYN_VROW 0x0239FBD0 + hooks 0x0224C88E/0x0224C9A0/0x0224CD34/0x0224CD60, ov5).

### Donor pre-build checklist — Aqua Madoor 0x107B (this session)
1. Per-cid gates: **PROVEN none.** donor_scan 0x107B: "CLEAN - no data structure names this cid";
   its 4 non-key u16 hits (ov3 0x02145580, 0x02193D54, arm9 0x020214A6, 0x020214D0) are all the
   instruction `asrs r3,r7,#1` (=0x107B), disassembled. Derived-constant scan
   (scratchpad derived_cid_scan.py: literal/movs +- imm, 16-insn window, ov3+arm9) found 0 hits
   for 0x107B; positive control 0x14D7 found at 0x021ECCEC (`subs r2,#0x75` from 0x154C) and
   0x02197010.
2. Zones: C1 Deck via criteria handler 0x0223CAF5 (KB dispatch.criteria_aux_is_has_set_code_index);
   C2 resolver 0x02208211 reads self in GY/banished (disasm above); Tribute from field via
   0x021E7C89 (KB, Jet Warrior C2 shipped).
3. Blob lengths: irrelevant — cid goes into card_text.CARD_TEXT (index-order re-emit, MAX_NAME 110 /
   MAX_DESC 1196). Stock slots name>=11 desc>=55.
4. OPT stamps: C1 in slot4 on Yes (Psi stub shape); C2 in the cost wrapper on Yes (Assault/Jet
   Warrior shape) — stamping in the resolver loses to the chain (KB, Maiden).
- User decisions 2026-10-13: whole card; hard-coded cid list; donor <1500 ATK -> Aqua Madoor;
  C2 RE first; C2 GY row = 2nd VIRTUAL row extending Revolution Synchron's hooks (ov5, normal
  duel only); speed 2 (can't chain Counter Traps, matches real rules).

- **Build-time facts (2026-10-13):** phantoms (scratchpad phantom_find.py on rom_all_patches.nds: 1 row, no
  card_prop, unclaimed): cls1 0x130F (only ov3 mention = its row), cls2 0x1B19, criteria 0x167D, c7 0x19D3.
  cave3 free gaps total only 0x452 B; Rod's list takes run 0x0221782C..0x0221783C (zero in the chain ROM).
- **GY two-row stubs proven by EXECUTION** (scratch/gyvrow_equiv.py, 173 inputs): only H5 r6=61, H6 cid
  0x107B (r4>=0x3C) and H7 cid 0x107B differ; row 60/61 fetches return the right rows. Latent shipped
  behaviour preserved: Revolution's H6 returns r0 = 0x1649 (nonzero) for any unmatched cid past row 60.
- thumb_asm has no `tst`, `bhs`, `bcc` (signed conds only) -> used `ands` / `bge` / `blt` (r4/r6 small, >= 0).

## Ruled Out
- (none yet)

## Open Questions
- (Q1-Q3 answered, see Confirmed.)
- Does class-2 slot +0C receive (mine, act) like cls3 slot3? Check Necro Gardna's cls2 +0C.
- Which speed-2 mechanism to use: the speed list is full in the chain; Overtex/Miscellaneousaurus hook the default leaf 0x021A894C (ov5). Want an ov3 home.
- Donor gate checklist for 0x107B (base±imm cid switches, set-code memberships) — pending.

## Architecture (proposed 2026-10-13, awaiting user go)
C1 (Psi-Reflector C1 minus the code-9 insert):
- set code 0x28 (stock list 0x0209C582 = 2 phantoms {0x1433,0x1434}, aux unused): thunk 0x02023AF0,
  count imm @0x02023AF4 -> movs r2,#7, list literal @0x02023AF8 -> cave3 0x0221782C (7 x u16, free gap 0x10).
  No ARM9 set code has a >=7 all-phantom list (scratchpad setcode_scan.py: 0x28 n=2, 0x2A n=4 hanzo,
  0x6E n=4 psi, 0x4B/0x5C aux used).
- c7 NS list 0x0228F7AC over phantom 0x19D3; cls1 Gearframe {0x02207EF5,0,COND,SLOT4,0} over a phantom;
  criteria {0x107B, 0x28, 0x0223CAF5, 0x0000000C}; timing_class_hook ARM_JW (desc[+5]==1 only).
- card_prop Effect Monster / DARK / Spellcaster / Lv3 / 1600 / 100; text via card_text.CARD_TEXT.
C2 (Jet Warrior C2 chassis + Damage Eater cond shape):
- cls2 {0x02208211 self GY->hand, FILT, COND, COST, 0} over a phantom.
  FILT = zone pred 0x021D6E41 mask 0x8011 && 0x021B8D90(side,zone) & (1<<18) (Spellcaster).
  COND = kind-2 turn-log clear; act != 0; act[+3] <= 0xA; ctrl(act) == ctrl(me); act cid Spell 0x02022FC9
  or Trap 0x02022FDD; [0x0229DD14+0x34] != my side; candidates 0x0224AB39(desc,0x0224A8C1) > 0 -> 1.
  COST = Tribute machine 0x021E7C89, stamp kind 2 on 1.
- GY row: shared gy_vrow_hook (lift Revolution's H4-H7 into a cid/row table) + row {0x107B,0x0E,0x0224C591,0x0224C6C1}.
- speed 2: front-chain stub at leaf 0x021A894C (0x107B && desc[+5]==2 -> 2, else tail CAVE_OQ_SPEED);
  Overtex verify learns the front chain (Misc's _speed_chained precedent).
- Damage Step: free (cid not in 0x0226D8B0 / 0x0226DB0C).
Test ROM: layer on rom_all_patches.nds (needs Revolution/Overtex/Misc hooks present) after a staleness check.

## Build (2026-10-13)
- `_build_magicians_rod.py` -> data/over_the_nexus/working/rom_magicians_rod.nds, layered on
  rom_all_patches.nds (fresh: built 15:38, no patch module newer). sha256
  f5aceea3c508fbefa6ea13dcc75efa4db3816cfc3eb6df13da99591ed342a776. verify(): 37/37 PASS (static only).
- Text == ygoprodeck cache exactly; card_prop decodes DARK / Spellcaster / Lv3 / 1600 / 100 / type 3.
- KB: battle.damage_step_offer_flag, dispatch.self_gy_to_hand_resolver_0x02208211,
  dispatch.gy_quick_effect_native_chassis (VERIFIED), card.magicians_rod (UNVERIFIED). author_facts --check
  630 PASS / 0 FAIL.
- EXPECTED on this test ROM: patch_revolution_synchron.verify and patch_overtex_qoatlus.verify FAIL (their
  H4-H7 stubs / speed-leaf bytes are deliberately replaced). No sweep run (card still in debug).

## Compact (all-ov3, puzzle) build (2026-10-13, user request)
- `_build_magicians_rod.py --compact`: step 0 re-run fresh from rom.nds into a stage file, then
  patch_magicians_rod.main(ov3=True) -> rom_magicians_rod_compact.nds, sha256
  3b334ac20333e2e3da0c4ef791c4ca40d356a9c6cbbd6503e0340ccc0a2feed2. verify(ov3=True) 33/33 PASS +
  patch_ov3_compact.verify OK. No other card patches on it.
- Every stub in cave3 (CAVE3_ROD_*, ~500 B -- nearly all remaining cave3 gap space): Rod-only timing stub
  at site 0x0224AF96, 1-row virtual GY table + hooks at Revolution's 4 sites, speed stub over the native
  leaf (falls back to `adds r0,r2,#0 ; bx 0x0202345D`, returns to 0x021A8951).
- scratch/gyvrow_ov3_stock_equiv.py (108 inputs): 1-row hooks == stock for every cid but 0x107B.
- Native fact: GY post-by-cid scanner 0x0224CD08 exits a miss with r0 = row 59's cid (last `ldr r0,[r1,r0]`),
  so Revolution's r0 = cid quirk at H6 is no worse than native -- the caller cannot depend on r0 there.
- Refactor kept the ov5 hosting byte-identical (all 12 blobs == the built rom_magicians_rod.nds).

## Ship-time TODO (only after the user approves shipping)
1. Lift the two-row GY stubs + CAVE_GYVROW into a shared module (gy_vrow_hook.py, VROWS register);
   patch_revolution_synchron imports it; re-run scratch/gyvrow_equiv.py.
2. Move the 0x107B ARM_JW arm into timing_class_hook.ARMS (drop timing_arms()).
3. Overtex/Misc verify learn the Rod speed front stub (Misc `_speed_chained` precedent).
4. steps.STEPS + _verify_all_patches.SHIPPED; donor-pool note: Aqua Madoor -> "Used as donors".

## In-game report (2026-10-13) -- PARKED by user
- User, verbatim: "Magicians rod GY effect is not firing." Then: "dont worry about it, lets bank this and
  do something else." Reading NOT confirmed. Unknown which ROM (compact / chain), what S/T was activated,
  whether the response window was forced, whether a Spellcaster was on the field, whether C1 worked.
- C2 = FAILED IN-GAME (unconfirmed reading). Card is PARKED, not shipped.
- **C1 (+ its once-per-turn) in-game confirmed by user 2026-10-13**: "C1 worked perfectly." (ROM not stated;
  the compact build was the one handed over for testing.) Do not touch C1's pieces when fixing C2.

## Next Experiment (when resumed)
1. Get the answers above (ROM, S/T type, window forced?, Spellcaster present, C1 result).
2. Ask for a savestate AT the expected prompt; run the C2 path offline with scratch/thumbemu:
   GY enumerator 0x0224C820 -> does it reach virtual row 60/61 and call check 0x0224C591 for 0x107B?
   -> 0x021EC740 -> offer gate 0x021ECC6C (speed: does 0x021A87BC return 2 for our desc?) -> cls2 +0C
   C2COND with r1 = chain top (which test returns 0: turn player, controller, Spell/Trap, OPT, candidates?).
3. Suspects to rule out first, cheapest first: (a) window not forced (Maiden lesson); (b) the GY enumerator
   only runs for the turn player / own-turn ignition menu, not in the opponent's-turn response window --
   Necro Gardna is the native precedent, so check how ITS offer is reached (it may not use 0x0224C820);
   (c) desc[+5] at the speed leaf is not 2 for the GY descriptor; (d) C2COND controller test (act[+2]^act[+6]
   vs desc[+2]).
