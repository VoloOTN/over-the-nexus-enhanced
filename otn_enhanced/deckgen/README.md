# deckgen — generative deck builder for Over the Nexus

Builds a legal 40-card deck plus Extra Deck from a single seed card, by
**deriving** from card text the two things `power_ranking.py` had to hand-type:

- **what a card wants** — Rekindling's `FIRE monster, DEF == 200` is written on
  the card, so it is parsed, not typed;
- **how good a card is** — split into *economy* (net card advantage) and *power*
  (stats, summon cost, floodgates, protection).

```
uv run python -m otn_enhanced.deckgen.cli gen --seed "Rekindling"
```

## Commands

| command | what it does |
|---|---|
| `build-pool` | join `card_prop.bin` to real card text; prints join diagnostics |
| `parse [--unparsed N]` | parse all effect text, print coverage |
| `explain "<card>"` | economy + power breakdown for one card |
| `partners "<card>"` | best synergy partners, ranked |
| `top [--monsters\|--spells]` | highest-impact cards in the pool |
| `gen --seed "<card>"` | build a deck; `--ydc <file>` also emits a patch entry |
| `golden` | the ground-truth economy assertions |
| `validate` | the falsifiable checks against the 305 shipped decks |

`gen` flags: `--size 40`, `--beam N`, `--lam F` (fix synergy weight instead of
sweeping restarts), `--candidates N`, `--banlist limit201009` (off by default —
3 copies of anything), `--ydc <name> --out <path>`.

## How it works

**Pool** (`cardpool.py`, `namematch.py`) — `card_prop.bin` defines 4,305 cids;
4,076 are playable in a normal duel. Names resolve through exact match → the
konami TSV → `data/aliases.toml` → **an exact ROM-stat match**, which is how
every Over the Nexus pre-TCG translation (`Laval Twin Slayer` → `Laval Dual
Slasher`, `Crimson Mefist` → `Blood Mefist`) is recovered without typing a table.
4,072 playable cards end up with real effect text.

**Parse** (`text/`) — segments text into condition / cost / effect, extracts
clauses per verb, and turns target phrases into `Predicate`s. 90.9% of
effect-bearing cards yield at least one clause. Pronouns resolve to the
sentence's antecedent, so `"Target 1 Spell/Trap; destroy it"` is removal rather
than a card destroying itself.

**Economy** (`economy.py`) — `gains − costs − what it cost to play the card`,
evaluated on three *activation-conditioned* board states to give a
`(min, exp, max)` triple. It is context-free and cached; the deck-dependent part
rides on the card's `wants` and is paid out by `deckscore.context_payoff`.

**Power** (`power.py`) — deliberately scores only what economy *cannot* see.
`stat_eff` is a z-score against the pool median ATK for the card's level, so
"good stats" needs no table and reflects this ROM's 2011 pool.

**Search** (`search.py`) — beam search with restarts over `lambda_synergy`,
in four phases: monsters to 18–22, spells/traps to 40, Extra Deck by which
Synchro Levels the chosen Tuners can actually make, and bundles enforced
throughout.

## Tuning

Every coefficient is in `data/params.toml`. After any edit, run:

```
... -m otn_enhanced.deckgen.golden     # must stay green
... -m otn_enhanced.deckgen.validate.run
```

Tune against the **fit** half of the corpus only; report held-out numbers.

## Data files

| file | purpose |
|---|---|
| `data/params.toml` | every tunable coefficient |
| `data/aliases.toml` | name fixes the automatic resolver cannot reach (Spells/Traps only) |
| `data/bundles.toml` | "A is dead without B" pairs the *text does not state* |
| `data/golden.toml` | ground-truth economy assertions |

Most "dead without a partner" cards need no bundle entry: any card with unmet
wants is charged `penalty_orphan` automatically. `bundles.toml` is only for what
the text omits — Future Fusion never mentions Elemental HERO Absolute Zero.

## Known limitations

- **Effect text is modern errata over a 2011 engine.** ygoprodeck is the
  authoritative text source in this repo, but some cards behave differently
  in-ROM. Reports carry a warning; ROM stats always win over ygoprodeck stats.
- **Economy cannot see tempo.** Book of Moon and Shrink trade one card for no
  card advantage and score ≈ −1.0. That is correct on the economy axis and
  understates them in play.
- **Deck reconstruction is the model's weakest measured area** — see
  `validate/run.py`. It beats a no-synergy ablation decisively but only modestly
  beats a frequency-matched random deck on raw card overlap.
- 4 cards in the ROM have no confident real-card match; they stay in the pool
  with no text and fall back to the stat/power model.
