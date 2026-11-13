# Writing a custom effect with the effect registry

> **Correction (read first).** The worked example below was written when `0x021D2584` was believed to be
> `special_summon_from_deck`. It is not: it is the **turn-log post** `(side, cid, kind, 0)` (KB fact
> `dispatch.turnlog_once_per_turn_pair`), and `PRIMITIVES["special_summon_from_deck"]` (`0x021D1AFC`) was the middle
> of a function. The registry names are fixed. So the example's claim that Giant Rat's handler "special summons
> from the Deck" via that call, and its `call("special_summon_from_deck", side, cid)` step, **do not work**. The real
> Special Summon engine is `0x0226925C` and takes a stack protocol (`cards/w_nebula_meteorite.py`, `SS_ENGINE`), not a
> plain `(side, cid)`. The method (find a donor, read its calls through the registry, author with `EffectBuilder`)
> still stands; the SS-specific steps need rewriting from a proven Special Summon implementation.

This walks through authoring a brand-new card effect end to end, using the
**effect registry** to discover how the engine already does each piece, then the
**`effect_builder`** stack to emit the Thumb-1 bytes.

Worked example:

> **"When this card is Normal Summoned: Special Summon 1 Level 3 Fiend from your
> Deck or hand."**

The registry does not write the effect for you. It is a *navigator*: it answers
"which real card already does this?", "what engine routine performs the
sub-action?", and "what does that routine's caller look like?" You assemble the
answer with `EffectBuilder` / `ThumbAssembler`, then validate and inject it the
same way the finished patches do.

> New to the injection mechanics (cls tables, the overlay-5 cave, the Thumb-1
> rule)? Read `finished_patches/HOWTO.md` first — this guide assumes it.

---

## The loop

1. **Find a donor** — a real card whose trigger + action match yours.
2. **Read its effect** through the registry to see which primitives it calls.
3. **Name the primitives** you'll reuse (add them to `effect_builder.PRIMITIVES`).
4. **Author** the resolver with `EffectBuilder`.
5. **Validate** with `effect_verify`, then wire it into a patch.

---

## 1. Find a donor

Our effect has two halves: a **trigger** ("when Normal Summoned") and an
**action** ("Special Summon a monster from the Deck"). Search the registry for a
card that already pairs them.

```python
from ygo_tools.tools.effect_registry import load_registry

reg = load_registry()

# Which cards Special Summon from the Deck? special_summon_from_deck is a named
# primitive; ask the registry who calls it.
ssd = reg.primitive(0x021D2584)            # special_summon_from_deck
print(ssd.display, ssd.call_count)         # -> special_summon_from_deck 119
print(len(reg.callers_of(ssd.addr)))       # -> 116 distinct handlers
```

`Giant Rat` is the cleanest match — a Normal monster that, when it leaves, SSes a
matching monster from the Deck. Read its effect:

```python
giant = reg.card_by_name("Giant Rat")      # cid 0x1333, table index 62
for slot, addr in giant.slots.items():
    h = reg.handler(addr)
    calls = [reg.primitive(t).display if reg.primitive(t) else hex(t)
             for t in h.calls]
    print(f"{slot:16s} 0x{addr:08X} {h.size:3d}B  {calls}")
```

```
main_handler     0x0220DFBC  48B  ['special_summon_from_deck', 'notify_summon_event', 'ov+0x0C55AC']
activation_cond  0x021F3B94 120B  ['ov+0x0AED18', 'count_matching_in_deck']
target_filter    0x021E50DC 146B  ['ov+0x109694', 'ov+0x0AC9E0', 'get_phase_info', ...]
```

That tells us the shape of the answer **before we write a line**:

- `main_handler` performs the action: `special_summon_from_deck` + a
  `notify_summon_event`.
- `activation_cond` gates it with `count_matching_in_deck` (don't offer the
  effect if the Deck holds no valid target).
- `target_filter` decides which Deck cards qualify.

The slot model (which cls table each handler lives in, and the
trigger-registration that fires it) is covered in `HOWTO.md §6–9`. For an
*on-Normal-Summon* trigger you adopt a donor that already registers that event
(see HOWTO's discussion of the summon-trigger registries) and only replace the
slot handlers below.

## 2. Read the building blocks you need

The action is `special_summon_from_deck`. The filter ("Level 3 Fiend") is two
property checks. The registry already has primitives for both halves of the
filter:

```python
reg.primitive(0x0202ABD8).display   # -> 'cid_level'   (returns a cid's Level)
reg.primitive(0x02029E60).display   # -> 'is_monster'  (used by Reasoning etc.)
```

For the **race** check (Fiend), find the routine a known race-filtering card
calls. Pull a card that filters by type and inspect its `target_filter`:

```python
# A type-restricted searcher's filter will call the engine's race/type getter.
# Use primitives_by_frequency() to see the candidates, ranked by how heavily
# the engine reuses them — the busiest unnamed overlay routine in a filter slot
# is almost always the property getter.
for p in reg.primitives_by_frequency()[:30]:
    print(f"{p.call_count:4d}  {p.display:24s} 0x{p.addr:08X}")
```

Pick the routine, confirm it by reading two or three other filters that use it
(`reg.callers_of(addr)` → the handlers, then look at the cards via
`reg.cards_using_handler`), and you have your race getter's address.

> The registry gives you **addresses and call frequency, not signatures**.
> Confirm argument order by reading how existing callers set up `R0..R3` before
> the call — `lift_handler_to_builder(overlay, addr)` (from `effect_shim`)
> prints the surrounding instructions.

## 3. Name the primitives you'll reuse

`effect_builder.PRIMITIVES` ships with the handful proven in patches
(`draw`, `reveal_top`, `is_monster`, `cid_level`). Add the ones this effect
needs, sourcing addresses from the registry:

```python
from ygo_tools.tools.effect_builder import Primitive, PRIMITIVES

PRIMITIVES["special_summon_from_deck"] = Primitive(0x021D2584, "(side, cid)")
PRIMITIVES["cid_race"]                 = Primitive(0x0XXXXXXX, "(cid) -> race")
# (use the race-getter address you confirmed in step 2)
```

Each entry you promote here is reusable by every future effect — this is how the
registry's 921-primitive catalog gradually becomes a named vocabulary.

## 4. Author the resolver

Now write the effect with `EffectBuilder`. The structure mirrors Giant Rat:
the resolver picks a valid Deck/hand monster and Special Summons it; a separate
condition handler gates activation.

```python
from ygo_tools.tools.effect_builder import EffectBuilder, R0, R4, R5

FIEND_RACE = 0x...    # the Fiend race value (from game_constants.ERA2_RACE_MAP)

def build_resolution(base: int) -> bytes:
    b = EffectBuilder()
    b.prologue(save=[R4, R5])
    side = b.ctx_field("controller", dest=R4)        # who is summoning
    # ... choose a candidate cid (a menu/builder call, as Giant Rat does) -> R5
    cid = R5
    # filter: Level == 3 AND race == Fiend  (skip to a reject label otherwise)
    b.call("cid_level", cid)
    b.if_ne(R0, 3, "done")
    b.call("cid_race", cid)
    b.if_ne(R0, FIEND_RACE, "done")
    b.call("special_summon_from_deck", side, cid)    # the action
    b.label("done")
    b.epilogue(ret=0)
    return b.assemble(base)
```

When a sub-action has no named primitive yet, call it by address:
`b.call_addr(0x021D6E40, side)`. Labels (`"done"`) replace hand-computed branch
offsets; `ldr_const` / pool words are placed automatically. See
`HOWTO.md §9` for the full vocabulary and the `peek-before-async-draw` pattern.

> **Reality check on scope.** The hard part of a Deck/hand Special Summon is
> *candidate selection* — the menu/builder that lets the player pick the target.
> Real cards delegate that to engine routines (Giant Rat's
> `target_filter` + the deck-search builder). The registry is how you find those
> routines and a donor whose selection framework you can keep verbatim (the
> Pattern-A "transplant" in HOWTO), customizing only the filter — exactly what
> `patch_gravekeepers_recruiter` does for a two-criteria search.

## 5. Validate, then wire it in

Guard every authored stub before it touches a ROM:

```python
from ygo_tools.tools.effect_verify import assert_thumb1_only

stub = build_resolution(cave_addr)
assert_thumb1_only(stub, cave_addr)   # raises on movw/movt/cbz/b.w (HOWTO §11)
```

If your stub re-emits an existing handler (e.g. you cloned a donor's filter),
prove byte-fidelity against the ROM with
`effect_verify.verify_against_overlay(stub, addr, overlay, RAM_BASE)`.

Then install it into the overlay-5 cave and point the donor's cls slot at
`cave_addr | 1`, following `patch_mystic_piper.py` (single-resolver swap) or
`patch_gravekeepers_recruiter.py` (custom filter + cloned wrapper) as templates.

---

## Quick reference — registry calls used here

| Goal | Call |
|------|------|
| Look up a card by name / id | `reg.card_by_name("Giant Rat")`, `reg.card(0x1333)` |
| All entries for a repeated id | `reg.card_entries(cid)` |
| A card's per-slot handlers | `card.slots` → `{slot: addr}` |
| What a handler calls / its pool / card refs | `reg.handler(addr).calls / .pool / .card_refs` |
| Resolve a call target's name | `reg.primitive(addr).display` |
| Most-reused engine routines | `reg.primitives_by_frequency()` |
| Named routines at a confidence tier | `reg.primitives_by_confidence("known" / "proven")` |
| Handlers tagged by a card-text theme | `reg.handlers_by_theme("special_summon")` |
| A card's English effect text | `reg.text_of(cid)` |
| Which handlers call a routine | `reg.callers_of(addr)` |
| Which cards use a handler | `reg.cards_using_handler(addr)` |

> **Names are tiered by confidence.** `primitive.confidence` is `"known"`
> (from `KNOWN_SUBROUTINES` / `PRIMITIVES`) or `"proven"` (used in a shipped,
> in-game-tested patch). Unnamed routines have `confidence = None`. A handler's
> `themes` are *advisory* — inferred from the effect text of the cards that use
> it (`theme_evidence` = how many had text), describing its callers, **not** the
> routine's true function. Never treat a theme as a verified name.

Regenerate the registry data after a ROM/overlay change:

```sh
uv run python -m ygo_tools.tools.effect_registry.gen_registry \
    data/over_the_nexus/working/rom.nds
```
