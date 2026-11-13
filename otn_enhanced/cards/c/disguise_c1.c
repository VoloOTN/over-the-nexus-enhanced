/* Disguise, the Copycat Hero -- C1:
 *   "If you have an Equip Spell in your field or GY: You can Special Summon this card from your hand."
 *   (once per turn, key KEY_C1; user ruling 2026-11-04: a FACE-DOWN Equip Spell does not count)
 * One cls2 record {0x111E, RES, 0, COND, 0x0224A115, 0x0224A115} in the shape of Infernoble Oliver's hand branch
 * (in-game confirmed 2026-10-20): no cost, no target (slot4/slot5 = the native `movs r0,#2` leaf = advance).
 * The hand offer itself needs the ARM9 H4 front (LIST B is full). Build with -DSTUB=COND|RES. */
#include "disguise.h"

#define COND 1
#define RES  2

#define RES_PHASE (*(volatile u32 *)(0x0229AAFC + 0x70))
#define HAND_ZONE 0x0B

#if STUB == COND
/* +0C: hand only; OPT clear (menu time); a free Monster Zone; >= 1 Equip Spell (face-up field or GY) -> 2. */
ENTRY int entry(EffectCtx *e)
{
    u8 *d = (u8 *)e;
    if (d[3] != HAND_ZONE)
        return 0;
    if (opt_used(e, KEY_C1))
        return 0;
    if (!fn_021AD870(d[2], 0, 0))
        return 0;
    if (!count_equip_spells(d[2]))
        return 0;
    return 2;
}

#elif STUB == RES
/* +04: phase 0x80 re-checks + stamps the OPT (Oliver: OPT at resolution, Maugis lesson), then the native hand
 * self-SS resolver 0x02206ABC does the Summon in its own 0x80 and finishes in its 0x7F. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u8 *d = (u8 *)e;
    if (RES_PHASE == 0x80) {
        if (turnlog_query(d[2], TURNLOG_SLOT, KEY_C1, TURNLOG_KIND))
            return 0;
        turnlog_post(d[2], KEY_C1, TURNLOG_KIND, 0);
    }
    return handss_res((u32)e, a1);
}
#else
#error "build with -DSTUB=COND|RES"
#endif
