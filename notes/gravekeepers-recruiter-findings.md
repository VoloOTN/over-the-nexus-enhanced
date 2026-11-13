# Gravekeeper's Recruiter (0x0FB4) — inherited claims (UNVERIFIED, not re-proven)

Moved out of the pre-DSL module docstring when the card was converted to the DSL. The old file is in git history.

## Confirmed
- DSL rebuild is byte-identical to the original module's ROM (see `notes/dsl-findings.md`). Byte-equality only.

## Inherited, UNVERIFIED (from the old docstring)
- The trigger is a leave-MASK row, not list30: the leave dispatcher has three registration paths that all set arm flag
  `[sp+0x18]`; the mask table is consulted only when neither list armed it. A records-free donor cannot join list30 by
  data (30 real entries, 0x0226E940 abuts the 30th, growing down needs a cid < 0x0D7C = all Speed Spells).
  *Encoded in the DSL as asserts (donor in neither list), not as the reasoning.*
- Mask 0x0800 (destination is GY) is field-only because the whole dispatcher is, which gives "you control".
- cls2 and the trigger are a matched pair: list30/mask registration pairs with +0C=0 / +10=0 (Sangan's wiring);
  Garsem's destruction-only +0C=0x0224A115 mixed with it froze an earlier build. *Encoded: the cls2 row is Sangan's.*
- Filter is a clone of native DEF filter 0x0223C89C with a has_set_code prefix; wrapper is Botanical Girl's native
  deck-search wrapper (36 B, BL at +0x18, filter literal at +0x20).
- In-game (old record, per old docstring, 2026-09-10): triggers on battle/effect destruction, Tribute and Synchro
  Material; not on discard or mill; Botanical Girl is her own card again; puzzles still play. Not re-confirmed here.
- Dropped from the DSL version: the Botanical-untouched asserts (cls2/populate/list30 of 0x1ED4) and the `ov3=False`
  (ov5) placement. The ov3 placement was already the default.

## Next Experiment
- None for the conversion. `steps` runs the module with its defaults, as before.
