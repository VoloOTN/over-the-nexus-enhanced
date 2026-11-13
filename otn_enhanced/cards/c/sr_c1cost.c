/* Scrap Raptor C1a cost (CAVE_SR_C1COST, cls3 +10): log (side, cid, kind 1) for once-per-turn, then hand the ctx to 0x021E5060
 * (KB timing.you_can_tag_posts_a_per_copy_rider) and return its result. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, e->cid, 1, 0);
    return fn_021E5060((u32)e);
}
