# Redox C3 (discard -> revive a GY target) — findings

Status: ROOT CAUSE PROVEN (savestate + disasm); fix BUILT; in-game confirmed by user 2026-10-19 ("That works!") on rom_redox_c3.nds 488b88f4...fdeac. Oracle items 2-4 (C1, baby, Blaster C3) not separately reported.
Patch: `otn_enhanced/cards/dragon_rulers.py` (SHIPPED 2026-10-16; C3 apparently never
exercised for Redox in-game before this report).

## Confirmed (2026-10-19)
- USER REPORT (verbatim): "What happened was I discarded, i chose something from the GY, but that monster did not
  special summon" -> confirmed reading ("Yes confirmed"): cost paid, GY target picker shown + target chosen, target
  stays in GY; no freeze.
- Savestates data/over_the_nexus/working/rom_rulers_field_banish.ml1 / .ml2 (ROM rom_rulers_field_banish.nds),
  read with knowledge.env.SaveState + scratch/dump_zones.py:
  - ml1: hand [0x1474, 0x0FEA, 0x2359, Redox 0x17CD i32, Redox 0x17CD i33]; GY [0x15E9, 0x0FEA, 0x115E, 0x1CC6,
    Blaster 0x1145 (word 0x05001145), 0x12D5]; both sides' monster zones empty. Cost phase [0x0229AAFC+0x7C] = 3.
    Acting desc (0x0229A9FC+0x50): +0x10 = 0, +0x12 = 0, +0x18 = 2 (C3 mode).
  - ml2: hand lost both Redox; GY [.., 0x12D5, Redox i32, Redox i33, Blaster 0x05001145] (Blaster word unchanged,
    re-appended last); monster zones still empty. Acting desc: +0x10 = 1, +0x12 = 3, +0x14 = 0x0042, +0x16 = 0,
    **+0x18 = 0x029C** (mode clobbered).
- ROOT CAUSE: the pick appender 0x022345F4(desc, half) (ov3 disasm, this ROM) does
  `n = desc[+0x12]; desc[+0x12] = n+1; desc[+0x14 + 2n] = half` (n < 5). Both target recorders reach it:
  list form 0x02234880 -> 0x0223473C -> bl 0x022345F4 @0x0223479C; board form 0x022347B0 (same sink, KB
  dispatch.pick_record_and_resolver_readback). Our cost commit's discard branch does `strh 2, [desc,#0x12]`
  (patch_dragon_rulers cost_src `discard:`), so the C3 GY target is appended at **entry 2 = desc[+0x18] — our mode
  halfword**. ml2's +0x12 = 3 and +0x18 = 0x029C match this exactly.
- Consequence 1: res_h_src reads desc[+0x18] != 2 -> takes the C1 branch (RES_HAND_SS 0x02206ABD, "SS this card
  from the hand") instead of PARAMS res_c3 (0x02207191) -> Redox is in the GY, nothing summoned.
- Consequence 2 (even if the mode survived): the revive core 0x02204730 (reached from 0x02207191's default leaf
  0x022072DA, `bl 0x02204730(desc, 1, 2)`) reads picks via 0x02234904(desc, i) / 0x02234964(desc, i) = entry
  desc[+0x14 + 2i] starting at i = 0 -> entry 0 = 0x0042 = the cost's discard pick, NOT the target. So the target
  must land in entry 0.
- The same appender serves the board recorder -> Blaster C3 (destroy, BOARD_STEP 0x02234DA5) is exposed to the
  same clobber. NOT in scope; not tested.
- Why +0x12 = 2 exists: crit_src treats `desc[+0x12] >= 2` as "cost picks done -> serve the C3 (GY target) row",
  as a second test after `[STATE+0x7C] == 0`.

- Activation driver (ov3 disasm): the +0x10 step 0x02258D34 (counter [0x0229A7FC+0x48]) zeroes [0x0229AAFC+0x7C]
  @0x02258D66 then 0x0224AE50 = `blx rec[+0x10]`; the +0x14 step 0x02258DD0 (counter +0x4C) zeroes
  [0x0229AAFC+0x7C] @0x02258E0E and [0x0229AB7C],[+4] then 0x0224AE84 = `blx rec[+0x14]`. So during the target step
  the cost phase is 0 and crit_src's first test (`[STATE+0x7C] == 0 -> gyt`) already serves the C3 row.
- 0x02234904's cid gate is ARM9 0x02023660 = {0x19A5, 0x201E, 0x219E} -> for 0x17CD the pick index is unshifted
  (entry i = desc[+0x14 + 2i]).

## Ruled Out
- (none yet)

## Fix (BUILT 2026-10-19; in-game confirmed by user 2026-10-19: "That works!")
- cost_src `discard:` commit: `movs r0, #0x2` -> `#0x0` before `strh r0, [r4, #0x12]` (ov5 0x023A66E4). Target now
  lands at entry 0 (+0x14, the spent discard ref), mode +0x18 untouched.
- `_build_redox_c3.py`: delta on rom_rulers_field_banish.nds, asserts the stub differs by exactly that one byte
  -> data/over_the_nexus/working/rom_redox_c3.nds sha256 488b88f4975b61853163dd6dab1db07529b2cf5a783c50d02861fad12f7fdeac.
  rul.verify PASS (static only). Built bytes disassembled: 0x023A66E4 movs r0,#0 ; strh r0,[r4,#0x12].
- No new slots claimed. Not wired / no chain build (stub source changed in place; the Dragon Rulers STEP picks it up
  at the next EE build once the user ships).

## Open Questions
- Blaster C3 (board target, same appender) was exposed to the same clobber; the fix covers it too. Untested.
- What moved Blaster to the end of the GY (unchanged word)? Not needed for the fix; noted.

## Next Experiment
- None for Redox C3. Rebuild the EE chain (Dragon Rulers step already carries the source change) when shipping.
