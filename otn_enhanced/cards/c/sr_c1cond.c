/* Scrap Raptor C1 condition (CAVE_SR_C1COND): before the cost ran, refuse if (side, 0xB, cid, kind 1) is logged this
 * turn; otherwise the once-per-turn rider 0x021F01C0(ctx). Same shape as mystic_piper_cond.c. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if (!e->cost_ran && turnlog_query(e->controller, 0xB, e->cid, 1))
        return 0;
    return opt_rider((u32)e);
}
