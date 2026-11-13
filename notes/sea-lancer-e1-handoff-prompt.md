# Handoff prompt — Sea Lancer E1, step 2

Paste everything below the line into a fresh session.

---

Continue work on **Sea Lancer** in the Over the Nexus ROM. Specifically: **E1, step 2 —
establish what the five cls record slots actually do.** Do not build anything yet.

## Read these first, in this order

1. `CLAUDE.md` — rules of engagement.
2. `otn_enhanced/docs/engine/README.md`, then run
   `.venv-1/Scripts/python.exe -m otn_enhanced.knowledge.verify_knowledge`
   (expect ~109 facts, 0 FAIL). The YAML is the source of truth; where it and any note
   disagree, the YAML wins.
3. `notes/sea-lancer-findings.md` — the full evidence trail for this card. Read the whole
   thing; it contains a retraction you must not undo.

## Where the card stands

Donor is **Mermaid Archer, cid `0x1FFC`** (keep-cid). `patch_sea_lancer.py` is shipped and
registered in `apply_all_patches.py`.

- **E3** (+1000 ATK while equipped) — DONE, in-game confirmed. A 4-byte overlay-3 retune at
  leaf `0x021B75F8`. Do not touch; `verify()` guards it and its look-alike twin `0x021B7246`.
- **E2** (destroy an equipped card instead of this card) — DONE with **no code change**; the
  donor's native effect already is Sea Lancer's wording. Do not touch.
- **Reskin** — DONE: Lv5 / WATER / Beast-Warrior / 1300 / 1000, name + desc.
- **E1** — NOT DONE. She still runs the donor's selector, "target 1 face-up Level 3 or lower
  monster **you control**", instead of "target your **banished** Fish / Sea Serpent / Aqua
  monsters; equip them to this card".
- Card art is still Mermaid Archer's (cid `0x1FFC` is not in `patch_card_art.py`).

Scope already agreed with the user: **v1 is 1-at-a-time**, not "any number". Race ships as
**Beast-Warrior**.

## What is already VERIFIED (do not re-derive)

- `ram.container_for_zone_code` — `0x0219CA28(r0=side, r1=zone_code, r2=index)` returns a
  pointer to one packed u32 card word. `0x0B` recent-summon list (`player+0x124`), `0x0C`
  Extra Deck (`+0x4E4`), `0x0D` Deck (`+0x304`), `0x0E` Graveyard (`+0x55C`),
  **`0x0F` banished (`+0x7B4`)**; anything else = zone records at `player+0x34 + code*0x14`.
  **E1's parameter is `zone_code = 0x0F`.**
- `ram.graveyard_and_banished_arrays` — banished = `player+0x7B4`, count `player+0x1C`;
  GY = `+0x55C`, count `+0x14`. Packed arrays (exactly `count` leading nonzero words).
- `ram.card_instance_record` — stride-0x28 records in the `0x0229 6xxx` heap: cid `+0x0C`,
  effective ATK `+0x20`, Level `+0x24`, live only while face-up on the field.
- `dispatch.cls_tables` — **cid-FIRST**, stride 24, five Thumb callback slots at `+0x04..+0x14`:
  cls2 base `0x02275C04` count 697; cls0 base `0x0227E64C` count 1306; cls1 base `0x022860D4`
  count 1333.

## What was RETRACTED — do not resurrect

`dispatch.master_handler_row_layout` and `dispatch.cls_table_bases` are kept as UNVERIFIED
with `corrected_by`. They claimed one 4116-record table at `0x02275C08` with the cid at
`+0x14`. That is wrong by four bytes and it poisoned a whole round of analysis. Every
structural check passed under the wrong reading, so **cross-check table geometry against an
external anchor** — the shipped patches encode real ones, e.g. `patch_armory_arm.py` uses
`cls1[0x1F33] +04 = 0x022215DD` (that is cls1 record 938).

## Your task — step 2

Determine, with evidence, **what each of the five cls slots (`+0x04`..`+0x14`) does.** The
names in `data/over_the_nexus/decompiled/cards/*.py` (main / sub / activation_cond /
target_filter / resolution) are the decompiler's guesses and have **never been verified** —
treat them as unlabelled slots 1-5 until you prove otherwise.

Study set (already re-dumped with the correct geometry) — the banished selectors all live in
**cls0**, and three share the `0x2235604` slot-5 template:

| cid | card | record | slots `+04 +08 +0C +10 +14` |
|---|---|---|---|
| `0x1C95` | Release from Stone — select 1 banished **Rock**, Special Summon it | cls0[873] | `0x2207528`, —, `0x21F03B4`, —, `0x2235604` |
| `0x231A` | Unicorn Beacon — banished + **two-race** filter + level cap | cls0[1204] | `0x222FC44`, —, `0x22031B8`, —, `0x2235604` |
| `0x2012` | Psychic Path — banished + race + **up-to-2 multi-select** | cls0[1056] | `0x2208180`, —, `0x21F05A8`, `0x21E4D80`, `0x2235700` |
| `0x21EF` | Forgotten Temple of the Deep — the **Fish/Sea Serpent/Aqua** triple | cls0[1160] + cls1[1146] | `0x2208DB0`, `0x21E3CF0`, `0x21F0BA0`, `0x21E74A0`, `0x2235EBC` |

Note **Mermaid Archer `0x1FFC` and Genetic Woman `0x2081` have no cls record at all** — they
are records-free, which is why the donor's three clauses are cid-literal switches
(E1 `0x0225026C`, E2 `0x0225C3A6`, E3 `0x021B74B0`).

Good method: for each slot, count how many records share each pointer (a slot with few
distinct pointers is a template slot; a pointer used by exactly one record is bespoke), then
disassemble bespoke ones and check the behaviour against the card's known text. Confirm any
conclusion against a card whose text makes the slot's role unambiguous.

Then **step 3**: find the Fish/Sea Serpent/Aqua race predicate. Forgotten Temple of the Deep
`0x21EF` already implements exactly that triple ("target 1 Level 4 or lower Fish, Sea Serpent
or Aqua-Type monster you control; banish that target"). Its four code literals are
`0x0219F7F4` (loader `0x0219F5A4`), `0x021AE948` (`0x021AE92A`), `0x021E3D68` (`0x021E3D0A`),
`0x0224427C` (`0x02244238`). If that predicate is reusable, E1 gets its filter for free.

## Traps already hit this session — don't repeat them

- **A self-consistent structural story is not proof.** Anchor table geometry externally.
- **Query codes in `0x021A3054` / `0x021A30D0` are COUNTER TYPES**, not zone or race filters.
  The table at `0x0226D3FC` maps them to the counter-placing card's cid (Magic Reflector,
  Alien Grey, Ice Master, Venom Swamp, Cloudian - Ghost Fog, Card Guard, Speed World). Dead end.
- **Never quote card stats or text from memory.** Read `scratch/ygoprodeck_cache.json`. I
  asserted Mermaid Archer was Lv4 1400/1500 from recall — she is **Lv3 1200/200** — and it
  invalidated a whole RAM scan.
- **`thumb-stack-based-switch-footgun`**: register-only simulation of these cid switches has
  reported the wrong leaf. GDB is the arbiter.
- The donor's equip-target selector leaf `0x0225028E` builds a **10-bit slot mask** over
  `side 0..1 x zone 5..9` and hands it to `0x02251040`. That shape cannot address a
  variable-length list, so **E1 is not a parameter swap of that leaf** — it needs the list
  picker used by the cls0 banished selectors.

## Assets

- Savestates: `data/over_the_nexus/working/sealancer_recon.ml3..ml7` — `.ml3` Mermaid Archer +
  Deep Sea Diva both face-up unequipped; `.ml4` equipped; `.ml5` destroy-redirect prompt;
  `.ml6` post-destruction; `.ml7` Mermaid Archer banished. RAM0 file offset `0x24`.
  Pass one with `verify_knowledge --savestate`.
- GDB probes: `scratch/gdb_e3_leaf_probe.py` (single-connection, preflights overlay-3
  residency, always resumes) and `scratch/gdb_sea_lancer_leaves.py` (all four sites).
  **The melonDS stub desyncs if you connect repeatedly — do everything in ONE connection and
  do not "check if it's connected" first; that burns the trace window.**

## Rules

Keep `notes/sea-lancer-findings.md` updated as you go, not at the end. No speculative
build-test cycles — if the hook site isn't proven reachable, say `unproven` and name the
experiment. Contribute anything you prove to
`otn_enhanced/knowledge/author_facts.py` and regenerate with `--check`.
