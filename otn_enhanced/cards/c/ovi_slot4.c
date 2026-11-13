/* Souleating Oviraptor slot 4 (CAVE_OVI_SLOT4): the "You can" tag 0x021E51E4(ctx, a1); when it answers 1, log
 * (side, 0x0FC6, kind 1). Returns the tag's answer. Same shape as psi_slot4.c. */
#include "engine.h"

ENTRY int entry(EffectCtx *e, u32 a1)
{
    int r = you_can_tag(e, a1);
    if (r == 1)
        turnlog_post(e->controller, 0x0FC6, 1, 0);
    return r;
}
