# Hooking a shared routine (trampolines)

## Goal

Give a card an effect when no table row can express it, by intercepting a routine the engine runs for *every*
card and branching on the donor's cid.

## Before you start

- You have tried [effect-insertion](../effect-insertion/HOWTO.md) and the effect needs something a table row
  cannot carry: an offer or eligibility test on a card with no rows, or behaviour at a chokepoint that is pure
  data lookup in the tables.
- You can run a melonDS GDB session ([debugging-in-game](../debugging-in-game/HOWTO.md)). Finding the hook site
  is the hard part, and it needs a live register.

## The method

1. **Find a shared dispatch or switch the game runs with the card's cid live in a register.** Pin the register
   with GDB. It is specific to the site and the build.
2. **Install a trampoline over a `BL` (or switch entry) at that site.** It replays the displaced instruction(s),
   then `if cid == DONOR:` computes your condition and forces the result. Every other cid falls through to the
   native behaviour untouched.
3. **Use a plain Normal Monster as the donor.** The trampoline reads nothing from the effect tables, so a
   records-free vanilla has nothing native to neuter and nothing to collide with.

Examples of the same trick: a hand-Special-Summon offer (trampoline over a `BL` in the summon-offer path, cid in
a register, force a flag bit), and an any-leave trigger (trampoline over the per-cid leave-switch entry, branch
into the gate that arms the End-Phase trigger).

## Steps

### 1. Prove the site is reached on your code path

Breakpoint the site in a duel that performs the action. If it never hits, stop. This is the check that
separates a working patch from a build-test loop.

### 2. Write the trampoline

Build it with `asm/effect_builder.EffectBuilder` (every shipped card does now; the raw `ThumbAssembler` is only for
what the builder cannot say), replay the displaced
instruction, and branch back to the instruction after the hook. Validate with `assert_thumb1_only`.

Do not give every card its own compare arm. `effects/tg_table.py` shows the shape that scales: **one shared
trampoline that looks the cid up in a list held in memory**, so adding a card appends a cid instead of
growing code.

| Function in `effects/tg_table.py` | Role |
|---|---|
| `_shared_arm_trampoline(tramp_addr, list_addr, ...)` | builds the shared trampoline for the any-leave trigger |
| `arm_tg_leave_trigger(rom, ov, cid, ...)` | installs the hook once, then appends `cid` to the list |
| `_shared_reg_invoke_trampoline` / `invoke_tg_endphase` | same idea for End-Phase registration |
| `_shared_ss_trampoline` / `register_tg_handss` | same idea for the hand-Special-Summon offer |
| `tg_handss_ok`, `tg_reg_ok`, `CAVE_TG_ARM_OK` | the `verify()` helpers: is the hook still intact and the cid listed |

Read `cards/tg_striker.py` to see a card use them.

### 3. Patch the hook site

A `BL` is 4 bytes. Re-encode it for the new target with `effects.common.thumb_bl(site, target)` or
`bl(site, target)`. Assert the **before-image** (the bytes you are replacing) so a different base ROM fails
loudly:

```python
assert view.blob(SITE, 4) == EXPECTED_BEFORE
view.write(SITE, thumb_bl(SITE, stub_addr))
```

### 4. Host the code

ov3 pool (`effects/cave3.py`) if it must work in puzzles; ov5 cave otherwise. See
[caves-and-allocation](../caves-and-allocation/HOWTO.md).

## When the site is already hooked

Several single-`BL` sites are shared modules with a cid register of **arms**: `effects/criteria_row_hook.py`,
`timing_class_hook.py`, `summon_rider_hook.py`, `c79_trigger_hook.py`, `c9_trigger_hook.py`,
`ss_commit_hook.py`, `summon_trigger_hook.py`, `deck_send_follow_hook.py`, `gy_vrow_hook.py`,
`handss_banish_cost.py`, `atktgt_gate.py`. Re-pointing the site to your own stub silently breaks every card
already using it. Add an arm to the shared module instead. See
[shared-hooks-and-ordering](../shared-hooks-and-ordering/HOWTO.md).

## Limits

- **No chokepoint, no hook.** A pure per-cid data lookup with no cid-switch exposes nothing to intercept.
- **No per-instance state.** A trampoline decides "can this cid do X". It carries no once-per-turn latch,
  targeting or embargo. Those need the turn log, the registry or attached-effect nodes.
- **Hook sites are scarce** and each arm costs a compare per cid.
- **A default-leaf hook is only reached by cids that default.** A cid with its own dedicated switch arm never
  arrives, and the hook is dead for it with no error.
- ov5 cave stubs do not run when a puzzle is started from the puzzle editor (overlay 41 replaces ov5). A puzzle
  played through the game's own puzzle mode keeps ov5.

## Check it

- A breakpoint on the hook site hits in the target scenario, and on a non-donor cid the native result is
  unchanged.
- `verify()` asserts `hook_points_at(c, view, SITE, stub)` and `cave_holds(c, host, stub_addr, blob)`.
- Run the shared hook module's check over every existing arm after adding yours.

## Pitfalls

- Do not poison the context cid (`ctx+0`) to borrow another card's behaviour. Retarget the leaf instead.
- Never assume a site is free: grep the address across `cards/` and `effects/`.
- One GDB connection per emulator session. Plan the whole experiment first.
