# Infernoble Knight Captain Roland — findings

Family card 10 (first Synchro). User 2026-10-21: "While I test Bradamante, begin Captain Roland". Clause split +
donor Thousand Dragon 0x0FEB confirmed by user 2026-10-21 ("Confirmed, Thousand Dragon — proceed"); losing its Fusion recipe accepted.

## Printed text (scratch/ygoprodeck_cache.json): Synchro Tuner, Warrior, FIRE, L5, 2000/500
1 Tuner + 1+ non-Tuner monsters
- C1 If this card is Synchro Summoned: You can activate this effect; during the End Phase of this turn, send 1 Equip
  Spell from your Deck to the GY, then add 1 Warrior monster from your Deck to your hand. (once per turn)
- C2 During the Main Phase, if this card is in your GY (Quick Effect): You can target 1 Warrior monster you control;
  equip this card to that monster you control as an Equip Spell that gives it 500 ATK. (once per turn)

## Donor scan (2026-10-21, effectless Fusion candidates from notes/donor-pool-normal-and-effectless-fusion.md)
- Thousand Dragon 0x0FEB (Lv7 WIND Dragon 2400/2000): ENTANGLED only by its own fusion recipe A[8] (Time Wizard +
  Baby Dragon) -- the normal state for a Fusion donor. RECOMMENDED.
- Master of Oz 0x17EF (Lv9 EARTH Beast 4200/3700): recipe A[73] + unclassified arm9 u32 0x0201B074 (unchecked).
- Rabid Horseman 0x1002: ov3 u32 literal 0x021E1E78 + arm9 0x0206A5B8 -> per-cid code gate. RULED OUT. (WRONG, see below)
- CORRECTED 2026-10-22 (re-checked when the user asked): the Rabid Horseman 0x1002 "per-cid code gate" ruling was WRONG.
  ov3 0x021E1E78 is the literal behind `ldr r3,=0x1002 ; bl 0x021D6E40` @0x021E1DD0 = a zone-predicate SELECTOR MASK,
  not a cid; arm9 0x0206A5B8 is `ldr r2,=0x1002` (with r1 = 0xFFFF) into the varargs helper 0x0206A580 -> 0x0206A418,
  not card-effect code (exact meaning unproven). Only binding ref left = its own fusion recipe A[10] -> usable donor.
- Labyrinth Tank 0x1118: ov3 0x0229113C + arm9 literals 0x0205849C / 0x020588F0. RULED OUT -- CORRECTED 2026-10-22
  (notes/infernoble-captain-oliver-findings.md): all three are struct offsets / a pointer half, not cid gates.

## User decisions
- 2026-10-21: C2 GY Quick Effect -> "Research Quick Effect now" (not the ignition fallback).

## Confirmed (2026-10-21, static)
- Identity = patch_accel_synchro_stardust_dragon / patch_junk_speeder recipe (copy a real Synchro's card_prop with
  the cid swapped -> use a Synchro TUNER reference; genre clear bit 29 / set bit 36; fusion recipe A[8]
  @0x02270BD4 materials -> 0x3FFF; absent from LIST_A 0x02275AB8 / min-3; 0 literals within 0xFF in
  0x02248280..0x02249600; trigger via the shared summon-trigger hook).
- C1 delayed End Phase = Into the Void 0x2278's machinery: End-Phase registry row 107 {0x0225432D, 0x2278};
  0x0225432C = `r2 = 0x10 ; bx 0x02254121` -> the turn-log walker with zone 0x10 = SKIP the zone check (card anywhere);
  event word -> desc[+3] = 0x10, desc[+4] = 6, cls2; Into the Void's EP action is its cls2 record (res 0x0222F2A9).
  => C1 = Synchro trigger posts {cid, kind 1, ref}; registry row {0x0225432D, 0x0FEB}; cls2 branch (zone 0x10,
  event 6) does send-Equip-Spell then add-Warrior.
- GY offers (dispatch.gy_action_registry_consumers): enumerator A 0x0224C820 is called ONLY from 0x0224B4F4, which
  requires r4 == turn player [0x0229DD14+0x34] and zone 0xE => the GY effect MENU is turn-player only. The other
  readers: 0x0224CD08 (B, post-by-cid) <- 0x0224B53A / 0x0224CCF6 (GY viewer UI), 0x0224CD3C (C, has-row) <-
  0x0224B060 (player-activated-effect predicate, sole caller 0x021FBFD8) and 0x0226BCB6 (GY viewer UI). Thunk
  0x02243A9C -> A is only referenced from a criteria-handler pointer table @0x022754CC.
- Necro Gardna 0x1C0A (the only native "opponent's turn" GY quick effect besides Skill Successor's own-turn one):
  cls2 {0x0221F9E1, 0, IGN_DISPATCH 0x021F0BDD, 0x021E5709, 0}, ignition row {f1 0x021F0A11, f2 0x021F8F79}, REAL GY
  row 20 {0xE, 0x0224C591, 0x0224C6C1} -- same wiring as our GY ignitions.

- Synchro material rule (2026-10-21): 0x0FEB absent from LIST_A 0x02275AB8; three literals within 0xFF in
  0x02248280..0x02249600 (0x0F7D Ceremonial Token, 0x237A Necro Linker load, 0x0E66 exact compare) -- walking the
  INNER_PRED cid tree from 0x022482C6 (r4 = cid): 0x0FEB -> bl 0x02023138, the SAME generic leaf as Junk Speeder 0x120B
  and ASSD 0x126F (both in-game confirmed); 0x0F7D / 0x0E66 stop in their own arms. => generic "1 Tuner + 1+ non-Tuner".
- Synchro trigger: shared summon_trigger_hook lives in cave3 CAVE3_SUMMONTRIG 0x0221D760 (0x30, full: +1 arm = 60 B)
  -> Captain Roland front in ov5 at TRIG_SITE 0x02265900 (0x0FEB -> member path, else tail-jump to the cave3 stub).
- Add-to-hand resolver 0x02207EF5: 0x0FEB reaches 0x02207FCC (Striker's default path). End-Phase row 99
  {0x0225432D, phantom 0x0EC3} unclaimed -> cid -> 0x0FEB. Fusion recipe A[8] @0x02270BD4 = {0x0FEB, 0x0FB6, 0x0FAA, 0}.
- Synchro Tuner reference for card_prop: Formula Synchron 0x239E.

## IN-GAME RESULT BUILD 14 (user 2026-10-22)
User's words: "All of the other points for captain roland have been observed, just need to confirm C2".
- PASSED (in-game confirmed by user 2026-10-22): CR1 identity, CR2 Synchro materials / no Fusion, CR3 End-Phase
  send + add, CR4 OPT / proper-summon only, CR5 ASSD / Junk Speeder / Life Stream triggers.
- C2 not built yet. Necro Gardna observation (user 2026-10-22): "necrogardna's effect is available duing the
  opponent main-phase" -- savestate rom_infernoble.ml3 (BUILD 14 code in RAM verified; turn player 1, phase 2;
  side-0 GY = 3 x Necro Gardna 0x1C0A, ..., Roland 0x0FDB).

## BUILD 14 (2026-10-21) -- identity + C1 only
- rom_infernoble.nds sha256 f1ec1ddc97504d1b36bb26c01af55c73d349e3001e0810a4c2537256f4e44b7d; verify PASS (rows, EP row
  99, recipe A[8] dead, trigger front, text 8 langs); card_prop[310] <- Formula Synchron, genre 0x20200000 ->
  0x1000200000. Regression = the known set. NOT run: ASSD / Junk Speeder / Life Stream verify (they expect 0x02265900 ->
  the cave3 stub directly; it now BLs CR_FRONT, which tail-jumps there).
- Build time 173 s (ov5 batching).

## IN-GAME RESULT
- in-game confirmed by user 2026-10-22 on BUILD 17 (rom sha256 a239d17c...9eed): "All of captain roland and captain oliver is confirmed". Not shipped.

## Ruled Out
- Rabid Horseman, Labyrinth Tank as donors.
- "virtual GY rows are invisible to some reader": all four readers handle rows >= 60 (KB).

## GY QUICK EFFECT PATH -- MEASURED by execution over rom_infernoble.ml3 (2026-10-22, BUILD 14 in RAM)
(scratch/infernoble/gy_menu_flags.py; opponent's Main Phase, UI mode [0x0229DD94+0x4C] = 5, Gardna offered in-game)
- 0x0224BC40(side 0, zone 0xE, idx) -> flags 0xA for EVERY GY card (zone-level "GY has an activatable effect").
- Path: 0x0224BC40 -> 0x0224B838 -> criteria query on pseudo-cid 0xFFFE (0x02243FA8(0, 0xFFFE, 0x2010E) -> row 0x56B
  handler) -> thunk 0x02243A9C -> enumerator A 0x0224C820 (walks the VIRTUAL GY rows too: calls into 0x023A7700)
  -> per matching row: check 0x0224C591(side, cid, ref) -> 0x021EC740 -> offer gate 0x021ECC6C -> SPEED 0x021A87BC
  (desc, cid) -> activation check 0x0224AD94 -> Gardna: IGN_DISPATCH 0x021F0BDC -> f2 0x021F8F78.
  => in the opponent's turn the GY enumerator is NOT turn-player-gated on this route (only the own-turn menu caller
  0x0224B4F4 is); the per-card gates are the offer gate's SPEED and the record's +0C.
- Speed 0x021A87BC = cid tree; unlisted cids -> default leaf 0x021A894C `bl` (chain: CAVE_OQ_SPEED 0x023A33D0 Overtex
  -> Miscellaneousaurus -> ARM9 0x0202345C); contract r0 = desc, r2 = cid, return r0 = speed.
- PLAN C2: GY row (gy_vrow ARMS) + speed front (0x0FEB && desc[+3] == 0xE -> 2) + +0C "Main Phase of either player"
  ([0x0229DD14+0x48] in {2, 4}) + OPT + Vylon f1/f2 -> 1 (+08 Vylon filter -> EQFILT Warrior arm) + Vylon equip
  resolver + grant row {0x0FEB, +500, 0}. Verify offline by relabelling a Gardna as 0x0FEB in .ml3 and re-running.

## C2 BUILD 16 (2026-10-22) -- AWAITING IN-GAME TEST
- Two more gates found by execution (BUILD 15 offline run: 0x0FEB's row was never checked):
  * the GY enumerator 0x0224C820 prefilters each row with the NATIVE ARM9 speed 0x0202345C(row cid) >= 2 at
    0x0224C8AC (quick-only pass) and 0x0224C8E4 (whenever NOT the turn player's own Main Phase) -- Necro Gardna is
    natively speed 2; fixed by CR_SPD9 fronts at both BLs.
  * the opponent's-turn path calls the record's +0C with desc[+4] = 7 (own-turn menu passes 0) -- CR_CONDX no longer
    checks the event code.
- rom_infernoble.nds sha256 e1c03f1e2e96db2764ce26b9bdf3e7a5aaca7e7a51c0adab8f455f549c828a72; verify PASS.
- OFFLINE PROOF (scratch/infernoble/caprol_c2_ss.py over .ml3, opponent's Main Phase, BUILD 16 ov5 + tables + sites
  in memory, GY #0 relabelled 0x0FEB): speed 2; CR_CONDX 1; and INSIDE the 0x0224BC40 enumeration 0x0224AD94 returns
  1 for {0x0FEB, zone 0xE, event 7} -- identical to both Necro Gardnas. => C2 should be offered in the opponent's
  Main Phase. NOT measured: the activation flow after the offer (Vylon equip resolver, +500 grant row).
- New regression line (expected, local-front category): patch_overtex_qoatlus "M speed leaf -> BL Qoatlus speed stub".

## Open Questions
- (answered above) WHAT OPENS A RESPONSE / OPPONENT'S-TURN WINDOW FOR A GY EFFECT? Magician's Rod suspect (a)/(b). Needs an engine
  observation (native Necro Gardna), not more static reading.

## Next Experiment
- User (any ROM): Necro Gardna in your GY, opponent's turn. Note exactly when the game lets you use it (only at the
  attack declaration? can you open the GY in their Main Phase?) and take a savestate at a moment it IS offered and
  one in their Main Phase where you try. Then trace the offer path offline over those states.
