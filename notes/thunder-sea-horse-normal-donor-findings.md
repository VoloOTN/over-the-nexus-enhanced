# Thunder Sea Horse — re-home onto Normal donor Fiend Kraken 0x0FEC (2026-09-17)

Task (user): move `patch_thunder_sea_horse` off Thunder Dragon 0x114F (a real
Effect Monster) onto **Fiend Kraken 0x0FEC** (user-chosen donor). Mechanism is
unchanged; only the cid the records hang off changes.

Status: **BUILD 2 IN-GAME CONFIRMED by user 2026-09-17** ("All confirmed." -- oracles 1-6 of the
build-2 test list: offered from hand, discard + pick + add 2, second activation refused, no SS
after, not offered after an SS, Thunder Dragon back to normal). Chain build / sweep NOT yet run.
Build 1 (sha256 4242ea32…) FAILED in-game test 1: effect not offered in hand (see below).
Build 2 adds PART A0: 0x0FEC inserted into ARM9 hand-effect list 0x0209BC4E over phantom
0x1B42. `data/over_the_nexus/working/rom_thunder_sea_horse.nds` sha256 14657ac5…6d0bd0f7,
verify() RESULT PASS (12 checks), check_allocations OK (251 claims), KB 476 PASS / 0 FAIL
(new fact `dispatch.hand_effect_offer_list`). No chain build run.

What changed: patch module now inserts cls2 `{0x0FEC, main|1, 0, cond|1, res|1, 0}`
over phantom 0x0E9E and criteria `{0x0FEC, 0, wrapper|1, 2}` over 0x0EB0 (tg_striker
`_insert_sorted`), SS-gate key follows DONOR_CID, card_type → Effect Monster, Thunder
Dragon's cls2 + criteria rows asserted stock at build and verify, text checked with
`card_text.check_rom_text`. `card_text.py` / `patch_card_art.py` keys 0x114F → 0x0FEC;
ledger claims added (cls2 0x0E9E, populate 0x0EB0, donor 0x0FEC). The combined chain
still runs this module in the same step, so the next EE build picks the re-home up.

Risk carried from history: the old 0x1A1D clone "could not be activated from hand, root
cause never found". ✅ Explained by test 1's root cause below (hand-effect list A); build 2
fixes it -- in-game confirmed by user 2026-09-17.

In-game oracles: (1) Fiend Kraken reads Thunder Sea Horse, LIGHT/Thunder/Lv4/1600/1200,
full text; (2) from hand the effect is offered only with ≥2 copies of a qualifying
name in Deck; (3) discards itself, pick list, adds 2 of the chosen name; (4) a second
activation the same turn refused; (5) no Special Summon later that turn; (6) not
offered if you already Special Summoned this turn; (7) Thunder Dragon is its real
self again (Lv5, 1600/1500, its own discard-search).

## Confirmed (this session, stock `rom.nds` + chained `rom_all_patches.nds`)

* Printed text (ygoprodeck_cache.json): "You can discard this card; add 2 Level 4
  LIGHT Thunder-Type monsters of the same name with 1600 or less ATK from your Deck
  to your hand. You can only use the effect of "Thunder Sea Horse" once per turn.
  You cannot Special Summon during the turn you activate this effect."
* Fiend Kraken 0x0FEC = Normal Monster, Lv4 WATER Aqua 1200/1400.
  `donor_scan 0x0FEC` → **CLEAN**. Its 8 ARM9 hits are smooth numeric curves
  (`0185 0FED 018B 0FED 0191 0FEC 0198 0FEC …` @0x0209D660), not cid tables. Its one
  ov3 hit 0x021D4A2A is inside a PC-relative jump table
  (`add r2,pc; ldrh r2,[r2,#6]; … add pc,r2` then offsets `0072 0198 01BE 01E2 038E 0FEC 1080 1096`),
  no u32 reference into it. No u32 literal 0x00000FEC anywhere → no native turn-log
  key collides with the SS-embargo/HOPT node key.
* Thunder Dragon 0x114F is named ONLY by cls2[48] @0x02276084, criteria row[76],
  fusion recipe A[47] (donor_scan). The current patch edits cls2 +04/+0C/+10 and the
  criteria row in place; the fusion recipe was never touched (so today "Thunder Sea
  Horse" is still Twin-Headed Thunder Dragon material — the re-home fixes that too).
* TD native cls2 row: `{0x114F, +04 0x0220B029, +08 0, +0C 0x021F0821, +10 0x021E6FD9, +14 0}`.
  Native criteria row: `{0x114F, 0xFFFF, 0x0223D075, 0x0E}`.
* +0C 0x021F0820 (disassembled): floodgate `bl 0x021BAD70(side^desc[6])`, then kid
  compare vs 0x1FC9 / 0x2049 / 0x2410 (need 3/3/2 candidates), everyone else needs 1;
  `0x02243FE0(side, kid, 0x02234E78(desc))` candidate count. 0x114F and 0x0FEC both
  take the default branch → identical behaviour. Otherwise cid-blind.
* +10 0x021E6FD8 (disassembled): `0x021A25A0(side, desc[+0xC])` → if >=0
  `0x021C6DB4(side, idx)` = discard self. Cid-blind.
* Our ov5 cond/res/main shims read kid from `desc[+0]`; only `_build_ssgate` hardcodes
  DONOR_CID. So the cave stubs are cid-agnostic except that one literal.
* Phantoms, both unclaimed in allocations.yaml / finished_patches, each present exactly
  once in stock AND chained images:
  - cls2: **0x0E9E** (stock idx 31, chain idx 25, record `{0x02206139,0,0,0,0}`)
  - criteria: **0x0EB0** (stock idx 63, record `{0xFFFF, 0x0223D501, 0x10002}`)
  0x0FEC sorts to cls2 idx 42 / criteria idx 71 (stock) → both inserts shift ≤ 11 rows.
* No per-cid gate on 0x0FEC found; no ledger claim on 0x0FEC or 0x114F.

### IN-GAME TEST 1 (user, 2026-09-17) — effect NOT offered in hand
User: "1. Confirmed 2. The card does not offer the option to activate in hand 3-6 Cannot
confirm 7. Did not confirm". Conditions: ≥2 qualifying copies in Deck, no SS that turn,
normal duel, own Main Phase. Savestate `rom_thunder_sea_horse.ml2`.

### ROOT CAUSE (static, from savestate RAM): hand-effect cid MEMBERSHIP LIST
* Savestate is the right build: cls2 donor row live `{0x0FEC, 0, 0x0239A8D9, 0, 0x0239A809, 0x0239A869, 0}`,
  cond shim bytes == built.
* Hand-menu flag builder (the function holding the hand-SS call @0x0224C026):
  `@0x0224C050 bl 0x0202354C(cid) ; beq skip ; bl 0x021EDD90(side, r7, cid) ; beq skip ; r5 |= 8`.
  Flag 0x8 = "activate effect". The cls2 record is only consulted AFTER the list test.
* ARM9 `0x0202354C(cid)` = `bsearch(0x0209BC4E, 0x1E) || bsearch(0x0209BC8C, 0x24)` via 0x02022E14.
  * **List A 0x0209BC4E x30, sorted** — the "discard this card from hand" family: 0x0EB2(PHANTOM), Kuriboh 0x0FE0,
    **Thunder Dragon 0x114F**, Charm of Shabti, King of the Swamp, D-Hero Blade Master, Cyber Ogre,
    Electric Virus, 0x1B42(PHANTOM), Marionette Mite, D.D. Crow, Captain Gold, GK Commandant,
    Warrior of Atlantis, Destroyersaurus, Zeradias, Archfiend General, Harpie Queen, Neo Space Pathfinder,
    Hecatrice, Temperance, Hanewata, Assault Beast, Lifeforce Harmonizer, AoJ Cycle Reader,
    Genex Ally Chemistrer, Swift Scarecrow, Wightmare, Gishki Vanity, Gishki Shadow.
    u32 refs: 0x02023544 (thunk 0x0202353C, count 0x1E, no BL callers found) and 0x0202356C.
  * List B 0x0209BC8C x36 = the ledger's `quickeffect_list`; its phantoms 0x0E63/0x1774/0x1A86 are all claimed.
* 0x0FEC is in neither list → 0x0202354C returns 0 → never offered. Thunder Dragon passes via list A[2].
  This also explains the old 0x1A1D clone failure in the docstring.
* donor_scan flagged arm9:0x0209BC52 for 0x114F as "ambiguous" — it was this list. ⚠️ donor_scan does
  not know these lists; a Normal donor's CLEAN verdict says nothing about them.

## Ruled Out
* "cls2 record + criteria row are sufficient for a hand ignition" — falsified in-game 2026-09-17 (test 1).
* ARM9 / ov3 donor_scan hits on 0x0FEC as cid references (see above).

## Open Questions
* None blocking. Text goes through `card_text.CARD_TEXT` re-emit (no slot limit).

## Next Experiment
None for the card. Remaining: EE chain build + verify sweep, only when the user asks.
