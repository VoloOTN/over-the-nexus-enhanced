# Wattuna → Normal-Monster donor — findings (2026-09-21)

Task: implement **Wattuna** (LIGHT / Thunder / Tuner / Lv4 / 800 / 700) on a
records-free vanilla Normal Monster. User scope decision this session: **all
three clauses** (U1 direct attack, U3 SS-from-hand, U4 Tribute → Watt Synchro),
with **one approved deviation: at most one hand material in U4**.

Wattkyuki is explicitly OUT of scope this session (separate card, needs a new
Extra-Deck Synchro donor + Watt set-code grow before any clause exists).

Printed text sourced from `scratch/ygoprodeck_cache.json` this session, NOT recall:

> This card can attack directly. You can only use each of the following effects of
> "Wattuna" once per turn. At the end of the Damage Step, if your monster inflicts
> battle damage to your opponent: You can Special Summon this card from your hand.
> When this card inflicts battle damage to your opponent by a direct attack: You
> can Tribute this card on the field and 1 or more non-Tuner monsters from your
> hand and/or face-up field, and Special Summon 1 "Watt" Synchro Monster from your
> Extra Deck whose Level equals the total Levels of those Tributed monsters.

## Confirmed (this session)

### Neither card exists in EITHER build — reference source 2 is exhausted
Name scan over the NDS card database and over all 5888 3DS `CARD_Indx_E` records
(`3ds_extract/partition0/romfs/duel/card/`, UTF-16LE names): **zero hits** for
`tuna` and zero for `kyuki`, by exact prefix, whitespace-stripped exact, and raw
substring sweep. The NDS ships 22 Watt cards, the 3DS 25 (it adds Wattcobra
`0x2612`, Wattcancel `0x263F`, Wattaildragon `0x2728`); the shared 22 have
identical cids in both builds. `CARDS_ZEXAL_3DS_ASM.md` documents only Wattcobra.
So there is **no Konami implementation to port** for Wattuna — NDS-side design.

Both cards are on the repo's own wishlist at
`data/over_the_nexus/enhanced_wip/changelog.md:99-102`.

⚠️ **Spelling trap for anyone grepping that changelog:** it lists `-> Watttuna`
and `-> Watttrain` with THREE t's. The canonical TCG names are **Wattuna** and
**Wattrain** (one `t` before the vowel), which is what
`scratch/ygoprodeck_cache.json` uses. A name-based grep of the changelog misses
both. (ygoprodeck ids: Wattuna 10113611, Wattkyuki 67752972.)

Corroborated independently against the stock **US** image
(`data/over_the_nexus/backup/unpatched/us.nds`, 4307 index / 4306 prop records):
the 22 Watt cids are identical there, confirming the cid space is shared across
regions. ⚠️ That image is only safe for cid/name questions — per CLAUDE.md the US
build's overlay-3 layout is NOT address-compatible, so every ADDRESS in this file
comes from the EU `BYYP` working ROM.

### DONOR = SPIRIT OF THE HARP `0x1050` — `donor_scan` VERDICT: **CLEAN**
`python -m otn_enhanced.tools.donor_scan 0x1050` this session:

```
0x1050  Spirit of the Harp   Normal Monster  Lv4  LIGHT Fairy  800/2000
        name slots (floor 10): {'e':18,'f':18,'g':11,'i':17,'j':10,'k':11,'r':18,'s':17}
        desc slots (floor 60): {'e':67,'f':62,'g':69,'i':97,'j':60,'k':74,'r':104,'s':65}
        VERDICT: CLEAN - no data structure names this cid
```

Zero aligned u16/u32 occurrences in ov3 + arm9 (the 70 reported hits are all
code-region instruction encodings). Unclaimed in `otn_enhanced/docs/engine/allocations.yaml`
and in `check_allocations.py` under every pool name.

Lowest card_prop churn of the three clean LIGHT Lv4 vanillas (others: Rogue Doll
`0x0FD2`, Shining Abyss `0x13E2`; Dunames Dark Witch `0x12B2` excluded — playable
beater, already White Dragon Ninja's donor): **Level 4, LIGHT and ATK 800 already
match Wattuna**. Only race (Fairy → Thunder), DEF (2000 → 700) and card_type
(Normal 1 → Tuner Effect 33) move.

Risk-checklist item 3 **PROVEN**: name slot floor 10 B ≥ `"Wattuna"` 7 B. Desc is
not slot-limited — the cid joins `card_text.CARD_TEXT`, which takes the
index-order re-emit path.

**There are ZERO clean Thunder-race Normal Monsters** (`donor_scan --free --race
Thunder` → 0 rows), so a race rewrite was unavoidable for any donor.

### Membership-list free slots — measured in BOTH images this session
Dumped from stock `rom.nds` and chained `rom_all_patches.nds`:

| list | addr | count | phantoms free (chained) |
|---|---|---|---|
| direct-attack grant | `0x0226D730` | 25 | `0x1129 0x1133 0x1134 0x118E 0x1221` (5) |
| LIST A "damage by DIRECT attack" | `0x0226EE7C` | 19 | `0x15D0 0x1A1F 0x1DB6` (3) |

In the chained image `0x0FD3` (Wattkid/Wattcobra) occupies index 0 of both, i.e.
Wattcobra spent `0x0EB3` and `0x0EC0` — matching `allocations.yaml:1562-1563`:

```
  - {pool: direct_attack_list, cid: 0x0EB3, owner: wattcobra}
  - {pool: da_damage_trigger_list, cid: 0x0EC0, owner: wattcobra}
```

⚠️ Phantom status above was labelled via `scratch/cid_to_name.json`, which is a
**PARTIAL dump** (4305 keys, cid range 3400–9448, 1744 gaps) and can mislabel a
real card as a phantom. The same phantom sets were independently derived via
`donor_scan.cards()` in `notes/wattcobra-normal-donor-findings.md:42-89`, so they
corroborate — but **re-prove against `card_prop` presence in the build.**

### Watt set-code list `0x0209CBEA` has NO phantoms — a grow, not an insert
Dumped via `ndspy.code.MainCodeFile` this session (the list is in a compressed
ARM9 section; a raw `rom.arm9` index is out of range and throws). All 22 entries
are real cards, in sorted order, ending at Wattkey `0x2481`; index 22 onward is
the next set-code list (Karakuri, `0x1140` then `0x2388`…):

```
0 0xfd3 Wattkid       1 0x2261 Wattgiraffe   2 0x2262 Wattfox      3 0x2263 Wattwoodpecker
4 0x227d Wattcube     5 0x22fb Wattbetta     6 0x22fc Wattlemur    7 0x22fd Wattpheasant
8 0x230f Wattchimera  9 0x2315 Wattcine     10 0x232a Wattcannon  11 0x238f Wattkiwi
12 0x2390 Watthopper 13 0x2391 Wattdragonfly 14 0x2392 Wattsquirrel 15 0x23a7 Wattcastle
16 0x23a8 Wattjustment 17 0x23bf Wattkeeper 18 0x246a Wattberyx   19 0x246b Wattmole
20 0x2477 Watthydra  21 0x2481 Wattkey
```

⇒ PART F must use the `patch_psi_reflector` **relocate-and-bump** (repoint the
thunk's list literal at a longer copy, bump its `movs r2,#N`), not a phantom drop.
Watt set code = `0x58`; `has_set_code` ptr table `0x0209D0D8`.

### The hand-material Synchro gate has a DEAD literal — U4's material half is ONE WORD
`synchro.native_hand_material_mode` (VERIFIED) gate `0x022494EC` compares the
FIRST pick's cid against three ov3 literals. Read live this session, **identical
in stock and chained images**:

```
0x02249534 = 0x0E66   <-- T.G.-reserved phantom, NO card_prop
0x02249538 = 0x2184   Eccentric Boy
0x0224953C = 0x2353   Malefic Parallel Gear
```

Repointing `0x02249534` at the donor grants it the native mode count-neutrally.
`0x0E66` is claimed in `allocations.yaml:1390` only under pool `cls2_table`
(owner `hyper_librarian_chain`) — a **different pool**, so the claim is legal
under the ledger's distinct-address-space convention. Flagged to the user.

This also delivers the user-approved deviation for free: the validator accepts a
hand pick only as the SECOND one (`cmp r6,#0xb` @ `0x02249BE8`, `cmp r0,#1` @
`0x02249BF0`) ⇒ Wattuna first (field) + at most ONE hand non-Tuner.

### U3's template is Battle Fader `0x21A9`, and the gate is an ARM9 list
`donor_scan 0x21A9` this session — `VERDICT: ENTANGLED`, 5 binding occurrences:

```
cls2 record[519]+0x0:  ov3:0x02278CAC/u16
unclassified:          ov3:0x022700F4/u16, ov3:0x02270164/u16,
                       ov3:0x021C697C/u32, ov3:0x02206C88/u32
arm9 data-region u16:  arm9:0x0209BD4E, arm9:0x020AA9DC
```

`dispatch.hand_effect_offer_list` (VERIFIED, and MEASURED in-game during the
Thunder Sea Horse re-home 2026-09-17) proves a card is offered from hand **only**
if its cid is in an ARM9 list — the cls2 record alone is never consulted. The two
known lists are LIST A `0x0209BC4E` (`0x1E` entries) and LIST B `0x0209BC8C`
(`0x24`). **`0x0209BD4E` is outside both**, so Battle Fader is gated by a THIRD,
as-yet-unclassified ARM9 list: the battle-time hand-response gate. That is U3's
missing piece and the next thing to pin down.

### ✅ U3 SOLVED STATICALLY — the hand-responder gate is a LIST + a cls2 record

Open Question 1 is closed. Battle Fader's arm9 hit `0x0209BD4E` is index 23 of a
**third ARM9 hand list**, distinct from `dispatch.hand_effect_offer_list`'s two:

* **base `0x0209BD20`, 38 entries (`0x26`)**, sorted, ends `0x0209BD6A`.
* **Reader = thunk `0x02023574`** (Thumb `0x02023575`):
  `ldr r1,[pc,#4] (= 0x0209BD20) ; ldr r3,[pc,#8] (= 0x02022E15) ; movs r2,#0x26 ; bx r3`
  — i.e. the shared sorted binary search `0x02022E14`.
* **Count immediate `movs r2,#0x26` @ `0x02023578`**; sole list literal @
  `0x0202357C`. That literal sits in the SAME pool as the two known hand lists
  (`0x0202356C` = `0x0209BC4E`, `0x02023570` = `0x0209BC8C`), which is why it was
  never classified before.
* **The thunk is LIVE — three ov3 BL callers**: `0x021D3078`, `0x021D382E`,
  `0x021F0ADE`. (Contrast its dead sibling thunk `0x0202353C`, which the KB notes
  has no caller.) All three load `r0 = ldrh [descriptor]`, i.e. the cid.

**The acceptance rule, disassembled this session at `0x021D3828`:**

```
0x021D3828  push {r4,lr}
0x021D382A  adds r4,r0,#0        ; r4 = event descriptor
0x021D382C  ldrh r0,[r4]         ; r0 = cid
0x021D382E  bl   0x02023574      ; member of list 0x0209BD20 ?
0x021D3832  cmp  r0,#0
0x021D3834  beq  0x021D3844      ; miss -> falls through to a cid-compare chain
0x021D3836  ldrb r0,[r4,#5]      ; descriptor[+5] = TABLE SELECTOR
0x021D3838  cmp  r0,#2           ; must be 2  ==  cls2
0x021D383A  bne  0x021D3840
0x021D383C  movs r0,#1 ; pop     ; ACCEPT (hand responder)
0x021D3840  movs r0,#0 ; pop     ; REJECT
```

⇒ **A card responds from the hand iff (cid ∈ `0x0209BD20`) AND (it owns a cls2
record).** That is exactly the pair PART C needs, and it matches the family the
list contains: Gorz `0x199E`, Tragoedia `0x1F99`, Battle Fader `0x21A9`,
Van'Dalgyon `0x190A`, Green/Yellow Baboon `0x18EC`/`0x2195`, Dragon Ice `0x1D3C`,
Watapon `0x17CC`, Rose Fairy `0x21B0`, Synchro Magnet `0x2253`, Doppelwarrior
`0x244D`.

The `0x021D3078` caller is the same test inside a `0x24`-stride record walk, with
a fallback `bsearch(<pool@0x021D315C>, count 0x1D)` for non-members — noted, not
needed.

**`0x0209BD20[0] = 0x0E68` is a PHANTOM** (T.G.-reserved, `TG_NATIVE` range
`0x0E66..0x0E6C`) and is **unclaimed** — `grep 0x0E68` over
`otn_enhanced/docs/engine/allocations.yaml` and `check_allocations.py` returns nothing. Donor
`0x1050` sorts below `0x17C9`, so dropping `0x0E68` and inserting `0x1050` keeps
the list sorted and **count-neutral — no relocate-and-bump needed.**

⚠️ Verify `0x0E68` has no `card_prop` row in the build before spending it.

### ✅ U4's RESOLVER IS A SHARED NATIVE ONE — `0x02249EC0`, and it is pure DATA

After the Eccentric Boy route was falsified (see Ruled Out), grepping the shipped
patches for the printed clause — CLAUDE.md `grep-shipped-patches-for-the-clause` —
found it immediately. `otn_enhanced/docs/engine/resolver_protocol.yaml:77`
(`resolver.shared_synchro_summon`):

> **THE SHARED SYNCHRO-SUMMON RESOLVER `0x02249EC0`** (Formula Synchron
> `cls3[730]`, Urgent Tuning `cls0[996]`) IS NATIVELY MANDATORY AND NATIVELY
> RE-ENTERS PHASE `0x80` … "Immediately after this effect resolves, Synchro
> Summon" is realised INSIDE the resolver.

Phase machine on `[0x0229AAFC+0x70]`:

| phase | action |
|---|---|
| `0x80` | probe candidates — `0x021F05A8` → `0x02243FE0` **on the cid's criteria row**; on a hit `0x0219A818(player, 0x11D)` (a MESSAGE, not a Yes/No) → `0x7F` |
| `0x7F` | open the picker `0x0219C430(player, 6, cid, param)` → `0x7E` |
| `0x7E` | write the pick into summon record `0x02298A28` (`+0xE` cid, `+0xC` instance) → `0x7D` |
| `0x7D` | poll the Synchro procedure `0x02263494` (`bl` @ `0x0224A096`): `>0` commit via `0x02269320(player, instance, 2, 0)`; `==0` stay; `<0` → `0x80` |

The only per-cid code in phase `0x80` is Urgent Tuning `0x1EF0`'s Battle-Phase
gate — so the resolver is **cid-blind for our donor**.

**Shipped precedent: `patch_steam_synchron`** (`otn_enhanced/docs/engine/cards.yaml:810`,
IN-GAME CONFIRMED 2026-09-03, all eight oracles) transplants Formula Synchron's
clause as **four count-neutral data edits and no injected code at all** — cls3
record, criteria row, spell-speed-2 list, set-code list. It even works in puzzle
mode because nothing lives in the ov5 cave.

⚠️ **`resolver_protocol.yaml:141` — the resolver FORCES the activating card as a
material** for any cid whose `0x02029E60` bit is set: in phase `0x7D` it stores
`desc[+0xC]` into the forced-material slot `0x0229AC7C` @ `0x0224A094` before
polling. For Accel Synchro Stardust Dragon (which Tributes *itself*) that was a
bug needing `0x0229AC7C` zeroed. **For Wattuna it is the FEATURE** — the printed
text requires Wattuna itself to be one of the Tributed materials. Do not "fix" it.

⇒ PART E becomes: a record for `0x1050` pointing at resolver `0x02249EC0`, fired
from LIST A, plus a **criteria row** for the phase-`0x80` candidate probe. The
Watt-only restriction is expressible in that criteria row's handler (the Sea
Lancer `CAVE_SL_CRIT` shape — a custom ov5 criteria handler), rather than needing
a hook on the Extra-Deck offer.

### Battle Fader's two "ov3 tables" are FALSE POSITIVES — PART C is just 2 edits

Open Question 2 is closed, and the answer removes work. `donor_scan 0x21A9`
reported `ov3:0x022700F4/u16` and `ov3:0x02270164/u16` as *binding, unclassified*.
Both are inside the **ignition-condition registry `0x0226FAFC`** (146 rows ×
12 B, `{u16 cid, u16 aux, u32 f1, u32 f2}`; ends `0x022701D4`), and neither is a
cid key — they are the **low halfword of the function pointer `0x021F21A9`**:

```
hit 0x022700F4 -> row 127 @0x022700F0 off +4   cid=0x23F0 Liberty at Last!  f1=0x021F21A9
hit 0x02270164 -> row 136 @0x0227015C off +8   cid=0x248C Blackboost        f2=0x021F21A9
0x21A9 present as a cid key in the registry: False
```

⇒ Battle Fader's **only** real ov3 data reference is `cls2 record[519]`
@ `0x02278CAC`. So PART C needs exactly **two** count-neutral edits: a cls2 record
for `0x1050`, and membership of the ARM9 hand-responder list `0x0209BD20` (drop
phantom `0x0E68`). No ov3 membership tables to join.

⚠️ Reusable lesson, same shape as the KB's Darkbright `0x1C08` warning: a u16 scan
over a data region hits **pointer halves** as well as cids. Any `0x021Fxxxx` /
`0x0220xxxx` pool word whose low half looks like a plausible cid will do this.
Always re-derive the row offset before believing a `donor_scan` "binding" hit.

### U4 dispatches to cls1, U3 to cls2 — no leftmost-record shadow

`find_event_handler` returns the LEFTMOST same-cid record, so a cid cannot own two
dispatchable rows in one table (the Warwolf E1/E2 shadow). Checked this session:
the LIST A battle-damage event (code `0x10`) dispatches to **cls1** —
`patch_wattcobra.py:74,175-195` clones Fane's `cls1 record[1021]` for exactly this
trigger (`CLS1_BASE = 0x022860D4`, stride 24, count `0x535`). U3's hand-responder
gate demands `descriptor[+5] == 2` = **cls2**. Different tables ⇒ **the two
clauses do not shadow each other.**

### ✅ PART E fully designed — and the Watt filter needs NO custom code

A delegated design pass (this session) independently reached the same Eccentric
Boy conclusion and settled the rest. Claims marked ✔ I re-verified myself against
the ROM; the others carry the design pass's cited disassembly and **must be
re-read at build time** before being trusted.

**(a) Open Question 3 is CLOSED: `0x02249EC1` is a legal cls1 `+04`.** The risk was
that the `[0x0229AAFC+0x70]` phase protocol is ignition-only. It is not — Wattcobra's
own in-game-confirmed resolver `0x02207EF4` runs the same protocol on the
battle-damage path: `0x02207FCC` loads `[0x0229AAFC+0x70]`, subtracts `0x78` and
indexes a 9-entry halfword table @ `0x02207FEE` covering phases `0x78..0x80`,
then at `0x02208026` runs the identical `0x02234E78 → 0x02243FA8 → 0x0219A818`
idiom as `0x02249EC0`. ⇒ the event-`0x10` cls1 path enters `+04` at phase `0x80`
and re-enters on the returned phase.

**(b) ✔ The Watt-only Extra-Deck restriction is a DATA slot, not a hook.** The
offer happens in the Extra-Deck enumerator `0x0223BE40`, reached from phase `0x80`
via `0x02243FE0` → the criteria row's own handler. Blackwing - Aurora the Northern
Lights `0x2385` already pairs that enumerator with the **stock set-code filter**.
Read by me from both images, **byte-identical stock vs chained**:

```
0x022430A0  0eb5 021c 0220 105e 02ab 0290 9068 0090
0x022430B0  0420 0190 081c 1188 014a f8f7 c1fe 0ebd
0x022430C0  25c8 2302                     ; pool = 0x0223C825 (has_set_code filter)

0x022430A4  movs r0,#2 ; ldrsh r0,[r2,r0]  ; row.b = THE SET CODE -> [sp+8]
0x022430B0  movs r0,#4                     ; mode = is_synchro   -> [sp+4]
0x022430BA  bl   0x0223BE40                ; the Extra-Deck enumerator
```
✔ Aurora's criteria row 1254 @ `0x02274E8C` = `{a=0x2385, b=0x003F, h=0x022430A1,
fl=0x00000002}` — `0x3F` is the Blackwing set code, passed to the filter as
`*crit` and tested against **the candidate's** cid.

⇒ PART E's filter = clone those `0x24` bytes (pool word included) into
`CAVE_WU_ED`, change `movs r0,#4` → `movs r0,#0x24` (adds the native
`can_synchro 0x02249540` gate), re-encode the `BL` @ `+0x1A` for the cave address.
**No `has_set_code` call we write, no code hook anywhere**, and the filter itself
stays stock ov3.

Criteria row for the donor: `{a = D, b = 0x0058, h = CAVE_WU_ED|1, fl = 0x00000802}`
— set code `0x58` = Watt; `fl` taken from Formula/Steam Synchron (the word proven
on the `0x02249EC0` resolver path) rather than Aurora's `0x0002`.
⚠️ `fl = 0x0802` vs `0x0002` on Aurora's handler is **`unproven`** — settle it
offline with `scratch/thumbemu.py` before any ROM ships (see Next Experiment).

**(c) The cls1 row**, cloned from Wattcobra's (itself Fane's, verbatim but `+04`):

| slot | Wattcobra | Wattuna U4 |
|---|---|---|
| `+00` | `0x0FD3` | `0x1050` |
| `+04` | `0x02207EF5` | **`0x02249EC1`** (shared Synchro resolver) |
| `+08` | `0x021E32D5` | unchanged (masked zone predicate) |
| `+0C` | `0x0224A115` | `CAVE_WU_COND\|1` — HOPT query `0x021A14E8`, else tail `0x0224A115` |
| `+10` | `0` | `CAVE_WU_SLOT4\|1` — "You can" `0x021E51E5` + turn-log post `0x021D2584` |
| `+14` | `0x02234E01` | **`0`** (Wattcobra's is the "add to hand?" prompt — wrong here) |

A cave pointer in `+10` needs a `timing_class_hook.py` arm for category 2.

**(d) LIST A drop = `0x1DB6`** — least entangled of the three free phantoms: in the
chained image its only surviving occurrence is the list entry itself (its cls1 row
was consumed by `maiden_eyes_of_blue`). `0x15D0` and `0x1A1F` each still own two
cls1 rows plus more.

**(e) DEVIATION — RULED ON BY THE USER 2026-09-21: "Accept both".** Reusing the Synchro procedure
posts a **genuine Synchro Summon**, but printed Wattuna says *Special Summon*. So
"each time a Synchro Monster is Synchro Summoned" responders fire — and **T.G.
Hyper Librarian is shipped in this ROM**, so it would draw. Conversely the
materials are sent as Synchro Material, not Tributed, so "when a monster is
Tributed" responders will NOT fire. Neither is a bug to route around; it is the
cost of the only architecture that enforces the printed Level arithmetic.

**Both accepted as deliberate deviations — user ruling 2026-09-21**, chosen from
four options (accept both / fix the Tribute half / suppress the Synchro post /
rebuild U4 bespoke) BEFORE the build, not discovered after it. Record them in the
module docstring and in the in-game test script so the Hyper Librarian draw is
read as expected behaviour rather than a regression.

**(f) ❌ CORRECTION to the design pass — the Watt set-code table is NOT a blocker.**
It claimed the donor must already be in the 22/22 Watt list or a real card must be
dropped. Wrong twice over: (i) the criteria row's `b = 0x58` is tested against the
**candidate** Extra-Deck Synchro, not against Wattuna, so U4 works regardless of
the donor's own membership; (ii) the list can be GROWN without dropping anyone via
the `patch_psi_reflector` relocate-and-bump (see above). Donor Watt membership is
PART F, severable, flavour-only.

### U3's cls2 record shape — read from FIVE native hand-self-SS cards

Read from the stock cls2 table (`0x02275C04`, stride `0x18`, count `0x2B9`):

```
cls2[155] 0x17CC Watapon         +04=0x02206ABD +08=0 +0C=0x021F0A39 +10=0x021E51E5 +14=0
cls2[196] 0x199E Gorz            +04=0x02206ABD +08=0 +0C=0x021FA265 +10=0x021E51E5 +14=0
cls2[424] 0x1F99 Tragoedia       +04=0x02206ABD +08=0 +0C=0x021F0A39 +10=0x021E51E5 +14=0
cls2[519] 0x21A9 Battle Fader    +04=0x02206ABD +08=0 +0C=0x021F0A39 +10=0x021E51E5 +14=0
cls2[521] 0x21B0 Rose Fairy      +04=0x02206ABD +08=0 +0C=0x021F0A39 +10=0x021E51E5 +14=0
cls2[557] 0x2253 Synchro Magnet  +04=0x02206ABD +08=0 +0C=0x021F0A39 +10=0x021E51E5 +14=0
```
(Green Baboon `0x18EC` / Dragon Ice `0x1D3C` are the *mandatory* variant:
`+04=0x0221E9DD`, `+10=0x021E5201`.)

⇒ **the hand self-Special-Summon shape is `{+04 0x02206ABD, +08 0, +0C <cond>,
+10 0x021E51E5, +14 0}`.** `+04 = 0x02206ABD` corroborates the KB's Doppelwarrior
note (`cls2[658]` hand-SS `+04 = 0x02206ABD`). `+10 = 0x021E51E5` is the "You can"
optional tag — the same slot-4 literal U4's row needs.

**The shared condition `0x021F0A38` is NOT the trigger discriminator.** Battle
Fader (opponent declares a direct attack), Tragoedia (you take battle damage),
Watapon and Rose Fairy (added to hand) all share it. Disassembled this session it
is an ordered per-cid compare chain over pool literals, then generic checks:
`0x021A25A0(side, desc[+0xC])` — *the card must actually be in the hand*, `>= 0`
or return 0 — then a second cid chain, `0x021B9ECC` (can-SS wrapper), `0x021F0384`
and `0x021BA440`. The per-card timing is therefore carried by **which event
reaches the record**, not by the condition.

⇒ **U3's design**: cls2 record `{0x1050, 0x02206ABD, 0, CAVE_WU_U3COND|1,
0x021E51E5, 0}` where the ov5 condition narrows the timing to "my monster just
inflicted battle damage on the opponent" and then tail-calls the stock
`0x021F0A38`. The battle context is already known from the LIST A gate —
`0x02298AD8`, whose `[+2]` is the direct-attack flag — so the fields for
"damage dealt" and "recipient side" live in the same struct.

⚠️ `unproven`: the exact `0x02298AD8` field for *damage was dealt to the opponent*,
and whether adding `0x1050` to `0x0209BD20` offers it on unwanted events too
(Watapon/Rose Fairy sit in the same list on "added to hand" events). Both are
readable offline — see Next Experiment.

### ✅ ALL PHANTOM DROPS CHOSEN AND VALIDATED (2026-09-21)

Every drop below was proven **absent from `card_prop`** via `donor_scan.cards()`
(4305 real rows) and confirmed present in **both** the stock and chained images.
`scratch/cid_to_name.json` was NOT used. Each owns exactly one row in its table.

| resource | drop | ledger status |
|---|---|---|
| cls1 `0x022860D4` (count 1333, insert pos 66) | `0x1147` | UNCLAIMED |
| cls2 `0x02275C04` (count 697, insert pos 38) | `0x0EC3` | UNCLAIMED |
| criteria `0x022713C4` (count 1389, insert pos 58) | `0x0EB9` | UNCLAIMED |
| LIST A `0x0226EE7C` | `0x1DB6` | claimed only as `cls1_table:maiden_eyes_of_blue` — **different pool, legal**; its cls1 row is already spent so the list entry is its last occurrence |
| direct-attack `0x0226D730` | `0x1129` | UNCLAIMED |
| hand-responder `0x0209BD20` | `0x0E68` | UNCLAIMED |
| donor cid | `0x1050` | UNCLAIMED; **is** a real card (correct — it is the donor) and absent from all three lists in both images |

### U3 BUILD DECISION — user 2026-09-21: "using watapon/rose-fairy"

U3 ships with the **stock** condition `0x021F0A39`, i.e. the Watapon / Rose Fairy /
Battle Fader record verbatim — no ov5 stub, so U3 is **pure data and works in
puzzles**. The timing question (which events reach a `0x0209BD20` member) is
deliberately left to the in-game test rather than more disassembly.

⇒ **U2's once-per-turn on U3 is DEFERRED**, because the HOPT and the eventual
timing narrowing both live in that same `+0C` slot and building it now means
building it twice. U4 still gets its HOPT. State this in the test script: U3 may
be usable more than once per turn, and may be offered at unintended times.

### Hand-SS dispatch table is NOT full — corrects a stale KB claim
`otn_enhanced/docs/engine/cards.yaml` (`card.unknown_synchron`) says the shared hand-SS
trampoline's dispatch table is FULL at four 8-byte rows. **Stale.** It was
re-homed 2026-09-14: `ov5_cave.py:1625` `CAVE_TG_SSTABLE = 0x0239F240`,
`tg_table.py:440` `SS_TABLE_BYTES = 0x40` = 7 registrants + terminator. Read live
from `rom_all_patches.nds` this session:

```
row0 cid=0x11b7 cond=0x0239fda1   (Elder of the Six Samurai / Flame Cerebrus)
row1 cid=0x1f18 cond=0x0239b1c9   (T.G. Striker)
row2 cid=0x17ce cond=0x0239def1   (Junk Servant)
row3 cid=0x181c cond=0x0239df21   (Unknown Synchron)
row4 cid=0x13ae cond=0x0239f311   (Assault Synchron)
row5..7 = 0 (terminator + 2 free)
```

⇒ 5 used, **2 free**. (Not needed by the current U3 design, which uses the Battle
Fader battle-response route rather than the Main-Phase hand menu — but the KB
correction stands and must be filed with `corrected_by:`.)

### Cave headroom
`ov5_cave.py:1803` `CAVE_FREE = 0x023A12B0` (read this session; last allocations
are `patch_dragunity_remus`'s `CAVE_DR_*`, ending `CAVE_DR_ARM = 0x023A12A0`).

## ✅ BUILT 2026-09-21 — `rom_wattuna.nds`, verify 22/22 PASS — AWAITING IN-GAME TEST

`.venv-1/Scripts/python.exe -m otn_enhanced.cards.wattuna --text`

```
B direct-attack list @0x0226D730: dropped 0x1129, inserted 0x1050 @1, count 25 unchanged
C cls2 (hand self-SS): dropped phantom 0x0EC3 @38, inserted 0x1050 @41, count 697 unchanged
D LIST A (damage by DIRECT attack) @0x0226EE7C: dropped 0x1DB6, inserted 0x1050 @1, count 19 unchanged
E cls1 (Synchro-summon resolver): dropped phantom 0x1147 @72, inserted 0x1050 @66, count 1333 unchanged
E criteria row (Watt Synchro, set code 0x58): dropped phantom 0x0EB9 @66, inserted 0x1050 @71, count 1389 unchanged
E hand-material gate @0x02249534: 0x0E66 -> 0x1050
E ov5 CAVE_WU_ED @0x023A12B0: 36 B (Aurora clone, mode 0x24, filter 0x0223C825)
C hand-responder list @0x0209BD20 (x38): dropped 0x0E68, inserted 0x1050 @0
BEFORE: lvl=4 attr=LIGHT race=Fairy atk=800 def=2000 type=Normal Monster
```

Read back from the built ROM: `level 4, LIGHT, Thunder, atk 800, def 700,
card_type 'Tuner Monster'` ✓. `card_text.check_rom_text` matches in all 8
languages ✓ (asserted against `card_text`, never a local constant).

**The cave stub disassembles clean** — `push {r1,r2,r3,lr}` / `pop {r1,r2,r3,pc}`
correctly paired (no POP-into-LR miscode), `ldr r2,[pc,#4]` resolves to its own
carried pool word `0x0223C825`, one `bl 0x0223BE40` correctly re-encoded, and
**exactly 5 bytes differ from Aurora's stock handler**: the mode byte at `+0x10`
(`04 20` → `24 20`) and the 4-byte BL at `+0x1A`.

**Regression sweep over the shared resources (stock vs built):** ZERO real cards
lost from the direct-attack list, LIST A, LIST B or the hand-responder list; the
only gain in each is `0x1050`. LIST B is byte-identical. Wattgiraffe, Wattpheasant,
Wattchimera and Watthydra all still in both battle lists; Battle Fader, Watapon
and Rose Fairy all still in the hand-responder list. Aurora's native handler and
the Eccentric Boy / Malefic Parallel Gear literals are byte-identical to stock.

`check_allocations --emit`: **no collisions** — 267 ov5 slots, 274 phantom claims.

⚠️ NOT wired into `steps.STEPS` or `_verify_all_patches.SHIPPED`, per CLAUDE.md —
single-card ROM only until the user confirms in-game.

## ❌ IN-GAME TEST 1 FAILED — user 2026-09-21 (build 1, `rom_wattuna.nds`)

User's exact words:

> 1. Confirmed
> 2. Confirmed
> 3. Negative. See .ml2 (before attack), .ml3 (after attack, effect activation
>    prompt opens), .ml4 (effect resolves) but nothing happens
> 4. Could no verify
> 5. Confirmed
> 6. Negative, nothing happens when a watt makes direct damage.

Reading confirmed by the user before any investigation, plus two disambiguations:
**item 3 — NO PICKER APPEARED**; **item 6 — WATTUNA WAS NEVER OFFERED from hand.**

### What PASSED (do not regress these)
* **U1 works** — Wattuna declares a direct attack (test 2).
* **Card data is right** (test 1).
* **U4's TRIGGER AND DISPATCH WORK.** The direct attack posts event `0x10`, the
  cls1 record is found, and the resolver is entered and runs to completion — the
  activation prompt opens and the effect resolves. ⇒ LIST A membership, the cls1
  insert, `find_event_handler` routing, and `+10 = 0x021E51E5` (the "You can"
  prompt) are all **in-game confirmed**.
* **Test 5 passed** — attacking INTO a monster offers nothing. ⇒ the LIST A vs
  LIST B split is correct in game, corroborating Wattcobra's measurement.

### Failure 1 (U4): resolver enters, NO PICKER, exits
Prompt opens → accepted → **no material picker** → nothing. Because
`+0C = 0x0224A115` is `movs r0,#2 ; bx lr` (ALWAYS activatable), the offer is
unconditional, so an empty candidate probe cannot suppress the prompt — it can
only make the effect fizzle exactly as observed. That places the failure in
**phase `0x80`**, which probes `0x021F05A8` → `0x02243FE0(side, cid, param)` and
only advances to `0x7F` (the picker) on a nonzero count.

Candidate causes, none yet tested:
 (a) `fl = 0x0802` on the cloned Aurora handler is wrong — **this was the single
     `unproven` item in the build** and is now the prime suspect;
 (b) `param = 0x02234E78(desc)` is not 0 for THIS descriptor. The design pass
     measured 0 for *records-free* cids, but `0x1050` now owns cls1 + cls2 +
     criteria rows, so that measurement may not transfer;
 (c) the row lookup `0x02243B9C(cid, param)` does not resolve to our row;
 (d) `CAVE_WU_ED` returns no candidates (mode `0x24`'s `can_synchro` gate
     rejecting, or the ov5 cave not resident on this path).

### Failure 2 (U3): never offered from hand
The gate I proved statically — cid in `0x0209BD20` **AND** a cls2 record — is
satisfied by the build (verify confirms both), yet **no offer appears**. So
membership + cls2 is NECESSARY but NOT SUFFICIENT: the missing piece is that the
battle-damage event evidently is not posted to HAND cards at all. Battle Fader's
trigger is *attack declaration*, Watapon's and Rose Fairy's is *added to hand* —
none of the list's members actually responds to "your monster dealt damage".
⇒ the assumption that a battle-damage event reaches a hand responder is
**FALSIFIED IN GAME**. This is the question the user deliberately deferred to a
duel rather than disassembly, and the duel answered it.

### Next: the savestates are the authoritative read
`.ml2` (before attack), `.ml3` (prompt open), `.ml4` (resolving). Parse rather
than reason from prose: read the resolver phase at `[0x0229AAFC+0x70]`, the param
from `0x02234E78(desc)`, and the candidate count `0x02243FE0(side, 0x1050, param)`
— then re-run that call under `scratch/thumbemu.py` with `fl = 0x0802` vs
`0x0002` to settle cause (a) offline.

## ✅ U4 ROOT-CAUSED OFFLINE — `scratch/wattuna_u4_probe.py`, 2026-09-21

Emulated `0x02243FE0(side, 0x1050, 0)` — the phase-`0x80` candidate probe — over
the user's own savestates. Reproducible on BOTH `.ml2` and `.ml4`:

| variant | count | set-code filter reached |
|---|---|---|
| **shipped** `h=CAVE_WU_ED`, mode `0x24` | aborts inside `can_synchro` | **NO** |
| `h=CAVE_WU_ED`, mode `0x04` | **2** | yes |
| **`h` = Aurora's STOCK `0x022430A1`, no cave at all** | **2** | yes |
| ditto with `fl = 0x0002` | **2** | yes |

Ruled IN as correct by the same run (so do not "fix" these):
* `CAVE_WU_ED` is **resident and byte-correct** in all three states — the cave was
  never the problem.
* The criteria row is live and exactly as written:
  `a=0x1050 b=0x0058 h=0x023A12B1 fl=0x0802`, and `0x02243B9C(0x1050, 0)`
  resolves to **row 71** — the lookup works.
* **THE WATT-ONLY FILTER IS CORRECT**, which answers the user's unverifiable
  test 4: side 0's Extra Deck holds `0x1179`×3, `0x2164`×3, `0x230F`, `0x2477`
  and the count is exactly **2** — only Wattchimera and Watthydra pass.

### ROOT CAUSE: the `0x20` mode bit I added — my "improvement" was the bug
`CAVE_WU_ED` cloned Aurora's handler with `movs r0,#4` → `movs r0,#0x24` to add
`can_synchro 0x02249540` on top of `is_synchro`, reasoning it would keep the
offer honest. But `synchro.procedure_picks_and_sends_hand_materials` already
records that **`can_synchro` only walks the 10 FIELD slots**. Wattuna's printed
materials may come from the HAND, and on the tested board the field-only dry run
returns "cannot summon" for every Extra-Deck candidate → count 0 → phase `0x80`
never advances to `0x7F` → **no picker, effect fizzles**, exactly as observed.

That looseness is *Formula Synchron's own native looseness*, in-game confirmed
via Steam Synchron, and the design pass had said so in plain words ("the offer
filter is slightly loose ... that is Formula's exact native looseness"). Adding
the bit contradicted the cited evidence.

### THE FIX, and it makes U4 PURE DATA
Point the criteria row's `h` at **Aurora's stock handler `0x022430A1`** and
**delete `CAVE_WU_ED` entirely**. The handler is cid-blind and takes the set code
from the row's own `b` field, so `b = 0x0058` is the whole Watt restriction.
⇒ no injected code anywhere in the module, and U4 becomes **puzzle-safe** like
the rest of the card. `fl` stays `0x0802` (proven equivalent to `0x0002` here;
keep the value taken from the proven Formula/Steam Synchron resolver path).

⚠️ `unproven` and NOT fixed by this: whether phase `0x7F`'s picker then actually
offers the HAND cell. The hand-material literal at `0x02249534` is in place, but
nothing has exercised it yet — the first test never reached the picker.

## U3: STOPPING ON THE TWO-STRIKE RULE (2026-09-21)

Three hypotheses about U3's mechanism have now been falsified:
1. the Main-Phase hand-SS menu (`0x0224C026` trampoline) — wrong route;
2. the cls2 `+0C` condition as the per-card trigger discriminator — it is shared
   verbatim by five cards with five different printed triggers;
3. **"membership of `0x0209BD20` + a cls2 record is sufficient"** — the build
   satisfies both and the offer still never appears (in-game, user 2026-09-21).

Per CLAUDE.md that is the point to stop writing code. What the last read DID
establish, for the next session:

* The hand-responder predicate `0x021D3828` has exactly **two BL callers and no
  u32 references**: `0x021D4096` and `0x021E51A0`.
* `0x021E51A0` sits in the function entered at **`0x021E50DC`** — immediately
  adjacent to the "You can" optional-trigger literal `0x021E51E5` — and is gated
  by `[0x0229DD94 + 0x34] == 0`. ⚠️ `0x0229DD94` is the **picker/UI state**
  struct, NOT the phase struct `0x0229DD14`; I guessed "turn player" from the
  offset and the literal proved otherwise, so resolve these pools, never infer.
* `0x021D4096` reads: `bl 0x021D3828 ; bne skip ; bl 0x0224AF7C ; bne skip ;
  bl 0x021CF834` — i.e. the predicate is a KEEP test applied to a descriptor that
  **already exists**. So the predicate is a filter, not the enumerator.

⇒ The open question is now sharp and narrow: **does the battle-damage event ever
create a responder descriptor for a card sitting in the HAND?** Everything in
`0x0209BD20` responds to being attacked (Gorz `0x199E`, Battle Fader `0x21A9`,
Tragoedia `0x1F99`), to being added to hand (Watapon `0x17CC`, Rose Fairy
`0x21B0`), or to a destruction/negation event. **Not one member responds to
"my own monster dealt damage"**, so there may be no native analogue in this
engine for U3 as printed.

### The decision that belongs to the user, not to another guess
* **(a)** One GDB session: breakpoint `0x021D3828` and `0x021D4096` during a
  Damage Step in which your monster deals damage, and see whether a descriptor
  for the hand card is built at all. Settles it by measurement.
* **(b)** Accept a timing deviation and use the route that is already proven and
  shipped five times over: the shared hand-SS trampoline (`CAVE_TG_SSTABLE`
  `0x0239F240` has **2 free rows**, measured this session) with a condition stub
  querying a turn-log node stamped when your monster inflicts battle damage.
  Wattuna then becomes summonable from hand in **Main Phase 2** after a damaging
  attack instead of during the Damage Step.

## ✅ BUILD 2 TEST — U4 ALMOST WORKS; ROOT CAUSE OF THE LAST FAILURE FOUND

User 2026-09-21, exact words: *"1. Confirmed  2. Confirmed  3. see .ml5 does not
let me choose"*, then *"4. Confirmed"*, and on my reading being wrong:
**"It doesn't let me pick anything. Hand or field."** (I had guessed hand-only.)

### Confirmed working in game (build 2)
* The **material picker now opens** — the `mode 0x24` fix landed.
* **TEST 4 CONFIRMED IN GAME**: the Extra-Deck list shows *only* Wattchimera and
  Watthydra. The Watt-only criteria row + Aurora's stock handler is correct on
  hardware, matching the offline measurement.
* The Extra-Deck target is really chosen: `.ml5` summon record reads
  `cid=0x2477` (Watthydra), `step=2`, resolver phase `0x7D`, picker mode `8`.

### The failure: NOTHING is selectable as material, field or hand
`.ml5` board (read from the player struct, `0x0229AC94 + side*0xB3C + 0x34`):
`side 0 zone 2 = 0x00801050` → **Wattuna IS on the field**; hand =
`0x21D0, 0x1B5A, 0x1050, 0x15A1, 0x2263` (a 2nd Wattuna + **Wattwoodpecker
`0x2263`, Lv3**). Target Watthydra is Lv7 = Wattuna 4 + Wattwoodpecker 3, so the
intended play was set up correctly. Validator sweep over every kind: **zero
selectable cells anywhere** (`kind 0x02` = monster field, `0x0B` = hand).

### ❌ RULED OUT: the forced-material slot
`0x0229AC7C = 0x00000002`, which decodes as inst_idx 1 / side 0 = **Wattuna's own
packed ref** — i.e. it is set CORRECTLY. A/B over the savestate with it zeroed,
left as captured, and re-set: **all three traces are byte-identical, 2740
instructions, same verdict**. So `synchro.effect_summon_forced_material_global`
(the Accel Synchro Stardust C3 symptom, whose KB wording — "the material cursor
can select nothing" — matches this failure verbatim) is **NOT the cause here**.
Measured, not assumed.

### ✅ ROOT CAUSE: Wattuna is not a "Watt", and the Watt Synchros demand one
Traced the validator `0x02249AFC(0, 2, 0)` rejecting Wattuna on the field:

```
0x02249D12  bl 0x022485B4        ; OUTER Synchro-material predicate
0x02249D16  cmp r0,#0
0x02249D1A  b  0x02249B20        ; TAKEN -- returned 0 -> reject -> return 0 @0x02249E44
```
and inside that predicate the verdict comes from the leaf
`0x02248A40: adds r0,r4,#0 ; bl 0x02023EF4 ; pop`, fronted by the shared binary
search `0x02022E14`. That thunk is:

```
has_set_code ptr table 0x0209D0D8[0x58] = 0x02023EF5
0x02023EF4:  ldr r1,=0x0209CBEA   ; THE WATT CID LIST
             ldr r3,=0x02022E15   ; bsearch
             movs r2,#0x16        ; 22 entries
             bx  r3
```
`0x58` is the ONLY set code using that thunk. So the leaf is literally
**`is this card a "Watt"?`**, and both Extra-Deck targets demand it:
Watthydra and Wattchimera are each *"1 **Watt** Tuner + 1 or more non-Tuner
Thunder-Type monsters"*. Wattuna is absent from `0x0209CBEA`, so **no legal Tuner
exists for either target and every cell is correctly refused.**

### ⚠️ CORRECTION — PART F IS NOT SEVERABLE
This file and the module docstring both claimed the Watt set-code membership was
"severable, flavour-only" and "does not affect U4 -- the criteria row's 0x58 tests
the CANDIDATE Synchro, not Wattuna." **That is wrong.** The row's `0x58` filters
the candidate *Synchro*; this leaf filters the *material*. PART F is load-bearing
for U4 and must ship with it.

⇒ FIX: add `0x1050` to `0x0209CBEA`. The list is 22/22 with **no phantom**, so it
needs the `patch_psi_reflector` relocate-and-bump — repoint the pool word at
`0x02023EFC` to a 23-entry copy and bump `movs r2,#0x16` → `#0x17` at
`0x02023EF8`.

## ✅ BUILD 3 — PART F shipped as a DISPLACEMENT; fix proven offline

`verify(): 26/26 PASS`. `check_allocations --emit`: no collisions (266 ov5 slots,
276 phantom claims — **no cave claimed by this module at all**).

```
F Watt set code @0x0209CBEA (x22, count/geometry unchanged):
    displaced 0x2481, inserted 0x1050 @1
```

### Why a displacement rather than a grow
The Watt list is **boxed in with zero slack on both sides** (measured 2026-09-21):
Dragunity `0x4A` (`0x0209CBC0` ×21) ends exactly at `0x0209CBEA`, and Karakuri
`0x5D` (`0x0209CC16` ×22) begins exactly where the Watt list ends. Relocation
targets were considered and rejected:
* **ARM9 slack** — the three zero runs near the set-code region are all unsafe:
  `0x0209D4B5` is the unused TAIL OF THE PTR TABLE `0x0209D0D8`; `0x020AC074`
  (72 B) is a hole *inside a pointer table* (neighbours decode as `0x02049E24`
  etc.); `0x020AE940` (212 B) has 60 pointers landing nearby and the string
  `"rom\0"` immediately after.
* **ov5 cave** — would make `has_set_code(·,0x58)` read evicted memory in a
  puzzle, breaking the archetype for **all 22 stock Watts**, not just ours.
  (`patch_psi_reflector` gets away with this only because its stock `0x6E` list
  is four phantoms.)

⇒ **USER DECISION 2026-09-21: "Wattkey, Wattcannon, wattcine and wattcastle can
lose membership."** Took **Wattkey `0x2481`**. All four are Watt Spell/Traps whose
own membership nothing reads — every "Watt" consumer in this ROM looks for Watt
*monsters* (Wattcobra's filter explicitly ANDs in the card_intid monster bit),
and none of the four refers to itself. The thunk's list pointer, count immediate
and bsearch pointer are all left stock; only the 22 list entries change.
⇒ The whole card stays **pure data and puzzle-safe**.

### The fix is PROVEN, not hoped
Re-ran the material validator `0x02249AFC` over the user's `.ml5` with the list
change applied **in emulator memory only**:

| Watt list | selectable cells |
|---|---|
| build 2 (stock) | **NONE anywhere** |
| build 3 (`0x2481` → `0x1050`) | **side 0 field idx0 cid=0x1050 → 2048** |

`2048` is the same "legal Tuner" return the KB records for
`synchro.effect_summon_forced_material_global`. The first-pick blocker is cleared;
once Wattuna is picked, `picks == 1` makes the hand legal and Wattwoodpecker
`0x2263` (Lv3) completes Lv7 for Watthydra.

⚠️ Still `unproven`: the second (hand) pick itself has never been exercised.

## U3 REFRAMED BY THE USER 2026-09-21 — it is the WATAPON trigger, not the printed one

User's words: *"When I test U3 make sure build with wattcobra. The specific
timing I need to test is that wattcobra activates, and then adds tuna and then
tuna activates, summoning itself. If that gives you the window when the effect
activates. It's the same window cobra activates in."*

⚠️ **I had misread the earlier instruction.** When the user said "using
watapon/rose-fairy" I took it as *use their record shape*; they meant **use their
TRIGGER**. Watapon `0x17CC` and Rose Fairy `0x21B0` are both *"when this card is
added from your Deck to your hand by a card effect: Special Summon it"* — which
is exactly the Cobra→Tuna line. The activation window is the one Wattcobra
already fires in (the LIST A direct-attack damage window).

**The build may already satisfy this and it has never been tested.** Wattuna's
cls2 record is Watapon's verbatim (`+04 0x02206ABD`, `+0C 0x021F0A39`,
`+10 0x021E51E5`, `+14 0`) and it is in the hand-responder list `0x0209BD20`.
In-game test 1 item 6 exercised a DIFFERENT thing — Wattuna sitting in hand while
a Watt dealt damage — never Wattuna being *added* to the hand.

⇒ So the earlier conclusion "the battle-damage event is not posted to hand cards"
remains true for the PRINTED timing, but is **not** the question the user wants
answered. Do not spend a GDB session on it until the Watapon path is tested.

## ✅ BUILD 4 — two-card test ROM `rom_wattuna_cobra.nds`

`_build_wattuna_cobra.py` (repo root): patch_wattcobra from stock, then
patch_wattuna on top, then verify BOTH positionally.

* **patch_wattcobra: `RESULT: PASS`** — including `A3 Fane 0x2069 is a real card
  again` and `Watt set-code table holds the donor and is stock`. PART F displaces
  only Wattkey `0x2481`; Wattkid `0x0FD3` stays at index 0 and the count stays
  22, so Wattcobra's `assert_donor_is_a_watt` is unaffected.
* **patch_wattuna: 26/26 PASS.**
* Composition checked before building: the two modules share **no phantom in any
  pool** (Cobra: `0x0EB3 0x0EC0 0x0E14 0x2347`; Wattuna: `0x1129 0x1DB6 0x1147
  0x0EB9 0x0EC3 0x0E68 0x2481`). Cobra owns `CAVE_WATT_FILTER`/`WRAPPER`;
  Wattuna claims no cave.
* **Cobra can now search Tuna**, which is what makes the test line possible:
  Cobra's filter is `has_set_code(cid, 0x58) AND is_monster AND DEF <= 1500`, and
  Wattuna is now a Watt (PART F), is a monster, and has DEF 700.

## BUILD 4 IN-GAME TEST — user 2026-09-21

User's exact words:

> okay for U4 still works. however when watttuna is on the field with nothing
> else it lets me synchro summon with a material from the hand.
>
> For U3, watttuna does not activate when wattcobra attacks directly.

Disambiguated by the user before any investigation:
* the hand-material permission is **ALWAYS ON**, not only during U4;
* on the U3 line Cobra **did** offer and add Wattuna — *"Yes — added, then
  nothing"* — so the search half works and only the self-Summon fails.

### ✅ U4 IS IN-GAME CONFIRMED (with the deviation below)
Direct attack → prompt → material picker → Wattuna selectable → Watt Synchro.
The `mode 0x24` fix and the PART F Watt membership both landed. Wattcobra still
searches correctly in the same ROM.

### ❌ NEW DEFECT 1: the hand-material grant is UNCONDITIONAL
PART E grants hand materials by retargeting the gate literal `0x02249534`
(`0x0E66` → `0x1050`). `synchro.native_hand_material_mode`'s gate `0x022494EC` is
a **static cid test on the FIRST pick** — it has no idea which effect is running.
So Wattuna permanently carries Eccentric Boy's property: in ANY Synchro Summon
where she is the first material (including an ordinary Main-Phase Extra-Deck
summon with nothing else on the field) a hand monster becomes legal material.
The printed card allows hand materials ONLY as part of U4's Tribute effect.

⚠️ **There is no data-only way to scope this.** The gate is consulted by the
per-slot validator (`bl` @`0x02249B12`) and by `level_sum` (@`0x02249924`) on
every Synchro Summon; the permission is either on for the cid or off for it.
Options are therefore: (a) revert the literal → U4 becomes FIELD-ONLY materials;
(b) hook the gate in ov5 and AND in "an effect-driven summon is in progress"
(candidate discriminator: the forced-material slot `0x0229AC7C != 0`, which the
procedure zeroes at `0x022634E0` and only the shared resolver's phase `0x7D`
sets) — costs injected code, hence normal-duel-only, and must compose with
`patch_revolution_synchron`, which already owns the `BL` @`0x02249B12`.

### ❌ DEFECT 2: U3 still does not fire, even on the WATAPON path
Cobra searched and added Wattuna; she never offered to Special Summon herself.
So `0x0209BD20` membership + a cls2 record + Watapon's own condition
`0x021F0A39` is STILL not sufficient — the fourth falsified U3 hypothesis.

⇒ Next step is the one CLAUDE.md's two-strike rule prescribes and I have not yet
done for this trigger: **enumerate Watapon `0x17CC` and Rose Fairy `0x21B0`'s
COMPLETE footprints with `donor_scan` and diff them against Wattuna's**, instead
of reasoning about which list ought to matter.

## ✅✅ U3 ROOT-CAUSED — "self-SS when added to hand" is a HARDCODED 4-cid CHAIN

The diff the two-strike rule asked for paid off. `donor_scan 0x21B0` (Rose Fairy)
shows her ENTIRE footprint is **cls2 record[521] + the hand-responder list entry
`arm9:0x0209BD52`** — byte-for-byte the same shape Wattuna now has, with an
identical cls2 record. So the difference could not be data, and it is not:

**`ov3:0x021C73B6..0x021C73E2`, inside the relocation ("card moved to hand")
path**, is an ordered per-cid chain on the moved card's 14-bit cid
(`(w << 0x12) >> 0x12`), matching → `0x021C73EE`, missing → `0x021C7412`:

```
021C73B8  ldr r2,=0x20D3        ; pool 0x021C7470
021C73BE  cmp r0,r2
021C73C0  bhi 0x021C73CC        ; r0 > 0x20D3
021C73C2  bhs 0x021C73E4        ; r0 == 0x20D3   -> R-Genex Oracle
021C73C4  ldr r1,=0x17CC        ; pool 0x021C7474   (r0 < 0x20D3 arm)
021C73C6  cmp r0,r1 ; beq       ; -> Watapon
021C73CA  b   0x021C7412        ; else NO MATCH
021C73CC  adds r1,r2,#0 ; adds r1,#0xDD   ; = 0x21B0
          cmp r0,r1 ; bhi 0x021C73DC
          adds r2,#0xDD ; cmp r0,r2 ; beq  ; -> Rose Fairy
021C73DC  ldr r1,=0x224B        ; pool 0x021C7478
          cmp r0,r1 ; beq       ; -> Blackwing - Breeze the Zephyr
```

Membership = **{Watapon `0x17CC`, R-Genex Oracle `0x20D3`, Rose Fairy `0x21B0`,
Blackwing - Breeze the Zephyr `0x224B`}** — precisely the four "when this card is
added from your Deck to your hand by a card effect: Special Summon it" cards.

⚠️ **Rose Fairy `0x21B0` is DERIVED as `0x20D3 + 0xDD`** (`adds r2,#0xDD`), the
`thumb.stack_based_switch` footgun: her cid is never stored, which is why
`donor_scan` reports no reference and why every data-side search for this
mechanism came up empty across four hypotheses.

### What this means for U3
Membership of `0x0209BD20` + a cls2 record was NEVER going to be enough; the
event only reaches a hand card whose cid is in this chain. **U3 is not
implementable as pure data.**

Slot analysis for a fix (the chain is ORDERED, so position matters):
* `0x1050 < 0x20D3`, so Wattuna can only ever be tested in the **`r0 < 0x20D3`
  arm**, which compares against exactly one literal: `0x021C7474` = Watapon.
* Repointing `0x021C7470` is out — that word is used BOTH as R-Genex Oracle and
  as the base for Rose Fairy's `+0xDD`, so it would move two cards at once.
* `0x021C7478` (Breeze) is in the `r0 > 0x21B0` arm and unreachable for `0x1050`.

⇒ The only single-word edit that works is **`0x021C7474`: `0x17CC` → `0x1050`,
which costs Watapon its self-Summon.** Otherwise the arm needs a second compare,
i.e. injected code — and that must be hosted in **ov3, not ov5**: this is the
shared relocation path that runs for EVERY card moved to hand, so an evicted ov5
stub in a puzzle would be a branch into garbage, not a silent miss.

## Ruled Out

* **"U3 can be plain LIST A / LIST B membership."** Both lists are keyed on the
  **attacker's** cid — `0x021D0212 ldr r0,[sp,#0x18] ; movs r1,#0xA ; ldrsh r0,[r0,r1]`
  gives the attacker, then a sorted binary search via `bl 0x02022E14`. Wattuna sits
  in the HAND while some other monster attacks, so it can never be the search key.
  U3 needs hand-responder wiring (Battle Fader), not list membership.
* **"Wattkyuki can share this session."** Out of scope by the user's decision and
  by CLAUDE.md's one-patch rule. It additionally needs an Extra-Deck Synchro donor
  and a Watt set-code grow before any clause exists.
* **"A clean Thunder Normal Monster donor exists."** `donor_scan --free --race
  Thunder` returns 0 rows.
* **❌ "U4 = clone Eccentric Boy `0x2184`'s record." FALSIFIED this session.**
  This was the plan's PART E assumption and it is wrong: **Eccentric Boy owns no
  cls record at all.** `donor_scan 0x2184` reports `VERDICT: ENTANGLED` with 7
  binding occurrences and **not one cls0/cls1/cls2/cls3 row**:
  ```
  unclassified:      ov3:0x0226FADE/u16, ov3:0x021B0A40/u32, ov3:0x021ED0F0/u32,
                     ov3:0x0224A0F0/u32, ov3:0x022669DC/u32
  in Synchro material predicates: ov3:0x02248534/u32, ov3:0x02249538/u32
  ```
  Disassembling the loaders this session shows what those are: `0x021B0A40` and
  `0x021ED0F0` are **attached-effect node keys** (passed as r2 to the two node
  walkers `0x021A1430` / `0x021A0950`, per the KB's node system); `0x0224A0F0` is
  a cid compare via `bl 0x021AC9D0`; and `0x022669DC` is loaded at `0x02266760`
  by the classic `ldr r0,[pc] ; str r0,[sp,#X] ; adds r0,#N ; str r0,[sp,#X]`
  sequence — i.e. a **stack-based per-cid switch**, the exact
  `thumb.stack_based_switch_footgun` shape. So Eccentric Boy's "immediately
  Synchro Summon" is **per-cid code plus a node**, with no data record to
  transplant. Superseded by the shared resolver `0x02249EC0` above.
  *(Its one useful contribution stands: the hand-material gate literal at
  `0x02249538`, which is why `0x02249534`'s dead `0x0E66` slot is still PART E's
  material half.)*

## Open Questions

1. ~~The battle-response ARM9 list~~ — **CLOSED**, see Confirmed above:
   list `0x0209BD20` x38, thunk `0x02023574`, count imm `0x02023578`, phantom
   `0x0E68` free at index 0.
2. ~~What Battle Fader's two ov3 tables gate~~ — **CLOSED**: they are not tables.
   Both are halves of the pointer `0x021F21A9` inside the ignition-condition
   registry. PART C = cls2 record + ARM9 list `0x0209BD20` only.
3. ~~PART E's record / which table~~ — **CLOSED**: cls1, `+04 = 0x02249EC1`; the
   phase protocol is proven on the battle-damage path via `0x02207FCC`.
4. ~~The criteria row / Watt-only filter~~ — **CLOSED**: Aurora `0x022430A0` clone
   with `movs r0,#0x24`; row `{D, 0x0058, CAVE_WU_ED|1, 0x0802}`. Zone is
   **PROVEN** to be the Extra Deck (`0x0223BE40` pool: `0x0229ACAC` ED count,
   `0x04E4` ED array, zone id `0xC`).
5. ~~Tribute vs Synchro Summon~~ — **ANSWERED, and it is a real deviation
   needing a user ruling**: a genuine Synchro Summon is posted ⇒ **T.G. Hyper
   Librarian over-draws**; and materials are Synchro Material, not Tributes, so
   Tribute-responders stay silent. See Confirmed (e).
6. **U2's two HOPT latches** — U3 and U4 need *separate* once-per-turn nodes
   (`dispatch.turnlog_once_per_turn_pair`, kind 1 and kind 2, as Dragunity Remus
   does for C3a vs C4).
7. **`fl = 0x0802` vs `0x0002`** on the cloned Aurora handler — `unproven`.
8. **U3's trigger condition.** The gate (list + cls2) is proven, but the condition
   that means "your monster inflicted battle damage to your opponent" is not yet
   designed. ⚠️ If U3 also ends up LIST-A-driven it would want a cls1 row on the
   same cid as U4 — `find_event_handler` returns the leftmost, so that needs an
   ov5 splitter (Dragunity Remus C3a `CAVE_DR_C3_COND` precedent), not a second
   record. Current design avoids this (U3 = cls2), but re-check when built.

## Next Experiment

All offline; no emulator, no duel.

1. **Settle `fl` (risk #7).** Run `0x02243FE0(side, 0x1050, 0)` under
   `scratch/thumbemu.py` over a duel savestate with the `CAVE_WU_ED` clone
   injected, once with `fl = 0x00000802` and once with `0x00000002`; assert the
   candidate count equals the number of Watt Synchros in the Extra Deck in both.
2. **U3's condition** (open question 8). Record shape is settled; two reads left:
   (a) map the battle-context struct at **`0x02298AD8`** — `[+2]` is already known
   to be the direct-attack flag (from the LIST A gate `0x021D020A`), so read the
   whole function `0x021D020A..0x021D0256` and the damage applier for the fields
   meaning *damage amount* and *recipient side*; (b) determine which events reach
   a `0x0209BD20` member, by disassembling the `0x24`-stride walk at
   `0x021D3048..0x021D30A6` (it compares `[r5+0xC] == r6` and `[r5+5]` = table
   selector) — this decides whether Wattuna would also be offered on unwanted
   events, as Watapon and Rose Fairy respond to "added to hand" from the same list.
3. **Pick the phantoms**: one cls1 row and one criteria row nearest `0x1050`'s
   sorted position, re-proven against `card_prop` absence in BOTH the stock and
   chained images (never `scratch/cid_to_name.json`).

## ⚠️ 2026-10-05 — hand-material gate literal REASSIGNED to Mara of the Nordic Alfar
By user decision ("Take the literal", Mara session 2026-10-05), the gate literal
0x02249534 (0x0E66) now belongs to `patch_mara` (donor Happy Lover 0x106C). The
check_allocations claim `("hand_material_gate", 0x0E66, ...)` moved from wattuna to
mara. Wattuna's PART E "the hand material is one word" no longer has a word: U4's
hand material needs a new design (e.g. an ov5 hook on the gate's callers --
level_sum `bl` @0x02249924 and the validator after Revolution's H1 @0x02249B16;
both sites were stock in the chain on 2026-10-05). See notes/mara-findings.md.

## 2026-10-05 SESSION — U3 fix (scope: U3 only; U1/U4 must not regress)

Text re-sourced this session from `scratch/ygoprodeck_cache.json` (id 10113611) — matches the quote at the top.
(Note: the Grep tool returns NO match on that 20 MB single-line file; read it with Python `bytes.find`.)

### Confirmed this session (scratch/wattuna_u3_dis.py, stock rom.nds vs rom_all_patches.nds)
* The cid chain `0x021C73B6..0x021C73E3` lives in the **Deck->hand mover `0x021C72CC`**
  (event_queue.yaml calls it that). It is **byte-identical stock vs chain**; literals
  `0x021C7470=0x20D3`, `0x021C7474=0x17CC`, `0x021C7478=0x224B`, `0x021C747C=0x1A43` (Puppet King,
  used @0x021C7422 — do not touch). Match -> `0x021C73EE` posts event code `0x4B` via `bl 0x021D3168`.
  The only chain-ROM diff in 0x021C7380..0x021C7480 is Dark Law's log BL @0x021C743E (unrelated).
* r2 = 0x20D3 is live from 0x021C73B8; R-Genex Oracle (== 0x20D3) goes to 0x021C73E4 (extra check
  `bl 0x02023BE8`), not straight to match.
* cls2 condition `0x021F0A38` is stock in chain. Its leading cid chain (0x1D3C/0x17C9/0x18EC/0x2176/0x2352)
  only SKIPS the in-hand test for those cards; 0x1050 takes the generic path:
  in-hand `0x021A25A0` -> `0x021F0384` (`0x021F0114`, can-SS `0x021B9EC0`) -> `0x021BA440`
  (`0x021B9FC0`, SS gate `0x021BA258`) -> no-duplicate walk over pending links (list `0x0209BD20`).
  No per-cid gate for 0x1050 in any of them.
* => With chain membership, Wattuna's footprint == Rose Fairy's (cls2 + 0x0209BD20 + chain).

### Design (no ov3/ov5 space needed, keeps Watapon)
Rewrite `0x021C73BE..0x021C73E3` (38 B) as a linear compare list (36 B + 1 nop):
`cmp r0,r2; beq ORACLE` / `ldr r1,=0x17CC (same pool word); cmp; beq MATCH` /
`adds r1,r2,#0; adds r1,#0xDD; cmp; beq MATCH` (Rose Fairy) / `ldr r1,=0x224B; cmp; beq MATCH` /
`movs r1,#0x83; lsls r1,r1,#5; subs r1,#0x10 (=0x1050); cmp; beq MATCH` / `b NOMATCH`.
Pure data, puzzle-safe (ov3 is resident in every mode).

### PART G written + PROVEN offline (2026-10-05)
`patch_wattuna.HANDCHAIN_NEW` @0x021C73BE (38 B, assert_thumb1_only, idempotent, asserts stock bytes first).
`scratch/wattuna_u3_equiv.py` runs stock vs new chain under thumbemu for ALL 0x4000 cids (r2=0x20D3):
```
stock MATCH: 0x17cc 0x21b0 0x224b   ORACLE: 0x20d3
new   MATCH: 0x1050 0x17cc 0x21b0 0x224b   ORACLE: 0x20d3
PASS: only 0x1050 changed (NOMATCH -> MATCH)
```
ASSUMED (not proven): `[0x0229C294+0x78]` bit 0 (mover skips its posts, bne @0x021C73B4) is clear when
Wattcobra's resolver 0x02207EF4 adds the card. Watapon searched by any stock searcher depends on the same.
Not in scope / untouched: PART E still writes 0x02249534, which Mara now owns -> must be redesigned before ship.

## ✅ BUILD 5 — `rom_wattuna_cobra.nds` (Cobra + Wattuna incl. PART G) — AWAITING IN-GAME TEST
`_build_wattuna_cobra.py` 2026-10-05: wattcobra RESULT PASS, wattuna verify 28/28 PASS.
sha256 `6009977ad7c29f3816beb53282d3376c093a93499e1c56bbbdad6d87e4eb3109`.
KB: `event.deck_to_hand_self_ss_cid_chain` VERIFIED (author_facts --check 569 PASS / 0 FAIL).
Single-card ROM only — NOT in steps.STEPS (and PART E's literal now collides with Mara in the chain).

## Next Experiment
In-game test of build 5 (U3): Wattcobra direct attack -> add Wattuna -> Wattuna offers to SS itself.
Regression: Watapon / Rose Fairy still self-SS when searched. If U3 is still silent: savestate right
after the add; check [0x0229C294+0x78] bit 0 and whether event 0x4B was posted.

## ❌ BUILD 5 IN-GAME TEST — user 2026-10-05
User: "It didn't fire, see .ml3" / "1. Wattcobra added tuna, 2. After wattcobra added tuna, but I also had a tuna in my hand which also didn't fire."
Reading: Cobra's add WORKS; the ADDED Wattuna never offered to SS itself. .ml3 = just after the add.
(The pre-existing hand Wattuna staying silent is expected under the Watapon trigger.)

### .ml3 offline read (scratch/wattuna_u3_ml3.py, wattuna_u3_post_emu.py) — 2026-10-05
* PART G IS RESIDENT in RAM (.ml2 and .ml3). [0x0229C294+0x78] = 0 in both (flag value AT the add unproven). No pending descriptors.
* CORRECTION: 0x4B is NOT an event code. The posted word is side<<31 | 0x4B<<16 | cid, i.e. desc[+3] zone = 0x0B (HAND),
  desc[+5] selector = 2 (cls2). (0x80000000 @0x021C73F2 is only the side MASK.)
* Emulating the poster 0x021D3168(0x004B1050, 0, 0) on .ml3: the offer gate 0x021EDA08 ACCEPTS (falls to 0x021D31D4)
  and execution enters the enqueue routine 0x021D2FC4 (emulator stops at BLX ARM 0x0214C1D4 @0x021D30F2).
  Gate path includes 0x021D3918 = bsearch(cid, ov3 list 0x0226EF68 x0x1D) + cid chain — Watapon is in neither, so not the discriminator.
* => IF the mover posts, Wattuna's descriptor is enqueued. Remaining: (a) the post never happens on Cobra's add, or
  (b) enqueued then dropped (cls2 cond 0x021F0A38 at offer time / miss-timing). TWO-STRIKE: stop patching, measure.

## Next Experiment (2026-10-05) — ONE GDB session: scratch/gdb_wattuna_u3_trace.py
Breakpoints split (a) no post vs (b) post dropped, and name the failing check of cls2 cond 0x021F0A38
(exits: 0x021F0A76 not-in-hand / 0x021F0AA8 can-SS / 0x021F0AB6 SS gate / 0x021F0AE6 responder pending / 0x021F0AF0 PASS).
Preflight: build-5 ROM, active normal duel, Cobra able to attack directly, Wattuna in Deck, attack not yet declared.

## ✅ GDB RESULT 2026-10-05 (scratch/gdb_wattuna_u3_trace.txt) — case (a): the mover does NOT post
At Cobra's add, hit F @0x021C73AE read [0x0229C294+0x78] = 0xB (bit 0 SET; was 0x0 at preflight) ->
 skips the whole cid chain to the move-log call (code 0x1C, bl 0x022391CC @0x021C743E).
K/M/N never hit. (Stub died right after hit #4, so later zeros are not evidence; the flag read is.)
=> ASSUMED item FALSIFIED. During an effect's resolution the add is only LOGGED; hypothesis: the
'when added' trigger is posted later from the log by a DEFERRED poster with its own cid check. Next: find it.

(Fix for the entry above: the skip is `ldr r1,[r0,#0x78] ; lsls r1,r1,#0x1f ; bne 0x021C743A` @0x021C73B0..B4.)

### Second Watapon site FOUND — 0x021D0E1A..0x021D0E61 (stock == chain), static only
ov3 u32 scan: Watapon 0x17CC is stored only at 0x021C7474 (mover) + its cls2 row; Oracle/Breeze are also at
0x021D1010/0x021D1014 and Oracle at 0x021D0CA8 — loaded by a STACK-BASED switch in the function holding the
draw handler (move-log 0x1B @0x021D0C3A). Stack values set @0x021D0B20..0x021D0B6A:
  [sp+0xA8] = 0x188C-0xC0 = 0x17CC Watapon -> 0x021D0F04
  [sp+0xB0]/[sp+0xAC] = 0x20D3+0xDD = 0x21B0 Rose Fairy -> 0x021D0F04
  pool 0x021D1014 = 0x224B Breeze -> 0x021D0F04 ; pool 0x021D1010 = 0x20D3 Oracle -> 0x021D0EFA (extra check, then 0x0F04)
  [sp+0xA4] = 0x123B+0x66 = 0x12A1 -> 0x021D0E62 ; pool 0x021D100C = 0x1549 -> 0x021D0EC6 ; [sp+0x9C/0xA0] = 0x20D3-0x83 = 0x2050 -> 0x021D0F34 (reads r0 = cid)
  0x1050 lands in the <0x1549 arm, which tests only 0x12A1 -> miss (0x021D0F60).
⚠️ 0x021D0F04 ALSO requires [sp+8] != 0 AND [0x0229C294+0x78] bit 0 CLEAR (0x021D0F0A..0x021D0F10).
So this is NOT obviously the deferred consumer of a skipped mover post — it may be the DRAW path (Watapon drawn
by effect). What sets/clears the flag is still UNKNOWN (KB lists it as open).

### Open after the GDB run
1. Was hit F (flag 0xB) the REAL add, or an engine pre-run of Cobra's resolution? The stub died after 4 hits,
   so a later real add (flag clear) was never observed. Hits came in order P(Cobra cls1 post) -> G -> H -> F.
2. What did the game do after the stub died (breakpoints were left inserted)?

## Next Experiment (probe #2): scratch/gdb_wattuna_u3_trace2.py -> scratch/gdb_wattuna_u3_trace2.txt
E mover entry / F flag / M,N chain / S 0x021D0E22 2nd-site switch / T 0x021D0F04 / C,c5 cls2 cond. Capped hits. Restart melonDS first.

## ✅ PROBE #2 (scratch/gdb_wattuna_u3_trace2.txt) — the REAL add is flagged; root cause of U3 build 5
* Hit E: mover body 0x021C72D8 entered with side 0, cid 0x1050, flag [0x0229C294+0x78] = 0xB,
  lr = 0x022080FB = INSIDE Cobra's resolver 0x02207EF4 -> this IS the real add, not a pre-run.
* Hit F: flag still 0xB -> chain (PART G) skipped. Stub died right after F AGAIN (both probes):
  stopping at 0x021C73AE seems to kill the melonDS stub — don't put a breakpoint there next time.
* The second Watapon switch 0x021D0E1A lives in 0x021D0950 = the DRAW handler (callers 0x021D12FA,
  0x0220B6D4, 0x02253D7E) -> it is the "Watapon drawn" path, NOT a deferred poster for a searched add.
* The move log 0x022391CC has one known reader (Dimensional Inversion criteria) -> no deferred replay.

### [0x0229C294+0x78] bit 0 = "a battle is in progress" (static, 2026-10-05)
Writers (ov3 scan of every `ldr =0x0229C294` + `str [rX,#0x78]`): bit 0 is SET only @0x021BC176..7E
(`orrs #1`, same routine sets [0x0229DD94+4] = 4); CLEARED with bit 1 @0x021BC10A and @0x021BC1CE —
the latter (fn 0x021BC198) then clears the attacker's bit 25 in [0x0229ACD8 + side*0xB3C + slot*0x14]
(slot from battle context 0x02298AD8 +8) = end of the attack. Preflight (no attack) read 0x0; Cobra's
Damage-Step resolution read 0xB. => the mover deliberately posts NO hand self-SS trigger during a battle;
Watapon added by Cobra mid-battle would be silent natively too.

### Offline: the post is accepted even with the flag set
scratch/wattuna_u3_post_emu.py on .ml3 with [0x0229C294+0x78] forced 0x0 vs 0xB: identical trace,
offer gate 0x021EDA08 accepts, enqueue 0x021D2FC4 reached (.ml3 is post-battle, so battle-context
fields are not the live ones — partial evidence only).

### Fix design (NOT built — needs user OK on the deviation)
Rewrite 0x021C73AE..0x021C73E3 (54 B) so Wattuna is tested BEFORE the battle flag:
  cid = [r6]&0x3FFF ; if cid == 0x1050 -> MATCH ; flag test (pool 0x021C7454) -> 0x021C743A ;
  r2 = 0x20D3 ; linear chain (Oracle / Watapon / Rose Fairy / Breeze) ; b NOMATCH.   (~52 B)
Deviation: MATCH falls through to 0x021C7412, so for THIS add during battle the Puppet King
(0x021D36C0, 0x1A43) and 0x20D2 (0x021D3438) posters also run, which stock skips in battle.

## BUILD 6 — rom_wattuna_cobra.nds — AWAITING IN-GAME TEST
User approved the flag-bypass design + Puppet King / 0x20D2 deviation (2026-10-05, "yes").
PART G now = 0x021C73AE..0x021C73E3 (54 B): cid==0x1050 -> MATCH before the battle-flag test; rest stock.
scratch/wattuna_u3_equiv.py: all 0x4000 cids x flag {0, 0xB}: only 0x1050 changes (-> MATCH). Thumb-1 asserted.
Build: wattcobra PASS, wattuna verify 28/28. sha256 ccb1e279b2899b08c0263772a174137fab1aab5d665fcb7b6ecaf1b62a3a7642.
KB event.deck_to_hand_self_ss_cid_chain updated (flag = battle in progress), author_facts --check 569/0 FAIL.
NOTE: the gdb_wattuna_u3_trace*.py PARTG preflight signature matches BUILD 5 only — update before reuse.
Unproven: whether the engine actually PROMPTS a posted hand trigger inside the Damage Step.

## ✅ BUILD 6 IN-GAME — user 2026-10-05
User: "Okay it did fire. Except for when Wattgiraffe and Wattpheasant attacked directly" -> clarified as reading 1.
* U3 (Watapon-style: added from Deck by Cobra mid-battle -> SS itself): IN-GAME CONFIRMED BY USER 2026-10-05 (build 6, sha256 ccb1e279...).
* Wattuna sitting in hand while Wattgiraffe / Wattpheasant deal direct damage: NO offer. Expected — the PRINTED
  trigger ("if your monster inflicts battle damage") was never built. Not a regression.

## Open (for a next session, needs user decision)
* Printed U3 timing for an in-hand Wattuna. Precedent worth checking first: Gorz 0x199E / Tragoedia 0x1F99 ARE hand
  responders to battle damage, but for the player who TAKES it; Wattuna needs the attacker's side.
* U3 HOPT still deferred. PART E hand-material literal 0x02249534 still collides with Mara -> U4 redesign before ship.

## 2026-10-05 — U3 PRINTED timing (in-hand Wattuna, "your monster inflicts battle damage") — PART H
### Confirmed (static, this session)
* Battle-damage handler tail @0x021D079C..0x021D082A (logs move code 0x10 @0x021D0824). r7 = player TAKING
  damage, r6 = arg. cid-keyed posters: 0x021D07AC hand 0x021D36C0 Gorz 0x199E (direct only) /
  0x021D07B8 hand Tragoedia 0x1F99 / 0x021D07C4 FIELD 0x021D3438 phantom 0x0EC4 / 0x021D07D0 field
  Gellenduo 0x1B8C / 0x021D07DC GY 0x021D3648 Volcanic Counter 0x1CF7.
* Hand poster 0x021D36C0(side, cid, code, arg): side masked &1 (ands @0x021D36C8, lsls #31 @0x021D36D6),
  walks player+0x124 hand x count player+0xC, posts 0x4B<<16 | side<<31 | code<<25 | cid via 0x021D3168.
  No battle-flag test (Tragoedia uses it mid-battle).
* Tragoedia's cls2 record == Wattuna's (+04 0x02206ABD, +0C 0x021F0A39, +10 0x021E51E5) and it is in 0x0209BD20.
* 0x0EC4: no card_prop (donor_scan.cards), unclaimed in ledger, sole pool loader 0x021D07C4, region stock == chain.
### PART H (built into patch_wattuna)
0x021D07C4: `ldr r1,=0x1050 (pool 0x021D0834 0x0EC4->0x1050) ; adds r0,r7,#1 ; movs r2,#0x10 ; adds r3,r6,#0 ;
bl 0x021D36C0` (was adds r0,r7,#0 / bl 0x021D3438). Pure data in ov3, puzzle-safe.
### Deviation to put to the user (NOT yet ruled on)
Fires when battle damage is inflicted (Tragoedia timing), not "at the end of the Damage Step".

## BUILD 7 — rom_wattuna_cobra.nds (PART G + PART H) — AWAITING IN-GAME TEST
wattcobra PASS, wattuna verify 30/30. sha256 c682256015e5c712cbd7280a696da92191f4944ab376d60104f36090d138a0b8.
Ledger: (battle_damage_poster, 0x0EC4) + (mover_handss_chain, 0x1050) claimed for wattuna; --emit clean.
KB: event.battle_damage_cid_posters VERIFIED; 570 PASS / 0 FAIL.
Test: Wattuna in hand, Wattgiraffe/Wattpheasant (or any monster) inflicts battle damage -> offer.
Not built: HOPT (both U3 paths), the end-of-Damage-Step timing.

## ✅ BUILD 7 IN-GAME — user 2026-10-05: "Okay U3 is working now"
U3 (Watapon-style PART G + printed battle-damage PART H) IN-GAME CONFIRMED BY USER 2026-10-05, build 7 sha256 c6822560....
Timing deviation (offer at damage, not end of Damage Step): not separately ruled on — user reported U3 working.
NEXT (user): U3 once-per-turn, then U4.

## U3 HOPT — session start

* Rejected: +10 slot-4 stamp (Qoatlus C3 shape) — needs a timing_class_hook arm and the SHARED stub is 248/256 B (RESERVE 0x100); no room without editing shipped code.
* Chosen: Eva 0x160A shape — +0C CAVE_WU_U3COND (turn-log query kind 1 -> 0, else tail native 0x021F0A39),
  +10 native 0x021E51E5 kept, +14 CAVE_WU_U3COST (short-circuit 0x021D2BC8, post 0x021D2584(side,cid,1,0), return 1).
  Cost runs only after a Yes -> declining does not burn the OPT. ov5 -> duel-only (U3 now crashes nothing in puzzles?
  NO: in a puzzle +0C/+14 point at evicted ov5 -> do not use Wattuna in puzzles).
## BUILD 8 — U3 + HOPT — AWAITING IN-GAME TEST
ov5 CAVE_WU_U3COND 0x023A4840 (48 B) / CAVE_WU_U3COST 0x023A4870 (36 B); CAVE_FREE -> 0x023A48A0; ledger 378 slots, clean.
verify 32/32, wattcobra PASS. sha256 2a20441d172ed317e38b63e8ea13f4f20855b14f6fe6b86b0fc5e36cf9136b47.
Unproven: same-window double activation by TWO copies offered simultaneously (both +0C may run before either cost).

## ✅ BUILD 8 IN-GAME — user 2026-10-05: "HOPT works, U4 now"
U3 once-per-turn IN-GAME CONFIRMED BY USER 2026-10-05 (build 8 sha256 2a20441d...). (Two-copies-simultaneous case not separately reported.)

# ===== U4 SESSION (2026-10-05) =====

### U4 hand-material — design facts (2026-10-05, chain ROM)
* Gate 0x022494EC (leaf, bx lr): count [0x0229ABFC+0x7C] != 0, first-pick cid vs pool 0x02249534 (=0x106C Mara, chain),
  0x02249538 (0x2184 Eccentric Boy), 0x0224953C (0x2353 Parallel Gear); ret1 0x0224951C / ret0 0x02249520. In-place
  rewrite with a 0x1050 + forced-slot test needs ~18 B more than exists.
* Plan: 0x02249516  (pool 0x0224953C -> STUB|1; bx keeps LR), STUB tests 0x2353 itself, then
  cid == 0x1050 AND [0x0229AC7C] != 0 (forced-material slot = U4 in progress, measured 2 in .ml5). ~40 B, MUST be ov3
  (gate runs for every Synchro, also in puzzles).
* ❌ RULED OUT as ov3 space: 0x02228F4A (phantom 0x0E8F, '86 B free' in memory otn-phantom-leaf-ov3-space) is LIVE:
  @0x02228F44  FALLS THROUGH into it.
  The old scan ignored fall-through entry. Re-check every candidate for fall-through before use.

### U4 hand-material — design facts (2026-10-05, chain ROM)
* Gate 0x022494EC (leaf, bx lr): count [0x0229ABFC+0x7C] != 0, first-pick cid vs pool 0x02249534 (=0x106C Mara,
  chain), 0x02249538 (0x2184 Eccentric Boy), 0x0224953C (0x2353 Parallel Gear); ret1 0x0224951C / ret0 0x02249520.
  An in-place rewrite with a 0x1050 + forced-slot test needs ~18 B more than exists.
* Plan: 0x02249516 `ldr r0,=STUB ; bx r0` (pool 0x0224953C -> STUB|1; bx keeps LR). STUB tests 0x2353 itself, then
  cid == 0x1050 AND [0x0229AC7C] != 0 (forced-material slot = U4 in progress; measured 2 in .ml5). ~40 B. MUST be
  ov3: the gate runs for every Synchro material check, puzzles included.
* RULED OUT as ov3 space: 0x02228F4A (phantom 0x0E8F, "86 B free" in memory otn-phantom-leaf-ov3-space) is LIVE.
  @0x02228F44 `adds r0,r0,#4` (= 0x1DA2 Arcana Force VII - The Chariot) `; cmp r5,r0 ; bne 0x02228FAC` FALLS
  THROUGH into it. The old scan ignored fall-through entry: re-check every candidate for it.

### Confirmed this session for U4 (static)
* Forced-material slot 0x0229AC7C: shared resolver stores desc[+0xC] @0x0224A094 only while pick count
  [0x0229ABFC+0x7C] == 0, right before `bl 0x02263494`; procedure init zeroes it with the pick count @0x022634E0.
* ov3 dead leaf 0x021BB288 (phantom 0x1433, 64 B): entered only via `cmp r4,=0x1433 ; bne 0x021BB2C8`
  @0x021BB282..86; scratch/ov3_leaf_check.py: no inbound branch/BL/pointer (stock + chain), no card_prop,
  unclaimed. 0x0224F2FA (0x0E9E) also dead-shaped but 0x0E9E is claimed by thunder_sea_horse (cls2) -> left.
* cls1 +14 = slot5 (target declaration), run by the activation machine after the Yes, done-flag desc[+8];
  Kuribandit ships a cls1 +14 in-game -> U4 OPT stamp goes there.
### BUILD 9 — rom_wattuna_cobra.nds — AWAITING IN-GAME TEST
* E2: gate 0x02249516 `ldr r0,[0x0224953C] ; bx r0`, pool 0x2353 -> 0x021BB289; stub (40 B) = 0x2353 -> 1,
  0x1050 && [0x0229AC7C] != 0 -> 1, else 0. Seal 0x021BB286 0xD11F -> 0xE01F. Old literal write REMOVED.
  scratch/wattuna_u4_gate_emu.py: 12/12 cases as designed.
* U4 OPT: cls1 +0C CAVE_WU_U4COND (kind 2 query -> 0, else 0x0224A115), +14 CAVE_WU_U4COST (kind 2 stamp).
  CAVE_FREE -> 0x023A4900.
* verify 35/35, wattcobra PASS, sha256 4df25ea83763ca1fa85375b9e430e28ccd7deab02091fa3aee973a98cb5b3533.
  Ledger: 380 ov5 slots, 18 ov3 dead blocks, clean. Chain dry run of apply_effect: composes (Mara 0x106C intact).
* Unproven: whether the forced slot stays nonzero through the 2nd (hand) pick validation (count 1) — the
  resolver only stores while count == 0, nothing zeroes it until the next procedure init, so it should.

## BUILD 9 IN-GAME — user 2026-10-05
User: "Okay U4 works with one final defect when the effect is activated and accepted, wattuna offers all synchros despite not being able to make some: see .ml3. In this case only wattchimera is valid because i have a wattuna + lv 2, and watt hydra should not be offered."  Clarified: the Lv2 was in HAND; .ml3 = build 9, ED list on screen.
* U4 (activation, hand material, summon) IN-GAME CONFIRMED BY USER 2026-10-05 except the defect below.
* DEFECT: Extra-Deck offer lists every Watt Synchro (Aurora handler mode 4 = is_synchro only), incl. unmakeable Watthydra Lv7.
* Re-examining: build 2 changed TWO things (mode 0x24 -> 4 AND, in build 3, PART F Watt membership). Build 1's
  count 0 may have been the not-a-Watt Tuner rejection, not can_synchro being field-only. Also: the forced slot is
  NOT set during the phase-0x80 probe (resolver stores it only before polling the procedure in 0x7D).

### U4 offer defect — offline (scratch/wattuna_u4_offer_probe.py on rom_wattuna_cobra.ml3), 2026-10-05
Board: side 0 field z2 = 0x1050 (ref 12); hand 0x2278, 0x1DC7, 0x2261, 0x2391; ED 0x230F Wattchimera, 0x2477 Watthydra.
.ml3: phase 0x7E, forced slot 0x0. Emulator gained a Python stand-in for ARM signed divide 0x020989A4 (r0/r1, r0%r1).
| Aurora mode | gate grants 0x1050-first during probe | count |
| 0x04 (built) | n/a | 2 (both Watts — the defect) |
| 0x24 | no (E2 stub: forced == 0) | 0 (would fizzle) |
| 0x24 | yes (stub forced test NOP'd in emu) | 1 = 0x230F Wattchimera — CORRECT |
* CORRECTION: build 1's "can_synchro is field-only, mode 0x24 kills the offer" was an EMULATOR ABORT (BLX to ARM
  divide), never a measurement. can_synchro 0x02249540(side, cid, forced, flag): saves procedure state, sets the
  forced slot = r2, tries each of the 10 FIELD slots as FIRST pick via validator 0x02249AFC; level_sum reaches the
  hand through the gate (as for Mara/Eccentric Boy). Enumerator 0x0223BE40 mode bit 0x20 calls
  can_synchro(side, cid, 0, 1) @0x0223BF76 -> forced = 0 -> E2 stub refuses -> count 0.
* Fix design: ov5 handler = Aurora with mode 0x24 that sets a probe FLAG word around the enumerator call; E2 stub
  grants 0x1050-first when forced != 0 OR flag != 0. Deviation: the probe does not FORCE Wattuna into the
  materials, so a Watt Synchro makeable from other field materials without Wattuna could still be listed.

## BUILD 10 — rom_wattuna_cobra.nds (E3 offer fix) — AWAITING IN-GAME TEST
* E3: criteria row h -> CAVE_WU_OFFER 0x023A4900 (52 B): Aurora logic, mode 0x24, CAVE_WU_PROBE 0x023A4940 = 1 around
  `blx 0x0223BE41`, then 0. E2 gate stub (now 52 B) grants 0x1050-first if forced slot != 0 OR probe != 0.
  Aurora's own handler untouched. Row's set code loaded with ldrh (0x58 positive; assembler has no ldrsh).
* scratch/wattuna_u4_offer_probe.py END-TO-END with the real code in emulator memory over .ml3:
  count 1 = 0x230F Wattchimera, probe flag 0 after, gate stub hit. (Built mode-4 code: count 2.)
* verify 36/36, wattcobra PASS, sha256 c0abc25977cf69e56f02bf80e966b71b2fe8e41142de01673db31a2373b49685.
  Ledger 382 ov5 slots / 18 ov3 blocks, clean. KB synchro.can_synchro_forced_arg_and_offer_mode VERIFIED (571/0).
* Known deviation (state to user): the probe does not force Wattuna into the materials.

## ✅ BUILD 10 IN-GAME — user 2026-10-05: "U4 Works now, ship it"
U4 (incl. E3 makeable-only offer) IN-GAME CONFIRMED BY USER 2026-10-05, build 10 sha256 c0abc259....
WHOLE CARD (U1, U2 x2, U3 both paths, U4) confirmed. User APPROVED SHIPPING 2026-10-05.

## SHIPPED 2026-10-05
steps.STEPS step 91/95 (after patch_mara) + _verify_all_patches.SHIPPED. EE build 95/95, sha256
56bfa553fdb8037262b1d5d5f0fdadc03bdae6001f76d38bf5bd352a2c13f049 (pre-ship chain backed up as rom_all_patches.pre_wattuna.nds).
All Wattuna code + 6 ov5 stubs byte-identical to tested build 10. Sweep: 81 passed, 0 failed. KB card.wattuna added.
Donor pool: Spirit of the Harp moved to used (notes + scratch/donor_resource.json).
