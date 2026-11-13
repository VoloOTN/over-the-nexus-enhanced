# Safe Zone — findings

Session 2026-07-21. Donor: **Battle-Scarred `0x16A2`** (keep-cid).

> ## ✅ STATUS: COMPLETE — all 7 clauses IN-GAME CONFIRMED
>
> Shipped as `otn_enhanced/cards/safe_zone.py`; chained into
> `apply_all_patches.py` at step 22 of 27. `verify()` **25/25 PASS** both
> standalone (`rom_safe_zone.nds`) and inside the combined `rom_all_patches.nds`.
>
> **Read the retraction notices before trusting any early section.** This file is
> a working log kept in write-order, so several entries in *## Confirmed* below
> were later proved wrong and are marked **SUPERSEDED** in place — deliberately,
> so the corrections survive. In particular:
> * the donor was **changed from Shadow Spell `0x1243` to Battle-Scarred**;
> * the clause-3/4 host is **`0x021B05CC`**, not the Forbidden-Lance chain;
> * the clause-5 host is **`0x021A6680`**, not the attack-eligibility chain;
> * `0x021A1430` vs `0x021A0950` is a **silent-no-op trap** — see the walker
>   families section.
>
> | Clause | Mechanism | |
> |---|---|---|
> | 1 targets a face-up monster you control | PART A leaf strip `0x021E08C2` | ✅ |
> | 2 cannot be destroyed by battle | PART C `CAVE_SZ_PROTECT` | ✅ |
> | 3 nor by the opponent's card effects | PART D `CAVE_SZ_TARGET` | ✅ |
> | 4 opponent cannot target it | PART D (same stub) | ✅ |
> | 5 cannot attack directly | PART E `CAVE_SZ_DIRECT` | ✅ |
> | 6 target dies when this leaves | native to the donor | ✅ |
> | 7 this dies when the target is destroyed | native to the donor | ✅ |
>
> Deliberate divergences: accepts **any** face-up monster you control (not
> Attack Position only); clause 3 covers **targeting** effects, so Dark Hole /
> Torrential Tribute still destroy. Card art is still Battle-Scarred's.

Card text (from `scratch/ygoprodeck_cache.json`, id 38296564, Continuous Trap):

> Activate this card by targeting 1 face-up Attack Position monster on the field;
> that face-up monster cannot be destroyed by battle or your opponent's card
> effects, your opponent cannot target it with card effects, also it cannot
> attack your opponent directly. When this card leaves the field, destroy that
> monster. When that monster leaves the field, destroy this card.

| # | Clause |
|---|---|
| 1 | Activate by targeting 1 face-up **Attack Position** monster on the field |
| 2 | That monster cannot be destroyed **by battle** |
| 3 | …nor by your **opponent's card effects** |
| 4 | Opponent **cannot target** it with card effects |
| 5 | It **cannot attack directly** |
| 6 | When *this card* leaves the field → destroy that monster |
| 7 | When *that monster* leaves the field → destroy this card |

No previously-working clause can regress: nothing of Safe Zone shipped when this
log was opened.

---

## Confirmed

All entries below were derived **this session** from the committed oracles
(`ygo_tools/reference_files/nds_overlay_3.bin`, base `0x02141700`;
`arm9.bin`, base `0x02000000`) unless marked otherwise. KB baseline at session
start: `verify_knowledge` = **65 PASS / 0 FAIL / 13 UNVERIFIED**.

### Safe Zone is not in the ROM
No `c*_Safe_Zone.py` among the 4117 files in
`data/over_the_nexus/decompiled/cards/`. Donor technique required. The card is
already listed under *Cards to do* in `finished_patches/todo.md`.

### The node-rider idiom (the mechanism for clauses 2–5)
"Card X grants a property to the monster it is attached to" is a **relationship
node keyed by X's cid**, read back with `0x021A1430(side, slot, X_cid)` (variant
`0x021A0950`). Proof: the native double-attack tail at `0x021A3E48–0x021A3F20`
is a flat chain of exactly those calls, each followed by `cmp r0,#0 / movs r0,#1
/ pop`, with cid literals:

| cid | card |
|---|---|
| `0x18CB` | Double Attack |
| `0x1D46` | Assault Armor |
| `0x203F` | Worm Tentacles |
| `0x248D` | Divine Relic Mjollnir |
| `0x14DC`, `0x1EF4` (Lineage of Destruction) | … |

The same shape appears in the **"cannot attack"** predicate at `0x021A4770`,
chaining `0x021A0950` checks for `0x1243` Shadow Spell → `0x14B2` Nightmare
Wheel → `0x21E3` Fiendish Chain → `0x23AE` Darkworld Shackles. So continuous
traps that lock a target already attach cid-keyed nodes.

### Clause 2 host candidate — the battle-indestructibility cid list
- List at **`0x0226D26C`**, **33** sorted u16 cids.
- Sole search site **`0x02197F0E`**: `ldr r1,[pc]` = list, `movs r2,#0x21` (33),
  `bl 0x02022E14` (ARM9 sorted-list search). On hit: `movs r0,#0; bl 0x02198FBC`,
  and `0x02198FBC` is the enclosing function's shared epilogue
  (`add sp,#0xCC; pop {r4,r5,r6,r7,pc}`) — i.e. **hit ⇒ return 0**.
- Sole literal-pool reference to the list address in the whole overlay:
  `0x02198150`.
- Members are exactly the pool's battle-indestructible monsters: Spirit Reaper
  `0x1596`, Reaper on the Nightmare `0x1598`, Exodia Necross `0x1645`,
  Marshmallon `0x1770`, Castle Gate `0x1855`, E-Hero Phoenix Enforcer `0x19FF`
  / Shining `0x1A00`, Gellenduo `0x1B8C`, Cloudians `0x1C60/62/6E/6F/70/71`,
  Armityle `0x1CAE`, Yubel `0x1CF1/F2/F3`, Cloudian - Storm Dragon `0x1DBD`,
  X-Saber Pashuul `0x1E90`, Blackwing Armor Master `0x1F64`, Shiba-Warrior Taro
  `0x204B`, Darkness Neosphere `0x2159`, Reptilianne Naga `0x21B4`, Scrap Goblin
  `0x22F7`, Dark Diviner `0x2401`, Daigusto Sphreeze `0x24B3` (+ 4 unnamed).
- Cross-check that membership is the *entire* grant: Taro / Pashuul / Gellenduo /
  Marshmallon each own a cls1 record, but each implements that card's **other**
  clause — Taro's bounce `0x0220A900`, Gellenduo's self-destruct `0x0221ED50`,
  Pashuul's 1000 damage `0x02212760`, Marshmallon's shared LP resolver
  `0x02206138` (which calls the LP-change resolver `0x02204D08`). Nothing else is
  shared between them.
- Same "sole literal reference = the entire static grant" argument that Quasar's
  PART O double-attack insert used and that was in-game confirmed.

### ⚠️ SUPERSEDED — Clause 3 + 4 host — the Forbidden-Lance "unaffected" predicate
**Not what shipped.** The real host is the target-eligibility predicate
`0x021B021C`, hooked at Heart of Clear Water's query `0x021B05CC` (PART D). The
Forbidden-Lance chain below is real machinery but was never used, and it queries
with `0x021A1430` (family 1) which our family-2 rider would never match.

At `0x021EF000–0x021EF022`, a chain that ORs node checks into `[sp,#0x10]`:

```
0x021EF002  ldr r2,=0x0D82   ; Speed Spell - Forbidden Lance
0x021EF006  bl  0x021A1430   ; hit -> movs r0,#1 ; str r0,[sp,#0x10]
0x021EF014  ldr r2,=0x2488   ; Forbidden Lance
0x021EF018  bl  0x021A1430   ; hit -> movs r0,#1 ; str r0,[sp,#0x10]
0x021EF024  ldr r0,[sp,#0x10] ; cmp r0,#0 ; bne 0x021EF0CE  (protected -> skip)
```
Immediately above, a `0x021A1624` check for `0x2237` Djinn Disserere of Rituals.
Forbidden Lance grants "unaffected by the effects of other Spells/Traps", which
covers Safe Zone's clauses 3 and 4 for Spell/Trap sources.

### ⚠️ SUPERSEDED — Clause 5 host — attack eligibility
**Wrong host, and the cause of two failed attempts.** `0x021A6ABC` and the chain
below are the direct-attack **GRANT**; the prohibition is `0x021A6680` (see
"CLAUSE 5 GATE FOUND"). Do not build on the text that follows.

Same function contains the direct-attack grant list search at `0x021A6BDE`
(list `0x0226D730`, count 25) **and** a long node-check chain at
`0x021A6FD4–0x021A7138` (`0x0E5E`, `0x1295` Gear Golem the Moving Fortress,
`0x13AB` Jowls of Dark Demise, `0x15CF` Kiryu, …) each branching to
`0x021A6E00` on hit — the attack-restriction sink.

### Clause 7 host — "destroyed when its monster leaves"
List `0x0226E940`, **40** entries, search site `0x021CB3BC` (`movs r2,#0x28`).
Members: Amplifier, Premature Burial, Call of the Haunted, Autonomous Action
Unit, Big Bang Shot, Battle-Scarred, Soul Resurrection, Fulfillment of the
Contract, Re-Fusion, Symbol of Heritage, Miraculous Descent, Hysteric Party,
Fossil Excavation, Birthright, Symbols of Duty, Il Blud, Escape from the Dark
Dimension, Limit Reverse, Portable Battery Pack, Graceful Revival, … — i.e.
exactly the "continuous card dies with its monster" family.

### ⚠️ SUPERSEDED — Donor suitability — Shadow Spell `0x1243`
**The donor changed to Battle-Scarred `0x16A2`**, which natively provides clauses
1, 6 and 7 (Shadow Spell provided none of them). Kept for the consumer-site
analysis method, not the conclusion.

Exactly **three** consumer sites in the whole overlay:

| site | pool word | nature |
|---|---|---|
| `0x021A477C` | `0x021A4970` | flat node-check chain ("cannot attack") — safe to retarget the literal |
| `0x021B6DA8` | `0x021B6E40` | **switch comparison operand** — must be neutralised at the leaf |
| `0x021CBD84` | `0x021CBF88` | **switch comparison operand** — must be neutralised at the leaf |

Shadow Spell's cls0 record is at `0x0227F24C` (resolver `0x0220BCAD`, sub
`0x021DA071`, tail `0x02234D99`; tail shared with Nightmare Wheel `0x14B2`).

### The clause-2 host function `0x02197E90` **writes game state**
Enumerated every `BL` in `0x02197E90–0x02198FC0` (55 distinct callees):

- **`0x021C479C` × 20** — the attach-node API. Disassembled it this session:
  it builds command **`0x35`** (`movs r0,#0x35`, OR'd with `0x8000` when
  `r0 != 0`), packs `slot | side<<8`, reads the caller's `[sp+8]` param, and
  dispatches through `0x021C3BC8`. That is a real state mutation, matching
  `otn-attached-effect-rider`'s "cmd 0x35" note (now re-verified).
- `0x021A1430` × 29 and `0x021A0950` × 7 — node queries.
- `0x02022E14` × 1 — the list-B search.
- ATK/DEF/level getters `0x021AF7A4` / `0x021AFA20` / `0x021AFBDC`.

Its caller `0x02198FEC` indexes a **0x24-stride two-element struct at
`0x02298AE8`** by side, using the global side byte at `0x02298AD8`, and passes
one element as `r3` and the other via `[sp]`. `r6` inside `0x02197E90` is that
record: `side` @+0 (`ldrsb`), `slot` @+1 (`ldrsb`), `@+6` (`ldrsh`), **cid @+8**
(`ldrsh`) — i.e. an attacker/defender battle pair.

Reference counts for those globals (unique `ldr` sites resolving to the pool
word):
- `0x02298AE8` — 67 sites spread across `0x21BB`, `0x21CD`, `0x21D0`, `0x21F5`,
  `0x220A`, `0x2210`, `0x221D`, `0x2223`, `0x2228`, `0x222A`, `0x222D`,
  `0x2247`, `0x224D–0x2252` … i.e. the **card-effect resolver and dispatcher
  region**, not one module.
- `0x02298AD8` — **587** sites across essentially the whole engine
  (`0x224F` alone has 47).

Neither global is private to the `0x02196000–0x0219A000` block.

### ✅ Experiment A ANSWERED — `0x02197E90` IS the rules battle-destruction predicate
Settled **statically**, no debugger needed, by the same "sole reference = the
entire grant" method that PART O validated in-game.

`0x02197E90` returns **0 ⇔ this monster cannot be destroyed by battle**, via the
shared tail `0x02197F16: movs r0,#0 ; bl 0x02198FBC` (the `add sp,#0xCC; pop`
epilogue). **Two grant families both branch to that same return-0:**

1. **Innate** — the defender's cid is in list `0x0226D26C` (search `0x02197F0E`).
2. **Attached rider** — a flat chain at `0x0219848C–0x02198512` of
   `0x021A0950(r0=side, r1=slot, r2=granting cid)`:

| cid | card | printed effect |
|---|---|---|
| `0x150A` | Heart of Clear Water | not destroyed by battle **or by a card effect that targets it** |
| `0x17FF` | Ninjitsu Art of Decoy | **Trap**: target 1 face-up "Ninja" you control; it cannot be destroyed by battle |
| `0x1992` | **Mist Body** | the equipped monster cannot be destroyed by battle |
| `0x1C8E` | Gladiator Beast's Battle Manica | it cannot be destroyed by battle |
| `0x21D6` | Rocket Pilder | while attacking, cannot be destroyed by battle (gated on `[sp,#4]`) |

**The clincher:** Mist Body's *entire* printed text is "the equipped monster
cannot be destroyed by battle", and its cid `0x1992` has exactly **one** u32 pool
word in the whole overlay — `0x02198734`, referenced from this chain. Mist Body
is a native, working card. An AI-only module cannot be the sole implementation of
a working card. Therefore this is the rules path, and the list-B search in the
same function is the rules gate.

**Consequence for Safe Zone: clause 2 needs no new hook site.** It is one more
link in an existing chain, in the exact shape of Mist Body's. Ninjitsu Art of
Decoy proves a *Trap that targets a monster* can carry this rider, and Heart of
Clear Water is the precedent for clauses 2+3+4 on one card.

### ✅ Experiment B ANSWERED — and it **corrects the inherited node layout**
From `rom_all_patches.ml3` (Shadow Spell face-up and active). The targeted
monster's zone chain holds exactly one node:

```
node[2] @0x0229D350   +0 = 0x0700   +2 = 0x0017   +4 = 0x1243   +6 = 33   +8 = 0
```

Reading the two walkers rather than trusting the note:

- **Family 1** — `0x021A1430(side, slot, cid)` → walker `0x021A1238`: accepts only
  `kind nibble < 6`, and compares the word `@+0` **directly** against the cid.
  Returns a node pointer. This is what the double-attack tail uses.
- **Family 2** — `0x021A0950(side, slot, cid)` → walker `0x021A0714`: accepts
  `kind nibble` in **[6, 0xB]**; the word `@+0` is **not a cid** but a packed
  **source-card locator** (`side = w & 0xFF`, `slot = (w >> 8) & 0xFF`), resolved
  to the cid *currently at that field location* by `0x021A36EC(side, slot)` and
  then compared. Returns a **count**.

`0x021A36EC` reads the field-slot card word at
`0x0229AC94 + side*0xB3C + slot*0x14 + 0x34`.

So Shadow Spell's rider is **family 2**: `kind = 0x17` (nibble 7), `@+0 = 0x0700`
= source at side 0 slot 7 (a Spell/Trap zone — the Shadow Spell card itself),
`@+4 = 0x1243` = its cid cached.

⚠️ **This is the trap the 3DS cross-check predicted, caught before a line of code
was written.** The approved plan specified `0x021A1430(side, slot, 0x1243)` for
clauses 2–5. That call would have **matched nothing, ever** — wrong walker
family, wrong key semantics — and every clause would have silently done nothing
with `verify()` passing. **All Safe Zone rider queries must use `0x021A0950`.**

Also note **kind `0x17` is the same number the 3DS uses as Safe Zone's
continuous-effect category**, and both engines gate on `(kind & 0xF)` vs 6. The
two engines share this category numbering, which makes Shadow Spell an even
better-matched donor than the static analysis suggested.

**The donor attaches its rider for free** — no `0x021C479C` call needed from our
own code.

### ✅ Experiment C ANSWERED — Shadow Spell targets the OPPONENT's monster
In ml3 the rider sits on **side 1**, slot 2 (the opponent's Gladiator Beast
Laquari, cid `0x1C76`); the player's own Spirit Reaper (side 0, slot 2, cid
`0x1596`) has `head = 0`, no rider. Safe Zone must be able to protect the
controller's **own** monster, so **widening/flipping the donor's target filter is
a confirmed Phase-1 work item**, not a surprise.

### ⭐ DONOR UPGRADE — Battle-Scarred `0x16A2` beats Shadow Spell `0x1243`
Prompted by the user's "surely we can remove those conditions". Correct, and the
payoff is bigger than just the target side.

**Battle-Scarred** (Continuous Trap): *"Select 1 Archfiend monster **on your side
of the field** to activate this card. Your opponent also pays the same Life
Points that you pay for the selected monster during the Standby Phase. **If this
card is removed from the field, destroy the selected monster. When the selected
monster is removed from the field, destroy this card.**"*

Those last two sentences are **clauses 6 and 7 verbatim** — and clause 6 was the
one host I had failed to locate. Confirmations:

- `0x16A2` **is** in the clause-7 list `0x0226E940`. Shadow Spell is not.
- **Own-side selection is shared machinery, and the archetype condition is a
  separable switch leaf.** cls0 `+08` sub-handler `0x021E0680` is shared by
  Machine Duplication `0x157A`, Staunch Defender `0x1669`, Battle-Scarred
  `0x16A2`, Ninjitsu Art of Decoy `0x17FF`, `0x18DF`, The League of Uniform
  Nomenclature `0x1978`, Next to be Lost `0x19DC`, Battle Waltz `0x2416`. Its
  prologue calls the **zone predicate `0x021D6E40` with mask `0x0C15`** (the
  own-side/face-up filter), *then* switches on cid to a per-card condition leaf.
  Battle-Scarred's arm is `0x021E06F2` → leaf **`0x021E08C2`** (the Archfiend
  test). ⚠️ The compared literal is a **switch operand** — patch the *leaf*, not
  the literal (`thumb-stack-based-switch-footgun`).
- The Standby-Phase LP payment to strip is at `0x0225889C` / `0x022588C6`:
  `0x021A09F4(side, …, 0x16A2, …)` guarding `0x021CF924` (the LP-pay primitive).

Revised clause coverage, donor = Battle-Scarred:

| Clause | Native? | Work |
|---|---|---|
| 1 own-side face-up target | ✅ shared prologue + zone predicate | drop the Archfiend test at leaf `0x021E08C2` |
| 2 no battle destruction | ❌ | one `0x021A0950(…,0x16A2)` link at `0x0219848C–0x02198512` |
| 3 + 4 | ❌ | link at `0x021EF000`; investigate `0x021B07AC` |
| 5 no direct attack | ❌ | link in the attack-eligibility chain `0x021A6FD4` |
| 6 this leaves → destroy monster | ✅ **native** | keep |
| 7 monster leaves → destroy this | ✅ **native** (list `0x0226E940`) | keep |
| — Standby LP payment | — | neutralise `0x0225889C` / `0x022588C6` |

Shadow Spell provided **none** of 1/6/7 (it targets the opponent and is absent
from the clause-7 list). This supersedes the donor choice in the approved plan.

**Strong inference, not yet verified:** Battle-Scarred's rider is family 2 (kind
6..0xB) like Shadow Spell's. It shares its cls0 sub-handler *and* tail
(`0x02234D8D`) with Ninjitsu Art of Decoy, whose rider is demonstrably family 2
(it is queried by `0x021A0950` at `0x021984A2`). Confirm by savestating a duel
with Battle-Scarred active and re-running the `rider.shadow_spell_observed`
parse against cid `0x16A2`.

**Open:** whether mask `0x0C15` restricts to face-up only or also encodes battle
position. Safe Zone wants **Attack Position**; the mask is shared by all cards in
the switch so it cannot be narrowed globally — a position test would have to go
in our own leaf, or we accept "any face-up" as a documented divergence.

### Free resources
`CAVE_FREE = 0x0239B7A0` (from the live `ov5_cave.py` sentinel — do not
hardcode; it moves). Nothing Safe Zone wants is claimed in `PHANTOM_CLAIMS` or
the cave ledger.

### 3DS cross-check (different binary — shape only, never addresses)
`CARDS_ZEXAL_3DS_ASM.md` §10 + re-verified against
`3ds_extract/partition0/exefs/code_dec.bin` (ARM11/ARMv6, VA = `0x00100000 +
file_offset`) this session:

- 3DS Safe Zone (Konami `0x254D`) is one row in the Continuous-Trap registry
  `0x6BA0A0`; handler `0x00414F6C` is six instructions —
  `ldrh r2,[r0]` / `mov r1,#0x17` / `bl 0x00458754` = register a continuous
  effect of **category `0x17`** keyed by this card.
- Of all **13** `bl 0x00458754` sites in the binary, category `0x17` is **unique
  to Safe Zone** (others: `0x1,0x2,0x3,0x4,0x5,0x12,0x16`). Even the descendant
  engine gave the card a bespoke category — there is no generic "protection"
  primitive to reuse on either engine, so the per-predicate hook plan is the
  right shape rather than a workaround.
- `0x00458754` does `and r7,r1,#0xf` / `cmp r7,#6` — the same low-nibble *kind*
  semantics as the NDS relationship node. **Consequence: the NDS Safe Zone node
  must be attached with `kind < 6`, or `0x021A1430` will never see it and every
  clause silently no-ops.**

---

## Ruled Out

### "`0x02196000–0x0219A000` is a private CPU-AI module" — **contradicted**
This was the one doubt that made the clause-2 host `unproven`. Three pieces of
evidence this session argue against it:

1. `0x02197E90` calls the attach-node API `0x021C479C` **20 times**, and that
   API emits engine command `0x35` through `0x021C3BC8`. An AI evaluator
   predicting outcomes does not emit real commands.
2. The struct it operates on (`0x02298AE8`, stride `0x24`, indexed by side) is
   read by 67 sites spanning the card-effect **resolver** region
   `0x224D–0x2252` and many individual card modules — it is engine-wide state,
   not an AI scratchpad.
3. The side global `0x02298AD8` has **587** references across the whole engine.

⚠️ **This weakens the doubt; it does not promote the claim.** "The module writes
state" is not the same as "`0x02197F0E` is reached on the battle-destruction
path". CLAUDE.md: *static pass ≠ working*. Experiment A still has to run.

### "`0x02197E90` is a battle-forecast / damage-prediction routine" — **ruled out**
Killed by the Mist Body argument above: `0x1992` has exactly one reference in the
overlay, inside this function's rider chain, and Mist Body is a working native
card whose whole text is that one property. A forecast routine cannot be the sole
implementation.

### "Node key `@+0` is the granting card's cid" — **wrong for family 2**
The inherited memory note `otn-attached-effect-rider` says "key = the NEGATING
card's cid". That holds **only** for the `kind < 6` walker (`0x021A1238` /
`0x021A1430`). For the `kind` 6..0xB family the word `@+0` is a packed
`(side | slot<<8)` **source-card locator**; the cid is cached at `@+4` and the
match is done by resolving the locator through `0x021A36EC`. Corrected in the KB
as `rider.two_walker_families`; the memory note has been updated.

### "Safe Zone clause 2 needs a new hook site" — **wrong, it's cheaper**
It is one more link in the existing `0x021A0950` chain at `0x0219848C–0x02198512`.

---

## Open Questions — ALL CLOSED

Every question this log opened with is resolved. For the record:

1. ~~Clause 6 host not located~~ → **native to Battle-Scarred**, which is why the
   donor changed. Confirmed in-game.
2. ~~Widening the target filter to own-side~~ → moot: Battle-Scarred already
   selects on your own side. The Archfiend restriction was the only gate, and it
   is a separable switch leaf (PART A).
3. ~~Clause 4 host~~ → `0x021B021C`, hooked at `0x021B05CC` (PART D). The third
   Heart-of-Clear-Water reference `0x021B07AC` was indeed the lead.
4. ~~In-game confirmation owed~~ → all seven clauses confirmed 2026-07-21.

Nothing functional remains. The only outstanding item is **card art** (Safe Zone
is not yet in `patch_card_art.py`'s list, so it still shows Battle-Scarred).

---

## 🎮 PHASE 1 IN-GAME RESULTS (2026-07-21, `rom_safe_zone.nds`) — ALL PASS

| # | Test | Result |
|---|---|---|
| 1 | targets any monster you control | ✅ **PASS** — PART A works |
| 2 | selected monster survives battle | ✅ **PASS** — PART C works |
| 3 | no Standby-Phase LP cost | ✅ **PASS** — PART B works |
| 4 | **clause 7** — Battle-Scarred dies when the target leaves | ✅ **PASS** (destroy the monster → the trap leaves) |
| 5 | **clause 6** — target dies when Battle-Scarred leaves | ✅ **PASS** — native |

Two claims are promoted from inference to **in-game confirmed** by test 2:

1. **`0x02197E90` is the rules battle-destruction predicate.** The Mist-Body
   sole-reference argument was right; the CPU-AI reading is dead for good. This
   retires the last doubt in `battle.indestructible_is_rules_path`.
2. **Battle-Scarred's rider is family 2** (kind 6..0xB), readable by
   `0x021A0950`. The load-bearing inference held — if it had been family 1 the
   monster would have died.

Also confirmed live: the whole family-2 rider model (source-locator key at `@+0`,
cid cached at `@+4`), and that a fresh `0x021A0950` link in the protection chain
is a working way to grant clause-2 protection to an arbitrary donor.

### ⚠️ Clause 7 was NOT exercised — the target was flipped face-down
The test removed the monster by **flipping it face-down**, which does not remove
it from the field. The printed trigger is "when that monster **leaves the
field**", so the trap surviving is the correct reading, not a failure.

Savestate evidence (`rom_safe_zone.ml4`, parsed this session): Battle-Scarred
`0x16A2` is face-up in side 0 slot 7; the monster is still in slot 2; and **no
rider node exists anywhere in the pool** — the flip cleared the rider. That is
the engine behaving correctly: every Safe Zone protection clause is worded "that
**face-up** monster", so a face-down target should stop receiving protection
while the trap itself stays on the field.

So the flip case is arguably already right. **Clause 7 remains untested**; it
needs a genuine leave-the-field removal.

Useful engine detail found while chasing this (kept — it is the clause-7 host):
the clause-7 list search `0x021CB3BC` and the cid switch `0x021CBD84` (which
holds Shadow Spell `0x1243`, Spellbinding Circle `0x1103`, Nightmare Wheel
`0x14B2` and Battle-Scarred `0x16A2` — every card with a clause-7-style trigger)
live in **one** function starting at `0x021CB354`. It takes `(r0=side, r1=slot,
r2, r3=flags)`, resolves the cid at that location via `0x021A36EC`, and branches
on **bits 1 and 3 of the `r3` flags word** before doing anything else — i.e. it
is parameterised by *why* the card left. That flags word is where a
destroy-vs-bounce-vs-tribute distinction would live if clause 7 turns out to fire
for only some removals.

**Next experiment:** re-test clause 7 with a real removal — destroy the selected
monster with a card effect (the cleanest case, matching Spellbinding Circle's
"when that monster is destroyed" wording), and separately tribute it. If the
effect-destruction case fails, decode the `r3` flags word at `0x021CB354`.

## Phase 2 — PART D, clauses 3 + 4 ✅ IN-GAME CONFIRMED

Host found by following **Heart of Clear Water `0x150A`**, whose text is exactly
clause 3: *"not destroyed as a result of battle or **by the effect of a card that
targets** the monster"*.

`0x021B021C(r0=acting card, r1=side, r2=slot, r3=[sp] "targets" flag)` is the
**target-eligibility predicate**:
- `0x021B081E` → `movs r0,#1` = the monster **IS** affectable;
- `0x021B0296` → `ldr r0,[sp,#0x58]` = **NOT** affectable (returns the caller's
  default).

Inside the `targets` block (gated at `0x021B05BE`), HoCW queries its rider at
`0x021B05CC` and takes the protected exit. It already uses **`0x021A0950`** —
the same rider family as our donor, so no family mismatch this time.

PART D detours `0x021B05CC` to `CAVE_SZ_TARGET 0x0239B7D0` (56B): replay HoCW's
query untouched; on a miss check our rider **and** that the acting card belongs
to the **opponent** (`ldrb [r7,#2] & 1` vs `r6 & 1`), then drop the saved LR
(restoring SP so `0x021B0296`'s `ldr r0,[sp,#0x58]` stays valid) and jump to the
reject exit.

`verify()` 15/15 PASS, `check_allocations` OK (71 ov5 slots, 16 phantom claims).

**Divergence:** the insert is inside the `targets` block, so protection covers
effects that *target* the monster. Non-targeting destruction (Dark Hole,
Torrential Tribute) still destroys it. That is the limit of what this host
models — "destroyed by a card that targets it", not "by any card effect".

### ✅ PART D IN-GAME CONFIRMED 2026-07-21
1. Opponent's targeting effect on the protected monster → **fizzles**. ✅
2. Your own targeting effects still work → the **opponent-only gate works**. ✅
3. Regression: **Heart of Clear Water and Mist Body both unaffected**. ✅

Both detoured links (PART C on Mist Body's chain, PART D on HoCW's query) are
confirmed non-destructive to their native cards — the "replay the original query
first, only OR in ours on a miss" stub shape is validated twice over.

Clauses **1, 2, 3, 4, 6, 7 are now all in-game confirmed.**

## Phase 2 PART E — clause 5 ⚠️ FIRST ATTEMPT (wrong host; see the rebuild below)

`0x021A6ABC(r0=r5 side, r1=r6 slot)` answers "**can this monster attack
directly?**": `1` = yes (the direct-attack cid list `0x0226D730` **or** a rider
chain of *grants* — Opti-Camouflage Armor `0x1759`, Gear Golem `0x1295`, Jowls of
Dark Demise `0x13AB`, Kiryu `0x15CF`), `2` = the Toon Defense `0x1561` special
case, `0` = no (`0x021A72A4`).

Clause 5 is the **inverse** of what every chain in that function does, so PART E
forces the 0 exit: detour the Toon Defense query at the top (`0x021A6AE0`),
replay it untouched (a hit must still yield the caller's code 2), and on a miss
check our rider then drop the saved LR and jump to `0x021A72A4` (whose
`add sp,#0x40` needs the caller's frame). `CAVE_SZ_DIRECT 0x0239B820`, 44B.

Returning 0 is what an ordinary monster returns, so this can only *remove* a
capability — it cannot enable anything.

`verify()` 19/19 PASS · `check_allocations` OK (72 ov5 slots) · KB `103 facts,
0 FAIL`.

### ❌ PART E IN-GAME: FAILED — the protected monster still attacks directly

**My host was wrong.** `0x021A6ABC` is not the direct-attack *permission* gate;
it is the "does this monster have a **special direct-attack GRANT**" query. Proof
that I should have spotted before building:

- Its early gate at `0x021A6AD0` (`bl 0x021A6680`, miss → `b 0x021A72A4`) makes
  **every ordinary monster return 0** — and ordinary monsters obviously *can*
  attack directly into an empty field. So `0` ≠ "cannot attack directly"; it
  means "has no special grant".
- Every rider in its chains (Opti-Camouflage Armor `0x1759`, Gear Golem `0x1295`,
  Jowls of Dark Demise `0x13AB`, Kiryu `0x15CF`) *grants* the ability.
- It has **13 callers** — it is a widely-consulted capability query, not a gate.

Forcing `0` therefore changes nothing in the normal "opponent's field is empty"
case, which is exactly what the test showed.

**What PART E does still do:** it denies a direct attack to a Safe-Zone'd monster
that has a *granted* direct-attack ability (an Opti-Camouflage-Armor'd or
Gear-Golem-style monster). That is a real but rare sub-case of clause 5.

### Ruled out for clause 5 — do not re-walk
- `0x021A6ABC` and its rider chains: the GRANT query, not the permission gate.
- `0x0226D730` (direct-attack cid list) is likewise a grant list.
- **Zombyra the Dark `0x147D`** — the pool's only card whose sole mechanic is
  "cannot attack your opponent directly" — appears **exactly once** in overlay 3,
  in its cls1 record `0x02287154`, whose resolver `0x022082A4` is a *shared*
  per-cid ATK-modifier switch (its leaf is Zombyra's "loses 200 ATK" clause).
  There is also **no `card_prop` bit** for direct attack in `game_constants.py`.
  So the restriction is encoded somewhere not greppable as a literal — most
  likely a switch operand (`base±imm`, the known ungreppable footgun) or an ARM9
  table.

### ⚠️ RETRACTED — the "clause 5 does not exist" claim below was WRONG

**In-game 2026-07-21 (savestate `rom_safe_zone.ml2`): a Zombyra the Dark in the
Battle Phase, with the opponent's field EMPTY, cannot declare a direct attack.**
The mechanic is implemented. My negative result rested on a false premise.

**The mistake:** I asserted "`0x147D` appears exactly once in overlay 3" without
ever running that search — I inferred it from an earlier cls-record lookup and
then wrote it into these notes as a fact. It is false. `0x147D` has **five**
aligned u16 occurrences in overlay 3:

| addr | in |
|---|---|
| `0x0226E4BC` | not in any `0x02022E14`-searched list |
| `0x0226E7E2` | **list `0x0226E7C4`, 159 entries, site `0x021C779C`** |
| `0x0226EA7C` | not in any `0x02022E14`-searched list |
| `0x0226FD4E` | not in any `0x02022E14`-searched list |
| `0x02287154` | its cls1 record (the "loses 200 ATK" clause) |

Also ruled out along the way (these parts stand):
- **Not a rider.** Zombyra's zone chain in `ml2` is empty (`head = 0`).
- **Not `card_genre` bit 7.** 717 cards carry it — Speed Spells, equip spells,
  field spells, United We Stand, Mage Power … it is an **ATK-modifier category**,
  which is Zombyra's *other* clause. (Zombyra has only that one bit.)
- The `base±imm` scan and the ARM9 scan were real and came back empty, but they
  were looking for an encoding that was never needed — the cid is present as a
  plain u16 in overlay-3 tables.

**Next step for clause 5:** identify the three non-`0x02022E14` tables at
`0x0226E4BC`, `0x0226EA7C`, `0x0226FD4E` — find each enclosing sorted run, the
pool word that points at its start, and its consumer. One of them is the
direct-attack prohibition. `0x0226E7C4` (159 entries: Satellite Cannon, Copycat,
Exodia Necross, Berserk Dragon, Insect Princess …) looks like a generic
"has a continuous self-effect" set rather than clause 5.

**RESOLVED — and all five are Zombyra's ATK clause, NOT clause 5:**

| site | structure | Zombyra's entry |
|---|---|---|
| `0x0226E4BC` | stride-6 `[cid][ATK delta][DEF delta]` | `0xFF38` = **-200** (Exarion `0xFE70` = -400) |
| `0x0226E7E2` | list `0x0226E7C4`, 159 entries | generic "has a continuous self-effect" |
| `0x0226EA7C` | stride-4 `[cid][flags]`, 110 entries | `0x0008` = bit 3 |
| `0x02270D4E` | a pointer table (my "0x0226FD4E" was an arithmetic slip) | not a cid |
| `0x02287154` | its cls1 row | the ATK-loss resolver |

Flags-table bit 3 = **"has a when-this-destroys-a-monster-by-battle trigger"**:
its 70 members are Cactus Fighter, Hydrogeddon, Goyo Guardian, Jurrac Guaiba,
Flamvell Firedog, Blackwing Shura … Zombyra's ATK-loss trigger again.

Also cleared: the overlay-6 hits for `0x147D` are ARM-mode
`strb r1,[r4,#0x47D]` struct offsets, not cids.

**So clause 5 is still UNLOCATED.** Every cid-keyed reference to Zombyra across
every overlay and ARM9 is accounted for by its *other* clause, yet the
restriction demonstrably works in-game. Remaining hypotheses, untested:
- the prohibition is not cid-keyed but derived from some per-instance property;
- or the in-game observation had another cause (battle position, already
  attacked). Zombyra's `ml2` zone record is
  `7d1480060f000000010000000000000000014100` — word `0x0680147D`, face-up,
  inst 13; the `+0x04 = 0x0F` field is undecoded.

**Cheapest next experiment:** savestate an ordinary monster that CAN attack
directly into an empty field and diff its 0x14-byte zone record against
Zombyra's. If `+0x04` differs, that field is the lead.

---

## ✅ CLAUSE 5 GATE FOUND (2026-07-21) — by intersection, not by chasing Zombyra

The user named four more cards with the mechanic: **Magical Scientist `0x1619`**,
**Barbaroid `0x24BA`**, **Sorciere de Fleur `0x24E6`**, **Vision HERO Trinity
`0x23EC`**. Intersecting their overlay-3 sites put three of them in one place:

| card | site |
|---|---|
| Vision Hero Trinity | `0x021A6960` |
| Magical Scientist | `0x021A69A0` |
| Sorciere de Fleur | `0x021A6A1C` |

All inside **`0x021A6680`**, whose tail is a flat chain of **`0x021A1430`
(family 1)** rider queries — the cards that *apply* the restriction attach
cid-keyed riders:

```
021A69A4  bl 0x021A1430   ; Magical Scientist 0x1619
021A69BC  bl 0x021A1430   ; 0x18E5
021A69CC  bl 0x021A1430   ; Genex Ally Axel 0x223B
021A69DC  bl 0x021A1430   ; Sorciere de Fleur 0x24E6
021A69F0  bl 0x021A1430   ; 0x2536
021A6A02  bl 0x021A1430   ; 0x195B
          hit -> b 0x021A6A0E -> movs r0,#0
          all miss          -> movs r0,#1
```

And the caller: `0x021A6AD0 bl 0x021A6680 / cmp r0,#0 / bne … / b 0x021A72A4`.

**So `0` from `0x021A6680` = "cannot attack directly".** My earlier claim that
*"every ordinary monster returns 0 there"* was **wrong** — ordinary monsters fall
through the chain and return **1**. That single misreading is what made PART E a
no-op.

**Why chasing Zombyra could never have worked:** its cid is not in this chain at
all. Zombyra's restriction must come from somewhere else (or from a rider applied
to it), and every one of its five overlay-3 sites is its *ATK-loss* clause. The
"pick a card with only this mechanic" trick failed here because Zombyra has two
mechanics and the engine indexes only the other one — **intersecting several
cards that share the mechanic is the stronger tool**, and it is what worked.

**PART E rebuilt:** detour the Genex Ally Axel link `0x021A69CC` →
`CAVE_SZ_DIRECT 0x0239B820`. Replay the family-1 query untouched; on a miss, OR
in `0x021A0950(side, slot, 0x16A2)` (our rider is family 2). Returning non-zero
IS the chain's "cannot attack directly" contract, so no stack manipulation is
needed — this stub is simpler than the one it replaces.

`verify()` 25/25 PASS.

### ✅ PART E IN-GAME CONFIRMED 2026-07-21
The protected monster can no longer declare a direct attack.

**ALL SEVEN CLAUSES ARE NOW IN-GAME CONFIRMED.** Safe Zone is functionally
complete; only the card art still shows Battle-Scarred.

KB: `rider.no_direct_attack_gate` (VERIFIED, in-game confirmed).

**Process lesson:** state a search was run only when it was run. This is the
second time in this session that an unverified assumption reached the notes as
fact (the first was the `0x021A1430` walker family, caught by the 3DS
cross-check before it shipped).

---

### 🔴 SUPERSEDED — "CLAUSE 5 DOES NOT EXIST IN THIS ENGINE" (wrong, see above)

Before spending a GDB session, I brute-forced the ungreppable encoding rather
than assuming it was hiding:

1. **`base±imm` scan.** Every 4-aligned overlay-3 pool word within ±0x1FF of
   `0x147D` (963 candidates), each of its `ldr` sites, then a forward walk of up
   to 24 instructions tracking register-copy chains (`adds rD,rS,#imm3`,
   `adds rX,#imm8`, `mov`) looking for any site that computes `0x147D`.
   → **0 hits.**
2. **ARM9.** `0x147D` has **zero** aligned u16 references and **zero** u32 pool
   words in ARM9. Its single byte-level hit (`0x020634FB`) is unaligned, i.e. a
   coincidence.
3. **Overlay 3.** `0x147D` appears exactly **once** — its cls1 record
   `0x02287154`, whose shared resolver `0x022082A4` implements Zombyra's *other*
   clause ("loses 200 ATK when it destroys a monster by battle").

Zombyra the Dark has exactly two printed mechanics; the engine implements the
second and **not** "This card cannot attack your opponent directly". There is no
cid list, no rider chain, no ARM9 table, and no per-cid switch for it anywhere.

**Conclusion:** the restriction is simply **not modelled** by this engine, so
clause 5 cannot be delivered by adding a link to existing machinery — the way
clauses 2, 3 and 4 were. It would require bespoke code in the attack-declaration
path (locate where a direct attack is authorised against an empty field, and add
a rider check there). That is a self-contained RE project, not a one-line insert.

**Cheap confirmation available:** put a **Zombyra the Dark** on the field against
an empty opponent field. If it attacks directly, the mechanic is confirmed absent
from the game and this finding is closed.

PART E is retained as the partial it is (it denies *granted* direct attacks under
Safe Zone) and is documented as such in the module.

## Phase 1 detail (static)

`otn_enhanced/cards/safe_zone.py`, donor **Battle-Scarred
`0x16A2`**. Built to `data/over_the_nexus/working/rom_safe_zone.nds`; `verify()`
all PASS; `check_allocations` OK (70 ov5 slots, 16 phantom claims); KB proofs
`96 facts, 0 FAIL`.

| Part | Site | Change |
|---|---|---|
| A (clause 1) | `0x021E08C2` (2B) | Archfiend leaf → `b 0x021E0A80` (the switch's own generic-accept leaf) |
| B (LP strip) | `0x02258A50` (2B) | shared literal `0x16A2` → phantom `0x2617` |
| C (clause 2) | `0x021984EC` (4B) + `CAVE_SZ_PROTECT 0x0239B7A0` (28B) | GB Battle Manica chain link → ov5 stub that runs the original query then ORs in `0x021A0950(side, slot, 0x16A2)` |

Clauses delivered: **1, 2, 6, 7** (6 and 7 native to the donor).

Safety checks done, not assumed:
- Leaf `0x021E08C2` has **exactly one** inbound branch (`0x021E06F8`), so the
  overwrite cannot misroute another cid. The switch's compared literal was *not*
  touched (`thumb-stack-based-switch-footgun`).
- `verify()` asserts the other six links of the protection chain still
  `bl 0x021A0950` — no collateral damage to Mist Body et al.
- Pool `0x02258A50` has exactly two `ldr` references, both feeding
  `0x021A09F4` → `0x021CF924`. `0x021CF924` confirmed as the LP-change command
  (builds command `0x24`). The neighbouring Archfiend test at `0x022588F6` and
  attach at `0x02258918` belong to **Pandemonium** `0x169F` (the Archfiend
  maintenance-cost waiver), not to Battle-Scarred — different literals, untouched.
- Clauses 6/7 live at the `0x021CBD84` switch and list `0x0226E940`, neither of
  which this patch touches.
- Stub is Thumb-1 only, `PUSH {LR}` / `POP {PC}` (never `POP {…,LR}`).

### DIVERGENCE from the printed card
"face-up **Attack Position** monster" → this build accepts **any face-up monster
you control**. Mask `0x0C15` is shared by all eight cards in the selector switch
so it cannot be narrowed globally, and no position test was added.

### ⚠️ Still inferred, not observed
Battle-Scarred's rider being family 2 (kind 6..0xB, readable by `0x021A0950`).
Strong inference — it shares its cls0 sub-handler *and* tail `0x02234D8D` with
Ninjitsu Art of Decoy, whose rider is queried by `0x021A0950` at `0x021984A2`.
**If this is wrong, clause 2 silently does nothing** (the classic family-mismatch
no-op). The in-game test below distinguishes it immediately.

### In-game test script (the oracle)
Load `rom_safe_zone.nds` in melonDS, normal duel (not a puzzle — ov5 is not
resident there).

1. **Clause 1** — set Battle-Scarred, activate it. It must offer **any face-up
   monster you control**, not only Archfiends. *(If it offers nothing, PART A
   failed.)*
2. **Clause 2** — attack the selected monster with a stronger opponent monster,
   or let the CPU attack it. It must **survive**, and battle damage must still
   apply normally. *(If it dies, the rider family inference was wrong.)*
3. **PART B** — pass through several of your Standby Phases. **Neither player
   should lose Life Points.** *(If LP drains, the literal retarget missed.)*
4. **Clause 7** — destroy or bounce the selected monster by some other means.
   Battle-Scarred must be destroyed with it.
5. **Clause 6** — destroy Battle-Scarred (e.g. MST). The selected monster must
   be destroyed with it.
6. **No regression** — separately confirm **Mist Body** still makes its equipped
   monster battle-proof (that is the chain link the stub detours).

Also worth a savestate after step 1: parse the target's zone chain for a node
with `@+4 == 0x16A2` and record its `kind` nibble, which promotes
`rider.shadow_spell_observed`'s sibling claim from inference to observation.

## What's left

**Nothing functional.** Card art only — add Safe Zone to `patch_card_art.py`'s
list; it currently shows Battle-Scarred's picture.

If a future session revisits this card, the two most reusable results are the
KB facts `rider.two_walker_families` (the `0x021A1430` vs `0x021A0950` trap) and
`rider.no_direct_attack_gate` (`0x021A6680`, plus the warning that `0x021A6ABC`
is the grant, not the prohibition).

---

## Superseded — the original Phase-0 experiment scripts (kept for provenance)

**Experiment A (keystone).** Live duel, player attacks a face-up Marshmallon
`0x1770` with a higher-ATK monster. Breakpoint `0x02197F0E`; record `r0` (should
be the defender's cid), `r6` (descriptor: side@+0, slot@+1, cid@+8) and `lr`;
then run to damage resolution and observe whether Marshmallon survives.

- Fires on the player's own declared attack with `r0 == 0x1770`, monster
  survives → rules path. CONFIRMED; proceed to Phase 1.
- Does not fire on the player's attack yet Marshmallon still survives → AI model
  only. Go to A′.
- Fires only while the CPU is deciding → AI model only. Go to A′.

Also walk the saved LRs back through `0x02198FEC` → `0x0219988C` → `0x0226B9FC`
→ `0x0226A3A8` and record what invokes `0x0226A3A8`.

**Experiment A′ (fallback).** Breakpoint the leave-field hook `0x021C8216` on a
battle destruction (descriptor `[sp+0x44]` = battle, `[sp+0x90]` = DESTROYED —
inherited from `otn-leave-descriptor-slots`, **UNVERIFIED** until re-seen this
session) and walk the saved LRs upward to find the function that *decided* the
destruction. That function is the real clause-2 host.

**Experiment B.** Activate Shadow Spell on a monster; either breakpoint
`0x021A1430` and look for `r2 == 0x1243` from `0x021A477C`, or savestate-parse
the target zone's chain: head index at
`0x0229AC94 + 0x3E + side*0xB3C + slot*0x14`, node pool `0x0229D33C` stride 10
(`+0` cid, `+2` kind, `+8` next). Record the `kind` nibble explicitly.

**Experiment C.** Observe Shadow Spell's target prompt: own side, opponent side,
or both.

### ⛔ Preflight BLOCKED 2026-07-21 — experiments not run

melonDS (`melonDS.exe`, pid 14132) is running and `melonDS.toml` has
`[Instance0.Gdb] Enabled = true`, `[Instance0.Gdb.ARM9] Port = 3333`,
`BreakOnStartup = false`. Port 3333 is **LISTENING** and accepts a TCP
connection, but the stub **services nothing**:

- `$?#3f` → no bytes back within 4 s.
- `\x03` (interrupt) → no bytes back either.
- `netstat` shows three server-side sockets in **CLOSE_WAIT** on 3333 (pid
  14132) against my probes — melonDS `accept()`ed them and never read them.

So the stub thread is not pumping. Per CLAUDE.md's *Emulator / GDB Preflight*
this is a hard stop: breakpoints set now would never hit. **No experiment was
run; nothing below is observed.**

Likely causes, in order: no ROM loaded / emulator sitting in its own menu so the
core is not stepping; emulation paused; or the stub wedged from an earlier
session's unclean detach (memory `otn-attached-effect-rider`: "the melonDS GDB
stub wedges easily"). The fix is to load `rom_all_patches.nds` (or a Shadow-Spell
test ROM), get into an **active normal duel**, and restart melonDS if the stub
still does not answer `$?#3f`.

Preflight before any of this: melonDS GDB stub on port **3333**, an **active
normal duel** (not a menu, not a puzzle — puzzles load overlay 1/41 so overlay 3
and the ov5 cave are absent), overlay 3 resident. melonDS write-watchpoints do
**not** fire — use breakpoints. Savestate parsing beats GDB for bulk RAM reads;
the savestate RAM base offset is version-dependent, auto-detect it.

## 2026-10-08 — C1 either-side + Attack Position, and "your opponent" = Safe Zone's controller's opponent

USER 2026-10-08 (in-game, ov3 test ROM 03543275): "Safe Zone is only targetting monsters on my side of the field but it should
be able to target the opponents monsters too." -> scope confirmed: "Yes Fix both" (either side + Attack Position only).
Ruling (user, verbatim): "Your opponent is always the opponent of the player who controls Safe Zone. So an opponents monster
equipped by this is unaffected by the opponents card effects but can attack me directly". Position re-check after activation:
NOT wanted (keeps protecting a monster that later goes to Defense) -- default stated, not objected.
Printed text (ygoprodeck 38296564): "Activate this card by targeting 1 face-up Attack Position monster on the field; ..."

### Confirmed (this session)
- Safe Zone = cls0[472] @0x0228128C {0x16A2, 0, +04 0x0220BCAD, +08 0x021E0681, +0C 0, +10 0, +14 0x02234D8D}.
  Resolver 0x0220BCAD (= `bl 0x022078FC(desc, 0x17, cid)`, the category-0x17 attach) is SHARED by 11 cls0 rows incl. Shadow
  Spell 0x1243, which natively attaches to the OPPONENT's monster -> the resolver is side-neutral; only the +08 filter limits C1.
  +14 0x02234D8D = board template with prompt 0x7C (Shadow Spell's 0x02234D99 = prompt 0x64). Kept.
- Zone predicate 0x021D6E40 mask bits, decoded from its disassembly AND the 168-wrapper corpus vs printed text:
  bits0-1 side (0 any [Shield Crush 0x1510 'on the field'], 1 same as source, 2 opponent [Mirror Force 0x1092]);
  0x04 face-up ([0x0229ACD0+..] != 0); 0x80 = ATTACK POSITION ([0x0229ACCE+..] == 0; Mirror Force / Block Attack 0x40496 /
  Cell Explosion Virus); 0x100 = Defense Position ([0x0229ACCE] != 0; Shield Crush, Stop Defense); 0x70 zone class (0x10
  monster zone); 0x400 = targetability check 0x021AFD3C (Block Attack has it, Mirror Force not); 0x800 only feeds the 0x1000
  branch (0x021B0828 arg). 0x40000 = 0x021AEB30 (NOT position: not-face-down && no cid-0x1DE1 rider).
  -> C1 mask = 0x0C15 minus own-side bit plus Attack Position = 0x00000C94. No native wrapper carries it (corpus scan).
- Family-2 rider chain: head u16 @0x0229ACD2 + side*0xB3C + slot*0x14; node = 0x0229D33C + idx*0xA; next = u16 @+8; idx 0 ends;
  kind nibble = [+2]&0xF in [6,0xB]; [+0] u16 = source locator (side = low byte, slot = high byte); cid at source via
  0x021A36EC(side, slot). (walker 0x021A0714 disassembled this session.) => Safe Zone's CONTROLLER = low byte of the Safe Zone
  node's [+0].
- Current C3/C4 gate (PART D stub) compares the acting card's controller with the PROTECTED MONSTER's side (r6) and C5 (PART E)
  denies a direct attack for any protected monster: both are wrong once C1 can pick an opponent's monster.

### Plan (ov3 path only; the shipped ov5 Safe Zone stays byte-identical until "ship it")
- C1: cls0 +08 -> new thin wrapper `push {r3,lr}; ldr r3,=0xC94; bl 0x021D6E40; pop {r3,pc}`.
- helper SZSIDE(side, slot) -> controller side of the first Safe Zone node on that monster (or -1).
- C3/C4: allow iff acting controller == SZSIDE(protected); else reject (old: == protected side).
- C5: deny direct attack iff protected monster's side == SZSIDE.
- C2, C6/C7, PART A/B unchanged. ponytail: two Safe Zones (both players) on one monster -> first node wins.

### Round 2 BUILT (2026-10-08) -- AWAITING IN-GAME TEST
- patch_safe_zone ov3 path only (main(ov3=True); default still the shipped ov5 version, chain 83aef57e re-built byte-identical):
  cls0[472] +08 -> CAVE3_SZ_FILTER 0x0220A640 (16 B wrapper, mask 0xC94); CAVE3_SZ_SIDE 0x021F6AE0 (96 B rider-chain walker);
  CAVE3_SZ_TARGET re-homed 0x022222C8 -> 0x021F5778 (64 B), CAVE3_SZ_DIRECT 0x021F4C1C -> 0x022222C8 (56 B). check_allocations OK.
- TEST ROM rom_safe_zone_ov3.nds sha256 b14974969a53e82fd846b27f7cfbda6672aa82f76d0b648fddf306c5fea81397; verify ALL PASS.
- EXECUTION PROOF (scratchpad sz_exec.py, thumbemu over the BUILT ROM's stubs + the native zone predicate, its 6 externals = 1):
  C1 filter accepts face-up ATK on side 0 AND side 1, rejects face-up DEF / face-down / an S/T zone (7/7); SZSIDE over built
  chains: none -> -1, family-1 only -> -1, own -> 0, opponent's -> 1, foreign rider first then own -> 0 (5/5); C3/C4 reject iff
  actor != Safe Zone's controller, all 8 (monster side x SZ side x actor); C5 deny iff monster side == SZ side or Axel, all 8 +
  no-Safe-Zone cases; REGRESSION: own-side C3/C4/C5 == the shipped stubs (6/6). 36/36 PASS.
- PROOFS: ov5 + arm9 identical to base; ov3 diff vs ov5-placement ref = 264 B = 3 BL sites + 5 slots + cls0 +08 0x02281294;
  PROTECT equal to its ov5 original; negative control REFUSES on stock.

### Safe Zone SHIPPED 2026-10-08 (round 2: either side + Attack Position, controller-relative "your opponent")
- USER 2026-10-08 verbatim on rom_safe_zone_ov3.nds b1497496: "Safe Zone works now, ship it" -> in-game confirmed by user 2026-10-08.
- Default flipped: patch_safe_zone main(ov3=True) + SRC -> rom_ov3_compact.nds; CAVE_SZ_PROTECT/TARGET/DIRECT (ov5) RETIRED.
  check_allocations OK, live ov5 280 -> 277.
- FIRST SHIP BUILD ABORTED at step 39: patch_azure_eyes asserted 0x021B05CC == native or Safe Zone's OV5 BL (the known
  'hook neighbour hard-codes the owner's ov5 slot' trap -- I did not grep before shipping). Fixed: it accepts the ov3 BL too
  (build + verify). The failed build left rom_all_patches.nds untouched (83aef57e), so the sweep after it was meaningless.
- NEW CHAIN rom_all_patches.nds: 101/101, sha256 b56a0fccdc4f7bf5f54bc01951cebf79ed28fd94cb1c507eeb7406fe9cfa47b2
  (previous kept as rom_all_patches_83aef57e.bak.nds). Sweep 87 passed / 0 failed. vs 83aef57e: arm9 identical; ov5 diff = 90 B,
  all inside the 3 retired SZ slots, now zero; ov3 240 B.
- KB card.safe_zone_either_side_controller_relative (VERIFIED). verify_knowledge 608 PASS / 0 FAIL / 74 UNVERIFIED.
