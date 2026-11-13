# Disguise, the Copycat Hero — findings

Started 2026-11-04. Status: **SHIPPED 2026-11-04 on user approval ("Looks good. Add to card arts and ship") --
in-game test NOT reported, so nothing here is in-game confirmed.** Both cards (Disguise 0x111E on Monster Tamer,
Cursed Copycat Noble Arms 0x10E3 on Cyber Shield) in steps.STEPS step 111/122 ("Disguise, the Copycat Hero + Cursed
Copycat Noble Arms", cards.disguise_copycat, right after Infernoble Knights), card art in data.card_art.CARDS.
Chain: 122/122, rom_all_patches.nds sha256 9824c3d2db24481709f3d8dd60b40eda0640304752ddd1e4507f0bc81cf1d9a5;
verify sweep 112 passed / 1 failed (data.bulk_ydcs: wcs084_formula + rpg046_8_glaton -- already failing on the
pre-build chain, from the user's uncommitted ydc_decks.py; neither deck uses either donor).
Ship-time integration (2026-11-04): c79 stub re-homed to CAVE_C79TRIG 0x023AC970 (0x40; old 0x023A53F0 RETIRED),
0x111E in c79_trigger_hook.ARMS + PREPENDED ARM_DC in timing_class_hook.ARMS; the 5 fronts registered in
ov5_cave.dc_next() (ik_walk/ik_tail follow it; dc_skip for direct compares); owner verifies widened: dragon_rulers
(H2/H3/ARM9 H4), fire_formation_tenki, sacred_sword_seven_stars, infernoble (T/RO H4, CO stat, AR miss, M miss).
bulk_card_pack keys renamed ("Monster Tamer" / "Cyber Shield"). The in-game test plan is under Next Experiment.

## Confirmed

- Printed text (scratch/ygoprodeck_cache.json, id 87750925): Warrior / Tuner / Effect,
  LIGHT, Level 4, ATK 1400 / DEF 1200 (passes the ATK <= 1500 donor-style filler bar
  irrelevant here — this is the *new* card). Text:
  > If you have an Equip Spell in your field or GY: You can Special Summon this card from
  > your hand. If this card is Normal or Special Summoned: You can add 1 "Cursed Copycat
  > Noble Arms" from your Deck to your hand. While this card is equipped with an Equip
  > Card: You can target 1 non-Tuner Warrior monster on the field with a Level; this
  > card's Level, also its name, become the same as that monster's until the End Phase.
  > You can only use each effect of "Disguise, the Copycat Hero" once per turn.
- No prior work in repo (grep `copycat|disguise` over otn_enhanced/notes/ygo_tools:
  only the unrelated 1-star "Copycat" in bulk_card_pack / ydc_decks).
- "Cursed Copycat Noble Arms" (id 23249029, Equip Spell, 2023) is **not in the ROM**
  and not implemented here (same grep). Clause 2's search target does not exist yet.
- 3DS second source: `3ds_extract/` is **absent from disk** this session (CLAUDE.md path
  missing). Both cards are 2023 (DOOD) so the 3DS (2013) cannot ship them anyway.
  `scratch/bin2/card_name_e.bin` (UTF-8 name table) has no "Disguise"/"Noble Arms".

- **Scope (user, 2026-11-04): ALL clauses of Disguise, AND implement Cursed Copycat
  Noble Arms as a second card.**
- Cursed Copycat Noble Arms text (cache id 23249029, Equip Spell, archetype Noble Arms):
  > The equipped monster gains 200 ATK/DEF for each Equip Spell in your field and GY.
  > While this card is equipped to a Warrior monster: You can activate this effect; you
  > cannot Special Summon for the rest of this turn, except Warrior monsters, also Special
  > Summon 1 Warrior monster with the same Attribute and Level as the equipped monster but
  > a different name from your Deck, and if you do, equip it with this card, then destroy
  > the monster this card was equipped to. You can only use this effect of "Cursed Copycat
  > Noble Arms" once per turn.

### Donor scan (this session, `donor_scan --free` + an Equip-subtype scan via donor_scan.cards()/occurrences())
- Disguise donor candidates (clean = zero aligned u16/u32 cid hits in ov3+arm9, ATK <= 1500, unspent):
  Chamberlain of the Six Samurai 0x1C6C (only clean WARRIOR; Lv3 EARTH 200/2000),
  Big Insect 0x0FD7, Gokibore 0x0FDC, Giant Flea 0x0FDD, Grappler 0x0FF3, Red Archery Girl 0x127B (all Lv4).
  Aqua Madoor 0x107B appears in --free but is PARKED (Magician's Rod) -- exclude.
  Only 3 clean Warriors exist; the other two (Judge Man 2200, Monster Tamer 1800) fail the ATK bar.
- Noble Arms donor candidates (unspent Equip Spells):
  **Mage Power 0x145D -- ZERO aligned hits**; printed "+500 ATK/DEF per S/T you control" = same
  shape as Noble Arms' "+200 ATK/DEF per Equip Spell in field+GY" (per-count, both stats).
  United We Stand 0x145C (noise-only hits, +800 per face-up monster, same shape).
  Megamorph 0x1237 (noise only, but it's a halve/double, wrong shape).
  Single-binding-hit: Book of Secret Arts 0x10E9, Cyber Shield 0x10E3, Burning Spear 0x12EE, Synchro Boost 0x1E0B.
  Per Infernoble lesson: base+-imm scans MISS gates in equip legality switch 0x021D7348 -> emulate it for the chosen donor.
### Precedents (KB, not re-proven this session -> UNVERIFIED until reused)
- **C3 Level + name until End Phase: Copy Plant 0x1EC1 and E-HERO Prisma 0x1D43 share cls3 resolver 0x02208499**
  (KB dispatch.level_rider_is_kind_3, dispatch.prisma_extra_deck_reveal_cost). Level SET = rider
  {key 0x1EC1, kind 3, N} (dispatch.level_rider_set_key_0x1EC1_kind3; Oliver used it in-game).
  Prisma's NAME change mechanism is NOT in the KB yet -- find it inside 0x02208499's Prisma leaf.
- C1 hand SS: Infernoble Oliver/Ricciardetto (Stygian Street Patrol resolver 0x0220667D), Renaud (tg_table procedure).
- C2 / Arms ignition: Emperor Charles C2 & Almace E1 (Vylon Sigma pick/zone/move(0x021C7484)/link(0x021C4A68)
  phases; equip link kind must be 0xA). Criteria registry has NO free row -> virtual criteria row (Tenki 0x02243F24 front).

- User 2026-11-04: **REJECTED Mage Power and Big Insect** ("absolutely NOT"); asked for Level 5/6 Normals.
  Clean Lv5/6 unspent (donor_scan --free --level 5/6) -- ALL are > 1500 ATK (none pass the old bar):
  Lv5 Kairyu-Shin 0x0FEF, King of Yamimakai 0x0FFB, Dungeon Worm 0x111D, Monster Tamer 0x111E (Warrior),
  The Earl of Demise 0x146D, Giga Gagagigo 0x16EF; Lv6 Judge Man 0x0FC7 (Warrior), Megazowler 0x0FF5,
  Pendulum Machine 0x112A, Firewing Pegasus 0x1270, Steel Ogre Grotto #2 0x1285, Amphibian Beast 0x13CA,
  Gadget Soldier 0x13E4, Luster Dragon #2 0x14E5, Frostosaurus 0x1B31, (Summoned Skull 0x0F0A -- banned by CLAUDE.md).

### Disguise donor = Monster Tamer 0x111E (user pick 2026-11-04) -- vetting this session
- (a) Normal Monster, Lv5 EARTH Warrior 1800/1600. `donor_scan 0x111E` -> "VERDICT: CLEAN - no data
  structure names this cid" (zero aligned u16/u32 in ov3 + arm9 => no cls0-3 record, no criteria row,
  no leave/summon list row).
- (c) base+-imm per-cid code: scratch/infernoble/baseimm_scan.py (import fixed to otn_enhanced.knowledge.env,
  run from scratchpad copy with PYTHONPATH=.) on 0x111E -> **no hits**. Positive control same run:
  0x15E3 Demotion -> hits ov3 0x021B845C / 0x021B8464 (the known Level-recompute table), so the scanner works.
  Known blind spot: switches at a BRANCH TARGET / stack-based [sp] switches (it missed Psychic Sword 0x1F71
  in the control too). Residual risk = those patterns only.
- (b) text: cid goes into card_text.CARD_TEXT -> INDEX-ORDER RE-EMIT, no slot limit (card_text.py:98,
  check_rom_text @1699). Slot floors irrelevant (name 13 / desc 52).
- (d) props are rewritten to Lv4 LIGHT Warrior Tuner/Effect 1400/1200; Warrior already matches.
- Build-time TODO: bulk_card_pack.py:2572 keys "Monster Tamer" by in-ROM name -> rename the key in the
  same edit (Infernoble lesson).

### Noble Arms donor = Cyber Shield 0x10E3 (user pick 2026-11-04) -- vetting this session
- `donor_scan 0x10E3` -> ENTANGLED by exactly ONE binding hit: equip ATK/DEF grant row[17] @ov3 0x0226E016
  (the +500 stat). That row gets rewritten/neutralised for N1 anyway.
- baseimm_scan 0x10E3 -> no hits (blind to jump tables / branch targets, see below).
- **Equip-legality switch 0x021D7348 EMULATED** (scratch/equip_tree.py, run `PYTHONPATH=. uv run python scratch/equip_tree.py <cid..>`: thumbemu over stock ov3, start
  0x021D73A2 with u16[desc] = cid, step until the first non-compare instruction; follows the
  `add pc,r1` jump table at 0x021D7424). Controls: Molting Escape 0x2124 -> 0x021D7F38 and
  Psychic Sword 0x1F71 -> 0x021D7F2A (both = KB/known arms); Black Pendant 0x10DD (any monster) and
  junk cid 0x0001 -> default 0x021D7FA6 (entered at 0x021D7FA4 `adds r0,r2,#0`).
- **Cyber Shield lands in its OWN arm 0x021D7A7C** (sole cid in 0x0F00..0x25FF to land there):
  `bl 0x02022E98 ; cmp r0,#0 ; bne accept ; subs r7,#0xEE ; cmp r5,r7 ; bne reject` -> accept 0x021D8178
  (ret 1) / reject 0x021D7F5E (ret 0) = the "Harpie Lady only" gate. MUST be removed (Noble Arms equips
  any monster). Planned fix: halfword at 0x021D7A7C -> `b 0x021D7FA4` (default arm, r2 still = equip cid;
  distance 0x528 fits an 11-bit B). Prove by re-running equip_tree.py on the patched image (expect 0x021D7FA6).
- Residual ASSUMED: other per-cid trees (e.g. the Equip-Spell activation tree near 0x021F076E) not yet emulated for 0x10E3.

### C3 name change = Prisma's rider (disassembled this session, stock ov3)
- **WRITE**: shared cls3 resolver 0x02208498 (Prisma 0x1D43 / Copy Plant 0x1EC1 / ...). Entry stashes
  key = u16[desc] (own cid) at [sp+8] (@0x022084A4), r7 = 0. Compare tree on u16[desc]: 0x1D43 is reached
  at 0x02208518 (`subs r3,#0x17` off 0x1D5A) -> leaf **0x022085FA `ldrh r4,[r5,#0x14]`** (value = desc[+0x14]
  = the material cid Prisma's cost stashed) -> 0x0220873E r0=0xFFFF, clamp @0x02208784 -> tail
  0x0220878A..0x022087AA: **0x021C479C(side=desc[2], zone=desc[3], key=[sp+8], kind = 2 | (r7&0xF)<<4 = 2,
  [sp] = value)**. So Prisma's name change = rider **{key 0x1D43, kind 2, value = new cid}** on its own zone.
- **READ**: **0x021A3320(side, zone) = "current cid/name of the monster in that zone"** (also the equip
  switch's candidate-cid call @0x021D739C). r4 = r5 = zone word & 0x3FFF (@0x021A3346). zone <= 4: walks the
  zone's rider chain (head u16 [0x0229ACD2 + (side&1)*0xB3C + zone*0x14], pool 0x0229D33C stride 0xA, next
  = node+8). Node kind = u16[node+2] & 0xF must be 2 (or 3 with key 0x221E). Key whitelist tree
  @0x021A33C6..0x021A3432; **0x1D43 accepted @0x021A33EA -> 0x021A3476: r4 = u16[node+4] (new cid),
  [sp+0xC] = u16[node+6]**. Other keys landing on 0x021A3476: 0x1DC2, 0x1F0E, 0x1F5B, 0x1FA9, 0x21C6,
  0x2165, 0x24DC (base+-imm on the stack, @0x021A335E..0x021A339C); 0x1A74/0x221E -> 0x021A3434 (value
  only if 0x02029E60(value) != 0); 0x1E7E -> 0x021A3444; 0x1F5B..0x1FA9 range also via 0x021A3448 chain walk.
  After the walk: if u16[0x0229ACCC + side*0xB3C + zone*0x14] <= [sp+0xC] -> return r4 (overridden cid)
  @0x021A348C -> 0x021A3576; else falls into a per-cid "treated as" tree on r5.
- => Disguise C3 name half = write **{0x1D43, kind 2, target cid}** via 0x021C479C on Disguise's zone
  (the key is a whitelisted SELECTOR, like the Level rider's 0x1EC1 -- an own-cid key would be ignored).
  Level half = KB-proven {0x1EC1, kind 3, N} (dispatch.level_rider_set_key_0x1EC1_kind3).
- **PROVEN BY EXECUTION 2026-11-04** (scratch/disguise_rider_probe.py, thumbemu over
  rom_infernoble.ml5 -- getter/Level/sweep code byte-identical to stock; board side 0 zone 2 = 0x13A3,
  Level 4; node appended exactly as 0x0219F190 does, +6 = u32[0x0229DD14+0x2C]):
  name rider {0x1D43, kind 2, 0x0FF4} -> 0x021A3320 returns **0x0FF4**; key 0x111E (own cid) -> 0x13A3
  (ignored); {0x1D43, kind 6} -> 0x13A3 (ignored). Level rider {0x1EC1, kind 2, 7} -> **7**, {.., 1} -> 1,
  {0x1EC1, kind 3, 7} -> 7, {0x111E, kind 2, 7} -> 4 (ignored). **Both riders together -> name 0x0FF4, Level 7.**
- Node writer 0x0219F190: kind byte low nibble -> [+2] bits 0-3, high nibble -> bits 4-7 (duration);
  [+6] = u32[0x0229DD14+0x2C] (a serial, NOT the turn); appended at the TAIL of the zone list.
  The getter's [0x0229ACCC + side*0xB3C + zone*0x14] (= zone_rec+4) <= node[+6] test = "rider newer than
  the monster's arrival", so a rider dies with a zone change automatically.
- Expiry: KB continuous_riders 0x0219F9E0 (VERIFIED): kinds 1/2 with duration nibble 0 are freed by the
  once-per-turn end sweep -> "until the End Phase" for both riders, NO extra code. Use kind 2, NOT 3
  (kind 3 is only swept for keys 0x18D9/0x1F6A, so {0x1EC1, kind 3} would be PERMANENT -- that's
  Revolution Synchron's "Level becomes 1", not Copy Plant's timed form).
- Coverage: 347 ov3 BL sites call 0x021A3320 (0 in ARM9) -> wide, but ARM9-side name checks (deck/menu,
  any 0x0202xxxx cid reads) will NOT see the rename. UNPROVEN which once-per-turn / "different name"
  checks the card cares about read through it.
- CAVEAT: rom_all_patches.ml3/.ml4 differ from stock inside 0x021B807C..0x021B8900 (the chain patches the
  Level getter) -> re-run the probe on a savestate from the Disguise chain build before shipping.
- => C3 resolution = two calls 0x021C479C(side, zone, 0x1D43, 2, target_cid) and
  0x021C479C(side, zone, 0x1EC1, 2, target_level). Same two riders Prisma / Copy Plant write natively.

### C3 targeting + condition (disassembled this session, stock ov3)
- Copy Plant 0x1EC1 = cls3[438] @0x0227C684 {+04 0x02208499, +08 0x021DA929, +0C 0x021F01C1,
  +10 0x021E5061, +14 0x02234D81}. Prisma = cls3[374] @0x0227C084.
- +08 0x021DA928(desc, side, zone): `0x021D6E40(desc, side, zone, 0xC14)` must pass, then a cid switch on
  u16[desc]; Copy Plant's arm **0x021DAC78**: if desc[8] != 0 -> 1; else `0x021B8E30(side, zone, 0xD)`.
  0x021B8E30 = `0x021B8D90(side,zone)` race MASK `& (1 << race)`. Race enum (game_constants.ERA2_RACE_MAP):
  Plant 13 = 0xD (matches), **Warrior 15 = 0xF**. Mask 0xC14 low 2 bits = 0 = no side restriction
  (KB 0x021D6E40 side selector: 1 own / 2 opp / 3 rejects) -> "on the field" either side. No side check
  in the arm.
- +0C 0x021F01C0: `0x021A1430(desc[2], desc[3], 0xFB6) == 0` -> 1 = per-COPY OPT rider (Time Wizard key).
  Disguise needs a HARD OPT per effect -> use dispatch.turnlog_once_per_turn_pair (Mystic Piper):
  cost posts 0x021D2584(side, cid, 1, 0); cond queries 0x021A14E8(side, 0x0B, cid, 1), GUARDED on desc[+7].
- **non-Tuner**: KB synchro.is_tuner_predicate (VERIFIED): 0x021A1C7C(side, zone) = static Tuner
  (0x02023110 on the BASE zone cid) OR granted-Tuner rider 0x1E40. Non-Tuner = result 0.
  "with a Level": WC2011 has no Xyz -> every monster has a Level; nothing to test.
- **"equipped with an Equip Card"**: Captain Oliver's in-game-confirmed cond (infernoble.py
  `_co_equipped`, :3669): scan both sides' S/T zones 5..9; card present (0x021A36ED(side,z) != 0) and
  0x021A0DF9(side, z) == this monster's locator (zone<<8 | side) -> equipped. Covers monsters equipped
  as Equip Spells (they sit in S/T zones).
- **C3 design**: count-neutral cls3 insert (Mystic Piper recipe, KB dispatch.vanilla_can_take_an_ignition)
  {0x111E, +04 own resolver, +08 own filter, +0C own cond, +10 own cost (OPT post, then a cost-free tail),
  +14 Copy Plant's 0x02234D81?}; card_type -> Tuner/Effect.
  - filter = 0x021D6E40(desc,side,zone,0xC14) && race(0xF) && !0x021A1C7C(side,zone) (desc[8] != 0 -> 1 like CP).
  - cond = desc[7]-guarded OPT query && Disguise equipped (_co_equipped on desc[3]<<8|desc[2]).
  - resolver = Copy Plant leaf's target fetch 0x022349B0(desc, 0, &t) + recheck 0x0224A924(desc, side, zone),
    then lvl = 0x021B8064(t_side, t_zone), cid = 0x021A3320(t_side, t_zone) (target's CURRENT name),
    then 0x021C479C(desc[2], desc[3], 0x1D43, 2, cid) and (.., 0x1EC1, 2, lvl).

### C1 design (hand SS if an Equip Spell is in your field or GY; hard OPT) -- precedents read this session
- Template = Infernoble OLIVER C2 (in-game confirmed by user 2026-10-20, notes/infernoble-oliver-findings.md):
  ONE cls2 record, hand branch (desc[+3] == 0x0B); +04 = OPT check/stamp at phase 0x80, then the native hand
  self-SS 0x02206ABD (it summons in ITS 0x80 and ends in 0x7F with 0 -- Oliver lesson); +0C = OPT + free MZ
  0x021AD870 + condition -> 2 (no-target record: return 2, NOT 1 -- Roland lesson: 1 = "needs a +08 target");
  +08 = 0, NO cost (+10) -- Disguise has no cost. OPT stamp at resolution (Maugis lesson).
- Hand OFFER: ARM9 LIST A 0x0209BC4E / LIST B 0x0209BC8C are FULL -> join the ARM9 H4 front chain at
  0x02023566 (`bl LIST-B bsearch`): current head = infernoble RO_H4 -> T_H4 -> Rulers CAVE3_RUL_H4 -> native.
  New front = `cmp r0,#0x111E -> return 1, else tail-jump to the previous head`; needs an ov5_cave.ik_next()
  entry + Rulers'/infernoble verify widened (shared-hook rule).
- "Equip Spell" test (Oliver `_fire_warrior_or_equip`, infernoble.py:780, in-game confirmed):
  0x0202ABE9(cid) == 3 (spell type Equip) && 0x0202ABB9(cid) == 23 (race 'Spell').
- Scan: own S/T zones 5..9 (cid word at zone_rec(side, z) & 0x3FFF / 0x021A36ED) + own GY:
  P = 0x0229AC94 + (side&1)*0xB3C, count u32[P+0x14], cid = u32[P+0x55C + 4i] & 0x3FFF (KB donor_card_technique).
  The same helper serves Noble Arms N1's COUNT ("each Equip Spell in your field and GY").
- cls2 phantoms left in STOCK: 0x1B19, 0x234D (unclaimed per PHANTOM_CLAIMS) -- recheck in the CHAIN image too.
- **RULING (user 2026-11-04): FACE-UP ONLY** -- a Set Equip Spell does NOT count for C1's "in your field".
  Face-up test = u16[zone_rec(side, z) + 8] != 0 (KB ram.zone_record_faceup_flag, ANCHORED, census of 17
  savestates; used by shipped Denko Sekka's lock). GY cards need no face-up test.
  (Noble Arms N1 "each Equip Spell in your field": apply the same face-up rule unless the user says otherwise.)

### C2 design (NS or SS: "You can" add 1 Cursed Copycat Noble Arms = cid 0x10E3 from Deck; hard OPT)
- Trigger: NS-or-SS list 0x0228F60A has NO free phantom (0xE17/0xE77/0x164A/0x1B6B all claimed) ->
  add (0x111E, ...) to effects/c79_trigger_hook.ARMS (site 0x02265C44; Windrose / Ogier / Ricciardetto arms are
  in-game confirmed; RESERVE 0x30 -- check a 4th arm fits; re-test every ARMS cid after adding).
- Record: a cls1 record (phantoms plentiful: 49 unclaimed in stock) -- resolver = generic "add 1" main
  0x02207EF5 (Remus / RotA) fed by a criteria row; Remus' named-search handler 0x0223D075 reads the row's
  AUX as the target cid (aux = 0x10E3) and calls Deck builder 0x0223BC3C.
- Criteria registry is FULL -> VIRTUAL row: chain one more front on the miss tail 0x02243F24 (Tenki
  CAVE3_TENKI_H2 <- SSS CAVE3_SSS_H2 ...), own 0x40-aligned ov5 row slot; widen earlier verifies.
- "If ... You can" must NOT miss timing: optional triggers go through 0x021EE0E0 -> admit 0x111E into the
  never-miss IF-cid tree (Shadow Mist / Arms AR_MISS pattern) and give the record a timing_class_hook arm if
  its +0x10 isn't a classifier-known tag.
- OPT: turn-log pair (post in cost, desc[+7]-guarded query in cond), a DIFFERENT key/param from C1 and C3.

### Noble Arms N2 design (ignition while equipped to a Warrior; HOPT)
- Shape = Infernoble Arms E1 (Joyeuse/Durendal/Almace, in-game confirmed 2026-10-22, notes/infernoble-arms-findings.md):
  an ignition on a face-up Equip Spell is a **cls3 record** (Spark Blaster 0x1909 cls3[216] shape); Almace E1 = own
  pick / zone UI / move 0x021C7484 / link 0xA machine. cls3 phantoms: 21 unclaimed in stock.
- (a) Warrior-only SS lock: Durendal E2 reuses Ricciardetto's lock node {0x4FE6, kind 1} (front at 0x021BA368
  ahead of Obedience's LOCK) -> post the same node; applies even if the Summon fails ("also").
- (b) Deck pick: criteria word (KB dispatch.criteria_word_fully_decoded, matcher 0x0223BA24): race bits 31:27,
  ATTRIBUTE 26:24, LEVEL 21:18 (== when bits 22/23 clear), low 0x0002 real card. Build at resolution
  word = 15<<27 | attr<<24 | lvl<<18 | 2 and write it into Noble Arms' OWN virtual criteria row (Animadorned
  wrote its row +0xA at runtime; never bake a row address). "Different name": Deck callback excluding
  cid == 0x021A3320(holder) (Ogier C2H / Oliver HANDCB callback shape, [sp+4] = excluded cid). Deck builder
  0x0223BC3C records list-meta zone 0xD (Almace) -> summon commit 0x02269315 (zone-agnostic, Astolfo).
- (b') "equip it with this card" = **native relink 0x021C4BF0(equip_loc, new_target_loc)** -- Equip Shot 0x1E49
  (cls0[969] @0x02284124, res 0x02229621) phase 0x80 -> 0x0220E22C: t0 = 0x022349B0(desc,0) (the equip),
  t1 = (desc,1) (new monster), recheck 0x0224A924, legality 0x021A1190(t0s,t0z,t1s,t1z), holder
  0x021A0F10(t0) != t1, then `bl 0x021C4BF0` @0x0220E2C8 with (t0 loc, t1 loc) as u16 (zone<<8|side).
  0x021C4BF0 finds the holder via 0x021A0F10 (scan for link kind >= 0xA via 0x021A0C94) and special-cases only
  Vicious Claw 0x1D14 / Double Tool C&D 0x200D. Disassembly only -- UNPROVEN in-game for this use.
- (c) destroy the OLD holder (saved BEFORE the relink): generic destroy by loc (Catsith / Roland record shape);
  "then" = only if (b) happened.
- Offer cond: this card face-up, holder = 0x021A0F10(desc side, desc zone) != 0xFFFF, holder is Warrior
  (0x021B8E30(hs, hz, 0xF)), free MZ, HOPT turn-log (desc[+7]-guarded), >= 1 Deck match.
- Holder's Level = 0x021B8064(hs, hz) (current). Holder's CURRENT ATTRIBUTE = **0x021B8E48(side, zone, 0)**
  (disassembled 2026-11-04): base = 0x0202ABC8(zone cid) @0x021B8EBA, then card-specific overrides (kind-5
  rider path only for cids 0xF47/0xF49/0xF57/0xF82 when 0x020230AC(cid) -- NOT general), Synchro-ish path
  0x021B3794 when 0x021A1C54, and the S/T-zone scan for the newest face-up **DNA Transplant 0x171F**
  (literal @0x021B9058; declared attribute = [zone_rec+0x40]) + 0xEAD arm -> 2 (DARK). Sibling of the race
  getter 0x021B8E30 just above it. EXECUTED (disguise_rider_probe.py, rom_infernoble.ml5, function bytes
  0x021B8E48..0x021B9290 identical to stock): Robotic Knight 0x13A3 printed 4 (FIRE) -> current 4.
  Ruled out: a generic kind-5 {own cid, attr} rider changes it (values 1/6 -> still 4).
  UNPROVEN: the DNA Transplant branch by execution (no savestate with it face-up).
- **RULING (user 2026-11-04): CURRENT values** of the equipped monster's Attribute and Level.
- OPEN: Noble Arms needs its own virtual criteria row (second new one after Disguise C2's) -> two fronts or one
  front with two cids on 0x02243F24.
- N1 (+200 ATK/DEF per face-up Equip Spell in your field + GY): Captain Oliver's stat-recompute front 0x021B7088
  (grant bsearch keyed by equip cid r5) + Sea Lancer's once-per-computation rule; reuse C1's Equip-Spell scan.
  Kill Cyber Shield's grant row[17] (+500) @0x0226E016. N0: equip-tree arm 0x021D7A7C -> `b 0x021D7FA4`.

### BUILD PLAN (user 2026-11-04: "Both at the same time, Same file")
- Module otn_enhanced/cards/disguise_copycat.py: TWO dsl specs (0x111E Disguise, 0x10E3 Noble Arms), one
  combined main/verify; build script _build_disguise_copycat.py; out rom_disguise_copycat.nds.
  NOT in steps.STEPS / SHIPPED (single-card test ROM only).
- Base = chain ROM rom_all_patches.nds (2026-11-04 09:54): the shared fronts we join only exist there.
  Newer than it: ydc_decks.py (user's uncommitted CPU-deck edit, effect-irrelevant), author_facts (mine),
  card-art tools -> NOT rebuilt.
- Phantoms in the CHAIN image (this session): cls3 21 unclaimed (0xE73, 0xE88, 0x14C5 ...), cls1 49 (0xE8A ...),
  **cls2 ONLY 0x1B19 left** (still listed in list106 @0x0226E9E6, 0x022709D0, ARM9 -- harmless for a non-card
  cid) -> C1 spends the LAST cls2 phantom: flag to user. (0x234D is gone in the chain: tg_warwolf phantoms.)
  0x111E / 0x10E3 own ZERO cls0-3 records in the chain image.
- ov5 free: CAVE_FREE 0x023AC1B0 .. RESERVE end 0x023AE120 = 0x1F70 B.
- C3 cls3 = {0x111E, RES, FILT, COND, COST, +14 0x02234D81}; +14 PROVEN cid-blind: `ldr r3,=0x02234CA5 ;
  movs r2,#0x6F ; bx r3` (target-select step, prompt 0x6F); also used by Uni-Zombie (in-game confirmed).
- OPT keys (turn-log kind 1, slot 0x0B): C3 0x111E, C1 0x511E, C2 0x711E, N2 0x50E3 (Infernoble high-bit idiom).

### C3 pre-build risk checklist
1. Per-cid gates on 0x111E: PROVEN none in data (donor_scan CLEAN) and none by base+-imm (scan + control).
   ASSUMED: none in jump tables / stack switches (scanner blind spot).
2. Zone: PROVEN by disassembly -- filter 0x021DA928 + mask 0xC14 = monster zones, either side; race
   via 0x021B8D90 mask. Riders written on Disguise's own (desc[2], desc[3]).
3. Text blob: PROVEN n/a (CARD_TEXT re-emit, no slot limit).
4. OPT stamp: PLANNED in the +10 cost (turn-log node, Mystic Piper pattern), cond guarded on desc[+7].
   ASSUMED until built: +14 = 0x02234D81 is cid-blind (not yet disassembled) -- or use 0.

### Build progress (2026-11-04, AWAITING IN-GAME TEST -- nothing built into a ROM yet)
- C sources: otn_enhanced/cards/c/disguise.h (shared: is_equip_spell, count_equip_spells face-up+GY,
  is_equipped = Oliver's scan, opt_used), disguise_c3.c (FILT 0x40 / COND 0x60 / COST 0x24 / RES 0x84),
  disguise_c1.c (COND 0xCC / RES 0x40). All compile Thumb-1 clean via asm/cc.py.
- engine_syms.txt + engine.h gained: rider_attach 0x021C479C, pick_validate 0x022349B0, revalidate 0x0224A924,
  level_of_zone 0x021B8064, zone_card_resolve 0x021A3320, race_bit_test 0x021B8E30, is_tuner_rt 0x021A1C7C,
  equip_target_of 0x021A0DF8, spell_type 0x0202ABE8, handss_res 0x02206ABC (each cites an existing KB fact).
- PROVEN by disassembly this session: 0x021AD870(side) = thunk to 0x021AD79C with r1 = 0; r2 is only saved
  (push), never read -> free-MZ check needs side only.
- N1 site facts (0x021B7088 inside recompute 0x021B44C0): r5 = equip cid = 0x021A36EC([sp+0x7C], [sp+0x78])
  (@0x021B703A..42) -> equip card's SIDE = [sp+0x7C]; native grant adds row+2 to [sp+0xB0] (ATK) and row+4 to
  [sp+0xAC] (DEF) per equip card (@0x021B7098..AA). Behind a 6-reg push: side [sp+0x94], ATK [sp+0xC8], DEF [sp+0xC4].
- Cls slot picks: C3 cls3 phantom 0x0E88; N2 cls3 0x14C5; C1 cls2 0x1B19 (LAST); C2 cls1 TBD.
- **Virtual criteria rows: the Rulers window is FULL.** H3 (Rulers' CAVE3_RUL_H3 @ site 0x02243F62, stock
  `adds r3,r6,#0 ; movs r0,#0xC`) decodes index r6 > 0x3FFF as row = CAVE_RUL_ROWS + ((r6>>8)-0x40)*0x40 and
  resumes at 0x02243F70 with r0 = &row, r3 = [row+4] (native: `adds r1,r5 ; adds r2,r7 ; blx r3`). u16 index ->
  k <= 0xBF -> window 0x023A6BF0..0x023A9BB0; scan of the CHAIN ROM: every 0x40 grid point there is a live
  slot (13 zero points are all slack inside live reserves: BR_COND, CR_RES2, IK_PROT, GYV_ROWS ...).
  DESIGN (test ROM): own namespace -- H2 front returns 0xFF00|j for 0x111E / 0x10E3; an H3 FRONT ahead of
  Rulers' H3 maps r6>>8 == 0xFF -> CAVE_DC_ROWS + (r6 & 0xFF)*0x10, else tail-jumps to Rulers' H3.
  (high byte 0xFF = k 0xBF: no shipped virtual row uses it). Ship-time: widen Rulers/Tenki/SSS verify.
- N2 (b) = the native Deck-SS machine **0x02206CAD** (KB counter_engine 0x02206CD2 VERIFIED blueprint:
  0x80 gates + count via the card's own criteria row -> 0x7F/0x7B; 0x7E picker 0x0219C430(side,6,cid,param);
  0x7C commit -> 0x78; 0x78 shuffle -> 0x64). Wrapper plan: own 0x80 prologue (lock + row word/exclude +
  stash), delegate, intercept the 0x78 return with a private phase (relink 0x021C4BF0 + destroy old holder),
  then hand back 0x78. ⚠️ NAST: three attempts to WRAP a native resolver froze -- prove by execution first.
- Destroy = DESTROY_AT 0x021CF389(desc, side, zone) (infernoble :4818/:5661, after VALID_AT 0x0224A925);
  KB dispatch.destroy_then_protocol: 0x021CF388 -> 0x021CDD4C(desc, 1<<(side*16+slot), 0xE, 0x10000002).
- **BUILD 1 (2026-11-04): rom_disguise_copycat.nds sha256 638ff9fd9bee7d6c7d1a17af661cce05d7d458e8262df38da32c74b78c3ad348,
  verify 0x111E 36/36 + 0x10E3 16/16. AWAITING IN-GAME TEST.** Layered on rom_all_patches.nds (chain).
  Records: cls3 0x111E @40 (phantom 0x0E88), cls2 0x111E @43 (0x1B19), cls1 0x111E @67 (0x0E9F), cls3 0x10E3 @36 (0x14C5).
  Deviations from the plan, both forced: (1) the shared c79 stub cannot hold a 4th arm (60 B > 0x30) -> a 4-arm copy
  at CAVE_DC_C79 and the c79 site BL re-pointed there (ship-time: move c79 to a bigger slot); (2) the Cyber Shield
  grant row is NOT at 0x0226E016 in the chain (that row is 0x10E2 300/300 there) -> located by searching the table.
  In the chain the equip-switch entry 0x021D73A0 is Infernoble's EQFILT front BL (0x023A7D60), not `ldr r7`.
- EXECUTION PROOFS on the built ROM (2026-11-04):
  N0: equip tree walked from 0x021D73A4 (r7 = stock pool word 0x1ABA, = EQFILT's replay for a non-Infernoble cid):
    chain 0x10E3 -> 0x021D7A7C (Harpie arm); BUILT 0x10E3 -> 0x021D7FA6 (default = Black Pendant / junk cid);
    Molting/Heirloom 0x2124 -> 0x021D7F3A in both (unchanged).
  Rows (scratch/disguise_row_probe.py: savestate rom_all_patches.ml4 data RAM + BUILT ov3/ov5 code):
    0x02243B9C(cid): 0x111E -> 0xFF00, 0x10E3 -> 0xFF01, Tenki 0x1777 -> 0x5B00, SSS 0x130A -> 0x5F00 (chain intact).
    0x02243F38(0, cid, 0, idx): 0x111E -> H3 front -> Remus handler 0x0223D074 -> Deck walker 0x0223BC3C;
    0x10E3 -> H3 front -> N2 handler 0x023AC920 -> Deck walker -> N2 callback 0x023AC950 called; Rulers H3 NOT hit.
    Regression: Tenki 0x5B00 -> my H3 front -> Rulers H3 0x0220A5E0 -> Tenki handler 0x0223CAD8.
    (the run stops later at an ARM-state BLX 0x020989A4 inside the walker -- thumbemu limit, past the routing.)
- NOT executable offline: helpers that reach ITCM ARM code (0x021A36EC -> bx 0x01FFFA1C, even = ARM state;
  0x021A1C7C) -- thumbemu is Thumb-only. probe now maps ITCM from the ARM9 autoload, but ARM is still unsupported.
  So C3 FILT / C1 COND / N1 count / N2 COND+RES were NOT executed end to end; the native callees are in-game proven
  by shipped cards (Oliver, Ogier, Copy Plant shape), the stubs are compiler output.
- VERIFY SWEEP on the test ROM: 93 passed, 19 failed. bulk_ydcs fails IDENTICALLY on the base chain ROM (user's
  newer ydc_decks.py) -> pre-existing. The other 18 are owner checks of the shared sites/stubs this build fronts or
  rewrites (expected on a test ROM): timing stub byte-exact (14 timing-arm owners), c79 site, H2/H3 (Rulers, Tenki,
  SSS), miss node (Infernoble AR/M -- M_MISS bytes are IDENTICAL, its check derives the chain from the site head),
  ARM9 H4 (Turpin/Roland), stat site (Captain Oliver). ov3 diff chain->built = only the 6 hook sites, the grant row,
  and the 3 cls-table insert shifts. Ship-time: widen those owners' verify (ik_next-style map) + move c79 slot.
- Warrior-only lock = turn-log post (side, key 0x4FE6, kind 1) read by Ricciardetto's front at 0x021BA368
  (infernoble :1748 / :1917 / :5920 -- Durendal reuses it).

## Ruled Out

- Mage Power 0x145D, Big Insect 0x0FD7 as donors (user veto 2026-11-04).

- 3DS build as an architecture source for this card (post-dates it by a decade).

## Open Questions

- C3 rest: target filter "non-Tuner Warrior with a Level" (field, either side) and the activation
  condition "while this card is equipped with an Equip Card" -- find a native cls3 cond/+08 to reuse.
- C3 name rename is invisible to ARM9-side reads (0 ARM9 callers of 0x021A3320); does any check
  Disguise needs (e.g. Noble Arms "different name", OPT keys) read the name via ARM9?
- Noble Arms N0: other per-cid trees for 0x10E3 (Equip activation tree ~0x021F076E) not emulated.
- Criteria registry is full -> C2 search + N2 Deck pick need virtual criteria rows (Tenki/Sacred Sword fronts).

## Next Experiment

IN-GAME TEST of BUILD 1 (rom_disguise_copycat.nds 638ff9fd...ad348). A normal duel (NOT the puzzle editor: ov5).
Disguise = Monster Tamer's slot; Noble Arms = Cyber Shield's slot.
- D1 (C1): a FACE-UP Equip Spell on your field, or one in your GY -> Disguise's hand effect is offered and Special
  Summons it. Only a face-DOWN Set Equip Spell and none in GY -> NOT offered. Once per turn.
- D2 (C2): Normal Summon Disguise (and separately Special Summon it with D1) -> "You can" prompt -> add Cursed
  Copycat Noble Arms from Deck. Declining costs nothing. Once per turn. Also: SS'd mid-chain by another effect ->
  still offered (never-miss).
- D3 (C3): Disguise equipped with any Equip Card -> target a face-up non-Tuner Warrior (either side) -> Disguise's
  Level AND name become the target's; reverts at end of turn. Not offered when unequipped; Tuners / non-Warriors not
  targetable. Once per turn.
- N0: Noble Arms equips to ANY monster (not only Harpie Lady).
- N1: equipped monster +200 ATK and DEF per face-up Equip Spell on its controller's field (incl. itself) + in GY.
- N2: equipped to a Warrior -> activate: SS from Deck a Warrior with the same CURRENT Attribute and Level but a
  different name; Noble Arms moves onto it; the old monster is destroyed; for the rest of the turn only Warriors
  can be Special Summoned. Combo: Disguise renamed by C3 -> the Deck pick excludes the COPIED name.
- Regression spot checks (shared sites fronted): Tenki / Sacred Sword searches, a Dragon Ruler, Infernoble Arms
  (never-miss + Captain Oliver +500), Roland / Turpin / Ricciardetto hand effects, Windrose / Ogier NS-SS triggers,
  one timing-arm card (Psi-Reflector).
If a step fails: savestate at the failure point; do not patch blind.
