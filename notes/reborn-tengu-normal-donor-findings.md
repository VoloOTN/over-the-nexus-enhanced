# Reborn Tengu -> Normal-Monster donor — findings (session 2026-08-24)

Task: re-home the shipped "Reborn Tengu" (currently donor **Minefieldriller 0x2085**,
a real Effect Monster whose native effect is destroyed by the patch) onto a
records-free **Normal Monster** donor.

Printed text (scratch/ygoprodeck_cache.json, id 10028593):
> "If this face-up card leaves the field: Special Summon 1 "Reborn Tengu" from your Deck."
WIND / Beast-Warrior / Level 4 / 1700 / 600 / Effect Monster. ONE clause.

## Confirmed (this session)

* **The current donor is a real card with a real effect.** Minefieldriller 0x2085 =
  "When this face-up card you control leaves the field and is still in your possession:
  You can target 1 Field Spell Card in your Graveyard; add that target to your hand."
  Native wiring the patch overwrites: `cls2[470] {+04 0x02208181, +0C 0x021F05A9,
  +10 0x021E51E5, +14 0x02235605}` and `crit[954] {aux 0xFFFF, hnd 0x0223CBB1,
  word 0x00010184}`. Re-homing **restores this card**.
* **Why the shipped card triggers at all**: 0x2085 owns a *dedicated arm* in the
  leave-field per-cid switch (traced from the 0x021C8216 entry, arm body at
  **0x021C8CC4**). The arm is PURELY an arming computation — it sets `[sp+0x18]`
  and then falls into the SAME generic tail 0x021C93D0 every mask/list-armed card
  uses. A Normal-Monster donor lands on the generic tail with `[sp+0x18] == 0`
  and never posts. (Tracer validated against the two documented cases: 0x0FB1 and
  Sangan 0x0FD6 both reach `bl 0x021C93D0` @0x021C827A.)
* **The leave-mask bit semantics are fully decoded** (0x021C8116..0x021C81F0),
  and cross-checked against the printed text of native mask-row holders:
  | bit | predicate | meaning | witness |
  |---|---|---|---|
  | base | `[sp+0x28] == 0` | destination zone != 0x0D | every row |
  | 0x0001 | `[sp+0x98] == r6` | "you control" | Pinch Hopper 0x0805, Ice Queen 0x0C15 |
  | 0x0002 | `0x021A0DF8(r6,[sp+0xA0]) != 0xFFFF` | slot still resolvable | |
  | 0x0004 | `[sp+0x2C]` | left the FIELD | KB event.leave_dispatcher_three_registers |
  | 0x0008 | `[sp+0x94] != 0` | was FACE-UP (card struct +8) | Draupnir 0x060C |
  | 0x0010 | `[sp+0x54]` | face-up AND not "attacked face-down & destroyed by battle" | Poison Draw Frog 0x0814 |
  | 0x0020 | `[sp+0x94] == 0` | was FACE-DOWN | Statue of the Wicked 0x0C20 |
  | 0x0040 | opponent did it | "by your opponent's card effect" | Shark Cruiser 0x064C |
  | 0x0080 / 0x0100 | `[sp+0x44]` != / == 0 | by battle / NOT by battle | T.A.D.P.O.L.E. 0x0881 |
  | 0x0200 | `[sp+0x8]` | by a card effect | Seed of Flame 0x0E05 |
  | 0x0400 | `[sp+0x90]` | DESTROYED | KB 0x0C04 |
  | 0x0800 | `[sp+0x144]` | destination is the GY | Dandylion family |
  `[sp+0x54]` is built at 0x021C8080..0x021C809A: face-up AND NOT (destroyed by
  battle while it was the face-down attack target) — literally Poison Draw Frog's
  parenthetical.
* **THE 3DS SHIPS REBORN TENGU: cid 0x25E3** (CARD_Indx_E idx 4748). Konami's own rows:
  * leave-mask row **{0x25E3, 0x000C}** = face-up + left the field. (3DS mask table
    located by content at file off 0x5A18FC = **VA 0x6A18FC**, 243 rows —
    ⚠️ notes/eclipse-wyvern-findings.md line 1158 says 0x007A18FC, which is
    **off by +0x100000**; row indices 44/174 match exactly, so it is the same table.)
  * criteria row **{0x25E3, aux 0xFFFF, hnd 0x004A6834, word 0x00000802}**.
* **3DS handler 0x004A6834 == NDS 0x0223D075** — established by joining the 80 3DS
  rows on that handler to the same cids' NDS rows: 49 of the 53 that exist in both
  builds map to 0x0223D075 with **byte-identical words**. Method validated in the
  same run on 0x004B1B04 == NDS 0x0223CBB1 (52/57, incl. Minefieldriller itself).
* **aux 0xFFFF on handler 0x0223D075 means "a card with THIS card's own name"** —
  all 14 NDS rows {aux 0xFFFF, 0x0223D075, word 0x0802} are self-summoners
  (Giant Germ, Troop Dragon 0x14DD, Hyena, Hero Kid, Hydrogeddon, D-HERO Malicious,
  Cyber Larva, Infernity Beetle, Evil Thorn); rows with a real aux name another card
  (White Stone -> 0x0FA7 Blue-Eyes, Berfomet -> 0x1291 Gazelle).
* **The native NDS template for the whole action is Troop Dragon 0x14DD**:
  `cls2[97] {+04 0x02206CAD, +08 0, +0C 0, +10 0, +14 0}` + `crit[164]
  {aux 0xFFFF, hnd 0x0223D075, word 0x00000802}`, armed via list106.
  Resolver **0x02206CAD = "Special Summon the criteria-row selection, 1 copy"**
  (0x0221D7E9 is the any-number variant; 0x0220E805 the damage+SS variant).

* **The donor rides the SAME resolver arm as the shipped cid.** 0x02206F41 opens with
  a per-cid switch (key = `ldrh r1,[r4]` @0x02206F4E, arms at 0x02206FCC / 0x02206FD0 /
  default 0x02206FD2). Simulating every cid in 0x0E00..0x2600 gives exactly twelve named
  arms -- Doom Shaman, Summon Cloud, Il Blud, Gigaplant, Red-Eyes Darkness Metal Dragon,
  Magical Exemplar, Morphtronic Cameran, Fake Explosion, Urgent Synthesis, Batteryman AAA,
  Cloudian - Turbulence, Rainbow Gravity -- and the default for everything else, including
  **both 0x2085 and 0x1463**. (The simulator refuses to model any stack access, so it
  cannot repeat the thumb-stack-based-switch footgun; this switch touches no stack slot.)
* **Donor chosen: The Portrait's Secret 0x1463** -- Level 4 non-Tuner Normal Monster, in
  pack 1. Swept against cls0-3, the criteria registry, the leave-mask table, list30,
  list106, both Fusion recipe tables and the hand-SS/summon-restriction region, plus an
  occurrence scan: **zero aligned u16 or u32 hits anywhere in ov3 + arm9**. Name-slot
  floor across the eight languages is 12, exactly "Reborn Tengu".
* **Phantoms consumed.** 0x14E9 appears in exactly two places in the whole build -- mask
  row 28 and cls2[100] -- so taking both retires the cid entirely; its mask row is already
  at the donor's sorted index, so PART B shifts nothing. 0x1452 owns exactly one criteria
  row (132), is in neither membership list, and sits two rows below the insert point.
* **SHIPPED**: `patch_reborn_tengu.py` (supersedes and replaces `patch_minefield_driller.py`,
  which is deleted). 20/20 checks PASS on BOTH the single-card ROM and the combined
  `rom_all_patches.nds`; the full composition sweep `_verify_all_patches.py` reports
  **PASS 26 / FAIL 0 / SKIP 2** (the two skips are boggart_knight and darksoul, which
  have never had a `verify()`), so no shipped card regressed.
* **Measured blast radius** vs the clean overlay: leave-mask **0 rows moved**; criteria
  rows 132-133 only (`patch_dragon_shrine`'s index-anchored `crit[157]` re-read and
  unchanged); cls2 rows 92-100, and nothing in the tree anchors cls2 by index.
* **Collateral fixed**: `patch_darksoul.verify_against_proven` and
  `patch_zeta_reticulant` both imported the deleted module (the latter for three
  bin2.pac text helpers); both repointed at `patch_reborn_tengu`, and zeta now handles
  `_place_string` returning `None` rather than the old hard assert.

## Ruled Out

* **Stealing Minefieldriller's switch arm** (re-keying its equality literal): that
  arm IS the real card's trigger; the point of the exercise is to give the card back.
* **The ov5 leave trampoline** (CAVE_TG_ARMTRAMP @0x021C8216): destruction-only
  ([sp+0x90] gate), 4 bytes of headroom, and normal-duel-only. The mask row reaches
  the same flag with the right preconditions and works in puzzles.
* **Keeping the injected ov5 Yubel-selector clone (CAVE_MINEFIELD)**: unnecessary —
  {aux 0xFFFF, 0x0223D075, 0x0802} is the engine's own "SS a copy of me from the Deck"
  selector, and it is what the 3DS Reborn Tengu uses.

## Open Questions

* The native 0x2085 arm sets `[sp+0x18] = 1 + ([sp+0xC] & 0xC0 ? 1 : 0)`; the mask
  path always sets 1. The consumer switches on that value at **0x021CA980** (1/2/3
  build different packed words; variant 2 flips the side field to `r6 != [sp+0x98]`).
  Reading Minefieldriller's text, variant 2 is its **"and is still in your possession"**
  clause — which Reborn Tengu does not have, so variant 1 is the correct/faithful
  post for this card. Not proven in-game.

## Deliberate deviations (state these before testing)

* The Japanese **description** could not be relocated (no trailing padding left in
  `card_desc_j.bin`), so Japanese keeps The Portrait's Secret's flavour text. The NAME is
  correct in all eight languages. Same graceful degradation the shipped build had.
* Under the mask row the leave event always posts variant 1; the old donor's per-cid arm
  posted variant 2 when `[sp+0xC] & 0xC0`. That flag is Minefieldriller's "and is still in
  your possession" clause, which Reborn Tengu does not have -- so variant 1 is the correct
  post here, but the difference is untested in-game.
* Still **ov5, so normal duels only** (unchanged from the shipped build). The pure-ov3
  replacement is documented and ready: `card.self_ss_from_deck_row`.

## Next Experiment

In-game on the single-card ROM: get the donor on the field face-up, then make it
leave by each route — destroyed by battle, destroyed by effect, Tributed, bounced
to hand, banished, used as Synchro Material — and confirm a copy is Special
Summoned from the Deck every time (mandatory, no prompt), and that
**Minefieldriller** now shows its own name/effect and adds a Field Spell from the GY.
