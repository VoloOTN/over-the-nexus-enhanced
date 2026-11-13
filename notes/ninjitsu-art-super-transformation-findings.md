# Ninjitsu Art of Super-Transformation — findings (session 2026-08-31)

Printed text (`scratch/ygoprodeck_cache.json`, id 90200789) — **Continuous Trap**:

> Activate this card by targeting 1 "Ninja" monster you control and 1 face-up
> monster your opponent controls; send them to the GY, then Special Summon 1
> Dragon, Dinosaur, or Sea Serpent monster from your Deck whose Level is less
> than or equal to the combined original Levels of the sent monster(s). When this
> card leaves the field, banish that monster.

User's added requirement: **"this card should also be searchable by hanzo"** —
i.e. it must join the repurposed "Ninjitsu Art" set code `0x2A`.

Clause split (proposed, **NOT yet confirmed by the user**):

1. **C1** — the card exists as a Continuous Trap with the right name/text/stats,
   and is a member of set code `0x2A` so Hanzo clause 1 can search it.
2. **C2** — activate by targeting 1 "Ninja" you control **and** 1 face-up monster
   your opponent controls; send both to the GY.
3. **C3** — Special Summon 1 Dragon / Dinosaur / Sea Serpent from your **Deck**
   whose Level <= the combined original Levels of the sent monster(s).
4. **C4** — when this card leaves the field, **banish** that monster.

**STATUS 2026-08-31 (session 12): ROUND 12 BUILT, AWAITING IN-GAME TEST.** User directive: *"build all
of it. put it in ov5"*, donor **Goblin Fan `0x1255`**.

Module `otn_enhanced/cards/ninjitsu_art_super_transformation.py`
Build `.venv-1/Scripts/python.exe _build_nast.py --text`
ROM `data/over_the_nexus/working/rom_nast.nds`
sha256 `22c6112db710c4863d27d5a67bfab46dd0626f4e8c33d40800ce141b0822bb4d`
(deterministic — two clean builds from `rom.nds` gave the same digest).

`verify()` 22/22 PASS for this card **and** 46/46 for Hanzo on the same ROM;
`check_allocations` OK (150 ov5 slots, 127 phantom claims, no collisions, ledger
in sync); `verify_knowledge` 364 facts / 329 PASS / 0 FAIL / 35 UNVERIFIED.

⚠️ **NOT wired into `apply_all_patches`** — single-card ROM only until the user
says ship.

⚠️ One composition edit outside this card:
`patch_ninja_grandmaster_hanzo.verify()` asserted the set-code `0x2A` list by
EXACT EQUALITY against its own four entries, so any later card joining that list
read as a Hanzo regression. Relaxed to "Transformation and Decoy are still
members, the list is still 4 long and strictly sorted" — which is what clause 1
actually depends on. Hanzo's ROM bytes are unchanged.

**Clause status as built** (see the module docstring for the full deviation list):

| clause | built? | how |
|---|---|---|
| C1 exists + Hanzo-searchable | yes | data only |
| C2 two targets, both sides | yes | `+14` default arm + an ov5 predicate |
| C2 "send BOTH to the GY" | **no** | Bubble Shuffle's resolver tributes target 0 only |
| C3 SS Dragon/Dino/Sea Serpent from Deck | yes | criteria row + ov5 handler |
| C3 "Level <= combined original Levels" | **no** | level bits omitted; any Level is summonable |
| C4 monster leaves when the card leaves | yes | membership list insert |
| C4 specifically a BANISH | **unproven** | the list does not encode destroy vs banish |

---

## Confirmed (proven this session)

### The 3DS ships the card — cid `0x26DD`

`.venv-1/Scripts/python.exe -m otn_enhanced.tools.threeds_lookup "Ninjitsu Art of Super-Transformation"`
→ 3DS index 4996, **cid `0x26DD`**, one row in the main-effect / criteria registry:

| registry row | cid | aux | handler | word |
|---|---|---|---|---|
| `0x686CBC`[1564] | `0x26DD` | `0xFFFF` (= -1, no set-code filter) | `0x004B0478` | `0x00000002` |

Same word as NDS Transformation's row. Handler differs (`0x004B0478` vs
Transformation's 3DS `0x004A8840`), and no NDS equivalence is proven for either.

### The 3DS Spell/Trap cls table — base VA `0x6B2600`, stride `0x18`, **1646 rows**

Found by walking the lattice backwards from the address `threeds_lookup.py`
lists as `continuous_traps` (`0x6BA0A0`, count 22) until the cid column left
range. Row shape is the NDS cls shape: `{u32 cid, +04 resolver, +08, +0C, +10, +14}`.

⚠️ **`threeds_lookup.py`'s `REGISTRIES` entry `("continuous_traps", 0x6BA0A0, 0x18, 22)`
is a 22-row window onto this 1646-row table.** That is why the tool reported no
`continuous_traps` hit for `0x26DD` — its row is index 1426 of the real table,
at VA `0x6BABB0`, well past the 22-row window. Same class of undercount as the
Hanzo session's "two provider call sites → actually three".

| row | cid | card | +04 | +08 | +0C | +10 | +14 |
|---|---|---|---|---|---|---|---|
| 494 | `0x1768` | NA of Transformation | `0042D1F4` | `003DDA4C` | `00488108` | `00402AD8` | `0` |
| 531 | `0x17FF` | NA of Decoy | `00414F6C` | `003F033C` | `0` | `0` | `004787C0` |
| 1426 | `0x26DD` | **NA of Super-Transformation** | `00457B38` | `003ED908` | `0049D734` | `0` | `00478390` |
| 1441 | `0x2727` | NA of Duplication | `00404B94` | `003DC3A4` | `0049BFF8` | `00402AD8` | `0` |

Slot-sharing census over all 1646 rows (this is the architecture signal):

* Super-Transformation's **`+04` resolver `0x00457B38` is used by exactly 1 row** —
  it is a **bespoke Konami resolver**, not a shared chassis.
* Its `+08` `0x003ED908` is shared by 7 rows: Common Soul, Faustian Bargain,
  Curse of the Circle, Evo-Miracle, Impenetrable Attack, Butterspy Protection —
  all "**target a monster on the field**" cards.
* Its `+0C` `0x0049D734` is shared by 6: Beast Soul Swap, NEX, Mask Change,
  Zenmairch, `0x0E83` — all "**send/return a targeted monster, then Special
  Summon a replacement**" cards.
* Transformation's `+04` `0x0042D1F4` is shared with exactly one other card:
  **Super Solar Nutrient `0x1F75`**.

### That last pair carries straight across to the NDS — and it is the chassis

NDS cls tables (geometry from `dispatch.cls_tables`), read from
`data/over_the_nexus/working/rom.nds`:

| record | cid | card | +04 | +08 | +0C | +10 | +14 |
|---|---|---|---|---|---|---|---|
| cls0[524] | `0x1768` | NA of Transformation | `0221B2FD` | `021DA1C9` | `021F7D05` | `021E7C89` | `0` |
| cls0[1023] | `0x1F75` | Super Solar Nutrient | `0221B2FD` | `021DC625` | `021F7D05` | `021E7C89` | `0` |
| cls0[561] | `0x17FF` | NA of Decoy | `0220BCAD` | `021E0681` | `0` | `0` | `02234D8D` |

**Four of the five slots are byte-identical between Transformation and Super
Solar Nutrient.** Sharer counts, measured across all four cls tables:

| slot | value | # records sharing | role |
|---|---|---|---|
| +04 resolver | `0x0221B2FD` | **2** (`0x1768`, `0x1F75`) | tribute → SS-from-deck/hand + leave-rider |
| +08 candidate pred | `0x021DA1C9` | 7 (`0x12C5`, `0x167D`, `0x1768`, `0x1BF6`, `0x20BA`, cls3 `0x1C30`, cls3 `0x1D90`) | **per-acting-cid switch** — which monster may be tributed |
| +0C activation cond | `0x021F7D05` | **2** (same pair) | generic "a monster zone is free" |
| +10 cost | `0x021E7C89` | 110 | generic 1-monster tribute |

The two cards' printed texts are the same shape, which is what makes the
chassis legible:

* Transformation — *"Activate by Tributing 1 face-up 'Ninja' monster; Special
  Summon 1 Beast, Winged Beast or Insect monster from your hand or Deck whose
  Level <= the Level the Tributed monster had on the field +3. When this card
  leaves the field, destroy that monster."*
* Super Solar Nutrient — *"…Tributing 1 Level 2 or lower Plant-Type monster;
  Special Summon 1 Plant-Type monster from your hand or Deck whose Level <= the
  Level the Tributed monster had on the field +3…"*

### The resolver `0x0221B2FC` is a 0x30-byte wrapper; the rider kind is `0x17`

```
0221B2FC  push {r3,lr}
0221B2FE  ldr  r2,=0x0229AAFC
0221B302  ldr  r2,[r2,#0x70]      ; the resolver PHASE
0221B304  cmp  r2,#1
0221B306  beq  0x0221B30E
0221B308  bl   0x02206F40         ; every other phase -> the generic resolver
0221B30C  pop  {r3,pc}
0221B30E  ldrb r0,[r3,#2]         ; phase 1 only:
0221B310  movs r1,#0
0221B312  str  r1,[sp]
0221B314  ldrb r2,[r3,#3]
0221B316  ldr  r1,=0x02298A28
0221B318  movs r3,#0x17           ; <-- the RIDER KIND
0221B31A  lsls r2,r2,#8
0221B31C  orrs r2,r0
0221B31E  lsls r2,r2,#0x10
0221B320  ldrh r1,[r1,#4]
0221B322  lsrs r2,r2,#0x10
0221B324  bl   0x021C479C         ; rider.attach_api
0221B328  movs r0,#0
0221B32A  pop  {r3,pc}
```

⚠️ **A CORRECTION THAT WAS ITSELF WRONG, RETRACTED — read this, it is the
cautionary bit.** Mid-session I saw that `0x021C479C` builds command `0x35` and
tail-calls `0x021C3BC8`, matched that against `event.animation_command_queue`,
and wrote here that it is "the animation queue, NOT a rider attach", so `0x17`
was "a parameter in an animation command, not a kind byte". **That retraction is
withdrawn; the original reading was right.**

`rider.node_writer_and_kind_byte` (VERIFIED, with a passing proof) already
documents exactly this and is the authority:

> THE QUEUED ROUTE to the same writer is `0x021C479C(side, slot, key, kind byte,
> [caller sp+0] = param)`, which packs animation command `0x35` ... its handler
> `0x021C3E68 -> 0x021BE044` unpacks it ... and calls `0x0219F190` with the FULL
> KIND BYTE INTACT. Both routes are legal from ordinary effect code.

So command `0x35` **is** the queued rider attach, `0x0221B2FC` **does** attach a
leave-rider, and `0x17` **is** its kind byte (high nibble 1 = a one-turn-boundary
countdown per `rider.turn_sweeper`; `kind & 0xF = 7` puts it in the 6..0xB
walker family, where the key at `+0` is a source-card locator).

Two lessons, both already written down elsewhere and both re-learned the hard
way here: **the YAML wins over a fresh disassembly read** (CLAUDE.md: where a
fact appears in both, the YAML with a passing proof is ground truth), and
recognising one call at the bottom of a wrapper is not the same as knowing what
the wrapper does. Nothing in the built patch depended on the wrong reading —
PART E is list membership and is independent of it.

What is still genuinely open is narrower than either version claimed: Escape
from the Dark Dimension passes the SAME kind `0x17` with the SAME 5th arg
(`r7 = 0`, set at `0x022075F6`) as Transformation, yet one destroys and the
other destroys-then-banishes. So the destroy/banish split is encoded neither in
the kind byte nor in the leave-cleanup list.

### ⭐ C4 IS A MEMBERSHIP LIST, AND IT HAS FREE PHANTOM SLOTS

`donor_scan 0x1768` and `donor_scan 0x1D2F` both report an unclassified hit in
the same structure — `ov3:0x0226E950` and `ov3:0x0226E970`. That is the KB's
`leave.attached_card_destroy_list` @ **`0x0226E940`**, searched at
`0x021CB3BC`: a sorted **40-entry** u16 list, indices 0..39, ending at `0x23A6`
(index 40 starts an unrelated list at `0x0E10`).

Every member is a card that puts a monster on the field and takes it away again
when it leaves: Premature Burial, Call of the Haunted, Birthright, Limit
Reverse, Fulfillment of the Contract, Hysteric Party, Miraculous Descent,
Fossil Excavation, Symbols of Duty, Graceful Revival, Wicked Rebirth,
**Ninjitsu Art of Transformation `0x1768`**, **Super Solar Nutrient `0x1F75`**,
**Escape from the Dark Dimension `0x1D2F`**.

**Indices 0 and 1 are PHANTOMS — `0x0E42` and `0x0E48`** (no `card_prop`
record). So C4's base behaviour is a **count-neutral insert**: drop `0x0E42`,
insert the donor `0x1255` in sorted position (it lands at index 2, just below
Amplifier `0x12D3`). **Pure data, no code.**

⚠️ What this list does NOT settle is **destroy vs banish**. Transformation
destroys, Escape destroys-then-banishes, and both are plain members — so the
distinction lives elsewhere (Escape's resolver branches on
`0x0202ABE8(cid) == 3` between `0x021C4A5C` and `0x021C479C`, but both of those
are animation-queue wrappers, so that is the visual and not the mechanic).
**C4 as an insert gives "the summoned monster leaves when this card leaves";
making that leave specifically a BANISH is still unproven.**

### The Special-Summon half is a criteria row + a race whitelist

NDS criteria registry `0x022713C4`:

| row | cid | aux | handler | word |
|---|---|---|---|---|
| 283 | `0x1768` | `-1` | `0x0223E769` | `0x00000002` |
| 822 | `0x1F75` | `-1` | `0x02241089` | `0x68000002` |

Both handlers are unique to their card. Disassembled, they are the same shape:

```
; 0x0223E768  (Transformation)   r0 = row, r1 = side, r2 = LEVEL CAP
0223E76C  ldr r4,=0x02271304 ; ldm/stm x2   ; copy a 4-word RACE LIST to [sp+8]
0223E77C  ldr r4,[r5,#8]                    ; the row's criteria word
0223E77E  cmp r2,#0xc ; bls ; movs r2,#0xc  ; clamp the level cap to 12
0223E784  movs r0,#2 ; lsls r1,r2,#0x12 ; lsls r0,r0,#0x16 ; orrs r0,r1 ; orrs r4,r0
0223E78E  ldr  r7,=0x0223C791               ; the race-list predicate
0223E79E  bl   0x0223C16C   ...  [sp+4] = 2   ; zone 2  = HAND
0223E7B0  bl   0x0223BC3C   ...  [sp+4] = 0xA ; zone 0xA = DECK
```

`0x02241088` (Super Solar Nutrient) is identical except it passes `r2 = 0` and
`r3 = 0` — **no race list at all**.

Three facts fall out, each independently checked:

1. **`(2 << 0x16) | (r2 << 0x12)` is exactly `(0x80 | (L << 2)) << 16`** — i.e.
   the "Level <= L" encoding of `counter.criteria_registry_layout`, written into
   the word at run time. So **the level cap is dynamic data, not a constant.**
2. **`0x02271304` = `{11, 16, 10, 0}` = Beast, Winged Beast, Insect** — an exact
   match to Transformation's printed text, which confirms the whole reading.
   Neighbouring lists in the same pool: `0x022712DC` `{11,16,0}`,
   `0x022712E8` `{15,7,0}`, `0x022712F4` `{11,12,16,0}`.
3. **Super Solar Nutrient's word `0x68000002` decodes as race only**: flags
   `0x0002`, extra `0x6800`, extra-high-byte `0x68` → race `0x68 >> 3` = 13 =
   **Plant**, attribute `0x68 & 7` = 0 = unrestricted. Its text says Plant-Type.
   This independently re-confirms `dispatch.criteria_word_race_attribute`
   against printed text, and shows **a SINGLE race needs no list and no code —
   it is one criteria row.**

### The level cap is delivered by the param provider's **L3** arm

The criteria handler's `r2` is the `param` produced by `0x02234E78`.
Disassembled the provider: five membership arms, then a per-cid switch.

| arm | list | n | site of its `bl 0x02022E14` | returns | owner |
|---|---|---|---|---|---|
| L1 | `0x022710E2` | 17 | `0x02234E84` | `desc[+0x0C]` | **claimed — `patch_ninja_grandmaster_hanzo` PART J** |
| L2 | `0x02271104` | 28 | `0x02234E96` | `1 << 0x1C` | **claimed — `patch_gates_of_dark_world`** |
| **L3** | `0x022710B2` | 12 | **`0x02234EAC`** | `desc[+0x14]` (u16) | **UNCLAIMED** |
| L4 | `0x0227109C` | 11 | `0x02234EC0` | `desc[+0x16]` | unclaimed |
| L5 | `0x022710CA` | 12 | `0x02234ED2` | `desc[+0x18]` | unclaimed |

**Both `0x1768` and `0x1F75` are members of L3.** Full L3 contents, resolved
against `card_prop`:

`0x0D4C` Speed Spell - Insect Imitation, `0x0D79` Speed Spell - Swallow's Nest,
`0x0DEA` Speed Spell - Metamorphosis, `0x140B` Insect Imitation,
`0x15A3` Metamorphosis, `0x1768` **NA of Transformation**,
`0x1A8D` Miracle Jurassic Egg, `0x1F75` **Super Solar Nutrient**,
`0x1FB3` Worm Queen, `0x1FD3` Synchro Change, `0x2083` Cyborg Doctor,
`0x20BA` Swallow's Nest.

**⚠️ L3 contains NO phantom** — all 12 are real cards. A count-neutral insert
would have to evict a real card, so the route for a new member is the
**unclaimed L3 hook at `0x02234EAC`**, exactly the technique Hanzo used for L1
and Gates of Dark World used for L2.

### Records-free Trap donors exist, and they are ALL Continuous Traps

Scanned all 4305 `card_prop` records for `card_type == "Trap Card"` cids absent
from all four cls tables, from the criteria registry `0x022713C4`, and from all
five provider lists: **40 candidates, every one of them subtype Continuous.**
(Makes sense: a Normal/Counter Trap needs a handler; a purely-passive Continuous
Trap's effect lives in the stat engine or a rider chain instead.)

⚠️ This is the CLAUDE.md (a)+(partial c) screen only. **`donor_scan` has NOT
been run on any of them yet**, so per-cid gates elsewhere in ov3/ov5 (stat
engine, rider chains, the `0x021D1392` switch, attack-restriction chains) are
**unchecked**. Do not propose a donor from this list without that run.

Best candidates by description budget (`desc_floor` = smallest slot across the 8
languages; descriptions are written **strictly in place** and a language is
skipped if it does not fit):

| cid | name | desc_floor | name_floor |
|---|---|---|---|
| `0x1DE2` | Sanguine Swamp | 182 | 8 |
| `0x1B66` | Swift Samurai Storm! | 156 | 12 |
| `0x2020` | Morphtronic Bind | 152 | 9 |
| `0x17BF` | Pyramid of Light | 139 | 13 |
| `0x14E3` | Dragon's Rage | 136 | 8 |
| `0x10EF` | Dragon Capture Jar | 131 | 14 |
| `0x1255` | Goblin Fan | 131 | 10 |
| `0x20A3` | Pixie Ring | 127 | 10 |
| `0x21E5` | Serpent Suppression | 125 | 13 |
| `0x2026` | Grave of the Super Ancient Organism | 120 | 16 |

The name `"Ninjitsu Art of Super-Transformation"` is **37 bytes with the NUL**
and no candidate's `name_floor` reaches that — but that is not a blocker:
`apply_stats_and_text` appends to the name blob and repoints the index when the
slot is short (Hanzo did exactly this for j/k). Only the **description** is
hard-capped in place.

### Hanzo's set code `0x2A` has room for this card

`0x0209C5D2` (4 entries, count immediate `movs r2,#4` @ `0x02023B14`) currently
reads `{0x1768, 0x17FF, 0x1C55, 0x1C5F}`, the last two being phantoms left as
padding by `patch_ninja_grandmaster_hanzo`. Neither is in
`otn_enhanced/docs/engine/allocations.yaml`, i.e. **both are unclaimed**. Dropping one and
re-sorting the four entries makes the new card Hanzo-searchable in **2 bytes**,
with no constraint on the donor cid.

### ⭐ THE 3DS → NDS SLOT MAPPING, BY SHARER-SET AGREEMENT

**USER DECISION 2026-08-31: build the FAITHFUL card (C1-C4 as printed), leaning
on the 3DS implementation because it is a working Konami implementation. Donor:
Goblin Fan `0x1255`.**

The method (reusable, and it is the reason this card stopped being blocked):
for each of the card's 3DS cls slots, collect **the set of cards that share that
slot value on the 3DS**, look every one of those cids up in the NDS cls tables,
and see which NDS function the NDS-present sharers agree on. **An agreeing
sharer-set is a structural equivalence proof** — the same family of cards hangs
off the same slot in both builds, so the two addresses are one function compiled
for two CPUs. This generalises the KB's hand-found
`threeds.deck_handler_equivalence` into something mechanical.

Script: `scratchpad/xbuild_map.py` (read-only; run
`.venv-1/Scripts/python.exe <path>/xbuild_map.py 0x26DD`).

Result for Super-Transformation `0x26DD`:

| slot | 3DS value | 3DS sharers | NDS verdict |
|---|---|---|---|
| +04 resolver | `0x00457B38` | **1** (itself) | **no NDS twin — bespoke, must be written** |
| +08 candidate pred | `0x003ED908` | 7 | **split 1-1**: Common Soul → `0x021DD859`, Faustian Bargain → `0x021E3919`. Only 2 of 7 sharers exist on the NDS and they disagree — **unresolved** |
| +0C activation cond | `0x0049D734` | 6 | **`0x021F8549`, 3/3 unanimous** (Beast Soul Swap `0x1889`, NEX `0x1BFA`, Mask Change `0x236A`) = the "send/return the targeted monster, then Special Summon a replacement" condition |
| +10 cost | NULL | — | — |
| +14 target decl | `0x00478390` | 32 | **`0x02235C75`, 16/16 unanimous** = **the TWO-TARGET declaration template** |

### `0x02235C75` is the two-target declaration, and Bubble Shuffle is the precedent

The 16 NDS cards sharing `+14 = 0x02235C75`, with their printed texts, are
overwhelmingly "target N cards **across both sides**":

| cid | card | printed shape |
|---|---|---|
| `0x1908` | **Bubble Shuffle** | **1 named monster you control AND 1 face-up monster your opponent controls → Tribute yours → Special Summon a replacement** |
| `0x2311` | Double Cyclone | 1 S/T you control and 1 S/T your opponent controls; destroy them |
| `0x2310` | Blind Spot Strike | 1 face-up DEF monster your opponent controls and 1 face-up ATK monster you control |
| `0x12E7` | Two-Pronged Attack | 2 of your monsters and 1 of your opponent's |
| `0x23F0` | Liberty at Last! | target 2 face-up monsters on the field |

plus Xing Zhen Hu, Icarus Attack, Treacherous Trap Hole, Chain Whirlwind,
Widespread Dud, Morphtronic Mix-up, Synchro Gift, Nordic Relic Brisingamen,
Offering to the Snake Deity, Trap of the Imperial Tomb, `0x0E6F`.

**Bubble Shuffle `0x1908` is the closest thing in the ROM to C2+C3**:

> Target 1 face-up Attack Position "Elemental HERO Bubbleman" you control **and**
> 1 face-up Attack Position monster your opponent controls; change both those
> targets to Defense Position, then **Tribute** that "Elemental HERO Bubbleman",
> then **Special Summon** 1 "Elemental HERO" monster from your hand.

Its NDS wiring:

| | value |
|---|---|
| cls0[627] | `{0x1908, +04 0x0221EBBD, +08 0x021E00D9, +0C 0x021F9671, +10 0, +14 0x02235C75}` |
| criteria row 370 | `{0x1908, aux 8, fn 0x0223CA71, word 0x00000002}` |

`aux 8` is a has_set_code index ("Elemental HERO"), and `0x0223CA71` is a
**HAND** handler (24/24 in the KB's `counter.criteria_handler_selects_container`
census) — consistent with "Special Summon … from your hand". For our card that
handler swaps to a **Deck** one, which is the same axis Transformation already
demonstrates.

So the faithful build now has a source for every clause:

| clause | mechanism | inherited from |
|---|---|---|
| C1 | card_prop + 8-language text + 2-byte set-code `0x2A` entry | Hanzo |
| C2 | `+14 = 0x02235C75` two-target declaration + a `+08` candidate predicate splitting "Ninja you control" from "face-up monster your opponent controls" | **Bubble Shuffle `0x1908`** |
| C3 | criteria row w/ a Deck handler + an ov5 clone of `0x0223E768` carrying a new `{1, 9, 5, 0}` race list; level cap through the unclaimed **L3 hook `0x02234EAC`** | Transformation `0x1768` |
| C4 | rider kind byte in an ov5 clone of the 0x30-byte wrapper `0x0221B2FC` | Transformation `0x1768` |
| +04 | must be written — no shared resolver exists in either build | — |

### ⭐ Bubble Shuffle's `+08` IS the two-side split, and it is ~40 bytes

Disassembled `0x021E00D8` in full. This is the single most reusable thing found
this session:

```
021E00D8  push {r3,r4,r5,lr}
021E00DA  ldrb r3,[r0,#2]       ; r0 = descriptor; [+2] = the ACTING side
021E00DC  adds r5,r1,#0         ; r1 = candidate side
021E00DE  adds r4,r2,#0         ; r2 = candidate zone
021E00E0  cmp  r5,r3
021E00E2  bne  0x021E00FE       ; --- candidate is on the OPPONENT's side ---
021E00E4  ldr  r3,=0x00040495   ; --- candidate is on MY side ---
021E00E6  bl   0x021D6E40       ; the zone predicate (face-up ATK, my field)
021E00EA  cmp  r0,#0 ; beq 0x021E00FA  -> return 0
021E00EE  ldr  r2,=0x000018F9   ; Elemental HERO Bubbleman
021E00F0  adds r0,r5,#0 ; adds r1,r4,#0
021E00F4  bl   0x021A3800       ; "is the card at (side, zone) this cid?"
021E00F8  pop  {r3,r4,r5,pc}
021E00FA  movs r0,#0 ; pop {r3,r4,r5,pc}
021E00FE  ldr  r3,=0x00040496   ; opponent's side: zone predicate only
021E0100  bl   0x021D6E40
021E0104  pop  {r3,r4,r5,pc}
```

**ONE predicate serves both targets and branches on `[desc+2] == candidate
side`.** My side gets zone-mask `0x00040495` + a cid test; the opponent's side
gets zone-mask `0x00040496` and nothing else. The two masks differ only in the
low nibble (5 vs 6) — the side bit of `0x021D6E40`'s mask encoding.

**C2's predicate is this function with `0x021A3800(side, zone, cid)` replaced by
a Ninja set-code test** (`has_set_code(cid, 6)` via `0x020240D8`, the path
`dispatch.criteria_aux_is_has_set_code_index` already documents). ~40 bytes of
Thumb-1 in ov5.

### `0x02235C74` (+14) is a per-cid switch — the donor needs an arm or a hook

```
02235C74  push {r3,r4,r5,r6,r7,lr}
02235C76  adds r4,r0,#0
02235C78  ldrh r2,[r4]          ; the ACTING cid
02235C7A  mov  ip,r1
02235C7C  ldr  r1,=0x00001DB4   ; switch pivot
02235C7E  ldr  r6,=0x0229AB7C
02235C80  movs r7,#1            ; defaults
02235C82  movs r5,#2
02235C84  cmp  r2,r1 ; bgt/bge ...   ordered binary search, arms as base+/-imm
```

**⭐ DECODED 2026-08-31 — and it removes C2's biggest risk entirely.** The tree
is an ordered comparison chain with the base literal `0x1DB4` held in `r1`/`r0`
(it is NOT spilled to the stack here, so it is readable statically; the
`thumb.stack_based_switch` hazard does not bite on this one). Arms, with each
cid resolved against `card_prop`:

| cid | card | effect |
|---|---|---|
| `0x0E07` | Speed Spell - High Speed Crash | `r7 = 0` |
| `0x12E7` | Two-Pronged Attack | `r5 = 3` |
| `0x18F8` | *phantom* | leaf `0x2235CF6` (r5 from table `0x0229ACD4`) |
| `0x1CFC` | Dark Nephthys | leaf `0x2235CF6` |
| `0x1D34` | Offering to the Snake Deity | `r5 = 3` |
| `0x1DB4` | Batteryman Industrial Strength | `r7 = 0` |
| `0x1E7C` | Red Ogre | leaf `0x2235CF6` |
| `0x2046` | Gungnir, Dragon of the Ice Barrier | leaf `0x2235CF6` |
| `0x2100` | Solitaire Magician | `r7 = 0` |
| `0x2396` | Dance Princess of the Ice Barrier | leaf `0x2235D16` |
| `0x23A1` | Scrap Twin Dragon | `r5 = 3` |
| `0x240C` | *phantom* | `r7 = 0` |
| — | **DEFAULT** | **`r7 = 1`, `r5 = 2`** |

**`r5` is the TARGET COUNT.** Every `r5 = 3` arm belongs to a card printed with
three targets (Two-Pronged Attack "2 of your monsters and 1 of your opponent's";
Offering to the Snake Deity; Scrap Twin Dragon), and the default `r5 = 2` is
what two-target cards get.

**⭐ Bubble Shuffle `0x1908` is NOT in the arm set — it runs on the DEFAULT.**
So does Goblin Fan `0x1255`. **CONSEQUENCE: C2 needs no switch arm and no hook
at `0x02235C74`.** Pointing the donor's `+14` at `0x02235C75` inherits Bubble
Shuffle's two-target, both-sides declaration byte for byte, as data.

### `donor_scan` screen of the shortlist (run this session)

`.venv-1/Scripts/python.exe -m otn_enhanced.tools.donor_scan <cid>` on eight
candidates. **All eight report `ENTANGLED`** — but the counts differ by an order
of magnitude, and most hits are coincidental u32 literals rather than table rows:

| cid | card | binding occurrences | note |
|---|---|---|---|
| `0x1255` | Goblin Fan | **1** (`ov3:0x02268C48/u32`) | **CHOSEN.** A literal-pool word feeding one guarded block — see the section below |
| `0x14E3` | Dragon's Rage | **1** (`ov3:0x021A775C/u32`) | referenced by `ldr r1,[pc,#0x1CC]` @ `0x021A758E` — a per-cid switch constant, i.e. the donor's own stock effect |
| `0x21E5` | Serpent Suppression | **1** (`ov3:0x02198A48/u32`) | referenced by `ldr r1,[pc,#0x26C]` @ `0x021987D8` — same shape |
| `0x1DE2` | Sanguine Swamp | 6 | incl. `ov3:0x022756F4/u16` |
| `0x10EF` | Dragon Capture Jar | 5 | incl. `ov3:0x022754F8/u16` |
| `0x2026` | Grave of the Super Ancient Organism | 7 | incl. ARM9 u32 hits |
| `0x2020` | Morphtronic Bind | 4 | `ov3:0x02271156/u16` |
| `0x20A3` | Pixie Ring | 2 | `ov3:0x0227115A/u16` |

The `0x0227115x` u16 hits are membership in a **sorted response-timing list**
running `0x0227113C`..`0x02271160` — its members are Threatening Roar, Taunt,
A Feint Plan, Frozen Soul, Array of Revealing Light, Effect Veiler, Formula
Synchron etc., i.e. cards activatable in response / on the opponent's turn.
Identified by dumping the region and resolving each u16 against `card_prop`.
Not a continuous-trap registry, and **the "how does a Continuous Trap activate"
question is still open** — nothing found this session answers it.

**Best three donors on this screen: Goblin Fan `0x1255`, Dragon's Rage `0x14E3`,
Serpent Suppression `0x21E5`** — one occurrence each, and for the latter two it
is a per-cid switch arm implementing the donor's own stock effect, which is the
routine "retarget the donor's own arm" neutralisation
(`patch_gates_of_dark_world` precedent). ⚠️ None of the three has been checked
for the CLAUDE.md (d) criterion, and none has been presented to the user for
approval — **no donor is chosen.**

### Retiring Goblin Fan's stock text is a ONE-WORD write

⚠️ **CORRECTION to an earlier claim in this same session.** I first reported that
nothing referenced `0x02268C48`, based on a linear capstone disassembly walking
backwards from the pool — that scan drifts through literal pools and is
unreliable. An **exhaustive halfword scan** for the Thumb `LDR Rd,[PC,#imm]`
encoding (`0x48xx`..`0x4Fxx`) over `[POOL-1024, POOL]` — alignment-independent,
and 1020 B is the full reach of that encoding — finds **two** references:

```
02268B04  ldr r6,[pc,#0x140]   ; = 0x1255
02268B38  ldr r3,[pc,#0x10C]   ; = 0x1255
```

Both are inside one block, and the block **is Goblin Fan's printed effect**,
inline in a shared Flip-Summon handler. Printed text: *"When a Level 2 or lower
monster is Flip Summoned, destroy it. Its effects do not activate at that time."*

```
02268AF8  ldrh r0,[r4,#2] ; ldrh r1,[r4,#4]
02268AFC  bl   0x021B8064          ; -> the flipped monster's LEVEL
02268B00  cmp  r0,#2
02268B02  bgt  0x02268B4C          ; "Level 2 or lower"
02268B04  ldr  r6,=0x1255
02268B06  adds r0,r6,#0 ; bl 0x021AC204   ; is Goblin Fan face-up on the field?
02268B0C  cmp  r0,#0 ; beq 0x02268B4C     ; no -> skip the whole block
...       0x021CF898 / 0x021D290C / 0x021AC0C8 / 0x021CF35C  ; destroy it
02268B44  ldrh r0,[r4,#0x24] ; adds r0,#1 ; strh r0,[r4,#0x24]
```

The `cmp r0,#2 / bgt` gate matching "Level 2 or lower" is what identifies the
block beyond doubt.

**CONSEQUENCE, and it is good news:** the whole block is gated by
`0x021AC204(0x1255) != 0` = "is cid `0x1255` face-up on the field". Our converted
card **keeps that cid**, so if left alone the new Ninjitsu Art card would also
destroy every Flip Summoned Level-2-or-lower monster. Neutralising it is a
**single u32 write** — repoint the literal at `0x02268C48` from `0x1255` to a
phantom cid, and `0x021AC204(phantom)` returns 0 so the `beq` skips the block
forever. Both `ldr` sites read the same word, and the second is downstream of
the gate, so one write retires both.

That is **cleaner than the other two candidates**, whose single occurrence is a
per-cid *switch arm* rather than a pool word. The donor choice stands, and for a
better reason than the one it was originally made on.

---

## IN-GAME TEST 1 (2026-08-31) — FAILED, and the savestate says where it did NOT fail

User's exact words:

> See .ml2, when I search with hanzo, the game freezes and i cannot pick anything

Savestate `data/over_the_nexus/working/rom_nast.ml2` (13:07, after the 13:01
build). Parser: `scratchpad/nast_state.py`.

⚠️ **The RAM-base auto-detect needs a plausibility filter.** The anchor byte
pattern for `0x021A25A0` occurs **twice** in the file (`0x1A24A4` and
`0x1A25C4`); a bare `find()` takes the first and yields a **negative** base of
`-0xFC`. That is not obviously wrong in the output, because `0x120` happens to be
an exact multiple of BOTH the criteria stride (12) and the cls stride (24), so
every table row still decodes correctly and only the row INDEX is shifted — while
ARM9 and ov5 reads silently return garbage. The correct base is **`0x24`**.
Filter candidates to `0 <= base < 0x1000`.

### Confirmed by the savestate — the whole search pipeline WORKS

* **ROM identity**: both ov5 stubs match the built blobs byte for byte, and set
  code `0x2A` reads `{0x1255, 0x1768, 0x17FF, 0x1C5F}`. Right ROM.
* **PART A works.** Hanzo's two criteria rows are intact at 122/123; our row is
  at 79 `{0x1255, aux -1, fn 0x0239D991, word 0x02}`; our cls0 record is at 133.
* **The search RAN and SUCCEEDED.** The candidate buffer
  (`dispatch.banished_walker_and_candidate_buffer`) holds **6 entries**, and both
  the count at `0x0229944C+2` and the one at `+6` read 6:

  | # | word | cid | card |
  |---|---|---|---|
  | 0,1,3 | `0x01801255` / `0x00801255` / `0x01001255` | `0x1255` | **Ninjitsu Art of Super-Transformation** ×3 |
  | 2,5 | `0x09001768` / `0x09801768` | `0x1768` | Ninjitsu Art of Transformation |
  | 4 | `0x0A8017FF` | `0x17FF` | Ninjitsu Art of Decoy |

* **The selection machine is set up for Hanzo**: `0x0229DD94+0x64` = `0x13E7`,
  side 0. So this is **clause 1**, and the new card really is being offered.
* The resolver is parked at phase **`0x7E`** with step counters `0x0229AAFC+0x74`
  and `+0x7C` and `0x0229AB7C` all zero — i.e. waiting on a pick that never
  arrives.

**So the failure is NOT in the set-code list, the criteria row, the deck walker,
or the candidate recorder.** It is downstream of a correctly-populated
6-candidate buffer.

### Ruled out this session, without spending a duel

* **"The 36-character name overflows a UI buffer."** FALSIFIED by measurement:
  the longest stock name per language is **e 47 / f 60 / g 62 / i 59 / s 57 /
  j 64 / k 38 / r 110** bytes. Ours is 36 — unremarkable in every language.
* **"The appended name is malformed."** Not so: in all 8 languages the index
  points at a correctly NUL-terminated 36-byte string, the blobs grew by exactly
  0x25, and neither `card_name_*.bin` nor `card_indx_*.bin` carries a length in
  its header that we failed to update (`card_indx` is unchanged at 4306 entries).
  `donor.name_blob_has_no_slack` is about `_place_string`'s trailing-padding
  fallback, which is a different mechanism from the append-and-repoint that
  `apply_stats_and_text` does and that Hanzo already ships in j/k.

### Next experiment — the bisect, and a FREE control first

The remaining suspects are all things this patch gave the donor that it did not
have before, all downstream of the candidate buffer:

1. the donor now owns a **cls0 record** where it owned none — in particular a
   `+08` candidate predicate. `dispatch.cls2_plus08_is_the_per_card_candidate_filter`
   is explicit that **a card with NO `+08` accepts every candidate**, and the
   generic sweepers feed `+08` zones 0..0xA. Our stub's mask `0x0C15` has
   zone-class 1 = "zone < 5", so for a DECK candidate it returns 0 = reject.
2. the cls0 insert **shifted records 45..133**; the criteria insert shifted rows
   12..79.
3. PART B's literal rewrite at `0x02268C48`.

**FREE CONTROL, no new build:** `rom_nast_hanzo.nds` already exists on disk — it
is the same chain with Hanzo applied and this card NOT applied. If Hanzo's
Normal-Summon search is fine there and freezes on `rom_nast.nds`, this patch is
confirmed as the cause and suspect (1)/(2) survive; if it freezes there too, the
cause is older than this card entirely.

## IN-GAME TEST 2 — the TEXT BISECT (built 2026-08-31, awaiting result)

User refined the symptom:

> perhaps the bug is coming from whenever I have nast in my hand the game
> freezes... probably due to text overflow

If that is right the freeze is not about Hanzo's search at all — the search was
merely what put the card in hand, which is consistent with the savestate showing
the whole search pipeline completing correctly.

Two more hypotheses died statically before building anything, so no duel was
spent on them:

* **Description overflow — NO.** Ours is 123 B; stock descriptions run to a
  **median of 165 B and a maximum of 657 B**. Ours contains no control bytes,
  and neither does Goblin Fan's stock text. (496 stock descriptions do carry
  CR/LF pairs, so line breaks exist but are not required.)
* **The activation condition `0x021F8549` — NO.** Disassembled: it is
  straight-line, `0x021D2BC8` -> `0x0224AE70` -> `0x021B9ECC`, returning 0 or 1.
  No per-cid switch, no loop, nothing a new cid can default into badly.

**BUILD:** `.venv-1/Scripts/python.exe _build_nast.py --no-text`
ROM `data/over_the_nexus/working/rom_nast_notext.nds`
sha256 `b865146ea708cd282f1e5be05ee5ea558dbdd0448b6667ed77c60568d6a7f3ec`

Every effect part (A/B/C/D/E/F) is applied, but `bin2.pac` is left **completely
untouched** — verified byte-identical to the Hanzo-only input ROM
(`bin2` sha256 prefix `769324b5b9019833`, size 10,974,768 in both). The card
still reads **"Goblin Fan"** with Goblin Fan's stock description.

⚠️ A build accident worth remembering: the old `_build_nast.py` derived
`write_text` as `"--text" in sys.argv`, so the first `--no-text` run silently
skipped **Hanzo's** text too AND overwrote `rom_nast.nds`. The flag is now
`"--no-text" not in sys.argv`, Hanzo always gets its text, and the bisect writes
to its own path. `rom_nast.nds` was rebuilt and is back to
`22c6112db710c4863d27d5a67bfab46dd0626f4e8c33d40800ce141b0822bb4d`.

**WHAT THE RESULT MEANS**

| outcome | conclusion |
|---|---|
| card sits in hand fine | the effect records are innocent; the **text** is the cause, and the next step is narrowing name vs description |
| still freezes | the text is innocent; the cause is the **cls0 record / criteria row** the card now owns (prime suspect: the `+08` predicate, since `dispatch.cls2_plus08_is_the_per_card_candidate_filter` says a card with NO `+08` accepts every candidate, and ours rejects any zone >= 5) |

## IN-GAME TEST 2 RESULT (2026-08-31) — TEXT CONFIRMED as the in-hand freeze; ROOT CAUSE of the resolution freeze FOUND

User's exact words:

> Okay. --no-text stopped the freeze so I was able to normal summon hanzo and
> search goblin fan/nast without it causing a crash. Also no regressions on
> machina gearframe.
>
> However, when I activate NAST, I am able to select 2 monsters. However it only
> changes the battle positions of the monsters and then freezes wheb the effect
> is resolving. See .ml3.

### CONFIRMED WORKING (user-observed)

* **The in-hand freeze is the TEXT.** With `bin2.pac` untouched the card can sit
  in hand, be searched and be added with no crash. The effect records are
  innocent of it.
* **Hanzo clause 1 fetches the new card** — the user's `search goblin fan/nast`.
* **No regression on Machina Gearframe.**
* **C2's TWO-TARGET DECLARATION WORKS.** The user selects 2 monsters. That
  confirms `dispatch.two_target_declaration`: pointing `+14` at `0x02235C75` and
  taking the DEFAULT arm really does give a records-free donor a two-target,
  both-sides declaration with zero code.
* The battle-position change happens, exactly as predicted in the module's
  DEVIATIONS list.

### ⭐ ROOT CAUSE — BUBBLE SHUFFLE'S RESOLVER HARD-CODES ITS OWN CARD'S CID

`0x0221EBBC` phase `0x7F` (`0x0221EC46`..`0x0221ECA0`):

```
0221EC46  ldrh r0,[r5,#0x12]           ; the declared-target count
0221EC48  subs r4,r0,#1                ; walk the targets backwards
0221EC4C  ... 0x02234904 -> unpack target into side r6 / zone r7
0221EC68  bl 0x021AFCBC(desc,side,zone)      ; nonzero -> skip this target
0221EC76  bl 0x021AE124(desc[+2],side,zone)  ; zero    -> skip this target
0221EC7E  ldr r2,=0x000018F9                 ; *** ELEMENTAL HERO BUBBLEMAN ***
0221EC84  bl 0x021A3800(side,zone,0x18F9)    ; "is this target THAT cid?"
0221EC88  cmp r0,#0 ; beq skip
0221EC92  bl 0x021CF6B8(desc,side,zone)      ; <- the TRIBUTE
0221EC9E  movs r0,#0x7E
```

`0x18F9` is **Elemental Hero Bubbleman** (`0x18F8` is a phantom; Bubble Shuffle
itself is `0x1908`). Its printed text is *"Tribute that 'Elemental HERO
Bubbleman'"* — the resolver implements that clause **by cid**, so **no card other
than Bubble Shuffle can ever pay this cost.** Our targets are a Ninja and an
opponent's monster; neither is `0x18F9`; nothing is tributed; resolution cannot
reach the summon.

**This is `grep-the-template-cards-text-too` exactly, and I walked into it.** I
disassembled the resolver's HEAD, found no cid compare in the phase dispatch, and
recorded "card-AGNOSTIC in its head ... so the donor reuses it directly". The
head is agnostic; the phase-`0x7F` BODY is not. **A 0x50-byte look at a
multi-phase resolver is not a check for hard-coded cids — every phase body has to
be read.**

### Savestate corroboration (`rom_nast_notext.ml3`, base 0x24)

* ROM identity confirmed (both ov5 stubs match, tables correct).
* Resolver phase `[0x0229AAFC+0x70]` = **`0x80`**.
* **Candidate buffer count = 0** — the Deck search never produced anything.
* And it is NOT because the Deck is empty of legal targets: side 0's 35-card Deck
  holds **Handcuffs Dragon `0x1E1F` (Dragon), Dark Driceratops `0x16FF`
  (Dinosaur) and Divine Dragon Aquabizarre `0x207D` (Sea Serpent)** — all three
  races, all legal. The criteria handler simply never ran, because the cost
  before it never completed.
* Field at the freeze: side 0 zone 2 Melchid/Hanzo `0x13E7`, side 1 zone 2
  Gladiator Beast Laquari `0x1C76` — i.e. exactly the two declared targets, both
  still on the field, un-tributed.

⚠️ **The criteria handler `CAVE_NAST_CRIT` is NOT exonerated and NOT convicted** —
it was never reached. Its missing level bits remain an open question for the next
test (Transformation ORs `(0x80|(L<<2))<<16` into the word from `param`; ours
omits the level field entirely, and whether 0 there means "no bound" or
"Level <= 0" for this handler family is still unproven).

### The fix

Our card needs **its own resolver** in ov5 — which was always true (the 3DS says
this card's `+04` is used by exactly one row, i.e. Konami wrote it bespoke; I
tried to dodge that by borrowing Bubble Shuffle's and the borrow is what failed).
A clone of `0x0221EBBC` with three changes, each of which also RETIRES one of the
module's stated deviations:

1. phase `0x80`: drop the `bl 0x021C5324` battle-position change — our card does
   not print it.
2. phase `0x7F`: replace the `0x18F9` cid test with "send **both** declared
   targets to the GY" (`0x021CF6B8` is the tribute/send primitive already in
   hand), which is what the printed card says and which also fixes the
   "opponent's monster survives" deviation.
3. phase `0x7E`: leave the summon path, which then reaches our criteria row.

## ROUND 2 BUILD (2026-08-31) — the ov5 resolver

`CAVE_NAST_RES = 0x0239D9E0`, **216 B of 0xE0**, built with the repo's own
label-resolving Thumb-1 assembler (`otn_enhanced.asm.thumb_asm.asm`) rather than
hand-encoded halfwords.

⚠️ **`asrs` was missing from `thumb_asm`** and is now added — the shift-by-
immediate family is LSL `0x0000` / LSR `0x0800` / **ASR `0x1000`**, and only the
first two were implemented. Cross-checked against capstone. Additive change; no
existing mnemonic is touched.

**A 3DS byte-transplant is NOT possible and was never the plan.** The 3DS is
ARM11 executing 32-bit ARM; injected NDS code must be ARMv5TE **Thumb-1**, and
every branch target, literal and struct offset in the 3DS function refers to 3DS
addresses. The 3DS supplies *architecture and data* — which handler family, which
zone, which criteria word, and equivalences proved by sharer-set agreement. The
clone source for executable code is always an **NDS** function.

Resolver = Bubble Shuffle's `0x0221EBBC` with exactly two changes:

| phase | Bubble Shuffle | ours |
|---|---|---|
| `0x80` | validate declared targets, then a second loop calling `0x021C5324` to flip both to Defence Position | validation loop only — **the position change is dropped** (that clause is Bubble Shuffle's, not ours) |
| `0x7F` | find the ONE target whose cid is `0x18F9` and `0x021CF6B8` it | **loop EVERY declared target** through both guards to `0x021CF6B8`; no cid test, no early break |
| default | `phase += 2`, `bl 0x0220667C`, return | identical, verbatim |

`0x021CF6B8(desc, side, zone)` was checked before reuse: it builds
`1 << (zone + side*16)` and calls `0x021CDD4C` with destination **`0x0E` =
Graveyard** (`ram.container_for_zone_code`), so it is a generic, side-agnostic
send-to-GY and works on the opponent's monster.

Literal pool verified — all 8 entries present with the Thumb bit set:
`PHASE_BLOCK 0x0229AAFC`, `TARGET_FETCH 0x022349B1`, `TARGET_UNPACK 0x02234905`,
`TARGET_STILL_LEGAL 0x0224A925`, `AFFECT_GUARD 0x021AFCBD`,
`TARGET_GUARD 0x021AE125`, `SEND_TO_GY 0x021CF6B9`, `SUMMON_STEP 0x0220667D`.

**Also fixed this round: the criteria handler now writes the LEVEL FIELD.**
Round 1 omitted it entirely; Transformation's handler always ORs
`(0x80 | (L << 2)) << 16` in from `param`. Ours now hardcodes the clamp maximum
`LEVEL_BITS = 0x00B00000` (= "Level <= 12"). Whether a zero level field means
"no bound" or "Level <= 0" for this handler family is still unproven — but since
the round-1 Deck search returned 0 candidates against a Deck that provably held
three legal monsters, writing the field explicitly is the safer reading.

Guards kept deliberately: `0x021AFCBC` (a protection/affect test) and
`0x021AE124`. `0x021AE124`'s behaviour on an OPPONENT's monster is **unproven** —
Bubble Shuffle never exercised it there, because only its own Bubbleman ever got
past the cid test. If in-game only the player's Ninja reaches the GY, that guard
is the first suspect and dropping it is the fix.

`verify()` all-pass, `check_allocations` OK (151 ov5 slots, no collisions),
`verify_knowledge` 366 facts / 331 PASS / 0 FAIL.

## IN-GAME TEST 3 (2026-08-31) — the resolver WORKS; the opponent-side guard does not

User's exact words:

> See .ml3, My monster (hanzo went to the GY) and then the game froze

Savestate `rom_nast_notext.ml3` (14:05), all three ov5 stubs matching the ROUND 2
build, so the right ROM.

### CONFIRMED — the round-2 resolver does what it was written to do

* **Side 0 GY = 1 card: Melchid (= Hanzo).** Phase `0x7F` ran, the guards passed
  for the player's own monster, and `SEND_TO_GY 0x021CF6B8` moved it. The clone,
  the ov5 hosting, the `blx`-through-literal calls and the loop all work.
* No battle-position change was reported — that removal held.

### THE BUG — the opponent's monster is silently skipped

* Side 1 zone 2 still holds **Gladiator Beast Laquari `0x1C76`**, and **side 1's
  GY is EMPTY**. Only one of the two declared targets was sent.
* Cause, disassembled: `TARGET_GUARD 0x021AE124` wraps
  `0x021AD8F4(acting_side, side, zone, mode=1)`, which at `0x021AD93E` does
  `cmp acting, side` and branches:
  * **same side** -> `0x021AD964`, a chain of `0x021A1430(side, zone, KEY)`
    protection-rider lookups (keys `0x16A4`, `0x0DCC`, `0x12D1`, `0x1F70`), each
    of which REJECTS only if the rider is present. Accepts by default.
  * **opposite side** -> `0x021A14B4` with keys `0x0DDE`, `0x13EB`, ... — an
    opponent-specific chain, and it rejected an ordinary Gladiator Beast.
* **That opponent-side path was DEAD CODE for Bubble Shuffle**: its `0x18F9` cid
  test meant only its own Bubbleman ever reached the guard, so the branch was
  never exercised by the card the code was written for. Cloning it inherited an
  untested path — the same shape of trap as the hard-coded cid itself.

**FIX (round 3):** call the guard with the **candidate's own side** in r0
(`adds r0,r6,#0` instead of `ldrb r0,[r5,#2]`). That forces the same-side
landing, so every generic "cannot be targeted" protection rider is still
honoured and only the "your opponent may not touch this" tests are skipped —
which is exactly what this card's text overrides by naming the opponent's monster
as a target.

### Also decoded — `SUMMON_STEP 0x0220667C` is a per-cid switch, and its DEFAULT IS FINE

`ldrh r3,[r4]` against a pivot tree (`0x2048`, `0x16FD`, `0x12CA`, `0x1A81`,
`0x2459`, ...). ⚠️ It looked at first like another Bubble-Shuffle-only gate, but
it is not: **every arm merely sets parameters and then branches to the common
convergence point `0x02206776`** (arms set `r5` = 2 / 4 / 5, or tweak `r6` /
`[sp+8]`), and an unlisted cid simply keeps the defaults `r5=1, r6=0, r7=1`.
`r5 = 1` is what a one-monster summon wants. So the donor needs **no arm here**,
and this is NOT the reason the candidate buffer read 0.

### Still open

The candidate buffer read **0** again even though the round-2 build writes the
level bits. The most likely reading is that the summon never legitimately ran
because the cost was incomplete (only one of the two targets was sent) — but that
is an INFERENCE, not a measurement. If round 3 sends both monsters and the picker
is still empty, the criteria handler `CAVE_NAST_CRIT` is the next suspect and the
level field is the first thing to vary.

**ROUND 3 BUILD:** `data/over_the_nexus/working/rom_nast_notext.nds`
sha256 `ec5929612b6d4cc7d375e9e3b4a78d3a56d6785eeb6166e43cc64abc8dd7125e`

## IN-GAME TEST 4 (2026-08-31) — cost COMPLETE; summon still dead

User's exact words:

> 1. Both monsters go to the GY
> 2. Game freezes

**C2 IS NOW FULLY WORKING.** Two targets declared across both sides, both sent to
the GY. The side-argument fix to `TARGET_GUARD` was correct. Everything from
activation through cost is done:

| clause | state |
|---|---|
| C1 exists + Hanzo-searchable | working (with stock text) |
| C2 target 1 Ninja + 1 opponent monster, send BOTH to GY | **working** |
| C3 Special Summon from Deck | **DEAD — freezes** |
| C4 leave-cleanup | not yet reachable |

### ESCALATION TO MEASUREMENT (otn-escalate-to-measurement)

That is **two consecutive failures on the summon half**, and a static re-read
shows my criteria handler matches Transformation's byte-for-byte on every axis
that could plausibly matter:

* stack-argument convention — `0x0223BC3C` does `push {r3..r7,lr}` + `sub sp,#0x50`
  and reads `[sp,#0x68]`/`[sp,#0x6c]`, i.e. the caller's `[sp+0]`/`[sp+4]`, which
  is exactly what the stub writes;
* `[sp+4] = 0x0A` is a **type bitfield**, NOT a zone (bit 1 = both players, bit 3
  = container-presence per `dispatch.criteria_registrar_type_and_criteria_bits`) —
  and Transformation passes the same 0x0A to the same walker;
* the word: Transformation ORs `(2<<0x16)|(r2<<0x12)`, which for r2=12 is exactly
  our hardcoded `0x00B00000`;
* the race list is 3 races + a 0 terminator, same shape, and the predicate
  `0x0223C791` is identical.

So a third guess would be exactly the pattern CLAUDE.md's two-strike rule forbids.
**Round 4 instruments instead.**

### ROUND 4 — the DEBUG build

`CAVE_NAST_DIAG = 0x0239D990`, 0x20 B. ⚠️ **DEBUG ONLY, STRIP BEFORE SHIPPING**
(the `card.eclipse_wyvern` precedent).

| offset | meaning |
|---|---|
| `+0x00` | times `CAVE_NAST_CRIT` was entered |
| `+0x04` | the Deck walker's last return value |
| `+0x08` | times the resolver's default arm called `0x0220667C` |
| `+0x0C` | that call's last return value |

`r4` is callee-saved, so the criteria stub keeps the DIAG pointer across the
walker call and banks the return with `str r0,[r4,#4]`.

**This splits the remaining question in one duel:**

* `+0x00 == 0` -> the handler is **never entered**; the summon step never reaches
  the Deck search, and the fault is upstream in `0x0220667C`'s phase machine.
* `+0x00 > 0` and `+0x04 == 0` -> the handler **runs and finds nothing**; the
  filter itself is wrong (race list / word / level bits) and the next variable to
  move is the level field.
* `+0x08` also shows how many times the phase machine span, confirming the
  infinite-loop reading of the freeze.

Cave map after the reshuffle (the criteria stub outgrew its old 0x50 slot once
instrumented and moved twice):

```
CAVE_NAST_PRED 0x0239D940   72 B of 0x50
CAVE_NAST_DIAG 0x0239D990   32 B of 0x50   (DEBUG)
CAVE_NAST_RES  0x0239D9E0  228 B of 0x100
CAVE_NAST_CRIT 0x0239DAE0   92 B of 0x60
CAVE_FREE      0x0239DB40
```

**ROUND 4 BUILD:** `data/over_the_nexus/working/rom_nast_notext.nds`
sha256 `37dea2a70f0f670554e59a3c156b8fa0e5db9c640da60128ff0b0a1ed857b7bb`
`check_allocations` OK (152 ov5 slots, no collisions).
Reader: `scratchpad/nast_state.py` now prints the DIAG block.

## IN-GAME TEST 5 (2026-08-31) — the instrumentation paid off immediately

Savestate `rom_nast_notext.ml3` (14:29). DIAG block read:

| counter | value | meaning |
|---|---|---|
| `+0x00` | **0** | `CAVE_NAST_CRIT` was **NEVER ENTERED** |
| `+0x04` | 0 | (walker never ran) |
| `+0x08` | **1** | the resolver called `0x0220667C` exactly **once** |
| `+0x0C` | **0** | and that call returned **0** |

### Two things this settles outright

* **THE CRITERIA HANDLER IS INNOCENT.** Every round-1..4 worry about the race
  list, the level bits and the container index was aimed at code that never
  executes. `LEVEL_BITS` may still be needed later, but it was never the cause.
* **THERE IS NO INFINITE RESOLVER LOOP.** `+0x08 == 1` — the phase machine ran
  ONCE and stopped. The earlier "0x80 -> 0x7F -> 0x7E -> 0x80 spins forever"
  reading (written into this file in round 2) is **WRONG and is retracted**. The
  resolver returns 0 and the outer machine simply stops, leaving the duel with no
  pending action — which is what the player sees as a freeze.

### Where it dies

`0x0220667C` at the convergence point dispatches on the phase again:

```
0220678C  cmp r1,#0x64 ; bgt 0x0220679C
0220679C  subs r1,#0x7d ; cmp r1,#3 ; bls -> jump table ; else b 0x02206A90 (return 0)
```

Jump table `@0x022067B0`, base `0x022067B2`, resolved:

| phase | arm |
|---|---|
| `0x7D` | `0x02206976` |
| `0x7E` | `0x0220695C` |
| `0x7F` | `0x022067F2` |
| `0x80` | `0x022067B8` |

The `0x80` arm has two return-0 exits: `0x021B9ECC(side) == 0`, and
`[sp+0x10] == 0` where `[sp+0x10] = 0x021F0114(desc, side)` -> `0x021AD870(side)`
= the free-monster-zone count (`dispatch.summon_from_opponent_hand_recipe` warns
it returns 5, not 1).

### Measured against the live state — and none of it should have failed

* `0x021B9ECC(side)` = `0x021B9708(side, mask 8, 0)`; the mask-8 arm at
  `0x021B986A` rejects on `[0x02299414+0x2C] == 5`, `[0x0229AB7C+0x1C] != 0`, or
  bit 25 of `[0x0229ADB4 + side*0xB3C]`. **All three read PASSING in the
  savestate** (0, 0, and bit25=0 on both sides).
* **Both players have 0/5 monster zones occupied** — completely empty — so the
  free-zone count cannot be 0 either.
* The cost is confirmed complete: side 0 GY = Melchid (Hanzo), side 1 GY =
  Gladiator Beast Laquari.

So the failing input is something the savestate cannot show, because the
resolver's descriptor lives on the **stack**, not in a known global: the PHASE
actually handed to `0x0220667C`, and the SIDE it derives as
`desc[+2] ^ desc[+6]`.

### ROUND 5 — instrument those two

Added to the DIAG block:

| offset | meaning |
|---|---|
| `+0x10` | the phase passed to the summon step |
| `+0x14` | `desc[+2]` |
| `+0x18` | `desc[+6]` |
| `+0x1C` | times the resolver's phase-`0x80` arm was entered |

`+0x1C` also measures the invocation ORDER, confirming or killing the assumed
`0x80 -> 0x7F -> 0x7E` sequence.

⚠️ **A live hypothesis worth recording before it is tested:** our card's summon
half is Transformation's, not Bubble Shuffle's. Transformation defers to
`0x02206F40` (the tribute -> SS-from-DECK engine); Bubble Shuffle defers to
`0x0220667C`, which summons from the HAND. If round 5 shows the phase is fine and
the side is fine, the fix is probably to defer the summon phase to **`0x02206F40`**
instead — i.e. take the cost half from Bubble Shuffle and the summon half from
Transformation, which is what the printed text actually is.

**ROUND 5 BUILD:** `data/over_the_nexus/working/rom_nast_notext.nds`
sha256 `a7b371b995dc6640a586f41af8021bba6bf9a580b604104ea62f712d2cdbdc83`

## IN-GAME TEST 6 (2026-08-31) — phase and side both PROVEN correct

DIAG from `rom_nast_notext.ml3` (14:39):

| counter | value |
|---|---|
| criteria handler entered | 0 |
| summon step called / returned | 1 / **0** |
| **phase passed to the summon step** | **0x80** — in range, correct arm |
| **`desc[+2]` / `desc[+6]`** | **0 / 0** -> side **0**, the player, correct |
| resolver's own phase-0x80 arm entered | 1 |

So the assumed `0x80 -> 0x7F -> 0x7E -> default` sequence is confirmed, the phase
handed to `0x0220667C` is a valid jump-table index, and the side is the player's.

### Narrowed by elimination to ONE call

`0x02206A90` was read raw and is `movs r0,#0` -> `add sp,#0x14 ; pop`, so **both**
tail paths return 0. The phase-`0x80` arm's other two exits return `0x32` and
`0x7F`, never 0. Therefore the summon step returned 0 through either

* `0x021B9ECC(side) == 0`, or
* `[sp+0x10] == 0`, i.e. `0x021F0114(desc, side)` -> `0x021AD870(side)` = the
  free-monster-zone count.

⚠️ **AND THAT IS PARADOXICAL**, which is why it must be measured rather than
reasoned about: `0x021B9ECC(desc[+2])` is exactly the check inside our `+0C`
activation condition `0x021F8548`, it passed at activation with the SAME
argument (side 0), and by resolution time the board has strictly MORE free zones
(both players 0/5 occupied). Something in the mask-8 arm depends on state that
changed between activation and resolution.

### ROUND 6 — probe the paradox directly

The resolver now CALLS the two predicates itself, with the same argument the
summon step will use, immediately before deferring, and banks the results:

| offset | meaning |
|---|---|
| `+0x20` | the side used for the probes |
| `+0x24` | **`0x021B9ECC(side)`** — 0 here convicts the legality predicate |
| `+0x28` | free monster zones (`0x021AD870`; returns 5 when empty) |
| `+0x2C` | `[0x0229AB7C+0x1C]` — nonzero rejects the mask-8 arm |
| `+0x30` | `[0x02299414+0x2C]` — `== 5` rejects it |

Both probes are pure reads, so they cannot perturb the run.

**If both probes PASS**, the two return-0 paths are excluded and the summon step
bails somewhere the arm-level reading has not covered — which would confirm the
standing architectural suspicion: **`0x0220667C` is the HAND-summon step**
(Bubble Shuffle summons from the hand), while this card summons from the DECK and
its natural engine is Transformation's **`0x02206F40`**. Switching
`SUMMON_STEP` to `0x02206F40` is a one-literal change and the resolver already
preserves `r1` on the path to the default arm, which that engine needs
(`str r1,[sp]` at `0x02206F48`; cf. the "chain a 2-arg resolver" note in
`otn-shooting-quasar`).

**ROUND 6 BUILD:** `data/over_the_nexus/working/rom_nast_notext.nds`
sha256 `1200598cfdce09d02506c3a6ae58fdcd77124b39b0085fb7a01358eb23fd5532`
Cave map now PRED 0x0239D940 / DIAG 0x0239D990 / RES 0x0239D9E0 (0x140) /
CRIT 0x0239DB20; `check_allocations` OK. The resolver is 300 B only because of
the probes and drops back to ~0xD8 once they are stripped.

## IN-GAME TEST 7 (2026-08-31) — every entry condition PASSES, so the engine is wrong

Probes from `rom_nast_notext.ml3` (16:28), round-6 build `1200598c`:

| probe | value | verdict |
|---|---|---|
| `0x021B9ECC(side)` | **1** | PASSES — not the blocker |
| free monster zones (`0x021AD870`) | **5** | PASSES |
| `[0x0229AB7C+0x1C]` | 0 | PASSES |
| `[0x02299414+0x2C]` | 0 | PASSES |
| phase / side | 0x80 / 0 | correct |
| criteria handler entered | 0 | never reached |
| summon step's recorded "return" | 0 | see below |

### ⚠️ THE "RETURN VALUE OF 0" WAS NEVER A RETURN VALUE

`+0x08` is incremented BEFORE the call and `+0x0C` is stored AFTER it. Every
entry condition passes, and the phase-`0x80` arm's only exits are `0x32`
(`0x022067E6`) and `0x7F` (`0x022067EE`) — **it has no path that returns 0 once
`0x021B9ECC` and the free-zone count both pass**. Since `+0x0C` reads 0, the
store after the call never executed:

**`0x0220667C` DOES NOT RETURN. The hang is INSIDE it.**

Six rounds of this file reasoned about "the summon step returns 0"; that framing
was wrong and is retracted. ⚠️ **HONESTY NOTE:** the new `+0x34` "returned"
counter did NOT exist in the round-6 build, so the 0 it shows in THIS savestate
is uninitialised, not evidence. The no-return conclusion above rests on
ELIMINATION (all entry probes pass + the arm has no return-0 exit), and `+0x34`
in the round-7 build measures it directly for the first time.

### The architectural fix

`0x0220667C` is **Bubble Shuffle's HAND-summon step** — its card ends "Special
Summon 1 'Elemental HERO' monster **from your hand**". Our criteria row carries a
**DECK** handler (`CAVE_NAST_CRIT` -> `0x0223BC3C`), and
`dispatch.criteria_zone_is_the_handler` says the handler is what picks the
container. Feeding a Deck row to the hand engine is the mismatch, and it hangs
rather than failing cleanly.

**ROUND 7: `SUMMON_STEP` switched from `0x0220667C` to `0x02206F40`** —
Transformation's tribute -> Special-Summon-**from-Deck** engine, the one whose
criteria row shape ours was cloned from in the first place. The default arm is
now Transformation's wrapper tail verbatim: call it with `r0 = desc` and return
its value directly, with **no `phase += 2`** (that was Bubble Shuffle's
convention; `0x0221B2FC` passes the phase through untouched).

⚠️ `0x02206F40` is a **2-argument** resolver — `str r1,[sp]` at `0x02206F48`
(cf. "chain a 2-arg resolver: preserve r1 = event" in `otn-shooting-quasar`).
The resolver's head and default arm never touch `r1`, so the caller's value
reaches it intact. The round-6 probes DID clobber `r1` and have been removed for
exactly this reason.

**ROUND 7 BUILD:** `data/over_the_nexus/working/rom_nast_notext.nds`
sha256 `34be0104310bd5a686dd6e574b3b07deeb924ed96e9804dcdd6741fc94b33f0a`
Resolver back down to 232 B. `check_allocations` OK.

## IN-GAME TEST 8 (2026-08-31) — FREEZE FIXED; root cause of the wrong summon FOUND

User's exact words:

> It just special summoned a random card from my deck and didn't even let me pick
> see: ml3 and ml4

**THE FREEZE IS GONE.** `0x02206F40` was the right engine: `+0x34` (returned) is
1 in ml3 and 3 in ml4, phases advance `0x7E -> ... -> 0x01`, and a monster is
Special Summoned from the Deck. Everything through the cost is working, and the
engine now completes.

But `+0x00` is **still 0** — `CAVE_NAST_CRIT` never runs — so the summon ignores
our criteria row entirely. Hence "a random card, no prompt".

⚠️ The `+0x24` / `+0x28` probe values in these two states are STALE: they are
sampled on the LAST default-arm call, which happens after the summon, when the
zones are full. They are not evidence about the failing call.

### ⭐ ROOT CAUSE — OUR RESOLVER STEALS THE PHASE THAT DOES THE SEARCH

`0x02206F40`'s own phase dispatch (`0x02206FDE`, `subs r0,#0x75 ; cmp r0,#0xb`,
12-entry table at `0x02206FF6`, add-pc base `0x02206FF8`):

| phase | arm | | phase | arm |
|---|---|---|---|---|
| 0x75 | `0x02207140` | | 0x7B | `0x0220714E` |
| 0x76 | `0x0220714E` | | 0x7C | `0x0220714E` |
| 0x77 | `0x0220714E` | | 0x7D | `0x02207116` |
| 0x78 | `0x02207124` | | 0x7E | `0x02207098` |
| 0x79 | `0x0220714E` | | 0x7F | `0x02207082` |
| 0x7A | `0x0220714E` | | **0x80** | **`0x0220700E`** |

**Phase `0x80` is the search-and-prompt phase** — it contains
`bl 0x02234E78` (the param provider) at `0x02207056`, feeding `0x02243FE0` /
`0x0219C430`, the criteria candidate count and the card-selection UI.

**Our resolver intercepts `0x80` and `0x7F` and only delegates from `0x7E`
onwards.** So the engine never sees its own setup phase, never runs the criteria
search, never shows a picker — and summons whatever its later phases default to.
That is the entire remaining bug.

### The correct architecture — move the cost OUT of the resolver

The reason Bubble Shuffle's resolver did the target work in phases `0x80`/`0x7F`
is that Bubble Shuffle has **no `+10` cost slot**. Transformation does:
`+10 = 0x021E7C89`, the generic one-monster tribute, and
`dispatch.cls_slot_roles` says **slot4 (`+10`, COST) and slot5 (`+14`, TARGET
DECLARATION) are sub-machines run by the activation state machine `0x02217F80`
BEFORE slot1 (the resolver) is ever called.**

So the targets are already declared, and the cost is already paid, by the time
`0x02206F40` runs. The card should therefore be:

| slot | value | why |
|---|---|---|
| `+04` | `0x02206F40` (or a thin wrapper) **with NO phase interception** | let the Deck engine own every phase, including `0x80` |
| `+08` | `CAVE_NAST_PRED` | the Ninja / opponent two-side predicate — already working |
| `+0C` | `0x021F8549` | activation condition — already working |
| **`+10`** | **a NEW ov5 COST stub** | send BOTH declared targets to the GY — this is the code currently sitting in the resolver's phase `0x7F`, moved to where Transformation puts its tribute |
| `+14` | `0x02235C75` | the two-target declaration — already working |

The phase-`0x7F` loop already written (unpack target -> `0x021AFCBC` guard ->
`0x021AE124` guard with the candidate's own side -> `0x021CF6B8` send to GY) is
exactly the body the cost stub needs; only its driver changes.

**REMAINING UNKNOWN, and the next thing to reverse-engineer:** slot4's step
protocol — it is driven by `[0x0229AAFC+0x7C]` / `[0x0229AB7C]` and
`dispatch.cls_slot_roles` says it "returns 0 or negative to ABORT the activation
and positive to advance". Read `0x021E7C88` (Transformation's own cost, shared by
110 records) for the shape before writing the stub.

## ROUND 9 — the COST moves to slot4 and the resolver is handed back to Konami

### Slot4's protocol, decoded from `0x021E7C88` (Transformation's own Tribute)

```
021E7C88  push {r3,r4,r5,r6,r7,lr} ; sub sp,#0x30
021E7C8C  adds r5,r0,#0            ; r0 = descriptor
021E7C8E  str  r1,[sp,#4]          ; r1 = second arg, preserved
021E7C90  bl   0x021D2BC8          ; already-handled probe -> return 1
021E7C9C  ldr  r4,=0x0229AAFC
021E7C9E  ldr  r0,[r4,#0x7c]       ; *** THE STEP COUNTER ***
021E7CA0  cmp  r0,#0 ; beq <step 0: choose the tribute>
021E7CA4  cmp  r0,#1 ; beq <step 1: perform it>
```

**So slot4 is a step machine on `[0x0229AAFC+0x7C]`, and returns 1 to advance**
(`dispatch.cls_slot_roles`: positive advances, 0/negative aborts the activation).
Our card needs no "choose" step — slot5 has already declared both targets — so
the stub acts on step 0 and returns 1.

### The new shape

| slot | value | note |
|---|---|---|
| `+04` | **`0x0221B2FD`** | **Transformation's own resolver wrapper, UNMODIFIED.** It owns every phase, so `0x02206F40` gets its phase `0x80` back and runs the criteria search + picker + summon. It also keeps Transformation's phase-1 leave-rider. |
| `+08` | `CAVE_NAST_PRED` | Ninja / opponent two-side predicate — in-game proven |
| `+0C` | `0x021F8549` | activation condition — in-game proven (the card activates) |
| `+10` | **`CAVE_NAST_COST`** | NEW: send BOTH declared targets to the GY |
| `+14` | `0x02235C75` | two-target declaration — in-game proven |

The cost stub's loop body is **verbatim the code proven in-game** as the
resolver's phase `0x7F` (unpack target -> `0x021AFCBC` -> `0x021AE124` with the
candidate's own side -> `0x021CF6B8`). Only its driver changed, from a resolver
phase to the slot4 step counter. 128 B.

⚠️ The ov5 constant is still named `CAVE_NAST_RES` for ledger continuity; its
comment now records that the slot holds the COST and why it moved.

**ROUND 9 BUILD:** `data/over_the_nexus/working/rom_nast_notext.nds`
sha256 `659aaa8eb794de710938126ca2c6dafbec3bcd9dc0af93bbdb3af2602ee9c812`
cls0[133] = `{0x1255, 0221B2FD, 0239D941, 021F8549, 0239D9E1, 02235C75}`.
`check_allocations` OK; `verify_knowledge` 366 / 331 PASS / 0 FAIL.

DIAG in this build: `+0x00` criteria handler entered (**the success signal**),
`+0x08` cost stub entered, `+0x0C` targets sent to the GY.

## IN-GAME TEST 9 (2026-08-31) — slot4 runs BEFORE the targets exist

Freeze returned. DIAG (⚠️ the reader's LABELS are stale in this build: `+0x08` is
now "cost stub entered", `+0x0C` is "targets sent to the GY"):

* `+0x08` = **1** — the slot4 cost stub RAN
* `+0x0C` = **0** — **and it sent ZERO targets**
* `+0x00` = 0 — criteria handler still never entered

### ⭐ NEW ENGINE FACT — SLOT4 (COST) RUNS BEFORE SLOT5 (TARGET DECLARATION)

The cost loop reads the declared-target count from `desc[+0x12]`; it was **0**.
`dispatch.cls_slot_roles` states the order and I read past it: the activation
state machine `0x02217F80` runs the **slot4 block (gated on `descriptor[+7]`)
BEFORE the slot5 block (gated on `descriptor[+8]`)**, then slot1.

**So a cost that must CONSUME targets declared by slot5 cannot live in slot4.**
Transformation gets away with putting its Tribute there only because that Tribute
*chooses its own victim*; ours has to consume someone else's declaration.

That is a genuinely reusable fact and it is the reason round 9 failed.

### ROUND 10 — a THIN WRAPPER at +04, not a clone and not a cost

`+04` = `CAVE_NAST_COST` (name historical), 144 B:

```
push {r3,r4,r5,r6,r7,lr}
str  r1,[sp]                  ; 0x0221B2FD is a 2-ARG resolver -- stash it
adds r5,r0,#0
ldr  r3,[0x0229AAFC+0x70]
cmp  r3,#0x80
bne  deleg                    ; every other phase: pure pass-through
<send EVERY declared target to the GY -- the loop proven in-game>
deleg:
ldr  r1,[sp]                  ; restore the 2nd arg
adds r0,r5,#0
blx  0x0221B2FD               ; Transformation's OWN resolver, every phase
pop  {r3,r4,r5,r6,r7,pc}
```

`+10` is back to **0**. The difference from the round-2..8 clone is that this
wrapper **intercepts nothing** — it adds one step at phase `0x80` and then hands
that same phase to Konami's code, so `0x02206F40` still runs its criteria search
and picker. Ordering is right (cost paid, then the Deck search), matching
Transformation's own slot4-then-resolver sequence. Re-entry is safe because
`0x021AD8F4` rejects an empty zone, so a second pass sends nothing.

All seven literals verified present in the blob, delegation tail disassembled and
correct.

**ROUND 10 BUILD:** `data/over_the_nexus/working/rom_nast_notext.nds`
sha256 `dfb5fada6448c446dd90e07e1f5c83a3d22008c286e7b3244362ffa9b9c4f365`
cls0[133] = `{0x1255, 0239D9E1, 0239D941, 021F8549, 0, 02235C75}`.
`check_allocations` OK.

DIAG: `+0x00` criteria handler entered (**the success signal**), `+0x08` wrapper
hit phase 0x80, `+0x0C` targets sent, `+0x10` the declared-target count it saw
(**0 here would mean slot5 still has not run at resolver time**).

## DRIFT AUDIT vs the 3DS (asked for 2026-08-31, before testing round 10)

3DS `0x26DD` owns exactly TWO records — one cls row and one criteria row. It
appears in **no other 3DS registry**.

| slot | 3DS | 3DS sharers | ours | verdict |
|---|---|---|---|---|
| `+04` | `0x00457B38` | **1 (itself)** | ov5 wrapper -> `0x0221B2FD` (Transformation, shared w/ Super Solar Nutrient) | **MAJOR DRIFT** |
| `+08` | `0x003ED908` | 7 | bespoke ov5 predicate | **DRIFT** — mapping never resolved (NDS vote split 1-1 between `0x021DD859` and `0x021E3919`) |
| `+0C` | `0x0049D734` | 6 | `0x021F8549` | **MATCH** (3/3 unanimous) |
| `+10` | **NULL** | — | NULL | **MATCH** (after round 10 reverted round 9) |
| `+14` | `0x00478390` | 32 | `0x02235C75` | **MATCH** (16/16 unanimous) |
| criteria | `{aux 0xFFFF, fn 0x004B0478, word 0x00000002}` | fn used by **1 row** | `{aux 0xFFFF, ov5 clone, word 0x00000002}` | aux + word MATCH; **fn is bespoke on BOTH sides**, so no equivalence exists to inherit |

### The honest reading

**Every slot the 3DS shares with other cards, we matched — and every one of those
matched parts WORKS in-game** (`+0C` activation, `+14` two-target declaration).
**Every slot the 3DS marks bespoke (`+04` and the criteria handler) is a slot we
substituted with shared or cloned code — and that is exactly where all ten rounds
of failure have been.** Konami wrote unique code for this card's resolver and its
candidate filter; we are steering a generic engine into approximating them.

### Drift I should have caught earlier

* **`+10` = NULL on the 3DS.** Round 9 put a cost stub in slot4 anyway and failed
  precisely because slot4 runs before the targets exist. The 3DS record said
  "this card has no slot4" and would have prevented that round outright.
* **The level cap.** The 3DS word is `0x00000002` with **no level bits at all** —
  the "combined original Levels" arithmetic lives inside the bespoke handler
  `0x004B0478`. Ours ORs a hardcoded `0x00B00000` ("Level <= 12"). That is an
  invention, not a transplant, and it is a KNOWN deviation.
* **`+08`.** The 3DS family is "target a monster on the field" (Common Soul,
  Faustian Bargain, Curse of the Circle, Evo-Miracle, Impenetrable Attack,
  Butterspy Protection). Only 2 of those 7 exist on the NDS and they disagree, so
  the mapping is genuinely unavailable — but our predicate is in-game proven to
  offer the right two pickers, so this drift is benign so far.
* **PART E (leave-cleanup list).** The 3DS gives NO row for C4 anywhere, so that
  clause rests entirely on NDS-side reasoning and is unvalidated cross-build.

### What this does and does not imply

It does NOT mean round 10 will fail: `+0C`, `+14`, the predicate and the
GY-send are all separately proven in-game, and the wrapper now leaves Konami's
resolver in charge of the phase it needs. It DOES mean the remaining risk is
concentrated exactly where the 3DS says Konami wrote custom code, and that if
round 10 fails the honest next step is a **purpose-written resolver** rather than
another attempt to steer `0x02206F40`.

## ROUND 11 — the purpose-written resolver, and the RIGHT engine underneath it

The drift audit said the residual risk sits where the 3DS marks `+04` bespoke, so
`+04` is now genuinely ours: a wrapper that performs this card's unique step and
then delegates to the engine whose printed clause matches ours **exactly**.

⚠️ **The engine changed, and the previous one was the wrong pick.** Rounds 9-10
delegated to Transformation's `0x0221B2FD` -> `0x02206F40`, which is
*Tribute-then-summon*: it expects to choose and consume its own victim.
`counter.deck_ss_resolver` names the better chassis:

**`0x02206CAD` — the SHARED "Special Summon 1 \<filtered\> monster from your
Deck" resolver.** It is slot `+04` of **Shien's Footsoldier `0x1B3A`** and **Six
Scrolls of the Samurai `0x1F76`** — the two cards whose text is exactly *"Special
Summon 1 &lt;filtered&gt; monster from your Deck"*, driven by the card's OWN criteria
row. Nine-way phase table on `[0x0229AAFC+0x70] - 0x78` (window `0x78..0x80`,
offsets at `0x02206CC6`). That is our summon clause with no tribute semantics
attached, which is why it is the right chassis and Transformation's was not.

Final shape:

```
cls0[133] = {0x1255, +04 CAVE_NAST_COST|1, +08 CAVE_NAST_PRED|1,
             +0C 0x021F8549, +10 0, +14 0x02235C75}

+04 wrapper (144 B):
    if phase == 0x80:  send EVERY declared target to the GY   (in-game proven)
    always:            tail-call 0x02206CAD                   (deck-SS engine)
```

`+10` stays NULL, matching the 3DS record. Added a precondition assert anchoring
`0x02206CAD` on Shien's Footsoldier's cls2[237] record and on the `0x78..0x80`
phase window, so drift in that shared address aborts the build.

**ROUND 11 BUILD:** `data/over_the_nexus/working/rom_nast_notext.nds`
sha256 `d7f37f04b6848cfd8f3904b17b4042376d6ddd9bf2961ce7b285aa081bce2488`

⚠️ `0x02206CAC` has a per-cid switch whose compare base lives in `[sp,#n]`
(`thumb.stack_based_switch`), so our donor's arm membership CANNOT be settled by
a register-only scan — the defaults are what we are betting on, and the in-game
test is the arbiter.

## Ruled Out

* **A pure-data criteria row for the three-race whitelist.** Scanned every
  4-word window of overlay 3 for `{race, race, race, 0}` with all values in
  1..21: **`{1, 9, 5, 0}` (Dragon, Dinosaur, Sea Serpent) does not exist
  anywhere in ov3.** The single-race shortcut (Super Solar Nutrient's word top
  byte) holds only one race. So C3's type whitelist needs a new 4-word list plus
  a clone of `0x0223E768` — injected code, not data.
* **Cloning Transformation's `+08` predicate `0x021DA1C9` verbatim.** It is a
  per-acting-cid switch over 7 cids (`ldrh r0,[r6]` @ `0x021DA1F0`); an unlisted
  donor takes the default arm. A donor gets no Ninja check for free.
* **Reading Super-Transformation's behaviour off the 3DS as a shared chassis.**
  Its 3DS resolver is used by exactly one row — Konami wrote it bespoke. The
  3DS settles *architecture* here (which zone, which handler family, one cls row
  + one criteria row), not a transplantable address.
* **A count-neutral L3 insert.** No phantom in the list (see above).

---

## Open Questions

* **`0x02235C74`'s arm set is not decoded** (the `+14` two-target declaration).
  Arm cids are `base +/- imm` off a pool literal — the `thumb.stack_based_switch`
  footgun, which has already made a register-only simulator report the wrong leaf
  on this codebase. What the DEFAULT arm does for an unlisted donor is unmeasured,
  and `r7 = 1` / `r5 = 2` are only *suspected* to be the per-side target counts.
  **This is C2's load-bearing unknown.**
* **Where `desc[+0x14]` is written.** It is C3's level cap and already carries
  the "+3" for both chassis cards, but the writer is unidentified — it is not
  `0x021F7D04` (disassembled; a generic free-zone check). Candidates: the shared
  cost `0x021E7C89`, or the generic resolver `0x02206F40`. Needed to replace "+3"
  with "combined original Levels".
* **C4's banish kind byte.** `0x17` is the destroy-on-leave node kind. Which kind
  means *banish* on leave is **unknown**; "it is a one-constant change in a clone
  of `0x0221B2FC`" is a hypothesis, not a finding.
* **The `+08` 3DS→NDS mapping did not resolve** (1-1 split between
  `0x021DD859` and `0x021E3919`). Not a blocker — Bubble Shuffle's `0x021E00D8`
  supersedes it as the template — but the disagreement is unexplained.
* **Does a records-free Continuous Trap donor activate at all?** Every candidate
  donor is a passive card. Whether the engine will let a Continuous Trap be
  activated and then run a cls0 record is untested, and the KB has **no fact
  covering Continuous Trap activation** (confirmed gap).
  `patch_infernity_barrier` (Destruction Jammer → Infernity Barrier) is the
  nearest Trap-donor precedent and should be read first.
* ~~Goblin Fan's single occurrence is unexplained~~ — **RESOLVED, see
  "Retiring Goblin Fan's stock text" in Confirmed.**

---

## Next Experiment

Donor is chosen (**Goblin Fan `0x1255`**, user 2026-08-31) and the architecture
has a source for every clause. Build order, one clause per session:

1. **C1 first** — donor conversion only: `card_prop` → Continuous Trap, name +
   description in 8 languages, and the 2-byte set-code `0x2A` insert that makes
   it Hanzo-searchable. Pure data, no ov5 slot, no cls record. It is a
   prerequisite for C2-C4 and is independently testable in one duel (Hanzo
   Normal Summon → is the card offered? does it appear in the deck editor?).
2. Before C1 is written: explain `ov3:0x02268C48`, and read
   `patch_infernity_barrier.py` for the Trap-donor pattern.
3. **C2 next**, and its first step is a measurement, not a patch: decode
   `0x02235C74`'s arm set with a CFG walk (never a register-only simulator —
   `thumb.stack_based_switch`), and determine the default arm's target counts.
4. C3 then C4, both on the Transformation chassis mapped above.

---

## ROUND 11 RESULT + ⭐ THE HANDOFF'S PHASE TABLE WAS MIS-DECODED (2026-08-31, session 12)

**Round 11 (delegate to `0x02206CAD`) FROZE in-game** — inherited from
`PROMPT_nast_resolver.md`, not re-measured this session. That makes three
delegation attempts (`0x0221EBBD` Bubble Shuffle, `0x0221B2FD` Transformation,
`0x02206CAD` deck-SS) and three freezes. The user has rejected delegation.

### The handoff's nine-way phase table is WRONG — it read the INSTRUCTIONS as the table

`PROMPT_nast_resolver.md` states the table "sits at `0x02206CC6`, add-pc base
`0x02206CC8`" and lists arms `0x02208511 / 0x0220B141 / 0x021FF591 / 0x022070D1 /
0x022080D1 / 0x0220B157 / 0x02206EE8 / 0x02206EF2`.

`0x02206CC6` is not the table — it is `adds r1,r1,r1` (halfword `0x1849`), and
`0x02206CC8 + 0x1849 = 0x02208511`, which is exactly the handoff's first "arm".
**Every arm in that table is an instruction halfword of the dispatch prologue
added to the wrong base.** So "`0x022080D0`, the picker arm" is an artefact; that
address is not on this card's code path at all.

The real dispatch, disassembled from `rom.nds` ov3 this session:

```
02206CBA  ldr  r1,=0x0229AAFC
02206CBC  ldr  r1,[r1,#0x70]      ; phase
02206CBE  subs r1,#0x78
02206CC0  cmp  r1,#8
02206CC2  bls  0x02206CC6         ; in-window
02206CC4  b    0x02206EFE         ; else return 0
02206CC6  adds r1,r1,r1
02206CC8  add  r1,pc              ; pc = 0x02206CCC
02206CCA  ldrh r1,[r1,#6]         ; *** TABLE = 0x02206CD2 + 2*i ***
02206CCC  lsls r1,r1,#0x10
02206CCE  asrs r1,r1,#0x10
02206CD0  add  pc,r1              ; *** ADD-PC BASE = 0x02206CD4 ***
```

Table halfwords at `0x02206CD2`, target = `0x02206CD4 + sign_extend(hw)`:

| phase | hw | arm | | phase | hw | arm |
|---|---|---|---|---|---|---|
| 0x78 | 0x0220 | `0x02206EF4` | | 0x7D | 0x022A | `0x02206EFE` (unused) |
| 0x79 | 0x022A | `0x02206EFE` (unused) | | 0x7E | 0x017A | `0x02206E4E` |
| 0x7A | 0x022A | `0x02206EFE` (unused) | | 0x7F | 0x0156 | `0x02206E2A` |
| 0x7B | 0x0214 | `0x02206EE8` | | **0x80** | **0x0010** | **`0x02206CE4`** |
| 0x7C | 0x018E | `0x02206E62` | | | | |

Self-check that the decode is right: the three "unused" arms are `0x02206EFE`,
which is **the same target as the out-of-window `b` at `0x02206CC4`** — exactly
what an unused jump-table slot looks like. The old table had no such structure.

`0x02206CAC` prologue: `push {r1,r2,r3,r4,r5,r6,r7,lr}` (the r1/r2/r3 slots are
scratch reserved for outgoing **stack arguments 5+**), `r4 = descriptor`,
`r6 = event`, **`r5 = side = desc[+2] ^ desc[+6]`** (both `ldrb`).

### ⭐ THE WHOLE STATE MACHINE, DECODED (this is the blueprint for our resolver)

Return value = the next phase; `0` = stop.

**Phase 0x80 — `0x02206CE4`, SETUP + CANDIDATE COUNT**

```
ldrh r2,[r4] ; cmp =0x247D ; bne 0x02206D2A     ; one hard-coded card, skipped by us
0x02206D2A: 0x021AD870(r5)  -> 0 ? return 0     ; SS-legality gate 1
            0x021B9ECC(r5)  -> 0 ? return 0     ; SS-legality gate 2
            0x021B9ED8(r5)  -> 0 ? return 0     ; SS-legality gate 3
            <per-cid switch: 0x0D4C 0x136A 0x140B 0x1612 0x1A98 0x1BA1 0x1E2C 0x21F8 0x2233>
0x02206E06 (DEFAULT ARM -- an unlisted donor lands here):
            r0=r4 ; bl 0x02234E78     -> r2 = param        ; the param provider
            r1 = ldrh[r4]             = acting cid
            r0 = r5                   = side
            bl 0x02243FA8             ; *** COUNT CRITERIA CANDIDATES ***
            if r0 == 0: 0x0219A818(r5,#0xD) ; return 0x7B  ; "no valid targets"
            else:                       return 0x7F
```

**Phase 0x7F — `0x02206E2A`, AUTO-vs-PROMPT SPLIT**

```
0x02022E14(cid, 0x0227020C, #0x12)   ; 18-entry u16 cid list
  hit  -> strh 0 -> [0x0229944C+4] ; return 0x7C      (skip the picker)
  miss -> 0x0219A818(r5,#0x30) ;     return 0x7E      (our donor: MISS)
```

**Phase 0x7E — `0x02206E4E`, ⭐ THE PICKER**

```
bl 0x02234E78          -> r3 = param      (NOTE: called with r0 = r4 = descriptor,
                                           inherited, no explicit set)
r2 = ldrh[r4]          = cid
r0 = r5                = side
r1 = #6                = *** A CONSTANT, not an unknown ***
bl 0x0219C430          ; open the card-selection UI
return 0x7C
```

The handoff's "`r4`'s meaning is the open question" was a consequence of the
mis-decode. **`0x0219C430(side, 6, cid, param)` — arg 2 is the literal `6`.**

**Phase 0x7C — `0x02206E62`, ⭐ THE READ-BACK + SUMMON COMMIT**

```
movs r0,#1 ; str r0,[sp,#4]                  ; arg3 default = 1
0x02022E14(cid, 0x022701EC, #0x10) ; hit -> r7 = r6 (=0)
r7 = 2 ; r6 = 0                              ; defaults
r4 = ldrh[r4]                                ; ⚠️ r4 STOPS BEING THE DESCRIPTOR
<per-cid switch: 0x1232/0x1F7A -> r6=1 ; 0x136A/0x1612/0x1E2C/0x2233 -> [sp,#4]=0
                 0x2361/0x2458 -> r7=1 ; DEFAULT -> keep 1/2/0>
0x02206ECA:
  bl 0x0219C510              ; *** READ BACK THE PICKED CARD (NO ARGUMENTS) ***
  r1 = r0                    ; = the picked card
  r2 = r6 (u16)
  r0 = (r4 << 16) | r2       ; cid<<16 | r6
  str r0,[sp]                ; stack arg 5
  r2 = [sp,#4]
  r0 = r5                    ; side
  r3 = r7
  bl 0x0226925C              ; *** THE SUMMON ***
  return 0x78
```

**So for an unlisted donor the commit is exactly**
`0x0226925C(r0=side, r1=picked, r2=1, r3=2, [sp]= (cid<<16))`.

⚠️ The handoff named `0x02269314` as "the actual summon". The call this chassis
actually makes is **`0x0226925C`** (whether that is a wrapper over `0x02269314`
is checked below).

**Phase 0x7B — `0x02206EE8`** : `0x0225BF30(1 - r5)` ; return 0x78
**Phase 0x78 — `0x02206EF4`** : `0x021D269C(r5)` ; return **0x64** (terminator)
**0x02206EFE** : `movs r0,#0 ; pop` — the "not my phase" return.

### ⭐ THE THREE MISSING CONTRACTS — ALL THREE CLOSED (session 12)

**(1) THE PICKER — `0x0219C430(r0 = side, r1 = mode, r2 = cid, r3 = param)`**

```
0219C430  push {r1,r2,r3,r4,r5,r6,r7,lr}
0219C432  adds r7,r1,#0 ; adds r6,r7,#0        ; r7 = r6 = mode
0219C436  ldr  r5,=0x0229DD94
0219C438  adds r4,r0,#0                        ; r4 = side
0219C43A  str  r4,[r5,#0x30]                   ; UI request: side
0219C43C  adds r6,#0xf ; str r6,[r5,#0x2c]     ; UI request: mode + 0xF
0219C440  ldr  r5,=0x0229911C ; lsls r6,r4,#2 ; ldr r5,[r5,r6]
0219C446  str  r2,[sp] ; str r3,[sp,#4]        ; stash cid + param
0219C44A  cmp  r5,#1 ; bne .. ; cmp r7,#5 ; blt ..
0219C452  bl   0x0226AD50 ; pop                ; *** AI path: auto-pick, no UI ***
0219C458  ldr  r0,=0x0229944C
0219C45A  strh r4,[r0]    ; [+0] = side
0219C45E  strh r7,[r0,#2] ; [+2] = mode
0219C462  strh r1,[r0,#4] ; [+4] = 0   <-- THE RESULT SLOT, cleared here
0219C466  memset 0x02299458, 0x4B0     ; the candidate LOCATOR array (stride 4)
0219C46E  memset 0x02299908, 0x258     ; the candidate CID array (stride 2)
0219C47C  bl   0x02243FA8(side, cid, param)    ; *** REFILLS the buffers itself ***
```

So the phase-0x80 `0x02243FA8` call is only a *"is it > 0?"* pre-check — the picker
recounts and refills. **`mode` is the literal `6`** in this chassis, not an
unpinned register. (`dispatch.deck_send_phase_machine`, VERIFIED, gives the
general form: `min(count,32) + 6` for the pick-N-from-a-list prompt, so 6 is the
one-card case.)

**(2) HOW THE PICK IS READ BACK — `0x0219C510()`, NO ARGUMENTS**

```
0219C510  ldr  r1,=0x0229944C
0219C512  movs r0,#4 ; ldrsh r0,[r1,r0]   ; the chosen index (signed halfword)
0219C516  ldr  r2,=0x02299458
0219C518  lsls r0,r0,#2 ; adds r0,r2,r0   ; &LOCATORS[index]
0219C51C  bx   lr
```

**It returns a POINTER — `&0x02299458[index]` — not a value.** Its sibling
`0x0219C534()` returns the u16 *cid* of the same index out of `0x02299908`.
`0x0229944C` is the picker control block: `[+0] side, [+2] mode, [+4] chosen
index, [+6] candidate count` (`0x02243FA8` returns `ldrsh [0x0229944C+6]`).

**(3) THE SUMMON COMMIT — `0x0226925C`, and the handoff's `0x02269314` is not it**

Signature (matches the VERIFIED `summon.commit_r0_places_bit4_only_attributes`):

```
0x0226925C(r0 = placing side, r1 = &locator, r2 = face-up, r3 = position,
           [sp] = (summoner_cid << 16) | flags)
```

Disassembled this session, and every field traced to its store in the summon
block `0x02298A28`:

| in | store |
|---|---|
| `bl 0x021AD8C4(side)` | `< 0` -> **abort, no summon** (free-zone check) |
| `[r6]` = the locator word | `[g+0x0E] = w & 0x3FFF` (**the cid comes from the LOCATOR**), `[g+0x0C]` = packed ref |
| r2 | `[g+6]` face-up |
| r3 | `[g+8]` position |
| `[sp]` low half | `[g+0x10] = (w & 0xFFFF) \| 4` |
| **`[sp]` high half** | **`[g+0x12]` — the SUMMONER's cid, i.e. the C4 attribution field** |

`0x02269314` is not a function entry at all — `0x0226930C` is `0x0226925C`'s
literal pool. The handoff's "the actual summon is `0x02269314`" came from the
same mis-read as the phase table.

**And the criteria handler's own call site is closed too** —
`0x02243FA8(side, cid, param)` -> `0x02243B9C(cid, param)` (binary search of
`0x022713C4`, returns `0xC - 0xD = -1` when the cid is absent, which `bmi`s
straight past the fill and returns count 0) -> `0x02243F38(side, cid, param,
row_index)`, which at `0x02243F74` does

```
r0 = 0x022713C4 + row*12   (&row)   r1 = side   r2 = param
r3 = [0x022713C8 + row*12] (row+4)  blx r3
```

confirming `CAVE_NAST_CRIT`'s `(r0 = row, r1 = side, r2 = param)` signature as
already built.

### Ledger re-read (CLAUDE.md: quote the exact line, never assert from memory)

```
otn_enhanced/effects/ov5_cave.py:938  CAVE_NAST_PRED   = 0x0239D940
otn_enhanced/effects/ov5_cave.py:945  CAVE_NAST_DIAG   = 0x0239D990
otn_enhanced/effects/ov5_cave.py:957  CAVE_NAST_CRIT   = 0x0239DB20  # 0x5C B of 0x60
otn_enhanced/effects/ov5_cave.py:963  CAVE_NAST_RES    = 0x0239D9E0
otn_enhanced/effects/ov5_cave.py:989  CAVE_FREE        = 0x0239DB80
```

⚠️ The module's inline comment on line 181 said `CAVE_NAST_CRIT # 0x0239D990,
0x48 B of 0x50` — **stale, and it names DIAG's address**. The value itself is
read from `ov5_cave`, so no ROM byte was ever wrong; the comment is corrected.

### A correction to the module's own reasoning about the level field

`dispatch.criteria_word_level_field` (VERIFIED) says the byte at bits 23:16 is
`[op:2 @7:6][level:4 @5:2][flag:2 @1:0]` and **`level 0` = NO level constraint**.
The module docstring claims the opposite ("writing 0 there is NOT the same as
'no bound' ... may well read as 'Level <= 0'") and blames round 1's empty search
on it. That reasoning is wrong — round 1's search was empty because the criteria
handler was never reached at all. `0x00B00000` (op 2, level 12, "Level 12 or
lower") is still what is built; it is simply not load-bearing.

## ROUND 12 — THE PURPOSE-WRITTEN RESOLVER (built 2026-08-31, AWAITING IN-GAME TEST)

`+04` is now genuinely ours and delegates to nothing.  It is not invented either:
it is a byte-level reimplementation of the DEFAULT-ARM path of `0x02206CAC`
decoded above, with the GY send prepended to phase `0x80`.

```
CAVE_NAST_RES2 = 0x0239DB80   372 B of 0x180 reserved
cls0[133] = {0x1255, +04 0x0239DB81, +08 0x0239D941, +0C 0x021F8549,
             +10 0, +14 0x02235C75}
criteria row = {0x1255, aux 0xFFFF, 0x0239DB21, word 0x00000002}
```

| phase | what our stub does | returns |
|---|---|---|
| `0x80` | send every declared target to the GY (the loop proven in-game rounds 3-8), then `0x021AD870`/`0x021B9ECC`/`0x021B9ED8` gates, then `param = 0x02234E78(desc)` and `n = 0x02243FA8(side, cid, param)` | `0x7F` if n>0; `0x0219A818(side,0x0D)` then `0x7B` if n==0; **0** if a gate fails |
| `0x7F` | `0x0219A818(side, 0x30)` | `0x7E` |
| `0x7E` | `0x0219C430(side, 6, cid, param)` | `0x7C` |
| `0x7C` | `r1 = 0x0219C510()` then `0x0226925C(side, r1, 1, 2, cid<<16)` | `0x78` |
| `0x7B` | `0x0225BF30(1 - side)` | `0x78` |
| `0x78` | `0x021D269C(side)` | `0x64` |
| any other | nothing | **0** |

The chassis's phase-`0x7F` list test (`0x02022E14(cid, 0x0227020C, 0x12)`, which
skips the picker for 18 specific cids) is DROPPED — our donor is not a member, so
it can only ever take the miss branch.

**Why the donor takes every default.**  Checked this session rather than assumed:

* `0x1255` is in **neither** `0x0227134C` (0x3B entries) nor `0x02271314` (0x1B)
  — the two lists that let `param` shift the criteria row — so `0x02243B9C`
  always returns the LEFTMOST row for the cid, i.e. our single row, whatever the
  param is.
* `0x1255` is in none of `0x02234E78`'s five lists, and the nearest cid literal
  anywhere in that function's per-cid switch is `0x0E2E` / `0x15FD` — over
  `0x3A8` away, and Thumb-1 sub-arms address cids as `base ± imm8`. So it cannot
  reach an arm and takes the provider's default.
* Row-offset epilogue `0x02243EEC` is `movs r4,#0`, then `0x02243EEE..0x02243F22`
  walks BACK to the leftmost row for the cid and adds `r4`. Offset 0 = our row.

### Cave move

`CAVE_NAST_RES` (`0x0239D9E0`, `0x140`) is too small for 372 B and is boxed in by
`CAVE_NAST_CRIT` at `0x0239DB20`, so the resolver moved to a new ledger slot
`CAVE_NAST_RES2 = 0x0239DB80` (`0x180`), `CAVE_FREE` bumped to `0x0239DD00`.
The old slot stays **reserved to this card** rather than freed — freeing a slot
mid-debug is how one gets double-booked.
`check_allocations`: 153 ov5 slots, 127 phantom claims, no overlaps, ledger in sync.

### Build

```
.venv-1/Scripts/python.exe _build_nast.py --no-text
data/over_the_nexus/working/rom_nast_notext.nds
sha256 d7e48606de572ac684868b4c1f653c648b3b81f1db1c4f27eb14c52d1019e98a
```

`verify()` all PASS for this card; `patch_ninja_grandmaster_hanzo.verify()` all
PASS on the SAME ROM; `check_allocations` OK; `verify_knowledge` 368 facts /
333 PASS / 0 FAIL / 35 UNVERIFIED.  ⚠️ **Static only. NOT in-game confirmation.**

### New build-time guards (so this cannot rot silently)

`_assert_preconditions` now decodes the chassis's nine-way table itself and
asserts the nine arms, plus the `bl` target of every native call the stub copies
(`0x02234E78`, `0x02243FA8`, `0x0219A818`, `0x0219C430`, `0x0219C510`,
`0x0226925C`, `0x0225BF30`, `0x021D269C`), the `movs r1,#6` picker mode, the two
literals proving `0x0219C510` returns `&LOCATORS[index]`, and the `blx r3` in
`0x02243F38` that invokes the row's own handler.  A new `_bl_target()` helper
resolves ARMv4T two-halfword `BL`s.

### Instrumentation — one duel now bisects the whole machine

`scratch/nast_state.py` (NEW — the file the handoff referenced did not exist).
It refuses a savestate whose resident resolver bytes do not match the rebuilt
blob, which is verified working: all three round-9 states are correctly rejected.

| DIAG | meaning |
|---|---|
| `+0x00` | criteria handler entered — **the success signal, 0 in every round so far** |
| `+0x04` | Deck walker's last return |
| `+0x08` | resolver entries, all phases |
| `+0x0C` | targets actually sent to the GY |
| `+0x10` | declared-target count read from `desc[+0x12]` |
| **`+0x14`** | **rolling PHASE TRACE — the last four phases, newest in the low byte** |
| `+0x18` | candidates `0x02243FA8` returned |

The trace is the point: a freeze now says *which phase it died in* instead of
nothing at all.  Expected healthy walk: `0x80 -> 0x7F -> 0x7E -> 0x7C -> 0x78`.

## Ruled Out (added session 12)

* **`0x022080D0` as "the picker arm", and `0x02269314` as "the summon".** Both
  came from decoding the chassis's jump table at the wrong address. `0x02206CD2`
  / base `0x02206CD4` is the table; `0x0226930C` is `0x0226925C`'s literal pool,
  so `0x02269314` is not even a function entry.
* **"`r4`'s meaning is the open question" in the picker call.** There is no `r4`:
  the picker is `0x0219C430(side, 6, cid, param)` and the `6` is a literal.
* **The criteria handler being wrong.** Its `(row, side, param)` signature is
  confirmed against its only call site, `blx r3` at `0x02243F74` with
  `r0 = 0x022713C4 + row*12`, `r1 = side`, `r2 = param`.

## Next Experiment (session 12)

One duel with `rom_nast_notext.nds`
(`d7e48606de572ac684868b4c1f653c648b3b81f1db1c4f27eb14c52d1019e98a`), in a
**normal duel** (never a puzzle — ov5 is evicted there):

1. Get the card to the field and activate it targeting a Ninja you control and a
   face-up opponent monster.  Have a **Dragon, Dinosaur or Sea Serpent in the
   Deck** — otherwise a correct build legitimately reports "no candidates".
2. Save state whatever happens — success, wrong summon, or freeze.
3. `.venv-1/Scripts/python.exe -m scratch.nast_state <state>`

`+0x14` names the last phase reached, and each phase's failure has a distinct
next step already written into the reader's output.

## ⭐⭐ IN-GAME TEST 12 (2026-08-31) — ROOT CAUSE FOUND, AND IT WAS NEVER THE RESOLVER

Savestate `rom_nast_notext.ml3` (19:33), round-12 build `d7e48606`:

| DIAG | value |
|---|---|
| `+0x00` criteria handler entered | **0** |
| `+0x04` deck walker return | 0 |
| `+0x08` resolver entries | **1** |
| `+0x0C` targets SENT to the GY | **2** |
| `+0x10` declared-target count | **2** |
| `+0x14` phase trace | **0x80** only |
| `+0x18` candidates | 0 |

So: the resolver ran once at phase `0x80`, sent BOTH targets to the GY, and then
stopped without the criteria handler ever running.

### ⭐ THE BUG — `build_crit_stub` LOADED THE RACE LIST'S FIRST ELEMENT AS ITS ADDRESS

```
0x0239DB28  ldr  r4,[pc,#0x30]    ; pool@+0x3C = 0x00000001   <-- the race CODE
0x0239DB2A  ldm  r4!,{r0,r1}      ; reads from address 0x00000001
```

Transformation's original loads a **POINTER**: `ldr r4,[pc,#0x48]` = `0x02271304`,
a list that lives in ov3. Our clone carries its own list and pointed the `ldr`
**at the list itself**, so `r4` came out as `1` — the first race code, Dragon —
and the `ldm r4!` read from address 1. The handler never got as far as its own
DIAG counter, which is exactly why "criteria handler entered" read 0.

**ONE WORD. It has been in the module since round 1** and was invisible for
eleven rounds because the handler was never reached: rounds 2-8 intercepted phase
`0x80` themselves, so the search never ran. **The moment a build finally let the
engine reach the criteria search — round 10 — the game froze, and it froze again
in round 11 and stopped again in round 12.** All three "unexplained delegation
freezes" are this one bug. The delegation hypothesis was never falsified by those
tests; it was never tested by them.

### How it was proven — a Thumb-1 interpreter over the savestate's RAM

`scratch/thumbemu.py` (NEW): an ARMv4T Thumb-1 interpreter whose memory is backed
by a melonDS savestate, with copy-on-write so a predicate cannot corrupt the run.
Unlike the register-only simulator `thumb.stack_based_switch` warns about, it has
the real memory and a real stack, so struct reads and stack-based switches
resolve correctly.

Run against `rom_nast_notext.ml3`, A/B on the same state:

| | shipped build | with the one-word fix |
|---|---|---|
| resolver result | **fault reading address 0x1** | **returns 0x7F** |
| crit handler entered | 0 | 1 |
| deck walker return | 0 | **3** |
| candidates | 0 | **3** |
| targets sent to GY | 2 | 2 |

The shipped column **reproduces the savestate's DIAG block exactly**
(`crit_entered=0`, `sent_to_gy=2`), which is what makes this a measurement rather
than a hypothesis. With the fix the walker finds 3 legal Dragon / Dinosaur / Sea
Serpent monsters in that Deck and the resolver advances to `0x7F`.

⚠️ Two emulator bugs were found and fixed while doing this, both of which had
produced a wrong answer first: `BLX <label>` to ARM now raises instead of
executing ARM words as Thumb, and `add pc,rX` now reads PC as `pc+4` (the pc+2
version made the container accessor `0x0219CA28` take the wrong jump-table arm
and return NULL). **A simulator that has not been shown to reproduce the observed
state is not evidence** — the reproduction of DIAG above is what licenses the
conclusion.

### Everything the round-12 resolver was written to do, it did

Independently confirmed from this savestate, so none of it needs re-testing:

* the three Special-Summon legality gates all PASS — emulated at side 0 on the
  real board: `0x021AD870` = 4 (four free monster zones), `0x021B9ECC` = 1,
  `0x021B9ED8` = 1.
* `0x02243B9C(0x1255, 0)` returns **79** — our criteria row is found, correctly
  sorted, with handler `0x0239DB21` and word `0x00000002`.
* `0x02243F38(side 0, cid 0x1255, param 0, row 79)` `blx`es our handler.
* the param provider path takes the Hanzo hook `0x0239D900` and returns 0, so
  the row offset stays 0 as predicted.
* the GY send works: both declared targets reached the Graveyard.

### The board this was measured on (for the next test's context)

side 0: Hanzo `0x13E7` in monster zone 2; our card `0x1255` face-up in S/T zone 6;
Transformation `0x1768` in zone 7; a second `0x1255` set in zone 8.
side 1: `0x1C76` in monster zone 2, `0x1CE8` / `0x12FF` in S/T.
Player struct base `0x0229AC94`, stride `0xB3C`, monster zone *i* at `+0x34+i*0x14`,
packed word: cid = `w & 0x3FFF`, **bit 14 = side**.

## ROUND 13 BUILD (2026-08-31) — the one-word fix

`build_crit_stub` gains a pool word `lit_list_ptr` holding the ADDRESS of the
race list, and `ldr r4,=&RACE_LIST` reads that instead of the list's first
element. Two build-time asserts now pin both halves (the pointer word really
points at the list; the list really starts with race 1). Crit stub 96 B of the
0x60 reserve — exactly full.

```
data/over_the_nexus/working/rom_nast_notext.nds
sha256 6de5fdec8a841498fe249c3e278a4822b60c44b9bf225f949030864286df0fe6
```

`verify()` PASS for this card and for Hanzo on the same ROM; `check_allocations`
OK. ⚠️ **Static + emulated only. NOT in-game confirmation.**

### Next experiment

Same procedure as round 12 — activate targeting a Ninja and a face-up opponent
monster, then save and run `scratch/nast_state.py`. Expected if the fix is right:
`+0x00` >= 1, `+0x18` > 0, and the phase trace showing `0x80 -> 0x7F -> 0x7E`
followed by a card picker on screen.

## ⭐ IN-GAME TEST 13 (2026-08-31) — C2 AND C3 CONFIRMED WORKING BY THE USER

Build `6de5fdec8a841498fe249c3e278a4822b60c44b9bf225f949030864286df0fe6`
(`rom_nast_notext.nds`, round 13, the race-list pointer fix).

User's exact words:

> "Okay that works! Both monsters were tributed and I could pick one of the
> choices from my deck AND special summon it to my field!"

and, on the race filter:

> "The race filter was correct, I had machine types in my deck that I did not see!"

**IN-GAME CONFIRMED BY USER 2026-08-31** — scoped to exactly this:

* **C2** — the card activates targeting 1 Ninja you control and 1 face-up monster
  your opponent controls, and **both** are sent to the Graveyard.
* **C3 search** — the Deck search runs and shows a **picker with several
  choices**, driven by our criteria row + `CAVE_NAST_CRIT`.
* **C3 race filter** — the whitelist `{1, 9, 5, 0}` = Dragon / Dinosaur / Sea
  Serpent is applied correctly. ⭐ This is a **NEGATIVE CONTROL, not just a
  positive one**: the user had **Machine**-type monsters in the same Deck and
  they were **not offered**. That rules out "the walker returns everything".
* **C3 summon** — the chosen monster is Special Summoned to the **user's own**
  field.

So the whole round-12 phase machine ran end to end:
`0x80 -> 0x7F -> 0x7E -> 0x7C -> 0x78`, with `0x0219C510` -> `0x0226925C`
placing the card on side `r0` as `summon.commit_r0_places_bit4_only_attributes`
predicts.

### NOT confirmed — do not record these as working

* **The Level cap.** User: *"If the level cap is hard-coded then I wasn't able to
  test"*. Correct — as built it is `0x00B00000` = "Level 12 or lower", i.e.
  effectively unrestricted, so the printed "combined original Levels" clause is
  **still an open deviation** and this duel could not have tested it either way.
* **C4** — *"Haven't verified..."*. AWAITING IN-GAME TEST, and expected NOT to
  work: PART E's leave-cleanup list membership is in, but Transformation attaches
  the actual link from its resolver's **phase 1** (`0x0221B30E`), and our
  resolver returns 0 for phase 1. The rider is not built.
* **The name / description.** This was a `--no-text` build, so the in-hand text
  freeze (deviation 3) is untouched and untested.

## ⭐ THE IN-HAND TEXT FREEZE — MECHANISM IDENTIFIED (2026-08-31)

User: *"Consider shortening the name and description"*. Measured before acting,
and the measurement splits the two halves apart:

### The DESCRIPTION is not the problem and shortening it buys nothing

Goblin Fan `0x1255`'s description slots, read from the clean ROM's `bin2.pac`:

| lang | e | f | g | i | s | j | k | r |
|---|---|---|---|---|---|---|---|---|
| desc slot (B) | 153 | 191 | 201 | 195 | 184 | 138 | **131** | 246 |

`NEW_DESC` is **123 B**, so it fits **in place in all eight languages** — the safe
path (`apply_stats_and_text` writes a description strictly in place, and SKIPS a
language whose slot is too small rather than growing the blob). No language is
skipped and no blob grows because of the description.

### The NAME is the problem: it is the only thing that GROWS a blob

Same card's **name** slots: e **10**, f 19, g 12, i 20, s 25, j 12, k 11, r 22.
`NEW_NAME` = `"Ninjitsu Art of Super-Transformation"` = **36 B**, so it overflows
**every** language. `apply_stats_and_text` then takes its other branch: **append
the name at the end of `card_name_<L>.bin` and repoint the index table.**

### The census that convicts it

Across all 34 `patch_*.py` modules with a `NEW_NAME`, comparing it to the donor's
ENGLISH name slot:

* **32 write the name IN PLACE.** Every single in-game-confirmed card in this
  repo does. The names are visibly abbreviated *for exactly this reason* —
  `GK's Recruiter` (14/14), `MetalArm Bug` (12/12), `TG RushRhino` (12/12),
  `XXS - Boggart` (13/14), `T. Sea Horse` (12/14), `W Nebula` (8/9).
* **2 append**: this card (36 into 10), and `tg_striker` (10 into 9, by one byte).

So "shorten the name until it fits the donor's slot" is not a workaround — it is
this codebase's **established, uniformly-followed convention**, and this card is
the one that grossly violates it. Combined with `--no-text` being clean and
`--text` freezing with the card in hand (where the NAME is what is rendered
continuously), the append/repoint path is the mechanism.

⚠️ **NOT PROVEN, and honestly labelled**: no duel has isolated append-vs-in-place.
What is proven is the byte-level fact (36 B into a 10 B slot => append in all 8
languages, description unaffected) and the census. The cheap confirmation is the
next `--text` build with a name that fits.

⚠️ `patch_tg_striker` carries the same latent defect at one byte over
(`"TG Striker"` = 10 into a 9 B slot on donor `0x1F18`). Out of scope this
session — flagged, not touched.

### Consequence for the fix

Shortening the DESCRIPTION is not required and would change nothing mechanically.
The NAME must come down to **10 bytes** to fit English, which is the binding
constraint (Korean 11 and German/Japanese 12 are next). The name is cosmetic for
this card's machinery: **Hanzo finds it by SET CODE `0x2A` (PART A), never by
name**, so no clause depends on the string.

## ROUND 14 — THE TEXT FIX (built 2026-08-31, AWAITING IN-GAME TEST)

`NEW_NAME` = **`b"NA SuperTF"`** (10 B, chosen by the user 2026-08-31).
`NEW_DESC` unchanged at 123 B — it was never implicated.

New build-time guard `assert_text_fits_in_place(rom)`: reads the donor's
per-language name AND description slots straight out of `bin2.pac` and aborts the
build if either string would overflow. Tested both directions — it passes on the
new name and rejects the old 36 B one with
`"NEW_NAME is 36 B but language 'e' only has a 10 B name slot"`.

**Measured on the built ROM — every language wrote IN PLACE:**

| | e | f | g | i | s | j | k | r |
|---|---|---|---|---|---|---|---|---|
| name offset, clean | 0x2BF8 | 0x334C | 0x3698 | 0x31DC | 0x35FC | 0x2858 | 0x1D40 | 0x47AC |
| name offset, `--text` | **same** | same | same | same | same | same | same | same |

**Not one offset moved and not one name blob grew because of this card.**
`bin2.pac` is +48 B overall, which is exactly Hanzo's own two appends (its donor
`0x13E7` has j 14 / k 13 B slots against a 23 B name) — unrelated to this card and
pre-existing on a ROM the user has already played.

```
data/over_the_nexus/working/rom_nast.nds        (--text)
sha256 0b3119600b6bc5139575a0dbd3c177c30b2d53e818a4d97e76a1f6d8d0b0f6e0
```

⚠️ Static only. The in-hand freeze is AWAITING IN-GAME TEST with this build — the
mechanism is argued from the byte facts and the 32-of-34 census, not yet from a
duel.

KB: added `tool.card_name_must_fit_the_donor_slot` (VERIFIED, proof asserts
Goblin Fan's 10 B and donor 0x1F18's 9 B English slots and that three confirmed
cards' names still fit). 370 facts / 335 PASS / 0 FAIL.

## ⭐⭐ C4 — ROOT CAUSE FOUND (2026-08-31), and it is ONE RETURN VALUE

User's exact words:

> "About clause 4. When NAST is destroyed by MST or similar, the monster summon
> does not get banished. See .ml3"

Savestate `rom_nast_notext.ml3` (20:05) confirms the symptom exactly:

* side 0 monster zone 2 = **cid `0x16FF`** — the Special Summoned monster is
  **still on the field**.
* **no `0x1255` in any zone** — the Continuous Trap is gone, destroyed by MST.
* DIAG: resolver entered **6x**, trace `0x7E -> 0x7C -> 0x78 -> 0x64`, criteria
  handler entered 2x, 3 candidates, both targets sent to the GY. So the whole
  C2/C3 machine ran perfectly and the card resolved; only the link is missing.

### THE DIFFERENCE BETWEEN THE TWO CHASSIS IS THE TEARDOWN'S RETURN VALUE

Both chassis end by calling the SAME teardown `0x021D269C(side)`. They differ in
one instruction:

```
deck-SS  0x02206EF4 (phase 0x78):  bl 0x021D269C ; movs r0,#0x64 ; pop
named-SS 0x02207116 (phase 0x7D):  bl 0x021D269C ; movs r0,#1    ; pop   <-- !!
```

The activation driver at `0x02218042` does `strh r0,[r4,#0x18]` and re-enters the
resolver for any NONZERO return, publishing that value at `[0x0229AAFC+0x70]`.
**So returning 1 drives PHASE 1** — and phase 1 is exactly where Ninjitsu Art of
Transformation's wrapper `0x0221B2FC` attaches the "when this card leaves, the
monster goes with it" link:

```
0221B30E ldrb r0,[r3,#2]          ; r0 = desc[+2]           = SIDE
0221B314 ldrb r2,[r3,#3]          ;      desc[+3]           = the card's ZONE
0221B316 ldr  r1,=0x02298A28
0221B318 movs r3,#0x17            ; the rider KIND byte
0221B31A lsls r2,r2,#8 ; orrs r2,r0 ; (zone<<8)|side = a SOURCE-CARD LOCATOR
0221B320 ldrh r1,[r1,#4]          ; r1 = [summon block + 4] = the DESTINATION SLOT
0221B324 bl   0x021C479C          ; rider.node_writer_and_kind_byte, [sp]=0
```

**We copied the deck-SS chassis faithfully — including its `0x64`. Shien's
Footsoldier and Six Scrolls have no attached monster to clean up, so they never
need phase 1. Our card does.** That is the whole of C4's failure.

### Every input the rider needs is present and correct in the savestate

* `[0x02298A28 + 0x04]` = **2** — and `0x16FF` really is in monster zone **2**. ✓
* `[g+0x0E]` = `0x16FF` (the summoned card), `[g+0x12]` = `0x1255` (the summoner,
  written by `0x0226925C` from our `cid << 16` fifth argument). ✓
* descriptor `0x0229A7FC`: `desc[+2]` = 0 (side), `desc[+3]` = **6** — and our
  card was in **S/T zone 6**. ✓ So `(desc[+3]<<8)|desc[+2]` = `0x0600` really is
  this card's locator.

⚠️ **DO NOT copy Transformation's phase-1 body verbatim.** It reads the
descriptor out of **`r3`**, which the resolver invoker `0x0224AEB8` does NOT
set — `0x0224AEC4`'s `bl 0x021A1430` clobbers r0-r3 before the `blx r2` at
`0x0224AF00`. Transformation gets away with whatever `0x021A1430` happens to
leave there. Our arm must rebuild r0/r2 from the descriptor we are handed in r0.

### STILL UNSOLVED: destroy vs banish

This fix makes the monster **leave** when the card leaves. Whether that leave is
a **BANISH** (what the card prints) or a destroy is still unproven — kind `0x17`
is shared by Transformation (destroy) and Escape from the Dark Dimension
(destroy-then-banish), so the kind byte does not encode it. Treat "the monster
now goes away" and "it is banished" as two separate results.

## ⭐ THE BANISH ENCODING — FOUND (2026-08-31), and the earlier note was wrong about WHERE

Rounds 1-12 recorded "the leave-cleanup list does not encode destroy vs banish,
and neither does the rider kind byte 0x17 — the distinction lives elsewhere,
UNPROVEN." **Both halves of that were right; the location was never found. It is
a per-cid switch inside the cleanup body itself:**

```
0x021CB488  movs r0,#0    ; str r0,[sp,#0xAC]     ; reason code
0x021CB48C  movs r0,#0x0E ; str r0,[sp,#0xA8]     ; *** DEFAULT DESTINATION = GRAVEYARD ***
0x021CB490  <per-cid switch on r4 = the LEAVING card's cid>
0x021CB504    movs r0,#0x0D ; -> 0x021CB518       ; one other arm
0x021CB50A    movs r0,#0x0F ; -> 0x021CB514       ; *** BANISHED ***  (0x1D2F Escape)
0x021CB510    r0 = 0x0F     ; -> 0x021CB506/18    ; *** BANISHED ***  (0x1625/0x1880/0x1881/0x1E30)
0x021CB514  movs r0,#2    ; str r0,[sp,#0xAC]     ; the shared tail
0x021CB518  if [sp+0xA8] == 0 -> skip
0x021CB53C  bl 0x021CC290(..., r2 = [sp+0xA8] = THE DESTINATION, ..., [sp] = cid)
```

`[sp+0xA8]` is a **destination zone code**: `0x0E` Graveyard, `0x0F` banished,
`0x0D` something else. Our donor matches no arm, so it took the default `0x0E` —
the card would have DESTROYED the monster, not banished it, even once the link
existed.

**No free compare to steal:** all five cids that reach an `0x0F` arm — `0x1625`,
`0x1880`, `0x1881`, `0x1D2F`, `0x1E30` — are live members of the 40-entry leave
list, so repointing one would cost a real card its banish.

## ROUND 15 — C4 BUILT (both halves)

**PART F3 (ov5), two changes to the resolver:**

1. **phase `0x78` now returns `1`, not `0x64`.** That single immediate is what
   drives phase 1 at all.
2. **a new phase-`0x01` arm** — `0x021C479C(side, [0x02298A28+4], locator, 0x17,
   [sp]=0)` with `locator = (desc[+3]<<8) | desc[+2]`, rebuilt from R5 rather
   than read out of R3 the way Transformation does (the invoker `0x0224AEB8`
   does not set R3 — its `bl 0x021A1430` clobbers r0-r3 before the `blx r2`).

Resolver 412 B; `CAVE_NAST_RES2` reserve grown `0x180 -> 0x200`, `CAVE_FREE`
`0x0239DD00 -> 0x0239DD80`.

**PART H (ov3), the destination:** a 20 B stub at **`0x0225F2A8`** — the 22 B
still free in the `0x0225F240` dead block — reached from a 4-byte `BL` that
replaces the DEFAULT `movs r0,#0x0E ; str r0,[sp,#0xA8]` at `0x021CB48C`:

```
movs r0,#0x0E ; movs r1,#0x12 ; lsls r1,r1,#8 ; adds r1,#0x55
cmp r4,r1 ; bne keep ; movs r0,#0x0F
keep: str r0,[sp,#0xA8] ; bx lr
```

Pool-free (0x1255 built with `movs/lsls/adds`) so it needs no 4-aligned literal,
and it runs at the host's own SP — **no push**, or `[sp,#0xA8]` would address the
wrong slot. Our cid then falls through to `0x021CB514` and picks up
`[sp+0xAC] = 2`, i.e. **the same destination AND the same reason code as Escape
from the Dark Dimension**.

⚠️ **THE STUB IS IN OV3, NOT THE OV5 CAVE, DELIBERATELY.** `0x021CB48C` is a
SHARED site all 40 leave-list cards run through, and a puzzle loads overlay 41
over overlay 5 — a `bl` into ov5 here would freeze Premature Burial, Call of the
Haunted and friends in every puzzle (`otn-continuous-stat-engine`: *never
bl-hijack a shared fall-through into ov5*).

Safety of replacing those 4 bytes, checked by inspection of the whole intervening
range: between the call at `0x021CB47C` and the reload at `0x021CB4DC`, **only r0
and r4 are read** — r1/r2/r3 are dead scratch — and `0x021CB514` re-sets r0
anyway, so only `[sp+0xA8]` has to survive, and nothing on the default path
rewrites it. Four new preconditions pin the hook bytes, Escape's own banish arm,
the shared tail, and the destination read at `0x021CB536`.

⚠️ **ASSUMED, not proven:** that phase 1 is actually driven for our card once the
resolver returns 1. The driver `0x02218042` is card-agnostic so it should be, but
it is unmeasured — DIAG `+0x14`'s trace will show `0x01` if it happened.

### Next experiment — C4, one duel

Build `_build_nast.py --text` (or `--no-text`) and, in a NORMAL duel:

1. Activate the card on a Ninja + a face-up opponent monster, Special Summon a
   monster from the Deck.
2. Destroy the face-up Continuous Trap with MST or equivalent.
3. Save state and run `scratch/nast_state.py`.

Three distinguishable outcomes, and the DIAG phase trace `+0x14` separates them:

| what you see | trace | reading |
|---|---|---|
| monster still there | no `0x01` | phase 1 is NOT driven by returning 1 — the ASSUMED step is wrong, and the hook has to move |
| monster still there | `0x01` present | phase 1 ran but `0x021C479C` did not create a link the cleanup reads — suspect the locator or `[g+4]` |
| monster **destroyed** (to the GY) | `0x01` present | the link works and PART H's destination stub did not take — check `0x021CB48C` in the built ROM |
| monster **banished** | `0x01` present | C4 complete |

Expect the trace to read `0x7C -> 0x78 -> 0x01 -> ...` where round 13 read
`0x7C -> 0x78 -> 0x64`.

### ROUND 15 BUILDS

```
rom_nast_notext.nds  sha256 23486ead4aea1235f342dd477af9bf2c4e1e5f849209bfc34c173ff4e1b25848
rom_nast.nds (--text) sha256 d95d933c056326f5cc93687a3890c83bc1a6a1dc88614d7af01d75925129dd69
```

Both: `verify()` all PASS for this card AND for Hanzo; PART H's `BL 93f00cff` is
at `0x021CB48C` and the 20 B stub is at `0x0225F2A8` in both. `--text` logged
**in-place** for the name in all 8 languages (`10/12 B` Japanese, `10/11 B`
Korean being the tightest) and in-place for the description everywhere
(`123/131 B` Korean tightest). ⚠️ Static only.

## ⭐⭐ IN-GAME TEST 15 (2026-08-31) — THE TEXT FREEZE IS FIXED, AND C4 FIRES

User's exact words:

> "I confirm the new text does not cause a freeze and C4 works"

**IN-GAME CONFIRMED BY USER 2026-08-31:**

* **The in-hand text freeze is GONE.** Built with `--text`
  (`d95d933c056326f5cc93687a3890c83bc1a6a1dc88614d7af01d75925129dd69`), the card
  can be held in hand with its own name and description and the game does not
  freeze. This closes deviation 3, open since round 1.
  ⭐ **It confirms the mechanism, not just the fix**: the ONLY change between the
  freezing build and this one is that `NEW_NAME` went from 36 B to 10 B, which
  moved the name from `apply_stats_and_text`'s APPEND+repoint path onto its
  IN-PLACE path in all 8 languages. Nothing else about the text changed — the
  description was byte-identical in both builds. So the blob-growing append
  really was the freeze, and `tool.card_name_must_fit_the_donor_slot` is now
  behaviourally confirmed rather than argued from a census.
* **C4 FIRES.** Returning `1` instead of `0x64` from resolver phase `0x78` does
  drive **phase 1** — the one ASSUMED step in round 15 — and the phase-1 arm's
  `0x021C479C(side, [0x02298A28+4], locator, 0x17, [sp]=0)` creates a link the
  leave-cleanup acts on. The summoned monster no longer survives the Continuous
  Trap leaving the field.

### ⭐ C4 IS A BANISH — CONFIRMED 2026-08-31

User's exact words, asked directly whether the leave was a destroy or a banish:

> "C4 is a banish"

So **clause 4 is complete as printed**, and PART H does what it was written to do.
This also **behaviourally proves the destination switch** that rounds 1-14
recorded as *"the distinction lives elsewhere, UNPROVEN"*: our donor `0x1255`
matches no arm and therefore took the default `0x0E` (Graveyard); a 20 B ov3 stub
that replaces ONLY the default preset and writes `0x0F` for that one cid changed
the observed behaviour from "nothing happens" to "the monster is banished".
`[sp+0xA8]` really is a destination zone code, and `0x0E` / `0x0F` really are
Graveyard / banished. Written up as the new KB fact
`leave.cleanup_destination_switch` (VERIFIED).

## ROUND 16 — THE LEVEL CAP, THE LAST UNBUILT CLAUSE (2026-08-31)

Deviation 1 — *"whose Level is less than or equal to the combined original
Levels of the sent monster(s)"* — was hardcoded to "Level 12 or lower" through
15 rounds because no `param` source carried the sum. It is now computed.

### The primitive: `0x0202ABD8(cid)` -> the card's ORIGINAL Level

ARM9, Thumb, always resident. Same accessor family as the VERIFIED race reader
`0x0202ABB8` (`card_data_files`): `bl 0x0202A084` for the card_prop record, then
`ldr r0,[r0,#4] ; lsls #0x12 ; lsrs #0x1C` — the 4-bit level field at bit 42,
matching `game_constants`' `level=BitField(42, 4)`.

**Cross-checked against `card_prop.bin` by emulating it on three cards**
(`scratch/thumbemu.py`): `0x13E7` -> 4, `0x16FF` -> 6, `0x1255` -> 0 (a Trap),
all matching the decoder. The whole family fell out of the same check:
`0x0202ABB8` race, `0x0202ABC8` attribute, `0x0202ABD8` **level**, `0x0202ABF8`
card type.

⭐ Incidental corroboration of C3: `0x16FF`, the monster the user actually
summoned in the round-15 duel, reads back as **race 9 = Dinosaur, Level 6** —
independently confirming the `{1, 9, 5, 0}` whitelist was doing its job.

### The handoff: the crit stub's OWN literal is the mutable word

The obvious design — have the criteria handler compute the cap — fails on space:
the handler is 96 B of a 96 B reserve and is boxed in by `CAVE_NAST_RES2` at
`0x0239DB80`. So instead **the resolver overwrites the handler's `LEVEL_BITS`
pool word** at `CAVE_NAST_CRIT + 0x50` = `0x0239DB70`:

```
phase 0x80, BEFORE the GY send (the monsters must still be on the field):
  for each declared target i:
      0x02234904(desc, i) -> packed side/zone
      0x021A36EC(side, zone)  -> cid
      0x0202ABD8(cid)         -> level ; sum += level
  clamp sum to 15                      (the level field is 4 bits)
  [0x0239DB70] = (0x80 | (sum << 2)) << 16      ; op 2 = "Level N or lower"
```

`build_crit_stub` is **completely unchanged** — it still does
`ldr r1,=LEVEL_BITS ; orrs r0,r1`, so it needs no extra space, and `verify()`'s
static byte-compare still passes because the built ROM carries the default
`0x00B00000`. Two new build asserts pin the literal to `+0x50` and to that
default, so the resolver's hardcoded write address cannot drift out of step.

Emulated against `rom_nast_notext.ml3`: the word really is rewritten
(`0xB00000 -> 0x800000`). It reads level 0 there only because that savestate was
taken after the targets had already left the field, which is also the safe
failure mode — `dispatch.criteria_word_level_field` says **level 0 = no level
constraint**, so a failed read leaves the card unrestricted rather than unable to
summon. (The emulator then stops at a `BLX` into ARM code, which is an
interpreter limit, not a patch fault.)

⚠️ AWAITING IN-GAME TEST. The check is a duel where the two sent monsters have a
small combined Level: send e.g. two Level-3 monsters and confirm the Deck search
offers only Level 6 or lower, and that a Level 7+ Dragon in the same Deck is NOT
offered — the same negative-control shape that settled the race filter.

### ROUND 16 BUILDS

```
rom_nast.nds (--text)   sha256 d326d8bab0fc7cd75121f272b2141848a1d3bfc355991f1f91a2496ccdd9f43e
rom_nast_notext.nds     sha256 e159f77507a8743b0a58148c0bf71dc4b87518425823dac12fbc459d3b38f7ec
```

`verify()` all PASS for this card and for Hanzo; `check_allocations` in sync
(153 ov5 slots, 11 ov3 dead-code claims, 54 B ov3 still free); `verify_knowledge`
371 facts / 335 PASS / 0 FAIL. Resolver 488 B of its 0x200 reserve; criteria
handler unchanged at 96 B. ⚠️ Static + emulated only.

## ⭐ IN-GAME TEST 16 (2026-08-31) — THE LEVEL CAP WORKS; REDMD IS CORRECTLY EXCLUDED

User's exact words:

> "1. I have 3 REDMD in my deck and I am not offered them when tributing 2 level
> 4s. See .ml3 to confirm."

Savestate `rom_nast.ml3` (21:53), round-16 `--text` build
`d326d8bab0fc7cd75121f272b2141848a1d3bfc355991f1f91a2496ccdd9f43e`, captured
**with the picker open** (trace ends at `0x7E`, `0x7C` has not run yet — the
ideal moment):

```
LEVEL CAP word @0x0239DB70 = 0x00A00000  ->  "Level 8 or lower"
DECK SEARCH OFFERED 2 candidate(s):
   0x16FF  Dark Driceratops             Lv6  Dinosaur
   0x207D  Divine Dragon Aquabizarre    Lv5  Sea Serpent
```

**THIS IS THE CLAUSE WORKING, NOT A BUG.** Two Level 4 monsters were sent, the
resolver summed their original Levels to **8**, and wrote op 2 / level 8 =
"Level 8 or lower" into the criteria word. **Red-Eyes Darkness Metal Dragon is
cid `0x1D85`, Level 10** — read out of `card_prop.bin` in this very ROM, not from
recall (`never-assert-ygo-rulings-from-recall`). 10 > 8, so the printed text —
*"whose Level is less than or equal to the combined original Levels of the sent
monster(s)"* — requires it to be excluded.

⭐ The picker's own contents prove BOTH remaining filters at once: the two cards
offered are a **Dinosaur** and a **Sea Serpent** (the race whitelist) and both are
**Level 5-6** (the new cap), while a Level 10 Dragon in the same Deck is refused.
That is a positive and a negative control in a single duel.

**So every printed clause of this card is now in-game confirmed.**

### Two tooling fixes this test forced

1. `scratch/nast_state.py` REFUSED the savestate as "mixed build" — because the
   criteria handler's `LEVEL_BITS` word at `+0x50` is a deliberate RUNTIME
   handoff, so a byte-compare against the rebuilt blob fails on every
   post-resolution state. The identity check now skips those 4 bytes and prints
   the live value decoded as `"Level N or lower"`. ⚠️ A guard that cannot tell
   "different build" from "this build, mid-run" is worse than no guard.
2. The reader now **dumps the candidate list with each card's name, Level and
   race**, from the locator array `0x02299458` (stride 4, cid in the low 14 bits)
   and the count at `[0x0229944C+6]`. That is the single most informative read in
   the file: a wrongly-included or wrongly-excluded card is visible BY NAME.

## SHIPPED — WIRED INTO `apply_all_patches` (2026-08-31, on the user's "Wire it in")

Inserted as step **36 of 43**, immediately after Ninja Grandmaster Hanzo (step 35)
and well before the WiFi-timers step, which must stay last.

### Composition analysis, done BEFORE wiring rather than after

**One hard ordering constraint.** It MUST follow `ninja_grandmaster_hanzo`: PART A
inserts the donor into the ARM9 set code `0x2A` over the phantom `0x1C55`, and
that set code only means "Ninjitsu Art" — and only has that phantom to spend —
because Hanzo repurposed it. On a clean ROM PART A's assert fires rather than
shipping silently.

**The shared-site risk, and why it is safe.** PART H replaces the 4 bytes at
`0x021CB48C`, which are the leave-cleanup's DEFAULT destination preset and are run
by **all 40 members** of `leave.attached_card_destroy_list` — Premature Burial,
Call of the Haunted, and notably **Battle-Scarred, `patch_safe_zone`'s donor,
which is natively a member**. The replacement BL reaches a stub that writes `0x0F`
for cid `0x1255` and `0x0E` for every other cid, so every other member's
behaviour is preserved **byte-for-byte**. Checked, not assumed:

* the only two shipped patches that mention `0x0226E940` / `0x021CB48C` at all are
  `patch_lightpulsar` and `patch_safe_zone`, and **neither writes there** — both
  only reference the address in comments (Lightpulsar to explain that list30 abuts
  it and therefore cannot grow; Safe Zone to note its donor is already a member).
* only `r0` and `r4` are live between `0x021CB47C` and `0x021CB4DC`, and
  `0x021CB514` re-sets `r0` anyway, so only `[sp+0xA8]` has to survive the stub.

**Slots claimed, all registered and collision-checked** (`check_allocations`:
153 ov5 slots, 127 phantom claims, 11 ov3 dead-code claims, no overlaps, ledger in
sync): ov5 `CAVE_NAST_PRED` / `CAVE_NAST_DIAG` / `CAVE_NAST_CRIT` /
`CAVE_NAST_RES2`; ov3 dead code `0x0225F2A8` (20 B, the tail of the `0x0225F240`
block whose head `handss_banish_cost` owns); phantoms `0x1C55` (set code),
`0x0E1A` (cls0), `0x0E12` (criteria), `0x0E42` (leave list).

### ⚠️ A GAP THIS SHIP EXPOSED — the verify sweep was silently incomplete

`_verify_all_patches.py`'s `SHIPPED` list is deliberately explicit ("a wrong
pairing here would silently skip a card"), and **`patch_ninja_grandmaster_hanzo`
was never added to it when it shipped on 2026-08-30** — so for a day the sweep
quietly did not check Hanzo at all. That is precisely the failure mode the
module's own docstring warns about: an omission from an explicit list is
invisible, because a skipped card looks exactly like a card that passed. Both
Hanzo and this card are now in the list.

**Standing lesson: when shipping a card, adding it to `apply_all_patches` is only
half the job — it must go into `_verify_all_patches.SHIPPED` in the same edit.**

### ⚠️ THE FIRST CHAIN BUILD DIED AT 27/43 AND LEFT A VALID-LOOKING ROM

Started 2026-08-31 22:01, last wrote at **22:26 on step 27 of 43**, and was dead
by the time it was next checked. It had already written
`data/over_the_nexus/working/rom_all_patches.nds` — 129,522,824 B, correct size,
loads fine, and **missing this card entirely** (step 36 never ran):

```
sha256 ddc5265470ef614ed72ccaf5b8b0036ac9597cbd5272675a2b1bba7d63522792
  our cls0 record present?   False
  PART H hook installed?     False (still the stock 0e202a90)
```

This is exactly the failure CLAUDE.md's *Shell Usage* rule names — *"a silent
death at 4/32 once produced a valid-looking ROM that wasted an in-game test"* —
and the reason the rule says to assert the **final patch count and ROM hash**
rather than trusting that the file exists. The partial output was renamed to
`rom_all_patches.INCOMPLETE_27of43.nds` so it cannot be mistaken for a build, and
the chain was restarted.

**Reusable habit:** move the previous combined ROM aside BEFORE starting a chain
build. A partial build then leaves no file at all rather than a plausible one,
which converts a silent wrong-ROM test into an obvious missing-file error.

### ⚠️ THE CHAIN BUILD THEN ABORTED AT STEP 36 — A HARDCODED ROW INDEX

`CHAIN_EXIT=1` at step **36/43**, which is this card, on:

```
AssertionError: Shien's Footsoldier no longer routes to the shared deck-SS resolver
  assert _u32(ov, 0x02275C04 + 237 * 24) == 0x1B3A ...
```

**The assert was right to fire and the fact it encoded was wrong.** `cls2[237]` is
where Shien's Footsoldier sits **in a clean ROM**; the 35 patches ahead of us do
count-neutral inserts into cls2, and every one of those shifts every row after its
insertion point. A row index is a fact about ONE IMAGE, not about the table.

Fixed to search by cid — `cls2.index(0x1B3A)` — and **validated against the exact
image that failed** (the partial 35-patch ROM) rather than by rebuilding and
hoping. Then the whole patch was applied onto that same 35-patch image as a smoke
test: all of PARTS A/C/D/E/F/H verified PASS in the combined context, including
`PART H: Escape from the Dark Dimension's own banish arm unregressed`. Only then
was the ~25-minute clean rebuild started.

**Reusable rule, and it applies to every precondition in this directory: anchor a
shipped-chain assert on a CID, never on a row index.** Single-card builds start
from `rom.nds` and so never catch this; the chain build is the only thing that
does, which makes it the first place a clean-ROM index assumption shows up. The
other anchors in this module already used `.index(cid)` — this was the one that
did not.

⚠️ Both failed outputs were renamed rather than deleted, so neither can be
mistaken for a build: `rom_all_patches.INCOMPLETE_27of43.nds` (the overnight
death) and `rom_all_patches.PARTIAL_35of43.nds` (this abort).

## ✅ SHIPPED — CHAIN BUILT AND SWEPT CLEAN (2026-09-01)

```
data/over_the_nexus/working/rom_all_patches.nds
sha256 bb6229d6060991a077e66cc60dd15c6fb957d8a25dd67743a775c33578ee6eee
```

**The assertions CLAUDE.md requires, checked against the ARTIFACT and not the log:**

* `CHAIN_EXIT=0`, **43/43** steps, and `len(apply_all_patches.PATCHES) == 43`.
* our `cls0` record for `0x1255` **is present** in the built ROM;
* PART H's `BL` **is installed** at `0x021CB48C`.

(The first two builds both produced a plausible file and neither was a build:
one died overnight at 27/43, one aborted at 36/43. Checking the log or the file's
existence would have passed both. Checking the CONTENT is what caught them.)

**`_verify_all_patches.py` over the combined ROM: PASS 32 / FAIL 0 / SKIP 2.**
The two skips are `patch_boggart_knight` and `patch_darksoul`, which have no
`verify()` of their own — pre-existing, not a regression. 34 modules covered,
including `patch_ninja_grandmaster_hanzo` (in the sweep for the first time) and
this card. Notably `PART H: Escape from the Dark Dimension's own banish arm
unregressed` passes on the combined image, which is the shared-site check that
mattered.

`check_allocations`: 154 ov5 slots, 130 phantom claims, 11 ov3 dead-code claims,
no overlaps, ledger in sync. `verify_knowledge`: 377 facts / 341 PASS / 0 FAIL.

⚠️ The combined ROM is **NOT puzzle-safe** — this card uses ov5, as do Hanzo
clause 2 and several others already in the chain. Normal, turbo, tag and
tag-turbo duels are unaffected.
