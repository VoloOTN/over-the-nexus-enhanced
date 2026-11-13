# Dragon Shrine — findings (session 2026-08-18)

## The card (sourced from scratch/ygoprodeck_cache.json, NOT recall)

> **Dragon Shrine** — Spell Card / Normal
> "Send 1 Dragon monster from your Deck to the GY, then, if that monster in your
> GY is a Dragon Normal Monster, you can send 1 more Dragon monster from your
> Deck to the GY. You can only activate 1 'Dragon Shrine' per turn."

Clauses:
1. **Send 1 Dragon monster from your Deck to the GY.** (mandatory, on activation)
2. **Then, if that monster is a Dragon *Normal* Monster, you *can* send 1 more
   Dragon monster from your Deck to the GY.** (optional, conditioned on 1's result)
3. **You can only activate 1 "Dragon Shrine" per turn.** (hard OPT, name-locked)

Scope: donor **The Puppet Magic of Dark Ruler 0x14C1** (user-chosen). Clause 1
SHIPPED AND **IN-GAME CONFIRMED** (user test, standalone `rom_dragon_shrine.nds`):
the card activates, offers Dragon monsters from the Deck, and sends one to the GY.
Clauses 2 and 3 are **confirmed absent in-game**, as designed and documented
(user: "it is not once per turn"; "when I send a normal dragon it does not let me
mill another dragon"). Both are now IN SCOPE.

## Confirmed (this session)

- **KB is healthy.** `verify_knowledge` = 254 facts, **222 PASS / 0 FAIL /
  32 UNVERIFIED**. Oracles: arm9 yes, ov3 yes, ov5 yes, savestate
  `rom_all_patches.ml2`.

- **Dragon Shrine is NOT in the ROM.** No cid. `patch_card_art.py:104` carries it
  as a commented `CardArt(0xFFFF, 'dragon_shrine', 'dragon_shrine')` wishlist
  entry, and the art asset already exists at
  `data/over_the_nexus/card_arts/dragon_shrine`. A donor is required.

- **Foolish Burial 0x1474 is the exact structural twin of clause 1.**
  Read out of the committed ov3 oracle this session:
  - `cls0[305]` (table 0x0227E64C, stride 24) = `{+04 0x02208DD5 resolver,
    +08 0, +0C 0x021F0B19 condition, +10 0 (NO COST), +14 0 (no target slot)}`
  - `crit[138]` (registry 0x022713C4, stride 12) = `{cid 0x1474, aux 0xFFFF,
    handler 0x0223CAD9, word 0x00000002}`

  Its entire printed effect is those two rows — nothing else.

- **Handler 0x0223CAD9 = "select from the DECK".** Already VERIFIED in the KB
  (`dispatch.criteria_hand_vs_deck_handlers`): 66 rows, zero crossovers, Dark
  Grepher's adjacent same-word pair is the internal control.

- **Word 0x08000002 = "Dragon monster", and it already ships working.**
  `crit[1249] = {0x2359 Dragon Ravine, 0xFFFF, 0x0223CAD9, 0x08000002}`, whose
  printed text is literally *"send 1 Dragon monster from your Deck to the GY"*.
  Top byte 0x08 = race<<3 = Dragon, per `dispatch.criteria_word_race_attribute`.
  So clause 1's criteria row is a byte-for-byte copy of a shipping row.

- **THE KEY FACT: the resolver's per-cid switch DEFAULTS TO "send exactly 1".**
  Disassembled 0x02208DD4 this session. At 0x02208E1A it presets
  `[r5+0x74] = 1` (count) and `[r5+0x78] = 0` (mode), then runs a
  **register-based** compare tree on `ldrh r1,[r4]` (= cid) against PC-relative
  literals — NOT the stack-based-switch footgun, so a static read is safe here.
  Resolved literals @0x0220906C..0x0220907C:

  | cid | arm |
  |---|---|
  | 0x1BFE Snake Rain | count = **4** |
  | 0x1D3E Skreech | count = **2** |
  | 0x228E | count = `desc[+0x18]` |
  | 0x22C3 (= 0x228E + 0x35) | count = **2** |
  | 0x1FCA Colossal Fighter/Assault Mode | mode = 2 |
  | **everything else** | **count = 1, mode = 0** |

  Then `0x02208E6E: bl 0x02243FA8` (the list-zone candidate count) is compared
  against the count; short → message 0xD, return 0x78.

- **The activation condition 0x021F0B18 has the same shape and also defaults to 1.**
  `side = desc[+2] ^ desc[+6]` (matches `dispatch.criteria_probe_side_is_xor_desc6`),
  `movs r4,#1` preset, a two-literal cid switch (4 / 2), then `bl 0x02234E78` and
  the candidate count. Default arm = "needs >= 1 candidate".

  **=> Clause 1 needs ZERO new code.** Any donor cid inherits "send exactly 1
  card from whatever zone its criteria row's handler names."

- **Donor text slots** (measured from `bin2.pac` in `working/rom.nds` this session).
  Text is written **in place only** — `apply_text` silently SKIPS a string longer
  than the donor's slot. "Dragon Shrine" = 13 B; full 3-clause text = 219 B;
  clauses 1+2 only = 168 B; clause 1 only = 46 B.

  | donor | name slot | desc slot | fits name | fits full text |
  |---|---|---|---|---|
  | Foolish Burial 0x1474 | 14 B | **52 B** | yes | no (clause 1 only) |
  | The Puppet Magic of Dark Ruler 0x14C1 | 30 B | 241 B | yes | **yes** |
  | Contract with Exodia 0x165B | 20 B | 279 B | yes | **yes** |
  | Curse of Fiend 0x131E | 14 B | 303 B | yes | **yes** |
  | Venom Shot 0x1C15 | **10 B** | 281 B | **NO** | — |
  | Snake Rain 0x1BFE | **10 B** | 93 B | **NO** | — |

- **Zero-insert donor candidates** — they already own exactly one criteria row
  AND one cls0 record, so both can be rewritten **in place**: no count-neutral
  insert, no phantom drop, no sortedness risk, because the cid never changes.

  | donor | crit row | cls0 record | u32 cid literals in ov3 |
  |---|---|---|---|
  | The Puppet Magic of Dark Ruler 0x14C1 | crit[157] `{0xFFFF, 0x0223DCB1, 0x00000000}` | cls0[329] `{0x02213DC5, 0x021DE22D, 0x021F533D, 0, 0x02235605}` | **1** |
  | Contract with Exodia 0x165B | crit[231] `{0x1645, 0x0223DAA5, 0x00000802}` | cls0[448] `{0x0220667D, 0, 0x021F6F75, 0, 0}` | 2 |
  | Ritual Foregone 0x1AF4 | crit[481] `{0xFFFF, 0x0223F6D9, 0x00000000}` | cls0[756] `{0x0220667D, 0, 0x021F0BDD, 0x021EA83D, 0}` | 3 |

  ("u32 cid literals in ov3" is a residue proxy: 1 means the only occurrence is
  the cls0 record itself, i.e. no other code path keys on that cid.)

## 3DS cross-check (the mandated first move for clause 2) — DONE this session

`.venv-1/Scripts/python.exe -m otn_enhanced.tools.threeds_lookup "Dragon Shrine"`

**Dragon Shrine SHIPS in the 3DS build, cid 0x295E.** Its complete footprint:

- `main_effect[1949]` (3DS 0x686CBC == NDS 0x022713C4) =
  `{cid 0x295E, aux 0xFFFF, handler 0x004B1BE8, word 0x08000002}`
- `predicates[569]` (3DS 0x6A6D44) =
  `{cid 0x295E, handler 0x0049C570, param 0x0049C0D8}`
- **ZERO occurrences of the cid anywhere in the 3DS code region** (searched the
  whole image for u16/u32 0x295E: every hit is in a data/registry/text region).

**NEW cross-build handler equivalence proven this session: 3DS 0x004B1BE8 ==
NDS 0x0223CAD9 (select from the DECK).** Four independent one-to-one matches with
identical words, which is what makes it a proof rather than a guess:

| card | 3DS row | NDS row |
|---|---|---|
| Foolish Burial 0x1474 | `{0x004B1BE8, 0x00000002}` | `{0x0223CAD9, 0x00000002}` |
| Dragon Ravine 0x2359 | `{0x004B1C1C, 0x00900002}` + `{0x004B1BE8, 0x08000002}` | `{0x0223CAF5, 0x00900002}` + `{0x0223CAD9, 0x08000002}` |
| Dark Grepher 0x1D89 | `{0x004B0A48, 0x02000002}` + `{0x004B1BE8, 0x02000002}` | `{0x0223CB19, 0x02000002}` + `{0x0223CAD9, 0x02000002}` |
| Armageddon Knight 0x1CFF | `{0x004B1BE8, 0x02000002}` | `{0x0223CAD9, 0x02000002}` |

This extends `threeds_lookup.HANDLER_EQUIV`, which previously held only the GY and
HAND handlers.

**=> Konami's own criteria word for Dragon Shrine is 0x08000002 — byte-identical
to the value independently derived from Dragon Ravine's NDS row.** Clause 1's data
is now confirmed from both sources of truth.

**Registry semantics decoded by cohort** (who else shares each pointer):

- `param 0x0049C0D8` is shared by **Snake Rain, Dark Grepher, The Fabled
  Peggulsus, Jewels of the Valiant, Dragon Shrine** — i.e. the "send monster(s)
  from your Deck to the GY" family. Disassembled: it is the **3DS twin of NDS
  0x021F0B18**, the activation condition. Same shape, same `side = desc[+2] ^
  desc[+0xA]` XOR rule, `mov r5,#1` default count, then a cid compare encoded as
  sub-immediates (`sub r0,r0,#0x1B00 / subs r0,r0,#0xFE` = cid - **0x1BFE**,
  Snake Rain -> count 4; a second arm -> count 2), ending in
  `bl 0x469A5C(side, cid, param)` compared `>= r5`.
- `handler 0x0049C570` is shared by **60+ unrelated cards** (Beetron, Spellbook of
  Life, Ghostrick Alucard, ...), so it is a generic registrar and carries no
  card-specific logic. An early read of it as a card-specific predicate was wrong.

### ⚠️ THE CLAUSE-2 CONCLUSION

**Konami's 3DS implementation of Dragon Shrine is CLAUSE 1 ONLY.** In the 3DS the
card takes the *default* arm of the shared condition (count = 1), owns exactly one
criteria row, and has no code arm anywhere. There is **no second criteria row, no
"is it a Normal Monster" predicate, and no optional-second-send record.**

So **clause 2 has no blueprint in either build.** It is not a transliteration job;
it is new machinery on the NDS side — read the type of the card that was just
sent, then offer an optional second send reusing the same criteria row. Budget it
as genuine reverse-engineering, not as a port.

## Ruled Out

- **A records-free Spell donor.** Only one Normal Spell in the ROM is free of
  both cls records and criteria rows with a name slot >= 13 B — Nightmare's
  Steelcage 0x1400. Rejected: a Spell is never *effect*-free the way a Normal
  Monster is, so the T.G. "records-free vanilla" lesson does not transfer.
  Steelcage's attack-lock lives outside the cls tables and would still fire
  alongside the mill. The right test for a Spell donor is **"is its whole effect
  the cls record I am overwriting?"**, not "is it records-free?".
- **Venom Shot 0x1C15 / Snake Rain 0x1BFE** — structurally attractive (both are
  already `0x02208DD5` deck-senders) but their **name slots are 10 B** and
  "Dragon Shrine" is 13 B. The in-place text write would be silently skipped and
  the card would keep the donor's name. Dead.
- **Painful Choice 0x132F** — name 14 B fits and desc 179 B fits clauses 1+2, but
  it owns **two** criteria rows and is a genuinely strong card. Deprioritised,
  not impossible.

## Open Questions

- **Donor choice is the user's call** — Foolish Burial (a 4-byte edit, but the
  ROM loses Foolish Burial and the desc slot holds clause-1 text only) vs. a junk
  zero-insert donor such as The Puppet Magic of Dark Ruler 0x14C1.
- **Clause 2** ("if that monster is a Dragon *Normal* Monster, send 1 more"):
  needs a second Deck selection gated on the first pick's card type. Both steps
  are the SAME zone, which per `card.darkflare_clause2` is the easy case (one
  machine, the list-zone path) — but reading *what was just sent* and making the
  second send optional is **unproven**. Not in scope until clause 1 is confirmed
  in-game.
- **Clause 3** (OPT). The engine's `0x021E5060` latch is the "once while face-up
  on the field" kind-0xC node hung off a **monster zone record**
  (`dispatch.once_while_face_up`) — a Normal Spell has no such record and leaves
  the field on resolution anyway. Likely a deliberate deviation (it only bites
  with 2+ copies). Needs its own investigation if wanted.
- **Card art** — the `dragon_shrine` asset exists; the `CardArt` row needs the
  chosen donor cid.

## Clause 2 / clause 3 reverse-engineering (this session)

### CONFIRMED: the deck-send resolver is a 9-phase state machine

Disassembled 0x02208DD4 in full. `[r5+0x70]` is the phase; the 9-way halfword
jump table at **0x02208DFA** (`add pc` base 0x02208DFC) covers phases 0x78..0x80:

| phase | entry | role |
|---|---|---|
| 0x80 | 0x02208E0C | ACTIVATE: preset count=1 / mode=0, per-cid switch, candidate check, `0x0219A818(side,0x3A)`, -> 0x7F |
| 0x7F | 0x02208EB4 | SELECT: prompt code = min(count,32)+6, or min(mode,32)+0x27 when mode!=0; `0x0219C430(side, prompt, cid, param)`, -> 0x7E |
| 0x7E | 0x02208EE4 | count := `[0x0229DD94+0x34]` (how many were actually picked); mode := 1; falls into 0x7D |
| 0x7D | 0x02208EEE | SEND LOOP: entry `0x0219C94C(n)` -> packed ref `(idx<<1)|side` -> `0x021D21B0(side, ref, cid, 0, 0)`; count--; -> 0x7D |
| done | 0x02208F30 | `0x021D2964`; if mode!=0 -> 0x7C else 0x64 |
| 0x7C | 0x02208F42 | **POST-SEND FOLLOW-UP**, gated on a 3-cid switch |
| 0x79/0x7A/0x7B | 0x02209062 | return 0 |
| 0x78 | 0x0220904A | `0x0225BF30(1-side)` |

### CONFIRMED: phase 0x7C is the clause-2 hook

Its gate @0x02208F42 admits exactly **0xDBF (Speed Spell - Power Baton),
0x1C15 (Venom Shot), 0x1DC2**; everything else falls to `bne 0x02209046` -> return
0x64. The action dispatch is a second cid switch @0x02208FB8. **Venom Shot is the
proof this phase really runs after the send**: its arm @0x02209018 is
`0x021C7D80(side, slot, 0x1D, 2)` = place 2 counters of type 0x1D, matching its
printed "place 2 Venom Counters on it". (Its text is counters, NOT a destroy --
an early recollection of "destroy it" was wrong; the ROM settled it.)

### CONFIRMED: the Normal-Monster test is a card_prop field

Decoded card_prop (bits[32:38] = card_type) against ygoprodeck across the whole
table: **card_type 1 = Normal Monster (224 cards)**, 31 = Normal Tuner Monster (5),
3 = Effect, 33 = Tuner, 37 = Synchro, 27 = Spell, 29 = Trap. **race 1 = Dragon**
(Blue-Eyes 0x0ED9, Luster Dragon 0x160C, Divine Dragon Ragnarok 0x1859 all
ct=1/race=1; Masked Dragon 0x17E6 and Decoy Dragon 0x1C4F are ct=3). So clause 2's
extra test is `card_type in {1, 31}` -- the Dragon half is already guaranteed by
the criteria row. GY = `player+0x55C`, count = `player+0x14` (ram.gy_and_banished,
VERIFIED); trust the count, never the nonzero span.

### RULED OUT: the ov3 dead-code cave cannot host a clause-2 stub

`allocations.yaml: ov3_dead_blocks` is **fragmented**: the largest fully-free block
is 16 B (0x021B56B8), then 12, 10, 8, 8 -- about 54 B free but **no contiguous run
over 16 B**. A clause-2 stub is ~100 B. The 36 KB `ov3_cave.py` WINDOW_PRIMARY is
NOT usable either: that file states the slot map is "INTENTIONALLY EMPTY until the
canary run passes", and the canary verdict is still ambiguous. So clauses 2/3 must
live in the **ov5 cave** => normal-duel only. Clause 1 stays pure ov3 data and
remains puzzle-safe.
⚠️ The ov3 -> ov5 branch MUST be cid-gated in ov3 first: phase 0x7C's fall-through
is shared by every deck-sending card, and bl-hijacking a shared fall-through into
ov5 is the documented freeze footgun.

### ⚠️ CORRECTION MADE THIS SESSION -- do not inherit the wrong version

`0x021D2B88` is **NOT** the once-per-turn latch query. Disassembled: it tests
`desc[+4] == 0x25`, `desc[+3] <= 4`, then `0x02022FDC(cid)` and a zone word via
0x0229C33C. An inference chain that read it as the OPT check (because it opens Pot
of Duality's condition 0x02203259) does **not** close. Likewise `0x021E4D80`, which
Ritual Foregone's cost 0x021EA83D calls first, is a Spell-activation-legality gate
(it probes cid 0x209B in zone 0xA), not the OPT.

What IS established: every native Normal Spell printed "You can only activate 1 X
per turn" carries a **cost slot (+10)**, and three of them share **0x021E8E75**
(Pot of Duality 0x2321, Pot of Benevolence 0x21E0, Spell Power Grasp 0x1FC8);
Ritual Foregone 0x1AF4 and Instant Fusion 0x1AF5 share 0x021EA83D, a wrapper that
tail-calls it. **0x021E8E74 is cid-generic** -- it reads the cid straight from the
descriptor (`ldrh r1,[r4]`) and posts via `0x021D2584(side, cid, 1, 0)`, with no
per-cid switch, so unlike Darkflare's 0x021E7245 a donor does NOT fall into a
do-nothing default arm. **The POST half is solved; the REFUSAL half is not
identified.** Do not ship clause 3 on the assumption that +10 alone is sufficient.

### Progress on open question 1 (the OPT latch) -- mechanism found, proof not closed

`0x021D2584(side, cid, r2, r3)` is a thin wrapper: it sets `r1 = 0xB` and tail-calls
**`0x021C479C(side, 0x0B, cid, r2, r3)`**. Per `dispatch.once_while_face_up`,
0x021C479C is the **attached-effect node WRITE** (the same primitive the kind-0xC
"once while face-up" cost 0x021E5060 uses). So the once-per-turn mark for a Spell is
an **attached node of KIND 0x0B keyed by the cid**, on the player's side rather than
on a monster zone record -- which is exactly why it can outlive a Normal Spell that
resolves into the GY, and why the kind-0xC latch could not express this.

REMAINING STEP: identify the kind-0x0B READER (the analogue of the kind-0xC reader
0x021A10A0, which walks the node array at 0x0229D33C matching `[node+2] & 0xF`) and
confirm it gates activation. Per otn-attached-effect-rider kinds 6..0xB are walked by
**0x021A0950**, but that note is provenance, not proof -- verify before relying on it.

## Open Questions (clause 2 / 3)

1. **What refuses the second activation?** Find the consumer of the
   `0x021D2584(side, cid, 1, 0)` turn-log entry. Until that is found, clause 3 is
   unproven.
2. **Can phase 0x7C return 0x7F to re-enter selection?** The machine would run
   0x7F -> 0x7E -> 0x7D -> done -> 0x7C again, so it also needs a latch or it
   loops forever. Latch location unchosen.
3. **Prompt semantics**: phase 0x7F picks prompt `count+6` when mode==0 and
   `mode+0x27` when mode!=0. If the +0x27 family is the cancelable "up to N" form,
   a second pass gets clause 2's "you can" for free. UNPROVEN.
4. **How to read the just-sent card at phase 0x7C.** Two candidates: re-read
   selection entry 1 (`0x0219C94C(1)` -> ref -> `0x021A2510`, which is what
   0xDBF/0x1DC2 do), or read the GY top (`player+0x55C`, index count-1).

## Next Experiment

Answer (1) statically first -- it is free: find the reader of the turn-log slot
written by `0x021D2584`, and confirm it gates activation. If it does, clause 3 is
a 4-byte edit (+10 = 0x021E8E75) plus possibly nothing else.
Then answer (3) by reading `0x0219C430`'s prompt-code table rather than guessing.
Only after both should any ov5 code be written -- no blind build-test cycle.

## CLAUSES 2 + 3 IMPLEMENTED (ov5) -- built, verified, NOT yet in-game tested

User direction: use the ov5 cave like every other card patch. Done -- the card is
now NORMAL-DUEL ONLY (overlay 41 evicts ov5 in a puzzle), same as Darkflare
clause 2, Lightpulsar clauses 2/3, Sea Lancer and Shien's Dojo.

### The parts

| part | where | what |
|---|---|---|
| D | ov3 data, 8 B | cls0[329] +0C -> `CAVE_DS_COND\|1`, +10 -> `CAVE_DS_COST\|1` |
| E | ov3 CODE, 8 B | phase-0x7C gate @0x02208F42 -> `ldr r0,[pc,#4] ; bx r0 ; nop ; .word CAVE_DS_FOLLOW\|1` (stock 20 B asserted first) |
| F | ov5 cave | COND 36 B @0x0239C84C, COST 32 B @0x0239C88C, FOLLOW 160 B @0x0239C8CC, SCRATCH 4 B @0x0239C98C |

### CONFIRMED: clause 3 is Pot of Duality's mechanism, reused verbatim

The per-turn record is the **TURN LOG**, not the kind-0xC "once while face-up" node.
- POST `0x021D2584(side, cid, 1, 0)` -- a thin wrapper that sets `r1 = 0xB` and
  tail-calls the attached-node writer **0x021C479C**, posting **event 0x35**. It
  reads the cid straight from the descriptor, so it is **fully cid-generic** and a
  donor does NOT hit a do-nothing default arm (contrast Darkflare's 0x021E7245).
- QUERY `0x021A14E8(side, 0xB, cid, 1)` -- exactly what Pot of Duality's native
  condition 0x02203259 calls (`ldrb r0,[r5,#2] ; mov r1,#0xB ; ldrh r2,[r5] ;
  mov r3,#1 ; bl 0x021A14E8`). Cross-checked against Quasar's shipped PART K, which
  already uses this pair -- so this is a reused, in-game-proven mechanism.
The COST slot is the right home for the stamp because it runs exactly once per
activation (0x02217F80 tests desc[+7], runs slot4 only while clear, then sets it).

### CONFIRMED: the card-type reader

`0x0202ABF8(cid)` is `bl 0x0202A084 ; ldr r0,[r0,#4] ; lsls #0x1A ; lsrs #0x1B`
= **card_prop card_type >> 1**. That reconciles the two encodings that looked
contradictory: card_prop ct 1/3/5/7/31/33/35/37/39 vs the KB's Synchro {17,18,19}.
So Normal Monster (ct 1) -> **0** and Normal Tuner (ct 31) -> **15**; the stub
accepts both. It lives in **ARM9**, i.e. always resident.

### Build state

`--verify` PASS on all ten checks (A criteria row, B cls0 +04/+08/+14, registry
sorted, cls0 sorted, exactly-one-record, D slots, E gate, F x3 cave contents).
Stubs were disassembled back out of the built ROM: `subs r3,#1` uses the 2-operand
form (dodges thumb.add_sub_imm3) and every exit is `pop {...,PC}` (dodges
thumb.pop_into_lr); all 11 literal-pool entries resolve to the intended values.
Composition: no other patch module references 0x02208Fxx, 0x02208DD5 or cid 0x14C1;
`check_allocations` clean (104 ov5 slots, no overlaps).

## ⚠️ STILL UNPROVEN -- the in-game test is the arbiter

1. **Re-entry.** That returning 0x7F from phase 0x7C re-enters selection cleanly.
   The phase map says it must; it has never been exercised.
2. **Clause 2 is MANDATORY, not optional.** The card says "you CAN send 1 more";
   this build always sends it. Phase 0x7F picks its prompt as `count+6` when
   mode==0 and `mode+0x27` when mode!=0, and the **+0x27 family is undecoded** --
   it may be the cancelable "up to N" form that would give the optional wording for
   free. The stub forces mode = 0 (the same known-good prompt the first send uses)
   rather than guessing. Same class of deliberate deviation as Eclipse Wyvern
   clause 2. **Decoding the +0x27 prompt family is the single highest-value next
   experiment.**
3. **GY-top assumption.** The stub reads player+0x55C at index count-1 and assumes
   that is the card just sent. It correctly trusts the count rather than the
   nonzero span (per ram.gy_and_banished), but "last entry == what we just sent"
   is an assumption, not a measurement.

## In-game test steps (standalone rom_dragon_shrine.nds)

Deck needs BOTH a Dragon **Normal** Monster (e.g. Luster Dragon 0x160C, Divine
Dragon Ragnarok 0x1859, Blue-Eyes 0x0ED9) and at least one other Dragon.

1. Activate Dragon Shrine, pick a Dragon **Normal** Monster -> expect a SECOND
   Dragon prompt, and both cards in the GY. (clause 2)
2. Activate it picking a Dragon **Effect** Monster (Masked Dragon 0x17E6, Decoy
   Dragon 0x1C4F) -> expect NO second prompt, exactly one card milled.
3. Activate a second copy the same turn -> expect it to be UNOFFERABLE. (clause 3)
4. Pass the turn, activate again -> expect it to work. (the latch is turn-scoped)
5. Regression: Venom Shot still places 2 Venom Counters after its mill (it shares
   the phase-0x7C gate this patch rewrote).

## Next Experiment (clause 1 -- CLOSED)

None pending: clause 1 is fully evidenced statically and needs no GDB session.
The in-game oracle is the arbiter — activate the card with >= 1 Dragon monster
in the Deck and confirm (a) it offers, (b) it sends exactly one, (c) only Dragons
are offered, (d) it refuses with no Dragon in the Deck.

## Composition (slots this patch would claim)

Clause 1 claims **no ov5 cave slot, no phantom cid, no new record**:

- one criteria-registry row **rewritten in place** at the donor's existing index;
- one cls0 record **rewritten in place** at the donor's existing index.

Both keep the donor's cid, so the sorted binary searches over 0x022713C4 and
0x0227E64C are untouched and neither array's count changes. There is no
`find_event_handler` leftmost-record risk (the donor keeps exactly one record).
Pure ov3 data, so it is **puzzle-safe** (no overlay-41 eviction concern).
