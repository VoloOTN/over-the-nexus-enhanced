/* Accel Synchro Stardust Dragon C2 cost (CAVE_ASSD_C2_COST): log (side, 0x126F, kind 2), then Tribute it. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, 0x126F, 2, 0);
    return tribute_tag((u32)e);
}
