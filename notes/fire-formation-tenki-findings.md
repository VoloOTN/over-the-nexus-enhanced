# Fire Formation - Tenki — findings (live)

Printed text (scratch/ygoprodeck_cache.json): "When this card is activated: You can add 1 Level 4 or lower
Beast-Warrior monster from your Deck to your hand. All Beast-Warrior monsters you control gain 100 ATK. You can
only activate 1 "Fire Formation - Tenki" per turn." — Continuous Spell.

Clauses: C1 activation search, C2 +100 ATK to own Beast-Warriors, C3 once-per-turn activation.
Status: donor Marshmallon Glasses 0x1777. BUILD 1 (whole card) built 2026-10-19, static + offline-execution PASS.
WHOLE CARD IN-GAME CONFIRMED BY USER 2026-10-19 ("All confirmed, ship it"). SHIPPED 2026-10-19: steps.STEPS after
Sekka's Light; chain 118/118 sha256 619b8db0...c989 (byte-identical to the tested single-card ROM); sweep 99/0.
Card art added 2026-10-19 (patch_card_art CARDS, folder implemented/fire_formation_tenki): chain 118/118 sha256
7e792694...f157, sweep 99/0; 0x1777's 64x64 slot read back == the encoded PNG. Art-only delta vs the tested ROM.

## Confirmed (this session, 2026-10-19; all by static disassembly of ov3 image, NOT executed)
- 3DS cid of Tenki is 0x28B2; NDS has no 0x28B2 (donor_scan.cards(): 4305 cards) -> donor card, keep donor cid.
- Marshmallon Glasses 0x1777: ONE binding, ov3:0x021A6644 (u32 pool literal). Only reader: `ldr r4,[pc]` @0x021A6570
  (only pc-relative load of that address in ov3 0x02180000..0x02270000, raw halfword scan). Block 0x021A6570..0x021A65A4:
  r4=0x1777; 0x021AC0C8(r5=defender side, r4, -1) = count of face-up copies of 0x1777; if nonzero, 0x021AC9D0(r5, r4-7=0x1770
  Marshmallon) must hold, else every target except 0x1770 is marked unattackable via 0x021A5836. => stock effect fires only
  when 0x1777 face-up AND Marshmallon on same side. Neutralise = retarget literal @0x021A6644 to a phantom cid (count 0 -> skipped).
- S/T-card-sourced continuous ATK engine: the cid switch in ov3 ~0x021B3240..0x021B355E (function prologue push @0x021B2B7C).
  r4 = cid of the S/T-zone card, r6 = that card's side, r7 = affected monster's side (cmp r6,r7 = "monsters YOU control"),
  r5 = running ATK bonus, [sp] = affected monster record ([rec+8] = race bitmask, [rec+0xC] = attribute), [sp+4] = zone
  index (>=5 gate @0x021B3242). Banner of Courage arm @0x021B3352 (`adds r5,#0xC8` after side + turn-player + Battle Phase
  [0x0229DD14+0x34]/[+0x48]==3 tests). The A. Forces arm @0x021B3314 is the exact race-filter template
  (`ldr r0,[sp]; ldr r1,[r0,#8]; movs r0,#2; lsls r0,#14; tst` -> Warrior 1<<15).
- Race bits: game_constants.ERA2_RACE_MAP: 12 = Beast-Warrior, 15 = Warrior.
- Marshmallon 0x1777 has NO arm in that switch (cids seen: 1CE7 1429 0E2C 13F6 15A2 14CF 19B2 21DC 2098 2091 234B 234A 227A 235A).
- Dead phantom arms in that switch (no card_prop): 0xE2C arm 0x021B32E4..0x021B3300 (28 B), 0x234A (0x021B3458..), 0x234B.
- CORRECTION: donor_scan called The A. Forces 0x14CF "clean", but it has a live arm here (0x15A2-0xD3 computed constant).
  donor_scan only sees literals, not derived constants. Do NOT use The A. Forces. Treat "clean" as advisory.

## Confirmed (session 2, 2026-10-19; data reads of stock rom.nds + 3DS code_dec.bin)
- User scope: WHOLE CARD (C1+C2+C3) this session.
- 3DS main registry 0x686CBC: Tenki's only row = {0x28B2, 0xFFFF, 0x004B1BE8, 0x60900002} @0x0068C2D0.
- 3DS 0x004B1BE8 == NDS 0x0223CAD9 (Deck select): every cid that has a 0x004B1BE8 row in 3DS (~60, e.g.
  0x14D0 RotA, 0x1474 Foolish Burial, 0x15A1 Terraforming) has a 0x0223CAD9 row in NDS with the IDENTICAL word.
  RotA 0x14D0 = {0xFFFF, 0x0223CAD9, 0x78900002} (Lv<=4 Warrior) -> Tenki word 0x60900002 differs only in top byte.
- 3DS stride-0x18 continuous table: {0x28B2, 0x40B3B0, 0, 0x49C570, 0x400EF0, 0} @0x6BB690 (the +100 ATK).
- NDS cls0 (0x0227E64C, 0x51A x 24): 0x1777 has NO cls0 row. RotA [332] and Terraforming [395] =
  {resolver 0x02207EF5, 0, cond 0x021F0821, 0, 0}.
- cls0 phantom rows (cid not in card_prop) remain: 79 in rom_all_patches (e.g. 0x0E6F..0x0E73) -- claims unchecked.
- Criteria phantoms exhausted (NEXT/NSC notes) -> C1 Deck row must be a Dragon Rulers virtual criteria row.

- C2 tree path (capstone, chain ROM rom_all_patches.nds): r4=0x1777 -> 0x021B325C (<0x1CE7) -> 0x021B3266
  (>0x1429) -> 0x021B3280 vs 0x15A2: `bgt 0x021B3290` @0x021B3284 -> Shien's Dojo 0x19B2 node (cmp @3292, its BEQ
  NOP'd @3294) -> `b 0x021B355E` @3296. ⚠️ patch_shiens_dojo.verify() ASSERTS hw @0x021B3296 == 0xE162 and
  @0x021B3292 == 0x4284 -> the session-1 design (retarget the b @3296) would FAIL the Dojo sweep. NEW hook = the
  `bgt` @0x021B3284 (0xDC04) -> retarget to 0x021B32E4; arm's cid-mismatch path branches back to 0x021B3290.
- Dead arm 0x021B32E4..0x021B32FF: ONLY inbound branch in ov3 = `beq` @0x021B3274 (phantom 0xE2C); arm ends in
  `b 0x021B333C` (no fallthrough into 0x3300). 0xE2C appears in no allocation/patch file.
- Derived-0x1777 scan (arm9+ov3+ov5): pc-literal +/- imm chains within 0x200 -> 2 hits @0x021BD012/0x021BFAEA,
  both FALSE (real literal 0x1822-0x50 = 0x17D2); movs/lsls/adds constructions -> none. Only 0x1777 site =
  literal @0x021A6644 (Marshmallon block). Per-cid gate list for 0x1777 = that one site.
- All S/T stat arms exit via `b 0x021B355E`; r5 = ATK accumulator (Banner `adds r5,#0xC8`), [sp+0x34] = other stat.

- C2 OFFLINE EMU PASS (scratchpad tenki_c2_emu.py, thumbemu over chain ov3, patched): arm @0x021B32E4 (28 B)
  `172000027730844207d1be4204d100988168c90400d564352fe1c7e7` + bgt @0x021B3284 0xDC04 -> 0xDC2E. Results:
  0x1777 same-side BW +100; other side +0; Warrior-only +0; BW|Warrior +100; 0x19B2/0x1700/0x1800 +0 AND still
  pass through Dojo's node 0x021B3290. NOT executed in-game.
- Marshmallon neutralise: literal @0x021A6644 0x1777 -> 0x0E2C (phantom, no card_prop: face-up count always 0).

- C1 design facts (disasm, chain ROM):
  * Stock Continuous Spells with "When this card is activated" effects: Burning Land 0x1406 / Swords of
    Concealing Light 0x187C cls0 = {RES, +08, cond 0x0224A115 (`movs r0,#2; bx lr`), 0, 0}.
  * RotA cond 0x021F0821(desc): side = desc[2]^desc[6]; 0x021BAD70(side) gate; returns 1 iff
    0x02243FE0(side, cid, 0x02234E78(desc)) >= 1 (criteria candidate count).
  * Criteria resolver 0x02243B9C: bsearch hit returns the row index; MISS tail @0x02243F24 = `bl CAVE3_RUL_H2`
    (Dragon Rulers). Invoker row compute @0x02243F62 = `bl CAVE3_RUL_H3`: index > 0x3FFF -> row =
    CAVE_RUL_ROWS + ((idx>>8)-0x40)*0x40, handler = [row+4], resume 0x02243F70 (r0=row, r1=side, r2=param).
    Rulers' Deck search uses RES 0x02207EF5 + handler 0x0223CAD9 through exactly this path (in-game confirmed
    2026-10-16) -> a virtual row works for 0x02207EF5 / 0x021F0821.
  * Rulers' FINDK list CANNOT take 0x1777: H1/H4/H6/H7 also key on it. Rulers' verify() pins
    `bl @0x02243F24 == CAVE3_RUL_H2` -> a Tenki front at that site needs Rulers' verify to accept it.
  * Optional prompt: engine optional-trigger 0x021E50DC uses `0x0219AAAC(desc, msg, desc[+0xC])` (= 0x0219AA68
    with r3=1), msg 0xFA default / 0x149 zone 0xE / 0x148 zone 0xB; answer [0x0229DD94+0x34] != 0 = Yes.
    0x0219AAB8 = same with r3=0 (NEXT's, in-game confirmed). 0x021E51E5 ("You can" tag) is a MARKER fn only.
  * cls slot +14 = message thunk (0x02234E00: `ldr r2,=0x165; bx 0x02234CA5`), not a Yes/No.
  * cave3 free fragments >= 0x14 B: 0x021FAE30 (0x26), 0x021F1994 (0x1A), 0x021F16CC / 0x02220BCC (0x16).
  * ov5 CAVE_FREE = 0x023A72A0; ROWS = 0x023A6BF0 -> first 0x40-aligned-from-ROWS addr >= FREE = 0x023A72B0
    (k=27, virtual index 0x5B00).

- BUILD 1 (2026-10-19): `_build_fire_formation_tenki.py` -> rom_fire_formation_tenki.nds sha256
  619b8db0184a8ea80ea30adb849a747855dbd21c3442306bdc13bcac9c8cb989, on rom_all_patches.nds. verify 11/11 PASS;
  check_allocations clean; Dragon Rulers / Shien's Dojo / Sekka's Light verify PASS on it. NOT in steps.STEPS.
  Claims: cls0 phantom 0x1765; dead leaf 0x021B32E4 (phantom 0x0E2C); cave3 CAVE3_TENKI_H2 0x021FAE30 (0x14);
  ov5 CAVE_TENKI_ROW/COND/COST/RES 0x023A72B0..0x023A739F (CAVE_FREE -> 0x023A73A0).
  patch_dragon_rulers.verify edited to accept the H2 site calling CAVE3_TENKI_H2.
- OFFLINE EXECUTION on the built ROM (scratchpad tenki_built_emu.py, thumbemu, ov3+ov5+arm9 images):
  0x02243B9C(0x1777)=0x5B00, (0x14D0)=0x9D, (ruler 0x1125)=0x4300, (0x1765)=-1; invoker 0x02243F38 -> blx with
  r0=0x023A72B0 r3=0x0223CAD9; C2 +100/0/0/0 as designed; COND menu no-log = 1; RES 0x90 No -> 0, Yes -> reaches
  0x02207EF4, 0x80 empty board -> 0. Offline only at the time; whole card in-game confirmed by user 2026-10-19.

## Proposed C2 design (session 1, SUPERSEDED by the bgt hook above) (UNPROVEN until executed)
Cid 0x1777 currently falls through at `0x021B3296 b 0x021B355E` (compare chain ends vs 0x19B2). Replace that `b` with
`b 0x021B32E4` and overwrite the dead 0xE2C arm (28 B) with ~26 B:
  movs r0,#0x17; lsls r0,#8; adds r0,#0x77; cmp r4,r0; bne X; cmp r6,r7; bne X; ldr r0,[sp]; ldr r1,[r0,#8];
  lsls r1,r1,#19; bpl X; adds r5,#0x64; X: b 0x021B355E.
(`lsls #19` moves race bit 12 to bit 31.) No ov5 cave, ov3-resident (works in puzzles). Validate with
effect_verify.assert_thumb1_only and scratch/thumbemu.py before any build.

## Ruled Out
- Field-spell stat engine 0x021B26F4 as the C2 home: keyed on the FIELD-ZONE cid, Continuous Spells never reach it.
- The A. Forces as donor (live arm in S/T stat switch).

## Open Questions
- Was the whole stat tree checked for derived 0x1777 constants (second tree from 0x021B355E, other functions)? Only literals checked.
- Phantom cid for retargeting 0x021A6644 (pick unclaimed one from PHANTOM_CLAIMS).
- Does 0x021B32E4 have any other inbound branch than 0x021B3274 (phantom 0xE2C's beq)? Scan for branches into it.
- C1: Spell cls0 activation record + Deck criteria row (Lv<=4 Beast-Warrior). C3: cid turn-log OPT at activation.
- Name 22 chars vs donor name floor 13 (Korean): relies on card_text.CARD_TEXT re-emit path; untested on this cid.
- KB: nothing added to author_facts.py yet (pending, UNVERIFIED entries for the S/T stat switch and Marshmallon block).

- Unproven until in-game: phase protocol of a cls0 resolver returning a private phase (0x90) -- proven for
  cls1 (Oviraptor) and cls2 (Sekka GYRES) only; message 0xFA's text on a Spell activation; a Continuous
  Spell's cls0 path keeping the card on the field (Burning Land precedent, not executed).
- Ship-time: rename donor in patch_bulk_card_pack + patch_bulk_ydcs; move Marshmallon Glasses in
  notes/donor-pool-normal-and-effectless-fusion.md; steps.STEPS position AFTER Dragon Rulers.

## Next Experiment (superseded by BUILD 1 -> in-game oracle in _build_fire_formation_tenki.py docstring)
Run scratch/thumbemu.py on a savestate with Banner-like state, or offline: emulate the proposed 26 B block with r4=0x1777,
r6=r7, [sp] -> a record with race bit 12 set/clear, expect r5 +0x64 / unchanged; then scan for branches into 0x021B32E4.
