/* Assault Synchron C2 cost (CAVE_ASSAULT_C2COST): the costless "You can" tag 0x021E50DC(ctx, a1); unless it answers
 * 1, return that. Otherwise log (side, 0x13AE, kind 2) and pay the self-GY-banish cost 0x021E5708(ctx). */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r = costless_you_can(e, a1);
    if (r != 1)
        return r;
    turnlog_post(e->controller, 0x13AE, 2, 0);
    return self_gy_banish_cost((u32)e);
}
