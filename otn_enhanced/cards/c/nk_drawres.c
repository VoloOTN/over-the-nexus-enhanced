/* Nikitama draw resolver (CAVE_NK_DRAWRES): when 0x021ACFE8(side, filter 0x020230D5, -1, 1) counts at least one
 * (signed), run the per-cid draw resolver 0x022065B8(ctx). Returns 0. Side = controller ^ ctx[+6]. */
#include "engine.h"

ENTRY int entry(EffectCtx *e)
{
    if ((int)fn_021ACFE8(e->controller ^ ((u8 *)e)[6], 0x020230D5, 0xFFFFFFFF, 1) > 0)
        draw_resolver((u32)e);
    return 0;
}
