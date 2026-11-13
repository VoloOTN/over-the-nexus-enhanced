# Coral Dragon — findings (live)

Session 2026-11-09. Donor chosen by user: **B. Skull Dragon 0x107F** (effectless Fusion, Lv9 DARK Dragon 3200/2500;
user explicitly accepted the ATK > 1500 breach of the donor rule). Status: **NOTHING BUILT. AWAITING DESIGN APPROVAL.**

Printed text (`scratch/ygoprodeck_cache.json`, read this session; NOT in NDS or 3DS card pool, so no reference impl):
Coral Dragon — Synchro Tuner Effect, Lv6, WATER, Dragon, 2400/500.
```
1 Tuner + 1+ non-Tuner monsters
Once per turn: You can discard 1 card, then target 1 card your opponent controls; destroy it.
If this Synchro Summoned card is sent from the field to the GY: You can draw 1 card.
You can only use this effect of "Coral Dragon" once per turn.
```
| # | Clause |
|---|---|
| C0 | Synchro Tuner Effect Monster identity, 2400/500 Lv6 WATER Dragon, 1 Tuner + 1+ non-Tuner |
| C1 | OPT ignition: discard 1 card (cost), target 1 opp card (monster OR S/T), destroy it |
| C2 | If Synchro Summoned and sent field->GY: may draw 1. "Only use this effect once per turn" = this clause (reading assumed) |

## Confirmed (this session)
- cid 0x107F; name budget EU 15 chars ("Coral Dragon" = 12 fits); desc floor 30 (new text far longer -> needs a `card_text.CARD_TEXT`
  entry for the index-order re-emit, no slot limit). Source: `donor_scan.cards()`.
- `donor_scan 0x107F` = ENTANGLED by exactly one binding: **fusion recipe A[16] @ov3 0x02270C14**, stock
  `(0x107F, 0x0FBC Summoned Skull, 0x0FF8 Red-Eyes B. Dragon, 0)` (read from ov3 image) -> `fusion_recipe_blanked(row=16, stock=...)`.
- **Archfiend set-code list** (thunk 0x01, base 0x0209CF90, 42 entries) holds 0x107F at **index 3** (@0x0209CF96);
  neighbours `[2]=0x1070, [4]=0x10AB`. Coral Dragon must stop being an "Archfiend" -> `set_code_slot_to_phantom(base=0x0209CF90, count=42, index=3, phantom=<0x1070 dup or free phantom in (0x1070,0x10AB)>)`.
  (KB `setcode.archfiend_*` already records the list.)
- The 5 other ARM9 u16 hits (0x0209876C, 0x02099344, 0x0209946C, 0x02099560, 0x020995FC) are neighbouring `0xE211/E212 ... 0xE12FFF1E` words = ARM instruction
  encodings (`tst/and ..., #imm`, `bx lr`), not cid tables. Judged from the surrounding halfwords, not by disassembly proof.

## Precedents located (UNVERIFIED as fit until read in full)
- Conversion Fusion -> Synchro Tuner Effect: `life_stream_dragon.py` (Steam Gyroid 0x18FA): `fusion_recipe_blanked` + `card_prop_copied_from_template(ref_cid=0x239E,
  card_type="Synchro Tuner Effect Monster", donor_genre=0x0000000020200000, new_genre=0x0000001800200000)` + `card_props(...)`.
- cls3 ignition on an Extra-Deck Fusion donor: `accel_synchro_stardust_dragon.py` (Meteor B. Dragon 0x126F), C2 Quick Effect, confirmed by user 2026-09-14 (per its findings).
- Discard-1-as-cost ignition targeting a field card: `uni_zombie.py` C1 (donor is non-Normal; check whether it ports to a cls3 on a Fusion donor).
- Leave-field hook on an Extra-Deck donor: dsl `synchro_materials_..._revive_shooting_star_dragon_on_leave` (`shooting_quasar.py`).
- Destroy primitive on an opponent card (monster or S/T): needs a precedent still — candidates Grapha C2, Dark Law, Eclipse Wyvern.

## Pre-build risk checklist (CLAUDE.md)
1. Per-cid gates on 0x107F: **PROVEN** for data tables (recipe A[16] + Archfiend list idx 3, above). **ASSUMED** for `base +/- imm` stack switches
   (donor_scan cannot see them; no one has scanned ov3 for them for this cid).
2. Zone: C1 must reach opp monster zone AND S/T zone; leave-field detection must see the Extra-Deck donor. Both **ASSUMED** — no disassembly read yet.
3. Blob lengths: name **PROVEN** (12 <= 15). Desc handled by CARD_TEXT re-emit (**PROVEN as the mechanism per CLAUDE.md**, not yet exercised for this cid).
4. OPT flag: C1 latch in cost / checked in condition (ignition DSL shape); C2 needs its own latch. Where stamped: **ASSUMED**, decide at design.
5. "If Synchro Summoned" persistence through to the leave-GY event (is there a per-instance summon-type flag the leave hook can read?): **UNPROVEN**.

## Ruled Out
(none yet)

## Open Questions
- Does the C2 draw need the card to have been Synchro Summoned *and still be the same instance*, i.e. what flag does the engine keep? (check Shooting Quasar revive-on-leave and Revolution/Jet Synchron)
- Free phantom for the Archfiend slot, or a duplicate of [2]=0x1070 (list stays sorted, count unchanged).

## Next Experiment
Read `shooting_quasar.py` leave hook + `uni_zombie.py` C1 + Grapha C2 destroy; prove (disasm) the target-selection criteria row can cover opp monster + S/T zones; then present PROVEN/ASSUMED table to user before writing the module.

---
## Session 2026-11-09 (part 2): precedent reading

### Confirmed (read this session from KB yaml + disassembly; nothing built)
- **C1 destroy half has an in-game-confirmed precedent**: Grapha C2 (cards.yaml ~l.354, user-confirmed 2026-08-28) = "Target 1 card your opponent controls; destroy that target":
  target picker `0x02234DA5` (cls +14), filter `0x021DE7C9` (Goldd's "cards your opponent controls"), destroy resolver `0x02204899`.
  Covers opponent monster AND Spell/Trap by the filter's wording; zone coverage itself not re-disassembled this session -> still check before claiming.
- **cls3 reaches Extra-Deck donors** (KB `dispatch.cls3_reaches_extra_deck`-style fact at effect_dispatch_tables.yaml ~l.3869; Armory Arm, Accel Synchron are shipped on it).
  So C1 as a cls3 ignition on 0x107F is structurally supported.
- **Discard cost**: native cls3 cost `0x021E8FD4` = `0x0225991C(side,1,r2,r3)`; disasm 0x0225991C: r2!=0 -> mode 1 (Effect), r3!=0 -> mode 7 (Spell), both 0 -> mode 0, and
  0x02259934 then sets flags only `0x10` for mode 0 -> request `0x0225985C(side,2,mode,flags)`. Candidate "discard 1 card (any)" cost = `0x0225991C(side,1,0,0)`.
  **UNPROVEN** that mode 0 means "any card" and that the cost window works with it: no shipped card is known to call it that way (Uni-Zombie discards on RESOLUTION via 0x022598A1, not as cost).
  KB `dispatch.discard_window_pickers_and_the_freeze`: hooking the discard window's legality callbacks FREEZES the game -> do not hook them.
- **"Synchro Summoned" proxy**: card-word bit 15 = PROPERLY SUMMONED (KB `summon.card_word_bit15_is_properly_summoned`, VERIFIED, 0x021A2618; measured on a Synchro Summoned Iron Chain Dragon).
  A Synchro that is on the field and has bit 15 set was Synchro Summoned (a revived-from-GY Synchro has it clear). **Not proven** that the leave dispatcher has this word readable
  (the card is leaving; the descriptor slots [sp+0x90]/[sp+0x44]/[sp+0x144] are documented, a card-word slot is not).

### Ruled Out
- **Reusing the shared T.G./Quasar leave trampoline as-is for C2.** Disassembled `tg_table._shared_arm_trampoline`: on a cid-list match it requires `[sp+0x90]` (DESTROYED)
  and then branches either to Quasar's one hard-coded IMMEDIATE_CID stub or to the T.G. End-Phase gate. Coral C2 says "sent from the field to the GY" (any cause, e.g. as Synchro
  material/cost), and needs an OPTIONAL draw, so neither branch fits. It needs a new branch (extend the shared trampoline; byte-identical-install constraint) or a different hook.
- cls2 leave record as the route: KB says cls2 never reaches Extra-Deck donors for the LEAVE enumeration (3 row shapes A/B vs Reborn Tengu, Quasar session). Root cause was never found
  (those probes may have lacked a leave-mask row; not checked).

### Open Questions (C2 is the hard clause)
1. Where to read "was Synchro Summoned" at leave time (dispatcher stack slot or by cid+field slot lookup before the card is removed).
2. How to offer an optional Yes/No from inside the leave dispatcher (re-entrancy; Quasar's stub drove a Special Summon from there but had no prompt). Fallback: latch a flag and post the
   prompt at a later safe point.
3. Mask bits wanted if a mask-row route is feasible: 0x0001 you control + 0x0004 left field + 0x0800 dest GY = **0x0805** (Pinch Hopper's value). Whether Extra-Deck cids honor it is the unknown.
4. Which stack-switch (`base +/- imm`) gates mention 0x107F: not scanned.

### Next Experiment
(a) Read the leave dispatcher 0x021C7FD0..0x021C8216 for where the departing card's word/pointer lives; (b) check how Reborn Tengu's mask row 0x000C row is consulted and whether it is a
cid-gated path that would skip an Extra-Deck cid; (c) disassemble a native any-card discard COST (search cls3 cost slots for callers of 0x0225991C with r2=r3=0).

---
## Session 2026-11-09 (part 3): leave-hook RE (static disassembly of ov3 image; no emulator)

### Confirmed
- **"Synchro Summoned" IS readable at the leave hook.** Leave dispatcher 0x021C7FD0: `0x021C7FD8 str r1,[sp,#4]` keeps arg 2 = POINTER TO THE LIVE FIELD SLOT; 0x021C7FE8 `ldr r2,[r1]` loads the card word
  (cid = bits 0-13 -> r4 = what the hook compares; bit 14 -> [sp+0x98] controller; `[r1+8]` halfword -> [sp+0x94] face-up). Its sole caller 0x021CD2AC passes
  `r1 = [sp+0x6c] + [sp+0x30]` where (caller 0x021CC290 prologue, 0x021CC2C4..0x021CC2E0) `[sp+0x6c] = 0x0229AC94-based player + 0x34` and `[sp+0x30] = slot*0x14`, i.e. the slot struct
  `0x0229AC94 + side*0xB3C + 0x34 + slot*0x14` (same layout KB documents for 0x021A241C). Nothing between 0x021C7FE8 and the hook 0x021C8216 writes that slot (only reads / bsearch calls seen in
  0x021C7FD0..0x021C8120). => at the hook, `([sp+4]) -> word; (word>>15)&1` = PROPERLY SUMMONED (KB `summon.card_word_bit15_is_properly_summoned`). For a Synchro that is the Synchro Summoned test.
  Residual risk: I did not read 0x021C8120..0x021C8216; only 'no writes seen' in the disassembled stretch.
- Hook-time descriptor slots for C2: GY destination `[sp+0x144]`, left-field `[sp+0x2C]`, controller `[sp+0x98]`, destroyed `[sp+0x90]` (unpack at 0x021C7FD6..0x021C8052, read this session).
- Trigger posting: gate 0x021CA640 (terms [sp+0x2C]!=0, r6==[sp+0x98], [sp+0x144]!=0) -> `0x021D2584(side,cid,2,[sp+0x9C])` -> `0x021C479C(side,0xB,cid,..)` = posts a leave event record (event 0x0B).
  Consumption goes via the cls2 binary search `0x0224A118` (read prologue only: bsearch of 24-byte rows @ a literal base, then a 19-entry list test `movs r2,#0x13`@0x0224A1AE).
  I did NOT find why Extra-Deck cids are never matched (not read past 0x0224A1C0).
- The engine's own optional prompt `0x0219AAAC` is a **phase-driven** prompt (raised in a resolver phase, answer read in a later phase from [0x0229DD94+0x34]) -> it can NOT be called synchronously from a leave-hook stub.

### Consequence for C2 (design options, none built)
A. Immediate stub on the shared leave trampoline (Quasar pattern, in-game proven for a MANDATORY Special Summon): checks Synchro-Summoned bit + GY dest + controller, then draws. No Yes/No -> printed "You can" would
   become mandatory. By CLAUDE.md that is a bug unless the user accepts it.
B. Make the posted event 0x0B reach a real cls2 optional record (clean "You can" prompt). Blocked by the unexplained Extra-Deck cls2 miss; needs the rest of 0x0224A118 / its caller read, or a savestate A/B.
C. Ship C0+C1 first, C2 later.

---
## Session 2026-11-09 (part 4): the "cls2 miss" is probably a CONFOUNDED A/B, not an Extra-Deck exclusion  (hypothesis H1, UNPROVEN)

### Evidence (static, read this session)
- The Quasar A/B that produced "cls2 leave-dispatch NEVER happens for an Extra-Deck donor" is dated **2026-07-20** (memory otn-leave-trigger-cls2). The finding that **a cls2 row alone is NOT the trigger — the
  dispatcher must arm `[sp+0x18]` via a leave-MASK row / list / dedicated arm** is dated **2026-08-24**, i.e. AFTER. The Reborn Tengu control 0x2085 had its own dedicated arm (Minefieldriller, body 0x021C8CC4);
  Quasar had neither a mask row nor an arm. `LEAVE_MASK` is not used by any Extra-Deck module (grep: only block_dragon, eva, gravekeepers_recruiter, dragon_rulers use it). So the control and the test
  were NOT equivalent: the "never consulted" result is explained by "never armed".
- Nothing in the arming/consumer path reads the card TYPE as an Extra-Deck exclusion: tail 0x021C93CE.. only calls `0x02029E60(cid)` (= IS_MONSTER, bit 15 of card_prop; true for Synchro/Fusion) and
  destination/controller slots; consumer 0x021CA980 switches on [sp+0x18] = 1/2/3 (variant), and caller 0x021CD2B0 posts message 0x17/0x1D via `0x022391CC`. No type gate seen.
  (Not read: 0x021C8120..0x021C8216 mask-row evaluation beyond the bsearch call at 0x021C8104; and the message consumer that finally looks up the cls2 row.)
- Mask row consulted at exactly one site, 0x021C8104 (`bsearch(cid, table 0x0226EC1C, 0x98 rows, stride 4)`), disassembled this session; table is FULL (0x98) -> a row needs a phantom (Row(LEAVE_MASK, ...) in dsl).
- Precedent shape for our wording ("sent from the field to the GY"): Gravekeeper's Recruiter = `{cid, 0x0800}` + cls2 `CLS2_SEARCH_RESOLVER` record + criteria row 1389 (3 phantoms) — Normal donor, confirmed.
  Eva / Block Dragon also use `Row(LEAVE_MASK, ...)`.

### Proposed design for C2 (NOT built; needs approval)
leave-MASK row `{0x107F, 0x0800}` (phantom) + cls2 record with an OPTIONAL "You can" shape (`+10 0x021E51E5`) and a condition that tests the Synchro-Summoned bit + resolver = draw 1.
Open sub-questions: (1) does the cls2 CONDITION still see card-word bit 15 once the card is in the GY? (KB measured it surviving in the banished zone, GY unverified); (2) OPT latch for the draw;
(3) single-card test ROM is the experiment that settles H1 (expected: mask row makes the Extra-Deck donor's cls2 resolver fire, like Tengu); Fusion-donor type 0x107F is `Fusion Monster`->Synchro conversion.

### Next Experiment
Single-card ROM (no chain): Coral Dragon C0 + C2 only. Mask row + cls2 optional-draw record, instrumented with an ov5 counter (CAVE_*) incremented in the condition and the resolver, then ask the user to Synchro Summon it
and destroy it. Savestate read: counter(cond) > 0 => H1 true.

---
## Part 5 — user hint: "like Card Trooper / Mathematician, but only armed when Synchro Summoned"  (2026-11-09)
Native rows read from the ov3 image this session (donor_scan 0x1B1B / 0x1A07, struct dump):
- **Card Trooper 0x1B1B** (text: "If this card you control is destroyed and sent to your GY: Draw 1 card"): leave-mask row[54] `{0x1B1B, 0x0C05}`, cls2[232] `{0x022065B9 draw, 0, 0, 0, 0}` (mandatory), draw-count row `{0x1B1B, 1}`.
- **Cyber Phoenix 0x1A07** (optional): leave-mask `{0x1A07, 0x0890}`, cls2[205] `{0x022065B9, 0, 0x021F069D, 0x021E51E5, 0}`, draw-count `{0x1A07, 1}`.
- Mathematician (confirmed 2026-09-14): same cls2 transplant + draw-count row, armed by list106 instead of a mask row.
=> **C2 is expressible as pure data** (3 phantoms: leave-mask, cls2, draw-count): mask `{0x107F, 0x0805}` ("you control it" 0x0001 + left field 0x0004 + dest GY 0x0800; Pinch Hopper's value; drop 0x0400 DESTROYED because Coral says "sent to GY", any cause),
  cls2 `{0x022065B9, 0, <cond>, 0x021E51E5, 0}` (optional), draw row `{0x107F, 1}`. This also confirms H1: the dispatcher is armed by the mask row, which Quasar's 2026-07-20 A/B never had.
- "ONLY when Synchro Summoned" = the one non-native part: `<cond>` = small stub `bit15(card word) && 0x021F069D(desc)`; native 0x021F069D alone would offer it for any departure.
  Open: (a) does cond receive something from which the card word is reachable once the card is in the GY (desc zone/slot -> GY array entry; KB measured bit 15 surviving in the banished zone, GY unverified)?
  (b) mask 0x0805 vs 0x0800 (GK Recruiter used 0x0800 and fired on Tribute AND Synchro Material alike - consistent with "any cause").
  (c) OPT: "You can only use this effect once per turn" is moot for a card that can leave once per Synchro Summon, so no latch planned (state this to user).

---
## Part 6 — BUILD 1 (C0 + C2), 2026-11-09 — AWAITING IN-GAME TEST (not user-confirmed)
Module `otn_enhanced/cards/coral_dragon.py` (DSL). Single-card ROM `data/over_the_nexus/working/rom_coral_dragon.nds`, sha256 `a3d72a1cf6a0a0633b09204df7024aad0b88e0b98a16637e7c34cacb51381244`
(layered on rom_ov3_compact.nds = stock + step 0; NOT on the chain, NOT in steps.STEPS). `--verify`: **25/25 passed**. check_allocations: clean (765 ov5 slots, 689 phantom claims, ledger in sync).
Claims: ov5 `CAVE_CORAL_C2COND 0x023AEA70` (0x70) + `CAVE_CORAL_DBG 0x023AEAE0` (0x10), CAVE_FREE -> 0x023AEAF0 (inside RESERVE ceiling 0x023AED20);
phantoms: cls2 0x234D, draw-count 0x1AE9, leave-mask 0x194A (each free in its OWN table); donor 0x107F; recipe A[16] blanked; Archfiend list idx 3 -> dup 0x10AB.
Rows: cls2 {0x107F,0,0x022065B9,0,COND|1,0x021E51E5,0}; draw {0x107F,1}; mask {0x107F,0x0805}. card_prop copied from Formula Synchron 0x239E, genre 0x0000001800200000.
NOT built: C1 (discard + destroy ignition). NOT run: CPU mirror duel (5b), full verify sweep, chain build.
Unproven (that the in-game test answers): (1) mask row arms the leave dispatcher for an Extra-Deck donor (hypothesis H1); (2) desc[+0xC] is a valid card ref for the leave-trigger desc and `0x021A2510` finds it in the GY;
(3) bit 15 of the GY array word is set after a proper Synchro Summon and survives into the GY; (4) prompt appears and draw works.
Savestate readout: DBG @0x023AEAE0 = {calls, last GY word, idx, desc[+0xC]}; calls==0 => dispatcher/cls2 never consulted (H1 false); idx==-1 => ref wrong; word bit15==0 => flag lost.
In-game steps: Extra Deck Coral Dragon; (a) Synchro Summon it (Tuner + non-Tuner, Level 6), destroy it (e.g. Dark Hole) -> expect Yes/No "draw 1"; (b) Synchro Summon it, send it as cost/material elsewhere -> same;
(c) negative: get it into the GY without Synchro Summoning (e.g. revive via Call of the Haunted then destroy) -> NO prompt; (d) check Coral Dragon no longer counts as "Archfiend".

---
## Part 7 — BUILD 2 (C0 + C1 + C2), 2026-11-09 — AWAITING IN-GAME TEST (not user-confirmed)
`rom_coral_dragon.nds` sha256 `7d227b5c23dfec4ecebbb1374fa0ab834cdc9b47e1784e8ee51b05e24c57d1b5`, `--verify` 32/32, check_allocations clean (ledger re-emitted).
### C1 design (read this session from the cls3 table + disassembly)
- **Native exact precedent**: XYZ-Dragon Cannon 0x15B4 (cls3) = `{res 0x02204899, filter 0x021DE7C9, cond 0x021F0221, cost 0x021E4EA5, picker 0x02234DA5}` = "discard 1 card; destroy 1 card your opponent controls".
  Elemental Hero Thunder Giant 0x18C9 / Desert Twister 0x1C2B / Frost and Flame 0x1C2A use the once-per-turn pair cond 0x021F024D + cost 0x021E4ECD.
- **Those two are NOT cid-blind**: they take the discard COUNT from `0x021E4C60`, a per-cid function (bsearch list 0x78 + `0x0202353C` + a cid switch returning 2/5, default **0**); an unlisted cid would discard 0 = free effect.
  So Coral gets its own stubs (ov5 `CAVE_CORAL_C1COND 0x023AEAF0`, `CAVE_CORAL_C1COST 0x023AEB30`), cloned from Chiron's cost 0x021E8FD4 / cond 0x021F7375 shape with discard mode = ANY:
  cost = `0x021E5060(desc)` (OPT node 0x0FB6 stamp, cid-blind: disasm'd) then `0x0225991C(side,1,0,0)` (r2=r3=0 -> mode 0, flags 0x10; native caller 0x021E4EC2 uses the same (0,0) for N-card discards);
  cond = `!0x021A1430(side,desc[3],0x0FB6)` && (`0x021D2BC8()` || `0x021EFF30(side,1,desc[+0xC],0)`) (same calls as native 0x021F024C -> 0x021F0220 with the count fixed at 1).
- cls3 row `{0x107F, 0x02204899, 0x021DE7C9, COND|1, COST|1, 0x02234DA5}` over phantom cls3 0x1BCE. Template slots of 0x15B4 asserted at build; tag literal @0x021F0278 == 0x0FB6 asserted.
- Proven-by-precedent: cls3 reaches Extra-Deck donors (ASSD, Armory Arm); filter 0x021DE7C9 + picker 0x02234DA5 + destroy 0x02204899 = Grapha C2 (in-game confirmed 2026-08-28).
- **UNPROVEN / the in-game test answers**: (1) mode-0 discard window offers any card from the hand and the cost completes (no shipped card is known to use mode 0 as an ignition cost; XYZ-Dragon Cannon's 0x021E4EA5 goes through 0x021E4C60's count);
  (2) the picker/target step runs AFTER the discard cost as printed ("discard 1 card, THEN target"): native ordering puts the target declaration (+14) relative to cost (+10) as the framework decides -- not checked;
  (3) opponent's Spell/Trap zone is reachable by filter 0x021DE7C9 (Grapha C2 was only confirmed on... unchecked); (4) OPT: second activation in the same turn must be refused.
- Printed once-per-turn for C1 ("Once per turn:") handled by the OPT node; C2 has no latch (see Part 5).
### In-game test (C1)
Own Main Phase with Coral Dragon face-up, opponent has a monster AND a Spell/Trap, you hold >=1 card: (a) activate -> choose a discard (any card type, incl. a monster and a Spell) -> choose target (try both a monster and a face-down S/T) -> destroyed;
(b) try again same turn -> not offered; (c) hand empty -> not offered; (d) opponent controls nothing -> not offered / no discard taken.

---
## Part 8 — CPU check (step 5b), 2026-11-09 — emulator CPU evidence, NOT user-confirmed
- **Phantom correction**: cls2 phantom 0x234D was ALREADY SPENT in the chain image (rom_all_patches.nds) by `tg_warwolf` (phantoms=(0x234D,0x234A)) although the ledger did not show it for cls2_table
  -> the ledger said "free", the chain build would have aborted (`phantom 0x234D not present to drop`). Switched to **0x1B46** (present + unclaimed in BOTH stock and chain ROMs; checked with scratchpad phchain.py).
  The other three (draw 0x1AE9, mask 0x194A, cls3 0x1BCE) are present in the chain image. LESSON (matches memory otn-register-phantom-same-edit): check phantoms in BOTH images; a ledger-clean build is not a chain-clean build.
  Possible ledger gap to fix by whoever owns it: tg_warwolf's 0x234D drop from cls2 is not claimed under `cls2_table`.
- Current ROMs: stock-layer `rom_coral_dragon.nds` sha256 `21b00a6aaffbdc902015f3826aeada45503823cb231011361c14004a3c45572d` (supersedes the Part 6/7 hashes; verify 32/32);
  chain-layer `rom_coral_dragon_chain.nds` (= rom_all_patches.nds of 2026-11-09 11:46 + Coral, built ONLY to carry the View Mode runtime the CPU rig needs; NOT a shipped chain) sha256 `c5df4cb9bbeb067f65add541963522695281c9f045d4287163a74935fa07f5cf`, verify 32/32.
  The rig needs `SD11` View Mode runtime in the ROM (only rom_all_patches.nds-derived ROMs have it; rom_ov3_compact.nds does not).
- cardtest rows 0x107F: no ov5 CPU row (monster donor: expected).
- Tool change: `cardtest.py mirror` now (a) keeps an Extra Deck card out of the Main Deck and (b) counts Extra slots (60+i) -- before, an Extra Deck cid was put x3 in the Main Deck and its stats were never read.
- **Mirror, 8 duels (16 decks), kit Quillbolt Hedgehog x3 + Nitro Synchron x3 + Lightsworn filler, Extra = Coral Dragon: summoned 8, activated 0** (kit 172 drawn / 79 summoned / 101 activated).
  Precedent in the same tool: Ophrys 0x17CF summoned 8 / activated 8, so the CPU CAN activate a donor monster's ignition. Coral Dragon is summoned and NEVER activated -> **a defect until explained**.
  Not explained yet. Counter-hypotheses to test: (a) the CPU never reaches a legal cost (any-card discard mode 0) / cond for an Extra-Deck cid; (b) the CPU's target evaluation for cls3 +14 picker; (c) opponent had no card at the time (unlikely over 8 summons);
  (d) activation counter keys on something an Extra slot lacks (summons did count, so unlikely). C2 (draw) cannot show up in this mirror (needs Coral destroyed after a Synchro Summon).
- Next experiment: instrument C1 cond/cost with an ov5 counter (like CAVE_CORAL_DBG) and read it from a savestate/GDB-free mirror dump, to see if the CPU ever CALLS the cond; if calls>0 and cond returns 0 -> bug in the stub; if calls==0 -> CPU planner skips it (donor-specific CPU gate; look at ov5 planner for cls3 monster rows).

---
## Part 9 — CPU instrumentation, 2026-11-09 (emulator CPU, NOT user-confirmed)
- Added C1 counters `CAVE_CORAL_DBG1 0x023AEBD0` {cond calls, cond yes, cost calls}; re-homed `CAVE_CORAL_C1COST` to 0x023AEB90 (0x40) because the Block Dragon session had meanwhile claimed `CAVE_BD_GYRES 0x023AEB60` right behind my slots
  (CAVE_FREE now 0x023AEBE0; check_allocations clean: 769 ov5 slots, 690 phantom claims). Standalone ROM `rom_coral_dragon.nds` verify 33/33 (sha256 changed again -- re-read it with sha256sum, do not trust earlier hashes).
- The counters cannot be read back from a cardtest mirror (only deck-slot stats are returned); they are for a savestate / user-side read.
- **A/B diagnostic ROM** (`CORAL_C1_DIAG=cond1` makes the C1 cond return 1 unconditionally; env-gated, default OFF, `rom_coral_dragon_diag.nds`, same mirror, same seeds): **identical result** to the normal build:
  Coral summoned 8 / activated 0, kit 172 / 79 / 101 (all counters equal). => the cond's answer does not matter to the CPU: **the CPU planner never gets as far as asking our cond** (or reaches the activation another way).
  So the "never activated" result is a CPU-side gate on this card, not evidence that the cond/cost stubs refuse. It says nothing about human play.
- Ruled out: "cond returns 0 for the CPU" (forcing it to 1 changes nothing).
- Open: what makes the CPU consult a cls3 monster ignition (Ophrys 0x17CF is activated 8/8; its wiring is virtual rows + cls1/cls3 in dsl); is there a CPU-planner cid/zone list (ov5, `ai_row_at 0x023359C0`, Extra-Deck monsters?) that an Extra-Deck donor is simply absent from.
- Next experiment (only if CPU play matters): GDB one-shot per CLAUDE.md preflight, break at the CPU's cls3 enumeration for a native ignition monster vs 0x107F; or diff against a native Extra-Deck monster with a cls3 ignition that the CPU DOES play. Not started.

---
## Part 10 — CPU dig: GDB session (private port 3340, melonDS interpreter, user's own melonDS untouched), 2026-11-09
Harness: `scratch/coral_gdb.py <chain rom> <seed idx> <timeout>` (copy of scratch/grass_gdb.py; breakpoints on the three Coral stubs + the effect enqueue 0x021D2FC4 filtered to cid 0x107F).
- Run 1 (seed idx 1, 540 s, NOT finished -- interpreter is slow): **the C1 cond WAS called, once, at t=39 s**: r0 = 0x027E3650, LR = 0x0224AE13 (inside the ov3 find_event_handler/enumeration region, same area as 0x0224AD94),
  desc bytes `7f10 00 02 09 03 0000 00000000 5200 0100` => desc[0..1]=0x107F, desc[2]=side 0, desc[3]=0x02, desc[+0xC]=0x0052. No return event was logged before the timeout and no enqueue of 0x107F.
  Correction to Part 9: "the CPU never asks our cond" is NOT established (the A/B showed the cond's answer did not change the mirror, but the cond is reached at least once). What is unknown is its return value and what the caller does with it.
- Run 2 (seed idx 2, 1700 s) is running in the background to completion; results will be appended below.

---
## Part 11 — FREEZE found from the user's savestate (2026-11-09) — FIXED IN BUILD, AWAITING RE-TEST (not user-confirmed)
User report (verbatim): "I think it froze i made a savestate for you" ... "I made a savestate on your own private emulator" ... "The savestate is build/cpu_battery/cardtest_coral_gdb/gdb_coral/battery.ml1, this one. I made it"
(the savestate came from the private GDB-harness worker, ROM = rig_rom_coral_dragon_chain.nds, NOT the user's own play-test).
### Confirmed (read this session from the savestate; copy at scratchpad coral_gdb.ml1; RAM offset 0x24)
- Stubs in the savestate are byte-identical to the build (C1cond / C1cost / C2cond == chain ROM): not the savestate-restores-old-ov5 trap.
- `CAVE_CORAL_DBG1 0x023AEBD0` = {cond calls 1, cond yes 0, cost calls 0}: the C1 cond ran once and never reached its "yes" path.
- ARM9 section (tag 'ARM9' @file 0x1018d7f): **CPSR = 0x40000097 = ABORT mode (0x17), I set**; PC-slot = 0xFFFF0108 (BIOS exception loop); R14 = 0x021D2BD4; SPSR_abt = 0x4000003f (Thumb SYS), LR_abt-slot 0x023AEB0F.
  R14 = 0x021D2BD4 = 0x021D2BCC + 8 = a DATA ABORT at `ldrb r0,[r5,#4]` = the FIRST instruction of `0x021D2BC8` after `adds r5,r0,#0`.
  (Layout of the CPU section was deduced by inspection, not from melonDS source -- the field order is my reading; the abort mode + 0x021D2BD4 + the stub's BL site 0x023AEB0A all agree.)
- ROOT CAUSE (mine): `_c1_cond_stub` called `0x021D2BC8` with r0 = the result of the OPT-tag query (0), not the desc pointer; the native caller 0x021F0220 passes desc in r0, and 0x021D2BC8's first act is `ldrb [r0,#4]`
  (reads desc[4] == 0x25 test). Fault -> abort vector -> hard freeze. Disassembly of the built stub confirms: `0x023AEB06 cmp r0,#0 ; bne ; 0x023AEB0A bl 0x021D2BC8` with no r0 reload.
- This would freeze a HUMAN duel too, as soon as the engine evaluates clause 1's condition (the activation menu / CPU enumeration both call it) -- so the earlier "CPU never activates" and the
  one-call GDB log are explained by this crash, not by a CPU-planner gate. Part 9's "cond forced yes changes nothing" and Part 10 are SUPERSEDED: the forced-yes diag skipped the faulting call.
  UNEXPLAINED: the earlier non-GDB mirror duels (8/8) completed with the buggy cond; the rig may tolerate/abandon an aborted duel. Do not trust any C1 CPU number measured on the buggy stub.
### Fix
`ADD R0, R5, #0x0` before `bl 0x021D2BC8` (coral_dragon.py `_c1_cond_stub`). Rebuilt: `rom_coral_dragon.nds` verify 33/33 sha256 `81dbd94658fabd633814d6662e7bb164381fad6224d3c1fa9110402ab1aca69b`;
chain-layer `rom_coral_dragon_chain.nds` sha256 `9cc190ac8bb0fa197b508bf3f7983ef4dd91d41efd322687dc9858f99608e8a6` (rig must be rebuilt before another cardtest/GDB run); check_allocations clean.
Not yet checked by anything but the disassembly: the other C1 call sites (0x021A1430, 0x021EFF30 arg registers) and the cost stub (r0 = desc untouched before the 0x021E5060 call) -- read, look right, UNPROVEN until run.
### Next experiment
Re-run the CPU mirror on a rebuilt rig (cardtest rig + mirror, kit unchanged) and compare activated; then the user's in-game test (activate C1; counters at 0x023AEBD0 readable from a savestate).

---
## Part 12 — re-run after the stub fix (2026-11-09) — emulator CPU evidence, NOT user-confirmed
- Mirror (rebuilt rig, same 8 duels / kit): **Coral summoned 8, activated 0, kit 172/79/101 -- identical to the buggy-stub run.** The crash fix did not change the CPU-mirror numbers.
- GDB seed idx 1 (private port 3340, fixed chain ROM `9cc190ac...`, duel finished, ~65 s of emulated play): events =
  `C1cond` @39.4 s desc `7f10 00 02 09 03 ...` -> **returned 1**; `C1cond` @57.8 s desc `7f10 00 02 07 03 ...` -> **returned 1**; an effect enqueue of cid 0x107F (r1=0x3A4E107F, LR 0x021D3227) between them and the C2 call;
  `C2cond` @63.0 s desc `7f10 00 0e 1d 02 ...` (desc[3]=0x0E = GY destination zone, desc[+0xC]=0x0052) -> **returned 1**. Rig stats for Coral (slot 60): summoned 1, activated 0.
  => (a) C1's condition now runs and says YES instead of faulting; (b) the C2 condition resolved the card in the GY through `0x021A2510(side, desc[+0xC])`, read its word, found bit 15 set and `0x021F069D` said draw is legal --
  this is the first evidence for open questions (a)/(b)/(c) of Part 5 (ref valid for leave-trigger desc; bit 15 survives into the GY array); the mask row + cls2 record DID arm and reach the cond for an Extra-Deck donor (H1 supported).
  NOT shown: whether the Yes/No prompt appeared or a card was drawn (the rig's `activated` stat stayed 0), whether the C1 cost/discard ran (no C1COST event was logged), and what the enqueue of 0x107F was.
  The sequence C1cond(yes) x2 -> enqueue -> C2cond is consistent with: CPU was offered clause 1 twice, declined (no C1COST breakpoint hit), and Coral then left the field to the GY by some other means; but that ordering is my reading of timestamps, not proven.
- Still open: why the CPU never pays C1's cost (it is offered: cond = 1 twice); in-game human test of both clauses.

---
## Part 13 — generic activation check traced; CPU declines an activatable C1 (2026-11-09, emulator CPU, NOT user-confirmed)
User hint (verbatim): "it doesnt activate because it can simply run over the card... maybe try a different seed?" (reading: the CPU has no reason to pay a discard when it can attack over the card; not a duel report).
- Generic "can activate" check (ov3 ~0x0224AD94..0x0224AE46, caller of every cls record's +0C): `blx [rec+0xC]` (our cond) -> if 1 and rec+08 (target filter) != 0 -> `0x0224A988(desc, filter)` = scan of BOTH players' 11 field slots, calling filter(desc, side, slot),
  skipping slots with bit 21 of [slot+0x44] set, returns a bitmask of legal targets; empty mask -> not activatable. (disassembled this session)
- GDB seed idx 1 (fixed ROM): C1cond ret 1 -> `gen_filter` filter 0x021DE7C9 -> `gen_after` mask **0x40000** (exactly one legal target: opponent slot 2) -> `gen_final` **1**; same again at 59.9 s. So **clause 1 WAS ACTIVATABLE twice** (cond + target scan pass);
  the CPU did not take it (no C1COST hit, rig activated 0). Not a stub/gate defect on our side. Later: enqueue of 0x107F, C2cond ret 1, gen_final 1 (the draw trigger is offered).
- Seeds 4-8 queued in the background (scratch/coral_gdb_seeds.log) to find a duel where the CPU pays the cost.

## Part 13b — seeds 4-8 (fixed ROM, GDB harness; emulator CPU, NOT user-confirmed)
Seeds 4, 5, 6, 8: Coral never summoned (no events). **Seed 7: both seats summoned Coral** (stats [0,1,0] / [0,1,0]):
- side-1 Coral: C1cond ret 1 but the target scan `gen_after` = **0x0** (no legal opponent card) -> `gen_final` 0: correctly NOT activatable (negative case works); later C2cond ret 1 (goes to GY), gen_final 1, enqueue 0xBA4E107F.
- side-0 Coral: C1cond ret 1, mask 0x40000, gen_final **1** at 164.7 s and again 166.6 s (activatable, not taken); then enqueue 0x3A4E107F and C2cond ret 1 / gen_final 1.
Across seeds 1 and 7: clause 1 activatable 4 times in 3 Coral lifetimes, **never taken by the CPU (no C1COST hit)**; clause 2's trigger offered 3/3 times a Coral reached the GY (all via CPU-controlled play, none user-driven).
Reading (UNPROVEN): the CPU does not pay a hand-discard cost for this effect (Cardcar D's tribute-to-draw is likewise never used); whether that is CPU strategy or a CPU cost-evaluator gate is not established.
Rig 'activated' stat stays 0 even though C2cond was offered, so whether the CPU accepts/draws on the Yes/No is not shown either.
The negative case for C1 (no target -> not offered) is the one human-relevant check this harness did confirm. The positive paths (discard prompt, target pick, destroy, draw) are only testable by a human in-game.

---
## Part 14 — user in-game test #1 (2026-11-09) and the fixes (emulator CPU evidence, NOT user-confirmed)
User report (verbatim): "2. It prompts to draw even if the card was special summoned from GY e.g. with monster reborn" / "Also 2. The effect is an IF you can effect so it does not miss timing e.g, used for a synchro summon." /
"The positive case did work for destruction and battle but missed timing. In the instance of the leaving the field the second time, it was destroyed by dark hole." / "Tribute can miss too, discard as cost and banish cannot miss because they do not fulfill coral dragons condition. All other points are correct."
Reading (confirmed by the user): (a) revive via Monster Reborn then Dark Hole still prompts = BUG; (b) after a real Synchro Summon the prompt appears for destruction and battle; (c) as Synchro material / Tribute it MISSES the timing = BUG (IF effect must not miss); discard-cost / banish are correctly not offered (don't fulfil "sent from the field to the GY").
### (a) cause + fix
- Bit 15 of the card word = "properly summoned" and is NOT cleared by going to the GY / being Reborn'd, so it cannot tell "Synchro Summoned" from "revived". (inference from the user's result; the word was not measured.)
- New marker: 512-bit bitmap `CAVE_CORAL_MARK` indexed by the packed card ref (idx<<1|side); set when the donor's last summon came from zone 0xC (Extra Deck), cleared for any other source. The C2 cond reads the bit for desc[+0xC].
- Hook: **the SS-commit routines 0x022692F2 / 0x022693A0 are NOT reached for a Synchro Summon** (GDB probe, seed 7: DBG2 stayed zero; ssA/ssC 0 hits, ssN = Normal Summons only). Every Special Summon reaches the summon-event evaluator 0x02265768, which has THREE callers:
  0x02267A38 (code 7), 0x0226878A (code 9), 0x02268B7C (code 8) -- each `movs r0,#code ... bl 0x02265768`. Probe at the proper-SS trigger site 0x02265900 shows Coral summon with src zone 0x0C and the SAME ref (0x52/0x53) the leave cond sees; GY revivals of other cards show src 0x0E.
  The marker front now sits on those 3 BLs (stub CAVE_CORAL_SSF, prev head in CAVE_CORAL_PREV).
- Evidence after the fix (GDB seed 7, chain ROM cef891b4...): DBG2 = {cid 0x107F, src 0xC, ref 0x53/0x52, count 1/2}; C2 cond: marker byte 0x08 / 0x0C (bit 3 / 2 for ref 0x53 / 0x52) -> bit 1 -> **returns 1**; rig stats **Coral activated 1 on BOTH seats** (before: 0) = the CPU took the draw offer.
  NOT shown (needs the user): the revive case clears the bit (Monster Reborn then Dark Hole -> NO prompt).
### (b) cause + fix
- "If ... You can" = the miss-timing test 0x021EE0E0 must never-miss the cid: same mechanism as Shadow Mist PART J / Eva PART J / Block Dragon C3MISS (cid-tree node 0x021EE10C). Added `CAVE_CORAL_MISS` front at the node; the previous head is kept in CAVE_CORAL_PREV[+4] (0 = stock node: the front replays the two displaced ops). In the chain ROM the previous head is Block Dragon's front 0x023AE9B1.
- NOT shown by any CPU run (the CPU never used Coral as material/tribute); in-game retest required.
### Builds (current): rom_coral_dragon.nds sha256 `70255af44af645edf4ef700cc4dfe0f3bd08571b4b95b90ccd0a3c96294ab33c` (verify 43/43); chain-layer cef891b4196e6779ba4d4fec598418c320cbc349f1e01b5f8a4e8f27f3d9c8e5 (43/43). check_allocations clean (CAVE_FREE 0x023AECE0, ceiling 0x023AED20).
### In-game retest list
1) Synchro Summon -> destroy / battle-destroy: prompt (regression). 2) Synchro Summon -> use as Synchro material AND as Tribute: prompt must now appear. 3) Synchro Summon -> Monster Reborn -> Dark Hole: NO prompt. 4) discard-cost / banish: no prompt.
5) clause 1 from the earlier test list; counters at 0x023AEAE0 (C2 cond), 0x023AEBD0 (C1), 0x023AECD0 (SS front record) if a savestate is needed.

---
## Part 15 - SHIP attempt 2026-11-09 (user: "All confirmed. Ship" -- in-game confirmed by user 2026-11-09, all test cases incl. Synchro material/Tribute/Monster Reborn)
- Added Step("Coral Dragon","cards.coral_dragon") to otn_enhanced/steps.py at index 118 (after block_dragon 116 / cpu_hand_ss 117). Backup: rom_all_patches.PRE_coral_dragon.nds. NOT YET SHIPPED: full build fails.
- Full build FAILS at step 125 (data.bulk_card_pack): ValueError Card name "Stream, Dragon Ruler of Droplets" not found in card_name_e.bin. CONTROL build without coral (scratch/build_nocoral.py) passes 128/128 (sha256 522873ac...1b9fe).
- Bisect so far: after step 118 (build --upto 118 -> rom_upto118.nds) Stream IS present in card_name_e.bin (decoded with bulk_card_pack._decode_card_names). Coral applied on the finished chain ROM also keeps it. So a step in 119-124 (card_art, default_banlist, regulus, bulk_card_props, field_backgrounds, card_genre) loses/renames it ONLY when coral ran. Suspects: bulk_card_props (name edits by index) and _build_name_to_index ambiguity (duplicate name). Next: build --upto 124 and check names; read bulk_card_props for index-based name edits.
- Still to do once green: assert N/N steps + sha256, run -m otn_enhanced.verify on the new ROM, then update notes/KB/donor note with the confirmation wording.

---
## Part 16 - SHIPPED 2026-11-09 (user: "All confirmed. Ship")
in-game confirmed by user 2026-11-09 (all cases of the retest list: clause 1, clause 2 incl. Synchro material / Tribute / Monster Reborn). Wired into steps.STEPS (step 118, after block_dragon + cpu_hand_ss).
- Chain build: 129/129 steps, rom_all_patches.nds sha256 dd7772ff3e50d0f574ac4f5e574b66e081add97b55059b4b2188d250b5abef4b. Verify sweep: 119 passed, 1 failed (data.bulk_ydcs, which ALSO fails in the control build without coral = not ours), 5 without verify().
- Shipping fixes: (1) bulk_card_pack.py CHANGES key "B. Skull Dragon" -> "Coral Dragon" (step 125 looks names up in the ROM; the old name no longer exists). (2) the displaced heads are inline literals in the fronts (other cards walkers follow literals), with the PREV slot kept so verify() can recover them. (3) ov5_cave.dc_next += CAVE_CORAL_MISS -> CAVE_BD_C3MISS; block_dragon.py miss-node assert/check now accept any registered front ahead of its own (dc_ahead_of) -- block_dragon is another session WIP file, review that 2-line change.
- The original step-125 error message named "Stream, Dragon Ruler of Droplets" although Stream was present; after the key rename the build is green. Cause of that message NOT diagnosed (UNVERIFIED).
- Not done: author_facts.py KB entries (summon evaluator 0x02265768 has 3 callers 7/9/8; SS-commit sites 0x022692F2/0x022693A0 not reached by Synchro Summon; miss-node front pattern; bit 15 = properly summoned survives Reborn; 0x021D2BC8 needs desc in r0) -- proofs are in Parts 11-14 above.

## Part 17 - KB facts written (2026-11-09)
author_facts.py: VERIFIED summon.event_evaluator_0x02265768_has_three_callers, dispatch.in_cost_sim_0x021D2BC8_takes_the_desc_in_r0; UNVERIFIED (evidence attached) summon.synchro_summon_skips_the_ss_commit_sites_0x022692F2_0x022693A0, summon.card_word_bit15_survives_gy_and_reborn, leave.mask_row_arms_extra_deck_donor_cls2_trigger (corrects the 2026-07-20 Quasar A/B), timing.miss_front_chain_is_a_registry_dc_next. Regenerated docs/engine/*.yaml; --check: 895 PASS / 7 FAIL / 179 UNVERIFIED -- the 7 FAILs are environment (3ds_extract and docs/ov3_catalogue files absent) plus tool.rom_files_entries_must_be_bytearray; none are the new facts.
