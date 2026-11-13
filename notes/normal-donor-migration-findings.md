# Re-homing every shipped card onto a Normal-Monster donor — findings (2026-08-24)

Task: revisit every patch in `otn_enhanced/cards/` and, where the
engine allows it, move the card off its Effect-Monster donor onto a records-free
**Normal Monster**, so the patch stops cannibalising a playable card.

Trigger for the task: `patch_reborn_tengu` (2026-08-24) proved the last missing
piece — a vanilla can be given a leave-field trigger by DATA alone (mask row +
cls2 row + criteria row), no per-cid switch arm required.

## Confirmed (this session)

### New tool: `otn_enhanced/tools/donor_scan.py.py`

The decisive vetting test — the one that picked The Portrait's Secret — is
**"scan overlay 3 + ARM9 for the cid as an aligned u16 / u32"**. Every per-cid
structure in this engine is a table of cids, so zero aligned occurrences ⇒ the
cid is entangled in nothing. Packaged as a reusable tool with three refinements
that the ad-hoc sweep did not have, each of which produced a false positive on a
real donor:

* **A u16 hit in CODE space is an instruction encoding, not a table entry.**
  Hitotsu-Me Giant 0x0FA9 (shipped Warwolf donor) matches `lsrs r1,r5,#0x1e` at
  ov3:0x02187168. ov3's per-cid data block starts at ≈0x0226D000; below that a
  bare u16 is noise. A **u32**-aligned hit anywhere IS binding — that is a
  PC-relative literal-pool constant, which is how a per-cid compare gets its key.
* **A hit on a NON-KEY field of a known table is not a cid reference.**
  Criteria row 811's handler is 0x02240FD9, whose low halfword equals Armored
  Lizard 0x0FD9 (the shipped Lightpulsar donor).
* **ARM9's data region holds numeric tables, not just cid tables.** The four
  "hits" on Armored Lizard / Basic Insect at 0x0209D6D2 / 0x0209E400 /
  0x0209E6D0 / 0x020A1402 are consecutive-integer runs paired with a smoothly
  varying second field — geometry/curve tables where the cid match is arithmetic
  coincidence. Reported as *advisory*, never disqualifying.

Verified against ground truth: every donor the shipped patches already treat as
records-free scans CLEAN, and Mermaid Archer 0x1FFC is correctly caught by
`cls3 record[527]` — the exact entanglement `dispatch.cls_tables` records as
having misdirected several Sea Lancer rounds.

Donor pool: **131 clean, obtainable Normal Monsters**
(`python -m otn_enhanced.tools.donor_scan --free --obtainable`), filterable by
level / race / attribute / name-slot floor.

Also added: **name / description slot budgets per language**. The in-place slot is
the length of the donor's CURRENT string — what the shared writer `_place_string`
tests — NOT the gap to the next `card_indx` entry, which over-reports by the
inter-string padding. Getting that wrong cost a donor re-pick below. Now KB fact
`donor.text_slot_is_the_current_string_length`.

### The audit

`card_type` read from the WORKING ROM's `bin2.pac` card_prop. (The committed
`ygo_tools/reference_files/nds_card_prop.bin` decodes Blue-Eyes as NONE /
Beast-Warrior — already a known KB fact, `tool.stale_card_prop_reference` /
`tool.card_prop_race_attr_decode`: those files are randomiser output, and race
and attribute must never be read from them. `donor_scan.cards()` reads the ROM.)

**Already on a vanilla donor — nothing to do (8):**

| patch | donor | type |
|---|---|---|
| `patch_darkflare` | Battle Footballer 0x1646 | Normal Monster |
| `patch_lightpulsar` | Sword Arm of Dragon 0x0FB1 | Normal Monster |
| `patch_maiden_eyes_of_blue` | Comrade Swordsman of Landstar 0x1ED7 | Tuner, but a **vanilla** — no printed effect, scans CLEAN |
| `patch_metal_armored_bug` | Basic Insect 0x0FD8 | Normal Monster |
| `patch_reborn_tengu` | The Portrait's Secret 0x1463 | Normal Monster |
| `patch_tg_striker` | Ally Mind 0x1F18 | Normal Tuner |
| `patch_tg_warwolf` | Hitotsu-Me Giant 0x0FA9 | Normal Monster |
| `patch_zeta_reticulant` | Gross Ghost of Fled Dreams 0x1464 | Normal Monster |

**⚠️ A REAL DEFECT FOUND IN A SHIPPED PATCH.** `patch_eclipse_wyvern`'s donor
Divine Dragon Ragnarok 0x1859 is a Normal Monster but is **not** clean: it is
`fusion recipe A[78] +0x4` — the second material of **King Dragun 0x1879**
(Lord of D. 0x128B + Divine Dragon Ragnarok). Converting it silently rewrites
that Fusion's recipe to "Lord of D. + Eclipse Wyvern". This is exactly the trap
`donor.vetting_beyond_cls_records` documents for Meteor Dragon, and the module's
own vetting prose says only "absent from ALL FOUR cls tables and from the
criteria registry" — it never checked the Fusion tables. Worth re-homing to a
clean vanilla even though the card type is already right.

**Structurally impossible — the target card is not a Main-Deck monster (11):**
`azure_eyes`, `escuridao`, `hyper_librarian`, `shooting_quasar` (must be Extra
Deck); `dragon_shrine`, `shiens_dojo`, `vylon_element`, `wonder_wand` (Spells);
`infernity_barrier`, `safe_zone`, `w_nebula_meteorite` (Traps).

**Not donor conversions at all (2):** `patch_armory_arm` and `patch_regulus` fix
/ extend the native card in place.

**Migration candidates (11)** — Main-Deck monsters still hosted on a real Effect
Monster, tiered by what the patch borrows from the donor's NATIVE machinery:

*Tier A — a shipped, IN-GAME-CONFIRMED recipe already does this on a vanilla:*

The enabling mechanism is **{records-free Normal Monster donor + a leave-mask row
in 0x0226EC1C + a cls2 record}**, and it is not speculative: `patch_eclipse_wyvern`
(mask 0x0800, donor 0x1859) and `patch_lightpulsar` clause 3 (mask 0x0800, donor
0x0FB1) both ship it and are in-game confirmed — Lightpulsar's three clauses were
re-tested unregressed on 2026-08-18.
⚠️ **list30 0x0226E904 cannot be joined**: it is the semantically exact "sent from
the field to the GY" register, but all 30 entries are real cards, there is no
phantom to drop and its count is a hard-coded bound. The mask table is the register
for every non-native member, and it reaches the same arming flag `[sp+0x18]`.


| patch | donor | borrows | replacement recipe |
|---|---|---|---|
| `patch_gravekeepers_recruiter` | Botanical Girl 0x1ED4 | list30 membership (sent-to-GY trigger) + Sangan's cls2 shape | ✅ **DONE — see below** |
| `patch_darksoul` | Deep Diver 0x1CE6 | native End-Phase trigger + a STOLEN registry slot (costs Manticore of Darkness 0x16F9 its own) | exactly the T.G. Striker/Warwolf E2 recipe, already shipped on 0x1F18 / 0x0FA9 |
| `patch_boggart_knight` | Vampire Orchis 0x15D4 | native "when Normal Summoned" cls1 trigger | ✅ **DONE 2026-09-08 → Molten Behemoth 0x13A5 — IN-GAME CONFIRMED by user 2026-09-08** (all five oracles, first test; verify 19/19) — see `notes/boggart-knight-normal-donor-findings.md` |
| `patch_tour_guide` | Synchron Explorer 0x229E | same on-Normal-Summon engine (cls1 +04 0x02206F41 / +0C 0x021F0419) | same as Boggart. ⚠️ but see the embargo blocker below |

*Tier B — feasible, needs a mechanism that is understood but not yet built here:*

* `patch_elder_six_samurai` (AoJ Cosmic Gateway 0x1F1D) — today it is a **2-byte**
  edit retargeting the donor's OWN node in the hand-SS BST. A vanilla has no
  node, and `handss.dead_arm_donor_windows` proves **all four dead arms are
  spent**: two windows are entirely Speed Spells, 0x0225E6E6 is Lightpulsar's and
  0x0225E88E is Darkflare's. So the only route left is the shared ov5 trampoline
  over `BL 0x0225E51C` @0x0224C026 (`tg_table.py`, already live for T.G. Striker
  and built to host several cids). **Cost: Elder stops working in puzzles** — it
  is pure ov3 today, and ov41 evicts ov5.
* ~~`patch_wattcobra` (Fane 0x2069)~~ ✅ **DONE 2026-09-10 -> WATTKID 0x0FD3**
  (`verify()` 11/11, **IN-GAME CONFIRMED by user 2026-09-10, first test, all five oracles**) — see
  `notes/wattcobra-normal-donor-findings.md`. Open Question 2 below is ANSWERED:
  the battle-damage trigger IS a membership list
  (`battle.damage_trigger_is_a_membership_list`), so the card is Tier A and pure
  DATA — three count-neutral sorted inserts (direct-attack grant list 0x0226D730,
  direct-attack-damage trigger list 0x0226EE7C, cls1) plus the populate row it
  already had. The donor was chosen by the user and is better than any clean
  vanilla: Wattkid is already LIGHT/Thunder/1000/500 AND already entry 0 of the
  ARM9 Watt set-code table, so the old ARM9 PART D deletes itself and the
  "Wattkid is a false Watt member" bug fixes itself.
* `patch_tg_rush_rhino` (Dash Warrior 0x22E6) — E2 is already the donor-free T.G.
  recipe, but E1 is Dash Warrior's NATIVE damage-step ATK boost, dispatched by
  cid at 0x0224DC0A with the amount as a code immediate. The donor also owns two
  data-table rows (ov3:0x0226E708 in a 6-byte `{cid, s16, s16}` table, and
  ov3:0x0226E8EE in the sorted cid list ending at 0x0226E902). ⚠️ The module
  docstring calls this donor "RECORDS-FREE", which is true only of
  cls0-3/populate/registry — it is NOT clean, and its own E1 section depends on
  that fact.

*Tier C — donor-locked; migration is a rewrite, not a re-home:*

* ~~`patch_mystic_piper` (Ancient Gear Cannon 0x19BB) and `patch_thunder_sea_horse`
  (Thunder Dragon 0x114F) both need a **manually-activated (ignition) effect**,
  and mystic_piper's own v2 round already proved the blocker: *"adding a cls3
  entry to a card with no NATIVE ignition is not enough; an upstream gate decides
  whether a monster's ignition is offered at all."* Finding that gate is the
  single highest-value unlock in this whole list — it converts both to Tier A and
  makes "give a vanilla an ignition" a general recipe.~~
  ⚠️ **STRUCK 2026-09-08 — THE GATE DOES NOT EXIST.** See
  `dispatch.vanilla_can_take_an_ignition` and
  `notes/mystic-piper-normal-donor-findings.md`. `patch_upstart_golden_ninja`
  was already the counter-example: an ignition on the records-free vanilla
  0x1464, in-game confirmed 2026-09-01. What blocked v1/v2 was the **condition
  slot they cloned** (Cyber Valley's / Exiled Force's, both cid-keyed), not
  anything upstream — "a SHARED slot is not a CID-BLIND one; the test is to
  disassemble the slot". `patch_mystic_piper` is **re-homed onto Flame Dancer
  0x13B8** as one count-neutral cls3 insert — **IN-GAME CONFIRMED by the user
  2026-09-08, first test** (effect offered, Tributes, reveals, draws, Lv1 bonus
  draw, and a second copy the same turn refused; no regressions).
  **`patch_thunder_sea_horse` is thereby unblocked too and moves to Tier A** —
  not yet attempted.
* `patch_sea_lancer` (Mermaid Archer 0x1FFC) — E2 IS the donor's own replacement
  effect, which lives in a per-cid switch arm of step 5 @0x0225C2B8
  (`dispatch.step_table_replacement`, 8 cids, all with an "instead" clause), and
  the equip-target selector step 5 @0x0224FA4C names her too. Both are
  base±imm switches (ungreppable).
* `patch_ninishi` (Dverg 0x245B) — the extra-Normal-Summon grant is cid-keyed
  code with two Dverg-specific ARM9 archetype-predicate call sites
  (0x021B963A, 0x02261E3E).

## Ruled Out

* **Re-homing Elder of the Six Samurai onto a spare dead hand-SS arm.** All four
  are spent, and two could never take a monster (`handss.dead_arm_donor_windows`,
  VERIFIED with a full-tree simulation). Confirmed by re-reading the fact, not
  assumed.
* **Trusting `ygo_tools/reference_files/nds_card_prop.bin` for card facts.** It
  decodes Blue-Eyes White Dragon as attribute NONE / race Beast-Warrior; the
  ROM's own `bin2.pac` copy decodes it correctly as LIGHT / Dragon. card_type,
  level, ATK and DEF happen to agree, which is why the discrepancy is easy to
  miss. `donor_scan.cards()` reads the ROM.

## Open Questions

1. ~~**The ignition-offer gate.** Which upstream check decides that a monster's
   ignition effect is offered at all? (mystic_piper v2 hit it; never located.)
   Unlocks Tier C's two ignition cards and vanilla ignitions generally.~~
   ✅ **ANSWERED 2026-09-08: there is no such check.** The offer test is the cls3
   record's own `+0C` slot, reached from the menu via `0x0224AD94(desc)`. A
   vanilla takes an ignition from one cls3 record plus `card_type` → Effect
   Monster. KB fact `dispatch.vanilla_can_take_an_ignition`.
2. ~~**Battle-damage trigger dispatch.** Is a cls1 record with +08 = 0x021E32D5
   enough for a records-free donor, or is there a membership list like
   `summon.trigger_is_a_membership_list`? Decides Wattcobra.~~
   ✅ **ANSWERED 2026-09-10: it IS a membership list**, and there are TWO —
   list A 0x0226EE7C x 0x13 (gated on the "direct attack" flag at
   0x02298AD8+2) and list B 0x0226EEA4 x 0x33 (ungated), both posting event
   code 0x10 via 0x021D3230 from one function at 0x021D020A. A miss means the
   event is never posted, so the cls1 record alone is dead weight. Both lists
   carry phantoms, so each insert is count-neutral. KB fact
   `battle.damage_trigger_is_a_membership_list`. ⚠️ It also CORRECTS the old
   `patch_wattcobra` docstring: cls1 +08 = 0x021E32D5 is the masked ZONE
   predicate (`bl 0x021D6E40`), NOT a direct-attack condition.
3. **Tour Guide's embargo after a donor change.** The 4-byte trick works because
   deny key 2 is computed as `key1 ± imm8` and 0x229E − 0x2B == 0x2273 (Chaos
   Goddess). A new donor D must satisfy D ± imm8 == 0x2273, i.e. D ∈
   [0x2174, 0x2372] — a range with (checked) no clean vanilla. So the embargo
   needs its own pool word or another mechanism.

## ✅ MIGRATION 1 DONE — Gravekeeper's Recruiter, Botanical Girl 0x1ED4 → Atlantean Pikeman 0x1CC6

Built, `verify()` PASS (9/9), stub byte-identity tests PASS (6/6), allocation guard
clean. **Not yet tested in a duel** — that is the next experiment.

`data/over_the_nexus/working/rom_gravekeepers_recruiter.nds`

* **Botanical Girl is a real card again.** The module now touches 0x1ED4 nowhere;
  `_assert_botanical_untouched` pins her native cls2 record, criteria row and
  list30 membership, both when building and in `verify()`. A future patch that
  reaches for 0x1ED4 as "records-free" trips it.
* **Donor: Atlantean Pikeman 0x1CC6** — a junk vanilla (Lv2 WATER Sea Serpent
  1400/0, pack 19), zero binding occurrences anywhere. **Chosen on TEXT SLOTS,
  not on a matching face**: card_prop is rewritten wholesale, so a donor whose
  printed face already matches buys nothing. Saggi the Dark Clown 0x0FC8 is
  *already* DARK/Spellcaster/Lv3/DEF 1500 and needs **zero** phantom rows to move
  — and was rejected, because its Japanese description slot is 59 B, so the card
  would have displayed Saggi's own flavour text in 7 of 8 languages.
* **The trigger moved tables**: leave-mask row `{0x1CC6, 0x0800}` instead of list30
  membership, for the reason above. Paired with Sangan's cls2 shape
  (+04 = 0x02207EF5, rest 0 = mandatory).
* Three count-neutral inserts, phantoms registered in the ledger: cls2 over 0x1B8F
  (41 rows move), criteria over 0x19C0 (198 rows move), leave-mask over 0x194A
  (22 rows move). **Composition checked**: the only absolute-index anchor into any
  of these tables is `patch_shiens_dojo`'s `CRIT_ROW = 409`, and the criteria
  window is [411, 609], so it never moves — asserted in code, not just in prose.
  (`patch_dragon_shrine`'s "crit[157]" is prose only; it searches by cid.)
* **Text is BETTER than the build it replaces**: the effect text was trimmed to
  120 B ("to hand" for "to your hand") to clear the donor's real 124 B Japanese
  floor, so it now lands in **all eight languages**. The old build's 125 B text
  overflowed Botanical Girl's 113 B Korean slot. The name "GK's Recruiter" (14 B)
  lands in six — Japanese (12 B) and Korean (13 B) keep the donor's name, the same
  graceful degradation the shipped build had.

## Next Experiment

In-game on `rom_gravekeepers_recruiter.nds` (single-card ROM only —
`ship-the-card-before-the-chain`; no combined build or all-patches sweep until
this passes). Four oracles:

1. **Atlantean Pikeman** now reads "GK's Recruiter", DARK / Spellcaster / Lv3 /
   1200 / 1500, with the real effect text and the real artwork.
2. Send it from the field to the GY by **each** route — destroyed by battle,
   destroyed by effect, Tributed, used as Synchro Material — and each time a
   "Gravekeeper's" monster with DEF ≤ 1500 is added from the Deck to the hand,
   **mandatorily** (no Yes/No prompt).
3. It does **not** fire from a hand discard or a mill (the leave dispatcher is
   field-only; that is the intended reading of "this card you control").
4. **Botanical Girl** is back: her own name, her own art, and her own effect
   ("you can add 1 Plant with DEF ≤ 1000 from your Deck to your hand") when she
   is sent from the field to the GY.

If 2 fails, the arming flag is the suspect: check that the donor really is absent
from list30/list106 (verify() asserts it) before touching the cls2 shape.
