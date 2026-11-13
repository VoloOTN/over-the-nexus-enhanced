# CPU duelist unlock — findings

Goal: unlock every CPU duelist from the start, as an option in
`randomiser/otn_randomiser.py`. **Mechanism in-game confirmed by user
2026-09-17** for the numeric-threshold conditions — see "IN-GAME CONFIRMED"
section near the end of this note.

## ⚠️ Correction (2026-09-17): the "event flags" conclusion was wrong

An earlier pass this session concluded duelist-unlock storage was inside the
event-flag array at `master+0x288C`. **That was an arithmetic error**: the
`0xFA` (250) constant in `event_flag_get`/`set`'s range-3 dispatch is a
**count of flag ids**, not a byte size — the array is bit-packed
(`asrs r,#3` / `ands r,#7`), so its true footprint is `ceil(250/8) = 32 BYTES`
(`0x021268F8`–`0x02126918`), not 250. The AR code's target address,
`0x02126976`, is **0x5E bytes past the real end of that array** — outside it,
not inside. The "duelist id `N` = event flag `N + 0x51A0`" formula does not
hold; **do not reuse it.** KB fact `duelist.unlock_is_event_flags` has been
corrected and demoted back to `UNVERIFIED`.

**What's still real from that detour** — `event_flag_get` (`0x0201B36C`) and
`event_flag_set`/`clear` (`0x0201B2AC`) are a genuine matched Thumb read/write
pair for the game's general event-flag system (3 ranges: `[10000,11280)`,
`[20000,20250)` at `master+0x288C`, and a 16-bit-per-entry `[0,80)` range).
Real, just not proven to be how duelists unlock.

**What `0x02126976` (`master+0x290A`) actually is remains open.** The
original AR-code-derived bit-layout evidence still stands on its own: 60 bits
set matching the CPU-duel roster exactly, a 20-bit block matching the
independently-known `0xD5-0xE8` third roster under the same `id-0x70`
indexing. That evidence doesn't depend on the event-flag theory and is
unaffected by the correction — only the *explanation* ("it's part of the
event-flag array") was wrong.

## New lead (2026-09-17): overlay 31, prompted by the user's own hypothesis

The user asked why booster-pack conditions live in overlay 1 but the
duelist-unlock check functions live in ARM9 main, and proposed that CPU
duelists likely unlock in **groups tied to story chapters** (e.g. "CPUs 1-6
unlocked by default, 7-12 by clearing chapter 2"). That prompted re-checking
callers of `event_flag_set`/`get` — the earlier caller search only checked
**Thumb `BL`** and only within **arm9 itself** (found 2, both irrelevant,
flag ids 4/8). It never checked **ARM-mode overlay code**, which reaches
these Thumb functions via the ARM `BLX(immediate)` encoding — a completely
different instruction shape a Thumb-BL scanner can't see.

Redone properly (ARM `BLX` scan across all 50 overlays):
**66 callers of `event_flag_set`, 178 of `event_flag_get`**, spread across
overlays 1/3/7/8/10/15/18/23/25/29/30/31/32/33/34/37/38 — **none in ov1 for
the write side** (ov1 only *reads* flags, for pack-shop display; consistent
with packs being derived, not stored).

**Overlay 31 (`0x0215ca40` base, 178720 B) is the standout candidate** —
over a third of all `event_flag_set` call sites. Two shapes seen there:
- Tight clusters of **sequential literal** flag ids, e.g. `0x02177fcc`:
  `0x2a6a, 0x2a6b, 0x2a6c, 0x2a6d, 0x2a6e, 0x2a6f, 0x2a70, 0x2a71, 0x2a72` —
  nine in a row, one call each. None of these literals fall in the CPU-roster
  id space checked so far.
- Many more calls where the flag id is a **runtime-computed value** (a
  register from a loop/base+offset, not a literal my backward-scan could
  resolve) — exactly the shape a "for each duelist in this chapter's unlock
  group, set their flag" loop would have. **Not yet resolved** — need to find
  the loop bounds and base-value source for these specific call sites.

## Next Experiment

Resolve ov31's computed-flag-id `event_flag_set` call sites: trace each
base register back to its source (literal, struct field, or loop induction
variable) and find the loop bounds. This is the live thread — matches the
user's "chapters unlock groups of duelists" hypothesis better than anything
found so far, and ov31 is by far the most active flag-setting overlay in the
whole ROM.

Opened 2026-08-17 while building the standalone randomiser. Everything under
Confirmed was verified in that session against
`data/over_the_nexus/working/rom.nds` (EU `BYYP`).

## Confirmed

- **`Data_arc_pac/cpuduel.pac` is not the roster data.** Parsed it: v6 format,
  **4 files only** — `background_up.5bg` (11192 B), `graph_frame.5bg` (2352 B),
  `workset.ini` (45 B) and a `makefile`. It is the CPU-duel *screen assets*, so the
  obvious first guess is dead. Verified by `pac.parse_pac` on the live ROM.

- **The game already computes "is CPU duelist *n* unlocked".** Nine booster packs
  are gated on a count of unlocked duelists, and reading those arms back out of
  overlay 1 with `pack_unlock_conditions.read_conditions()` gives the roster
  bounds and the bitfield offset each arm reads:

  | pack | need | duelist ids | bitfield offset |
  |---|---|---|---|
  | 47, 48 | 36, 48 | `0x71..0xAC` | `master + 0x2818` |
  | 52, 53 | 12, 16 | `0xD5..0xE8` | `master + 0x2818` |
  | 49, 50, 51 | 7, 12, 16 | `0x00..0x13` | `master + 0x2848` |
  | 54, 55 | 8, 9 | `0x14..0x1D` | `master + 0x2848` |

  So there are **two** unlocked-duelist bitfields, and the CPU-duel roster is
  `0x71..0xAC` — exactly **60** opponents (`0xAC - 0x71 + 1 == 60`), which matches
  the "36 / 48 CPU duelists unlocked" pack wording.

- **Absolute addresses (EU).** The master game-state block is `0x0212406C` in ARM9
  BSS (from [booster-pack-unlock-findings.md](booster-pack-unlock-findings.md),
  re-derived consistently here), so:

  - CPU-duel + third-roster unlocked bitfield: **`0x02126884`**
  - story-roster unlocked bitfield: **`0x021268B4`**

- **The per-duelist *win* records are a different array.** `master + 0x2EC + id*4`
  (solo) and `master + 0x75C + ...` (tag), read by the helpers `0x02144F08`,
  `0x02144F4C`, `0x02144FA0`, `0x02144FD0`. These record *how often you beat*
  a duelist and are not the availability gate.

- **The `master + 0x2818` pack-unlock read, disassembled directly (2026-09-17).**
  Pack 47's arm (`0x021456D0`, ARM mode) is a plain bit-count loop:
  ```
  r0 = 0; r1 = 0x71
  loop:
    r2 = r1 >> 5                       ; word index = id / 32
    r4 = master + r2*4 + 0x2000        ; ARM's 12-bit imm can't hold 0x2818, split as #0x2000 + #0x818
    r2 = [r4, #0x818]                  ; word at master + 0x2818 + word*4
    r3 = r1 & 0x1f                     ; bit index
    if (r2 >> r3) & 1: r0++
    r1++; if r1 < 0xAD: goto loop
  return r0 >= 0x24 (36)
  ```
  Confirms word-granularity (`id/32`, `id&31`), matching id range `0x71..0xAC`
  exactly (loop bound `0xAD`). This nails down that **this specific bitfield**
  is real, word-indexed, and reachable — but it's a strong hypothesis, not yet
  proven, that it's the same thing that gates the CPU-duel *menu* (see below).

- **A working "unlock everyone" AR (Action Replay DS) code exists**, supplied by
  the user, decoded 2026-09-17:

  | label | write | address | value | bits set |
  |---|---|---|---|---|
  | normal CPUs | 16-bit | `0x02126976` | `0xFFFE` | 15 |
  | normal CPUs | 32-bit | `0x02126978` | `0xFFFFFFFF` | 32 |
  | normal CPUs | 16-bit | `0x0212697C` | `0x1FFF` | 13 |
  | tag CPUs | 16-bit | `0x02126982` | `0xFFE0` | 11 |
  | tag CPUs | 16-bit | `0x02126984` | `0x01FF` | 9 |
  | turbo + tag-turbo | 32-bit | `0x02126998` | `0x3FFFFFFF` | 30 |

  "normal CPUs" sets **exactly 60 bits** (15+32+13), matching the CPU-duel
  roster count exactly. Laid out as one bit-per-id array starting at byte
  `0x02126976` = `master + 0x290A`, bit 0 = id `0x70` (left **clear** — not a
  real opponent) and bits `1..60` = ids `0x71..0xAC` (all **set**) — i.e.
  `byte_addr(id) = 0x02126976 + (id-0x70)/8`, `bit = (id-0x70) % 8`.

  "tag CPUs" sets **exactly 20 bits**, at bit offset 96-120 from the same
  base (byte `0x02126982` = `master + 0x2916`). Under the *same* `id-0x70`
  indexing that lands exactly on ids `0xD5..0xE8` — the "third roster" this
  note's Confirmed section already ties to packs 52/53. Strong convergent
  evidence for the `id-0x70` indexing being right, from two independent
  sources (an old disassembly-derived id range, and an externally-authored
  cheat code neither of us wrote).

  "turbo + tag-turbo" sets **30 bits** starting at byte `0x02126998` =
  `master + 0x292C` — **144 bits (18 bytes) past** where the tag block ends.
  Under the same `id-0x70` scheme that would be id `0x70+272 = 0x180` (384),
  which is nonsense (`otn_enhanced/docs/engine/deck_names.yaml`'s `deck_names.table_base`
  proof shows the deck-name id space tops out around `0xFC`). **This is
  almost certainly a separate, small array with its own 0-based indexing**
  (turbo-mode racer slot, not a raw duelist id) — not confirmed further.

  ⚠️ This `master + 0x290A` array is a **different address** from the
  `master + 0x2818` array the pack-47/48 arms actually read (disassembled
  above) — 242 bytes apart, not an off-by-one. Both are real (one
  disassembly-confirmed as a *reader*, one AR-code-confirmed as *something
  the game's unlock check treats as authoritative*), and reconciling them
  (same data, two views? a cache and its source? two unrelated systems that
  happen to check the same id ranges?) is unresolved — see Open Questions.

- **Exhaustive ARM-mode search for the `master + 0x290A` writer: negative.**
  Since ARM's 12-bit immediate can't encode offsets `> 0xFFF`, ANY ARM-mode
  access to `master + 0x290A` (10506) *must* split it into two constants
  (an `ADD #imm` plus a `LDR/STR #imm12` residual, or two `ADD`s). Tried,
  across **all 50 overlays + arm9**, every plausible split (`#0x2000`+resid,
  `#0x2800`+resid, `#0x2900`+resid, direct absolute-literal load of each of
  the 6 target addresses, direct absolute-literal load of each residual
  offset): **zero hits** tied to the `master` (`0x0212406C`) register. The
  one `#0x2900` add that does exist in the whole ROM (`ov8 0x02151390`,
  confirmed `r2 == master` via its literal pool) reads a *different* field
  (`master + 0x29A0`, part of an unrelated-looking checksum/anti-tamper
  routine) — not our target. **Conclusion: if a writer exists, it is Thumb
  code** (the dominant mode in this game), which can't encode a >255
  immediate in one `ADD` at all and instead loads a precomputed literal —
  a fundamentally different, much more expensive pattern to hunt for
  statically (would need full register dataflow tracking across ~400
  `master`-referencing sites, not a byte-pattern grep).

## Ruled Out

- **`cpuduel.pac` holds the roster or its unlock flags** — it contains four files,
  two of them graphics and two build leftovers. See Confirmed.
- **The win-count array at `master + 0x2EC` is the availability gate** — it is
  indexed by duelist id but holds three counters per duelist, and the pack arms
  read a *separate* bitfield at `master + 0x2818` / `+0x2848` to answer "unlocked".

## Open Questions

1. **Is `master + 0x290A` stored or derived?** AR codes only prove the address
   is *read* by whatever gates duelist availability — Action Replay reapplies
   every frame, so a working "force these bits high" code is consistent with
   either a persisted save value **or** a per-frame-recomputed cache that
   nothing else happens to overwrite differently. Not settled by the AR code
   alone (corrected 2026-09-17 — an earlier draft of this note overclaimed
   "stored" from the AR code; that inference doesn't actually follow).
2. **How do `master + 0x2818` (disassembly-confirmed reader, pack 47/48) and
   `master + 0x290A` (AR-code-confirmed, matches CPU roster bit-for-bit)
   relate?** Same data through two access paths? One a cache of the other?
   Two unrelated systems that both happen to be keyed by duelist id over the
   same ranges? Not determined.
3. **Does the CPU-duel *menu itself* read `master + 0x290A`**, or does the AR
   code work through some other indirect effect? Not confirmed — the AR code's
   *effect* (unlocks everyone) is user-reported, not something verified in
   this session's own emulator run.
4. What is the `master + 0x292C` (30-bit, "turbo + tag-turbo") array, if not
   part of the same `id - 0x70` scheme? Own small index space, unconfirmed.

## Superseded: the event-flag detour (kept for provenance, don't reuse)

Everything above this point (the `event_flag_set`/`get` catalog, the "live
GDB session" plan) turned out to be **the wrong subsystem entirely**. The
user supplied the real unlock conditions for all 60 CPU duelists (see below)
and they are NOT simple stored flags — they're a rich mix of story-chapter
clears, per-duelist win counts, playtime, win streaks, max damage, various
summon-type counters, and specific-card triggers. That rules out
`event_flag_set` as the write path (it can't represent "beat duelist X 3
times" or "666 total Synchro Summons" — those need live counters, not a
single bit) and confirms the mechanism is **derived**, evaluated fresh,
matching the already-known booster-pack precedent.

## The real unlock conditions (user-supplied, 2026-09-17)

Full list of all 60 CPU-duel roster duelists (ids `0x71-0xAC`, in roster
order) plus the separate turbo-CPU roster, each with its exact unlock
condition — story chapter clears (6 duelists per chapter, 5 chapters +
"clear story mode"), beat-a-specific-duelist-3-times (9), stat/playtime
thresholds (5: 50h/100h playtime, 50% bonuses, 10 consecutive wins, 10000
max damage), and specific summon/win triggers (10). Recorded verbatim in
this session's transcript; not reproduced here in full — ask the user or
check chat history if this note is read stand-alone. Two of the numeric
thresholds (**666**, **573**) proved distinctive enough to grep directly and
led straight to the real table (next section).

## Breakthrough: the real condition-record table, found in overlay 18

Grepped **666** (Dragunity Arma Leyvaten's Total-Summons count) and
**573** (Earthbound Immortal Aslla piscu's Special-Summon count) as raw
4-byte pool literals across arm9 + all 50 overlays. Both landed in
**overlay 18** (`0x0214C840` base, 73280 B), only 0x260 bytes apart — and
capstone can't decode anything sane at either address in ARM or Thumb mode,
confirming this is a **data table**, not code:

```
0x0215cf70: 9a020000 ffffffff 00000000 00000000   = [666, -1, 0, 0]
0x0215d1d0: 3d020000 ffffffff 00000000 00000000   = [573, -1, 0, 0]
```

Nearby entries are **`{pointer, flag_id}` pairs** referencing the event-flag
range-2 ids already cataloged (20088-20093, sequential story-ish flags):
```
0x0215d190: 10cf1502 7b4e0000  = {ptr 0x0215cf10, flag 20091}
            f0ce1502 7c4e0000  = {ptr 0x0215cef0, flag 20092}
0x0215cf58: c8cf1502 784e0000  = {ptr 0x0215cfc8, flag 20088}
```
i.e. a linked/tree structure: some leaves are a raw numeric threshold
(`{666,-1,0,0}` = "counter >= 666"), others are `{pointer, flag_id}`
("needs this story flag, AND recurse via pointer" — a prerequisite chain).
Richer than the booster-pack flat per-pack arms, matching the wider variety
of condition *types* the user's list describes.

## Evaluator chain traced (2026-09-17) — leads into UI text-formatting, not yet a clean boolean check

Found the dispatcher that reads the ov18 table: a big ARM-mode function in
ov18 starting around `0x02152E80` has **one arm per record**, each loading
its own literal pointer into the table (e.g. `0x02152f58: ldr r0,[pc,#...]`
resolves to `0x0215cc04`) then calling `blx #0x0201b400` (a **third**
sibling function right after `event_flag_set`/`get` in arm9 — not yet
examined) followed by `blx #0x020168e8` with `(record_ptr, type=4, ctx)`.

`0x020168E8` (arm9, Thumb) is **not** the boolean "is this satisfied" check
— tracing into it and its helper `0x0201686C` (which decodes the record)
leads into a **UI progress-text formatter**: calls to what look like a
string-builder (`0x02024714`/`0x02024718`) and number-to-string conversion
(`0x02089ef0`/`0x0208a024`/`0x0208a048`), i.e. this is the code that builds
the "X/Y" progress display (e.g. "Win 2/3 times") for the unlock-conditions
screen, not the underlying pass/fail test. The actual boolean evaluator is
presumably a *sibling* of this display function (same record format, no
string building) — not yet located.

**Not yet found:** the boolean evaluator itself, and the top-level
duelist-id -> record index (the ov18 dispatcher's arms are keyed by
something, but what selects "arm for duelist 0x71" hasn't been traced back
to an id parameter yet).

## Next Experiment

Two parallel threads, either productive:

1. **Find the boolean evaluator.** `0x020168E8`'s sibling (same record
   format, called for the pass/fail check rather than display text) is
   likely called from the same per-record arms in ov18's dispatcher, or from
   wherever decides "does this duelist show as unlocked" in the CPU-duel
   select menu itself (not the story chapter's own notification code this
   arm chain seems to serve). Also worth examining: `0x0201B400` (arm9), a
   third sibling of `event_flag_get`/`set` found mid-trace, not yet
   disassembled.
2. **Map more of the ov18 table by value.** 666/573 anchor two exact
   entries (Dragunity Arma Leyvaten, Aslla piscu). Search for more of the
   user's distinctive numbers (200 for Gae Bulg's Synchro-Summon count, 10
   for Gyzarus's consecutive wins, etc.) as raw pool literals in the same
   ov18 region to place more records without needing the evaluator solved
   first — cheaper than tracing code, and each placed record narrows what
   the discriminator/stride actually is.

Gae Bulg's threshold is 200 (Total Synchro Summons) — **not** 666; corrected
after an initial mis-attribution earlier in this session.

## SOLVED (2026-09-17): the full id -> condition-group table, ov18

Dumping the whole `0x0215ce00-0x0215d400` region of ov18 word-by-word found
**six clean id-lists**, each a run of consecutive duelist ids terminated by
`0xFFFFFFFF` — and they match the user's chapter groups exactly, in order:

| Address | Ids | Group |
|---|---|---|
| `0x0215d034` | `0x71-0x76` | From the Start (Moja, Cherry Inmato, Hypnocorn, Naturia Cherries, Wattmole, Tiki Curse) |
| `0x0215d018` | `0x77-0x7C` | Clear Chapter 2 |
| `0x0215d088` | `0x7D-0x82` | Clear Chapter 3 |
| `0x0215cfe0` | `0x83-0x88` | Clear Chapter 4 |
| `0x0215d050` | `0x89-0x8E` | Clear Chapter 5 |
| `0x0215cffc` | `0x8F-0x94` | Clear Story Mode |

This fixes the exact id for all 36 duelists in those 6 groups (6 ids per
group, sequential, in the same order the user listed them).

**The "beat X 3 times" group (ids `0x95-0x9D`) uses `{this_id, ref_id, 3}`
triples**, found at `0x0215d348-0x0215d3b0`. Cross-checked against the
user's list — **all 9 match exactly**:

| id | duelist | refs id | = |
|---|---|---|---|
| `0x95` | Master Hyperion | `0x76` | Tiki Curse ✓ |
| `0x96` | Power Tool Dragon | `0x7c` | Wynnda, Priestess of Gusto ✓ |
| `0x97` | Stardust Dragon/Assault Mode | `0x82` | Great Maju Garzett ✓ |
| `0x98` | Dark Simorgh | `0x88` | Vylon Omega ✓ |
| `0x99` | Thunder King Rai-Oh | `0x8e` | Gravekeeper's Visionary ✓ |
| `0x9a` | Bountiful Artemis | `0x94` | Deep Sea Diva ✓ |
| `0x9b` | Queen Angel of Roses | `0x90` | Flamvell Baby ✓ |
| `0x9c` | Meklord Emperor Granel Infinity | `0x92` | Earthbound Immortal Ccapac Apu ✓ |
| `0x9d` | Archlord Kristya | `0x9f` | Guardian Eatos ✓ |

So ids `0x9E-0xA2` are the 5-duelist stats/playtime group (`0x9E`=Evil Hero
Dark Gaia/50h, `0x9F`=Guardian Eatos/100h, `0xA0`=Thestalos/50% bonuses,
`0xA1`=Gladiator Beast Gyzarus/10 consecutive wins, `0xA2`=X-Saber Souza/
10000 max damage) — confirmed `0x9F`=Guardian Eatos independently via the
beat-3-times cross-reference above.

**Ids `0xA3-0xAC` (the 10-duelist "summon a specific card" group)**: found
**9 of 10** as `{id, card_ref}` pairs at `0x0215d294-0x0215d2d4`
(`0xa3,0xa6,0xaa,0xa4,0xa5,0xa8,0xa9,0xab,0xac` — every summon-group id
except `0xA7`). `0xA7` = **Dragunity Arma Leyvaten** is the odd one out
because its condition is a raw counter ("666 Total Summons"), not a
card-summon trigger, so it gets its own leaf record instead — found at
`0x0215cf68` as `{id=0xA7, param=0x11, threshold=666}`, confirmed exact
match against the user's list. Gae Bulg's `200` (Total Synchro Summons) is
similarly a leaf record but for a **turbo-roster** id (ids `0xbd`/`0xbe`
nearby, a different numbering space from the main 60 — not yet mapped to
the turbo roster's own id list).

**Not yet decoded:** the exact meaning of the `card_ref` values (245-253
decimal, `0xf5-0xfd`) in the summon-group pairs — presumably an index into
a separate card/cid lookup table, not a raw game cid directly. The
`0xD5-0xDA` id-list found at `0x0215d06c` (6 ids, start of the "third
roster" `0xD5-0xE8` range) is very likely the tag-roster's own "From the
Start" group, by the same pattern — consistent with, but not yet
cross-checked against, the tag-CPU conditions (not given by the user in
this session's list, which only covered the main 60 + turbo 17).

This is now solid enough to build a per-duelist condition editor for the
groups solved here (all 36 chapter-gated + all 9 beat-3-times + the 5
stats-group ids, i.e. 50 of 60 — everything except the 10-duelist summon
group's card references, which need the card-ref table decoded first).

## COMPLETE (2026-09-17): all 60 main + all 20 turbo CPU duelists mapped

**The summon-group card refs were resolved by direct correlation**, not by
finding a lookup table: the `{id, card_ref}` pairs at `0x0215d294` (9 of the
10 summon-group ids, `0xA3,0xA6,0xAA,0xA4,0xA5,0xA8,0xA9,0xAB,0xAC` with refs
`0xF5-0xFD` sequentially) line up 1:1 with the user's list once matched by
table position rather than id order:

| id | duelist | card_ref | = user's condition |
|---|---|---|---|
| `0xA3` | Infernity Doom Dragon | `0xf5` | Win with Final Countdown's effect |
| `0xA6` | Ehren, Lightsworn Monk | `0xf6` | Summon Judgment Dragon |
| `0xAA` | Blackwing - Zephyrus the Elite | `0xf7` | Summon Blackwing - Silverwind the Ascendant |
| `0xA4` | Junk Destroyer | `0xf8` | Summon Shooting Star Dragon |
| `0xA5` | Malefic Paradox Dragon | `0xf9` | Summon Malefic Paradox Dragon |
| `0xA8` | Elemental Hero The Shining | `0xfa` | Summon Vylon Omega |
| `0xA9` | Red-Eyes Darkness Metal Dragon | `0xfb` | Summon Red Nova Dragon |
| `0xAB` | Legendary Six Samurai - Shi En | `0xfc` | Summon Gladiator Beast Heraklinos |
| `0xAC` | Machina Fortress | `0xfd` | Summon Odin, Father of the Aesir |

`0xA7` (Dragunity Arma Leyvaten) is the one summon-group id with its own
leaf-style triple instead of a card_ref pair — see below.

**The turbo roster is `0xD5-0xE8` (20 ids) — and this CORRECTS the AR
code's own label.** The AR code you supplied called this block "tag CPUs";
it is not — it is the **turbo roster**, proven by exact numeric matches
against every distinctive turbo threshold in your list (Gae Bulg's 200,
Formula Synchron's 100, Aslla piscu's 573 all land exactly here, and all 4
turbo "beat 3 times" cross-references resolve perfectly). Tag duels
apparently have no dedicated roster of their own — most likely they just
pair up existing single-duel opponents (`0x71-0xAC`), consistent with there
being no separate id-list for them anywhere found in this table.

Turbo roster layout, same table, `0x0215d060-0x0215d260`:

| ids | group |
|---|---|
| `0xD5-0xDB` | From the Start (7: Aile, Dragon Manipulator, Steamroid, Psychic Commander, Naturia Dragonfly, Dokurorider, Mefist) — list only stores `0xD5-0xDA` (6); `0xDB` confirmed independently via the beat-3x cross-ref below |
| `0xDC` | Clear Chapter 4 (Delta Tri) |
| `0xDD` | Clear Chapter 5 (Vylon Sigma) |
| `0xDE` | Clear Story Mode (Ally of Justice Searcher) |
| `0xDF-0xE2` | Beat-3-times (4) |
| `0xE3-0xE8` | Stats/summon group (6) |

Turbo beat-3-times, `{id, ref, 3}` triples at `0x0215d218-0x0215d244`, all 4
confirmed exactly against the user's list:

| id | duelist | refs id | = |
|---|---|---|---|
| `0xDF` | Kasha | `0xDB` | Mefist the Infernal General ✓ |
| `0xE0` | Destiny Hero - Dasher | `0xDC` | Delta Tri ✓ |
| `0xE1` | Gaia Drake, the Universal Force | `0xDD` | Vylon Sigma ✓ |
| `0xE2` | Fossil Dyna Pachycephalo | `0xDE` | Ally of Justice Searcher ✓ |

Turbo stats group, `{id, stat_type, threshold}` triples at
`0x0215d1b0-0x0215d1d0`:

| id | duelist | stat_type | threshold | = |
|---|---|---|---|---|
| `0xE3` | Dragunity Knight - Gae Bulg | `0x16` (22) | `200` | Total Synchro Summons ✓ |
| `0xE4` | Formula Synchron | `0x1e` (30) | `100` | Total Speed Spell Activations ✓ |
| `0xE5` | Earthbound Immortal Aslla piscu | `0x13` (19) | `573` | Total Special Summons ✓ |
| `0xE6` | Judgment Dragon | — | — | Get the "Max Speed Bonus" (special trigger, no numeric record found) |
| `0xE7` | Machina Fortress | — | — | Summon Machina Force (special trigger) |
| `0xE8` | Malefic Stardust Dragon | — | — | Summon Evigishki Soul Ogre (special trigger) |

**Bonus: partial stat-type enum decoded** from the `{id, stat_type,
threshold}` triples (Leyvaten's main-roster record uses the same shape):

| stat_type | meaning |
|---|---|
| `0x11` (17) | Total Summons (Dragunity Arma Leyvaten, 666) |
| `0x13` (19) | Total Special Summons (Aslla piscu, 573) |
| `0x16` (22) | Total Synchro Summons (Gae Bulg, 200) |
| `0x1e` (30) | Total Speed Spell Activations (Formula Synchron, 100) |

## Summary: every CPU duelist id, solved

- **`0x71-0x76`** From the Start (Moja, Cherry Inmato, Hypnocorn, Naturia
  Cherries, Wattmole, Tiki Curse)
- **`0x77-0x7C`** Clear Chapter 2 (6)
- **`0x7D-0x82`** Clear Chapter 3 (6)
- **`0x83-0x88`** Clear Chapter 4 (6)
- **`0x89-0x8E`** Clear Chapter 5 (6)
- **`0x8F-0x94`** Clear Story Mode (6)
- **`0x95-0x9D`** Beat a specific earlier duelist 3 times (9, exact refs
  table above)
- **`0x9E-0xA2`** Stats/playtime (Dark Gaia/50h, Eatos/100h, Thestalos/50%
  bonuses, Gyzarus/10 consecutive wins, Souza/10000 max damage)
- **`0xA3-0xAC`** Summon or win-with a specific card (10, exact card-ref
  table above; `0xA7` is a raw counter instead)
- **`0xD5-0xDB`** Turbo: From the Start (7)
- **`0xDC-0xDE`** Turbo: Chapter 4 / Chapter 5 / Story Mode (1 each)
- **`0xDF-0xE2`** Turbo: Beat a specific earlier duelist 3 times (4)
- **`0xE3-0xE8`** Turbo: Stats/summon group (6)

All 80 CPU-duel roster ids (60 main + 20 turbo) now have a known unlock
condition, cross-verified against the user's real in-game knowledge at
every point that admitted a check (id-list membership, beat-3x references,
and 4 distinct numeric thresholds — zero mismatches).

**Still open, lower priority:** the exact byte offset/stride that lets code
select "which record for duelist id X" in one step (the dispatcher found
earlier uses one hardcoded literal per arm — id-list scans still needed to
turn "id" into "which arm" for an automated tool); the boolean pass/fail
evaluator (only the UI-text-formatting sibling was traced); and the tag-duel
question (does tag mode really reuse `0x71-0xAC` pairs, unconfirmed).

## SOLVED (2026-09-17): tag-turbo is `0xE9-0xFC`, ten 2-duelist teams

The mysterious `0xE9-0xFC` block (20 ids I'd initially lumped in with
"turbo") is actually **ten tag-turbo TEAMS, each two adjacent ids**, found
by systematically scanning ov18 for every `u32` word packing two adjacent
u16 ids (44 candidates ROM-wide; 10 of them cluster in `0xE9-0xFC`). The
user supplied the real team names and unlock conditions from GameFAQs-style
data, which cross-verified every pairing found:

- **The base 5 pairs `(0xE9,0xEA)` through `(0xF1,0xF2)`** are a plain
  id-list (no per-pair value, terminated by `-1`, at `0x0215cfc8`) — these
  are the **default/story-unlocked** teams (per the user's source: "ones
  unlocked in story are not added" to the Free Duel unlock list). Their own
  team names are text-ids **4783-4787**, in list order:

  | pair | members | team name |
  |---|---|---|
  | `0xE9,0xEA` | Let's Go Cycling! / Monster School | Riding Cycles |
  | `0xEB,0xEC` | Mach Quacker / Highway Sprinter | Sonic Sprint |
  | `0xED,0xEE` | Rush! Charge! Blitz! / Bull Fighter! | Sort of Wild Charge |
  | `0xEF,0xF0` | Gila Monster / Hamster Strike! | Food Chain Friends |
  | `0xF1,0xF2` | Wave Runner / Shark Attack | Down to the Sea |

- **Three more pairs (`0xF3-0xF8`) unlock by beating one of the above 3
  times**, found as `{pair, ref_pair, 3}` triples at `0x0215d150` — the
  `ref_pair` is a literal 2nd copy of one of the base-5 pairs above, and all
  three cross-check exactly against the user's conditions:

  | pair | unlocked team | beats (3x) |
  |---|---|---|
  | `0xF3,0xF4` | We're on a Mission (4788) | `0xEB,0xEC` = Sonic Sprint ✓ |
  | `0xF5,0xF6` | Underworld Cops (4789) | `0xEF,0xF0` = Food Chain Friends ✓ |
  | `0xF7,0xF8` | Unified in Darkness (4790) | `0xF1,0xF2` = Down to the Sea ✓ |

- **The last two pairs (`0xF9-0xFC`) unlock via a summon condition**, found
  as `{pair, card_ref}` at `0x0215cf80` (`card_ref` 262/263, continuing the
  same small-index space as the main roster's summon-group `card_ref`s
  245-253):

  | pair | unlocked team | members | condition |
  |---|---|---|---|
  | `0xF9,0xFA` | Hurricane Regiment (4791) | Mist Valley Squadron (Harpie's Pet Baby Dragon) / Blackwing Squadron (Blackwing - Zephyrus the Elite) | Summon Ultimate Axon Kicker |
  | `0xFB,0xFC` | You-Go! (4792) | Speedy Delivery / Heavy-Hitting Hero | Summon Scrap Twin Dragon |

  Confirmed in real time by the user: id `0xFA`'s deck name in this
  tag-turbo context is "Blackwing Squadron" (not "Blackwing Elite", its
  solo/main-roster deck name at `0xAA`) — **the same underlying duelist
  (Zephyrus) gets a different id and different deck name per game mode**,
  consistent with the main roster (`0xAA`), turbo-partner slots, and
  tag-turbo slots all being separate id ranges for the same character.

**Net result: every AR-code block is now fully explained.**
`master+0x2976` (60 bits) = main roster `0x71-0xAC`. `master+0x2982`
(20 bits, AR-mislabeled "tag") = turbo roster `0xD5-0xE8`. The AR code never
covered `0xE9-0xFC` (tag-turbo teams) at all — the 30-bit third block
(`master+0x2998`) remains a separate, still-unexplained mystery (see
earlier section; exhaustive static tracing found no access code for it),
but it is NOT needed to answer "what are all the CPU duelists and how do
they unlock" — that question is now completely answered for all 90 ids
(60 main + 20 turbo + 10 tag-turbo teams × 2 members).

## IN-GAME CONFIRMED by user 2026-09-17

`duelist_unlock_conditions.py` built a ROM with all 26 threshold-based
condition records zeroed (`BeatDuelist`/`StatThreshold`/`RawValue`/
`BeatDuelistPair` — count/value fields only, `ref_id`/`stat_type` fields
left untouched). User's exact words: *"Okay that worked I see all 15 of
the Normal CPU duelists when starting a new game (I havent unlocked the
ability to Turbo, Tag or Tag Turbo duel yet"*, confirmed as read after I
restated the interpretation (per `CLAUDE.md`'s reporting protocol): on a
**fresh save**, the Normal CPU-duel select screen shows **exactly the 15
zeroed main-roster duelists** (the 9 beat-3x + 5 stats/playtime + Leyvaten)
as available, and correctly does **not** show the other 45 main-roster
duelists (chapter/story-gated, summon-gated) which were left untouched.

**What this proves:** the record-editing mechanism itself — zeroing a
`count`/`value` field in this ov18 table makes that duelist immediately
selectable, with no story progress needed — genuinely works, confirmed by
the user in melonDS, not just by static byte-level readback. This validates
`BeatDuelist`, `StatThreshold`, and `RawValue` as real, effective condition
types for all ids using those shapes.

**What is NOT yet confirmed:** the 8 turbo-roster and 3 tag-turbo-pair ids
also zeroed in the same build (same record shapes, so very likely to work
the same way, but not directly observed) — the Turbo/Tag/Tag-Turbo game
modes are gated by a separate, still-unidentified mode-unlock condition the
user's save hasn't reached, so those menus aren't reachable to check yet.
Also still unconfirmed: `SwapChapter` (list-membership editing) and
`SummonCard`/`SummonCardPair` (card-summon conditions) — neither was
exercised in this test.
