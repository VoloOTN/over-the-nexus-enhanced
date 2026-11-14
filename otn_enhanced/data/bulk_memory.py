import ndspy.rom
import ndspy.lz10

from otn_enhanced.rom.duel_reward_codec import (
    parse_duel_rewards,
    patch_duel_reward,
    parse_script_rewards,
    patch_script_reward,
    OVERLAY_ID as REWARD_OVERLAY_ID,
    SCRIPT_BLACK01_IDX,
    SCRIPT_DUEL01_IDX,
    SCRIPT_DUEL02_IDX,
)
from otn_enhanced.rom.pac import parse_pac, build_modified_pac
from otn_enhanced.rom.ydc_codec import card_name_to_konami_id

# elbow: this lived in the 6k-line Dash GUI (app/nds_dash.py), which made plotly and dash build dependencies.
SCRIPT_IDX_MAP = {
    SCRIPT_DUEL01_IDX: "duel01",
    SCRIPT_DUEL02_IDX: "duel02",
    SCRIPT_BLACK01_IDX: "black01",
}


def _cid(name: str) -> int:
    cid = card_name_to_konami_id(name)
    if cid is None:
        raise KeyError(name)
    return cid

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_test.nds"


def _iter_paths(folder, prefix=""):
    """Yield every file path inside an ndspy filename folder tree (used to find bin2.pac)."""
    for f in getattr(folder, "files", []) or []:                # files directly under this folder
        yield f"{prefix}{f}"                                    # emit the file's full path
    folders = getattr(folder, "folders", []) or []              # sub-folders (dict OR list across ndspy versions)
    items = folders.items() if isinstance(folders, dict) else folders  # normalise to (name, folder) pairs
    for item in items:                                          # walk each sub-folder
        if isinstance(item, tuple) and len(item) >= 2:          # guard against unexpected shapes
            yield from _iter_paths(item[1], prefix=f"{prefix}{item[0]}/")  # recurse with extended path prefix



def apply_change(rec, ov7_data, archive, script_overrides, new_cards=None):
    """Apply a single reward patch.

    For script records, records the recompressed replacement in *script_overrides*
    keyed by inner-file index. For overlay records, returns updated ov7_data.
    """
    if rec.get("source") == "script":
        script_idx = rec["script_idx"]
        # A script file holds MANY records. If an earlier RECORDS entry already touched this
        # same script_idx, decompress ITS override -- not the pristine archive -- or that
        # earlier edit is silently discarded when this one overwrites script_overrides[script_idx].
        if script_idx in script_overrides:
            dec = bytes(ndspy.lz10.decompress(script_overrides[script_idx]))
        else:
            pac_file = archive.files[script_idx]
            raw = archive.data[pac_file.address:pac_file.address + pac_file.size]
            dec = bytes(ndspy.lz10.decompress(raw))
        patched_script = patch_script_reward(dec, rec["offset"], new_cards)
        script_overrides[script_idx] = bytes(ndspy.lz10.compress(patched_script))
        return ov7_data
    else:
        return patch_duel_reward(ov7_data, rec["offset"], new_cards)


RECORDS = {
    'West': {
        'original_cards': [_cid(x) for x in [
            'Dandylion',
            'Majestic Mech - Ohka',
            'Cyber Valley',
            'Swing of Memories',
            'Tornado',
            'Crystal Seer',
        ]],
        'cards': [_cid(x) for x in [
            'Cyber Valley',
            'Tuningware',
            'Darksea Rescue',
            'Machine Duplication',
            'Turbo Rocket',
            'Turbo Cannon',
        ]],
    },

    # --- Auto-filled from every OTHER script/overlay reward record in the stock ROM
    # (generated). 'cards' starts identical to 'original_cards' -- a no-op
    # scaffold -- so nothing changes until you edit a specific record's 'cards' list.
    # Keys are 'script_<duel_id>' (RPG_SCRIPT_J.pac, duel_ids 1-141) or
    # 'overlay_<record_id>' (overlay 7, record_ids 142-251); the record already claimed
    # by 'West' above is excluded here so the two entries don't fight over one record.
    'script_001': {
        'original_cards': [8038, 7430, 7572, 7912, 4742, 8265],  # Arcanite Magician / The Immortal Bushi / Hecatrice / Psychokinesis / Blast Sphere / Ojama Blue
        'cards':          [8038, 7430, 7572, 7912, 4742, 8265],  # unchanged -- edit to replace
    },
    'script_002': {
        'original_cards': [6397, 7423, 7945, 7740, 5607, 7728],  # Cyber End Dragon / Armageddon Knight / Naturia Rock / Domino Effect / Poison of the Old Man / Kinka-byo
        'cards':          [6397, 7423, 7945, 7740, 5607, 7728],  # unchanged -- edit to replace
    },
    'script_003': {
        'original_cards': [6397, 7423, 7945, 7740, 5607, 7728],  # Cyber End Dragon / Armageddon Knight / Naturia Rock / Domino Effect / Poison of the Old Man / Kinka-byo
        'cards':          [6397, 7423, 7945, 7740, 5607, 7728],  # unchanged -- edit to replace
    },
    'script_004': {
        'original_cards': [4861, 7398, 7404, 6823, 7623, 8413],  # Solemn Judgment / Deep Diver / Fog King / Jurassic World / Cup of Ace / Worm Zero
        'cards':          [4861, 7398, 7404, 6823, 7623, 8413],  # unchanged -- edit to replace
    },
    'script_005': {
        'original_cards': [8692, 5129, 6308, 8696, 8694, 6303],  # Machina Fortress / Limiter Removal / Machina Force / Machina Armored Unit / Machina Peacekeeper / Machina Defender
        'cards':          [8692, 5129, 6308, 8696, 8694, 6303],  # unchanged -- edit to replace
    },
    'script_006': {
        'original_cards': [4910, 8089, 4373, 8480, 8453, 8635],  # Giant Trunade / Tragoedia / Jirai Gumo / Spider Web / Spyder Spider / Informer Spider
        'cards':          [4910, 8089, 4373, 8480, 8453, 8635],  # unchanged -- edit to replace
    },
    'script_007': {
        'original_cards': [6784, 7659, 4821, 5132, 5210, 5318],  # Elemental Hero Stratos / Kuraz the Light Monarch / Card Destruction / Dimensionhole / Jar of Greed / Marauding Captain
        'cards':          [6784, 7659, 4821, 5132, 5210, 5318],  # unchanged -- edit to replace
    },
    'script_008': {
        'original_cards': [8350, 6078, 8977, 5327, 6212, 4927],  # Rekindling / Return from the Different Dimension / Double Cyclone / The A. Forces / Back to Square One / Flying Kamakiri #1
        'cards':          [8350, 6078, 8977, 5327, 6212, 4927],  # unchanged -- edit to replace
    },
    'script_009': {
        'original_cards': [8960, 7850, 8675, 7519, 7469, 4547],  # Naturia Bamboo Shoot / The White Stone of Legend / Fiendish Chain / D.D.R. - Different Dimension Reincarnation / Dark Spirit Art - Greed / Hane-Hane
        'cards':          [8960, 7850, 8675, 7519, 7469, 4547],  # unchanged -- edit to replace
    },
    'script_010': {
        'original_cards': [5162, 8435, 8490, 7220, 5548, 4969],  # Creature Swap / Supervise / Gemini Spark / Summoner's Art / Rite of Spirit / Morphing Jar #2
        'cards':          [5162, 8435, 8490, 7220, 5548, 4969],  # unchanged -- edit to replace
    },
    'script_011': {
        'original_cards': [7570, 8187, 8188, 5389, 7202, 6963],  # Allure of Darkness / Deep Sea Diva / Mermaid Archer / Smoke Grenade of the Thief / Doom Shaman / The Six Samurai - Yariza
        'cards':          [7570, 8187, 8188, 5389, 7202, 6963],  # unchanged -- edit to replace
    },
    'script_012': {
        'original_cards': [4866, 8961, 8977, 6350, 7636, 4036],  # Royal Decree / Amazoness Sage / Double Cyclone / Doriado's Blessing / Limit Reverse / Zombie Warrior
        'cards':          [4866, 8961, 8977, 6350, 7636, 4036],  # unchanged -- edit to replace
    },
    'script_013': {
        'original_cards': [5099, 8095, 8088, 4899, 7018, 6970],  # Soul Exchange / Fabled Kushano / Violet Witch / Chorus of Sanctuary / Metal Shooter / Shien's Footsoldier
        'cards':          [5099, 8095, 8088, 4899, 7018, 6970],  # unchanged -- edit to replace
    },
    'script_014': {
        'original_cards': [6821, 8022, 8023, 4815, 7426, 7107],  # Light and Darkness Dragon / Assault Beast / Night Wing Sorceress / Graceful Dice / Shadowpriestess of Ohm / Warrior of Atlantis
        'cards':          [6821, 8022, 8023, 4815, 7426, 7107],  # unchanged -- edit to replace
    },
    'script_015': {
        'original_cards': [8693, 7246, 7248, 4857, 4917, 4522],  # Machina Gearframe / Herald of Creation / Trade-In / Soul Release / UFO Turtle / Muka Muka
        'cards':          [8693, 7246, 7248, 4857, 4917, 4522],  # unchanged -- edit to replace
    },
    'script_016': {
        'original_cards': [6941, 8159, 8197, 5345, 7489, 7175],  # Burial from a Different Dimension / Phoenixian Cluster Amaryllis / One for One / Stamping Destruction / Security Orb / Elemental Hero Marine Neos
        'cards':          [6941, 8159, 8197, 5345, 7489, 7175],  # unchanged -- edit to replace
    },
    'script_017': {
        'original_cards': [8960, 8134, 8135, 5166, 5493, 6418],  # Naturia Bamboo Shoot / Defender, the Magical Knight / Magical Citadel of Endymion / Thousand Knives / Malevolent Catastrophe / Goblin Elite Attack Force
        'cards':          [8960, 8134, 8135, 5166, 5493, 6418],  # unchanged -- edit to replace
    },
    'script_018': {
        'original_cards': [8430, 7400, 6901, 7671, 5658, 7279],  # Cyber Eltanin / Dimensional Prison / Instant Fusion / Miracle Fertilizer / Royal Magical Library / Cloudian - Cirrostratus
        'cards':          [8430, 7400, 6901, 7671, 5658, 7279],  # unchanged -- edit to replace
    },
    'script_019': {
        'original_cards': [7397, 8173, 8174, 4659, 6977, 7146],  # Thunder King Rai-Oh / Koa'ki Meiru Valafar / Koa'ki Meiru Powerhand / Warrior Elimination / Electric Virus / Diabolos, King of the Abyss
        'cards':          [7397, 8173, 8174, 4659, 6977, 7146],  # unchanged -- edit to replace
    },
    'script_020': {
        'original_cards': [7864, 6433, 6405, 6399, 6443, 5593],  # Avenging Knight Parshath / Dragon's Mirror / The Wicked Dreadroot / Skyscraper / A Rival Appears! / D.D. Crazy Beast
        'cards':          [7864, 6433, 6405, 6399, 6443, 5593],  # unchanged -- edit to replace
    },
    'script_021': {
        'original_cards': [6654, 4988, 7193, 7219, 9148, 6478],  # Dandylion / Dust Tornado / Hunter Dragon / Double Summon / Karakuri Trick House / Elemental Hero Wildheart
        'cards':          [6654, 4988, 7193, 7219, 9148, 6478],  # unchanged -- edit to replace
    },
    'script_022': {
        'original_cards': [7397, 7285, 7349, 6280, 9006, 6508],  # Thunder King Rai-Oh / Gladiator Beast Bestiari / Dark Bribe / Good Goblin Housekeeping / Horn of the Phantom Beast / Familiar-Possessed - Eria
        'cards':          [7397, 7285, 7349, 6280, 9006, 6508],  # unchanged -- edit to replace
    },
    'script_023': {
        'original_cards': [7937, 7763, 7683, 5298, 9124, 6201],  # Kasha / Gladiator Beast War Chariot / Geartown / Nightmare Wheel / Golden Gearbox / Dekoichi the Battlechanted Locomotive
        'cards':          [7937, 7763, 7683, 5298, 9124, 6201],  # unchanged -- edit to replace
    },
    'script_024': {
        'original_cards': [4842, 7916, 7567, 7470, 9150, 8645],  # Monster Reborn / Secret Village of the Spellcasters / Prime Material Dragon / Dark Illusion / Scrap Crash / Gundari
        'cards':          [4842, 7916, 7567, 7470, 9150, 8645],  # unchanged -- edit to replace
    },
    'script_025': {
        'original_cards': [7592, 6078, 6217, 6148, 6884, 6195],  # Lyla, Lightsworn Sorceress / Return from the Different Dimension / Divine Wrath / Cemetary Bomb / Barrier Statue of the Inferno / Pitch-Black Warwolf
        'cards':          [7592, 6078, 6217, 6148, 6884, 6195],  # unchanged -- edit to replace
    },
    'script_026': {
        'original_cards': [7400, 6280, 6932, 8833, 8859, 8643],  # Dimensional Prison / Good Goblin Housekeeping / Ancient Gear Gadjiltron Dragon / Koa'ki Meiru Initialize! / Wild Tornado / Codarus
        'cards':          [7400, 6280, 6932, 8833, 8859, 8643],  # unchanged -- edit to replace
    },
    'script_027': {
        'original_cards': [4842, 8627, 8628, 9050, 6447, 8316],  # Monster Reborn / Reptilianne Gardna / Reptilianne Naga / Dragon Mastery / Conscription / Armed Sea Hunter
        'cards':          [4842, 8627, 8628, 9050, 6447, 8316],  # unchanged -- edit to replace
    },
    'script_028': {
        'original_cards': [7567, 8675, 7899, 7885, 7886, 7888],  # Prime Material Dragon / Fiendish Chain / Iron Chain Dragon / Iron Chain Repairman / Iron Chain Snake / Iron Chain Coil
        'cards':          [7567, 8675, 7899, 7885, 7886, 7888],  # unchanged -- edit to replace
    },
    'script_029': {
        'original_cards': [8260, 6433, 5323, 6434, 8500, 6387],  # Naturia Barkion / Dragon's Mirror / Exiled Force / System Down / Enlightenment / Drillroid
        'cards':          [8260, 6433, 5323, 6434, 8500, 6387],  # unchanged -- edit to replace
    },
    'script_030': {
        'original_cards': [6821, 4938, 6054, 4804, 4862, 6626],  # Light and Darkness Dragon / Messenger of Peace / Level Limit - Area B / Negate Attack / Magic Jammer / Malfunction
        'cards':          [6821, 4938, 6054, 4804, 4862, 6626],  # unchanged -- edit to replace
    },
    'script_032': {
        'original_cards': [4818, 8326, 6901, 4871, 8304, 7116],  # Scapegoat / XX-Saber Faultroll / Instant Fusion / Restructer Revolution / Darksea Rescue / Mei-Kou, Master of Barriers
        'cards':          [4818, 8326, 6901, 4871, 8304, 7116],  # unchanged -- edit to replace
    },
    'script_033': {
        'original_cards': [5328, 5133, 7351, 4335, 5511, 7670],  # Reinforcement of the Army / Magic Drain / Phantom of Chaos / Dragon Capture Jar / Gravekeeper's Guard / Cursed Fig
        'cards':          [5328, 5133, 7351, 4335, 5511, 7670],  # unchanged -- edit to replace
    },
    'script_034': {
        'original_cards': [7549, 4866, 8001, 4934, 7429, 4924],  # Mist Wurm / Royal Decree / Black Salvo / Molten Destruction / Vengeful Shinobi / Shining Angel
        'cards':          [7549, 4866, 8001, 4934, 7429, 4924],  # unchanged -- edit to replace
    },
    'script_035': {
        'original_cards': [4354, 6692, 6693, 5670, 5669, 7689],  # Swords of Revealing Light / Herald of Purple Light / Herald of Green Light / Gather Your Mind / Big Bang Shot / Magna Drago
        'cards':          [4354, 6692, 6693, 5670, 5669, 7689],  # unchanged -- edit to replace
    },
    'script_036': {
        'original_cards': [6939, 6733, 6704, 7519, 5560, 8756],  # Card Trooper / Elemental Hero Ocean / Swift Birdman Joe / D.D.R. - Different Dimension Reincarnation / Interdimensional Matter Transporter / Cactus Bouncer
        'cards':          [6939, 6733, 6704, 7519, 5560, 8756],  # unchanged -- edit to replace
    },
    'script_037': {
        'original_cards': [6996, 9389, 8474, 5900, 4916, 4929],  # Advanced Ritual Art / Evigishki Tetrogre / Divine Grace - Northwemko / Manju of the Ten Thousand Hands / Senju of the Thousand Hands / Sonic Bird
        'cards':          [6996, 9389, 8474, 5900, 4916, 4929],  # unchanged -- edit to replace
    },
    'script_038': {
        'original_cards': [8815, 8193, 8476, 8821, 8222, 9093],  # Black-Winged Dragon / Blackwing Armed Wing / Blackwing - Silverwind the Ascendant / Cards for Black Feathers / Fake Feather / Blackwing - Aurora the Northern Lights
        'cards':          [8815, 8193, 8476, 8821, 8222, 9093],  # unchanged -- edit to replace
    },
    'script_039': {
        'original_cards': [7898, 7893, 9420, 7903, 7568, 8623],  # Black Rose Dragon / Tytannial, Princess of Camellias / Fallen Angel of Roses / Mark of the Rose / Lonefire Blossom / Witch of the Black Rose
        'cards':          [7898, 7893, 9420, 7903, 7568, 8623],  # unchanged -- edit to replace
    },
    'script_040': {
        'original_cards': [9119, 7735, 8192, 7871, 9086, 9297],  # Red Nova Dragon / Red Dragon Archfiend / Exploder Dragonwing / Mad Archfiend / Lancer Archfiend / Barrier Resonator
        'cards':          [9119, 7735, 8192, 7871, 9086, 9297],  # unchanged -- edit to replace
    },
    'script_041': {
        'original_cards': [9117, 8475, 7734, 7700, 8937, 9237],  # Shooting Star Dragon / Majestic Star Dragon / Stardust Dragon / Nitro Synchron / Stronghold Guardian / Big One Warrior
        'cards':          [9117, 8475, 7734, 7700, 8937, 9237],  # unchanged -- edit to replace
    },
    'script_042': {
        'original_cards': [6000, 5400, 9095, 7456, 6218, 8325],  # Marshmallon / Bottomless Trap Hole / Glow-Up Bulb / Chain Summoning / Xing Zhen Hu / Minefieldriller
        'cards':          [6000, 5400, 9095, 7456, 6218, 8325],  # unchanged -- edit to replace
    },
    'script_043': {
        'original_cards': [7549, 9046, 7349, 6207, 6621, 6599],  # Mist Wurm / Dragunity Arma Leyvaten / Dark Bribe / Harpies' Hunting Ground / Generation Shift / Chainsaw Insect
        'cards':          [7549, 9046, 7349, 6207, 6621, 6599],  # unchanged -- edit to replace
    },
    'script_044': {
        'original_cards': [8038, 7430, 7572, 7912, 4742, 8265],  # Arcanite Magician / The Immortal Bushi / Hecatrice / Psychokinesis / Blast Sphere / Ojama Blue
        'cards':          [8038, 7430, 7572, 7912, 4742, 8265],  # unchanged -- edit to replace
    },
    'script_045': {
        'original_cards': [7371, 7106, 7010, 8207, 8026, 7436],  # Dark End Dragon / Gravekeeper's Commandant / The Transmigration Prophecy / Iron Core of Koa'ki Meiru / Inmato / The Calculator
        'cards':          [7371, 7106, 7010, 8207, 8026, 7436],  # unchanged -- edit to replace
    },
    'script_046': {
        'original_cards': [7617, 5396, 5213, 7225, 7229, 7206],  # Gladiator Beast Gyzarus / Blast with Chain / Mage Power / Broken Bamboo Sword / Destructive Draw / Gravitic Orb
        'cards':          [7617, 5396, 5213, 7225, 7229, 7206],  # unchanged -- edit to replace
    },
    'script_047': {
        'original_cards': [7261, 8378, 5410, 7001, 6906, 6957],  # Evil Hero Dark Gaia / Swallow's Nest / Vampire Lord / Card Trader / Mystical Wind Typhoon / Phantom Beast Rock-Lizard
        'cards':          [7261, 8378, 5410, 7001, 6906, 6957],  # unchanged -- edit to replace
    },
    'script_048': {
        'original_cards': [6941, 7663, 5133, 4932, 4953, 8223],  # Burial from a Different Dimension / Oyster Meister / Magic Drain / Gaia Power / Backup Soldier / Trap Stun
        'cards':          [6941, 7663, 5133, 4932, 4953, 8223],  # unchanged -- edit to replace
    },
    'script_049': {
        'original_cards': [7674, 6278, 7823, 6436, 4985, 5035],  # Herald of Perfection / Threatening Roar / X-Saber Palomuro / Pot of Generosity / Graverobber / Jowls of Dark Demise
        'cards':          [7674, 6278, 7823, 6436, 4985, 5035],  # unchanged -- edit to replace
    },
    'script_050': {
        'original_cards': [7046, 7864, 8333, 5023, 6692, 6694],  # Neo-Parshath, the Sky Paladin / Avenging Knight Parshath / Ancient Sacred Wyvern / Airknight Parshath / Herald of Purple Light / Layard the Liberator
        'cards':          [7046, 7864, 8333, 5023, 6692, 6694],  # unchanged -- edit to replace
    },
    'script_051': {
        'original_cards': [8816, 9141, 7850, 6678, 9090, 9297],  # Chaos King Archfiend / Red Screen / The White Stone of Legend / D - Time / Creation Resonator / Barrier Resonator
        'cards':          [8816, 9141, 7850, 6678, 9090, 9297],  # unchanged -- edit to replace
    },
    'script_052': {
        'original_cards': [6782, 8341, 9141, 8301, 8302, 8446],  # Future Fusion / Future Visions / Red Screen / Fortune Lady Light / Fortune Lady Fire / Fortune Lady Dark
        'cards':          [6782, 8341, 9141, 8301, 8302, 8446],  # unchanged -- edit to replace
    },
    'script_053': {
        'original_cards': [8137, 5129, 4663, 7906, 7879, 8205],  # Power Tool Dragon / Limiter Removal / Megamorph / Morphtronic Accelerator / Morphtronic Radion / Double Tool C&D
        'cards':          [8137, 5129, 4663, 7906, 7879, 8205],  # unchanged -- edit to replace
    },
    'script_054': {
        'original_cards': [4342, 8090, 8442, 8292, 8293, 4694],  # Dark Hole / Ancient Fairy Dragon / Regulus / Kuribon / Sunny Pixie / Bad Reaction to Simochi
        'cards':          [4342, 8090, 8442, 8292, 8293, 4694],  # unchanged -- edit to replace
    },
    'script_055': {
        'original_cards': [6782, 6504, 6505, 4836, 5405, 7082],  # Future Fusion / Sillva, Warlord of Dark World / Goldd, Wu-Lord of Dark World / Trap Hole / Fiend Comedian / Volcanic Shell
        'cards':          [6782, 6504, 6505, 4836, 5405, 7082],  # unchanged -- edit to replace
    },
    'script_056': {
        'original_cards': [4887, 8085, 5655, 5649, 7799, 8134],  # Mirror Force / Tempest Magician / Breaker the Magical Warrior / Skilled Dark Magician / Magical Exemplar / Defender, the Magical Knight
        'cards':          [4887, 8085, 5655, 5649, 7799, 8134],  # unchanged -- edit to replace
    },
    'script_057': {
        'original_cards': [6000, 8333, 7737, 9006, 8442, 7537],  # Marshmallon / Ancient Sacred Wyvern / Magical Android / Horn of the Phantom Beast / Regulus / X-Saber Airbellum
        'cards':          [6000, 8333, 7737, 9006, 8442, 7537],  # unchanged -- edit to replace
    },
    'script_058': {
        'original_cards': [4989, 5740, 6960, 7013, 7365, 5644],  # Call of the Haunted / Skill Drain / Gene-Warped Warwolf / Birthright / Gladiator Beast Andal / Luster Dragon
        'cards':          [4989, 5740, 6960, 7013, 7365, 5644],  # unchanged -- edit to replace
    },
    'script_059': {
        'original_cards': [8287, 9066, 9175, 6215, 6198, 4970],  # Darklord Asmodeus / Mask Change / Steelswarm Moth / Lighten the Load / Fox Fire / Bubonic Vermin
        'cards':          [8287, 9066, 9175, 6215, 6198, 4970],  # unchanged -- edit to replace
    },
    'script_060': {
        'original_cards': [7342, 8357, 8358, 8340, 8299, 8300],  # Armityle the Chaos Phantom / Imperial Custom / Discord / Spirit Burner / Jester Lord / Jester Confit
        'cards':          [7342, 8357, 8358, 8340, 8299, 8300],  # unchanged -- edit to replace
    },
    'script_061': {
        'original_cards': [8386, 8328, 4758, 5001, 7264, 8555],  # Darklord Desire / Flamvell Firedog / Jinzo / Windstorm of Etaqua / Cloudian - Eye of the Typhoon / The Fabled Catsith
        'cards':          [8386, 8328, 4758, 5001, 7264, 8555],  # unchanged -- edit to replace
    },
    'script_062': {
        'original_cards': [6166, 6164, 6162, 6133, 5544, 4886],  # Silent Swordsman LV7 / Silent Swordsman LV5 / Silent Swordsman LV3 / Level Up! / Raigeki Break / Waboku
        'cards':          [6166, 6164, 6162, 6133, 5544, 4886],  # unchanged -- edit to replace
    },
    'script_063': {
        'original_cards': [8974, 4866, 7445, 8825, 4664, 4501],  # Scrap Dragon / Royal Decree / Super Polymerization / Intercept Wave / Metalmorph / Musician King
        'cards':          [8974, 4866, 7445, 8825, 4664, 4501],  # unchanged -- edit to replace
    },
    'script_064': {
        'original_cards': [6613, 8556, 8234, 8348, 5442, 4839],  # Demise, King of Armageddon / The Fabled Cerburrel / Fabled Krus / Saber Slash / Needle Ceiling / Two-Pronged Attack
        'cards':          [6613, 8556, 8234, 8348, 5442, 4839],  # unchanged -- edit to replace
    },
    'script_065': {
        'original_cards': [5127, 6274, 7600, 6214, 9140, 8191],  # Cold Wave / The Big March of Animals / Dark Valkyria / Ballista of Rampart Smashing / D2 Shield / G.B. Hunter
        'cards':          [5127, 6274, 7600, 6214, 9140, 8191],  # unchanged -- edit to replace
    },
    'script_066': {
        'original_cards': [4817, 7573, 7581, 6674, 9186, 6457],  # Mind Control / Valhalla, Hall of the Fallen / Arcana Force 0 - The Fool / O - Oversoul / Blessings for Gusto / Warrior Lady of the Wasteland
        'cards':          [4817, 7573, 7581, 6674, 9186, 6457],  # unchanged -- edit to replace
    },
    'script_067': {
        'original_cards': [6000, 5400, 9095, 7456, 6218, 8325],  # Marshmallon / Bottomless Trap Hole / Glow-Up Bulb / Chain Summoning / Xing Zhen Hu / Minefieldriller
        'cards':          [6000, 5400, 9095, 7456, 6218, 8325],  # unchanged -- edit to replace
    },
    'script_068': {
        'original_cards': [8973, 8971, 7970, 8945, 8942, 8943],  # Lightning Tricorn / Thunder Unicorn / Dewloren, Tiger King of the Ice Barrier / Mine Mole / D.D. Unicorn Knight / Unibird
        'cards':          [8973, 8971, 7970, 8945, 8942, 8943],  # unchanged -- edit to replace
    },
    'script_070': {
        'original_cards': [4861, 7398, 7404, 6823, 7623, 8413],  # Solemn Judgment / Deep Diver / Fog King / Jurassic World / Cup of Ace / Worm Zero
        'cards':          [4861, 7398, 7404, 6823, 7623, 8413],  # unchanged -- edit to replace
    },
    'script_071': {
        'original_cards': [7738, 7445, 5213, 4352, 5120, 7425],  # Thought Ruler Archfiend / Super Polymerization / Mage Power / Ookazi / Nightmare's Steelcage / Obsidian Dragon
        'cards':          [7738, 7445, 5213, 4352, 5120, 7425],  # unchanged -- edit to replace
    },
    'script_072': {
        'original_cards': [7738, 7445, 5213, 4352, 5120, 7425],  # Thought Ruler Archfiend / Super Polymerization / Mage Power / Ookazi / Nightmare's Steelcage / Obsidian Dragon
        'cards':          [7738, 7445, 5213, 4352, 5120, 7425],  # unchanged -- edit to replace
    },
    'script_073': {
        'original_cards': [6603, 7358, 7399, 4933, 7236, 9326],  # Treeborn Frog / Shutendoji / Burden of the Mighty / Umiiruka / Counter Counter / Symphonic Warrior Piaano
        'cards':          [6603, 7358, 7399, 4933, 7236, 9326],  # unchanged -- edit to replace
    },
    'script_074': {
        'original_cards': [6432, 5935, 7314, 7914, 7520, 7714],  # Miracle Fusion / Zoma the Spirit / Cunning of the Six Samurai / The World Tree / By Order of the Emperor / Mind Master
        'cards':          [6432, 5935, 7314, 7914, 7520, 7714],  # unchanged -- edit to replace
    },
    'script_075': {
        'original_cards': [9334, 9121, 8954, 8978, 8950, 9102],  # Atomic Scrap Dragon / Scrap Twin Dragon / Scrap Golem / Scrapyard / Scrap Chimera / Scrap Searcher
        'cards':          [9334, 9121, 8954, 8978, 8950, 9102],  # unchanged -- edit to replace
    },
    'script_076': {
        'original_cards': [9335, 8975, 8801, 9322, 9323, 9104],  # Watthydra / Wattchimera / Wattgiraffe / Wattberyx / Wattmole / Watthopper
        'cards':          [9335, 8975, 8801, 9322, 9323, 9104],  # unchanged -- edit to replace
    },
    'script_077': {
        'original_cards': [7570, 8753, 6244, 8496, 7476, 4195],  # Allure of Darkness / XX-Saber Emmersblade / Behemoth the King of All Animals / Insect Neglect / Offering to the Snake Deity / Fusionist
        'cards':          [7570, 8753, 6244, 8496, 7476, 4195],  # unchanged -- edit to replace
    },
    'script_078': {
        'original_cards': [8283, 7981, 8089, 5631, 7383, 7111],  # Archlord Kristya / Gallis the Star Beast / Tragoedia / Diffusion Wave-Motion / Hero's Rule 2 / Harpie Lady
        'cards':          [8283, 7981, 8089, 5631, 7383, 7111],  # unchanged -- edit to replace
    },
    'script_079': {
        'original_cards': [7421, 7401, 7537, 7750, 4662, 4691],  # Dark Armed Dragon / Vortex Trooper / X-Saber Airbellum / Unstable Evolution / Eternal Rest / Acid Trap Hole
        'cards':          [7421, 7401, 7537, 7750, 4662, 4691],  # unchanged -- edit to replace
    },
    'script_080': {
        'original_cards': [5127, 6274, 7600, 6214, 9140, 8191],  # Cold Wave / The Big March of Animals / Dark Valkyria / Ballista of Rampart Smashing / D2 Shield / G.B. Hunter
        'cards':          [5127, 6274, 7600, 6214, 9140, 8191],  # unchanged -- edit to replace
    },
    'script_081': {
        'original_cards': [7574, 8970, 6912, 9137, 6286, 6201],  # Honest / Ultimate Axon Kicker / Justi-Break / Tokkosho of Ghost Destroying / Forced Ceasefire / Dekoichi the Battlechanted Locomotive
        'cards':          [7574, 8970, 6912, 9137, 6286, 6201],  # unchanged -- edit to replace
    },
    'script_082': {
        'original_cards': [8817, 8823, 8272, 8846, 8790, 8788],  # Infernity Doom Dragon / Infernity Launcher / Infernity Archfiend / Infernity Inferno / Infernity Beetle / Infernity Mirage
        'cards':          [8817, 8823, 8272, 8846, 8790, 8788],  # unchanged -- edit to replace
    },
    'script_083': {
        'original_cards': [8818, 6709, 4821, 8989, 8255, 8160],  # Splendid Rose / Icarus Attack / Card Destruction / Pestilence / Worm Tentacles / Hedge Guard
        'cards':          [8818, 6709, 4821, 8989, 8255, 8160],  # unchanged -- edit to replace
    },
    'script_084': {
        'original_cards': [5533, 5935, 8001, 6997, 7636, 6258],  # Necrovalley / Zoma the Spirit / Black Salvo / Synthesis Spell / Limit Reverse / The Earth - Hex-Sealed Fusion
        'cards':          [5533, 5935, 8001, 6997, 7636, 6258],  # unchanged -- edit to replace
    },
    'script_085': {
        'original_cards': [8262, 7219, 7193, 7911, 5506, 4108],  # Gungnir, Dragon of the Ice Barrier / Double Summon / Hunter Dragon / Teleport / Master Kyonshee / Mask of Darkness
        'cards':          [8262, 7219, 7193, 7911, 5506, 4108],  # unchanged -- edit to replace
    },
    'script_086': {
        'original_cards': [8038, 5253, 6217, 5355, 6135, 8567],  # Arcanite Magician / Aqua Spirit / Divine Wrath / Shrink / The Graveyard in the Fourth Dimension / Naturia Butterfly
        'cards':          [8038, 5253, 6217, 5355, 6135, 8567],  # unchanged -- edit to replace
    },
    'script_087': {
        'original_cards': [8137, 8090, 8442, 7908, 7876, 7877],  # Power Tool Dragon / Ancient Fairy Dragon / Regulus / Morphtronic Engine / Morphtronic Datatron / Morphtronic Boomboxen
        'cards':          [8137, 8090, 8442, 7908, 7876, 7877],  # unchanged -- edit to replace
    },
    'script_088': {
        'original_cards': [6782, 7991, 9141, 8301, 8302, 7708],  # Future Fusion / Vice Dragon / Red Screen / Fortune Lady Light / Fortune Lady Fire / Dark Resonator
        'cards':          [6782, 7991, 9141, 8301, 8302, 7708],  # unchanged -- edit to replace
    },
    'script_089': {
        'original_cards': [8692, 8089, 8693, 8696, 8450, 8451],  # Machina Fortress / Tragoedia / Machina Gearframe / Machina Armored Unit / Dark Spider / Ground Spider
        'cards':          [8692, 8089, 8693, 8696, 8450, 8451],  # unchanged -- edit to replace
    },
    'script_090': {
        'original_cards': [7346, 5935, 7567, 6051, 5918, 6341],  # Beast King Barbaros / Zoma the Spirit / Prime Material Dragon / Spell Economics / Begone, Knave! / King of the Skull Servants
        'cards':          [7346, 5935, 7567, 6051, 5918, 6341],  # unchanged -- edit to replace
    },
    'script_091': {
        'original_cards': [8283, 7349, 9095, 8984, 9110, 6335],  # Archlord Kristya / Dark Bribe / Glow-Up Bulb / Amazoness Village / Dance Princess of the Ice Barrier / Aussa the Earth Charmer
        'cards':          [8283, 7349, 9095, 8984, 9110, 6335],  # unchanged -- edit to replace
    },
    'script_092': {
        'original_cards': [8693, 8731, 9049, 5743, 5616, 6239],  # Machina Gearframe / Dragunity Knight - Barcha / Dragon Ravine / Soul Taker / Thunder of Ruler / Granmarg the Rock Monarch
        'cards':          [8693, 8731, 9049, 5743, 5616, 6239],  # unchanged -- edit to replace
    },
    'script_093': {
        'original_cards': [5099, 6980, 6932, 5608, 6291, 5769],  # Soul Exchange / D.D. Crow / Ancient Gear Gadjiltron Dragon / Ante / Overpowering Eye / Iron Blacksmith Kotetsu
        'cards':          [5099, 6980, 6932, 5608, 6291, 5769],  # unchanged -- edit to replace
    },
    'script_094': {
        'original_cards': [4842, 7491, 6380, 6046, 5854, 6188],  # Monster Reborn / Elemental Hero Prisma / Green Baboon, Defender of the Forest / Special Hurricane / Tower of Babel / Harpie Lady 3
        'cards':          [4842, 7491, 6380, 6046, 5854, 6188],  # unchanged -- edit to replace
    },
    'script_095': {
        'original_cards': [9335, 8975, 9121, 9127, 9128, 8952],  # Watthydra / Wattchimera / Scrap Twin Dragon / Wattcastle / Wattjustment / Scrap Beast
        'cards':          [9335, 8975, 9121, 9127, 9128, 8952],  # unchanged -- edit to replace
    },
    'script_096': {
        'original_cards': [9117, 7735, 9118, 7687, 7708, 8786],  # Shooting Star Dragon / Red Dragon Archfiend / Formula Synchron / Junk Synchron / Dark Resonator / Flare Resonator
        'cards':          [9117, 7735, 9118, 7687, 7708, 8786],  # unchanged -- edit to replace
    },
    'script_098': {
        'original_cards': [7371, 8089, 8739, 8738, 8740, 7712],  # Dark End Dragon / Tragoedia / Stygian Sergeants / Stygian Security / Stygian Street Patrol / Montage Dragon
        'cards':          [7371, 8089, 8739, 8738, 8740, 7712],  # unchanged -- edit to replace
    },
    'script_099': {
        'original_cards': [4887, 8332, 7848, 8269, 8268, 8270],  # Mirror Force / Archfiend Zombie-Skull / Doomkaiser Dragon / Skull Flame / Supersonic Skull Flame / Burning Skull Head
        'cards':          [4887, 8332, 7848, 8269, 8268, 8270],  # unchanged -- edit to replace
    },
    'script_100': {
        'original_cards': [9218, 7423, 5655, 8825, 8304, 8305],  # Dark Flattop / Armageddon Knight / Breaker the Magical Warrior / Intercept Wave / Darksea Rescue / Darksea Float
        'cards':          [9218, 7423, 5655, 8825, 8304, 8305],  # unchanged -- edit to replace
    },
    'script_101': {
        'original_cards': [7864, 6980, 9288, 8356, 8899, 9212],  # Avenging Knight Parshath / D.D. Crow / The Agent of Mystery - Earth / Fairy Wind / Laval Miller / Gem-Knight Emerald
        'cards':          [7864, 6980, 9288, 8356, 8899, 9212],  # unchanged -- edit to replace
    },
    'script_102': {
        'original_cards': [7549, 4910, 7982, 9182, 8353, 9173],  # Mist Wurm / Giant Trunade / Red-Eyes Wyvern / Gishki Ceremonial Mirror / Skill Successor / Steelswarm Caller
        'cards':          [7549, 4910, 7982, 9182, 8353, 9173],  # unchanged -- edit to replace
    },
    'script_103': {
        'original_cards': [7898, 8159, 9420, 7903, 8795, 8623],  # Black Rose Dragon / Phoenixian Cluster Amaryllis / Fallen Angel of Roses / Mark of the Rose / Spore / Witch of the Black Rose
        'cards':          [7898, 8159, 9420, 7903, 8795, 8623],  # unchanged -- edit to replace
    },
    'script_106': {
        'original_cards': [9199, 9200, 9198, 9201, 5899, 5208],  # Chevalier de Fleur / Liberty at Last! / Fleur Synchron / Sacred Knight Joan / Guardian Angel Joan / St. Joan
        'cards':          [9199, 9200, 9198, 9201, 5899, 5208],  # unchanged -- edit to replace
    },
    'script_107': {
        'original_cards': [9219, 6252, 9316, 8251, 7430, 6967],  # Driven Daredevil / Armed Samurai - Ben Kei / Kagemusha of the Six Samurai / Samurai of the Ice Barrier / The Immortal Bushi / The Six Samurai - Kamon
        'cards':          [9219, 6252, 9316, 8251, 7430, 6967],  # unchanged -- edit to replace
    },
    'script_108': {
        'original_cards': [7552, 8970, 7600, 6137, 7210, 4126],  # Ally of Justice Catastor / Ultimate Axon Kicker / Dark Valkyria / Big Wave Small Wave / Frost and Flame Dragon / Dream Clown
        'cards':          [7552, 8970, 7600, 6137, 7210, 4126],  # unchanged -- edit to replace
    },
    'script_109': {
        'original_cards': [9333, 9319, 9099, 9123, 9096, 9100],  # Karakuri Steel Shogun mdl 00X "Bureido" / Karakuri Ninja mdl 919 "Kuick" / Karakuri Ninja mdl 339 "Sazank" / Karakuri Showdown Castle / Karakuri Soldier mdl 236 "Nisamu" / Karakuri Bushi mdl 6318 "Muzanichiha"
        'cards':          [9333, 9319, 9099, 9123, 9096, 9100],  # unchanged -- edit to replace
    },
    'script_110': {
        'original_cards': [6835, 6511, 5882, 4353, 7380, 7401],  # Super Vehicroid - Stealth Union / Pot of Avarice / Stealth Bird / Tremendous Fire / Evil Hero Malicious Fiend / Vortex Trooper
        'cards':          [6835, 6511, 5882, 4353, 7380, 7401],  # unchanged -- edit to replace
    },
    'script_111': {
        'original_cards': [8192, 7991, 8008, 8783, 7705, 7706],  # Exploder Dragonwing / Vice Dragon / Trap Eater / Archfiend Interceptor / Medium Piece Golem / Big Piece Golem
        'cards':          [8192, 7991, 8008, 8783, 7705, 7706],  # unchanged -- edit to replace
    },
    'script_112': {
        'original_cards': [7552, 7973, 7836, 8813, 8408, 7964],  # Ally of Justice Catastor / Ally of Justice Field Marshal / Ally of Justice Light Gazer / Ally of Justice Core Destroyer / Ally of Justice Quarantine / Ally of Justice Thunder Armor
        'cards':          [7552, 7973, 7836, 8813, 8408, 7964],  # unchanged -- edit to replace
    },
    'script_113': {
        'original_cards': [7552, 8813, 8408, 7964, 8111, 8112],  # Ally of Justice Catastor / Ally of Justice Core Destroyer / Ally of Justice Quarantine / Ally of Justice Thunder Armor / Ally of Justice Reverse Break / Ally of Justice Unlimiter
        'cards':          [7552, 8813, 8408, 7964, 8111, 8112],  # unchanged -- edit to replace
    },
    'script_114': {
        'original_cards': [9334, 9121, 8954, 8978, 8950, 9102],  # Atomic Scrap Dragon / Scrap Twin Dragon / Scrap Golem / Scrapyard / Scrap Chimera / Scrap Searcher
        'cards':          [9334, 9121, 8954, 8978, 8950, 9102],  # unchanged -- edit to replace
    },
    'script_115': {
        'original_cards': [9335, 8975, 8801, 9322, 9323, 9104],  # Watthydra / Wattchimera / Wattgiraffe / Wattberyx / Wattmole / Watthopper
        'cards':          [9335, 8975, 8801, 9322, 9323, 9104],  # unchanged -- edit to replace
    },
    'script_116': {
        'original_cards': [9333, 9289, 9099, 9349, 9344, 9319],  # Karakuri Steel Shogun mdl 00X "Bureido" / The Agent of Miracles - Jupiter / Karakuri Ninja mdl 339 "Sazank" / Foolish Return / Karakuri Gold Dust / Karakuri Ninja mdl 919 "Kuick"
        'cards':          [9333, 9289, 9099, 9349, 9344, 9319],  # unchanged -- edit to replace
    },
    'script_117': {
        'original_cards': [9199, 9200, 9198, 9201, 5899, 5208],  # Chevalier de Fleur / Liberty at Last! / Fleur Synchron / Sacred Knight Joan / Guardian Angel Joan / St. Joan
        'cards':          [9199, 9200, 9198, 9201, 5899, 5208],  # unchanged -- edit to replace
    },
    'script_118': {
        'original_cards': [9335, 8975, 9121, 9127, 9128, 8952],  # Watthydra / Wattchimera / Scrap Twin Dragon / Wattcastle / Wattjustment / Scrap Beast
        'cards':          [9335, 8975, 9121, 9127, 9128, 8952],  # unchanged -- edit to replace
    },
    'script_119': {
        'original_cards': [7898, 9062, 8739, 8740, 8014, 8623],  # Black Rose Dragon / Queen Angel of Roses / Stygian Sergeants / Stygian Street Patrol / Twilight Rose Knight / Witch of the Black Rose
        'cards':          [7898, 9062, 8739, 8740, 8014, 8623],  # unchanged -- edit to replace
    },
    'script_120': {
        'original_cards': [9117, 8475, 7734, 7700, 8937, 9237],  # Shooting Star Dragon / Majestic Star Dragon / Stardust Dragon / Nitro Synchron / Stronghold Guardian / Big One Warrior
        'cards':          [9117, 8475, 7734, 7700, 8937, 9237],  # unchanged -- edit to replace
    },
    'script_121': {
        'original_cards': [9119, 7735, 8192, 7871, 9086, 9297],  # Red Nova Dragon / Red Dragon Archfiend / Exploder Dragonwing / Mad Archfiend / Lancer Archfiend / Barrier Resonator
        'cards':          [9119, 7735, 8192, 7871, 9086, 9297],  # unchanged -- edit to replace
    },
    'script_122': {
        'original_cards': [8815, 8378, 8476, 8821, 8295, 9093],  # Black-Winged Dragon / Swallow's Nest / Blackwing - Silverwind the Ascendant / Cards for Black Feathers / Blackwing - Mistral the Silver Shield / Blackwing - Aurora the Northern Lights
        'cards':          [8815, 8378, 8476, 8821, 8295, 9093],  # unchanged -- edit to replace
    },
    'script_123': {
        'original_cards': [8971, 6380, 8941, 8996, 8942, 8943],  # Thunder Unicorn / Green Baboon, Defender of the Forest / Monoceros / Howl of the Wild / D.D. Unicorn Knight / Unibird
        'cards':          [8971, 6380, 8941, 8996, 8942, 8943],  # unchanged -- edit to replace
    },
    'script_124': {
        'original_cards': [8972, 5838, 8944, 9005, 8995, 8945],  # Voltic Bicorn / Wild Nature's Release / Bicorn Re'em / Beast Rising / Battle Instinct / Mine Mole
        'cards':          [8972, 5838, 8944, 9005, 8995, 8945],  # unchanged -- edit to replace
    },
    'script_125': {
        'original_cards': [8973, 4866, 8946, 9006, 8947, 8948],  # Lightning Tricorn / Royal Decree / Trident Warrior / Horn of the Phantom Beast / Delta Flyer / Rhinotaurus
        'cards':          [8973, 4866, 8946, 9006, 8947, 8948],  # unchanged -- edit to replace
    },
    'script_126': {
        'original_cards': [9331, 9364, 9308, 9363, 9310, 4861],  # Odin, Father of the Aesir / Gleipnir, the Fetters of Fenrir / Valkyrie of the Nordic Ascendant / Odin's Eye / Tyr of the Nordic Champions / Solemn Judgment
        'cards':          [9331, 9364, 9308, 9363, 9310, 4861],  # unchanged -- edit to replace
    },
    'script_127': {
        'original_cards': [9329, 9304, 9302, 9358, 9303, 5493],  # Thor, Lord of the Aesir / Tanngnjostr of the Nordic Beasts / Guldfaxe of the Nordic Beasts / Solemn Authority / Garmr of the Nordic Beasts / Malevolent Catastrophe
        'cards':          [9329, 9304, 9302, 9358, 9303, 5493],  # unchanged -- edit to replace
    },
    'script_128': {
        'original_cards': [9330, 9306, 9362, 9360, 9305, 9008],  # Loki, Lord of the Aesir / Svartalf of the Nordic Alfar / The Golden Apples / Nordic Relic Laevateinn / Ljosalf of the Nordic Alfar / Solemn Warning
        'cards':          [9330, 9306, 9362, 9360, 9305, 9008],  # unchanged -- edit to replace
    },
    'script_129': {
        'original_cards': [9117, 7735, 9118, 7687, 7708, 8786],  # Shooting Star Dragon / Red Dragon Archfiend / Formula Synchron / Junk Synchron / Dark Resonator / Flare Resonator
        'cards':          [9117, 7735, 9118, 7687, 7708, 8786],  # unchanged -- edit to replace
    },
    'script_130': {
        'original_cards': [8973, 8971, 7970, 8945, 8942, 8943],  # Lightning Tricorn / Thunder Unicorn / Dewloren, Tiger King of the Ice Barrier / Mine Mole / D.D. Unicorn Knight / Unibird
        'cards':          [8973, 8971, 7970, 8945, 8942, 8943],  # unchanged -- edit to replace
    },
    'script_131': {
        'original_cards': [6821, 9308, 9304, 9363, 9310, 9303],  # Light and Darkness Dragon / Valkyrie of the Nordic Ascendant / Tanngnjostr of the Nordic Beasts / Odin's Eye / Tyr of the Nordic Champions / Garmr of the Nordic Beasts
        'cards':          [6821, 9308, 9304, 9363, 9310, 9303],  # unchanged -- edit to replace
    },
    'script_132': {
        'original_cards': [9117, 8475, 7734, 7700, 8937, 9237],  # Shooting Star Dragon / Majestic Star Dragon / Stardust Dragon / Nitro Synchron / Stronghold Guardian / Big One Warrior
        'cards':          [9117, 8475, 7734, 7700, 8937, 9237],  # unchanged -- edit to replace
    },
    'script_133': {
        'original_cards': [9119, 7735, 8192, 7871, 9086, 9297],  # Red Nova Dragon / Red Dragon Archfiend / Exploder Dragonwing / Mad Archfiend / Lancer Archfiend / Barrier Resonator
        'cards':          [9119, 7735, 8192, 7871, 9086, 9297],  # unchanged -- edit to replace
    },
    'script_134': {
        'original_cards': [8815, 8378, 8476, 8821, 8295, 9093],  # Black-Winged Dragon / Swallow's Nest / Blackwing - Silverwind the Ascendant / Cards for Black Feathers / Blackwing - Mistral the Silver Shield / Blackwing - Aurora the Northern Lights
        'cards':          [8815, 8378, 8476, 8821, 8295, 9093],  # unchanged -- edit to replace
    },
    'script_135': {
        'original_cards': [8971, 6380, 8941, 8996, 8942, 8943],  # Thunder Unicorn / Green Baboon, Defender of the Forest / Monoceros / Howl of the Wild / D.D. Unicorn Knight / Unibird
        'cards':          [8971, 6380, 8941, 8996, 8942, 8943],  # unchanged -- edit to replace
    },
    'script_136': {
        'original_cards': [8972, 5838, 8944, 9005, 8995, 8945],  # Voltic Bicorn / Wild Nature's Release / Bicorn Re'em / Beast Rising / Battle Instinct / Mine Mole
        'cards':          [8972, 5838, 8944, 9005, 8995, 8945],  # unchanged -- edit to replace
    },
    'script_137': {
        'original_cards': [8973, 4866, 8946, 9006, 8947, 8948],  # Lightning Tricorn / Royal Decree / Trident Warrior / Horn of the Phantom Beast / Delta Flyer / Rhinotaurus
        'cards':          [8973, 4866, 8946, 9006, 8947, 8948],  # unchanged -- edit to replace
    },
    'script_138': {
        'original_cards': [9331, 9364, 9308, 9363, 9310, 4861],  # Odin, Father of the Aesir / Gleipnir, the Fetters of Fenrir / Valkyrie of the Nordic Ascendant / Odin's Eye / Tyr of the Nordic Champions / Solemn Judgment
        'cards':          [9331, 9364, 9308, 9363, 9310, 4861],  # unchanged -- edit to replace
    },
    'script_139': {
        'original_cards': [9329, 9304, 9302, 9358, 9303, 5493],  # Thor, Lord of the Aesir / Tanngnjostr of the Nordic Beasts / Guldfaxe of the Nordic Beasts / Solemn Authority / Garmr of the Nordic Beasts / Malevolent Catastrophe
        'cards':          [9329, 9304, 9302, 9358, 9303, 5493],  # unchanged -- edit to replace
    },
    'script_140': {
        'original_cards': [9330, 9306, 9362, 9360, 9305, 9008],  # Loki, Lord of the Aesir / Svartalf of the Nordic Alfar / The Golden Apples / Nordic Relic Laevateinn / Ljosalf of the Nordic Alfar / Solemn Warning
        'cards':          [9330, 9306, 9362, 9360, 9305, 9008],  # unchanged -- edit to replace
    },
    'script_141': {
        'original_cards': [9117, 7735, 9118, 7687, 7708, 8786],  # Shooting Star Dragon / Red Dragon Archfiend / Formula Synchron / Junk Synchron / Dark Resonator / Flare Resonator
        'cards':          [9117, 7735, 9118, 7687, 7708, 8786],  # unchanged -- edit to replace
    },
    'script_251': {
        'original_cards': [7625, 7683, 7797, 7166, 8086, 7721],  # Solar Recharge / Geartown / Ehren, Lightsworn Monk / Snake Rain / Treacherous Trap Hole / Destructotron
        'cards':          [7625, 7683, 7797, 7166, 8086, 7721],  # unchanged -- edit to replace
    },
    'overlay_142': {
        'original_cards': [7397, 7573, 7970, 6098, 6099, 6100],  # Thunder King Rai-Oh / Valhalla, Hall of the Fallen / Dewloren, Tiger King of the Ice Barrier / Horus the Black Flame Dragon LV4 / Horus the Black Flame Dragon LV6 / Horus the Black Flame Dragon LV8
        'cards':          [7397, 7573, 7970, 6098, 6099, 6100],  # unchanged -- edit to replace
    },
    'overlay_143': {
        'original_cards': [7557, 8602, 8296, 8667, 8672, 8833],  # Red-Eyes Darkness Metal Dragon / Gateway of the Six / Blackwing - Vayu the Emblem of Honor / Gravekeeper's Stele / Pot of Benevolence / Koa'ki Meiru Initialize!
        'cards':          [7557, 8602, 8296, 8667, 8672, 8833],  # unchanged -- edit to replace
    },
    'overlay_145': {
        'original_cards': [8262, 7454, 8001, 4659, 9293, 8321],  # Gungnir, Dragon of the Ice Barrier / Fires of Doomsday / Black Salvo / Warrior Elimination / Doppelwarrior / Genetic Woman
        'cards':          [8262, 7454, 8001, 4659, 9293, 8321],  # unchanged -- edit to replace
    },
    'overlay_146': {
        'original_cards': [7893, 5328, 8439, 8836, 6672, 8615],  # Tytannial, Princess of Camellias / Reinforcement of the Army / Quickdraw Synchron / Leeching the Light / E - Emergency Call / Drill Synchron
        'cards':          [7893, 5328, 8439, 8836, 6672, 8615],  # unchanged -- edit to replace
    },
    'overlay_147': {
        'original_cards': [8090, 5400, 9095, 4837, 8072, 4926],  # Ancient Fairy Dragon / Bottomless Trap Hole / Glow-Up Bulb / Polymerization / Metaphysical Regeneration / Mother Grizzly
        'cards':          [8090, 5400, 9095, 4837, 8072, 4926],  # unchanged -- edit to replace
    },
    'overlay_148': {
        'original_cards': [7969, 8244, 6939, 4905, 6995, 9113],  # Naturia Beast / Naturia Cliff / Card Trooper / Rush Recklessly / Ancient Rules / Anarchist Monk Ranshin
        'cards':          [7969, 8244, 6939, 4905, 6995, 9113],  # unchanged -- edit to replace
    },
    'overlay_149': {
        'original_cards': [8860, 4818, 7942, 8990, 9154, 6197],  # Junk Destroyer / Scapegoat / Parallel World Fusion / Cursed Armaments / Different Dimension Ground / Gaia Soul the Combustible Collective
        'cards':          [8860, 4818, 7942, 8990, 9154, 6197],  # unchanged -- edit to replace
    },
    'overlay_150': {
        'original_cards': [7552, 5935, 9371, 8976, 8838, 5884],  # Ally of Justice Catastor / Zoma the Spirit / Tiki Soul / Blind Spot Strike / Power Frame / Enraged Battle Ox
        'cards':          [7552, 5935, 9371, 8976, 8838, 5884],  # unchanged -- edit to replace
    },
    'overlay_151': {
        'original_cards': [4887, 5127, 8039, 5355, 9240, 4924],  # Mirror Force / Cold Wave / Cosmic Fortress Gol'gar / Shrink / Card of Sacrifice / Shining Angel
        'cards':          [4887, 5127, 8039, 5355, 9240, 4924],  # unchanged -- edit to replace
    },
    'overlay_152': {
        'original_cards': [6654, 9178, 6284, 6136, 8446, 4080],  # Dandylion / Evigishki Mind Augus / Deck Devastation Virus / Two-Man Cell Battle / Fortune Lady Dark / Giant Soldier of Stone
        'cards':          [6654, 9178, 6284, 6136, 8446, 4080],  # unchanged -- edit to replace
    },
    'overlay_153': {
        'original_cards': [8261, 7561, 4354, 6546, 7389, 8709],  # Locomotion R-Genex / Dark Grepher / Swords of Revealing Light / Mist Body / Hand Destruction / Genex Ally Birdman
        'cards':          [8261, 7561, 4354, 6546, 7389, 8709],  # unchanged -- edit to replace
    },
    'overlay_154': {
        'original_cards': [8736, 6688, 7595, 7836, 7764, 7744],  # Lightning Warrior / Majestic Mech - Ohka / Ryko, Lightsworn Hunter / Ally of Justice Light Gazer / Lightsworn Barrier / Lightwave Tuning
        'cards':          [8736, 6688, 7595, 7836, 7764, 7744],  # unchanged -- edit to replace
    },
    'overlay_155': {
        'original_cards': [7371, 5799, 6200, 5217, 5387, 4054],  # Dark End Dragon / Sakuretsu Armor / Fusilier Dragon, the Dual-Mode Beast / Lightning Vortex / A Legendary Ocean / Sangan
        'cards':          [7371, 5799, 6200, 5217, 5387, 4054],  # unchanged -- edit to replace
    },
    'overlay_156': {
        'original_cards': [5114, 9181, 9180, 4909, 9166, 9165],  # Torrential Tribute / Daigusto Eguls / Daigusto Gulldos / Mystical Space Typhoon / Gusto Thunbolt / Gusto Egul
        'cards':          [5114, 9181, 9180, 4909, 9166, 9165],  # unchanged -- edit to replace
    },
    'overlay_157': {
        'original_cards': [8933, 7594, 7900, 8962, 8023, 7892],  # Effect Veiler / Lumina, Lightsworn Summoner / Psychic Lifetrancer / Amazoness Trainee / Night Wing Sorceress / Botanical Girl
        'cards':          [8933, 7594, 7900, 8962, 8023, 7892],  # unchanged -- edit to replace
    },
    'overlay_158': {
        'original_cards': [7738, 4866, 8005, 5354, 8936, 4592],  # Thought Ruler Archfiend / Royal Decree / Debris Dragon / Spell Reproduction / A/D Changer / Greenkappa
        'cards':          [7738, 4866, 8005, 5354, 8936, 4592],  # unchanged -- edit to replace
    },
    'overlay_159': {
        'original_cards': [8818, 6078, 5400, 8835, 5330, 6195],  # Splendid Rose / Return from the Different Dimension / Bottomless Trap Hole / Forbidden Graveyard / The Warrior Returning Alive / Pitch-Black Warwolf
        'cards':          [8818, 6078, 5400, 8835, 5330, 6195],  # unchanged -- edit to replace
    },
    'overlay_160': {
        'original_cards': [4842, 6511, 8795, 6617, 7203, 6988],  # Monster Reborn / Pot of Avarice / Spore / End of the World / King Pyron / Elemental Hero Glow Neos
        'cards':          [4842, 6511, 8795, 6617, 7203, 6988],  # unchanged -- edit to replace
    },
    'overlay_161': {
        'original_cards': [6397, 8430, 7413, 7852, 6832, 6737],  # Cyber End Dragon / Cyber Eltanin / Cyber Valley / Cyber Shark / Cyberdark Keel / Cyber Summon Blaster
        'cards':          [6397, 8430, 7413, 7852, 6832, 6737],  # unchanged -- edit to replace
    },
    'overlay_162': {
        'original_cards': [8129, 8378, 6390, 5840, 5404, 8809],  # Elemental Hero Absolute Zero / Swallow's Nest / Cyber Dragon / Stumbling / Drop Off / Des Frog
        'cards':          [8129, 8378, 6390, 5840, 5404, 8809],  # unchanged -- edit to replace
    },
    'overlay_163': {
        'original_cards': [9120, 6054, 5124, 6213, 4963, 8808],  # Karakuri Shogun mdl 00 "Burei" / Level Limit - Area B / Magic Cylinder / Monster Reincarnation / Nobleman of Crossout / Testudo erat Numen
        'cards':          [9120, 6054, 5124, 6213, 4963, 8808],  # unchanged -- edit to replace
    },
    'overlay_164': {
        'original_cards': [6558, 6709, 8675, 5355, 9200, 4538],  # Gorz the Emissary of Darkness / Icarus Attack / Fiendish Chain / Shrink / Liberty at Last! / Gemini Elf
        'cards':          [6558, 6709, 8675, 5355, 9200, 4538],  # unchanged -- edit to replace
    },
    'overlay_165': {
        'original_cards': [7421, 5663, 8109, 8977, 5414, 8797],  # Dark Armed Dragon / Magical Merchant / Mist Valley Falcon / Double Cyclone / Dark Dust Spirit / Biofalcon
        'cards':          [7421, 5663, 8109, 8977, 5414, 8797],  # unchanged -- edit to replace
    },
    'overlay_166': {
        'original_cards': [6782, 5961, 4910, 8824, 6618, 8946],  # Future Fusion / Legendary Jujitsu Master / Giant Trunade / Into the Void / Samsara / Trident Warrior
        'cards':          [6782, 5961, 4910, 8824, 6618, 8946],  # unchanged -- edit to replace
    },
    'overlay_167': {
        'original_cards': [7549, 7574, 6901, 7747, 7353, 8783],  # Mist Wurm / Honest / Instant Fusion / Emergency Teleport / Dark Cure / Archfiend Interceptor
        'cards':          [7549, 7574, 6901, 7747, 7353, 8783],  # unchanged -- edit to replace
    },
    'overlay_168': {
        'original_cards': [9394, 7400, 4821, 6458, 5427, 8157],  # Vylon Omega / Dimensional Prison / Card Destruction / Divine Sword - Phoenix Blade / Des Lacooda / Dark Verger
        'cards':          [9394, 7400, 4821, 6458, 5427, 8157],  # unchanged -- edit to replace
    },
    'overlay_169': {
        'original_cards': [8960, 7991, 5905, 5531, 8207, 8966],  # Naturia Bamboo Shoot / Vice Dragon / Smashing Ground / Dark Room of Nightmare / Iron Core of Koa'ki Meiru / Synchro Fusionist
        'cards':          [8960, 7991, 5905, 5531, 8207, 8966],  # unchanged -- edit to replace
    },
    'overlay_170': {
        'original_cards': [7987, 9335, 8975, 5225, 5978, 8033],  # Armory Arm / Watthydra / Wattchimera / The Dark Door / Mystik Wok / Alien Overlord
        'cards':          [7987, 9335, 8975, 5225, 5978, 8033],  # unchanged -- edit to replace
    },
    'overlay_171': {
        'original_cards': [8038, 7592, 8023, 6168, 5869, 8464],  # Arcanite Magician / Lyla, Lightsworn Sorceress / Night Wing Sorceress / Magician's Circle / Magician's Valkyria / Tuned Magician
        'cards':          [8038, 7592, 8023, 6168, 5869, 8464],  # unchanged -- edit to replace
    },
    'overlay_172': {
        'original_cards': [9244, 5162, 4989, 5606, 7891, 4557],  # Blackwing - Zephyrus the Elite / Creature Swap / Call of the Haunted / Autonomous Action Unit / Psychic Jumper / Dark Elf
        'cards':          [9244, 5162, 4989, 5606, 7891, 4557],  # unchanged -- edit to replace
    },
    'overlay_173': {
        'original_cards': [6784, 6001, 5399, 5170, 4908, 8634],  # Elemental Hero Stratos / Doomcaliber Knight / Royal Oppression / Ground Collapse / Chain Energy / Supay
        'cards':          [6784, 6001, 5399, 5170, 4908, 8634],  # unchanged -- edit to replace
    },
    'overlay_174': {
        'original_cards': [5533, 5822, 5509, 9319, 4617, 6506],  # Necrovalley / D.D. Scout Plane / Gravekeeper's Spy / Karakuri Ninja mdl 919 "Kuick" / Hiro's Shadow Scout / Scarr, Scout of Dark World
        'cards':          [5533, 5822, 5509, 9319, 4617, 6506],  # unchanged -- edit to replace
    },
    'overlay_175': {
        'original_cards': [7674, 4866, 5526, 5352, 7476, 9078],  # Herald of Perfection / Royal Decree / Spirit Reaper / Dragged Down into the Grave / Offering to the Snake Deity / Swift Scarecrow
        'cards':          [7674, 4866, 5526, 5352, 7476, 9078],  # unchanged -- edit to replace
    },
    'overlay_176': {
        'original_cards': [8350, 8328, 7687, 5350, 4663, 8497],  # Rekindling / Flamvell Firedog / Junk Synchron / Emergency Provisions / Megamorph / Faustian Bargain
        'cards':          [8350, 8328, 7687, 5350, 4663, 8497],  # unchanged -- edit to replace
    },
    'overlay_177': {
        'original_cards': [8974, 9126, 8950, 8953, 8954, 8980],  # Scrap Dragon / Scrap Lube / Scrap Chimera / Scrap Hunter / Scrap Golem / Scrap Sheen
        'cards':          [8974, 9126, 8950, 8953, 8954, 8980],  # unchanged -- edit to replace
    },
    'overlay_178': {
        'original_cards': [8172, 8481, 8171, 8600, 8760, 5916],  # Earthbound Immortal Ccapac Apu / Earthbound Whirlwind / Earthbound Immortal Aslla piscu / Earthbound Revival / Earthbound Linewalker / Self-Destruct Button
        'cards':          [8172, 8481, 8171, 8600, 8760, 5916],  # unchanged -- edit to replace
    },
    'overlay_179': {
        'original_cards': [9176, 9171, 8089, 8352, 5298, 8716],  # Steelswarm Girastag / Steelswarm Scout / Tragoedia / Fossil Dig / Nightmare Wheel / Dragunity Corsesca
        'cards':          [9176, 9171, 8089, 8352, 5298, 8716],  # unchanged -- edit to replace
    },
    'overlay_180': {
        'original_cards': [6821, 7454, 7096, 5784, 6623, 8636],  # Light and Darkness Dragon / Fires of Doomsday / Destiny Hero - Plasma / Contract with the Abyss / Success Probability 0% / Koa'ki Meiru Urnight
        'cards':          [6821, 7454, 7096, 5784, 6623, 8636],  # unchanged -- edit to replace
    },
    'overlay_181': {
        'original_cards': [9287, 9289, 9288, 6705, 5537, 4924],  # Master Hyperion / The Agent of Miracles - Jupiter / The Agent of Mystery - Earth / Celestial Transformation / Terraforming / Shining Angel
        'cards':          [9287, 9289, 9288, 6705, 5537, 4924],  # unchanged -- edit to replace
    },
    'overlay_182': {
        'original_cards': [8137, 5212, 5213, 5669, 8049, 7225],  # Power Tool Dragon / United We Stand / Mage Power / Big Bang Shot / Psychic Sword / Broken Bamboo Sword
        'cards':          [8137, 5212, 5213, 5669, 8049, 7225],  # unchanged -- edit to replace
    },
    'overlay_183': {
        'original_cards': [8091, 8058, 4758, 9139, 5403, 6566],  # Stardust Dragon/Assault Mode / Assault Mode Activate / Jinzo / Heat Wave / Nutrient Z / Elemental Hero Bubbleman
        'cards':          [8091, 8058, 4758, 9139, 5403, 6566],  # unchanged -- edit to replace
    },
    'overlay_184': {
        'original_cards': [7570, 7400, 7145, 5214, 4963, 8800],  # Allure of Darkness / Dimensional Prison / Grandmaster of the Six Samurai / Offerings to the Doomed / Nobleman of Crossout / Lyna the Light Charmer
        'cards':          [7570, 7400, 7145, 5214, 4963, 8800],  # unchanged -- edit to replace
    },
    'overlay_185': {
        'original_cards': [7397, 9104, 8811, 7879, 7058, 4431],  # Thunder King Rai-Oh / Watthopper / Batteryman Fuel Cell / Morphtronic Radion / Elemental Hero Voltic / Thunder Dragon
        'cards':          [7397, 9104, 8811, 7879, 7058, 4431],  # unchanged -- edit to replace
    },
    'overlay_186': {
        'original_cards': [7898, 4861, 4692, 8991, 8367, 8709],  # Black Rose Dragon / Solemn Judgment / Widespread Ruin / Wiseman's Chalice / Psychic Soul / Genex Ally Birdman
        'cards':          [7898, 4861, 4692, 8991, 8367, 8709],  # unchanged -- edit to replace
    },
    'overlay_187': {
        'original_cards': [9062, 7568, 7595, 6912, 5248, 8796],  # Queen Angel of Roses / Lonefire Blossom / Ryko, Lightsworn Hunter / Justi-Break / Kycoo the Ghost Destroyer / Fairy Archer
        'cards':          [9062, 7568, 7595, 6912, 5248, 8796],  # unchanged -- edit to replace
    },
    'overlay_188': {
        'original_cards': [4342, 5905, 4835, 4856, 4836, 5544],  # Dark Hole / Smashing Ground / Fissure / Tribute to The Doomed / Trap Hole / Raigeki Break
        'cards':          [4342, 5905, 4835, 4856, 4836, 5544],  # unchanged -- edit to replace
    },
    'overlay_189': {
        'original_cards': [8283, 7573, 4910, 8992, 8683, 6960],  # Archlord Kristya / Valhalla, Hall of the Fallen / Giant Trunade / Summoning Curse / Core Blast / Gene-Warped Warwolf
        'cards':          [8283, 7573, 4910, 8992, 8683, 6960],  # unchanged -- edit to replace
    },
    'overlay_190': {
        'original_cards': [7261, 7381, 8609, 6617, 8166, 4927],  # Evil Hero Dark Gaia / Dark Calling / Starlight Road / End of the World / Morphtronic Remoten / Flying Kamakiri #1
        'cards':          [7261, 7381, 8609, 6617, 8166, 4927],  # unchanged -- edit to replace
    },
    'overlay_191': {
        'original_cards': [7346, 6332, 7403, 5606, 7048, 6655],  # Beast King Barbaros / D.D. Survivor / Chimeratech Fortress Dragon / Autonomous Action Unit / Harvest Angel of Wisdom / Elemental Hero Phoenix Enforcer
        'cards':          [7346, 6332, 7403, 5606, 7048, 6655],  # unchanged -- edit to replace
    },
    'overlay_192': {
        'original_cards': [7516, 6603, 5905, 8282, 9004, 4926],  # Caius the Shadow Monarch / Treeborn Frog / Smashing Ground / Gottoms' Emergency Call / Queen's Pawn / Mother Grizzly
        'cards':          [7516, 6603, 5905, 8282, 9004, 4926],  # unchanged -- edit to replace
    },
    'overlay_193': {
        'original_cards': [7617, 7285, 7405, 8982, 5234, 6258],  # Gladiator Beast Gyzarus / Gladiator Beast Bestiari / Fossil Dyna Pachycephalo / Naturia Forest / Embodiment of Apophis / The Earth - Hex-Sealed Fusion
        'cards':          [7617, 7285, 7405, 8982, 5234, 6258],  # unchanged -- edit to replace
    },
    'overlay_194': {
        'original_cards': [8334, 8655, 8753, 9134, 9239, 8327],  # XX-Saber Gottoms / XX-Saber Hyunlei / XX-Saber Emmersblade / Darkworld Shackles / Synchro Gift / XX-Saber Ragigura
        'cards':          [8334, 8655, 8753, 9134, 9239, 8327],  # unchanged -- edit to replace
    },
    'overlay_195': {
        'original_cards': [8817, 8823, 4818, 6785, 8756, 8932],  # Infernity Doom Dragon / Infernity Launcher / Scapegoat / Hero's Bond / Cactus Bouncer / Earthquake Giant
        'cards':          [8817, 8823, 4818, 6785, 8756, 8932],  # unchanged -- edit to replace
    },
    'overlay_196': {
        'original_cards': [9122, 7986, 8581, 8378, 8207, 6949],  # Tuning / Tuningware / Junk Archer / Swallow's Nest / Iron Core of Koa'ki Meiru / Destiny Hero - Malicious
        'cards':          [9122, 7986, 8581, 8378, 8207, 6949],  # unchanged -- edit to replace
    },
    'overlay_197': {
        'original_cards': [8865, 9232, 5399, 6431, 7694, 9175],  # Malefic Stardust Dragon / Malefic World / Royal Oppression / Fusion Recovery / Scrap-Iron Scarecrow / Steelswarm Moth
        'cards':          [8865, 9232, 5399, 6431, 7694, 9175],  # unchanged -- edit to replace
    },
    'overlay_198': {
        'original_cards': [7868, 7625, 7735, 8979, 6435, 8259],  # Charge of the Light Brigade / Solar Recharge / Red Dragon Archfiend / Scrapstorm / Des Croaking / Jurrac Velphito
        'cards':          [7868, 7625, 7735, 8979, 6435, 8259],  # unchanged -- edit to replace
    },
    'overlay_199': {
        'original_cards': [9046, 8392, 4989, 4837, 8677, 4930],  # Dragunity Arma Leyvaten / Dragunity Phalanx / Call of the Haunted / Polymerization / Serpent Suppression / Mystic Tomato
        'cards':          [9046, 8392, 4989, 4837, 8677, 4930],  # unchanged -- edit to replace
    },
    'overlay_200': {
        'original_cards': [7736, 6432, 7445, 8435, 8060, 9078],  # Goyo Guardian / Miracle Fusion / Super Polymerization / Supervise / Descending Lost Star / Swift Scarecrow
        'cards':          [7736, 6432, 7445, 8435, 8060, 9078],  # unchanged -- edit to replace
    },
    'overlay_201': {
        'original_cards': [7557, 7982, 7698, 5743, 6448, 5031],  # Red-Eyes Darkness Metal Dragon / Red-Eyes Wyvern / Colossal Fighter / Soul Taker / Dimension Wall / Injection Fairy Lily
        'cards':          [7557, 7982, 7698, 5743, 6448, 5031],  # unchanged -- edit to replace
    },
    'overlay_202': {
        'original_cards': [7548, 8013, 8163, 5603, 8379, 6989],  # Brionac, Dragon of the Ice Barrier / Blackwing - Sirocco the Dawn / Blackwing - Shura the Blue Flame / Demotion / Overwhelm / Elemental Hero Air Neos
        'cards':          [7548, 8013, 8163, 5603, 8379, 6989],  # unchanged -- edit to replace
    },
    'overlay_203': {
        'original_cards': [9332, 9311, 8602, 5840, 8219, 8617],  # Legendary Six Samurai - Shi En / Legendary Six Samurai - Kizan / Gateway of the Six / Stumbling / Wicked Rebirth / Battle Fader
        'cards':          [9332, 9311, 8602, 5840, 8219, 8617],  # unchanged -- edit to replace
    },
    'overlay_204': {
        'original_cards': [8993, 8693, 6996, 8862, 8228, 8196],  # Pot of Duality / Machina Gearframe / Advanced Ritual Art / Synchron Explorer / Proof of Powerlessness / Sea Dragon Lord Gishilnodon
        'cards':          [8993, 8693, 6996, 8862, 8228, 8196],  # unchanged -- edit to replace
    },
    'overlay_205': {
        'original_cards': [6656, 7594, 7900, 6434, 6646, 7426],  # Elemental Hero Shining Phoenix Enforcer / Lumina, Lightsworn Summoner / Psychic Lifetrancer / System Down / Helios - The Primordial Sun / Shadowpriestess of Ohm
        'cards':          [6656, 7594, 7900, 6434, 6646, 7426],  # unchanged -- edit to replace
    },
    'overlay_206': {
        'original_cards': [8283, 8318, 6939, 6995, 6287, 6324],  # Archlord Kristya / Fishborg Blaster / Card Trooper / Ancient Rules / Vampire's Curse / Megarock Dragon
        'cards':          [8283, 8318, 6939, 6995, 6287, 6324],  # unchanged -- edit to replace
    },
    'overlay_207': {
        'original_cards': [7371, 7297, 8234, 8825, 8696, 8265],  # Dark End Dragon / Enishi, Shien's Chancellor / Fabled Krus / Intercept Wave / Machina Armored Unit / Ojama Blue
        'cards':          [7371, 7297, 8234, 8825, 8696, 8265],  # unchanged -- edit to replace
    },
    'overlay_208': {
        'original_cards': [5114, 7318, 7319, 8482, 5133, 6387],  # Torrential Tribute / Light-Imprisoning Mirror / Shadow-Imprisoning Mirror / Savage Colosseum / Magic Drain / Drillroid
        'cards':          [5114, 7318, 7319, 8482, 5133, 6387],  # unchanged -- edit to replace
    },
    'overlay_209': {
        'original_cards': [5127, 7561, 4692, 8056, 8079, 8080],  # Cold Wave / Dark Grepher / Widespread Ruin / Arcane Barrier / Cactus Fighter / Overdrive Teleporter
        'cards':          [5127, 7561, 4692, 8056, 8079, 8080],  # unchanged -- edit to replace
    },
    'overlay_210': {
        'original_cards': [8556, 8287, 7595, 8348, 8349, 8690],  # The Fabled Cerburrel / Darklord Asmodeus / Ryko, Lightsworn Hunter / Saber Slash / Sword of Sparkles / Widespread Dud
        'cards':          [8556, 8287, 7595, 8348, 8349, 8690],  # unchanged -- edit to replace
    },
    'overlay_211': {
        'original_cards': [8521, 8328, 7687, 6515, 8810, 8811],  # XX-Saber Gardestrike / Flamvell Firedog / Junk Synchron / Gateway to Dark World / Batteryman AAA / Batteryman Fuel Cell
        'cards':          [8521, 8328, 7687, 6515, 8810, 8811],  # unchanged -- edit to replace
    },
    'overlay_212': {
        'original_cards': [7552, 5162, 4989, 8853, 8703, 8704],  # Ally of Justice Catastor / Creature Swap / Call of the Haunted / Crevice Into the Different Dimension / Neo Flamvell Origin / Neo Flamvell Hedgehog
        'cards':          [7552, 5162, 4989, 8853, 8703, 8704],  # unchanged -- edit to replace
    },
    'overlay_213': {
        'original_cards': [6467, 7423, 7248, 8375, 6315, 6527],  # Elemental Hero Shining Flare Wingman / Armageddon Knight / Trade-In / Moja / Ancient Gear Golem / Elemental Hero Necroshade
        'cards':          [6467, 7423, 7248, 8375, 6315, 6527],  # unchanged -- edit to replace
    },
    'overlay_214': {
        'original_cards': [4342, 7567, 7247, 8358, 8598, 8599],  # Dark Hole / Prime Material Dragon / Decoy Dragon / Discord / Gemini Scorpion / Metabo-Shark
        'cards':          [4342, 7567, 7247, 8358, 8598, 8599],  # unchanged -- edit to replace
    },
    'overlay_215': {
        'original_cards': [9047, 7399, 8282, 8660, 8096, 5067],  # Dragunity Arma Mystletainn / Burden of the Mighty / Gottoms' Emergency Call / Viper's Rebirth / Jurrac Protops / Rocket Warrior
        'cards':          [9047, 7399, 8282, 8660, 8096, 5067],  # unchanged -- edit to replace
    },
    'overlay_216': {
        'original_cards': [7597, 7400, 7145, 8688, 6222, 6256],  # Celestia, Lightsworn Angel / Dimensional Prison / Grandmaster of the Six Samurai / Tuner's Scheme / Fuh-Rin-Ka-Zan / The Light - Hex-Sealed Fusion
        'cards':          [7597, 7400, 7145, 8688, 6222, 6256],  # unchanged -- edit to replace
    },
    'overlay_217': {
        'original_cards': [6821, 7384, 7285, 8720, 8721, 8317],  # Light and Darkness Dragon / Phantom Skyblaster / Gladiator Beast Bestiari / Naturia Stinkbug / Naturia Mantis / Divine Dragon Aquabizarre
        'cards':          [6821, 7384, 7285, 8720, 8721, 8317],  # unchanged -- edit to replace
    },
    'overlay_218': {
        'original_cards': [7562, 6969, 6284, 7316, 4962, 5037],  # Darklord Zerato / Great Shogun Shien / Deck Devastation Virus / Updraft / Magical Hats / Slate Warrior
        'cards':          [7562, 6969, 6284, 7316, 4962, 5037],  # unchanged -- edit to replace
    },
    'overlay_219': {
        'original_cards': [9332, 8089, 7245, 4659, 8067, 8264],  # Legendary Six Samurai - Shi En / Tragoedia / Darkblaze Dragon / Warrior Elimination / Morphtronic Forcefield / Ojama Red
        'cards':          [9332, 8089, 7245, 4659, 8067, 8264],  # unchanged -- edit to replace
    },
    'overlay_220': {
        'original_cards': [7570, 6709, 8675, 5784, 6623, 8636],  # Allure of Darkness / Icarus Attack / Fiendish Chain / Contract with the Abyss / Success Probability 0% / Koa'ki Meiru Urnight
        'cards':          [7570, 6709, 8675, 5784, 6623, 8636],  # unchanged -- edit to replace
    },
    'overlay_221': {
        'original_cards': [8038, 7153, 7093, 8714, 8179, 8098],  # Arcanite Magician / Eradicator Epidemic Virus / Spell Striker / The Fabled Kokkator / Brain Golem / Jurrac Monoloph
        'cards':          [8038, 7153, 7093, 8714, 8179, 8098],  # unchanged -- edit to replace
    },
    'overlay_222': {
        'original_cards': [9177, 4866, 7445, 8825, 6505, 6614],  # Steelswarm Caucastag / Royal Decree / Super Polymerization / Intercept Wave / Goldd, Wu-Lord of Dark World / D.3.S. Frog
        'cards':          [9177, 4866, 7445, 8825, 6505, 6614],  # unchanged -- edit to replace
    },
    'overlay_223': {
        'original_cards': [8129, 7381, 7093, 6470, 6689, 6657],  # Elemental Hero Absolute Zero / Dark Calling / Spell Striker / Ojamagic / Majestic Mech - Goryu / Elemental Hero Mariner
        'cards':          [8129, 7381, 7093, 6470, 6689, 6657],  # unchanged -- edit to replace
    },
    'overlay_224': {
        'original_cards': [8993, 6511, 9095, 7221, 6444, 9114],  # Pot of Duality / Pot of Avarice / Glow-Up Bulb / Creature Seizure / Magical Explosion / Delg the Dark Monarch
        'cards':          [8993, 6511, 9095, 7221, 6444, 9114],  # unchanged -- edit to replace
    },
    'overlay_225': {
        'original_cards': [7421, 6396, 7595, 8056, 5423, 8252],  # Dark Armed Dragon / Cyber Twin Dragon / Ryko, Lightsworn Hunter / Arcane Barrier / Pyramid Turtle / Dewdark of the Ice Barrier
        'cards':          [7421, 6396, 7595, 8056, 5423, 8252],  # unchanged -- edit to replace
    },
    'overlay_226': {
        'original_cards': [4342, 8604, 6980, 9324, 9325, 9326],  # Dark Hole / Hundred Eyes Dragon / D.D. Crow / Symphonic Warrior Basses / Symphonic Warrior Drumss / Symphonic Warrior Piaano
        'cards':          [4342, 8604, 6980, 9324, 9325, 9326],  # unchanged -- edit to replace
    },
    'overlay_227': {
        'original_cards': [7898, 8085, 5124, 9184, 7769, 5496],  # Black Rose Dragon / Tempest Magician / Magic Cylinder / First Step Towards Infestation / Needlebug Nest / Lava Golem
        'cards':          [7898, 8085, 5124, 9184, 7769, 5496],  # unchanged -- edit to replace
    },
    'overlay_228': {
        'original_cards': [7117, 8036, 8037, 7718, 7719, 7720],  # Raiza the Storm Monarch / Blackwing Armor Master / Hyper Psychic Blaster / Psychic Commander / Psychic Snail / Telekinetic Shocker
        'cards':          [7117, 8036, 8037, 7718, 7719, 7720],  # unchanged -- edit to replace
    },
    'overlay_229': {
        'original_cards': [5114, 7491, 7942, 8958, 8959, 7899],  # Torrential Tribute / Elemental Hero Prisma / Parallel World Fusion / Naturia Mosquito / Naturia Beans / Iron Chain Dragon
        'cards':          [5114, 7491, 7942, 8958, 8959, 7899],  # unchanged -- edit to replace
    },
    'overlay_230': {
        'original_cards': [8260, 8333, 4354, 6213, 7694, 7608],  # Naturia Barkion / Ancient Sacred Wyvern / Swords of Revealing Light / Monster Reincarnation / Scrap-Iron Scarecrow / Diskblade Rider
        'cards':          [8260, 8333, 4354, 6213, 7694, 7608],  # unchanged -- edit to replace
    },
    'overlay_231': {
        'original_cards': [4842, 8731, 9049, 8335, 8687, 7956],  # Monster Reborn / Dragunity Knight - Barcha / Dragon Ravine / Release Restraint Wave / Forgotten Temple of the Deep / Mist Valley Baby Roc
        'cards':          [4842, 8731, 9049, 8335, 8687, 7956],  # unchanged -- edit to replace
    },
    'overlay_232': {
        'original_cards': [6613, 8605, 8089, 8347, 9153, 9112],  # Demise, King of Armageddon / Zeman the Ape King / Tragoedia / Brain Research Lab / Vanity's Emptiness / Wightmare
        'cards':          [6613, 8605, 8089, 8347, 9153, 9112],  # unchanged -- edit to replace
    },
    'overlay_233': {
        'original_cards': [7736, 5399, 7897, 8055, 9376, 9377],  # Goyo Guardian / Royal Oppression / Turbo Warrior / Verdant Sanctuary / Vylon Tetrah / Vylon Stella
        'cards':          [7736, 5399, 7897, 8055, 9376, 9377],  # unchanged -- edit to replace
    },
    'overlay_234': {
        'original_cards': [6654, 8816, 7857, 9133, 8422, 8369],  # Dandylion / Chaos King Archfiend / Zombie World / Koa'ki Ring / Dragonic Tactics / At One With the Sword
        'cards':          [6654, 8816, 7857, 9133, 8422, 8369],  # unchanged -- edit to replace
    },
    'overlay_235': {
        'original_cards': [7570, 7937, 8296, 8495, 8264, 8265],  # Allure of Darkness / Kasha / Blackwing - Vayu the Emblem of Honor / Raging Mad Plants / Ojama Red / Ojama Blue
        'cards':          [7570, 7937, 8296, 8495, 8264, 8265],  # unchanged -- edit to replace
    },
    'overlay_236': {
        'original_cards': [7562, 7982, 6996, 6546, 8758, 8477],  # Darklord Zerato / Red-Eyes Wyvern / Advanced Ritual Art / Mist Body / The Dragon Dwelling in the Deep / Reptilianne Hydra
        'cards':          [7562, 7982, 6996, 6546, 8758, 8477],  # unchanged -- edit to replace
    },
    'overlay_237': {
        'original_cards': [7557, 7574, 7697, 9125, 7752, 8280],  # Red-Eyes Darkness Metal Dragon / Honest / Gaia Knight, the Force of Earth / Karakuri Anatomy / Book of Eclipse / Powered Tuner
        'cards':          [7557, 7574, 7697, 9125, 7752, 8280],  # unchanged -- edit to replace
    },
    'overlay_238': {
        'original_cards': [8283, 7854, 7405, 8257, 8411, 8412],  # Archlord Kristya / Red-Eyes Zombie Dragon / Fossil Dyna Pachycephalo / Worm Victory / Worm Xex / Worm Yagan
        'cards':          [8283, 7854, 7405, 8257, 8411, 8412],  # unchanged -- edit to replace
    },
    'overlay_239': {
        'original_cards': [8974, 8392, 6284, 9131, 4836, 4917],  # Scrap Dragon / Dragunity Phalanx / Deck Devastation Virus / Medallion of the Ice Barrier / Trap Hole / UFO Turtle
        'cards':          [8974, 8392, 6284, 9131, 4836, 4917],  # unchanged -- edit to replace
    },
    'overlay_240': {
        'original_cards': [7548, 9118, 7735, 8337, 7824, 8295],  # Brionac, Dragon of the Ice Barrier / Formula Synchron / Red Dragon Archfiend / Advance Draw / X-Saber Pashuul / Blackwing - Mistral the Silver Shield
        'cards':          [7548, 9118, 7735, 8337, 7824, 8295],  # unchanged -- edit to replace
    },
    'overlay_241': {
        'original_cards': [7346, 6511, 7145, 9238, 8323, 8456],  # Beast King Barbaros / Pot of Avarice / Grandmaster of the Six Samurai / Battle Waltz / Cyborg Doctor / Reptilianne Medusa
        'cards':          [7346, 6511, 7145, 9238, 8323, 8456],  # unchanged -- edit to replace
    },
    'overlay_242': {
        'original_cards': [6558, 7592, 9121, 7591, 7593, 7598],  # Gorz the Emissary of Darkness / Lyla, Lightsworn Sorceress / Scrap Twin Dragon / Jain, Lightsworn Paladin / Garoth, Lightsworn Warrior / Gragonith, Lightsworn Dragon
        'cards':          [6558, 7592, 9121, 7591, 7593, 7598],  # unchanged -- edit to replace
    },
    'overlay_243': {
        'original_cards': [8993, 9311, 7445, 8050, 5423, 8300],  # Pot of Duality / Legendary Six Samurai - Kizan / Super Polymerization / Telekinetic Power Well / Pyramid Turtle / Jester Confit
        'cards':          [8993, 9311, 7445, 8050, 5423, 8300],  # unchanged -- edit to replace
    },
    'overlay_244': {
        'original_cards': [7734, 8475, 7403, 7903, 7990, 8315],  # Stardust Dragon / Majestic Star Dragon / Chimeratech Fortress Dragon / Mark of the Rose / Shield Wing / Shiny Black "C"
        'cards':          [7734, 8475, 7403, 7903, 7990, 8315],  # unchanged -- edit to replace
    },
    'overlay_245': {
        'original_cards': [8193, 4861, 8675, 8528, 8555, 8637],  # Blackwing Armed Wing / Solemn Judgment / Fiendish Chain / Pseudo Space / The Fabled Catsith / XX-Saber Garsem
        'cards':          [8193, 4861, 8675, 8528, 8555, 8637],  # unchanged -- edit to replace
    },
    'overlay_246': {
        'original_cards': [8603, 4354, 9049, 6439, 6186, 8176],  # Underground Arachnid / Swords of Revealing Light / Dragon Ravine / Spiritual Earth Art - Kurogane / Harpie Lady 1 / Koa'ki Meiru Drago
        'cards':          [8603, 4354, 9049, 6439, 6186, 8176],  # unchanged -- edit to replace
    },
    'overlay_247': {
        'original_cards': [8860, 8439, 6980, 6442, 6187, 8177],  # Junk Destroyer / Quickdraw Synchron / D.D. Crow / Spiritual Wind Art - Miyabi / Harpie Lady 2 / Koa'ki Meiru Ice
        'cards':          [8860, 8439, 6980, 6442, 6187, 8177],  # unchanged -- edit to replace
    },
    'overlay_248': {
        'original_cards': [9219, 8392, 8005, 6440, 6188, 8178],  # Driven Daredevil / Dragunity Phalanx / Debris Dragon / Spiritual Water Art - Aoi / Harpie Lady 3 / Koa'ki Meiru Doom
        'cards':          [9219, 8392, 8005, 6440, 6188, 8178],  # unchanged -- edit to replace
    },
    'overlay_249': {
        'original_cards': [7261, 7491, 7413, 6441, 6175, 8310],  # Evil Hero Dark Gaia / Elemental Hero Prisma / Cyber Valley / Spiritual Fire Art - Kurenai / Harpie Girl / Koa'ki Meiru Crusader
        'cards':          [7261, 7491, 7413, 6441, 6175, 8310],  # unchanged -- edit to replace
    },
    'overlay_250': {
        'original_cards': [8261, 5399, 8655, 6800, 6801, 6804],  # Locomotion R-Genex / Royal Oppression / XX-Saber Hyunlei / Alien Grey / Alien Mars / Alien Warrior
        'cards':          [8261, 5399, 8655, 6800, 6801, 6804],  # unchanged -- edit to replace
    },
    'overlay_251': {
        'original_cards': [9244, 7986, 6939, 8490, 8449, 8326],  # Blackwing - Zephyrus the Elite / Tuningware / Card Trooper / Gemini Spark / Catoblepas and the Witch of Fate / XX-Saber Faultroll
        'cards':          [9244, 7986, 6939, 8490, 8449, 8326],  # unchanged -- edit to replace
    },
}

def find_record_by_cards(cards, all_records):
    for record in all_records:
        if set(cards) == set(record.get("cards", [])):
            return record
    return None

def main(src: str, out: str) -> None:
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    overlays = rom.loadArm9Overlays([REWARD_OVERLAY_ID])
    ov = overlays[REWARD_OVERLAY_ID]
    ov_data = bytes(ov.data)

    pac_path = next((p for p in _iter_paths(rom.filenames) if p.lower().endswith("rpg_script_j.pac")), None)
    fid = rom.filenames.idOf(pac_path)                          # resolve the archive's file id in the ROM
    orig_pac = bytes(rom.files[fid])                            # ORIGINAL bin2.pac bytes (inner addresses are relative to this)
    archive = parse_pac(orig_pac, pac_path)
    script_rewards = []
    for script_idx, script_name in SCRIPT_IDX_MAP.items():
        pac_file = archive.files[script_idx]
        raw = orig_pac[pac_file.address:pac_file.address + pac_file.size]
        try:
            dec = bytes(ndspy.lz10.decompress(raw))
        except Exception:
            continue
        for rec in parse_script_rewards(dec):
            rec["record_id"] = rec["duel_id"]
            rec["value"] = rec.get("param", 0)
            rec["source"] = "script"
            rec["script_idx"] = script_idx
            rec["script_name"] = script_name
            script_rewards.append(rec)
    ov_rewards = parse_duel_rewards(ov_data)
    script_rewards.extend(ov_rewards)
    script_overrides: dict[int, bytes] = {}
    for k, rec in RECORDS.items():
        target_record = find_record_by_cards(rec["original_cards"], script_rewards)
        if not target_record:
            print(f"Could not find record for {k} with cards {rec['original_cards']}")
            continue
        ov_data = apply_change(target_record, ov_data, archive, script_overrides, new_cards=rec["cards"])

    # Write the modified overlay back into the ROM
    ov.data = bytes(ov_data)
    ov.ramSize = len(ov_data)
    compressed = ov.save(compress=ov.compressed)
    rom.files[ov.fileID] = compressed

    # Only rewrite the PAC when a script-sourced reward actually changed.
    if script_overrides:
        rom.files[fid] = build_modified_pac(orig_pac, pac_path, script_overrides)

    rom.saveToFile(out)
if __name__ == "__main__":
    main(src=SRC, out=OUT)