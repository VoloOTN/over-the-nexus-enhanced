# Ultimate Conductor Tyranno — findings (started 2026-09-28)

Donor: **Sengenjin 0x1265** (user-chosen 2026-09-28). All four clauses in scope (user override).
Not in the 3DS build (user-confirmed) — NDS precedent only.
Plan: `~\.claude\plans\ultimate-conductor-tyranno-compiled-pnueli.md`.

Text (ygoprodeck 18940556, Lv10 LIGHT Dinosaur 3500/3200):
- C1 Nomi; SS from hand by banishing 2 Dinosaurs from GY.
- C2 OPT, either player's Main Phase: destroy 1 monster in hand/field; if you do, all opp face-up -> face-down DEF.
- C3 Can attack all opp monsters, once each.
- C4 Start of Damage Step vs a DEF-position monster: you can inflict 1000; if you do, send it to GY.

## User decisions (2026-09-28)
- C3: ov5/ov3 hook on the lookup, no real card dropped from list 0x0226D6E4.
- C2 picker: TWO-STEP (Hand/Field prompt, then the normal picker for that zone).
- Build order: first test ROM = C1+C3+C4; C2 comes in a second ROM.

## Build state (2026-09-28): C1+C3+C4 BUILT, AWAITING IN-GAME TEST
- Module otn_enhanced/cards/ultimate_conductor_tyranno.py; script
  _build_ultimate_conductor_tyranno.py (base rom_all_patches.nds sha256 9b82f8a1...ca7e).
- Output rom_ultimate_conductor_tyranno.nds sha256 ccc3369c65f126b6e5010cea2e3fbfa568c2307ff24cd893b7c02520b3ebd697,
  verify() 21/21 PASS. check_allocations [OK].
- Claims: ov5 CAVE_UCT_SSCOND 0x023A2480 (0x40), CAVE_UCT_RES 0x023A24C0 (0xB0), CAVE_FREE -> 0x023A2570;
  ov3 0x022234C0 (64 B); phantoms 0x1758 (criteria / registry / nomi class 2), cls1 0x0E54.
- All 4 stubs disassembled after assembly: Thumb-1 only, every blx literal odd, no POP-LR, no imm3 ADD.
- No b/bcc in ov3 targets 0x02262962/0x02262964 (scanned), so the `bx r1` rewrite has no side entry.
- thumb_asm.py gained the 2-operand register-shift form (`lsls Rd, Rs` 0x4080 / lsrs 0x40C0 / asrs 0x4100).
  Additive: that form used to raise IndexError, so no existing stub's bytes change.
- C4 deviation-free design, but NOTE: 0x021D28A4 / 0x021D2964 get r1 = the phase (0x80 / 0x7E), exactly as
  Zephyros passes them.

## Build state 2 (2026-09-28): ALL FOUR CLAUSES BUILT, AWAITING IN-GAME TEST
- rom_ultimate_conductor_tyranno_c2.nds sha256 94e77c654839e851f62eb0b49e280d1dff436466f6ed42f3919c0897e0fd6b4a,
  verify() 28/28 PASS, check_allocations [OK]. First ROM (C1+C3+C4) still ccc3369c...d697, untouched.
- C2 adds: cls3 over 0x0E46 (Junk Defender shape), speed-2 0x1529 -> 0x1265, ov5 CAVE_UCT_C2COND 0x023A2570
  (0x30), C2HELP 0x023A25A0 (0xA0), C2RES 0x023A2640 (0x220); CAVE_FREE -> 0x023A2860.
- ASSUMED, not proven offline (the in-game test decides):
  (a) a hand-built picker list (header + recorder, no 0x02243FA8) drives UI 0x0219C99C correctly;
  (b) 0x021CF374 (field) / 0x021D2478 (hand) have finished destroying by the next resolver phase (the
      "if you do" check reads the slot / hand count one phase later);
  (c) desc[+0x18/+0x1A/+0x1C] are free on a cls3 resolution descriptor;
  (d) speed-2 membership does not change C4's cls1 trigger behaviour (compare against the first ROM);
  (e) CPU side (ctrl 1/4) auto-picks candidate 0 with no UI; the prompt's CPU behaviour is unknown.

## Confirmed
- **Donor 0x1265 has no per-cid gates** (2026-09-28): `donor_scan 0x1265` -> CLEAN (no ov3/arm9
  data structure names it); its lone code hit arm9:0x02042448 disassembles (ARM) as
  `00506512 rsbne r5,r5,#0` — an instruction, not a cid. ov5 (0x022C5900, 870432 B) has zero
  aligned u16 0x1265. Name slot e=9 B, desc e=52 B -> text must go through card_text.CARD_TEXT.
- **C1 template = Doom Dozer 0x19CA** (nomi, "banish 2 Insect from GY", own race). Payment
  dispatch 1 (root 0x02262962, disassembled from reference ov3 this session) sends cids
  {0x1466 Necrofear, 0x18B4 Megarock, 0x19CA Doom Dozer, 0x1D86 Gaia Plate, 0x1D91 Aztekipede,
  0x234F} to arm 0x02262A52: `bl 0x0202ABB8; adds r5,r0,#0; b 0x02262AB6` (r6 left 0).
  The default arm 0x02262AAE instead does `bl 0x0202ABC8; r5=r0; r6=1`. Reading: r5 = filter
  value from the summoned card itself (race for the 0x0202ABB8 arm, attribute for the default),
  i.e. "banish N of THIS card's race". Once the donor's race is Dinosaur, the Necrofear arm filters
  Dinosaurs with no new filter code. (Inference from the Necrofear/Doom Dozer printed text;
  0x0202ABB8 = race getter still to be confirmed by disasm.)
- 0x0225CF5E (count branch for cids < 0x1466) was retargeted to return 1 by Lightpulsar
  (patch_darkflare docstring), and the donor 0x1265 takes that branch. So count=2 cannot be a
  branch retarget; it needs a per-cid arm.

- **Count function 0x0225CF28** (reference ov3 disasm): Doom Dozer 0x19CA -> 0x0225D066
  `movs r0,#2`. Donor 0x1265 path: ... `ldr r1,=0x1466; cmp; bgt; bne 0x0225CF5E` -> the branch
  Lightpulsar retargeted to return 1. The entry `ldr r2,[pc,#0x174]` is the ONLY ov3 reference to
  literal 0x0225D0A0 (=0x1C2B), scanned this session. 6 callers: 0x0225D0D8, 0x0225F678,
  0x0225FA7C, 0x0225FA9C, 0x0226295A, 0x02264814.
- **0x0225D0D0(r0=side, r1=cid)** = single-row cost legality: count=0x0225CF28(cid);
  0x021B9ECC(side) and 0x021AD870(side) must be nonzero; n=0x02243FE0(side,cid,0 [or 1<<28 for
  0x234F]); return n>=count. This is what the hand-SS condition stub can call directly.
- **Payment dispatch 2** (root 0x02262C24): 0x19CA and 0x1265 both reach 0x02262CA4 (single-pass
  completion). No dispatch-2 edit needed.
- **Doom Dozer rows**: criteria[413] {0x19CA,0xFFFF,0x0223CA11,0x50000002} (race 10 Insect <<27);
  registry[58] {0x19CA -> 0x0226292D}. Donor gets {0x1265,0xFFFF,0x0223CA11,0x48000002}
  (Dinosaur = race 9 per game_constants.py:440).
- **Nomi: Doom Dozer is in class-2 list 0x0209BE9C** (57, literal 0x0202321C, count imm
  0x020231E0), not class 1. Class-2 phantoms: 0x0E63 0x0EB3 0x1758 0x176C 0x18B9.
- **Phantom 0x1758** has no card_prop and is unclaimed in PHANTOM_CLAIMS. It is in class-2, the
  registry (-> 0x02261F8D, "no procedure") and criteria (1 row {0xFFFF,0x0223CB65,0x01000002}),
  and all of these are still present in rom_all_patches.nds (2026-09-28 15:55) -> drop it in all 3.
- **The ov3 host for the per-cid stubs:** block 0x02223450 (180 B) holds
  dark_law 0x02223450+0x40 and norden 0x02223490+48, so **0x022234C0..0x02223504 (68 B) is free**.
  The handss cave 0x0225F240 is full (banish 104 + NAST 20 of 126).

### C1 design (derived; not built yet)
1. Hand-SS: register_tg_handss(0x1265, ov5 cond `push{lr}; ldr r1,=0x1265; bl 0x0225D0D0; pop{pc}`).
2. Count: repoint literal 0x0225D0A0 at an ov3 stub and turn 0x0225CF2A `cmp r0,r2` into `bx r2`.
   The stub returns 2 when r0==0x1265; otherwise it replays `ldr r2,=0x1C2B; cmp r0,r2` and does
   pop{pc} back to 0x0225CF2D. ov3, so puzzles keep working.
3. Pay1: same trick at root 0x02262962 (literal 0x1C81). 0x1265 goes to Necrofear's race arm
   0x02262A53; everything else replays the displaced instructions and returns to 0x02262967.
4. Criteria row, registry row {0x1265 -> 0x0226292D}, class-2 entry, all dropping 0x1758.

### C3 (partial RE, 2026-09-28)
- Attack-all membership thunk **0x021A3FE0**: `ldr r1,=0x0226D6E4; ldr r3,=0x02022E15; movs r2,#0xA;
  bx r3` (reference ov3 disasm). Its 5 BL callers: 0x021A0016, 0x021A0458, 0x021BBE3C,
  0x021BC318, 0x021C61BE.
- 3 more inline bsearches of the same list: 0x021A424C (pool 0x021A4358), 0x021A58CC (pool
  0x021A5AF0), 0x021A67A8 (pool 0x021A696C). Each pool is referenced ONLY by its own site.
- **No per-cid refinement blocks the donor** (disasm of all 8 sites this session). The thunk callers
  0x021BBE3C and 0x021C61BE, plus the inline sites 0x021A58CC and 0x021A67A8, go on to
  0x021A1584(side,zone,0x1505), with Asura Priest's cid as a SHARED node key for every member.
  0x021A424C special-cases only 0x1A4E / 0x1A79 / 0x1AB3 (Chimeratech, U. Tyranno, Stealth Union).
  Any other member takes the default b 0x021A42F0.
  No caller dereferences the bsearch result; all of them do `cmp r0,#0`.
- Literal 0x021A3FEC (=0x02022E15) is read only by the thunk's `ldr r3` @0x021A3FE2.
  The literal 0x02022E15 also appears at 0x021AABC4, in an unrelated function.
- None of the C3 sites differ from stock in rom_all_patches.nds.

### C3 design
One ov3 stub AT = `ldr r3,=0x1265; cmp r0,r3; beq y; ldr r3,=0x02022E15; bx r3; y: movs r0,#1; bx lr`
(it clobbers only r3, which the bsearch clobbers anyway). Point the thunk literal 0x021A3FEC at AT|1,
and retarget the 3 inline `bl 0x02022E14` (0x021A4252, 0x021A58D0, 0x021A67AC) to AT. ov3 because
battle code runs in puzzles.

### C4 (RE done 2026-09-28, reference ov3 disasm)
- cls1 rows on resolver 0x02215109 (layout {u16 cid, u16 0, +04 res, +08 0, +0C cond, +10 tag, +14 0}):
  1524, 15E0, 17D7, 17D8, 17DF (cond 0x021F842D), 1963, 19C2, 1B38, 1ECB, 1FAF, 2043 and 246B.
  2043 Velphito and 246B Wattmole use +10 = 0x021E51E5 (optional "You can").
- donor_scan 0x17DF (Ninja Grandmaster Sasuke): its ONLY binding occurrence is cls1[412]. So the
  Start-of-Damage-Step event reaches an attacker's cls1 row with no list membership (structural
  proof from a native card).
- Cond 0x021F842D: returns 0 if ctx 0x02298AD8[+2] != 0 (direct attack); otherwise side=[+1]&1,
  zone=[+0xA]; the card id at 0x0229ACD0 + side*0xB3C + zone*0x14 must be nonzero, and the u16 at
  0x0229ACCE + same offset must be nonzero (read as the Defense-position flag). There is NO
  attacker==self test, so the dispatcher delivers only the attacker's rows.
- Resolver 0x02215109 is single-shot: returns 0 if ctx[+5] != 0; otherwise if
  0x02196928(side,zone) != 0, it calls destroy 0x021CF374(desc,side,zone).
- **Send to GY by effect** = 0x021CDD4C(desc, 1<<(side*16+zone), 0xE, 0x1000). 0x021CF658 does
  exactly this with a synthetic desc; destroy 0x021CF374 is the same call with kind 2. The mask is
  generic, so a non-self target is fine.
- **Phase protocol** (Zephyros 0x02230EBC, disasm): phase=[0x0229AAFC+0x70]. 0x80: bl 0x021D28A4
  (r0=desc, r1 as received), act, return 0x7F (continue) or 0x7E; 0x7F: damage
  0x021CFBC8(desc,side,amt), return 0x7E; 0x7E: bl 0x021D2964, return 0; anything else returns 0.
- Bonus for C2: 0x0221513D is a phased flip-face-down resolver. 0x80: 0x021C5894(desc?,[r2+2],
  [r2+3]); nonzero -> 0x7F; 0x7F: 0x021C4C88(...) -> 0x7E. Still to be decoded.

### C2 (RE, 2026-09-28)
- No native card destroys "1 monster in your hand or field" and none selects across hand+field,
  except the Ritual tribute picker. Scanned: every card_prop name x ygoprodeck desc matching
  destroy/tribute/send ... "hand or field".
- **A hand-destroy primitive exists:** 0x021D2478(r0=side, r1=hand idx, r2=slot locator,
  r3=source cid, [sp]=flag) is a thin wrapper of 0x021D2314(side, zone 0xB, idx, loc, [sp]=cid,
  [sp+4]=flag). Zone 0xB = HAND (KB effect_dispatch_tables.yaml:2024: all hand->GY movers resolve
  the slot via 0x0219CA28(side,0x0B,idx)).
  Native callers: Chain Destruction 0x12CD's resolver 0x0220CBB4 @0x0220CC52 (loc =
  0x0219CA28(side,0xB,idx), r3 = desc[+0] cid, [sp] = side != desc[+2]); Crush Card Virus family
  resolver 0x0220BA04 @0x0220BB7E.
- Sibling wrappers: 0x021D2490 (zone 0xD), 0x021D24B4 (zone 0xC). Both resolve their own locator.
- Field destroy: 0x021CF374(desc, side, zone) = 0x021CDD4C(desc, 1<<(side*16+zone), 0xE, 2).
- Flip face-down: see the 0x0221513D bonus below.

### C2 RE, part 2 (2026-09-28, reference ov3 disasm)
- **Template = Junk Defender 0x23FF** ("once per turn, during either player's turn", untargeted):
  cls3 {0x23FF, 0, 0x02208499, 0, 0x021F01C1, 0x021E5061, 0} + a speed-2 list 0x0209C118 member.
  Junk Gardna 0x2355 and Mist Valley Thunder Lord 0x1FB9 have the same +0C/+10.
  0x021F01C1 = per-copy OPT latch: 0x021A1430(desc[2], desc[3], 0x0FB6) == 0 -> 1. The cost
  0x021E5061 stamps it.
- Main Phase = [0x0229DD14+0x48] in {2,4} (Apophis cond 0x021F4EC0).
- **Picker internals**: 0x0219C430(side, code, cid, param) stores [0x0229DD94+0x30]=side and
  [+0x2C]=code+0xF. If [0x0229911C+side*4]==1 and code>=5 it calls the AI chooser 0x0226AD50 and
  returns. Otherwise it writes header 0x0229944C {u16 side, u16 code, u16 pick=0, s16 count @+6},
  clears the words 0x02299458 (0x4B0 B) and locators 0x02299908, fills them with
  0x02243FA8(side,cid,param), and unless (code>=5 and ctrl==4) opens the UI
  0x0219C99C(0x37, side, code, 0). Readback 0x0219C510 = &words[pick].
- Recorder 0x02243B2C(side, zone, idx): words[n] = *0x0219CA28(side,zone,idx); locator[n] =
  side | zone<<1 (no index); count++. **Field zones are recorded natively** with idx 0: e.g. the
  Virus-family walker @0x0223E0F8 loops side 0..1 x zone 0..0xA. So the picker UI shows field cards.
- Book of Eclipse 0x1E48 resolver 0x0222958C (mass flip face-down):
  - 0x80: 0x021D28A4; [0x0229AAFC+0x74]=0; for side, zone 0..0xA: if 0x0224A924(desc,side,zone),
    call 0x021C4F24(desc,side,zone,1) and do [+0x74]++; return 0x7F.
  - 0x7F: draw 0x021D12F4 (its own clause) + close 0x021D2964, return 0.
- Own side = desc[2] ^ desc[6] (Oviraptor C2).
- is-monster(cid) = 0x02029E60. Hand count = [0x0229ACA0 + side*0xB3C]. Hand slot =
  0x0219CA28(side, 0xB, i).
- Dialog ids (dlg_text_e): 0x103 "Use which effect?", 0x192 "Hands", 0x23C "Field",
  0x6D "Select the monster(s) to destroy."
- Spare phantoms (checked against rom_all_patches.nds + PHANTOM_CLAIMS): cls3 0x0E46; speed-2 0x1529
  (the ONLY unclaimed speed-2 phantom left).

### C2 design (two-step, user's choice)
cls3 {0x1265, 0, RES2|1, 0, COND2|1, 0x021E5061, 0} over 0x0E46; speed-2 list 0x1529 -> 0x1265.
COND2 = (desc[+7] != 0 or phase in {2,4}), then tail-call 0x021F01C1.
RES2 phases:
- 0x80: open; if hand AND field both have monsters -> prompt(desc,0x103,0x192,0x23C,0,0,3), 0x90;
  otherwise set desc[+0x18] and go 0x91.
- 0x90: desc[+0x18] = [0x0229DD94+0x34], then 0x91.
- 0x91: MESSAGE(side, 0x6D), then 0x92.
- 0x92: build the candidate list myself (header + recorder), then UI 0x0219C99C (or pick 0 for
  ctrl 1/4), then 0x93.
- 0x93: destroy the pick. Field: 0x021CF374(desc,side,zone). Hand: find i with slot word == picked
  word, then 0x021D2478(side,i,slot,cid,[sp]=0). Then 0x94.
- 0x94: if the card is gone, Book of Eclipse's loop on the opponent side only; then 0x7E.
- 0x7E: close, return 0.

### C4 design
cls1 {0x1265, 0, RES4|1, 0, 0x021F842D, 0x021E51E5, 0} over an unclaimed cls1 phantom.
RES4 (ov5):
- 0x80: bl 0x021D28A4; if ctx[+5] != 0 or 0x02196928(defSide,defZone) == 0, return 0x7E;
  otherwise 0x021CFBC8(desc, defSide, 1000) and return 0x7F.
- 0x7F: if the defender is still present, 0x021CDD4C(desc, 1<<(defSide*16+defZone), 0xE, 0x1000);
  return 0x7E.
- 0x7E: bl 0x021D2964, return 0.

### C1 design REVISED (the count-entry hook is dropped to save ov3 space)
- The other count callers are off Tyranno's path: 0x0225F678 = another card's leaf (gated on
  0x021B1734 == 3), 0x02264814 = a DARK-prompt message routine.
- Legality: the ov5 cond stub reimplements 0x0225D0D0 with count 2: 0x021B9ECC(side) != 0,
  0x021AD870(side) != 0, 0x02243FE0(side,0x1265,0) >= 2.
- Payment: the pay1 root stub, for 0x1265, sets **r7=2** (r7 = count, computed at 0x0226295E) and
  jumps to 0x02262A53. Other cids replay `ldr r1,=0x1C81; cmp r0,r1` and pop{pc} to 0x02262967
  (r2 is scratch, verified dead).
- ov3 budget: pay1 stub ~22 B + AT 14 B + shared pool of 5 literals 20 B = ~56 B of the free 68 B
  at 0x022234C0.

## In-game results (user, 2026-09-28, first ROM ccc3369c...d697)
Verbatim: "1. Confirmed 2. Confirmed 3. Confirmed 4. Confirmed 5. Confirmed 6. Confirmed 7. No (no prompt)".
So C1 and C3 are in-game confirmed by the user 2026-09-28 (checks 1-6: text/stats, no NS/Set, banish exactly
2 GY Dinosaurs, Doom Dozer / Necrofear / Chaos Sorcerer / Lightpulsar regression, attacks each opp monster
once, other attack-all cards regression). C4 FAILED: attacking a DEF monster gives no prompt.
Double Evolution Pill (user): "Tyranno was missing from the list when it should have appeared".

### C4 ROOT CAUSE (proven by disassembly 2026-09-28)
- Start-of-Damage-Step poster: after its guards (ctx[+5]==0, defender slot [0x0229ACD0+...] non-empty),
  0x0224F588..0x0224F666 is a hard-coded BST over the ATTACKER cid r4. A hit reaches 0x0224F668, which
  requires ctx[+2]==0 (not direct) and then calls 0x021D3230(ip = side, r1, 0x15, [sp+0xC]), i.e. posts
  event 0x15. The default leaf 0x0224F67A posts nothing.
- Members decoded from the tree: 0x1524 Sasuke Samurai, 0x15E0 Paladin of White Dragon, 0x17D7/0x17D8
  Mystic Swordsman LV2/LV4, 0x17DF Ninja Grandmaster Sasuke, 0x1829, 0x1823, 0x1963, 0x19C2, 0x1A72,
  0x1B38, 0x1C2C, 0x1D80, 0x1ECB, 0x1FAF, 0x2000, 0x2043 Velphito, 0x21C5, 0x226D, 0x246B Wattmole,
  0x24DD, 0x24E4 (literal pool 0x0224F728..; relative arms decoded by hand).
- 0x1265 is not in it, so no event 0x15 is posted and the cls1 row is never offered. donor_scan missed this
  because the tree encodes most cids as base+/-imm, the thumb.stack_based_switch blind spot.
- Hook site candidate: 0x0224F588 `ldr r3,[pc] (=0x1C2C, literal 0x0224F730, read ONLY here) ; cmp r4,r3`.
  Same literal trick as PAY1: the literal becomes the stub, and `cmp` becomes `bx r3`. The stub sends
  0x1265 to 0x0224F669; everything else replays and returns to 0x0224F58D. r0 is dead there (r0 is
  rewritten on every path before it is read).
- **BLOCKER: this runs for every attack, in puzzles too, so the stub must be ov3 (~40 B).** The ov3 dead
  pool has only 22 B free, fragmented (0x022234C0 block: 4 B left). Needs more ov3 dead space, or a
  user decision.

### C4 fix host FOUND (2026-09-28)
- 0x021F065C..0x021F069B (64 B incl. the literal 0x0FB6 @0x021F0698) is phantom cls3 0x0E46's private +0C
  cond (OPT latch + 0x02204D08). The previous function ends at 0x021F065A (pop pc), so nothing falls
  through into it. Scanned stock ov3, rom_all_patches.nds and the _c2 ROM (ov3 + ov5, u32 + BL):
  - its ONLY reference is 0x0E46's cls3 record (0x02279EA0 in the chain ROM);
  - after Tyranno's J insert there are ZERO pointers and ZERO BLs, and the body is still stock.
  So it is dead, puzzle-resident ov3 space, valid only together with J (same module).
- Plan M: literal 0x0224F730 (=0x1C2C, read only by 0x0224F588) -> M|1, 0x0224F58A `cmp r4,r3` -> `bx r3`.
  M: 0x1265 goes to 0x0224F669 (post event 0x15); otherwise replay `ldr r3,=0x1C2C ; cmp r4,r3` and pop pc
  -> 0x0224F58D. It clobbers only r0 (dead) and r3 (reloaded); r1/r2/ip are untouched.

### Double Evolution Pill regression (caused by Tyranno C1), proven 2026-09-28
- _c2 savestates (user: ml2 before activation, ml3 before the Deck pick, ml4 during it): the picker
  list has 2 cands, Super Conductor Tyranno 0x1AA0 and Ultimate Tyranno 0x1A79 (zone 0xD), yet the
  Deck (player+0x304) holds 3x 0x1265. So Tyranno is filtered out of the candidate build.
- DEP TARGET mode calls DECK builder 0x0223BC3C with type 0xA. Walker disasm: type&8 ->
  [sp+0x2C] -> 0x021BA69C(...,1) @0x0223BD7A, whose classifier (KB dispatch.summon_restriction_classifier)
  rejects every restricted-class cid. 0x1265 is class 2 because of C1 C. DEP's own docstring had assumed
  "no Dinosaur is in any restriction class", which Tyranno C1 falsified.
- Among the Lv7+ Dinosaurs only 0x1265 is class-restricted (the others are class 0; Sauropod Brachion is
  excluded by a different gate and should stay excluded).
- The commit 0x02269314 -> 0x0226925C does not call the classifier or 0x021BA69C (disasm), so the fix is
  candidate-side only.
- Walker predicate ABI: pred(side, 0xD, idx, row cid, [sp]=&card word, [sp+4]=list), the same as DEP's
  _filter.
- Plan N: in DEP's handler (0xA8 of 0xC0 used), add a second DECK pass with type 2 (no gate) and a
  predicate that keeps only class-restricted cids (0x020231C9(cid) != 0). No duplicates, since pass 1
  never records restricted cids.

## Build state 3 (2026-09-28): fix1 = C4 poster fix M + DEP upgrade, AWAITING IN-GAME TEST
- rom_ultimate_conductor_tyranno_fix1.nds sha256 76ef0ea4cf671129ca051343c69234e5e2e673b18cec69c5e6001ef9ed5ea3b6.
  Tyranno verify 30/30 PASS, DEP verify PASS, check_allocations [OK]. The _c2 ROM (94e77c65...) is untouched.
- M: 36 B @0x021F065C; literal 0x0224F730 -> 0x021F065D; 0x0224F58A -> bx r3 (0x4718). The only branch
  into the root is 0x0224F584 -> 0x0224F588 (the ldr, kept); nothing branches to 0x0224F58A.
- DEP: handler relocated to CAVE_DEP_HAND 0x023A2860 (0xC0 B of 0xE0), predicate CAVE_DEP_NOMI 0x023A2940
  (0x1C B), old slot CAVE_DEP_HAND_OLD 0x023A2360 retired; CAVE_FREE -> 0x023A2960. The criteria row is
  upgraded in place when the old row is present.
- ⚠️ SHIPPING NOTE: patch_double_evolution_pill (already in steps.STEPS) changed, so the chain output
  changes when the chain is rebuilt. Rebuild + sweep only when the user approves shipping Tyranno.

## In-game results on fix1 (user, 2026-09-28, sha256 76ef0ea4...)
Verbatim: "1. Does not offer me a prompt 2. Confirmed 3. Confirmed 4. Confirmed"; then "Face down Defence, the
attack resolved normally".
- Double Evolution Pill fix: in-game confirmed by user 2026-09-28 (offers + summons Tyranno from the Deck;
  UT / SCT still offered, no duplicates, Brachion still excluded; Sasuke Samurai / Mystic Swordsman LV2 OK).
- C4 still no prompt, TARGET WAS FACE-DOWN DEFENSE.

### C4 cause #2 (proven by disassembly 2026-09-28): the +0C condition is face-UP only
- Slot fields (per side*0xB3C + zone*0x14): 0x0229ACCE = position (non-zero = Defense), 0x0229ACD0 = face-up
  flag. Evidence: the two native conds differ ONLY in that test.
  - 0x021F842D (Ninja Grandmaster Sasuke; used for Tyranno's G row): not direct, [ACD0] != 0, [ACCE] != 0
    = face-UP Defense.
  - 0x021F5A1D (Sasuke Samurai family, printed "face-down Defense Position"): not direct, [ACD0] == 0,
    [ACCE] != 0 = face-DOWN Defense.
  - Consistent with the ml2 savestate: a set Revival Rose shows ACCE 1 / ACD0 0; face-up ATK Mystic Tomato
    shows ACCE 0 / ACD0 1.
- So a face-down target fails G's condition whether or not the poster (M) works. M is still UNOBSERVED
  in-game.
- Fix plan: an ov5 +0C that returns 0x021F842D(desc) || 0x021F5A1D(desc) = "not direct and Defense
  Position, either face".

## Build state 4 (2026-09-28): fix2, AWAITING IN-GAME TEST
- rom_ultimate_conductor_tyranno_fix2.nds sha256 6a4671ce90fc52a3519b640b35a2ac37318fb779fe539e93e738ddac4a7e8e15.
  Tyranno verify 31/31 PASS, DEP verify PASS, check_allocations [OK].
- G row +0C is now CAVE_UCT_C4COND 0x023A2960 (28 B): 0x021F842D || 0x021F5A1D. CAVE_FREE -> 0x023A2980.
- Test BOTH a face-up and a face-down Defense target. If face-up ALSO shows no prompt, poster fix M is not
  working -> stop patching and measure: savestate at the start of the Damage Step, read the event queue
  for code 0x15.

## C2 bug: face-down ATTACK position (user, fix2 ml2/ml3, 2026-09-28)
Verbatim: "See .ml2 and .ml3, UCT flips cards into face-down attack position, which is impossible" (ROM: fix2).
- Savestates: the opponent's 2x Evil Thorn 0x1FE1 have pos(+0xA) 0 = Attack and face-up(+0xC) 0 =
  face-down, which confirms the report.
- CAUSE (disasm): 0x021C4F24 -> 0x021C4F44 only toggles the face bit and queues flip command 0x34
  (0x021C3BC8); it never writes the position field. It is DARKNESS APPROACHES' primitive (0x1326
  resolver 0x0220E184 calls 0x021C4F24(desc,side,zone,0); printed "its battle position remains the same").
  BOOK OF MOON 0x1538 (resolver 0x02214098, printed "face-down Defense Position") calls
  0x021C5894(desc, side, zone) @0x02214116. C2 copied Book of Eclipse's 0x021C4F24 call, which is wrong
  for "face-down Defense".
- Fix: C2RES's flip loop calls 0x021C5894(desc, opp, zone) (3 args) instead.

- SECOND C2 BUG found while rechecking: the presence reads (C2HELP field count, C2RES 0x94 "still there")
  used 0x0229ACD0 = the FACE-UP flag, so the player's own face-down monsters were not offered and the
  if-you-do check could misfire on a face-down pick. Fixed: they read the card word at 0x0229ACC8
  (player+0x34). Verified on the fix2 ml2 savestate: low u16 is non-zero exactly for the occupied zones
  (face-down Tomato / Thorns included) and 0 for empty zones.

## Build state 5 (2026-09-28): fix3, AWAITING IN-GAME TEST
- rom_ultimate_conductor_tyranno_fix3.nds sha256 26f9e309c93720c649da908dd862a98bb6a798e53df415b397d806f6c8d2f7ca.
  Tyranno verify 31/31 PASS, DEP verify PASS, check_allocations [OK].
- C2 flip = 0x021C5894 (Book of Moon); presence = 0x0229ACC8. Everything else as fix2.

## IN-GAME RESULTS on fix3 (sha256 26f9e309...f7ca): in-game confirmed by user 2026-09-28
Verbatim: "1. Confirmed 2. Confirmed 3. Confirmed 4. Confirmed".
- C2 flip -> face-down DEFENSE (opp only); C2 picker lists own face-down monster + flip follows;
  C4 prompt on face-down AND face-up DEF, Yes = 1000 + to GY, ATK target no prompt; C2 either Main Phase,
  not Battle Phase, once per turn.
- With C1 + C3 (first ROM, confirmed 2026-09-28) and the DEP fix (fix1, confirmed 2026-09-28):
  WHOLE CARD in-game confirmed by user 2026-09-28. NOT yet in steps.STEPS (awaiting the user's ship approval).

## SHIPPED 2026-09-28 (user: "Ship it")
- steps.STEPS [81/84] "Sengenjin -> Ultimate Conductor Tyranno (whole card)", right after Double Evolution Pill
  (it must stay after Dark Law / Norden for the 0x022234C0 host); _verify_all_patches.SHIPPED; donor pool updated.
- EE build: 84/84 steps, BUILD_EXIT 0, rom_all_patches.nds sha256
  b85c3441855e007fff9efb97b7049926dbc068794e98ea0c161988bf76241634 (129,640,584 B). Pre-ship backup:
  rom_all_patches.pre_tyranno.nds (9b82f8a1...ca7e).
- Sweep: 69 passed, 1 failed. The failure is patch_ninishi (5 hook-site checks), and it is PRE-EXISTING:
  the identical 5 FAILs reproduce on the pre-Tyranno backup 9b82f8a1..., so this ship did not cause it.
  Tyranno + DEP both PASS.

## Ruled Out
- C4 "miss-timing" (hypothesis 1): executing 0x021EE0E0 offline gives IDENTICAL verdicts for 0x1265,
  0x2043 Velphito, 0x246B Wattmole and 0x1524 Sasuke Samurai across event codes 0x1E/0x17/0x10/0x0C/
  0x05/0x00, so it cannot tell the working cards from Tyranno.

## Open Questions
Inherited from precedent search, all UNVERIFIED until re-read this session:
- C1: trampoline 0x0224C026; leaf 0x0225FA36; criteria row {cid,0xFFFF,0x0223CA11,0x48000002};
  procedure registry 0x0228F158 -> 0x0226292D; count=2 (Fenrir arm); payment 2-in-one-pass
  (Necrofear arm 0x02262A52); nomi class-1 list 0x0209BE2C (count imm 0x37 @0x020231CC).
- C3: attack-all list 0x0226D6E4 (10 cids, bsearch 0x02022E14); sites 0x021A3FE0 / 0x021A424C /
  0x021A58CC / 0x021A67A8. Ultimate Tyranno 0x1A79 also at ov3 0x0226E77A (unknown list).
- C4: cond 0x021F842D (Ninja Grandmaster Sasuke cls1[412] @0x02288774), you-can 0x021E51E5,
  battle ctx 0x02298AD8, damage 0x021CFBC8, send 0x021CF658.
- C2: speed-2 list 0x0209C118 (count 0x76 @0x02023490); main-phase cond 0x021F4EC0;
  destroy-then 0x02204674 / [0x0229C314+0x14]; flip 0x021C5894. Hand-destroy: no precedent.

## Next Experiment
Donor gate checklist on 0x1265 (every u16 0x1265 occurrence in ARM9/ov3/ov5).
