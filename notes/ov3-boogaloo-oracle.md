# ov3-boogaloo in-game oracle (AWAITING IN-GAME TEST)

ROM: see the session report (path + sha256). Every card below now runs its injected code from overlay 3
instead of the ov5 cave. Test EVERY clause in a **normal duel** AND in a **puzzle** (the new capability).

Failure modes to name if seen:
- freeze on trigger/activation (bad branch / Thumb-2)
- clause silently does nothing in BOTH modes (hook not retargeted)
- works in a duel but not in a puzzle (something still lives in ov5)
- black screen on the create-puzzle window

Also smoke-test: E-HERO Stratos search + destroy (step-0 sanity), and one of the earlier ov3 cards (e.g. Koa'ki Meiru Wall, T.G. Striker) -- step 0 changed (EXTRA_RUNS).

TEST-ROM HAZARD: this ROM leaves out the 32 cards that still use the ov5 cave, so their donors appear as their ORIGINAL cards. Do not play those donors here -- notably **Bracchio-raidus (0x11A3, the Accel Synchron donor)**: the shared deck-send follow hook (moved with Dragon Shrine) has an arm for 0x11A3 whose body slot is empty in this ROM. Not moved / not in this ROM: Eclipse Wyvern, Obedience Schooled, Seal of Orichalcos, Masked HERO Dark Law, W Nebula Meteorite, Pyrorex, Junk Speeder, Ninjitsu Art of Super-Transformation, Revolution Synchron, Double Evolution Pill, White Dragon Ninja, Dragunity Remus, Darkflare, Brilliant Fusion, Upstart Golden Ninja, Accel Synchron, Jet Warrior, Eva, Miscellaneousaurus, Ultimate Conductor Tyranno, Grapha, Wattkyuki, Shadow Mist, Accel Synchro Stardust Dragon, Animadorned Archosaur, Sea Lancer, Psi-Reflector, Overtex Qoatlus, Lightpulsar, Souleating Oviraptor, Jet Synchron, Ojamassimilation.

## Petiteranodon  (step module patch_petiteranodon, cid 0x0FE1)

> If this card is destroyed by a card effect and sent to the Graveyard: Special Summon 1 Level 4 or higher Dinosaur-Type monster from your Deck, but it cannot attack this turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Orient Dragon  (step module patch_orient_dragon, cid 0x0FCB)

> 1 Tuner + 1 or more non-Tuner monsters If this card is Synchro Summoned: Target 1 Synchro Monster your opponent controls; banish that target.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Ninja Grandmaster Hanzo  (step module patch_ninja_grandmaster_hanzo, cid 0x13E7)

> When this card is Normal Summoned: You can add 1 "Ninjitsu Art" card from your Deck to your hand. When this card is Flip or Special Summoned: You can add 1 "Ninja" monster from your Deck to your hand, except "Ninja Grandmaster Hanzo".

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Armory Arm  (patch_armory_arm, cid 0x1F33 -- bug fix, not a donor)

> Equipped monster destroys a monster by battle and sends it to the GY: inflict damage equal to the destroyed monster's ATK -- EVEN IF that monster has already left the GY when the burn resolves (the fix).

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Elder of the Six Samurai  (step module patch_elder_six_samurai, cid 0x11B7)

> If your opponent controls a monster and you control no monsters, you can Special Summon this card (from your hand).

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Junk Servant  (step module patch_junk_servant, cid 0x17CE)

> If you control a "Junk" monster, you can Special Summon this card (from your hand).

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Amazoness Heirloom  (step module patch_amazoness_heirloom, cid 0x2124)

> Equip only to an "Amazoness" monster. Once per turn, that monster cannot be destroyed by battle. After damage calculation, if the equipped monster attacks a monster: Destroy the attacked monster.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## The Gates of Dark World  (step module patch_gates_of_dark_world, cid 0x1C8B)

> All Fiend-Type monsters gain 300 ATK and DEF. Once per turn: You can banish 1 Fiend-Type monster from your Graveyard; discard 1 Fiend-Type monster, then draw 1 card.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Wattcobra  (step module patch_wattcobra, cid 0x0FD3)

> This card can attack your opponent directly. When this card inflicts Battle Damage to your opponent by a direct attack: Add 1 "Watt" monster from your Deck to your hand.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Safe Zone  (patch_safe_zone, cid 0x16A2)

> Activate this card by targeting 1 face-up Attack Position monster on the field; that face-up monster cannot be destroyed by battle or your opponent's card effects, your opponent cannot target it with card effects, also it cannot attack your opponent directly. When this card leaves the field, destroy that monster. When that monster leaves the field, destroy this card.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Snoww, Unlight of Dark World  (step module patch_snoww, cid 0x1C18)

> If this card is discarded to the Graveyard by a card effect: If it was discarded from your hand to your Graveyard by an opponent's card effect, you can target 1 monster in your opponent's Graveyard; add 1 "Dark World" card from your Deck to your hand, then Special Summon that target (if any) in face-up Defense Position.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## That Grass Looks Greener  (step module patch_that_grass_looks_greener, cid 0x10FD)

> If you have more cards in your Deck than your opponent does: Send cards from the top of your Deck to the Graveyard so you have the same number of cards in the Deck as your opponent.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Karakuri Muso mdl 818 "Haipa"  (step module patch_karakuri_haipa, cid 0x0FC8)

> This card must attack if able. When this face-up Attack Position card is selected as an attack target, change it to Defense Position. If this card attacks, it is changed to Defense Position at the end of the Battle Phase.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Shien's Dojo  (step module patch_shiens_dojo, cid 0x19B2)

> Each time a "Six Samurai" monster(s) is Normal or Special Summoned, place 1 Bushido Counter on this card. You can send this card to the GY; Special Summon 1 "Six Samurai" or "Shien" Effect Monster from your Main Deck, whose Level is less than or equal to the number of Bushido Counters on this card.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Mystic Piper  (step module patch_mystic_piper, cid 0x13B8)

> You can Tribute this card to draw and reveal 1 card. If that card is a Level 1 Monster Card, draw 1 more card. The effect of "Mystic Piper" can only be activated once per turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Crimson Blader  (step module patch_crimson_blader, cid 0x1179)

> 1 Tuner + 1 or more non-Tuner monsters If this card destroys an opponent's monster by battle and sends it to the Graveyard: Your opponent cannot Normal or Special Summon Level 5 or higher monsters during their next turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Unknown Synchron  (step module patch_unknown_synchron, cid 0x181C)

> If your opponent controls a monster and you control no monsters, you can Special Summon this card (from your hand). You can only Special Summon "Unknown Synchron" once per Duel this way.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Moulinglacia the Elemental Lord  (step module patch_moulinglacia, cid 0x1C1A)

> Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 WATER monsters in your GY. If this card is Special Summoned: Discard 2 random cards from your opponent's hand (or their entire hand, if less than 2). You can only use this effect of "Moulinglacia the Elemental Lord" once per turn. If this face-up card leaves the field, skip the Battle Phase of your next turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Ceruli, Guru of Dark World  (step module patch_ceruli, cid 0x1B3E)

> If this card is discarded to the Graveyard by a card effect: Special Summon this card from the Graveyard to your opponent's side of the field in face-up Defense Position. When this card is Special Summoned by the effect of a "Dark World" card: Your opponent must discard 1 card.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Soul Charge  (step module patch_soul_charge, cid 0x123D)

> Target any number of monsters in your GY; Special Summon them, and if you do, you lose 1000 LP for each monster Special Summoned by this effect. You cannot conduct your Battle Phase the turn you activate this card. You can only activate 1 "Soul Charge" per turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Windrose the Elemental Lord  (step module patch_windrose, cid 0x190B)

> Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 WIND monsters in your GY. If this card is Special Summoned: Destroy all Spells and Traps your opponent controls. You can only use this effect of "Windrose the Elemental Lord" once per turn. If this face-up card leaves the field, skip the Battle Phase of your next turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Cardcar D  (step module patch_cardcar_d, cid 0x0FAE)

> Cannot be Special Summoned. During your Main Phase 1, if this card was Normal Summoned this turn: You can Tribute this card; draw 2 cards, then it becomes the End Phase. You cannot Special Summon during the turn you activate this effect.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Naturia Pineapple  (step module patch_naturia_pineapple, cid 0x1465)

> All face-up monsters you control are treated as Plant-Type. During your Standby Phase, if you do not control a face-up "Naturia Pineapple", and have no monsters in your Graveyard except Plant or Beast-Type: You can Special Summon this card from your Graveyard. You must not control any Spell or Trap Cards to activate and resolve this effect.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Azure-Eyes Silver Dragon  (step module patch_azure_eyes, cid 0x1E9C)

> 1 Tuner + 1+ non-Tuner Normal Monsters If this card is Special Summoned: Until the end of the next turn, neither player can target Dragon monsters you currently control with card effects, also they cannot be destroyed by card effects. Once per turn, during your Standby Phase: You can target 1 Normal Monster in your GY; Special Summon it.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Shooting Quasar Dragon  (step module patch_shooting_quasar, cid 0x211B)

> 1 Tuner Synchro Monster + 2 or more non-Tuner Synchro Monsters Must be Synchro Summoned, and cannot be Special Summoned by other ways. This card's maximum number of attacks per Battle Phase equals the number of non-Tuner monsters used as its Synchro Material. Once per turn, during either player's turn, when a card or effect is activated: You can negate the activation, and if you do, destroy it. When this card leaves the field: You can Special Summon 1 "Shooting Star Dragon" from your Extra Deck.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Wattuna  (step module patch_wattuna, cid 0x1050)

> This card can attack directly. You can only use each of the following effects of "Wattuna" once per turn. At the end of the Damage Step, if your monster inflicts battle damage to your opponent: You can Special Summon this card from your hand. When this card inflicts battle damage to your opponent by a direct attack: You can Tribute this card on the field and 1 or more non-Tuner monsters from your hand and/or face-up field, and Special Summon 1 "Watt" Synchro Monster from your Extra Deck whose Level equals the total Levels of those Tributed monsters.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Life Stream Dragon  (step module patch_life_stream_dragon, cid 0x18FA)

> 1 Tuner + "Power Tool Dragon" When this card is Synchro Summoned: You can make your LP become 4000. You take no effect damage. If this face-up card on the field would be destroyed, you can banish 1 Equip Spell Card from your Graveyard instead.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Kuribandit  (step module patch_kuribandit, cid 0x0FD5)

> During the End Phase, if this card was Normal Summoned this turn: You can Tribute this card; excavate the top 5 cards of your Deck, you can add 1 excavated Spell/Trap to your hand, also send the remaining cards to the GY.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Maiden with Eyes of Blue  (step module patch_maiden_eyes_of_blue, cid 0x1ED7)

> When a card or effect is activated that targets this card (Quick Effect): You can Special Summon 1 "Blue-Eyes White Dragon" from your hand, Deck, or GY. When this card is targeted for an attack: You can negate the attack, and if you do, change the battle position of this card, then you can Special Summon 1 "Blue-Eyes White Dragon" from your hand, Deck, or GY. You can only use 1 "Maiden with Eyes of Blue" effect per turn, and only once that turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Assault Synchron  (step module patch_assault_synchron, cid 0x13AE)

> During your Main Phase: You can Special Summon this card from your hand, then take 700 damage, also you cannot Special Summon monsters from the Extra Deck, except Synchro Monsters, while this card is face-up in the Monster Zone. If a face-up Dragon Synchro Monster(s) you control is Tributed or banished (except during the Damage Step): You can banish this card from your GY, then target 1 of those monsters; Special Summon it. You can only use each effect of "Assault Synchron" once per turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Mara of the Nordic Alfar  (step module patch_mara, cid 0x106C)

> When using this card as Synchro Material, the other Synchro Materials must be 2 "Nordic" monsters in your hand.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Raiden, Hand of the Lightsworn  (step module patch_raiden, cid 0x0FD2)

> During your Main Phase: You can send the top 2 cards of your Deck to the GY, then if any "Lightsworn" monsters were sent to the GY by this effect, this card gains 200 ATK until the end of your opponent's turn. You can only use this effect of "Raiden, Hand of the Lightsworn" once per turn. Once per turn, during your End Phase: Send the top 2 cards of your Deck to the GY.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Dragon Shrine  (step module patch_dragon_shrine, cid 0x14C1)

> Send 1 Dragon monster from your Deck to the GY, then, if that monster in your GY is a Dragon Normal Monster, you can send 1 more Dragon monster from your Deck to the GY. You can only activate 1 "Dragon Shrine" per turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## T.G. Hyper Librarian  (step module patch_hyper_librarian, cid 0x2338)

> 1 Tuner + 1+ non-Tuner monsters If a monster is Synchro Summoned: Draw 1 card. This card must be face-up on the field to activate and to resolve this effect.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Thunder Sea Horse  (step module patch_thunder_sea_horse, cid 0x0FEC)

> You can discard this card; add 2 Level 4 LIGHT Thunder-Type monsters of the same name with 1600 or less ATK from your Deck to your hand. You can only use the effect of "Thunder Sea Horse" once per turn. You cannot Special Summon during the turn you activate this effect.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Karakuri Komachi mdl 224 "Ninishi"  (step module patch_ninishi, cid 0x0FFD)

> This card must attack if able. When this face-up card is selected as an attack target, change its battle position. While this card is face-up on the field, once per turn during your Main Phase, you can Normal Summon 1 "Karakuri" monster in addition to your Normal Summon or Set. (You can only gain this effect once per turn.)

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Scrap Raptor  (step module patch_scrap_raptor, cid 0x0FF6)

> You can target 1 monster you control; destroy it, also, during your Main Phase this turn, you can Normal Summon 1 "Scrap" monster in addition to your Normal Summon/Set. If this card is destroyed by the effect of a "Scrap" card and sent to your GY: You can add 1 non-Tuner "Scrap" monster from your Deck to your hand. You can only use each effect of "Scrap Raptor" once per turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause

## Grandsoil the Elemental Lord  (step module patch_grandsoil, cid 0x1110)

> Cannot be Normal Summoned/Set. Must be Special Summoned (from your hand) by having exactly 5 EARTH monsters in your GY. When this card is Special Summoned: You can target 1 monster in either player's GY; Special Summon that target. You can only use this effect of "Grandsoil the Elemental Lord" once per turn. If this face-up card leaves the field, skip the Battle Phase of your next turn.

- [ ] normal duel: every clause
- [ ] puzzle: every clause
