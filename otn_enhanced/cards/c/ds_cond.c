/* Ds condition (CAVE_DS_COND): 0 if (side, 0xB, cid, kind 1) is logged this turn, else 0x021F0B18(ctx). */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1)
{
    if (turnlog_query(e->controller, 0xB, e->cid, 1))
        return 0;
    return fn_021F0B18((u32)e);
}
