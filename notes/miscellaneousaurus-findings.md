# Miscellaneousaurus — findings

Scope: **C2 only** (GY: banish N Dinosaurs incl. this card; SS Level-N Dinosaur from Deck; destroy at End Phase; OPT).
C1 deferred by user ("Decide after C2"). Donor: **Krokodilus 0x0FF2** (user's pick, 2026-09-22).
Status: **C2 in-game confirmed by user 2026-09-22 on build 3**. Build 4 adds C1 (AWAITING IN-GAME TEST) + the speed hook (C2 regression test pending). NOT shipped to steps.STEPS.

## Confirmed
- Printed text: ygoprodeck_cache.json id 38572779, FIRE Dinosaur Lv4 1800/1000. (read 2026-09-22)
- Not in the 3DS build: "Miscellaneous" not in CARD_Name_E.bin (Explore agent, 2026-09-22).
- Krokodilus = cid 4082 (0x0FF2) per scratch/cid_to_name.json; only repo ref = patch_bulk_card_pack.py:2170 (pack 50).

- **Donor 0x0FF2 per-cid gates: NONE in ov3/ov5** (aligned-u16 scan of stock rom.nds, all overlays, 2026-09-22,
  scratchpad scan_cid.py). ARM9 hits are not cids: 0x0203072C/0x02030778 = Thumb `lsrs r2,r6,#0x1f`;
  0x0209D63E.. / 0x0209E490.. / 0x020A1492.. = monotonic ramp math tables; ov6/ov34 hits = ARM imm operands.
  Deckgen deck lists: 0 hits for Krokodilus / 4082.
- **GY-action registry 0x0228DDF8 row 12 = {0x144C, 0x0E, 0x0224C55D, 0x0224C669}** in BOTH stock rom.nds and
  rom_all_patches.nds (2026-09-22 dump) → unclaimed sibling-family phantom, convertible to the Grapha family
  {chk 0x0224C591, post 0x0224C6C1} per the Remus method. Row 13 (0x1452) likewise.
  ⚠️ Ledger gap: Remus converts row 11 (0x1449) but allocations.yaml has no gy_action_registry entry for it;
  chained row 10 now reads cid 0x1449 (stock 0x1315) — some patch rewrote it; not investigated.
- **Survival Instinct 0x1AA2 (native "banish any number of Dinosaurs from GY")** in stock ov3:
  - cls0[743] @0x02282BF4 = {0x1AA2, 0x02206139, 0, cond 0x021F94ED, cost 0x021E5319, 0}
  - criteria[467] @0x022729A8 = {0x1AA2, 0xFFFF, 0x0223CA11 (GY), 0x48000002} (race byte 0x48>>3 = 9)
  - LP-change row @0x022709B0 = {0x1AA2, 0, 0x0190 (=400), 7}
  - banish-count switch 0x021E5318 leaf 0x021E53F0 → r4 = 0x20 ("any number"), cid literal @0x021E55B4
    (leaf table from notes/gates-of-dark-world-findings.md:620 — re-confirm by disasm).
- **Race byte 0x48 = Dinosaur**: KB dispatch.criteria_word_race_attribute race 9 = Dinosaur (8/8); game_constants.py:440.
- **Banish cost 0x021E5318 disassembled (stock ov3, 2026-09-22)** — a phase machine on [0x0229AAFC+0x7C]:
  - entry: r4=1 (count), r6=1 (exact). `bl 0x021D2BC8` nonzero → return 1 (copy-exempt path).
  - cid switch on ldrh [desc]; first literal @0x021E55B4 (loaded at 0x021E5330) = 0x1AA2 → `bge 0x021E53F0`:
    r4=0x20, r6=0 ("up to / any number"). DEFAULT leaf 0x021E5422 keeps r4=1,r6=1.
  - phase 0: (cid == literal@0x021E55E4 special) else `0x0219A818(side,0x56)` prompt, phase++.
  - phase 1: r1 = r6 ? r4+6 : r4+0x27 → **any number = 0x47** (matches Soul Charge COUNT_CODE);
    r3 = 0x02234E78(desc) (criteria param = the donor's criteria row); `0x0219C430(side, code, cid, crit)`.
  - phase 2: if r6==0: **desc[+0x14] = [0x0229DD94+0x34]** (the chosen count, u16; CORRECTED — first written as
    0x0229AAFC+0x34, which is wrong, see "In-game test 2"), then a second per-cid switch.
  - So Survival Instinct's count reaches its resolver via desc[+0x14]. A donor on the default leaf banishes exactly 1.
- **Deck-SS Dinosaur criteria template = Babycerasaurus 0x1A8F criteria[462]** {0x1A8F, 0xFFFF, 0x0223CA99 (Deck),
  0x48900002} (0x90 = op2 Level<=4). For "Level exactly N": level byte = N<<2 (op 0; KB
  dispatch.criteria_word_level_field, level 0 = unconstrained so N>=1, max 15). Its cls2[222] @0x022770D4 =
  {0x1A8F, 0x02206CAD, 0, 0x0224A115, 0, 0}. All stock race-9 rows: 270 Ultra Evolution Pill, 461 Miracle
  Jurassic Egg, 462 Babycerasaurus, 465 Fossil Excavation, 466 Hunting Instinct, 467 Survival Instinct,
  469 Seismic Shockwave, 965 Fossil Dig. (stock dump 2026-09-22). cls2 base = 0x02275C04.
- **"Destroy it during the End Phase" is PURE DATA — the Rescue Cat / Swing of Memories mechanism** (stock ov3, 2026-09-22):
  1. Summon-event handler opcode 0x14 prologue: `ldrh r0,[r4,#0x12]` searched in list **0x0228F708 (0x24 entries,
     count immediate `movs r2,#0x24` @0x0226808E, search bl 0x02022E14 @0x02268090)** → on hit
     `0x021C479C(side [r4+2], zone [r4+4], key [r4+0x12], kind 2, 0)` @0x022680A4.
     (Other list 0x0228F750, 0x2E entries → kind 3 @0x02268086.)
  2. End-Phase registry 0x0228E1E0 (8-B rows {fn, cid}): **fn 0x02254E95** rows 215 Rescue Cat, 216 0x21D4 Viper's
     Rebirth, 217 0x23BF Wattkeeper, 230 0x0DAD, 232 0x1B5F, 233 0x1B27, 234 0x0D5D, 235 Swing 0x1C58,
     236 0x1F62, 237 0x1F79, 238 0x200C, 239 0x247D.
  3. 0x02254E95 = `0x02254DFC(r0, r1=cid, 0xE, 1, [sp]=0, [sp+4]=0)`; worker walks monster zones 0..4, family-1
     walker **0x021A1430(side, zone, cid)** (node keyed by the source cid), on hit removes node
     0x021C48DC(side,zone,cid,1) and destroys via 0x021CDDA8(side, zone, 0xE, ...).
  ⚠️ **KB CORRECTION: [r4+0x12] is the SOURCE effect's cid, not "the summoned card's cid"**
  (rider.banish_marker_attach_site). Proof: list 0x0228F708 holds Spells that are never summoned — Swing of
  Memories 0x1C58, Level Modulation 0x1944, Over Destiny 0x1B27, Junk Box 0x200C, Wicked Rebirth 0x201B — and
  the End-Phase worker keys the node by the registry (source) cid. The KB's self-summon examples
  (Plaguespreader/Quillbolt/Jet Synchron) have source == summoned, which hid the difference.
  List 0x0228F708 members (36): 0x0D5D 0x0D62 0x0D6B 0x0DAD 0x0DB2 0x0DBE **0x0E2E (no name — phantom?)** 0x1481
  0x156A 0x15ED 0x1619 0x16A4 0x1876 0x1900 0x1944 0x1A7B 0x1B27 0x1B5F 0x1BFB 0x1C58 0x1CD6 0x1D6A 0x1E43
  0x1F62 0x1F79 0x200C 0x201B 0x20CD 0x2152 0x21B7 0x21D4 0x225E 0x231F 0x237A 0x23BF 0x24E6.
- **End-Phase slots chosen (both unclaimed, present in stock AND rom_all_patches.nds, 2026-09-22):**
  - List 0x0228F708: **0x0E2E is a phantom** (not among the 4305 card_prop cids) and sorts between 0x0DBE and
    0x1481, as does 0x0FF2 → in-place swap keeps the list sorted and the count at 0x24. Its only ledger mention
    is ("populate_table", 0x0E2E, "tour_guide"), a different pool → new pool `list_0228F708`.
  - Registry section 63..287 (the End-Phase section, KB timing classifier): **row 254 @0x0228E9D0 =
    {0x02254ED1, 0x0E43 phantom}** → rewrite to {0x02254E95, 0x0FF2}. Unclaimed phantom rows in that section:
    99 103 104 105 133 144 145 152 154 161 176 198 249 254 (+ cid-0 rows). Pool `registry_row`.
- **Self-banish-from-GY = native 0x021E5709(desc)** (disasm 2026-09-22): idx = 0x021A2510(side, desc[+0xC] ref)
  (bmi → skip); &word = 0x0229AC94 + (side&1)*0xB3C + 0x55C + idx*4; 0x021C7104(side, &word, 0) → GY→banished
  applier 0x021C7118. It is the cls2 +10 cost of ~20 natives whose text is "banish this card from your GY"
  (Necro Gardna 0x1C0A, Mezuki 0x1CBF, Shield Warrior 0x1E17, Skill Successor 0x20A1, Symphonic Warriors
  0x246C-E, Stardust Phantom 0x244E ...). GY array = player + 0x55C.
- **0x021E5318 phase-2 tail** (default path 0x021E56A2): chain push 0x021D28A4; for i < [0x0229DD94+0x34] (CORRECTED, literal @0x021E56E4):
  0x021C7104(side, 0x0219C94C(i+1), 0); chain pop 0x021D2964; return 1. (0x021E56E9 = 0x021E5318 then
  0x021E5060 stamp — Bazoo/Freed/Lifetrancer wrapper.)
- **Deck-SS resolver: DO NOT delegate to 0x02206CAD** — froze in-game for NAST round 11 (patch_ninjitsu_art_
  super_transformation.py:28-34); user ruled delegation out. Reimplement its default-arm phase machine as NAST
  PART F3 does (phases 0x80 gates+count 0x02243FA8 / 0x7F msg 0x30 / 0x7E picker 0x0219C430(side,6,cid,param) /
  0x7C 0x0219C510() → commit 0x0226925C(side,&loc,1,2,[sp]=acting_cid<<16) / 0x7B 0x0225BF30(1-side) /
  0x78 0x021D269C(side) → 0x64). The commit's [sp] high half → [0x02298A28+0x12] = the SOURCE attribution the
  End-Phase list keys on (consistent with the KB correction above).
- **Two criteria rows via LIST A (data, no row-hook arm)**: list A 0x0227134C (59, sorted, `movs r2,#0x3b`
  @0x02243BF0), rule row = (param != 0) ? 1 : 0. Our own stubs call 0x02243FA8 / 0x0219C430 with param 0 (Deck
  row) or 1 (GY row). Chained-ROM phantom **0x0EA8: in list A, owns criteria rows 33+34, unclaimed in every pool**
  ("last spare list-A pair, kept for the next card", patch_darkflare.py:383) → drop both rows + its list-A slot.
  Rows: rel0 {0x0FF2, 0xFFFF, 0x0223CA99, 0x48000002} (Babycerasaurus handler, level byte 0 at rest, set to N<<2
  by the resolver); rel1 {0x0FF2, 0xFFFF, 0x0223CA11, 0x48000002} (Survival Instinct verbatim).
- **cls2 record slot**: chained cls2 (0x2B9, sorted) phantom **0x0EBF @idx 28, unclaimed in every pool** → drop,
  insert 0x0FF2 sorted.

## Pre-build risk checklist (C2)
1. Per-cid gates on 0x0FF2 — PROVEN none (ov3/ov5 u16 scan). Donor takes DEFAULT arms everywhere it passes a
   cid switch; our stubs replace every switch-bearing native (cost 0x021E5318, resolver 0x02206CAC).
2. Zones — PROVEN: cost row handler 0x0223CA11 = GY (KB counter.criteria_handler_selects_container 46/46);
   effect row 0x0223CA99 = Deck (30/30); self-banish 0x021E5709 reads the GY array.
3. Text — card_text.CARD_TEXT re-emit (no slot limit).
4. OPT — query 0x021A14E9(side,0x0B,cid,1) in +0C; stamp 0x021D2585(side,cid,1,0) at the cost's final phase
   (Jet Synchron precedent, dispatch.once_per_turn_must_stamp_at_activation).
ASSUMED: (a) picker code 0x47 human MINIMUM (can a player pick 0 others → N=1?) unmapped; stub skips the picker
when there are 0 other GY Dinosaurs. (b) self-banish BEFORE the picker excludes this card from its candidates.
(c) the End-Phase node attaches for a cls2-sourced Deck SS (list 0x0228F708 path is source-agnostic by reading).
- Once-per-turn pair (patch_soul_charge.py): check 0x021F6DD8(desc)→0 iff own turn node exists; post
  0x021D2584(side, cid, 1, ref); cond must skip on desc[+7].

## Ruled Out
- Stock NDS/3DS handler for this card: none exists.
- **Level via the ACTING DESCRIPTOR [0x0229A9FC+0x50] in a custom criteria handler** — killed by disasm
  2026-09-22: the slot dispatcher writes +0x50 ONLY around the slot-2 (+08) filter call (`str r5,[r0,#0x50]`
  @0x0224AE20, restored @0x0224AE3C); the slot-3 condition runs BEFORE it (blx @0x0224AE10) and the resolver
  invoker 0x0224AEB8 never writes it. So at resolution time it can be another chain link's descriptor.
  → Instead: cond/resolver locate row 0 with 0x02243B9C(cid, 0) (binary search → row index; 0x02243BCA
  `muls r2,r3(=0xC)`) and write the level byte at row+0xA; the native Deck handler 0x0223CA99 reads it.
- **Level word in ov5** — avoided: mem.ov5_runtime_state_wiped_mid_duel (UNVERIFIED) risk; ov3 criteria table is
  main-RAM resident (Shien's Dojo rewrites its row's bound byte the same way).
- 0x0223CA98 (Deck handler) reads ONLY row+0 (cid) and row+8 (word), then 0x0223BC3C(ctx, cid, 0, 0,
  [sp]=word, [sp+4]=0xA) — so the level byte in the row IS the filter.

## Open Questions (all inherited from Explore agents — UNVERIFIED)
- GY activation: phantom rows 12/13 (0x144C/0x1452) per patch_dragunity_remus.py:493-512 — free?
- Variable-count Dinosaur banish cost: Survival Instinct (cid 0x1AA2 vs 0x1A52 — join unverified).
- Deck SS Level N: NAST criteria handler LEVEL_BITS word `(N<<2)<<16`.
- End-Phase destroy rider: native precedent via walker 0x0225432D (W Nebula family).
- Donor per-cid gates on 0x0FF2: unchecked.

- How to route donor 0x0FF2 onto the 0x20 leaf: (a) hook the switch head 0x021E532E (shared, 6k cids pass) or
  (b) own ov5 cost that sets r4/r6 and tail-jumps into 0x021E5422 (needs r4..r7 frame reproduced).
- "including this card": Survival Instinct's picker is plain GY-Dinosaur — nothing forces this card in. UNRESOLVED.
  Ruled out as a native "force-include": the phase-0 pre-select at 0x021E5450 is The Fountain in the Sky 0x227B
  only (literal @0x021E55E4); 0x02243FA8(side,cid,crit) returns the CANDIDATE COUNT ([0x...+6]) and the branch
  auto-picks pick 0 when it is exactly 1. Count-switch literals 0x021E55B4.. = Survival Instinct, Lekunga,
  Bazoo, 0x18F8, Naturia Barkion, Dark Nephthys, Splendid Rose, Enishi (2026-09-22 dump).
  Picker MINIMUM for code 0x47 (can a human pick 0?) — UNMAPPED (KB dispatch.multiselect_count_code_ranges).
- Donor needs TWO criteria rows (cost: GY Dinosaur 0x0223CA11/0x48000002; effect: Deck Dinosaur Level N) →
  two-row mechanism (LIST B / param-provider hook 0x02234E78) — which row does the cost's 0x02234E78 call read?
- cls2 slot roles for a Grapha-family GY action with a COST (Jet Synchron C2 precedent) — unread.

## Build (2026-09-22)
- patch_miscellaneousaurus.py + _build_miscellaneousaurus.py → data/over_the_nexus/working/rom_miscellaneousaurus.nds
  sha256 6ed6b46d6be076e86596739a38ca58171fd112264e822ce38d47bfb47ab86f6a (deterministic across 2 builds),
  verify 8/8 PASS, check_allocations clean after --emit, all blx literals odd / no POP-LR (capstone pass).
  Edits on stock: GY row 12, cls2 @41 (0x0EBF dropped), criteria @69/70 (0x0EA8 pair), list A @4,
  End-Phase list @6 (0x0E2E), registry row 254. ov5: COND 0x023A14F4 (172 B), COST 0x023A15A4 (188 B),
  RES 0x023A1664 (296 B); CAVE_FREE → 0x023A1794.
- NOT wired into steps.STEPS (user has not approved shipping). Donor-pool note NOT updated (only on ship).
- KB: added rider.endphase_destroy_by_source_cid, dispatch.self_gy_banish_cost,
  dispatch.banish_count_cost_machine, dispatch.acting_desc_scoped_to_slot2 (all VERIFIED),
  card.miscellaneousaurus_c2 (UNVERIFIED). author_facts --check: 500 PASS 0 FAIL.
  Left alone: rider.banish_marker_attach_site's "summoned card's cid" wording (corrected in the new fact).

## In-game test 1 (user, 2026-09-22, build sha 6ed6b46d...)
- Item 1 card/text: in-game confirmed by user 2026-09-22
- Item 2 N=1 path (only Misc in GY, Lv1 summoned): in-game confirmed by user 2026-09-22
- Item 3 FAILED: "There were some graphical glitches but it didn't let me select another dinosaur".
  User: Misc was banished first; the effect continued and summoned a monster.
- Item 4 End-Phase destroy: in-game confirmed by user 2026-09-22
- Item 5 once per turn: in-game confirmed by user 2026-09-22
- Items 6, 7: not verified.
- Savestates rom_miscellaneousaurus.ml2..4 (ml1 has no duel), identity = our 3 stubs + 2 criteria rows:
  - ml3 (cost phase +7C = 1, picker open): picker block 0x0229944C [+2] = 0x4B, [+6] = 2 candidates; locator
    list 0x02299458 = [0x0F0020CD Jurrac Guaiba, 0x01000FF2 Krokodilus] — the already-banished Misc is still a
    candidate. GY (side 0) held only ONE other Dinosaur (Jurrac Guaiba).
  - ml4 (cost phase 2): [0x0229AAFC+0x34] = 0 picks, picker [+2] = 0x47, [+6] = 1 → N = 1 path taken.
- DEAD HYPOTHESIS (strike 1 on the cost picker): "self-banish in phase 0, then the picker" — the picker was built
  against a GY we had just mutated (stale candidate incl. Misc; glitched UI). Native 0x021E5318 never mutates the
  GY before its picker. Fix (user's proposal): picker over ALL GY Dinosaurs incl. Misc, banish picks, then banish
  Misc only if not picked.

## Build 2 (2026-09-22)
- COST rewritten to native order: phase 0 -> if row-1 candidates <= 1 (only Misc) banish Misc, N=1; else prompt.
  phase 1 picker 0x47 over ALL GY Dinosaurs (Misc included). phase 2: N = picks + 1, scan picks (cid == 0x0FF2
  -> N = picks); chain push; banish picks; if N != picks banish Misc via 0x021E5709; chain pop; OPT stamp.
- Cave re-laid (nothing shipped): COST 0x023A15A4 (236 B / 0xF0), RES 0x023A1694, CAVE_FREE 0x023A17C4.
- ROM sha256 2a5c3c918fd39fba348af7c81a7b5101561d8042c521be0d0f043d243b3a11f4, verify 8/8, ledger clean.

## In-game test 2 (user, 2026-09-22, build 2 sha 2a5c3c91...)
- Picker opens without glitches, lists Misc + the other GY Dinosaurs: in-game confirmed by user 2026-09-22.
- Item 6 (no Lv1/Lv2 Dinosaur in Deck -> NOT offered): in-game confirmed by user 2026-09-22.
- Item 7 (confirm picker with 0 selected -> only Misc banished, Lv1 summoned): in-game confirmed by user 2026-09-22.
- FAILED: "I select 2 cards, but only misc is banished and i can only summon a level 1"; picked cards stayed in GY.
- ROOT CAUSE (proven, not a hypothesis): the pick count is [0x0229DD94+0x34], NOT [0x0229AAFC+0x34].
  0x021E5318's literals: 0x021E55DC = 0x0229AAFC (phase counter +0x7C), 0x021E55E8 and 0x021E56E4 =
  0x0229DD94 (count +0x34, loop bound). Savestate ml3 (build-2 cost bytes identity-matched, cost phase 2):
  AAFC+0x34 = 0, DD94+0x34 = 1. Our stub read AAFC → count 0 → picks ignored, N = 1. My earlier note line
  "desc[+0x14] = [0x0229AAFC+0x34]" was WRONG (literal never decoded); KB fact dispatch.banish_count_cost_machine
  corrected same session, proof now asserts both literals.

## Build 3 (2026-09-22)
- Phase 2 reloads r6 = 0x0229DD94 before every +0x34 read. COST 0x023A15A4 (244 B / 0x100), RES 0x023A16A4,
  CAVE_FREE 0x023A17D4. sha256 ad0bac489fcfbf8e7b2f374dc3b6299a8a01a36fee7e308bba08db81578aff0f, verify 8/8.

## In-game test 3 (user, 2026-09-22, build 3 sha ad0bac48...)
- User: "Perfect! C2 Works as described!" -> multi-pick cost (3 / 3b / 3c), Level-N Deck summon and End-Phase
  destroy: in-game confirmed by user 2026-09-22. With tests 1-2, EVERY C2 oracle item is confirmed.

## C1 scope (user decisions 2026-09-22)
- C1 as implemented = hand quick effect, either player's Main Phase, cost: send this card from hand to GY;
  effect: YOUR face-up Dinosaurs (snapshot at resolution) become unaffected by ALL card effects until end of turn,
  via the Azure-Eyes protection link 0x021B0592 (user chose "B"; printed "opponent's activated effects" / "this
  Main Phase" are USER-ACCEPTED simplifications, 2026-09-22). C2 (confirmed) must not regress.

## C1 research (2026-09-22, stock ov3/ARM9 disasm)
- Protection: Azure-Eyes link 0x021B0592 stub queries family-1 walker for PRIVATE key 0x1E9C (patch_azure_eyes
  PROT_KEY). Reuse = attach 0x021C479C(side, slot, 0x1E9C, kind byte 0x02 (duration 0 = until end of THIS turn),
  [sp]=0) per own face-up Dinosaur zone. No new hook. Single-card ROM must also carry Azure's link stub.
- Hand quick-effect template = Effect Veiler 0x22E5: cls2[582] {res 0x02208849, filter 0x021E01E5, cond
  0x02202EED, cost 0x021E8FB9 (send THIS card from hand to GY; Honest 0x1D96 shares it), target 0x02234D99}.
  Offer = hand list B 0x0209BC8C (36, sorted) AND speed-2 list 0x0209C118 (0x76, sorted): every list-B quick
  effect (Veiler, Honest, Kalut, Gadget Driver...) is in both; list-B hand IGNITIONS (Noisy Gnat, Fabled) are not.
  List B phantoms 0x0E63 / 0x1774 / 0x1A86 are claimed only under "quickeffect_list" (the 0x0209C118 pool).
- ONE cls2 record per cid (leftmost shadow) → C1 shares C2's record, split on desc[+3]: 0x0E GY / 0x0B hand.
- Phase codes (KB, VERIFIED): [0x0229DD14+0x48] 2 = MP1, 4 = MP2; +0x34 turn player.
- ⚠️ SPEED LEAK: GY offer gate 0x021ECC6C — no pending link: passes if speed(desc) >= 2 BEFORE the own-turn/MP
  check 0x021ECC28; pending link r1: needs speed(ours) >= speed(link) and >= 2 (0x021ECC7E..0x021ECC9A).
  So joining 0x0209C118 would make C2 usable on the opponent's turn and as a chain response.
- Speed lookup 0x021A87BC(desc): per-cid tree (r2 = cid throughout), native dual-speed cards force 1 by desc[+5]
  / desc[+4]; DEFAULT leaf 0x021A894C `adds r0,r2,#0 ; bl 0x0202345C` then 0x021A8952 `pop {r4,pc}`. No shipped
  patch hooks it. Some native leaves reach 0x021A894C with r0 = a class byte (not desc), but only for their cids.

## Build 4 = C1 + C2 (2026-09-22)
- C1 on the SAME cls2 record; stubs split on desc[+3] (0x0E GY -> C2 unchanged; 0x0B hand -> C1; else cond 0).
  COND: hand AND [0x0229DD14+0x48] in {2,4} -> 2. COST: tail-call 0x021E8FB9. RES (phase 0x80 only): own
  side desc[+2]^desc[+6], zones 0..4: cid = 0x021A36EC, face-up u16 [0x0229ACD0+(side&1)*0xB3C+slot*0x14] != 0,
  race 0x0202ABB8 == 9 -> 0x021C479C(side, slot, 0x1E9C, 0x02, [sp]=0); return 0.
- ARM9: list B 0x0209BC8C 0x0E63 -> 0x0FF2 (@1); speed-2 list 0x0209C118 0x1534 -> 0x0FF2 (@8).
- Speed hook 0x021A894C: stock bytes 101c7af685fd (adds r0,r2,#0 ; bl 0x0202345C) -> bl CAVE_MISC_SPEED + nop.
  Stub: cid == 0x0FF2 && desc[+3] == 0x0E -> 1, else r0 = r2, bx 0x0202345D.
- Azure-Eyes link 0x021B0592 + its stub CAVE_AZURE_PROT installed idempotently (single-card ROM).
- ov5: COND 0x023A14F4 (208 B) / COST 0x023A15C4 (256 B) / RES 0x023A16D4 (420 B) / SPEED 0x023A1884 (32 B),
  CAVE_FREE 0x023A18A4. sha256 ab4f6f086b96e537c856f537d035e2290db6ac64e37a103a2c4ab5a0ece18ac3 (after the C1 text rewording, user request 2026-09-22), verify 12/12, ledger in sync, stubs footgun-clean.
- ASSUMED: face-up flag = u16 at player+0x3C+slot*0x14 (read from native face-up counter 0x021AC9FC, not
  measured); hand-path descriptor desc[+3] == 0x0B (criteria_row_hook's documented zone codes).

## In-game test 4 / C1 (user, 2026-09-25)
- User built a Dark Hole / Offerings-to-the-Doomed CPU testbench ROM
  (_build_miscellaneousaurus_testbench.py, chains patch_miscellaneousaurus + patch_testbench_decks,
  default DECK_CARDS pair) to exercise C1 against both non-targeting and targeting removal every turn.
- User: "Looks great! Ship it" -> "confirmed C1 works as expected" -- **C1 in-game confirmed by user
  2026-09-25**. With build-3/test-3's C2 confirmation, both clauses are now in-game confirmed.

## SHIPPED 2026-09-25
- Wired into ygo_tools/tools/enhanced_edition_definitive/steps.STEPS (after patch_scrap_raptor) and
  _verify_all_patches.py SHIPPED list.
- EE fast build: 75/75 steps, sha256 3cfd1d72d3d43716260247c0d507c1117aa927aa603590baba90a0ca3c550331.
- Verify sweep (otn_enhanced.verify): 60 passed, 1 failed
  (patch_ninishi -- PRE-EXISTING, unrelated: patch_scrap_raptor's C1b intentionally rewires ninishi's
  five CAVE_NS_* hook sites to chain through its own sr_ns* trampolines, so ninishi's own verify (which
  expects a direct `bl ns_*`) fails once scrap_raptor sits in front of it. Documented in
  patch_scrap_raptor.py itself; not caused by this card).
- Side fix required: patch_miscellaneousaurus's GY-action row conversion (0x144C, sibling family ->
  Grapha family {0x0224C591,0x0224C6C1}) is the SECOND phantom converted into that family (Dragunity
  Remus converted 0x1449 first). patch_dragunity_remus.py's verify() hardcoded the resulting family
  counts (46/9/5); fixed to floor checks (>=46 Grapha, ==9, >=4 sibling) since the count legitimately
  grows every time another card joins the family. Not a functional bug -- same staleness class as the
  card_text drift documented in notes/verify-sweep-failures.md.
- Investigation note: a build run against a STALE __pycache__ (from an unrelated, already-uncommitted,
  not-yet-shipped Souleating Oviraptor entry in timing_class_hook.py's ARMS) transiently produced 5
  extra false FAILs (patch_lightpulsar/jet_synchron/jet_warrior/accel_synchro_stardust_dragon/
  patch_psi_reflector) on a shared stub byte-count mismatch. Clearing __pycache__ and rebuilding made
  them disappear; unrelated to this card. If a future session sees these five fail together again,
  clear __pycache__ and rebuild before suspecting a real regression.

## Next Experiment
- Card is shipped; nothing outstanding for Miscellaneousaurus itself.
- Unrelated, for a future session: Souleating Oviraptor (donor Two-Headed King Rex 0x0FC6) has an
  uncommitted ARMS entry in timing_class_hook.py ("AWAITING IN-GAME TEST 2026-09-25") but no
  patch_souleating_oviraptor module or steps.STEPS entry yet -- picked up mid-flight, not started this
  session, do not assume it is further along than that comment says.
