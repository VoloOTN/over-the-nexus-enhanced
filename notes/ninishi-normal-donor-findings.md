# Ninishi -> Normal-Monster donor (migration off Dverg 0x245B)

Session 2026-09-10. Goal: move `patch_ninishi` from Dverg of the Nordic Alfar
(0x245B, a real Effect Monster) onto a records-free Normal Monster, the way
Boggart Knight / XX-Saber Darksoul / GK Recruiter were migrated. User chose the
expensive option: **keep Dverg fully working too** (a fifth granter arm, not a
retarget). Donor: **Dark Chimera 0x0FFD**.

STATUS: **DONE — all three clauses in-game confirmed by user 2026-09-10.**

- Clause 3 (Karakuri extra Normal Summon): confirmed on the round-2 single-card
  ROM ("The grant works now").
- Clauses 1 + 2: confirmed on the joined ROM `rom_ninishi_test.nds`
  (`_build_ninishi_test.py` = Maiden -> Haipa -> Ninishi). "Ninishi, must attack
  now"; position change confirmed after a follow-up — "ninishi works as expected.
  Changes to defense when in attack mode."
- Controls, same session, both clean: **Dverg** — "Dvergs summon is still valid -
  so are his other effects no regressions" (so CAVE_NS_FIELD's tail-call
  preserves his summoned-this-turn window); **Haipa** — "no regressions" (so
  Ninishi joining his shared MUSTATK_ADMIT list cost him nothing).

### Round 4 — clause 2 made SYMMETRICAL (2026-09-10, AWAITING IN-GAME TEST)

The user rejected the deviation below by quoting the card: "When this face-up
card is selected as an attack target, change its battle position." Fixed.

How the engine encodes the direction, all read this session:
- condition `0x021F4D4D` returns 1 iff the card is in ATTACK position; its mirror
  `0x021F4D99` returns 1 iff in DEFENSE (Reptilianne Naga 0x21B4, cls1[1130], is
  its only user).
- resolver `0x0220C6B1` sets r4 = 1 (target Defense), or r4 = 0 for Naga alone,
  and calls the flip primitive `0x021C5324` ONLY when r4 differs from the current
  position.
- that primitive takes **no target argument** — Naga reaches it from the DEFENSE
  gate with byte-identical constants and ends in Attack — so it is a TOGGLE, and
  the r4 compare IS the whole direction mechanism.

So a symmetrical card needs neither piece of directionality. Ninishi's cls1
record now points at two ov5 stubs: `CAVE_NIN_POSCOND` = `movs r0,#1` (the
disjunction of the two stock gates) and `CAVE_NIN_POSRES` = the stock resolver
minus the r4 compare (always toggle, same gates 0x021D2C1C / 0x021D2D18, same
primitive, same return 0). Both pointers carry the Thumb bit, like the odd stock
literals they replace.

### The deviation this fixed — was NOT acceptable, do not restore it

Printed: "When this face-up card is selected as an attack target, **change its
battle position**" — symmetrical. What ships flips **Attack -> Defense only**.
The cloned record's condition 0x021F4D4D is a face-up ATTACK Position gate that
returns 0 outright when the card is already in Defense, because the record comes
from Black Stego ("When this face-up **Attack Position** card is targeted for an
attack: Change this card to **Defense** Position"). A Defense-position Ninishi
being attacked therefore does nothing, which is almost certainly what the first
round-3 report ("does not change position when attacked") actually observed.
The engine CAN invert: the same resolver has a Reptilianne Naga 0x21B4 arm that
sets r4 = 0 (flip to ATTACK) instead of 1 — see
`battle.change_own_position_resolver`. Fixing the Defense -> Attack half means a
cid-scoped arm there. Left unfixed and flagged; the user has not been asked to
accept it as a deviation.

## Confirmed (this session)

- **The extra-Normal-Summon grant is pure DATA at four ov3 literal-pool words.**
  Full-overlay scan for the aligned u32/u16 0x245B (scratchpad/probe_grant.py)
  finds it at exactly 7 places; four of them are code literal pools. Every use
  is "the granter's cid" as a search key / rider key / descriptor stamp, so the
  grant is not Dverg-specific at all:
  - `0x021B9670` — pool of `0x021B95C4` ("which granter permits summoning this
    hand card"). Arm shape: archetype-predicate (skipped when r4 == 0 = "any
    card") -> granter-on-field `bl 0x021ABE4C` (`blt` = absent) -> spent-rider
    `bl 0x021A1430(side, 0xB, cid)` (`bne` = spent) -> return the granter cid.
    Arms: 0x20D6 Grunard/Ice Barrier, 0x2115 Swap Frog/Frog, 0x245B Dverg/Nordic.
  - `0x021B9FBC` — pool of `0x021B9EFC` ("is the extra Normal Summon spent"):
    a flat chain of the same rider query, one link per granter (0x12F3 Ultimate
    Offering, 0x1D35 Cry Havoc!, 0x1CA4, 0x209B Brain Research Lab, 0x20D6, 0x245B).
  - `0x02261F84` — the action state machine (0x02261D60..): one big arm per
    granter, selected by an archetype test, reading the granter cid THREE times
    (0x02261E62 / 0x02261E9A / 0x02261EE8); the last stamps it into summon
    descriptor +0x12.
  - `0x022651B4` — the consume path: compare descriptor +0x12 @0x0226515C, then
    the cid handed to the spent-rider set `bl 0x021D2584(side, cid, 1, 0)`
    @0x0226517C.
  - **A kind-0xB rider keyed by the granter cid == "this grant is spent this turn".**
- **Pool-reader count is CLOSED.** Every `ldr rX,[pc,#imm]` encoding in ov3 was
  decoded and resolved (scratchpad/poolrefs.py): the four pools have exactly the
  readers listed above and no others. This is what licenses site 3's stub
  writing the granter cid into pool 0x02261F84 at runtime — all three readers are
  downstream of the predicate that sets it, on every re-entry of the state machine.
- **Dverg's other three occurrences are its Nordic-Relic clause, not the grant:**
  cls2 record[667] @0x02279A8C, criteria row[1326] @0x022751EC, leave-mask
  row[140] @0x0226EE4C. All left alone now; PART A3 (the class0 strip) is gone.
- **Dark Chimera 0x0FFD is CLEAN** (`donor_scan 0x0FFD`): Normal Monster, Lv5
  DARK Fiend 1610/1460, no cls0-cls3 record, no criteria row, no leave-mask row,
  no list membership.
- **Blob length is a non-issue**: `card_text.rebuild_blobs` re-emits in index
  order, so the donor's 12 B name slot carries the full 34 B styled name.
  Verified on the built ROM: 0x0FFD reads `Karakuri Komachi mdl 224 "Ninishi"`
  and 0x245B is byte-identical to stock (`Dverg of the Nordic Alfar` + its
  original description).
- **Built + statically verified** (`patch_ninishi --verify`, all PASS): four
  hooks, four ov5 stubs (Thumb-1 asserted), cls1 graft on 0x0FFD with phantom
  0x1140 consumed and the table still 1333/sorted, Dverg's record + all four
  granter pools intact, ARM9 Karakuri table sorted with 0x0FFD, card_prop =
  Tuner Monster EARTH/Machine Lv3 0/1900. `check_allocations --emit` clean.

## Round 2 — the first build failed in-game (2026-09-10)

User report, verbatim: *"Okay there are quite a few regressions. 1) Ninishi's
attack if able isn't working 2) Ninishi didn't change battle position when
attacked 3) Ninishi didn't offer another normal summon."* Tested on
`rom_ninishi.nds` (the single-card build); Dverg was not tested.

- **Clause 2 was untestable in that ROM**, not regressed: it needs
  `patch_maiden_eyes_of_blue`'s shared attack-target gate hook, absent from a
  single-card build.
- **Clause 1 was never implemented, on either donor.** The cls1 record grafted
  by PART A6 is only the position change: Black Stego 0x1A78 carries the
  BYTE-IDENTICAL record and has no "must attack if able" clause. Nor is
  must-attack a cid list — 0x238B (Karakuri Ninja "Sazank") appears in no
  membership list anywhere in ov3, only in its own two cls1 records.
  **RESOLVED 2026-09-10 (user pointed at the precedent): it is already
  implemented in `patch_karakuri_haipa` PART E** — two ordered compare chains at
  0x0224D250 / 0x0224D530 that accept exactly the eight monsters printing the
  clause, reached by remapping a donor cid onto Nisamu 0x2388 at the shared cid
  getter `bl 0x021A36EC` (hooks 0x0224D254 / 0x0224D534, stub
  CAVE_HAIPA_MUSTATK). Both hook sites are single-site, so Ninishi joins that
  stub's `MUSTATK_ADMIT` list (now `(0x0FC8, 0x0FFD)`) instead of installing a
  rival stub — the same shape as maiden's `ATKTGT_ADMIT`. Ninishi's module
  contributes NO code for this clause, only list membership, and haipa's
  verify() asserts 0x0FFD stays listed.
  *(Lesson: the mechanism was already in the repo and I searched for it from
  scratch. Grep the shipped patches for the printed clause before concluding a
  mechanism is unfound.)*
- **Clause 3 WAS a real bug, and it is the interesting one. ROOT CAUSE FOUND
  AND FIXED: `0x021ABE4C` is not "is this cid face-up on the field".** After
  matching the cid and the alive/not-negated predicate `0x021A32B4`, it also
  requires `0x021A1430(side, SLOT, cid)` — a kind<6 node keyed by the card's OWN
  cid on its OWN slot — and skips the slot when that node is absent.
  MEASURED by executing it over the repo's 8 duel savestates
  (`scratch/ninishi_onfield_probe.py`): **-1 for every face-up monster in every
  state**, because no ordinary card carries such a node.
  That node is Dverg's printed window: *"**After you Normal Summon this card**,
  you can Normal Summon 1 'Nordic' monster during your Main Phase **this
  turn**"*. Grunard, whose text has no window (*"During your Main Phase, you can
  Normal Summon 1 'Ice Barrier' monster in addition..."*), uses `0x021AC0C8`
  instead — which the same probe shows returning 1 for every alive face-up
  monster. **Cloning Dverg's arm verbatim imported Dverg's timing gate**, and
  Ninishi (*"While this card is face-up on the field"*) is Grunard-shaped.
- **The fix**: `CAVE_NS_FIELD` — the native loop minus the node query for the
  donor cid, tail-calling native `0x021ABE4C` for every other cid so Dverg keeps
  its window. Every `bl 0x021ABE4C` in the granter machinery (0x02261E68,
  0x02261EA0, 0x02265164, plus the site-1 stub's own call) now goes through it.
  **Proven by execution, not inspection**: built for each board's own card and
  run over 9 face-up monsters across 7 savestates, it returns the true slot in
  every case where native returns -1 (`--fix-check` half of the probe).

## Round 5 — the full chain build FAILS, and not because of this card

`apply_all_patches` died at **step 24/55** (Shien's Dojo) with
`RuntimeError: criteria row 409 is 0x19B1, expected phantom 0x19B5`, exit code 1
— and still left a 129 MB plausible-looking `rom_all_patches.nds` behind, which
was deleted. (Exactly the trap in `otn-chain-build-verify-artifact`: assert the
artifact, never the exit code. The previous good chain ROM had been moved aside
to `rom_all_patches.PREV.nds` first, so nothing was lost.)

- `patch_shiens_dojo` anchors on criteria-registry **row INDEX 409**
  (`CRIT_ROW = 409`, expecting phantom cid 0x19B5). Measured: the **stock** table
  does have 0x19B5 at 409, so the anchor is correct against stock and wrong
  against the chain — some earlier step inserts a row ahead of it (a
  count-neutral insert that drops a phantom ABOVE 0x19B5 and inserts BELOW it
  shifts every row between them down one).
- This is the failure mode `otn-chain-build-verify-artifact` already names:
  **anchor chain preconditions on a CID, never a row index.** Nothing in this
  session's Ninishi work touches the criteria registry (cls1, the ARM9 Karakuri
  table and code hooks only), and a single-card ROM cannot see this class of bug.
- Culprit being measured by `scratch/criteria_shift_probe.py`, which applies the
  chain steps in order with `WRITE_TEXT = False` (the criteria table is in
  overlay 3, so skipping the bin2.pac repack costs nothing) and reports where
  0x19B5 sits after each step.

## Ruled Out

- **Stealing a dead granter arm.** Every cid in the granter chains is a real
  card: 0x12F3 Ultimate Offering, 0x1AA3 Big Evolution Pill, 0x1C33 Double
  Summon, 0x1D35 Cry Havoc!, 0x209B Brain Research Lab, 0x20D6 Grunard,
  0x2115 Swap Frog, 0x21D3 Advance Force. No phantom arm exists to recycle.

## Open Questions

- Does the fifth arm actually fire in a duel? Nothing here has been in-game
  tested. Note the grant is now **normal-duel only** (ov5 stubs; a puzzle loads
  ov41 over ov5) — it used to be puzzle-safe as pure ov3 data.
- Precedence when both granters are on the field and the "any card" query
  (r4 == 0) runs: the stub answers Dverg first, matching the engine's own
  first-match-wins order for the Grunard/Frog arms. Not observed in play.

## Next Experiment (the in-game test) — ROUND 3, JOINED ROM

ROM: `data/over_the_nexus/working/rom_ninishi_test.nds`, built by
`_build_ninishi_test.py` (Maiden -> Haipa -> Ninishi). All three clauses are live
in it; clause 3 is already confirmed, so this test is about 1 and 2.

1. **Clause 1, must attack if able**: Ninishi face-up in Attack Position with a
   legal attack available — the game must not let you skip its attack.
2. **Clause 2, position change when attack-targeted**: opponent declares an
   attack on a face-up Ninishi — it should change battle position.
3. **Negative control for clause 1**: Muso "Haipa" (Saggi 0x0FC8) must still be
   forced to attack — Ninishi joined Haipa's shared remap list, so a mistake
   there breaks Haipa too.
4. **Dverg regression** (still untested): Dverg on the field + a "Nordic"
   monster in hand must still get its own extra Normal Summon on the turn Dverg
   was Normal Summoned, and its Nordic-Relic GY recovery must still trigger.
   This is the control for CAVE_NS_FIELD's tail-call.
5. Clause 3 needs no retest (confirmed 2026-09-10) but comes along for free.
