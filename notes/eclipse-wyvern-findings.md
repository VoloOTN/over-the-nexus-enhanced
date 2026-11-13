# Eclipse Wyvern — findings

Session 2026-08-04. Status: **recon complete for clause 1; clause 2 blocked on one
unknown.** No ROM code written yet — nothing built, nothing claimed in the ledger.

## Card text (authoritative source)

From `scratch/ygoprodeck_cache.json`, id **51858306**, name "Eclipse Wyvern":

> If this card is sent to the Graveyard: Banish 1 Level 7 or higher LIGHT or DARK
> Dragon-Type monster from your Deck. If this card is banished from your
> Graveyard: You can add the monster banished by this card's effect to your hand.

Stats: **Effect Monster, LIGHT, Dragon, Level 4, ATK 1600 / DEF 1000.**

### Clauses

1. **(mandatory trigger)** If this card is sent to the Graveyard: Banish 1 Level 7
   or higher LIGHT or DARK Dragon-Type monster from your Deck.
2. **(optional trigger)** If this card is banished from your Graveyard: You can add
   *the monster banished by this card's effect* to your hand.

User decision (2026-08-04): **both clauses in scope**; donor chosen on engine
reachability with `card_prop` retune; **prefer a vanilla Normal Monster donor**.

## Confirmed (this session)

**KB health.** `verify_knowledge` = 186 facts, **158 PASS / 0 FAIL / 28 UNVERIFIED**
(all 28 narrative). Oracles: arm9, ov3, ov5, savestate all present.

**Eclipse Wyvern is absent from the ROM.** `scratch/cid_to_name.json` has only Book
of Eclipse 0x1E48, Red-Eyes Wyvern 0x1F2E, Ancient Sacred Wyvern 0x208D. Donor
conversion required.

**Gold Sarcophagus 0x1811 is fully implemented** — `cls0[569]`, slots
`+04 = 0x0221CD29` (resolver), `+0C = 0x021F0BDD` (condition), rest NULL.
Its resolver is the standard 3-phase machine on `[0x0229AAFC+0x70]`
(0x80 = act, 0x7F, 0x7E), verified by disassembly:
  * phase 0x80: `0x021BABE8(side)` then `0x02243FA8(side, cid, 0)` (candidate count
    via the criteria registry); 0 candidates -> return 0; else prompt
    `0x0219A818(side, 0x46)` -> return 0x7F.
  * phase 0x7F: `0x0219C430(side, 6, cid, 0)` -> return 0x7E.
  * phase 0x7E: reads the pick via `0x0219C510`, unpacks it to a packed ref
    `(inst_idx<<1)|side`, then **`0x021D21DC(side, ref, cid, 0x80)`**.

**THE DECK-BANISH PRIMITIVE (clause 1's action): `0x021D21DC(r0=side, r1=packed_ref,
r2=acting_cid, r3=flags)`.** It is a 6-instruction thunk into
`0x021D1DAC(side, r1=dest_sel, r2=ref, r3=flags, [sp]=cid)` with `dest_sel = 1`.
In `0x021D1DAC`, verified by disassembly:
  * `r1 != 0` -> destination zone **0x0F (banished)**; `r1 == 0` -> **0x0E (GY)**
    (`movs r4,#0xf` @0x021D1DE2 / `movs r4,#0xe` @0x021D1DE8).
  * source zone is `0x0C` (Extra) or **`0x0D` (Deck)** chosen by `0x0202307C(cid)`.
  * flags: Gold Sarcophagus passes **0x80**, D.D. Capsule passes **0xC0**.
Zone codes cross-check against the VERIFIED KB fact `ram.container_for_zone_code`
(0x0D Deck / 0x0E GY / 0x0F banished).

**Only 8 call sites for `0x021D21DC` in ov3**, owners resolved via cls-slot lookup:
`0x02216650` D.D. Capsule 0x159C, `0x0221C578` Inferno Tempest 0x17CA,
`0x0221CD96` **Gold Sarcophagus 0x1811 + Watthydra 0x2477 (shared resolver)**,
`0x02224D1E` Soul of Fire 0x1BAF, `0x02227922` Spell Chronicle 0x1D19,
`0x02230354` Blackwing Aurora 0x2385, `0x02233572` the Fusion-spell family,
`0x02263450` (unresolved).

**The criteria / "populate" registry is the deck-search candidate pool.** Base
**0x022713C4** (NOT a pointer — literal confirmed at `0x02243DFC`, loaded by the
binary search `0x02243B9C`), stride 12, count 0x56C = 1388, **sorted by cid**
(checked: sorted, range 0x0D48..0xFFFE). Layout `<HHII` = `[a=cid][b=aux][h=handler]
[fl=criteria]`. This is the same table seven shipped patches call `POP_BASE`
(patch_boggart_knight, patch_minefield_driller, patch_sea_lancer, patch_shiens_dojo,
patch_shooting_quasar, patch_tg_rush_rhino, patch_tg_striker).
  * Gold Sarcophagus row **[320]**: `cid=0x1811 aux=0xFFFF h=0x0223CAD9 fl=0x0000000E`
  * D.D. Capsule row [198] and Watthydra row [1342] are **byte-identical** in
    handler + criteria — the shared "1 card from your Deck, no filter" pool.
  * `h = 0x0223CAD9` is exactly the handler `patch_darksoul.py` retargets
    (`h 0x0223CAD9 -> 0x0223CAF5`, `b 0xFFFF -> 0x0048`) for its filtered
    Level<=4 X-Saber deck search. So a filtered deck search = new `h` + `b`.

**DONOR FOUND — Divine Dragon Ragnarok `0x1859`.** Records-free (absent from all
four cls tables *and* from the populate table — searched all four per the
`dispatch.cls_tables` warning) **Normal Monster**, and its printed stats are
**LIGHT / Dragon / Level 4 / ATK 1500 / DEF 1000** against Eclipse Wyvern's
LIGHT / Dragon / Level 4 / 1600 / 1000. Attribute, race, level and DEF already
match; **only ATK (1500 -> 1600) and the name/text need retuning.** 224
records-free Normal Monsters exist; only 6 are Level 4 Dragons and only this one
is LIGHT.

## Ruled out

- **`0x021C3BC8` is NOT a state/node store — it is the duel REPLAY MESSAGE LOG.**
  Disassembly: ring buffer at **0x02299B68**, stride 8, four u16 fields
  `[+0]=msg [+2]=arg1 [+4]=arg2 [+6]=arg3`, write index at `[0x0229A360+8]`,
  **capped at 0x100 (256)**, gated on `[0x02299114+8] != 3`.
  Consequently `0x021D2584(side, cid, code, ref)` -> `0x021C479C(side, kind=0x0B,
  cid, code, ref)` -> `0x021C3BC8` merely **logs** message 0x35 with
  `(code<<8)|kind`. **I initially read the `code=0x41` call at `0x0221CDAE` as the
  "card banished by this effect" store. That was wrong** — 0x41 is a
  message/animation id, and `0x021D2584` has **206 call sites** across ov3, so it
  is generic logging, not per-card state. Do not build clause 2 on it.
- The `cmp rX,#0x41` sites at `0x0219D52C` / `0x0219D57A` are unrelated: they are
  the bounds of a generic id-indexed counter store (id<0xA -> word array
  0x02298BC0; id<0x41 -> halfword array 0x02298BE8; else bitfield 0x02298C54).
- Only **43** `#0x41` immediate sites exist in all of ov3 and exactly **one**
  falls inside a cls-slot function (`0x0221CDAA`, the logger call itself) — so the
  clause-2 consumer is **not** a card record; it is engine code.

**CLAUSE 2'S TRIGGER EXISTS NATIVELY — Cyber Ouroboros `0x1CF6`.** Printed text
"When this card is removed from play, you can send 1 card from your hand to the
Graveyard to draw 1 card" — i.e. a *this card is banished* trigger. It is
implemented as a single record **`cls2[307]`**:
`+04 = 0x022065B9` (resolver), `+08 = 0`, `+0C = 0`, **`+10 = 0x021E5201`**, `+14 = 0`.
`+10` is the event-classifier slot. ⚠️ **Do NOT read `0x021E5201` as "the banished
tag"** — disassembly shows it is the **generic classifier plus a per-cid veto**:
it looks the acting cid up in a table at **`0x0226F628`** (count **0x61 = 97**,
stride **0xC = 12**) via `0x02022E44(cid, base, count, stride)`; if the phase word
`[0x0229AAFC+0x7C] == 0`, a row exists, and its predicate `blx [row+0x04]` returns
**0**, the classifier returns **-1** (suppress); otherwise it tail-calls the shared
classifier **`0x021E50DC`**. So the "which event am I?" discrimination lives in
`0x021E50DC`'s switch on `[0x0229AAFC+0x7C]` (arms for 0, 1, 2, ...), **not** in
the `+10` value. What IS established is that Cyber Ouroboros is the native
"when this card is removed from play" card and `cls2[307]` is its complete wiring.
(`0x021E51E5`, the Yubel-TI leave tag, is a thin veneer over the same
`0x021E50DC`, confirming the family shape.)

**KB cross-check:** `0x0226F628` is the address the equip-spell note records only
negatively — "*NOT* the equip-target gate (no race-locked equip has a row — this
burned Wonder Wand rounds 1–4)". This session gives it a **positive** identity for
the first time: a 97-row × 12-byte **per-cid veto table** consulted by the
classifier family, rows carrying a predicate at `+0x04`. Worth contributing back.
Contrast D.D. Survivor `0x18BC` = `cls2[172]`, `+10 = 0x021E9021` — a *different*
tag ("was banished face-up from the field this turn", End-Phase), so the two are
not interchangeable.

**The banished card word identifies where it came from.** From the verified
bitfield decode of `0x021D1DAC`'s destination-word build, the packed word carries
`[0..8] = ref`, `[9] = side`, **`[10..13] = SOURCE zone`**, `[19..22] = dest zone`,
and `[28] = face-down-in-banish` (set only when `flags & 1`; Gold Sarcophagus's
0x80 and D.D. Capsule's 0xC0 both leave bit 0 clear, so neither banishes with that
bit). Because a clause-1 banish moves the card **from the Deck (0x0D)**, a card
banished by Eclipse Wyvern is distinguishable in the banished array
(`player+0x7B4`, count `+0x1C`, zone code 0x0F) by `source zone == 0x0D`.

**Donor `0x1859` confirmed records-free**: no record in cls0/cls1/cls2/cls3 and no
populate row. Clean slate for both clauses.

## ⚠️ Composition blocker (must resolve before building)

Clause 1 and clause 2 are two different triggers on **one cid**. Per the VERIFIED
KB fact `dispatch.find_event_handler_offset`, `find_event_handler` returns the
**leftmost** same-cid record, and its `+1` offset applies **only to cls1**
(selector 1, event code != 6). So **two cls2 records under 0x1859 would shadow
each other** — this is exactly the shipped Warwolf E1/E2 regression.

The conflict is concrete: clause 1's trigger (Recruiter recipe) wants a cls2 record
with `+0C = 0` and `+10 = 0`; clause 2's trigger wants `+10 = 0x021E5201`. They
cannot be the same record as-is. Three candidate resolutions, none yet proven:
  a. Put clause 1 in cls2 and clause 2 in **cls1** (different tables, no shadow).
  b. **One** record whose resolver switches on the event code `desc[+0x04]` — this
     is precisely how D.D. Capsule's `0x02216560` serves two behaviours
     (`ldrb r0,[r5,#4]; cmp r0,#2` splits delayed retrieval from activation).
     Requires proving both events reach the same record.
  c. Clause 1 via the leave-hook trampoline `0x021C8216` (records-free, per
     `otn-leave-trigger-cls2`), leaving cls2 free for clause 2.

## 3DS CROSS-REFERENCE — the decisive evidence (2026-08-04)

Per `counter.criteria_registry_layout` / `counter.bespoke_criteria_handler`, the
sibling 3DS build shares the **cid namespace** (its *addresses* must never enter
the NDS namespace; lift algorithms only). Reference files are committed:
`ygo_tools/reference_files/3ds_{name,indx,card_prop,desc,overlay_3}.bin`.

**Mapping established and validated this session.** `3ds_indx.bin` = 5888 × (u32
name-offset, u32 desc-offset); `3ds_name.bin` = UTF-16LE NUL-terminated strings;
`3ds_card_prop.bin` = 5887 × 8-byte records, **no header**, **cid at +0x00**
(low 14 bits; bit 15 is a flag). **`card_prop_record_index == indx_index`** —
validated against five cards whose NDS cids are known: Gold Sarcophagus 0x1811,
Divine Dragon Ragnarok 0x1859, Book of Eclipse 0x1E48, Red-Eyes Wyvern 0x1F2E,
Ancient Sacred Wyvern 0x208D — **all five exact**.
**3DS code base: file offset = address − 0x00100000** (verified: three probed
addresses all land on clean ARM prologues; base 0 gives mid-function garbage).

**ECLIPSE WYVERN = cid `0x26E5`** in the shared namespace (above OTN's ~0x2600
ceiling, hence absent from the NDS build — no collision risk). Its 3DS card text
is **character-identical** to the ygoprodeck text sourced in step 1.

### Clause 1's filter is a DATA ROW — no 3-property stub needed

Eclipse Wyvern's 3DS criteria/populate row:
`{cid=0x26E5, filt=0xFFFF, handler=<bespoke, 1 card>, flags=0x0002, extra=0x085C}`
Decoded against `counter.criteria_registry_layout`:
  * `filt = 0xFFFF` — no archetype/set-code filter ✓
  * `extra` **high byte `0x08`** -> `race = 0x08>>3 = 1 = **Dragon**`,
    `attribute = 0x08&7 = 0 = **unrestricted**` ✓
  * `extra` **low byte `0x5C`** = `0x40 | (7 << 2)` -> **Level >= 7** ✓
  * `flags = 0x0002` — the same deck-search flag as Shien's Footsoldier 0x1B3A.

**NEW ENCODING FACT: `0x40 | (L<<2)` = "Level >= L"**, the mirror of the KB's
already-recorded `0x80 | (L<<2)` = "Level <= L". **Independently confirmed** by the
neighbouring row: Chaos Zone `0x26E6`, `extra = 0x0051` = `0x40|(4<<2)` =
"Level >= 4", matching its text "remove **4 or more** Chaos Counters ... target 1
banished monster with a Level equal to the number of Chaos Counters removed".
Two cards, two independent texts, same encoding.

**Consequence:** race and level bound come **free from the row**. The attribute
field is deliberately left unrestricted because LIGHT-**or**-DARK cannot fit one
attribute slot — so the *only* custom code clause 1 needs is a LIGHT-or-DARK
per-candidate check, which is the `patch_shiens_dojo` recipe verbatim (replace the
per-candidate **callback** + clone the generic handler to point at it). This is far
smaller than the 3-property ov5 filter originally planned.

### Composition: the 3DS uses TWO records under one cid

3DS cls table has the **same shape as NDS** (cid at +0x00, five slots +04..+14,
stride 24, sorted by cid). Eclipse Wyvern owns **two consecutive records**:
  * **A** `+04=<generic resolver, shared with 3 other cids>`, `+0C`, `+10`, `+14` set
  * **B** `+04=<resolver>`, `+08/+0C/+10/+14 all NULL` — a mandatory, condition-free
    trigger. **This is clause 2.**
Record B's resolver is a phase machine on the same protocol as NDS
(`[global+0xBB4]`, phases 0x64/0x78/0x7C/0x7D/0x7E/0x7F/0x80 — cf. NDS
`[0x0229AAFC+0x70]` 0x7E/0x7F/0x80), with a per-cid switch in phase 0x7C encoding
cids as **base ± imm around 0x25E7** (the ungreppable idiom of
`thumb-stack-based-switch-footgun`); Eclipse Wyvern's arm is `0x25E7 + 0xFE`.

### ⭐ How clause 2 remembers the banished card

Eclipse Wyvern's clause-2 arm reads **`desc[+0x16]`** — twice as the key, once more
as an argument. **The remembered card lives ON THE EFFECT DESCRIPTOR, not in a
global node array.** In the NDS descriptor this is exactly
**`desc[+0x14 + i*2]` with `i = 1`** — i.e. **recorded pick #1** of the pick array
that `dispatch.pick_halfword_layout` already documents as VERIFIED, with
accessors `0x022348C0` (raw halfword), `0x02234904` (side | key<<8) and
**`0x02234964` (packed card ref)**.

So the mechanism is: **clause 1 records the banished card as a recorded pick on the
descriptor; clause 2 reads it back.** No new storage engine is required on NDS —
the pick array and its three accessors are already verified machinery. This
**supersedes** the "source-zone approximation" workaround proposed earlier: exact
identity IS achievable.

## BUILD ATTEMPT (2026-08-04, later) — architecture resolved, one blocker found

**Composition question RESOLVED — and my earlier answer was wrong.** I proposed
putting both cls records in **cls1** (using the `+1` offset of
`dispatch.find_event_handler_second_record`). **That does not work.** The offset
only applies when the *event descriptor* carries selector 1, and both of this
card's triggers arrive with **selector 2**: Cyber Ouroboros's banish trigger lives
in `cls2[307]`, and Sangan's any-means sent-to-GY registration is likewise a cls2
record. Moving records to cls1 does not move the events. The viable shape is
therefore **ONE cls2 record whose resolver switches on the descriptor**, the
D.D. Capsule pattern (`0x02216560`: `ldrb r0,[r5,#4]; cmp r0,#2`).
Two usable discriminators are confirmed present on the descriptor:
`desc[+0x04]` = event code and **`desc[+0x03]` = ZONE code** (seen in
`0x021E50DC` at 0x021E512C selecting prompt text for 0xE = GY, 0xB = recent-list).
Clause 2 needs "banished **from the GY**", so `desc[+0x03] == 0x0E` is the natural
gate.

**Clause 1's resolver may need NO new action code.** Gold Sarcophagus's resolver
`0x0221CD29` is generic in its inputs — it reads `desc[+2]` (side) and `desc[+0]`
(cid) only, counts candidates with `0x02243FA8(side, cid, 0)` (which consults *the
acting cid's own criteria row*), opens the picker, and banishes with
`0x021D21DC(...,0x80)`. Given the donor a criteria row of its own, that resolver
performs exactly clause 1. Neither Gold Sarcophagus (0x80) nor D.D. Capsule (0xC0)
sets card-word bit 28, so both banish **face-up** — correct for Eclipse Wyvern.

### ⛔ BLOCKER: list30 is FULL — clause 1's trigger cannot be registered that way

`patch_gravekeepers_recruiter`'s trigger is membership in the sent-to-GY leave
dispatcher list **list30 @ `0x0226E904`, `0x1E` = 30 entries, u16, sorted**.
Dumped this session: **all 30 slots hold real, obtainable cards** (Sangan 0x0FD6,
Witch of the Black Forest 0x11E4, Goblin Zombie 0x15B9, Botanical Girl 0x1ED4,
Naturia Cliff 0x2034, ... Naturia Eggplant 0x24E0). **There is no phantom to drop**,
so a count-neutral insert would have to delete a working card's trigger.
⚠️ Index 12 is **Emissary of the Afterlife 0x1796 — already claimed as T.G.
Warwolf's donor** by a shipped patch.
The list also **cannot grow in place**: `0x0226E940` (immediately after it) is the
start of another sorted u16 list (`0x0E42, 0x0E48, 0x12D3, 0x1366, ...`), so
writing a 31st entry corrupts the neighbour. There is exactly **one** literal-pool
reference to the list, at `0x021C8320`, loaded by `LDR r1` at **`0x021C80EC`** —
inside the same large leave-dispatcher function that contains the leave hook.

**Resolution (not yet built):** do **not** touch list30. Use the **leave-hook
trampoline `0x021C8216`** instead — records-free, already IN-GAME CONFIRMED for
Shooting Quasar (`otn-leave-trigger-cls2`), and re-confirmed here byte-for-byte
(`movs r1,#0x77 ; lsls r1,r1,#6` -> cid compared against 0x1DC0, matching the
VERIFIED KB fact `leave.leave_hook`). It yields `r4 = cid` plus the leave
descriptor slots (`[sp+0x90]` DESTROYED, `[sp+0x144]` to-GY), which is precisely
the "sent to the GY by any means" condition clause 1 needs. The alternative —
detouring the membership test at `0x021C80EC` to also accept the donor cid — is
count-neutral by construction and worth comparing.

**Status: NOT BUILT.** No ROM bytes were written, no ov5 cave slot claimed, no
allocation-ledger entry made. The session ran out of runway at the point where the
trigger mechanism changed from "insert into list30" to "trampoline", which is a
different (and larger) piece of work than the Recruiter recipe I had costed.

## SESSION 2 (fresh start on the trigger) — blocker dissolved, donor changed

**The list30 detour point is real but needs a puzzle-safe host.** The arming code is
`[sp+0x18] = 1`, set at `0x021C80FC` after `bl 0x02022E14(r0=cid, r1=list, r2=count)`
at **`0x021C80F2`**, gated on `[sp+0x2C] != 0` and `[sp+0x144] != 0` (to-GY).
Retargeting that BL to a ~22-byte stub (`if cid == donor: return 1; else tail-call
0x02022E14`) would work — but this is **shared code that runs in puzzles**, where
ov5 is evicted by ov41, so an ov5 host would freeze. And the ov3 BSS cave
(`ov3_cave.py`) is **explicitly canary-gated**: "Do not claim a CAVE3_* slot until
the canary passes." So the only legal host would be one of the 15 remaining
provably-dead ov3 arms (the Escuridao technique; Escuridao took 44 B at
`0x021B54E0`). Viable, but unnecessary — see below.

### ⛔ RULED OUT: the second to-GY list (0x0226E990)

`0x021C80C8..0x021C80DE` checks a SECOND list — **`0x0226E990`, `0x6A` = 106
entries, sorted** — and sets the SAME `[sp+0x18]` arming flag, gated only on
`[sp+0x144]` (to-GY) without list30's extra `[sp+0x2C]` condition. It contains
**15 phantoms** (0x0E10, 0x0E3A, 0x0EB9, 0x14DD, 0x14E7, 0x1B18, 0x1B19,
0x1B45..0x1B4A, 0x1BBE, 0x234E), of which only 0x234E is claimed
(tg_rush_rhino) — so a count-neutral insert would have been trivial.
**But the semantics are wrong.** Sampling its real members shows it is the
**"destroyed by BATTLE and sent to the Graveyard"** family: UFOroid, Sun Dragon
Inti, Lord Poison, Regenerating Rose, Rai-Mei, Dread Dragon, Pandaborg — nearly
every text reads "when this card is destroyed by battle and sent to the Graveyard".
Eclipse Wyvern's clause 1 is **any-means**, so this list would under-trigger
(no Tribute, no Synchro Material, no effect-destruction). Do not use it.
list30 — Sangan, Witch of the Black Forest, Goblin Zombie, Botanical Girl,
Emissary, Naturia Cliff — is the any-means family and is the correct one.

### ✅ THE BLOCKER WAS A FALSE ONE — reframe the donor, don't patch the list

`patch_gravekeepers_recruiter` never inserted into list30: **Botanical Girl 0x1ED4
was NATIVELY a member**, and the patch explicitly KEEPS that membership ("the
earlier build REMOVED it, which is why the effect stopped triggering"). So the
correct move is to **choose a donor that is already in list30**, making the trigger
count-neutral by construction — no list edit, no cave, no stub, no canary.

**NEW DONOR CANDIDATE: Genesis Dragon `0x1F2A`.**
  * **LIGHT / Dragon** — Eclipse Wyvern's exact attribute AND race, so no
    archetype/race retune and any Dragon interactions are natively correct.
  * **Natively in list30** (index 19) -> clause 1's any-means sent-to-GY trigger
    is free.
  * **Unclaimed** by any shipped patch (checked against `PHANTOM_CLAIMS` and the
    donor list).
  * **Already owns TWO populate rows**, pop[792] `{filt 0xFFFF, h 0x0223CB65,
    flags 0x0002, extra 0x0800}` and pop[793] `{... h 0x0223CBB1, ... extra 0x0801}`
    — both already **race = 1 (Dragon)**. So clause 1's criteria row can be edited
    **in place**, which is count-neutral without dropping any phantom at all.
  * Retune needed: Level 6->4, ATK 2200->1600, DEF 1800->1000, name/text
    (all `card_prop`, already approved).
  * ⚠️ Complication: it has `cls2[398]` `{+04 0x0222AC79, +0C 0x021FF8C9,
    +10 0x021E51E5}` AND `cls3[469]` `{+04 0x02208181, +0C 0x021FF8C9,
    +10 0x021E7245, +14 0x02235605}`. Both native effects must be neutralised,
    and cls2[398] is the record clause 1 (and possibly clause 2) will reuse.

**THE ROW TEMPLATE ALREADY EXISTS IN THE NDS.** Decoy Dragon `0x1C4F` pop[571] =
`{filt 0xFFFF, h 0x0223C9D1, flags 0x0002, extra 0x085D}` = **Dragon + Level >= 7**,
matching its text "target 1 Level 7 or higher Dragon-Type monster in your
Graveyard". Eclipse Wyvern's 3DS row is `extra = 0x085C` — the same value with
bit 0 cleared. Decoy Dragon reads the **GY**, Eclipse Wyvern the **Deck**, so
`extra` bit 0 is very likely the source container — **INFERRED, NOT PROVEN**;
Genesis Dragon's own two rows also differ only in that bit (0x0800 / 0x0801),
which is consistent but not decisive. Prove it before relying on it.

**Still NOT BUILT.** No ROM bytes written, no ledger entry, no cave slot claimed.

## SESSION 3 — container bit PROVEN (and my inference REFUTED), clause 1 BUILT

**`extra` bit 0 is NOT the source container. The HANDLER is.** Correlated all 1388
criteria rows against the owning card's printed text (classified by the single
container the text names). Handlers with n>=8 are essentially pure:
  * **Deck**: 0x0223CAF5 (52/53), 0x0223CAD9 (44/47), 0x0223D075 (37/37),
    0x0223CA99 (30/30), **0x0223CAB5 (25/25)**, 0x022400E5 (12/12)
  * **GY**: 0x0223CA11 (46/46), 0x0223CBB1 (40/40), 0x0223C9ED (37/37),
    **0x0223C9D1 (32/32 — Decoy Dragon's)**, 0x0223CBC9 (30/30)
  * **hand**: 0x0223CF45 (44/44), 0x0223CA51 (31/31), 0x0223CA71 (24/24),
    **0x0223CB65 (12/12 — Genesis Dragon's)**
`flags` does not separate containers either (flags=0x0002 alone spans gy:243
hand:148 deck:143).
⚠️ **My earlier inference was wrong.** The raw bit-0 correlation *looked* strong
(bit0=1 -> gy 243/259 = 94%) but is an ARTIFACT: the GY-family handlers happen to
set bit 0. The tell is that bit0=0 is thoroughly mixed (deck:273 hand:247 gy:103).
Recorded as VERIFIED fact `counter.criteria_handler_selects_container`.

### DONOR CHANGED AGAIN: Naturia Cliff `0x2034` (not Genesis Dragon)

Genesis Dragon has TWO criteria rows *and* a cls3 record. Naturia Cliff is
strictly better on every axis:
  * **natively in list30** (index 20) -> trigger is free, no table edit
  * **exactly ONE** criteria row and **ONE** cls2 record — nothing to shadow
  * its row's handler `0x0223CAB5` is **already a Deck-family handler**
  * printed stats **Level 4 / DEF 1000 are already Eclipse Wyvern's**
  * unclaimed
Its native row `extra=0x0090` = `0x80|(4<<2)` = "Level <= 4" matches its real text
("Special Summon 1 Level 4 or lower 'Naturia' monster from your Deck") — an
independent confirmation of the level-bound encoding this build depends on.

### BUILT — `otn_enhanced/cards/eclipse_wyvern.py`

Three edits, two of them pure data, nothing inserted or shifted:
  * **A0** list30 membership ASSERTED, not written (idx 20).
  * **A1** criteria row for 0x2034, **in place**: `filt 0x003C -> 0xFFFF`,
    `extra 0x0090 -> 0x085C` (Dragon + Level>=7). Handler `0x0223CAB5` (Deck) and
    `flags 0x0002` unchanged.
  * **A2** `cls2[0x2034]`: `+04 0x02206CAD -> 0x0221CD29` (Gold Sarcophagus's
    deck-banish resolver), `+0C 0x021F0419 -> 0`, `+10 0x021E51E5 -> 0` —
    Sangan's matched list30 pairing (`cls2[40]` = `+04 0x02207EF5, +0C 0, +10 0`).
  * **B** card_prop: `lvl=4 attr=LIGHT race=Dragon atk=1600 def=1000`
    (raw `0x00CC11433225A034` -> `0x00C2104332282034`), name/desc.

`verify()` PASSES: list30 kept + still sorted, row = Deck/Dragon/Level>=7, cls2
`+04 = 0x0221CD29`, criteria registry still globally sorted.
Registered in `apply_all_patches.PATCHES` (before the always-last WiFi step) and
in `check_allocations` (`populate_table`/`cls2_table`/`list30_subscription` for
0x2034) — ledger regenerated, **no collisions**.

### KNOWN DEVIATION (deliberate)

The filter is **Dragon + Level >= 7 from the Deck** but NOT "LIGHT or DARK": a
criteria row carries exactly ONE attribute code, so the pair cannot be data. The
3DS build hits the identical wall and leaves its attribute field 0, pushing the
test into a bespoke handler. The filter is therefore strictly **wider** than the
real card, never narrower. Closing it = one per-candidate ov5 callback (the
`patch_shiens_dojo` recipe); ov5 is a legitimate host here because the callback is
reached ONLY through this card's own row, so a puzzle (where ov41 evicts ov5)
degrades this card rather than freezing the engine.

### ⚠️ THE ONE UNPROVEN THING — what the in-game test must decide

Gold Sarcophagus's resolver is native to a **Spell activation**. Driving it from a
**trigger** exercises the same 0x7E/0x7F/0x80 phase protocol on
`[0x0229AAFC+0x70]`, but that it is actually pumped through those phases on the
trigger path is **not proven statically**. If no prompt appears when the card hits
the GY, clause 1 needs its own resolver rather than this one.

## SESSION 3b — Naturia Cliff build WITHDRAWN; moving to a Normal Monster donor

User direction: **do not consume a real card — use a records-free Normal Monster
donor, as T.G. Striker / Warwolf / Rush Rhino do.** The Naturia Cliff (0x2034)
build was unhooked from `apply_all_patches.PATCHES` and its ledger claims released
(`check_allocations` re-emitted clean; chain imports, 30 steps). The module
`patch_eclipse_wyvern.py` is kept on disk as a working reference for the
data-edit half — its criteria-row and cls2 values are still correct and reusable.

**This changes the MECHANISM, not just the cid.** A records-free vanilla is not in
list30, so the native any-means sent-to-GY registration is unavailable. The proven
substitute is the **shared any-leave arming trampoline** already installed at hook
**`0x021C8216`** (`ov5_cave.CAVE_TG_ARMTRAMP`, 0x40 B; cid list
`CAVE_TG_ARMLIST`, 0x10 B = up to 7 cids). Its contract, from the shipped patches:
  * entered by **BL**, `LR = 0x021C821A`, SP still the dispatcher's (it pushes
    nothing), displaced ops `movs r1,#0x77 ; lsls r1,r1,#6` must be replayed;
  * **`r4` = departing card's cid**; **`[sp+0x90]` = DESTROYED**;
    **`[sp+0x98]` = side** (the gate's own controller check reads it);
    **`[sp+0x144]` = to-GY** (`leave.descriptor_slots`);
  * each patch **idempotently installs the hook and appends its cid** to the list.

Two exit shapes exist in the shipped code, and the choice matters here:
  * **T.G. shape** — branch into the GY gate `0x021CA640`, which trigger-builds an
    **End-Phase** trigger. This is what Striker/Warwolf/Rhino use, and it also
    tests `[sp+0x90]` so it fires on **destruction only** (no Tribute, no Synchro
    Material). Both properties are wrong for Eclipse Wyvern, whose clause 1 is
    **immediate** and **any-means**.
  * **Quasar shape** — `BX` to a donor-only, self-contained stub that performs the
    action **immediately** inside the leave path. This is the shape to copy.

### Plan for the rewrite

  * **Donor: Divine Dragon Ragnarok `0x1859`** — records-free Normal Monster
    (absent from all four cls tables and the criteria registry), and already
    **LIGHT / Dragon / Level 4 / DEF 1000**; only ATK 1500 -> 1600 plus name/text.
  * Append `0x1859` to `CAVE_TG_ARMLIST` and add a donor-only branch that `BX`es to
    a new ov5 stub, leaving the T.G. cids' path byte-identical.
  * Gate the stub on **`[sp+0x144]` (to-GY)**, NOT `[sp+0x90]` (DESTROYED), so the
    trigger is any-means as the card requires.
  * Stub action, self-contained (no cls2 record, no criteria row, no phantom
    drops): walk the controller's **Deck (`player+0x304`, count `player+0x10`,
    zone code 0x0D)**, filter to race == Dragon and Level >= 7, and banish the
    match with the verified **`0x021D21DC(side, packed_ref, cid, 0x80)`**
    (r1=1 selects banished 0x0F; flags 0x80 leaves card-word bit 28 clear = face-up).
  * Size guide: Quasar's leave stub reserved 0x80 B. Thumb-1 ONLY; validate with
    `effect_verify.assert_thumb1_only`; take the slot from the live `CAVE_FREE`
    and register it in `ov5_cave.py` + `check_allocations`.

### Consequences to accept with this donor

  * **ov5 is normal-duel only** — in a puzzle overlay 41 evicts it and the card is
    inert (the project norm; identical to every T.G. card). This is SAFE here
    because the trampoline is entered only via the hook the T.G. patches already
    own and which already handles a missing-cid case.
  * **Auto-select vs prompt**: a self-contained stub picks the target itself,
    whereas the real card lets the player choose. Gold Sarcophagus's resolver
    (which does prompt) is not reachable from the leave path, so either accept
    auto-selection of the first legal Dragon or drive a picker from the stub.
    ⚠️ **Decide before building.**
  * ⚠️ **Re-entrancy** — the same risk Quasar's notes flag: this drives an
    engine action from INSIDE the card-removal path. If it freezes, the fallback
    is to latch a flag in the stub and perform the banish at a later, safer point.

### ✅ BUILT AND CHAIN-VERIFIED (Normal Monster donor, with the native picker)

The self-contained-leave-stub plan above was **superseded**: it could only
auto-select, and the picker was wanted. The picker is asynchronous (Gold
Sarcophagus's resolver yields across phases 0x80 -> 0x7F -> 0x7E while the effect
system re-invokes it) and the leave path is synchronous, so the action had to run
through a **real cls2 record**. That in turn needs the IMMEDIATE trigger, i.e.
list30 membership — which the donor lacks and the list cannot grant.

**Solution: detour the membership TEST, not the list.**
`0x021C80F2: bl 0x02022E14 -> bl 0x021B591E`. The 22-byte stub answers "member"
for 0x1859 and tail-calls the native sorted search for every other card, so
list30 itself is untouched and all other cards are bit-identical.
⚠️ **Hosted in ov3 dead code (0x021B591E, the 28 B leaf of phantom 0x19BE), NOT
ov5** — this is a SHARED path that also runs in puzzles, where ov41 evicts ov5 and
a BL into it would freeze the engine. This is the ov3 DEAD-CODE pool (Escuridao's
technique), not the still-canary-gated ov3 BSS cave.

Final edits:
  * **A** 22 B ov3 stub + membership detour; list30 untouched and still sorted.
  * **B** cls2 count-neutral insert, drops phantom **0x194A**:
    `{+04 0x0221CD29, +08/+0C/+10/+14 = 0}` (Sangan's matched shape). Count 697.
  * **C** criteria count-neutral insert, drops phantom **0x18F8**:
    `{filt 0xFFFF, h 0x0223CAB5 (Deck), flags 0x0002, extra 0x085C}`. Count 1388.
  * **D** card_prop: `Lv4 LIGHT Dragon 1600/1000` **Effect Monster**
    (the vanilla's card_type MUST be promoted, as the T.G. conversions do) + text.

**Chain: 31/31 patches applied, zero errors.** Full-chain `verify()` sweep against
`rom_all_patches.nds`: **22 PASS**, including `patch_eclipse_wyvern` and every
shipped card (T.G. Striker/Warwolf/Rush Rhino, Quasar, Sea Lancer, Shien's Dojo,
Escuridao, Gravekeeper's Recruiter, Infernity Barrier, Hyper Librarian, ...).
Ledger regenerated, no collisions (110 B ov3 dead-code free, was 132).

Two verify results that are NOT regressions, checked rather than assumed:
  * `patch_bulk_ydcs` fails at **module import** (`Main deck must have between 40
    and 60 cards, got 15`) — hardcoded deck data, never reads a ROM, untouched by
    this work. Pre-existing.
  * `patch_unlock_all_packs`, `patch_wonder_wand`, `patch_zeta_reticulant` are
    **not in `PATCHES`**, so their edits were never applied and their verify()
    failing against the combined ROM is expected.
  * ⚠️ Harness note: four modules name their parameter `out_path`, not `out`. A
    sweep that only passes `out=` silently verifies them against their own stale
    standalone ROMs and reports false regressions. Also `patch_zeta_reticulant`
    calls `sys.exit()` inside `verify()`, which kills a naive harness.

## SESSION 4 — IN-GAME FREEZE diagnosed from rom_all_patches.ml2 (2026-08-04)

**Symptom:** the ROM freezes when Eclipse Wyvern's effect activates.

**Measured from the savestate** (`find_ram_offset` -> 0x24, the documented value):
  * Every edit IS resident and correct: ov3 stub bytes at 0x021B591E match, the
    membership call at 0x021C80F2 is retargeted (`edf714fc`), `cls2[166]` =
    `{0x1859, 0x0221CD29, 0, 0, 0, 0}`, `criteria[333]` = our row.
  * **`[0x0229AAFC+0x70] = 0x80`** — parked in the ACT phase.
  * **`[0x0229DD94+0x64] = 0x1859`** — our cid is the acting card.
  * **candidate count `[0x0229944C+6]` = 0** — the search found NOTHING.
  * Side 0's deck (33 cards) contained **4 legal targets**: Dark Armed Dragon
    0x1CFD (Lv7 DARK Dragon) and 3x Red-Eyes Darkness Metal Dragon 0x1D85
    (Lv10 DARK Dragon).

**GOOD NEWS: the trigger works.** The list30-membership detour fired, the cls2
record dispatched, and Gold Sarcophagus's resolver was entered with our cid on a
TRIGGER path — which settles the one thing that was flagged unproven at build
time. The failure is entirely in the candidate search.

### ROOT CAUSE — wrong handler family

The row used **`h = 0x0223CAB5`**, inherited from Naturia Cliff. Correlating that
handler's 32 rows against card text: **28 of 32 are SPECIAL SUMMONS**. It is the
Special-Summon-from-Deck family and requires every candidate to be SS-legal.
Dark Armed Dragon and Red-Eyes Darkness Metal Dragon **cannot be Special Summoned
from the Deck**, so all four legal targets were rejected -> 0 candidates.
⚠️ This refines `counter.criteria_handler_selects_container`: a handler selects the
container *and* carries ACTION semantics. "Deck-family" is not interchangeable.

**FIX: `h = 0x0223CAD9`** — the general-purpose Deck handler.
**Template = Soul of Fire 0x1BAF** `{filt 0xFFFF, h 0x0223CAD9, flags 0x0002,
extra 0x2000}` = "Select 1 Pyro-Type monster from your Deck and remove it from
play" — the SAME action (race-filtered deck pick + banish) and one of the 8 native
callers of the deck-banish primitive 0x021D21DC. **Fossil Dig 0x20A0**
`{h 0x0223CAD9, fl 0x0002, extra 0x4898}` = Dinosaur + Lv<=6 additionally proves
handler + flags + race + level bound compose. Applied; standalone verify passes.

### ⚠️ SECOND BUG, DIAGNOSED BUT NOT YET FIXED — empty-deck freeze

The freeze mechanism itself is independent of the handler bug and WILL recur
whenever the Deck holds no Level 7+ Dragon. Gold Sarcophagus's resolver calls the
completion routine **0x021D269C(side)** only on the phase-0x7E success path; the
phase-0x80 "0 candidates" arm returns 0 *without* it, so the effect never
finishes. Harmless in a Dragon deck, fatal otherwise. Note 0 is ALSO the normal
completion return value, so the return code is not the signal — 0x021D269C is.

**Planned fix (not built):** a small cid-keyed wrapper resolver in the ov5 cave
(legal host — reached only through this card's own cls2 record): on phase 0x80,
if `0x02243FA8(side, cid, 0) == 0` then call `0x021D269C(side)` and return 0,
otherwise tail-call `0x0221CD29`.

## SESSION 5 — trigger scope fixed: list30 was the WRONG table

**In-game report:** after the handler fix the effect activates correctly, but it
only triggers when the card leaves the FIELD to the GY. Eclipse Wyvern must
trigger on being sent to the GY from ANYWHERE (hand, Deck, field) — "like
Dandylion".

### The dispatcher has TWO mutually exclusive registration paths

Re-reading 0x021C80C8..0x021C8114:
  * **list30** `0x0226E904` (30) and **list106** `0x0226E990` (106) both set the
    arming flag `[sp+0x18]`. list30's arm is additionally gated on **`[sp+0x2C]`,
    which means "left the FIELD"** — now confirmed empirically, not just suspected.
  * **The LEAVE-MASK TABLE `0x0226EC1C`** ({u16 cid, s16 mask}, `0x98` = 152 rows,
    stride 4, sorted, looked up by `0x02022E44`) is consulted at 0x021C8104
    **ONLY IF `[sp+0x18]` is still 0** (`ldr r0,[sp,#0x18]; cmp r0,#0; bne skip`
    @0x021C80FE).

⚠️ **So the previous build was doubly wrong**: forcing the donor onto list30 not
only restricted the trigger to field-leaves, it *actively suppressed* the
mask-table path that would have been correct. The ov3 dead-code stub and the
`bl` retarget at 0x021C80F2 are **removed**; block 0x021B591E is released.

### DANDYLION IS THE TEMPLATE — mask 0x0800

**Dandylion `0x19FE`** ("If this card is sent to the Graveyard: Special Summon 2
Fluff Tokens") is NOT in list30. It is **mask-table row 47 with mask `0x0800`**,
and its `cls2[203]` = `{+04 0x02207A09, +08 0, +0C 0, +10 0, +14 0}` — the SAME
record shape this patch already used, which independently validates PART B.

**Mask `0x0800` = "sent to the Graveyard", any source zone.** All 15 real cards
carrying exactly this mask are worded that way: Dandylion, Peten the Dark Clown
0x17C5, Jinzo - Returner 0x1D9B, The White Stone of Legend 0x1EAA, Skull-Mark
Ladybug 0x12A2, Archfiend of Gilfer 0x13E3, Limiter Overload 0x1F35, Cockroach
Knight 0x1185, Outstanding Dog Marron 0x1687, Sword of Deep-Seated 0x1309,
Cross Porter 0x1D97, Amulet of Ambition 0x1C38, Snap Dragon 0x24DB, Tender of the
Laval Volcano 0x249D. 100% consistent.
(Contrast the KB's `0x0C04` = destroyed + to-GY — strictly narrower. The full mask
distribution has 42 distinct values; 0x0C04 is the most common at 21 rows.)

**FIX APPLIED:** mask row `{0x1859, 0x0800}` inserted count-neutrally over phantom
**0x16F5** (itself already a 0x0800-family phantom, so dropping it is doubly
inert). The insert point (37) is ABOVE the phantom (34), so `_insert_sorted` was
made bidirectional — sliding the block DOWN when the phantom sits below the
insert position.

Clause 1 is now **pure data**: three count-neutral table rows (mask, cls2,
criteria) plus card_prop. No code, no cave, no stub, nothing shifted in size.

### Trigger-path question RESOLVED

The build-time caveat — "does a TRIGGER pump Gold Sarcophagus's Spell-activation
resolver through its 0x80 -> 0x7F -> 0x7E phases?" — is **answered YES in-game**:
the prompt appears and the banish resolves. Remaining untested: that the mask-table
registration fires from the HAND (discard) and the DECK (mill), not just the field.

## SESSION 6 — mask row is correct but discard/mill STILL does not trigger

**Measured from `rom_eclipse_wyvern.ml2` (20:53:20, the standalone ROM the user
tested — note `rom_all_patches.ml2` is 21 min older and NOT this test):**
  * **The mask row IS resident and correct**: row 37 = `{0x1859, 0x0800}`, phantom
    0x16F5 gone, table still sorted. `cls2[165]` +04 = 0x0221CD29 and
    `criteria[333]` = `{0xFFFF, 0x0223CAD9, 0x0002, 0x085C}` also resident.
  * **The cards DID reach the Graveyard**: side 0 GY holds
    `{Reload 0x16D9, 0x1859, 0x1859}` — two copies of the donor, i.e. the discard
    and the mill both completed. A third copy is still in the 33-card deck.
  * **NO effect state whatsoever**: `[0x0229AAFC+0x70] = 0`, `[+0x7C] = 0`,
    candidate count 0. Contrast the earlier FIELD test, which reached phase 0x80.

**CONCLUSION: the leave dispatcher is never entered for a hand->GY discard or a
deck->GY mill.** The mask table refines *which field-leaves* fire; it does not
extend the trigger to other source zones. So this is NOT a wrong-mask problem and
no data row can fix it — the registration is correct but the code that reads it
never runs.

Consistent with the repo memory `otn-leave-trigger-cls2`: "⚠️ OTN wording is
'removed from the field' ('leaves the field' = 0 hits)", and with the KB naming
`leave.leave_hook` a *leave-FIELD* per-cid switch.

**Dispatcher entry** = `0x021C7FD2` (`push` + `sub sp,#0x1E8`, matching the huge
[sp+0x210] frame). It has **zero BL callers** and **no pointer to it anywhere in
ov3 or arm9**, so it is reached by neither a direct call nor a table — how it is
invoked is still unidentified, and that is the thread to pull if this is pursued.

### The cheap decisive experiment (engine limitation vs my bug)

**Discard a NATIVE Dandylion 0x19FE from the hand.** It carries the same mask
0x0800 in the same table and is dispatched by the same code. If native Dandylion
does NOT summon its Fluff Tokens on a discard, then OTN simply never implements
"sent to the GY from hand/Deck" and Eclipse Wyvern is already behaving exactly
like the engine's own equivalent card. If it DOES, then something specific to this
donor is wrong and the dispatcher is reachable after all.

### If true from-anywhere is required

It needs a HOOK on the generic relocation path rather than a table row — candidates
`0x021C7484(side, src_zone, ref, side, ...)` (the KB's relocation primitive) or
`0x021D1300` (the generic relocation applier, which the Deck->GY/banished mover
0x021D1DAC tail-calls). Both are SHARED paths that also run in puzzles, so the stub
must live in ov3 dead code (132 B currently free) and would have to build the
trigger descriptor itself rather than piggy-back on the dispatcher. Substantial new
RE — not a data edit.

## SESSION 6b — engine limitation RULED OUT; mask semantics decoded; cause still open

**IN-GAME (user): a native Dandylion DISCARDED from the hand DOES summon its Fluff
Tokens.** So the leave dispatcher IS reached for hand->GY, OTN does implement
"sent to the GY from anywhere", and the previous session's "engine limitation"
hypothesis is **WRONG — discard it.** The fault is specific to this card.

### The leave-mask is a CONJUNCTION OF REQUIREMENTS (decoded @0x021C8116..0x021C81EA)

`r5` starts at 1 (eligible); each SET mask bit imposes a condition and clears r5
on failure. If r5 survives, `[sp+0x18] = 1` @0x021C81F0 (armed). Decoded bits:
  * `0x0001` -> `[sp+0x98]` (side) must equal r6
  * `0x0002` -> `0x021A0DF8(r6, [sp+0xA0])` must not be 0xFFFF
  * `0x0004` -> **`[sp+0x2C]` != 0 = LEFT THE FIELD**
  * `0x0008` -> `[sp+0x94]` != 0        * `0x0010` -> `[sp+0x54]` != 0
  * `0x0020` -> `[sp+0x94]` == 0        * `0x0080` -> `[sp+0x44]` != 0 (battle)
  * `0x0100` -> `[sp+0x44]` == 0        * `0x0200` -> `[sp+0x08]` != 0
  * `0x0400` -> **`[sp+0x90]` != 0 = DESTROYED**
  * `0x0800` -> **`[sp+0x144]` != 0 = TO-GY**
So **mask 0x0800 means "destination is the GY" and imposes NOTHING else** — no
field requirement, which is exactly why Dandylion fires from the hand. The row is
semantically right. (This also explains the KB's 0x0C04 = 0x0800|0x0400|0x0004 =
"destroyed AND left the field AND to the GY".)

### The table surgery is PROVABLY CLEAN

Byte-diffed the built ROM's mask table against pristine ov3: exactly one row lost
(the phantom `0x16F5/0x0800`), exactly one added (`0x1859/0x0800`), **zero masks
changed on any surviving card**, still sorted, count still 152. The new
bidirectional `_insert_sorted` slide is correct.

### So the remaining difference vs Dandylion is NOT the registration

Both have mask 0x0800 and a cls2 record with +0C = +10 = 0. Dandylion has NO
criteria row and NO other registration anywhere (full ov3+arm9 cid scan: only its
resolver literal, its token-table row 0x0226D554 = {cid, token 0x0F55, count 2,
mode 1}, and its mask row). The differences left are:
  1. **the resolver** — ours is Gold Sarcophagus's 0x0221CD29, whose phase-0x80
     arm opens with an UNIDENTIFIED gate `0x021BABE8(side)` that returns 0 -> bail;
  2. we additionally own a criteria row (irrelevant to triggering);
  3. our donor is a card_type-promoted vanilla.
⚠️ Hypothesis (UNPROVEN): the trigger arms correctly but Gold Sarcophagus's
resolver bails for a non-field source — i.e. the failure is in the ACTION, not the
trigger. Consistent with the savestate showing no effect state at all, but NOT
distinguished from "never armed" by any measurement taken so far.

### NEXT EXPERIMENT — one-shot GDB (plan the whole thing offline first)

Per the CLAUDE.md preflight: connect ONCE on port 3333, in an active NORMAL duel,
arm all breakpoints up front, collect in a single wait window, write to a file.
  * **bp 0x021C8104** (mask-table lookup) — record `r4`. Does it fire with
    r4 == 0x1859 on a DISCARD? -> is the dispatcher even reached for our cid?
  * **bp 0x021C81EE** (the arming store) — record `r5`/`[sp+0x18]`. -> did the
    mask conjunction survive?
  * **bp 0x0221CD28** (resolver entry) and **bp 0x0221CD3E** (the `bl 0x021BABE8`
    gate) — record `r0` on return. -> does the action bail, and where?
Run the same set for a Dandylion discard as the CONTROL; the first breakpoint that
fires for Dandylion but not for us localises the divergence exactly.

## SESSION 7 — LIVE GDB: field path PROVEN end-to-end; discard is a SEPARATE dispatcher

### Instrument caveats that cost three sessions (all mine, all fixed)

1. A 608-byte `read_mem` of the mask table returned **E02** -- melonDS rejects large
   reads. Replaced with a BINARY SEARCH over each cid-sorted table (~40 reads of
   <=64 B). See `_find_row`.
2. `Tee` called `print(line)` without `flush=True`. Python block-buffers stdout when
   it is not a tty, so the operator saw NOTHING until the process exited -- including
   the "discard now" cue. The script was working correctly and silently the whole
   time; two "NOTHING FIRED" results were simply nobody playing.
3. The collect loop `continue`d silently on any unmatched PC, so a real hit at an
   unexpected PC was indistinguishable from no hit. Now EVERY stop is logged with
   its PC, and a `total stops seen:` line makes zero-stop runs self-identifying.
⚠️ Breakpoints DO work in this melonDS build (proved with `--selftest` on the
replay-log poster 0x021C3BC8). The earlier "the stub cannot sustain 3 breakpoints"
theory was WRONG -- discard it.
⚠️ Breakpoints SURVIVE a dropped connection: stale ones from a previous run kept
firing (as UNMATCHED PCs) in the next. Restart melonDS between runs, or they add
noise -- though in one run they luckily supplied the whole action-side trace.

### FIELD -> GY IS FULLY PROVEN WORKING (battle destruction)

```
mask-lookup:   dispatcher REACHED, r4=0x1859
mask-eligible: r5=1  -> ARMED
pc=0x0221cd28  resolver entered
pc=0x0221cd42  r0=0x1   -> the 0x021BABE8 gate PASSES
pc=0x0221cd50  r0=0x7   -> the Deck search found SEVEN Level 7+ Dragons
```
So the mask row, the cls2 record, the criteria row and Gold Sarcophagus's resolver
are all correct and functioning. **This also permanently settles the old open
question**: a TRIGGER does drive that Spell-activation resolver through its
0x80 -> 0x7F -> 0x7E phases.

### DISCARD IS A DIFFERENT DISPATCHER ENTIRELY

* On a discard the field-leave dispatcher at **0x021C8104 is never reached -- not
  for our card and NOT for Dandylion** (zero hits across a 150 s window), yet
  Dandylion's tokens still appear.
* The leave-mask table 0x0226EC1C has **exactly ONE literal reference in all of
  ov3** (pool 0x021C8324, loaded by `LDR r1` @0x021C8104), so the discard path
  cannot be using it.
* Dandylion carries **no second cid registration anywhere** (full ov3+arm9 scan:
  its resolver literal 0x02207ED8, token-table row 0x0226D554, mask row 0x0226ECD8).
  So its discard dispatch must come from a per-cid SWITCH encoding cids as
  base+-imm -- ungreppable, per `thumb-stack-based-switch-footgun`.

**MEASURED: a DISCARD dispatches as `event 0x1F`, `zone 0x0E` (GY), `selector 2`
(cls2)**, descriptor at the GLOBAL **0x0229A7FC**:
`raw = fe19 00 0e 1f 02 00 01 01 00 00 00 26 00 00 00`
(+0 cid 0x19FE, +2 side, +3 zone, +4 event, +5 selector, +7/+8 slot4/slot5-done, +0C 0x26)

**The invoker is generic** -- entry **0x0224AEB8**, and its body is just:
`bl find_event_handler 0x0224A118` -> `ldr r2,[r0,#4]` -> `blx r2` (LR = 0x0224AF03).
It works purely off the descriptor. **Therefore, if a descriptor with cid 0x1859 +
event 0x1F + selector 2 is ever built, our cls2 record MUST be found and our
resolver MUST run.** Our card owns exactly such a record. So the failure is that
**no descriptor is being built for our cid on a discard** -- the divergence is in
whatever ENUMERATES cards for the 0x1F event, upstream of the invoker.

Invoker callers (8): 0x021D5AA4 (the resolution driver -- descriptor already built,
stores the result to [r6,#0x70]), 0x02208DCA, 0x0221803E, 0x0221D324, 0x0221F472,
0x02228F92, 0x02258ECE, 0x0225BCF8. The descriptor global 0x0229A7FC has ~24
literal-pool references, so the builder was not pinned statically.

### NEXT EXPERIMENT (script ready: `--invoker`)

`... gdb_eclipse_wyvern_discard 120 --invoker` breaks on 0x0224AEB8 and dumps
{cid, side, zone, event, selector} for EVERY dispatched event. Discard an Eclipse
Wyvern and a Dandylion.
  * donor cid never appears -> nothing builds a descriptor for it; find the
    enumerator that decides which cards get a 0x1F event (start from the 8 callers).
  * donor appears with event 0x1F/sel 2 -> find_event_handler is failing to match a
    record we know exists, i.e. a table problem instead.

## SESSION 7b — PROVEN: no descriptor is built for our cid on a discard

`--invoker` (breakpoint 0x0224AEB8, dumping every dispatched descriptor) over a
120 s window containing both discards:
  * **Dandylion 0x19FE appears 3x**: `zone=0x0e event=0x1f sel=2`, and its resolver
    runs each time.
  * **Our cid 0x1859 NEVER appears** -- not once, across 17 dispatches.
  * (Also seen: Dragon Ravine 0x2359 polled 12x with `zone=0x0a event=0x00 sel=3`.)

Since the invoker is generic (`find_event_handler` -> `blx [rec+4]`) and our card
owns a matching cls2 record, this is conclusive: **the failure is that nothing
ENQUEUES an event for our cid on a discard.** Not a registration problem, not a
table problem -- an enumeration problem upstream.

### THE EVENT QUEUE (found while chasing the 0x1F literal)

⚠️ First, a dead end worth recording: grepping for `movs rX,#0x1F` as the event code
is WRONG. Those sites are BIT-MASKS. The descriptor is UNPACKED from a packed event
word (in r4) at 0x021D30A4..0x021D313E:
  * `desc[+3] ZONE`  = (r4 >> 16) & 0x1F      (`movs #0x1f; lsls #0x10; ands r4; lsrs #0x10`)
  * `desc[+4] EVENT` = (r4 >> 25) & 0x7F      (`movs #0x7e; lsls #0x18; ands r4; lsrs #0x19`)
  * `desc[+2] side`, `desc[+5]`, `desc[+6]`, `desc[+0xC]`, `desc[+0xE]` likewise.
So **the event code is never a literal anywhere** and cannot be grepped -- the same
class of trap as the base+-imm cid switches.

**The queue itself**: entries at **0x0229A37C**, stride **0x24**, count at
**[0x0229A9FC + 0x54]**, capacity **0x20** (see 0x021D30D0..0x021D30EE, which
appends: `r5 = 0x0229A37C + count*0x24`, then `count+1` stored back). The function
around 0x021D3030-0x021D3168 DRAINS this queue and builds descriptors from it.

### STATIC HUNT FOR THE ENQUEUER -- how far it got, and where it stops

**The enqueue function is `0x021D2FC4`.** Its tail (0x021D30D0..0x021D30EE) scans the
existing queue and, on no match, APPENDS: `r5 = 0x0229A37C + count*0x24`, then
`count+1 -> [0x0229A9FC+0x54]`, capped at 0x20.
**It has exactly FIVE callers**: `0x0219ED3C`, `0x021D3222`, `0x021D3402`,
`0x021D3430`, `0x021D3E0E`. One of these posts the sent-to-GY event.

⚠️ **Two searches for the event code came back EMPTY, and both are worth recording
so nobody repeats them:**
  * no literal-pool word anywhere in ov3 has `(w >> 25) & 0x7F == 0x1F` (i.e. the
    event is not baked into a packed constant);
  * no `movs rX,#0x1F` is followed by `lsls rY,rX,#25` (it is not built by a
    constant shift either).
**CONCLUSION: the event code is a RUNTIME PARAMETER**, passed down into
0x021D2FC4 by its caller -- so it cannot be located by grepping for 0x1F in any
form. This is the third instance in this card of the same lesson: cids are hidden
in base+-imm switches, event codes are packed at runtime; **static grep cannot find
either.**

### NEXT EXPERIMENT (live -- static is exhausted)

ONE breakpoint on the enqueue entry **`0x021D2FC4`**, dumping the packed event word
argument and **LR** on every call, while discarding a Dandylion and then an Eclipse
Wyvern:
  * LR identifies WHICH of the five callers posts the sent-to-GY event;
  * the packed word shows the cid/zone/event it carries;
  * if the enqueue is never called for our cid, step one level up to that caller
    and find its admission gate.
Add a `--enqueue` mode to `scratch/gdb_eclipse_wyvern_discard.py` (the existing
`--invoker`/`--dandylion` modes are the template; both are proven working).

### (superseded) earlier plan

Find the ENQUEUER -- whoever writes a packed event word into 0x0229A37C / bumps
[0x0229A9FC+0x54] for a card sent to the GY, and decides Dandylion qualifies while
our donor does not. Two cheap options:
  * **static**: xref the queue base 0x0229A37C and the counter 0x0229A9FC, and look
    for the gate that admits a card (likely a card_prop/property test rather than a
    cid table, since Dandylion has NO cid registration for this path);
  * **live** (one GDB session): breakpoint the append site **0x021D30E0** and dump
    the packed word + cid for a Dandylion discard vs an Eclipse Wyvern discard --
    if our card never reaches the append, step back to its caller.

⚠️ Do NOT assume the enumerator is cid-keyed. Dandylion carries no registration for
this path, so admission is more likely derived from a card PROPERTY. The donor is a
card_type-promoted vanilla, which is the most obvious way it could differ.

## Open questions

1. **Exact-identity vs approximation for clause 2.** No per-instance "I banished
   *that* card" pointer was found; Gold Sarcophagus's `cls0[569]` has no delayed
   slot (+08/+10/+14 NULL), and the `code=0x41` call is replay logging (ruled out
   above). The practical substitute is "the Lv7+ LIGHT/DARK Dragon in my banished
   zone whose source zone is Deck (0x0D)". This is faithful in the common case and
   diverges only when another Deck-banish of a matching monster happened first.
   **User decision needed** — see the report.
2. Which of composition options (a)/(b)/(c) above is correct.
3. Does `0x021E5201` fire for a banish **from the GY specifically**, or for any
   banish (including from hand/field)? Eclipse Wyvern requires GY-source only.
   Cyber Ouroboros's printed text is source-agnostic, so the tag may be broader
   than clause 2 needs and require a source check in the resolver.
4. Whether a *trigger* resolver can reuse Gold Sarcophagus's pick/banish phase
   machine, which is written for a Spell **activation**.

## Next experiment

1. Disassemble Cyber Ouroboros's resolver `0x022065B9` and the classifier
   `0x021E5201` to determine (i) the event-code value the banish trigger delivers
   in `desc[+0x04]`, and (ii) whether the source zone is available to the resolver
   (which would settle open question 3 statically, no emulator needed).
2. Settle the composition question by checking whether `0x021E5201` and the
   Sangan sent-to-GY registration deliver **different** `desc[+0x04]` event codes
   to the same cid. If they do, option (b) — one record, one resolver, switch on
   the event code — is the clean build and avoids the shadow entirely.
3. Only then build. Nothing should be written to the ROM or the allocation ledger
   until 1 and 2 are answered.

## Design for clause 1 (evidence-backed, not yet built)

- **Donor:** Divine Dragon Ragnarok `0x1859` (keep cid; retune ATK + name/text).
- **Trigger:** Sangan's any-means sent-to-GY registration, per the shipped
  `patch_gravekeepers_recruiter.py`: keep/add donor membership in the sent-to-GY
  leave-dispatcher list `0x0226E904`, plus a cls2 record with `+0C = 0` and
  `+10 = 0` (the matched partner of that list membership). UNVERIFIED for this
  donor — Ragnarok's native list30 membership must be checked before relying on it.
- **Candidate pool:** a new populate row `[a=0x1859][b=filter param][h=ov5 filter
  wrapper][fl=0x0E-style deck criteria]`, inserted **count-neutrally** (drop a
  phantom) to keep the 1388-row table sorted and sized.
- **Filter:** custom Thumb-1 in the ov5 cave — Level >= 7 AND attribute in
  {LIGHT, DARK} AND race == Dragon. Native filters test one property only (the
  Recruiter hit the same wall), and the criteria word's top byte encodes exactly
  one race + one attribute, so LIGHT-or-DARK cannot be expressed as a plain row.
- **Action:** `0x021D21DC(side, ref, cid, 0x80)` from a resolver, replacing the
  Recruiter's add-to-hand `0x02207EF5`.

**Not yet proven for clause 1:** that a *trigger* resolver can drive the
Sarcophagus pick/banish phases, and Ragnarok's list30 membership. Both are static
checks, not emulator work.

## SESSION 8 — the sent-to-GY event poster FOUND (static); admission chain fully mapped

All of this session is **static disassembly of the pristine ROM**
(`data/over_the_nexus/working/rom.nds`) — no emulator was used, no ROM bytes were
written, no ledger entry was made. Scripts added: `scratch/disasm_event_enqueue.py`,
`scratch/scan_event_post.py`, `scratch/scan_event_post2.py`, `scratch/scan_lit_refs.py`,
`scratch/disasm_range.py`, `scratch/scan_event1f_sites.py`,
`scratch/scan_event_code_map.py`, `scratch/scan_gy_trigger_membership.py`,
`scratch/sim_reloc_cid_switch.py`.

### ⚠️ Session 7b's "static grep is exhausted" conclusion was WRONG — twice over

Two negative results from session 7b were **artefacts of a wrong field width**, and
repeating them would waste another session:

1. **The event field is bits 25..30, six bits — not seven.** The unpacker uses
   `movs #0x7e ; lsls #0x18` = mask `0x7E000000`, then `lsrs #0x19`. So event 0x1F
   is the constant **`0x3E000000`**, which a Thumb-1 compiler spells
   `movs rX,#0x3E ; lsls rX,rX,#0x18`. Session 7b searched for `movs #0x1F` followed
   by `lsls #25` and for pool words masked with `0x7F` — neither could ever match.
2. **Event codes ARE plain `movs #imm` immediates in this engine.** The leave
   dispatcher picks its own event code that way at `0x021C80A2`/`0x021C80A6`
   (`movs r0,#0x17` battle / `movs r0,#0x1D` otherwise, then `str r0,[sp,#0x1c]`).
   The claim "the event code is a RUNTIME PARAMETER, so it cannot be located by
   grepping for 0x1F in any form" is **false** — it is a runtime parameter *to the
   poster*, but its callers pass literals.

### CONFIRMED — the packed event-word layout (from the unpacker at 0x021D3168)

```
[0..15]  cid                          [16..20] zone          -> desc[+3]
[21..23] cls selector -> desc[+5]     [24]     flag          -> desc[+6]
[25..30] event code   -> desc[+4]     [31]     side          -> desc[+2]
```

Decoded at `0x021D3168..0x021D31B4`; the packers at `0x021D3256`, `0x021D33B0`,
`0x021D1D5C` and `0x021D3DC2` all build it with the same shifts.

### CONFIRMED — the event queue has TWO arrays, selected by enqueue arg0

`enqueue = 0x021D2FC4(r0 = queue_sel, r1 = packed_word, r2, r3)`:
  * `r0 != 0` → array **0x0229A7FC**, count `[0x0229A9FC+0x40]`, cap **0x10**
    (appended at 0x021D302A..0x021D303E; the cap is checked at 0x021D3DEC).
  * `r0 == 0` → array **0x0229A37C**, count `[0x0229A9FC+0x54]`, cap **0x20**
    (appended at 0x021D30E0..0x021D30EE).

Both are stride **0x24**. ⚠️ Session 7b recorded only the second and called the
region 0x021D3030–0x021D3168 "the DRAIN" — it is not, it is the *merge/append tail
of the enqueue itself*. **The descriptor measured in session 7b lived at
0x0229A7FC**, i.e. it came from the `r0 != 0` queue.

### CONFIRMED — the event-code vocabulary (a map that did not exist before)

`0x021D3230(r0 = side, r1 = zone_index, r2 = EVENT_CODE, r3 = arg)` is the
**selector-1** event poster: it packs `cid | zone<<16 | 1<<21 | event<<25 | side<<31`
and hands it to the register-prim `0x021D3168`. It has **60 call sites**, and at 56
of them `r2` is a literal `movs`, giving the vocabulary:

```
0x00 x9   0x01 x1   0x02 x4   0x06 x6   0x0C x2   0x0D x1   0x0E x2
0x10 x11  0x13 x5   0x15 x6   0x16 x1   0x17 x1   0x18 x4   0x19 x2
0x1F x1   (0x02244F8A — a cid-0x1354-specific loop, not the generic path)
```

### ⭐ CONFIRMED — the sent-to-GY poster is the GENERIC RELOCATION APPLIER 0x021D1300

`0x021D1300` (the function `0x021D1DAC`, the Deck→GY/banished mover, tail-calls —
already named in session 6 as "the generic relocation applier") ends with the only
**selector-2** event post in the engine:

```
0x021D1D5C..0x021D1D90   word = cid | dest_zone<<16 | 1<<22 | event<<25 | side<<31
0x021D1D80  movs r2,#1 ; lsls r2,r2,#0x16     <- SELECTOR 2, hardcoded
0x021D1D92  bl 0x021D3168                     <- register-prim
```

with the **event code taken from arg0** (`[sp+4]`, stored at 0x021D1304) and the
**zone from the DESTINATION zone** (`[sp+0x30]`, bits 19..22 of the card word).
This is byte-for-byte the descriptor shape session 7b measured for a Dandylion
discard: `zone=0x0E, event=0x1F, sel=2`. **Only 3 callers**: `0x021C6CB8`,
`0x021D1F06`, `0x021D2450`.

Prologue decode of `0x021D1300(r0 = event_code, r1 = &card_word, r2 = flags, r3)`:
`[sp+0x38]` ref (bits 0..8), `r7` side (bit 9), `[sp+0x34]` **SOURCE zone**
(bits 10..13), `[sp+0x2C]` DESTROYED (bit 15), `[sp+0x30]` **DEST zone**
(bits 19..22), `r5` = **cid** (via `0x0229C33C[ref*8] & 0x3FFF`).

### CONFIRMED — the post is gated on `[sp+0x14]`, and how that gate is built

```
0x021D1308  [sp+0x14] = 0                       (default REJECT)
0x021D1930..0x021D19BA  arm chain -> 0x021D199E (=1) or 0x021D19BC (=0),
                        converging on the store at 0x021D19BE.
                        The arms test [sp+0x2C] DESTROYED, [sp+0x20],
                        [sp+0x34] source zone == 0x0D, [sp+0x1C], r7 vs r4,
                        and 0x02023EE4([sp+0x10]) — none of them cid-derived.
0x021D1B98..0x021D1CD8  a per-cid OVERRIDE switch (base±imm, ungreppable)
0x021D1D54  [sp+0x14] = <override result>
0x021D1D58  if [sp+0x14] == 0 -> return WITHOUT posting
```

**The per-cid override switch was simulated exhaustively** over cids 0..0x26FF
(`sim_reloc_cid_switch.py`, which refuses rather than guesses on any unmodelled
instruction — the `thumb-stack-based-switch-footgun` trap). It covers exactly
**20 cids**:

```
leaf 0x021D1CDA: 0x0E1C 0x0E1D 0x0EBA 0x1294 0x1C08 0x1CE9 0x1CF1 0x1DC0 0x2145
leaf 0x021D1CDE: 0x1BE9 0x2262 0x22FC 0x230C 0x230D 0x2391
leaf 0x021D1CF2: 0x1D98      leaf 0x021D1D0A: 0x210B
leaf 0x021D1D1A: 0x2189      leaf 0x021D1D3E: 0x17BB 0x1CF6
```

**Neither Dandylion 0x19FE nor the donor 0x1859 is in it**, so it is a special-case
refinement, NOT the general admission gate. (Note **0x1CF6 = Cyber Ouroboros** —
clause 2's native template — has a bespoke arm here. Relevant when clause 2 is built.)

### RULED OUT — the downstream admission tests reject neither card

  * `0x021D3168` drops the event unless **`0x021EDA08(desc, 0)`** returns non-zero.
  * `0x021EDA08` returns `[sp+0x14]`, which is set at `0x021EDC64`/`0x021EDC90` from
    **`0x0224AD94(desc, arg)`** — the cls2 invoker the KB already names.
  * `0x0224AD94` calls `find_event_handler 0x0224A118`; if **no record is found
    (r4 == 0) it branches to 0x0224AE3E with r6 still 1 and returns 1 = ACCEPT**.
    When a record IS found it runs the condition `[rec+0x0C]`, and `+0C == 0` skips
    the call (`cmp r2,#0; beq` @0x0224AE08), leaving r6 = 1 = ACCEPT.
  * Our record and Dandylion's are the **same shape** (`+0C = +10 = 0`), so this
    chain accepts both. **The divergence is not here.**

### RULED OUT — a missing table registration (data-side intersection test)

`scan_gy_trigger_membership.py` scanned every 2-byte-aligned u16 in ov3 **and**
arm9 for five cards that all trigger on "sent to the GY by any means", with
Dandylion IN-GAME PROVEN from a hand discard:

    Dandylion 0x19FE, Peten the Dark Clown 0x17C5, Jinzo - Returner 0x1D9B,
    The White Stone of Legend 0x1EAA, Skull-Mark Ladybug 0x12A2

Every one of them has exactly **one leave-mask row** (0x0226EC6C / 0x0226ECB0 /
0x0226ECD8 / 0x0226ED44 / 0x0226ED60, all inside 0x0226EC1C + 152×4) and **one cls2
record** (cls2[57] / [159] / [203] / [339] / [387]) — and **nothing else in common**.
That is exactly the pair our donor already owns. **There is no third table to
join**, which finally closes the question session 6b left open.

### Where that leaves it

The chain is now mapped end to end, and every link except one has been shown to
treat the donor and Dandylion identically:

```
relocation (3 call sites) -> 0x021D1300 -> [sp+0x14] gate -> pack sel-2 word
  -> 0x021D3168 -> 0x021EDA08 -> 0x0224AD94 (find_event_handler) -> enqueue
  -> descriptor at 0x0229A7FC -> invoker 0x0224AEB8 -> our cls2 +04
```

Session 7b proved the far end never sees cid 0x1859. Everything downstream of
`0x021D1300` is now shown to be cid-blind for records of our shape. **So either
`0x021D1300` is never entered for the donor's discard, or its `[sp+0x14]` gate
rejects it** — and since the gate's arms are cid-independent, "never entered" is the
strong hypothesis. That cannot be settled statically: the three callers are reached
from the card-movement code, whose own dispatch uses the same base±imm switch idiom.

## Next experiment (ONE-SHOT GDB — the plan is complete, nothing left to decide offline)

Per the CLAUDE.md preflight: connect ONCE on port 3333, active NORMAL duel, arm up
front, one wait window, transcript to a file. **ONE breakpoint**, because it answers
both halves at once:

  * **bp `0x021D1D58`** (`cmp r0,#0` on `[sp+0x14]`, immediately before the post).
    At that instruction `r5` = **cid** and `r0` = the gate verdict.
      - fires with `r5 == 0x19FE, r0 != 0` on a Dandylion discard → instrument good;
      - never fires with `r5 == 0x1859` on an Eclipse Wyvern discard → **0x021D1300
        is not entered for our card**; step up to its three callers
        (0x021C6CB8, 0x021D1F06, 0x021D2450) and find which one handles hand→GY
        and what it dispatches on;
      - fires with `r5 == 0x1859, r0 == 0` → the gate rejects; read back which arm
        of 0x021D1930..0x021D19BA was taken (the arms are zone/flag-keyed, so this
        would mean the donor's card word differs — most likely `card_type`, the one
        way a promoted vanilla still differs from a native effect monster).

Add this as a `--reloc` mode to `scratch/gdb_eclipse_wyvern_discard.py`; the existing
`--invoker` / `--dandylion` modes are the working template.

⚠️ Restart melonDS before the run — session 7 established that breakpoints **survive
a dropped connection** and stale ones from a previous run keep firing as noise.

## SESSION 9 — 3DS CROSS-REFERENCE: every data-side hypothesis is now DEAD

Static only, both builds. Nothing written to a ROM, no ledger entry. Scripts added:
`scratch/scan_3ds_gy_registration.py`, `scratch/diff_cardprop_3ds_vs_nds.py`,
`scratch/scan_3ds_eclipse_records.py`, `scratch/find_3ds_cls_tables.py`.

The 3DS build **ships Eclipse Wyvern with clause 1 working** (cid 0x26E5 in the
shared namespace) *and* ships Dandylion 0x19FE. So instead of inferring the
registration from NDS analogues, it can be read off a working implementation.
⚠️ 3DS **addresses** never enter the NDS namespace — shapes and roles only.

### ✅ The leave mask is CONFIRMED CORRECT — 3DS Eclipse Wyvern also carries 0x0800

The 3DS leave-mask table is at address **0x007A18FC**, stride 4, **243 rows**,
cid-sorted, `{u16 cid, s16 mask}` — the same shape as the NDS `0x0226EC1C`×152.
Membership:

    row[ 16] 0x12A2 Skull-Mark Ladybug         mask=0x0800
    row[ 33] 0x17C5 Peten the Dark Clown       mask=0x0800
    row[ 44] 0x19FE Dandylion                  mask=0x0800
    row[ 72] 0x1D9B Jinzo - Returner           mask=0x0800
    row[ 80] 0x1EAA The White Stone of Legend  mask=0x0800
    row[174] 0x26E5 **Eclipse Wyvern**         mask=0x0800

Konami's own Eclipse Wyvern uses **exactly the mask value session 5 chose**. The
mask row is right.

### ✅ card_prop is CONFIRMED CORRECT — byte-identical to the shipped card

The two builds share the **same card_prop layout**, proved by a card present in
both: Divine Dragon Ragnarok's record is **byte-identical across builds**
(`5998253241100200` in the 3DS DB and in the pristine NDS ROM). That validates the
whole cross-reference method, not just this comparison.

    3DS  Eclipse Wyvern  0x26E5           e526283243100200
    NDS  donor PATCHED   0x1859           5918283243100200
                                          ^^^^ cid halfword only

**Our patched card_prop is identical to the 3DS's shipped Eclipse Wyvern in every
byte beyond the cid.** Level 4 / LIGHT / Dragon / 1600 / 1000 / Effect Monster.

⚠️ This **kills the leading hypothesis** carried since session 7b — "the donor is a
card_type-promoted vanilla, which is the most obvious way it could differ". It does
not differ. The promotion produced precisely Konami's own record.
(Bit 15 is part of the card_type field, not a separate flag: pristine Ragnarok
0x9859 decodes as Normal Monster, patched 0x1859 as Effect Monster, and 3DS
Eclipse Wyvern 0x26E5 likewise — the decoder reads card_id as bits 0..14.)

### ✅ The cls record SHAPE is CONFIRMED CORRECT — and Eclipse Wyvern owns TWO

Located the 3DS cls tables on evidence rather than sortedness (a dense sorted u16
list is also "sorted" sampled every 24 bytes, which produced obvious false
positives on the first pass — rows whose "slots" were plainly pairs of cids). The
grounded test: cid strictly increasing, `pad == 0`, and slot1 either NULL or a
pointer inside the image.

    Eclipse Wyvern 0x26E5, TWO CONSECUTIVE rows in one table:
      A  {+04 0x0045E5D0, +08 0, +0C 0x0049BD9C, +10 0x004001F4, +14 0x004774CC}
      B  {+04 0x0043D564, +08 0, +0C 0, +10 0, +14 0}
    Dandylion 0x19FE, one row:
      {+04 0x00463C48, +08 0, +0C 0, +10 0, +14 0}

**Record B is exactly Dandylion's shape, and exactly the shape our NDS build
writes** (`{+04 = 0x0221CD29, rest 0}`). Record A carries the `+0C` condition and
the `+10` classifier tag — the same shape 3DS Cyber Ouroboros 0x1CF6 has
(`{+04, +0C, +10, +14}` set), i.e. the *banished-from-GY* clause.

So the two-record composition the findings sketched in the 3DS section is real, and
our single clause-1 record matches the right one of the pair.

### ⛔ AND THE MASK ROW CANNOT BE WHAT MAKES A DISCARD WORK

Checked this session: the leave-mask table `0x0226EC1C` has **zero literal
references in arm9** (as well as the single known one in ov3, at `0x021C8104`).
Session 7 measured that `0x021C8104` is **never reached on a discard — not for our
card and not for Dandylion**, yet Dandylion fires. Therefore:

**Dandylion's discard trigger does not consult its mask row at all.** The mask row
governs *field* leaves only. Adding it in session 5 was correct and necessary, but
it was never going to make a discard fire — and no further data edit will either.

### Where this leaves the diagnosis

Every data-side difference is now eliminated by direct comparison with a shipped,
working implementation of the same card:

| thing | our NDS build | reference | verdict |
|---|---|---|---|
| leave mask | `{0x1859, 0x0800}` | 3DS EW `0x0800` | ✅ identical |
| card_prop | `5918283243100200` | 3DS EW `e526283243100200` | ✅ identical beyond cid |
| cls record shape | `{+04, rest 0}` | 3DS EW record B / Dandylion | ✅ identical |
| criteria row | present | 3DS EW has one too | ✅ present in both |

Combined with session 8 (the whole dispatch chain downstream of the relocation
applier `0x021D1300` is cid-blind for a `{+04, rest 0}` record), **there is no
remaining registration hypothesis.** The failure is in whether `0x021D1300` runs
for this card's discard at all.

## Next experiment — a DATA BISECT, no emulator needed

The one thing our donor has that Dandylion does **not** is the **criteria row**
(Dandylion has no populate/criteria entry anywhere). And the one thing that is
genuinely untested is whether Gold Sarcophagus's resolver `0x0221CD29` behaves on a
hand-sourced trigger. Both can be settled by building test ROMs and playing them —
cheaper and more reliable than another one-shot GDB session:

1. **Clone Dandylion exactly onto the donor.** Same mask row, cls2 record
   `{+04 = 0x02207A09 (Dandylion's own resolver), rest 0}`, and **drop the criteria
   row**. Discard it.
     * Fluff Tokens appear → the registration is fine and the fault is in
       Gold Sarcophagus's resolver on a hand-sourced trigger (or in the criteria
       row's presence). Go to step 2.
     * Nothing → something about the donor **cid** itself is not enumerated, which
       is a much stronger and stranger claim, and *then* the GDB run at
       `0x021D1D58` (session 8's plan) is worth the session.
2. If step 1 fires, re-add our resolver but keep the criteria row dropped, then
   re-add the criteria row — the first re-addition that breaks it is the cause.

This is a three-ROM bisect against an in-game observation, which is the project's
own standard of ground truth ("the emulator, not the compiler") without spending a
one-shot stub connection on a hypothesis that has a 50% chance of being answered by
a build instead.

## SESSION 10 — BISECT ROM BUILT: `rom_ew_bisect.nds` (one variable, tested on the control)

### Why this experiment and not the obvious one

The first plan was to clone Dandylion's effect onto the donor (its resolver plus a
token-table row) and see whether the donor made Fluff Tokens on a discard. **That
route is blocked, and the reason is worth recording.** Dandylion's resolver
`0x02207A09` does look the token row up generically — `bl 0x021A2EE0` at
`0x02207A1C` with `r0 = desc[+0]`, and `0x021A2EE4` loads the token-table base
`0x0226D484` — but immediately afterwards, at **`0x02207A2E`**, it drops into a
**per-cid `base±imm` switch** on `desc[+0]` (compares against 0x1D1E, 0x12D2,
0x0DF1, 0x0DF1−0x93 = 0x0D5E, …). A donor cid would land in whatever default arm it
hits, so the clone would not reproduce Dandylion's behaviour and a null result
would have been uninterpretable.

**Token table, mapped this session** (needed for that ruled-out plan, worth keeping):
base **0x0226D484**, stride **8**, **44 rows**, sorted by cid, layout
`{u16 cid, u16 token_cid, u16 count, u16 mode}`. Dandylion = row 26 =
`{0x19FE, 0x0F55, 2, 1}`. **Six phantoms** are available to sacrifice
(rows 4/5/6 = 0x0E43/0x0E47/0x0E8B, rows 29/31/33 = 0x1A37/0x1A8A/0x1BB1).

### The variable that is actually left

After sessions 8 and 9 there is exactly ONE registration difference between the
donor (silent on a discard) and Dandylion (fires on a discard, proven in-game):

    the donor owns a CRITERIA/POPULATE row; Dandylion owns none.
    (confirmed: 0x19FE appears nowhere in the 1388-row registry)

So test that variable — and test it on the card KNOWN to work, which makes the
result decisive in both directions rather than merely suggestive.

### `_build_ew_bisect.py` -> `data/over_the_nexus/working/rom_ew_bisect.nds`

Everything the shipped Eclipse Wyvern patch does, **plus one edit**: Dandylion
0x19FE gets a criteria row identical in shape to the donor's,
`{filt 0xFFFF, h 0x0223CAD9, flags 0x0002, extra 0x085C}`, inserted
count-neutrally over criteria phantom **0x19C0** (chosen automatically as the
phantom nearest the insert point; the donor's own phantom 0x18F8 is excluded).

Dandylion's resolver never consults the criteria registry, so **the row is inert
unless the mere existence of one changes how a card is enumerated** for the
sent-to-GY event.

Verified on the built ROM:
  * shipped `patch_eclipse_wyvern.verify()` **PASSES** — donor wiring untouched;
  * Dandylion mask row[47] mask **0x0800** — unchanged;
  * Dandylion `cls2[203] +04 = 0x02207A09` — unchanged;
  * Dandylion token row `{0x19FE, 0x0F55, 2, 1}` — unchanged;
  * Dandylion `criteria[420] = {0x19FE, 0xFFFF, 0x0223CAD9, 0x0002, 0x085C}` — **the
    only change**;
  * registry still sorted, still 1388 rows; donor row still at [333].

⚠️ THROWAWAY DIAGNOSTIC ROM. Not registered in `apply_all_patches`, claims nothing
in the allocation ledger, and deliberately alters a stock card (0x19C0 phantom
dropped). Do not ship it.

### How to read the result

Discard a **Dandylion** from the hand (Reload / Card Destruction / any discard cost):

  * **Fluff Tokens still appear** → the criteria row is INNOCENT. Every data-side
    hypothesis is then exhausted and the one-shot GDB run at **0x021D1D58**
    (session 8's plan, `--reloc` mode already added to
    `scratch/gdb_eclipse_wyvern_discard.py`) is justified.
  * **No Fluff Tokens** → **THE CRITERIA ROW IS THE CAUSE**: a card carrying one is
    not enumerated for the sent-to-GY event. Clause 1 then needs a candidate pool
    that is not a criteria row, or a resolver that does not need one.

Also discard an Eclipse Wyvern in the same session — it should still do nothing,
which confirms the ROM under test is the intended one.

### RESULT (in-game, user-reported): FLUFF TOKENS STILL APPEAR

Dandylion, carrying a criteria row identical in shape to the donor's, **still
summons its Fluff Tokens on a hand discard**. So:

**THE CRITERIA ROW IS INNOCENT.** Owning a criteria/populate row does not change
how a card is enumerated for the sent-to-GY event.

That was the last remaining data-side difference between the donor and Dandylion.
Combined with sessions 8 and 9, the registration is now exhaustively exonerated:

| candidate cause | how it was killed |
|---|---|
| wrong leave mask | 3DS ships Eclipse Wyvern with the same 0x0800 (session 9) |
| mask row missing/misplaced | byte-diffed; correct and sorted (session 6b) |
| card_prop / promoted vanilla | byte-identical to the 3DS shipped card (session 9) |
| cls2 record shape | matches Dandylion AND the 3DS clause-1 record (session 9) |
| find_event_handler / admission | accepts even a recordless cid (session 8) |
| **criteria row** | **Dandylion keeps working with one (this session)** |

No data edit can fix this. The failure is in whether the relocation applier
`0x021D1300` is entered for the donor cid on a discard at all -- which is exactly
what the session-8 breakpoint measures, and it is now the cheapest remaining
question rather than a speculative one.

### THE GDB RUN IS NOW JUSTIFIED

    .venv-1/Scripts/python.exe -m scratch.gdb_eclipse_wyvern_discard \
        120 notes/eclipse-wyvern-gdb-reloc.txt --reloc

Breakpoint **0x021D1D58** (`CMP R0,#0` on `[sp+0x14]`); there `r5` = cid and
`r0` = the post verdict. Checked against the disassembly: 0x021D1D54 stores
`[sp+0x14]`, 0x021D1D56 reloads it into r0, and r5 still holds the cid that
0x021D1D5C uses to build the packed word.

Reading it:
  * fires `r5=0x19FE r0!=0` on a Dandylion discard -> the instrument is good;
  * never fires for `0x1859` -> **0x021D1300 is not entered for our card**; go up
    to its three callers 0x021C6CB8 / 0x021D1F06 / 0x021D2450 and find which one
    handles hand->GY;
  * fires `r5=0x1859 r0==0` -> the GATE rejects; identify which arm of
    0x021D1930..0x021D19BA ran.

⚠️ Use `rom_eclipse_wyvern.nds`, NOT the bisect ROM -- the bisect ROM carries the
extra Dandylion criteria row, which is now known to be irrelevant but is one more
difference than the run needs.
⚠️ Restart melonDS first: breakpoints survive a dropped connection and stale ones
from an earlier run reappear as unmatched-PC noise.

## SESSION 11 — ROOT CAUSE FOUND: a HARDCODED cid switch gates the sent-to-GY event

### The measurement (live GDB, `--reloc`, breakpoint 0x021D1D58)

```
[1] reloc-post cid=0x19fe [sp+0x14]=0x1 -> POSTS the event   <<< DANDYLION (control)
[2] reloc-post cid=0x1859 [sp+0x14]=0x0 -> SKIPS (gate rejects) <<< ECLIPSE WYVERN
```

So `0x021D1300` **IS entered** for our card on a discard — session 8's "maybe it is
never entered" alternative is dead. **The gate rejects us.**

### The gate, decoded (0x021D1364..0x021D1392)

```
0x021D1364  ldr r0,[sp,#4]     ; the EVENT CODE (arg0)
0x021D1366  cmp r0,#0x1f       ; sent-to-GY?      -> [sp+0x18]
0x021D1388  ldr r0,[sp,#0x30]  ; DESTINATION zone
0x021D138A  cmp r0,#0xe        ; Graveyard?
0x021D138C  beq #0x21d1392     ; YES -> the per-cid GY switch
0x021D138E  bl  #0x21d1b98     ; NO  -> the 20-cid switch simulated in session 8
```

⚠️ That also explains session 8's puzzle: the 20-cid switch at 0x021D1B98 contained
neither card because **it is the NON-GY branch**. The GY branch is a separate,
much bigger comparison chain at **0x021D1392**.

### ⭐ THE SWITCH ADMITS EXACTLY 16 CIDS — AND THAT IS THE WHOLE FEATURE

Simulated the chain for every cid 0..0x26FF (`scratch/sim_gy_cid_switch.py`; the
simulator models only ldr-literal / movs / adds / subs / cmp / branches and treats
anything else as a leaf, so it stops rather than guessing). **9906 cids skip the
`[sp+0x14]` store entirely** (landing at 0x021D19C0 with the default 0 = reject).
Sixteen reach an **unconditional accept** (`movs r0,#1` @0x021D199E):

    0x1185 Cockroach Knight          0x12A2 Skull-Mark Ladybug
    0x1309 Sword of Deep-Seated      0x13E3 Archfiend of Gilfer
    0x1687 Outstanding Dog Marron    0x16F5 *** PHANTOM, no card_prop ***
    0x17C5 Peten the Dark Clown      0x19FE Dandylion
    0x1B8B Radiant Jeral             0x1C38 Amulet of Ambition
    0x1D97 Cross Porter              0x1D9B Jinzo - Returner
    0x1EAA The White Stone of Legend 0x1F35 Limiter Overload
    0x249D Tender of the Laval Vol.  0x24DB Snap Dragon

**The simulation reproduces the live measurement exactly**: 0x19FE reaches the
accept path, 0x1859 lands on 0x021D19C0 (reject). That is a validated model.

This list is the **same set** as the 0x0800 leave-mask family from session 5. So the
mask table and this switch are two halves of one feature, and **the switch is the
gatekeeper**: the mask row only refines *which field leaves* fire, while this
hardcoded chain decides who is enumerated at all.

### ⛔ CONSEQUENCE: "sent to the GY from anywhere" IS NOT DATA

A records-free Normal Monster donor **can never** have a sent-to-GY trigger, because
membership is compiled into a comparison chain. Every registration we verified in
sessions 8–10 was correct and none of it could ever have been enough. This retires
the whole line of investigation from session 5 onward.

### THE FIX — two options, and one of them is nearly free

**0x16F5 is the ONLY phantom among the 16** — a live arm in the switch that no real
card uses. Its acceptance is encoded at:

```
0x021D1472  adds r1,r0,#0 ; adds r1,#0xb6 ; cmp r5,r1 ; bgt ...   (range step)
0x021D147A  adds r0,#0xb6      ; r0 = 0x163F + 0xB6 = 0x16F5
0x021D147C  cmp  r5,r0
0x021D147E  beq  -> unconditional ACCEPT
```

  * **Option A — donor swap (pure data, no code).** Use one of the 15 real admitted
    cids as the donor. Costs a real card, which the user previously ruled out.
  * **Option B — repoint the dead 0x16F5 arm to 0x1859 (ov3 dead code, ~20 B).**
    ⚠️ The obvious 2-byte edit does NOT work: 0x1859 − 0x163F = 0x21A, which does
    not fit an `adds rX,#imm8`. (r2 happens to hold 0x1793 there and 0x1859 − 0x1793
    = 0xC6 *does* fit, but rebuilding the constant needs 2 instructions and the
    6 bytes at 0x021D147A are already 3.) So the arm must be replaced by a branch
    into an **ov3 dead-code stub** that compares r5 against a pooled 0x1859 and
    jumps to 0x021D199E on match. LR is free (0x021D1300 pushed it). This is the
    Escuridao technique; **132 B of ov3 dead code are currently free** and ov3 is
    the correct host because this path also runs in puzzles, where ov41 evicts ov5.

**Option B is recommended**: it consumes no card, touches no real cid's behaviour
(0x16F5 is inert), and is count-neutral by construction.

⚠️ Whichever is chosen, the leave-mask row and the criteria row we already ship stay
— they are correct and still needed for the field path and the candidate pool.

## SESSION 12 — OPTION B BUILT: the dead 0x16F5 arm now admits the donor

### The edit (PART E of `patch_eclipse_wyvern.py`)

```
0x021D1472  ADD R1,R0,#0 ; ADD R1,#0xB6 ; CMP R5,R1 ; BGT 0x021D1482   <- UNTOUCHED
            (the binary-search step that routes every cid > 0x16F5; re-keying a
             phantom's SLOT would mis-route the whole interval -- see the warning
             on OV3_DEAD_BLOCKS)
0x021D147A  BL 0x021B5920        <- was ADD R0,#0xB6 (r0 = 0x163F + 0xB6 = 0x16F5)
0x021D147E  MOV R8,R8  (NOP)     <- was CMP R5,R0 / BEQ 0x021D1526
0x021D1480  B 0x021D19C0         <- UNTOUCHED (the reject fall-through)
```

Stub, 20 B at **0x021B5920** in ov3 dead block 0x021B591E (28 B, phantom 0x19BE --
released in session 5, re-claimed here), based 2 B in so the literal pool is
4-aligned:

```
0x021B5920  ldr r0,[pc,#8]   ; = 0x00001859
0x021B5922  cmp r5,r0
0x021B5924  beq 0x021B5928
0x021B5926  bx  lr           ; not ours -> NOP -> B 0x021D19C0 (reject)
0x021B5928  ldr r0,[pc,#4]   ; = 0x021D1527  (0x021D1526 | Thumb bit)
0x021B592A  bx  r0           ; -> 0x021D1938 -> 0x021D199E  MOV R0,#1  = ACCEPT
0x021B592C  .word 0x00001859
0x021B5930  .word 0x021D1527
```

**Disassembled from the built ROM**, not trusted from the encoder
(`thumb-pop-into-lr-footgun`): every instruction matches, both literals resolve,
and the range step + reject fall-through are byte-identical to stock.

### Why these choices

  * **ov3, not ov5.** 0x021D1300 is shared engine code that also runs in puzzles,
    where overlay 41 evicts ov5 and a BL into it would freeze the console. This is
    the ov3 DEAD-CODE pool (the Escuridao technique), not the still-canary-gated
    ov3 BSS cave in `ov3_cave.py`.
  * **A stub, not a 2-byte immediate edit.** 0x1859 - 0x163F = 0x21A, far past an
    `ADD Rd,#imm8`. (r2 happens to hold 0x1793 there and 0x1859 - 0x1793 = 0xC6
    *would* fit, but rebuilding the constant needs two instructions and the site
    has room for three in six bytes -- no space for the CMP and BEQ as well.)
  * **Clobbering r0 and LR is safe**, checked on both exits: the ACCEPT path
    reaches 0x021D199E `MOV R0,#1` and the REJECT path reaches 0x021D19C0
    `LDR R0,[SP,#0x2C]`, so r0 is dead across the stub either way; LR is dead
    because 0x021D1300 pushed it at entry and returns via `POP {...,PC}`.
  * **Nothing branches into the replaced bytes.** Scanned every B/Bcond in ov3:
    zero target 0x021D147A/C/E, so they are reachable only by fall-through from
    the BGT at 0x021D1478.

### Ledger

`(0x021B591E, 22, "eclipse_wyvern")` added to `OV3_CLAIMS`; ledger regenerated,
no overlaps, **110 B of ov3 dead code still free** (was 132).

### Standalone verify

`patch_eclipse_wyvern.verify()` extended to cover PART E: the arm must be the BL +
NOP, the stub bytes must match `_gate_stub()` exactly and pass
`assert_thumb1_only`, the 0x16F5 range step must be stock, and the reject
fall-through must still be there. PASSES on `rom_eclipse_wyvern.nds`.

### What the in-game test must now show

Discard an Eclipse Wyvern from the hand: the banish prompt should appear and a
Level 7+ Dragon should leave the Deck. Also mill one (deck -> GY) and check the
field -> GY path still works (it was already confirmed and must not regress).

⚠️ The known empty-deck freeze is STILL PRESENT and is now easier to hit, because
the trigger fires from more places: if the Deck holds no Level 7+ Dragon, Gold
Sarcophagus's resolver returns from phase 0x80 without calling the completion
routine 0x021D269C and the game hangs. **Test with Level 7+ Dragons in the deck.**
Fixing it needs the small cid-keyed wrapper resolver described in PART C's note.

## SESSION 13 — PART E was hooked at the WRONG NODE; corrected and proved by simulation

### In-game result of the first PART E build

    Field -> GY  works
    Hand  -> GY  does NOT work
    Deck  -> GY  does NOT work

i.e. **no change at all** — and the user confirmed they ran `rom_eclipse_wyvern.nds`,
which did contain the stub. So the patch was inert.

### Why: a sorted binary search never routes our cid to a phantom's arm

The first build repointed the DEAD 0x16F5 arm at 0x021D147A. Its bytes were
correct and it disassembled perfectly out of the built ROM — but **cid 0x1859
never visits that node.** The chain at 0x021D1392 is a SORTED BINARY SEARCH, and
0x1859 > 0x16F5, so the search branches away several nodes earlier.

⚠️ This is the exact warning already written on `OV3_DEAD_BLOCKS` in
`check_allocations.py`:

> Only the leaf BODY is free. A phantom arm's SLOT cannot be re-keyed: each sits
> at a fixed point of a sorted binary chain, so giving it an out-of-interval cid
> mis-routes every card in that interval.

**LESSON (the generalisable one): disassembling a stub proves the BYTES are right.
Only simulating the SEARCH proves the card ever ARRIVES there.** The session-11
simulator had already printed 0x1859's path — ending at 0x021D14D6, nowhere near
0x021D147A — and it was not read carefully enough before building.

### The correct hook: the TERMINAL NODE of the donor's own interval

Simulated path for 0x1859 ends here, and 0x021D14D2 is reached from exactly one
place (`BGT` @0x021D14AA):

```
0x021D14D2  ADD R2,#0x95     ; r2 = 0x1793 + 0x95 = 0x1828   <- DISPLACED
0x021D14D4  CMP R5,R2                                         <- DISPLACED
0x021D14D6  BEQ 0x021D14E8   ; cid == 0x1828 -> its own arm   <- KEPT IN PLACE
0x021D14D8  B   0x021D19C0   ; everyone else -> REJECT        <- KEPT IN PLACE
```

Checked before touching it: **nothing in ov3 branches to 0x021D14D4/D6/D8**
(0x021D14DA IS a target, from 0x021D1498, and is untouched).

### The stub — 24 B at 0x021B5920, and it hands the flags back

```
0x021B5920  ADD R2,#0x95     ; replicate the displaced op: the reject path
                             ;   downstream expects r2 == 0x1828
0x021B5922  LDR R0,[PC,#0xC] ; = 0x00001859
0x021B5924  CMP R5,R0
0x021B5926  BEQ 0x021B592C   ; our cid -> unconditional accept
0x021B5928  CMP R5,R2        ; the displaced 0x1828 test -- sets Z for the CALLER
0x021B592A  BX  LR           ; -> 0x021D14D6 BEQ, flags intact (BX never writes them)
0x021B592C  LDR R0,[PC,#4]   ; = 0x021D1527  (0x021D1526 | Thumb bit)
0x021B592E  BX  R0           ; -> 0x021D1938 -> 0x021D199E  MOV R0,#1 = ACCEPT
0x021B5930  .word 0x00001859
0x021B5934  .word 0x021D1527
```

Reusing the caller's own `BEQ` is what makes it fit: the stub returns with Z set
from the 0x1828 compare, so the native branch still works and no far jump is
needed for that case. Register safety, checked on all THREE exits — reject reaches
0x021D19C0 `LDR R0,[SP,#0x2C]`, accept reaches 0x021D199E `MOV R0,#1`, and the
0x1828 arm reaches 0x021D14E8 -> 0x021D18C4 `LDR R0,[SP,#0x34]` — so r0 is dead on
every one. LR is dead (0x021D1300 pushed it and returns via `POP {...,PC}`).

### ⭐ THE VERIFICATION THAT WAS MISSING — `scratch/verify_gy_switch_patch.py`

Walks the GY-event chain for **every cid 0..0x26FF on stock and on the patched
overlay** and diffs the leaf. The simulator now follows `BL` / `BX LR` / `BX Rn`
so it traverses the ov3 stub, and still refuses on any unmodelled instruction
rather than guessing.

```
stock   0x1859 -> reject
patched 0x1859 -> ACCEPT

cids whose verdict CHANGED: 1
  0x1859: reject -> ACCEPT

Dandylion 0x19FE still ACCEPT: True
0x1828 (the displaced test) unchanged: True (arm 0x021D18C4)

PASS: exactly the donor flipped reject -> ACCEPT
```

This is now the standard of proof for any edit to a cid comparison chain, and it
should have been run on the first build.

### Ledger

The 0x16F5 arm is restored to STOCK and `verify()` asserts it. The ov3 claim on
block 0x021B591E is now 26 B (24 B stub, based 2 B in for a 4-aligned pool);
**106 B of ov3 dead code still free**. Standalone `verify()` PASSES.

### Still to test in-game

Discard an Eclipse Wyvern, and mill one, and re-check field -> GY has not
regressed. ⚠️ Keep Level 7+ Dragons in the deck — the empty-deck freeze
(resolver returns from phase 0x80 without calling 0x021D269C) is still unfixed and
is now reachable from more places.

### ✅ IN-GAME CONFIRMED (user, 2026-08-13): CLAUSE 1 WORKS FROM ALL SOURCES

    Field -> GY   works   (was already working)
    Hand  -> GY   WORKS   (discard)
    Deck  -> GY   WORKS   (mill)

Clause 1 of Eclipse Wyvern is **DONE**. The corrected PART E hook at the terminal
node 0x021D14D2 is the piece that made the any-location trigger real; parts A-D
were all necessary but none of them could ever have been sufficient, because
"this card is sent to the Graveyard" is gated by a hardcoded cid comparison chain
(event.sent_to_gy_cid_switch).

The full working recipe, for the next card that needs this trigger:

  1. leave-mask row {cid, 0x0800} in 0x0226EC1C   -- the FIELD-leave path
  2. cls2 record {+04 resolver, +08/+0C/+10/+14 = 0}  -- Dandylion's shape
  3. a criteria row, if the resolver needs a candidate pool
  4. **admission to the GY-event cid switch at 0x021D1392** -- hook the TERMINAL
     NODE of the new cid's own interval, never a phantom's arm, and prove it with
     scratch/verify_gy_switch_patch.py
  5. card_prop card_type promoted to Effect Monster if the donor is a vanilla

### Still open on this card

  * **Clause 2** ("If this card is banished from your Graveyard: you can add the
    monster banished by this card's effect to your hand") -- designed, not built.
    The 3DS shows it as the SECOND of two consecutive cls records under one cid,
    the one carrying +0C/+10/+14 (Cyber Ouroboros 0x1CF6's shape), and the
    remembered card lives on the effect descriptor as recorded pick #1
    (desc[+0x14 + i*2], accessors 0x022348C0 / 0x02234904 / 0x02234964).
  * ⚠️ **The empty-deck freeze is STILL UNFIXED and is now easier to hit**, because
    the trigger fires from three sources instead of one. With no Level 7+ Dragon in
    the Deck, Gold Sarcophagus's resolver returns from phase 0x80 without calling
    the completion routine 0x021D269C and the game hangs. Fix = a small cid-keyed
    wrapper resolver: on phase 0x80, if 0x02243FA8(side, cid, 0) == 0 then call
    0x021D269C(side) and return 0, else tail-call 0x0221CD29. ov5 is a legal host
    (reached only through this card's own cls2 record). **This should be built
    before the card ships in a deck that is not Dragon-heavy.**
  * The filter remains Dragon + Level >= 7 (not "LIGHT or DARK") -- deliberate and
    strictly wider than the real card; see the module docstring.

## SESSION 14 — empty-deck freeze FIXED (pure data); clause-2 blocker SOLVED

### PART F -- the freeze fix turned out to need no code at all

Planned as an ov5 wrapper resolver; the native cards had a better answer. Gold
Sarcophagus's own cls0 record pairs the resolver we borrowed (0x0221CD29) with
**+0C = 0x021F0BDD**, a per-cid condition DISPATCHER over a table at **0x0226FAFC**
(146 rows x 12, `{u16 cid, u16 pad, u32 pred, u32 act}`, sorted). Its row for
0x1811 is `{pred 0x021F0619, act 0x021F6565}`:

  * `0x021F0619` -- side = desc[+2] ^ desc[+6], then
    `0x02243FE0(side, cid, 0x02234E78(desc))` != 0  => "a legal target exists"
  * `0x021F6565` -- `0x021BABE8(side)` != 0         => the SAME gate the resolver
    tests first at phase 0x80

i.e. the condition tests exactly the two things that made the resolver bail. With
**no row the dispatcher returns 0** (0x021F0C0C) -- which is why our record, having
+0C = 0, fell straight through into the hang.

FIX: a count-neutral row `{0x1859, 0, 0x021F0619, 0x021F6565}` over phantom 0x1748
(row 22; 7 phantoms exist in that table), plus cls2 `+0C = 0x021F0BDD`. Now a
target-less trigger returns 0 from the condition, 0x0224AD94 hands back 0, the
event is never admitted, and the effect simply does not trigger -- also the correct
ruling. Standalone verify PASSES; chain applied 31/31 cleanly with PART E.

⚠️ The docstring's old warning "a non-zero +0C froze earlier builds" came from
patch_gravekeepers_recruiter pairing a MISMATCHED condition with its resolver. The
warning is now corrected in place: the native pair is the whole point.

### ⭐ CLAUSE 2 BLOCKER SOLVED -- how two records under ONE cid coexist

The open question since session 1 ("two cls2 records would shadow each other, the
Warwolf E1/E2 regression") has a data answer. Reading `find_event_handler`
0x0224A118 rather than trusting the summary:

  * selector (desc[+5]) picks the table via a 4-way jump table @0x0224A132:
    sel 0 -> cls2 0x02275C04 (0x2B9) unless event == 0x25, which uses cls0
    0x0227E64C (0x51A) with the search LOW BOUND r6 = 3;
    sel 1 -> cls1 0x022860D4 (0x535); sel 3 -> cls3 0x02279D74 (0x308).
  * the search is a **lower_bound** (0x0224A17E..0x0224A19A), so it lands on the
    LEFTMOST record with that cid -- confirming the shadowing hazard.
  * **BUT** 0x0224A1AA onward then consults a family of (CID LIST, EVENT CODE)
    pairs to redirect to a different record:
        list 0x02275B60, 0x13 = 19 entries, event code 2 -> 0x0224A7FC
        list 0x02275B86, 0x19 = 25 entries, event code 6 -> ...
    (the region 0x02275B60..0x02275C04 = 0xA4 B sits immediately below the cls2
    table and holds several such lists)

**So a card MAY own more than one record: membership in the event-keyed list for a
given event routes that event to the other record.** This is the mechanism the 3DS
uses for Eclipse Wyvern's two consecutive records, and it is DATA, not code.

NEXT (recon, before any ROM edit): enumerate every (list, count, event code,
target) tuple in 0x0224A1AA.., dump each list, and identify which pair corresponds
to the "banished from the GY" event that Cyber Ouroboros 0x1CF6 responds to.

## SESSION 15 — CLAUSE 2 RECON (no ROM edits): the banish gate is the mirror of PART E

USER DECISION (2026-08-13): clause 2 must present a **Yes/No prompt** -- the text
says "You can add", so it is an OPTIONAL trigger, not mandatory.

### The banish trigger is gated the same way the sent-to-GY trigger was

`0x021D1300`'s dest-zone test at 0x021D138A sends NON-GY relocations to the switch
at **0x021D1B98** (session 8's "20-cid switch" -- now correctly understood as the
non-GY branch, reached via the compiler's `BL`-as-long-jump at 0x021D138E).

**Leaf 0x021D1D3E is the BANISH gate**, and only two cids reach it:

```
0x021D1D3E  LDR R0,[SP,#0x30] ; CMP R0,#0xF   -> destination == BANISHED
0x021D1D44  LDR R0,[SP,#0xC]  ; AND #0xC0 ; CMP #0xC0 ; BEQ reject
0x021D1D4E  MOV R0,#1                          -> eligible
```

    0x17BB  (a REAL card)
    0x1CF6  Cyber Ouroboros -- "when this card is removed from play, ..."

So clause 2 needs the SAME kind of admission PART E needed, on the other switch.

### The hook point (terminal node for our cid's interval) -- already located

Simulated 0x1859's path through 0x021D1B98; it ends at the node that routes 0x17BB:

```
0x021D1C3E  BGT 0x021D1C44                  <- the only inbound branch
0x021D1C44  LDR R0,=0x17BB                  <- DISPLACE
0x021D1C46  CMP R5,R0                       <- DISPLACE
0x021D1C48  BEQ 0x021D1D3E  (banish leaf)   <- KEEP
0x021D1C4A  B   0x021D1D56  (no store -> 0) <- KEEP
```

Verified: nothing branches to 0x021D1C46/48/4A. ⚠️ 0x17BB IS a real card, so its
test must be preserved -- exactly the PART E situation, and the same trick applies:
the stub hands the flags back to the caller's own BEQ.

Proposed stub, **20 B** (fits ov3 dead block 0x021B57EE, 22 B free):

```
ldr r0,=0x1859 ; cmp r5,r0 ; beq done
ldr r0,=0x17BB ; cmp r5,r0            ; preserve the native test
done: bx lr                            ; caller's BEQ sees Z for either cid
.word 0x1859 ; .word 0x17BB
```

⚠️ MUST be proved with a stock-vs-patched sweep over every cid before building
(scratch/verify_gy_switch_patch.py generalises), per the session-13 lesson.

### Two records under one cid -- SOLVED, and it is data

`find_event_handler` 0x0224A118 is a lower_bound binary search (so the leftmost
record wins -- the Warwolf E1/E2 hazard is real), BUT from 0x0224A1AA it consults a
family of **(cid list, event code)** pairs that redirect to a different record:

    list 0x02275B60, 0x13 = 19 entries + event code 2 -> 0x0224A7FC
    list 0x02275B86, 0x19 = 25 entries + event code 6 -> ...
    (the region 0x02275B60..0x02275C04, 0xA4 B, holds several such lists)

This is how the 3DS gives Eclipse Wyvern two consecutive records. **Membership in
the list keyed to an event routes that event to the other record.**

### Open questions before any build

  1. Which (list, event) pair corresponds to the banish event, and what event code
     the banish relocation actually posts (the sent-to-GY one is 0x1F).
  2. ONE record or TWO? A single record whose resolver switches on desc[+4] is the
     D.D. Capsule pattern (0x02216560: `LDRB R0,[R5,#4] ; CMP R0,#2`) and would
     avoid the list mechanism entirely -- but needs our own dispatching resolver
     instead of Gold Sarcophagus's native one.
  3. **Source-zone check.** Leaf 0x021D1D3E tests only the DESTINATION (0x0F), so it
     fires for a banish from ANY zone. Clause 2 needs "banished FROM THE GRAVEYARD"
     only, and the descriptor built at 0x021D1D5C carries the DEST zone in desc[+3]
     -- so the source test has to come from somewhere else.
  4. Whether the NDS descriptor really carries the remembered card as recorded
     pick #1 (desc[+0x14 + i*2]; accessors 0x022348C0 / 0x02234904 / 0x02234964),
     which is what the 3DS arm reads. This decides exact identity vs the
     source-zone approximation.
  5. How an OPTIONAL trigger raises its Yes/No prompt (Cyber Ouroboros 0x1CF6 =
     cls2[307] {+04 0x022065B9, +0C 0, +10 0x021E5201} is the template to read).

**NOTHING BUILT.** No ROM bytes written, no ledger claim, no cave slot taken.

## SESSION 16 — 3DS CLAUSE 2 DISASSEMBLED: it uses the descriptor PICK ARRAY

USER STEER: match the 3DS byte-for-byte where possible; and note that Gold
Sarcophagus / D.D. Capsule / Watthydra ALREADY remember a banished card and add it
back later, so the engine can do this natively.

⚠️ 3DS addresses below are STRUCTURE ONLY and must never enter the NDS namespace.

### Where clause 2 lives on the 3DS

Record B's resolver 0x0043D564 is a SHARED phase machine on `[global+0xBB4]`
(phases 0x64/0x78/0x7C/0x7D/0x7E/0x7F/0x80) -- the same protocol as the NDS
`[0x0229AAFC+0x70]` (0x7E/0x7F/0x80). Phase 0x7C runs a per-cid switch:

```
0x0043D6B4  LDRH R0,[R4]        ; cid
0x0043D6B8  LDR  R1,=0x25E7     ; switch base
0x0043D6C0  SUB  R1,R0,R1
0x0043D6F0  CMP  R1,#0xFE       ; 0x25E7 + 0xFE = 0x26E5 = ECLIPSE WYVERN
0x0043D6F8  B    0x0043D86C     ; -> its arm
```

### ⭐ THE ARM -- and it settles the "exact identity" question

```
0x0043D86C  LDRH R0,[R4,#0x16]      ; the REMEMBERED CARD, on the DESCRIPTOR
0x0043D870  BL   0x003CD1A4         ; pick accessor -> (side | key<<8)
0x0043D874  LDRH R1,[R4,#4]
0x0043D87C  CMP  R1, R0, LSR #8     ; desc[+4] == key  ?
0x0043D880  BNE  0x0043D8D0         ; no -> just return phase 0x64
0x0043D884  BL   0x00381344 ; LDR R0,[R0] ; LSL #1 ; LSR #0x18 ; LSL R5,R0,#1
0x0043D898  BL   0x00381344 ; LDR R0,[R0] ; LSL #0x11
0x0043D8AC  ADD  R5,R5,R0,LSR #31   ; r5 = (inst_idx<<1) | side  -- a PACKED REF
0x0043D8B0  LDRH R0,[R4,#0x16] ; MOV R3,R5 ; BL 0x0038C80C   (r1=0x252B, r2=5)
0x0043D8BC  LDRH R3,[R4,#0x16] ; MOV R0,R5 ; BL 0x0038C80C   (r1=0x2518, r2=3)
0x0043D8D0  MOV  R0,#0x64           ; return
```

**`desc[+0x16]` is read THREE times and is the remembered card.** On the NDS
descriptor that offset is exactly `desc[+0x14 + i*2]` with **i = 1**, i.e.
**recorded pick #1** of the pick array that the KB already records as VERIFIED
(`dispatch.pick_halfword_layout`), with accessors
`0x022348C0` (raw halfword), `0x02234904` (side | key<<8), `0x02234964` (packed ref).

And the correspondence is tight: the 3DS calls its accessor then compares
`R0 LSR #8` against `desc[+4]` -- i.e. it uses the **(side | key<<8)** form, so
3DS `0x003CD1A4` is the analogue of NDS **`0x02234904`**. The packed ref it builds,
`(inst_idx<<1) | side`, is the same convention the KB already documents.

### CONCLUSION: exact identity IS achievable, and no new storage is needed

The remembered card is **not** in a global node array -- it rides on the effect
descriptor as a recorded pick. The NDS has that machinery already, and the user's
observation is the independent confirmation: D.D. Capsule 0x159C's resolver
0x02216560 serves BOTH activation and delayed retrieval, split by
`LDRB R0,[R5,#4] ; CMP R0,#2` on the descriptor's event code -- so an NDS
descriptor demonstrably persists from the banish to the later retrieval, carrying
its picks. Gold Sarcophagus 0x1811 and Watthydra 0x2477 share that same
deck-banish resolver family.

**So the source-zone approximation proposed in session 1 is NOT needed and should
be dropped from the design.**

### What this implies for the NDS build (design, NOT yet built)

  * clause 1's resolver must RECORD the banished card as pick #1 on the descriptor.
    Gold Sarcophagus's resolver already reads the player's pick at phase 0x7E
    (via 0x0219C510) before calling 0x021D21DC -- the open question is whether it
    also STORES it as a recorded pick, or whether we need a small wrapper that does.
  * clause 2 reads it back with 0x02234904 / 0x02234964 and adds it to the hand.
  * the Yes/No prompt (user-confirmed requirement) still needs its mechanism found;
    Cyber Ouroboros 0x1CF6 cls2[307] {+04 0x022065B9, +0C 0, +10 0x021E5201} is the
    NDS template for an optional "removed from play" trigger.

### Next recon step

Disassemble D.D. Capsule's resolver 0x02216560 (the `desc[+4] == 2` split) and
Gold Sarcophagus's 0x0221CD29 phase-0x7E arm side by side, to find (a) where the
pick is recorded on the descriptor and (b) how the delayed retrieval event is
scheduled. That is the NDS mechanism to copy, and it is the same one the 3DS arm
above is reading.

**NOTHING BUILT.**

## SESSION 17 — PART G BUILT: the donor is admitted to the BANISH event gate

Clause 2's prerequisite, and the exact mirror of PART E on the other branch of
0x021D1300.

```
0x021D1C3E  BGT 0x021D1C44                  <- the only inbound branch
0x021D1C44  BL  0x021B57F0                  <- was LDR R0,=0x17BB ; CMP R5,R0
0x021D1C48  BEQ 0x021D1D3E  (banish leaf)   <- KEPT, reused by the stub
0x021D1C4A  B   0x021D1D56  (no store -> 0) <- KEPT
```

Stub, 20 B at 0x021B57F0 in ov3 dead block 0x021B57EE (22 B, phantom 0x1789):

```
ldr r0,=0x1859 ; cmp r5,r0 ; beq +10
ldr r0,=0x17BB ; cmp r5,r0        ; the displaced native test (0x17BB is REAL)
bx  lr                             ; caller's BEQ sees Z for either cid
```

r0 is dead on both exits (banish leaf opens `LDR R0,[SP,#0x30]`, reject opens
`LDR R0,[SP,#0x14]`); LR is dead throughout 0x021D1300.

### Verified by simulation, both gates, stock vs patched, every cid

`scratch/verify_gy_switch_patch.py` generalised to check BOTH chains:

```
=== sent-to-GY gate (chain 0x021d1392) ===   cids CHANGED: 1   0x1859 reject -> ACCEPT   PASS
=== banished  gate (chain 0x021d1b98) ===   cids CHANGED: 1   0x1859 reject -> ACCEPT   PASS
ALL GATES PASS
```

Ledger: `(0x021B57EE, 22, "eclipse_wyvern")`; standalone verify PASSES with the new
PART G assertions.

### ⚠️ PART G ALONE PRODUCES NO VISIBLE EFFECT

It only makes the engine POST an event when the donor is banished. Nothing consumes
that event yet, so in-game behaviour is unchanged. It is a prerequisite brick, and
it is the piece that could not be tested any other way.

### What clause 2 still needs

  1. **Recording the pick.** Gold Sarcophagus's phase-0x7E arm (0x0221CD74..) builds
     the packed ref with shifts IDENTICAL to the 3DS arm --
     `LSL #1 ; LSR #0x18 ; LSL #1` and `LSL #0x11 ; LSR #0x1F` -> `(inst_idx<<1)|side`
     -- then banishes with 0x021D21DC and completes with 0x021D269C. **It does NOT
     store the pick on the descriptor.** So clause 1 needs a wrapper that also writes
     it to desc[+0x16] (recorded pick #1), which is what the 3DS clause-2 arm reads.
  2. **A record for the banish event** -- either a second cls2 record disambiguated
     by the (cid list, event code) pairs at 0x02275B60.., or ONE record whose
     resolver switches on desc[+4] (the D.D. Capsule pattern at 0x02216560).
  3. **The source-zone test**: leaf 0x021D1D3E checks only the DESTINATION (0x0F),
     so it fires for a banish from any zone; clause 2 needs GY-source only.
  4. **The Yes/No prompt** (user-confirmed): Cyber Ouroboros 0x1CF6 cls2[307] is the
     NDS template.

## SESSION 18 — PARTS G + H BUILT; and a design problem with H, stated plainly

### Built and verified offline

  * **PART G** -- banish-gate admission (mirror of PART E on the non-GY branch).
    Hook 0x021D1C44, 20 B ov3 stub at 0x021B57F0, block 0x021B57EE fully consumed.
  * **PART H** -- the pick recorder. `cls2 +04` now points at a 68 B ov5 stub
    (CAVE_EW_RECORD 0x0239C014) that calls Gold Sarcophagus's resolver 0x0221CD29
    and, on phase 0x7E, recomputes the packed ref `(inst_idx<<1)|side` exactly as the
    native arm does and stores it to **desc[+0x16]** -- recorded pick #1, the offset
    the 3DS clause-2 arm reads.

Pick-array layout CONFIRMED from the accessors themselves (0x022348C0 / 0x02234904 /
0x02234964): `desc + 0x14 + i*2` for i < 5, with i >= 5 overflowing to a ring buffer
via desc[+0x1E] into 0x0229AA58. So desc[+0x16] == pick #1, byte-for-byte the 3DS.

Both gates still change exactly one cid (ALL GATES PASS); stub Thumb-1 clean and
byte-verified out of the built ROM; ledger regenerated (86 ov5 slots, no collisions).

⚠️ **Disassembling the built stub caught FOUR encoder bugs** that `assert_thumb1_only`
happily passed: `LDR R5,[R5,#0x54]` instead of `#0x70`, two mis-indexed literal-pool
slots, and an inverted `BEQ` where `BNE` was meant. The rule "always disassemble
built stubs" earned its keep again.

### ⚠️ THE PROBLEM WITH PART H AS BUILT

desc[+0x16] rides on **one** effect descriptor. But on the NDS the banish event
builds a **NEW** descriptor: 0x021D1D5C packs a fresh word and the register-prim
0x021D3168 constructs a new 0x24-byte descriptor from it. So a banish-triggered
record would see an EMPTY desc[+0x16], and clause 1's recorded pick would never
reach clause 2.

This is where the NDS and the 3DS genuinely diverge, and it is worth stating rather
than papering over: on the 3DS clause 2 is an ARM OF THE SAME PHASE MACHINE
(record B, phase 0x7C), i.e. plausibly the same descriptor instance -- which is why
reading desc[+0x16] works there. The instruction "match the 3DS byte for byte"
cannot be fully honoured for the STORAGE, only for the offset and the ref encoding.

D.D. Capsule 0x159C proves NDS descriptors CAN persist across a delayed retrieval
(0x02216560 splits activation from retrieval on `LDRB R0,[R5,#4] ; CMP R0,#2`), so
the mechanism exists -- but that is a *delayed* effect scheduled by the same
descriptor, not a fresh trigger, and clause 2 is a fresh trigger.

**PART H is harmless as built** (one extra store on a path that already runs), but
it is not sufficient on its own.

### THE CLAUSE-2 ARCHITECTURE (decided, not yet built)

  1. **ONE cls2 record, not two.** The banish event dispatches to the same cid and
     the same selector, so it lands on the record we already own. The resolver
     switches on **desc[+3] = the DESTINATION ZONE** -- 0x0E = sent-to-GY (clause 1),
     0x0F = banished (clause 2). That is a discriminator already verified (the packer
     at 0x021D1D5C puts the dest zone in bits 16..20), needs no event-code hunt, and
     avoids the (cid list, event code) redirect mechanism entirely.
     This is the D.D. Capsule pattern adapted to the zone field.
  2. **Storage: a small ov5 scratch, keyed by side** (2 x u16), written by the PART H
     recorder alongside desc[+0x16] and read by the clause-2 arm. Per-instance state
     is not achievable here (a known project limitation --
     otn-normal-donor-trampoline-method), so two Eclipse Wyverns resolving in the
     same window would share a slot. Acceptable; the alternative is a new RE effort
     into the native delayed-effect scheduler.
  3. **The Yes/No prompt is ASYNCHRONOUS** and needs the phase protocol
     (0x80 act -> 0x7F -> 0x7E), exactly as Gold Sarcophagus's own resolver does.
     This is the substantial remaining piece: ~100 B, and it must not be written
     casually -- see the four encoder bugs above.

### Next

Extend the PART H recorder with the side-keyed ov5 scratch write (~10 B, needs the
reserve bumped from 0x50), then build the clause-2 arm as a phase machine that
prompts and calls the add-to-hand primitive on the remembered ref.

## SESSION 19 — the NATIVE RETRIEVAL TEMPLATE found (clause 2's action)

Per user direction, builds now target `rom_eclipse_wyvern.nds` only;
`apply_all_patches` is deferred until "ship it".

### PART H final shape (built, verified, in the standalone ROM)

```
strh r0,[r4,#0x16]      ; recorded pick #1 -- faithful to the 3DS offset
ldrb r1,[r4,#2]         ; side
lsls r1,r1,#1
ldr  r2,=CAVE_EW_SCRATCH (0x0239C064)
strh r0,[r2,r1]         ; side-keyed slot clause 2 will read
```

80 B at CAVE_EW_RECORD 0x0239C014 (0x60 reserved). Both writes happen: the
descriptor one matches the 3DS, the scratch one is what actually survives, because
the NDS builds a NEW descriptor for the banish event.

⚠️ SIX encoder bugs were caught by disassembling the built stubs today
(`LDR R5,[R5,#0x54]` for `#0x70`; two mis-indexed literal slots; an inverted
`BEQ`/`BNE`; `LDRB R1,[R4,#1]` for `#2]`; one stale branch distance).
`assert_thumb1_only` passed all of them -- it only rejects Thumb-2, it does not
check that the code means what you intended. **Disassemble every built stub.**

### ⭐ THE NATIVE RETRIEVAL TEMPLATE -- 0x0221CECC

Found next door to Gold Sarcophagus's resolver: the code that reads a RECORDED PICK
back off the descriptor and acts on it. This is exactly clause 2's action, and it
is the NDS analogue of the 3DS arm at 0x0043D86C.

```
0x0221CECC  push {r1-r7,lr} ; r5 = desc ; r4 = 0 (pick index)
0x0221CED6  bl 0x022349B0(desc, 0, 0)     ; is there a pick? 0 -> bail
0x0221CEE2  bl 0x02234904(desc, index)    ; -> (side | key<<8)
0x0221CEE6  r7 = r0 & 0xFF                ; side
0x0221CEEC  r6 = (r0 >> 8) & 0xFF         ; key / instance index
0x0221CEFA  bl 0x0224A924(desc, side, key); validity check, 0 -> bail
0x0221CF02  [sp] = 2 ; [sp+4] = 1 ; r3 = desc[+0] (cid)
0x0221CF12  bl 0x021C47CC(desc, side, key, cid, 2, 1)   ; ** NOT the action **
```

So the accessor pair to use is **0x022349B0** ("does pick i exist") and
**0x02234904** ("pick i as side | key<<8").

⚠️ **CORRECTION (same session): 0x021C47CC is NOT the mover.** Disassembled: it
builds message **0x35** (`MOV R0,#0x35 ; ORR R0,R1 ; ...`), i.e. it is the same
replay-log family as 0x021C479C, which session 1 already ruled out as "merely logs".
Labelling it THE ACTION was wrong. The accessor half of the template is still good --
the pick IS read back off the descriptor with 0x022349B0 / 0x02234904 -- but the code
that actually MOVES the card has not been identified yet, and 0x0221CECC needs to be
read past 0x0221CF16 to find it (or it may live further downstream).
Note this reads the pick from the DESCRIPTOR -- which is why our scratch exists:
our clause 2 runs on a different descriptor than clause 1 did.

### Clause 2 -- fully designed, NOT built

  * dispatch: the PART H wrapper switches on **desc[+3]** (dest zone): 0x0E ->
    clause 1 (native resolver + record), 0x0F -> clause 2.
  * action: read CAVE_EW_SCRATCH[side]; if 0, return 0. Otherwise decode it the way
    0x0221CEE6.. does and call the mover.
  * ⛔ **STILL UNKNOWN: the Yes/No prompt.** Cyber Ouroboros 0x1CF6's resolver
    0x022065B9 has NO phase machine and NO prompt -- it just computes and draws. And
    the `+10` classifier does not correlate with "you can" across the 0x0800 family
    (Peten 0x17C5 optional has 0x021E5201, but so do several mandatory cards, and
    Dandylion has 0). So the mechanism that OFFERS an optional trigger is not yet
    identified, and the user requires the prompt.
  * The remaining signatures to pin down before writing the arm: 0x0224A924 and
    0x021C47CC (arg order and the meaning of the two stack args 2 and 1).

**NOTHING NEW BUILT this session beyond PART H's scratch write.**

## SESSION 20 — REVERTED TO KNOWN-GOOD, then the 3DS RESOLVER READ PROPERLY

### Revert (confirmed working in-game)

PARTS F, G and H are all DISABLED. `rom_eclipse_wyvern.nds` is back to A/B/C/D/E:
cls2 `{+04 = 0x0221CD29 native, +0C = 0}`, mask row 0x0800, criteria row, PART E
gate. Field / discard / mill all trigger again.

Every failure between the first working build and this revert was self-inflicted:
  * PART F (native condition on +0C) -- refused the event off-field;
  * PART G (banish gate) -- a GY-bound card FALLS THROUGH into the same chain, so
    the banish leaf's `dest == 0x0F` test failed and STORED 0 over PART E's accept;
  * PART H (ov5 wrapper) -- clobbered the resolver's r1 argument, then, once fixed,
    counted candidates with the wrong function.
⚠️ The gate simulator gave false confidence: it walks each chain from its own entry,
so it can never see one chain overwrite the other's verdict. Any future edit to
these chains must be verified by walking the WHOLE function, not one chain.

### ⭐ THE 3DS RECORD-B PHASE MACHINE, IN FULL (0x0043D564)

```
0x80 -> return 0x7F                                   (does NO work)
0x7F -> r2 = 0x464D58(desc) ; n = 0x46D510(side, cid, r2)
        n > 0  -> 0x3805A4(side, 0x125)  ; return 0x7E     PROMPT
        n == 0 -> 0x380DB8(side, 0x0D)   ; return 0x78     graceful decline
0x7E -> r3 = 0x464D58(desc) ; 0x3819A4(side, 6, cid, r3) ; return 0x7D   PICKER
0x7D -> pick via 0x381344 x2 -> ref = (inst<<1)|side
        0x388C10(side, ref, cid, 0) ; return 0x7C                        BANISH
0x7C -> per-cid switch -> Eclipse Wyvern arm 0x0043D86C                  CLAUSE 2
0x78 -> 0x4B3028(1 - side) ; return 0x64
0x64 -> 0x388E3C(side) ; return 0                                        COMPLETION
```

### The NDS mapping (each anchored to an already-verified NDS call)

    3DS 0x464D58  ->  NDS 0x02234E78   descriptor -> param
    3DS 0x46D510  ->  NDS 0x02243FE0   CANDIDATE COUNT
    3DS 0x3805A4  ->  NDS 0x0219A818   prompt
    3DS 0x3819A4  ->  NDS 0x0219C430   picker
    3DS 0x381344  ->  NDS 0x0219C510   read pick
    3DS 0x388C10  ->  NDS 0x021D21DC   banish
    3DS 0x388E3C  ->  NDS 0x021D269C   completion

Corroborated independently: the NDS native condition 0x021F0619 computes
`0x02243FE0(side, cid, 0x02234E78(desc))` -- the SAME pair the 3DS uses at phase
0x7F. That call was sitting in my own notes from the PART F work and I used
0x02243FA8(side, cid, 0) instead, which is why the search returned 0 with six
legal Dragons in the deck (savestate-verified).

### ⭐ WHERE THE REMEMBERED CARD ACTUALLY COMES FROM

The 3DS clause-2 arm reads desc[+0x16] three times, and NOTHING in phases 0x7D/0x7C
writes it. The only candidate writer is the PICKER: the 3DS calls
`0x3819A4(side, 6, cid, 0x464D58(desc))` whereas Gold Sarcophagus calls
`0x0219C430(side, 6, cid, 0)` -- a FOURTH ARGUMENT the NDS Spell does not pass.
**Hypothesis (to verify before building): that 4th argument makes the picker record
its result into the descriptor's pick array**, which is why the banish arm and the
clause-2 arm can both read it back.

If true, PART H's whole reason for existing disappears -- no ov5 wrapper, no scratch;
clause 1 records the pick simply by passing the right argument to the picker.

### Clause 2's real shape on the 3DS

Phase 0x7C runs IMMEDIATELY AFTER the banish, and its body calls
`0x38C80C` twice with (pick, 0x252B, 5, ref) and (ref, 0x2518, 3, pick). That looks
like registering an ASSOCIATION between the banished card and this card -- i.e. the
persistent link that a later "banished from the GY" trigger consults. So clause 2 is
NOT resolved here; this phase RECORDS the relationship, and record A (the one with
+0C/+10/+14 set, Cyber Ouroboros's shape) carries the actual trigger.

### Next, in order, BEFORE any ROM edit

  1. Find the NDS analogue of 3DS 0x38C80C (the association registrar).
  2. Disassemble 3DS record A (0x0045E5D0) -- the banish trigger and its condition.
  3. Verify the picker's 4th argument on the NDS (does 0x0219C430's arg3 make it
     write desc[+0x14 + i*2]?).
Only then write anything.

**NOTHING BUILT this session beyond the revert.**

### RECORD A (0x0045E5D0) -- clause 2's actual trigger, on the 3DS

A two-phase machine on the same global, with a per-cid switch at phase 0x80.
Eclipse Wyvern 0x26E5 has its own arm:

```
phase 0x80, arm 0x0045E648:
    ldrh r0,[r4,#0x20]      ; the RECORDED-PICK COUNT on the descriptor
    strh r0,[r4,#0x1C]      ; seed the walk index
    b    0x0045E690         ; -> advance to 0x7F
phase 0x7F, 0x0045E698:
    ldrh r0,[r4,#0x1C] ; if 0 -> done
    0x4726D8(desc, idx-1, 0)      ; is entry idx-1 usable?
    0x465E6C(desc, idx-1) -> r5   ; read it   (NDS 0x02234904 family)
    0x465DA4(desc, idx-1)         ; ...
```

So clause 2 WALKS THE DESCRIPTOR'S RECORDED PICKS: desc[+0x20] is the pick COUNT and
desc[+0x1C] the walk index. That is the same array clause 1's picker fills and the
0x7C arm reads at desc[+0x16]. The NDS analogue is the pick array at
`desc + 0x14 + i*2` with its count/ring index at desc[+0x1E]
(dispatch.pick_halfword_layout, accessors 0x022348C0 / 0x02234904 / 0x02234964).

### The NDS picker CONFIRMS the mechanism

`0x0219C430(r0=side, r1=6, r2=cid, r3=param)` disassembled: it stores r2/r3 to the
stack, initialises the search state at **0x0229944C** (`[0]=side, [2]=r1, [4]=0`),
clears the result buffers at 0x02299458 / 0x02299908, and then calls
**`0x02243FA8(side, cid, param)`** -- i.e. the picker and the counter are the SAME
search, and `param` is passed straight through. `0x02243FA8` runs the criteria
binary search 0x02243B9C and writes the count to **[0x0229944C+6]** -- the very word
session 4 read out of a savestate.

So `param` (3DS `0x464D58(desc)`, NDS `0x02234E78(desc)`) is a real search argument,
not decoration. `0x02234E78` resolves an EFFECTIVE cid off the descriptor (it looks
the cid up via 0x02022E14 and returns either desc[+0xC] or a table-derived value),
which is how one resolver searches on another card's behalf.

## THE SPEC for clause 1 + 2 (port of the 3DS machine; NOT yet built)

Implement ONE resolver as a faithful port, replacing the borrowed Gold Sarcophagus
arms entirely. Phases and calls, with the NDS addresses already mapped:

```
0x80 : return 0x7F                                    (no work -- matches the 3DS)
0x7F : p = 0x02234E78(desc)
       n = 0x02243FA8(side, cid, p)
       n > 0  -> 0x0219A818(side, PROMPT_ID) ; return 0x7E
       n == 0 -> <decline call> ; return 0x78
0x7E : p = 0x02234E78(desc)
       0x0219C430(side, 6, cid, p)  ; picker -- p is what makes it RECORD the pick
       return 0x7D
0x7D : ref = pick via 0x0219C510 x2 -> (inst<<1)|side
       0x021D21DC(side, ref, cid, 0x80)     ; banish face-up
       return 0x7C
0x7C : clause 2's association step (3DS 0x38C80C x2 -- NDS analogue STILL UNKNOWN)
0x78 : <decline tail> ; return 0x64
0x64 : 0x021D269C(side) ; return 0           ; completion
```

`side` is `desc[+2]` (savestate-verified: desc[+6] == 0 on this path, so the XOR the
native condition does is a no-op here -- do NOT "fix" it again).

### Still unresolved before this can be written

  1. the NDS analogue of 3DS 0x38C80C (the association registrar) -- clause 2's
     persistent link;
  2. the NDS decline calls (3DS 0x380DB8(side,0x0D) at 0x7F and 0x4B3028(1-side) at
     0x78) -- these are what make an empty search end cleanly instead of hanging;
  3. the correct PROMPT_ID for a trigger (Gold Sarcophagus uses 0x46 for a Spell
     activation; the 3DS uses 0x125 in its own id space).

⚠️ Implementation note for whoever writes this: it is ~200 B of Thumb-1. Today six
encoder bugs were caught only by disassembling built stubs, and `assert_thumb1_only`
passed every one of them -- it rejects Thumb-2, it does NOT check intent. Write the
stub with a label-resolving assembler, disassemble it, and walk the WHOLE relocation
function (not one chain) when verifying any gate edit.

### The three unknowns -- two RESOLVED, one is an ENGINE-CAPABILITY problem

**(2) The decline calls -- RESOLVED.** The NDS uses the same phase vocabulary as the
3DS: 94 sites return 0x78 and 155 return 0x64. The native decline idiom is

```
0x02206EE8  movs r0,#1 ; subs r0,r0,r5 ; bl 0x0225BF30 ; movs r0,#0x78 ; pop
```

i.e. **`0x0225BF30(1 - side)` then return 0x78** -- the exact analogue of the 3DS's
`0x4B3028(1 - side)` at its own 0x78 arm. A second common shape is
`0x0219A818(side, <id>) ; movs r0,#0x78 ; pop` (e.g. id 0x15 @0x0220803A).

**(3) The prompt id -- RESOLVED ENOUGH.** Enumerated every 0x0219A818 call site by
its r1 immediate. Gold Sarcophagus uses **0x46** (7 sites) for "select and banish
from the Deck", which is the right UI for clause 1 and is what we already inherit.
⚠️ Note id **0x0D** has 39 sites and is the same number the 3DS passes to its
decline call -- consistent with 0x0D being the "nothing happens" message.

**(1) The association registrar -- NO NDS TEMPLATE EXISTS.**
The 3DS phase-0x7C arm calls `0x38C80C` twice, and the two constants identify the
mechanic exactly:

    0x252B = Overmind Archfiend
    0x2518 = Silent Psychic Wizard
             "When this card is removed from play, you can Special Summon 1
              Psychic-Type monster that was BANISHED BY THIS CARD'S EFFECT."

That is clause 2's mechanic in another card, so `0x38C80C(a, family_cid, kind, b)`
registers the "banished by X" link in both directions (kinds 5 and 3; both < 6, so
the reader is the `0x021A1430` walker family per otn-attached-effect-rider, whose
key at +0 IS a cid).

**But NEITHER card exists in the NDS build**: cid 0x2518 has ZERO u16 occurrences in
overlay 3, and 0x252B's single occurrence is an entry in the synchro LIST_A region
(0x02275AB8), nothing to do with riders. Over the Nexus therefore ships **no card
that remembers "the card banished by this card's effect"**, so there is no native
writer to copy and, more importantly, no evidence the reader side exists either.

### DECISION POINT for clause 2

  a. **Exact identity** -- would require inventing a rider kind (writer + reader) for
     a relationship this engine appears never to use. That is a substantial new RE
     effort with no reference implementation on the NDS side, and the 3DS addresses
     cannot be lifted.
  b. **Approximation** -- "the Level 7+ Dragon in my banished zone whose SOURCE ZONE
     is Deck (0x0D)". The card-word bitfield already carries the source zone
     (bits 10..13, verified), and a Deck-sourced banished Lv7+ Dragon is almost
     always the one this card banished. Diverges only if another Deck-banish of a
     matching monster happened first.
  c. **Descriptor picks** -- works only if clause 1 and clause 2 share a descriptor.
     They do not on the NDS: the banish event builds a fresh one (0x021D1D5C ->
     register-prim 0x021D3168). This is what PART H was trying to work around.

(b) is the only option with a bounded cost. It was proposed back in session 1 and
dismissed once the 3DS appeared to offer exact identity -- but the 3DS achieves that
through machinery this build does not have.

### Also captured (for whenever two records under one cid ARE needed)

The event-keyed redirect lists that let find_event_handler pick a non-leftmost
record, dumped from 0x02275B60 (19 entries, event code 2) and 0x02275B86 (25
entries, event code 6).

## SESSION 21 — CLAUSE 1 COMPLETE, per-copy memory verified in-game

### ⭐ THE BUG BEHIND MOST OF TODAY'S FREEZES: `BLX Rm` needs the THUMB BIT

`BLX Rm` takes the instruction set from **bit 0 of Rm**. An injected stub doing
`LDR R3,=<native fn> ; BLX R3` with the RAW (even) address switches the core to
**ARM** and executes garbage -- an instant freeze. Native code reaches these
functions with a Thumb `BL`, so every address in our notes is even.

Every even address the wrapper called was a mode-switch crash: 0x021BABE8,
0x02243FA8, 0x021D269C, 0x0219A818, 0x0219C510. The one call that always worked was
0x0221CD29 -- because a cls-record slot already carries the bit.

⚠️ `effect_verify.assert_thumb1_only` does NOT catch it: it rejects Thumb-2, not
wrong-mode branches. Nor does disassembly -- the stub looks perfect.

This invalidates a long chain of reasoning from earlier today. The act-phase freezes
were blamed in turn on the 0x021BABE8 gate, on 0x02243FA8 vs 0x02243FE0, on the
missing third argument, and on the side derivation. **None of those were the cause** --
the code never survived the first BLX, so nothing downstream ever ran. Recorded as
KB fact `thumb.blx_needs_thumb_bit`.

### How it was finally found

A black-box recorder in the ov5 scratch, read from a savestate: `entries`,
`last phase`, and a `progress` marker written on either side of the capture block.
The frozen state read `entries=3, phase=0x7E, progress=1` -- i.e. the wrapper WAS
invoked once per phase (the model was right), it entered the capture block, and died
on the next two instructions. That pinned it to the BLX with no further guessing.
**Build the recorder before the first speculative fix, not after the fifth.**

### Tooling: `otn_enhanced/asm/thumb_asm.py.py`

A label-resolving Thumb-1 assembler. Branch distances and literal-pool indices are
computed, not hand-counted; it refuses unknown mnemonics rather than emitting
something plausible, and it rejects the 3-operand `adds imm > 7` footgun outright.
Six of today's bugs were in that class. It accepts a 2-mod-4 base (some ov3 dead
blocks only fit if you start 2 bytes in).

### PART H final: per-copy memory, keyed by the ACTING INSTANCE

`desc[+0xC]` is the acting card's RAW INSTANCE INDEX -- which physical copy is
resolving -- and it is populated on BOTH the field-leave (event 0x1D) and the
discard/mill (event 0x1F) paths (verified on live savestates, both cases). Index it
into the instance table **0x0229C33C**, stride 8, `cid = word & 0x3FFF`. The picker's
recorded result (via 0x0219C510) is an index into the SAME table.

Keying the scratch on desc[+2] (side) was WRONG and it was measured wrong: two
Eclipse Wyverns discarded in one action banished two Dragons, but the side-keyed slot
kept only the last. Replaced with an 8-slot table of
`{u16 acting_instance, u16 banished_instance}`; a full table drops the record rather
than corrupting another copy's.

IN-GAME CONFIRMED (double discard):
```
slot 0: acting 26 (cid 0x1859) -> banished 22 (cid 0x17D4)
slot 1: acting 28 (cid 0x1859) -> banished 50 (cid 0x1E20)
2 slot(s) in use
```

### CLAUSE 1 IS DONE

Trigger from field / hand / deck, correct Dragon + Level>=7 filter, graceful decline
with no legal target, and exact per-copy memory of what each copy banished --
clause 2's input, ready and verified.

### Clause 2 -- the one remaining unknown

The hand-mover primitive. 0x021C72CC is a thunk (`bx r3`) and the native add-to-hand
resolver 0x02207EF5 is cid-switched, so neither is directly callable. Everything else
is specified: the phase machine ported from the 3DS (session 20), the decline call
0x0225BF30(1 - side) -> return 0x78, and the per-instance lookup above.
⚠️ When writing it: every BLX target needs `| 1`.

## SESSION 22 — THE HAND MOVER FOUND: clause 2 has no unknowns left

`0x02207EF5` is the SHARED add-to-hand resolver (White Stone of Legend 0x1EAA,
Cross Porter 0x1D97). Its per-cid switch only selects the criteria; the phase chain
below it is generic, and it is the NDS twin of the 3DS machine mapped in session 20:

```
0x02208028  bl 0x02234E78   ; descriptor param      (3DS 0x464D58)
0x02208032  bl 0x02243FA8   ; candidate count WITH that param   (3DS 0x46D510)
0x0220803E  bl 0x0219A818   -> return 0x78          ; decline    (3DS 0x380DB8)
0x022080BC  bl 0x0219A818   -> return 0x7E          ; prompt     (3DS 0x3805A4)
0x022080E2  bl 0x0219C430   -> return 0x7D          ; picker     (3DS 0x3819A4)
0x022080EE  bl 0x0219C510   ; read the pick         (3DS 0x381344)
0x022080F6  bl 0x021C72CC   ; *** MOVE TO HAND ***
0x02208128  bl 0x0225BF30   ; decline/finish        (3DS 0x4B3028)
0x02208132  bl 0x021D269C   ; completion            (3DS 0x388E3C)
```

### ⭐ THE MOVER: `0x021C72CC(r0 = side, r1 = &cardword)`

Exact native sequence, to copy verbatim:

```
bl   0x0219C510        ; r0 = &pick word
adds r1, r0, #0        ; r1 = that pointer
adds r0, r6, #0        ; r0 = side
bl   0x021C72CC        ; move it to the hand
->   movs r0, #0x64    ; then return the COMPLETION phase
```

⚠️ It takes a POINTER to a card word, not a ref. The word encodes the instance the
way every other site does -- `inst = (w >> 23) & 0xFF`, `side = (w >> 14) & 1` -- so
from a stored `v = (inst << 1) | side` the word is
`((v >> 1) << 23) | ((v & 1) << 14)`, built into a 4-byte ov5 scratch and passed by
address. (An earlier read of 0x021C72D8 looked like a DECK searcher; that loop over
player+0x304 is just one of its per-zone searches -- it locates the card wherever it
is, then moves it.)

⚠️ `0x021C72CC` is itself a thunk -- `LDR R3,=0x021C72D9 ; MOV R2,#1 ; BX R3` -- and
note the engine's own literal carries the THUMB BIT. Same rule as
thumb.blx_needs_thumb_bit; ours must too.

### CLAUSE 2 IS NOW FULLY SPECIFIED

```
0x80 : return 0x7F
0x7F : slot = table lookup by desc[+0xC]        (per-instance, session 21)
       none  -> 0x0225BF30(1 - side) ; return 0x78
       found -> 0x0219A818(side, <yes/no id>) ; return 0x7E
0x7E : build the card word from the slot's banished_instance into scratch
       0x021C72CC(side, &word)
       clear the slot
       return 0x64
0x64 : 0x021D269C(side) ; return 0
```
Every address needs `| 1` when reached by `BLX Rm`.

Remaining choice, not a blocker: the Yes/No prompt id. Clause 2 is OPTIONAL ("you
can"), and id 0x46 is the Spell-activation "select" message. The id enumeration from
session 20 is the menu to pick from.

## SESSION 23 — CLAUSE 2 BUILT, but the BANISH EVENT IS NEVER POSTED

### Clause 1: confirmed correct, including the per-copy fix

Double discard, both effects resolved:
```
slot 0: acting 26 (0x1859) -> banished 72 (cid 0x2356)
slot 1: acting 24 (0x1859) -> banished 46 (cid 0x1D85)
```
Two copies, two independent records, correct cards. The side-keying collision is
fixed and clause 1 is DONE.

### Clause 2: no dispatch at all

Savestates: ml3 (one Wyvern banished from the GY), ml4 (both banished). In BOTH:
```
entries = 6        <- unchanged from the discard; the resolver was NEVER invoked
```
Build verified resident in the same savestate: PART G applied at 0x021D1C44
(e3f7d3fd), ov5 stub head f0b5, cls2[165] +04 = 0x0239C015.

**The event was never posted.** The queues hold only the discard events for our cid:
```
0x0229A7FC[1] : cid 0x1859 zone 0x0E event 0x1E sel 2
0x0229A37C[0] : cid 0x1859 zone 0x0E event 0x1F sel 2
0x0229A37C[1] : cid 0x1859 zone 0x0E event 0x1E sel 2
```
No entry with zone 0x0F anywhere, in either state.

### ⛔ THE RELOCATION APPLIER IS NOT UNIVERSAL

PART G gates the banish leaf inside 0x021D1300, and the gate simulation proves it
admits 0x1859 when dest == 0x0F. Since no event appears, **0x021D1300 is not entered
for a GY -> banished move at all.** PART G is correct and irrelevant.

This is the SAME class of mistake as assuming the leave dispatcher handled hand->GY:
different (source, destination) pairs are moved by different routines, and the
applier only covers the ones tested so far. 0x021D1300 has just THREE callers
(0x021C6CB8, 0x021D1F06, 0x021D2450), so it was never going to cover everything.

⚠️ Note also: the discard posts TWO events for the cid, 0x1F and 0x1E -- worth
remembering when reasoning about which one a record responds to.

### Next experiment (static, cheap)

Find what actually moves a card GY -> banished, and whether it posts an event:
  1. read 0x021D1300's three callers and see which (src, dst) pairs each covers;
  2. find the routine used when an effect banishes a card ALREADY IN THE GY -- the
     natural candidates are 0x021C7484 (the KB's relocation primitive) and the
     0x021D1DAC family, whose dest_sel selects GY(0x0E)/banished(0x0F);
  3. check whether Cyber Ouroboros 0x1CF6 -- the native "when this card is removed
     from play" card, and one of only two cids on the banish leaf -- is actually
     reachable in this build, i.e. whether that leaf is live at all for a GY source.
     If the leaf only fires for FIELD -> banished, clause 2 needs a different hook
     entirely.

**Clause 1 ships as-is; clause 2 is blocked on (3).**

## SESSION 24 — PROVEN: the relocation applier does NOT move GY -> banished

Instrumented PART G to record the destination zone our cid is seen with at the
banish node (block A 0x021B57EE routes our cid to block B 0x021B56B8, which does
`STRH r0,[scratch+0x2A]` before gating). Pure ov3 in both blocks -- 0x021D1300 runs
in PUZZLES, where a BLX into the ov5 cave would freeze the console.

MEASURED, before and after banishing an Eclipse Wyvern out of the GY:
```
ml2 (before): scratch[+0x2A] = 0x0E    GY [0x2321, 0x1D85, 0x1859]
ml3 (after) : scratch[+0x2A] = 0x0E    banished [0x1D85, 0x1859]
```
The card moved. Our cid was NEVER seen at that node with dest = 0x0F.

**Conclusion: 0x021D1300 is not the mover for a GY -> banished move.** PART G gates
a chain this transition never enters. No tuning of it can make clause 2 fire.

(The recorded 0x0E is the GY-bound pass FALLING THROUGH the first chain into the
second -- which independently confirms the dest-zone gate rejects that case, the
bug that killed discard/mill in session 23.)

### Where that leaves the search

0x021D1300 has three callers and posts events 0x1E (0x021D1F06), 0x20 (0x021D2450)
and a variable one (0x021C6CB8); the discard posts BOTH 0x1F and 0x1E. None of them
covers GY -> banished, so that move has its own routine, exactly as hand -> GY had
its own dispatcher separate from the leave path.

⚠️ CORRECTION to the KB: `0x021C7484` is NOT a relocation primitive. Disassembled,
it only calls 0x021C3BC8 -- the replay-message log. Anything built on that label is
built on sand.

### Next experiment

Find the routine that moves a card GY -> banished and see whether it posts any event:
  1. locate the writer of the banished array (player+0x7B4, count +0x1C) -- the
     store that appends to it is the anchor, and it is a small search;
  2. from there, walk up to the caller and check for a post (register-prim
     0x021D3168 or enqueue 0x021D2FC4);
  3. if it posts nothing at all, clause 2 cannot be a triggered effect on this
     build and needs a different design entirely (e.g. a poll at a phase boundary).
⚠️ Do NOT assume a third mover is universal either -- verify per (source,
destination) pair. That assumption has now cost two builds.

## SESSION 25 — ⭐ SOLVED: the GY→banished mover IS found, and it DOES post an event

Session 24's next-experiment is answered. **Clause 2 is implementable as a real
triggered effect.** The blocker was never "no event exists" — it was that
`0x021D1300` is the wrong applier for this transition, and the right one has its
own, separate, hardcoded 2-cid gate.

### ⭐⭐ `0x021C7118` — the banish-FROM-GRAVEYARD core

```
0x021C7118(r0 = side, r1 = &cardword, r2 = flags, r3 = facedown)
```
It is NOT one of the eight wrappers of the general relocation core `0x021C6B00`;
it is a separate routine that hardcodes BOTH zones into the word it builds:

```
0x021C7156  movs r0,#0x0E ; lsls r0,r0,#0xA  ; orrs r1,r0   ; SOURCE zone = 0x0E (GY)
0x021C7178  movs r0,#0x1E ; lsls r0,r0,#0x12 ; orrs r0,r1   ; DEST  zone = 0x0F (banished)
0x021C7184  bl 0x021BABE8      ; 0 -> return 0, no move at all
0x021C7198  bl 0x021A2510      ; <0 -> return 0
0x021C71A4  r3 != 0 -> set the face-down banish flag (0x10 in the word's high byte)
```

### ⭐⭐ THE GATE — a plain two-cid compare, not a binary-search chain

```
0x021C71BC  ldr  r0,[r4]                          ; the card word
0x021C71BE  ldr  r1,=0x000017BB                   ; Necroface        (pool 0x021C724C)
0x021C71C0  lsls r0,r0,#0x12 ; lsrs r0,r0,#0x12   ; cid = w & 0x3FFF
0x021C71C4  cmp  r0,r1
0x021C71C6  beq  0x021C71CE                       ; -> POST
0x021C71C8  ldr  r1,=0x00001CF6                   ; Cyber Ouroboros  (pool 0x021C7250)
0x021C71CA  cmp  r0,r1
0x021C71CC  bne  0x021C71F8                       ; everyone else: NO EVENT, move only
0x021C71CE  ... bl 0x021D3168                     ; <== THE EVENT POST (register-prim)
```

**Exactly the same two cids** as the `0x021D1D3E` leaf of `0x021D1300`'s non-GY
chain — the engine registers this trigger in two independent places, and PART G
only ever reached the one on the wrong path.

The posted event (`0x021D3168(r0, r1, r2)`):
```
r0 = 0x404F0000 | (card_side << 31) | cid
r1 = ref = (side | inst << 1)
r2 = the new card word
```
Decoding r0 against the identical construction at 0x021D1D5C
(bits 0..15 cid, 16..20 zone, bit 22 = 1, bits 25..30 event code, bit 31 side):
**zone = 0x0F, event code = 0x20.** Then unconditionally, gate or no gate:
`0x021C3BC8(0x32|flag, 0x0E, flags, ref)` (animation cmd 0x32 "banish", from-zone
0x0E) and `0x022391CC(0x20, word)` (replay/network log), then `return 1`.

### How it was found (the chain of anchors — reproducible)

1. `scratch/find_lit_refs.py 7B4` -> only 3 in-duel `ldr =0x7B4` append sites, and
   all three are the scenario loader / whole-state rebuild. So the arrays are
   reached generically, and the "bounded search on the append" of session 24's plan
   could never have found the mover directly.
2. **`0x0219CA28(side, zone, index) -> &zone_array[index]`** — jump table at
   `0x0219CA40`, index `zone - 0x0B`, base `0x0219CA42`:

   | zone | arm | player offset | meaning |
   |---|---|---|---|
   | 0x0B | 0x0219CA9C | +0x124 | **HAND** (savestate-confirmed: 4 and 5 cards) |
   | 0x0C | 0x0219CA4A | +0x4E4 | Extra Deck |
   | 0x0D | 0x0219CA5E | +0x304 | Deck |
   | 0x0E | 0x0219CA74 | +0x55C | Graveyard |
   | 0x0F | 0x0219CA88 | +0x7B4 | Banished |
   | else | 0x0219CAB2 | +0x34 + n*0x14 | monster / S-T zones |

   ⚠️ This CORRECTS the memory note that calls `player+0x124` the "summon list".
   Sibling with the identical jump table: `0x0219CAE4(side, zone, index) -> cid`.
3. **Identify the actual banisher from the savestates**, instead of guessing.
   `scratch/dump_zones.py` on ml2 vs ml3:
   ```
   GY      : [0x2321 i33, 0x1d85 i22, 0x1859 i14] -> [0x2321 i33, 0x1d85 i22, 0x12f9 i04]
   BANISHED: [0x1d85 i24]                         -> [0x1d85 i24, 0x1859 i14]
   HAND    : [..., 0x12f9 i04]                    -> [...]           (0x12f9 left)
   ```
   **cid 0x12F9 = Soul Release** ("select up to 5 cards in any Graveyard(s);
   banish them") — it went hand -> GY as it resolved. That is the card that did it.
4. Soul Release's resolver: **cls0[179] +04 = `0x02208D18`** (all four cls tables
   searched). Its resolve loop:
   ```
   0x02208D80  bl 0x02234964   ; pick i off the descriptor
   0x02208D84  bl 0x021A25E8   ; ref -> &cardword
   0x02208D8E  bl 0x021C7098   ; <== the banish
   ```
   and the *validation* loop above it requires `zone == 0x0E` for every pick.
5. `0x021C7098(desc, &word, flags)` -> `0x021C7118` (31 call sites; `0x021C7104`
   is a second thin wrapper of the same core).

### Why PART G could never have seen it — and the diagnostic is sound

`0x021C7118` calls the register-prim `0x021D3168` **directly**. It never touches
`0x021D1300`. Re-verified this session that PART G is resident and correctly placed
in the ROM that produced ml2/ml3:
```
0x021D1C44 = e3 f7 d3 fd            -> BL 0x021B57EE  (decoded, not assumed)
0x021B57EE = 0c 98 03 49 8d 42 02 d0 9e 39 8d 42 70 47 5c e7 ... 59 18   (block A)
0x021B56B8 = 02 4a 50 85 0f 28 00 d1 ad 42 70 47 44 c1 39 02             (block B)
```
and that our cid **does** reach node 0x021D1C44 — on ANY `0x021D1300` entry, not
just a banish: the GY chain's accept/reject leaves at 0x021D19BE fall straight
through into a second cid chain at 0x021D19C0 that routes 0x1859 there. So
`scratch[+0x2A]` is written on every applier entry for our cid. It read 0x0E in
both ml2 and ml3 -> **`0x021D1300` was not entered at all**. The measurement was
right; the conclusion drawn from it ("nothing posts an event") was too strong.

⚠️ THE LESSON, THIRD TIME: hand->GY, field->banished and **GY->banished** each have
their own routine AND their own independent cid gate. Three appliers now:
`0x021C6B00` (8 wrappers, posts via 0x021D1300), `0x021D1DAC` (event 0x1E, posts
via 0x021D1300), `0x021C7118` (GY->banished, posts via 0x021D3168 directly).

### Also mapped this session (secondary, all static)

* `0x021C6B00` — the general relocation core, exactly 8 thin wrappers, each
  hardcoding a destination zone; event code `[sp+0x48] != 0 -> 0x1F else 0x20`;
  posts at `0x021C6CB8 bl 0x021D1300`. `0x021C6E4C` = generic banish (16 callers,
  nearly all banishing from the HAND, zone 0x0B).
* `0x021C3BC8(op, a1, a2, a3)` is an **append to the 4xu16 animation/replay command
  queue at 0x02299B68** (count at 0x0229A360+8, cap 0x100) — not a mover, but not
  merely a log either. Command 0x32 = banish, 0x3E = other relocation.
* `0x021D1300` performs **no physical movement whatsoever** — its only tail is
  `bl 0x021D3168`. It is purely event admission + post.
* The `0x021D1B98` non-GY cid chain, simulated for every cid (new tool
  `scratch/sim_cid_switch.py`): 6 arms; the banish leaf `0x021D1D3E`
  (`dest == 0x0F && (flags & 0xC0) != 0xC0`) holds exactly **{0x17BB, 0x1CF6}**.
* Cyber Ouroboros 0x1CF6 = **cls2[307]**, slots `+04 = 0x022065B8`,
  `+10 = 0x021E5200`, the rest 0. Necroface 0x17BB = cls2[151] AND cls1[396], both
  `+04 = 0x0221C204`. Neither has a leave-mask row — a banish trigger needs **no**
  mask-table or list30 registration.

### Tools added this session
- `scratch/dis.py` — resilient Thumb disassembler that RESYNCS over literal pools.
  `scratch/disasm_range.py` silently stops at the first non-instruction, which is
  why this whole region looked empty for the first hour. Prefer `dis.py`.
- `scratch/find_lit_refs.py <hex>` — every `ldr Rd,[pc,#imm]` whose literal == V.
- `scratch/find_bl_callers.py <addr>` — decoded BL/BLX-imm call sites.
- `scratch/sim_cid_switch.py <entry> <hi>` — walk ANY base±imm cid chain for every
  cid (generalises `sim_gy_cid_switch.py`).
- `scratch/dump_zones.py <savestate>...` — both players' hand/deck/GY/banished/Extra
  with each word's decoded fields. This is what identified Soul Release in one shot.
- `scratch/classify_banish_sites.py`, `scratch/find_banish_array_writer.py`,
  `scratch/dump_zone_offset_tables.py` — the search that got here.

## Next experiment — the hook is designed; ONE unknown left before building

### The hook (verified safe, NOT yet written)

Displace `0x021C71C8 ldr r1,=0x1CF6 ; 0x021C71CA cmp r0,r1` (4 B, native bytes
`21 49 88 42`) into a `BL` to an ov3 dead-code stub:

```
        ldr  r1, =0x1CF6
        cmp  r0, r1
        beq  out          ; Z already set -> caller's BNE falls through to POST
        ldr  r1, =0x1859  ; DONOR_CID
        cmp  r0, r1
  out:  bx   lr           ; BX never touches the flags
```
12 B code + 8 B pool = 20 B. **Checked this session:**
* nothing anywhere in ov3 branches to 0x021C71C8 / CA / CC (exhaustive scan);
* `r0` (the cid) is live afterwards at 0x021C71DC and the stub never writes it;
* `r1` is dead on both exits (reloaded at 0x021C71CE, re-set at 0x021C71FC);
* LR is free — `0x021C7118` pushed it and returns `pop {...,pc}`, and the code past
  the hook calls `bl` anyway;
* ⚠️ **ov3, never ov5**: 0x021C7118 is shared engine code that also runs in puzzles,
  where ov41 evicts the cave;
* space: reclaim PART G's two blocks (0x021B57EE 22 B + 0x021B56B8 16 B), now
  provably pointless — they gate a chain this transition never enters. 20 B fits
  0x021B57EE alone (base 0x021B57F0 for a 4-aligned pool).

### THE ONE REMAINING UNKNOWN

Whether a cls2 record on our donor is actually *enumerated* for event **0x20 /
zone 0x0F**. Everything else clause 2 needs already exists and is verified: the
per-copy memory (PART H), the phase machine (the `desc[+3] == 0x0F` branch, written
and offline-verified), and every primitive.

The experiment, in order, all static — no emulator:
1. Disassemble Cyber Ouroboros's resolver **0x022065B8** and its `+10` slot
   **0x021E5200**. It is the native consumer of exactly this event, so it shows what
   a cls2 record must look like to receive it — and whether the `+10` condition slot
   (which our donor leaves at 0) is required.
2. Identify the four data rows referencing 0x1CF6 at **0x0226F070, 0x0226F784,
   0x0226FD18, 0x02270624**. If any is a criteria/timing registration, the donor
   needs the matching row, inserted count-neutrally over a phantom.
3. ⚠️ COMPOSITION: the donor ALREADY has a cls2 record (clause 1).
   `find_event_handler 0x0224A118` returns the LEFTMOST same-cid record, so a SECOND
   cls2 record would shadow clause 1 — the Warwolf E1/E2 bug exactly. Clause 2 must
   reuse the existing record and branch inside the ov5 wrapper on `desc[+3]`, which
   is what PART H already does. **Do not add a second row.**

Only after (1)-(3) write the hook.

## SESSION 25 (cont.) — PART G RETIRED, PART I BUILT

Because the gate is on a path now **proven** to run (Soul Release -> 0x021C7098 ->
0x021C7118, with the move itself visible in the ml2/ml3 savestate diff), admitting
the donor there is not a speculative hook — it is the single instruction pair
standing between the mover and its `bl 0x021D3168`.

### PART G — RETIRED (`BYPASS_G = True`)

`0x021D1C44` is back to stock (`55 48 85 42`), and both of its ov3 dead blocks are
released: `0x021B57EE` (22 B, re-used by PART I) and `0x021B56B8` (16 B, free).
ov3 dead-code budget went 68 B -> 84 B free.

### PART I — the banish-from-GY event gate

Displaces `LDR R1,=0x1CF6 ; CMP R0,R1` (4 B @`0x021C71C8`, native `21 49 88 42`)
into `BL 0x021B57F0` (`ee f7 12 fb`). Stub, 20 B at `0x021B57F0` (2 B into the block
so the literal pool is 4-aligned; 0x021B57F0+20 lands exactly on the block end):

```
0x021B57F0  02 49   ldr r1,[pc,#8]   ; = 0x1CF6   Cyber Ouroboros
0x021B57F2  88 42   cmp r0,r1
0x021B57F4  01 d0   beq 0x021B57FA               ; Z already set -> caller posts
0x021B57F6  02 49   ldr r1,[pc,#8]   ; = 0x1859   DONOR
0x021B57F8  88 42   cmp r0,r1
0x021B57FA  70 47   bx  lr                       ; BX never touches the flags
0x021B57FC  f6 1c 00 00      .word 0x1CF6
0x021B5800  59 18 00 00      .word 0x1859
```
`assert_thumb1_only` clean; disassembled from the built ROM, not just from the
emitted bytes. Kept halves confirmed untouched in the built image: `0x021C71BC`
= `20 68 23 49` (LDR R0,[R4] ; LDR R1,=0x17BB) and `0x021C71CC` = `14 d1`
(BNE 0x021C71F8).

Necroface 0x17BB keeps its own arm above the hook; Cyber Ouroboros 0x1CF6 is
re-tested inside the stub, so **both native cards still work**.

`verify()` PASSES on the single-card ROM; `check_allocations` clean (84 B ov3 free).

### ⭐ AND THE "ONE REMAINING UNKNOWN" IS ALSO CLOSED — STATICALLY

The register-prim `0x021D3168(r0 = event word, r1 = ref, r2 = card word)` memsets a
0x24-byte descriptor on its own stack, unpacks the event word into it, and hands it
to COMMIT `0x021EDA08`. Read straight off 0x021D317A..0x021D31B6:

```
desc[+0x0] u16 = w & 0xFFFF          the CID
desc[+0x2] u8  = (w >> 31) & 1       side
desc[+0x3] u8  = (w >> 16) & 0x1F    the ZONE
desc[+0x4] u8  = (w >> 25) & 0x3F    the EVENT CODE
desc[+0x5] u8  = (w >> 21) & 0x7     *** the CLASS SELECTOR ***
desc[+0x6] u8  = (w >> 24) & 1
desc[+0xC] u16 = r1 (packed ref; refilled from 0x021A23E0 when (r1>>1)==0)
[sp+0x20]      = the card word
```

`desc[+0x5]` is exactly the field `find_event_handler 0x0224A118` uses to choose
which cls table to binary-search. Feeding it our event word:

```
w = 0x404F0000 | (side << 31) | cid
  desc[+3] ZONE  = 0x0F     <- precisely what PART H's clause-2 branch already tests
  desc[+4] EVENT = 0x20
  desc[+5] CLASS = 2        <- cls2, where the donor's record ALREADY lives
```

So the banish event reaches `find_event_handler` with **our cid and class 2**, and
the donor has exactly one cls2 record (cls2[165], +04 = the ov5 wrapper 0x0239C015).
It is found, and the wrapper is entered with `desc[+3] == 0x0F`.

Note both posters OR in bit 22 unconditionally — `0x021D1300` at 0x021D1D80
(`movs r2,#1 ; lsls r2,#0x16`) and `0x021C7118` via the 0x404F0000 literal — and
`(1<<22) >> 21 & 7 == 2`, so **every relocation event in this engine is class 2**.
That is also why a second cls2 row must never be added for clause 2: it would be
shadowed (leftmost-record rule) *and* it is unnecessary — one record, branch on
`desc[+3]`.

Recorded as KB fact `event.register_prim_descriptor_layout` (VERIFIED).

**Net: the only thing left unmeasured about clause 2 is its behaviour** (prompt id,
the pick, the move-to-hand) — not whether it is reachable. The test below is now a
behaviour test, not a feasibility test.

### ⚠️ WHAT THIS BUILD DOES AND DOES NOT PROVE

Proven statically, this session — an unbroken chain from the card to the wrapper:
* Soul Release 0x12F9 (cls0[179] resolver 0x02208D18) banishes via
  `0x021C7098 -> 0x021C7118`, and the ml2/ml3 savestate diff shows the move itself;
* `0x021C7118` is the GY -> banished mover (source 0x0E and dest 0x0F hardcoded);
* its ONLY gate on posting the event is the 2-cid compare PART I now widens;
* the post is `0x021D3168` with word `0x404F0000 | side<<31 | cid`;
* that word unpacks to `desc[+3] = 0x0F`, `desc[+4] = 0x20`, **`desc[+5] = 2`**;
* `find_event_handler 0x0224A118` searches cls2 for our cid — one record, cls2[165],
  `+04 = 0x0239C015` = PART H's wrapper, entered with `desc[+3] == 0x0F`.

**What remains unmeasured is clause 2's BEHAVIOUR, not its reachability**: PART H's
phase machine has never executed, so its prompt id, its pick and its move-to-hand
are all untested in-game. Two things could still be wrong that no static reading
catches: the wrapper could be entered and then mis-sequence its phases, or the
Yes/No prompt id could be the wrong message. Both are visible in the diagnostics.

### Composition check — the FULL chain, not just this card

`apply_all_patches` ran all 31 steps to
`data/over_the_nexus/working/rom_all_patches.nds` (collision guard clean before any
byte was written: 87 ov5 slots / 29 phantom claims / 5 ov3 dead-code claims, 84 B
ov3 free). Then `verify()` was run on **every** patch module in the chain against
that combined ROM:

```
19 PASS, 1 "FAIL", 4 modules with no verify()
```

The single failure is **patch_wonder_wand** (`grant row is +800/+0, expected
+500/+0`) and it is **pre-existing and expected**: Wonder Wand is commented out of
the chain (`apply_all_patches.py:814`), and its grant row reads 800/0 identically in
stock `rom.nds` — i.e. the patch simply was never applied. Nothing to do with PART I.
⚠️ Note for anyone running this sweep again: `verify()`'s first parameter is `out` in
some modules and `out_path` in others, so pass it positionally or by introspection —
calling `verify(out=...)` uniformly produces 17 bogus TypeError "failures".

PART I cannot collide with another patch: an exhaustive grep shows Eclipse Wyvern is
the only module that touches 0x021C7xxx, and its ov3 block is in the ledger.

### Slots claimed / released by this session

| slot | before | after |
|---|---|---|
| ov3 dead block 0x021B57EE (22 B) | PART G block A | **PART I** gate stub (20 B @0x021B57F0) |
| ov3 dead block 0x021B56B8 (16 B) | PART G block B | **RELEASED** |
| ov3 free total | 68 B | **84 B** |

No ov5, phantom-cid, registry or cls-table changes — clause 1's allocations are
untouched.

### KB contribution this session

216 facts, **0 FAIL** (2 FAIL at session start). New, all VERIFIED:
`event.gy_to_banished_mover`, `event.banish_from_gy_cid_gate`,
`event.register_prim_descriptor_layout`, `event.animation_command_queue`,
`ram.hand_is_zone_0x0B`. Corrections: the GY/banished arrays are NOT zero-filled
past `count` (removals leave ghost words — the old proof asserted something false and
that is what was FAILing); `ram.card_instance_record`'s proof ignored its own
face-up caveat and broke on a SET monster; `player+0x124` is the HAND, not the
"summon list" (fixed in `ram.container_for_zone_code` and in the
otn-summon-event-dispatch-tg note); and the stale "0x021C7484 relocates a card"
comment in `ov5_cave.py` now carries the correction (it tail-calls 0x021C3BC8 with
opcode 0x40 — a command-queue append), which matters for whoever revisits Sea Lancer E1.

### THE TEST (one savestate, no GDB)

In a normal duel (not a puzzle — ov5 must be resident for the wrapper):
1. get an Eclipse Wyvern into the GY so clause 1 resolves and records its pick
   (discard or mill it; confirm with `read_ew_scratch`);
2. banish it out of the GY (Soul Release is the known-good actor);
3. save state, then
   `.venv-1/Scripts/python.exe -m scratch.read_ew_scratch <state>`.

Read `entries` and `event`:
* `entries` INCREASES past its post-clause-1 value and `event = 0x20`
  -> the wrapper was invoked for the banish. Clause 2's machine is live; from here
  it is a behaviour question (prompt id, the pick, the move-to-hand).
* `entries` UNCHANGED -> the event posts but no cls2 record is enumerated for
  event 0x20 / zone 0x0F. Then the next question is the descriptor's class
  selector (`descriptor[+5]`, consumed by `find_event_handler 0x0224A118`) —
  compare against what Cyber Ouroboros's cls2[307] receives, since it is the one
  native card that demonstrably consumes this exact event.

Also re-check clause 1 in the same session (field / discard / mill) — PART I
touches a routine clause 1 never uses, so a regression there would mean something
unrelated moved.

## SESSION 26 — ⭐ CLAUSE 2 TRIGGERS IN-GAME. The action was the wrong mover.

### The measurement (rom_eclipse_wyvern.ml2 before / .ml3 after, 18:01/18:02 vs ROM 16:40)

```
ml2  entries=3  phase=0x7e  progress=2  acting=28  event=0x1e
     slot 0: acting 28 (0x1859) -> banished 44 (0x1D85)
     GY [0x2359 i37, 0x1859 i14]   BANISHED [0x1D85 i22]   hand [0x12F9, 0x19FE, 0x2278, 0x1D85 i23]

ml3  entries=7  phase=0x64  progress=2  acting=28  event=0x20     <-- BANISH EVENT
     per-instance table EMPTY (the slot was consumed)
     GY [0x2359 i37, 0x12F9 i04]   BANISHED [0x1D85 i22, 0x1859 i14]   hand [0x19FE, 0x2278, 0x1D85 i23]
```

Everything up to the final primitive is **confirmed working**:

* **PART I works.** `event = 0x20` — the banish event was posted and dispatched.
* **The record routes to our cls2 row**, so `desc[+5] = 2` was right.
* **The phase machine sequences correctly**: entries 3 -> 7 = exactly four invocations
  (0x80, 0x7F, 0x7E, 0x64) and the last phase seen is 0x64, the completion phase.
* **The slot lookup by acting ref works**: the table is empty in ml3, i.e. `c2_do`
  reached `do_found` and released it. Clause 1's record (`acting 28 -> banished 44`)
  was correct too: 44 = (22 << 1) | 0, and 0x1D85 sits at instance 22 in the
  banished array.
* Clause 1 is unregressed (it recorded the pick in ml2 as always).

The card did NOT arrive in the hand (ml3's hand is unchanged apart from Soul Release
leaving), and the user saw a **deck search + shuffle** instead.

### ⚠️⚠️ THE BUG — `0x021C72CC` IS THE **DECK** -> HAND MOVER, NOT A GENERAL ONE

Its single search loop (0x021C732A..0x021C744C) walks `player + 0x304` with count
`player + 0x10` — the Deck, and only the Deck — and its own emit at 0x021C739C
passes source zone **0x0D**. It is the primitive behind White Stone of Legend and
Cross Porter, and **both of those search the Deck**, which should have been the
tell. The session-22 note "that loop over player+0x304 is just one of its per-zone
searches — it locates the card wherever it is" is WRONG; there is exactly one loop,
and `find_lit_refs 21C72D9` shows exactly ONE thunk into its body, so there are no
per-zone sibling variants either.

Our word construction was fine (that function only reads inst/side off the word, and
our ref decoded back to 44 correctly). The zone was the whole problem.

**THIRD TIME.** hand->GY, GY->banished, and now banished->hand each needed their own
routine. The rule in `event.gy_to_banished_mover` is not a curiosity, it is the
dominant fact about this engine's relocation layer.

### ⭐ THE GENERAL EMITTER — `0x021C69D0`, and the complete native zone-pair map

`0x021C69D0(r0 = side, r1 = SOURCE zone, r2 = ref, r3 = side,
            [sp+0] = DEST zone, [sp+4] = DEST index, [sp+8] = flags)`
packs both endpoints into two u16s — `{bit0 side, bits1-5 zone, bits6-15 ref}` each —
and emits animation/relocation command **0x3E** through 0x021C3BC8. It is the only
routine in the engine with BOTH zones as parameters. Its eight native callers give
the whole map:

| call site | source | dest |
|---|---|---|
| 0x021C69C0 | 0x0B hand | 0x0D deck |
| 0x021C6A80 | 0x0E GY | runtime |
| 0x021C6AE4 | 0x0F banished | 0x0C/0x0D (deck or Extra, by card type) |
| 0x021C6CA8 | 0x0B hand | 0x0E GY |
| 0x021C6F78 | runtime | runtime |
| 0x021C726C | 0x0F banished | 0x0E GY |
| 0x021C72B2 | 0x0F banished | 0x0D deck |
| **0x021C739C** | **0x0D deck** | **0x0B HAND** |

**There is no native banished -> hand caller** — no OTN card does it. (Gold
Sarcophagus comes closest but its add-back is a delayed rider: it banishes at
0x0221CD96 then registers an association at `0x021D2584(side, cid, kind 0x41, ref)`.
⚠️ That is worth knowing on its own: it means the NDS *does* have the
"card banished by this card's effect" association mechanic that session 20 concluded
was absent — it just is not the 3DS's 0x38C80C shape. Not needed here, since our ov5
scratch already remembers the card correctly, but it is the right lead if a future
card needs it without a cave.)

So clause 2 builds the missing pair as a **one-immediate change from the native
deck->hand site**, whose exact shape is at 0x021C7384..0x021C739C:

```
movs r0,#0x0B ; str r0,[sp]        ; DEST zone  = hand
ldr  r1,=0x0229ACA0                ; player+0x0C = the HAND COUNT
ldr  r0,[sp,#0x10] ; ldr r0,[r1,r0]; player[side].hand_count
movs r1,#0x0D                      ; SOURCE zone = deck   <- we pass 0x0F
str  r0,[sp,#4]                    ; DEST index = append at the end
movs r0,#0 ; str r0,[sp,#8]
r0 = r3 = side ; r2 = ref
bl 0x021C69D0
```
⚠️ `0x0229ACA0` being the hand count independently corroborates
`ram.hand_is_zone_0x0B` from a completely different direction.

⭐ And it takes a **REF**, `(inst << 1) | side` — exactly what CAVE_EW_SCRATCH already
stores. The card-word synthesis (and the WORD_SLOT scratch word) is gone entirely.

### The rebuilt action (PART H, `c2_do`)

```
ldrh r4,[r2,r5]        ; the banished card's packed REF
strh r0,[r2,r5]        ; release the payload
movs r6,#1 ; ands r6,r4               ; side = ref & 1 (the card's owner)
ldr  r1,=0x0229ACA0 / =0x0229B7DC     ; two literals beat a MULS
ldr  r5,[r1]                          ; destination index = current hand size
ldr  r7,=0x021C69D1                   ; ⚠️ THUMB BIT
push {r0,r1,r2}                       ; reserve the 3 outgoing stack words
movs r0,#0x0B ; str r0,[sp]           ; DEST = hand
str  r5,[sp,#4] ; movs r0,#0 ; str r0,[sp,#8]
r0 = r3 = r6 ; movs r1,#0x0F ; r2 = r4
blx  r7
pop  {r0,r1,r2}
movs r0,#0x26 ; movs r1,#0 ; blx =0x022391CD   ; the tail 0x021C6A9C/0x021C7258 emit
movs r0,#0x64
```
`push {r0,r1,r2}` reserves the outgoing frame without needing `sub sp,#imm`, which
thumb_asm does not implement. Both BLX literals carry the Thumb bit (0x021C69D1,
0x022391CD) — `thumb.blx_needs_thumb_bit`.

Recorder grew 288 -> 316 B, so its reserve went 0x130 -> 0x160 and
**CAVE_EW_SCRATCH moved 0x0239C144 -> 0x0239C178**, CAVE_FREE -> 0x0239C1A8.
`check_allocations` clean. `verify()` passes.

### NEXT TEST — same recipe

Discard/mill a Wyvern (clause 1 records), then Soul Release it out of the GY, save,
`read_ew_scratch` + `dump_zones`.

* **hand gains the remembered card and the banished array loses it** -> clause 2 is
  functionally DONE, and only the prompt remains.
* the deck search is gone but nothing moves -> the emitted command 0x3E is right but
  something downstream refuses; compare against a live deck->hand (any searcher).
* ⚠️ Expect it to be **mandatory**, not a Yes/No: `c2_ask` raises
  `0x0219A818(side, 0x33)`, the native add-to-hand MESSAGE, and there is no evidence
  that id produces a choice. That is the last known gap, and it is separate work —
  the hand-SS offer path (Battle Fader wiring) is the template to mine, not Cyber
  Ouroboros (whose draw is mandatory).
* Also still to do before shipping: strip the diagnostics at +0x20..+0x2A.

## SESSION 27 — ⭐⭐ CLAUSE 2 IS FUNCTIONALLY CORRECT IN-GAME

### The measurement (ml2 18:30 / ml3 18:30 vs ROM 18:12 — both newer than the build)

```
ml2  entries=3 phase=0x7e event=0x1e   slot 0: acting 24 (0x1859) -> banished 44 (0x1D85)
     hand [0x1E20 i25, 0x198D i16, 0x12F9 i03]   BANISHED [0x1D85 i22]   GY 7 incl 0x1859 i12

ml3  entries=7 phase=0x64 event=0x20   table EMPTY
     hand [0x1E20 i25, 0x198D i16, 0x1D85 i22]   BANISHED [0x1859 i12]   GY 7 incl 0x12F9 i03
```

**The exact remembered card moved from the banished zone to the hand.** Instance 22 —
the very copy clause 1 banished (slot said `banished 44` = (22 << 1) | 0) — left
`player+0x7B4` and appeared in `player+0x124`, while the Wyvern itself took its place
in the banished zone. Clause 1 unregressed. `0x021C69D0(side, 0x0F, ref, side,
[sp]=0x0B, [sp+4]=hand_count, [sp+8]=0)` is the correct banished -> hand emit.

Two defects remain, both cosmetic/UX rather than state:

### 1. THE DECK WAS GENUINELY SHUFFLED

Not an animation — measured. Side 0's deck is the **same multiset in a different
order** across ml2 -> ml3 (side 1 untouched, count 28 both sides).

**Prime suspect: prompt id 0x33.** Enumerating every `0x0219A818` call site by its r1
immediate gives 0x33 exactly THREE users — 0x022080BC (the shared add-from-DECK-to-hand
resolver = White Stone of Legend / Cross Porter), 0x02221018, 0x0222BCB2 — **all Deck
searches**. Raising it put the game in the Deck-search UI, and a Deck search shuffles
on close. It is also, obviously, not a choice, which is defect 2.

⚠️ It is a suspect, not a proof. The other candidates on clause 2's path are
`0x021D269C(side)` (the completion phase, which clause 1 also calls — but clause 1
banishes from the Deck, so a shuffle there is legitimate and invisible) and the
command-0x3E executor itself. **Removing the prompt is the experiment that separates
them**, and it is a change we want regardless since 0x33 is the wrong message.
DONE: `c2_ask` no longer raises any prompt (recorder 316 -> 304 B).

* shuffle GONE -> it was id 0x33. Clause 2 is then correct-but-silent.
* shuffle REMAINS -> it is `0x021D269C` or the 0x3E executor; next step is to drop the
  completion call and see, then inspect the command handler.

### 2. NO YES/NO — and the mechanism is already in the repo

The prompt was never going to come from the resolver. Per `dispatch.cls_slot_roles`:
**+0x0C slot3 = ACTIVATION CONDITION** (returns a code: 0 = cannot activate, 1 =
activatable if slot2 finds a target, >=2 = unconditional; **DEFAULT 1 when the slot is
0**) and **+0x10 slot4 = COST / ACTIVATION-PROCEDURE step**, both driven by the
activation state machine at **0x02217F80**. That machine is what asks.

`patch_gravekeepers_recruiter` already ships the A/B pair that proves it:

```
Botanical Girl  (OPTIONAL "you can")  cls2 = (0x02207EF5, 0, 0x021F0821, 0x021E51E5, 0)
Sangan          (MANDATORY)           cls2 = (0x02207EF5, 0, 0,          0,          0)
```

Our donor's cls2[165] is `(wrapper, 0, 0, 0, 0)` — the **Sangan shape**. That is
exactly why clause 2 resolved without asking, and it predicts the symptom precisely.

### ⚠️ THE COMPOSITION PROBLEM (unsolved — read before building)

**ONE cls2 record serves BOTH clauses.** Clause 1 is MANDATORY ("If this card is sent
to the Graveyard: Banish 1...") and clause 2 is optional ("You can add..."). Filling
+0C/+10 with Botanical Girl's values would make **clause 1 optional too** — a
regression on the one part of this card that is finished and confirmed.

The way out is the trick the resolver already uses: point +0C and +10 at **ov5 stubs
that branch on `desc[+3]`** — 0x0E takes the mandatory shape (condition >= 2, no
activation procedure), 0x0F takes Botanical Girl's optional shape.

⚠️ UNPROVEN and it must be checked before any build: that slot3/slot4 are invoked with
a descriptor carrying the zone at +3 at all. Slot1 demonstrably is (that is how the
whole clause split works), but slot3/slot4 run in a different machine (0x02217F80)
and may receive a different structure. **Verify that first.** Also confirm what
0x021F0821 actually tests — Botanical Girl is "sent from the FIELD to the Graveyard",
so its condition may be field-only and wrong for a banish.

### Where clause 2 stands

| | status |
|---|---|
| trigger on banish from GY | ✅ IN-GAME CONFIRMED (PART I) |
| routes to our cls2 record | ✅ |
| phase machine sequences | ✅ 4 phases, ends 0x64 |
| remembers the exact card, per copy | ✅ |
| moves that card banished -> hand | ✅ IN-GAME CONFIRMED |
| declines cleanly with nothing remembered | untested |
| no spurious deck shuffle | ⏳ prompt removed; next test decides |
| Yes/No prompt | ❌ needs the slot3/slot4 activation procedure |
| diagnostics stripped | ❌ before shipping |

## SESSION 28 — the shuffle SOLVED: `0x021D269C` is SHUFFLE THE DECK, not "completion"

Test 3 (ml2/ml3 18:43, ROM 18:36): clause 2 correct again — hand
`[0x19FE, 0x198D]` -> `[0x19FE, 0x198D, 0x1D85]`, banished `[0x1D85]` -> `[0x1859]`,
no prompt (as expected for the Sangan record shape). **Deck still shuffled** (same
multiset, new order, our side only). So prompt id 0x33 was NOT the cause — removing
it was still right, but it exonerated itself.

### How it was found (no more elimination-by-rebuild)

1. The shuffle is a real permutation, so find the permuter: the only RNG caller
   (0x0219C98C) that also touches the deck container is **`0x021A7B7C(side)`** —
   Fisher-Yates over `player+0x304`, count `player+0x10`, swapping via 0x021A1F9C.
2. It has 4 callers; the only in-duel one is `0x021C0C20`, inside the handler
   **`0x021C0BB4`**, which reads its arguments from `0x02299B60` — a *command*
   register, not a card.
3. `0x021C0BB4` is not in any pointer table and has exactly ONE `bl`, at
   `0x021C3F28` — inside an array of 6-byte `bl <handler> ; pop {r3,pc}` stubs.
4. That array is the **animation-command dispatcher** at `0x021C3C3C`:
   `op = [0x02299B60] & 0xFFF`, `cmp op,#0x68`, halfword table at 0x021C3C5E based
   at 0x021C3C60. Decoding it: **opcode 0x55 -> the deck shuffle.**
   (Also: 0x32 -> 0x021BF884 banish, 0x3E -> 0x021BC4B8 zone-to-zone relocate,
   0x52 -> 0x021C1BB0, 0x26 -> 0x021C3B70.)
   ⭐ This is also where a queued command finally becomes a STATE CHANGE — which
   explains why neither 0x021C6B00 nor 0x021C7118 nor 0x021D1300 contains an array write.
5. Clause 2 emits 0x3E and 0x26, never 0x55. So who does? Exactly two sites, and one
   of them is `0x021D26C2` — inside **`0x021D269C`**.

### ⚠️⚠️ `0x021D269C` IS `shuffle_deck(side)`

```
0x021D269C  r2 = [0x0229DD14 + 0x28]        ; the RNG state
            r1 = side ? 0x8000 : 0
0x021D26AE  r0 = 0x55 | r1                  ; the SHUFFLE opcode
            args = seed low, seed high      ; so a replay reproduces the permutation
0x021D26C2  bl 0x021C3BC8                   ; enqueue
```

It appears at the end of the native add-to-hand resolver 0x02207EF5 and of Gold
Sarcophagus 0x0221CD29 **because both of those SEARCH THE DECK**, where shuffling is
correct. That is how the 3DS mapping `0x388E3C -> 0x021D269C` (session 20) came to be
written down as "the completion phase 0x64", and the label then spread: it is
`COMPLETE` here and `EFFECT_DONE` in **patch_thunder_sea_horse**,
**patch_w_nebula_meteorite** and **patch_wonder_wand**. In those three the CALL is
correct (they are Deck searches) — only the NAME is wrong. Worth a look anyway if any
of them ever shuffles when it should not.

**FIXED**: `c2_fin` no longer calls it; the phase just returns 0. Recorder 304 -> 296 B.
`verify()` passes, `check_allocations` clean.

⚠️ Same failure mode as `0x021C72CC` (deck-only mover) and `0x021D1300` (wrong applier):
a primitive learned from a DECK-searching card, assumed general. That is now three
mislabels from the same source. When lifting a primitive out of a native resolver,
**check what zone that card actually touches.**

### Clause 2 status

| | |
|---|---|
| triggers on banish from GY | ✅ in-game |
| moves the exact remembered card banished -> hand | ✅ in-game |
| per-copy memory | ✅ in-game |
| no spurious deck shuffle | ✅ IN-GAME CONFIRMED 2026-08-13 (test 4: no shuffle, no regressions) |
| Yes/No prompt | ❌ needs the cls2 activation procedure (+0C/+10) |
| declines cleanly with nothing remembered | untested |
| diagnostics stripped | ❌ before shipping |

### Next

1. **Test the shuffle fix** (same recipe). Expect: card moves, nothing else happens.
2. Then the Yes/No — see `event.optional_trigger_is_record_shape` and the composition
   trap recorded there (one record, two clauses of different optionality; +0C/+10 must
   branch on desc[+3], and it is NOT yet proven that slot3/slot4 even see the zone).
3. Then strip diagnostics and re-run the whole chain.

## SESSION 28b — shuffle fix CONFIRMED; clause 2 made MANDATORY by user decision

**IN-GAME 2026-08-13 (test 4): no deck shuffle, no regressions.** Dropping the
`0x021D269C` call from `c2_fin` was the whole fix. Clause 2 now does exactly one
thing: move the remembered card from the banished zone to the hand.

### User decision: clause 2 is MANDATORY, and the card text says so

The printed card is "You can add". Making that real needs the cls record's ACTIVATION
PROCEDURE (+0x0C / +0x10, run by 0x02217F80) — nothing a resolver raises can do it.
Our donor carries BOTH clauses on ONE cls2 record and clause 1 is mandatory, so
optionality cannot be switched on there without regressing clause 1; it would need
+0C/+10 pointed at ov5 stubs that branch on desc[+3]. The user chose to change the
wording instead. Recorded so nobody "fixes" it later.

What the RE got to before that call (worth keeping — it is most of the way there):

* **`0x021F0820`, Botanical Girl's slot3, is a LEGALITY check, not optionality:**
  ```
  side = desc[+2] ^ desc[+6]
  if !0x021BAD70(side): return 0            ; cannot activate at all
  need = 1, except cid 0x1FC9 -> 3, 0x2049 -> 2, 0x2410 -> 3
  n = 0x02243FE0(side, desc[+0], 0x02234E78(desc))   ; candidate count
  return n >= need ? 1 : 0
  ```
  ⭐ Note it reads `desc[+2]`, `desc[+6]`, `desc[+0]` — **the same descriptor struct the
  resolver gets**, which answers the question flagged last session: a slot3 stub CAN
  branch on `desc[+3]`.
* **`0x021E51E4`, Botanical's slot4, is a thunk** whose `cmp r3,r2` compares two
  distinct constants (0x021E50DD vs 0x021E51E5) and so always tail-calls `0x021E50DC`.
* So optionality most likely comes from **having a slot4 at all** -> the activation
  state machine runs -> it offers the choice. ⚠️ NOT PROVEN, and Cyber Ouroboros is a
  counterexample to the simple version: it has slot4 = 0x021E5201 with no slot3.
  Anyone resuming this should classify the 0x021E5xxx tag space via the WHEN-vs-IF
  classifier 0x0224AF7C before building.

### Card text

⚠️ The description is written IN PLACE and the tool **silently skips a language** whose
slot is too small (it keeps Divine Dragon Ragnarok's original text). Both clauses fully
worded = 222 B and was skipped in every language on the first attempt. Final text is
120 B:

```
Sent to the GY: Banish 1 Lv7+ LIGHT or DARK Dragon from your Deck.
If banished from your GY: add that card to your hand.
```
Written for e/g/i/s/r; [f] 99 B, [j] 88 B and [k] 86 B still skip — the same three that
skipped with the clause-1-only text, so this is not a regression.

### Remaining before this ships

1. **Decline path, untested**: banish a Wyvern that never resolved clause 1 (or whose
   slot was already consumed) — `c2_ask` should call `0x0225BF30(1 - side)` and return
   0x78 without moving anything. Worth one deliberate test.
2. **Strip the diagnostics** at scratch +0x20..+0x2A from the wrapper (keep them for
   the decline test first — they are how it would be diagnosed).
3. Rebuild the full chain and re-run `verify()` on every patch.

## SESSION 28c — SHIPPED. Diagnostics stripped, both clauses live.

### What shipped

* PARTS A/B/C/D/E — clause 1 (sent to GY -> banish a Lv7+ Dragon from the Deck)
* PART I — the banish-from-GY event gate at 0x021C71C8 (ov3 stub 0x021B57F0, 20 B)
* PART H — the ov5 wrapper at CAVE_EW_RECORD: records clause 1's pick per copy, and
  carries clause 2's phase machine, reached on `desc[+3] == 0x0F`
* PART G — RETIRED (wrong applier); its second dead block 0x021B56B8 released
* Card text rewritten (120 B) to describe both clauses, mandatory wording

Recorder 316 -> 268 B with the diagnostics removed. Verified: **no residual writes
anywhere in the +0x20..+0x2A window**. The per-instance table at +0x00..+0x1F stays —
that is clause 2's input, not instrumentation.

⚠️ CAVE_EW_RECORD still reserves 0x160 (352 B) for a 268 B blob, and CAVE_EW_SCRATCH
stays at 0x0239C178. Left as-is deliberately: the addresses are baked into a tested
build and cave space is not scarce (~0x2980 B free). Do not "tidy" it without
re-testing.

### ⚠️ RESTORING THE DIAGNOSTICS

They are what solved every hard bug on this card (the BLX thumb-bit freeze, the
deck-only mover, the deck shuffle). To bring them back, re-add to `_recorder`'s head:
```
ldr  r2, =CAVE_EW_SCRATCH
ldrh r3, [r2, #0x20] ; adds r3,#1 ; strh r3,[r2,#0x20]   ; entries
strh r5, [r2, #0x22]                                     ; phase
ldrh r3, [r4, #0xc]  ; strh r3,[r2,#0x26]                ; acting ref
ldrb r3, [r4, #4]    ; strh r3,[r2,#0x28]                ; event code
```
plus `movs r3,#1 / #2 ; strh r3,[r2,#0x24]` around clause 1's capture block.
`scratch/read_ew_scratch.py` reads exactly that layout.

## KNOWN MISSING BEHAVIOUR (shipped deliberately — do not treat as newly found bugs)

### 1. Clause 2 is MANDATORY, not "You can"

The printed card is optional. Optionality is the cls record's ACTIVATION PROCEDURE
(slot3 +0x0C / slot4 +0x10, driven by 0x02217F80) — see
`event.optional_trigger_is_record_shape`. **One cls2 record serves both clauses and
clause 1 is mandatory**, so it cannot simply be switched on.

The route, if it is ever wanted: point +0C/+10 at ov5 stubs that branch on
`desc[+3]` (0x0E -> mandatory shape, 0x0F -> Botanical Girl's optional shape
`+0C = 0x021F0821, +10 = 0x021E51E5`). Feasible — slot3 provably receives the same
descriptor struct (0x021F0820 reads desc[+0]/[+2]/[+6]). **Blocked on**: decoding the
0x021E5xxx slot4 tag space (Cyber Ouroboros has slot4 with NO slot3 and is not
optional, so "slot4 present == optional" is too simple). Start at the WHEN-vs-IF
classifier 0x0224AF7C.

### 2. Clause 1 searches ANY Level 7+ Dragon, not just LIGHT/DARK

**IN-GAME OBSERVED 2026-08-13.** A criteria row carries exactly ONE attribute code
(`dispatch.criteria_word_race_attribute`), so "LIGHT **or** DARK" cannot be expressed
as data — our row leaves the attribute nibble 0 (= any). The 3DS build hits the same
wall and does the same thing, pushing the test into a bespoke handler.

The deviation is strictly WIDER than the real card, never narrower: every LIGHT/DARK
Dragon the real card can take is still takeable, plus some it should not (e.g. a
Level 7+ EARTH Dragon).

Fix, when wanted: the `patch_shiens_dojo` recipe — replace the criteria row's handler
with an ov5 callback that runs the native Level/race test then ANDs an attribute check
for LIGHT or DARK. Note that puts injected code on the criteria path, so confirm ov5
residency for every context that path runs in first.
