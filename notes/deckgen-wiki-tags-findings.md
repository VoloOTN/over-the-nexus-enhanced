# deckgen — wiki categories replace the derived tags (2026-07-30)

Task: `PROMPT_deckgen_wiki_tags.md`.  Live findings file; every fact below was
verified **this session** unless marked UNVERIFIED.

## Confirmed

### 0. The scrape is complete, and now fully auditable

`data/deckgen/wiki_categories.json`: **4,076 / 4,076 found, 0 missing**, 77
cards `found: True` with no categories (Normal Monsters — the correct answer),
**18** category groups (the prompt said 17; `Mentions`, 48 cards, is the extra
and carries no signal).

`python -m otn_enhanced.deckgen.wiki_categories --selftest` → 22/22.

23 rows resolved to a title different from the ROM's name; every one audits
clean.  The only one that needed checking beyond the table in the prompt was
`Falchion゚` → `Falchion`, which looks like a truncation: the wiki's `Falchion`
is a **redirect to `Falchionβ`** (`action=query&redirects=1`, checked live), so
the row is the right card.  4 pages carry a parenthetical and all 4 are
`(card)`, as the audit rule requires.

**Hole found and closed:** 806 rows — the most-played cards, fetched first —
predate the `page` field, so *which title answered* was unrecorded and a
wrong-card capture in that set would have been invisible.  Added
`wiki_categories.py --repage`, which re-fetches exactly those rows through the
current guarded resolver.

### 1. The mapping: `wikitags.py`

175→184 rules over `(group, value)` → tag, mapping the wiki's vocabulary onto
the model's existing 69-tag vocabulary so the diff below is meaningful.
`python -m otn_enhanced.deckgen.wikitags` self-tests three invariants:
no tag claimed by both the wiki table and `DERIVED_ONLY`, every regex compiles,
and **every rule matches at least one card in the scrape** (that last one caught
four rules pointing at the wrong group — a typo'd category name is otherwise
silent).

Three facts about the wiki's vocabulary that the mapping depends on, each
checked against samples rather than assumed:

* **Side is in the wording.**  `your` / `the player's` = the card's controller;
  `your opponent's` = the opponent; bare = both.  So "Prevents the player's
  Normal Summons" is Scapegoat and Stray Lambs — a **drawback** — and "Prevents
  your monsters from attacking" is Instant Fusion, not a floodgate.  Getting
  this backwards would have made 68 drawbacks look like floodgates.
* **A category is a fact, not a judgement.**  "Destroys your Monster Cards" is a
  cost; "Destroys your opponent's Monster Cards" is removal.  Never collapsed.
* **An empty block is an answer**, not a miss (the 77 vanillas).  `tags_for`
  returns `None` only when the cid is absent from the scrape entirely.

Wired into `text.parse.derive_tags` as `tags = (tags - AUTHORITATIVE) | wiki`,
after the regex rules and **before** the "if still untagged" fallback, so every
card still ends with at least one tag (**0 tagless**, re-checked).
`parse._MODULE_SOURCES` now hashes `wikitags.py` and the scrape, so editing
either invalidates the parse pickle.

Result: **69 → 79 distinct tags**, golden **20/20**.

### 2. The audit — where the regexes were wrong

Both taggers restricted to the 57 tags the wiki claims.  Counts are cards;
examples are ordered by era-corpus play count.

| tag | derived | wiki | agree | only-derived | only-wiki |
|---|---:|---:|---:|---:|---:|
| summoner | 740 | 686 | 597 | 143 | 89 |
| spot_removal | 392 | 746 | 340 | 52 | 406 |
| gy_payoff | 327 | 510 | 128 | 199 | 382 |
| recurring | 455 | 425 | 310 | 145 | 115 |
| floodgate | 404 | 218 | 112 | **292** | 106 |
| battle_payoff | 242 | 276 | 35 | 207 | 241 |
| recursion | 77 | 432 | 77 | **0** | **355** |
| free_body | 210 | 373 | 205 | 5 | 168 |
| burn | 165 | 308 | 164 | 1 | 144 |
| searcher | 252 | 151 | 144 | **108** | 7 |
| protection | 172 | 147 | 69 | 103 | 78 |
| conditional | 10 | 215 | 0 | 10 | 215 |
| tribute_cost | 47 | 251 | 24 | 23 | 227 |
| banish_cost | 19 | 165 | 3 | 16 | 162 |
| lp_cost | 18 | 157 | 16 | 2 | 141 |
| attack_lock | 9 | 142 | 2 | 7 | 140 |
| battle_immune | **0** | 122 | 0 | 0 | 122 |
| summon_payoff | 6 | 272 | 4 | 2 | 268 |
| leave_payoff | 3 | 92 | 2 | 1 | 90 |

The five findings that matter:

1. **`floodgate` had 292 false positives** — Sangan, Sirocco, Black Luster
   Soldier, Chaos Sorcerer, Blizzard the Far North.  The regex includes
   `cannot be (?:Special )?Summoned`, which fires on **every Nomi monster**.
   `power.tag_floodgate` ships at **2.20**, so a large chunk of the pool has
   been collecting a floodgate bonus for being hard to summon.  This is the
   single largest scoring error the audit found.
2. **`battle_immune` matched zero cards** — a dead coefficient.  The regex was
   always discarded by the "keep the broader tag" dedup against `protection`,
   because both patterns fire on the same sentence.  The wiki lists the two as
   separate entries (Attack categories vs Monster/Spell/Trap), so both survive:
   122 cards, led by Blackwing Armor Master (102 decks) and Spirit Reaper.
3. **`recursion` found 77 of 432** — a strict subset, 0 disagreements the other
   way.  Monster Reborn, Goyo Guardian, Scrap Dragon, Colossal Fighter and Call
   of the Haunted were all untagged.
4. **`searcher` had 108 false positives** — Archlord Kristya, Gold Sarcophagus,
   Salvage, Hero Blast.  The `search` verb does not distinguish "add from Deck"
   (a searcher, and what `searchability` / `deck.w_search_access` price) from
   "add from Graveyard", which is `recursion`.
5. **The fallback tags were placeholders.**  `tribute_cost` 47→251,
   `banish_cost` 19→165, `lp_cost` 18→157, `conditional` 10→215,
   `summon_payoff` 6→272, `leave_payoff` 3→92, `attack_lock` 9→142.  They only
   ever fired on cards where **nothing else** matched, so the model could not
   see that Solemn Judgment pays LP or that Stardust Dragon tributes itself.

Ten tags the engine had no way to derive at all:
`attack_trigger` 89, `self_damage` 86, `damage_block` 83, `attack_redirect` 72,
`random_outcome` 53 (coin/die — Arcana Force were priced as if the good half
always happens), `deck_stack` 44, `generic_nontuner` 40, `generic_tuner` 32,
`generic_material` 31, `extra_normal_summon` 7.

### 3. Where the wiki LOSES — three cases, all measured

The prompt says the wiki wins; these are the exceptions, and each is backed by
the diff rather than by preference.

* **`combat_trick` → derived only.**  Its nearest category, "Activates upon
  attack declaration", agrees with the regex on **zero cards**.  They are
  different facts: the category is Mirror Force and Dimensional Prison (a card
  that *answers* an attack), the regex is Honest and Kalut (a card in hand that
  *wins* the combat).  Honest's page carries no attack category at all.  The
  category now feeds a separate tag, `attack_trigger`.
* **`flip_effect` → additive.**  A FLIP monster is marked by its type line on
  the wiki, not by a category, so Ryko (69 decks) has no flip category.  The
  ROM text's `FLIP:` prefix is complete; the wiki's "Pseudo-Flip Effect"
  (Snowman Eater) is unioned in.
* **`summon_answer` → additive.**  Torrential Tribute's page lists exactly one
  category, "Destroys Monster Cards" — nothing records *when* it activates.
  Replacing would have lost the format's two best answers (Torrential 238
  decks, Bottomless 152).  Also corrected in the other direction: "Banishes
  negated Summons" is **not** a summon answer — it is Macro Cosmos and
  Dimensional Fissure catching a monster someone *else* negated.
* `summon_locked` stays derived on the standing rule that **in-game behaviour
  beats text** — the wiki's modern wording would re-lock Elemental HERO
  Mariner, which Instant Fusion can summon in this engine.

Full list with reasons: `wikitags.DERIVED_ONLY`.

### 4. `Supports: <Type/Attribute>` → wants

550 cards support a Type and 252 an Attribute; only 122 of the Type supports
were already visible as a text want, so **641 cards gained a want they never
had** (total wants 1,708 → 2,375).  This is the gap named last session and not
buildable from text: nothing stopped The Sanctuary in the Sky going in a Dragon
deck or Super Rejuvenation in a Fairy deck.

**One want per axis, not one per value.**  Forest supports Insect, Beast,
Beast-Warrior and Plant; four wants would leave a Plant deck orphaning three of
them and paying for a card doing its job.  A `race` set is a disjunction in
`Predicate.matches`, so it becomes one "any of these" want — the same treatment
`split_conjunctions` already gives a genuine "LIGHT or DARK".  Weight 0.5, the
non-search want weight; the orphan penalty then scales by exclusivity, so
supporting 72 Plants costs more than supporting 352 Warriors.

### 5. `w_extra_generic` — implemented off the wiki, and the measurement
### disagrees with the prompt

`wikitags.material_genericity` reads the material line directly, graded
1.0 / 0.5 / 0.0 (fully generic / generic in one half / restricted), replacing
"does any parsed want carry an archetype or a card name".  The inferred test
read the **whole card**: Scrap Dragon (179 era decks) counted as locked because
its *effect* names an archetype though its material line is the fully generic
"1 Tuner + 1 or more non-Tuner monsters", and Blackwing Armor Master counted as
free though its non-Tuners must be Blackwings.

**But on the obvious objective the old proxy wins.**  Played vs unplayed Extra
Deck cards, era corpus (105 played / 182 not):

| test | AUC |
|---|---|
| inferred boolean (ships today) | **0.709** |
| graded wiki genericity (applied) | 0.686 |
| "Does not require specific Synchro Materials" alone, as the prompt specified | 0.588 |

Applied anyway, and this is the reasoning: an archetype-locked Synchro **is**
played — inside its own archetype — so "does the era play it" rewards the proxy
for smuggling in a fact that the orphan/want channel already prices.  Keeping
the proxy here double-counts the lock.  The strict form the prompt named (the
single "Does not require specific Synchro Materials" category) is much worse
than either, because it calls Goyo Guardian and every Blackwing Synchro fully
locked; the graded form is what makes the wiki fact usable.

### 6. The refit — evidence off, era corpus, 5 seeds × 2 rounds

`deckgen train --no-evidence` (new flag; the previous session had to hand-roll
this).  Held-out gain **+0.0363 ± 0.0073, 5/5 positive** — indistinguishable
from last session's +0.0357 ± 0.0063, on populations that have changed a lot.

| coefficient | shipped | fit | seeds |
|---|---:|---:|---|
| `power.tag_opponent_turn` | 0.00 | **+1.20** | 5/5 |
| `power.tag_free_body` | 0.00 | **+1.20** | 5/5 |
| `power.w_extra_generic` | 1.20 | **+2.00** | 5/5 |
| `gain.negate` | 0.70 | **+1.10** | 5/5 |
| `power.tag_floodgate` | 2.20 | **+0.50** | 4/5 |
| `power.tag_spot_removal` | 0.00 | **+0.90** | 4/5 |
| `power.tag_summon_answer` | 0.00 | +1.50 | 3/5 |
| `power.tag_recurring` | 0.00 | +1.20 | 3/5 |
| `power.tag_banish_payoff` | 0.00 | +0.70 | 3/5 |
| `gain.negate_destroy` | 1.00 | +1.30 | 4/5 — **rejected, see below** |

The three new wiki-only coefficients were offered with 0.0 in the grid and the
fit **rejected all three**: `tag_damage_block` 0.00 (5/5), `tag_self_damage`
0.00 (5/5), `tag_random_outcome` 0.00 (4/5).  They stay as description.

**`gain.negate_destroy` 1.00 → 1.30 breaks golden** — Solemn Judgment stops
reading as a 1-for-1 (`exp` +0.00 → +0.30).  Isolated to that one coefficient:
the eight `power.*` values and `gain.negate` 1.10 all pass 20/20.  Same value
the previous session's evidence-off fit wanted and never applied; the guard has
been doing its job.

#### Confirmed on splits the fit never used

The fit splits the era corpus at random, once per seed, so all five seeds share
one *kind* of split.  Re-measured with the nine golden-safe values on splits
built differently — by format, and on a corpus the fit never touched:

| check | shipped | fitted | Δ |
|---|---:|---:|---:|
| era, evidence OFF, held formats Crow+Edison | +0.2399 | +0.2676 | **+0.0278** |
| era, evidence OFF, held formats Tengu+Trishula | +0.2567 | +0.2819 | **+0.0252** |
| all ~100 formats, evidence OFF (fit never saw this corpus) | +0.1946 | +0.2071 | **+0.0125** |
| era, evidence **ON** — the shipping configuration | +0.7756 | +0.7776 | +0.0021 |
| deck AUC, random split | +0.9564 | +0.9575 | +0.0010 |
| deck AUC, **by-format** split | +0.8743 | +0.8756 | +0.0013 |

**Positive on every one**, including the two the fit could not have seen.

**This is new evidence on the standing open decision.**  The reason these values
were left at 0.00 last session was the fear that applying evidence-off values
while shipping with evidence ON would double-count.  Measured directly, in that
exact configuration: **+0.0021 Spearman and +0.0010 / +0.0013 deck AUC — small,
but positive on both splits, not a regression.**  The double-count is real in
principle and is not costing anything in practice.

### 7. What the tagging change alone did, before any refit

At **unchanged** params.toml, so this isolates the tags/wants from the
coefficients:

| metric | before | after | Δ |
|---|---:|---:|---:|
| Spearman era, evidence OFF | +0.2705 | +0.2651 | **−0.0054** |
| Spearman all-format, evidence OFF | +0.1964 | +0.1946 | −0.0018 |
| Spearman era, evidence ON | +0.7744 | +0.7756 | +0.0012 |
| deck AUC, random split | 0.9530 | **0.9564** | +0.0034 |
| deck AUC, by-format split | 0.8684 | **0.8743** | +0.0059 |
| distinct tags / wants | 69 / 1708 | 79 / 2375 | |

The card-level dip is expected and is **not** a defect in the tags: every
coefficient in params.toml was fitted against the old populations, and the
largest of them, `tag_floodgate` at 2.20, was tuned on 404 "floodgates" of which
292 were Nomi monsters.  Paying 2.20 to a now-correct 218-card set is a
different model.  After the refit the same metric goes to +0.2676 / +0.2819 on
the two format splits (from +0.2399 / +0.2567).

## 8. Decklist scrape expanded to every entry, 66 retro formats (user request)

The corpus was built from `placement in (1, 2)` capped at 150 per format.  Both
limits were losing data — the cap alone was cutting off **328 first-place
decks**.

- `tournament.ERA_FORMATS` replaced with the user's list: `ERA_FORMATS_TCG` (36)
  + `ERA_FORMATS_OCG` (30).  **All 66 verified against the API's own
  `/api/formats`** (122 canonical names) — a renamed format fails silently, it
  just selects nothing, so `report --check-formats` now checks.
- `fetch_decks` takes `placements=None` (every entry) and `per_format=None` (no
  cap), plus a `formats=` filter; CLI `--all-placements`, `--era-only`,
  `--per-format 0`, `--refresh-index`.  Defaults unchanged, so the old
  behaviour is still reproducible.
- Sort is now `(not era, format, placement)`, so an interrupted run holds each
  format's best finishes rather than a random slice.
- Index refreshed: 12,903 → 12,917.

**15 of the 30 OCG formats have zero decks indexed** (Mirror, Snake, Makyura,
Demon, Goblin, Envoy, Catapult, Dark Cat, OCG TeleDAD, Dark Strike, Lightlord,
Infernity, OCG Treasure, OCG Imperial, plus one more).  They are real formats,
not typos — formatlibrary's OCG coverage is simply thin: of the 30, Crow (110)
is the largest and most have 1-8 lists.

### Result of the fetch

**2,518 → 8,667 decklists.**  11 lost to persistent HTTP 500s on
formatlibrary's side (0.18%; the client already retries 5xx three times).
7,646 rows are in the 66 retro formats and **7,225 map >= 75% onto the ROM
pool**.  Placements now run to 33rd, where the corpus previously held only 1st
and 2nd.

The training corpus (`mining.era_decks`, Tengu/Edison/Crow/Trishula) went
**348 → 2,060 decks, 5.9x**: Edison 150→1,301, Tengu 124→464, Crow 43→110,
Trishula 31→185.

### Every applied coefficient survives 5.9x the data

Re-ran `train --no-evidence` from the values applied earlier this session.
**All nine came back 5/5, unchanged** — `tag_floodgate` 0.50, `tag_free_body`
1.20, `tag_opponent_turn` 1.20, `tag_recurring` 1.20, `tag_spot_removal` 0.90,
`tag_summon_answer` 1.50, `tag_banish_payoff` 0.70, `w_extra_generic` 2.00,
`gain.negate` 1.10.  Held-out gain is now **+0.0017 ± 0.0014**, i.e. the fit is
converged and there is nothing left to extract.  The three wiki-only
coefficients stayed rejected at 0.00 (5/5).

This is the strongest available answer to the prompt's warning that "a unanimous
5/5 reversed under a different corpus": the corpus grew six-fold and nothing
moved.

**`gain.negate_destroy` 1.00 → 1.30 now reaches 4/5 on the larger corpus too**,
and golden still rejects it (Solemn Judgment `exp` +0.00 → +0.30).  Third fit in
a row to want it.  Either the coefficient is right and the golden assertion is
wrong about Solemn Judgment, or economy is double-counting the destroy — worth
resolving deliberately rather than by suppressing it a third time.
`gain.spin_opp` 0.55 → 1.20 appeared at 3/5, too weak to act on.

### Placement does not matter; being a tournament result does

Deck-level AUC against the ROM's 222 AI decks, split by finishing position:

| placement | decks | deck AUC |
|---|---:|---:|
| 1st | 207 | 0.9546 |
| 2nd | 217 | 0.9566 |
| 3rd-4th | 380 | 0.9489 |
| 5th-8th | 367 | 0.9536 |
| 9th+ | 371 | 0.9509 |
| **unplaced** | 40 | **0.8759** |

A 9th-place list is as distinguishable from a ROM AI deck as a 1st-place list —
the spread across real placements is 0.004, inside noise.  **Fetching every
entry was the right call**, and the old top-2 filter was discarding 5.9x the
data for nothing.

The outlier is real and has a clean cause: those rows are `origin: "user"` —
someone's submitted list, no event, no placement.  The field is perfectly
separable (12,721 `event` rows all carry a placement; all 196 `user` rows carry
none), so `map_to_pool` now drops them, and `fetch_decks` records `origin` for
future rows.  Era corpus 2,109 → **2,060**.

### Coverage is not legality — and the current corpus is not clean either

`MIN_COVERAGE` asks whether a deck's cards **exist** in the ROM.  It does not
ask whether you could play the deck, and the ROM's default Forbidden/Limited
list is **2010.09**.  Measured against `Limits.named("limit201009")` over all
7,100 usable retro decks:

| format | decks | avg coverage | decks with NO Forbidden card | avg Forbidden | avg over-limit |
|---|---:|---:|---:|---:|---:|
| Goat | 2008 | 99.7% | **0.0%** | 13.66 | 2.88 |
| Edison | 1301 | 100.0% | 3.8% | 2.30 | 0.26 |
| Tengu | 464 | 84.0% | 9.5% | 1.48 | 0.92 |
| Perfect Circle | 241 | 99.7% | 3.3% | 3.67 | 2.82 |
| Reaper | 208 | 99.5% | 0.0% | 6.75 | 2.17 |
| Trishula | 185 | 95.9% | **100%** | 0.00 | 0.36 |
| Chaos | 79 | 97.4% | 0.0% | 21.87 | 1.97 |
| Crow | 110 | 100.0% | **100%** | 0.00 | 0.00 |
| **all 7,100** | | 97.8% | **10.1%** | 7.36 | 2.21 |

Also 100% Forbidden-free: **X-Saber** (129), **Starstrike** (68), **Nexus** (77).
Those five — Trishula, Crow, X-Saber, Starstrike, Nexus — are the formats whose
banlist actually resembles this ROM's.

A Goat deck maps at 99.7% and is built around ~14 cards this ROM Forbids.  This
is the quantified form of the previous session's note, and it applies to the
corpus already in use: **only 18.9% of the 2,060-deck era corpus is free of
Forbidden cards** (it was 26.1% at 348 decks — the added lower placements are
slightly worse, being mostly Edison).

Split deliberately into two measures, because only one is fatal: a deck running
3 Pot of Duality where the ROM allows 1 still says Duality is good (over-limit);
a deck built around Pot of Greed is evidence about a card that can never be
played here (Forbidden).

### Which of the 7,100 decks should actually TRAIN the model — measured

Having the data does not mean training on it.  Five candidate corpus
definitions, each fitted evidence-off (3 seeds x 2 rounds) and scored on **one
fixed evaluation set**: 228 held-out decks from Tengu / Trishula / Crow (the
formats closest to the ROM), whose deck ids were removed from every candidate so
none can train on what it is scored against.

| candidate | decks | Forbidden/deck | Spearman | deck AUC |
|---|---:|---:|---:|---:|
| shipped params, no refit | — | — | +0.2287 | 0.7371 |
| A  current 4 formats, top-2 only | 501 | 1.93 | +0.2350 | 0.7566 |
| B  current 4 formats, **all placements** | 1881 | 1.88 | **+0.2363** | **0.7573** |
| C  2010-2011 formats, all placements | 2421 | 1.68 | **+0.2363** | **0.7573** |
| D  **all 66 retro formats** | 6918 | 7.58 | +0.2299 | 0.7372 |
| E  all 66, minus any deck with a Forbidden card | 620 | 0.00 | +0.2350 | 0.7566 |

(These AUCs are not comparable to the 0.95 figures elsewhere in this file: the
positives here are only the 228 held-out decks and the params run evidence-off
with `play_rate={}`.  Only the column is comparable, not the level.)

Four things fall out, and one of them is a genuine warning:

1. **Training on all 66 formats is the WORST option** — +0.2299 / 0.7372, barely
   distinguishable from not refitting at all, and it moved nothing but a junk
   `tag_nomi`.  Goat alone is 2,008 of those decks at ~14 Forbidden cards each.
   **More data from the wrong era is worse than less data from the right one**,
   and the effect is large (−0.0064 Spearman, −0.020 AUC against B) rather than
   marginal.  `mining.ERA_FORMATS` should stay as it is.
2. **All placements beats top-2** (B over A): +0.2363 vs +0.2350, 0.7573 vs
   0.7566.  Small, but consistent across both metrics and off 3.75x the decks —
   the expansion is a real if modest win, and it is already in effect.
3. **Widening from 4 formats to the whole 2010-2011 window buys nothing** (C is
   identical to B to four decimals).  The extra 540 Lightsworn / Frog / X-Saber
   / Starstrike / Nexus decks carry no signal Tengu/Edison/Crow/Trishula lacks.
4. **Legality filtering is not a win on its own** (E ≈ A): 620 perfectly legal
   decks land exactly where 501 top-2 era decks do.  Era-appropriateness matters
   more than strict legality — which is why D fails, not because Goat decks are
   illegal but because they are a different game.

Caveat: one evaluation split, one shuffle seed.  The D result is large enough to
act on; the A-vs-B gap is not, on its own — it is reported as directional.

Every candidate that improved at all chose `gain.negate_destroy` 1.30.  That is
now the **fourth** independent fit to want it.

### Checked and NOT a problem: name matching

The 315 distinct unmapped card names are dominated by cards genuinely absent
from the ROM — Number 39: Utopia (207), Leviair (202), Tour Guide (179), Maxx
"C" (147), Reborn Tengu, T.G. Hyper Librarian.  Spot-checked twelve of the
suspicious-looking older names (Roaring Ocean Snake, Metal Dragon, Empress
Judge, Sanwitch, Skull Knight, Punished Eagle, Super Roboyarou/Robolady, Orient
Dragon): **every one is absent from the ROM**, not a `namematch` miss.  The
mapping layer is sound and needs no work.

## 9. `gain.negate_destroy` released — and the golden assertion was hiding a bug

User's call, and their reasoning is the right one: negating stops the effect
from ever resolving, which beats removing the same card later, most of all
against a boss monster or a high-impact spell.  Four fits had already asked for
1.30 and been blocked each time by golden.toml asserting Solemn Judgment at
exactly 0.00.

**The assertion was encoding a coincidence, not a mechanism.**  `explain`
showed why:

```
economy +0.00 cards
    self_spend[counter_trap]   -1.000
    gain.negate_destroy x1     +1.000
```

"Pay half your LP" appears nowhere.  The `pay_lp` clause rule is
`\bpay ([\d,]+) (?:LP|Life Points)` — it wants literal digits, so "pay **half**
your LP" matched nothing and **eight cards paid that cost for free**: Solemn
Judgment, Return from the Different Dimension, A Hero Lives, Gandora, Vanity's
Call, Malefic Truth Dragon, Steelswarm Hercules, Dark Magic Curtain.

So 0.00 was an underpriced negate+destroy cancelling an unpriced cost.  Both
fixed: `clauses.HALF_LP = 4000` (half the starting total, documented as an upper
bound) and the coefficient at 1.30.  Solemn Judgment is now
−1.00 − 0.80 + 1.30 = **−0.50**, and the golden assertion was rewritten to state
the mechanism.  Not a downgrade of the card — it still ranks **11th of 4,076**
and appears in **67%** of the era corpus; its value lives in power
(`summon_answer`, `opponent_turn`), not in card advantage.

A/B on one fixed corpus (2,060 decks, one sample, one split):

| arm | era Sp | all-format Sp | deck AUC | SJ econ | SJ rank |
|---|---:|---:|---:|---:|---:|
| base | +0.2907 | +0.2033 | 0.9521 | −0.00 | 9 |
| + half-LP cost only | +0.2893 | +0.2028 | 0.9517 | −0.80 | 12 |
| + coefficient 1.30 only | **+0.2918** | **+0.2037** | **0.9524** | +0.30 | 9 |
| both (applied) | +0.2907 | +0.2034 | 0.9518 | −0.50 | 10 |

**Stated honestly: the coefficient alone is the best arm, and adding the LP cost
gives most of that back.**  Every delta here is ≤0.0015 — noise on one split.
The cost is kept anyway because it is a *correctness* fix: a cost written on the
card was priced at zero, and this repo's economy is defined as cards of
advantage with golden.toml existing to lock mechanisms.  Buying 0.001 of
Spearman by continuing not to charge half a life total would be the wrong trade.

Refit afterwards: `gain.negate_destroy` **5/5 at 1.30** — settled.

## 10. `gain.spin_opp` 0.55 → 1.20, surfaced by fixing the above

With negate_destroy no longer absorbing the variance, `spin_opp` went from 3/5
to **5/5**.  The shipped 0.55 was **equal to `bounce_opp`**, contradicting the
comment directly above it ("spin ... beats a bounce").  1.20 sits just over
`destroy_opp` (1.00), which is the shape the reasoning implies.

Only 4 cards carry it, 2 of them played — Phoenix Wing Wind Blast (14% of the
era corpus) and Raiza (8%) — so a 5-seed consensus is thin on its own.  Checked
on splits the fit never saw:

| check | 0.55 | 1.20 | Δ |
|---|---:|---:|---:|
| era, held formats Crow+Edison | +0.2408 | +0.2422 | +0.0014 |
| era, held formats Tengu+Trishula | +0.2625 | +0.2637 | +0.0012 |
| all ~100 formats | +0.2034 | +0.2041 | +0.0007 |
| era, evidence ON | +0.6302 | +0.6302 | +0.0000 |
| deck AUC, random split | +0.9517 | +0.9518 | +0.0002 |
| deck AUC, by-format split | +0.8636 | +0.8641 | +0.0006 |

Never negative, all tiny.  Applied; golden 20/20.

## 11. The deck-level fit, and the p_orphan confound measured at last

`train-deck`, 5 seeds x 2 rounds, on the 2,060-deck corpus with the new support
wants.  Headline: **held-out AUC gain +0.1089 ± 0.0111, 5/5 positive** — and it
**does not transfer**.  On a by-format split the same 12 coefficients are
**−0.0162**.  The fit splits the corpus at random, which puts decks from the
same event on both sides; splitting by format removes that and the gain
evaporates.

Three instruments were used, and the third is the point:

* **A** — vs ROM AI decks, by-format split.  The fit's own objective, harder split.
* **B** — does a top-2 deck outscore a 9th+ deck?  **No ROM decks involved**, so
  the "themed pile vs goodstuff" confound cannot reach it.
* **C** — the card model, evidence off.  A deck weight should not touch it.

| subset | A | B | C |
|---|---:|---:|---:|
| all 12 | −0.0162 | +0.0072 | +0.0432 |
| deck-level 6 | +0.0101 | −0.0028 | 0.0000 |
| ↳ minus `p_orphan`/`p_role_balance` | +0.0022 | −0.0010 | 0.0000 |
| ↳ **only `p_orphan` + `p_role_balance`** | **+0.0078** | **−0.0024** | 0.0000 |
| card-level 6 | −0.0401 | +0.0199 | +0.0432 |

**`deck.p_orphan` 3.00 → 1.00 was rejected despite 5/5 seeds.**  It and
`p_role_balance` supply +0.0078 of the deck half's +0.0101 gain, and on the
instrument free of the confound they are **negative**.  Konami's AI decks are
mono-archetype and orphan few wants; a goodstuff tournament deck orphans many —
so this objective pays to switch the orphan penalty off whether or not that is
correct.  The previous session recorded this as a suspicion ("do not write them
on the strength of this AUC alone"); it is now a measurement.  Recorded in
params.toml next to the coefficient.

**Applied** (both non-confounded, both ≥4/5, golden 20/20):
`deck.w_deckout` 6.00 → 0.00 (fired on 4 of 250 decks) and
`deck.w_search_access` 3.00 → 6.00 — the one the previous session explicitly
deferred to a multi-seed run.

**Not applied, referred to the user:** the card-level six, dominated by
`impact.w_power` 0.10 → **1.10** and `impact.w_evidence` 2.40 → **0.50**.  It is
a straight trade — −0.0401 at separating tournament decks from ROM AI decks
(from a high base), against +0.0199 at separating good tournament decks from
worse ones (from near-chance 0.514) and +0.0432 on the card model's reasoning.
Less lookup, more reasoning.  B is a weak instrument so +0.0199 is ~1 SE.

Also of note: the corpus expansion **stabilised** three weights the previous
session feared were confounded — `w_archetype` (5/5 on 2.00), `w_want_scale`
(3/5 on 4.00) and `w_tuner_reach` (4/5 on 1.50) all declined to collapse this
time.

## 12. A corpus leak that survived randomisation, in two places

`search._mined_playsets` has always dropped its per-cid evidence after a
randomiser run — its comment: *"after a randomiser run it says nothing about the
one that does now"*.  But `synchro_level_value` was fed per-cid play rate
**unconditionally**, in both `search._level_value` and `score.score_pool`, so a
randomised pool kept rating Level 8 highly because Stardust Dragon *used* to be
there.  `power.tuner_value` is built from it.

Fixed, and the duplicated `altered` test (three copies, one missing) factored
into `cardpool.is_randomised`.  Inert on the stock pool (0/2478 stat conflicts),
golden 20/20.

## 13. Two profiles: `[profile.randomised]`

`Params.with_profile(name)` applies a sparse dotted override block;
`score_pool` resolves it whenever the pool is randomised, and
`score_pool(simulate_randomised=True)` forces the branch so the profile can be
fitted without a randomised ROM to hand.

Why it is needed, measured on the era corpus:

| feature set | Spearman |
|---|---:|
| per-cid play rate (stock ROM) | +0.6302 |
| **per-tag rates (randomiser fallback)** | **+0.4988** |
| no evidence at all | +0.2919 |

The fallback keeps far more than expected — and the tags carrying it are the
ones added this session: `generic_material` **0.247**, `summon_answer` 0.062,
`generic_nontuner` 0.046, `opponent_turn` 0.036.  The wiki tagging matters most
exactly where the per-cid lookup dies.  Until now that fallback was read through
coefficients fitted for the per-cid feature.

## 14. Two parser bugs, found by asking why the reasoning channel is weak

The diagnosis that mattered: **evidence is not redundant with reasoning — it is
orthogonal to it.**  Spearman(evidence rank, reasoning rank) over the 876
era-played cards = **−0.014**; against economy alone −0.026, against power alone
**+0.046**.  So `w_power` cannot substitute for `w_evidence`: power predicts
actual play at essentially zero.

Which meant the reasoning channel was ranking the format's best cards in its
bottom decile — Book of Moon (722 decks) at **831/876**, Trap Dustshoot (1472)
at 762, Brain Control (1020) at 758, Icarus Attack (319) at 817.  Chasing that
found two real defects:

1. **Anaphors did not inherit their antecedent's count.**  "Target 2 cards on
   the field; destroy **them**" bound the predicate, zone and side but kept
   `destroy`'s default count of 1, so Icarus Attack priced as a 1-for-2.
   **55 cards** affected, led by Mist Wurm (573 decks), Blackwing - Silverwind
   (533), Starlight Road (340), Gyzarus, Celestia, Treacherous Trap Hole,
   Mobius.  Guarded twice: only when the anaphor took the default count, and
   only when its own text states no number.
2. **"Tribute this card to destroy …" captured the whole sentence as the
   tribute's target.**  The phrase was then not a SELF_WORD, so the clause lost
   `self_ref`, kept a bogus predicate, and `_side_of` read the trailing "your
   opponent" and scored a self-cost as **+0.95 of `gain.opp_tribute`**.  Turbo
   Booster: +2.04 economy, 2 era decks, reasoning rank 23.

**Ruled out on the way:** fixing (2) by stopping the target capture at every
" to ".  It truncates target phrases that legitimately continue — **−85 wants,
−0.006 Spearman**.  Reverted for a narrow `_LEADING_SELF` trim; the reason is in
the `_STOP` comment so it is not retried.

Net against the start of this stretch: era reasoning **+0.2919 → +0.2973**,
all-format **+0.2041 → +0.2070**, deck AUC by-format **0.8641 → 0.8668**,
evidence-on unchanged.  Golden 20/20.  Icarus Attack's economy rank 829 → 542.

## 15. `--use-evidence`, and the randomised profile fitted

`score_pool(use_evidence=...)` replaces the earlier `simulate_randomised`, so
there is one switch rather than two overlapping ones.  `None` auto-detects;
`deckgen {gen,explain,top,partners,seeds} --no-use-evidence` forces the
randomised mode on a stock ROM, which is both how the profile is fitted and how
to build a deck that does not lean on knowing which cid was a staple.

**`[profile.randomised]` fitted leave-one-format-out** — fit on three era
formats, test on the fourth, tag-rate feature mined from a disjoint quarter of
the fitting formats only, so the test format takes no part in fitting, feature
mining or selection:

| held-out | stock | profile | Δ |
|---|---:|---:|---:|
| Crow | +0.3548 | +0.3927 | +0.0378 |
| Edison | +0.3049 | +0.3301 | +0.0252 |
| Tengu | +0.3416 | +0.3648 | +0.0232 |
| Trishula | +0.3118 | +0.3510 | +0.0392 |
| **mean** | +0.3283 | **+0.3597** | **+0.0314** |

**4/4 folds agreed on all three values and every fold improved.**
`power.w_staple` 8.00 → 5.00, `impact.w_power` 0.10 → 0.80, `power.w_stat`
0.30 → 0.10.  Trust the weaker fallback feature less; make reasoning carry more.

Note **0.80, not the 1.10** the deck fit wanted for the stock path: every
`power.tag_*` weight was fitted at `w_power` 0.10, so raising it multiplies all
of them at once.  At 1.10 the generated deck lost Icarus Attack and filled with
Gravity Collapse / Mirror of Oaths / Solemn Warning 3-ofs — the tags this
session raised, amplified 11×.  At 0.80 with the parser fixes in, the Blackwing
engine and the trap suite both survive and Icarus Attack returns at 3 copies.

Caveat worth carrying forward: the randomised build still takes off-theme
Level 1-3 Tuners (Dragunity Darkspear, Scrap Hunter, Dark Bug) as Synchro
reach.  Defensible, not obviously right.

### …and the tag weights refit at the profile's own scale

The profile's three values were fitted with the tags held at their stock
numbers, which left the defect the profile exists to fix half-open: every
`power.tag_*` was fitted at `w_power` 0.10 and the profile runs them at 0.80,
multiplying all of them by eight.  Refit leave-one-format-out on top of the
profile.  **All four folds positive** — Crow +0.0030, Edison +0.0105, Tengu
+0.0052, Trishula +0.0022, mean +0.3597 → **+0.3649**.

Five reached ≥3 of 4 folds and were written: `tag_nomi` −0.90 → −1.60,
`tag_lifegain` 0.00 → −0.30, `tag_random_outcome` 0.00 → −0.70,
`tag_atk_scaling` 0.55 → 0.00, `tag_hand_disruption` 0.00 → 1.20.
`tag_spot_removal` split 2/4 and was left alone.

The two worth understanding rather than just recording:

* **`random_outcome` −0.70.**  The card-level fit rejected it at 0.00 five
  times — correctly, because with the lookup on, the model already knew Arcana
  Force and Barrel Dragon are unplayed.  Take the lookup away and the coin-flip
  unreliability has to be priced directly.  A tag can be worth nothing in one
  mode and real in the other; that is the whole argument for having two.
* **`tag_nomi` −1.60**, harsher, for the same reason: without knowing *which*
  Nomi monsters turned out playable, the drawback is worth more.

### Which wiki tags are actually consumed

**21 of the 59 are read by nothing.**  Three groups:

* Redundant labels — `tribute_cost`, `banish_cost`, `lp_cost` are already priced
  by economy through their clauses.
* Read via a function, not the tag — `generic_material` / `generic_tuner` /
  `generic_nontuner` look dead but `power.w_extra_generic` calls
  `wikitags.material_genericity()` directly.
* Genuinely unused signal — `summon_payoff` (272 cards), `conditional` (221),
  `attack_lock` (143), `leave_payoff` (92), `attack_trigger` (89),
  `extra_normal_summon` (7), plus `stat_boost`, `equip_effect`, `name_change`,
  `level_mod`, `deck_stack`, `information`, `fusion_payoff`,
  `continuous_effect`, `attack_redirect`.

The last group has never been offered to a fit.  `attack_lock` and `conditional`
are the two that look most like real drawbacks with nothing charging them.

## 16. The evidence lookup is now OFF by default (user play-testing)

The user built decks in both modes and preferred every no-evidence one: with
the lookup on, "all the decks converge onto 3 Ryko and 3 Caius and the seed gets
lost".  CLI default flipped to `--no-use-evidence`; pass `--use-evidence` to
restore the lookup.  `score_pool(use_evidence=None)` still auto-detects, which
is what library callers and `deckgen validate` want — only the CLI changed.

**Partly reproduced, and the part that failed is instructive.**  Ten archetype
seeds x 3 RNG seeds, both modes:

| | with evidence | without |
|---|---:|---:|
| Caius the Shadow Monarch at 3 copies | 2 of 10 decks | **0 of 10** |
| Trap Dustshoot in >=8 of 10 decks | yes | no |
| mean pairwise Jaccard | 0.253 | 0.227 |
| mean seed-archetype share | 40.8% | 38.9% |

The specific complaint is real — generic staples crowd into unrelated
archetypes.  Ryko at 3 appears only in the Lightsworn build, in *both* modes,
which is correct (it is a Lightsworn).

**The aggregate proxies do not show it, and they are the wrong instrument.**
Seed-archetype share cannot see the swap because the cards Caius displaces are
*also* off-archetype.  A played deck beats a proxy for a played deck; this repo
already holds that principle for the emulator and it applies here.

Worth being blunt about the methodological hole this exposes: **every fitted
metric in this file rewards the behaviour the user rejected.**  Card Spearman
and deck AUC both score agreement with the tournament corpus, and that corpus is
survivor-biased — these are the decks that won money, so they converge on
whatever the meta settled on.  Optimising toward it builds the meta, not a deck.
The evidence channel is that bias in its purest form: a per-cid lookup that is
**73% of what separates one card from another**.

## 17. Every wiki tag made fittable, and fitted

**30 of 79 tags were read by nothing** — 21 of the 59 wiki tags, and 9 of the 20
derived ones.  Three different situations, and only one was a gap:

* redundant labels (`tribute_cost`, `banish_cost`, `lp_cost` — economy already
  prices them through their clauses);
* read via a function rather than the tag (`generic_material` and friends, via
  `wikitags.material_genericity`), and the structural `effect_monster` /
  `spell_card` / `trap_card`, which exist so nothing has to reason about an
  untagged card;
* genuinely unused signal — `stat_boost` (494 cards), `summon_payoff` (272),
  `conditional` (221), `attack_lock` (143), `equip_effect` (105) and ten more.

All 21 got a params key at 0.00, a `_TAG_KEYS` entry and a search grid; four
more (`piercing`, `direct_attack`, `double_attack`, `gy_setup`) were scored but
had never been in a search space.  `SEARCH_SPACE` 28 → 53.

**A guard caught an error:** adding `power.tag_battle_removal` raised
`RuntimeError: SEARCH_SPACE and DECK_SEARCH_SPACE both fit [...]; whichever fit
runs last would silently win`.  It is already owned by the deck objective.

**Also fixed, and it would have made deck-level profile fitting a silent
no-op:** `search.generate` does `p = p or default()` with no profile
resolution, so `deckscore.score` read stock `[deck]` weights even in randomised
mode.  The CLI now resolves the profile before handing `p` to `generate`.

### Result — 53 coefficients, leave-one-format-out

All four folds positive: Crow +0.0034, Edison +0.0111, Tengu +0.0242, Trishula
+0.0116; mean **+0.3680 → +0.3806**.  Nine reached ≥3/4; eight written.

`gy_setup` 0.70→1.10, `name_change` 0.00→0.70, `fusion_payoff` 0.00→0.30,
`generic_nontuner` 0.00→0.70, `generic_tuner` 0.00→0.70, `equip_effect`
0.00→−0.60, `piercing` 0.25→0.00, `staple_exponent` 0.60→1.00.

**Four of the six predicted-redundant tags refused, as predicted** —
`tribute_cost`, `banish_cost`, `lp_cost` and `generic_material` never reached
consensus.  The two that did are the *half*-generic Synchro categories, and that
reads as a correction rather than double counting: `material_genericity` scores
"generic in one half only" at 0.5 and the fit is saying 0.5 is too low.  The
fully-generic case it already prices at 1.0 was left alone.

**`impact.w_power` 1.50 refused for the second time.**  3/4 folds wanted it.
Measured over 10 archetype seeds × 3 RNG seeds at 0.80 vs 1.50: seed-archetype
share 38.2% → 37.2% (worse), pairwise Jaccard 0.234 → 0.209 (better).  A wash on
the only criterion that has ever caught this coefficient out, and it would run
the tag weights at nearly twice the scale they were just fitted at.

`[profile.randomised]` now overrides **16** coefficients.

**Stated honestly:** the +0.0126 held-out gain does *not* show up in the deck
proxies (38.9% → 38.2% archetype share, 0.227 → 0.234 Jaccard, both noise).
Either the gain is real and the proxies cannot see it — which is exactly what
happened with the Caius convergence — or it is fit noise that survived four
folds.  Play-testing is the arbiter, as it was for the default flip.

## 18. Four bugs from play-testing — all real, and two were the same bug

User-reported after building decks.  Every one reproduced.

### 1 + 2 are ONE bug: the Extra Deck was answering Main Deck wants

Reported separately — "Stratos gets added without a valid search target, the
output says it is satisfied because it counts itself" and "Allure of Darkness
gets added to decks with no DARKs, I think it is counting the Extra Deck".

Stratos does **not** self-satisfy (`self_satisfied` handles that correctly).
What satisfied its `1 "HERO" monster` want was **Elemental Hero Absolute Zero,
a Fusion in the Extra Deck** — `satisfied=2, self_sat=1, met=1`, so the orphan
penalty never fired.  Allure's DARK want matched 654 cards, **67 of them Extra
Deck**.  Same defect: you cannot search, draw, discard or banish-from-hand an
Extra Deck monster.

`Predicate.main_deck_only`, set on every want whose clause does not explicitly
reach the Extra Deck, plus on all support wants.  Instant Fusion correctly keeps
it False (its want matches 33 cards, all Extra Deck).  Stratos' want went 89 →
44 matches, Allure's 654 → 587, both with zero Extra Deck.

### 3. `distinct_names` — copies were counting as names

Judgment Dragon wants "4 or more 'Lightsworn' monsters with different names".
With 2 Lyla and 2 Ryko: `satisfied=5, met=4` — four copies, **two names**.
`Predicate.distinct_names` counts distinct cids instead; the same deck now reads
`met=2`, and four differently-named Lightsworn read `met=4`.  12 cards word a
want this way, including Rainbow Dark Dragon and the whole Six Samurai line,
whose entire mechanic is needing a *differently-named* Samurai.

### 4. Fusions reserved without their materials

`_fill_extra` runs in **phase 3, after the main deck is locked**, so an Extra
Deck card's material wants arrive too late to pull anything in.  The fallback
pass at the bottom has always applied `_fusion_ready`; the `_wanted_extra`
*reservation* pass never did.  So Overload Fusion's "1 DARK Machine Fusion
Monster" want reserved Chimeratech Overdragon into a deck with no Cyber Dragon
and no Machines.

`_wanted_extra` now refuses to reserve a Fusion the deck cannot make.  The want
then stays unmet and the orphan penalty prices the asker — which is correct:
Overload Fusion with no Machines *is* a dead card.  Verified: the Overload
Fusion seed now ships no Fusion at all rather than an unsummonable one.

### Measured

| metric | before | after |
|---|---:|---:|
| Spearman era, evidence off | +0.2973 | **+0.2991** |
| Spearman all formats, evidence off | +0.2070 | **+0.2113** |
| Spearman era, evidence on | +0.6299 | +0.6301 |
| deck AUC, by-format | 0.8668 | 0.8659 |
| wants | 2365 | 2377 |

Golden 20/20, validate 3 PASS / 0 FAIL.  These are correctness fixes and the
metric movement is noise either way; the reason to believe them is that each
reproduces a specific wrong deck.

## 19. `_fusion_ready` was a boolean, so material DEPTH was invisible

User-reported: a LIGHT-heavy HERO deck took Future Fusion + Stratos + **Absolute
Zero** + a splashed WATER monster, when **Elemental Hero The Shining** was
available and needs only a LIGHT monster the deck already had 20 of.

**Not a readiness failure.**  Both are `_fusion_ready=True` there.  The Shining
lost on impact, +0.935 against +1.099, and the fallback sorted by `-impact`.
The gap is economy and it is defensible in the abstract: Absolute Zero's
on-leave board wipe prices as `gain.destroy_opp x2.2` = +2.20, The Shining's
return of 2 banished HEROes as `gain.search x2` = +1.90.

What the model had no way to see is *how well the deck feeds each one*.
`_fusion_ready` answers "can I assemble this at all", so "12 LIGHT monsters" and
"exactly 1 WATER monster" scored identically and raw impact broke the tie.
Measured in that deck: The Shining is **6 copies deep** on its scarcest
material, Absolute Zero **1**.

`search._material_depth` scores the bottleneck material, saturating at 3 copies,
skipping support wants (`parse.SUPPORT_WANT_PREFIX` — "supports LIGHT" is not a
material).  Both the `_wanted_extra` reservation pass and the `_fill_extra`
fallback now rank by `impact x depth`:

    Elemental Hero The Shining     rank +0.935  (impact +0.935 x depth 1.00)
    Elemental Hero Absolute Zero   rank +0.366  (impact +1.099 x depth 0.33)

**Correction to the report's premise, worth keeping:** The Shining needs
*1 "Elemental HERO" monster* + 1 LIGHT monster, not any two LIGHT monsters — so
a LIGHT deck with no Elemental HEROes still cannot make it, and correctly ships
no Fusion at all.  Verified across three seeds: the Stratos deck now takes The
Shining, and the Lumina (22 LIGHT) and Honest (18 LIGHT) decks take no Fusion,
which is right.

Golden 20/20, validate 3 PASS / 0 FAIL, headline metrics unmoved.

## 20. Future Fusion's mill — the enabler half fixed, the materials half not

User: "the payoff for Future Fusion is firstly the milling effect and secondly
the fusion summon — e.g. Elemental Hero Gaia can mill an EARTH monster like
Dandylion."

**Future Fusion's mill is not parsed at all.**  "Send the Fusion Materials
listed on it from your Main Deck to the GY" yields no mill/send clause — its
clauses are `special_summon`, `target`, `destroy x2`.  Its `gy_filler` /
`gy_setup` tags come from the **wiki** ("Sends from your Deck to your
Graveyard"), which is a good demonstration of why the scrape was worth doing.

But `provides` is built from *clauses*, so Future Fusion did not provide
`send_gy`, and every card REQUIRING one — Dandylion, Necro Gardna, Treeborn Frog
— took `penalty_no_enabler` sitting next to it.  **33 cards** were in that state:
Painful Choice, Reasoning, Monster Gate, Card Trooper, Destiny Hero - Diamond
Dude among them.

Fixed by deriving the capability from the wiki tag as well as from clauses —
the same claim by a more reliable route.  Providers **146 → 178**, one residual
gap.  Verified: `penalty_no_enabler` on Future Fusion + Dandylion + Stratos goes
to 0, `synergy_cycles` 0.461, and a Dandylion-seeded deck now takes Future
Fusion as a miller.  Golden 20/20, validate 3 PASS / 0 FAIL.

### BUILT: `deck.w_fusion_mill` — milling a payoff on purpose

The chain is Future Fusion names Gaia -> Gaia lists "1 Elemental HERO + 1 EARTH
monster" -> Dandylion is EARTH and pays off for being sent.  The generic
`gy_filler` <-> `gy_payoff` cycle cannot see it: it pays for ANY GY payoff,
including a Spell no Fusion could ever list.

The simplification that made it tractable: **Future Fusion may name any Fusion**,
and the Extra Deck is not chosen until phase 3 — so the gate does not need the
*chosen* Extra Deck, only whether a card is a Fusion material at all.  That is a
pool-level bitmask (`MatchIndex.fusion_material_mask`, 2,500 of 4,076 cards)
computed once, not a per-score scan.

`DeckState` accumulates `fusion_millers` (an enabler that is `fusion_payoff` +
`gy_setup` + provides `send_gy` — exactly Future Fusion in this pool) and
`millable_payoff` (a `gy_payoff` card that is somebody's Fusion material);
`deckscore` pays `w_fusion_mill * sat(millers) * sat(payoffs)` on top of the
cycle.  Verified in isolation: `synergy_cycles` 0.461 -> 0.923.

**Two wrong layers found on the way, both worth recording:**

1. It was first built in `synergy.pair` — which is **only the candidate
   prefilter**; `deckscore.score` never calls it.  So it reshuffled which cards
   got evaluated without ever rewarding the pairing: millable payoffs across
   four decks went **15 -> 13**, noise in the wrong direction.  A note now sits
   in `synergy.py` saying so.
2. Moved to `deckscore`, it still did nothing — at 1.5, 4.0 **or 10.0**.  Beam
   search clones a `DeckState` per candidate and `clone()` did not carry the two
   new accumulators, so they reset to 0 for every card the search actually
   evaluated.  The term fired in a direct test and never during a build.

With `clone()` fixed: 15 -> **16** millable payoff copies at w=1.5, and 4.0 buys
nothing more, so 1.50 (the `w_gy_cycle` range) is the value.  Small, but real
and in the right direction.  Golden 20/20, validate 3 PASS / 0 FAIL.

### BUILT: which Fusion gets named (`_mill_value`, reserved in phase 3)

The other half, and it turned out to need **no phase reordering at all** — which
was the wrong framing in the first place.  Future Fusion does not have to
*Summon* the Fusion it names, so any Extra Deck slot will do; the question is
never "which Fusion can I make" but "which Fusion mills the payoffs I already
built".  That is answerable in phase 3, when the main deck is already known,
which is exactly when `_fill_extra` runs.

`_mill_value(state, s)` counts the `gy_payoff` copies in the main deck that *s*'s
material predicates match.  Cheap: once per candidate in phase 3, never in the
score loop.

**Ranking it in the fallback was not enough** — measured identical at W=0.00 and
W=0.35, because the Synchro reach ranking spends 14 of the 15 slots first and the
Fusion fallback barely runs (the Future Fusion deck had exactly one non-Synchro).
So the mill target is now *reserved* alongside `_wanted_extra`, before the reach
ranking, whenever the deck holds a Fusion-miller and some Fusion would mill
something.

Verified:

| seed | before | after |
|---|---|---|
| Future Fusion | Absolute Zero, mill 0.0 | **Dark Balter the Terrible, mill 3.0** |
| Elemental Hero Gaia | Gaia 2.0 | Gaia 2.0 + **The Shining 2.0** |
| Elemental Hero Stratos | — | **Absolute Zero 2.0 + Dark Balter 2.0** |

Golden 20/20, validate 3 PASS / 0 FAIL, headline metrics unmoved.

### The pattern worth carrying forward

Four separate changes this session did nothing until the layer was right, and in
every case a direct synthetic test PASSED while the search saw nothing:

1. the fusion-mill bonus in `synergy.pair` — that module is only the candidate
   prefilter, `deckscore.score` never calls it (15 -> 13, wrong direction);
2. the same term in `deckscore` — `DeckState.clone()` did not carry the new
   accumulators, so they reset to 0 for every candidate the beam evaluated
   (no effect at 1.5, 4.0 **or** 10.0);
3. `_mill_value` in the `_fill_extra` fallback — the reach ranking had already
   spent the slots;
4. (earlier) the `w_power` A/B, where `score_pool` re-applied the profile over
   the value under test and produced byte-identical decks.

**Rule: A/B a new term against a real `search.generate` build, never against a
hand-built DeckState.**

### Still NOT modelled

The `gy_filler` ↔ `gy_payoff` cycle is generic (+0.4 a pair), so Future Fusion
scores with *any* GY payoff, including one no Fusion in the Extra Deck could
ever mill.  The real chain is three cards — Future Fusion names Gaia, Gaia lists
"1 Elemental HERO + 1 EARTH monster", Dandylion is EARTH and pays off on being
sent.

Modelling it needs the Extra Deck's material predicates available **while the
main deck is being chosen**, and `_fill_extra` is phase 3 — the same
phase-ordering limitation that caused the Overload Fusion bug in section 18.4.
A term added to `deckscore` would see the right Extra Deck only after every
main-deck slot was already spent.

The tractable design, for whoever picks this up: give a deck-milling Fusion
enabler a *want* for "a Fusion Monster whose material predicates match a
`gy_payoff` card in this deck", so it is expressed during selection rather than
scored after it.  That is the same trick `_wanted_extra` uses to reserve Extra
Deck slots for main-deck wants, run in the other direction.

## Ruled out / corrected

- **"map 'Activates upon attack declaration' to `battle_payoff`"** — plausible
  and wrong; it is a card answering the *opponent's* attack, not an effect paid
  for by attacking.  Split into `attack_trigger`.
- **"'Banishes from your Graveyard' is `banish_payoff`"** — wrong direction.
  Miracle Fusion and King of the Skull Servants *feed* the banished zone; they
  are `gy_payoff`.  `banish_payoff` is only the harvest side.
- **"`_matches` can use `fullmatch`"** — silently killed every unanchored rule
  (`~battling monster`).  Regex rules **search**; anchor with `^`/`$`.
- **"`synergy_combo` never fires" — MY measurement error, not a model defect.**
  Reported it dead on all 250 decks with `deck.w_one_card_combo` at 8.00.
  `DeckState` only builds `combo_levels` `if self.level_value`, which
  `search.generate` sets and a bare `DeckState(idx=idx)` does not.  With it set
  as the search sets it, `synergy_combo` fires on **124 of 250** decks and is
  the **third largest mover** in the whole deck score (stdev 3.06, behind only
  `impact` and `penalty_payoff`).  Any future harness that scores a deck outside
  `search.generate` must set `level_value` and `_scored_cache` or it silently
  measures a different model.  `penalty_dead_draws`, `penalty_unsummonable` and
  `penalty_curve` really are off — their params are 0.00.

## Open questions

- `spot_removal` now means "has removal" (746 cards) rather than "single-target
  answer" (392) — the wiki does not distinguish 1-for-1 from mass.
  `mass_removal` stays derived and marks the subset, so both are visible to the
  fit, but the coefficient's *meaning* changed and it must be refit.
- `recurring` is mapped from "Limited activations", gated to monsters and
  Continuous/Field/Equip S/T.  A once-per-turn limit on a Normal Spell is a
  deckbuilding rule, not an engine.  Judgement call, not a wiki fact.

## Applied (user decision, 2026-07-30)

Asked, as the prompt requires; the user chose **apply all nine**.  Written to
`params.toml` via `training.write_params`; golden **20/20** after.  The stale
comments on `tag_floodgate` ("4 of 5 seeds chose 2.20") and `w_extra_generic`
("names no specific card and no archetype") were corrected in the same pass —
both described the state before this session.

`gain.negate_destroy` 1.00 → 1.30 was blocked here and **applied later** — see
section 9, after the golden assertion turned out to be hiding a parser bug.

### ⚠️ The numbers above and below are on DIFFERENT corpora

Everything up to this point was measured on the **348-deck** era corpus.
Section 8 replaced it with a **2,060-deck** one, which changes both the
evaluation sample and the target, so the two are **not comparable** and no
before/after should be read across that boundary.

On the 348-deck corpus, the tag/want work plus the nine coefficients moved era
Spearman (evidence off) +0.2705 → **+0.2987** and deck AUC by-format
0.8684 → **0.8756**.

On the 2,060-deck corpus, final shipped state:

| metric | after the corpus swap | now |
|---|---:|---:|
| Spearman era, evidence OFF | +0.2897 | **+0.2973** |
| Spearman all formats, evidence OFF | +0.2123 | **+0.2070** |
| Spearman era, evidence ON | +0.6270 | +0.6299 |
| deck AUC, random split | 0.9504 | **0.9530** |
| deck AUC, by-format split | 0.8620 | **0.8668** |
| distinct tags / wants / tagless | 79 / 2375 / 0 | 79 / 2365 / 0 |

(The all-format dip is the 2,618-card sample changing with the corpus, not a
regression: the same config measured +0.2014 before the parser fixes.)

## Coefficients CHANGED this session, in one place

| coefficient | from | to | why |
|---|---:|---:|---|
| `power.tag_floodgate` | 2.20 | 0.50 | old value fitted against 292 mis-tagged Nomi monsters |
| `power.tag_opponent_turn` | 0.00 | 1.20 | 5/5, held on 5.9x corpus |
| `power.tag_free_body` | 0.00 | 1.20 | 5/5, held on 5.9x corpus |
| `power.tag_recurring` | 0.00 | 1.20 | 3/5 then 5/5 |
| `power.tag_spot_removal` | 0.00 | 0.90 | 4/5 then 5/5 |
| `power.tag_summon_answer` | 0.00 | 1.50 | 3/5 then 5/5 |
| `power.tag_banish_payoff` | 0.00 | 0.70 | 3/5 then 5/5 |
| `power.w_extra_generic` | 1.20 | 2.00 | 5/5; now reads the wiki material fact |
| `gain.negate` | 0.70 | 1.10 | 5/5 |
| `gain.negate_destroy` | 1.00 | 1.30 | 4 fits wanted it; golden was hiding a parser bug |
| `gain.spin_opp` | 0.55 | 1.20 | 5/5; old value contradicted its own comment |
| `deck.w_deckout` | 6.00 | 0.00 | 5/5, non-confounded |
| `deck.w_search_access` | 3.00 | 6.00 | 4/5, deferred by the previous session |
| `[profile.randomised]` | — | 3 values | 4/4 leave-one-format-out folds |

**Rejected despite consensus:** `deck.p_orphan` 3.00 → 1.00 and
`deck.p_role_balance` 1.50 → 0.00 (confound measured, section 11);
`impact.w_power` 0.10 → 1.10 for the stock path (amplifies every tag 11x and
wrecks deck synergy — section 14).

## Next experiment

- **AI pilotability: dropped.**  The user ruled it out of scope on 2026-07-30.
  What was known is recorded in section 12's neighbourhood: the reactive rule
  table `0x02275510` covers 147 cards (3.61%) and is not the main move path;
  the per-card heuristics in `0x0224B094` remain unfound.  Do not build a
  pilotability term from the rule table alone.
- `Supports archetypes` (762 cards) and `Anti-supports` (263) are scraped and
  unused.  Anti-support has no channel at all — "this card is bad against LIGHT"
  has nowhere to go today.
- `spot_removal` and `recurring` (see Open questions) changed meaning when the
  wiki took them over; both were refit afterwards, but their *names* now
  overstate what they mark.
- The randomised profile only moves three coefficients.  The `power.tag_*`
  weights are shared between both modes and were fitted at `w_power` 0.10; if
  the randomised mode is used seriously they want refitting **inside** the
  profile, at its own `w_power` 0.80.
