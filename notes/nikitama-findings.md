# Nikitama — findings (started 2026-10-13)

Printed text (scratch/ygoprodeck_cache.json, passcode 24701235, Spirit L4 LIGHT Fairy 800/1800):

> Cannot be Special Summoned. During the End Phase of the turn this card is Normal Summoned or flipped face-up:
> Return it to the hand. During the turn this card was Normal Summoned or flipped face-up, you can Normal Summon
> 1 Spirit monster in addition to your Normal Summon/Set. (You can only gain this effect once per turn.) When this
> card is sent to the Graveyard: Draw 1 card. You must control a Spirit monster to activate and to resolve this effect.

Clauses:
- C1 cannot be Special Summoned
- C2 End Phase return (NS or flipped face-up)
- C3 extra Normal Summon of 1 Spirit during the turn it was NS / flipped (gain once per turn)
- C4 sent to GY -> draw 1; must control a Spirit on activation AND resolution

Scope: WHOLE CARD (user 2026-10-13: "Do the whole card").
Status: RE / design. Nothing built. Nothing in-game tested.

## Confirmed (this session)
- Not in the 3DS build: CARD_Name_E.bin has no "Nikitama" (Aratama present, 3DS cid 0x2A0E). No 3DS template.
- KB proofs: verify_knowledge 626 PASS / 0 FAIL / 75 UNVERIFIED (2026-10-13).
- SPIRIT END-PHASE POSTER = 0x02254B64 (side): loops zones 0..4 (r4), slot rec r5 = player + zone*0x14;
  requires is_spirit(cid) @0x02254B92, [r5+0x3C] != 0 (face-up), 0x021A32B4 alive, [r5+0x44] bits 26/27 clear.
  Then if 0x020232AC(cid) == 0: ARMED iff [r5+0x44] bit 16 | bit 17 | bit 19; else ARMED iff bit 18.
  Posts via 0x021D3230(side, zone, 6, ...). (Disassembly of stock ov3, this session.)
  => "this card was Normal Summoned or flipped face-up this turn" == the field slot's +0x44 bits the engine
     itself uses to arm the Spirit return. Reusable as C3's window predicate.
- Savestate corpus (57 duel states, scratchpad slots.py): bit 16 of [slot+0x44] set on monsters summoned
  this turn by the turn player (e.g. rom_sakitama_compact.ml1: Sakitama 0x13E5 NS'd by its C3 -> 0x00410100).
  Bits 17 / 19 never observed set in the corpus (no flip state in it). Bit meaning per summon kind NOT proven.
- 0x021D2A40(side, zone, bit, val) is the slot-flag setter for some bits (0x05, 0x16, 0x1B ...); no caller
  passes bit 0x10/0x11/0x13 (static arg scan) -> bits 16/17/19 are written elsewhere (not found yet).
- C4 sent-to-GY admission: KB event.sent_to_gy_cid_switch (VERIFIED) -- hardcoded sorted cid chain at
  0x021D1392; a donor needs its terminal node re-keyed (Shadow Mist, in place) or an ov3 stub (Eclipse Wyvern).
  Draw resolver 0x022065B9 + count table row (resolver.draw_n_is_a_per_cid_table,
  dispatch.draw_condition_needs_the_count_row).
- Donor scan (donor_scan, this session):
  - Chamberlain of the Six Samurai 0x1C6C (EARTH Warrior Lv3 200/2000): CLEAN.
  - Charcoal Inpachi 0x17CD (FIRE Pyro Lv1 100/2100): CLEAN.
  - Mystical Shine Ball 0x173D: ENTANGLED -- criteria row[274] {0x1741 Agent of Creation - Venus, aux 0x173D,
    0x0223CF45} (Venus summons it by name). Rejected.
  - Mokey Mokey 0x1782: named by Mokey Mokey King 0x183D row[329]. Rejected.
  - Unicycular 0x21A4: named by Bicular 0x21A5 row[1076]. Rejected.
  - Archfiend Marmot 0x1070, Petit Moth 0x10BC, Thousand-Eyes Idol, Skull Servant, Sapphire, Labyrinth Wall:
    ENTANGLED (unclassified u32 hits / fusion material).

### Session 1 design facts (2026-10-13)
- Donor: **Wolf 0x0FE3** (EARTH Beast Lv3 1200/800), user pick 2026-10-13 from 17 CLEAN ATK<1500 Normals
  (donor_scan CLEAN; no cid literal in any finished_patches module except bulk).
- C3 ruling (user 2026-10-13): the extra Spirit Normal Summon PERSISTS after Nikitama leaves the field.
  => grant must be a player-slot node posted at NS/flip time (Raptor/Sakitama shape), not a field check.
- Free slots (scratchpad phant.py over rom.nds AND chained rom_all_patches.nds, minus PHANTOM_CLAIMS):
  cls1 phantom 0x0E2F (2 rows, unclaimed); cls2 0x1B18 (1 row, unclaimed); code-7-or-8 list 0x120E
  (unclaimed); flip list 0x1534 (only claim = quickeffect_list, other pool; LAST flip-list phantom);
  draw-count 0x0E86 (unclaimed); leave-mask 0x0E1C (only claim cls2_table, other pool).
- rom_all_patches.nds (Oct 13 12:34) is newer than every finished_patches / EE / ov3_compaction module.
- Sent-to-GY switch: 0x0FE3 (and 0x0FE2/0x0FE4) ends at node 0x021D13C2 `ldr r0,=[0x021D15A4] ; cmp r5,r0 ;
  bne ; b arm`, which in the CHAINED ROM tests 0x0FE1 (Petiteranodon re-keyed the literal; arm 0x021D18D2).
  Node bytes 0x021D13C2 = 7848 8542 (stock ldr/cmp) in both images -> 4-byte BL front possible; re-key
  impossible. Traced with patch_snoww._switch_leaf (scratchpad gytrace.py).
- Native templates (stock cls dumps): Maharaghi 0x14FD cls1 #1 = {0x0220FF51,0,0,0,0} (mandatory NS/flip
  trigger, no +10 tag); mandatory sent-to-GY with cond = 0x1B8B cls2 {0x02206139,0,0x021FC009,0,0};
  Cyber Phoenix 0x1A07 cls2 {0x022065B9 draw,0,0x021F069D,0x021E51E5,0}.
- ov3 pool free space (cave3 constants vs pool_blocks.FREE_RUNS): 0x542 B total; biggest runs
  0x021F1B2C (0xCE), 0x0220A570 (0xCE), 0x0221AB78 (0xA8), 0x02220B3C (0xA6), 0x021FADB8 (0x9E), 0x021F1008 (0x84).

### BUILD 1 (2026-10-13) -- PUZZLE TEST BASE, AWAITING IN-GAME TEST
- User approved the plan incl. ASSUMED items (C3 gain = visible mandatory chain link; C4-on-Tribute timing
  settled in-game) and asked for its own ROM on the ov3-compact base, all stubs ov3, ov5 after confirmation.
- `_build_nikitama.py --compact`: rom_ov3_compact -> EE ninishi -> patch_scrap_raptor -> patch_nikitama ->
  data/over_the_nexus/working/rom_nikitama_compact.nds,
  sha256 3276fd151584797b274cc792973cc78a2b42a47bc1ab6a4ab1cd498f0dd5855f, verify 26/26 PASS (static only).
  Fronts chain Raptor's CAVE3_SR_* there (arm 0x021C74CC, spent 0x0221AE54, pred 0x021F10B4, field
  0x021F17DC, count 0x021F94C8, match 0x021FAE58); GY node literal there = stock phantom 0x0EC9.
- `_build_nikitama.py` (chain variant, NOT for testing yet): rom_all_patches -> rom_nikitama.nds,
  sha256 4caf6ecd16764863aef04f65f83b20d8c14f230fd581fe59e701cff740ba7ebf, verify PASS; fronts chain
  Sakitama's CAVE3_SK_* (0x02212330 / 0x02212404 / 0x0221236C / 0x022123B4 / 0x022123E4 / 0x021F0FF4),
  GY stub replays literal 0x0FE1 (Petiteranodon).
- ov3 slots cave3.CAVE3_NK_* (11); check_allocations OK. All blobs pass assert_thumb1_only; disassembled.
- EXECUTION PROOF on the compact ROM (scratch.nikitama_equiv, adapted from sakitama_equiv; old image = the
  same bytes with the six site BLs restored via patch_nikitama.unfronted and the GY node restored):
  identical 11339, Nikitama-owned 149, BAD 0. GY part walks cids 0..0x27FF with patch_snoww._switch_leaf:
  only 0x0FE3 changes leaf (-> accept 0x021D19BE).
  Owned route: site 3 phase 0, grant (G,1), counter 1 -> pool 0x02261F84 = 0x3E51, [0x0229DD94+0x34] = 1,
  no announce, phase -> 0x64; phase 0x64 (ack 1) -> desc+0x12 = 0x3E51; site 4 desc+0x12 = K ->
  POST(0, 0x3E51, 1, 0); site 1 Spirit -> 0x3E51, non-Spirit -> 0; site 2 with node K -> 1.
- NOT proven (needs the in-game test): cls1 #1 gain trigger on NS / Flip Summon / battle flip; the hand menu
  offering the Spirit summon after the gain; C4 from field / hand / Deck; 0x021ACFE8 + is_spirit at runtime.

### IN-GAME CONFIRMED + SHIPPED (2026-10-13)
- User verbatim: "Everything confirmed, move to ov5 and ship it!" -> whole card in-game confirmed by user
  2026-10-13 on rom_nikitama_compact.nds (3276fd15...855f, puzzle base, all stubs ov3).
- Ship: card-only stubs -> ov5 CAVE_NK_GAINCOND 0x023A5840 / GAINRES 0x023A5870 / DRAWCOND 0x023A5890 /
  DRAWRES 0x023A58C0 (CAVE_FREE -> 0x023A58F0); cave3 test-home slots removed; fronts + GY node stay ov3.
  steps.STEPS "Nikitama" after Uni-Zombie (must follow Sakitama + Petiteranodon); _verify_all_patches.SHIPPED;
  patch_card_genre 0x0FE3 0x1400004; bulk_card_pack 'Wolf' -> 'Nikitama'; donor notes + donor_resource.json.
  patch_sakitama.verify()/unfronted() now look through patch_nikitama.unfronted.
- EE build 112/112 sha256 7cc95c80dab2328ca82cd754ee2af5e93c8029913c3bb7713327dfbd732ed0ec (BUILD_EXIT 0);
  sweep 93 passed / 0 failed; scratch.nikitama_equiv on it 11339 / 149 / 0 BAD; ov5 stubs read back equal.
  Previous chain ROM kept at scratchpad rom_all_patches.before_nikitama.nds.
- The ov5 home itself was not re-tested in-game (same bytes, different address; records point at it).

## Inherited (UNVERIFIED until re-proven here)
- Sakitama (shipped) C3 grant machinery: six ov3 fronts at SITE1 0x021B9634 / SITE2 0x021B9F9C /
  SITE3 0x02261E3E pred, 0x02261E68 field, 0x02261E92 counter / SITE4 0x0226515C, chaining Raptor -> ninishi.
  Grant = kind-1 node on 0x13E5, spent key K = 0x3E50. A Nikitama arm would be a 4th link in that chain.
- Aratama/Sakitama Spirit recipe: card_type 15 = C1 native; one cls1 return row = C2.

## Ruled Out

## Open Questions
- C4 when Nikitama is Tributed for a Spirit Tribute Summon: is "control a Spirit" evaluated after the new
  Spirit lands? (oracle item 12)
- Which [slot+0x44] bit (16/17/19) a flip sets -- only needed if the gain trigger misses a flip.

## Next Experiment
- USER IN-GAME TEST of rom_nikitama_compact.nds (sha256 3276fd15...855f) against the 13-item oracle in
  _build_nikitama.py. Report verbatim; quote back + MY INTERPRETATION before touching anything (CLAUDE.md).
- If the gain does not trigger on a flip: savestate after the flip; check flip list / genre / [slot+0x44].
- If the extra Spirit summon is not offered after the gain: savestate in Main Phase; walk slot 0xB nodes for
  (0x3E52, kind 1) and emulate 0x021B95C4 with scratch/thumbemu.py.
- SHIP-TIME TODO (only after user approval): card stubs -> ov5 (CAVE_NK_*; retire CAVE3_NK_GAIN*/DRAW*),
  steps.STEPS after Sakitama; _verify_all_patches.SHIPPED; teach patch_sakitama.verify()/unfronted() to look
  through patch_nikitama.unfronted; patch_card_genre row 0x0FE3 0x1400004; bulk_card_pack 'Wolf' ->
  'Nikitama'; donor-pool notes Wolf -> used; scratch/donor_resource.json; rerun scratch.nikitama_equiv on the
  EE build; KB card.nikitama.
