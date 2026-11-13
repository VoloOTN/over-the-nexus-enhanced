# Plan: move every card's injected code onto the C toolchain

Status: PHASE 0 COMPLETE 2026-11-03; Phase 1 in progress (batches 1-18 + slot-calling stubs + templates: 105 gated, see notes/c-migration-status.md). The pilot (Mystic Piper's resolver in C, `_build_mystic_piper_c.py`) was in-game
confirmed by the user on 2026-11-03. Findings live in `notes/c-toolchain-findings.md`.

**Target: all effect logic in C. Only the glue where our code meets the engine's code stays in `.S`**, as a few
shared shim macros. A stub stays fully `.S` only when C plus its shim doesn't fit its slot, or when a verifier
needs an exact instruction pattern. Both C and `.S` build through `cc.py` (gcc/as 14.2.Rel1), so the encoding
footguns disappear either way: Thumb-2, ADD imm3, POP-into-LR, BL-label size.

## What there is to move (census 2026-11-03)

- 104 card modules in `otn_enhanced/cards/`; 86 build stubs with `EffectBuilder`, and there are 442 `.assemble()`
  calls in all.
- The captured corpus (`tests/golden_asm.json.gz`, 574 stubs from 65 modules), by how a stub meets the engine:

  | Shape | Stubs | Bytes | Becomes |
  |---|---:|---:|---|
  | plain function (`push {..lr}` ... `pop {..pc}`) | 350 | 37.7 KB | C |
  | front that hands off to native code (`bx rN` / `b 0x...`) | 132 | 8.5 KB | C, or C + front shim |
  | mid-function hook (no prologue, inside an engine frame) | 85 | 11.6 KB | C + splice shim |
  | tiny thunks / other | 7 | 0.2 KB | `.S` (C gains nothing) |

  The split is a text heuristic. Phase 0 replaces it with a per-stub classification.
- The stubs reference 137 distinct engine addresses, which is the eventual size of `engine_syms.txt`.

## Why some stubs can't be plain C, and the fix for each

| Obstacle | Fix |
|---|---|
| **Splice hooks**: the inputs are the engine's live registers; the stub returns into the middle of the engine function | **splice shim**: save r0–r7 into a `Regs` struct on the stack, call `void hook(Regs *r)`, restore, jump back to the site |
| **Fronts that pass the original registers to native code** (r1 kept for the callee, LR deliberately not kept) | Often just C: `return native(a, b, c, d);` keeps r4–r7 and passes ≤4 register args. This only works if the **native callee takes ≤4 args and never reads its caller's frame**, because C adds a stack frame where the old stub tail-jumped. Otherwise use the **front shim**: C returns a decision, and the shim does the original tail-jump |
| **Reads of the engine's stack** (leave-descriptor `[sp+0x90]` / `+0x44` / `+0x144`) | **frame shim**: pass the entry `sp` in as `u32 *frame`; C reads `frame[0x90/4]` |
| **Verifier pattern-matching** (`effect_verify.bl_reaches` / `addr_reaches` follow list-search fronts by their exact `ldr r3,=key; cmp r0,r3; bne miss; ...` shape, used by 12 card modules) | Keep those fronts in `.S` as they are (about 7 instructions each). A follow-by-emulation verifier would free them; that's optional, later |
| **Fixed slot sizes** (each shim costs about 8–16 B; the ov3 pool has about 60 B free) | Measure C+shim against the slot per stub. Too big means a byte-identical `.S` fallback. **Never move a stub out of the ov3 pool**: that breaks the card in puzzles |
| **Tiny thunks** (1–3 instructions) | `.S` |

The shims are **three macros in one shared file** (`asm/c/shim.S`): splice, front and frame. Each one is
written and proven once with the trace harness on a real hook. After that, a card's `.S` is one line per hook
(`SPLICE_SHIM hook_name, return_site, scratch_reg`).

## How a converted stub is proven

| Form | Gate |
|---|---|
| C, or C + shim | **trace-equivalence** against the old bytes on every branch, plus it fits its slot, plus (for fronts) the callee audit |
| `.S` fallback | **byte-identical** to the old slot bytes |

There's no in-game testing per batch (decision 1). Everything goes behind `build --c` until the user's final
retest.

## Phase 0: infrastructure (once, before any card)

1. **DONE 2026-11-03. `.S` support in `cc.py`**: assemble `.S` files with the same linker script, so the entry sits at the slot and
   engine symbols come from `engine_syms.txt`. Pools are placed with explicit `.ltorg`, which byte-identical
   fallbacks need. A card can mix C and `.S` files.
2. **DONE 2026-11-03 (`tools/c_corpus.py`). Stub corpus from the ledger.** `allocations.yaml` names every slot (1495 entries). A tool reads each live
   slot's bytes from `rom_baseline.nds`. That gives the "before" side of every comparison, whatever builder
   made the stub.
3. **DONE 2026-11-03. Trace-equivalence harness** (`tools/c_equiv.py`), built on `scratch/thumbemu.py`:
   - Run the old and new blob from the same savestates.
   - Intercept every engine call: record it with its arguments and return a scripted value.
   - Sweep the return values of predicate calls so every branch runs.
   - Compare the call sequence, the arguments, every memory write, the return value, and (for shims) the
     registers and `sp` at the jump back into the engine.
   - Flag any read above the entry `sp`, so an undeclared frame read is caught.
4. **DONE 2026-11-03 (`tools/c_callee_audit.py`; KB facts deferred to first use). Callee audit** for fronts that become plain C: disassemble the native callee and prove it takes ≤4 register
   args and makes no `sp`-relative read above its own frame. Record each result as a KB fact. A callee that
   fails needs the front shim.
5. **DONE 2026-11-03 as TWO macros (SPLICE carries the frame pointer; `tools/c_shim_proof.py`). The three shim macros**, each proven on one real hook with the harness before any card uses it.
6. **DONE 2026-11-03. Classifier** (`tools/c_classify.py`): for each corpus stub, propose C / C+front / C+splice / C+frame / `.S`
   with its reason (entry shape, exit shape, frame reads, callee audit, pattern-matched by a verifier).
   Ambiguous cases get a human look.
7. **DONE 2026-11-03: 287/287 routines have a fact (`tools/c_engine_syms.py`; 283 callable, 4 c_midfn). engine.h/engine_syms entries still go in per card (name + arity). `engine.h` grows from the corpus.** Each of the 137 engine addresses needs a VERIFIED or ANCHORED KB fact
   before it goes in (cc.py enforces this). Addresses without one get one first, the way `reveal_top` did.
   This is the bulk of Phase 0's work.
8. **DONE 2026-11-03 (`otn_enhanced/c_forms.py`: slot overrides applied as a gated final step). `build --c` + `notes/c-migration-status.md`**: the switch that selects converted forms, and one row per
   stub (form, gate result, size vs slot) that becomes the final-retest checklist.

## Phase 1: plain functions → C

The 350 plain functions. Start with the 25 modules made only of plain functions, smallest first, and modules
already shipped and confirmed in-game first: Koa'ki Meiru Wall, Raiden, Sekka's Light, That Grass Looks Greener,
and so on. For DSL-built cards (`dsl.py`), switch the slot to `c_source`, or have the verb emit C. Decide that
once the first few are done; don't redesign the DSL up front.

## Phase 2: fronts → C (direct or + front shim)

The 132 fronts, taking the callee-audit passes as plain C first. Then the front shim for the rest, minus the
verifier-pattern fronts (Phase 4).

## Phase 3: splice and frame hooks → C + shim

The 85 mid-function hooks and the frame readers. Group them by hook family (the shared summon-trigger site,
the leave hook, the param-provider hook, and so on). One family's shim parameters are then proven once and
reused across its cards.

## Phase 4: `.S` fallbacks

Everything that didn't fit its slot with a shim, the verifier-pattern fronts and the thumbs. Each is converted
to `.S`, and each must be byte-identical to its old slot.

## Phase 5: final retest and switch-over

1. `build --c` passes the `otn_enhanced.verify` sweep (46/0 or better), and every row in the status table is
   green.
2. The user retests every card in-game from `rom_all_patches_c.nds`.
3. Failures revert to their old form (one flag per module). The rest become the default, the old forms are
   deleted, and the baseline is re-frozen once and recorded in `CURRENT-BASELINE.md`.
4. New cards are written in C (+ shim) from the start. The `card` skill and the `effect-writing` tutorial say so.
   `EffectBuilder` / `ThumbAssembler` / `thumb_asm` and their golden tests are retired once no module uses them.
   `PRIMITIVES` merges into `engine_syms.txt`.

## Risks

- **Toolchain drift.** gcc is pinned to 14.2.Rel1. Upgrading it changes every C stub's bytes, and that means a
  new retest.
- **Hidden contracts.** A stub that looks plain may rely on r1 surviving or on the caller's frame. The harness
  flags reads above entry `sp` and register differences at shim exits. A front's callee is covered by the
  audit, not the harness, because the harness intercepts it.
- **Slot pressure in the ov3 pool.** Expect most `.S` fallbacks there. Measure; don't guess.
- **The deck preflight abort** (`rpg015_8_jill.ydc`, 39 cards). The user is fixing it. It blocks any
  byte-identity check until then.

## Decisions

1. **Retest policy. DECIDED 2026-11-03:** the user retests **every card once, after everything is
   converted**. The default build and `rom_baseline.nds` don't move until then; converted forms build only
   with `build --c`. Each converted card is AWAITING IN-GAME TEST until that pass.
2. **Model. DECIDED 2026-11-03:** all logic in C, glue in shared `.S` shims, and `.S` fallback only where C
   doesn't fit or a verifier needs the exact pattern.
