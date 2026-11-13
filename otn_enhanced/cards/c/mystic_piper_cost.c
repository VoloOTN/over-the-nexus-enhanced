/* Mystic Piper cost (CAVE3_PIPER_COST): log (side, cid, kind 1) for once-per-turn, then Tribute it
 * (0x021E50CC, KB resolver.tribute_tag) and return that result. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, e->cid, 1, 0);
    return tribute_tag((u32)e);
}
