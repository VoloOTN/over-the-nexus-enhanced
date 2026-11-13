# Overlay-3 BSS cave — findings

Goal: a code cave that is resident in **every** duel mode (normal duel, puzzle,
turbo duel, tag duel, tag turbo duel), unlike the ov5 cave which is normal-duel-only.

Session: 2026-07-22.

## Confirmed (this session)

- **melonDS savestate main-RAM file offset = 0x24** for every `*.ml*` in
  `data/over_the_nexus/working/` that carries this layout (91 of 119 files).
  Verified by locating the ov3 prologue anchor `38b5012202400e480e4c5043` and
  solving for the base: the match lands at exactly **0x021A25A0**, the known
  address of the recent-summon-list lookup. The `FILE_OFF_OF_RAM0 = 0x3C` in
  `otn_enhanced/tools/savestate_diff.py.py` is **stale** for these captures.
  (28 older files use a different layout and were excluded by the anchor check.)

- **Overlay residency by mode.** Method: decompress each overlay's file image
  with ndspy and compute the fraction of bytes matching RAM at its load address.

  | overlay | ml1 duel | ml2 puzzle | ml3 turbo | ml4 tag | ml5 |
  |---|---|---|---|---|---|
  | ov3 @0x02141700 | 100% | **100%** | 100% | 100% | 100% |
  | ov5 @0x022C5900 | 100% | **3.5%** | 100% | 100% | 100% |
  | ov41 @0x022C5900 | 2.9% | **100%** | 2.9% | 2.9% | 2.9% |
  | other 47 overlays | ~8% | ~8% | ~8% | ~8% | ~8% (noise floor) |

  So: **ov5 is duel-only (confirmed, evicted by ov41 in puzzles)**, and
  **ov3 is resident in ALL five modes including puzzles**. ov3 is the only
  overlay co-resident everywhere → the only viable host for mode-independent code.

- **ov3 geometry** (EU `rom.nds`): load 0x02141700, data 0x152CE0 → data end
  **0x022943E0**, bss 0x31520 → footprint end **0x022C5900** (== ov5/ov41 base).
  Compressed (flags 0x01), stored 0xEA4F4 bytes (69.2% of decompressed).

- **Two candidate windows in ov3's BSS tail** — each satisfies BOTH independent tests:

  | window | range | size | nonzero bytes across 92 savestates | code pointers into it |
  |---|---|---|---|---|
  | PRIMARY | 0x022B9000–0x022C2000 | 36.0 KB | **0** | **0** |
  | SECONDARY | 0x022A7000–0x022ACC00 | 23.0 KB | **0** | **0** |

  - *Never-written test*: accumulated the nonzero mask over all 92 layout-matching
    savestates (all ROM variants, all five modes). Longest never-written runs
    anywhere in ov3 BSS: `0x022B8ABD–0x022C293C` (39.6 KB) and
    `0x022A6FA9–0x022ACC4C` (23.2 KB). The windows above are aligned subsets.
  - *Reference test*: scanned every 4-byte-aligned word of the ARM9 (all 3
    sections) and all 50 overlays for values landing inside ov3's BSS. 264
    distinct referenced addresses; largest unreferenced gaps
    `0x022B4018–0x022C33AC` (60.9 KB) and `0x022A449B–0x022B22FF` (55.6 KB).
    Both never-written runs sit inside unreferenced gaps.

- **The resize itself is lossless and disturbs no shipped patch.** Verified on a
  *frozen* copy of `rom_all_patches.nds` (`fill_canary` applied, then compared):
  - ARM9 bytes identical; ov3's native prefix (0..0x152CE0) identical; **all 49
    other overlays byte-identical**.
  - `verify()` run for all 18 patch modules exposing one, before and after the
    resize: **0 modules changed verdict**.
  - Built geometry: size 0x152CE0 → 0x180900, bss 0x31520 → 0x3900, footprint end
    still 0x022C5900, arena-lo literal @0x51ED8 unchanged at 0x0239A120.
    Compressed cost of the 183 KB of zero padding: 0xEA4F4 → 0xEFB78 = **+22 KB**.

  ⚠️ Method note: the first attempt at this regression was **invalid** — it read
  `rom_all_patches.nds` while an `apply_all_patches` build was rewriting it
  (mtime moved 21:55 → 22:00:43, md5 changed between two runs in the same
  minute). That produced nonsense (patches "appearing" in the canary that were
  missing from the baseline, non-deterministic byte diffs at ov5 cave slots).
  **Always snapshot the ROM before an A/B**, and treat a non-deterministic diff
  as an unstable input rather than a code bug.

## Ruled Out

- **ov5 cave for puzzle-capable effects** — ml2 shows ov5 at 3.5% image match
  (i.e. gone) while ov41 is at 100% on the same address. Any effect calling an
  ov5 stub is inert in a puzzle. This is now measured, not inferred.

- **Naive "zero in ml1 and ml2" as the free-space criterion** — five states gave
  `0x022B2B2D–0x022C294C` (63.5 KB) and `0x022A5589–0x022ACC4C` (29.7 KB), but
  widening to 92 savestates showed both get written in other captures (up to 1121
  nonzero bytes in `rom_armory_arm.ml2`). The turbo duel (ml3) in particular
  sprinkles writes across the upper BSS. The 92-state intersection is the honest
  number; the 5-state one would have shipped a cave the engine reclaims.

- **0x023F89A5–0x023FF800 (27.6 KB, top of main RAM)** — never written in 92
  states, but no loader backs it (would need a boot-time copier) and the ARM9
  references 0x023FE800 inside it (`arm9@0x02086C3C`).

- **0x02131514–0x02137F0C (26.5 KB)** — never written, but it lies in the
  0x020AF120..0x02141700 main-heap gap (the ARM9 main section has **no bss**),
  i.e. it is heap, not statically owned, and no loader backs it.

## Canary round 1 — FAILED (2026-07-22)

Played `rom_ov3_canary.nds` in all five modes (`rom_ov3_canary.ml1..ml5`).
**Both windows came back 100% zero in every state** — 36864/36864 and
23552/23552 bytes, value 0x00, not a partial reclamation. Additionally there is
**no 0xA5 run longer than 16 bytes anywhere in the 4 MB of main RAM** (2420
scattered 0xA5 bytes = noise). So the 59 KB of canary never appeared in RAM.

The five states are genuine: the ov3 anchor resolves at 0x021A25A0 (duel loaded),
melonDS named them after the canary ROM, and RAM matches ov3's native image 100%.

Two hypotheses remain, and they have opposite consequences:

- **(A) The engine clears ov3's BSS itself** using its own compiled-in extent
  (which still spans the full original 0x022943E0..0x022C5900). Then the region
  is live managed memory and is unusable for code — but the loader works.
- **(B) Our grown ov3 image never reaches RAM at all** (build/loader problem).
  Then the BSS verdict is premature and says nothing about the windows.

Investigated and did NOT resolve it:
- The in-RAM overlay table is not resident (no ov3 OVT entry found in main RAM),
  so it cannot be used to tell which image booted.
- `0x022943E0` (ov3's BSS start) appears as a literal **7 times inside ov3**, but
  disassembly shows these are **ARM-mode** pools (`push`/`pop`/`ldr rX,[pc,#n]`
  around them) loading it as a *global pointer variable* — code does
  `ldr r0,[pc,#..] ; ldr r0,[r0]`. It is a handful of globals at the head of BSS,
  **not** an arena base, and not the eraser. `0x022C5900` and the bss size
  `0x31520` appear as literals **nowhere** in the ARM9 or any overlay.
- This is nonetheless the blind spot the plan predicted: ov3 addresses its BSS
  through runtime pointers, so the "0 code references" test was never capable of
  proving the windows unowned.

## Canary round 2 — RESOLVED: hypothesis (A). **The ov3 BSS cave is DEAD.**

All five modes, unanimous:

- `[PASS] CONTROL PROBE 0x0226CAA0-0x0226CAE0` — 0xA5 intact → the grown ov3
  image **is** decompressed into RAM correctly. The build, the overlay-table
  edit, the recompression and the loader are all sound.
- `[FAIL] PRIMARY` and `[FAIL] SECONDARY` — 36864/36864 and 23552/23552 bytes,
  all `0x00`.

**Conclusion: the engine clears overlay 3's BSS region itself, after the loader
copies the image, over the ORIGINAL extent** — not the extent declared in the
overlay table (we set bss to `0x3900`, so the standard loader would only have
cleared `0x022C2000..0x022C5900`, well above both windows). Converting BSS to
file data therefore cannot hold anything: whatever we put there is wiped before
the first frame of a duel.

This kills the approach outright — it is NOT a "shrink the window and retry"
failure. Both windows were 100% cleared, and there is no sub-window to retreat
to. **Do not re-attempt an ov3 BSS cave without first finding and neutering the
clear.**

Still unlocated: the code performing the clear. `0x022C5900` and `0x31520`
appear as literals nowhere; the 7 occurrences of `0x022943E0` are ARM-mode
globals, not the memset. Finding it would need a GDB write-breakpoint at
`0x022B9000` across duel init (melonDS write-*watchpoints* do not fire — use a
breakpoint).

### What survives from this work

- The **residency table** stands on its own (measured, independent of the cave):
  ov3 is resident in all five modes, ov5 is evicted in puzzles. That is still a
  correction to CLAUDE.md worth landing.
- `ov3_cave.py`'s expansion mechanism is proven *mechanically* correct — it is
  lossless, footprint-stable, and the bytes demonstrably arrive in RAM. Only the
  destination is unusable.

## PIVOT: extend the ARM9 static image instead (next experiment)

The ARM9 main section is the one region that is loaded once at boot, never
evicted in any mode, and — critically — **has `bssSize == 0`**, so no BSS clear
covers it. Static evidence gathered this session:

- arm9 main section = `0x02000000..0x020AF120`, no bss; the next thing in the map
  is ov0/ov3 at `0x02141700`, leaving a **0x925E0 (600 KB) gap** that is
  currently main heap.
- That heap base is a literal, exactly like the duel arena-lo `ov5_cave.py`
  already raises (`0x51ED8` → `0x0239A120`). `0x020AF120` appears **7 times**:
  a boot memory-map table at main-section offset **0xB90/0xB94** (immediately
  followed by `0x02141700` at 0xB98 — the heap TOP), and two Thumb literal-pool
  pairs at **0xCE4/0xCE8** and **0x81558/0x8155C**.
- `0x020AF120-0x020B0AC4` (6.4 KB) is never written across all 92 savestates,
  consistent with it being the unused head of that heap.

Proposed round 3: append code to the ARM9 main section via
`ndspy.code.MainCodeFile` (the path `ov5_cave._raise_arena_lo` already uses — a
raw `codeCompression` round-trip white-screens), raise the `0x020AF120` literals
past the appended region, and canary it the same way. Thumb-1 `BL` reach is
±4 MB: `0x020AF120` → ov3's top (`0x022943E0`) is ~1.9 MB and → the ov5 caves
(`0x0239A120`) is ~3.0 MB, so both remain callable.

⚠️ Unproven: whether all 7 literals are the same allocator, and whether anything
else derives the heap base independently. Canary before trusting it.

## Canary round 2 — control probe design (kept for reference)

`NATIVE_PROBE = 0x0226CAA0-0x0226CAE0` (64 bytes) now also gets 0xA5. It sits in
a 75-byte run of zeros **inside ov3's native data image** (0x0226CA9D-0x0226CAE8)
that is zero in RAM across all five round-1 states — dead padding, carried by the
same memcpy/decompress that would carry the windows.

| probe | windows | conclusion |
|---|---|---|
| 0xA5 | 0x00 | loader fine → **the engine clears ov3's BSS**; hypothesis (A); BSS unusable as-is |
| 0x00 | 0x00 | **our ov3 image never reaches RAM**; hypothesis (B); round-1 verdict void, fix the build |

The checker now prints the probe FIRST and suppresses the "safe sub-window"
advice when the probe fails, so a (B) result cannot be misread as a real
measurement of the windows.

## Open Questions

- **Where is the ov3 BSS clear?** Not located. Needed only if we ever want the
  197 KB back; the ARM9 pivot does not depend on it.
- Are all 7 `0x020AF120` literals the same allocator, and does anything derive
  the main heap base independently (e.g. `arm9_end` computed from a module
  header rather than read from a literal)? **Round 3 must answer this before the
  raise is trusted.**
- ov3 residency in non-duel contexts (deck editor, story map, WiFi) is unmeasured.
  Not needed for card effects, but do not assume it.
- The ARM9 main section has `bssSize == 0` in `MainCodeFile`, but the ARM9 also
  has two autoload sections (`0x01FF8000` ITCM, `0x027E0000` DTCM). Confirm the
  boot loader's BSS clear (if any) covers neither the appended region.

## Round 3a — heap-base literals pinned (2026-07-27). RISK PROFILE CHANGED.

The pivot assumed the ARM9 arena-lo raise is "the same shape" as the duel
arena-lo `ov5_cave.py` raises cleanly. **It is not.** Findings:

- `0x020AF120` is the **live NitroSDK OS main-arena base**, allocated bottom-up:
  in `rom.ml1` the first ~6.5 KB above it are zero, then real allocations begin
  at `0x020B2120`. "Never written in 92 states" for the bottom slice is the same
  trap round 1 fell into — it is live heap, just not yet high-water at capture.
- The descriptor at `0x02000B80` is the SDK **module-params block** (magic
  `0xDEC08133`/`0x3381C0DE`, `[SDK+NINTENDO:DWC5.3` version string right after).
  Fields: `+8/+12` = `0x020B6760`/`0x020B6778` (autoload list ptrs),
  `+16/+20` = `0x020AF120` (arena-lo, twice), `+24` = `0x02141700` (arena-hi ==
  overlay load base), `+28` = `0x02086E2C`.
- **Its arena-lo fields are referenced NOWHERE as addresses in code** — so the
  block is consumed by the boot/autoload crt0 before game code runs, not by a
  runtime literal load. That makes it boot-critical: a wrong edit white-screens
  at startup, a far worse failure mode than a dead cave.
- Of the seven `0x020AF120` literals, **cluster 3 (`0x02081558`/`0x0208155C`) is
  a FALSE POSITIVE** — disassembly shows it is the lo/hi bound of an empty
  20-byte-record table (`subs r0,r1,r0` → `÷0x14` → walk records calling fn
  ptrs); both equal `0x020AF120` only because the table's backing store starts at
  the arena base and is empty at boot. Raising it would corrupt the table bounds.
  So the "raise all 7" plan is wrong; the authoritative `OSArenaLo` is a subset I
  have not yet closed statically.
- Dead padding *inside* the existing arm9 image (no growth, no raise): only
  **353 bytes** across 3 fragments (`0x020AD8D9`, `0x020A1E94`, `0x020AC074`),
  each dead-in-image AND never-written across 99 states. Enough for a small
  trampoline, NOT a code home.

**Consequence:** appending to the arm9 image requires raising the OS main-arena
base, which is boot-consumed and whose authoritative literal set is not yet
pinned. This is a real risk fork — surfaced to the user rather than built blind.
**User chose (2026-07-27): build the canary now, accept boot risk.**

## Round 3b — ARM9 canary BUILT (2026-07-27), awaiting play

`codeSettingsOffs = 0xB88` is the NitroSDK **ModuleParams** (nitroCode magic
`0x2106C0DE` at +0x20 confirms). Fields: `+0` autoloadListStart, `+4`
autoloadListEnd, `+8` autoloadStart, `+0x0C` **staticBssStart** (`0x020AF120`),
`+0x10` staticBssEnd (`0x02141700`), `+0x14` compressedStaticEnd. In the clean
image `staticBssStart == autoloadStart == 0x020AF120` — that invariant is the
lever.

`_build_arm9_canary.py` (N = 0x8000 = 32 KB):
- grows arm9 section[0] by N (0xA5 tail) → new static end 0x020B7120;
- **ndspy `MainCodeFile.save()` auto-relays** autoloadStart/List (+N) and
  compressedStaticEnd — verified byte-for-byte, this is the intended path;
- hand-raises the raw-byte fields ndspy leaves: `staticBssStart` (0xB94) and the
  two boot-init arena-lo copies `CE4`/`CE8` → 0x020B7120, keeping
  `bssStart == autoloadStart`;
- leaves the proven false-positive table bounds (0x81558/0x8155C) at 0x020AF120;
- control probe: 64 B at 0x020AD8E0 (dead zeros in the ORIGINAL static module,
  below bssStart, never cleared) also 0xA5.
- 15/15 static checks PASS: geometry, all ModuleParams edits, ITCM/DTCM autoloads
  byte-identical, no stray mutations, arena-hi fixed at 0x02141700.

⚠️ `save(compress=True)` is mandatory — the clean arm9 is stored compressed
(0x86E2C → 0x0B6778); an uncompressed write white-screens (per ov5_cave's note).

### The run — six states, INCLUDING a non-duel screen

The whole point of an ARM9 cave is surviving where ov3 is NOT loaded, so this
round adds a sixth state on a non-duel screen. `arm9_cave_check.py` auto-detects
RAM0 via the ov3 anchor in duels and falls back to an arm9-static signature at
0x02000004 for the non-duel state.

1. `.venv-1/Scripts/python.exe _build_arm9_canary.py`
2. Play `rom_arm9_canary.nds`, saving:
   `.ml1` normal duel, `.ml2` puzzle, `.ml3` turbo, `.ml4` tag, `.ml5` tag turbo,
   `.ml6` **a non-duel screen** (deck editor or story map — anywhere ov3 is out).
3. `.venv-1/Scripts/python.exe -m otn_enhanced.tools.arm9_cave_check`

| probe | region | verdict |
|---|---|---|
| 0xA5 | 0xA5 | **PASS** — mode-independent cave is real; promote to `ov9_cave.py`, claim slots |
| 0xA5 | wiped | region owned live from the reported offset; raise more arena-lo copies / rethink |
| 0x00 | — | grown ARM9 didn't load (boot broke); region verdict void |

⚠️ If it **white-screens / won't boot at all**: the arena-lo literal set was
wrong (most likely CE4/CE8 are not the allocator's arena-lo, or another copy
needs raising). That is itself the round-3b signal — report it; do not retry
blind.

## Round 3b-v1 — WHITE-SCREENED (2026-07-27). Root cause: arm9 recompression.

The first canary (compress=True) white-screened before the duel, with text
greyed out first. Root cause found STATICALLY (no second play session needed):

- The clean arm9 is stored **compressed**. Growing the static section forces a
  recompression, and **ndspy's own `save(compress=True)` output is not
  round-trippable** — `MainCodeFile(out).sections[0].data != the data I put in`
  (measured). The real DS BIOS backward-LZ decompressor is stricter still, so it
  produced a corrupt static module → greyed text → white screen.
- Also confirmed the address `0x020AF120` is overloaded 5 ways (static end /
  autoloadStart / staticBssStart / arena-lo / dereferenced by the boot fn at
  0x02000C7C which does `ldr r0,[CE4] ; ldr r0,[r0]`), so CE4/CE8 are autoload-
  region pointers, not plain arena-lo — but that was NOT the fault here; the
  recompression was.

**Fix (evidence-backed, not a guess): store the grown arm9 UNCOMPRESSED.**
`save(compress=False)` emits the full 0xBE778-byte image and sets
`ModuleParams.compressedStaticEnd = 0` — the NitroSDK flag telling the BIOS the
static module is not compressed, so no decompression runs. 5.6 MB ROM headroom
absorbs the larger arm9. This is the same "disable arm9 compression to allow
static expansion" technique standard in DS ROM hacking.

## Round 3b-v2 — UNCOMPRESSED canary BUILT (2026-07-27), awaiting play

`_build_arm9_canary.py` now saves `compress=False`; 18/18 static checks PASS
(incl. `compressedStaticEnd == 0`, full-image size 0xBE778, autoloads identical,
arena edits intact). Same run + checker as 3b; same PASS/FAIL/boot-broke matrix.
If THIS still white-screens, the recompression was not the only fault and the
next suspect is the CE4/CE8 raise (autoload pointers) — re-test with those left
at 0x020AF120 but bssStart still raised.

## 🔴 Round 3b-v2 — PLAYED 2026-08-03. **FREEZES ON ENTERING A DUEL.**

User-reported, first play session of the v2 (uncompressed) canary. Rebuilt
immediately before the run: `_build_arm9_canary.py` all static checks PASS
(`compressedStaticEnd == 0`, full image `0xBE778`, ITCM/DTCM autoloads
byte-identical, no stray static mutations, arena-hi still `0x02141700`).

**This is NOT the v1 failure.** v1 white-screened *before* the duel with text
greying out first — a corrupt static module from ndspy's non-round-trippable
recompression. v2 **boots and runs the menus fine** and dies specifically at
**duel entry**. So:

- storing the arm9 uncompressed **did fix the boot**, and the round-3b-v1 root
  cause (recompression) is confirmed as real and now resolved;
- the remaining fault is **at duel init**, i.e. in the path that allocates the
  arena / loads the duel overlays — the one thing the +0x8000 arena-lo raise
  actually changes.

**No savestates were captured** (the freeze precludes an in-duel state and the
run was stopped), so `arm9_cave_check.py` was never run and the region verdict
is formally void. It does not matter: a canary that cannot reach a duel is not a
usable cave regardless of whether the bytes survive.

### What this most likely means

`0x020AF120` is overloaded five ways (round 3a): static end, `autoloadStart`,
`staticBssStart`, arena-lo, and the value dereferenced by the boot function at
`0x02000C7C` (`ldr r0,[CE4] ; ldr r0,[r0]`). Round 3a already flagged that
**`CE4`/`CE8` are autoload-region pointers, not plain arena-lo** — raising them
was the acknowledged risk, and duel init is exactly where a wrongly-based arena
would first bite (it is the biggest allocation the game makes).

### Next Experiment (if this is ever resumed — it is NOT scheduled)

Bisect the two independent edits instead of retrying the pair:

1. **v3a** — `staticBssStart` raised (stops the crt0 clear), **`CE4`/`CE8` left
   at `0x020AF120`**. If this reaches a duel, `CE4`/`CE8` were the fault and the
   real arena-lo is elsewhere; the cave may still be clobbered by the allocator,
   which the checker then measures.
2. **v3b** — `CE4`/`CE8` raised, `staticBssStart` left alone. Expect the canary
   to be wiped by the crt0 clear but the game to run; that isolates which edit
   the duel-init path is sensitive to.
3. Shrink `N` from `0x8000` to something small (e.g. `0x400`) in either case — if
   the freeze is an arena-size sensitivity rather than a base-pointer error, a
   32 KB bite out of a 600 KB arena is far more likely to trip it than 1 KB.

**Verdict for now: the ARM9 main-section cave is NOT a usable host.** ov5 (normal
duels only) and the 180 B ov3 dead-code pool (`stat.phantom_arm_scratch`, all
modes) remain the available hosts. The two never-written fallbacks from round 3's
plan (`0x023F89A5-0x023FF800`, `0x02131514-0x02137F0C`, both needing a boot-time
copier) are untouched.

## Next Experiment — ROUND 3: ARM9 main-section cave

Same canary discipline as rounds 1-2; only the host changes. **Do not skip the
canary because the mechanism "should" work — round 1 also should have.**

### Step 3a — pin the heap base before touching anything

Prove the 7 literals are one allocator, statically and then live:

1. Disassemble around each of the three clusters (`0xB90`/`0xB94` in the boot
   memory-map table, and the Thumb pools at `0xCE4`/`0xCE8`, `0x81558`/`0x8155C`)
   and classify each: heap-lo vs heap-hi vs unrelated. The `0xB98` neighbour is
   `0x02141700` (= ov0/ov3 base, the heap TOP), which is what identifies the
   table as the main arena descriptor.
2. Cross-check against live RAM: in a savestate, find the allocator's current
   lo/hi and confirm they equal the literals (or a value derived from them).
3. Only literals that provably feed the main heap get raised. Any that turn out
   to be something else (e.g. a module-end marker) get left alone and recorded.

### Step 3b — build the canary

`ov9_cave.py` (new module, modelled on `ov3_cave.py`, which is mechanically
proven):

- Append `RESERVE` bytes to the ARM9 **main section** via
  `ndspy.code.MainCodeFile` — the path `ov5_cave._raise_arena_lo` already uses.
  ⚠️ A raw `ndspy.codeCompression` round-trip **white-screens**; go through
  `MainCodeFile` only.
- Raise every confirmed heap-lo literal from `0x020AF120` to
  `0x020AF120 + RESERVE`.
- Fill the appended region with `0xA5`. Keep a **control probe** in the ARM9's
  existing native data (same trick that resolved round 2) so a "nothing loaded"
  result can never be misread as "cleared".
- Static checks, mirroring `_build_ov3_canary.py`: arm9 main section grew by
  exactly `RESERVE`; every raised literal reads back correctly; **ov0/ov3 base
  `0x02141700` unchanged** (the appended region must not collide with the
  overlay load zone — `RESERVE` must stay well under `0x925E0`); the duel
  arena-lo at `0x51ED8` untouched; all overlays byte-identical.

### Step 3c — the run

Same five modes, plus **one non-duel screen** (deck editor or story map) this
time — the whole point of an ARM9 cave is that it survives everywhere, so test
somewhere ov3 is not loaded.

```
.venv-1/Scripts/python.exe _build_arm9_canary.py
# play, saving rom_arm9_canary.ml1..ml6
.venv-1/Scripts/python.exe -m otn_enhanced.tools.arm9_cave_check
```

**PASS** = probe `0xA5` **and** the appended region entirely `0xA5` in every
state. **FAIL with probe 0xA5** = something clears or allocates over it — report
the first offset, do not work around it. **FAIL with probe 0x00** = the grown
ARM9 never reached RAM; fix the build, the region verdict is void.

### Step 3d — only after a PASS

Claim slots (`CAVE9_*` + `CAVE9_FREE`), teach `check_allocations.py` to parse the
new module alongside `ov5_cave.py`, `--emit` the ledger, and add the KB facts
(`mem.arm9_cave`) as VERIFIED with the canary as proof.

### Fallback if round 3 fails

The remaining never-written candidates, both needing a boot-time copier (worse,
but not impossible): `0x023F89A5-0x023FF800` (27.6 KB top of RAM, but the ARM9
references `0x023FE800` inside it) and `0x02131514-0x02137F0C` (26.5 KB, inside
the same main-heap gap this round is trying to carve properly).


## Round 4 — re-measured 2026-09-07 (5 fresh mode savestates)

Re-ran residency on five NEW stock-ROM savestates (normal/tag/turbo/tag-turbo/
puzzle, `scratch/mode_residency.py`, all 50 overlays vs RAM). **Reproduces
round 1 exactly**: ov3 100%% in all five; ov5 100%% in four and 3.4%% in puzzle;
ov41 100%% puzzle only; ov48 100%% puzzle only. No other overlay is resident in
any duel mode. Provenance checked first (`scratch/mode_provenance.py`): all five
are stock `rom.nds` (resident ov3 differs from stock by 33 B, from
rom_all_patches by 26772).

Two facts that are NEW (not in rounds 1-3):

**1. The puzzle duel-arena base is 0x022E2858, not 0x0239A158.**
`scratch/mode_heap.py` walks every NNS heap in main RAM. Exactly three exist in
every mode: FRMH 0x020C0640, EXPH 0x020C4C78 (system), and the duel arena. The
arena base coincides with an overlay-table end address — ov5's end 0x0239A120 in
a duel, ov49's end 0x022E2820 in a puzzle. ⚠️ The DERIVATION is UNPROVEN: the
obvious reading ("max end over loaded overlays") is undercut by ov49 matching
only 2.1% of its image in the puzzle state, i.e. ov49 may not be loaded at all
there. The two base ADDRESSES are measured; the mechanism is an open question.
So in a puzzle
the entire ov5 span **including the ov5 cave at 0x0239A120+ is live allocatable
heap**, not merely un-loaded. Consequence: the arm9 arena-lo literal at
0x02051ED8 that `ov5_cave._raise_arena_lo` edits does NOT set the puzzle arena
base, and raising it can never protect the cave in a puzzle.

**2. `ov5_cave.RESERVE = 0x10000` is safe in tag / turbo / tag-turbo too.**
Duel-arena used is **33.1 KB in all four non-puzzle modes alike** (identical free
list: one block 0x3DA54 at 0x023A259C), against 215.7 KB of arena left after the
raise — 6.5x. This closes the gap `ov5_cave.py`'s own sizing comment flags
("the sample is mid-turn normal duels, not tag/turbo modes"). Still mid-turn
snapshots only; duel load/end remain unsampled.

**No new cave was built.** Round 2 already killed the ov3 BSS host (engine
clears ov3 BSS over its ORIGINAL extent, control probe PASS + both windows
wiped) and round 3b-v2 killed the ARM9 host (freeze at duel entry). The only
proven all-mode host remains ov3's INITIALISED image — the round-2 control probe
at 0x0226CAA0 held 0xA5 in all five modes, which proves ov3 image bytes survive
everywhere. Today that is `stat.phantom_arm_scratch` (~180 B of dead arms) plus
0x110 B of image zero-runs. If more all-mode space is ever needed, the cheap
direction is MORE dead-code reclamation inside ov3's image, not a new host.
