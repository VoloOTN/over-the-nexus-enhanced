"""Deck DISPLAY name reader/writer for CPU and story opponents.

Deck names ("Dingy Daredevil", "My Almighty Legend", ...) resolve the same
way duelist names do (pack_unlock_conditions.py:304-321): duelist id ->
arm9 u16[] table -> game_indx_e.bin (u32 offset) -> null-terminated ASCII in
game_text_e.bin, both inside Data_arc_pac/bin2.pac. See
notes/deck-name-findings.md and docs/engine/deck_names.yaml for the
reverse-engineering write-up (id range, table boundary, resolver function).

Edit CHANGES below ({duelist_id: "New Name"}) and run::

    python -m otn_enhanced.system.deck_names

A rename that fits within the original name's byte budget (the gap up to
the next 4-byte-aligned boundary) is patched in place. A longer name is
appended to the end of game_text_e.bin and only its one index entry is
repointed -- no other string in the file moves.
"""
from __future__ import annotations

import shutil
import struct
from pathlib import Path

import ndspy.code
import ndspy.rom

from otn_enhanced.rom.pac import build_modified_pac, parse_pac

SRC = "data/over_the_nexus/working/rom.nds"
OUT = "data/over_the_nexus/working/rom_deck_names.nds"

# arm9 u16[]: duelist id -> game-text id. docs/engine/deck_names.yaml
# (deck_names.table_base, VERIFIED). Same id space as duelist names: ids 0/1
# are the player ("You", text-id 0 -- not a real deck, don't target these),
# ids 0x02-0x70 are the story roster, 0x71-0xAC the 60-strong CPU-duel
# roster, and further ids continue into later rosters (confirmed valid
# through ~0xFC).
DECK_NAME_TABLE = 0x020AA5D8
from otn_enhanced.effects.common import ARM9_BASE

BIN2_PAC = "Data_arc_pac/bin2.pac"
INDX_NAME = "game_indx_e.bin"
TEXT_NAME = "game_text_e.bin"

CHANGES: dict[int, str] = {
    # Prefilled with every current deck name (ids 0x02-0xFC: story roster,
    # the 60-strong CPU-duel roster 0x71-0xAC, and further rosters beyond it).
    # All commented out -- edit a value and uncomment its line to rename it;
    # leave the rest alone.
    # -- story roster ----------------------------
    # 0x02: "Bug Stampede",
    # 0x03: "Tetsu's Justice",
    # 0x04: "Ex-Champion's Glory",
    # 0x05: "The Facility",
    # 0x06: "Burning Speed",
    # 0x07: "Firebomber",
    # 0x08: "Masterful Magician",
    # 0x09: "Boneyard Battle",
    # 0x0a: "The Sea's Torment",
    # 0x0b: "Cc: Sea Hunter",
    # 0x0c: "Blister's Machiners",
    # 0x0d: "Knight's Oath",
    # 0x0e: "Dandy Deck",
    # 0x0f: "Chums of Dark World",
    # 0x10: "Today's Guard",
    # 0x11: "Remove from Fray",
    # 0x12: "Want a Star?",
    # 0x13: "Auction Price!",
    # 0x14: "Classic Deck",
    # 0x15: "Duel Catenaccio",
    # 0x16: "Colorful Jurrac",
    # 0x17: "Picture Musketeers",
    # 0x18: "Endymion's Award",
    # 0x19: "Where's the Arcana?",
    # 0x1a: "Iranami's Temptation",
    # 0x1b: "Growing Up!",
    # 0x1c: "Arcana Presence",
    # 0x1d: "Gladiators Award",
    # 0x1e: "The Samurai",
    # 0x1f: "MA-SA-KI",
    # 0x20: "Fight! Impact!",
    # 0x21: "Ida Dragons",
    # 0x22: "Lucky Turtle Shell",
    # 0x23: "The Prime Dragons",
    # 0x24: "Fresh Catch",
    # 0x25: "Unimpeded Fruit",
    # 0x26: "Fermentation",
    # 0x27: "Bass/Assault Mode",
    # 0x28: "Underground Darkness",
    # 0x29: "Modern Deck",
    # 0x2a: "Fallen Light",
    # 0x2b: "Court Jester",
    # 0x2c: "Earth's New Light",
    # 0x2d: "Fortunetelling",
    # 0x2e: "The Enforcing Ones",
    # 0x2f: "Richard's Gishki",
    # 0x30: "Wasteland Blokes",
    # 0x31: "Lion King's Pride",
    # 0x32: "Wandering Naturia",
    # 0x33: "Rallying Warriors",
    # 0x34: "Dragons' Lair",
    # 0x35: "Ascending Legend",
    # 0x36: "Angel Inside",
    # 0x37: "Queen of Roses",
    # 0x38: "Feel the Wind",
    # 0x39: "Gotham World",
    # 0x3a: "Legendary Magician",
    # 0x3b: "Nurse's Medicine",
    # 0x3c: "Thrilling Twin Attack",
    # 0x3d: "Bending Willow",
    # 0x3e: "Forsaken Light",
    # 0x3f: "My Eyes are Clear",
    # 0x40: "Scrap Garage",
    # 0x41: "Thanks, Scrap",
    # 0x42: "Electrikiss",
    # 0x43: "Electrikiss Plus",
    # 0x44: "Awakened Mind",
    # 0x45: "Full-Steam Synchro",
    # 0x46: "Burning Inferno",
    # 0x47: "Speeding Inferno",
    # 0x48: "Red Fiend's Roar",
    # 0x49: "Rise, Black-wing!",
    # 0x4a: "Driven on Blackwing",
    # 0x4b: "Meklord Ruler",
    # 0x4c: "Sky Meklord",
    # 0x4d: "Land Meklord",
    # 0x4e: "Master of Demise",
    # 0x4f: "Flower of Vengeance",
    # 0x50: "Chivalric Keeper",
    # 0x51: "Treasure Digger",
    # 0x52: "The Secret of X",
    # 0x53: "Combat Realist",
    # 0x54: "Nasty Cyber Lady",
    # 0x55: "My Almighty Legend",
    # 0x56: "Pretty & Prettier",
    # 0x57: "Dad's Revolver",
    # 0x58: "One Horn, One Strike",
    # 0x59: "Card-piercing Bihorn",
    # 0x5a: "Call of the Trihorn",
    # 0x5b: "Nightmare Clown",
    # 0x5c: "Karakuri Squared",
    # 0x5d: "Stealth Blaster",
    # 0x5e: "Odin's Spear",
    # 0x5f: "Thor's Hammer",
    # 0x60: "Loki's Tricks",
    # 0x61: "Fresh Blue-Eyes",
    # 0x62: "Angel's Bitter Dart",
    # 0x63: "Sparking Flint",
    # 0x64: "Rotten Recycler",
    # 0x65: "Bone Destroyer",
    # 0x66: "Minegishi: Scorpio",
    # 0x67: "Silent Swordsman",
    # 0x68: "Laval Lover",
    # 0x69: "Lock 'n' Burn X",
    # 0x6a: "Equipped! Click!",
    # 0x6b: "Inverse Order",
    # 0x6c: "Tyrant's Reign",
    # 0x6d: "Breaking Wheel",
    # 0x6e: "Hidden Feelings",
    # 0x6f: "GHOST-01",
    # 0x70: "GHOST-02",
    # -- CPU-duel roster -------------------------
    0x71: "Hidden Beasts",
    # 0x72: "Tomato Alliance",
    # 0x73: "Hip Hypnocorn",
    # 0x74: "Organic Cherries",
    # 0x75: "Watt's Up?",
    # 0x76: "Statues: Standby",
    # 0x77: "Laval-Pattern Burn",
    # 0x78: "Ritua Poor",
    # 0x79: "Accelerating Genex",
    # 0x7a: "Sparkling Knights",
    # 0x7b: "Unicorn Grit",
    # 0x7c: "Me Gusto",
    # 0x7d: "Masked Hero",
    # 0x7e: "Wonderful Wanghu",
    # 0x7f: "Skull Savant",
    # 0x80: "Amazoness Law",
    # 0x81: "Reptilian Wrecker",
    # 0x82: "I am the Great Maju!",
    # 0x83: "Karakuri Kamikaze",
    # 0x84: "Manly Burrower",
    # 0x85: "Plateful of Monsters",
    # 0x86: "Supple Beats Strong",
    # 0x87: "Swamp Concert",
    # 0x88: "Mega Omega",
    # 0x89: "Bamboo Shoot Forest",
    # 0x8a: "Watt Killers",
    # 0x8b: "Cry of the Fabled",
    # 0x8c: "A Worm Feeling",
    # 0x8d: "Feeling Koa'ki",
    # 0x8e: "Graveyard Closed!",
    # 0x8f: "Herald Generation",
    # 0x90: "True Flame Backdraft",
    # 0x91: "Ruin & Renewal",
    # 0x92: "Unbound Immortal",
    # 0x93: "Steelswarm Space",
    # 0x94: "Diva of the Dead",
    # 0x95: "Galaxy Master",
    # 0x96: "Vidi! Geri! Vici!",
    # 0x97: "Assault Academy",
    # 0x98: "Mist Vale Blackwings",
    # 0x99: "Gemini of Light",
    # 0x9a: "Counter Angel",
    # 0x9b: "Such a Fallen Angel",
    # 0x9c: "Meklord Summon Works",
    # 0x9d: "Archangel's Advent",
    # 0x9e: "Gaia Impact",
    # 0x9f: "Dimensional Love",
    # 0xa0: "Frog Kaiser",
    # 0xa1: "Gladiator Gradation",
    # 0xa2: "X-Soul Successor",
    # 0xa3: "Infinite Inferno",
    # 0xa4: "Hunk of Junk",
    # 0xa5: "Malefic Planet",
    # 0xa6: "Ehren There",
    # 0xa7: "Dragon-Riding Beasts",
    # 0xa8: "Time of Heroes",
    # 0xa9: "Dr. RED, M.D.",
    # 0xaa: "Blackwing Elite",
    # 0xab: "Six Samurai Spirits",
    # 0xac: "Mobile Cog Fortress",
    # -- further roster (unconfirmed which mode) -
    # 0xad: "Echoing Defender",
    # 0xae: "Echoing Builder",
    # 0xaf: "Magic Shallow Eon",
    # 0xb0: "Shallow Eon",
    # 0xb1: "Ya Shan't Pass",
    # 0xb2: "Gundari Us",
    # 0xb3: "Dark Miasma",
    # 0xb4: "Dark Boreas",
    # 0xb5: "The Spoils of Spore",
    # 0xb6: "Wat a Ponisher",
    # 0xb7: "Bisque's Revenge",
    # 0xb8: "Go, Chopper!",
    # 0xb9: "No Spells! No Traps!",
    # 0xba: "No Monsters At All!",
    # 0xbb: "Burn Princess",
    # 0xbc: "Adverse Reaction",
    # 0xbd: "Stargazing Beast",
    # 0xbe: "Scarecrow-Magnon",
    # 0xbf: "Golden Archfiend",
    # 0xc0: "Salmon Max",
    # 0xc1: "Alien Nation",
    # 0xc2: "After-School Snake",
    # 0xc3: "Sink Crow",
    # 0xc4: "Just Tuners",
    # 0xc5: "Spirit of Duty",
    # 0xc6: "Ancestral Dignity",
    # 0xc7: "Artists of War",
    # 0xc8: "Sudden Dance",
    # 0xc9: "Undersea Ceremony",
    # 0xca: "Final Ceremony",
    # 0xcb: "Knight of Gems",
    # 0xcc: "Lightspeed Prisma",
    # 0xcd: "Blackwing Assassin",
    # 0xce: "I Mist You, Baby",
    # 0xcf: "Resolute Returner",
    # 0xd0: "Recon Complete",
    # 0xd1: "Fountain of Crystal",
    # 0xd2: "Fountain of Tragedy",
    # 0xd3: "Solar Guidance",
    # 0xd4: "Lunar Guidance",
    # 0xd5: "Aile Be Back",
    # 0xd6: "Dragon Dash",
    # 0xd7: "Runway Train",
    # 0xd8: "Psychic Sidekick",
    # 0xd9: "Naturunner",
    # 0xda: "Skel's Angels",
    # 0xdb: "Mefast Mefist",
    # 0xdc: "Dragon Racer",
    # 0xdd: "Sigmax Speed",
    # 0xde: "In Justice's Name",
    # 0xdf: "Vile Deeds",
    # 0xe0: "Dashing Dasher",
    # 0xe1: "Gaia's Sunrise",
    # 0xe2: "Fissile Fossil",
    # 0xe3: "Dragunity Storm",
    # 0xe4: "Full Throttle!",
    # 0xe5: "Nazca Liner",
    # 0xe6: "Lightsworn Runner",
    # 0xe7: "Superspeed Fortress",
    # 0xe8: "Transcendental Evil",
    # 0xe9: "Let's Go Cycling!",
    # 0xea: "Monster School",
    # 0xeb: "Mach Quacker",
    # 0xec: "Highway Sprinter",
    # 0xed: "Rush! Charge! Blitz!",
    # 0xee: "Bull Fighter!",
    # 0xef: "Gila Monster",
    # 0xf0: "Hamster Strike!",
    # 0xf1: "Wave Runner",
    # 0xf2: "Shark Attack",
    # 0xf3: "Wild Rider",
    # 0xf4: "Berserk Rider",
    # 0xf5: "Maximum Security",
    # 0xf6: "On the Beat",
    # 0xf7: "Nightmare Hunter",
    # 0xf8: "Soaring Dark Dragon",
    # 0xf9: "Mist Valley Squadron",
    # 0xfa: "Blackwing Squadron",
    # 0xfb: "Speedy Delivery",
    # 0xfc: "Heavy-Hitting Hero",
}


def _arm9(rom: ndspy.rom.NintendoDSRom) -> bytes:
    mc = ndspy.code.MainCodeFile(bytes(rom.arm9), rom.arm9RamAddress)
    return bytes(mc.sections[0].data)


def _text_id(arm9: bytes, duelist_id: int) -> int:
    off = DECK_NAME_TABLE - ARM9_BASE + duelist_id * 2
    return struct.unpack_from("<H", arm9, off)[0]


def _bin2_files(rom: ndspy.rom.NintendoDSRom):
    blob = bytes(rom.getFileByName(BIN2_PAC))
    archive = parse_pac(blob, BIN2_PAC)
    by_name = {f.get_clean_name(): i for i, f in enumerate(archive.files)}
    return blob, archive, by_name


def deck_name(rom_path: str | Path, duelist_id: int) -> str:
    """Read the current deck name for *duelist_id* out of *rom_path*."""
    rom = ndspy.rom.NintendoDSRom.fromFile(str(rom_path))
    text_id = _text_id(_arm9(rom), duelist_id)
    blob, archive, by_name = _bin2_files(rom)
    idx_f = archive.files[by_name[INDX_NAME]]
    txt_f = archive.files[by_name[TEXT_NAME]]
    idx = blob[idx_f.address:idx_f.address + idx_f.size]
    txt = blob[txt_f.address:txt_f.address + txt_f.size]
    off = struct.unpack_from("<I", idx, text_id * 4)[0]
    return txt[off:txt.index(b"\x00", off)].decode("ascii")


def set_deck_names(changes: dict[int, str], *, src: str | Path = SRC, out: str | Path = OUT) -> None:
    if not changes:
        # Still produce *out*: keeps this module a drop-in step like the
        # other finished_patches, even with nothing to change.
        if str(src) != str(out):
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(src), str(out))
        print("  CHANGES is empty -- uncomment a duelist id in CHANGES to edit it")
        return

    rom = ndspy.rom.NintendoDSRom.fromFile(str(src))
    arm9 = _arm9(rom)
    blob, archive, by_name = _bin2_files(rom)
    indx_i, text_i = by_name[INDX_NAME], by_name[TEXT_NAME]
    idx_f, txt_f = archive.files[indx_i], archive.files[text_i]
    idx = bytearray(blob[idx_f.address:idx_f.address + idx_f.size])
    txt = bytearray(blob[txt_f.address:txt_f.address + txt_f.size])

    for duelist_id, new_name in changes.items():
        text_id = _text_id(arm9, duelist_id)
        if text_id == 0:
            raise ValueError(f"id {duelist_id:#x} has no deck name (text-id 0 -- "
                              f"likely the player slot, not a CPU/story opponent)")
        try:
            new_bytes = new_name.encode("ascii") + b"\x00"
        except UnicodeEncodeError as e:
            raise ValueError(f"id {duelist_id:#x}: name must be ASCII: {new_name!r}") from e

        off = struct.unpack_from("<I", idx, text_id * 4)[0]
        end = txt.index(b"\x00", off)
        budget = ((end + 1 + 3) // 4) * 4 - off  # gap up to the next 4-byte boundary

        if len(new_bytes) <= budget:
            txt[off:off + len(new_bytes)] = new_bytes
            print(f"  id {duelist_id:#x}: in-place ({len(new_bytes)}/{budget} bytes)")
        else:
            padded = new_bytes + b"\x00" * (-len(new_bytes) % 4)
            new_off = len(txt)
            txt.extend(padded)
            struct.pack_into("<I", idx, text_id * 4, new_off)
            print(f"  id {duelist_id:#x}: appended at {new_off:#x} "
                  f"({len(new_bytes)} bytes, {budget}-byte in-place budget was too small)")

    new_bin2 = build_modified_pac(blob, BIN2_PAC, {indx_i: bytes(idx), text_i: bytes(txt)})
    rom.setFileByName(BIN2_PAC, new_bin2)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rom.saveToFile(str(out))
    print(f"  wrote {out}")


def main(src: str = SRC, out: str = OUT, *, write_text=None) -> None:
    del write_text  # accepted for apply-all-patches uniformity
    set_deck_names(CHANGES, src=src, out=out)


def verify(*, out: str | Path = OUT) -> bool:
    if not CHANGES:
        return True
    ok = True
    for duelist_id, expected in CHANGES.items():
        got = deck_name(out, duelist_id)
        good = got == expected
        ok &= good
        print(f"  [{'OK ' if good else 'BAD'}] id {duelist_id:#x}: {got!r} (expected {expected!r})")
    return ok


if __name__ == "__main__":
    main()
    verify()
