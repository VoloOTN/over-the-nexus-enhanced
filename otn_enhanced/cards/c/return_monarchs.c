/* Return of the Monarchs (0x14A1, donor Vengeful Bog Spirit).  Build with -DSTUB=R_COND|R_COST|R_RES|R_TEST and -DDATA=<ov5 data address>.
 * DATA layout (ov5 slot CAVE_RT_DATA): +0 u32 swap flag, +4 u32 side, +8 u32 zone, +0xC u32 summoned cid.
 * Design + UNPROVEN list: notes/monarch-megas-findings.md Session 23 and cards/return_monarchs.py. */
#include "disguise.h"

#define R_COND 1
#define R_COST 2
#define R_RES  3
#define R_TEST 4

#define RETURN        0x14A1
#define STATE         0x0229AAFC          /* +0x70 resolver phase, +0x7C cost step */
#define RT_FLAG       (*(volatile u32 *)(DATA + 0x0))
#define RT_SIDE       (*(volatile u32 *)(DATA + 0x4))
#define RT_ZONE       (*(volatile u32 *)(DATA + 0x8))
#define RT_CID        (*(volatile u32 *)(DATA + 0xC))

typedef int (*fn2)(u32, u32);
#define HAS_CANDIDATE ((fn2)0x021F0821)     /* RotA's candidate test on the Deck row */
#define DECK_TO_HAND  ((fn2)0x02207EF5)     /* native Deck -> hand resolver */

/* "The Tribute Summoned monster must be face-up on the field": the recorded zone still holds that card, face-up. */
static inline int summoned_faceup(void)
{
    u32 side = RT_SIDE & 1, zone = RT_ZONE;
    if (zone > 4)
        return 0;
    return ZONE_FACEUP(side, zone) != 0 && CID(ZONE_WORD(side, zone)) == RT_CID;
}

#if STUB == R_COND
/* cls1 +0C: OPT clear, the Tribute Summoned monster still face-up, and a Deck candidate exists (the Deck row, via the H2/H3 fronts). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    u8 *d = (u8 *)e;
    if (turnlog_query(d[2], 0x0B, RETURN, 1))
        return 0;
    if (!summoned_faceup())
        return 0;
    return HAS_CANDIDATE((u32)e, a1);
}

#elif STUB == R_COST
/* cls1 +14 (after the native "You can" prompt said yes): stamp the once-per-turn node (cost step 0 only: the cost may be re-entered). */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    (void)a1;
    if (*(volatile u32 *)(STATE + 0x7C) == 0)
        turnlog_post(e->controller, RETURN, 1, 0);
    return 1;
}

#elif STUB == R_RES
/* cls1 +04: at the first phase the monster must still be face-up ("to resolve"), then the native Deck -> hand resolver. */
ENTRY int entry(EffectCtx *e, u32 a1)
{
    if (*(volatile u32 *)(STATE + 0x70) == 0x80 && !summoned_faceup())
        return 0;
    return DECK_TO_HAND((u32)e, a1);
}

#elif STUB == R_TEST
/* Trigger test (called by the TRIG wrapper with r0 = the summon descriptor 0x02298A28): the summoner has a face-up Return in its
 * Spell/Trap zones 5..9 and has not used the once-per-turn node -> record the summoned monster and raise the swap flag. */
ENTRY int entry(u8 *d)
{
    u32 side = d[2] & 1, z, have = 0;
    for (z = 5; z <= 9; z++) {
        if (ZONE_FACEUP(side, z) && CID(ZONE_WORD(side, z)) == RETURN) {
            have = 1;
            break;
        }
    }
    if (!have || turnlog_query(side, 0x0B, RETURN, 1))
        return 0;
    RT_SIDE = side;
    RT_ZONE = *(volatile u16 *)(d + 4);
    RT_CID = *(volatile u16 *)(d + 0xE) & 0x3FFF;
    RT_FLAG = 1;
    return 1;
}

#else
#error "build with -DSTUB=R_COND|R_COST|R_RES|R_TEST -DDATA=<addr>"
#endif
