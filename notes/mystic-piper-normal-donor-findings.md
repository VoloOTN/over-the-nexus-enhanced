# Mystic Piper — re-home onto a Normal-Monster donor (2026-09-08)

Task: `patch_mystic_piper` USED TO cannibalise **Ancient Gear Cannon 0x19BB**, a real
Effect Monster, because its build history (v1–v4) concluded the card was
*donor-locked*: it needs a manually-activated (ignition) effect, and the v2 round
concluded *"adding a cls3 entry to a card with no NATIVE ignition is not enough;
an upstream gate decides whether a monster's ignition is offered at all."*
That conclusion is recorded as Tier C in `notes/normal-donor-migration-findings.md`
and as Open Question 1 ("the ignition-offer gate") in the same file.

**Status: ✅ DONE — IN-GAME CONFIRMED BY USER 2026-09-08, first test.**
`verify()` 13/13 PASS, allocation guard clean, KB 411 PASS / 0 FAIL.
`data/over_the_nexus/working/rom_mystic_piper.nds`

The user's exact words: *"Voth confirmed, no regressions"*, disambiguated by them
to reading **(a)**: **both clauses** — the C1/C2 draw effect works (the effect is
OFFERED in the menu, Tributes the card, reveals the top of the Deck, draws it,
and draws a second card when that card is a Level 1 monster) **AND** C3 refuses a
second activation in the same turn. Oracles 2–5 of the list at the bottom of this
file. Plus: no regressions elsewhere in the duel.

⚠️ **NOT separately attested, and must not be read as confirmed:**
* oracle 1 (the card's printed face — name / LIGHT / Spellcaster / Lv1 / 0 / 0 /
  full text) was not part of reading (a), though the effect could not have been
  offered at all if the record were missing;
* the **negative control on C2** (a Level 2+ monster, or a Spell/Trap, drawing
  only ONE card) was never explicitly requested or reported;
* **Ancient Gear Cannon 0x19BB being a real card again** was not visually checked
  in the duel — it is asserted statically at build time and in `verify()`.

User approved donor **Flame Dancer 0x13B8**, phantom **0x1436**, and **C3 rides
along** (2026-09-08).

## What was built

| part | where | what |
|---|---|---|
| A | ov5 `CAVE_MYSTIC` 0x0239A180 | the 72-B resolver, **byte-identical and same address** as the old build (it is side-keyed and cid-blind, so the donor swap does not touch it) |
| B | ov3 cls3 `0x02279D74` | `{0x13B8, +04 CAVE_MYSTIC\|1, +08 0, +0C CAVE_PIPER_COND\|1, +10 CAVE_PIPER_COST\|1, +14 0}` — dropped phantom 0x1436 @67, inserted @65, **2 rows shifted, count 776 unchanged, still sorted** |
| C | ov5 `CAVE_PIPER_COND` 0x0239EBA0 (38 B) | C3 condition: `desc[+7]` guard, then `0x021A14E8(side, 0x0B, cid, 1)` → 0 if already posted, else chain `0x021F06E8` |
| C | ov5 `CAVE_PIPER_COST` 0x0239EBD0 (24 B) | C3 cost: `0x021D2584(side, cid, 1, 0)` then tail-chain the native Tribute `0x021E50CC` |
| D | bin2.pac | card_prop `Normal Monster → Effect Monster`, FIRE/Pyro/Lv2/550/450 → LIGHT/Spellcaster/Lv1/0/0; name + the **full 176-byte printed text in all 8 languages** via `card_text.CARD_TEXT[0x13B8]` |

`CAVE_FREE` bumped 0x0239EBA0 → 0x0239EBF0. Ledger claims registered in the same
edit: `("donor_cid", 0x13B8, "mystic_piper")` and
`("cls3_table", 0x1436, "mystic_piper")`.

### The desc[+7] guard in the condition is load-bearing

`dispatch.slot3_recheck_and_cost_flag`: slot3 is re-evaluated mid-activation
AFTER the cost has run — and the cost is what posts the node. An unguarded query
would return 0 on the re-check, so the effect would activate from the menu and
then **fizzle silently**. `desc[+7]` is exactly "the cost has already run"
(0 at the menu, set to 1 at `0x02217FB4`). Piper has `+14 == 0` (no target
template) and the KB says only the MULTI-select template `0x02235700` re-checks,
so this is belt-and-braces — but a silent fizzle costs a duel.

### Which "once per turn" C3 implements — SETTLED IN GAME (oracle 5)

The turn-log pair is keyed on the **cid**, so one activation locks every copy for
the turn. The per-copy alternative (upstart's 0x0FB6 rider, side+slot) is
**vacuous for this card**: the cost tributes the card itself, so a copy is gone
the instant it activates and could never activate twice anyway. Only the
cid-keyed reading produces observable behaviour. ⚠️ That was a mechanical argument
from the self-tribute cost, **not a ruling asserted from recall** — and the user
then confirmed the resulting behaviour in a duel (a second copy the same turn is
refused), so the 0x0FB6 rider is not needed here.

## Confirmed (this session, read out of the committed ov3/ARM9 oracles + stock ROM)

### 1. THERE IS NO "IGNITION-OFFER GATE". Open Question 1 is answered — it was a cid-keyed CONDITION SLOT, not an upstream membership test.

`patch_upstart_golden_ninja` is a **shipped, IN-GAME-CONFIRMED (user, 2026-09-01,
four rounds)** manually-activated ignition effect on a **records-free vanilla
Normal Monster donor, The Gross Ghost of Fled Dreams 0x1464**. Its PART D is a
brand-new cls3 record for the donor cid, inserted count-neutrally over phantom
0x144C. So a vanilla CAN be given an ignition by data alone.

What actually bit mystic_piper v2 is named in upstart's own docstring, PART D:

> ⚠️ +0C 0x021F0BDD IS **NOT** A GENERIC CONDITION ... It binary-searches the
> per-cid registry 0x0226FAFC and returns 0 for any cid without a row.
> A SHARED slot is not a CID-BLIND one; the test is to disassemble the slot.

i.e. the "gate" is whichever cls3 **+0C condition** the cloned framework carried.
v1 cloned Cyber Valley's (cid-keyed). v2 cloned Exiled Force's framework.

### 2. The three framework slots Mystic Piper keeps are ALL CID-BLIND — disassembled this session.

* **+0C `0x021F06E9`** (0x021F06E8, ov3). Reads `desc[+2]` side, `desc[+3]` slot,
  `desc[+6]`; indexes `0x0229ACD8 + side*0xB3C + slot*0x14`, tests bit 26 of the
  zone word, then `0x021AE130(side^desc[+6], side)`. Returns 1/0.
  **No cid load, no table search, no literal-pool cid.** Full listing:
  pool words are only `0x00000B3C` and `0x0229ACD8`.
* **+10 `0x021E50CD`** (0x021E50CC, ov3) is 7 instructions:
  `push {r3,lr} ; r0=desc[+2] ; r1=desc[+3] ; bl 0x021CF658 ; movs r0,#1 ; pop`.
  That `bl` is the send-self primitive — **this slot IS the "Tribute this card"
  cost**, and it is cid-blind (side+slot only).
* **+08 = 0, +14 = 0** — no sub-handler, no target/resolution tail, so no target
  framework can abort (the v3 Mei-Kou failure mode cannot recur).

### 3. Donor candidate: **Flame Dancer 0x13B8** (the user's suggestion) — `donor_scan` VERDICT **CLEAN**

    0x13B8  Flame Dancer   Normal Monster  Lv2 FIRE Pyro 550/450  pack1=49
    VERDICT: CLEAN - no data structure names this cid
    21 non-key / code-region u16 hits, all instruction encodings (ov3 code region)

* Zero aligned u16/u32 occurrences in any ov3/ARM9 **data** structure.
* **Unclaimed**: no hit for `0x13B8` anywhere in `finished_patches/`,
  `check_allocations.py`, `otn_enhanced/docs/engine/allocations.yaml`, or `notes/`.
* Text slots (name floor 11 B, desc floor 51 B) **do not matter** — the cid goes
  into `card_text.CARD_TEXT` and `apply_stats_and_text` re-emits the blobs in
  index order (the boggart_knight path, user-confirmed 2026-09-08). The full
  printed text already exists in `card_text.py` keyed 0x19BB, line 321.

### 4. The count-neutral cls3 insert has an unclaimed phantom two rows away.

cls3 = `0x02279D74`, 0x308 rows, stride 24, **sorted** (asserted this session).
0x13B8 sorts to **index 65**, between `0x13A8` (64) and `0x1402` (65).

Phantom rows in that neighbourhood, and their ledger status:

| cls3 row | phantom cid | claimed by |
|---|---|---|
| 67 | **0x1436** | **UNCLAIMED — zero hits in allocations.yaml / check_allocations.py** |
| 68 | 0x143B | unclaimed (backup) |
| 69 | 0x1449 | `populate_table` claimed by upstart_golden_ninja (cls3 row itself free) |
| 71 | 0x144C | `cls3_table` claimed by upstart_golden_ninja |
| 72 | 0x1452 | `populate_table` claimed by reborn_tengu |

**0x1436 is the pick**: dropping cls3[67] and inserting at 65 shifts exactly two
rows (65, 66), keeps the count at 0x308 and keeps the table sorted.
Checked in **both** the stock ROM and the CHAINED image
`data/over_the_nexus/working/rom_all_patches.nds`: 0x1436 still sits at cls3[67]
in both, i.e. unspent.

### 5. Ancient Gear Cannon 0x19BB is recoverable in full.

The current patch touches 0x19BB in exactly three places: cls3[234] `+04`,
card_prop, and the name/desc blobs. Nothing else. Not touching the cid at all
restores the real card, and a boggart-style `_assert_agc_untouched` pin (its
native record `{+04 0x02220A8D, +08 0, +0C 0x021F06E9, +10 0x021E50CD, +14 0}`)
makes a future patch reaching for 0x19BB as "records-free" trip.

## Ruled Out

* **"An upstream gate decides whether a monster's ignition is offered at all"**
  (mystic_piper v2, 2 rounds; carried into `normal-donor-migration-findings.md`
  as Tier C + Open Question 1). Falsified by `patch_upstart_golden_ninja`, which
  is the same shape — new cls3 record on a records-free vanilla — and is in-game
  confirmed. The offer test is the record's own `+0C` slot; upstart's was
  cid-keyed (`0x021F0BDD` → registry `0x0226FAFC`), Piper's (`0x021F06E9`) is not.
* **card_type as the gate.** Not tested as such, but not needed as an
  explanation: `apply_stats_and_text(card_type=...)` already exists and every
  vanilla-donor patch (darksoul, tg_striker, upstart) sets
  `ERA2_CARD_TYPE_REVERSE["Effect Monster"]`. Piper currently passes **no**
  `card_type` at all because Ancient Gear Cannon already is one — so the new
  build must add it. Flagged as `ASSUMED` on the risk checklist, not `PROVEN`.

## Open Questions

1. **The printed "once per turn" is NOT implemented today and never was.**
   `card_text.CARD_TEXT[0x19BB]` carries the full text including *"The effect of
   'Mystic Piper' can only be activated once per turn"*, but the `NEW_DESC`
   fallback string in the module drops that sentence and the resolver has no
   latch. Pre-existing, out of scope for a donor re-home, but it should not be
   silently inherited — decide whether to add the turn-log pair
   (`dispatch.turnlog_once_per_turn_pair`) or the per-copy 0x0FB6 rider
   (upstart PART E) in the same build.
2. Order dependency in `apply_all_patches`: mystic_piper is step 4 and
   upstart_golden_ninja retires 0x144C later. 0x1436 is untouched by every
   shipped step, so no ordering constraint is expected — but this needs the
   chain rebuild + full `_verify_all_patches.py` sweep to prove, exactly as the
   boggart re-home did.

## Next Experiment

**The chain.** The card itself is done. What is left is the integration proof:
rebuild `apply_all_patches` and run the `_verify_all_patches.py` sweep, asserting
the BUILT ROM's content + final patch count + sha256 (a chain build has twice
exited 0 while leaving a plausible-looking broken ROM —
`otn-chain-build-verify-artifact`). Nothing in the chain touches 0x1436 or
0x13B8, so no ordering constraint is expected, but that is unproven until the
sweep runs.

Also unblocked and not attempted: **`patch_thunder_sea_horse`** (Thunder Dragon
0x114F), the other card the "ignition-offer gate" hypothesis had filed as Tier C.

### The oracles this card was tested against (2–5 confirmed, reading (a))

1. the card reads **Mystic Piper**, LIGHT / Spellcaster / Lv1 / 0 / 0, with the
   full printed text including the once-per-turn sentence;
2. **the effect is OFFERED in its menu** — this is the whole point of the
   re-home, and the thing v1/v2 could never get;
3. activating it Tributes the card, reveals the top of the Deck and draws it;
4. if the revealed card is a Level 1 monster, a second card is drawn
   (negative control: a Level 2+ monster or a Spell/Trap must draw only one);
5. **C3** — with a second Mystic Piper Summoned the same turn, its effect is
   NOT offered; on the following turn it is offered again.

**Oracle 5 passing settles the "once per turn" reading.** The cid-keyed turn-log
pair is the behaviour the user accepted in a duel, so the per-copy 0x0FB6 rider
is not needed here. (The argument for it was mechanical, not a recalled ruling:
the cost tributes the card itself, so a per-copy latch could never fire twice.)

**The silent-fizzle failure mode did not occur** — the effect resolved and drew.
So the `desc[+7]` guard in `CAVE_PIPER_COND` is doing its job on the live path:
without it, `dispatch.slot3_recheck_and_cost_flag` predicts the effect would
activate from the menu and then draw nothing. That is now evidence for the guard,
not just a precaution.

## Not done this session

* **No chain build.** `patch_mystic_piper` is step 4 of `apply_all_patches` and
  its descriptions were updated to the new donor, but the combined ROM was NOT
  rebuilt and `_verify_all_patches.py` was NOT swept — per the
  ship-the-card-before-the-chain rule, that waits until the card passes in a
  duel. Nothing in the chain touches 0x1436 or 0x13B8, so no ordering constraint
  is expected, but that is unproven until the sweep runs.
* **`patch_thunder_sea_horse` is now unblocked** (same Tier C reasoning, same
  refutation) and has not been attempted.
