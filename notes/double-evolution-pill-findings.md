# Double Evolution Pill — findings

Text (user-supplied 2026-09-28; NOT in scratch/ygoprodeck_cache.json, NOT in the 3DS build):

> Banish 1 Dinosaur monster and 1 non-Dinosaur monster from your hand and/or GY;
> Special Summon 1 Level 7 or higher Dinosaur monster from your hand or Deck,
> ignoring its Summoning conditions. You can only activate 1 "Double Evolution
> Pill" per turn. — Normal Spell

Clauses: C1 cost (banish Dino + non-Dino, hand and/or GY) · C2 SS Lv7+ Dino from
hand/Deck ignoring conditions · C3 hard OPT · C4 Normal Spell.
Scope: user chose **whole card** this session. Donor: user chose **a scrap
Normal Spell** ranked by cid hits (not Ultra Evolution Pill / Fossil Dig).
Plan: ~\.claude\plans\double-evolution-pill-memoized-sedgewick.md
Status: WHOLE CARD in-game confirmed by user 2026-09-28 (all 11 oracle items). SHIPPED to steps.STEPS 2026-09-28 (EE 83/83, sha256 9b82f8a1...118ca7e = the confirmed test ROM, byte-identical; verify sweep 68 passed, 1 failed = patch_ninishi, PRE-EXISTING: same 5 hook FAILs on the pre-ship and pre-Norden chains). Edge case (only Lv7+ Dinosaur banished as the cost -> nothing to summon): user ALLOWS it 2026-09-28.

## Confirmed
- 2026-09-28 `verify_knowledge`: 578 facts, 516 PASS / 0 FAIL / 62 UNVER. The
  facts the plan depends on are all PASS VERIFIED:
  dispatch.summon_restriction_classifier, counter.deck_ss_phase_arms,
  dispatch.criteria_zone_is_the_handler, dispatch.criteria_hand_vs_deck_handlers,
  dispatch.turnlog_once_per_turn_pair, dispatch.two_row_criteria_is_list_b_plus_l2,
  dispatch.criteria_word_level_field, dispatch.banish_count_cost_machine,
  dispatch.deck_handlers_ca99_cad9_same_shape, event.gy_to_banished_mover.
- 3DS name table (CARD_Name_E / CARD_Prop, read 2026-09-28): no "Double
  Evolution Pill". Relatives that are present, with their cids: Ultra Evolution Pill 0x1715,
  Big Evolution Pill 0x1AA3, Evolution Burst 0x1D84, Fossil Dig 0x20A0,
  Miracle Jurassic Egg 0x1A8D.
- Criteria rows (Explore dump of ygo_tools/reference_files/nds_overlay_3.bin,
  words identical to 3DS): Ultra Evolution Pill crit[270] {0x0223CA51,
  0x48000002}; Fossil Dig crit[965] {0x0223CAD9 Deck, 0x48980002 = Dino Lv<=6}.
  So race Dinosaur = top-5-bits 9 (0x48 byte).
- **"Ignoring its Summoning conditions" needs no hook at the classifier gate.**
  Proof: scratchpad dino_class.py, 2026-09-28. It read the four class lists of
  0x020231C8 (0x0209BE2C/0x37, 0x0209BE9C/0x39, 0x0209BA12/3, 0x0209BC14/0x1D)
  through the KB Helpers and checked all 51 race=Dinosaur cids from ROM
  card_prop. Result: **0 of 51 are in any class.**
  - The 8 main-deck Lv7+ Dinosaurs are 0x1701 (L7), 0x1A79 (L8), 0x1AA0 (L8),
    0x1D87 (L8), 0x1E7A (L8), 0x1FA3 (L7), 0x2031 (L7) and 0x20CC (L9).
  - Extra-deck Dinosaurs (0x1C86 L7 Fusion, 0x1FB6 L7 Synchro, 0x2181 L10
    Synchro) can never be in the hand or Deck.
  - Caveat: this covers only the classifier. The separate 0x021B9E28 test on
    the 0x021BA69C path has not been examined.
- **Donor ranking** (scratchpad rank_spells.py + donor_hits.py, 2026-09-28).
  Method: count 2-aligned raw u16 hits across the arm9, ov3 and stock ov5 images;
  Normal Spells only; excluded the 83 DONOR* cids in finished_patches.
  - Speed Spells (0x0D4B..0x0DFD) have 0–1 hits in these images. Their logic
    presumably lives in another overlay, so they are **excluded** (possible
    hidden gates, and they are Turbo cards).
  - Non-Speed Normal Spells with exactly 1 hit, and in every case that hit is
    the card's own cls0 record (cls0 base 0x0227E64C, stride 24):

    | cid | card | record | fields |
    |---|---|---|---|
    | 0x1319 | Share the Pain | cls0[199] | {0x0220DFED, 0, 0x021F3C0D, 0x021E7BE5, 0} |
    | 0x170F | Gryphon's Feather Duster | cls0[496] | {0x022137F5, 0x021DF06D, 0, 0, 0} |
    | 0x17A9 | Dark Magic Attack | cls0[538] | {0x022048FD, 0x021DA081, 0x021F4B25, 0, 0} |
    | 0x1923 | Des Croaking | cls0[632] | {0x022048FD, 0x021DED69, 0x021F9795, 0, 0} |
    | 0x1DCD | Short Circuit | cls0[939] | {0x022048FD, 0x021DED69, 0x021FE285, 0, 0} |

  - No criteria rows. None of these cids appears anywhere in ygo_tools/tools
    (grep 2026-09-28).
- Blob length is not a donor constraint: card_text.CARD_TEXT uses the
  index-order re-emit (card_text.py:98), which has no slot limit.

- **User decision 2026-09-28: donor = Share the Pain 0x1319** (cls0[199]
  stock {0x1319, 0x0220DFED, 0, 0x021F3C0D, 0x021E7BE5, 0}; record rewritten
  in place, like Breath of Light for Soul Charge).

- **C2 template = Emergency Teleport 0x1E43** (proof: scratchpad ofo.py + et_rider.py, 2026-09-28,
  read from the committed ov3 oracle).
  - Record shapes:
    - Emergency Teleport: cls0[966] {0x1E43, 0x02206F41, 0, 0x021F0419, 0, 0} + criteria
      row 736 {0xFFFF, 0x02240A95, 0xA88C0002}.
    - One for One 0x2005: cls0[1046] {0x02206F41, 0, 0x021F0BDD, 0x021E7245, 0} + rows 887
      {0x02241519, 0x2} / 888 {0x02240A95, 0x40002}.
    - None of the three is in list A.
  - **Handler 0x02240A94 = hand + Deck builder**, disassembled in full: `push {r1-r5,lr}; r5=row`,
    then `[sp]=row[+8] (word), [sp+4]=2, bl 0x0223C16C` (HAND builder), then
    `[sp]=row[+8], [sp+4]=0xA, bl 0x0223BC3C` (DECK builder), then `pop`. The filter is
    **the row word**, so a Level 7+ Dinosaur needs only a word change.
  - **Resolver 0x02206F40, per-cid switch (0x02206F4E..0x02206FD0):**
    - Sets r6/r7 flags only for {0x1C22, 0x1C71(r7), 0x1CAC, 0x1D03, 0x1D85, 0x1DD6(r7),
      0x1E77, 0x1EC6, 0x1F82, 0x2011, 0x226A}.
    - **0x1319 takes the default arm** (0x1319 < 0x1C22 -> `beq` fails -> `b 0x02206FD2`),
      and so does 0x1E43.
    - The second switch @0x0220700E tests {0x0E2B, 0x17F5, 0x1BF6}; 0x1319 falls to
      0x02207046 (the generic cond + param path).
  - **Emergency Teleport's End-Phase banish is NOT in the resolver.** Its ov3 u16 hits are
    0x021E906E (code), 0x02273644 (crit row), 0x022840DC (cls0), 0x0228EA64 (?), and 0x0228F734,
    which lies inside the End-Phase list 0x0228F708 (the Miscellaneousaurus "destroy in the End
    Phase" data path). So the donor gets no rider.
  - **Cond 0x021F0418:** 0x021F0384(desc) -> param 0x02234E78(desc) -> 0x02243FE0(side, cid,
    param) != 0 -> 1. It is generic, with no per-cid code.
  - Criteria word, Level 7+ Dinosaur = **0x485C0002**: race 9<<27 = 0x48000000, level 7<<18 =
    0x1C0000, >= bit 22 = 0x400000, monster bit 1. Checked against Emergency Teleport
    0xA88C0002 = Psychic(21), level 3, <= bit 23.
  - Cost-handler precedent: 0x02241518 = `0x0223BFD4(side, cid, ?, r3 = pool FILTER FN,
    [sp] = 0, [sp+4] = word, [sp+8] = 0x11)` -- a generic builder that takes a filter callback
    and a zone argument. It is a candidate for the "non-Dinosaur from hand/GY" row. UNVERIFIED:
    the meaning of 0x11.

- **Criteria handler survey** (scratchpad handlers.py -> handlers.txt, 2026-09-28): every distinct
  handler in the 0x022713C4 registry (349), with the BL targets in its first 0x50 bytes.
  - **Zone builders:** HAND 0x0223C16C, DECK 0x0223BC3C, **GY 0x0223C4E8** (0x0223CA11 calls
    only it). 0x0223CA51 / 0x0223CB19 go through 0x0223BFD4 instead.
  - **0x0223BFD4 is a single-card evaluator**, not a zone builder. Proof: disasm 0x0223BFD4.. —
    it indexes player (0x0229AC94 + side*0xB3C) + 0x124 + r2*4 and tests ONE card word.
  - **Native HAND+GY handlers** (BL 0x0223C16C + 0x0223C4E8 only): 0x0223FE65 (0x1C22/0x1CAC),
    0x0224000D (0x1C66), 0x02240729 (0x1D85), 0x02240CC9 (0x1E77), 0x02240E99 (0x1EC6/0x2011),
    0x02240F9D (0x1F55), 0x0224115D (0x1F82/0x226A), 0x0224355D (0x2447).
    - Their cids are the same set as the 0x02206F40 resolver's special arms, i.e. these are the
      "SS from hand or GY" cards.
- **Param provider 0x02234E78** (disasm 2026-09-28): a chain of sorted-list searches (0x02022E14)
  over lists 0x022710E2/0x11, 0x02271104/0x1C, 0x022710B2/0xC, 0x0227109C/0xB, 0x022710CA/...,
  each returning a desc field. Not yet shown: that 0x1319 misses every list.

- **0x1319 gets param 0 from 0x02234E78** (manual trace of the compare tree, disasm 2026-09-28):
  0x02234EDE: <0x1F59 -> <0x19B6 -> <0x15FD -> >0x0E2E (0x02234F3A) -> >0x0E6B (0x02234F56) ->
  !=0x1536 -> 0x022355F0 `movs r0,#0; pop`.
  - STILL UNCHECKED: the five head sorted lists 0x022710E2/0x11, 0x02271104/0x1C, 0x022710B2/0xC,
    0x0227109C/0xB, 0x022710CA/0xC. If 0x1319 is in one, a desc field is returned instead.
- **0x02240E98 (native HAND+GY handler)**, full disasm:
  - Setup: r6 = filter 0x0223C825; [sp+8] = (s16)row[+2] (aux) and r3 = &[sp+8] = ctx.
  - Calls: HAND 0x0223C16C(side, cid, r2 = filter, r3 = ctx, [sp] = row[+8] word, [sp+4] = 2),
    then GY 0x0223C4E8(same, [sp+4] = 0xC).
- **Builder filter-callback convention**, proven from 0x0223C824 / 0x0223C838 / Tour Guide's
  shipped filter: at entry, [sp] = &card word and [sp+4] = ctx; return 1 = keep.
  - 0x0223C825 itself tail-calls ARM9 0x020240D9(cid, *ctx), a relation check, so it is
    card-specific and not reusable.
- **PICK_AT 0x0219C94C returns 0x02299458 + 4*i**, a pointer into the picker's own buffer (a COPY),
  not into the zone array. So a zone cannot be told from the pointer.
- **0x021A2510(side, ref) = GY index of ref, else -1.** It walks player+0x55C for count
  player+0x14 and computes ref = bit14(w) + (((w<<1)>>24)<<1).
- **Dark Simorgh 0x1E5A = the native two-pick banish-cost protocol, in BOTH zones**
  (cls2 @0x02277F14 {res 0x02206ABD, cond 0x021FEBA9, cost 0x021EB7AD};
   @0x02277F2C {res 0x0220731D, cond 0x021FEBA9, cost 0x021EC57D}; disasm 2026-09-28):
  - Phase machine at [0x0229AAFC+0x7C]. Pick k's REF (u16) goes to desc[+0x14+2k] and the count
    to desc[+0x12]; after 2 picks it goes to commit.
  - GY cost 0x021EB7AC: picker 0x0219C430(side, 6, cid, param = (desc[+0x12] ? 6 : 2) << 28),
    readback 0x0219C510.
    Commit: CHAIN_PUSH 0x021D28A4; for k in 0..1:
    `0x021A25E8(ref) -> &word ; 0x021C7104(side, &word, 0)`; CHAIN_POP 0x021D2964; return 1.
  - HAND cost 0x021EC57C: hand picker 0x0224B9F0(side, cid, 0, filter 0x022065F9) /
    0x0224BBB0; the chosen index is at [0x0229DE14]; ref is read from player+0x124[idx].
    Commit: `0x021A25A0(side, ref) -> &word ; 0x021C6E98(side, &word)`.
  - CORRECTION (disasm 2026-09-28): **0x021A25A0(side, ref) = HAND INDEX of ref, else -1**. It
    walks player+0x124 (0x49<<2) for count player+0x0C and returns an index, NOT a pointer.
    **0x021C6E98(side, handIdx)**: `bmi` on a negative idx; locator 0x0219CA28(side, 0xB, idx);
    core 0x021C6B00 with r3 = 0xF (banish), [sp] = 0, [sp+4] = 1.
    **0x021A25E8(ref) -> &word, in ANY zone** (0x021A220C(ref) -> packed locator, 0x1000 = not
    found -> returns 0; else 0x0219CA28(side, zone, idx)).
    **0x0219C510() = 0x02299458 + 4*[0x0229944C+4]**, the current pick's buffer slot.
  - => mixed hand/GY banish, per ref:
    `h = 0x021A25A0(side, ref); h >= 0 ? 0x021C6E98(side, h) : 0x021C7104(side, 0x021A25E8(ref), 0)`.
- **Row resolver 0x02243B9C head** (disasm): `r5 = cid, r4 = r1 (param)`; alias map 0x020236F4;
  binary search -> r6. At the hook site 0x02243BEC, r4 is the caller's RAW param. Both
  candidate counters, 0x02243FA8 and 0x02243FE0, pass their r2 param straight in.
  => a criteria_row_hook arm for 0x1319 can simply keep r4 = param (0 / 1 / 2).
- SUPERSEDED (3-row design abandoned, see Ruled Out; only 0x16FD is used, 0x0EA9/0x0EAE were
  un-claimed again). Original note: **Phantom drops chosen for the 3-row criteria insert: 0x16FD, 0x0EA9, 0x0EAE.** Each has:
  no card_prop; exactly 1 criteria row; absent from PHANTOM_CLAIMS; absent from list A; not any
  row's aux; identical in stock ov3 and rom_all_patches.nds (scratchpad phantoms.py).
  Passed over: 0x14DD (list106), 0x167D (arm of 0x021E7C88's switch), 0x14D7 (fusion
  recipe), 0x1529 (another phantom's aux), 0x0E9D (tribute-switch arm).

- **0x0202ABB8 race getter = card_prop bits 49..53** (disasm: `ldr r0,[r0,#4]; lsls #0xA; lsrs #0x1B`),
  the field holding 23 for every Spell and 24 for every Trap. So `race < 23` is a valid monster test.
- **Builder flag word** (KB dispatch.criteria_handler_flags_word): bit 3 = action SS, bit 16 = action BANISH.
  Native GY banish thunk 0x0223CA10 passes 0x10000; the hand+GY SS handler 0x02240E98 passes 2 (hand) / 0xC (GY).
- **BUILT 2026-09-28**: `_build_double_evolution_pill.py` on rom_all_patches.nds (sha256 30e0c109...d04c),
  giving rom_double_evolution_pill.nds sha256 9b82f8a1109acb98ee4485a88bc258a6c1db3687542a5c1aff04e7256118ca7e.
  verify() 5/5 PASS. check_allocations clean (ledger emitted). **in-game confirmed by user 2026-09-28: all 11 items** (11-item
  oracle in the build script docstring).
  - Final design, one criteria row:
    - cls0[199] = {0x02206F41, 0, COND 0x023A2141, COST 0x023A2221, 0}.
    - criteria {0x1319, 0xFFFF, HAND 0x023A2361, 0x485C0002}, count-neutral over phantom 0x16FD.
  - ov5 slots: COND 0x023A2140 (0xC8/0xE0), COST 0x023A2220 (0x10C/0x140), HAND 0x023A2360
    (0xA8/0xC0), FILT 0x023A2420 (0x54/0x60). CAVE_FREE -> 0x023A2480.
  - HAND mode switch:
    - Cost mode when [0x0229AAFC+0x7C] != 0 && [0x0229A9FC+0x50] cid == 0x1319 && desc[+0x12] < 2.
    - Otherwise target mode, a copy of 0x02240A94.
  - ASSUMED (the in-game test decides):
    - (a) [0x0229A9FC+0x50] points at our desc during the cls0 cost's picker (the cost also writes it
      in phase 2);
    - (b) builder 0x0223BFD4 ANDs the filter callback with the word;
    - (c) PICKER 0x0219C430 accepts a mixed hand+GY candidate list for a banish cost;
    - (d) the chosen prompt 0x56 text is sensible.

## Ruled Out
- 0x0223BFD4 as a hand+GY zone builder (it evaluates one card).
- **A 3-row design via a criteria_row_hook arm**: appending ANY arm to the shared stub puts its top
  `beq native` out of Thumb conditional range (thumb_asm AsmError "beq out of range: 137"). The stub
  is FULL at 9 arms; adding a tenth needs a trampoline edit to the shared stub. Measured 2026-09-28.
- **List A / list B two-row membership**: every no-card_prop cid in list A (0x0E32, 0x0E6B, 0x0EA8,
  0x1303, 0x234E) and list B (0x234F) is already in PHANTOM_CLAIMS; in the chained image only
  0x234E (claimed) remains in list A.
- Telling a picked card's zone from the PICK_AT pointer (it points into a buffer copy).
- 3DS as an architecture source for this exact card: the card is not in the 3DS build.
- A summon-restriction hook for "ignoring Summoning conditions": no Dinosaur
  is in a class (see Confirmed).

- **ASSUMED (a)-(d) under BUILT are settled by the user's in-game test 2026-09-28** (items 2-4: both
  picks listed the right cards from hand+GY and banished a hand/GY mix). That confirms by behaviour the
  single-row mode-switching handler and the cost-state-word discriminator on a cls0 cost.

## Open Questions
- Word 0x485C0002 (Dino, Lv>=7) is derived from dispatch.criteria_word_level_field and the Emergency
  Teleport word; it has not been seen verbatim in the ROM. The in-game oracle item 5 tests it.
- RESOLVED 2026-09-28 (user: allow it). Edge case: if the ONLY Lv7+ Dinosaur is in the hand and it is also banished as the
  Dinosaur cost, the summon has no target (COND does not reserve it). Ask the user whether that
  matters.
- The hit scan covered arm9/ov3/ov5 only; the AI-rule overlays were not scanned for 0x1319.
- The KB tool.criteria_row_hook_stub_full fact: the next card needing a row-hook arm must fix the
  shared stub first.

## Next Experiment
- USER in-game test of rom_double_evolution_pill.nds, normal duel (NOT a puzzle), using the 11-item
  oracle in _build_double_evolution_pill.py.
- If the cost picker shows the wrong / empty candidate list: take a savestate at the prompt and read
  [0x0229AAFC+0x7C], [0x0229A9FC+0x50] -> desc[+0x12], and picker count [0x0229944C+6] to see which
  HAND mode ran.
