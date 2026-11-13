/* Restoration of the Monarchs (0x12EE, donor Burning Spear).  Build with -DSTUB=RS_COND|RS_COST|RS_TRIB.
 * Design + UNPROVEN list: notes/restoration-findings.md and cards/restoration.py. */
#include "disguise.h"

#define RS_COND 1
#define RS_COST 2
#define RS_TRIB 3

#define RESTORATION   0x12EE
#define STATE         0x0229AAFC          /* +0x7C cost step */

typedef int (*fn2)(u32, u32);
#define NATIVE_COND ((fn2)0x021F03B5)     /* Premature Burial's cls0 cond: free zone + a GY candidate through the criteria row */

#if STUB == RS_COND
/* cls0 +0C: once per turn (menu check only), then the native GY-Special-Summon condition. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    if (opt_used(e, RESTORATION))
        return 0;
    return NATIVE_COND((u32)e, a1);
}

#elif STUB == RS_COST
/* cls0 +10: stamp the once-per-turn node (cost step 0 only: the cost may be re-entered).  No LP is paid. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    (void)a1;
    if (*(volatile u32 *)(STATE + 0x7C) == 0)
        turnlog_post(e->controller, RESTORATION, 1, 0);
    return 1;
}

#elif STUB == RS_TRIB
/* "The equipped monster can be treated as 2 Tributes": is the own monster at (side, slot) equipped with a face-up Restoration?
 * Called by the 0x021AE14A front with r0 = player, r1 = candidate side, r2 = slot (the front already tested the hit for the caller). */
ENTRY int entry(u32 player, u32 side, u32 slot)
{
    u32 me = (slot << 8) | (side & 1), z;
    if (side != player)
        return 0;
    for (z = 5; z <= 9; z++) {
        if (ZONE_FACEUP(side, z) && CID(ZONE_WORD(side, z)) == RESTORATION && (equip_target_of(side, z) & 0xFFFF) == me)
            return 1;
    }
    return 0;
}

#else
#error "build with -DSTUB=RS_COND|RS_COST|RS_TRIB"
#endif
