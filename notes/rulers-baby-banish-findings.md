# Dragon Rulers — babies build an empty chain link when banished — findings

Status: ROOT CAUSE PROVEN (static, patch source + built-ROM disasm); fix BUILT; in-game confirmed by user 2026-10-19 ("All confirmed" -- all 4 oracle items) on rom_rulers_baby_ban.nds 72dabbf7...c308d.
Patch: `otn_enhanced/cards/dragon_rulers.py` (SHIPPED 2026-10-16).

## Confirmed (2026-10-19)
- USER REPORT (verbatim): "Another bug, is that all the level 3 and 4 baby rules "Activate" when they are banished,
  but they shouldnt" + "rom_redox_c3, I do not have a save state. 1. From anywhere 2. They just 'activated' but there
  was no prompt - no freeze or anything but just built a chain link" -> confirmed reading ("yes"): banishing any baby
  (Reactan / Stream / Burner / Lightning) from hand, GY or field auto-builds a chain link, no prompt, no freeze.
- Printed text (scratch/ygoprodeck_cache.json): every baby has ONE effect (discard it + 1 Dragon/<attr>; SS its big
  ruler from the Deck). No banish clause.
- vrec_blob(): only big rulers get a BAN virtual record; a baby's BAN slot is 0x18 zero bytes -> H1 (`got: ldrh
  [rec]; cmp 0`) returns 0 for a baby.
- The banish POSTERS gate on FINDK = any of the 8 rulers: H6 (`cmp r0,#0; bmi other`), H7 (`bmi native`), H8A
  (`bmi h8a_nat`, LEAVE body returns the virtual mask row for any ruler with dest 0xF). So a baby's banish posts the
  C4 event and the link is built with no record -> no "You can" tag (the prompt comes from TAG_YOU_CAN 0x021E51E5 in
  BAN +0x10) -> silent empty link. Matches the report on all three origins.
- Big rulers are k 0..3 (`assert CIDS[:len(BIGS)] == BIGS`; FINDK returns k or -1).

## Ruled Out
- (none)

## Fix (BUILT 2026-10-19; in-game confirmed by user 2026-10-19 ("All confirmed" -- all 4 oracle items) on rom_rulers_baby_ban.nds 72dabbf7...c308d)
- Gate the three posters on k < 4 via `lsrs r0, r0, #2 ; bne <not-big>` (nonzero for k 4..7 AND for -1; the
  assembler has no bhs/bcs). `assert len(BIGS) == 4` added.
  - H6 (cave3 0x021F105C, 0x24 of 0x30): same size. Non-big -> Eclipse Wyvern's stub 0x021B57F0 as before.
  - H7 (cave3 0x021F1A0C, 0x28 of 0x28): restructured to fit -- shared `pop {r0,r2,r3}` + `ldr r1,=0x1d98` (neither
    touches flags), then `beq leaf` (Z from `cmp dest,#0xf`) else the native `cmp r5, r1`. Built disasm checked:
    literals 0x021F1A2C = 0x1D98, 0x021F1A30 = leaf.
  - H8 body ov5 CAVE_RUL_LEAVE 0x023A75A0 (0x1C of 0x20): k arrives in r0 from H8A's FINDK -> non-big returns 0
    (= native bsearch miss; no ruler owns a native mask row, verify asserts it).
- `_build_rulers_baby_ban.py`: delta on rom_redox_c3.nds -> data/over_the_nexus/working/rom_rulers_baby_ban.nds
  sha256 72dabbf75d6cff132edb2a44b361eaaa9b7911391ffd01db8ad9cdd2315c308d. verify(): patch_dragon_rulers PASS,
  patch_eclipse_wyvern PASS (static only). No new slots.

## Open Questions
- none

## Next Experiment
- None. Ships with the Dragon Rulers step at the next EE build (source changed in place).
