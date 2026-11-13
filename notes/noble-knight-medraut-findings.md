# Noble Knight Medraut — findings

Started 2026-11-04. Status: **SHIPPED 2026-11-04 on user approval ("ship it") — ALL EFFECTS IN-GAME CONFIRMED BY USER 2026-11-04 ("All the effects are confirmed").** The five declared deviations below were NOT separately accepted by the user. Chain: 123/123 steps, rom_all_patches.nds sha256 b2fe93346ea35588c4a868dd9a98bca57bb69884aa2ca58dcbad0261aa235292; verify sweep 113 passed / 1 failed (data.bulk_ydcs: wcs084_formula + rpg048_4_nelson deck mismatches, from the user's uncommitted ydc_decks.py, not Medraut). Card art line added.

## Scope (user, 2026-11-04)
- Whole card. Build off Disguise / Cursed Copycat Noble Arms (cards/disguise_copycat.py) if possible.
- Donor search extended to Normal Monsters Lv4-8.
- Clause 4's "Equip Spell you control" = ANY Equip Spell.

## Confirmed
- Printed text (scratch/ygoprodeck_cache.json, id 59057152): Warrior/Effect, LIGHT, Lv4, 1700/1000.
  > This card is treated as a Normal Monster while face-up on the field. While equipped with a "Noble Arms"
  > Equip Spell, this card becomes an Effect Monster with this effect.
  > ● This card becomes DARK and its Level is increased by 1. Once per turn, if you control no other monsters:
  > You can Special Summon 1 "Noble Knight" monster from your Deck in Defense Position, except "Noble Knight
  > Medraut", and if you do, destroy 1 Equip Spell you control.
- Not implemented anywhere in otn_enhanced (grep this session). Only mention: notes/infernoble-ogier-findings.md
  says the 3DS ships it.
- 3ds_extract/ is ABSENT from disk this session (ls failed) -> 3DS second-source lookup not possible.
- Donor scan this session (`-m otn_enhanced.tools.donor_scan --free --level N`): clean (zero aligned u16/u32
  in ov3+arm9) Normal donors exist at Lv4 (many), Lv5 (5), Lv6 (10), Lv7 (7), Lv8 (5). Table in the chat report.
- Prior user rulings that apply (infernoble.py): "Noble Arms" = the four Infernoble Arms (+ Cursed Copycat Noble
  Arms, 0x10E3); "Noble Knight" == "Infernoble Knight" in this build (KNIGHTS, infernoble.py:6691).

## Donor = Armored Lizard 0x0FD9 (user pick 2026-11-04) — vetting this session
- (a) Normal Monster, Lv4 EARTH Reptile 1500/1200. `donor_scan 0x0FD9` -> "VERDICT: CLEAN - no data structure names
  this cid". Name slots floor 14 B, desc floor 51 B; irrelevant if the cid joins card_text.CARD_TEXT (re-emit).
- (c) Four ARM9 data-region u16 hits (0x0209D6D2, 0x0209E400, 0x0209E6D0, 0x020A1402) dumped this session: each sits in a
  run of SEQUENTIAL cids (0xFD6,0xFD7,0xFD8,0xFD9,0xFDA...) paired with a per-index value (0x227,0x22D,0x234...,
  0xFDC0,0xFDC6...) = generic every-cid index tables, NOT card-specific. Harmless. baseimm_scan 0x0FD9 -> no hits.
  Residual: stack-based/branch-target switch blind spot (same as every donor).
- (d) props to rewrite: Lv4 LIGHT Warrior 1700/1000, type Effect (vanilla-ignition recipe needs Effect type; see Open).

## Hook sites for the continuous half (disassembled stock ov3 this session; UNPROVEN until executed)
- Level getter 0x021B807C(side, zone, 0): entry saves side [sp], r6 = zone*0x14; final formula at 0x021B88B4:
  `ldr r0,[sp,#0xc]` (base) ... `ldr r0,[sp,#0x24]; adds r1,r4,r0; ... adds r0,r0,r1` then clamp >= 1. A +1 for
  Medraut-equipped-with-Noble-Arms can be added into [sp+0x24] (or r4) just before 0x021B88BA. Needs side+zone
  at that point ([sp]=side; zone only as r6/0x14 -> must re-derive) and a per-cid test of the zone's cid.
- Attribute getter 0x021B8E48(side, zone, 0): base attribute = 0x0202ABC8(cid) @0x021B8EBA, result [sp+0x4C];
  DNA Transplant override later (KB). A DARK override for Medraut-equipped = a front at the exit / after 0x021B8EBA.
- Already-proven alternative for Level: rider {key 0x22EB (Egotistical Ape), kind 3, +1} honoured by the getter
  (dispatch.level_rider_key_is_a_selector). But a rider is NOT conditional: it would stay after the Noble Arms leaves.
- Precedent for a continuous "treated as" hook: naturia_pineapple.py (race resolver 0x021B88F0 board-scan front).

## Reusable pieces from Disguise/Infernoble (grep this session, UNVERIFIED until reused)
- is_equipped = Captain Oliver's scan (disguise.h), Equip Spell test (spell type 3 + race 'Spell'),
  Noble Arms set: infernoble ARMS_CIDS (Joyeuse, Durendal, Almace, Hauteclere) + 0x10E3 (to confirm).
- Noble Knight set: infernoble KNIGHTS. Deck SS native 0x02206CAC; Deck-pick callback shape Ogier C2H / Oliver HANDCB.
- Virtual criteria row namespace 0xFF00|j (Disguise: j=0,1 used) via CAVE_DC_H3 -> CAVE_DC_ROWS.
- cls3 ignition record: Mystic Piper recipe; cls3 phantoms in stock 21, Disguise spent 0x0E88 + 0x14C5.

## Open (new)
- "Treated as a Normal Monster while face-up": engine treats type from card_prop; Effect type needed for the cls3
  ignition. Cards that test "Normal Monster" would see an Effect Monster. Ask user whether to accept as a declared limit.

## Ruled Out
- (none yet)

## Open Questions
- Does "Noble Arms" for equip-detection include Cursed Copycat Noble Arms 0x10E3? (assumed yes, CONFIRM)
- Continuous "DARK + Level+1 while equipped with Noble Arms": hook the Level getter 0x021B8064 / attribute
  getter 0x021B8E48 (both touched by the chain) vs a rider. Needs disassembly; UNPROVEN.
- "Treated as a Normal Monster": a Normal donor gives this for free in the engine, but the effect clause must
  still be offered only while equipped (condition), and type flips Effect<->Normal is cosmetic. UNPROVEN.
- "Once per turn, if you control no other monsters": cond = own monster count == 1 (this card). Check the
  count primitive used by shipped cards.
- Clause 4 destroy: any Equip Spell you control, player-chosen; "if you do" = only after the SS succeeded.

## BUILD 1 (2026-11-04) — AWAITING IN-GAME TEST
- Module otn_enhanced/cards/noble_knight_medraut.py, C stubs cards/c/medraut.{c,h}, build script _build_noble_knight_medraut.py.
  NOT in steps.STEPS / SHIPPED / apply_all_patches. Out: data/over_the_nexus/working/rom_noble_knight_medraut.nds
  sha256 69db89be140af2672ee38a080fdf4a5bfceed90e8020516ab980a51835bea13d (layered on rom_all_patches.nds, which carries Disguise);
  own verify 29/29; disguise_copycat 43/43 + 16/16, dragon_rulers 62/62, fire_formation_tenki 18/18, sacred_sword 11/11 on this ROM
  (owner verifies run individually; NO full sweep, NO chain build — per scope rule).
- Slots claimed: ov5 CAVE_MK_* 0x023AC9B0..0x023ACF10 (13 slots, ledger emitted, guard OK); CAVE_FREE -> 0x023ACF10;
  cls3 phantom 0x0E73 dropped, 0x0FD9 inserted @29; donor 0x0FD9 claimed in check_allocations; virtual criteria index 0xFF10
  (DC namespace never issues 0x10+); OPT key 0x5FD9.
- Wiring: H2 0x02243F24 and H3 0x02243F62 fronts AHEAD of Disguise's (dc_next gained MK_H2->DC_H2, MK_H3->DC_H3; dc_skip now
  follows chains; Disguise's own verify loosened to accept fronts ahead); Level getter BL @0x021B88BA; attribute getter BL
  @0x021B927E; Deck-SS position BL @0x02206E70. cls3 record {0x0FD9, RES, FILT, COND, COST, 0x02234D81 (Copy Plant tsel)}.
- Props rewritten: Lv4 LIGHT Warrior 1700/1000 Effect Monster. Text in card_text.CARD_TEXT[0xFD9] (EN uses  for the bullet like
  Horn of Olifant; j/k/r use the real bullet). bulk_card_pack key "Armored Lizard" renamed. dsl.make now encodes the fallback
  ASCII bytes with errors="replace" (bullet).
- Mechanism PROVEN by static checks only (NOT executed): stubs Thumb-1 clean, no even BLX literal, hook windows read from stock
  disassembly (KB facts added UNVERIFIED), Disguise/Noble Arms machinery reused as-is.

## DECLARED LIMITS / DEVIATIONS (not acceptable until the user says so)
1. Equip Spell to destroy is chosen AT ACTIVATION (cls3 +08/+14 target step), not at resolution; the printed text does not target.
2. Medraut is an Effect Monster (card_prop type) at all times; "treated as a Normal Monster while face-up" is not implemented.
3. The Deck pick lists the Infernoble Knight set (infernoble KNIGHTS, 13 cids incl. Angelica); Medraut itself is NOT in that set
   for other cards' "Noble Knight" checks.
4. The Equip Spell destroyed must be face-up in your S/T zones 5..9 (any Equip Spell, per ruling).
5. "if you control no other monsters" counts every occupied monster zone (face-down included).

## Next Experiment (in-game, normal duel, NOT the puzzle editor)
- M0: Medraut with NO Noble Arms: Lv4 LIGHT 1700/1000, effect NOT offered.
- M1: equip Cursed Copycat Noble Arms (or an Infernoble Arms): card shows Lv5 / DARK.  Remove the Arms (destroy it): back to Lv4 LIGHT.
- M2: only monster on your field, equipped: activate -> pick 1 of your face-up Equip Spells -> pick a Knight from the Deck ->
  it arrives in Defense Position, then the picked Equip Spell is destroyed.  Not offered with another monster on the field,
  or twice in a turn.
- Failure: take a savestate AT the failure; do not patch blind.
