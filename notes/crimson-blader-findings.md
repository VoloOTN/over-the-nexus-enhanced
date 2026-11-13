# Crimson Blader — findings

Status: **SHIPPED 2026-09-21. Stage A in-game confirmed by user 2026-09-21
(items 1-3, 5 by their report; item 4 by savestate, C9). Stage B in-game
confirmed by user 2026-09-21 ("All good - ship it", after confirming they ran
the Stage B duel). In `steps.STEPS` + `_verify_all_patches.SHIPPED`.**

**Two things are still NOT confirmed and must not be read as if they were:**
1. The two AI planner arms `0x0225D87A` / `0x0225E0DA` are **not built** (C15).
2. The `0x21` opposite-parity countdown has **never executed in-game** (C10) —
   it is thumbemu-proven only, and the ordinary test cannot reach it.

Card (source `scratch/ygoprodeck_cache.json`, id 80321197) — Synchro Monster,
Level 8, FIRE, Warrior, 2800 / 2600:

> 1 Tuner + 1 or more non-Tuner monsters
> If this card destroys an opponent's monster by battle and sends it to the
> Graveyard: Your opponent cannot Normal or Special Summon Level 5 or higher
> monsters during their next turn.

Donor: **Crimson Sunbird 0x1179** (effectless Fusion, Lv6 FIRE Winged Beast 2300/1800).

---

## Confirmed (this session, 2026-09-20)

### C1. 3DS: the card exists, the handler is useless
`3ds_extract/.../CARD_Indx_E.bin` index **4850** = "Crimson Blader";
`CARD_Prop.bin[4850] & 0x3FFF` = **0x2649**. Anchored: index 3094 →
"Dark Simorgh" → 0x1E5A, matching the NDS cid.
3DS on-event registry `0x6C335C` (stride 0x18) **row 248** =
`{0x2649, 0x0045AB5C, 0, 0x00404260, 0, 0}`. No row in the main effect-script
registry `0x686CBC`. Router `0x0045AB5C` is used by **no other row**; ARM disasm
shows a message-code switch terminating in `bl 0x0038BDD0` with packed nibbles —
a descriptor/score responder. **The 3DS gives no template for this effect.**

### C2. The attacker-side battle-destroy trigger table — ov3 `0x0226EA64`
Stride 4, `{u16 cid, u16 mask}`, sorted, **110 rows** (last row `0x0226EC18`,
cid 0x24DF). Count immediate `movs r2,#0x6E` @ `0x021CAAF4`; sole LDR literal
site `0x021CAAF2`; sole pool reference `0x021CAB90`.

Mask semantics, derived from membership over the whole table:

- **`0x000F` = "destroys an OPPONENT's monster by battle and sends it to the GY"**
  — Goyo Guardian 0x1E38, Hydro Genex 0x1E9A, Hydrogeddon 0x194F,
  Jurrac Spinos 0x2031, Flamvell Firedog 0x2088, Blackwing Shura 0x1FE3,
  Inferno 0x16C5, Truckroid 0x1A57, Fossil Tusker 0x1CAA, X-Saber Uruz 0x1D72,
  Chaos-End Master 0x1E9D, Jurrac Tyrannus 0x1FA3, Infernity Destroyer 0x2053,
  GB Samnite 0x1F59, Lightning Warrior 0x2220, Stygian Sergeants 0x2223.
- **`0x0007` = "destroys A monster by battle"** (either side) — Thought Ruler
  Archfiend 0x1E3A, Guardian Angel Joan 0x170B, Royal Knight 0x1A23,
  Darkblaze Dragon 0x1C4D, Iron Chain Repairman 0x1ECD, Flamvell Grunika 0x1F16.
- Other masks seen (0x0000/0x0001/0x0008/0x0009/0x0010/0x0018/0x001F/0x0020/
  0x0021/0x0027) not decoded.

**Four phantom rows at the head** — `0x0E12`(mask 0x000F), `0x0E8A`(0x0000),
`0x0E9C`(0x0008), `0x0EA7`(0x0000) @ `0x0226EA64..0x0226EA70`; none is in
`scratch/cid_to_name.json`. A count-neutral insert is therefore available.

⚠️ Independently corroborated: `notes/safe-zone-findings.md:596-608` and
`otn_enhanced/knowledge/author_facts.py:8212` call bit 3 of this table
"has a when-this-destroys-a-monster-by-battle trigger" (they quote Zombyra's row
address `0x0226EA7C`, not the base). This table has **never been banked as a KB
fact** — see *KB TODO*.

### C3. The summon-legality gate is ONE function
`0x021B9708(r0 = side, r1 = mode mask, r2 = cid)`.
Prologue `push {r4,r5,r6,r7,lr}; sub sp,#0x24; r5=r0; r6=r1; r4=r2`.
Deny leaf `0x021B972C` (`movs r0,#0`), allow leaf `0x021B9D98` (`movs r0,#1`),
epilogue `0x021B9D9A`.

Six tail-call wrappers (`ldr r3,=0x021B9709; movs r1,#mask; bx r3`):

| wrapper | mask | meaning | callers |
|---|---|---|---|
| `0x021B9E6C` | 1 | **Normal Summon** | `0x021AF104`, `0x0220D860`, `0x0225D80E` |
| `0x021B9DAC` | 2 | Set | `0x0220D86A`, `0x0225D864` |
| `0x021B9E78` | 4 | Flip Summon | `0x021AEFD4` |
| `0x021B9EC0` | 8 (+cid in r2) | **Special Summon** | 16 sites |
| `0x021B9ECC` | 8 (r2 = 0) | **Special Summon** | 125 sites |
| `0x021B9EF0` | 0x18 | Synchro Summon | `0x0224956C`, `0x02249F14` |

Bit meanings were read off the cards checked in each arm: bit 0 Narrow Pass
0x15A9 / Reptilianne Servant 0x21B2; bit 1 Light of Intervention 0x135D;
mask 0xB Non Aggression Area 0x15AD ("Normal Summon, Set and/or Special
Summon"); mask 0x10 Discord 0x20A6 / Dark Highlander 0x2350 ("cannot Synchro
Summon"). **`0x021B9EF0` passes 0x18, so bit 3 already covers Synchro Summons.**

### C4. Non Aggression Area 0x15AD is the duration template
cls0 record **[406] @ `0x02280C5C`** =
`{0x15AD, 0x02216A39, 0, 0x021F679D, 0x021E4EA5, 0}`.
Handler `0x02216A38`, twelve instructions:

```
push {r3,lr}
r2 = r0                 ; effect descriptor
r1 = [r2+2]             ; controller side
r0 = 1 - r1             ; the OPPONENT's side
r3 = 0
r1 = [r2+0]             ; its own cid (u16)
r2 = 0x11               ; kind 1 | countdown 1
bl 0x021D2584
r0 = 0 ; pop
```

`0x021D2584(side, key, kind, 0)` tail-calls
`0x021C479C(side, 0x0B, key, kind, [sp]=0)` — posts a node on pseudo-zone 0x0B.
The gate reads it back at `0x021B9B90`:

```
movs r1,#0xb ; tst r6,r1 ; beq skip
ldr r2,=0x15AD ; r0 = side ; bl 0x021A151C ; bne -> DENY
```

Kind byte `0x11` = kind 1 with a 1-turn countdown in the high nibble =
"until the end of their next turn" (`rider.turn_sweeper`, VERIFIED;
`patch_azure_eyes.py:470-491` uses `0x12` and is in-game confirmed 2026-08-24).
**Crimson Blader's duration is identical to Non Aggression Area's.**

### C5. Donor vetting — Crimson Sunbird 0x1179 (LEVEL 6+ constraint)
The user's constraint is **effectless Fusion, Level 6 or higher, only**. The full
card_type-5 pool is 39 cards; **16 are Level 6+**, and four of those are already
claimed (0x11A3 accel_synchron, 0x126F accel_synchro_stardust, 0x13C6
scrap_archfiend, 0x0FCB orient_dragon).

Exactly **two** unclaimed Lv6+ members have a clean `donor_scan`
(bind=1 / 0 ambiguous ARM9 hits / 0 code-region hits / 0 CPU decks):

| cid | card | lvl | stats | fusion row | materials |
|---|---|---|---|---|---|
| **0x1179** | **Crimson Sunbird** | 6 | FIRE Winged Beast 2300/1800 | A[31] @`0x02270C8C` | Faith Bird 0x1023 + **0x1178** |
| 0x1127 | Bickuribox | 7 | DARK Fiend 2300/2000 | A[23] @`0x02270C4C` | Crass Clown 0x1005 + Dream Clown 0x101E |

**Tiebreaker, and it is decisive: `0x1178` has NO card_prop record** (checked
against all 4305 records in the stock ROM). Crimson Sunbird's fusion is therefore
already unperformable, so blanking its material columns — which the recipe step
must do, because the CPU planner reads the table without an `is_fusion` gate —
costs nothing. Blanking Bickuribox's would have removed a real, performable
Crass Clown + Dream Clown fusion.

Both are `result`-column only in their recipe (neither is a material of any other
fusion), both have zero flags-table and zero cls1 rows, and both were checked in
**rom.nds AND rom_all_patches.nds**.
Name floor for 0x1179 is 6 B (Japanese/Korean) against a 14 B name — irrelevant,
because the text goes through `card_text.CARD_TEXT`'s index-order re-emit.

⚠️ Earlier in this session the donor was **Cyber Saurus 0x11A2 (Level 5)**, which
the user rejected on the Level 6+ constraint. It is equally clean and stays
unclaimed if a Lv5 donor is ever acceptable.

### C6. Stage A is built and statically clean — **AWAITING IN-GAME TEST**
`otn_enhanced/cards/crimson_blader.py` +
`_build_crimson_blader.py`. ROM
`data/over_the_nexus/working/rom_crimson_blader.nds`,
sha256 `f6c482a28707fe5d826d7c84a5c3889c5325bad1bccb91ec3fc3ed814ffefb82`.
16/16 static checks PASS, allocation guard clean (257 ov5 slots, 256 phantom
claims, no overlaps). **Not** wired into `steps.STEPS` / `SHIPPED`.

Parts: A card_prop ← Laval Twin Slayer 0x23FE (already FIRE/Warrior), Lv8
2800/2600 · B card_genre `0x20200000` → `0x1000200000` · C fusion A[31]
@`0x02270C8C` materials → `0x3FFF` · D flags row `{0x1179, 0x000F}` over phantom
`0x0E9C` · E cls1 `{0x1179, 0, CAVE_CB_LOCK|1, 0,0,0,0}` over phantom `0x1197` ·
F the 44-byte ov5 stub at `CAVE_CB_LOCK = 0x023A0FD0`.

### C7. A cls1 resolver may be phase-agnostic and return 0
`0x02206138`, the handler shared by **Hydro Genex 0x1E9A and the donor-family
card Lightning Warrior 0x2220** — both cls1 rows of shape `{cid,0,handler,0,0,0,0}`
on this very trigger — never reads the resolver phase `[0x0229AAFC+0x70]`, takes
its side from `[desc+2]`, and ends `movs r0,#0 ; pop`. Non Aggression Area's
cls0 handler `0x02216A38` has exactly the same shape. So the cls0→cls1 protocol
question in Open Question 1 is answered for *this* handler shape: a
phase-agnostic "do it once, return 0" resolver is what cls1 already uses here.

### C8. Countdown 1 is WRONG for a card that can trigger on either turn
Non Aggression Area hardcodes kind `0x11` because it can only ever be activated
during its controller's **Standby Phase**. Crimson Blader also fires when the
opponent attacks into it. A node posted on the opponent's own turn with
countdown 1 is swept at the end of that same turn and would be gone before their
next turn began. The stub therefore reads the turn player from
**`[0x0229DD14 + 0x34]`** (the side the gate compares against the summoner at
`0x021B9B3A`) and posts kind `0x11` on the controller's own turn, `0x21` on the
opponent's. All four (controller, turn player) combinations are proven **by
execution** of the installed stub with `scratch/thumbemu.py` in
`_build_crimson_blader.py::prove_lock_stub`.

### C9. Stage A in-game test — PASSED, and the lock node is proven to land LIVE
User's verbatim report, 2026-09-21: items **1, 2, 3 and 5 "Confirmed"**; item 4
*"The card \"activated\" but I don't know what happened. No freeze occured"*.

Item 4 settled offline from the two savestates the user supplied,
`data/over_the_nexus/working/rom_crimson_blader.ml2` (before the battle
destruction) and `.ml3` (after). Both parse with main RAM at file offset
**0x24** (auto-detected via the `0x021A25A0` anchor, per
`melonds-savestate-ram-offset`), and the 44 ov5 bytes at
`CAVE_CB_LOCK = 0x023A0FD0` are **identical in both states and equal to the
installed stub** — so overlay 5 was resident and this was a normal duel, not a
puzzle.

Node-pool layout used for the read, disassembled this session from
`0x021A1430` / `0x021A1238` (stock `rom.nds`, overlay 3):

- pool base **`0x0229D33C`**, record stride **0xA**;
- record = `{+0x0 u16 key, +0x2 u16 kind, +0x4 u16, +0x6 u16, +0x8 u16 next}`;
- chain head = u16 at **`0x0229ACD2 + (side & 1) * 0xB3C + zone * 0x14`**,
  index 0 terminates;
- the walker accepts a node only when `kind & 0xF < 6` (`lsl #28 ; lsr #28 ;
  cmp #6 ; bcs`) — so `0x11` and `0x21` both pass.

The delta across the battle destruction, with the turn player
`[0x0229DD14 + 0x34] = 0` (the user's side) in **both** states:

```
side 1 zone 0x0B  [11] key=0x1179 kind=0x0011  <-- NEW in .ml3, absent in .ml2
```

That is exactly what part F is supposed to post: **the opponent's side**
(controller = side 0 → node on side 1), pseudo-zone **0x0B**, key **`0x1179`**,
kind **`0x11`** = kind 1 with countdown 1 — the controller's-own-turn branch of
the C8 turn-player test, now confirmed by **live execution**, not just by
`thumbemu`. The `0x21` (opponent's turn) branch is still only thumbemu-proven.

Every other delta is unrelated and accounted for: `0x197D` Tualatin's zone-2
node disappears (that is the destroyed monster), `0x2092` is the KB's
`battle.attacked_marker_rider` sentinel appearing on the attack, and `0x1EF4` /
`0x22F4` are pre-existing battle-phase riders on the user's own side.

**Consequence: parts A-F of Stage A all work. The "activation" the user saw is
the engine's ordinary cls1 effect-activation presentation for record E; the
resolver returns 0 and the only side effect is the hidden node. Nothing in
Stage A needs fixing.** Open Question 6 is also closed in passing: the
flags-table row `{0x1179, 0x000F}` (part D) really does drive the trigger on its
own — nothing else in the ROM references `0x1179` as a trigger source.

### C10. The `0x21` (opponent's-turn) branch is UNTESTED, and the obvious test is impossible
User, 2026-09-21: *"that is an impossible to test because the CPU would never
attack into a monster stronger than it"* — correct, and it kills Stage B in-game
test 5 as written. Crimson Blader must be in **Attack** position for the attacker
to be destroyed at all (a defending monster's DEF never destroys an attacker), so
the test needs a CPU monster with ATK < 2800 to attack into it, which the AI will
never choose.

Two consequences, and **both are still open**:

- **(a) UNPROVEN — does the `0x0226EA64` mask `0x000F` trigger fire when Crimson
  Blader is the DEFENDER?** The mask means "destroys an opponent's monster by
  battle and sends it to the GY" with no turn qualifier, and the printed text has
  none either, but this has never been observed. If it does not fire, the card is
  **bugged**, not merely deviating — the printed effect covers that case.
- **(b) The `0x21` countdown branch is only `thumbemu`-proven**, never executed
  live. C9 proved the `0x11` branch live; the other arm of the same `cmp` has not
  run on hardware.

**The workaround — force the attack.** Both cards exist in this ROM and the text
below is from `scratch/ygoprodeck_cache.json`, not recall:

- **Battle Mania, cid 7918** (Normal Trap) — *"Activate only during your
  opponent's Standby Phase. All face-up monsters your opponent controls are
  changed to Attack Position, and cannot change their battle positions this turn.
  All monsters your opponent currently controls must attack this turn, if able."*
  **Preferred**: it removes AI judgement from the loop entirely and yields several
  forced attacks into the 2800 body in one turn.
- **Shrink, cid 5355** (Quick-Play) — *"Target 1 face-up monster on the field; its
  original ATK becomes halved until the end of this turn."* Fallback: let the CPU
  attack Crimson Blader with something >2800, then halve it mid-battle. Simpler
  engine mechanism, but depends on the CPU owning a big enough monster and
  choosing to swing.

**This test does NOT require Stage B.** Nothing reads the node yet, so the
`0x21` branch has no visible in-game consequence — the read is a savestate pair
across the forced attack, parsed exactly as C9 parsed `.ml2`/`.ml3`. Expect
`side 1 zone 0x0B key=0x1179 kind=0x0021` to appear. Zero code, zero build.

### C11. ⭐ THE PRECEDENT: Worm Bait `0x2146` is Crimson Blader's clause 3, already native
**This replaces the B1/B2 hypothesis. Found on Stage B's first experiment, before
writing any code.**

Printed text, `scratch/ygoprodeck_cache.json`:

> **Worm Bait** — If you control an Insect monster: Special Summon 2 "Worm
> Tokens" (Insect/EARTH/Level 1/ATK 0/DEF 0). **You cannot Normal or Special
> Summon any Level 3 or 4 monsters the turn you activate this card.**

That is Crimson Blader's clause 3 with a different comparison and a different
side. It is implemented as **a pseudo-zone `0x0B` node read plus a Level test**
— the same node machinery Stage A already writes to.

The Normal-Summon arm, inside the predicate `0x021AF0A8(r0 = side, r1 = hand
slot)`, disassembled this session from stock `rom.nds` ov3:

```
0x021AF176:  4a13      ldr  r2,=0x2146        ; the lock key
0x021AF178:  1c28      adds r0,r5,#0          ; r0 = side (the SUMMONER)
0x021AF17A:  210b      movs r1,#0x0B          ; pseudo-zone 0x0B
0x021AF17C:  2301      movs r3,#1             ; kind filter
0x021AF17E:  bl 0x021A14E8                    ; kind-filtered node query
0x021AF182:  2800      cmp  r0,#0
0x021AF184:  d008      beq  0x021AF198        ; no node -> allow
0x021AF186:  1c28      adds r0,r5,#0
0x021AF188:  1c31      adds r1,r6,#0          ; (side, hand slot)
0x021AF18A:  bl 0x021B8064                    ; LEVEL_OF_ZONE
0x021AF18E:  1ec0      subs r0,r0,#3
0x021AF190:  2801      cmp  r0,#1
0x021AF192:  d801      bhi  0x021AF198        ; Level not in {3,4} -> allow
0x021AF194:  2000      movs r0,#0             ; DENY
0x021AF196:  bdf8      pop  {r3-r7,pc}
```

**Every code site in ov3 that loads the key `0x2146`** (found by scanning all
aligned pool words and resolving the PC-relative `LDR` that feeds each):

| site | enclosing func | role |
|---|---|---|
| `0x021AF176` | `0x021AF0A8` | **Normal Summon**, per hand slot (above) |
| `0x021BA1F0` | ~`0x021BA1xx` | **Special Summon** — adjacent to the B2 chain `0x021BA69C` |
| `0x021C24FE` | ~`0x021C24xx` | third site, loads into **r6** — role not yet read |
| `0x0225D87A` | `0x0225D73C` | **AI** mirror of the Normal/Set path |
| `0x0225E0DA` | ~`0x0225Exx` | **AI** second site |

Heat Wave `0x23B3` ("Neither player can Normal or Special Summon Effect
Monsters") is enforced by the **same shape at a parallel set of sites** —
`0x021AF198`, `0x021BA378`, `0x0220EAE8`, `0x0225D8E0` — which corroborates that
this small site-set *is* the engine's summon-restriction enforcement surface. Its
Normal arm queries **side 0 hardcoded** (`movs r0,#0` @ `0x021AF19A`), the
encoding of "neither player".

**Consequence for Stage B.** The architecture is no longer a hypothesis: add a
parallel arm keyed `0x1179` at each `0x2146` site, with the Level test inverted
to `Level >= 5` and the side taken as the summoner's own side (Stage A already
posts the node on the *opponent's* side, so a plain `side` query is correct —
the node is only present for the player who is locked). The B1 hook at
`0x021AF104` and the B2 hook at `0x021BA69C` are **superseded** and should not be
built; `0x021AF104` is in the same function but several instructions too early,
before the Level is available.

Open: the roles of `0x021C24FE` and `0x0225E0DA`, and whether the two AI sites
must be patched for the CPU to respect the lock (they almost certainly must, or
the AI will attempt illegal summons).

### C12. The complete enforcement surface for "cannot summon Level X monsters"
All five `0x2146` sites read this session from stock `rom.nds` ov3. Every one has
the same shape: **query a pseudo-zone `0x0B` node, then test the Level.**

| # | site | enclosing func | path | how the Level is obtained |
|---|---|---|---|---|
| 1 | `0x021AF176` | `0x021AF0A8` | **Normal Summon**, per hand slot (6 callers) | `bl 0x021B8064(side, hand slot)` inline |
| 2 | `0x021BA1F0` | **`0x021BA1E8`** | **Special Summon** | **passed in as r1** |
| 3 | `0x021C24FE` | `0x021C2298` | kind filter **2** (not 1), gated on turn player, tail-calls `0x0219F190` | `bl 0x021B8064(r7, [sp+0x18])` |
| 4 | `0x0225D87A` | `0x0225D73C` | **AI** Normal/Set planner | `bl 0x021B20AC` → `[sp+0x44]` |
| 5 | `0x0225E0DA` | ~`0x0225Exxx` | **AI** second planner | `[sp+0x44]` |

**`0x021BA1E8` is the prize.** A 0x20-byte standalone function with the exact
contract Crimson Blader needs:

```
0x021BA1E8: b508      push {r3,lr}
0x021BA1EA: 1ec9      subs r1,r1,#3        ; r1 = LEVEL, passed in by the caller
0x021BA1EC: 2901      cmp  r1,#1
0x021BA1EE: d808      bhi  0x021BA202      ; Level not 3/4 -> ALLOW
0x021BA1F0: 4a05      ldr  r2,=0x2146
0x021BA1F2: 210b      movs r1,#0x0B
0x021BA1F4: 2301      movs r3,#1
0x021BA1F6: bl 0x021A14E8
0x021BA1FA: 2800      cmp  r0,#0
0x021BA1FC: d001      beq  0x021BA202
0x021BA1FE: 2000      movs r0,#0 ; pop     ; DENY
0x021BA202: 2001      movs r0,#1 ; pop     ; ALLOW
```

`0x021BA1E8(r0 = side, r1 = Level) -> 1 allow / 0 deny`. Its feeder is the
**summon-restriction aggregator `0x021BA258(r0 = side, r1 = cid, r2 = ref,
r3 = location code)`**, which resolves the Level into `[sp+0x8]` — via
`0x0202ABD8` `LEVEL_OF_CID` for a cid, or `0x021B20AC(side, ref)` when the
location code is `0xB` and a live ref exists, i.e. the card's CURRENT Level —
and then calls it at `0x021BA368`. `0x021BA258` has **11 callers**, covering the
Special-Summon surface the prompt's B2 hook was trying to reach piecemeal:

```
0x021B1D48 (~0x021B1BE8)   0x021BA430   0x021BA45E   0x021BA7EC (~0x021BA69C)
0x021F07EC (~0x021F072C)   0x02200D8C   0x022074D0   0x02207C88   0x02207D8A
0x0223BBB2 (~0x0223BA24, the Deck walker)   0x0225E59E (~0x0225E51C, hand-SS)
```

Note `0x021BA7EC` is inside `0x021BA69C` — **the prompt's B2 target is itself a
caller of the aggregator**, i.e. B2 would have hooked one branch of a tree whose
trunk is `0x021BA258`. Hooking `0x021BA1E8` is the root-cause shape.

**The AI planner sites matter MOST, not least.** Crimson Blader's lock applies to
the *opponent*, who in a normal duel is the CPU. Sites 4 and 5 are how the AI
decides what it may play; sites 1 and 2 are enforcement. Both halves are needed —
enforcement alone risks the AI stalling on a play it believes is legal.
Corroboration that site 5 is the right neighbourhood: `0x0225E0F6` already
contains `cmp r0,#5 ; blt` — **the exact Level >= 5 comparison this card needs**,
serving some other restriction.

Also seen: site 4 carries a cid exemption inside the Worm Bait arm
(`ldr r0,=0x1FDB ; cmp r4,r0` @ `0x0225D88A`).

**Consequence — the Stage B shape.** One shared ov5 stub with `0x021BA1E8`'s
exact contract `(r0 = side, r1 = Level) -> 1/0`, implementing Worm Bait's rule
AND Crimson Blader's; `0x021BA1E8` becomes a trampoline to it; sites 1, 4 and 5
get their inline arms rewritten as a call to it with per-site glue to load the
side and Level. Site 3's role must be read before deciding whether it needs an
arm. **NOT YET BUILT — awaiting user approval of the donor-free overlay-3 edits.**

### Prompt open questions, resolved by C11/C12
- **OQ1 "is `0x021AF0A8` enforcing or only UI?"** — moot. It is where Konami put
  Worm Bait's Normal-Summon arm, so it is the Normal lock site by precedent. The
  AI has a separate planner path (site 4) which must also be patched.
- **OQ2 "which side is the summoner at `0x021BA69C`?"** — moot, B2 superseded.
- **OQ3 "does `0x021BA69C` see effect-driven Special Summons?"** — superseded:
  the trunk `0x021BA258` has 11 callers including the Deck walker and hand-SS.
- **OQ4 "are pseudo-zone `0x0B` nodes swept?"** — STILL OPEN, and now more
  important, since the whole lock hangs on the node expiring.

### C13. Site 3 is a WRITER, not an enforcement arm — and OQ4 is CLOSED
**Site 3 `0x021C24FE` needs no Crimson Blader arm.** `0x0219F190(r0 = side,
r1 = zone, r2 = kind, r3 = key)` is the **node allocator/linker**, disassembled
this session: it takes a free index from `0x0219F020`, forms the record address
`0x0229D33C + idx * 0xA`, forms the chain head
`0x0229AC94 + (side & 1) * 0xB3C + 0x3E + zone * 0x14`, and bails with `-1` past
index `0x100`. **77 callers** — it is the generic attach primitive.

Site 3, inside `0x021C2298` (**one** caller, `0x021C3EC2` in `0x021C3C3C`),
therefore reads as: on the controller's own turn (`[0x0229DD14+0x34]` vs
`[sp+0x14]`), if no **kind-2** `0x2146` node exists yet and the Level is 3 or 4,
**post** `0x0219F190(side, 0x0B, 2, 0x2146)`. That is a once-per-turn marker
write, not a restriction read. Excluded from the patch set.

**OQ4 — are pseudo-zone `0x0B` nodes swept? YES. Closed offline, no savestate
spent.** `0x0219F9E0` disassembled this session:

```
0x0219F9F0:  2501      movs r5,#1              ; index = 1
0x0219FA0C:  200a      movs r0,#0xA
0x0219FA10:  4341      mul  r1,r0              ; idx * 0xA
0x0219FA12:  4869      ldr  r0,=0x0229D33C     ; POOL BASE -- no chain head, no zone
0x0219FA14:  1844      adds r4,r0,r1
0x0219FA16:  8860      ldrh r0,[r4,#0x2]       ; the kind byte
0x0219FA18:  0701 0f09 lsl/lsr #28             ; low nibble
0x0219FA1C:  2908      cmp  r1,#8
0x0219FA1E:  d866      bhi  0x0219FAEE         ; -> 9-arm PC-relative jump table @0x0219FA2C
```

It walks the pool **by index**, reading `[rec+2]` directly — it never consults a
chain head and never sees a zone. Jump table resolved: nibble 0/4/5 skip, **1 and
2 both land on the countdown arm `0x0219FA3E`**, 3 → `0x0219FA5C`, 6/7/8 →
`0x0219FA6C`. The countdown arm:

```
0x0219FA3E:  lsl r1,r0,#24 ; lsr r1,r1,#28     ; r1 = HIGH nibble = the countdown
0x0219FA42:  beq 0x0219FA56                    ; countdown 0 -> DELETE
0x0219FA44:  subs r1,r1,#1                     ; else DECREMENT
0x0219FA52:  strh r0,[r4,#0x2]                 ; write back
```

Crimson Blader's node is kind `0x11` → low nibble **1** → the countdown arm. So
it decrements and expires like any other rider. Corroborated by the existing
VERIFIED KB fact `rider.turn_sweeper`, whose proof
`bl_callers(0x0219F9E0) == [0x021C1358]` matches this session's independent scan
exactly; `0x021C12F0` is the end-of-turn animation opcode-3 handler.

Lifetime check against C8's design, assuming one sweep per turn end:
`0x11` posted on the controller's turn → end of that turn `1 -> 0` → present for
the whole of the opponent's next turn → deleted at its end. ✓
`0x21` posted on the opponent's turn → `2 -> 1` → `1 -> 0` → present for the
whole of the opponent's *next* turn. ✓ Both match the printed text.

### C14. Stage B pre-build risk checklist — all PROVEN, awaiting user sign-off
Per CLAUDE.md, every line `PROVEN` (with evidence) or `ASSUMED`:

1. **Per-cid gates on the donor `0x1179`** — `PROVEN` clean in Stage A (C5,
   `donor_scan` bind=1, 0 ambiguous ARM9 hits, 0 code-region hits, 0 CPU decks).
   **New for Stage B: `0x1179` as a NODE KEY is collision-free** — a scan of all
   aligned u32 pool words in ov3 finds **0 occurrences** of `0x00001179`, so no
   existing code queries or posts that key. No shadowing possible.
2. **The zone the effect searches** — `PROVEN` pseudo-zone **`0x0B`**, two ways:
   C9's live savestate shows the node landing on `side 1 zone 0x0B`, and all four
   enforcement arms query `0x021A14E8(side, 0x0B, key, kind)`.
3. **Donor blob lengths** — `PROVEN` in Stage A; text goes through
   `card_text.CARD_TEXT`'s index-order re-emit, so no in-place slot limit.
4. **Once-per-turn stamp** — **N/A**, the card has no once-per-turn clause.
5. **Are the four arms safely rewritable?** — `PROVEN`. A scan of every Thumb
   `B` / `Bcc` / `BL` in ov3 for targets landing strictly inside each arm finds
   **0 external inward branches** to all four ranges
   (`0x021AF176..0x021AF198`, `0x021BA1E8..0x021BA206`,
   `0x0225D87A..0x0225D8A0`, `0x0225E0DA..0x0225E0F6`). Each block can be
   rewritten as a unit.
6. **Side semantics** — `PROVEN`. Stage A posts the node on the **opponent's**
   side (C9: controller side 0 → node on side 1). The arms query the
   **summoner's own** side, so the locked player finds their own node. Correct
   without any inversion.
7. **Cave headroom** — `PROVEN` from the live source, not a comment:
   `OV5_RAM_BASE 0x022C5900 + OV5_NEW_LEN 0xE4820` = ceiling **`0x023AA120`**;
   `CAVE_FREE = 0x023A1000`; free tail = **`0x9120` (37152) bytes**. One shared
   stub needs well under 0x80.

### C15. Stage B BUILT (arms 1+2) — IN-GAME CONFIRMED BY USER 2026-09-21, SHIPPED
`patch_crimson_blader.py` parts **G / H**, ROM
`data/over_the_nexus/working/rom_crimson_blader.nds`,
sha256 `ec8567ae02358081e65ebf0706533ea9d695839080412f99432575e0075aae08`.
**28/28 static PASS**, allocation guard clean (258 ov5 slots, no overlaps).
Still **not** in `steps.STEPS` / `SHIPPED`.

- **`CAVE_CB_GATE = 0x023A1000`**, 104 B in an `0x80`-byte reserve, `CAVE_FREE`
  bumped to `0x023A1080`, ledger re-emitted. Signature
  `(r0 = side, r1 = Level-or-slot, r2 = unused, r3 = flags) -> 1 allow / 0 deny`;
  `flags` bit 0 = "r1 is a hand slot, resolve via `0x021B8064`", bit 1 = "skip
  the Worm Bait arm" (for the AI arms' `0x1FDB` exemption, unused so far).
  It answers **both** locks — Worm Bait Level 3-4 and Crimson Blader Level >= 5.
- **Arm G** `0x021AF176..0x021AF198` (34 B, exact fit): loads side + hand slot,
  `bl` to the gate, denies with `movs r0,#0 ; pop`, else NOPs through to
  `0x021AF198` (the Heat Wave arm) — the original fall-through contract.
- **Arm H** `0x021BA1E8..0x021BA206` (30 B, exact fit): Konami's whole
  `(side, Level)` function replaced by `push {r4,lr} ; movs r2,#0 ; movs r3,#0 ;
  bl gate ; pop {r4,pc}`.
- Both arms assert the **stock bytes** before writing, so a drift or a second
  patch touching the same range aborts the build instead of corrupting it.
- `thumb_asm.asm` supports neither `bl <abs>` nor `bhi`, so the arms use a
  hand-emitted two-halfword ARMv4T `BL` (`_bl()`) and the Worm Bait Level test is
  expressed as signed `cmp #3 / blt` + `cmp #4 / bgt` — equivalent for Level >= 0.
- Register safety `PROVEN`: the stub keeps side in r4, Level in r5, flags in r6
  across both calls; `0x021B8064` tail-calls a `push {r4-r7,lr}` body and
  `0x021A14E8` pushes `{r4,r5,r6,lr}`, so r4-r6 survive. The stub uses no r7.

**PROVEN BY EXECUTION** (`scratch/thumbemu.py`, `_build_crimson_blader.py::
prove_gate_stub`) against the **installed** bytes, 18 cases x both sides = 36,
all PASS, with the node query intercepted and asserted to be called as
`(side, 0x0B, key, 1)`:

| case | result |
|---|---|
| no lock, Lv4 / Lv8 | allow |
| Crimson node, Lv5 / Lv8 | **deny** |
| Crimson node, Lv4 / Lv1 | allow ← the clause that distinguishes it from a blanket lock |
| Worm Bait node, Lv3 / Lv4 | **deny** ← the shipped card still works |
| Worm Bait node, Lv5 / Lv2 | allow |
| both nodes, Lv4 / Lv6 | deny; Lv2 allow |
| exemption flag, Lv3 | allow (Worm Bait skipped) |
| slot-resolve flag, Lv7 / Lv3 | deny via `0x021B8064` |

**NOT BUILT — the two AI planner arms** `0x0225D87A` and `0x0225E0DA`. Their
deny signal is `movs r7,#0`, a local flag in functions read only ~20
instructions deep this session. Patching a hook whose contract is not fully
understood is the blind build-test cycle CLAUDE.md forbids, so they are left for
a session that reads `0x0225D73C` end to end. **Consequence: the lock is
enforced against the CPU (arms G/H are the real gates) but the CPU's planner
does not yet know about it, so it may propose a Level 5+ summon and be refused.**
Watch for that in the in-game test and report it verbatim — it is expected, not
a new bug.

## Ruled Out

- **The 3DS build as an architecture source for this card.** Its handler is
  bespoke and is not a restriction primitive (C1). Checked first, per CLAUDE.md;
  the answer is "no help", which is itself worth not re-deriving.
- **`list106 0x0226E990` as the trigger.** That list is the **victim** side
  ("*this card* destroyed by battle and sent to the GY" — Colossal Fighter
  0x1E12, Lord Poison 0x156D, Sun Dragon Inti 0x21CD;
  `event.leave_dispatcher_three_registers`, VERIFIED). Crimson Blader needs the
  **attacker** side, which is C2's table.
- **A Synchro summon-procedure registry.** There is none
  (`synchro.no_cid_whitelist`, VERIFIED). `0x0228F158` is the **hand-SS**
  procedure registry (`handss.summon_procedure_registry`), and
  `donor_scan.py:93` mislabels the range — do not add a row there.
- **A main-deck donor.** No patch in this repo has ever moved a card between the
  main deck and the Extra Deck; the Fusion→Synchro recipe is safe precisely
  because `is_extra_deck 0x0202307C` is left unchanged.
- **Putting the Level-5 test inside the gate `0x021B9708`.** The Normal-Summon
  wrapper `0x021B9E6C` and the dominant Special-Summon wrapper `0x021B9ECC`
  (125 callers) both pass `r2 = 0`, so the gate is cid-blind on exactly the two
  paths the card needs. The test has to live at a call site where the cid is
  live.
- **Deny key `0x0E3C` as the primary mechanism.** The gate already queries this
  dead phantom at `0x021B9C94` in its shared Normal+Special tail
  (`movs r1,#0xb; bl 0x021A1430; bne -> deny`), which would lock both paths with
  zero overlay-3 edits — but it is a **blanket** lock with nowhere to hang the
  Level-5 condition. Kept as a fallback only. Its deadness is UNVERIFIED.

---

## Open Questions

1. Is `0x02216A39` (a **cls0** handler) invocable from a **cls1** record? If the
   invocation protocols differ, fall back to a ~24 B Thumb-1 ov5 stub making the
   same `0x021D2584` call.
2. ~~Which cls1 phantom row is free?~~ **CLOSED.** `0x1197` — one of 123
   single-row phantoms in cls1 (base `0x022860D4`, stride 0x18, count 0x535), not
   named anywhere in `check_allocations.py` or `allocations.yaml`, present in
   **both** `rom.nds` and `rom_all_patches.nds`. Claimed as
   `("cls1_table", 0x1197, "crimson_blader")`.
3. Is `0x021AF104` the *enforcing* Normal-Summon gate or a UI predicate? The
   other two callers of the wrapper are `0x0220D860` (command path) and
   `0x0225D80E` (AI).
   Partly answered: `0x021AF104` sits inside **`0x021AF0A8(r0 = side, r1 = hand
   slot)`**, a per-hand-slot "can this card be Normal Summoned" predicate with
   **six** callers — `0x021AF1DE`, `0x021F2C96`, `0x021FCE76`, `0x02200CA4`,
   `0x0220D8EC`, `0x0224C196` — i.e. the UI command path *and* five others. So
   hooking the single `bl 0x021B9E6C` inside it covers all six at once, which is
   the root-cause shape. Whether any Normal Summon can reach the field WITHOUT
   passing through `0x021AF0A8` is still open and is Stage B's first experiment.
4. Is `0x021BA69C` reached by effect-driven Special Summons and by
   Synchro/Fusion/Ritual Summons, or only by the Deck/hand candidate walkers?
5. Are pseudo-zone `0x0B` nodes swept by `0x0219F9E0`? It walks the node pool by
   index 1..0xFF rather than by chain, so it should be zone-agnostic, and Pot of
   Duality relies on it — but the KB's proof only exercises monster-zone chains.
6. ~~Does the flags-table row alone drive the trigger?~~ **CLOSED by C9** — it
   does. Row D fired the cls1 record and the node landed.

---

## Next Experiment

**Stage B read side — architecture settled by C11/C12, build NOT started,
awaiting user approval.** Before any Thumb, two things to read:

1. **Site 3 `0x021C2298`** — why kind filter **2** instead of 1, and what
   `0x0219F190(side, 0x0B, 2, 0x2146)` does. If it is the expiry/consume path
   rather than an enforcement arm, it needs no Crimson Blader arm.
2. **OQ4, the sweep.** Confirm pseudo-zone `0x0B` nodes are swept by
   `0x0219F9E0`. The whole lock hangs on the `0x11`/`0x21` countdown expiring;
   if they are not swept the lock is permanent, which is a bug. Cheapest read:
   a savestate from the turn after the lock was posted — the `0x1179` node's
   kind byte should have decremented, then the node should vanish.

Then the pre-build risk checklist for four overlay-3 inline-arm rewrites plus
one shared ov5 stub, and user sign-off, before a single byte is emitted.

---

## KB TODO (author_facts.py)

1. `event.battle_destroy_flags_table` — C2 (never banked).
2. `summon.legality_gate_and_mode_bits` — C3, including the `r2 = 0`
   cid-blindness.
3. `summon.non_aggression_area_lock` — C4.
4. `card.crimson_blader_3ds` — C1, including the negative result.
5. Correct the `0x0228F158` "Synchro summon-procedure registry" mislabel; keep
   the old claim as UNVERIFIED with `corrected_by:`.
