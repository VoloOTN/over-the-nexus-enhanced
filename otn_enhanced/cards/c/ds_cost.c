/* Ds cost (CAVE_DS_COST): clear the word at 0x0239C98C, log (side, cid, kind 1), return 1. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    *(volatile u32 *)0x0239C98C = 0;
    turnlog_post(e->controller, e->cid, 1, 0);
    return 1;
}
