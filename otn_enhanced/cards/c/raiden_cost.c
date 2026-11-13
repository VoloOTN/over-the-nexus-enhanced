/* Raiden, Hand of the Lightsworn: cost (CAVE_RAIDEN_COST). Log (side, cid, kind 1) for once-per-turn. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, e->cid, 1, 0);
    return 1;
}
