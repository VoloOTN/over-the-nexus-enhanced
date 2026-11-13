/* Ultimate Conductor Tyranno C4 condition (CAVE_UCT_C4COND): 0x021F842C's verdict if nonzero, else 0x021F5A1C's.
 * Both get the ctx in r0 as before (arg_regs says neither reads it; passing it costs nothing). */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    int r = fn_021F842C((u32)e);
    return r ? r : fn_021F5A1C((u32)e);
}
