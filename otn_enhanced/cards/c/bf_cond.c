/* Brilliant Fusion condition (CAVE_BF_COND): once the cost ran, or when 0x021F6DD8(ctx, a1, a2, a3) passes, the
 * answer is 0x02232CB0(ctx); otherwise 0. */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1, u32 a2, u32 a3)
{
    if (!e->cost_ran && !fn_021F6DD8((u32)e, a1, a2, a3))
        return 0;
    return fn_02232CB0((u32)e);
}
