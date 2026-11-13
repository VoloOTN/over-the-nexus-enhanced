# Jet Warrior — findings

Session 1: **2026-09-04**. Donor **Ignition Beast Volcannon `0x23EB`**, keep-cid.
Scope: all four clauses (the user explicitly approved the full card in one patch,
overriding CLAUDE.md's one-clause rule).
Plan: `~\.claude\plans\jet-warrior-like-with-warm-squid.md`.

**STATUS**

- **Clauses 0 and 1: IN-GAME CONFIRMED BY THE USER 2026-09-04**, all six oracles,
  on the first test — on ROM `c4488bdf…2b67e869` (clauses 0+1 only).
- **Clause 3: in-game confirmed by user 2026-09-04** (both latches independent,
  declines do not burn them) — reported as *"3. Confirmed Unchanged"*.
- **Clause 2: IN-GAME CONFIRMED BY THE USER 2026-09-07**, all five oracles, on
  ROM **`d61470207f26e373240f21ceae5ff304d36385b5d52bb627929d77e6d7113f24`**.
  Their words: *"1. CONFIRMED / 2. CONFIRMED / 3. Confirmed / 4. Confirmed /
  5. Confirmed"*, against the five rows of the in-game test in
  `PROMPT_jet_warrior_clause2.md` — reading confirmed by the user before this was
  written. So: **not offered when no Level ≤2 monster is on the field** (the bug
  is gone); offered with one, picker lists only Level ≤2, it is tributed, Jet
  Warrior arrives in **Defense Position**; clause 3's two latches still
  independent; a decline still does not burn the once-per-turn; **and clause 1
  did not regress**. The root cause was our own timing-class arm — see
  **C21 / C22 / C23**.
- **O15, the banish rider: IN-GAME CONFIRMED BY THE USER 2026-09-07** — see
  **C24 / C25**. Both the rider AND its negative control (a Synchro Summoned Jet
  Warrior still goes to the GY) pass, and Jet Synchron did not regress.
- **SHIPPED 2026-09-07** on the user's instruction (*"Ship it"*): `PatchStep`
  "Ignition Beast Volcannon -> Jet Warrior (all clauses + rider)" at index 48,
  immediately AFTER Jet Synchron (the named-material row is cid-keyed on
  `0x224C`), and `patch_jet_warrior` added to `_verify_all_patches.SHIPPED` in
  the SAME edit (`otn-register-phantom-same-edit`). See **C26** for the chain
  build.
- **Continuation prompt: `PROMPT_jet_warrior_clause2.md`** (written 2026-09-04,
  updated 2026-09-07).

---

## The card

`scratch/ygoprodeck_cache.json`, id 286392, grepped this session — never recalled.

> Synchro Monster / FIRE / Warrior / Level 5 / ATK 2100 / DEF 1200
>
> `"Jet Synchron" + 1 or more non-Tuner monsters`
>
> If this card is Synchro Summoned: You can target 1 card your opponent
> controls; return it to the hand. If this card is in your Graveyard: You can
> Tribute 1 Level 2 or lower monster; Special Summon this card in Defense
> Position, but banish it when it leaves the field. You can only use each effect
> of "Jet Warrior" once per turn.

Clauses: **0** chassis/materials · **1** Synchro-Summoned bounce · **2** GY
Tribute revive in Defense + banish rider · **3** once per turn **each** (two
*independent* latches — note the word *each*; Jet Synchron prints the shared
form, so this is new work).

"Jet Synchron" is shipped on donor **Changer Synchron `0x224C`**
(`patch_jet_synchron.py`), so the named material = cid `0x224C`.

---

## Confirmed (measured this session)

### C1. The named-material rule is a 4-byte DATA row, not code

**`0x02275B04` — 23 rows × 4 B, `{u16 synchro_cid, u16 named_material_cid}`,
strictly ascending, binary-searched.** Dumped all 23 rows and verified
ascending-ness directly this session.

Read from OUTER `0x022485B4`:

```
0x02248608  ldr  r1,=0x02275B04
0x0224860A  adds r0,r5,#0        ; r0 = the SYNCHRO's cid
0x0224860C  movs r2,#0x17        ; count = 23
0x0224860E  movs r3,#4           ; stride = 4
0x02248610  bl   0x02022E44      ; binary search -> row ptr, or 0
0x02248618  beq  0x02248660      ; MISS -> the generic per-Synchro cid switch
0x02248636  ldr  r0,=0x000020F7  ; HIT: is the material QUICKDRAW SYNCHRON?
0x0224863E  ldrsh r0,[row,#2] ; bl 0x02023E1C   ; ...and is the named cid a "Synchron"?
0x0224864E  ldrsh r0,[row,#2] ; cmp r4,r0       ; ACCEPT iff material cid == named cid
0x0224865C  movs r0,#0 ; pop                    ; else REJECT
```

⇒ **A donor gets a named-material rule by DATA ALONE.** No ov5 stub, no material
predicate hook, and it stays **puzzle-safe** (ov3 data, resident in every mode).

**Junk Warrior `0x1E10` is row 1 `@0x02275B08` = `{0x1E10, 0x1E07}`** and prints
`"Junk Synchron" + 1 or more non-Tuner monsters` — the identical count clause.
It is Jet Warrior's structural twin, and that row is its *entire* material rule.

**The table's one phantom is row 22 `@0x02275B5C` = `{0x2524, 0x1E07}`**
(`0x2524` = Junk Berserker, not a card in this ROM).

**The insert for Jet Warrior (count-neutral, sort-preserving):**

```
[20] @0x02275B54  0x2355 Junk Gardna        <- 0x1E07   unchanged
[21] @0x02275B58  0x23EB JET WARRIOR        <- 0x224C   NEW
[22] @0x02275B5C  0x23EF Chevalier de Fleur <- 0x23EE   shifted down from [21]
                  (drops phantom 0x2524)
```

`0x2355 < 0x23EB < 0x23EF`, so the key column stays strictly ascending. **The
binary search makes sortedness mandatory.**

**Free bonus, and the correct real-world ruling:** `0x224C` is a stock member of
the "Synchron" set-code table `0x0209C968`, so the arm at `0x02248636` makes
**Quickdraw Synchron a legal substitute Tuner** automatically.

### C2. "1 or more non-Tuner" — three absences, nothing to add

Dumped and checked `0x23EB` against all three opt-in exception lists this
session:

```
LIST_A 0x02275AB8 (16 x u16): 0E6C 2004 208B 211B 219B 219D 21CB 22A3
                              239D 239E 239F 2400 2401 24B2 2525 2526
min-3  0x02275AD8 (21 x u16): 1D7D 1DFF 1F25 208C 20E1 211B 211C 2181 21CB
                              221C 2273 239F 241F 2420 2471 2472 2473 2476
                              24B2 252A 252B
2-Tuner pair 0x02248280     : 0x239F, 0x24B2 only
```

`0x23EB` is **ABSENT from all three**. Absence from LIST_A is what gives the
"N or **more**" form. ⚠️ **Never add this donor to LIST_A** — membership means
"EXACTLY N, extras forbidden" and would break the printed text.

The three tables abut: `0x02275AB8 + 16*2 == 0x02275AD8`, then `0x02275AD8 +
21*2 == 0x02275B02` (a `0x0000` pad), then the named-material table at
`0x02275B04`.

### C3. The Synchro-Summoned trigger list has NO phantoms — this chose the donor

**`0x0228F6C0`, 36 × u16 cid, sorted, binary-searched by `0x02022E14` at
`0x022658FC`, hard count `0x24`.** Fires on event code 9 (Special Summon) **AND**
`[0x02298A28+0x10] & 1` ("went through a summoning procedure"), so Synchro and
Fusion share one list.

**All 36 rows are real cards.** It is the only one of the nine summon-trigger
lists with no droppable phantom.

⇒ **An Extra-Deck donor for an "If this card is Synchro Summoned:" effect must
ALREADY be in this list.** That makes its 6 Fusion and 3 Ritual members the only
viable donor pool for that timing — the effectless Fusions the Accel Synchron
session catalogued are all *outside* it.

The one escape is hooking the `bl 0x02022E14` at `0x022658FC`, which
`patch_azure_eyes.py:977` and `:1154` **assert is still native** in its
apply-guard and its `verify()`. Hooking it breaks that shipped card's verify and
costs puzzle-safety. Rejected.

### C4. The donor: Ignition Beast Volcannon `0x23EB`

Lv6 EARTH Machine Fusion Effect Monster 2300/1600, pack 56. `donor_scan 0x23EB`:

```
5 binding occurrence(s):
  fusion recipe A[155]+0x0:        ov3:0x0227106C/u16
  cls1 record[1279]+0x0:           ov3:0x0228D8BC/u16
  summon list: proper SS[30]+0x0:  ov3:0x0228F6FC/u16
  unclassified:                    ov3:0x0226D974  (u16 and u32, same address)
1 non-key / code-region u16 hit:   ov3:0x0228D8BC  (the cls1 record itself)
```

Every binding is accounted for. Three are things we *want*; the fourth is O2.

- **cls1[1279] `@0x0228D8BC` = `{0x23EB, 0x02230C7D, 0x021D882D, 0x02203C5D,
  0x021E51E5, 0x02234DA5}`** — its only record; clause 1's home.
- Printed timing already matches clause 1: *"When this card is Fusion Summoned:
  **You can target 1 monster your opponent controls**; destroy that target, …"*
  (`otn-donor-timing-match-jet-synchron`).
- Name slots `{e:24, f:27, g:23, i:27, j:18, k:0, r:34, s:28}`.
  ⚠️ **Korean is 0 B** — `TEXT_LANGS` must exclude `'k'`
  (`patch_jet_synchron.py:269` precedent). Floor excluding `k` = **18 ≥ 11**.
- Desc slots `{e:312, f:361, g:363, i:324, j:272, k:0, r:534, s:340}` — floor
  excluding `k` = **272 B** (Japanese binds).

**Reference record for the conversion: Laval Twin Slayer `0x23FE`** — measured
`Synchro Effect Monster / Lv5 / FIRE / Warrior / 2400 / 200`. Level, attribute,
race and card_type are *exactly* Jet Warrior's; the reference-record copy only
overwrites cid + ATK + DEF.

### C5. Clause 1 is a 20-byte in-place cls1 rewrite, zero code

Transplant source **Nightmare Penguin cls1[325] `@0x02287F4C` =
`{0x16AB, 0x02204911, 0x021DED49, 0x0224A115, 0, 0x02234DCD}`** — dumped this
session. The same 5-tuple is shared verbatim by Gem-Knight Aquamarine (cls2[579])
and Lavalval Dragon (cls3[696]); all three print *"target 1 card your opponent
controls; return it to the hand"*.

```
cls1[1279] @0x0228D8BC   (+00 stays 0x23EB -- keep-cid)
  +04  0x02230C7D -> 0x02204911   destroy/damage resolver -> BOUNCE resolver
  +08  0x021D882D -> 0x021DED49   "1 MONSTER your opponent controls"
                                  -> "1 CARD your opponent controls"
  +0C  0x02203C5D -> 0x0224A115   Volcannon's condition -> always activatable
  +10  0x021E51E5 -> 0x021E51E5   UNCHANGED -- timing class 2, the "You can" tag
  +14  0x02234DA5 -> 0x02234DCD   destroy prompt -> target declaration, code 0x57
```

`+10` needs no move because Jet Warrior also prints *"**You can** target"*. That
matters: `timing.class_is_the_slot4_literal` (VERIFIED) says `0x0224AF7C` reads
`+0x10` as a raw literal and never calls it, so a wrong value is the silent-drop
failure that cost `patch_lightpulsar` a withdraw-and-restore.

⚠️ Do **not** use `0x021D8CF5` for `+08` (Compulsory Evacuation Device's) — that
predicate is *"1 monster on the field"*: both sides, monsters only.

### C6. Sword of Sparkles `0x209D` — the GY-action row, and exactly what it costs

**GY-action registry `0x0228DDF8`, 60 rows × 0x10 B `{u32 cid, u32 zone, u32 chk,
u32 post}`, unsorted, linear-scanned** (four scanners, each bounded by a
hard-coded `cmp rX,#0x3C`).

> **Row 33 `@0x0228E008` = `{0x209D, 0x0E, 0x0224C591, 0x0224C6C1}`** — family C,
> the GY-self-SS family.

Family C phantoms are **exhausted**: row 15 `0x0EB2` → grapha, row 47 `0x0E3E` →
lightpulsar, row 48 `0x0E64` → jet_synchron. The table cannot grow — it ends at
`0x0228E1B8` and a pointer table starts immediately there. Family B's three
phantoms (rows 11/12/13) are a trap: that family builds **no class descriptor**
and gates on the **hand** (`effect_dispatch_tables.yaml:3501`, VERIFIED).

Cost of spending row 33, measured: it kills exactly Sword of Sparkles' **third**
sentence (*"You can Tribute 1 monster you control to return this card from your
Graveyard to the top of your Deck"*), whose action is **cls2[475] `@0x0227888C` =
`{0x209D, 0x0220AD5D, 0x021D87F9, 0, 0x021E7BE5, 0}`**. Its equip +
battle-destruction clause lives in **cls1[1042] `@0x0228C284`** and is reached by
the battle/equip path, so it stays live. The card loses one of three sentences;
it is not bricked. It has no criteria row and no leave-mask row.

### C7. cls2 geometry and capacity

`0x02275C04`, `0x2B9` records × `0x18`, **verified strictly sorted this session**
(so binary-searched, and the insert must be sorted + count-neutral). **70 phantom
rows exist** — capacity is not a constraint. Cross-check the chosen phantom
against `PHANTOM_CLAIMS` in `check_allocations.py` before claiming.

### C9. The clause-2 COST is solved: slot4 is reusable data, the filter is slot2

Measured this session, and it **corrects the working assumption the plan was
written on** (see the Corrections section).

**`0x021E7C88` is NOT a level-filtered Tribute machine.** Disassembled it and
hand-decoded its per-cid switch (`r2 = [r5]` = descriptor cid), resolving every
pc-relative literal:

| cid | | `r4` | |
|---|---|---|---|
| `0x0E9D` | (phantom) | `0x0E9B` | (phantom) |
| `0x0FE0` | Kuriboh | `0x0FE0` | Kuriboh |
| `0x167D` | (phantom) | `0x0FC9` | Dark Magician |
| `0x1713` | Dedication through Light and Darkness | `0x0FC9` | Dark Magician |
| `0x187E` | Release Restraint | `0x13C3` | Gearfried the Iron Knight |
| `0x19B5` | (phantom) | `0x18F6` | Cyber Dragon |
| `0x1AE5` | Barrier Statue of the Stormwinds | `0x1ACF` | Elemental Hero Knospe |
| `0x1B1E` | Edge Hammer | `0x194D` | Elemental Hero Bladedge |
| `0x1B1F` | Kid Guard | `0x19A7` | Hero Kid |
| `0x20B9` | King of the Beasts | `0x20B7` | Moja |

It is a **cid → NAMED-TRIBUTE cid** map, and `r4` is consumed only as a **UI
message parameter** (`0x021E7D4E: movs r0,#0x13 ; bl 0x0219A6F4` then
`bl 0x0219A798(r4)`). **Default `r4 = 0`** for any cid not listed. It is not a
filter at all.

**The filter is slot2 (+0x08).** The cost machine calls
`0x0224AB38(r0 = desc, r1 = 0x0224A8C1)` at `0x021E7D40`, and `0x0224A8C1` is
the **slot2 invoker** (`dispatch.cls_slot_roles`, and the GDB-confirmed Sea
Lancer chain). Proof by the three cards that print a level-restricted Tribute:

```
0x1855 Castle Gate  "Tribute 1 Level 5 or lower monster"
    cls3[188]  @0x0227AF14  0x02206139 0x021D9189 0x021F8D89 0x021E7C89 0
0x2006 Mind Trust   "Tribute 1 Level 2 or higher monster"
    cls0[1047] @0x02284874  0x02208181 0x021D9189 0x021F452D 0x021E7C89 0x02235605
0x20B9 King of the Beasts   (named tribute: Moja)
    cls2[481]  @0x0227891C  0x02206ABD 0x021D9189 0x021F0A39 0x021E7C89 0
    cls2[482]  @0x02278934  0x0220731D 0x021D9189 0x021F04FD 0x021E7C89 0
```

All three share **slot4 `0x021E7C89`** *and* **slot2 `0x021D9189`**. Since slot4
only supplies a prompt name, the level/name discrimination must be in slot2 — and
`0x021D9188` is a giant **per-cid switch** (`ldrh r2,[r6]`, with
`str r0,[sp,#4]` at `0x021D920E` — the `thumb-stack-based-switch-footgun`
pattern, so never hand-simulate it register-only).

⇒ **Clause 2's cost costs almost nothing:**
- **slot4 = `0x021E7C89` verbatim, pure data.** `0x23EB` is absent from its
  switch, so `r4 = 0` = "no named card in the prompt" — exactly right for a
  Level filter.
- **slot2 = a small ov5 stub** (do **not** add an arm to `0x021D9188`).

**The slot2 idiom is already fully documented.** `dispatch.zone_predicate_mask_rosetta`
(VERIFIED, `0x021D6E40`): a generic bitmask candidate predicate
`(r0 = source desc, r1 = candidate side, r2 = candidate zone, r3 = MASK) -> 1/0`,
with a **168-entry Rosetta stone** in ov3 of 4-instruction thunks
`push {r3,lr} ; ldr r3,[pc,#8] ; bl 0x021D6E40 ; pop {r3,pc}` + literal. Decoded
fields: bits 0-1 = side selector, **bits 4-6 = a 3-bit ZONE-CLASS field**
(`0x10` = "zone < 5", a monster zone), bit 2 = face-up, bit 15, bit 21.

Worked examples read this session:
- Swap Frog `0x2115` slot2 `0x021E38F9`, mask **`0x00008011`** — *"return 1
  monster you control to the hand"* (you control + monster zone, **no** face-up bit).
- Genex Ally Birdman `0x2205`, mask `0x00008015` — *"return 1 **face-up**
  monster you control"* (KB).

⚠️ **There is no Level field in the mask.** An earlier scan of mine flagged Swap
Frog's `0x021E38F9` as a possible ready-made "Level 2 or lower" predicate — that
was a **false positive**: the phrase appears in a *different* clause of Swap
Frog's printed text. **No stock slot2 pointer means "Level 2 or lower monster you
control".** The stub must add the level test itself, exactly the way
`card.grapha_clause1` part (E) adds an archetype test on top of a mask tail-call.

Planned shape (`CAVE_JW_TRIBFILT`, ~0x30 B):

```
push {r4,r5,r6,lr}          ; r4=desc  r5=side  r6=zone
bl   0x021D6E40(desc, side, zone, r3 = 0x00008011)
cmp  r0,#0 ; beq reject
<cid = the card in (side, zone)>          ; 0x021A36EC(side, zone)
<level = level_getter(cid)>
cmp  level,#2 ; bgt reject
movs r0,#1 ; pop {r4,r5,r6,pc}
reject: movs r0,#0 ; pop {r4,r5,r6,pc}
```

Two sub-questions remain (O9, O10 below): which mask, and which level getter.

### C8. ov5 budget

`ov5_cave.py`: `CAVE_FREE = 0x0239E950`; ceiling `0x023AA120` ⇒ **0xB7D0 =
47,056 bytes free**. `check_allocations` is green (180 ov5 slots, 157 phantom
claims, 11 ov3 dead-code claims, no overlaps).

---

### C10. BUILT this session — clauses 0 + 1, pure data, `verify()` 22/22

`otn_enhanced/cards/jet_warrior.py` + `_build_jet_warrior.py`
→ `data/over_the_nexus/working/rom_jet_warrior.nds`.
**IN-GAME CONFIRMED BY THE USER 2026-09-04, all six oracles, first test.** The
decisive one is oracle 4: a *different* Level 1 Tuner with the same non-Tuners is
**refused** — that is what proves the named-material row is being read, rather
than the card summoning off any Tuner and merely looking correct.

⚠️ **THE TEST ROM IS A TWO-PATCH BUILD, AND MUST BE.** The first build of this
card was made onto the CLEAN rom.nds, where cid `0x224C` is still **Changer
Synchron** — so the named-material row said "the Tuner must be `0x224C`" and the
card that satisfies it was the wrong one. The user caught it immediately
("Jet Synchron isn't built in this rom how am I expected to summon it?").
`_build_jet_warrior.py` now applies the shipped `patch_jet_synchron` first and
layers Jet Warrior on top, and runs **both** modules' `verify()` against the
final artifact, positionally. **Generalisable: when a card's material rule NAMES
another patched card, the single-card test ROM must contain both — a cid-keyed
rule is satisfied by whatever that cid currently is, so the build looks correct
and tests nothing.** Superseded artifact: sha256 `e9e13915…` (clean-base, no Jet
Synchron).

Not wired into `apply_all_patches`. **No injected Thumb, no ov5 slot ⇒ clauses 0
and 1 are puzzle-safe.**

| part | edit | address |
|---|---|---|
| A | `card_prop` reference-record copy from Laval Twin Slayer `0x23FE`, cid swapped; then Lv5 / FIRE / Warrior / 2100 / 1200 / card_type 37 | index 4137 |
| B | `card_genre` `0x0000000420200402` → `0x0000001400200402` (clear bit 29 FUSION, set bit 36 SYNCHRO) | index 4137 |
| C | name + description, 7 languages (`efgijrs`) | — |
| D | fusion recipe A[155] materials `0x0007`/`0x0004` → `0x3FFF`/`0x3FFF` | `0x0227106C` |
| E | named-material insert `{0x23EB, 0x224C}` at row 21, dropping phantom `0x2524` | `0x02275B58` |
| F | cls1[1279] action slots → Nightmare Penguin's bounce tuple | `0x0228D8BC` |

⚠️ **Volcannon's `card_genre` is NOT the effectless `{21, 29}`** the Accel patch
asserts — it is `{1, 10, 21, 29, 34}`. Whole-table census this session: only bits
21 / 29 / 36 are class-coupled (147/147, 147/147, 139/140); bits 1/10/34 are
effect-category tags spread across both classes, so they are **left alone**. Jet
Warrior therefore inherits Volcannon's effect-category tags — a deck-editor-filter
cosmetic, not a duel-path effect. See O11.

⚠️ **Volcannon's fusion materials are CATEGORY CODES, not cids** — its recipe is
*"1 Machine-Type monster + 1 Pyro-Type monster"* and the row holds `(7, 4)`, so
the blanking guard asserts those, not stock cids.

**The description ships as a three-entry LADDER** (Accel's idiom: the shared
writer skips any language the string does not fit, so drive it once per group).
Measured placements: `f g r s` → 333 B, `e i` → 301 B, `j` → 260 B; Korean is
skipped entirely (slot 0 B). Every clause appears in all three — what shrinks is
the wording, not the content.

`check_allocations`: **159 phantom claims, no double-claims, ledger in sync.**
Registered in the same edit: `("donor_cid", 0x23EB, "jet_warrior")` and the new
pool `("named_material_table", 0x2524, "jet_warrior")`.

---

### C11. The GY-offer path, traced end to end — and O1 and O2 are THE SAME QUESTION

Disassembled the whole chain this session (clause-2 work, 2026-09-04). **No
`card_type` / `is_extra_deck` / `card_category` read anywhere on the Graveyard
path.** The chain:

```
0x0224C88E  zone scanner: for each registry row matching [sp+0x18] == zone,
            walk the ZONE ARRAY -- 0x0219CE2C(side,zone)=count,
            0x0219CAE4(side,zone,idx)=cid, 0x0219CBB8(side,zone,idx) --
            and match on CID ALONE, then blx [row+8]
0x0224C591  zeroes a 0x24 B descriptor (0x0209A080) and fills
            desc[+0]=cid  desc[+2]=side  desc[+3]=0x0E (GY)
            desc[+4]=<per-slot code, from a table>  desc[+5]=2 (CLASS 2)
            desc[+0xC]=r7 ... then bl 0x021EC740
0x021EC740  ldrb r4,[r5,#3] ; cmp r4,#0xA ; bls ... -> OUR zone 0x0E is > 0xA,
            so it takes `b 0x021EC892`, which does `movs r0,#2 ; strb r0,[r5,#5]`
            = SET THE cls2 TABLE SELECTOR.  *** THE ENTIRE card_type-READING
            BRANCH (0x021EC7A8/B6/E6/FC, 0x021EC81E, 0x021EC86C -- including
            0x020230E8 = "card_type == 8") IS ON-FIELD ONLY AND IS SKIPPED. ***
            Then: bl 0x021ECC6C, then bl 0x021EDA14(desc, r7, 0).
```

⇒ **cls2 is the correct and intended class for a GY-action offer**, and the
selector is set by zone, not by card type.

**⚠️ BUT `0x021ECC6C` CALLS `0x021A897C` — THE CONSUMER OF THE MYSTERY LIST FROM
O2.** So the unexplained binding of `0x23EB` at `0x0226D974` is **on clause 2's
live path**, not an idle inheritance:

```
0x021ECD24  ldr  r0,=<global> ; ldr r0,[r0,#0x78] ; tst r0,#1
0x021ECD2C  beq  0x021ECD4E        ; bit CLEAR -> the check is skipped entirely
0x021ECD2E  ldrh r0,[r5]           ; r0 = the descriptor cid
0x021ECD30  ldrb r1,[r5,#4]        ; r1 = desc[+4]  (NOT the zone)
0x021ECD32  bl   0x021A897C
0x021ECD36  cmp  r0,#0 ; bne 0x021ECD4E   ; NONZERO = PASS
0x021ECD3A  ...  message 0x15, then `movs r0,#0` = REJECT THE OFFER
```

`0x021A897C(cid, r1)` returns 1 if `0x0202ABE8(cid) == 1`, **or** if the cid is
in a 48-entry binary-searched list, **or** via a 16-arm jump table on `r1 - 0xE`
(so `r1` ∈ 0xE..0x1D) whose arms compare the cid against literals and against the
three sorted sub-lists based at `0x0226D874` — the third of which **ends with our
donor `0x23EB`**.

### C12. ✅ O1 AND O2 ARE CLOSED — the gate is DORMANT in a normal duel

`scratch/jw_gyoffer_probe.py`, run 2026-09-04. The `bl 0x021A897C` is guarded by

```
0x021ECD24  ldr r0,=0x0229C294 ; ldr r0,[r0,#0x78] ; tst r0,#1
0x021ECD2C  beq 0x021ECD4E          ; flag CLEAR -> skip the gate entirely
```

and **`[0x0229C30C] = 0x00000000` in every duel savestate measured** — `rom.ml1`,
`rom.ml2`, `rom.ml3`, each with overlay 3 resident and byte-matching the image at
`0x021A897C` / `0x0224C590` / `0x021EC740` (3/3). So the gate **is never called**,
and the donor's `0x0226D874` membership is **inert on this path**.

**Corroboration, and the reason not to trust a forced run:** with the gate forced
to execute, it rejects **every** cid tested — Plaguespreader `0x1EA9`, Quillbolt
`0x1E15`, Glow-Up Bulb `0x2387` included, whose GY effects the engine
demonstrably offers today. A gate that would reject those cannot be running in a
normal duel. (The `0x0202ABE8` reads also error on several cids under the
emulator, so the forced-run numbers are corroboration only, not a result.)

⇒ **Combining C11 and C12: there is NO `card_type` / `is_extra_deck` /
`card_category` read anywhere on the Graveyard offer path, and the single per-cid
gate on it is disabled in normal duels. An Extra-Deck cid can ride the
GY-action → class-2 path.** The old memory note
(`otn-leave-trigger-cls2`: "cls2 dispatch NEVER reaches an Extra-Deck donor") is
about the **leave-field** enumeration, a different path, and does not apply here.

**Still unknown, and deliberately:** what sets `[0x0229C294+0x78] bit 0`. Some
non-normal duel mode. If a future card must work under it, measure it there —
`scratch/jw_gyoffer_probe.py` is the tool.

### C13. Clause 2/3 design questions closed (2026-09-04)

**O9 — the tribute filter's mask: `0x00020013`.** Swept all **168** thin mask
wrappers (`push {r3,lr} ; ldr r3,[pc,#8] ; bl 0x021D6E40 ; pop {r3,pc}` + literal)
and joined them to their owning cls records and printed text. Wrapper
`0x021DFD0D`, mask **`0x00020013`**, has 4 owners and **4/4 print "Tribute"**:
The Little Swordsman of Aile, Hand of Nephthys, Raviel Lord of Phantasms,
Destiny Hero - Dasher. That is the engine's own Tribute-candidate mask — use it,
not Swap Frog's `0x00008011` ("return 1 monster you control", a different cost)
and not Genex Ally Birdman's `0x00008015` (adds the face-up bit).

**O10 — the level getter: `0x021B807C(side, zone, 0)`, the LIVE Level.** KB fact
`dispatch.level_rider_is_kind_3`'s correction (`effect_dispatch_tables.yaml:1214`)
names it as "the Level getter … the one Copy Plant's leaf and Egotistical Ape's
own legality check both reach", with its final formula at `0x021B88B4` and a
real-board measurement via `scratch/accel_level_probe.py`. It takes (side, zone),
which is exactly what a slot2 predicate already holds — no cid lookup needed, and
it honours Level modifiers, unlike the printed-level getter `0x0202ABD8`.

**O6 — two independent once-per-turn latches: same key, kinds 1 and 2.**
`dispatch.turnlog_once_per_duel_is_kind_5` carries the closed proof of the kind
semantics: the node search `0x021A1268` matches `node[+2] & 0xF` under
`cmp r7,#6 ; bhs`, so **kinds are 0..5**, and the end-of-turn sweeper
`0x0219F9E0`'s 9-entry jump table sends **kinds 1 and 2** to the
countdown-or-remove block while 0/4/5 persist. So kind 1 **and** kind 2 are both
per-turn. Query `0x021A14E8(side, 0x0B, key, kind)` matches key **and** kind, and
no native code posts key `0x23EB`, so:

| clause | latch |
|---|---|
| 1 (Synchro-Summoned bounce) | `(key 0x23EB, kind 1)` |
| 2 (GY Tribute revive) | `(key 0x23EB, kind 2)` |

independent by construction, both swept at end of turn, no collision possible.

**⚠️ Clause 1's latch must NOT go in slot +10.** `timing.class_is_the_slot4_literal`
(VERIFIED): the classifier `0x0224AF7C` reads `+0x10` as a RAW LITERAL and never
calls it, so an ov5 pointer there is unclassified and the record is silently
dropped — the `patch_lightpulsar` withdraw-and-restore failure. Instead: **`+04`
becomes an ov5 stub that stamps and tail-calls the native bounce `0x02204911`**
(slot1 is invoked via `blx`, so a cave pointer is fine there), and **`+0C`
becomes the turn-log query**. `+10` stays `0x021E51E5` untouched, so **no
registration on the shared timing-class hook is needed**.

### C14. Clause 2 + 3 ARCHITECTURE (settled 2026-09-04, not yet built)

⚠️ **My first plan was wrong and the KB caught it.**
`dispatch.once_per_turn_must_stamp_at_activation` (VERIFIED, measured in-game on
`card.maiden_clause1` 2026-08-20): **a once-per-turn stamped in the RESOLVER
loses to the chain** — both activations run the slot3 query before either
resolves, so both see the log clear and the card activates twice in one chain.
**The stamp must go in slot +10, the activation procedure**, wrapping the
costless "you can" BODY `0x021E50DC` (**not** the thunk `0x021E51E5`) and posting
only when it returns 1 = "the player said yes" — so declining the prompt does not
burn the latch.

That collides with `timing.class_is_the_slot4_literal` (the classifier
`0x0224AF7C` reads `+0x10` raw and never calls it). The escape is per-class:
`0x0224AF7C` returns 0 immediately for descriptor selectors **0 and 3**, so a
cls0/cls3 `+0x10` may hold a cave pointer — **but ours are cls1 and cls2, so both
need an arm on the SHARED timing-class hook** (`CAVE_TIMINGHOOK 0x0239E340`,
existing arms `0x0FB1`, `0x224C`). One arm on cid `0x23EB` covers both records;
both clauses are class 2.
⚠️ Adding an arm moves every other arm's offsets — run
`scratch/timing_hook_equiv.py` and assert no shipped cid changed
(`otn-shared-hook-lift-prove-by-execution`).

**The two clauses live in DIFFERENT records** (clause 1 = cls1[1279], clause 2 =
a new cls2 row), so unlike Jet Synchron **no resolver/condition dispatcher is
needed** — each record gets its own small stub.

| slot | clause 1 — cls1[1279] `@0x0228D8BC` | clause 2 — new cls2 row |
|---|---|---|
| +04 resolver | `0x02204911` **unchanged** (native bounce) | `CAVE_JW_C2_RES` — arm the rider byte, then the GY self-SS **in Defense** |
| +08 candidate | `0x021DED49` **unchanged** | `CAVE_JW_TRIBFILT` — mask `0x00020013` + live Level ≤ 2 |
| +0C condition | `CAVE_JW_C1_COND` — turn-log query (key `0x23EB`, kind 1) → 0 or 2 | `CAVE_JW_C2_COND` — query (kind 2), then Plaguespreader's GY-revive gate `0x021FF06D` |
| +10 activation | `CAVE_JW_C1_SLOT4` — wrap `0x021E50DC`, stamp kind 1 on return 1 | `CAVE_JW_C2_SLOT4` — stamp kind 2, then chain the Tribute machine `0x021E7C89` |
| +14 target | `0x02234DCD` **unchanged** | 0 |

Plus the data edits: **GY-action registry row 33 `@0x0228E008`** cid
`0x209D` → `0x23EB` (spends Sword of Sparkles' GY self-recycle, user-approved),
and a **count-neutral sorted cls2 insert** over an unclaimed phantom.

**✅ O12 CLOSED — Defense Position is a 4-byte cid-scoped hook, not a clone.**
The commit is `0x0226925C(r0 = side, r1 = locator, r2 = face_up, r3 = POSITION)`
at `0x022074EA`, with `[sp] = cid << 16`; `r3` comes from `r4`, and the KB's token
fact fixes the encoding: **1 = Defense, 0 = Attack, 2 = player's choice**.
Cloning the tail is impractical (`r7`, the locator, is built far upstream), but
the two instructions that load the commit's arguments are exactly 4 bytes:

```
0x022074E6  ldrb r0,[r5,#2]     ; side
0x022074E8  adds r3,r4,#0       ; position
```

Replace both with `bl CAVE_JW_C2_POS`, whose body is:

```
    ldrh r0,[r5]        ; the descriptor cid (r0 is dead here)
    ldr  r3,=0x23EB     ; r3 is about to be written anyway
    cmp  r0,r3
    bne  native
    movs r3,#1          ; DEFENSE, for our cid only
    b    setside
  native:
    adds r3,r4,#0       ; the native instruction, verbatim
  setside:
    ldrb r0,[r5,#2]     ; the native instruction, verbatim
    bx   lr
```

It writes only `r0` and `r3` — precisely the two registers the native pair
writes — and leaves `r1`/`r2`/`r4`/`r5` alone (`r1` and `r2` are already loaded at
`0x022074DE`/`E0` and must not be clobbered). For every cid but ours it performs
the same two writes in the opposite order, which is unobservable. So the
equivalence argument is closed by construction, even though 68 cls2 records share
this resolver.

**✅ O13 CLOSED — `0x021E7C89` returns 1 exactly when the Tribute was paid.**
Its phase protocol, read this session: phase 0 opens the picker
(`0x0219A818` dialog, `0x0224BB98` selection), bumps `[0x0229AAFC+0x7C]` and
returns **0**; phase 1 calls `0x0224BBB0` — zero means cancelled, so it
*decrements* the phase at `0x021E8144` and returns 0; nonzero falls through to the
actual send-to-GY `0x021CF68C` and then `b 0x021E7C98` = `movs r0,#1` = **return
1**. Same shape as `0x021E50DC`. So `CAVE_JW_C2_SLOT4` chains the machine and
stamps **only on a return of 1** — cancelling the Tribute does not burn the latch.

> ⚠️ SUPERSEDED — O15 was BUILT and in-game confirmed 2026-09-07; see C24/C25.
**⚠️ O15 — THE RIDER IS A COMPOSITION PROBLEM, and it is the one piece that
touches a shipped, in-game-confirmed card.** "Banish it when it leaves the field"
cannot be attached from our resolver: the node is keyed on the (side, slot) the
monster lands in, and `patch_jet_synchron`'s own comment records that the commit
`0x0226925C` can finish *after* the resolver has returned. That is why Jet
Synchron attaches it from the **summon-event default leaf `0x02268666`**, via a
one-shot arm byte — and **`patch_jet_synchron.verify()` asserts that site still
points at `CAVE_JS_RIDER 0x0239E680`**, so Jet Warrior may not simply retarget it.
Options: (a) generalise `CAVE_JS_RIDER` into a small `ARMS` table the way
`criteria_row_hook` / `timing_class_hook` already work, and register `0x23EB` —
correct, but it edits an in-game-confirmed card's bytes and needs a new
equivalence harness; (b) chain a Jet Warrior stub in front of it — breaks that
`verify()` as written. **Prefer (a).** Not yet built.
- **O14.** Whether clause 1's `+0C`/`+10` change can regress the **in-game
  confirmed** clause 1. `dispatch.slot3_reevaluated_after_cost` says slot3 can run
  again mid-activation; if it re-runs after +10 stamped, the query would abort the
  card's own resolution. Jet Synchron ships the identical split and is confirmed,
  but on cls2 — for cls1 this is a **precedent, not a proof**. Distinguishable
  symptom: *offered, prompt accepted, then nothing happens.*

---

### C15. BUILT 2026-09-04 — clauses 2 + 3, six ov5 stubs, both verifies PASS

`rom_jet_warrior.nds` sha256 **`abd22deb…96a59723`**, 129,524,360 B
(supersedes `4cc84340…`, which FROZE on Synchro Summon — see C16).
`jet_synchron.verify` **PASS**, `jet_warrior.verify` **PASS** (all checks).
`check_allocations`: 186 ov5 slots, **161 phantom claims**, no overlaps, ledger in
sync. KB: 432 facts, 395 PASS, **0 FAIL**. **AWAITING IN-GAME TEST.**

| part | edit | address |
|---|---|---|
| G | GY-action row 33 cid `0x209D` → `0x23EB` | `0x0228E008` |
| H | cls2 insert `{0x23EB, 0x0220731D, TRIBFILT, C2_COND, C2_SLOT4, 0}` over phantom `0x1655` | row 643 |
| H | cls1[1279] `+0C`/`+10` → the clause-3 stubs (`+04`/`+08`/`+14` untouched) | `0x0228D8BC` |
| I | SS-commit argument load → `CAVE_JW_C2_POS` (Defense Position) | `0x022074E6` |
| J | six ov5 stubs + one arm on the shared timing-class hook | `0x0239E950`+ |

**The shared timing-class hook was lifted by EXECUTION, not by argument**
(`otn-shared-hook-lift-prove-by-execution`). `scratch/timing_hook_equiv.py` was
stale — it swept a cid list without `0x23EB` and its `ADDED` set named only
`0x224C`. Updated and re-run: **39,780 inputs through both emitted blobs**, and
the only cids whose `(r0, Z)` differ are `0x224C` and `0x23EB`. Lightpulsar
`0x0FB1` and the neighbours `0x23EA`/`0x23EC` are unchanged.

**Three build bugs worth recording, all caught by assertions rather than in-game:**
1. `_count_neutral_insert` asserted **strictly** ascending. Right for the
   named-material table, **wrong for cls2**, which is only non-decreasing — a cid
   may legitimately own two records (Doppelwarrior `0x244D`, King of the Beasts
   `0x20B9`). Now a `strict=` parameter.
2. `POS_SITE_NATIVE` was written from memory as `a879e01c`; the real encoding is
   `A8 78 23 1C` (`ldrb r0,[r5,#2]` = `0x78A8`, `adds r3,r4,#0` = `0x1C23`). The
   guard caught it. Never hand-write an encoding you have not disassembled.
3. `timing_class_hook.verify(ov, check, ...)` folds its `check`'s return with
   `&=`, so a `check` that returns `None` TypeErrors. Ours now returns the verdict.

**⚠️ Clauses 2 and 3 use ov5 ⇒ NORMAL-DUEL ONLY** (overlay 41 evicts ov5 in a
puzzle). Clauses 0 and 1 stay pure data and live in every mode.

> ⚠️ SUPERSEDED — O15 was BUILT and in-game confirmed 2026-09-07; see C24/C25.
**⚠️ THE CARD IS NOT YET FAITHFUL: O15, "but banish it when it leaves the field",
is NOT built.** As it stands clause 2 revives *without* the banish restriction —
strictly better than printed. That is a known gap, not an acceptable deviation,
and clause 2 must not be reported as matching its text until it is closed.

---

### C16. ❌→✅ FREEZE ON SYNCHRO SUMMON — my bug, and the KB already had the answer

**User report, verbatim (2026-09-04):** *"I hit a freeze when jet warrior is
summoned see .ml3"* → *"at the moment of summoning - before i believe it worked
so this is a regression"*. ROM `4cc84340…` (clauses 0+1+2+3).

**Cause: four `blx` targets written without the Thumb bit.**
`blx rX` takes the instruction set from **bit 0 of rX**. With it clear the core
switches to **ARM** state and decodes Thumb halfwords as ARM words — instant
freeze. Every address in a disassembly listing is even, so copying one into a
stub constant is the *default* mistake.

| constant | was | is |
|---|---|---|
| `TURNLOG_QUERY` | `0x021A14E8` | `0x021A14E9` |
| `TURNLOG_POST` | `0x021D2584` | `0x021D2585` |
| `ZONE_PRED` | `0x021D6E40` | `0x021D6E41` |
| `LEVEL_GETTER` | `0x021B807C` | `0x021B807D` |

All four are Thumb functions (each begins `push {…}`). The one that froze was
`TURNLOG_QUERY` inside **`CAVE_JW_C1_COND`, the cls1 `+0C` condition** — which
the engine evaluates while *enumerating* the summon trigger. That is precisely
why the symptom was "at the moment of summoning" and why it presented as a
regression: clause 1 was confirmed working before clause 3 put a stub in that
slot.

**⚠️ THE KB ALREADY HAD THIS FACT AND I DID NOT APPLY IT.**
`thumb.blx_needs_thumb_bit` was written 2026-08-13 after "a run of freezes
wrongly blamed on gates and candidate counters", and says in terms: *"Always OR
in bit 0 for a BLX target"* and *"assert_thumb1_only does NOT catch this"*.
Prose in the KB did not stop the recurrence. **Two mechanical checks now exist,
and they are the actual fix:**

1. a module-level `assert v & 1` over every constant destined for a `blx`
   (in `patch_jet_warrior`, with the report quoted at the assertion);
2. a **whole-cave sweep** — disassemble each occupied `ov5_cave` slot, track
   `ldr rX,[pc,#imm]` → literal, flag any `blx rX` whose literal is even.
   **Result: 14/14 occupied slots clean.**

Nothing else could have caught it: `assert_thumb1_only` checks the stub's own
encoding, `verify()` passed, and a capstone listing shows only
`ldr rX,[pc,#imm]` — **the literal's value never appears in the disassembly.**

Fixed build: `rom_jet_warrior.nds` sha256 **`abd22deb…96a59723`**, both verifies
PASS. **AWAITING RE-TEST.** The `.ml3` savestate was not needed to find this and
was not parsed.

---

### C17. ❌→✅ CLAUSE 2 SUMMONED FOR FREE — two bugs, both mine, found offline

**User report, verbatim (2026-09-04):** *"Issues here, I can activate the effect
where there isnt a level <2 on the board - in this case it summons itself in
defense. If there is a <2 level monster on the board (see .ml4, level eater not
tributed) and .ml5 (nothing to tribute, still summons), .ml3 (effect is
activatable("* → confirmed: *"The cost machine never ran - it goes straight to
summon."* Items 1, 3 and 4 **confirmed working** on `abd22deb…`.

Diagnosed entirely from the user's savestates via `scratch/jw_cost_probe.py` and
`scratch/thumbemu` — **no duel spent**. Both savestates were verified to be from
the fixed build by comparing `CAVE_JW_C2_SLOT4` in live RAM against the emitted
blob.

**The mechanism that made a filter bug look like a missing cost.** The Tribute
machine `0x021E7C89` at phase 0 does `bl 0x0224AB38(desc, 0x0224A8C1)` — count
the legal candidates through the record's own slot2 — and on **0** it takes
`b 0x021E7C98` = **return 1**. That is the engine's *"there is nothing to pay, so
the cost is satisfied"* convention. My `+10` stub reads 1 as "the Tribute was
paid", stamps the latch, and the activation advances to the summon. **A slot2
that accepts nothing is indistinguishable, in play, from having no cost at all.**

**BUG 1 — the mask. Bits 0-1 are a 2-bit SIDE SELECTOR, not two flags.**
`0x021D6E48`: `movs r0,#3 ; ands r0,r4` then a switch — **1** = same side as the
source, **2** = opponent's side, **3** = a third mode gated on `0x021AE130`,
**0** = no side test. I had set bits 0 *and* 1 (`0x00020013`), selecting mode 3,
which rejected the one legal candidate. Measured on the user's `.ml4`:

```
mask        Level Eater L1   Dandylion L3   Brionac L5   Volcannon L5
0x00020013        0                1             1            1
0x00000011        1                1             1            1     <- side mode 1
```

The mask came from a sweep of the 168 thin wrappers whose owners print
"Tribute" — but those cards (Raviel, Hand of Nephthys, …) **Tribute for a
SUMMON** and use side mode 3 deliberately. **Matching on the word "Tribute" was
the wrong join; match on the printed POPULATION.** Now `0x00008011` — Swap Frog
`0x2115`'s exact mask, printed *"return 1 monster you control to the hand"*.
Bit 15 is kept and is *wanted*: its arm at `0x021D714E` requires
`0x021B088C(side,zone)` and `0x021BAF30(side, 1<<(zone+side*16))`, i.e. the
tributability checks.

**BUG 2 — slot3 returned 2 where it must return 1.** `dispatch.cls_slot_roles`:
slot3's return is a **code** — 0 = cannot activate, **1 = activatable but slot2
must find at least one legal target**, ≥2 = activatable unconditionally.
`CAVE_JW_C2_COND` was forwarding `0x021FF06D`'s value (≥2), so the effect was
offered with an empty board — and by the convention above, offering it *is*
summoning for free. It now returns **1**, so the engine runs our slot2 over the
board and refuses the activation when nothing passes.

**Verified offline on the user's own boards** (side/zone semantics via the
bit-15-free twin `0x00000011`; bit 15's arm reaches ARM-mode code the Thumb
emulator cannot run, so it rests on Swap Frog's precedent):

| state | board | filter verdict |
|---|---|---|
| `.ml4` | Level Eater L1, Dandylion L3, Brionac L5, self L5 | **exactly one ACCEPT** (Level Eater) |
| `.ml5` | self L5, Dandylion L3, Brionac L6 | **none** — so with bug 2 fixed the effect is no longer offered |

Fixed build: **`2220082a…8bb6baff`**, both verifies PASS, guards green.
**AWAITING RE-TEST.**

---

### C18. ❌→✅ ROUND 2 — the mask fix landed; slot3's code 1 is ignored here

**User report, verbatim (2026-09-04), on `2220082a…`:**
> 1. The effect is still offered, no cost machine is entered, then the card is
> summoned. See .ml4 (where jet warior is in GY)
> 2. The cost-machine is entered and target is tributed, then card is summoned.
> 3. Confirmed Unchanged  4. Confirmed Unchanged

So **C17's mask fix worked** — with a legal target the picker appears, the target
is tributed, and the summon happens (item 2). **C17's second fix did not.**

**`dispatch.slot3_code1_not_honoured_on_gy_offer` (new KB fact).**
`dispatch.cls_slot_roles` says slot3's code 1 means *"activatable but slot2 must
find at least one legal target"*, and names `0x0224AD94` as what implements it.
**The GY-action offer path never reaches `0x0224AD94`** — a BL scan of
`0x021EDA14`'s body finds no call to it — so my `1` was read as a plain yes.

And that is not cosmetic: by the zero-candidate convention from C17, a cost
machine that finds no candidates *returns success*. "Offered with no legal
target" and "resolves for free" are the same bug.

**Fix:** `CAVE_JW_C2_COND` counts the candidates itself with
`0x0224AB38(desc, 0x0224A8C1)` — **the same sweeper the Tribute machine calls at
`0x021E7D40`**, so the gate and the cost can never disagree about what a legal
Tribute is — and returns 0 on a count of zero. The stub grew 56 → 76 B, so its
reserve went 0x40 → 0x60 and the three later cave slots shifted up 0x20.

**Verified offline on the user's three savestates** (`scratch/thumbemu`, with the
new stubs and record slots written into the emulator's overlay so an old state
exercises the new build):

| state | board | `CAVE_JW_C2_COND` |
|---|---|---|
| `.ml3` | Dandylion L3, Brionac L5 | **0 — denied** |
| `.ml4` | Black Rose Dragon | **0 — denied** |
| `.ml5` | self L5, Dandylion L3, Brionac L6 | **0 — denied** |

**Positive control** (the thing that stops this being a gate that never opens):
on `.ml3`, raising the filter's cap from 2 → 3 → 9 moves both sweepers' counts
0 → 1 → 2, matching Dandylion (L3) and then Brionac as well. So the count
demonstrably reflects **our slot2's** verdict, not something else.
⚠️ The control had to use the bit-15-free twin mask `0x00000011`: bit 15's arm
reaches ARM-mode code the Thumb emulator cannot execute. That remains the one
piece of the mask resting on Swap Frog's in-game precedent rather than
measurement.

Fixed build: **`2cd44ac7…2acf544a`**, both verifies PASS, guards green, KB 434
facts / 0 FAIL. **AWAITING RE-TEST.**

---

### C19. ⛔ TWO-STRIKE STOP — the OFFER does not consult the cls2 slots at all

**User (2026-09-04), on `2cd44ac7…`:** *"See .ml2, jet warrior is still available
to activate"*. `.ml2` verified to be from that build (`CAVE_JW_C2_COND` in RAM ==
the emitted blob); board = Stardust Dragon L8 (ours) + Bubonic Vermin L3
(opponent's), i.e. **no legal Tribute**. And `CAVE_JW_C2_COND` run over that
state returns **0**. So the condition says deny and the game offers it anyway.

**Traced the offer path itself** (`0x021EC741(desc, 0)` under `scratch/thumbemu`
on `.ml2`, 6,398 instructions):

```
0x021EC740(desc, 0) -> 1          # = OFFER IT
  CAVE_JW_C2_COND  (+0C)   never reached
  CAVE_JW_TRIBFILT (+08)   never reached
  CAVE_JW_C2_SLOT4 (+10)   never reached
  0x021F04FC offer gate    never reached
```

⇒ **On this path the offer is decided by `0x021ECC6C` && `0x021EDA14`
(0x021EC89E / 0x021EC8AA), and neither consulted our record's slots.** Both
returned non-zero and `0x021EC8B8 movs r0,#1` offered the effect.

⚠️ Caveat on that trace, stated so the next session does not over-trust it: I
passed `r1 = 0` for both calls, and `0x021EC896` branches on
`[<global>+0x30]`, so a live call may take a different arm. It is strong
evidence, not a closed proof.

**TWO-STRIKE RULE INVOKED.** Hypotheses about this dispatch falsified in a row:
(1) "slot3 returning 1 makes the engine check slot2" — no; (2) "slot3 returning 0
denies the offer" — no. **Stop writing code, go to the precedent.**

**THE PRECEDENT, and the uncomfortable finding in it.** The template is
Blackwing - Zephyros `0x241C` (`dispatch.gy_self_ss_template`), cloned by
`card.grapha_clause1`:

```
cls2[652] = {0x241C, 0x02230EBD, 0x021E454D, 0x021F44D9, 0x021EB1B1, 0}
   +0C 0x021F44D8 -> 0x021F04FC = the "may this GY effect be offered" gate
   +10 0x021EB1B0 = the shared "return 1 monster you control" COST machine
```

`dispatch.gy_offer_free_zone_triple`: that gate's generic branch requires **free
monster zones** and returns 0 when there are none; a hard-coded triple
(Infernal Dragon `0x1B20`, King of the Beasts `0x20B9`, Zephyros `0x241C`) skips
that precondition because *their cost frees the zone*. Grapha needed an ov5 +0C
forcing that bypass.

**But Grapha's printed cost — "returning 1 Dark World monster you control" — has
exactly the same candidate problem, and its oracle list never tested it.**
>
> ⛔ **THE PARAGRAPH BELOW IS WRONG AND IS RETRACTED — see C20.** The user checked
> in game (2026-09-07): *"Grapha does not carry this bug, I have checked"*. Grapha
> is a **working precedent**; the absence of an oracle was not evidence of a bug,
> and treating it as such was my error. Kept only so the mistake is visible.
The
recorded checks are the pick list's contents, no LP loss, a full five-monster
field, and twice per Duel. **Nothing checks "is it still offered when you control
no Dark World monster?"** So the precedent may carry this same bug unnoticed —
it is *not* a known-good answer to my question, and I should not clone it
expecting one.

## Next Experiment

**Do NOT put the gate in `+0C` again.** Two options, in order of preference:

1. **Gate in `+10`, which is provably on the ACTIVATION path.** The in-game
   evidence proves slot4 runs at activation: the summon only happens because the
   cost machine returns 1 (the zero-candidate convention) and my stub forwards
   it. So `CAVE_JW_C2_SLOT4` should call `0x0224AB38(desc, 0x0224A8C1)` FIRST and,
   on a count of 0, return an ABORT value instead of chaining the cost machine
   (`dispatch.cls_slot_roles`: slot4 "returns 0 or negative to ABORT the
   activation and positive to advance"). Cost: the effect may still *appear*
   selectable and then do nothing — worse UX than greyed-out, but it stops the
   free summon, which is the actual rules violation.
2. **Find the real offer gate** by tracing `0x021ECC6C` / `0x021EDA14` with live
   arguments (r1 = the `[sp]` value `0x0224C591` passes, not 0) and identifying
   which of their calls reads a per-card slot. That is the only route to a
   correctly greyed-out effect.

---

## Ruled Out

- **"Use a Level 6+ effectless Fusion donor"** (the session's opening
  instruction). Killed by **C3**: an effectless Fusion is not in `0x0228F6C0`, so
  clause 1 would need to evict a real card's trigger or hook `0x022658FC`. The
  *reasoning* behind the instruction — Extra Deck, already has a material cost —
  is fully satisfied by Volcannon. The user approved the substitution.
  (Best effectless candidate, if one is ever wanted: **Meteor B. Dragon `0x126F`**
  — 1 binding, 0 noise hits, 0 CPU decks, name floor 16, but desc floor only 34 B.)
- **Junk Warrior `0x1E10` as donor.** Structurally ideal — same Level/Race/type,
  already in the trigger list, already owns the named-material row and a cls1
  record. Rejected because it is a **real playable Synchro** and the user is
  building a Junk deck (Junk Synchron, Junk Servant, Junk Speeder all shipped).
  CLAUDE.md: donors must be cards the user does not play.
- **Blue-Eyes Ultimate Dragon `0x1122`** (the only effectless Fusion whose desc
  slot reaches 46 B): it is a **material of Dragon Master Knight**
  (`A[64] @0x02270D94`, m2 slot `0x02270D98`), entry [3] of a 15-cid boss table
  at `0x0226C248`, and present in one CPU extra deck.
- **Editing `CAVE_JSP_TUNER` or claiming a fresh material-predicate hook site.**
  Unnecessary — the named-material rule is data (**C1**). For the record the four
  inner-predicate sites are all owned anyway: `0x022482B2` boggart,
  `0x022482B6` shooting_quasar, `0x022485D8` junk_speeder, `0x02248AAC`
  azure_eyes.
- **Cloning Zephyros `0x241C`'s cls2 `+04 0x02230EBC`** as the clause-2 resolver.
  `dispatch.resolver_hardcodes_printed_damage`: its phase `0x7F` hard-codes
  Zephyros's own 400 LP self-damage (`grep-the-template-cards-text-too`).
- **Editing `CAVE_JS_RIDER`** to attach the banish rider. Unnecessary — see O5 —
  and it would be a shared-stub edit to an in-game-confirmed card with no
  equivalence harness.

### Corrections to inherited claims

- **`0x021E7C89` is not "the filtered Tribute-cost machine" and its switch is not
  a filter selector.** That framing entered this session from a subagent report
  and was written into the approved plan as O3. Measurement (C9) shows the switch
  is a cid → named-tribute-cid map feeding a **UI prompt**, and that the real
  filtering is slot2. Recorded here so the next session does not re-derive it.

- **`patch_junk_speeder.py:236-243`** calls Quickdraw Synchron's restriction "a
  NINE-CID WHITELIST inside INNER `0x0224829C`". **There is no whitelist.** It is
  `0x02275B04` ∩ `has_set_code[0x4C]`, read at `0x022483CC` with the *same*
  binary search. The nine cids it measured are exactly the table rows whose
  *named* cid is a Synchron. The measurement was right; the mechanism was not.
- **`synchro.outer_pred` (`synchro_material.yaml:4`)** says OUTER `0x022485B4`
  "switches on r5 = the Synchro's cid → named-material leaves". It does a **table
  lookup first** (`0x02248610`) and only falls into the cid switch on a **miss**
  (`0x02248618 beq 0x02248660`).

---

## Open Questions

> **STILL OPEN, as of 2026-09-04 — everything else in this section is CLOSED and
> kept only for its reasoning:**
>
> - **The clause-2 offer gate.** Where is a GY offer actually decided, and can it
>   be made to depend on the cost being payable? See **C19** and
>   **`## Next Experiment`**. Two attempts falsified; two-strike stop in force.
> - **O11.** Jet Warrior inherits Volcannon's `card_genre` effect-category tags
>   (bits 1, 10, 34 — *destroy + burn*, not *bounce + revive*). Proven
>   not class-coupled, so believed to be a deck-editor cosmetic, but the bits are
>   undecoded and the CPU AI may read them.
> - **O14.** Whether clause 1's `+0C`/`+10` move can regress the confirmed clause
>   1 via `dispatch.slot3_reevaluated_after_cost`. **Partly answered:** the user
>   confirmed clause 1 unchanged on 2026-09-04, so no regression has been
>   observed — but the mechanism was never ruled out.
  ⚠️ SUPERSEDED — CLOSED 2026-09-07, in-game confirmed; see C24/C25.
> - **O15.** The banish rider — not built, needs a decision (it re-touches Jet
>   Synchron).
> - **Mask bit 15** (`0x021D714E`, the tributability checks) is the one shipped
>   element never executed offline: its arm reaches ARM-mode code the Thumb
>   emulator cannot run. Rests on Swap Frog's in-game precedent.
>
> **CLOSED this session:** O1, O2 (C11+C12) · O3 (C9) · O6, O9, O10 (C13) ·
> O12, O13 (C14) · O7 (C15, verify asserts one cls1 + one cls2, different
> enumerators).

- ~~**O1.** Can an Extra-Deck cid ride the GY-action → class-2 path?~~
  **CLOSED by C11 + C12 (2026-09-04): YES.** No card_type read on the path; the
  one per-cid gate is dormant in a normal duel.
- ~~**O2.** `0x23EB`'s unexplained binding at `0x0226D974`.~~ **CLOSED by C12:**
  its only consumer on this path is the dormant gate. No mitigation needed.
- **O1 (superseded, kept for the reasoning). Can an Extra-Deck cid ride the GY-action → class-2 path?**
  No stock row of `0x0228DDF8` is an Extra-Deck monster, and memory
  (`otn-leave-trigger-cls2`) says "cls2 dispatch NEVER reaches an Extra-Deck
  donor" — but that finding was about the **leave-field** enumeration, a
  different path.
  **No blocker found, not closed.** Disassembled this session:
  - the zone scanner `0x0224C88E` walks the **zone array** —
    `0x0219CE2C(side,zone)` = count, `0x0219CAE4(side,zone,idx)` = cid,
    `0x0219CBB8(side,zone,idx)`, then `blx [row+8]` — matching on **cid alone**;
  - `chk 0x0224C591` zeroes a 0x24-byte descriptor via `0x0209A080` and fills
    `desc[+0]=cid`, `[+2]=side`, `[+3]=0x0E` (GY), `[+5]=2` (**CLASS 2**),
    `[+4]=index`, `[+0xC]=r7`, then calls `0x021EC740`;
  - **neither reads `card_type`, `is_extra_deck 0x0202307C`,
    `card_category 0x02022D70`, nor the Extra-Deck array (player+0x4E4)**;
  - the only per-cid gate is `0x0202345C` (result must be `>= 2`), which for a
    monster is a binary search of a 118-entry list, and it is applied **only**
    when `[sp+4]` is set (off-turn / outside Main Phase) — i.e. a **quick-effect**
    gate. Correct behaviour for an ignition GY effect, not an Extra-Deck gate.
- **O2.** `0x23EB` is inherited into a cid list at **`0x0226D874`** (three sorted
  sub-lists, 129 u16 total; `0x23EB` is the **last** entry of sub-list 3,
  terminator `0x0000` at `0x0226D976`). Base literal `@0x021A8AF0`; consumer is
  the per-cid switch **`0x021A897C(r0 = cid, r1 = ?)`**, which calls
  `0x0202ABE8`, binary-searches a 48-entry list, then jumps a 16-arm table on
  `r1 - 0xE`. **Semantics unidentified.** Mitigation if it matters is cheap:
  replace `0x23EB` with a phantom cid `> 0x23B9`, a 2-byte sort-safe edit.
- ~~**O3.** The "Tribute 1 Level 2 or lower monster" cost.~~ **CLOSED by C9:**
  slot4 = `0x021E7C89` verbatim (pure data), slot2 = a ~0x30 B ov5 stub.
- **O9.** Which mask for the slot2 tail-call — `0x00008011` ("1 monster you
  control", Swap Frog's, **no** face-up bit) or `0x00008015` ("face-up"). A
  Tribute may legally use a face-down monster, so `0x00008011` is the intended
  choice; confirm against the Rosetta corpus before building.
- **O10.** The level getter. `0x0202ABD8(cid)` is the **printed** Level (used by
  `can_synchro_summon 0x02249540`). The **live** Level can differ (Level Eater,
  Sun Dragon Inti…). The predicate prologue at `0x021D91DC` calls
  `0x021B44B4(side, zone, sp+8)` to fill a stat struct, which is the likelier
  home of the live Level. Decide, and prefer the live one if the offset is cheap
  to prove.
- **O4.** Forcing **Defense Position**. `handss.self_ss_from_gy_resolver
  0x0220731D`'s second per-cid switch `0x02207424` (init `movs r6,#1 ; movs
  r4,#2`) picks the SS-commit position: `r4=1` (Defense) for
  `0x0E10 0x13C7 0x1E98 0x1FDF 0x2400`; `r4=1,r6=0` (face-down Defense) for
  `0x20DC 0x2209`; **everything else defaults to `r4=2` = "player chooses"**.
  Needs a new switch arm or an ov5 clone — unpriced.
- **O5.** The banish rider is believed free: `0x021C479C(side, slot, key 0x1E15,
  kind 3, param 0)` called directly from our resolver, per
  `rider.banish_marker_is_cid_blind_to_the_destination`. **Re-verify the fact's
  grading and the exact signature against `patch_jet_synchron.py` before use.**
- **O6.** Clause 3 needs **two independent** turn-log latches
  (`0x021A14E8` query / `0x021D2584` stamp). The log is keyed on the **cid**, so
  a single stamp would lock both clauses. Two distinct `kind` values must be
  chosen and cross-checked against every kind already used by a shipped patch.
- **O11.** Jet Warrior inherits Volcannon's `card_genre` **effect-category tags**
  (bits 1, 10, 34), which describe *destroy + burn*, not *bounce + revive*. The
  census proves they are not class-coupled, so this is believed to be a
  deck-editor-filter cosmetic — but the bits are **undecoded**, and the CPU AI
  may read them when deciding how to play the card. Deliberately not guessed at.
- **O7.** Volcannon will own **one cls1 and one cls2 record**. Believed *not* a
  `find_event_handler 0x0224A118` leftmost shadow (the Warwolf E1/E2 bug was two
  records of the **same** class under one cid), but confirm explicitly.
- **O8.** The description must fit **272 B**. A 282 B draft exists and needs ~10 B
  trimmed. Korean keeps the donor's name and text (slot 0 B) — an accepted
  deviation, Changer Synchron precedent.

---

## Next Experiment

### C20. The C19 caveat is CLOSED — the trace was faithful. And a contradiction.

**⚠️ WITHDRAWN: "Grapha may carry this same bug."** The user checked in game and
stated plainly (2026-09-07): *"Grapha does not carry this bug, I have checked"*.
`card.grapha_clause1` is a **working precedent** — its GY effect is correctly not
offered when its cost cannot be paid. My speculation that its oracle list had
simply missed the case was wrong and is retracted; do not act on it.

**The C19 trace passed the RIGHT arguments after all.** Resolved the two literals
and read them from the user's own savestates:

```
0x021EC896 global = 0x0229AB7C  ->  [+0x30] = 0x00000000 in ml2/ml3/ml4
0x0224C5BC global = 0x0229A9FC  ->  [+0x44] = 0        in ml2/ml3/ml4
0x0224C5CC table  = 0x0229A7FC  ->  [sp] (= r1) = 0    in all three
```

So `r1 = 0` and the non-loop arm at `0x021EC89E` **were** correct, and C19's
"strong evidence, not a closed proof" is now a **closed measurement**:
`0x021EC740` returns 1 (offer) while `+08`, `+0C`, `+10` and `0x021F04FC` are
never reached.

**The offer-builder layer, newly identified.** The GY-action zone scanner is the
function `0x0224C820` (which contains `0x0224C88E`), and it has exactly ONE
caller: **`0x0224B4F4`, inside `0x0224B380`** — the menu builder. It works by
*count delta*: `0x0224B4E8` snapshots `[list+6]`, calls the scanner, then
`0x0224B4FE-0x0224B502` tests `[list+6] - snapshot >= 2` before showing prompt
`0xE2` and building the submenu. The sibling scanner `0x0224CD08` (cid-keyed,
`blx [row+0xC]`) is called from `0x0224B53A` in the same function and from
`0x0224CCF6`. **So the scanner APPENDS one entry per offerable GY action, and
`chk 0x0224C591` returning 1 is what makes it append.**

**THE CONTRADICTION, stated for the next session rather than guessed at:**

- Grapha is **confirmed correct in game** (user, 2026-09-07) — not offered when
  its cost is unpayable.
- Jet Warrior is **confirmed wrong in game** (user, 2026-09-04) — offered, and
  resolves free, when its cost is unpayable.
- Both reach `0x021F04FC`: Grapha via its transcribed `+0C`
  (`patch_grapha.gate_stub`), Jet Warrior via Plaguespreader's `0x021FF06D`,
  whose documented body is `0x021F0168(desc, arg) && 0x021F04FC(desc, arg)`.
- Both cost machines share the zero-candidate → return 1 convention
  (`0x021EB1D6: bl 0x0224AA94 ; bne ; movs r0,#1` for Grapha's bounce machine;
  `0x021E7D40: bl 0x0224AB38 ; ... b 0x021E7C98` for the Tribute machine).
- And the measured offer path consults **neither** card's `+0C`.

**One of those five statements is false, and finding which is the task** — most
likely the fourth or fifth: the descriptor my probe synthesises may differ from
the live one in a field that changes which arm runs (`desc[+0xC]`, which
`0x0224C591` fills from `r7` and which `0x021F04FC` feeds to `ZONE_INDEX
0x021A2511`, is **zero in my probe and almost certainly not zero in play**).

---

> ⚠️ The M1 / M3 / M4 list that used to sit here is **CLOSED and removed** —
> M1 by C12, M3 by C9, M4 by C14's O12, M2 by C15's ledger registration. Do not
> resurrect it.

**THE TASK (user chose "Option 2", 2026-09-04): find where the GY offer is
actually decided, and gate there.** Full write-up, with the exact commands, the
literals to resolve and the discriminating control, is in
**`PROMPT_jet_warrior_clause2.md`** — that file is the authority for the next
session; this note is the log behind it.

In short, and agreeing with the prompt:

1. **FIX THE DESCRIPTOR FIRST — it is the most likely reason the trace found
   nothing.** My probes synthesise a descriptor with `desc[+0xC] = 0`, but
   `0x0224C591` fills it from `r7`, and `0x021F04FC` feeds `desc[+0xC]` to
   `ZONE_INDEX 0x021A2511(side, desc[+0xC])`, which **returns < 0 → reject** on a
   bad value. A wrong `desc[+0xC]` could make every gate bail early and make the
   whole path look like it skips them. Recover the real `desc[+0xC]` for a GY
   card from a savestate (it is the acting card's instance ref — see
   `dispatch.descriptor_acting_instance`, `desc[+0xC]` indexes the instance table
   at `0x0229C33C`, stride 8, cid = word & 0x3FFF) and re-run **every** probe in
   `scratch/jw_cost_probe.py` and the C19 trace with it.
2. **A/B AGAINST GRAPHA ON ONE BOARD.** Grapha is a confirmed-working precedent
   (user, 2026-09-07). Build its `patch_grapha.gate_stub()` bytes into the
   emulator at a scratch address and run **Grapha's gate** and
   **`CAVE_JW_C2_COND`** over the SAME savestate with matched descriptors. The
   first input on which they disagree is the answer. If they agree, the
   difference is not in `+0C` and the search moves to `0x0224B380`, the menu
   builder (see C20).
3. **Then bisect** `0x021ECC6C` vs `0x021EDA14` with the corrected descriptor.

**Fallback (Option 1), only after telling the user:** `CAVE_JW_C2_SLOT4` calls
`0x0224AB38(desc, 0x0224A8C1)` first and returns an ABORT value (0 or negative,
`dispatch.cls_slot_roles`) on a count of zero, instead of chaining the cost
machine. Provably on the activation path — the free summon happens *because* the
cost machine returns 1 and that stub forwards it. Converts a rules violation into
a cosmetic wart (selectable, does nothing).

> ⚠️ SUPERSEDED — O15 was BUILT and in-game confirmed 2026-09-07; see C24/C25.
**Also still open: O15, the banish rider** — see the prompt's own section. Not
started; it edits an in-game-confirmed card and costs a Jet Synchron re-test, so
it needs an explicit decision.

---

### C21. ✅ THE CONTRADICTION RESOLVES — statement 5 is FALSE. The offer path DOES consult `+0C`; C19's BL scan was TRUNCATED.

Measured **2026-09-07**, by disassembling the **whole** of `0x021EDA14` (extent
`0x021EDA14..0x021EDCA2`, ending at `pop {r4,r5,r6,r7,pc}`) and scanning every
`bl`/`blx` in it with capstone.

RULED-OUT #1 rested on the claim *"a BL scan of `0x021EDA14`'s body finds no call
to `0x0224AD94`"*. **That scan covered only the first ~0xE0 bytes of a 0x290-byte
function.** Eight call targets were missing from it — `0x02029E80`, `0x0202A158`,
`0x0214C1D4`, `0x021A25A0`, `0x021AE5F4`, `0x021D3788`, `0x0224AF7C` and
**`0x0224AD94`, which is called THREE times** (`@0x021EDC06`, `@0x021EDC60`,
`@0x021EDC8C`).

**The arm a GY descriptor actually takes:**

```
0x021EDB62  ldrb r0,[r5,#5]        ; desc[+5] = 2  (class 2, set by 0x021EC892)
0x021EDB64  cmp  r0,#0 ; bne       -> 0x021EDC70
0x021EDC70  bl   0x0224AF7C        ; timing class, from the record's +10 LITERAL
0x021EDC76  cmp  r0,#2 ; beq       -> 0x021EDC84 movs r0,#1 = OFFER, unconditional
0x021EDC7A  bl   0x021D3788        ; per-cid switch on desc[+0]
0x021EDC80  cmp  r0,#0 ; beq       -> 0x021EDC88
0x021EDC88  ldr r1,[sp] ; adds r0,r5,#0 ; bl 0x0224AD94   ; *** RECORD CONSULTED ***
0x021EDC90  str r0,[sp,#0x14]      ; ...and its return IS the offer verdict
```

**and `0x0224AD94` calls `+0C`:**

```
0x0224AD9A  bl 0x0224A118 ; r4 = find_event_handler(desc)
0x0224ADA2  movs r6,#1                     ; <- THE DEFAULT IS "OFFER"
0x0224ADA4  cmp r0(class),#0 ; bne 0x0224ADF4
0x0224ADF4  cmp r4,#0 ; beq 0x0224AE3E      ; NO RECORD  -> r6 stays 1 -> OFFER
0x0224AE06  ldr r2,[r4,#0xc] ; cmp r2,#0 ; beq 0x0224AE14  ; NO +0C -> r6 = 1 -> OFFER
0x0224AE10  blx r2                          ; *** +0C, args (desc, [sp]) ***
0x0224AE12  adds r6,r0,#0
0x0224AE14  cmp r6,#1 ; bne 0x0224AE32      ; ==1 -> ALSO require slot2 to find one
0x0224AE18  ldr r0,[r4,#8] ; ... bl 0x0224A988 ; r6 = (count != 0)
0x0224AE3E  movs r0,#1 ; cmp r6,#0 ; bgt    ; RETURNS r6 > 0
```

⇒ **`+0C` returning 0 DOES deny the offer, and slot3 code 1 IS honoured here**
(`cmp r6,#1` then slot2 counted via `0x0224A988`). Both "falsified" hypotheses
describe the real mechanism. **`dispatch.slot3_code1_not_honoured_on_gy_offer` is
WRONG and must be corrected in the KB, not worked around.**

Two corroborations that this is the real path and not a lookalike:

- **Zephyros / Grapha take exactly this arm too.** `0x0224AF7C` returns 2 only
  when `+10 == 0x021E51E5`; Zephyros's `+10` is `0x021EB1B1` and Jet Warrior's is
  `CAVE_JW_C2_SLOT4|1`, so both fall through its literal chain to
  `0x0224B028 movs r0,#0`. `0x021D3788`'s cid switch (`0x20FD 0x18D1 0x1ECE
  0x23B9 0x2201 0x24DB 0x0E10 0x22C5 0x24E6`) contains neither `0x241C` nor
  `0x23EB`, so both fall to `0x021D380C movs r0,#0`. **Both cards therefore reach
  `0x0224AD94`, and Grapha's confirmed-correct greying-out is produced by its
  `+0C`** — which is exactly the working precedent the user pointed at.
- **Our record IS findable.** `find_event_handler` picks the table by class from
  the jump table at `0x0224A134` (`class 0 -> 0x0224A148`, `1 -> 0x0224A166`,
  **`2 -> 0x0224A13C`**, `3 -> 0x0224A16C`); arm 2 binary-searches cls2
  `0x02275C04`, `0x2B9` rows, stride `0x18` — a lower-bound loop
  (`0x0224A17E..0x0224A19A`) followed by an exact compare at `0x0224A1A0`, so the
  table MUST stay sorted. Replicated over the real images: cls2 keys are strictly
  ascending in **both** `rom.nds` and `rom_jet_warrior.nds` (0 inversions), and
  `0x23EB` is found at **row 643** (stock lower_bound for it is 644; the dropped
  phantom `0x1655` was row 126). So `r4 != 0` and the `blx` at `0x0224AE10` is
  reached.

⇒ **The false statement in C20's list is #5.** The emulated trace diverged
somewhere before `0x021EDC70` — the synthesised descriptor is the prime suspect,
exactly as C20 predicted. **Find the divergence point; do not re-litigate the
mechanism.** ⚠️ This is reverse-engineering, not a third hypothesis: the
two-strike stop is satisfied by measurement, and no code has been written.

---

### C22. ⛳ ROOT CAUSE, MEASURED AND A/B-CONFIRMED — **our own shared timing-class hook makes the offer unconditional.**

**2026-09-07. `scratch/jw_offer_trace.py` + `scratch/jw_offer_ab.py`.** No ROM
written; emulation over the user's own savestates from build `2cd44ac7…`.

**What was faithful this time.** Every earlier probe hand-rolled the descriptor
with `desc[+0xC] = 0`. This one recovers the real value and lets `0x0224C591`
build its own: the zone scanner invokes the callback at `0x0224C934` as
`blx [row+8]` with `r0 = side`, `r1 = row cid`,
`r2 = 0x0219CBB8(side, zone, idx)`, and `0x0224C591` stores that `r2` into
`desc[+0xC]` (`strh r7,[r0,#0xc]`). Measured `desc[+0xC] = 108` on ml2/ml3/ml4.
**It changed nothing** — the divergence was elsewhere, so C20's `desc[+0xC]`
suspicion is RULED OUT.

**The divergence.** The path does reach `0x021EDC70` and call the classifier
`0x0224AF7C` — and then takes the **short-circuit** at
`0x021EDC76 cmp r0,#2 ; beq 0x021EDC84 movs r0,#1`, i.e. **`0x0224AF7C` returns
2**, so `0x0224AD94` and therefore `+0C` / `+08` are never reached.

`0x0224AF7C` returns 2 only for the tag `0x021E51E5`. Jet Warrior's cls2 `+0x10`
is `CAVE_JW_C2_SLOT4|1`, **not** that tag. It returns 2 because
**`timing_class_hook.ARM_JW` substitutes the tag** — the hook replaces
`ldr r0,[r0,#0x10] ; cmp r0,#0` at `0x0224AF96` with `bl CAVE_TIMINGHOOK`
(verified byte-for-byte: stock `0x0224AF96 ldr r0,[r0,#0x10]`, built
`bl 0x0239E340`), and `ARM_JW` is

```
ldrh r1,[r4,#0]  ; cmp r1,#0x23EB  ; bne next
ldr  r0,=0x021E51E5 ; b out          <- UNCONDITIONAL
```

keyed on **`desc[+0]` alone**, with none of the `zone == 0x0E && event > 6`
window that `ARM_LP` and `ARM_JET` carry. Its comment — *"one unconditional arm
is correct for every descriptor that reaches here with this cid"* — is the false
assumption: the GY-action **offer** descriptor also reaches here with this cid,
and for it "class 2" means *skip the condition entirely*.

**THE A/B (`scratch/jw_offer_ab.py`), reverting the 4-byte hook in emulator
memory only — an exact simulation of "the JW arm does not fire here":**

| board | A: hook as shipped | B: hook reverted |
|---|---|---|
| ml2 | `0x0224C591 -> 1` **OFFERED**, short-circuit hit, `+0C` never reached | `-> 0` **DENIED** via `0x0224AD94` → `blx +0C` → `CAVE_JW_C2_COND` → `CAVE_JW_TRIBFILT` |
| ml3 | `-> 1` **OFFERED**, same | `-> 0` **DENIED** (`+0C` returned 1, then `0x0224A988` counted 0) |
| ml4 | `-> 1` **OFFERED**, same | `-> 0` **DENIED** |

All three boards hold **no legal Tribute**, so DENY is the correct verdict, and
the shipped `+0C` produces it the moment it is allowed to run.

⇒ **Both "falsified" hypotheses (RULED OUT #1 and #2) described the real
mechanism.** They failed in game for a reason neither predicted: our own
timing-class arm was short-circuiting the gate above them. **`+0C` was always the
right place; it was simply never called.**

**Why Grapha is correct and we are not** — the contradiction fully closed:
Grapha has **no arm in this hook**, so its classifier returns 0, it reaches
`0x0224AD94`, and its `+0C` greys the effect out. Jet Warrior is the only card in
the ROM whose GY offer is short-circuited, and *we* put it there.

**The classifier has 5 call sites in ov3** (byte-pattern scan for the BL
encoding): `0x021D3A0A`, `0x021D3FF6`, `0x021D40A0`, **`0x021EDC72`** (the GY
offer) and `0x021F053E` (inside Zephyros's `0x021F04FC` gate). Only `0x021EDC72`
tests `== 2`; the other four test the result as a boolean, so they care whether
the effect *has* a class, not which.

**⚠️ NOT YET DECIDED — the discriminator.** The arm must keep returning the tag
for whatever descriptor clause 1 needs it for, while falling through for the
GY-action offer. `desc[+5]` (record class: clause 1 is **cls1** → class 1,
clause 2 is **cls2** → class 2) and `desc[+3]` (zone `0x0E`) are both candidates;
the module's own header documents `desc[+5]` as *"never 0 or 3 here"*. Changing a
shared module that two in-game-confirmed cards ride (Lightpulsar `0x0FB1`, Jet
Synchron `0x224C`) requires re-running `scratch/timing_hook_equiv.py` and
asserting no shipped cid's answer moved
(`otn-shared-hook-lift-prove-by-execution`). **Not started — awaiting the user.**

---

### C23. ✅ THE FIX — the discriminator. **IN-GAME CONFIRMED BY THE USER 2026-09-07.**

User: *"yes measure it then build"*.

**The discriminator is closed, not chosen.** `0x0224AF7C` reads `+0x10` out of the
record that `find_event_handler 0x0224A118` returns, and `find_event_handler`
picks **which table to search from `desc[+5]`** — jump table `@0x0224A134`
(halfwords `0x12 / 0x30 / 0x06 / 0x36`): class 1 → cls1 base `0x022860D4`,
class 2 → cls2 base `0x02275C04`. So the classifier is looking at clause 1's
cls1 record **iff `desc[+5] == 1`** and at clause 2's cls2 record **iff
`desc[+5] == 2`**. Both records were confirmed to carry cave pointers at `+0x10`
in the built ROM (`cls1[1279] @0x0228D8BC +10 = 0x0239E981`,
`cls2[643] @0x0227984C +10 = 0x0239EA21`), so clause 1 genuinely still needs the
substituted tag.

**The change** — `timing_class_hook.ARM_JW`, from unconditional to:

```
ldrb r1, [r4, #0x5]
cmp  r1, #0x1          ; desc[+5] == 1  ->  clause 1's cls1 record
bne  out
ldr  r0, =0x021E51E5
b    out
```

Falling through leaves clause 2 at class 0 — what Zephyros `0x241C` and Grapha
have (`cls2 +0x10 = 0x021EB1B1`, equally absent from the classifier's literal
chain), and Grapha's correct greying-out is in-game confirmed by the user
2026-09-07. **Class 0 is the correct class for a GY ignition.**

**Pre-build proofs, all offline, all on the user's own savestates:**

- `scratch/timing_hook_equiv.py` — **extended this session to sweep `desc[+5]`**,
  without which it would never have exercised the new discriminator. 159,120
  inputs through both emitted blobs: `0x0FB1` (Lightpulsar) **unchanged**; only
  `0x224C` and `0x23EB` differ from the pre-lift stub, as registered in `ADDED`.
- `scratch/jw_offer_fixsim.py` — writes the newly emitted stub over
  `CAVE_TIMINGHOOK` **in emulator memory only** and re-runs the real path:

  | board | old arm | new arm | classifier cls1 | classifier cls2 | LP `0x0FB1` control |
  |---|---|---|---|---|---|
  | ml2 | `-> 1` OFFERED | `-> 0` **DENIED** via `blx +0C` | 2 → **2** | 2 → **0** | 0 → 0 |
  | ml3 | `-> 1` OFFERED | `-> 0` **DENIED** via `blx +0C` | 2 → **2** | 2 → **0** | 0 → 0 |
  | ml4 | `-> 1` OFFERED | `-> 0` **DENIED** via `blx +0C` | 2 → **2** | 2 → **0** | 0 → 0 |

  Both halves hold at once: the offer denies *and gets there by actually reaching
  `0x0224AE10 blx +0C`*, while a class-1 descriptor still classifies as 2 — the
  class clause 1 was in-game confirmed with on 2026-09-04.

**Build.** `_build_jet_warrior.py --text` → `rom_jet_warrior.nds`
sha256 **`d61470207f26e373240f21ceae5ff304d36385b5d52bb627929d77e6d7113f24`**
(was `2cd44ac7…`). `BUILD_EXIT=0`; `jet_synchron.verify: PASS`,
`jet_warrior.verify: PASS`. The shared stub grew 76 B → **88 B**, still inside
its `0x100` reserve, so **no cave move and no ledger change**;
`check_allocations` still reports `186 ov5 slots (170 live), 161 phantom claims,
11 ov3 dead-code claims (54 B free)` / `[OK]`.

**KB.** `dispatch.slot3_code1_not_honoured_on_gy_offer` retired to UNVERIFIED
with `corrected_by:`, and the correction
`dispatch.gy_offer_consults_slot3_and_the_timing_class_can_bypass_it` added and
PASSING. `verify_knowledge` → `435 facts: 397 PASS 0 FAIL 38 UNVERIFIED`.

**✅ IN-GAME CONFIRMED BY THE USER 2026-09-07**, all five oracles, on this exact
ROM — *"1. CONFIRMED / 2. CONFIRMED / 3. Confirmed / 4. Confirmed /
5. Confirmed"*, reading confirmed by the user before this line was written.
Test 1 (**not offered with no legal Tribute**) is the one this session existed
for; tests 3 and 5 were the regression risk the change carried, since clause 1
and clause 3 ride the very arm that moved, and both came back clean.

**The lesson worth carrying forward** is not about this card. Two in-game tests
were spent, and a "two-strike stop" invoked, chasing a mechanism that was never
broken: `+0C` was always the right place and slot3 code 1 was always honoured.
What actually happened is that **a shared, cid-keyed hook we installed for one
clause silently changed the answer for another clause of the same card**. The
two failures were mis-attributed because the trace that exonerated `+0C` was
built on a **truncated BL scan** — a measurement error, not a reasoning error,
and one that no amount of further hypothesising would have found. Corroborating
against a card known to work (Grapha) is what forced the contradiction into the
open; scanning the *whole* function is what resolved it.

---

### C24. O15, the banish rider — the pre-build checklist

**2026-09-07, user: "Do O15 please".** Clause in scope: *"…but banish it when it
leaves the field"*, the only unimplemented part of clause 2. Everything already
confirmed (clauses 0/1/2/3) must not regress.

**1. PROVEN — the donor reaches the hook.** The rider attaches at the DEFAULT
leaf `0x02268666` of the summon-event per-cid switch (root `0x022680A8`, input
`ldrh r2,[r4,#0x12]`). `rider.banish_marker_attach_site` simulated `0x224C`,
`0x0FB1`, `0x1463`, `0x1F18` and `0x19CB` — **but never `0x23EB`**, and a donor
with its own dedicated arm would never reach the hook at all. Measured this
session with `scratch/summon_event_sim.walk`:

```
0x23EB  arm body @0x02268666:  <-- DEFAULT   # JET WARRIOR donor -- UNDER TEST
0x224C  arm body @0x02268666:  <-- DEFAULT   # Jet Synchron, known
0x1EA9  arm body @0x02268546:  <-- DEDICATED ARM   # Plaguespreader, known
0x1E15  arm body @0x02268546:  <-- DEDICATED ARM   # Quillbolt, known
0x19CB  arm body @0x02268666:  <-- DEFAULT   # Treeborn Frog, known
```

The two known-arm controls landing on `0x02268546` is what validates the walk.

**2. PROVEN — the node alone is sufficient for an arbitrary cid.**
`rider.banish_marker_is_cid_blind_to_the_destination`, and it is *in-game
confirmed* on Jet Synchron (user 2026-09-03) — a donor the engine's own per-cid
switch never reaches was banished on leaving. Jet Warrior's clause 2 uses the
**same** GY self-SS resolver `0x0220731D`, so the same summon event fires.

**3. PROVEN — arming site.** The rider must attach on clause 2's revive **only**,
never on a Synchro Summon of Jet Warrior (which prints no rider). `CAVE_JW_C2_POS`
is the right one-shot setter: it is cid-scoped AND lives at `0x022074E6` inside
the GY self-SS resolver, immediately before the SS commit `bl 0x0226925C` at
`0x022074EA`. Clause 1 uses a different resolver and the Synchro Summon never
enters `0x0220731D`, so the byte can only be set by the clause-2 revive. This is
**tighter than Jet Synchron's**, which arms from its resolver.
⚠️ The byte is cleared by the CONSUMER, never the setter —
`rider.banish_marker_attach_site`'s timing warning (the commit `0x0226925C` can
finish after the resolver returns; the window that killed Upstart Golden Ninja's
first STAGE latch).

**4. PROVEN — register safety at the arming site.** `_stub_c2_pos` may write only
`r0` and `r3` (the two registers the displaced `ldrb r0,[r5,#2] ; adds r3,r4,#0`
writes); `r1`, `r2`, `r4`, `r5` are live. Setting the byte needs an address and a
value — both fit in `r0`/`r3`, which are clobbered on that branch anyway. **No
new register is touched, so the 68-cls2-record equivalence argument still holds
by construction.**

**5. Cave.** `CAVE_JS_RIDER 0x0239E680` is `0x60` with ~28 B spare and **abuts
`CAVE_JS_ARM 0x0239E6E0`**, so it cannot grow to hold a second arm. Following the
`CAVE_LP_TIMING -> CAVE_TIMINGHOOK` precedent exactly: a **new shared slot** for
the two-arm stub, the old slot **RETIRED**, plus a new 4-byte one-shot for Jet
Warrior.

**Cost to the user, stated up front:** this edits `patch_jet_synchron`, which is
in-game confirmed, so **Jet Synchron needs a re-test** alongside the new Jet
Warrior banish test.

---

### C25. ✅ O15 — the banish rider. **IN-GAME CONFIRMED BY THE USER 2026-09-07.**

**The lift.** `0x02268666` is a single 4-byte BL already owned by
`patch_jet_synchron`, so it became a shared module —
**`otn_enhanced/effects/summon_rider_hook.py`** — with a cid register,
the `criteria_row_hook` / `timing_class_hook` structure exactly.
`CAVE_JS_RIDER 0x0239E680` is **RETIRED** (it could not grow: `CAVE_JS_ARM` sits
at exactly `+0x60`); the stub is re-homed to **`CAVE_RIDERHOOK 0x0239EAC0`**
(`0x80` reserve, 88 B used, 2 arms). Jet Warrior's one-shot byte is
**`CAVE_JW_ARM 0x0239EB40`** (4 B, ships clear). `CAVE_FREE` → `0x0239EB50`.

Each arm compares the event record's cid, loads **its own** one-shot byte, and
falls into a shared consume-and-attach tail:
`0x021C479C(side=[r4+2], slot=[r4+4], key=0x1E15, kind=3, [sp]=0)`.

**Arming.** `_stub_c2_pos` (the Defense-Position hook) now also sets
`CAVE_JW_ARM`. Its register invariant is intact — the two added instructions use
`r0` and `r3`, the only registers that branch already clobbers — so the
by-construction equivalence over the 68 cls2 records that share resolver
`0x0220731D` still holds, with no harness needed.

**Proofs.**

- `scratch/rider_hook_equiv.py` — **new harness.** Executes the committed
  pre-lift blob (`patch_jet_synchron._stub_rider`, kept solely as the reference)
  against the shared blob over every (cid × one-shot-byte combination), comparing
  **four** observables: whether `0x021C479C` was called and with which
  `(side, slot, key, kind, param)`; **both** one-shot bytes afterwards (so a stub
  clearing the *wrong* card's byte is caught); the replayed `r0`/`r6` that
  `0x0226866A`'s `cmp r0,r6` consumes; and that `r4` survives. Result:
  `cids whose observable behaviour differs: {'0x23eb': 2}` —
  **`0x224C` unchanged** — plus positive checks that the new arm attaches
  `key=0x1E15, kind=3, param=0` when armed, clears its byte, and does **nothing**
  when unarmed.
- Disassembled from the finished ROM: `blx r7` loads **`0x021C479D`** — odd, so
  `thumb.blx_needs_thumb_bit` is satisfied — and the return is
  `pop {r4, r5, r7, pc}` with **`r6` correctly absent**, or the pop would undo
  the replayed literal.
- `assert_thumb1_only` PASS on both changed stubs; `CAVE_JW_C2_POS` is 32 B in
  its `0x20` reserve (**exactly full** — any further edit there needs a bigger
  slot; `check_allocations` is the backstop).

**Build.** `rom_jet_warrior.nds` sha256
**`128e1269c1f1f3dcff2ce401351e2789db432a9f6228a2373fa252cc069ce441`**
(was `d6147020…`). `BUILD_EXIT=0`, `jet_synchron.verify: PASS`,
`jet_warrior.verify: PASS`. Ledger refreshed — 188 ov5 slots, `[OK]`.
KB: `rider.summon_rider_hook_is_shared` added and passing —
`437 facts: 399 PASS 0 FAIL 38 UNVERIFIED`.

**✅ IN-GAME CONFIRMED BY THE USER 2026-09-07**, all four oracles, on this exact
ROM. Their words: *"1. Confirmed / 2. Confirmed / 3. No Regression"* and, on the
fourth, *"No regressions in test 4"* — reading confirmed by the user before this
was written. So:

1. Jet Warrior Special Summoned by clause 2 is **BANISHED** when it leaves the
   field — the printed rider works.
2. Jet Warrior **Synchro Summoned normally** goes to the **GRAVEYARD** when it
   leaves — no rider. This is the decisive negative control: it proves the
   one-shot byte gates the attach, rather than the hook ridering every summon
   (the imprecision `rider.banish_marker_attach_site` warns about).
3. **Jet Synchron did not regress** — the lift of its hook into the shared module
   is transparent in play, including its own banish rider. The offline
   equivalence harness and the duel agree.
4. Clause 2's already-confirmed behaviour is intact on the new ROM — which
   matters because this build edited `_stub_c2_pos`, the Defense-Position stub
   itself.

⚠️ **CHAIN CONSEQUENCE.** `patch_jet_synchron` **is** in `apply_all_patches` and
`_verify_all_patches.SHIPPED`, and its hook now targets `CAVE_RIDERHOOK`, so the
`rom_all_patches.nds` built before 2026-09-07 is stale. Actioned below — see
**C26**.


---

### C26. ⛔ CHAIN BUILD BLOCKED — by `patch_card_art`, NOT by Jet Warrior

**2026-09-07, user: "Ship it".** The shipping edits are done and correct; the
chain build is blocked by a pre-existing, unrelated breakage.

**Shipped (one edit, per `otn-register-phantom-same-edit`):** `PatchStep`
"Ignition Beast Volcannon -> Jet Warrior (all clauses + rider)" at **index 48,
immediately after Jet Synchron** — mandatory, because the named-material row is
cid-keyed on `0x224C`; on an image where that cid is still Changer Synchron the
card summons off the wrong Tuner *while looking correct*. `patch_jet_warrior`
added to `_verify_all_patches.SHIPPED` in the same edit. 52 steps, WiFi timers
still last; `SHIPPED` = 43.

**THE BUILD DIED AT STEP 42/52, "Card art":**

```
FileNotFoundError: data\over_the_nexus\card_arts\gk_recruiter\gk_recruiter_64x64.png
  patch_card_art.py:204  _patch_card_pac  ->  Image.open(c.png("64x64"))
```

Steps 43-52 never ran — Jet Synchron (47), **Jet Warrior (48)** and the
WiFi-timers-last (52) are all absent from the artifact.

**⚠️ `BUILD_EXIT=0` WAS A LIE, AND FOR A NEW REASON — BANK THIS.** The command
was `... 2>&1 | tail -30; echo "BUILD_EXIT=$?"`, so `$?` is **`tail`'s** exit
status, never Python's; a pipeline always reports 0 here. `otn-chain-build-verify-
artifact` says exit 0 has lied twice before; this is a *third* mechanism, and a
purely self-inflicted one. **Never read an exit code through a pipe.** Redirect
to a file and check the real status, and assert the ARTIFACT regardless.

**What actually caught it** was the artifact assertion the KB mandates: on the
built ROM `cls2[643]` was still `0x23DE` (not `0x23EB`), the rider site
`0x02268666` still native `e089154e`, and named-material row 21 unmodified. The
file was 129,531,528 B and looked entirely plausible.

**THE CAUSE IS PRE-EXISTING AND UNRELATED.** `patch_card_art.py` and
`card_art_codec.py` were already modified in the working tree when this session
opened. Those edits un-comment several `CardArt` entries, and exactly **two** of
the 44 name directories that do not exist:

| entry | expects | on disk |
|---|---|---|
| `gk_recruiter` `0x1ED4` | `card_arts/gk_recruiter/gk_recruiter_{32x32,64x64}.png` | `card_arts/gravekeepers recruiter/Gravekeepers_Recruiter_*.png` |
| `infernity_barrier` `0x1DDD` | `card_arts/infernity_barrier/infernity_barrier_*.png` | `card_arts/infernity barrier/Infernity_Barrier_*.png` |

Every other entry resolves, **including `jet_warrior` `0x23EB`**, whose PNGs are
present — so Jet Warrior gets its artwork as soon as the chain runs.

**Artifacts left on disk, deliberately named so neither can be mistaken for a
build:**
- `rom_all_patches.BROKEN_42of52.nds` — the incomplete build, kept for evidence.
- `rom_all_patches.nds` — **RESTORED** to the last known-good chain build
  `520739ddb80a053c5c6edd0e411938b7147c3822f1889a919a04528dca13a60f`
  (2026-09-04, 51 steps, **no Jet Warrior**).

**Next step: the user chooses** how to fix the two art entries (re-point the code
at the space-named directories / rename the directories / re-comment the two
entries). Then re-run the chain **without a pipe**, and assert the real exit
status, 52/52, and the sha256 before calling it shipped.


---

### C27. ⛔ SECOND CHAIN BLOCKER — a ROW-INDEX anchor. The KB's own rule, ignored.

**Reported by the user 2026-09-07**, who ran the chain themselves:

```
AssertionError: cls1[1279] @0x0228D8BC holds cid 0x23FD,
                expected the donor 0x23EB -- refusing to patch a moved table
```

`otn-chain-build-verify-artifact` says **"Anchor chain preconditions on a CID,
never a row index."** `patch_jet_warrior` did the opposite: `CLS1_INDEX = 1279`
is the **stock** position, and an earlier chain step deletes a cls1 row above
ours, so on the chained image the donor sits at **1278**. The single-card build
could never see this — only `patch_jet_synchron` runs before it there.

**MEASURED — exactly ONE anchor drifted.** Compared every index the module pins,
stock vs. the 51-step chained image:

| anchor | stock | chain |
|---|---|---|
| **cls1 row** | **1279** `0x0228D8BC` | **1278 `0x0228D8A4`** ⛔ |
| fusion row 155 | `0x23EB` | `0x23EB` ok |
| GY-reg row 33 | phantom `0x209D` | phantom `0x209D` ok |
| SS-trigger row 30 | `0x23EB` | `0x23EB` ok |
| cls2 phantom `0x1655` | present, sorted, donor absent | same ok |
| namedmat phantom `0x2524` | present, sorted | same ok |

**THE FIX** — `cls1_addr(ov)` locates the row **by cid**, asserting exactly one
hit. Keep-cid means `+00` is the donor before *and* after the transplant, so the
lookup is stable and idempotent. `CLS1_INDEX`/`CLS1_ADDR` are kept, relabelled
"STOCK only", because the KB proof for `card.jet_warrior_clauses_0_and_1` pins
them. Resolves to `0x0228D8BC` on stock/single-card and `0x0228D8A4` on the
chain; single-card `verify()` still PASSES.

**THE CHECK THAT SHOULD HAVE EXISTED FIRST** —
`scratch/dryrun_chain.py`: runs all six ov3 appliers in `main()`'s order against
`rom_all_patches.PRE_JW.nds`, the exact image step 48 sees, **in memory in
seconds**. It reproduces this class of failure without a 25-minute build. All six
now pass. ⚠️ Do not extend it to a second pass over the same buffer:
`apply_clause23_records` rewrites cls1 `+0C/+10`, so re-running `apply_clause1`
afterwards correctly fails — an ordering `main()` never performs.
`patch_jet_warrior.main()` is not idempotent on its own output; nothing re-applies
it, so that is left alone deliberately.

**GENERALISE — and this is the reusable half.** A single-card test ROM cannot
prove a patch composes; it exercises exactly one predecessor. **Before wiring any
new card into `apply_all_patches`, dry-run its ov3 appliers against the current
chained image.** Two 25-minute builds were spent discovering, serially, two
blockers that this in-memory check finds in seconds.
