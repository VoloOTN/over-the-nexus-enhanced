/* Souleating Oviraptor C2 cost (CAVE_OVI_C2COST): log (side, 0x0FC6, kind 2), then the "You can" rider 0x021E5060. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    turnlog_post(e->controller, 0x0FC6, 2, 0);
    return fn_021E5060((u32)e);
}
