# NEXT (Normal Trap) — findings (live)

Status: **WHOLE CARD (C1, C2, C4, C5) IN-GAME CONFIRMED BY USER 2026-10-15 + SHIPPED.** C3 dropped by user decision.

Printed text (scratch/ygoprodeck_cache.json id 74414885, Normal Trap):
"Special Summon any number of monsters with different names from your hand and/or GY, in Defense
Position, that are all "Neo-Spacian" monsters or "Elemental HERO Neos", but negate their effects, and as
long as you control any of those Special Summoned monsters face-up, you cannot Special Summon monsters
from the Extra Deck, except Fusion Monsters. You can only activate 1 "NEXT" per turn. If you control no
cards, you can activate this card from your hand."

Clauses:
- C1 SS any number, different names, from hand and/or GY, Defense Position, Neo-Spacian or E-HERO Neos.
- C2 Negate their effects.
- C3 While you control any of them face-up: no Extra Deck SS except Fusion.
- C4 Hard once per turn (activate 1 "NEXT" per turn).
- C5 If you control no cards, activate from hand.

## Confirmed
- 2026-10-15: 3DS build does NOT ship NEXT (CARD_Name_E.bin has no UTF-16LE "\0NEXT\0") -> no Konami reference.

- 2026-10-15 user scope: **the whole card** (build/test clause by clause).
- 2026-10-15 native in-ROM precedents (cache text x scratch/cid_to_name.json; precedent ONLY, mechanisms unproven):
  - C1 multi-SS: Mustering of the Dark Scorpions 0x169E (any number from HAND, 1 copy each = different names);
    Backs to the Wall 0x1BDE (Normal Trap, as many Six Samurai w/ different names from GY);
    Telekinetic Power Well 0x1F72 (any number from GY); Doomkaiser Dragon/Assault Mode 0x1F51.
  - C2 negate: Doomkaiser Dragon/Assault Mode 0x1F51 ("Those monsters' effects are negated").
  - C4 hard OPT on a Trap: Ring of Destruction 0x138D; Spells: Instant Fusion 0x1AF5, Pot of Duality 0x2321.
  - C5 Trap from hand: Delta Crow - Anti Reverse 0x201C.
  - C3 Extra-Deck lock except Fusion: NO native precedent found by text grep. Candidate: SS gate 0x021BA258
    (Obedience Schooled C4 hook) — UNVERIFIED for this use.
- Neo-Spacian filter already proven + shipped by Neo Space Connector (notes/neo-space-connector-findings.md):
  set 0x17 list 0x0209C702 (8 cids) + Neos 0x19FD. To be re-dumped before reuse.

### Mechanism map (2026-10-15, static disassembly this session; scratchpad rec.py / cb_pick.py)
- **C1 SS loop precedent = Mustering of the Dark Scorpions resolver 0x022194F8** (cls0[469] slot1 0x022194F9):
  phases 0x80 (free zone 0x021B9ECC + any candidate -> msg 0x11E, 0x021D28A4) -> 0x7F (picker 0x0224B9F0(side,
  cid, 1, filter 0x0221943D) -> 0x7E) -> 0x7E (0x0224BBB0 picked? -> 0x7D else 0x7C end) -> 0x7D (names-used bit
  in desc[+0x14], commit 0x02269314 -> 0x7F loop) -> 0x7C (0x021D2964, stop). Phase jump table 0x02219514.
  BUT its callback picker 0x0224B9F0 (mode 8) is HAND/BOARD only: of 34 distinct callbacks passed to it, the zone
  compares seen are 0x0-0xB only (0xB = hand), never a GY code -> cannot show hand+GY together. (cb_pick.py)
- **Mixed hand+GY candidate list = list picker 0x0219C430 over the criteria candidate buffer** — Neo Space
  Connector's CAVE_NSC_CRIT calls the hand builder 0x0223C16C then the Deck builder 0x0223BC3C into one buffer, and
  hand+Deck was IN-GAME CONFIRMED (NSC C1, user 2026-10-14). GY builder = 0x0223C4E8 (flags 8). Pick readback:
  single 0x0219C510() -> &locator; multi 0x0219C94C(i) -> &locator of pick i (both index buffer 0x02299458).
  Commit 0x0226925C(side, &loc, faceUp 1, position 1 = DEF, [sp] cid<<16) is zone-agnostic (NSC hand+Deck).
- Multi-select "any number" count code = 0x47 (KB dispatch.multiselect_count_code_ranges, Soul Charge confirmed).
- Native GY multi-SS resolver 0x0221B4E0 (Power Well / Infernity Launcher / Doomkaiser): commit locator is
  HARDCODED GY (player+0x55C, literal @0x0221B6A4) and position 2 or 0 -> NOT reusable for hand+GY / DEF.
- **C2 negate = data**: KB summon.negate_is_kind2_node_plus_reader_list (VERIFIED): source cid in poster list
  0x0228F708 -> kind-2 node {key = source cid} on each summoned monster; key in reader list 0x0226FAB4 -> negated.
  The same node marks "those Special Summoned monsters" for C3 (query 0x021A1430(side, slot, donor)).
- **C3 lock seat**: Obedience Schooled's LOCK hook at `bl 0x021BA1E8` @0x021BA368 inside the SS-only gate
  0x021BA258 (r5 = cid, r7 = side; r6 = source zone per OS notes — re-check live at the seat). In-game: OS item 11
  "a non-Beast Synchro cannot be made" confirmed by user 2026-10-01 -> Synchro Summons DO pass this gate.
  The site is already fronted by OS's LOCK stub -> NEXT must pre-check and tail-call it (OS "full list" pattern).
- **C4 hard OPT**: Soul Charge / Upstart recipe — post turn-log 0x021D2584(side, cid, 1, 0) in the cls0 COST
  slot, cond queries 0x021A14E8(side, 0xB, cid, 1). (KB dispatch.activation_turn_locks) — reuse, not re-proven.
- **C5 Trap-from-hand gate = 0x021EC93C(desc, r1)**: desc[+3] == 0xB (hand) -> 0x02029E60 monster? /
  0x02022FC8 spell? else TRAP path 0x021ECA20: r4 = "may activate from hand" permission, set by grants
  (turn-log keys, Jetroid 0x18F5 battle scan) and by **Delta Crow - Anti Reverse 0x201C @0x021ECAA0**:
  `ldrh r1,[r5] ; ldr r0,=0x201C (lit 0x021ECC0C) ; cmp ; bne 0x021ECAB6 ; r0 = 0x021ACFB0(side, Blackwing
  thunk 0x02023D09) ; cmp r0,#3 ; bne ; movs r4,#1`. 0x021ECAB6: r4 == 0 -> return 0 (refused).
  => C5 = a hook over 0x021ECAA0..0x021ECAB5 that keeps Delta Crow's arm and adds donor && "controls no cards".
  Delta Crow is the ONLY in-ROM card whose text activates a Trap from hand (cache grep). Caller path of
  0x021EC93C (menu offer) NOT yet traced.

### Donor scan (2026-10-15, scratchpad trap_donors.py + donor_scan)
- In-ROM Normal Traps not in allocations.yaml/steps.py, ranked by aligned u16 cid hits in arm9+ov3 OUTSIDE the
  cls/criteria tables: 22 have 0 hits. Shortlist (all one cls0 record, no criteria row):
  - Exhausting Spell 0x162F cls0[439] {0x022184DD, 0, 0x021F6E51, 0, 0}; donor_scan: only its own cls0 record.
  - Armored Glass 0x134E cls0[221] {0x0220EA8D, 0, 0x021F3F41, 0, 0}; donor_scan: only its own cls0 record.
  - Disarmament 0x1633 cls0[442] {0x022048FD, 0x021DEBA1, 0, 0, 0}.
- base±imm switch gates NOT yet scanned for any of them (residual risk, scan before build).
- Text: NEXT desc ~480 B >> any donor blob -> must go through card_text.CARD_TEXT (index re-emit).
- Yes/No dialog primitive (for an "SS another?" loop): 0x0219A6F4(prompt id) + 0x0219A818(side, 1); answer in
  [0x0229DD94+0x34] (non-zero = yes) — KB dispatch 0x021E50DC decode. Prompt id for "Special Summon another?" unknown.

### User decisions 2026-10-15
- Donor first picked: Disarmament 0x1633 (user). REOPENED, see the blocker below.
- C1 design (user, verbatim): "The same way junk speeder does it? But with card IDs instead of levels".
  = Junk Speeder's POOLED PICKER: each prompt lists every eligible card whose cid is not used yet; picked
  cid struck; NO cancel; repeat until zones full / nothing left. DEVIATION vs printed "any number": the player
  cannot stop early. To be restated to the user for explicit acceptance.
  Junk Speeder lesson (patch_junk_speeder.py:120): ONE SUMMON PER PHASE RE-ENTRY — 0x0226925C only fills the
  global summon descriptor 0x02298A28, so N commits in one phase = 1 summon. The loop must re-enter the phase.

### BLOCKER found 2026-10-15: the list picker needs a criteria ROW for its cid argument
- 0x0219C430(side, mode, cid, param) memsets the buffers and re-counts via `bl 0x02243FA8` @0x0219C47C with the
  caller's cid/param (disasm this session); 0x02243FA8 -> row index 0x02243B9C(cid, param) -> if >= 0,
  0x02243F38 calls the row handler(row_ptr, side, param). The cid is used for NOTHING else in the picker
  (human path). No row => empty picker.
- Disarmament 0x1633 has NO criteria row; the table has no free phantom (0x14D7 went to NSC; 0x0EAD is
  claimed by assault_synchron); criteria_row_hook only offsets WITHIN a cid's existing rows.
- Fix with zero new machinery: a donor that ALREADY owns one row. In-ROM Normal Traps with 0 outside hits,
  1 cls0 record and exactly 1 criteria row (donor_scan: entangled only by their own records):
  - Return Soul 0x1B22: cls0[779] {0x022197B9, 0, 0x021FBC95, 0, 0x02235701}; crit[489] {FFFF, 0x0223F8E5, 0x00010002}
  - D - Fortune 0x1DD7: cls0[947] {0x02228E39, 0, 0x021FE321, 0x021E5319, 0}; crit[708] {0009, 0x0223CA2D, 0x2}
  - Dramatic Rescue 0x14B3: cls0[327] {0x02213B3D, 0, 0x021F519D, 0, 0}; crit[155] {FFFF, 0x0223DC39, 0x2}
  The row's handler is then overwritten with NEXT's hand+GY handler (NSC crit_stub hand+Deck half, Deck builder
  swapped for GY builder 0x0223C4E8) and its predicate strikes used cids.

### User decisions 2026-10-15 (round 2)
- **Donor = Return Soul 0x1B22** (owns criteria row 489 -> no phantom needed for the picker key).
- **C1 = pooled picker + Yes/No after each summon** ("Add a Yes/No after each") -> no deviation from "any number".

### Yes/No-per-summon native template (disasm this session)
- Giant Germ 0x1339 / Nimble Momonga 0x133A / 0x1DEE / 0x2393 share cls2 resolver 0x0220E804 ("then you can SS any
  number of X from your Deck"). Phase table add-pc base 0x0220E84C:
  0x7E (0x0220E90E): free zone 0x021AD870 + 0x02243FA8 count (per-cid caps) -> **0x0219AAB8(desc, 0x35, desc[+0xC])**
       (0x34 for the face-down cards) -> return 0x7D
  0x7D (0x0220E968): `ldr [0x0229DD94+0x34]` == 0 -> 0x64 stop; else (first pass only 0x021D28A4) find card,
       0x0226925C commit -> return 0x7E (loop; one summon per re-entry)
  0x78: if any summoned -> 0x021D269C shuffle + 0x021D2964.
  => prompt primitive = 0x0219AAB8(desc, 0x35, desc[+0xC]); answer = [0x0229DD94+0x34] != 0 = Yes.

### ov3 hosting facts (2026-10-15)
- Return Soul's native cond 0x021FBC94 (0x18 B, only cls0[0x1B22] +0C) and criteria handler 0x0223F8E4 (0x20 B,
  only crit row 489) are EXCLUSIVE (record + u32 literal + BL scan) -> dead ov3 once replaced (56 B total; fall-
  through into them NOT yet checked). Resolver 0x022197B9 is SHARED by 13 records -> not reusable.
- Working tree (user, uncommitted): Magician's Rod cave3 slots renamed NOOP_CAVE3_ROD_* = unclaimed -> ~0x1C0 B of
  cave3 runs free again (0x021F1938/0x74, 0x0221AB78/0x38+0x2C+0x2C, 0x02220B3C..0x02220BCC, 0x021FADB8..0x021FAE08).

## Architecture (PROPOSED 2026-10-15, awaiting user go)
Donor Return Soul 0x1B22 keep-cid; card_prop -> Normal Trap (already); text via card_text.CARD_TEXT.
- cls0[779] = {RES, 0, COND, COST, 0}
  - COND (+0C): turn-log 0x021A14E8(side, 0xB, 0x1B22, 1) clear (C4) AND free monster zone AND >= 1 listed cid in
    own hand/GY (direct scan, NSC cond shape with the GY array swapped in for the Deck).
  - COST (+10): post 0x021D2584(side, 0x1B22, 1, 0) once (C4, stamped at activation), return 1.
  - RES (+04): Giant Germ loop, one summon per phase re-entry:
    0x80 SS gates (0x021AD871 / 0x021B9ECD / 0x021B9ED9), clear USED mask, -> 0x7F
    0x7F picker 0x0219C430(side, 6, 0x1B22, 0) -> 0x7E
    0x7E commit 0x0226925C(side, 0x0219C510(), 1, 1 = DEF, 0x1B22<<16 ...), set USED bit of the picked cid -> 0x7D
    0x7D if free zone && count 0x02243FA8(side, 0x1B22, 0) > 0 -> Yes/No 0x0219AAB8(desc, 0x35, desc[+0xC]) -> 0x7C
         else -> 0x78
    0x7C answer [0x0229DD94+0x34] != 0 -> 0x7F else 0x78 ; 0x78 -> stop (no Deck shuffle needed).
- crit row 489 = {0x1B22, 0xFFFF, CRIT, 0x2}: hand builder 0x0223C16C + GY builder 0x0223C4E8, predicate =
  9-cid list (set 0x17 list 0x0209C702 + Neos 0x19FD) AND USED bit clear.
- C2: 0x1B22 into poster list 0x0228F708 and reader list 0x0226FAB4 via pre-check fronts (OS "full list"
  pattern at bl 0x02268090 and bl 0x021EE418), so each summoned monster carries kind-2 node {key 0x1B22}.
- C3: front OS's LOCK at bl 0x021BA368: deny if (summoned card is Extra-Deck sourced) && (not Fusion) &&
  (side controls a FACE-UP monster with kind-2 node 0x1B22 via 0x021A1430). Zone/type signals at the seat: TODO.
- C5: hook 0x021ECAA0..0x021ECAB5: keep Delta Crow's arm; add cid == 0x1B22 && side controls no cards -> r4 = 1.
- Hosting: shared-path fronts (C2 x2, C3, C5) in ov3 (cave3 Rod runs + Return Soul's dead 56 B); card-private
  RES/COND/COST/CRIT/PRED in ov5 (normal-duel default).

### Pre-build risk checklist
1. Per-cid gates on 0x1B22: donor_scan = only its own cls0 record + crit row (PROVEN). base±imm switch scan: ASSUMED clean (not run).
2. Zones: hand builder 0x0223C16C + GY builder 0x0223C4E8 in one picker = PROVEN by NSC (hand+Deck in-game, GY
   builder in-game on NSC C2). Hand+GY combination itself = ASSUMED (same buffer mechanism).
3. Blob lengths: CARD_TEXT index re-emit, no slot limit (PROVEN by shipped long-text cards).
4. OPT stamp: COST slot, at activation (Soul Charge / OS precedent, PROVEN in-game on those cards).
- C3 Synchro passes 0x021BA258: user-confirmed via OS item 11 (2026-10-01). Extra-Deck-source signal at the seat: UNPROVEN.
- C5 gate 0x021EC93C is on the menu-offer path for a hand Trap: structurally PROVEN (Delta Crow), caller chain UNPROVEN.

## Build session 2026-10-15 (user: "Go" -> build C1 first, single-card ROM)
- base±imm scan 0x1B22 (scratchpad baseimm.py: literal L within 0xFF + adds/subs on the same reg within 0x100 B;
  positive control Doitsu 0x1917 hits). 3 hits, all reviewed:
  - 0x02235794 `subs r0,#0xd7` (0x1BF9-0xD7): Return Soul's arm in the multi-select slot5 template 0x02235700 —
    unreachable once cls0[779] +14 = 0.
  - 0x021F05BE `adds r0,r0,#2` (0x1B20+2): inside 0x021F05A8 (criteria probe cond; param 2 for 0x1B20/0x1B22) —
    only reached via Return Soul's old cond 0x021FBC94, which the new record drops.
  - 0x02239776 `adds r0,#0x7a` (0x1AA8+0x7A): CPU per-cid AI switch 0x022393CC treats {Volcanic Eruption 0x1AA8,
    Return Soul 0x1B22, Metaphysical Regeneration 0x1F88} alike (End-Phase cards) -> b 0x022397D2. AI-ONLY: may
    affect when a CPU activates NEXT; no human-path effect. NOT patched (note for the user).

### BUILD 1 (2026-10-15) = C1 + C4 -- AWAITING IN-GAME TEST
- `_build_next.py` -> data/over_the_nexus/working/rom_next.nds (single-card on clean rom.nds), sha256
  c9c5d697b8a1ec1a51b83a13880f762bb477e7f18f4c24eeeda1f304f5259e79. BUILD_EXIT 0, verify() 11/11 PASS (static).
- Claims: ov5 CAVE_NEXT_DATA 0x023A5E30 (0x20) / PRED 0x023A5E50 (0x40) / CRIT 0x023A5E90 (0x50) / COND 0x023A5EE0
  (0xA0) / COST 0x023A5F80 (0x30) / RES 0x023A5FB0 (0x160); CAVE_FREE -> 0x023A6110. check_allocations --emit OK.
  In-place (no phantom): cls0[779] and criteria row 489 (both the donor's own). card_text.CARD_TEXT[0x1B22].
- Disassembly of all stubs reviewed (scratchpad next_dis.txt): every POP ends in PC, every blx literal odd,
  assert_thumb1_only clean.
- `python -m scratch.next_equiv` ALL OK (EXECUTED through thumbemu):
  - predicate: 0x4000 cids x 11 USED masks -> hits == CIDS minus the USED bits.
  - criteria: hand args == NSC hand (word 2, zone 2, filter, aux 0xE, cid, side); GY args == NSC C2 GY (0x10002, 8,
    filter, r3 0, cid, side); hand before GY.
  - cond: 10 cases (OPT only on desc[+7]==0, free zone, hand/GY hits, exclusions, side 1, decoys, desc[+6], ignores USED).
  - cost: posts (desc[+2], 0x1B22, 1, 0) unless exempt; returns 1.
  - resolver: every phase transition + USED bookkeeping (see the script).
- KB: dispatch.list_picker_needs_a_criteria_row, dispatch.ss_any_number_yesno_loop,
  dispatch.trap_from_hand_gate_delta_crow_arm (VERIFIED, static), card.next (UNVERIFIED). author_facts --check
  635 PASS / 0 FAIL.
- NOT PROVEN: the live path (that the Trap offers, that hand+GY share one picker, that prompt 0x35 reads sensibly,
  that one commit per re-entry really places each card). That is the user's in-game test.

### BUILD 2 (2026-10-15) = C1 + C2 + C4 -- AWAITING IN-GAME TEST (user testing build 1 meanwhile)
- `_build_next.py` now writes data/over_the_nexus/working/rom_next_c2.nds (build 1 rom_next.nds left untouched,
  sha still c9c5d697...), sha256 3cc16b0247703c023cade0b2d34f0894ec94d7ad1ddb86b90bea1127ef0a3305. verify() 16/16 PASS.
- C2 = KB summon.negate_is_kind2_node_plus_reader_list. Poster key [0x02298A28+0x12] is the SOURCE cid = the high
  half of our commit's [sp] (0x1B22 << 16) -- KB fact (Rescue Cat / Swing of Memories) re-read this session.
  Pre-check fronts (OS shape: key 0x1B22 -> 1, else tail-call the bl's CURRENT target):
  - bl @0x021EE418 (reader list 0x0226FAB4, n 0x23) -> NEGR 0x021FBC94 (Return Soul's dead cond, 0x18 B, exact fit)
  - bl @0x02268090 (poster list 0x0228F708, n 0x24) -> EPL 0x0223F8E4 (Return Soul's dead criteria handler, 0x20 B)
  Stock tail = bsearch 0x02022E14; chain tail = Obedience Schooled's NEGR 0x02237D8C / EPL 0x02237DA4.
  Hosts: no bl, no other u32, no b/bcc into either body, both preceded by pop{..pc} (scan this session); stock sha
  asserted before writing. Ledger: OV3_DEAD_BLOCKS + OV3_CLAIMS + PHANTOM_CLAIMS donor_cid 0x1B22; --emit OK.
- `python -m scratch.next_c2_equiv` ALL OK (EXECUTED): for every key 0..0x3FFF, new == old + {0x1B22}, on the
  BUILT ROM (old = stock bsearch; 35 / 36 old hits) AND on rom_all_patches.nds + apply_c2 (old = OS fronts;
  37 / 38 old hits). So no other card's negate / kind-2 membership changes.
- KB card.next updated; author_facts --check 635 PASS / 0 FAIL.
- NOT PROVEN: in-game that a NEXT-summoned monster is negated (oracle items 8-9 in _build_next.py).

### User decision 2026-10-15: C3 DROPPED as an accepted deviation
- User, verbatim: "dont bother with the "fusion summon-only" text. We will skip it as a deviation, focus on the
  activate from hand". So the Extra-Deck lock (C3) is NOT implemented, by user decision. Next = C5.

### BUILD 3 (2026-10-15) = C1 + C2 + C4 + C5 -- AWAITING IN-GAME TEST
- `_build_next.py` -> step 0 (patch_ov3_compact) fresh from rom.nds into _next_stage.nds, then patch_next ->
  data/over_the_nexus/working/rom_next_c5.nds, sha256 10181b10d783cdca6545c4448b5f191ea94bc51a1099f2a5ba07e209acf84c95.
  verify() 17/17 PASS + step0.verify OK. Builds 1/2 untouched.
- "You control no cards" = Gorz 0x199E's cls2 cond 0x021FA264 -> 0x021ACF28(side): counts zones 0..0xA (monster,
  S/T, Field) whose word [player+0x34+z*0x14] has a cid and [+0x44] bit 21 clear (disasm this session).
- C5 site 0x021ECAA0 (stock 22 B = Delta Crow arm `29885a48...0124`) -> `bl CAVE3_NEXT_HANDGATE ; adds r4,r0,#0 ;
  b 0x021ECAB6`; front 60 B @0x0221AB78 (cave3 run 0x0221AB78..0x0221AC20, freed by the user's Rod NOOP rename) =
  Delta Crow arm verbatim + (cid 0x1B22 && 0x021ACF28(desc[+2]) == 0 -> 1). No b/bcc anywhere lands in the dead
  site bytes 0x021ECAA2..0x021ECAB5 (scan). r0-r3 are dead at the join (0x021ECAB6 reloads).
- `python -m scratch.next_c5_equiv` OK (EXECUTED on real ov3 + ARM9): 180 cases (9 boards x 5 cids x 2 sides x
  r4 0/1): new r4 == stock r4 | (0x1B22 && own side holds no card); 11 NEXT grants; Delta Crow's arm fires exactly
  for 3 face-up Blackwings (2 cases), unchanged. Board model needs the face-up halfword [+0x3C] = 1 for the
  Blackwing count (0x021ACFE8 with r3 = 1 skips face-down) -- first run without it never fired the crow arm.
- Ledger: cave3.CAVE3_NEXT_HANDGATE (0x40); check_allocations --emit OK.
- NOT PROVEN in-game: that 0x021EC93C is the menu path that offers a hand Trap (only Delta Crow's arm living there
  says so), and NEXT's resolution from a hand activation.

## IN-GAME CONFIRMED BY USER 2026-10-15 -- user, verbatim: "All the in-game tests passed"
- Read as: the _build_next.py oracle items (C1+C4 1-7, C2 8-9, C5 11-15). ROM (user, verbatim: "rom_next_c5 is
  what i tested on") = rom_next_c5.nds sha256 10181b10...4c95. Item 10 (chain regression of Level Modulation / Fire Ant / OS / Petiteranodon) was marked "later"
  -- not separately confirmed.

## SHIPPED 2026-10-15 (user, verbatim: "Perfect, Ship it!")
- steps.STEPS: Step("NEXT", "patch_next") right after Neo Space Connector (after Obedience Schooled, whose NEGR/EPL
  the C2 fronts tail-call). _verify_all_patches.SHIPPED += patch_next. patch_bulk_card_pack key "Return Soul" ->
  "NEXT" (pack 52 kept; the vanilla+ unobtainable step skips names it can't find, the full step runs after NEXT).
- Pre-build copy: rom_all_patches.pre_next.nds. EE build: 114/114 steps, BUILD_EXIT 0, step 103 = NEXT,
  rom_all_patches.nds 129694344 B sha256 24d63641282872562232f8d6096f0191c1251980c4d7c43c89a1eb16f251a826.
- Sweep 1: 92 passed / 3 failed = patch_petiteranodon, patch_elder_entity_norden, patch_obedience_schooled -- all
  exact-target asserts at the two list-search bls NEXT now fronts. Fix (verify-only, no ROM bytes):
  effect_verify.bl_reaches now follows a CHAIN of exact-shape pre-checks (<= 8); OS verify uses it for its HOOKS.
  Checked: on the new chain reader site reaches NEXT/OS/Norden stubs, poster site reaches NEXT/OS; wrong-stub
  controls False; the pre_next ROM gives the same answers as before.
- Sweep 2 on the shipped chain: **95 passed, 0 failed, 0 without verify()**. Control on rom_all_patches.pre_next.nds:
  94 passed, 1 failed = patch_next only (not in that ROM) -> the bl_reaches change regresses nothing.

## Next Experiment
- C5: user runs oracle items 11-15 on rom_next_c5.nds (it also carries C1/C2/C4).
- C2: user runs oracle items 8-9 on rom_next_c2.nds.
- User runs the C1+C4 oracle in `_build_next.py`'s docstring on rom_next.nds (normal duel, not the puzzle editor).
- On a failure: ask for a savestate at the failing step; replay RES/CRIT offline with scratch/thumbemu on it.
- After C1+C4 confirm: C2 (poster 0x0228F708 + reader 0x0226FAB4 fronts, ov3), then C3, then C5.

## Ruled Out
- Callback picker 0x0224B9F0 (Mustering) for C1: hand/board zones only, no GY (cb_pick.py zone compares).
- Native resolver 0x0221B4E0 for C1: GY-only commit locator, no DEF position.

## Open Questions
- Which clause is in scope first (awaiting user).
- Donor: needs a Trap donor (not a Normal Monster) — candidate search pending.

## Next Experiment
- After scope confirmation: grep shipped patches + ov3 for a native "SS from hand and/or GY, any number"
  precedent; pick a Trap donor; run the donor checklist.
