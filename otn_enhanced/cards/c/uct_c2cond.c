/* Ultimate Conductor Tyranno C2 condition (CAVE_UCT_C2COND): before the cost ran, only in phase 2 or 4 (word
 * 0x0229DD14 + 0x48); then the once-per-turn rider 0x021F01C0(ctx). */
#include "engine.h"

#define DUEL_PHASE (*(volatile u32 *)(0x0229DD14 + 0x48))

ENTRY int entry(EffectCtx *e)
{
    if (!e->cost_ran) {
        u32 p = DUEL_PHASE;
        if (p != 2 && p != 4)
            return 0;
    }
    return opt_rider((u32)e);
}
