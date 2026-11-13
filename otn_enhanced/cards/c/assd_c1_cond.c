/* Accel Synchro Stardust Dragon C1 condition (CAVE_ASSD_C1_COND): 0 if (side, 0xB, 0x126F, kind 1) is logged this
 * turn, else 0x021F03B4(ctx). */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if (turnlog_query(e->controller, 0xB, 0x126F, 1))
        return 0;
    return fn_021F03B4((u32)e);
}
