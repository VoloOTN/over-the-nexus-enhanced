/* Thunder Sea Horse resolver (CAVE_TSH_RES): unless 0x021D2B88(a0..a3) says so, log (side, cid, kind 1); then 0x021E6FD8(ctx). */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1, u32 a2, u32 a3)
{
    if (!fn_021D2B88((u32)e, a1, a2, a3))
        turnlog_post(e->controller, e->cid, 1, 0);
    return fn_021E6FD8((u32)e);
}
