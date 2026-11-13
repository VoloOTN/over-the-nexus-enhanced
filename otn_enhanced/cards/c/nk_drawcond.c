/* Nikitama draw condition (CAVE_NK_DRAWCOND): 0 unless 0x021ACFE8(side, filter 0x020230D5, -1, 1) counts at least
 * one (signed); then the native draw condition 0x021F069C(ctx). Side = controller ^ ctx[+6]. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if ((int)fn_021ACFE8(e->controller ^ ((u8 *)e)[6], 0x020230D5, 0xFFFFFFFF, 1) <= 0)
        return 0;
    return draw_condition((u32)e);
}
