# Reborn Tengu (0x1463) — findings

## Confirmed
- 2026-10-29: DSL rewrite of `cards/reborn_tengu.py` builds a ROM byte-identical to the previous hand-written
  module (SHA-256 `d4908d7e…d81a`, `write_text=True`, base `rom_ov3_compact.nds`). Byte-equality only.

## Ruled Out
- (none)

## Open Questions
- (none)

## Next Experiment
- (none)

## Inherited from the pre-DSL docstring — UNVERIFIED (not re-proven, and no longer checked by `verify()`)
- The resolver's per-cid switch (entry 0x02206F50) sends 0x1463 and 0x2085 to the default arm 0x02206FD2
  (old `verify()` checked this with a Thumb simulator, `_res_switch_leaf`).
- Minefieldriller 0x2085 keeps its NATIVE cls2 record and criteria row (old `verify()` asserted both).
- Phantom 0x14E9 occurs only in the leave-mask table and cls2[100], so dropping it from both leaves it nowhere.
- The 3DS's own Reborn Tengu leave-mask row `{0x25E3, 0x000C}` settles the mask value 0x000C.
- list30/list106 membership would arm the dispatcher first and skip the mask table (0x021C80FE); the DSL
  timing still asserts the donor is in neither.
- Full RE record lives in `finished_patches/reborn_tengu.py` (oracle) and git history.
- `main(ov3=False)` (the ov5-cave placement of the selector blob) is gone from this module; the parked
  `new_cid_reborn_tengu.py` imported `rt.*` constants from the old file and will not import until fixed.
