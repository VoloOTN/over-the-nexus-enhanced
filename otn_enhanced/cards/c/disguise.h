/* Shared helpers for Disguise, the Copycat Hero (0x111E) and Cursed Copycat Noble Arms (0x10E3).
 * Facts: notes/disguise-copycat-hero-findings.md. Every engine call is declared in asm/c/engine.h. */
#ifndef DISGUISE_H
#define DISGUISE_H
#include "engine.h"

#define DISGUISE        0x111E
#define NOBLE_ARMS      0x10E3
#define TURNLOG_SLOT    0x0B
#define TURNLOG_KIND    1
#define KEY_C1          0x511E   /* hand Special Summon            */
#define KEY_C2          0x711E   /* NS/SS search                   */
#define KEY_C3          0x111E   /* copy Level + name              */
#define KEY_N2          0x50E3   /* Noble Arms ignition            */

#define RACE_WARRIOR    15       /* game_constants.ERA2_RACE_MAP   */
#define NAME_KEY        0x1D43   /* E-HERO Prisma: name rider key  (dispatch.name_rider_key_0x1D43_kind2) */
#define LEVEL_KEY       0x1EC1   /* Copy Plant: Level SET rider key */
#define KIND_UNTIL_EP   2        /* kind 2, duration nibble 0: freed by the end-of-turn sweep 0x0219F9E0 */

#define PLAYER(side)    (0x0229AC94 + ((side) & 1) * 0xB3C)
#define ZONE_REC(s, z)  (PLAYER(s) + 0x34 + (z) * 0x14)
#define ZONE_WORD(s, z) (*(volatile u32 *)ZONE_REC(s, z))
#define ZONE_FACEUP(s, z) (*(volatile u16 *)(ZONE_REC(s, z) + 8))      /* ram.zone_record_faceup_flag */
#define GY_COUNT(side)  (*(volatile u32 *)(PLAYER(side) + 0x14))
#define GY_CID(side, i) (*(volatile u32 *)(PLAYER(side) + 0x55C + 4 * (i)) & 0x3FFF)

/* "is an Equip Spell": spell type 3 && race 23 (Infernoble Oliver's in-game-confirmed test) */
static inline int is_equip_spell(u32 cid)
{
    return cid && spell_type(cid) == 3 && get_race(cid) == 23;
}

/* Number of Equip Spells: face-up in side's S/T zones 5..9, plus side's GY. */
static inline u32 count_equip_spells(u32 side)
{
    u32 n = 0, z, i, cnt;
    for (z = 5; z <= 9; z++) {
        if (ZONE_FACEUP(side, z) && is_equip_spell(CID(ZONE_WORD(side, z))))
            n++;
    }
    cnt = GY_COUNT(side);
    for (i = 0; i < cnt; i++) {
        if (is_equip_spell(GY_CID(side, i)))
            n++;
    }
    return n;
}

/* Is the monster at (side, zone) equipped with any Equip Card (Captain Oliver's _co_equipped scan)? */
static inline int is_equipped(u32 side, u32 zone)
{
    u32 me = (zone << 8) | side, s, z;
    for (s = 0; s <= 1; s++) {
        for (z = 5; z <= 9; z++) {
            if (zone_cid_at(s, z) && (equip_target_of(s, z) & 0xFFFF) == me)
                return 1;
        }
    }
    return 0;
}

/* Menu-time hard once-per-turn: 1 = already used. Never re-queried once the cost ran (Mystic Piper rule). */
static inline int opt_used(EffectCtx *e, u32 key)
{
    return !e->cost_ran && turnlog_query(e->controller, TURNLOG_SLOT, key, TURNLOG_KIND);
}

#endif
