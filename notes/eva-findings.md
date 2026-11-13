# SHIPPED 2026-10-05 (user: "Ship it")
- steps.STEPS step 89/92 (after the Seal) + _verify_all_patches.SHIPPED. EE build 92/92 in 340.6 s,
  sha256 e2cf11837729c2c5214009095fe7f7047461e55653d67654890c511a38e398f4 (129,661,576 B).
- vs the tested rom_eva.nds: arm9, all 50 overlays and every file except Data_arc_pac/card.pac are identical. card.pac =
  patch_card_art's art, committed 14:24 2026-10-02, after the old base chain was built at 14:15. Cosmetic.
- Verify sweep: 78 passed / 0 failed. patch_eva's chain-walk check now compares against STOCK with the
  registered-donor allowance, because SRC = the chain contains Eva once shipped.
- Pre-ship chain backup: scratchpad rom_all_patches_pre_eva.nds (69562b52...).
- Aitsu moved to "Used as donors" and removed from scratch/donor_resource.json candidate_normal.

# Eva — findings

Card: Eva (LIGHT Fairy, Lv1, 500/200, Effect). Not in 3DS or NDS (per the user, so not looked up).
Donor: Soitsu 0x190B (vanilla WIND Fairy Lv3 0/0). Mystic Shine Ball is excluded by the user.
Plan: ~\.claude\plans\eva-not-in-3ds-quizzical-yao.md

Text (`scratch/ygoprodeck_cache.json`):
> If this card is sent to the GY: You can banish up to 2 other LIGHT Fairy monsters from your field and/or GY; add the same number of Level 2 or lower LIGHT Fairy monsters with different names from your Deck to your hand, except "Eva". You can only use this effect of "Eva" once per turn.

Scope: the whole effect, C1–C4 (user, 2026-10-05).

User rulings (2026-10-05):
- The banish is 1 or 2, never 0.
- "Different names" applies only among the added cards.
- Max banish = min(2, other LIGHT Fairies that can be banished, distinct-name Lv≤2 LIGHT Fairy targets in the Deck).

Precedents (from notes; UNVERIFIED this session):
- C1 = Shadow Mist D/E/F/G/J
- C2 = Ojamassimilation cost
- C3 = Ojamassimilation C2 loop plus an add-to-hand mover
- C4 = Shadow Mist C3 turn-log

## Confirmed
- **KB** (2026-10-05): `verify_knowledge` reports 627 facts: 557 PASS, 0 FAIL, 70 UNVERIFIED.
- **donor_scan 0x190B**: CLEAN, meaning no data structure names this cid.
  - It reports 7 "code" u16 hits. I disassembled them (scratchpad eva_hits.py): every one is the instruction `adds r3,r1,r4` (encoding 0x190B), and there are no ldr-literal users. **No literal per-cid gate.**
  - Name slot 6 B, desc slots 71–160 B. Text has to go through `card_text.CARD_TEXT`.
- **Sent-to-GY chain 0x021D1392**: `_switch_leaf(stock, 0x190B)` gives REJECT 0x021D19C0 (traced in scratchpad eva_leaf.py).
  - The terminal node is **0x021D14E2** `subs r1,#0x23 ; cmp r5,r1` with r1 = 0x1969, which is Ojamagic's node.
  - In the chain ROM this node is ALREADY `bl 0x021B594A`: **Grapha PART H's** 16 B stub, which is full.
- **Arm 0x021D18C4** (Ojamagic's arm, also reached by Eclipse Wyvern's node) is `ldr r0,[sp,#0x34] ; cmp r0,#0xB ; bne reject ; b accept`. It is **HAND-ONLY**, so it is wrong for Eva.
  - The any-location accept is 0x021D1938 → 0x021D199E (`movs r0,#1 ; b 0x021D19BE str [sp,#0x14]`), Shadow Mist's leaf. Read by disassembly this session.
- **Miss-timing tree 0x021EE0E0**: executing it in thumbemu (eva_miss.py) shows 0x190B ends at **node 0x021EE10C**, the node Shadow Mist J and Overtex J share.
  - In the chain ROM that node is `bl 0x021B58D0` (block A), then B 0x021B5AAA, then C 0x021B5840. All of them are full.
  - The stock verdict for 0x190B is 1 (missed).
- **No near ov3 dead block** within B-range (±2 KB) of 0x021B5954 or 0x021B5840 has ≥ 12 B free. The listing was from `OV3_DEAD_BLOCKS` against `OV3_CLAIMS`; the largest near block had 4 B free.
- **Far blocks with room**:
  - 0x022212E4 (phantom 0x0E82): 24 B free at 0x02221328.
  - 0x02237D8C (phantom 0x17F4): 28 B free.

- **Slot 0x02221328 (24 B)**: identical in the stock ROM and in `rom_all_patches.nds` (2026-10-02 build). It is the last 24 B of the 0x0E82 block; Seal of Orichalcos uses the first 68 B.
- **Slot 0x02237E38 (28 B)**: Obedience Schooled zero-fills the whole Abyssal Designator block 0x02237D8C..E53, and Seal of Orichalcos takes up to 0x02237E37. This tail is all zeros and unclaimed.
- **Exit 0x021EE176** (from the miss node's `beq`) is `b 0x021EE27E`, i.e. never miss. It does not read r2.

### C1 design (proposed, not built)
Both nodes are already hooked by shipped cards, so Eva puts a **front stub** in front of each existing stub. The shipped stubs' bytes stay untouched; only the node's BL target changes.
- **GY_FRONT @0x02221328 (24 B, ov3)**, reached from node 0x021D14E2 (BL retargeted from 0x021B594A):
  `ldr r0,=0x190B ; cmp r5,r0 ; bne g ; bl 0x021D199E (any-location accept) ; g: ldr r0,=0x021B594B ; bx r0`.
  - r1 = 0x1969 is preserved for Grapha's stub.
  - r0 is dead on every exit: reject 0x021D19C0, Ojamagic 0x021D18C4 and DW 0x021D185C all reload r0 from the stack, and accept sets it.
- **MISS_FRONT @0x02237E38 (≤ 28 B, ov3)**, reached from node 0x021EE10C (BL retargeted from 0x021B58D0):
  `ldr r1,=0x190B ; cmp r3,r1 ; beq ret ; ldr r1,=0x021B58D1 ; bx r1 ; ret: bx lr`.
  - r1 is already scratch in Shadow Mist B / Overtex C. r2 stays intact for A's replay.
- **Cost**: the verify() of Grapha, Shadow Mist and Overtex checks the exact node BL. Each needs a "lifted into a registered front stub" tolerance (precedent: Shadow Mist's verify already tolerates Overtex's lift).
  - The proof is by execution: walk every cid stock vs patched through `_switch_leaf`, and run `scratch/sm_misstiming_exec`-style verdicts. Only 0x190B may change.

### DONOR CHANGED → **Aitsu 0x160A** (user, 2026-10-05), replacing Soitsu
Reason: Soitsu's chain node is Grapha's hooked node. A comparison run (scratchpad eva_cmp.py) showed every candidate shares miss node 0x021EE10C. Aitsu, Basic Insect, Water Spirit and Chamberlain all have stock chain nodes.
- **donor_scan 0x160A**: CLEAN. Its one code hit, ov3 0x02186838, is the word 0xE1A0160A, ARM code and not a cid literal.
  - Name slot 5 B, desc slots 64–152 B, so text goes through CARD_TEXT.
  - Stats: FIRE Fairy Lv5 100/100.
- **Chain terminal node 0x021D1436**: `subs r0,#0x64 ; cmp r5,r0 ; bne 0x021D143E(reject) ; b 0x021D193A`, with r0 = 0x163F, so it tests 0x15DB = Neko Mane King. That card is REAL and must keep working.
  - Its only inbound branch is `bgt 0x021D1436` from 0x021D142A, which lands at the start of the 4-byte site. Nothing targets 0x021D1438.
  - Neither node is hooked in the 2026-10-02 chain ROM.
  - 0x021D1300's prologue is `push {r4-r7,lr}`, so LR is saved and the stub's BL to the accept leaf is safe. Same reasoning as Grapha's shipped BL to DW_ARM.
- **Aitsu's miss node is 0x021EE10C** (shared, hooked), as for every candidate.

### C1 design for Aitsu (proposed, not built)
- **GY_STUB @0x02221328 (18 B, ov3)**, BL'd from 0x021D1436:
  `subs r0,#0x64 ; cmp r5,r0 ; beq ret ; adds r0,#0x2F ; cmp r5,r0 ; bne ret ; bl 0x021D199E ; ret: bx lr`.
  - 0x15DB + 0x2F = 0x160A. Neko Mane King keeps Z and so its arm.
  - No shipped card is touched.
- **MISS_FRONT @0x02237E38**: front stub as above, but testing 0x160A.
  - Shadow Mist's and Overtex's verify() need a lift tolerance.

### C2/C3/C4 facts (disassembly of stock ov3, 2026-10-05)
- **Chain machine**: it calls slot4 (+10) at 0x021D4582 (via 0x0224AE50), which sets desc[+7]. At **0x021D45B6/B8** it zeroes both [0x0229AAFC+0x7C] and [0x0229AB7C], then calls slot5 (+14) at 0x021D466E (via 0x0224AE84), which sets desc[+8].
  - So a +14 cost stub can phase on [STATE+0x7C], exactly as Ojamassimilation's cls0 COST does. Return 0 = call again, 1 = done.
- **desc[+0xC] = this card's ref**: the native "banish this card from your GY" cost 0x021E5708 does `ldrb r0,[r4,#2] ; ldrh r1,[r4,#0xC] ; bl 0x021A2510` (GY index by ref), then `bl 0x021C7104`.
  - So "other" means card ref != desc[+0xC].
- **Native add-to-hand resolver 0x02207EF4**:
  - 0x7E picker 0x0219C430(side, 6 | N+6, cid, 0x02234E78(desc)).
  - 0x7D (single pick) `bl 0x0219C510 ; bl 0x021C72CC(side, &cardword)`. The multi version wraps 0x0219C94C(i+1) per pick in CHAIN_PUSH 0x021D28A4 / POP 0x021D2964.
  - Then 0x64 shuffles 0x021D269C(side) and returns 0.
  - Messages: 0x33 before the picker, 0x15 for "none".
  - **The Deck→hand mover is 0x021C72CC(side, &cardword).**
- **Criteria word for Eva's Deck search: 0x89880022**.
  - Fairy = race 17 << 27. Anchor: Darklord Asmodeus "send 1 Fairy-Type monster" crit row word 0x88000002 (quoted in patch_accel_synchron).
  - LIGHT = 1 << 24.
  - Lv ≤ 2 = 0x00880000 (bit 23 ≤ | 2 << 18), as in Obedience Schooled's 0x58880002.
  - 0x02 monster; 0x20 "except this card" (KB fact, crit bit 5).
  - Banish-side GY word: 0x89000002.
  - The matcher 0x0223BA24 does NOT test bit 5 (it tests bits 1, 10, 13–16), so bit 5 is applied by the builder using the cid argument.

- **Timing class**: classifier 0x0224AF96 reads +0x10 raw, and 0x021E51E5 gives class 2 natively. So `+10 = 0x021E51E5` needs NO timing_class_hook arm. Once-per-turn is stamped in +14 phase 0 (at activation).
- **Phantoms** (scratchpad eva_phantoms.py; one row in stock AND chain, non-real, unclaimed in that table):
  - cls2 **0x1775** (strict-clean)
  - criteria **0x15D0** (only its c7 list entry is claimed, by another card)
  - leave-mask **0x0E4A** (only its populate row is claimed)
- **ov5 CAVE_FREE = 0x023A4250** (ov5_cave.py:2121).
- **Shared miss node**: only patch_shadow_mist checks miss node 0x021EE10C (verify line 370 and the `_apply_never_miss` idempotence). Overtex checks only blocks B/C.

### Full design (Aitsu 0x160A)
- **cls2** {0x160A, 0, RES, 0, COND, 0x021E51E5 (native You-can), COST, …} over phantom 0x1775.
- **Leave mask** {0x160A, 0x0800} over 0x0E4A, for field sends.
- **Criteria** {0x160A, 0xFFFF, HANDLER, 0x89880022} over 0x15D0.
- **HANDLER(row, side, param)**:
  - Mode 2 = DECK: `0x0223BC3C(side, cid, DPRED, excl, [sp] row word, [sp+4] 0xA)`. DPRED rejects a card with the same name as excl.
  - Mode 1 = BANISH:
    - GY builder `0x0223C4E8(side, cid, BPRED, ownref, 0x89000002, 0x10000)`. BPRED: ref != ownref.
    - Field zones 0–4: occupied, face-up, and `0x0223BA24` matcher (0x89000002), then RECORD 0x02243B2C.
- **COND**:
  - desc[+7] → pass.
  - The turn log (desc[+2], 0xB, cid, 1) must be clear.
  - COUNT(BANISH|ref) > 0 and COUNT(DECK|0) > 0.
- **COST (+14)**, phase [STATE+0x7C]:
  - Phase 0: stamp once-per-turn. M = min(2, COUNT(BANISH), distinct names). Distinct names is found greedily: COUNT(DECK|CAND[0]) > 0 means 2. If M > 1, open number picker 0x0219AE10.
  - Phase 1: N = clamp(UI+0x34); message 0x46.
  - Phase 2: picker(N+6, BANISH|ref).
  - Phase 3: CHAIN_PUSH; banish each pick through GY 0x021C7104 or field 0x021CF40C; desc+0x12 = number banished; CHAIN_POP; return 1.
- **RES (+04)**, phase [STATE+0x70]:
  - 0x80: CHAIN_PUSH, k = excl = 0.
  - 0x7F: k < N and COUNT(DECK|excl) > 0 → message 0x33.
  - 0x7E: picker(6, DECK|excl).
  - 0x7D: readback; excl = cid; k++; 0x021C72CC(side, ptr).
  - 0x64: shuffle, CHAIN_POP.
- **ov3**: GY_STUB @0x02221328 (BL from 0x021D1436); MISS_FRONT @0x02237E38 (BL from 0x021EE10C, which tail-jumps to Shadow Mist's block A).
- **Text**: card_text.CARD_TEXT[0x160A]. Stats LIGHT/Fairy/Lv1/500/200/Effect.

### BUILD 1 (2026-10-05): IN-GAME CONFIRMED BY USER 2026-10-05 (oracle items 2–10, reported as my summary items 1–9, each "Confirmed")
- Item 1 (card face / stats / text) was not on the reported list, so it is not recorded as confirmed.
- This settles both user-approved assumptions: desc[+0xC] = the ref, which keeps "other" from offering the triggering Eva, and desc +0x12/+0x14/+0x1A used as scratch in a cls2 descriptor.
- NOT SHIPPED. Waiting for the user's approval to add it to steps.STEPS.
- `_build_eva.py` on rom_all_patches.nds (sha256 69562b52...a659ef355) produced `data/over_the_nexus/working/rom_eva.nds`, **sha256 6e8af74d445fbe6a47a44a3915eb8721be3dd98c5936d96cd10eedd6f018456c**. BUILD_EXIT 0, `patch_eva.verify` 24/24 PASS.
- Ran the miss-timing test 0x021EE0E0 over cids 0..0x26FF, base vs Eva: the ONLY change is 0x160A, 1 → 0. Shadow Mist, Overtex and Sprocket stay 0.
- Chain walk (`_switch_leaf`) over all cids with every patch module imported: base and Eva both have 0 unregistered moves; Eva adds only 0x160A.
- Related verifies on rom_eva PASS with all modules imported: shadow_mist, snoww, grapha, overtex, eclipse_wyvern, obedience_schooled, seal, ojamassimilation, life_stream_dragon, that_grass.
  - Note: shadow_mist and snoww FAIL on the BASE ROM too when only a few modules are imported. Their chain walks need every registering module loaded, so that failure is an import-order artifact, not Eva's.
- Installed ov5 stubs, read back from the ROM: no pop-lr, no push-pc, and every blx literal is odd.
- Allocation guard OK: 372 ov5 slots, 402 phantom claims, 29 ov3 claims. author_facts --check: 561 PASS / 0 FAIL.
- Shipped-module edit: in patch_shadow_mist, `_miss_node_reaches_a` now accepts a front stub whose pool tail-jumps to block A. It is used by both `_apply_never_miss` and verify.

## Ruled Out
- Re-keying a phantom node in place (Shadow Mist G style) for 0x190B: its terminal node is Ojamagic 0x1946's node, which is real and already hooked by Grapha.
- Routing Eva to arm 0x021D18C4: that arm is hand-only.

## Open Questions
- (ASSUMED, user-approved) Does a sent-to-GY trigger descriptor carry the card's ref at desc[+0xC]? Oracle item 4.
- (ASSUMED) Are desc +0x12/+0x14/+0x1A free in a cls2 descriptor? Oracle items 5–7.
- Number-picker title 0xA4 says "from the Graveyard" even though field cards are banishable too. Cosmetic.
- Field LIGHT Fairy test uses matcher 0x0223BA24 with zone 0..4, so it checks PRINTED race/attribute, not modified ones.

## Next Experiment
- User in-game test of rom_eva.nds (sha256 6e8af74d...), oracle items 1–10 in `_build_eva.py`.
- If the effect is not offered or the wrong cards are offered: ask for a savestate before touching code.
