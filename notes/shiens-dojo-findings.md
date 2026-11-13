# Shien's Dojo — findings

Card: **Shien's Dojo** (Konami 47436247), Continuous Spell. **Not present in the
OTN ROM** (0 hits for `Dojo` in `nds_name.bin`).

Effect text (authoritative — `scratch/ygoprodeck_cache.json`):

> Each time a "Six Samurai" monster(s) is Normal or Special Summoned, place 1
> Bushido Counter on this card. You can send this card to the GY; Special Summon
> 1 "Six Samurai" or "Shien" Effect Monster from your Main Deck, whose Level is
> less than or equal to the number of Bushido Counters on this card.

Clauses:
1. **Counter accrual** — each Six Samurai N/SS → place 1 Bushido Counter.
2. **Send-to-GY → Special Summon** — send this card to the GY; SS 1 "Six Samurai"
   or "Shien" **Effect Monster** from the **Main Deck**, Level ≤ counters.

**Decisions taken (user, this session):** donor must be an *unrelated* card (keep
Six Samurai United and Temple of the Six intact); scope = both clauses, but
**verify clause 1 in-game before building clause 2**.

**Donor chosen: `0x19B2` Ancient Gear Castle.** (`0x1F75` Super Solar Nutrient
was the first pick on structural grounds; the user rejected it as a
meta-relevant card. Ancient Gear Castle costs more residual-cleanup work but is
expendable.)

**STATUS: clause 1 CONFIRMED IN-GAME. Clause 2 CONFIRMED IN-GAME** (user: Dojo
correctly sends itself to the GY and summons only Level<=4 Six Samurai, refusing
Level 5+). **PART H (counter-derived Level bound, ov5) CONFIRMED IN-GAME.** **PART I ("Six Samurai OR Shien") CONFIRMED IN-GAME. SHIPPED** — added to
`apply_all_patches.py` (above the always-last WiFi-timers step). The card is
COMPLETE: both clauses, the counter-derived Level bound, the dual set-code
filter, and full retirement of the donor's Ancient Gear Castle behaviour.

**CLAUSE 1 IS CONFIRMED WORKING IN-GAME** (user, 2026-08-04: "It gains
counters now"). Round 1 failed in-game (no counters accrued); root cause was the
counter CAPACITY gate, fixed by PART E. Donor cleanup (PART F) is also done.
`verify()` = 18/18 PASS.
ROM: `data/over_the_nexus/working/rom_shiens_dojo.nds`
(`otn_enhanced/cards/shiens_dojo.py`).

## Confirmed (this session, committed oracles `nds_overlay_3.bin` / `arm9.bin`)

- **KB healthy**: `verify_knowledge` = 171 facts, 145 PASS, **0 FAIL**, 26 UNVER.
- **Shien's Dojo is absent**: 0 occurrences of `Dojo` in `nds_name.bin`.
- The ROM implements Bushido Counters for exactly three cards: `0x1D22` Six
  Samurai United, `0x219A` Gateway of the Six, `0x247E` Temple of the Six.

### The full clause-1 chain (end to end, all by disassembly)

1. **Summon-trigger dispatcher**, arm at `0x02266BC2`:
   `LDR R0,[SP,#0x58]` (summoned cid) → `BL 0x02023A18`.
2. **`0x02023A18` = the Six Samurai predicate (ARM9)**. Binary-searches
   (`0x02022E14`) the **18-entry** table `0x0209CA8C` (`MOV R2,#0x12`), else a
   **4-entry** table `0x0209C5C2` (the Six Samurai *Spell/Trap* group: Return of
   the Six Samurai, Cunning, Six Samurai United, Asceticism). Returns 1/0.
   ✔ Cross-confirmed by the shipped `patch_elder_six_samurai.py`, which names
   `0x0209CA8C` / set-code `0x1E` / consumer thunks `0x02023A18`+`0x02023A3C`.
3. If it returns non-zero, **three arm calls** follow, back to back:
   - `0x02266BCE: LDR R0,=0x1D22 ; BL 0x02244418`
   - `0x02266BD4: LDR R0,=0x219A ; BL 0x02244418`
   - `0x02266BDA: LDR R0,=0x247E ; BL 0x02244418`
   (literals in the pool at `0x02266DD4/D8/DC`.) **This is the archetype gate —
   the only one on the whole path.**
4. **`0x02244418(cid)`** = `0x022443C8(0,cid)` then `0x022443C8(1,cid)` — arm on
   both sides.
5. **`0x022443C8(side,cid)`**: picks a zone span by card kind
   (`0x02029E60`=monster → zones 0..4; `0x02029E80`=field → zone 10; else 5..9),
   and for each zone where `0x021AC004(side,zone,cid)` matches, calls
   `0x021D2A40(side, zone, 5, 1)`.
6. **`0x021D2A40(side, zone, bit, value)` = generic per-zone bit setter.** Reads
   the flag word `0x0229ACD8 + (side&1)*0xB3C + zone*0x14`, computes
   `cur = (word>>bit)&1`, returns if `cur == value`, else posts change message
   `0x021B940C` (opcode 0x29). So arming sets **bit 5**.
- **Continuous-trigger registry @ `0x02275510`, 181 rows × 8 B,
  `{+0x00 Thumb handler, +0x04 cid}`** (cid 0 = unconditional). Geometry proven
  closed: a shape-walk yields exactly 181 rows AND both walkers hardcode
  `CMP Rn,#0xB5`. Table ends `0x02275AB0`, immediately below the known
  `synchro.list_a` @ `0x02275AB8` — **zero spare bytes to append into.**
  - **Exactly two consumers** (proved: no other pointer anywhere in ov3/arm9
    lands inside `0x02275510..0x02275AB8`):
    - **walker A `0x02248154`** — filters to 5 handlers
      (`0x02246AE9/0x02245265/0x02245C49/0x02246129/0x02244D99`); called by BL
      from `0x02224A52`, `0x0224B2C2`, `0x02251354`.
    - **walker B `0x022481C0`** — **no handler filter**: `R0=[row+4]` (cid),
      `R1=[row+0]` (handler), `BLX R1`, stop at first non-zero return. Gated at
      entry on `[0x0229DD94+0x18] != 0`. Called by BL from `0x021D48B2`,
      `0x021D64C4`, `0x021D6AEA`, `0x021D6D5A`.
    Walker A excludes the Bushido thunks ⇒ **walker B is the invocation path.**
  - **Bushido rows** (indices relative to base `0x02275510`):
    **[76]** `0x02275770` → `0x022473C5` / `0x1D22` United;
    **[77]** `0x02275778` → `0x022473C5` / `0x247E` Temple;
    **[78]** `0x02275780` → `0x022473D1` / `0x219A` Gateway.
    Walker count immediates: `CMP R4,#0xB5` @`0x02248196` (A),
    `CMP R5,#0xB5` @`0x0224821C` (B).
- **Handlers are 12-byte thunks** `{LDR R3,[PC,#4]; MOV R1,#type; MOV R2,#amt;
  BX R3; .word 0x02247305}`:
  `0x022473C4` → **type 6, amount 1** (United + Temple);
  `0x022473D0` → **type 6, amount 2** (Gateway). Amounts match the printed text
  1/1/2 exactly ⇒ **counter type 6 = Bushido Counter**. Sibling thunks encode
  type `0x1B` (A-Counters), `8` (Realm of Light), `0xA`, `0xB`, `0xC`.
- **Shared body `0x02247304(cid, type, amount)`**: sweeps side 0..1 × zone 0..10;
  `0x021A36EC(side,zone)` gives the zone's cid, compared against the passed cid;
  face-up bit `[player+zone*0x14+0x44]>>5`; **clears bit 5**
  (`0x021D2A40(side,zone,5,0)`); `0x021A32B4(side,zone)` zone-active predicate;
  skips if bit 26 of the flag word is set; then
  **`0x021C7D80(side, zone, type, amount)`** = the place-counter primitive
  (validated type range, posts opcode 0x3B via `0x021C3BC8`). Returns 1 on the
  first match, so walker B is a **pump** — arm sets bit 5, the body consumes it.
- **cls records** (all four tables searched per `dispatch.cls_tables`):
  `0x1D22` → one record `cls3[370]`; `0x219A` → three (`cls3[628..630]`);
  `0x247E` → **none** (purely continuous).
- **United's resolution `0x022065B8`** = generic draw resolver; `N` from the
  shared per-cid switch `0x02206304`, whose United leaf is
  **`0x0220651A: LDRH R5,[R4,#0x1E]`** → the counter count is read from the
  effect descriptor at **+0x1E (u16)**; payload is `0x021D12F4(side, N)` (the
  known `equip.draw` primitive).
- **16 registry rows are provably dead** — their cid has no `card_prop` record
  (card_prop = 4305 entries, all cids distinct), so the body can never match a
  field card:
  `[2] 0x0EAD, [20] 0x0E30, [21] 0x0E46, [22] 0x0E4C, [23] 0x0E51, [24] 0x0E56,
  [29] 0x0E9F, [58] 0x0EC4, [64] 0x0E9A, [69] 0x0E12, [107] 0x0EB7,
  [137] 0x2349, [154] 0x1A50, [164] 0x1A8A, [175] 0x1875, [178] 0x11C9`.

### Donor selection (Super Solar Nutrient `0x1F75`)

Filter: Continuous Spell, no registry row, text slots fit Dojo's **299-byte**
desc + **12-byte** name (text is written strictly IN-PLACE by
`apply_stats_and_text`; oversized = skipped).

- Records-free Continuous Spells: 39 candidates, but only **three** have a desc
  slot ≥ 299 B: `0x150E` Spiritual Energy Settle Machine (408 B, 3 residual code
  sites), `0x15E5` Kaiser Colosseum (346 B, **1** residual site `0x021AD816`),
  `0x19B2` Ancient Gear Castle (308 B, **10** sites — rejected).
- Widening to *exactly one cls record* found **`0x1F75` Super Solar Nutrient**
  (desc slot 304 B, one record `cls0[1023]`
  `+04 0x0221B2FD +08 0x021DC625 +0C 0x021F7D05 +10 0x021E7C89 +14 0`).
  Its real text is
  *"Activate this card by Tributing 1 Level 2 or lower Plant-Type monster;
  Special Summon 1 Plant-Type monster from your hand or Deck **whose Level is
  less than or equal to** the Level the Tributed monster had on the field +3…"*
  — i.e. the engine already implements **Deck Special Summon with a runtime
  Level-≤ bound** on a Continuous Spell. That is clause 2's hard part, native.
  Its `+04` is a phase state machine (`switch on [0x0229AAFC+0x70] - 0x7C`,
  0..4), matching the KB `resolver_protocol` phase contract.

### ⚠️ ROUND 1 FAILED IN-GAME — the counter CAPACITY gate (root cause)

A registry row + an arm call are **necessary but NOT sufficient**. `0x021C7D80`
does not place a counter blindly:

- `0x021C7D8C: BL 0x021A3054(side, zone, type)` → the card's **current** count
- `0x021C7DD0: BL 0x021A2F10(side, zone, type)` → the card's **capacity** for
  that type — and the primitive **returns 0, placing nothing**, when the capacity
  is 0 or already reached.

`0x021A2F10` switches on the counter type. The **type-6 (Bushido)** arm at
`0x021A2F9E` is a hard-coded per-cid chain over the zone card's cid
(from `0x021A36F8`):

| cid | card | capacity |
|---|---|---|
| `0x1D22` | Six Samurai United | **2** |
| `0x219A` | Gateway of the Six | `0xFF` |
| `0x247E` | Temple of the Six | `0xFF` |
| anything else | — | **0** |

Ancient Gear Castle `0x19B2` had no entry ⇒ capacity 0 ⇒ nothing could ever be
placed, no matter how correctly it was armed. **This is what the user's in-game
test caught.** It also closes an earlier open question: United's printed
"(max. 2)" is *this capacity value*, not a separate clause. Other type arms grant
capacity by archetype predicate rather than a cid literal (type 1 — Ancient Gear
Castle's native counter — calls the ARM9 thunk `0x0202352C`).

**This is now confirmed working in-game.** Fixed by **PART E**: `BL` from the chain head `0x021A2F9E` into a 24 B stub at
`0x021B58E8` that returns `0xFF` for the donor and otherwise re-runs the
displaced `LDR R1,=0x1D22` / `CMP R0,R1` and `BX LR` back to the `BNE`.
LR is free to clobber — `0x021A2F10` opens with `PUSH {R3,R4,R5,LR}`.

### The Six Samurai set-code table is NOT involved for the counter-holder

`0x02023A18` is called with the **summoned monster's** cid, not the
counter-holder's, so Shien's Dojo does **not** need to be in `0x0209CA8C`.
Confirmed structurally: neither Gateway of the Six `0x219A` nor Temple of the Six
`0x247E` appears in the 18-entry monster table or the 4-entry Spell/Trap table
`0x0209C5C2`, yet both accrue counters natively.

## Ruled out

- **Temple of the Six as donor** — records-free and already owns a Bushido row,
  but it is a **Field** Spell (Dojo is Continuous): needs a `card_prop` type
  change plus stripping its continuous ATK-loss rider (`0x247E` referenced at
  `0x021B29D0`). Also excluded by the user's "keep both" decision.
- **Six Samurai United as donor** — cheapest of all (clause 1 free, one payload
  swap) but destroys United. Excluded by user decision.
- **Appending a 182nd registry row** — both walkers hardcode `0xB5`, and the
  table butts directly against `synchro.list_a` at `0x02275AB8` with **0 spare
  bytes**. Overwriting a provably-dead row is the count-neutral option.
- **Ancient Gear Castle donor** — 10 residual code sites.
- **A Six-Samurai check inside the counter path** — there is none. Walker B, the
  thunk, the body `0x02247304` and `0x021C7D80` are all archetype-agnostic; the
  gate is solely the `0x02023A18` test at the arm site `0x02266BC2`.

## Open questions

- **Which bit actually gates placement.** Arming sets zone bit 5; the body
  *clears* bit 5 but tests **bit 26**, and `0x021A32B4` tests bits 6/1/21 — so
  the precise consume-check is not pinned. **UNVERIFIED — measure, don't infer.**
  This does **not** change the patch: our row uses a byte-identical handler and
  our arm call uses the identical `0x02244418` inside the identical
  Six-Samurai-gated branch, so the donor is wired exactly like United.
- Is descriptor `+0x1E` specifically "Bushido Counters on this card", or a
  generic value stashed by the cost step? Strong inference only. **UNVERIFIED.**
- Clause 2 needs **"Six Samurai" OR "Shien" Effect Monster**. `0x02023A18` covers
  Six Samurai monsters + Six Samurai Spell/Traps, but there is **no "Shien" name
  group** in the set-code tables. Great Shogun Shien `0x1B39` is *not* in the
  18-entry table. A "Shien" cid list must be built (candidates: `0x1B39`,
  `0x1B3A` Footsoldier, `0x1C81` Enishi, `0x2465` Squire).
- Super Solar Nutrient's residual riders ("when this card leaves the field,
  destroy that monster" / vice versa) must be stripped for clause 2.

## Next experiment

**Clause 1 in-game verification — this is the gate before any clause-2 work.**
ROM: `data/over_the_nexus/working/rom_shiens_dojo.nds`.

1. Deck-edit in **"Shien's Dojo"** (it occupies Ancient Gear Castle's slot) plus
   any Six Samurai monster from the 18-entry set-code table `0x0209CA8C`
   (e.g. `0x1B33` The Six Samurai - Yariza, `0x245F` Legendary Six Samurai -
   Kizan) and one non-Six-Samurai vanilla monster as the control.
2. Start a **normal duel** (ov3 is resident in every mode, but keep it simple).
   Activate Shien's Dojo.
3. **Test:** Normal Summon the Six Samurai → Dojo must show **1 Bushido Counter**.
   Summon a second → 2.
4. **Control:** Normal Summon the non-Six-Samurai monster → the count must NOT
   change. This is also the empirical answer to the bit-5-vs-bit-26 question.
5. **Regression:** Six Samurai United and Temple of the Six must still gain their
   counters (the arm stub performs Temple's displaced call first), and Gateway of
   the Six must still gain **2**.

If step 3 fails, the first thing to check is whether the pump ran at all: break
on the stub at `0x021B582C` and confirm it is reached with R0 = 0x247E.

## Composition (claims REGISTERED, guard passes)

- **New pool `counter_trigger_row`** (registry @ `0x02275510`) — claims
  `0x2349` (the dead row 137 consumed) and `0x19B2` (the donor cid now in it).
  No existing patch claims anything in this table; the pre-existing
  `registry_row` pool is the *different* effect registry @ `0x0228E1E0`.
- **ov3 dead-code pool**: `(0x021B582A, 22, "shiens_dojo")` — the stub is based
  at `0x021B582C` (2 B in; the assembler needs a 4-aligned base for its literal
  pool), 20 B used, inside the 30 B block of phantom arm cid `0x1827`.
- **`lp_literal` pool**: `0x1A50` — the dead cid the native accrual literal
  `0x02265FF8` is repointed to.
- `check_allocations`: **no ov5 overlaps, no phantom double-claims, no ov3
  overlaps, ledger in sync** (82 ov5 slots, 22 phantom claims, 158 B ov3 free).
- `patch_elder_six_samurai` owns phantom `0x251B` in `0x0209CA8C` (donor
  `0x1F1D`). Untouched — and a bonus: Elder correctly counts as a Six Samurai for
  Dojo's counter.
- **NOT added to `apply_all_patches.py`** — deliberately. It stays a standalone
  test ROM until clause 1 is confirmed in-game.

## Remaining work

1. ~~Clause-1 in-game confirmation~~ — **DONE, confirmed by the user.**
2. ~~Donor residue~~ — **DONE (PART F).** Five equality/argument literals
   (`0x0225D274`, `0x0225E4F8`, `0x022613AC`, `0x02261CE4`, `0x02267A5C`)
   repointed to the dead cid `0x1A50`; the "+300 ATK to Ancient Gear monsters"
   arm neutralised by NOPing its leaf `BEQ` @`0x021B3294` so a match falls
   through to the same `B 0x021B355E` the non-match path already takes — the
   sorted chain's literal, CMP and exit are all provably untouched (guarded in
   `verify()`). Worth an in-game spot-check that Ancient Gear monsters no longer
   gain 300 ATK.
3. **Clause 2** — not started. Needs, in order:
   - **An activated effect record.** Ancient Gear Castle is records-free across
     all four cls tables, so this is a **count-neutral cls insert** (a phantom cid
     must be dropped to keep the array sorted and its hard-coded count valid) —
     not the in-place transplant a donor with an existing record would allow.
   - **The cost:** "send this card to the GY". `equip.send_self` `0x0208F188` is
     the known primitive.
   - **The counter read.** Six Samurai United's resolver reads the count from the
     effect descriptor at **`+0x1E` (u16)** (`0x0220651A: LDRH R5,[R4,#0x1E]`).
     Whether `+0x1E` is specifically "Bushido counters on this card" or a generic
     stashed value is still **UNVERIFIED** — that is the first thing to pin.
     A safer alternative now exists: call `0x021A3054(side, zone, 6)` directly,
     which is the engine's own "current type-6 count" accessor (proven this
     session as the first call inside `0x021C7D80`).
   - **The target filter:** "Six Samurai" **OR** "Shien" **Effect Monster**.
     `0x02023A18` covers Six Samurai monsters + Six Samurai Spell/Traps, but
     there is **no "Shien" name group** anywhere — Great Shogun Shien `0x1B39` is
     not in the 18-entry table. A "Shien" cid list must be built:
     `0x1B39` Great Shogun Shien, `0x1B3A` Shien's Footsoldier,
     `0x1C81` Enishi Shien's Chancellor, `0x2465` Shien's Squire.
   - **The Level ≤ N bound + Deck SS.** The engine demonstrably implements
     "Special Summon 1 monster from the Deck whose Level is less than or equal to
     <runtime value>" — Super Solar Nutrient `0x1F75`'s `cls0[1023]`
     (`+04 0x0221B2FD`, a phase machine switching on `[0x0229AAFC+0x70] - 0x7C`).
     That card is no longer the donor, so this is a **model to copy**, not a
     record to transplant.


---

# Clause 2 — work started

## Confirmed this session

- **The shared "Special Summon from Deck" resolver is `0x02206CAC`** (Thumb entry
  `0x02206CAD`). Reached as slot **+04** by both of the closest analogues:
  - `0x1B3A` **Shien's Footsoldier** — `cls2[237]`
    `+04 0x02206CAD +08 0 +0C 0x021F0419 +10 0x021E51E5 +14 0`.
    Its `+0C`/`+10` are the known leave-trigger pair (`otn-leave-trigger-cls2`),
    so **+04 is the resolution**. Native effect = "SS 1 **Level 3 or lower**
    **'Six Samurai'** monster from your **Deck**" — i.e. Deck SS + set-code
    filter + Level bound, which is clause 2 with a constant bound.
  - `0x1F76` **Six Scrolls of the Samurai** — `cls0[1024]` `+04 0x02206CAD`
    ("SS 1 Great Shogun Shien from your Deck").
- **Its shape:** `R4` = descriptor, `R5 = [R4+2] ^ [R4+6]` = side, then a
  **9-way phase jump table** on `[0x0229AAFC + 0x70] - 0x78` (phases
  **0x78..0x80**, `CMP #8 / BLS`, halfword offset table at `0x02206CC6`);
  anything outside that range exits at `0x02206EFE`. Per-cid arms live inside
  the phase bodies (e.g. `0x02206CE6` compares the descriptor cid against
  `0x247D` Asceticism).
- **Its literal pool `0x02206F04..0x02206F3C`** holds 11 cids: `0x247D, 0x1A98,
  0x136A, 0x1612, 0x1E2C, 0x1BA1, 0x21F8, 0x1232, 0x2233, 0x1F7A, 0x2361`.
  The function ends there — `0x02206F40` is the next function (the KB's
  `0x02206F41` Yubel-TI leave-trigger slot).
- **Cost primitive:** `resolver.send_self_gy` = **`0x021CF658`** (send this card
  to the GY), per the KB — better than the equip-engine `0x0208F188` I cited
  earlier.
- **Counter read:** prefer **`0x021A3054(side, zone, 6)`** — the engine's own
  "current count of type-6 counters" accessor, proven this session as the first
  call inside `0x021C7D80` (`0x021C7D8C`). This avoids depending on the
  still-UNVERIFIED descriptor `+0x1E` reading.

## THE CRITERIA REGISTRY — where clause 2's filter actually lives

The Deck-SS resolver's per-cid switch holds only **exceptions**. The real
per-card search criteria live in the **criteria/populate registry
`0x022713C4`** (KB `populate_table`; 1388 rows x 12 B, **sorted by the u16 cid at
+0x00**, binary-searched by `0x02243B9C`). Decoded layout:

| off | width | meaning |
|---|---|---|
| `+0x00` | u16 | cid (the sorted key) |
| `+0x02` | u16 | filter value — a **set code** normally, a **cid** when flags has `0x0800` (by-name), `0xFFFF` = no archetype filter |
| `+0x04` | u32 | Thumb handler pointer |
| `+0x08` | u16 | flags (`0x0002` base, `0x0802` by-name, `0x1002`, `0x0022`) |
| `+0x0A` | u16 | extra criteria — **low byte = the Level bound**, high byte = Type/race filter |

Observed rows:

```
cid    filt   handler     flags  extra   card
1B3A   001E   0223CAB5    0002   008C    Shien's Footsoldier   (Lv<=3 Six Samurai, SS from Deck)
247B   001E   0223CAF5    0002   008C    Shien's Smoke Signal  (Lv<=3 Six Samurai, to hand)
247D   001E   02243781    0002   0000    Asceticism of the Six Samurai
1BA1   001F   0223CAB5    0002   0000    Crystal Beacon        (Crystal Beast, no level bound)
2233   FFFF   0223E31D    0002   588C    Super-Nimble Mega Hamster (Lv<=3 Beast)
1612   FFFF   0223E31D    0002   9088    Apprentice Magician   (Lv<=2 Spellcaster)
1F76   1B39   0223D075    0802   0000    Six Scrolls           (by NAME: Great Shogun Shien)
```

**`0x001E` is the Six Samurai set code** — the same one `patch_elder_six_samurai`
uses for the ARM9 table `0x0209CA8C`. So `0x1B3A`'s row is literally
"set-code 0x1E, Level <= 3, SS from Deck" — clause 2 minus the dynamic bound.

**Level-bound encoding (VERIFIED across all 1388 rows):** `+0x0A` low byte =
`0x80 | (L << 2) | b0`, where `L` is the level cap and `b0` is an unrelated flag.
Observed values map exactly: `0x88`→2, `0x8C`→3, `0x90`→4, `0x94`→5, `0x98`→6,
`0x9C`→7, `0xA0`→8, and `0x00` = no bound. The population is monotone and
`0x90` (Level <= 4) is by far the most common (86 rows) — exactly what the real
card pool looks like, which is what makes this a closed reading rather than a
guess.

**Design consequence for clause 2.** The donor `0x19B2` has **no** row, so this
is a **count-neutral insert** into a sorted, hard-counted array (drop a phantom;
`0x234F` is already taken by `sea_lancer`, pick another). The row would be
`19B2 | 001E | <handler> | 0002 | 0x00LL`. The **dynamic** Level bound
("<= the number of Bushido Counters") cannot be expressed by that static field —
but the row lives in overlay-3 RAM, so a small stub can **write the level nibble
at activation time** from `0x021A3054(side, zone, 6)`, i.e.
`extra = 0x80 | (min(N, 12) << 2)`. That is far cheaper than reimplementing the
search.

**Known deviation to decide:** the row filters by ONE set code. "Six Samurai"
is `0x1E`; **"Shien" is not a set code at all**. So a plain row gives
"Six Samurai only", dropping Great Shogun Shien / Footsoldier / Enishi / Squire
as targets. Matching the real card needs either a second row/pass or a hook in
the criteria handler `0x0223CAB5`.

## Ruled out / hazard hit

- **A register-only scan of the per-cid switch is NOT trustworthy here.** I
  decoded `LDR Rd,[PC]` + `ADD/SUB Rd,#imm8` across `0x02206CAC..0x02206F00` and
  it reported 14 cids — but it did **not** find `0x1B3A` or `0x1F76`, which
  provably route into this function via their cls records. That is exactly the
  documented `thumb.stack_based_switch` footgun: these switches keep the compare
  base in **`[sp,#n]`**, which a register-only simulator does not model, so its
  answers are wrong. Several of the 14 (e.g. `0x1B39` Great Shogun Shien) are
  almost certainly **summon TARGETS loaded in leaves**, not switch keys.
  **Do not build on that list.**

## Next experiment (clause 2, step 2)

The CFG walk is DONE (step 1 complete). The phase jump table decodes to:
`0x78 -> 0x02206EF4, 0x79/0x7A/0x7D -> 0x02206EFE (exit), 0x7B -> 0x02206EE8,
0x7C -> 0x02206E62, 0x7E -> 0x02206E4E, 0x7F -> 0x02206E2A, 0x80 -> 0x02206CE4`.
Only phases **0x80** (9 cids incl. `0x247D`) and **0x7C** (8 cids) carry per-cid
arms, and every cid in them is a "SS from Deck" card — they are the exception
list, not the mechanism. `0x1B3A` / `0x1F76` are absent from both because their
behaviour is fully described by their criteria-registry rows.

Remaining, in order:

1. **Decode the criteria handler `0x0223CAB5`** (Footsoldier's and Crystal
   Beacon's and Tanngnjostr's) — it is the function that consumes `+0x02`
   (set code), `+0x08` (flags) and `+0x0A` (level/type). This is what a "Shien
   OR Six Samurai" hook would have to touch, and what a runtime level-nibble
   write must run before.
2. **Pick the phantom** to drop for the count-neutral insert into
   `0x022713C4`, and confirm the row count immediate consumed by
   `0x02243B9C`.
3. **Confirm on the emulator** that a Footsoldier trigger really reaches
   `0x02206CAD` phase 0x80 and then `0x0223CAB5` -- before writing any patch.
   Nothing here has been observed live yet; it is all static reading.


---

# Clause 2 — BUILT (Six Samurai variant), untested in-game

Two count-neutral inserts, **no new code**:

- **G1 — cls3 record.** Cloned from **Six Samurai United's `cls3[370]`**, which
  is already exactly this card's activation shape ("You can send this card to the
  GY; *payload*"). Only the cid and the resolution slot change:
  `+04 0x022065B9` (draw N) → **`0x02206CAD`** (SS from Deck);
  `+08 0`; `+0C 0x021FD489`; `+10 0x021E6FF5`; `+14 0`.
  **`+0C 0x021FD488` is the win** — it is the activation condition "do I hold
  >= 1 counter of type R2?", and its per-cid `R2` **defaults to 6 (Bushido)**
  (only `0x1F78`→0 and `0x23A5`→0x17 are special-cased), so the donor inherits
  the Bushido test for free. It reads the count with `0x021A3054(side, zone, 6)`
  — the same accessor PART E's capacity gate uses.
  Insert: drop phantom row **223** (cid `0x1941`), shift rows 224..233 down one,
  donor lands at **cls3[233]** between `0x19A9` and `0x19BB`. Count stays 776.
- **G2 — criteria-registry row.** Row **409** was *itself* a phantom
  (cid `0x19B5`, no card_prop) sitting between `0x19B1` and `0x19B6`, so the
  donor's row overwrites it **in place with no shifting** and the sort order
  still holds. Contents mirror Shien's Footsoldier:
  `{0x19B2, setcode 0x001E, handler 0x0223CAB5, flags 0x0002, extra 0x0090}`.

`verify()` guards both inserts for count-neutrality **and** sortedness, and
asserts Footsoldier's own row (the structural template) is untouched.

## Two deliberate, documented deviations from the printed card

1. **Six Samurai only.** The criteria row filters by ONE set code. "Six Samurai"
   is `0x1E`; **"Shien" is not a set code anywhere in this engine**, so Great
   Shogun Shien / Footsoldier / Enishi / Squire are not yet valid targets.
   Adding them needs a hook in the criteria handler `0x0223CAB5`.
   *(This is the variant the user explicitly asked for.)*
2. **The Level bound is STATIC (`<= 4`), not "<= the Bushido Counters".**
   `+0x0A` is a static field. Making it dynamic means writing
   `0x80 | (min(N,12) << 2)` into it at activation time — best hooked by pointing
   **our own record's `+0C`** at a stub that does the write and then tail-calls
   `0x021FD489` (no shared-function surgery, since that slot is ours alone).
   The stub is ~44 B; the largest contiguous **free ov3 dead block is 28 B**
   (132 B total but fragmented). It **cannot** live in ov5 — a puzzle evicts ov5
   and the record slot would branch into dead memory. So this is **blocked on ov3
   cave space**: either the ov3 BSS cave (`CAVE3_*`, gated on an un-run canary),
   or measuring a larger dead block.

## Next experiment (clause 2)

**Nothing here has been observed live.** Test:

1. Deck: Shien's Dojo + several Level <= 4 Six Samurai (Kizan `0x245F`,
   Kageki `0x2461`, Yariza `0x1B33`).
2. Activate Dojo, summon a Six Samurai to put >= 1 Bushido Counter on it.
3. Activate Dojo's effect. Expect: **Dojo is sent to the GY** and you may
   **Special Summon 1 Level <= 4 "Six Samurai" monster from the Deck**.
4. With **zero** counters the effect must be **unavailable** (that is `+0C`
   `0x021FD489` doing its job).
5. Regression: Six Samurai United's own "send to GY; draw" must still work, and
   Shien's Footsoldier must still search on battle-destruction.

If the effect does not appear at all, the first suspect is an analogous hidden
gate to the PART E capacity one — check that `0x02206CAD` phase 0x80 is reached
and that the criteria handler `0x0223CAB5` reads our row.


---

# How the 3DS build does it (answers the dynamic-Level question)

⚠️ The 3DS build is a **different binary** (ARMv6, different VA base). Per
CLAUDE.md its addresses must **never** be mixed into the NDS namespace — they are
quoted below only as provenance. The *cid namespace is shared*, which is what
makes the comparison legitimate.

**Shien's Dojo exists in the 3DS build**: `3ds_name.bin` is **UTF-16LE** (not
ASCII — the first search missed it), and `3ds_card_prop.bin` has **no 8-byte
header** (records start at offset 0; with that fix the indx-derived entry indices
match exactly). Shien's Dojo = **cid `0x2538`**, Spell Card / Continuous. United
`0x1D22`, Footsoldier `0x1B3A`, Gateway `0x219A` all match the NDS cids.

The 3DS criteria registry is the same 12-byte row structure (found structurally:
a 2127-row sorted run). Rows:

```
 cid    filt   handler(3DS)  flags  extra
0x2538  FFFF   004AF93C      0002   0000    Shien's Dojo
0x1B3A  001E   004B1D74      0002   008C    Footsoldier
0x247B  001E   004B1C1C      0002   008C    Smoke Signal
0x1F76  1B39   004A6834      0802   0000    Six Scrolls
0x247D  001E   004AF2B4      0002   0000    Asceticism
0x219A  FFFF   004ADAD0      0002   0001    Gateway of the Six
```

**This independently CROSS-VALIDATES `counter.criteria_registry_layout`** — the
Footsoldier / Smoke Signal / Six Scrolls / Asceticism rows are byte-identical to
the NDS rows decoded from a completely different binary.

## The answer: the 3DS does NOT do the calc in data

- **Shien's Dojo's row carries no criteria at all**: `filt 0xFFFF` (no set-code
  filter) and `extra 0x0000` (no level bound).
- Its handler is used by **exactly one card — itself**. By contrast Footsoldier's
  handler is shared by **67** cards and Smoke Signal's by **135**: those are the
  generic, data-driven handlers parameterised by the row's filter/level fields.

So the engine implements "Six Samurai **or** Shien Effect Monster whose Level is
**≤ the number of Bushido Counters**" as a **bespoke handler function**, not as a
row. **The dynamic Level bound is not expressible as a data tweak** — that was
the open question, and the answer is no.

## What this changes for the NDS patch

1. My shipped clause 2 (`{0x19B2, setcode 0x001E, <generic handler>, 0x0002,
   0x0090}`) is a **data-driven approximation** of something the engine itself
   does in code. It is not wrong, it is *simplified* — exactly the two deviations
   already documented.
2. The proper NDS shape mirrors the 3DS: row =
   `{0x19B2, 0xFFFF, <our own handler>, 0x0002, 0x0000}` with **one bespoke
   criteria handler** that does BOTH the name/set-code filter and the
   counter-derived Level bound.
3. That **merges the two blockers into one**: there is no separate "level-nibble
   writer" stub and "Shien-name hook" — it is a single handler. But it is
   correspondingly bigger than the ~44 B estimated earlier, so **ov3 cave space
   is now firmly the gating task**: the ov3 dead-code pool (132 B, largest
   contiguous block 28 B) cannot host it. The ov3 **BSS cave** (`CAVE3_*`,
   ~0x2DC20 bytes) can — it is gated on the un-run canary in
   `notes/ov3-cave-findings.md`. **Running that canary is the next enabling
   step.**
4. Worth doing before writing the handler: disassemble the 3DS handler
   (ARMv6) purely to lift the **algorithm** — which primitives it calls, how it
   reads the counter count, how it expresses the "Shien" name group. Addresses
   stay in the 3DS namespace; only the shape crosses over.


---

# ⚠️ Correction: the criteria-handler ABI, and a bad assumption of mine

Decision taken: **the custom criteria handler goes in the ov5 cave** (user call).
That is consistent with CLAUDE.md's own norm — "injected code lives in the
overlay-5 cave and runs in normal duels only" — and the risk profile is the same
as every shipped ov5 patch: the handler pointer is **cid-keyed**, dereferenced
only when this card is actually involved, not on a shared always-executing path.
(My earlier ov3 insistence was correct for the PARTS B/E hooks, which fire on
every summon and every counter query, but overcautious here.)

## The ABI (proven)

`0x0223CAB4` (the generic handler used by Footsoldier, Crystal Beacon,
Tanngnjostr) is called with:

- **R0 = pointer to the card's 12-byte criteria row**
- **R1 = a context value**

and tail-calls the shared worker **`0x0223BC3C`** with
`r0 = ctx (R1 passed through)`, `r1 = row +0x00` (cid, `LDRH`),
`r2 = 0x0223C825` (a callback), `r3 = SP+8`, plus three outgoing stack words
`{[SP+0] = row +0x08 flags, [SP+4] = 0xA, [SP+8] = row +0x02 filter}`. The filter
is read with **`LDSH` (signed)** — which is exactly why `0xFFFF` reads as -1 =
"no filter". Siblings `0x0223CAF4` (Smoke Signal, adds to hand) and `0x0223E31C`
differ only in the callback and constants.

## The bad assumption — STOP before building on it

**None of the three handlers reads row `+0x0A`.** Each touches only `+0x00`,
`+0x02` and `+0x08`. So my earlier "`+0x0A` low byte = Level bound
(`0x80 | (L << 2)`)" was a **self-consistent bit pattern mistaken for a label** —
the same trap as `dispatch.master_handler_row_layout`. The pattern is real
(Lv<=3 cards share `0x8C`, Lv<=2 share `0x88`) but its *meaning* is unproven and
its consumer is unknown.

**Consequences:**

1. The shipped PART G row writes `extra = 0x0090` intending "Level <= 4". That
   may well be **inert** (or worse, mean something else). The Six-Samurai set
   code (`+0x02 = 0x001E`) and the handler are still sound, so clause 2 should
   still summon a Six Samurai from the Deck — but **do not trust the level
   restriction**. Test 3 below is now the priority.
2. I did **not** write the ov5 handler this session. Computing "Level <= counters"
   into a field the engine may never read would be guessing, which is exactly
   what the no-blind-build rule forbids. The ov5 decision stands; the handler
   waits on knowing where the level bound actually lives.

## Next experiment

1. **Find `+0x0A`'s consumer.** Search ov3 for reads at row-stride offset 10 off
   a pointer derived from `0x022713C4`, and disassemble the worker
   `0x0223BC3C` (and its callback `0x0223C825`) — the level bound is most likely
   applied there, since that is what actually walks the Deck.
2. **In-game check of the shipped build**: does Dojo's effect summon a Six
   Samurai from the Deck at all, and is the result restricted by Level? If a
   Level 5+ Six Samurai can be summoned, `+0x0A` is confirmed inert.
3. Only then write the ov5 handler, mirroring the 3DS shape
   (`row = {0x19B2, 0xFFFF, <ov5 stub>, 0x0002, 0x0000}`) with the filter and
   the counter-derived level both computed in code.


---

# Clause 2 CONFIRMED, and PART H (the dynamic Level bound)

**User's in-game result:** Shien's Dojo correctly **sends itself to the GY**, and
**can only summon Level <= 4 Six Samurai — Level 5+ is refused.**

That settles the field I had wrongly cast doubt on: **row `+0x0A` IS the Level
bound**, encoded `0x80 | (L << 2)`, and the seed value `0x0090` behaved exactly
as predicted.

## Lesson recorded (worth more than the fix)

My falsification test was **inconclusive, not decisive**. I checked whether the
three thin criteria handlers read `+0x0A`, found they don't (they touch only
`+0x00/+0x02/+0x08`), and concluded the field was probably meaningless. But the
bound is consumed **downstream** — in the worker `0x0223BC3C` or its callback,
which is what actually walks the Deck. *"The immediate caller doesn't read it"
is not evidence a field is dead.* This is now called out in
`counter.criteria_registry_layout` so the next session does not repeat it.

Both errors this session had the same shape and opposite signs: first I asserted
a bit pattern's meaning without proof (and was right by luck), then I retracted
it on an incomplete check (and was wrong). The emulator settled both.

## PART H — counter-derived Level bound (BUILT)

Because the bound is **plain data**, the dynamic version needs no replacement
handler at all — just a rewrite of the row's bound byte before each search:

- Host: **ov5 cave `CAVE_DOJO_LVL = 0x0239BF54`** (0x40 reserved, 44 B used).
  ov5 is safe here and was the user's call: a cls-record slot is **cid-keyed**,
  dereferenced only when this card is involved — unlike the PART B/E hooks, which
  fire on every summon / every counter query and must stay in ov3. The ov5 cave
  notes already record deck-search stubs working in a normal duel (Reborn Tengu,
  Gravekeeper's Recruiter). Cost: normal duels only, the project's documented norm.
- Installed as the donor's **own `cls3[233] +0C`** slot (the activation
  condition), so there is no shared-function surgery.
- It does: `N = 0x021A3054(side, zone, 6)`; clamp to 12;
  `STRB (0x80 | (N << 2))` into `0x022726FA` (= the row's `+0x0A` byte); then
  `BLX 0x021FD489` and return the native condition's verdict unchanged, so the
  "do I hold >= 1 Bushido Counter?" gate is preserved verbatim.

Disassembled out of the built ROM and confirmed Thumb-1 and correct.

## Test PART H

1. Dojo face-up with **1** Bushido Counter -> activating should offer only
   **Level 1** Six Samurai (e.g. none; the list should be near-empty).
2. Build to **3** counters -> Level <= 3 (Kageki `0x2461` Lv3 legal,
   Kizan `0x245F` Lv4 refused).
3. Build to **4+** -> Kizan becomes legal.
4. With **0** counters the effect must still be unavailable.

## Remaining deviation (unchanged, accepted)

"Six Samurai" only — `0x1E` is a set code, "Shien" is not one anywhere in the
engine, so Great Shogun Shien / Footsoldier / Enishi / Squire are not targets.
Fixing it needs a custom criteria handler (ABI in `counter.criteria_handler_abi`);
the 3DS build does exactly that, with a handler bespoke to this one card.


---

# Is there a set code covering both Six Samurai and Shien?  **No.**

PART H is **confirmed working in-game** (user), so clause 2 is now complete except
for the "Shien" name group. That prompted the question: is there a broader set
code containing both groups?

Enumerated **all 112 set codes** via the ARM9 thunk pointer table `0x0209D0D8`
(index = set code; `ptr[0x1E] = 0x02023A19`, the known Six Samurai thunk, anchors
the indexing).

- **Set code `0x1E`** owns **three** member tables:
  - `0x0209CA8C` (18) — the Six Samurai monsters
  - `0x0209C5C2` (4) — the Six Samurai Spell/Traps
  - `0x0209C712` (8) — the six original Six Samurai + **Great Shogun Shien
    `0x1B39`** + Shi En `0x2474`
- **Set code `0x4F`** owns `0x0209C664` (7) = **the "Shien" name group**:
  `{0x19C3, 0x1B39 Great Shogun Shien, 0x1B3A Footsoldier, 0x1C81 Enishi,
  0x2465 Shien's Squire, 0x24EB, 0x251C}` (the last two are phantoms with no
  card_prop — plausibly reserved for Shien's Advisor / Daredevil, absent here).

**So "Six Samurai OR Shien" = set code `0x1E` OR set code `0x4F`.** Two codes, and
a criteria-registry row holds exactly one. There is no combined code — the
hypothesis was worth testing and is disproven.

## But this makes the fix much cheaper than expected

The remaining deviation no longer needs a name-matching reimplementation. A
custom criteria handler only has to **OR two existing set-code thunks** — both
already exist and are engine-proven. Per `counter.criteria_handler_abi` the
handler gets `R0 = row pointer`, `R1 = ctx`, and tail-calls the worker
`0x0223BC3C` with the filter as a signed stack word. The open design question is
whether that worker can express a two-code filter at all, or whether the handler
must call it twice (once per code) and merge — **that is the next thing to
determine**, and it is static disassembly, no emulator needed.

Note `0x0209C664` is only 7 entries with 2 phantom slots, so it is also a
candidate for count-neutral edits if a "Shien" membership ever needs extending.


---

# PART I — "Six Samurai OR Shien" (CONFIRMED IN-GAME)

The last deviation. A criteria row holds one set code and the card needs two
(`0x1E` Six Samurai, `0x4F` Shien — no combined code exists). The fix turned out
small because **the deck search is callback-driven**:

The generic handler `0x0223CAB4` hands the worker `0x0223BC3C` a per-candidate
predicate `0x0223C825`, which does:

```
r0 = [[sp+0]] & 0x3FFF      ; the candidate's cid (low 14 bits)
r1 = [[sp+4]]               ; the filter = the row's set code
tail-call 0x020240D9(cid, setcode)
```

and `0x020240D8` is just `if setcode < 0x70: return 0x0209D0D8[setcode](cid)`.
So ORing two codes = replacing that **one predicate**.

- **`CAVE_DOJO_CB = 0x0239BF94`** (36 B) — the OR predicate:
  `has_set_code(cid, 0x1E) || has_set_code(cid, 0x4F)`.
  ⚠️ It reads its argument from `[sp,#0]` **before** pushing anything — that slot
  belongs to the worker's frame, and any push first would shift SP out from
  under it. (This is the one genuinely delicate bit of the stub.)
- **`CAVE_DOJO_CRIT = 0x0239BFD4`** (36 B) — a faithful clone of `0x0223CAB4`
  with the baked-in callback literal swapped for `CAVE_DOJO_CB`. Identical stack
  shape (`PUSH {R1,R2,R3,LR}` reserving the three outgoing words
  `{flags, 0xA, filter}` with `R3` -> the filter slot). The row's `+0x02` stays
  `0x001E`, so anything else that reads the filter is unchanged; our predicate
  simply ignores it.
- The criteria row's handler `+0x04` now points at `CAVE_DOJO_CRIT | 1`.

Both stubs were disassembled **out of the built ROM** and are Thumb-1 clean.

⚠️ `verify()` checks the ov3 side (including that the row points at our handler)
but does **not** re-read the ov5 stubs — `install_cave` asserts the slot is free
and the blob fits, and the disassembly above is the real check.

## Test PART I

1. Deck: Shien's Dojo + **Great Shogun Shien `0x1B39`** (Lv7),
   **Shien's Squire `0x2465`** (Lv2, Tuner), **Enishi `0x1C81`** (Lv6),
   plus Six Samurai (Kizan Lv4, Kageki Lv3).
2. Few counters -> **Shien's Squire** (Lv2) should now be a legal target, which
   it was NOT before this part. That is the single clearest pass/fail.
3. Build counters to 6-7 -> **Enishi** and then **Great Shogun Shien** should
   become legal.
4. Regression: Six Samurai targets must still work (Kizan/Kageki), and Shien's
   Footsoldier's own Deck search must still be Six-Samurai-only and Level<=3 —
   it uses the untouched native handler.
