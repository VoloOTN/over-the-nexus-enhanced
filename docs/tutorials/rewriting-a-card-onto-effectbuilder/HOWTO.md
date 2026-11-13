# Porting a card onto EffectBuilder

## Goal

Replace a card's hand-assembled Thumb stubs with `EffectBuilder` calls **without changing a single byte** of the
built ROM, and grow the shared vocabulary as you go.

## Before you start

- One card per session. A batch migration once produced broken output and had to be reverted.
- Read [effect-writing](../effect-writing/HOWTO.md). The builder lives in `asm/effect_builder.py` on top of
  `asm/effect_shim.py` (`ThumbAssembler`, `StubBuilder`).
- Current state (2026-10-28): **the port is complete.** No `cards/` module calls `asm()`; every module with stub code
  builds it with `EffectBuilder`. Left as they were on purpose: the parked `highlander_list` and `new_cid_reborn_tengu`,
  and `reborn_tengu` (its only code is a legacy ROM-byte lift, off the default path). `thumb_asm.asm` stays as the
  encoder behind the golden tests and `stub_port`; new cards should not call it. The builder knows only the
  primitives in `PRIMITIVES` and the context fields in `CTX_FIELDS`; everything else goes through `b.insn(...)` and
  `b.bl(...)`.
- This tutorial now serves two jobs: writing a NEW card on the builder (steps 3-4), and the recipe below for porting
  any old text-assembler stub you meet (a card outside `cards/`, a restored module). Both end at a byte-identical ROM.
- Pick a small, boring card first. **Never port a card the notes mark PARKED.**

## Steps

### 1. Freeze the reference

```
uv run python -m otn_enhanced.build --out data/over_the_nexus/working/rom_before.nds
```

Keep that ROM. For a single card the sharper reference is the old-tree module (`equiv` default).

### 2. Get a readable starting point

If the card writes `asm(base, """...""")`, let the converter do it:

```
uv run python -m otn_enhanced.tools.stub_port cards.soul_charge            # report only
uv run python -m otn_enhanced.tools.stub_port cards.soul_charge --apply    # rewrite the file
```

The report lists each `asm()` block as convertible or skipped, with the reason. A converted block becomes
`b.label` / `b.ldr_const` / `b.bl` / `b.insn` lines (f-string placeholders stay your original Python expressions),
the turn-log call shapes become `b.turnlog_query` / `b.turnlog_post`, a literal call (`[arg setup] ldr rN,=ADDR ; blx rN`
or a bare `bl ADDR`) becomes `b.call("name", args, via=RN)` / `b.call_addr(ADDR, args, via=RN, arm=...)`, and the call site becomes
`b.assemble(base, pad="nop")`, which matches `asm()`'s bytes (see [effect-writing](../effect-writing/HOWTO.md)).

`--apply` checks the result against the golden bytes (`tests/golden_asm.json.gz`, every `asm()` call of a full
build with its real address) for each function that takes only `base`, **restores the file on any mismatch**, and
adds the checked functions to `tests/golden_ported.json`. A function whose own original output already differs from
its golden row (it patches the `asm()` bytes afterwards, e.g. `eva.gy_stub`) is not golden-checked; the build proves it. Functions it cannot check (extra arguments, or no
arguments with the base hard-coded inside) are proven by the full build: run `build --compare` and `verify`.

What it resolves: text held in a local variable assigned once from a literal (the dead assignment is removed),
and a module-level text constant (kept in place, with a note, because other code may import it).

What it skips, and why: text built by a function, a join or a concatenation; a placeholder that splices whole
lines of assembly (usually a named macro such as `_scan(...)`: expanding it is byte-safe but flattens a helper
into anonymous instructions, so port it by hand into a helper that takes the builder); a placeholder inside a
register name or half an immediate; `ldr` into a high register; and `asm()` with `symbols=`.

**Hand-porting a macro helper.** When a block splices a helper such as `{_param("r7")}`, port the helper itself so
it emits into the builder, and keep it as a named helper:

1. Run `stub_port --apply` first; it converts the card's other blocks and skips the splicing one.
2. Add the splicing function's golden row to `tests/golden_ported.json` from `tests/golden_asm.json.gz` before you
   touch it (module, function, base, bytes).
3. Rewrite the helper as `def _param(b: EffectBuilder, reg: int) -> None` that calls `b.insn(...)` for each line.
4. For the block, replace each `{_helper(...)}` in a scratch copy with a one-line marker (`movs r7, #0x77`), let the
   converter lower the whole function, then swap each marker line `b.insn("MOV", "R7, #0x77")` for `_helper(b)`.
   Lower the helper's own text the same way (as a throwaway `asm()` function) and wrap the result in
   `def _helper(b: EffectBuilder)`. A helper's branch labels (`to7e`) stay as labels the caller defines.
   Do not commit the expanded form. Worked example: `cards/ultimate_conductor_tyranno.py` (`_defender`).
5. Check the `effect_builder` import line: the converter imported only the registers it saw, and the hand-ported
   function may name more (a missing `R2` is a `NameError` in the golden test).
6. `python -m otn_enhanced.tests.test_stub_golden`, then the full build (compare its sha256 to the Enhanced hash) and
   `verify <rom> --only cards.<module>` (seconds; the full sweep costs as much as the build, run it once at the end).
7. Run `python -m otn_enhanced.knowledge.verify_knowledge`: a KB proof may call your helper directly and assert on its old
   TEXT result (`card.grapha_clause2` did). Rewrite such a proof to compare bytes with the old helper's.

Gotchas met while hand-porting (each cost a failed run):
- `b.ldr_const(reg, ...)` takes a plain int register; a `Reg` object formats as `RR3` and crashes. Pass `int(reg)`.
- A marker for the lowering trick must not use r0-r3 when it sits before a literal call (absorbed as argument setup).
- The converter names its builder `prog` when `b` is already used in the function; swap markers by regex on `\w+\.insn`.
- A helper may be a local closure (`call3`), a loop that builds a string (`body`), or a build-time flag (`C3_DIAG`). Port
  closures to module level; port a flag-gated helper and prove it by flipping the flag in a pre-edit copy and the new module.
- Write scripts with the Write tool: a bash heredoc ate `\\n` in a path-substring edit and produced a confusing failure.
- **Padding.** `asm()` pads the gap before a literal pool with NOP (`0x46C0`); the builder's default is `0x0000`. Use
  `assemble(base, pad="nop")` when the original called `asm()` and the default when it hand-packed halfwords (check
  which the original did, a missed pad is one wrong halfword). A fragment with no pool that must not grow: assemble with
  `pad="nop"` and slice to the exact length.
- **Explicit zero offsets.** `LDR R0, [R0]` and `LDRH R3, [R5]` need `[R0, #0]` / `[R5, #0]` to encode.
- **Text-returning stubs become byte-returning.** Many stubs returned asm text that a caller passed to `asm()` and to
  `cave3.put(..., src)`. The port returns bytes (`b.assemble(...)`) and `cave3.put`/`cave3._checked` no longer get a
  source string: it only fed a pop-into-LR regex check, and the builder cannot make that mistake.
- **`"".join(...)` and local string builders become `for` loops** emitting into the builder (`b.ldr_const(1, cid)` /
  `CMP` / `BEQ` per cid). Registers that were strings (`"r2"`) become ints. A stub taking an optional "previous" text
  becomes `if prev:`.
- **Blob factories** (`ov5_blobs()`, `ov3_blobs()`: no base argument) cannot get `golden_ported.json` rows. Check the new
  stubs directly against the captured hex in `tests/golden_asm.json.gz` (keyed to the factory), plus an old-vs-new script.
- **A stub reached through a wrapper** (`_stub(addr, reserve, asm_text)`) is invisible to `stub_port`: point a scratch
  copy at `asm()` directly, run `convert_source`, then re-wrap. `brilliant_fusion` did this (8/8 converted).
- **Raw-halfword modules** (no `asm()`): disassemble with `asm/thumb_disasm`, write builder code, and gate on an
  old-vs-new script only; there is no golden row to lean on. If the module's only "code" is a ROM-byte copy plus a patch
  (`reborn_tengu`), leave it.
- **`compare_orig` only runs `*_stub` / `build_*` functions of the form `f(base)`.** For anything else (extra arguments,
  no base, factories) write your own old-vs-new script in a uniquely-named scratchpad folder: pre-edit copy vs new,
  every argument and several bases, including bases where both must raise.
- **`verify --only` imports every step module** (shared hooks register on import). It used to import only the one
  module, which made `snoww` fail with a phantom "cid 0 changed leaf"; fixed 2026-10-28.
- **`build --compare` needs `rom_baseline.nds`, which does not exist.** Compare `sha256sum rom_all_patches.nds` by hand.
- **Several modules at once.** Safe to port in parallel (one agent per module) as long as nobody builds: a build
  imports every module, so an edit mid-build changes the hash. Agents share `tests/golden_ported.json` (re-check the
  other rows survive a write). Build once per batch, then `verify --only` each module and `verify_knowledge`.

The converter is mechanical. The readability gain is in the idiom lines; plain instructions become `b.insn(...)`,
which reads about the same as the asm text. Polish the result by hand (names, short comments), and re-run the
golden test after each edit.

Do not call every function of a module to compare it before and after: `main()` and `verify()` have no required
arguments and will build and overwrite single-card ROMs in `data/over_the_nexus/working/`.


`asm/effect_shim.lift_handler_to_builder` turns an existing overlay-3 handler into builder calls. For your own
stub, disassemble the current blob (`asm/thumb_disasm.decode_thumb`) and write down, per instruction group, what
it does.

### 3. Rewrite one stub at a time

Replace the halfword list or `ThumbAssembler` calls with builder calls. Keep raw `b.insn` lines for anything the
vocabulary does not name; do not invent an abstraction for a one-off. Then:

```python
blob = b.assemble(addr)
assert blob == OLD_BLOB          # while porting: the old bytes, captured before you touched anything
assert_thumb1_only(blob, addr)
```

Capture `OLD_BLOB` by calling the old builder at the same address, then delete the assertion once the port is
proven.

### 4. Grow the vocabulary

When a call is repeated across cards, add it to `PRIMITIVES` (`Primitive(addr, "(args) -> result")`) or a field
to `CTX_FIELDS`, using an address that is proven (a KB fact or a shipped, tested card). Keep the name stable.

### 5. Prove it

```
uv run python -m otn_enhanced.equiv cards.my_card              # vs the old-tree original
uv run python -m otn_enhanced.build --compare data/over_the_nexus/working/rom_before.nds
uv run python -m otn_enhanced.verify <rom> --only cards.my_card
```

`equiv` must report `[IDENTICAL]`. The full build must hash identically: `equiv` cannot see two cards fighting over
a shared row.

### 6. Trim the comments

Once it is proven, shorten the module's prose to what a reader needs: the card text, the clause map, load-bearing
`⚠` warnings, and one `# elbow:` line for any place that could be improved. Move long reverse-engineering notes
into `notes/<card>-findings.md`.

## Worked example

`cards/mystic_piper.py`. `_build_stub` is `EffectBuilder` end to end. `_build_cond` and `_build_cost` were the
first stubs ported onto the turn-log idioms (`ctx_field`, `turnlog_query`, `turnlog_post`): capture the current
bytes at every slot home first, port, then compare, and they matched at ov5 and ov3. The native `PUSH`/`POP`,
guard compare and chain stay as `b.insn`/`b.bl` because the vocabulary does not name them. Both styles live in the
same file, and `verify()` checks each against `decode_thumb`.

## Check it

- `equiv` identical, full build identical, `verify` passes.
- The module is shorter and a reader can follow the effect without disassembling.

## Pitfalls

- **Do not "improve" behaviour while porting.** A different instruction sequence that is functionally equal still
  changes bytes and can change flag state a downstream stub relies on.
- A rewrite that passes the card's own check can still change a shared hook's register. Always run the full
  build.
- `ThumbAssembler.insn("BL", label)` is mis-sized; use `bl(addr)`.
- Do not mark a card confirmed because the rewrite passed `equiv`. Only an in-game test does that.
