# Jet Synchron — findings

Card: **Jet Synchron**, Konami id 9742784. FIRE / Machine / Tuner / Effect,
Level 1, ATK 500 / DEF 0.

Printed text (`scratch/ygoprodeck_cache.json`, verbatim — NOT from recall):

> If this card is sent to the GY as Synchro Material: You can add 1 "Junk"
> monster from your Deck to your hand. If this card is in your GY: You can send
> 1 card from your hand to the GY; Special Summon this card, but banish it when
> it leaves the field. You can only use 1 "Jet Synchron" effect per turn, and
> only once that turn.

Clauses:

1. sent to the GY as Synchro Material → you can add 1 "Junk" monster from Deck
   to hand.
2. in your GY → cost: send 1 card from hand to GY; SS this card; rider: banish
   it when it leaves the field.
3. one "Jet Synchron" effect per turn, once that turn (one HOPT across 1 and 2).

## STATUS: DONE — ALL THREE CLAUSES IN-GAME CONFIRMED, SHIPPED 2026-09-03

**In-game confirmed by user 2026-09-03.** Asked specifically whether they had
seen the three items that could each have failed on their own, they answered
**"yes to all"**, then **"Ship it!"**:

1. **Clause 1 still searches** after the timing-class hook — no "missed the
   timing". (That single message was the whole test of PART T.)
2. **Clause 3 locks BOTH clauses** to one use per turn, and **declining a prompt
   burns nothing**.
3. **The copy summoned by clause 2 is BANISHED**, not sent to the GY, when it
   leaves the field.

Tested build: `rom_jet_synchron.nds`, sha256
`4871e198ca522130e0abcb166649a6e67d906331795dc1f2226b623d4a93439a`.
Clause 1 alone was separately confirmed 2026-09-02 (six oracle items, first test).

Wired into `apply_all_patches` on 2026-09-03 — `PatchStep` and the
`_verify_all_patches.SHIPPED` entry added in the **same edit**
(`otn-chain-build-verify-artifact`), with the step placed immediately above the
WiFi-timers step, which must stay last.

⚠️ **THE CARD IS NOW DUEL-ONLY, and that is a REGRESSION from clause 1's state.**
Clause 1 alone was two overlay-3 table writes and puzzle-safe. Clause 2 puts the
card on the shared `criteria_row_hook`, which lives in the ov5 cave and sits
inside `0x02243B9C` — the row resolver every selecting card passes through — so a
puzzle now crashes on the first selection by **any** card. Accepted by explicit
user decision 2026-09-03.

⚠️ **`patch_lightpulsar` CHANGED THIS SESSION and has not been re-duelled.** Its
PART T timing stub moved into the new shared `timing_class_hook.py`, because the
classifier site `0x0224AF96` is a single 4-byte BL and Jet Synchron needed a
second arm. The lift was proven behaviour-preserving **by execution**, not by
argument — but a regression duel on Lightpulsar is still worth one run.

---

## Confirmed (this session, 2026-09-02)

### Sourcing

- **Jet Synchron is NOT in the 3DS build.** Decoded
  `3ds_extract/partition0/romfs/duel/card/CARD_Name_E.bin` (215 316 B, flat
  NUL-terminated UTF-16LE): `Junk Synchron`, `Junk Warrior`, `Junk Servant`,
  `Junk Berserker`, `Junk Blader`, `Junk Collector`, `Junk Defender`,
  `Junk Destroyer`, `Junk Archer`, `Junk Forward` are all present; **`Jet
  Synchron` is absent.** So CLAUDE.md's "check the 3DS first" step is
  *exhausted*, not skipped — there is no Konami implementation to copy.

### KB health

- `verify_knowledge`: **400 facts, 363 PASS / 0 FAIL / 37 UNVERIFIED**.
- `check_allocations`: clean — 167 ov5 slots (152 live), 140 phantom claims,
  11 ov3 dead-code claims (54 B free), no overlaps.

### Donor: Changer Synchron `0x224C`

`donor_scan 0x224C`:

```
0x224C  Changer Synchron   Tuner Monster  Lv1  DARK  Machine  0/0   pack1=28
        name slots: {e:16, f:24, g:13, i:21, j:20, k:0,  r:20, s:17}
        desc slots: {e:131, f:155, g:154, i:143, j:144, k:0, r:278, s:155}
        VERDICT: ENTANGLED -- named by exactly ONE record: cls2 record[555] (+0x0)
        binding occurrence: ov3:0x0227900C/u16
        arm9 data hit: 0x0209C97A   (= its slot in the Synchron set-code list)
```

Three properties, each verified this session:

1. **Stat match.** Level 1 Machine **Tuner** 0/0 → Jet Synchron is Level 1
   Machine Tuner 500/0. Only Attribute (DARK→FIRE) and ATK (0→500) need to
   change; Level, Race and `card_type` are already correct.
2. **Already a "Synchron".** Read the stock ARM9 set-code `0x4C` list at
   `0x0209C968` (15 × u16):
   `0x0D6B 0x1E07 0x1E14 0x1E4E 0x1EA1 0x1EBE 0x1F46 0x20F7 0x21A7 0x224C
   0x229E 0x239E 0x23EE 0x2414 0x2501` — `0x224C` is a stock member. So
   **Junk Speeder and Tuning reach it with no table edit and no phantom spend.**
   (That list's only phantom `0x2501` is already spent by
   `patch_unknown_synchron`, so this was otherwise unbuyable.)
3. **Its printed effect is already the clause-1 trigger.** Changer Synchron:
   *"If this card is sent to the Graveyard for a Synchro Summon, select 1
   monster your opponent controls and change its battle position."*

⚠️ **Korean name and description slots are 0 bytes.** `langs` must exclude `k`
or `apply_stats_and_text` takes the append path and grows the blob — the failure
mode that froze the game once (`tool.card_name_must_fit_the_donor_slot`).
English budget: name **16** (`"Jet Synchron"` = 12 ✓), desc **131**.

### cls2 rows read out of the stock ov3 (`0x02275C04`, stride 24)

```
cls2[555] @0x0227900C  0x224C Changer Synchron
    +04 0x022076A5  +08 0x021E0501  +0C 0x0224A115  +10 0          +14 0x02234E01
cls2[644]            0x23EE Fleur Synchron
    +04 0x0220667D  +08 0          +0C 0          +10 0x021E9A21  +14 0
cls2[358]            0x1E14 Nitro Synchron
    +04 0x022065B9  +08 0          +0C 0          +10 0          +14 0
cls2[385] @0x0227801C  0x1EA9 Plaguespreader Zombie
    +04 0x0220731D  +08 0          +0C 0x021FF06D  +10 0x021E9039  +14 0
cls2[359] @0x02277DAC  0x1E15 Quillbolt Hedgehog
    +04 0x0220731D  +08 0x021DBB75  +0C 0x021F04FD  +10 0          +14 0
```

`+04 = 0x022076A5` is the shared **change-battle-position** resolver; its only
four users are Gadget Driver `0x1ECA`, Changer Synchron `0x224C`, A/D Changer
`0x22E8`, Junk Gardna `0x2355` — a clean semantic family, so reading it as "the
position-change action" is not a guess.

Sibling Synchro-Material triggers, useful as wording/shape controls:
**Fleur Synchron `0x23EE`** *"If this card is sent to the Graveyard as a Synchro
Material: **You can** Special Summon 1 Level 2 or lower monster from your hand"*
(note the optional "You can" — the wording Jet Synchron needs) and
**Bri Synchron `0x2414`**.

### ✅ CLAUSE 1 IS FULLY SPECIFIED — three exemplars ship it verbatim

Joined every cls2 record's cid to its printed ygoprodeck text and matched
`sent to the (GY|Graveyard) ... (Synchro Material|Synchro Summon)`:
**23 cls2 records** are Synchro-Material triggers. Three of them are Jet
Synchron clause 1 *word for word* — "if sent to the GY as Synchro Material:
**You can** add 1 &lt;X&gt; from your **Deck** to your **hand**" — and all three carry
an **identical** row shape:

```
[ 409] 0x1F54 Arcane Apprentice   "...you can add 1 'Assault Mode Activate' from your Deck to your hand."
[ 577] 0x22CB Vylon Cube          "...You can add 1 Equip Spell Card from your Deck to your hand."
[ 596] 0x2306 Synchro Fusionist   "...you can add 1 Spell Card from your Deck to your hand with
                                   'Polymerization' or 'Fusion' in its name."

   all three:  +04 0x02207EF5   add-to-hand resolver
               +08 0x00000000   no candidate filter
               +0C 0x021F0821   activatable iff a candidate exists
               +10 0x021E51E5   the costless optional "You can" tag
               +14 0x00000000
```

`+10 = 0x021E51E5` puts them in **timing class 2** per
`timing.class_is_the_slot4_literal` — the correct class for an optional
"You can" trigger, and the one Jet Synchron's wording needs.

Their criteria rows, and the two that pin the exact fields we want:

```
row 1214 @0x02274CAC {0x2306 Synchro Fusionist, aux 0x0059, 0x0223CAF5, 0x00000004}
row 1193 @0x02274BB0 {0x22CB Vylon Cube,        aux 0xFFFF, 0x0223CAD9, 0x00000204}
row  807 @0x02273998 {0x1F54 Arcane Apprentice, aux 0x1F7A, 0x0223D075, 0x0000000E}
row 1136 @0x02274904 {0x221F Junk Blader,       aux 0x0050, 0x0223CA2D, 0x00000002}
```

Synchro Fusionist is the structural template: `aux` = a **set code**,
`handler 0x0223CAF5` = **select from DECK → add to HAND**, `word` low bits =
the card type (`0x04` = Spell for Fusionist). Junk Blader independently pins
the two fields Jet Synchron needs: **`aux 0x0050` (the Junk set code)** and
**`word 0x00000002` (Monster)**.

**None of the three exemplars is in LIST A (`0x0227134C`) or LIST B
(`0x02271314`)** — verified by dumping both — so ONE criteria row is enough and
no `criteria_row_hook` arm is needed.

#### ⇒ The trigger is carried by the cls2 record + the event, NOT by a membership list

Decisive, because Changer Synchron `0x224C` demonstrably has the
Synchro-Material trigger and `donor_scan` reports it is named by **exactly one**
structure, `cls2[555]`. And the discrimination is not in the action slots
either: Nitro Synchron `0x1E14`, Tuningware `0x1F32` and Sunny Pixie `0x2065`
are all Synchro-Material triggers with `+0C = 0` and `+10 = 0`.

**Therefore rewriting cls2[555]'s action slots preserves the trigger.**
Clause 1 is a pure table transplant:

```
cls2[555] @0x0227900C   (keep +00 = 0x224C)
  +04  0x022076A5 -> 0x02207EF5    change-position resolver -> add-to-hand resolver
  +08  0x021E0501 -> 0x00000000    drop the "monster your opponent controls" filter
  +0C  0x0224A115 -> 0x021F0821    -> activatable iff a candidate exists
  +10  0x00000000 -> 0x021E51E5    -> costless "You can" tag (timing class 2)
  +14  0x02234E01 -> 0x00000000    drop the position-change param provider

new criteria row  {0x224C, aux 0x0050, handler 0x0223CAF5, word 0x00000002}
                  = "add 1 Junk MONSTER from your Deck to your hand"
```

### The GY self-SS family (clause 2 material)

`handss.self_ss_from_gy_resolver` `0x0220731D` — enumerated the cls2 table
this session: **68 records** carry it. Disassembled `0x0220731C..0x022074F8`:

- Two distinct per-cid switches. The **first** (`0x02207332`) picks a condition
  arm; the **second** (`0x02207424`, init `movs r6,#1 ; movs r4,#2`) picks
  `r2`/`r3` of the SS commit `0x0226925C` = face-up / battle position.
- Hand-decoded the second switch completely:
  `r4=0` (Attack) for `0x1FCF 0x1CEF 0x1FDD 0x20F5`; `r4=1` (Defense) for
  `0x0E10 0x13C7 0x1E98 0x1FDF 0x2400`; `r4=1,r6=0` (face-down Defense) for
  `0x20DC 0x2209`. **Everything else — including any donor cid — takes the
  default `r4=2` (player chooses) / `r6=1` (face-up).**
- The flag half of `[sp]` is hard-zero at `0x022074E2`.

### GY-action registry `0x0228DDF8` — dumped all 60 rows

Layout `{u32 cid, u32 zone, u32 chk, u32 post}`, stride 16. Rows 15–59 are the
GY-effect family `chk 0x0224C591 / post 0x0224C6C1`. Phantom rows in that family:

```
row 15 @0x0228DEE8  cid 0x0EB2  -> CLAIMED by patch_grapha
row 47 @0x0228E0E8  cid 0x0E3E  -> CLAIMED by patch_lightpulsar
row 48 @0x0228E0F8  cid 0x0E64  -> FREE  (the last one)
```

Rows 11–13 (`0x1449 0x144C 0x1452`) are the *other* family
(`chk 0x0224C55D / post 0x0224C669`) and are not drop-in substitutes.

### Criteria registry `0x022713C4` — capacity

1388 rows, stride 12, `{u16 cid, u16 aux, u32 handler, u32 word}`. **100 rows
name a cid with no `card_prop`** (phantoms) in the stock image, so insert
capacity is not a constraint for this card.

Rows read this session:

```
row  766 @0x022737AC  {0x1EA9 Plaguespreader, aux 0xFFFF, 0x0223CB19, 0x0000000E}
row 1148 @0x02274994  {0x225B Spore,          aux 0xFFFF, 0x0223FE41, 0x68000002}
row 1155 @0x022749E8  {0x2269 Ronintoadin,    aux 0x0034, 0x0223CA2D, 0x00000002}
```

Plaguespreader's row is `aux 0xFFFF` (no set-code filter) + handler
`0x0223CB19` (select from HAND) + `0x0E` (Monster|Spell|Trap) — literally
**"any 1 card in your hand"**, which is exactly Jet Synchron clause 2's cost
target.

### Two hand→GY / hand→Deck movers are argument-compatible

Disassembled both:

```
0x021C6988(A, B, flag): ... movs r1,#0xB ; bl 0x0219CA28(r0=A, r1=0xB, r2=B)
                        ... [sp]=0x0D (DECK), [sp+4]=flag -> bl 0x021C69D0
0x021C6DB4(A, B):       adds r4,r0 ; adds r2,r1 ; movs r1,#0xB
                        ; bl 0x0219CA28(r0=A, r1=0xB, r2=B)
                        ; movs r0,#1 ; str [sp] ; str [sp,#4]   (kind 1 = COST)
                        ; movs r3,#0xE (GY) ; bl 0x021C6B00
```

**They take the same `(A, B)` in `r0, r1`**; `0x021C6DB4` ignores the third
argument. So a deck-return call site can be turned into a kind-1 **cost**
discard by retargeting the `BL` alone — no argument marshalling.

⚠️ **But a cid-scoped trampoline at Plaguespreader's call site `0x021E9120` is
impossible.** `r5` holds the descriptor on entry to `0x021E9038` and is
**reloaded at `0x021E90E6` (`ldr r5,[0x0229AAFC+0x78]`)**, so by `0x021E9120`
no register holds the cid. The `patch_gates_of_dark_world` `CAVE_GDW_MOVER`
trick (which relies on `[r5]` still being the cid at `0x021E4F66`) does **not**
transfer here.

### A generic "sent to the GY as Synchro Material" hook exists and is unclaimed

Not needed for this card (the donor carries the trigger natively), but found
and worth banking:

> **`0x02263956 : bl 0x021CF768`**, in **phase 4** of the Synchro/Xyz summon
> procedure `0x02263494` (tail-delegated to from `0x02264DC2`).
> `r0 = sp+0x74` = the 0x24-byte leave descriptor; `r1 = [sp+0xC]` = the
> **material zone bitmask**. `0x021CF768` enqueues all materials to the GY in
> one call (`dest 0x0E`, flags `0`).

`0x021CF768` has 12 BL callers, **but this call site is reachable only from the
Synchro/Xyz procedure**, so a 4-byte BL retarget there is
Synchro-Material-exclusive *by construction* — no gate required. Every material
is still in its zone at that moment; each material's cid is readable with
`0x021A36EC(side, zone)` for each set bit (`bit = zone + side*16`).
**Unclaimed** — no patch or note in the repo references `0x02263956`.

### The "Junk" search half needs no new tables

"Junk" is set code **`0x50`** (`setcode.junk_table`, VERIFIED — pointer table
`0x0209D0D8` index `0x50` → thunk `0x02023E5D`, list `0x0209C842`, 13 entries).
A criteria row `{0x224C, aux 0x0050, handler 0x0223CAF5, word 0x00000002}`
(`0x0223CAF5` = select from DECK → add to HAND; `0x0002` = Monster only) reaches
**Junk Synchron `0x1E07`, Junk Collector `0x219E`, Junk Blader `0x221F`, Junk
Forward `0x2335`, Junk Gardna `0x2355`, Junk Defender `0x23FF`**, plus the
shipped Junk Servant (`0x17CE`) and Junk Speeder (`0x24B3`). The three
Extra-Deck Junks and the two Junk Spells are excluded automatically.

**Jet Synchron does not need to JOIN the Junk list to search it** — which is
lucky, because both of that list's phantoms (`0x2500` → junk_servant,
`0x2524` → junk_speeder) are already spent.

### ✅ OPEN QUESTION 2 ANSWERED (2026-09-02, session 2) — the five cls2 slots do NOT carry the timing

The question that gated the edit was: *what makes cls2[555] a Synchro-Material
trigger, and would rewriting its action slots destroy that?* Three independent
static results, all reproducible offline:

**(a) The exemplar 5-tuple is shared across at least three different printed
timings.** Dumped all 0x2B9 cls2 records and grouped by the full
`(+04,+08,+0C,+10,+14)` tuple. **26 records** carry the exact target tuple
`(0x02207EF5, 0, 0x021F0821, 0x021E51E5, 0)`, and their printed texts are not
one timing:

```
[ 409] 0x1F54 Arcane Apprentice   "sent to the Graveyard FOR A SYNCHRO SUMMON"
[ 577] 0x22CB Vylon Cube          "sent to the Graveyard for the Synchro Summon of a LIGHT monster"
[ 596] 0x2306 Synchro Fusionist   "sent to the Graveyard AS A SYNCHRO MATERIAL Monster"
[  72] 0x139D Birdface            "DESTROYED BY BATTLE and sent to the GY"
[ 198] 0x19C5 Gokipon             "DESTROYED BY BATTLE and sent to the GY"
[ 393] 0x1ED4 Botanical Girl      "sent FROM THE FIELD to the Graveyard"
[ 540] 0x21F6 Machina Peacekeeper "on the field is DESTROYED and sent to the GY"
   ... (26 total, spanning battle-destruction, any-send, field-send and Synchro Material)
```

⇒ **the timing is not encoded in any of the five slots.** Rewriting them changes
*what the record does*, never *when it is offered*. This is a stronger statement
than the session-1 inference (which rested on Changer Synchron being named by
exactly one structure) because it is a positive exhibit, not an absence.

**(b) Neither the donor nor any exemplar has a per-cid arm in either leave
dispatcher.** Both trees are `r4 = cid` compare/branch, so a concrete cid gives
a concrete leaf. Simulated both offline
(`scratchpad/switchsim.py`; supports the `str/ldr [sp,#n]` spills that make
register-only simulators lie — `thumb.stack_based_switch`):

```
tree 1, root 0x021C8216: 0x224C, 0x1F54, 0x22CB, 0x2306, 0x139D, 0x23EE, 0x2414,
        0x1E14, 0x1F32, 0x2065, 0x1CE6, 0x1E15, 0x1EA9, 0x2250, 0x19C5
        -> ALL reach the default 0x021C93D0 (no arm)
tree 2, root 0x021C9F1C: same set -> ALL reach the default 0x021CA68A, EXCEPT
        Deep Diver 0x1CE6 -> 0x021CA4B4
```

The Deep Diver result is the **simulator's validation**: `patch_darksoul` PART A5
independently documents Deep Diver's native leaf as `0x021CA0AA beq -> handler
0x021CA4B4`, and the simulator reproduces it without being told.

**(c) None of them is in the leave-mask table `0x0226EC1C`** (dumped all 0x98
rows): 0x224C, 0x1F54, 0x22CB, 0x2306, 0x139D, 0x23EE, 0x2414, 0x1E14, 0x1F32,
0x2065 are all absent.

⇒ Changer Synchron's trigger comes from the **generic** sent-to-GY path, gated by
the record's own `+0C` condition. Nothing outside cls2[555] has to be preserved,
and nothing inside it selects the event.

**One consequence to flag, not to hide.** Because the trigger is the generic
path and not a Synchro-Material-specific arm, clause 1's real firing window may
be **wider than "as Synchro Material"** — the same over-fire the KB already
records for any-leave triggers (`leave.descriptor_slots`: the gate 0x021CA640
omits DESTROYED). Whether Jet Synchron also searches when it is discarded or
destroyed by battle is **not settled statically and is an in-game question**.
It is a fidelity deviation if it happens, not a freeze, and it is the same
window Changer Synchron ships with.

**And the `+10` edit is safe.** `timing.class_is_the_slot4_literal` (VERIFIED):
the classifier 0x0224AF7C reads +0x10 as a RAW LITERAL and never calls it;
`0` = class 0, `0x021E51E5` = class 2 (the "You can" tag). Both are
**recognised** tags, so the 0 -> 0x021E51E5 move cannot produce the
unclassified-and-silently-dropped failure that cost patch_lightpulsar a
withdraw-and-restore. Class 2 is the class the three exemplars sit in and the one
the printed "You can" wording needs.


### ✅ CLAUSE 1 IS BUILT AND IN-GAME CONFIRMED (2026-09-02) — `patch_jet_synchron.py`

**In-game confirmed by user 2026-09-02**, all six oracle items, on the FIRST test.

```
otn_enhanced/cards/jet_synchron.py   the patch (main / verify)
_build_jet_synchron.py                                   single-card ROM + in-game oracle
data/over_the_nexus/working/rom_jet_synchron.nds         129 321 096 B
    sha256 3800cd694663ca487a105a4cd9c1c13364af454bc8f5a81a1702708d29a70196
```

Build output — every assertion passed, and the patch is idempotent (re-running
`main` on its own output reports "already transplanted / already inserted" and
`verify` still passes):

```
A  cls2[555] 0x224C @0x0227900C: +04=0x02207EF5 +08=0x00000000 +0C=0x021F0821
                                 +10=0x021E51E5 +14=0x00000000
B  criteria row {0x224C, aux 0x0050, 0x0223CAF5, flags 0x0002, extra 0x0000}
   inserted at [1144], dropped phantom 0x234A at [1237]
C  card_prop 0x000E04A10000224C -> 0x000E0521000CA24C
   (DARK -> FIRE, ATK 0 -> 500; Lv1 / Machine / "Tuner Monster" unchanged)
D  name "Jet Synchron" 12 B in place in all 7 languages (tightest slot g = 13 B)
   desc 96 B in place in all 7 languages (tightest slot e = 131 B); NO Korean
   bin2.pac 10,974,720 B -> 10,974,720 B (+0 B)
verify: 12/12 PASS
```

**The phantom.** `0x234A` — no `card_prop` record, owns exactly ONE criteria row
(1237), unclaimed. It also owns a cls3 record, which is left alone and is
unreachable for a cid with no obtainable card; that is a *cleaner* phantom than
the ones azure-eyes (`0x1ABE`), eclipse-wyvern (`0x18F8`) and maiden
(`0x1BBE`) already spent, each of which is named by three structures. Registered
in `check_allocations.PHANTOM_CLAIMS` under `populate_table`, alongside a
`donor_cid` claim on `0x224C`; the ledger regenerated clean (167 ov5 slots, 143
phantom claims, no overlaps).

**What was NOT needed** — worth recording, because each was a budgeted cost that
did not have to be paid: no ov5 cave slot, no injected Thumb, no ARM9 edit (the
donor is already in the Synchron set-code list), no `criteria_row_hook` arm (one
row, index 0), no LIST A / LIST B membership, no cls2 phantom (the record is
rewritten in place). The whole card is two overlay-3 table writes, so it is
**puzzle-safe**.

**Deliberately not done:** the module is NOT in `apply_all_patches`, and no
combined build or all-patches verify sweep was run — the card is still
pre-first-test (CLAUDE.md: ship the card before the chain).

**KB contributions this session** (`author_facts --check`: 402 facts,
364 PASS / 0 FAIL / 38 UNVERIFIED):

- `dispatch.cls2_slots_do_not_encode_timing` — **VERIFIED**, closed structural
  proof (the 28-record tuple census + the leave-mask absence + both dispatcher
  root signatures).
- `card.jet_synchron_clause1` — **UNVERIFIED** with the exact in-game oracle as
  its `next_experiment`. It will not be graded higher without a duel.

Tools kept for the next session (run them **as modules** — `scratch/dis.py`
shadows the stdlib `dis`):

```
.venv-1/Scripts/python.exe -m scratch.cls2_shape_census      # the tuple census
.venv-1/Scripts/python.exe -m scratch.leave_dispatcher_sim   # both cid trees
```

### In-game oracle — ALL SIX PASSED (user, 2026-09-02, first test)

Normal duel. Deck: Jet Synchron, a non-Tuner to Synchro with, at least one
"Junk" MONSTER left in the Deck.

1. ✅ Card reads Jet Synchron, FIRE / Machine / Tuner / Lv1 / 500 / 0, clause-1 text.
2. ✅ Synchro Summon using it as Material → optional prompt → Deck search offering
   only "Junk" monsters → added to hand. **Junk Synchron seen.**
3. ✅ It no longer changes a monster's battle position.
4. ✅ **The decisive one, and it came back NEGATIVE — which is the pass.** Sent to
   the GY by other means, the search **does not activate**.
5. ✅ Tuning finds it, so it is still in the Synchron archetype.
6. ✅ With no "Junk" monster left in the Deck, the prompt does not appear.

**What item 4 buys.** Every static result in this file about the trigger is an
argument from ABSENCE — no dispatcher arm, no leave-mask row, no membership list —
so it left open that these cards ride a generic any-send-to-GY trigger and merely
*look* narrow, in which case a transplanted clause would over-fire. It does not.
The window really is Synchro-Material-specific, so whatever selects it lives
outside both the five action slots and every per-cid data structure `donor_scan`
knows — most plausibly the generic path's own leave-descriptor flag tests from
`0x021CA68A` on (cid-independent, reading `[sp+0x2C]` / `[sp+0x44]` / `[sp+0x90]`
/ `[sp+0x144]`). **Which flag is the Synchro-Material bit is still unknown, and
nobody has needed it** — a donor whose printed timing already matches carries it
for free. That is the reusable lesson: this card passed on the first duel where
Lightpulsar's comparable clause took four, and donor choice is why.


### ✅ THE BANISH RIDER IS FOUND — MEASURED, not guessed (2026-09-02, savestates)

After two falsified static hypotheses the two-strike rule said *measure*. The user
made three savestates — `rom.ml1` (Plaguespreader + Quillbolt **in the GY**),
`rom.ml2` (**both Special Summoned from the GY**), `rom.ml3` (**both banished
after being used as Synchro Material**) — and the rider fell out of the first
diff. Reproduce with:

```
.venv-1/Scripts/python.exe -m scratch.rider_pool_diff      # defaults to rom.ml1/2/3
```

All three states auto-detect RAM0 at file offset `0x24` (consistent), turn
counter 9 in all three.

**ml1 → ml2 (the summon).** Two rider nodes are created, one on each card's own
zone chain, and they are IDENTICAL apart from the turn stamp:

```
ml1: monster zones (none); NO rider node reachable from any zone chain
ml2: s0z2 = 0x1EA9 Plaguespreader, s0z3 = 0x1E15 Quillbolt
     node[1] s0z2 (holder 0x1EA9)  key=0x1E15  kind=3  dur=0  param=0x0000  stamp=1
     node[2] s0z3 (holder 0x1E15)  key=0x1E15  kind=3  dur=0  param=0x0000  stamp=2
```

**ml2 → ml3 (they leave the field).** Both nodes are freed and their pool slots
immediately recycled for the Synchro monster's own riders (node[1] key→0x1303,
node[2] key→0x2146 kind 2, plus fresh nodes 3–6). Consistent with the rider being
consumed on leave.

#### What each field means, and why this is the rider

- **`key = 0x1E15` IS A MARKER CONSTANT, NOT A REFERENCE TO QUILLBOLT.**
  Plaguespreader's node carries the same key `0x1E15`. This is exactly the
  pattern the KB already records for `battle.attacked_this_bp_marker`: key
  `0x2092` is Ancient Forest's cid used as a *marker value*, and "the compiler
  pools constants by value". Do not read `0x1E15` here as "Quillbolt".
- **`kind = 3` → family 1** (kind < 6 ⇒ walker `0x021A1430`, and the node's word
  `@+0` is compared DIRECTLY against the key). And per `rider.turn_sweeper`,
  kind 3 dispatches to `0x0219FA5C`, which frees the node **only for keys
  `0x18D9` / `0x1F6A`**. `0x1E15` is neither ⇒ **the node survives every turn
  sweep**, which is precisely what "when it leaves the field" requires.
- `dur = 0`, `param = 0`.

#### The producer — cid-keyed, so a donor does NOT get it for free

`0x1E15` occurs as an aligned u32 pool literal at exactly seven places in ov3
(`scratch/find_lit_loaders.py` resolves each to its loader):

```
0x0219F504 <- 0x0219F4C8   node-retention chain (keys 0x1E15/0x1F70/0x20C8 skip the free call)
0x021B0A38 <- 0x021B09CC   ⇒ THE CONSUMER: `ldr r2,=0x1E15 ; bl 0x021A1430(side, slot, key)`
0x02207504 <- 0x02207368   the GY self-SS resolver's per-cid switch (Quillbolt -> 0x022073D6)
0x022683B0 <- 0x02268238   ⇒ THE PRODUCER's per-cid switch, in the summon path
0x022686B4 <- 0x0226854A, 0x022685AE
0x02277DAC                 data: cls2[359] +00, Quillbolt's own record
0x0228DF78                 data: a GY-action registry row
```

The attach itself is the **queued rider writer** — `0x0226857E: movs r3,#3 ;
bl 0x021C479C`, i.e. `0x021C479C(r0 = side, r1 = slot, r2 = key, r3 = kind byte,
[sp+0] = param)` with **kind 3**, matching the measured node exactly. Its arm is
selected by the per-cid compare chain at `0x02268238`, so **it is cid-keyed**:
Jet Synchron's donor `0x224C` will not receive it by data alone.

#### ⇒ The recipe for clause 2's rider

**Do not hook the engine's per-cid switch. Attach the node ourselves**, with the
same call the engine makes, at the moment the card is Special Summoned:

```
0x021C479C(side, slot, key = 0x1E15, kind = 3, param = 0)
```

Everything downstream — persistence across turns (kind 3 is never swept for this
key) and the banish itself (the consumer at `0x021B09CC` queries this exact key
through the family-1 walker, cid-blind) — then comes for free.

⚠️ STILL UNPROVEN: that `0x021B09CC` is the *whole* consumer story, i.e. that the
node alone produces the banish for an arbitrary cid. The chain it heads was read
statically, not executed. The cheap confirmation is in-game: attach the node and
watch the card banish itself on leaving. Do not write this up as proven before
that duel.


### CLAUSE 2 — ARCHITECTURE A, worked up (2026-09-02). NOT BUILT.

**Lightpulsar is the precedent, and it is a closer match than Grapha.** Its
clause 2 (a cost-bearing SS) and clause 3 (a sent-to-GY trigger) already SHARE
ONE cls2 record, split by ov5 dispatchers — the identical conflict Jet Synchron
has, in the identical slots, shipped and in-game confirmed:

```
slot            LP clause 2 (cost)        LP clause 3 (trigger)     via
+04 resolver    0x0220731D                0x02207191                CAVE_LP_RESDISP
+08             0                         0                         (unchanged)
+0C condition   hand LIGHT/DARK scan      0x021F03B5                CAVE_LP_C2COND2
+10 cost/tag    the cost machine          0x021E51E5 ("You can")    CAVE_LP_C2COST
+14 target      `movs r0,#1 ; bx lr`      0x02235605                CAVE_LP_TGTDISP
```

Slot ABI, confirmed by disassembly in that patch: **every slot wrapper calls with
`r0` = the DESCRIPTOR and `r1` = the invoker's arg**; `r2`/`r3` are free scratch.
And `+10` doubles as the timing tag, read RAW by the classifier — which is why
LP needs **PART T**, a 0x40 B stub displacing `ldr r0,[r0,#0x10] ; cmp r0,#0` at
`0x0224AF96` so the classifier sees a recognised value for that cid only.

Jet Synchron maps onto it with the roles swapped:
`clause 1` (sent-to-GY trigger, needs the `0x021E51E5` tag) = LP's clause 3;
`clause 2` (ignition + hand-send cost) = LP's clause 2.

#### ⚠️ THE ONE THING THAT DOES NOT TRANSFER — and it is the discriminator

LP splits on **`desc[+3] == 0x0E` AND `desc[+4] > 6`**. The zone half is useless
here: LP's clause 2 is a **hand**-SS so its zone is not `0x0E`, but **Jet
Synchron's clause 2 is a GY ignition and `0x0224C590` hardcodes `desc[+3] =
0x0E`** — so BOTH of our clauses arrive with zone `0x0E`. Only `desc[+4]` is
left.

**Where `desc[+4]` comes from, read out of `0x0224C590`:** `desc[+4] =
eventcode[r5]`, an array of bytes at **`0x0229ABB4`** indexed by the pending-event
index `r5 = [0x0229AB7C+0x30] - 1`, or **index 0 when that count is 0**
(`bne` skipped ⇒ `movs r5,#1 ; subs r5,r5,#1`).

**Measured from the savestate triple** (free, no GDB):

```
ml1 (both in GY)                 count 0   eventcode[0..1] = 0x00, 0x00
ml2 (both SS'd from GY)          count 0   eventcode[0..1] = 0x09, 0x00
ml3 (banished after Synchro)     count 0   eventcode[0..1] = 0x09, 0x1D
```

`0x09` = Special Summon (`summon.trigger_is_a_membership_list`: codes 7/8/9 =
Normal/Flip/Special) and `0x1D` is the non-battle leave code LP names explicitly.
Two independent corroborations of the event-code semantics.

**⇒ LP's `> 6` test is UNSAFE for this card.** The array is **not cleared** —
`eventcode[0]` still read `0x09` in ml2 and ml3, long after the summon. A GY
ignition performed while a stale `0x09` sits at index 0 would satisfy `> 6` and
be **misrouted into clause 1's arm**. That is a silent wrong-clause bug, exactly
the class of failure the two-strike rule exists for.

**The fix is to raise the threshold, not to reuse LP's constant:** the leave codes
are `0x17` / `0x1D` / `0x1E` and the summon codes are `<= 9`, so

```
clause 1 iff desc[+4] >= 0x17      (leave family)
clause 2 otherwise                 (ignition; stale summon codes 0x00/0x07..0x09 land here)
```

separates them with a wide margin. **This is the single item still unproven** —
see Next experiment.


### ✅ OPEN QUESTION 4 CLOSED STATICALLY (2026-09-03) — the rider node IS cid-blind, and it rewrites the destination zone

Session 2026-09-02 left this as "the consumer chain at `0x021B09CC` was read
statically, never executed". It has now been read **to its end**, and the end is
a destination-zone rewrite that never looks at a cid. Reproduce with
`.venv-1/Scripts/python.exe -m scratch.dis <addr> <len>`.

**The predicate is `0x021B0950(r0 = side, r1 = slot)` → 1 = banish, 0 = GY.**
Its full body, disassembled `0x021B0950..0x021B0A1C`:

```
0x021B0950  push {r4,r5,r6,lr} ; r5 = side (r0), r4 = slot (r1)
0x021B0952  ldr r2,=0x20DC ; bl 0x021A1430   -> rider key 0x20DC  ? return 1
0x021B0964  r2 = slot*0x14 ; r6 = side&1 ; r3 = r6*0xB3C
0x021B097A  ldrh [0x0229ACD0 + r3 + r2] == 0            -> return 0
0x021B0984  ldr  [0x0229ACD8 + r3 + r2] >> 0x15 & 1     -> return 0
0x021B0994  cid = [0x0229AC94 + r3 + 0x34 + r2] & 0x3FFF
            cid == 0x16F8 || cid == 0x1CE0 -> two extra flag/0x021AEA7C tests
0x021B09CC  ldr r2,=0x1E15 ; bl 0x021A1430(side, slot, key)  -> return 1
0x021B09DE  ldr r2,=0x1F5B ; bl 0x021A1430                   -> return 1
0x021B09F2  r6 += 0x15 (=0x1F70) ; bl 0x021A1430             -> return 1
0x021B0A06  ldr r2,=0x2184 ; bl 0x021A1430                   -> return 1
0x021B0A18  movs r0,#0 ; pop                                  (no rider -> GY)
```

**The four rider keys `0x20DC / 0x1E15 / 0x1F5B / 0x1F70 / 0x2184` are tested
with NO cid compare in scope.** The only two cid compares in the function
(`0x16F8`, `0x1CE0`) are *early-exit* arms that fall THROUGH to the same rider
tests when they don't match. So a card of any cid carrying the `0x1E15` node
reaches `0x021B09CC` and the walker answers 1.

**And the caller turns that 1 into the banish.** `find_bl_callers 0x021B0950` →
six sites (`0x021B0AFA 0x021CCBDA 0x021CF4B8 0x0222E4A0 0x0222E7DA 0x022621C6`,
none in arm9). The decisive one is `0x021CCBDA`:

```
0x021CCBD2  cmp  r4, #0xa          r4 = the DESTINATION ZONE
0x021CCBD4  ble  0x021CCC14        (only when the card is actually leaving)
0x021CCBD6  adds r0,r5,#0 ; adds r1,r6,#0
0x021CCBDA  bl   0x021B0950
0x021CCBDE  cmp  r0,#0
0x021CCBE2  movs r4,#0xf           <-- destination 0x0E (GY) becomes 0x0F (BANISHED)
```

`0x0E` = GY / `0x0F` = banished is the same encoding `patch_nast` measured for
the destroy-vs-banish switch at `0x021CB490`. The second site `0x021CF4B8` does
the corroborating thing (`if (pred) { r4 = 0; r6 = 0; }` — it suppresses the
GY-send bookkeeping).

⇒ **`0x021C479C(side, slot, key = 0x1E15, kind = 3, param = 0)` is sufficient.**
No cid gate stands between the node and the banish. This is now a closed
structural chain, not a hypothesis — but it is still **not in-game confirmed**,
and the duel remains the arbiter.

**The producer's argument shapes, for cloning.** Decoded `0x021C479C` fully:

```
0x021C479C(r0, r1, r2, r3, [sp+0]):
    r4  = r0 ? 0x8000 : 0            <- r0 is the SIDE, folded into a flag bit
    r0  = 0x35 | r4                  <- the node opcode
    r1  = ((r3 & 0xFF) << 8) | (r1 & 0xFF)     <- (kind << 8) | slot
    r3  = ldrh [sp+8]                <- the 5th arg, a HALFWORD param
    bl  0x021C3BC8(r0, r1, r2 = key, r3 = param)
```

Two native call sites give the (side, slot) pair verbatim:

```
0x0226857A (the Quillbolt/Plaguespreader producer, cid-keyed arm; gated by
            [[r5,#0x50],#5] == 1)
    r0 = ldrh [r4,#2]    side
    r1 = ldrh [r4,#4]    slot
    r3 = 3               kind
    [sp] = 0             param
0x021E91C2 (an unrelated kind-2 attacher, key 0x16C9)
    r0 = ldrb [r5,#2]    side   <- r5 is a DESCRIPTOR: +2 = side
    r1 = ldrb [r5,#3]    slot
```

and the consumer indexes the per-player card array with exactly that pair
(`slot*0x14 + (side&1)*0xB3C` into `0x0229ACD0` / `0x0229AC94+0x34`), so
**"slot" is the zone index within the side, not a packed reference.**

### ✅ OPEN QUESTION 6, PART 1 (2026-09-03) — the cost machine is sized, and its ONLY cid gate is harmless

`0x021E9038` (Plaguespreader's `+10`) disassembled end to end.

- **Extent: `0x021E9038 .. 0x021E918C` = 0x154 B of code**, followed by its
  literal pool `0x021E918C .. 0x021E91B8` (0x2C B, 11 words). A clone costs
  **0x180 B** of ov5. The next function starts at `0x021E91B8`.
- **Shape: a 3-phase machine** driven by the phase counter `[0x0229AAFC+0x7C]`,
  the same chassis `patch_nast` documented (`0x02206CD2`), returning 0 to mean
  "call me again next phase" and 1 to mean "done":

```
entry   r5 = r0 = DESCRIPTOR, r7 = r1 = the invoker's arg   (matches the slot ABI)
        defaults r4 = 1, [sp] = 0, [sp+4] = 1
        --- per-cid switch on ldrh [r5] ---
0x021E909C  bl 0x021D2BC8(desc)     ; already-paid / short-circuit -> return 1
phase 0     0x0219A818(side, 0x1F)                      ; open the prompt
            0x0224B9F0(side, 0x13, 0, 0x022065F9)       ; arm the hand picker
            phase++ ; return 0
phase 1     bl 0x0224BBB0            ; 0 => cancelled: phase-- , return 0
            r5 = [0x0229DD94+0x78]   ; NOTE: r5 is REBOUND to the SIDE here
            r7 = [0x0229DE14]        ; the chosen card index
            if ([sp]) 0x021D2598(side, r4+r6)
    +0xE8   bl 0x021C6988(side, idx, [sp+4])   <-- THE HAND->DECK MOVER
            0x021A14B4(side, 0xB, 0x1379, r4+r6) -> 0x021CF8D0 / 0x021CFB8C
            phase++ ; return 0
phase 2     if (r4) bl 0x021D26CC
            0x021D29E8(side, 2, 0)
            if (cid == 0x24A7) 0x021E5060(desc, r7)
            return 1
default     return 0
```

- **The cid switch and what it actually selects.** Hand-decoded
  `0x021E9044..0x021E909C`. It compares `ldrh [r5]` against `0x1F6F`, `0x16C1`,
  `0x1EA9` (encoded **ungreppably** as `0x1F6F - 0xC6` — the
  `thumb.stack_based_switch` / base±imm pattern again), `0x2078`, `0x2079`,
  `0x24A7`, and sets only three values:

```
cid            r4   [sp]  [sp+4]
0x1F6F          1     1      1
0x16C1          0     0      1     (via 0x021E9084: r4=0, [sp+4]=0, [sp]=1)
0x1EA9 Plague   0     0      1
0x2078 / 0x2079 0     1      1
0x24A7          0     0      0
DEFAULT         1     0      1     <-- what donor cid 0x224C gets
```

  `[sp]` gates an extra `0x021D2598` call; `[sp+4]` is the third argument of the
  mover; `r4` gates `0x021D26CC` in phase 2. **Plaguespreader's arm differs from
  the default in `r4` alone** (0 vs 1), and `0x021D26CC` is a
  turn/phase-bookkeeping routine over `0x0229DD14` — not a cost. So the default
  arm is *usable as-is*, and a clone that wants Plaguespreader's exact behaviour
  needs one two-byte change (`movs r4,#1` -> `movs r4,#0` at `0x021E904A`).

- **Cloned-pool POINTER footgun: CHECKED, and the function is CLEAN.** Its 11
  pool words are `0x00001F6F 0x000016C1 0x00002079 0x000024A7 0x0229AAFC
  0x022065F9 0x0229DD94 0x0229AC94 0x0229DE14 0x00000B3C 0x00001379`. Four are
  small immediates, one is a Thumb function pointer passed as an argument, and
  the four RAM addresses (`0x0229AAFC 0x0229DD94 0x0229AC94 0x0229DE14`) are
  **loaded as values and then dereferenced with `ldr [rX,#imm]`** — i.e. the pool
  word IS the address the code wants, which is the safe case. There is **no
  `ldr rD,[pc,#imm]` whose target is a table the clone would have to relocate**,
  so `thumb.cloned-pool-pointer-footgun` does not bite here. A verbatim copy with
  the pool re-emitted at the clone's own PC-relative offsets is correct.

- **The one edit the clone needs:** the `BL` at `0x021E9120` (clone offset
  `+0xE8`) retargeted from `0x021C6988` (hand -> **DECK**, `[sp]=0x0D`) to
  `0x021C6DB4` (hand -> **GY**, kind 1 = COST, `r3=0x0E`). Both take `(side,
  idx)` in `r0,r1` and `0x021C6DB4` ignores the third argument, so no argument
  marshalling is required — confirmed by the 2026-09-02 disassembly of both.

### ✅ OPEN QUESTION 5 CLOSED (2026-09-03) — and the handoff's warning about it was WRONG in the direction that mattered

The 2026-09-02 handoff said Lightpulsar's `desc[+4] > 6` split "does NOT transfer"
and is "actively unsafe", on the reasoning that (a) LP's clause 2 is a *hand*-SS
so its zone is not `0x0E` whereas both of ours are, and (b) the event-code array
is never cleared, so a stale `0x09` sitting at index 0 during a GY ignition would
satisfy `> 6` and misroute clause 2 into clause 1's arm. **Both halves are
false, and the second one is impossible by construction.**

**(a) LP's clause 2 IS a GY self-SS with zone `0x0E`, exactly like ours.** Read
`patch_lightpulsar.py:1436-1485` — the header block over `C3_EVENT_MIN`:

> *"The two descriptors share the cid AND the zone (0x0E), so the zone cannot
> separate them -- only the event code can."*

and its measured table, from the savestates that shipped the card:

```
rom_eclipse_wyvern.ml2  cid 0x1859 zone 0x0E event 0x1E cls 2   sent-to-GY
rom_lightpulsar.ml3/4/5 cid 0x1303 zone 0x0E event 0x00 cls 2   CLAUSE 2
```

`criteria_row_hook.ARM_LP` tests `desc[+3] == 0x0E` and then splits on
`desc[+4] > 6` for the same pair. So Jet Synchron's conflict is **structurally
identical** to Lightpulsar's, not different from it, and the precedent is
in-game confirmed.

**(b) A stale event code can NEVER misroute clause 2 into clause 1's arm,
because with a stale code above 6 the GY action is not offered at all.**
Disassembled the off-field offer gate this session:

```
0x021ECC6C (the off-field branch's gate, reached with r1 = 0, no pending event)
    0x021ECCD0  bl 0x021A87BC(desc) ; cmp r0,#2 ; bge PASS
    0x021ECCD8  cid in {0x131E, 0x14D7, 0x154C, 0x1E08, 0x2272}     -> PASS
    0x021ECD06  bl 0x021ECC28(desc) ; bne PASS
    0x021ECD20  movs r0,#0 ; pop                                     REFUSE

0x021ECC28(desc)
    own turn ([0x0229DD14+0x34] == desc[+2] ^ desc[+6])   else 0
    phase [0x0229DD14+0x48] in {2, 4}                     else 0
    0x021ECC42  ldrb r1,[r0,#4] ; cmp r1,#6 ; bhi ->      r1 <= 6  => RETURN 1
    0x021ECC4C  ldrb r0,[r0,#3] ; cmp r0,#4 ; bhi -> 0    zone > 4 => RETURN 0
                (the {7,8,9} arm below is reachable only for zone <= 4)
```

The GY-action builder `0x0224C590` **hardcodes `desc[+3] = 0x0E`**
(`movs r1,#0xe ; strb r1,[r0,#3]` @0x0224C5E8), so the `desc[+3] <= 4` arm is
dead on this path and the gate reduces to **`desc[+4] <= 6` or refuse**.

The two escape hatches are both closed for our donor, checked this session:

- **The whitelist** `{0x131E, 0x14D7, 0x154C, 0x1E08, 0x2272}` does not contain
  `0x224C`.
- **`0x021A87BC(desc) >= 2`** is the card's *speed*. Its default leaf
  `0x021A894C` tail-calls the arm9 speed lookup `0x0202345C`, which for a
  MONSTER returns 2 only if the cid is in the quick-effect list `0x0209C118`
  (118 sorted u16, `bl 0x02022E14`, count immediate `movs r2,#0x76`). Dumped the
  list: **`0x224C` is not in it** (nor is LP's `0x0FB1`), so the lookup returns 1
  and the gate falls through to `0x021ECC28`.

⇒ **Clause 2 offered ⇒ `desc[+4] <= 6`.** PROVEN, structurally. The stale-`0x09`
scenario does not misroute the card; it merely makes the GY effect unavailable
that moment, which is the behaviour Grapha and Lightpulsar already ship.

**And clause 1's side is closed too, by the producers.** A class-2 descriptor
with zone `0x0E` reaching `cls2[555]` today can only come from the leave /
relocation path — `0x224C` is not yet in the GY-action registry, so
`0x0224C590` never runs for it — and that path has exactly two code sources:

```
0x021C809C (the leave dispatcher, the function that also hosts hook 0x021C8216)
    ldr r0,[sp,#0x44] ; cmp r0,#0        [sp+0x44] = DESTROYED BY BATTLE
    bne -> movs r0,#0x17                 battle    -> 0x17
    beq -> movs r0,#0x1d                 otherwise -> 0x1D
    str r0,[sp,#0x1c]                    every native arm ORs [sp+0x1C] << 0x19
0x021D1300  the relocation applier       -> 0x1E
```

and the Synchro-Material send lands in that dispatcher: phase 4 of the
Synchro/Xyz procedure calls `0x02263956: bl 0x021CF768`, and `0x021CF768` is a
6-instruction thunk — `ldrh r4,[r5] ; strh #0,[r5] ; movs r2,#0xE ;
bl 0x021CDD4C ; strh r4,[r5]` — into the shared relocation applier with
destination `0x0E`. Independently, `card.shooting_quasar`'s leave-hook
trampoline **at `0x021C8216`, in this same function, is in-game confirmed to see
Synchro-Material uses**.

⇒ clause 1 arrives with `desc[+4]` ∈ {`0x17`, `0x1D`, `0x1E`}, all > 6.

**⇒ THE DISCRIMINATOR IS LIGHTPULSAR'S, VERBATIM:**

```
clause 1 (the Synchro-Material trigger)  iff  desc[+3] == 0x0E && desc[+4] > 6
clause 2 (the GY ignition)               otherwise
```

The handoff's proposed `desc[+4] >= 0x17` would also work, but `> 6` is the
in-game-confirmed constant and it is the one the shared
`criteria_row_hook.ARM_LP` already uses, so the card stays consistent with the
precedent it is cloned from. **The user's savestate (STEP 1) is now a
CONFIRMATION, not a gate** — the expected reading is `0x1D`.

### ✅ OPEN QUESTION 6, PART 2 (2026-09-03) — clause 2's cost needs a SECOND criteria row, and the shared hook already ships the arm for it

Sizing the cost machine turned up a hazard the handoff did not list. Traced the
prompt it arms:

```
0x021E90C4  0x0224B9F0(side, 0x13, param = 0, callback = 0x022065F9)
              -> [0x0229DD94+0x4C] = 8      selection mode
                 [0x0229DD94+0x50] = param
                 [0x0229DE14+0x0C] = the candidate-filter CALLBACK
0x022065F8  the callback: rejects unless arg0 == the acting side and arg1 == 0x0B
            (the HAND), then r1 = ldrh [[0x0229A9FC+0x50]] -- THE ACTING CARD'S
            CID -- and tail-calls 0x02243FE0(side, cid, candidate_index)
```

`0x02243FE0` is the criteria evaluator (`dispatch.criteria_registry_lookup_
default`), so **the hand picker is filtered by a criteria row keyed on OUR cid**
— and clause 1 has already installed `{0x224C, aux 0x0050, 0x0223CAF5 (select
from DECK), 0x0002}` as that cid's rel-0 row. Left alone, clause 2's hand prompt
would be filtered by clause 1's *Deck* row: the wrong zone and the wrong handler.

**This is exactly `card.upstart_golden_ninja`'s problem, and its solution ports
one-for-one.** That card's cost filters the HAND while its effect searches the
DECK, both consumers pass param 0, and the fix is an arm on the SHARED
`criteria_row_hook` keyed on the cost machine's own state word:

```
counter.cost_machine_state_is_the_row_discriminator (VERIFIED, measured in-game)
    [0x0229AAFC + 0x7C] is non-zero exactly while the record-driven cost runs,
    and 0 at the menu and at resolution; the reset is proven, not assumed --
    0x02217FB6 `movs r1,#0` / 0x02217FBA `str r1,[r4,#0x7c]`.
```

and **`0x0229AAFC+0x7C` is the very phase counter the cost machine we are cloning
runs on** (`0x021E90AA: ldr r6,=0x0229AAFC ; ldr r0,[r6,#0x7c]`), which it
increments to 1 at the end of phase 0 — i.e. it is non-zero for exactly the
window in which the picker asks the callback to filter. So the arm is:

```
Jet Synchron:  [0x0229AAFC+0x7C] != 0  (or the hand-scan probe flag set)
                   -> rel 1  the HAND row
               else
                   -> rel 0  the DECK row (clause 1, unchanged)
```

Two consequences that are load-bearing:

1. **ROW ORDER IS FIXED: the DECK row must stay at rel 0.**
   `dispatch.offer_check_probes_rel0_only` — the offer-check probes rel 0 only,
   and on a HAND row `0x02243FE0`'s param is a candidate INDEX rather than a row
   selector, so a hand row at rel 0 would only ever test hand slot 0. Clause 1's
   row is already rel 0, which is the correct order; the new hand row is
   inserted **immediately after it** (`after_same_cid`, per
   `card.ninja_grandmaster_hanzo_clause2`'s "a sorted insert that places a new
   record BEFORE existing equal keys silently SWAPS the two clauses and still
   passes a 'both rows present' check").
2. **Clause 2's own offer condition must scan the whole hand itself**, with the
   probe flag raised — Upstart's TEST 3 failure was exactly this: the stock
   condition only probes rel 0, so with nothing legal in hand the effect was
   still offered and the picker opened empty and inescapable. That is oracle
   item 6 ("activate clause 2 with an empty hand -> not offered") and it is a
   **soft-lock**, not a fizzle, if skipped.

**⚠️ COST: this makes Jet Synchron DUEL-ONLY.** `criteria_row_hook`'s stub is in
the ov5 cave and sits inside `0x02243B9C`, the row resolver every selecting card
passes through, so a puzzle (which evicts ov5) crashes on the first selection by
ANY card. Clause 1 alone is pure ov3 and puzzle-safe; adding clause 2 gives that
up. Lightpulsar, Darkflare and Upstart Golden Ninja already carry the same trade
by explicit user decision (2026-08-14). **The user must be told before the
build.**

The hand row itself is already specified by an existing exemplar — Plaguespreader
Zombie's own row, read 2026-09-02:

```
row 766 @0x022737AC  {0x1EA9, aux 0xFFFF, 0x0223CB19, 0x0000000E}
                      = "any 1 card in your hand" -- no archetype filter,
                        select-from-HAND handler, Monster|Spell|Trap
```

which is literally clause 2's printed cost ("send 1 card from your hand to the
GY"). The new row is that, with the cid changed to `0x224C`.

### 🚫 BLOCKER FOUND (2026-09-03) — PART T's hook site is ALREADY OWNED by patch_lightpulsar

The handoff described PART T as "a ~0x40 B stub displacing `ldr r0,[r0,#0x10] ;
cmp r0,#0` at `0x0224AF96`" as though the site were free. **It is not.**

```
patch_lightpulsar.py:1792   TIMING_SITE     = 0x0224AF96   # `ldr r0,[r0,#0x10] ; cmp r0,#0`
patch_lightpulsar.py:1793   TIMING_NATIVE   = bytes.fromhex("00690028")
patch_lightpulsar.py:1795   TIMING_RESERVE  = 0x40
patch_lightpulsar.py:528    def _stub_timing(base) -> ...  # installed over those 4 bytes
```

That is **four bytes**, replaced by one BL — so, exactly like `ROWHOOK_SITE`, a
stub owned by one card module can only ever serve one card. This is the same
situation that produced `criteria_row_hook.py`, and that module's own docstring
states the rule:

> *"AND THERE IS EXACTLY ONE 4-BYTE BL AT THAT SITE. A stub owned by one card
> module can therefore only ever serve one card. Lightpulsar shipped one;
> Darkflare needed a second arm; re-pointing the hook would have broken
> Lightpulsar's clauses 2 AND 3, both in-game confirmed."*

**Jet Synchron cannot avoid needing it.** `+10` is one slot shared by both
clauses; clause 2 must put a real cost function there, which is not one of the
literals the classifier `0x0224AF7C` recognises, so clause 1 falls into **no
timing class at all** and its trigger evaporates. That is precisely oracle item
3's failure mode ("missed the timing", or silence).

**THE FIX, and it is the established repo pattern, not a new idea:** lift
`patch_lightpulsar`'s PART T into a shared `timing_class_hook.py` carrying an
`ARMS` register — structurally a copy of `criteria_row_hook.py`, which was itself
created by lifting Lightpulsar's row hook when Darkflare needed a second arm —
and register both `0x0FB1` (Lightpulsar's existing arm, byte-for-byte) and
`0x224C`. `patch_lightpulsar` then delegates, as it already does for the row
hook and for `handss_banish_cost`.

⚠️ **This edits a SHIPPED, in-game-confirmed card.** It is mechanical (the arm
body is moved verbatim; only its host changes) and both `patch_lightpulsar.verify`
and `_verify_all_patches` cover it, but it is still a change to Lightpulsar and
the user should decide whether it happens now or at shipping time. Note the
sequencing subtlety: in a SINGLE-CARD `rom_jet_synchron.nds` Lightpulsar is not
applied at all, so the site is free and Jet Synchron could install its own stub
and be tested in-game without touching LP — but the collision then becomes a hard
blocker the moment the card is wired into `apply_all_patches`, and the shared
lift would change the tested bytes.

### ⚠️ CLAUSE 2 COSTS JET SYNCHRON ITS PUZZLE SAFETY — the user must accept this before the build

Clause 1 is two overlay-3 table writes and uses no cave at all, so the shipped
card is puzzle-safe. Clause 2 needs, at minimum, an arm on `criteria_row_hook`,
whose stub lives in the **ov5 cave** and sits inside `0x02243B9C` — the row
resolver every card that selects anything passes through. A puzzle loads overlay
41 over ov5 (`mem.ov5_ov41_share_base`), so in a puzzle that hook branches into
ov41's data: **the first selection by ANY card crashes**, not merely Jet
Synchron. Lightpulsar, Darkflare and Upstart Golden Ninja already carry exactly
this trade by explicit user decision (2026-08-14).

### Budget, quoted live (2026-09-03)

```
ov5_cave.py:1210   CAVE_FREE = 0x0239E340
computed tail      OV5_RAM_BASE + OV5_NEW_LEN - CAVE_FREE = 0x023AA120 - 0x0239E340
                 = 0xBDE0 = 48608 bytes free
check_allocations  167 ov5 slots (152 live), 143 phantom claims, 11 ov3 dead-code
                   claims (54 B free) -- [OK] no overlaps, ledger in sync
criteria_row_hook  stub is 152 B against RESERVE 0x100 -> 104 B headroom for a
                   fourth arm (Jet's arm is ~24 B plus a ~10 B cid preamble)
```

Estimated clause-2 ov5 spend: cost-machine clone 0x180 + four slot dispatchers
~0x80 + hand-scan condition ~0x60 + rider attach ~0x40 + the shared timing stub
~0x60 ≈ **0x360 B**, comfortably inside the tail.

### ✅ THE SHARED TIMING HOOK IS BUILT (2026-09-03) — and the Lightpulsar lift is MEASURED, not argued

User approved both decisions 2026-09-03: lift PART T into a shared module now,
and accept that clause 2 makes the card duel-only.

**New module `otn_enhanced/effects/timing_class_hook.py`** — a
structural copy of `criteria_row_hook.py`, owning the single 4-byte site
`0x0224AF96` inside the WHEN-vs-IF classifier `0x0224AF7C`, with an `ARMS`
register:

```
0x0FB1  Lightpulsar   zone 0x0E, event > 6 -> tag 0            (class 0)  MOVED VERBATIM
0x224C  Jet Synchron  zone 0x0E, event > 6 -> tag 0x021E51E5   (class 2)  NEW
```

The register contract was re-read from the image rather than inherited:
`0x0224AF7E adds r4,r0,#0` (r4 = the DESCRIPTOR), `0x0224AF8E bl 0x0224A118`
(r0 = the RECORD), `0x0224AF96 ldr r0,[r0,#0x10]`, `0x0224AF9A bne` = 0xD101,
and the class-2 comparand at `0x0224B02C` = `0x021E51E5`. Also confirmed
`0x0224AF80: ldrb r1,[r4,#5] ; r1 in {0,3} -> return 0`, so cls0/cls3 records
never reach the site — our cls2 record does.

**Why Jet Synchron substitutes a DIFFERENT literal from Lightpulsar, on purpose.**
LP wanted class 0. Jet Synchron's clause 1 SHIPPED with `+10 == 0x021E51E5`
(class 2) and is in-game confirmed with it, so the arm restores exactly that
literal — the minimum change from a known-good state. In clause 2's window
(event <= 6) the arm leaves the raw value alone, which is what LP already ships
and duels on.

**Cave.** `CAVE_LP_TIMING 0x0239C568` RETIRED (its 0x40 reserve holds one arm;
`CAVE_ROWHOOK` sits at exactly +0x40). New `CAVE_TIMINGHOOK = 0x0239E340`,
0x100 reserve, stub is **68 B**. `CAVE_FREE` bumped `0x0239E340 -> 0x0239E440`;
free tail now `0xBCE0`. Ledger re-emitted:

```
allocation check: 168 ov5 slots (152 live), 143 phantom claims, 11 ov3 dead-code
                  claims (54 B free)
  [OK] no ov5 overlaps, no phantom double-claims, no ov3 overlaps, ledger in sync
```

**THE LIFT IS PROVEN BEHAVIOUR-PRESERVING BY EXECUTION.**
`scratch/timing_hook_equiv.py` (new, kept) assembles the **committed pre-lift
stub** from `patch_lightpulsar@736a0b3` and the **current shared stub**, and runs
BOTH through `scratch/thumbemu` over 30 600 input combinations of
(cid x desc[+3] x desc[+4] x raw tag), comparing the returned `r0` **and the Z
flag** the classifier's own `bne` consumes:

```
executed 30600 inputs through BOTH emitted blobs
  pre-lift 32 B @0x0239C568  ->  shared 68 B @0x0239E340 (2 arms)
  cids whose (r0, Z) differ: {'0x224c': 108}
  [OK] every shipped arm ('0xfb1',) is unchanged; only ('0x224c',) differs
```

Zero differences on `0x0FB1`, and the only cid that changed is the one the arm
was added for. `patch_lightpulsar` rebuilds and its own `verify()` passes,
including the delegated timing checks. ⚠️ A byte diff against the old
`rom_lightpulsar.nds` (2026-08-18) is meaningless — ov5 `RESERVE` was raised to
64 KB on 2026-09-02, so the file sizes differ; the execution equivalence is the
real check. Re-run `-m scratch.timing_hook_equiv` after adding any third arm.


### ✅ THE RIDER'S ATTACH POINT IS PINNED (2026-09-03) — and the simulator reproduces the savestate result

`rider.banish_when_it_leaves_marker` named the producer as "the per-cid compare
chain at `0x02268238`" but never located its root, its input, or the arm. All
three are now nailed, with `scratch/summon_event_sim.py` (new, kept).

**The host function is `0x02267A6C`**, the summon-event handler. Its `r4` is the
**GLOBAL event record `0x02298A28`** (not an argument), and it dispatches on
`[r4+0x24]`, the event opcode, through a jump table at `0x02267AA4`. The rider
lives under **opcode `0x14`** (`0x02267AAC: cmp r0,#0x14 ; bne ; b 0x02268028`).

**The per-cid switch's root is `0x022680A8`, and the cid is `ldrh r2,[r4,#0x12]`.**
Its default leaf is **`0x02268666`**, the fall-through immediately after the
shared attach:

```
0x02268660  movs r3,#3
0x02268662  bl   0x021C479C          ; (side, slot, key, kind, [sp] = param)
0x02268666  ldrh r0,[r4,#0xe]        ; <- THE DEFAULT LEAF
```

**The arm that grants the banish rider is `0x02268542`, and it is ungated:**

```
0x02268542  movs r0,#0 ; str r0,[sp]      param = 0
0x02268546  ldrh r0,[r4,#0x2]             side
0x02268548  ldrh r1,[r4,#0x4]             slot
0x0226854A  ldr  r2,=0x1E15               THE MARKER KEY, as an explicit literal
0x0226854C  b    0x0226846E -> 0x02268660 -> kind 3, attach
```

**The simulator's result, and why it is trustworthy:**

```
root 0x022680AA   default leaf 0x02268666   cid in r2
  0x1EA9 Plaguespreader Zombie   arm body @0x02268546
  0x1E15 Quillbolt Hedgehog      arm body @0x02268546
  0x224C Changer Synchron        arm body @0x02268666  <-- DEFAULT
  0x0FB1 Sword Arm of Dragon     arm body @0x02268666  <-- DEFAULT
  0x1463 The Portrait's Secret   arm body @0x02268666  <-- DEFAULT
  0x1F18 Ally Mind               arm body @0x02268666  <-- DEFAULT
  0x19CB Treeborn Frog           arm body @0x02268666  <-- DEFAULT
```

**BOTH cards that print "banish it when it leaves the field" land on the SAME
arm, and that arm supplies key `0x1E15` — which is exactly the node the
2026-09-02 savestate diff measured on both of them.** The simulator was not told
that; it is the independent corroboration, the same role Deep Diver played for
`scratch/leave_dispatcher_sim`. **Treeborn Frog is the negative control**: a GY
self-Special-Summon that prints NO rider, and it defaults.

⇒ **Our donor `0x224C` defaults**, so the rider must be supplied by a hook.

**Two data-only routes checked and RULED OUT.** The opcode-0x14 prologue runs two
membership lists before the switch, and both attach a node whose **key is the
card's own cid**, not a marker:

```
0x02268070  list 0x0228F750 x0x2E -> 0x021C479C(side, slot, cid, kind 3, 0)
0x0226808C  list 0x0228F708 x0x24 -> 0x021C479C(side, slot, cid, kind 2, 0)
```

Joining either list would give cid `0x224C` as the key, and the consumer
`0x021B09CC` compares against `0x1E15`. **There is no data-only way to get the
banish rider.**

### The hook, specified

**Site: `0x02268666`, 4 bytes** — `ldrh r0,[r4,#0xe]` (`88E0`) +
`ldr r6,[pc,#0x54]` (`4E15`, `=0x000014FC`) — replaced by a `BL` to an ov5 stub
that gates on the cid, attaches, then **replays both displaced instructions** and
returns to `0x0226866A` (whose `cmp r0,r6` consumes them).

Register budget at the site, read off the following code: `r4` is the global base
and MUST survive; `r0`/`r6` are both redefined by the two displaced instructions
so they are free; `r1`/`r2`/`r3` are rebuilt after. `r5` and `r7` may be live, so
the stub saves them. **⚠️ `r6` must NOT be in the `pop` list** — popping it would
undo the replayed `ldr r6,=0x14FC`. Shape:

```
        push    {r4, r5, r7, lr}
        sub     sp, #0x4                  ; our own [sp] slot for the 5th argument
        ... cid gate, then 0x021C479C(side, slot, 0x1E15, 3, [sp] = 0) ...
      replay:
        add     sp, #0x4
        ldrh    r0, [r4, #0xe]
        ldr     r6, =0x14fc
        pop     {r4, r5, r7, pc}
```

⚠️ `0x021C479C` must be reached by `ldr r7,=0x021C479D ; blx r7`, NOT a bare
`bl` — and `lr` is already on the stack, so the `blx` clobbering it is safe.
`pop {…, pc}` is the Thumb-1-legal return (`thumb-pop-into-lr-footgun`).

### ⚠️ OPEN — a FIDELITY question the hook must answer, and it is NOT settled

**Opcode `0x14` is a general "a card arrived on the field" event, not a
GY-revive-specific one.** Five posters write it (`0x02261542`, `0x022618E6`,
`0x02265078`, `0x02265602`, `0x022656A4`), several from sub-type switches
(`cmp r0,#2`, `cmp r0,#7`), and the arm at `0x02268542` has **no gate of its
own**. So on the face of it the engine gives Plaguespreader its banish rider on
**any** summon, including a Normal Summon from the hand — an over-application of
the printed text.

That is Konami's behaviour for the two cards that print this rider, so copying it
is defensible; but Jet Synchron's rider is printed as belonging to **clause 2's
summon only**. The safer build gates the attach on "this summon came from clause
2" with a **one-shot ARM byte**: clause 2's `+04` resolver dispatcher sets it,
and the rider stub CONSUMES it (attach, then clear). It must be cleared **by the
stub, not by the resolver** — the summon commit `0x0226925C` may complete after
the resolver returns, which is exactly the timing window that killed
`card.upstart_golden_ninja`'s first STAGE latch.

**Not yet decided; flag it to the user with the build.** The in-game test can
distinguish: Normal Summon Jet Synchron from the hand and let it leave the field
— if it banishes, the gate is missing.

---

## Ruled out

- ❌ **OPTION B: hosting clause 2 on the sibling GY-action family
  `chk 0x0224C55D / post 0x0224C669`.** FALSIFIED 2026-09-02 by disassembling
  both functions. It looked attractive for two reasons — it is not one of the
  four sites that build a class-2 descriptor (so it seemed to dodge the
  `find_event_handler` leftmost-record shadow), and all three of its spare
  phantom rows (11 `0x1449`, 12 `0x144C`, 13 `0x1452`) are unclaimed while the
  Grapha family has only one left. Both reasons are irrelevant, because the
  family cannot host this effect at all:

  1. **It never builds a class descriptor, so it never reaches a cls record.**
     Contrast the two, side by side:

     ```
     0x0224C591 (Grapha family)          0x0224C55D (this family)
       add  r0,sp,#8                       r3 = (side<<31 & 0x80000000)
       strh r4,[r0]      desc[+0]=cid           | 0x00500000 | cid
       strb r6,[r0,#2]   desc[+2]=side       movs r1,#0xB
       movs r1,#2                            bl   0x021A1584      <- HAND lookup
       strb r1,[r0,#5]   desc[+5]=CLASS 2    bl   0x021EDDEC      <- posts the word
       movs r1,#0xE
       strb r1,[r0,#3]   desc[+3]=ZONE GY
       ... -> 0x021EC740 -> COMMIT
              -> cls2 invoker -> find_event_handler
     ```

     It packs a 32-bit event word and posts it. There is no descriptor, so there
     are no `+04` resolver / `+08` filter / `+0C` condition / `+10` cost slots —
     and those four slots ARE Grapha's template. Nothing to hang the effect on.

  2. **It gates on the card being in your HAND, not your Graveyard.** BOTH `chk`
     and `post` call `0x021A1584(side, 0x0B, cid)` — zone `0x0B` is the HAND
     (`dispatch.gy_offer_call_chain`: "0x0B (HAND) -> 0x0224BEFC") — and bail on
     a non-positive result (`chk`: `bpl` then `movs r1,#0`; `post`:
     `cmp r1,#0 ; ble 0x0224C6B6`). A card sitting in the Graveyard is not in the
     hand, so this family would never fire for Jet Synchron at all.

  Its two real members corroborate: **Last Will `0x1315`** and **Speed Spell -
  Last Will `0x0DD2`** (zone `0x0D`) and **The Forgiving Maiden `0x1457`**
  (zone `0x0E`) all act from the FIELD or the hand, never from the GY. ⇒ the
  `zone` column here is the zone the effect OPERATES ON, not where the acting
  card sits — the two only coincide in the Grapha family, where the card is in
  the GY *and* summons itself from it.

  ⇒ **The three spare rows in this family are unusable for a GY self-SS**, and
  they are free precisely because the family is a narrow hand mechanism nobody
  has needed. Clause 2 must use the Grapha family and spend its last phantom
  row, `0x0E64` (row 48). ⚠️ The exact semantics of `0x021A1584` and
  `0x021EDDEC` were READ, not executed; what is closed is the absence of a class
  descriptor and the hand gate, which is enough to rule the family out.


- **The 3DS as a second source** — the card is not in `CARD_Name_E.bin`.
- **The GY self-SS resolver's position switch as the banish rider.** Hand-decoded
  `0x02207424..0x022074A8`: Plaguespreader `0x1EA9` and Treeborn Frog `0x19CB`
  both land on the same default leaf (`r4=2, r6=1`), yet only Plaguespreader
  prints the rider. The switch selects face-up / battle position, nothing else.
- **`0x021C6988` as a discard** — it is a hand→**Deck** mover (`[sp] = 0x0D`),
  which is Plaguespreader's *"place 1 card from your hand on the top of the
  Deck"*, not a send-to-GY.
- **A cid-scoped trampoline at `0x021E9120`** — no register holds the cid there
  (see above).
- ❌ **"OTN prints the banish rider and does not implement it."** This was my
  leading hypothesis after an extensive static search came up empty (no
  leave-mask row, no rider table, no list containing all three rider cards, no
  rider-attach call in any of the involved functions). **FALSIFIED by the user
  2026-09-02: they have seen Quillbolt Hedgehog banish itself in-game.**
  Recorded loudly because leaving that wrong negative in the KB would have cost
  the next session a duel.
- **The rider living in the resolver, for Quillbolt.** `0x0220731C`'s *first*
  per-cid switch (`0x02207332`) does contain a rider-attaching arm —
  **`0x022073A0` calls `0x021C4814(desc[+0xC], desc[+0], 1, 0)`**, the rider
  node writer's thin wrapper, guarded by `0x021A167C(desc[+0xC]) < 0xA`. But
  hand-decoding the switch, that arm is reached by the **phantom cid `0x0E10`**;
  **Quillbolt `0x1E15` routes to `0x022073D6`** instead (`bl 0x0224AD94`, the
  cls2 invoker). Quillbolt's `+10` is `0` (no cost function at all) and its
  `+0C 0x021F04FD` is shared with 22 other cards. So for Quillbolt the rider is
  in none of: the resolver, `+0C`, `+10`.

---

## Open questions

1. ~~**Where is the banish-when-it-leaves-the-field rider?**~~ — **ANSWERED
   2026-09-02 BY MEASUREMENT** (savestate triple): a family-1 attached node,
   `key 0x1E15 / kind 3 / param 0`, on the summoned card's own zone chain. All
   three static candidates previously listed here were wrong.
2. ~~**What event actually reaches `cls2[555]`?**~~ — **ANSWERED 2026-09-02**,
   statically and then in-game: the five action slots do not encode the timing,
   and oracle item 4 confirmed the window is Synchro-Material-specific, not the
   generic any-send-to-GY path.
3. ~~**Composition blocker for clause 2**~~ — **RESOLVED as a DESIGN, not yet
   built.** Architecture A: ONE shared cls2 record with ov5 slot dispatchers,
   exactly as `patch_lightpulsar` already ships. Architecture B (the sibling
   GY-action family) is FALSIFIED — see Ruled out.

### Still open — these gate the clause-2 build

4. ~~**Does the rider work on an ARBITRARY cid?**~~ — **CLOSED STATICALLY
   2026-09-03.** The predicate `0x021B0950` tests the four marker keys with no
   cid in scope and its caller `0x021CCBDA` rewrites the destination zone
   `0x0E -> 0x0F`. See *OPEN QUESTION 4 CLOSED* above and KB fact
   `rider.banish_marker_is_cid_blind_to_the_destination`. Still not in-game
   confirmed — it stays on the oracle list.
5. ~~**Is clause 1's event code `>= 0x17`?**~~ — **CLOSED STATICALLY
   2026-09-03**, and the handoff's framing of the risk was backwards. The
   GY-action offer gate provably caps clause 2 at `desc[+4] <= 6`, so a stale
   code can never misroute clause 2 into clause 1's arm; and clause 1's only
   producers post `0x17` / `0x1D` / `0x1E`. **Lightpulsar's `desc[+3] == 0x0E &&
   desc[+4] > 6` transfers verbatim.** KB fact
   `dispatch.gy_action_offer_caps_the_event_code`. The user's savestate is now a
   confirmation (expect `0x1D`), not a gate.
6. ~~**The hand-send cost machine.**~~ — **SIZED AND CLEARED 2026-09-03.**
   `0x021E9038..0x021E918C` + a 0x2C B pool = a 0x180 B clone; its cid switch's
   default arm differs from Plaguespreader's only in `r4`; no cloned-pool pointer
   footgun; one `BL` to retarget at `+0xE8`. KB fact
   `dispatch.hand_cost_machine_0x021E9038`. **BUT IT OPENED A NEW ITEM:** the
   picker it arms is filtered by a criteria row keyed on our cid, which clause 1
   already occupies at rel 0 — see *OPEN QUESTION 6, PART 2* above. Solution is
   `card.upstart_golden_ninja`'s, ported.
7. **Clause 3 (the shared once-per-turn) must land WITH clause 2**, not after.
   Mechanism unchanged: `patch_maiden_eyes_of_blue` — stamp in **slot4**,
   wrapping the costless body `0x021E50DC` (NOT the thunk `0x021E51E5`) and
   posting `0x021D2584(side, cid, 1, 0)` only when it returns 1, so declining the
   prompt does not burn the once-per-turn. ⚠️ NOT yet worked out for the
   clause-2 side, whose slot4 is the cost machine rather than the costless body.
8. **ov5 cave `RESERVE` was raised to 64 KB on 2026-09-02** and no duel has run
   on the enlarged cave. Clause 1 uses no cave, so its pass does not exercise it.
   If the first clause-2 build freezes, **suspect the cave before the card.**
9. **NEW — the PART T hook site is already owned by `patch_lightpulsar`.** A
   4-byte site, one card. Needs a shared `timing_class_hook.py` with an ARMS
   register. See the BLOCKER section above. **This is a user decision, not a
   technical unknown.**
10. **NEW — clause 2 makes the card DUEL-ONLY.** The shared `criteria_row_hook`
    stub is in ov5 and sits on every selecting card's path. **User must accept
    before the build.**

---

---

## Session 2026-09-03 — clause 2 + clause 3, built and confirmed

Everything the 2026-09-02 handoff left open was closed **statically** before any
Thumb was written, and two of its conclusions turned out to be wrong.

### What the handoff got wrong, and it mattered

**1. The discriminator DOES transfer from Lightpulsar.** The handoff said
`desc[+4] > 6` was "actively unsafe" here, reasoning that (a) LP's clause 2 is a
*hand*-SS so its zone is not `0x0E` while both of ours are, and (b) the event-code
array is never cleared, so a stale `0x09` during a GY ignition would satisfy `> 6`
and misroute clause 2 into clause 1's arm.

Both halves are false. `patch_lightpulsar.py:1436-1485` says in terms that *"the
two descriptors share the cid AND the zone (0x0E), so the zone cannot separate
them"* — LP's conflict is **structurally identical** to ours, not different. And
the stale-code scenario is impossible by construction: the off-field offer gate
`0x021ECC6C -> 0x021ECC28` **refuses** any GY-action descriptor whose `desc[+4]`
is above 6, so with a stale code the effect is simply not *offered*. The handoff
had the risk pointing the wrong way.

**2. PART T's hook site was already owned.** The handoff described `0x0224AF96` as
free. It is `patch_lightpulsar`'s, and it is a single 4-byte BL — the same
one-card-per-site situation that produced `criteria_row_hook.py`.

### What was proven, and how

| item | result | how |
|---|---|---|
| OQ4 the rider on an arbitrary cid | **closed** | predicate `0x021B0950` tests four marker keys with no cid in scope; caller `0x021CCBDA` rewrites destination `0x0E -> 0x0F` |
| OQ5 the discriminator | **closed** | the offer gate caps clause 2 at `desc[+4] <= 6`; the leave path only posts `0x17`/`0x1D`/`0x1E` |
| OQ6 the cost machine | **closed** | `0x021E9038` sized (0x154 B + 0x2C pool), its one cid gate benign, pool clean of the pointer footgun, one `BL` to retarget |
| the rider's attach point | **closed** | root `0x022680A8`, cid from `[0x02298A28+0x12]`, arm `0x02268542`, default leaf `0x02268666` |
| the hand count | **measured** | `player+0x0C`, 4 savestates x 2 sides |

`scratch/summon_event_sim.py` is the reusable artefact from that work, and it
**validated itself**: Plaguespreader `0x1EA9` and Quillbolt `0x1E15` — the two
cards whose savestate nodes carry key `0x1E15` — both land on the same arm, while
Treeborn Frog `0x19CB` (a GY self-SS that prints **no** rider) defaults, as does
our donor. The simulator was never told the savestate result.

### The two shared hooks, and the standard applied to them

Adding an arm to a shared stub relocates every other arm's branch offsets and pool
entries, so "the body is byte-identical" is an argument, not a measurement
(`otn-escalate-to-measurement`). Both lifts were therefore checked **by running
the emitted Thumb**:

```
scratch/timing_hook_equiv.py   30 600 inputs   0 differences on 0x0FB1
scratch/rowhook_equiv.py       20 160 inputs   0 differences on 0x0FB1 / 0x1646 / 0x1464
```

Re-run both after adding any further arm.

### The one bug the process caught

The first draft of the cost stub called the mover **before** computing the packed
card reference. After `0x021C6DB4` the card has left the hand array and the picked
index no longer identifies it, so the Graverobber sub-clause would have tested the
wrong card. The native computes the reference first
(`0x021E90F0..0x021E9108` before `0x021E9120`); the mandatory
disassemble-the-built-stub review is what surfaced it.

### Deliberate deviations and known imprecisions

- **The rider is gated by a one-shot byte.** Event opcode `0x14` is a general "a
  card arrived on the field" event and the engine's own arm `0x02268542` has no
  gate, so Konami appears to grant Plaguespreader its banish rider on *any*
  summon. Jet Synchron's rider is printed as belonging to clause 2's summon only,
  so clause 2's resolver sets a byte and the summon-event stub consumes it. ⚠️ If
  a clause-2 activation is abandoned after its resolver ran, the byte survives and
  the next Jet Synchron summon by any means takes the rider.
- **The Graverobber `0x1379` sub-clause is reproduced verbatim** — a hard-coded
  per-card clause riding inside the shared cost machine
  (`grep-the-template-cards-text-too`). Copying it keeps that one interaction
  exactly as the engine already has it; omitting it would have changed it.

### Allocations claimed

```
ov5   CAVE_TIMINGHOOK 0x0239E340 (0x100)   the SHARED timing-class hook
      CAVE_JS_RESDISP 0x0239E440 (0x40)    +04 dispatcher
      CAVE_JS_COND    0x0239E480 (0x80)    +0C dispatcher (clause 3's query)
      CAVE_JS_SLOT4   0x0239E500 (0x40)    +10 dispatcher (clause 3's stamp)
      CAVE_JS_COST    0x0239E540 (0x140)   the hand-send cost machine
      CAVE_JS_RIDER   0x0239E680 (0x60)    the banish-rider attach
      CAVE_JS_ARM     0x0239E6E0 (0x4)     the rider's one-shot byte
      CAVE_LP_TIMING  0x0239C568           RETIRED (lifted into the shared hook)
phantom  0x0E4A  criteria row 33   -> clause 2's Hand row
         0x0E64  GY-action row 48  -> the LAST free row in the Grapha family
```

`check_allocations`: **174 ov5 slots (158 live), 143 phantom claims, 11 ov3
dead-code claims (54 B free) — no overlaps, ledger in sync.**

⚠️ **The GY-action registry's Grapha family is now FULL.** Row 48 was its last
phantom. A future GY-effect card must overwrite a real card's row, which costs
that card its GY effect (the `patch_darksoul` precedent took Manticore's End-Phase
slot outright).

---

## Shipped 2026-09-03 — the chain build, and the collision it caught

`apply_all_patches`: **ALL 49 PATCHES APPLIED**, `BUILD_EXIT=0` captured from the
build itself.

```
data/over_the_nexus/working/rom_all_patches.nds
  129 536 648 bytes
  sha256 d46389132465315bb9995a590141597536d8617c504418e8db56842208da6bc5
```

Asserted on the BUILT ROM's **content**, not its exit status:

```
cls2[557] 0x224C = 0239E441 00000000 0239E481 0239E501 00000000   the dispatchers
criteria rows for 0x224C = [Deck row rel 0, Hand row rel 1]        correct order
GY-action rows for 0x224C = 1
rider hook installed = True    ov5 cost machine present = True
the rider's one-shot byte ships CLEAR = True
```

`_verify_all_patches.py` over the combined ROM: **PASS 38, FAIL 0, SKIP 2** (the
two skips are `patch_boggart_knight` and `patch_darksoul`, which have no
`verify()` of their own — pre-existing and documented). **Lightpulsar, Darkflare,
Upstart Golden Ninja and T.G. Warwolf all PASS**, which is the regression check
that matters for the two shared-hook lifts.

### ⚠️ THE CHAIN CAUGHT A COLLISION THE SINGLE-CARD BUILD COULD NOT

The first two chain attempts **died at step 48/49**:

```
AssertionError: B  phantom 0x234A owns 0 row(s), need exactly 1 -- another patch probably took it
```

**`patch_tg_warwolf` has always consumed `0x234A`** (its `POP_PHANTOM`), but its
`populate_table` claim was **never entered in `check_allocations.PHANTOM_CLAIMS`**
— only its `tg_setcode_table` / `cls2_table` / `registry_row` claims were. So the
guard truthfully reported `[OK] no phantom double-claims` while clause 1 was
independently written to drop the same row. The single-card ROM could not see it:
Warwolf is not applied there, so `0x234A` genuinely *is* free, and the card passed
`verify()`, `check_allocations` **and an in-game test** for two days.

Fixed both ways:

- `CRIT_DROP_PHANTOM` `0x234A` -> **`0x0EAF`**, chosen against a new standard:
  it owns exactly one criteria row in the **stock image AND the fully-chained
  ROM**. 59 phantoms met that bar, so the constraint is free.
- **`tg_warwolf`'s `0x234A` claim is now registered**, so the guard catches this
  class of collision instead of a 25-minute build doing it. Ledger: 147 claims.
- Banked as `tool.register_the_phantom_in_the_same_edit`.

**⚠️ `exit 0` LIED A THIRD TIME.** The task runner reported success because the
wrapper ended in a `tail` that succeeded; the build itself had exited **1**. The
third chain run appends `BUILD_EXIT=$?` to the log for exactly this reason.
`otn-chain-build-verify-artifact` already said to assert the artifact — the final
step number, the patch count and the ROM's own sha256 — and this is the case that
proves the status line is worthless.

### The single-card ROM changed, and by exactly how much

The phantom swap means `rom_jet_synchron.nds` is no longer byte-identical to the
build the user played. Diffed rather than asserted:

| | |
|---|---|
| the build the user TESTED | `4871e198…3439a`, kept at `rom_jet_synchron.TESTED.nds` |
| after the description fix | `09f98ee7…0a22` — overlay 3, every ov5 slot and arm9 **byte-identical**; only `bin2.pac` differed |
| after the phantom fix | `4dbe9158…a80f` — the current build |

The complete overlay-3 difference between the tested build and the current one:

```
rows ONLY in the tested build:  (0x0EAF, 0x0009, 0x0223CAB5, 0x0002, 0x008C)
rows ONLY in the current build: (0x234A, 0x200F, 0x02241A81, 0x000E, 0x0000)
Jet Synchron's own two rows:    IDENTICAL
registry still sorted, still 1388 rows
```

Both `0x234A` and `0x0EAF` are phantoms with **no `card_prop` record**, so no
obtainable card carries either cid and neither row is reachable by anything. The
change is behaviourally inert and the in-game result carries. A re-test on the
current build is belt-and-braces, not a correction.
