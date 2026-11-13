/* The Monarchs Awaken (0x1633, donor Disarmament).  Build with -DSTUB=AW_FILT|AW_COND|AW_RES.
 * Design + UNPROVEN list: notes/monarchs-awaken-findings.md and cards/monarchs_awaken.py. */
#include "disguise.h"

#define AW_FILT 1
#define AW_COND 2
#define AW_RES  3

#define AWAKEN        0x1633
#define FLAGS(s, z)   (*(volatile u32 *)(0x0229ACD8 + ((s) & 1) * 0xB3C + (z) * 0x14))   /* zone flag word: bit 3 = Tribute Summoned */
#define TRIBUTE_SUMMONED 0x8
#define EXTRA_COUNT(side) (*(volatile u32 *)(PLAYER(side) + 0x18))

#if STUB == AW_FILT
/* cls0 +08 (desc, side, zone) -> 1 = legal target: your own face-up monster (the native 0x0C15 own-side / face-up mask) that was Tribute Summoned. */
ENTRY int entry(u8 *desc, u32 side, u32 zone)
{
    if (!zone_predicate((u32)desc, side, zone, 0x0C15))
        return 0;
    if (zone > 4)
        return 0;
    return (FLAGS(side, zone) & TRIBUTE_SUMMONED) != 0;
}

#elif STUB == AW_COND
/* cls0 +0C: "If you have no cards in your Extra Deck".  Returns a CODE: 0 = no, 1 = activatable if the +08 sweep finds a target. */
ENTRY int entry(EffectCtx *e)
{
    return EXTRA_COUNT(e->controller) == 0 ? 1 : 0;
}

#elif STUB == AW_RES
/* cls0 +04: one phase.  The picked monster must still be a legal target; it gets a kind-3 rider keyed 0x1633 (kind 3 survives every turn sweep):
 * the negate reader honours the key (module PREB front) and the affect predicate front protects it from every card but this one. */
ENTRY int entry(EffectCtx *e)
{
    u32 loc, ts, tz;
    if (!pick_validate((u32)e, 0, &loc))
        return 0;
    ts = loc & 0xFF;
    tz = (loc >> 8) & 0xFF;
    if (!revalidate((u32)e, ts, tz))
        return 0;
    rider_attach(ts, tz, AWAKEN, 3, 0);
    return 0;
}

#else
#error "build with -DSTUB=AW_FILT|AW_COND|AW_RES"
#endif
