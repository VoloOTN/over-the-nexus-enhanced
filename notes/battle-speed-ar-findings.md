# AR "battle speed up" code — decode (session 2026-09-10)

## Confirmed (this session, from `data/over_the_nexus/working/rom.nds`, EU BYYP)

- The code targets **overlay 3** (0x02141700–0x022943E0), not ARM9 main.
  Both AR guard lines match the EU ov3 image byte-for-byte:
  - `[0x0214503C] == 0xE3520006` (`cmp r2,#6`)  — MATCH
  - `[0x0214603C] == 0xEB004FB6` (`bl 0x02159F1C`) — MATCH
  So it is an EU code and applies to the ROM this repo patches.

- `0x02145FC0` = the **duel per-frame tick**. Its body 0x02146014–0x02146100
  updates ~14 subsystems (each `ldr r0,<ctx literal>; bl <update>`) and is
  already a **sub-iteration loop**:
  - `0x0214600C  str r5,[r0,#0x13C]`  with r0 = `0x022943F8`  → counter := 0
  - `0x021460F0..F8` counter := counter+1  (`[0x02294534]`)
  - `0x021460FC  cmp r1, r7` / `0x02146100 ble 0x02146014` → loop while ctr <= r7
  - r7 comes from `0x02145FE4`: if `blx 0x0201757C` (Thumb getter,
    returns `[0x020B9970+0x4C]`) == 2 then `r7 = min([0x020B7C8C+0x2C], 4)`
    else **r7 = 0** (one pass = normal speed).

- Literal-pool map of the 14 update calls (proof: pool dump at 0x02146200+):
  ctx 0x022943F8/0x02295148/0x022956C4/**0x022952E4**/0x02296ED8/**0x022963F8**/
  0x02296DF8/0x022972D4/0x02297740/0x02296D78/0x0229777C/0x02298570.

- `0x020B87E4` = halfword field **+0xB58 of the global struct 0x020B7C8C**
  (0 pool refs to 0x020B87E4 itself in ARM9 or ov3; 174 refs to 0x020B7C8C).
  Semantics not yet identified.

## What the AR code does (3 edits + an 80-byte stub blob)

1. `0x021460FC : cmp r1,r7  ->  cmp r1,#4`  — forces the loop bound to 4
   regardless of r7, i.e. **5 logic passes per rendered frame = 5x duel speed**.
   This single word is the entire speedup.
2. `0x0214603C : bl 0x02159F1C -> b <stubA>` — stubA re-issues the call
   **only when `[0x02294534] == 0`** (first sub-pass), then `b 0x02146040`.
3. `0x0214604C : bl 0x0216D624 -> b <stubB>` — stubB re-issues the call when
   `halfword[0x020B87E4] == 0` **OR** `[0x02294534] == 0`, then `b 0x02146050`.
   (Both stubs are ARM, live in the AR scratchpad at 0x02000190.)

So: everything runs 5x except subsystems `0x02159F1C` (ctx 0x022952E4) and
`0x0216D624` (ctx 0x022963F8), which are throttled to once per rendered frame.

## Open Questions

- What are 0x02159F1C and 0x0216D624? (0x022963F8 is also passed to
  `0x0216E41C` right after the loop exits at 0x02146110 — likely render/UI.)
- What is `[0x020B9970+0x4C]` == 2? If it is a user-visible duel-speed option,
  NOPing the mode gate at `0x02145FE8 (bne 0x02146000)` may enable the game's
  own frameskip in normal duels — a 4-byte patch with no stub and no cave.
  Nothing writes `[0x020B7C8C+0x2C]` that a pool-adjacency scan could find.

## Next Experiment

Before building: decide the stub home. 0x02000190 is an AR-only scratchpad and
is not usable from a ROM image. `ov3_dead_blocks` (allocations.yaml) max block
is 44 B and Thumb; the ov3 cave (`ov3_cave.py`) is still **uncanaried**.
A tightened ARM stub pair using r12 as scratch is ~56 B.

STATUS: decode only. **AWAITING IN-GAME TEST** — the AR code itself has not been
run by the user in this session, and no patch has been written.

---

# Port to a ROM patch (same session, 2026-09-10)

## Confirmed (this session)

- **`[0x020B9970+0x4C]` (the mode field) == 0 in ALL 184 layout-matching
  savestates** in `data/over_the_nexus/working/`. So `blx 0x0201757C` never
  returns 2 in real play, `r7 = 0` always, and Konami's own frame-skip path
  (`min([0x020B7C8C+0x2C],4)`) is dead code. Raising the loop bound is the
  entire speedup.
- **`[0x02294534]` IS the sub-pass counter** — it reads 1 in 168 of those states
  (loop exits after one increment when r7 == 0), 0 in the rest.
- **`[0x020B87E4] == 0 in all 184 states**, so AR stub B's guard
  (`flag==0 OR ctr==0`) is always true and that throttle never skips its call.
  Dropped from the port as a no-op; see the module docstring. ⚠️ Savestates are
  captured at rest, so a flag that is only set *during* an animation would read 0
  here — this is evidence, not proof.

## Ruled Out (this session)

- **ov3 native-image zero runs as a code home.** Scan found 4 runs >= 56 B
  (0x0226C7B0, 0x0226C82C, 0x0226CAA0, 0x02294080). All four sit inside **data
  tables** (identity ramps `00 01 02 03 ...` at 0x0226C7F0/0x0226C810, byte
  tables at 0x0226C870) — they are zero-filled *rows* the engine still READS.
  "Never written across 194 savestates" does not mean dead.
- ⚠️ **`ov3_cave.NATIVE_PROBE` (0x0226CAA0-0x0226CAE0) is NOT dead**: 320
  nonzero bytes across 194 savestates. The cave note validated it against 5
  canary states only. Anyone re-running the ov3 cave canary needs a new probe.
- **ov5 cave**: hook site runs in puzzles, ov41 evicts ov5 -> freeze.
- **ov3 BSS cave**: canary FAILED (engine clears ov3 BSS).
- **ARM9 main cave**: recorded "NOT a usable host".
  => the ov3 dead-code pool is the only always-resident host left.

## Shipped code (AWAITING IN-GAME TEST)

`otn_enhanced/system/battle_speed.py`, built by
`_build_battle_speed.py [SPEED]` -> `rom_battle_speed.nds`. Three words, ov3 only:

| site | before | after |
|---|---|---|
| 0x021460FC | `cmp r1,r7`      | `cmp r1,#SPEED-1`  (5x => `E3510004`, identical to the AR word) |
| 0x0214603C | `bl 0x02159F1C`  | `b 0x021B54FC` |
| 0x021B54FC | dead-leaf bytes  | 16 B ARM stub (below) |

```
021B54FC  E510CDB0  ldr  ip, [r0, #-0xdb0]   ; ip = [0x02294534] (ctx 0x022952E4 - 0xDB0)
021B5500  E35C0000  cmp  ip, #0
021B5504  0BFE9284  bleq 0x02159f1c
021B5508  EAFE42CC  b    0x02146040
```
Verified by disassembling the BUILT ROM. escuridao's 28 B in the same block are
byte-identical after the write. `check_allocations`: no overlaps, 38 B ov3 free.
Claim registered as `(0x021B54FC, 16, "battle_speed")`.

NOT wired into `apply_all_patches` — single-card ROM only until the user approves.

## Next Experiment

Load `rom_battle_speed.nds` in melonDS, play a normal duel AND a puzzle.
Watch for: animations/prompts desyncing, the subsystem behind `bl 0x0216D624`
misbehaving (that is the dropped stub B), and whether 5x is comfortable.
Then rebuild with a higher SPEED (`_build_battle_speed.py 8`) and repeat.

## In-game test round 1 — user report 2026-09-10 (verbatim)

> "5x seems to be better. Can we speed up the animations too?"

> "8x 10x and 50x were extremely jerky and difficult to parse."

Recorded as-is. What this does and does not establish:

- **No freeze, hang or corruption was reported at ANY multiplier, 50x included.**
  The failure mode at high SPEED is perceptual (jerky / unreadable), not
  structural. That is weak positive evidence that dropping AR stub B did no
  structural harm, and that the ceiling is a frame-rate/legibility limit rather
  than an engine limit. NOT a clean bill of health: the user did not say they
  looked for corruption, only that it was hard to parse.
- **5x is the user's preferred setting** of {5, 8, 10, 50}.
- **Puzzle mode: still untested at any multiplier.**
- ⚠️ NOT established: whether 5x is artifact-free, and whether animations at 5x
  run at stock duration or are already faster-but-choppier. That question is
  open and blocks the "speed up the animations" work — see below.

STATUS: still **AWAITING IN-GAME TEST** for correctness. "Preferred" is not
"confirmed working"; no clause has been signed off.

---

# Animation skip — second AR code (user-supplied 2026-09-10)

User confirmed reading (a): at 5x, **animations play at stock duration and the
speed patch does not touch them**. So animation timing is NOT driven by the
frame-loop sub-pass count at all. The user then supplied two more AR codes; the
first is exactly this problem.

## Confirmed (this session)

- **No native animation-speed / skip option exists.** Searched every file in the
  ROM for "Animation"/"Speed"/"Skip" in ASCII and UTF-16LE: the only hits are
  card text ("Speed Spell", "Spell Speed") and asset filenames. Nothing to flip.
- **All 4 guard words of both new AR codes match this EU ROM**, so both were
  written for this build:
  `[0x02147B00]=0xE20310FF`, `[0x02148B00]=0xE59F5F34`,
  `[0x021520A8]=0xBAFFFFFA`, `[0x0215DA74]=0xE3A08001`,
  `[0x0216BBD4]=0xEA000013`, `[0x0217A27C]=0xE3A02004`.
- **0x02148B08 is an 80-case animation state machine**:
  `cmp r6,#0x4F` / `addls pc,pc,r6,lsl#2` (pc reads 0x02148B10 = table base),
  80 `b` entries ending 0x02148C4C, default at 0x02148B0C.
- **0x02148C50 is the function's own epilogue** — the two optional `[sp,#0x290]`
  callbacks then `add sp,#0x264 / mov r0,#1 / pop / bx lr`, i.e. "state done,
  return 1".
- ⚠️ **Case 79 (0x02148C4C) targets 0x02148C50 NATIVELY** (`b` offset -1). The
  engine's own encoding for "nothing to animate, report done" is precisely the
  retarget this patch performs. Found by `verify()` rejecting the first build;
  an earlier scan missed it because it did not sign-extend the branch offset.
  **Lesson: sign-extend ARM branch offsets — an unsigned read silently turns a
  backward branch into a bogus forward target.**

## Ruled Out (this session)

- Animations are **not** stepped by the 11 subsystem updates in the frame body
  (idx 0..10) — none share an ARM9-main helper, and the user's report of
  stock-duration animations under 5x settles it empirically.

## Shipped code (AWAITING IN-GAME TEST)

`otn_enhanced/system/skip_animations.py` — five HALFWORD
writes to ov3, no stub, no cave, no allocation claim:

| entry | case | before | after |
|---|---|---|---|
| 0x02148B88 | 30 | 0x0214A5C0 | 0x02148C50 |
| 0x02148B98 | 34 | 0x0214A284 | 0x02148C50 |
| 0x02148BC0 | 44 | 0x021497B0 | 0x02148C50 |
| 0x02148BF0 | 56 | 0x0214AD14 | 0x02148C50 |
| 0x02148BF4 | 57 | 0x0214ADEC | 0x02148C50 |

75 of 80 cases untouched (asserted by `verify()`), so other animations still
play. Composes with patch_battle_speed — disjoint sites, both verify on the
combined image. Built by `_build_duel_qol.py [SPEED]`.

## NOT ported yet — "Enhance Button Response" (decoded, not built)

Two independent blocks, all ov3, no stub needed:
- `0x021530AC` `mov r1,#1` -> `mov r1,#15`  (ctx 0x022952E4, stored to [r4,#0x18]
  when state == 0x36)
- `0x0215DA74` `mov r8,#1` -> `mov r8,#16`
- `0x0216CBD0` `ldrh r0,[r0,#0x50]` -> `ldrh r0,[r0,#0x54]` and
  `0x0216CBD4` `mvn r1,r2` -> `b 0x0216CBE8`, which skips the
  `(~held) & (held ^ prev)` edge-detect on the input struct **0x020B878C** —
  i.e. it reads a held/repeat word instead of new-press-only.
Ask the user before building; it is a separate clause.

## Next Experiment

Test in this order, each in a normal duel AND a puzzle:
1. `rom_skip_anim.nds`     — animation skip ALONE (isolates the new variable)
2. `rom_qol_5x_anim.nds`   — 5x + animation skip (the target config)
Watch for: a summon/activation that never completes (a case whose epilogue the
engine needed to reach some other way), and whether any of the 75 untouched
animations now look out of place.

---

# THE BUSY BREAK and Konami's own duel fast-forward (2026-09-10)

Chasing "can we speed up the AI thinking step" found the real structure of this
whole subsystem, and it corrects how the shipped speed patch should be understood.

## Confirmed (this session)

### 1. The sub-pass loop BREAKS OUT whenever the duel engine is busy

```
021460CC  blx 0x0219D470        ; the duel tick
021460D0  mov r6, r0            ; r6 = "am I busy"
021460D4  bl  0x021459B0
021460D8  cmp r0, #0
021460DC  movne r0, #1
021460E0  popne {r3-r7,pc}
021460E4  cmp r6, #0
021460E8  bne 0x02146104        ; <<< BUSY -> skip the increment AND the back edge
021460EC  ldr r0, <0x022943F8>  ;      i.e. exactly ONE pass this frame
021460F0..F8  counter++
021460FC  cmp r1, r7            ; (our SPEED patch edits this word)
02146100  ble 0x02146014
```

**So `SPEED` only multiplies frames on which the duel tick reports NOT busy.**
Every frame with an animation playing or the AI thinking runs exactly one pass,
whatever SPEED says. This is the mechanism behind the user's report (a):
animations at stock duration under 5x was never a bug, it is the busy break.
It also explains the jerkiness at 8x/10x/50x: idle stretches blast past at N x
while every busy stretch stays at 1x, so the duel alternates between the two.

### 2. `[0x020B7C8C+0xF54]` is a native duel FAST-FORWARD gate, dead in retail

```
021460A8  ldr r0, <0x020B7C8C>
021460AC  ldr r0, [r0, #0xF54]
021460B0  cmp r0, #0
021460B4  beq 0x021460CC        ; gate clear -> straight to the single tick
021460B8  mov r6, #0
021460BC  blx 0x0219D470        ; 4 EXTRA duel ticks, NOT gated on busy
021460C0  add r6, r6, #1
021460C4  cmp r6, #4
021460C8  blt 0x021460BC
021460CC  blx 0x0219D470        ; the normal tick (always)
```

**`[0x020B7C8C+0xF54] == 0 in ALL 184 savestates`** -> the extra-tick loop never
runs in the retail build. Turning it on gives **5 duel ticks per pass**, and
because those 4 extra calls sit BEFORE the busy check they advance the duel tick
during animations and during AI thinking too — which SPEED cannot do.

This is Konami's own fast-forward, not an injection: it is the right lever for
both the AI step and animation duration.

### 3. Call path, resolved

`0x0219D470` (thumb, `push {r4,lr}`) reads handler table **0x0226D2B0**
(`[0]=0x0219D321`) and `blx`es it -> `0x0219D320`, the cooperative duel tick
chain from notes/dueling-ai-findings.md, whose `bl 0x021D6D34` @0x0219D388 is the
**AI turn controller**. So the AI runs inside the duel tick, and multiplying the
duel tick multiplies the AI's compute budget per rendered frame.
0x0219D320 has NO direct BL callers — it is reached only through the table, which
is why a plain call-graph walk dead-ends. Climb via the table's consumer instead.

## Ruled Out

- "The AI is unaffected by SPEED because it lives outside the frame loop" — false.
  It is inside, via 0x021460CC; it is the **busy break** that protects it.

## Next Experiment

Enable the gate (NOP the `beq` @0x021460B4) and measure the AI step. The tick
count is `cmp r6,#4` @0x021460C4, so the multiplier is (that immediate + 1).

## Shipped code (AWAITING IN-GAME TEST)

`otn_enhanced/system/duel_fastforward.py` — 1-2 words, ov3:

| site | before | after |
|---|---|---|
| 0x021460B4 | `beq 0x021460CC` | `nop` (gate forced open) |
| 0x021460C4 | `cmp r6,#4` | `cmp r6,#TICKS-1` (only if TICKS != 5) |

`verify()` re-asserts all 10 words of the protected block, because opening a gate
onto edited code would be worse than leaving it shut.

Built by `_build_duel_qol.py [SPEED] [TICKS]`:

| ROM | contents | sha256 (head) |
|---|---|---|
| rom_skip_anim.nds | animation skip only | e4c8a4eb7c19327f |
| rom_duel_ff.nds | fast-forward only | 61594df7fae8e6e1 |
| rom_qol_5x_anim.nds | 5x + animation skip | 4106a569b647a3bd |
| rom_qol_all.nds | ff + 5x + animation skip | 8aabb9b6df3d98e5 |

All three modules verify on every combined image. None wired into
apply_all_patches.

⚠️ CORRECTION to this file's earlier claim "raising the loop bound is the entire
speedup": it is the entire speedup **only on idle frames**. The busy break caps
every animation/AI frame at one pass regardless of SPEED.

---

## In-game test round 2 — user report 2026-09-10 (verbatim)

> "I dont think the FF does anything. Lets try 2x + animation skip"

Recorded as-is, with the user's own hedge ("I dont think"). Read as: on
`rom_duel_ff.nds` the AI thinking pause and animation durations were unchanged;
no crash or breakage reported either.

### ⚠️ RULED OUT (pending user confirmation of the reading)

**Opening the `[0x020B7C8C+0xF54]` gate @0x021460B4 does NOT speed up the AI or
animations.** The static case for it was strong — the 4 extra `blx 0x0219D470`
calls sit before the busy check, and the tick reaches the AI controller — and it
was still wrong. Something makes those extra calls a no-op. NOT investigated:
the two-strike rule applies (see below), so the next move is measurement, not a
third guess.

Candidates for whoever picks this up, none of them tested:
- `0x0219D470` may early-return unless a scene/state field says it is its turn to
  run, making repeat calls within one frame idempotent.
- The AI controller may itself be gated on a per-rendered-frame token rather than
  per-tick, so extra ticks give it no extra budget.
- The gate field may need to be nonzero for reasons beyond this branch (other
  readers of +0xF54), so forcing only the branch is not the same as enabling the
  feature.

### Two-strike status on this subsystem

1. "Raising SPEED speeds up the duel" — falsified in part by the busy break
   (@0x021460E4/E8): SPEED only multiplies idle frames.
2. "Opening the native fast-forward gate speeds the AI" — falsified in-game.

Per CLAUDE.md and the `otn-escalate-to-measurement` rule: **stop patching this
subsystem and instrument it.** The next AI/animation timing attempt must start
from a measurement of where the wall-clock time actually goes, not another
static hypothesis.

### Next Experiment (measurement, NOT a patch)

One-shot GDB session per CLAUDE.md (connect once, arm everything, one wait
window, write results to a file):
- PC-sample during an AI turn (`ai_trace sample -n 400` already exists) and
  again during a summon animation, and compare the region histograms. That says
  where the time goes without needing any address in advance.
- Breakpoint `0x0219D470` and count hits per rendered frame on the FF build vs
  the stock build. If the count is identical, the extra `blx` calls are being
  short-circuited inside the tick and the gate is a dead end for good.

## Build round 3

| ROM | contents | sha256 (head) |
|---|---|---|
| rom_qol_2x_anim.nds | 2x sub-pass + animation skip | 6b674964063853d2 |
| rom_qol_all.nds | ff + 2x + animation skip (rebuilt at 2x) | f8736f247eb143d8 |

---

# Animation SPEED (not skip) — the cut-in player mapped, 2026-09-10

## Confirmed (this session)

- **0x02148AA4 is a duel COMMAND INTERPRETER, not an animation player.** r6 = the
  command id, args off the stack, each case starts something and returns 1. So
  patch_skip_animations neutralises five *commands*; the playing happens elsewhere.
- **The summon / card-activation animation player is the module with context
  0x0229777C**, reached from command 30:
  `0214A5D4 ldr r0,=0x0229777C ; mov r1,#4 ; bl 0x0218E2C4`.
  - `0x0218E2C4(ctx, mode, arg)` starts it: `[ctx+0xC0C] = mode`, clears
    +0xC18/+0xC1C/+0xCA8/+0xDC0, dispatches on mode 0..0x19.
  - `0x0218D324(ctx)` steps it once per frame, dispatching on `[ctx+0xC0C]`
    (0..0x17). **This is subsystem idx9 of the frame body.**
  - **+0xC0C and +0xC18 are phase indices; +0xC1C is the frame counter within the
    current phase** (`+= 1` per frame, phase advances past a threshold).

- **Full enumeration of every load of +0xC1C in 0x0218C000..0x02190000**: 8
  thresholds and 8 step sites (all `+1`).

  | threshold | value | consumed by |
  |---|---|---|
  | 0x0218FB94 | 1 | **ne** |
  | 0x0218FC40 | 16 | gt |
  | 0x0218FCAC | 16 | gt |
  | 0x0218FCD8 | 16 | **ne** |
  | 0x0218FDEC | 1 | **ne** |
  | 0x0218FE10 | 16 | gt |
  | 0x0218FEFC | 1 | **ne** |
  | 0x0218FFA8 | 16 | gt |

- **There is also a COUNTDOWN path** at 0x0218FC84:
  `ldr r0,[sb,#0xC1C] / subs r0,r0,#1 / str / moveq r0,#0x10 / streq r0,[sb,#0xC18]`
  — it advances the phase only when the counter hits **exactly 0**.

## Ruled Out

- **Scaling the counter STEP (`add #1` -> `add #N`) is unsafe.** Four thresholds
  are equality-gated and the countdown fires on exactly zero; a step of 2 jumps
  over all five and the animation stalls instead of playing faster. Making it
  safe needs 13 edits including 5 hand-reasoned equality->inequality conversions.
  Rejected in favour of scaling the durations.

## Shipped code (AWAITING IN-GAME TEST)

`otn_enhanced/system/animation_speed.py` — scales the five
`cmp <+0xC1C>, #16` phase lengths to `16 // DIVISOR`. The counter still steps by
1, so **every equality test still fires exactly**, just sooner. Five words, ov3,
no stub, no cave, no allocation claim. `verify()` asserts the countdown path and
the three `cmp #1` thresholds are untouched.

⚠️ SCOPE: this is the summon/activation cut-in module ONLY. Card movement,
attacks and damage-step animations are other modules with their own counters.

| ROM | contents | sha256 (head) |
|---|---|---|
| rom_anim_speed_div2.nds | phases 16->8 frames | aaf841617f17336a |
| rom_anim_speed_div4.nds | phases 16->4 frames | 3c4918de6286e711 |
| rom_qol_2x_animspeed.nds | 2x sub-pass + phases 16->8 | 7140594e57173d7a |
