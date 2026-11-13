/* Accel Synchro Stardust Dragon C1 slot 4 (CAVE_ASSD_C1_SLOT4): the costless "You can" tag 0x021E50DC(ctx, a1); when
 * it answers 1, log (side, 0x126F, kind 1). Returns the tag's answer. */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r = costless_you_can(e, a1);
    if (r == 1)
        turnlog_post(e->controller, 0x126F, 1, 0);
    return r;
}
