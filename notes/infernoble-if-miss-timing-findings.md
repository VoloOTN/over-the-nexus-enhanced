# Infernoble Knights: IF triggers miss timing after Cursed Copycat (2026-11-06)

User report (verbatim): "copycat is exposing that the infernoble effects have been coded as WHEN effects instead of IF
effects. For example if I use copycat noble arm to summon Ogier, I would be able to activate ogiers effect. Instead I get a
prompt stating that it missed timing". Status: AWAITING IN-GAME TEST (nothing built yet).

## Confirmed
- Miss-timing test 0x021EE0E0, node 0x021EE10C (r3 = cid). A "You can" trigger whose cid is not in the test's IF tree
  returns 1 = MISSED when it is not the last event. Fronts there: AR_MISS (Arms) -> Maugis M_MISS -> Eva/Shadow Mist, plus dc_miss.
- Offline execution on rom_all_patches.nds (2026-11-06, scratch/infernoble/knights_misstiming_exec.py, same harness as
  arms_misstiming_exec: event 0x1E, empty trigger log). Verdict 1 = misses, 0 = never misses:
  - never miss (0): Maugis 0x139A, Joyeuse 0x15E3 (Arms)
  - MISS (1): Ogier 0x13A3, Renaud 0x1E05, Ricciardetto 0x0FE6, Captain Roland 0x0FEB, Charles 0x17EF
    (also Roland, Oliver, Turpin, Astolfo, Captain Oliver, Angelica = 1, but their printed clauses are not "If ..." triggers)
- Printed text (scratch/ygoprodeck_cache.json) "If" triggers that need never-miss:
  Ogier C2 "If Normal or Special Summoned", Renaud C3 "If Special Summoned", Ricciardetto C2 "If Normal or Special Summoned",
  Captain Roland C1 "If Synchro Summoned", Charles C1 "If an Equip Card becomes equipped". Maugis C2 already fixed.
- Same bug class as the Arms E2 fix (BUILD 25), which was execution-proven 1 -> 0.

## Built 2026-11-06 (miss-timing fix: in-game confirmed by user 2026-11-06, "nothing misses timing now")
- infernoble.py `ar_miss_stub` is now a zero-terminated halfword table walk (AR_MISS_CIDS = Arms + IF_KNIGHT_CIDS
  Ogier/Renaud/Ricciardetto/Captain Roland/Charles); 9 straight compares would be 100 B > the 0x40 slot.
- ROM data/over_the_nexus/working/rom_if_miss_test.nds (fast build, 124/124, sha256 0b94f883...3ec3).
- Execution proof (arms_misstiming_exec vs the old rom_all_patches.nds): exactly 0x0FE6, 0x0FEB, 0x13A3, 0x17EF, 0x1E05
  change 1 -> 0; Arms/Maugis unchanged.
- Sweep 114 pass / 1 fail (data.bulk_ydcs, also fails on the old chain ROM); old chain ROM also failed cards.infernoble.

## Ruled Out
- Copycat itself. Its miss_front only adds Disguise. It is the Knights that were never admitted.

## Open Questions
- Charles' trigger is posted by its own event post (0x021D3230); whether it reaches 0x021EE0E0 on the Copycat path is unproven.
- Which of Roland C2 / Angelica C1 count as "If" (Angelica is not in the cache).

## Next Experiment
- Add the five cids to AR_MISS (extend ARMS_CIDS-style list in ar_miss_stub, infernoble.py ~6393), rebuild single-card,
  rerun knights_misstiming_exec before/after: expect only the five cids to change 1 -> 0.
