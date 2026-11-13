/* Uni-Zombie condition (CAVE_UZ_COND): before the cost ran, 0 unless the Uni-Zombie mask (CAVE_UZ_MASK) passes;
 * then the vanilla ignition check 0x021F06E8(ctx). */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if (!e->cost_ran && !slot_CAVE_UZ_MASK((u32)e))
        return 0;
    return can_take_ignition((u32)e);
}
