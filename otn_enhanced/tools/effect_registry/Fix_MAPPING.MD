 Problem 1 — the tribute bucket is false signal

  "tribute" matches Wattgiraffe because its text says
  "Tribute Summon this card... by Tributing 1 Spellcaster" —
  that's a summoning condition, not an effect. The bucket
  can't tell a cost/condition from an effect verb.
  
  Fix in ygo_tools/tools/effect_registry/infer_names.py, 
  _THEME_KEYWORDS (line 33): either delete the "tribute" line
  entirely, or narrow it so it only matches a tribute
  effect, not "Tribute Summon"/"Tributing". If you keep it,
  the realistic phrasings for an actual tribute-as-cost
  effect are things like "tribute 1", "by tributing" — but
  those also appear in summon conditions, so I'd just delete 
  it. Same latent trap exists for "special summon" (matches a
  card whose condition is "cannot be Special Summoned"), but
  that one's rarer; your call whether to guard it.

  If you want to keep tribute but exclude the
  summon-condition phrasing, the bucket would need negative
  matching (skip when the surrounding text is "tribute
  summon" / "tributing N ... monster"), which is more
  machinery than it's worth — deletion is cleaner.

  Problem 2 — shared-handler themes mislabel the individual 
  card

  This is the bigger one. destroy on Wattgiraffe came from
  its main_handler (0x0221E0F4), a dispatch routine shared by
  6 cards; the majority mention destroy, so the handler is
  tagged destroy — but Wattgiraffe doesn't destroy anything.
  A shared handler's theme describes its caller pool, not any
  one card.

  The shim generator currently builds a card's Themes: header
  by unioning the themes of its handlers
  (gen_card_shims._card_summary). That's the bug: it
  attributes pooled-handler themes to the individual card.

  Fix in ygo_tools/tools/gen_card_shims.py, _card_summary:
  derive the card's themes from its own effect text, not its
  handlers. You already have everything needed:

  - reg.text_of(cid) → (name, desc) for the card itself (now
  correct after the join fix).
  - infer_names.text_themes(desc) → themes of a single text
  string.

  So replace the handler-theme union with:
  from ygo_tools.tools.effect_registry.infer_names import
  text_themes
  txt = reg.text_of(cid)
  themes = sorted(text_themes(txt[1])) if txt else []
  That gives Wattgiraffe tribute (from its own text — which
  Problem 1's deletion then removes) and nothing about
  destroy, because its text never says destroy.

  Keep the Uses: line as-is — named primitives are real,
  code-side facts and aren't affected.
  
  What you do NOT need to touch

  - load_card_text — already fixed (header=0, desc boundary
  scan). Leave it.
  - handler.themes / handlers_by_theme — these are
  legitimately "themes of the cards that use this handler"
  and are documented as advisory/caller-derived. The mistake
  was only the shim header presenting handler-pool themes as
  the card's own. If you'd rather, rename the handler field
  to caller_themes to make that unambiguous, but it's not
  wrong.

  After editing

  Regenerate both artifacts and re-run tests:
  uv run python -m
  ygo_tools.tools.effect_registry.gen_registry
  data/over_the_nexus/working/rom.nds
  uv run python -m ygo_tools.tools.gen_card_shims
  data/over_the_nexus/working/rom.nds
  data/over_the_nexus/shims
  uv run --with pytest python -m pytest tests/ -q
  Then spot-check: Wattgiraffe's shim header should show no
  destroy, and (after deleting the tribute bucket) no tribute
  either — leaving Themes: (none inferred), which is the
  honest answer for a lockdown effect none of the buckets
  cover.

  One thing to decide:
  test_primitive_names.py::test_text_themes_classify_keywords
  doesn't assert tribute, so deleting the bucket won't break
  it — but if you keep a tribute test anywhere, drop it too.
