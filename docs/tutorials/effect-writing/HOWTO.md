# Writing the code an effect runs

## Goal

Write a small Thumb-1 routine (a "stub") that does what the card's text says, using the engine's own
routines, and get it into a form you can place in the ROM.

## Before you start

- Read [donor-cards](../donor-cards/HOWTO.md). The stub is only half of a card; a table row points at it.
- Have the printed text from `scratch/ygoprodeck_cache.json`. Do not work from memory.
- Know the instruction-set rule. The NDS ARM9 is ARMv5TE: **Thumb-1 only**. `movw`, `movt`, `b.w`, `bl.w`,
  `cbz`, `cbnz`, `it`, `tbb`, `tbh` are undefined instructions and freeze the console. `capstone` will happily
  disassemble them as valid, so never trust a plain disassembly.

## Steps

### 1. Find how the engine already does each sub-action

Look for a real card that does the same thing and see which routines it calls.

```python
from otn_enhanced.tools.effect_registry import load_registry
reg = load_registry()
card = reg.card_by_name("Giant Rat")
for slot, addr in card.slots.items():
    h = reg.handler(addr)
    print(slot, hex(addr), h.size, [hex(t) for t in h.calls])
```

`tools/effect_registry/WRITING_EFFECTS.md` walks through this end to end.

### 2. Author the stub with `EffectBuilder`

`asm/effect_builder.py` lowers named operations to relocatable Thumb-1 bytes. It handles `BL` re-encoding,
the literal pool and branch offsets.

| Call | Meaning |
|---|---|
| `b.prologue(save=[R4, R5])` | `push {r4, r5, lr}` |
| `b.epilogue(ret=0)` | `movs r0,#ret; pop {r4, r5, pc}` |
| `b.ctx_field("controller", dest=R4)` | load a field of the effect context (R0 at entry) |
| `b.call("draw", side, 1)` | marshal args into R0.. and `bl` a named primitive. A value above `0xFF` (a cid) is loaded with `ldr rN,=value`, anything smaller with `movs` |
| `b.call("draw", side, 1, via=R5)` | the literal form `ldr r5,=addr\|1 ; blx r5`, which is how most stubs call the engine. `via` must be above the argument registers |
| `b.call_addr(0x021D2584, ..., via=R5)` | same, for an address not in `PRIMITIVES` (omit `via` for a direct `BL`) |
| `b.turnlog_query(side, cid, kind, via=R5)` | has `cid` logged a kind-`kind` node this turn (slot `0x0B`)? Nonzero in R0 if so |
| `b.turnlog_post(side, cid, kind, via=R5)` | log a kind-`kind` node for `cid` this turn (the once-per-turn stamp) |
| `b.if_eq(R0, 0, "done")` / `b.if_ne(...)` | compare with an immediate and branch |
| `b.label("done")` | branch target |
| `b.insn("LDRB", "R0, [R4, #0x2]")` | any single Thumb-1 instruction as text |
| `b.bl(addr)` | a raw `bl` |
| `b.bl_label("name")` | a `bl` to a local `b.label("name")`; clobbers LR, so use it only after LR is saved |
| `b.peek_deck_top_cid(side, dest=R5, scratch=(R2, R3))` | read the top Deck card's cid |

Named primitives (`asm/effect_builder.PRIMITIVES`): `draw`, `reveal_top`, `is_monster`, `cid_level`, `get_race`,
`turnlog_post`, `turnlog_query`. A primitive goes in the table when a card first calls it, with the
knowledge-base fact that proves it; read the signature string before calling. Routines nothing calls yet are
still named in the effect registry (`tools/effect_registry/primitive_names.py`, `_PROVEN`: `has_set_code`,
`ui_event_post`, `depth_push`/`depth_pop`, `picker_readback`, `list_picker`, `ss_gate_a`/`ss_gate_b`), so
`reg.primitive(addr)` finds them; call them with `call_addr(addr, ...)` until a card makes them worth a table
entry. The `ss_gate_*` thunks are named for what they call, not for what the gate checks, which is not proven.
Context fields (`CTX_FIELDS`): `cid` (+0, u16), `controller` (+2), `race` (+3), `trigger_type` (+4),
`trigger_category` (+5), `slot_phase` (+6), `cost_ran` (+7, descriptor), `card_instance` (+0xC).

Entry convention: `R0` is the effect context; the routine returns in `R0`, usually 0.

### 3. Assemble and validate

```python
blob = b.assemble(stub_addr)                     # relocatable: pass the address it will live at
assert len(blob) <= RESERVE
assert_thumb1_only(blob, stub_addr)              # asm/effect_verify.py -- walks the encoding itself
```

`assert_thumb1_only` raises on any 32-bit Thumb-2 form or `cbz`/`cbnz`. Use it instead of a `capstone` grep.

**Padding mode.** `assemble(addr)` pads the literal pool with a `0x0000` halfword and needs a 4-aligned address.
That is what the cards already on the builder ship, so it stays the default. `assemble(addr, pad="nop")` is
byte-for-byte what the text assembler `thumb_asm.asm` emits: `nop` (`0x46C0`) padding, always to a 4-byte
boundary of the real address (even with no pool), and a halfword-aligned address is allowed. Use `pad="nop"` when
you are porting a stub that used `asm()`, so no byte moves. `tests/test_stub_golden.py` proves the two agree on
574 real stubs. No card in `cards/` calls `asm()` any more, so a NEW stub should use the default pad; reach for
`pad="nop"` only to match old bytes. `thumb_asm.asm` remains as the reference encoder for the golden tests and
`tools/stub_port.py`, not as something cards import.

### 4. Place it

Put the blob in the ov3 pool or the ov5 cave and point a table field at `addr | 1` (the Thumb bit). See
[caves-and-allocation](../caves-and-allocation/HOWTO.md) and [effect-insertion](../effect-insertion/HOWTO.md).

## Worked example: Mystic Piper's resolver

`cards/mystic_piper.py`, `_build_stub`. "Draw and reveal 1 card; if it is a Level 1 monster, draw 1 more."

```python
b = EffectBuilder()
b.prologue(save=[R4, R5])
side = b.ctx_field("controller", dest=R4)
b.call("reveal_top", side)
cid = b.peek_deck_top_cid(side, dest=R5, scratch=(R2, R3))   # BEFORE the draw: draws are queued
b.call("draw", side, 1)
b.call("is_monster", cid)
b.if_eq(R0, 0, "done")
b.call("cid_level", cid)
b.if_ne(R0, 1, "done")
b.call("draw", side, 1)
b.label("done")
b.epilogue(ret=0)
blob = b.assemble(stub_addr)
assert_thumb1_only(blob, stub_addr)
```

The two framework stubs in the same file (`_build_cond`, `_build_cost`) read the descriptor with
`b.ctx_field(...)` and use `b.turnlog_query` / `b.turnlog_post`; only the `PUSH`/`POP`, the guard compare and
the chain into the native routine stay as `b.insn` and `b.bl`. They were ported from raw `b.insn` lines and
assemble to the same bytes at both slot homes.

## Check it

- `assert_thumb1_only` passes and the size equals what you reserved.
- Disassemble the **built ROM**, not your source: `asm/thumb_disasm.decode_thumb(blob, addr)` and compare the
  `BL` targets with what you meant to call (see `verify()` in `cards/mystic_piper.py`).
- Run it in melonDS. Static checks catch bad encodings and wrong addresses; only the emulator shows the effect
  fires.

## Pitfalls

These each cost real debugging time.

| Trap | Rule |
|---|---|
| Thumb-2 opcodes | Never emit them. Load 32-bit constants from the literal pool, not `movw/movt`. |
| 3-operand `ADD`/`SUB` with an immediate above 7 | It miscodes. Use the 2-operand imm8 form. |
| `POP {..., LR}` | It miscodes to `POP {..., PC}`. Disassemble every built stub. |
| `BLX` to a literal with bit 0 clear | That is ARM state and freezes. Literals meant for `blx rX` need the Thumb bit. |
| `ThumbAssembler.insn("BL", label)` | Sized 2, emits 4. Use `a.bl(addr)` (two-pass). |
| Stack-based cid switches | The engine encodes some switches as `base ± imm` in `[sp]`; register-only analysis picks the wrong leaf. |
| A literal that is a table *address* | Do not inline the table's contents. The pool word is a pointer. |
| Draws are queued | Inspect a card **before** drawing it. |
| Stub start alignment | Keep it 4-aligned: `ldr rX,[pc,#imm]` uses `pc & ~3`. |
| Injecting the donor's own cid into `ctx+0` | Never overwrite `ctx+0` with a phantom cid. It passes static checks and crashes in-game. Retarget a switch leaf instead. |

## Known rough edges

- `PRIMITIVES` has six entries. Most cards use `call_addr` or `b.bl(ADDR)` with a local constant, which is why
  the same address appears under different names across cards.
- `0x021D2584` used to be labelled `special_summon_from_deck` (a heuristic name in `effect_extract`). It is the
  turn-log **post**, proven by the knowledge base, and is now `PRIMITIVES["turnlog_post"]` with
  `turnlog_query` (`0x021A14E8`) beside it. The old `PRIMITIVES` entry for `0x021D1AFC` was the middle of a
  function and has been removed. `WRITING_EFFECTS.md`'s Special Summon example is still based on the wrong name
  and carries a correction banner; there is no plain `(side, cid)` summon primitive (the engine is `0x0226925C`).
- Five modules use `EffectBuilder` (`cardcar_d`, `kuribandit`, `mystic_piper`, `ninishi`, `scrap_raptor`).
  About 96 use the layer below it (`ThumbAssembler` / `StubBuilder`) directly. The blocker for moving the rest
  is the six-entry vocabulary, not the builder itself: each card that gets ported should add the primitives and
  context fields it needed. See
  [rewriting-a-card-onto-effectbuilder](../rewriting-a-card-onto-effectbuilder/HOWTO.md).
