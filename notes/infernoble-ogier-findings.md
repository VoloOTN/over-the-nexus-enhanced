# Infernoble Knight Ogier — findings

Family roadmap: ~\.claude\plans\add-all-the-infernoble-merry-rainbow.md (card 1 of 19).
Started 2026-10-20. Clause split + C3-first CONFIRMED by user 2026-10-20. Donor: Robotic Knight 0x13A3
(L4 FIRE Machine 1600/1800 Normal) chosen by user 2026-10-20 ("Looks good - proceed."). Status: pre-build
checklist (no ROM code yet). Order: monsters first (user needs Knights to test the Arms), Arms after.
Noble Arms plan: "Noble Arms" = a list of exactly the 4 Infernoble Arms donor cids (user 2026-10-20).

## Printed text (scratch/ygoprodeck_cache.json, id 21351206)
Effect Monster, Warrior, FIRE, L4, 1500/2000.
- C1 (continuous, while an Equip Card): the equipped monster cannot be destroyed by card effects.
- C2 (trigger, OPT shared-heading): If this card is Normal or Special Summoned: send 1 "Noble Arms"
  card, or 1 FIRE Warrior monster except "Infernoble Knight Ogier", from your Deck to the GY.
- C3 (ignition, OPT): If this card is in your GY: target 1 Warrior monster you control; equip this
  card to that monster.

## Confirmed
- 3DS ships no Infernoble cards; it does ship Noble Knight Joan/Artorigus/Gawayn/Medraut/Gwalchavad,
  Noble Arms Gallatin/Arfeudutyr/Caliburn/of Destiny, 21 Dragunity names (CARD_Name_E.bin string scan,
  this session).
- ov5 cave: CAVE_FREE 0x023A7600, ceiling 0x023AA120 -> 0x2B20 B free (Explore survey of ov5_cave.py
  line 2284, this session — re-read before claiming).

- User 2026-10-20: "do the whole card first instead of breaking clauses" -> one build, all 3 clauses.
- Donor Robotic Knight 0x13A3: donor_scan CLEAN (no aligned u16/u32 anywhere) AND
  scratch/infernoble/near_lits.py finds no base±imm computation of 0x13A3 -> no per-cid gate (PROVEN
  within those two scanners' coverage).
- Records dumped this session (scratch/infernoble/recs.py, stock rom.nds):
  * "equip THIS card from GY to target" RESOLVER = **0x02210961** (cls2 +04 of Vylon Sphere 0x249F
    cls2[684], Stella 0x24A1 cls2[686], Prism 0x24A2 cls2[687], Handcuffs Dragon 0x1E1F cls2[364]).
    Vylon: +08 0x021D8465 (face-up monster you control), +0C 0x0224A115, +10 0x021E5201, +14 0x02234D81.
    Handcuffs: +08 0x021E26B5, +0C 0x021F8049, +10 0x021E51E5 "You can", +14 0x02235E81.
    Vylons also own igncond rows {0, 0x021F8049, 0x022043F5} (rows 139/141/142).
  * GY IGNITION template = Glow-Up Bulb 0x2387: cls2[619] {+04 0x0222D1AD, +08 0, +0C 0x021F0BDD,
    +10 0x021E81E5, +14 0}; igncond[120] {f1 0x021F7B75, f2 0x021F44D9}; gyrow[50] {0x2387,0xE,0x0224C591,0x0224C6C1}.
  * C2 TEMPLATE = Armageddon Knight 0x1CFF: cls1[745] {+04 0x02208DD5, +08 0, +0C 0x021F0B19, +10 0x021E51E5,
    +14 0}; crit[632] {aux 0xFFFF, 0x0223CAD9 (Deck->GY), 0x02000002 DARK}; member of "summon list: any summon[17]".
    FIRE Warrior word = (15<<3 | 4) << 24 = 0x7C000002 (KB dispatch.criteria_word_race_attribute).
- GY-action rows: real registry 0x0228DDF8 has no family-C phantoms; Dragon Rulers' virtual table
  CAVE_RUL_GYROWS (0x60 = 6 rows) is FULL (Revolution + 4 big rulers + Sekka's Light) -> must be enlarged.
- Free phantom rows in the CHAIN ROM (scratch/infernoble/free_phantoms.py, rom_all_patches.nds 2026-10-19):
  cls2 39 (e.g. 0x1A8A 0x1B48 0x1B49 0x1B4A 0x1B8F unclaimed anywhere), cls1 126, cls3 61, criteria 19,
  igncond 5 (0x0E3E 0x0E7D 0x0E86 0x0EA9 0x0EAE, all claimed in other pools — per-table claim, check).

## IN-GAME RESULT — in-game confirmed by user 2026-10-20 (BUILD 1, rom_infernoble.nds e1d04eb3...3015f)
User's words: "All of ogiers effects pass, (with the exception of the send equip spell). Please log these as confirmed."
- CONFIRMED: C1 (equipped monster not destroyed by card effects), C2 FIRE Warrior Deck->GY half (incl. "except
  Ogier" + once per turn), C3 (GY equip to a Warrior you control, once per turn).
- NOT BUILT / NOT TESTED: C2's "Noble Arms" half (no Noble Arms card exists yet; joins with the Infernoble Arms).
- NOT REPORTED: regression items 13 (Rulers / Revolution / Sekka GY effects) and 14 (Windrose / Psi-Reflector).
- Consequently also in-game confirmed (Ogier is their only user): gy_vrow_hook's virtual row for 0x13A3, the
  0x02210961 equip-from-GY reuse, the 0x021D73A0 equip-target front, the 0x021B059C protection front,
  the synthetic OPT key 0x53A3. NOT shipped: not in steps.STEPS (awaiting the user's ship decision).

## BUILD 1 (2026-10-20)
- `_build_infernoble.py` -> data/over_the_nexus/working/rom_infernoble.nds
  sha256 e1d04eb3ea5583fe10ec7c9c6e8a2198deafde991075fdb2963a25165713015f (layered on rom_all_patches.nds 2026-10-19).
- Module otn_enhanced/cards/infernoble.py (family module) + NEW shared gy_vrow_hook.py
  (user decision "a" 2026-10-20). User approved the Tenki-style "except Ogier" exclusion 2026-10-20.
- verify(): patch_infernoble PASS; regression verify PASS for patch_revolution_synchron, patch_dragon_rulers,
  patch_sekkas_light (each got a one-clause tolerance for the lifted GY sites).
- EXECUTION PROOF of the GY lift (scratch/infernoble/gyv_equiv.py over the built ROM): old Rulers stubs vs new
  shared stubs agree on fetch rows 0..65, loop exit 60..65, has-row for all 6 existing cids, post for r4 59/60;
  new adds Ogier row 66 and still rejects non-members. ALL PASS.
- Local shared-arm registrations (NOT in their ARMS until ship): c79_trigger_hook + timing_class_hook (ARM_JW).
  ⚠️ So patch_windrose / timing-hook owners' verify() will FAIL on this ROM (stub has an extra arm) — expected
  until ship; at ship move Ogier into c79.ARMS and tch.ARMS.
- KB facts added: leave.equip_loss_reason_bits, dispatch.equip_this_card_from_gy_resolver,
  rider.majestic_red_dragon_unconditional_arm (author_facts --check: 723 PASS 0 FAIL).
- Slots: ov5 CAVE_GYV_* + CAVE_IK_* (0x023A7600..0x023A7A50); phantoms cls2 0x1B48, igncond 0x0E86,
  cls1 0x1370 (1 of 2 rows), criteria 0x0E7E. Ledger refreshed, check_allocations OK.
- Known UNPROVEN: (a) the equipped Ogier keeps cid 0x13A3 in the S/T zone and 0x021A0DF8 links it (C1);
  (b) C2's synthetic OPT key 0x53A3 through 0x021D2584 -> 0x021C479C; (c) +14 0x02234D81 copied from Vylon.

## Architecture draft (as built)
- C3: cls2 record for 0x13A3 {+04 0x02210961, +08 Warrior-you-control filter, +0C 0x021F0BDD, +10 OPT
  stamp kind 1 ("You can"), +14 ?} + igncond row + virtual GY row (Rulers table enlarged).
- C2: cls1 record = Armageddon clone + criteria row FIRE Warrior 0x7C000002 + summon-list membership.
  "except Ogier" not expressible in the word -> needs exclusion (open).
- C1: "equipped monster cannot be destroyed by card effects" — no native equip found yet (open).

## "Noble Arms" half (2026-10-22) -- BUILD 27 AWAITING IN-GAME TEST
- rom_infernoble.nds sha256 9acdb6fa935264b7bd69025297cfd8004619c12f009956e203269750ecc6ade1; verify PASS; regression FAIL
  set identical to BUILD 26.
- Row words made type-only (Ogier 0x00000006 Deck; Maugis 0x00010006 GY+banished); new shared callback AR_NACB (ov5
  0x023AB770): cid != excluded AND (one of the four Infernoble Arms OR Warrior + FIRE). Ogier's old C2CB is kept (Charles
  and Angelica use it with FIRE-Warrior words).
- EXECUTION-PROVEN: scratch/infernoble/nacb_check.py -- AR_NACB matches a Python oracle on 8,610 (card, excluded) cases;
  all four Arms kept, the excluded card never kept.

## Ruled Out
(none yet)

## Open Questions
- Is a monster equipped via the Cyberdark/Barcha resolver 0x022186E4 treated as an Equip Card
  for C1's "while this card is an Equip Card" test? (UNVERIFIED — from Explore survey)
- "Noble Arms" set code: does the NDS have one? (no stock Noble Arms cards in OTN — likely needs a new set code)

## Next Experiment
- Read 3DS handlers for Noble Knight Gwalchavad / Dragunity Knight - Barcha / Noble Arms - Gallatin.
