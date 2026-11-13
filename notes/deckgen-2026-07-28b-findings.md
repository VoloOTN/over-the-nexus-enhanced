# deckgen — session findings (2026-07-28, continuation)

Picks up the "next session — priority order" list in
[deckgen-session-findings.md](deckgen-session-findings.md).  Items 1–3 of that
list were the brief; item 4 (training method) was pulled in because it is a
**prerequisite** for item 3 being trustworthy.

## Confirmed this session

### 1. The Hecatrice family — self-discard is now charged

`economy._spent_from_hand` (new).  `self_spend.monster` is 0.00 on the reasoning
that a monster going hand -> field is still your card; Hecatrice never goes to
the field, and the `self_ref and verb in _REMOVAL` skip in `_evaluate` then
dropped the only clause that would have charged for it.

- Fix: when a **monster**'s own effect discards / sends / banishes it **from the
  hand**, `self_spend` is raised to `cost.discard` (`max`, never `+`, so nothing
  is double-billed), evaluated per *mode*.
- **Scope verified by scan, not by reasoning**: 44 cards carry a self-referential
  hand cost — 38 monsters, 2 spells, 4 traps.  All 38 monster texts were read and
  all 38 are genuine self-discards.  The spell/trap ones are **parser artefacts**
  (Confiscation's "then discard it" is the *opponent's* card; Forced Requisition
  is not a self-discard at all) — gating on `_self_spend_key == "monster"` dodges
  both, and `max` would have protected the Normal Spells/Traps anyway.
- Field and Graveyard self-costs stay uncharged deliberately: the parser reads
  "Tribute Summon" as a self-tribute on ~20 cards including **Dandylion**, so
  widening this to `zone_from == "field"` would silently bill it a card.
- Measured: Hecatrice econ **+0.95 -> -0.05**, impact **+1.16 -> +0.48**.  Also
  corrected: Thunder Dragon +1.90 -> +0.90 (discard 1, get 2 = +1 — right),
  Gravekeeper's Commandant +0.95 -> -0.05, D.D. Crow +1.04 -> +0.04, Effect
  Veiler +0.67 -> -0.33, Honest -0.00 -> -1.00.  Veiler and Honest reading as a
  clean −1 card is correct by the axis's own convention; their value is combat,
  not cards.
- `golden` still 14/14.

### 2. Search access — the consistency a searcher actually buys

`hypergeom.effective_copies` / `hypergeom.search_access` (new),
`DeckState.access_score`, `deckscore` term `search_access`, param
`deck.w_search_access` (3.00, in `DECK_SEARCH_SPACE` with 0.0 in range).

Charging the discard leaves Hecatrice a flat 1-for-1, so the model needed the
*other* half or it would have no reason to run the card at all.  Three Hecatrice
make the "1 Valhalla" want **six copies deep, not three: P(open) 0.338 -> 0.577**
(verified numerically).

- Per `ActiveWant`, `fetchers` = copies in the deck that can search or SS a
  satisfier **out of the Deck**.  Weighted exactly like `synergy_wants` — by
  `weight * exclusivity * seed affinity` — so making "1 Valhalla" findable
  (exclusivity 0.98) pays and making "1 monster" findable does not.
- Saturating by construction: 3 -> 6 effective copies buys 0.24, 6 -> 9 buys
  0.13, so it cannot be farmed by stacking searchers.
- Implementation is a single `int` AND: `DeckState.deck_mask` is a bitmask over
  the pool, `fetch_mask(cid)` is memoised per MatchIndex, and `searchers` is a
  Counter restricted to deck cards that fetch *something* — so the term walks ~8
  cards, not ~40.  Measured 0.22s / 2000 `score()` calls; build time unchanged
  (2m48s -> 2m58s, within noise of the added bootstrap rounds).
- Surfaced in the report: the WANTS section now prints `+N found`.
- **What it actually fires on, measured** (per-want breakdown, not inferred):
  the top-scoring ROM deck `sd18_machine` gets its +8.04 from the **Gadget loop**
  — `'1 "Red Gadget"'` met=1 fetch=3 gain 0.308, likewise Yellow/Green, plus
  `'1 "Commander Covington"'` met=1 fetch=4 gain 0.389.  The broad material wants
  in the same deck contribute **+0.001 and +0.000** (`'1 Machine monster'`
  met=25, `'it by Tributing these monsters'` met=35) — saturated `p_open` and low
  exclusivity, exactly as intended.  The textbook case of the mechanism is the
  deck the term picks out.
- **Caveat, stated up front:** on its own this term has
  **AUC(tournament > ROM) = 0.487** — no independent support from that corpus,
  and ROM decks median slightly *higher* (+0.421 vs +0.368).  That is the
  **documented concentration confound**, not a defect: the ROM ships
  mono-archetype structure decks (Gadget, Machina, Genex) whose entire identity
  is cards fetching each other, while the tournament corpus is Goat/Edison
  goodstuff.  The justification for the term is the mechanism plus the fact that
  charging the self-discard removed the *only* channel that priced it — not this
  AUC.  Treat a fit that zeroes it the same way params.toml already treats a fit
  that zeroes `concentration`.

### 2b. Ablation of the two halves, at otherwise fixed parameters

Deck-level AUC(tournament > ROM AI), all 1201 vs 222 decks, nothing refitted:

| configuration | AUC |
|---|---|
| pre-session (both off) | 0.7111 |
| **self-discard charge only** | **0.7198** |
| `search_access` only | 0.7085 |
| both on (shipped) | 0.7173 |

- **The self-discard charge is a clear, independent win: +0.0087.**  Removing a
  full card of phantom economy from 38 monsters improves how the model ranks real
  decks.  That is the strongest evidence produced this session.
- **`search_access` costs −0.0025 on this objective.**  Small, but real and not
  noise (the ablation is deterministic).  It is the same confound as above: the
  term rewards mono-archetype fetch loops, and the ROM's decks are mono-archetype
  structure decks.  Its justification is mechanistic and its payoff is in **deck
  construction**, which this AUC does not measure — the acid test below is what
  it was added for.
- **Acid test (what the term was for):** seeded on **Hecatrice**, the generator
  now builds the Valhalla Fairy deck — 3 Hecatrice + 3 Valhalla, WANTS reporting
  `1 "Valhalla, Hall of the Fallen"  3 copies +3 found`.  Before this session
  Hecatrice's value was a phantom +0.95 of economy; it is now a correctly-priced
  1-for-1 whose worth is consistency, and the deck still gets built.

### 3. The candidate-pool bug — `refinement_pool` (new)

`bootstrap` and `seed_holdout` both ranked against `top 200 by raw impact`.  The
top 200 by impact are the 200 best **staples**, so this was a false negative *by
construction* for every engine piece, and it meant bootstrap could only ever swap
a themed card **out** for a staple.

- Replaced with `search.refinement_pool`: ranked by `impact + best seed synergy`
  (the same quantity `_prefilter` drives the build with), and the **seeds, every
  card already in the deck, and the seed's engine are admitted unconditionally**.
- `engine_pool` is now built once before the restart loop instead of once per
  lambda — it never depended on lambda.
- **Measured on the same Valhalla build:** pool 200 staples -> **316 cards, 142
  of them engine**.  Seed holdout for Valhalla went from
  `+3.579 NOT competitive` to `+3.579 rank 11` — same marginal, and the old
  verdict was a statement about the list, not the deck.
- Bootstrap now finds real swaps (Yaksha -> Torrential Tribute +5.03,
  Future Fusion -> Monster Reborn +4.71 at theme **+0.42**, Stratos -> Sangan
  +3.48 at theme +0.16).

### 4. Training method (prerequisite for the deck fit)

- `fit_deck` **randomises parameter order per round**.  Dict order is insertion
  order, so every coefficient added later was measured against a deck the
  earlier ones had already claimed credit for — a systematic handicap on exactly
  the parameters that most needed measuring, and `w_search_access` would have
  been added at the end.
- `min_gain` replaces the `1e-6` acceptance threshold (default **0.002**).  This
  objective is an AUC over a few hundred deck pairs; 1e-6 is one pair swapping
  order.
- `fit_deck_multi` + `MultiFitResult`: N independent runs from the **same neutral
  base**, reporting per-seed choices and writing only what `--min-seeds` agree on.
- **`impact.w_economy` removed from `DECK_SEARCH_SPACE`.**  `score_pool`
  normalises impact to `target_spread`, so scaling `w_economy`, `w_power` and
  `w_evidence` together is exactly a no-op — only ratios are identifiable.
  Leaving all three free lets coordinate descent wander that degenerate direction
  and report "changes" that change nothing.  `w_economy` is now the numeraire.
- New CLI: `deckgen train-deck [--seeds ...] [--min-seeds N] [--apply]`.

### 5. The deck-level AUC fit — it runs, and it confirms the trap

Smoke run (1 seed, 1 round) on the new model: held-out AUC **0.688 -> 0.772**,
gain +0.0837.  `impact.w_power` **0.80 -> 0.10**, exactly as params.toml
predicted.  Full 5-seed / 2-round run: see below.

### 5b. The 5-seed deck fit — result and what was applied

Held-out gain **+0.0807 ± 0.0055, 5/5 positive** (0.688->0.775, 0.711->0.793,
0.731->0.817, 0.728->0.802, 0.715->0.789).

**Applied** (5/5 seeds AND not in the documented confound family).  Full-corpus
deck AUC **0.7173 -> 0.7744**; golden still 14/14:

| coefficient | old | new | why it is safe |
|---|---|---|---|
| `impact.w_power` | 0.80 | **0.10** | the trap params.toml already documents |
| `power.w_searchability` | 1.00 | **0.15** | card-level findability, now largely superseded by `deck.w_search_access` |
| `deck.p_orphan` | 3.00 | **8.00** | rewards coherence, not mono-archetype-ness |

**Withheld deliberately — the fit wants these and it should not get them:**

- `deck.w_want_scale` 4.00 -> 1.00 [5/5], `deck.w_tuner_reach` 1.50 -> 0.50
  [5/5], `deck.w_archetype` 2.00 -> 0.50 [4/5] — the concentration/synergy
  confound, exactly what the standing tension in params.toml is about.
- `deck.p_dead_advantage` 2.00 -> 0.50 [5/5] — params.toml records this as kept
  at 2.00 **because it was asked for explicitly**.  The fit is now unanimous
  rather than weak, so the note's stated reason ("the fit's preference was weak")
  no longer holds — but overturning an explicit request is the user's call.
- `power.self_ss_tax_relief` 0.35 -> 1.00 [4/5] — **the two objectives disagree**.
  The previous session's card-level fit called 0.35 robust across every seed.
  Needs a decision about which objective owns this coefficient.
- `deck.interaction_max` 0.50 -> 0.65 [3/5] — bare majority, left alone.
- `deck.w_search_access` 3.00 -> 0.00 [3/5] — my own new term; see the caveat in
  section 2.  Kept, with the reasoning written into params.toml.

## Performance (asked for separately: logging + speed)

Full build of one deck, end to end, **~103s -> ~5.9s (17x)**.  Everything below
was verified equivalent, not assumed: a differential test compares old and new
formulations over 4,076 cards and 705 decks and reports **0 mismatches**, and
the cache artifacts are checked field-by-field against a fresh build.

**Instrumentation first** (`search.BuildStats`, `deckscore.CALLS`, the
`-- BUILD TIMING --` report section).  Seconds *and* score-call count per phase,
because those two separate a scoring regression from a search-shape regression;
guessing which it was is how this started.

| fix | saving |
|---|---|
| memoise `namematch.normalize` — 7.9M calls, called per deck card per bundle partner per score | 53s -> 5s |
| cache the **parse** (`load_parsed` re-parsed all 4,076 cards *every run*; its "well under a second" comment was 9x stale) | 9.2s -> 0.4s |
| cache `MatchIndex.build` (3.1M `Predicate.matches` to rebuild fixed integers) | 2.6s -> 0.03s |
| `Partner.match_cids` — precompute the cid set per bundle partner | 13s -> 4s |
| two-stage playset pricing (`resize_top`) — price each candidate once, sweep 3/2/1 only for contenders | 237,880 -> 97,927 score calls |
| `wants_mask`, `_is_interaction`, `_can_cheat_out`, `Params` path cache, `p_at_least_k` LRU, `_copy_counter` | ~20s |
| **narrow search is now the CLI default** | 36s -> 3.9s |

**The narrow-search finding is the interesting one.**  Paired over 2 seeds x 3
RNG seeds, wide (3 restarts / 200 candidates / beam 8) scores **139.16 ± 16.91**
against narrow (1 / 60 / 4) at **143.18 ± 7.66** — paired difference
**+4.02 ± 16.49**, i.e. nothing, and narrow has *lower* variance.  The search
samples its picks stochastically, so its RNG spread is several times larger than
anything the extra width buys.  Practical consequence: at ~4s a build, running
nine `--rng-seed` values and keeping the best strictly beats one wide build.
`--thorough` restores the old behaviour.

## Retraining round 2 (after the two withheld coefficients were released)

`deck.p_dead_advantage` 2.00 -> **0.50** and `power.self_ss_tax_relief` 0.35 ->
**1.00** applied on an explicit decision.  Both comments in params.toml were
rewritten rather than left standing — the `p_dead_advantage` one asserted it was
pinned at 2.00 *because the fit's preference was weak*, which was true of the old
single-seed run and false of the 5-seed one.  Deck AUC **0.7744 -> 0.7806**.

### The two search spaces overlapped on eight coefficients — a race, not a choice

`SEARCH_SPACE` (card play rate) and `DECK_SEARCH_SPACE` (deck AUC) both fitted
`impact.w_power`, `impact.econ_scale`, `power.w_stat`, `power.w_searchability`,
`power.self_ss_tax_relief`, `power.tag_battle_removal`, `power.tag_combat_trick`
and `power.tag_board_reset`.  **Whichever command ran last won**, and the
card-level grid for `w_power` starts at 0.35 — so a routine `train --apply` would
have silently undone the deck fit's 0.10, the precise value params.toml documents
the card objective as getting *wrong*.

Split by which question each objective can answer, and asserted disjoint at
import so re-adding one is a hard error:

- **card play rate** owns per-card quality: tag weights, gain coefficients (9).
- **deck AUC** owns how card scores aggregate into a deck: the whole impact
  balance, the stat/searchability channels that summing over 40 cards distorts,
  and every `deck.*` term (37).

### The card-level fit is converged — and that is the interesting part

5 seeds x 2 rounds over the 9 remaining coefficients: **held-out gain 0.0000,
nothing moved on any seed.**  Verified it is not the new `min_gain` threshold
hiding something — the best single move available anywhere in the space is
`tag_atk_scaling 0.55 -> 0.00` at **+0.000053** Spearman, 20x under the
threshold, and six of the nine have *literally zero* improvement available.

So the previous session's card-level gain (+0.0217 ± 0.0062) was coming almost
entirely from the impact-balance coefficients — the ones the deck objective
measures as anti-correlated with deck quality.  Strip those out and play rate has
nothing left to say about the tag weights.  That is independent corroboration for
the split above, and it means `train` is now a cheap no-op check rather than a
source of drift.

Both fits also gained the multi-seed / randomised-order / real-threshold
treatment, so `train` and `train-deck` are now measured the same way.

### Deck fit round 2 — converged

5 seeds x 2 rounds from the updated base: held-out **+0.0206 ± 0.0008, 5/5
positive** (0.756->0.776, 0.774->0.795, 0.798->0.819, 0.781->0.801,
0.771->0.790).  Every value released this session is now **stable at 5/5**:
`w_power` 0.10, `w_searchability` 0.15, `p_orphan` 8.00, `p_dead_advantage` 0.50,
`self_ss_tax_relief` 1.00.

`deck.w_archetype` no longer wants cutting (5/5 at 2.00 — the earlier 4/5 vote
for 0.50 was pressure that other coefficients absorbed once they moved).

**`deck.w_search_access` flipped to 3/5 for KEEPING 3.00** (was 3/5 for 0.00).
The evidence is genuinely marginal in both directions and should be described
that way — but on the current base the fit no longer votes to delete it.

Still asked for and still withheld: `deck.w_want_scale` 4.00 -> 1.00 [5/5] and
`deck.w_tuner_reach` 1.50 -> 0.50 [5/5] — the documented concentration confound
— plus `deck.interaction_max` 0.50 -> 0.65 at a bare 3/5.  Nothing new applied:
the fit has converged onto the values already in params.toml.

## Blind spots, measured against play rate (2026-07-28)

Method: rank every card played in >=15 of the 1,201 tournament decks by
`play-rate percentile - impact percentile`.  The top of that list is what the
corpus loves and the model cannot see.  Three of the four causes are **one bug
class — clause reference resolution — not coefficient tuning.**

### 1. Anaphoric removal is silently dropped (largest)

`economy._evaluate` skips any clause with `self_ref and verb in _REMOVAL`.  That
is right for "destroy **this card**" and for a card destroying its own summon
(Premature Burial, Call of the Haunted — both correctly skipped, 116 cards).  It
is **wrong** when the anaphor points at a card the effect just targeted on the
opponent's side.

- **283 cards, 4,285 deck appearances** carry a dropped gain clause of this shape.
- Verified wrong: **Bottomless Trap Hole** ("banish it", econ 0.00, 297 decks),
  **Trap Hole** ("destroy that target", −1.00, 167), **Solemn Warning**
  ("destroy it", 107), **D.D. Warrior Lady** ("banish that monster", 327),
  **Ally of Justice Catastor** ("Destroy that monster", 303), **Tsukuyomi**.
  Each loses its *entire* payoff and reads as a pure self-spend.
- A fix must distinguish "the card I targeted" from "the monster I summoned",
  so it is a parser change, not a one-line predicate — and golden's Smashing
  Ground / Share the Pain conventions have to survive it.

### 2. Opponent-directed effects recorded as `side="you"`

`_gain_key` returns `None` for removal with `side="you"`, so these score exactly
zero rather than being credited.  **134 cards**, including **Crush Card Virus**
(econ −2.00, 132 decks — the destroys are both `side="you"`),
**Thousand-Eyes Restrict** (0.00, 402), **Brionac** (0.00, 302).

### 3. Hand disruption — the most-played cluster in the corpus, all negative

Three *different* failures, one theme:

- **Delinquent Duo** (340 decks, econ **−2.20**): "your opponent discards" parses
  as `kind=cost, side=you`, so the opponent's loss is billed as **our** cost.
  A sign flip, and the first discard yields no clause at all.
- **Confiscation** (362 decks, −1.20): "discard that card" marked `self_ref`, so
  it is dropped entirely.
- **The Forceful Sentry** (223 decks, −1.00): "return it to his/her Deck"
  produces **no clause whatsoever**.

Note `side="opponent"` discards *are* filed correctly as gains when the parser
gets the side right (24 of 24), so this is reference resolution again, not the
economy model.

### 4. Genuine model gaps (not parser bugs)

- **No ATK/DEF modification economy** — Megamorph (econ −0.85, only a self_spend),
  Injection Fairy Lily (−1.37, 172 decks).  Belongs in `power`, not `economy`.
- **Restricted draw is priced as free draw** — the overrated tail is
  Moray of Greed (+2.09 impact, 15 decks), Junk Synchron (+2.47, 16),
  Necrovalley (+1.74, 17).  "Shuffle 2 WATER from your hand into the Deck, draw
  3" is billed as +2 cards with no charge for the requirement.
- **Fiber Jar** still −0.87 at 111 decks; `board_reset` matches only 2 cards.

### Why this matters more than more tuning

The card-level fit is converged (best available move +0.000053 Spearman) and
Spearman sits at ~0.42.  These blind spots are the ceiling: no coefficient can
recover a clause the parser dropped.  **Fix order by evidence: 1, then 3, then 2**
— together ~5,000 deck appearances of the corpus's most-played cards.

## Parser fixes (2026-07-28, after the blind-spot survey)

Card-level Spearman **+0.4218 -> +0.4365**, deck AUC **0.7806 -> 0.7831**,
golden 14/14, clause rate 92.5% -> 92.7%.  Every fix below was traced to a
specific mechanism on a specific card before being written.

1. **Clauses now come out in TEXT order, not RULE order** (`clauses.extract`).
   `resolve_pronouns` scans forward for an antecedent, so a pronoun emitted
   before its target never bound.  Confiscation's "select 1 card in it and
   discard that card" produced the discard *first*.
2. **Trigger objects are antecedents** (new `trigger_object` verb).  Every
   existing trigger rule had `target_group=None` and so carried no predicate —
   which is why "When your opponent Summons 1 monster with 1000+ ATK: Target
   that monster; destroy that target" resolved nothing.  **Trap Hole −1.00 ->
   0.00**, **Ally of Justice Catastor −0.00 -> +1.00**, **D.D. Warrior Lady
   −0.00 -> +1.04**.
3. **"targeting" (gerund)** was not matched, only the imperative "Target".
   **Call of the Haunted 0.00 -> +0.65** — it raised no target at all, so
   "Special Summon that target" fell back to `ss_unspecified` (0.35) instead of
   `ss_from_gy` (1.00).  The single most-played card in the corpus.
4. **Explicit self-reference is never a pronoun** (`_EXPLICIT_SELF`).  Caught in
   review: fix 2 made D.D. Warrior Lady bind "also banish **this card**" to the
   opponent's monster and score **+2.09**, paid twice.
5. **A target already removed cannot be removed again.**  Also caught in review:
   Bottomless Trap Hole's "Destroy that monster … banish it" paid `destroy_opp`
   AND `banish_opp` for one monster (**+1.10**).  Now 0.00 — spend one, remove
   one, which is the axis's convention.
6. **Hand disruption**: `discard` added to `_SIDE_SENSITIVE`; new
   `_OPPONENT_HAND` sentence signal (the existing `_OPPONENT_TRIGGER` is
   trigger-shaped, and Confiscation opens with a *statement*); `discards?` for
   the third person; and a rule for "return it to his/her Deck", which matched
   nothing at all.  **Delinquent Duo −2.20 -> +0.60**, **Confiscation −2.20 ->
   −0.30**, **The Forceful Sentry −1.00 -> −0.40**, Don Zaloog +0.90.
   Graceful Charity and Card Destruction deliberately unchanged — their discard
   really is ours.

## CORRECTION: the blind-spot survey was measured against the wrong formats

**My earlier "underrated cards" list was an artefact.**  It ranked by play rate
over `tournament.load()`, which spans **~100 formats from Goat (2005) to 2024**.
`mining.era_decks` already restricts to `("Tengu", "Edison", "Crow",
"Trishula")` — the 2010-11 formats this ROM actually models — and documents why.

Re-run against the ROM's own era (348 decks), **there is essentially no blind
spot left**: the "underrated" list is Mirror Force (+8.22), Heavy Storm (+7.89),
Torrential Tribute (+7.66), MST (+7.26) — cards the model already ranks at the
very top and cannot rank higher.  The rest are 8-14 deck samples.

So Premature Burial, Delinquent Duo, Confiscation, Snatch Steal, Pot of Greed
and Raigeki scoring low is **correct for this ROM**: they are Goat-format
staples and **Forbidden** under the default `limit201009` banlist.  Their
mined play rate is 0.0000 by design, not by failure — 68 cards are in that
position and I initially mis-read it as a coverage bug.

**The measurement that matters:**

| objective | value |
|---|---|
| Spearman(impact, play rate), all ~100 formats | **+0.4365** |
| Spearman(impact, play rate), ROM's own era | **+0.7377** |

The model is far better than the headline metric said; it was being graded
against formats it does not cover.

**APPLIED** (on an explicit decision): both objectives now fit against
`ERA_FORMATS` (348 decks), with `--all-formats` to restore the old behaviour.

### …and doing so exposed a circularity that had to be closed first

The evidence channel (`power.w_staple`) turns **play rate into a feature**.
Scoring `impact` against play rate therefore measures the lookup, not the model.
Quantified by zeroing `impact.w_evidence`:

| corpus | with evidence | evidence OFF (the model's own signal) |
|---|---|---|
| era | **+0.7377** | **+0.2039** |
| all-format | +0.4365 | +0.1982 |

**About three quarters of the apparent correlation was play rate predicting
itself**, and it is worse on the era corpus precisely because `mining` derives
the feature from those same decks.  Switching the objective to era decks without
fixing this would have driven `w_staple` to its maximum and reported a large
fake gain.

Closed by splitting the corpus:

- `score_pool` takes an optional `play_rate=` override.
- `training.fit` mines the feature from the **fit half** and evaluates on the
  **held-out half** — `w_staple` can still earn its weight by generalising
  (play rate in one half really does predict the other), but not by memorising.
- `train-deck` mines the feature from a **held-out quarter** of the good decks
  and scores the remaining three quarters, so no deck contributes to its own
  staple bonus.

Honest card-level number after the fix: **held-out Spearman +0.662** on the era
corpus, and the card fit remains a no-op (converged).

**Every Spearman figure quoted earlier in this file predates this fix and is
inflated.** The comparable honest numbers are +0.662 (era, split) and +0.20
(model-only, no evidence channel).

## The era refit — and reverting three coefficients applied earlier the same day

Era corpus (261 good vs 222 poor), evidence mined from a held-out quarter:
held-out gain **+0.1953 ± 0.0201, 5/5 positive** — but the *baselines* had
collapsed to 0.51-0.61 (from 0.76-0.80) because closing the leak removed the
free signal.  Most of that "gain" is recovering ground the leak was giving away,
not new ground.

**The fit reversed three coefficients applied earlier today**, each 5/5 in both
directions:

| coefficient | pre-session | all-format fit | era fit |
|---|---|---|---|
| `deck.p_orphan` | 3.00 | **8.00** [5/5] | **1.00** [5/5] |
| `deck.p_dead_advantage` | 2.00 | **0.50** [5/5] | **4.00** [5/5] |
| `power.self_ss_tax_relief` | 0.35 | **1.00** [4/5] | **0.00** [5/5] |

Two unanimous fits pointing in opposite directions is what an **unidentified
coefficient** looks like.  Settled by measurement on five held-out era splits
that neither fit optimised on:

| parameter set | held-out AUC |
|---|---|
| pre-session | 0.9455 ± 0.0049 |
| **applied earlier today** | **0.9349 ± 0.0062** |
| era-fit values | 0.9485 ± 0.0041 |

Per-parameter, **every** era-fit change is worth at most **+0.0016** and several
are negative (`p_atk_floor` −0.0025, `tax_level_7_plus` −0.0015,
`p_role_balance` −0.0010) — all noise against a 0.945 baseline.  The three
applied earlier cost **−0.0106**, which is 4-7x larger and consistent across
every seed.

**Action taken: the three were reverted to their pre-session values; nothing
from the era fit was applied.**  Verified 0.9349 -> 0.9455, golden 14/14.

Kept, because they are stable and independently supported:

- `impact.w_power` **0.10** — 5/5 in both all-format fits, no consensus to move
  it in the era fit, and backed by the documented deck-level AUC split (economy
  0.625 vs power 0.393).  Reverting it is worth +0.0005, i.e. nothing.
- `power.w_searchability` **0.15** — 5/5 in every fit including the era one.
  Reverting is worth +0.0001.

**Lesson for the next session:** a 5/5 multi-seed consensus is *not* sufficient
evidence to move a coefficient.  All five seeds share one corpus and one
feature/objective split, so they agree about the data far more than they agree
about the model.  Confirm on a held-out split built differently from the one the
fit used before writing anything.

## Remaining blind spots (measured properly: era corpus, evidence channel OFF)

Method matters here.  Scoring against `impact` **hides** blind spots, because
the evidence channel gives a heavily-played card a large staple bonus whether or
not the model understands it.  These are scored with `impact.w_evidence = 0` and
`play_rate={}` — economy and power only — against the 348 era decks, restricted
to cards legal under `limit201009`.

**Parser coverage is no longer the gap**: exactly **one** era-played card yields
no clauses (Mystical Shine Ball, a vanilla with flavour text).

### 1. Self-directed removal written as an *effect* is free  (largest)

`_gain_key` returns `None` for removal on our own side (correct — destroying your
own card is not a gain), but `_cost_key` is never consulted because the clause's
`kind` is `"gain"`.  So it falls through both and costs nothing.

| clause shape | cards | era deck-appearances |
|---|---|---|
| `gain destroy you` | 503 | **1541** |
| `gain banish you` | 98 | 440 |
| `gain bounce you` | 45 | 436 |
| `gain send you` | 83 | 244 |
| `gain mill you` | 13 | 122 |
| `gain shuffle you` | 23 | 112 |

Clean example: **Moray of Greed** "Shuffle 2 WATER monsters from your hand into
the Deck, then draw 3" scores **+2.00** instead of +1.00 — the two cards put back
are free.  It is the top overrated card in the era list.

⚠️ **Do not simply route these to `_cost_key`.**  A large share are legitimately
free: "destroy this card" drawbacks (already in `self_spend`) and a card
destroying its own revived monster — Call of the Haunted and Premature Burial
both rely on not being charged there.  The safe subset is a self-directed
`shuffle`/`bounce`/`send` **whose `zone_from` is the hand**, which is a real
resource leaving.  Needs golden coverage before it ships.

### 2. Two dead parameters

`gain.negate_destroy` and `gain.opp_destroy_own` are declared in params.toml and
**never referenced in economy.py** — `_gain_key` maps every `negate` to
`gain.negate` (0.70) regardless.  Solemn Judgment (65% of era decks) negates
*and* destroys and is priced as a bare negate.

### 3. No tempo / position channel at all

Book of Moon (28% of era decks, econ −1.00), Enemy Controller (15%), Tsukuyomi.
Flipping a monster face-down or changing its battle position is neither card
advantage nor a printed stat, so both axes score it at a flat self-spend.  This
is a *design* gap, not a bug — it would need a `tempo` channel in `power`.

### 4. Negation looks underpriced

Solemn Judgment (65%, −0.55 model-only), Solemn Warning (40%, −1.14), Effect
Veiler (24%, −0.60).  A negate spends their card as well as ours, so `gain.negate
= 0.70` may be low — but see item 2 first: fixing `negate_destroy` may be most of
it.

### 5. Specific parse gaps still open

- **Trap Dustshoot** (72% of era decks, the most-played card in the era corpus):
  "return it to **the** Deck" — the rule added this session only accepts
  "his/her | their | the owner's | your opponent's Deck".  One alternation short.
- **One for One** (−1.85): "Special Summon … from your hand **or Deck**" — the
  disjunctive zone does not resolve, so it falls back to `ss_unspecified` (0.35)
  instead of `ss_from_deck` (1.15).

### ALL FIVE IMPLEMENTED

| # | fix | effect |
|---|---|---|
| 5a | `return … to **its owner's** Deck` (Trap Dustshoot, 72% of era decks) | −1.00 -> **−0.46** |
| 5b | disjunctive zone `from your hand **or Deck**` (One for One) | −1.85 -> **−0.85** |
| 2 | `gain.negate_destroy` reachable (`economy._negates_and_destroys`) | Solemn Judgment −0.30 -> **+0.00**, Solemn Warning −0.70 -> −0.40, Thunder King +0.67 -> +0.95 |
| 2 | `gain.opp_destroy_own` **deleted** — unreachable, and 0 of 4,076 cards are worded for it | — |
| 3 | new `tempo` tag + `power.tag_tempo` (48 cards) | Book of Moon impact −0.63 -> **+3.45**, Enemy Controller -> +2.23 |
| 1 | `economy._uncharged_own_cost` — own-hand spend in a gain clause (54 cards) | Moray of Greed **+2.00 -> +1.10** |

Also: a zone-bearing `shuffle … from X into the Deck` rule, ordered *before* the
bare one (the dedup key is `(verb, offset)`, so the bare rule would claim the
span and `_STOP` drops `from your hand` from the capture).

**Guards held.** Item 1's tempting generalisation — route every own-side removal
through `_cost_key` — would charge Call of the Haunted and Premature Burial for
destroying the monster they revived.  Restricting to `zone_from == "hand"` makes
that impossible; both are unchanged (+0.65, −0.20), as is Rekindling (−1.00).

**golden.toml 14 -> 20 assertions**, one per mechanism, including Call of the
Haunted explicitly labelled as a *guard* so the generalisation cannot be made
silently later.

### Measured outcome — modest, and stated as such

| metric | before the 5 | after |
|---|---|---|
| model-only Spearman, era (evidence OFF) | +0.2039 | **+0.2128** |
| model-only Spearman, all formats | +0.1982 | +0.1991 |
| era Spearman, card fit held-out (split) | ~0.662 | **~0.694** |
| deck AUC, held-out era splits | 0.9455 | 0.9446 |
| golden | 14/20 exist | **20/20 pass** |

The deck-level AUC is **flat** (−0.0009, noise).  That is the honest result:
these are correctness fixes on cards that were rarely decisive in deck
*construction*, so the payoff is that the model no longer prices Solemn Judgment
as a loss, no longer hands Moray of Greed a free card, and can see Book of Moon
at all.  The model's own reasoning improved (+0.009 on the metric that is not
contaminated by the play-rate lookup); nothing here is a headline win and it
should not be reported as one.

Refit afterwards: **no coefficient reached the bar.**  `gain.negate_destroy`
1.00 -> 1.30 got only 3/5 with a gain of +0.0011 ± 0.0011 — well under the
standard set earlier today, when a *unanimous* 5/5 turned out to be wrong.
`power.tag_tempo` had 0.0 in range and all five seeds kept 0.55, which is mild
evidence the channel is not harmful.

## Second blind-spot pass — the Extra Deck (never examined before)

Every earlier survey filtered `not c.is_extra`, so the Extra Deck had never been
looked at.  In a 2011 Synchro format that is a large omission.

### Fixed: the Extra Deck summon tax invented its own material count

`power._summon_tax` charged `max(2, round(level/2))` materials, so a Level 8
Synchro was billed for **four** and a Level 10 for **five**.  A Synchro Summon is
1 Tuner + 1-or-more non-Tuners — **two** cards whatever the Level; the material
*Levels* sum to the Synchro's Level, the material *count* does not.  Checked
against the text: of the Extra Deck cards that state a material line, **252 name
two materials and 23 name three; none names four or five.**

Now read off the parsed material clause (` + ` as the separator — the bare `+` in
"1 Tuner + **1+** non-Tuner monsters" is a quantifier), floored at 2.  Stardust
Dragon and Trishula go from −1.20 to **−0.40**.

Effect, measured: **era Spearman +0.7435 -> +0.7894**, all-format +0.4387 ->
+0.4854, deck AUC flat (0.9446 -> 0.9447), golden 20/20.

### NOT fixed, and the honest headline: the model cannot rank Extra Deck cards

AUC(played > unplayed) within the Extra Deck, model-only (evidence channel off):

| feature | AUC |
|---|---|
| `impact` | 0.578 |
| economy alone | 0.597 |
| **power alone** | **0.436 — anti-correlated** |
| `stat_eff` | 0.563 |
| raw ATK (trivial baseline) | 0.558 |
| Level | 0.507 |
| clause count | 0.533 |

Compare the other channels: main-deck monsters 0.638, spells 0.679, traps 0.677.

**The material-count bug was a real factual error but not the cause** — fixing it
moved `summon_tax` to a constant (AUC exactly 0.500, contributing nothing) and
`power` stayed at 0.436.  Something else in `power` is anti-correlated for Extra
Deck cards; `normal_summon_atk` and `searchability` are the obvious suspects
(a Synchro is never Normal Summoned and never searched), neither checked yet.

The deeper problem is that **no feature the model has separates a good Synchro
from a bad one**: Brionac appears in 95.4% of era decks and scores +0.02, and the
median played Synchro has 2500 ATK against 2400 for the never-played ones.  What
actually distinguishes them is effect quality on a free body, and economy prices
a Synchro as card-neutral by construction (two cards in, one out).

`_fill_extra` ranks the Extra Deck by `impact`, so the generator is choosing 15
of its 55 cards close to arbitrarily among reachable Levels.  **This is the
highest-value open item in the model.**

### Also examined, and not a defect

`_condition_mod` applies the worst trigger multiplier to *every* gain on a card
(526 cards).  Mostly correct — Goyo Guardian's take-control really is gated by
its battle trigger.  The narrow exception is a leave/destroy trigger that gates
only a **drawback**: Premature Burial's revival is discounted x0.65 by "when this
card is destroyed, destroy the equipped monster".  Fixing it needs clause ->
sentence association, which the parser does not retain.

## Gladiator Beast report (user-reported: Gyzarus seed, no Heraklinos)

The reported symptom had **four independent causes**, only one of which was the
stat model.  Card facts checked against the text first, per the sourcing rule —
both user claims held: Equeste's "add that target to your hand" is a real +1
(econ +1.26) and Laquari's "its original ATK becomes 2100" is on the card.

### 1. Stat scoring: percentile within Level bands (as proposed)

`StatBaseline` bucketed by **exact level AND `is_extra`**, so Gyzarus's 2400 ATK
was compared only against other Level 6 Extra Deck monsters — where it is
typical — and scored **−0.06**.  A body is only big relative to what it will
*face*, not to other cards sharing its Level and deck zone.

Replaced with a **percentile within bands 1-4 / 5-6 / 7+** (the real breakpoints:
Normal Summonable, one tribute, two tributes), merging extra and main.  Percentile
rather than z-score because ATK inside a band is lumpy and long-tailed, and the
old IQR-scaled z was floored at 400.

### 2. `nomi` was charged to Extra Deck monsters

"Must first be Special Summoned (from your Extra Deck) by shuffling the above
cards…" is how *every* Gladiator Beast Fusion works — it is the summoning rule,
not a drawback.  `power.tag_nomi` (−0.90) hit exactly the Extra Deck cards with
the most demanding, most powerful summoning text.  The real cost is already in
`summon_tax`.

| card | power before | after |
|---|---|---|
| GB Heraklinos (L8 3000/2800) | **−0.22** | **+0.93** |
| GB Gyzarus (L6 2400/1500) | **−0.42** | **+0.92** |

### 3. Contact Fusions required a Fusion spell they never use

**21 cards** — every GB Fusion, the XYZ-Dragon Cannon family, the Neos family —
carried `requires={'fusion_summon'}` despite their text saying "(You do not use
'Polymerization.')".  At `p_enabler = 4.00` per unmet requirement, Heraklinos cost
−4.00 in the very deck built to summon it.  See `text.parse._is_contact_fusion`.

### 4. `_fill_extra` left 11 of 15 slots EMPTY

The real reason Heraklinos was absent.  The two existing stages are
want-answering cards and *Synchros ranked by Level reach* — and a Gladiator Beast
deck has **no Tuners**, so stage 2 yielded nothing.  The deck shipped with a
**4-card Extra Deck**.

Added a fallback that tops up with Fusions the deck can actually assemble
(`_fusion_ready`: every material want answered by a card in the deck, plus a
Fusion spell unless it is a contact Fusion), **ordered engine-first then by
impact**.  Ranking it by impact alone filled the GB deck with Elemental HERO
Fusions — Absolute Zero (+3.04) beats Heraklinos (+0.54), and two stray HEROes in
the main deck were enough to qualify them.

Result: Extra Deck 4 -> **15 cards, with 3 Gyzarus + 3 Heraklinos**.  Gaiodiaz is
still correctly excluded — it needs Spartacus, which the main deck does not run.
A Synchro deck (Rekindling) still fills with Synchros: no regression.

### Honest limits

Golden 20/20; era Spearman +0.7894 -> +0.7892, deck AUC 0.9447 -> 0.9446 (both
flat).  **Extra Deck AUC barely moved: impact 0.578 -> 0.576, power 0.436 ->
0.442.**  Fixes 1 and 2 correct the *cross-zone* comparison — an Extra Deck card
no longer looks bad next to a main-deck one, which is what the report was about —
but they do not separate a good Synchro from a bad one, because after banding
they all sit high in the 5-6 / 7+ percentiles.  The item from the previous survey
stands: **nothing in the model ranks within the Extra Deck.**

## Extra Deck ranking + the anti-correlation (both closed)

Decomposed `power` per component over the era corpus.  The anti-correlation had
**one** cause, and the missing ranking signal was a different thing entirely.

### The anti-correlation was `searchability`  (AUC 0.402)

`power` added `w_searchability * log1p(idx.searchability(cid))` to Extra Deck
cards.  But **you never search the Extra Deck** — you Summon out of it by
material.  What `searchability` counts there is how many cards *name* this
Fusion, which is an **archetype lock**, not consistency, and it runs backwards:
a "HERO" Fusion that Miracle Fusion can name scored high and is playable in one
deck, while Brionac and Catastor — nameable by nothing, summonable by everything
— scored zero.  Now zeroed for `is_extra`; that component moved 0.402 -> 0.500.

### The ranking signal is material genericity  (AUC 0.701)

Candidate features tested against era play:

| feature | AUC |
|---|---|
| **materials name no card and no archetype** | **0.701** |
| is Synchro (vs Fusion) | 0.730 |
| economy | 0.597 |
| raw ATK | 0.558 |
| Level | 0.507 |
| number of tags | 0.486 |

`is Synchro` scores marginally higher but is an **era artefact** — 2011 is the
Synchro format — and hardcoding a card-type preference would not survive a
different pool.  Genericity is the mechanism underneath it and is not merely
is_synchro in disguise: the cross-tab has **17 generic Fusions and 26 locked
Synchros**.  A card's material line is already parsed into `wants`, so the test
is just "does any want carry an archetype or a specific card name".

New `power.w_extra_generic` (1.20), fittable with 0.0 in range.  **29% of the
Extra Deck cards played in the era are locked, against 69% of those never
played.**

### Measured

| | before | after |
|---|---|---|
| Extra Deck AUC — `power` | **0.442** (anti-correlated) | **0.583** |
| Extra Deck AUC — `impact` | 0.576 | **0.617** |
| main-deck monsters | 0.632 / 0.550 | 0.632 / 0.550 (untouched) |
| model-only era Spearman | +0.2116 | **+0.2236** |
| card-fit held-out Spearman | ~0.694 | **~0.744** |

Card fit: **no change reached the bar**, and `w_extra_generic` had 0.0 in range
and was **never chosen** — 3/5 kept 1.20 and 2/5 wanted *more*.  Golden 20/20,
deck AUC flat at 0.9446, ydc round-trip ok, Synchro decks unaffected.

### Still open

Ranking is better but not solved.  The top model-only Extra Deck picks still
include cards with 0 era plays (Neo-Spacian Marine Dolphin +2.12, Reptilianne
Hydra, Jurrac Meteor) — their parsed *economy* is high and nothing checks whether
the card is realistically castable or worth a slot.  Brionac (95% play) and
Catastor (97%) are still not top-10 on model reasoning alone.  The next lever is
probably economy: a Synchro's effect is priced as if it always resolves, with no
discount for needing the body to survive to use it.

## Extra Deck economy — my "survival discount" hypothesis was WRONG

I predicted the residual gap was economy pricing a Synchro's effect as if it
always resolves, with no discount for needing the body to survive.  Dumping the
cards said otherwise — two unrelated causes, neither of them survival:

### 1. Anaphoric noun phrases never bound to their antecedent

A generalisation of the earlier anaphora bug, and it cost the format's best card
everything.  "those cards" / "that target" / "them" parse into a Predicate that
is **non-None but empty**, so `self_ref` is False and `resolve_pronouns` — which
only rebinds `predicate is None` — skipped them.

**Brionac, in 332 of 348 era decks (95%)**, reads "target the same number of
cards your opponent controls; **return those cards** to the hand".  The bounce
kept an empty predicate and `side="you"`, `_gain_key` returned `None`, and it
scored econ **−0.00**.  Now **+0.52**.  See `parse._is_anaphor`.

### 2. `all`-count sweeps ignored how narrow their target is

"Destroy all monsters" and "destroy all face-up monsters **with 0 ATK** your
opponent controls" both resolved to the board prior of 2.2.  **Reptilianne
Hydra** — 0 era plays — was billed +2.20 of removal for a clause that hits almost
nothing and outranked Brionac and Catastor.  New `economy._board_breadth` /
`economy.all_narrow_factor` (0.45 per extra restriction), **board-bound counts
only**.  Hydra econ **3.20 -> 1.99**; Jurrac Meteor correctly unchanged at 2.65
("destroy all cards on the field" really is unrestricted); Dark Hole, Heavy Storm
and Mirror Force constrain nothing beyond class/position and are untouched.

This is the distinction that makes it safe where the earlier attempt was not:
applying breadth to a **fixed** count broke the axis convention and dropped
Smashing Ground to −0.19.  Applied to an **all** count it is just estimating how
many cards the sweep removes, which is what the count already means.

### Measured

| | before | after |
|---|---|---|
| Extra Deck AUC (model-only) | 0.617 | **0.622** |
| main-deck monsters | 0.632 | 0.633 |
| spell+trap | 0.679 | 0.675 |
| model-only era Spearman | +0.2236 | **+0.2241** |
| era Spearman (with evidence) | +0.7903 | **+0.7912** |

Golden 20/20, deck AUC flat at 0.9445.

**Small, and the top-8 list is still wrong**: Neo-Spacian Marine Dolphin (0 era
plays, and "cannot be Special Summoned except with NEX" — effectively
unsummonable) still leads at +2.12, because its `cannot_summon` tag is parsed but
priced at nothing.  That is the next thread: **a card the deck cannot legally put
on the field should not score at all**, and `tag_nomi` no longer applies to the
Extra Deck (correctly — see the Gladiator Beast section), so nothing catches it.

## Instant Fusion reserved illegal targets (user-reported)

Instant Fusion reserved Extra Deck monsters it cannot legally Summon.

**The line is NOT where the wording suggests, and my first attempt got it
wrong.**  Corrected by the user from play; three near-identical-looking phrasings
behave differently:

| wording | example | Instant Fusion? |
|---|---|---|
| "Must be Fusion Summoned and cannot be Special Summoned by other ways" | Mariner, Steam Healer | **CAN** |
| "cannot be Special Summoned **except with 'NEX'**" | Neo-Spacian Marine Dolphin, Twinkle Moss | cannot |
| "Must **first** be Special Summoned … by shuffling the above cards" | the Neos contact Fusions | cannot |

I initially keyed on "Must be Fusion Summoned", which wrongly locked Mariner —
the tag matched 152 cards; correctly scoped it matches **84**.  The real rule is
"only one named card can Summon it" **or** "must be properly Summoned its own way
at least once".

⚠ **Errata hazard, as CLAUDE.md warns.**  ygoprodeck gives Instant Fusion the
MODERN erratum "(This is treated as a Fusion Summon.)"; this 2011 engine has no
such clause.  Neither the text nor my reading of it settled this — **in-game
behaviour did**.

- New `summon_locked` tag (84 cards) for Extra Deck monsters bound to one named
  Summoner or to their own method.
- `search._legal_target_for` gates want-reservation on the **asker**, not the
  candidate — which is the whole subtlety: Mariner is a perfectly good
  *Polymerization* target and must stay reservable for a deck that runs one.
  `_proper_fusion_summoner` distinguishes a real Fusion Summon from a bare
  Special Summon out of the Extra Deck.

Verified: Instant Fusion reserves **Dark Balter the Terrible** (L5, unlocked)
where it previously took Mariner; Polymerization still reserves a locked card
(Chimeratech Fortress Dragon), which is correct.  4 of the 33 cards in Instant
Fusion's Level<=5 range were locked, two of them top-6 by impact — so this fired
often.

Golden 20/20; era Spearman +0.7912, deck AUC 0.9445, ydc round-trip ok, both
sample builds still fill 15 Extra Deck cards.

## The summonability gate — built, measured, and turned OFF

My own proposal: "a card the deck cannot legally put on the field should not
score at all."  Implemented in full, then **disabled on the evidence**.

Shipped and kept (all correct):

- **`_named_summoner`** — "cannot be Special Summoned except with **'NEX'**"
  becomes a want for that card.  Only a **quoted** name is taken: 22 of the 34
  matches for that sentence shape describe a *method* ("except by Tributing…"),
  not a card.
- A card with a named sole Summoner no longer also `requires` `fusion_summon`.
  Marine Dolphin comes down with NEX, never with a Fusion Spell, so requiring
  one made it **permanently** unsummonable — the want could be satisfied and the
  capability never could.
- **`DeckState.unsummonable_extra`** — verified on hand-built cases: Marine
  Dolphin alone 1 / with NEX 0; Heraklinos without its Gladiator Beasts 1 / with
  them 0.

### The borrow caveat (user-reported) — a 3x cut in false positives

A deck holding **Mind Control** (123 era decks) or **Creature Swap** puts the
*opponent's* monsters on your field, where they are legal Fusion / Synchro
material.  So "are this card's named materials in my deck" is the wrong question
for roughly a third of the format — Chimeratech Fortress Dragon off a borrowed
Cyber Dragon is the textbook case.

Wired through the existing capability machinery: a `take_control` /
`control_swap` clause now `provides` **`borrow_monster`** (43 cards), and both
`unsummonable_extra` and `search._fusion_ready` stand down on named *materials*
when it is present.  The named **sole Summoner** still counts — you cannot
borrow a NEX.  Verified: Chimeratech alone 1 / + Mind Control 0 / + Creature Swap
0; Marine Dolphin + Mind Control **1** (correctly still dead), + NEX 0.

### Measured, and the verdict

| version | tournament | ROM AI | deck AUC |
|---|---|---|---|
| with Synchro Level reach | 2.02 /deck | 0.41 /deck | 0.9238 |
| named requirements only | 0.73 /deck | 0.16 /deck | 0.9394 |
| **+ borrow caveat** | **0.24 /deck** | **0.14 /deck** | 0.9441 @1.50 |
| **off (shipped)** | — | — | **0.9444** |

The caveat was clearly right — false positives fell 3x and the wrong-direction
gap narrowed from 4.6x to 1.7x, taking the penalty from *harmful* to roughly
*neutral*.  It still does not **improve** deck ranking, so `p_unsummonable` stays
at 0.00.

What remains is the same class of thing the caveat fixed: real decks Summon
Fusions through routes the parser cannot see (Overload Fusion, Power Bond,
Chimeratech Fortress using Cyber Dragon from either field).

**Do not chase these one at a time — the tail is unbounded, and that is the real
argument for leaving the penalty at 0.00.**  Monster Reborn targets 1 monster in
*either* Graveyard, so it can revive the **opponent's** Tuner and reach a Synchro
Level the deck could never make from its own list; it is in **186 of 348 era
decks (53%)**.  Once a card that common invalidates the reach check outright,
"can this deck Summon this" stops being answerable from a decklist at all.  The
conservative version belongs where it already lives — `search._fusion_ready`, at
construction time, choosing what to put in rather than judging what is there.

**The caveat matters regardless of the penalty**, because `_fusion_ready` is live
at construction time: a deck running Mind Control can now put Chimeratech
Fortress Dragon in its Extra Deck, which it could not before.

The same logic *is* right at **construction** time, where conservatism is correct
because we are choosing what to put in rather than judging someone else's deck —
`search._fusion_ready` uses it and is what got Heraklinos into the Gladiator
Beast build.  Left wired and in `DECK_SEARCH_SPACE` so a future parser that
learns those Fusion routes can revisit it.

Final state: golden 20/20, deck AUC 0.9444, era Spearman +0.7912 (model-only
+0.2241), Gladiator Beast Extra Deck still 15 cards with 3 Gyzarus + 3
Heraklinos.

## Anti-seeds — `gen --anti-seed CARD [CARD ...]`

Cards that must never appear in a build.  Implemented as a **zero copy limit**
(`Limits.forbidding`) rather than as a filter in the search, because "0 copies
allowed" is a rule the whole pipeline already obeys — beam growth, bundle
auto-fill, the Extra Deck fill and fallback, bootstrap swaps and the
seed-holdout ranking all go through `legal_addition` / `max_copies`.  A new
filter would have to be threaded into all six and would silently miss the
seventh.  It is the same mechanism the ROM's Forbidden list uses.

Also guards a seed listed as its own anti-seed, which raises rather than
producing a deck that quietly ignores one of them.

**Two plumbing bugs it exposed, both of which made the first version a no-op:**

1. `generate` rebound its *local* `limits`, but `_grow` re-derives them from
   `opts.limits` — so the ban never reached the search and all three banned
   staples came back.  Now written back to `opts.limits`.
2. **Pre-existing:** `_bundled_marginal` built `Limits.flat(...)` instead of
   using the real ones, so **a bundle partner bypassed the Forbidden/Limited
   list entirely** — a card banned by the 2010.09 list could be dragged into a
   deck as somebody's bundle partner.  Now takes `limits` from its caller.

Verified: 6 staples banned -> **0 leaked**, 40 main / 15 extra, no violations;
banning the seed's own engine pieces (Flamvell Magician + Firedog) also leaks
nothing and still fills 40; clash guard raises.  Golden 20/20, ydc round-trip ok.

## Second perf pass — `synergy.pair` memo (28%)

Once the score loop was optimised, the profile moved: **`synergy.pair` was
200,065 calls and 2.22s of a 9.4s profile**, because `_prefilter` re-ranks the
whole pool at every step of every beam.  The answer depends only on the two
cards' parsed text and the pool, so it is the same every time.

Memoised on `(a.cid, b.cid, level_value is not None)`.  `level_value` is not in
the key beyond present/absent because it comes from `_level_value(cards)` /
`synchro_level_value(cards, play_rate)` — pure functions of the pool, so every
non-None value in a process is content-identical.  `best_partners` is the one
caller passing None, and that genuinely changes the result, hence the flag.

Verified equal to the uncached function over 8,000 random pairs (0 mismatches),
then timed with the cache cleared between runs so the comparison is fair:

| seed | uncached | memoised |
|---|---|---|
| Rekindling | 3.99s | **2.60s** |
| Hecatrice | 4.36s | **3.21s** |
| Gladiator Beast Gyzarus | 10.62s | **7.87s** |
| **mean** | **6.32s** | **4.56s** (−28%) |

### What is left, honestly

The profile is **flat** now — no hotspot above ~9%.  `deckscore.score` is 48% of
the build but only 0.75s of that is its own body; the rest is spread across its
terms.  Remaining candidates, all small:

- `_prefilter` (20%) could score the pool cheaply and add the `recent`-synergy
  refinement only to the leaders — the same two-stage trick used for playset
  sizes.  Worth less now that `pair` is memoised.
- `Scored.cid` is a `@property` called **1.65M** times; a stored field would
  shave ~0.3s of profile (~0.1s real).
- Startup is ~0.7s, of which `score_pool` is ~0.3s and could be disk-cached on a
  params hash.
- ~0.4s is Python interpreter start and imports, and is not recoverable.

Realistic ceiling is roughly 4.6s -> 4.0s for a fair amount of work.  **The
build-to-build spread is larger than that**: Gladiator Beast takes 7.9s against
Rekindling's 2.6s, because a 28-card archetype makes the engine phase run far
longer.  If worst case matters more than mean, `engine_max` and the engine-phase
cutoff are the lever, not further micro-optimisation.

## Banlists baked out of the ROM

`Limits.from_rom` opened the whole NDS image with ndspy, located `bin.pac`,
parsed the archive and decoded one entry **on every invocation** — 0.24s a run,
and a hard dependency on having the ROM present just to know that Pot of Greed is
Forbidden.

- New `bake_banlists.py` extracts all six lists in a single ROM pass to
  `data/banlists.json` (8 KB), recording the source ROM's SHA-1.
- `Limits.named(name)` reads the baked data; `Limits.available()` lists them.
- `Limits.from_rom` is kept as the source of truth the bake comes from, and as
  the fallback for a ROM whose lists were edited without re-baking.
- `gen --banlist` now has `choices`, so a typo is rejected with the six valid
  names instead of a stack trace.

Verified **all six match the ROM exactly** (per-cid dicts compared, 0
mismatches): limit200609 (95 entries), 200703 (100), 200709 (110), 200809 (113),
200909 (125), 201009 (132).  Load time 0.24s -> ~0.000s.

## CORRECTED + FIXED: the emit path could patch in the WRONG CARD

**My first diagnosis was wrong** — the user pushed back on it and was right.
Dupe Frog is not *missing* from the name table, it is **mislabelled**.

`konami_id_to_card_name.tsv` maps `0x1E6C -> "Des Frog"`, but 0x1E6C *is* Dupe
Frog; "Des Frog" appears three times (0x1918, 0x1E6C, 0x2269).
`CARD_NAME_TO_KONAMI_ID` is built by **inverting** that table, so duplicates
collapse, last one wins.  Same defect `namematch.py` already documents
("0x19BC is Proto-Cyber Dragon, not Cyber Dragon").

**Verified: `Card.cid` IS the Konami ID** — all 4,305 pool cards are keys of
`KONAMI_ID_TO_CARD_NAME`; 4,289 names agree, 16 are wrong.

### The serious part, found by chasing the correction

**30 pool cards have a name that resolves to a *different* cid.**  Most are
harmless alternate-art pairs of the same card.  One is not:

```
'Cyber Dragon' (cid 0x0F07) -> emits 0x19BC = 'Proto-Cyber Dragon'
```

A deck holding **Cyber Dragon** would have been patched as **Proto-Cyber
Dragon** — a different, much weaker card — **silently**, because the pre-flight
only checked whether a name was *present*, never whether it was *correct*.

### Fixed

- `emit.to_changes_entry` now emits `{"konami_id": cid, "card_name": name}`.
  The id is exact; the name rides along for readability only.
- `patch_bulk_ydcs.YDC.validate` accepts an int id or a `{"konami_id": ...}`
  dict as well as a name.  Names still work and a bad name is still rejected —
  the hand-written CHANGES table is untouched.
- `emit.round_trip_ok`'s last leg compared **bytes** after `decode_ydc` ->
  `encode_ydc`, which re-introduced the very name path its own docstring says it
  avoids: a deck holding Dupe Frog reported "re-encoding produced different
  bytes" on bytes that were perfectly correct.  Now compared at cid level, and a
  lossy decode leg is reported as a note rather than condemning a correct deck.

Verified: 55/55 entries resolve to their exact cid, Dupe Frog -> 0x1E6C,
`YDC.validate` accepts ids **and** names and still rejects unknown names, both
sample decks emit `ydc round-trip: ok`, golden 20/20.

### Also found: `patch_bulk_ydcs` does not import

Unrelated and pre-existing: the module builds `CHANGES` at import time and the
`Ghost RD?` entry (`rpg118_6_ghost_rd.ydc`) has **15 main-deck cards**, so
`YDC.validate` raises "Main deck must have between 40 and 60 cards" before the
module finishes loading.  Not touched — flagging it because it blocks any use of
that patch module.

## SUPERSEDED (wrong diagnosis, kept for the correction): "missing from the table"

`emit.to_changes_entry` rejects any deck containing a card absent from
`CARD_NAME_TO_KONAMI_ID`, and **16 of the 4,076 playable cards are absent**:

- mojibake names, as CLAUDE.md describes — `C? Chulainn the Awakened`,
  `Fiendish Engine ?`, `Machine Lord ?r`, `Falchion?`, the Meklord Emperors,
  the Reactor series;
- **clean names simply missing from the table** — `Dupe Frog`, `Harpie Queen`,
  `Ronintoadin`, `Proto-Cyber Dragon`, `Elemental Hero Neo Bubbleman`.

Not caused by this session's work — but this session's scoring changes made the
generator start picking **Dupe Frog** for the Rekindling deck, so
`gen --seed Rekindling --ydc ...` now exits 1.  ⚠ **Earlier "ydc round-trip ok"
results in this file predate that and were run on decks that happened to avoid
these 16 cards.**

Note the failure is easy to miss from a terminal: stderr is unbuffered and stdout
is block-buffered, so with `> file 2>&1` the traceback lands at the *top* of the
output, above the deck report.

Two ways forward, neither guessed here because the fix needs real Konami IDs:
add the missing entries to `CARD_NAME_TO_KONAMI_ID`, or have `cardpool` mark
unemittable cards unplayable so a generated deck is always patchable.  The
second is one line but silently drops legitimate cards (Dupe Frog is a real
Frog-deck staple), so it is the user's call.

## GY self-revival was worded the wrong way round for the tagger

User-reported via Ronintoadin scoring −0.79 in a deck built around it.
`recursion` / `self_ss` only matched "Special Summon … **from your GY**"; 11
cards state the zone **first** — "If this card is in your GY: … Special Summon
this card" — and were tagged inconsistently or not at all.  Plaguespreader Zombie
(66 era decks) and Glow-Up Bulb (54) carried only `tuner`; Ronintoadin and
Blackwing - Zephyrus carried **nothing**.

Now `gy_payoff` + `self_ss` + `recursion`, which is the right encoding of the
user's point — *being discarded or milled is upside, the card wants to be down
there*, and `gy_payoff` is what pairs with the deck's `gy_filler` in
`synergy_cycles`.

| card | era decks | impact |
|---|---|---|
| Plaguespreader Zombie | 66 | +2.94 -> **+3.28** |
| Glow-Up Bulb | 54 | +2.41 -> **+2.83** |
| Treeborn Frog | 41 | +1.48 -> **+1.90** |
| Ronintoadin | 8 | −0.79 -> **−0.37** |

Era Spearman +0.7912 -> **+0.7923**, golden 20/20.

### Still unmodelled: a free body as tribute/cost fodder

Ronintoadin is **still negative** (holdout −0.261).  The remaining half of the
user's point has no channel at all: a monster that Special Summons itself from
the GY for a resource the deck does not miss is **repeatable fodder** — for
Tributes, for costs, for anything that eats a body — and the model only ever
prices bodies by their stats and their summoning tax.  Its own text even says
"Cannot be used as a Synchro Material", so the value is explicitly in *being
spent*, which is the one thing nothing measures.

Would need a `power` term for "recurring zero-cost body", fed by the new
`gy_payoff`+`self_ss` pair on a monster whose revival cost is a GY resource.
Not built: it is a new channel and wants measuring against the era corpus, not
another coefficient added on reasoning alone.

## Every card now carries at least one tag

**1,503 of the 4,076 playable cards had NO tags** — 233 Normal Monsters, 579
Effect Monsters, 346 Spells, 345 Traps.  Anything reasoning over tags (the
deck-level channels, `mining.learn_tag_rates`, the randomiser fallback that
replaces per-cid play rate with per-tag rates) was blind to a third of the pool.

Structural tags now added from the card itself, after the text rules:
`vanilla` / `effect_monster` / `spell_card` / `trap_card`.  **0 cards are
tagless.**

`vanilla` is the notable one: it was declared in `power._TAG_KEYS`, priced at
**−0.30** in params.toml, and assigned to **zero cards** — a third dead
coefficient alongside `gain.negate_destroy` and `gain.opp_destroy_own`.  A Normal
Monster really is worth less than its stat line implies, and that is now charged
(Blue-Eyes White Dragon −0.86, Summoned Skull −0.64).

Measured — small but real, and on the metric that is *not* contaminated by the
play-rate lookup:

| | before | after |
|---|---|---|
| model-only Spearman, era | +0.2241 | **+0.2283** |
| model-only Spearman, all formats | +0.1996 | **+0.2021** |
| deck AUC | 0.9445 | **0.9448** |
| era Spearman (with evidence) | +0.7923 | +0.7924 |

Golden 20/20.  The other three tags are deliberately **not** in `_TAG_KEYS`, so
they describe without scoring — they exist so nothing has to reason about a card
that says nothing about itself.

## Mechanic tags from a text analysis — added, and the fit says they are worth 0

Asked for meaningful tags rather than perfunctory ones.  Method: list the cards
the **format actually plays** whose only tag was structural — 26 main-deck cards
in >=5 era decks — rather than mining n-grams, which came back dominated by
Synchro material boilerplate ("1 Tuner + 1 or more non-Tuner monsters") and told
me nothing.

Those 26 fell into five clean groups, now tagged **off the parsed clauses** so
they cannot drift from the economy model:

| tag | cards | played | examples |
|---|---|---|---|
| `spot_removal` | 383 | 76 | Catastor, Brionac, Stardust, MST |
| `hand_disruption` | 57 | 9 | Spirit Reaper, XX-Saber Gottoms |
| `token_maker` | 56 | 5 | Gorz, Dandylion, Scapegoat |
| `control_theft` | 43 | 7 | Brain Control, Mind Control |
| `banish_payoff` | 12 | 6 | Vayu, Return from the Different Dimension |

### The fit rejected all five, and that is the right answer

All introduced at **0.00** with 0.0 in the search grid.  5 seeds x 2 rounds:
**5/5 kept every one at 0.00**, held-out gain +0.0004 ± 0.0005.

That is not a failed experiment, it is the model's own design asserting itself —
params.toml's `[power]` note says *"Power must only score what economy CANNOT
see"*, and `spot_removal` **is** `gain.destroy_opp`, `hand_disruption` **is**
`gain.opp_discard`, `control_theft` **is** `gain.take_control`.  Paying for them
again would be the double-counting that once inflated the impact spread so far
that no synergy term could change a pick.

They are kept at 0.00 because they are still worth having: they make the pool
legible in the report, they are available to deck-level channels (which reason
over tag *counts*, not card economy), and `token_maker` in particular is the
feature a future "recurring body as Tribute fodder" term would key off — the
Ronintoadin thread above.

**Genuinely open:** `token_maker` (56 cards) and `banish_payoff` (12) are the two
NOT redundant with economy, and both have samples too small for this objective to
resolve.  If either is worth something it will show at the deck level, not the
card level.

## Card-by-card tags — and why the first fit said they were worthless

Read the 34 most-played era cards one at a time.  Three properties recur that
economy provably **cannot** see, because it counts cards and these are about
tempo and timing:

| tag | cards | played | what economy misses |
|---|---|---|---|
| `opponent_turn` | 169 | 38 | acts while the OPPONENT commits — 8 of the top 25 era cards; all priced as flat 1-for-1s |
| `free_body` | 210 | 46 | arrives without the Normal Summon, the one hard per-turn resource nothing models |
| `summon_answer` | 21 | 7 | stops a threat AS IT ARRIVES so its on-summon effect never resolves |

`summon_answer` lands on exactly the right seven (Torrential Tribute, both
Solemns, Bottomless, Thunder King Rai-Oh); Dark Hole correctly has no
`opponent_turn`.

### The measurement that matters

The card-level fit **rejected all of them, 5/5 at 0.00** — and that was an
artefact, not a verdict.  Its objective includes the evidence channel, where
`w_staple` (8.00) is a lookup of *the very play rate being predicted*.  Any tag
correlated with being played is redundant with the lookup, so the fit cannot
credit it.

Refit with `impact.w_evidence = 0`, i.e. asking whether the model's **own
reasoning** predicts play rate:

| coefficient | from | to | seeds |
|---|---|---|---|
| `power.tag_opponent_turn` | 0.00 | **+1.20** | **5/5** |
| `power.tag_spot_removal` | 0.00 | **+0.90** | **5/5** |
| `power.tag_summon_answer` | 0.00 | +0.90 | 3/5 |
| `power.tag_free_body` | 0.00 | +1.20 | 3/5 |
| `power.tag_banish_payoff` | 0.00 | +0.70 | 3/5 |
| `gain.negate` | 0.70 | +1.10 | 5/5 |
| `gain.negate_destroy` | 1.00 | +1.30 | 5/5 |
| `power.tag_floodgate` | 2.20 | +0.50 | 5/5 |
| `power.w_extra_generic` | 1.20 | +2.00 | 5/5 |

`control_theft`, `hand_disruption` and `token_maker` stayed at 0.00 across every
seed in **both** fits — they really are restatements of `gain.take_control` and
`gain.opp_discard`.

### NOT APPLIED — this is a decision, not a result

The two fits disagree because they answer different questions, and picking one is
a judgement call:

- ship-as-is (evidence ON) says 0.00, because the lookup already explains it;
- evidence-OFF says these tags are among the strongest signals in `power`.

Applying the evidence-off values while shipping with evidence ON would
**double-count**: a played card would collect the staple bonus *and* the tag
bonus.  The case for applying them anyway is that `score_pool` already has an
`altered` branch that discards per-cid play rate on a randomised ROM — and in
that mode the model has nothing *but* this reasoning.

Left at 0.00 with the numbers recorded.  Today has twice shown a unanimous 5/5
reversing under a different corpus or split, so this wants deciding
deliberately rather than by whichever fit ran last.

## Ruled out / corrected

- **"Charge every self-referential cost"** — wrong, and the scan proved it before
  any code shipped.  Dandylion's "Tribute Summon during the turn they are
  Special Summoned" parses as a self-tribute from the field; charging it would
  have cost a real card for a parser artefact.
- **"opener_consistency already covers the Hecatrice case"** — plausible and
  wrong.  It pools every starter and asks "did I open anything live", so three
  Hecatrice look identical to three unrelated Fairies that happen to search.  It
  cannot express "six of my forty cards produce Valhalla".

## Open / next

- The deck fit wants to collapse **exactly the confounded weights** the standing
  tension in params.toml is about (`w_want_scale 4.00 -> 1.00`,
  `w_archetype 2.00 -> 0.50`, `p_dead_advantage 2.00 -> 0.50`,
  `p_role_balance -> 0.00`, `w_tuner_reach 1.50 -> 0.50`).  ROM decks are
  mono-archetype and the tournament corpus is goodstuff, so these partly measure
  "is this a ROM deck".  **Do not write them on the strength of this AUC alone.**
- `power.w_searchability 1.00 -> 0.15` is *not* obviously confounded and is worth
  looking at on its own — but note it interacts with the new `search_access`
  term, which prices the same idea at the deck level rather than the card level.
- `deck.w_search_access` was not moved by the smoke run (stayed 3.00).  The
  multi-seed run is the real evidence.
- Still unfitted / untouched from the previous list: Ring of Destruction econ
  0.00, `board_reset` matching only 2 cards, `burn` at 157 tags, `combat_trick` /
  `battle_immune` breadth, the inert Hex-Sealed attribute gate.
- `access_score` writes `want.fetchers` as a side effect of scoring (for the
  report).  Harmless — wants are deep-copied by `clone()` — but `score()` is no
  longer strictly pure.
