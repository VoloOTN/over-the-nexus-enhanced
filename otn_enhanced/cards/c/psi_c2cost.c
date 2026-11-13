/* Psi-Reflector C2 cost (CAVE_PSI_C2COST): the reveal cost 0x021EAAA0(ctx, a1, ?, a3); when it answers 1, log
 * (side, 0x1008, kind 2). Returns its answer. The old stub calls it as `ldr r2,=0x021EAAA1; blx r2`, so r2 is the
 * callee's own address: pass the identical value, (u32)reveal_cost. */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1, u32 a2, u32 a3)
{
    (void)a2;
    int r = reveal_cost((u32)e, a1, (u32)reveal_cost, a3);
    if (r == 1)
        turnlog_post(e->controller, 0x1008, 2, 0);
    return r;
}
