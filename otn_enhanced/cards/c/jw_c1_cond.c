/* JW C1 condition (CAVE_JW_C1_COND): 0 if (side, 0xB, 0x23EB, kind 1) is logged this turn, else 2. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    return turnlog_query(e->controller, 0xB, 0x23EB, 1) ? 0 : 2;
}
