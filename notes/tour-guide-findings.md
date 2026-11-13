# Tour Guide From the Underworld — migration to a records-free Normal Monster donor

Session 2026-09-10. Scope: **donor migration only.** No behaviour change intended;
the effect is already in-game confirmed on the old donor.

Printed text (`scratch/ygoprodeck_cache.json`, authoritative):

> When this card is Normal Summoned: You can Special Summon 1 Level 3 Fiend
> monster from your hand or Deck, but negate its effects, also it cannot be used
> as Synchro Material.

## Confirmed

**Crawling Dragon 0x1004 is NOT a usable donor.** `donor_scan 0x1004` →
`VERDICT: ENTANGLED`, 13 binding occurrences (ov3 `0x021D87E4/u32`; ARM9
`0x02056798`, `0x02056908`, `0x02056A1C`, `0x02056C18`, `0x02056FFC` +7 more).
Verified this session.

**Donor chosen: Rock Ogre Grotto #1 `0x0FC2`** (user-approved 2026-09-10).
EARTH / Rock / Lv3 / 800 / 1200, pack1=51. `donor_scan 0x0FC2` → `VERDICT: CLEAN`
(zero aligned u16/u32 occurrences in ov3 + ARM9). Unclaimed by any other patch
(grepped all of `finished_patches/`). Name/desc slot floors 17 B / 48 B are NOT a
constraint: `apply_stats_and_text` prefers the `card_text.CARD_TEXT` path, which
re-emits the blobs in index order.

**The old donor's cid `0x229E` IS in the code-7 (Normal Summon) membership list**
— verified this session by reading `0x0228F7AC` × `0x67` out of the stock ROM.
That confirms Tour Guide's trigger is event code 7 and that the records-free
recipe is Boggart's PART A (A1 list + A2 cls1 + A3 criteria row).

**The negate tail `0x02235604` is donor-agnostic for our donor.** It carries a
per-cid switch at `0x0223563E`–`0x02235664` on `LDRH R2,[R5,#0]` against
`{0x2019, 0x2147, 0x21FE (= 0x2147+0xB7), 0x228B}`. Neither `0x229E` nor `0x0FC2`
is a member, and both route to the **same** fall-through arm `0x02235676`
(`0x0FC2 < 0x2147` → BGT/BGE both untaken → `CMP 0x2019` untaken → `B`;
`0x229E > 0x21FE` → BGT → `CMP 0x228B` untaken → `B`). No further cid gate exists
in phases 1 and 2 (disassembled through `0x022356EE`).

**The Synchro-material predicate's deny list has FIVE keys, in TWO CHAINED PAIRS
plus one terminal.** Disassembled `0x02248508`–`0x022485AE` this session:

| key | source | card | on hit |
|-----|--------|------|--------|
| 1 | pool `0x02248560` = `0x225E` | Cherry Inmato | deny |
| 2 | `ADD R5,#0x15` @`0x0224851C` → `0x2273` | Chaos Goddess | deny |
| 3 | pool `0x02248564` = `0x237A` | Necro Linker | deny |
| 4 | `SUB R5,#0x5B` @`0x0224857A` → `0x231F` | Wiseman's Chalice | deny (walker `0x021A14E8`, r3=3) |
| 5 | pool `0x022485B0` = `0x24B5` | Vylon Element | deny **unless** `0x02023ED4(r7)` |

Each pool word has exactly **one** referencing LDR in all of overlay 3
(`0x02248508`, `0x02248530`, `0x02248590` respectively — measured by decoding the
whole overlay).

`0x02023ED4` is `has_set_code` pointer-table slot **0x56** (list `0x0209CAD6`,
19 entries) = the **"Vylon"** archetype test — i.e. key 5 encodes Vylon Element's
printed "except for the Synchro Summon of a 'Vylon' monster".

## Ruled Out

**Keeping the shipped embargo edit (key 1 + the `ADD R5,#0x15` → `SUB R5,#0x2B`
fixup) on a Normal-Monster donor.** That repair only works because
`|0x2273 − 0x229E| = 0x2B` fits an 8-bit immediate. For donor `0x0FC2` the delta
is `0x12B1`; the same applies to the key3/key4 pair (`0x135D`). There is no free
4-aligned pool word in LDR range to convert the derived instruction into a load
(the pool `0x02248550`–`0x022485B0` is dense and every word is referenced).

**Picking a donor cid near the chain instead.** `donor_scan --free` has exactly
one clean Normal Monster above `0x2000` — Gem-Knight Crystal `0x249C` — and it is
`0x229` from `0x2273` and `0x17D` from `0x231F`, both out of imm8 range (and its
name/desc slot floors are 0).

## The chosen mechanism (donor-independent, still data-only)

Spend **key 5**, the only key with no arithmetic successor:

* pool `0x022485B0`: `0x24B5` → `DONOR_CID` (4 B).
* `0x022485A6`: `BNE 0x022485AC` (`0xD101`) → `MOV R0,R0` NOP (`0x46C0`), so the
  hit falls through to `MOV R0,#0; POP` = **unconditional** deny. Needed because
  key 5's native form is conditional on the Vylon set code, and Vylon Element no
  longer owns this slot.

Keys 1–4 stay native, so **Cherry Inmato gets her embargo back** (the old build
cost her) and Chaos Goddess / Necro Linker / Wiseman's Chalice are untouched.
Net casualty is exactly one card, as before: **Vylon Element** loses her
"cannot be used as Synchro Material except for a 'Vylon' Synchro" rider.

## Open Questions

**Reported, not fixed (user decision 2026-09-10: report only).**
`patch_steam_synchron.SYNCHRON_STALE = 0x229E` drops Synchron Explorer from the
ARM9 "Synchron" set-code list `0x0209C968`, justified by "0x229E is Tour Guide
here, not a Synchron". After this migration Synchron Explorer is a real card
again and that justification is void. Measured cost is cosmetic — per
`archetype.setcode_4c_is_monster_only` the only non-criteria reader is the
deck-editor archetype filter, and Tuning `0x23A2` / Junk Speeder `0x24B3` both
gate on the Tuner bit 15 that Explorer lacks. The clean follow-up is to repoint
that drop at the inert member `0x1E4E` (Synchro Deflector, a Spell — the KB's own
"drop of last resort"). Also stale, in the same way:
`author_facts.archetype.synchron_list_is_full_and_has_a_stale_member`, whose
proof literally asserts `patch_tour_guide.DONOR_CID == 0x229E`.

## Built

`data/over_the_nexus/working/rom_tour_guide.nds`
sha256 `b0fe2f43cb1f522f079d33ffd359094e6cc8ec2e5967e29cf8c8e043fe7821ff`
(built with `--text`; `verify()` passes; `check_allocations` clean;
`verify_knowledge` 412 PASS / 0 FAIL / 38 UNVERIFIED).

Read back out of the built ROM as a cheap oracle:

* `0x0FC2` → `'Tour Guide From the Underworld'`, DARK/Fiend/Lv3/1000/600, full
  printed text.
* `0x229E` → `'Synchron Explorer'`, EARTH/Machine/Lv2/0/700 with his own native
  text — **byte-identical to stock**.

Overlay edits: `A1 c7 list dropped 0x0E7E, inserted 0x0FC2 @2 (count 103)`;
`A2 cls1 dropped 0x0E1B, inserted @56 (count 1333)`;
`A3 criteria dropped 0x0E2E, inserted @69 (count 1389)`;
`deny key 5 0x24B5 -> 0x0FC2 @0x022485B0`, `BNE->NOP @0x022485A6`.

New KB fact banked this session: `synchro.material_embargo_deny_keys` (VERIFIED,
closed structural proof) — the five-key chain and why key 5 is the only
donor-independent slot.

## IN-GAME TEST 1 — FAILED (user report 2026-09-10)

User's exact words: *"See .ml3 the monster summoned by tour guide is not negated
or is synchro embargoed."* Savestate `rom_tour_guide.ml3`, monster still on the
field.

**Measured** by `scratch/tour_guide_state.py` (savestate parse, RAM base
auto-detected at file offset 0x24). ROM identity check PASSED — live overlay-3
RAM carries this build's edits (`0x022485B0` = `0x0FC2`, `0x022485A6` = `0x46C0`),
so the state is from the right ROM.

Board:

| side | slot | cid | card | node_head | status | bit26 |
|---|---|---|---|---|---|---|
| 0 | 2 | `0x0FC2` | **Tour Guide** | 0 | `0x00410100` | 0 |
| 0 | 3 | `0x1E1C` | **Dark Resonator** | 0 | `0x00448110` | 0 |

Attached-node pool `0x0229D33C` holds **exactly one** live record:
`[1] key=0x2146 (Worm Bait) kind=0x2` — unrelated. **No node keyed `0x0FC2`
exists anywhere in the pool, and neither slot carries a node head.**

### What this establishes

* **The summon clause WORKS.** Dark Resonator is a Level 3 Fiend, i.e. the cls1
  record, the c7 membership, the criteria row and the dual-zone hand+Deck
  selector all fired correctly on a records-free donor. PART A is good.
* **The negate node was never attached.** That is a single root cause for both
  reported symptoms, because the embargo *rides* that node — the deny-key edit
  can only match a node that exists. So the PART B data patch is not implicated
  by this evidence; nothing reached it.
* This is a **regression against the old donor**, where the same negate tail was
  in-game confirmed. So the break is donor-dependent, in the path that attaches
  the node — not in the embargo.

## Ruled Out (test 1)

* "The embargo deny-key edit is wrong / spent the wrong slot." Not reachable:
  there is no node to match. The ROM identity check proves both bytes landed.
* "The state was taken on the wrong ROM." The identity check passed.
* "The selector searched the wrong zone / wrong filter." A Level 3 Fiend was
  summoned.

## Ruled Out (diagnosis after test 1) — three hypotheses, all killed by measurement

1. **"The donor needs a second criteria row."** Measured: the old donor `0x229E`
   has exactly **one** criteria row (1183) in stock, and our donor has exactly
   one (69). The two rows are byte-identical apart from the cid — same `b`
   (`0x000E`), same `h` (`0x0239A2A1`), same `fl` (`0x00000002`).
2. **"The rider is a declarative bit in the criteria word."** The 3DS ships
   Tour Guide as cid **`0x25E6`**, ONE criteria row:
   `aux=0xFFFF handler=0x004ABD50 word=0x180C0002`. Scanning all 1388 NDS
   criteria words shows bits 31:24 are the **race filter**, not a rider:
   `0x10`=Zombie (Pyramid Turtle, Mezuki, Book of Life, Il Blud…),
   `0x50`=Insect (Pinch Hopper, Gokipon, Doom Dozer…), `0x30`=Rock,
   `0x78`=Warrior, `0x90`=Spellcaster, `0x58`=Beast, `0x38`=Machine,
   **`0x18`=Fiend** (Dark Necrofear, Doom Shaman, Gaap). Cross-check:
   Rescue Cat `0x588C0002` = Beast + `op=10 level=3` = "Level 3 **or lower**
   Beast", which is its printed text. So `0x180C0002` = Fiend + Level 3 exactly
   + Monster — **purely the search filter**, no rider bits at all.
   ⚠️ **This falsifies a claim in our own patch docstring**: "negate+embargo is
   one declarative rider = param bit `0x10000000`". `0x10000000` is the Zombie
   race code. The 3DS does NOT encode the riders in the criteria word.
3. **"The row lookup fails for a records-free donor."** `0x02243FA8` (phase 0 of
   the negate tail) is just `r0 = 0x02243B9C(cid, param); if r0 < 0: return 0`.
   A/B'd through `scratch/thumbemu` over the failing savestate's real RAM
   (`scratch/tg_rowlookup_ab.py`): our donor resolves to row **69** for every
   param 0-3, exactly as `0x229E` resolves to 1183 and Boggart to 1235. The
   lookup is fine.

## Precedent (two-strike rule)

`dispatch.level_rider_key_is_a_selector`, already in the KB and shipped in
`patch_accel_synchron` clause 2, is the same bug class measured before:

> "**THE LEVEL RIDER'S KEY IS A SEMANTIC SELECTOR DRAWN FROM A HARDCODED SET,
> NOT 'the card that created the rider'.** A rider keyed by an arbitrary donor
> cid IS WRITTEN, IS LINKED, AND IS THEN SILENTLY IGNORED… the failure is
> invisible to every static check."

Its resolution was to key the rider by a cid the *reader* honours (`0x22EB`,
Egotistical Ape) rather than by the donor's. The **write** side there was
generic; only the reader dispatched on a hardcoded key set. Our situation is the
mirror image and one step worse: we patched the reader (deny key 5 → `0x0FC2`),
but the savestate proves **no node was written at all**.

## ROOT CAUSE — FOUND AND FIXED (2026-09-10, pure data)

User confirmed the old donor's negate+embargo **did** work in-game. So this was a
port failure, not a broken mechanism. `donor_scan 0x229E` classifies three tables
the port replicated and reports **three unclassified binding occurrences** it did
not — two of those are the gates.

**The rider has three independent gates.** The port satisfied only the reader.

| gate | where | what it decides |
|---|---|---|
| **WRITE** | list `0x0228F750` × `0x2E`, searched at `0x0226806E` | whether *any* node is attached |
| **KEY** | `LDRH R2,[R4,#0x12]` at `0x02268082` | generic — the summoning card's cid |
| **READ (negate)** | list `0x0226FAB4` × `0x23`, searched at `0x021EE414` | whether the node means "effects negated" |
| **READ (embargo)** | the 5 deny keys at `0x02248508`+ | whether it means "no Synchro Material" |

Write site (`0x0226806E`): binary-search the summoning cid in `0x0228F750`; on a
miss, `BEQ` past everything. On a hit, `MOV R3,#3` + `BL 0x021C479C` attaches
`{key = that cid, kind = 3}`. **No membership ⇒ no node ⇒ both riders silently
absent** — exactly the empty pool the savestate showed. Sibling list
`0x0228F708` × `0x24` attaches **kind 2** the same way (Cherry Inmato and Necro
Linker live there; Vylon Element in the kind-3 list; Wiseman's Chalice in *both*,
matching its two printed riders).

Negate reader (`0x021EE402`): walks pool `0x0229D33C`, masks kind, `CMP R1,#6 /
BCS` (family-1 range), then honours the node **only if its key is in
`0x0226FAB4`**. Same shape as `dispatch.level_rider_key_is_a_selector` — except
here the key set is a plain sorted list a donor can join.

Third occurrence `0x0226DBBC` × `0x82` (consumer `0x021AABC8` ← `0x021EFE88`) is
the **revival** list (Rekindling, Miracle's Wake, Damage Gate, Descending Lost
Star). Synchron Explorer is in it because he summons **from the GY**; Tour Guide
summons from hand/Deck, so the donor stays out — `verify()` asserts that.

### The fix: two count-neutral inserts, no code

* **A4** `0x0228F750` ← donor, drop phantom `0x0E4B` (its only one) → node written.
* **A5** `0x0226FAB4` ← donor, drop phantom `0x0E57` (its only one) → negate honoured.
* Embargo needs no list — deny key 5 already points at the donor.

**Cherry Inmato does not have to lose her embargo after all** — the offer was
appreciated but keys 1-4 stay native.

Rebuilt: `rom_tour_guide.nds` sha256
`f81b80d6770c3392c48a1e0e0087eaaa02961c386f8e34136e1b3a271e39bc92`,
`verify()` passes, `check_allocations` clean, KB 412 PASS / 0 FAIL.
**IN-GAME CONFIRMED BY USER 2026-09-10** -- "Tour Guide Works now!"

## KB regression (my error, corrected)

I inferred from test 1 that the write-side mechanism was falsified and wrote that
retraction into `synchro.material_embargo_deny_keys`. That was wrong: a failed
port falsifies the **port**, not the mechanism. The user's in-game confirmation
on `0x229E` is ground truth. Reverted, and the fact now carries the measured
mechanism plus the lesson.

## Old Open Question (RESOLVED)

* ~~**Was Tour Guide's negate+embargo EVER confirmed in-game on the old donor?**~~
  **YES — user, 2026-09-10.** The `PLAN_tour_guide_synchro_embargo.md` wording
  describing the embargo as broken predates the shipped deny-key build.
  This decides whether we are fixing a regression or finishing an unfinished
  clause, and it changes the whole approach. The module docstring asserted
  "FINAL production patch (in-game confirmed)" and claimed the `{key=0x229E,
  kind=3}` node was "live-confirmed via savestate" — but `PLAN_tour_guide_
  synchro_embargo.md` in the repo root describes the embargo as **broken** and
  the negate as the only working half. Both cannot be true. Per CLAUDE.md the
  inherited claim is **UNVERIFIED** until the user says otherwise.
* The negate tail's phase global `0x0229AB7C` reads **0** in the failing
  savestate. Our `CAVE_TG_NEGATE` stub discards the native return and always
  returns 1; if the invoker stops on 1, only phase 0 ever runs and the global
  would be left at **1**, not 0. Reading 0 is therefore consistent with
  **the tail never executing at all** on this activation — the leading
  hypothesis, deliberately NOT acted on (it would be guess #4).

## Next Experiment

In-game test on `rom_tour_guide.nds` (single-card build, **not** the chain):

1. Normal Summon Rock Ogre Grotto #1's slot — the card must read
   **Tour Guide From the Underworld**, DARK / Fiend / Lv3 / 1000 / 600, full text.
2. The prompt offers Level 3 Fiends from **hand AND Deck**, including a second
   copy of itself.
3. The summoned monster's effects are negated.
4. The summoned monster is **refused** as Synchro Material.
5. Negative control: a monster summoned some other way IS accepted as material.
6. Regression: Synchron Explorer `0x229E` is a real card again with its own name,
   art, stats and native effect.

## STATUS: DONE -- in-game confirmed by user 2026-09-10

Donor migration complete. Test 1 (same day) failed with the summon perfect and no
rider attached; the A4/A5 membership inserts fixed it and test 2 passed.

## DSL conversion (2026-10-29) -- inherited claims, UNVERIFIED (from the old module docstring, not re-proven)
- Trigger is a code-7 MEMBERSHIP list, not a flag. A4 (rider list 0x0228F750: the Special-Summon commit 0x0226806E attaches the node only for members) and A5 (negate key set 0x0226FAB4 x 0x23: reader 0x021EE402 honours only those keys) are both required; embargo depends on A4, negate on A5 (in-game test 1 failed without them).
- Donor must stay OUT of the revival list 0x0226DBBC (that is the from-GY recipe) -- still checked in DSL verify.
- Key 4 = key 3 - 0x5B, so Necro Linker 0x237A and Wiseman's Chalice 0x231F lost riders when key 3 moved; Vylon Element (key 5) keeps hers -- encoded in `cannot_be_synchro_material` docstring.
- Not carried over: old `_assert_synchron_explorer_untouched` tripwire (Explorer 0x229E cls1/criteria/c7 unchanged) and the idempotent-rerun print notes. Old file is in git history.
