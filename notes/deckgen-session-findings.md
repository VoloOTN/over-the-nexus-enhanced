# deckgen — session findings (2026-07-28)

Generative deck builder (`otn_enhanced/deckgen/`). This session closed a set
of modelling blind spots, retrained, and added two refinement/validation tools.

Ground rules that held all session: **card text comes from
`scratch/ygoprodeck_cache.json`, never from recall** (violated it three times —
Hex-Sealed Fusion's restriction, Mist Wurm/Gottoms Levels, Debris Dragon's
partners — and was wrong every time), and `golden.toml`'s 14 assertions gate
every change.

## Confirmed / landed this session

### Parser + model coverage
- **Recovery to hand** — `return X to your hand` was matched by no rule (the
  bounce rule only accepted "the"/"its owner's" hand). Dimensional Alchemist
  scored −0.00. Now a `search`; 14 cards affected, no false positives.
- **Synchro material restrictions** (`material.py`, new) — 9 rules decoded
  (Debris Dragon Dragon-only + no Level 4 partner, Torapart, Chain Dog,
  R-Genex Oracle, Majestic Dragon, Blackwing-Breeze, Scrap Chimera/Soldier,
  Ronintoadin). Wired into `reachable_synchro_levels()` (partner bans) and
  `_extra_candidates` via new `DeckState.summonable_synchros()`.
- **Fusion Summoning** — was completely unmodelled. `_fusion_materials` reads
  the material line; **138/147** Fusions now carry derived material wants.
  Fusion Monsters `requires={'fusion_summon'}`; the Fusion spells `provides` it.
  Absolute Zero now *derives* `['1 "HERO" monster', '1 WATER monster']` — the
  bundle that used to be hand-written.
- **Fusion substitutes** — 8 found (King of the Swamp, Versago, Beastking,
  Goddess with the Third Eye, Mystical Sheep #1 (hyphenated "Fusion-Material"),
  3x Hex-Sealed). Unioned into name-based material wants.
- **Ritual Summoning** — 26 monsters detected, 25 carry `requires`;
  28 Ritual Spells provide. Binding derived from the quoted name.
- **`_fill_extra`** — three coupled bugs: `DeckState.add()` returned early for
  extra cards *before* want accounting; `_count_matching` ignored the Extra Deck;
  `_extra_candidates` filtered on `is_synchro` so Fusions were never candidates.
  Now reserves want-answering Extra cards (restricted to wants only the Extra
  Deck can answer) *before* the Synchro reach fill.
- **Other new signal**: `gy_denial` (5), `deckout` (5), `burn` (157),
  `flip_effect` (96), `level_mod` (21), `self_ss` (**165** — was barely firing),
  `atk_scaling`, `board_reset` (2), combat tags, `control_swap`, `draw_denial`,
  `spin`.
- **Karma Cut fix** — "banish all cards with the same name" hit the board-prior
  path and billed **2.2 monsters**; econ +1.52 → +0.20. `same name` is the only
  reliable marker (the target capture stops before "from your opponent's GY").

### Training
- `SEARCH_SPACE` / `DECK_SEARCH_SPACE` extended with everything added this
  session, **zero in every new range** so the fit can reject features outright.
- Method is **coordinate descent over a hand-authored discrete grid** — greedy,
  order-dependent, blind to interactions, ~260 evaluations.
- **Neutral-base multi-seed (5 seeds) is the trustworthy run**: held-out
  **+0.0217 ± 0.0062, 5/5 positive**. The earlier incumbent-based run
  (+0.0017 ± 0.0016, 3/5) was biased — base was seed 1's own output.
- **Unanimous across 5 neutral seeds** (safe): `control_swap 0.70`,
  `draw_denial 1.10`, `recurrence 1.00`, `tag_battle_immune 0.40`,
  `tag_battle_removal 0.90`, `tag_board_reset 1.00`, `w_searchability 1.00`,
  `w_stat 0.30`. **The combat channel is the best-evidenced thing added.**
- **Applied this session:** only `tag_floodgate 0.50 -> 2.20` (4/5 seeds; the
  0.50 was the lone minority answer). The other eight already matched.
- `self_ss_tax_relief` 1.00 -> 0.35 — robust (every seed 0.35–0.60). Its old
  value had been fitted while the `self_ss` tag matched almost nothing.

### Refinement tools (new)
- `seed_holdout` — strip each seed, ask what the deck now wants most.
- `bootstrap(rounds)` — leave-one-out refinement. Evaluates **all** swaps,
  walks them best-first, takes the best **allowed** one. A swap is allowed if
  `theme_delta >= -deck.bootstrap_theme_tolerance` (0.25) **or** it reduces the
  `penalty_role_balance` gap. Seeds are protected. CLI: `--bootstrap N`,
  `--no-holdout`.
- Demonstrated working: found `Darklord Asmodeus -> Debris Dragon` at
  **theme +1.64**, a thematic upgrade that the earlier halting version hid
  beneath a staple.

## Ruled out / corrected

- **"Extra Deck cards in the main deck"** — did not happen. The block was the
  Extra Deck section, proven by perfect ascending Level order (6,6,6,6,6,9,9,9,
  10,10) which only `_fill_extra`'s renderer produces. Report headers now carry
  card counts. A hard guard was added in `emit.deck_cids` regardless.
- **"1,046 cards with clauses but no tags/wants is a gap"** — mostly wrong.
  It is MST, Bottomless, Book of Moon et al. scoring econ 0.00 correctly.
- **"The fit rejected `tag_combat_trick`"** — wrong. Neutral-base seeds give
  `[0.0, 0.25, 0.0, 0.0, 0.8]`, sd 0.31. The corpus cannot tell.
- **Target breadth in `economy`** — implemented, then reverted. It broke the
  axis's defining convention (Smashing Ground fell to −0.19 and failed golden).
  Breadth is real but is **not card advantage**; `_breadth()` is retained in
  `economy.py`, unused, for a move into `power`.

## Next session — priority order

1. **The Hecatrice family (highest value).** Self-discard is **not charged**:
   "discard this card" is a self-reference and produces no cost clause, so
   Hecatrice reads as a free +0.95 search. Two errors cancel — economy is
   overstated ~1.00, and the real value (consistency) is unmodelled. Fix both:
   charge the self-discard (econ -> ~0.00), then credit **effective copy count**
   of a search target in `hypergeom` (Hecatrice makes Valhalla 6 copies, not 3;
   P(open) 34% -> 58%). Same idea as `deckstate.thinning`. Generalises to
   Sangan, Stratos, Dandylion — the glue of real decks.
2. **Candidate-pool bug in `bootstrap` / `seed_holdout`.** Both use
   `top 200 by raw impact`. Hecatrice (impact +1.16) is not in it, so holdout
   reported "NOT competitive" for a card the deck is visibly built around — a
   false negative **by construction** for every engine piece. It also means
   bootstrap can only swap *in* staples, which is part of the drift we fought.
   Build the pool with seed affinity + want satisfaction, as the search does.
3. **Deck-level AUC fit.** `cli train` only runs `SEARCH_SPACE` (card-level
   Spearman). `DECK_SEARCH_SPACE` — `p_role_balance`, `interaction_min/max`,
   `p_gy_denial`, `w_deckout`, `w_burn`, `w_flip_cycle`,
   `bootstrap_theme_tolerance` — is **still unfitted**. Critically,
   `impact.w_power` is at **0.80** from the card-level fit, which is exactly the
   trap params.toml documents (deck-level AUC 0.393, anti-correlated). Revert to
   ~0.10 or fit it properly.
4. **Training method improvements** (cheap, high value): multiple seeds by
   default with mean ± spread; randomise parameter order per round (dict order
   currently disadvantages newly-added params); raise the `1e-6` acceptance
   threshold so it stops chasing noise; joint pass for `w_power`/`w_economy`,
   which are a ratio and cannot be resolved axis-aligned.
5. **Left unstable, do not apply single-seed results**: `tag_combat_trick`,
   `tag_nomi`, `tag_atk_scaling`, `tag_protection`, `impact.econ_scale`.
6. **Unverified / unfinished**
   - `fills-gap` branch in bootstrap is **written but never exercised** — needs
     a deck that opens under `interaction_min`.
   - **Ring of Destruction** (362 corpus plays) still reads econ 0.00 despite
     being removal + burn. Never traced.
   - `board_reset` matched only **2** cards; Cyber Jar / Morphing Jar #2 likely
     missed. Fiber Jar still scores impact −0.90.
   - `burn` at 157 tags still looks loose.
   - `combat_trick` (98) and `battle_immune` (94) probably over-broad — they may
     be catching Battle-Phase *timing* language.
   - Hex-Sealed partner-attribute gating in `material.py` is **inert** (matches
     zero cards — their text says "must be correct", no Attribute clause).
     Consider deleting.
   - Whether the 7 non-King substitutes can replace a *descriptor*
     ("1 WATER monster") vs only a named material is an **unresolved ruling**.
   - Triple-material Fusions: repeated materials weight `1 + 0.5*(n-1)`, and one
     substitute marks the whole want satisfied (known overcount).
   - Spurious duplicate `target` clause generated by the spin rule on PWWB.
7. **Known-open from earlier sessions**: `summon_cheat` refund is
   all-or-nothing per card (no draw-probability weighting); conjunction wants
   aren't balance-weighted (Chaos Sorcerer's LIGHT/DARK halves both read "OK");
   `seed_affinity` over-permissive (2,562 of 4,076 "strongly related").

## Standing tension (unresolved, deliberate)

Fitting deck quality drives concentration/synergy weights to zero. This is
**confounded**: ROM decks are mono-archetype, the tournament corpus is mostly
goodstuff, so concentration partly measures "is this a ROM deck". Intermediate
values are kept deliberately; do not let a fit collapse them without saying so.
