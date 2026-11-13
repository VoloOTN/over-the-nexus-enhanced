/* Cardcar D cost (CAVE_CARDCAR_COST): log (side, 0x2321, kind 1) for once-per-turn, then Tribute it. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, 0x2321, 1, 0);
    return tribute_tag((u32)e);
}
