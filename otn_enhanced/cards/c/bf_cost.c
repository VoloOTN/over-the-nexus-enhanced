/* Brilliant Fusion cost (CAVE_BF_COST): clear the byte at 0x023A1CDC, then unless 0x021D2B88 says so, log
 * (side, cid, kind 1) for once-per-turn. Returns 1. 0x021D2B88 (arity bounded at 4) gets (ctx, 0, a2, a3): the old
 * stub's store left 0 in r1. */
#include "engine.h"

#define BF_LATCH (*(volatile u8 *)0x023A1CDC)

ENTRY int entry(EffectCtx *e, u32 a1, u32 a2, u32 a3)
{
    (void)a1;
    BF_LATCH = 0;
    if (!fn_021D2B88((u32)e, 0, a2, a3))
        turnlog_post(e->controller, e->cid, 1, 0);
    return 1;
}
