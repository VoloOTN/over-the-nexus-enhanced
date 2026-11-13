/* Raiden End-Phase mill (CAVE_RAIDEN_EP): if the on-field check and the acting-zone check pass, mill the top 2 of
 * the controller's Deck. Always returns 0. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if (slot_CAVE_RAIDEN_ONFIELD((u32)e) && acting_zone_check((u32)e))
        mill_top_n((u32)e, e->controller, 2);
    return 0;
}
