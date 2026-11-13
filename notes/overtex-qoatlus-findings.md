# Overtex Qoatlus — findings

Donor: **Prevent Rat 0x10A5** (user-chosen 2026-09-29). Whole card in scope (user: "All clauses").
3DS lookup FORBIDDEN for this card (user instruction).
C3 scope: field + hand/Deck (full printed text, user choice 2026-09-29).

Text (scratch/ygoprodeck_cache.json id 41782653):
- C1 Cannot be Normal Summoned/Set. Must be SS (from hand) by shuffling 5 of your banished Dinosaurs into the Main Deck.
- C2 Once per turn, when opponent activates a Spell/Trap (Quick Effect): destroy 1 Dinosaur in hand or face-up field; if you do, negate the activation, and if you do that, destroy that card.
- C3 If sent to the GY by a card effect: add 1 "Evolution Pill" Spell from Deck to hand. HOPT.

## Confirmed
- **WHOLE CARD IN-GAME CONFIRMED BY USER 2026-09-29** ("All confirmed", then "yes, ship it"):
  all 19 items of _build_overtex_qoatlus.py on sha 66b01000...f49432, incl. both rulings (costs /
  Tribute Summon NOT by effect; C2 once per turn = per copy). SHIPPED 2026-09-29.
- 2026-09-29 verify_knowledge: 522 PASS / 0 FAIL / 65 UNVERIFIED.
- 2026-09-29 steps.py contains Koa'ki Wall (l.110), Shadow Mist (128), Double Evolution Pill (132),
  Ultimate Conductor Tyranno (134), Animadorned Archosaur (135) — templates are shipped.
- 2026-09-29 donor_scan 0x10A5: VERDICT CLEAN. Only hit ov3:0x0227E458 = bytes a5102302 =
  pointer 0x022310A5 low half, not a cid. Name slots e=11 (floor 7), desc e=89 (floor 56) —
  card_text re-emit makes these irrelevant. (base±imm switch arms are not scannable — standing limitation.)
- "Evolution Pill" Spells = 0x1AA3 Big, 0x1715 Ultra, 0x1319 Double (patch_animadorned_archosaur.PILLS).

### C1 payment machine 0x0226292C (disassembled from reference ov3 this session)
- rec = 0x02298A28 in r4 for the whole state fn; [rec+0xE]=cid, [+2]=side, [+0x24]=state,
  [+0x26]=count/loop index, [+0x28]=pass. Picks count = [0x0229DD94+0x34].
- State 2 (0x02262B1C): per-cid arm on cid (r2) -> picker `bl 0x0219C430` @0x02262B6E with
  r1 = min([rec+0x26],0x20)+6, r3=[rec+0x28]. Default arm 0x02262B60/0x02262B68.
- State 3 (0x02262B7E): per pick, ref = r5+r6; `bl 0x021A2510` @0x02262BA4 = GY index lookup
  (player+0x55C, count +0x14); >=0 -> `bl 0x021C7104` @0x02262BB2 (GY->banished); else hand
  0x021A25A0 -> 0x021C6E98; else field 0x021A241C -> 0x021CF40C. A banished pick matches NONE
  (nothing moves) -> the donor needs its own mover arm.
- 0x021A2558(side, ref) = banished index lookup (player+0x7B4, count +0x1C).
- 0x021C727C(side, ref) = banished->Deck mover: dest 0x0C if 0x0202307C(cid) else 0x0D, via
  zone-pair emitter 0x021C69D0 src 0xF, then 0x022391CC(0x26,0), returns 1 (0 if not banished).
- Banished walker 0x0223C52C type bits: 8 -> 0x0219CD08(side,0xF,idx) movable check;
  4 -> 0x021B1E38; 0x10 -> 0x02023050. Handler 0x0223DB25 passes type 8 (add/return family).
  GY handler 0x0223CA11 passes type 0x10000 via 0x0223C4E8.
- Count tree 0x0225CF28 leaves return 3/2/1/7/0/computed — no 5 -> count can't come from it.
- DEAD ARM: state-2 arm 0x02262B4E..0x02262B5F (18 B) is reached only by `beq` @0x02262B2E
  (test `ldr r0,[pc]=0x234F` @0x02262B2A) + an internal blo @0x02262B52. 0x234F = phantom
  (KB: membership_list_b / populate phantom). Pool word 0x02262BD8 (=0x234F) is ALSO read by
  dispatch 1 @0x02262A40 (Hyperion 0x2447 BST) -> do NOT edit the pool word; repoint the ldr
  at 0x02262B2A to a new literal inside the arm. Scanned whole chained ov3 for B/Bcc/BL into
  the arm: only those two. Chain vs stock in 0x02262B28..BE0: only Tyranno's lit 0x02262BBC.
- Free ov3 ledger remainder: 0x021F065C block (64 B, 36 used) -> 28 B at 0x021F0680.

- STATE NUMBERING (jump table @0x02262944 decoded, add pc @0x02262942): state0 0x0226294E
  (open 0x021D28A4, count r7=0x0225CF28(cid), cid arm -> r5/r6, msg 0xD6..0xD9, [+0x26]=r7,
  state=1, 0x0219A818(side,1)); state1 0x02262B1C (picker, then state=2,[+0x26]=0);
  state2 0x02262B7E (per-pick mover loop, done -> state 3); state3 0x02262C24 (pass driver
  -> close 0x021D2964, return 1); state4 = 0x02262952 (re-pass, skips open).
  (The "state 2 / state 3" labels above in this file = states 1 / 2 in this numbering.)
- REGISTRY HANDLER CALL: 0x02264DBC `ldr r0,[row,#4]; blx r0` — no args. Second searcher
  0x022651D2 special-cases only 0x02261F8D / 0x0226448D, else cid BST (same as 0x0226292D rows).
  All 32 refs to 0x0226292D in ov3 are registry rows; zero in arm9. => a per-cid ov5 handler
  in the registry is reached ONLY by that cid: no shared hook, no ov3 bytes, puzzle-irrelevant.
  DESIGN CHOSEN: registry {0x10A5 -> CAVE_OQ_PAY|1}, wrapper replaces states 0 and 2, defers
  1/3/4 to 0x0226292D. (Supersedes the dead-arm plan above — no ov3 edit needed.)
- Count code 11 = exactly 5 (dispatch.multiselect: 6..0x26 -> code-6).
- SHUFFLE_DECK 0x021D269C(r0=side) queues cmd 0x55. Pick fetch 0x0219C94C(i 1-based) -> &word.
- Phantoms (chained ROM, no card_prop, unclaimed in pool): criteria 0x0E92 (1 row, no claims
  anywhere); registry + nomi class-2 0x18B9 (registry row handler 0x02261F8D; no claims).

### C3 (built 2026-09-29, AWAITING IN-GAME TEST)
- OFF-FIELD "BY A CARD EFFECT" SIGNAL (static, this session): relocation applier 0x021D1300's r3 ->
  [sp+0x10] ("cause"). Its only 3 callers: hand-discard mover 0x021C6CB8 (r3 = 1 - kind: effect 1, cost 0,
  UI -1), Deck mover 0x021D1DAC via 0x021D1F06 (event 0x1E, cause = its 5th arg), and 0x021D2314 via
  0x021D2450 (event 0x20, hand/Deck/Extra -> GY; cause = its [sp] arg; DESTROY_HAND 0x021D2478 passes the
  acting cid). Deck->GY thunks: 0x021D21B0 (22 callers, resolver code, r2 = `ldrh [desc]` = acting cid),
  0x021D21CC (cause 0; ALL 4 callers 0x021E6D72/0x021EA024/0x021EAA06/0x021EB164 are in the COST region),
  0x021D21DC (banish). => cause > 0 <=> by a card effect. Descriptor word: bits 0..8 ref, 14..17 source zone
  ([sp+0x34]), 19..22 dest ([sp+0x30]).
- Field destructions ALSO reach the chain (Babycerasaurus leaf 0x021D18D2), so the chain leaf is restricted
  to source >= 0xB; the field is covered by leave-mask 0x0A04 (stock Supay 0x21BA).
- 0x10A5's chain search ends at Shadow Mist's node 0x021D13CC (interval (0x106D, 0x1185) holds only 0x10A5
  and 0x111F). Lift: node[0:4] -> BL GY_STUB 0x021F0680 (28 B, rest of Tyranno's dead 0x0E46 body; stock +
  unreferenced on the chain ROM, checked). 0x10A5 also reaches Shadow Mist's miss-timing node 0x021EE10C:
  block B 0x021B5AAA `bx lr` -> `b C`, C = 0x021B5840 (8 B dead tail of 0x1827's block, stock + unreferenced).
- criteria_row_hook stub is FULL (adding an arm -> head `beq native` out of range, 270 B). C3 therefore reuses
  row 0 via a MODE-SWITCHED handler (Double Evolution Pill precedent): acting desc [0x0229A9FC+0x50] is
  0x10A5's cls2 (desc[+5]==2) -> Deck walker 0x0223BC3D word 0x4 + CAVE_ARCH_PRED (Pills); else banished walk.
- timing_class_hook arm (local until ship): desc[+5]==2 -> "You can" class 2. Stub 224 -> 248 / 256 B.
- EXECUTED (scratch exec_c3.py, thumbemu over the built ROM's ov3): 11 chain cases + 6 miss cases ALL PASS
  (0x10A5 accepts src 0xB/0xC/0xD with cause>0, rejects cause 0/-1 and field src; 0x111F still accepts;
  0x1100/0x1175 still reject; never-miss for 0x10A5/0x111F/0x1E1B, walk for 0x1100/0x10A4/0x1120).
- Build rom_overtex_qoatlus.nds sha256 c48ca2ab0828906947867d75e9a9d264eb099718bd431a9de0bf1d57aadaa59c:
  16/16 verify PASS (qoatlus + shadow_mist, tyranno, DEP, archosaur, lightpulsar, darkflare, misc, oviraptor,
  petiteranodon, snoww, eclipse_wyvern, grapha, dark_law, psi, jet_synchron). Slots: CAVE_OQ_CRIT 0x023A2F00
  (0xA0), CAVE_OQ_C3COND 0x023A2FA0, CAVE_OQ_C3SLOT4 0x023A2FD0; phantoms mask 0x174E, cls2 0x14DD.
- Shadow Mist verify() edited (ROM bytes unchanged): accepts the lifted node / block B.
- Harness gotchas: (1) the sent-to-GY whole-chain walk FAILS on the untouched chain ROM too unless every
  chain module is imported first (stubs register at import). (2) tch.stub's `arms=ARMS` default is bound at
  def time -- reassigning tch.ARMS is not enough.

### C2 (built 2026-09-29, AWAITING IN-GAME TEST)
- Speed: list 0x0209C118 has no unclaimed phantom (0x0E63 Wall, 0x0E5B/0x0E82/0x1534/0x1529 claimed). The speed
  lookup 0x021A87BC walks 0x10A5 (root 0x1E3A -> 0x1C03 -> 0x1534 -> node 0x021A87F2 tests phantom 0x1529) to
  the default leaf 0x021A894C with r0 = desc intact; Miscellaneousaurus already BLs that leaf into its ov5 stub.
  Chained: leaf -> CAVE_OQ_SPEED (0x10A5 && desc[+5]==3 -> 2) else tail to Misc's stub. EXECUTED (exec_c2.py):
  0x10A5 cls3 -> 2; 0x10A5 cls2/cls1 -> native 0x0202345C; Misc 0x0FF2 GY -> 1; 0x1234 -> native. PASS.
  0x0202345C = type-derived speed (Quick-Play 2, Trap 2, Counter 3, else 1).
- Negate: 0x022062F8 = `movs r2,#1 ; bl 0x02206230` -> 0x022061A4(desc, act, 1) returns 0 (no-op) if act == 0,
  then destroys the activated card by zone. So the resolver's r1 MUST be the activation.
- Chain resolution loop 0x021D5A0E sets [0x0229A9FC+0x50] = link, phase 0x80, and calls the invoker 0x0224AEB8
  @0x021D5AA4 (r0 = link desc; r1 NOT traced statically -- the preceding `bl 0x021D6AF8` jumps into the
  function epilogue). The activation state machine calls it with r1 = 0 @0x0221803E. => r1 on RE-ENTRY is
  UNPROVEN; the resolver stashes r1 on its 0x80 entry into ov5 cell CAVE_OQ_C2ACT and uses the stash.
- OPT: soft per-copy latch 0x021F01C0(desc) = rider 0x0FB6 on (side, zone) absent -> 1; stamp 0x021E5061 at +10
  (Junk Defender / Tyranno C2 shape).
- Build sha256 66b01000104f895482c20a4a6d19735b938ae83eab6501f4e6251be896f49432, 16/16 verify PASS
  (+ Misc's verify now accepts the chained leaf; ROM bytes of Misc unchanged). All 9 Qoatlus ov5 stubs: every
  blx/bx literal odd, no pop-lr (exec_c2.py). cls3 over phantom 0x0E4C. Slots CAVE_OQ_C2COND 0x023A3000 (0xA0),
  C2HELP 0x023A30A0, C2RES 0x023A3180 (0x240, 504 B), C2ACT 0x023A33C0 (runtime cell), SPEED 0x023A33D0.
- UNPROVEN (in-game will tell): (1) r1 == activation on the resolver's first entry (Wall's 0x022062F9 relies on
  the same, in-game confirmed); (2) a cls3 resolver enters at [0x0229AAFC+0x70] == 0x80 (Tyranno's C2 relies on
  it; Maiden's cls3 measured 1 -- KB resolver.phase_protocol); (3) negate after closing the 0x021D28A4 bracket.

## Ruled Out
- Single-cid named search (0x0223D075 aux=cid) for C3: three pills exist.
- Off-field endpoint 0x021D199E for C3: fires on any means incl. battle.
- 3DS lookup: forbidden by user.

- C1 BUILT 2026-09-29 (AWAITING IN-GAME TEST): _build_overtex_qoatlus.py onto rom_all_patches.nds
  (fresh: 11:23 vs newest shipped module 11:18) -> rom_overtex_qoatlus.nds sha256
  76fd97dae714c80cb2c1d94fb3c86155dc1176c706c62b11362247d689535b2c. verify PASS for overtex_qoatlus,
  tyranno, double_evolution_pill, archosaur, lightpulsar, darkflare, miscellaneousaurus.
  check_allocations clean (331 ov5 slots). author_facts --check: 525 PASS / 0 FAIL.
  Slots: CAVE_OQ_SSCOND 0x023A2E00 (60 B), CAVE_OQ_PAY 0x023A2E40 (168/0xC0), CAVE_OQ_CRIT 0x023A2F00
  (64/0x40: handler + predicate @+0x28). Phantoms 0x0E92 (criteria), 0x18B9 (registry + nomi).
  Stubs disassembled from the built ROM: all blx targets odd, no pop-LR.
- Extra-Deck Dinosaurs exist (Jurrac Giganoto 0x1FB6 / Velphito 0x2043 / Meteor 0x2181, Bracchio-raidus
  0x11A3, Pragtical 0x1188, Gaiodiaz 0x1C86) -> CRIT's predicate rejects 0x0202307C(cid) ("Main Deck").
- New KB facts: handss.procedure_registry_handler_is_per_cid, handss.banish_payment_state_layout,
  leave.banished_to_deck_mover (VERIFIED), card.overtex_qoatlus (UNVERIFIED, build status).
- Known cosmetic: state-0 prompt reuses native race-arm message 0xD6 (text unread; likely says
  "banish"). Nomi class membership also hides the cid from deck/hand search candidates (same as Tyranno).

## Open Questions
- C1: does prompt 0xD6's wording read acceptably? (user to report)
- C2 RULING TO CONFIRM WITH USER: "Once per turn" (no card name) built as a SOFT per-copy limit; Qoatlus
  itself counts as a destroyable Dinosaur.
- C3 RULING TO CONFIRM WITH USER: costs (discard/mill as cost) and Tribute Summons are treated as NOT
  "by a card effect" (built that way). Never assert rulings from recall.

## Next Experiment
- USER: in-game C1 test per _build_overtex_qoatlus.py docstring.
- USER: C3 test items 7-13 in _build_overtex_qoatlus.py.
- USER: C2 test items 14-19. If C2 fails with no negate after a destroy: suspect r1 on the 0x80 entry.
