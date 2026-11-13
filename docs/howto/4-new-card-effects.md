# HOWTO 4: Create a new card effect

The short path. Each step links to the deep tutorial in [docs/tutorials](../tutorials/README.md).

**The technique:** you never add a card. You take a useless vanilla Normal Monster (the *donor*), **keep its
cid**, and overwrite its name, stats, text and effect-table rows so it becomes the new card.

## 0. Before you start

- [HOWTO 1](1-setup-and-build.md) done, `rom_all_patches.nds` built.
- Open `notes/<card>-findings.md` with `## Confirmed` / `## Ruled Out` / `## Open Questions` /
  `## Next Experiment`. Write facts into it as you prove them, not at the end.

## 1. Get the real card text

Read it from `scratch/ygoprodeck_cache.json`. Never from memory, never from the ROM's `cards_text.json`
(mistranslated). Split it into numbered clauses and decide which are in scope.

## 2. Pick a donor

Must be: a **Normal Monster**, not competitively played, ideally ATK ≤ 1500 filler, with name/description slots
big enough (or a `card_text.CARD_TEXT` entry, which lifts the length limit), and **no per-cid gates**:

```bash
uv run python -m otn_enhanced.tools.donor_scan 0x1463
```

A clean scan = no data structure names the cid. Prefer a donor whose printed timing already matches.
→ [donor-cards](../tutorials/donor-cards/HOWTO.md)

Before writing code, mark each as PROVEN (with address evidence) or ASSUMED: per-cid gates on the donor;
the exact zone the effect searches; text lengths; where once-per-turn is stamped.

## 3. Write the card module

Create `otn_enhanced/cards/<card>.py`. Prefer the **DSL** (`otn_enhanced/dsl.py`): the spec reads like the
card text and compiles to Thumb stubs plus table rows.

Model it on [mystic_piper.py](../../otn_enhanced/cards/mystic_piper.py):

```python
from otn_enhanced import dsl
from otn_enhanced.dsl import ignition, tribute_self, once_per_turn, draw, card_props
from otn_enhanced.effects import cave3

SPEC = ignition(0x13B8, cost=tribute_self(), limit=once_per_turn(), effect=[draw(1)],
                slots=(cave3.CAVE3_MYCARD_RES, cave3.CAVE3_MYCARD_COND, cave3.CAVE3_MYCARD_COST),  # your claimed slots (step 6)
                phantom=0x1436)
PROPS = card_props("LIGHT", "Spellcaster", 1, 0, 0)
main, verify = dsl.make(SPEC, PROPS, out="data/over_the_nexus/working/rom_mycard.nds")
```

Available timings and verbs are listed in the `dsl.py` docstring. A missing verb = add a class with
`lower(b, ctx)`; a missing timing = a spec class with `compile(view)`.

If the DSL has no verb for your effect, write the ASM yourself (next section).

Every module exposes `main(write_text=, src=, out=)` and `verify(out)`.

## 3b. Writing the ASM

### How an effect runs

An effect is **a table row plus a few small Thumb routines ("stubs")**. The row is keyed by the card's cid and
holds the stubs' addresses. The engine calls each stub at the right moment with **`R0` = the effect context**,
and reads the answer back from **`R0`**.

For an ignition effect ("You can …", a cls3 row `(cid, resolver|1, 0, condition|1, cost|1, 0)`):

| slot | stub | called when | returns |
|---|---|---|---|
| `+04` | resolver | the effect resolves: do the thing | `0` |
| `+0C` | condition | the game asks "can this activate now?" | `0` = no, non-zero = yes |
| `+10` | cost | on activation, before resolving: pay the cost, stamp once-per-turn | native routine's result |

Other timings (triggers, Spells, summon procedures) use other tables: cls0 Spells, cls1/cls2 triggers,
criteria rows for "select a card". Find a shipped card with the same timing and copy its row shape.
→ [effect-insertion](../tutorials/effect-insertion/HOWTO.md)

Effect context fields (`EffectBuilder.ctx_field`):

| name | offset | meaning |
|---|---|---|
| `cid` | +0 (u16) | the card's cid |
| `controller` | +2 | 0/1, the player who owns the effect: pass this as "side" |
| `race` | +3 | |
| `trigger_type` / `trigger_category` | +4 / +5 | |
| `slot_phase` | +6 | |
| `cost_ran` | +7 | non-zero once the cost has run (the condition is called again mid-activation) |
| `card_instance` | +0xC | |

### The hard rules

- **Thumb-1 only.** The DS CPU is ARMv5TE. `movw`, `movt`, `b.w`, `bl.w`, `cbz`, `cbnz`, `it` freeze the
  console. Load 32-bit constants from a literal pool; call far with the two-halfword `BL`.
- Save what you use: `push {r4.., lr}` on entry, `pop {r4.., pc}` on exit. Never `pop {.., lr}`.
- Any address you call through a register needs the **Thumb bit** (`addr | 1`); an even address switches to
  ARM mode and freezes.
- Draws are queued: inspect a card (e.g. peek the Deck top) **before** you draw it.

### Find the engine routine to call

You don't write game logic; you call the engine's own routines. Find them by looking at a card that already
does the same thing:

```python
from otn_enhanced.tools.effect_registry import load_registry
reg = load_registry()
card = reg.card_by_name("Pot of Greed")            # any stock card with the sub-action you need
for slot, addr in card.slots.items():
    h = reg.handler(addr)
    print(slot, hex(addr), [hex(t) for t in h.calls])   # the routines its handlers call
```

Then check the address in `otn_enhanced/docs/engine/*.yaml` (proven facts) and grep `otn_enhanced/cards/`
for a card that already calls it. Named routines in `EffectBuilder` (`PRIMITIVES`): `draw`, `reveal_top`,
`is_monster`, `cid_level`, `get_race`, `turnlog_post`, `turnlog_query`. Anything else: `call_addr(0x0…)`.

### Write the stub with `EffectBuilder`

`otn_enhanced/asm/effect_builder.py` turns calls into Thumb-1 bytes and handles `BL` encoding, branch
offsets and the literal pool.

| call | emits |
|---|---|
| `b.prologue(save=[R4, R5])` | `push {r4, r5, lr}` |
| `b.epilogue(ret=0)` | `movs r0, #0 ; pop {r4, r5, pc}` |
| `b.ctx_field("controller", dest=R4)` | load a context field (context in `R0`, or `ctx=R4`) |
| `b.call("draw", R4, 2)` | put args in `R0`, `R1`, … and `bl` a named routine |
| `b.call_addr(0x021AD870, R4)` | the same, for any address |
| `b.if_eq(R0, 0, "skip")` / `b.if_ne(...)` | compare with an immediate and branch |
| `b.label("skip")` | branch target |
| `b.turnlog_query(side, cid, 1)` / `b.turnlog_post(side, cid, 1)` | has this card activated this turn? / mark it as activated (once per turn) |
| `b.insn("LDRB", "R0, [R4, #0x2]")` | any single Thumb-1 instruction, as text |
| `b.bl(0x021F06E8)` | a raw `bl` |
| `b.raw(0x46C0)` | a raw halfword (an instruction the encoder lacks) |

**Resolver: "Draw 2 cards."**

```python
from otn_enhanced.asm.effect_builder import EffectBuilder, R0, R2, R4

def resolver(addr):
    b = EffectBuilder()
    b.prologue(save=[R4])
    side = b.ctx_field("controller", dest=R4)
    b.call("draw", side, 2)
    b.epilogue(ret=0)
    return b.assemble(addr)       # pass the address the stub will live at
```

which assembles to:

```
PUSH {R4, LR}
LDRB R4, [R0, #0x2]     ; controller
ADD  R0, R4, #0x0       ; arg0 = side
MOV  R1, #0x2           ; arg1 = 2
BL   0x021D12F4         ; draw
MOV  R0, #0x0
POP  {R4, PC}
```

**Condition: "once per turn".** Refuse if this card already activated this turn, otherwise hand over to the
engine's normal check:

```python
def condition(addr):
    b = EffectBuilder()
    b.prologue(save=[R4])
    b.insn("ADD", "R4, R0, #0x0")                # keep the context in R4
    b.ctx_field("cost_ran", dest=R0, ctx=R4)
    b.if_ne(R0, 0, "chain")                      # re-check during activation: don't re-query
    b.ctx_field("controller", dest=R0, ctx=R4)
    b.ctx_field("cid", dest=R2, ctx=R4)
    b.turnlog_query(R0, R2, 1)
    b.if_eq(R0, 0, "chain")                      # not used yet this turn
    b.insn("MOV", "R0, #0x0")                    # used: cannot activate
    b.insn("POP", "{R4, PC}")
    b.label("chain")
    b.insn("ADD", "R0, R4, #0x0")
    b.bl(0x021F06E8)                             # the engine's generic "can activate" gate
    b.insn("POP", "{R4, PC}")
    return b.assemble(addr)
```

The matching **cost** stamps the turn log (`turnlog_post(side, cid, 1)`), then `bl`s the native cost routine
(`0x021E50CC` = "Tribute this card"). The full working set of three is `_resolver` / `_condition` / `_cost` in
`otn_enhanced/dsl.py`.

### Check it

```python
from otn_enhanced.asm.effect_verify import assert_thumb1_only
from otn_enhanced.asm.thumb_disasm import decode_thumb

blob = resolver(SLOT)
assert len(blob) <= RESERVED_BYTES
assert_thumb1_only(blob, SLOT)      # NOT a capstone disasm: capstone accepts Thumb-2 silently
for i in decode_thumb(blob, SLOT):
    print(hex(i.addr), i.mnemonic, i.operands)   # check every BL lands where you meant
```

Run this from the repo root with `uv run python`.

### Put it in the ROM

Wrap your stubs in a spec class. `dsl.make` writes the stubs to their slots, inserts the row
count-neutrally (spending a phantom cid), writes the text/stats and gives you `main` / `verify`:

```python
from dataclasses import dataclass
from otn_enhanced import dsl
from otn_enhanced.dsl import Compiled, Row, CLS3, card_props
from otn_enhanced.effects import cave3

RES, COND, COST = cave3.CAVE3_MYCARD_RES, cave3.CAVE3_MYCARD_COND, cave3.CAVE3_MYCARD_COST   # step 5

@dataclass(frozen=True)
class my_card:
    cid: int
    def compile(self, view=None) -> Compiled:
        stubs = ((RES, resolver(RES), "resolver"), (COND, condition(COND), "condition"), (COST, cost(COST), "cost"))
        for addr, blob, _ in stubs:
            assert_thumb1_only(blob, addr)
        row = Row(CLS3, (self.cid, RES | 1, 0, COND | 1, COST | 1, 0), phantom=0x1436)
        return Compiled(stubs, (row,))

main, verify = dsl.make(my_card(0x13B8), card_props("LIGHT", "Spellcaster", level=1, atk=0, defense=0),
                        out="data/over_the_nexus/working/rom_mycard.nds")
```

The table row points at `addr | 1`: the Thumb bit again.

### Or write it in C

A resolver can be C instead: `effect=c_source("otn_enhanced/cards/c/mycard.c", size)` in `ignition(...)`,
compiled by the pinned GCC (`otn_enhanced/asm/cc.py`). See `otn_enhanced/cards/c/` for examples.

### When there is no table row for your timing

Some effects can't be reached through a row at all (hand Special Summons, "when another card is summoned").
Then you hook a shared engine routine with a trampoline:
[trampolines](../tutorials/trampolines/HOWTO.md), [shared-hooks-and-ordering](../tutorials/shared-hooks-and-ordering/HOWTO.md).
Deeper on everything above: [effect-writing](../tutorials/effect-writing/HOWTO.md).

## 4. Text, stats, art

- Name + full printed text: add the cid to `otn_enhanced/data/card_text.py` `CARD_TEXT`.
- Stats: `card_props(...)`. Art: `otn_enhanced.tools.make_card_art`.
→ [card-text-and-stats](../tutorials/card-text-and-stats/HOWTO.md), [art-tweaks](../tutorials/art-tweaks/HOWTO.md)

## 5. Claim your slots

Injected code goes in the ov5 cave (`effects/ov5_cave.py`) or the ov3 pool (`effects/cave3.py`, works in
puzzles too). Never hardcode an address:
- read the current free pointer (`CAVE_FREE` in `ov5_cave.py`), add a `CAVE_*` constant, bump it;
- add any phantom cid you consumed to `PHANTOM_CLAIMS` in `otn_enhanced/knowledge/check_allocations.py`;
- refresh the ledger:
  ```bash
  uv run python -m otn_enhanced.knowledge.check_allocations --emit
  ```
→ [caves-and-allocation](../tutorials/caves-and-allocation/HOWTO.md)

## 6. Build a single-card test ROM

Every card module runs on its own: its `main()` applies just that card on top of
`rom_ov3_compact.nds` (the stock ROM plus step 0, see [SETUP](../SETUP.md) step 5) and writes the
single-card ROM named in its `dsl.make(..., out=...)` line. Run the allocation guard first.

```bash
uv run python -m otn_enhanced.knowledge.check_allocations
```

```bash
uv run python -m otn_enhanced.cards.mycard
```

```bash
uv run python -m otn_enhanced.cards.mycard --verify
```

Do **not** add it to the full build yet.

## 7. Test

1. Optional, automatic: the CPU plays a mirror deck of it
   ([HOWTO 2](2-cpu-tournaments-and-gauntlets.md), `cardtest mirror`).
2. **Load the ROM in melonDS and play each clause.** Only this counts as working.
3. Broken? Don't guess-and-rebuild. Grab a savestate or a GDB trace (port 3333, one connection per
   session) and find where the path actually goes.
   → [debugging-in-game](../tutorials/debugging-in-game/HOWTO.md)

Write the result into the findings file: `AWAITING IN-GAME TEST` until the person testing says it passed.

## 8. Ship

Only once it's confirmed in-game and approved for shipping:
1. Add a `Step` for the module to `otn_enhanced/steps.py` `STEPS`.
2. Rebuild and run the full verify sweep — every shipped card, not just yours:
   ```bash
   uv run python -m otn_enhanced.build
   ```
   ```bash
   uv run python -m otn_enhanced.verify data/over_the_nexus/working/rom_all_patches.nds
   ```
3. Bank any engine facts you proved in `otn_enhanced/knowledge/author_facts.py`, then
   `uv run python -m otn_enhanced.knowledge.author_facts --check`.

## The classic failures

| symptom | usual cause |
|---|---|
| freeze on activation | Thumb-2 instruction, `BLX` to an even address, `POP {..,LR}` |
| effect does nothing | a per-cid gate on the donor; wrong dispatch class for the timing |
| searches the wrong place | the primitive reads a different zone than assumed |
| another card broke | duplicate cls2 record / leftmost-record shadowing / double-claimed slot |
| text truncated | donor slot too short and cid missing from `CARD_TEXT` |
