# In-game test checklist — Erebus / Ehther / Escalation / The Prime Monarch (test ROM only, nothing shipped)

ROM: `data/over_the_nexus/working/rom_monarch_erebus.nds` (sha256 2bf21b13a57d95ed7e02e638d13cbfe1c13a996a084155acb20d5a3aefb77aaf, 22 Monarch modules on rom_chain_19C00).
Everything below was CPU-traced in the emulator only (notes/ehther-erebus-findings.md, notes/escalation-findings.md); the human UI paths are untested. Report in the CLAUDE.md format (your words are quoted back verbatim first).
Deck idea: empty Extra Deck, Zaborg/Caius/Raiza, Erebus x2, Ehther x2, March / Stormforth / Pantheism / Tenacity / Return (Monarch Spell/Trap), Escalation x1, The Prime Monarch x1, some 2400/1000 monsters in the Deck.

## Erebus the Underworld Monarch (0x1313, DARK Zombie Lv8 2800/1000)
1. Tribute Summon it by Tributing ONE Tribute Summoned monster (alternate Tribute): works?
2. When Tribute Summoned: "You can" prompt. Cost: a list of Monarch Spell/Traps from hand AND Deck together; pick 2 with different names (the second pick must not offer the first one's name). Does the mixed list picker open and not freeze?
3. Then: pick a card from the OPPONENT'S GRAVEYARD -> it goes to their Deck, their Deck is shuffled. (Opponent hand-random and field halves are NOT built.)
4. From your GY (Main Phase, either player's): discard a Monarch Spell/Trap, target a 2400+/1000 monster in your GY, add it to hand; once per turn. Offered in the OPPONENT's Main Phase too?

## Ehther the Heavenly Monarch (0x1312, LIGHT Fairy Lv8 2800/1000)
1. Same M0 / trigger / cost as Erebus. Then a 2400+/1000 monster from the Deck is Special Summoned and RETURNS TO YOUR HAND in the End Phase.
2. From the hand in the OPPONENT's Main Phase: banish a Monarch Spell/Trap from your GY, then Ehther is Tribute Summoned (Quick Effect). Offered at all? (no CPU evidence)

## Escalation of the Monarchs (0x1800, Continuous Trap)
Set it. In the OPPONENT's Main/Battle Phase, once per turn: pick a Level 5+ monster in your hand and Tribute Summon it (Tribute selection UI). Offered? Only Level 5+? Not Set?

## The Prime Monarch (0x14CF, Continuous Trap)
Once per turn: pick 2 Monarch Spell/Traps from your GY (list picker) -> back to the Deck, shuffle, draw 1. (Not a targeting effect here.)
GY half (BUILT 2026-11-12 in rom_monarch_prime.nds only, sha256 871f86b9...; CPU-traced: cost, GY Special Summon, Trap-Monster stats path): with The Prime Monarch AND another Monarch Spell/Trap in your GY, in your Main Phase the GY effect should be offered; pay = banish the OTHER Monarch S/T (picker; The Prime Monarch itself must not be listed), then it is Special Summoned in DEFENSE Position as a Fairy / LIGHT / Level 5 / ATK 1000 / DEF 2400 monster. Once per turn. While it is a monster its shuffle-and-draw effect must NOT be offered. Failures to tell apart: never offered; offered but freezes; summoned with wrong stats (Level 1 / 0 / 0 = the old phantom arm); summoned in Attack Position; the Prime Monarch itself banished as the cost. KNOWN DEVIATIONS: it is still a Trap Card while a monster and not typed "Normal Monster". A 2nd copy of The Prime Monarch in the GY IS a legal cost (only the activating card is excluded).

## NEWEST ROM (use this one): rom_monarch_art.nds (sha256 c41ac95b...) = rom_monarch_eidos.nds + card art for all 30 Monarch cards (only Data_arc_pac/card.pac differs; arm9 / overlays identical). Art is test-build only (scratch/_monarch_session.py MONARCH_ARTS), NOT in card_art.CARDS.
## Previous: rom_monarch_eidos.nds (sha256 fa81552f...) -- everything below + Eidos' remaining effects + Masterplan's banished effect + never-miss-timing for all 30 Monarch cards
- Eidos the Underworld Monarch E1: when Normal / Special Summoned, the add list should now include "Monarch" Spell/Traps and 2800/1000 monsters from your GY as well as your Deck.
- Eidos E3: with Eidos in your GY, Tribute Summon a 2400+/1000 monster -> "Add it to your hand." / "Special Summon it." menu (CPU-traced: the add-to-hand branch).
- The Monarchs Masterplan, banished: banish it (e.g. as The Prime Monarch's GY cost, Ehther's or Perfection's) -> you should be offered: pick an opponent's face-up monster -> pick a same-Attribute 2400/1000 monster from your Deck or GY -> it is added -> if you hold Zaborg / Mobius / Thestalos / Granmarg / Raiza / Caius (the original Monarchs) that can be Normal Summoned: "Normal Summon a Monarch." / "Do not activate effect." NEVER EXERCISED BY THE CPU. Known deviation: the opponent's monster is chosen when the effect resolves, not targeted on activation.
- Missed timing: every optional "If/When ...: You can" trigger of the 30 new Monarch cards should now be offered even when the summon / send was not the last thing to happen (e.g. Erebus Tribute Summoned by Escalation or Ehther's Quick Effect mid-chain, Eidos Summoned by an effect). Mobius, Angmarl and Return of the Monarchs print "When ...: You can" and were included on request.

## Monarchic Perfection (0x12F6 on Call of the Grave, Continuous Trap) -- ONLY in rom_monarch_perfection.nds (sha256 61fdd31e..., also contains everything in rom_monarch_prime.nds)
Activate it (face-up), control a Tribute Summoned monster, have a "Monarch" Spell/Trap in your GY. When your OPPONENT Special Summons: you should be offered the effect -> pick a Monarch S/T in your GY to banish -> menu "Use which effect?" with up to 3 effects + "Show other effects." (page 2 = face-down / top of Deck / banish) -> pick the target(s) on the field -> it happens. Each effect once per turn (an effect already used, or with nothing to act on, is greyed out / missing).
Failures to tell apart: never offered; offered on YOUR own Special Summons (wrong side); menu labels blank or garbage (the 7 new dialog strings are not read); wrong card destroyed / moved; "Discard 1 random card" takes from your hand instead of theirs; freezes.
KNOWN DEVIATIONS: "once per Chain" and "except during the Damage Step" are not enforced; the CPU does not activate its own Set copy.

(Erebus E1 hand/field halves, The First Monarch and the Prime Monarch GY half have since been built -- see their sections.)

## The First Monarch (0x249B, Continuous Trap = native Trap Monster on Tiki Soul)
1. Activate it: it is Special Summoned as an Effect Monster (Fiend / DARK / Level 6 / ATK 1000 / DEF 2400) and stays a Trap Card too. (Stats not read back yet; if it shows Tiki Soul's 1000/1800 Rock LIGHT, the stat arm is not reached.)
2. "You can" prompt: discard 1 card, then declare an Attribute (the list picker for the discard + the Attribute prompt). The monster should show the declared Attribute afterwards (permanent rider: UNVERIFIED).
3. Tribute Summon a monster with the SAME Attribute as the First Monarch: the First Monarch should count as 2 Tributes.
4. While it is on the field: Special Summons of monsters with a DIFFERENT base Attribute should fail (they bail out at the engine, not hidden from the menu).
Also not built: Prime Monarch GY half, Monarchic Perfection, Erebus E1 opponent hand/field halves.
