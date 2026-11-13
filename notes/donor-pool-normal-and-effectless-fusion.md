# Donor pool: vanilla Normal Monsters and effectless Fusion Monsters

Generated 2026-09-22 from `steps.py` (STEPS list) cross-referenced against
`scratch/ygoprodeck_cache.json`. **Not yet cross-checked against the actual NDS
card table** — before proposing a candidate below as a donor, still run the full
Donor Card Selection checklist in CLAUDE.md (records-free, blob length, no per-cid
gates). This resource only narrows the search space by card type.

## Used as donors (already spent, in STEPS build order)

### Vanilla Normal Monsters (38)

- The Portrait's Secret
- Molten Behemoth
- Flame Dancer
- Battle Steer
- Rock Ogre Grotto #1
- Wattkid
- Dark Chimera
- Flame Cerebrus
- Hitotsu-Me Giant
- Divine Dragon Ragnarok
- Sword Arm of Dragon
- Battle Footballer
- Renge, Gatekeeper of Dark World
- Zure, Knight of Dark World
- Saggi the Dark Clown
- Melchid the Four-Face Beast
- Dunames Dark Witch
- The Gross Ghost of Fled Dreams
- Neo Aqua Madoor
- Woodborg Inpachi
- Cyber-Tech Alligator
- Mushroom Man
- Boneheimer
- Torike
- Shapesnatch
- Clown Zombie
- Dark Rabbit
- Headless Knight
- Acrobat Monkey
- Petit Dragon
- Two-Headed King Rex
- Mammoth Graveyard
- Rogue Doll
- Ryu-Kishin Powered (Elemental HERO Shadow Mist, 2026-09-28 -- still listed in
  `scratch/donor_resource.json` `candidate_normal`; treat it as spent)
- Sengenjin (Ultimate Conductor Tyranno, 2026-09-28)
- Swordsman of Landstar (Animadorned Archosaur, 2026-09-29 -- removed from
  `scratch/donor_resource.json` `candidate_normal`)
- Prevent Rat (Overtex Qoatlus, 2026-09-29)
- Aitsu (Eva, 2026-10-05 -- removed from `scratch/donor_resource.json` `candidate_normal`)
- Happy Lover (Mara of the Nordic Alfar, 2026-10-05 -- removed from `scratch/donor_resource.json` `candidate_normal`)
- Spirit of the Harp (Wattuna, 2026-10-05 -- moved to `scratch/donor_resource.json` `used_normal`)
- Basic Insect (-> Metal Armored Bug, stats + text; was missing from this list and
  re-offered by `donor_scan --free` until 2026-10-05 -- do NOT offer it)
- Millennium Shield 0x1110 (-> Grandsoil the Elemental Lord, 2026-10-06)
- Venom Cobra 0x1C1A (-> Moulinglacia the Elemental Lord, 2026-10-06)
- Harpie Girl 0x181F (-> Pyrorex the Elemental Lord, 2026-10-06 -- moved to `scratch/donor_resource.json` `used_normal`)
- Soitsu 0x190B (-> Windrose the Elemental Lord, 2026-10-06 -- moved to `scratch/donor_resource.json` `used_normal`)
- Illusionist Faceless Mage 0x0FD0 (-> Uni-Zombie, 2026-10-12 -- moved to `scratch/donor_resource.json` `used_normal`)
- Souleater 0x13AC (-> Aratama, 2026-10-12 -- moved to `scratch/donor_resource.json` `used_normal`)
- Grand Tiki Elder 0x13E5 (-> Sakitama, 2026-10-13 -- moved to `scratch/donor_resource.json` `used_normal`)
- Wolf 0x0FE3 (-> Nikitama, 2026-10-13 -- moved to `scratch/donor_resource.json` `used_normal`)
- Kanan the Swordmistress 0x1106 (-> Neo Space Connector, 2026-10-14 -- moved to `scratch/donor_resource.json` `used_normal`)
- Aqua Madoor 0x107B (-> Magician's Rod, PARKED, not shipped -- listed so it is not re-offered)
- Charcoal Inpachi 0x17CD (-> Redox, Dragon Ruler of Boulders, 2026-10-16 -- moved to `scratch/donor_resource.json` `used_normal`)
- Mech Bass 0x115F (-> Tidal, Dragon Ruler of Waterfalls, 2026-10-16 -- moved to `scratch/donor_resource.json` `used_normal`)
- Mechanicalchaser 0x1145 (-> Blaster, Dragon Ruler of Infernos, 2026-10-16 -- moved to `scratch/donor_resource.json` `used_normal`)
- Parrot Dragon 0x1125 (-> Tempest, Dragon Ruler of Storms, 2026-10-16 -- moved to `scratch/donor_resource.json` `used_normal`)
- Axe Raider 0x0FF4 (-> Reactan, Dragon Ruler of Pebbles, 2026-10-16 -- moved to `scratch/donor_resource.json` `used_normal`)
- 7 Colored Fish 0x115E (-> Stream, Dragon Ruler of Droplets, 2026-10-16 -- moved to `scratch/donor_resource.json` `used_normal`)
- Garoozis 0x0FEA (-> Burner, Dragon Ruler of Sparks, 2026-10-16 -- moved to `scratch/donor_resource.json` `used_normal`)
- Atlantean Pikeman 0x1CC6 (-> Lightning, Dragon Ruler of Drafts, 2026-10-16 -- moved to `scratch/donor_resource.json` `used_normal`)
- Kojikocy 0x0FE8 (-> Denko Sekka, SHIPPED 2026-10-18 on user approval; in-game test not reported)
- Monster Tamer 0x111E (-> Disguise, the Copycat Hero, SHIPPED 2026-11-04 on user approval; in-game test not reported;
  Lv5 1800 ATK -- the user ASKED for Level 5/6 donors here, an exception to the ATK <= 1500 rule)
- Armored Lizard 0x0FD9 (-> Noble Knight Medraut, SHIPPED 2026-11-04, all effects in-game confirmed by user 2026-11-04)
- Jellyfish 0x0FED (-> Predaplant Darlingtonia Cobra, SHIPPED 2026-11-06 on user approval, no art yet, in-game test not reported)
- Skull Dog Marron 0x17CF (-> Predaplant Ophrys Scorpio, SHIPPED 2026-11-06 on user approval, no art yet, in-game test not reported)
- Giant Flea 0x0FDD (-> Block Dragon, SHIPPED 2026-11-09: whole card in-game confirmed by user 2026-11-09; CPU play for the Elemental Lords / Dragon Rulers split into cards.cpu_hand_ss)
- (Equip Spell donor, outside this list: Invigoration 0x10EA -> Phoenix Gearblade, SHIPPED 2026-11-06 on user approval ("it works now"))
- Judge Man 0x0FC7 (-> Immortal Phoenix Gearfried, SHIPPED 2026-11-04, whole card in-game confirmed by user 2026-11-04; Lv6 2200 ATK -- the user CHOSE it, an exception to the ATK <= 1500 rule)

(Spell donor, outside this file's scope but noted so it is not re-offered: Stop Defense 0x10E6 -> Sekka's Light,
SHIPPED 2026-10-18, whole card in-game confirmed by user. Marshmallon Glasses 0x1777 -> Fire Formation - Tenki,
SHIPPED 2026-10-19, whole card in-game confirmed by user. Cyber Shield 0x10E3 (Equip Spell) -> Cursed Copycat Noble Arms,
SHIPPED 2026-11-04 on user approval, in-game test not reported. Mage Power was VETOED by the user, do not offer it.)

### Effectless Fusion Monsters (9)

- Twin-Headed Thunder Dragon (-> Junk Speeder, 2026-09-22; was left in "Candidates" by mistake until 2026-10-05)
- St. Joan (-> Wattkyuki, 2026-10-05)
- Bracchio-raidus
- Humanoid Worm Drake
- Gaia the Dragon Champion
- Meteor Black Dragon
- Crimson Sunbird
- Aqua Dragon (-> Masked HERO Dark Law, 2026-09-28)
- Bickuribox (-> Elder Entity Norden, 2026-09-28)
- Steam Gyroid (-> Life Stream Dragon, 2026-10-01; also removed from the "roid" set-code list)
- B. Skull Dragon 0x107F (-> Coral Dragon, 2026-11-09, user-chosen despite 3200 ATK; test ROM only; also removed from the "Archfiend" set-code list)

Note: `Ally Mind` (Normal Tuner Monster) is also effectively vanilla — a Tuner
flag with no effect text — but is tracked separately since it isn't type `Normal Monster`.

## Candidates for future patches (unused, by type — NOT vetted for ROM presence)

### Vanilla Normal Monsters: 639 in the ygoprodeck cache

Full list dumped to `scratch/donor_resource.json` (`candidate_normal`) — too many to
hand-review here. Filter by: exists in the NDS ROM card table, not competitively
playable (per CLAUDE.md), name+desc blob length >= replacement text.

### Effectless Fusion Monsters: 43 (filtered to Level 6+)

Level filter applied 2026-09-22 — all 5 already-used effectless Fusion donors
(Bracchio-raidus Lv6, Humanoid Worm Drake Lv7, Gaia the Dragon Champion Lv7,
Meteor Black Dragon Lv8, Crimson Sunbird Lv6) are Level 6-8, so candidates
below are held to that same floor. Useful when the target effect needs an
Extra Deck donor (leave-hook trampoline, not cls2 dispatch — see CLAUDE.md).

⚠️ donor_scan 2026-09-28: these have a fusion recipe row but NO card_prop row, i.e. they are
NOT in the NDS card pool and cannot be donors: Metal Dragon, Skelgon, Skullbird, Mystical Sand,
Punished Eagle, Rose Spectre of Dunn, Soul Hunter, Great Mammoth of Goldfine, Kaiser Dragon,
Warrior of Tradition (Skull Knight / Empress Judge / Roaring Ocean Snake don't resolve at all).

- **Master of Oz** (Lv9) — "Big Koala" + "Des Kangaroo"
- **Kaiser Dragon** (Lv7) — "Winged Dragon, Guardian of the Fortress #1" + "Fairy Dragon"
- **Labyrinth Tank** (Lv7) — "Giga-Tech Wolf" + "Cannon Soldier"
- **Skull Knight** (Lv7) — "Tainted Wisdom" + "Ancient Brain"
- **Thousand Dragon** (Lv7) — "Time Wizard" + "Baby Dragon"
- **Empress Judge** (Lv6) — "Queen's Double" + "Hibikime"
- **Great Mammoth of Goldfine** (Lv6) — "The Snake Hair" + "Dragon Zombie"
- **Metal Dragon** (Lv6) — "Steel Ogre Grotto #1" + "Lesser Dragon"
- **Mystical Sand** (Lv6) — "Giant Soldier of Stone" + "Ancient Elf"
- **Punished Eagle** (Lv6) — "Blue-Winged Crown" + "Niwatori"
- **Rabid Horseman** (Lv6) — "Battle Ox" + "Mystic Horseman"
- **Roaring Ocean Snake** (Lv6) — "Mystic Lamp" + "Hyosube"
- **Rose Spectre of Dunn** (Lv6) — "Feral Imp" + "Snakeyashi"
- **Skelgon** (Lv6) — "The Snake Hair" + "Blackland Fire Dragon"
- **Skullbird** (Lv6) — "Takuhee" + "Temple of Skulls"
- **Soul Hunter** (Lv6) — "Lord of the Lamp" + "Invader from Another Dimension"
- **Warrior of Tradition** (Lv6) — "Sonic Maid" + "Beautiful Headhuntress"
