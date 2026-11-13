/* Nikitama gain-node resolver (CAVE_NK_GAINRES): post the gain node 0x3E52 to the turn log. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, 0x3E52, 1, 0);
    return 0;
}
