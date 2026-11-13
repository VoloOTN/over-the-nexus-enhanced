# AI rule table - priority order

Table at **0x02275510** (overlay-3 image offset 0x133E10): 181 records of
`{u32 fn, u32 arg}`, stride 8, spanning 0x02275510-0x02275AB8.

Walked top-down by the loop at 0x0224820C. Each rule is called as
`fn(arg)`; the **first one to return nonzero picks the AI's move** and the
rest are never evaluated. So **lower index = higher priority**.

`arg` is a cid. The table is byte-identical for every CPU opponent
(verified across 5 savestates / 2 different duelists).

Names resolved via card_prop.bin `card_id` -> row, then card_name_e.bin
at row+2. Spot-checked: 0x1DC1 Gyzarus, 0x20B7 Moja, 0x1C76 Laquari,
0x2338 Scarred Warrior - all agree with independent sources.

| # | fn | cid | card | type |
|---:|---|---|---|---|
| 0 | 0x02244191 | - | **(generic rule)** | |
| 1 | 0x02247C95 | 0x1D08 | Gladiator Beast Darius | Effect Monster |
| 2 | 0x02247CCD | 0x0EAD | ? |  |
| 3 | 0x02247CCD | 0x1D14 | Rainbow Veil | Spell Card |
| 4 | 0x02247CCD | 0x1FEE | Koa'ki Meiru Powerhand | Effect Monster |
| 5 | 0x02247CCD | 0x200D | Double Tool C&D | Spell Card |
| 6 | 0x022475B9 | 0x15F6 | Rivalry of Warlords | Trap Card |
| 7 | 0x022478CD | 0x15F6 | Rivalry of Warlords | Trap Card |
| 8 | 0x022475B9 | 0x1EFE | Gozen Match | Trap Card |
| 9 | 0x022478CD | 0x1EFE | Gozen Match | Trap Card |
| 10 | 0x02247725 | 0x23AC | Mirror of the Ice Barrier | Spell Card |
| 11 | 0x02247855 | 0x1468 | Destiny Board | Trap Card |
| 12 | 0x02247855 | 0x17AF | The First Sarcophagus | Trap Card |
| 13 | 0x02247F41 | - | **(generic rule)** | |
| 14 | 0x02246AE9 | - | **(generic rule)** | |
| 15 | 0x02247F9D | 0x1DD4 | Limit Reverse | Trap Card |
| 16 | 0x02245265 | - | **(generic rule)** | |
| 17 | 0x022457BD | 0x1A9C | Brainwashing Beam | Trap Card |
| 18 | 0x022457BD | 0x1C84 | Alien Hypno | Gemini Monster |
| 19 | 0x02245C49 | 0x0E0B | Speed Edge | Trap Card |
| 20 | 0x02245C49 | 0x0E30 | ? |  |
| 21 | 0x02245C49 | 0x0E46 | ? |  |
| 22 | 0x02245C49 | 0x0E4C | ? |  |
| 23 | 0x02245C49 | 0x0E51 | ? |  |
| 24 | 0x02245C49 | 0x0E56 | ? |  |
| 25 | 0x02245C49 | 0x158B | Gravekeeper's Chief | Effect Monster |
| 26 | 0x02245C49 | 0x160F | Amazoness Tiger | Effect Monster |
| 27 | 0x02245C49 | 0x1BD7 | Field Barrier | Spell Card |
| 28 | 0x02245C49 | 0x1BE9 | Grandmaster of the Six Samurai | Effect Monster |
| 29 | 0x02245C49 | 0x0E9F | ? |  |
| 30 | 0x02245C49 | 0x1D3C | Dragon Ice | Effect Monster |
| 31 | 0x02245C49 | 0x1D66 | Winged Kuriboh LV9 | Effect Monster |
| 32 | 0x02245C49 | 0x1E66 | Alector, Sovereign of Birds | Effect Monster |
| 33 | 0x02245C49 | 0x1E73 | Guardian of Order | Effect Monster |
| 34 | 0x02245C49 | 0x1F61 | Alien Overlord | Effect Monster |
| 35 | 0x02245C49 | 0x1F91 | Rai-Jin | Effect Monster |
| 36 | 0x02245C49 | 0x1F97 | Ido the Supreme Magical Force | Effect Monster |
| 37 | 0x02245C49 | 0x206C | Jester Confit | Effect Monster |
| 38 | 0x02245C49 | 0x20A5 | Imperial Custom | Trap Card |
| 39 | 0x02245C49 | 0x20B9 | King of the Beasts | Effect Monster |
| 40 | 0x02245C49 | 0x1FEB | Earthbound Immortal Aslla piscu | Effect Monster |
| 41 | 0x02245C49 | 0x1FEC | Earthbound Immortal Ccapac Apu | Effect Monster |
| 42 | 0x02245C49 | 0x2073 | Earthbound Immortal Cusillu | Effect Monster |
| 43 | 0x02245C49 | 0x2074 | Earthbound Immortal Chacu Challhua | Effect Monster |
| 44 | 0x02245C49 | 0x210B | Earthbound Immortal Ccarayhua | Effect Monster |
| 45 | 0x02245C49 | 0x210C | Earthbound Immortal Uru | Effect Monster |
| 46 | 0x02245C49 | 0x210D | Earthbound Immortal Wiraqocha Rasca | Effect Monster |
| 47 | 0x02245C49 | 0x21B5 | Reptilianne Vaskii | Effect Monster |
| 48 | 0x02245C49 | 0x22A0 | Malefic Blue-Eyes White Dragon | Effect Monster |
| 49 | 0x02245C49 | 0x22A1 | Malefic Stardust Dragon | Effect Monster |
| 50 | 0x02245C49 | 0x22A3 | Malefic Paradox Dragon | Synchro Effect Monster |
| 51 | 0x02245C49 | 0x22BC | Malefic Red-Eyes B. Dragon | Effect Monster |
| 52 | 0x02245C49 | 0x2351 | Malefic Cyber End Dragon | Effect Monster |
| 53 | 0x02245C49 | 0x2352 | Malefic Truth Dragon | Effect Monster |
| 54 | 0x02245C49 | 0x2354 | Malefic Rainbow Dragon | Effect Monster |
| 55 | 0x02246129 | - | **(generic rule)** | |
| 56 | 0x02244D99 | 0x1343 | Kotodama | Effect Monster |
| 57 | 0x02246845 | 0x169A | Falling Down | Spell Card |
| 58 | 0x02246935 | 0x0EC4 | ? |  |
| 59 | 0x02246935 | 0x13F7 | Tornado Wall | Trap Card |
| 60 | 0x02246935 | 0x1DE2 | Sanguine Swamp | Trap Card |
| 61 | 0x02246935 | 0x227E | Electromagnetic Shield | Spell Card |
| 62 | 0x02245AB9 | - | **(generic rule)** | |
| 63 | 0x022445A9 | - | **(generic rule)** | |
| 64 | 0x02245F31 | 0x0E9A | ? |  |
| 65 | 0x02245F31 | 0x123B | Crush Card Virus | Trap Card |
| 66 | 0x02245F31 | 0x188C | Deck Devastation Virus | Trap Card |
| 67 | 0x02245F31 | 0x1BF1 | Eradicator Epidemic Virus | Trap Card |
| 68 | 0x02245F31 | 0x18DB | Grave Lure | Trap Card |
| 69 | 0x02246E69 | 0x0E12 | ? |  |
| 70 | 0x02246DCD | 0x1817 | Silent Magician LV4 | Effect Monster |
| 71 | 0x02246DCD | 0x1DC5 | D - Formation | Spell Card |
| 72 | 0x02246ECD | 0x1E95 | Worm Gulse | Effect Monster |
| 73 | 0x022473AD | 0x1A8D | Miracle Jurassic Egg | Effect Monster |
| 74 | 0x022473B9 | 0x1C93 | "A" Cell Incubator | Spell Card |
| 75 | 0x022473B9 | 0x1FD2 | Code A Ancient Ruins | Spell Card |
| 76 | 0x022473C5 | 0x1D22 | Six Samurai United | Spell Card |
| 77 | 0x022473C5 | 0x247E | Temple of the Six | Spell Card |
| 78 | 0x022473D1 | 0x219A | Gateway of the Six | Spell Card |
| 79 | 0x022473DD | 0x1DCA | Realm of Light | Spell Card |
| 80 | 0x022473E9 | 0x1E97 | Worm Illidan | Effect Monster |
| 81 | 0x022473F5 | 0x1EEA | The World Tree | Spell Card |
| 82 | 0x02247401 | 0x1F6D | Morphtronic Map | Spell Card |
| 83 | 0x0224740D | 0x1F74 | Seed Cannon | Spell Card |
| 84 | 0x02247419 | 0x1F78 | Arcane Barrier | Spell Card |
| 85 | 0x02247425 | 0x21DC | Machine Assembly Line | Spell Card |
| 86 | 0x0224743D | 0x2206 | Genex Ally Bellflame | Effect Monster |
| 87 | 0x02247431 | 0x23A5 | Karakuri Anatomy | Spell Card |
| 88 | 0x022444D5 | 0xFFFFFFFF | **(sentinel)** | |
| 89 | 0x02247C01 | - | **(generic rule)** | |
| 90 | 0x02246091 | 0x1510 | Convulsion of Nature | Spell Card |
| 91 | 0x02248065 | - | **(generic rule)** | |
| 92 | 0x022474DD | - | **(generic rule)** | |
| 93 | 0x022475B9 | 0x17EE | Ojama King | Fusion Effect Monster |
| 94 | 0x022475B9 | 0x1C0B | Ojama Knight | Fusion Effect Monster |
| 95 | 0x022475B9 | 0x1DBE | Phantom Dragon | Effect Monster |
| 96 | 0x0224779D | 0x207A | Scary Moth | Effect Monster |
| 97 | 0x02245929 | 0x1405 | Solemn Wishes | Trap Card |
| 98 | 0x02244C5D | 0x1306 | Magical Thorn | Trap Card |
| 99 | 0x02244FB1 | 0x1361 | Skull Invitation | Trap Card |
| 100 | 0x02244FB1 | 0x14BF | Fatal Abacus | Trap Card |
| 101 | 0x022459E1 | 0x144D | Fire Princess | Effect Monster |
| 102 | 0x02244B91 | 0x12FB | Call of Darkness | Trap Card |
| 103 | 0x02245E8D | 0x14FC | Gradius' Option | Effect Monster |
| 104 | 0x022462C5 | 0x1624 | Pitch-Black Power Stone | Trap Card |
| 105 | 0x02246391 | 0x1BFC | Venom Swamp | Spell Card |
| 106 | 0x02246A2D | - | **(generic rule)** | |
| 107 | 0x022443B1 | 0x0EB7 | ? |  |
| 108 | 0x022443B1 | 0x16DA | Soul Absorption | Spell Card |
| 109 | 0x022443BD | 0x159B | Dark Room of Nightmare | Spell Card |
| 110 | 0x02244431 | 0x142C | Spring of Rebirth | Spell Card |
| 111 | 0x02244431 | 0x17A4 | Blessings of the Nile | Spell Card |
| 112 | 0x02244431 | 0x151A | Spirit's Invitation | Trap Card |
| 113 | 0x02244431 | 0x1574 | Coffin Seller | Trap Card |
| 114 | 0x02244431 | 0x1A51 | Cyber Summon Blaster | Trap Card |
| 115 | 0x02244431 | 0x1C68 | Natural Disaster | Trap Card |
| 116 | 0x02244431 | 0x1CDF | Crystal Tree | Spell Card |
| 117 | 0x02244431 | 0x1C8B | Colosseum - Cage of the Gladiator Beasts | Spell Card |
| 118 | 0x02244431 | 0x1D70 | X-Saber Axel | Effect Monster |
| 119 | 0x02244431 | 0x1DA9 | Garoth, Lightsworn Warrior | Effect Monster |
| 120 | 0x02244431 | 0x1DDB | Light Spiral | Trap Card |
| 121 | 0x02244431 | 0x1E0D | Synchronized Realm | Spell Card |
| 122 | 0x02244431 | 0x1EE6 | Paralyzing Chain | Spell Card |
| 123 | 0x02244431 | 0x1EEB | Everliving Underworld Cannon | Spell Card |
| 124 | 0x02244431 | 0x1DF2 | Gigantic Cephalotus | Effect Monster |
| 125 | 0x02244431 | 0x1EE3 | Morphtronic Cord | Spell Card |
| 126 | 0x02244431 | 0x1F11 | Genex Solar | Effect Monster |
| 127 | 0x02244431 | 0x1F3E | Summon Reactor ｷSK | Effect Monster |
| 128 | 0x02244431 | 0x1F3F | Flying Fortress SKY FIRE | Effect Monster |
| 129 | 0x02244431 | 0x2004 | Sea Dragon Lord Gishilnodon | Synchro Effect Monster |
| 130 | 0x02244431 | 0x204B | Shiba-Warrior Taro | Tuner Monster |
| 131 | 0x02244431 | 0x2089 | Ancient Crimson Ape | Effect Monster |
| 132 | 0x02244431 | 0x20FE | Fortune Lady Dark | Effect Monster |
| 133 | 0x02244431 | 0x21C0 | Black Potan | Effect Monster |
| 134 | 0x02244431 | 0x225D | Biofalcon | Effect Monster |
| 135 | 0x02244431 | 0x232A | Wattcannon | Trap Card |
| 136 | 0x02244431 | 0x2333 | Light of Destruction | Trap Card |
| 137 | 0x02244431 | 0x2349 | ? |  |
| 138 | 0x02244431 | 0x238C | Karakuri Bushi mdl 6318 "Muzanichiha" | Effect Monster |
| 139 | 0x02244431 | 0x23C1 | Vanity's Emptiness | Trap Card |
| 140 | 0x02244431 | 0x2475 | Karakuri Steel Shogun mdl 00X "Bureido" | Synchro Effect Monster |
| 141 | 0x022464A1 | 0x1666 | Morale Boost | Spell Card |
| 142 | 0x0224660D | 0x16D0 | Stumbling | Spell Card |
| 143 | 0x0224660D | 0x1CB9 | Dark Cure | Trap Card |
| 144 | 0x0224660D | 0x1D32 | All-Out Attacks | Trap Card |
| 145 | 0x0224660D | 0x1EF7 | Morphtronic Monitron | Trap Card |
| 146 | 0x0224660D | 0x1EE0 | Black Garden | Spell Card |
| 147 | 0x0224660D | 0x201A | Overdoom Line | Trap Card |
| 148 | 0x0224660D | 0x2103 | Ground Spider | Effect Monster |
| 149 | 0x0224660D | 0x2179 | Naturia Strawberry | Effect Monster |
| 150 | 0x0224660D | 0x2191 | Koa'ki Meiru Beetle | Effect Monster |
| 151 | 0x0224660D | 0x2320 | Summoning Curse | Spell Card |
| 152 | 0x022443B1 | 0x18B2 | Criosphinx | Effect Monster |
| 153 | 0x02246D91 | 0x1744 | Soul-Absorbing Bone Tower | Effect Monster |
| 154 | 0x02246D91 | 0x1A50 | ? |  |
| 155 | 0x02246D91 | 0x1C7B | Witch Doctor of Sparta | Effect Monster |
| 156 | 0x02246D91 | 0x1D93 | Athena | Effect Monster |
| 157 | 0x02246D91 | 0x1E7A | Super-Ancient Dinobeast | Effect Monster |
| 158 | 0x02246D91 | 0x2207 | Genex Ally Crusher | Effect Monster |
| 159 | 0x02246045 | 0x1A0B | Guard Penalty | Spell Card |
| 160 | 0x02246F8D | 0x1810 | Blockman | Effect Monster |
| 161 | 0x02246C6D | 0x17C9 | Theinen the Great Sphinx | Effect Monster |
| 162 | 0x02247049 | 0x183F | Harpies' Hunting Ground | Spell Card |
| 163 | 0x02247A65 | 0x1B67 | Cloak and Dagger | Trap Card |
| 164 | 0x02247131 | 0x1A8A | ? |  |
| 165 | 0x02247B25 | 0x20FF | Fortune Lady Earth | Effect Monster |
| 166 | 0x02247205 | 0x1632 | Remove Brainwashing | Trap Card |
| 167 | 0x022480F9 | - | **(generic rule)** | |
| 168 | 0x02247ECD | - | **(generic rule)** | |
| 169 | 0x02244431 | 0x1762 | Backfire | Trap Card |
| 170 | 0x0224660D | 0x1387 | Slifer the Sky Dragon | Effect Monster |
| 171 | 0x0224660D | 0x1398 | King Tiger Wanghu | Effect Monster |
| 172 | 0x02244431 | 0x186B | Gearfried the Swordmaster | Effect Monster |
| 173 | 0x02244431 | 0x23EA | Seven Swords Warrior | Synchro Effect Monster |
| 174 | 0x02244431 | 0x1862 | Maji-Gire Panda | Effect Monster |
| 175 | 0x02244431 | 0x1875 | ? |  |
| 176 | 0x02244431 | 0x1C7B | Witch Doctor of Sparta | Effect Monster |
| 177 | 0x022443B1 | 0x118A | Ameba | Effect Monster |
| 178 | 0x022443B1 | 0x11C9 | ? |  |
| 179 | 0x022443B1 | 0x1E2D | Kunoichi | Effect Monster |
| 180 | 0x022443B1 | 0x1F69 | Vengeful Servant | Spell Card |
