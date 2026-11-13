# Infernoble Knight Ricciardetto — findings

Family card 6. Donor Tiger Axe 0x0FE6 (L4 EARTH Beast-Warrior Normal 1300/1100) + clause split confirmed by user
2026-10-20 ("Confirmed, Tiger Axe — proceed").

## Printed text (scratch/ygoprodeck_cache.json): Tuner, Warrior, FIRE, L1, 500/0
- C1 (hand OR GY ignition) cost: banish this card; SS 1 Level 4 or lower FIRE Warrior from your hand as a Tuner.
- C2 (NS or SS trigger, optional) target 1 Level 4 or lower FIRE Warrior in your GY, except Ricciardetto; SS it,
  also you cannot SS monsters for the rest of this turn, except Warrior monsters.
- C3 HOPT shared: only 1 Ricciardetto effect per turn.

## Confirmed (this session, static / offline)
- Donor 0x0FE6 has NO cls0-3 / criteria / ignition / GY rows in rom_infernoble.nds (scratch/infernoble/recs.py).
- Summon-event walk: SOURCE cid 0x0FE6 reaches the DEFAULT leaf 0x02268666 (leave_dispatcher_sim.walk root
  0x022680AA, cid_reg r2); control Plaguespreader 0x1EA9 -> its own arm 0x02268546. => a rider-latch front at
  RIDER_SITE sees C1's summon (KB summon.event_record_0x12_is_the_source_cid: [ev+0x12] = summoning effect's cid).
- NATIVE PRECEDENT C1 = Stygian Street Patrol 0x2224 ("banish this card from your GY; SS 1 Fiend ... from your hand"):
  cls2[549] {res 0x0220667D, +0C 0x021F0BDD, +10 0x021E5709, +14 0}; ignition row f1 0x021F047D, f2 0x021F0A11;
  native GY row 40 {0xE, 0x0224C591, 0x0224C6C1}. Hand-SS resolver 0x0220667D is shared by Marauding Captain 0x14C6,
  Kageki 0x2461, Gemini Scorpion, Seed of Deception (criteria handler 0x0223CA51 = hand worker 0x0223BFD4 mode 2).
  - 0x021E5708 cost = GY only: 0x021A2510(side, desc[+0xC]) GY index -> 0x021C7104 GY->banished.
  - f1 0x021F047C = free-zone count (0x021F0114) >= 1, can-SS 0x021B9EC0, hand candidate count 0x0224401C(desc) > 0.
  - f2 0x021F0A10 = card in GY (0x021A2510 >= 0) and 0x021BAC00(side, side) (can banish).
  - 0x0224401C(desc) loops hand index i over 0x02243FE0(side, cid, i) (Oliver lesson, confirmed again).
- Hand banish for the hand-zone cost: Dragon Rulers' HAND_INDEX 0x021A25A1(side, ref) + HAND_BANISH 0x021C6E99(side,
  idx), wrapped in CHAIN_PUSH/POP (patch_dragon_rulers cost phase 5, shipped + confirmed).
- Criteria word level byte (bits 16..23) = 0x80 ("or lower") | level << 2 | 0x01 GY: hand Lv<=4 0x90 (Marauding
  Captain), hand Lv<=2 0x88 (Seed), GY Lv<=2 0x89 (Junk Synchron), GY Lv<=4 0x91 (Alien Ammonite / Wattkeeper).
  => C1 hand row word 0x7C900002, C2 GY row word 0x7C910002.
- OFFLINE (scratch/infernoble/ricc_handcount.py over rom_infernoble.ml2): worker 0x0223BFD4 as 0x0223CA51 calls it,
  word 0x7C900002, per hand index -> hits exactly Turpin + Maugis (the L4 FIRE Warriors); with row cid = 0x139A the
  Maugis slot STILL counts => no same-cid exclusion => Ricc in hand counts itself => hand-zone +0C needs count >= 2.
- NATIVE PRECEDENT C2 = Junk Synchron 0x1E07 cls1 {res 0x02207191, +0C 0x021F03B5, +10 0x021E51E5, +14 0x02235605},
  criteria handler 0x0223C9D1 (= GY worker 0x0223C4E8 flags 8). 0x021F03B4 = 0x021F0384 then 0x02243FE0(side, cid,
  param 0x02234E78(desc)).
- One cid -> 2 criteria rows needs the shared criteria_row_hook arm (row resolver forces rel 0 for a cid in neither
  membership list): Shadow Mist / Oviraptor shape keyed on desc[+5] == 1 (cls1 = C2) -> rel 1.
- Warrior lock: bl @0x021BA368 currently -> Obedience Schooled's LOCK 0x02237DBC (chain); Ricc front calls it first.

## Ruled Out
- Appending an arm to criteria_row_hook.ARMS: the shared stub's prelude `beq native` overflows Thumb-1's conditional
  range (thumb_asm: "beq out of range: 135" halfwords) -- the stub is FULL for appended arms. Ricc uses its own FRONT
  CAVE_IK_RC_ROW at the site 0x02243BEC that tail-jumps to the unchanged CAVE_ROWHOOK. (Ship-time: the shared stub
  needs a long-range prelude, e.g. `bne arms ; ldr r3,=native ; bx r3`, before any further arm can be appended.)

## Build design (BUILD 8)
- Slots: CAVE_IK_RC_{ARM, COND, COST, RES, C2CND, C2RES, C2H, LOCK, LATCH, ROW}; phantoms cls2 0x1B8F, cls1 0x0E61,
  populate 0x0E42 (rel 0 hand row) + 0x0E4B (rel 1 GY row).
- Fronts: rider site 0x02268666 -> RC_LATCH -> Renaud's R_LATCH -> CAVE_RIDERLATCH; SS gate bl 0x021BA368 -> RC_LOCK
  -> Obedience LOCK 0x02237DBC; row hook 0x02243BEC -> RC_ROW -> CAVE_ROWHOOK; ARM9 H4 front (Turpin's) accepts 0x0FE6.
- Shared registers touched: gy_vrow_hook.ARMS (+0x0FE6), C79_ARMS (local, +0x0FE6).

## IN-GAME RESULT -- in-game confirmed by user 2026-10-20 (BUILD 8, sha256 5622c964...9ffb)
User's words: "All confirmed. Build Roland" (answer to RC1-RC8 + regression 12-15). Whole card confirmed, incl.
RC4 => PROVES in-game that the 0x0220667D hand-SS summon's event SOURCE cid is 0x0FE6 (latch fired). NOT shipped.

## BUILD 8 (2026-10-20)
- rom_infernoble.nds sha256 5622c96424d6d84722687a17389464d2305c6d1da7b89fc57bfd980804079ffb (all six Knights).
- patch_infernoble.verify PASS (every RC line incl. shared row stub unchanged, rows in order, text 8 langs).
- Regression list = BUILD 7's (Eva / Shadow Mist chain-walk + Overtex timing = local-arm category) PLUS one new
  expected line: Shadow Mist's "R row hook @0x02243BEC -> the SHARED stub" (site now BLs RC_ROW, which tail-jumps
  to the unchanged shared stub -- the Renaud latch-front category).
- OFFLINE EXECUTION (scratch/infernoble/ricc_ss.py, BUILD 8 tables/sites/stubs written into the savestate memory):
  .ml2 + .ml3: row resolver 0x02243B9C(0x0FE6, 0) -> row 33 (hand, rel 0) with a cls2 acting desc, row 34 (GY, rel 1)
  with a cls1 acting desc. C1 +0C HAND desc: .ml2 (2 hand FIRE Warriors) -> 2; .ml3 (1) -> 0 (Ricc is the 2nd).
- ASSUMED (KB-anchored, not measured for THIS resolver): C1's hand-SS summon event carries SOURCE cid 0x0FE6
  (summon.event_record_0x12_is_the_source_cid -- Brilliant Fusion). If the C1 monster is NOT a Tuner in-game,
  measure [0x02298A28+0x12] at the RIDER_SITE with a savestate.

## Open Questions
- Is the C1-summoned monster a Tuner (latch fires on the 0x0220667D summon)? -> in-game item.

## Next Experiment
- User in-game test of BUILD 8 (steps in _build_infernoble.py docstring, RICCIARDETTO block).
