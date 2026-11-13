# Junk Speeder — findings

Live file. Everything below is verified **this session (2026-09-02)** unless
explicitly marked UNVERIFIED / inherited.

Card (`scratch/ygoprodeck_cache.json`, id **77075360**):
WIND / Warrior / Synchro / Effect, **Level 5**, ATK **1800** / DEF **1000**.

> 1 "Synchron" Tuner + 1+ non-Tuner monsters
> If this card is Synchro Summoned: You can Special Summon as many "Synchron"
> Tuners as possible with different Levels from your Deck, in Defense Position.
> You cannot Special Summon monsters from the Extra Deck, except Synchro
> Monsters, the turn you activate this effect. When an attack is declared
> involving this card that was Synchro Summoned this turn and another monster:
> You can make this card's ATK become double its original ATK until the end of
> this turn. You can only use each effect of "Junk Speeder" once per turn.

Not present in the 3DS build (user-stated) — no Konami second source. Every
mechanism must be built from NDS primitives.

## Clause split (awaiting user confirmation of scope)

1. **Materials**: 1 "Synchron" Tuner + 1+ non-Tuner monsters.
2. **On Synchro Summon**: SS as many "Synchron" Tuners as possible with
   *different Levels* from Deck, in **Defense Position**.
3. **Rider on clause 2**: cannot SS from the Extra Deck except Synchro Monsters
   that turn.
4. **Attack-declaration**: ATK becomes double original ATK until end of turn,
   only if this card was Synchro Summoned this turn and the attack involves
   another monster.
5. **HOPT**: each effect once per turn.

## Confirmed (this session)

- KB proofs green: `verify_knowledge` = 393 facts, **356 PASS / 0 FAIL / 37
  UNVERIFIED** (all UNVERIFIED are narrative, no address claims).
- `CAVE_FREE` = **0x0239DFB0**; free ov5 cave tail 0x0239DFB0..0x0239E120 =
  **0x170 (368) bytes** remaining. (ov5_cave.py:1107 — its comment quoting 464 B
  is stale relative to the sentinel; re-derive before claiming.)
- "Junk Speeder" does **not** exist in the ROM card text — needs a donor.
- The ROM ships many "Synchron" Tuners (Junk / Nitro / Turbo / Quickdraw /
  Road / Drill / Formula / Changer / Bri / Fleur / Hyper / Quillbolt-era set),
  so clause 2 has real targets.

## Ruled Out

(nothing yet)

## Open Questions

- Does a **"Synchron" archetype set-code** exist in the set-code thunk table
  (`0x0209D0D8`)? Clause 2's search predicate needs one, or a hardcoded cid list.
- Donor must be an **Extra-Deck Synchro** (Level 5 Warrior ideally). Extra-Deck
  donors are **never reached by cls2 dispatch** (KB: `otn-leave-trigger-cls2`),
  so clauses 2 and 4 need trampoline-style hooks, not cls2 records.
- Is there a native "Special Summon as many as possible / different Levels"
  multi-target deck-SS primitive, or must it be a loop in ov5?

## Next Experiment

Pending user's clause-scope decision.

---

# Clause 2 — scope locked 2026-09-02

User decision: **clause 2 only** this session (Deck SS of Synchron Tuners).
Clause 1 (Synchron-only materials) is **required, no deviation permitted**, but
deferred to its own session.

## Confirmed (clause-2 recon, this session)

### The "Synchron" archetype already exists — set code 0x4C
`setcode.synchron_table` (VERIFIED, proof re-run green this session as part of
the 393-fact sweep):
- has_set_code ptr table `0x0209D0D8` index **0x4C** -> thunk `0x02023E1D`
- sorted **15**-entry u16 cid array @ **0x0209C968**, count immediate
  `movs r2,#0x0F` @ `0x02023E20`
- Members: 0x0D6B Speed Spell - Deceased Synchron, 0x1E07 Junk Synchron,
  0x1E14 Nitro Synchron, 0x1E4E Synchro Deflector, 0x1EA1 Road Synchron,
  0x1EBE Turbo Synchron, 0x1F46 Hyper Synchron, 0x20F7 Quickdraw Synchron,
  0x21A7 Drill Synchron, 0x224C Changer Synchron, 0x229E Synchron Explorer,
  0x239E Formula Synchron, 0x23EE Fleur Synchron, 0x2414 Bri Synchron,
  + phantom 0x2501 (**already spent by patch_unknown_synchron** -> in the
  chained ROM that slot is Woodborg Inpachi 0x181C).
- ⚠️ Two members are NOT monsters (0x0D6B Speed Spell, 0x1E4E Synchro Deflector)
  and one is not a Tuner in the relevant sense (0x229E Synchron Explorer is a
  Tuner? UNVERIFIED). Clause 2 says "Synchron **Tuners**", so the search needs a
  Tuner test on top of set-code 0x4C.

### The trigger: "when this card is Synchro Summoned" is a DATA TABLE
`summon.trigger_is_a_membership_list` (VERIFIED):
- `0x02265768(event code)` is the summon-trigger evaluator; caller
  `0x0226878A` passes **9** (SPECIAL summon).
- The flag comes from nine sorted cid lists searched with the generic binary
  search `0x02022E14(value, table, count)`.
- **`0x0228F6C0` x 0x24 = the "code 9 + [0x02298A28+0x10] & 1" list = the
  "when Synchro / Fusion / Ritual Summoned" set.** Members named in the KB
  include Mist Wurm 0x1D7D, Locomotion R-Genex 0x2045, Trishula 0x221C,
  Vylon Alpha 0x24B1, Junk Warrior, Black Rose Dragon, Formula Synchron,
  Karakuri Burei.
- The event posts via register-prim `0x021D3168` with the selector
  **hard-coded to 1** (`movs r6,#2 ; lsls r6,r6,#0x14`), so a summon trigger
  can only dispatch to a **cls1** record.

### ⇒ cls1 DOES reach an Extra-Deck (Synchro) donor
Inference, not yet measured this session, but the evidence is strong: Junk
Warrior / Black Rose Dragon / Formula Synchron / Trishula are Extra-Deck Synchro
monsters whose native "when Synchro Summoned" effects work in the stock game,
and the only dispatch path for that event is cls1. This is the escape from
`otn-leave-trigger-cls2` ("cls2 dispatch NEVER reaches an Extra-Deck donor").
**Marked UNVERIFIED until I read the actual cls1 record of one of them.**

### A shared Deck-Special-Summon chassis exists
`counter.deck_ss_resolver` = **0x02206CAD** (the shared deck-SS resolver, slot
+04 of Shien's Footsoldier 0x1B3A's cls2 record). Its nine-way phase jump table
is at **0x02206CD2**, add-pc base `0x02206CD4`. Used by NAST
(patch_ninjitsu_art_super_transformation) — a shipped, in-game-confirmed
precedent for Special Summoning from the Deck.

## Open Questions (clause 2)

- Which Extra-Deck Synchro donor? Must be reachable, un-missed by the user, and
  ideally already a member of `0x0228F6C0` (so no count-neutral insert needed).
- Does the deck-SS chassis support **multiple** summons in one resolution, and
  can it be forced to **Defense Position**?
- How to express "as many as possible with **different Levels**"?

## Confirmed — the trigger list, profiled (2026-09-02)

`0x0228F6C0` x 0x24 dumped and cross-referenced against card_prop
(`carddata.card_prop_era2_bitfield`) and the four cls tables. **All 36 entries
are real cards — there is NO phantom in this list**, so a donor cannot be
*inserted*; it must already be a member. Every one of the 36 already owns a
cls1 record, so the patch **rewrites a record in place — no count change, no
phantom needed.**

Level-5 members: Junk Warrior 0x1E10 (DARK Warrior 2300/1300), X-Saber Wayne
0x1E9B (EARTH Warrior 2100/400), Fabled Ragin 0x20DF (LIGHT Fiend 2300/1800).
Members with GENERIC materials ("1 Tuner + N non-Tuner", no named rule):
Mist Wurm 0x1D7D, X-Saber Wayne 0x1E9B, Black Rose Dragon 0x1EDA,
Trishula 0x221C, Formula Synchron 0x239E. Ritual members (card_type 11) and
Fusion members (card_type 7) are unusable as a Synchro donor.

### *** THE TEMPLATE: Karakuri Burei 0x23A0 / Bureido 0x2475 ***
Printed text (ygoprodeck): "1 Tuner + 1 or more non-Tuner Machine-Type monsters
/ **When this card is Synchro Summoned: You can Special Summon 1 'Karakuri'
monster from your Deck.**" That is clause 2's exact shape, minus "as many as
possible / different Levels / Defense Position".

Their cls1 records (measured this session):
- `cls1[1255]` cid 0x23A0: s1=**0x02206CAD** s2=0 s3=**0x021F0419**
  s4=**0x021E51E5** s5=0
- `cls1[1309]` cid 0x2475: s1=**0x02206CAD** s2=0 s3=**0x021F0419**
  s4=**0x021E51E5** s5=0  (0x2475 owns TWO cls1 records, 1308 and 1309)

s1 = `counter.deck_ss_resolver` **0x02206CAD**, the SHARED deck-SS chassis (the
same one NAST ships on). It is used by **~95 records across all four cls
tables** — every "Special Summon 1 <filter> monster from your Deck" card in the
game (Giant Rat / Mystic Tomato / UFO Turtle family, Deep Sea Diva, Shien's
Footsoldier, Gravekeeper's Spy, Lonefire Blossom, ...). The `s3=0x021F0419 /
s4=0x021E51E5` pair is the common "optional trigger, no target declaration"
shape shared by dozens of them.

⇒ The donor needs NO new dispatch machinery for clause 2: rewrite the donor's
existing cls1 record to {s1=0x02206CAD, s3=0x021F0419, s4=0x021E51E5} and give
it a criteria row whose aux is the **Synchron set code 0x4C**.

## Ruled Out

- **Inserting a new cid into the Synchro-summon trigger list 0x0228F6C0** — no
  phantom slot exists (all 36 are real cards), so a count-neutral insert would
  have to delete a working card's trigger. The donor must be chosen from the 36.
- **A cls2 record for the trigger** — `summon.trigger_is_a_membership_list`
  proves the summon event's selector is hard-coded to 1 (`movs r6,#2 ; lsls
  r6,r6,#0x14`), so only cls1 is reachable from a summon trigger.
- **A second cls1 record on the donor** — `dispatch.second_cls1_record_is_
  spirit_only`: the `leftmost+1` offset requires `0x020230D4(cid) != 0`
  (card_type >> 1 == 7 = Spirit Monster). No Synchro donor qualifies.

## Confirmed — the deck-SS chassis is fully decoded and already reimplemented

`patch_ninjitsu_art_super_transformation.py:199-260` decoded the chassis
`0x02206CAC` halfword-by-halfword (2026-08-31) and its ov5 resolver
reimplements the default-arm path. Every native call clause 2 needs is named
there, in phase order:

| primitive | address | signature |
|---|---|---|
| free monster zones | `0x021AD870` | (side) -> n; 0 = cannot Special Summon |
| SS legality A / B | `0x021B9ECC` / `0x021B9ED8` | (side) |
| criteria param provider | `0x02234E78` | (desc) -> param |
| candidate count | `0x02243FA8` | (side, cid, param) -> n; CALLS THE ROW HANDLER |
| message | `0x0219A818` | (side, code) 0x0D "none" / 0x30 "choose" |
| list picker | `0x0219C430` | (side, mode=6, cid, param) |
| pick read-back | `0x0219C510` | () -> &0x02299458[[0x0229944C+4]] (POINTER) |
| **SS commit** | **`0x0226925C`** | **(side, &locator, face-up, POSITION, [sp]=cid<<16)** |
| **original Level** | **`0x0202ABD8`** | **(cid) -> Level** (ARM9, Thumb) |
| Deck walker | `0x0223BC3C` | the Deck container walker |

⇒ **Defense Position comes free** — it is the 4th argument of `0x0226925C`.
⇒ **"different Levels" comes free** — `0x0202ABD8(cid)` is the original Level.
⇒ "as many as possible" = loop until `0x021AD870(side)` is exhausted.

`summon.commit_r0_places_bit4_only_attributes` (VERIFIED) documents the same
commit: r0 = the side the card is PHYSICALLY placed on; the fifth argument's
bit 4 only writes the attribution field. Pass r0 = own side, low half zero.

## Confirmed — Daigusto Sphreeze 0x24B3 carries a per-cid gate
`0x0226D26C` is the 33-entry sorted "cannot be destroyed by battle" list
(`battle_attributes`, VERIFIED; sole search site `0x02197F0E`, count immediate
`movs r2,#0x21` read live at `0x02197F0C` = 0x2221). Dumped this session:
**0x24B3 Daigusto Sphreeze is entry [32], the LAST**. So a Sphreeze donor would
inherit battle-indestructibility unless the count immediate is decremented to
0x20 — a legal one-halfword fix precisely because it is last, but it is a real
gate and exactly the failure mode donor rule (c) exists to catch.

## Confirmed — donor evidence (all measured this session)

Name slots are **not** a constraint: `apply_stats_and_text`
(patch_boggart_knight.py:494-505) appends a too-long NAME to the blob and
repoints the index; only the DESCRIPTION is strictly in-place. So donor rule (b)
reduces to the desc slot alone.

Target description sizes (UTF-8, measured):
- FULL, all four printed clauses = **566 B** — fits NO English slot in the list.
- Variant B, clauses 1/2/4/5 condensed = **386 B**.
- Variant C, clauses 1/2/5 = **211 B**.

| donor | lvl/attr/race | EN desc | structures naming it | LIST_A | criteria row | notes |
|---|---|---|---|---|---|---|
| Fabled Ragin 0x20DF | 5 LIGHT Fiend | **176** | cls1[1055], summon list[11] — **fewest of all** | no | **none** | desc too small for even variant C; would need a criteria INSERT (phantom drop) |
| Reptilianne Hydra 0x211D | 6 DARK Reptile | 202 | cls1[1086], summon list[14] | no | none | desc < variant C |
| Locomotion R-Genex 0x2045 | 9 DARK Machine | 207 | cls1[1008], summon list[10] | no | none | desc < variant C |
| Laval Stannon 0x24B0 | 7 FIRE Pyro | 279 | cls1[1317], **cls3[773]**, crit[1366], summon list[32] | no | row 1366 aux 0x55 | extra cls3 record to neutralise |
| **Daigusto Sphreeze 0x24B3** | **6 WIND Psychic** | **325** | cls1[1320], crit[1369], summon list[35] | no | **row 1369** aux 0x5F | ⚠️ in the battle-indestructible list as the LAST entry |
| Dragunity Kt Vajrayana 0x2164 | 6 WIND Dragon | 360 | cls1[1106], **cls3[609]**, crit[1051], summon list[15] | no | row 1051 aux 0x4A | extra cls3 record |
| Tempest Magician 0x1F95 | 6 DARK Spellcaster | 372 | cls1[964], **cls3[494] + cls3[495]**, crit[840], summon list[7] | near 0x02275BDC | row 840 | also touches the LP-change table 0x02270AB0 |
| Blackwing Silverwind 0x211C | 8 DARK W.Beast | **419** | cls1[1085], summon list[13] | **YES 0x02275AE4** | none | only donor whose EN slot fits variant B; 14 bindings; its "2+ non-Tuners" LIST_A rule must be unwound |

### Fabled Ragin's per-cid literal, resolved
`ov3:0x02206598` = the u32 `0x000020DF`, a **literal-pool word** read by exactly
one site, `ldr r0,[pc,#0x1A0]` @ `0x022063F4`, inside the per-cid switch
`0x02206304` (the ungreppable base±imm shape of
`thumb-stack-based-switch-footgun`). `0x02206304` is a per-cid PARAMETER helper
("how many cards does this card draw"), called by the shared draw resolver
`0x022065B8` — which is Fabled Ragin's own cls1[1055] slot1. It has **5 BL
callers** (`0x021AB3D0`, `0x021F06A0`, `0x021F2810`, `0x022065C4`,
`0x0220CA4C`), so it is NOT reached only through the record we would replace.
Marked **ASSUMED-safe, not PROVEN** — moot unless Fabled Ragin is chosen.

### Daigusto Sphreeze 0x24B3 — the cleanest roomy donor
- criteria **row 1369** = {cid 0x24B3, aux **0x005F** (Gusto), handler
  `0x0223CBC9`, word `0x0001000E`} — **rewritable in place** to
  {aux 0x004C (Synchron), handler `0x0223CAB5` (Burei's Deck handler),
  word `0x00000002`}. **No insert, no phantom drop, no count change.**
- cls1**[1320]** = {s1 0x02208181, s2 0, s3 0x021F05A9, s4 0x021E51E5,
  s5 0x02235605} — rewritable in place to Burei's shape
  {s1 = our ov5 resolver, s2 0, s3 0x021F0419, s4 0x021E51E5, s5 0}.
- NOT in LIST_A ⇒ no exact-count material rule to unwind.
- ⚠️ **the one gate**: entry [32] (last) of the battle-indestructible list
  `0x0226D26C`. Fix = `movs r2,#0x21` -> `movs r2,#0x20` at `0x02197F0C`
  (read live this session as 0x2221). Legal precisely because it is last.

## Open Questions

- **Donor choice is the user's call** (which Extra-Deck card they can lose).
- Does slot3 `0x021F0419` consult the criteria row for its activation gate?
  If yes the criteria row must be correct for the prompt to appear at all.
- Is there a **Tuner** bit in the criteria word? Set code 0x4C alone also
  matches Synchron Explorer 0x229E (the only non-Tuner Main-Deck Synchron),
  plus the Spell 0x0D6B and Trap 0x1E4E (excluded by the word's MONSTER mask).
  A custom ov5 resolver can apply its own Tuner test regardless.

---

# Donor APPROVED by user 2026-09-02: Daigusto Sphreeze 0x24B3
Text scope approved: **variant C** (clauses 1/2/5, 211 B) — fits the 325 B
English slot.

## Confirmed — slot3 0x021F0419 GATES ON THE CRITERIA ROW (disassembled this session)

```
0x021F0418  push {r3,r4,r5,lr}
0x021F041A  adds r4,r0,#0          ; r4 = descriptor
0x021F041C  ldrb r3,[r4,#2]        ; side
0x021F041E  ldrb r2,[r4,#6]
0x021F0420  adds r5,r3,#0
0x021F0422  eors r5,r2             ; r5 = effective side
0x021F0424  bl   0x021F0384        ; PRE-GATE -> 0 means "cannot activate"
0x021F0428  cmp  r0,#0
0x021F042A  bne  0x021F0430
0x021F042C  movs r0,#0             ;   ... return 0
0x021F0430  adds r0,r4,#0
0x021F0432  bl   0x02234E78        ; PARAM_PROVIDER(desc) -> criteria param
0x021F0436  adds r2,r0,#0
0x021F0438  ldrh r1,[r4]           ; r1 = cid
0x021F043A  adds r0,r5,#0          ; r0 = side
0x021F043C  bl   0x02243FE0        ; CRITERIA CANDIDATE LOOKUP
0x021F0440  cmp  r0,#0
0x021F0442  beq  0x021F0448
0x021F0444  movs r0,#1             ; >=1 candidate -> ACTIVATABLE
0x021F0448  movs r0,#0             ; none -> not activatable
```
**⇒ the criteria row is load-bearing for the PROMPT, not just the search.** If
row 1369 is wrong the effect never even offers. This is PROVEN by disassembly,
and it is the single most important structural fact for clause 2.

## Confirmed — criteria handler 0x0223CAB5 is the DECK handler

```
0x0223CAB4  push {r1,r2,r3,lr}
0x0223CAB6  adds  r2,r0,#0         ; r2 = the criteria ROW
0x0223CAB8  movs  r0,#2
0x0223CABA  ldrsh r0,[r2,r0]       ; row[+2] = AUX (read SIGNED -> 0xFFFF = -1 = "no set code")
0x0223CABE  str   r0,[sp,#8]
0x0223CAC0  ldr   r0,[r2,#8]       ; row[+8] = WORD
0x0223CAC2  str   r0,[sp]
0x0223CAC4  movs  r0,#0xA
0x0223CAC6  str   r0,[sp,#4]       ; mode 0x0A  (the "to the field" form)
0x0223CAC8  adds  r0,r1,#0         ; side
0x0223CACA  ldrh  r1,[r2]          ; row cid
0x0223CACC  ldr   r2,[pc,#4]
0x0223CACE  bl    0x0223BC3C       ; the container walker (NAST's DECK_WALKER)
```
Note the AUX is read with **LDRSH** — 0xFFFF is the sentinel -1 = "no set-code
filter", which is why Giant Rat / Deep Sea Diva carry aux 0xFFFF and encode
their filter in the word instead.

⚠️ `[sp+4]` is **NOT** the zone: the sibling handler `0x0223CAF5` (Tuning
0x23A2, which also searches the **Deck**, to the hand) passes 2 there while
0x0223CAB5 passes 0x0A. Both read the Deck, so 0x0A/2 is a MODE (destination /
"must be summonable"), not a container id. **Marked ASSUMED, not PROVEN.**
Mitigation: the patch copies Burei's row verbatim except the aux, so the mode is
inherited from a working card rather than reasoned about.

Empirical zone proof (donor rule 2, "the exact zone the effect searches"):
handler 0x0223CAB5 is shared by Gravekeeper's Spy 0x1585, Shien's Footsoldier
0x1B3A, XX-Saber Emmersblade 0x2231, Gusto Gulldo 0x23CC and Karakuri Burei
0x23A0 / Bureido 0x2475 — **every one of whose printed text says "from your
Deck"**. Distinct from the HAND handler 0x0223CB19
(`tool.threeds_hand_handler_equivalence`, == 3DS 0x004ABE08).

## Confirmed — ov5 cave budget
`ov5_cave.py:1107` `CAVE_FREE = 0x0239DFB0`; region end `OV5_END = 0x0239E120`
(env.py). Free tail = **0x170 = 368 bytes**. ⚠️ The comment on line 1109 claims
0x1D0 = 464 B "as of 2026-09-01" — that is **stale**; the sentinel is
authoritative and gives 368. Last claimed slot is
`CAVE_UNKSYN_STAMP = 0x0239DF70`.

## *** CONFIRMED — THE SUMMON-POSITION ENCODING, FULLY DECODED (2026-09-02) ***

The deck-SS chassis's phase-0x7C arm `0x02206E62` builds the `0x0226925C` call.
Signature confirmed against `summon.commit_r0_places_bit4_only_attributes`:

```
SS_COMMIT(r0 = side, r1 = &locator, r2 = face_up, r3 = position,
          [sp] = (cid << 16) | flags)
```

How the chassis chooses `face_up` / `position`:

```
0x02206E62  movs r0,#1 ; str r0,[sp,#4]   ; face_up = 1        (DEFAULT)
0x02206E6C  movs r7,#2                    ; position = 2       (DEFAULT)
0x02206E6E  movs r6,#0                    ; flags = 0          (DEFAULT)
0x02206E70  bl 0x02022E14                 ; binary-search cid in a 16-entry list
0x02206E78  adds r7,r6,#0                 ;   FOUND -> position = 0
            <per-cid switch on the cid>
0x02206EBE    movs r6,#1                  ;   flags = 1
0x02206EC2    movs r0,#0 ; str r0,[sp,#4] ;   face_up = 0, falls through to:
0x02206EC8    movs r7,#1                  ;   position = 1
```

The 16-entry position-override list is at **`0x022701EC`** (pointer literal
`0x02206F2C`): 0x0E9B, Giant Rat 0x1333, UFO Turtle 0x1335, Shining Angel
0x133C, Mother Grizzly 0x133E, Flying Kamakiri #1 0x133F, Mystic Tomato 0x1342,
UFOroid 0x18F4, Warrior Lady 0x1939, Damage Condenser 0x19B6, Reverse of Neos
0x1BFB, Mind Master 0x1E22, Genex Searcher 0x1E82, Assault Mode Activate 0x1F7A,
Naturia Cliff 0x2034, Karakuri Nisamu 0x2388.

**THE ENCODING, PROVEN BY THREE CARDS WHOSE PRINTED TEXT NAMES THE POSITION:**

| face_up | position | meaning | proof card |
|---|---|---|---|
| 1 | **0** | face-up **Attack** | Giant Rat 0x1333 — in the 16-list; prints "in face-up Attack Position" |
| 1 | **1** | face-up **Defense** | **Phantom Magician 0x2361** — switch arm 0x02206EC8; prints "in face-up Defense Position" |
| 0 | **1** | face-down Defense | **Bubonic Vermin 0x136A** and **Super-Nimble Mega Hamster 0x2233** — switch arm 0x02206EC2; both print "in face-down Defense Position" |
| 1 | 2 | the DEFAULT (position unspecified on the card) | Gravekeeper's Spy, Burei, Shien's Footsoldier, Deep Sea Diva |

⇒ **Junk Speeder clause 2's "in Defense Position" is `face_up = 1, position = 1`**
— exactly Phantom Magician's leaf. This is a closed structural proof: the
per-cid switch arms partition precisely along the printed position wording of
the cards that reach them.

Chassis teardown for reference: phase 0x78 = `0x021D269C(side)` then returns
**0x64** (stop). NAST needed 1 instead because it attaches a phase-1 rider;
**Junk Speeder has no rider, so 0x64 is correct here.**

## Open Questions (narrowed)

- **How to read the CID of candidate *i*** out of the locator array
  `0x02299458` (stride 4; `0x0219C510` returns `&0x02299458[[0x0229944C+4]]`).
  Needed for the "different Levels" test. Two routes to evaluate:
  (a) find a "cid at locator" accessor; (b) avoid it entirely by re-running the
  criteria search once per Level with a level-filtered word, taking candidate 0
  each time — needs the criteria word's Level encoding.

## *** CONFIRMED — NEW ENGINE FACT: CRITERIA-WORD BIT 15 (0x8000) IS "IS A TUNER" ***

`dispatch.criteria_word_fully_decoded` lists bit 15 only as
"`0x02023110(cid) == 1`" — undecoded. Decoded this session:

```
0x02023110  push {r3,lr}
0x02023112  bl   0x0202ABF8       ; -> card_type >> 1
0x02023116  subs r0,#0x0F
0x02023118  cmp  r0,#5
0x0202311A  bhi  0x02023132       ; outside 15..20 -> return 0
0x0202311E  add  r0,pc            ; byte jump table @0x02023128
0x02023120  ldrb r0,[r0,#6]
0x02023126  add  pc,r0            ; base 0x0202312A
0x0202312E  movs r0,#1 ; pop      ; YES
0x02023132  movs r0,#0 ; pop      ; NO
```
Jump-table bytes @`0x02023128` = `04 04 08 08 04 04`:

| idx | `0x0202ABF8` | card_type | arm | result |
|---|---|---|---|---|
| 0 | 15 | 31 **Normal Tuner** | 0x0202312E | **1** |
| 1 | 16 | 33 **Tuner (effect)** | 0x0202312E | **1** |
| 2 | 17 | 35 Synchro (no effect) | 0x02023132 | 0 |
| 3 | 18 | 37 Synchro Effect | 0x02023132 | 0 |
| 4 | 19 | 39 **Synchro Tuner Effect** | 0x0202312E | **1** |
| 5 | 20 | 41 (unused) | 0x0202312E | 1 |

The set {31, 33, 39} is **exactly** `game_constants.ERA2_CARD_TYPE_MAP`'s three
Tuner types, and the two rejected are exactly the two non-Tuner Synchro types.
`0x0202ABF8` returns `card_type >> 1` (corroborated by
`dispatch.second_cls1_record_is_spirit_only`, which uses the same accessor for
"Spirit" == 7).

**INDEPENDENT CROSS-VALIDATION FROM A SHIPPED ROW:** Tuning `0x23A2` owns
criteria row 1269 = `{aux 0x004C, handler 0x0223CAF5, word 0x00008002}` and its
printed text is *"Add 1 **'Synchron' Tuner monster** from your Deck to your
hand."* aux 0x4C = Synchron, bit 15 = Tuner, bit 1 = real card. Necro Linker
0x237A carries the same 0x8002 low half with aux 0x4C.

⇒ **Clause 2's filter needs NO deviation and NO custom predicate.** It is
Tuning's word plus a Level field:
```
aux  = 0x004C                                   ; "Synchron"
word = ((k << 2) << 16) | 0x8002                ; Level EXACTLY k, Tuner, real card
handler = 0x0223CAB5                            ; the DECK -> FIELD handler
```
using `dispatch.criteria_word_level_field` (VERIFIED): level byte =
[op:2 @7:6][level:4 @5:2], **op 0 = "Level N exactly"**.

This also removes the last deviation risk: Synchron Explorer 0x229E, the only
non-Tuner Main-Deck "Synchron" monster, is correctly excluded by bit 15.

## Architecture — clause 2, FINAL

Donor Daigusto Sphreeze 0x24B3, all edits IN PLACE (no inserts, no phantoms):

- **card_prop**: Lv6 WIND Psychic 2000/1300 -> **Lv5 WIND Warrior 1800/1000**,
  card_type stays 37 (Synchro Effect).
- **cls1[1320]**: {s1 0x02208181, s2 0, s3 0x021F05A9, s4 0x021E51E5,
  s5 0x02235605} -> {s1 = **CAVE_JS_RES**, s2 0, s3 **0x021F0419**,
  s4 **0x021E51E5**, s5 **0**} (Karakuri Burei's shape).
- **criteria row 1369**: {aux 0x005F, handler 0x0223CBC9, word 0x0001000E} ->
  {aux **0x004C**, handler **CAVE_JS_CRIT**, word **0x00008002**}.
- **battle-indestructible list**: `movs r2,#0x21` -> `movs r2,#0x20` at
  `0x02197F0C`, dropping 0x24B3 (the last entry).
- **ov5 CAVE_JS_CRIT**: a clone of `0x0223CAB4` that takes its WORD from
  **CAVE_JS_WORD** instead of row[+8], so the Level field can vary per
  iteration without ever mutating the ov3 table (NAST's proven pattern).
- **ov5 CAVE_JS_RES**: the phase machine. Phase 0x80 = the three SS legality
  gates + a candidate probe; phase 0x7E = **the loop over Levels 1..12**, each
  iteration setting CAVE_JS_WORD, re-running `0x02243FA8`, and on a hit calling
  `0x0226925C(side, &locator, face_up=1, position=1, (cid<<16))`; phase 0x7B =
  no-candidate cleanup; phase 0x78 = teardown, return **0x64** (no rider).
  No picker is opened — "as many as possible" involves no player choice.

## Out of scope this session (recorded, NOT implemented)
- Clause 1 (Synchron-only materials) — user requires it, deferred, no deviation.
- Clause 3 (Extra-Deck lock the turn you use this effect).
- Clause 4 (double original ATK on attack declaration).
- Clause 5 (once per turn per effect). **Pre-build checklist item 4 = NOT
  STAMPED.** Low practical risk for clause 2 because the trigger requires a
  fresh Synchro Summon of this card, but it is a known gap, not a deviation.

---

# BUILD COMPLETE — 2026-09-02.  STATUS: **AWAITING IN-GAME TEST**

`.venv-1/Scripts/python.exe _build_junk_speeder.py` ->
`data/over_the_nexus/working/rom_junk_speeder.nds`.
`verify()` = **12/12 PASS**.  NOT wired into `apply_all_patches` (CLAUDE.md:
no chain build while a card is being debugged).

Files: `otn_enhanced/cards/junk_speeder.py`,
`_build_junk_speeder.py`, cave claims in `ov5_cave.py`.

## What the build actually wrote

| part | address | before | after |
|---|---|---|---|
| A cls1[1320] | `0x0228DC94` | `02208181 00000000 021F05A9 021E51E5 02235605` | `0239E001 00000000 021F0419 021E51E5 00000000` |
| B criteria[1369] | `0x022753F0` | aux `0x005F` hnd `0x0223CBC9` word `0x0001000E` | aux `0x004C` hnd `0x0239DFC1` word `0x00008002` |
| C battle list count | `0x02197F0C` | `0x2221` (`movs r2,#0x21`) | `0x2220` (`movs r2,#0x20`) |
| D data words | `0x0239DFB0` | — | 16 B |
| D criteria handler | `0x0239DFC0` | — | 56 B, Thumb-1 |
| D resolver | `0x0239E000` | — | 268 B, Thumb-1 |
| E card_prop | — | Lv6 WIND Psychic 2000/1300 | **Lv5 WIND Warrior 1800/1000**, card_type 37 |

Text: name in place in all 8 languages (Korean appended + repointed, its slot was
empty); description in place in 7 of 8 at 211/325 B English. **Korean desc
SKIPPED** — its slot is 0 B, so the donor text is kept. Expected, not a fault.

⚠️ **THE ov5 CAVE IS NOW FULL.** `CAVE_FREE` = `0x0239E120` = `OV5_END`. This
patch took the last 0x150 bytes. `check_allocations` = 163 ov5 slots, no
overlaps, ledger in sync. A further stub needs a freed slot or a different host.

## KB contributions (all three PASS their proofs; `verify_knowledge` 0 FAIL)
- `dispatch.criteria_word_bit15_is_tuner` (VERIFIED, `0x02023110`, arm9)
- `summon.commit_position_encoding` (VERIFIED, `0x02206E62`, ov3)
- `summon.synchro_trigger_list_has_no_phantom` (VERIFIED, `0x0228F6C0`, ov3)

## Next Experiment — the in-game test (the ONLY thing that can confirm this)

The nine numbered checks are in `_build_junk_speeder.py`'s docstring. The two
that discriminate between failure modes:
- **No Yes/No prompt on the Synchro Summon** ⇒ the fault is the activation gate
  `0x021F0419` -> criteria row (PART B), NOT the resolver. `0x021F0419` returns 1
  only if `0x02243FE0` finds >= 1 candidate, so an empty/incorrect row silently
  suppresses the whole effect.
- **Prompt appears, nothing is summoned** ⇒ the fault is in the ov5 resolver's
  phase 0x7E loop or in the ov5 criteria handler, not in dispatch.
If it freezes on activation, suspect the criteria-handler clone's r3-by-reference
aux cell (`CAVE_JSP_DATA+4`) — that is the one place this patch deviates
structurally from the stock handler `0x0223CAB4`.

---

# IN-GAME TEST 1 — 2026-09-02.  PARTIAL PASS, one clear bug.

User's exact words:
> "Okay - I summoned junk speeder, and activated it's effect. But it only
> specials summoned 1 monster from my deck instead of up to 4"

Plus, on request: (1) the monster was in FACE-UP DEFENSE POSITION, (2) it was
**Quickdraw Synchron, Level 5**, (3) the Deck held Synchrons of Levels 1-5,
(4) there were **4 empty monster zones**.

## Confirmed IN-GAME (user-reported, 2026-09-02)

- The Synchro-Summon trigger FIRES on the donor and the Yes/No prompt appears
  ⇒ PART A (cls1 rewrite) + `0x021F0419`'s criteria gate + PART B (criteria row)
  are all correct, and **cls1 dispatch does reach an Extra-Deck donor**.
- The Deck search finds "Synchron" Tuners ⇒ aux 0x4C + word bit 15 (Tuner) +
  the ov5 criteria-handler clone all work.
- **The summon is in FACE-UP DEFENSE POSITION** ⇒ `summon.commit_position_encoding`
  (face_up=1, position=1, Phantom Magician's leaf) is **IN-GAME CONFIRMED**.
- ⇒ the ONLY failure is multiplicity: one summon instead of one per Level.

## Confirmed — savestate read (rom_junk_speeder.ml3, the post-resolution state)

⚠️ The files are `.ml1/.ml2/.ml3`, not the `.ml2/.ml3/.ml4` named in the report,
and their timestamps run ml1 (10:42) -> ml3 (10:44) -> ml2 (10:46). `.ml1` has no
live duel. `.ml2` and `.ml3` are DIFFERENT boards (side 1 holds Hyena in one,
Beast Striker + Moja in the other), so they cannot be diffed against each other.
**`.ml3` is the state that matters** and it is unambiguous:

- side 0 zones: z2 = 0x24B3 (Junk Speeder), z3 = 0x20F7 Quickdraw Synchron.
  z0, z1, z4 empty — so **three zones were still free**; the zone check is NOT
  the limiter.
- summon descriptor `0x02298A28`: side 0, zone 3, **srczone 0x0D (= DECK)**,
  cid 0x20F7 Quickdraw Synchron, flags 0x0004, **cid2 0x24B3** (Junk Speeder as
  the summoning card). Exactly one summon recorded.
- **`CAVE_JSP_DATA+0` = `0x00308002` ⇒ Level field k = 12.**
- `CAVE_JSP_DATA+4` = `0x0000004C` ⇒ the ov5 criteria handler ran.

### *** THE LOOP RAN TO COMPLETION. ***
k = 12 is the value the LAST iteration writes. So all twelve iterations
executed, the zone check never broke out, and the criteria search ran twelve
times — and yet exactly ONE monster is on the field, the one from the HIGHEST
matching Level (5 = Quickdraw; Levels 6-12 have no Synchron Tuners).

"Loop completed, last successful iteration is the one that survives" is the
signature of the twelve `0x0226925C` calls **not each placing a card**. The
leading hypothesis is that `0x0226925C` populates the SINGLE GLOBAL summon
descriptor `0x02298A28` and the actual placement is driven from it once, after
the resolver returns — so twelve calls overwrite one slot and the last wins.
**NOT YET PROVEN — this is hypothesis 1 of the two-strike budget.**

## Ruled Out (by this savestate)

- Early loop exit (zone-full break, counter not advancing): **k reached 12**.
- The criteria handler not being reached: aux cell holds 0x4C.
- The per-Level word not being written: the word carries a Level field.
- A wrong summon position: face-up Defense confirmed in-game.
- Too few free zones: three were still empty after the single summon.

## Next Experiment
Disassemble `0x0226925C` to establish whether it WRITES the monster-zone record
(`player + 0x34 + zone*0x14`) itself — immediate placement — or only fills the
descriptor. Then find the native precedent for placing SEVERAL monsters in one
resolution (Scapegoat's 4 tokens / Ojama Trio's 3) and copy its sequencing.

## *** ROOT CAUSE — PROVEN 2026-09-02 (savestate emulation, not inference) ***

### Step 1: every Level's search WORKS.
Ran `0x02243FA8(side=0, cid=0x24B3, param=0)` under `scratch/thumbemu.py` over
`rom_junk_speeder.ml3`'s real RAM, rewriting `CAVE_JSP_DATA+0` per Level.
(`param` is safe to pass as 0: this handler family does `adds r2,r0,#0` as its
third instruction, discarding it.)

| k | word | count | locator[0] |
|---|---|---|---|
| — | 0x00008002 | 14 | Turbo Synchron |
| 1 | 0x00048002 | **4** | Turbo Synchron |
| 2 | 0x00088002 | **2** | Fleur Synchron |
| 3 | 0x000C8002 | **3** | Junk Synchron |
| 4 | 0x00108002 | **3** | Bri Synchron |
| 5 | 0x00148002 | **2** | Quickdraw Synchron |
| 6..12 | — | 0 | (array unchanged) |

⇒ the Level filter, the Tuner bit, the aux set code and the ov5 criteria handler
are all **correct**, and `0x02243FA8` **does populate** the locator array at
`0x02299458` (it is NOT picker-only, which had been an open question).
So the resolver had a valid, distinct candidate at Levels 1, 2, 3, 4 and 5 and
called `0x0226925C` for each.

### Step 2: `0x0226925C` DOES NOT PLACE THE CARD.
Emulated two consecutive commits over the same board, exactly as the loop does:

```
initial          zones: z0:- z1:- z2:0x24B3 JunkSpeeder z3:0x20F7 Quickdraw z4:-
call 1  Level 1 -> locator[0] = Turbo Synchron 0x1EBE
        0x021AD8C4(0) -> first free zone = 1
        0x0226925C returned 1
        descriptor cid = 0x1EBE Turbo Synchron
        zones UNCHANGED
call 2  Level 2 -> locator[0] = Fleur Synchron 0x23EE
        0x021AD8C4(0) -> first free zone = 1     <-- STILL 1
        0x0226925C returned 1
        descriptor cid = 0x23EE Fleur Synchron   <-- OVERWROTE call 1
        zones UNCHANGED
```

**`0x0226925C` fills the single global summon descriptor `0x02298A28` and
returns; the physical placement is DEFERRED.** The proof that it is deferred and
not merely emulator-invisible is `0x021AD8C4`: that function
(`for z in zone_code_table[0x0226DF18] = {2,3,1,4,0}: if zone free return z;
return -1`) returns **zone 1 on both calls**. If call 1 had placed a card, call 2
would have been handed a different zone. Nothing moved, so every call targets the
same slot and **the last write wins** — which is exactly why the ONE monster that
appeared was Quickdraw Synchron, the highest matching Level (5), i.e. the LAST
iteration with a hit.

### Step 3: there is NO native precedent for multi-summon in one phase.
Scapegoat 0x12D2 (cls0[152]), Ojama Trio 0x166A (cls0[455]) and Dandylion 0x19FE
(cls2[203]) all share slot1 = **0x02207A09**, the TOKEN summoner — a different
path that does not go through `0x0226925C`. No card in the pool Special Summons
several real cards from the Deck in a single resolution, which is why the shared
chassis `0x02206CAD` commits exactly once and then returns 0x78.

## Ruled Out (added)
- "0x02243FA8 only counts; the locator array is populated by the picker
  0x0219C430" — **false**, measured: the array is rewritten by the count call.
- "The loop exited early" — k reached 12.
- "Too few free zones" — `0x021AD8C4` returns a free zone on every call.

## Next Experiment
The fix must give the engine a step between summons instead of looping inside one
phase. The phase machine already offers that: NAST's decode of the driver
(0x02218042) says it **stores any NONZERO return as the next phase and
re-enters**. So phase 0x7E should do ONE summon and return 0x7E again, with the
Level counter held in a cave cell, until the Levels are exhausted -> 0x78.
**VERIFY FIRST** that a repeated phase return really re-enters and that the
deferred placement runs between re-entries — that is hypothesis 2 of the
two-strike budget, and it must be read out of the driver, not assumed.

## Confirmed — the invoke site IS a step machine (hypothesis 2, read not assumed)

Disassembled `0x02218032..0x0221804C`:
```
0x02218034  ldrh r1,[r4,#0x18]      ; the stored phase
0x02218038  str  r1,[r0,#0x70]      ; publish to [0x0229AAFC+0x70]
0x0221803E  bl   0x0224AEB8         ; invoke slot1 ONCE
0x02218042  strh r0,[r4,#0x18]      ; store the RETURNED phase
0x02218046  cmp  r0,#0
0x02218048  beq  -> movs r0,#0x0A   ; 0 = the resolution is FINISHED
0x0221804A  movs r0,#0x64           ; nonzero = "call me again"
0x0221804C  b    -> return
```
It calls the resolver **once and returns**; it does not loop. A nonzero phase
ends the step with 0x64 and the outer state machine re-invokes later — and that
gap is where the deferred placement runs. This also retro-explains the chassis's
0x64: that value is just a phase no arm handles, so the next invocation returns
0 and the driver reports 0x0A = done.

## ROUND 2 FIX — built 2026-09-02, AWAITING IN-GAME TEST

Phase 0x7E no longer loops. It does **one summon per invocation and returns
0x7E to be re-entered**, with the Level counter in a new cave cell
`LEVEL_CELL = CAVE_JSP_DATA + 8` (the counter cannot be a register — it has to
survive between phase invocations). Phase 0x80 initialises it to 1.

Order of operations per entry: read k; **advance the counter immediately** (so
every exit path progresses and it cannot spin); stop if k > 12 or the zones are
full; publish the Level word; search; if a candidate exists, summon it face-up
in Defence; return 0x7E. Bounded at MAX_LEVEL + 1 = 13 re-entries.

Side effect worth noting: the free-zone check is now **meaningful**. In round 1
the zones never changed mid-loop so it could never fire; now it stops the effect
exactly when the field fills, which is what "as many as possible" means.

Resolver grew 268 -> **284 B**, still inside its 0x120 reserve. `verify()` 12/12
PASS. Disassembled and checked: `ph80ok` sets LEVEL_CELL=1 and returns 0x7E;
`ph7e` at 0x0239E08A does `ldr r4,[LEVEL_CELL] ; cmp r4,#0xC ; bgt done`, stores
k+1, and both the summon path and the empty-Level path fall into
`movs r0,#0x7E`; `pop {r3,r4,r5,r6,r7,pc}` (correct POP form).

### Predicted result for the SAME board as test 1
Junk Speeder occupies one zone, leaving **4 free**, and the Deck holds Synchron
Tuners at Levels 1,2,3,4,5 (measured: counts 4/2/3/3/2). The loop ascends, so
expect **4 monsters — one each of Levels 1, 2, 3 and 4 — all face-up Defence**,
with Level 5 refused for lack of a zone.
⚠️ **DEVIATION TO CONFIRM WITH THE USER:** the printed card says "as many as
possible" without saying WHICH, so when the zones cannot hold every distinct
Level the choice of *which* Levels is the implementation's. This build picks the
LOWEST Levels (ascending sweep). Descending, or a player prompt, are the
alternatives.

---

# IN-GAME TEST 2 — 2026-09-02.  Round-2 fix CONFIRMED.

User's exact words:
> "Better... However I didn't get to choose which monsters to summon at each level..."

On request: **4 monsters arrived, all face-up defense, in order 1, 2, 3, 4** —
exactly the prediction. So the phase-re-entry fix is **IN-GAME CONFIRMED**:
one summon per re-entry, correct Levels, correct position, and the free-zone
check correctly refused Level 5 with the field full.

Remaining fault: where a Level has several eligible Tuners (the Deck held Turbo
x3 + Changer at Lv1, Junk x2 + Drill at Lv3, ...) the resolver took candidate 0
instead of prompting. User's decision: **prompt at EVERY Level, even when only
one card qualifies.**

## *** BUG CAUGHT BEFORE SHIPPING — the stale criteria word ***

Disassembled both lookups: `0x02243FA8` (resolver) and **`0x02243FE0` (the
activation gate slot3 0x021F0419 calls)** BOTH go through `0x02243B9C` -> the
row's handler. Our handler reads its word from `CAVE_JSP_DATA+0`.

⇒ after a resolution that cell held the **Level-12** word `0x00308002`, so the
NEXT Junk Speeder activation in the same duel would be tested as "Level exactly
12 Synchron Tuner", find nothing, and **never be offered**. Not yet observed
in-game only because both tests summoned a single copy.

FIX: phase 0x78 (teardown) restores `CAVE_JSP_DATA+0` to `BASE_CRIT_WORD`
(0x00008002). Every path that writes a Level word goes through 0x78; the
"cannot Special Summon" path never writes one. Verified by inspection of all
exit paths.

# ROUND 3 — built 2026-09-02, AWAITING IN-GAME TEST

Phase machine now runs the chassis's OWN prompt cycle once per Level:

| phase | does |
|---|---|
| 0x80 | three SS legality gates; LEVEL_CELL = 1; -> 0x7F |
| 0x7F | advance to the next Level WITH candidates (searching loops safely inside one phase — it summons nothing); stop at MAX_LEVEL or when zones fill; message 0x30 "choose"; -> 0x7E |
| 0x7E | `0x0219C430(side, 6, cid, param)` opens the picker; -> 0x7C |
| 0x7C | `0x0219C510()` -> &LOCATOR[picked]; `0x0226925C(side, loc, 1, 1, cid<<16)`; LEVEL_CELL += 1; -> 0x7F |
| 0x78 | restore CAVE_DATA; `0x021D269C(side)` teardown; -> 0x64 stop |

**Dead code removed:** the phase-0x80 candidate probe, its 0x0D "there is none"
message and the whole 0x7B cleanup arm. They were unreachable — slot3 has
already run the identical criteria lookup, so the effect cannot be activated
unless the Deck holds at least one "Synchron" Tuner. (This is also what paid for
the picker's bytes.)

Resolver 284 B of its 0x120 reserve — **4 bytes spare**. `verify()` 12/12 PASS.
Disassembled: dispatch covers 0x78/0x80/0x7F/0x7E/0x7C; the 0x7F empty-Level
loop branches back to its counter re-read; `pop {r3,r4,r5,r6,r7,pc}`.

⚠️ **THE CAVE IS THE BINDING CONSTRAINT NOW.** 4 bytes spare, and
`CAVE_FREE == OV5_END`. Clauses 1/3/4/5 cannot be built until the approved
64 KB enlargement lands (notes/ov5-cave-capacity-findings.md).

## Next Experiment (in-game, round 3)
Same board. Expect a "choose a card" prompt at **each** of Levels 1, 2, 3, 4 —
four prompts, four summons, all face-up Defence, stopping when the zones fill.
Then, the regression this round is really about: **Synchro Summon a SECOND Junk
Speeder in the same duel and confirm its effect is still OFFERED** (that is the
stale-word fix; before it, the second copy would silently not prompt).

---

# IN-GAME TEST 3 — CLAUSE 2 **IN-GAME CONFIRMED BY USER 2026-09-02**

User's exact words:
> "I can confirm I got a prompt for every synchron summon. levels 1,2,3,4. All
> good on this front.
>
> The effect is offered a second time. Extend ov5_cave then. and proceed"

Both round-3 test points PASS:
- **A** — a "choose a card" prompt at every Level with a candidate (1, 2, 3, 4),
  the picked card is the one summoned, face-up Defence.
- **B** — a SECOND Junk Speeder in the same duel is still OFFERED, i.e. the
  stale-criteria-word fix (phase 0x78 restoring `CAVE_JSP_DATA+0`) works.

## CLAUSE 2 STATUS: **DONE — in-game confirmed by user 2026-09-02.**

Everything clause 2 needs is confirmed on the live path:
- the Synchro-Summon trigger reaches an Extra-Deck donor through cls1;
- the optional-trigger prompt (slot3 `0x021F0419` + criteria row);
- the "Synchron" + Tuner + exact-Level filter (aux 0x4C, word bit 15, Level
  op 0), via the ov5 criteria-handler clone reading a mutable word;
- one summon per phase re-entry (`0x7F`/`0x7E`/`0x7C` cycle);
- **face-up Defence position** (`face_up=1, position=1`);
- the free-zone stop ("as many as possible");
- repeat activation in the same duel.

⚠️ STILL NOT IMPLEMENTED, and the card is therefore INCOMPLETE:
clause 1 (Synchron-only materials — user requires it, no deviation), clause 3
(Extra-Deck lock), clause 4 (double original ATK), clause 5 (once per turn).
**NOT wired into `apply_all_patches`** — the user has not said "ship it", and
CLAUDE.md forbids chaining a card that is still being built.

---

# DONOR AUDIT COMPLETED 2026-09-02 — two inherited properties I had MISSED

Found while reconning clause 1. `donor_scan` had reported two ov3 hits as
"unclassified" and one ARM9 hit as "ambiguous"; in round 1 I resolved only the
first and moved on. Finishing the audit found the donor cid in **exactly six
places**, two of them still live:

| occurrence | what it is | handled by |
|---|---|---|
| `ov3:0x0228DC94` | cls1 record 1320 | PART A (rewritten) |
| `ov3:0x022753F0` | criteria row 1369 | PART B (rewritten) |
| `ov3:0x0226D2AC` | battle-indestructible list, last entry | PART C (count decrement) |
| `ov3:0x0228F706` | Synchro-summon trigger list | kept deliberately |
| **`ov3:0x02197E88`** | **battle-damage redirection literal** | **PART F (new)** |
| **`arm9:0x0209C874`** | **"Gusto" set-code list, last entry** | **PART G (new)** |

## PART F — the donor granted BATTLE-DAMAGE REDIRECTION
`0x02197D14` is the "who takes the battle damage" function. It hardcodes three
cids and sets its redirect flag if the side controls any of them:
- Dimension Wall **0x1930** — "Instead of you, your opponent takes the Battle
  Damage you would have taken from this battle."
- Naturia Mosquito **0x22FE** — "Your opponent takes any Battle Damage you would
  have taken from battles involving a face-up 'Naturia' monster you control..."
- **Daigusto Sphreeze 0x24B3** — the donor.

The donor's compare is `ldr r1,[pc,#0x7C]` @ **0x02197E08** -> literal slot
**0x02197E88**, then `0x021AC0C8(side, cid, -1)` ("does this side control a
face-up <cid>"). So Junk Speeder was redirecting the player's battle damage to
the opponent — a real, strictly-beneficial deviation that testing would not
surface unless you looked for it.

FIX: retarget the literal to **0x3FFF**, a cid no card owns. `0x021AC0C8` calls
`0x02029E60(cid)` ("is this a real card") first and returns 0 when that fails,
so the grant becomes unreachable. **Verified sole consumer**: exactly ONE
pc-relative load in all of ov3 targets that slot, so the 4-byte edit cannot
disturb anything else. `verify()` also asserts the Dimension Wall / Naturia
Mosquito grants are still intact.

## PART G — the donor was a "Gusto" card
has_set_code ptr-table index **0x5F** -> thunk **0x02023F65** = the "Gusto"
list, a sorted 13-entry u16 array @ **0x0209C85C**: Gusto Gulldo 0x23CC, Gusto
Egul 0x23CD, Gusto Thunbolt 0x23CE, Wynnda 0x23CF, Caam 0x23D0, Windaar 0x23D1,
Daigusto Gulldos 0x23DC, Daigusto Eguls 0x23DD, Contact with Gusto 0x23DF,
Blessings for Gusto 0x23E2, Gusto Skwirl 0x24A6, Reeze 0x24A7, and **the donor
last**. So Junk Speeder was searchable//supported as a Gusto card.

FIX: the donor is the LAST entry, so one count decrement drops it —
`movs r2,#0x0D` -> `#0x0C` at **0x02023F68** (thunk body + 4), the same shape as
PART C. Guarded by asserts that the thunk and list base have not moved, the list
is still sorted, and it still ENDS with the donor. ARM9 edits go through
`ndspy.code.MainCodeFile` per the ov5_cave note.

Both built; `verify()` now **16/16 PASS**. Neither touches anything clause 2
does, so the round-3 in-game confirmation stands.

## Scope decision (user, 2026-09-02)
> "Fix the bugs, and skip clause 3 and 4 for the time being."

- Clause 3 (Extra-Deck lock) and clause 4 (double ATK): **DEFERRED**, not waived.
  Both are recorded above with their candidate mechanisms.
- Clause 1 (Synchron-only materials): still REQUIRED, still outstanding.
- Clause 5 (once per turn): not discussed this round; still outstanding.
- The optional "Junk" archetype membership (Junk table 0x50 has a free phantom
  0x2524) was NOT done — it is an addition, not a bug, and was not requested.

## Clause 1 recon (read-only, this session)
- The material subsystem is closed over one driver (`synchro.third_pred_is_the_
  nontuner_caller`): the TUNER goes to OUTER `0x022485B4`, every NON-TUNER to
  THIRD `0x02248A88`, both calling INNER `0x0224829C`.
- Hook precedents: Boggart owns `0x022482B2`, Quasar owns `0x022482B6` (they
  chain); the non-Tuner gate is `0x02248AAC` (Azure Eyes PART F).
- ⚠️ **0x24B3 has NO literal-pool reference anywhere in the material
  subsystem**, so Sphreeze's "WIND Tuner + WIND non-Tuners" rule is encoded
  base±imm and is UNGREPPABLE. Locating it needs emulator measurement
  (`scratch/thumbemu.py`), not a scan. That is the first job of the clause-1
  session.
- ⚠️ Cross-link found: `synchro.is_tuner_predicate` ALREADY documented
  `0x02023110` as "is this cid a Tuner". This session's
  `dispatch.criteria_word_bit15_is_tuner` re-derived the same function from the
  criteria-word side. The two agree exactly; a grep for the address would have
  found the existing fact sooner.

---

# CLAUSE 1 — measured 2026-09-02.  The donor's REAL material rule, and the plan.

## Ruled Out — hypothesis 1: "no literal in the subsystem => no named rule"
FALSIFIED by a control. `0x24B3` has no literal anywhere in
`0x0224829C..0x02249DA0`, which looked like proof that Sphreeze's material rule
is unimplemented. But classifying all 36 trigger-list members by their printed
material line shows **30 cards with NAMED rules also have no literal there**
(Junk Warrior "Junk Synchron" + ..., Arcanite Magician "non-Tuner Spellcaster",
Locomotion R-Genex "Genex Tuner + DARK non-Tuners", ...); only Trident Dragion
0x2003 does. The switches reach most cids as `base +- chained adds`, exactly the
shape `thumb.stack_based_switch_footgun` warns about. **Absence of a literal
proves nothing here.** Two near-literals that looked promising (0x24B5 Vylon
Element at delta -2, 0x2419 Synchro Material) are not switch arms at all -- both
load into r2 and call the attached-rider walker `0x021A1430`, where r2 is a
rider KEY.

## Confirmed — measured with scratch/thumbemu.py over rom_junk_speeder.ml3

### NON-TUNER side: the donor HAS an exclusive arm, and it demands **GUSTO**
Tracing THIRD `0x02248A88` per cid and diffing PC paths, the donor diverges from
generic Trishula at `0x02248D0E` and terminates at leaf **`0x02249360`**.
Donor-exclusivity is then closed structurally, not statistically:
```
0x02248EBE  ldr  r0,=0x2527
0x02248ED8  subs r0,#0x74        ; 0x2527 - 0x74 = 0x24B3  <- THE DONOR
0x02248EDA  cmp  r5,r0
0x02248EDC  bne  0x02248EE0
0x02248EDE  b    0x02249360      ; reached ONLY when r5 == 0x24B3
```
The leaf resolves the material's cid (hand path via `player+0x124`, field path
via `0x021A3320`) and then:
```
0x0224938E  bl 0x02023F64        ; <- the "Gusto" has_set_code THUNK
0x02249392  b  0x022494C6        ; return its verdict
```
`0x02023F64` is the thunk whose pointer-table entry (index 0x5F) is
`0x02023F65` -- the same one PART G edits.
**⇒ Junk Speeder's non-Tuner materials must currently be GUSTO monsters.**
That is why the test boards had Wynnda, Priestess of Gusto 0x23CF on them, and
it is a serious playability problem for a Junk/Synchron deck.

### TUNER side: NO restriction at all
Tracing OUTER `0x022485B4`, the donor and generic Black Rose Dragon both end at
**`0x02248A70`** = `synchro.allow_leaf`. The donor has no exclusive node; it
falls through the shared `b 0x02248A70` at `0x0224898C`.
**⇒ "1 WIND Tuner" is NOT implemented; any Tuner is accepted.**

### So OTN implements Daigusto Sphreeze as
"**any Tuner + 1+ non-Tuner GUSTO monsters**" -- not the printed
"1 WIND Tuner + 1+ non-Tuner WIND monsters".

## Plan for clause 1 (two edits, one of them 4 bytes)

**PART H -- non-Tuner: drop the Gusto requirement.** The leaf `0x02249360` is
donor-exclusive (proven above), so overwrite its verdict call in place:
`bl 0x02023F64` @ `0x0224938E` -> `movs r0,#1 ; nop`. The following
`b 0x022494C6` then returns 1 = accept any non-Tuner. Four bytes, no cave, and
it cannot affect another card because no other cid reaches that leaf.

**PART I -- Tuner: require "Synchron".** The donor has no arm to retarget, so
hook the call `bl 0x0224829C` at **`0x022485D8`** -- OUTER's call into INNER.
By `synchro.third_pred_is_the_nontuner_caller`, INNER has EXACTLY TWO callers,
`0x022485D8` (OUTER = the TUNER caller) and `0x02248AAC` (THIRD = the NON-TUNER
caller, which Azure Eyes PART F owns). So a gate at `0x022485D8` is
**Tuner-only by construction**, the exact mirror of Azure Eyes' argument, and it
needs no GDB and no LR sniffing.
**`0x022485D8` IS UNCLAIMED** -- verified: it appears only in comments in
patch_azure_eyes / patch_shooting_quasar and in the KB fact, and no patch writes
it. (Deliberately NOT `0x022482B6`/`0x022482B2`: Quasar and Boggart own those and
they already chain.)
The ov5 stub: if the Synchro cid != 0x24B3, tail-call INNER unchanged; otherwise
call INNER and AND its verdict with the "Synchron" thunk `0x02023E1C`
(setcode.synchron_table index 0x4C) applied to the material's cid.

## Next Experiment
Write PART H + PART I, rebuild, and in-game test that Junk Speeder can be made
with **Junk Synchron (DARK) + any non-Tuner** and CANNOT be made with a
non-Synchron Tuner.

# CLAUSE 1 BUILT 2026-09-02 — AWAITING IN-GAME TEST

**PART H — non-Tuner side opened.** `bl 0x02023F64` (the Gusto thunk) at
`0x0224938E` -> `movs r0,#1 ; nop` (bytes `01 20 C0 46`). The leaf returns 1 for
any monster, which is the printed "1+ non-Tuner monsters". Guarded by asserts
that the displaced instruction really was the Gusto-thunk call AND that
`subs r0,#0x74` @ `0x02248ED8` is intact — that instruction IS the proof the leaf
is donor-exclusive, so verify() re-checks it rather than trusting the earlier
measurement.

**PART I — Tuner side gated on "Synchron".** New ov5 stub
`CAVE_JSP_TUNER = 0x0239E200` (52 B of 0x60), installed over OUTER's
`bl 0x0224829C` at **`0x022485D8`**:
```
push {r4,r5,r6,r7,lr}
r4 = synchro cid ; r5 = arg1 ; r6 = arg2
INNER(0x0224829C)            ; replay the displaced call
if verdict == 0      -> return it unchanged
if r4 != 0x24B3      -> return it unchanged      (every other Synchro untouched)
r0 = 0x021A3320(r5, r6)      ; the material's cid, OUTER's own accessor
r0 = 0x02023E1C(r0)          ; has_set_code[0x4C] = "Synchron"
pop {r4,r5,r6,r7,pc}
```
Tuner-only BY CONSTRUCTION: INNER has exactly two callers, and the other
(`0x02248AAC`, inside THIRD) is the non-Tuner path that patch_azure_eyes owns.
verify() asserts THIRD's call is NOT claimed by this patch.

`verify()` **20/20 PASS**. Ledger refreshed: 164 ov5 slots, no overlaps.

## Next Experiment — clause 1 in-game
1. **Junk Synchron (DARK, Lv3) + any non-Tuner totalling Lv5** must now make
   Junk Speeder. Before this build the non-Tuners had to be GUSTO monsters, so
   this is the headline change.
2. A **non-Synchron Tuner** (e.g. any generic Lv3 Tuner) + a non-Tuner must be
   REFUSED — that is PART I doing its job.
3. Regression: clause 2 must still fire (prompt per Level, face-up Defence).
4. Regression: other Synchro monsters must still summon normally — especially
   **Daigusto Gulldos / Daigusto Eguls** (still real Gusto Synchros) and any
   Azure Eyes / Boggart / Quasar card, since PART I sits on a shared call site.

---

# IN-GAME TEST 4 — CLAUSE 1 **IN-GAME CONFIRMED BY USER 2026-09-02**

User's exact words:
> "Okay I am only able to summon with junk Synchron + Any non-tuner. Clause 2
> still fires, no regressions"

Clarified on request: "only" means **only a "Synchron" Tuner is accepted** (a
non-Synchron Tuner is refused); Junk Synchron was simply the one they tested.

So both halves of clause 1 are confirmed on the live path:
- **PART H** — the non-Tuner side is open. "Any non-tuner" works, where before
  this build the non-Tuners had to be GUSTO monsters.
- **PART I** — the Tuner side requires set code 0x4C. The ov5 gate over
  `0x022485D8` correctly ANDs the "Synchron" thunk into INNER's verdict, and it
  is Tuner-only by construction.
- **No regressions**: clause 2 still fires, and other Synchro Summons are
  unaffected — which is the live evidence that hooking `0x022485D8` leaves every
  other Synchro's material rule untouched.

## CLAUSE 1 STATUS: **DONE — in-game confirmed by user 2026-09-02.**
## CLAUSE 2 STATUS: **DONE — in-game confirmed by user 2026-09-02.**

## Card state
| clause | status |
|---|---|
| 1 materials: 1 "Synchron" Tuner + 1+ non-Tuner | **DONE, in-game confirmed** |
| 2 Deck SS of Synchron Tuners, different Levels, Defence | **DONE, in-game confirmed** |
| 3 Extra-Deck lock for the turn | DEFERRED by user (downside clause) |
| 4 double original ATK on attack declaration | DEFERRED by user |
| 5 once per turn per effect | NOT STAMPED |
| donor hygiene: battle-indestructible / damage redirect / Gusto | **fixed (C/F/G)** |

⚠️ Still NOT wired into `apply_all_patches` — the user has not said "ship it".
⚠️ The 64 KB cave has still not had a duel played on `rom_all_patches.nds`.

---

# CLAUSE 2 REDESIGN — pooled picker (user request 2026-09-02)

User's exact words:
> "Can we try to do clause 2 slightly differently... Instead of summoning out
> monster in sequences, offer all synchrons levels 1,2,3,4,5 and then remove the
> level of the summoned monster each time one is summoned. So if the first
> summon summons a level 1, then the next entry into the effect only offers
> 2,3,4,5"

Confirmed on questioning: (1) one POOLED prompt per summon, offering every
eligible "Synchron" Tuner whose Level has not been used yet; (2) **NO cancel** --
"the effect says summon as many, the prompt shouldnt say no or cancel. The cust
must summon until the board is full each unique levelled synchrons".

This is also closer to the printed card than the ascending sweep: "as many as
possible with different Levels" fixes how many and at what Levels, not the order.

## Confirmed — the criteria WORD cannot express a Level SET
`dispatch.criteria_word_level_field`: one Level field, op in {exactly, >=, <=}.
There is no way to say "Levels {1,2,4,5}". So the filter has to move to a
per-candidate hook.

## *** Confirmed — 0x0223C825 IS A PER-CANDIDATE VETO (measured, twice) ***
The walker callback (the pointer the stock criteria handler passes in r2):
```
0x0223C824  ldr r0,[sp] ; ldr r1,[sp,#4] ; ldr r0,[r0] ; ldr r1,[r1]
            lsls r0,#0x12 ; lsrs r0,#0x12      ; r0 = the candidate's CID
            ldr r3,=0x020240D9 ; bx r3         ; TAIL-call the matcher
```
⚠️ Its tail target `0x020240D8(r0 = cid, r1 = selector)` does `cmp r1,#0x70 ;
blt` and dispatches through a pointer table -- so the second argument is a small
SELECTOR, **not** the criteria word. Reading the callback as "the criteria
matcher" would have been wrong.

MEASUREMENT 1 -- it runs once per ACCEPTED candidate. Running the real
`0x02243FA8(side=0, cid=0x24B3, 0)` under thumbemu over rom_junk_speeder.ml3:
| criteria word | count | callback executions | matcher executions |
|---|---|---|---|
| 0x00008002 (any Synchron Tuner) | 10 | **10** | 10 |
| 0x000C8002 (Level exactly 3) | 2 | **2** | 2 |
So it is consulted AFTER the word filtering, once per surviving candidate.

MEASUREMENT 2 -- its return value is a VETO. Patching the callback in the
emulator's copy-on-write memory:
| callback | resulting candidate count |
|---|---|
| unmodified | 10 |
| forced `movs r0,#0 ; bx lr` | **0** |
| forced `movs r0,#1 ; bx lr` | 10 |

**⇒ an ov5 clone of this callback that returns 0 for a candidate whose Level is
already used gives exactly the requested behaviour, with ONE search per prompt.**

## Design
- **CAVE_JSP_USED** -- 16 bytes, one per Level 0..15 (a byte array, not a
  bitmask: Thumb-1 has no register-operand shift in this assembler, but
  `ldrb rt,[rn,rm]` is available).
- **CAVE_JSP_CB** -- the callback clone: read [sp]/[sp+4] BEFORE pushing (the
  original has no frame), call the matcher, and veto if `used[LEVEL_OF(cid)]`.
- **CAVE_JSP_CRIT** -- pass CAVE_JSP_CB instead of 0x0223C825; the word is now
  CONSTANT 0x00008002, so the varying-word machinery and its stale-word hazard
  both disappear.
- **CAVE_JSP_RES** -- 0x80 clears used[] and goes to 0x7F; 0x7F checks zones,
  counts, and prompts; 0x7E opens the picker; 0x7C reads the pick, marks
  `used[level] = 1`, summons, and returns to 0x7F; 0x78 clears used[] again and
  tears down.
⚠️ used[] MUST be cleared at teardown as well as at 0x80, because the ACTIVATION
GATE (slot3 -> 0x02243FE0 -> our handler -> our callback) runs before 0x80 --
the same trap the stale criteria word had.

## POOLED-PICKER REVISION BUILT 2026-09-02 — AWAITING IN-GAME TEST

Slots claimed: `CAVE_JSP_USED = 0x0239E260` (0x20) and
`CAVE_JSP_CB = 0x0239E280` (0x50). `CAVE_FREE` -> 0x0239E2D0. Ledger: 166 ov5
slots, no overlaps.

- **callback clone** 60 B — loads `[sp]`/`[sp+4]` BEFORE pushing (the original
  has no frame), extracts the cid, calls the matcher `0x020240D8`, and on a
  pass vetoes when `used[LEVEL_OF(cid)] != 0`.
- **criteria handler** now passes `CAVE_JSP_CB|1` in r2 instead of the stock
  `0x0223C825`; the word is CONSTANT `0x00008002`. verify() asserts both.
- **resolver** 276 B, and SIMPLER than the sweep — the Level counter is gone:
  - `0x80` three legality gates, clear `used[]` (4 stores), -> `0x7F`
  - `0x7F` free-zone check -> `0x78`; `0x02243FA8` count -> 0 means `0x78`;
    else message 0x30 -> `0x7E`
  - `0x7E` picker -> `0x7C`
  - `0x7C` read-back -> `&locator`; cid = `[locator] & 0x3FFF`;
    `used[LEVEL_OF(cid)] = 1`; `0x0226925C(side, &locator, 1, 1, cid<<16)`
    -> `0x7F`
  - `0x78` clear `used[]`, teardown, -> 0x64
  ⚠️ `used[]` is cleared at BOTH `0x80` and `0x78` because the ACTIVATION GATE
  runs the same handler+callback before `0x80` — the same trap the stale
  criteria word had.

Dead code removed with the sweep: `LEVEL_CELL`, `MAX_LEVEL`, `PICK_INDEX_BLOCK`,
`LOCATOR_ARRAY`, `NO_CANDIDATE_CLEANUP`. `verify()` **27/27 PASS**.

### Next Experiment (in-game)
1. The FIRST prompt should list Synchron Tuners of **every** Level at once
   (1,2,3,4,5 together), not just Level 1.
2. Pick a mid Level (say a Level 3). The NEXT prompt should show the same pool
   **minus every Level-3 Synchron**.
3. It should keep prompting with no cancel option until the zones fill.
4. Regression: clause 1 (Synchron Tuner required, any non-Tuner) unchanged.
5. Regression: a SECOND Junk Speeder in the same duel must still be offered —
   that is the `used[]`-cleared-at-teardown check.

---

# IN-GAME TEST 5 — POOLED PICKER **IN-GAME CONFIRMED BY USER 2026-09-02**

User's exact words:
> "That effect works perfectly!"

Confirmed (test points A-D of the round-5 list): the first prompt offers every
eligible "Synchron" Tuner across all Levels at once; picking one strikes that
Level from the next prompt; there is no cancel; clause 1 still holds.

⚠️ **Test point E was NOT explicitly reported**: a SECOND Junk Speeder in the
same duel still being OFFERED. That exercises the `used[]`-cleared-at-teardown
path (phase 0x78), and it is the one failure mode "the effect works" would not
reveal — the activation gate runs the same criteria handler and callback BEFORE
phase 0x80, so leftover used-Levels would make a second copy silently never
prompt. Recorded as UNTESTED, not as confirmed.

## CLAUSE 2 (pooled-picker revision) STATUS: **DONE — in-game confirmed 2026-09-02**

## Card state
| clause | status |
|---|---|
| 1 materials: 1 "Synchron" Tuner + 1+ non-Tuner | **DONE, in-game confirmed** |
| 2 Deck SS, pooled picker, distinct Levels, Defence | **DONE, in-game confirmed** |
| 3 Extra-Deck lock that turn | DEFERRED by user (downside clause) |
| 4 double original ATK on attack declaration | DEFERRED by user |
| 5 once per turn per effect | NOT STAMPED |
| donor hygiene (battle-indestructible / damage redirect / Gusto) | fixed, C/F/G |

Outstanding, both independent of the card:
- the 64 KB ov5 cave has still had **no duel** on `rom_all_patches.nds`;
- Junk Speeder is **not wired into `apply_all_patches`**.

## Ruled Out — "Road Synchron + Level Eater won't summon" is NOT a bug
Reported 2026-09-02, then self-corrected by the user ("road synchrons effect
makes it level 2 when not summoning road warrior"). Confirmed against ov3 and
`rom_junk_speeder.ml4` (board: Road Synchron 0x1EA1 in z2, Level Eater 0x20F8 in
z3, Level Eater's live instance record Level 1):

```
0x02249A54  bl 0x021A36EC     ; r0 = the material's cid
0x02249A58  ldr r1,=0x1EA1    ; Road Synchron
0x02249A5C  beq 0x02249A66
0x02249A68  subs r1,#0xA2     ; 0x1EA1 - 0xA2 = 0x1DFF = ROAD WARRIOR
0x02249A6C  cmp r0,r1         ; the Synchro being summoned  ([0x0229ABFC+0x68])
0x02249A6E  beq 0x02249A78    ;   Road Warrior -> no reduction
0x02249A70  subs r5,r5,#2     ;   otherwise LEVEL -= 2
0x02249A76  movs r5,#1        ; floored at 1
```
So Road Synchron counts as **Level 2** for anything but Road Warrior:
2 + 1 = 3, and Junk Speeder is Level 5. Correct refusal.
Level Eater 0x20F8 has **no literal anywhere** in 0x0224829C..0x02249DA0, so its
old "cannot be Synchro Material except for a DARK monster" clause is not what
blocked it either.

⚠️ Note for future card work: `scratch/ygoprodeck_cache.json` carries the MODERN
errata'd text (its Level Eater entry has no material restriction at all), while
the 2011 engine implements the ORIGINAL printing. Where the two differ, the
engine is the authority on what the engine does.

⚠️ Also confirms PART I is innocent here: Road Synchron IS in the Synchron
set-code table, so the Tuner gate accepted it; the refusal came from the level
arithmetic, downstream of the material predicates entirely.

## Quickdraw Synchron + Level Eater refusal — measured 2026-09-02

User: "See .ml4, quickdraw synchron + level eater cannot summon junk speeder.
This is definetely a bug! It is likely that junk speeder needs to be added to
another table"

Board in `rom_junk_speeder.ml4`: side 0 z2 = Quickdraw Synchron 0x20F7,
z3 = Level Eater 0x20F8, **GY EMPTY (count 0)**, hand = Instant Fusion, Ryko,
Bri Synchron, Quillbolt Hedgehog.

### Ruled Out — the "another table" hypothesis
`0x02248280(synchro)` = the REQUIRED LEADING TUNER COUNT the driver uses
(`synchro.third_pred_is_the_nontuner_caller`). Emulated over this very board:
| synchro | N |
|---|---|
| **0x24B3 (Junk Speeder)** | **1** |
| 0x1EDA Black Rose Dragon | 1 |
| 0x239E Formula Synchron | 1 |
| 0x1E10 Junk Warrior | 1 |
The donor is identical to every control, so it is not missing from that table.
It is also NOT in LIST_A (checked earlier), which is what would have imposed an
"exact count, extras forbidden" rule.

### Ruled Out — Level Eater being refused as a material
Emulating THIRD `0x02248A88` (the NON-TUNER caller) over this board:
`synchro 0x24B3 -> 1` and `synchro 0x1EDA (control) -> 1`. Level Eater is
ACCEPTED as a non-Tuner material for Junk Speeder. So its original-printing
"cannot be used as Synchro Material except for a DARK monster" clause is not
firing here. (Worth stating because a LITERAL SCAN cannot prove this either way
-- that method was falsified earlier this session.)

### The arithmetic
`0x0202ABD8` over the same state: Quickdraw Synchron = **Level 5**, Level Eater =
**Level 1**, Junk Speeder = **Level 5**. 5 + 1 = **6**, not 5.
The canonical real-world line needs Level Eater to act FROM THE GRAVEYARD first
("If this card is in your GY: target 1 Level 5 or higher monster you control;
reduce its Level by 1, and if you do, Special Summon this card"), taking
Quickdraw to 4 so that 4 + 1 = 5. In this state the GY is empty and Level Eater
is already on the field, so that reduction has not happened.

### ⚠️ Open, and the reason this is not yet closed
Quickdraw 0x20F7 has **no live instance record** on this board, while Level Eater
does (rec[0], Level 1). Per `ram.card_instance_record` the Level/ATK fields are
live only while a card is FACE-UP on the field, so this is consistent with
Quickdraw being SET (face-down) -- and a face-down monster cannot be Synchro
material at all. The two zone words differ in their high half
(0x0D80_20F7 vs 0x0E80_20F8), which may encode exactly that.
NOT RESOLVED: needs the user to say whether Quickdraw was face-up.

## *** CONFIRMED BUG — Quickdraw Synchron's material whitelist predates Junk Speeder ***

User's exact words: "See .ml4, quickdraw synchron + level eater cannot summon
junk speeder. This is definetely a bug! It is likely that junk speeder needs to
be added to another table" — followed by "Quickdraw was level 4 because of level
eaters effect", which makes 4 + 1 = 5 and the summon legal.

**The user's hypothesis was correct.** Measured, not inferred:

### Printed text (scratch/ygoprodeck_cache.json — the authority)
> **Quickdraw Synchron**: "... **Cannot be used as a Synchro Material, except for
> the Synchro Summon of a monster that LISTS a 'Synchron' Tuner as material.**"

Junk Speeder's materials are `1 "Synchron" Tuner + 1+ non-Tuner monsters`, so it
DOES list one and Quickdraw should be legal.

### The engine implements that clause as a 9-CID WHITELIST
Emulated INNER `0x0224829C` with the material fixed to Quickdraw and the SYNCHRO
varied over all 140 real Synchro monsters in card_prop. **Exactly 9 accept:**
Road Warrior 0x1DFF, Junk Warrior 0x1E10, Nitro Warrior 0x1E35, Turbo Warrior
0x1ED9, Junk Archer 0x2185, Drill Warrior 0x21CC, Junk Destroyer 0x229C, Junk
Gardna 0x2355, Chevalier de Fleur 0x23EF — i.e. precisely the 2011-era Synchros
that list a "Synchron" Tuner. **The donor 0x24B3 is not among them**, because
Junk Speeder did not exist when the game shipped.
Control: material = Level Eater is accepted for **all 140**, so Level Eater was
never the blocker.

### Scope: Quickdraw is the ONLY affected Synchron Tuner
Sweeping every member of the Synchron set-code list as the material (by rewriting
the zone-2 cid in copy-on-write memory) against the donor:
ACCEPT for Junk / Nitro / Road / Turbo / Hyper / Drill / Changer / Formula /
Fleur / Bri Synchron and the 0x2501 slot; **REFUSE for Quickdraw 0x20F7 alone.**
Control: Quickdraw IS accepted for Junk Warrior 0x1E10. (0x0D6B and 0x1E4E are a
Speed Spell and a Trap, 0x229E Synchron Explorer is not a Tuner; all three fail
to emulate and none is relevant.)

### ⚠️ Not a table insert
The whitelist is NOT a contiguous sorted array — searching both oracles for the
9-cid u16 sequence finds nothing. It is another base±imm compare chain inside
INNER, same as every other per-cid switch in this subsystem.

### The fix, and a defect it also repairs
PART I's gate already sits at `0x022485D8`, is already donor-scoped, and already
runs on the TUNER path only — so it is the natural place. New behaviour:
```
verdict = INNER(...)
if synchro != donor            -> return verdict unchanged
material = 0x021A3320(arg1, arg2)
if verdict == 0 and material != 0x20F7 -> keep the rejection
   (only Quickdraw's stale whitelist is overridden; every OTHER
    "can only be used for X" rejection INNER makes still stands)
return has_set_code[0x4C](material)      ; clause 1's Synchron rule
```
⚠️ It also fixes a real defect I shipped in round 4: `synchro.nontuner_gate_hook`
requires a stub here to **re-establish r1/r2/r3 on exit** (INNER restores them
from its own `push {r1-r7,lr}` and the caller may rely on it). The round-4 stub
called 0x021A3320 and the Synchron thunk AFTER INNER returned and then popped
only r4-r7, leaving r1/r2/r3 clobbered on the donor's path. Now restored
explicitly (arg3 is 0 at this site — OUTER does `movs r3,#0`).

## FIX BUILT + VALIDATED OFFLINE 2026-09-02 — awaiting in-game confirmation

Tuner gate grew 52 -> **84 B** (slot widened 0x60 -> 0x80; CAVE_JSP_USED moved to
0x0239E280, CAVE_JSP_CB to 0x0239E2A0, CAVE_FREE 0x0239E2F0). `verify()` 28/28,
ledger 166 slots no overlaps.

**A/B'd against the FAILING board (ml4) before spending a duel** — the new stub
written into copy-on-write memory and OUTER re-run, materials swapped by
rewriting the zone-2 cid:

| material -> synchro | round-4 gate | NEW gate |
|---|---|---|
| **Quickdraw -> Junk Speeder** | **0** | **1** ← the bug, fixed |
| Junk Synchron -> Junk Speeder | 1 | 1 |
| Road Synchron -> Junk Speeder | 1 | 1 |
| Level Eater -> Junk Speeder | 0 | 0 |
| Quillbolt Hedgehog -> Junk Speeder | 0 | 0 |
| Quickdraw -> Junk Warrior (control) | 1 | 1 |
| Quickdraw -> Black Rose (control) | 0 | 0 |
| Junk Synchron -> Black Rose (control) | 1 | 1 |

**Exactly one cell changed.** No other Synchro's material legality moved, and
non-Synchron Tuners are still refused for the donor.

### In-game test for this round
1. **Quickdraw Synchron (reduced to Level 4 by Level Eater from the GY) +
   Level Eater** must now Synchro Summon Junk Speeder. That is the exact line
   from ml4.
2. Regression: Junk Synchron + any non-Tuner still works.
3. Regression: a non-Synchron Tuner is still refused.
4. Regression: **Quickdraw must still be usable for Junk Warrior / Junk
   Destroyer / Road Warrior**, and must still be REFUSED for a Synchro that
   does not list a Synchron Tuner (e.g. Black Rose Dragon). The gate is
   donor-scoped, so those go through untouched — but they are the thing that
   would break if the scoping were wrong.

---

# IN-GAME TEST 6 — QUICKDRAW FIX **CONFIRMED**, CARD **SHIPPED** 2026-09-02

User's exact words: > "Perfect. Ship it"

So the Quickdraw whitelist override works in-game, and the regressions held
(Quickdraw still usable for its native Synchros, still refused for ones that do
not list a Synchron Tuner).

## SHIPPED — wired into the combined build chain
Both edits made together, per `otn-chain-build-verify-artifact` (a PatchStep
without the sweep entry means the sweep silently stops covering the card):
- `apply_all_patches.py`: import, `_apply_junk_speeder(src, out)` wrapper
  carrying the full in-game history and the shared-state audit, and
  `PatchStep("Daigusto Sphreeze -> Junk Speeder (clauses 1+2)")` at index 46 —
  **above the always-last WiFi-timers step**. PATCHES: 47 -> **48**.
- `_verify_all_patches.py`: `patch_junk_speeder` appended to SHIPPED, 38 -> **39**.

## FINAL CARD STATE
| clause | status |
|---|---|
| 1 materials: 1 "Synchron" Tuner + 1+ non-Tuner | **DONE, in-game confirmed** |
| 2 Deck SS, pooled picker, distinct Levels, face-up Defence | **DONE, in-game confirmed** |
| 3 Extra-Deck lock that turn | DEFERRED by user — downside clause, card is stronger than printed without it |
| 4 double original ATK on attack declaration | DEFERRED by user |
| 5 once per turn per effect | NOT STAMPED |
| donor hygiene: battle-indestructible / damage redirect / Gusto | fixed (C / F / G) |
| Quickdraw Synchron usable as material | fixed (PART I override) |

## Still open after shipping
1. **The second-copy check was never run** — a SECOND Junk Speeder in the same
   duel must still be OFFERED (the `used[]`-cleared-at-teardown path). Recorded
   UNTESTED, not confirmed.
2. **The 64 KB ov5 cave has still had no duel.** Statically clean, but only play
   confirms the smaller heap; rollback is the single `RESERVE` constant.
3. Junk Speeder is NOT a "Junk" archetype card. Its name says it should be, and
   the Junk set-code table has a free phantom slot 0x2524 — never requested, so
   never done.

---

# PART J + PART K added 2026-09-02 (user: "Add the Hard once-per-turn and add it to the Junk table")

Both AWAITING IN-GAME TEST. `verify()` **34/34 PASS**; ledger 167 ov5 slots, no
overlaps. The in-flight 48-patch chain build was STOPPED at 7/48 first, so no
stale artifact was left and only one chain build is needed.

## PART J — "Junk" archetype membership
Junk Speeder's NAME makes it a "Junk" card. `setcode.junk_table` (set code 0x50,
sorted 13 x u16 @0x0209C842) ships with TWO phantoms, 0x2500 and 0x2524 -- the
real Konami ids of Junk Servant and Junk Berserker. patch_junk_servant already
spends 0x2500, so this patch spends **0x2524**; both coexist, the list stays a
sorted 13, and the consumer thunk's hardcoded `movs r2,#0x0D` keeps reading it.
Reuses the SHIPPED helper `patch_junk_servant.add_junk_member` rather than a new
implementation. Result in the single-card build:
`1E07 1E10 1E3D 200C 2185 219E 221F 229C 2335 2355 23FF **24B3** 2500`.

## PART K — the hard once-per-turn (clause 5)
`dispatch.turnlog_once_per_turn_pair` (VERIFIED), the same pair
patch_shooting_quasar PART K already ships in-game:
- QUERY `0x021A14E8(side, 0x0B, cid, 1)` -> nonzero iff already used this turn
- POST  `0x021D2584(side, cid, 1, 0)`
- **kind 1 is the END-OF-TURN-SWEPT kind** (kinds 1/2 take the countdown-and-remove
  arm of the sweeper 0x0219F9E0), which is what makes it per TURN and not per
  Duel like kind 5.

**GATE** -- new ov5 stub `CAVE_JSP_COND = 0x0239E2F0` (56 B of 0x50) installed as
cls1 slot3 in place of the shared `0x021F0419`:
```
if 0x021D2B88(desc)  -> chain the native condition
     (a RESOLVING effect must not re-deny itself)
if QUERY(desc[+2], 0x0B, desc[+0], 1) -> return 0
else                 -> chain 0x021F0419(desc, arg1)
```
⚠️ r1 is carried in r4 and restored: `0x021F0419` is a TWO-argument condition,
and Quasar's notes record an in-game regression from chaining a 2-arg native
without restoring its second argument. r6 is pushed because the query needs all
of r0-r3 and a register for the call target.

**STAMP** -- the resolver posts the node in phase 0x80, right after clearing
`used[]`. Resolver 276 -> 292 B.

### ⚠️ DEVIATION, stated not hidden
The stamp happens at the START OF RESOLUTION (phase 0x80), not at activation.
A true hard OPT is consumed even if the activation is negated before resolving;
this one is not. For this card the gap is narrow -- the effect only triggers on a
fresh Synchro Summon of Junk Speeder -- but it IS a deviation from "hard".
Quasar stamps in a non-resolve context via `0x021D2B88`, which is the faithful
place; doing the same here would mean chaining the slot4 activation-step machine.

### Next Experiment (in-game)
1. Summon Junk Speeder, use the effect. Summon a SECOND Junk Speeder the SAME
   turn -> its effect must NOT be offered.
2. Next turn -> a new Junk Speeder's effect IS offered again (kind 1 is swept at
   end of turn; if it behaved per-Duel the kind would be wrong).
3. Regression: the FIRST activation still works normally (the gate chains the
   native condition, so the prompt and the pooled picker are unchanged).
4. PART J: a "Junk" search/support card should now find Junk Speeder, and
   Junk Servant must still be findable (both phantoms spent, list still sorted).

## PART K — **IN-GAME CONFIRMED BY USER 2026-09-02**
User's exact words: > "Confirmed it is a hard once per turn."

So the gate works: after the effect is used, a second Junk Speeder the same turn
is NOT offered, and the first activation still behaves normally (the shim chains
the native condition 0x021F0419, so the prompt and pooled picker are unchanged).

⚠️ SCOPE OF THAT CONFIRMATION — two things it does NOT cover, both recorded
UNTESTED rather than assumed:
1. **The per-TURN reset.** Nobody has confirmed that a NEW turn offers the effect
   again. That is the whole point of using turn-log kind 1 (swept at end of turn
   by 0x0219F9E0) instead of kind 5 (never swept, per Duel). If the kind were
   wrong the observed behaviour so far would be IDENTICAL -- it would just never
   come back. One duel that passes a turn settles it.
2. **PART J, the "Junk" membership.** Not mentioned in the report. A Junk search
   or Junk support card should now find Junk Speeder, and Junk Servant must
   still be findable (both phantoms are now spent, list still a sorted 13).

Also still untested from earlier rounds: a SECOND Junk Speeder being offered in a
LATER duel/turn is the same experiment as (1); and the 64 KB ov5 cave has still
had no duel.

## PART J — **IN-GAME CONFIRMED BY USER 2026-09-02**
User's exact words: > "I can confirm the Junk membership"

Junk Speeder is found by "Junk" support, i.e. the count-neutral insert into
setcode.junk_table (spending phantom 0x2524) works on the live path.

The paired risk -- that the insert did not knock Junk Servant out of the same
list -- does NOT need a duel: patch_junk_servant's own verify() asserts its
membership, and `_verify_all_patches.py` runs it against the CHAINED ROM, where
both patches have applied. That is covered by the sweep.

## Remaining UNTESTED after this round
1. **The once-per-turn RESET.** Still nobody has passed a turn and re-used the
   effect. kind 1 vs kind 5 is indistinguishable from everything observed so far
   -- a wrong kind would look identical and simply never come back.
2. **The 64 KB ov5 cave has had no duel.** Static validation across the whole
   chain is clean; only play confirms the smaller heap. Rollback is the single
   `RESERVE` constant.

---

# COMBINED ROM BUILT AND VERIFIED — 2026-09-02

Artifact asserted, not trusted (exit code 0 has produced a plausible but
incomplete ROM twice on this build):
- log banner: **ALL 48 PATCHES APPLIED**, progress reached **48/48**, zero errors
- WiFi timers ran LAST (the TURN/MATCH timer lines are the final step's output)
- `data/over_the_nexus/working/rom_all_patches.nds`, 129,536,136 B
- **sha256 `2768443508979996dd2e08cbcff84e1e178282269c85e53b0d25d07dbd596d2f`**

`_verify_all_patches.py` over that ROM: **PASS 37, FAIL 0, SKIP 2**
(patch_boggart_knight and patch_darksoul have no verify() of their own).
That sweep is what independently proves Junk Speeder's insert did not disturb
any previously shipped card — patch_junk_servant's own verify() runs against the
combined ROM, so the shared "Junk" table is checked from both sides.

"Junk" set-code list in the COMBINED ROM — both cards present, count still
`movs r2,#0x0D`, still sorted:
```
17CE Neo Aqua Madoor  <- JUNK SERVANT   1E07 1E10 1E3D 200C 2185 219E
221F 229C 2335 2355 23FF   24B3 Daigusto Sphreeze  <- JUNK SPEEDER
```
Both phantoms (0x2500, 0x2524) are now spent; the list is full at 13. A third
Junk insert would need the array relocated, not an eviction.

## FINAL STATE — Junk Speeder
| item | status |
|---|---|
| clause 1 materials | **in-game confirmed** |
| clause 2 Deck SS (pooled picker) | **in-game confirmed** |
| clause 5 hard once-per-turn | **in-game confirmed** (per-turn RESET untested) |
| "Junk" archetype membership | **in-game confirmed** |
| Quickdraw whitelist override | **in-game confirmed** |
| donor hygiene: battle-indestructible / damage redirect / Gusto | fixed |
| clause 3 Extra-Deck lock | DEFERRED by user, not waived |
| clause 4 double original ATK | DEFERRED by user, not waived |
| in the combined build chain | **SHIPPED**, step 47 of 48 |

## STILL UNTESTED (both need a duel; neither is closable statically)
1. **The once-per-turn RESET.** kind 1 (end-of-turn swept) vs kind 5 (per-Duel)
   are indistinguishable from everything observed so far — a wrong kind would
   look identical and simply never come back. Pass a turn and re-use the effect.
2. **The 64 KB ov5 cave.** Whole chain re-verifies clean, but only play confirms
   the smaller duel heap (215.7 KB vs a 37.3 KB measured peak). Rollback is the
   single `RESERVE` constant in ov5_cave.py; no CAVE_* slot moves.
