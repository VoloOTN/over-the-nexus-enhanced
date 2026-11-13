/* Brilliant Fusion C3 condition (CAVE_BF_C3COND): 0 if the C3 finder (CAVE_BF_C3FIND) finds nothing (< 0),
 * else 0x021F7374(ctx, a1). */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1)
{
    if (slot_CAVE_BF_C3FIND((u32)e) < 0)
        return 0;
    return fn_021F7374((u32)e, a1);
}
