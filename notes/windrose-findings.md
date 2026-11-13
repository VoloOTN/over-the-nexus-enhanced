# Windrose the Elemental Lord — findings

Status (2026-10-06): plan approved (~\.claude\plans\windrose-the-elemental-lord-sparkling-axolotl.md).
Whole card in one build (user). Donor: Soitsu 0x190B (user-chosen 2026-10-06). NOT built, NOT shipped.

Text (scratch/ygoprodeck_cache.json id 53027855): Lv8 WIND Winged Beast 2800/2200. 3DS cid 0x2916.
C1 nomi / C2 exactly 5 WIND in GY, from hand / C3 If SS: destroy all opp S/T (mandatory) / C4 HOPT on C3 /
C5 leaves face-up -> skip next BP.
User rulings 2026-10-06: empty opp S/T -> C3 still activates and spends the HOPT (3DS +0C = OPT-or-2).
C3 trigger = new shared hook on the c79 search (N-or-SS list 0x0228F60A has no phantoms).

## Confirmed (agent disasm on rom_all_patches.nds, 2026-10-06 — re-check before relying on it)
- HFD 0x1246 cls0[129] @0x0227F264 = {0x1246, 0, 0x022048FD, 0x021DA081, 0, 0, 0}.
  Resolver 0x022048FC: bl 0x0224AA20 (mask via find_event_handler on desc -> record +08 sweep 0x0224A988) ;
  bl 0x021CF310(desc, mask) (queue destroy; mask 0 -> clears and returns) ; return 0. No cid switch.
- Filter 0x021DA080 = 0x021D6E40(desc, side, zone, 0x1042): opponent of desc[2], zones 5..10, occupied.
- Moisture Creature cls1 {0x13B5, 0, 0x022048FD, 0x021DA081, 0, 0, 0} = native mandatory twin.
- 3DS Windrose row 0x6C5C3C {0x2916, res 0x458A00, +08 0x3DD89C, +0C 0x49BFF8 (OPT-or-2), +10 0x400EF0 (OPT post), 0}
  = HFD's resolver/filter pair.
- c79 search: 0x02265C40 bl 0x02022E14(cid, 0x0228F60A, 0x18) only for code 7/9; 0x02265C44 cmp r0,#0 ;
  beq 0x02265C4A; member 0x02265C48 movs r5,#1; 0x02265C4A reloads r0/r1 (disasm this session).
- Slots: CAVE_FREE 0x023A5350; hand-SS 10/15; C5 stub 4 cids = 100/104 B; WIND = 6; cls1 free phantoms
  incl. 0x18E5; nomi class-2 full; class-4 list 0x0209BC14 has unclaimed phantom 0x19A8.
- Pyrorex is SHIPPED (steps.STEPS line 180) — pyrorex-findings.md header is stale.

### Step 0 — Soitsu per-cid gates (disasm this session, rom_all_patches.nds)
- **RULES GATE (blocker-class): Doitsu 0x1917's union-equip target lock is Soitsu 0x190B.**
  Doitsu cls3 @0x0227B214 = {0x1917, 0, 0x02216A51, +08 0x021D8465, 0x021F67C1, 0x02237639} (Koitsu 0x1620
  @0x0227AA7C shares the handlers). +08 0x021D8464 -> 0x021D7348 (equip-target lock, KB equip_spell_engine:103).
  Equip-cid tree: Doitsu/Koitsu fall to the default arm 0x021D7FA4 (0x020230E8 = card type == 8 Union ->
  0x021A10EC) -> union sub-switch from 0x021D7FF2 on u16[desc] with r1 = literal 0x1917:
  `0x021D7FFE b 0x021D811A` (== Doitsu) -> `0x021D811A subs r1,#0xc ; cmp r5,r1 ; beq 0x021D816C (accept)`.
  r5 = candidate cid (0x021A3320). So 0x1917 - 0xC = 0x190B: **a card on cid 0x190B is a legal Doitsu
  target** (+2500 ATK per Doitsu's text). Invisible to u16 scans (base-imm). Walker: scratchpad equip_leaf.py.
  Doitsu ships on the NDS (donor_scan.cards(): Union Monster Lv4 EARTH Fairy 100/200).
- ov5 hits are CPU-AI Aitsu/Koitsu/Soitsu/Doitsu heuristics, not rules:
  - 0x022D0374 literal, used @0x022D016C inside 0x022CFD68 (7 ov5 callers): compare tree r5 in
    {0x160A Aitsu, 0x1620 Koitsu, 0x190B Soitsu, 0x1917 Doitsu} -> same treatment (0x021AE90C test, then
    0x022D100C(0)). 0x022CFD68 also calls 0x022D100C(0/1) from unrelated checks = an AI action scorer.
  - 0x0237F390 literal, used @0x0237F216: `0x021AC9D0(side, 0x190B)` then 0x0236AF90(.., 0x190B+0xC = Doitsu);
    sibling block @0x0237F1F4 does the same for Aitsu 0x160A -> +0x16 = Koitsu. AI union-pair planning.
  - Structural support: ov5 is evicted by ov41 in puzzles, and rules run there unchanged.
- Names (3DS CARD_Name): 0x19A8 = Cyber Barrier Dragon, 0x18E5 = Mutant Mindmaster (both NDS phantoms).
- ⚠️ Side note for Eva (Aitsu 0x160A, shipped): Koitsu 0x1620's union target is Aitsu by the same mechanism
  (AI block +0x16) — NOT checked in the ov3 lock this session.

### Step 0 — nomi class 4 (disasm this session)
- 0x020231C8(cid): class 1 list 0x0209BE2C (0x37), class 2 0x0209BE9C (0x39), class 3 0x0209BA12 (3),
  class 4 0x0209BC14 (0x1D) else 0. Class-4 members = "SS only by a specific card effect": LV monsters,
  Assault Modes, Yubel forms, Cyber Laser Dragon, Exodia Necross, Gearfried the Swordmaster, ... ; phantoms
  0x0E22 / 0x167C / 0x19A8 (Cyber Barrier Dragon).
- Callers (BL + pointer scan over ARM9 / ov3 / ov5): ARM9 0x020232DA (>0), 0x020233F4 (2 or 4 -> 0, same);
  ov5 0x022D43FE (==0), 0x023590AC (!=0), cave ptr 0x023A2958 = CAVE_DEP_NOMI (!=0);
  **ov5 0x0236A1BA: jump table (pc 0x0236A1D2): class 0 -> 0x0236A398, 1/2 -> 0x0236A1DE (cid tree),
  3/4/5 -> 0x0236A1DC (b 0x0236A086 skip).** That function also BLs 0x0225E51C (hand-SS legality) = the CPU
  AI's hand-SS planner. So class 4 vs 2 differs ONLY for the AI: a CPU holding Windrose would skip it.

- AI planner fn 0x02368B40: return 1 = SKIP the card. Class 3/4/5 -> 0x0236A1DC b 0x0236A086 (movs r0,#1).
  Class 1/2 unknown cid -> tree default 0x0236A3C6 (0x19FD / 0x1DAC arms) -> 0x0236A3F0 (r4 == 0x247B arm)
  -> 0x0236A404 movs r0,#0 = consider. So class 4 makes the CPU skip Windrose; class 2 would not.

### User decisions 2026-10-06 (after Step 0)
- Doitsu gate: NEUTER Doitsu's arm: ov3 0x021D811E `beq 0x021D816C` -> nop (mov r8,r8 0x46C0); falls to
  `b 0x021D7F5E` reject. Soitsu no longer exists, so Doitsu has no legal target either way.
- Class 4 AI skip: user said "find another way". Chosen: rules stay class 4 (phantom 0x19A8); ov5 AI site
  0x0236A1BA `bl 0x020231C8` -> ov5 stub returning 2 for 0x190B else native class. Both ov5 -> puzzle-safe.
- Koitsu/Aitsu (Eva) check spun off as a separate task.

### BUILT 2026-10-06 (layered on chain rom_all_patches.nds 14:22)
- data/over_the_nexus/working/rom_windrose.nds sha256
  67dd60743c80c0c3ed68f53b8cffcbb14f54dfe5acee8b1408e1b12e1eb9b059. --verify 17/17 PASS.
- Stubs (all Thumb-1, literals odd, no POP-LR): SSCOND 0x023A5350 56 B, RES 0x023A5390 40 B, COND 0x023A53C0
  36 B, C79TRIG 0x023A53F0 28 B, AICLASS 0x023A5420 28 B; CAVE_FREE -> 0x023A5440.
- cls1 {0x190B, 0, 0x023A5391, 0x021DA081, 0x023A53C1, 0, 0} over 0x18E5 (count 1333 unchanged); nomi class 4
  0x19A8 -> 0x190B; c79 site 0x02265C44 -> BL 0x023A53F0; AI site ov5 0x0236A1BA -> BL 0x023A5420;
  Doitsu 0x021D811E 25d0 -> c046; C5 stub 4 cids 100 B (local); summon_trigger_hook.stub(skip=) bytes unchanged.
- EXECUTION PROOFS scratch/windrose_equiv.py: C5 224 inputs, only 0x190B changed == 0x1110; c79 48 inputs ==
  native + 0x190B member; AI class 16 cids == native, 0x190B -> 2; RES posts then HFD(desc), returns 0;
  COND 2 / 0 on used.
- Sweep: 82 passed / 3 failed = grandsoil / moulinglacia / pyrorex "C5 stub == C5_CIDS" checks only
  (local addition until ship; expected).

## Ruled Out
- summon_trigger_hook (0x02265900): proper-SS only, a Monster Reborn revive would not trigger.
- Any-code list 0x0228F678: also fires on Flip Summon (deviation) — user chose the hook.

## Open Questions
- Soitsu ov5 literal hits 0x022D0374 / 0x0237F390: AI or rules gate? (Step 0)
- Class-4 nomi list: what does class 4 mean natively? (Step 0)

## SHIPPED 2026-10-06
- User: "All confirmed, ship it" -> whole card in-game confirmed by user 2026-10-06 on rom_windrose.nds 67dd6074...
- Shipped: 0x190B in gs.C5_CIDS (ledger 0x0220A158 92 -> 100 B), steps.STEPS after patch_pyrorex,
  _verify_all_patches.SHIPPED, donor pool + donor_resource.json (Soitsu -> used_normal), status strings.
- EE build 100/100, sha256 67dd60743c80c0c3ed68f53b8cffcbb14f54dfe5acee8b1408e1b12e1eb9b059 == the tested ROM.
  Sweep 86 passed / 0 failed. equiv --all IDENTICAL. Pre-ship chain backup: scratchpad
  rom_all_patches_pre_windrose.nds (faa1dfee...).

## Next Experiment (historical)
- USER IN-GAME TEST of rom_windrose.nds (67dd6074...), normal duel, steps in the session report. DONE.
- KB 2026-10-06: 665 facts, 591 PASS / 0 FAIL (+ card.hfd_resolver_is_record_driven,
  card.union_lock_doitsu_soitsu_base_minus_imm, summon.c79_verdict_site, summon.nomi_class4_equals_class2_for_rules).
- SHIP TODO (only after user sign-off): 0x190B into gs.C5_CIDS (+ ledger 0x0220A158 92 -> 100 B);
  steps.STEPS after patch_pyrorex + _verify_all_patches.SHIPPED; donor pool note (Soitsu -> Used);
  c79_trigger_hook ARMS comment -> confirmed; EE build + sweep.
