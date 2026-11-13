# Vylon Element vs Tour Guide — the Synchro-material deny-key contention (2026-09-11)

> **RESOLVED (user decision 2026-09-11): Tour Guide MOVED from deny key 5 to deny key 3.**
> `patch_tour_guide` PART B is now the single 4-byte pool edit `0x02248564: 0x237A -> 0x0FC2`.
> Key 5 and its `BNE` gate are left native, so **Vylon Element 0x24B5 has her rider back** and
> her real printed description is now written into the ROM via `card_text.CARD_TEXT[0x24B5]`.
>
> **The price, stated plainly: Necro Linker 0x237A AND Wiseman's Chalice 0x231F both lose their
> Synchro-Material riders** — key 4 is derived from key 3's pool word, and the measurements
> below prove it cannot be repaired. That is one card MORE than the key-5 arrangement cost.
> The user chose this knowing the count; which cards matter is their call, not a numeric one.
>
> Verified on a real build: slot1 Cherry Inmato 0x225E native, slot2 Chaos Goddess 0x2273
> native, slot3 = 0x0FC2 (ours), slot4 = 0x0F67 (dead), slot5 0x24B5 native, gate 0xD101 native.
>
> ## IN-GAME CONFIRMED BY USER 2026-09-11 — both embargoes AND Vylon's exception
>
> Tested on `rom_ee_definitive_my_test.nds`,
> sha256 `7196d23eeb0f5520c20139dabef2360fa8fe8f2932bfb645ccc8a413e0dc414c`.
>
> **That hash IS the new canonical baseline.** The oracle chain
> (`apply_all_patches`, 55/55, `ALL 55 PATCHES APPLIED`) rebuilt to
> `7196d23e...dc414c` byte-for-byte, so the confirmation below applies to the shipped build and
> not to a side ROM. Previous baseline was `602a0308...f357`.
> **ROM identity was checked, not assumed** — its deny slots read
> `slot1=0x225E slot2=0x2273 slot3=0x0FC2 slot4=0x0F67 slot5=0x24B5 gate=0xD101`, i.e. the
> key-3 arrangement, so the report is about this build and not a stale ROM.
>
> User's exact words:
> > "Okay vylon elements synchro restriction applies. Tour Guides, sychro restriction applies"
>
> and, asked specifically whether the Vylon exception fires:
> > "yes I can synchro vylon synchros"
>
> **Confirmed:**
> * Tour Guide's summoned Level 3 Fiend is REFUSED as Synchro Material (the half that moved from
>   key 5 to key 3).
> * Vylon Element's summoned "Vylon" Tuners are REFUSED as Synchro Material.
> * Vylon Element's Tuners ARE ACCEPTED for the Synchro Summon of a "Vylon" Synchro Monster —
>   the `has_set_code` exception at `0x02023ED4` behind the restored `BNE` gate. This is the
>   behaviour that distinguishes a genuine key-5 restore from a plain unconditional deny, so it
>   is the check that actually proves the rearrangement landed correctly.
>
> * **Tour Guide's NEGATE half — CONFIRMED BY USER 2026-09-11**, in a follow-up test:
>   "Tour Guide negate was tested and it works as expected." The Level 3 Fiend it Special
>   Summons has its effects negated. This matters independently of the embargo: the two are
>   separate consumers of the same attached node — the embargo proves A4 (the node is attached
>   at all), while negation proves **A5's reader key set `0x0226FAB4`** still honours the
>   donor's key. Every current build hashes `7196d23e…dc414c`, so ROM identity is unambiguous.
>
> * **The collateral — CONFIRMED BY USER 2026-09-11**, in a third test: "Necro Linker /
>   Wiseman's Chalice collateral is confirmed now. I just tested." Necro Linker 0x237A and
>   Wiseman's Chalice 0x231F no longer impose their "cannot be used as Synchro Material" rider.
>   This is the PREDICTED consequence of key 4 being derived from key 3's pool word
>   (`SUB R5,#0x5B` -> 0x0F67, which is nothing), observed rather than inferred.
>
> **THE DENY-KEY WORK IS FULLY CLOSED.** All five deny slots are now accounted for in a duel,
> not on paper:
>
> | slot | cid | card | in-game 2026-09-11 |
> |---|---|---|---|
> | 1 | 0x225E | Cherry Inmato | untouched (native) |
> | 2 | 0x2273 | Chaos Goddess | untouched (native, derived from slot 1) |
> | 3 | 0x0FC2 | **Tour Guide** | embargo applies; negate works |
> | 4 | 0x0F67 | *(was Wiseman's Chalice 0x231F)* | **rider lost — confirmed** |
> | 5 | 0x24B5 | **Vylon Element** | rider applies AND the Vylon-Synchro exception fires |
>
> plus Necro Linker 0x237A, displaced from slot 3 — **rider lost, confirmed**.
>
> The 2-for-1 trade the user chose knowingly (two cards lose a rider so Vylon regains hers and
> her printed text becomes true) is now fully observed. Nothing about this change remains
> inferred.

## The problem

`patch_tour_guide` PART B spends **deny key 5**, which natively belongs to **Vylon Element
0x24B5**, and NOPs the Vylon archetype gate so the deny becomes unconditional. Its own docstring
records this: *"KNOWN TRADE-OFF, one card as before: Vylon Element loses her 'cannot be used as
Synchro Material except for a Vylon Synchro' rider."*

Vylon is step 6, Tour Guide is step 8, so in the chained ROM the rider is gone. That collides
with writing Vylon Element's printed description (2026-09-11), whose last sentence promises
exactly that rider.

## Confirmed this session — the predicate's real shape

Disassembled `0x02248500-0x022485C8` from the clean overlay 3 (`eu_apfix.nds`), not from prose.

**There are exactly FIVE deny slots, each one a separate call to the family-1 attached-node
walker `0x021A1430` with the key in r2.** A slot is one equality test against one key value.

| slot | key source | value | card |
|---|---|---|---|
| 1 | `ldr r5,[pc,#0x54]` -> pool `0x02248560` | 0x225E | Cherry Inmato |
| 2 | `adds r5,#0x15` @`0x0224851C` (derived from slot 1) | 0x2273 | Chaos Goddess |
| 3 | `ldr r5,[pc,#0x30]` -> pool `0x02248564` | 0x237A | Necro Linker |
| 4 | `subs r5,#0x5B` @`0x0224857A` (derived from slot 3) | 0x231F | Wiseman's Chalice |
| 5 | `ldr r2,[pc,#0x1c]` -> pool `0x022485B0` | 0x24B5 | Vylon Element |

Slot 5 in full:

```
02248590  ldr  r2,[pc,#0x1c]   ; 0x24B5
02248596  bl   0x021A1430      ; slot carries a node keyed r2?
0224859C  beq  022485AC        ; no node  -> ALLOW
0224859E  adds r0,r7,#0        ; r7 = the SYNCHRO being summoned
022485A0  bl   0x02023ED4      ; has_set_code(synchro, "Vylon")
022485A6  bne  022485AC        ; it IS a Vylon Synchro -> ALLOW
022485A8  movs r0,#0           ; else DENY
022485AC  movs r0,#1           ; ALLOW
```

**The pool word `0x022485B0` is the last 4 bytes before the next function begins at
`0x022485B4` (`push {r1-r7,lr}`). There is no slack after it.**

The literal pool at `0x02248534-0x02248566` is packed with live values (0x2184, 0x0F7D, 0x0E66,
0x1FEA, **0x2346** — boggart's pivot literal —, 0x02275B04, 0x0229ABFC, 0x0B3C, 0x0229ACD8,
0x2068, 0x23D2, 0x225E, 0x237A). No free word there, which matches the older note.

## The arithmetic constraint, restated precisely

Slots 2 and 4 are *derived* from 1 and 3 by an 8-bit immediate, so a pool word covers two cids
only when they differ by <= 0xFF. The relevant deltas:

* Tour Guide 0x0FC2 vs Chaos Goddess 0x2273 = **0x12B1**
* Tour Guide 0x0FC2 vs Wiseman's 0x231F = **0x135D**
* Tour Guide 0x0FC2 vs Vylon 0x24B5 = **0x14F3**

All far beyond imm8. This is why the old Synchron Explorer build could take slot 1 (|0x2273 -
0x229E| = 0x2B fits) and a Normal-Monster donor cannot.

## So: FIVE slots, SIX cards want them

Cherry Inmato, Chaos Goddess, Necro Linker, Wiseman's Chalice, Vylon Element, Tour Guide.
Something has to give. Three ways out, in order of how much they cost:

### (A) Add a SIXTH deny check in ov3 dead code — nobody shares, nobody loses

`OV3_DEAD_BLOCKS` (`check_allocations.py:1069`) is **always-resident in every duel mode,
puzzles included** (`mem.ov3_resident_all_modes`) — unlike the ov5 cave. The ledger currently
reports **38 B free**.

A sixth check is roughly: `ldr r2,[pc,#..]` + 3 `adds` + `bl walker` + `cmp` + `beq` + `movs r0,#0`
+ `pop`, plus a 4-byte literal ~= **20-24 B**. It fits, if a single block has that much left
(the pool is fragmented: blocks are 8-44 B).

Reached by replacing one instruction pair in the predicate with a `BL` into the dead block
(Thumb-1 `B` cannot reach — the dead blocks are ~0x93000 / ~0x17000 away — but `BL` is +-4 MB).
This is the boggart trampoline pattern, except the target is ov3 rather than ov5, so it stays
puzzle-safe.

**Cost:** ~22 B of a shared 38 B pool, a ledger claim, and an in-game test.

### (B) Share slot 5 — what "just let them share" would require

Two cards can share one slot only if their attached nodes carry the **same key**. Tour Guide's
node key is *not* choosable: at `0x0226806E` the Special-Summon commit reads it generically with
`LDRH R2,[R4,#0x12]` — the summoning card's own cid.

So sharing needs a **cid remap (0x0FC2 -> 0x24B5) hooked into the SS-commit path**. That path
runs for EVERY Special Summon and is puzzle-resident, so the stub cannot live in ov5 (overlay 41
evicts it -> freeze on the first SS in a puzzle). It would have to go in the same ov3 dead pool
as (A) — i.e. **the same cost, on a hotter path, for a strictly worse outcome.**

It also hands Tour Guide the Vylon exception (its summoned monster becomes legal material for a
"Vylon" Synchro Summon). Negligible in practice, but it is a real deviation from the printed
"it cannot be used as Synchro Material".

**(A) dominates (B).** Sharing is possible but there is no reason to prefer it.

### (C) Accept the trade-off and drop the sentence from Vylon's description

Zero ROM risk. The card then reads as what it does.

## ⚠️ MEASURED 2026-09-11: (A) AND (B) ARE BOTH BLOCKED ON SPACE

I recommended (A) and then ran its own step-1 check, which falsified it. Recording that, because
the number is the useful part.

**The ledger's "38 B free" is FRAGMENTED. The largest contiguous run is 12 B.**
(`OV3_DEAD_BLOCKS` minus `OV3_CLAIMS`, computed per block:)

```
block 0x021B2A4C  30 B  free   0    block 0x021B58E6  30 B  free   4  (largest run  4)
block 0x021B54E0  44 B  free   0    block 0x021B591E  28 B  free   2  (largest run  2)
block 0x021B56B8  16 B  free   0    block 0x021B594A   8 B  free   0
block 0x021B57EE  22 B  free   0    block 0x021B5952   8 B  free   0
block 0x021B582A  30 B  free   8    block 0x021B5AAA  10 B  free  10  (largest run 10)
block 0x021B58D0  12 B  free  12    block 0x0225F240 126 B  free   2  (largest run  2)
   ^ LARGEST CONTIGUOUS FREE RUN = 12 B
```

Sizing both candidates honestly:

* **(A) a 6th deny check:** `ldr r2,[pc]` + 2 `adds` + `bl walker` + `cmp` + `bne` + replayed
  pair + `bx lr` + `movs r0,#0` + `pop` + a 4 B literal ~= **28 B**.
* **(B) a node-key remap at the SS-commit site:** replayed pair + `ldr r3,[pc]` + `cmp` + `bne`
  + `ldr r2,[pc]` + `bx lr` + two 4 B literals ~= **22 B**.

Both need roughly double the 12 B available. Splitting across the 12 B and 10 B blocks costs a
2 B `B` each way and still does not reach. **So the clean fix is blocked on SPACE, not design.**

## MEASURED 2026-09-11: "steal Cherry Inmato's key" costs TWO cards, not one

Slot 2 (Chaos Goddess) is **derived from slot 1's pool word** — `adds r5,#0x15` at
`0x0224851C`. Repointing pool 1 (`0x02248560`) at Tour Guide 0x0FC2 therefore makes slot 2 check
0x0FD7, which is nothing. Both Cherry Inmato AND Chaos Goddess lose their embargo.

To keep Chaos Goddess, slot 2 must become independent — i.e. convert a 2-byte instruction
(`adds r5,#0x15` at `0x0224851C`, or `adds r2,r5,#0` at `0x02248522`) into a 2-byte
`ldr rX,[pc,#imm]` reading a word that holds 0x2273. **Measured: impossible here.**

* **Every 4-aligned word in every literal-pool cluster within LDR reach is already referenced.**
  Clusters in range (scanning the whole overlay for the `ldr rX,[pc,#imm]` encoding, which
  over-approximates references and so errs on the safe side):
  ```
  0x02248534..0x02248564  13 words, HOLES: none
  0x022485B0..0x022485B0   1 word,  HOLES: none
  0x02248840..0x0224886C  12 words, HOLES: none
  ```
* **No word in range already CONTAINS 0x2273** (which would have allowed a read-only share).
  0x00002273 appears at exactly three 4-aligned addresses in all of overlay 3 —
  `0x0226C364`, `0x02270030`, `0x0227DD7C` — and PC-relative LDR reaches only +0x3FC, i.e. no
  further than `0x02248920`.

The same arithmetic rules out every rearrangement of the pair: for one pool word to cover both
Tour Guide and Chaos Goddess they would have to differ by <= 0xFF, and
|0x2273 - 0x0FC2| = 0x12B1. Setting pool 1 to 0x0FAD instead (so slot 2 lands on Tour Guide)
just wastes slot 1 rather than slot 2. **Taking the 1/2 pair always costs both cards.** The 3/4
pair behaves identically (Necro Linker + Wiseman's Chalice, delta 0x135D).

### Consequence: the shipped arrangement is already the minimum-cost one

| arrangement | Tour Guide | cards that lose their embargo |
|---|---|---|
| **shipped today** (key 5, the terminal slot) | yes | Vylon Element — **1** |
| steal Cherry's key (slot 1/2 pair) | yes | Cherry Inmato + Chaos Goddess — **2**, Vylon restored |

Key 5 is the only slot with no arithmetic successor, which is precisely why the previous session
chose it. Swapping to slot 1 trades one lost card for two.

⚠️ That is a *count*, not a judgement. Which cards actually matter is the user's call — they
play these decks. If Vylon Element is wanted and Cherry Inmato / Chaos Goddess are not, the
trade is rational even though it is numerically worse.

## Where that leaves it

1. **Free ov3 dead-code space.** Audit the 12 existing `OV3_CLAIMS` for slack (several are
   round numbers that may be over-reserved). Invasive: it touches shipped, in-game-confirmed
   patches, and each reclaim needs its own re-verification.
2. **Accept the trade-off** and drop the Synchro-Material sentence from Vylon Element's
   description, so the card reads as what it does. Zero ROM risk. This is the only option that
   costs nothing and leaves nothing misleading.
3. **Park it** until a larger always-resident block is found. The 126 B hand-SS run
   (`0x0225F240`) was the last big discovery; another may exist.

Option 2 is what I would do now, with 1 as its own session if the rider is wanted back.

*(Superseded — the user took the slot-3 steal instead. Kept because the space measurement is
still the reason a sixth key is not on the table.)*

## THE IN-GAME TEST THIS NEEDS (nothing below is confirmed)

A byte diff cannot establish any of this. Four oracles, on the rebuilt chain ROM:

1. **Tour Guide still works** — Normal Summon it, it offers the prompt, Special Summons a Lv3
   Fiend from hand or Deck, and that monster's effects are negated. (Regression check: the
   embargo moved, but A1-A5 did not.)
2. **Tour Guide's embargo still bites** — the summoned Lv3 Fiend is REFUSED as Synchro Material.
   This is the half that moved from key 5 to key 3.
3. **Vylon Element's rider is back** — the "Vylon" Tuners it Special Summons are REFUSED as
   Synchro Material for a non-"Vylon" Synchro Summon, and ACCEPTED for a "Vylon" Synchro Summon
   (the has_set_code exception at `0x02023ED4`, now un-NOPed).
4. **The collateral is real but bounded** — Necro Linker and Wiseman's Chalice no longer impose
   their riders. Expected; worth one confirmation that nothing else regressed.

Until the user reports these, the correct wording everywhere is **AWAITING IN-GAME TEST**.

⚠️ Whatever is chosen, changing this touches a **shipped, in-game-confirmed card** (Tour Guide's
embargo), so it needs an in-game test of BOTH halves — Tour Guide's summoned Lv3 Fiend still
refused as Synchro Material, AND Vylon's Tuners refused except for a "Vylon" Synchro. Neither is
claimable from a byte diff.
