/* Maiden condition (CAVE_MAIDEN_COND): only for trigger types 0x13/0x14, and only if (side, 0xB, cid, kind 1) is not logged: 2, else 0. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if ((u8)(e->trigger_type + 0xED) > 1)
        return 0;
    return turnlog_query(e->controller, 0xB, e->cid, 1) ? 0 : 2;
}
