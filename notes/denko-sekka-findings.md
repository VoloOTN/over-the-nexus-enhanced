# Denko Sekka — findings (live)

Printed text (scratch/ygoprodeck_cache.json, id 13974207; LIGHT Thunder L4 1700/1000 Effect):
"Cannot be Special Summoned. While you control no Set Spells/Traps, neither player can Set
Spells/Traps nor activate Spell/Trap Cards that are Set on the field."

Clauses: C1 cannot be SSd | C2a neither player can Set S/T | C2b neither player can activate
Set S/T — C2 active only while Denko's controller controls 0 Set S/T.
Scope: WHOLE CARD (user, 2026-10-18).

## Confirmed
- Denko Sekka is NOT in the 3DS build (CARD_Name_E scan 2026-10-18; Jinzo 0x1296, Royal Decree
  0x1302, Anti-Spell Fragrance 0x1390, Anti-Spell 0x1634 are). No Konami reference for C2.
- C1 list ARM9 0x0209BD6C = KB VERIFIED `summon.cannot_be_special_summoned_list` (proof PASS
  2026-10-18; KB 641 PASS / 0 FAIL). Cardcar D recipe (patch_cardcar_d.apply_arm9_cannot_ss).
- Capability enumerator 0x0224BC40(side, zone, idx) (static read of ov3 catalogue 2026-10-18):
  zone switch 0..4 monsters, 5..10 S/T+Field -> 0x0224B644(cid, side, zone), 0xB hand.
  HAND arm, race 0x17/0x18 (S/T), phase 2/4: 0x021AE67C(side,cid) [zone free] -> 0x021EDD90 ->
  flag 0x8 (activate); then `0x021B9690(side) != 0 && 0x021A1B20(cid) == 0` -> flag 0x80 = SET.
- 0x021B9690(side) = generic "may side Set ANY card" floodgate: literals 0x1407, 0x1679
  Judgment of the Pharaoh, 0x1A1B Searchlightman, 0x1E5A Dark Simorgh (on 1-side). Monster
  Sets use it too -> WRONG hook for Denko (monsters must stay Settable).
- 0x021A1B20(cid) = S/T-only "this card cannot be Set" (returns 1 = cannot): 0x1407 node /
  0x021AEA7C / tail `bl 0x020235F0(cid)`. Callers: 0x0224BC40 hand arm + criteria handlers
  0x0223D1A0/0x0223D834/0x0223F220/0x0223F638. Pointer census of stock ov3 (2026-10-18): 0x0223D834
  is the criteria handler of Dust Tornado 0x137C + Wild Tornado 0x229B ("then Set 1 S/T from
  hand"); the other three are filters passed by wrappers whose criteria rows are 0x0E3D,
  Ancient Gear Drill 0x19AE, Spell Calling 0x1A7D ("Set 1 Quick-Play from Deck"). => 0x021A1B20
  IS the "can this S/T be Set" gate for hand Set AND Set-by-effect. C2a hook = its tail
  `bl 0x020235F0` (site 0x021A1B4C, computed from the 0x38-byte layout; bytes asserted in patch).
- 0x021ECDA4(desc, f, r2) = activation "prohibited" predicate: returns 1 = prohibited (posts
  UI msg 0x14 to [0x0229DE14+8] for the local player), 0 = allowed. desc +0 cid, +2 side,
  +3 zone. Field block (desc[+3] <= 0xA) already denies per-instance Set-card locks:
  Cursed Fig 0x1DF6 via 0x021A1430(side, zone, 0x1DF6), Sergeant Electro 0x233E via
  0x021A08A0(side, zone, cid). C2b hook candidate = the Cursed Fig BL.
- Zone record = player(0x0229AC94 + side*0xB3C) + 0x34 + zone*0x14: +0 card word (cid low 14),
  +6 position, +8 FACE-UP halfword, +0x10 flags. For S/T zones 5..10 +8 == 0 <=> Set: savestate
  census 2026-10-18 (17 states): face-up Seal/Continuous fu=1, every Set card fu=0.

- PATH PROOF (scratch/denko_path_proof.py, thumbemu over 0x0224BC40 on the user's savestates,
  2026-10-18): C2a site 0x021A1B4C EXECUTES for a S/T in hand -> flags 0x80 (rom_raiden.ml3
  hand[1] 0x171A; Seal 0x10F5 in hand -> 0x88). C2b site 0x021ED614 EXECUTES inside 0x021ECDA4
  for the player's own Set card (rom_pyrorex.ml5 s0 z7 0x1638 fu=0; emu later stops on an ARM
  BLX, after the site). 0x021ECDA4 is called by the core legality fn 0x021EDA14, whose callers
  are 0x021EC740 (field), 0x021EC93C (hand), 0x021EDDEC, 0x02217DD8, 0x0223E1EC -> chain
  windows share it (static; Cursed Fig's native lock uses the same site).

- Stock bytes (rom.nds ov3, 2026-10-18): 0x021A1B4C = bl 0x020235F0 (preceded by adds r0,r5);
  0x021ED614 = bl 0x021A1430 preceded by a078 e178 674a (ldrb r0,[r4,#2]; ldrb r1,[r4,#3];
  ldr r2,=0x1DF6), r4 = desc.
- Donor candidates (donor_scan --free, ATK<=500, 2026-10-18): ONLY Chamberlain of the Six
  Samurai 0x1C6C (Normal L3 EARTH Warrior 200/2000, CLEAN, name slot 12 / desc 116) and Water
  Spirit 0x1E05 (Normal TUNER). 0x1C6C not referenced in steps.py / finished_patches / ledger.
- C1 phantom: cannot_ss_list phantoms in stock = 0x193B (cardcar_d), 0x19A8, 0x1B1A; 0x19A8 and
  0x1B1A are unclaimed IN THIS POOL (claimed only in nomi_class4_list / draw_count_table);
  both still present in rom_all_patches.nds's list.

- DONOR = Kojikocy 0x0FE8 (user-chosen 2026-10-18; Normal L4 EARTH Warrior 1500/1200). donor_scan
  0x0FE8: CLEAN. Its 8 "ambiguous" ARM9 u16 hits (0x0209D682/E44C/E680/0x020A144E pairs) are a
  4.12 sin/cos table (0x0FE5..0x0FEB ramp interleaved); ov3 0x02259370 = `lsr r0,r5,#31`,
  arm9 0x0207A410 = code. Not referenced in steps.py / finished_patches / ledger.
  Name slot floor 8 B < "Denko Sekka" -> MUST use card_text.CARD_TEXT re-emit (name + desc).
- C2b site regs (scratch/denko_site_regs.py, thumbemu, rom_pyrorex.ml5 0x0224BC40(0,7,0)):
  at 0x021ED614 r0 = 0 (side), r1 = 7 (zone), r2 = 0x1DF6, r4 = desc; desc[+2] = 0, desc[+3] = 7
  ABSOLUTE zone (5..10 numbering, same as the zone record), desc[+0] = 0x1638. PROVEN.
- cave3 free (candidates.free_fragments 2026-10-18): 858 B total; fragments >= 0x20 only
  0x021F1938 (0x76), 0x021FADE8 (0x6E), 0x0221ABB8 (0x50).
- BUILD 1 (2026-10-18): _build_denko_sekka.py -> rom_denko_sekka.nds sha256
  277df32296be7b911bf21f9cfe2c3d0476d07a4d134cc8004c51666994601696; verify() 7/7 PASS; card_prop =
  Effect / LIGHT / Thunder / Lv4 / 1700 / 1000; check_allocations OK. NOT in steps.STEPS.
  cave3: LOCK 0x021F1938 (0x5C), FIG 0x021FADE8 (0x48), SET 0x0221ABB8 (0x10).
- EXECUTION PROOF of the BUILT stubs (scratch/denko_stub_emu.py, 12/12 PASS): C2a via the real
  0x0224BC40 hand arm (rom_raiden.ml3): Set flag 0x80 removed for own AND opponent face-up Denko
  with no Set S/T; kept with no Denko / face-down Denko / Denko + own Set. C2b (rom_pyrorex.ml5
  s0 z7 Set): via 0x0224BC40 no Denko / own Denko+own Set / face-down opp Denko -> front 0;
  front called directly with the site's proven regs: opp face-up Denko + opp no Set -> 1,
  opp has Set -> 0, face-up target -> 0, monster zone -> 0.
  Emulator limit: a face-up OPPONENT monster sends 0x021ECDA4's monster loop @0x021ED54A into ARM
  code (BLX 0x020989A4) thumbemu cannot run -> those cases used the direct front call.
- SHIPPED 2026-10-18 on the user's go ("Looks good. Ship it") -- IN-GAME TEST NOT REPORTED, so NOT confirmed.
  steps.STEPS after Dragon Rulers + _verify_all_patches.SHIPPED; bulk_card_pack key "Kojikocy" -> "Denko Sekka".
  EE build 116/116 sha256 75cb14ea2cd124f539b2534bf69f6ea256e5488dd08f36bf9ab13562a56fe0af; sweep 97 passed / 0 failed.
  equiv --all: bulk_ydcs IDENTICAL, reborn_tengu DIFFERS (ov5/overlay-table level; not reachable from this patch's edits).
- User rule change 2026-10-18: donor ATK ceiling 1500 (skill + memory updated).

## Ruled Out
- Hooking 0x021B9690 for C2a: it is the ANY-card Set floodgate (Dark Simorgh) -> would also
  block monster Sets.

## Open Questions
- Does the CPU decide to Set via 0x0224BC40 / 0x021A1B20, or could it bypass the gate? (in-game item 4)
- Chain-window activation of a Set trap: static evidence only (0x021EDA14 callers); in-game item 6.
- Denko's own effect negated (Skill Drain etc.) is NOT modelled: lock reads only face-up + cid.
- Ancient Gear Drill's Field-Spell filter also calls 0x021A1B20 -> finds nothing while locked.

## Next Experiment
- USER IN-GAME TEST of rom_denko_sekka.nds (sha256 277df322...1696), oracle list in the
  _build_denko_sekka.py docstring. On a failure: ask for a savestate at the failing moment.
- Shipped. Still wanted: the in-game oracle run (_build_denko_sekka.py list) on rom_all_patches.nds.
