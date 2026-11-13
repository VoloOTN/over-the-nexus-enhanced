# Gladiator Beast Essedarii — findings

**Session start: 2026-08-03.** Target card text (source
`scratch/ygoprodeck_cache.json`, id **73285669** — NOT recalled; the ROM's own
`cards_text` descriptions are mistranslated and were not consulted):

> 2 "Gladiator Beast" monsters
> Must first be Special Summoned (from your Extra Deck) by shuffling the above
> cards you control into the Deck. (You do not use "Polymerization".)
> Fusion / Level 5 / EARTH / Beast / 2500 / 1400

Clauses — this is the **whole** card, it has no other effect:

1. materials = **2 "Gladiator Beast" monsters**
2. **contact fusion**: must first be SS'd from the Extra Deck by shuffling the
   materials you control into the Deck; no Polymerization

(⚠️ My own recall said Essedarii also has "cannot be destroyed by battle" and an
End-of-Battle-Phase tag-out. **Both wrong** — those belong to Nerokius /
Heraklinos and the Main-Deck GBs. The cache is the authority; this is exactly the
failure mode `otn-effect-text-db-untrustworthy` warns about.)

Essedarii is **not** in the OTN pool (0 hits over 4305 cards in
`scratch/cid_to_name.json`), so it needs the donor-card technique.

**Status: PARKED 2026-08-03, by user decision. No ROM was built for this card and
no patch module exists.** All the reverse-engineering below is done and proved;
resume at "Resume here" at the bottom.

Phase 0 (prove the ARM9 main-section cave, which was the only thing that could
have unlocked a Normal-Monster donor) was run and **FAILED**: the v2 canary boots
and runs the menus but **freezes on entering a duel** — see
`notes/ov3-cave-findings.md` → *Round 3b-v2 — PLAYED 2026-08-03*. So the donor
question is settled: **Armityle the Chaos Phantom `0x1CAE`, Phase 1A**, which
needs no cave at all and works in every duel mode.

---

## Confirmed (proved THIS session, static, on the committed oracles)

The engine KB had **no** Gladiator-Beast or summon-restriction facts before this
session. Everything below is a closed structural proof on
`ygo_tools/reference_files/{arm9,nds_overlay_3}.bin`.

### Clause 1 — material code 24 = "Gladiator Beast"

- The fusion material-code jump table `0x02231B54` (28 entries, codes 23–50,
  targets = `0x02231B56 + off`) routes **code 24** to leaf **`0x02231BA8`**:

  ```
  02231BA8  adds r0,r5,#0
  02231BAA  bl   0x02029E60      ; is-a-monster gate
  02231BAE  cmp  r0,#0
  02231BB0  bne  0x02231BB6
  02231BB2  cmp  r4,#4
  02231BB4  bgt  0x02231BC2
  02231BB6  adds r0,r7,#0        ; r7 = the candidate cid
  02231BB8  bl   0x02023AB0      ; <-- "Gladiator Beast" set-code thunk
  02231BBC  cmp  r0,#0
  02231BBE  beq  0x02231BC2
  02231BC0  b    0x02231DF4      ; accept
  ```

- **`0x02023AB0` is the "Gladiator Beast" set-code thunk**:
  `ldr r1,=0x0209CDF2 ; ldr r3,=0x02022E15 ; movs r2,#0x1d ; bx r3`
  — i.e. a u16 binary search over **29** entries at `0x0209CDF2`.
- **"Gladiator Beast" cid list `0x0209CDF2 … 0x0209CE2A`, 29 sorted u16.**
  Members are every GB card in the pool (Alexander `0x1C72` … Lanista `0x24DC`),
  and the **last entry `0x2521` is a PHANTOM** — absent from all 4305
  `card_prop` records, so it is a free slot for a count-neutral insert.
- Corroboration from the recipe table: all three shipped GB fusions use code 24 —
  `0x02270F84` Gaiodiaz `{0x1C73 Spartacus, 24}`,
  `0x02270F8C` Heraklinos `{0x1C76 Laquari, 24, 24}`,
  `0x02270FDC` Gyzarus `{0x1C75 Bestiari, 24}`.

⇒ **Clause 1 is a two-halfword edit**: the donor's table-A row becomes
`{donor_cid, 24, 24, 0x0000}`.

### Clause 2 — the summon-restriction classifier and the contact-fusion class

- **`0x02023228(cid)` classifies how a Fusion may be summoned.** It is five
  sorted-list searches (`0x02022E14`) in order, each returning a class code:

  | list | count | class | what the members are |
  |---|---|---|---|
  | `0x0209BCD4` | 0x26 = 38 | 1 | "Must be Fusion Summoned" (Polymerization): Flame Wingman, Dark Paladin, Cyberdark Dragon, Darkbright, Absolute Zero, … |
  | **`0x0209BB82`** | **0x15 = 21** | **4** | **contact fusion** — XYZ family, the ten Neos, GB Gaiodiaz/Heraklinos/Gyzarus, Armityle, Chimeratech Fortress |
  | `0x0209BA28` | 4 | 5 | Marine Dolphin, Twinkle Moss, Masked HERO Goka, Vapor |
  | `0x0209BA50` | 6 | 2 | the six Evil HERO (Dark Fusion) fusions |
  | `0x0209BA18` | 4 | 3 | `0x0EA1 0x0EA2 0x1C55 0x1C5F` — all four are phantom cids |
  | fallback | — | 4 or 0 | `0x02023050(cid)` = card type in {0xA,0xB} → 4 |

  Geometry of the class-4 list is pinned by the consumer's own immediates:
  base literal `0x0202329C` = `0x0209BB82`, count `movs r2,#0x15` @`0x02023240`,
  and it is strictly ascending `0x15B1 … 0x1DC1`.
- Wrapper `0x02023330(cid)` = "contact-or-ritual" (`0x02023050` OR class == 4);
  the fusion evaluator `0x0223298C` rejects a class-4 card for every summon mode
  except **4 and 5** (`cmp r4,#4 / cmp r4,#5` @`0x022329B6`), which is what stops
  a contact fusion being made with Polymerization.

⇒ **Clause 2 = membership of `0x0209BB82`.** ⚠️ That list has a hard-coded count,
**no phantom entry**, and abuts a different list at `0x0209BBAC`, so it cannot be
grown in place. **On today's proven ground the donor must already be one of the
21.**

### Fusion table A has 24 phantom rows (reusable, count-neutral)

24 of the 161 rows in table A (`0x02270B94`, 8 B/row) have a **result cid that is
not a card** in this ROM, so those rows are dead. A row can be re-keyed to any
cid inside its sorted interval without disturbing the binary search. Widest:

| row | addr | dead cid | free interval |
|---|---|---|---|
| 3 | `0x02270BAC` | `0x0ECB` | `(0x0EA2, 0x0FB5)` |
| 51 | `0x02270D2C` | `0x1269` | `(0x1225, 0x126F)` |
| 63 | `0x02270D8C` | `0x1508` | `(0x1507, 0x157D)` |
| 74 | `0x02270DE4` | `0x17F0` | `(0x17EF, 0x183C)` |
| 104 | `0x02270ED4` | `0x1A58` | `(0x1A53, 0x1A6D)` |

(Full list of 24 regenerable from the table + `cid_to_name.json`.)

### Donor survey — the 21 class-4 cids

| cids | family | real card sends materials to | cls records (all four tables) |
|---|---|---|---|
| `15B1 15B4 15F9 15FA 1953 1954` | XY / XYZ / XZ / YZ / VW / VWXYZ | banished | 1–2 each |
| `1A6D 1A6E 1A6F 1B4C 1B4D 1B4E 1C07 1C09 1C6B 1D12` | the ten Neos contact fusions | Deck, **but each self-bounces to the Extra Deck at the End Phase** | 1–3 each |
| `1C86 1C87 1DC1` | Gaiodiaz / Heraklinos / Gyzarus | Deck | real GBs — off limits |
| `1CEB` | Chimeratech Fortress Dragon | GY; special-cased in the fusion module (`0x02231D2C`, `0x02231E84`, `0x0223248C`) | none |
| **`1CAE`** | **Armityle the Chaos Phantom** | **Deck**, no End-Phase bounce | **NONE** |

⇒ **Armityle `0x1CAE` is the donor** unless Phase 0 unlocks something better.
`card_prop` record index **2528**: Level 12 / DARK / Fiend / 0 / 0 /
`Fusion Effect Monster`. Recipe row `0x02270F94` =
`{0x1CAE, 0x19A3 Uria, 0x19A4 Hamon, 0x19A5 Raviel}`.

Its stock clauses and where they live — **all five `0x1CAE` sites in overlay 3
were run down; only two need an edit**:

| stock clause | site | action |
|---|---|---|
| must be SS'd by its own procedure | class-4 list `0x0209BBA4` | **KEEP** — this *is* clause 2 |
| materials | recipe row `0x02270F94` | rewrite to `{0x1CAE, 24, 24, 0}` |
| cannot be destroyed by battle | `0x0226D26C` (33 sorted), Armityle at **index 20** = `0x0226D294`, neighbours `0x1C71` / `0x1CF1` | overwrite with phantom `0x1CB1` (free; preserves sort order) |
| gains 10000 ATK during your turn | stat-engine arm `0x021B5152` → leaf `0x021B5B06` | `bne` → `b` at `0x021B5156`: **2 bytes**, no phantom needed |
| — (cosmetic) | `0x0218E2AC`, `0x0218FDA4`, `0x0226C2FC` | **leave alone** — animation, not effect (see below) |

`0x1CB1` is confirmed absent from `cid_to_name.json` and unclaimed in
`PHANTOM_CLAIMS`.

### ⚠️ CORRECTION — the two ov3 `0x00001CAE` pool words are NOT the ATK gain

The plan's first draft said Armityle's +10000 lived in the literal-pool words
`0x0218E2AC` / `0x0218FDA4` and should be repointed at a phantom. **Wrong, and
doing it would have broken god-card summon cinematics for no benefit.**

- Both are **ARM-mode** literal pools (the surrounding words decode as `E5941C0C`,
  `E92D4078`, `E12FFF1E` …), which is why a Thumb-only `ldr [pc]` scan found *no*
  reference to either. The real loads are ARM: `0x0218DFB8`, and
  `0x0218FA64` / `0x0218FB30` (plus `0x0218F00C`/`0x0218F214`/`0x0218F480`).
- Their cid neighbourhoods are the god cards — Obelisk `0x1386`, Uria `0x19A3`,
  Armityle `0x1CAE`, Earthbound Immortals `0x1FEB`/`0x210C`, The Wicked
  Dreadroot `0x1905` / Avatar `0x1BB3` — and the arms assign small ids
  (`mov r1,#0x1c … #0x22`). This is the special-summon **animation / model**
  path.
- `0x0226C2FC` is the same family: a stride-4 `{cid, 0x0000}` table based at
  **`0x0226C248`** listing the game's cinematic boss monsters (Perfectly Ultimate
  Great Moth, Gate Guardian, Blue-Eyes Ultimate Dragon, the three Egyptian Gods,
  Exodia Necross, Ojama King, Five-Headed Dragon, …). Its only literal-pool
  references are `0x02144C10`, `0x021807F0`, `0x0218198C` — the same ARM region.
  Cosmetic; keeping it means Essedarii inherits Armityle's summon animation.

**Open Question 2 is therefore resolved: no edit needed at `0x0226C2FC`.**

### The +10000 ATK really lives in the continuous stat engine

`stat.recompute` predicted it and it holds. The constant 10000 occurs **exactly
once** in the whole `0x021B4000-0x021B8000` stat region, as the pool word
`[0x021B5E14] = 0x00002710`, loaded by one instruction:

```
021B5B06  ldr  r0,=0x0229DD14   ; turn-state struct
021B5B08  ldr  r1,[r0,#0x34]    ; whose turn it is
021B5B0A  ldr  r0,[sp,#0xc]     ; [sp+0xC] = side  (the stat.recompute frame)
021B5B0C  cmp  r1,r0
021B5B0E  bne  0x021B5B14
021B5B10  ldr  r0,=0x00002710   ; 10000
021B5B12  b    0x021B5B16
021B5B14  movs r0,#0
021B5B16  b    0x021B5722       ; -> the bonus tail
```

= "on its controller's turn the bonus is 10000, otherwise 0" — Armityle's text,
and the only card in the pool with it.

**Its arm, and the footgun.** The leaf has **exactly one** inbound edge in the
whole engine, `bl` @`0x021B5158`, from

```
021B5152  adds r0,#0x4c
021B5154  cmp  r2,r0
021B5156  bne  0x021B515C
021B5158  bl   0x021B5B06
021B515C  bl   0x021B5E6E      ; the non-match continuation
```

⚠️ Naively propagating `r0` forward from `0x021B5122` (`subs r0,#0x59`) gives
`0x1C03` Rainbow Dragon — **the `thumb.stack_based_switch` footgun exactly**.
That `subs` is on the `blt` subtree. The `bgt` at `0x021B510A` jumps to
`0x021B513E` with `r0` still holding the pivot literal
`[0x021B53A4] = 0x1C62` (Cloudian - Nimbusman), so on the path that actually
reaches this arm:

* `0x021B5140` → `r1 = 0x1C62 + 0x7E = 0x1CE0` **Exodius the Ultimate Forbidden
  Lord** → leaf `0x021B5B18`, which is `ldr r0,[sp,#0xc]; bl 0x021B1734` — a GY
  count, matching Exodius' "gains 1000 ATK for each monster with a different
  name in your GY". Independent corroboration that the base is right.
* `0x021B5152` → `r0 = 0x1C62 + 0x4C =` **`0x1CAE` Armityle** → leaf
  `0x021B5B06`. ✓

**The strip is 2 bytes:** `0x021B5156` `0xD101` (`bne +2`) → `0xE001` (`b +2`),
so the arm always falls through to the very `bl 0x021B5E6E` a non-match would
take. No literal pool touched, no phantom cid consumed, no other card's routing
changed, and the dead leaf stays in place. Current bytes confirmed:
`0x021B5152 = 0x304C`, `0x021B5154 = 0x4282`, `0x021B5156 = 0xD101`.

### Card-face measurements (from the ROM's own `bin2.pac`, not the stale reference file)

`"Gladiator Beast Essedarii"` = **25 B**. Armityle's per-language name slots:
`e` 26 · `f` 28 · `g` 25 · `i` 30 · `s` 30 · `j` 20 · `k` 17 · `r` 38 — fits
everywhere except **j / k**, which keep "Armityle" (cosmetic, JP/KR only).
Description slots are 304–530 B, so the ~155 B text fits in place in every
language.

---

## Ruled Out

- **A Normal Monster donor on today's proven ground.** It fails all three
  structural requirements: it is not in the Extra Deck (`card_type` — cheap to
  fix), owns no table-A row (fixable via a phantom row), and is **not in the
  class-4 list** (not fixable without 44 B of always-resident ARM9 space, which
  is exactly what Phase 0 is testing). The `otn-normal-donor-trampoline-method`
  recipe does not apply here — it needs a code chokepoint where a cid is live,
  and both of Essedarii's clauses are table membership, not code.
- **XZ-Tank Cannon `0x15F9` / the XYZ family as donor.** Smallest footprint of
  the 21, but the real card *banishes* its materials, so it only works if the
  material-payment path is class-generic — unproven (see below). Rejected in
  favour of a donor where the question cannot bite.
- **Chimeratech Fortress Dragon `0x1CEB`.** Records-free like Armityle, but it is
  special-cased inside the fusion module itself and its materials go to the GY.
  More baggage, no gain.
- **The ten Neos contact fusions.** All return materials to the Deck, but every
  one self-bounces to the Extra Deck at the End Phase — the same trap the Quasar
  work hit — and Marine Neos `0x1C07` carries that clause without a cls1 record,
  so it is not cleanly retirable.
- **Growing the class-4 list in place.** `0x0209BB82 + 21*2 = 0x0209BBAC`, which
  is the first entry (`0x1E12` Colossal Fighter) of the Assault-Mode pair list;
  the entry *below* the base is `0x2470` Yaksha, which would break the ascending
  order. Neither end can absorb a 22nd member.

---

## Open Questions

1. **Where does the engine actually send contact-fusion materials?** The class-4
   set mixes banish / Deck / GY in the real game, yet there is no per-cid
   discrimination: `0x15F9` occurs in ARM9 **only** at `0x0209BB86`, and `0x1DC1`
   only at `0x0209BBAA` / `0x0209CE1A`. So the payment is either class-generic or
   lives somewhere not yet found. Routed around by choosing a donor whose real
   card also returns materials to the Deck — but it must be **observed** in-game
   before the card is called done.
2. ~~What consumes the stride-4 table at `0x0226C2FC`?~~ **RESOLVED** — it is the
   cinematic boss-monster list based at `0x0226C248`, read from the ARM
   animation code. No edit needed.
3. **Is the ARM9 main-section cave real?** Phase 0.

---

## Resume here

Everything needed is pinned; a resuming session should go straight to writing
`ygo_tools/tools/finished_patches/patch_essedarii.py`, modelled on
`patch_escuridao.py`. Donor **Armityle the Chaos Phantom `0x1CAE`** (keep-cid).
Five edits, all count-neutral, no ov5 cave, no cls record, no registry row:

| part | site | edit |
|---|---|---|
| A — clause 1 | recipe row `0x02270F94` | `{0x1CAE, 0x19A3, 0x19A4, 0x19A5}` → `{0x1CAE, 24, 24, 0x0000}` (4 B) |
| — clause 2 | class-4 list `0x0209BBA4` | **nothing** — already a member |
| D — GB membership | set-code list `0x0209CDF2` (29) | insert `0x1CAE` between `0x1C8F` and `0x1CC5`, drop phantom `0x2521` off the end |
| S1 — strip battle immunity | `0x0226D26C` index 20 = `0x0226D294` | `0x1CAE` → phantom `0x1CB1` (2 B) |
| S2 — strip +10000 ATK | `0x021B5156` | `0xD101` (`bne +2`) → `0xE001` (`b +2`) (2 B) |
| B/C — card face | `bin2.pac` | `apply_stats_and_text(cid=0x1CAE, level=5, atk=2500, defense=1400, attribute="EARTH", race="Beast", name=b"Gladiator Beast Essedarii", desc=..., langs="efgisjkr")` |

`PHANTOM_CLAIMS` to add: `("gb_setcode_table", 0x2521, "essedarii")` and
`("indestructible_list", 0x1CB1, "essedarii")`. Register in
`apply_all_patches.PATCHES` above the WiFi-timers step. **Leave
`0x0218E2AC` / `0x0218FDA4` / `0x0226C2FC` alone** (animation, not effect).

The in-game oracle is unchanged — see the plan's Verification section; the one
that must be watched closely is **(b) the two materials are shuffled into the
Deck**, since `fusion.contact_material_destination` is still UNVERIFIED.

---

## Next Experiment (Phase 0 — RUN AND FAILED, kept for the record)

**Phase 0 — the ARM9 canary (needs the emulator; the ROM already exists).**
🔴 **Ran 2026-08-03: the canary freezes on entering a duel.** The steps below are
what was executed; the verdict and the bisect that would follow are in
`notes/ov3-cave-findings.md`. Do not re-run this as written.
`rom_arm9_canary.nds` (round 3b-v2, uncompressed) was built 2026-07-27 and
**never played** — there are no `rom_arm9_canary.ml*` states on disk.

```
.venv-1/Scripts/python.exe _build_arm9_canary.py          # expect 18/18 static PASS
# play, saving .ml1 normal .ml2 puzzle .ml3 turbo .ml4 tag .ml5 tag-turbo
#              .ml6 a NON-DUEL screen (deck editor / story map)
.venv-1/Scripts/python.exe -m otn_enhanced.tools.arm9_cave_check
```

| probe `0x020AD8E0` | region `[0x020AF120,0x020B7120)` | verdict |
|---|---|---|
| `0xA5` | `0xA5` | **PASS** — mode-independent cave is real |
| `0xA5` | wiped | still owned live; report the first reclaimed offset, do **not** work around |
| `0x00` | — | the grown ARM9 never reached RAM; region verdict void |

On a white-screen the next suspect is the `CE4`/`CE8` raise (they are
autoload-region pointers, not plain arena-lo): retest with those left at
`0x020AF120` and only `staticBssStart` raised. Report; do not retry blind.
