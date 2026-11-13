# Neo Space Connector — findings

Status: PLANNING / step 1 (donor + filter proofs). Nothing built. AWAITING IN-GAME TEST for every clause.
Plan: `~\.claude\plans\neo-space-connector-reactive-moth.md`.

Printed text (scratch/ygoprodeck_cache.json, id 85840608; LIGHT Warrior Lv4 800/1800):
> When this card is Normal Summoned: You can Special Summon 1 "Neo-Spacian" monster or 1 "Elemental HERO Neos"
> from your hand or Deck in Defense Position. You can Tribute this card, then target 1 "Neo-Spacian" monster or
> 1 "Elemental HERO Neos" in your GY; Special Summon it in Defense Position. You can only use each effect of
> "Neo Space Connector" once per turn.

- C1: NS trigger, SS listed monster from hand/Deck, DEF, OPT (kind 1).
- C2: ignition, Tribute self (cost), target listed monster in own GY, SS DEF, OPT (kind 2).
- User decisions 2026-10-14: whole card in scope (built/tested clause by clause); filter = explicit cid list;
  donor rule ATK < 1500 -> Kanan the Swordmistress 0x1106 chosen.

## Confirmed
- 3DS does NOT ship the card: CARD_Name_E.bin has 0 hits for UTF-16 "Connector" (research pass 2026-10-14, scratchpad q3.py).
- Set code 0x17 = Neo-Spacian: has_set_code ptr table 0x0209D0D8 idx 0x17 -> thunk 0x02023944, list 0x0209C702,
  8 entries 0x1A70-0x1A75, 0x1C06, 0x1D11, no phantoms (research pass walk of reference arm9.bin, 2026-10-14).
  E-HERO Neos = 0x19FD (scratch/cid_to_name.json). -- to be re-dumped in-session before relying on it.
- donor_scan --free lists Kanan 0x1106 (Lv4 EARTH Warrior 1400/1400, slots 11 B / 54 B) as clean
  (zero aligned u16/u32 occurrences in ov3+arm9). Run 2026-10-14.

- **Donor 0x1106 per-cid gates: none found (PROVEN for literal and base±imm forms; jump-table ranges ASSUMED).**
  - `donor_scan 0x1106`: "VERDICT: CLEAN - no data structure names this cid"; 12 non-key u16 hits are instruction encodings / pointer halves.
  - base±imm scan (scratchpad `baseimm_scan2.py`: every `ldr rX,=L` with |0x1106-L|<=0xFF, then any adds/subs imm == 0x1106-L
    within +-0x200 halfwords). Validated on the two known positives: it finds Doitsu 0x021D811A (0x1917-0xC) and BP-gate 0x0224CDB4 (0x0EB7+6).
    The 0x1106 hits were all reviewed in `tdis.py` disassembly; every one is a false positive:
    - arm9 0x0202B1A2: r2 = 0xFA6 → 0xF3D. ov3 0x021A9526: r3 = 0x209C → 0x2027.
    - ov3 0x021B4A4A: r5 = return value of 0x021ACCD4 (dynamic). ov3 0x022606AA: r5 = ldrh (dynamic).
    - ov3 0x021D7516 / 0x021D751C / 0x021D7896: inside equip-target lock 0x021D7348, but that switch is on r2 = ldrh [desc]
      (0x021D73A4), i.e. the EQUIP CARD's cid, not the candidate (r5, 0x021A3320). Its jump table at 0x021D7418 covers 0x10D4-0x10EE only.
    - +4 / -2 hits (0x0219FBD0, 0x021A00E0, 0x021A4D18, 0x021A5334, 0x021D3908, 0x021D3A72, arm9 0x020585B0): literal-pool
      data or unrelated registers (e.g. 0x021D3A72 = `adds r0,r4,#4` return-value arithmetic).
  - Residual: a compiler jump table keyed on a candidate cid whose range spans 0x1106 is not covered by the scanner.

- **Filter re-dumped this session** (reference arm9.bin): u16[0x0209C702..+8] = 1A70 1A71 1A72 1A73 1A74 1A75 1C06 1D11
  (next words 0x1B33.. belong to the following list); has_set_code[0x17] = 0x02023945. Names via scratch/cid_to_name.json;
  0x19FD = "Elemental Hero Neos".
- **C1 resolver design is proven by precedent, not new RE:** native Tour Guide resolver 0x02206F41 (tdis 0x02206F40..0x02207150)
  = the deck-SS machine: 0x80 candidates 0x02243FA8(side, cid, 0x02234E78(desc)) -> 0x7F picker 0x0219C430(side,6,cid,param)
  -> commit via 0x02269314, which is `str r3,[sp] ; movs r3,#2 ; bl 0x0226925C` (position 2 hardcoded, 0x02269318).
  0x0226925C(side, &loc, faceUp, position, [sp] cid<<16): 1 = forced DEF (KB counter.deck_ss_position_encoding).
  The same commit serves hand+Deck sources (Tour Guide in-game confirmed 2026-09-10). Oviraptor's c2_res_stub phases
  0x90->0x7F->0x7E->0x7C(POS 1)->0x7B/0x78 re-implement this machine (in-game confirmed 2026-09-25).
- **C2 resolver:** native 0x02207191 default arm (unlisted cid) goes straight to 0x022072DA:
  `0x02204730(desc, r4=1, r5=2) ; movs r0,#0 ; pop`. The 0x021AC9DC(0x175E Sanctuary in the Sky) check at 0x022072CC
  is only on per-cid arms. So own RES = 0x02204731(desc, 1, 1) then return 0 (Snoww's in-game-confirmed form, patch_snoww.py:514).
- Slot functions (KB greps this session):
  - 0x021F0821 (cls1 +0C) = cid-blind "candidate exists" via 0x02243FE0.
  - 0x021F03B5 (cls3 +0C) = cid-blind, reads desc only (free zone 0x021B9EC0 + candidate count).
  - 0x021E50CD = Tribute-self cost, side+slot only (send-self 0x021CF658).
  - 0x02235605 = off-field list-zone target declaration; the pick count is desc[+0x10].
  - AVOID 0x021F0419 and 0x021F0BDD: both are per-cid registry lookups.
- Predicate convention (Tour Guide filter + Assault Synchron pred): the builders blx the predicate with caller [sp] =
  card-word pointer; cid = word & 0x3FFF. Hand 0x0223C16C (zone 2), Deck 0x0223BC3C (zone 0xA), GY 0x0223C4E8 (flags 8).

- **BLOCKER 1, resolved by design:** the code-7 NS list 0x0228F7AC has **0 free phantoms**.
  - scratchpad `phantom_scan.py`: unclaimed, no card_prop, present once in both stock rom.nds and chained rom_all_patches.nds.
  - Magician's Rod took the last one, 0x19D3 (allocations.yaml line 2633).
- **Code-7 verdict site 0x022657A6** (tdis 0x02265768..): evaluator 0x02265768, `cmp r6,#7 ; bne` @0x02265798, then
  `ldrh r0,[r4,#0xe] ; ldr r1,=0x0228F7AC (pool 0x022659E8) ; movs r2,#0x67 ; bl 0x02022E14`, then
  **0x022657A6 `cmp r0,#0 ; beq 0x022657AC`**; member 0x022657AA `adds r5,r7,#0` (r7 = 1 since 0x02265772, callee-saved
  across bl 0x02265470); non-member 0x022657AC. r4 = 0x02298A28 (summon record, cid at +0xE).
  - Exact twin of c79 site 0x02265C44 (skip 2) and summon_trigger_hook 0x02265900. summon_trigger_hook.stub() is reusable with skip=2.
  - r0/r1 are dead after the site on every path: 0x022657AC reloads r0; 0x022657B2/B4 reload r0/r1;
    0x0226586E->0x022658AC->0x02265938->0x02265C1C reloads r0/r1 at 0x02265C22/24. r2 is untouched by the stub.
- **BLOCKER 2, resolved by design:** criteria table has only 1 usable free phantom, **0x14D7** (the other "free" entry is 0xFFFE, a sentinel).
  criteria_row_hook is FULL (KB dispatch.criteria_row_hook_full; DEP memory). So: ONE row + a mode-switching handler (DEP precedent):
  acting desc = [0x0229A9FC+0x50]; desc[+0]==0x1106 && desc[+5]==3 -> GY mode (builder 0x0223C4E8, flags 8, word 0x00010002),
  else hand+Deck mode (TG selector clone, word 0x2, aux 0xE).
  - The pointer is scoped around slot invocations (0x0224AE20/0x0224AE3C) and set at resolution (0x02218032), so +14 targeting
    and resolver picks see the right descriptor.
  - It may be STALE at menu-time +0C (Oviraptor findings line 114), so both conds scan zones DIRECTLY and never use the row.
- Zone layout (KB): hand player+0x124 / count +0xC; Deck player+0x304 / count +0x10; GY player+0x55C / count +0x14;
  player = 0x0229AC94 + side*0xB3C.
- 0x021D269C = SHUFFLE_DECK (KB), and it is phase 0x78 of the deck-SS machine and of Oviraptor's resolver. So a Deck pick gets shuffled.
- C2 cond chains Piper's cid-blind generic gate 0x021F06E9 behind a desc[+7] guard (patch_mystic_piper.py:297-311, in-game confirmed 2026-09-08).
- ov5 cave: CAVE_FREE = 0x023A5A90 (working tree, includes the parked Magician's Rod slots); ceiling ~0x023AA120 (recompute).

## Ruled Out
- Set 0x0A ("Neos" list) as the Neos test: it contains the Neos Fusions too. Use cid equality 0x19FD.
- 0x021F0BDD as C2 condition: per-cid registry lookup (KB cards.yaml:164) — unregistered donor never offered.

- Inserting into code-7 list (no phantom left) and adding a 2nd criteria row (no phantom; row hook full).
- 0x021F0419 as C1 +0C (per-cid registry, KB).

## C1 Build 1 (2026-10-14) -- IN-GAME CONFIRMED BY USER 2026-10-14
- User report verbatim: "C1 works in-game, build C2 now" (rom sha256 99833ed2...154df373).
- `_build_neo_space_connector.py` -> data/over_the_nexus/working/rom_neo_space_connector.nds,
  sha256 99833ed24d00ca609c08c83435a454bad0e01f0d60919403d46d7689154df373. verify(): 19/19 PASS (static only).
- Claims: code-7 phantom 0x19D3 (from Rod), cls1 phantom 0x11EA (@88 -> donor @71), criteria phantom 0x14D7 (@163 -> @74).
  CAVE_NSC_PRED 0x023A5A90 (108 B), CRIT 0x023A5B10 (128 B), COND 0x023A5BA0 (124 B), SLOT4 0x023A5C30 (44 B),
  RES 0x023A5C60 (224 B); CAVE_FREE -> 0x023A5D60. tch arm LOCAL (timing_arms()). check_allocations --emit OK.
- Disassembly of every installed stub reviewed (nsc_dis.txt in scratchpad): all POPs go to PC, all blx literals are odd.
- `python -m scratch.nsc_equiv` (EXECUTED via thumbemu), all OK:
  - predicate over 0x4000 cids: hits exactly the 9 listed.
  - criteria: mode switch (no act / cls1 / cls3 / other cid cls3 / cls2) + GY args (0x10002, 8, pred|1, cid, side),
    Deck args (2, 0xA, pred|1, aux 0xE, side), hand args (2, 2, pred|1, aux 0xE, cid).
  - cond: 8 cases. timing: 602208 inputs, only 0x1106 differs and == 0x0FC6; 292 -> 312 B (reserve 0x200).
- NOT proven: the in-game path (prompt appears, picker contents, DEF commit from hand AND Deck). That is the user's test.

## C2 Build 2 (2026-10-14) -- IN-GAME CONFIRMED BY USER 2026-10-14
- User report verbatim: "C2 works in-game, move it to ov5 and ship it" (rom sha256 d3c178b5...e2587cb).
  Whole card is now in-game confirmed. User approved shipping.

## SHIPPED 2026-10-14 (user: "ship it", as-is from ov5)
- steps.STEPS: "Neo Space Connector" right after Nikitama (the rest section, not vanilla+); _verify_all_patches.SHIPPED.
- Timing arm (0x1106, ARM_JW) moved into timing_class_hook.ARMS, appended LAST, so the bytes equal the stub the
  nsc_equiv proof executed.
- patch_bulk_card_pack key renamed "Kanan the Swordmistress" -> "Neo Space Connector" (pack 47 kept).
  Donor moved to used in notes/donor-pool... and scratch/donor_resource.json.
- EE build: 113/113 steps, BUILD_EXIT 0, rom_all_patches.nds 129691784 B,
  sha256 82c3ff60619a4689ae4fe8643e2bdee87afb608dfd1fdf57bc914faa5a321a66. Pre-build copy: rom_all_patches.pre_nsc.nds.
- verify sweep: 94 passed, 0 failed, 0 without verify(); patch_neo_space_connector PASS in the chain.
- The chained ROM itself has not been played in-game; the user's confirmations were on the single-card ROMs.
- Same script/ROM path; sha256 d3c178b57eceb4d83b2baab511e995f4e82e18d2c37563de47a1ef609e2587cb. verify(): 25/25 PASS (static).
- cls3 over phantom 0x14D7 (cls3[89]; same dead card as the criteria row) = {C2RES, 0, C2COND, C2COST, 0x02235605}.
  Build asserts the templates are intact: Necro Linker 0x237A {0x02207191, 0, 0x021F0BDD, 0x021E50CD, 0x02235605} and
  Blazewing 0x1CAD {0x02207191, 0, 0x021F8E89, 0x021E50CD, 0x02235605}.
- Slots: CAVE_NSC_C2COND 0x023A5D60 (112 B), C2COST 0x023A5DE0 (36 B), C2RES 0x023A5E10 (20 B); CAVE_FREE -> 0x023A5E30.
- No new timing arm (cls3 returns before the classifier site). The criteria row's GY mode was already built in Build 1.
- `python -m scratch.nsc_equiv` adds c2 (EXECUTED): 8 cond cases (desc[+7] guard, OPT kind 2, own-GY scan,
  exclusions, opponent-GY decoy, generic gate); cost posts (0x1106, kind 2) and then hands the DESC to the Tribute;
  res calls 0x02204731(desc, 1, 1) and returns 0. All earlier proofs still OK.
- NOT proven: the in-game GY targeting through 0x02235605 -> row E's GY mode (acting desc = our cls3 in the slot call).

## Decisions
- 2026-10-14 USER DECISION: do NOT add a c7 hook; **take Magician's Rod's parked code-7 phantom 0x19D3** (Rod C2 is parked;
  Rod's test build is knowingly broken by this). The one-row mode-switching criteria handler stands. C1 is built and tested first.

## Open Questions
- Free phantoms for cls1 / cls3 (scan): cls1 has 48, e.g. 0x0E5F, 0x0E6D, 0x0E8A; cls3 has 29, e.g. 0x0E51, 0x0E56, 0x0E5E.
  Pick at build time, prove absent from PHANTOM_CLAIMS, and register.

## Next Experiment
- None needed before the build: every hook site is a twin of an in-game-confirmed site. Build C1 after approval.
