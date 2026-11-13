# Dragunity Remus — findings

Donor: **Petit Dragon `0x106E`**. Clause in scope: **C2** (discard this card; add 1
"Dragon Ravine" from your Deck to your hand). Session opened 2026-09-21.

Printed text (`scratch/ygoprodeck_cache.json`; WIND Dragon / Tuner, Level 2, 800/800):

> Cannot be used as Synchro Material, except for the Synchro Summon of a "Dragunity"
> monster. You can discard this card; add 1 "Dragon Ravine" from your Deck to your
> hand. If you control a "Dragunity" monster: You can Special Summon this card from
> your GY, but banish it when it leaves the field, also you cannot Special Summon
> monsters from the Extra Deck for the rest of this turn, except Dragon monsters.
> You can only use each effect of "Dragunity Remus" once per turn.

| # | Clause | State |
|---|--------|-------|
| C1 | Cannot be Synchro Material except for a "Dragunity" Synchro Summon | not implemented |
| C2 | Discard this card; add 1 "Dragon Ravine" from your Deck to your hand | **IN-GAME CONFIRMED by user 2026-09-21** |
| C3 | GY self-SS if you control a Dragunity + banish-on-leave + Extra-Deck lock | not implemented |
| C4 | Each effect once per turn | deferred (user decision 2026-09-21) |
| D | "Dragunity" set-code membership (displaces Trident `0x2180`) | **IN-GAME CONFIRMED by user 2026-09-21** |

**Status: SHIPPED 2026-09-21 on the user's "ship it".** Everything except C3c is
in-game confirmed. Wired into `steps.STEPS` + `_verify_all_patches.SHIPPED` only —
NOT `apply_all_patches` (`ship-to-steps-only`). Combined build **73/73 steps**,
`rom_all_patches.nds` sha256 `07cb6876fd21dcd2f28bf94fa8ee78b9980676358db382ab5ab7ed7852d166e7`;
verify sweep **59 passed, 0 failed**, which includes `patch_junk_speeder`,
`patch_jet_synchron`, `patch_jet_warrior` and `patch_revolution_synchron` —
every patch that shares machinery with this card.

⚠️ Oracle re-baselining is RETIRED (user, 2026-09-14): `CURRENT-BASELINE.md`'s
hash is frozen deliberately and was **not** updated.

---

## Confirmed

*(each item verified THIS session against the committed oracles `arm9.bin` / `nds_overlay_3.bin`)*

### The card is absent from the 3DS build

Scanned all 5888 records of `3ds_extract/partition0/romfs/duel/card/CARD_Indx_E.bin`
(name offsets into `CARD_Name_E.bin`, cid from `CARD_Prop.bin` record *i* masked
`0x3FFF`). The 22 hits matching `Dragunity|Ravine` are exactly the 21 Dragunity cards
+ Dragon Ravine that the NDS already ships. **Reference source #2 is exhausted for
this card** — there is no Konami implementation to port, so NDS disassembly is the
legitimate path here.

### Dragon Ravine is `0x2359`

`scratch/cid_to_name.json`. It owns two criteria rows:
`crit[1248] {0x2359, aux 0x4A, fn 0x0223CAF5, w 0x00900002}` ("add 1 Level 4 or lower
Dragunity from your Deck") and `crit[1249] {0x2359, aux 0xFFFF, fn 0x0223CAD9,
w 0x08000002}` ("send 1 Dragon from your Deck to the GY").

### The "discard this card; add 1 named Field Spell from your Deck" family

`0x1BC1`–`0x1BC7` — Elemental Hero Captain Gold (Skyscraper), Gravekeeper's Commandant
(Necrovalley), Warrior of Atlantis (A Legendary Ocean), Destroyersaurus (Jurassic
World), Zeradias (The Sanctuary in the Sky), Archfiend General (Pandemonium), Harpie
Queen (Harpies' Hunting Ground). C2 is this effect with one name changed.

All seven share the identical cls2 record and own **no criteria row**:

```
cls2[262..268] {cid, 0x0000, main 0x0220DDA5, 0, cond 0x021F7F55, res 0x021E6FD9, 0}
```

### ⚠️ That family's main is NOT transplantable — RULED OUT, see below

### Criteria handler `0x0223D075` is the cid-blind named-card Deck selector

Disassembled `0x0223D074` this session:

```
push {r1,r2,r3,lr}
adds  r2, r0, #0          ; r2 = the criteria row
movs  r0, #2
ldrsh r0, [r2, r0]        ; r0 = (s16) row[+2]  = AUX
cmp   r0, #0
bgt   +2
ldrh  r0, [r2]            ; aux <= 0  ->  fall back to the ACTING cid
str   r0, [sp, #8]        ; [sp+8] = TARGET CID
ldr   r0, [r2, #8]
add   r3, sp, #8
str   r0, [sp]            ; [sp+0] = the criteria WORD
movs  r0, #0
str   r0, [sp, #4]        ; [sp+4] = flags 0  (controller's side, no SS/banish action)
adds  r0, r1, #0          ; r0 = side
ldrh  r1, [r2]            ; r1 = acting cid
ldr   r2, =0x0223C6F1     ; the match filter
bl    0x0223BC3C          ; the SINGLE-ZONE (Deck) candidate builder
pop  {r1,r2,r3,pc}
```

**aux is the target cid.** 51 rows use it, and every legible one is a named search:

| row | acting | aux | target | printed |
|-----|--------|-----|--------|---------|
| 96 | `0x1308` Fusion Sage | `0x12E5` | Polymerization | *Add 1 "Polymerization" from your Deck to your hand.* |
| 767 | `0x1EAA` White Stone of Legend | `0x0FA7` | Blue-Eyes White Dragon | *add 1 "Blue-Eyes White Dragon" from your Deck* |
| 121 | `0x139D` Birdface | `0x0FE4` | Harpie Lady | *add 1 "Harpie Lady" from your Deck* |
| 1380 | `0x24E1` Gem-Turtle | `0x22D6` | Gem-Knight Fusion | *add 1 "Gem-Knight Fusion" from your Deck* |
| 352 | `0x189F` Machina Defender | `0x18A3` | Commander Covington | *Add 1 "Commander Covington" from your Deck* |
| 76 | `0x114F` Thunder Dragon | `0xFFFF` | (self) | *add up to 2 "Thunder Dragon" from your Deck* |

`0x0223BC3C` is the Deck enumerator (`patch_thunder_sea_horse` PART A1 documents its
callback: candidate-entry pointer into the real deck array at `player+0x304`).
Contrast Neo Space Pathfinder `0x1C29`, whose *"from your Deck **or Graveyard**"* uses
a different handler `0x0223E351` — so `0x0223D075` really is single-zone Deck.

### Generic main `0x02207EF5` defaults to "add 1"

Disassembled `0x02207EF4`: opens with a per-cid switch on `desc[+0]` whose arms are
special cases only — `0x200B`, `0x2049` (`0x200B+0x3E`), `0x220C`, `0x23CA`
(`0x23E4-0x1A`), `0x23E4`, `0x24E1` (`0x23E4+0xFD`). Every other cid takes
`b 0x02207FCC` with `r4 = 1`. 105 cls users across the four tables (43 of them cls2),
incl. Birdface, White Stone, Green Gadget, Machina Defender, Gem-Turtle — all
"add 1 named card from Deck to hand".
**`0x106E` is not one of the six special cases.**

### Cond `0x021F0821` / cost `0x021E6FD9` are cid-blind (inherited, re-checked)

KB `dispatch.hand_discard_ignition_cls2_slots` (VERIFIED): cond `0x021F0820` is the
floodgate + "candidates >= 1 via the criteria row keyed on `desc[+0]`", cid-blind for
any donor outside `{0x1FC9, 0x2049, 0x2410}`; cost `0x021E6FD8` discards self by
`desc[+0xC]` with no cid use. Re-disassembled both this session — unchanged.
In-game confirmed by user 2026-09-17 on Fiend Kraken `0x0FEC`.

### The hand offer gate is ARM9 LIST A, and `0x0EB2` is its last free phantom

KB `dispatch.hand_effect_offer_list` (VERIFIED): list `0x0209BC4E` ×30, sorted, count
`movs r2,#0x1E` at `0x02023550`. Read live this session — members are Kuriboh `0x0FE0`,
Thunder Dragon `0x114F`, Fiend Kraken `0x0FEC` (thunder_sea_horse's donor, already in
the stock arm9? **no** — the stock list still shows phantom `0x1B42`; `0x0FEC` is
inserted by the patch at build time), Captain Gold `0x1BC1` … Zeradias `0x1BC5`, …
Stock phantoms: `0x0EB2` and `0x1B42`. `0x1B42` is claimed by `thunder_sea_horse` in
`otn_enhanced/docs/engine/allocations.yaml`; **`0x0EB2` is the only one left.**

### Donor Petit Dragon `0x106E` is clean

- Vanilla **Normal Monster**, **WIND / Dragon / Level 2**, 600/700 — exact attribute,
  race and level match to Dragunity Remus (only ATK/DEF and the Tuner flag differ).
- Records-free in **all four** cls tables (cls2 `0x02275C04`, cls0 `0x0227E64C`,
  cls1 `0x022860D4`, cls3 `0x02279D74`).
- No criteria row (`0x022713C4` ×`0x56C`), no row in the ignition-cond registry
  `0x0226FAFC` (×`0x92`).
- Member of **no** set-code list (walked all `0x0209D0D8` thunks), and in neither the
  hand-effect list `0x0209BC4E` nor the quick-effect list `0x0209BC8C`.
- Absent from `otn_enhanced/docs/engine/allocations.yaml` entirely.
- **Literal scan:** exactly one u16 hit in arm9 at `0x02022E4E` — that is *inside the
  bsearch function's code* (`0x02022E44`), an instruction encoding, not a cid. Exactly
  one u16 hit in ov3 at `0x02270C00`, a **fusion-recipe row** (the neighbourhood is
  8-byte `{u32 cid, u16, u16}` records: Baby Dragon `0x0FAA`, Ryu-Kishin `0x0FAB`,
  Mystic Horseman `0x1001`, …). **No per-cid gate anywhere.**

### The Dragunity set code

Set code **`0x4A`**. `has_set_code` ptr table `0x0209D0D8[0x4A]` = thunk `0x02023DFD`.
Thunk shape `01 49 02 4b NN 22 18 47` at `0x02023DFC`; count immediate `movs r2,#0x15`
at `0x02023E00`; pool literal (list base) at `0x02023E04` = `0x0209CBC0`.

All 21 entries are **real cards** — Dux `0x20C4`, Legionnaire, Tribus, Darkspear,
Phalanx `0x20C8`, Gae Bulg `0x20DE`, Gae Dearg `0x20EB`, Vajrayana `0x2164`, Militum,
Primus Pilus, Brandistock, Javelin `0x2172`, Trident `0x2180`, Corsesca, Partisan,
Pilum, Angusticlavii `0x220F`, Barcha `0x221B`, Arma Leyvaten `0x2356`, Arma
Mystletainn `0x2357`, Aklys `0x2358`. **No phantom → a count-neutral insert is
impossible.** Dragon Ravine `0x2359` is correctly *not* a member.

### There is no free space in the set-code list region

Walked every `0x0209D0D8` thunk and mapped each list's `[base, base + 2n)`. The lists
are packed; every apparent gap is another cid list belonging to a differently-shaped
consumer thunk (the `10b5074912 22041c` / `38b51a493a22051c` variants I did not decode
in the first pass). Largest all-zero run inside the region is **2 bytes**
(`0x0209CE6A`). Growing the Dragunity list therefore needs a cascade, not slack.

Neighbourhood, contiguous:

```
AoJ        0x0209CB96  n=21  -> 0x0209CBC0
Dragunity  0x0209CBC0  n=21  -> 0x0209CBEA     thunk 0x02023DFC
Watt       0x0209CBEA  n=22  -> 0x0209CC16     thunk 0x02023EF4
Karakuri   0x0209CC16  n=22  -> 0x0209CC42     thunk 0x02023F44
```

AoJ and Watt have **no** free phantom. **Karakuri has five**: `0x24EC`, `0x251D`,
`0x251E`, `0x2539`, `0x2549` (none appears anywhere in `allocations.yaml`).

---

## Ruled Out

### Cloning the `0x1BC1`–`0x1BC7` cls2 record onto the donor

It would silently search **Polymerization**. Both that family's main `0x0220DDA5` and
its cond `0x021F7F55` resolve the target through **`0x0220DCC0`**, which is a per-cid
switch that hard-codes every target:

```
0x0220DCC0  ldrh r2,[r0]            ; acting cid
            ldr  r3,=0x1BC7
            ldr  r1,=0x12E5         ; *** DEFAULT TARGET = Polymerization ***
            cmp  r2,r3 ; bgt <high half>
            subs r3,r3,#5           ; 0x1BC2
            subs r3,r2,r3 ; bmi <low half>
            add  r3,pc ; ldrh r3,[r3,#6] ; add pc,r3   ; jump table @0x0220DCDE
                                                        ; over 0x1BC2..0x1BC7
  ... explicit compares for 0x1BAA, 0x0E93/0x0E94, 0x1D94, 0x1D6D, 0x1F56 ...
  arms load r1 = 0x18FF / 0x159D / 0x150B / 0x1AA7 / 0x175E / 0x169F / 0x183F ...
0x0220DD56  ldr r3,=0x1BC3
            cmp r2,r3 ; bne +
            bl 0x021A7C0C            ; Warrior of Atlantis takes a name-variant path
          + bl 0x021A7BC4            ; find <target cid> in side's Deck
```

A donor cid matches nothing and falls out with `r1 = 0x12E5`. **Do not use this
record.** (This is the `grep-the-template-cards-text-too` failure mode: the shared
handler hard-codes its own cards' targets.)

### Growing the Dragunity list into slack inside the set-code region

There is none — see Confirmed above.

### A native `res` slot that both posts the once-per-turn node and discards self

Scanned every non-null callback slot across all four cls tables and disassembled each
for `BL` targets: **zero** functions call both `{0x021D2584, 0x021E8E74}` (the turn-log
poster) and `{0x021C6DB4, 0x021E6FD8}` (discard self). Users of the poster are Gather
Your Mind `0x1626`, Spell Power Grasp `0x1FC8`, Pot of Benevolence `0x21E0`, Pot of
Duality `0x2321`, Snap Dragon `0x24DB`, Coat of Justice `0x2054` — all cards that do
not discard themselves. **C4 will need one ov5 stub chaining the two.**

---

## Built (2026-09-21) — CLAUSE 2 IN-GAME CONFIRMED BY USER 2026-09-21

User reported all four oracle items "Confirmed" (verbatim: *"1, Confrimed / 2.
Confirmed / 3. Confirmed / 4. Confirmed / Dragunity Remus is not yet part of the
dragunity table..."*). That is:

1. Remus is offered from hand (PART A / the ARM9 list gate works).
2. Activating discards him and adds **Dragon Ravine** to hand.
3. The option greys out when Dragon Ravine is not in the Deck.
4. The predicted deviations hold.

⚠️ Item 4 bundled TWO deviations and the user restated only the set-code one, so
"the effect can be used more than once per turn" is recorded as **expected, not
separately measured**. Do not promote it without asking.


`otn_enhanced/cards/dragunity_remus.py` +
`_build_dragunity_remus.py`. **Pure data — no ov5 cave, no injected Thumb**, so it
works in a puzzle too. NOT wired into `apply_all_patches` / `steps.STEPS` /
`_verify_all_patches.SHIPPED`.

| Part | Edit |
|------|------|
| A (ARM9) | hand-effect list `0x0209BC4E`: dropped phantom `0x0EB2`, inserted `0x106E` (30, sorted) |
| B (ov3) | cls2 `{0x106E, +04 0x02207EF5, +08 0, +0C 0x021F0821, +10 0x021E6FD9, +14 0}` over phantom `0x0E1D` |
| C (ov3) | criteria `{0x106E, aux 0x2359, fn 0x0223D075, word 0x00000004}` over phantom `0x0E3D` |
| E | card_prop + `card_text.CARD_TEXT[0x106E]` (full printed text) |

Build output — `rom_dragunity_remus.nds`, 129 518 216 B,
sha256 `d7b08b2b55864c10e60b8de5b784751e7a9785d120030021dc044804bbb789f2`.
`verify()`: **5 PASS / 0 FAIL**. `check_allocations`: OK, ledger in sync.
`verify_knowledge`: **532 facts, 489 PASS, 0 FAIL, 43 UNVERIFIED**.

card_prop read back from the built ROM (independent decode, not the writer's own
report): cid 4206, ATK 800 / DEF 800, **Tuner Monster**, WIND, Level 2, Dragon.

KB facts contributed this session (all VERIFIED, all passing):
`dispatch.named_deck_search_aux_is_the_target_cid`,
`dispatch.field_spell_searcher_family_hardcodes_its_targets`,
`setcode.dragunity_table_is_full_and_boxed_in`,
`card.dragunity_remus_clause2`.

### Not done: "Dragunity" set-code membership

User asked for the list to be grown (2026-09-21); it is **blocked, not dropped**.
The list is full (21 real cards) and boxed in (no slack in the region). Every
route costs something:

- **ov5 relocation — WRONG.** All 12 BL callers of the thunk are in ov3, resident
  in all five duel modes; ov5 is evicted by ov41 in a puzzle. The bsearch would
  read overlay-41 data and return silent wrong answers, no crash.
- **ov3 relocation — correct host, no room.** 38 B free, fragmented into 8–12 B
  blocks; the list needs 44 contiguous bytes.
- **Cascade either way — 5–6 shipped modules hardcode the neighbour bases**
  (`patch_wattcobra`, `ee/patches/wattcobra`, `patch_ninishi`, `ee/patches/ninishi`,
  `patch_karakuri_haipa` forward; `tg_table`, `patch_hyper_librarian`,
  `xsaber_table`, `patch_azure_eyes`, `ee/arm9.py`, `ee/test_utils.py` backward).
- **Displace a real member** — works today, zero collateral, costs one card's
  membership. The `patch_white_dragon_ninja` / Sazank precedent; user's choice.
  ⚠️ "Dragunity Mastery" is not in the ROM; "Dragon Mastery" `0x235A` is, but it
  is not a list member (it reads the set code, like Dragon Ravine `0x2359`).
- **The appended ARM9 cave `[0x020AF120, 0x020B7120)` — FALSIFIED, not open.**
  🔴 The canary was **run 2026-08-03 and freezes on entering a duel**
  (`notes/gladiator-beast-essedarii-findings.md`, "Phase 0 — RUN AND FAILED").
  ⚠️ That same note ALSO still contains the stale sentence "built 2026-07-27 and
  **never played**", two lines below the failure verdict; I quoted the stale half
  to the user on 2026-09-21 before spotting the contradiction. `0x020AF120` is the
  live NitroSDK OS **main-arena base**, consumed by the boot/autoload crt0 rather
  than by a runtime literal load, so a wrong raise white-screens at startup; one of
  its seven literals (`0x02081558`/`0x0208155C`) is a proven false positive
  (`notes/ov3-cave-findings.md`, "Round 3a — RISK PROFILE CHANGED").
- **The tail between the last set-code list and the pointer table — NOT free.**
  `0x0209D058..0x0209D0D8` (128 B) looked like a gap; it is a live
  `{u16 cid, u16 group}` table referenced from thunk `0x02023804` (ptr-table index
  0x07). Checked 2026-09-21. **There is no free space anywhere in the region.**

**Resolved: PART D is BUILT by displacement** (the `patch_white_dragon_ninja` /
Sazank precedent) — **Dragunity Knight - Trident `0x2180` gives up membership**
(user's choice 2026-09-21). Base `0x0209CBC0` and count immediate `0x02023E00`
are untouched; the array stays 21 entries, strictly sorted.

Trident was the cheapest slot in the list: no "Dragunity" test can reach it —
Level 10, Extra Deck, not searchable from the Deck, not equippable, and every
GY-targeting Dragunity effect filters "Level 3 or lower Dragon". It keeps its
effect, its Synchro materials and its Extra-Deck presence; it forfeits only its
contribution to Dux's "gains 200 ATK for each Dragunity card you control".

New pool `dragunity_setcode_table` in `check_allocations.PHANTOM_CLAIMS`
(`0x2180` displaced, `0x106E` joins).

**PART D IN-GAME CONFIRMED BY USER 2026-09-21** (second test, oracle items 6–10,
all five reported "Confirmed"): Dragon Ravine fetches Remus; Dux counts him;
Trident still summons and keeps its effect and Extra-Deck presence, having lost
only membership; the other 20 Dragunity cards are unaffected; and Fusion Sage /
Birdface / The White Stone of Legend still search Polymerization / Harpie Lady /
Blue-Eyes, so the shared handlers were not disturbed.

## C4 — IN-GAME CONFIRMED BY USER 2026-09-21 ("C4 lands")

Two ov5 stubs, `CAVE_DR_COND = 0x023A1080` (44 B) and `CAVE_DR_RES = 0x023A10C0`
(32 B), behind `ENABLE_C4 = True`. The cls2 record's `+0C`/`+10` now point at them.
Build: 9 PASS / 0 FAIL, sha256
`85aa21374da9b281f8c39e3245152c2baf3020a8ffd6146347cccb0ce7267785`.

Mechanism — `dispatch.turnlog_once_per_turn_pair`, both halves cid-generic (they
read the cid from the descriptor, so a donor does not hit a do-nothing default):

- cond shim: `IS_RESOLVE_CTX 0x021D2B88` guard → `TURNLOG_QUERY 0x021A14E8(p, 0x0B,
  desc[+0], 1)` → deny on a hit → else chain the native cond `0x021F0820`.
- res shim: `IS_RESOLVE_CTX` guard → `NODE_ATTACH 0x021D2584(p, desc[+0], 1, 0)` →
  chain the native discard-self `0x021E6FD8`.

Both emitted stubs were **disassembled from the built ROM**, not trusted from the
assembler: correct BL targets, `pop {…, pc}`, no Thumb-2, no BLX-to-even-literal.

⚠️ This makes **C4 normal-duel-only** (`cave.normal_duel_only`) — the cls2 record
now points into the ov5 cave, which ov41 evicts in a puzzle. C2's data path is
unchanged, but the record as a whole is now cave-dependent.

⚠️ A per-SLOT latch (key `0x0FB6`) was NOT usable: Remus discards himself as the
cost, so no slot survives to carry the flag. It has to be the per-name turn log.

## C1 — IN-GAME CONFIRMED BY USER 2026-09-21 ("C1 Lands")

Unblocked by the user on 2026-09-21 ("Yes add it as a chain point to junk speeder").

`CAVE_DR_C1 = 0x023A1100` (56 B), behind `ENABLE_C1 = True`. Remus is a **Tuner**,
so the driver `0x02249C60` sends him to OUTER `0x022485B4`, and the gate is OUTER's
`bl 0x0224829C` at **`0x022485D8`** — TUNER-ONLY by construction, so no is-a-Tuner
test is needed (`synchro.tuner_gate_hook`, in-game confirmed 2026-09-02 on Junk
Speeder).

The stub, disassembled from the built ROM: replay INNER → if it already rejected,
return unchanged → else `0x021A3320(r1, r2)` for the material's cid → if it is not
`0x106E`, return unchanged → else `has_set_code[0x4A]` on the **Synchro's** cid
(r0) and return that. It restores r1/r2/r3 on exit because INNER preserves r1–r7
via `push {r1-r7,lr}`, so a drop-in replacement must too.

### The chain, and why it is order-independent

`0x022485D8` is the **only** Tuner-side gate and `patch_junk_speeder` was there
first. Rather than clobber it, the two now chain — the Boggart/Quasar precedent at
`0x022482B2`/`0x022482B6`:

```
0x022485D8  ->  CAVE_JSP_TUNER  ->  CAVE_DR_C1  ->  INNER 0x0224829C
```

The only change to `patch_junk_speeder` is that its stub's "call INNER" became a
**parameter** (`build_tuner_gate(base, next_link=None)`). Its own rule is
byte-identical; only the address it delegates the base verdict to moves. Plus:
`chain_tuner_gate()` for another patch to insert itself, and `apply_tuner_gate()`
now **adopts** a foreign hook at the site as its next link instead of asserting.

⚠️ `ov5_cave.install_cave` refuses a non-zero slot by design (that is what stops two
patches overlapping), so re-chaining goes through `_reinstall_tuner_gate`, which
clears the slot **it already owns** first rather than weakening the guard.

**Both build orders were tested statically 2026-09-21** and converge on the same
chain:

| order | result |
|---|---|
| junk_speeder → dragunity | `site → CAVE_JSP_TUNER`, JSP.next → `CAVE_DR_C1` |
| dragunity → junk_speeder | `site → CAVE_JSP_TUNER`, JSP.next → `CAVE_DR_C1` |

In the single-card ROM (junk_speeder not applied) the gate takes the site directly
and calls INNER itself — which is what the current build does (`G C1 site
0x022485D8 reaches the gate (direct)`).

⚠️ **`patch_junk_speeder`'s clause 1 is in-game confirmed (2026-09-02) and its gate
has now changed shape.** Its rule is byte-identical, but it has not been re-tested
since. Junk Speeder should be re-checked in the same duel as C1.

## C3a — IN-GAME CONFIRMED BY USER 2026-09-21

The two structural blockers dissolved; C3a (the GY self-Summon) is built. C3b
(banish-on-leave) and C3c (the Extra-Deck lock) are still not implemented, and
**the card is STRONGER than printed** until they are.

### Blocker 1 dissolved — one cls2 record, split on the path

A second cls2 record would shadow C2 (`find_event_handler` returns the leftmost).
Instead ONE record serves both clauses, split on `desc[+3] == 0x0E` — the GY-action
descriptor builder `0x0224C590` hardcodes that byte
(`dispatch.gy_action_offer_caps_the_event_code`), so it is a reliable positive test
for the GY path. Three thin splitters sit in front of the three slots; the **hand
path falls through to the in-game-confirmed C4 stubs, whose bytes are untouched**.
Same idiom as `patch_lightpulsar` and `card.jet_synchron`.

### Blocker 2 dissolved — the registry was NOT exhausted

The Grapha family `{0x0224C591, 0x0224C6C1}` is full (its three phantoms went to
grapha row 15 `0x0EB2`, lightpulsar row 47 `0x0E3E`, jet_synchron row 48 `0x0E64`).
But **all four fields of a row are data**, and the sibling family
`{0x0224C55D, 0x0224C669}` still had three unclaimed phantoms — rows 11 `0x1449`,
12 `0x144C`, 13 `0x1452`. `dispatch.gy_action_family_0224C55D_is_a_hand_gate`
correctly says that family cannot host a GY effect, but that is a property of its
two **functions**, not of the row slot. Rewriting a phantom row's chk/post to the
Grapha pair **converts** it, and every reader agrees because each discriminator is
a data comparison (enumerator scans `[row+4]` zone; reader D tests
`[row+0xC] == 0x0224C669`; reader B calls `post()`; reader C tests
`post != 0x0224C7C1`). Row count untouched, so the three imm8 bounds are undisturbed.

**Zero hooks, zero cave, puzzle-safe** — contrast `card.revolution_synchron` C2,
which synthesised a virtual row 60 in ov5 behind **four** hooks because this was not
known. Two sibling phantoms (rows 12/13) remain for future cards. New KB fact:
`dispatch.gy_action_row_is_all_data_so_a_family_can_be_converted`.

### What was built

| slot | address | role |
|---|---|---|
| `CAVE_DR_C3_COND` | `0x023A1160` (116 B) | cls2 +0C splitter: GY = kind-2 turn log + a face-up "control a Dragunity" zone walk; hand = C4 cond |
| `CAVE_DR_C3_MAIN` | `0x023A11E0` (32 B) | cls2 +04 splitter: GY = the SS resolver; hand = `0x02207EF5` |
| `CAVE_DR_C3_RES` | `0x023A1210` (44 B) | cls2 +10 splitter: GY = stamp kind 2 (no discard, it is in the GY); hand = C4 res |
| `CAVE_DR_C3_SS` | `0x023A1250` (52 B) | the self-Summon resolver: `0x80` CHAIN_PUSH + `GY_SELF_SS 0x0220731C` → `0x7F` CHAIN_POP → `0x64` |
| GY-action registry | row 11 | `0x1449` converted to `{0x106E, 0x0E, 0x0224C591, 0x0224C6C1}` |

C3a carries its **own** once-per-turn latch at turn-log **kind 2**, separate from
C4's kind 1, because the text says *each* effect once per turn.

Zephyrus's resolver `0x02230EBC` was **not** reused — it hardcodes his printed
400 LP self-damage (`dispatch.resolver_hardcodes_printed_damage`).

All four stubs were **disassembled from the built ROM**; BL targets exact, no
POP-into-LR, no BLX-to-even-literal, no Thumb-2.

## C3b — IN-GAME CONFIRMED BY USER 2026-09-21

⚠️ **I was wrong to call this unknown.** The user pushed back ("plague-spreader and
assault-synchron and jet synchron all do it") and they were right: the KB has had
the mechanism measured since 2026-09-02. I had scanned for a membership list
instead of grepping the KB for the printed phrase — the
`grep-shipped-patches-for-the-clause` rule, not followed.

**The mechanism** (`rider.banish_when_it_leaves_marker`): *"but banish it when it
leaves the field"* is a family-1 attached node `{key 0x1E15, kind 3, param 0}`.
`0x1E15` is a **marker constant, not a reference to Quillbolt** — Plaguespreader's
node carries the same key. `rider.banish_marker_is_cid_blind_to_the_destination`
closes it: the predicate `0x021B0950` tests four marker keys with **no cid in
scope**, and its caller `0x021CCBDA` rewrites the leave destination `0x0E` (GY) →
`0x0F` (banished). So `0x021C479C(side, slot, 0x1E15, 3, 0)` is sufficient for any
cid.

**Why a membership-list scan found nothing:** there is no list. The engine's own
attach is a per-cid switch arm, and only Plaguespreader `0x1EA9` and Quillbolt
`0x1E15` reach it — everyone else falls to the default leaf.

**Built as an arm on the shared hook** `summon_rider_hook.py` (site `0x02268666`, a
single 4-byte BL — so one module cannot own it). Now three arms: Jet Synchron
`0x224C`, Jet Warrior `0x23EB`, Remus `0x106E`.

**Reaching the default leaf was MEASURED, not assumed** — the KB warns a cid with
its own dedicated arm never arrives there. `scratch/summon_event_sim`:

| cid | leaf | |
|---|---|---|
| `0x106E` Remus | `0x02268666` | **DEFAULT** ✓ |
| `0x1EA9` Plaguespreader | `0x02268546` | dedicated arm (control) |
| `0x224C` Changer Synchron | `0x02268666` | DEFAULT (control) |

**The one-shot byte** `CAVE_DR_ARM = 0x023A12A0` is set by the C3a resolver at
phase `0x80`, *inside* the `desc[+3] == 0x0E` branch, so **only the Graveyard
revive riders** — a Normal Summoned Remus still goes to the GY. The byte is
cleared by the **consumer**, never the setter (the commit `0x0226925C` can finish
after the setting resolver returns — the window that killed upstart_golden_ninja's
first STAGE latch).

**The lift was proven BY EXECUTION**, per `otn-shared-hook-lift-prove-by-execution`.
`scratch/rider_hook_equiv` (extended this session to probe `0x106E`), 128 inputs
through both emitted blobs:

- `0x224C` Jet Synchron — **behaviour unchanged** (it is in-game confirmed; the
  lift must be transparent to it)
- `0x23EB` Jet Warrior — armed → attach, unarmed → no attach
- `0x106E` Remus — armed → `attach(side=1, slot=3, key=0x1E15, kind=3, param=0)`,
  own byte cleared, **no other card's byte clobbered**; unarmed → no attach

## C3c — NOT IMPLEMENTED, and the reason is now measured

*"You cannot Special Summon monsters from the Extra Deck for the rest of this turn,
except Dragon monsters."*

**There is no template.** Assault Synchron prints the same shape (*"except Synchro
Monsters"*) but that clause was **dropped by the user 2026-09-14** and never built.

**And the obvious hook cannot work.** `summon.legality_gate_and_mode_bits` proves
the summon-legality gate `0x021B9708(side, mode, cid)` is **cid-blind on the path
that matters**: the Special-Summon wrapper `0x021B9ECC` has **125 callers and
passes `r2 = 0`**, so the gate cannot tell *what* is being summoned. Only
`0x021B9EC0` (16 callers) carries a cid. A lock that must exempt Dragon monsters
needs the summoned card's identity, so it cannot be a mega-gate arm — it needs a
hook on the Extra-Deck summon path itself, which is unmeasured.

That is the next experiment, and it is a real one, not a guess.

## Open Questions

- ~~**C1:** may `patch_junk_speeder` be edited?~~ **ANSWERED 2026-09-21: yes.** Done,
  as a parameterised next-link. Junk Speeder's own rule is byte-identical but its
  gate changed shape, so **re-test Junk Speeder's clause 1** alongside C1.
- ~~**C3 (1):** is there a free GY-action registry row?~~ **ANSWERED 2026-09-21:**
  yes, by converting a sibling-family phantom — no virtual row, no hooks.
- **C3 (4):** what is the engine's shape for a *conditional* Special-Summon lock?
  Unmeasured. No card in the KB is documented with an Extra-Deck-only, type-exempt
  lock.
- **Ship C2 + D + C4?** Still single-card only — not in `apply_all_patches.PATCHES`,
  `steps.STEPS` or `_verify_all_patches.SHIPPED`.

## Next Experiment

Test C4 in-game first — it is built and costs one duel:

```
.venv-1/Scripts/python.exe _build_dragunity_remus.py     -> 9 PASS / RESULT: PASS
```

Then, in a **normal duel** (not a puzzle — C4 is cave-hosted):

1. Discard Remus #1 → Dragon Ravine added to hand.
2. Discard Remus #2 **the same turn** → the activate option must be **greyed out**.
3. Next turn → it works again.

- FAIL A (still usable twice): the node is not being posted. The write goes through
  the async command queue `0x021C3BC8`, so check the res shim actually ran.
- FAIL B (never usable, even the first time): the query is denying unconditionally
  — the `IS_RESOLVE_CTX` guard or the deny branch is inverted.

Regression check every build: Remus still offered from hand, still adds Dragon
Ravine, and Dragon Ravine still lists Remus.
