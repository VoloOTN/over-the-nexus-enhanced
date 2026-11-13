/* Psi-Reflector condition (CAVE_PSI_COND): 0 if (side, 0xB, 0x1008, kind 1) is logged this turn, else the native
 * hand-discard ignition condition 0x021F0820(ctx). */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if (turnlog_query(e->controller, 0xB, 0x1008, 1))
        return 0;
    return fn_021F0820((u32)e);
}
