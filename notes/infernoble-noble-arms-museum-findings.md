# Noble Arms Museum — findings (2026-10-22)

Donor **Molten Destruction 0x1346** (Field Spell -> Field Spell, keep-cid). User answers 2026-10-22:
"Noble Knight" = every Infernoble monster we built ("All the monster cards"); "Infernoble Knight" = all of them
incl. Bradamante; "Noble Arms" = the four Infernoble Arms. Donors Molten Destruction / Big Burn were the
recommended picks in the proposal the user answered (no objection raised -- flag it in the report).

Text (cache id 25807544): C1 FIRE Warriors you control +500 ATK. C2 OPT: pay 1200 LP; add 1 "Noble Arms" from
Deck. C3 OPT, if C2 was applied this turn: target 1 "Noble Knight" Monster Card in your S/T Zone; SS it; if
activated while you did not control Emperor Charles, Warrior-only SS for the rest of the turn.

BUILD 28 rom_infernoble.nds sha256 6c190fa775716d90c495929d80ef00ae9db63c3cabc5ff07c6a3a99ecc046531 --
AWAITING IN-GAME TEST. Verify failure set identical to BUILD 27 (only the known local-front checks of other modules).

## Confirmed
- Molten's only per-cid code = field-spell arm 0x021B28FA (12 B, stock `0c20315e1020084211d0ede7`); base+-imm scan
  (scratch/infernoble/baseimm_scan.py 0x1346) empty; no cls/criteria rows (scratch/infernoble/recs.py).
- Field arm frame: [sp] = field-spell side, r7 = monster side, r6 = monster record, [r6+8] race bitmask (Warrior =
  bit 15: Sogen arm `9<<12`), [r6+0xC] attribute bitmask (FIRE = 0x10: Molten arm). Epilogue 0x021B2B48.
- MU_STAT executed (scratch/infernoble/museum_exec.py): 50 cases, +500 ATK only for own FIRE Warrior, DEF untouched.
- Criteria registry has NO free phantom row (free_phantoms: populate_table only 0xFFFE). Museum's search therefore
  drives the native Deck-add phases itself over **Almace's** row in a new mode 3; Almace's handler is fronted by
  MU_CRITF. Executed: modes 0..2 reach Almace's CRIT with r0..r2 intact; mode 3 calls the Deck worker with MU_ARMCB.
- Native Deck add machine 0x02207EF4 phases (KB dispatch.native_deck_add_phase_machine).
- S/T -> monster zone SS = SS commit with the zone record (KB summon.st_zone_monster_ss_commit; Phalanx r3 = 2).
- Generic LP cost 0x021E780C activates only if LP > cost (`cmp lp, cost ; bgt`) -> MU_COND uses LP > 1200.
- Warrior-only lock = Horn of Olifant's node 0x5976 (its front at 0x021BA368 already denies non-Warriors).

## Ruled Out
- Molten's LP-cost row: Molten is not in 0x0226F1A8, and a row would charge C3 too -> own +10 pays via 0x021CF924.
- Virtual criteria row (Tenki pattern): k would be ~304 (> the 0xFF index byte) and cave3 is nearly full.

## Open Questions
- Target-step prompt text: +14 uses Wonder Clover's step (message 0x7C) -- wording unknown.
- 0x021BA440 (Armory's own "can SS this desc" check) is skipped for the target; KNIGHTS are all Warriors.
- In a puzzle-editor duel the ov5 stubs are gone (accepted default).

- KNOWN DEVIATION IN BUILD 28 (found after building): MU_RES C3 passes [sp] = TARGET cid << 16 to the SS commit
  0x0226925C. Angelica (confirmed) passes the SUMMONING card's cid << 16; the commit only tests bit 0x10 of it
  (side flip), so the cid half is probably the 'summoned by' source. Fix = `ldr r0,=0x1346<<16` instead of the
  CARD_CID_AT call. APPLIED 2026-10-27 (BUILD 29).

## Continuing Epic -- WIRED 2026-10-27, BUILD 29 = chain rom_all_patches.nds sha256
3e85b233a1b912c55dd6397577f037927873776a4d06585ecb4d0586e3970a33 (120/120, sweep 101/0). AWAITING IN-GAME TEST (EP1..EP6).
- MU_CRITF moved to a 0x80 slot (old 0x40 slot = CAVE_IK_MU_SPARE, dead); executed: modes 0..2 Almace untouched,
  3 Deck worker+ARMCB, 4 hand builder+ARMCB word 4, 5 hand builder+KNCB word 2 (then Deck worker, not executed).
- 'Big Burn' key in patch_bulk_card_pack.CHANGES renamed (chain keys by in-ROM name).
(earlier draft notes:)
- Section drafted (scratchpad ep_section.py, NOT in the repo): Big Burn 0x16DB cls0 re-pointed; E2 cls2 over 0x0E63
  + gy_vrow_hook ARMS row (15/16); lists via MU_CRITF new modes 4 (Arms in hand, hand builder word 4) and 5 (Knights
  hand word 2 + Deck worker word 2). Deck worker word 0 matches NOTHING (dispatch.deck_walker_word_is_a_type_union).
- Hand zone code 0xB (Charles C2 mover); SS commit derives source zone from the card ref (works hand/Deck);
  'send to GY' = 0x021C6D90 kind 2 (neither cost nor effect discard) -- user ruling 2026-10-27: "It should be a send. Not a discard" (kind 2 is correct).
- Charles + monster equip already gets +500 from Captain Oliver's stat front (co_stat_src) -> Epic E2 needs no stat code.

## Next Experiment (in-game, BUILD 28) -- MU1..MU6 in _build_infernoble.py docstring

## Epic E2 +500 bug (user 2026-10-27: "E2 does not grant the attack increase"; "Knight was equipped")
- The +500 is Captain Oliver's stat front @0x021B7088 (holder 0x17EF, equip card race < 23); confirmed for Charles C2
  (CH5). Path to 0x021B7088 skips an equip card if its record +8 face-up halfword is 0, if [rec+0x10]>>6 has the side
  bit, or if the holder's +0x20/+0x21 byte (chosen by 0x02022FDC(cid)) has it -> 0x021B7738.  UNPROVEN which one.
- Next experiment: savestate with Charles + an E2-equipped Knight on the field (ATK visible) -> run the recompute
  0x021B44C0 in thumbemu and read which branch skips the Knight.
- ROOT CAUSE, execution-proven over .ml3/.ml4 (user: before/after): the stat loop walks link nodes 0x0229D33C
  (stride 0xA: +0 loc, +2 low nibble = LINK KIND, +8 next) and dispatches on the kind @0x021B6090: kind 0xA -> equip
  path 0x021B7008 -> Captain Oliver's +500 front; kind 0xC (Allure's kind) -> 0x021B740C (cid switch 0x1AAF..0x1AB1,
  else skip). Epic E2 linked Oliver with kind 0xC (node 0x0229D350); Ogier / Hauteclere / Captain Roland are 0xA.
  Rewriting that node's kind to 0xA in emulation: Charles ATK 5000 -> 5500. FIX: Epic E2 link kind 0xA.
  APPLIED: chain sha256 1d350c1536a033d8d39d7ad978d773bbb8468beca3af31ec634e46c5936be1b6, 120/120, sweep 101/0 -- AWAITING IN-GAME TEST.
- SAME kind 0xC is used by Emperor Charles C2 stage B (ch_c2res_src) -> its +500 should be missing too, although CH5
  was reported confirmed. User 2026-10-27: "Yes, switch Charles C2 to 0xA too" -> done. Chain sha256 d432355ae31bfb07d4db9033a42d7664357cbd94f45342eb85ee010cf1296495, 120/120, sweep 101/0 -- AWAITING IN-GAME TEST (CH5).

## Epic E2 +500 and Charles C2 +500: in-game confirmed by user 2026-10-27 on chain d432355a ("All three confirmed, ship").
