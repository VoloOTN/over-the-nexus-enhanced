# Infernoble Knight Turpin — findings

Family card 4. Started 2026-10-20. Donor Beaver Warrior 0x0FC1 (L4 EARTH Beast-Warrior Normal 1200/1500), clause
split, and the "Use which effect?" GY offer — all confirmed by user 2026-10-20 ("Confirmed, Beaver Warrior, use which
effect — proceed"). No ROM code yet.

## Printed text (scratch/ygoprodeck_cache.json): Effect, Warrior, FIRE, L4, 1400/1700
- C1 While this card is an Equip Card, the equipped monster can be treated as a Tuner if used as Synchro Material.
- C2 (OPT) If you control a monster equipped with an Equip Card: You can Special Summon this card from your hand or
  GY, but if you Summon it from the GY, banish it when it leaves the field.
- C3 (OPT) If this card is in your GY: You can target 1 Warrior monster you control; equip this card to that monster.

## Plan
- ONE cls2 record: hand (desc[+3] == 0x0B) -> C2 hand SS (Oliver's hand path minus the cost); GY -> "Use which
  effect?" (C2 GY SS / C3 equip) when both are legal, mode in desc[+0x18] (Dragon Rulers' prompt pattern).
- OPT stamps at RESOLUTION (Maugis lesson: slot5 re-runs +0C).
- Hand offer: LIST B has NO phantom left (Oliver took 0x1A86), LIST A full -> front Dragon Rulers' H4 hook at ARM9
  0x02023566 (CAVE3_RUL_H4) for 0x0FC1.
- GY SS: 0x0220731D GY self-SS resolver + banish-when-leaves (Jet Synchron's summon_rider_hook arm).
- C1: Synchro material Tuner test — RE needed.

## Confirmed (static, this session)
- C1: Synchro material "is Tuner" = runtime wrapper 0x021A1C7C(side, idx) (KB synchro.is_tuner_predicate; 60 callers,
  all duel code): static 0x02023110 || riders 0x1E40 Lightwave Tuning / 0x2013 Natural Tune / 0x202D Fabled Miztoji ||
  0x021A0950(.., 0x1F87 Psychic Tuning) || **0x021A09BC(side, idx, 0x220D Dragunity Partisan, 0xA)** @0x021A1D06 =
  Konami's own "monster card held as an equip makes the equipped monster a Tuner". Site bytes stock == chain (fef759fe).
  ⚠️ Partisan's text is "IS treated as a Tuner"; Turpin's is "CAN be treated as a Tuner if used as Synchro Material".
  Mirroring Partisan makes the equipped monster a Tuner everywhere, so it cannot be NON-Tuner Synchro material (the KB:
  there is no "treated as a non-Tuner" path) -> a deviation to put to the user with the test.
- C2 GY: 0x0FC1 reaches the summon-event DEFAULT leaf 0x02268666 (scratch/summon_event_sim walk, this session) ->
  one summon_rider_hook ARMS entry + a one-shot byte gives "banish when it leaves" (Remus C3a / Jet Synchron recipe:
  phase 0x80 CHAIN_PUSH, set byte, GY self-SS 0x0220731D, -> 0x7F; 0x7F CHAIN_POP -> 0x64).
- Hand offer: 0x0202354C callers are all ov3/ov5 (0x021EC982, 0x02239656, 0x0224B082, 0x0224C052, 0x0224C0C4, ov5
  0x02346706) -> duel-only -> an ov5 front at Rulers' ARM9 H4 site 0x02023566 is duel-safe.
- dlg_text_e labels: 0x103 "Use which effect?", 0x19F "Special Summon the designated monster(s).", 0x1A1 "Equip this
  card to a monster.".
## IN-GAME RESULT — in-game confirmed by user 2026-10-20 (BUILD 6, rom_infernoble.nds 09ecae22...5e73)
User's words: "All confirmed! Proceed with Renaud" -- given as the answer to the 9-step list, which included step 8
(the Partisan-style Tuner behaviour, "judge this"). Recorded: whole card confirmed; the step-8 behaviour ACCEPTED by
the user as part of "All confirmed". NOT shipped.

## BUILD 6 (Ogier + Maugis + Oliver + Turpin, 2026-10-20)
- rom_infernoble.nds sha256 09ecae22c234ccf11be7553c2ba6546d5a041bb7189d9347e9f08dedd7695e73.
- cls2 over phantom 0x1A8A: hand -> T_HANDRES (OPT 0x4FC1 + native hand SS); GY -> +0C resets mode, LEGAL bitmask;
  +10 "Use which effect?" (0x103 / 0x19F / 0x1A1) or the single legal mode; +04 mode 1 -> T_GYSS (Remus template + arm
  byte CAVE_IK_T_ARM -> summon_rider_hook LOCAL arm 0x0FC1, stub 124/128 B), mode 2 -> T_EQRES (OPT 0x0FC1 + Vylon
  resolver); +08 / +14 Vylon only in equip mode. EQX = "a monster of yours is equipped" (0x021A0DF8 scan).
  C1 = front of Partisan's 0x021A09BC @0x021A1D06 (native first, then Ogier-style 0x0FC1 scan).
  Hand offer = ov5 front of Rulers' ARM9 H4 BL @0x02023566 (CAVE_IK_T_H4 -> CAVE3_RUL_H4).
- PROOFS: H4 front executed for all 0x2700 cids over .ml2 with the new stubs: only 0x0FC1 changes (0 -> 1).
  patch_infernoble.verify PASS; chain_walk_diff / miss_diff / gyv_equiv PASS. Sweep 82/18: the 18 = shared timing /
  c79 / RIDER stubs carrying LOCAL arms + the unregistered-walk artifact; nothing else.
- Tolerance added: patch_dragon_rulers.verify accepts the ARM9 H4 BL pointing at CAVE_IK_T_H4.
- DEVIATION TO PUT TO THE USER (not decided by me): C1 mirrors Partisan ("is treated as a Tuner") -> the equipped
  monster is a Tuner everywhere and probably cannot be NON-Tuner Synchro material while Turpin is attached.
- ASSUMED: the GY prompt's mode survives in desc[+0x18] from +10 to +04 (Rulers precedent); +0C is not re-run after
  +10 on the GY path (Ogier's +10 stamp worked, so Vylon's slot5 does not re-run it).

## Ruled Out
## Open Questions
## Next Experiment
