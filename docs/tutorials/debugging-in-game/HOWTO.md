# Finding out why an effect fails in-game

## Goal

Turn "it didn't work" into a mechanism you can fix, spending as few duels as possible. In-game testing is the
slowest loop, so reason from evidence first.

## Before you start

- Record **exactly what the tester saw**, in their words, before forming a theory. "The effect didn't fire" is
  not "it fired and was undone"; "it froze" is not "it froze on activation". If a report is ambiguous, list the
  readings consistent with it and ask which one it was.
- If the failure is subtle, **ask for a savestate** (melonDS `.ml*`). Savestate parsing is the authoritative
  read.
- Check the overlay is resident. A normal duel has overlay 3 at `0x02141700` and overlay 5 at `0x022C5900`. A
  puzzle started from the **puzzle editor** loads overlay 41 over overlay 5, so ov5 stubs are dead there. A
  puzzle reached through the game's own puzzle mode keeps ov5. Overlay 3 is resident in every mode tested.

## Steps

### 1. Savestate first (no emulator connection needed)

```
uv run python -m otn_enhanced.tools.savestate_diff before.ml1 after.ml2 [--start ADDR --size N]
uv run python -m otn_enhanced.tools.librarian_recorder state.ml1
```

Main RAM sits at a file offset that differs between melonDS versions. Auto-detect it (`librarian_recorder` finds
the native prologue of a known routine) instead of hardcoding it.

Before diagnosing from a savestate, **byte-check its stubs against the current build**. A savestate restores the
old ov5 code it was taken with.

### 2. GDB, once, with the whole experiment planned

melonDS has a GDB stub (port 3333). `tools/gdb_rsp.py` is the client.

- **The stub is one-shot.** Connect exactly once per emulator session. Repeated connect, detach or halt/continue
  polling wedges it. Fold preflight reads into the same connection.
- Plan every breakpoint first. Write **one** script that connects, arms them, waits in a single window, cleans up
  and writes its results to a **file**.
- melonDS write-watchpoints do not fire; use breakpoints.
- Finish with an RSP detach (`D`), never a bare socket close.
- Confirm the emulator is in an **active duel**, not a menu, before arming anything.

### 3. Reading a freeze

Halt the CPU and read PC, LR, SP and CPSR.

| Observation | Meaning |
|---|---|
| PC spinning near `0xFFFF0104`, CPSR mode `0x1B` | undefined instruction (Thumb-2 in a stub, or a branch into data or the wrong state) |
| PC near `0xFFFF0108` and up | data abort |
| Normal mode, valid instruction, PC equals a breakpoint you set | a stale breakpoint halted the game; it is not a crash |

### 4. Use a puzzle for repeatable edge cases

For ov3 reverse-engineering, author a puzzle with `rom/ydq_codec.py` so the board state is exact and replayable.
Record a do-nothing baseline run and subtract it; puzzle scripting adds code paths. Puzzles start with the turn
counter at 10. Confirm "never runs" claims with one normal-duel trace.

## Rules of engagement

- **Two failed in-game tests on one subsystem means instrument, not patch.** Stop writing code.
- **Two falsified hypotheses about a hook or dispatch path means stop** and find a shipped card that triggers the
  same way (grep `cards/` for the printed wording or the hook address), diff its implementation against yours and
  report the precedent before proposing anything new.
- Never propose a build-and-test cycle based on an unverified hypothesis. Show evidence that the hook site is
  reached on the target path, or say `unproven` and name the experiment.

## Check it

- You can state the mechanism in one sentence and name the address or register that proves it.
- The fix is backed by the savestate, trace or emulator result, not by a successful `verify()`.

## Pitfalls

- A decoder or simulator that agrees with your own code proves nothing about the console.
- `capstone` disassembles illegal Thumb-2 as valid. Use `asm/effect_verify.assert_thumb1_only`.
- Write any proven fact (an address, a struct offset) down the moment you prove it, including falsified
  hypotheses; a dead hypothesis stops the next session paying for the same experiment.
