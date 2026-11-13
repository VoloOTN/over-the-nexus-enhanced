# Sea Lancer — live findings

> ## ✅✅ STATUS 2026-07-22: **SEA LANCER IS DONE — ALL THREE CLAUSES IN-GAME CONFIRMED.**
>
> E1 targets any number of your banished Fish / Sea Serpent / Aqua monsters and equips them;
> E2 (destroy an equipped card instead) works untouched; E3 grants a **flat +1000 ATK** while
> equipped, regardless of how many monsters are attached (user-verified 0 / 1 / 2 equips →
> 1300 / 2300 / 2300). Reskin is Lv5 WATER Beast-Warrior 1300/1000.
>
> Static state: `patch_sea_lancer.verify()` PASS, `check_allocations` clean (82 ov5 slots /
> 17 phantom claims), `verify_knowledge` **132 facts, 111 PASS, 0 FAIL**.
>
> **The once-while-face-up gate is CORRECT — no fidelity gap.** ✅ (user-observed in-game
> 2026-07-22, and structurally confirmed.) I had recorded this as a known gap ("still the
> donor's once-per-turn"); that was **wrong**. The donor's condition `0x021F2460` tests
> `0x021A10A0(side, slot) == 0xFFFF`, and that function reads the **attached-node list head**
> at `0x0229ACD2 + side*0x0B3C + slot*0x14` — i.e. off the monster's **ZONE RECORD** — then
> walks the node array at `0x0229D33C` (stride `0xA`) for a node with `[+2] & 0xF == 0xC`,
> returning `0xFFFF` when absent. The donor's cost `0x021E5060` -> `0x021C479C` attaches that
> kind-`0xC` node. Nodes hung off a zone record are destroyed when the card **leaves the
> field**, and nothing turn-scopes them — so the gate is literally "once while this card is
> face-up on the field", which is Sea Lancer's exact wording.
> (Amusingly the donor's own printed text is "Once per turn", so the ROM is slightly wrong for
> Mermaid Archer and exactly right for Sea Lancer.)
>
> **Still open:** only the card art — `0x1FFC` is not in `patch_card_art.py`, so she still
> wears Mermaid Archer's picture.
>
> The trail below is the full evidence log, including the wrong turns — read the retractions.

> ## STATUS 2026-07-21 (build session): **E1 IS BUILT — awaiting the in-game test.**
>
> `patch_sea_lancer.py` now carries E1. Static state: the patch's own `verify()` passes all
> 27 checks, `check_allocations` is clean (75 ov5 slots / 17 phantom claims), and
> `verify_knowledge` reports **127 facts, 106 PASS, 0 FAIL**.
>
> **The build is FIVE edits, not the four the plan called for, and two of the plan's
> instructions were wrong.** Both were caught by disassembly before anything was written:
>
> 1. ❌ **"Leave `+0x08` (slot2) alone — it becomes dead for E1."** It does not become dead.
>    The resolver **re-validates the recorded pick** through the slot2 single-card invoker
>    `0x0224A924(desc, side, key)` at `0x0220C03A` and aborts the whole resolution if it
>    returns 0. Worse, `0x0224A924` indexes `player + key*0x14` *itself*, before calling
>    slot2 — and an off-field pick's key is the zone code `0x0F`, ten zone-records past the
>    five monster zones. **`+0x08` must be NULLed** (which is free: the invoker's NULL default
>    is the literal 1 at `0x0224A978` = accept). This is also why every off-field card ships
>    with no slot2 — Unicorn Beacon and Release from Stone both have `+0x08 == 0`, as do 2596
>    records overall. Recorded as `dispatch.resolver_revalidates_pick_via_slot2`.
> 2. ❌ **"Resolve the pick through `0x0219CA28(side, 0x0F, index)`."** There is no index.
>    The pick descriptor stores `bit 0 = side | bits 1..4 = KEY | bits 5..13 = PACKED REF`,
>    and for an off-field pick the template writes the **zone code** into the key field (from
>    `0x0219C534`, which returns bits 1..5 of the candidate locator). A container index never
>    reaches the descriptor, so `0x0219CA28` has nothing to index with.
>    **But the packed card ref is already sitting in the descriptor** — the board recorder and
>    the off-field template derive an *identical* ref from their respective container words
>    (`bit 14 = side`, `bits 23..30 = instance index`), and accessor `0x02234964(desc, i)`
>    reads it straight back. The shipped detour uses that and skips the container lookup
>    entirely, which is both simpler and representation-independent.
>    Recorded as `dispatch.pick_halfword_layout`; the wrong prescription is retracted in place
>    inside `dispatch.pick_record_and_resolver_readback`.
>
> **The five edits as shipped** (full rationale in `patch_sea_lancer.py`'s docstring):
>
> | # | edit | where |
> |---|---|---|
> | 1 | slot5 `+0x14` `0x02234D8D` → `0x02235605` (off-field template, prompt `0x5E`) | cls3[527] |
> | 2 | slot2 `+0x08` `0x021E2071` → `0` (**required**, see above) | cls3[527] |
> | 3 | criteria row `{0x1FFC, 0xFFFF, CAVE_SL_CRIT\|1, 0x00010002}`, count-neutral | `0x022713C4` [883] |
> | 4 | ov5 criteria handler (Unicorn Beacon clone) + race list `{8,5,14,0}` | `CAVE_SL_CRIT` / `CAVE_SL_RACELIST` |
> | 5 | ov5 cid-scoped pick read-back detour over `0x0220C05C..0x0220C07E` | `CAVE_SL_PICK` |
>
> **Type is `0x8`, not Unicorn Beacon's `0xE`.** The walker's type bits decode as
> `0x1` side-flip / `0x2` both players / `0x4` Special-Summon-legality gate /
> `0x8` container-presence / `0x10` `0x02023050`. UB's `0xE` would search **both** players'
> banished zones and demand SS-legality; Sea Lancer says "**your** banished" and *equips*, so
> it takes the plain `0x8` of the add-to-hand family. Recorded as
> `dispatch.criteria_registrar_type_and_criteria_bits`, which also corrects an earlier guess:
> the double-pass is driven by the **type**'s bit 1, not the criteria word's, and the criteria
> word's bit 0 means "count only, do not record".
>
> **Phantom dropped:** `0x234F` in the new `criteria_registry` pool — a non-existent cid that
> owned **two** rows, so the drop cannot orphan a real card. Registered in `PHANTOM_CLAIMS`.
>
> **Why the insert resolves:** `0x02243B9C` runs a per-cid disambiguation switch after the
> binary search. A CFG walk tracking r0-r7 **and the `[sp]` slots** (register-only simulation
> reports the wrong leaf — `thumb-stack-based-switch-footgun`) enumerated all 22 equality
> cases and 19 tree constants; `0x1FFC` is in none of them, nor in either membership list, so
> it takes the default leaf `0x02243EEC` = "the leftmost row for this cid".
> Recorded as `dispatch.criteria_registry_lookup_default`.
>
> **NOT yet proven: the live path.** Everything above is static. The in-game test is the
> arbiter — see "Definition of done" at the very bottom. Known v1 gaps, all deliberate:
> one monster at a time; the gate is still the donor's **once per turn** rather than "once
> while face-up on the field" (slot3 untouched); and the criteria word `0x00010002` is copied
> from the 3DS build rather than derived, so it is the first suspect if the prompt misbehaves.
>
> ---
>
> ### 🔬 IN-GAME TEST 1 (2026-07-21, user) — **the SELECTION half works, the ACTION half does not**
>
> Savestates `data/over_the_nexus/working/rom_sea_lancer.ml2/.ml3/.ml4` (single-card test ROM).
> User-reported, verbatim:
>
> 1. **The prompt offers a MULTI-card selection** from the banished zone, but only one card
>    can actually be selected. (`.ml2`)
> 2. **The selected card does not move** from the banished zone to the S/T (equip) zone —
>    **but Sea Lancer still gains the ATK.** (`.ml3`)
> 3. **Flipping Sea Lancer face-down while "equipped" CRASHES the game.** (`.ml4`)
>
> **What this proves (do not re-derive):** the enumeration half is CORRECT end to end — the
> criteria row is found for `0x1FFC`, the ov5 handler runs, the race list filters the banished
> zone, the off-field picker opens over the right candidates, a pick is recorded, and the
> resolver reaches the equip call. Edits 1-4 are therefore sound, and the `0x1FFC`
> disambiguation-switch default-leaf argument held on the live path.
>
> **What is broken:** the equip ACTION. Symptoms 2 and 3 are one bug — the equip *linkage* is
> created (hence the ATK grant, which is gated on it) while the card is never *relocated* out
> of the banished array, leaving a dangling reference that the flip path dereferences.
> Symptom 1 is separate (a picker selection-count / prompt issue).
>
> **Working hypothesis (unproven):** `0x0225BDD8` — the call the donor's resolver ends on, which
> I assumed was "the equip action" purely because the board path ends there — likely expects the
> target to be **on the field** and locates it by a zone scan, so for a banished card the move
> silently no-ops while the link is still written.
>
> **Best lead for the fix:** the **Cyberdark** monsters (Horn `0x1AAE`, Edge `0x1AAF`,
> Keel `0x1AB0`) equip a monster **from the Graveyard** — an off-field LIST zone, exactly Sea
> Lancer's shape. Their resolver already solves the action half. Read it before writing
> anything. (They were ruled out as *donors* earlier only because their E2 is battle-only —
> that has no bearing on reusing their equip action.)
>
> ### ✅ ROOT CAUSE FOUND (static, this session) — the donor's resolver never moves the card
>
> **`0x0225BDD8` is NOT an equip action.** It builds a 5..9 monster-zone bitmask via
> `0x021AE58C` and posts a **UI request of kind 4** through `0x0225BD40`. The donor's resolver
> `0x0220BFFC` ends there and *never calls a card-mover at all* — which is exactly symptom 2.
> My "the resolver's equip action is already correct, keep `+0x04`" assumption was wrong; it
> was inherited from the plan and never checked against the disassembly.
>
> **The Cyberdark resolver `0x022186E4` is the correct action, and it is nearly a drop-in:**
>
> | | Cyberdark Horn/Edge/Keel | Sea Lancer (as shipped) |
> |---|---|---|
> | cls row | cls1[588..590] | cls3[527] |
> | `+0x04` resolver | **`0x022186E5`** | `0x0220BFFD` ← the bug |
> | `+0x08` / `+0x0C` / `+0x10` | **all NULL** | NULL / `0x021F2461` / `0x021E5061` |
> | `+0x14` slot5 | **`0x02235605`** | `0x02235605` ✅ already identical |
> | criteria | `0x088D0002`, handler `0x0223CBB0` → GY walker `0x0223C4E8` | `0x00010002`, ov5 handler → banished walker `0x0223C52C` |
>
> It reads its pick with **`0x02234964`** — the very accessor the shipped pick detour uses,
> confirming that half — loops over **all** recorded picks (`desc[+0x12]` count vs
> `[state+0x74]` index, so "any number" is engine-native), and moves each card with
> **`0x021C7484(side, SOURCE_ZONE, ref, side, ...)`**.
>
> **It is Graveyard-bound in exactly THREE places — all pinned:**
>
> | # | site | what it does | Sea Lancer needs |
> |---|---|---|---|
> | 1 | **`0x021A2510`** (whole fn) | ref → index within the GY; array `player+0x55C`, count `player+0x14`, stride `0x0B3C`, base `0x0229AC94` (pool `0x021A254C..0x021A2554`) | array `player+0x7B4`, count `player+0x1C` |
> | 2 | pool word **`0x022188C8` = `0x55C`** | re-reads the located entry out of the GY array to get its cid (`LDR [PC,#0xFC]` @`0x022187C8`) | `0x7B4` |
> | 3 | **`0x02218856` = `MOV R1,#0xE`** (`0x210E`) | the SOURCE ZONE code handed to the mover `0x021C7484` | `#0x0F` |
>
> `0x0E`/`0x0F` are the GY/banished codes of `ram.container_for_zone_code`, so site 3 is a
> one-halfword change and sites 1-2 are container-offset swaps.
>
> ### ✅ ROUND 2 BUILT (2026-07-21) — clone both functions, don't detour them
>
> Rather than four cid-scoped detours inside `0x022186E4` (which 4 records share), **both
> functions are lifted whole into the ov5 cave** with four constant substitutions. The natives
> are then provably untouched and no cid-scoping is needed — the clones are reachable only from
> `cls3[527]`. `lift_handler_to_builder` round-trips both byte-exactly at their original
> address, which is asserted before every relocation, so the extent detection is self-checking.
>
> | | change |
> |---|---|
> | `cls3[527] +0x04` | `0x0220BFFD` → `CAVE_SL_EQUIP\|1` (the clone) |
> | `CAVE_SL_LOCATE` (0x48 B) | `0x021A2510` clone: `ldr r4,[r2,#0x14]` → `[r2,#0x1C]`, pool `0x55C` → `0x7B4` |
> | `CAVE_SL_EQUIP` (0x1F4 B) | `0x022186E4` clone: `mov r1,#0xE` → `#0xF`, pool `0x55C` → `0x7B4`, and its `BL 0x021A2510` retargeted to `CAVE_SL_LOCATE` |
> | `CAVE_SL_PICK` | **RETIRED** — round 1's detour is removed and `0x0220C05C` restored to stock, so the 18 records sharing `0x0220BFFC` are no longer touched at all |
>
> `verify()` now runs **36 checks**, including that both clone *sources* still lift byte-exactly,
> that all three Cyberdark records still point at the native resolver, and that the locator clone
> differs from its source in **only the 2 intended sites (3 bytes)**.
> Static state: patch `verify()` PASS, `check_allocations` clean (77 ov5 slots / 17 phantoms),
> `verify_knowledge` **128 facts, 107 PASS, 0 FAIL**. Recorded as
> `dispatch.equip_from_list_zone_resolver`, whose proof also re-asserts the exhaustive scan
> (no other zone-code immediate or container offset exists in either function).
>
> ### 🔬 IN-GAME TEST 2 (2026-07-21, user) — symptoms 2 and 3 FIXED
>
> "That fixed a couple of the bugs." The card now moves out of the banished zone into the equip
> zone, and the face-down flip no longer crashes. **The Cyberdark-clone approach is confirmed
> on the live path.** One bug left: only ONE card can be equipped, but the printed text is
> "any number".
>
> ### ✅ ROUND 3 BUILT — the multi-select template
>
> Root cause: **`0x02235604` records exactly one pick.** It reads the picker result once and
> calls one recorder, so E1 could never equip more than one card regardless of the resolver.
> (The cloned equip resolver was already fine — it loops over every recorded pick.)
>
> **`0x02235700` is the multi-select twin** (Pot of Avarice, Miracle Dig, Burial from a
> Different Dimension, Psychic Path, Backup Soldier). Its prologue is a per-cid switch setting
> `r4` (count code) and `r6` (prompt id); the shared tail at `0x02235912` then computes
>
> - **max picks = `r4 - 6`**, handed to the UI via `0x0219A7F8`
> - **min required = `r4 - 6` only while `6 <= r4 <= 0x26`, else 1** — that collapse is how
>   "any number" is expressed
> - sub-step 1 passes **`r4` itself as the picker mode** to `0x0219C430`, where `0x02235604`
>   passes the constant `6` — so **mode 6 == "exactly one"**
> - sub-step 2 is a **loop** over the picks, ending in the same `0x022347B0` / `0x02234880`
>   recorders, returning 0 each time so the machine re-enters until all are recorded
>
> CFG walk of the switch (tracking `[sp]`, per `thumb-stack-based-switch-footgun`) gives the
> groups: `r4 = 8/9/0xA/0xB` = "exactly 2/3/4/5" (Fifth Hope, Pot of Avarice, Gladiator's
> Return, Behemoth); `r4 = 0x29/0x2A/0x2B/0x2C` = "min 1, max 35..38", differing only in prompt.
> **A cid with no case takes the default `r4 = 8` = "exactly 2"** — so simply repointing slot5
> at the native `0x02235700` would have capped E1 at two and fizzled on a single banished
> target.
>
> So `0x02235700` is **cloned** too, with its three prologue halfwords at `+0x06` replaced by
> `mov r4,#0x2A ; mov r6,#0x4C ; b +0x212` — bypassing the switch entirely for
> **min 1 / max 36** and Burial from a Different Dimension's prompt (the closest shipped
> analogue: banished zone, multi-target, no minimum). `CAVE_SL_SELECT`, 562 B.
>
> `verify()` is now **41 checks**; it asserts the clone differs from its source *only* in those
> three halfwords plus relocated `BL` displacements (0 stray bytes), and that the forced branch
> lands exactly on the tail. Recorded as `dispatch.multiselect_target_template`
> (KB: **129 facts, 108 PASS, 0 FAIL**; ledger 78 slots / 17 phantoms, clean).
>
> ### 🔬 IN-GAME TEST 3 — ROUND 3 **FROZE**. Two causes, both mine.
>
> User: freeze when activating with an empty banished pile (`.ml2`/`.ml3`, and it should not be
> activatable at all), and freeze with a **valid** target (`.ml4` — banished Treeborn Frog
> `0x19CB`, which *is* Aqua, so this was a genuine valid-target case).
>
> #### ❌❌ THE BIG ONE — I fabricated the prompt id, via the exact footgun the KB warns about
>
> Round 3 picked `r4 = 0x2A` / prompt `0x4C` from a **symbolic CFG walk** of `0x02235700`'s cid
> switch. That walk followed `BGT`/`BLT` edges as though they were equality cases, so it
> attributed leaves to cids that never reach them and **invented (r4, prompt) pairs that no card
> has**. The giveaway was in its own output and I did not read it: it listed a "card" `?(0x0020)`
> — a comparison constant mistaken for a cid. Burial from a Different Dimension's real prompt is
> **`0x5A`, not `0x4C`**. Shipping `0x0219A6F4(0x4C)` — an id no card uses — is the freeze.
>
> This is `thumb-stack-based-switch-footgun` verbatim: *"register-only simulation of these cid
> switches has reported the wrong leaf; measure, don't infer."* I quoted that rule in the round-1
> writeup and then broke it.
>
> **The fix is CONCRETE EXECUTION, not symbolic walking** — set `r1` to the real cid, evaluate
> the flags, take or don't take each branch. `scratch/sl_concrete.py`. Sanity-checked against
> cards whose printed text pins the count exactly: Pot of Avarice → exactly 5, Miracle Dig → 3,
> Gladiator's Return → 3, and Mermaid Archer → the default 2. Real pairs:
>
> | card | r4 | max | min | prompt |
> |---|---|---|---|---|
> | Pot of Avarice `0x196F` | `0x0B` | 5 | 5 | `0x116` |
> | Burial from a Different Dimension `0x1B1D` | `0x2A` | 36 | 1 | **`0x5A`** |
> | Psychic Path `0x2012` | `0x29` | 35 | 1 | `0x4D` |
> | **Dragunity Knight - Barcha `0x221B`** | **`0x47`** | **65** | **1** | **`0x139`** |
> | Mermaid Archer `0x1FFC` (no case → default) | `0x08` | 2 | 2 | `0x116` |
>
> #### 🎯 BARCHA IS THE EXACT ANALOGUE (the user's lead, and it is better than Burial)
>
> *"When this card is Synchro Summoned, you can select **any number** of Dragon-Type 'Dragunity'
> monsters in your Graveyard, and **equip them to this card**."* — equip-any-number from an
> off-field list zone, i.e. Sea Lancer's clause with a different zone and filter. Its record is
> `cls1[1166] = {+04 0x022186E5, +08 NULL, +0C 0x021F9B81, +10 0x021E51E5, +14 0x02235701}`:
> **the same equip resolver we already cloned AND the same multi-select template**. So round 4
> uses Barcha's `(r4 = 0x47, prompt = 0x139)` rather than anything derived.
>
> Prompt `0x139` exceeds a Thumb `MOV` imm8, so the clone's prologue is now **five** halfwords:
> `mov r4,#0x47 ; mov r6,#0x4E ; lsl r6,r6,#2 ; add r6,#1 ; b +0x212` (0x4E<<2 | 1 = 0x139,
> asserted in the patch).
>
> #### ❌ THE SECOND BUG — activatable with nothing to equip
>
> The donor's activation condition (`+0x0C`) knows nothing about the banished zone and slot2 is
> NULL, so `0x0224AD94` said "activatable" with an empty pile. The target template then found 0
> candidates and returned 1 ("step complete") **without recording a pick**, and the equip
> resolver's first phase reads pick 0 unconditionally (`0x02234964` → `0x021C4A68`) — consuming
> an uninitialised descriptor slot. Hence the freeze, and hence it must be blocked at activation.
>
> Round 4 adds **`CAVE_SL_COND`**, an ov5 slot3 shim that chains the donor's condition and then
> additionally requires `0x02243FE0(side, cid, 0x02234E78(desc)) >= 1` — the same candidate probe
> the template itself uses. Returns the donor's code unchanged when a candidate exists, 0
> otherwise.
>
> #### ⚠️ AND A REAL COMPOSITION BUG — the chain build was failing all along
>
> `apply_all_patches` aborted at step 21: *"criteria row [1241] cid = 0x2351, expected 0x234F"*.
> **`0x022713C4` is the SAME table `patch_boggart_knight.py` calls `POP_BASE`** (the "populate"
> table) — this note's "criteria registry" is an alias for it. Several shipped patches already do
> count-neutral inserts there (the T.G. cards consume `0x2346`/`0x2347`), so **row indices are not
> stable across the chain**: `0x1FFC` sorts to 883 on a clean ROM but 884 after them.
> Two fixes: the insert now **locates the insertion point and the phantom row by cid at apply
> time** instead of hardcoding indices, and the phantom is claimed in the existing
> **`populate_table`** pool rather than a new `criteria_registry` one — filing it under a fresh
> pool name had hidden it from the duplicate-claim guard entirely.
>
> ### 🔬 IN-GAME TEST 4 — round 4 still FROZE. Cause: a **silently truncated clone**.
>
> Diagnosed with **no GDB**, straight from the freeze savestate's ARM9 register block
> (`b.find(b"ARM9")`, then `Cycles, Halted, R[16], CPSR`):
>
> ```
> PC = 0xFFFF0108      <- the ARM DATA-ABORT vector
> LR = 0x0239BD8C      <- inside CAVE_SL_SELECT, +0x21C
> regs held 0x0239BB71 (the clone), 0x47 (count code), 0x139 (prompt)
> ```
>
> `+0x21C` is the template's tail, whose first instruction is `ldr r7,[pc,#0x78]` — wanting a
> literal at clone offset **`0x28C`**, when the clone was only **`0x232`** bytes. `r7` loaded
> whatever followed in the cave (zero) and `ldr r1,[r7,#0]` aborted.
>
> **`detect_function_size` under-reported the function by `0x11A` bytes.** It stops at the
> `pop {..,pc}` at `0x02235946`, which sits *before* the inline literal pool at
> `0x02235954..0x02235990`. True extent: **`0x34C`** (code to `0x02235A40`, trailing pool to
> `0x02235A4C`, where the next function's `push` begins).
>
> ⚠️ **The lesson, and it is a verification lesson.** My `verify()` asserted the lift
> **round-trips byte-for-byte at its original address** — and a truncated lift passes that
> trivially, because the prefix that *was* copied is genuine code. The identity check can never
> detect truncation. Round 2's two clones were unaffected only by luck (their pools happened to
> end exactly at the detected boundary).
> Fixes: `lift_handler_to_builder` gained an explicit `size=`, and `_lift` now asserts **every
> `ldr rX,[pc,#imm]` in a clone resolves inside the clone**. Recorded as
> `tool.lift_extent_truncation` (VERIFIED — its proof demonstrates the truncation *and* that
> the truncated lift still round-trips).
>
> ### 🔬 IN-GAME TEST 5 — no more freeze, but "nothing happens". GDB trace: **enumeration is FINE**
>
> Ruled out statically first, all verified rather than assumed:
> - **Race codes** — `Fish 8 / Sea Serpent 5 / Aqua 14` confirmed against the game's own
>   `ERA2_RACE_MAP` (`game_constants.py`), i.e. NDS-native, retiring the cross-binary 3DS
>   dependency. The test board's Poison Draw Frog `0x191A` **is** Aqua.
> - **The type-`0x8` banished gate** — `0x0219CD08`'s banished arm (`0x0219CDAA`; the jump-table
>   target is `0x0219CD22 + off`, my first read was 8 bytes low) checks a per-entry status
>   halfword at **`player + 0xA0C`**: low byte `0xC0` → reject, `0x40` → accept iff `(hi>>1)&1`,
>   anything else → accept. The savestates read `0x0000` → **accept**. (The GY arm `0x0219CDA6`
>   just returns 1 unconditionally.)
> - **`param`** — `0x02234E78` returns 0 for *every* card including Barcha, so it is not the
>   differentiator between us and a working multi-select card.
> - **The cost slot** — `0x021E5060` unconditionally returns 1; it cannot abort.
> - **Buffer filling** — the multi template's sub-step 0 uses `0x02243FE0`, which *appends*,
>   returns the delta, then **restores the count** (a non-destructive probe), where the single
>   template used `0x02243FA8` (a real fill). That is fine: the picker `0x0219C430` calls
>   `0x02243FA8` itself at `0x0219C47C`.
>
> **GDB (`scratch/gdb_sealancer_e1_trace.py probe`, one breakpoint, one connection):**
>
> ```
> *** HIT 0x0239BEEE ***   (the CMP right after 0x02243FE0 inside CAVE_SL_COND)
>     r0 = 2      <- candidate count: BOTH banished Poison Draw Frogs found
>     r5 = 1      <- the donor's condition code, passed through
>     stack: 0x0224AE13, 0x0224BEA9, 0x0224BBF1, 0x02256AA5  (the menu module)
> ```
>
> So **the criteria row, the ov5 handler, the race list, the walker and the activation gate all
> work on the live path**, and the effect really is offered. The failure is downstream — the
> select template's sub-steps or the resolver. Next probes are wired in the trace script:
> `select` / `fizzle_cand` / `fizzle_legal` / `prompt` / `picker` / `collect` / `record` / `equip`.
> Prime suspect: the template **re-runs `0x0224AD94` itself** at `0x0223599C` (clone `+0x29C`),
> separately from the menu check that already passed; failing that returns 1 = silent fizzle.
>
> ### ✅ ROUND 6 — the silent fizzle, SOLVED by GDB (`fizzle_legal` hit, `r0 = 0`)
>
> `gdb_sealancer_e1_trace.py fizzle_legal` hit clean, `r0 = 0`, `r4 = 0x47`, `r6 = 0x139`, with
> `[sp+0x14] = 0x0224AE9F` (the slot5 invoke wrapper). So we were inside slot5, and the
> template's re-check of `0x0224AD94` returned 0.
>
> **Root cause: slot3 is re-evaluated MID-ACTIVATION, after the cost has run.**
>
> - `0x0224AD94` returns `slot3(desc) > 0` (slot2's branch is skipped because `+0x08` is NULL —
>   so *my cond shim alone* decides legality).
> - It is called **twice**: once by the menu to offer the effect, and again **by the
>   multi-select template itself** at `0x0223599C`, inside sub-step 0, before the picker. The
>   single template `0x02235604` never re-checks — which is exactly why rounds 2–3 never hit this.
> - Between the two, the activation state machine `0x02217F80` runs the **cost**: it tests
>   `desc[+7]` at `0x02217F8E`, runs slot4 only if clear, then **sets `desc[+7] = 1`** at
>   `0x02217FB4`.
> - The donor's slot3 `0x021F2460` requires `0x021A10A0(side, slot) == 0xFFFF` — a once-per-turn
>   "effect not yet used" marker — and the donor's cost `0x021E5060` **spends** it. So the donor
>   condition is TRUE at the menu and FALSE on the re-check. My shim chained it unconditionally →
>   `1` then `0` → **silent fizzle, "nothing happens".**
>
> **Fix:** gate the donor-condition call on `desc[+7]`. Run it only when `+7 == 0` (menu);
> mid-activation (`+7 == 1`) skip it and return the candidate-count check alone. Nothing slot3
> tests can change between the cost and the target step of one activation, so this is safe.
> Recorded as `dispatch.slot3_recheck_and_cost_flag` (VERIFIED). Cond shim is now 52 B (still in
> its 0x40… wait, 0x40 reserve — 52 = 0x34 ≤ 0x40, fits).
>
> This is the clean counterpart to the round-4 empty-pile fix: `desc[+7]` is the same flag, used
> to tell the two `0x0224AD94` calls apart.
>
> ### 🔬 IN-GAME TEST 6 — E1 EQUIPS! New bug: E3 ATK is +1000 **per equipped card**
>
> ml4: Sea Lancer with two Frogs equipped reads **ATK 3300 = 1300 + 2×1000**. E1 now works end
> to end (both banished Aqua monsters equipped, card-instance record `0x02296470` shows the
> holder with `+0x08 = 0x00010001`). The remaining bug is E3: "gains 1000 ATK **while equipped
> with a monster(s)**" is a flat +1000, but we get +1000 *per* card.
>
> **Cause (static):** the +1000 grant leaf `0x021B75F8` (our E3 retune) lives inside the
> ATK-compute function `0x021B44C0`, reached **once per equipped card** by an inner loop over the
> holder's equipped monsters. `[sp+0xB0]` is that function's modifier accumulator (zeroed once at
> `0x021B44EE`), and the leaf does `[sp+0xB0] += r1` each visit via the shared tail `0x021B7226`.
> The donor Mermaid Archer only ever equips ONE monster ("you can only equip 1 monster at a time
> with this effect"), so its native +800 never stacked — the per-equip model was invisible until
> Sea Lancer equipped several.
>
> Note the neighbouring leaf `0x021B722E` does `1000 × [r6+0x40]` in a single visit, i.e. some
> cards read an equip-count field and add once; ours adds flat and is *visited* per card.
>
> **Fix plan (needs the loop index):** redirect the 4-byte leaf `movs r1,#0x7D; lsls r1,#3` to an
> ov5 stub via an in-place `bl` (LR is free here — the leaf immediately branches into the
> accumulator/loop, never using LR before the function's own `pop {..,pc}`). The stub sets
> `r1 = 1000` on the FIRST equipped-card visit and `r1 = 0` otherwise, then returns; the existing
> `b 0x021B7226` still applies it. The gate is the equipped-card index — and **which register/
> stack slot holds it must come from GDB, not static liveness** (this is exactly the
> register-reuse case the footgun warns about; the loop sets it at `0x021B775E`/`0x021B776E` but
> r5/r6 are reused by the switch dispatch). `scratch/gdb_sealancer_atk_trace.py` captures the
> first N leaf hits and prints which slot goes 0,1,2,… across them.
>
> Rounding note (why NOT the divide trick): `1000/N` per card sums to 1000 exactly for N ∈ {1,2,4}
> but 999 for N=3. Gating on "first visit" is exact for all N.
>
> ### ✅ E3 SOLVED — the grant leaf is reached by TWO KINDS OF PASS, not a loop index
>
> The GDB stat-block dump settled it. With Frogs equipped, the leaf `0x021B75F8` is hit twice per
> ATK computation, and the two hits are **not** loop iterations — they are two different *kinds*
> of pass, distinguished by the stat block at `r7`:
>
> | | `[r7+0x3C]` | `[r7+0x24]` | meaning |
> |---|---|---|---|
> | hit A | **`0x02296470`** | `0x02296470` | the **holder's own** ATK pass — `+0x3C` is Sea Lancer's card-instance pointer. Happens **once** per computation. |
> | hit B | **`0`** | `0x191A191A` | an **equip-contribution** pass — carries the equipped card's packed word (Poison Draw Frog). One **per equipped card**. |
>
> Both add `r1` to the accumulator, and each pass owns a **separate frame** (SP differs by 0x50,
> so `[sp+0xB0]` is at a different address each time) whose totals are summed upstream — hence
> 1300 + 2×1000. Common to both: `r7+0x00 = 0x1FFC1FFC`, `+0x10 = 0x514` (1300 base ATK),
> `+0x14 = 0x3E8` (1000 DEF), `+0x0C` level 5, `+0x04` race 12 — i.e. both stat blocks describe
> **Sea Lancer**, which is why both dispatch to her cid's leaf.
>
> **Fix (exact, no rounding):** the leaf's 4 bytes become `bl CAVE_SL_ATK`; the stub sets
> `r1 = 1000` only when `[r7+0x3C] != 0` (the holder pass) and `0` otherwise. The leaf's own
> `b 0x021B7226` still applies `r1`. Because the holder pass happens exactly once, this is flat
> for **any** equip count — no divide (`1000/3` would have been 999), no cross-frame state.
> LR is free at the leaf: it branches straight into the accumulator and then the loop, and the
> function returns via its own stacked PC.
>
> ov5 dependency is safe: the leaf is only reached **while equipped**, which only happens in a
> duel (where ov5 is resident). A deck-editor ATK read has no equips and never reaches it.
>
> ⚠️ Bounded risk: `[r7+0x3C]` is n=1 per pass kind. If the read is wrong the worst case is the
> current behaviour (still ×N) or, if the holder pass somehow never fires, +0 — but the holder
> pass demonstrably fired in the trace, so at minimum the grant survives.
>
> ### ✅ E3 SOLVED (round 3) — COUNT the passes, don't try to tell them apart
>
> ⚠️ Two attempts to discriminate passes from a single GDB sample failed **in opposite
> directions**, and the three-point ATK measurement is what settled each:
>
> | gate | 0 / 1 / 2 equips | meaning |
> |---|---|---|
> | `[r7+0x3C] != 0` | 1300 / 2300 / **3300** | grants on **every** contributing pass (N×1000) |
> | `[r7+0x3C] == 0` | 1300 / **1300** / **1300** | that pass's accumulator never reaches the stored ATK |
>
> So **every pass that reaches the card's ATK looks identical** — there is no discriminator.
> The stat block invites a "holder vs equip pass" story (one hit has `[r7+0x3C]` = a
> card-instance pointer, another has 0 with `[r7+0x24]` = the equipped card's packed word) that
> the arithmetic flatly contradicts. Single-sample register semantics are not evidence.
>
> **The shipped fix counts instead of discriminating:**
> - `CAVE_SL_ATK` — the leaf redirect. Grants 1000 only if a flag is clear, then sets it.
> - `CAVE_SL_ATKRESET` — hooked at **`0x021B44EC`**, exactly where `0x021B44C0` zeroes its own
>   accumulator `[sp+0xB0]`. That instruction runs **once per invocation** by construction, so
>   it is the correct scope to clear the flag. The stub replays `mov r4,#0 ; str r4,[sp,#0xB0]`
>   verbatim — a `BL` does not move SP, so it writes the caller's slot — then clears the flag.
>
> Register budget at the reset site: `r2/r5/r6/r7` are live (`r5`,`r6` two instructions later,
> `r2` at `0x021B44F6`), `r4` is being zeroed anyway, and `r3`'s value is already saved by the
> function's own `push {r3,…}` — so `r3` is the scratch. At the leaf, `r1` is the output and
> `r0` is push/popped.
>
> Independent of any pass-kind guess: one reset per computation, one grant per reset → exactly
> +1000 for any equip count. Recorded as `battle.atk_grant_two_pass_stacking`.
>
> **IN-GAME CONFIRMED** (user, 0 / 1 / 2 equips → 1300 / 2300 / 2300).
>
> - Whether `0x021D7348` (the 0x24-byte struct built at `0x022187D8`, which stores `0xB` at
>   `+3` and the ref at `+0xC`) and `0x021C4A68` (phase `0x80`) carry further Graveyard
>   assumptions. Neither reads a container offset or a zone-code immediate, but neither has
>   been traced.
> - Whether the multi-equip actually resolves for N > 1: the selection loop and the resolver
>   loop are each proven in isolation (static + the round-2 in-game test for N = 1), but the
>   two have never run together. Watch for the 2nd..Nth card being skipped, or the equip zone
>   overflowing.
> - The once-per-turn gate is still the donor's, now wrapped by `CAVE_SL_COND` (which only ADDs
>   the candidate requirement). "Once while this card is face-up on the field" is still not
>   implemented — out of scope for v1.
> - Prompt `0x139` is Barcha's, so the on-screen wording is whatever Barcha shows. It is at least
>   an *equip* prompt, unlike round 3's; swap the constant if it reads wrong.
> - `0x021D7348` and `0x021C4A68` inside the cloned resolver are still untraced for further
>   Graveyard assumptions (neither reads a container offset or zone-code immediate).

> **STATUS 2026-07-21: E2 + E3 + reskin are IN-GAME CONFIRMED.** All four checks passed:
> card face reads Sea Lancer / Lv5 / WATER / Beast-Warrior / 1300 / 1000; ATK increases by
> exactly **1000** on equip; ATK drops back when the equipped monster leaves; the
> "destroy the equipped monster instead?" replacement effect and prompt still work.
> **E1 is still the donor's** ("target 1 face-up Lv≤3 monster you control") and card art is
> still Mermaid Archer's. Everything below is the evidence trail.
>
> **E1 steps 2, 3 and 3b are DONE (2026-07-21, second session; no ROM writes).** The five cls
> slot roles are established, a fourth dispatch table (cls3) and a fifth (the criteria
> registry `0x022713C4`) were found and mapped, the Fish/Sea Serpent/Aqua on-field predicate
> is a single mask `0x4120`, and the off-field race codes are **Fish 8 / Sea Serpent 5 /
> Aqua 14**. E1 cannot be a plain registry row (the criteria word holds ONE race); the
> blueprint is Unicorn Beacon's bespoke handler `0x02242E60`.
>
> **Step 4 also DONE.** Reading the **3DS** implementation of Sea Lancer settled it: its shim is
> a line-for-line twin of Unicorn Beacon's NDS handler, and its race list literally reads
> `{8, 5, 14, 0}`. `0x0223C6AC` takes a **predicate + value list**, so multi-race banished
> filters are a shipped engine feature.
>
> **Step 5 was attempted and deliberately STOPPED before writing any patch.** Two static reads
> found (a) the NDS decodes no `0x40` equip-variant type bit, and (b) **Mermaid Archer has no
> cls record and no criteria row, so nothing would ever look one up** — the criteria path is
> only reachable from a cls record, while her E1 runs on the step-table machine. The
> enumeration half is fully proven. The **list-picker handoff has since been mapped too**
> (`0x0219C430` mode 6) — but it exposed a **third** blocker: the donor's board-slot MASK and
> the off-field candidate buffer are incompatible representations, so E1 on this donor is a
> full selection-step rewrite plus an unproven equip handoff, not a hook.
> **E1 now needs a donor decision from the user — see the three options at the end of
> "Step 5 attempted".**

Session: 2026-07-21. Scope agreed with user: **recon only, no ROM writes.**
Target: add **Sea Lancer** (GENF-EN081) to OTN EU (`BYYP`) by donor reskin.

Decisions locked with the user:
- **E1 fidelity:** accept **1-at-a-time** equip for v1 (not "any number"); keep the
  once-while-face-up gate.
- **Race:** ship **Beast-Warrior** (TCG-accurate) *iff* no native code path branches on the
  donor's race (see Open Questions).

---

## Effect text (authoritative — `scratch/ygoprodeck_cache.json`, NOT recalled)

> "You can target any number of your banished Fish, Sea Serpent, and Aqua-Type monsters;
> equip them to this card. This effect can only be used once while this card is face-up on
> the field. If this face-up card on the field would be destroyed, you can destroy 1 of
> those cards, instead. This card gains 1000 ATK while equipped with a monster(s) by this
> effect."

WATER / Beast-Warrior / Level 5 / ATK 1300 / DEF 1000.

- **E1** ignition equip: target *your banished* Fish / Sea Serpent / Aqua; equip to this
  card. Once **while face-up on the field** (resets on leaving the field, not per turn).
- **E2** destruction replacement: if this face-up card would be destroyed, you *can* destroy
  1 equipped card instead. **Any** destruction, not battle-only.
- **E3** continuous: **+1000 ATK** while equipped by E1.

---

## Confirmed (this session)

### KB is healthy
`.venv-1/Scripts/python.exe -m otn_enhanced.knowledge.verify_knowledge`
→ **78 facts, 65 PASS, 0 FAIL, 13 UNVERIFIED**. Oracles: arm9=yes, ov3=yes, ov5=yes,
savestate=`rom_all_patches.ml2`. `CAVE_FREE = 0x0239B7A0` (`ov5_cave.py:200`).

### Sea Lancer is NOT in the OTN pool
`otn_enhanced/rom/konami_id_to_card_name.py.tsv` (4308 OTN cids, format `HEXID<4 spaces>Name`)
has no "Sea Lancer" row. → donor reskin required. Also listed at
`ygo_tools/tools/finished_patches/todo.md:38` under "Cards to do".

### ❌ RETRACTED — "master handler table, cid at +0x14"

> **This was wrong and I chased it for a while. Recorded here so nobody repeats it.**
>
> I claimed a single 4116-record table at `0x02275C08` with the layout
> `{+0x00 main, +0x04 sub, +0x08 act, +0x0C, +0x10, +0x14 cid}` — cid last. **The cid is
> first.** The real cls2 base is `0x02275C04`, four bytes lower; reading from `…C08` shifts
> every field by one word and makes the cid appear at `+0x14`.
>
> What makes this instructive: the structural checks I ran were all *true of the wrong
> reading too*. The `+0x14` column really is per-segment sorted and in cid range; the `+0x00`
> column really is 100% Thumb pointers. A self-consistent structural story is **not** proof of
> the labels. I even talked myself out of the correct reading once, writing "it is not off by
> one".
>
> It was caught by an **external anchor**: the shipped `patch_armory_arm.py` records
> `cls1[0x1F33] +04 = 0x022215DD`, and *no* record matched that under the shifted reading.

**The correct geometry** (matches the constants the shipped patches already use), cid-FIRST,
stride 24, five Thumb callback slots at `+0x04..+0x14`:

| table | base | count |
|---|---|---|
| cls2 | `0x02275C04` | 0x2B9 (697) |
| cls0 | `0x0227E64C` | 0x51A (1306) |
| cls1 | `0x022860D4` | 0x535 (1333) |

Verified: each independently sorted by cid; every callback slot is NULL or a Thumb ov3
pointer; `cls1[938]` = cid `0x1F33` with `+04 = 0x022215DD` — the Armory Arm anchor exactly.
Recorded as `dispatch.cls_tables`; the two wrong facts are kept as UNVERIFIED with
`corrected_by`.

> ### ❌❌ RETRACTED (later the same day) — "Mermaid Archer is records-free"
>
> The paragraph below is **wrong** and cost several rounds of analysis. She has a full record
> at **`cls3[527]`**. The search covered cls0/cls1/cls2 only, because **cls3 `0x02279D74` had
> not been discovered yet**, and it was never re-run once it was. See "SOLVED by GDB" further
> down, and `dispatch.donor_cls3_record`. **Always search all four cls tables.**

~~**Mermaid Archer `0x1FFC` has NO record in cls0/cls1/cls2** — she is records-free. That is
*why* all three of her clauses are driven by cid-literal switches (E1 `0x0225026C`,
E2 `0x0225C3A6`, E3 `0x021B74B0`) rather than by table rows.~~

> **Blast radius: none.** The shipped patch never used row data — E3 came from the cid-literal
> switch and is GDB- and in-game-confirmed; E2 was untouched. Only this note's E1 study tables
> and two KB facts were affected, and both are now corrected.

### Donor selected: **Mermaid Archer, cid `0x1FFC`**
Method: cross-referenced all 4308 OTN cids against `scratch/ygoprodeck_descs.json` for
`equip .{0,30} to this card` (42 hits), `destroy .{0,60} instead` (67), and
`gains \d+ ATK .{0,80} equip` (29). Mermaid Archer is the only card in all three.

Text (ygoprodeck):
> "Once per turn: You can target 1 face-up Level 3 or lower monster you control; equip that
> target to this card. (You can only equip 1 monster at a time to this card with this
> effect.) While equipped with a monster by this effect, this card gains 800 ATK. If this
> card would be destroyed, you can destroy the monster equipped to it with this effect,
> instead."

- **E2 is word-for-word Sea Lancer's** — "would be destroyed" (any destruction) + "you can".
- **E3 differs only in the constant** 800 → 1000.
- **Donor stats — read from `scratch/ygoprodeck_cache.json`, NOT recalled:** WATER /
  Sea Serpent / **Level 3 / ATK 1200 / DEF 200**. (I first wrote "Level 4 / 1400 / 1500" from
  memory and it was wrong on all three — see the correction below.) Attribute is already right;
  the reskin rewrites Level 3 → 5, ATK 1200 → 1300, DEF 200 → 1000, race → Beast-Warrior.
- **Unclaimed:** `grep -rn "0x1FFC\|Mermaid"` over `otn_enhanced/cards/*.py`
  and `otn_enhanced/knowledge/check_allocations.py` → **no hits**.

### The four overlay-3 sites carrying cid `0x1FFC`
All aligned u32 occurrences in `ygo_tools/reference_files/nds_overlay_3.bin` (base
`0x02141700`); exactly four:

| VA | role | reached from |
|---|---|---|
| `0x0227CEDC` | master-handler-table row 1224, cid field (`+0x14`) | — |
| `0x02250424` | literal pool of a **linear** cid switch | loader `0x0225026C` `ldr r0,[pc,#0x1b4]; cmp r5,r0`; host fn prologue `0x0224FA4C` |
| `0x0225C494` | literal pool of a second cid switch | loader `0x0225C3A6` `ldr r0,=0x1FFC; cmp r4,r0; beq 0x0225C3B2`; host fn prologue `0x0225C2B8` |
| `0x021B7700` | literal pool of a **binary-search** cid switch | loader `0x021B74B0` `ldr r0,=0x1FFC; cmp r2,r0; bgt 0x021B74C2 / blt 0x021B74BA`; equal-leaf `0x021B75F8` |

### All three sites identified by switch co-membership

The two "hosts" are **not** called by `BL` — they are entries in small function-pointer
**step tables** driven by generic phase machines, which is why a caller scan finds nothing:

| host | pointer lives at | table | driver |
|---|---|---|---|
| `0x0224FA4C` | `0x0228E1CC` | `0x0228E1B8`, 12 entries | `0x02253834`: `ldr r4,=0x0228E1E8; ldr r1,[r4,#4]; ldr r1,[base,r1<<2]; blx r1`, advances `[r4,#4]` on success |
| `0x0225C2B8` | `0x0228EF98` | `0x0228EF84`, 13 entries | `0x0225CD92`: step index from `[r4,#0x58]`, bounds-checked `1..0xC`, `blx` |

#### Site 2 → **E2**, the destruction-replacement dispatcher — `0x0225C2B8`
Every one of the **8** cids in this switch has an "instead of being destroyed" replacement
clause (texts from `scratch/ygoprodeck_descs.json`):

| cid | card | its "instead" clause |
|---|---|---|
| `0x1B39` | Great Shogun Shien | destroy a Six Samurai instead |
| `0x1FC6` | Defender, the Magical Knight | remove Spell Counters instead |
| `0x1FC9` | Power Tool Dragon | send 1 equipped Equip Spell instead |
| **`0x1FFC`** | **Mermaid Archer** | **destroy the equipped monster instead** |
| `0x2073` | Earthbound Immortal Cusillu | Tribute 1 other monster instead |
| `0x2172` | Dragunity Javelin | equip itself instead of going to GY |
| `0x219B` | Underground Arachnid | destroy the equipped monster instead |
| `0x226F` | Black-Winged Dragon | place a counter instead of taking damage |

8/8 — a closed argument. Mermaid Archer's leaf is entered at `0x0225C3A6`
(`ldr r0,=0x1FFC; cmp r4,r0; beq 0x0225C3B2`).
**E2 needs no change at all** — the donor's wording already *is* Sea Lancer's.

#### Site 1 → **E1**, the target-selector step — `0x0224FA4C`, shared leaf `0x0225028E`
The `0x1FFC` comparison at `0x0225026C` funnels **three** cids into one shared leaf
`0x0225028E`: `0x1FC9` Power Tool Dragon, **`0x1FFC` Mermaid Archer**, `0x219B` Underground
Arachnid — exactly the "select a card, then equip it to this card" trio.

The leaf body is a selectable-target mask builder:
```
0x0225028E  pack (side, slot) -> [sp,#0x34]
0x022502A6  for side  = 0..1:            ([sp,#0x4C])
0x022502B4    for zone = 5..9:           ([sp,#0x48])
0x022502BC      bl 0x021A3930(side, zone, packed_ref, r5=cid)
0x022502C4      if r0: set bit (zone + side*5) in the mask [sp,#0x44]
0x0225031E  bl 0x02251040(mask)          -> hand the mask to the picker
```
So **`0x021A3930` is the per-cid target predicate** — the "face-up Level 3 or lower monster
you control" filter — and it is the thing E1 must be redirected away from (to a banished-zone
enumeration with a race filter). The zone loop `5..9` is the monster zones; the banished zone
is a different container entirely, so E1 is **not** a predicate-only swap. `unproven` beyond
the static read.

#### Site 3 → **E3**, the ATK/DEF accumulator — leaf `0x021B75F8` ✅ **the +800 is located**
The binary-search switch at `0x021B74B0` (`ldr r0,=0x1FFC; cmp r2,r0; bgt/blt`, equal-arm
`b 0x021B75F8` at `0x021B74B8`) lives in a function whose co-members are the ATK/DEF
modifiers: Stim-Pack, Phalanx Pike, Dragonic Attack, Chthonian Alliance, Fighting Spirit,
Double Tool C&D, Molting Escape, Power Frame, Darkworld Shackles, Flint, Weapon Change,
Miniaturize, Wattcastle, Overdoom Line, Fairy Box, Shadow Spell, Cocoon of Evolution — and,
clustered right around Mermaid Archer's leaf, the *absorb-the-equipped-monster's-ATK* set:
`0x1284` Thousand-Eyes Restrict, `0x1AB1` Cyberdark Dragon, `0x1BB8` Destiny Hero - Plasma,
`0x21FC` Transforming Sphere.

The leaf:
```
0x021B75F8   movs r1, #0x32      ; 32 21
0x021B75FA   lsls r1, r1, #4     ; 09 01     -> r1 = 0x320 = 800
0x021B75FC   b    0x021B7226
0x021B7226   ldr r0,[sp,#0xB0] ; adds r0,r0,r1 ; str r0,[sp,#0xB0]   ; accumulate the delta
```
✅ **GDB-CONFIRMED 2026-07-21** (`scratch/gdb_e3_leaf_probe.py`, breakpoint on the leaf itself,
not the switch arm — the leaf is exclusive to cid `0x1FFC`, so a single hit is decisive):
```
*** HIT 0x021b75f8 ***
    pc=0x021b75f8  lr=0x021b7743  sp=0x027e3388
    r0=0x00001ffc  r1=0x00001ab1  r2=0x00001ffc  r3=0  r4=0  r5=0x700  r6=0x0c  r7=0x027e3664
```
`r2 = 0x1FFC` is the switch operand — the engine reached this leaf *for Mermaid Archer*.
The +800 provably originates here, so the 4-byte retune is correct and sufficient.
(`r1 = 0x1AB1` is Cyberdark Dragon, a leftover comparison operand from the binary search.)

⚠️ **She was UNEQUIPPED when it fired** — zone record `10001ffc 00010002 00000001 ...`, bit
`0x40000` clear, with Deep Sea Diva `0x1FFB` still in her own zone. So the "while equipped"
condition is **not at the leaf**. See Open Question 1: the gate is either in the caller
(`lr = 0x021B7743`), in the accumulator's consumer, or absent. A reskin inherits whatever
the donor does here.

- Raw bytes at `0x021B75F8` = `32 21 09 01`; **overlay-3 file offset `0x00075EF8`**.
- **Exactly one** branch targets `0x021B75F8` (the `B` at `0x021B74B8`), so the leaf is
  Mermaid Archer's alone — verified by scanning every `B`/`Bcc` in `0x021B6800..0x021B7700`.
- **The 800 → 1000 retune is a 4-byte, same-length in-place edit:**
  `movs r1,#0x7D` (`7D 21`) + `lsls r1,r1,#3` (`C9 00`) = `0x3E8` = 1000.
  Thumb-1 only, no literal pool, no cave slot, no table resize.
- ⚠️ **A second `movs r1,#0x32; lsls r1,#4` exists at `0x021B7246`** (another card's +800).
  The patch must target `0x021B75F8` exactly and `verify()` must assert `0x021B7246` is
  still `32 21 09 01`.

---

### The `0x02275C08` region is FOUR cls tables, not one
Proving the row layout incidentally proved the previously-UNVERIFIED `dispatch.cls_table_bases`.
The cid column at `+0x14` has **exactly 4 descents**, at rows 696 / 1473 / 2780 / 4114:

| segment | rows | cid range |
|---|---|---|
| cls0 | 0..696 | `0x0D7E`..`0x24E8` |
| cls1 | 697..1473 | `0x0D48`..`0x24E4` |
| cls2 | 1474..2780 | `0x0BB8`..`0x24E7` |
| cls3 | 2781..4114 | `0x0E0B`..`0x24E6` |
| terminator | 4115 | `0x0002` |

Each segment is independently non-decreasing (the binary-search precondition). **198 adjacent
row pairs share a cid** — that population *is* the `find_event_handler` leftmost-record hazard
that shadowed Warwolf E1/E2. Mermaid Archer's row 1224 sits in **cls1**.

### 🔓 The banished zone is `player+0x7B4`, count `player+0x1C` — E1 is unblocked

Found by diffing the user's savestates (see the savestate table below). Between `.ml6`
(Mermaid Archer on the field, equipped with Deep Sea Diva) and `.ml7` (Mermaid Archer
banished), the player-0 struct changed at exactly these places:

```
+0x001C  0 -> 1            banished count
+0x0014  7 -> 8            GY count
+0x0070..0x0080            Mermaid Archer's monster-zone record cleared
+0x00C0..0x00E4            Deep Sea Diva's record cleared
+0x0578  0 -> 0x0F101FFB   Deep Sea Diva appended to the GY
+0x07B4  0 -> 0x10881FFC   Mermaid Archer appended to the BANISHED zone
```

| array | base | count | shape |
|---|---|---|---|
| Graveyard | `player+0x55C` | `player+0x14` | packed u32 card words |
| **Banished** | **`player+0x7B4`** | **`player+0x1C`** | packed u32 card words |
| Extra Deck (known) | `player+0x4E4` | `player+0x18` | packed u32 card words |

Verified as a closed invariant — "exactly `count` leading nonzero words, then zeros" — over
**5 savestates × 2 players × 2 arrays = 20 cases, all clean**. In `.ml7`, side-0's GY holds
8 entries at `+0x55C..+0x578` with count `+0x14 == 8`; side-0's banished holds 1 entry at
`+0x7B4` with count `+0x1C == 1`.

Note the GY/banished/Extra-Deck triple share one layout (`base`, packed, count in the
`+0x0C..+0x1C` count block) — so the same enumeration code shape works for all three.

### ✅ Effective ATK IS stored — card-instance record, and the grant IS gated

> **Correction.** I first claimed "a monster's current ATK is never materialised in RAM",
> after scanning all of main RAM for **1400 → 2200** and finding nothing. The premise was
> fine; **the search values were wrong.** Mermaid Archer is **ATK 1200 / DEF 200 / Level 3**,
> not the 1400/1500/Level 4 I asserted from recall. Searching **1200 → 2000** finds the slot
> instantly. Root cause: card stats quoted from memory instead of read from
> `scratch/ygoprodeck_cache.json` — the exact failure mode CLAUDE.md forbids for card *text*;
> it applies to stats too. Kept in the KB as `battle.atk_never_stored_wrong` with
> `corrected_by: ram.card_instance_record`.

**Card-instance records**: a stride-`0x28` array in the `0x0229 6xxx` heap —
**cid at `+0x0C`, effective (post-modifier) ATK at `+0x20`, Level at `+0x24`.** The ATK/Level
fields are live only while the card is face-up *on the field*; a card in hand/Deck/GY, or one
equipped to another monster, carries 0 in both. Validated in `.ml3` against the printed cards:
Deep Sea Diva `0x1FFB` 200/Lv2, Mermaid Archer `0x1FFC` 1200/Lv3, Gladiator Beast Laquari
`0x1C76` 1800/Lv4 — all exact. Mermaid Archer's record sits at `0x02296470`.

**The +800 is correctly gated on being equipped** (record `0x02296470 + 0x20`):

| state | board | ATK |
|---|---|---|
| `.ml3` | on field, **not** equipped | **1200** |
| `.ml4` | equipped with Deep Sea Diva | **2000** |
| `.ml5` | equipped, destroy-redirect prompt | **2000** |
| `.ml6` | equipped monster destroyed as the replacement → no longer equipped | **1200** |
| `.ml7` | banished | record cleared to 0 |

(The first `.ml6` capture was taken slightly too early and read 2000; the user re-saved it and
it now reads 1200. My copy has been refreshed.)

So although leaf `0x021B75F8` computes the 800 unconditionally — the GDB breakpoint hit it
while she was unequipped — **the gate is downstream of the accumulator**. A card reskinned
onto cid `0x1FFC` therefore inherits *correct* conditional-ATK behaviour for free; only the
constant needs retuning. Recorded as `battle.atk_grant_is_gated_on_equip` (VERIFIED).

### The monster-zone record, and an equip flag (ambiguous)
Zone records are `player+0x34`, stride `0x14`, 5 zones; word 0 is the packed card ref.
Mermaid Archer's word at **`+0x08`** went `0x00000001` → `0x00040001` the moment her equip
effect resolved, and stayed set in `.ml4`/`.ml5`/`.ml6`. Gladiator Beast Laquari (never
equipped) stays `0x00000001` throughout.

⚠️ **Ambiguous**: bit `0x00040000` could mean *"has a monster equipped by this effect"* or
*"once-per-turn effect already used"* — both became true at the same instant, and n=1 card.
Recorded as `ram.zone_equip_flag` (UNVERIFIED) with a disambiguating experiment.

### Race-dependency audit (gates the Beast-Warrior reskin)

| clause | leaf | reads the card's race? |
|---|---|---|
| E3 | `0x021B75F8` | **No** — the leaf is `movs`/`lsls`/`b`, zero memory accesses. Proven. |
| E2 | `0x0225C3B2` | **No** — sweeps zones via `0x0225C288(side, zone, 0)`; no race field touched. Proven at leaf level. |
| E1 | `0x0225028E` | **No** in the leaf; the filter lives behind `0x021A3930`. **Not audited.** |

→ **Beast-Warrior is safe for the E2/E3 slice.** Re-check before E1 lands.

Notable: cid `0x1FFC` has only **four** aligned u32 occurrences in all of overlay 3, and none
of them is in the `0x021A3xxx` range — so `0x021A3930` **cannot** be cid-switching on Mermaid
Archer by literal. The "face-up Level 3 or lower monster you control" filter must therefore
come from somewhere else, most likely row 1224's `target_filter` slot `0x021E4E84`. Unresolved.

---

### 🔓 E1 recon: the zone-code → container selector `0x0219CA28` (VERIFIED)

`0x0219CA28(r0=side, r1=zone_code, r2=index)` returns a pointer to one packed u32 card word.
`r4 = zone_code - 0xB; if (unsigned)r4 > 4` → the slot path `player + 0x34 + (zone_code+index)*0x14`
(0x14-stride zone records, clamped at 10); otherwise a 5-entry PC-relative halfword jump table
at `0x0219CA40` selects a **list** container `player + CONST + index*4`:

| zone code | container | array | count |
|---|---|---|---|
| `0x0B` | recent-summon list | `player+0x124` | `player+0x0C` |
| `0x0C` | Extra Deck | `player+0x4E4` | `player+0x18` |
| `0x0D` | **Deck** | `player+0x304` | `player+0x10` |
| `0x0E` | Graveyard | `player+0x55C` | `player+0x14` |
| **`0x0F`** | **Banished** | **`player+0x7B4`** | **`player+0x1C`** |
| else | monster / S-T zone records | `player+0x34 + code*0x14` | — |

Container↔count pairings measured on `.ml4`: side0 deck 27 cards ↔ `+0x10` = 27; side1 30 ↔ 30;
GY 7/4 ↔ `+0x14`; banished 0/0 ↔ `+0x1C` (and 1 in `.ml7`). `0x0E` = GY independently explains
the Armory Arm `cmp r0,#0xE` GY-presence gate. Recorded as `ram.container_for_zone_code`.

**So the parameter E1 needs is `zone_code = 0x0F`.**

### ⚠️ But E1 is not a parameter swap of the donor's selector

The donor's equip-target leaf `0x0225028E` builds a **10-bit slot mask** — `for side in 0..1,
for zone in 5..9: if 0x021A3930(side, zone, ref, cid) then set bit ((side-1)*5 + zone)` — then
hands the mask to `0x02251040`. That shape only addresses a fixed 5-slots-per-side board. The
banished zone is a **variable-length list**, so it needs a list picker, not a slot mask.

E1 therefore needs the *other* selection path — the one used by the banished readers. Study
targets, **re-dumped with the corrected cls geometry** (slots are `+04 +08 +0C +10 +14`; what
each slot means is still **unverified** — the decompiler's main/sub/act/filter/resolution
names have not been checked):

| cid | card | record | slots |
|---|---|---|---|
| `0x1C95` | **Release from Stone** — select 1 banished **Rock**, SS it | cls0[873] | `0x2207528`, —, `0x21F03B4`, —, `0x2235604` |
| `0x231A` | **Unicorn Beacon** — banished + **two-race** + level cap | cls0[1204] | `0x222FC44`, —, `0x22031B8`, —, `0x2235604` |
| `0x2012` | **Psychic Path** — banished + race + **up-to-2 multi-select** | cls0[1056] | `0x2208180`, —, `0x21F05A8`, `0x21E4D80`, `0x2235700` |
| `0x21EF` | **Forgotten Temple** — the Fish/Sea Serpent/Aqua triple | cls0[1160] + cls1[1146] | `0x2208DB0`,`0x21E3CF0`,`0x21F0BA0`,`0x21E74A0`,`0x2235EBC` |
| `0x1FFC` | Mermaid Archer (donor) | **none** | records-free |
| `0x2081` | Genetic Woman | **none** | records-free |

So the banished selectors live in **cls0**, and three of them share the `0x2235604`
resolution template. Both Genetic Woman and the donor are **records-free**, which is why the
donor's clauses are all cid-literal switches.

⚠️ Everything I previously wrote about these cards' handlers came from the mis-based table and
was junk — including "Genetic Woman is records-driven, the ideal transplant shape". She has no
record at all. Start step 2 from the table above, not from the earlier text.

### 🎯 The race triple already exists in the ROM
**Forgotten Temple of the Deep `0x21EF`** — "Once per turn: You can target 1 Level 4 or lower
**Fish, Sea Serpent or Aqua-Type** monster you control; banish that target. During your End
Phase: Special Summon the monster(s) banished by this effect."

That is *exactly* Sea Lancer's race triple, already implemented. It has three handler rows
(1346, 2634, 3927) and 8 aligned ov3 sites: `0x0219F7F4`, `0x021AE948`, `0x021E3D68`,
`0x0224427C` (code literals) plus its table entries. Finding its race predicate would give E1
its filter for free — and note it also *banishes*, so it touches the same container.

---

## ✅ STEP 2 COMPLETE — what the five cls slots actually do

**All five roles established this session, from the dispatcher code itself, then cross-checked
against card text.** The decompiler's names in `data/over_the_nexus/decompiled/cards/*.py`
(`main / sub / activation_cond / target_filter / resolution`) map to slots 1-5 in order —
and **three of the five are wrong.**

| slot | decompiler called it | it actually is | fill (cls0/1/2) |
|---|---|---|---|
| `+0x04` | main | **RESOLVER — the effect body** | 1132 / 1099 / 592 (~99%) |
| `+0x08` | sub | **ON-FIELD CANDIDATE PREDICATE** `(desc, side, zone) -> bool` | 556 / 287 / 108 |
| `+0x0C` | activation_cond | **ACTIVATION CONDITION** ✔ correct — but returns a *code*, not a bool | 943 / 701 / 412 |
| `+0x10` | target_filter | **COST / activation-procedure step** ✘ | 304 / 387 / 332 |
| `+0x14` | resolution | **TARGET-DECLARATION step** ✘ | 481 / 277 / 144 |

### 🔓 First: there are FOUR cls tables, and the names are now *proven*

`find_event_handler 0x0224A118` reads the event descriptor's byte at **`+0x05`** (0..3) and
jumps through a PC-relative halfword table at `0x0224A134` (offsets `0x12 / 0x30 / 0x06 / 0x36`
relative to `0x0224A136`):

| sel | arm | table | base | count |
|---|---|---|---|---|
| 0 | `0x0224A148` | cls0 | `0x0227E64C` | 0x51A (1306) |
| 1 | `0x0224A166` | cls1 | `0x022860D4` | 0x535 (1333) |
| 2 | `0x0224A13C` | cls2 | `0x02275C04` | 0x2B9 (697) |
| 3 | `0x0224A16C` | **cls3** | **`0x02279D74`** | **0x308 (776)** |

**cls3 was never mapped before.** It is sorted, all-Thumb-or-NULL, and ends at `0x0227E634` —
`0x18` (exactly one record) below cls0's base. This also **proves the cls0/cls1/cls2 labels**,
which the retraction above correctly flagged as "pure inference": *the selector index is the
cls number.* (sel 2 with `descriptor[+4] == 0x25` falls through to the cls0 arm.)

The descriptor is a **0x24-byte stack struct**: `{+0x00 u16 cid, +0x04 u8 event code,
+0x05 u8 table selector, +0x07 / +0x08 "slot4 / slot5 already done" flags}`.
`find_event_handler` binary-searches (stride 0x18, leftmost-equal walk-back at `0x0224A808`)
and returns the **record base**, so a caller's `[r0,#0x04..0x14]` are exactly slots 1-5.

Recorded as `dispatch.cls_table_selector` (VERIFIED).

### The invoker module — one wrapper per slot, right beside the dispatcher

| wrapper | reads | behaviour |
|---|---|---|
| `0x0224AEB8` / `0x0224AEEE` (`ldr` @`0x0224AEF6`) | slot1 `+04` | `slot1(desc, phase)`, **default 0** |
| `0x0224A8C0`, `0x0224A924` | slot2 `+08` | one card: `slot2(desc, side, zone)` |
| `0x0224A988` | slot2 | → **bitmask** over side 0..1 × zone 0..0xA |
| `0x0224AA94` / `0x0224AC54` / `0x0224ACD0` / `0x0224AD20` | slot2 | → **count**; zone ranges 0..0xA / 0..4 / 5..0xA |
| `0x0224A8A0` | slot3 `+0C` | `slot3(desc, r1)`, **default 1** |
| `0x0224AD94` | slot3 **then** slot2 | the activation-legality test (below) |
| `0x0224AE50` (getter `0x0224AE70`) | slot4 `+10` | `slot4(desc, r1)`, **default 1** |
| `0x0224AE84` (getter `0x0224AEA4`) | slot5 `+14` | `slot5(desc, r1)`, **default 1** |

Every slot2 sweep **skips** a zone whose record word `[player + 0x44 + zone*0x14]` has bit
`0x200000` set (the negated/disabled bit).

### slot3 returns a CODE, not a bool — proven by `0x0224AD94`

```
r4 = find_event_handler(desc)
r6 = 1
if r4:
    if r4[+0x0C]: r6 = slot3(desc, arg)         # the activation condition
    if r6 == 1 and r4[+0x08]:                   # ONLY when slot3 said exactly 1
        r6 = (mask_builder(desc, slot2) != 0)   # ...must slot2 find a target
return r6 > 0
```

- **0** = cannot activate
- **1** = activatable *but slot2 must find at least one legal on-field target*
- **≥2** = activatable unconditionally, slot2 not consulted

The two ubiquitous constant stubs sit immediately before the dispatcher:
`0x0224A114 = movs r0,#2; bx lr` (**318 cls1 + 112 cls2 records** — "always, no field target
needed") and `0x0224A110 = movs r0,#0; bx lr`.

### Slots never share code — 2166 pointers, five disjoint blocks

Pooling every non-NULL slot pointer across cls0/cls1/cls2 (2166 distinct), the five slot
pools are **pairwise disjoint** and fall in five near-contiguous address blocks:

```
0x021D81A0 .. 0x021E4D7F   slot2  (+0x08)   346 ptrs
0x021E4D80 .. 0x021F01BF   slot4  (+0x10)    97 ptrs
0x021F01C0 .. 0x02204897   slot3  (+0x0C)   810 ptrs
0x02204898 .. 0x02234D73   slot1  (+0x04)   819 ptrs
0x02234D74 .. 0x0223913C   slot5  (+0x14)    94 ptrs
```

Slot role is a function of address band. **This is a cheap sanity check for any future slot
claim** — a pointer in the wrong band means the geometry is being read wrong again.

### The text correlation (the independent cross-check)

Share of cards whose ygoprodeck text contains each phrase, per slot vs the table baseline:

| population | Tribute | discard | pay LP | Target | Select | "on the field" | "from your Deck" |
|---|---|---|---|---|---|---|---|
| cls0 ALL | 8% | 7% | 5% | 22% | 13% | 28% | 7% |
| cls0 **has slot2** | 13% | 4% | 2% | 32% | 17% | **47%** | 4% |
| cls0 **has slot4** | **24%** | **19%** | **16%** | 20% | 11% | 24% | 9% |
| cls0 **has slot5** | 6% | 5% | 3% | **51%** | **27%** | 36% | 3% |
| cls1 ALL | 9% | 5% | 3% | 23% | 9% | 31% | 11% |
| cls1 **has slot2** | 13% | 1% | 3% | 37% | 13% | **65%** | 2% |
| cls1 **has slot5** | 10% | 3% | 3% | **55%** | **21%** | 51% | 5% |
| cls2 ALL | 8% | 10% | 4% | 18% | 9% | 24% | 20% |
| cls2 **has slot2** | 8% | 12% | 5% | 39% | 15% | **56%** | 3% |
| cls2 **has slot5** | 6% | 11% | 3% | **55%** | **25%** | 47% | 2% |

- **slot4 → cost words** (Tribute 3.0×, discard 2.7×, pay-LP 3.2×) and *not* targeting words.
- **slot5 → targeting words** (Target 2.5-3.1×, Select 2.1-2.8×) and *not* cost words.
- **slot2 → on-field words** (2.0-2.3×), *depleted* for "from your Deck" (4%/2%/3% vs 7/11/20%).
- **slot1** tracks the baseline exactly on every feature — it is the universal effect body.

### slot4 = cost — confirmed card-by-card

| slot4 pointer | n | the cards |
|---|---|---|
| `0x021E50CD` | 55 | Exiled Force *"You can **Tribute this card**"*, Jigen Bakudan *"**Tribute it** during your Standby Phase"*, The Forgiving Maiden *"**Tribute this face-up card**"*, Valkyrion, Maryokutai — it is `0x021E50CC: bl 0x021CF658` = **send-self-to-GY** |
| `0x021E7215` | 14 | Baou / Twin Swords / Card Rotator / Reptilianne Medusa *"**Send 1 card from your hand** to the GY"*, Limit Impulse & Meteor Flare *"send **2** cards from your hand"* — never aborts (always returns 1) |
| `0x021E51E5` | 352 | the generic trampoline to `0x021E50DC` |

This corroborates the Quasar note's "the cls3 `+10` tag was the Tribute" — with the correction
that **`0x021E7215` is not "costless"**, it is the send-from-hand cost (it merely can never fail).

### slot5 = target declaration — the picker, and what the per-card immediate means

361 cards reach one shared body through a one-line thunk
`movs r2,#code; ldr r3,=0x02234CA5; bx r3`. The body `0x02234CA4(desc, r1, r2=code)`:

```
sub-step 0:  n = 0x0224AA94(desc)              # count legal targets -- USING SLOT2
             if n == 0: return 1               # nothing to target, succeed silently
             0x0219A818(side, code)            # show the prompt
             0x0224BA34(side, cid, 0, 0x0224A8C1)   # open the board cursor,
             [0x0229AB7C] += 1                 #   handing it the SLOT2 invoker 0x0224A8C0
             return 0                          #   as its legality callback
sub-step 1:  if 0x0224BBB0(): 0x022347B0(...); return 1   # pick finished -> record it
             else: [0x0229AB7C] -= 1; return 0
```

**The per-card immediate is a prompt-string id, not an action** — the action is in slot1:

| code | n | every card in the group is worded… |
|---|---|---|
| `0x3A` | 12 | *"send it to the Graveyard"* — Ruthless Denial, NEX, Faustian Bargain, Mask Change, Dragon Laser |
| `0x4E` | 12 | *"place that target on the top of the Deck / return it to the Deck"* — Back to Square One, Phoenix Wing Wind Blast, Level Down!?, Wrath of Neos |
| `0x4F` | 5 | *"return that target to the **Extra Deck**"* — De-Fusion, Contact Out, De-Synchro |
| `0x57` | 31 | *"return that target to the hand"* — Compulsory Evacuation Device, Spiritualism, Relieve Monster, Beast Soul Swap |
| `0x64` `0x6F` `0x77` `0x7C` `0x85` `0x00` | 26-90 each | control/ATK-DEF/counter/Speed-Spell groups |

### The activation state machine `0x02217F80` — the order slots run in

```
if !desc[+7]: if slot4_getter(desc): r = slot4_invoke(desc, ...)
                                     if r == 0 -> abort;  if r < 0 -> abort(0x0A)
              desc[+7] = 1; [0x0229AAFC+0x7C] = 0; [0x0229AB7C] = 0; return 0x76
if !desc[+8]: <the same, with slot5>                                  return 0x75
...
0x0221803E:   [state+0x18] = slot1_invoke(desc, 0)      # the resolver
```
Both slot4 and slot5 are **multi-step sub-machines** driven by the counter `[0x0229AB7C]` /
`[0x0229AAFC+0x7C]`, returning 0 to yield ("call me again"), negative/0 to abort the whole
activation, positive to advance. `0x76` / `0x75` are the yield codes.

Recorded as `dispatch.cls_slot_roles` and `dispatch.slot5_target_picker` (both VERIFIED).

### ⚠️ NEW TRAP — `data/over_the_nexus/decompiled/cards/` is off by one record

That directory was generated under the **retracted** geometry, so it attributes every record's
five handlers to the **previous card**. The five pointers are correctly *grouped*; only the
card label is shifted. Demonstrated:

- `c05541_i1872_Reversal_Quiz.py` claims `main = RAM 0x02216714`.
- Under the correct geometry **Reversal Quiz `0x15A5` is cls0[398], slot1 = `0x02216805`**.
- `0x02216715` is the slot1 of **cls0[397] = `0x15A4` Royal Tribute**.

So the filenames, `KONAMI_ID` constants and `Table idx` comments in that directory are all
unreliable, on top of the field names being wrong. Recorded as
`dispatch.decompiled_cards_off_by_one` (UNVERIFIED, with the regeneration experiment).

### 🎯 The consequence for E1 — the on-field picker is a dead end, and why

The `0x02234CA4` slot5 template and slot2 **only ever address the on-field board**
(side 0..1 × zone 0..0xA; `0x0224BA34` is a board cursor). That is the *same* limitation the
donor's own leaf `0x0225028E` has. **So E1 cannot be built from the common slot5 template
either.**

The banished selectors use the **other** slot5 template, `0x02235604` (254 records across the
three tables — Release from Stone `0x1C95` and Unicorn Beacon `0x231A` both use it, and both
have **no slot2 and no slot4**). It calls a different enumerator family:

```
0x02235604:  param = 0x02234E78(desc)              # per-cid criteria selector
             n = 0x02243FA8(side, cid, param)      # LIST-ZONE candidate count
0x021F03B4:  (Release from Stone's slot3) 0x02243FE0(side, cid, param)   # "any legal one?"
```
`0x02243F38 / 0x02243F60` dispatch through a **stride-12 table at `0x022713C4` / `0x022713C8`**
indexed by container kind, and `0x02244030` walks a list container by index. **That module —
`0x02243xxx` — is the off-field selection engine E1 needs.** `unproven` beyond the static read.

## ✅ STEP 3 COMPLETE — the Fish / Sea Serpent / Aqua predicate is ONE MASK

Forgotten Temple of the Deep `0x21EF` implements the triple in its **cls0 slot2** at
`0x021E3CF0` — i.e. it is an *on-field candidate predicate*, exactly as slot2's role predicts
(its text says "…monster **you control**"):

```
0x021E3D1E  bl 0x021B44B4(side, zone, &buf)   ; fill a 0x24-byte stat block on the stack
0x021E3D24  movs r0,#0xE ; ldrsh r0,[r1,r0]   ; buf[+0x0E] = LEVEL
0x021E3D28  cmp r0,#4 ; bgt reject            ; "Level 4 or lower"
0x021E3D2E  ldr r1,[sp,#8]                    ; buf[+0x08] = RACE BITFIELD
0x021E3D30  ldr r0,=0x00004120                ; @0x021E3D6C
0x021E3D32  tst r0,r1 ; beq reject            ; <-- the Fish/Sea Serpent/Aqua triple
0x021E3D36  movs r0,#1                        ; accept
```

**The triple is the constant `0x4120` = `0x0020 | 0x0100 | 0x4000`**, ANDed against
`stat_block[+0x08]`. Reusable verbatim for an on-field filter — and the level cap is right
next to it if a level gate is ever wanted.

Recorded as `dispatch.race_mask_fish_seaserpent_aqua` (VERIFIED). Two caveats stated in the
fact and **not** to be assumed away:
1. The **per-bit assignment** is unproven — only that the *union* of the three is `0x4120`.
   Sea Lancer needs all three, so this does not block E1, but do not claim "Fish = 0x20".
2. `0x021B44B4` is keyed by **(side, zone)** — on-field. A banished-zone filter needs the
   equivalent stat fetch for a packed card word, not this entry point.

---

## ✅ STEP 3b COMPLETE — the off-field selection engine, and E1's real shape

### 🔓 A FIFTH per-card dispatch table: the criteria registry `0x022713C4`

Stride **12**, count **`0x56C` = 1388**, sorted by cid, binary-searched by `0x02243B9C`
(`ldrh r2,[r0,r2]` against the u16 at row+0). All 1388 handlers are Thumb ov3 pointers in
`0x0223C938..0x02243A9C`.

| offset | field |
|---|---|
| `+0x00` | u16 **cid** |
| `+0x02` | u16 aux (`0xFFFF` for most) |
| `+0x04` | Thumb **handler** |
| `+0x08` | u32 **criteria word** |

`0x02243F38` does `blx [row+4](row, side, param)`; `0x02243FA8` (count) and `0x02243FE0`
(any?) wrap it — and those are exactly what slot5 template `0x02235604` and Release from
Stone's slot3 `0x021F03B4` call. **This is the engine that reads list zones (Deck / GY /
banished)** — the one the on-field slot2 + slot5 pair cannot reach.

⚠️ **A cid may own several rows.** Agent of Miracles - Jupiter `0x2449` owns three (its cost
row, its target row, and a generic one). Do not assume one row per card.

### The banished readers share handlers — the criteria word is the *only* per-card parameter

| handler | n | family |
|---|---|---|
| `0x0223E5D0` | 10 | **Special Summon from banished** — Dimension Distortion, Dimension Fusion, Return from the Different Dimension, D.D.M., Miraculous Descent, Release from Stone, Dimension Explosion, Escape from the Dark Dimension, **D.D.R.**, Agent of Miracles - Jupiter |
| `0x0223DB24` | 9 | **add banished to hand** — Miracle Dig, Layard, Shutendoji, Dimensional Alchemist, Light of Redemption, Psychic Path, Genetic Woman, Parallel Selection, Laval Lancelord |
| `0x0223F8C8` | 1 | **return banished to GY** — Burial from a Different Dimension |

`0x0223E5D0` is a **9-instruction thunk**:

```
0x0223E5D0  push {r1,r2,r3,lr} ; r2 = row
0x0223E5D4  r0 = [row,#8]      ; the criteria word
0x0223E5D8  [sp] = criteria ; [sp+4] = 0xC ; r1 = row.cid ; r2 = 0
0x0223E5E4  bl 0x0223C6AC      ; the generic list-zone picker
```

So **every difference between "SS a banished Rock" and "SS a banished DARK" and "SS any
banished monster" is the one u32 at `row+0x08`.** That is the lever E1 wants.

### 🎯 The criteria word decoded — race and attribute, and Sea Lancer's three codes

**Top byte = race in the high 5 bits, attribute in the low 3**: `race = byte >> 3`,
`attr = byte & 7`, `0` = unrestricted in either field.

The decisive anchor is **Agent of Miracles - Jupiter `0x2449`** — *"select 1 face-up **LIGHT
Fairy**"* — which owns both a `0x88` row and a **`0x89`** row. `0x89 = 0x88 (Fairy) | 0x01
(LIGHT)`: the only way one byte carries both fields at once.

| attr code | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| | LIGHT | DARK | WATER | FIRE | EARTH | WIND |

(each 100% pure over its rows except LIGHT 14/15 — standard Konami order)

Race codes are **this game's internal order, not Konami's** (purity in brackets):

| 1 | 2 | 3 | 4 | **5** | 6 | 7 | **8** | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|
| Dragon (29/35) | Zombie (18/19) | Fiend (9/10) | Pyro (6/6) | **Sea Serpent** (1/1) | Rock (6/6) | Machine (12/15) | **Fish** (2/3) | Dinosaur (8/8) | Insect (13/13) |

| 11 | 12 | 13 | **14** | 15 | 16 | 17 | 18 | 19 | 20 | 21 |
|---|---|---|---|---|---|---|---|---|---|---|
| Beast (11/12) | Beast-Warrior | Plant (19/19) | **Aqua** | Warrior (15/16) | Winged Beast (5/5) | Fairy (14/15) | Spellcaster (4/5) | Thunder (2/2) | Reptile (16/16) | Psychic (15/15) |

**The three codes Sea Lancer E1 needs:**

| race | code | witness |
|---|---|---|
| **Fish** | **8** | Superancient Deepsea King Coelacanth `0x1D0A` crit `0x40900002` *"Level 4 or lower **Fish-Type**"*; Metabo-Shark `0x2197` crit `0x40010002` *"2 **Fish-Type** monsters"* |
| **Sea Serpent** | **5** | Deep Sea Diva `0x1FFB` crit `0x288C0002` *"Level 3 or lower **Sea Serpent** monster"* |
| **Aqua** | **14** | ⚠️ **by elimination** — Swap Frog `0x2115` crit `0x73880002` is race 14 / WATER but its text names *both* WATER and Aqua-Type, so it is not a clean witness. 14 is the only code left unassigned in 1..21 once the other twenty are pinned. **Do not treat Aqua = 14 as directly proven.** |

Nice coincidence worth noting: **Deep Sea Diva `0x1FFB` — the very card sitting on the
recon savestates' board — is the Sea Serpent anchor.**

### ❌ …but a plain registry row CANNOT express E1

The criteria word carries **one** race code. Sea Lancer needs **three**. So the "just add a
row" path is closed.

**The in-ROM precedent is Unicorn Beacon `0x231A`** — *"Select 1 removed from play Level 5 or
lower **Beast-Type or Winged Beast-Type** monster"*. Two races + a level cap, on the banished
zone: exactly Sea Lancer's shape one race short. Its row is
`{cid 0x231A, aux 0xFFFF, fn 0x02242E60, crit 0x00950002}` — **top byte `0x00`, i.e. no race
in the criteria word at all.** It carries its multi-race filter in a **bespoke handler**.

**That is E1's blueprint: a bespoke handler, not a plain row.** And the ov5 cave already gives
us somewhere to put one.

Recorded as `dispatch.criteria_registry` and `dispatch.criteria_word_race_attribute` (both
VERIFIED).

### Not yet decoded (do not guess these)

- The **low 3 bytes** of the criteria word. Partial observations only: bit 1 (`0x2`) is set on
  833 of 1388 rows and makes `0x0223C6AC` run the search **twice**, once with bit 0 clear and
  once set (`r5 &= ~3` … `r5 |= 1`), which smells like a side selector — but Return from the
  Different Dimension ("*your* banished") and Dimension Fusion ("*both players*") both carry
  `0x0002`, so that story does not hold up. **Unproven.** Bit 16 (`0x00010000`) is set on the
  targeting/selecting cards and clear on Return from the Different Dimension ("as many as
  possible") and Genetic Woman — plausibly "the player picks" — also **unproven**.
- The `[sp+4] = 0xC` constant `0x0223E5D0` passes to `0x0223C6AC`. It is *not* obviously the
  `0x0F` banished zone code from `ram.container_for_zone_code` — different namespace, or a
  size/stride. **Unproven; do not assume the two namespaces are the same.**

---

## ✅ STEP 4 COMPLETE — the 3DS shows the shape, and the NDS already has every piece

The user's instinct was right on both counts: **custom code in the ov5 cave**, and **read the
3DS implementation first**. The 3DS build has Sea Lancer natively, and its implementation maps
onto an NDS function that already exists.

### The 3DS Sea Lancer shim, side by side with an NDS card

> ⚠️ 3DS addresses below are **structural evidence only** — a different binary (ARMv6,
> VA = `0x00100000` + file offset). Per `otn_enhanced/docs/engine/README.md` they are deliberately kept
> **out** of the knowledge base.

| step | 3DS Sea Lancer shim `0x4B0210` | NDS **Unicorn Beacon** handler `0x02242E60` |
|---|---|---|
| load a value list | `ldr r1,=0x006AA518` | `ldr r6,=0x022712DC` |
| copy it to the stack | `vldmia/vstmia` (16 B) | `ldm r6!,{r0,r1}; stm r5!,{r0,r1}; ldr/str` (12 B) |
| `r3` = &copy | `add r3, sp, #8` | `adds r3, r5, #0` |
| `r1` = cid | `ldrh r1,[r0]` | `ldrh r1,[r4]` |
| `[sp]` = criteria word | `ldr r1,[r0,#8]` | `ldr r0,[r4,#8]; str r0,[sp]` |
| `[sp+4]` = **type** | `mov r2,#0x48` | `movs r0,#0xE` |
| `r2` = **predicate** | `ldr r2,=0x003F8F20` | `ldr r2,=0x0223C791` |
| call the registrar | `bl 0x4B0AC4` | `bl 0x0223C6AC` |

**They are the same function, written twice.** The two predicates are the same code too — both
open with the identical 14-bit card-id mask (`lsl #0x12` / `lsr #0x12`) and the same
`cmp r1,#0xE` branch, then linear-scan a caller-supplied, zero-terminated u32 list.

### 🔓 So `0x0223C6AC` takes SIX arguments, not four

```
0x0223C6AC(r0 = side,
           r1 = cid,
           r2 = extra predicate  (or 0),
           r3 = &value list      (or 0),
           [sp]   = criteria word,
           [sp+4] = type)
```

The shared thunks just pass `r2 = r3 = 0`. **11 ov3 call sites already pass a real predicate +
list** — multi-value filters are a first-class, shipped feature of this engine.

- `0x0223C790` = the **race-list** predicate (the NDS twin of the 3DS one).
- `0x0223C764` = the same idiom for a packed level/attribute key.
- `0x0223C52C` (the walker `0x0223C6AC` calls) loads the literal **`0x000007B4`** — that is
  `player+0x7B4`, **the banished array** from `ram.graveyard_and_banished_arrays`. Independent
  confirmation that this really is the banished-zone engine.
- The **type is a bitfield**, tested bit by bit (`tst r1,#1` → side flip at `0x0223C562`;
  `movs r2,#8; ands r2,r6` at `0x0223C584`). NDS thunks pass `0xC` = Special Summon,
  `0x8` = add/return, `0xE`, `0x1E`, `0xA`, `0x9`, `0x1` — matching the 3DS namespace exactly.

### 🎯 Aqua = 14 is now CONFIRMED, from two independent directions

The caveat from step 3b is retired:

1. **NDS.** Unicorn Beacon's list at `0x022712DC` is **`{0x0B, 0x10, 0x00}`** = `{Beast=11,
   Winged Beast=16, terminator}` — exactly its *"Beast-Type or Winged Beast-Type"* text. The
   next list, `0x022712E8 = {0x0F, 0x07, 0x00}`, is `{Warrior=15, Machine=7}`. The race
   numbering and the zero-terminator convention are both confirmed in-ROM.
2. **3DS.** Sea Lancer's own race list reads literally **`{8, 5, 14, 0}`** — Fish, Sea Serpent,
   Aqua — the same three values I had derived independently on the NDS side, in the same order.
   (Both of Sea Lancer's 3DS shims point at the same triple.)

### 🛠️ E1 is now a build, not a research problem

No trampoline needed for the selection: **the criteria row's handler pointer *is* the hook.**
The ov5 stub is a ~25-instruction clone of `0x02242E60` with three substitutions:

| | Unicorn Beacon | **Sea Lancer** |
|---|---|---|
| value list | `0x022712DC` = `{11, 16, 0}` | **`{8, 5, 14, 0}`** — 16 B in the ov5 cave |
| predicate | `0x0223C791` | **`0x0223C791`** (unchanged — it is the race-list predicate) |
| criteria word | `0x00950002` | **`0x00010002`** (the 3DS's own param for Sea Lancer; note top byte `0x00` = no single race, because the race comes from the list) |
| type | `0xE` | see the open question below |

**Open question — the type, i.e. where the equip comes from.** The 3DS gives Sea Lancer type
**`0x48` = `0x40 | 0x08`**, and it is the *only* type-`0x48` shim in that entire binary; the
`0x40` bit is the equip variant. **The NDS types observed top out at `0x1E`, so `0x40` is
probably not implemented there** — `unproven` either way. Two routes:

- **(a)** confirm whether `0x0223C52C` decodes bit `0x40`; if it does, E1 is nearly free.
- **(b)** otherwise use a plain type for the *selection* and keep the donor's **already-working
  equip action** (`0x0225028E` → `0x02251040`), which is exactly what step 4 of the original
  plan proposed — replace only what feeds it a target.

Recorded as `dispatch.criteria_registrar_predicate_list` (VERIFIED), and
`dispatch.criteria_word_race_attribute` updated to drop the Aqua caveat.

---

## Ruled Out

- **Cyberdark Horn `0x1AAE` / Edge `0x1AAF` / Keel `0x1AB0` / Dragon `0x1AB1`,
  Allure Queen LV3/5/7 `0x1AD6`–`0x1AD8`, Relinquished `0x1281`,
  Thousand-Eyes Restrict `0x1284`** as the donor. All four Cyberdarks and both
  Relinquished-family cards phrase E2 as **"If this card would be destroyed *by battle*"**;
  Allure Queen likewise. Sea Lancer's E2 is *any* destruction. Mermaid Archer's is the only
  in-pool wording that matches exactly. (Texts read from `scratch/ygoprodeck_descs.json`.)
- **Cloning a shared "equip from banished" template.** In the 3DS engine (see below)
  Sea Lancer is the **sole** member of its effect type — there is no template to copy, in
  either engine. E1 needs real RE regardless of donor.

---

## 3DS (Zexal WDC) reference — what it does and does not buy us

Via the existing analyzer `scratch/zexal_card_engine.py` against
`3ds_extract/partition0/exefs/code_dec.bin` (ARMv6, **VA = 0x00100000 + file offset**).

> ⚠️ **Different binary.** Per `otn_enhanced/docs/engine/README.md` these addresses must never enter the
> NDS namespace or the knowledge base. They are structural evidence only.

- Sea Lancer is present: 3DS cid `0x131A`, Konami `0xA671` → masked **`0x2671`**, with the
  exact English text quoted above.
- It decomposes into **four registry rows + one boolean id-list membership**:

  | table | row |
  |---|---|
  | effect-script registry `0x686CBC` | `{0x2671, shim 0x4B0210, param 0x00010002}` |
  | predicate/helper registry `0x6A6D44` | `{0x2671, 0x49DC54, 0x48ACC4}` |
  | stride-0x18 event registry (~`0x6D21B4`) | `{0x2671, 0x428AE0, 0, 0x49BFF8, 0x4008A8, 0x477E88}` |
  | stride-0x10 registry (~`0x6D6394`) | `{0x2671\|flags, 0, 0x355ADC, 0x22DAC0}` |
  | sorted u16 membership list (~`0x69F090`) | contains `0x2671` |

- Shim `0x4B0210` calls registrar **`0x4B0AC4`** with type **`0x48`**. Enumerating *every*
  card that reaches `0x4B0AC4` gives a coherent family: Return from the Different Dimension,
  Escape from the Dark Dimension, D.D.R., Miracle Dig, Burial from a Different Dimension,
  Dimensional Alchemist, Light of Redemption, Leviair, Release from Stone, Brain Hazard,
  Miraculous Descent, Primal Seed… → **`0x4B0AC4` is the "reads the banished zone"
  registrar**; the type nibble is the disposition (`0xC` = Special Summon, `0x8` =
  add/return, Sea Lancer's `0x48` = `0x40|0x8` = the equip variant).
- Its per-card callback `0x3F8F20` is a tiny **race-filter predicate**: fetch a card
  property, mask to 14 bits (`lsl #0x12 / lsr #0x12`), linear-scan a caller-supplied id list.
- **Sea Lancer is the only type-`0x48` card in the entire binary.**

**Takeaways for OTN:** (a) the three clauses are *independent registrations* even in the
sibling engine, so implementing them one clause at a time is engine-native; (b) E1 is
fundamentally "enumerate the banished zone + race filter + equip", which is what step 5 of
the plan goes looking for on the NDS side.

---

## Open Questions

1. ~~Is the `+800` gated on "while equipped"?~~ ✅ **RESOLVED — yes, it is gated.** The gate is
   downstream of the accumulator (1200 unequipped / 2000 equipped / 1200 again once the equipped
   monster is gone). The reskin inherits correct behaviour. See the section above.
2. **Where does the "face-up Level 3 or lower monster you control" filter live?** Not at
   `0x021A3930` by cid literal (cid `0x1FFC` has no occurrence in `0x021A3xxx`). Most likely
   row 1224's `target_filter` slot `0x021E4E84`. This is the thing E1 must replace.
3. **Where is the banished zone in the player struct?** (base `0x0229AC94`, stride `0xB3C`).
   Not the monster zones (`+0x34`), the recent-summon list (`+0x124`) or the Extra Deck
   (`+0x4E4`). **This is E1's real blocker** — the equip-target selector only sweeps monster
   zones 5..9, so E1 is *not* reachable by swapping the selector's predicate.
   Now recorded in the KB as `ram.banished_zone_array` (UNVERIFIED, with this experiment).
4. **How is "once while face-up on the field" stored?** Mermaid Archer is once-per-turn; the
   two gates differ in reset timing. Unknown whether the donor's HOPT word is reusable.
5. **Does the E1 path read the card's race?** (see the audit above — E2/E3 are clear).

---

## Next Experiment

### A0. E1 — the plan from here (next session starts at step 2)

**Step 1 ✅ done.** Zone code `0x0F` = banished, via the verified selector `0x0219CA28`.
Corroboration: `0x0219F784` gates a zone TRANSITION with `cmp r6,#0xE / cmp r7,#0xF /
cmp r6,#0xF / r0 = r7-0xB; cmp r0,#2` — i.e. from-zone/to-zone codes drawn from the same
namespace, with GY=0xE and banished=0xF exactly as mapped.

**Step 2 ✅ done — see "STEP 2 COMPLETE" above.** All five slot roles established; the
decompiler's names are wrong for slots 2, 4 and 5; a fourth table (cls3 `0x02279D74`) was
found and the cls0/1/2 labels are now *proven* rather than inferred.

**Step 3 ✅ done — see "STEP 3 COMPLETE" above.** The race triple is the single mask
`0x4120` tested against `stat_block[+0x08]`, in Forgotten Temple's slot2 `0x021E3CF0`.

**Step 3b ✅ done — see "STEP 3b COMPLETE" above.** The criteria registry `0x022713C4` is
mapped, the race/attribute encoding is solved, and Fish = 8 / Sea Serpent = 5 / Aqua = 14.

**Step 4 ✅ done — see "STEP 4 COMPLETE" above.** `0x0223C6AC` takes a predicate + value list;
Unicorn Beacon is the worked NDS example; Aqua = 14 confirmed twice over.

### ⛔ Step 5 attempted — STOPPED SHORT OF BUILDING, on purpose

User said "build it". I did the two static reads first, and they turned up **two blockers that
make a build speculative right now.** Recording rather than guessing.

**Blocker 1 — the NDS has no equip variant.** `0x0223C52C` decodes type bits **`0x01`, `0x04`,
`0x08`, `0x10` and nothing else**; there is no `0x40` test. The 3DS's type `0x48` has no NDS
counterpart, so the equip must come from elsewhere (the donor's own action). *Answered — this
one is closed, and it is route (b).*

**Blocker 2 — there is no route from Mermaid Archer into this machinery at all.** This is the
real one, and it is new:

- The criteria path is only ever entered from a **cls record** (slot3 `0x021F03B4`-style, or
  slot5 template `0x02235604`) → `0x02243FA8`/`0x02243FE0` → criteria row → handler.
- **Mermaid Archer `0x1FFC` has no cls record and no criteria row.** Her E1 runs on a
  completely different machine: the 12-entry step table `0x0228E1B8` → step 7 `0x0224FA4C` →
  cid-literal switch → leaf `0x0225028E` → board-mask picker `0x02251040`.
- So adding a criteria row alone would be **dead code — nothing would look it up.**

**What IS now fully proven** (`dispatch.banished_walker_and_candidate_buffer`): `0x0223C52C`
walks `player+0x7B4`, hardcodes zone `0x0F`, applies the extra predicate, and records each
survivor via `0x02243B2C` into a global candidate buffer — count `(s16)[0x0229944C+6]`, card
word `0x02299458 + n*4`, locator `0x02299908 + n*2` (bit 0 = side, bits 1-5 = zone code),
capped at 299. `0x02243B2C` resolves its slot with the KB-verified `0x0219CA28`. Note this also
proves the zone-code namespace is shared — `0x0F` here **is** `ram.container_for_zone_code`'s
banished.

**The missing link is the picker handoff.** I can enumerate the right cards into the candidate
buffer; I cannot yet show how a *list* picker is opened over that buffer and how the chosen
entry comes back — `0x02251040` takes a 10-bit **board** mask and cannot represent a banished
index. Until that is mapped, any patch would be a guess at the one interface that matters.

### ✅ The picker handoff is now mapped — and it revealed a THIRD blocker

`0x02235604` is a three-sub-step machine on `[0x0229AB7C]`:

```
step 0:  n = 0x02243FA8(side, cid, param)   ; counts AND fills the candidate buffer
         if n == 0: return 1
         0x0219A818(side, 0x5E)             ; prompt
         step++ ; return 0                  ; yield
step 1:  0x0219C430(side, 6, cid)           ; ← THE LIST PICKER (mode 6), over the buffer
         step++ ; return 0                  ; yield
step 2:  r = 0x0219C534()                   ; the result
         if r <= 0xA: 0x022347B0(desc, side, r)          ; a board slot
         else: 3x 0x0219C510() + 0x0219C534(), unpack with the walker's key extraction,
               0x02234880(desc, side, key, ref)          ; a list entry
         return 1
```

Recorded as `dispatch.offfield_picker_sequence` (VERIFIED).

> ⛔ **Blocker 3 — the two selection paradigms are not interchangeable.** I checked the donor's
> leaf tail: `0x0225028E` builds a **10-bit board-slot mask**, hands it to **`0x0225BE0C`**
> (not `0x02251040`, which is only an intermediate), and returns yield code `0x6E`. A board
> mask has **no representation for a banished list index**. The off-field path uses a
> completely different picker (`0x0219C430` mode 6) reading the candidate buffer.
>
> So moving Mermaid Archer onto the off-field path is **not** a hook or a parameter swap — it
> means replacing her entire selection step, inside a step machine whose yield/status codes
> (`0x6E` / `0x76` / `0x75` / `0x64` / `0x0A`) are only partly decoded — **and then** proving
> that the donor's downstream equip action accepts a banished-zone locator where it currently
> receives a board slot. That last interface is unproven and is exactly the kind that silently
> no-ops.

**I was wrong last session to call this "mechanical" once the picker was found.** The picker
was one of three gaps, not the last one.

### 🔀 The decision this forces — a donor question, not a code question

Sea Lancer's three clauses may not be satisfiable by one donor:

- **Mermaid Archer `0x1FFC` (current)** — gives **E2 + E3 free** (shipped, in-game confirmed),
  but her E1 is board-mask/step-table based, so banished selection is a rewrite of the
  selection step + an unproven equip handoff.
- **A records-driven off-field donor** — e.g. **D.D.R. `0x1D5F`**, which *already* does
  "target 1 of your banished monsters; Special Summon it **and equip it with this card**" on
  the shared handler `0x0223E5D0`. E1 would come nearly free. But D.D.R. is a **Spell**, so the
  reskin to a Level 5 WATER monster is a different (and probably larger) problem, and E2/E3
  would both have to be rebuilt.

### Option 2 chosen — progress, and where it stands

User picked **option 2** (keep the donor, full off-field rewrite). Half of what option 2 needed
is now done; the other half is a live-RAM question that cannot be answered statically.

**✅ The step-machine protocol is decoded** (`dispatch.activation_step_machine_protocol`):

```
0x02253834:  idx = [0x0229DD94+4]
             fn  = [0x0228E1B8 + idx*4]      ; 11 steps then NULL
             if !fn: return 1
             if blx fn():                    ; NONZERO = finished
                 [0x0229DD94+8] = 0          ; per-step scratch, reset on advance
                 [0x0229DD94+4] = idx + 1
             return 0
```

- **Return 0 = yield ("call me again"), nonzero = advance.** This is exactly the sub-step
  protocol a replacement step needs, and it matches `0x02235604` returning 0/1.
- **`[0x0229DD94+8]` is a free per-step scratch word**, cleared on every advance — the natural
  home for a replacement step's own sub-step counter.
- Correction: the target selector `0x0224FA4C` is **step 5**, not step 7. The address in
  `dispatch.step_table_target_select` was always right; the index label was miscounted, and is
  now fixed.

**✅ The donor's UI request is a posted struct, not a call**: `0x0225BD40(side, kind, u16, u16)`
sets `[0x0229DE14+0x50] = 1` (pending), `+0x54` side, `+0x58` kind, args at `[0x0229DE54+0x20]`
/ `+0x22`. Kind wrappers 1,2,3,5,6,7,8,9,0xA,0xB exist; the donor's board pick is **kind 5**.
Note the two u16 arg slots would comfortably hold a candidate index or count.

**⛔ The remaining unknown — and it is genuinely a GDB question.** There are **two distinct
UI-request systems**:

| | posts via | used by |
|---|---|---|
| step machine | `0x0225BD40` (`0x0229DE14` struct) | the donor's step 5, kind 5 = board mask |
| criteria engine | `0x0219C430` (module `0x0219Cxxx`) | the off-field slot5 template, mode 6 = list |

**They are not known to share a result channel.** Whether the donor's steps 6-10 can consume a
pick produced by the criteria engine's picker is the one thing standing between here and a
working E1 — and it cannot be settled by reading more disassembly, because it is about what is
actually in RAM when those steps run.

**Next experiment (GDB, one session, per the preflight in CLAUDE.md):** breakpoint the donor's
step 5 leaf `0x0225028E` and each of steps 6-10 (`0x022510D0`, `0x02251CC4`, `0x022523B4`,
`0x022529B0`, `0x0225372C`) while activating Mermaid Archer's equip effect on the `.ml3` board.
Record, at each hit: `[0x0229DE14 + 0x4C..0x5C]`, `[0x0229DE54 + 0x20]`, and the candidate-buffer
triple (`(s16)[0x0229944C+6]`, `0x02299458`, `0x02299908`). That tells us **which step reads the
pick and in what representation** — and therefore whether an ov5 step-5 replacement can write a
banished locator the rest of the machine will accept.

⚠️ Do this in **one** connection — the melonDS stub desyncs on repeated connects, and
`scratch/gdb_sea_lancer_leaves.py` is already written for exactly this shape.

#### GDB attempt 2026-07-21 — inconclusive, stub died. New constraint learned.

`scratch/gdb_sealancer_pickchannel.py` was written and run twice. **Neither run captured a
hit**, but two things were learned and one is a hard constraint:

- ⚠️ **The melonDS stub drops the socket if you arm ~6 software breakpoints at once.** Run 1
  armed all six sites, and the connection was closed by the stub on the first `continue`
  (`WinError 10053`) before any hit. Run 2 armed **one at a time** and survived the first
  `continue`, but timed out at 40 s with no hit and the socket then died on the second arm.
  **Arm one breakpoint at a time, and budget one wait per connection.**
- Board state read cleanly both times (preflight passed, overlay 3 resident):

  | side | zone | cid | card |
  |---|---|---|---|
  | 0 | 2 | `0x1FFC` | Mermaid Archer |
  | 0 | 3 | `0x2115` | **Swap Frog** — Level 2 **Aqua/WATER**, a legal Lv≤3 target |
  | 1 | 2 | `0x1DEE` | opponent |

- Baseline (idle, nothing activated): step index 0, scratch 0, UI request struct all zero,
  **candidate buffer count 0** — so the buffer is genuinely empty until something fills it.

**Revised experiment — use a SAVESTATE, not GDB.** CLAUDE.md already prefers savestate parsing
for bulk RAM reads, and the state we need is a *static* mid-activation snapshot, which is
exactly what a savestate captures without any timing pressure:

> **Ask the user for one savestate taken while the donor's equip-target prompt is OPEN** — i.e.
> Mermaid Archer's effect activated, the game asking which monster to equip, cursor on screen,
> before confirming. Save as `data/over_the_nexus/working/sealancer_pick.ml8`.

#### ✅ Savestates captured and parsed — and they OVERTURN the working model

User supplied `rom_sea_lancer.ml2` (before) / `.ml3` (during the effect) / `.ml4` (after).
RAM0 offset `0x24` in all three; the effect really did resolve (**Swap Frog `0x2115` is gone
from side0 z3 in `.ml4`** — it was equipped).

Board throughout: side0 z2 Mermaid Archer `0x1FFC`, side0 z3 **Swap Frog `0x2115`** (Level 2
**Aqua**/WATER — a legal Lv≤3 target), side1 z2 `0x1DEE`.

> ⚠️ **The donor's E1 does NOT run on the step-table board-mask path.** Recorded as
> `dispatch.donor_e1_not_on_step_table_path` (UNVERIFIED — a contradiction to resolve, not a
> new claim). Two independent measurements agree:
>
> 1. **GDB:** the breakpoint on `0x0225028E` never fired in 40 s while the effect was activated.
> 2. **Savestate `.ml2` → `.ml3`:** the `0x0225BD40` request words — `[0x0229DE14+0x50]`
>    pending, `+0x54` side, `+0x58` kind — are **all still zero during the activation**. So
>    `0x0225BD40` was never called.
>
> `dispatch.step_table_target_select`'s *structural* proof still passes; what is wrong is the
> inference that this is the path actually taken. Its argument was static co-membership — the
> same class of "self-consistent structural story" this note already got burned by once.

**What the diff says is really happening** (`.ml2` → `.ml3`, sprite churn filtered out):

| address | before → during | meaning |
|---|---|---|
| `[0x0229DE14+0x0C]` | `0` → **`0x0224A8C1`** | the **slot2 single-card invoker** `0x0224A8C0` — exactly the legality callback the cls **board** slot5 template `0x02234CA4` hands to picker `0x0224BA34` |
| `[0x0229AB7C]` | `0` → `1` | the **cls substep counter** — the same one `0x02235604` (the off-field template) drives |
| `[0x0229DD94+0x18]`, `+0x34` | `0` → `1` | selection pending |
| `[0x0229DD94+0x60]`, `+0x64` | → `0x1FFC` | the acting card is Mermaid Archer |
| `[0x0229AB5C]` | `0x0F` → `0x05` | a zone code narrowing |
| candidate buffer | count stays **0** | the criteria engine is *not* involved (the `0x0f002115` word sitting at `0x02299458` is a **stale leftover** — `0x02243FA8` zeroes the count on entry, so the data there persists as garbage) |

**Why this is good news.** If the donor's selection runs on the **cls picker family** rather
than the step-table board-mask path, then it is the *same* infrastructure as the off-field
template `0x02235604` — both driven by `[0x0229AB7C]`, both ending at `0x022347B0`/`0x02234880`.
The "two incompatible UI systems" reading that blocked the build may simply be wrong.

**But there is a puzzle that must be solved before building:** `0x1FFC` has **no cls record**,
so `0x02234CA4` cannot have been dispatched from one. Something else is putting `0x0224A8C1`
into the picker slot for a records-free cid. Until we know what, we do not know where to hook.

#### ✅ SOLVED by GDB — and the "records-free donor" claim was FLAT WRONG

One breakpoint at picker entry `0x0224BA34`, one connection
(`scratch/gdb_sealancer_whichpicker.py`). It hit on the first activation:

```
*** HIT 0x0224ba34 ***
    lr=0x02234d1f   <- cls BOARD slot5 template 0x02234CA4 +0x7a
    r0=0 (side)  r1=0x1ffc  r2=0  r3=0x0224a8c1 (slot2 invoker)  r4=0x7c (prompt code)
    [sp+0x14] 0x0224ae9f  <- slot5 invoke wrapper 0x0224AE84 +0x1a
```

So the live chain is exactly what `dispatch.cls_slot_roles` predicts:

```
slot5 wrapper 0x0224AE84  ->  thunk (prompt 0x7C)  ->  board template 0x02234CA4  ->  picker 0x0224BA34
```

### ❌ RETRACTED — "Mermaid Archer is records-free"

**She has a full cls record at `cls3[527]`.** The original search covered
**cls0/cls1/cls2 only** — it was run *before* cls3 (`0x02279D74`) was discovered, and was never
re-run afterwards. That single stale negative sent several rounds of this analysis chasing the
step-table/board-mask path, which **never executes**.

| slot | value | role |
|---|---|---|
| `+0x04` | `0x0220BFFC` | **resolver — the equip action** |
| `+0x08` | `0x021E2070` | on-field candidate predicate ("face-up Lv≤3 you control") |
| `+0x0C` | `0x021F2460` | activation condition |
| `+0x10` | `0x021E5060` | cost |
| `+0x14` | `0x02234D8C` | target declaration → board template, prompt `0x7C` (90 records share it) |

Recorded as `dispatch.donor_cls3_record` (VERIFIED, GDB-confirmed); `dispatch.cls_tables`
carries the correction, and `dispatch.donor_e1_not_on_step_table_path` is marked resolved with
`corrected_by`.

**Lesson for the KB: always search all FOUR cls tables.** A negative result from before cls3
was known is not a negative result.

### 🛠️ E1 is now a slot rewrite, not new machinery

1. **`cls3[527] +0x14`**: `0x02234D8C` (board thunk) → the **off-field template `0x02235604`**,
   or an ov5 clone of it with Sea Lancer's prompt code.
2. **Criteria row for `0x1FFC`**: handler = ov5 clone of Unicorn Beacon's `0x02242E60`, list
   `{8, 5, 14, 0}`, predicate `0x0223C791`, criteria word `0x00010002`. Count-neutral insert
   into the 1388-row sorted registry (drop a phantom; register it in `PHANTOM_CLAIMS`).
3. **`+0x08`** (the on-field predicate) becomes unused for E1 — leave it; E2/E3 do not use it.
4. **`+0x04` resolver `0x0220BFFC` stays** — it is the working equip action.

### ✅ The read-back check — done statically, no emulator needed

**The two recorders converge.** `0x022347B0` (board: `desc, side, zone`) reads the zone record
`player+0x34+zone*0x14` and unpacks it into a key; `0x02234880` (list: `desc, side, a, b`)
takes the key already unpacked. Both then make the **identical** call
`0x021C750C(side, x, key, desc[+0x10])` and bump the same counter. Storage is shared — the
resolver cannot tell which recorder produced an entry.

**But the resolver's read-back is board-specific.** `0x0220BFFC` switches on the phase code
`[0x0229AAFC+0x70]` (`0x7E`/`0x7F`/**`0x80`** = act), fetches pick *i* through the shared
accessor `0x02234904(desc, i)`, and splits the halfword into **low byte = side, high byte =
index**. Then:

```
0x0220C06A  adds r3, #0x34
0x0220C06C  ldr  r2, [r3, r2]        ; player + 0x34 + idx*0x14  <-- BOARD zone record
```

⚠️ **It dereferences the index as a monster-zone slot.** A pick recorded from the banished
list would index the board array with a list position and silently equip the wrong card —
precisely the failure mode we have been trying to avoid.

Recorded as `dispatch.pick_record_and_resolver_readback` (VERIFIED).

### 🛠️ So E1 is FOUR edits, all of a shape already shipped in this repo

1. **`cls3[527] +0x14`** → off-field template `0x02235604` (or an ov5 clone with Sea Lancer's
   prompt code).
2. **Criteria row for `0x1FFC`** → ov5 clone of Unicorn Beacon's `0x02242E60`, list
   `{8, 5, 14, 0}`, predicate `0x0223C791`, criteria word `0x00010002`. Count-neutral insert
   into the 1388-row registry; register the phantom in `PHANTOM_CLAIMS`.
3. **NEW — resolver detour**: a cid-scoped ov5 hook at `0x0220C05C..0x0220C06C` that resolves
   the pick via the verified `0x0219CA28(side, 0x0F, index)` instead of the raw
   `player+0x34+idx*0x14` dereference. **Same shape as the shipped Armory Arm zone-gate detour
   in `patch_armory_arm.py`** — that is the template to copy.
4. `+0x08` (the on-field predicate) becomes dead for E1; leave it alone. `+0x04` resolver
   otherwise unchanged.

**No unknowns left in the design.** Every address above is VERIFIED, and the one live-path
question (is the cls3 record actually reached?) is GDB-confirmed. Build order: ov5 stubs first
(claim `CAVE_*`, bump `CAVE_FREE`, re-emit the ledger), then the registry insert, then the slot
retarget, then `verify()` on **every** shipped patch.

---

*(Superseded plan, kept for the record.)* Parsing that one file answers the whole question
offline: read `[0x0229DE14 + 0x4C..0x5C]`
(pending / side / kind — kind should read **5** if the board-mask path is what is live),
`[0x0229DE54 + 0x20]` (the mask), and the candidate triple (`(s16)[0x0229944C+6]`,
`0x02299458`, `0x02299908`). If the candidate buffer is **empty** while the prompt is open, the
donor's path never touches the criteria engine and an ov5 step-5 replacement must also drive
the board channel; if it is **populated**, the two systems do share state and E1 is buildable
as planned.

---

**The earlier three-way donor question, kept for reference.** Options, cheapest first:

1. **Ship E1 as a board-target effect** (equip a face-up Fish/Sea Serpent/Aqua you control,
   using the already-proven `0x4120` mask at the donor's predicate `0x021A3930`). Not the real
   card, but it is a small, provable change on the existing donor and keeps E2+E3.
2. **Keep the donor and do the full off-field rewrite** — accept that it needs the step-machine
   status codes decoded and a GDB session to prove the equip handoff.
3. **Re-donor to an off-field card** and rebuild E2/E3.

---

**Step 5 (original plan) — the build, once the picker handoff above is mapped.**

1. ~~Does the NDS decode type bit `0x40`?~~ ✅ **Answered: no.** Use the donor's equip action.
2. **How does a criteria row get added?** The registry `0x022713C4` is a **fixed sorted array
   of 1388**, binary-searched — so a new row for cid `0x1FFC` must be a **count-neutral
   insert** (drop a phantom cid to make room), per the donor-card rule. Confirm nothing else
   indexes this table by absolute row number before shifting rows. **Register the phantom in
   `PHANTOM_CLAIMS` and re-emit the ledger** before building.
3. **Then build**, in this order, verifying at each stage:
   - the ov5 stub (clone of `0x02242E60`) + the 16-byte `{8, 5, 14, 0}` list — claim a
     `CAVE_*` slot, bump `CAVE_FREE`, re-emit `allocations.yaml`;
   - the criteria row insert;
   - re-run `verify()` on **every** shipped patch, not just Sea Lancer.

⚠️ Live traps that remain:
- The **low 3 bytes of the criteria word are still undecoded** (see "Not yet decoded"). We are
  copying `0x00010002` wholesale from the 3DS's own Sea Lancer row rather than deriving it —
  that is fine as a starting value, but if E1 misbehaves (wrong side, no prompt), this word is
  the first suspect. Two plausible stories for bit 1 and bit 16 were each contradicted by a
  card; do not "fix" it by reasoning, anchor against a card whose text pins the value.
- The hook site is **static-only so far.** Before claiming E1 works, prove the criteria row is
  actually reached for cid `0x1FFC` on the live path — breakpoint the stub with Sea Lancer on
  the field and a Fish/Sea Serpent/Aqua monster banished. Savestate `.ml7` already has
  Mermaid Archer banished and can be adapted.

**Step 4 — the action.** Sea Lancer must *equip* the picked card, not Special Summon it
(Release from Stone) or add it to hand (Genetic Woman). The donor's own equip action is
already correct and already wired to cid `0x1FFC`; the goal is to keep it and replace only
what feeds it a target.

**Step 5 — the gate.** "Once while this card is face-up on the field" vs the donor's
once-per-turn. Different reset timing; see `ram.zone_equip_flag` (the `0x40000` bit at zone
record `+0x08`), whose meaning is still ambiguous between the two.

Scope reminder: v1 is **1-at-a-time**, agreed with the user — "any number" is out of scope.

### A. ~~Banished-zone array~~ — ✅ **SOLVED** (`player+0x7B4`, count `player+0x1C`)
What remains of E1 is now a *code* question, not a data one: which routine enumerates that
array, and can the equip-target selector be pointed at it. Study targets — the in-pool
banished readers, with their master-handler rows dumped this session:

| cid | card | row | main | act | res |
|---|---|---|---|---|---|
| `0x1D5F` | **D.D.R.** (selects a banished monster **and** equips — best study target) | 2399 | `0x02204A24` | `0x021F2294` | `0x02238B08` |
| `0x1D2F` | Escape from the Dark Dimension | 2388 | `0x022062F8` | `0x021F5F94` | — |
| `0x1DCE` | Light of Redemption | 2414 | `0x022048FC` | `0x021FE284` | — |
| `0x1B1D` | Burial from a Different Dimension | 2249 | `0x02208180` | `0x021F05A8` | `0x02235604` |
| `0x1D5D` | Dimensional Alchemist | 1075 | `0x02208498` | `0x021F0354` | — |
| `0x17BE` | Return from the Different Dimension | 2023 | `0x0221C0AC` | `0x021F80E0` | `0x02234D80` |

(An intersection of these six `activation_cond` callees came back empty — they share no
obvious banished-zone helper, which is why the savestate diff was the right tool.)

**Strong lead for the enumerator.** The three container offsets occur as *adjacent words in
the same literal pools*, which means some routine selects among them by a zone code:

```
0x0219CAD8: 0x4E4 (Extra Deck)   0x0219CADC: 0x55C (GY)   0x0219CAE0: 0x7B4 (banished)
0x0219CBAC: 0x4E4                0x0219CBB0: 0x55C        0x0219CBB4: 0x7B4
0x0219CCB0: 0x4E4                0x0219CCB4: 0x55C        0x0219CCB8: 0x7B4
0x021A23D4: 0x55C                0x021A23D8: 0x7B4        0x021A23DC: 0x4E4
```
Counts across ov3: `0x7B4` 32 sites, `0x4E4` 32 sites, `0x55C` 122 sites. **Next static step:**
disassemble the functions owning those pools — one of them is the generic
`container_for(zone_code)` selector, and pointing E1's enumeration at zone = banished is
almost certainly a matter of feeding it a different zone code rather than writing a new walker.

### B. GDB confirmation of the three leaves (needs the user)
Preflight per CLAUDE.md: melonDS GDB stub on port **3333**, an **active normal duel** (not a
puzzle — overlay 3 and the ov5 cave are not resident there), overlay 3 loaded. Breakpoints on
`0x0225026C` (E1 selector), `0x0225C3A6` (E2 replacement), `0x021B74B0` (E3 ATK):

| in-game action | expected to hit |
|---|---|
| summon Mermaid Archer | — |
| activate its equip effect on a face-up Lv ≤ 3 monster you control | `0x0225026C` |
| ATK recomputed/displayed while equipped (check it reads 2200) | `0x021B74B0` |
| destroy it while equipped — the "destroy the equipped monster instead?" prompt | `0x0225C3A6` |

The co-membership arguments above are strong (8/8 for E2), but ⚠️
`thumb-stack-based-switch-footgun`: register-only simulation of these switches has reported
the wrong leaf before. GDB is the arbiter.
melonDS **write-watchpoints do not fire** — use breakpoints. For bulk RAM reads prefer
savestate parsing (`otn_enhanced/tools/librarian_recorder.py.py`, auto-detect the RAM0 offset;
never hardcode it).

### C. ~~Then: the E2+E3 slice is ready to build~~ ✅ **BUILT** — `patch_sea_lancer.py`
1. `0x021B75F8` ← `7D 21 C9 00` (`movs r1,#0x7D; lsls r1,r1,#3` = +1000), ov3 file offset
   `0x00075EF8`. `verify()` asserts the twin at `0x021B7246` is still `32 21 09 01`, that the
   equal arm at `0x021B74B8` still branches to the leaf, and that the accumulator tail and the
   E2 switch literal are untouched.
2. Identity reskin of cid `0x1FFC`: Level 3 → **5**, ATK 1200 → **1300**, DEF 200 → **1000**,
   Sea Serpent → **Beast-Warrior**, WATER unchanged, name/desc in 8 languages.
   *(Korean name skipped — the original slot is 7 bytes and "Sea Lancer" needs 10.)*
3. E2: **no change**.

Registered in `apply_all_patches.py` as
`PatchStep("Mermaid Archer -> Sea Lancer (E2+E3+reskin; E1 pending)", _apply_sea_lancer)`,
placed after the Armory Arm fix and before the card-art step.

No ov5 cave slot, no phantom drop, no table resize, no registry row → nothing for the
allocation ledger, and no composition risk against any shipped card.

**Still to do: card art** (64x64 + 32x32) — `patch_card_art.py` handles the other donors;
Sea Lancer is not in its list yet, so she currently wears Mermaid Archer's picture.

## Savestates (captured — do not delete)

The user built a Mermaid Archer board and saved five states. They were captured as
`rom_safe_zone.ml3..ml7` and **copied to stable names** so future Safe Zone work cannot
overwrite them (the `working/` directory is gitignored, so these are local-only):

| file | board state |
|---|---|
| `data/over_the_nexus/working/sealancer_recon.ml3` | Mermaid Archer (z3) + Deep Sea Diva `0x1FFB` (z2) both face-up, **not yet equipped** |
| `sealancer_recon.ml4` | Deep Sea Diva **equipped** to Mermaid Archer (Diva gone from z2, zone `+0x08` bit `0x40000` set) |
| `sealancer_recon.ml5` | the "destroy the equipped monster instead?" **redirect prompt** |
| `sealancer_recon.ml6` | post-equip destruction (zone `+0x0C` 0 → `0x00000700`) |
| `sealancer_recon.ml7` | **Mermaid Archer banished** — the state that located the banished array |

Opponent board throughout: Gladiator Beast Laquari `0x1C76` (side 1, z2), a useful
never-equipped control. RAM0 file offset is `0x24` in all five.
`verify_knowledge --savestate data/over_the_nexus/working/sealancer_recon.ml7` → 0 FAIL.

---

## KB contributions made this session

`otn_enhanced/knowledge/author_facts.py` → regenerated; **102 facts, 87 PASS, 0 FAIL,
15 UNVERIFIED**; `check_allocations` clean (70 ov5 slots / 16 phantoms, ledger in sync).

| fact | grade |
|---|---|
| `dispatch.master_handler_row_layout` — cid at `+0x14`, not `+0x00` | VERIFIED |
| `dispatch.cls_table_bases` — four sorted cls segments + terminator (**promoted from UNVERIFIED**) | VERIFIED |
| `dispatch.step_table_replacement` — the "instead of being destroyed" dispatcher, 8/8 membership | VERIFIED |
| `dispatch.step_table_target_select` — the equip-target selector + predicate `0x021A3930` | VERIFIED |
| `battle.atk_delta_accumulator` — the `0x021B7226` accumulator tail idiom | VERIFIED |
| `battle.mermaid_archer_atk_leaf` — the +800 leaf, its exclusivity, and the look-alike twin | VERIFIED |
| `ram.banished_zone_array` — unknown offset, with experiment A above | UNVERIFIED |

### Step 2/3/3b/4 session — KB now **117 facts, 97 PASS, 0 FAIL, 20 UNVERIFIED**

| fact | grade |
|---|---|
| `dispatch.cls_table_selector` — descriptor `+0x05` picks the table; **cls3 `0x02279D74` count 0x308**; the cls0/1/2 names are proven, not inferred | VERIFIED |
| `dispatch.cls_slot_roles` — all five slot roles, the invoker wrappers, slot3's return code, the five disjoint address bands (2166 pointers) | VERIFIED |
| `dispatch.slot5_target_picker` — the shared `0x02234CA4` body, the prompt-code thunks, and the board-only limitation | VERIFIED |
| `dispatch.race_mask_fish_seaserpent_aqua` — the `0x4120` triple in Forgotten Temple's slot2 | VERIFIED |
| `dispatch.decompiled_cards_off_by_one` — `decompiled/cards/` attributes handlers to the previous card | UNVERIFIED |
| `dispatch.criteria_registry` — the fifth table `0x022713C4` (1388×12), its three shared banished handlers, and the `0x0223E5D0` thunk | VERIFIED |
| `dispatch.criteria_word_race_attribute` — race `>>3` / attribute `&7`; **Fish 8, Sea Serpent 5, Aqua 14**; Unicorn Beacon needs a bespoke handler | VERIFIED |
| `dispatch.criteria_registrar_predicate_list` — `0x0223C6AC` takes a predicate + value list; race-list predicate `0x0223C790`; Unicorn Beacon's `{11,16,0}` list; type is a bitfield | VERIFIED |
| `dispatch.banished_walker_and_candidate_buffer` — `0x0223C52C` walks `player+0x7B4` with zone `0x0F` hardcoded, **decodes only type bits 1/4/8/0x10 (no `0x40`)**, records into the candidate buffer via `0x02243B2C` | VERIFIED |
| `dispatch.offfield_picker_sequence` — the 3-sub-step list selection (`0x0219C430` mode 6, `0x0219C534`/`0x0219C510`, `0x02234880`) and **why it is not interchangeable with the board-mask path** | VERIFIED |
| `dispatch.activation_step_machine_protocol` — **return 0 = yield / nonzero = advance**, the free per-step scratch `[0x0229DD94+8]`, the 11 steps, and the `0x0225BD40` UI-request post + kind wrappers | VERIFIED |
| `dispatch.step_table_target_select` — **corrected**: the selector is step **5**, not step 7 | VERIFIED |
