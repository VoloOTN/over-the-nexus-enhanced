/* E-HERO Shadow Mist condition (CAVE_SM_COND): 0 if (side, 0xB, 0x111F, kind 1) is logged this turn, else the
 * native hand-discard ignition condition 0x021F0820(ctx). Same shape as psi_cond.c. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if (turnlog_query(e->controller, 0xB, 0x111F, 1))
        return 0;
    return fn_021F0820((u32)e);
}
