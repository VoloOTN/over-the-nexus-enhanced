/* Shared helpers for Noble Knight Medraut (0x0FD9, donor Armored Lizard). Facts: notes/noble-knight-medraut-findings.md.
 * Builds on Disguise's helpers (disguise.h): zone/GY macros, is_equip_spell, opt_used. */
#ifndef MEDRAUT_H
#define MEDRAUT_H
#include "disguise.h"

#define MEDRAUT   0x0FD9
#define KEY_MK    0x5FD9          /* Medraut's hard once-per-turn (turn-log slot 0x0B, kind 1) */

/* "Noble Arms" = the four Infernoble Arms (Joyeuse, Durendal, Almace, Hauteclere) + Cursed Copycat Noble Arms
 * (user 2026-11-04: "yes" to counting 0x10E3). */
static inline int is_noble_arms(u32 c)
{
    return c == 0x15E3 || c == 0x1663 || c == 0x1C39 || c == 0x1F71 || c == NOBLE_ARMS;
}

/* Is the monster at (side, zone) equipped with a Noble Arms Equip Spell? (Captain Oliver's scan, filtered by cid.) */
static inline int armed(u32 side, u32 zone)
{
    u32 me = (zone << 8) | side, s, z;
    for (s = 0; s <= 1; s++) {
        for (z = 5; z <= 9; z++) {
            if (is_noble_arms(CID(zone_cid_at(s, z))) && (equip_target_of(s, z) & 0xFFFF) == me)
                return 1;
        }
    }
    return 0;
}

/* Medraut's effect text is live: a Medraut in monster zone `zone`, present and not disabled, equipped with Noble Arms. */
static inline int mk_active(u32 side, u32 zone)
{
    side &= 1;
    if (zone > 4 || CID(ZONE_WORD(side, zone)) != MEDRAUT || !zone_active(side, zone))
        return 0;
    return armed(side, zone);
}

#endif
