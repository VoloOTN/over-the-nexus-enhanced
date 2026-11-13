/* The Seal of Orichalcos condition (CAVE3_SEAL_COND): 0 if already logged this turn (slot 0xB, kind 5), else 2. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    return turnlog_query(e->controller, 0xB, e->cid, 5) ? 0 : 2;
}
