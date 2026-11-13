# Naturia Pineapple — findings

Donor: **Headless Knight 0x1465** (EARTH Fiend Lv4 Normal, user-approved 2026-09-15).
Status: **all 9 oracles in-game confirmed by user 2026-09-15** on Build 1 (sha256 f69b5ebf...2c67eaf); oracle 10 in-game confirmed by user 2026-09-15 on Build 2
(7f4212c5...7dccd31d). SHIPPED 2026-09-15 ("Confirmed. Ship it") to steps.STEPS + SHIPPED.

Printed text (scratch/ygoprodeck_cache.json id 7304544, EARTH Plant Lv2 100/100):
> All face-up monsters you control are treated as Plant-Type. During your Standby Phase,
> if you do not control a face-up "Naturia Pineapple", and have no monsters in your
> Graveyard except Plant or Beast-Type: You can Special Summon this card from your
> Graveyard. You must not control any Spell or Trap Cards to activate and resolve this effect.

- C1 continuous: your face-up monsters are Plant.
- C2 Standby, optional, GY self-SS; (a) no face-up Pineapple, (b) GY monsters all
  Plant/Beast, (c) no S/T you control — at activation AND resolution.

Scope: user chose ALL clauses (2026-09-15).

## Confirmed (this session, 2026-09-15)

All by capstone disasm of `ygo_tools/reference_files/nds_overlay_3.bin` (base 0x02141700)
unless noted.

### 3DS (code_dec.bin, VA = 0x100000 + off) — Explore-agent scan, reported with disasm
- Pineapple 3DS cid 0x23F4 (CARD_Prop idx 4341). Not in NDS card_prop.
- event_trigger 0x6C6780 row [652] == Treeborn [202] except cid; predicate switch 0x49C820
  Pineapple arm: S/T count==0 -> face-up count(cid)==0 -> GYmon == GYrace(13)+GYrace(11).
- Standby GY poster table 0x6AB890 (stride 8 {handler,cid}) row [11] handler 0x4B3B0C (Treeborn's).

### C2 machine (NDS)
- Standby registry row 297 @0x0228EB28 = {0x022573DD, 0x19CB Treeborn}; row 300 @0x0228EB40 =
  {0x022573DD, 0x1FCF Totem}. Row 316 @0x0228EBC0 = {0x02256F7D, 0x1338} (stock ov3 image).
- Poster 0x022573DD is cid-agnostic: `bl 0x021A14B4(side,0xB,cid,0)` latch, walks GY word list
  `[r4+i*4] & 0x3FFF == cid`, per-instance latch 0x021A14B4 again, posts `bl 0x021D3168`.
  No cid switch in the function body (0x022573DC..0x0225747E).
- Resolver 0x0220731D: first cid switch pool 0x022074F8.. = 0x1FCF,0x1CEF,0x19CB,0x1E15,...
  Treeborn/0x19CB -> 0x022073C8: `ldrb r0,[r5,#2]; bl 0x021AE4AC; cmp r0,#0; beq go; movs r0,#0; pop`.
  0x1465 path: <0x1FCF, <0x1CEF, >0xE10, !=0x19CB -> default 0x022073E8 (no S/T recheck).
- Treeborn condition 0x021FA584: `ldrh r1,[r5]` then arm `ldrb r0,[r5,#2]; bl 0x021AC9FC` (r1=cid)
  -> fail if !=0; `bl 0x021AE4AC(side)` fail if !=0; tail `bl 0x021F04FC(desc, r6=r1_in)`.
  Totem arm: `0x021ACF68(side)` ==0, `0x021B1770(side,1)` == `0x021B16F0(side)`.

### C1 machine (NDS)
- Live race resolver 0x021B88F0(side, zone, mode); starts `[sp+8]` = 0x0202ABB8(cid).
- Board scan 0x021B8A64..0x021B8BBE: r7 = source side, r5 = zone 0..10, r4 = slot ptr,
  `[sp]` = affected side, `[sp+0x24]` = monster-eff unaffected mask (from 0x021AFBDC @0x021B894A).
- Hook site 0x021B8ACC = `bl 0x021A36EC` (cid at r7/r5); compares: <=0x1357 / 0x12A1 / 0x1EB1 /
  0x1F81; non-matching cid -> 0x021B8BB0 (next zone).
- Paracide arm 0x021B8AF6 (monster source): r5<=4, [sp+0x24]<=0, 0x021A32B4(r7,r5) face-up,
  [r4+0x44] bit 26 clear, ... `ldrh r6,[r4,#0x38]; movs r0,#0xA; str r0,[sp,#8]`.
- Ivy Shackles arm 0x021B8B7C: race 0xD, requires [sp] != r7 and turn player == r7.

### Build 1 (2026-09-15) — in-game confirmed by user 2026-09-15 (oracles 1-9 all "Confirmed")
- `_build_naturia_pineapple.py` on rom_all_patches.nds -> rom_naturia_pineapple.nds,
  sha256 f69b5ebfcd4ab230d63fcd570a96740a24dd3762e35e94003512dfcac2c67eaf, BUILD_EXIT=0, verify 10/10 PASS.
- A row 316 @0x0228EBC0 7d6f25023813 -> dd7325026514; C BL @0x021B8ACC eaf70efe -> e6f170ff;
  B cls2 phantom 0x1435 @84 dropped, 0x1465 @91 inserted (count 0x2B9).
- Stubs: CAVE_PINE_COND 0x0239F920 (92 B), CAVE_PINE_RES 0x0239F980 (40 B), CAVE_PINE_RACE 0x0239F9B0 (88 B).
- Probe (both stock + chain ROM): row 316 stock, hook bytes stock, 0x1338 & 0x1435 no card_prop & unclaimed.
- Helper disasm: 0x021B1770(side,race) = GY count where 0x021B1EE8(cid)==race; 0x021B16F0(side) = GY
  count where 0x02029E60(cid)!=0; 0x021AE4AC(side) = 0x021AE4BC(side,0,0,1); 0x021AC9FC(side,cid) =
  zones 0..10 where 0x021A3800(side,zone,cid) && slot occupied.
- NOT proven by execution (no savestate on this ROM) — in-game oracle is the first execution.

### Build 2 (2026-09-15) — archetype membership, oracle 10 in-game confirmed by user 2026-09-15
- User request: "It needs to be added to the naturia archetype table btw".
- Thunk walk (scratchpad setcode_walk.py, stock + chain ROM identical): "Naturia" = set code 0x3C,
  thunk 0x02023CD8, list 0x0209CEB0, n=36, only phantom 0x23F4 = Pineapple's own 3DS cid.
- Step E swaps 0x23F4 -> 0x1465 (count-neutral). Claim ("naturia_setcode_table", 0x23F4).
- sha256 7f4212c5d3a604a10d28f612487ae49b5b57fa63ae52f9b3460dbd0b7dccd31d, BUILD_EXIT=0, verify 11/11 PASS.
- Build 2 differs from Build 1 ONLY by step E (ARM9 list bytes).

### Shipped (2026-09-15)
- EE fast build: 68/68 steps, rom_all_patches.nds sha256 7f4212c5...7dccd31d == the tested Build 2 ROM
  (Pineapple and the WiFi-timers step are byte-disjoint, so order does not matter).
- verify sweep: 56 passed, 0 failed. equiv --all: every migrated module IDENTICAL.

## Ruled Out
- Poster 0x02256F7D for C2: scans monster zones 0..4 only (KB) — wrong zone.
- Repointing Treeborn's 0x19CB recheck literal — would take the arm away from Treeborn.

## Open Questions
- Resolver 0x0220731D second switch (0x02207424) sets summon mode r4/r6 per cid; donor gets
  default (r4=2, r6=1). Is Treeborn's arm the same? (affects position prompt only)

## KB
- Added VERIFIED `stat.race_override_resolver` and `battle.standby_gy_revive_poster`
  (author_facts --check: 466 PASS / 0 FAIL / 40 UNVERIFIED, 2026-09-15).

## Next Experiment
- User runs the 9-step oracle in `_build_naturia_pineapple.py`'s docstring on
  rom_naturia_pineapple.nds (sha256 f69b5ebf...2c67eaf), NORMAL duel.
- If C1 shows no Plant in card info: savestate with Pineapple face-up + another monster, then
  thumbemu/GDB bp on 0x0239F9B0 (is the stub reached?) and on 0x021B8BAE-equivalent write.
- If C2 offers nothing: bp 0x0239F920 (cond reached?) vs 0x022573DD (poster reached for 0x1465?).
