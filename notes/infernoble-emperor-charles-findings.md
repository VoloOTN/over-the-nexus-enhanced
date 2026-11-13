# Infernoble Knight Emperor Charles — findings

Family card 12 (Synchro). Started 2026-10-22 after the user confirmed Captain Roland + Captain Oliver
("All of captain roland and captain oliver is confirmed, continue to the next card").
NOTE: "Infernoble Knight Emperor Charles" (77656797) is a SYNCHRO; only "Emperor Charles the Great" (97864322) is the
Link Monster (skipped). Angelica's search targets cards that mention Emperor Charles, so Charles goes first.

## Printed text (scratch/ygoprodeck_cache.json id 77656797): Synchro, FIRE, Warrior, L9, 3000/200
1 Tuner + 1+ non-Tuner monsters
- C1 If an Equip Card becomes equipped to a monster on the field, even during the Damage Step: You can destroy
  1 card on the field.  (once per turn)
- C2 During the End Phase: You can equip 1 Equip Spell from your hand or GY to this card, then you can equip
  1 FIRE Warrior monster from your Deck to this card as an Equip Spell that gives it 500 ATK.  (once per turn)

## Donor candidates (effectless Fusions; scan 2026-10-22 in infernoble-captain-oliver-findings.md)
- Barox 0x0FFC (Lv5 DARK Fiend 1380/1530, only ref = own recipe A[9]) -- proposed.
- Kaminari Attack 0x1170, Marine Beast 0x120F, Mavelus 0x10B6, Kamionwizard 0x1019 -- alternates.

- Level 6+ effectless Fusions left (user asked 2026-10-22): only Master of Oz 0x17EF (Lv9 EARTH Beast 4200/3700).
  donor_scan: recipe A[73] + arm9 u32 0x0201B074 = literal of a 16-way index->cid map at 0x0201AF98
  (Oz, Neo-Daedalus, Exxod, VWXYZ, Vennominaga, Rainbow Dragon, Exodius, Chaos Neos, Armityle, BEWD, Fuh-Rin-Ka-Zan,
  Five-Headed, Tempest, Victory Dragon, Uria, Hamon) -- boss-card list, likely achievement/emblem (UNPROVEN: no BL or
  pointer caller found in arm9/ov*). Not an effect-engine gate. Rabid Horseman 0x1002 was "RULED OUT (per-cid code gate)" -- CORRECTED 2026-10-22: both hits are false positives, it is usable;
  Labyrinth Tank / Thousand Dragon spent on the Captains; the other Lv6+ list entries are used or not in the NDS pool.

## Status: whole card in-game confirmed by user 2026-10-22 on BUILD 18 ("All good next card"). Not shipped. Donor Master of Oz 0x17EF chosen by user 2026-10-22; C2 = "only appropriate equips" (user).

## Confirmed (2026-10-22, static disassembly of stock ov3)
- EVERY equip goes through 0x021C4A68(r0, r1 = equip loc side|zone<<8, r2 = target loc, r3 = source kind):
  callers incl. the 0xA thunk 0x021C4A5C, Allure 0x0220C0E8 (r3 0xC), Cyberdark 0x022188A2. At 0x021C4B4A
  r0 = cid of the equipped monster ([sp+0xC] side, [sp+8] zone); 0x021C4B4E `ldr r1,=0x13C3 ; cmp r0,r1` (4 B).
- Gearfried the Iron Knight 0x13C3 (printed: when an Equip Spell is equipped to this card) = DIRECT cls1 post
  0x021D3230(side, zone, 0x19, (r7<<16)|r6) @0x021C4B6C; 0x021D3230 builds the event word cid | zone<<16 |
  code<<25 | 1<<21 (selector 1 = cls1) | side<<31. => "equipped" event code = 0x19. Iron Knight cls1[153]
  {0x022048FD, 0x021DB9A5, 0x0224A115, 0, 0}. Swordmaster 0x186B / Seven Swords 0x23EA take 0x021D2A40(...,5,1) instead.
- 0x021D2A40(side, zone, bit, value) = zone flag setter; 0x021D3504(side, cid, code, word) posts cls1 to every
  0x021AC004 match whose zone bit 5 is clear, then sets bit 5 (dedupe); 0x021D357C(cid, code, word) = both sides.
  Summon code uses "mark self bit 5, then 0x021D357C" for "another copy summoned" cards (Witch Doctor 0x1C7B ...).
- 0x022391CC(0x19, word) @0x021C4BBC appends event 0x19 to the event log 0x0229AB7C.
- Non-target "destroy 1 card on the field" = Dark Voltanis 0x1FCB / Armor Breaker 0x1CD1 cls1
  {0x02204899, +08 0x021DE5A9, 0x0224A115, 0, 0x02234DA5}.
- On-field End Phase "You can" = registry row {0x02253F89, cid} in section 63..287 + cls1. Phantom row 198 cid
  0x1337 is unclaimed in check_allocations (154 = Rulers, 188 = Kuribandit).
- Equip-from-list-zone = Cyberdark resolver 0x022186E4 (also The Kick Man 0x1745 / Chopman 0x16BC for an Equip
  SPELL from the GY: cls1 {0x022186E5, 0, 0x021F9B81, 0x021E51E5, 0x02235605}, crit {0xFFFF, 0x0223E3F9, 0x10204});
  GY-bound in 4 places, Sea Lancer's cid-gated detours already sit on it (KB continuous_stat_engine 0x022186E4).
- Vylon Sigma resolver 0x0222DC49 equips from the DECK to ITSELF for every cid except Pilus (Bradamante notes).

## Build plan (draft)
- One cls1 record (second cls1 is Spirit-only) mode-switched on desc[+4]: 0x19 -> C1, End Phase -> C2.
- C1: ov5 front at 0x021C4B4E posting 0x021D3230(side, zone, 0x19, word) to each face-up 0x17EF (both sides),
  then replaying `ldr r1,=0x13C3 ; cmp r0,r1`. Effect = Voltanis's destroy record + OPT stamped at resolution.
- C2: row 198 cid -> 0x17EF; Equip Spell from hand/GY (Cyberdark/Kick Man machinery with a hand source) then
  FIRE Warrior from Deck (Sigma self-branch or Cyberdark with a Deck source); +500 via Captain Oliver's stat front.

## BUILD 18 (2026-10-22) -- in-game confirmed by user 2026-10-22 ("All good next card")
- rom_infernoble.nds sha256 c383a5afb8ed1cda51f51b13050f2f0fb1e7a4657bdd36a74d7d1371f0904289; patch_infernoble verify PASS;
  regression FAIL set byte-identical to BUILD 17 (known local-arm artifacts).
- cls1 over phantom 0x1337 {CH_RESW, CH_FILT, CH_COND, You-can 0x021E51E5, CH_SLOT5}; criteria row over 0x0E9C
  {0x17EF, 0xFFFF, CH_CRIT, 0}; End-Phase row 198 -> {0x02253F89, 0x17EF}; recipe A[73] killed; front BL @0x021C4B4E;
  Captain Oliver's stat front now also adds +500 for holder 0x17EF. ov5 CAVE_IK_CH_* 0x023A9CB0..0x023AA050
  (CAVE_FREE 0x023AA050: only 0xD0 B of ov5 cave left).
- PROVEN by disassembly: every equip calls 0x021C4A68 and passes 0x021C4B4E; Iron Knight's 0x021D3230(..,0x19,..)
  post; EP poster posts event 6; Sigma passes the picker param through to its criteria handler (&param callback);
  Sigma's Deck source zone = 0xD, link kind 0xA; Cyberdark link kind 0xC for monsters.
- ASSUMED (not executed): hand builder 0x0223C16D honours word 0x10204 + legality callback (Astolfo used word 2);
  mover 0x021C7484 with source 0xB (hand) for an Equip Spell; desc[+4] keeps 0x19 / 6 in every slot call.

## Ruled Out
## Open Questions
- C2 "equip 1 Equip Spell ... to this card" ignores that Spell's own equip restriction? (ask; no ruling from recall)
- C1 trigger scope: any monster on the field (either side), any Equip Card (Spell or monster-as-equip).
## Next Experiment
- User 2026-10-22: C2 Equip Spell = 'only appropriate equips' (native legal-equip check, Kick Man/Sigma style).
