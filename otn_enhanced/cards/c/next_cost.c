/* NEXT cost (CAVE_NEXT_COST): unless 0x021D2B88 says so, log (side, cid, kind 1). Returns 1.
 * The old stub calls it as `ldr r3,=0x021D2B89; blx r3`, so r3 is its own address: pass (u32)fn_021D2B88. */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1, u32 a2)
{
    if (!fn_021D2B88((u32)e, a1, a2, (u32)fn_021D2B88))
        turnlog_post(e->controller, e->cid, 1, 0);
    return 1;
}
