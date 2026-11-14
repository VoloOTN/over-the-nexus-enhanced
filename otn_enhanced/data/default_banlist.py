"""Patch that modifies the banlist in a Yu-Gi-Oh! NDS ROM.

This module allows you to ban, limit, or semi-limit specific cards by modifying
the limit*.bin file inside bin.pac (or bin2.pac for newer games).

Usage:
  1. Configure SRC, OUT, and the card lists below.
  2. Run: python -m otn_enhanced.data.default_banlist
  3. The modified ROM will be written to OUT.

Example:
  # Ban cards 1, 2, 3
  BANNED = [1, 2, 3]
  # Limit cards 10, 20, 30
  LIMITED = [10, 20, 30]
  # Semi-limit cards 100, 200
  SEMI = [100, 200]
"""

import json
import logging
import tempfile
from pathlib import Path

from otn_enhanced.data.card_stats import iter_paths
from otn_enhanced.rom.limit_codec import decode_limit, encode_limit
import ndspy.rom
from otn_enhanced.rom.pac import parse_pac, repack_pac

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_test.nds"

# Card Konami IDs to modify.  Specify empty lists if no changes are needed.
BANNED = [ # Cards to mark as Forbidden (0 copies)
'Chaos Emperor Dragon - Envoy of the End',
'Cyber Jar',
'Cyber-Stein',
'Dark Magician of Chaos',
'Destiny Hero - Disk Commander',
'Fiber Jar',
'Magical Scientist',
'Magician of Faith',
'Makyura the Destructor',
'Rescue Cat',
'Sinister Serpent',
'Tribe-Infecting Virus',
'Tsukuyomi',
'Victory Dragon',
'Witch of the Black Forest',
'Yata-Garasu',
'Thousand-Eyes Restrict',
'Dark Strike Fighter',
'Goyo Guardian',
'Brain Control',
'Butterfly Dagger - Elma',
'Card of Safe Return',
'Change of Heart',
'Cold Wave',
'Confiscation',
'Delinquent Duo',
'Dimension Fusion',
'Giant Trunade',
'Graceful Charity',
'Harpie\'s Feather Duster',
# 'Last Will',  # REMOVED from the banlist: converted to W Nebula Meteorite (w_nebula_meteorite)
'Mass Driver',
'Metamorphosis',
'Mirage of Nightmare',
'Painful Choice',
'Pot of Greed',
'Premature Burial',
'Raigeki',
'Snatch Steal',
'Temple of the Kings',
'The Forceful Sentry',
'Crush Card Virus',
'Exchange of the Spirit',
'Imperial Order',
'Last Turn',
'Ring of Destruction',
'Royal Oppression',
'Sixth Sense',
'Time Seal',
"Trap Dustshoot",
]          
LIMITED = [ # Cards to mark as Limited (1 copy)
'Left Arm of the Forbidden One',
'Right Arm of the Forbidden One',
'Left Leg of the Forbidden One',
'Right Leg of the Forbidden One',
'Black Luster Soldier - Envoy of the Beginning',
'Blackwing - Gale the Whirlwind',
'Mind Master',
'Fishborg Blaster',
'Substitoad',
'Dark Armed Dragon',
'Elemental Hero Stratos',
'Exodia the Forbidden One',
'Gorz the Emissary of Darkness',
'Lumina, Lightsworn Summoner',
'Marshmallon',
'Mezuki',
'Morphing Jar',
'Necroface',
'Neo-Spacian Grand Mole',
'Night Assailant',
'Plaguespreader Zombie',
'Sangan',
'Brionac, Dragon of the Ice Barrier',
'Formula Synchron',
'Legendary Six Samurai - Shi En',
'Trishula, Dragon of the Ice barrier',
'Allure of Darkness',
'Black Whirlwind',
'Burial from a Different Dimension',
'Card Destruction',
'Charge of the Light Brigade',
'Dark Hole',
'Emergency Teleport',
'Foolish Burial',
'Future Fusion',
'Gateway of the Six',
'Heavy Storm',
'Infernity Launcher',
'Level Limit - Area B',
'Limiter Removal',
'Mind Control',
'Monster Gate',
'Monster Reborn',
'One for One',
'Pot of Avarice',
'Primal Seed',
'Reasoning',
'Reinforcement of the Army',
'Scapegoat',
'Shien\'s Smoke Signal',
'Ceasefire',
'Magical Explosion',
'Mirror Force',
'Return from the Different Dimension',
'Solemn Judgment',
'The Transmigration Prophecy',
'Torrential Tribute',
'Wall of Revealing Light',
]         
SEMI = [ # Cards to mark as Semi-Limited (2 copies)
    "Lonefire Blossom",
    "Dandylion",
    'Blackwing - Kalut the Moon Shadow',
    'Honest',
    'Archlord Kristya',
    'Card Trooper',
    'Destiny Hero - Malicious',
    'Necro Gardna',
    'Summoner Monk',
    'Tragoedia',
    'Dewloren, Tiger King of the Ice Barrier',
    'Chain Strike',
    'Destiny Draw',
    'Magical Stone Excavation',
    'Royal Tribute',
    'Swords of Revealing Light',
    'Bottomless Trap Hole',
    'Call of the Haunted',
    'Magic Cylinder',
    'Mind Crush',
    'Ojama Trio',
    'Solemn Warning',
]            

from otn_enhanced.rom.ydc_codec import card_name_to_konami_id

def name_to_cid(name: str) -> int:
    """Convert a card name to its Konami ID (CID).

    Raises KeyError if the name is not found.
    """
    cid = card_name_to_konami_id(name)
    if cid is None:
        raise KeyError(name)
    return cid

BANNED = [name_to_cid(name) for name in BANNED]
LIMITED = [name_to_cid(name) for name in LIMITED]
SEMI = [name_to_cid(name) for name in SEMI]

# ── Implementation ─────────────────────────────────────────────────


def find_limit_file_in_pac(archive) -> tuple[int, str] | None:
    """Find the limit*.bin file in a PAC archive.
    
    Returns: (file_index, filename) or None if not found.
    """
    for idx, file in enumerate(archive.files):
        clean_name = file.get_clean_name()
        if clean_name.lower().startswith("limit2010") and clean_name.lower().endswith(".bin"):
            return idx, clean_name
    return None




def find_bin_pac_in_rom(rom: ndspy.rom.NintendoDSRom) -> str | None:
    """Find bin.pac or bin2.pac file in ROM.
    
    Returns: file path (e.g. "/data/bin.pac") or None if not found.
    """
    pac_path = next((p for p in iter_paths(rom.filenames) if p.lower().endswith("bin.pac")), None)
    return pac_path


def patch_banlist(src, out) -> None:
    """Load ROM, modify banlist, and save result."""
    
    # 1. Load ROM
    logger.info("Loading ROM from %s", src)
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    
    # 2. Find bin.pac or bin2.pac
    bin_pac_path = find_bin_pac_in_rom(rom)
    fid = rom.filenames.idOf(bin_pac_path)
    pac_data = bytes(rom.files[fid])
    logger.info("Found %s in ROM", bin_pac_path)
    archive = parse_pac(pac_data, bin_pac_path)
    logger.info("Parsed %s: %d files", bin_pac_path, len(archive.files))
    
    # 4. Find limit file
    limit_result = find_limit_file_in_pac(archive)
    if not limit_result:
        raise RuntimeError("Could not find limit*.bin file in PAC")
    
    limit_idx, limit_name = limit_result
    limit_file = archive.files[limit_idx]
    logger.info("Found limit file: %s (idx=%d, size=%d)", limit_name, limit_idx, limit_file.size)
    
    # 5. Extract and decode limit file
    limit_bytes = pac_data[limit_file.address : limit_file.address + limit_file.size]
    limit_json, limit_meta = decode_limit(limit_bytes)
    limit_data = json.loads(limit_json)
    
    logger.info("Current banlist:")
    logger.info("  Forbidden: %d", len(limit_data.get("Forbidden", [])))
    logger.info("  Limited: %d", len(limit_data.get("Limited", [])))
    logger.info("  Semi-Limited: %d", len(limit_data.get("Semi-Limited", [])))
    
    # 6. Apply modifications
    logger.info("Applying modifications...")
    logger.info("  Banning: %s", BANNED)
    logger.info("  Limiting: %s", LIMITED)
    logger.info("  Semi-limiting: %s", SEMI)
    
    # Remove cards from all lists first (in case they're moving between categories)
    all_to_modify = set(BANNED) | set(LIMITED) | set(SEMI)
    for category in ["Forbidden", "Limited", "Semi-Limited"]:
        limit_data[category] = [c for c in limit_data.get(category, []) if c not in all_to_modify]
    
    # Add cards to their new categories
    limit_data["Forbidden"] = BANNED
    limit_data["Limited"] = LIMITED
    limit_data["Semi-Limited"] = SEMI
    
    # Remove duplicates and sort
    limit_data["Forbidden"] = sorted(set(limit_data["Forbidden"]))
    limit_data["Limited"] = sorted(set(limit_data["Limited"]))
    limit_data["Semi-Limited"] = sorted(set(limit_data["Semi-Limited"]))
    
    logger.info("Modified banlist:")
    logger.info("  Forbidden: %d", len(limit_data.get("Forbidden", [])))
    logger.info("  Limited: %d", len(limit_data.get("Limited", [])))
    logger.info("  Semi-Limited: %d", len(limit_data.get("Semi-Limited", [])))
    
    # 7. Encode back
    modified_limit_json = json.dumps(limit_data, ensure_ascii=False, indent=2)
    replacement_bytes = encode_limit(modified_limit_json, limit_meta)
    
    logger.info("Encoded limit file: %d bytes (was %d)", len(replacement_bytes), limit_file.size)
    
    # 8. Replace in PAC (with repacking if size changed)
    modified_pac_bytes: bytes
    
    if len(replacement_bytes) == limit_file.size:
        # In-place replacement: same size
        modified_pac = bytearray(pac_data)
        modified_pac[limit_file.address : limit_file.address + limit_file.size] = replacement_bytes
        modified_pac_bytes = bytes(modified_pac)
        logger.info("Applied in-place replacement (same size)")
    else:
        # Full repack: size changed
        logger.info("Size changed, repacking PAC...")
        
        with tempfile.TemporaryDirectory(prefix="banlist_patch_") as tmp_dir:
            tmp_root = Path(tmp_dir)
            input_dir = tmp_root / "input"
            input_dir.mkdir(parents=True, exist_ok=True)
            
            original_pac_path = tmp_root / "original.pac"
            output_pac_path = tmp_root / "output.pac"
            original_pac_path.write_bytes(pac_data)
            
            # Extract all files from PAC
            for pac_file in archive.files:
                clean_name = pac_file.get_clean_name()
                entry_bytes = pac_data[pac_file.address : pac_file.address + pac_file.size]
                
                # Replace limit file with modified version
                if clean_name == limit_name:
                    entry_bytes = replacement_bytes
                
                (input_dir / clean_name).write_bytes(entry_bytes)
            
            # Repack PAC
            repack_result = repack_pac(str(input_dir), str(original_pac_path), str(output_pac_path))
            if repack_result != 0:
                raise RuntimeError(f"repack_pac failed with exit code {repack_result}")
            
            modified_pac_bytes = output_pac_path.read_bytes()
            logger.info("PAC repacked: %d bytes (was %d)", len(modified_pac_bytes), len(pac_data))
    
    # 9. Replace PAC in ROM
    rom.files[fid] = modified_pac_bytes
    
    # 10. Save modified ROM
    logger.info("Saving modified ROM to %s", out)
    modified_rom_bytes = rom.save()
    Path(out).write_bytes(modified_rom_bytes)
    logger.info("Done! Modified ROM saved to %s", out)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    patch_banlist(src = SRC, out = OUT)
