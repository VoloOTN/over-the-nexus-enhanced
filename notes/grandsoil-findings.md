# Grandsoil the Elemental Lord — findings

Status (2026-10-06): WHOLE CARD in-game confirmed by user; SHIPPED 2026-10-06 (steps.STEPS 97 steps,
_verify_all_patches.SHIPPED, 0x1110 arm moved into timing_class_hook.ARMS). EE chain rom_all_patches.nds
sha256 8494c75e...f1aaae01 == the in-game-tested rom_grandsoil.nds byte for byte; sweep 83 passed / 0
failed; ledger OK; KB 655 / 581 PASS. Pre-ship chain kept as rom_all_patches.pre_grandsoil.nds.
Earlier: C1 + C2 (Stage A) in-game confirmed by user 2026-10-05 (rom_grandsoil.nds; user's
report, verbatim: "1. Confirmed 2. Confirmed 3. Confirmed 4. Confiremd 5. Confirmed" against the
5-step test: 4 EARTH no offer / 5 EARTH offer + SS works / 6 EARTH no offer / no Normal
Summon/Set / Striker-or-Elder hand-SS still offered). NOT shipped, not in steps.STEPS.
C3/C4 (Stage B) and C5 (Stage C) not started. Donor: Millennium Shield 0x1110 (user-chosen
2026-10-05). Scope: whole card (user-chosen 2026-10-05). Plan:
`~\.claude\plans\grandsoil-the-elemental-lord-witty-flask.md`.

Text (scratch/ygoprodeck_cache.json id 61468779): Lv8 EARTH Beast-Warrior 2800/2200.
C1 nomi / C2 exactly 5 EARTH in GY, from hand / C3 When SS: target 1 monster in either GY; SS it /
C4 HOPT on C3 / C5 face-up leaves field -> skip BP of your next turn.

## Confirmed
- 2026-10-06 session (Stage B): user confirmed scope C3+C4 together, C5 deferred; and the ruling
  "revived monster comes to my side" (incl. from opponent's GY). KB 578 PASS / 0 FAIL / 74 UNV.
- timing_class_hook MEASURED 2026-10-06: CAVE_TIMINGHOOK 0x0239E340, stub(…) = 248 B of RESERVE
  0x100, 10 arms; + an ARM_JW arm for 0x1110 = 268 B -> does NOT fit -> relocation needed
  (user pre-approved, conditional on execution-proof equivalence: scratch/timing_hook_equiv.py).
- 3DS criteria row @0x68BB7C bytes read 2026-10-06: B8 27 FF FF 3C 71 4A 00 02 00 01 00 =
  {0x27B8, 0xFFFF, 0x004A713C, 0x00010002} (HYPOTHESIS now PROVEN).
- NDS either-GY handler 0x0223D6E1 rows (stock rom.nds / chain): Monster Reborn 0x12EA
  {0xFFFF, 0x0223D6E1, 0x00010002} = crit[90] stock / [83] chain; Zombie Master 0x1C2F word
  0x10910002; Colossal Fighter 0x1E12 word 0x78010002 (race byte 0x78 = Warrior).
- NATIVE TEMPLATE for "target 1 monster in EITHER GY; SS it" as a trigger: Colossal Fighter cls2[357]
  = {0x02207191, 0, 0x021F03B5, 0x021E51E5, 0x02235605} + criteria handler 0x0223D6E1; Zombie
  Master cls3[321] also uses 0x02207191 + 0x0223D6E1. So the resolver 0x02207191 (Junk Synchron /
  Norden C1a) is the same one Konami pairs with the either-GY handler. Junk Synchron cls1 = [840]
  @0x0228AF94 stock, [838] @0x0228AF64 chain (both readings were right; the chain shifts it).
- Donor 0x1110 has NO cls1/2/3 record and NO criteria row in stock or chain (script read 2026-10-06).
- N-or-SS list 0x0228F60A chain: 0x0E17, 0x164A, 0x1B6B still present (0x0E77 -> 0x1297 Archosaur).
- Phantom picks (present as ONE row in BOTH rom.nds and rom_all_patches.nds, no NDS card_prop, NO
  ledger claim in ANY pool; script scratchpad gs_phantoms.py 2026-10-06): cls1 0x0E5D, criteria
  0x0E94, N-or-SS list 0x1B6B. (Ledger criteria pool is incomplete -- e.g. Norden 0x0E7D, Oviraptor
  0x0E67 never registered -- so "still present in the chain ROM" is the real test.)
- 0x021F03B4 (native cls1 +0C) reads ONLY r0 = desc (disasm 2026-10-06): side = desc[2]^desc[6];
  0x021F0384 (desc) -> 0x021F0114 + free zone 0x021B9EC0(side, cid); then 0x02234E78(desc) param ->
  0x02243FE0(side, cid, param) candidate count via the criteria row. So wrapping it with r0 only
  (Oviraptor cond_stub shape) is safe, and its target-exists test runs through OUR criteria row.
- Summon-trigger reach: KB summon.trigger_is_a_membership_list (VERIFIED) -- the evaluator
  0x02265768 runs after every summon; code 9's only caller is 0x0226878A; c79 list 0x0228F60A has no
  extra gate. Native Archlord Kristya 0x205B = hand-procedure SS + "When SS" trigger (list c9+12),
  so Konami's hand-procedure SS reaches the evaluator. NO in-game precedent of a TRAMPOLINE hand-SS
  card carrying a summon-list trigger (none of the 7 table cids is in any of the 9 lists). The
  trampoline only forces the tree verdict (bit 0x4), so the downstream SS is the native one.
  Grade: PROVEN BY STRUCTURE, not by trace -- flagged to the user.
- ov5 free tail 2026-10-06: CAVE_FREE 0x023A4EC0, ceiling 0x023AA120 -> 0x5260 B.
- Timing-hook consumers: tch.install/apply/verify + patch_masked_hero_dark_law / patch_overtex_qoatlus
  (_rewrite_shared, verify) all read ov5_cave.CAVE_TIMINGHOOK -> changing the constant re-homes all
  of them; asm stub literals are cids/tags only (position-independent if base stays 4-aligned).
- NDS has no Elemental Lord (CARD_NAME_TO_KONAMI_ID scan, 2026-10-05).
- 3DS: Grandsoil = cid 0x27B8 (CARD_Prop idx 5213); Moulinglacia 0x2811, Pyrorex 0x289F,
  Windrose 0x2916 (scan of CARD_Indx_E/CARD_Name_E/CARD_Prop, 2026-10-05).

## 3DS wiring (Explore agent read, 2026-10-05; re-check bytes before relying on them)
- criteria 0x686CBC row @0x68BB7C = {0x27B8, 0xFFFF, 0x4A713C, 0x00010002}; Monster Reborn shares
  handler; NDS twin handler 0x0223D6E1 word 0x00010002 (Monster Reborn row 90).
- Procedure: case 0x4B72C8 = count_gy_attr(player, own attr via 0x1C9D44) == 5, no data row.
  NDS Dark Armed Dragon gate 0x0225FB8C = canSS 0x021AD870 && 0x021B1810(side,2)==3 (agent sim).
- Nomi: 3DS class-2 list 0x685E8E has 0x27B8; NDS twin list 0x0209BE9C (DAD idx 32).
- C5: leave case 0x507838 posts 0x38BDD0(owner, 0x27B8, 1|(n<<4), 0), n = 2 if own turn else 1;
  skip-BP predicate 0x3B95EC checks key 0x27B8 w/ countdown nibble zero. NDS twin predicate
  0x0224CF90 (pool 0xE7B / 0x16A1 / 0x1502, no 0x27B8); NDS poster 0x021D2584.

- KB proofs 2026-10-05: 576 PASS / 0 FAIL / 74 UNVERIFIED.
- Donor 0x1110 donor_scan: CLEAN (no data structure names it). 5 ARM9 hits read by hand:
  0x0209B4A2, 0x020A2210, 0x020A244C, 0x020A24CC = counting/numeric runs (not cid lists).
  **0x0209C24C is real**: it is entry 18 of a 60 x {u16 cid, u16 variant} table @0x0209C204
  (pool refs arm9 0x02022F10/0x02022F58/0x02022F9C). Functions: 0x02022ED8 virtual-id ->
  cid (ids 0x0ED8..0x0F13 = base 0x0ED8 + idx), 0x02022F20 virtual-id -> variant,
  0x02022F64 (cid, variant) -> virtual-id. Used by the ov3 deck-load path (0x021C0628
  area: cid = word & 0x3FFF, variant = word >> 14). So virtual id 0x0EEA = (0x1110, variant 1),
  which is an art/print variant and NOT an effect gate. 0x0EEA has no card_prop row.
  Risk: only cosmetic (alt-art index for 0x1110) if some deck carries 0x0EEA.

- tg_table hand-SS table @CAVE_TG_SSTABLE 0x0239F240 is FULL in rom_all_patches.nds
  (2026-10-05): rows 11B7,1F18,17CE,181C,13AE,1265,10A5 + zero terminator; code follows at
  +0x40, so it cannot grow in place -> must relocate (table literal lives in the trampoline).
- 0x021B1810(side, attr) = count of GY cards with attr: P = 0x0229AC94 + (side&1)*0xB3C,
  loop i < [P+0x14] over [P+0x55C + 4i] & 0x3FFF -> 0x021B1F7C(cid) == attr (disasm 2026-10-05;
  GY array per event_queue.yaml). 0x021B1F7C = Advanced-Dark override -> 2 else 0x0202ABC8(cid).
  DAD gate passes 2 = DARK; ERA2 attr map same numbering -> EARTH = 5.
- DAD leaf 0x0225FB8C bytes read: canSS 0x021AD870 ; 0x021B1810(r6,2) ; cmp #3 ; bl 0x0225F216.
- Free-zone gate 0x021B9ECC, may-SS gate 0x021AD870 (cards.yaml); Tyranno sscond uses both.
- Chained ROM: nomi class-2 list (57) still holds phantoms 0x0E63/0x0EB3/0x176C (unclaimed in
  pool nomi_class2_list); N-or-SS list 0x0228F60A still holds 0x0E17/0x164A/0x1B6B.
- rom_all_patches.nds mtime is ~12 min older than the newest finished_patches/*.py (staleness
  check: rebuild the chain before layering the test ROM).

- **Hand-SS table RELOCATED 2026-10-05**: CAVE_TG_SSTABLE 0x0239F240 (0x40, now
  CAVE_TG_SSTABLE_OLD2, retired) -> 0x023A4E00 (0x80 = 15 rows). register_tg_handss migrates
  rows when the installed trampoline still points at a retired home (layered builds).
  Proof: (a) layered rom_grandsoil.nds: 7 old rows + 0x1110 in new table, trampoline literal
  @0x0239B198 = 0x023A4E00, all 8 cids tg_handss_ok; (b) fresh EE chain to scratch
  (sha256 cdf80444...6556): ov3 byte-identical to the old chain, ov5 differs ONLY in the
  literal + the same 7 rows (same order) moved; sweep 82 passed / 0 failed.
- Stage A built: data/over_the_nexus/working/rom_grandsoil.nds (layered on the existing chain
  ROM, which predates the user's uncommitted patch_field_backgrounds.py edit). verify() 5/5 PASS.
  CAVE_GS_SSCOND 0x023A4E80 disassembled: free-zone 0x021B9ECD, canSS 0x021AD871,
  0x021B1811(side, 5) == 5 -> 1. Nomi: 0x0E63 -> 0x1110 in class-2 list.

- User APPROVED the Stage B slot list + risk checklist 2026-10-06 ("Go"), incl. item 4 on structure.
- TIMING HOOK RELOCATED 2026-10-06: CAVE_TIMINGHOOK 0x0239E340 (0x100, now CAVE_TIMINGHOOK_OLD,
  retired) -> 0x023A4EC0 (0x200); tch.RESERVE 0x200. Fresh EE chain to scratch (96/96, sha256
  087351cc...b5d28f) vs old rom_all_patches.nds (scratchpad gs_tmh_diff.py): ov3 differs ONLY at
  0x0224AF96..99 (the BL); ov5 differs ONLY in [0x0239E340,+0x100) (old home now zero),
  [0x023A4EC0,+0x100) (new home), plus last session's tg_table literal/rows. Stub bytes at new home
  == old chain's old-home bytes (position-independent). check_allocations: [OK].

- scratch/timing_hook_reloc_equiv.py 2026-10-06: 514080 inputs, old chain's old-home blob vs new-home
  stub + 0x1110 arm -> ONLY 0x1110 differs; all 10 shipped arms unchanged. Fresh chain sweep 82/0.
- STAGE B BUILT 2026-10-06: rom_grandsoil.nds (layered on scratch chain chain_tmh.nds sha256
  087351cc...b5d28f), sha256 A14533C7...80AA1DBB. patch_grandsoil --verify 17/17 PASS. Installed
  stubs disassembled: literals 0x1110 / 0x021A14E9 / 0x021F03B5 and 0x021E51E5 / 0x1110 /
  0x021D2585, all odd, POP {r4,r5,pc}. Sweep on the test ROM 72 / 10 FAIL -- the 10 = exactly the
  timing-arm owners, each failing ONLY "shared stub == tch.stub(ARMS)" because the 0x1110 arm is
  local until ship (expected; clears when the arm moves into tch.ARMS at ship time).
- KB: timing.hook_relocated_2026_10_06 + card.either_gy_revive_trigger_template VERIFIED (654 / 580 PASS).
- C3/C4: in-game confirmed by user 2026-10-06 on rom_grandsoil.nds sha256 A14533C7...80AA1DBB.
  User's report, verbatim: "All confirmed" -- against the 6-step test (own-GY revive / opp-GY revive
  to own side / decline keeps HOPT / accept spends HOPT / C1-C2 no regression / timing-arm cards).
  Risk item 4 (trampoline hand-SS reaches the c79 evaluator) is therefore settled in-game.
  NOT shipped: not in steps.STEPS; timing arm still local in patch_grandsoil.timing_arms().

### Stage C (C5) static, 2026-10-06 (user chose Stage C after C3/C4 confirmation)
- Skip-BP predicate 0x0224CF90(side) (stock disasm): 1 if 0x021ACC10(1-side, 0xE7B, 1) OR
  0x021A1430(side, 0xB, 0x16A1 Frozen Soul) OR 0x021A151C(side, 0xB, 0x1502). Its caller
  0x0224E12C (BP start): if set -> 0x021C48DC(side, 0xB, 0x16A1, 1) removes Frozen Soul's node,
  message 0x136, BP skipped. (0x0224CD84 is the different "cannot conduct BP" gate Soul Charge uses.)
- Frozen Soul cls0[471] @0x02281274 resolver 0x022196AC: 0x021D2584(1-side, 0x16A1, kind 5, 0) --
  persistent node on the opponent, consumed at its BP start.
- 0x021A1430 -> walker 0x021A1238(head, key): any kind < 6, IGNORES the countdown nibble.
- 0x021A151C -> walker 0x021A12D4(head, key, -1): kind 1 or 2 only, key match, AND countdown nibble
  ([node+2] bits 4..7) == 0; r2 < 0 = any ref. -> ANSWERS the open question: 0x021A151C HONOURS the
  countdown. Key 0x1502 = phantom (no card_prop); its only ov3 literals are the predicate pool
  0x0224CFD8 and its own two dead cls1 rows [213]/[214] @0x022874CC/0x022874E4.
- End-of-turn sweep (KB timing VERIFIED, continuous_riders.yaml): kinds 1/2 -> n = nibble; n == 0
  free else n -= 1; once per turn at phase 8 before the turn-player toggle [0x0229DD14+0x34].
  => post kind 0x21 if the leave is on the owner's own turn, 0x11 on the opponent's turn -> the
  node has nibble 0 exactly on the owner's next turn, and is freed at its end.
- NATIVE PRECEDENT for that exact shape: resolver 0x022107F0 (used by 5 cls records incl.
  0x1502's [214]) posts 0x021D2584(1-side, desc cid, 1 | ((1 + (TP == 1-side)) << 4), 0) =
  "skip the BP of the opponent's next turn" with the same countdown rule.
- Poster 0x021D2584(side, key, kind, ref) -> 0x021C479C(side, 0xB, key, kind, [sp]=ref) (disasm).
- Leave dispatcher 0x021C7FD0 (disasm 0x021C7FD0..0x021C8220): every invocation runs straight-line
  through 0x021C8078 `movs r0,#0 ; str r0,[sp,#0x18]` (0020 0690, stock == chain), after r4 = cid
  (0x021C7FEE), [sp+0x2C] left-field, [sp+0x94] face-up, [sp+0x98] card-word bit 14 are set. No
  branch in 0x021C7FD0..0x021CA800 targets 0x021C8078/0x021C807A. r1-r3 are not read again before
  `bl 0x021B8D90` @0x021C80B6 (but the stub preserves them anyway on its own path).
- Leave-mask route (Reborn Tengu's 0x000C) REJECTED for C5: it is a chain trigger (3DS posts directly,
  no chain), and the mask path zeroes r5 when dest == Deck (0x021C8116), so "leaves to the Deck"
  would be missed.
- ov5 hook at a every-leave site REJECTED: puzzles evict ov5 -> freeze on any leave (memory rule
  "never bl-hijack a shared fall-through into ov5").
- ov3 DEAD HOST: 0x0220A158..0x0220A1C0 (104 B) = resolver of phantom 0x0EAB's cls0[86] ONLY
  (literal @0x0227EE60 stock / 0x0227EE48 chain); no BL/B/Bcc anywhere in ov3 targets the range;
  preceded by a literal pool; 0x0EAB unclaimed in the ledger. (scratchpad dead_fn_scan.py lists ~25
  more such phantom-only functions, e.g. 0x02212374 520 B / 0xE79 0x02209C44 460 B.)

## Ruled Out
- Plain SS-trigger list 0x0228F63A: full (all 5 phantoms spent) -> use N-or-SS list 0x0228F60A.
- Summon-procedure registry row: not needed (costless SS; DAD/Kristya have none).

## Open Questions
- (answered) hand-SS table was full -> relocated, see Confirmed.
- (answered) 0x1110 arm9 hits -> 4 numeric runs + 1 art-variant row; donor approved by user.
- Stage B: Junk Synchron cls1 index (Norden docstring says [838], subagent stock scan says
  [840] @0x0228AF94) -- re-read before cloning.
- Stage B: timing_class_hook occupancy (subagent: 248 / 0x100 B, 10 arms) -- re-measure.
- Stage C: does 0x021A151C honour the kind countdown nibble? Turn-player address
  [0x0229DD14+0x34]?

## Next Experiment
- STAGE C BUILT 2026-10-06 (design approved by user, "owner" side approved): rom_grandsoil.nds sha256
  8494C75E...F1AAAE01 (on scratch chain 087351cc...). --verify 19/19 PASS; sweep 72/10 = the same 10
  timing-arm owners only (local arm, expected). Hook @0x021C8078 disassembles as bl 0x0220A158; stub
  72 B, pool {0x1110, 0x0229DD14, 0x1502, 0x021D2585}. Ledger [OK] (dead block + claim + 0x1502 /
  0x0EAB registered). KB timing.skip_next_battle_phase_node VERIFIED (655 / 581 PASS).
  C5 in-game confirmed by user 2026-10-06 on sha256 8494C75E...F1AAAE01, verbatim "All confirmed, Ship it"
  (6-step test: opp-turn leave / own-turn leave / every leave route / face-down / no chain / regression).
  WHOLE CARD CONFIRMED; user approved shipping 2026-10-06. (Old fallback plan:) If the BP is never skipped -> GDB bp at 0x0220A158 on a leave (is the
  dispatcher reached for that route?) then at 0x0224CF90 on the owner's next BP start.
- (done) Stage C design (2026-10-06, approved): BL @0x021C8078 -> ov3 stub @0x0220A158:
  r4 == 0x1110 && [sp+0x2C] && [sp+0x94] -> 0x021D2584([sp+0x98] owner, 0x1502,
  owner == [0x0229DD14+0x34] ? 0x21 : 0x11, 0); always replay movs r0,#0 ; str r0,[sp,#0x18].
- USER IN-GAME TEST of rom_grandsoil.nds (normal duel): steps 1-5 in PROMPT_grandsoil_clause3.md +
  timing-arm regression (Psi-Reflector / Oviraptor / Archosaur / Shadow Mist / Dark Law / Qoatlus /
  Accel Synchro SD / Jet Synchron / Jet Warrior / Lightpulsar). No prompt at all -> suspect risk item 4
  (trampoline hand-SS reaching the c79 evaluator) -> GDB bp at the c79 search 0x02265C40.
- (done) Stage B design (2026-10-06, approved):
  cls1 {0x1110, 0, 0x02207191, 0, CAVE_GS_COND|1, CAVE_GS_SLOT4|1, 0x02235605} over 0x0E5D;
  criteria {0x1110, 0xFFFF, 0x0223D6E1, 0x00010002} over 0x0E94; c79 list 0x1B6B -> 0x1110;
  CAVE_GS_COND = turnlog(side,0xB,0x1110,1) clear -> 0x021F03B5; CAVE_GS_SLOT4 = 0x021E51E5, on 1
  post 0x021D2585(side,0x1110,1,0); timing arm ARM_JW kept LOCAL (qoatlus timing_arms pattern).
  Timing hook relocate 0x0239E340 (0x100) -> 0x023A4EC0 (0x200); GS slots 0x023A50C0 / 0x023A50F0.
  Build: fresh EE chain to scratch, layer Grandsoil on it; equivalence = byte diff vs old chain +
  execution sweep old-home blob vs new-home blob.
