# The Monarchs Erupt — findings (live)

Card text (scratch/ygoprodeck_cache.json): "Activate this card only if you have no cards in your Extra Deck and control a Tribute
Summoned monster. Negate the effects of all face-up monsters on the field, while those monsters are face-up on the field, except
Tribute Summoned monsters'. During your End Phase, if you control no Tribute Summoned monsters, send this card to the Graveyard."

Status: WHOLE CARD BUILT (E1 + E2 approved 2026-11-11 "Approve, build it"; E3 2026-11-11 "Build E3 first").  CPU-traced.  AWAITING IN-GAME TEST.
Current ROMs: rom_erupt.nds 93b9f2a1… (19/19, built on rom_chain_18C00 before the chain moved to 19C00), rom_monarch_all.nds 8a2c7b73… (erupt PASS).
- Module otn_enhanced/cards/erupt.py + cards/c/erupt.c; slots CAVE_ER_TINY/COND/TEST/NEG (0x023B2790..0x023B2910); cls0 phantom 0x0E3B;
  card_text 0x135E; added to tenacity.MONARCH (set "Monarch"); `_build_erupt.py` -> rom_erupt.nds sha256
  e9b4992c2c31b665ca7c667a15c2a608d81a083954734ce58a32881d2fc6149b, verify 16/16.
- Combined: 'erupt' appended to scratch/_monarch_session.py ORDER -> rom_monarch_all.nds sha256
  70d82cc18c7e3f69b4fb2598a2a3010c1ed7264dc854e9128c2ca08ce8624c83 (17 modules; previous build kept as rom_monarch_all_prev.nds).
- NEG front disassembled from the built ROM: push {r4,r5,lr}; save r0/r1; blx =0x021EE3DD; nonzero -> pop; else blx =0x023B2821 (TEST); pop {r4,r5,pc}.
- NOT traced: no CPU/GDB run yet shows the front reached or a monster negated.
- Combined-ROM verify of all 17 ORDER modules: erupt PASS; mega_monarch (3), restoration (2), edea (1), eidos_squire (1) FAIL with the SAME lines on
  rom_monarch_all_prev.nds (later modules take over their chain heads), so not an Erupt regression.
- CPU row: Respect Play already owns ov5 row 0x02393FAC {0x3D35E, always-true 0x023107C1} (`cardtest rows`): the CPU should play it.
- Trace tool: scratch/erupt_gdb.py (Caius/Raiza/Zaborg x3 + Erupt x3 + Lightsworn fodder, ED empty) -> build/cpu_battery/gdb_er/er_N.json;
  breakpoints COND 0x023B27A0, NEG verdict 0x023B28F6 (r4 side, r5 zone, logged when r0 = 1), RESNEG 0x021D4432 (desc in r4).

## Confirmed (2026-11-11, this session)
- 0x021EE3DC(r0 = side, r1 = zone) has exactly TWO BL callers in ov3 (scratch/_bl_callers.py on rom_chain_17C00):
  0x021D3AE6 and 0x021EE4F6.  Body (disassembled 0x021EE3DC..0x021EE4BA): rider chain kind<6 keys in list 0x0226FAB4 (bl @0x021EE418),
  zone word [+0x34] bit 22, kind-3 node 0x1B98, locators 0x2142 / 0xEAD / 0x1D14 / 0x1FEE / 0x200D (0x021A0950 / 0x021A09BC) -> return 1 = negated.
- Caller 1: 0x021D3AA0(desc) — returns 1 when the effect described by desc is negated: 0x021AB90C (activation-negated) short-circuits to 0;
  if desc[+3] <= 10 and the zone's instance id (zone word [+0x34] bits) == desc[+0xC] -> bl 0x021EE3DC(desc[+2], desc[+3]); else off-field:
  0x021A25E8(desc[+0xC]) word bit 22.  Its only BL caller is 0x021D442A, inside the resolution path: nonzero -> `strb #2, [desc+0xA]`
  (effect resolves as negated).  Disassembled 0x021D3AA0..0x021D3B0A and 0x021D4400..0x021D444E.
- Caller 2: 0x021EE4E4(side, zone, r2) — for zone <= 4 and r2 != 0, bl 0x021EE3DC first, then a list of field-card locators
  (0x1A6D, 0x1A9B, 0xE42, 0x201B, 0x21E3, 0x23A6, 0x1E66, 0x2142 …) -> "this monster's effects are negated" (continuous).
  It has 7 BL callers: 0x021EE984, 0x021EEC62, 0x021EEDA8, 0x021EEE56, 0x021EEEE2, 0x021EF1F4, 0x021EF438.
- => A front at 0x021EE3DC's two call sites (or a precheck on its entry path) covers BOTH resolution-time and continuous monster negation
  with one condition.  Restoration already fronts the list search @0x021EE418 inside it (PREB, chain head 0x023AAC30).

- Both call sites are UNFRONTED in rom_chain_18C00.nds and rom_monarch_all.nds (BL decode: 0x021D3AE6 and 0x021EE4F6 -> 0x021EE3DC).
- Native negation uses this gate: kind-2 "summoned by X" node + key in reader list 0x0226FAB4 (Level Modulation, Fire Ant Ascator; the
  recipe Obedience Schooled used, whole card confirmed by the user 2026-11-06 per memory otn-obedience-schooled).  So fronting 0x021EE3DC's
  callers gives Erupt the same semantics as native "effects negated".
- Skill Drain 0x166C's own references: 0x021EE7D0 (`bl 0x021AC204(0x166C)` = "cid face-up active on the field", then 0x021AC72C(cid) into
  state [r4+0x10/+0x14]) inside the continuous-effect scan that calls 0x021EE4E4 @0x021EE984; 0x021EDEE4 (a cid compare tree);
  0x021EF7CC (Skill Drain's own activation legality, `cmp 0x166C/0x23C3 ; bl 0x021AC9DC(0x1302)`).  Skill Drain is NOT on the 0x021EE3DC path.
- 0x021AC204(cid): scans both sides' zones (0x021A36EC cid-at, 0x021A32B4, zone flag [+0x44] bit 26 clear) -> generic "cid face-up and active".
- Donor candidate: Respect Play 0x135E (Continuous Trap, scratch/_spell_donors.py "Trap Card" Continuous: clean, undecked, unclaimed).
  Halfword scan of the stock ROM: 0 hits in ov3, 0 in ov5, 1 in arm9 @0x02059902 = an instruction (`adds r7, r2, #0`), not a literal.
  The only other result, Enervating Mist 0x1800, has 189 ov3 hits (0x1800 is a common constant; unusable as evidence).
- Strike donors (Quick-Play, clean+undecked): only Speed Spells 0x0DE4 / 0x0DF0 / 0x0DFF.  Domain donors (Field): Wasteland 0x10F1,
  Sogen 0x10F3, Umiiruka 0x1345, Mystic Plasma Zone 0x1349, Acidic Downpour 0x1D21 — these have native stat effects; donor_scan calling them
  "clean" is suspicious (the field-boost data may not be scanned).  Unresolved.

- Trace seed 1 (build/cpu_battery/gdb_er/er_1.json): NEG front hit 18,165 times (front IS on the live path), verdict 1 never (no face-up non-Tribute
  monster existed while a face-up Erupt was on the field: only a face-down 0x1E74).  COND hit 12x, all with side 0's Erupt ALREADY face-up in
  zone 7 (+8 = 1), ED counts [0, 0], no Tribute Summoned monster -> COND returned 0 (correct verdict).  Open: how Erupt got face-up before any COND
  hit (CPU activation path not calling cls0 +0C?) -> seeds 2-4 add COST/RES breakpoints.

- Trace seeds 2-4 (er_2/3/4.json, COST/RES breakpoints added) — CPU evidence, NOT in-game confirmation:
  * E1: the CPU activated Erupt in seeds 2 and 3 (COST 0x023B2790 then RES 0x023B2794, lr 0x0224AE6B / 0x0224AF03), both times with ED counts [0, 0]
    and Zaborg the Thunder Monarch 0x174D face-up with flags 0x00410108 (bit 3 = Tribute Summoned).  Before Zaborg arrived, COND (lr 0x0224AE13) was
    polled 9-30x with only non-Tribute monsters and no activation followed.
  * E2: after activation the NEG front returned 1 (via lr 0x021EE4FB, the continuous-check caller) for Wulf 0x1DAC (flags 0x4110, Special Summoned),
    Ehren 0x1E75, Lyla 0x1DA8, Alligator's Sword 0x129F, Garoth 0x1DA9 — on BOTH sides — and never for Zaborg 0x174D (bit 3 set).
  * Resolutions marked negated (0x021D4432, desc+0xA = 2) under a face-up Erupt: seed 2 Ehren 0x1E75 (side 0 zone 1); seed 3 Lyla 0x1DA8 (side 1
    zone 3) and Jain 0x1DA7 (side 0 zone 2).
  * Seed 2: Lyla face-up non-Tribute on side 0 zone 2 from t=5.3 while Erupt was still Set: no verdict 1 logged before the activation at t=14.8.
  * Oddity: the Set Erupt's zone +8 (face-up halfword) read 1 at every COND poll, before activation (flags word 0 -> 0x102 at COST -> 0x100).  The KB
    (ram.zone_record_faceup_flag) says Set = 0.  Likely the activation check flips it temporarily; the seed-2 point above says the negate did not
    fire while Set.  If the user sees negation from a Set Erupt, require zone flag bit 8 (0x100) on the Erupt zone too.

- (2026-11-11) er_1..4.json were deleted before the E3 trace run (my mistake); the E2 evidence above is the only record — re-run
  scratch/erupt_gdb.py with the old EV set to regenerate.

### E3 (built 2026-11-11, user: "Build E3 first")
- Section walker 0x022566F8 (registry rows 63..287, base pool 0x0228E3D8, bound 0xE1): 4 passes r5 = 0..3, [0x0229DD94] = r5 & 1 (the
  "which player" toggle), [0x0229AB7C+0x18] = (r5 >= 2); each row: `blx fn(r0 = r7 side, r1 = row cid)`; 0 -> return 0 (re-enter later), nonzero ->
  next row.  Pass 3 stops at the first 0x02255F41 row.  Disassembled 0x022566A0..0x0225672C.
- Row 277 @0x0228EA88 = {0x02255959, cid 0}, rows 278/279 = {0x02255959, 0x2192 / 0x21DA}; stock in rom_chain_18C00 and rom_monarch_all (read
  2026-11-11); 0x02255959 appears as a literal ONLY in those three rows.  No module touches them.
- Send primitive: 0x021CF6B8(desc, side, zone) = 0x021CDD4C(desc, 1 << (side*16+zone), 0x0E, 0x1000) — NAST's SEND_TO_GY (whole card in-game
  confirmed).  0x021CDD4C copies the 0x24-B desc to 0x0229DE34, ORs the mask into [0x0229C294+0x7C], dest -> [0x0229DE14+0x44]: QUEUED.
  The walker's own maintenance destroy (0x021CF35C -> 0x021CF31C builds a fake desc {cid, side, 0|5, 0x24}) is queued the same way and returns 0.
- Build: CAVE_ER_EP 0x023B2910 (0x100 B, 0xEC used), CAVE_FREE 0x023B2A10; row 277 fn -> CAVE_ER_EP|1; rom_erupt.nds sha256
  93b9f2a150e01a55da55d5b95fb172e4f94ee170440758377def7078a62dd4e2 (19/19); rom_monarch_all.nds sha256
  0a52d47ff09d67e1a3f0b65e00153e0c64c3f51c3c39e48f92ef5c27edab8159 (erupt 19/19).
- Trace (build/cpu_battery/gdb_er/run_noforce/er_2/3/5.json, rom_monarch_all 0a52d47f…): the CPU activated Erupt in all 3 seeds (with Zaborg
  Tribute Summoned).  ER_EP entered with r0 = the TURN player, phase [0x0229DD14+0x48] = 5, four calls per End Phase (toggle/round2 = 0/0, 1/0, 0/1,
  1/1), only on turns of Erupt's controller while Erupt was face-up (seeds 2, 3, 5: 1, 4, 2 End Phases).  Zaborg (flag bit 3) stayed on the
  field every time -> no SENDGY, Erupt stayed (correct negative).  Positive case not reached naturally -> forced run (GDB clears bit 3 on every own
  monster at the first pass-0 EP hit), scratch/erupt_gdb.py ... --force.
- FORCED POSITIVE (build/cpu_battery/gdb_er/er_2.json, er_5.json, `--force`): at the first pass-0 ER_EP hit GDB cleared bit 3 on Zaborg
  (0x40C10108 -> 0x40C10100).  Both seeds: ONE SENDGY (0x021CF6B8 from lr 0x023B29C1, side 0, zone 7, desc 5e130005 24000000), and the very
  next ER_EP call (same End Phase, t+0.0 s) shows 0x135E as the newest GY card and zone 7 empty; the remaining passes (1/0, 0/1, 1/1) ran, no stall,
  duel continued (seed 5 activated a second Erupt later).  So: the queued move executes before the re-call (PROVEN), pass 0 runs at phase 5
  = End Phase on Erupt's controller's turn (PROVEN), a Set Erupt (seed 5 side 1, +8 = 0) is ignored.
- Side effect seen: Wulf's flags 0x40C04150 -> 0x40C04110 when Erupt left (bit 6 cleared) — consistent with the negation lifting.  Not studied.

## Ruled Out (do not retry)
- 0x021AB90C as a continuous negate: it is the ACTIVATION-negated check (inherited, see the Monarch prompt).
- Patching the giant legality function around 0x021EF7xx for a second Skill-Drain arm: Skill Drain is NOT on the 0x021EE3DC path at all (its references
  are the continuous-effect scan 0x021EE7D0, a cid tree 0x021EDEE4 and its own activation legality 0x021EF7CC).
- E3 through an arm inside the maintenance walker's compare tree @0x022559E2 (a branch-site patch): not needed — re-pointing registry row 277's fn is a
  pure data edit and was traced working.
- E3 with the walker's maintenance DESTROY 0x021CF35C: the text says SEND; 0x021CF6B8 (NAST's send) is the right primitive.

## Open Questions
- Does a negated monster still get its ignition/trigger OFFERED (then resolve negated, desc+0xA = 2)?  That is the native behaviour of every kind-2/3
  "negated" rider (Level Modulation, Obedience Schooled); the CPU trace only proves the resolution half.  HYPOTHESIS until the user's test.
- The Set Erupt's zone +8 read 1 during every COND poll (KB says Set = 0); the CPU trace showed no negation before activation.  If the user sees a Set
  Erupt negating, add "zone flag bit 8 (0x100) set" to ER_TEST's Erupt-zone check.

## Next Experiment
- THE USER'S IN-GAME TEST of rom_monarch_all.nds sha256 8a2c7b73aa5e1551eba3f087d0b6e3f9b0db60b9d682e6844d6da7354116e690 (Erupt + Strike + Domain).
  Steps and pass/fail readings: PROMPT_monarch_erupt_domain_strike.md, "The in-game test".
