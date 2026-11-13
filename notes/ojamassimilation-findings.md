# SHIPPED 2026-10-01 (user: "Ship it")
- Whole card in-game confirmed by user 2026-10-01; Ojama Blue search confirmed by user 2026-10-01 ("I can confirm
  that Ojama Blue can search Ojamassimilation"). Item 18 (C1 banish picker unchanged) not reported.
- steps.STEPS step 85/88 (after Life Stream Dragon) + _verify_all_patches.SHIPPED. EE build 88/88, chain sha256
  e55b608fc383585b2b73d09e6811cf8756a7171161a12fe7d8ba686efef973da (byte-identical to the tested ROM); sweep
  74 passed / 0 failed. Pre-ship chain backup: scratchpad rom_all_patches_pre_oj.nds (9c2cdc4d...).

# Ojamassimilation — findings (live)

Status: C1a + C1b + C2 IN-GAME CONFIRMED BY USER 2026-10-01 (all 9 test steps = all 11 oracle items of
_build_ojamassimilation.py, on rom_ojamassimilation.nds sha256 f95bb7a2...ca28b0c; user's words "1. Confirmed
... 9. Confirmed"). That also confirms A1-A5 below. NOT SHIPPED (user 2026-10-01: record only, ship after C3).
C3 (GY effect) NOT IMPLEMENTED -- next session.
- rom_ojamassimilation.nds sha256 f95bb7a24b68cb7964eae02f477aebdccbab62db8530be01d51739831ca28b0c
  (base rom_all_patches.nds 66b01000...f49432 = shipped Qoatlus chain). BUILD_EXIT 0, verify() 5/5 PASS.
- Installed stubs disassembled from the built ROM (scratchpad stubcheck.py): every BLX literal odd, no
  pop-lr, frames balanced. Related shipped verify() on the built ROM: DEP, Qoatlus, Soul Charge, Psi,
  Brilliant Fusion, Darkflare, Lightpulsar, Misc, Remus, Tyranno, Archosaur, Gates — 12/12 PASS.
- check_allocations OK (CAVE_OJ_* 0x023A3470..0x023A3C00; phantom populate 0x0EA9; donor 0x170F).
- KB: dispatch.prisma_extra_deck_reveal_cost + dispatch.criteria_handler_param_in_r2 VERIFIED,
  card.ojamassimilation UNVERIFIED; author_facts --check 536 PASS / 0 FAIL.
- NOT in steps.STEPS (single-card ROM only until the user approves shipping).

## Scope (user-confirmed 2026-10-01)
- In scope: C1a (reveal 1 LIGHT Machine Fusion from Extra Deck) + C1b (banish any
  number of "Ojama" from hand / face-up field / GY) + C2 (SS listed materials with
  different names from hand/Deck/GY, count = N banished).
- Out of scope: C3 (GY: banish self, shuffle 3 banished Ojama, draw 1).
- Rulings chosen by user: N capped at min(distinct summonable listed materials,
  free MZ); only literal-cid recipe slots (>= 0x33) count as "specifically listed".
- Donor: Gryphon's Feather Duster 0x170F (Normal Spell) — checklist pending.

## Confirmed
- Card absent from NDS (card_name_e.bin, 4306 cards) and 3DS (CARD_Name_E.bin) —
  subagent name scan 2026-10-01. No Konami implementation exists.
- Ojama set code 0x0D: thunk slot 0x0209D0D8[0x0D] = 0x02023895
  (ldr r1,=0x0209C9E6; movs r2,#0x10), 16 cids — subagent read of arm9 2026-10-01
  (UNVERIFIED by me yet).

- **Donor 0x170F gate scan** (scratchpad donor_hits.py, 2026-10-01): u16 hits in
  DECOMPRESSED arm9 = 0 (stock + chain), ov5 = 0, ov3 = 1 = its own cls0 record
  (stock @0x022814CC, chain @0x022814B4 — shifted one record by an earlier patch).
  Record {0x170F, res 0x022137F5, f2 0x021DF06D, 0, 0, 0}. (The 4 hits in the raw
  stock arm9 are compressed-stream noise.) No per-cid gate.
  Blob length: n/a — use card_text.CARD_TEXT re-emit.

- **E-HERO Prisma 0x1D43 = native "reveal Fusion from Extra Deck + pick listed
  material"** (scratchpad tdis.py on stock images, 2026-10-01):
  - cls record @0x0227C084 {res 0x02208499, cond 0x021FD8D9, cost 0x021EB081};
    criteria row @0x0227329C {0x1D43, 0xFFFF, 0x02240551, word 0}.
  - Row handler 0x02240550(row, side, param):
    - param bit28 SET: union of every literal recipe slot (>= 0xBB8) over the whole
      Extra Deck (player+0x4E4, count player+0x18) -> DECK builder 0x0223BC3C with
      filter 0x0223C715 (cid-in-zero-terminated-list, ctx = list), [sp]=[sp+4]=2.
    - param == 0: EXTRA DECK builder 0x0223BE40(side, cid, filter 0x0224050D, 0, 2, 2).
    - param == fusion cid: list = 0x02231E8C(cid, i) for i < 0x02231E08(cid), 0-term
      -> DECK builder with filter 0x0223C715.
    - Engine's literal-cid threshold is **>= 0xBB8**, not >= 0x33.
  - Cost 0x021EB080, phase at [0x0229AAFC+0x7C]:
    0 prompt 0x0219A818(side, 0x155) | 1 picker 0x0219C430(side, 6, cid, 0) |
    2 ref = from 0x0219C510 -> desc[+0x18]; prompt 0x121 |
    3 picker(side, 6, cid, param = cid of fusion = [0x0229C33C + ref*8] & 0x3FFF) |
    4 desc[+0x14] = mat cid, desc[+0x16] = mat ref; **REVEAL = 0x021C3BC8(0x58 |
      (side ? 0x8000 : 0), zone 0xC, fusion ref, 0)** |
    5 0x021D2660 / 0x021C7654 / 0x021D2660 / 0x021D21CC(side, mat ref) |
    6 0x021D269C(side); 0x021E5060(desc, r1) return.
  - 0x021C3BC8(code, zone, ref, x) = append 8-byte UI command to 0x02299B68,
    count [0x0229A360+8] (cap 0x100). 0x58 = reveal, 0x59 / 0x55 / 0x28 = other
    Extra-Deck view commands (meaning UNVERIFIED).
  - ref -> card word: [0x0229C33C + ref*8], cid = low 14 bits.

- **Criteria row for 0x170F lands on ROW 0 for every param** (scratchpad rowres.py:
  thumbemu over stock AND chain images, 0x02243B9C executed with 0x170F re-keyed into
  row 266/261; chain path runs through criteria_row_hook BL 0x0239F6F8): params 0, 1,
  0x15B4, 0xFFFF -> leftmost row. Control Prisma 0x1D43 -> its row 658/653.
- **Handler ABI** (disasm 0x02243F38, 2026-10-01): `r0 = &row, r1 = side, r2 = param;
  blx [row+4]`. So the picker/counter param reaches the handler in r2 (Prisma's handler
  switches on it). => ONE row, mode by param, no acting-desc tricks needed.
- **Named SS resolver 0x02206F40 phases** (disasm): 0x80 cond 0x021F0384 + count
  0x02243FA8(side, cid, param) -> msg 0x11D -> 0x7F | none -> msg 0x122 -> 0x78;
  0x7F picker 0x0219C430(side, 6, cid, param) -> 0x7E; 0x7E SS
  0x02269314(side, 0x0219C510() /*picker buffer ptr*/, 1, (cid<<16)|noShuffleFlag)
  -> 0x7D; 0x7D SHUFFLE 0x021D269C(side) unless flag -> return 1; 0x78 0x0225BE7C; 0x75.
  0x02269314 = 0x0226925C with r3 = 2 (player chooses position).
- **SS engine 0x0226925C fills the ONE global summon record 0x02298A28 then
  0x02269084** — the native multi-summon resolver 0x0221B4E0 does ONE summon per
  resolver entry (0x0221B5D8 then `return 0x7E`) and loops back via 0x7F. => our
  resolver must also SS one card per entry.

- **3-zone cost banish = the native hand-SS payment machine's per-pick mover**
  (disasm 0x02262B7E..0x02262C18, KB handss.banish_payment_state_layout): word =
  *0x0219C94C(i 1-based); ref = (w>>23&0xFF)*2 + (w>>14&1);
  GY 0x021A2510(side,ref) >= 0 -> 0x021C7104(side, &word, 0);
  else hand 0x021A25A0(side,ref) >= 0 -> 0x021C6E98(side, idx);
  else field loc = 0x021A241C(ref) (>=0: side | zone<<8) -> 0x021CF40C(loc&0xFF, (loc>>8)&0xFF, 0)
  (= 0x021CDD4C(fake desc, 1<<(side*16+zone), 0xF banish, 0)). Pick count = [0x0229DD94+0x34].
- **Field slot layout** (Tyranno notes, in-game confirmed there): 0x0229ACC8 + side*0xB3C +
  zone*0x14: +0 card word, +6 position, +8 face-up flag. Recorder 0x02243B2C(side, zone, idx)
  adds a field card to the picker list (UNVERIFIED by me: Tyranno notes).
- **Number picker** 0x0219AE10(side, cid, title, item, [sp] min, [sp+4] max) -> answer at
  [0x0229DD94+0x34] next phase (Psi-Reflector, used in a RESOLVER; in a COST = unproven).
- **Criteria word** (KB dispatch.criteria_word_fully_decoded): race bits 31:27, attribute
  26:24, low bit1 = real card. LIGHT Machine = 0x39000002 (Machine 7, LIGHT 1 — LIGHT=1 per
  shipped Thunder Sea Horse / W Nebula GET_ATTRIBUTE, race ids per DEP's in-game Dinosaur 9).
- **List filter 0x0223C714** (disasm): ctx = [sp+4] -> u32 cid list, terminated by <= 0;
  match = 0x02022E98(card cid, list cid) (non-GY) / 0x021A3810(side, idx) (GY). Named
  multizone handler 0x0223E2C8 = Deck 0x0223BC3C ([sp+4]=0), GY 0x0223C4E8 (4), hand
  0x0223C16C (0), [sp] = row word, r2 = filter, r3 = ctx.
- ⚠️ reference_files/nds_card_prop.bin decoded with game_constants gives WRONG race/attr
  for known cards (Ojama Yellow -> Dragon, Cyber Dragon -> Plant) though level/ATK match.
  RAM table pointer [[0x02121A5C+0x10]+0x38] = 0 in a duel savestate; getters then go
  through ARM 0x02029C0C (thumbemu can't run it). Do NOT trust file race/attr decodes.

- **Recorder 0x02243B2C(side, zone, idx)** (disasm): words[n] = *0x0219CA28(side,zone,idx)
  into 0x02299458, locator into 0x02299908, count [0x0229944C+6]++ (cap 0x12B). PROVEN.
- **Prisma ED predicate 0x0224050C** (disasm): r0 = side, [sp+0x18] (after a 6-reg push) =
  &card word; for each recipe slot >= 0xBB8: 0x021A7BC4(side, mat) >= 0 -> 1.
  0x021A7BC4 = Deck find-by-name (player+0x304, count player+0x10, match 0x02022E98).
- **ED walker 0x0223BE40(side, cid, pred, ctx, [sp] word, [sp+4] flags)**; Prisma passes
  word 2 / flags 2 (Fusions). KB: flags 0x02 = is-Fusion 0x0202303C.
- **NDS LIGHT Machine Fusions** (cids from konami tsv; recipes from table A this session):
  XY 0x15B1 {X 0x1580, Y 0x15B0}; XYZ 0x15B4 {X, Y, Z 0x15B3}; XZ 0x15F9 {X, Z};
  YZ 0x15FA {Y, Z}; VW 0x1953 {V 0x1947, W 0x194B}; VWXYZ 0x1954 {VW 0x1953, XYZ 0x15B4};
  Cyber Twin 0x18FC {Cyber Dragon 0x18F6 x2}; Cyber End 0x18FD {0x18F6 x3};
  UFOroid Fighter 0x18FB {UFOroid 0x18F4, race code 0xF}. 0x0F08 has no recipe row.
  => max distinct literal names = 3 (XYZ) => N <= 3.
- **Ojama set list 0x0209C9E6** (16): monsters 0x1681 Green, 0x16B3 Yellow, 0x16B4 Black,
  0x17EE King, 0x1C0B Knight, 0x2048 Red, 0x2049 Blue; tokens 0x0F4B-0x0F4D; Spells/Traps
  0x166A, 0x16CF, 0x1945, 0x1946, 0x204A; 0x0EB0 phantom. Thunk 0x02023894 =
  bsearch 0x02022E14(cid, list, 0x10).
- **Dialog ids (dlg_text_e, decoded 8-bit this session):** 0x155 "Select the card(s) to
  show your opponent." | 0x046 "Select card(s) to remove from play." | 0x0A4 "Select the
  number of monsters to remove from play from the Graveyard." | 0x11B "%d" | 0x11D "Select
  monster(s) to Special Summon." | 0x122 "There is no monster that you can Special Summon."

- **Criteria phantom candidates** (scratchpad phantoms.py on the CHAIN ROM: no card_prop, 1 row,
  not in PHANTOM_CLAIMS, not in list A/B, not any row's aux, same row stock==chain):
  0x0E93, 0x0E94, 0x0E9B (position-0 list member — avoid), 0x0E9D (tribute switch arm — avoid),
  **0x0EA9** (vetted by DEP 2026-09-28 by the same checks, then un-claimed), 0x14D7 (fusion
  recipe — avoid), 0x167D (switch arm — avoid). Proposed: 0x0EA9.

## Design (built 2026-10-01; C1+C2 in-game confirmed by user 2026-10-01)
- cls0 0x170F rewritten in place: {0x170F, RES, 0, COND, COST, 0}.
- ONE criteria row {0x170F, 0xFFFF, HANDLER, 0x802} over phantom 0x0EA9; HANDLER switches on r2:
  - 0 REVEAL: ED walker 0x0223BE40(side, cid, RPRED, 0, word 0x39000002, flags 2);
    RPRED = some literal (>= 0xBB8) recipe slot found by name in own hand/Deck/GY.
  - 1 BANISH: hand 0x0223C16C + GY 0x0223C4E8 (flags 0x10000, OPRED = monster && Ojama set) +
    own face-up field zones 0..4 (Ojama monster, not token 0x0F4B-D) via recorder 0x02243B2C.
  - 0x10000|fusion|excl<<20 MAT: zero-terminated list of the recipe's distinct literal cids
    minus excluded slots -> Deck/GY/hand builders exactly as 0x0223E2C8 with filter 0x0223C715.
  - 0x20000|cid ONE: same with a one-cid list (availability count for the cap).
- COST phases [0x0229AAFC+0x7C]: 0 msg 0x155 | 1 picker(6, REVEAL) | 2 store fusion; M =
  min(#names with ONE-count > 0, #Ojama candidates, empty MZ + own field Ojamas, 3); M==1 ->
  skip; else number picker 0x0219AE10(title 0x0A4, item 0x11B, 1..M) | 3 N; msg 0x046 |
  4 picker(N+6 exact, BANISH) | 5 reveal cmd 0x58 + 3-zone banish of every pick (CHAIN bracket) |
  6 Prisma's 0x021D2660 / 0x021C7654 / 0x021D2660 -> return 1.
- RES phases [+0x70]: 0x80 open, k=0 | 0x7F k<N && may-SS && zone && MAT-count>0 -> msg 0x11D
  -> 0x7E else 0x78 | 0x7E picker(6, MAT) | 0x7D exclude picked name, k++, SS 0x02269314
  (side, pick ptr, 1, cid<<16) -> 0x7F | 0x78 shuffle 0x021D269C, close 0x021D2964, 0.

## C3 BUILT 2026-10-01 (session #2) -- IN-GAME CONFIRMED BY USER 2026-10-01 (test steps 1-5: "1. Confirmed 2. Confirmed 3. Confirmed 4. Confirmed 5. Confirmed")
- rom_ojamassimilation.nds sha256 007352d29ef59dd0280b57ba61bfc46a14db88b6c6952f52846aa89d227dedd7,
  base rom_all_patches.nds 9c2cdc4d...6aa25c (chain now incl. Life Stream Dragon, built 13:18; its module
  was edited 13:23 but LSD verify() PASSES on that chain -> not stale). BUILD_EXIT 0, verify() 8/8 PASS.
- cls2: phantom 0x1452 dropped @88, 0x170F inserted @137 (rows 89..137 shifted -0x18); no literal in
  ov3/ov5 of the built ROM points into 0x02276444..0x022768F4 (scan), so nothing hardcoded the moved rows.
- GY-action row 13 converted. Stubs from the built ROM (scratchpad stubcheck.py): every BLX literal odd, no
  pop-lr, GYSEL / GYRES disassembled and read by eye against the native tail / Pot of Avarice.
- Slots: GYCOND 0x023A3640 (0x40) + GYSEL 0x023A3680 (0x100) reuse the old handler slot; handler re-homed
  to 0x023A3C80 (0x1B0, now 0x1A0 B); GYRES 0x023A3E30 (0x100); CAVE_FREE 0x023A3F30. check_allocations OK
  (357 slots / 389 phantom claims). Claims: cls2_table 0x1452, gy_action_registry 0x1452 + 0x170F.
- Related shipped verify() on the built ROM: 20/20 PASS after lowering patch_dragunity_remus's
  sibling-family floor 4 -> 3 (same precedent as Misc 5 -> 4; Remus still PASS on the chain).
- KB: 4 new VERIFIED facts (dispatch.spell_gy_ignition_is_cls2_plus_gy_row,
  dispatch.multiselect_template_param_from_provider, dispatch.banished_list_builder,
  dispatch.pot_of_avarice_resolver_and_banished_to_deck); card.ojamassimilation updated; 609: 542 PASS 0 FAIL.
- UNPROVEN until the duel: the GY offer for a SPELL donor end-to-end (precedent only: Ritual of Grace /
  Skill Successor), flags 8 semantics (0x0219CD08) copied from Miracle Dig, desc[+6] == 0 on the GY path
  (read in 0x0224C590: memset + no +6 store) so the XOR side == desc[+2].

## Ojama archetype membership (user request 2026-10-01: "needs to be part of the ojama archetype so the
## ojama blue can search it") -- BUILT 2026-10-01 (user approved), AWAITING IN-GAME TEST
- rom_ojamassimilation.nds sha256 e55b608fc383585b2b73d09e6811cf8756a7171161a12fe7d8ba686efef973da (same base
  9c2cdc4d...); verify() 10/10 PASS (F thunk stock + list swapped/sorted); 23 related shipped verify() PASS incl.
  raiden / scrap_archfiend / wattcobra (other ARM9 set lists). Claim ojama_setcode_table 0x0EB0.
- Ojama set code 0x0D list @ARM9 0x0209C9E6 (16 u16, thunk 0x02023894: ldr list / movs r2,#0x10 / bsearch
  0x02022E15): [0x0EB0 PHANTOM, 0x0F4B-D tokens, 0x166A, 0x1681, 0x16B3, 0x16B4, 0x16CF, 0x17EE, 0x1945,
  0x1946, 0x1C0B, 0x2048, 0x2049, 0x204A] (stock arm9.bin read). 0x0EB0 is in NO other set list (thunk walk).
- Ojama Blue 0x2049 ("add 2 'Ojama' cards from your Deck") criteria row 923 {aux 0x000D, 0x0223CAF5, word
  0x0E}: 0x0223CAF4 = Deck builder 0x0223BC3C with filter 0x0223C825 and ctx = &aux; 0x0223C824 =
  tail-call has_set_code 0x020240D9(cid, [ctx] = 0x0D). => list membership is the whole gate (disasm).
- Plan: replace 0x0EB0 with 0x170F in place, re-sorted (count 16, thunk untouched) = patch_raiden's
  apply_setcode recipe. OJ helper requires IS_MONSTER, so C1b/C3 pickers can't start offering the Spell.

## Ojama list capacity (2026-10-01, thunk walk of stock arm9.bin)
- 0x0EB0 was the ONLY phantom in the Ojama list; it is now 0x170F. The other 15 are real cards / the 3 Ojama Tokens.
- The list is boxed in: set 0x09 at 0x0209C9C6..0x0209C9E6,
  Ojama 0x0D 0x0209C9E6..0x0209CA06, Dark World 0x0F starts 0x0209CA06 (no slack either side).
- Unexplained gaps between standard-thunk lists: 0x0209C9A6..0x0209C9C6 (0x20 B) and 0x0209CA8C..0x0209CAB0
  (0x24 B) -- NOT proven free (may belong to the 17 non-standard thunks). Growing the list = relocate it in
  ARM9 (thunk literal 0x0202389C + count imm 0x02023898, imm8 so <= 255) -- never to ov5 (Raiden: breaks
  the deck editor). No shipped patch has grown a set list yet; all swapped a member.

## C3 user rulings + approval (2026-10-01, session #2)
- Usable the turn the card was sent to the GY (no restriction; printed text literal).
- Resolution = Pot of Avarice model: any target no longer banished -> nothing shuffled, no draw.
- Design approved for a single-card build: cls2 record over phantom 0x1452's cls2 row + GY-action row 13
  conversion + re-homed handler with param 2 (BANISHED) + own GYCOND / GYSEL / GYRES stubs.

## C3 research (session 2026-10-01 #2) -- all by disassembly of the stock ov3 ref bin / registry dumps
- KB at session start: verify_knowledge TOTAL 605: 538 PASS 0 FAIL 67 UNVERIFIED (matches the handoff).
- **Native Spell/Trap GY ignitions exist and use cls2 + a Grapha-family GY-action row** (scratchpad
  gyreg.py + cls2dump.py): GY-registry rows 16 Phoenix Blade, 27 Indomitable GB, 34 Skill Successor (Trap),
  38 Ritual of Grace, 39 Ritual of Destruction, 44 Gem-Knight Fusion are all {zone 0x0E, 0x0224C591,
  0x0224C6C1}. Skill Successor 0x20A1 owns BOTH cls0[1086] (activation) and cls2[476] (GY effect):
  cls2 {0x02208849, 0x021DEF31, 0x02200909, COST 0x021E5709, 0x02234DC1}. Ritual of Grace cls2[496]
  {0x02208849, 0x021E0681, 0x021F0A11, COST 0x021E5709, 0x02234D8D}. => a Spell's GY effect = a cls2
  record next to its cls0 record; "banish this card from your GY" cost = 0x021E5709 (natively).
- **Free GY-action row:** on the C1/C2 ROM (rom_ojamassimilation.nds) row 13 is still the sibling-family
  phantom {0x1452, 0x0E, 0x0224C55D, 0x0224C669} (rows 11/12 went to Remus 0x106E / Misc 0x0FF2 by
  conversion, KB dispatch.gy_action_row_is_all_data_so_a_family_can_be_converted). Not in
  check_allocations gy_action_registry claims (only populate_table 0x1452 by reborn_tengu = another pool).
- **Phantom 0x1452 also owns a cls2 record** (stock cls2[89] @0x0227645C, chain cls2[88] @0x02276444,
  {0x02212621, 0, 0x021F4CBD, 0, 0}); no ("cls2_table", 0x1452) claim -> droppable for 0x170F's record.
- **Multi-select target template tail 0x02235912** (disasm): param = 0x02234E78(desc) at BOTH the count
  (0x02243FE0) and the picker (0x0219C430) call. 0x02234E78 for 0x170F hits default leaf 0x022355F0 =
  `movs r0,#0` -> param 0 = CAVE_OJ_HANDLER's REVEAL mode. **So the native template (and Soul Charge's
  prologue-stub trick) CANNOT be used for C3 as-is** -- it would offer Extra-Deck Fusions.
- **Banished builder 0x0223C52C(side, cid, pred, ctx, [sp] word, [sp+4] flags)**: zone 0xF, array
  player+0x7B4, count player+0x1C; flags bit0 = other side, bit3 -> 0x0219CD08(side,0xF,i), bit2 ->
  0x021B1E38, bit4 -> 0x02023050; pred called (side, 0xF, idx, cid) with [sp] = &card word (same ABI as
  OPRED). Wrapper 0x0223C6AC adds a both-sides pass when flags bit1.
- **Miracle Dig 0x149E** = "3 of your banished monsters": criteria row 153 {0xFFFF, 0x0223DB25, word
  0x00010002}; 0x0223DB24 = 0x0223C6AC(side, cid, 0, 0, [row+8], flags 8). Template 0x02235701,
  count code 0x09 / prompt 0x116 (KB dispatch.multiselect_target_template, measured).
- **Pot of Avarice resolver 0x0221FB94** (shared; disasm): n = desc[+0x12]; 0x80: every pick i
  (0x02234964) must be in GY 0x021A2510 else return 0; [st+0x74]=1, [st+0x78]=n, CHAIN_PUSH -> 0x7F;
  0x7F: per pick 0x022349B0(desc,i,0) -> mover 0x021C6A0C(desc, side, ref, 1) (GY->Deck), fail ->
  [0x74]=0; 0x7E: CHAIN_POP 0x021D2964 + 0x021D26CC -> 0x7D; 0x7D: if [0x74], draw (cid 0x203D arm:
  CHAIN_PUSH, 0x021D12F4(side,1), ..., CHAIN_POP; default 0x022065B8 = 0x021D12F4(side, 0x02206304(desc))).
- **Banished->Deck mover 0x021C727C(side, ref)** (disasm): 0x021A2558(side, ref) (banished index,
  player+0x7B4 / count +0x1C) < 0 -> 0; else 0x021C69D0(side, 0xF, ref, side, [sp] 0xD main / 0xC extra
  via 0x0202307C) + log 0x022391CC(0x26, 0) -> 1. It is the GY mover 0x021C6A18 minus the replacement
  check, zone 0xE -> 0xF.

## Ruled Out
- (C3) Reusing the multi-select template 0x02235700/0x02235912 or Soul Charge's prologue stub unchanged:
  param comes from 0x02234E78 = 0 for 0x170F = REVEAL mode (disasm above).

## Open Questions
- (answered) Extra-Deck reveal = UI cmd 0x58 via 0x021C3BC8, not 0x021D2598; the cost stores the
  Fusion in desc[+0x14] (cid) / desc[+0x18] (ref).
- C3 machinery: how does a Spell activate FROM THE GY (GY-action registry 0x0228DDF8 is exhausted;
  Revolution Synchron C2 added a virtual ov5 row 60 via 4 hooks)? UNRESEARCHED.

- Formerly unproven, now covered by the user's in-game confirmation 2026-10-01: A1 number picker
  0x0219AE10 inside a COST phase machine; A2 field banish 0x021CF40C from a cost stub; A3 Prisma's
  post-reveal cmds 0x59 / 0x28; A4 zone cap = empty MZ + face-up field Ojamas (bounded imprecision);
  A5 prompt text 0xA4 says "from the Graveyard"; cap dedups ADJACENT equal recipe slots only
  (true for every NDS LIGHT Machine Fusion).

## Next Experiment
- (C3) In-game test on rom_ojamassimilation.nds 007352d2...: oracle items 12-16 in _build_ojamassimilation.py
  plus regression items 2-7 (the criteria handler moved). If the GY effect is NOT offered, ask for a
  savestate before touching code (check desc path: registry row 13, cls2 lookup of 0x170F, GYCOND count).
- (old) C1a/C1b/C2 done (in-game confirmed by user 2026-10-01). Next session: C3 "You can banish this card
  from your GY, then target 3 of your banished "Ojama" monsters; shuffle them into the Deck, then draw
  1 card." Precedents to check first: GY-action registry (otn-virtual-gy-action-row: 0x0228DDF8
  exhausted, Revolution C2's ov5 row 60), banished->Deck 0x021C727C (Qoatlus PAY), draw 0x021D12F4,
  banished walker 0x0223C6AC. Then ship (steps.STEPS + SHIPPED + donor-pool note) on user approval.
