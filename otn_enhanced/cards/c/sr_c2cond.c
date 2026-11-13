/* Scrap Raptor C2 condition (CAVE_SR_C2COND): 0 unless the word at 0x0229A9FC + 0x50 is set; then that word goes
 * through 0x021D2D78 and the set-code thunk 0x02023EE4, and a match defers to the criteria probe 0x021F05A8(ctx). */
#include "engine.h"

#define WATCHED (*(volatile u32 *)(0x0229A9FC + 0x50))

ENTRY int entry(EffectCtx *e)
{
    u32 w = WATCHED;
    if (!w || !fn_02023EE4(fn_021D2D78(w)))
        return 0;
    return criteria_probe((u32)e);
}
