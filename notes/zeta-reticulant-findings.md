# Zeta Reticulant — findings (session 2026-08-04)

## Card text (authoritative — `scratch/ygoprodeck_cache.json`, id 64382839)

> You can Tribute 1 "Eva Token" to Special Summon this card from your hand.
> While this card is in your Graveyard, each time a monster(s) your opponent
> controls is removed from play, Special Summon 1 "Eva Token"
> (Fiend-Type/DARK/Level 2/ATK 500/DEF 500).

Stats: Fairy / Effect, DARK, Level 7, ATK 2400 / DEF 2100.

Clauses:
1. **Hand-SS with tribute cost** — Tribute 1 "Eva Token" → SS this card from hand.
2. **GY-resident banish-watcher** — while in *your* GY, each time a monster(s)
   *your opponent* controls is removed from play, SS 1 "Eva Token".

**SCOPE (agreed with user, 2026-08-04): BOTH clauses — the full, faithful card.**
Consequences: the Eva Token must really be Fiend/DARK/Lv2/500/500 (clause 1
Tributes it, clause 2 makes it), and the surviving on-death placeholder is *not*
reusable as behaviour (see the measurement below) — only as plumbing.

## Confirmed (this session)

### Baseline
- KB proofs green before any change: **183 facts, 155 PASS, 0 FAIL, 28 UNVERIFIED**.
  Oracles arm9/ov3/ov5 = yes, savestate = `rom_all_patches.ml2`.

### Identity — Zeta IS partly in the ROM, as a CUT card
- **Zeta Reticulant = cid `0x1A8A`** (6794). Sources agree: the decompiled file
  `data/over_the_nexus/decompiled/cards/c06794_i0219_Unknown_1A8A.py` (filename =
  `c{cid_dec}_i{idx}_{name}_{cid_hex}`, cross-checked against
  `c03000_..._0BB8.py` where 3000 == 0xBB8), and `CARDS_ZEXAL_3DS_ASM.md` §12
  ("Zeta Reticulant — Konami `0x1A8A` (6794)"). The 3DS doc's ID column matches
  our NDS cid space on every card we have shipped (T.G. Striker 0x2510, Warwolf
  0x2513, Hyper Librarian 0x2552, Quasar 0x25ED).
- **Eva Token = cid `0x0F5A`.**
- **Both are cut from the playable card database.** Neither has a `card_prop`
  record, a name, or a `card_intid` entry (`card_intid[cid] == 0x0000`, the
  "no such card" sentinel). They are *holes*, not phantoms-in-use.
- Neither cid is claimed by any shipped patch or by `PHANTOM_CLAIMS` (grepped
  `check_allocations.py` + all of `finished_patches/`) — **no collision**.

### The surviving Zeta effect data (three fragments)
1. **Token table row 31** @ `0x0226D57C`: `{cid 0x1A8A, token 0x0F5A, count 1,
   mode 2}` — "Special Summon 1 Eva Token".
2. **`cls2[220]`** @ `0x022770A4`: `{cid 0x1A8A, +04 = 0x02207A09, +08..+14 all
   NULL}`.
3. A `{u32 cid, u32 handler}` row @ `0x0228F350` → handler **`0x02261F8D`**,
   shared with **37 other cids** (Larvae Moth, Great Moth, Metalzoa, Red-Eyes
   Black Metal Dragon, Masked Beast Des Gardius + many holes). A generic
   template, not Zeta-specific — semantics NOT established, see Open Questions.

**cls2[220] is Dandylion-shaped.** Dandylion (0x19FE) is `cls2[203]` with the
identical slot pattern (`+04 = 0x02207A09`, rest NULL) and its real effect is
"if this card is sent to the GY: SS 2 Fluff Tokens". So the surviving fragment
encodes *"on this card's cls2 event → SS 1 Eva Token"* — it does **not** encode
"each time your opponent's monster is banished", and there is **no** surviving
hand-SS/tribute-cost record. Clause 1 and the trigger half of clause 2 are still
new work.

### Token summoning is TABLE-DRIVEN (reusable engine fact)
Every token-maker shares one resolver — searched all four cls tables (geometry
from `dispatch.cls_tables` / `dispatch.cls_table_selector`):

| card | cid | table | slot1 (+04) |
|---|---|---|---|
| Scapegoat | 0x12D2 | cls0[152] | 0x02207A09 |
| Ojama Trio | 0x166A | cls0[455] | 0x02207A09 |
| Dandylion | 0x19FE | cls2[203] | 0x02207A09 |
| Fires of Doomsday | 0x1D1E | cls0[901] | 0x02207A09 |
| Reptilianne Spawn | 0x2125 | cls0[1107] | 0x02207A09 |
| **Zeta Reticulant** | **0x1A8A** | **cls2[220]** | **0x02207A09** |

`0x02207A08` does `ldrh r0,[r5]` (descriptor cid) → `bl 0x021A2EE0`, then reads
`[r0,#2] → [sp,#0xC]`, `[r0,#4] → r6`, `[r0,#6] → [sp,#8]`. `0x021A2EE0` is a
**linear scan of 0x4C (76) 8-byte records based at `0x0226D484`** matching u16 at
+0 (`cmp r4,#0x4C / blo`; literal `0x0226D484` @ 0x021A2F00).

**Table `0x0226D484` layout: `{+0 u16 activating cid, +2 u16 token cid,
+4 u16 count, +6 u16 mode}`.** Verified on every named row: Scapegoat → Sheep
Token 0x0F3E ×4; Ojama Trio → Ojama Token 0x0F4B ×3; Dandylion → Fluff Token
0x0F55 ×2; Doppelwarrior → Doppel Token 0x0F84 ×2. Per-cid side flip (Ojama Trio
putting tokens on the *opponent's* field) is a resolver switch leaf @0x02207BAA
(`movs r0,#1 / subs r0,r0,r4 / str r0,[sp,#0x10]`).

Because the lookup is a **linear scan**, rows need no sort order — any cid may go
in any row. The table ends at 0x0226D6E4 with **no free gap** (battle-attribute
cid lists follow immediately), so adding a row means overwriting one; but for
Zeta *no new row is needed* — row 31 already exists.

### Card-database structure (needed for any "un-cut a card" work)
- **`card_prop.bin`** (bin2.pac): 8-byte header + **4305 records × 8 B**,
  **sorted by cid**, cid = **low 14 bits** of the record u64.
- **`card_intid.bin`**: **`u16[6049]`, NO header**, indexed by `cid - 0xD48`
  (6049 == the cid span 0xD48..0x24E8 exactly, and 6049×2 == 12098 == the file
  size). Value: **bit15 = "summonable monster" flag**, **low14 = card_prop index
  + 1**, **0x0000 = card does not exist**. Measured: Scapegoat 0x12D2 →
  0x0277 (low14 631, card_prop idx 630); Dandylion → 0x87D1 (2001 / idx 2000);
  Black Ptera 0x1A8E → 0x883C (2108 / idx 2107). Spell cards have bit15 clear,
  monsters set.
  - ⚠️ **This contradicts `patch_yubel_normal_summon.py`**, which indexes
    `intid.address + 8 + card_prop_index*2` (an 8-byte header, and keyed by
    card_prop index rather than cid). Both are wrong under the measurement
    above; `patch_aegis_cardprop.py`'s `intid.address + (cid - 0xD48)*2` is
    right. The Yubel patch is therefore very likely writing its 0x4000 bit into
    an unrelated entry. **Not yet re-verified in-game — flagged, not fixed.**

### Donor analysis (if we go the donor route rather than un-cutting)
`cls2` is sorted by cid and binary-searched, so retargeting `cls2[220]`'s cid
constrains the donor to the open interval between `cls2[219]` (0x1A86, a hole)
and `cls2[221]` (0x1A8E Black Ptera) → **0x1A87..0x1A8D**. Enumerating that
window, the only real cards are **Sabersaurus 0x1A8C** (Normal Monster, EARTH,
Lv4, 1900/500) and Miracle Jurassic Egg 0x1A8D (Effect Monster).
- **Sabersaurus 0x1A8C is RECORDS-FREE** — no record in cls0/cls1/cls2/cls3, no
  token-table row; only one stray aligned u16 in ov3 (@0x02209340, an immediate,
  not a record). It is the preferred donor per the Normal-Monster rule.

### THE BANISH PRIMITIVE — `0x021C7098` (clause 2's hook) — PROVEN

`0x021C7098(r0 = event ctx, r1 = card-locator ptr, r2 = flag) -> nonzero on
success` **removes a card from play**. It is a wrapper: it extracts the target's
side into r5 (`ldr r0,[r1] / lsls #0x11 / lsrs #0x1f`), calls worker
`0x021C7118`, and then runs a tail that fires only when the target's side !=
the acting side.

Proof (closed, static): `0x021C7098` has **31 BL callers**. Mapping each call
site to the cls-slot function that contains it, and joining the owning cid to
its ygoprodeck text, **25 of 31 owning cards' printed text explicitly says
banish / remove from play** — Karma Cut, System Down, Iron Chain Dragon,
Blackwing Vayu, Stardust Shimmer, Big Burn, Inferno Tempest, Dimension Jar,
Soul Release, Book of Life, Fiend Comedian, Question, Arcana Call, Factory of
100 Machines, Morphtronic Remoten, Memory Crush King, Gladiator Beast Lanista,
Ancient Gear Factory, Volcanic Counter, Tongue Twister, Phantom of Chaos,
Chaosrider Gustaph, Trap of Darkness, White-Horned Dragon, Ancient Gear Factory.
The 6 non-matching sites are 2 holes, 2 in Trishula (which banishes — its ROM
name failed the text join), and 2 in Speed Spell - Deceased Synchron (banishes).
No caller's text contradicts "banish". Found via D.D. Crow 0x1B44 (cls2[244],
resolver 0x02208D18), whose entire effect is "banish 1 card in a GY" and whose
only card-moving call is this one, gated on source zone `0xE` (= GY, matching
the Armory Arm gate).

### THE SPECIAL-SUMMON PRIMITIVE — `0x0226925C`

The token resolver's per-token loop ends in
`bl 0x0226925C(r0 = target side, r1 = ptr to built locator, r2 = 1,
r3 = mode(+6 field))` with `[sp] = (activating_cid << 16) | flags`.
**`0x0226925C` contains the already-known SS-commit hook `0x022692E6`**
(`summon.ss_commit_hook`, ANCHORED) at +0x8A — i.e. this is the generic
"Special Summon this card" entry point. An ov5 stub can call it directly.

Resolver phase protocol (matches `resolver_protocol`): `[0x0229xxxx + 0x70]`
selects the phase; 0x80 = ACT (validate + reserve zones, reset counter
`[X,#0x74]=0`, set `[X,#0x78]=count`), 0x7F = the per-token summon loop, and it
returns 0x7F to be re-entered until `[X,#0x74] >= [X,#0x78]`.

### CORRECTION — token `count` does NOT generally mean consecutive cids

I inferred from the loop (`r2 = [sp,#0xC] + [X,#0x74]`, i.e. token_cid +
counter) that a row with count N uses cids T..T+N-1. **Tested and falsified:**
of the 28 rows with count >= 2, only **6** have T..T+N-1 all sharing one name;
**22 mismatch** (e.g. Cloudian - Sheep Cloud → 2 tokens but only one Cloudian
Token cid exists, and T+1 is Engine Token).

The resolution: the `cid + counter` code at `0x02207D6E` is reached only through
a **per-cid switch at 0x02207D36** — exactly the ungreppable stack-based-switch
idiom the KB warns about. Only cards that own several distinct token cids
(Scapegoat ×4, Ojama Trio ×3, Dandylion ×2, Stray Lambs ×2) take it; every other
card reuses a single cid N times via the other leaf at 0x02207D9E.
**Consequence for Zeta: moot** — count is 1, so both paths are identical, and
only the single cid 0x0F5A is required.

### DONOR DECISION (user's proposal, adopted 2026-08-04)

**Zeta Reticulant ← Sweet Corn `0x2299`; Eva Token ← Grain Corn Token `0x0F7E`.**
Chosen as a *matched generator+token pair* — the user's suggestion, and better
than the earlier Zoa 0x112D + Grain Corn split, which would have left Sweet Corn
alive and spuriously summoning "Eva Tokens".

Why it fits:
- **Token-table row 66 is already `{cid 0x2299, token 0x0F7E, count 1, mode 2}`**
  — exactly "Special Summon 1 Eva Token". **No token-table edit is required.**
- Grain Corn Token `0x0F7E` is **records-free** (no cls0/1/2/3 record).
- `mode` = battle position: **1 = Defense** (Scapegoat, Ojama Trio, Dandylion all
  print "in Defense Position"), **0 = Attack** (Doppelwarrior, Nightmare
  Archfiends). Sweet Corn is **mode 2**, and its text specifies no position —
  matching Zeta's Eva Token, whose text also specifies none. Already correct.
- Consuming both halves means no orphaned generator.

To do for the donor: rewrite `card_prop` for 0x2299 →
Effect Monster / Fairy / DARK / Lv7 / 2400 / 2100 (currently Effect Monster /
Plant / EARTH / Lv2 / 0 / 0) and for 0x0F7E → Token / Fiend / DARK / Lv2 /
500 / 500 (currently Token / Plant / EARTH / Lv1 / 0 / 0); rename both; and
**neutralise or repurpose Sweet Corn's `cls3[690]`** (`+04` 0x02207A09,
`+0C` 0x02202DAD, `+10` 0x021E4E85 — its "once per turn, MP2, pay 500 LP,
summon 1 token" ignition), which Zeta must not keep.

### 3DS REFERENCE IMPLEMENTATION (Zexal: Duel Carnival, `code_dec.bin`)

`ygo_tools/reference_files/3ds_overlay_3.bin` **is** `code_dec.bin` (both exactly
6742016 B); VA = 0x00100000 + file offset, ARM mode. 3DS Zeta = Konami `0x1A8A`
(same id space as our NDS cid), card-DB cid `0x08D7`.

- **3DS text (UTF-16LE, `3ds_indx` 8-byte {name_off, desc_off} pairs indexed by
  cid) is the REAL card text**, verbatim ygoprodeck including "**removed from
  play**". This independently confirms the target text and the banish hook.
  ⚠️ `CARDS_ZEXAL_3DS_ASM.md` §12 paraphrases it as "sent to the GY" — **that
  note is wrong**; the game's own DB says removed from play.
- **Clause 1 = registry `0x6AC2D4` (stride 0x10) row 59 → handler `0x4B79E4`**, a
  shared "SS this card from hand by paying a self-declared cost" template used by
  **54 cards** (Raviel, Dogma, Turret Warrior, Galaxy-Eyes, Hieratic…).
  **The id field's high 16 bits encode the cost COUNT** — tested against the
  printed text on every member that states a number: **40 match, 1 mismatch**
  (Neos Wiseman). Zeta = `0x11A8A` → count 1. Turret Warrior ("Tribute 1
  Warrior-Type monster to SS this card from your hand") is the closest analogue.
- **Clause 2 — UNRESOLVED, and the repo note is suspect.** §12 claims registry
  `0x6AAA58` → handler `0x4A0F58` is Zeta's GY trigger. That table is really an
  array of 8-byte `{u32 id, u32 handler}` pairs (same shape as the NDS table at
  0x0228EFE8+, cf. the 0x0228F350 row), and 0x1A8A → 0x4A0F58 is real. **But
  disassembling `0x4A0F58` shows a field scan** (side 0..1 × zone 0..4, locate
  instance via 0x3AE3D8, compare `[r0,#0x43]` occupancy, read packed ATK/DEF at
  `[r0,#0x48]`, recompute via 0x3A9600 / 0x3A9608, write back via 0x384B10) —
  i.e. a **continuous stat refresher**, which Zeta has no clause for. Do not
  repeat §12's "GY trigger" label as fact until this is explained.

## Ruled Out

- *"Token summoning needs a custom ov5 stub."* — No. It is a cid-keyed data table
  (`0x0226D484`) consumed by a shared resolver (`0x02207A08`). Pattern A.
- *"Zeta Reticulant is simply absent from the ROM."* — Wrong (my first read, from
  `scratch/cid_to_name.json`). That file only covers the 4305 *playable* cards;
  the effect tables retain data for cut cids.
- *"cid 0x2349 is Zeta."* — My interim guess from the token table's unnamed rows.
  Wrong. 0x2349 is a *different* cut card (it has `cls1[1228]` and its own token
  row → token 0x0F80). Zeta is 0x1A8A, per the decompiled filename + 3DS doc.
- *"The registry at 0x0228E1E0 has stride 0x18."* — Not for this region. The rows
  around 0x0228F350 are 8-byte `{u32 cid, u32 handler}`; the region near
  0x0228E1E0 is 8-byte `{u32 handler, u32 cid}` (opposite order). At least two
  distinct tables share the area; my outward walk from 0x0228F350 spanned a
  boundary (came back "sorted? False"), so the 179-row extent is **not** a
  reliable table bound.
- *The decompiled file for this card is STALE and must not be trusted.*
  `c06794_i0219_Unknown_1A8A.py` claims "Table idx 219" and lifts a hand-SS
  resolver (0x02206ABC), an activation condition (0x021FB274) and a target filter
  (0x021EA6AC). Under the correct **cid-FIRST** geometry, 0x1A8A is `cls2[220]`
  with **only** `+04 = 0x02207A09`. The off-by-one index and the shifted slots are
  exactly the known cid-LAST 4-byte-shift bug (`dispatch.decompiled_dir_stale` /
  `dispatch.master_handler_row_layout`).

### What `cls2[220]` fires on — MEASURED (was an inference, now a fact)

Enumerated every `cls2` row whose slot pattern is **exactly** Zeta's (only
`+04 == 0x02207A09`, all other slots NULL). There are **11**, and all 10 named
ones are self-death / self-tribute token triggers:

| cid | card | printed trigger |
|---|---|---|
| 0x1543 | Statue of the Wicked | face-down card destroyed & sent to GY |
| 0x19FE | Dandylion | sent to GY |
| **0x1A8A** | **Zeta (hole)** | — |
| 0x1C63 | Cloudian - Sheep Cloud | destroyed by battle |
| 0x1D8D | Metabo Globster | Tributed for a DARK Tribute Summon |
| 0x1DEF | Oyster Meister | sent from field to GY |
| 0x1DF5 | Horseytail | destroyed by battle |
| 0x1FDA | Rockstone Warrior | destroyed while attacking |
| 0x205F | Darklord Asmodeus | (send-cost / trigger) |
| 0x20A9 | Damage Translation | delayed End-Phase token summon |
| 0x20CE | Jurrac Stauriko | destroyed by battle |

**Conclusion:** this record shape is the engine's idiom for *"when THIS card
dies, Special Summon N of your tokens."* Zeta's surviving fragment is therefore a
**simplified placeholder** — an Eva-Token generator on a generic on-death hook —
**not** clause 2 (a GY-*resident* watcher on the *opponent's* banishes) and not
clause 1. A self-death trigger and a GY-resident watcher share no machinery.

## Open Questions
- What is handler **`0x02261F8D`** (the `0x0228F350` row)? It is a 3-step state
  machine switching on `[r4,#0x24]` and calling 0x0225CEA4 / 0x0219A818 /
  0x0224BAEC / 0x0224BBB0 (the last two neighbour the picker 0x0224BA34). Shared
  by 38 cids whose common trait looks like "special summon procedure /
  Metalmorph-style", **not** a per-card trigger. Unproven either way.
- Is there a **"removed from play" (banish) event** distinguishable at the
  leave-field hook `0x021C8216`? The mask table `0x0226EC1C` encodes
  destroyed + to-GY (0x0C04); no banish bit identified yet.
- Does this engine have **any GY-resident continuous trigger**? No precedent
  found. If none exists, clause 2 needs an ov5 trampoline that re-checks GY
  residency itself — and ov5 is **normal-duel only**.
- Making a *true* "Eva Token" (0x0F5A, Fiend/DARK/Lv2/500/500) requires
  **inserting** a `card_prop` record into a **sorted, fixed-size** 4305-record
  array — which shifts every later index and therefore every `card_intid` low14
  plus all the parallel index-keyed arrays (`card_genre`, `card_pass`,
  `card_sort*`, `card_kana*`, `card_indx_*`/`card_name_*`, `card_pack`,
  `card_pwcost`). Cost/risk of that "pool surgery" is **not yet assessed**.

## Build state

Allocation ledger clean (`check_allocations`): 85 ov5 slots (76 live), 26 phantom
claims, no overlaps. **`CAVE_FREE = 0x0239C014`**, cave ends 0x0239E120 →
~0x210C B (8.4 KB) free. No slot claimed for Zeta yet.

Settled inputs for the build:
- donor pair 0x2299 / 0x0F7E (above); token-table row 66 needs no edit
- clause 2 hook: banish primitive `0x021C7098` (proven above)
- SS primitive `0x0226925C`
- clause 1 hook: `0x0224C026` (KB `handss.hook_site`, VERIFIED) + dispatch
  `0x0225E51C` bit 0x4

### ITEMS 2 & 3 CLOSED — from existing KB facts (no new RE needed)

- **Item 2, "is Zeta in my GY?"** — `ram.graveyard_and_banished_arrays` (VERIFIED):
  player base **0x0229AC94**, stride **0xB3C**; GY = player+0x55C, count
  player+0x14; packed u32 card words with cid = `word & 0x3FFF`. A ~20-instruction
  Thumb-1 loop answers it; no engine helper required.
- **Item 3, "a monster your opponent CONTROLS"** — `ram.container_for_zone_code`
  (VERIFIED): **0x0E = GY, 0x0F = banished**; field zones are the slot path
  `player + 0x34 + (zone+index)*0x14`. Design: at the hook, take the target's
  side from card-word bit 14, require it to be the opponent's, then confirm the
  card is ON THE FIELD by scanning that player's 5 monster zone records for its
  packed ref `(instance_index << 1) | side`. This uses only VERIFIED structures
  and sidesteps the unexplained 0xE constant in the banish worker (below).

### DOPPELWARRIOR 0x244D IS THE STRUCTURAL TWIN (clause blueprint)

It carries **both** of Zeta's clause shapes under one cid:

| record | slots | clause |
|---|---|---|
| `cls2[657]` | +04 **0x02207A09** (token resolver), +0C 0x021F072D, +10 0x021E51E5 | "When [event]: SS N tokens" |
| `cls2[658]` | +04 **0x02206ABD** (HANDSS_RES), +0C 0x021F0A39, +10 0x021E51E5 | "SS this card from hand by Tributing 1 monster" |

Its token row 72 = `{0x244D, 0x0F84, 2, 0}`. Note cid 0x2349 (the other cut card
I chased earlier) has `cls1[1228]` with the *same* shape as cls2[657].

### ⚠️ NEW COMPOSITION CONSTRAINT (contributed to the KB)

`find_event_handler` returns **`table[leftmost + offset]`**, where
`offset = 1 iff (descriptor[+5] == 1 && descriptor[+4] != 6) else 0`
(computed at 0x0224A7F0..0x0224A804), falling back to leftmost if that row is
past the count or holds a different cid (0x0224A81E..0x0224A83E). So:

- **cls1** can dispatch **two** records per cid (split by event code 6 vs not);
- **cls0 / cls2 / cls3** dispatch **leftmost only** — a second same-cid record
  there is unreachable *through this function*.

That is the true shape of the Warwolf E1/E2 shadow. Doppelwarrior nevertheless
ships two cls2 records, so its hand-SS record (cls2[658]) must be reached via the
**hand-SS dispatch `0x0225E51C`**, not via `find_event_handler`. **Consequence
for Zeta: its two clauses cannot both be cls2 records dispatched by
find_event_handler.** Now KB fact `dispatch.find_event_handler_second_record`
(VERIFIED); the old blanket "leftmost" fact was amended to point at it.

### Sweet Corn's full footprint (exactly 3 sites; Grain Corn Token exactly 1)

Scanning ov3 for aligned u16 references:

| addr | what | action |
|---|---|---|
| 0x0226D694 | token table row 66 `{0x2299, 0x0F7E, 1, 2}` | **keep — already correct** |
| 0x0226F30C | per-cid **LP-cost table** `{cid, LP}`; 0x2299 → 0x01F4 = **500** (its "pay 500 LP"; Solemn Warning → 2000, Psychic Path → 800 all check out) | neutralise |
| 0x0227DE24 | `cls3[690]` (its MP2 ignition) | neutralise / repurpose |

`0x0F7E` has exactly **one** reference — the token field at 0x0226D696. Clean.

### CROSS-GAME TRACE: Zeta's COMPLETE footprint in both engines

Exhaustive scan for the id 0x1A8A (every 2-aligned u16) in the 3DS image and
every aligned reference in NDS ov3. The two engines are **structurally
parallel**, with matching table membership and ordering.

| piece | 3DS | NDS | meaning |
|---|---|---|---|
| token table | `0x68D2D8` row `{tok 0x0F5A, cid 0x1A8A, mode 2, count 1}` | `0x0226D57C` row `{cid 0x1A8A, tok 0x0F5A, count 1, mode 2}` | **the ACTION** — both agree: 1 token, cid 0x0F5A, mode 2 |
| main per-card handler | `0x6C7C68` (stride 0x18) → `0x463C48` | `cls2[220]` → `0x02207A09` | the shared **token-summon router** in both |
| continuous registry | `0x6AAA88` → `0x4A0F58` | `0x02275A34` → `0x02247B25` | **stat refresher in BOTH** (see below) |
| hand-SS cost registry | `0x6AC684` → `0x4B79E4`, id `0x11A8A` (count 1) | **ABSENT** | **clause 1 — 3DS only** |

The continuous-registry tables are the same table in both games — identical tail
membership *and order*: `… 0x183F Harpies' Hunting Ground, 0x1B67 Cloak and
Dagger, 0x1A8A ZETA, 0x20FF Fortune Lady Earth, 0x1632 Remove Brainwashing`.
The NDS one is at **0x0227586C, 60 rows of `{u32 cid, u32 handler}`**, and its
membership is the "continuous / each-time / registered-effect" family (Soul
Absorption, Coffin Seller, Cyber Summon Blaster, Dark Room of Nightmare,
Fortune Lady Earth/Dark, both cut cids 0x1A8A and 0x2349, …).

**The decisive negative result:** Zeta's handler in that registry is a
**stat-refresh loop in BOTH games** —
NDS `0x02247B24`: sides 0..1 x zones 0..4, locate this card via
`0x021A37D8(side,zone)`, read stored packed ATK/DEF at zone-record `+0x40`,
recompute with `0x021B8064(side,zone)` / `0x021B807C(side,zone,2)`, and write
back with `0x021C7CAC` only if changed;
3DS `0x4A0F58`: the same algorithm (locate via `0x3AE3D8`, packed stats at
`[+0x48]`, recompute `0x3A9600`/`0x3A9608`, write `0x384B10`).
It is NOT a copy-paste placeholder — byte-compared against Fortune Lady Earth's
handler `0x02247204` it shares only 12/208 bytes (6%, i.e. noise), so it is
bespoke code. It simply is not a banish watcher.

**CONCLUSION — the 3DS cannot supply clause 2's trigger.** Neither engine
contains a "each time an opponent's monster is banished" implementation for
Zeta; both give it the token ACTION plus a continuous-presence stat refresh, and
nothing that watches banishes. (The 3DS card DB carries the full printed text,
but complete text does not imply a complete implementation.) So clause 2's
trigger must be **built**, and the proven `leave.banish_primitive` 0x021C7098
ov5 hook remains the plan — this trace removes the hope of a native shortcut
rather than providing one.

**Clause 1 IS copyable**, from two directions: the 3DS ships a real
implementation (shared template `0x4B79E4`, cost count in the id's high 16 bits
= 1), and the NDS has equivalent native machinery in Doppelwarrior's `cls2[658]`
(`+04 = 0x02206ABD` HANDSS_RES) plus the hand-SS dispatch `0x0225E51C`.

## Next Experiment (in order — all still `unproven`, NO build until resolved)

1. **How the ov5 banish hook fires the token summon.** Two candidates: (a) call
   `0x0226925C` directly with a hand-built locator — needs the locator bitfield
   and the zone-reservation the resolver's ACT phase does; (b) drive cid
   0x2299's existing resolver (row 66 already correct) by posting a descriptor.
   (b) is preferable — it reuses native plumbing. Determine what descriptor the
   cls3[690] invoker builds.
2. **"Is cid 0x2299 in side S's GY?"** — locate the helper. GY zone code is
   `0xE` (established via D.D. Crow + Armory Arm). Look for a
   "find card by cid in zone" scan next to `0x021A220C` / `0x021A2510`.
3. **"a monster your opponent CONTROLS"** — at the `0x021C7098` hook the target
   locator still holds its *source* zone; require a monster-zone value (field
   0..4), not GY/hand/deck, else Zeta would wrongly trigger off D.D. Crow-style
   GY banishes. Confirm the zone encoding in the locator word.
4. **Clause 1's cost** — the hand-SS trampoline only forces "may SS from hand"
   (bit 0x4); the actual *Tribute 1 Eva Token* cost needs a cost mechanism.
   3DS analogue: shared template + count in the id's high 16 bits (see above).
   Find the NDS equivalent (Turret Warrior 0x1F44 is the closest live card —
   "Tribute 1 Warrior-Type monster to SS this card from your hand").
5. **Neutralise `cls3[690]`** (Sweet Corn's MP2 / pay-500-LP ignition) so Zeta
   does not inherit it.

⚠️ Both clauses will live in the ov5 cave = **normal duels only** (a puzzle loads
overlay 41 over it). Zeta will be inert in puzzles; ov3 is resident in all modes
but cave space there is only 132 B.
