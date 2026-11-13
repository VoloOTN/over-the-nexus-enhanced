"""The build order, as data.

Each `Step` names a module under `otn_enhanced` and how to call it. Order matters and is not alphabetical:

  1. Vanilla+: ov3 compaction, WiFi timers, pack unlocks, banlist menu, card-pack edits for unobtainable
     cards, then the Vanilla+ cards with their art. `VANILLA_PLUS_END` marks where `build --vanilla-plus` stops.
  2. The remaining cards, their art, banlist, Regulus, bulk property conversions, remaining field art.
  3. Full card-pack changes, decks, rewards, deck names, duelist unlocks.

Ordering constraints are written above the row that needs them as `After X: why`. They are enforced by
before-image asserts in the later card, so a wrong order mostly fails loudly rather than shipping quietly.

Call shapes (the only ones that exist):
  text=FLAG    main(write_text=<--no-text flag>, src=, out=)
  text=ALWAYS  main(write_text=True, src=, out=)       grapha, ceruli, dragon_shrine
  text=None    main(src=, out=)
plus one positional entry (`pack_unlock_conditions.main(src, out)`) and one non-`main` entry
(`default_banlist.patch_banlist`).

elbow: the constraints live only in comments; a table of `after=` names checked at import would be sturdier.
"""
from __future__ import annotations

import importlib
from typing import Callable, NamedTuple

FLAG = "flag"        # follow the build's --no-text switch
ALWAYS = "always"    # this module hardcodes write_text=True in the old chain

_PKG = "otn_enhanced"


class Step(NamedTuple):
    name: str                     # human label, printed while applying
    module: str                   # dotted path under otn_enhanced
    text: str | None = FLAG       # FLAG / ALWAYS / None -- see CALL SHAPES above
    entry: str = "main"           # the callable to invoke
    positional: bool = False      # entry(src, out) instead of entry(src=, out=)
    kwargs: dict | None = None    # extra keyword args for entry (subset / filter switches)


# Art and field backgrounds are split at the divergence point: the vanilla+ cards' art goes
# in with them, everything else's goes in with the remaining cards.
VANILLA_PLUS_ART = frozenset({
    0x1463, 0x13B8, 0x0FD3, 0x0FC2, 0x0FD8, 0x0FFD, 0x11B7, 0x1F18, 0x0FA9, 0x22E6,   # Tengu .. Rush Rhino
    0x1315, 0x1FFC, 0x16A2, 0x1225, 0x211B, 0x19B2, 0x0FB4, 0x1DDD, 0x0FC8,           # Meteorite .. Haipa
    0x1126, 0x0FCB, 0x13C6, 0x17CE, 0x181C, 0x18FA, 0x106C,                           # Meiru Wall .. Mara
    0x13A5,                                                                           # Boggart Knight (see below)
    0x10F5,                                                                           # The Seal of Orichalcos
    0x13AC,                                           # Aratame
    0x1783,                                           # XX-Saber Darksoul
    0x2124, 0x1465,                                   # Amazoness Heirloom, Naturia Pineapple
})
# The Seal 0x10F5 is vanilla+: all its code is ov3 (cave3.CAVE3_SEAL_*), and its C3 stub
# The Seal is Vanilla+: all its code is ov3. Boggart Knight is Vanilla+ and must precede Rush Rhino,
# which spends its template phantom 0x2346. Maiden is not Vanilla+: Ninishi and Haipa install the
# shared attack-target gate themselves (effects/atktgt_gate.py).
VANILLA_PLUS_FIELD = frozenset({0x10F5})                  # The Seal of Orichalcos


def _rest(module: str, attr: str, vp: frozenset) -> frozenset:
    cards = getattr(importlib.import_module(f"{_PKG}.{module}"), attr)
    return frozenset(c.cid if hasattr(c, "cid") else c for c in cards) - vp


REST_ART = _rest("data.card_art", "CARDS", VANILLA_PLUS_ART)
REST_FIELD = _rest("data.field_backgrounds", "CARDS", VANILLA_PLUS_FIELD)


STEPS: list[Step] = [
    # ===== VANILLA+ (1/2): global / menu patches, in this exact order =====
    # Before ov3 compaction, which then asserts its freed runs are still stock (fails on an overlap).
    Step("CardWorkshop CPU speed-up + View Mode",                     "system.cardworkshop_speed_view", None),
    # First ov3 edit after CardWorkshop's: asserts stock ov3 bytes and frees dead/duplicate code.
    Step("ov3 compaction (free phantom-dead + duplicate code)",        "system.ov3_compact", None),
    Step("WiFi Turn/Match timers (99 / 999 min)",                     "system.wifi_timers", None),
    Step("Booster-pack unlock conditions (All at Random open)",       "system.pack_unlock_conditions", None, "main", True),
    Step("Banlist menu: Treat Ltd as Forb -> No Banlist",             "system.no_banlist_mode", None),
    Step("Wi-Fi emblems piggybacked on offline emblems",             "system.wifi_emblems", None),
    # ===== VANILLA+ (2/2): the new cards (existing relative order kept) =====
    Step("Reborn Tengu",                      "cards.reborn_tengu"),
    Step("Mystic Piper",                               "cards.mystic_piper"),
    Step("Infernity Barrier",                    "cards.infernity_barrier"),
    Step("Vylon Element -- WHEN -> IF trigger fix",                    "cards.vylon_element"),
    Step("Gravekeeper's Recruiter",                    "cards.gravekeepers_recruiter"),
    Step("Tour Guide",                          "cards.tour_guide"),
    Step("Wattcobra",                                       "cards.wattcobra"),
    Step("Karakuri Komachi Ninishi",  "cards.ninishi"),
    Step("T.G. Hyper Librarian",                    "cards.hyper_librarian"),
    Step("Shooting Quasar",                    "cards.shooting_quasar"),
    Step("Metal Armored Bug -- stats + text",                          "cards.metal_armored_bug"),
    Step("W Nebula Meteorite",                            "cards.w_nebula_meteorite"),
    Step("Elder of the Six Samurai", "cards.elder_six_samurai"),
    Step("T.G. Striker",                 "cards.tg_striker"),
    Step("T.G. Warwolf",          "cards.tg_warwolf"),
    Step("XX-Saber Boggart Knight",                 "cards.boggart_knight"),
    Step("T.G. Rush Rhino",           "cards.tg_rush_rhino"),
    Step("Armory Arm -- battle-burn GY-presence bug fix",              "cards.armory_arm"),
    Step("Sea Lancer",                               "cards.sea_lancer"),
    Step("Safe Zone",                                "cards.safe_zone"),
    Step("Shien's Dojo",         "cards.shiens_dojo"),
    Step("Karakuri Muso mdl 818 'Haipa'",     "cards.karakuri_haipa"),
    Step("Junk Servant",           "cards.junk_servant"),
    Step("Unknown Synchron",        "cards.unknown_synchron"),
    Step("Scrap Archfiend ",    "cards.scrap_archfiend"),
    Step("Orient Dragon", "cards.orient_dragon"),
    Step("Koa'ki Meiru Wall",          "cards.koaki_meiru_wall"),
    Step("Life Stream Dragon",            "cards.life_stream_dragon"),
    # Its hook at 0x0226395C precedes Revolution Synchron's H3 in the same site.
    Step("Mara of the Nordic Alfar",       "cards.mara"),
    # Before eva: Eva's G stub follows the Seal's C5 block at 0x02221328.
    Step("The Seal of Orichalcos",               "cards.seal_of_orichalcos"),
    Step("Aratama",                                 "cards.aratama"),
    Step("Amazoness Heirloom",   "cards.amazoness_heirloom"),
    Step("Naturia Pineapple",      "cards.naturia_pineapple"),
    # After every other Vanilla+ card: fixes the phantom-drop order (set-code 0x2346, cls2 0x0E15,
    # populate 0x0E21, registry row 0x0228E598).
    Step("Dark Soul",                                    "cards.darksoul"),
    Step("Field background -- The Seal of Orichalcos",                 "data.field_backgrounds", None,
         kwargs={"cids": VANILLA_PLUS_FIELD}),
    Step("Card art -- vanilla+ cards",                                 "data.card_art", None,
         kwargs={"cids": VANILLA_PLUS_ART}),
    Step("Battle sprites -- vanilla+ cards",                           "data.battle_sprites", None,
         kwargs={"cids": VANILLA_PLUS_ART}),
    # Name-guarded, so it runs twice: after the Vanilla+ cards and again after the rest.
    Step("Card genre (search filters) -- vanilla+ cards",             "data.card_genre", None),
    Step("Extra banlists: Mar 2010 / Mar 2011 / Sep 2011 / Mar 2012",  "data.extra_banlists", None),
    Step("Card Pack Changes (unobtainable cards only)",               "data.bulk_card_pack", None,
         kwargs={"unobtainable_only": True}),
    # ===== DIVERGENCE POINT: everything above is VANILLA+ (build --vanilla-plus stops here) =====
    # ===== FULL: the remaining cards =====
    Step("Thunder Sea Horse",                       "cards.thunder_sea_horse"),
    Step("E-HERO Escuridao",      "cards.escuridao"),
    Step("Eclipse Wyvern",        "cards.eclipse_wyvern"),
    Step("Lightpulsar Dragon",       "cards.lightpulsar"),
    Step("Darkflare Dragon",           "cards.darkflare"),
    Step("Dragon Shrine", "cards.dragon_shrine", ALWAYS),
    Step("The Gates of Dark World",            "cards.gates_of_dark_world"),
    Step("Snoww, Unlight of Dark World",       "cards.snoww"),
    Step("Grapha, Dragon Lord of Dark World",    "cards.grapha", ALWAYS),
    Step("Ceruli, Guru of Dark World",        "cards.ceruli", ALWAYS),
    Step("Maiden with Eyes of Blue",   "cards.maiden_eyes_of_blue"),
    Step("Azure-Eyes Silver Dragon",    "cards.azure_eyes"),
    Step("Ninja Grandmaster Hanzo",          "cards.ninja_grandmaster_hanzo"),
    Step("Ninjitsu Art of Super-Transformation",     "cards.ninjitsu_art_super_transformation"),
    Step("White Dragon Ninja",   "cards.white_dragon_ninja"),
    Step("Upstart Golden Ninja",     "cards.upstart_golden_ninja"),
    Step("Junk Speeder", "cards.junk_speeder"),
    Step("Jet Synchron",         "cards.jet_synchron"),
    Step("Jet Warrior",      "cards.jet_warrior"),
    Step("Steam Synchron",                     "cards.steam_synchron"),
    Step("Accel Synchron",            "cards.accel_synchron"),
    Step("Cardcar D",              "cards.cardcar_d"),
    Step("Soul Charge",             "cards.soul_charge"),
    Step("Mathematician",                 "cards.mathematician"),
    Step("Kuribandit",                      "cards.kuribandit"),
    Step("Accel Synchro Stardust Dragon",  "cards.accel_synchro_stardust_dragon"),
    Step("Assault Synchron",                    "cards.assault_synchron"),
    Step("Psi-Reflector",               "cards.psi_reflector"),
    Step("Revolution Synchron",    "cards.revolution_synchron"),
    Step("Crimson Blader",             "cards.crimson_blader"),
    Step("Dragunity Remus",
         "cards.dragunity_remus"),
    # After ninishi: C1b chains into ninishi's five CAVE_NS_* stubs and asserts their before-images.
    # Running it first aborts the build.
    Step("Scrap Raptor",                      "cards.scrap_raptor"),
    # After scrap_raptor and assault_synchron: fronts raptor's six CAVE3_SR_* granter sites and
    # assault's leave hook 0x021C93D0, asserting both before-images.
    Step("Sakitama",                          "cards.sakitama"),
    Step("Miscellaneousaurus",                   "cards.miscellaneousaurus"),
    Step("Souleating Oviraptor",        "cards.souleating_oviraptor"),
    Step("Petiteranodon",              "cards.petiteranodon"),
    Step("Brilliant Fusion",     "cards.brilliant_fusion"),
    Step("Raiden, Hand of the Lightsworn",  "cards.raiden"),
    Step("Elemental HERO Shadow Mist", "cards.shadow_mist"),
    Step("Masked HERO Dark Law",           "cards.masked_hero_dark_law"),
    # After masked_hero_dark_law: its ov3 stubs live in 0x1AC7's body, dead once Dark Law drops that cls1.
    Step("Elder Entity Norden",             "cards.elder_entity_norden"),
    Step("Double Evolution Pill",       "cards.double_evolution_pill"),
    # After masked_hero_dark_law and elder_entity_norden: stubs in 0x1AC7's body at 0x022234C0.
    Step("Ultimate Conductor Tyranno",       "cards.ultimate_conductor_tyranno"),
    Step("Animadorned Archosaur", "cards.animadorned_archosaur"),
    # After shadow_mist (lifts its chain and miss-timing nodes), miscellaneousaurus, tyranno
    # (stub in 0x0E46's body) and animadorned_archosaur (borrows its Pill predicate).
    Step("Overtex Qoatlus",                "cards.overtex_qoatlus"),
    # After life_stream_dragon.
    Step("Ojamassimilation",   "cards.ojamassimilation"),
    Step("That Grass Looks Greener",            "cards.that_grass_looks_greener"),
    # After elder_entity_norden (NEG_STUB) and petiteranodon (CAVE_PTER_NOATK): two bls pointing at
    # those stubs get a pre-check in front.
    Step("Obedience Schooled",     "cards.obedience_schooled"),
    # After shadow_mist (fronts its miss node 0x021EE10C), obedience_schooled (zero-filled host tail
    # 0x02237E38) and seal_of_orichalcos (owns 0x02221328's block head).
    Step("Eva",                                  "cards.eva"),
    # After mara: mara owns the gate literal 0x02249534; wattuna hooks the gate tail 0x02249516.
    Step("Wattuna",                 "cards.wattuna"),
    Step("Wattkyuki",                         "cards.wattkyuki"),
    Step("Grandsoil the Elemental Lord", "cards.grandsoil"),
    # After grandsoil: shares its ov3 leave stub (dsl.ELEMENTAL_LORD_CIDS).
    Step("Moulinglacia the Elemental Lord", "cards.moulinglacia"),
    # After moulinglacia. Timing arm in timing_class_hook.ARMS, C5 cid in dsl.ELEMENTAL_LORD_CIDS.
    Step("Pyrorex the Elemental Lord",     "cards.pyrorex"),
    # After pyrorex. C5 cid in dsl.ELEMENTAL_LORD_CIDS; C3 rides the shared c79_trigger_hook.
    Step("Windrose the Elemental Lord",          "cards.windrose"),
    Step("Uni-Zombie",                           "cards.uni_zombie"),
    # After sakitama (fronts its six CAVE3_SK_* granter stubs) and petiteranodon (fronts node 0x021D13C2,
    # whose literal petiteranodon re-keys).
    Step("Nikitama",                             "cards.nikitama"),
    Step("Neo Space Connector",                  "cards.neo_space_connector"),
    # After obedience_schooled: its C2 pre-checks front OS's NEGR/EPL at bl 0x021EE418 / 0x02268090.
    Step("NEXT",                                 "cards.next_card"),
    # Virtual registry: cave3 hooks instead of table rows. After revolution_synchron (takes over its 4 GY
    # sites, keeping row 60), eclipse_wyvern (fronts its banish-gate stub), petiteranodon,
    # obedience_schooled and next_card (splices the babies' can't-attack prechecks into their chains).
    Step("Dragon Rulers",                        "cards.dragon_rulers"),
    Step("Denko Sekka",                          "cards.denko_sekka"),
    # After dragon_rulers and revolution_synchron: C4 appends a 6th virtual GY row to Rulers' table.
    # Composes with denko_sekka's front inside the activation-prohibited predicate.
    Step("Sekka's Light",                        "cards.sekkas_light"),
    # After dragon_rulers: fronts its H2 and uses H3. The Deck row is virtual (front on 0x02243F24).
    Step("Fire Formation - Tenki",               "cards.fire_formation_tenki"),
    # After dragon_rulers and fire_formation_tenki: its criteria row is virtual, chaining Tenki's front.
    Step("Sacred Sword of Seven Stars",          "cards.sacred_sword_seven_stars"),
    # After dragon_rulers and revolution_synchron (gy_vrow_hook lifts their GY table), and after
    # shadow_mist, obedience_schooled and next_card.
    # elbow: shipped with known gaps; see the notes for the original step in ygo_tools.
    Step("Infernoble Knights",                   "cards.infernoble"),
    # Its fronts sit AHEAD of infernoble's (miss node, stat site, ARM9 H4), dragon_rulers' H3 and sacred_sword's H2
    # front (ov5_cave.dc_next), so it must run after all three. Its C2 arms live in c79/timing_class_hook.ARMS.
    Step("Disguise, the Copycat Hero + Cursed Copycat Noble Arms", "cards.disguise_copycat"),
    # After disguise_copycat: its H2/H3 fronts sit AHEAD of Disguise's (ov5_cave.dc_next) and use Disguise's Noble Arms.
    Step("Noble Knight Medraut",                 "cards.noble_knight_medraut"),
    # After medraut and disguise_copycat: its H2/H3/H4/stat fronts sit AHEAD of theirs (ov5_cave.dc_next), its find_event_handler front
    # (0x0224A86A) sits AHEAD of dragon_rulers' H1, and its Damage-Step poster front sits AHEAD of tyranno's M stub.
    Step("Immortal Phoenix Gearfried",           "cards.immortal_phoenix_gearfried"),
    # After gearfried and disguise_copycat: its never-miss front sits AHEAD of Disguise's (ov5_cave.dc_next), its leave front AHEAD of the
    # Infernoble Arms chain head (Hauteclere's), and its validity front is the default arm of 0x021EDE48 (0x021EE05A).
    Step("Phoenix Gearblade",                    "cards.phoenix_gearblade"),
    # After phoenix_gearblade: its never-miss front sits AHEAD of Gearblade's and its H2/H3 fronts AHEAD of Gearfried's (ov5_cave.dc_next); its arms live in
    # c79_trigger_hook.ARMS / c9_trigger_hook.ARMS. Shipped WITHOUT custom art (user 2026-11-06: art to follow).
    Step("Predaplant Darlingtonia Cobra + Ophrys Scorpio", "cards.predaplant"),
    # After predaplant, gearfried, windrose, seal_of_orichalcos, dragon_rulers, infernoble (gy_vrow_hook) and eva/shadow_mist: its H1-H4 fronts sit AHEAD of
    # theirs (ov5_cave.dc_next), its CPU hand-loop front tails to the shared hand-SS trampoline, its C2 front sits ahead of Seal's survive-check stub and
    # its never-miss front ahead of the miss-node chain head. Also carries the CPU-play fixes for the Elemental Lords and the four big Dragon Rulers.
    Step("Block Dragon",                         "cards.block_dragon"),
    # After block_dragon, windrose and the tg_table registrants (its CPU front tails to the shared hand-SS trampoline): CPU play for the Elemental Lords, the four
    # big Dragon Rulers and Block Dragon (split out of block_dragon 2026-11-09); a card-less module (no stats or text).
    Step("CPU hand Special Summons (Elemental Lords, Dragon Rulers, Block Dragon)", "cards.cpu_hand_ss"),
    # After block_dragon: Coral Dragon's never-miss front reads the live miss-node head (block_dragon's front, which hard-codes the head it expects, so
    # block_dragon must install FIRST) and its Special-Summon marker front sits on the three `BL 0x02265768` callers (stock in every build so far).
    Step("Coral Dragon",                         "cards.coral_dragon"),
    Step("Card art -- remaining cards",                                "data.card_art", None,
         kwargs={"cids": REST_ART}),
    # Battle (attack) sprites from each card's <base>_character_256x96.png; repacks duel2d/BattleMonster{1,2,3}.pac
    # (user said "wire it in" 2026-11-13; AWAITING IN-GAME TEST). Encodes are cached in working/battle_sprite_cache/.
    Step("Battle sprites -- remaining cards",                          "data.battle_sprites", None,
         kwargs={"cids": REST_ART}),
    Step("Apply Banlist Changes",                                      "data.default_banlist", None, "patch_banlist"),
    Step("PB Regulus",                                                 "data.regulus", None),
    Step("Bulk Card Changes",                                          "data.bulk_card_props", None),
    Step("Field backgrounds -- remaining converted Field Spells",       "data.field_backgrounds", None,
         kwargs={"cids": REST_FIELD}),
    Step("Card genre (search filters) -- remaining cards",            "data.card_genre", None),
    # ===== FULL: the Monarch set (SHIPPED 2026-11-12 on the user's word "Ship them"; NOT in-game tested at ship time) =====
    # Applied in the exact order of the tested combined build (scratch/_monarch_session.py ORDER, on top of every step above): each shared front tails
    # to the previous owner, so this order is load-bearing (ov5_cave.combo() is now on by default -- MONARCH_COMBO=0 only for single-card test builds).
    # Their card art is in data.card_art.CARDS (the "Card art -- remaining cards" step above). Known chain-head verify lines: see notes/eidos-masterplan-timing-2026-11-12.md.
    Step("Mega Monarchs + Angmarl",                                    "cards.mega_monarch"),
    Step("March of the Monarchs",                                      "cards.march"),
    Step("The Monarchs Stormforth",                                    "cards.stormforth"),
    Step("Tenacity of the Monarchs",                                   "cards.tenacity"),
    Step("Return of the Monarchs",                                     "cards.return_monarchs"),
    Step("Restoration of the Monarchs",                                "cards.restoration"),
    Step("The Monarchs Awaken",                                        "cards.monarchs_awaken"),
    Step("Pantheism of the Monarchs",                                  "cards.pantheism"),
    Step("Frost Blast of the Monarchs",                                "cards.frost_blast"),
    Step("The Monarchs Revolt",                                        "cards.revolt"),
    Step("Edea the Heavenly Squire",                                   "cards.edea"),
    Step("Eidos the Underworld Squire",                                "cards.eidos_squire"),
    Step("Tessera the Primal Squire",                                  "cards.tessera"),
    Step("Eidos the Underworld Monarch",                               "cards.eidos_monarch"),
    Step("Tessera the Primal Squire (hand effect)",                    "cards.tessera_hand"),
    Step("The Monarchs Masterplan",                                    "cards.masterplan"),
    Step("The Monarchs Erupt",                                         "cards.erupt"),
    Step("Strike of the Monarchs",                                     "cards.strike"),
    Step("Domain of the True Monarchs",                                "cards.domain"),
    Step("Erebus / Ehther / Prime / First (E1) / Perfection",          "cards.erebus"),
    Step("Escalation of the Monarchs",                                 "cards.escalation"),
    Step("The First Monarch",                                          "cards.first_monarch"),
    # card_genre only tags a cid once its NAME matches, and the run above happens before the Monarch set renames
    # its donors -- without this pass every Monarch card ships its donor's search-filter genre.
    Step("Card genre (search filters) -- Monarch set",                 "data.card_genre", None),

    # ===== FULL: bulk data, menus and unlocks -- LAST =====
    # CHANGES is keyed by the ROM-HACK's card names (donor rows renamed), so it resolves against src.
    Step("Apply Card Pack Changes (all)",                              "data.bulk_card_pack", None),
    Step("Apply Deck Changes",                                         "data.bulk_ydcs", None),
    Step("Apply Concentration Changes",                                "data.bulk_memory", None),
    Step("Deck name renames",                                          "system.deck_names", None),
    Step("CPU duelist unlock conditions",                              "system.duelist_unlock_conditions", None),
]

# Number of leading STEPS that make up VANILLA+ (`build --vanilla-plus` stops after them).
VANILLA_PLUS_END = next(i for i, s in enumerate(STEPS) if s.name == "Card Pack Changes (unobtainable cards only)") + 1

def resolve(step: Step) -> tuple[Callable, str]:
    """Return (callable, module_path) for *step*."""
    path = f"{_PKG}.{step.module}"
    return getattr(importlib.import_module(path), step.entry), path


def call(step: Step, src: str, out: str, *, write_text: bool) -> None:
    """Invoke *step* with the call shape it expects."""
    fn, _ = resolve(step)
    kw = step.kwargs or {}
    if step.positional:
        fn(src, out, **kw)
    elif step.text is None:
        fn(src=src, out=out, **kw)
    else:
        fn(write_text=True if step.text == ALWAYS else write_text, src=src, out=out, **kw)
