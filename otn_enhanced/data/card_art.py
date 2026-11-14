"""Card-art replacement for the four converted cards (single, self-contained patch).

This patch swaps the ON-DISK ARTWORK of each donor card so its pictures match the
card it was turned into by the effect patches. It edits the two card.pac image
stores per card and leaves everything else (effects, stats, text) untouched, so it
stacks cleanly as the LAST step of ``apply_all_patches`` (the effect patches never
touch card.pac, so all art offsets are stable).

  Donor (kept cid)          becomes                 art folder
    Vampire Orchis  0x15D4 -> XX-Saber Boggart Knight  boggart knight
    Gigobyte        0x1783 -> XX-Saber Darksoul         darksoul
    Portrait's Secret 0x1463 -> Reborn Tengu            reborn tengu
    Ancient Gear C. 0x19BB -> Mystic Piper              mystic piper

Two stores per card (see card_art_codec for the NTBG formats):
  1. card.pac file3  64x64 cropped art  -> in-place 2820-byte splice (fixed stride).
  2. card.pac file1  32x32 full card    -> file1 + index-table + header REBUILD
        (the detailed art compresses larger than the stock thumbnail, so the LZ10
        stream cannot be spliced in place; card.pac grows by one 0x200 block).

The atlas index for each card is found from card_prop.bin by its (kept) cid, so
this works on the clean ROM or on top of the effect patches identically.

(The 256x96 2D battle sprite was previously also swapped, but that splice did not
work in-game and has been removed; the BattleMonster pacs are left untouched.)

Usage:
    python -m otn_enhanced.data.card_art
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import ndspy.rom
from PIL import Image

from otn_enhanced.rom.lz_compression import compress, decompress
from otn_enhanced.rom.lz5bg_codec import _parse_ntbg_sections, _parse_palette
from otn_enhanced.rom.pac import parse_format_v1
from otn_enhanced.rom.card_art_codec import encode_card_art_64x64, encode_card_thumb_32x32

# ---------------------------------------------------------------------------
# Paths and the card table
# ---------------------------------------------------------------------------
SRC = "data/over_the_nexus/working/rom.nds"               # clean base ROM (never modified in place)
OUT = "data/over_the_nexus/working/rom_cardart.nds"       # standalone output (orchestrator overrides this)
ART_ROOT = Path("data/over_the_nexus/card_arts/implemented")          # the prepared PNG art per card

CARD_PAC = "Data_arc_pac/card.pac"
BIN2_PAC = "Data_arc_pac/bin2.pac"

# card.pac internal file table — byte offsets are RELATIVE to the 0x200 data base
# (the filename header is not 4-aligned, so these land on odd addresses).
H_F1SIZE, H_F2START, H_F2SIZE, H_F3START, H_F3SIZE = 0x4D, 0x51, 0x55, 0x59, 0x5D
DATA_BASE = 0x200
ART64_STRIDE = 2820          # every 64x64 atlas image is exactly this many bytes


class CardArt:
    """One card's art job: cid and PNG basename."""

    def __init__(self, cid: int, folder: str, base: str):
        self.cid = cid
        self.folder = folder
        self.base = base

    def png(self, suffix: str) -> Path:
        return ART_ROOT / self.folder / f"{self.base}_{suffix}.png"


CARDS: list[CardArt] = [
    CardArt(0x13A5, "boggart knight",         "XX-Saber_Boggart_Knight"),
    CardArt(0x1783, "darksoul",               "XX-Saber_Darksoul"),
    CardArt(0x1463, "reborn tengu",           "Reborn_Tengu"),
    CardArt(0x13B8, "mystic piper",           "Mystic_Piper"),
    CardArt(0x0FD3, "wattcobra",              "Wattcobra"),
    CardArt(0x0FC2, "tour_guide",             "Tour_Guide"),
    CardArt(0xFD8,  "metal arm bug",          "Metal_Armored_Bug"),
    CardArt(0x0FFD, "ninishi",                "Ninishi"),
    CardArt(0x0FEC, "seahorse",               "seahorse"),
    CardArt(0x11B7, 'eldersix',               'eldersix'),
    CardArt(0x1F18, 'striker',                'striker'),
    CardArt(0x0FA9, 'warwolf',                'warwolf'),
    CardArt(0x22E6, 'rush_rhino',             'rush_rhino'), # Effect Monster
    CardArt(0x1315, 'meteorite',              'meteorite'),
    CardArt(0x1FFC, 'sea_lancer',             'sea_lancer'), # Effect Monster
    CardArt(0x16A2, 'safe_zone',              'safe_zone'),
    CardArt(0x1225, 'librarian',              'librarian'), # Consumes Synchro (re-donor; was 0x2338)
    CardArt(0x211B, 'quasar',                 'quasar'), # Consumes Synchro
    CardArt(0x1C08, 'escuridao',              'escuridao'), # Consume non-effect
    CardArt(0x0FB1, 'lightpulsar',            'lightpulsar'),
    CardArt(0x1859, 'eclipse_wyvern',         'eclipse_wyvern'),
    CardArt(0x19B2, 'shiens_dojo',            'shiens_dojo'),
    CardArt(0x1E9C, 'azure_eyes',             'azure_eyes'), # Consumes Synchro
    CardArt(0x0FB4, 'gravekeepers recruiter', 'Gravekeepers_Recruiter'),
    CardArt(0x1DDD, 'infernity barrier',      'Infernity_Barrier'),
    CardArt(0x1B3E, 'ceruli',                 'ceruli'),
    CardArt(0x1646, 'darkflare',              'darkflare'),
    CardArt(0x12B2, 'dragon_ninja',           'dragon_ninja'),   # Change Base.
    CardArt(0x14C1, 'dragon_shrine',          'dragon_shrine'),
    CardArt(0x1C18, 'snoww',                  'snoww'),
    CardArt(0x1961, 'grapha',                 'grapha'),
    CardArt(0x1C8B, 'gates',                  'gates'),
    CardArt(0x0FC8, 'haipa',                  'haipa'),
    CardArt(0x13E7, 'hanzo',                  'hanzo'),
    CardArt(0x2124, 'heirloom',               'heirloom'),
    CardArt(0x1ED7, 'maiden',                 'maiden'),
    CardArt(0x1126, 'meiru_wall',             'meiru__wall'),
    CardArt(0x1465, 'naturia_pineapple',      'naturia_pineapple'),
    CardArt(0x0FCB, 'orient_dragon',          'orient_dragon'),
    CardArt(0x13C6, 'scrap_archfiend',        'scrap_archfiend'),
    CardArt(0x1255, 'super_transformation',   'super_transformation'),
    CardArt(0x1464, 'upstart_ninja',          'upstart_ninja'),
    CardArt(0x1008, 'psi_reflector',          'psi_reflector'),
    CardArt(0x224C, 'jet_synchron',           'jet_synchron'),
    CardArt(0x17CE, 'junk_servant',           'junk_servant'), # Change Base
    CardArt(0x120B, 'junk_speeder',           'junk_speeder'),
    CardArt(0x181C, 'unknown_synchron',       'unknown_synchron'),
    CardArt(0x11A3, 'accel_synchron',         'accel_synchron'),
    CardArt(0x107F, 'coral_dragon',           'coral_dragon'),   # Coral Dragon on B. Skull Dragon (shipped; art was prepared but never registered -- added 2026-11-12 on the user's request)
    # The Monarch set (shipped 2026-11-12, steps.py). Art lives in card_arts/<slug>/ (NOT implemented/), hence the "../" folders.
    *[CardArt(cid, "../" + slug, slug) for cid, slug in (
        (0x0FD7, "granmarg_the_mega_monarch"), (0x0FF3, "mobius_the_mega_monarch"), (0x139B, "zaborg_the_mega_monarch"), (0x1E87, "raiza_the_mega_monarch"),
        (0x0FC5, "caius_the_mega_monarch"), (0x127B, "thestalos_the_mega_monarch"), (0x14D8, "angmarl_the_fiendish_monarch"), (0x1313, "erebus_the_underworld_monarch"),
        (0x1312, "ehther_the_heavenly_monarch"), (0x1230, "eidos_the_underworld_monarch"), (0x0FDC, "edea_the_heavenly_squire"), (0x1123, "tessera_the_primal_squire"),
        (0x0FE2, "eidos_the_underworld_squire"), (0x15EC, "march_of_the_monarchs"), (0x1328, "the_monarchs_stormforth"), (0x12EB, "tenacity_of_the_monarchs"),
        (0x14A1, "return_of_the_monarchs"), (0x12EE, "restoration_of_the_monarchs"), (0x1633, "the_monarchs_awaken"), (0x1923, "pantheism_of_the_monarchs"),
        (0x14C3, "frost_blast_of_the_monarchs"), (0x1DCD, "the_monarchs_revolt"), (0x0D6A, "the_monarchs_masterplan"), (0x0DE4, "strike_of_the_monarchs"),
        (0x10F3, "domain_of_the_true_monarchs"), (0x135E, "the_monarchs_erupt"), (0x1800, "escalation_of_the_monarchs"), (0x14CF, "the_prime_monarch"),
        (0x249B, "the_first_monarch"), (0x12F6, "monarchic_perfection"))],
    CardArt(0x12B6, 'steam_synchron',         'steam_synchron'), # Change Base.
    CardArt(0x23EB, 'jet_warrior',            'jet_warrior'), # Change Base.
    CardArt(0x0FAE, 'cardcar',                'cardcar'),
    CardArt(0x0FD5, 'kuribandit',             'kuribandit'),
    CardArt(0x123D, 'soul_charge',            'soul_charge'),
    CardArt(0x13B6, 'mathematician',          'mathematician'),
    CardArt(0x126F, 'accel_synchro',          'accel_synchro'),
    CardArt(0x13AE, 'assault_synchron',       'assault_synchron'),
    CardArt(0x1649, 'revolution_synchron',    'revolution_synchron'),
    CardArt(0x106E, 'dragunity_remus',        'dragunity_remus'),
    CardArt(0x1179, 'crimson_blader',         'crimson_blader'),
    CardArt(0x0FE1, 'petiteranodon',          'petiteranodon'),
    CardArt(0x0FF2, 'miscellaneousaurus',     'miscellaneousaurus'),
    CardArt(0x0FC6, 'souleating_oviraptor',   'souleating_oviraptor'),
    CardArt(0x0FF6, 'scrap_raptor',           'scrap_raptor'),
    CardArt(0x1297, 'archosaur',  'archosaur'),
    CardArt(0x21D5, 'brilliant_fusion',       'brilliant_fusion'),
    CardArt(0x1160, 'masked_hero_dark_law',   'masked_hero_dark_law'),
    CardArt(0x1127, 'elder_entity_norden',     'elder_entity_norden'),
    CardArt(0x111F, 'elemental_hero_shadow_mist', 'elemental_hero_shadow_mist'),
    CardArt(0x1319, 'evo_pill',                'evo_pill'),
    CardArt(0x18FA, 'life_stream',            'life_stream'),
    CardArt(0x170F, 'ojamassimilation',        'ojamassimilation'),
    CardArt(0x10A5, 'overtex_qoatlus',          'overtex_qoatlus'),
    CardArt(0x1265, 'uct',                     'uct'),
    CardArt(0x0FD2, 'raiden_hand_of_the_lightsworn', 'raiden_hand_of_the_lightsworn'),
    CardArt(0x10FD, 'that_grass_looks_greener', 'that_grass_looks_greener'),
    CardArt(0x10F5, 'the_seal_of_orichalcos', 'the_seal_of_orichalcos'),
    CardArt(0x17F4, 'obedience_schooled', 'obedience_schooled'),
    CardArt(0x160A, 'eva', 'eva'),
    CardArt(0x106C, 'mara', 'mara'),
    CardArt(0x1050, 'wattuna', 'wattuna'),
    CardArt(0x1458, 'wattkyuki', 'wattkyuki'),
    CardArt(0x13AC, 'aratama', 'aratama'),
    CardArt(0x1110, 'grandsoil', 'grandsoil'),
    CardArt(0x1C1A, 'moulinglacia_the_elemental_lord', 'moulinglacia_the_elemental_lord'),
    CardArt(0x1106, 'neo_space_connector', 'neo_space_connector'),
    CardArt(0x0FE3, 'nikitama', 'nikitama'),
    CardArt(0x181F, 'pyrorex_the_elemental_lord', 'pyrorex_the_elemental_lord'),
    CardArt(0x13E5, 'sakitama', 'sakitama'),
    CardArt(0x190B, 'windrose_the_elemental_lord', 'windrose_the_elemental_lord'),
    CardArt(0x0FD0, 'uni_zombie', 'uni_zombie'),
    CardArt(0x1B22, 'next', 'next'),                                                          # Return Soul -> NEXT
    CardArt(0x17CD, 'redox_dragon_ruler_of_boulders', 'redox_dragon_ruler_of_boulders'),       # Charcoal Inpachi
    CardArt(0x115F, 'tidal_dragon_ruler_of_waterfalls', 'tidal_dragon_ruler_of_waterfalls'),   # Mech Bass
    CardArt(0x1145, 'blaster_dragon_ruler_of_infernos', 'blaster_dragon_ruler_of_infernos'),   # Mechanicalchaser
    CardArt(0x1125, 'tempest_dragon_ruler_of_storms', 'tempest_dragon_ruler_of_storms'),       # Parrot Dragon
    CardArt(0x0FF4, 'reactan_dragon_ruler_of_pebbles', 'reactan_dragon_ruler_of_pebbles'),     # Axe Raider
    CardArt(0x115E, 'stream_dragon_ruler_of_droplets', 'stream_dragon_ruler_of_droplets'),     # 7 Colored Fish
    CardArt(0x0FEA, 'burner_dragon_ruler_of_sparks', 'burner_dragon_ruler_of_sparks'),         # Garoozis
    CardArt(0x1CC6, 'lightning_dragon_ruler_of_drafts', 'lightning_dragon_ruler_of_drafts'),   # Atlantean Pikeman
    CardArt(0x0FE8, 'denko_sekka', 'denko_sekka'),                                            # Kojikocy -> Denko Sekka
    CardArt(0x10E6, 'sekka_s_light', 'sekka_s_light'),                                        # Stop Defense -> Sekka's Light
    CardArt(0x1777, 'fire_formation_tenki', 'fire_formation_tenki'),                          # Marshmallon Glasses -> Fire Formation - Tenki
    CardArt(0x130A, 'sacred_sword_of_seven_stars', 'sacred_sword_of_seven_stars'),            # Block Attack -> Sacred Sword of Seven Stars
    CardArt(0x13A3, 'infernoble_knight_ogier', 'infernoble_knight_ogier'),
    CardArt(0x139A, 'infernoble_knight_maugis', 'infernoble_knight_maugis'),
    CardArt(0x1E04, 'infernoble_knight_oliver', 'infernoble_knight_oliver'),
    CardArt(0x0FC1, 'infernoble_knight_turpin', 'infernoble_knight_turpin'),
    CardArt(0x1E05, 'infernoble_knight_renaud', 'infernoble_knight_renaud'),
    CardArt(0x0FE6, 'infernoble_knight_ricciardetto', 'infernoble_knight_ricciardetto'),
    CardArt(0x0FDB, 'infernoble_knight_roland', 'infernoble_knight_roland'),
    CardArt(0x0FD4, 'infernoble_knight_astolfo', 'infernoble_knight_astolfo'),
    CardArt(0x160B, 'courageous_crimson_chevalier_bradamante', 'courageous_crimson_chevalier_bradamante'),
    CardArt(0x0FEB, 'infernoble_knight_captain_roland', 'infernoble_knight_captain_roland'),
    CardArt(0x1118, 'infernoble_knight_captain_oliver', 'infernoble_knight_captain_oliver'),
    CardArt(0x17EF, 'infernoble_knight_emperor_charles', 'infernoble_knight_emperor_charles'),
    CardArt(0x1002, 'angelica_princess_of_noble_arms', 'angelica_princess_of_noble_arms'),
    CardArt(0x1976, 'horn_of_olifant', 'horn_of_olifant'),
    CardArt(0x15E3, 'infernoble_arms_joyeuse', 'infernoble_arms_joyeuse'),
    CardArt(0x1663, 'infernoble_arms_durendal', 'infernoble_arms_durendal'),
    CardArt(0x1C39, 'infernoble_arms_almace', 'infernoble_arms_almace'),
    CardArt(0x1F71, 'infernoble_arms_hauteclere', 'infernoble_arms_hauteclere'),
    CardArt(0x1346, 'noble_arms_museum', 'noble_arms_museum'),                                # Molten Destruction -> Noble Arms Museum
    CardArt(0x16DB, 'the_continuing_epic_of_charles', 'the_continuing_epic_of_charles'),      # Big Burn -> The Continuing Epic of Charles
    CardArt(0x111E, 'disguise_the_copycat_hero', 'disguise_the_copycat_hero'),                # Monster Tamer -> Disguise, the Copycat Hero
    CardArt(0x10E3, 'cursed_copycat_noble_arms', 'cursed_copycat_noble_arms'),                # Cyber Shield -> Cursed Copycat Noble Arms
    CardArt(0x0FD9, 'noble_knight_medraut', 'noble_knight_medraut'),                          # Armored Lizard -> Noble Knight Medraut
    CardArt(0x0FC7, 'immortal_phoenix_gearfried', 'immortal_phoenix_gearfried'),              # Judge Man -> Immortal Phoenix Gearfried
    CardArt(0x10EA, 'phoenix_gearblade', 'phoenix_gearblade'),                                # Invigoration -> Phoenix Gearblade
    CardArt(0x0FED, 'predaplant_darlingtonia_cobra', 'predaplant_darlingtonia_cobra'),        # Jellyfish -> Predaplant Darlingtonia Cobra
    CardArt(0x17CF, 'predaplant_ophrys_scorpio', 'predaplant_ophrys_scorpio'),                # Skull Dog Marron -> Predaplant Ophrys Scorpio
    CardArt(0x0FDD, 'block_dragon', 'block_dragon'),                                          # Giant Flea -> Block Dragon
]


# ---------------------------------------------------------------------------
# Small ROM helpers
# ---------------------------------------------------------------------------
def _build_p2id(rom: ndspy.rom.NintendoDSRom) -> dict[str, int]:
    """Map every ROM filename -> file id by walking the filename tree."""
    p2id: dict[str, int] = {}

    def walk(folder, prefix=""):
        for i, name in enumerate(folder.files):
            p2id[prefix + name] = folder.firstID + i
        for sub_name, sub in folder.folders:
            walk(sub, prefix + sub_name + "/")

    walk(rom.filenames)
    return p2id


def _cid_to_art_index(rom: ndspy.rom.NintendoDSRom, p2id: dict[str, int],
                      cards: list["CardArt"] | None = None) -> dict[int, int]:
    """Return {cid: card-art atlas index} from card_prop.bin (index 0 = blank)."""
    cards = CARDS if cards is None else cards
    bin2 = bytes(rom.files[p2id[BIN2_PAC]])
    files = {f.name: f for f in parse_format_v1(bin2, "bin2.pac").files}
    pf = files[b"card_prop.bin"]
    prop = bin2[pf.address:pf.address + pf.size]
    wanted = {c.cid for c in cards}
    out: dict[int, int] = {}
    for i in range(len(prop) // 8):
        cid = struct.unpack_from("<Q", prop, i * 8)[0] & 0x3FFF
        if cid in wanted:
            out[cid] = i
    missing = wanted - set(out)
    if missing:
        raise ValueError(f"cids not found in card_prop: {[hex(c) for c in missing]}")
    return out


# ---------------------------------------------------------------------------
# card.pac rebuild (32x32 file1 + 64x64 file3)
# ---------------------------------------------------------------------------
def _patch_card_pac(rom: ndspy.rom.NintendoDSRom, p2id: dict[str, int],
                    cid_idx: dict[int, int],
                    cards: list["CardArt"] | None = None) -> None:
    cards = CARDS if cards is None else cards
    card = bytearray(rom.files[p2id[CARD_PAC]])

    f1_size = struct.unpack_from("<I", card, H_F1SIZE)[0]
    f2_start = struct.unpack_from("<I", card, H_F2START)[0]
    f2_size = struct.unpack_from("<I", card, H_F2SIZE)[0]
    f3_start = struct.unpack_from("<I", card, H_F3START)[0]
    f3_size = struct.unpack_from("<I", card, H_F3SIZE)[0]
    f2_abs, f3_abs = DATA_BASE + f2_start, DATA_BASE + f3_start

    # index table: idx[k] = stream k start (rel 0x200); deltas = compressed sizes
    n_idx = f2_size // 4
    idx = [struct.unpack_from("<I", card, f2_abs + k * 4)[0] for k in range(n_idx)]
    n_thumbs = n_idx - 1

    # shared palette lives only in thumbnail image[0]
    buf0 = decompress(bytes(card[DATA_BASE + idx[0]:DATA_BASE + idx[1]]))
    shared_pal = _parse_palette(buf0, _parse_ntbg_sections(buf0)[b"PALT"][0])

    # ---- 1) 64x64 in-place splice (fixed 2820-byte stride) ----
    for c in cards:
        ti = cid_idx[c.cid]
        off = f3_abs + ti * ART64_STRIDE
        assert struct.unpack_from("<I", card, off + 8)[0] == ART64_STRIDE, "unexpected 64x64 stride"
        template = bytes(card[off:off + ART64_STRIDE])
        f = Image.open(c.png("64x64"))
        # Convert to 64x64 RGBA, then encode to NTBG with the shared palette and the template's sections
        f = f.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
        new = encode_card_art_64x64(f, template)
        card[off:off + ART64_STRIDE] = new

    # ---- 2) 32x32 rebuild: slice all streams, replace targets, reconcat ----
    streams = [bytes(card[DATA_BASE + idx[k]:DATA_BASE + idx[k + 1]]) for k in range(n_thumbs)]
    for c in cards:
        ti = cid_idx[c.cid]
        template_ntbg = decompress(streams[ti])
        f = Image.open(c.png("32x32"))
        f = f.convert("RGBA").resize((32, 32), Image.Resampling.LANCZOS)
        new_ntbg = encode_card_thumb_32x32(f, template_ntbg, shared_pal)
        streams[ti] = compress(new_ntbg, 0x10)

    new_file1 = b"".join(streams)
    new_idx, acc = [], 0
    for s in streams:
        new_idx.append(acc)
        acc += len(s)
    new_idx.append(acc)                                  # sentinel end == file1 size
    new_f1_size = acc

    new_f2_start = (new_f1_size + 0x1FF) & ~0x1FF        # keep file2/file3 0x200-aligned
    new_f3_start = (new_f2_start + f2_size + 0x1FF) & ~0x1FF
    new_f2_abs, new_f3_abs = DATA_BASE + new_f2_start, DATA_BASE + new_f3_start

    file3_bytes = bytes(card[f3_abs:f3_abs + f3_size])   # already 64x64-spliced above
    idx_bytes = b"".join(struct.pack("<I", v) for v in new_idx)
    assert len(idx_bytes) == f2_size, (len(idx_bytes), f2_size)

    out = bytearray(card[:DATA_BASE])                    # header + pad
    struct.pack_into("<I", out, H_F1SIZE, new_f1_size)
    struct.pack_into("<I", out, H_F2START, new_f2_start)
    struct.pack_into("<I", out, H_F3START, new_f3_start)
    out += new_file1
    out += b"\x00" * (new_f2_abs - len(out))
    out += idx_bytes
    out += b"\x00" * (new_f3_abs - len(out))
    out += file3_bytes
    if len(out) % 0x200:
        out += b"\x00" * (0x200 - len(out) % 0x200)
    rom.files[p2id[CARD_PAC]] = bytes(out)


# ---------------------------------------------------------------------------
# Entry point (matches the apply_all_patches main(src, out) convention)
# ---------------------------------------------------------------------------
def main(src: str = SRC, out: str = OUT, *, cids=None, cards: list[CardArt] | None = None) -> None:
    """Replace the on-disk art (32x32 + 64x64) for every card in CARDS, or only *cids*, or an explicit *cards* list
    (test builds of unshipped cards, e.g. scratch/_monarch_session.py, which must not touch CARDS: CARDS is a release step)."""
    if cards is not None:
        cids = None
    cards = cards if cards is not None else (CARDS if cids is None else [c for c in CARDS if c.cid in set(cids)])
    if cids is not None and len(cards) != len(set(cids)):
        raise ValueError(f"cids not in CARDS: {sorted(map(hex, set(cids) - {c.cid for c in cards}))}")
    # Card art is not distributed with the repo: a card without its PNGs keeps its stock art.
    absent = [c for c in cards if not (c.png("32x32").exists() and c.png("64x64").exists())]
    if absent:
        print(f"WARNING: no art PNGs for {len(absent)} card(s), keeping stock art "
              f"(see docs/howto/5-card-art.md): {', '.join(c.base for c in absent)}", file=sys.stderr)
        cards = [c for c in cards if c not in absent]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    p2id = _build_p2id(rom)
    cid_idx = _cid_to_art_index(rom, p2id, cards)

    _patch_card_pac(rom, p2id, cid_idx, cards)

    rom.saveToFile(out)
    for c in cards:
        print(f"  art 0x{c.cid:04X} idx {cid_idx[c.cid]:4d} -> {c.base}")
    print(f"wrote card art (32x32 + 64x64) for {len(cards)} cards -> {out}")


if __name__ == "__main__":
    main()
