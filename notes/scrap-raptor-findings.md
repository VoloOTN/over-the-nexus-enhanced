# Scrap Raptor — findings (live)

> **READ THE TAIL FIRST.** This file is a chronological log and several early
> sections were later DISPROVEN — they are kept, clearly marked, only as
> provenance for how the errors were made. The canonical state is the
> **`## Status`**, **`## Next Experiment`** and **`## KB contributions`**
> sections at the BOTTOM. The continuation prompt is
> **`PROMPT_scrap_raptor_clause1b.md`**.
>
> ⚠️ Two sections are explicitly wrong and say so in their headings:
> "the stock Scrap clause is dead in OTN" (disproven by the user's savestates)
> and the `+14` root-cause claim (the fix did not work). Do not act on either.

Session 2026-09-22. Donor **Uraby `0x0FF6`**. User scoped the **whole card**
(C0 + C1 + C2) in one session, sequenced as four independently-testable stages.

## Printed text (`scratch/ygoprodeck_cache.json`, grepped — never recall)

    Scrap Raptor   Tuner Effect Monster / EARTH / Dinosaur / Level 4 / 1400 / 1000

    You can target 1 monster you control; destroy it, also, during your Main
    Phase this turn, you can Normal Summon 1 "Scrap" monster in addition to your
    Normal Summon/Set. If this card is destroyed by the effect of a "Scrap" card
    and sent to your GY: You can add 1 "Scrap Factory" or 1 non-Tuner "Scrap"
    monster from your Deck to your hand. You can only use each effect of "Scrap
    Raptor" once per turn.

| # | Clause | Stage |
|---|---|---|
| C0 | Chassis: Lv4 EARTH Dinosaur Tuner 1400/1000 + "Scrap" set code | 1 |
| C2 | Destroyed by a "Scrap" card's effect -> add 1 non-Tuner "Scrap" from Deck | 2 |
| C1a | Ignition: target 1 monster you control; destroy it | 3 |
| C1b | ...also Normal Summon 1 "Scrap" in addition, this Main Phase | 4 |
| C3 | Each effect once per turn | folded into 3 + 4 |

**USER-APPROVED DEVIATION (2026-09-22):** the `"Scrap Factory" or` half of C2 is
dropped — Scrap Factory is absent from the NDS *and* the 3DS build. C2 ships as
"add 1 non-Tuner 'Scrap' monster from your Deck to your hand". Strictly weaker
than printed, never stronger.

## Confirmed (this session)

- **Scrap Raptor is in NEITHER build.** 3DS name sweep over all 5887
  `CARD_Prop.bin` records lists 26 "Scrap" cards; Raptor is not among them
  (2019 card). **Reference source #2 is unavailable for this card.** Substitute
  authority = the 21 Scrap cards the NDS does ship.
- **No reserved phantom cid for Scrap Raptor or Scrap Factory.** The "Scrap" set
  code list's 3 remaining phantoms resolve (3DS) to `0x2441` Scrap Mind Reader,
  `0x24ED` Scrap Breaker, `0x251F` Scrap Kong — none is Raptor.
- **"Scrap" set-code list**: thunk `0x02023EE5`, base `0x0209CC70`, **n=25**,
  strictly sorted. Stock and current baseline both read clean (baseline already
  holds `0x13C6` from `patch_scrap_archfiend`, which spent phantom `0x23F2`).
  None of `0x2441` / `0x24ED` / `0x251F` is in `PHANTOM_CLAIMS`.
- **Donor Uraby `0x0FF6`** — Normal Monster, **already Level 4 / EARTH /
  Dinosaur**, 1500/800. `donor_scan 0x0FF6` → **VERDICT CLEAN**, no data
  structure names the cid. **Zero CPU decks** (`deck.json`). Only ATK/DEF change.
  - Its 8 ARM9 data-region u16 hits (`0x0209D61E`, `0x0209D622`, `0x0209E4B0`,
    `0x0209E4B4`, `0x0209E61C`, `0x0209E620`, `0x020A14B2`, `0x020A14B6`) are a
    **sine / circle-coordinate LUT** — smoothly-varying `(x,y)` pairs
    (`0xFF9,0xEF` -> `0xFF9,0xF5` -> ...) plus a negated mirror table
    (`0xFF18 == -0xE8`). 4086 appears as a coordinate value, not a cid. **Not a
    per-cid gate.**
  - Name slot floor is **5 B** (`"Uraby"`) vs 12 B for `"Scrap Raptor"`, so the
    cid **must join `card_text.CARD_TEXT`** (63 entries today, `0x0FF6` absent)
    and take the INDEX-ORDER RE-EMIT path, which has no slot limit.
    (Elder-of-the-Six-Samurai precedent: long name on a short donor.)

### The criteria-row mechanism — decoded this session, by disassembly

Row shape `{u16 cid, u16 aux, u32 handler, u32 word}` @ `0x022713C4`, 0x56C rows,
stride 12, sorted by cid.

- **`aux` IS THE SET CODE.** Every Scrap card's row carries `aux = 0x0057`
  (Chimera, Goblin, Beast, Scrapyard, Scrapstorm, Soldier, Lube, Worm, Shark,
  Orthros). Gusto rows carry `0x5F`, Gladiator Beast `0x24`, Blackwing `0x3F`.
- **Deck handlers all tail-call the shared builder `0x0223BC3C`** and pass
  `[sp+4]` as the **DESTINATION**, not a predicate:
  - `2` = add to **hand** (Scrapyard `0x2312`, Pot of Duality, Witch of the
    Black Forest, Goblin Zombie)
  - `0x0A` = **Special Summon** from Deck (Giant Rat, UFO Turtle, Shining Angel,
    Gravekeeper's Spy, Pyramid Turtle, Jurrac Velo, Gusto Egul)
  - `0` and `0x4` / `0xE` / `0x12` / `0x20` are further destinations, unmapped.
- **`word` is a predicate bitmask:**
  - `0x00008000` = **Tuner only** — Scrapyard `0x00008002` ("1 'Scrap' **Tuner**
    monster"), Scrap Hunter's Deck row `0x00008002` ("send 1 **Tuner** monster
    from your Deck"). Two independent confirmations.
  - `0x00900000` = **Level 4 or lower** — Gladiator Proving Ground, Charge of the
    Light Brigade, Scarr Scout of Dark World, Worm Cartaros all print "Level 4 or
    lower" and all carry it. Four-way confirmation.
  - low bits `...02` ride along with the destination.
- **`r2` is a pooled per-card PREDICATE CALLBACK** `(candidate, aux) -> bool`,
  loaded `ldr r2,[pc,#imm]` inside the handler.
  - `0x0223C825` (generic `0x0223CAF5`'s) = set-code test only.
  - **`0x02243305` (Gusto Egul's) = `has_set_code(cid, aux) AND NOT
    is_tuner(cid)`** — disassembled at `0x02243304`: masks the candidate cid
    (`lsl #18 / lsr #18`), `bl 0x020240D8` (set-code test), rejects on 0; then
    re-masks and `bl 0x02023110` (**is_tuner**), rejects on non-zero; else
    returns 1. **It reads `aux` from the row** — it is NOT card-specific.
- **Gusto Egul's handler `0x02243339` is structurally the SAME FUNCTION as the
  generic Deck handler `0x0223CAF5`**, differing in exactly two things: the
  `[sp+4]` destination immediate (`0xA` vs `2`) and the pooled callback. Both
  read aux from row+2, word from row+8, cid from row+0.

### What actually makes a card a TUNER — VERIFIED, closed (Stage 1's core fact)

**The rules-level Tuner flag is `card_prop.card_type_encoded`, NOT genre bit 35.**

`is_tuner` = **`0x02023110`** (the predicate Gusto Egul's callback BLs).
Disassembled end to end this session:

    push {r3,lr}
    bl   0x0202ABF8        ; getter -> card_type_encoded >> 1
    subs r0,#0xf           ; window the result to [15..20]
    cmp  r0,#5
    bhi  -> return 0
    add  r0,pc ; ldrb r0,[r0,#6] ; add pc,r0     ; 6-byte jump table @0x02023128

- **Getter `0x0202ABF8`** is `ldr r0,[r0,#4] ; lsls #26 ; lsrs #27` — a 5-bit
  field = `card_type_encoded >> 1`. (card_type occupies bits [32:38] and every
  legal value is odd, so the top 5 bits are the value halved.)
- **Jump table `0x02023128` = `04 04 08 08 04 04`**, branch base `0x0202312A`;
  `+4` -> `movs r0,#1` (Tuner), `+8` -> `movs r0,#0`. All six bytes read, so the
  table is CLOSED:

  | card_type_encoded | | verdict |
  |---|---|---|
  | 31 Normal Tuner Monster | -> 15 | **TUNER** |
  | 33 Tuner Monster | -> 16 | **TUNER** |
  | 35 Synchro Monster | -> 17 | not |
  | 37 Synchro Effect Monster | -> 18 | not |
  | 39 Synchro Tuner Effect Monster | -> 19 | **TUNER** |
  | 41 (unused) | -> 20 | **TUNER** |
  | anything else | | not |

  => **Scrap Raptor needs `card_type_encoded = 33`.** This is also what makes the
  C2 non-Tuner callback correctly exclude Raptor itself.

- **`0x020240D8` = `has_set_code(cid, setcode)`** — bounds-checks `setcode < 0x70`,
  indexes the pointer table `0x0209D0D8` (pool literal at `0x020240EC`), `blx`es
  the thunk. Independent confirmation that a criteria row's `aux` is a set code.

- **Genre bit 35 is a deck-editor TAG, not the rules flag.** Measured across all
  4305 records: bit 35 is set on **5/5** ct-31, **172/172** ct-33 and **1/1**
  ct-39 records — but *also* on 15 plain Effect Monsters, 1 Gemini and 5 Synchro
  Effect monsters (e.g. **Scrap Chimera `0x22F6`, a non-Tuner, has bit 35**).
  So it tracks "Tuner-related" for search, and cannot be the predicate.
  Genre bit 6 is not type-correlated (232/1686 Effect, 31/172 Tuner) — meaning
  unproven, left clear.

- **`genre == exactly 1<<35` is the most common Tuner Monster shape** (10 of the
  172 ct-33 records, e.g. Genex Spare) — a real existing record shape, so it is
  what Scrap Raptor gets. Not invented.

- **Reference record for the card_prop copy: Scrap Beast `0x22F8`** (idx 3943) —
  already `card_type_encoded=33`, **Level 4, EARTH**, 1600/1300. Copy the whole
  record (carrying its reserved/unknown bits), then set cid, race=Dinosaur and
  1400/1000. ⚠️ Never a one-field card_type flip: `patch_w_nebula_meteorite`
  proved that leaves a hybrid record that renders a glitched frame and freezes.

### C2's trigger is a shipped, cid-BLIND record

Scrap Goblin `0x22F7`, Beast `0x22F8`, Soldier `0x238D`, Worm `0x2468` and
Orthros `0x24DE` carry the **byte-identical** cls2 record for the **identical**
printed trigger ("If this card is destroyed by the effect of a 'Scrap' card and
sent to the Graveyard, you can select 1 'Scrap' monster in your Graveyard,
except <self>, and add it to your hand"):

    +04=0x02208181  +08=0  +0C=0x021F05A9  +10=0x021E51E5  +14=0x02235605

Five different cids, one record => cid-generic. `0x021F05A9` is the
"destroyed by a 'Scrap' card's effect and sent to your GY" condition.
Scrap Shark `0x2469` reuses the same `+0C`/`+10` with a different `+04`, which is
the independent confirmation that `+04` is the free parameter.

`0x02207EF5` is the generic "add 1 -> hand" resolver (Scrapyard's `+04`; the same
one `patch_dragunity_remus` uses).

## Ruled Out (hypotheses killed this session, with the evidence)

- **"non-Tuner is a bit in the criteria `word`."** FALSE. Every non-Tuner search
  in the ROM uses a **custom handler**, not a word bit: Gusto Egul `0x02243339`,
  Blackwing Vayu `0x02241A0D`, Viper's Rebirth `0x0224263D`, Scrap Dragon
  `0x02242E41`. None of them is the generic `0x0223CAF5`.
- **"`[sp+4]` is the predicate selector."** FALSE — it is the **destination**.
  Mode `0x0A` is shared by Giant Rat / UFO Turtle / Shining Angel / Gravekeeper's
  Spy / Pyramid Turtle, all of which Special Summon from the Deck and none of
  which is non-Tuner-filtered.
- **"Gusto Egul's handler hardcodes its own set code `0x5F`."** FALSE, and this
  was the dangerous one — it is the `patch_dragunity_remus` `0x1BC1`-`0x1BC7`
  trap (a cloned handler that silently searches the template's own target and
  still passes `verify()`). The `movs r1,#0x5f` at `0x02243364` belongs to the
  **next routine**, which starts at `0x0224335C`, past the `pop {r1,r2,r3,pc}`
  at `0x02243356` and its literal pool at `0x02243358`.
- **"Some existing Deck->hand handler already carries the non-Tuner callback."**
  FALSE. All seven mode-2 handlers checked (`0x0223CAD9`, `0x0223CAF5`,
  `0x0223D5FD`, `0x0223D675`, `0x02240D59`, `0x02241EA5`, `0x02242F09`) — none
  BLs `0x02023110`. => C2 needs its own ~0x20 B ov5 handler.
- **`0x021DF0B9` is NOT the target framework for C1a.** It is the *Scrap-filtered*
  "target 1 face-up 'Scrap' monster you control" picker, shared by Scrap Sheen,
  Scrap Hunter and Scrap Orthros — all three of whose printed text carries that
  exact archetype restriction. C1a targets **any** monster you control.

## Open Questions

- **C1a's target framework**: which cls `+08` is "target 1 monster you control"
  with **no** archetype filter? Best candidate `0x021DEF31` (7 of its 11 cards
  print the phrase: Energy Drain, H - Heated Heart, Hero Mask). UNPROVEN.
- **C1b's grant window**: Scrap Raptor's is "you resolved C1a this turn", not a
  field state, so no existing extra-NS arm's field check can be cloned.
- Whether C1a and C2 can take **two independent** turn-log latches under one cid
  (C3 is "each effect once per turn").

## Next Experiment

1. Disassemble `0x0223BC3C` at its callback call site: confirm the two stack args
   the callback reads are `(candidate, aux)` in the order `0x02243305` expects,
   and confirm destination `2` adds to hand.
2. Disassemble `0x021DEF31` and diff against `0x021DF0B9` to locate which
   argument carries the archetype filter.

## Stage 1 (C0, the chassis) — BUILT 2026-09-22, verify PASS, AWAITING IN-GAME TEST

`otn_enhanced/cards/scrap_raptor.py` + `_build_scrap_raptor.py`.
Pure data: no ov5 cave slot, no cls record, no criteria row, no injected Thumb.

    data/over_the_nexus/working/rom_scrap_raptor.nds
    129,517,704 B   sha256 cf42452045985efc439be9b3a0257b6ffe1d536e4de1ee9382f523989b15e8d6

`verify()` **12/12 OK**. Artifact asserted independently of `verify()`
(`otn-chain-build-verify-artifact` — assert content, not the exit code):

    Scrap list n=25, sorted, 0x0FF6 @1, phantom 0x2441 gone,
                     0x24ED / 0x251F still unspent
    card_prop[320]   cid 0x0FF6  ct33 Tuner Monster  Lv4 EARTH Dinosaur 1400/1000
    card_genre[320]  0x0000000800000000   (bit 35 only)
    name             'Scrap Raptor'
    desc             full printed text, all 8 languages

`check_allocations` clean (279 phantom claims, ledger re-emitted):
`scrap_setcode_table 0x2441 -> scrap_raptor`, `scrap_setcode_table 0x0FF6`,
`donor_cid 0x0FF6`.

**Deviation from the approved plan, and why:** the plan said to build the
card_prop record as a **reference-record copy** from Scrap Beast `0x22F8`. I did
a plain same-size field edit instead. Reason: field-by-field, Uraby and Scrap
Beast differ only in cid / atk / def / card_type / race **and bit 56**, and bit
56 measured across all 4305 records is NOT type-structural — it is set on
~18-24% of cards in *every* card_type including Spells and Traps (9/233 ct-1,
361/1686 ct-3, 42/172 ct-33, 176/1024 Spells, 148/731 Traps). Copying the
reference record would have imported a per-card flag of unknown meaning for no
reason. The `patch_w_nebula_meteorite` hybrid-record lesson applies to a
main-deck <-> Extra-deck change (Fusion -> Synchro); Normal -> Tuner is
main-deck -> main-deck with every field aligned, and
`patch_elder_six_samurai` already does Normal -> Effect by field edit,
in-game confirmed.

⚠️ Two small API traps hit while building, worth carrying:
- `patch_boggart_knight.apply_stats_and_text(card_type=...)` is annotated
  `card_type: str` but assigns straight to `fields["card_type_encoded"]` — it
  wants the **encoded int** (`ERA2_CARD_TYPE_REVERSE[...]`). Passing the display
  string raises `TypeError: unsupported operand type(s) for &: 'str' and 'int'`.
- Its `skip_name_if_too_long` is irrelevant once the cid is in
  `card_text.CARD_TEXT` — the re-emit path ignores slot sizes entirely.

## Stage 2 (C2) — BUILT 2026-09-22, verify PASS 29/29, AWAITING IN-GAME TEST

Three parts, all in the one module:

- **E** `CAVE_SR_DECKFIND = 0x023A12B0` (0x24 B) — **Gusto Egul's criteria
  handler `0x02243338` relocated byte-for-byte**, with exactly ONE halfword
  changed (`+0x10`: `movs r0,#0xa` -> `movs r0,#2`), the two-halfword BL
  re-encoded to the shared builder `0x0223BC3C`, and the 4-byte literal pool
  keeping Gusto Egul's callback pointer `0x02243305` unchanged. Built by copying
  the shipped bytes, never hand-assembled. Disassembled from the built ROM:
  correct `push {r1,r2,r3,lr}` / `pop {r1,r2,r3,pc}` pair, `ldr r2,[pc,#4]`
  resolving to `0x023A12D0` exactly.
- **F** criteria row `{0x0FF6, aux=0x0057, handler=0x023A12B1, word=0x00000002}`,
  count-neutral (dropped phantom `0x0EA4`), table still 0x56C rows and sorted.
- **G** cls2 record
  `{0x0FF6, +04=0x02207EF5, +08=0, +0C=0x021F05A9, +10=0x021E51E5, +14=0x02235605}`,
  count-neutral (dropped phantom `0x0E2D`). Exactly one cls2 row for the cid, so
  no `find_event_handler` leftmost shadow. All five template cards re-asserted
  unchanged.

### The `word` / `mode` split — CORRECTED, and it matters

An earlier reading in this file said "`[sp+4]` mode: 2 = add to hand,
0x0A = Special Summon from Deck". **That is wrong and is corrected here.**

Disassembling the shared builder `0x0223BC3C` shows it takes the handler's
`[sp+0]` as `word` (into r6) and `[sp+4]` as `mode` (into r4), and then tests
`mode` **as a bitmask** (`tst r0,r4` against 0x18, 4, 2, 8, 0xFE<<24).
`0x0A == 8|2`, so Gusto Egul's mode is Scrapyard's mode **plus bit 8**, and
bit 8 is what makes the builder run the Special-Summon legality check
`bl 0x021B9ED8` on every candidate.

**The criteria row does NOT choose the destination.** Proof: Scrapyard `0x2312`
(*add* 1 Scrap Tuner from Deck to hand) and Scrap Shark `0x2469` (*send* 1 Scrap
monster from Deck to the GY) share handler `0x0223CAF5` **and** mode 2 **and**
differ only in their cls `+04` resolver. So:

    criteria row + handler  ->  WHICH ZONE and WHICH PREDICATE (the candidate list)
    cls record +04 resolver ->  WHAT HAPPENS to the pick

This is why Scrap Raptor takes its **mode from Scrapyard** (whose *action*
matches: a Deck->hand search) and its **callback from Gusto Egul** (whose
*predicate* matches: non-Tuner). Taking both from one card would be wrong.

⚠️ **This is the retired `CAVE_WU_ED` failure in reverse, and it validates the
direction.** `patch_wattuna` put a cloned criteria handler at this same address
with the mode byte changed `movs r0,#4` -> `movs r0,#0x24`; the extra bit added
`can_synchro 0x02249540`, which walks only the 10 field slots, and the Extra-Deck
offer came back empty **in-game**. Scrap Raptor *removes* a mode bit rather than
adding one, and removes precisely the check that does not apply to an
add-to-hand search.

### Artifact

    data/over_the_nexus/working/rom_scrap_raptor.nds
    verify() 29/29 OK  (Stage 1's 12 + Stage 2's 17)

`check_allocations` clean: 267 ov5 slots, 281 phantom claims, ledger re-emitted.
New claims: `cls2_table 0x0E2D`, `criteria_table 0x0EA4`,
`ov5 CAVE_SR_DECKFIND 0x023A12B0` (CAVE_FREE bumped to `0x023A12D4`).

## Stage 3 (C1a + its once-per-turn) — BUILT 2026-09-22, verify PASS 41/41

One cls3 ignition record, two ov5 OPT stubs. **Every framework slot was proven
cid-blind by disassembly or multi-card consensus, not assumed.**

    cls3 {0x0FF6, +04=0x02204899, +08=0x021DEF31,
                  +0C=0x023A12D5, +10=0x023A1305, +14=0x02234DA5}

- **`+04 = 0x02204899` "destroy that target"** — a 3-instruction cid-blind
  wrapper (`push {r3,lr}; bl 0x02204674; movs r0,#0; pop {r3,pc}`). No switch,
  no pool. Consensus over all its users: Trap Hole, Mystical Space Typhoon,
  Michizure, Thousand Knives, Remove Trap, Double Snare, Scrap Orthros — every
  one prints "destroy that target".
- **`+08 = 0x021DEF31` "target 1 face-up monster you control"** — a
  4-instruction thunk `push {r3,lr}; ldr r3,=0x00000415; bl 0x021D6E40;
  pop {r3,pc}`. **`0x021D6E40` is the shared target-selection worker and `r3` is
  its FILTER argument** — that is the mechanism behind every cls `+08`. All 11
  users with printed text say exactly "target/select 1 face-up monster you
  control", and two of them are cls3 **ignitions** (Frequency Magician `0x1E0A`,
  Tree Otter `0x1EA4`), so the picker is proven on the ignition path.
- **`+0C`/`+10`** = our ov5 stubs, chaining the natives `0x021F01C0` /
  `0x021E5060`.
- **`+14 = 0x02234DA5`** from the 10-card group pairing it with that exact
  condition/cost — which includes **Uria `0x19A3` and Cyber Laser Dragon
  `0x19A9`, both already using `+04 = 0x02204899`**. So
  `(+04, +0C, +10, +14)` is a shipped multi-card generic "once per turn: target
  something; destroy it" ignition and the only thing this card changes is `+08`.

### The once-per-turn: why NOT the free native pair

`(+0C 0x021F01C1, +10 0x021E5061)` is already a complete cid-blind
once-per-turn latch — disassembled: the condition calls the attached-node walker
`0x021A1430` and returns "can activate" only if the node is absent; the cost
calls `0x021C479C` to post it. Both pool **node kind `0x0FB6`**, which the KB
([[otn-vanilla-ignition-recipe]]) names as the **per-copy rider**.

It was rejected on mechanism, per that note's own warning ("pick per-copy vs
cid-keyed by mechanism, not recall"):

1. the printed limit is per-**name** ("each effect of *Scrap Raptor* once per
   turn"), and the `0x0FB6` node is keyed `(side, slot)` — per copy; and
2. **C1a can legally target and destroy itself**, which destroys a slot-keyed
   node that Stage 4's grant window still has to read.

So C1a uses the cid-keyed turn log (`0x021A14E8` query / `0x021D2584` post) and
**chains** the native pair, so the per-copy latch also holds. Per-name is
strictly stricter, so the turn log is what binds.

⚠️ The `desc[+7]` guard is live here, not belt-and-braces: this record has a real
target template at `+14` (Mystic Piper had `+14 == 0`), so slot3 IS re-evaluated
after the cost runs. Without the guard the effect would activate and then fizzle
silently.

### Deviation, recorded

**C1a targets a FACE-UP monster you control.** The printed text says "1 monster
you control", which in modern rulings can include a face-down monster. A
narrowing — weaker than printed, never stronger. Every cid-blind own-field
picker in this engine is the face-up one.

### Artifact (Stages 1 + 2 + 3)

    data/over_the_nexus/working/rom_scrap_raptor.nds
    129,525,896 B   sha256 c0be636caba200a8b97e2ce3ac5fb94e3ce179a80fe8da87b3b9f29e416de368
    verify() 41/41 OK

Both stubs disassembled from the built ROM: correct `push {r4,lr}` /
`pop {r4,pc}` pairs, correct BL targets, `desc[+7]` guard in place.
`check_allocations` clean (269 ov5 slots, 282 phantom claims, ledger in sync).

## Stage 4 (C1b) — THE TWO NATIVE MECHANISMS, and why neither alone is enough

User ruling 2026-09-22: **"The grant has to outlive the granter (like how double
summon works)."** So the on-field narrowing below is REJECTED. That sent me to
Double Summon, and the engine turns out to have **two different** extra-Normal-
Summon mechanisms:

### A. The DOUBLE SUMMON path — granter-free, but UNRESTRICTED

Double Summon `0x1C33` is one resolver and nothing else:
`cls0 {+04=0x02208C51, rest 0}`. `0x02208C51` is a shared multi-card resolver
with a per-cid switch; tracing cid `0x1C33` falls to the common tail with r5=0:

    r0 = side, r1 = acting cid, r2 = 1 | ((r5 & 0xF) << 4), r3 = 0
    bl 0x021D2584                      ; TURN-LOG POST, keyed by the ACTING CID

The consumer is **`0x021B9514(side) -> how many Normal Summons remain`**:

    r4 = 0
    if the base Normal Summon is unused (0x0229ADB4 + 0xB3C*(side&1), bit 20): r4++
    if node(side, 0xB, 0x1D20):
        if !0x021A14E8(side, 0xB, 0x1D20, 2): r4++
        if !0x021A14E8(side, 0xB, 0x1C33, 2): r4++
    else if node(side,0xB,0x0E00) or node(side,0xB,0x1C33)
            or 0x021ACB94(side, 0x23D4, 1):
        if !0x021A14E8(side, 0xB, 0x1C33, 2): r4++     ; 0x1C33 = the SPENT key

So: grant existence = an attached node keyed by the granter cid (kind < 6);
"already used" = a turn-log node kind 2 keyed `0x1C33`. **No field presence
anywhere** — this is exactly the behaviour the user asked for. But the +1 it
grants is **unrestricted**: any monster, no archetype filter.

### B. The DVERG / GRUNARD path — archetype-RESTRICTED, but needs the granter on field

`0x021B95C4` + the 3 other sites `patch_ninishi` owns. Arm shape:
`archetype(hand card) && on_field(side, granter) >= 0 && !spent(granter)`.
The on-field slot is genuinely dereferenced at `0x02261EA0`
(`muls r3,r1,r3` with stride 0x14 indexes `player + slot*0x14`), so a sentinel
slot would read another card's sub-struct. **The granter must be on the field.**

### THE CALL FLOW (mapped 2026-09-22) — where each property is decided

**`0x021B9674(side)` is the top-level "can this side Normal Summon?" gate:**

    bl 0x021B9514          ; THE COUNTER
    cmp r0,#0 ; bne -> return 1        ; count > 0 -> YES, and UNRESTRICTED
    r0 = side, r1 = 0                  ; "any card"
    bl 0x021B95C4          ; else: does an ARCHETYPE granter permit it?

=> **The counter is checked FIRST and wins outright.** Anything that increments
the counter grants an UNRESTRICTED Normal Summon — the archetype query is never
reached. That is why option A cannot be restricted: it is structural, not a
missing filter.

=> A **restricted** grant must go through `0x021B95C4` (SITE1). SITE1 takes
(side, hand-card cid) and returns a granter cid — **it needs no slot**, so
Raptor's arm there can test the turn-log node instead of `on_field`.

**The action state machine's Dverg arm** (`0x02261E3C`..`0x02261EF0`):

    r0 = desc[+0xE] (the chosen hand card) ; bl 0x02023FC4 (is_nordic)  <- SITE3 hook
    ... desc[+0x24] phase switch (0 / 0x64) ...
    r6 = 0x245B ; bl on_field(desc[+0], r6)      <- SITE3a: slot only TESTED
    blt bail
    node query (side, 0xB, 0x245B) -> already spent? bne bail
    r0 = desc[+2] ; bl 0x021B9514                ; THE COUNTER
    cmp r0,#0 ; beq 0x02261ED6                   ; <-- counter == 0 SKIPS the announce
    ... on_field again  <- SITE3b: slot DEREFERENCED, builds a card ref and calls
        0x0219AA50(side, granter, 0xE2, ref) -> 0x0219A9F0(..., 1): an event post
        attributing the extra summon to the granter CARD ON THE FIELD

`0x0219AA50` is a thin wrapper: `str 1,[sp] ; bl 0x0219A9F0`.

**The promising seam:** the slot-dereferencing announce (SITE3b) is only reached
when the counter is NON-zero. If Raptor's grant does NOT touch the counter, that
branch may be skipped entirely via `0x02261ED6` — which would remove the only
hard requirement for the granter to be on the field.
⚠️ UNPROVEN: `0x02261ED6` does `str r0,[r5,#0x34]` and r5 is not set on that
path within this arm, so r5 comes from earlier in the enclosing function —
which starts at **`0x022619DC`** (`push {r1-r7, lr}`, mask 0xFE) and runs past
`0x02261F00`. Tracing r5 through a state machine that large is the next job.
**That is the one unknown that decides whether option C is a small build or
needs the announce path rebuilt.**

### OPTION C — the build plan, and its honest size

1. **C1a posts the grant node** keyed `0x0FF6` (kind < 6, the Double-Summon
   shape) from the C1a resolver. SMALL — the cost stub already posts a turn-log
   node.
2. **Relocate `patch_ninishi`'s five `CAVE_NS_*` stubs** to larger fresh slots
   and re-point its 4 hooks (zero headroom; `CAVE_NS_PRED` has 0 B free).
   MEDIUM, mechanical, but it touches an in-game-confirmed card.
3. **SITE1 arm for Raptor** (`0x021B95C4`): test the grant NODE instead of
   `on_field`, return granter `0x0FF6`. SMALL once (2) is done — and SITE1 needs
   no slot, which is why this is the viable seam.
4. **SITE3 predicate**: extend "Nordic OR Karakuri" to include Scrap
   (thunk `0x02023EE4`). SMALL once (2) is done.
5. **The action state machine arm** — must perform the summon without the
   on-field announce. **UNBOUNDED until r5 is traced.** This is the risk.
6. **SITE4**: mark the grant spent. MEDIUM.
7. Prove the lift by execution over both patch orders; user re-tests Ninishi,
   Dverg and Haipa.

Steps 1, 3, 4 are small; 2 and 6 are mechanical; **5 is the open risk.**

### The problem

Scrap Raptor needs BOTH properties — granter-free AND "Scrap"-only — and
**no native card has both.** Double Summon and Ultimate Offering are both
unrestricted; every archetype-restricted granter (Dverg, Grunard, Swap Frog,
Ninishi) is a "while this card is face-up on the field" card.

So it is a choice of which half to give up, or new construction to combine them:

| option | persistence | restriction |
|---|---|---|
| A: Double-Summon node | ✅ outlives Raptor | ❌ ANY monster (wider than printed) |
| B: Dverg machinery | ❌ lost if Raptor leaves | ✅ Scrap only |
| C: A + a new restriction hook | ✅ | ✅ | 

C is new work, not a recipe: it needs the point where the extra summon's
legality/offer is decided to consult "did this +1 come from Raptor's node?" and
filter the hand to Scrap monsters there.

## Stage 4 (C1b) — earlier scoping: two blockers (on-field deviation now REJECTED)

### Blocker 1: zero cave headroom in `patch_ninishi`'s stubs

The extra-NS machinery is 4 hook sites + 5 ov5 stubs, all owned by
`patch_ninishi` and **in-game confirmed 2026-09-10**. A sixth granter means a
third arm in every stub. Measured headroom:

| stub | used | reserve | free |
|---|---|---|---|
| `CAVE_NS_ARM` 0x0239EBF0 | 100 | 0x70 | **12** |
| `CAVE_NS_SPENT` 0x0239EC60 | 28 | 0x20 | **4** |
| `CAVE_NS_PRED` 0x0239EC80 | 48 | 0x30 | **0** |
| `CAVE_NS_MATCH` 0x0239ECB0 | 20 | 0x20 | 12 |
| `CAVE_NS_FIELD` 0x0239ECD0 | 128 | 0x90 | 16 |

A third arm costs ~40 B in `NS_ARM` alone. **All five slots are contiguous**, so
none can grow in place — the five stubs must be **relocated** to fresh, larger
cave slots (the cave has ~36 KB free, so this is cost, not a wall). The 4 hook
sites re-point to the new addresses; the old slots are freed.

### Blocker 2: a FORCED deviation — the granter must be ON THE FIELD

The arm's structure is `archetype(hand card) && on_field(side, granter) >= 0 &&
!spent_this_turn(granter)`. I checked whether the returned slot is merely tested
or actually used, at all three `bl 0x021ABE4C` sites:

- `0x02261E68` — only tested (`cmp r0,#0 ; blt`). Fine.
- **`0x02261EA0` — USED**: `adds r3,r0,#0 ; movs r1,#0x14 ; muls r3,r1,r3` indexes
  `player + slot*0x14`, the granter's slot sub-struct. A sentinel slot would read
  another card's data.
- `0x02265164` — used as r1 to `0x021CF7D4`, but skipped when negative.

⟹ **The grant cannot be made to outlive the granter.** So C1b would be
"Raptor is on the field AND resolved C1a this turn":

- C1a destroys ANOTHER monster (the normal play) -> Raptor survives -> grant works.
- **C1a destroys Raptor ITSELF -> the extra Normal Summon is LOST.** Printed text
  says the grant persists for the turn regardless.

A NARROWING (weaker than printed), in the same family as the other two accepted
deviations — but it needs the user's decision, not my assumption.

### The design, once approved

1. Relocate the five `CAVE_NS_*` stubs to fresh slots and re-point the 4 hooks.
2. Turn the granter list into an ARMS registry (house pattern:
   `criteria_row_hook`, `handss_banish_cost`, `summon_rider_hook`) and add
   `(0x0FF6, is_scrap 0x02023EE4)` as the third entry, in `NS_ARM`, `NS_SPENT`,
   `NS_PRED` and `NS_MATCH`.
3. `CAVE_NS_FIELD` gains an arm for `0x0FF6`: return -1 unless C1a's turn-log
   node is posted (`0x021A14E8(side, 0x0B, 0x0FF6, 1)`), else the slot scan.
   This reuses the existing "negative = unavailable" contract, so the arm
   structure is untouched.
4. Prove the lift BY EXECUTION over both patch orders
   (`otn-shared-hook-lift-prove-by-execution`), Ninishi and Dverg unchanged.
5. User regression-tests Ninishi, Dverg and Haipa.

## Stage 4 (C1b) — earlier deferral rationale (superseded by the scoping above)

C1b's window is "you resolved C1a this turn" — it reads the very turn-log node
Stage 3's cost posts. **It cannot be validated until C1a is confirmed in a duel**:
if C1a does not fire, a C1b test yields no information. It also has to add a
sixth arm to the four extra-Normal-Summon pool sites (`0x021B9670`,
`0x021B9FBC`, `0x02261F84`, `0x022651B4`) that `patch_ninishi` owns and that are
**in-game confirmed** — stacking a shared-hook edit on two untested stages
compounds risk for no gain. Stage 4 follows an in-game pass on the oracle in
`_build_scrap_raptor.py`.

When it is built: retarget the per-hand-card archetype predicate BL to the
**"Scrap" thunk `0x02023EE5`**, and supply a custom `CAVE_NS_FIELD` that queries
C1a's turn-log node — do NOT clone Dverg's "was Normal Summoned this turn" or
Grunard's "is face-up" field check (that substitution is what cost a duel on
Ninishi). Re-test Ninishi and Dverg as regression controls.

## *** IN-GAME RESULTS 2026-09-22 (user-reported) ***

User's verbatim report:

    1. Confirmed
    2. Confirmed
    3. Scrap Raptor does not activate when destroyed by self
    4. Cannot confirm
    5. All confirmed
    6. Monster is destroyed

    No normal summon after effect activates as described.

Reading confirmed by the user as **(A)**: C1a was activated targeting Scrap
Raptor ITSELF, it destroyed itself, and then **no C2 search prompt appeared**.

### IN-GAME CONFIRMED BY USER 2026-09-22

- **Stage 1 / C0 — the whole chassis.** Deck editor identity (Lv4 EARTH Dinosaur
  Tuner 1400/1000, effect frame, Main Deck, full printed text), and
  **SCRAPYARD FINDS IT** — a real duel-path consumer reaching the card, which
  proves both the `0x0209CC70` set-code insert and `card_type 33` (is_tuner).
- **Stage 3 / C1a — the ignition.** Activates, targets, **destroys the target**
  (so no silent fizzle — the `desc[+7]` guard is correct), is once-per-turn, and
  refuses opponent-controlled monsters. It can target and destroy itself.

### NOT working

- **Stage 2 / C2 does not fire** on the self-destroy path. No search offered, so
  the non-Tuner filter (the new mechanism) is still **untested**, not disproven.
- C1b absent as expected (Stage 4 not built) — not a fault.

## Ruled Out (C2 diagnosis, 2026-09-22)

- **"The cls2 record needs a leave-mask row / leave-list membership."** FALSE.
  Checked the mask table `0x0226EC1C` (152 rows), list30 `0x0226E904` and
  list106 `0x0226E990`: **all five template cards (Goblin `0x22F7`, Beast
  `0x22F8`, Soldier `0x238D`, Worm `0x2468`, Orthros `0x24DE`) and Scrap Shark
  `0x2469` are ABSENT from all three.** The probe was validated with a positive
  control first — Dandylion `0x19FE` reads back at mask row 47 with mask
  `0x0800`, exactly as `leave.registration_paths_and_mask_table` states. So this
  trigger family is **not dispatched by the leave dispatcher at all**, and the
  "pairing" rule in that KB fact (mask row <-> cls2 with +0C/+10 both 0) does not
  apply here.

## CORRECTION to this session's own Stage 2 write-up

**`0x021F05A9` is NOT the "destroyed by the effect of a 'Scrap' card and sent to
your GY" condition.** That claim is wrong and is corrected here; the patch header
repeats it and must be fixed.

Disassembled at `0x021F05A8`:

    r5 = desc ; r6 = desc[+2] ^ desc[+6]        ; the side to search
    r4 = 1, or 2 for two pooled cids (compared against desc[+0])
    bl 0x02234E78        ; the PARAM PROVIDER (otn-param-provider-internal-hook)
    bl 0x02243FE0        ; COUNT the candidates the criteria row yields
    cmp r0, r4 ; blt -> return 0                ; too few candidates -> no activation
    return 1

So `+0C` here is an **availability gate on the criteria row's candidate count**,
not a timing/trigger test. The "when" for this family comes from somewhere else,
still unidentified. Two consequences:

1. the five-card consensus proves the record is cid-generic, but it does **not**
   prove what I claimed it proves about the trigger; and
2. a C2 failure could be either dispatch (the record is never consulted) **or**
   `0x02243FE0` counting 0 candidates from the ov5 criteria row.

## Open Questions (C2)

- What dispatches this family's cls2 record on "destroyed by a Scrap card's
  effect and sent to the GY", given no leave-table registration?
- Does the generic destroy resolver `0x02204899` (which C1a uses) post whatever
  that dispatch needs, while the Scrap-specific destroy resolvers
  (Scrap Sheen `0x0222FBE5`, Scrap Hunter `0x0222F95D`, Scrap Dragon
  `0x022048A5`) do? If so, C2 may be fine and only the SELF-destroy path is dead.
- Does `0x02243FE0` return >0 for the ov5 criteria row at all?

## *** ROOT CAUSE FOUND (offline, 2026-09-22): +14 WAS A TARGET TEMPLATE ***

**`+14` is the TARGET TEMPLATE, and a DECK search must carry `+14 = 0`.**

The trigger family has SIX members, not five, and the sixth is the one that
mattered — split by SEARCH ZONE:

| cid | card | zone | `+04` | `+14` |
|---|---|---|---|---|
| 0x22F7 / 0x22F8 / 0x238D / 0x2468 / 0x24DE | Goblin/Beast/Soldier/Worm/Orthros | **GY** | 0x02208181 | **0x02235605** |
| **0x2469** | **Scrap Shark** | **Deck** | 0x02208DD5 | **0** |
| 0x2312 | Scrapyard (same `+04` as ours) | **Deck** | 0x02207EF5 | **0** |
| 0x0FF6 | Scrap Raptor (first build) | Deck | 0x02207EF5 | **0x02235605** ← BUG |

A GY search *targets* ("target 1 'Scrap' monster in your GY"); **nothing in the
Deck is targetable**, so the target template found no legal target and the
activation was declined — **with no prompt at all**, which from the player's seat
is indistinguishable from the trigger never firing.

**The mistake was taking the record from the cards whose TRIGGER matched instead
of the one whose ZONE matched** — [[grep-the-template-cards-text-too]] exactly.
Scrap Shark was sitting in the same family the whole time, on the same `+0C`/`+10`,
with the correct `+14`. Both Deck-zone precedents (Shark on this trigger,
Scrapyard on this resolver) ship `+14 = 0`.

⚠️ Generalisation worth carrying: **a wrong criteria row or a wrong target
template on this trigger presents as SILENCE, not as an error**, because `+0C`
(`0x021F05A9`) is an availability gate — "is there anything to find" — evaluated
before any prompt. Never read a missing prompt on such a card as "the trigger did
not fire".

### Also ruled out on the way (both by disassembly, both dead ends)

- **"The generic destroy resolver `0x02204899` fails to post the trigger."**
  FALSE. It and Scrap Dragon's multi-target `0x022046B8` converge on the same
  pair — `0x0224A924` then the destroy primitive `0x021CF388`. No trigger-post
  exists in either for the other to be missing.
- **"Some per-cid structure registers the template family."** FALSE. An aligned
  u16/u32 sweep of ov3 + ARM9 for all five templates found exactly two
  structures naming ≥3 of them: the "Scrap" set-code list `0x0209CC70` (which
  this patch already joins) and `0x0228E2EC`, which belongs to their *other*
  clause (the end-of-Battle-Phase self-destruct shared by Goblin/Beast/Soldier/
  Worm and absent from Orthros and Shark). Nothing else. The cls2 record is
  reachable by cid alone.

## FIXED BUILD (2026-09-22) — AWAITING IN-GAME RETEST

`CLS2_TAIL` `0x02235605` -> `0x00000000`. One constant. The record is now
**Scrap Shark's with `+04` swapped for Scrapyard's Deck->hand resolver** — both
halves now from Deck-zone precedents.

    cls2 {0x0FF6, +04=0x02207EF5, +08=0, +0C=0x021F05A9, +10=0x021E51E5, +14=0}

    data/over_the_nexus/working/rom_scrap_raptor.nds
    129,525,896 B  sha256 cbb4f3d3ad42d8c95f0df7dc549729a300b5e45bfdb5f2651bcbb2d09fefaf00
    verify() 45/45 OK

Two new guards so this cannot regress: `apply_cls2_record` asserts Scrap Shark's
record is the expected Deck-zone template *before* writing, and `verify()`
asserts `+14 == 0` with the reason attached.

## STRIKE 2 — the `+14` fix did NOT work (in-game, 2026-09-22)

User: *"I had activated scrap raptor, destroyed itself, still no search."*
Savestate `data/over_the_nexus/working/rom_scrap_raptor.ml2` supplied.

### Savestate parse — every input is CORRECT

RAM base auto-detected at file offset 0x24.

| check | result |
|---|---|
| `cls2[0x0FF6]` in RAM | `+14 = 0` -> the **FIXED** build; state is from the right ROM |
| ov5 cave `0x023A12B0` | stub intact, mode `0x2002`, callback `0x02243305` -> **ov5 resident** |
| criteria row in live RAM | `row[70] cid=0x0FF6 aux=0x0057 handler=0x023A12B1 word=0x00000002` |
| did Raptor reach the GY? | **yes** — side0 GY count=2, holds `0x0FF6` |
| legal C2 candidates in Deck | **6** — Scrap Chimera x3, Scrap Golem, Uraby x2 |

Record, row, stub, residency and candidate pool are all correct, so the
availability gate would have passed. **The cls2 record is never consulted.**

## *** ROOT CAUSE: NO LEAVE SUBSCRIPTION *** (two-strike precedent search)

Stopped patching per the two-strike rule and diffed against the shipped,
in-game-confirmed card with this exact trigger shape —
**`patch_gravekeepers_recruiter`** ("If this card you control is sent to your GY:
add 1 ... from your Deck to your hand", records-free Normal donor Battle Steer
`0x0FB4`, confirmed 2026-09-10).

Its PART A3 states the mechanism outright. The leave dispatcher `0x021C7FD0` has
**three registration paths**, all setting the same arm flag `[sp+0x18]`
(`event.leave_dispatcher_three_registers`):

    0x021C80BC   battle && DESTROYED && to-GY  -> bsearch(list106 0x0226E990, 0x6A)
    0x021C80E0   left the FIELD && to-GY       -> bsearch(list30  0x0226E904, 0x1E)
    0x021C80FE   ONLY IF [sp+0x18] == 0        -> bsearch(mask table 0x0226EC1C, 0x98)

**Scrap Raptor is in none of the three**, so `[sp+0x18]` never arms and the cls2
record is never reached. That is exactly the observed silence — and it is the
same absence my Strike-1 check measured. I **wrongly dismissed it** because the
five Scrap templates are also absent, instead of treating their absence as the
anomaly that needed explaining.

**The paths are PAIRED with the record.** GK Recruiter uses Sangan's matched
pair: registration **+ `+0C = 0` and `+10 = 0`**. Its header records that MIXING a
registration with a non-zero `+0C` (Garsem's `0x0224A115`) caused a **freeze**.
My record has `+0C = 0x021F05A9`, `+10 = 0x021E51E5` and no registration — the
unpaired combination.

⚠️ Also: the donor must stay **OUT** of list30/list106, because arming
`[sp+0x18]` makes the dispatcher **skip the mask lookup entirely** (the bug an
earlier Eclipse Wyvern build hit).

## ⚠️⚠️ THE SECTION BELOW IS WRONG — DISPROVEN BY THE USER 2026-09-22

**"The stock Scrap clause is dead in OTN" is FALSE.** The user supplied four
savestates on the STOCK rom that disprove it outright:

- `rom.ml2 -> rom.ml3` — **Scrap Beast destroyed by a Scrap card: TRIGGERS.**
  The acting descriptor at `[0x0229A9FC+0x50]` reads
  **`{cid 0x22F8, side 0, zone 0x0E (GY), event 0x1D, class 2}`**.
- `rom.ml4 -> rom.ml5` — Scrap Orthros destroyed by **Dark Hole: does NOT trigger**.

The reasoning kept below is preserved only as provenance for how the error was
made. **The real root cause is in the next section.** My error: I inferred
"absent from every cid table => unwired" from a sweep, when `donor_scan`'s own
docstring warns that a per-cid switch encoding cids as `base +/- imm` off a pool
literal **leaves no occurrence at all**. Absence from the tables was evidence only
that they are not wired *by data*.

## *** THE ACTUAL ROOT CAUSE: SCRAP RAPTOR HAS NO LEAVE ARM ***

A leave-field trigger fires only if the dispatcher arms `[sp+0x18]`; unarmed, it
never builds the `{zone 0x0E, event 0x1D, class 2}` descriptor, so
`find_event_handler` is never called and the class-2 record is dead weight.
There are **FOUR** arming paths — three data, one pure code:

    list106 0x0226E990 | list30 0x0226E904 | mask table 0x0226EC1C
    + a DEDICATED PER-CID ARM in the leave switch  (leave.per_cid_arm_is_arming_only)

The six Scrap trigger cards use the **fourth**. Evidence: they are absent from
all three data paths, yet Scrap Beast demonstrably triggers, and the leave-switch
region carries pool literals at exactly the right distances —
**`0x021C95CC = 0x2318`, which is Goblin `0x22F7` minus 0x21 and Beast `0x22F8`
minus 0x20** — the classic `base +/- imm` per-cid switch encoding.

**Scrap Raptor (`0x0FF6`) has no arm of any kind**, so the event is never posted.
Proven directly from my own savestate: `rom_scrap_raptor.ml2`'s acting descriptor
is still **`{cid 0x0FF6, zone 0x02, event 0x07, class 3}`** — C1a's own ignition.
No class-2 leave descriptor was ever created. This is independent of `+14`, of
the resolver, and of which card does the destroying.

### Two of my own claims, corrected

- **`find_event_handler` class mapping** (jump table `0x0224A134`, base
  `0x0224A136`): class 0 -> `0x0227E64C`, class 1 -> `0x022860D4`,
  **class 2 -> `0x02275C04`**, class 3 -> `0x02279D74`. So `donor_scan`'s
  "cls2" label for `0x02275C04` is CORRECT, and my momentary claim that it is
  "class 0" was a misreading of the arm ordering. **My record is in the right
  table with the right `+0C` all along.**
- **The `+14` fix was not the cause and not the cure.** The data claim (GY
  searchers carry `0x02235605`, Deck searchers carry 0) is true and worth
  copying, but it did not break or fix anything here. KB fact
  `counter.cls_tail_is_a_target_template_zone_must_match` has been amended to say
  so.

### The fix, and the deviation it forces

Per-cid arms are not stealable (each belongs to a real card), so a donor must buy
its arm from the **mask table** — a count-neutral row in `0x0226EC1C`.

⚠️ **The mask bits cannot express the destroyer's ARCHETYPE**
(`leave.mask_bit_semantics` enumerates all twelve: destroyed / by battle / not by
battle / by card effect / to GY / face-up / face-down / you control it / opponent
did it / left field / ...). So "destroyed by the effect of a **Scrap** card" is
**not expressible as a mask row**. Closest is **`0x0E05`** (Seed of Flame
`0x1F8E`, "destroyed by a card effect") — **WIDER than printed**.

## *** C2 REBUILT 2026-09-22 — EXACT, NO DEVIATION *** (awaiting in-game test)

The destroyer IS reachable, and Konami's own test was sitting in the arm all
along. Disassembling the stock Scrap leave arm at `0x021C92E6`:

    ldr r0,=0x0229A9FC ; ldr r0,[r0,#0x50]   ; the ACTING descriptor
    cmp r0,#0 ; beq skip
    bl  0x021D2D78                            ; -> the DESTROYER's cid
    str r0,[sp,#8]
    ldr r0,[sp,#0x90]  ; DESTROYED?           (== mask bit 0x0400)
    ldr r0,[sp,#0x144] ; destination is GY?   (== mask bit 0x0800)
    ldr r0,[sp,#8]
    bl  0x02023EE4                            ; has_set_code(destroyer, "Scrap")
    movs r0,#1 ; b 0x021C93CE                 ; ARM [sp+0x18]

`0x021D2D78` takes a descriptor pointer, and the arm feeds it the **acting
descriptor global `0x0229A9FC+0x50`** — which during a destroy resolution is the
DESTROYING effect's descriptor. That global is reachable from anywhere, so the
archetype test can be reproduced outside the dispatcher's frame.

**So the clause splits cleanly in two:**

| piece | how | what it covers |
|---|---|---|
| **L** mask row `{0x0FF6, 0x0C00}` in `0x0226EC1C` | pure DATA, puzzle-safe | `0x0400` destroyed \| `0x0800` to-GY — the arm's two non-archetype tests, and it ARMS `[sp+0x18]` |
| **K** `CAVE_SR_C2COND` ov5 stub at cls2 `+0C` | 40 B Thumb-1 | the archetype test: acting desc -> `0x021D2D78` -> `0x02023EE4`, then chains the native availability gate `0x021F05A8` |

Together they reproduce the printed text **exactly** — "destroyed by the effect
of a 'Scrap' card and sent to your GY". **The wider-than-printed deviation I
proposed earlier is NOT needed and was not taken.**

Record is now Gravekeeper's Recruiter's proven mask-path shape with the archetype
test folded into `+0C`:

    cls2 {0x0FF6, +04=0x02207EF5, +08=0, +0C=0x023A1385, +10=0, +14=0}
    mask {0x0FF6, 0x0C00}    (dropped phantom 0x0E41)

`+10 = 0` matches BOTH mask-path precedents (Scrap Dragon and GK Recruiter);
the `0x021E51E5` the code-arm family uses was dropped with it.

Asserted at build time and in `verify()`: the donor stays OUT of list30/list106
(being in either arms `[sp+0x18]` and makes the dispatcher **skip** the mask
lookup — the Eclipse Wyvern bug), and the stock Scrap arm still makes both calls
this stub copies.

    data/over_the_nexus/working/rom_scrap_raptor.nds
    129,525,896 B  sha256 99d3d91d2d1f5d4dba7905285cdec2ec0144edf706eb1ee665cfc7492cbd93ec
    verify() 55/55 OK

Stub disassembled from the built ROM: plain `BL`s (no BLX-even-literal risk),
`push {r4,lr}` / `pop {r4,pc}` pairs correct, literal resolving to `0x0229A9FC`.

⚠️ Self-destruction is expected to PASS the archetype test: when C1a destroys
Raptor itself the acting descriptor is Raptor's own, destroyer cid = `0x0FF6`,
which is in the Scrap set-code list — so "destroyed by the effect of a 'Scrap'
card" is satisfied. That is the case the user tested.

### *** C2 IN-GAME CONFIRMED BY USER 2026-09-22 ***

User, verbatim: **"Okay that works."** — on the leave-mask + ov5-archetype build
(sha256 `99d3d91d…`), self-destruct route.

⚠️ SCOPE OF THAT SIGN-OFF, deliberately narrow: it confirms **C2 fires and the
Deck search appears**. The user did NOT separately report the non-Tuner filter
contents (oracle 13) or the Dark-Hole negative control (oracle 15), so those
remain **AWAITING IN-GAME TEST** — do not upgrade them without an explicit
statement.

## *** SUPERSEDED / WRONG: "the stock Scrap clause is dead in OTN" ***

The user pointed out that Scrap Orthros carries the same printed clause. Chasing
that produced the decisive control, entirely offline.

`find_event_handler 0x0224A118` switches on **`desc[+5]`, the record class**, and
**class 0 selects the table `0x02275C04`** — so `donor_scan`'s "cls2 record"
label for that table is a MISNOMER; it is the class-0 table, exactly as
[[otn-extra-normal-summon-arch]] says. The table base appears as a literal at
exactly ONE place in ov3 (`0x0224A398`, count `0x0224A39C`), reached from
`0x0224A142`/`0x0224A144` — so there is only one searcher.

Then the control that settles it — within the SAME archetype:

| cid | card | `+0C` | leave subscription | trigger works in stock? |
|---|---|---|---|---|
| 0x230E | Scrap Dragon | `0x0224A115` | **MASK row 126, `0x0C40`** | YES (famous card) |
| 0x23A1 | Scrap Twin Dragon | `0x0224A115` | **MASK row 133, `0x0C40`** | YES |
| 0x2476 | Atomic Scrap Dragon | `0x0224A115` | **MASK row 141, `0x0C40`** | YES |
| 0x22F7 | Scrap Goblin | `0x021F05A9` | **NONE** | — |
| 0x24DE | Scrap Orthros | `0x021F05A9` | **NONE** | — |
| 0x2469 | Scrap Shark | `0x021F05A9` | **NONE** | — |
| 0x238E | Scrap Searcher | `0x021F04FD` | **NONE** | — |

`0x0C40` decodes as *OPPONENT did it | DESTROYED | to GY* — which is verbatim
Scrap Dragon's printed "destroyed by your opponent's card and sent to your GY".
The mask table tracks printed text precisely, so the subscribed cards' triggers
are real.

**CONCLUSION: the main-deck Scrap "destroyed by the effect of a 'Scrap' card and
sent to the GY" clause is NOT IMPLEMENTED in Over the Nexus.** Konami shipped the
class-0 records AND the criteria rows for Goblin / Beast / Soldier / Worm /
Orthros / Shark, but never subscribed those cids to the leave dispatcher, so the
records are unreachable and the clause is inert. Scrap Raptor's C2 was cloned
from that family — **faithfully, including its inertness.** Nothing was ever
going to fire.

(42% of all 697 class-0 records are subscribed; class 0 serves many event codes,
so an unsubscribed record can still fire on a NON-leave event. For a LEAVE event
subscription is required, and the Scrap Synchros prove it inside this archetype.)

⚠️ **`0x0224A115` is NOT a condition at all**: `movs r0,#2 ; bx lr`. An
unconditional yes. So the GK Recruiter freeze ("mixing list30 membership with
Garsem's 0x0224A115") was about that specific LIST pairing, not about this
function being unsafe — Scrap Dragon pairs `0x0224A115` with a MASK row happily.

### The fix, and the deviation it forces

Same-archetype template: **Scrap Dragon's configuration** — a count-neutral
leave-mask row + `+0C = 0x0224A115`, `+10 = 0` (its class-0 record is
`+04=0x02207191 +08=0 +0C=0x0224A115 +10=0 +14=0x02235605`). Keep the criteria
row and the ov5 non-Tuner handler, both proven correct by the savestate.

Mask for Scrap Raptor: **`0x0E05`** = `0x0800` to GY | `0x0400` DESTROYED |
`0x0200` by a CARD EFFECT | `0x0004` left the field | `0x0001` you control it.
That is Seed of Flame `0x1F8E`'s row, printed "destroyed by a card effect".

⚠️ **DEVIATION, NEEDS THE USER'S DECISION — this one is WIDER than printed.**
The mask has no archetype bit and the destroyer's identity is not among its
inputs (`leave.mask_bit_semantics` lists all 12 bits), so "by the effect of a
**Scrap** card" cannot be expressed. C2 would fire on destruction by ANY card
effect while you control it — including the opponent's Dark Hole / Raigeki.
Every deviation accepted on this card so far has been NARROWER; this is the
first that would make it stronger.

## The unexplained anomaly — RESOLVED ABOVE; original reasoning kept for provenance

The five Scrap templates carry `+0C = 0x021F05A9` / `+10 = 0x021E51E5` and have
**no leave registration either**. Under the mechanism above their C2 clause could
not fire in the stock game. Two readings, leading to different work:

- **(i) The stock Scrap "destroyed by a Scrap card" clause is DEAD in OTN** —
  Konami shipped the records but never wired the trigger. Then cloning it was
  doomed from the start and C2 must be rebuilt on the GK Recruiter recipe.
- **(ii) A fourth dispatch path** exists for "destroyed by a card effect" that
  bypasses the leave dispatcher; the Scrap family rides it and `0x0FF6` does not.

**Cheapest discriminator, one duel:** destroy a stock **Scrap Goblin / Beast /
Soldier / Worm / Orthros** with a Scrap card's effect and see whether IT offers
its GY search. This was check 6 in `_build_scrap_raptor.py`'s oracle and has never
been run. Fires => (ii). Silent => (i).

## Next Experiment (CURRENT — supersedes every earlier "Next Experiment" above)

**Trace r5 from `0x022619DC` to `0x02261ED6`.** This is the one unknown blocking
C1b. The granter-announce at `0x02261E9A..0x02261ED0` — the only hard requirement
that the granter be on the field — is reached **only when the counter
`0x021B9514` returns non-zero** (`cmp r0,#0 ; beq 0x02261ED6` at `0x02261E96`).
If Raptor's grant does not touch the counter, that branch is skipped. But
`0x02261ED6` does `str r0,[r5,#0x34]` and r5 comes from earlier in the enclosing
function (`0x022619DC`, `push {r1-r7,lr}`, running past `0x02261F00`).

- r5 valid regardless of the granter -> **option C is a small build** (steps 1-4, 6).
- r5 depends on locating the granter on the field -> **the announce path must be
  rebuilt for Raptor** and step 5 is a substantial ov5 stub.

⚠️ `thumb.stack_based_switch` applies — this state machine uses `base ± imm`
comparisons off pool literals; a register-only simulator picks the wrong leaf.

The exact command is in `PROMPT_scrap_raptor_clause1b.md`.

## KB contributions (2026-09-22)

- `counter.nontuner_callback_is_the_only_one`
- `counter.tuner_flag_is_card_type_not_genre_bit_35`
- `counter.cls_tail_is_a_target_template_zone_must_match`
  (⚠️ its CAUSAL half was wrong and is amended in place — the `+14` change did
  not fix C2; the missing leave arm did)
- `event.leave_arm_is_required_and_has_a_fourth_code_only_path` — the big one:
  four arming paths, the fourth is CODE and invisible to every cid sweep.

On arrival expect:

    verify_knowledge   -> TOTAL 538 facts:  495 PASS   0 FAIL   43 UNVERIFIED
    check_allocations  -> 271 ov5 slots (250 live), 288 phantom claims,
                          12 ov3 dead-code claims (38 B free)  [OK] ledger in sync

## Status (2026-09-22, end of session)

- **C0 — IN-GAME CONFIRMED BY USER 2026-09-22.** Identity, Tuner via
  `card_type 33`, "Scrap" set-code membership, with **Scrapyard** reaching it on
  the duel path.
- **C1a — IN-GAME CONFIRMED BY USER 2026-09-22.** Activates, destroys the target
  (including itself), once-per-turn holds, refuses opponent monsters.
- **C2 — IN-GAME CONFIRMED BY USER 2026-09-22** ("Okay that works"), after two
  failed builds. ⚠️ Narrow sign-off: it confirms the search APPEARS. The
  **non-Tuner filter contents** (oracle 13) and the **Dark-Hole negative control**
  (oracle 15) were NOT separately reported and remain AWAITING IN-GAME TEST.
- **C1b — NOT BUILT.** Mechanism fully mapped, option C chosen by the user,
  7-step plan written, one unknown open (see Next Experiment).

    data/over_the_nexus/working/rom_scrap_raptor.nds
    129,525,896 B  sha256 99d3d91d2d1f5d4dba7905285cdec2ec0144edf706eb1ee665cfc7492cbd93ec
    verify() 55/55 OK

**NOT wired into `steps.STEPS` / `_verify_all_patches.SHIPPED`** — single-card
ROM only until the user says ship.

Continuation prompt: **`PROMPT_scrap_raptor_clause1b.md`**

## *** STEP 5 RESOLVED 2026-09-22 (session 2): r5 IS A FIXED GLOBAL ***

**The open question is CLOSED. The announce CAN be skipped. Option C is the
SMALL build (steps 1-4, 6 — step 5 is one branch, not a rebuilt path).**

PROVEN by full disassembly of `0x022619DC..0x02261F00` (stock
`data/over_the_nexus/working/rom.nds`, overlay 3, Thumb).

### r5 is loaded in the PROLOGUE and is granter-independent

    0x022619DC push {r1, r2, r3, r4, r5, r6, r7, lr}
    0x022619DE ldr  r4, [pc, #0x2e4]    ; = 0x02298A28   the acting descriptor
    0x022619E0 ldr  r5, [pc, #0x2e4]    ; = 0x0229DD94   <-- FIXED GLOBAL

The dispatch chain from the prologue to the Dverg arm is a straight fall-through
of archetype predicates on `desc[+0xE]` (the HAND card being summoned), and
**not one of its instructions writes r5**:

    0x022619E4 bl 0x0202381C ; cmp r0,#0 ; beq -> 0x02261AF8
    0x02261AF8 bl 0x020238D4 ; cmp r0,#0 ; beq -> 0x02261C9A
    0x02261C9A bl 0x02023BC8 ; cmp r0,#0 ; beq -> 0x02261D7A
    0x02261D7A bl 0x02023B60 ; cmp r0,#0 ; beq -> 0x02261E3C
    0x02261E3C bl 0x02023FC4 ; (is_nordic)  the DVERG arm

Inside the Dverg arm r5 is first written only at `0x02261E9A`
(`ldr r5,=0x245B`) and `0x02261EC0` (`ldr r5,[r6,r3]`) — **both on the announce
path**. On the skip path r5 is still `0x0229DD94`, so

    0x02261ED6 movs r0,#1 ; str r0,[r5,#0x34]      ==  [0x0229DDC8] = 1

is a plain flag write to a global state struct. **No granter, no slot, no field
presence.**

### What that flag is: the announce ACK

`[0x0229DD94 + 0x34]` is the "announce completed / proceed" flag. Same shape in
all four arms of this machine (`0x02261A26`, `0x02261BB6`, `0x02261C62`,
`0x02261D5C`, `0x02261E1C`, `0x02261ED6`). Phase `0x64` consumes it:

    0x02261EE2 ldr  r0,[r5,#0x34]
               cmp  r0,#0 ; beq -> 0x02261EEC    ; 0 = bail, phase := 0
               ldr  r0,=0x245B ; strh r0,[r4,#0x12]   ; record the GRANTER cid
    0x02261EEC movs r0,#0 ; strh r0,[r4,#0x24]        ; phase := 0

So the announce path and the skip path differ **only** in who sets the flag: the
async UI announce `0x0219AA50(side, granter, 0xE2, ref)`, or the `str` itself.
Everything functional happens afterwards in phase `0x64`.

### Consequence for the build

Raptor's arm = Dverg's arm with two edits:

1. the `on_field(side, 0x245B)` test at `0x02261E68` replaced by a **grant-node**
   test (the Double-Summon-shape node keyed `0x0FF6`), and
2. the counter branch at `0x02261E90..0x02261E98` **not taken at all** — write
   the ACK flag unconditionally and fall to phase `0x64`.

Edit (2) also closes a hazard that a naive copy of Dverg's arm would open: with
the `on_field` test removed, a NON-zero counter would reach `0x02261EA0`
(`bl 0x021ABE4C` -> negative when Raptor has left) and then
`muls r3,#0x14 ; ldr r5,[r6,r3]` would index `player+0x34` with a **negative**
slot and announce a garbage card ref. Skipping the announce unconditionally
avoids it.

**COST: the 0xE2 announce event is not posted for Raptor's grant.** That is the
visual "<granter>'s effect!" attribution. Cosmetic, and unavoidable — the card
it would point at may no longer be on the field, which is precisely the user's
ruling ("the grant has to outlive the granter"). **Flagging it for user
approval before the build.**

### Still UNVERIFIED (do not assume)

- How a **third** cid joins this arm — `0x245B` is a hardcoded pool literal at
  `0x02261E62` / `0x02261E9A` / `0x02261EE8`. `patch_ninishi` already made this
  arm serve two cids; its hook shape has NOT been re-read this session.
- Steps 1, 3, 4, 6 are unchanged and unbuilt.

### The SITE-3 pool word — re-verified this session, and why Raptor CANNOT reuse it

`patch_ninishi`'s self-modifying-pool trick is real and its reader count is
exact. Re-proved by scanning **every 2-byte-aligned halfword in ov3** that
encodes `ldr rX,[pc,#imm]` (T1, `0x4800..0x4FFF`) and resolving its literal
address — a linear capstone disasm desyncs on this overlay and finds nothing, so
the alignment-agnostic scan is the right instrument:

    pool word @0x02261F84 = 0x0000245B
      0x02261E62  ldr r6,[pc,...]
      0x02261E9A  ldr r5,[pc,...]
      0x02261EE8  ldr r0,[pc,...]

**Exactly three readers, all inside the Dverg arm** — as `patch_ninishi`'s
docstring claims. Ninishi therefore serves two granters with ZERO cloned arm
code: `CAVE_NS_PRED` answers the predicate and writes the matching granter cid
into `0x02261F84`, and the arm body runs unmodified.

**That trick does not extend to Raptor.** It reuses the arm body *verbatim*, and
the body contains the two things Raptor must not do:

    0x02261E68  bl 0x021ABE4C   ; on_field(side, granter) ; blt -> bail
    0x02261E92  bl 0x021B9514   ; the counter ; beq -> 0x02261ED6 (skip announce)

The first is precisely the on-field requirement the user REJECTED. So Raptor
needs the body to behave differently for its own granter cid.

**The cheap way — two single-site BL retargets, NOT a cloned arm** (the
docstring's own fallback was "clone the arm", ~0xB8 B; this is ~0x20 B):

| site | 4 B hook | ov5 stub behaviour |
|---|---|---|
| `0x02261E68` | `bl 0x021ABE4C` | pool word == `0x0FF6` -> answer from the GRANT NODE, return 0; else tail-call the real `on_field` |
| `0x02261E92` | `bl 0x021B9514` | pool word == `0x0FF6` -> return **0** (forces the announce-skip at `0x02261ED6`); else tail-call the real counter |

Both are **single call sites inside the arm**, so Nordic and Karakuri are
unaffected as long as the stub branches on `0x02261F84`. Safe because:

- the `on_field` return at `0x02261E68` is consumed **only** by the `blt` — r0 is
  immediately reloaded at `0x02261E70` (`ldrh r0,[r4]`), so returning 0 is inert;
- forcing the counter to 0 makes `0x02261EA0`'s slot dereference unreachable for
  Raptor, which is the same hazard closed above.

### Step 2 (relocating Ninishi's five stubs) is probably AVOIDABLE

Headroom re-read from `ov5_cave.py` (quoted, not recalled):

    CAVE_NS_ARM   = 0x0239EBF0  # 0x70 B
    CAVE_NS_SPENT = 0x0239EC60  # 0x20 B
    CAVE_NS_PRED  = 0x0239EC80  # 0x30 B
    CAVE_NS_MATCH = 0x0239ECB0  # 0x20 B
    CAVE_NS_FIELD = 0x0239ECD0  # 0x90 B
    CAVE_FREE     = 0x023A13B4

Still contiguous, so still zero headroom — but **growing them in place is not the
only option**. Raptor can take FRESH stubs from `CAVE_FREE` that **tail-chain
into** Ninishi's existing ones: the hook at `0x02261E3E` points at a new Raptor
predicate stub, which answers "Scrap" itself and otherwise tail-calls
`CAVE_NS_PRED` unchanged. Same for SITE 1 / SITE 4.

That leaves **every byte of the in-game-confirmed Ninishi stubs untouched** and
replaces the "mechanical but touches a confirmed card" step with a chain.

⚠️ Both designs create the SAME patch-order dependency on the shared 4-byte
hooks (`otn-shared-hook-lift-prove-by-execution`): whichever module installs
second must chain to, not overwrite, the first. Step 7 (prove the lift by
execution over BOTH patch orders) is required either way.

**Not yet decided — needs the user.** See the two questions at the end of this
section.

### USER RULINGS 2026-09-22 (session 2) — both decisions APPROVED

1. **The skipped 0xE2 announce is ACCEPTED** as a deviation. Raptor's arm forces
   the counter to 0 so `0x02261E9A..0x02261ED0` is never reached. Recorded
   honestly: I did **not** prove the 0xE2 event is cosmetic (`0x0219A9F0` is
   undisassembled) — the user accepted it on the reasoning that the stock path
   already skips the same announce whenever the base Normal Summon is spent,
   which is the main C1b scenario.
2. **CHAIN, do not relocate.** `patch_ninishi`'s five `CAVE_NS_*` stubs are **not
   to be moved or rewritten**. Raptor takes fresh stubs from `CAVE_FREE` that
   answer "Scrap" themselves and **tail-call Ninishi's stubs unchanged** for the
   Nordic/Karakuri answer. Step 2 of the original 7-step plan is therefore
   RETIRED.

**Revised build plan (supersedes the 7-step plan for everything except step 7):**

| # | step | hook | stub |
|---|---|---|---|
| 1 | C1a's resolver posts the grant node keyed `0x0FF6` | — | extend `CAVE_SR_C1COST` or a new stub |
| 3 | SITE 1 "which granter permits this hand card?" | `0x021B9634` (already Ninishi's) | chain -> `CAVE_NS_ARM` |
| 4 | SITE 3 predicate + pool-word write | `0x02261E3E` (already Ninishi's) | chain -> `CAVE_NS_PRED` |
| 5a | SITE 3 on_field -> grant-node test | `0x02261E68` **(fresh, unclaimed)** | new |
| 5b | SITE 3 counter -> force 0 | `0x02261E92` **(fresh, unclaimed)** | new |
| 2' | SITE 2 "is the extra summon spent?" | `0x021B9F9C` (already Ninishi's) | chain -> `CAVE_NS_SPENT` |
| 6 | SITE 4 consume the grant | `0x0226515C` (already Ninishi's) | chain -> `CAVE_NS_MATCH` |
| 7 | prove the lift by EXECUTION over both patch orders | — | required, unchanged |

Four of the six hooks are **already owned by `patch_ninishi`**, so this is a
shared-hook lift: whichever module installs second must chain, not overwrite.
`0x02261E68` and `0x02261E92` are the only fresh hook sites.

### ⚠️ CORRECTION to the revised plan, same session — `0x02261E68` is NOT a fresh hook

I wrote above that `0x02261E68` and `0x02261E92` were "the only fresh hook
sites". **`0x02261E68` is wrong.** `patch_ninishi` already owns it:

    FIELD_CALL_SITES = (0x02261E68, 0x02261EA0, 0x02265164)

— every `bl 0x021ABE4C` in the granter machinery, all three retargeted to
`CAVE_NS_FIELD`. Caught before writing any Thumb, by grepping each site against
the whole repo rather than trusting the plan.

**Ownership of every site Raptor needs (grepped 2026-09-22, both the
`finished_patches` original AND the migrated `otn_enhanced/
patches/ninishi.py` — `ninishi` is in `steps.MIGRATED`, so there are TWO copies
to keep in step):**

| site | what | owner |
|---|---|---|
| `0x021B9634` | SITE 1 arm entry | `patch_ninishi` -> `CAVE_NS_ARM` |
| `0x021B9F9C` | SITE 2 spent-check tail | `patch_ninishi` -> `CAVE_NS_SPENT` |
| `0x02261E3E` | SITE 3 predicate | `patch_ninishi` -> `CAVE_NS_PRED` |
| `0x02261E68` | SITE 3 on_field | `patch_ninishi` -> `CAVE_NS_FIELD` |
| `0x02261EA0` | SITE 3 announce on_field | `patch_ninishi` -> `CAVE_NS_FIELD` |
| `0x0226515C` | SITE 4 granter match | `patch_ninishi` -> `CAVE_NS_MATCH` |
| `0x02265164` | SITE 4 on_field | `patch_ninishi` -> `CAVE_NS_FIELD` |
| `0x02261F84` | SITE 3 granter pool word | `patch_ninishi` (self-modified) |
| **`0x02261E92`** | **SITE 3 counter** | **UNCLAIMED — the only fresh site**

So C1b is **one fresh hook + five chained stubs**, and step 5a folds into the
`CAVE_NS_FIELD` chain rather than needing its own hook. `CAVE_NS_FIELD` already
has exactly the right shape to chain into — *"for any cid other than the donor
it TAIL-CALLS the native function"* — Raptor adds a third arm that answers from
the **grant node** instead of scanning the field at all.

### The chaining contracts — read from `patch_ninishi`'s stub builders this session

How each Ninishi stub exits decides how Raptor chains into it. Read, not assumed:

| stub | exit | how Raptor chains |
|---|---|---|
| `CAVE_NS_ARM` | `POP {R3-R7,PC}` — the **HOST's** epilogue, LR is dead | Raptor tests Scrap first, else **`bl NS_ARM`** as a tail-jump (clobbering the dead LR is safe; NS_ARM pops the host frame and returns past Raptor) |
| `CAVE_NS_SPENT` | `POP {R3-R7,PC}` — host epilogue | same tail-jump |
| `CAVE_NS_PRED` | `push {lr} … pop {pc}` | `push {lr} ; bl NS_PRED ; pop {pc}` |
| `CAVE_NS_FIELD` | `bx lr` (it replaces `bl 0x021ABE4C`) | `push {lr} ; bl NS_FIELD ; pop {pc}` |
| `CAVE_NS_MATCH` | `bx lr`, **and the host reads both Z and r1** | must NOT use `bl` (it would eat the LR that `bx lr` returns through) and must not disturb Z: `ldr r2,=NS_MATCH\|1 ; bx r2` ⚠️ the literal MUST have bit 0 set — see `thumb-blx-even-literal-footgun` |

⚠️ Use `pop {pc}`, never `pop {..,lr}` — see `thumb-pop-into-lr-footgun`.

The one fresh hook's before-bytes, read from the stock ROM:

    0x02261E90: 60 88          ldrh r0,[r4,#2]
    0x02261E92: 57 f7 3f fb    bl 0x021B9514        <- the 4 B Raptor claims

### ⚠️ NEW OPEN QUESTION — the grant node and the spent node COLLIDE

`NODE_QUERY = 0x021A1430` and `PLAYER_SLOT = 0x0B`. For Dverg/Ninishi the two
states are encoded as:

- **grant exists** = the granter is ON THE FIELD (`ON_FIELD 0x021ABE4C`)
- **grant spent**  = a kind<6 node on slot `0xB` keyed by the granter cid,
  queried with `0x021A1430` (`NS_ARM` arm 1: `beq hit`, i.e. node ABSENT = available)

Raptor has no field presence, so its **grant** must itself be a node keyed
`0x0FF6` on slot `0xB`. **That is the same query `NS_ARM` uses to mean "spent".**
Posting the grant would immediately read as spent — the card would never work.

The Double Summon path already distinguishes the two, and it does it by QUERY,
not by key (from the `0x021B9514` disassembly banked earlier):

    node(side, 0xB, 0x1C33)                  ; 0x021A1430 -> the GRANT exists
    0x021A14E8(side, 0xB, 0x1C33, 2)         ; sub-kind 2 -> the grant is SPENT

Same slot, same key, **two different query functions**. So Raptor should use
`0x021A1430` for the grant and `0x021A14E8(...,2)` for spent.

**UNPROVEN, and I will not guess it:** what `r2` means in
`0x021D2584(side, cid, r2, r3)` — the poster. Double Summon's resolver passes
`r2 = 1 | ((r5 & 0xF) << 4)`, `r3 = 0`; `patch_ninishi` SITE 4 passes
`0x021D2584(side, cid, 1, 0)` and that produces a node `0x021A1430` can see.
If `r2 = 1` posts a node visible to BOTH queries, Raptor needs a different `r2`
for the grant than for the spent mark, and nothing in hand says which.

**NEXT EXPERIMENT (exact):** disassemble `0x021D2584` and `0x021A14E8` and
determine the field that separates a plain node from a sub-kind-2 node — i.e.
which `r2`/`r3` posts a node that `0x021A1430` sees but `0x021A14E8(...,2)` does
not, and which posts one that both see. Everything else in C1b is designed and
unblocked; this is the last unknown before Thumb gets written.

## *** THE NODE COLLISION IS RESOLVED — it is a KIND field *** (2026-09-22, session 2)

All four functions disassembled from the stock ROM this session.

### The two queries are the SAME list through two lenses

Both are thin wrappers that resolve `(side, slot)` to a list head
(`0x0229ACD2 + 0xB3C*(side&1)`, stride 0x14) and hand it to a walker over nodes
at `0x0229D33C`, **stride 0xA**:

    node[+0] = key (u16)   node[+2] = kindword   node[+4] = key2   node[+8] = next

`0x021A1430(side, slot, key)` -> **WALK_A `0x021A1238`**:

    ldrh r5,[r3,#2] ; lsls #0x1C ; lsrs #0x1C   ; kind = node[+2] & 0xF
    cmp  r5,#6 ; bhs next                       ; kind < 6 required
    ldrh r5,[r3]   ; cmp r5,r1 ; bne next       ; key match
    -> HIT                                      ; ** KIND-AGNOSTIC **

`0x021A14E8(side, slot, key, kind)` -> **WALK_B `0x021A1268`**: byte-identical
walk **plus one extra compare**:

    cmp r7,r2 ; bne next                        ; kind == the r3 argument

**So: same node list, same key — WALK_A finds a node of ANY kind < 6, WALK_B
finds one of EXACTLY that kind.** That is the whole mechanism, and it is what
lets Double Summon keep "granted" and "spent" on one key.

### The poster carries the kind as a BYTE

`0x021D2584(r0=side, r1=key, r2=kindword, r3=extra)` is a shim that only inserts
the slot:

    r1 = 0xB ; r2 = key ; r3 = <the r2 arg> ; bl 0x021C479C   ; [sp] = <the r3 arg>

`0x021C479C(side, slot, key, kindword, extra)` packs and posts a duel message:

    r0 = 0x35 | (side ? 0x8000 : 0)        ; message opcode 0x35
    r1 = ((r3 & 0xFF) << 8) | (r1 & 0xFF)  ; KINDWORD in the high byte, SLOT in the low
    bl 0x021C3BC8(op, packed, key, extra)

So the third argument of `0x021D2584` **is** the node's `+2` byte. That matches
Double Summon's resolver passing `r2 = 1 | ((r5 & 0xF) << 4)` exactly:

    node[+2] = kind | (turn-countdown << 4)

— low nibble the kind, high nibble the countdown, as `otn-attached-effect-rider`
already recorded. Double Summon posts **kind 1, countdown 0**.

⚠️ **GRADING: ANCHORED, not VERIFIED.** The argument flows positionally into a
byte whose shape matches `node[+2]` and matches the existing memory note, but I
did **not** trace opcode `0x35`'s handler to the actual node write. Do not
upgrade this without that trace.

### What Raptor does with it

| state | post | query |
|---|---|---|
| grant exists | `0x021D2584(side, 0x0FF6, 1, 0)` — kind 1, from C1a's resolver | `0x021A1430(side, 0xB, 0x0FF6)` |
| grant spent | `0x021D2584(side, 0x0FF6, 2, 0)` — kind 2, from SITE 4 | `0x021A14E8(side, 0xB, 0x0FF6, 2)` |

**The collision is avoided by KIND, on a single key — exactly Double Summon's
convention, not a new invention.**

⚠️ Raptor's arms must therefore use **`0x021A14E8(...,2)`** for the spent test,
NOT the kind-agnostic `NODE_QUERY 0x021A1430` that Ninishi's arms use — the
kind-agnostic query would see Raptor's own kind-1 grant node and report the
grant spent the instant it was made. This applies to Raptor's chained arms at
**SITE 1** and **SITE 2**. Ninishi's own arms keep `0x021A1430` and are untouched.

## C1b IS NOW FULLY DESIGNED AND UNBLOCKED — nothing is left to reverse-engineer

Every unknown that blocked this clause is closed. No Thumb written yet.

### ⚠️ CORRECTION to my own grading above — the KB already had this, VERIFIED

I graded the kind-byte mechanism ANCHORED because I had not traced opcode `0x35`
to the node write. **I did not need to: `rider.node_writer_and_kind_byte` is an
existing VERIFIED fact that already closes it**, and closes it better than my
inference did. Quoted:

> `0x0219F190(r0 = side, r1 = slot, r2 = kind BYTE, r3 = key, [caller sp+0] =
> param)` … fills the node: `[+0] = key`, `[+2]` low nibble = `kind & 0xF`,
> `[+2]` bits 4..7 = `(kind & 0xF0) >> 4` … **THE HIGH NIBBLE OF THE KIND BYTE IS
> A PER-TURN COUNTDOWN** … A caller passing kind = `0x12` therefore creates a
> kind-2 node that survives exactly one turn boundary.
>
> THE QUEUED ROUTE to the same writer is `0x021C479C(side, slot, key, kind byte,
> …)`, which packs animation command `0x35 | (side ? 0x8000 : 0)` … its handler
> `0x021C3E68 -> 0x021BE044` unpacks it … and calls `0x0219F190` with the FULL
> kind byte intact.

So the path I stopped short of is `0x021C3E68 -> 0x021BE044 -> 0x0219F190`, and
the kind byte arrives intact. **Upgrade the grading: the grant/spent design rests
on a VERIFIED fact, not an inference.** Lesson for the next session — I nearly
authored a duplicate of an existing VERIFIED fact; grep `author_facts.py` for the
prefix (`rider.`, `node.`, `summon.`) BEFORE writing one up.

### KB contribution this session

**`rider.family1_has_a_kind_exact_lens`** (VERIFIED, new, passes its proof) —
the one genuinely new piece. `rider.two_walker_families` documents `0x021A1430`
as *the* family-1 query; it misses `0x021A14E8 -> 0x021A1268`, the kind-EXACT
lens on the same list, which is precisely what lets one key carry both "granted"
and "spent". The fact also records the trap that would have killed C1b: Ninishi's
arms use the kind-agnostic query as their SPENT test, so Raptor must not.

    verify_knowledge -> TOTAL 539 facts:  496 PASS   0 FAIL   43 UNVERIFIED

## Next Experiment (CURRENT — supersedes every earlier one in this file)

**None outstanding. C1b is fully designed; the next session WRITES THUMB.**
Build order, all of it proven above:

1. **C1a's resolver posts the grant.** `0x021D2584(side, 0x0FF6, 1, 0)` — kind 1,
   countdown 0. Extend `CAVE_SR_C1COST` (or a new stub if it is out of room —
   measure, do not assume).
2. **SITE 1** `0x021B9634` — chain a Raptor arm ahead of `CAVE_NS_ARM`:
   `is_scrap(hand cid)` AND `0x021A1430(side, 0xB, 0x0FF6)` (grant exists) AND
   NOT `0x021A14E8(side, 0xB, 0x0FF6, 2)` (not spent) -> return `0x0FF6`;
   else tail-jump to `CAVE_NS_ARM`. Exit via `POP {R3-R7,PC}` (host epilogue).
3. **SITE 2** `0x021B9F9C` — chain ahead of `CAVE_NS_SPENT`, spent test
   `0x021A14E8(...,2)`.
4. **SITE 3 predicate** `0x02261E3E` — chain ahead of `CAVE_NS_PRED`: if Scrap,
   write `0x0FF6` into the pool word `0x02261F84` and return 1; else
   `push {lr} ; bl CAVE_NS_PRED ; pop {pc}`.
5. **SITE 3 on_field** `0x02261E68` — chain ahead of `CAVE_NS_FIELD`: for pool
   word `0x0FF6` return 0 (the value is consumed ONLY by the following `blt`;
   r0 is reloaded at `0x02261E70`); else tail into `CAVE_NS_FIELD`.
6. **SITE 3 counter** `0x02261E92` — **the one fresh hook**, before-bytes
   `57 f7 3f fb`. For pool word `0x0FF6` return **0**, forcing the announce-skip
   at `0x02261ED6`; else tail into the native `0x021B9514`.
7. **SITE 4** `0x0226515C` — chain ahead of `CAVE_NS_MATCH`, matching `0x0FF6`
   too. ⚠️ flags AND r1 are both live: `ldr r2,=NS_MATCH|1 ; bx r2`, never `bl`.
   The spent mark it sets must be **kind 2**.
8. **Step 7 of the original plan still stands:** prove the lift by EXECUTION over
   both patch orders (`otn-shared-hook-lift-prove-by-execution`). Six of the
   seven hooks are shared with `patch_ninishi`, which exists in TWO copies
   (`finished_patches/patch_ninishi.py` and the migrated
   `ygo_tools/tools/enhanced_edition_definitive/patches/ninishi.py`) — keep them in step.

Then build `.venv-1/Scripts/python.exe _build_scrap_raptor.py --text`, disassemble
every stub (the `assert_thumb1_only` check misses POP-into-LR and
BLX-to-even-literal), and run the in-game oracle list in
`PROMPT_scrap_raptor_clause1b.md`, **including regression controls 8-11**
(Ninishi, Dverg, Haipa, C2).

## *** BUILD STEP 1 IS ALREADY DONE — C1a's OPT LATCH *IS* THE GRANT NODE ***

Found by reading `patch_scrap_raptor.build_c1_cost` before writing a line of new
Thumb. **No new code is needed to post the grant.**

C1a's cost stub (`CAVE_SR_C1COST`, shipped, and C1a is in-game confirmed
2026-09-22) already does exactly this on activation:

    ldrb r0,[r4,#2]        ; side
    ldrh r1,[r4,#0]        ; cid = 0x0FF6
    movs r2,#1             ; TURNLOG_KIND = 1
    movs r3,#0
    bl   0x021D2584        ; TURNLOG_POST

and C1a's condition reads it back with `0x021A14E8(side, 0x0B, 0x0FF6, 1)` —
**the kind-EXACT lens**, i.e. the module already uses the mechanism
`rider.family1_has_a_kind_exact_lens` describes. Constants, quoted:

    TURNLOG_QUERY = 0x021A14E8   # QUERY(side, 0x0B, cid, kind)
    TURNLOG_POST  = 0x021D2584   # POST(side, cid, kind, 0)
    TURNLOG_KIND  = 1
    TURNLOG_SLOT  = 0x0B
    DONOR_CID     = 0x0FF6

So the node C1b needs as its **grant** is the node C1a already posts, on the same
slot and the same key. And the two conditions are *semantically identical*:

> the grant exists  ⟺  C1a was activated this turn

which is precisely the printed text — *"also, during your Main Phase **this
turn**, you can Normal Summon 1 'Scrap' monster in addition"*.

Three consequences, all favourable:

1. **Step 1 of the build plan is deleted.** Nothing to write, and the posting
   path is already in-game confirmed by C1a working.
2. **The grant automatically outlives Raptor** — it is a player-slot (`0xB`) node
   keyed by cid, never a field lookup. That is the user's ruling, for free.
3. **It automatically expires at the turn boundary** via the kind byte's high
   nibble (countdown 0 -> swept; `rider.turn_sweeper`), so C1b needs no separate
   duration logic.

⚠️ **This makes the kind discipline load-bearing, not merely tidy.** Slot `0xB`
key `0x0FF6` now carries TWO booleans:

| kind | meaning | posted by | queried by |
|---|---|---|---|
| **1** | C1a activated this turn == **the C1b grant exists** | `CAVE_SR_C1COST` (shipped) | `0x021A14E8(side, 0xB, 0x0FF6, 1)` |
| **2** | the extra Normal Summon has been **used** | SITE 4 (to build) | `0x021A14E8(side, 0xB, 0x0FF6, 2)` |

If any Raptor arm uses the **kind-agnostic** `0x021A1430` instead, it sees C1a's
kind-1 latch and reports the grant spent the moment C1a is activated — the extra
summon would never once be offered, and `verify()` would pass. This is exactly
the trap recorded in `rider.family1_has_a_kind_exact_lens`.

**Revised build: 6 chained stubs, 1 fresh hook, 0 new posting code.**

### SITE 4 posts the spent mark with kind 1 — Raptor needs a SEVENTH hook

Disassembled `0x02265140..0x022651A8` this session. The granter arm's spent-post:

    0x0226515A ldrh r0,[r4,#0x12]      ; the granter cid the state machine stamped
    0x0226515C ldr  r1,=0x245B         ; <- SITE4_HOOK (patch_ninishi -> CAVE_NS_MATCH)
    0x0226515E cmp  r0,r1
    0x02265160 bne  0x02265182
    0x02265162 ldrh r0,[r4]
    0x02265164 bl   0x021ABE4C         ; <- patch_ninishi -> CAVE_NS_FIELD
    ...
    0x02265172 ldrh r0,[r4]
    0x02265174 ldr  r1,=0x245B         ; <- patch_ninishi IN-PLACE -> ldrh r1,[r4,#0x12]
    0x02265176 movs r2,#1              ; *** THE KIND: 1 ***
    0x02265178 movs r3,#0
    0x0226517C bl   0x021D2584         ; <- UNCLAIMED. Raptor's 7th hook.

`patch_ninishi`'s in-place edit at `0x02265174` already makes the post key off
`desc[+0x12]`, so for Raptor the key is `0x0FF6` — correct. But the **kind is
hardcoded 1** by the `movs r2,#1` at `0x02265176`, and kind 1 on key `0x0FF6` is
**C1a's once-per-turn latch**, which C1a already posted. Posting it again is a
no-op, so *the extra summon would never be marked spent* and C1b would be
repeatable — while `verify()` passed.

`0x02265176` is a lone 2-byte instruction and cannot branch, so the fix is a
4-byte hook on the **`bl` at `0x0226517C`**: if `r1 == 0x0FF6` set `r2 = 2`, then
tail into the native `0x021D2584`. Both `0x0226517C` and `0x02265176` are
**unclaimed across every module** (grepped, including the migrated ninishi copy).

### FINAL HOOK TABLE for C1b — 7 hooks, 5 chained into `patch_ninishi`, 2 fresh

| # | site | before | Raptor stub | chains to |
|---|---|---|---|---|
| 1 | `0x021B9634` | `bl CAVE_NS_ARM` | `CAVE_SR_NSARM` | `CAVE_NS_ARM` |
| 2 | `0x021B9F9C` | `bl CAVE_NS_SPENT` | `CAVE_SR_NSSPENT` | `CAVE_NS_SPENT` |
| 3 | `0x02261E3E` | `bl CAVE_NS_PRED` | `CAVE_SR_NSPRED` | `CAVE_NS_PRED` |
| 4 | `0x02261E68` | `bl CAVE_NS_FIELD` | `CAVE_SR_NSFIELD` | `CAVE_NS_FIELD` |
| 5 | `0x02261E92` | `bl 0x021B9514` **(stock)** | `CAVE_SR_NSCOUNT` | native `0x021B9514` |
| 6 | `0x0226515C` | `bl CAVE_NS_MATCH` | `CAVE_SR_NSMATCH` | `CAVE_NS_MATCH` |
| 7 | `0x0226517C` | `bl 0x021D2584` **(stock)** | `CAVE_SR_NSPOST` | native `0x021D2584` |

### ⚠️ C1b HARD-DEPENDS ON `patch_ninishi`, and the order is FIXED

Five of the seven before-images are `bl CAVE_NS_*`, i.e. **`patch_ninishi` must
already be applied**. That is a feature, not a problem: asserting those exact
before-bytes turns a missing or mis-ordered dependency into a build-time abort
instead of a freeze in a duel.

- `_build_scrap_raptor.py` must apply `patch_ninishi` **before**
  `patch_scrap_raptor` once C1b lands. It currently does **not** apply it at all,
  so the single-card ROM would chain into an empty cave — **a freeze**. This is
  the single most likely way to break this build; do not skip it.
- When the card ships, its `steps.STEPS` entry must sit **after** ninishi's.
- This supersedes "prove the lift over BOTH patch orders": only one order is
  legal, and it is asserted. Still run the ninishi equivalence check to prove
  Raptor's chain leaves Ninishi's own behaviour identical.

## *** C1b IS BUILT 2026-09-22 (session 2) — AWAITING IN-GAME TEST ***

**NOTHING about C1b is confirmed. `verify()` passing is not in-game confirmation.**

    data/over_the_nexus/working/rom_scrap_raptor.nds
    129,528,968 B
    sha256 b0499257986ea4f9523d008e1ae421de22d6e95e39b0927ae67da9c61bb78d19
    verify() 73 OK / 0 FAIL

    .venv-1/Scripts/python.exe _build_scrap_raptor.py --text

Still **NOT** wired into `steps.STEPS` / `_verify_all_patches.SHIPPED`.

### What was built

Seven ov5 stubs, 252 B total, all disassembled after assembly (the
`assert_thumb1_only` check misses POP-into-LR and BX-to-even-literal, so both
were checked by eye and by assertion):

| stub | addr | used/reserve | role |
|---|---|---|---|
| `CAVE_SR_NSARM` | `0x023A13B4` | 60/64 | SITE 1 granter arm |
| `CAVE_SR_NSSPENT` | `0x023A13F4` | 36/48 | SITE 2 spent check |
| `CAVE_SR_NSPRED` | `0x023A1424` | 36/48 | SITE 3 predicate + pool-word write |
| `CAVE_SR_NSFIELD` | `0x023A1454` | 44/48 | SITE 3 **grant-node lookup** — the clause that makes the grant outlive the granter |
| `CAVE_SR_NSCOUNT` | `0x023A1484` | 32/48 | SITE 3 counter -> announce skip |
| `CAVE_SR_NSMATCH` | `0x023A14B4` | 20/32 | SITE 4 granter match |
| `CAVE_SR_NSPOST` | `0x023A14D4` | 24/32 | SITE 4 spent post, **kind 2** |

`CAVE_FREE` is now `0x023A14F4`. `check_allocations`: **278 ov5 slots, no
overlaps, ledger in sync.**

⚠️ `CAVE_SR_NSCOUNT` was first given `0x20` and assembled to exactly 32 B —
**zero free**, the precise trap that forced `patch_ninishi`'s five stubs to be
relocatable. Bumped to `0x30` before anything was built on top of it.

Verified literals (read back out of the assembled blobs, not assumed):
`0x00000FF6` in all seven, `0x02261F84` in NSPRED/NSCOUNT, `0xFFFFFFFF` in
NSFIELD, and **`0x0239ECB1`** in NSMATCH — `CAVE_NS_MATCH | 1`, **odd**, so the
`bx r1` stays in Thumb (`thumb-blx-even-literal-footgun`).

### The ordering question, closed by disassembly

Raptor's SITE 1 arm is necessarily consulted **before** Ninishi's, because
`CAVE_NS_ARM` exits through the host's `POP {R3-R7,PC}` and can never return to
a caller that wanted to run after it. So on the `r4 = 0` "any card" availability
probe, Raptor can answer where Ninishi would have.

**That is unobservable.** All three callers of `0x021B95C4` were found by
scanning ov3 for BLs to it, and every one consumes the result as a **boolean**:

    0x021B9688  (r1 = 0, the probe)  -> pop {r4,pc}     ; 0x021B9674's tail
    0x0220D672  (r1 = a real cid)    -> cmp r0,#0 ; bne
    0x0225D6FE  (r1 = a real cid)    -> cmp r0,#0 ; bne

None uses the returned granter cid. `0x021B9674` itself returns `1` on the
counter path and a *cid* on the SITE 1 path, so it cannot be a cid to its own
callers either — self-evidencing.

For a **specific** hand card the question does not arise at all: Raptor's arm
requires `has_set_code(cid, "Scrap")`, so a Karakuri or Nordic card falls
straight through to Ninishi.

### ⚠️ HONEST GAPS — what is NOT proven

1. **The EXECUTION proof of the lift is NOT done**
   (`otn-shared-hook-lift-prove-by-execution`). What exists is a structural
   argument plus the caller analysis above. The repo's pattern for this is
   `scratch/*_equiv.py` driving `scratch/thumbemu.py`; note that thumbemu
   *executes* BLs into real engine code, so such a harness needs external-call
   interception (seed `Mem` with `movs r0,#K ; bx lr` bodies at `IS_NORDIC`,
   `IS_KARAKURI`, `SCRAP_SETCODE_THUNK`, `NODE_QUERY_EXACT`, `ON_FIELD`) and a
   pre-seeded 6-word stack frame ending in `MAGIC_LR`, because the SITE 1/2
   stubs exit through a host epilogue they never pushed. **Next session's job if
   the in-game test is ambiguous.**
2. **`patch_ninishi.verify()` no longer passes against a C1b ROM**, by design:
   five of its assertions demand the shared hooks point DIRECTLY at `CAVE_NS_*`.
   The build script now checks the chain targets and ninishi's non-hook card
   data instead, and says so in a comment. If C1b ever ships, decide then
   whether to teach `patch_ninishi.verify()` to accept a lifted hook — **and
   remember there are TWO copies of that module** (`finished_patches/` and the
   migrated `ygo_tools/tools/enhanced_edition_definitive/patches/ninishi.py`).
3. The `0xE2` announce is skipped for Raptor. **User-approved**, and I never
   proved it is purely cosmetic (`0x0219A9F0` is still undisassembled).

### The in-game test

`_build_scrap_raptor.py`'s docstring now carries oracles **17-21** for C1b and
**22-25** as mandatory regression controls (Ninishi, Dverg, Haipa, C2), each with
the failure it distinguishes. Oracle **20** is the decisive one: activate C1a
targeting **Scrap Raptor itself** — the extra Normal Summon must still be
available, because the grant is a player-slot node and never a field lookup.
