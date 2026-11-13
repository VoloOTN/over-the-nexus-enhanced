# Uni-Zombie — findings

Started 2026-10-12. No prior patch / notes for this card (grep of
finished_patches/ and notes/ for "uni-zombie" found nothing).

## Printed text (scratch/ygoprodeck_cache.json, id 49959355)

Level 3 DARK Zombie Tuner, ATK 1300 / DEF 0.

> You can target 1 face-up monster on the field; discard 1 card, and if you do,
> increase that target's Level by 1. You can target 1 face-up monster on the
> field; monsters you control cannot attack for the rest of this turn, except
> Zombie monsters, also send 1 Zombie monster from your Deck to the GY, and if
> you do, increase that target's Level by 1. You can only use each effect of
> "Uni-Zombie" once per turn.

Clauses:
- C1 ignition: target 1 face-up monster; discard 1 card, then target Level +1. (HOPT a)
- C2 ignition: target 1 face-up monster; non-Zombie attack lock this turn,
  send 1 Zombie from Deck to GY, then target Level +1. (HOPT b)
- C3 each effect once per turn (separate flags).

Scope (user 2026-10-12): **whole card**.

## Confirmed
- Uni-Zombie is NOT in the 3DS build: no CARD_Name_E string contains
  "Uni-Zombie" (only Uni-Horned Familiar etc.). No Konami reference.
- NDS precedents (ygoprodeck text x scratch/cid_to_name.json scan, 2026-10-12):
  - Level +1 on a target: Delta Flyer 0x22F3 ("select 1 other face-up monster
    you control; increase its Level by 1", ignition OPT); Noisy Gnat 0x1E33
    (target 1 face-up monster ON THE FIELD; +1 until End Phase, hand effect).
  - Level DELTA rider = 0x021C479C(side, zone, key 0x22EB, kind 3, value) — KB
    dispatch.level_rider_key_is_a_selector / Psi-Reflector C2 + Accel Synchron.
  - Discard as effect: Moulinglacia C3 discard prim 0x022599C8 (memory, UNVERIFIED).
  - Deck->GY by race: patch_dragon_shrine (Dragon) — to inspect.
  - "Your monsters cannot attack this turn": Misfortune 0x1A0D, Proof of
    Powerlessness 0x2024. Race exception in attack gate: Mind Protector 0x1E25
    ("...cannot declare an attack, except for Psychic-Type monsters").
- Precedent records (stock rom.nds, recs dump 2026-10-12):
  - Delta Flyer cls3[700] {0x022087B5, 0x021DCD49, 0x021F01C1, 0x021E5061, 0x02234D8D}
  - Noisy Gnat cls2[370] {0x02208849, 0x021DD859, 0x021FE6F9, 0x021E8FB9, 0x02234D81}
  - Misfortune cls0[701] {0x022219BD, 0x021DA071, 0x021FA871, 0, 0x02234D99}; its
    resolver ends with turnlog post 0x021D2584(side, 0x1A0D, 1, 0) — the
    "your monsters cannot attack this turn" lock is a TURN-LOG node keyed by
    Misfortune's cid (disasm 0x02221A18..0x02221A20).
  - Lightning Vortex cls0[299] cost 0x021E4EA5 (discard 1); Aqua Dolphin
    cls3[255] cost 0x021E4ECD.
  - Delta Flyer resolver 0x022087B4: cid 0x22F3 hits the default arm (r4=0),
    then 0x02207908(desc, 3, r4, 0).
- **TWO cls3 RECORDS ON ONE CID ARE REACHABLE** via find_event_handler's
  membership list 0x02275BB8 x 0x26 (bsearch 0x02022E14 @0x0224A1E0): for a
  member, offset = desc[+0x18] - 1 (`ldrh r0,[r4,#0x18]; subs r0,#1; bmi ->
  offset 0`, 0x0224A1E8..0x0224A1F0), then leftmost+offset @0x0224A81E.
  Members include Ice Master 0x1B71, Tragoedia 0x1F99, Tempest Magician 0x1F95
  (each 2 cls3 records). Sorted; one unnamed member 0x1AF0 (phantom candidate).
  Identical in stock and rom_all_patches.nds. This CORRECTS the Accel Synchron
  conclusion "two cls3 records on one cid cannot both be reached" (it read only
  the default arm). Sibling lists: 0x02275B60 x 0x13 (event 2 -> +1),
  0x02275B86 x 0x19 (event 6 -> +1).

- Native multi-ignition = N cls3 records + list 0x02275BB8 + label rows in
  0x0226F32C + shared cond 0x021F0935 (= 0x021E5794(desc) != 0 -> 2) + shared
  cost 0x021E6871 (phase [0x0229AAFC+0x7C]: 0 prompt 0x0219ABB4 "Use which
  effect?" 0x103; 1 desc[+0x18] = choice+1 @0x021E6958; >=2 per-cid cost arms).
  0x021E5794 is a per-cid switch whose DEFAULT returns 0 (0x021E6862), so a new
  cid would need an arm there -> NOT chosen. Plan: ONE cls3 record, own
  cond/cost/resolver stubs, choice in desc[+0x18] (Ape/Accel pattern).
- Target slot2 cid-blind: 0x021DB1D9 = mask wrapper 0x021D6E40 mask 0x414,
  used by Ice Master / Cold Enchanter / Rising Energy / Shrink... all printed
  "target 1 face-up monster on the field". slot5 thunk 0x02234D81 = 0x02234CA5
  prompt 0x6F "Select 1 monster." (Noisy Gnat's).
- dlg strings: 0x103 "Use which effect?", 0xEB "Discard from your hand.",
  0x1F3 "Send 1 designated card to the Graveyard from your Deck."
- Effect discard (player-chosen) = 0x022598A0(side, 1, 0, 0), precedent Dark
  World Lightning resolver 0x0221FCB8 phase 0x7F (phase word [0x0229AAFC+0x70]).
- Target read: 0x022349B0(desc,0,0) != 0, 0x02234904(desc,0) -> side = b0,
  zone = b1; revalidate 0x0224A924(desc, side, zone) (Misfortune 0x022219BC).
- Deck->GY Zombie: criteria {cid, 0xFFFF, 0x0223CAD9, 0x10000002} (race 2<<3
  in top byte; Dragon 0x08000002 Dragon Shrine, Reptile 0xA0000002 Snake Rain);
  resolver 0x02208DD4 phase 0x7C follow-up via deck_send_follow_hook.ARMS.

- ATTACK GATE: 0x021A4670(r5 side, r4 zone) (0x114C B) is the can-attack
  predicate. Misfortune's lock = `ldr r2,=0x1A0D; r0=r5; r1=0xB; bl 0x021A1430;
  cmp r0,#0; bne deny` @0x021A4BC2..0x021A4BCE (deny = bl-far 0x021A577E via
  0x021A4C52). The only other 0x1A0D word in ov3 is 0x02282804 = inside cls0
  (Misfortune's own record), so this is the sole code consumer. Proof of
  Powerlessness 0x2024 check @0x021A4C34. Mind Protector race test @0x021A5478
  (0x021AC494(0x1E25, side, [sp+0xB6])); stat struct from 0x021B44B4(side,
  zone, sp+0x94), +0x10 ATK.
  -> HOOK PLAN: replace `bl 0x021A1430` @0x021A4BC8 with bl to an ov3-pool stub
  (Misfortune query, then lock query (side,0xB,0x4000|cid,1) && race != Zombie).
- Turn-log: post 0x021D2584(side,key,kind,0) = 0x021C479C(side,0xB,key,kind,[sp]);
  query 0x021A14E8(side,0xB,key,kind) -> node search 0x021A1268. KB: kinds
  0..5, kinds 1/2 swept at end of turn, 5 = per duel. 0x4000|x key precedent
  = patch_assault_synchron REF_KEY_BASE (shipped).
- Deck-send resolver 0x02208DD4: phase word [0x0229AAFC+0x70]; 0x80 count/
  prompt (0x02243FA8 < [+0x74] -> 0x78 fail); 0x7E sets [+0x78]=1, send fail
  clears it @0x02208F24; 0x7D done @0x02208F30: pop 0x021D2964, return 0x7C iff
  [+0x78] != 0 else 0x64. So 0x7C is a RE-ENTRY phase reached only after a
  successful send -> a +04 wrapper can intercept phase 0x7C at entry (no ov5
  follow-hook dependency).
- Hand count = [0x0229ACA0 + (side&1)*0xB3C] (Wiraqocha 0x0222D3A6..AE).
- ov3 pool (cave3) free = 0x716 B in 16 runs >= 16 B (largest 0xF4 @0x02212330,
  0xF0 @0x021F0F9C, 0xCE @0x021F1B2C, 0xCE @0x0220A570, 0xB6 @0x021F18F8).
- Donor candidates (donor_scan --free, ATK <= 500, unused): Water Spirit 0x1E05
  (Lv1 WATER Aqua Normal TUNER 400/1200, name slot 11 B >= "Uni-Zombie" 10 B,
  desc 92 B), Chamberlain of the Six Samurai 0x1C6C (name 12 B), Charcoal
  Inpachi 0x17CD (name 8 B < 10 -> no). Only clean Zombie = Master Kyonshee
  0x1582 (1750 ATK -> violates prefer-weak-donors).

## Ruled Out
- (none yet)

## User decisions (2026-10-12)
- Rulings: C1 NOT activatable with an empty hand; C2 NOT activatable with no
  Zombie in the Deck.
- Hosting: ALL code in the ov3 pool (cave3) for now; migrate to ov5 when the
  user says "ship it" (flag then: attack-gate hook in ov5 freezes puzzle attacks).
- Donor: user asked for Lv5+ low-ATK Normals. Offered: Illusionist Faceless Mage
  0x0FD0 (only CLEAN unused Lv5+, 1200/2200 DARK), Labyrinth Wall 0x1114
  (0/3000, 2 binding refs ov3 0x021D7BD0 / arm9 0x02058498 -- unvetted),
  Water Spirit 0x1E05, Chamberlain 0x1C6C. AWAITING CHOICE.
- Phantoms planned: cls3 0x0E39, criteria 0x0E41 (unclaimed in stock + chain).

## STATUS: SHIPPED 2026-10-12
- In-game confirmed by user 2026-10-12: "All good. Everything works." (on the all-ov3
  build 9efec362...d371). User: "Move to ov5 and ship it!"; asked about the shared
  attack hook -> "Keep ATK in ov3".
- Shipped: MASK/COND/COST/RES -> ov5 CAVE_UZ_MASK 0x023A5440 / _COND 0x023A54C0 /
  _COST 0x023A54F0 / _RES 0x023A5580 (CAVE_FREE -> 0x023A5680); CAVE3_UZ_ATK stays
  0x021F18F8; the four freed ov3 pool slots are released. steps.STEPS after Windrose,
  _verify_all_patches.SHIPPED, donor moved to used lists, patch_bulk_card_pack row
  renamed "Illusionist Faceless Mage" -> "Uni-Zombie".
- Chain 109/109 rom_all_patches.nds sha256
  b8deab0796c7cf6a0b8a20d7faa350086db5ca8748ba621eec16ff1a9557e57c; sweep 90 passed 0 failed.
- The ov5 build itself was not re-tested in-game (stubs identical but re-based).

## Build (2026-10-12)
- Donor: Illusionist Faceless Mage 0x0FD0 (user choice). donor_scan CLEAN; its 4
  ambiguous ARM9 u16 hits (0x0209D6FA/0x0209E3D8/0x0209E6F8/0x020A13DA) are a
  fixed-point sin/cos table (0x0FCD..0x0FD3 beside small increasing values).
- patch_uni_zombie.py + _build_uni_zombie.py; ROM rom_uni_zombie.nds = stock +
  step 0 + this card, sha256 9efec3627eaba02953728d59a6a9b06da7294e87d4362560f9a7d6523ccad371.
  verify(): all PASS (static). patch_ov3_compact.verify OK.
- ov3 pool slots: CAVE3_UZ_MASK 0x021F0F9C (0x74), _COND 0x021F1010 (0x24),
  _COST 0x021F1B2C (0x88), _RES 0x02212330 (0xF4, exact fit), _ATK 0x021F18F8 (0x40).
- Hook: 0x021A4BC8 `bl 0x021A1430` -> `bl 0x021F18F8` (stock bytes fcf732fc,
  unpatched in stock / step-0 / chain).
- PHANTOM_CLAIMS: donor 0x0FD0, cls3 0x0E39, criteria 0x0E41. Ledger re-emitted.
- KB facts added (all PASS): dispatch.multi_effect_cls3_index_list,
  combat.can_attack_gate_turnlog_chain, stat.live_race_mask_0x021B8D90,
  dispatch.deck_send_7c_reentry_after_send; card.uni_zombie UNVERIFIED.
- Every stub disassembled from the built ROM: literals odd, BL targets right.

## Open Questions / ASSUMED
- Zombie criteria word 0x10000002 (ANCHORED by the race<<3 layout of Dragon /
  Reptile native rows, not by a native Zombie row).
- Lock key 0x4FD0 vs Assault Synchron 0x4000|ref keys (refs assumed small).
- Cost phase protocol mirrors Ape 0x021E88F4 minus the 0x021C3BC8 announce
  (Accel skipped it too).
- Whether the CPU picks a legal option via 0x0219ABB4 when it activates.
- On "ship it": user wants stubs moved to ov5; flag that CAVE3_UZ_ATK on the
  shared attack gate must stay ov3 or every puzzle attack freezes.

## Next Experiment
- None. Optional: quick ov5 re-test on the chain ROM (items 3, 5, 6).
